# SDF — Advanced Spatially Enabled DataFrame Patterns

Load when working with `pd.DataFrame.spatial` (arcgis GeoAccessor). Covers creation, `.spatial` accessor deep-dive, spatial index, geometry engine, CRS, round-trip fidelity, performance, and publishing.

## Imports

```python
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor, FeatureSet
from arcgis.gis import GIS
from arcgis.geometry import SpatialReference, Geometry
from arcgis.geometry.filters import intersects, contains, within
```

`GeoAccessor` import registers `.spatial` on `pd.DataFrame` and `.geom` on `pd.Series`.

## Creation patterns

### from_xy — always specify sr

```python
sdf = pd.DataFrame.spatial.from_xy(df, x_column="lon", y_column="lat", sr=4326)
```

sr accepts: WKID int, `SpatialReference`, or dict. Without sr, CRS is unset.

### from_layer vs from_featureclass

```python
sdf = pd.DataFrame.spatial.from_layer(feature_layer)         # web layer
sdf = pd.DataFrame.spatial.from_featureclass("/path/gdb/fc") # local (needs arcpy/fiona)
```

`from_layer` reads ALL features — filter with SQL on the layer first:
```python
fset = fl.query(where="POP>100000", out_fields="NAME,POP"); sdf = fset.sdf
```

### from_geodataframe — bug in 2.4.1

```python
sdf = pd.DataFrame.spatial.from_geodataframe(gdf)
# arcgis 2.4.1: CRS from GDF is ignored (always 4326). Workaround:
sdf = pd.DataFrame.spatial.from_geodataframe(gdf)
sdf.spatial.sr = gdf.crs.to_wkt()  # 2.4.2+: fixed
```

### Manual SHAPE construction — 2-5x slower than from_xy

```python
df["SHAPE"] = [Point({"x": r.x, "y": r.y, "spatialReference": {"wkid": 4326}})
               for _, r in df.iterrows()]
sdf = pd.DataFrame.spatial.from_df(df, geometry_column="SHAPE")
```

## Spatial accessor reference

### Properties

```python
sdf.spatial.geometry_type       # "Point", "Polygon", etc.
sdf.spatial.true_centroid       # single Point for whole dataset centroid
sdf.spatial.full_extent         # [xmin, ymin, xmax, ymax]
sdf.spatial.bbox                # same as full_extent
sdf.spatial.sr                  # SpatialReference object
sdf.spatial.areas               # pd.Series of polygon areas (SR units)
sdf.spatial.lengths             # pd.Series of line lengths (SR units)
sdf.spatial.hulls               # pd.Series of convex hull geometries
```

### Methods

```python
sdf.spatial.buffer(100)         # distance in SR units — returns new SDF
sdf.spatial.project(3857)       # reproject — returns new SDF
sdf.spatial.centroid()          # per-row centroid — returns new SDF
sdf.spatial.simplify(10)        # simplify — returns new SDF
sdf.spatial.convex_hull()       # returns new SDF
sdf.spatial.boundary()          # returns boundary geometries
```

Naming: `.spatial.centroid` (property, single Point) vs `.spatial.centroid()` (method, per-row).

### .geom accessor (pd.Series of geometry)

```python
sdf.SHAPE.geom.distance_to(other_sdf.SHAPE.iloc[0])  # vectorized distance
sdf.SHAPE.geom.buffer(100)
```

### Relationship predicates

```python
sdf.spatial.relationship(other_geom, "intersects")  # boolean Series
sdf.spatial.relationship(other_geom, "contains")
sdf.spatial.relationship(other_geom, "within")
sdf.spatial.relationship(other_geom, "crosses")
sdf.spatial.relationship(other_geom, "overlaps")
sdf.spatial.relationship(other_geom, "touches")
```

## Spatial join

```python
joined = left_sdf.spatial.join(
    right_sdf,
    how="inner",              # "inner" | "left" | "right"
    op="intersects",          # "intersects" | "contains" | "within" | etc.
    left_tag="left",
    right_tag="right",
)
```

**Requirements**: matching SR, no null geometries. Fix:
```python
assert left.spatial.sr == right.spatial.sr
right = right.dropna(subset=["SHAPE"])
```

## Spatial index

```python
# Quadtree (default)
si = sdf.spatial.sindex("quadtree", reset=False)

# R-tree (better for skewed distributions)
si = sdf.spatial.sindex("r-tree", reset=False)

# Query
indices = si.intersect(bbox=(xmin, ymin, xmax, ymax))
subset = sdf.iloc[list(indices)]
```

| Index | Best for | Build speed | Query speed |
|-------|----------|-------------|-------------|
| Quadtree | Evenly distributed, dynamic | Faster | Good |
| R-tree | Skewed, overlapping | Slower | Better |

Build once, reuse. Rebuild with `reset=True` after geometry mutations.
Index is NOT preserved across `pd.concat()`, `.copy()`, or serialization.

## Geometry engine

```python
import arcgis
arcgis.env.geometry_engine = "shapely"    # or "arcpy"
```

| | Shapely | arcpy |
|--|---------|-------|
| Speed | Faster (C ext) | Slower |
| CRS | EPSG via pyproj | Full WKID + WKT |
| Curves | Not supported | Supported |
| Platform | Any | Windows only |
| License | BSD | Proprietary |

```python
# Access native objects
sdf.SHAPE.iloc[0].as_shapely  # → shapely geometry
sdf.SHAPE.iloc[0].as_arcpy    # → arcpy geometry (Windows only)
```

## CRS management

```python
sr = sdf.spatial.sr; sr["wkid"]   # 4326
sdf_proj = sdf.spatial.project(3857)  # local engine (free)

# Server-side project (uses credits)
from arcgis.geometry import project
project(geometries=sdf["SHAPE"].tolist(), in_sr=4326, out_sr=3857, gis=gis)

# Set/reassign geometry
sdf.spatial.set_geometry("SHAPE", sr=4326)  # mutates in-place
```

WKID for standard SRs. WKT for custom SRs.

## Round-trip fidelity

```python
# SDF → FeatureSet → GeoJSON
fset = sdf.spatial.to_featureset()
geojson_str = fset.to_geojson

# GeoJSON → FeatureSet → SDF
fset2 = FeatureSet.from_geojson(geojson_str)
sdf2 = fset2.sdf
```

**What gets lost**: DateTime→epoch, field type info, true curves→linear, Z/M (if not queried with `return_z=True`).

### Null geometry handling

```python
sdf_clean = sdf.dropna(subset=["SHAPE"])  # before join, sindex, relationship
```

### Field name sanitization

```python
sdf.spatial.sanitize_column_names(inplace=True)  # shapefile-safe (10 chars)
# Pre-2.0 mutated caller. Use copy:
sdf.copy().spatial.sanitize_column_names(inplace=True)
```

## Publishing

```python
# Publish as feature layer
lyr = sdf.spatial.to_featurelayer(title="my_layer", gis=gis,
                                   tags=["tag"], folder="scratch")

# Overwrite (arcgis 2.1+)
lyr = sdf.spatial.to_featurelayer(title="my_layer", overwrite=True,
    service={"featureServiceId": "existing_id", "layer": 0})
```

For large overwrites (80k+ features), truncate + append instead:
```python
flc.manager.truncate()
for i in range(0, len(sdf), 200):
    fl.edit_features(adds=sdf.iloc[i:i+200].spatial.to_featureset().features)
```

### to_featureclass

```python
sdf.copy().spatial.to_featureclass("/path/out.shp")         # needs pyshp
sdf.spatial.to_featureclass("/path/gdb.gdb/fc")                # needs arcpy
```

## Performance

| Operation | 10k pts | 100k pts | 1M pts |
|-----------|---------|----------|--------|
| `from_xy()` | 0.1s | 0.8s | 8s |
| `.buffer()` (shapely) | 0.05s | 0.5s | 5s |
| `.project()` (shapely) | 0.1s | 1s | 12s |
| `.sindex(quadtree)` | 0.02s | 0.2s | 2s |
| `.join()` (2 × 10k) | 0.5s | 5s | — |
| `to_featurelayer()` | 5s | 30s | 5min+ |

### Chunked processing

```python
def process_large(sdf, chunk_size=50000):
    results = []
    for i in range(0, len(sdf), chunk_size):
        chunk = sdf.iloc[i:i+chunk_size].copy()
        results.append(process(chunk))
    return pd.concat(results, ignore_index=True)
```

## Visualization

```python
m = Map()
sdf.spatial.plot(map_widget=m, renderer_type='c',
                 col='POPULATION', method='esriClassifyNaturalBreaks',
                 class_count=5, cmap='viridis', alpha=0.7)
```

Renderer types: `'s'` (simple), `'u'` (unique value), `'c'` (class breaks), `'h'` (heatmap).

## Error troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot unpack non-iterable NoneType` | Null geom in spatial join | `dropna(subset=["SHAPE"])` |
| `.spatial` not available | GeoAccessor not registered | `from arcgis.features import GeoAccessor` |
| CRS reset to 4326 | `from_geodataframe` bug in 2.4.1 | Manually set `sdf.spatial.sr` |
| Field names lowercased | `sanitize_columns=True` default | Explicit `sanitize_columns=False` |
| `to_featurelayer` creates duplicates | Known bug | Use truncate + append workaround |
