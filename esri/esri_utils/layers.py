"""Feature layer tools: query to Spatially Enabled DataFrame (SDF) and edits.

The Spatially Enabled DataFrame is the bridge between the ArcGIS API and
pandas: ``df.spatial`` gives geometry-aware methods on an ordinary DataFrame.
"""

from __future__ import annotations

import pandas as pd


def get_feature_layer(gis, item_id: str, layer_index: int = 0):
    """Return a FeatureLayer from a Feature Service item."""
    item = gis.content.get(item_id)
    if item is None:
        raise ValueError(f"No item found with id {item_id!r}")
    return item.layers[layer_index]


def layer_from_url(url: str, gis=None):
    """Build a FeatureLayer directly from its REST URL."""
    from arcgis.features import FeatureLayer

    return FeatureLayer(url, gis=gis)


def query_to_sdf(
    layer,
    where: str = "1=1",
    out_fields: str = "*",
    geometry: bool = True,
    chunk_size: int | None = None,
) -> pd.DataFrame:
    """Query a FeatureLayer into a Spatially Enabled DataFrame.

    ``chunk_size`` pages large layers past the server's maxRecordCount.

    >>> sdf = query_to_sdf(layer, where="STATE = 'CA'")
    >>> sdf.spatial.plot()
    """
    if chunk_size is None:
        fset = layer.query(where=where, out_fields=out_fields, return_geometry=geometry)
        return fset.sdf

    frames, offset = [], 0
    while True:
        fset = layer.query(
            where=where,
            out_fields=out_fields,
            return_geometry=geometry,
            result_offset=offset,
            result_record_count=chunk_size,
        )
        if len(fset.features) == 0:
            break
        frames.append(fset.sdf)
        offset += chunk_size
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def query_layer_as_featureset(layer, where: str = "1=1", out_fields: str = "*", geometry: bool = True):
    """Query a layer and return a raw ``FeatureSet`` (not SDF).

    Useful when you need to pass query results into network analysis or
    geoprocessing tools without the SDF overhead.
    """
    return layer.query(where=where, out_fields=out_fields, return_geometry=geometry)


def sdf_to_layer(sdf: pd.DataFrame, gis, title: str, **publish_kwargs):
    """Publish a Spatially Enabled DataFrame as a new hosted Feature Layer."""
    return sdf.spatial.to_featurelayer(title=title, gis=gis, **publish_kwargs)


def append_features(layer, sdf: pd.DataFrame) -> dict:
    """Append rows of an SDF to an existing FeatureLayer (bulk insert)."""
    fset = sdf.spatial.to_featureset()
    return layer.edit_features(adds=fset.features)


def update_field(layer, where: str, field: str, value) -> dict:
    """Calculate/set a field value for matching features."""
    return layer.calculate(where=where, calc_expression=[{"field": field, "value": value}])


def field_summary(layer) -> pd.DataFrame:
    """Tabular summary of a layer's schema (name, type, alias, nullable)."""
    rows = [
        {
            "name": f["name"],
            "type": f["type"],
            "alias": f.get("alias"),
            "nullable": f.get("nullable"),
            "length": f.get("length"),
        }
        for f in layer.properties.fields
    ]
    return pd.DataFrame(rows)


def delete_features(layer, where: str = "1=0") -> dict:
    """Delete features matching *where* clause.

    Use carefully — defaults to no-op (where="1=0") to prevent accidents.
    """
    return layer.edit_features(deletes=where)


def add_attachment(layer, object_id: int, file_path: str) -> dict:
    """Attach a file to a feature by its OBJECTID.

    Supported in feature services with attachments enabled.
    """
    return layer.attachments.add(oid=object_id, file_path=file_path)


def get_attachments(layer, object_id: int) -> pd.DataFrame:
    """List attachments for a feature by OBJECTID.

    Returns
    -------
    pd.DataFrame with columns: id, name, content_type, size.
    """
    attachments = layer.attachments.get_list(oid=object_id)
    rows = [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "content_type": a.get("contentType"),
            "size": a.get("size"),
        }
        for a in (attachments or [])
    ]
    return pd.DataFrame(rows)
