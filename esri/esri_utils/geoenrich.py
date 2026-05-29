"""GeoEnrichment — enrich study areas with demographic & landscape data.

Backed by ``arcgis.geoenrichment`` (Business Analyst).  Requires a licensed
GeoEnrichment service on the Enterprise (or an ArcGIS Online subscription).

All functions accept an optional ``gis`` parameter; if omitted they use the
current active GIS session.

Usage
-----
    from esri_utils.geoenrich import (
        get_countries, enrich_study_areas,
        standard_geography_query, create_report
    )

    countries = get_countries(gis)
    enriched = enrich_study_areas(gis, study_areas_sdf, variables=...)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def get_countries(gis=None) -> pd.DataFrame:
    """List countries available for GeoEnrichment.

    Returns
    -------
    pd.DataFrame with columns: id, name, datasets, data_levels.
    """
    from arcgis.geoenrichment import get_countries as _get_countries

    raw = _get_countries(gis=gis)
    rows = [
        {
            "id": c.id,
            "name": c.name,
            "datasets": getattr(c, "datasets", []),
            "data_levels": getattr(c, "dataLevels", []),
        }
        for c in raw
    ]
    return pd.DataFrame(rows)


def get_enrich_variables(gis, country_id: str | None = None) -> pd.DataFrame:
    """List available enrich variables (demographic attributes) for a country.

    Parameters
    ----------
    gis : GIS, optional
        Connected GIS (or active session).
    country_id : str, optional
        Two-letter country code (e.g. ``"US"``, ``"CA"``).  If omitted uses
        the default country.

    Returns
    -------
    pd.DataFrame with columns: id, alias, category, dataset.
    """
    from arcgis.geoenrichment import Country

    country = Country(country_id, gis=gis) if country_id else Country(gis=gis)
    variables = country.enrich_variables
    rows = [
        {
            "id": v.get("id"),
            "alias": v.get("alias"),
            "category": v.get("category"),
            "dataset": v.get("dataset"),
        }
        for v in (variables or [])
    ]
    return pd.DataFrame(rows)


def enrich_study_areas(
    gis,
    study_areas: pd.DataFrame,
    variables: list[str] | pd.DataFrame | None = None,
    return_geometry: bool = True,
    proximity_type: str | None = None,
    proximity_value: float | None = None,
    proximity_metric: str | None = None,
    output_spatial_reference: int = 4326,
) -> pd.DataFrame:
    """Enrich study area polygons (or points/lines) with demographic data.

    Parameters
    ----------
    gis : GIS
        Connected GIS with GeoEnrichment license.
    study_areas : pd.DataFrame (SDF) or GeoDataFrame
        Polygon features defining areas to enrich.  Points/lines are also
        accepted and will be buffered automatically.
    variables : list[str] | pd.DataFrame, optional
        Variable IDs to include (e.g. ``"TOTPOP_CY"`` for total population).
        If omitted, all available variables for the country are used.
        Can also be a DataFrame from *get_enrich_variables*.
    return_geometry : bool
        Include geometry in the output (default True).
    proximity_type : str, optional
        Travel mode for buffering points (e.g. ``"Driving Time"``).
    proximity_value : float, optional
        Buffer size (e.g. ``5`` for 5-minute drive).
    proximity_metric : str, optional
        Unit for proximity (e.g. ``"Minutes"``, ``"Miles"``).
    output_spatial_reference : int
        Output WKID (default 4326).

    Returns
    -------
    pd.DataFrame with original columns plus enrich variables.
    """
    from arcgis.geoenrichment import enrich as _enrich

    var_ids = None
    if variables is not None:
        if isinstance(variables, pd.DataFrame):
            var_ids = variables["id"].tolist()
        else:
            var_ids = list(variables)

    result = _enrich(
        study_areas=study_areas,
        analysis_variables=var_ids,
        return_geometry=return_geometry,
        proximity_type=proximity_type,
        proximity_value=proximity_value,
        proximity_metric=proximity_metric,
        output_spatial_reference=output_spatial_reference,
        gis=gis,
    )
    return result


def standard_geography_query(
    gis,
    country: str,
    dataset: str = "USA.ZIP5",
    ids: list[str] | None = None,
    geoquery: str | None = None,
    return_geometry: bool = True,
    out_sr: int = 4326,
    max_features: int = 1000,
) -> pd.DataFrame:
    """Query standard geography boundaries (e.g. ZIP codes, counties, tracts).

    Parameters
    ----------
    gis : GIS
        Connected GIS with GeoEnrichment license.
    country : str
        Two-letter country code (e.g. ``"US"``, ``"CA"``).
    dataset : str
        Standard geography dataset name, e.g. ``"USA.ZIP5"``, ``"USA.County"``,
        ``"USA.Tract"``, ``"USA.State"``, ``"USA.CBSA"``.
    ids : list[str], optional
        Specific geography IDs to return (e.g. ZIP codes or FIPS codes).
    geoquery : str, optional
        Name-based query (e.g. ``"San Diego*"`` for counties matching).
    return_geometry : bool
        Include polygon geometry (default True).
    out_sr : int
        Output WKID.
    max_features : int
        Max features to return.

    Returns
    -------
    pd.DataFrame with geography attributes and (optionally) SHAPE column.
    """
    from arcgis.geoenrichment import standard_geography_query as _sgq

    result = _sgq(
        source_country=country,
        country_dataset=dataset,
        ids=ids,
        geoquery=geoquery,
        return_geometry=return_geometry,
        out_sr=out_sr,
        feature_limit=max_features,
        as_featureset=False,
        gis=gis,
    )
    return result


def create_report(
    gis,
    study_areas: pd.DataFrame,
    report_name: str = "AreaProfile",
    out_format: str = "PDF",
    out_path: str | None = None,
) -> str | bytes:
    """Generate a formatted GeoEnrichment report (PDF/HTML/CSV).

    Parameters
    ----------
    gis : GIS
        Connected GIS with GeoEnrichment license.
    study_areas : pd.DataFrame (SDF) or GeoDataFrame
        Areas to include in the report.
    report_name : str
        Report template name (default ``"AreaProfile"``).
    out_format : str
        ``"PDF"`` (default), ``"HTML"``, ``"CSV"``, ``"XLS"``.
    out_path : str, optional
        Write to file. If omitted, returns raw bytes.

    Returns
    -------
    str (path) if *out_path* was given, else bytes of the report.
    """
    from arcgis.geoenrichment import create_report as _create_report

    result = _create_report(
        study_areas=study_areas,
        report_name=report_name,
        out_format=out_format,
        gis=gis,
    )

    if out_path:
        out_path = Path(out_path) if isinstance(out_path, str) else out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(result, "write"):
            result.write(str(out_path))
        else:
            data = result if isinstance(result, bytes) else result.encode()
            out_path.write_bytes(data)
        return str(out_path)

    return result
