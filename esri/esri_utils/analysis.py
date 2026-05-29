"""Spatial & tabular analysis: merges, spatial joins, geopandas ops.

Bridges the ArcGIS SDF world and geopandas. ``to_geodataframe`` converts an
SDF so you can use the full geopandas/shapely toolset, then ``to_sdf`` brings
results back for publishing to Enterprise.
"""

from __future__ import annotations

import pandas as pd

GEOM_COL = "SHAPE"


def to_geodataframe(sdf: pd.DataFrame, crs: int | str = 4326):
    """Convert a Spatially Enabled DataFrame -> GeoDataFrame.

    Uses the SDF's native conversion when available, else rebuilds geometry
    from the SHAPE column via shapely.
    """
    import geopandas as gpd

    # arcgis SDFs expose this directly in recent versions.
    if hasattr(sdf, "spatial") and hasattr(sdf.spatial, "to_featureset"):
        try:
            gj = sdf.spatial.to_featureset().to_geojson
            import json

            return gpd.read_file(gj if isinstance(gj, str) else json.dumps(gj))
        except Exception:
            pass

    from shapely.geometry import shape

    geom = sdf[GEOM_COL].apply(lambda g: shape(g) if isinstance(g, dict) else g)
    return gpd.GeoDataFrame(sdf.drop(columns=[GEOM_COL]), geometry=geom, crs=crs)


def to_sdf(gdf) -> pd.DataFrame:
    """Convert a GeoDataFrame back to a Spatially Enabled DataFrame."""
    from arcgis.features import GeoAccessor  # noqa: F401  (registers .spatial)

    return pd.DataFrame.spatial.from_geodataframe(gdf)


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
    merged = left.drop(columns=[GEOM_COL], errors="ignore").merge(
        right, on=on, how=how, validate=validate
    )
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
