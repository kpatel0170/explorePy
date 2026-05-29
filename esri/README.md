# esri — ArcGIS Enterprise utility toolkit

Reusable Python utilities for ArcGIS Enterprise built on the **ArcGIS API for Python** (`arcgis`), `pandas` + the Spatially Enabled DataFrame (SDF), `geopandas`, and `arcpy`.

## Layout

```
esri/
├── esri_utils/
│   ├── config.py       # env-driven Portal connection config
│   ├── portal.py       # connect; item / user / web map inventory & admin
│   ├── layers.py       # FeatureLayer query → SDF, publish, edits, schema
│   ├── cleaning.py     # pandas / SDF cleaning (snake_case, types, nulls, dedupe)
│   ├── analysis.py     # merges, spatial join (sjoin), buffer, dissolve, SDF↔GDF
│   ├── geocode.py      # forward / reverse / batch geocoding + suggest
│   ├── network.py      # route, service area, closest facility, OD cost matrix
│   ├── geometry.py     # server-side geometry ops (project, buffer, simplify, hull)
│   ├── admin.py        # ArcGIS Server admin: services, logs, data stores, machines
│   ├── export.py       # print web maps (PDF/PNG), extract data, create service defs
│   ├── geoenrich.py    # GeoEnrichment: demographic & landscape data enrichment
│   ├── arcpy_db.py     # arcpy gdb / SDE ops (inventory, fields, load, maintenance)
│   ├── arcpy_aprx.py   # arcpy .aprx ops (repair sources, symbology, export layouts)
│   ├── viz.py          # choropleth, categorical, overlay maps
│   └── address_recon.py# Optius → CAR/AM address reconciliation
├── apps/
│   └── streamlit_app.py    # quick UI: query a layer, inspect, map
├── examples/
│   └── quickstart.py
└── pyproject.toml       # uv-managed deps
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

### Portal inventory + feature layer query

```python
from esri_utils.portal import connect, search_items
from esri_utils import layers, cleaning, analysis, viz

gis = connect()
items = search_items(gis, item_type="Feature Service")
layer = layers.get_feature_layer(gis, items.iloc[0]["id"])
sdf = layers.query_to_sdf(layer, where="STATE='CA'", chunk_size=2000)
sdf = cleaning.trim_strings(cleaning.standardize_columns(sdf))
gdf = analysis.to_geodataframe(sdf)
viz.choropleth(gdf, "population")
```

### Geocode addresses

```python
from esri_utils.geocode import geocode, reverse_geocode, batch_geocode

# forward
result = geocode(gis, "123 Main St, Springfield, IL")
# reverse
addr = reverse_geocode(gis, (-77.04, 38.91))
# batch from DataFrame
results = batch_geocode(gis, df, "address_column")
```

### Network analysis

```python
from esri_utils.network import find_routes, generate_service_areas

routes = find_routes(gis, stops_sdf, travel_mode="Driving Time")
# extract result layer as DataFrame
from esri_utils.network import extract_result_layer
routes_df = extract_result_layer(routes, "routes")

service_areas = generate_service_areas(gis, facilities_sdf, break_values=[5, 10, 15])
```

### Server-side geometry

```python
from esri_utils.geometry import project, buffer_geometries, areas_and_lengths

projected = project(gis, geoms, in_sr=4326, out_sr=3857)
buffered = buffer_geometries(gis, projected, distance=100, unit="meters")
```

### Administer services

```python
from esri_utils.admin import list_services, start_service, query_logs, list_machines

services = list_services(gis)
start_service(gis, "MyService", "MapServer")
logs = query_logs(gis, levels="SEVERE")
machines = list_machines(gis)
```

### Export web maps

```python
from esri_utils.export import export_web_map, get_print_templates

templates = get_print_templates(gis)
export_web_map(gis, web_map_id="abc123", fmt="PDF", out_path="output.pdf")
```

### GeoEnrichment

```python
from esri_utils.geoenrich import enrich_study_areas, standard_geography_query

counties = standard_geography_query(gis, "US", "USA.County", geoquery="San Diego*")
enriched = enrich_study_areas(gis, counties, variables=["TOTPOP_CY", "MEDHINC_CY"])
```

### arcpy database maintenance (inside ArcGIS Pro)

```python
from esri_utils import arcpy_db
arcpy_db.list_datasets(r"C:\connections\prod.sde")
arcpy_db.compress_and_rebuild(r"C:\connections\prod.sde")
```

### Repair broken project data sources

```python
from esri_utils import arcpy_aprx
arcpy_aprx.repair_broken_sources("CURRENT", old_workspace=r"D:\old.gdb", new_workspace=r"D:\new.gdb")
arcpy_aprx.export_layouts("CURRENT", out_dir="exports", fmt="PDF")
```

### Quick UI

```bash
streamlit run esri/apps/streamlit_app.py
```
