# ArcGIS query patterns reference

Load when querying feature layers, filtering data, or optimizing query performance.

## Always filter server-side

```python
# BAD — fetches everything
sdf = fl.query().sdf

# GOOD — filter + restrict fields
sdf = fl.query(where="STATE='CA'",
               out_fields="NAME,POP,SHAPE",
               return_geometry=True).sdf

# COUNT — no data transfer
count = fl.query(where="YEAR > 2023", return_count_only=True)

# PAGED — handle >maxRecordCount (default 2000)
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

## Spatial filters

```python
from arcgis.geometry.filters import contains, intersects, within

bbox = {"xmin": -13198303, "ymin": 4059062,
        "xmax": -13197797, "ymax": 4059421,
        "spatialReference": {"wkid": 102100}}

results = fl.query(geometry_filter=intersects(bbox, sr=102100),
                   out_fields="APN,UseType")
```

## OBJECTID chunking (very large)

```python
oids = fl.query(return_ids_only=True)["objectIds"]
for i in range(0, len(oids), 2000):
    chunk = oids[i:i+2000]
    batch = fl.query(where=f"OBJECTID>={chunk[0]} AND OBJECTID<={chunk[-1]}")
```

## out_fields best practices

- Always specify exact fields needed. Avoid `"*"` in production.
- Geometry is returned by default — set `return_geometry=False` when not needed.
- The `SHAPE` field is always included in SDF output regardless of `out_fields`.

## Performance

- Use `return_count_only=True` for fast counts
- Use `return_ids_only=True` for OBJECTID lists
- Use spatial filter to limit geographic extent
- Chunk with `result_offset` + `result_record_count` for large datasets
- Check `fl.properties.maxRecordCount` — default 2000, may be higher
- Use `result_type='standard'` for up to 32K per page on some services

## SQL injection prevention

```python
# Never concatenate user input
# BAD — user input in f-string
sdf = fl.query(where=f"NAME='{user_input}'")

# GOOD — escape single quotes
safe = user_input.replace("'", "''")
sdf = fl.query(where=f"NAME='{safe}'")
```

## Edits

```python
# Append
fl.edit_features(adds=[feature_dict_1, feature_dict_2])

# Update
fl.edit_features(updates=[modified_feature])

# Delete — default to safe no-op
fl.edit_features(deletes=[object_id_1])
```

## Error handling

```python
for attempt in range(3):
    try:
        return fl.query(**kwargs)
    except Exception as e:
        if "429" in str(e) or "too many" in str(e).lower():
            time.sleep(2 ** attempt)
        elif "invalid token" in str(e):
            gis = connect()  # fresh auth
            fl = FeatureLayer.fromitem(gis.content.get(fl.item_id))
        else:
            raise
```
