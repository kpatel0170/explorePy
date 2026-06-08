---
name: arcpy-workflows
description: "arcpy workflows: ArcGIS Pro/Server conda, geodatabases, SDE, APRX, layouts, safe lazy imports."
---

# arcpy workflows

Use for `arcpy_db.py`, `arcpy_aprx.py`, file geodatabases, SDE, ArcGIS Pro
projects, map layers, symbology, and layout export.

Rules:
- `arcpy` is conda-only; never add it to `pyproject.toml`.
- Lazy-import through an `_arcpy()` helper inside arcpy-only modules.
- Keep arcpy modules importable outside ArcGIS Pro by failing only when a public
  arcpy function is called.
- Prefer explicit paths and workspaces; avoid changing global env state unless
  restored.
- Do not delete/overwrite geodatabases, SDE data, APRX files, or layouts without
  explicit user instruction.

Pattern:

```python
def _arcpy():
    import arcpy

    return arcpy


def list_feature_classes(workspace: str):
    arcpy = _arcpy()
    old_workspace = arcpy.env.workspace
    try:
        arcpy.env.workspace = workspace
        return arcpy.ListFeatureClasses() or []
    finally:
        arcpy.env.workspace = old_workspace
```

Verify without ArcGIS Pro:

```bash
cd esri
python -m compileall esri_utils
ruff check .
```

Runtime acceptance: user runs arcpy paths inside ArcGIS Pro/Server Python.
