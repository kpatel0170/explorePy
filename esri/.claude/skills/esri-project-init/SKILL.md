---
name: esri-project-init
description: "Initialize esri_utils projects: structure, env, docs, CLI, examples, tests, agent instructions."
---

# esri project initialization

Use when starting or reshaping an `esri/` utility project/module.

Initial shape:
- `pyproject.toml` with `arcgis>=2.4.3`, Python `>=3.11,<3.15`.
- `esri_utils/` modules are function-first; no hidden Portal singletons.
- `examples/quickstart.py` for runnable patterns.
- `AGENTS.md` for hard rules and module map.
- `.codex/skills/` and `.claude/skills/` for agent workflows.

Module checklist:
- Module docstring with purpose + short usage.
- `from __future__ import annotations`.
- Top-level imports: stdlib + `pandas` + `._core` only.
- Lazy-import heavy deps inside functions.
- Public functions take `gis` if they hit Portal/Server.
- Return DataFrame/SDF where inspectable.
- Add README + AGENTS module-map row.
- Add CLI subcommand only for useful one-liners.

Verification:

```bash
cd esri
ruff check .
ruff format --check .
python -m compileall esri_utils
python -m esri_utils --help
python -m esri_utils doctor
```
