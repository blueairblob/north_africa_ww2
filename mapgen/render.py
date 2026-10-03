"""Draw data/map.json as a PNG in the manner of a map of the period: relief shading,
a neat border with the degrees marked, and a title block with legend and scale."""
import json
import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import build, fetch, geo, raster
from . import hexgrid as H

OUT = os.path.join(fetch.HERE, "map.png")
BASE = os.path.join(fetch.HERE, "art", "basemap.jpg")
BASE_HEX = 64                   # pixels across a hex, corner to corner, in the screen's base map
TITLE = ("Map 1", "CYRENAICA AND THE WESTERN DESERT", "1940 – 1942")
CREDIT = ("BENGHAZI HANDICAP  ·  North Africa 1940–42",
          "Hexes of 10 km.  Coast and frontier: Natural Earth.  Relief: Terrain Tiles (SRTM and other open data).  "
          "Places and tracks after maps of the period.")
PAPER, INK, HALO = (240, 230, 205), (45, 38, 30), (250, 244, 228)
COLOURS = {build.SEA: (186, 211, 224), build.DESERT: (236, 219, 176), build.ROUGH: (214, 186, 136),
           build.DEPRESSION: (188, 192, 172), build.SAND: (242, 214, 128),
           build.OASIS: (150, 190, 112)}
STIPPLE = {build.SAND: (176, 128, 52), build.DEPRESSION: (104, 116, 104)}
SCARP, ROAD, TRACK, RAIL, FRONTIER = (116, 58, 26), (156, 34, 30), (92, 72, 52), (25, 25, 25), (70, 66, 60)
PLACE = {"port": (200, 40, 40), "town": (40, 40, 40), "oasis": (40, 130, 60), "site": (250, 250, 250)}
LIGHT = 26.0                    # the slope (m per km) that takes the relief shading to full strength
SHADE = 0.42                    # how much darker or lighter a slope can be
MILE = 1.609344
FONTS = "/usr/share/fonts/truetype/dejavu/DejaVu%s.ttf"


def _font(size, style="Sans"):
    for path in (FONTS % style, FONTS % "Sans"):
        if os.path.exists(path):
            return ImageFont.truetype(path, int(size))
    return ImageFont.load_default()


def relief(size, scale):
    """Shading for the lie of the land, lit from the north-west: an image-sized array of
    factors around 1, or None if the elevation data has not been fetched."""
    try:
        elev = raster.elevation()
    except FileNotFoundError:
        return None
    gy, gx = np.gradient(elev, raster.RES)
    shade = 1 + np.tanh((gx + gy) / (2 ** 0.5 * LIGHT)) * SHADE
    h, w = shade.shape
    img = Image.fromarray(shade.astype(np.float32)).resize(
        (int(w * raster.RES * scale), int(h * raster.RES * scale)), Image.BILINEAR)
    out = np.ones((size[1], size[0]), dtype=np.float32)
    part = np.asarray(img)[:size[1], :size[0]]
    out[:part.shape[0], :part.shape[1]] = part
    return out


def _dashes(d, pts, on, off, **style):
    """A dashed line through the points."""
    left, draw = on, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        at = 0.0
        while at < length:
            step = min(left, length - at)
            if draw:
                k0, k1 = at / length, (at + step) / length
                d.line([(x0 + (x1 - x0) * k0, y0 + (y1 - y0) * k0), (x0 + (x1 - x0) * k1, y0 + (y1 - y0) * k1)], **style)
            at += step
            left -= step
            if left <= 0:
                draw = not draw
                left = on if draw else off


def _spaced(d, xy, text, font, gap, anchor="m", **style):
    """Text with its letters spread out, the way maps name regions; centred on xy, or from it."""
    widths = [d.textlength(ch, font=font) for ch in text]
    x = xy[0] - ((sum(widths) + gap * (len(text) - 1)) / 2 if anchor == "m" else 0)
    for ch, w in zip(text, widths):
        d.text((x, xy[1]), ch, font=font, anchor="lm", **style)
        x += w + gap


def _stipple(img, mask, colour, scale, dash):
    """The dotted ground of a sand sea, or the dashes of a salt marsh, as period maps draw them."""
    w, h = img.size
    marks = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(marks)
    step = 2.6 * scale
    row = 0
    y = step / 2
    while y < h:
        x = step / 2 + (step if row % 2 else 0)
        while x < w:
            # a little irregular, but always the same
            jx, jy = ((row * 7 + int(x)) % 5 - 2) * 0.22 * scale, ((row * 3 + int(x) * 5) % 5 - 2) * 0.22 * scale
            if dash:
                d.line([(x + jx - 1.1 * scale, y + jy), (x + jx + 1.1 * scale, y + jy)], fill=255, width=1)
            else:
                d.ellipse([x + jx - 0.8, y + jy - 0.8, x + jx + 0.8, y + jy + 0.8], fill=255)
            x += step * 2
        y += step * (0.8 if dash else 1)
        row += 1
    marks = Image.fromarray(np.minimum(np.asarray(marks), np.asarray(mask)))
    img.paste(Image.new("RGB", (w, h), colour), (0, 0), marks)


def _scarp(d, a, b, low, scale):
    """An escarpment from a to b (pixels), with ticks towards the low side."""
    d.line([a, b], fill=SCARP, width=max(2, int(1.6 * scale)))
    n = (low[0] ** 2 + low[1] ** 2) ** 0.5
    for k in (0.25, 0.5, 0.75):
        x, y = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        d.line([(x, y), (x + low[0] / n * 1.4 * scale, y + low[1] / n * 1.4 * scale)], fill=SCARP, width=1)


def _road(d, pts, scale):
    d.line(pts, fill=ROAD, width=max(2, int(1.3 * scale)), joint="curve")


def _track(d, pts, scale):
    _dashes(d, pts, 4 * scale, 2.5 * scale, fill=TRACK, width=max(1, int(0.8 * scale)))


def _rail(d, pts, scale):
    d.line(pts, fill=RAIL, width=1)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        length = max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, 1)
        nx, ny = (y1 - y0) / length * 1.5 * scale, -(x1 - x0) / length * 1.5 * scale
        for k in range(int(length // (5 * scale)) + 1):
            f = (k + 0.5) * 5 * scale / length
            if f <= 1:
                x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
                d.line([(x - nx, y - ny), (x + nx, y + ny)], fill=RAIL, width=1)


def _frontier(d, pts, scale):
    _dashes(d, pts, 7 * scale, 3 * scale, fill=FRONTIER, width=2)


def _place(d, xy, kind, scale):
    s = (2.4 if kind == "port" else 1.8) * scale
    d.ellipse([xy[0] - s, xy[1] - s, xy[0] + s, xy[1] + s], fill=PLACE[kind], outline=INK)


def _pass(d, xy, scale):
    s = 1.6 * scale
    d.ellipse([xy[0] - s, xy[1] - s, xy[0] + s, xy[1] + s], fill=(250, 250, 250), outline=SCARP)


def draw_map(m, scale, lettering=None):
    """The map itself, to the edge of the hexes. lettering sets the size of the names apart
    from the scale of the ground (for the screen's base map, which is drawn large)."""
    ls = lettering or scale
    cols, rows = m["cols"], m["rows"]
    w = int((H.COL_STEP * cols + H.SIZE) * scale) + 2
    h = int((H.ROW_STEP * (rows + 0.5)) * scale) + 2
    img = Image.new("RGB", (w, h), COLOURS[build.SEA])
    d = ImageDraw.Draw(img)

    def px(p):
        return p[0] * scale, p[1] * scale

    def at(lat, lon):
        return px(geo.to_km(lon, lat))

    masks = {t: Image.new("L", (w, h), 0) for t in COLOURS}
    for r in range(rows):
        for c in range(cols):
            t = m["terrain"][r][c]
            pts = [px(p) for p in H.corners(c, r)]
            d.polygon(pts, fill=COLOURS[t])
            ImageDraw.Draw(masks[t]).polygon(pts, fill=255)
    shade = relief((w, h), scale)
    if shade is not None:                                  # the lie of the land, under the hexes
        rgb = np.asarray(img, dtype=np.float32)
        lit = np.clip(rgb * shade[:, :, None], 0, 255)
        rgb = np.where(np.asarray(masks[build.SEA])[:, :, None] > 0, rgb, lit)
        img = Image.fromarray(rgb.astype(np.uint8))
    for t, colour in STIPPLE.items():
        _stipple(img, masks[t], colour, scale, dash=t == build.DEPRESSION)
    d = ImageDraw.Draw(img, "RGBA")
    for r in range(rows):
        for c in range(cols):
            if m["terrain"][r][c] != build.SEA:
                d.polygon([px(p) for p in H.corners(c, r)], outline=(90, 70, 40, 40))
    d = ImageDraw.Draw(img)

    for label in m.get("labels", []):                      # under the lines and the places
        xy = at(label["lat"], label["lon"])
        if label["kind"] == "country":
            _spaced(d, xy, label["name"], _font(10 * ls, "Serif-Bold"), 8 * ls, fill=(112, 96, 76))
        elif label["kind"] == "sea":
            _spaced(d, xy, label["name"], _font(7.5 * ls, "Serif-Italic"), 2.5 * ls, fill=(62, 98, 130))
        else:
            d.text(xy, label["name"], font=_font(7.5 * ls, "Serif-Italic"), fill=(96, 66, 36), anchor="mm",
                   stroke_width=2, stroke_fill=HALO)
    if m.get("frontier"):
        _frontier(d, [at(lat, lon) for lat, lon in m["frontier"]], scale)
    for c, r, k, high in m["escarpments"]:
        a, b, (nx, ny) = H.edge(c, r, k)
        _scarp(d, px(a), px(b), (-nx, -ny) if high else (nx, ny), scale)
    for route in m["routes"]:
        pts = [px(H.centre(c, r)) for c, r in route["hexes"]]
        {"road": _road, "rail": _rail}.get(route["kind"], _track)(d, pts, scale)
    for p in m["passes"]:
        a, b, _ = H.edge(p["col"], p["row"], p["side"])
        _pass(d, px(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)), scale)
    font = _font(6.5 * ls)
    for p in m["places"]:
        x, y = px(H.centre(p["col"], p["row"]))
        _place(d, (x, y), p["kind"], scale)
        if p["col"] > cols - 8:                            # at the east edge the name goes to the left
            d.text((x - 3.5 * scale, y), p["name"], fill=INK, font=font, anchor="rm", stroke_width=2, stroke_fill=HALO)
        else:
            d.text((x + 3.5 * scale, y), p["name"], fill=INK, font=font, anchor="lm", stroke_width=2, stroke_fill=HALO)
    return img


def title_block(d, x, y, scale):
    """Title, legend and scale, written on the sea at (x, y) as on a map of the period."""
    serif, italic, small = _font(11 * scale, "Serif-Bold"), _font(7 * scale, "Serif-Italic"), _font(6.5 * scale, "Serif")
    d.text((x + 150 * scale, y), TITLE[0], font=italic, fill=INK, anchor="mm")
    _spaced(d, (x + 150 * scale, y + 13 * scale), TITLE[1], serif, 1.6 * scale, fill=INK)
    _spaced(d, (x + 150 * scale, y + 27 * scale), TITLE[2], _font(9 * scale, "Serif"), 2 * scale, fill=INK)

    def row(k, col):
        return x + (10 + 150 * col) * scale, y + (46 + 11 * k) * scale

    def name(k, col, text):
        rx, ry = row(k, col)
        d.text((rx + 34 * scale, ry), text, font=small, fill=INK, anchor="lm")

    def line(k, col):
        rx, ry = row(k, col)
        return [(rx, ry), (rx + 28 * scale, ry)]

    _road(d, line(0, 0), scale); name(0, 0, "Coast road")
    _track(d, line(1, 0), scale); name(1, 0, "Desert track")
    _rail(d, line(2, 0), scale); name(2, 0, "Railway")
    _frontier(d, line(3, 0), scale); name(3, 0, "Frontier (the Wire)")
    a, b = line(4, 0)
    _scarp(d, a, b, (0, 1), scale); name(4, 0, "Escarpment (ticks on the low side)")
    _scarp(d, *line(5, 0), (0, 1), scale)
    rx, ry = row(5, 0)
    _pass(d, (rx + 14 * scale, ry), scale); name(5, 0, "Pass")
    for k, (kind, text) in enumerate((("port", "Port"), ("town", "Town"), ("oasis", "Oasis village"), ("site", "Other place"))):
        rx, ry = row(k, 1)
        _place(d, (rx + 14 * scale, ry), kind, scale); name(k, 1, text)
    for k, (t, text) in enumerate(((build.SAND, "Sand sea"), (build.DEPRESSION, "Depression, salt marsh"),
                                   (build.ROUGH, "Rough going"), (build.OASIS, "Oasis"))):
        rx, ry = row(4 + k, 1)
        box = [rx + 4 * scale, ry - 3.5 * scale, rx + 24 * scale, ry + 3.5 * scale]
        d.rectangle(box, fill=COLOURS[t], outline=INK)
        if t in STIPPLE:
            for i in range(5):
                bx, by = box[0] + (3 + 3.6 * i) * scale, ry + (1.2 if i % 2 else -1.2) * scale
                if t == build.SAND:
                    d.ellipse([bx - 0.8, by - 0.8, bx + 0.8, by + 0.8], fill=STIPPLE[t])
                else:
                    d.line([(bx - 1.1 * scale, by), (bx + 1.1 * scale, by)], fill=STIPPLE[t], width=1)
        name(4 + k, 1, text)
    # scale bars: miles above, kilometres below
    bx, by = x + 40 * scale, y + 133 * scale
    for unit, km, marks, dy, above in (("Scale of Miles", MILE, (0, 20, 40, 60, 80, 100), 0, True),
                                       ("Kilometres", 1.0, (0, 50, 100, 150), 9 * scale, False)):
        yy = by + dy
        for i, (m0, m1) in enumerate(zip(marks, marks[1:])):
            box = [bx + m0 * km * scale, yy, bx + m1 * km * scale, yy + 2.2 * scale]
            d.rectangle(box, fill=INK if i % 2 == 0 else HALO, outline=INK)
        for mark in marks:
            d.text((bx + mark * km * scale, yy + (-2 * scale if above else 4.4 * scale)), str(mark),
                   font=_font(5.5 * scale, "Serif"), fill=INK, anchor="mb" if above else "mt")
        d.text((bx + marks[-1] * km * scale + 9 * scale, yy + 1.1 * scale), unit, font=italic, fill=INK, anchor="lm")


def render(m, path=OUT, scale=2.0):
    """scale: pixels per km."""
    full = draw_map(m, scale)
    # trim to whole hexes all round, so the border cuts the map cleanly
    left, top = H.SIZE / 2, H.ROW_STEP / 2
    right, bottom = H.COL_STEP * m["cols"], H.ROW_STEP * m["rows"]
    chart = full.crop((int(left * scale), int(top * scale), int(right * scale), int(bottom * scale)))
    w, h = chart.size
    margin, gap = int(15 * scale), int(2 * scale)
    page = Image.new("RGB", (w + 2 * margin, h + 2 * margin + int(9 * scale)), PAPER)
    page.paste(chart, (margin, margin))
    d = ImageDraw.Draw(page)
    title_block(d, margin + int((26.45 - geo.LON_W) * geo.KM_PER_DEG_LON * scale - left * scale), margin + int(9 * scale), scale)
    # the neat line, and the degrees marked in the border
    d.rectangle([margin - 1, margin - 1, margin + w, margin + h], outline=INK, width=1)
    d.rectangle([margin - gap - 2, margin - gap - 2, margin + w + gap + 1, margin + h + gap + 1], outline=INK, width=2)
    font = _font(6 * scale, "Serif")
    tick = int(3 * scale)
    for lon in range(int(geo.LON_W) + 1, int(geo.LON_E) + 1):
        x = margin + (geo.to_km(lon, geo.LAT_N)[0] - left) * scale
        if 0 <= x - margin <= w:
            for y0, y1, ty, anchor in ((margin - gap - 2, margin + tick, margin - gap - 4 * scale, "mb"),
                                       (margin + h - tick, margin + h + gap + 1, margin + h + gap + 4 * scale, "mt")):
                d.line([(x, y0), (x, y1)], fill=INK, width=1)
                d.text((x, ty), f"{lon}°E", font=font, fill=INK, anchor=anchor)
    for lat in range(int(geo.LAT_S) + 1, int(geo.LAT_N) + 1):
        y = margin + (geo.to_km(geo.LON_W, lat)[1] - top) * scale
        if 0 <= y - margin <= h:
            for x0, x1, tx, anchor in ((margin - gap - 2, margin + tick, margin - gap - 3 * scale, "rm"),
                                       (margin + w - tick, margin + w + gap + 1, margin + w + gap + 3 * scale, "lm")):
                d.line([(x0, y), (x1, y)], fill=INK, width=1)
                d.text((tx, y), f"{lat}°", font=font, fill=INK, anchor=anchor)
    foot = margin + h + margin + int(1 * scale)
    _spaced(d, (margin, foot), CREDIT[0], _font(6.5 * scale, "Serif-Bold"), 0.8 * scale, anchor="l", fill=INK)
    d.text((margin + w, foot), CREDIT[1], font=_font(5.2 * scale, "Serif-Italic"), fill=INK, anchor="rm")
    part = path + ".part"
    page.save(part, format="PNG")
    for attempt in range(5):                               # the old picture may be open in a viewer
        try:
            os.replace(part, path)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(2)
    return path


def base(path=BASE):
    """The screen's base map: the ground with its relief, routes and names, with no border,
    at BASE_HEX pixels to the hex. The screen scales it to zoom and draws the counters on it."""
    with open(build.OUT) as f:
        m = json.load(f)
    img = draw_map(m, BASE_HEX / (2 * H.SIZE), lettering=3.2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="JPEG", quality=88)
    return path


def main(path=None):
    with open(build.OUT) as f:
        return render(json.load(f), path or OUT)
