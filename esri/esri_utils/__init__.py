"""esri_utils — utility toolkit for ArcGIS Enterprise.

Modules
-------
_core          : shared primitives — GEOM_COL, spatial-accessor registration, SDF<->GDF.
config         : environment-driven connection settings (supports API key, token, PKI, pwd).
portal         : connect to Portal/Enterprise; item, user, web map tools.
layers         : feature layer query -> Spatially Enabled DataFrame (SDF) & edits.
sdf            : Spatially Enabled DataFrame helpers — construction, ops, export, plot.
cleaning       : pandas / SDF cleaning helpers.
analysis       : merges, spatial joins, geopandas analysis.
geocode        : forward / reverse / batch geocoding.
network        : route, service area, closest facility, OD cost matrix.
geometry       : server-side geometry ops (project, buffer, simplify, hull, etc).
admin          : ArcGIS Server service & log administration.
export         : print web maps (PDF/PNG), extract data, create service definitions.
geoenrich      : GeoEnrichment demographic & landscape data enrichment.
arcpy_db       : arcpy database-focused ops (file gdb / SDE / fields).
arcpy_aprx     : arcpy ArcGIS Pro project (.aprx) / map / layout ops.
viz            : geopandas + matplotlib visualization helpers.
fire           : Saskatchewan fire-threat clouds from NASA FIRMS + CWFIS active fire.
address_recon  : fix Optius geocoding by matching addresses to CAR / AM.

Heavy/optional deps (arcgis, arcpy, geopandas) are imported lazily inside
functions so importing this package never fails on a machine missing one of
them.
"""

__version__ = "0.4.0"

__all__ = [
    "config",
    "portal",
    "layers",
    "sdf",
    "cleaning",
    "analysis",
    "geocode",
    "network",
    "geometry",
    "admin",
    "export",
    "geoenrich",
    "arcpy_db",
    "arcpy_aprx",
    "viz",
    "fire",
    "address_recon",
]
