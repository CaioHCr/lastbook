#!/usr/bin/env python3
"""Tests for tools/build_addresses_cnefe.py on a tiny CNEFE-shaped CSV zip (no network, no data folder).

  python3 -B -m unittest tools.test_build_addresses_cnefe
"""
import contextlib
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tools.build_addresses_cnefe as b  # noqa: E402

HEADER = ('COD_UNICO_ENDERECO;COD_UF;COD_MUNICIPIO;COD_DISTRITO;COD_SUBDISTRITO;COD_SETOR;NUM_QUADRA;NUM_FACE;CEP;'
          'DSC_LOCALIDADE;NOM_TIPO_SEGLOGR;NOM_TITULO_SEGLOGR;NOM_SEGLOGR;NUM_ENDERECO;DSC_MODIFICADOR;'
          'NOM_COMP_ELEM1;VAL_COMP_ELEM1;NOM_COMP_ELEM2;VAL_COMP_ELEM2;NOM_COMP_ELEM3;VAL_COMP_ELEM3;'
          'NOM_COMP_ELEM4;VAL_COMP_ELEM4;NOM_COMP_ELEM5;VAL_COMP_ELEM5;LATITUDE;LONGITUDE;NV_GEO_COORD;'
          'COD_ESPECIE;DSC_ESTABELECIMENTO;COD_INDICADOR_ESTAB_ENDERECO;COD_INDICADOR_CONST_ENDERECO;'
          'COD_INDICADOR_FINALIDADE_CONST;COD_TIPO_ESPECIE')


def row(uid, muni='3550308', cep='01311000', tipo='RUA', titulo='', nome='JOSE FULANO', num='64', mod='',
        lat='-23.5', lon='-46.6', nv='1', esp='1'):
    """One CNEFE row, built by column name so the positions always match HEADER."""
    names = HEADER.split(';')
    values = dict.fromkeys(names, '')
    values.update({'COD_UNICO_ENDERECO': uid, 'COD_UF': '35', 'COD_MUNICIPIO': muni, 'CEP': cep,
                   'NOM_TIPO_SEGLOGR': tipo, 'NOM_TITULO_SEGLOGR': titulo, 'NOM_SEGLOGR': nome,
                   'NUM_ENDERECO': num, 'DSC_MODIFICADOR': mod, 'LATITUDE': lat, 'LONGITUDE': lon,
                   'NV_GEO_COORD': nv, 'COD_ESPECIE': esp})
    return ';'.join(values[n] for n in names)


ROWS = [
    row('1', tipo='RUA', nome='JOSE FULANO', num='64'),
    row('1', esp='7'),  # same address, a second species: skipped
    row('2', tipo='AVENIDA', titulo='DOUTOR', nome='ALTINO ARANTES', num='1000', cep='04100000', muni='3550308'),
    row('3', tipo='RUA', nome='SEM NUMERO', num='0', mod='SN'),  # sem número: left out
    row('4', tipo='RUA', nome='FACE DE QUADRA', num='10', nv='4'),  # block face: left out
    row('5', tipo='RUA', nome='NUMERO TEXTO', num='S/N'),  # not a number: left out
    row('6', tipo='RUA', nome='SUFIXO', num='12', mod='B'),  # letter in DSC_MODIFICADOR, number kept
    row('7', tipo='RUA', nome='ESTIMADA', num='20', nv='3', lat='-23.4', lon='-46.5'),  # estimated, kept
]


def make_zip(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('35_SP.csv', (HEADER + '\n' + '\n'.join(ROWS) + '\n').encode('latin-1'))


MUNI = {'3550308': 'São Paulo', '3500105': 'Adamantina'}


class BuildAddressesCnefe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.zip = self.dir / '35_SP.zip'
        make_zip(self.zip)

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_row_per_address_and_the_engine_columns(self):
        target, count, stats = b.build(self.zip, 'BR-SP', 35, MUNI, self.dir / 'addresses')
        self.assertEqual(count, 4)  # addresses 1, 2, 6, 7
        self.assertEqual(stats['duplicate_rows_skipped'], 1)
        self.assertEqual(stats['sn_left_out'], 1)
        self.assertEqual(stats['coarse_coordinate_left_out'], 1)
        self.assertEqual(stats['non_numeric_number_left_out'], 1)
        con = sqlite3.connect(target)
        rows = con.execute('SELECT num, street, norm, city, state, zip, lat, lon FROM addr ORDER BY num').fetchall()
        meta = dict(con.execute('SELECT key, value FROM meta').fetchall())
        con.close()
        self.assertEqual(sorted(r[0] for r in rows), ['1000', '12', '20', '64'])
        by_num = {r[0]: r for r in rows}
        self.assertEqual(by_num['64'][1], 'RUA JOSE FULANO')
        self.assertEqual(by_num['64'][2], b.normalize('RUA JOSE FULANO'))
        self.assertEqual(by_num['64'][3], 'São Paulo')
        self.assertEqual(by_num['64'][4], 'BR-SP')
        self.assertEqual(by_num['64'][5], '01311-000')
        self.assertEqual(by_num['1000'][5], '04100-000')
        self.assertIn('AVENIDA DOUTOR ALTINO ARANTES', by_num['1000'][1])
        self.assertEqual(meta['builder'], b.BUILDER)
        self.assertEqual(meta['region'], 'BR-SP')
        self.assertEqual(meta['norm'], 'pt-1')
        self.assertIn('CNEFE', meta['source'])
        self.assertIn('Decreto 8.777/2016', meta['legal_basis'])
        self.assertEqual(json.loads(meta['stats'])['duplicate_rows_skipped'], 1)

    def test_refuses_to_replace_a_file_it_did_not_make(self):
        out = self.dir / 'addresses'
        out.mkdir()
        other = out / 'BR-SP.sqlite'
        con = sqlite3.connect(other)
        con.execute('CREATE TABLE other(x)')
        con.commit()
        con.close()
        with self.assertRaises(SystemExit):
            b.build(self.zip, 'BR-SP', 35, MUNI, out)
        with contextlib.closing(sqlite3.connect(other)) as con:
            self.assertEqual(con.execute("SELECT name FROM sqlite_master WHERE name='other'").fetchone()[0], 'other')

    def test_rerun_replaces_its_own_file(self):
        out = self.dir / 'addresses'
        b.build(self.zip, 'BR-SP', 35, MUNI, out)
        _, count, _ = b.build(self.zip, 'BR-SP', 35, MUNI, out)
        self.assertEqual(count, 4)

    def test_rejects_rows_from_another_state(self):
        other = self.dir / 'other.zip'
        with zipfile.ZipFile(other, 'w') as z:
            z.writestr('x.csv', (HEADER + '\n' + row('9').replace(';35;', ';33;', 1) + '\n').encode('latin-1'))
        with self.assertRaises(SystemExit):
            b.build(other, 'BR-SP', 35, MUNI, self.dir / 'addresses')


if __name__ == '__main__':
    unittest.main()
