# A detailed map of São Paulo state (`BR-SP`): how it is built and what it holds

A worked example in Brazil for the region map builder proposed in pull request #80, after the La Paz example
([MAP-BO-L.md](MAP-BO-L.md)). It maps the state of São Paulo with the box from [REGIONS-BR.md](REGIONS-BR.md), and it
records how the place finder labels places on each side of the state's borders.

**A prototype dependency.** The builder is a prototype from pull request #80, which is still open. It is not in the
main branch. This map was built and checked with #80 at commit
[`de997abc`](https://github.com/AngryAnt3201/lastbook/commit/de997abc9ad75fba742e11cd2cdb28d076ac08ba), the head of
#80 when the map was built (AngryAnt3201/lastbook, branch `map/bangkok-th-10`). The La Paz map used the earlier commit
`a453274`. The newer commit is needed here because it adds `--boundary`, the option that gives the border labels (see
"Labels at the border"). The files used:

- `tools/build_region_map.py`, the builder
- `tools/check_region_map.py`, the checker
- `tools/test_build_region_map.py`, its tests

If #80 changes, or is merged in another form, the build and the checks here need to be run again.

It adds no code to the app and no map to any pack. The map is not downloaded by setup.

## Why São Paulo

São Paulo is the most populous state in Brazil (general knowledge; not counted here). It is also the first Brazilian
region worked through in detail: its counts appear in pull request #469, which checks the Brazil proposal.

It is large: about 248,000 km², about twice La Paz (128,000 km²). That makes it the first build here that stresses the
machine, so the build's time and memory are recorded below.

## The id and the box

- **Id.** `BR-SP`, the ISO 3166-2 code (REGIONS-BR.md). The id is the maintainers' to change.
- **Box.** `-53.27, -25.46, -44.01, -19.62` (west, south, east, north): the IBGE state extent with the 0.15° margin,
  as it is in the `BR-SP` row of REGIONS-BR.md on `main`.
- **Which box, and #469.** Pull request #469 moves São Paulo's south edge from `-25.46` to `-25.51` (an islet near the
  Paraná border sets it). #469 is still open, so this build uses the `main` box. If #469 is merged, the south edge
  changes by 0.05° and the box should be re-run.
- **Boundary.** The state's OpenStreetMap boundary is relation `298204` (`ISO3166-2=BR-SP`, `admin_level=4`), in the
  Southeast extract.
- **What the rectangle holds.** The box is not the state. It takes in the south of Minas Gerais, the west of Rio de
  Janeiro and the north of Paraná. The part of the box in Paraná is blank in this build, because the extract used
  (below) does not cover the South region.

## Build it

The build machine needs Python 3.11 or later, pyosmium 4.3.2, and about 12 GB of free memory (see the measurements).
Nothing else is installed, and the tool downloads nothing.

The source is Geofabrik's Southeast Brazil extract (states of São Paulo, Rio de Janeiro, Minas Gerais and Espírito
Santo), not the whole of Brazil. The whole-country file is 2.1 GB and was not used (see "Limits of this build").

```bash
# 0. The prototype builder and checker from pull request #80, at commit de997abc (the head of #80 when this was built).
git fetch https://github.com/AngryAnt3201/lastbook.git de997abc9ad75fba742e11cd2cdb28d076ac08ba
git checkout FETCH_HEAD -- tools/build_region_map.py tools/check_region_map.py tools/test_build_region_map.py

# 1. The source: Geofabrik's Southeast Brazil extract (OpenStreetMap, ODbL 1.0), 864,241,364 bytes.
curl -LO https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf
curl -LO https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf.md5 && md5sum -c sudeste-latest.osm.pbf.md5
# expected MD5 73c5062f752b15b70b3238d1e13aa6ed. SHA-256 of the file used:
# a674ac12a69f403207b3e0657ced4376357992b01b1fd1c61b421ccdc069ec5d

# 2. Build. --boundary gives the state's OpenStreetMap relation; the name is in quotes because it has an accent.
python tools/build_region_map.py sudeste-latest.osm.pbf \
    --id BR-SP --name "São Paulo" --bbox=-53.27,-25.46,-44.01,-19.62 --boundary 298204 --out derived/regions

# 3. Check the files, then check that the engine can use them with every connection blocked.
python tools/check_region_map.py derived/regions/BR-SP
python tools/check_region_map.py derived/regions/BR-SP --engine \
    --find "Pinheiros" --find "Campinas" --find "Bragança Paulista" --near=-23.5505,-46.6333
```

### The build this was checked with

| | |
|---|---|
| Source file | `sudeste-latest.osm.pbf` (Geofabrik, Southeast Brazil), 864,241,364 bytes, MD5 `73c5062f752b15b70b3238d1e13aa6ed` (matches Geofabrik's `.md5`) |
| Source SHA-256 | `a674ac12a69f403207b3e0657ced4376357992b01b1fd1c61b421ccdc069ec5d` |
| OpenStreetMap data up to | 2026-11-24T21:21:23Z (from the file's header) |
| Builder | #80 at `de997abc`, unchanged; `--boundary 298204` |
| Built on | 25 November 2026, Windows 11, Python 3.13 with pyosmium 4.3.2 |
| Build time | 2,738 s (46 minutes) |
| Peak memory | 10.1 GB (the builder keeps node locations in memory); the machine has 32 GB |
| Box | -53.27, -25.46, -44.01, -19.62 (west, south, east, north) |

| File | Bytes | SHA-256 |
|---|---|---|
| `derived/geo/national.sqlite` | 1,301,000,192 | `723b71f5599dd0afaddf46344f9a91616724f421f751cec90a14b8278f39e684` |
| `derived/geo/places.sqlite` | 12,132,352 | `b41ece56b1d2b1a1fe6f84a3e0649b513c83187ad10d51839b4e15f9e8e50775` |
| `derived/geo/map.sqlite` | 36,864 | `0bd17638089cfca92b6c5b41fda1a2176d20016d9a02294e9795299f87b65ed5` |
| `derived/geo/national-status.json` | 60 | `685bdb433aaf2d0ad48a985c540a9a74fb6be7e78fe2e7969340f95885efff40` |
| `derived/geo/socal-cells.json` | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

The map set is 1,313,169,470 bytes (1.3 GB), most of it `national.sqlite`. The build's `BR-SP.build.json` lists these
hashes.

The build with the earlier commit `a453274` (before the label option) gave different bytes and counts; it is not used
here.

## What the map holds

Features by layer, from `national.sqlite`:

| Layer | Features | | Layer | Features |
|---|---|---|---|---|
| Buildings (outlines) | 3,113,983 | | Land use and parks | 406,997 |
| Roads | 1,759,872 | | Water areas | 48,579 |
| Waterways (rivers, streams, drains) | 108,464 | | Wetland | 6,302 |
| Place labels | 25,280 | | Railways | 3,940 |
| Islands | 601 | | Beaches | 875 |

Help points: 105,687 in 40 classes. Those a person looks for in an emergency:

| Class | Count | | Class | Count |
|---|---:|---|---|---:|
| Hospitals | 1,741 | | Police | 2,466 |
| Clinics | 3,100 | | Fire stations | 275 |
| Pharmacies | 3,890 | | Drinking water (`drinking_water`) | 565 |
| Springs | 3,276 | | Water towers | 3,640 |
| Shelters | 984 | | Toilets | 1,218 |

These are OpenStreetMap objects with their tags, not an official count.

Place finder: 87,483 rows, from 25,280 place labels and the named help points. Of the place labels, 72,473 rows lie
inside the state's boundary and 15,010 lie outside it.

## Checks

`tools/check_region_map.py` ran on the build and passed all checks. The file checks cover the five files, their
hashes, the tables, the feature layers, the spatial index and the help-point classes. The engine checks load `server.py`
on a copy with every outgoing connection blocked, and ask for:

- **Map tiles** at zoom 10, 13 and 16 around the Praça da Sé.
- **Pins**: 199 pin groups around the Praça da Sé.
- **Nearest help** to the Praça da Sé: pharmacies at 0.1 km and 0.11 km, and a police station at 0.33 km.
- **Place search**: "Pinheiros", "Sé", "Campinas", "Bragança Paulista", "Itapeva", "Socorro" and "Queluz" each return
  their places.
- **Map kinds**: 40 kinds, within the box.

The checker prints "all checks passed".

## Labels at the border

Places in the place finder carry a region name in their detail line. The first build of this map (with an earlier
builder commit) named every place São Paulo, including places in Minas Gerais and Rio de Janeiro, which was wrong. The
builder at `de997abc` takes `--boundary`: only rows inside the boundary get the region's name. Rows outside are kept
and say "OpenStreetMap" only, so they make no region claim.

The acceptance check (requested in #31 on 24 November) is one place on each side of a border, with each label naming
the right region or making no claim:

| Pair | Place | Where it lies | Label in the place finder | Result |
|---|---|---|---|---|
| SP x MG | Socorro (town) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x MG | Monte Sião (town) | Minas Gerais | OpenStreetMap | correct (no claim) |
| SP x MG | Bragança Paulista (city) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x MG | Extrema (town) | Minas Gerais | OpenStreetMap | correct (no claim) |
| SP x RJ | Queluz (village) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x RJ | Itatiaia (town) | Rio de Janeiro | OpenStreetMap | correct (no claim) |
| SP x PR | Itapeva (town, SP) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x PR | Sengés (town) | Paraná | not in this map | see below |

**Paraná side.** The Southeast extract does not cover Paraná, so Sengés is not in this map, and the pair cannot be
tested in it. A separate fixture check was run from the South extract (`sul-latest.osm.pbf`, 431 MB, MD5 OK) over the
Paraná part of the box, with `tools/build_places_region.py` and `--region Paraná`. In that fixture Sengés is labelled
"Paraná (OpenStreetMap)" (-24.114, -49.464). This is a place-finder check only, not part of the map. The same-box
boundary build from the South extract did not run: relation `297640` (Paraná) is not complete in that extract (the cause was not
confirmed; the border ways may sit in the Southeast file).

Why `--boundary` and not "label by the box", or a per-state name: the maintainers accepted the boundary option in #80
(see the comments on pull request #80, [gabtorr, 24 Nov](https://github.com/Immortal-Protocols/lastbook/pull/80#issuecomment-7139738924),
and [AngryAnt3201, 25 Nov](https://github.com/Immortal-Protocols/lastbook/pull/80#issuecomment-7150036735)), and the same
rule was merged for Berlin in #458, which labels places by the city boundary and keeps help beyond it. The acceptance
test in #31 asks for exactly this: [wonderdawg, 25 Nov](https://github.com/Immortal-Protocols/lastbook/issues/31#issuecomment-7146348516)
and [tobsiberlin, 24 Nov](https://github.com/Immortal-Protocols/lastbook/issues/31#issuecomment-7145968512). No region
name is invented for a place outside the state; a place is named only where it lies.

The La Paz and Santiago maps were built with the earlier commit, so their place labels still name the whole box. That is
the known problem in their documents, not fixed here.

## Limits of this build

- **Paraná is not in the map.** The Southeast extract stops at the state borders with the South region. The part of the
  box in Paraná is blank, and no Paraná place is in the map.
- **The whole-country file was not used.** The Brazil extract (2.1 GB) would need about 2.4 times the memory of this
  build (estimated 24 GB, from the 10.1 GB peak for 0.86 GB of source; not measured). This machine has about 10 GB free,
  so the build was not started. Using it, or a union of the Southeast and South extracts, needs more free memory
  or a change to the builder. That is the limit for the Paraná side.
- **Terrain, contours and the 3D view.** The builder does not build them. For São Paulo the relief matters: the Serra
  do Mar and the Paraíba valley are steep.
- **Hospitals are not all hospitals.** Many health centres are mapped as `amenity=hospital`, as in La Paz.
- **Counts follow OpenStreetMap**, not the official registers. Nothing here was compared with CNES, the fire service or
  the state police.
- **Duplicates were not removed** from the help-point counts.

## Licence and attribution

All data in this map is from OpenStreetMap, © OpenStreetMap contributors, under the Open Database License 1.0, taken
from Geofabrik's Southeast Brazil extract. The map is a database built from it, offered under the ODbL as well. The
credit and the date of the data are written into `meta` in `national.sqlite` and into `BR-SP.build.json`.

No IBGE layer is used in the map. The IBGE state polygons were used only to choose the box, as in REGIONS-BR.md.

## Open points for the maintainers

- The Paraná side of the box: a builder that takes a union of extracts, or a separate Paraná map, or a note that the box
  is only valid for the part of the state in the Southeast extract.
- Whether the box should follow #469's south edge (`-25.51`).
- The builder fix for the earlier commit (La Paz, Santiago): adopt `--boundary` there too, or leave their labels as
  documented.

## What was checked, and what was not

- Checked: the Geofabrik file's MD5 and SHA-256 (above); the builder and checker from #80 at `de997abc`; the build's
  files, hashes and counts (above); the checker's file and engine checks; the labels of the border test; the Paraná
  fixture for Sengés.
- Checked against the main branch: the `BR-SP` box in REGIONS-BR.md; the state of pull request #469 (open); the state of
  pull request #80 (open, head `de997abc`).
- Not checked: the Paraná side of the map; the whole-country build (not run); the IBGE licence; the packaged desktop
  app, Windows and macOS, and installing through setup.

