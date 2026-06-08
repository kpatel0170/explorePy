"""Enable ``python -m esri_utils ...`` (no install required)."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
