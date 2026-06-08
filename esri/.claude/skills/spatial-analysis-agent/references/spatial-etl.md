# Spatial ETL Pipeline Patterns

Load when designing spatial data pipelines, choosing storage formats, tiling large datasets, streaming, parallel processing, DuckDB Spatial, or quality gates.

## Medallion architecture (bronze/silver/gold)

```python
# BRONZE — raw ingestion, one row per feature, no transforms
gdf_raw = gpd.read_file("source.geojson")
gdf_raw.to_parquet("bronze/region=west/data.parquet")

# SILVER — cleaned, validated, projected, partitioned
gdf = gpd.read_parquet("bronze/")
gdf = gdf.dropna(subset=["geometry"])
gdf = gdf[gdf.is_valid]
gdf = gdf.to_crs(5070)
gdf.to_parquet("silver/region=west/clean.parquet")

# GOLD — analysis-ready aggregates, joins, dissolved
gold = gpd.read_parquet("silver/")
gold = gold.dissolve(by="zone", aggfunc={"pop": "sum"})
gold.to_parquet("gold/zonal_stats.parquet")
```

## GeoParquet ecosystem

### GeoParquet 1.1 features

```python
# Write with GeoArrow encoding + column metadata
gdf.to_parquet("data.parquet",
    compression="zstd",
    geometry_encoding="geoarrow",     # 1.1: native Arrow geometry
    schema_version="1.1",
)

# Column projection — only load what you need
gdf = gpd.read_parquet("data.parquet",
    columns=["id", "geometry", "pop"],
)

# Row-group spatial pruning (GeoParquet 1.1: bbox per row group)
# Readers skip row groups whose bbox doesn't overlap query bbox
gdf = gpd.read_parquet("data.parquet",
    filters=[("region", "==", "west")],
)
```

### Partitioning strategies

```python
# H3 hex grid partitioning
import h3
gdf["h3_6"] = gdf.geometry.representative_point().apply(
    lambda p: h3.latlng_to_cell(p.y, p.x, 6))

# Admin boundary partitioning
gdf["region"] = gdf["state"]  # one dir per state

# Tile-based
gdf["quadkey"] = gdf.geometry.apply(lonlat_to_quadkey, zoom=10)

# Write partitioned
gdf.to_parquet("data/", partition_cols=["region"])
```

### Format benchmarks

| Format | Read 1M rows | Size | Notes |
|--------|-------------|------|-------|
| GeoJSON | ~8s | 320 MB | Simple, no schema |
| Shapefile | ~12s | 180 MB | 10-char fields, 2GB limit |
| GeoPackage | ~5s | 150 MB | SQLite, single file |
| GeoParquet | ~1s | 48 MB | Columnar, compressed, schema |
| Feather | ~0.5s | 50 MB | Fastest, no compression |

GeoParquet: **5-10x faster reads, 5-6x smaller** than GeoJSON.

## Tile-based processing

### Grid systems

```python
# H3 hex grid
import h3
cell = h3.latlng_to_cell(40.7, -74.0, 8)      # hex cell at resolution 8
children = h3.cell_to_children(cell, 9)         # sub-hexes
ring = h3.grid_disk(cell, 2)                    # 2-ring neighborhood

# S2
import s2sphere
cell_id = s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(40.7, -74.0)).parent(15)

# Quadkey — Web Mercator tile scheme
def lonlat_to_quadkey(lon, lat, zoom=10):
    import mercantile
    tile = mercantile.tile(lon, lat, zoom)
    return mercantile.quadkey(tile)
```

### Tile-based map-reduce

```python
# MAP — process each tile independently
def process_tile(tile_id):
    gdf_tile = gpd.read_parquet(f"tiles/{tile_id}.parquet")
    result = gdf_tile.dissolve()  # tile-local dissolve
    return tile_id, result

# REDUCE — merge tile results
results = [process_tile(t) for t in tile_ids]
merged = pd.concat([r for _, r in results])
final = merged.dissolve()  # final global dissolve
```

## Streaming spatial patterns

### Chunked read with pyogrio

```python
# pyogrio chunked reader — 2-10x faster than fiona
import pyogrio
for chunk in pyogrio.read_chunked("big.geojson", chunk_size=10000):
    gdf = gpd.GeoDataFrame(chunk, geometry="geometry", crs=4326)
    process(gdf)
```

### Buffer + flush

```python
buffer = []
for feat in feature_stream():
    buffer.append(feat)
    if len(buffer) >= 1000:
        gdf = gpd.GeoDataFrame(buffer, crs=4326)
        write_batch(gdf)
        buffer = []
if buffer:  # flush remainder
    gdf = gpd.GeoDataFrame(buffer, crs=4326)
    write_batch(gdf)
```

## DuckDB Spatial

```python
import duckdb
con = duckdb.connect()
con.install_extension("spatial")
con.load_extension("spatial")

# Query Parquet directly
con.sql("""
    SELECT h3_kring(geometry, 1) as neighbors,
           ST_Area(ST_Buffer(geometry, 100)) as buf_area
    FROM read_parquet('data.parquet')
    WHERE ST_Intersects(geometry, ST_GeomFromText('POLYGON((...))'))
""").fetchdf()  # → pandas DataFrame

# DuckDB ↔ geopandas round trip
gdf = con.sql("SELECT * FROM read_parquet('data.parquet')").fetchdf()
gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=4326)
```

**Performance**: DuckDB spatial join on 100M rows ~6GB RAM vs Dask ~19GB.

## Coordinate transforms

```python
from pyproj import Transformer

# Batch transform with numpy
transformer = Transformer.from_crs(4326, 5070, always_xy=True)
xs, ys = gdf.geometry.x.values, gdf.geometry.y.values
x2, y2 = transformer.transform(xs, ys)  # numpy arrays

# Rebuild geometry
gdf["geometry"] = gpd.points_from_xy(x2, y2)
gdf = gdf.set_crs(5070)
```

## Geometry simplification

```python
# Ramer-Douglas-Peucker — topology preserving
simple = gdf.geometry.simplify(tolerance=10, preserve_topology=True)

# Zoom-level adaptive tolerance
tolerance_by_zoom = {0: 1000, 5: 100, 10: 10, 15: 1}
gdf[f"geom_z{z}"] = gdf.geometry.simplify(tolerance_by_zoom[z])
```

## Spatial data quality gates

```python
def quality_gate(gdf, checks):
    for name, check in checks.items():
        passed = check(gdf)
        if not passed:
            raise ValueError(f"Quality gate FAILED: {name}")

gates = {
    "no_null_geom": lambda g: g.geometry.isna().sum() == 0,
    "has_crs": lambda g: g.crs is not None,
    "valid_geom": lambda g: g.is_valid.all(),
    "within_extent": lambda g: g.intersects(study_area).all(),
}
quality_gate(gdf, gates)
```

## Parallel processing

### concurrent.futures + tile partitions

```python
from concurrent.futures import ProcessPoolExecutor

def process_tile(quadkey):
    gdf = gpd.read_parquet(f"tiles/{quadkey}.parquet")
    return gdf.dissolve()

with ProcessPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(process_tile, tile_ids))
```

### Ray distributed

```python
import ray
import geopandas as gpd

@ray.remote
def process_shard(path):
    gdf = gpd.read_parquet(path)
    return gdf.dissolve()

futures = [process_shard.remote(p) for p in paths]
results = ray.get(futures)
final = gpd.GeoDataFrame(pd.concat(results)).dissolve()
```

## Caching & materialization

```python
import hashlib, os

def cached_transform(src_path, out_path, transform_fn):
    """Cache transform output keyed by source hash."""
    src_hash = hashlib.sha256(open(src_path, "rb").read()).hexdigest()[:16]
    cache_key = f"{out_path}.{src_hash}.parquet"
    if os.path.exists(cache_key):
        return gpd.read_parquet(cache_key)
    gdf = transform_fn(gpd.read_parquet(src_path))
    gdf.to_parquet(cache_key)
    return gdf
```

## Spatial + ML pipeline

```python
# Feature engineering from geometry
gdf["area"] = gdf.geometry.area
gdf["perimeter"] = gdf.geometry.length
gdf["compactness"] = 4 * np.pi * gdf["area"] / gdf["perimeter"] ** 2
gdf["n_vertices"] = shapely.get_num_geometries(gdf.geometry.values)

# Spatial block CV — prevents data leakage
from sklearn.model_selection import KFold
blocks = gdf.dissolve(by="block_id")
kf = KFold(n_splits=5)
for train_blocks, test_blocks in kf.split(blocks):
    train_mask = gdf["block_id"].isin(blocks.iloc[train_blocks].index)
    test_mask = gdf["block_id"].isin(blocks.iloc[test_blocks].index)
    X_train, X_test = gdf[train_mask], gdf[test_mask]
```
