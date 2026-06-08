---
name: arcgis-workflows
description: "esri_utils end-to-end recipes for ArcGIS Enterprise/Online: Portal connect, feature-layer query->SDF, pandas cleaning, geopandas analysis, geocoding, network analysis, publishing, server admin. Use this skill whenever the user asks to work with ArcGIS data, query feature layers, run spatial analysis, clean/inspect dataframes, geocode addresses, compute routes/service areas, publish layers, administer ArcGIS Server, or run the `esri` CLI. This is the primary entry point — load this skill first before narrowing to companion skills."
---

# ArcGIS workflows (esri_utils)

Use when working in the `esri/` toolkit. This is the master workflow skill.
Read `esri/AGENTS.md` for hard rules (lazy imports, `_core`, SDF vs GeoDataFrame, arcgis 2.4).

## Before starting

```bash
cd esri
python -m esri_utils doctor           # env + dependency check (no Portal needed)
python -m esri_utils doctor --connect  # full auth + reachability test
python -m esri_utils --help            # CLI available subcommands
```

## Companion skills — load when the task narrows

- `arcgis-python-api`: SDK patterns — auth, content CRUD, layer ops, web maps, geocoding, network solvers, publishing.
- `arcpy-workflows`: ArcGIS Pro/Server-only paths — file GDB, SDE, APRX repair, layout export (conda env required).
- `sdf-pandas-geopandas`: Data analysis — SDF join/buffer (arcgis engine), pandas cleaning/null-inspection, GeoDataFrame overlay/dissolve/projection-aware ops (geopandas engine).
- `enterprise-portal-workflows`: Portal/Online admin — auth flows, content inventory, item migration, service admin, security.
- `esri-project-init`: Module/project scaffolding — new module checklist, pyproject.toml setup, docstring conventions.
- `esri-utils-best-practices`: Code review — lazy-import audit, engine-selection checks, CLI ergonomics, dry-run patterns.

## Connect

```python
from esri_utils.portal import connect
gis = connect()   # env-driven: ARCGIS_URL + api_key/token/profile/PKI/user+pwd
```

Auth priority: **profile > api_key > token > PKI > user+pwd**. Only URL = anonymous.
`connect()` reads `PortalConfig.from_env`. Never commit credentials — `.env` is gitignored.

### Common auth errors
- `ARCGIS_URL` not set → `ConfigurationError: ARCGIS_URL required`.
- No auth method resolves → `ConfigurationError: no auth method available` — set one of `ARCGIS_PROFILE`, `ARCGIS_API_KEY`, `ARCGIS_TOKEN`, `ARCGIS_CLIENT_CERT`+`KEY`, or `ARCGIS_USERNAME`+`PASSWORD`.
- SSL/cert issues on Enterprise → set `ARCGIS_VERIFY_SSL=false` (dev only) or point `REQUESTS_CA_BUNDLE` to internal CA.

## Query → clean → analyze → visualize

```python
from esri_utils import layers, cleaning, analysis, viz

# 1. Get data
lyr = layers.get_feature_layer(gis, "item_id")          # by item ID
lyr = layers.layer_from_url(url, gis)                    # by REST URL

# 2. Query with paging (handles >2000 features)
sdf = layers.query_to_sdf(lyr, where="STATE='CA'", chunk_size=2000,
                          out_fields="NAME,POP,STATE,SHAPE", spatial_rel="esriSpatialRelEnvelope")

# 3. Clean
sdf = cleaning.trim_strings(sdf)                         # strip whitespace on string cols
sdf = cleaning.standardize_columns(sdf)                  # snake_case, lowercase
quality = cleaning.null_report(sdf)                      # DataFrame: col, null_count, null_pct, dtype

# 4. Analyze
gdf = analysis.to_geodataframe(sdf)                      # SDF -> GeoDataFrame (shapely engine)
gdf = gdf.to_crs(3857)                                   # reproject before distance/buffer
counts = analysis.aggregate_by_polygon(points_gdf, polys_gdf, agg="count")

# 5. Visualize
ax = viz.choropleth(gdf, "pop", title="Population by region")
viz.save_figure(ax, "map.png")
```

## SDF helpers (arcgis engine)

```python
from esri_utils.sdf import from_xy, from_layer, sjoin, buffer, centroid, to_shapely

# Create SDF from xy coords
sdf = from_xy(df, x_column="lon", y_column="lat")        # auto SR WGS84
sdf = from_xy(df, x_column="easting", y_column="northing", sr=26910)  # explicit SR

# Spatial join (arcgis engine — runs on server/SDE)
joined = sjoin(points_sdf, polys_sdf, how="left", op="within")

# Buffer
buffered = buffer(sdf, distance=100, unit="meters")

# Geometry access
shape_wkt = to_shapely(sdf)                              # extract WKT for shapely consumption
```

**Engine choice**: SDF ops use the arcgis geometry engine (server-side for SDE layers).
GeoDataFrame ops (`analysis.buffer`, `analysis.spatial_join`) use geopandas/shapely (local).
Convert between them via `_core.to_geodataframe` / `_core.to_sdf`.

## Geocode

```python
from esri_utils.geocode import geocode, batch_geocode, reverse_geocode, geocode_dataframe, suggest

# Single address
result = geocode(gis, "123 Main St, Regina, SK")

# Batch a DataFrame column
out = geocode_dataframe(gis, df, "address")              # appends: geocode_x, geocode_y, geocode_score, geocode_match_addr

# Reverse geocode
addr = reverse_geocode(gis, 50.4, -104.6)

# Autocomplete
candidates = suggest(gis, "123 Main")
```

**Gotchas**: `geocode_dataframe` rate-limits internally — OK for <10k rows. For larger datasets, batch by chunk or use `esri_utils` CLI.

## Network

```python
from esri_utils.network import (find_routes, generate_service_areas,
                                closest_facility, extract_result_layer)

# Route
res = find_routes(gis, stops_sdf, travel_mode="Driving Time")
route_layer = extract_result_layer(res, "routes")
directions = extract_result_layer(res, "directions")      # turn-by-turn text

# Service area
sa = generate_service_areas(gis, facilities_sdf, break_values=[5, 10, 15],
                            travel_mode="Driving Time", overlap="dissolve")

# Closest facility
cf = closest_facility(gis, incidents_sdf, facilities_sdf,
                       default_cutoff=30, num_facilities=5)
```

**Gotchas**: Network solvers need a network dataset published as a routing service.
Travel modes: `"Driving Time"`, `"Driving Distance"`, `"Walking Time"`, `"Trucking Time"`.
Check available modes via `gis._con.post(route_url + "/suggestTravelModes")`.

## Publish

```python
from esri_utils.layers import sdf_to_layer, append_features, overwrite_layer

# Publish SDF as new feature service
item = sdf_to_layer(sdf, gis, title="My Layer",
                    folder="scratch", tags=["temp", "analysis"])

# Append data to existing layer
append_features(existing_layer, more_sdf)

# Overwrite (schema must match)
overwrite_layer(existing_layer, replacement_sdf)
```

**Dry-run pattern** — always confirm before publish:
```python
print(f"Would publish to folder='{folder}', title='{title}'")
print(f"Schema: {list(sdf.columns)} ({len(sdf)} rows)")
item = sdf_to_layer(sdf, gis, title=title)  # only after user confirms
```

## Admin

```python
from esri_utils.admin import list_services, start_service, stop_service, query_logs

services = list_services(gis)
start_service(gis, "MyService.MapServer")
stop_service(gis, "MyService.MapServer")
logs = query_logs(gis, levels="SEVERE", start_time="-24h")
```

**Gotchas**: Admin ops need Portal administrator or Publisher role.
`query_logs` only returns server-side logs. Portal audit logs need separate access.

## Fire-threat clouds (Saskatchewan)

```python
from esri_utils.fire import fire_threat_analysis

# 7-day fire threat, distinct age-class clouds
clouds = fire_threat_analysis(day_range=7)

# All age classes in one nested geometry
clouds = fire_threat_analysis(day_range=14, nested=True)
```

NASA FIRMS (MODIS/VIIRS/NOAA) + CWFIS active fires → SK filter + false-positive
drop → data-driven buffer → dissolve → smooth/shrink. One cloud per age class,
**distinct and drawn new-over-old** by default (recent = small/saturated on top,
old = large/pale background; use `draw_order`/`fill_color`/`fill_alpha` to style;
`nested=True` for concentric zones). Needs `FIRMS_MAP_KEY` env var for satellite data
(runs on CWFIS alone otherwise). Tune via `conf_min`, `min_km`/`max_km`,
`smooth_km`/`shrink_km`, `min_points`. CLI: `esri fire`.

## CLI reference

```bash
esri connect-test                  # verify Portal auth
esri doctor                        # env + dependency check
esri doctor --connect              # include live auth test
esri search --type "Feature Service"
esri query <item-id> --where "STATE='CA'" --out ca.csv
esri geocode "123 Main St"
esri services --folder Hosted
esri fire                          # fire-threat clouds
# No install:  python -m esri_utils <command>
```

## Gotchas & pitfalls

1. **arcpy is conda-only** — `arcpy_db` / `arcpy_aprx` fail outside ArcGIS Pro/Server Python env. Guard with `_arcpy()` lazy helper.
2. **address_recon** needs `uv sync --extra addr` (brings rapidfuzz, usaddress).
3. **Web maps** use `arcgis.map.Map` (2.4+). `arcgis.mapping.WebMap` removed in 2.4 — do not import.
4. **Lazy imports** — `arcgis`, `arcpy`, `geopandas`, `shapely` are never imported at module top level. Only import inside the function that needs them. `import esri_utils` must work without heavy deps installed.
5. **Geometry column** — always use `from esri_utils._core import GEOM_COL`. Never hardcode `"SHAPE"` or redefine the constant.
6. **CRS** — Never buffer/distance-compute in raw EPSG:4326. Always reproject to a projected CRS first (e.g. EPSG:3857 or local UTM zone).
7. **Chunking** — `query_to_sdf` with `chunk_size=2000` handles large layers. Without chunking, queries >2000 features are silently truncated by the ArcGIS REST API.
8. **Rate limits** — Portal/Online impose rate limits on geocoding, publishing, and admin ops. Batch work should pace requests.

## Acceptance

```bash
cd esri
ruff check . && ruff format --check .
python -m compileall esri_utils
python -m esri_utils doctor
python -m esri_utils doctor --connect   # requires live Portal
esri query <known-item-id> --out /tmp/test.csv
```
