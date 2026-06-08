---
name: arcpy-workflows
description: "ArcGIS Pro/Server arcpy operations: file geodatabase (GDB) and SDE inventory, schema inspection, field calculations, data loading, APRX project repair, map layer management, symbology updates, layout export, and spatial ETL. Use this skill when the task involves arcpy — geodatabase paths, APRX files, SDE connections, enterprise GDB (SQL Server/Oracle/PostgreSQL via SDE), feature class/table listing, field mapping, data conversion between GDB and SDF, or layout-to-PDF/PNG export. Also use whenever the user mentions ArcGIS Pro, arcpy, .gdb, .sde, .aprx, or .lyrx files. This skill only works inside an ArcGIS Pro/Server conda Python environment — arcpy is not pip-installable."
---

# arcpy workflows

Use for `arcpy_db.py`, `arcpy_aprx.py`, file geodatabases, SDE, ArcGIS Pro
projects, map layers, symbology, and layout export. These modules only run
inside ArcGIS Pro/Server Python conda environments — arcpy is **not**
pip/uv-installable.

## Hard rules

1. **arcpy is conda-only** — never add `arcpy` to `pyproject.toml` or any
   pip/uv requirements. It comes from ArcGIS Pro/Server's conda env.
2. **Lazy-import through `_arcpy()` helper** — always inside arcpy-only modules.
   Never `import arcpy` at module top level.
3. **Keep modules importable outside Pro** — `import esri_utils.arcpy_db`
   must succeed. Only fail when an actual arcpy function is called.
4. **Explicit paths + workspace restore** — never change `arcpy.env.workspace`
   without a try/finally to restore it.
5. **No accidental destruction** — never delete/overwrite GDBs, SDE data,
   APRX files, or layouts without explicit user instruction and confirmation.
6. **Releases cursors** — always wrap `arcpy.da.SearchCursor`/`InsertCursor`/
   `UpdateCursor` in `with` blocks.

## Pattern

```python
def _arcpy():
    import arcpy
    return arcpy


def list_feature_classes(workspace: str):
    arcpy = _arcpy()
    old = arcpy.env.workspace
    try:
        arcpy.env.workspace = workspace
        return arcpy.ListFeatureClasses() or []
    finally:
        arcpy.env.workspace = old
```

## Common patterns

### GDB/SDE inventory

```python
def _arcpy():
    import arcpy
    return arcpy

def inventory_gdb(workspace: str):
    arcpy = _arcpy()
    old = arcpy.env.workspace
    try:
        arcpy.env.workspace = workspace
        return {
            "feature_classes": arcpy.ListFeatureClasses() or [],
            "tables": arcpy.ListTables() or [],
            "datasets": arcpy.ListDatasets() or [],
            "domains": arcpy.ListDomains() or [],
            "workspace_type": arcpy.Describe(workspace).workspaceType,  # "FileSystem" | "LocalDatabase" | "RemoteDatabase"
        }
    finally:
        arcpy.env.workspace = old
```

### Field operations

```python
def list_fields(fc: str):
    arcpy = _arcpy()
    return [
        {"name": f.name, "type": f.type, "length": f.length,
         "nullable": f.isNullable, "domain": f.domain}
        for f in arcpy.ListFields(fc)
    ]

def add_field(fc: str, field_name: str, field_type: str, **kwargs):
    arcpy = _arcpy()
    arcpy.AddField_management(fc, field_name, field_type, **kwargs)

def calculate_field(fc: str, field: str, expression: str, code_block: str = None):
    arcpy = _arcpy()
    arcpy.CalculateField_management(fc, field, expression, code_block=code_block)
```

### Feature class to SDF (bridge to esri_utils)

```python
def fc_to_sdf(fc: str, fields: list[str] = None):
    """Return arcgis Spatially Enabled DataFrame from a GDB feature class.
    Only callable inside ArcGIS Pro — arcpy + arcgis must both be importable."""
    import arcpy  # noqa: F811 — reimport for export
    from arcgis.features import GeoAccessor, GeoSeriesAccessor  # register .spatial
    if fields:
        return arcpy.da.SearchCursor(fc, fields + ["SHAPE@"])
    return arcpy.da.SearchCursor(fc, ["*", "SHAPE@"])
```

### APRX manipulation

```python
def _arcpy():
    import arcpy
    return arcpy

def repair_sources(aprx_path: str, old_path: str, new_path: str):
    arcpy = _arcpy()
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.supports("CONNECTIONPROPERTIES"):
                props = lyr.connectionProperties
                # walk props and replace old_path -> new_path
                lyr.updateConnectionProperties(old_path, new_path)
    aprx.save()

def export_layout(aprx_path: str, layout_name: str, output_path: str, resolution: int = 300):
    arcpy = _arcpy()
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    layout = aprx.listLayouts(layout_name)[0]
    layout.exportToPDF(output_path, resolution=resolution)
```

### Symbology

```python
def apply_symbology(target_layer: str, source_layer: str):
    arcpy = _arcpy()
    arcpy.ApplySymbologyFromLayer_management(target_layer, source_layer)
```

## Cursor patterns

```python
def _arcpy():
    import arcpy
    return arcpy

# Search — always with block for release
def search(fc: str, fields: list[str], where: str = None):
    arcpy = _arcpy()
    with arcpy.da.SearchCursor(fc, fields, where_clause=where) as cursor:
        for row in cursor:
            yield dict(zip(fields, row))

# Update
def update(fc: str, updates: list[dict], key_field: str):
    arcpy = _arcpy()
    fields = [key_field] + list(updates[0].keys())
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            for u in updates:
                if row[0] == u[key_field]:
                    for k, v in u.items():
                        row[fields.index(k)] = v
                    cursor.updateRow(row)
                    break

# Insert
def insert(fc: str, rows: list[dict]):
    arcpy = _arcpy()
    fields = list(rows[0].keys())
    with arcpy.da.InsertCursor(fc, fields) as cursor:
        for row in rows:
            cursor.insertRow([row[f] for f in fields])
```

## Environment management

```python
def _arcpy():
    import arcpy
    return arcpy

def with_env(**overrides):
    """Decorator/context: set arcpy.env temporarily."""
    arcpy = _arcpy()
    class EnvContext:
        def __enter__(self):
            self.old = {k: getattr(arcpy.env, k, None) for k in overrides}
            for k, v in overrides.items():
                setattr(arcpy.env, k, v)
            return self
        def __exit__(self, *args):
            for k, v in self.old.items():
                setattr(arcpy.env, k, v)
    return EnvContext()

# Usage
def clip_fc(in_fc, clip_fc, out_fc):
    arcpy = _arcpy()
    with with_env(workspace=os.path.dirname(out_fc), overwriteOutput=True):
        arcpy.Clip_analysis(in_fc, clip_fc, out_fc)
```

## Known errors & fixes

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `ImportError: No module named arcpy` | Not in Pro/Server conda env | Switch to ArcGIS Pro Python env |
| `NameError: name 'describe' is not assigned` | `arcpy.Describe` typo | Use `arcpy.Describe()` |
| `RuntimeError: ERROR 000728` | Field already exists | Check `arcpy.ListFields()` first |
| `RuntimeError: Object: Error in executing geoprocessing` | Path or env issue | Check workspace, path separators, SDE connection |
| `RuntimeError: ERROR 000732` | Dataset does not exist | Verify path with `arcpy.Exists()` |
| `Not signed in as a user with a license` | ArcGIS Pro not licensed | Check Pro license level |

## Verification (without ArcGIS Pro)

```bash
cd esri
python -m compileall esri_utils    # syntax check (no arcpy needed)
ruff check .                        # lint (no arcpy needed)
```

Runtime acceptance: the user must run arcpy paths inside ArcGIS Pro/Server Python.
