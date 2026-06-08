Review `esri/` as a coding agent.

Focus:
- lazy imports and ArcGIS API 2.4+ compatibility
- SDF vs GeoDataFrame engine choice
- duplicate helpers that should move to `_core` or `diagnostics`
- CLI affordances developers can run before writing scripts
- docs/skills/prompts updates when behavior changes

Verify:

```bash
cd esri
ruff check .
ruff format --check .
python -m compileall esri_utils
python -m esri_utils --help
python -m esri_utils doctor
```
