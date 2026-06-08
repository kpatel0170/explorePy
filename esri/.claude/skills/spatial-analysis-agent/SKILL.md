---
name: spatial-analysis-agent
description: "Comprehensive guide for AI coding agents doing spatial analysis with the ArcGIS ecosystem and open-source geospatial Python stack. Covers end-to-end workflow patterns, tool-selection decision trees (arcpy vs arcgis API vs geopandas vs PostGIS), CRS management, data-quality validation, safety patterns (dry-run, destructive-op guarding), query optimization, spatial-index usage, geometry validation/repair, testing spatial code, and documentation conventions. Use this skill whenever the task involves ANY spatial/geospatial analysis — buffering, spatial joins, overlays, dissolving, geocoding, network analysis, CRS reprojection, geometry validation, feature-layer querying, publishing spatial data, or building geospatial pipelines. This is the spatial-analysis meta-skill that teaches agents HOW to think about spatial code correctly. Always load this skill when geopandas, arcpy, arcgis.features, shapely, or SDF (.spatial accessor) appear in the task."
---

# Spatial Analysis Agent — AI Coding Guide

Teaches AI agents how to write correct, efficient, safe spatial analysis code
using `arcgis`, `arcpy`, pandas/SDF, geopandas, and shapely.

## Workflow: Canonical pipeline

Frame Question → Ingest → Validate → Clean → Transform → Analyze → Visualize → Publish

**Never skip validation.**

```python
# 1. FRAME — spatial question, CRS needs, output format
# 2. INGEST — query/source
from esri_utils.portal import connect
gis = connect()
sdf = query_to_sdf(lyr, where="STATE='CA'", chunk_size=2000)

# 3. VALIDATE — CRS, nulls, schema
from esri_utils.cleaning import null_report
quality = null_report(sdf)

# 4. CLEAN
from esri_utils.cleaning import trim_strings, standardize_columns
sdf = trim_strings(standardize_columns(sdf))

# 5. TRANSFORM — reproject, buffer, clip
gdf = analysis.to_geodataframe(sdf).to_crs(5070)

# 6. ANALYZE — spatial join, overlay, aggregate
from esri_utils.analysis import spatial_join, buffer, dissolve
result = spatial_join(points_gdf, polys_gdf, predicate="intersects")

# 7. VISUALIZE
from esri_utils.viz import choropleth, save_figure
ax = choropleth(gdf, "population"); save_figure(ax, "output.png")

# 8. PUBLISH
out_sdf = analysis.to_sdf(result)
sdf_to_layer(out_sdf, gis, title="Analysis Result")
```

## Tool selection — engine decision tree

Ask these questions in order:

```
1. Runs on ArcGIS Pro Server?
   YES → arcpy (GDB/SDE) or arcgis API (Portal/service)
   NO  → go to 2

2. Needs Portal auth, publish, or admin?
   YES → arcgis API for Python
   NO  → go to 3

3. Data already in a GeoDataFrame?
   YES → geopandas
   NO  → go to 4

4. Data came from ArcGIS Portal layer?
   YES → SDF (native Portal I/O), convert → GDF for heavy local analysis
   NO  → go to 5

5. Data from file (shapefile/GeoJSON/Parquet)?
   → geopandas directly

6. Need high-performance spatial SQL locally?
   → DuckDB Spatial

7. Need multi-user transactional DB?
   → PostGIS

8. Planetary scale?
   → Apache Sedona or Cloud DW (BigQuery/Snowflake)
```

### arcpy vs arcgis API for Python

| Criterion | arcpy | arcgis API for Python |
|-----------|-------|----------------------|
| Environment | Pro/Server conda (Windows) | Any Python |
| License | ArcGIS Pro license | AGOL/Portal login |
| Data access | Local GDB, SDE, shapefiles | Web GIS, feature services |
| Analysis | 2000+ GP tools | Subset — features, geoanalytics |
| Map automation | APRX, layouts, export | Web maps, dashboards |
| Admin | No | Users, groups, content |

Interop: arcpy for heavy local GDB → publish via arcgis API.

### SDF vs GeoDataFrame

| Criterion | SDF (arcgis engine) | GeoDataFrame (geopandas) |
|-----------|---------------------|--------------------------|
| Portal I/O | Native `.spatial.to_featurelayer` | Needs convert → publish |
| Spatial join | `.spatial.join()` server-side | `gpd.sjoin()` R-tree (3-10x faster) |
| Overlay/dissolve | No built-in | `gpd.overlay()`, `.dissolve()` |
| Buffer | `.spatial.buffer()` arcgis | `.buffer()` shapely |
| CRS fidelity | Full WKID support | EPSG+proj (some esri WKIDs missing) |

Rule: Pull Portal → SDF → GDF for analysis → publish via SDF.

```python
gdf = analysis.to_geodataframe(sdf).to_crs(5070)
result = dissolve(gdf, by="region", aggfunc="sum")
out_sdf = analysis.to_sdf(result)
```

## CRS management — where agents make mistakes

See [CRS reference](references/CRS-reference.md) for full tables + zone finder.

**Golden rules**: Never buffer in 4326. Reproject once. Match CRS before join.
`set_crs` ≠ `to_crs`. Set CRS explicitly on GeoJSON reads.

```python
# Correct: auto-safe buffer
def safe_buffer(gdf, distance_meters):
    orig_crs = gdf.crs
    if not gdf.crs.is_projected:
        gdf = gdf.to_crs(5070)
    gdf["geometry"] = gdf.buffer(distance_meters)
    return gdf.to_crs(orig_crs)
```

## Data quality — pre-flight validation

Run before any spatial op:

```python
from esri_utils._core import validate_sdf, GEOM_COL
from esri_utils import cleaning

validate_sdf(sdf, "input")                           # raises TypeError if bad

null_geom = sdf[GEOM_COL].isna().sum()               # drop null geometries
if null_geom:
    sdf = sdf[sdf[GEOM_COL].notna()]

report = cleaning.null_report(sdf)                     # attribute nulls
sr = sdf.spatial.sr                                    # CRS check
if not sr or sr.get("wkid") == 4326:
    print("[WARN] Geographic CRS — reproject before distance/buffer")
```

For GeoDataFrame:

```python
def validate_gdf(gdf, name="input"):
    checks = []
    if len(gdf) == 0: checks.append(f"[FAIL] {name} empty")
    if gdf.crs is None: checks.append(f"[FAIL] {name} no CRS")
    null = gdf.geometry.isna().sum()
    if null: checks.append(f"[FAIL] {null} null geometries")
    invalid = (~gdf.is_valid).sum()
    if invalid: checks.append(f"[WARN] {invalid} invalid — run make_valid()")
    [print(c) for c in checks]
    return checks
```

## Safety patterns

```python
# Dry-run — always default to True
def publish_layer(sdf, gis, title, dry_run=True):
    if dry_run:
        print(f"[DRY-RUN] Would publish: {title} ({len(sdf)} rows)")
        return
    return sdf_to_layer(sdf, gis, title=title)

# Confirmation — require explicit 'y'
def confirm(prompt="Proceed?"):
    return input(f"{prompt} [y/N] ").strip().lower() == "y"

# Safe delete default — no-op
def delete_features(layer, where="1=0"):
    pass
```

**Never commit secrets.** Use `.env` (gitignored) for ARCGIS_* vars.
`esri doctor` shows `masked_summary()` — never full tokens.

## Query patterns

See [query patterns reference](references/arcgis-query-patterns.md) for full details.

- Always filter server-side with `where` clause
- Specify `out_fields` (avoid `*`)
- Chunk via `result_offset` + `result_record_count` (default limit = 2000)
- Use spatial filters: `intersects(bbox, sr=102100)`
- Fast counts: `return_count_only=True`
- OBJECTID chunking for very large datasets

```python
def query_all(fl, where="1=1", chunk_size=2000):
    frames, offset = [], 0
    while True:
        fset = fl.query(where=where, result_offset=offset,
                        result_record_count=chunk_size)
        if not fset.features: break
        frames.append(fset.sdf)
        offset += chunk_size
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
```

## arcpy patterns

See [arcpy reference](references/arcpy-patterns.md) for cursors, env, errors.

- Always `with`-block for cursors (releases exclusive locks)
- Prefer `SHAPE@XY` over `SHAPE@` (10x faster)
- `try/except` with `arcpy.GetMessages(2)` + `arcpy.GetReturnCode()`
- Check out extensions: `CheckExtension("Spatial")` before use
- Cache `ListFields()` — don't call inside loops
- `in_memory` workspace for intermediates
- `del aprx` after save to release lock

## Geometry validation & repair

```python
from shapely.validation import explain_validity
from shapely import make_valid

invalid = ~gdf.is_valid
gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].apply(
    lambda g: make_valid(g, method="structure")
)
```

## Edge cases — always check

- Null geometries: filter with `.notna()` or `~.isna()`
- Empty geometries: `gdf[~gdf.is_empty]`
- Invalid geometries: `make_valid()` or `buffer(0)`
- Multipart → singlepart: `gdf.explode(index_parts=False)`
- Z/M: shapely drops Z; arcgis handles natively
- CRS mismatch: `assert gdf1.crs == gdf2.crs` before join
- Token expiry: long sessions — call `connect()` again
- SQL injection: escape single quotes in `where` values
- Empty result: `query_all` returns empty DataFrame — check length

## Testing

```python
import pytest
from shapely.geometry import Point, box
from geopandas.testing import assert_geodataframe_equal

@pytest.fixture
def square_gdf():
    return gpd.GeoDataFrame({"id": [1, 2]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)], crs="EPSG:5070")

def test_spatial_join_finds_contained(square_gdf):
    pts = gpd.GeoDataFrame({"n": ["a"]},
        geometry=[Point(0.5, 0.5)], crs="EPSG:5070")
    joined = gpd.sjoin(pts, square_gdf, predicate="within")
    assert len(joined) == 1
```

Tag live-ArcGIS tests with `@pytest.mark.integration`. Never in CI without creds.

## Documentation conventions

Every spatial function docstring MUST state:
1. Assumed input CRS (or "auto-transforms")
2. Output CRS
3. Units of distance/tolerance params

```python
def buffer_in_meters(gdf, distance: float) -> gpd.GeoDataFrame:
    """Buffer geometries.

    CRS: Input must be projected. Auto-reprojects to 5070 if geographic.
         Returns in original CRS.
    distance: meters.
    """
    orig = gdf.crs
    if not gdf.crs.is_projected: gdf = gdf.to_crs(5070)
    gdf["geometry"] = gdf.buffer(distance)
    return gdf.to_crs(orig)
```

## Verification

```bash
cd esri
ruff check . && ruff format --check .
python -m compileall esri_utils
python -c "
from esri_utils import cleaning, analysis, sdf, viz
import geopandas as gpd; from shapely.geometry import Point
gdf = gpd.GeoDataFrame({'id':[1]}, geometry=[Point(0,0)], crs='EPSG:5070')
result = analysis.buffer(gdf, 100)
print(f'Buffer OK: {len(result)} features')
"
```
