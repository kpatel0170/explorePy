"""Shared primitives for the Spatially Enabled DataFrame (SDF) world.

Single home for the constants and conversions every spatial module needs, so
they are defined once instead of copy-pasted across ``sdf``/``analysis``/
``cleaning``/``network``/``address_recon``.

Heavy deps (arcgis, geopandas, shapely) are imported lazily inside functions so
importing this module never fails on a machine missing one of them.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

#: Geometry column name used by the ArcGIS GeoAccessor on every SDF.
GEOM_COL = "SHAPE"

_SPATIAL_REGISTERED = False


def register_spatial() -> None:
    """Ensure the ``.spatial`` / ``.geom`` accessors are registered.

    Importing ``GeoAccessor`` / ``GeoSeriesAccessor`` registers the pandas
    accessors as a side effect. Idempotent — safe to call repeatedly.
    """
    global _SPATIAL_REGISTERED
    if not _SPATIAL_REGISTERED:
        from arcgis.features import GeoAccessor, GeoSeriesAccessor  # noqa: F401

        _SPATIAL_REGISTERED = True


def validate_sdf(df: pd.DataFrame, label: str = "df") -> None:
    """Raise ``TypeError`` unless *df* is a spatially enabled DataFrame."""
    if not hasattr(df, "spatial") or GEOM_COL not in df.columns:
        raise TypeError(
            f"{label} is not spatially enabled. Use from_xy(), from_layer(), or from_geodataframe() first."
        )


def to_geodataframe(sdf: pd.DataFrame, crs: int | str = 4326):
    """Convert a Spatially Enabled DataFrame → geopandas GeoDataFrame.

    Uses the SDF's native GeoJSON export when available, else rebuilds geometry
    from the SHAPE column via shapely.
    """
    import geopandas as gpd

    if hasattr(sdf, "spatial") and hasattr(sdf.spatial, "to_featureset"):
        try:
            import json

            gj = sdf.spatial.to_featureset().to_geojson
            return gpd.read_file(gj if isinstance(gj, str) else json.dumps(gj))
        except Exception:
            pass

    from shapely.geometry import shape

    geom = sdf[GEOM_COL].apply(lambda g: shape(g) if isinstance(g, dict) else g)
    return gpd.GeoDataFrame(sdf.drop(columns=[GEOM_COL]), geometry=geom, crs=crs)


def to_sdf(gdf) -> pd.DataFrame:
    """Convert a geopandas GeoDataFrame → Spatially Enabled DataFrame."""
    register_spatial()
    return pd.DataFrame.spatial.from_geodataframe(gdf)


def to_featureset(sdf_or_gdf) -> Any:
    """Convert an SDF or GeoDataFrame to an arcgis ``FeatureSet``.

    Accepts a spatially enabled DataFrame (``.spatial.to_featureset``) or a
    geopandas GeoDataFrame (``FeatureSet.from_geodataframe``).
    """
    from arcgis.features import FeatureSet

    if hasattr(sdf_or_gdf, "spatial") and hasattr(sdf_or_gdf.spatial, "to_featureset"):
        return sdf_or_gdf.spatial.to_featureset()
    if hasattr(sdf_or_gdf, "crs"):
        return FeatureSet.from_geodataframe(sdf_or_gdf)
    raise TypeError("Expected a spatially enabled DataFrame or a GeoDataFrame.")
