"""Fit a map-image calibration from anchor points.

Usage:
    python3 tools/calibrate_map_image.py <pack> <anchors.json>

anchors.json: a list of anchor pairs tying grid coordinates (the engine's
100x32 underlay) to pixel positions on the pack's map image:

    [
      {"grid": [44, 8],  "px": [1410, 250]},   # e.g. Tobruk
      {"grid": [1, 22],  "px": [60, 700]},     # e.g. El Agheila
      {"grid": [97, 15], "px": [3105, 470]}    # e.g. Alexandria
    ]

Two anchors minimum (opposite corners work best); more anchors -> least
squares fit. The fit is axis-aligned affine (px = a*grid + b per axis),
which is what a straight-cropped scan needs. Writes
content_packs/<pack>/map_calibration.json and reports residuals so a bad
anchor is obvious.

Workflow for an archive scan: drop the image at
content_packs/<pack>/map.png, pick a few identifiable places, read their
pixel positions in any image viewer, list their grid coordinates (the
pack's features.json is the natural source), run this tool. NOTE: period
map scans are frequently still in copyright -- treat such an image like
data/tiles_original.json: keep it local, do not commit it (see NOTES.md).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fit_axis(pairs):
    """Least-squares a,b for px = a*grid + b."""
    n = len(pairs)
    sx = sum(g for g, _ in pairs)
    sy = sum(p for _, p in pairs)
    sxx = sum(g * g for g, _ in pairs)
    sxy = sum(g * p for g, p in pairs)
    denom = n * sxx - sx * sx
    if denom == 0:
        raise SystemExit("anchors are degenerate on one axis (need spread)")
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    return a, b


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    pack, anchors_path = sys.argv[1], sys.argv[2]
    anchors = json.loads(Path(anchors_path).read_text())
    if len(anchors) < 2:
        raise SystemExit("need at least 2 anchors")

    ax, bx = fit_axis([(a["grid"][0], a["px"][0]) for a in anchors])
    ay, by = fit_axis([(a["grid"][1], a["px"][1]) for a in anchors])

    print(f"x: px = {ax:.3f} * grid_x + {bx:.2f}")
    print(f"y: px = {ay:.3f} * grid_y + {by:.2f}")
    worst = 0.0
    for a in anchors:
        ex = ax * a["grid"][0] + bx - a["px"][0]
        ey = ay * a["grid"][1] + by - a["px"][1]
        err = (ex * ex + ey * ey) ** 0.5
        worst = max(worst, err)
        print(f"  anchor grid={a['grid']} px={a['px']} residual={err:.1f}px")
    print(f"worst residual: {worst:.1f}px")

    out = ROOT / "content_packs" / pack / "map_calibration.json"
    out.write_text(json.dumps({
        "_provenance": "Fitted by tools/calibrate_map_image.py from anchor points.",
        "cell_to_px_x": [round(ax, 4), round(bx, 2)],
        "cell_to_px_y": [round(ay, 4), round(by, 2)],
    }, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
