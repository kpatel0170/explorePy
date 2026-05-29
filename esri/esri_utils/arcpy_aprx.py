"""arcpy ArcGIS Pro project (.aprx) operations.

Programmatic edits to Pro projects: inventory maps & layers, repair broken
data sources, toggle/symbolize layers, and batch-export layouts to PDF/PNG.

Requires arcpy (ArcGIS Pro). Use 'CURRENT' as the path when running inside
the Pro Python window to target the open project.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _arcpy():
    import arcpy  # noqa: WPS433

    return arcpy


def open_project(aprx_path: str = "CURRENT"):
    """Open an .aprx ('CURRENT' = the project open in Pro)."""
    return _arcpy().mp.ArcGISProject(aprx_path)


def list_maps_layers(aprx_path: str = "CURRENT") -> pd.DataFrame:
    """Inventory every layer across every map in the project."""
    aprx = open_project(aprx_path)
    rows: list[dict[str, Any]] = []
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            conn = None
            if lyr.supports("DATASOURCE"):
                try:
                    conn = lyr.dataSource
                except Exception:
                    conn = None
            rows.append(
                {
                    "map": m.name,
                    "layer": lyr.name,
                    "is_broken": lyr.isBroken,
                    "visible": getattr(lyr, "visible", None),
                    "is_group": lyr.isGroupLayer,
                    "data_source": conn,
                }
            )
    return pd.DataFrame(rows)


def repair_broken_sources(aprx_path: str, old_workspace: str, new_workspace: str, save: bool = True) -> int:
    """Repoint broken layers from old workspace path to a new one.

    Returns the count of layers/tables repaired. Common after moving a gdb
    or migrating file gdb -> SDE.
    """
    aprx = open_project(aprx_path)
    repaired = 0
    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isBroken and lyr.supports("DATASOURCE"):
                lyr.updateConnectionProperties(old_workspace, new_workspace)
                repaired += 1
        for tbl in m.listTables():
            if tbl.isBroken:
                tbl.updateConnectionProperties(old_workspace, new_workspace)
                repaired += 1
    if save:
        aprx.save()
    del aprx
    return repaired


def set_layer_visibility(aprx_path: str, map_name: str, visibility: dict[str, bool], save: bool = True):
    """Toggle layer visibility by {layer_name: bool}."""
    aprx = open_project(aprx_path)
    m = aprx.listMaps(map_name)[0]
    for lyr in m.listLayers():
        if lyr.name in visibility:
            lyr.visible = visibility[lyr.name]
    if save:
        aprx.save()
    del aprx


def apply_symbology(aprx_path: str, map_name: str, layer_name: str, lyrx_path: str, save: bool = True):
    """Apply a saved .lyrx symbology to a layer."""
    arcpy = _arcpy()
    aprx = open_project(aprx_path)
    m = aprx.listMaps(map_name)[0]
    target = m.listLayers(layer_name)[0]
    arcpy.management.ApplySymbologyFromLayer(target, lyrx_path)
    if save:
        aprx.save()
    del aprx


def export_layouts(aprx_path: str, out_dir: str, fmt: str = "PDF", resolution: int = 300) -> list[str]:
    """Batch-export all layouts to PDF or PNG. Returns written file paths."""
    import os

    aprx = open_project(aprx_path)
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for layout in aprx.listLayouts():
        safe = layout.name.replace(" ", "_")
        if fmt.upper() == "PDF":
            path = os.path.join(out_dir, f"{safe}.pdf")
            layout.exportToPDF(path, resolution=resolution)
        else:
            path = os.path.join(out_dir, f"{safe}.png")
            layout.exportToPNG(path, resolution=resolution)
        written.append(path)
    del aprx
    return written
