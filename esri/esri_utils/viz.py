"""Visualization helpers using geopandas + matplotlib."""

from __future__ import annotations


def choropleth(
    gdf,
    column: str,
    ax=None,
    cmap: str = "viridis",
    scheme: str | None = "quantiles",
    k: int = 5,
    title: str | None = None,
):
    """Thematic map of ``column``. Uses mapclassify scheme if installed."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 8))
    kwargs = dict(column=column, cmap=cmap, legend=True, ax=ax)
    try:
        gdf.plot(scheme=scheme, k=k, **kwargs)
    except Exception:  # mapclassify missing -> continuous ramp
        gdf.plot(**kwargs)
    ax.set_title(title or column)
    ax.set_axis_off()
    return ax


def categorical_map(gdf, column: str, ax=None, cmap: str = "tab20", title: str | None = None):
    """Map a categorical attribute with a discrete legend."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(column=column, categorical=True, legend=True, cmap=cmap, ax=ax)
    ax.set_title(title or column)
    ax.set_axis_off()
    return ax


def overlay_map(layers: list, colors: list[str] | None = None, ax=None, title: str | None = None):
    """Stack multiple GeoDataFrames on one axes (e.g. boundaries + points)."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 8))
    colors = colors or [None] * len(layers)
    for gdf, color in zip(layers, colors):
        gdf.plot(ax=ax, color=color, edgecolor="black", alpha=0.6)
    if title:
        ax.set_title(title)
    ax.set_axis_off()
    return ax


def save_figure(ax, path: str, dpi: int = 200) -> str:
    """Save the axes' figure to disk."""
    ax.get_figure().savefig(path, dpi=dpi, bbox_inches="tight")
    return path
