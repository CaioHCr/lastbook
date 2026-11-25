# A detailed map of São Paulo state (`BR-SP`): how it is built and what it holds

A worked example in Brazil for the region map builder proposed in pull request #80, after the La Paz example
(`BO-L`, [MAP-BO-L.md](MAP-BO-L.md)), built with that tool unchanged. It maps the state of São Paulo with the box from
[REGIONS-BR.md](REGIONS-BR.md), to test that box against a real build, and it records where the builder fails on a
border: the place finder labels every place with the region's name.

**A prototype dependency.** The builder is a prototype from pull request #80, which is still open. It is not in the
main branch. This map was built and checked with #80 at commit `a453274` (AngryAnt3201/lastbook, branch
`map/bangkok-th-10`), the same commit La Paz used. The files used, at that commit:

- `tools/build_region_map.py`, the builder
- `tools/check_region_map.py`, the checker
- `tools/test_build_region_map.py`, its tests

If #80 changes, or is merged in another form, the build and the checks here need to be run again. Pull request #396
is a newer builder (`tools/build_osm_region.py`) and was not used.

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
- **Which box, and #469.** Pull request #469 recomputes the boxes from IBGE's full-resolution file and moves São Paulo's
  south edge from `-25.46` to `-25.51` (an islet near the Paraná border sets it). #469 is still open, so this build uses
  the `main` box. If #469 is merged, the south edge changes by 0.05° and the box should be re-run.
- **What the rectangle holds.** The box is not the state. It takes in the south of Minas Gerais, the west of Rio de
  Janeiro and the north of Paraná. The part of the box in Paraná is blank in this
  build, because the extract used (below) does not cover the South region. The parts in Minas Gerais and Rio de Janeiro
  are drawn, and the place finder labels them with the São Paulo name. See "Border test".

## Build it

The build machine needs Python 3.11 or later, pyosmium 4.3.2 (the version La Paz used) and about 12 GB of free memory
(see the measurements). Nothing else is installed, and the tool downloads nothing.

The source is Geofabrik's Southeast Brazil extract (states of São Paulo, Rio de Janeiro, Minas Gerais and Espírito
Santo), not the whole of Brazil. The whole-country file is 2.1 GB and was not used: the regional file is 864 MB and
covers the box.

```bash
# 0. The prototype builder and checker from pull request #80, at commit a453274 (as in MAP-BO-L.md).
git fetch https://github.com/AngryAnt3201/lastbook.git a453274353b2816b4ccb0114310024ea54c970b2
git checkout FETCH_HEAD -- tools/build_region_map.py tools/check_region_map.py tools/test_build_region_map.py

# 1. The source: Geofabrik's Southeast Brazil extract (OpenStreetMap, ODbL 1.0), 864,241,364 bytes.
curl -LO https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf
curl -LO https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf.md5 && md5sum -c sudeste-latest.osm.pbf.md5
# expected: 73c5062f752b15b70b3238d1e13aa6ed (MD5). The build recorded SHA-256
# a674ac12a69f403207b3e0657ced4376357992b01b1fd1c61b421ccdc069ec5d for this file.

# 2. Build. Give --name with the accent in quotes; the box starts with a minus sign, so use --bbox=...
python tools/build_region_map.py sudeste-latest.osm.pbf \
    --id BR-SP --name "São Paulo" --bbox=-53.27,-25.46,-44.01,-19.62 --out derived/regions

# 3. Check the files, then check that the engine can use them with every connection blocked.
python tools/check_region_map.py derived/regions/BR-SP
python tools/check_region_map.py derived/regions/BR-SP --engine \
    --find "Pinheiros" --find "Campinas" --find "Bragança Paulista" --near=-23.5505,-46.6333
```

The `--name` is written into every place row (see the border test). Nothing else in the build depends on it.

### The build this was checked with

| | |
|---|---|
| Source file | `sudeste-latest.osm.pbf` (Geofabrik, Southeast Brazil), 864,241,364 bytes, MD5 `73c5062f752b15b70b3238d1e13aa6ed` (matches Geofabrik's `.md5`) |
| Source SHA-256 | `a674ac12a69f403207b3e0657ced4376357992b01b1fd1c61b421ccdc069ec5d` |
| OpenStreetMap data up to | 2026-11-24T21:21:23Z (from the file's header) |
| Built on | 25 November 2026, Windows 11, Python 3.13 with pyosmium 4.3.2 |
| Build time | 3,310 s (55 minutes) on the same machine, while another build (the address index) ran alongside it |
| Peak memory | 10.2 GB (the builder keeps node locations in memory); the machine had 31 GB |
| Box | -53.27, -25.46, -44.01, -19.62 (west, south, east, north) |

| File | Bytes | SHA-256 |
|---|---|---|
| `derived/geo/national.sqlite` | 1,302,028,288 | `fb677cff491f78f3050fdc12133923b380ebd4d5a376f7e8288d7fa020f6173a` |
| `derived/geo/places.sqlite` | 13,135,872 | `8197771d51288ed1653a9cbd2e4cf50bd0593e2ef635205cf37eb95b8a77936c` |
| `derived/geo/map.sqlite` | 36,864 | `f96ec40b6c865f6e587aa1f6f79328ebf0455ac7f2821961fdd09c2d9ae61248` |
| `derived/geo/national-status.json` | 60 | `10aa9ffba5a4f9ba092e850dc4ad7245a18ea97e91a15ad3729af9d4d48d0687` |
| `derived/geo/socal-cells.json` | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

The map set is 1,315,201,086 bytes (1.3 GB), most of it `national.sqlite`. The builder's own `.build.json` lists
these hashes. The build is not repeated here bit for bit: the same extract and options should give the same bytes,
but that was not tested.

## What the map holds

Features by layer, from `national.sqlite`:

| Layer | Features | | Layer | Features |
|---|---|---|---|---|
| Buildings (outlines) | 3,113,983 | | Land use and parks | 406,997 |
| Roads | 1,759,872 | | Water areas | 48,580 |
| Waterways (rivers, streams, drains) | 108,464 | | Wetland | 6,302 |
| Place labels | 25,280 | | Railways | 3,921 |
| Islands | 601 | | Beaches | 875 |

Help points: 105,605 in 40 classes. Those a person looks for in an emergency:

| Class | Count | | Class | Count |
|---|---:|---|---|---:|
| Hospitals | 1,697 (1,566 with a name) | | Police | 2,466 |
| Clinics | 3,074 | | Fire stations | 275 |
| Pharmacies | 3,883 | | Drinking water (`drinking_water`) | 565 |
| Springs | 3,276 | | Water towers | 3,640 |
| Shelters | 984 | | Toilets | 1,218 |

These are OpenStreetMap objects with their tags, not an official count. They are useful for the map, and the
difference from official registers is unknown (see "Known limits").

Place finder: 87,434 rows, from 25,280 place labels and the named help points.

## Checks

`tools/check_region_map.py` ran on the build without errors. The file checks cover the five files, their hashes,
the tables, the feature layers, the spatial index and the help-point classes. The engine checks load `server.py` on a
copy with every outgoing connection blocked, and ask for:

- **Map tiles** at zoom 10, 13 and 16 around the Praça da Sé.
- **Pins**: 199 pin groups around the Praça da Sé.
- **Nearest help** to the Praça da Sé: pharmacies at 0.1 km and 0.11 km, and a police station (women's police
  station, 1ª Delegacia de Defesa da Mulher) at 0.33 km.
- **Place search**: "Pinheiros", "Sé", "Campinas", "Bragança Paulista", "Extrema", "Bananal", "Barra Mansa",
  "Ourinhos", "Jacarezinho" and "Santos" each return at least one result. Some of those results are outside São Paulo,
  and their region label is wrong (see the border test below).
- **Map kinds**: 40 kinds, within the box.

The checker prints "all checks passed".

## Border test

The test needs one place on each side of a boundary. The label the place finder shows must name the right region, or
make no region claim. The builder does not do that yet: it writes the `--name` into every row's detail line.

| Pair | Side | Place (kind) | Coordinates | Label in the place finder | Result |
|---|---|---|---|---|---|
| SP x MG | São Paulo | Socorro (town) | -22.590, -46.525 | São Paulo (OpenStreetMap) | correct |
| SP x MG | Minas Gerais | Monte Sião (town) | -22.433, -46.573 | São Paulo (OpenStreetMap) | **wrong** |
| SP x MG | São Paulo | Bragança Paulista (city) | -22.952, -46.542 | São Paulo (OpenStreetMap) | correct |
| SP x MG | Minas Gerais | Extrema (town) | -22.855, -46.319 | São Paulo (OpenStreetMap) | **wrong** |
| SP x RJ | São Paulo | Queluz (village) | -22.537, -44.775 | São Paulo (OpenStreetMap) | correct |
| SP x RJ | Rio de Janeiro | Itatiaia (town) | -22.496, -44.563 | São Paulo (OpenStreetMap) | **wrong** |
| SP x PR | Paraná | not in this build | | | not tested |

Verdict: the map draws both sides of each boundary, and the places are found, but the label is the state's name on
both sides. Three of the six labels name the wrong state. The Paraná side is not in this build at all: the Southeast
extract does not cover the South region, so the part of the box in Paraná is blank. Testing SP x PR needs the South
extract, a second build with the same tool, or a fix to the label first.

This is the problem the pull request thread raised for La Paz and Santiago (for example, Oruro is labelled "La Paz").
The smallest fix is in the builder, not in the map: label each place with the name of the area it lies in, or with no
region name, and keep the places in the box. This document does not change the builder.

## Address search and the example

The box has an address index from OpenStreetMap, built by `tools/build_addresses_osm.py` (ODbL 1.0), in the format
of #31: `derived/geo/addresses/BR-SP.sqlite`, with `state = BR-SP` in every row, `meta.region = BR-SP` and
`meta.norm = pt-1`. It is a separate file, not listed in `map-set.json`.

- **Addresses:** 231,101, from `addr:housenumber` and `addr:street` tags inside the OpenStreetMap boundary of the
  state (`ISO3166-2=BR-SP`). Points outside that boundary are dropped, so the box does not bring in addresses from
  Minas Gerais or Rio de Janeiro. The file is 30 MB.
- **`meta.norm = pt-1`** is recorded, but the search engine on `main` does not yet choose a normalization by index;
  it uses the shared `normalize()`. The name is a declaration for when that work lands (#79, #386).

Example. The search is given a number first, then the street with its type:

- `15 Viaduto do Chá` finds two points at Viaduto do Chá, 15, São Paulo, 01002-020. This is the address of the São
  Paulo city hall (general knowledge; not checked against an official source here).
- `4500 Avenida Morumbi` finds Avenida Morumbi, 4500, São Paulo, 05650-905. This is the address of the São Paulo state
  government palace (general knowledge; not checked here).

What does not work, with the engine as it is on `main`:

- `Av. Morumbi 4500` and `15 Viaduto do Cha` (no accent) find nothing. The search needs the full type word and the
  accent as it is written.
- `Rua do Lago, 50` (street first, number after) is not an address query at all.
- `SN` (no number) is not understood. In the OpenStreetMap data no-number addresses are left out.
- The result's source is written as "Overture Maps" for every index. For these rows the source is OpenStreetMap.

## What is and is not in it

**In it**

- Streets and paths of every class `tools/build_map.py` draws, with the same zoom rules, from the Serra do Mar to the
  interior.
- Rivers, streams, reservoirs, wetland, land use, parks and building outlines.
- Place labels and help points in the classes the engine already names (`HELP` in `server.py`).
- The place finder for the box, with the names as the builder writes them.

**Not in it**

- **Paraná** (the south of the box). The Southeast extract stops at the state borders with the South region, so the
  part of the box in Paraná is blank. The box does reach Paraná, and Paraná is not labelled.
- **Terrain, contours and the 3D view.** The builder does not build them. For São Paulo the relief matters: the Serra
  do Mar and the Paraíba valley are steep.
- **Addresses from the census (CNEFE 2022).** Not used: the IBGE licence for the address file has not been read on the
  IBGE site, and Overture's copy of it carries a per-row licence (`LicenseRef-Proprietary`) that does not match its own
  attribution page (which says CC0). Both need an answer before the census is used. Until then the index is from
  OpenStreetMap only.
- **Government lists.** The state's school list, GeoSampa and the other civic layers listed in #469 are not used here.
  Those with a clear open licence (state schools, CC BY 4.0) can be added in a later map; the rest need a decision first.
- **Anything outside the box.** The Minas Gerais and Rio de Janeiro parts are drawn with the names of the places they
  have, labelled as São Paulo (see the border test).

**Known limits**

- **Hospitals are not all hospitals.** Many health centres are mapped as `amenity=hospital`, as in La Paz.
- **Counts follow OpenStreetMap**, not the official registers. Nothing here was compared with CNES, the fire service or
  the state police.
- **The place finder labels every place with the state's name**, including those in Minas Gerais and Rio de Janeiro.
- **Duplicates were not removed** from the help-point counts.

## Licence and attribution

All data in this map is from OpenStreetMap, © OpenStreetMap contributors, under the Open Database License 1.0, taken
from Geofabrik's Southeast Brazil extract. The map and the address index are databases built from it, offered under
the ODbL as well. The credit and the date of the data are written into `meta` in `national.sqlite`, into
`map-set.json` and into `BR-SP.build.json`. The address index records the licence in its own `meta`.

No IBGE layer is used. The IBGE state polygons were used only to choose the box, as in REGIONS-BR.md; the IBGE
licence is not settled for any layer in this build.

## Open points for the maintainers

- The place finder's region label (above). The fix belongs to #80 or its successor.
- The Paraná side of the box: a second extract, or a note that the box is only valid for the part of the state in
  the Southeast extract.
- The census (CNEFE 2022) address file: its licence on the IBGE site, and Overture's per-row licence.
- Whether the state boundary should be used to clip the place finder, not only the box.

## What was checked, and what was not

- Checked: the Geofabrik file's MD5 and SHA-256 (above); the builder and checker from #80 at `a453274`; the build's
  files, hashes and counts (above); the checker's file and engine checks; the place labels for the border test; the
  address index's count, its state values and its meta; the search results for the examples.
- Checked against the main branch: the `BR-SP` box in REGIONS-BR.md; the state of pull request #469 (open).
- Not checked: the Paraná side of the box; the IBGE licence; the census file; the OpenStreetMap address counts against
  a second source; whether the public buildings' addresses are the official ones (the statements above are general
  knowledge); the packaged desktop app, Windows and macOS, and installing through setup.

## The address index from the census (CNEFE 2022)

The address index for `BR-SP` can come from the IBGE census address register (CNEFE, Censo Demográfico 2022), instead of
OpenStreetMap. `tools/build_addresses_cnefe.py` builds it from IBGE's state file `35_SP.zip`
(Arquivos_CNEFE/CSV/UF, 1,082,015,432 bytes). It is written to `derived/geo/addresses/BR-SP.sqlite`, in the format of
#31, with `state = BR-SP` in every row and `meta.region = BR-SP`, `meta.norm = pt-1`. It replaces the OpenStreetMap index
in the same path: both cannot sit in one folder.

**Legal basis, as the maintainers were given it.** The data is public federal data. The credit to IBGE is required,
under Decreto 8.777/2016, art. 4 (open data of the federal executive, free use with citation of the source). The decree
text was not re-read in this build (the Planalto site did not answer). No explicit licence was found on the CNEFE page,
in IBGE's Nota Técnica 01/2024, in IBGE's terms of use or on dados.gov.br. The IBGE note says IBGE brought the CNEFE
release forward because of the floods in Rio Grande do Sul in May 2024, to support emergency response.

| | |
|---|---|
| Source | `35_SP.zip`, 1,082,015,432 bytes, Last-Modified 20 May 2024 |
| Rows read | 22,953,725 (one per species at an address) |
| Distinct addresses | 22,647,398 |
| Duplicate rows skipped | 306,327 |
| Left out: `SN` (no number) | 1,651,253 |
| Left out: coordinate level 4, 5 or 6 (face of block, locality, census tract) | 109,508 |
| **Addresses written** | **20,886,637** |
| File | 2,869,927,936 bytes (2.87 GB), about 137 bytes per address |
| Build time | 821 s (13.7 min), on the same Windows machine |
| Peak memory | 1.94 GB |

Coordinate levels in the file: 1 original census point 20,317,716; 2 point moved for apartments at one number
2,272,608; 3 estimated point 253,221; 4 face of block 107,395; 5 locality 687; 6 census tract 2,098. Levels 1 to 3 are
kept.

What the rows look like: every row has a postcode (8 digits), a street type (`RUA`, `AVENIDA`, `ESTRADA`, ...), and
municipality codes for all 645 municipalities. The street names have no accents and are in capitals.

### Queries against this index

Run on the main engine, with real rows and typed variants. "Match" means the lookup returns the address.

| Query | Match | Note |
|---|---|---|
| `41 Rua Salvador Filardi` | yes (4 rows, several cities) | the same name exists in several municipalities |
| `41 RUA SALVADOR FILARDI` | yes | case does not matter |
| `41 Salvador Filardi` | no | the street type is part of the stored name |
| `Rua Salvador Filardi, 41` | no | not an address query: the number must come first |
| `41 R. Salvador Filardi` | no | 6.6 s, see below |
| `1215 Avenida Doutor Frederico Martins Da Costa Carvalho` | yes | |
| `1215 Av. Doutor Frederico Martins Da Costa Carvalho` | no | `av` is not mapped to `avenida` for Portuguese |
| `1578 Avenida Paulista` | yes | |
| `1578 Av. Paulista` | no | as above |
| `1578 Avenida Paulísta` | no | an accent in the query never matches |
| `4500 Avenida Morumbi` | yes | CEP 04703-002 in the record |
| `4500 Av. Morumbi`, `4500 Morumbi`, `Avenida Morumbi, 4500` | no | |
| `4500 Avenida Morumbi, São Paulo` | yes | the city after the street is read |
| `15 Viaduto do Chá` | no | not in this index |
| `SN Rua ...`, `0 Rua ...` | no | `SN` rows are not in the index; `0` finds nothing here |
| `01311-000`, `01311000` | no | a postcode alone goes to the place finder, not the address lookup |

Most lookups take 3 to 15 ms. The slow cases are short street prefixes: `41 R. Salvador Filardi` took 6.6 s, because the
prefix `r` matches a large part of the index. `0 Rua Pedro Alvares Cabral` took 4.2 s.

The public example, `4500 Avenida Morumbi`, is a number in the census register. Whether it is the state government
palace (Palácio dos Bandeirantes) is general knowledge and was not checked: the postcode in the census (04703-002)
differs from the one the OpenStreetMap index gave for the same street number (05650-905).

### What the search engine on `main` would need (for #386 and #31)

These are not changed in this step; the list is for the shared runtime work.

1. Match without the street type, or add the bare name as an alias in the index.
2. Map Portuguese abbreviations on both sides: `Av`, `Av.` to `avenida`; `Dr.`, `R.` to `rua`.
3. Fold accents on both the query and the stored name. Today `normalize()` turns an accent into a space, so a typed accent never matches.
4. Refuse or bound very short street prefixes: one-letter prefixes scan most of a large index (6.6 s here).
5. The `SN` rows (1,651,253) need a "no number" result type. The lookup must never present them as a house number.
6. The result's source is written as "Overture Maps" for every index. It should read `meta.source` of the index.
7. Read `meta.norm` to choose the rule for each index (#79, #386), instead of the one shared `normalize()`.
