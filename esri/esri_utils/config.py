"""Connection configuration, driven by environment variables.

Set these in your shell or a local .env (never commit secrets):

    ARCGIS_URL=https://gis.example.com/portal
    ARCGIS_USER=portaladmin
    ARCGIS_PASSWORD=********
    # OR for token / profile based auth:
    ARCGIS_PROFILE=my_profile

Usage
-----
    from esri_utils.config import PortalConfig
    cfg = PortalConfig.from_env()
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


@dataclass
class PortalConfig:
    """Holds credentials for an ArcGIS Enterprise / Online connection."""

    url: str
    username: str | None = None
    password: str | None = None
    profile: str | None = None
    verify_cert: bool = True

    @classmethod
    def from_env(cls) -> "PortalConfig":
        url = os.getenv("ARCGIS_URL")
        if not url:
            raise ValueError(
                "ARCGIS_URL is not set. Export ARCGIS_URL (and credentials) "
                "or pass a PortalConfig explicitly."
            )
        return cls(
            url=url,
            username=os.getenv("ARCGIS_USER"),
            password=os.getenv("ARCGIS_PASSWORD"),
            profile=os.getenv("ARCGIS_PROFILE"),
            verify_cert=os.getenv("ARCGIS_VERIFY_CERT", "true").lower() != "false",
        )

    def as_gis_kwargs(self) -> dict:
        """Translate into keyword args accepted by ``arcgis.gis.GIS``."""
        if self.profile:
            return {"profile": self.profile, "verify_cert": self.verify_cert}
        kwargs: dict = {"url": self.url, "verify_cert": self.verify_cert}
        if self.username:
            kwargs["username"] = self.username
        if self.password:
            kwargs["password"] = self.password
        return kwargs
