"""Address reconciliation: fix Optius geocoding by matching to CAR / AM.

Strategy (join key = address string only)
-----------------------------------------
1. classify    each row as 'civic' | 'lotblock' | 'unknown'.
2. normalize   all datasets into ONE canonical form:
                 - expand Optius abbreviations via a {abbrev: full} JSON map,
                 - parse civic addresses into components (usaddress),
                 - standardize directionals / suffixes / case / punctuation.
3. match       within address type, tiered: exact key -> fuzzy (rapidfuzz),
                with cheap blocking to cut comparisons.
4. score       assign a confidence tier and (optionally) a spatial sanity flag,
                then borrow the reliable geometry from the matched CAR/AM row.

Heavy deps (usaddress, rapidfuzz) are imported lazily; install with:
    uv sync --extra addr
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

GEOM_COL = "SHAPE"

# Canonical suffix / directional standardization (extend as needed).
SUFFIX_MAP = {
    "ST": "STREET", "AVE": "AVENUE", "RD": "ROAD", "BLVD": "BOULEVARD",
    "DR": "DRIVE", "LN": "LANE", "CT": "COURT", "CRES": "CRESCENT",
    "PL": "PLACE", "HWY": "HIGHWAY", "TER": "TERRACE", "PKY": "PARKWAY",
}
DIR_MAP = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST",
           "NE": "NORTHEAST", "NW": "NORTHWEST", "SE": "SOUTHEAST", "SW": "SOUTHWEST"}

# Registered-plan (urban) lot-block + SK rural ATS / DLS legal descriptions.
_LOTBLOCK_RE = re.compile(
    r"\b(lot|blk|block|plan|subdiv|parcel|quarter|qtr|sec|section|twp|township|rge|range|mer|meridian|"
    r"\bN[EW]\b|\bS[EW]\b)\b",
    re.I,
)
_CIVIC_RE = re.compile(r"^\s*\d+\s*[a-z]?\s+\S")

# Canadian postal code: A1A 1A1 (SK codes start with S). Used for blocking.
_POSTAL_RE = re.compile(r"\b([A-Za-z]\d[A-Za-z])\s*(\d[A-Za-z]\d)\b")


# --------------------------------------------------------------------------- #
# 1. classify
# --------------------------------------------------------------------------- #
def classify_address(s: str | None) -> str:
    """Return 'civic', 'lotblock', or 'unknown'."""
    if not s or not str(s).strip():
        return "unknown"
    text = str(s)
    if _LOTBLOCK_RE.search(text):
        return "lotblock"
    if _CIVIC_RE.match(text):
        return "civic"
    return "unknown"


# --------------------------------------------------------------------------- #
# 2. normalize
# --------------------------------------------------------------------------- #
def load_mapping(path: str | Path) -> dict[str, str]:
    """Load the {abbrev: full} JSON mapping (keys upper-cased)."""
    data = json.loads(Path(path).read_text())
    return {str(k).upper(): str(v).upper() for k, v in data.items()}


def expand_abbreviations(s: str, mapping: dict[str, str]) -> str:
    """Token-wise expand abbreviations (Optius short -> full)."""
    out = []
    for tok in re.split(r"(\s+)", str(s).upper()):
        if tok.strip() == "":
            out.append(tok)
            continue
        bare = tok.strip(".,")
        out.append(mapping.get(bare, bare))
    return " ".join(" ".join(out).split())


def _standardize_token(tok: str) -> str:
    tok = tok.strip(".,").upper()
    return DIR_MAP.get(tok, SUFFIX_MAP.get(tok, tok))


# Single-province dataset: drop these so they never pollute the match key.
_DROP_TOKENS = {"SK", "SASK", "SASKATCHEWAN", "CANADA", "CAN"}


def _postal(raw: str) -> str:
    """Pull a normalized Canadian postal code (A1A1A1) if present."""
    m = _POSTAL_RE.search(raw)
    return f"{m.group(1)}{m.group(2)}".upper() if m else ""


def normalize_civic(s: str, mapping: dict[str, str] | None = None) -> dict:
    """Parse + standardize a civic address into components and a match key.

    SK-aware: extracts a Canadian postal code for blocking (not a US ZIP),
    and drops province/country tokens (SK / SASKATCHEWAN / CANADA).
    """
    raw = expand_abbreviations(s, mapping) if mapping else str(s).upper()
    postal = _postal(raw)
    # Remove postal + province/country tokens before parsing the street.
    cleaned = _POSTAL_RE.sub(" ", raw)
    cleaned = " ".join(t for t in cleaned.split() if t.strip(".,") not in _DROP_TOKENS)

    comps: dict[str, str] = {}
    try:
        import usaddress

        tagged, _ = usaddress.tag(cleaned)
        comps = {
            "number": tagged.get("AddressNumber", ""),
            "predir": _standardize_token(tagged.get("StreetNamePreDirectional", "")),
            "street": tagged.get("StreetName", ""),
            "suffix": _standardize_token(tagged.get("StreetNamePostType", "")),
            "unit": tagged.get("OccupancyIdentifier", ""),
            "city": tagged.get("PlaceName", ""),
        }
    except Exception:
        # usaddress is US-trained; fall back to plain token standardization.
        comps = {"street": " ".join(_standardize_token(t) for t in cleaned.split())}

    comps["postal"] = postal
    key_parts = [comps.get("number", ""), comps.get("predir", ""),
                 comps.get("street", ""), comps.get("suffix", "")]
    comps["canon_key"] = " ".join(p for p in key_parts if p).strip()
    comps["block_key"] = (postal[:3] or comps.get("street", "")[:4]).strip()
    return comps


def normalize_lotblock(s: str) -> dict:
    """Extract a legal land description -> canonical key.

    Handles both SK styles:
      - urban registered plan:  Lot / Block / Plan
      - rural ATS (DLS) survey: Quarter Section-Township-Range-Meridian
        e.g. "NE 12-34-5 W3"  ->  QTR NE SEC 12 TWP 34 RGE 5 MER W3
    """
    text = str(s).upper()

    def grab(kw: str) -> str:
        m = re.search(rf"{kw}\s*[:#]?\s*([A-Z0-9\-]+)", text)
        return m.group(1) if m else ""

    # ATS compact form: <quarter> <sec>-<twp>-<rge> <meridian>
    ats = re.search(
        r"\b(NE|NW|SE|SW)?\s*(\d{1,2})\s*[-\s]\s*(\d{1,3})\s*[-\s]\s*(\d{1,2})\s*[-\s]?\s*([WE]\d)\b",
        text,
    )
    if ats:
        qtr, sec, twp, rge, mer = (g or "" for g in ats.groups())
        return {
            "quarter": qtr, "section": sec, "township": twp, "range": rge, "meridian": mer,
            "lot": "", "block": "", "plan": "",
            "canon_key": f"QTR {qtr} SEC {sec} TWP {twp} RGE {rge} MER {mer}".strip(),
            "block_key": f"{twp}-{rge}",
        }

    lot, block, plan = grab("LOT"), grab("BL?O?CK"), grab("PLAN")
    return {
        "lot": lot, "block": block, "plan": plan,
        "quarter": "", "section": "", "township": "", "range": "", "meridian": "",
        "canon_key": f"PLAN {plan} BLOCK {block} LOT {lot}".strip(),
        "block_key": plan or block,
    }


def normalize(df: pd.DataFrame, addr_col: str, mapping: dict[str, str] | None = None) -> pd.DataFrame:
    """Add addr_type / canon_key / block_key (+ components) columns to a copy."""
    df = df.copy()
    df["addr_type"] = df[addr_col].map(classify_address)

    def _norm(row):
        if row["addr_type"] == "civic":
            return normalize_civic(row[addr_col], mapping)
        if row["addr_type"] == "lotblock":
            return normalize_lotblock(row[addr_col])
        return {"canon_key": "", "block_key": ""}

    parsed = df.apply(_norm, axis=1, result_type="expand")
    # Avoid clobbering existing columns on collision.
    parsed = parsed[[c for c in parsed.columns if c not in df.columns]]
    return pd.concat([df, parsed], axis=1)


# --------------------------------------------------------------------------- #
# 3 + 4. match, score, borrow geometry
# --------------------------------------------------------------------------- #
def reconcile(
    optius: pd.DataFrame,
    reference: pd.DataFrame,
    optius_addr: str,
    ref_addr: str,
    mapping: dict[str, str] | None = None,
    ref_label: str = "REF",
    id_col: str | None = None,
    fuzzy_threshold: int = 88,
) -> pd.DataFrame:
    """Match Optius rows to a reference (CAR or AM) and return an audit table.

    Returns one row per Optius record:
        optius_idx, optius_addr, addr_type, match_source, match_type,
        score, matched_addr, status, [matched geometry as ref_SHAPE]
    """
    from rapidfuzz import fuzz, process

    o = normalize(optius, optius_addr, mapping)
    r = normalize(reference, ref_addr, mapping)

    # Index reference by canonical key for exact lookups.
    r_valid = r[r["canon_key"].astype(bool)]
    exact_index = r_valid.drop_duplicates("canon_key").set_index("canon_key")

    results = []
    for idx, row in o.iterrows():
        key, atype = row["canon_key"], row["addr_type"]
        rec = {
            "optius_idx": idx,
            "optius_id": row[id_col] if id_col else idx,
            "optius_addr": row[optius_addr],
            "addr_type": atype,
            "match_source": ref_label,
            "match_type": "none",
            "score": 0,
            "matched_addr": None,
            "status": "no-match",
        }

        if not key:
            results.append(rec)
            continue

        # Tier 1: exact canonical-key match.
        if key in exact_index.index:
            m = exact_index.loc[key]
            rec.update(match_type="exact", score=100,
                       matched_addr=m[ref_addr], status="auto-accept")
            if GEOM_COL in r.columns:
                rec[f"{ref_label}_{GEOM_COL}"] = m.get(GEOM_COL)
            results.append(rec)
            continue

        # Tier 2: fuzzy within same address type + same block (cheap candidates).
        cand = r_valid[(r_valid["addr_type"] == atype) &
                       (r_valid["block_key"] == row["block_key"])]
        if cand.empty:
            cand = r_valid[r_valid["addr_type"] == atype]
        if not cand.empty:
            best = process.extractOne(key, cand["canon_key"], scorer=fuzz.token_sort_ratio)
            if best:
                cand_key, score, pos = best
                if score >= fuzzy_threshold:
                    m = cand.iloc[pos]
                    rec.update(match_type="fuzzy", score=int(score),
                               matched_addr=m[ref_addr],
                               status="auto-accept" if score >= 95 else "review")
                    if GEOM_COL in r.columns:
                        rec[f"{ref_label}_{GEOM_COL}"] = m.get(GEOM_COL)
        results.append(rec)

    return pd.DataFrame(results)


def reconcile_multi(
    optius: pd.DataFrame,
    optius_addr: str,
    references: dict[str, tuple[pd.DataFrame, str]],
    mapping: dict[str, str] | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Run reconcile against several references (e.g. {'CAR': (df,'addr'), 'AM': (...)})
    and keep, per Optius row, the highest-scoring match across all sources."""
    frames = [
        reconcile(optius, ref_df, optius_addr, ref_addr, mapping=mapping, ref_label=label, **kwargs)
        for label, (ref_df, ref_addr) in references.items()
    ]
    allm = pd.concat(frames, ignore_index=True)
    allm = allm.sort_values("score", ascending=False)
    return allm.drop_duplicates("optius_idx", keep="first").sort_values("optius_idx").reset_index(drop=True)
