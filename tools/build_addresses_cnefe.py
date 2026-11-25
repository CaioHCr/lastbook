#!/usr/bin/env python3
"""Build one state's address index from the IBGE CNEFE 2022 (Cadastro Nacional de Endereços para Fins Estatísticos).

  python3 tools/build_addresses_cnefe.py 35_SP.zip --id BR-SP --uf 35 \\
      --municipios municipios_35.json --out derived/geo/addresses

The input is one state's CSV zip as IBGE publishes it (member 35_SP.csv, ';'-separated, latin-1 text). The municipality
names come from a JSON list of IBGE localities objects ({'id': 3500105, 'nome': 'Adamantina', ...}), read from the IBGE
localities API (https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios) and saved as a file, so the
build itself needs no network.

Writes <out>/<id>.sqlite, the table the address lookup reads (engine/address_search.py):
  addr(num, street, norm, city, state, zip, lat, lon)   index addr_norm(norm, num)
  meta(key, value)

Rules, each counted and written to meta:
- One address per COD_UNICO_ENDERECO. The file has one row per species at an address (COD_ESPECIE); the first row
  is kept and the others are not repeated.
- Street = NOM_TIPO_SEGLOGR + NOM_TITULO_SEGLOGR + NOM_SEGLOGR, so "RUA DOUTOR FULANO" keeps its type. norm is the
  engine's normalize() of that street, the same function the query goes through.
- NUM_ENDERECO = 0 with DSC_MODIFICADOR SN is a "sem número" (no number) address. The engine's lookup needs a number,
  so these rows are left out and counted.
- Only coordinates from the first three NV_GEO_COORD levels are kept: 1 original census point, 2 point moved for
  apartments at one number, 3 estimated point. Levels 4 (face of block), 5 (locality) and 6 (census tract) are not a
  house's position and are left out and counted.
- zip is written 00000-000, as the lookup compares it.
- The index file is only replaced if this tool made it, so a file made by another tool is never overwritten.

Data: IBGE, CNEFE 2022. The licence and legal basis are written into meta as given in the build's arguments.
"""
import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.address_search import normalize  # noqa: E402  (same rules as the lookup)

BUILDER = 'build_addresses_cnefe.py'
SOURCE = 'IBGE, Cadastro Nacional de Endereços para Fins Estatísticos - CNEFE, Censo Demográfico 2022'
LEGAL = ('Dado público federal. Crédito obrigatório ao IBGE, Decreto 8.777/2016, art. 4 '
         '(dados abertos do Poder Executivo federal, livre uso com citação da fonte). '
         'Nenhuma licença explícita foi encontrada na página do CNEFE, na Nota Técnica 01/2024, no termo de uso do IBGE '
         'ou no dados.gov.br.')
KEEP_NV = {'1', '2', '3'}
NUM = re.compile(r'^\d+$')


def load_municipalities(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return {str(m['id']): m['nome'] for m in data}


def fmt_zip(cep):
    cep = re.sub(r'\D', '', cep)
    return f'{cep[:5]}-{cep[5:]}' if len(cep) == 8 else ''


def read_rows(zip_path, uf):
    """Yield dicts for the CSV rows of one state, in file order."""
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.namelist() if m.lower().endswith('.csv')]
        if len(members) != 1:
            raise SystemExit(f'expected one CSV in {zip_path}, found {members}')
        with z.open(members[0]) as raw:
            text = io.TextIOWrapper(raw, encoding='latin-1', newline='')
            reader = csv.reader(text, delimiter=';')
            header = next(reader)
            col = {name: i for i, name in enumerate(header)}
            for r in reader:
                if len(r) < len(header):
                    r = r + [''] * (len(header) - len(r))
                if r[col['COD_UF']] != str(uf):
                    raise SystemExit(f'row for UF {r[col["COD_UF"]]} in a file for UF {uf}')
                yield {k: r[i] for k, i in col.items() if k in (
                    'COD_UNICO_ENDERECO', 'COD_MUNICIPIO', 'NOM_TIPO_SEGLOGR', 'NOM_TITULO_SEGLOGR', 'NOM_SEGLOGR',
                    'NUM_ENDERECO', 'DSC_MODIFICADOR', 'CEP', 'LATITUDE', 'LONGITUDE', 'NV_GEO_COORD')}


def build(zip_path, ident, uf, municipalities, out_dir, batch=500_000):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f'{ident}.sqlite'
    if target.exists():
        con = sqlite3.connect(target)
        try:
            marker = con.execute("SELECT value FROM meta WHERE key='builder'").fetchone()
        except sqlite3.Error:
            marker = None
        finally:
            con.close()
        if not marker or marker[0] != BUILDER:
            raise SystemExit(f'{target} exists and was not made by {BUILDER}; not replaced')
        target.unlink()
    tmp = target.with_suffix('.sqlite.tmp')
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    db.execute('PRAGMA journal_mode=OFF')
    db.execute('PRAGMA synchronous=OFF')
    db.execute('CREATE TABLE addr(num TEXT, street TEXT, norm TEXT, city TEXT, state TEXT, zip TEXT, lat REAL, lon REAL)')

    try:
        return _fill(db, tmp, target, zip_path, ident, uf, municipalities, batch)
    finally:
        db.close()


def _fill(db, tmp, target, zip_path, ident, uf, municipalities, batch):
    t0 = time.time()
    read = 0
    ids = set()
    duplicates = 0
    sn = 0
    coarse = 0
    no_coords = 0
    no_number = 0
    bad_number = 0
    written = 0
    pending = []
    nv_counts = {}
    for r in read_rows(zip_path, uf):
        read += 1
        nv = r['NV_GEO_COORD'].strip()
        nv_counts[nv] = nv_counts.get(nv, 0) + 1
        uid = int(r['COD_UNICO_ENDERECO'])
        if uid in ids:
            duplicates += 1
            continue
        ids.add(uid)
        if nv not in KEEP_NV:
            coarse += 1
            continue
        n = r['NUM_ENDERECO'].strip()
        if not n:
            no_number += 1
            continue
        if not NUM.match(n):
            bad_number += 1
            continue
        if int(n) == 0 or r['DSC_MODIFICADOR'].strip().upper() == 'SN':
            sn += 1
            continue
        try:
            lat, lon = float(r['LATITUDE']), float(r['LONGITUDE'])
        except ValueError:
            no_coords += 1
            continue
        street = ' '.join(x.strip() for x in (r['NOM_TIPO_SEGLOGR'], r['NOM_TITULO_SEGLOGR'], r['NOM_SEGLOGR']) if x.strip())
        if not street:
            no_number += 1
            continue
        city = municipalities.get(r['COD_MUNICIPIO'].strip(), '')
        pending.append((str(int(n)), street, normalize(street), city, ident, fmt_zip(r['CEP']), lat, lon))
        if len(pending) >= batch:
            db.executemany('INSERT INTO addr VALUES (?,?,?,?,?,?,?,?)', pending)
            written += len(pending)
            pending = []
            print(f'{read:,} rows read, {written:,} written, {time.time() - t0:.0f}s', flush=True)
    if pending:
        db.executemany('INSERT INTO addr VALUES (?,?,?,?,?,?,?,?)', pending)
        written += len(pending)
    db.execute('CREATE INDEX addr_norm ON addr(norm, num)')
    db.execute('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)')
    stats = {
        'rows_read': read, 'distinct_addresses': len(ids), 'duplicate_rows_skipped': duplicates,
        'no_number_left_out': no_number, 'sn_left_out': sn, 'coarse_coordinate_left_out': coarse,
        'no_coordinates_left_out': no_coords, 'non_numeric_number_left_out': bad_number,
        'nv_geo_coord_counts': nv_counts,
    }
    db.executemany('INSERT INTO meta VALUES (?,?)', [
        ('builder', BUILDER), ('id', ident), ('region', ident), ('state', ident), ('norm', 'pt-1'),
        ('count', str(written)), ('source', SOURCE), ('legal_basis', LEGAL), ('licence', 'no explicit licence found'),
        ('stats', json.dumps(stats, ensure_ascii=False)), ('built', time.strftime('%Y-%m-%dT%H:%M:%S')),
    ])
    db.commit()
    db.close()
    os.replace(tmp, target)
    return target, written, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('zip', help='the state CSV zip from IBGE, e.g. 35_SP.zip')
    ap.add_argument('--id', required=True, help='index id, e.g. BR-SP')
    ap.add_argument('--uf', required=True, type=int, help='IBGE state code, e.g. 35 for São Paulo')
    ap.add_argument('--municipios', required=True, help='JSON list of IBGE municipality objects for the state')
    ap.add_argument('--out', default='derived/geo/addresses')
    args = ap.parse_args(argv)
    if not re.fullmatch(r'[A-Z]{2}(-[A-Za-z0-9_]{1,48})?', args.id):
        raise SystemExit('--id must look like XX or XX-YYY')
    muni = load_municipalities(args.municipios)
    target, count, stats = build(args.zip, args.id, args.uf, muni, args.out)
    print(f'wrote {target} with {count} addresses')
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
