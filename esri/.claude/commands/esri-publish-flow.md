---
description: Draft a connect -> query -> clean -> analyze -> publish script for the esri toolkit.
argument-hint: <source item-id or REST URL> [target title]
---

Write a runnable Python script using `esri_utils` that takes data from `$1`
through to a published hosted feature layer. Read `esri/AGENTS.md` and
`esri/examples/quickstart.py` first to match conventions.

The script should:
1. `connect()` via env-var auth (`esri_utils.portal`).
2. Load the source `$1`:
   - REST URL -> `layers.layer_from_url(url, gis)`
   - item id  -> `layers.get_feature_layer(gis, item_id)`
   then `layers.query_to_sdf(layer, where=..., chunk_size=2000)`.
3. Clean with `cleaning.standardize_columns` + `trim_strings` +
   `drop_empty_geometries`; print `cleaning.null_report(sdf).head()`.
4. Do at least one analysis step appropriate to the data (e.g.
   `analysis.to_geodataframe` then `dissolve` / `aggregate_by_polygon`, or an
   SDF `sjoin`/`buffer`). Explain the choice in a comment.
5. Publish with `layers.sdf_to_layer(sdf, gis, title="${2:-Published Layer}")`
   and print the new item id + URL.

Constraints:
- Guard destructive/publishing steps behind an `if __name__ == "__main__":` block
  and a `--dry-run` flag (argparse) that stops before publishing.
- No credentials in the script — rely on `ARCGIS_*` env vars.
- Keep it dependency-light; only use `esri_utils` + stdlib.

Do NOT run the script (it needs a live Portal); just produce it and tell me the
exact command to run, including which env vars must be set.
