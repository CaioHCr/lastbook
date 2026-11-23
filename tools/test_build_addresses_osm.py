#!/usr/bin/env python3
"""Tests for tools/build_addresses_osm.py on a tiny synthetic .osm.pbf (no network, no data folder).

  python3 -B -m unittest tools.test_build_addresses_osm
"""
import contextlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import osmium
from osmium.osm.mutable import Node, Way, Relation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
import build_addresses_osm as b  # noqa: E402


def write_pbf(path):
    """A square boundary tagged BR-DF, points inside and outside it, and a way with an address.

    PBF entities must be written in ascending id order within each type (nodes, then ways, then relations).
    """
    w = osmium.SimpleWriter(str(path))
    # address nodes (ids 1-3) and the nodes of the address way (20-22)
    w.add_node(Node(id=1, location=(-47.8, -15.8), version=1, tags={
        'addr:housenumber': '10', 'addr:street': 'Quadra Teste', 'addr:city': 'Brasília', 'addr:postcode': '70000-000'}))
    # inside the bbox but outside the boundary (a neighbouring state): must be dropped
    w.add_node(Node(id=2, location=(-47.3, -15.8), version=1, tags={
        'addr:housenumber': '20', 'addr:street': 'Rua Fora', 'addr:city': 'Luziânia'}))
    # a house range is not a single address: dropped
    w.add_node(Node(id=3, location=(-47.7, -15.7), version=1, tags={
        'addr:housenumber': '10;12', 'addr:street': 'Quadra Teste'}))
    for nid, lon, lat in [(20, -47.6, -15.6), (21, -47.62, -15.6), (22, -47.61, -15.62)]:
        w.add_node(Node(id=nid, location=(lon, lat), version=1, tags={}))
    # boundary corners (ids 9000-9003)
    corners = [(-48.0, -16.0), (-47.5, -16.0), (-47.5, -15.5), (-48.0, -15.5)]
    for i, (lon, lat) in enumerate(corners):
        w.add_node(Node(id=9000 + i, location=(lon, lat), version=1, tags={}))
    # way 30: a house with a letter, inside the boundary; its nodes are 20-22
    w.add_way(Way(id=30, nodes=[20, 21, 22], version=1, tags={'addr:housenumber': '5B', 'addr:street': 'Via Teste'}))
    # way 900: the closed boundary ring
    w.add_way(Way(id=900, nodes=[9000, 9001, 9002, 9003, 9000], version=1, tags={}))
    # relation 901: the boundary, ISO3166-2=BR-DF
    w.add_relation(Relation(id=901, tags={'type': 'boundary', 'boundary': 'administrative',
                                          'admin_level': '4', 'ISO3166-2': 'BR-DF'},
                            members=[('w', 900, 'outer')], version=1))
    w.close()


class BuildAddressesOsm(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.pbf = self.dir / 'region.osm.pbf'
        write_pbf(self.pbf)

    def tearDown(self):
        self.tmp.cleanup()

    def test_keeps_inside_boundary_and_writes_lookup_table(self):
        out = self.dir / 'addresses'
        target, count, _ = b.build(self.pbf, 'BR-DF', 'BR-DF', 'DF', (-48.1, -16.1, -47.4, -15.4), out)
        self.assertEqual(count, 2)
        con = sqlite3.connect(target)
        rows = con.execute('SELECT num, street, norm, city, state, zip FROM addr ORDER BY num').fetchall()
        meta = dict(con.execute('SELECT key, value FROM meta').fetchall())
        con.close()
        self.assertEqual(rows[0], ('10', 'Quadra Teste', b.normalize('Quadra Teste'), 'Brasília', 'DF', '70000-000'))
        self.assertEqual(rows[1][0], '5B')
        self.assertEqual(meta['builder'], b.BUILDER)
        self.assertEqual(meta['licence'], 'ODbL 1.0')
        self.assertIn('OpenStreetMap', meta['source'])

    def test_refuses_to_replace_a_file_it_did_not_make(self):
        out = self.dir / 'addresses'
        out.mkdir()
        other = out / 'BR-DF.sqlite'
        con = sqlite3.connect(other)
        con.execute('CREATE TABLE other(x)')
        con.commit()
        con.close()
        with self.assertRaises(SystemExit):
            b.build(self.pbf, 'BR-DF', 'BR-DF', 'DF', (-48.1, -16.1, -47.4, -15.4), out)
        with contextlib.closing(sqlite3.connect(other)) as con:
            self.assertEqual(con.execute("SELECT name FROM sqlite_master WHERE name='other'").fetchone()[0], 'other')

    def test_rerun_replaces_its_own_file_without_duplicates(self):
        out = self.dir / 'addresses'
        b.build(self.pbf, 'BR-DF', 'BR-DF', 'DF', (-48.1, -16.1, -47.4, -15.4), out)
        _, count, _ = b.build(self.pbf, 'BR-DF', 'BR-DF', 'DF', (-48.1, -16.1, -47.4, -15.4), out)
        self.assertEqual(count, 2)

    def test_rejects_bad_bbox(self):
        for text in ('1,2,3', '-47,-16,-48,-15', 'nan,-16,-47,-15', '-200,-16,-47,-15'):
            with self.assertRaises(SystemExit):
                b.parse_bbox(text)


if __name__ == '__main__':
    unittest.main()
