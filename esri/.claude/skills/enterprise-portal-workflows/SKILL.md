---
name: enterprise-portal-workflows
description: "ArcGIS Enterprise Portal workflows: auth, content search, admin, migration, publish, diagnostics."
---

# Enterprise Portal workflows

Use for ArcGIS Enterprise/Online auth, content inventory, feature service query,
admin service checks, item migration, ownership, publishing, and acceptance.

Auth:
- Always rely on `ARCGIS_*` env vars or explicit `PortalConfig`.
- Priority: profile > api_key > token > PKI > user/password > anonymous.
- Run `esri doctor` before deeper debugging.
- Use `esri doctor --connect` only when live auth/network is expected.

Common flow:

```python
from esri_utils.portal import connect, search_items, list_users
from esri_utils.admin import list_services, query_logs

gis = connect()
content = search_items(gis, item_type="Feature Service", max_items=100)
users = list_users(gis)
services = list_services(gis)
logs = query_logs(gis, levels="SEVERE")
```

Migration/publish:
- Prefer clone/reassign helpers for Portal item movement.
- Keep source and destination GIS objects explicit.
- Make destructive actions visible: folder, owner, item id, title.
- For publish flows, dry-run first when practical; print item id + URL.

Acceptance:
- `python -m esri_utils doctor --connect`
- Query a small known layer.
- Publish to a scratch folder/item title.
- Confirm item owner, sharing, layer count, and URL.
