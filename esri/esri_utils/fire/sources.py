"""Data sources + shared constants for the fire workflow.

Fetchers for NASA FIRMS (LANCE) satellite hotspots and CWFIS agency-reported
active fires, plus the constants (bounding box, CRS, age classes, render styles)
the rest of the package shares. Heavy deps (geopandas) are imported lazily.
"""

from __future__ import annotations

import io
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
AGE_STYLE = {
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
