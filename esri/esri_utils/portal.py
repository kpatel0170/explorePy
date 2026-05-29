"""Portal / ArcGIS Enterprise connection and admin-style helpers.

Covers the common "enterprise portal -> tools" tasks: connecting, searching
items, inventorying content/users, and inspecting web maps + their layers.

All functions accept a live ``arcgis.gis.GIS`` object so they compose cleanly.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .config import PortalConfig


def connect(cfg: PortalConfig | None = None):
    """Return a connected ``arcgis.gis.GIS``.

    >>> gis = connect()                 # uses env vars
    >>> gis = connect(PortalConfig(...)) # explicit
    """
    from arcgis.gis import GIS

    cfg = cfg or PortalConfig.from_env()
    gis = GIS(**cfg.as_gis_kwargs())
    return gis


def search_items(
    gis,
    query: str = "",
    item_type: str | None = None,
    owner: str | None = None,
    max_items: int = 1000,
) -> pd.DataFrame:
    """Search Portal content and return a tidy DataFrame.

    Example
    -------
    >>> search_items(gis, item_type="Feature Service", owner="planning_dept")
    """
    parts = [query] if query else []
    if owner:
        parts.append(f"owner:{owner}")
    q = " AND ".join(parts)

    items = gis.content.search(query=q, item_type=item_type, max_items=max_items)
    rows = [
        {
            "id": it.id,
            "title": it.title,
            "type": it.type,
            "owner": it.owner,
            "views": getattr(it, "numViews", None),
            "modified": pd.to_datetime(getattr(it, "modified", None), unit="ms", errors="coerce"),
            "url": it.homepage,
        }
        for it in items
    ]
    return pd.DataFrame(rows)


def list_users(gis, max_users: int = 1000) -> pd.DataFrame:
    """Inventory Portal users (role, level, last login)."""
    users = gis.users.search(max_users=max_users)
    rows = [
        {
            "username": u.username,
            "full_name": getattr(u, "fullName", None),
            "email": getattr(u, "email", None),
            "role": getattr(u, "role", None),
            "level": getattr(u, "level", None),
            "last_login": pd.to_datetime(getattr(u, "lastLogin", None), unit="ms", errors="coerce"),
        }
        for u in users
    ]
    return pd.DataFrame(rows)


def get_webmap_layers(gis, item_id: str) -> pd.DataFrame:
    """List operational layers (and basemaps) inside a Web Map item."""
    from arcgis.mapping import WebMap

    item = gis.content.get(item_id)
    if item is None:
        raise ValueError(f"No item found with id {item_id!r}")
    wm = WebMap(item)

    rows = []
    for lyr in wm.layers:
        d = dict(lyr) if not isinstance(lyr, dict) else lyr
        rows.append(
            {
                "title": d.get("title"),
                "layerType": d.get("layerType"),
                "url": d.get("url"),
                "visibility": d.get("visibility"),
            }
        )
    return pd.DataFrame(rows)


def clone_items(src_gis, dest_gis, item_ids: list[str], **kwargs) -> list[Any]:
    """Clone items between two portals (e.g. dev -> prod migration)."""
    items = [src_gis.content.get(i) for i in item_ids]
    items = [i for i in items if i is not None]
    return dest_gis.content.clone_items(items=items, **kwargs)


def reassign_item(gis, item_id: str, target_owner: str, target_folder: str | None = None):
    """Reassign content ownership (offboarding / re-org)."""
    item = gis.content.get(item_id)
    if item is None:
        raise ValueError(f"No item found with id {item_id!r}")
    return item.reassign_to(target_owner=target_owner, target_folder=target_folder)
