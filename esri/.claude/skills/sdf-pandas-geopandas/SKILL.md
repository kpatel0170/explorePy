---
name: sdf-pandas-geopandas
description: "Spatially Enabled DataFrame (SDF), pandas cleaning, and GeoDataFrame analysis workflows for the esri_utils toolkit. Use this skill when the task involves DataFrame manipulation in an ArcGIS context: cleaning tabular data (nulls, types, string trimming), converting between SDF and GeoDataFrame, running spatial joins/buffers/dissolves with either the ArcGIS engine (SDF) or geopandas/shapely engine (GeoDataFrame), managing geometry columns, reprojecting CRS, computing distance/area, aggregating by polygon, or preparing data for publish. This is the right skill for any pandas-heavy or geopandas-heavy work in the esri stack — NOT for raw arcgis SDK operations (use arcgis-python-api) or arcpy paths (use arcpy-workflows)."
---

# SDF / pandas / geopandas

Use for Spatially Enabled DataFrames, pandas cleaning, GeoDataFrame conversion,
local spatial analysis, and publish-ready outputs.

## Mental model

| Format | Engine | Native use |
|--------|--------|-----------|
| **SDF** (pandas + `SHAPE` + `.spatial`) | arcgis geometry | Portal I/O, publishing, network/geoenrich solvers |
| **pandas** (no geometry) | — | Tabular cleaning, schema coercion, null reports, joins |
| **GeoDataFrame** (geopandas + shapely) | shapely/GEOS | Local overlay, dissolve, projection-aware buffer, complex spatial predicates |

## Hard rules

1. **Geometry column** — always `from esri_utils._core import GEOM_COL`. Never redefine `"SHAPE"` string constant in your code.
2. **Conversions** — use `_core.to_geodataframe(sdf)` / `_core.to_sdf(gdf)`. Never manually access `sdf.spatial` to extract geometry.
3. **Lazy imports** — `geopandas` and `shapely` must be imported inside functions, never at module top level.
4. **Geometry is sticky** — tabular ops (`drop_duplicates`, `merge`, `groupby`) can silently drop `SHAPE`. Use `deliberate_drop = sdf.drop(columns=[GEOM_COL])`.
5. **CRS awareness** — never buffer/distance-compute in raw EPSG:4326. Always reproject to a projected CRS first.

## Engine choice

| Operation | SDF engine (`esri_utils.sdf`) | GeoDataFrame engine (`esri_utils.analysis`) |
|-----------|-------------------------------|-------------------------------------------|
| Spatial join | `sjoin(points, polys, op="within")` | `analysis.spatial_join(points_gdf, polys_gdf)` |
| Buffer | `buffer(sdf, distance=100, unit="meters")` | `analysis.buffer(gdf, distance=500)` |
| Dissolve | — (use arcgis SDK) | `analysis.dissolve(gdf, by="region")` |
| Reproject | `sdf.spatial.project(target_sr)` | `gdf.to_crs(3857)` |
| Cluster/aggregation | — | `analysis.aggregate_by_polygon(points, polys, agg="count")` |

**Rule of thumb**: If the data is already in a GeoDataFrame or you need
shapely predicates (intersects, within, crosses, etc.), use `analysis.*`.
If the data came from a Portal layer and will be published back, stay in SDF land.

## Cleaning (pandas)

```python
from esri_utils import cleaning

# Standardize column names
sdf = cleaning.standardize_columns(sdf)              # -> snake_case, lowercase

# Trim whitespace from string columns
sdf = cleaning.trim_strings(sdf)

# Null report — safe with SHAPE column
report = cleaning.null_report(sdf)
# DataFrame: col | null_count | null_pct | dtype
# Use this to decide which cols to drop/fill before analysis

# Deduplicate
sdf = sdf.drop_duplicates(subset=["OBJECTID"])        # keep explicit subset

# Coerce types
sdf["POP"] = pd.to_numeric(sdf["POP"], errors="coerce")
sdf["date"] = pd.to_datetime(sdf["date"], errors="coerce")
```

**Gotchas with SHAPE column**:
- `sdf.dropna(subset=[GEOM_COL])` may not work as expected — use `sdf[sdf[GEOM_COL].notna()]` instead.
- GroupBy drops SHAPE: `sdf.groupby("region").size()` is safe (no SHAPE in agg), but `sdf.groupby("region").agg({"POP": "sum"})` needs the SHAPE column handled separately.

## SDF construction

```python
from esri_utils.sdf import from_xy, from_layer, sjoin, buffer, centroid

# From xy coordinates
sdf = from_xy(df, x_column="lon", y_column="lat")             # WGS84 (default)
sdf = from_xy(df, x_column="easting", y_column="northing", sr=26910)  # UTM zone 10N

# From feature layer
sdf = from_layer(lyr, where="1=1")

# Spatial join (arcgis engine)
joined = sjoin(points_sdf, polys_sdf, how="left", op="within")

# Buffer (arcgis engine)
buffered = buffer(sdf, distance=100, unit="meters")

# Centroid
centroids = centroid(sdf)
```

## GeoDataFrame analysis

```python
from esri_utils import analysis

# Convert
gdf = analysis.to_geodataframe(sdf)

# Always reproject before distance/area/buffer
gdf = gdf.to_crs(3857)                                        # Web Mercator
# Or use local UTM for accurate area:
gdf = gdf.to_crs(26910)                                       # UTM zone 10N

# Buffer (geopandas engine)
buffered = analysis.buffer(gdf, distance=500)

# Spatial join (geopandas engine)
joined = analysis.spatial_join(points_gdf, polys_gdf, how="inner", op="intersects")

# Dissolve
dissolved = analysis.dissolve(gdf, by="region", aggfunc="sum")

# Aggregate points into polygons
counts = analysis.aggregate_by_polygon(points_gdf, polys_gdf, agg="count")

# Convert back to SDF for Portal
out_sdf = analysis.to_sdf(buffered)
```

## CRS reference

| EPSG | Name | Use case |
|------|------|----------|
| 4326 | WGS84 (lat/lon) | Raw input, web coords |
| 3857 | Web Mercator | Web maps, approximate buffer |
| 26910–26919 | UTM zones 10N–19N | Accurate distance/area for North America |
| 4269 | NAD83 | US/Canadian data |
| 3338 | Alaska Albers | Alaska statewide |
| 3978 | Canada Lambert Conformal Conic | Canada nationwide |

## Performance tips

- **Project once**: do all your analysis in one projected CRS. Repeated `.to_crs()` calls are expensive.
- **Chunk large queries**: `layers.query_to_sdf(lyr, where="1=1", chunk_size=2000)`.
- **Drop unnecessary fields**: `out_fields="NAME,POP,SHAPE"` in queries — fewer fields = faster transfer.
- **GeoDataFrame spatial index**: `gdf.sindex` accelerates spatial joins — geopandas uses it implicitly.

## Edge cases

- **Null geometries**: SDF can have `None` in SHAPE column. Filter with `sdf[sdf[GEOM_COL].notna()]`.
- **Empty geometries**: GeoDataFrame may have `Point()` or `Polygon()` with no coords. Use `gdf[~gdf.is_empty]`.
- **Multipart vs single**: `shapely.geometry.shape` handles both. Check with `gdf.geom_type`.
- **Z/M values**: arcgis may include Z/M in SHAPE. Strip with `sdf.spatial.drop_z()`.

## Acceptance

```bash
cd esri
python -c "
from esri_utils import cleaning, analysis, sdf
print('SDF/GDF modules import OK')
"
ruff check . && ruff format --check .
python -m compileall esri_utils
```
