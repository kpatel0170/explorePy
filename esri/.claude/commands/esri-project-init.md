---
description: Plan or scaffold an esri_utils module/project using repo conventions.
argument-hint: <module-or-workflow>
---

Read `esri/AGENTS.md`, `esri-project-init`, and `esri-utils-best-practices`.

For `$1`, produce or update:
1. module docstring + lazy imports
2. function-first helper API
3. README + AGENTS module-map entries
4. CLI subcommand only when it is a useful repeated workflow
5. verify commands and live Portal acceptance steps

Keep ArcGIS heavy deps lazy and use `_core` for `GEOM_COL` / conversions.
