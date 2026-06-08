"""Cleaning helpers for (Spatially Enabled) DataFrames.

Plain pandas operations that keep the SHAPE column intact, plus a few
geometry-aware fixes. Works on any DataFrame; SDF-specific calls are guarded.
"""

from __future__ import annotations

import re

import pandas as pd

from ._core import GEOM_COL


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case all non-geometry columns; leave SHAPE untouched."""
    df = df.copy()

    def norm(c: str) -> str:
        if c == GEOM_COL:
            return c
        c = re.sub(r"[^\w]+", "_", c.strip())
        c = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", c)
        return c.lower().strip("_")

    df.columns = [norm(c) for c in df.columns]
    return df


def drop_empty_geometries(sdf: pd.DataFrame) -> pd.DataFrame:
    """Remove rows whose geometry is null or empty."""
    if GEOM_COL not in sdf.columns:
        return sdf
    mask = sdf[GEOM_COL].notna() & sdf[GEOM_COL].apply(
        lambda g: bool(g) and not getattr(g, "is_empty", False)
    )
    return sdf.loc[mask].reset_index(drop=True)


def coerce_types(df: pd.DataFrame, schema: dict[str, str]) -> pd.DataFrame:
    """Cast columns per a {column: dtype} map, coercing bad values to NaN/NaT."""
    df = df.copy()
    for col, dtype in schema.items():
        if col not in df.columns:
            continue
        if dtype.startswith("datetime"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif dtype in {"int", "float"}:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if dtype == "int":
                df[col] = df[col].astype("Int64")
        else:
            df[col] = df[col].astype(dtype)
    return df


def trim_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and collapse internal runs in object columns."""
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        if col == GEOM_COL:
            continue
        df[col] = (
            df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True).replace({"": pd.NA})
        )
    return df


def dedupe(df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first") -> pd.DataFrame:
    """Drop duplicate rows (ignores geometry object identity by default)."""
    cols = subset or [c for c in df.columns if c != GEOM_COL]
    return df.drop_duplicates(subset=cols, keep=keep).reset_index(drop=True)


def null_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column null counts and percentages — quick data-quality snapshot."""
    n = len(df)
    out = pd.DataFrame(
        {
            "n_null": df.isna().sum(),
            "pct_null": (df.isna().mean() * 100).round(2),
            "dtype": df.dtypes.astype(str),
        }
    )
    out.attrs["n_rows"] = n
    return out.sort_values("pct_null", ascending=False)
