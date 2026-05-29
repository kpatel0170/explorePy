"""Geometry service operations — server-side geometry processing.

Wraps ``arcgis.geometry.functions`` to run projections, buffers, simplifications,
and geometric calculations on the ArcGIS Server Geometry service.  All
operations happen server-side, avoiding local library dependencies.

Usage
-----
    from esri_utils.geometry import project, buffer_geometries, simplify

    projected = project(gis, geojson_geom, in_sr=4326, out_sr=3857)
    buffered = buffer_geometries(gis, projected, distance=100, unit="meters")
"""

from __future__ import annotations

from typing import Any


def project(
    gis,
    geometries: list[dict[str, Any]] | dict[str, Any],
    in_sr: int,
    out_sr: int,
    transformation: str = "",
    transform_forward: bool = False,
) -> list[dict[str, Any]]:
    """Project geometries from one spatial reference to another.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometries : list[dict] | dict
        One or more GeoJSON-like geometry dicts.
    in_sr : int
        Input WKID.
    out_sr : int
        Output WKID.
    transformation : str
        Geographic transformation name (auto-chosen if empty).
    transform_forward : bool
        Apply transformation in forward direction.

    Returns
    -------
    list[dict] — projected geometry dicts.
    """
    from arcgis.geometry.functions import project as _project

    input_list = geometries if isinstance(geometries, list) else [geometries]
    return _project(
        geometries=input_list,
        in_sr=in_sr,
        out_sr=out_sr,
        transformation=transformation,
        transform_forward=transform_forward,
        gis=gis,
    )


def buffer_geometries(
    gis,
    geometries: list[dict[str, Any]] | dict[str, Any],
    distances: list[float] | float,
    unit: str = "meters",
    in_sr: int = 4326,
    out_sr: int | None = None,
    buffer_spatial_ref: int | None = None,
    union: bool = False,
) -> list[dict[str, Any]]:
    """Buffer point/line/polygon geometries by a distance.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometries : list[dict] | dict
        Input geometries (GeoJSON-like).
    distances : list[float] | float
        Buffer distance(s) — one per geometry or a single value for all.
    unit : str
        ``"meters"``, ``"kilometers"``, ``"miles"``, ``"feet"`` (default "meters").
    in_sr : int
        Input WKID.
    out_sr : int, optional
        Output WKID (defaults to *in_sr*).
    buffer_spatial_ref : int, optional
        SR for geodesic buffer calculation.
    union : bool
        Merge overlapping buffer polygons (default False).

    Returns
    -------
    list[dict] — buffered geometry dicts.
    """
    from arcgis.geometry.functions import buffer as _buffer

    input_list = geometries if isinstance(geometries, list) else [geometries]
    dists = distances if isinstance(distances, list) else [distances] * len(input_list)

    return _buffer(
        geometries=input_list,
        distances=dists,
        unit=unit,
        in_sr=in_sr,
        out_sr=out_sr or in_sr,
        buffer_spatial_ref=buffer_spatial_ref,
        union=union,
        gis=gis,
    )


def simplify(
    gis,
    geometries: list[dict[str, Any]] | dict[str, Any],
    max_allowable_offset: float,
    in_sr: int = 4326,
    out_sr: int | None = None,
) -> list[dict[str, Any]]:
    """Simplify geometries by the Douglas-Peucker algorithm (server-side).

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometries : list[dict] | dict
        Input geometries.
    max_allowable_offset : float
        Maximum offset in the output SR units.
    in_sr : int
        Input WKID.
    out_sr : int, optional
        Output WKID.

    Returns
    -------
    list[dict] — simplified geometry dicts.
    """
    from arcgis.geometry.functions import simplify as _simplify

    input_list = geometries if isinstance(geometries, list) else [geometries]
    return _simplify(
        geometries=input_list,
        max_allowable_offset=max_allowable_offset,
        in_sr=in_sr,
        out_sr=out_sr or in_sr,
        gis=gis,
    )


def generalize(
    gis,
    geometries: list[dict[str, Any]] | dict[str, Any],
    max_allowable_offset: float,
    in_sr: int = 4326,
    out_sr: int | None = None,
) -> list[dict[str, Any]]:
    """Generalise geometries (remove vertices) within a tolerance.

    Similar to simplify but uses a different algorithm for line smoothing.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometries : list[dict] | dict
        Input geometries.
    max_allowable_offset : float
        Maximum offset in output SR units.
    in_sr : int
        Input WKID.
    out_sr : int, optional
        Output WKID.

    Returns
    -------
    list[dict] — generalised geometry dicts.
    """
    from arcgis.geometry.functions import generalize as _generalize

    input_list = geometries if isinstance(geometries, list) else [geometries]
    return _generalize(
        geometries=input_list,
        max_allowable_offset=max_allowable_offset,
        in_sr=in_sr,
        out_sr=out_sr or in_sr,
        gis=gis,
    )


def areas_and_lengths(
    gis,
    polygons: list[dict[str, Any]] | dict[str, Any],
    calculation_type: str = "geodesic",
    length_unit: str = "meters",
    area_unit: str = "square-meters",
    spatial_ref: int = 4326,
) -> list[dict[str, Any]]:
    """Compute geodesic or planar areas and lengths for polygons.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    polygons : list[dict] | dict
        Polygon geometry dicts.
    calculation_type : str
        ``"geodesic"`` (default) or ``"planar"``.
    length_unit : str
        Output length unit (default "meters").
    area_unit : str
        Output area unit (default "square-meters").
    spatial_ref : int
        Input WKID.

    Returns
    -------
    list[dict] with keys ``area``, ``length`` per polygon.
    """
    from arcgis.geometry.functions import areas_and_lengths as _aal

    input_list = polygons if isinstance(polygons, list) else [polygons]
    return _aal(
        polygons=input_list,
        calculation_type=calculation_type,
        length_unit=length_unit,
        area_unit=area_unit,
        spatial_ref=spatial_ref,
        gis=gis,
    )


def convex_hull(
    gis,
    geometries: list[dict[str, Any]] | dict[str, Any],
    in_sr: int = 4326,
    out_sr: int | None = None,
) -> list[dict[str, Any]]:
    """Compute the convex hull (minimum bounding geometry) for each input.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometries : list[dict] | dict
        Input geometries.
    in_sr : int
        Input WKID.
    out_sr : int, optional
        Output WKID.

    Returns
    -------
    list[dict] — convex hull polygon dicts.
    """
    from arcgis.geometry.functions import convex_hull as _ch

    input_list = geometries if isinstance(geometries, list) else [geometries]
    return _ch(
        geometries=input_list,
        in_sr=in_sr,
        out_sr=out_sr or in_sr,
        gis=gis,
    )


def relation(
    gis,
    geometry1: dict[str, Any],
    geometry2: dict[str, Any],
    relation: str = "esriGeometryRelationIntersects",
    spatial_ref: int = 4326,
) -> bool:
    """Test a spatial relation between two geometries (server-side).

    Supported relations: ``esriGeometryRelationIntersects``,
    ``esriGeometryRelationContains``, ``esriGeometryRelationWithin``,
    ``esriGeometryRelationCrosses``, ``esriGeometryRelationTouches``,
    ``esriGeometryRelationOverlaps``, ``esriGeometryRelationDisjoint``.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    geometry1 : dict
        First geometry (GeoJSON-like).
    geometry2 : dict
        Second geometry.
    relation : str
        Spatial relation to test.
    spatial_ref : int
        WKID.

    Returns
    -------
    bool
    """
    from arcgis.geometry.functions import relation as _relation

    result = _relation(
        geometry1=geometry1,
        geometry2=geometry2,
        relation=relation,
        spatial_ref=spatial_ref,
        gis=gis,
    )
    return bool(result)


def to_geo_coordinate_string(
    gis,
    coordinates: list[list[float]],
    conversion_type: str = "dd",
    conversion_mode: str = "mgrsDefault",
    num_of_digits: int = 6,
    add_spaces: bool = True,
) -> list[str]:
    """Convert xy coordinates to human-readable strings (MGRS, UTM, DMS, etc.).

    conversion_type: ``"dd"``, ``"dm"``, ``"dms"``, ``"mgrs"``, ``"usng"``,
    ``"utm"``, ``"geoRef"``, ``"gars"``.

    Returns
    -------
    list[str] — formatted coordinate strings.
    """
    from arcgis.geometry.functions import to_geo_coordinate_string as _togcs

    return _togcs(
        coordinates=coordinates,
        conversion_type=conversion_type,
        conversion_mode=conversion_mode,
        num_of_digits=num_of_digits,
        add_spaces=add_spaces,
        gis=gis,
    )


def from_geo_coordinate_string(
    gis,
    strings: list[str],
    conversion_type: str = "dd",
    conversion_mode: str | None = None,
    spatial_ref: int = 4326,
) -> list[dict[str, Any]]:
    """Parse coordinate strings (MGRS, UTM, DMS, etc.) into xy geometries.

    Returns
    -------
    list[dict] — geometry dicts with x, y.
    """
    from arcgis.geometry.functions import from_geo_coordinate_string as _fgcs

    return _fgcs(
        strings=strings,
        conversion_type=conversion_type,
        conversion_mode=conversion_mode,
        spatial_ref=spatial_ref,
        gis=gis,
    )
