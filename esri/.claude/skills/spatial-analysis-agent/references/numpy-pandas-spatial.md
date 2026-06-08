# NumPy + Pandas for Spatial Data Workflows

Load when doing memory optimization, vectorized geometry ops, coordinate arrays, groupby dissolves, spatiotemporal panel data, or Parquet/Feather I/O.

## Memory optimization

### Profile first

```python
gdf.info(memory_usage="deep")
mem = gdf.memory_usage(deep=True).sum() / 1e6  # MB
```

`object` dtype columns are the #1 memory sink (full Python pointers).

### Downcast numerics

```python
def downcast(df):
    for col in df.select_dtypes("int64"):
        cmin, cmax = df[col].min(), df[col].max()
        for t in [np.int8, np.int16, np.int32]:
            if cmin >= np.iinfo(t).min and cmax <= np.iinfo(t).max:
                df[col] = df[col].astype(t); break
    for col in df.select_dtypes("float64"):
        df[col] = pd.to_numeric(df[col], downcast="float")
    return df
```

int64→int8 = **8× smaller**. float64→float32 = **2× smaller**.

### Categoricals for low-cardinality strings

```python
for col in ["state", "land_use", "zone"]:
    if col in gdf.columns:
        gdf[col] = gdf[col].astype("category")
```

### Sparse for null-heavy columns (>60% NaN)

```python
from pandas.arrays import SparseArray
gdf["nullable_metric"] = SparseArray(gdf["nullable_metric"], fill_value=np.nan)
```

### Nullable int/bool (keep NaN without float64)

```python
gdf["population"] = pd.array(gdf["population"], dtype=pd.Int32Dtype())
gdf["flag"] = pd.array(gdf["flag"], dtype=pd.BooleanDtype())
```

### Chunked read with dtypes

```python
dtypes = {"fid": "int32", "state": "category", "pop": "float32"}
chunks = [c for c in pd.read_csv("big.csv", chunksize=50_000, dtype=dtypes)]
df = pd.concat(chunks)
```

## Vectorized ops — concrete benchmarks

### Geometry ops: apply() vs vectorized

```python
# BAD — Python loop per row, 200x slower
gdf["area"] = gdf.apply(lambda r: r.geometry.area, axis=1)

# GOOD — C-level vectorized
gdf["area"] = gdf.geometry.area
```

Benchmark: 1M rows → `apply` ~8s, vectorized ~0.04s.

### Shapely 2.x ufuncs on numpy arrays

```python
from shapely import area, length, buffer, distance, intersects

gdf["area"] = area(gdf.geometry.values)
gdf["buf"] = buffer(gdf.geometry.values, 100)
mask = intersects(gdf.geometry.values, target_poly)
```

Shapely 2.x exposes GEOS ops as numpy ufuncs — zero Python looping.

### np.where() for conditional geometry

```python
gdf["buf"] = np.where(
    gdf["population"] > 1_000_000,
    buffer(gdf.geometry.values, 5000),
    buffer(gdf.geometry.values, 1000),
)
```

### np.select() for multi-class

```python
conds = [gdf["area"] < 1000, gdf["area"] < 10000, gdf["area"] >= 10000]
choices = ["small", "medium", "large"]
gdf["class"] = np.select(conds, choices, default="unknown")
```

### Boolean indexing — vectorized beats apply

```python
# FAST — vectorized
mask = gdf.geometry.area > 5000; subset = gdf[mask]

# SLOW — row-by-row
subset = gdf[gdf.apply(lambda r: r.geometry.area > 5000, axis=1)]
```

## Coordinate arrays with numpy

### Extract x/y

```python
xs = gdf.geometry.x.values     # numpy float64
ys = gdf.geometry.y.values
coords = np.column_stack([xs, ys])  # (N, 2)
```

### Distance matrices (scipy)

```python
from scipy.spatial.distance import cdist
ca = np.column_stack([gdf_a.geometry.x, gdf_a.geometry.y])
cb = np.column_stack([gdf_b.geometry.x, gdf_b.geometry.y])
dist_matrix = cdist(ca, cb, metric="euclidean")  # (N, M)
```

### KDTree for nearest-neighbor (O(n log n) vs O(n²))

```python
from scipy.spatial import KDTree
tree = KDTree(coords_b)
dists, idxs = tree.query(coords_a, k=1)  # 1000x faster than brute force
gdf_a["nearest_idx"] = idxs
gdf_a["nearest_dist"] = dists
```

### Bounding-box filter with numpy

```python
xs, ys = gdf.geometry.x.values, gdf.geometry.y.values
mask = (xs >= xmin) & (xs <= xmax) & (ys >= ymin) & (ys <= ymax)
gdf_bbox = gdf.iloc[mask]  # microseconds for millions of points
```

## groupby + agg for spatial summary

### Dissolve via unary_union

```python
from shapely.ops import unary_union
dissolved = gdf.groupby("region", as_index=False)["geometry"] \
    .agg(lambda g: unary_union(g))
result = gpd.GeoDataFrame(dissolved, geometry="geometry", crs=gdf.crs)
```

### Multi-agg: tabular + geometry

```python
summary = gdf.groupby("zone").agg(
    count=("fid", "count"),
    pop_sum=("population", "sum"),
    geom=("geometry", lambda g: unary_union(g)),
)
result = gpd.GeoDataFrame(summary, geometry="geom", crs=gdf.crs)
```

### transform for zonal stats

```python
zone_mean = gdf.groupby("zone")["population"].transform("mean")
gdf["pop_deviation"] = gdf["population"] - zone_mean

zone_area = gdf.groupby("zone")["geometry"].transform(
    lambda g: unary_union(g).area)
gdf["pct_of_zone"] = gdf.geometry.area / zone_area * 100
```

## Spatiotemporal (panel data)

### MultiIndex: (time, location)

```python
gdf = gdf.set_index(["timestamp", "location_id"]).sort_index()
gdf_slice = gdf.loc[pd.IndexSlice["2025-01":"2025-03", :], :]
gdf_one = gdf.loc[pd.IndexSlice[:, "loc_42"], :]
```

### Resample + aggregate

```python
monthly = gdf.groupby(level="location_id").resample("ME", level="timestamp").agg(
    pop_mean=("population", "mean"),
    geom_union=("geometry", lambda g: unary_union(g)),
)
```

### Lag/shift features

```python
gdf["pop_lag1"] = gdf.groupby(level="location_id")["population"].shift(1)
gdf["pop_pct"] = gdf.groupby(level="location_id")["population"].pct_change()
```

### Rolling windows

```python
gdf["pop_roll3"] = gdf.groupby(level="location_id")["population"] \
    .rolling(3, min_periods=1).mean().values
```

### merge_asof — nearest temporal before spatial join

```python
weather = weather.sort_values("ts")
obs = obs.sort_values("ts")
merged = pd.merge_asof(obs, weather, on="ts", by="station_id",
                        tolerance=pd.Timedelta("1h"), direction="nearest")
result = gpd.sjoin(merged, admin_bounds, predicate="within")
```

## I/O performance

### Format benchmarks

| Format | Read 1M rows | Size | Compression | Schema |
|--------|-------------|------|-------------|--------|
| CSV | ~3s | 250 MB | None | No |
| Shapefile | ~12s | 180 MB | None | Weak |
| GeoJSON | ~8s | 320 MB | None | No |
| Parquet | ~0.8s | 45 MB | Zstd | Yes |
| Feather | ~0.5s | 50 MB | LZ4 | Yes |
| GeoParquet | ~1s | 48 MB | Zstd | Yes |

Parquet: **4-6x faster read, 5x smaller** than CSV.

### Parquet — column + row-group pushdown

```python
gdf.to_parquet("intermediate.parquet", compression="zstd")
subset = gpd.read_parquet("intermediate.parquet",
    columns=["fid", "geometry", "pop"],
    filters=[("region", "==", "west")],
)
```

### Feather — fastest round-trip

```python
gdf.to_feather("temp.feather", compression="lz4")
gdf_back = gpd.read_feather("temp.feather")
```

## Performance: tool selection

| Operation | Tool | Speedup vs apply |
|-----------|------|-----------------|
| Geometry area/length | `gdf.geometry.area` | 100-300x |
| Conditional geometry | `np.where()`, `np.select()` | 50-100x |
| Nearest neighbor | `scipy.spatial.KDTree` | 1000x vs brute force |
| Multi-condition filter | `df.query()` | 1.5-2x |
| Dissolve + aggregate | `groupby.agg(unary_union)` | 10x |
| Temporal align + spatial | `merge_asof` + `sjoin` | 100x |
| Lag/shift features | `groupby.shift()` | 100x |
| I/O intermediate | Parquet/Feather | 5-10x vs CSV |
| Memory | Downcast + categorical | 2-8x reduction |
