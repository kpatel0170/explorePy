"""arcpy database-focused operations.

Runs ONLY inside an ArcGIS Pro / Server conda env (arcpy is not pip-installable).
Targets file geodatabases and enterprise (SDE) geodatabases: inventory,
schema edits, field calc, and bulk loads.

Every function imports arcpy lazily so the module can be imported (e.g. for
docs/linting) on machines without arcpy.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _arcpy():
    import arcpy  # noqa: WPS433 (lazy import by design)

    return arcpy


def list_datasets(workspace: str) -> pd.DataFrame:
    """Inventory feature classes & tables in a gdb / SDE workspace."""
    arcpy = _arcpy()
    arcpy.env.workspace = workspace

    rows: list[dict[str, Any]] = []
    for fc in arcpy.ListFeatureClasses() or []:
        desc = arcpy.Describe(fc)
        rows.append(
            {
                "name": fc,
                "kind": "FeatureClass",
                "shape_type": getattr(desc, "shapeType", None),
                "spatial_ref": getattr(getattr(desc, "spatialReference", None), "name", None),
                "count": int(arcpy.management.GetCount(fc)[0]),
            }
        )
    for tbl in arcpy.ListTables() or []:
        rows.append(
            {
                "name": tbl,
                "kind": "Table",
                "shape_type": None,
                "spatial_ref": None,
                "count": int(arcpy.management.GetCount(tbl)[0]),
            }
        )
    return pd.DataFrame(rows)


def describe_fields(dataset: str) -> pd.DataFrame:
    """Return the schema (fields) of a feature class or table."""
    arcpy = _arcpy()
    rows = [
        {
            "name": f.name,
            "alias": f.aliasName,
            "type": f.type,
            "length": f.length,
            "nullable": f.isNullable,
            "editable": f.editable,
        }
        for f in arcpy.ListFields(dataset)
    ]
    return pd.DataFrame(rows)


def add_field(dataset: str, name: str, field_type: str = "TEXT", **kwargs) -> str:
    """Add a field. field_type: TEXT|SHORT|LONG|FLOAT|DOUBLE|DATE|BLOB."""
    arcpy = _arcpy()
    arcpy.management.AddField(dataset, name, field_type, **kwargs)
    return name


def calculate_field(dataset: str, field: str, expression: str, expression_type: str = "PYTHON3"):
    """Field calculator (e.g. expression='!POP! / !AREA!')."""
    arcpy = _arcpy()
    return arcpy.management.CalculateField(dataset, field, expression, expression_type)


def table_to_dataframe(dataset: str, fields: list[str] | None = None, where: str = "") -> pd.DataFrame:
    """Read a feature class / table into a pandas DataFrame via a cursor."""
    arcpy = _arcpy()
    if fields is None:
        fields = [f.name for f in arcpy.ListFields(dataset) if f.type != "Geometry"]
    with arcpy.da.SearchCursor(dataset, fields, where_clause=where) as cur:
        data = [list(row) for row in cur]
    return pd.DataFrame(data, columns=fields)


def dataframe_to_table(df: pd.DataFrame, out_table: str) -> str:
    """Write a (non-spatial) DataFrame to a gdb table via numpy structured array."""
    arcpy = _arcpy()
    import numpy as np

    arr = np.rec.fromrecords(df.to_records(index=False), names=list(df.columns))
    arcpy.da.NumPyArrayToTable(arr, out_table)
    return out_table


def copy_dataset(src: str, dest: str) -> str:
    """Copy a feature class/table (e.g. SDE -> file gdb staging)."""
    arcpy = _arcpy()
    arcpy.management.Copy(src, dest)
    return dest


def compress_and_rebuild(sde_workspace: str) -> None:
    """Enterprise gdb maintenance: compress + rebuild indexes + analyze."""
    arcpy = _arcpy()
    arcpy.management.Compress(sde_workspace)
    datasets = list_datasets(sde_workspace)["name"].tolist()
    for ds in datasets:
        try:
            arcpy.management.RebuildIndexes(sde_workspace, "NO_SYSTEM", ds, "ALL")
            arcpy.management.AnalyzeDatasets(sde_workspace, "NO_SYSTEM", ds, "ANALYZE_BASE")
        except Exception:  # pragma: no cover - continue maintenance on failure
            continue
