---
name: arcgis-workflows
description: "esri_utils recipes: connect, query layers->SDF, clean, analyze (geopandas), geocode, network, publish, admin on ArcGIS Enterprise."
---

# ArcGIS workflows (esri_utils)

Use when working in the `esri/` toolkit: connecting to ArcGIS Enterprise/Online,
moving feature layers into Spatially Enabled DataFrames (SDF), cleaning/analyzing,
geocoding, network analysis, publishing, or server admin. Read `esri/AGENTS.md`
for hard rules (lazy imports, `_core`, SDF vs GeoDataFrame, arcgis 2.4).

## Connect

```python
from esri_utils.portal import connect
gis = connect()   # env-driven: ARCGIS_URL + api_key/token/profile/PKI/user+pwd
```
Auth priority: profile > api_key > token > PKI > user+pwd. Only URL = anonymous.

## Query -> clean -> analyze -> visualize

```python
from esri_utils import layers, cleaning, analysis, viz
lyr = layers.get_feature_layer(gis, "item_id")             # or layers.layer_from_url(url, gis)
sdf = layers.query_to_sdf(lyr, where="STATE='CA'", chunk_size=2000)  # paged
sdf = cleaning.trim_strings(cleaning.standardize_columns(sdf))
cleaning.null_report(sdf)                                   # data-quality snapshot
gdf = analysis.to_geodataframe(sdf)                         # -> geopandas
counts = analysis.aggregate_by_polygon(points_gdf, polys_gdf, agg="count")
ax = viz.choropleth(gdf, "pop"); viz.save_figure(ax, "map.png")
```

## SDF helpers (arcgis engine)

```python
from esri_utils.sdf import from_xy, from_layer, sjoin, buffer, centroid
sdf = from_xy(df, x_column="lon", y_column="lat")
joined = sjoin(points_sdf, polys_sdf, how="left", op="within")
```
SDF ops (`sdf.buffer`/`sdf.sjoin`) use the arcgis engine; `analysis.buffer`/
`analysis.spatial_join` use geopandas/shapely. Convert via `analysis.to_geodataframe`
/ `analysis.to_sdf` (both delegate to `esri_utils._core`).

## Geocode

```python
from esri_utils.geocode import geocode, batch_geocode, reverse_geocode, geocode_dataframe
geocode(gis, "123 Main St")
out = geocode_dataframe(gis, df, "address")   # appends geocode_x/y/score/match_addr
```

## Network

```python
from esri_utils.network import find_routes, generate_service_areas, extract_result_layer
res = find_routes(gis, stops_sdf, travel_mode="Driving Time")
directions = extract_result_layer(res, "directions")
```

## Publish

```python
from esri_utils.layers import sdf_to_layer, append_features
item = sdf_to_layer(sdf, gis, title="My Layer")
append_features(existing_layer, more_sdf)
```

## Admin

```python
from esri_utils.admin import list_services, start_service, query_logs
list_services(gis); query_logs(gis, levels="SEVERE")
```

## Fire-threat clouds (Saskatchewan)

```python
from esri_utils.fire import fire_threat_analysis
clouds = fire_threat_analysis(day_range=7)   # nested FIRE_AREA polygons by age class
```
NASA FIRMS (MODIS/VIIRS/NOAA) + CWFIS active fires -> SK filter + false-positive
drop -> data-driven buffer -> dissolve -> smooth/shrink. One cloud per age class,
**distinct and drawn new-over-old** by default (recent = small/saturated on top,
old = large/pale background; use `draw_order`/`fill_color`/`fill_alpha` to style;
`nested=True` for concentric zones). Needs `FIRMS_MAP_KEY` for satellite data
(runs on CWFIS alone otherwise). Tune via `conf_min`, `min_km`/`max_km`,
`smooth_km`/`shrink_km`, `min_points`. CLI: `esri fire`.

## CLI (no script needed)

```bash
esri connect-test
esri search --type "Feature Service" --owner planning_dept
esri query <item-id> --where "STATE='CA'" --out ca.csv
esri geocode "123 Main St"
# or, no install:  python -m esri_utils <command>
```

## Gotchas

- `arcpy_db` / `arcpy_aprx` only run inside ArcGIS Pro/Server conda env.
- `address_recon` needs `uv sync --extra addr` (rapidfuzz, usaddress).
- Web maps/printing use `arcgis.map.Map` (2.4+), not the removed `arcgis.mapping.WebMap`.
- Heavy deps are lazy-imported; `import esri_utils` works without arcgis installed.
