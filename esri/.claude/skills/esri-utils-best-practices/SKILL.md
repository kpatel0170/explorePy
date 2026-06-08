---
name: esri-utils-best-practices
description: "esri_utils best practices: helper design, consolidation, CLI ergonomics, docs, tests, safety."
---

# esri_utils best practices

Use when reviewing, simplifying, consolidating, or extending helper utilities.

Design:
- Prefer small composable functions over classes unless SDK state requires it.
- Share constants/conversions in `_core`; avoid duplicate `SHAPE` handling.
- Keep Portal auth in `config.py` / `portal.connect()`.
- Keep CLI thin: parse args, call helper, print readable DataFrames.
- Preserve public API unless a compatibility contract says otherwise.
- Delete old paths after refactors unless explicit compatibility is needed.

Developer ergonomics:
- Add helpers that remove repeated Portal/SDF boilerplate.
- Make diagnostics safe: no secrets, no broad env dumps.
- Expose workflow one-liners through CLI only when they help repeated work.
- Include dry-run modes before publish/delete/admin changes.
- Document live acceptance steps when tests cannot hit ArcGIS.

Review checklist:
- Lazy imports still hold.
- ArcGIS 2.4+ API names.
- SDF vs GeoDataFrame engine is deliberate.
- Geometry column handling centralized.
- CLI and README match behavior.
- AGENTS/skills updated for new workflows.
