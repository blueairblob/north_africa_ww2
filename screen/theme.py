"""Colours and sizes (docs/COUNTERS.md for the hex and counter sizes)."""

BASE_HEX = 64                       # a hex, corner to corner, in the base map (mapgen.render.BASE_HEX)
ZOOM_MAX, ZOOM_START = 2.0, 1.0     # the base map is scaled by the zoom; the least zoom shows the whole map
ZOOM_STEP = 1.2
COUNTER = 0.64                      # a counter's side as a share of the hex
PANEL = 360                         # the side panel's width: everything to read and to press is in it
BAR = 32                            # the message line under the map
WINDOW = (1400, 860)

TERRAIN = {"~": (184, 208, 222), ".": (236, 219, 176), "^": (212, 186, 138),
           "v": (190, 194, 174), "s": (243, 216, 132), "o": (152, 192, 116)}
TERRAIN_NAME = {"~": "sea", ".": "open desert", "^": "rough ground", "v": "depression (impassable)",
                "s": "sand sea (impassable)", "o": "oasis"}
GRID, INK, PAPER, DIM = (206, 190, 150), (45, 38, 30), (240, 232, 210), (120, 108, 90)
SCARP, ROAD, TRACK, RAIL = (112, 56, 24), (168, 40, 34), (120, 96, 68), (30, 30, 30)
PLACE = {"port": (200, 40, 40), "town": (50, 50, 50), "oasis": (40, 130, 60), "site": (250, 250, 250)}
# counter faces by nation: Commonwealth blue, German dark grey, Italian green (the owner's choice
# of this game's own scheme); MARK is the colour of the picture and number on each face
FACE = {"cw": (110, 152, 208), "de": (78, 82, 88), "it": (112, 158, 92)}
MARK = {"cw": (24, 34, 58), "de": (238, 234, 222), "it": (26, 44, 22)}
BOX = {"cw": (186, 208, 236), "de": (150, 154, 160), "it": (180, 208, 164)}
SIDE = {"axis": (78, 82, 88), "cw": (70, 110, 170)}
SIDE_NAME = {"axis": "Axis", "cw": "Commonwealth"}
SELECT, PATH, PATH_FAR, ATTACK = (255, 226, 60), (30, 90, 200), (120, 150, 205), (200, 40, 30)
SUPPLY, REACH, REACH_FULL, SHORT = (24, 98, 170), (70, 140, 210, 34), (70, 140, 210, 46), (210, 40, 30)
ZOC_OWN, ZOC_FOE, UNSEEN = (40, 110, 200, 50), (210, 50, 40, 70), (60, 52, 40, 100)
GOOD, POOR, FUEL, STORES = (60, 150, 70), (200, 60, 40), (150, 110, 40), (40, 100, 180)
BUTTON, BUTTON_ON, BUTTON_GO = (222, 210, 182), (255, 226, 60), (120, 170, 110)
ORDER_KEY = {"move": "M", "attack": "A", "hold": "H", "dig_in": "D", "road_march": "R", "rest": "T"}
ORDER_NAME = {"move": "Move", "attack": "Attack", "hold": "Hold", "dig_in": "Dig in",
              "road_march": "Travel", "rest": "Rest"}            # Travel is the road march of the rules
ORDER_HELP = {"move": "go to a hex across country", "attack": "go there and attack what you meet",
              "hold": "stay and defend", "dig_in": "stay and build defences (costs stores)",
              "road_march": "far and fast by road; nearly helpless if caught", "rest": "stay and recover"}
TYPE_NAME = {"armour": "Tanks", "motorised": "Motorised infantry", "foot": "Infantry", "guns": "Guns",
             "recon": "Armoured cars", "hq": "Headquarters"}
# what a step of strength stands for (docs/RULES.md 4.2.1): so many of these
STRENGTH = {"armour": (10, "tanks"), "motorised": (800, "men"), "foot": (800, "men"), "guns": (12, "guns"),
            "recon": (15, "armoured cars")}
MORALE = ("Very poor", "Poor", "Very low", "Low", "Fair", "Normal", "Good", "Very good", "Excellent")
# the order bar: name, label, key shown
BUTTONS = (("move", "Move", "M"), ("attack", "Attack", "A"), ("road_march", "Travel", "R"),
           ("hold", "Hold", "H"), ("dig_in", "Dig in", "D"), ("rest", "Rest", "T"),
           ("s", "Supply", "S"), ("z", "Zones", "Z"), ("done", "End turn", "Enter"))


def morale(cohesion):
    """Cohesion as the player is told it: a level from 1 to 9 and its name."""
    level = 1 + cohesion * 9 // 101
    return level, MORALE[level - 1]


def strength(u):
    """A unit's strength in real terms, from its steps: "about 130 tanks"."""
    if u["type"] not in STRENGTH or "steps" not in u:
        return ""
    each, what = STRENGTH[u["type"]]
    return f"about {u['steps'] * each:,} {what}"


def count(n, one, many=None):
    """A number with its noun: "1 step", "2 steps"."""
    return f"{n} {one if n == 1 else many or one + 's'}"
