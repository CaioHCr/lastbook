# A detailed map of São Paulo state (`BR-SP`): how it is built and what it holds

A worked example in Brazil for the region map builder proposed in pull request #80, after the La Paz example
([MAP-BO-L.md](MAP-BO-L.md)). It maps the state of São Paulo with the box from [REGIONS-BR.md](REGIONS-BR.md), and it
records how the place finder labels places on each side of the state's borders.

**A prototype dependency.** The builder is a prototype from pull request #80, which is still open. It is not in the
main branch. This map was built with #80 at commit
[`de997abc`](https://github.com/AngryAnt3201/lastbook/commit/de997abc9ad75fba742e11cd2cdb28d076ac08ba) (the head of
#80 when it was built; AngryAnt3201/lastbook, branch `map/bangkok-th-10`), **not** at `a453274`, which La Paz and Santiago
use. The reason is the label option: `de997abc` adds `--boundary`, which gives the state's name only to places inside the
state's OpenStreetMap boundary. `a453274` has no such option, so its maps name every place with the region's name
(see "Labels at the border"). The builder files used, unchanged:

- `tools/build_region_map.py`, the builder
- `tools/check_region_map.py`, the checker
- `tools/test_build_region_map.py`, its tests

If #80 changes, or is merged in another form, the build and the checks here need to be run again.

It adds no code to the app and no map to any pack. The map is not downloaded by setup.

## Why São Paulo

São Paulo is the most populous state in Brazil (general knowledge; not counted here). It is also the first Brazilian
region worked through in detail: its counts appear in pull request #469, which checks the Brazil proposal.

It is large: about 248,000 km², about twice La Paz (128,000 km²).

## The id and the box

- **Id.** `BR-SP`, the ISO 3166-2 code (REGIONS-BR.md). The id is the maintainers' to change.
- **Box.** `-53.27, -25.46, -44.01, -19.62` (west, south, east, north): the IBGE state extent with the 0.15° margin,
  as it is in the `BR-SP` row of REGIONS-BR.md on `main`.
- **Which box, and #469.** Pull request #469 moves São Paulo's south edge from `-25.46` to `-25.51` (an islet near the
  Paraná border sets it). #469 is still open, so this build uses the `main` box.
- **Boundary.** The state's OpenStreetMap boundary is relation `298204` (`ISO3166-2=BR-SP`, `admin_level=4`).
- **What the rectangle holds.** The box is not the state. It takes in the south of Minas Gerais, the west of Rio de
  Janeiro and the north of Paraná.

## Extract: why a cut of the Brazil file

The Southeast extract (`sudeste-latest.osm.pbf`, Geofabrik) covers São Paulo, Rio de Janeiro, Minas Gerais and Espírito
Santo, but **not Paraná**, which is in the South extract. The box reaches Paraná, so an extract that stops at the
Southeast border leaves the north of Paraná blank. The first build of this map, from the Southeast extract, had no
Paraná places at all.

The fix is a cut of Geofabrik's whole-Brazil file, by the box with a 0.2° margin, with the two boundary relations kept
whole. The Brazil file is 2.1 GB; it cannot be built directly on a machine with about 10 GB of free memory, but the cut
can. The cut is made by `tools/clip_pbf_box.py` (in this pull request), and the builder reads the cut.

## Build it

The build machine needs Python 3.11 or later, pyosmium 4.3.2, and about 12 GB of free memory for the cut and about 11 GB
for the build (see the measurements). Nothing else is installed, and the tools download nothing.

```bash
# 0. The prototype builder and checker from pull request #80, at commit de997abc.
git fetch https://github.com/AngryAnt3201/lastbook.git de997abc9ad75fba742e11cd2cdb28d076ac08ba
git checkout FETCH_HEAD -- tools/build_region_map.py tools/check_region_map.py tools/test_build_region_map.py

# 1. The source: Geofabrik's whole-Brazil extract (OpenStreetMap, ODbL 1.0), 2,107,322,473 bytes.
curl -LO https://download.geofabrik.de/south-america/brazil-latest.osm.pbf
curl -LO https://download.geofabrik.de/south-america/brazil-latest.osm.pbf.md5 && md5sum -c brazil-latest.osm.pbf.md5
# expected MD5 c9e85d25cd0d444f564c362a2441d18e (the file used matched this).

# 2. Cut it to the box with a 0.2 margin, keeping the two state boundaries complete (SP 298204, PR 297640).
#    The scratch file for node locations is about 5.4 GB; delete it afterwards. 87 minutes, peak 12.1 GB.
python tools/clip_pbf_box.py brazil-latest.osm.pbf sp_clip.osm.pbf \
    --bbox=-53.27,-25.46,-44.01,-19.62 --margin 0.2 \
    --keep-relation 298204 --keep-relation 297640 --index scratch/locations.idx
sha256sum sp_clip.osm.pbf   # expected 5b3f2ed542fc05097c8eac84f11debfb3360ee47ecc0b94f015678c8fcd1c5ac (584,647,107 bytes)

# 3. Build. --boundary is the state's relation in the cut file; the name is in quotes because it has an accent.
python tools/build_region_map.py sp_clip.osm.pbf \
    --id BR-SP --name "São Paulo" --bbox=-53.27,-25.46,-44.01,-19.62 --boundary 298204 --out derived/regions

# 4. Check the files, then check that the engine can use them with every connection blocked.
python tools/check_region_map.py derived/regions/BR-SP
python tools/check_region_map.py derived/regions/BR-SP --engine \
    --find "Itapeva" --find "Sengés" --find "Socorro" --find "Queluz" --near=-23.5505,-46.6333
```

### The cut (`tools/clip_pbf_box.py`)

Two passes over the input after one pass that reads the two boundary relations. A way is kept when one of its nodes is
in the box with the margin, or when it belongs to a kept relation; a kept way keeps all its nodes. A relation is kept when
all its members are kept ways. Node locations come from a file-backed index, so the memory is the set of kept node ids.

| | |
|---|---|
| Source | `brazil-latest.osm.pbf`, 2,107,322,473 bytes, MD5 `c9e85d25cd0d444f564c362a2441d18e` (Geofabrik's `.md5`), data up to 2026-11-24 |
| Output | `sp_clip.osm.pbf`, 584,647,107 bytes, SHA-256 `5b3f2ed542fc05097c8eac84f11debfb3360ee47ecc0b94f015678c8fcd1c5ac` |
| Kept | 91,879,018 nodes, 7,213,414 ways, 59,990 relations (of 25,394,522 ways read) |
| Forced | relations 298204 (SP) and 297640 (PR), with their 708 member ways |
| Skipped | 165,063 relations with a node or relation member (not a boundary, not a map feature used here) |
| Time | 5,196 s (87 min): pass 0, 1 (2,636 s), 2 (2,536 s) |
| Peak memory | 12.1 GB |

### The build this was checked with

| | |
|---|---|
| Builder | #80 at `de997abc`, unchanged; `--boundary 298204` |
| Source | `sp_clip.osm.pbf` (above); data up to 2026-11-24T21:21:23Z |
| Built on | 25 November 2026, Windows 11, Python 3.13 with pyosmium 4.3.2 |
| Build time | 3,041 s (51 minutes) |
| Peak memory | 10.9 GB (the builder keeps node locations in memory); the machine has 32 GB |
| Box | -53.27, -25.46, -44.01, -19.62 (west, south, east, north) |

| File | Bytes | SHA-256 |
|---|---|---|
| `derived/geo/national.sqlite` | 1,584,545,792 | `0910d7fc1984d52e3b7f8ba78bab8d0971304ea381cdeb5f4b1806e70321e4a8` |
| `derived/geo/places.sqlite` | 13,586,432 | `f4dfc4dc57c68f78b24f659ef80f06dd2c0f391b41a9ecd98beac36ec0ef499a` |
| `derived/geo/map.sqlite` | 36,864 | `9221d11edecf09c163a93c0562d5ccb3cf7653e5850f3e5b1701793a59c5b082` |
| `derived/geo/national-status.json` | 60 | `f630290c6f73b2a5ed54d1edab25e477b0050a5fe4b35ccdcaa4311346956a9e` |
| `derived/geo/socal-cells.json` | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

The map set is 1,599,169,578 bytes (1.6 GB). The build's `BR-SP.build.json` lists these hashes. The national file is
larger than in the Southeast-only build (1.30 GB) because it now includes the north of Paraná and the margin.

## What the map holds

Features by layer, from `national.sqlite`:

| Layer | Features | | Layer | Features |
|---|---|---|---|---|
| Buildings (outlines) | 3,524,114 | | Land use and parks | 486,062 |
| Roads | 2,096,965 | | Water areas | 56,402 |
| Waterways (rivers, streams, drains) | 145,850 | | Wetland | 7,943 |
| Place labels | 28,188 | | Railways | 4,372 |
| Islands | 887 | | Beaches | 895 |

Help points: 119,662 in 40 classes. Those a person looks for in an emergency:

| Class | Count | | Class | Count |
|---|---:|---|---|---:|
| Hospitals | 2,081 | | Police | 2,755 |
| Clinics | 3,689 | | Fire stations | 330 |
| Pharmacies | 4,780 | | Drinking water (`drinking_water`) | 629 |
| Springs | 3,365 | | Water towers | 3,917 |
| Shelters | 1,069 | | Toilets | 1,388 |

These are OpenStreetMap objects with their tags, not an official count.

Place finder: 99,641 rows. Of the place labels and named help points, 72,433 lie inside the state's boundary and 27,208
lie outside it.

## Checks

`tools/check_region_map.py` ran on the build and passed every check (50 checks, "all checks passed"). The file checks
cover the five files, their hashes, the tables, the feature layers, the spatial index and the help-point classes. The
engine checks load `server.py` on a copy with every outgoing connection blocked, and ask for:

- **Map tiles** at zoom 10, 13 and 16 around the Praça da Sé.
- **Pins**: 199 pin groups around the Praça da Sé.
- **Nearest help** to the Praça da Sé: pharmacies at 0.1 km and 0.11 km, and a police station at 0.33 km.
- **Place search** for "Itapeva", "Sengés", "Socorro", "Queluz" and "Ourinhos": each returns its places.

## Labels at the border

The place finder shows a region name in each place's detail line. The builder at `de997abc` writes the name only for
places inside the state's boundary (relation 298204). Places outside it are kept and say "OpenStreetMap" only, so they
make no region claim. This is the rule the maintainers accepted: see the comments on pull request #80
([gabtorr, 24 Nov](https://github.com/Immortal-Protocols/lastbook/pull/80#issuecomment-7139738924) and
[AngryAnt3201, 25 Nov](https://github.com/Immortal-Protocols/lastbook/pull/80#issuecomment-7150036735)) and the same rule
merged for Berlin in [#458](https://github.com/Immortal-Protocols/lastbook/pull/458). The acceptance check asked for in
#31 is one place on each side of a border, each label naming the right region or making no claim:
[wonderdawg, 24 Nov](https://github.com/Immortal-Protocols/lastbook/issues/31#issuecomment-7146348516).

| Pair | Place | Where it lies | Label in the place finder | Result |
|---|---|---|---|---|
| SP x MG | Socorro (town) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x MG | Monte Sião (town) | Minas Gerais | OpenStreetMap | correct (no claim) |
| SP x MG | Bragança Paulista (city) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x MG | Extrema (town) | Minas Gerais | OpenStreetMap | correct (no claim) |
| SP x RJ | Queluz (village) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x RJ | Itatiaia (town) | Rio de Janeiro | OpenStreetMap | correct (no claim) |
| SP x PR | Itapeva (town) | São Paulo | São Paulo (OpenStreetMap) | correct |
| SP x PR | Sengés (town) | Paraná | OpenStreetMap | correct (no claim) |
| SP x PR | Jacarezinho (town) | Paraná | OpenStreetMap | correct (no claim) |
| SP x PR | Ourinhos (city) | São Paulo | São Paulo (OpenStreetMap) | correct |

The same name can exist on both sides: "Jacarezinho" is a town in Paraná (labelled no claim) and a hamlet in São Paulo
(labelled São Paulo); "Cambará" is a town in Paraná and a hamlet in São Paulo. The labels follow the place, not the name.

The La Paz and Santiago maps were built at `a453274`, which has no `--boundary`; their place labels still name the whole
box. That is the known problem in their documents. This map does not change them.

## Address index

Two indexes are possible for `BR-SP`. Both are written to `derived/geo/addresses/BR-SP.sqlite` (one or the other, not
both), in the format of #31: `state = BR-SP` in every row, `meta.region = BR-SP`, `meta.norm = pt-1`.

**Main proposal: the census address register (CNEFE 2022)**, built by `tools/build_addresses_cnefe.py` from IBGE's
`35_SP.zip`. 20,886,637 addresses (one per address code; 1,651,253 addresses with no number left out, and 109,508 whose
point is a block face, locality or census tract left out), 2.87 GB, 821 s, peak 1.94 GB. Its legal basis as the
maintainers were given it: Decreto 8.777/2016, art. 4 (free use of federal open data with credit to the source). No
explicit licence was found on the CNEFE page, in Nota Técnica 01/2024, in IBGE's terms of use or on dados.gov.br, and the
decree text was not re-read here. The index is not in this pull request (no data is committed).

What the CNEFE index answers (run on the main engine with real rows):

- Matches: `41 Rua Salvador Filardi`, `41 RUA SALVADOR FILARDI`, `1578 Avenida Paulista`, `4500 Avenida Morumbi, São Paulo`.
- Does not match: without the street type (`41 Salvador Filardi`), `Av.` for `avenida`, a typed accent, a number after the
  street (`Rua Salvador Filardi, 41`), `SN`.
- Short prefixes are slow: `41 R. Salvador Filardi` took 6.6 s.

**Alternative: OpenStreetMap**, built by `tools/build_addresses_osm.py` (ODbL 1.0). 231,101 addresses, 30 MB, from the
`addr:housenumber` and `addr:street` tags inside the state's OpenStreetMap boundary. It has the example below, which the
CNEFE index does not.

**Public example, CNEFE index (main proposal).** The Hemocentro de São Paulo (Fundação Pró-Sangue) at Avenida Doutor
Enéas Carvalho de Aguiar, 155, is a state-owned unit in the building of the Hospital das Clínicas da FMUSP.

- The address is in the CNEFE index as `155 AVENIDA DOUTOR ENEAS CARVALHO DE AGUIAR`, CEP 05403-000, latitude
  -23.55732, longitude -46.668708.
- The official source opened: the São Paulo State Health Secretariat page for the Fundação Pró-Sangue,
  <https://www.saude.sp.gov.br/ses/institucional/fundacoes/fundacao-pro-sangue-hemocentro-de-sao-paulo>. Quote: "Criada
  em 1984, a Fundação Pró-Sangue tem sua sede no 1.º andar do Prédio dos Ambulatórios do Hospital das Clínicas, na
  avenida Dr. Enéas Carvalho de Aguiar, 155." The page gives no postcode.
- The postcode 05403-000 and the coordinates come from the Ministry's national CNES file, record CO_CNES 2088789 (`AV DR
  ENEAS CARVALHO DE AGUIAR`, number 155, CEP 05403000, latitude -23.5571054705, longitude -46.6683410547, administrative
  sphere ESTADUAL). The CNES file is the Ministry's open data, downloaded from
  `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip` (56,958,207 bytes, SHA-256
  `b72441b75e5707aa016f4538ebbe89894a7dadee2751d1e46bf3d808a15de6ef`).
- **Distance between the two coordinates: 44 m** (CNEFE to CNES, same number and street), below the 100 m reference.
- The engine, main branch, on this index: `155 Avenida Doutor Eneas Carvalho De Aguiar` returns
  `155 AVENIDA DOUTOR ENEAS CARVALHO DE AGUIAR`, detail `São Paulo, BR-SP, 05403-000`, at -23.55732, -46.668708. The
  official spelling `155 Avenida Doutor Enéas Carvalho de Aguiar` returns nothing (the accent and the `Dr.` abbreviation
  do not match), and neither does `155 Av. Dr. Enéas Carvalho de Aguiar`. The query has to use the record's spelling.

Rejected candidates, for the record: Hospital das Clínicas itself at Enéas 255 (official page
<https://www.hc.fm.usp.br/hc/contato>, CEP 05403-000). The CNEFE point for 255 is about 230 m from the CNES coordinates
of two units at the same number, so it was not used as the example. The Legislative Assembly (Av. Pedro Álvares Cabral,
201) is on the official site with CEP 04097-900, which is not in the CNEFE index, so it was not used either.

**Alternative example, OpenStreetMap index.** `15 Viaduto do Chá` finds Viaduto do Chá, 15, São Paulo, 01002-020. This
is the address of the São Paulo city hall (general knowledge; not checked against an official source here). The CNEFE
index does not contain this address (it has no "Viaduto do Chá" at all), so the example works only with the OpenStreetMap
index.

## What is and is not in it

**In it**

- Streets and paths of every class `tools/build_map.py` draws, with the same zoom rules.
- Rivers, streams, reservoirs, wetland, land use, parks and building outlines.
- Place labels and help points in the classes the engine already names (`HELP` in `server.py`).
- The place finder for the box, with the labels described above.

**Not in it**

- **Terrain, contours and the 3D view.** The builder does not build them. For São Paulo the relief matters.
- **Government lists** (state schools, GeoSampa, and the others in #469). Not used here.
- **Anything outside the box.** The margin is used only to keep whole features near the edge.

**Known limits**

- **Hospitals are not all hospitals.** Many health centres are mapped as `amenity=hospital`, as in La Paz.
- **Counts follow OpenStreetMap**, not the official registers.
- **Duplicates were not removed** from the help-point counts.
- **The cut needs about 12 GB of memory and 87 minutes.** The build needs 11 GB. This machine has about 10 GB free at
  the start, so both steps ran close to its limit.
- **Whole Brazil was not built**: the cut is the way this map gets the north of Paraná.

## Licence and attribution

All map data is from OpenStreetMap, © OpenStreetMap contributors, under the Open Database License 1.0, taken from
Geofabrik's Brazil extract and cut to the box. The map is a database built from it, offered under the ODbL as well. The
credit and the date of the data are written into `meta` in `national.sqlite` and into `BR-SP.build.json`.

No IBGE layer is used in the map. The IBGE state polygons were used only to choose the box. The CNEFE index (alternative
address source, above) has its own licence status, described there.

## Open points for the maintainers

- The label option: whether the maintainers want `--boundary` at `de997abc` adopted for La Paz and Santiago too.
- Whether the box should follow #469's south edge (`-25.51`).
- The census address file (CNEFE): its licence on the IBGE site, and whether the decree basis is enough to ship it.
- Address search for the census form (type, abbreviations, accents, `SN`): see the list in the CNEFE pull request.

## What was checked, and what was not

- Checked: the Geofabrik file's MD5; the cut's output hash, counts and time; the builder and checker from #80 at
  `de997abc`; the build's files, hashes and counts; the checker's file and engine checks (50 checks); the labels of the
  border test for all ten places in the table.
- Checked against main: the `BR-SP` box in REGIONS-BR.md; pull request #469 (open); pull request #80 (open, head
  `de997abc`).
- Not checked: the IBGE licence; the census file's licence and the decree text; the Hemocentro's postcode on an official
  page (05403-000 comes from the CNES file; the state page gives no postcode and the FMUSP hematology page did not open);
  whether the Viaduto do Chá address is the city hall's; the packaged desktop app, Windows and macOS, and installing
  through setup.
