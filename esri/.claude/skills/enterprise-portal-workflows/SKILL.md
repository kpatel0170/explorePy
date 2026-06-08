---
name: enterprise-portal-workflows
description: "ArcGIS Enterprise Portal / ArcGIS Online operations: authentication configuration, content inventory and search, feature service CRUD, user/role management, service administration (start/stop/logs), item migration and cloning, publishing workflows, security and sharing, diagnostics and acceptance testing. Use this skill when the task involves Portal administration — connecting to Enterprise or AGOL, managing users/groups, searching inventory, cloning items between environments, monitoring server logs, configuring auth, or verifying Portal health. Also use whenever the user mentions Portal, AGOL, Enterprise, admin, content migration, item ownership, or sharing permissions."
---

# Enterprise Portal workflows

Use for ArcGIS Enterprise/Online auth, content inventory, feature service query,
admin service checks, item migration, ownership, publishing, and acceptance.

## Auth

Auth is env-driven. Priority: **profile > api_key > token > PKI > user/password > anonymous**.

```bash
# Required
export ARCGIS_URL="https://myserver.esri.com/portal"   # or https://www.arcgis.com

# Pick one auth method:
export ARCGIS_PROFILE="myprofile"                       # from arcgis profiles (~/.arcgis)
export ARCGIS_API_KEY="..."                              # API key (recommended for AGOL)
export ARCGIS_TOKEN="..."                                # pre-generated token
export ARCGIS_CLIENT_CERT="/path/to/cert.pem"            # PKI client cert
export ARCGIS_CLIENT_KEY="/path/to/key.pem"              # PKI key
export ARCGIS_USERNAME="user"
export ARCGIS_PASSWORD="pass"                             # env var only — never in code
```

**Best practices**:
- Prefer `api_key` for AGOL, `profile` or `PKI` for Enterprise.
- Never hardcode credentials. `.env` is gitignored — use it for local dev.
- For PKI auth, both `ARCGIS_CLIENT_CERT` and `ARCGIS_CLIENT_KEY` must be set.
- Use `esri doctor` first to validate env config without hitting the network.

```python
from esri_utils.config import PortalConfig
from esri_utils.portal import connect

cfg = PortalConfig.from_env()         # reads ARCGIS_* env vars
print(f"URL={cfg.url}, auth={cfg.auth_method}")
gis = connect()
```

## Content inventory

```python
from esri_utils.portal import search_items, list_users, list_groups

# Search — supports ArcGIS REST API search syntax
items = search_items(gis, item_type="Feature Service", owner="planning",
                     max_items=100, sort="modified", sort_order="desc")

# Get by ID
item = gis.content.get("item_id_here")

# List users
users = list_users(gis)               # returns list of user dicts
admins = [u for u in users if "admin" in (u.get("role") or "")]

# Groups
groups = list_groups(gis)
```

### Common search queries

| Search | Description |
|--------|-------------|
| `search_items(gis, item_type="Feature Service")` | All feature services |
| `search_items(gis, item_type="Web Map")` | Web maps |
| `search_items(gis, owner="planning")` | By owner |
| `search_items(gis, tags="forestry")` | By tag |
| `search_items(gis, type="csv")` | CSV files |
| `search_items(gis, typekeywords="[published]")` | Recently published |

## Feature service admin

```python
from esri_utils.layers import get_feature_layer, query_to_sdf, field_summary

# Inspect layer
lyr = get_feature_layer(gis, "item_id")
print(lyr.properties)                 # full JSON properties
summary = field_summary(lyr)          # per-field type, length, nullable, domain

# Query
sdf = query_to_sdf(lyr, where="1=1", chunk_size=2000)

# Check extent
extent = lyr.properties.extent
print(f"{extent.xmin}, {extent.ymin} to {extent.xmax}, {extent.ymax}")
```

## Server admin

```python
from esri_utils.admin import list_services, start_service, stop_service, query_logs

# List services
services = list_services(gis, folder="Hosted")
for svc in services:
    print(f"{svc['serviceName']}.{svc['type']} — {svc['status']}")

# Start/stop
start_service(gis, "MyService.MapServer")
stop_service(gis, "MyService.MapServer")

# Logs
logs = query_logs(gis, levels="SEVERE", start_time="-24h", end_time="now")
# Returns list of log entries with machine, service, message, timestamp
```

## Item migration

```python
from esri_utils.portal import clone_item, reassign_item

# Clone item between portals (or within the same portal)
new_item = clone_item(gis, "source_item_id",
                      target_gis=dst_gis,              # same or different portal
                      folder="migration",
                      title="Cloned Layer (Jan 2026)")

# Reassign ownership
reassign_item(gis, "item_id", new_owner="planner2")

# Copy between folders
item = gis.content.get("item_id")
item.move(folder="archive")
```

**Migration checklist**:
- [ ] Source and destination GIS objects are explicit (not same object reused).
- [ ] Item IDs, titles, and folders are printed before destructive actions.
- [ ] Sharing settings are re-applied after clone.
- [ ] For feature services, confirm layer count and schema match.
- [ ] For web maps, confirm layer references resolve in the new portal.

## Publishing

```python
from esri_utils.layers import sdf_to_layer
from esri_utils.export import print_web_map

# Dry-run pattern
print(f"Would publish: {len(sdf)} rows, folder=scratch")
print(f"Schema: {list(sdf.columns)}")
# item = sdf_to_layer(sdf, gis, title="Dry Run Layer")  # only after confirmation

# Actual publish
item = sdf_to_layer(sdf, gis, title="My Layer",
                    folder="scratch", tags=["analysis"])

# Print web map
webmap_data = print_web_map(gis, map_id="webmap_item_id",
                             format="PDF", layout="A3 Landscape")
```

## Security & sharing

```python
# Sharing
item.share(everyone=True)             # public
item.share(org=True)                  # entire organization
item.share(groups=[group])            # specific group

# Item permissions
item.update(item_properties={"access": "public"})   # AGOL only
item.update(item_properties={"access": "org"})      # org only

# User role management
users = gis.users.search(query="role: org_user")
admins = [u for u in users if u.role == "org_admin"]
```

## Diagnostics & acceptance

```bash
# Quick health check
python -m esri_utils doctor --connect

# Full acceptance
esri connect-test
esri query <known-item-id> --out /tmp/acceptance.csv
python -c "
from esri_utils.portal import connect
gis = connect()
print(gis.properties.portalName, gis.properties.portalHostname)
"
```

### Acceptance checklist
- [ ] `esri doctor` passes (env check).
- [ ] `esri doctor --connect` passes (live auth).
- [ ] Can query a known layer.
- [ ] Can list services.
- [ ] Can search content by owner/type/tags.
- [ ] Can publish to a scratch folder.
- [ ] Confirm item owner, sharing, layer count, URL after publish.

## Known issues

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| `gis = connect()` hangs | HTTPS cert or proxy | Set `REQUESTS_CA_BUNDLE` or `ARCGIS_VERIFY_SSL=false` (dev only) |
| `TokenExpired` | Long-running session | Reconnect: `gis = connect()` refreshes from env |
| `404: Not Found` on layer query | Item ID wrong or layer index off | Check item layers: `gis.content.get(id).layers` |
| `Permission denied` | Insufficient role | Check `list_users(gis)` role — needs Publisher minimum |
| `QuotaExceeded` | AGOL credit cap | Check AGOL subscription or switch to Enterprise |
