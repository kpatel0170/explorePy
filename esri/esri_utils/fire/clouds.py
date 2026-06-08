"""Normalize, filter, buffer, dissolve, and shape hotspots into FIRE_AREA clouds.

This is the analytical core: it takes the raw FIRMS + CWFIS feeds from
``sources`` and produces the styled, age-categorized cloud polygons. Heavy deps
(geopandas, shapely, numpy) are imported lazily.
"""

from __future__ import annotations

import os

import pandas as pd

from .sources import (
    AGE_ORDER,
    AGE_STYLE,
    PROJ_CRS,
    SK_BBOX,
    _now_utc,
    _VIIRS_CONF,
    age_class,
    fetch_cwfis_active,
    fetch_firms_all,
)


# --------------------------------------------------------------------------- #
# Normalize both feeds into one points GeoDataFrame
# --------------------------------------------------------------------------- #
def normalize_hotspots(firms: pd.DataFrame, cwfis, now: pd.Timestamp | None = None):
    """Merge FIRMS + CWFIS into one points GeoDataFrame with a common schema.

    Columns: source, reliable, lon, lat, acq_dt, age_hours, age_class,
    confidence (0..100), frp, hectares, geometry (EPSG:4326).
    """
    import geopandas as gpd
    from shapely.geometry import Point

    now = now or _now_utc()
    rows: list[dict] = []

    # --- FIRMS ---
    if firms is not None and not firms.empty:
        acq = pd.to_datetime(
            firms["acq_date"].astype(str).str.strip()
            + " "
            + firms["acq_time"].fillna(0).astype(int).astype(str).str.zfill(4),
            format="%Y-%m-%d %H%M",
            utc=True,
            errors="coerce",
        )
        conf_raw = firms.get("confidence")
        bright = firms.get("brightness")
        if bright is None:
            bright = firms.get("bright_ti4")
        for i, r in firms.reset_index(drop=True).iterrows():
            c = conf_raw.iloc[i] if conf_raw is not None else None
            conf = _VIIRS_CONF.get(str(c).strip().lower(), None)
            if conf is None:
                conf = pd.to_numeric(c, errors="coerce")
            rows.append(
                {
                    "source": r.get("source", "FIRMS"),
                    "reliable": False,
                    "lon": float(r["longitude"]),
                    "lat": float(r["latitude"]),
                    "acq_dt": acq.iloc[i],
                    "confidence": float(conf) if pd.notna(conf) else 0.0,
                    "frp": float(pd.to_numeric(r.get("frp"), errors="coerce") or 0.0),
                    "hectares": 0.0,
                    "ftype": pd.to_numeric(r.get("type"), errors="coerce"),
                    "brightness": float(pd.to_numeric(bright.iloc[i], errors="coerce") or 0.0)
                    if bright is not None
                    else 0.0,
                }
            )

    # --- CWFIS ---
    if cwfis is not None and len(cwfis) > 0:
        start_col = next((c for c in ("startdate", "start_date", "rep_date") if c in cwfis.columns), None)
        start = (
            pd.to_datetime(cwfis[start_col], utc=True, errors="coerce")
            if start_col
            else pd.Series([pd.NaT] * len(cwfis))
        )
        geom = cwfis.geometry
        for i in range(len(cwfis)):
            g = geom.iloc[i]
            if g is None or g.is_empty:
                continue
            pt = g if g.geom_type == "Point" else g.centroid
            rows.append(
                {
                    "source": "CWFIS",
                    "reliable": True,
                    "lon": float(pt.x),
                    "lat": float(pt.y),
                    "acq_dt": start.iloc[i],
                    "confidence": 100.0,
                    "frp": 0.0,
                    "hectares": float(pd.to_numeric(cwfis.iloc[i].get("hectares"), errors="coerce") or 0.0),
                    "ftype": 0.0,
                    "brightness": 0.0,
                }
            )

    if not rows:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    df = pd.DataFrame(rows)
    # Unknown timestamps -> treat as oldest (>96h) so they still register, low priority.
    age = (now - df["acq_dt"]).dt.total_seconds() / 3600.0
    df["age_hours"] = age.fillna(120.0).clip(lower=0.0)
    df["age_class"] = df["age_hours"].map(age_class)

    return gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )


# --------------------------------------------------------------------------- #
# Quality / Saskatchewan filtering (false-positive reduction)
# --------------------------------------------------------------------------- #
def filter_quality(gdf, conf_min: float = 60.0, vegetation_only: bool = True):
    """Drop low-confidence / non-vegetation satellite detections.

    CWFIS (reliable) rows are always kept. FIRMS rows must clear *conf_min*
    (60 ≈ VIIRS 'nominal'+'high', MODIS ≥60). With *vegetation_only*, FIRMS
    ``type`` other than 0 (presumed vegetation fire) is dropped when present.
    """
    if len(gdf) == 0:
        return gdf
    keep = gdf["reliable"] | (gdf["confidence"] >= conf_min)
    if vegetation_only and "ftype" in gdf.columns:
        keep &= gdf["reliable"] | gdf["ftype"].isna() | (gdf["ftype"] == 0)
    return gdf.loc[keep].reset_index(drop=True)


def filter_saskatchewan(gdf, boundary=None):
    """Clip points to Saskatchewan: the SK bbox, plus an optional boundary polygon.

    Pass *boundary* (a GeoDataFrame/GeoSeries of the SK province polygon, e.g. from
    a provinces feature layer) for an exact clip that removes neighbouring-province
    edge detections.
    """
    if len(gdf) == 0:
        return gdf
    w, s, e, n = SK_BBOX
    out = gdf.cx[w:e, s:n]
    if boundary is not None:
        import geopandas as gpd

        bnd = boundary if hasattr(boundary, "geometry") else gpd.GeoSeries(boundary, crs="EPSG:4326")
        bnd = bnd.to_crs(out.crs)
        poly = bnd.geometry.union_all() if hasattr(bnd.geometry, "union_all") else bnd.unary_union
        out = out.loc[out.geometry.within(poly)]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Data-driven buffer radius
# --------------------------------------------------------------------------- #
def data_driven_radius(gdf, min_km: float = 2.0, max_km: float = 12.0):
    """Per-point buffer radius (metres), scaled by the data, not a flat value.

    - Satellite points: log-scaled by FRP (more radiative power -> larger plume
      footprint), normalized to the 95th percentile of FRP in the data.
    - CWFIS points: ``radius = max(reported-area radius, midpoint floor)`` so a
      ground-confirmed fire never collapses to a pinprick.
    """
    import numpy as np

    g = gdf.copy()
    frp = pd.to_numeric(g.get("frp"), errors="coerce").fillna(0.0).clip(lower=0.0)
    ref = frp[frp > 0].quantile(0.95) if (frp > 0).any() else 0.0
    scaled = np.log1p(frp) / np.log1p(ref) if ref > 0 else pd.Series(0.0, index=g.index)
    scaled = scaled.clip(0.0, 1.0)
    radius_km = min_km + scaled * (max_km - min_km)

    # CWFIS: radius from reported hectares (area -> equivalent circle radius).
    hect = pd.to_numeric(g.get("hectares"), errors="coerce").fillna(0.0).clip(lower=0.0)
    area_km = np.sqrt(hect * 1e4 / np.pi) / 1000.0  # m -> km
    floor = (min_km + max_km) / 2.0
    radius_km = radius_km.where(~g["reliable"], np.maximum(area_km, floor))

    g["radius_m"] = radius_km.clip(lower=min_km, upper=max_km * 3) * 1000.0
    return g


# --------------------------------------------------------------------------- #
# Build FIRE_AREA clouds
# --------------------------------------------------------------------------- #
def _cloudify(geom, smooth_m: float, shrink_m: float):
    """Morphological close (merge + round) then shrink -> cloud-like polygon."""
    if geom is None or geom.is_empty:
        return geom
    g = geom.buffer(smooth_m, join_style="round", quad_segs=16)
    g = g.buffer(-smooth_m, join_style="round", quad_segs=16)
    if shrink_m:
        g = g.buffer(-shrink_m, join_style="round", quad_segs=16)
    return g


def _drop_false_positive_clusters(buffers, points, min_points: int):
    """Keep only dissolved components that hold a reliable point or >= min_points."""
    import geopandas as gpd

    union = buffers.union_all() if hasattr(buffers, "union_all") else buffers.unary_union
    comps = list(getattr(union, "geoms", [union]))
    if not comps:
        return points.iloc[0:0]
    comp_gdf = gpd.GeoDataFrame({"cid": range(len(comps))}, geometry=comps, crs=points.crs)
    joined = gpd.sjoin(points, comp_gdf, how="inner", predicate="within")
    stats = joined.groupby("cid").agg(n=("reliable", "size"), rel=("reliable", "sum"))
    valid = set(stats[(stats["rel"] > 0) | (stats["n"] >= min_points)].index)
    keep_ids = joined[joined["cid"].isin(valid)].index.unique()
    return points.loc[points.index.isin(keep_ids)]


CLOUD_COLS = [
    "age_class",
    "threat_rank",
    "draw_order",
    "n_hotspots",
    "n_reliable",
    "fire_area_km2",
    "sources",
    "fill_color",
    "fill_alpha",
]


def build_fire_clouds(
    points,
    nested: bool = False,
    smooth_km: float = 3.0,
    shrink_km: float = 1.0,
    min_points: int = 2,
    proj_crs: int = PROJ_CRS,
):
    """Build one FIRE_AREA cloud per AGE class, styled to render **new over old**.

    By default each class is an **independent** dissolved footprint (NOT nested):
    older classes usually accumulate more hotspots, so they form a larger, paler
    background cloud; the recent ``<24h`` class is a smaller, saturated cloud meant
    to be drawn on top. ``draw_order`` (0 = bottom/oldest) and ``fill_color`` /
    ``fill_alpha`` make that styling turnkey.

    Set *nested=True* for the alternative cumulative concentric-zone look.

    Returns a GeoDataFrame (EPSG:4326) with columns ``CLOUD_COLS`` + geometry,
    sorted by ``draw_order`` (background first) so a sequential plot stacks the
    most recent cloud on top.
    """
    import geopandas as gpd

    if points is None or len(points) == 0:
        return gpd.GeoDataFrame(columns=CLOUD_COLS, geometry=[], crs="EPSG:4326")

    g = points.to_crs(proj_crs).copy()
    if "radius_m" not in g.columns:
        g = data_driven_radius(g)
    g["age_rank"] = g["age_class"].map(lambda c: AGE_ORDER.index(c))
    g["_buf"] = g.geometry.buffer(g["radius_m"], quad_segs=16)

    # False-positive pass on the full footprint, then keep only surviving points.
    buffers = gpd.GeoSeries(g["_buf"], crs=g.crs)
    g = g.loc[_drop_false_positive_clusters(buffers, g, min_points).index]
    if len(g) == 0:
        return build_fire_clouds(points.iloc[0:0])

    smooth_m, shrink_m = smooth_km * 1000.0, shrink_km * 1000.0
    n = len(AGE_ORDER)
    rows = []
    for rank, cls in enumerate(AGE_ORDER):
        subset = g[g["age_rank"] <= rank] if nested else g[g["age_class"] == cls]
        if len(subset) == 0:
            continue
        merged = subset["_buf"].union_all() if hasattr(subset["_buf"], "union_all") else None
        if merged is None:
            from shapely.ops import unary_union

            merged = unary_union(list(subset["_buf"]))
        cloud = _cloudify(merged, smooth_m, shrink_m)
        if cloud is None or cloud.is_empty:
            continue
        own = g[g["age_class"] == cls]
        color, alpha = AGE_STYLE[cls]
        rows.append(
            {
                "age_class": cls,
                "threat_rank": rank,  # 0 = most recent / highest threat
                "draw_order": n - 1 - rank,  # 0 = oldest (bottom), higher = on top
                "n_hotspots": int(len(own)),
                "n_reliable": int(own["reliable"].sum()),
                "fire_area_km2": round(cloud.area / 1e6, 2),
                "sources": ",".join(sorted(subset["source"].unique())),
                "fill_color": color,
                "fill_alpha": alpha,
                "geometry": cloud,
            }
        )

    if not rows:
        return build_fire_clouds(points.iloc[0:0])

    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=proj_crs).to_crs("EPSG:4326")
    # Oldest/background first so a sequential renderer draws the recent cloud on top.
    return out.sort_values("draw_order").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# One-shot orchestration
# --------------------------------------------------------------------------- #
def fire_threat_analysis(
    map_key: str | None = None,
    day_range: int = 7,
    bbox: tuple[float, float, float, float] = SK_BBOX,
    boundary=None,
    conf_min: float = 60.0,
    min_km: float = 2.0,
    max_km: float = 12.0,
    smooth_km: float = 3.0,
    shrink_km: float = 1.0,
    min_points: int = 2,
    nested: bool = False,
    return_points: bool = False,
):
    """Run the full Saskatchewan fire-threat workflow and return FIRE_AREA clouds.

    Clouds are distinct per age class and styled new-over-old by default (set
    *nested=True* for cumulative concentric zones). *map_key* defaults to
    ``$FIRMS_MAP_KEY``; without it the analysis runs on CWFIS alone. Set
    *return_points* to also get the filtered hotspot layer (returns
    ``(clouds, points)``).

    >>> clouds = fire_threat_analysis(day_range=7)
    >>> clouds[["age_class", "fire_area_km2", "n_reliable"]]
    """
    map_key = map_key or os.getenv("FIRMS_MAP_KEY")
    firms = fetch_firms_all(map_key, bbox=bbox, day_range=day_range) if map_key else pd.DataFrame()
    cwfis = fetch_cwfis_active(bbox=bbox)

    points = normalize_hotspots(firms, cwfis)
    points = filter_quality(points, conf_min=conf_min)
    points = filter_saskatchewan(points, boundary=boundary)
    points = data_driven_radius(points, min_km=min_km, max_km=max_km)

    clouds = build_fire_clouds(
        points, nested=nested, smooth_km=smooth_km, shrink_km=shrink_km, min_points=min_points
    )
    return (clouds, points) if return_points else clouds
