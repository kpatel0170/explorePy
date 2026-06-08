---
description: Diagnose esri_utils environment, dependencies, and optional live Portal auth.
argument-hint: [--connect]
---

Run the toolkit readiness flow for `esri/`.

Steps:
1. Read `esri/AGENTS.md`.
2. Run `cd esri && python -m esri_utils doctor`.
3. If `$1` contains `--connect`, run `cd esri && python -m esri_utils doctor --connect`.
4. Summarize missing dependencies, selected auth mode, and exact next action.

Rules:
- Do not print secrets. The doctor command already masks token/API-key values.
- Missing `arcpy` is expected outside ArcGIS Pro/Server conda.
- Missing `rapidfuzz` / `usaddress` only matters for `address_recon`.
