"""End-to-end example: connect -> query -> clean -> analyze -> visualize.

Auth uses env vars (ARCGIS_URL + any of ARCGIS_API_KEY / ARCGIS_USER / ARCGIS_TOKEN / etc).

Run:
    export ARCGIS_URL=https://gis.example.com/portal
    export ARCGIS_API_KEY=APKs...
    python esri/examples/quickstart.py
"""

from __future__ import annotations

from esri_utils import analysis, cleaning, layers, viz
from esri_utils.portal import connect, search_items


def main() -> None:
    gis = connect()
    print("Connected as:", gis.properties.user.username)

    # 1. Discover feature services owned by a department.
    items = search_items(gis, item_type="Feature Service", max_items=10)
    print(items[["title", "owner"]].to_string(index=False))

    # 2. Query the first service's layer into an SDF.
    layer = layers.get_feature_layer(gis, items.iloc[0]["id"], 0)
    sdf = layers.query_to_sdf(layer, where="1=1", chunk_size=2000)

    # 3. Clean.
    sdf = cleaning.standardize_columns(sdf)
    sdf = cleaning.trim_strings(sdf)
    sdf = cleaning.drop_empty_geometries(sdf)
    print(cleaning.null_report(sdf).head())

    # 4. Analyze with geopandas (example: buffer + dissolve).
    gdf = analysis.to_geodataframe(sdf)
    buffered = analysis.buffer(gdf, distance=500)
    merged = analysis.dissolve(buffered)

    # 5. Visualize.
    ax = viz.overlay_map([merged, gdf], colors=["#cce5ff", "#003366"], title="Buffer overlay")
    viz.save_figure(ax, "buffer_overlay.png")
    print("Wrote buffer_overlay.png")


if __name__ == "__main__":
    main()
