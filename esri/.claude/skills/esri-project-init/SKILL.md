---
name: esri-project-init
description: "Scaffold and structure esri_utils utility projects/modules: create new modules following esri_utils conventions, set up pyproject.toml, write module docstrings with usage examples, add CLI subcommands, register in AGENTS.md and README, set up agent skills in .claude/ and .codex/. Use this skill whenever starting a new Python module in the esri/ toolkit, adding a new feature area, migrating an existing script into the toolkit structure, or setting up a new esri project from scratch. Also use when the user asks to 'add a module for X' or 'create a new tool for Y' in the esri context."
---

# esri project initialization

Use when starting or reshaping an `esri/` utility project or module.

## Project shape

```
esri/
├── pyproject.toml          # arcgis>=2.4.3, Python >=3.11,<3.15
├── README.md               # module map + usage examples
├── AGENTS.md               # hard rules, module map, verify steps
├── esri_utils/
│   ├── __init__.py         # __all__ + docstring
│   ├── _core.py            # GEOM_COL, register_spatial, to_geodataframe, to_sdf
│   ├── config.py           # PortalConfig.from_env / as_gis_kwargs
│   ├── portal.py           # connect, search, users, groups, clone
│   ├── layers.py           # query, edits, publish
│   └── <new_module>.py     # your new module (see checklist below)
├── .claude/skills/         # Claude Code agent skills
├── .codex/skills/          # Codex CLI agent skills
├── examples/
│   └── quickstart.py       # runnable demo
└── .env                    # gitignored — local env vars
```

## New module checklist

- [ ] Module docstring: purpose + short usage block (see template below).
- [ ] `from __future__ import annotations` as first import.
- [ ] Top-level imports: only stdlib + `pandas` + `from ._core import ...`.
- [ ] Lazy-import heavy deps (`arcgis`, `arcpy`, `geopandas`, `shapely`) inside functions.
- [ ] Public functions take `gis` if they hit Portal/Server.
- [ ] Functions return DataFrame/SDF where the output is tabular.
- [ ] Functions have docstrings with `>>>` examples (doctest-compatible).
- [ ] Add module to `esri_utils/__init__.py` `__all__` + package docstring.
- [ ] Add row in `README.md` module map.
- [ ] Add row in `AGENTS.md` module map.
- [ ] If it adds a useful one-liner, wire a CLI subcommand in `cli.py`.
- [ ] Run verification below.

### Module docstring template

```python
"""
<Module name>

<1-2 sentence purpose>.

Usage::

    from esri_utils.<module> import <function>

    result = <function>(gis, ...)
    print(result.head())
"""
```

### Function template

```python
from __future__ import annotations

import pandas as pd

from ._core import GEOM_COL

def my_function(gis, param1: str, param2: int = 10) -> pd.DataFrame:
    \"\"\"Do something useful.

    Parameters
    ----------
    gis : arcgis.gis.GIS
        Authenticated GIS object.
    param1 : str
        Description of param1.
    param2 : int, optional
        Description of param2 (default 10).

    Returns
    -------
    pd.DataFrame
        Description of returned data.

    >>> # doctest example (requires live Portal)
    \"\"\"
    import arcgis  # lazy import inside function
    # function body...
    return result_df
```

## CLI wiring

In `esri_utils/cli.py`:

```python
# Add subcommand
def register_subcommand(subparsers):
    parser = subparsers.add_parser("mycmd", help="Short description")
    parser.add_argument("--param", type=str, help="Parameter description")
    parser.set_defaults(func=run_mycmd)

def run_mycmd(args):
    from esri_utils.portal import connect
    from esri_utils import my_module
    gis = connect()
    result = my_module.my_function(gis, args.param)
    print(result.to_string(index=False))
```

## pyproject.toml baseline

```toml
[project]
name = "esri_utils"
requires-python = ">=3.11,<3.15"
dependencies = [
    "arcgis>=2.4.3",
    "pandas>=2",
]

[project.optional-dependencies]
addr = [
    "rapidfuzz>=3",
    "usaddress>=0.5",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.ruff.format]
quote-style = "double"
```

## Agent skill setup

Skills live in both `.claude/skills/` and `.codex/skills/`:

```
.claude/skills/<skill-name>/SKILL.md
.codex/skills/<skill-name>/SKILL.md
```

Keep content identical between both — the format is the same. Use `name` in
frontmatter matching the directory name. See existing skills for examples.

## Verification

```bash
cd esri
ruff check .
ruff format --check .
python -m compileall esri_utils                 # syntax (no arcgis needed)
python -m esri_utils --help                     # CLI wiring
python -m esri_utils doctor                     # env + dependency check
python -c "from esri_utils import <new_module>; print('OK')"
```
