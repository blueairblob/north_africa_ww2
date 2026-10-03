"""Elevation, land/sea and slope on a regular grid of the map (RES km per pixel)."""
import json
import math

import numpy as np
from PIL import Image, ImageDraw

from . import fetch, geo

RES = 0.5                       # km per pixel


def shape():
    return int(math.ceil(geo.HEIGHT_KM / RES)), int(math.ceil(geo.WIDTH_KM / RES))


def elevation():
    """Elevation in metres for every grid pixel (from the terrarium tiles)."""
    z = fetch.ZOOM
    x0, y0, x1, y1 = geo.tile_range(z)
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), dtype=np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            rgb = np.asarray(Image.open(fetch.tile_path(x, y)).convert("RGB"), dtype=np.float32)
            tile = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
            mosaic[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = tile
    h, w = shape()
    lon = geo.LON_W + (np.arange(w) + 0.5) * RES / geo.KM_PER_DEG_LON
    lat = geo.LAT_N - (np.arange(h) + 0.5) * RES / geo.KM_PER_DEG_LAT
    n = 256 * 2 ** z
    px = ((lon + 180) / 360 * n - x0 * 256).astype(np.int32)
    s = np.sin(np.radians(lat))
    py = ((0.5 - np.log((1 + s) / (1 - s)) / (4 * math.pi)) * n - y0 * 256).astype(np.int32)
    return mosaic[np.clip(py, 0, mosaic.shape[0] - 1)[:, None], np.clip(px, 0, mosaic.shape[1] - 1)[None, :]]


def land():
    """True where the grid pixel is land (Natural Earth 1:10m land polygons)."""
    h, w = shape()
    img = Image.new("1", (w, h), 0)
    draw = ImageDraw.Draw(img)
    pad = 1.0
    box = (geo.LON_W - pad, geo.LAT_S - pad, geo.LON_E + pad, geo.LAT_N + pad)

    def px(ring):
        return [((lon - geo.LON_W) * geo.KM_PER_DEG_LON / RES, (geo.LAT_N - lat) * geo.KM_PER_DEG_LAT / RES)
                for lon, lat in ring]

    def touches(ring):
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return not (max(xs) < box[0] or min(xs) > box[2] or max(ys) < box[1] or min(ys) > box[3])

    with open(fetch.land_path()) as f:
        features = json.load(f)["features"]
    for feat in features:
        g = feat["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            if not touches(poly[0]):
                continue
            draw.polygon(px(poly[0]), fill=1)
            for hole in poly[1:]:
                if touches(hole):
                    draw.polygon(px(hole), fill=0)
    return np.asarray(img, dtype=bool)


def slope(elev):
    """Steepness in metres per km."""
    gy, gx = np.gradient(elev, RES)
    return np.hypot(gx, gy)


def hex_index():
    """For every grid pixel, col * ROWS + row of its hex (-1 outside the map's hexes)."""
    from . import hexgrid as H
    h, w = shape()
    x = (np.arange(w) + 0.5) * RES - H.SIZE
    y = (np.arange(h) + 0.5) * RES - H.ROW_STEP / 2
    xx, yy = np.meshgrid(x, y)
    q = (2 / 3 * xx) / H.SIZE
    r = (-xx / 3 + math.sqrt(3) / 3 * yy) / H.SIZE
    s = -q - r
    rq, rr, rs = np.rint(q), np.rint(r), np.rint(s)
    dq, dr, ds = np.abs(rq - q), np.abs(rr - r), np.abs(rs - s)
    fix_q = (dq > dr) & (dq > ds)
    fix_r = ~fix_q & (dr > ds)
    rq = np.where(fix_q, -rr - rs, rq)
    rr = np.where(fix_r, -rq - rs, rr)
    col = rq.astype(np.int32)
    row = (rr + (rq - (col & 1)) / 2).astype(np.int32)
    ok = (col >= 0) & (col < geo.COLS) & (row >= 0) & (row < geo.ROWS)
    return np.where(ok, col * geo.ROWS + row, -1)
