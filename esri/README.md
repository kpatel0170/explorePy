# esri — ArcGIS Enterprise toolkit

```
layers       FeatureLayer → SDF, publish, edits, attachments
sdf          Spatially Enabled DataFrame: from_xy, sjoin, buffer, export, plot
cleaning     snake_case, coerce types, trim strings, dedupe, null report
analysis     SDF↔GDF, merge, sjoin, buffer, dissolve, polygon aggregate
geocode      forward / reverse / batch geocode + suggest
network      route, service area, closest facility, OD cost matrix, loc-allocation
geometry     server-side project, buffer, simplify, hull, relation, coord convert
admin        ArcGIS Server services, logs, data stores, machines
export       print web map (PDF/PNG), extract data, create service def
geoenrich    enrich study areas, standard geo query, reports
arcpy_db     gdb/SDE ops (arcpy-only)
arcpy_aprx   .aprx repair sources, symbology, export layouts (arcpy-only)
viz          choropleth, categorical, overlay maps
address_recon Optius → CAR/AM address match
```

## Auth

| Mode | Env vars | `GIS()` param |
|------|----------|---------------|
| API key | `ARCGIS_API_KEY` | `api_key=...` |
| User/pwd | `ARCGIS_USER` + `ARCGIS_PASSWORD` | `username=..., password=...` |
| Token | `ARCGIS_TOKEN` | `token=...` |
| Profile | `ARCGIS_PROFILE` | `profile=...` |
| PKI | `ARCGIS_CERT_FILE` [+ `ARCGIS_KEY_FILE`] | `cert_file=..., key_file=...` |

Always set `ARCGIS_URL`. Auth auto-detected by priority.

```bash
cd esri && uv sync
```

## Cheatsheet

```python
from esri_utils.portal import connect
gis = connect()                              # auto-detect auth from env

# --- layers ---
from esri_utils.layers import get_feature_layer, query_to_sdf, field_summary
lyr = get_feature_layer(gis, "item_id")
sdf = query_to_sdf(lyr, where="STATE='CA'", chunk_size=2000)
field_summary(lyr)

# --- sdf ---
from esri_utils.sdf import from_xy, from_layer, sjoin, buffer, centroid
sdf = from_xy(df, x_column="lon", y_column="lat")  # CSV → SDF
sdf = from_layer(lyr)                               # FeatureLayer → SDF
joined = sjoin(points_sdf, polygons_sdf, how="left", op="within")
buffered = buffer(sdf, distance=500)

# --- cleaning ---
from esri_utils.cleaning import standardize_columns, trim_strings, null_report
sdf = trim_strings(standardize_columns(sdf))
null_report(sdf)

# --- analysis ---
from esri_utils.analysis import to_geodataframe, dissolve, aggregate_by_polygon
gdf = to_geodataframe(sdf)
dissolved = dissolve(gdf, by="district")
counts = aggregate_by_polygon(points_gdf, polygons_gdf, agg="count")

# --- geocode ---
from esri_utils.geocode import geocode, batch_geocode, reverse_geocode
geocode(gis, "123 Main St")
batch_geocode(gis, df["address"])
reverse_geocode(gis, (-77.04, 38.91))

# --- network ---
from esri_utils.network import find_routes, generate_service_areas
routes = find_routes(gis, stops_sdf, travel_mode="Driving Time")
service_areas = generate_service_areas(gis, fac_sdf, break_values=[5, 10])

# --- geometry ---
from esri_utils.geometry import project, buffer_geometries, areas_and_lengths
project(gis, geoms, in_sr=4326, out_sr=3857)
buffer_geometries(gis, geoms, distance=100, unit="meters")

# --- admin ---
from esri_utils.admin import list_services, start_service, query_logs
list_services(gis)
query_logs(gis, levels="SEVERE")

# --- export ---
from esri_utils.export import export_web_map, get_print_templates
export_web_map(gis, web_map_id="abc123", fmt="PDF", out_path="out.pdf")

# --- geoenrich ---
from esri_utils.geoenrich import enrich_study_areas, standard_geography_query
enrich_study_areas(gis, sdf, variables=["TOTPOP_CY"])
standard_geography_query(gis, "US", "USA.County", geoquery="San Diego*")
```

> `arcpy_db`/`arcpy_aprx` require ArcGIS Pro env. `address_recon` needs `uv sync --extra addr`.

```bash
streamlit run esri/apps/streamlit_app.py     # quick UI explorer
```
