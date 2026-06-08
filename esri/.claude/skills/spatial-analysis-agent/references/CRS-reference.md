# CRS reference

Load when CRS reprojection, buffer, or distance ops are involved.

## Golden rules

1. Never buffer/distance-compute in EPSG:4326 — units are degrees, not meters.
2. Reproject ONCE at workflow start, not repeatedly.
3. Match CRS before spatial join — both sides same CRS.
4. `set_crs` declares (no transform); `to_crs` transforms — different ops.
5. Set CRS explicitly on GeoJSON reads (spec is 4326 but often loaded as None).

## Best CRS by region/operation

| Use case | EPSG | Name |
|----------|------|------|
| Web maps/display | 4326 | WGS84 |
| Web tiles | 3857 | Web Mercator |
| Distance (anywhere) | 326xx/327xx | UTM zone (use local) |
| Area (CONUS) | 5070 | NAD83 / CONUS Albers |
| Area (Europe) | 3035 | ETRS89 / LAEA Europe |
| Area (Alaska) | 3338 | Alaska Albers |
| Area (Canada) | 3978 | Canada Lambert Conformal Conic |
| Area (Australia) | 78xx | GDA2020 / MGA zones |
| Area (SK, Canada) | 26913 | UTM zone 13N |
| Area (Brazil) | 5641 | SIRGAS 2000 / Brazil Mercator |

## Decision tree

```
→ Web map display only?           → 4326 or 3857
→ Need accurate distances?        → UTM zone (326xx/327xx)
→ Need accurate areas?            → Equal-area Albers (5070/3035/3338/3978)
→ Continental CONUS analysis?     → 5070
→ Continental Europe?             → 3035
→ Canada-wide?                    → 3978
→ Global + accurate calcs?        → PostGIS geography type
→ Just checking validity?         → 4326 is fine
```

## Common mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| `buffer(100)` in 4326 | 100-degree buffer (planet-scale!) | Project → buffer → reproject back |
| Spatial join mismatched CRS | Wrong/missing joins | `gdf1.to_crs(gdf2.crs)` |
| Area calc in 4326 | Square degrees, meaningless | Equal-area CRS (5070/3035) |
| No CRS set | Ops fail silently | `gdf.set_crs(4326)` |
| Repeated `to_crs()` in loop | Slow | Done once outside loop |

## Code patterns

```python
# Safe buffer — auto-reproject
def safe_buffer(gdf, distance_meters: float):
    """Buffer in meters — auto-handles geographic CRS."""
    orig_crs = gdf.crs
    if not gdf.crs.is_projected:
        gdf = gdf.to_crs(5070)
    gdf["geometry"] = gdf.buffer(distance_meters)
    return gdf.to_crs(orig_crs)

# CRS check before spatial join
def assert_matching_crs(gdf1, gdf2):
    if gdf1.crs != gdf2.crs:
        raise ValueError(f"CRS mismatch: {gdf1.crs} vs {gdf2.crs}")

# Declare vs transform
gdf = gdf.set_crs(4326)    # CRS missing — declare (no coordinate change)
gdf = gdf.to_crs(5070)     # CRS known — transform (coordinates change)
```

## UTM zone finder

```python
def utm_zone(longitude: float) -> int:
    """Return UTM zone number (-60..+60) for longitude."""
    return int((longitude + 180) / 6) + 1

# EPSG for northern hemisphere: 32600 + zone
# EPSG for southern hemisphere: 32700 + zone
```
