---
name: arcgis-python-api
description: "ArcGIS API for Python workflows: GIS auth, content, layers, maps, geocode, network, publish."
---

# ArcGIS API for Python

Use for `arcgis` SDK work in `esri/`: Portal auth, content search, feature
layers, SDF, web maps, geocoding, network analysis, publishing, exports.

Read first: `esri/AGENTS.md`, then the module being touched.

Rules:
- Lazy-import `arcgis` inside functions.
- Target `arcgis>=2.4.3`; use `arcgis.map.Map`, not `arcgis.mapping.WebMap`.
- Accept a live `gis` object in service functions; avoid hidden global auth.
- Return DataFrame/SDF where useful; keep raw SDK objects only when the caller
  needs SDK methods.
- Never log tokens, API keys, usernames/passwords, or full env dumps.

Core flow:

```python
from esri_utils.portal import connect, search_items
from esri_utils.layers import get_feature_layer, query_to_sdf, sdf_to_layer

gis = connect()
items = search_items(gis, item_type="Feature Service", owner="planning")
lyr = get_feature_layer(gis, "item_id")
sdf = query_to_sdf(lyr, where="1=1", chunk_size=2000)
item = sdf_to_layer(sdf, gis, title="Clean layer")
```

Before debugging auth/deps:

```bash
cd esri
python -m esri_utils doctor
python -m esri_utils doctor --connect
```

Acceptance for live workflows: run against real ArcGIS Enterprise/Online with
`ARCGIS_URL` and one auth mode configured.
