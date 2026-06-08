"""Spatial & tabular analysis: merges, spatial joins, geopandas ops.

Bridges the ArcGIS SDF world and geopandas. ``to_geodataframe`` converts an
SDF so you can use the full geopandas/shapely toolset, then ``to_sdf`` brings
results back for publishing to Enterprise.
"""

from __future__ import annotations

import pandas as pd

# SDF<->GDF conversion + the geometry column constant live in _core so the
# whole package shares one implementation. Re-exported here for back-compat:
# ``from esri_utils.analysis import to_geodataframe`` keeps working.
from ._core import GEOM_COL, to_geodataframe, to_sdf

__all__ = [
    "GEOM_COL",
    "to_geodataframe",
    "to_sdf",
    "tabular_merge",
    "spatial_join",
    "aggregate_by_polygon",
    "buffer",
    "dissolve",
]


def tabular_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str],
    how: str = "left",
    validate: str | None = None,
) -> pd.DataFrame:
    """Attribute join (keeps left geometry). Thin, validated wrapper on merge."""
    geom = left[GEOM_COL] if GEOM_COL in left.columns else None
    right = right.drop(columns=[GEOM_COL], errors="ignore")
    merged = left.drop(columns=[GEOM_COL], errors="ignore").merge(right, on=on, how=how, validate=validate)
    if geom is not None:
        merged[GEOM_COL] = geom.reset_index(drop=True)
    return merged


def spatial_join(
    left_gdf,
    right_gdf,
    predicate: str = "intersects",
    how: str = "inner",
):
    """geopandas spatial join (point-in-polygon, overlap, etc.).

    predicate: intersects | within | contains | crosses | touches | overlaps
    """
    import geopandas as gpd

    if left_gdf.crs != right_gdf.crs:
        right_gdf = right_gdf.to_crs(left_gdf.crs)
    return gpd.sjoin(left_gdf, right_gdf, predicate=predicate, how=how)


def aggregate_by_polygon(
    points_gdf,
    polygons_gdf,
    value_col: str | None = None,
    agg: str = "count",
):
    """Summarize points within polygons (count or aggregate a value column)."""
    joined = spatial_join(points_gdf, polygons_gdf, predicate="within", how="inner")
    key = "index_right"
    if value_col:
        grouped = joined.groupby(key)[value_col].agg(agg)
    else:
        grouped = joined.groupby(key).size().rename("count")
    out = polygons_gdf.copy()
    out = out.join(grouped, how="left")
    return out


def buffer(gdf, distance: float, projected_crs: int = 3857):
    """Buffer features by ``distance`` (CRS units after reprojection)."""
    original = gdf.crs
    g = gdf.to_crs(projected_crs)
    g["geometry"] = g.geometry.buffer(distance)
    return g.to_crs(original) if original else g


def dissolve(gdf, by: str | None = None, aggfunc: str = "first"):
    """Merge geometries, optionally grouped by an attribute."""
    return gdf.dissolve(by=by, aggfunc=aggfunc).reset_index()
