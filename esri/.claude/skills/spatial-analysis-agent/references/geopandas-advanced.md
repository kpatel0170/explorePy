# GeoPandas — Advanced Patterns

Load when doing overlay, dissolve, spatial index, CRS management, geometry validation, large-scale processing, or shapely 2.x vectorized ops.

## Spatial operations — deep patterns

### dissolve

```python
# Single field
dissolved = gdf.dissolve(by="region", aggfunc="sum")

# Multiple aggfuncs
dissolved = gdf.dissolve(by="region", aggfunc={"pop": "sum", "area": "mean"})

# Multiple dissolve fields
dissolved = gdf.dissolve(by=["region", "zone"], aggfunc="sum")

# No by — merge ALL geometries into one
merged = gdf.dissolve(aggfunc="sum")

# Method parameter
dissolved = gdf.dissolve(by="region", method="hilbert")  # spatial sort for perf
```

### overlay — all 5 how options

```python
intersection = gpd.overlay(gdf1, gdf2, how="intersection")         # both overlap
union = gpd.overlay(gdf1, gdf2, how="union")                      # all areas
symmetric_diff = gpd.overlay(gdf1, gdf2, how="symmetric_difference") # non-overlap
difference = gpd.overlay(gdf1, gdf2, how="difference")             # gdf1 minus gdf2
identity = gpd.overlay(gdf1, gdf2, how="identity")                  # gdf1 with gdf2 attrs

# Keep geometry type, make_valid
result = gpd.overlay(gdf1, gdf2, how="intersection",
                     keep_geom_type=True, make_valid=True)
```

### clip

```python
clipped = gpd.clip(gdf, mask_polygon)               # polygon mask
clipped = gpd.clip(gdf, mask_bbox)                   # GeoDataFrame with single box
clipped = gpd.clip(gdf, bbox=(xmin, ymin, xmax, ymax))  # tuple — fastest, no geometry create
```

### sjoin — all predicates

```python
sjoin = gpd.sjoin(gdf1, gdf2, how="inner", predicate="intersects")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="within")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="contains")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="crosses")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="overlaps")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="touches")
sjoin = gpd.sjoin(gdf1, gdf2, predicate="covered_by")       # 1.0+
sjoin = gpd.sjoin(gdf1, gdf2, predicate="contains_properly") # 1.0+
```

### sjoin_nearest

```python
nearest = gpd.sjoin_nearest(pts, polys, max_distance=500,
                            exclusive=True,   # exclude exact matches
                            distance_col="dist")
```

**⚠️ max_distance is in CRS units.** For geographic CRS (4326), that's degrees.

### explode — multipart to singlepart

```python
single = gdf.explode(index_parts=False)   # flat integer index
single = gdf.explode(index_parts=True)    # MultiIndex (orig_idx, part)
single = gdf.explode(ignore_index=True)   # clean 0..n-1 index
```

## Spatial index (sindex)

```python
_ = gdf.sindex  # lazy build — triggers R-tree (STRtree)

# Query single geometry
matches = gdf.sindex.query(geom, predicate="intersects")
subset = gdf.iloc[matches]

# Query batch (1.0+)
indices = gdf.sindex.query_bulk(geom_array, predicate="intersects")
```

`sindex.query()` returns positional indices (iloc). Use `gdf.iloc[matches]`.

| Method | Use | Speed |
|--------|-----|-------|
| `sindex.query(geom)` | Single geometry | Fast |
| `sindex.query_bulk(geoms)` | Array of geometries (1.0+) | Faster for batch |
| `cx[xmin:xmax, ymin:ymax]` | Bounding box filter | Fastest for rect |

```python
# cx — coordinate-based indexing (bounding box)
candidates = gdf.cx[xmin:xmax, ymin:ymax]
```

## CRS — expert patterns

### Auto-detect UTM zone

```python
gdf = gdf.set_crs(4326)                     # declare (no transform)
gdf = gdf.to_crs(gdf.estimate_utm_crs())     # auto UTM — for distance ops
```

### set_crs vs to_crs

```python
gdf.set_crs(4326)      # DECLARE CRS (no coords change) — CRS was missing
gdf.to_crs(5070)       # TRANSFORM coords — CRS was correct but wrong type
```

### Custom CRS with pyproj

```python
from pyproj import CRS
crs = CRS.from_user_input("+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84")
gdf = gdf.to_crs(crs)
```

### WKT2 vs EPSG

```python
gdf.crs  # displays as EPSG or WKT2 depending on source
gdf.crs.to_epsg()           # extract EPSG code (None if not EPSG-compatible)
gdf.crs.to_wkt("WKT2_2019")  # full WKT2 string
```

### Axis order

```python
# CRS axis order: EPSG:4326 is (lat, lon) per ISO 19111
# Shapely/x/y always use (lon, lat). Proj handles the swap internally.
```

### Deprecated init=

```python
# DONT
gdf = gdf.to_crs("+init=EPSG:4326")  # removed in PROJ 6+

# DO
gdf = gdf.to_crs("EPSG:4326")
```

## GeoSeries operations

```python
gdf.geometry.area                    # vectorized
gdf.geometry.length
gdf.geometry.centroid
gdf.geometry.bounds                  # (minx, miny, maxx, maxy)
gdf.geometry.total_bounds            # single row: (minx, miny, maxx, maxy)
gdf.geometry.representative_point()  # guaranteed inside geometry
gdf.geometry.minimum_rotated_rectangle  # oriented bounding box
gdf.geometry.convex_hull
gdf.geometry.envelope                # axis-aligned bbox
gdf.geometry.exterior                # polygon boundary as LineString
gdf.geometry.boundary
gdf.geometry.buffer(100, resolution=16)  # resolution for curved buffer
gdf.geometry.simplify(10, preserve_topology=True)
gdf.geometry.unary_union             # merge ALL into one geometry

# Pairwise set ops
gdf.geometry.intersection(other)
gdf.geometry.union(other)
gdf.geometry.difference(other)
gdf.geometry.symmetric_difference(other)
```

## Geometry validation & repair

```python
mask = ~gdf.is_valid
print(f"{mask.sum()} invalid")

# Diagnose
from shapely.validation import explain_validity
gdf[mask].geometry.apply(explain_validity)

# Repair
from shapely import make_valid
gdf.loc[mask, "geometry"] = gdf.loc[mask, "geometry"].apply(
    lambda g: make_valid(g, method="structure")  # vs "linework"
)

# buffer(0) — classic fix for self-intersections
gdf.loc[mask, "geometry"] = gdf.loc[mask, "geometry"].buffer(0)

# Simple check (LineStrings)
gdf["is_simple"] = gdf.geometry.is_simple
```

## Large-scale geopandas

### dask-geopandas

```python
import dask_geopandas as dgpd
ddf = dgpd.from_geopandas(gdf, npartitions=4)
ddf = ddf.spatial_shuffle()  # locality-aware partitioning (1.0+)
result = ddf.sjoin(other_gdf).compute()
```

### GeoParquet

```python
gdf.to_parquet("data.parquet", compression="zstd", geometry_encoding="geoarrow")
gdf = gpd.read_parquet("data.parquet",
    columns=["id", "geometry", "pop"],
    filters=[("region", "==", "west")],
)
```

### Streaming read

```python
for chunk in gpd.read_file("big.geojson", chunksize=10000):
    process(chunk)

# Filter on read (if engine supports)
gdf = gpd.read_file("big.geojson", bbox=(xmin, ymin, xmax, ymax))
gdf = gpd.read_file("big.geojson", mask=polygon)  # spatial filter
gdf = gpd.read_file("big.geojson", rows=1000)      # first N rows
```

## Shapely 2.x vectorized

```python
from shapely import (
    area, length, distance, buffer, simplify,
    intersects, contains, within, crosses, overlaps,
    from_wkt, to_wkt, from_wkb, to_wkb,
    set_precision, get_coordinates, transform,
)

# Ufuncs — operate on entire arrays
areas = area(gdf.geometry.values)
buffered = buffer(gdf.geometry.values, 100)
mask = intersects(gdf.geometry.values, target)

# I/O
wkts = to_wkt(gdf.geometry.values)
geoms = from_wkt(wkt_array)

# Precision
gdf["geometry"] = set_precision(gdf.geometry.values, grid_size=0.001)

# Coordinates as numpy
coords = get_coordinates(gdf.geometry.values)  # (N*pts, 2)

# Transform (e.g., drop Z)
gdf["geometry"] = transform(lambda x, y, *z: (x, y), gdf.geometry.values)
```

## Performance anti-patterns

```python
# DON'T
for idx, row in gdf.iterrows():
    row.geometry.area  # iterrows is 100x slower

gdf["area"] = gdf.apply(lambda r: r.geometry.area, axis=1)  # 200x slower

# DO
gdf["area"] = gdf.geometry.area
```

## I/O performance

```python
# pyogrio engine — 2-10x faster than fiona
gdf = gpd.read_file("data.geojson", engine="pyogrio")

# Use Arrow (1.0+)
gdf = gpd.read_file("data.geojson", engine="pyogrio", use_arrow=True)

# PostGIS pushdown
gdf = gpd.read_postgis(
    "SELECT * FROM parcels WHERE ST_Intersects(geom, %s)",
    con, geom_col="geom", params=(bbox_wkt,)
)
```
