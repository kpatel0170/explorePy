---
name: arcgis-python-api
description: "Deep reference for the ArcGIS API for Python (arcgis>=2.4.3) SDK: GIS auth modes, content CRUD, feature layer queries and edits, Spatially Enabled DataFrames, web maps and scenes, geocoding, network analysis, publishing workflows, printing/exports, server admin. Use this skill when the task involves arcgis SDK internals — raw `arcgis` object manipulation, layer schema inspection, content item properties, web map JSON, role/permission management, or any operation that reaches below the `esri_utils` helper layer. Also use when troubleshooting arcgis SDK version quirks, import errors, or API changes between arcgis 2.x versions."
---

# ArcGIS API for Python

Use for raw `arcgis` SDK work in `esri/`. This skill covers SDK internals not
abstracted by `esri_utils` helpers. Read `esri/AGENTS.md` first, then the
specific module being touched.

## Hard rules

1. **Lazy-import `arcgis`** — never import at module top level. `import arcgis` or
   `from arcgis.gis import GIS` inside the function body.
2. **Target `arcgis>=2.4.3`** — `arcgis.mapping.WebMap` was removed in 2.4.
   Use `arcgis.map.Map`. Feature layer queries changed in 2.3; `.query()` kwarg
   names match 2.4+.
3. **Always accept a live `gis` object** in service functions. No hidden global
   auth. No module-level `gis = connect()`.
4. **Return DataFrame/SDF** where the output is tabular. Keep raw SDK objects
   only when the caller needs SDK methods (e.g. `Layer`, `Item`, `Group`).
5. **Never log tokens, API keys, secrets, or full env dumps** — even in debug
   output. Use `python -m esri_utils doctor` for safe diagnostics.

## Auth

```python
from arcgis.gis import GIS
from esri_utils.config import PortalConfig

# From env (standard)
cfg = PortalConfig.from_env()
gis = GIS(**cfg.as_gis_kwargs())

# Direct (for testing)
gis = GIS("https://myserver.esri.com/portal", username="user", password="pass")

# Anonymous
gis = GIS("https://www.arcgis.com")
```

Auth priority in `connect()`: **profile > api_key > token > PKI > user+pwd > anonymous**.

## Content CRUD

```python
# Search
items = gis.content.search("forest", item_type="Feature Service",
                           max_items=100, owner="planning")
for item in items:
    print(item.id, item.title, item.type, item.modified)

# Get by ID
item = gis.content.get("item_id_here")

# Create
item = gis.content.add(item_properties={
    "title": "My Layer",
    "type": "Feature Service",
    "tags": "analysis, temp",
}, data=None)                            # or data=path_to_sd_file

# Update
item.update(item_properties={"title": "Renamed"})
item.update(data=new_data_path)

# Delete
item.delete()
```

### Item properties — common fields
- `item.id`, `item.title`, `item.type`, `item.tags`
- `item.owner`, `item.created`, `item.modified`, `item.size`
- `item.url` — REST endpoint for services
- `item.description`, `item.snippet` — for rich metadata
- `item.extent` — dict `{"xmin", "ymin", "xmax", "ymax", "spatialReference"}`

### Sharing
```python
item.share(everyone=True)                # public
item.share(org=True)                     # organization
item.share(groups=[group1, group2])      # specific groups
```

## Feature layers

```python
# From item
item = gis.content.get("layer_item_id")
lyr = item.layers[0]                     # or item.tables[0]

# From URL (no item lookup)
from arcgis.features import FeatureLayer
lyr = FeatureLayer("https://server/rest/services/Folder/Service/FeatureServer/0")

# Query — always set out_fields to avoid pulling all columns
sdf = lyr.query(where="1=1",
                out_fields="NAME,POP,STATE,SHAPE",
                return_geometry=True,
                return_centroid=False).sdf

# Paged query for large datasets
page = 0
while True:
    sdf_chunk = lyr.query(where="1=1",
                          out_fields="NAME,SHAPE",
                          result_offset=page * 2000,
                          result_record_count=2000).sdf
    if len(sdf_chunk) == 0:
        break
    # process chunk...
    page += 1

# Edits
add_result = lyr.edit_features(adds=[new_feature_1, new_feature_2])
update_result = lyr.edit_features(updates=[modified_feature])
delete_result = lyr.edit_features(deletes=[object_id_1, object_id_2])
```

## Spatially Enabled DataFrame

```python
# Create from xy
sdf = df.spatial.from_xy(df, x_column="lon", y_column="lat")

# From featureset (layer query result)
fs = lyr.query()
sdf = fs.sdf

# Geometry column is always named "SHAPE" — use GEOM_COL constant
from esri_utils._core import GEOM_COL

# Spatial operations
sdf.spatial.project(3857)                               # reproject
sdf_spatial_join = sdf.spatial.join(another_sdf, "contains")
sdf_buffered = sdf.spatial.buffer(100)                  # arcgis engine
```

## Web maps

```python
from arcgis.map import Map

# Create map
webmap = Map(gis, basemap="dark-gray")

# Add layers
webmap.add_layer(lyr)
webmap.add_layer(another_lyr)

# Export/print
from arcgis.mapping import export_map
# (not arcgis.mapping.WebMap — removed in 2.4)
```

## Geocoding

```python
from arcgis.geocoding import geocode, reverse_geocode, batch_geocode, suggest

result = geocode(gis, "123 Main St, Regina, SK")
addr = reverse_geocode(gis, 50.4, -104.6)
```

## Network analysis

```python
from arcgis.network import solve_routes, generate_service_areas, closest_facility

result = solve_routes(gis, stops_sdf, travel_mode="Driving Time")
```

## Publishing

```python
from arcgis.features import FeatureLayerCollection

# Analyze SDF for publishing
from arcgis.features.manage import analyze_features_for_publish
analysis = analyze_features_for_publish(gis, sdf)

# Create service definition (.sd file)
from arcgis.features.manage import create_service_definition
sd_file = create_service_definition(gis, analysis, "My Service Definition")
```

## Server admin

```python
# Service management
server = gis.admin.server
services = server.services.list(folder="Hosted")
server.services.start("MyService.MapServer")
server.services.stop("MyService.MapServer")

# Logs
logs = server.logs.query(start_time="-24h", levels="SEVERE")

# Data stores
datastores = server.datastores.list()
```

## Version gotchas

| Version | Breaking change |
|---------|----------------|
| <2.3 | Old `FeatureLayer.query(where, out_fields, ...)` kwargs differ |
| 2.3 | `GIS()` constructor no longer accepts positional args for `username`/`password` — use keyword args |
| 2.4 | `arcgis.mapping.WebMap` removed — use `arcgis.map.Map` |
| 2.4 | `arcgis.mapping.export_map` signature changed |
| 2.4 | pandas pinned `<4`, numpy pinned `<3` in pyproject caps |

## Diagnostics before deep debugging

```bash
cd esri
python -m esri_utils doctor            # env check (no Portal needed)
python -m esri_utils doctor --connect  # full auth test
```

## Acceptance

Run against real ArcGIS Enterprise/Online with `ARCGIS_URL` + configured auth.
Test: `gis = connect()`, query a known layer, inspect item properties.
