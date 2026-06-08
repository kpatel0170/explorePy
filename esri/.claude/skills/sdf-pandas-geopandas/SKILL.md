---
name: sdf-pandas-geopandas
description: "SDF, pandas, GeoDataFrame workflows: clean, convert, join, buffer, dissolve, publish."
---

# SDF / pandas / geopandas

Use for Spatially Enabled DataFrames, pandas cleaning, GeoDataFrame conversion,
local spatial analysis, and publish-ready outputs.

Mental model:
- SDF: pandas DataFrame + `SHAPE` + `.spatial`; native for Portal I/O.
- pandas: tabular cleaning, schema coercion, null reports, joins.
- GeoDataFrame: shapely/geopandas engine for local overlay, dissolve, buffers.

Rules:
- Use `from esri_utils._core import GEOM_COL`; never redefine `"SHAPE"`.
- Use `_core.to_geodataframe()` / `_core.to_sdf()` for conversions.
- Lazy-import `geopandas` and `shapely` inside functions.
- Preserve geometry in tabular operations; drop/ignore `SHAPE` only deliberately.
- Reproject before distance/area/buffer work; never buffer in raw EPSG:4326.

Flow:

```python
from esri_utils import cleaning, analysis

sdf = cleaning.trim_strings(cleaning.standardize_columns(sdf))
quality = cleaning.null_report(sdf)
gdf = analysis.to_geodataframe(sdf)
gdf = gdf.to_crs(3857)
buffered = analysis.buffer(gdf, distance=500)
out_sdf = analysis.to_sdf(buffered)
```

Choose engine:
- Use `esri_utils.sdf` for ArcGIS engine SDF joins/buffers.
- Use `esri_utils.analysis` for geopandas/shapely local analysis.
- Use `layers.sdf_to_layer()` only after schema/geometry are checked.
