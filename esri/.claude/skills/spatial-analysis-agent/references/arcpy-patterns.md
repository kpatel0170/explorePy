# arcpy patterns reference

Use when the task involves arcpy operations. Load only when needed.

## Environment

```python
import arcpy

arcpy.env.workspace = r"C:\data\base.gdb"
arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "75%"
arcpy.env.XYTolerance = 0.001

# Always restore modified env
old_workspace = arcpy.env.workspace
try:
    # ... work ...
    pass
finally:
    arcpy.env.workspace = old_workspace
```

Use `in_memory` for intermediates (not final, not >500K features).

## Cursors — always with-block

```python
# Search (read) — SHAPE@XY is fastest
with arcpy.da.SearchCursor(fc, ["field1", "SHAPE@XY"],
                           where_clause="status='active'") as cursor:
    for (x, y), in cursor:
        ...

# Update (modify)
with arcpy.da.UpdateCursor(fc, ["field1", "field2"]) as cursor:
    for row in cursor:
        row[1] = row[0] * 1.5
        cursor.updateRow(row)

# Insert (create)
with arcpy.da.InsertCursor(fc, ["id", "SHAPE@"]) as cursor:
    for id_val, geom in data:
        cursor.insertRow([id_val, geom])
```

### Geometry tokens

| Token | Returns | Speed |
|-------|---------|-------|
| `SHAPE@XY` | (x, y) tuple | Fastest |
| `SHAPE@X`, `SHAPE@Y` | Individual coord | Fast |
| `SHAPE@` | Full geometry | Slow — avoid |
| `SHAPE@JSON` | GeoJSON string | Moderate |
| `SHAPE@WKT` | WKT string | Moderate |

## Error handling

```python
try:
    result = arcpy.Buffer_analysis(in_fc, out_fc, "100 Meters")
    if result.maxSeverity >= 2:
        print("ERROR:", result.getMessages(2))
except arcpy.ExecuteError:
    print("GP Error:", arcpy.GetMessages(2))
    print("Code:", arcpy.GetReturnCode())
```

### License checks

```python
if arcpy.CheckExtension("Spatial") != "Available":
    raise RuntimeError("Spatial Analyst not available")
arcpy.CheckOutExtension("Spatial")
try:
    pass  # use spatial tools
finally:
    arcpy.CheckInExtension("Spatial")
```

## Performance

- Cache `ListFields()` results — don't call inside loops
- Add indices before bulk cursor: `arcpy.AddIndex_management(fc, "field")`
- Chunk via `arcpy.da.GetOIDRanges()` for very large datasets
- Use `MakeFeatureLayer` + `SelectLayerByLocation` for repeated spatial filters
- `in_memory` workspace is faster than file GDB for intermediate results

## APRX manipulation

```python
aprx = arcpy.mp.ArcGISProject(r"C:\Projects\MyProject.aprx")
m = aprx.listMaps("Main Map")[0]
for lyr in m.listLayers():
    if lyr.isBroken:
        lyr.replaceDataSource(r"C:\NewData\base.gdb", "FILEGDB_WORKSPACE", lyr.name)
aprx.save()
del aprx  # release lock
```

## Common error codes

| Code | Meaning | Fix |
|------|---------|-----|
| 000732 | Dataset not found | Check path, workspace, spelling |
| 000728 | Field already exists | Check `ListFields()` first |
| 000210 | Cannot create output | Check overwriteOutput, permissions |
| 010067 | License error | `CheckExtension` before use |
| 030024 | Cursor lock conflict | Don't nest cursors on same dataset |

## SDE

```python
sde_conn = r"C:\Connections\Production.sde"
arcpy.env.workspace = sde_conn

# List versions
for v in arcpy.da.ListVersions(sde_conn):
    print(v.name, v.description)
```

Always use `with` for SDE cursors. Set `env.autoCommit = False` for batch ops.
