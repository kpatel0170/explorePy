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

Clouds are **distinct per age class, drawn new-over-old** by default: older
classes form a larger, paler background cloud; the recent ``<24h`` class is a
smaller, saturated cloud rendered on top (see ``draw_order`` / ``fill_color`` /
``fill_alpha``). Pass ``nested=True`` for cumulative concentric zones.

Env: ``FIRMS_MAP_KEY`` — free NASA FIRMS map key
(https://firms.modaps.eosdis.nasa.gov/api/). Without it, runs on CWFIS alone.

Layout
------
- ``sources``  : FIRMS / CWFIS fetchers + shared constants (bbox, CRS, age, style).
- ``clouds``   : normalize, filter, buffer/dissolve/shape, orchestration.
- ``example``  : end-to-end SK script (``python -m esri_utils.fire.example``).
- ``README.md``: full documentation.

Usage
-----
    from esri_utils.fire import fire_threat_analysis
    clouds = fire_threat_analysis(day_range=7)
    clouds.to_file("fire_sk.geojson", driver="GeoJSON")
"""

from __future__ import annotations

from .clouds import (
    CLOUD_COLS,
    build_fire_clouds,
    data_driven_radius,
    filter_quality,
    filter_saskatchewan,
    fire_threat_analysis,
    normalize_hotspots,
)
from .sources import (
    AGE_ORDER,
    AGE_STYLE,
    FIRMS_SOURCES,
    PROJ_CRS,
    SK_BBOX,
    age_class,
    fetch_cwfis_active,
    fetch_firms,
    fetch_firms_all,
)

__all__ = [
    # orchestration
    "fire_threat_analysis",
    # sources
    "fetch_firms",
    "fetch_firms_all",
    "fetch_cwfis_active",
    # processing
    "normalize_hotspots",
    "filter_quality",
    "filter_saskatchewan",
    "data_driven_radius",
    "build_fire_clouds",
    "age_class",
    # constants
    "SK_BBOX",
    "PROJ_CRS",
    "FIRMS_SOURCES",
    "AGE_ORDER",
    "AGE_STYLE",
    "CLOUD_COLS",
]
