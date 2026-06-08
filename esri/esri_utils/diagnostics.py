"""Developer diagnostics for environment, dependencies, and Portal readiness.

Use this module before debugging service behavior. It keeps secrets masked and
does not import heavy ArcGIS dependencies unless a caller explicitly connects.

Examples
--------
>>> from esri_utils.diagnostics import dependency_status, environment_report
>>> dependency_status()
>>> environment_report()
"""

from __future__ import annotations

from importlib import metadata, util

import pandas as pd

from .config import PortalConfig

DEFAULT_PACKAGES = {
    "arcgis": "arcgis",
    "pandas": "pandas",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "matplotlib": "matplotlib",
    "streamlit": "streamlit",
    "python-dotenv": "dotenv",
    "arcpy": "arcpy",
    "rapidfuzz": "rapidfuzz",
    "usaddress": "usaddress",
}

PACKAGE_NOTES = {
    "arcgis": "required for Portal/SDF workflows",
    "geopandas": "required for local spatial analysis",
    "shapely": "required by GeoDataFrame conversions",
    "arcpy": "ArcGIS Pro/Server conda env only",
    "rapidfuzz": "optional address_recon extra",
    "usaddress": "optional address_recon extra",
}


def dependency_status(packages: dict[str, str] | None = None) -> pd.DataFrame:
    """Return installed/version status for package import names.

    ``packages`` maps distribution name -> import name. Missing optional
    packages are reported as rows, not raised as import errors.
    """
    rows = []
    for dist_name, import_name in (packages or DEFAULT_PACKAGES).items():
        installed = util.find_spec(import_name) is not None
        try:
            version = metadata.version(dist_name)
        except metadata.PackageNotFoundError:
            version = ""
        rows.append(
            {
                "package": dist_name,
                "import_name": import_name,
                "installed": installed,
                "version": version,
                "note": PACKAGE_NOTES.get(dist_name, ""),
            }
        )
    return pd.DataFrame(rows)


def environment_report(cfg: PortalConfig | None = None) -> pd.DataFrame:
    """Return secret-safe ArcGIS connection settings as a DataFrame."""
    summary = (cfg or PortalConfig.from_env()).masked_summary()
    rows = [{"setting": key, "value": value} for key, value in summary.items()]
    return pd.DataFrame(rows)


def readiness_report(cfg: PortalConfig | None = None) -> dict[str, pd.DataFrame]:
    """Return all non-network diagnostics used by ``esri doctor``."""
    cfg = cfg or PortalConfig.from_env()
    return {
        "environment": environment_report(cfg),
        "dependencies": dependency_status(),
    }
