# AGENTS.md — esri toolkit

Domain guide for humans + coding agents working in `esri/`. Read before editing.

## What this is

`esri_utils` — function-first toolkit over the **ArcGIS API for Python** (`arcgis`)
for ArcGIS Enterprise / Online work. Every function takes a live
`arcgis.gis.GIS` and returns a pandas DataFrame / Spatially Enabled DataFrame
(SDF) where it makes sense, so results compose and stay inspectable.

## Hard rules

- **Lazy imports.** Never import `arcgis` / `arcpy` / `geopandas` / `shapely` at
  module top level. Import inside the function that needs it. This keeps
  `import esri_utils` working on machines missing the heavy deps (docs, linting,
  CI). Top-level imports are limited to stdlib + `pandas` + `._core`.
- **One geometry constant.** Use `from ._core import GEOM_COL` — do not redefine
  `"SHAPE"`. Same for `register_spatial`, `validate_sdf`, `to_geodataframe`,
  `to_sdf`, `to_featureset`.
- **arcgis 2.4.3+ on Python 3.11–3.14.** `arcgis.mapping.WebMap` was removed in
  2.4 — use `arcgis.map.Map`. If you touch web maps / web scenes / printing,
  target the 2.4 API (`arcgis.map`, `arcgis.layers`). arcgis pins pandas (`<4`)
  and numpy (`<3`); don't fight those caps. Pairs with geopandas 1.x / shapely 2.1.
- **arcpy is conda-only.** `arcpy_db` / `arcpy_aprx` run only inside an ArcGIS Pro
  / Server Python env; arcpy is not pip/uv-installable. Guard arcpy behind a
  lazy `_arcpy()` helper.
- **Keep files < ~500 LOC**, functions small, public API stable.

## Mental model: SDF vs GeoDataFrame

- **SDF** (Spatially Enabled DataFrame) = a pandas DataFrame with a `SHAPE`
  column and a `.spatial` accessor (from `arcgis`). Native to Portal I/O,
  publishing, network/geoenrich solvers.
- **GeoDataFrame** (geopandas) = the open-source spatial stack (shapely engine).
  Use for heavy local analysis (dissolve, overlay, projection-aware buffer).
- Convert with `_core.to_geodataframe(sdf)` / `_core.to_sdf(gdf)`.
- Two buffer/join pairs exist on purpose — different engines, not duplicates:
  - `sdf.buffer` / `sdf.sjoin` → arcgis geometry engine, operate on SDFs.
  - `analysis.buffer` / `analysis.spatial_join` → geopandas/shapely, operate on GDFs.

## Auth (config.py / portal.connect)

Env-driven, priority order: **profile > api_key > token > PKI (cert+key) > user+pwd**.
Always set `ARCGIS_URL`. `connect()` auto-detects; only-URL = anonymous.
Never commit credentials; `.env` is gitignored.

## Module map

```
_core    GEOM_COL, register_spatial, validate_sdf, SDF<->GDF, to_featureset
config   PortalConfig.from_env / as_gis_kwargs (auth)
portal   connect, search_items, list_users, get_webmap_layers, clone/reassign
layers   FeatureLayer query->SDF (paging), edits, attachments, field_summary
sdf      SDF construction/ops/export/plot (arcgis engine)
cleaning snake_case, coerce/trim, dedupe, null_report (SHAPE-safe)
analysis geopandas: SDF<->GDF, merge, sjoin, buffer, dissolve, aggregate
geocode  forward/reverse/batch/suggest + geocode_dataframe
network  route, service area, closest facility, OD matrix, loc-allocation
geometry server-side project/buffer/simplify/hull/relation/coord convert
admin    services start/stop, logs, data stores, machines
export   print web map (arcgis.map.Map), extract data, create service def
geoenrich enrich study areas, standard geography query, reports
viz      geopandas + matplotlib choropleth/categorical/overlay
fire     SK fire-threat: FIRMS+CWFIS -> buffer/dissolve/smooth FIRE_AREA by age ($FIRMS_MAP_KEY)
arcpy_db gdb/SDE inventory, fields, calc, load (arcpy-only)
arcpy_aprx .aprx repair sources, symbology, export layouts (arcpy-only)
address_recon Optius -> CAR/AM address match (needs --extra addr)
cli      argparse CLI (connect-test/search/services/query/geocode)
```

## Adding a module

1. Module docstring: purpose + a short usage block.
2. `from __future__ import annotations`; top imports = stdlib + pandas + `._core`.
3. Each public function: takes `gis` (if it hits a service), lazy-imports arcgis,
   returns a DataFrame/SDF when sensible, has a docstring with a `>>>` example.
4. Register the module in `esri_utils/__init__.py` `__all__` + docstring.
5. Add a row to `README.md` and the module map above.
6. If it adds a useful one-liner, add a CLI subcommand in `cli.py`.

## Verify before handoff

```bash
cd esri
ruff check . && ruff format --check .
python -m compileall esri_utils       # syntax (no arcgis needed)
python -m esri_utils --help           # CLI wiring
```

Runtime checks (need arcgis 2.4 + a live Portal): `esri connect-test`,
`esri query <id> --out out.csv`, web-map helpers in `portal`/`export`.
