"""Saskatchewan fire-threat analysis from NASA FIRMS + CWFIS active fire data.

Combines two complementary feeds and turns the points into smoothed
``FIRE_AREA`` "cloud" polygons, categorized by hotspot **age**:

- **NASA FIRMS** (LANCE) satellite hotspots — MODIS + VIIRS on SNPP / NOAA-20 /
  NOAA-21. Precise *current* detections, but noisy (false positives from sun
  glint, industry, agricultural burns).
- **CWFIS** ``activefires_current`` — fires reported daily by provincial /
  territorial agencies. Authoritative *ground truth* on location, slower cadence.

Pipeline (``fire_threat_analysis``)::

    fetch FIRMS + CWFIS  ->  normalize to one points layer  ->  filter to
    Saskatchewan + quality/confidence (drop false positives)  ->  data-driven
    per-point buffer  ->  dissolve  ->  morphological smooth/shrink  ->  one
    FIRE_AREA cloud per AGE class (<24h, 24-48h, 48-96h, >96h).

Accuracy choices
----------------
- CWFIS points are treated as reliable (kept regardless of confidence) and seed
  valid clusters; isolated low-confidence satellite pixels with no neighbours and
  no nearby CWFIS fire are dropped as false positives.
- Buffer radius is **data-driven**: scaled by FRP (fire radiative power) and, for
  CWFIS, by reported ``hectares``; reliable reports get a floor radius.
- Clouds are **distinct per age class, drawn new-over-old** (default): older
  classes accumulate more hotspots -> a larger, paler background cloud, while the
  recent ``<24h`` class is a smaller, saturated cloud rendered on top. The
  ``draw_order`` / ``fill_color`` / ``fill_alpha`` columns make this turnkey.
  (Pass ``nested=True`` for cumulative concentric threat-gradient zones instead.)

Auth / env
----------
- ``FIRMS_MAP_KEY`` — free NASA FIRMS map key (https://firms.modaps.eosdis.nasa.gov/api/).
  Without it the analysis runs on CWFIS alone.

Heavy deps (geopandas, shapely, numpy) are imported lazily.

Usage
-----
    from esri_utils.fire import fire_threat_analysis
    clouds = fire_threat_analysis(day_range=7)          # GeoDataFrame of FIRE_AREA
    clouds.to_file("fire_sk.geojson", driver="GeoJSON")
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import urlopen

import pandas as pd

# Saskatchewan bounding box (west, south, east, north) in EPSG:4326. Generous on
# the edges; precise filtering is done with agency='sk' + an optional clip polygon.
SK_BBOX = (-110.05, 48.95, -101.30, 60.05)

# Equal-area-ish projected CRS for metric buffering across Saskatchewan.
PROJ_CRS = 3978  # NAD83 / Canada Atlas Lambert

# FIRMS near-real-time sources covering MODIS + VIIRS (incl. NOAA-20/21).
FIRMS_SOURCES = (
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
)
_FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
_CWFIS_WFS = "https://cwfis.cfs.nrcan.gc.ca/geoserver/wfs"

# Age classes, freshest first. Index = threat rank (0 = most recent / most prominent).
AGE_ORDER = ["<24h", "24-48h", "48-96h", ">96h"]
_AGE_BINS = [(24, "<24h"), (48, "24-48h"), (96, "48-96h")]

# Suggested render style per age class: recent = small, saturated, on top;
# older = large, pale, in the background. (hex fill, alpha). OrRd-style ramp.
_AGE_STYLE = {
    "<24h": ("#d7301f", 0.90),
    "24-48h": ("#fc8d59", 0.75),
    "48-96h": ("#fdcc8a", 0.60),
    ">96h": ("#fef0d9", 0.45),
}

# VIIRS categorical confidence -> 0..100 so all sources share one numeric scale.
_VIIRS_CONF = {"l": 20.0, "low": 20.0, "n": 60.0, "nominal": 60.0, "h": 90.0, "high": 90.0}


# --------------------------------------------------------------------------- #
# Age helpers
# --------------------------------------------------------------------------- #
def age_class(hours: float) -> str:
    """Bucket an age in hours into one of the AGE_ORDER classes."""
    for limit, label in _AGE_BINS:
        if hours < limit:
            return label
    return ">96h"


def _now_utc() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


# --------------------------------------------------------------------------- #
# Fetch — NASA FIRMS
# --------------------------------------------------------------------------- #
def fetch_firms(
    map_key: str,
    source: str,
    bbox: tuple[float, float, float, float] = SK_BBOX,
    day_range: int = 7,
    date: str | None = None,
) -> pd.DataFrame:
    """Fetch one FIRMS source as a DataFrame (empty on no data / errors).

    ``day_range`` is 1..10; ``date`` is the end date (``YYYY-MM-DD``, default today).
    """
    area = ",".join(str(c) for c in bbox)
    url = f"{_FIRMS_AREA_URL}/{quote(map_key)}/{source}/{area}/{int(day_range)}"
    if date:
        url += f"/{date}"

    with urlopen(url, timeout=120) as resp:  # noqa: S310 (trusted NASA host)
        text = resp.read().decode("utf-8", errors="replace")

    head = text[:200].lstrip().lower()
    if not text.strip() or "latitude" not in text.splitlines()[0].lower():
        # FIRMS returns plain-text errors (e.g. "Invalid MAP_KEY") instead of CSV.
        if "invalid" in head or "error" in head or "exceeded" in head:
            raise RuntimeError(f"FIRMS {source}: {text.strip()[:160]}")
        return pd.DataFrame()

    df = pd.read_csv(io.StringIO(text))
    if not df.empty:
        df["source"] = source.replace("_NRT", "")
    return df


def fetch_firms_all(
    map_key: str,
    sources: tuple[str, ...] = FIRMS_SOURCES,
    bbox: tuple[float, float, float, float] = SK_BBOX,
    day_range: int = 7,
    date: str | None = None,
) -> pd.DataFrame:
    """Fetch + concatenate every FIRMS source. Skips sources that error/empty."""
    frames = []
    for src in sources:
        try:
            df = fetch_firms(map_key, src, bbox=bbox, day_range=day_range, date=date)
        except Exception:
            continue
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Fetch — CWFIS active fires (agency-reported ground truth)
# --------------------------------------------------------------------------- #
def fetch_cwfis_active(
    bbox: tuple[float, float, float, float] = SK_BBOX,
    agency: str | None = "sk",
    type_name: str = "public:activefires_current",
):
    """Fetch CWFIS active fires as a GeoDataFrame (filtered to *agency* if given).

    Returns an empty GeoDataFrame on failure so the workflow still runs on FIRMS.
    """
    import geopandas as gpd

    params = [
        "service=WFS",
        "version=2.0.0",
        "request=GetFeature",
        f"typeName={quote(type_name)}",
        "outputFormat=application/json",
        "srsName=EPSG:4326",
    ]
    if agency:
        params.append("CQL_FILTER=" + quote(f"agency='{agency}'"))
    url = f"{_CWFIS_WFS}?" + "&".join(params)

    try:
        gdf = gpd.read_file(url)
    except Exception:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    if gdf.empty:
        return gdf
    w, s, e, n = bbox
    return gdf.cx[w:e, s:n]


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

    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )
    return gdf


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


_CLOUD_COLS = [
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

    Returns a GeoDataFrame (EPSG:4326) with columns ``_CLOUD_COLS`` + geometry,
    sorted by ``draw_order`` (background first) so a sequential plot stacks the
    most recent cloud on top.
    """
    import geopandas as gpd

    if points is None or len(points) == 0:
        return gpd.GeoDataFrame(columns=_CLOUD_COLS, geometry=[], crs="EPSG:4326")

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
        color, alpha = _AGE_STYLE[cls]
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
