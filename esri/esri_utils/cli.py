"""Command-line interface for the esri toolkit.

A thin, dependency-free (stdlib ``argparse``) wrapper over the most common
``esri_utils`` functions, so developers can connect, inspect, query, and geocode
without writing a script.

Run::

    esri --help                 # after `uv sync` / `uv pip install -e .`
    python -m esri_utils --help # no install needed

Examples::

    esri connect-test
    esri search --type "Feature Service" --owner planning_dept
    esri services --folder Hosted
    esri query <item-id> --where "STATE='CA'" --out ca.csv
    esri geocode "123 Main St, Springfield, IL"

Auth is read from environment variables (see ``esri_utils.config``); set at least
``ARCGIS_URL`` plus one credential (``ARCGIS_API_KEY`` / ``ARCGIS_USER`` +
``ARCGIS_PASSWORD`` / ``ARCGIS_TOKEN`` / ``ARCGIS_PROFILE``).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__


def _print_df(df, max_rows: int = 50) -> None:
    """Print a DataFrame compactly without geometry noise."""
    show = df.drop(columns=["SHAPE"], errors="ignore")
    with_str = show.head(max_rows).to_string(index=False)
    print(with_str)
    if len(df) > max_rows:
        print(f"... ({len(df):,} rows total, showing {max_rows})")


def _print_section(title: str, df, max_rows: int = 50) -> None:
    print(f"\n== {title} ==")
    _print_df(df, max_rows=max_rows)


def _cmd_doctor(args: argparse.Namespace) -> int:
    from .diagnostics import readiness_report

    report = readiness_report()
    _print_section("Environment", report["environment"])
    _print_section("Dependencies", report["dependencies"], max_rows=100)

    if not args.connect:
        print("\nRun `esri doctor --connect` to test live Portal auth.")
        return 0

    from .portal import connect

    gis = connect()
    props = gis.properties
    user = getattr(props, "user", None)
    username = getattr(user, "username", "anonymous") if user else "anonymous"
    name = getattr(props, "name", "") or getattr(props, "portalName", "")
    print(f"\nConnected to {name or gis.url!r} as {username}")
    return 0


def _cmd_connect_test(args: argparse.Namespace) -> int:
    from .portal import connect

    gis = connect()
    props = gis.properties
    user = getattr(props, "user", None)
    username = getattr(user, "username", "anonymous") if user else "anonymous"
    name = getattr(props, "name", "") or getattr(props, "portalName", "")
    print(f"Connected to {name or gis.url!r} as {username}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    from .portal import connect, search_items

    gis = connect()
    df = search_items(gis, query=args.query or "", item_type=args.type, owner=args.owner, max_items=args.max)
    if df.empty:
        print("No items found.")
        return 0
    _print_df(df)
    return 0


def _cmd_services(args: argparse.Namespace) -> int:
    from .admin import list_services
    from .portal import connect

    gis = connect()
    df = list_services(gis, folder=args.folder)
    if df.empty:
        print("No services found.")
        return 0
    _print_df(df)
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    from .layers import get_feature_layer, layer_from_url, query_to_sdf
    from .portal import connect

    gis = connect()
    if args.source.lower().startswith("http"):
        layer = layer_from_url(args.source, gis=gis)
    else:
        layer = get_feature_layer(gis, args.source, args.layer_index)

    sdf = query_to_sdf(layer, where=args.where, out_fields=args.fields, chunk_size=args.chunk)
    print(f"Queried {len(sdf):,} features.")

    if args.out:
        sdf.drop(columns=["SHAPE"], errors="ignore").to_csv(args.out, index=False)
        print(f"Wrote {args.out}")
    else:
        _print_df(sdf)
    return 0


def _cmd_geocode(args: argparse.Namespace) -> int:
    from .geocode import geocode
    from .portal import connect

    gis = connect()
    df = geocode(gis, args.address, max_locations=args.max)
    if df.empty:
        print("No matches.")
        return 0
    _print_df(df)
    return 0


def _cmd_fire(args: argparse.Namespace) -> int:
    from .fire import fire_threat_analysis

    clouds = fire_threat_analysis(
        day_range=args.days,
        conf_min=args.conf_min,
        min_km=args.min_km,
        max_km=args.max_km,
        smooth_km=args.smooth_km,
        shrink_km=args.shrink_km,
        min_points=args.min_points,
        nested=args.nested,
    )
    if len(clouds) == 0:
        print("No fire clouds produced (no qualifying hotspots in Saskatchewan).")
        return 0
    print(clouds.drop(columns=["geometry"]).to_string(index=False))

    if args.out:
        clouds.to_file(args.out, driver="GeoJSON")
        print(f"Wrote {args.out}")
    if args.publish:
        from ._core import to_sdf
        from .layers import sdf_to_layer
        from .portal import connect

        gis = connect()
        item = sdf_to_layer(to_sdf(clouds), gis, title=args.publish)
        print(f"Published: {getattr(item, 'id', item)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esri",
        description="ArcGIS Enterprise toolkit CLI (auth via ARCGIS_* env vars).",
    )
    parser.add_argument("--version", action="version", version=f"esri {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("connect-test", help="Connect with env-var auth and print portal/user.")
    p.set_defaults(func=_cmd_connect_test)

    p = sub.add_parser("doctor", help="Print secret-safe env/dependency diagnostics.")
    p.add_argument("--connect", action="store_true", help="Also test live Portal auth.")
    p.set_defaults(func=_cmd_doctor)

    p = sub.add_parser("search", help="Search Portal content.")
    p.add_argument("query", nargs="?", default="", help="Free-text query (optional).")
    p.add_argument("--type", help='Item type, e.g. "Feature Service".')
    p.add_argument("--owner", help="Filter by owner username.")
    p.add_argument("--max", type=int, default=50, help="Max items (default 50).")
    p.set_defaults(func=_cmd_search)

    p = sub.add_parser("services", help="List ArcGIS Server services (admin).")
    p.add_argument("--folder", help="Restrict to a folder (default: all).")
    p.set_defaults(func=_cmd_services)

    p = sub.add_parser("query", help="Query a feature layer to CSV or stdout.")
    p.add_argument("source", help="Item ID or feature-layer REST URL.")
    p.add_argument("--where", default="1=1", help='SQL where clause (default "1=1").')
    p.add_argument("--fields", default="*", help='Comma-separated fields (default "*").')
    p.add_argument("--layer-index", type=int, default=0, help="Layer index for item IDs.")
    p.add_argument("--chunk", type=int, default=2000, help="Paging size (default 2000).")
    p.add_argument("--out", help="Write CSV to this path (else print head).")
    p.set_defaults(func=_cmd_query)

    p = sub.add_parser("geocode", help="Forward-geocode a single address.")
    p.add_argument("address", help="Address string.")
    p.add_argument("--max", type=int, default=1, help="Max candidates (default 1).")
    p.set_defaults(func=_cmd_geocode)

    p = sub.add_parser("fire", help="Saskatchewan fire-threat clouds from NASA FIRMS + CWFIS.")
    p.add_argument("--days", type=int, default=7, help="FIRMS day range 1-10 (default 7).")
    p.add_argument("--conf-min", type=float, default=60.0, help="Min satellite confidence (default 60).")
    p.add_argument("--min-km", type=float, default=2.0, help="Min buffer radius km (default 2).")
    p.add_argument("--max-km", type=float, default=12.0, help="Max buffer radius km (default 12).")
    p.add_argument("--smooth-km", type=float, default=3.0, help="Cloud smoothing km (default 3).")
    p.add_argument("--shrink-km", type=float, default=1.0, help="Edge shrink km (default 1).")
    p.add_argument("--min-points", type=int, default=2, help="Min hotspots per cluster (default 2).")
    p.add_argument(
        "--nested",
        action="store_true",
        help="Cumulative concentric zones instead of the default new-over-old clouds.",
    )
    p.add_argument("--out", help="Write FIRE_AREA GeoJSON to this path.")
    p.add_argument("--publish", metavar="TITLE", help="Publish clouds as a hosted layer.")
    p.set_defaults(func=_cmd_fire)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # surface a clean message, not a traceback dump
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
