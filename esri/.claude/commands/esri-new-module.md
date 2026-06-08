---
description: Scaffold a new esri_utils module following toolkit conventions.
argument-hint: <module_name> "<one-line purpose>"
---

Create a new module `esri/esri_utils/$1` for the esri toolkit.

First read `esri/AGENTS.md` and one existing module of similar shape (e.g.
`geocode.py` for service wrappers, `cleaning.py` for pure-pandas, `arcpy_db.py`
for arcpy-only) to match the established style.

Requirements (enforce all):
- `from __future__ import annotations` at the top.
- Top-level imports limited to stdlib + `pandas` + `from ._core import ...`.
  Import `arcgis` / `arcpy` / `geopandas` / `shapely` **lazily inside functions**.
- Use `from ._core import GEOM_COL` (and `register_spatial` / `validate_sdf` /
  `to_geodataframe` / `to_sdf` / `to_featureset` as needed) — never redefine them.
- Module docstring: purpose + a short usage block.
- Each public function: takes a live `gis` if it hits a service, returns a
  DataFrame / SDF when sensible, has a docstring with a `>>>` example.
- Target the arcgis 2.4+ API (`arcgis.map` / `arcgis.layers`, not `arcgis.mapping`).
- Keep the file under ~500 LOC.

Then wire it in:
1. Add the module to `esri_utils/__init__.py` (`__all__` + the docstring list).
2. Add a row to `esri/README.md`'s module table and `AGENTS.md`'s module map.
3. If it offers a useful one-liner, add a subcommand to `esri_utils/cli.py`.

Finally verify: `cd esri && ruff check . && ruff format . && python -m compileall esri_utils`.

Purpose of the new module: $2
