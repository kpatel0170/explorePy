"""Print / export / extraction: web maps to PDF/PNG and data extraction.

Wraps the Enterprise ``PrintingTools`` GPService (``Export Web Map Task``) and
the ``extract_data`` analysis tool.  These are deployed automatically in the
``Utilities`` folder of every ArcGIS Enterprise server.

Usage
-----
    from esri_utils.export import export_web_map, extract_data

    export_web_map(gis, web_map_item, fmt="PDF", out_path="output.pdf")
    extracted = extract_data(gis, input_layer, extent=extent_sdf)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# --------------------------------------------------------------------------- #
# Print / Export Web Map
# --------------------------------------------------------------------------- #
def get_print_templates(gis) -> pd.DataFrame:
    """List available print layout templates from the PrintingTools service.

    Returns
    -------
    pd.DataFrame with columns: label, format, layout.
    """
    helpers = gis.properties.get("helperServices", {})
    pt = helpers.get("printTask", {})
    templates = pt.get("templates", [])
    rows = [
        {
            "label": t.get("label"),
            "format": t.get("format"),
            "layout": t.get("layout"),
        }
        for t in templates
    ]
    return pd.DataFrame(rows)


def export_web_map(
    gis,
    web_map_id: str | None = None,
    web_map_json: dict[str, Any] | None = None,
    fmt: str = "PDF",
    layout: str = "MAP_ONLY",
    template_label: str | None = None,
    out_path: str | Path | None = None,
    dpi: int = 200,
    georeference: bool = True,
    **export_kwargs: Any,
) -> str | bytes:
    """Export a web map to PDF, PNG, JPEG, or SVG via the PrintingTools service.

    Provide either *web_map_id* (Portal item ID) or *web_map_json* (inline
    web map definition).

    Parameters
    ----------
    gis : GIS
        Connected GIS.
    web_map_id : str, optional
        Item ID of a Web Map in Portal.
    web_map_json : dict, optional
        Inline web map JSON (use instead of *web_map_id*).
    fmt : str
        ``"PDF"``, ``"PNG32"``, ``"PNG8"``, ``"JPG"``, ``"SVG"``, ``"GIF"``.
        Default ``"PDF"``.
    layout : str
        ``"MAP_ONLY"`` (default) or named layout size (e.g. ``"A4 Landscape"``,
        ``"Letter ANSI A Portrait"``).  See *get_print_templates* for options.
    template_label : str, optional
        Override the layout with a specific template label (advanced).
    out_path : str | Path, optional
        Write to file.  If omitted, returns raw bytes.
    dpi : int
        Output resolution (default 200).
    georeference : bool
        Embed georeference info in PDF (default True).
    **export_kwargs
        Passed through to the print task.

    Returns
    -------
    str (path) if *out_path* was given, else bytes of the exported file.
    """
    from arcgis.map import Map

    if web_map_id and web_map_json:
        raise ValueError("Provide either web_map_id or web_map_json, not both.")
    if not web_map_id and not web_map_json:
        raise ValueError("Either web_map_id or web_map_json is required.")

    if web_map_id:
        item = gis.content.get(web_map_id)
        if item is None:
            raise ValueError(f"No Web Map found with id {web_map_id!r}")
        wm = Map(item)
    else:
        wm = Map(web_map_json)

    params = {
        "format": fmt,
        "layout": layout,
        "dpi": dpi,
        "georefInfo": georeference,
    }
    if template_label:
        params["template_label"] = template_label
    params.update(export_kwargs)

    if not hasattr(wm, "print_map"):
        raise AttributeError(
            "This arcgis.map.Map has no 'print_map' method — your ArcGIS API for "
            "Python build may expose printing differently. Check the version's docs."
        )
    result = wm.print_map(gis=gis, print_params=params)

    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(result, "write"):
            result.write(str(out_path))
        else:
            out_path.write_bytes(result if isinstance(result, bytes) else result.encode())
        return str(out_path)

    return result if isinstance(result, bytes) else result.encode()


# --------------------------------------------------------------------------- #
# Data Extraction
# --------------------------------------------------------------------------- #
def extract_data(
    gis,
    input_layer,
    extent: pd.DataFrame | None = None,
    clip_geometry: str | None = None,
    output_name: str | None = None,
    format: str = "FeatureSet",
) -> Any:
    """Extract features from a layer, optionally clipped to an extent.

    Wraps ``arcgis.features.analysis.extract_data``.

    Parameters
    ----------
    gis : GIS
        Connected GIS.
    input_layer : Item | FeatureLayer | str
        Source layer (item ID, FeatureLayer, or URL).
    extent : pd.DataFrame, optional
        SDF with a single row containing a SHAPE polygon to clip by.
        If omitted, extracts all features.
    clip_geometry : str, optional
        ``"POLYGON"`` or ``"ENVELOPE"``.
    output_name : str, optional
        Name for the output feature service / item.
    format : str
        Output format: ``"FeatureSet"`` (default), ``"Shapefile"``,
        ``"CSV"``, ``"FileGeodatabase"``.

    Returns
    -------
    FeatureLayer item (if output_name set) or FeatureSet.
    """
    from arcgis.features.analysis import extract_data as _extract

    return _extract(
        input_layer=input_layer,
        extent=extent,
        clip_geometry=clip_geometry,
        output_name=output_name,
        format=format,
        gis=gis,
    )


# --------------------------------------------------------------------------- #
# Create Service Definition
# --------------------------------------------------------------------------- #
def create_service_definition(
    gis,
    title: str,
    service_type: str = "FeatureServer",
    capabilities: str = "Query,Create,Update,Delete,Uploads,Editing",
    max_record_count: int = 2000,
    tags: str | list[str] | None = None,
    snippet: str = "",
) -> Any:
    """Create an empty hosted feature service or map service definition.

    Useful for programmatic service provisioning before loading data.

    Parameters
    ----------
    gis : GIS
        Connected GIS with publishing privileges.
    title : str
        Service title and item name.
    service_type : str
        ``"FeatureServer"`` (default) or ``"MapServer"``.
    capabilities : str
        Comma-separated capabilities string.
    max_record_count : int
        Max records returned per query.
    tags : str | list[str], optional
        Search tags.
    snippet : str
        Short description.

    Returns
    -------
    Item — the new service item in Portal.
    """
    tags_str = tags if isinstance(tags, str) else ",".join(tags or [])
    item = gis.content.create_service(
        name=title,
        service_type=service_type.lower().replace("server", ""),
        capabilities=capabilities,
        max_record_count=max_record_count,
        tags=tags_str,
        snippet=snippet,
    )
    return item
