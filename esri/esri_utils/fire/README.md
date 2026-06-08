# fire — Saskatchewan fire-threat analysis

Turn live wildfire detections into **`FIRE_AREA` cloud polygons**, categorized by
hotspot **age** and styled to render recent fires *on top of* older ones.

It fuses two complementary feeds:

| Feed | What | Role | Cadence |
|------|------|------|---------|
| **NASA FIRMS** (LANCE) | MODIS + VIIRS (SNPP / NOAA-20 / NOAA-21) thermal hotspots | precise *current* detection | near-real-time |
| **CWFIS** `activefires_current` | fires reported by provincial/territorial agencies | authoritative *ground truth* | daily |

> **Saskatchewan only.** Satellite data is clipped to the SK bounding box (plus an
> optional exact boundary polygon); CWFIS is filtered with `agency='sk'`.

---

## Quick start

```bash
export FIRMS_MAP_KEY=...      # free key: https://firms.modaps.eosdis.nasa.gov/api/
cd esri && uv sync
```

```python
from esri_utils.fire import fire_threat_analysis

clouds = fire_threat_analysis(day_range=7)            # GeoDataFrame of FIRE_AREA
clouds[["age_class", "fire_area_km2", "n_hotspots", "n_reliable"]]
clouds.to_file("fire_sk.geojson", driver="GeoJSON")
```

CLI / scripts:

```bash
esri fire --days 7 --out fire_sk.geojson              # console script
python -m esri_utils.fire.example                     # end-to-end + preview PNG
```

Without `FIRMS_MAP_KEY` the workflow still runs on **CWFIS alone**.

---

## Pipeline

```
fetch FIRMS + CWFIS
      │
      ▼
normalize_hotspots      one points layer, common schema, age computed (UTC)
      │
      ▼
filter_quality          drop low-confidence / non-vegetation satellite pixels
filter_saskatchewan     clip to SK bbox (+ optional boundary polygon)
      │
      ▼
data_driven_radius      per-point buffer radius from FRP / hectares
      │
      ▼
build_fire_clouds       buffer → dissolve → drop false positives →
                        morphological smooth/shrink → one cloud per age class
```

Each step is a public function — call them individually, or use the
`fire_threat_analysis` one-shot.

---

## Thresholds — where they come from

Every threshold is a keyword argument on `fire_threat_analysis` (and the
underlying functions). There are **knobs** (fixed defaults you can override) and
**data-driven** values computed from the hotspots themselves.

### Buffer radius — data-driven

`data_driven_radius(min_km=2.0, max_km=12.0)` sets a **per-point** radius, so the
km bounds are just the floor/ceiling of a range the data fills in:

- **Satellite points** scale by **FRP** (fire radiative power), log-normalized to
  the 95th percentile of FRP in the current pull:

  ```
  ref       = FRP_p95
  scaled    = log1p(FRP) / log1p(ref)        # 0..1
  radius_km = min_km + scaled*(max_km-min_km)
  ```

- **CWFIS points** use reported area instead — the radius of the equivalent
  circle from `hectares`, with a midpoint floor so a confirmed fire never
  collapses to a dot:

  ```
  radius_km = max( sqrt(hectares*10000/π)/1000 , (min_km+max_km)/2 )
  ```

### Smooth + shrink — cloud shaping

`build_fire_clouds(smooth_km=3.0, shrink_km=1.0)` shapes the dissolved blobs via
a morphological **close** then a **shrink** (`_cloudify`):

```
geom.buffer(+smooth_m)   # close gaps, merge nearby fires, round corners
    .buffer(-smooth_m)   # back to size, now smooth
    .buffer(-shrink_m)   # tighten the outline
```

- `smooth_km` ↑ → nearby fires merge into one rounded cloud.
- `shrink_km` ↑ → tighter, smaller outline.

### Dissolve

A dissolve is a geometry union (no threshold): all buffers in a class are merged
with `union_all()`.

### False-positive removal

`min_points=2`: after dissolving, each connected blob survives only if it
contains a **CWFIS** point **or** ≥ `min_points` satellite hits. Lone spurious
pixels are dropped.

### Confidence / type

`conf_min=60.0`: CWFIS is always kept; satellite points need `confidence ≥
conf_min` (VIIRS `l/n/h` mapped to `20/60/90`, so 60 = nominal+high). With
`vegetation_only` (default), FIRMS `type ≠ 0` is dropped when present.

### Default summary

| Knob | Default | Effect |
|------|---------|--------|
| `conf_min` | 60 | satellite confidence cutoff |
| `min_km` / `max_km` | 2 / 12 | buffer radius range (km) |
| `smooth_km` | 3 | cloud merge / roundness |
| `shrink_km` | 1 | final edge pull-in |
| `min_points` | 2 | min satellite hits per isolated cluster |
| `day_range` | 7 | FIRMS lookback (1–10 days) |
| `nested` | False | distinct clouds vs. concentric zones |

---

## Output schema

`fire_threat_analysis` / `build_fire_clouds` return a GeoDataFrame (EPSG:4326):

| column | meaning |
|--------|---------|
| `age_class` | `<24h` \| `24-48h` \| `48-96h` \| `>96h` |
| `threat_rank` | 0 = most recent / highest threat |
| `draw_order` | 0 = oldest (bottom) … higher = drawn on top |
| `n_hotspots` | hotspots in this class |
| `n_reliable` | CWFIS-confirmed hotspots in this class |
| `fire_area_km2` | cloud area |
| `sources` | contributing feeds (e.g. `CWFIS,VIIRS_NOAA20`) |
| `fill_color` / `fill_alpha` | suggested render style |
| `geometry` | the FIRE_AREA polygon |

Rows are sorted by `draw_order` (background first).

---

## Rendering: new over old

Clouds are **distinct per age class** (not nested). Older classes accumulate more
detections, so they form a larger, paler **background**; the recent `<24h` class
is a small, saturated cloud drawn **on top**:

| age | color | alpha |
|-----|-------|-------|
| `<24h` | `#d7301f` | 0.90 |
| `24-48h` | `#fc8d59` | 0.75 |
| `48-96h` | `#fdcc8a` | 0.60 |
| `>96h` | `#fef0d9` | 0.45 |

Plot in `draw_order` and the most recent cloud lands on top automatically:

```python
ax = None
for _, r in clouds.iterrows():                          # already draw_order-sorted
    ax = clouds.iloc[[r.name]].plot(ax=ax, color=r.fill_color, alpha=r.fill_alpha)
```

Pass `nested=True` for the alternative **cumulative concentric** zones (each older
class contains the fresher ones).

---

## Tuning for accuracy

- **Fewer false positives** → raise `conf_min` (e.g. 80 for VIIRS high-only) and/or
  `min_points`.
- **Exact SK clip** → pass `boundary=` a GeoDataFrame/GeoSeries of the SK province
  polygon (e.g. from a provinces feature layer) to `fire_threat_analysis` /
  `filter_saskatchewan`; removes neighbouring-province edge detections.
- **Footprint size** → `min_km` / `max_km`. **Blob roundness** → `smooth_km`.

> **Caveat — calibration.** The *radius within* `[min_km, max_km]` is data-driven,
> but the bounds and smoothing distances are sensible engineering priors, **not**
> calibrated against observed SK fire perimeters. Validate cloud areas against
> CWFIS reported `hectares` before relying on absolute sizes.
>
> **Caveat — time zones.** CWFIS `startdate` is parsed as UTC if naive; if the feed
> reports local time, ages can be a few hours off (location is unaffected).

---

## Module layout

| file | contents |
|------|----------|
| `sources.py` | FIRMS / CWFIS fetchers; constants (`SK_BBOX`, `PROJ_CRS`, `AGE_ORDER`, `AGE_STYLE`, `FIRMS_SOURCES`) |
| `clouds.py` | `normalize_hotspots`, `filter_*`, `data_driven_radius`, `build_fire_clouds`, `fire_threat_analysis` |
| `example.py` | runnable end-to-end SK script + preview |
| `__init__.py` | public API re-exports |

## Data sources

- NASA FIRMS Area API — https://firms.modaps.eosdis.nasa.gov/api/area/
- CWFIS active fire catalogue — https://cwfis.cfs.nrcan.gc.ca/en/catalogue/results/bd641635-d30d-4b77-abc0-d6b59b1e8a00
- CWFIS WFS — https://cwfis.cfs.nrcan.gc.ca/geoserver/wfs

`arcgis`/`arcpy` are not required by this workflow — it uses geopandas/shapely
(lazy-imported). Projection: buffering happens in **EPSG:3978** (NAD83 / Canada
Atlas Lambert); output is **EPSG:4326**.
