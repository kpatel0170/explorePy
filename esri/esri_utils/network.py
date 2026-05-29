"""Network analysis: route, service area, closest facility, OD cost matrix.

Wraps ``arcgis.network.analysis`` — the server-side solvers that work against
an ArcGIS Enterprise Network Analysis service (or ArcGIS Online).

All functions return a results dict with FeatureSets; use the helper
``extract_result_layer`` to pull a tabular DataFrame from any result.

Usage
-----
    from esri_utils.network import find_routes, generate_service_areas

    routes = find_routes(gis, stops_sdf)
    df = extract_result_layer(routes, "routes")
"""

from __future__ import annotations

from typing import Any

import pandas as pd


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _to_featureset(
    sdf_or_gdf,
) -> Any:
    """Convert an SDF or GeoDataFrame to a FeatureSet for the solvers."""
    from arcgis.features import FeatureSet

    if hasattr(sdf_or_gdf, "spatial") and hasattr(sdf_or_gdf.spatial, "to_featureset"):
        return sdf_or_gdf.spatial.to_featureset()
    return FeatureSet.from_geodataframe(sdf_or_gdf) if hasattr(sdf_or_gdf, "crs") else None  # noqa: E501


def extract_result_layer(result: dict, key: str) -> pd.DataFrame:
    """Pull a result layer (FeatureSet) from a network analysis output as DataFrame.

    Parameters
    ----------
    result : dict
        Return value from a ``network.analysis`` solver.
    key : str
        Layer key, e.g. ``"routes"``, ``"serviceAreas"``, ``"facilities"``.

    Returns
    -------
    pd.DataFrame
    """
    fs = result.get(key)
    if fs is None:
        return pd.DataFrame()
    return fs.sdf if hasattr(fs, "sdf") else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Route
# --------------------------------------------------------------------------- #
def find_routes(
    gis,
    stops,
    preserve_terminal_stops: bool = True,
    travel_mode: str | None = None,
    time_of_day: str | None = None,
    out_sr: int = 4326,
) -> dict:
    """Find shortest/quickest routes visiting the given stops.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    stops : pd.DataFrame (SDF) or GeoDataFrame
        Point features for the route stops.
    preserve_terminal_stops : bool
        Keep first/last stop in place when reordering (default True).
    travel_mode : str, optional
        Travel mode name (e.g. "Driving Time").
    time_of_day : str, optional
        ``"YYYY-MM-DD HH:MM"`` — enables traffic-aware routing.
    out_sr : int
        Output spatial reference WKID.

    Returns
    -------
    dict with keys: ``routes``, ``stops``, ``directions`` (FeatureSets).
    """
    from arcgis.network.analysis import find_routes as _find_routes

    stops_fs = _to_featureset(stops)
    return _find_routes(
        stops=stops_fs,
        preserve_terminal_stops=preserve_terminal_stops,
        travel_mode=travel_mode,
        time_of_day=time_of_day,
        out_sr=out_sr,
        gis=gis,
    )


def get_route_directions(result: dict) -> pd.DataFrame:
    """Extract turn-by-turn directions from a find_routes result."""
    return extract_result_layer(result, "directions")


# --------------------------------------------------------------------------- #
# Service Area
# --------------------------------------------------------------------------- #
def generate_service_areas(
    gis,
    facilities,
    break_values: list[float],
    break_units: str = "Minutes",
    travel_mode: str | None = None,
    merge: bool = True,
    overlap: bool = False,
    out_sr: int = 4326,
) -> dict:
    """Generate drive-time / drive-distance polygons around facilities.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    facilities : pd.DataFrame (SDF) or GeoDataFrame
        Point features representing facility locations.
    break_values : list[float]
        One or more break values (e.g. ``[5, 10, 15]`` minutes).
    break_units : str
        ``"Minutes"`` or ``"Miles"`` / ``"Kilometers"``.
    travel_mode : str, optional
        Travel mode name.
    merge : bool
        Merge overlapping polygons at the same break (default True).
    overlap : bool
        Allow overlapping polygons (default False; requires ``merge=False``).
    out_sr : int
        Output WKID.

    Returns
    -------
    dict with keys: ``serviceAreas``, ``facilities`` (FeatureSets).
    """
    from arcgis.network.analysis import generate_service_areas as _gsa

    fac_fs = _to_featureset(facilities)
    return _gsa(
        facilities=fac_fs,
        break_values=break_values,
        break_units=break_units,
        travel_mode=travel_mode,
        merge=merge,
        overlap=overlap,
        out_sr=out_sr,
        gis=gis,
    )


# --------------------------------------------------------------------------- #
# Closest Facility
# --------------------------------------------------------------------------- #
def find_closest_facilities(
    gis,
    incidents,
    facilities,
    number_to_find: int = 1,
    travel_mode: str | None = None,
    travel_direction: str = "Incident to Facility",
    time_of_day: str | None = None,
    out_sr: int = 4326,
) -> dict:
    """Find the N closest facilities (by travel time/distance) to each incident.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    incidents : pd.DataFrame (SDF) or GeoDataFrame
        Incident point locations.
    facilities : pd.DataFrame (SDF) or GeoDataFrame
        Candidate facility point locations.
    number_to_find : int
        Number of closest facilities per incident (default 1).
    travel_mode : str, optional
        Travel mode name.
    travel_direction : str
        ``"Incident to Facility"`` (default) or ``"Facility to Incident"``.
    time_of_day : str, optional
        Enables traffic-aware analysis.
    out_sr : int
        Output WKID.

    Returns
    -------
    dict with keys: ``routes``, ``incidents``, ``facilities`` (FeatureSets).
    """
    from arcgis.network.analysis import find_closest_facilities as _fcf

    inc_fs = _to_featureset(incidents)
    fac_fs = _to_featureset(facilities)
    return _fcf(
        incidents=inc_fs,
        facilities=fac_fs,
        number_to_find=number_to_find,
        travel_mode=travel_mode,
        travel_direction=travel_direction,
        time_of_day=time_of_day,
        out_sr=out_sr,
        gis=gis,
    )


# --------------------------------------------------------------------------- #
# OD Cost Matrix
# --------------------------------------------------------------------------- #
def generate_od_cost_matrix(
    gis,
    origins,
    destinations,
    number_of_destinations: int | None = None,
    travel_mode: str | None = None,
    time_of_day: str | None = None,
    out_sr: int = 4326,
) -> dict:
    """Compute travel cost (time/distance) from every origin to every destination.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    origins : pd.DataFrame (SDF) or GeoDataFrame
        Origin point locations.
    destinations : pd.DataFrame (SDF) or GeoDataFrame
        Destination point locations.
    number_of_destinations : int, optional
        Max destinations to find per origin (default unlimited).
    travel_mode : str, optional
        Travel mode name.
    time_of_day : str, optional
        Enables traffic-aware analysis.
    out_sr : int
        Output WKID.

    Returns
    -------
    dict with keys: ``odCostMatrix``, ``origins``, ``destinations``.
    """
    from arcgis.network.analysis import generate_od_cost_matrix as _od

    orig_fs = _to_featureset(origins)
    dest_fs = _to_featureset(destinations)
    return _od(
        origins=orig_fs,
        destinations=dest_fs,
        number_of_destinations_to_find=number_of_destinations,
        travel_mode=travel_mode,
        time_of_day=time_of_day,
        out_sr=out_sr,
        gis=gis,
    )


# --------------------------------------------------------------------------- #
# Location-Allocation
# --------------------------------------------------------------------------- #
def solve_location_allocation(
    gis,
    demand_points,
    candidate_facilities,
    problem_type: str = "Maximize Attendance",
    number_of_facilities_to_find: int = 1,
    travel_mode: str | None = None,
    out_sr: int = 4326,
) -> dict:
    """Choose the best facility locations to serve demand points.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    demand_points : pd.DataFrame (SDF) or GeoDataFrame
        Point features representing demand.
    candidate_facilities : pd.DataFrame (SDF) or GeoDataFrame
        Potential facility locations.
    problem_type : str
        ``"Maximize Attendance"``, ``"Minimize Travel"``, etc.
    number_of_facilities_to_find : int
        How many facilities to select (default 1).
    travel_mode : str, optional
        Travel mode name.
    out_sr : int
        Output WKID.

    Returns
    -------
    dict with keys: ``locationAllocation``, ``demandPoints``, ``facilities``.
    """
    from arcgis.network.analysis import solve_location_allocation as _sla

    demand_fs = _to_featureset(demand_points)
    cand_fs = _to_featureset(candidate_facilities)
    return _sla(
        demand_points=demand_fs,
        candidate_facilities=cand_fs,
        problem_type=problem_type,
        number_of_facilities_to_find=number_of_facilities_to_find,
        travel_mode=travel_mode,
        out_sr=out_sr,
        gis=gis,
    )
