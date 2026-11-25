#!/usr/bin/env python3
"""Cut an OpenStreetMap extract to a box (plus a margin), keeping the features the map builders need.

  python3 tools/clip_pbf_box.py brazil-latest.osm.pbf out.osm.pbf \\
      --bbox=-53.27,-25.46,-44.01,-19.62 --margin 0.2 --keep-relation 298204 --keep-relation 297640 \\
      --index /path/to/scratch/locations.idx

Rules (each one is counted and printed):
- A way is kept when one of its nodes lies in the box plus the margin, or when it is a member of a kept relation.
  Kept ways are copied whole: every node they reference is kept, so no way is cut.
- A node is kept when it lies in the box plus the margin, or when a kept way references it.
- A relation is kept when every member is a kept way (or a node or relation that is kept), or when it is one of
  --keep-relation. The ids given there are kept in full: their member ways and nodes are added even outside the box,
  so a region's boundary is complete (the Paraná boundary, 297640, reaches outside the São Paulo box).
- Node locations come from a file-backed index (--index), so memory does not grow with the extract.

Two passes over the input: the first decides which ways and relations are kept; the second writes them. Output keeps
the input's object order, so a PBF writer can read it back.
"""
import argparse
import gc
import math
import os
import sys
import time

import osmium


def parse_bbox(text):
    try:
        w, s, e, n = (float(x) for x in text.split(','))
    except ValueError as exc:
        raise SystemExit(f'--bbox needs west,south,east,north: {exc}')
    if not all(math.isfinite(v) for v in (w, s, e, n)) or not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise SystemExit('--bbox is out of range or in the wrong order (west,south,east,north)')
    return w, s, e, n


class Forced(osmium.SimpleHandler):
    """Pass 0: the member ways of the relations to keep complete. Relations come last in a PBF, so this has to run first."""

    def __init__(self, ids):
        super().__init__()
        self.ids = set(ids)
        self.ways = set()
        self.found = set()

    def relation(self, r):
        if r.id in self.ids:
            self.found.add(r.id)
            self.ways.update(m.ref for m in r.members if m.type == 'w')


class Keep(osmium.SimpleHandler):
    """Pass 1: decide the kept ways and relations, and collect the nodes they need."""

    def __init__(self, box, forced_relations):
        super().__init__()
        self.box = box
        self.forced = set(forced_relations)
        self.forced_ways = set()
        self.kept_ways = set()
        self.need_nodes = set()
        self.kept_relations = set()
        self.ways_seen = 0
        self.rel_members_missing = 0

    def in_box(self, lon, lat):
        w, s, e, n = self.box
        return w <= lon <= e and s <= lat <= n

    def way(self, w):
        self.ways_seen += 1
        keep = w.id in self.forced_ways
        inside = False
        locs = []
        for nd in w.nodes:
            if not nd.location.valid():
                continue
            locs.append(nd.ref)
            if self.in_box(nd.location.lon, nd.location.lat):
                inside = True
        if inside or keep:
            self.kept_ways.add(w.id)
            self.need_nodes.update(n.ref for n in w.nodes)

    def relation(self, r):
        members = list(r.members)
        if r.id in self.forced:
            for m in members:
                if m.type == 'w':
                    self.forced_ways.add(m.ref)
            self.kept_relations.add(r.id)
            return
        ways = [m.ref for m in members if m.type == 'w']
        others = [m for m in members if m.type != 'w']
        if others:
            self.rel_members_missing += 1
            return
        if ways and all(ref in self.kept_ways for ref in ways):
            self.kept_relations.add(r.id)


class Write(osmium.SimpleHandler):
    """Pass 2: copy the kept nodes, ways and relations."""

    def __init__(self, writer, box, keep):
        super().__init__()
        self.writer = writer
        self.box = box
        self.keep = keep
        self.nodes = 0
        self.ways = 0
        self.relations = 0

    def node(self, n):
        if n.id in self.keep.need_nodes or (n.location.valid() and self.in_box(n.location.lon, n.location.lat)):
            self.writer.add_node(n)
            self.nodes += 1

    def in_box(self, lon, lat):
        w, s, e, n = self.box
        return w <= lon <= e and s <= lat <= n

    def way(self, w):
        if w.id in self.keep.kept_ways:
            self.writer.add_way(w)
            self.ways += 1

    def relation(self, r):
        if r.id in self.keep.kept_relations:
            self.writer.add_relation(r)
            self.relations += 1


def clip(src, dst, bbox, margin, forced, index):
    w, s, e, n = bbox
    expanded = (w - margin, s - margin, e + margin, n + margin)
    t0 = time.time()
    fx = Forced(forced)
    fx.apply_file(src)
    missing = set(forced) - fx.found
    if missing:
        raise SystemExit(f'--keep-relation {sorted(missing)} not found in {src}')
    print(f'pass 0: {len(fx.found)} forced relation(s), {len(fx.ways):,} member ways', flush=True)
    keep = Keep(expanded, forced)
    keep.forced_ways = set(fx.ways)
    # Node locations come from a file-backed index; the ways and relations are read in the same pass.
    keep.apply_file(src, locations=True, idx=f'sparse_file_array,{index}')
    print(f'pass 1: {keep.ways_seen:,} ways read, {len(keep.kept_ways):,} kept, '
          f'{len(keep.need_nodes):,} nodes referenced, {len(keep.kept_relations):,} relations kept, '
          f'{round(time.time() - t0)} s', flush=True)
    if os.path.exists(dst):
        raise SystemExit(f'{dst} exists; remove it or choose another name')
    writer = osmium.SimpleWriter(dst)
    handler = Write(writer, expanded, keep)
    t1 = time.time()
    handler.apply_file(src)
    writer.close()
    print(f'pass 2: {handler.nodes:,} nodes, {handler.ways:,} ways, {handler.relations:,} relations written, '
          f'{round(time.time() - t1)} s', flush=True)
    stats = {'nodes': handler.nodes, 'ways': handler.ways, 'relations': handler.relations,
             'expanded_box': expanded, 'missing_member_relations': keep.rel_members_missing}
    del keep, handler, fx
    gc.collect()  # releases the file-backed location index
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--bbox', required=True, help='west,south,east,north (use --bbox=... when the first number is negative)')
    ap.add_argument('--margin', type=float, default=0.2, help='degrees added on every side (default 0.2)')
    ap.add_argument('--keep-relation', type=int, action='append', default=[], dest='forced',
                    help='relation id to keep complete, with its members (may be repeated)')
    ap.add_argument('--index', required=True, help='scratch file for node locations (deleted by you afterwards)')
    args = ap.parse_args(argv)
    bbox = parse_bbox(args.bbox)
    stats = clip(args.src, args.dst, bbox, args.margin, args.forced, args.index)
    print(stats)


if __name__ == '__main__':
    main()
