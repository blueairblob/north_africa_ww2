"""Download the public source data into cache/ (once)."""
import os
import urllib.request

from . import geo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "cache")
ZOOM = 9            # about 260 m per pixel at this latitude
TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
LAND = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson"
AGENT = {"User-Agent": "benghazi-handicap-mapgen/0.1"}


def _get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120) as r:
        data = r.read()
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return True


def tile_path(x, y, zoom=ZOOM):
    return os.path.join(CACHE, "terrarium", str(zoom), f"{x}_{y}.png")


def land_path():
    return os.path.join(CACHE, "ne_10m_land.geojson")


def fetch(log=print):
    x0, y0, x1, y1 = geo.tile_range(ZOOM)
    n = new = 0
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            new += _get(TILES.format(z=ZOOM, x=x, y=y), tile_path(x, y))
            n += 1
    log(f"elevation: {n} tiles at zoom {ZOOM} ({new} downloaded)")
    log("coastline: " + ("downloaded" if _get(LAND, land_path()) else "cached"))
