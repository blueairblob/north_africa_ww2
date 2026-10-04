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
ORDER_KEY = {"move": "M", "attack": "A", "hold": "H", "dig_in": "D", "road_march": "T", "rest": "R", "join": "J"}
ORDER_NAME = {"move": "Move", "attack": "Attack", "hold": "Hold", "dig_in": "Dig in",
              "road_march": "Travel", "rest": "Rest", "join": "Join"}   # Travel is the road march of the rules
ORDER_HELP = {"move": "go to a hex across country", "attack": "go there and attack what you meet",
              "hold": "stay and defend", "dig_in": "stay and build defences (costs stores)",
              "road_march": "far and fast by road; nearly helpless if caught", "rest": "stay and recover",
              "join": "go to a unit of its division and group with it"}
TYPE_NAME = {"armour": "Tanks", "motorised": "Motorised infantry", "foot": "Infantry", "guns": "Guns",
             "recon": "Armoured cars", "hq": "Headquarters"}
# what a step of strength stands for (docs/RULES.md 4.2.1): so many of these
STRENGTH = {"armour": (10, "tanks"), "motorised": (800, "men"), "foot": (800, "men"), "guns": (12, "guns"),
            "recon": (15, "armoured cars")}
MORALE = ("Very poor", "Poor", "Very low", "Low", "Fair", "Normal", "Good", "Very good", "Excellent")
# the order bar: name, label, key shown
BUTTONS = (("move", "Move", "M"), ("attack", "Attack", "A"), ("road_march", "Travel", "T"),
           ("hold", "Hold", "H"), ("dig_in", "Dig in", "D"), ("rest", "Rest", "R"),
           ("join", "Join", "J"), ("split", "Split", "X"), ("recall", "Recall", "C"),
           ("next", "Next unit", "Space"), ("done", "End turn", "Enter"))
LAYERS = (("s", "Supply", "S"), ("z", "Zones", "Z"), ("k", "Key", "K"))   # the map's layers, behind the button in its corner
MARGIN = 46             # base-map pixels of paper shown beyond the map's edge, for its border
HQ_STAFF = 300          # a headquarters' nominal strength in men, for show: it has one step in the rules
STRONG, WORN, WEAK = (40, 90, 190), (214, 126, 24), (200, 40, 30)   # strength: under full, under 70%, under 50%
PREVIEW = (70, 150, 255)                                           # the way being chosen: blue, like one ordered
HAUL = (255, 214, 40)                                              # a supply haul: yellow
BADGE = (255, 214, 40)                                             # the trouble badge on a counter
ARM = ("armour", "motorised", "foot", "guns", "recon", "hq")       # which unit of a pile is shown on top


def order_name(name, units=()):
    """An order by the name the player sees: a road march is Travel for vehicles and March for
    any group with men on foot."""
    if name == "road_march" and any(u["type"] == "foot" for u in units):
        return "March"
    return ORDER_NAME[name]


def morale(cohesion):
    """Cohesion as the player is told it: a level from 1 to 9 and its name."""
    level = 1 + cohesion * 9 // 101
    return level, MORALE[level - 1]


def strength_now(u):
    """(now, at full, what) in real terms, or None for a unit whose strength is not known."""
    if "steps" not in u:
        return None
    if u["type"] == "hq":
        return HQ_STAFF, HQ_STAFF, "men"
    if u.get("real"):
        n, what, began = u["real"]
        return n * u["steps"] // began, n, "armoured cars" if what == "cars" else what
    each, what = STRENGTH[u["type"]]
    return u["steps"] * each, u.get("max", u["steps"]) * each, what


def strength_colour(u):
    """Black at full strength, blue from 70%, orange from 50%, red below."""
    now = strength_now(u)
    pct = 100 if not now else now[0] * 100 // max(1, now[1])
    return INK if pct >= 100 else STRONG if pct >= 70 else WORN if pct >= 50 else WEAK


def strength_tip(u):
    """The figures behind the word: "about 80 of 100 tanks (80%, 20 lost)"."""
    now, full, what = strength_now(u)
    if u["type"] == "hq":
        return f"a headquarters: about {now} men, a nominal figure"
    return f"about {now:,} of {full:,} {what} ({now * 100 // max(1, full)}%, {full - now:,} lost)"


def strength(u):
    """A unit's strength in real terms, from its steps: "about 130 tanks"."""
    if "steps" not in u:
        return ""
    if u["type"] == "hq":
        return f"about {HQ_STAFF} men"
    if u.get("real"):                                    # the scenario's own figure, scaled by what is left (RULES 20.4.2)
        n, what, began = u["real"]
        what = "armoured cars" if what == "cars" else what
        return f"about {n * u['steps'] // began:,} {what}"
    each, what = STRENGTH[u["type"]]
    return f"about {u['steps'] * each:,} {what}"


def fuel_words(hexes):
    """How far the fuel goes: "300 km (30 hexes)". A hex is 10 km."""
    return f"{hexes * 10:,} km ({count(hexes, 'hex', 'hexes')})"


def count(n, one, many=None):
    """A number with its noun: "1 step", "2 steps"."""
    return f"{n} {one if n == 1 else many or one + 's'}"
