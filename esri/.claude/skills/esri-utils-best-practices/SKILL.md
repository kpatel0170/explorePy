---
name: esri-utils-best-practices
description: "Code review and quality standards for the esri_utils toolkit: verify lazy-import discipline, SDF vs GeoDataFrame engine choice, geometry column centralization, ArcGIS 2.4+ API compatibility, CLI ergonomics, documentation accuracy, security (no secrets in logs), dry-run patterns for destructive ops, and AGENTS.md/skill alignment. Use this skill when reviewing code changes, simplifying helper utilities, consolidating duplicate patterns, auditing security, or ensuring consistency across the esri/ toolkit. This is the review gate — run the full checklist before accepting any PR or commit to the esri_utils project."
---

# esri_utils best practices

Use when reviewing, simplifying, consolidating, or extending helper utilities.
This is the quality gate for all esri_utils code.

## Design principles

1. **Small composable functions over classes.** Use classes only when SDK state
   wrapping requires it (e.g., `PortalConfig`). Prefer `gis`-passing functions.
2. **One geometry constant.** `from ._core import GEOM_COL` is the only way to
   reference the geometry column. Never hardcode `"SHAPE"` or redefine it.
3. **Centralized auth.** All Portal auth lives in `config.py` / `portal.connect()`.
   No module should construct `arcgis.gis.GIS` directly.
4. **Thin CLI.** Parse args → call helper → print result. Helpers do the work.
   No business logic in CLI handlers.
5. **Preserve public API** unless a compatibility contract says otherwise.
   Deprecate before removing. Use `warnings.warn` with a removal version.
6. **Delete old paths after refactors.** Unless explicit backward compatibility
   is needed, clean up old function signatures, aliases, and modules.
   The user has no interest in dead code.

## Developer ergonomics

- **Boilerplate reduction**: write helpers that eliminate 3+ lines of repeated
  Portal/SDF setup pattern. If the same arcgis incantation appears in 3 places,
  extract it.
- **Safe diagnostics**: `esri doctor` must never log tokens, API keys, passwords,
  or full environment dumps. Use `config.diagnostic_repr()` for safe redaction.
- **CLI one-liners**: only add CLI subcommands for workflow one-liners that save
  real keystrokes. Don't mirror every function.
- **Dry-run modes**: every publish/delete/admin operation needs a dry-run mode
  that prints what would happen without executing it.
- **Document live steps**: since tests can't hit live ArcGIS, document the manual
  acceptance steps clearly (what env vars, what items, what commands).

## Security checklist

- [ ] No credentials logged, printed, or stored in output files.
- [ ] `esri doctor` redacts secrets (shows key length/prefix, not value).
- [ ] `.env` is in `.gitignore` — never committed.
- [ ] API keys and tokens are passed via env var, not function arg or config file.
- [ ] No shell injection vectors in CLI (`argparse`, not `subprocess` with `shell=True`).
- [ ] `config.diagnostic_repr()` used for all config display.

## Review checklist

Run this checklist on every change:

### Imports
- [ ] No top-level `import arcgis`, `arcpy`, `geopandas`, or `shapely`.
- [ ] Top-level imports: stdlib + `pandas` + `from ._core import ...`.
- [ ] Heavy deps lazy-imported inside the function that needs them.
- [ ] arcpy imports go through `_arcpy()` helper.

### API compatibility
- [ ] Uses `arcgis.map.Map`, not removed `arcgis.mapping.WebMap`.
- [ ] No removed arcgis 2.4 APIs.
- [ ] No deprecated pandas/numpy patterns.

### Engine correctness
- [ ] SDF vs GeoDataFrame engine choice is deliberate (see `sdf-pandas-geopandas`).
- [ ] `_core.to_geodataframe()` / `_core.to_sdf()` for conversions.
- [ ] `_core.GEOM_COL` for geometry column reference.

### Documentation
- [ ] Module docstring has purpose + usage block.
- [ ] Public functions have docstrings with `>>>` examples.
- [ ] CLI `--help` output matches actual behavior.
- [ ] `README.md` module map row added/updated.
- [ ] `AGENTS.md` module map row added/updated.
- [ ] Companion skills updated if new workflow added.

### Code quality
- [ ] Functions <50 lines, files <~500 LOC.
- [ ] Docstring examples are runnable (or clearly marked as live-only).
- [ ] Return types consistent (DataFrame/SDF for tabular, dict for metadata).
- [ ] No `try/except Pass` — handle exceptions or let them propagate.

### Tests
- [ ] Unit tests for pure-logic functions.
- [ ] No live-ArcGIS tests in CI (they can't run without credentials).
- [ ] Acceptance steps documented for manual testing.

## Refactoring patterns

### Extract repeated code

```python
# BEFORE — repeated in 3 places
from esri_utils._core import GEOM_COL
sdf = sdf.drop(columns=[GEOM_COL])
df = pd.DataFrame(sdf)

# AFTER — one helper
def sdf_to_clean_dataframe(sdf, drop_cols=None):
    from esri_utils._core import GEOM_COL
    drop_cols = drop_cols or [GEOM_COL]
    return pd.DataFrame(sdf.drop(columns=drop_cols))
```

### Centralize geometry conversion

```python
# BEFORE — raw arcgis incantation repeated
sdf.spatial.to_geoegdataframe()     # typo-prone

# AFTER — always use _core
from esri_utils._core import to_geodataframe
gdf = to_geodataframe(sdf)
```

## CLI patterns

```python
# Good — thin dispatcher
def run_mycmd(args):
    gis = connect()
    result = my_module.my_function(gis, args.param)
    print(result.to_string(index=False))

# Bad — business logic in CLI handler
def run_mycmd(args):
    gis = connect()
    # ... 15 lines of arcgis manipulation ...
    # ... another 10 lines of data processing ...
    print("done")
```

## Conventions summary

| Rule | Standard |
|------|----------|
| Lazy imports | `arcgis`/`arcpy`/`geopandas`/`shapely` inside functions only |
| Geometry col | `from ._core import GEOM_COL` |
| SDF↔GDF | `_core.to_geodataframe()` / `_core.to_sdf()` |
| Auth | `config.PortalConfig` → `portal.connect()` |
| CLI | `parser.set_defaults(func=handler)` |
| Function return | DataFrame/SDF for tabular; dict for metadata |
| Dry-run | All destructive ops need `--dry-run` or pre-print |
| Diagnostics | `esri doctor` — safe env check, no secret leak |
| Files | <500 LOC; functions <50 lines |
