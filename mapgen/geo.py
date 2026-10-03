"""The map's place on the Earth, and the web-mercator tile arithmetic for elevation."""
import math

from . import hexgrid as H

# the map: from west of El Agheila to east of Alexandria, the Cyrenaican coast to Siwa
LON_W, LON_E = 18.9, 30.1
LAT_N, LAT_S = 33.05, 28.95
LAT_MID = (LAT_N + LAT_S) / 2
KM_PER_DEG_LAT = 110.9
KM_PER_DEG_LON = 111.32 * math.cos(math.radians(LAT_MID))

WIDTH_KM = (LON_E - LON_W) * KM_PER_DEG_LON
HEIGHT_KM = (LAT_N - LAT_S) * KM_PER_DEG_LAT
COLS = int((WIDTH_KM - 0.5 * H.SIZE) // H.COL_STEP)
ROWS = int((HEIGHT_KM - H.ROW_STEP / 2) // H.ROW_STEP)


def to_km(lon, lat):
    return (lon - LON_W) * KM_PER_DEG_LON, (LAT_N - lat) * KM_PER_DEG_LAT


def to_lonlat(x, y):
    return LON_W + x / KM_PER_DEG_LON, LAT_N - y / KM_PER_DEG_LAT


def hex_of(lon, lat):
    return H.hex_at(*to_km(lon, lat))


def in_map(col, row):
    return 0 <= col < COLS and 0 <= row < ROWS


# ---- web mercator (the elevation tiles) -----------------------------------
def global_pixel(lon, lat, zoom):
    n = 256 * 2 ** zoom
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def tile_range(zoom):
    x0, y0 = global_pixel(LON_W, LAT_N, zoom)
    x1, y1 = global_pixel(LON_E, LAT_S, zoom)
    return int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
