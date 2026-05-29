# esri — ArcGIS Enterprise utility toolkit

Reusable Python utilities for ArcGIS Enterprise built on the **ArcGIS API for Python** (`arcgis`), `pandas` + the Spatially Enabled DataFrame (SDF), `geopandas`, and `arcpy`.

## Layout

```
esri/
├── esri_utils/
│   ├── config.py       # env-driven Portal connection (supports API key / token / PKI / pwd)
│   ├── portal.py       # connect; item / user / web map inventory & admin
│   ├── layers.py       # FeatureLayer query → SDF, publish, edits, schema, attachments
│   ├── sdf.py          # Spatially Enabled DataFrame: from_xy, from_layer, sjoin, buffer, plot, export
│   ├── cleaning.py     # pandas / SDF cleaning (snake_case, types, nulls, dedupe)
│   ├── analysis.py     # merges, spatial join (sjoin), buffer, dissolve, SDF↔GDF
│   ├── geocode.py      # forward / reverse / batch geocoding + suggest
│   ├── network.py      # route, service area, closest facility, OD cost matrix, loc-allocation
│   ├── geometry.py     # server-side geometry ops (project, buffer, simplify, hull, relation)
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

### Auth via env vars (any of these)

```bash
# --- 1) API key (Enterprise 11.4+ / AGOL) ---
export ARCGIS_URL=https://gis.example.com/portal
export ARCGIS_API_KEY=APKSoJdwxBgSA0RiOZg7zJVVqlOG-...

# --- 2) Username + password ---
export ARCGIS_URL=https://gis.example.com/portal
export ARCGIS_USER=me
export ARCGIS_PASSWORD=secret

# --- 3) Token ---
export ARCGIS_URL=https://gis.example.com/portal
export ARCGIS_TOKEN=3G_e-FSoJdwxBgSA0RiOZ...

# --- 4) Profile (stored on disk) ---
export ARCGIS_PROFILE=my_profile

# --- 5) PKI ---
export ARCGIS_URL=https://gis.example.com/portal
export ARCGIS_CERT_FILE=/path/to/cert.pfx
export ARCGIS_KEY_FILE=/path/to/key.pem
export ARCGIS_PASSWORD=pfx_password
```

```bash
cd esri
uv sync                       # core deps: arcgis, geopandas, streamlit, …
uv sync --extra addr          # + address-reconciliation deps (rapidfuzz, usaddress)
```

> `arcpy` is **not** pip-installable — `arcpy_db.py` and `arcpy_aprx.py` run only
> inside an ArcGIS Pro / Server conda environment. The other modules run anywhere.

## Quick examples

### Connect (auto-detects auth method from env)

```python
from esri_utils.portal import connect
gis = connect()
print("Connected as:", gis.properties.user.username)
```

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

### Spatially Enabled DataFrame (SeDF) construction

```python
from esri_utils.sdf import from_xy, from_layer, from_geodataframe

# From lat/lon columns
sdf = from_xy(csv_df, x_column="longitude", y_column="latitude", sr=4326)

# From a FeatureLayer
sdf = from_layer(layer, where="CITY = 'Springfield'")

# From a GeoDataFrame
gdf = geopandas.read_file("parcels.shp")
sdf = from_geodataframe(gdf)
```

### SeDF operations

```python
from esri_utils.sdf import buffer, centroid, sjoin, to_featurelayer

buffered = buffer(sdf, distance=500)
centroids = centroid(sdf)

# spatial join: points -> polygons
joined = sjoin(points_sdf, polygons_sdf, how="left", op="within")

# publish
item = to_featurelayer(joined, "enriched_points", gis=gis)
```

### Geocode addresses

```python
from esri_utils.geocode import geocode, reverse_geocode, batch_geocode

result = geocode(gis, "123 Main St, Springfield, IL")
addr = reverse_geocode(gis, (-77.04, 38.91))
results = batch_geocode(gis, df["address_column"])
```

### Network analysis

```python
from esri_utils.network import find_routes, generate_service_areas
from esri_utils.network import extract_result_layer

routes = find_routes(gis, stops_sdf, travel_mode="Driving Time")
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
