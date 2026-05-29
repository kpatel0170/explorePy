# esri — ArcGIS Enterprise utility toolkit

Reusable Python utilities for ArcGIS Enterprise built on the **ArcGIS API for Python** (`arcgis`), `pandas` + the Spatially Enabled DataFrame (SDF), `geopandas`, and `arcpy`.

## Layout

```
esri/
├── esri_utils/
│   ├── config.py      # env-driven Portal connection config
│   ├── portal.py      # connect; item / user / web map inventory & admin
│   ├── layers.py      # FeatureLayer query → SDF, publish, edits, schema
│   ├── cleaning.py    # pandas / SDF cleaning (snake_case, types, nulls, dedupe)
│   ├── analysis.py    # merges, spatial join (sjoin), buffer, dissolve, SDF↔GDF
│   ├── arcpy_db.py    # arcpy gdb / SDE ops (inventory, fields, load, maintenance)
│   └── arcpy_aprx.py  # arcpy .aprx ops (repair sources, symbology, export layouts)
├── apps/
│   └── streamlit_app.py   # quick UI: query a layer, inspect, map
├── examples/
│   └── quickstart.py
└── pyproject.toml      # uv-managed deps
```

## Setup

```bash
cd esri
uv sync                       # core deps: arcgis, geopandas, streamlit, …
uv sync --extra addr          # + address-reconciliation deps (rapidfuzz, usaddress)
export ARCGIS_URL=https://gis.example.com/portal
export ARCGIS_USER=me
export ARCGIS_PASSWORD=…                       # or: export ARCGIS_PROFILE=my_profile
```

> `arcpy` is **not** pip-installable — `arcpy_db.py` and `arcpy_aprx.py` run only
> inside an ArcGIS Pro / Server conda environment. The other modules run anywhere.

## Quick examples

```python
from esri_utils.portal import connect, search_items
from esri_utils import layers, cleaning, analysis, viz

gis = connect()                                   # env-var auth
items = search_items(gis, item_type="Feature Service")

layer = layers.get_feature_layer(gis, items.iloc[0]["id"])
sdf   = layers.query_to_sdf(layer, where="STATE='CA'", chunk_size=2000)

sdf   = cleaning.trim_strings(cleaning.standardize_columns(sdf))
gdf   = analysis.to_geodataframe(sdf)
viz.choropleth(gdf, "population")
```

Spatial join + summarize:

```python
counts = analysis.aggregate_by_polygon(points_gdf, tracts_gdf, agg="count")
```

arcpy database maintenance (inside Pro):

```python
from esri_utils import arcpy_db
arcpy_db.list_datasets(r"C:\\connections\\prod.sde")
arcpy_db.compress_and_rebuild(r"C:\\connections\\prod.sde")
```

Repair broken project data sources:

```python
from esri_utils import arcpy_aprx
arcpy_aprx.repair_broken_sources("CURRENT", old_workspace=r"D:\\old.gdb", new_workspace=r"D:\\new.gdb")
arcpy_aprx.export_layouts("CURRENT", out_dir="exports", fmt="PDF")
```

Quick UI:

```bash
streamlit run esri/apps/streamlit_app.py
```
```
