"""Geocoding helpers: forward, reverse, batch — backed by arcgis.geocoding.

Leverages the ArcGIS Enterprise geocoding utility service (or ArcGIS Online
fallback).  Works with single addresses, bulk DataFrames, and raw coordinate
lookups.

Usage
-----
    from esri_utils.geocode import geocode, reverse_geocode, batch_geocode

    # single address
    result = geocode(gis, "123 Main St, Springfield, IL")

    # reverse
    addr = reverse_geocode(gis, (-77.04, 38.91))

    # batch from DataFrame column
    results = batch_geocode(gis, df, "address_column")
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def geocode(
    gis,
    address: str | dict[str, Any],
    out_sr: int | None = 4326,
    max_locations: int = 1,
    as_featureset: bool = False,
    location_type: str = "street",
    category: str | None = None,
) -> pd.DataFrame | Any:
    """Forward-geocode a single address string or structured address dict.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    address : str | dict
        Single-line address string, or dict of field:value pairs matching
        the geocoder's address fields.
    out_sr : int, optional
        Output spatial reference WKID (default 4326).
    max_locations : int
        Max candidates per address (default 1).
    as_featureset : bool
        Return raw FeatureSet instead of DataFrame.
    location_type : str
        "street" (routing-aware) or "rooftop" (display).
    category : str, optional
        Category filter (e.g. "City", "Postal", "Point of Interest").

    Returns
    -------
    pd.DataFrame with columns: address, score, x, y, wkid, match_addr, addr_type
    """
    from arcgis.geocoding import geocode as _geocode

    results = _geocode(
        address=address,
        geocoder=gis,
        out_sr=out_sr,
        max_locations=max_locations,
        as_featureset=as_featureset,
        location_type=location_type,
        category=category,
    )
    if as_featureset:
        return results

    rows = []
    for r in results or []:
        loc = r.get("location", {})
        attr = r.get("attributes", {})
        rows.append(
            {
                "address": address if isinstance(address, str) else str(address),
                "score": attr.get("Score"),
                "x": loc.get("x"),
                "y": loc.get("y"),
                "wkid": loc.get("spatialReference", {}).get("wkid"),
                "match_addr": attr.get("Match_addr"),
                "addr_type": attr.get("Addr_type"),
            }
        )
    return pd.DataFrame(rows)


def reverse_geocode(
    gis,
    location: list[float] | tuple[float, float] | dict[str, Any],
    distance: float | None = 500,
    out_sr: int | None = 4326,
    lang_code: str | None = None,
    for_storage: bool = False,
) -> dict[str, Any] | None:
    """Reverse-geocode an x,y location to the nearest address.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    location : list | tuple | dict
        [x, y] or {"x": x, "y": y}.
    distance : float, optional
        Search radius in meters (default 500).
    out_sr : int, optional
        Output spatial reference WKID.
    lang_code : str, optional
        Language code (e.g. "en", "fr").
    for_storage : bool
        Set True if result will be stored (lower cost).

    Returns
    -------
    dict with address components, or None on failure.
    """
    from arcgis.geocoding import reverse_geocode as _reverse

    try:
        return _reverse(
            location=location,
            distance=distance,
            out_sr=out_sr,
            lang_code=lang_code,
            for_storage=for_storage,
            geocoder=gis,
        )
    except Exception:
        return None


def batch_geocode(
    gis,
    addresses: list[str] | pd.Series,
    source_country: str | None = None,
    category: str | None = None,
    out_sr: int = 4326,
    location_type: str = "street",
) -> pd.DataFrame:
    """Batch-geocode a list of address strings.

    Uses the synchronous batch endpoint when available; falls back to
    iterative single calls for small lists.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    addresses : list[str] | pd.Series
        Address strings to geocode.
    source_country : str, optional
        Country code to constrain geocoding.
    category : str, optional
        Category filter.
    out_sr : int
        Output WKID (default 4326).
    location_type : str
        "street" or "rooftop".

    Returns
    -------
    pd.DataFrame with per-address match info (one row per candidate).
    """
    from arcgis.geocoding import batch_geocode as _batch

    raw = _batch(
        addresses=list(addresses),
        geocoder=gis,
        source_country=source_country,
        category=category,
        out_sr=out_sr,
        location_type=location_type,
    )
    rows = []
    for i, addr_results in enumerate(raw or []):
        for r in addr_results:
            loc = r.get("location", {})
            attr = r.get("attributes", {})
            rows.append(
                {
                    "input_idx": i,
                    "address": str(addresses[i]),
                    "score": attr.get("Score"),
                    "x": loc.get("x"),
                    "y": loc.get("y"),
                    "match_addr": attr.get("Match_addr"),
                    "addr_type": attr.get("Addr_type"),
                }
            )
    return pd.DataFrame(rows)


def suggest(
    gis,
    text: str,
    max_suggestions: int = 5,
    category: str | None = None,
    search_extent: list[float] | None = None,
) -> pd.DataFrame:
    """Get autocomplete suggestions for partial address / place text.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    text : str
        Partial address or place name.
    max_suggestions : int
        Max results (default 5).
    category : str, optional
        Category filter.
    search_extent : list[float], optional
        Bounding box [xmin, ymin, xmax, ymax] to constrain results.

    Returns
    -------
    pd.DataFrame with columns: text, magic_key, location
    """
    from arcgis.geocoding import suggest as _suggest

    raw = _suggest(
        text=text,
        geocoder=gis,
        max_suggestions=max_suggestions,
        category=category,
        search_extent=search_extent,
    )
    suggestions = raw if isinstance(raw, list) else raw.get("suggestions", [])
    rows = [
        {
            "text": s.get("text"),
            "magic_key": s.get("magicKey"),
            "location": s.get("location"),
        }
        for s in suggestions
    ]
    return pd.DataFrame(rows)


def geocode_dataframe(
    gis,
    df: pd.DataFrame,
    address_column: str,
    out_sr: int = 4326,
    location_type: str = "street",
) -> pd.DataFrame:
    """Geocode every row in a DataFrame and return a spatially-enabled copy.

    Adds columns: geocode_x, geocode_y, geocode_score, geocode_match_addr.
    The original SHAPE is left untouched.

    Parameters
    ----------
    gis : GIS
        Connected ArcGIS GIS object.
    df : pd.DataFrame
        Input data (must contain *address_column*).
    address_column : str
        Column name with address strings.
    out_sr : int
        Output WKID.
    location_type : str
        "street" or "rooftop".

    Returns
    -------
    pd.DataFrame with geocoded coordinate columns appended.
    """
    results = batch_geocode(gis, df[address_column], out_sr=out_sr, location_type=location_type)
    best = results.loc[results.groupby("input_idx")["score"].idxmax()].set_index("input_idx")
    out = df.copy()
    out["geocode_x"] = best["x"]
    out["geocode_y"] = best["y"]
    out["geocode_score"] = best["score"]
    out["geocode_match_addr"] = best["match_addr"]
    return out
