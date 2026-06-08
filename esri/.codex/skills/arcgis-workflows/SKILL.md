---
name: arcgis-workflows
description: "ArcGIS/esri_utils coding: connect, doctor, query layers, SDF/GDF, clean, analyze, publish, admin."
---

# ArcGIS workflows

Use for edits in `esri/`. Read `esri/AGENTS.md` first.

Use companion skills when the task narrows:
- `arcgis-python-api`: SDK auth/content/layer/map/publish patterns.
- `arcpy-workflows`: ArcGIS Pro/Server Python, geodatabases, SDE, APRX.
- `sdf-pandas-geopandas`: SDF, pandas cleaning, GeoDataFrame analysis.
- `enterprise-portal-workflows`: Enterprise auth, admin, migration, publish.
- `esri-project-init`: new module/project setup.
- `esri-utils-best-practices`: simplify/consolidate helper design.

Hard rules:
- Lazy-import `arcgis`, `arcpy`, `geopandas`, `shapely` inside functions.
- Use `_core.GEOM_COL` and `_core` conversion helpers; never redefine `SHAPE`.
- Target ArcGIS API for Python 2.4+ (`arcgis.map.Map`, not `arcgis.mapping.WebMap`).
- Keep functions small; files under ~500 LOC.

Useful flow:

```bash
cd esri
python -m esri_utils doctor
python -m esri_utils --help
python -m compileall esri_utils
ruff check .
ruff format --check .
```

Runtime flow:

```python
from esri_utils.portal import connect
from esri_utils import layers, cleaning, analysis

gis = connect()
lyr = layers.get_feature_layer(gis, "item_id")
sdf = layers.query_to_sdf(lyr, where="1=1", chunk_size=2000)
sdf = cleaning.trim_strings(cleaning.standardize_columns(sdf))
gdf = analysis.to_geodataframe(sdf)
```

Use `esri doctor --connect` only when live Portal auth/network is expected.
