"""Saskatchewan fire-threat analysis: NASA FIRMS + CWFIS -> FIRE_AREA clouds.

Combines NASA FIRMS satellite hotspots (MODIS + VIIRS on SNPP / NOAA-20 / NOAA-21)
with CWFIS agency-reported active fires, filters to Saskatchewan, drops false
positives, then buffers -> dissolves -> smooths into distinct cloud polygons by
hotspot age (<24h, 24-48h, 48-96h, >96h), drawn new-over-old.

Run:
    export FIRMS_MAP_KEY=...        # free key: https://firms.modaps.eosdis.nasa.gov/api/
    python -m esri_utils.fire.example
    # or, from the esri/ dir:  python esri_utils/fire/example.py
    # writes fire_sk.geojson and (optionally) a preview PNG

Without FIRMS_MAP_KEY it still runs on CWFIS alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make esri_utils importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from esri_utils.fire import fire_threat_analysis  # noqa: E402


def main() -> None:
    clouds, points = fire_threat_analysis(day_range=7, return_points=True)

    print(f"Hotspots after filtering: {len(points)} ({int(points['reliable'].sum())} CWFIS-confirmed)")
    if len(clouds) == 0:
        print("No qualifying fire activity in Saskatchewan right now.")
        return

    print("\nFIRE_AREA clouds by age class:")
    print(
        clouds[["age_class", "threat_rank", "n_hotspots", "n_reliable", "fire_area_km2"]].to_string(
            index=False
        )
    )

    clouds.to_file("fire_sk.geojson", driver="GeoJSON")
    print("\nWrote fire_sk.geojson")

    # Optional quick preview: draw old/pale background first, recent/saturated on
    # top (clouds are already sorted by draw_order), using each cloud's own style.
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 10))
        for _, row in clouds.iterrows():
            clouds.iloc[[row.name]].plot(
                ax=ax,
                color=row["fill_color"],
                alpha=row["fill_alpha"],
                edgecolor="#7f2704",
                linewidth=0.5,
            )
        if len(points):
            points.plot(ax=ax, color="red", markersize=6)
        ax.set_title("Saskatchewan fire threat — FIRE_AREA (recent over older)")
        ax.set_axis_off()
        fig.savefig("fire_sk.png", dpi=150, bbox_inches="tight")
        print("Wrote fire_sk.png")
    except Exception as exc:  # noqa: BLE001
        print(f"(skipped preview: {exc})")


if __name__ == "__main__":
    main()
