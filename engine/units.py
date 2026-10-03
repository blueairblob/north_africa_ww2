"""Unit types and what a unit carries (docs/RULES.md §4)."""

TYPES = ("armour", "motorised", "foot", "guns", "recon", "hq")
EXPERIENCE = ("green", "regular", "veteran")

STACK_COMBAT = 2        # combat units in a hex (4.3.1)
STACK_HQ = 1            # HQs in a hex
FUEL_HEX = {"armour": 4, "motorised": 3, "guns": 2, "recon": 2, "hq": 2, "foot": 0}   # tonnes per size per hex
FUEL_RANGE = 30         # hexes of fuel a full unit carries
STORES_CAP = 300        # tonnes of stores per size a full unit carries


def is_vehicle(u):
    return u["type"] != "foot"                                  # 4.1.2


def is_hq(u):
    return u["type"] == "hq"                                    # 4.1.3


def is_hard(u):
    return u["type"] in ("armour", "recon")                     # 4.1.4


def fuel_cap(u):
    return u["size"] * FUEL_HEX[u["type"]] * FUEL_RANGE         # 4.2.5


def stores_cap(u):
    return u["size"] * STORES_CAP                               # 4.2.5


def step_fuel(u):
    """Tonnes of fuel to enter one hex (9.7.1)."""
    return u["size"] * FUEL_HEX[u["type"]]
