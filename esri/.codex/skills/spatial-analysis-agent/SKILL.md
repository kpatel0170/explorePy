---
name: spatial-analysis-agent
description: "Comprehensive guide for AI coding agents doing spatial analysis with the ArcGIS ecosystem and open-source geospatial Python stack. Covers end-to-end workflow patterns, tool-selection decision trees (arcpy vs arcgis API vs geopandas vs PostGIS), CRS management, data-quality validation, safety patterns (dry-run, destructive-op guarding), testing spatial code, and documentation conventions. Use this skill whenever the task involves ANY spatial/geospatial analysis — buffering, spatial joins, overlays, dissolving, geocoding, network analysis, CRS reprojection, geometry validation, feature-layer querying, publishing spatial data, or building geospatial pipelines. This is the spatial-analysis meta-skill that teaches agents HOW to think about spatial code correctly."
---

# Spatial Analysis Agent — AI Coding Guide

This skill teaches AI coding agents how to write correct, efficient, and safe
spatial analysis code. It covers the full stack used in the `esri_utils` toolkit:
ArcGIS API for Python (`arcgis`), arcpy (`arcpy`), pandas, Spatially Enabled
DataFrame (SDF), geopandas, and shapely.

## When this skill activates

Load this skill when the user:
- Asks to buffer, join, overlay, dissolve, clip, or simplify geometries
- Mentions CRS, projection, reprojection, EPSG, WKID, or spatial reference
- Queries feature layers, geocodes addresses, or runs network analysis
- Publishes, migrates, or administers spatial data
- Cleans or validates geospatial data (null geometries, schema issues)
- Writes spatial analysis code and needs correctness guidance
- Asks about performance, engine choice, or spatial-data best practices

## Workflow: Canonical Pipeline

Frame Question → Ingest → Validate → Clean → Transform → Analyze → Visualize → Publish

Every spatial analysis follows this sequence. **Never skip validation.**

```python
# 1. FRAME — understand the spatial question, CRS needs, output format
# 2. INGEST — query/source the data
from esri_utils.portal import connect
gis = connect()
sdf = query_to_sdf(lyr, where="STATE='CA'", chunk_size=2000)

# 3. VALIDATE — check CRS, nulls, schema before any op
from esri_utils.cleaning import null_report
quality = null_report(sdf)
assert sdf.spatial.sr is not None, "CRS required"

# 4. CLEAN — trim, coerce, dedupe
from esri_utils.cleaning import trim_strings, standardize_columns
sdf = trim_strings(standardize_columns(sdf))

# 5. TRANSFORM — reproject, buffer, clip (choose engine)
gdf = analysis.to_geodataframe(sdf).to_crs(5070)

# 6. ANALYZE — spatial join, overlay, aggregate
from esri_utils.analysis import spatial_join, aggregate_by_polygon
result = spatial_join(points_gdf, polys_gdf, predicate="intersects")

# 7. VISUALIZE — choropleth, categorical, save
from esri_utils.viz import choropleth, save_figure
ax = choropleth(gdf, "population")
save_figure(ax, "output.png")

# 8. PUBLISH — SDF to feature layer, CSV export
out_sdf = analysis.to_sdf(result)
sdf_to_layer(out_sdf, gis, title="Analysis Result")
```

## Tool selection: Engine decision tree

Ask these questions in order:

```
1. Runs on ArcGIS Pro Server?
   YES → arcpy (GDB/SDE ops) or arcgis API (Portal/service ops)
   NO  → go to 2

2. Needs Portal auth, publish, or service admin?
   YES → arcgis API for Python (connect, search, publish, admin)
   NO  → go to 3

3. Data already in a geopandas GeoDataFrame?
   YES → geopandas (keep in GDF land)
   NO  → go to 4

4. Data came from ArcGIS Portal layer?
   YES → SDF (native for Portal I/O), convert to GDF for heavy local analysis
   NO  → go to 5

5. Data from file (shapefile, GeoJSON, Parquet)?
   → geopandas directly

6. Need high-performance spatial SQL on flat files?
   → DuckDB Spatial (local, fast, <100M rows)

7. Need multi-user transactional DB?
   → PostGIS

8. Planetary scale?
   → Apache Sedona or Cloud DW (BigQuery/Snowflake spatial)
```

### arcpy vs arcgis API for Python — when

| Criterion | arcpy | arcgis API for Python |
|-----------|-------|----------------------|
| Environment | ArcGIS Pro/Server conda (Windows) | Any Python (macOS/Linux/Windows) |
| License | ArcGIS Pro license | AGOL/Portal login (free tier available) |
| Data access | Local GDB, SDE, shapefiles | Web GIS features, feature services |
| Analysis tools | Full GP toolbox (2000+ tools) | Subset: features, geoanalytics |
| Map automation | APRX, layouts, export PDF | Web maps, dashboards |
| Admin | Not designed | Users, groups, content management |
| Performance | Fast for local data | Network-bound |

**Both can interoperate.** Typical: arcpy for heavy local GDB processing →
publish via arcgis API.

### SDF vs GeoDataFrame — when

| Criterion | SDF (arcgis engine) | GeoDataFrame (geopandas) |
|-----------|---------------------|--------------------------|
| Portal I/O | Native (.spatial.to_featurelayer) | Requires convert → publish |
| Spatial join | `.spatial.join()` server-side | `gpd.sjoin()` with R-tree (3-10x faster) |
| Overlay/dissolve | No built-in | `gpd.overlay()`, `.dissolve()` |
| Buffer | `.spatial.buffer()` arcgis engine | `.buffer()` shapely engine |
| CRS fidelity | Full WKID support | EPSG+proj; some esri WKIDs missing |
| Open-source stack | Heavy (arcgis dep) | Lightweight (pip install) |

**Rule**: Pull from Portal as SDF → convert to GDF for local analysis →
convert back to SDF to publish.

```python
# SDF → GDF → analyze → SDF → publish
from esri_utils._core import to_geodataframe, to_sdf
gdf = to_geodataframe(sdf).to_crs(5070)
buffered = gdf.buffer(500)
dissolved = buffered.dissolve(by="region")
out_sdf = to_sdf(dissolved)
```

## CRS management — where agents make mistakes

### Golden rules

1. **Never buffer/distance-compute in EPSG:4326.** 100 units in 4326 = 100 degrees.
2. **Reproject ONCE at the start of the workflow**, not repeatedly.
3. **Always match CRS before spatial joins.** Both sides must be in same CRS.
4. **`set_crs` is NOT `to_crs`.** One *declares* CRS (no transform), the other *transforms*.
5. **Set CRS explicitly on GeoJSON reads** — GeoJSON is always 4326 by spec but often loaded as `None`.

```python
# Correct pattern
gdf = gdf.set_crs(4326)     # declare (no transform) — only when CRS is missing
gdf = gdf.to_crs(5070)      # transform — expensive, do once
```

### Common mistakes & fixes

| Mistake | Consequence | Fix |
|---------|------------|-----|
| `buffer(100)` in 4326 | 100-degree buffer (planet-scale) | `to_crs(projected)` → buffer → `to_crs(original)` |
| Spatial join in mismatched CRS | Wrong/missing matches | `gdf1.to_crs(gdf2.crs)` before join |
| Area in 4326 | Square degrees (meaningless) | Use equal-area CRS (5070 CONUS, 3035 Europe) |
| No CRS set | Ops fail silently | `gdf = gdf.set_crs(4326)` if known |
| Repeated `to_crs()` inside loop | Slow (reprojects each iter) | Project once outside loop |

### Best CRS by region/operation

| Use case | EPSG | Name |
|----------|------|------|
| Web maps/display | 4326 | WGS84 |
| Web tiles | 3857 | Web Mercator |
| Distance (anywhere) | 326xx/327xx | UTM zone (use local zone) |
| Area (CONUS) | 5070 | NAD83 / CONUS Albers |
| Area (Europe) | 3035 | ETRS89 / LAEA Europe |
| Area (Alaska) | 3338 | Alaska Albers |
| Area (Canada) | 3978 | Canada Lambert Conformal Conic |
| Area (Australia) | 78xx | GDA2020 / MGA zones |

### Decision tree

```
→ Web map display only?           → 4326 or 3857
→ Need accurate distances?        → UTM zone (326xx/327xx)
→ Need accurate areas?            → Equal-area Albers (5070/3035/3338/3978)
→ Continental CONUS analysis?     → 5070 (Albers)
→ Global + accurate?              → PostGIS geography type
→ Just validity checking?         → 4326 is fine
```

## Data quality — pre-flight validation

Run this checklist before any spatial operation:

```python
from esri_utils import cleaning
from esri_utils._core import GEOM_COL, validate_sdf

# 1. Validate SDF structure
validate_sdf(sdf, "input_sdf")

# 2. Null/empty geometry check
null_count = sdf[GEOM_COL].isna().sum()
if null_count:
    print(f"[WARN] {null_count} null geometries — dropping")
    sdf = sdf[sdf[GEOM_COL].notna()]

# 3. Null report on attributes
report = cleaning.null_report(sdf)

# 4. CRS check
sr = sdf.spatial.sr
if sr is None or sr.get("wkid") == 4326:
    print(f"[WARN] CRS = {sr.get('wkid', 'None')} — verify before distance ops")

# 5. Schema inspection
from esri_utils.layers import field_summary
summary = field_summary(lyr)   # name, type, nullable, length, domain

# 6. Feature count sanity
count = len(sdf)
if count == 0:
    raise ValueError("Empty dataset — check query where clause")
```

For GeoDataFrame:

```python
def validate_gdf(gdf, name="input"):
    checks = []
    if len(gdf) == 0:
        checks.append(f"[FAIL] {name} is empty")
    if gdf.crs is None:
        checks.append(f"[FAIL] {name} has no CRS — use set_crs()")
    if not gdf.crs.is_projected and any(op in str(type(gdf).__name__).lower() for op in ["buffer", "distance"]):
        checks.append(f"[WARN] {name} is geographic — reproject before distance/buffer")
    null_geom = gdf.geometry.isna().sum()
    if null_geom:
        checks.append(f"[FAIL] {null_geom} null geometries")
    invalid = (~gdf.is_valid).sum()
    if invalid:
        checks.append(f"[WARN] {invalid} invalid geometries — call make_valid()")
    for c in checks:
        print(c)
    return checks
```

## Safety patterns

### Dry-run before destructive ops

```python
def publish_layer(sdf, gis, title, dry_run=True):
    if dry_run:
        print(f"[DRY-RUN] Would publish: {title} ({len(sdf)} rows)")
        print(f"[DRY-RUN] Schema: {list(sdf.columns)}")
        print(f"[DRY-RUN] Folder: scratch")
        return
    return sdf_to_layer(sdf, gis, title=title)

# Always default to dry_run=True; user explicitly opts in
# item = publish_layer(sdf, gis, "My Layer", dry_run=False)
```

### Confirm destructive edits

```python
def confirm_destructive(prompt="This modifies data in place. Proceed?"):
    """Require explicit 'y' confirmation — never assume."""
    response = input(f"{prompt} [y/N] ").strip().lower()
    return response == "y"
```

### Safe defaults for delete/overwrite

```python
# NEVER default to deleting everything
def delete_features(layer, where="1=0"):
    """Default where='1=0' prevents accidental bulk delete."""
    return layer.edit_features(deletes=...)
```

### Never commit secrets

- `ARCGIS_URL`, `ARCGIS_API_KEY`, passwords → `.env` (gitignored) or env vars
- PortalConfig stores access tokens — use `masked_summary()` for safe display
- `esri doctor` must never log full token values or passwords

## Query patterns — performance & correctness

### Always filter server-side

```python
# BAD — fetches ALL features into memory
sdf = fl.query().sdf                            # no where clause

# GOOD — filter + restrict fields
sdf = fl.query(where="STATE='CA'",
               out_fields="NAME,POP,SHAPE",
               return_geometry=True).sdf

# FAST — count only
count = fl.query(where="YEAR > 2023",
                 return_count_only=True)

# PAGED — handle >maxRecordCount
def query_all(fl, where="1=1", out_fields="*", chunk_size=2000):
    frames, offset = [], 0
    while True:
        fset = fl.query(where=where, out_fields=out_fields,
                       result_offset=offset, result_record_count=chunk_size)
        if not fset.features:
            break
        frames.append(fset.sdf)
        offset += chunk_size
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
```

### Spatial filter with arcgis geometry filters

```python
from arcgis.geometry.filters import contains, intersects, within

bbox = {"xmin": -13198303, "ymin": 4059062,
        "xmax": -13197797, "ymax": 4059421,
        "spatialReference": {"wkid": 102100}}

results = fl.query(geometry_filter=intersects(bbox, sr=102100),
                   out_fields="APN,UseType")
```

### OBJECTID-based chunking for very large sets

```python
oids = fl.query(return_ids_only=True)["objectIds"]
for i in range(0, len(oids), 2000):
    chunk = oids[i:i+2000]
    batch = fl.query(where=f"OBJECTID>={chunk[0]} AND OBJECTID<={chunk[-1]}")
```

## arcpy-specific patterns

### Environment management

```python
import arcpy

arcpy.env.workspace = r"C:\data\base.gdb"
arcpy.env.overwriteOutput = True     # always during dev
arcpy.env.parallelProcessingFactor = "75%"   # multi-core
arcpy.env.XYTolerance = 0.001         # avoid topology artifacts

# Reset between tasks
arcpy.ResetEnvironments()
```

Always use `try/finally` to restore modified env vars.

### Cursor patterns — always use with-block

```python
# SearchCursor (read)
with arcpy.da.SearchCursor(fc, ["field1", "SHAPE@XY"],
                           where_clause="status='active'") as cursor:
    for (x, y), in cursor:
        # SHAPE@XY is 10x faster than SHAPE@ (full geometry object)
        ...

# UpdateCursor (modify)
with arcpy.da.UpdateCursor(fc, ["field1", "field2"]) as cursor:
    for row in cursor:
        row[1] = row[0] * 1.5
        cursor.updateRow(row)

# InsertCursor (create)
with arcpy.da.InsertCursor(fc, ["id", "SHAPE@"]) as cursor:
    for id_val, geom in data:
        cursor.insertRow([id_val, geom])
```

### Geometry tokens (prefer these over SHAPE@)

| Token | Returns | Speed |
|-------|---------|-------|
| `SHAPE@XY` | (x, y) tuple | Fastest |
| `SHAPE@X`, `SHAPE@Y` | Individual coords | Fast |
| `SHAPE@` | Full geometry object | Slow |
| `SHAPE@JSON` | GeoJSON string | Moderate |

### Error handling

```python
import arcpy

try:
    result = arcpy.Buffer_analysis(in_fc, out_fc, "100 Meters")
    if result.maxSeverity >= 2:
        print("ERROR:", result.getMessages(2))
except arcpy.ExecuteError:
    print("GP Error:", arcpy.GetMessages(2))
    print("Code:", arcpy.GetReturnCode())
except Exception:
    import traceback; traceback.print_exc()
```

### License checks

```python
if arcpy.CheckExtension("Spatial") != "Available":
    raise RuntimeError("Spatial Analyst not available")
arcpy.CheckOutExtension("Spatial")
try:
    # spatial tools
    pass
finally:
    arcpy.CheckInExtension("Spatial")
```

### Performance tips

- Use `in_memory` workspace for intermediates (not for final or >500K features)
- Add attribute indices before bulk cursor ops: `arcpy.AddIndex_management(fc, "field")`
- Cache `ListFields()` results — don't call inside loops
- Chunk via `arcpy.da.GetOIDRanges()` for very large datasets
- Prefer `MakeFeatureLayer` + `SelectLayerByLocation` over GP tools for spatial filters

## Memory & performance

### pandas memory optimization

```python
# Downcast numeric types for large DataFrames
for col in sdf.select_dtypes("int64").columns:
    sdf[col] = pd.to_numeric(sdf[col], downcast="integer")
for col in sdf.select_dtypes("float64").columns:
    sdf[col] = pd.to_numeric(sdf[col], downcast="float")

# Use categoricals for low-cardinality strings
sdf["state"] = sdf["state"].astype("category")
```

### Vectorized ops over apply()

```python
# BAD — row-by-row Python loop
sdf["area"] = sdf.apply(lambda r: r["SHAPE"].geom.area, axis=1)

# GOOD — vectorized C-level
gdf["area"] = gdf.geometry.area

# For SDF, use .geom accessor
sdf["area"] = sdf.SHAPE.geom.area
```

### Spatial index

```python
# GeoDataFrame — automatically built on first spatial op
_ = gdf.sindex   # triggers R-tree construction

# Use cx for bounding-box prefilter before sjoin
candidates = gdf_left.cx[xmin:xmax, ymin:ymax]
result = gpd.sjoin(candidates, gdf_right, predicate="intersects")

# SDF spatial index
si = sdf.spatial.sindex("quadtree")
```

## Geometry validation & repair

```python
from shapely.validation import explain_validity
from shapely import make_valid

# Check validity
invalid = ~gdf.is_valid
print(f"{invalid.sum()} invalid geometries")

# Diagnose
for idx in gdf[invalid].index:
    print(explain_validity(gdf.at[idx, "geometry"]))

# Repair (prefer 'structure' method)
gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].apply(
    lambda g: make_valid(g, method="structure")
)

# Alternative: buffer(0) for simple self-intersections
gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
```

## Testing spatial code

### Synthetic data fixtures

```python
import pytest
from shapely.geometry import Point, box

@pytest.fixture
def square_gdf():
    return gpd.GeoDataFrame({"id": [1, 2]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)],
        crs="EPSG:5070")

@pytest.fixture
def point_gdf():
    return gpd.GeoDataFrame({"name": ["a", "b"]},
        geometry=[Point(0.5, 0.5), Point(10, 10)],
        crs="EPSG:5070")

def test_spatial_join_finds_contained_point(point_gdf, square_gdf):
    joined = gpd.sjoin(point_gdf, square_gdf, predicate="within")
    assert len(joined) == 1
    assert joined.iloc[0]["name"] == "a"
```

### Static reference data

Keep small GeoJSON/Parquet in `tests/data/`:

```python
from geopandas.testing import assert_geodataframe_equal

def test_against_known_result():
    result = my_analysis(gdf)
    expected = gpd.read_file("tests/data/expected.geojson")
    assert_geodataframe_equal(result, expected)
```

### Live ArcGIS — integration test only

```python
@pytest.mark.integration
def test_arcgis_feature_service():
    gdf = gpd.read_file(os.environ["TEST_SERVICE_URL"])
    assert len(gdf) > 0
```

Tag with `@pytest.mark.integration`, never run in CI without credentials.

## Documentation conventions for spatial code

Every spatial function docstring MUST state:
1. Assumed input CRS (or "auto-transforms to X")
2. Output CRS
3. Units of distance/tolerance parameters

```python
def buffer_in_meters(gdf, distance: float) -> gpd.GeoDataFrame:
    """Buffer geometries by distance in meters.

    CRS: Input must be in a projected CRS (meters).
         Will reproject to EPSG:5070 if geographic.
         Returns GeoDataFrame in original CRS.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input geometries. CRS: any.
    distance : float
        Buffer distance in meters.

    Returns
    -------
    GeoDataFrame
        Buffered geometries. CRS: same as input.
    """
    original_crs = gdf.crs
    if not gdf.crs.is_projected:
        gdf = gdf.to_crs(5070)
    gdf["geometry"] = gdf.buffer(distance)
    return gdf.to_crs(original_crs)
```

## Acceptance — verify spatial code

```bash
# Lint + syntax
cd esri
ruff check . && ruff format --check .
python -m compileall esri_utils

# Import check (no heavy deps)
python -c "from esri_utils import cleaning, analysis, sdf, viz; print('Modules OK')"

# Spatial analysis smoke test (no Portal needed)
python -c "
import pandas as pd; import geopandas as gpd
from shapely.geometry import Point
from esri_utils.analysis import buffer, dissolve
gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs='EPSG:5070')
result = buffer(gdf, 100)
print(f'Buffer OK: {len(result)} features')
"

# Portal-dependent (manual)
# python -m esri_utils doctor --connect
# esri query <known-item-id> --out /tmp/test.csv
```

## Edge cases — check for these

- Null geometries: `sdf[sdf[GEOM_COL].notna()]` or `gdf[~gdf.geometry.isna()]`
- Empty geometries: `gdf[~gdf.is_empty]` (Point() with no coords)
- Invalid geometries: `gdf[~gdf.is_valid]` — fix with `make_valid()` or `buffer(0)`
- Multipart geometries: `gdf.explode(index_parts=False)` to singlepart
- Z/M values: shapely ops drop Z automatically; arcgis handles Z natively
- CRS mismatch: always check `gdf1.crs == gdf2.crs` before spatial join
- Single-quote in where clause: escape via `field = val.replace("'", "''")`
- Empty result set from query: returns empty `pd.DataFrame()` — check `len(sdf)` before ops
- Rate limits: batch geocoding/publishing — pace with `time.sleep()` between calls
- Token expiry: long-running sessions — `connect()` returns fresh auth; call again if `TokenExpired`
