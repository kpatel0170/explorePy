"""Spatially Enabled DataFrame (SeDF) helpers — construction, ops, export.

Bridges the ArcGIS Python API's ``GeoAccessor`` / ``GeoSeriesAccessor`` with
pandas and geopandas.  Every operation here works on a ``pd.DataFrame`` that
has been spatially enabled (has a ``.spatial`` accessor and a ``SHAPE`` column).

Quick reference
---------------
    from esri_utils.sdf import from_xy, from_layer, sjoin, plot_sdf

    sdf = from_xy(df, x_col="lon", y_col="lat", sr=4326)
    sdf = from_layer(gis, item_id="abc123")

    joined = sjoin(sdf, polygons_sdf, how="inner")
    plot_sdf(sdf)
"""

from __future__ import annotations

from typing import Any

import pandas as pd

GEOM_COL = "SHAPE"


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #
def from_xy(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    sr: int = 4326,
) -> pd.DataFrame:
    """Create a Spatially Enabled DataFrame from latitude/longitude columns.

    Registers the ``.spatial`` accessor by importing ``GeoAccessor``,
    then calls ``pd.DataFrame.spatial.from_xy``.

    Parameters
    ----------
    df : pd.DataFrame
        Input with numeric lat/lon columns.
    x_column : str
        Longitude / X column name.
    y_column : str
        Latitude / Y column name.
    sr : int
        Spatial reference WKID (default 4326).

    Returns
    -------
    pd.DataFrame (spatially enabled — ``.spatial`` is available).
    """
    _register_spatial()
    return pd.DataFrame.spatial.from_xy(df=df, x_column=x_column, y_column=y_column, sr=sr)


def from_layer(layer, fields: str = "*", where: str = "1=1", sr: int | None = None) -> pd.DataFrame:
    """Query a FeatureLayer directly into a Spatially Enabled DataFrame.

    More concise than the two-step ``query_to_sdf`` — uses the native
    ``pd.DataFrame.spatial.from_layer`` under the hood.

    Parameters
    ----------
    layer : arcgis.features.FeatureLayer
        Any feature layer or table layer.
    fields : str
        Comma-separated field list (default "*").
    where : str
        SQL where clause (default "1=1").
    sr : int, optional
        Output spatial reference.

    Returns
    -------
    pd.DataFrame (spatially enabled).
    """
    _register_spatial()
    kwargs: dict[str, Any] = dict(layer=layer, fields=fields, where=where)
    if sr:
        kwargs["sr"] = sr
    return pd.DataFrame.spatial.from_layer(**kwargs)


def from_featureclass(path: str, **kwargs) -> pd.DataFrame:
    """Read a local feature class into a Spatially Enabled DataFrame.

    Requires arcpy (ArcGIS Pro environment).

    Parameters
    ----------
    path : str
        Full path to feature class (e.g. ``r"C:\\data\\my.gdb\\parcels"``).
    **kwargs
        Passed to ``pd.DataFrame.spatial.from_featureclass`` (e.g. ``where_clause``,
        ``fields``, ``sr``, ``spatial_filter``).

    Returns
    -------
    pd.DataFrame (spatially enabled).
    """
    _register_spatial()
    return pd.DataFrame.spatial.from_featureclass(path, **kwargs)


def from_geodataframe(gdf) -> pd.DataFrame:
    """Convert a geopandas GeoDataFrame to a Spatially Enabled DataFrame.

    Uses ``pd.DataFrame.spatial.from_geodataframe``.
    """
    _register_spatial()
    return pd.DataFrame.spatial.from_geodataframe(gdf)


# --------------------------------------------------------------------------- #
# Spatial operations
# --------------------------------------------------------------------------- #
def sjoin(
    target: pd.DataFrame,
    join: pd.DataFrame,
    how: str = "inner",
    op: str = "intersects",
) -> pd.DataFrame:
    """Spatial join — match rows from *target* to *join* based on location.

    Wraps ``.spatial.join`` (``arcpy`` geometry engine) when available,
    but works with any spatially enabled DataFrame.

    Parameters
    ----------
    target : pd.DataFrame
        Spatially enabled DataFrame (left).
    join : pd.DataFrame
        Spatially enabled DataFrame (right).
    how : str
        ``"inner"`` (default), ``"left"``, ``"right"``.
    op : str
        Spatial relationship: ``"intersects"`` (default), ``"contains"``,
        ``"within"``, ``"crosses"``, ``"touches"``, ``"overlaps"``.

    Returns
    -------
    pd.DataFrame (spatially enabled).
    """
    _validate_sdf(target, "target")
    _validate_sdf(join, "join")
    return target.spatial.join(join, how=how, op=op)


def buffer(sdf: pd.DataFrame, distance: float) -> pd.DataFrame:
    """Buffer every geometry in the SDF by *distance* (in SR units).

    Uses the ``.geom`` accessor on the SHAPE column.

    Returns
    -------
    pd.DataFrame with a new ``buffer`` column added.
    """
    _validate_sdf(sdf, "sdf")
    _register_spatial()
    sdf = sdf.copy()
    sdf["buffer"] = sdf[GEOM_COL].geom.buffer(distance=distance)
    return sdf


def centroid(sdf: pd.DataFrame) -> pd.DataFrame:
    """Compute centroid of every geometry.

    Returns
    -------
    pd.DataFrame with a new ``centroid`` column added.
    """
    _validate_sdf(sdf, "sdf")
    sdf = sdf.copy()
    sdf["centroid"] = sdf[GEOM_COL].geom.centroid
    return sdf


def distance(sdf: pd.DataFrame, other_geometry) -> pd.Series:
    """Compute distance from every row to *other_geometry*.

    Returns
    -------
    pd.Series of distances.
    """
    _validate_sdf(sdf, "sdf")
    return sdf[GEOM_COL].geom.distance(other=other_geometry)


def extent(sdf: pd.DataFrame) -> dict[str, float]:
    """Return the bounding box of the SDF as {xmin, ymin, xmax, ymax}."""
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.full_extent


def build_spatial_index(sdf: pd.DataFrame, index_type: str = "quadtree"):
    """Build a spatial index on the SDF for fast bounding-box queries.

    Parameters
    ----------
    sdf : pd.DataFrame
        Spatially enabled DataFrame.
    index_type : str
        ``"quadtree"`` (default) or ``"r-tree"``.

    Returns
    -------
    Spatial index object with an ``intersect(bbox)`` method.
    """
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.sindex(index_type)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def to_featurelayer(sdf: pd.DataFrame, title: str, gis, **publish_kwargs) -> Any:
    """Publish the SDF as a new hosted feature layer on the GIS.

    Parameters
    ----------
    sdf : pd.DataFrame
        Spatially enabled DataFrame.
    title : str
        Title for the new feature service item.
    gis : GIS
        Target GIS.

    Returns
    -------
    Item — the published feature layer item.
    """
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.to_featurelayer(title=title, gis=gis, **publish_kwargs)


def to_featureset(sdf: pd.DataFrame) -> Any:
    """Export the SDF as a FeatureSet (in-memory JSON).

    Useful as input to network analysis or geoprocessing tools.
    """
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.to_featureset()


def to_featurecollection(sdf: pd.DataFrame) -> Any:
    """Export the SDF as a FeatureCollection."""
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.to_feature_collection()


def to_featureclass(sdf: pd.DataFrame, path: str, **kwargs) -> str:
    """Write the SDF to a local feature class (requires arcpy).

    Parameters
    ----------
    sdf : pd.DataFrame
        Spatially enabled DataFrame.
    path : str
        Output path (e.g. ``r"C:\\data\\my.gdb\\parcels"``).
    **kwargs
        Passed to ``.spatial.to_featureclass``.

    Returns
    -------
    str — the output path.
    """
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.to_featureclass(path, **kwargs)


def to_table(sdf: pd.DataFrame, path: str, **kwargs) -> str:
    """Write non-spatial attributes to a CSV or table (requires arcpy for gdb)."""
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.to_table(path, **kwargs)


# --------------------------------------------------------------------------- #
# Visualization
# --------------------------------------------------------------------------- #
def plot_sdf(sdf: pd.DataFrame, map_widget=None, **plot_kwargs):
    """Plot the SDF on an interactive map or matplotlib axes.

    Uses the ``.spatial.plot()`` method which supports renderers, class breaks,
    and popups.

    Parameters
    ----------
    sdf : pd.DataFrame
        Spatially enabled DataFrame.
    map_widget : optional
        An ``arcgis.map.Map`` widget instance.  If omitted, creates a new one.
    **plot_kwargs
        Passed to ``.spatial.plot()`` (e.g. ``renderer=``, ``cmap=``).

    Returns
    -------
    The map widget (for further interaction).
    """
    _validate_sdf(sdf, "sdf")
    return sdf.spatial.plot(map_widget=map_widget, **plot_kwargs)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
_SPATIAL_REGISTERED = False


def _register_spatial():
    """Ensure the ``.spatial`` and ``.geom`` accessors are registered."""
    global _SPATIAL_REGISTERED
    if not _SPATIAL_REGISTERED:
        from arcgis.features import GeoAccessor, GeoSeriesAccessor  # noqa: F401

        _SPATIAL_REGISTERED = True


def _validate_sdf(df: pd.DataFrame, label: str = "df"):
    """Check that *df* is spatially enabled."""
    if not hasattr(df, "spatial") or GEOM_COL not in df.columns:
        raise TypeError(
            f"{label} is not spatially enabled. Use from_xy(), from_layer(), or from_geodataframe() first."
        )
