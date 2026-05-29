"""esri_utils — utility toolkit for ArcGIS Enterprise.

Modules
-------
config       : environment-driven connection settings.
portal       : connect to Portal/Enterprise; item, user, web map tools.
layers       : feature layer query -> Spatially Enabled DataFrame (SDF) & edits.
cleaning     : pandas / SDF cleaning helpers.
analysis     : merges, spatial joins, geopandas analysis.
arcpy_db     : arcpy database-focused ops (file gdb / SDE / fields).
arcpy_aprx   : arcpy ArcGIS Pro project (.aprx) / map / layout ops.
viz          : geopandas + matplotlib visualization helpers.
address_recon: fix Optius geocoding by matching addresses to CAR / AM.

Heavy/optional deps (arcgis, arcpy, geopandas) are imported lazily inside
functions so importing this package never fails on a machine missing one of
them.
"""

__version__ = "0.1.0"

__all__ = [
    "config",
    "portal",
    "layers",
    "cleaning",
    "analysis",
    "arcpy_db",
    "arcpy_aprx",
    "viz",
    "address_recon",
]
