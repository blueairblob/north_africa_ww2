"""Colours and sizes (docs/COUNTERS.md for the hex and counter sizes)."""

BASE_HEX = 64                       # a hex, corner to corner, in the base map (mapgen.render.BASE_HEX)
ZOOM_MAX, ZOOM_START = 2.0, 1.0     # the base map is scaled by the zoom; the least zoom shows the whole map
ZOOM_STEP = 1.2
COUNTER = 0.64                      # a counter's side as a share of the hex
PANEL = 330                         # the side panel's width
BAR = 86                            # the order bar's height: a message line and a row of buttons
WINDOW = (1400, 860)

TERRAIN = {"~": (184, 208, 222), ".": (236, 219, 176), "^": (212, 186, 138),
           "v": (190, 194, 174), "s": (243, 216, 132), "o": (152, 192, 116)}
TERRAIN_NAME = {"~": "sea", ".": "open desert", "^": "rough ground", "v": "depression (impassable)",
                "s": "sand sea (impassable)", "o": "oasis"}
GRID, INK, PAPER, DIM = (206, 190, 150), (45, 38, 30), (240, 232, 210), (120, 108, 90)
SCARP, ROAD, TRACK, RAIL = (112, 56, 24), (168, 40, 34), (120, 96, 68), (30, 30, 30)
PLACE = {"port": (200, 40, 40), "town": (50, 50, 50), "oasis": (40, 130, 60), "site": (250, 250, 250)}
FACE = {"cw": (204, 168, 104), "de": (140, 146, 142), "it": (140, 166, 118)}       # counter faces by nation
BOX = {"cw": (238, 216, 170), "de": (200, 205, 201), "it": (200, 218, 182)}
SIDE = {"axis": (96, 104, 100), "cw": (150, 112, 52)}
SIDE_NAME = {"axis": "Axis", "cw": "Commonwealth"}
SELECT, PATH, PATH_FAR, ATTACK = (255, 226, 60), (30, 90, 200), (120, 150, 205), (200, 40, 30)
SUPPLY, REACH, REACH_FULL, SHORT = (24, 98, 170), (70, 140, 210, 34), (70, 140, 210, 46), (210, 40, 30)
ZOC_OWN, ZOC_FOE, UNSEEN = (40, 110, 200, 50), (210, 50, 40, 70), (60, 52, 40, 100)
GOOD, POOR, FUEL, STORES = (60, 150, 70), (200, 60, 40), (150, 110, 40), (40, 100, 180)
BUTTON, BUTTON_ON, BUTTON_GO = (222, 210, 182), (255, 226, 60), (120, 170, 110)
ORDER_KEY = {"move": "M", "attack": "A", "hold": "H", "dig_in": "D", "road_march": "R", "rest": "T"}
ORDER_NAME = {"move": "Move", "attack": "Attack", "hold": "Hold", "dig_in": "Dig in",
              "road_march": "Road march", "rest": "Rest"}
ORDER_HELP = {"move": "go to a hex across country", "attack": "go there and attack what you meet",
              "hold": "stay and defend", "dig_in": "stay and build defences (costs stores)",
              "road_march": "far and fast along roads; weak if caught", "rest": "stay and recover"}
# the order bar: name, label, key shown
BUTTONS = (("move", "Move", "M"), ("attack", "Attack", "A"), ("road_march", "Road march", "R"),
           ("hold", "Hold", "H"), ("dig_in", "Dig in", "D"), ("rest", "Rest", "T"),
           ("s", "Supply", "S"), ("z", "Zones", "Z"), ("done", "End turn", "Enter"))
