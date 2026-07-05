"""Bake the default pack's cartographic map image -- VECTOR-DRAWN.

Draws content_packs/default/map.png at high resolution directly from the
same vector source that generates the 100x32 terrain grid (the eased
coast profile, the road polylines, the relief control points and the
place compilation in tools/build_default_map.py). The result is smooth
professional-style cartography -- anti-aliased coastline, soft relief,
curved roads -- instead of an upscaled cell grid, while staying
calibrated to the grid because both derive from one projection.

This is an ORIGINAL map drawn with generic period-atlas conventions
(cream paper, pale sea, coast stroke with offshore tint, blurred relief
with hachures, dot-and-serif-label settlements, italic region names,
scale bar, north arrow). It reproduces no published map's artwork.

Rebuild after changing terrain or features:
    python3 tools/build_default_map.py
    python3 tools/build_default_map_image.py
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_default_map as src  # the vector source

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 32                      # px per cell -> 3200 x 1024
W_PX, H_PX = src.W * S, src.H * S

PAPER = (243, 237, 216)
SEA = (199, 220, 229)
SEA_DEEP = (183, 209, 221)
COAST = (86, 110, 126)
COAST_TINT = (225, 238, 243)
ROAD = (122, 78, 36)
TRACK = (139, 100, 60)
RELIEF = (215, 194, 158)
RELIEF_DEEP = (198, 172, 130)
HACHURE = (172, 140, 100)
INK = (55, 47, 38)
REGION_INK = (150, 133, 106)
SEA_INK = (110, 136, 152)
DEPRESSION = (222, 212, 190)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def fonts():
    return (
        ImageFont.truetype(f"{FONT_DIR}/DejaVuSerif.ttf", 26),          # towns
        ImageFont.truetype(f"{FONT_DIR}/DejaVuSerif-Italic.ttf", 40),   # regions
        ImageFont.truetype(f"{FONT_DIR}/DejaVuSerif.ttf", 22),          # small
    )


def smooth_coast_path(samples_per_cell=8, window=13):
    """The eased per-column coast profile, upsampled and smoothed into a
    pixel-space path. Using the EASED profile (not the raw polyline)
    keeps the drawn coast consistent with the playable grid.
    """
    profile = src.constrained_coast_profile()
    dense = []
    n = src.W
    for i in range(n * samples_per_cell):
        x = i / samples_per_cell
        x0 = min(int(x), n - 2)
        t = x - x0
        dense.append(profile[x0] * (1 - t) + profile[x0 + 1] * t)
    half = window // 2
    sm = []
    for i in range(len(dense)):
        lo, hi = max(0, i - half), min(len(dense), i + half + 1)
        sm.append(sum(dense[lo:hi]) / (hi - lo))
    return [((i / samples_per_cell + 0.5) * S, y * S) for i, y in enumerate(sm)]


def polyline_px(lonlat_points, samples=200):
    pts = [src.to_grid(lon, lat) for lon, lat in lonlat_points]
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for i in range(samples // max(1, len(pts) - 1) + 1):
            t = i / (samples // max(1, len(pts) - 1) + 1)
            out.append(((x0 + t * (x1 - x0) + 0.5) * S, (y0 + t * (y1 - y0) + 0.5) * S))
    out.append(((pts[-1][0] + 0.5) * S, (pts[-1][1] + 0.5) * S))
    return out


def main():
    img = Image.new("RGB", (W_PX, H_PX), PAPER)
    draw = ImageDraw.Draw(img, "RGBA")
    town_f, region_f, small_f = fonts()

    coast = smooth_coast_path()

    # --- sea fill (gradient band: lighter along the shore)
    sea_poly = [(0, 0), (W_PX, 0)] + list(reversed(coast))
    draw.polygon(sea_poly, fill=SEA_DEEP)
    # near-shore tint band
    band = [(x, y) for (x, y) in coast]
    draw.line(band, fill=SEA, width=int(1.6 * S), joint="curve")
    draw.line(band, fill=COAST_TINT, width=int(0.55 * S), joint="curve")
    # redraw sea above the tint spill
    draw.polygon([(0, 0), (W_PX, 0),
                  (W_PX, min(y for _, y in coast) - 2 * S),
                  (0, min(y for _, y in coast) - 2 * S)], fill=SEA_DEEP)

    # land back over any band spill below the coast
    land_poly = [(0, H_PX), (W_PX, H_PX)] + list(reversed([(x, y + int(0.3 * S)) for x, y in coast]))
    draw.polygon(land_poly, fill=PAPER)

    # --- relief (blurred overlay, then hachures)
    relief = Image.new("RGBA", (W_PX, H_PX), (0, 0, 0, 0))
    rd = ImageDraw.Draw(relief)
    jebel = polyline_px([(20.6, 32.35), (21.4, 32.6), (22.3, 32.6), (22.9, 32.3)])
    rd.line(jebel, fill=RELIEF_DEEP + (235,), width=int(2.6 * S), joint="curve")
    rd.line(jebel, fill=RELIEF + (255,), width=int(1.6 * S), joint="curve")
    for pts in ([(25.15, 31.5), (25.5, 31.2), (25.9, 31.0)],
                [(23.3, 32.2), (23.9, 31.9), (24.6, 31.7)]):
        p = polyline_px(pts)
        rd.line(p, fill=RELIEF_DEEP + (220,), width=int(1.2 * S), joint="curve")
    relief = relief.filter(ImageFilter.GaussianBlur(S // 2))
    img.paste(Image.composite(Image.new("RGB", img.size, RELIEF), img, relief.split()[3]),
              (0, 0), relief.split()[3])
    draw = ImageDraw.Draw(img, "RGBA")

    # hachure ticks along the relief spines
    for path in (jebel, polyline_px([(25.15, 31.5), (25.9, 31.0)]),
                 polyline_px([(23.3, 32.2), (24.6, 31.7)])):
        for i in range(0, len(path) - 6, 6):
            (x0, y0), (x1, y1) = path[i], path[i + 5]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L, dx / L
            for side in (1, -1):
                draw.line([x0 + nx * side * 6, y0 + ny * side * 6,
                           x0 + nx * side * 20, y0 + ny * side * 20],
                          fill=HACHURE + (170,), width=2)

    # --- Qattara Depression: soft blob + stipple
    q = Image.new("RGBA", (W_PX, H_PX), (0, 0, 0, 0))
    qd = ImageDraw.Draw(q)
    qx0, qy0 = src.to_grid(27.4, 30.35)
    qx1, qy1 = src.to_grid(29.7, 29.45)
    qd.ellipse([qx0 * S, qy0 * S, qx1 * S, qy1 * S], fill=DEPRESSION + (255,))
    q = q.filter(ImageFilter.GaussianBlur(S // 2))
    img.paste(Image.composite(Image.new("RGB", img.size, DEPRESSION), img, q.split()[3]),
              (0, 0), q.split()[3])
    draw = ImageDraw.Draw(img, "RGBA")
    for gx in range(int(qx0 * S), int(qx1 * S), 14):
        for gy in range(int(qy0 * S), int(qy1 * S), 14):
            fx = (gx - qx0 * S) / max(1, (qx1 - qx0) * S)
            fy = (gy - qy0 * S) / max(1, (qy1 - qy0) * S)
            if (fx - 0.5) ** 2 / 0.25 + (fy - 0.5) ** 2 / 0.2 < 1:
                draw.point((gx + (gy // 14 % 2) * 7, gy), fill=(150, 140, 120))

    # --- coast stroke
    draw.line(coast, fill=COAST, width=max(3, S // 8), joint="curve")

    # --- roads: coastal road offset inland from the smooth coast + track
    coast_road = [(x, y + 0.9 * S) for (x, y) in coast]
    draw.line(coast_road, fill=ROAD, width=max(3, S // 9), joint="curve")
    chord = polyline_px([(20.2, 30.85), (21.3, 31.5), (22.5, 31.8), (23.9, 31.95)])
    # dashed track
    for i in range(0, len(chord) - 3, 6):
        draw.line(chord[i:i + 4], fill=TRACK, width=max(2, S // 11))

    # --- frontier wire (dashed vertical)
    bx, _ = src.to_grid(src.FRONTIER_LON, 31.0)
    px = (bx + 0.5) * S
    for y0 in range(0, H_PX, int(0.9 * S)):
        draw.line([px, y0, px, y0 + int(0.45 * S)], fill=INK, width=3)

    # --- labels & markers
    def halo_text(pos, label, fill, font):
        x, y = pos
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (1, -1), (-1, 1)):
            draw.text((x + ox, y + oy), label, font=font, fill=PAPER)
        draw.text((x, y), label, font=font, fill=fill)

    sx, sy = src.to_grid(*src.SEA_LABEL[1:])
    spaced = " ".join(src.SEA_LABEL[0])
    w = draw.textlength(spaced, font=region_f)
    draw.text(((sx + 0.5) * S - w / 2, (sy + 0.5) * S - 20), spaced, font=region_f, fill=SEA_INK)

    for name, lon, lat in src.REGION_LABELS:
        x, y = src.to_grid(lon, lat)
        spaced = " ".join(name)
        w = draw.textlength(spaced, font=region_f)
        halo_text(((x + 0.5) * S - w / 2, (y + 0.5) * S - 20), spaced, REGION_INK, region_f)

    r = 7
    for name, lon, lat, kind in src.FEATURES:
        x, y = src.to_grid(lon, lat)
        cx, cy = (x + 0.5) * S, (y + 0.5) * S
        if kind == "fort":
            draw.rectangle([cx - r, cy - r, cx + r, cy + r], outline=INK, width=3)
        elif kind == "port":
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=3)
            draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=INK)
        elif kind == "pass":
            draw.line([cx - r, cy + r, cx, cy - r], fill=INK, width=3)
            draw.line([cx, cy - r, cx + r, cy + r], fill=INK, width=3)
        else:
            draw.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=INK)
        halo_text((cx + r + 5, cy - 16), name, INK, town_f)

    # --- furniture: north arrow, scale bar
    nx, ny = W_PX - int(2.6 * S), int(0.9 * S)
    draw.line([nx, ny + 2 * S, nx, ny], fill=INK, width=4)
    draw.polygon([(nx - 12, ny + 26), (nx + 12, ny + 26), (nx, ny)], fill=INK)
    draw.text((nx + 14, ny), "N", font=small_f, fill=INK)

    features = json.loads((ROOT / "content_packs" / "default" / "features.json").read_text())
    kpc = features["km_per_cell"]
    bar_px = int(100 / kpc * S)
    bx0, by0 = W_PX - bar_px - int(2.2 * S), H_PX - int(1.3 * S)
    draw.line([bx0, by0, bx0 + bar_px, by0], fill=INK, width=5)
    for frac, lab in ((0, "0"), (0.5, "50"), (1.0, "100 km")):
        tx = bx0 + int(frac * bar_px)
        draw.line([tx, by0 - 12, tx, by0], fill=INK, width=3)
        halo_text((tx - 8, by0 - 42), lab, INK, small_f)

    out = ROOT / "content_packs" / "default" / "map.png"
    img.save(out, optimize=True)
    (ROOT / "content_packs" / "default" / "map_calibration.json").write_text(json.dumps({
        "_provenance": f"Identity calibration for the vector-drawn atlas image ({S}px per cell).",
        "cell_to_px_x": [S, 0],
        "cell_to_px_y": [S, 0],
    }, indent=1))
    print(f"wrote {out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
