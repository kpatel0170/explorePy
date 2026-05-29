"""Connection configuration, driven by environment variables.

Supports five auth modes (in priority order):
  1. Profile  — ARCGIS_PROFILE (stored credentials on disk)
  2. API key  — ARCGIS_API_KEY (ArcGIS Enterprise 11.4+ or AGOL)
  3. Token    — ARCGIS_TOKEN  (pre-generated short-lived token)
  4. PKI      — ARCGIS_CERT_FILE + ARCGIS_KEY_FILE
  5. User/pwd — ARCGIS_USER + ARCGIS_PASSWORD

Minimal env:
    ARCGIS_URL=https://gis.example.com/portal

Usage
-----
    from esri_utils.config import PortalConfig
    cfg = PortalConfig.from_env()
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


@dataclass
class PortalConfig:
    """Holds credentials for an ArcGIS Enterprise / Online connection.

    Auth methods (checked in this order):
    - profile        (``profile``)
    - api_key        (``api_key``)
    - token          (``token``)
    - cert + key     (``cert_file`` + ``key_file``)
    - user + pwd     (``username`` + ``password``)
    """

    url: str = ""
    username: str | None = None
    password: str | None = None
    profile: str | None = None
    api_key: str | None = None
    token: str | None = None
    cert_file: str | None = None
    key_file: str | None = None
    verify_cert: bool = True
    referer: str = "https"

    @classmethod
    def from_env(cls) -> "PortalConfig":
        url = os.getenv("ARCGIS_URL", "")
        return cls(
            url=url,
            username=os.getenv("ARCGIS_USER"),
            password=os.getenv("ARCGIS_PASSWORD"),
            profile=os.getenv("ARCGIS_PROFILE"),
            api_key=os.getenv("ARCGIS_API_KEY"),
            token=os.getenv("ARCGIS_TOKEN"),
            cert_file=os.getenv("ARCGIS_CERT_FILE"),
            key_file=os.getenv("ARCGIS_KEY_FILE"),
            verify_cert=os.getenv("ARCGIS_VERIFY_CERT", "true").lower() != "false",
            referer=os.getenv("ARCGIS_REFERER", "https"),
        )

    def as_gis_kwargs(self) -> dict:
        """Translate into keyword args for ``arcgis.gis.GIS``.

        Auth priority: profile > api_key > token > cert+key > user+pwd.
        If only *url* is set, anonymous access is used.
        """
        if self.profile:
            return {"url": self.url, "profile": self.profile, "verify_cert": self.verify_cert}

        kwargs: dict = {"url": self.url, "verify_cert": self.verify_cert}

        if self.api_key:
            kwargs["api_key"] = self.api_key
            kwargs["referer"] = self.referer
            return kwargs

        if self.token:
            kwargs["token"] = self.token
            kwargs["referer"] = self.referer
            return kwargs

        if self.cert_file:
            kwargs["cert_file"] = self.cert_file
            if self.key_file:
                kwargs["key_file"] = self.key_file
            if self.password:
                kwargs["password"] = self.password
            return kwargs

        if self.username:
            kwargs["username"] = self.username
        if self.password:
            kwargs["password"] = self.password

        return kwargs
