"""Draw data/map.json as a PNG, to look at the generated map."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

from . import build, fetch
from . import hexgrid as H

OUT = os.path.join(fetch.HERE, "map.png")
COLOURS = {build.SEA: (104, 150, 190), build.DESERT: (226, 205, 150), build.ROUGH: (190, 160, 110),
           build.DEPRESSION: (150, 150, 130), build.SAND: (240, 225, 130)}
SCARP, ROAD, TRACK, RAIL, INK = (110, 60, 30), (40, 40, 40), (90, 70, 50), (20, 20, 20), (30, 30, 30)


def _font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(m, path=OUT, scale=1.6):
    """scale: pixels per km."""
    cols, rows = m["cols"], m["rows"]
    w = int((H.COL_STEP * cols + H.SIZE) * scale) + 2
    h = int((H.ROW_STEP * (rows + 0.5)) * scale) + 2
    img = Image.new("RGB", (w, h), COLOURS[build.SEA])
    d = ImageDraw.Draw(img)

    def px(p):
        return p[0] * scale, p[1] * scale

    elev = m["elevation"]
    for r in range(rows):
        for c in range(cols):
            t = m["terrain"][r][c]
            col = COLOURS[t]
            if t in (build.DESERT, build.ROUGH):          # shade by height
                k = max(-0.12, min(0.18, (elev[r][c] - 150) / 2500))
                col = tuple(int(v * (1 - k)) for v in col)
            d.polygon([px(p) for p in H.corners(c, r)], fill=col,
                      outline=tuple(int(v * 0.93) for v in col))
    for c, r, k, high in m["escarpments"]:
        a, b, _ = H.edge(c, r, k)
        d.line([px(a), px(b)], fill=SCARP, width=3)
    for c, r, k in m["passes"]:
        a, b, _ = H.edge(c, r, k)
        mid = ((a[0] + b[0]) / 2 * scale, (a[1] + b[1]) / 2 * scale)
        d.ellipse([mid[0] - 3, mid[1] - 3, mid[0] + 3, mid[1] + 3], fill=(250, 250, 250), outline=SCARP)
    for route in m["routes"]:
        pts = [px(H.centre(c, r)) for c, r in route["hexes"]]
        if route["kind"] == "road":
            d.line(pts, fill=ROAD, width=3)
        elif route["kind"] == "rail":
            d.line(pts, fill=RAIL, width=1)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                mx, my, nx, ny = (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0), -(x1 - x0)
                n = max((nx * nx + ny * ny) ** 0.5, 1)
                d.line([(mx - nx / n * 3, my - ny / n * 3), (mx + nx / n * 3, my + ny / n * 3)], fill=RAIL, width=1)
        else:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):       # dashed
                d.line([(x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2)], fill=TRACK, width=2)
    font = _font(11)
    for p in m["places"]:
        x, y = px(H.centre(p["col"], p["row"]))
        big = p["kind"] == "port"
        s = 4 if big else 3
        fill = {"port": (200, 40, 40), "town": (40, 40, 40), "oasis": (40, 130, 60)}.get(p["kind"], (250, 250, 250))
        d.ellipse([x - s, y - s, x + s, y + s], fill=fill, outline=INK)
        d.text((x + 6, y - 6), p["name"], fill=INK, font=font, stroke_width=2, stroke_fill=(245, 240, 225))
    img.save(path)
    return path


def main(path=None):
    with open(build.OUT) as f:
        return render(json.load(f), path or OUT)
