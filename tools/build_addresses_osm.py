#!/usr/bin/env python3
"""Build one region's address index from OpenStreetMap addr:* tags (ODbL 1.0).

  python3 tools/build_addresses_osm.py brazil-latest.osm.pbf --id BR-DF --boundary BR-DF \\
      --state DF --bbox=-48.44,-16.20,-47.15,-15.35 --out derived/geo/addresses

Writes <out>/<id>.sqlite with the table the address lookup reads (engine/address_search.py):
  addr(num, street, norm, city, state, zip, lat, lon)   index addr_norm(norm, num)
  meta(key, value)

- A point is kept when it has addr:housenumber (a plain number, optionally one letter) and addr:street.
  Ways use the centre of their node coordinates.
- --boundary takes an OpenStreetMap relation whose ISO3166-2 tag equals that value (for example BR-DF).
  Points outside its outer rings are dropped, so a bounding box that reaches a neighbouring state does not
  leak that state's addresses in. Holes in the boundary are ignored (none in the Federal District).
- norm is engine.address_search.normalize(street), the same function the lookup uses on the query, so an
  index built here is matched by the existing search without any change to the engine.
- The index file is only replaced if it was made by this tool (meta.builder), so a hand-made or other-region
  file in the same folder is never overwritten.
"""
import argparse
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import osmium

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.address_search import normalize  # noqa: E402  (same rules as the lookup)

BUILDER = 'build_addresses_osm.py'
HOUSE = re.compile(r'^\d+[A-Za-z]?$')
SOURCE = '© OpenStreetMap contributors (ODbL 1.0)'


def parse_bbox(text):
    try:
        w, s, e, n = (float(x) for x in text.split(','))
    except ValueError as exc:
        raise SystemExit(f'--bbox needs west,south,east,north: {exc}')
    values = (w, s, e, n)
    if not all(math.isfinite(v) for v in values):
        raise SystemExit('--bbox has a non-finite number')
    if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
        raise SystemExit('--bbox is out of range or in the wrong order (west,south,east,north)')
    return w, s, e, n


def boundary_rings(pbf, iso):
    """Outer rings (lists of (lon, lat)) of the relation tagged ISO3166-2=iso."""
    rings = []
    for area in osmium.FileProcessor(pbf, osmium.osm.RELATION | osmium.osm.WAY | osmium.osm.NODE).with_areas():
        if isinstance(area, osmium.osm.Area) and area.tags.get('ISO3166-2') == iso:
            for ring in area.outer_rings():
                rings.append([(n.lon, n.lat) for n in ring])
            break
    if not rings:
        raise SystemExit(f'no boundary relation with ISO3166-2={iso} in {pbf}')
    return rings


def inside(lon, lat, rings):
    """Even-odd ray casting over all outer rings."""
    hit = False
    for ring in rings:
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def collect(pbf, bbox, rings):
    """Yield (housenumber, street, city, postcode, lon, lat) for addresses inside bbox and boundary."""
    w, s, e, n = bbox
    fp = osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY).with_locations() \
        .with_filter(osmium.filter.KeyFilter('addr:housenumber'))
    for obj in fp:
        tags = obj.tags
        house, street = tags.get('addr:housenumber', '').strip(), tags.get('addr:street', '').strip()
        if not (HOUSE.match(house) and street):
            continue
        if obj.is_node():
            if obj.location.valid() is False:
                continue
            lon, lat = obj.location.lon, obj.location.lat
        else:
            pts = [(nd.lon, nd.lat) for nd in obj.nodes if nd.location.valid()]
            if not pts:
                continue
            lon = sum(p[0] for p in pts) / len(pts)
            lat = sum(p[1] for p in pts) / len(pts)
        if not (w <= lon <= e and s <= lat <= n):
            continue
        if not inside(lon, lat, rings):
            continue
        yield house, street, tags.get('addr:city', '').strip(), tags.get('addr:postcode', '').strip(), lon, lat


def build(pbf, ident, boundary, state, bbox, out_dir, source=SOURCE):
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
    rings = boundary_rings(pbf, boundary)
    rows, seen, skipped = [], set(), 0
    for house, street, city, postcode, lon, lat in collect(pbf, bbox, rings):
        key = (house, street, round(lon, 7), round(lat, 7))
        if key in seen:
            continue
        seen.add(key)
        rows.append((house, street, normalize(street), city, state, postcode, lat, lon))
    tmp = target.with_suffix('.sqlite.tmp')
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE addr(num TEXT, street TEXT, norm TEXT, city TEXT, state TEXT, zip TEXT, lat REAL, lon REAL)')
    db.executemany('INSERT INTO addr VALUES (?,?,?,?,?,?,?,?)', rows)
    db.execute('CREATE INDEX addr_norm ON addr(norm, num)')
    db.execute('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)')
    db.executemany('INSERT INTO meta VALUES (?,?)', [
        ('builder', BUILDER), ('id', ident), ('boundary', boundary), ('bbox', ','.join(str(v) for v in bbox)),
        ('count', str(len(rows))), ('source', source), ('licence', 'ODbL 1.0'),
        ('norm', 'osm-en-1: engine.address_search.normalize'), ('built', time.strftime('%Y-%m-%dT%H:%M:%S')),
    ])
    db.commit()
    db.close()
    os.replace(tmp, target)
    return target, len(rows), skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pbf')
    ap.add_argument('--id', required=True, help='index id, e.g. BR-DF')
    ap.add_argument('--boundary', required=True, help='ISO3166-2 value of the boundary relation, e.g. BR-DF')
    ap.add_argument('--state', default='', help='value stored in the state column, e.g. DF')
    ap.add_argument('--bbox', required=True, help='west,south,east,north (use --bbox=... when the first number is negative)')
    ap.add_argument('--out', default='derived/geo/addresses')
    args = ap.parse_args(argv)
    bbox = parse_bbox(args.bbox)
    if not re.fullmatch(r'[A-Z]{2}(-[A-Za-z0-9_]{1,48})?', args.id):
        raise SystemExit('--id must look like XX or XX-YYY')
    target, count, _ = build(args.pbf, args.id, args.boundary, args.state, bbox, args.out)
    print(f'wrote {target} with {count} addresses')


if __name__ == '__main__':
    main()
