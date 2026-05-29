"""ArcGIS Enterprise server and portal administration.

Covers the most common admin tasks: listing/starting/stopping services,
publishing, querying logs, managing data stores, and inspecting machines.

Requires administrative privileges on the Enterprise connection.

Usage
-----
    from esri_utils.admin import list_services, start_service, query_logs

    services = list_services(gis)
    start_service(gis, "MyService", "MapServer")
    logs = query_logs(gis, levels="SEVERE")
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _server(gis):
    """Return the first federated ArcGIS Server admin object."""
    servers = gis.admin.servers.list()
    if not servers:
        raise RuntimeError("No ArcGIS Servers found in this Enterprise.")
    return servers[0]


# --------------------------------------------------------------------------- #
# Services
# --------------------------------------------------------------------------- #
def list_services(gis, folder: str | None = None) -> pd.DataFrame:
    """Inventory all services across (optionally) a specific folder.

    Parameters
    ----------
    gis : GIS
        Connected GIS with admin privileges.
    folder : str, optional
        Folder name (default: root + all folders).

    Returns
    -------
    pd.DataFrame with columns: folder, name, type, status, description
    """
    srv = _server(gis)
    rows: list[dict[str, Any]] = []

    targets = [folder] if folder else _resolve_folders(srv)
    for fol in targets:
        for svc in srv.services.list(folder=fol):
            rows.append(
                {
                    "folder": fol,
                    "name": svc.properties.get("serviceName"),
                    "type": svc.properties.get("type"),
                    "status": svc.properties.get("status", "unknown"),
                    "description": svc.properties.get("description", ""),
                }
            )
    return pd.DataFrame(rows)


def _resolve_folders(srv) -> list[str]:
    """Return [root] + all sub-folders."""
    folders = ["/"] + [f for f in srv.services.folders if f != "/"]
    return folders


def service_exists(gis, name: str, service_type: str, folder: str = "/") -> bool:
    """Check whether a named service exists on the server."""
    srv = _server(gis)
    return srv.services.exists(name, service_type, folder)


def start_service(gis, name: str, service_type: str, folder: str = "/") -> bool:
    """Start a stopped service.

    Returns True if the start succeeded.
    """
    srv = _server(gis)
    svc = _get_service(srv, name, service_type, folder)
    if svc is None:
        raise ValueError(f"Service {name!r} ({service_type}) not found in {folder}")
    return svc.start()


def stop_service(gis, name: str, service_type: str, folder: str = "/") -> bool:
    """Stop a running service.

    Returns True if the stop succeeded.
    """
    srv = _server(gis)
    svc = _get_service(srv, name, service_type, folder)
    if svc is None:
        raise ValueError(f"Service {name!r} ({service_type}) not found in {folder}")
    return svc.stop()


def restart_service(gis, name: str, service_type: str, folder: str = "/") -> bool:
    """Restart a service (stop then start).

    Returns True if both operations succeeded.
    """
    from time import sleep

    stopped = stop_service(gis, name, service_type, folder)
    if not stopped:
        return False
    sleep(2)
    return start_service(gis, name, service_type, folder)


def _get_service(srv, name: str, service_type: str, folder: str):
    """Look up a Service object by name+type+folder."""
    for svc in srv.services.list(folder=folder):
        props = svc.properties
        if props.get("serviceName") == name and props.get("type") == service_type:
            return svc
    return None


def get_service_properties(gis, name: str, service_type: str, folder: str = "/") -> dict:
    """Return the full properties dict of a service."""
    srv = _server(gis)
    svc = _get_service(srv, name, service_type, folder)
    if svc is None:
        raise ValueError(f"Service {name!r} ({service_type}) not found in {folder}")
    return dict(svc.properties)


def publish_service_definition(
    gis,
    sd_path: str,
    folder: str | None = None,
    config: dict | None = None,
) -> Any:
    """Publish a service from a .sd file (service definition).

    Service definitions are authored in ArcGIS Pro and contain both the
    cartographic definition and packaged data.

    Parameters
    ----------
    gis : GIS
        Connected GIS with admin privileges.
    sd_path : str
        Path to the .sd file on the server machine.
    folder : str, optional
        Target folder on the server.
    config : dict, optional
        Additional service configuration overrides.

    Returns
    -------
    Service object for the published service.
    """
    srv = _server(gis)
    return srv.services.publish_sd(sd_file=sd_path, folder=folder, service_config=config)


# --------------------------------------------------------------------------- #
# Logs
# --------------------------------------------------------------------------- #
def query_logs(
    gis,
    levels: str = "WARNING",
    start_time: str | None = None,
    end_time: str | None = None,
    max_messages: int = 100,
    filter_code: str | None = None,
) -> pd.DataFrame:
    """Query ArcGIS Server logs.

    Parameters
    ----------
    gis : GIS
        Connected GIS with admin privileges.
    levels : str
        ``"SEVERE"``, ``"WARNING"``, ``"INFO"``, ``"FINE"``, ``"DEBUG"``.
    start_time : str, optional
        ISO format start (default: 24h ago).
    end_time : str, optional
        ISO format end (default: now).
    max_messages : int
        Max log entries to return (default 100).
    filter_code : str, optional
        Filter by code pattern (e.g. ``"Invalid"``, ``"001442"``).

    Returns
    -------
    pd.DataFrame with columns: time, level, source, message, code.
    """
    srv = _server(gis)
    logs = srv.logs
    raw = logs.query(
        levels=levels,
        start_time=start_time,
        end_time=end_time,
        num_messages=max_messages,
        filter_code=filter_code,
    )
    messages = raw if isinstance(raw, list) else raw.get("logMessages", [])
    rows = [
        {
            "time": m.get("time"),
            "level": m.get("level"),
            "source": m.get("source"),
            "message": m.get("message"),
            "code": m.get("code"),
        }
        for m in messages
    ]
    return pd.DataFrame(rows)


def clear_logs(gis) -> bool:
    """Clear all server log entries."""
    srv = _server(gis)
    return srv.logs.clear()


# --------------------------------------------------------------------------- #
# Data Stores
# --------------------------------------------------------------------------- #
def list_data_stores(gis) -> pd.DataFrame:
    """Inventory registered data stores on the server.

    Returns
    -------
    pd.DataFrame with columns: name, type, path, id.
    """
    srv = _server(gis)
    stores = srv.datastores.list()
    rows = [
        {
            "name": s.name,
            "type": s.type,
            "path": s.path,
            "id": s.id,
        }
        for s in stores
    ]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Machines
# --------------------------------------------------------------------------- #
def list_machines(gis) -> pd.DataFrame:
    """List all server machines and their status.

    Returns
    -------
    pd.DataFrame with columns: name, platform, status, cores, ram_mb.
    """
    srv = _server(gis)
    machines = srv.machines.list()
    rows = [
        {
            "name": m.name,
            "platform": m.platform,
            "status": m.status,
            "cores": m.properties.get("numCores", "N/A"),
            "ram_mb": m.properties.get("memory", "N/A"),
        }
        for m in machines
    ]
    return pd.DataFrame(rows)
