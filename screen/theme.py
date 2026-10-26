"""Colours and sizes (docs/COUNTERS.md for the hex and counter sizes)."""
import re

BASE_HEX = 64                       # a hex, corner to corner, in the base map (mapgen.render.BASE_HEX)
ZOOM_MAX, ZOOM_START = 2.0, 1.0     # the base map is scaled by the zoom; the least zoom shows the whole map
ZOOM_STEP = 1.2
COUNTER = 0.74                      # a counter's side as a share of the hex: the most that keeps neighbours apart
PANEL = 420                         # the Field Atlas details ledger's width
BAR = 32                            # the message line under the map, above the command console
CONSOLE = 100                        # persistent full-width command footer
MASTHEAD = 54                       # map title band, over the map's top paper margin
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
COMMAND = {"axis": (42, 49, 40), "cw": (40, 77, 112)}
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
CLAIMED = ("tanks", "armoured cars", "guns", "men")                 # the order a battle's claim is told in
MORALE = ("Very poor", "Poor", "Very low", "Low", "Fair", "Normal", "Good", "Very good", "Excellent")
# the order bar: name, label, key shown
BUTTONS = (("move", "Move", "M"), ("attack", "Attack", "A"), ("road_march", "Travel", "T"),
           ("hold", "Hold", "H"), ("dig_in", "Dig in", "D"), ("rest", "Rest", "R"),
           ("join", "Join", "J"), ("split", "Split", "X"), ("recall", "Recall", "C"),
           ("next", "Next unit", "Space"), ("done", "End turn", "Enter"))
LAYERS = (("s", "Supply", "S"), ("z", "Zones", "Z"), ("k", "Key", "K"))   # the map's layers, behind the button in its corner
GAME = (("save", "Save game", "F5"), ("load", "Load game", "F9"),
        ("screenshot", "Screenshot", "F12"))  # behind the Game button beside Layers
MARGIN = 46             # base-map pixels of paper shown beyond the map's edge, for its border
HQ_STAFF = 300          # a headquarters' nominal strength in men, for show: it has one step in the rules
STRONG, WORN, WEAK = (40, 90, 190), (214, 126, 24), (200, 40, 30)   # strength: under full, under 70%, under 50%
PREVIEW = (70, 150, 255)                                           # the way being chosen: blue, like one ordered
HAUL = (255, 214, 40)                                              # a supply haul: yellow
BADGE = (255, 214, 40)                                             # the trouble badge on a counter
ARM = ("armour", "motorised", "foot", "guns", "recon", "hq")       # which unit of a pile is shown on top
NAMED = 90              # a counter this many pixels across or more carries its unit's short name and its pace
TILE = (218, 207, 172)  # the pale face of the tile in the panel
TILE_H = 210            # ...and its height; it is as wide as the panel's text
FLAG = (42, 28)         # the flag in its top right corner
FLAG_BLUE, FLAG_RED, FLAG_WHITE = (1, 33, 105), (200, 16, 46), (244, 242, 236)
FLAG_NAME = {"uk": "United Kingdom", "nz": "New Zealand", "au": "Australia", "in": "India", "sa": "Union of South Africa",
             "pl": "Poland", "de": "Germany", "it": "Italy"}
# a Commonwealth unit flies its own country's flag: told from its name, or failing that its division's
CONTINGENT = (("New Zealand", "nz"), ("South African", "sa"), ("Indian", "in"), ("Australian", "au"), ("Polish", "pl"))
PACE = {"cw": PAPER, "de": (160, 204, 240), "it": PAPER}           # the pace on a counter: not the strength's colour
# a division's notch on its units' counters, in the order of the divisions' HQs within a side: the
# strongest against any face first (docs/COUNTERS.md)
DIVISION = ((200, 44, 36), (246, 206, 48), (246, 242, 230), (34, 30, 26), (236, 130, 30), (140, 70, 170),
            (240, 140, 170), (130, 82, 40), (70, 200, 210), (170, 220, 60))
# a unit's name cut down for its counter, the first that matches first: the British Army's own
# short forms, the German Army's, and for the Italians the arm alone (docs/COUNTERS.md)
BRIEF = (("Armoured car regiments", "Armd Cars"), ("Reconnaissance battalions", "Recce"), ("Reconnaissance", "Recce"),
         ("Polish Carpathian", "Carpathian"), ("Support Group", "Sp Gp"), ("Divisional Artillery", "Div Arty"),
         ("Divisional Cavalry", "Div Cav"), ("Division artillery", "Div Arty"), ("South African", "SA"),
         ("New Zealand", "NZ"), ("Army Tank", "Army Tk"), ("Army tank", "Army Tk"), ("Armoured", "Armd"),
         ("Motorised", "Mot"), ("Infantry", "Inf"), ("Indian", "Ind"), ("Guards", "Gds"),
         ("Panzerjaeger-Abteilungen", "Pz.Jg."), ("Aufklaerungs-Abteilung", "Aufkl.Abt."),
         ("Panzer-Regiment", "Pz.Rgt."), ("Schuetzen-Regiment", "S.R."), ("Artillerie-Regiment", "Art.Rgt."),
         ("Infanterie-Regiment", "Inf.Rgt."), ("Afrika-Regiment", "Afr.Rgt."), ("Panzer-Division", "Pz.Div."),
         ("Panzergruppe", "Pz.Gr."), ("Panzer group", "Pz Gp"), ("Artillerie der Division", "Art."), ("Division z.b.V.", "zbV"),
         ("Artillery Group", "Gp"), ("III./255 und III./347", "III/255+347"), (" und ", ", "),
         ("Corpo d'Armata di Manovra", "CAM"), ("Corpo d'Armata", "Corpo"), ("Reggimento artiglieria celere", "Art. Celere"),
         ("Reggimento artiglieria", "Artigl."), ("Reggimento fanteria", "Fanteria"), ("Reggimento bersaglieri", "Bersaglieri"),
         ("Reggimento carri", "Carri"), ("Brigade", "Bde"), ("brigade", "Bde"), ("Division", "Div"), ("division", "Div"),
         ("garrison", "Garr"), ("Regiment", "Regt"))


def order_name(name, units=()):
    """An order by the name the player sees: a road march is Travel for vehicles and March for
    any group with men on foot."""
    if name == "road_march" and any(u["type"] == "foot" for u in units):
        return "March"
    return ORDER_NAME[name]


# the Timetable tab's sections: the kinds of event under each heading; the last takes whatever is left
TIMETABLE = ((("withdrawal",), "Withdrawals"), (("arrival", "replacement"), "Reinforcements"), ((), "Other"))


def flag_of(nation, name, division=""):
    """Whose flag a unit flies: Germany's, Italy's, or for the Commonwealth its own country's."""
    if nation != "cw":
        return nation
    return next((code for words in (name, division) for part, code in CONTINGENT if part in words), "uk")


def short(name):
    """A unit's name as its counter carries it: "4th Armoured Brigade" is "4 Armd Bde"."""
    for long, cut in BRIEF:
        name = name.replace(long, cut)
    return re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", name)


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
