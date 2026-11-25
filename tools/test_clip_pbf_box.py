#!/usr/bin/env python3
"""Tests for tools/clip_pbf_box.py on a tiny synthetic .osm.pbf (no network, no data folder).

  python3 -B -m unittest tools.test_clip_pbf_box
"""
import sys
import tempfile
import unittest
from pathlib import Path

import osmium
from osmium.osm.mutable import Node, Way, Relation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tools.clip_pbf_box as c  # noqa: E402

BOX = (-50.0, -20.0, -49.0, -19.0)  # the box for the test; margin 0.2 makes it -50.2..-48.8, -20.2..-18.8


def write_src(path):
    w = osmium.SimpleWriter(str(path))
    # nodes, in id order
    w.add_node(Node(id=1, location=(-49.5, -19.5), version=1, tags={}))    # A: inside the box
    w.add_node(Node(id=2, location=(-55.0, -25.0), version=1, tags={}))    # B: far outside
    w.add_node(Node(id=3, location=(-50.1, -19.5), version=1, tags={}))    # C: in the margin only
    w.add_node(Node(id=4, location=(-40.0, -10.0), version=1, tags={}))    # X: far, member of a forced way
    w.add_node(Node(id=5, location=(-40.5, -10.5), version=1, tags={}))    # Y: far, member of a forced way
    w.add_node(Node(id=6, location=(-30.0, -5.0), version=1, tags={}))     # Z: far, unused
    # ways, in id order
    w.add_way(Way(id=10, nodes=[1, 2], version=1, tags={'highway': 'residential'}))   # touches the box: kept
    w.add_way(Way(id=11, nodes=[2, 3], version=1, tags={'highway': 'track'}))         # only C is near: C is in margin
    w.add_way(Way(id=12, nodes=[4, 5], version=1, tags={'boundary': 'administrative'}))  # far, forced: kept
    w.add_way(Way(id=13, nodes=[6], version=1, tags={'highway': 'path'}))             # far, not forced: dropped
    # relations, in id order
    w.add_relation(Relation(id=100, tags={'type': 'boundary', 'ISO3166-2': 'BR-XX'},
                            members=[('w', 12, 'outer')], version=1))  # forced: kept with its way
    w.add_relation(Relation(id=101, tags={'type': 'route'}, members=[('w', 10, '')], version=1))  # all ways kept: kept
    w.add_relation(Relation(id=102, tags={'type': 'route'}, members=[('w', 13, '')], version=1))  # way 13 dropped: out
    w.close()


class ClipPbfBox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dir = Path(self.tmp.name)
        self.src = self.dir / 'src.osm.pbf'
        write_src(self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def read_ids(self, path):
        nodes, ways, rels = set(), set(), set()

        class R(osmium.SimpleHandler):
            def node(self, n):
                nodes.add(n.id)

            def way(self, w):
                ways.add(w.id)

            def relation(self, r):
                rels.add(r.id)
        R().apply_file(str(path))
        return nodes, ways, rels

    def test_keeps_the_box_margin_and_forced_relations_only(self):
        out = self.dir / 'out.osm.pbf'
        stats = c.clip(self.src, out, BOX, 0.2, [100], str(self.dir / 'idx.bin'))
        nodes, ways, rels = self.read_ids(out)
        self.assertEqual(ways, {10, 11, 12})        # 13 is far and not forced
        self.assertEqual(nodes, {1, 2, 3, 4, 5})    # 6 is unused; 2 is referenced by 10 and 11
        self.assertEqual(rels, {100, 101})          # 102 needs way 13, which was dropped
        self.assertEqual(stats['ways'], 3)
        self.assertEqual(stats['relations'], 2)

    def test_refuses_to_overwrite_the_output(self):
        out = self.dir / 'out.osm.pbf'
        out.write_bytes(b'x')
        with self.assertRaises(SystemExit):
            c.clip(self.src, out, BOX, 0.2, [100], str(self.dir / 'idx.bin'))

    def test_missing_forced_relation_is_an_error(self):
        out = self.dir / 'out.osm.pbf'
        with self.assertRaises(SystemExit):
            c.clip(self.src, out, BOX, 0.2, [999], str(self.dir / 'idx.bin'))

    def test_bbox_is_checked(self):
        for text in ('1,2,3', '-47,-16,-48,-15', 'nan,-16,-47,-15', '-200,-16,-47,-15'):
            with self.assertRaises(SystemExit):
                c.parse_bbox(text)


if __name__ == '__main__':
    unittest.main()
