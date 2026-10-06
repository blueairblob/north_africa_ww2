"""Unit types and what a unit carries (docs/RULES.md §4)."""

TYPES = ("armour", "motorised", "foot", "guns", "recon", "hq")
EXPERIENCE = ("green", "regular", "veteran")

STACK_FORMATIONS = 2    # formations in a hex (20.1.4)
FUEL_HEX = {"armour": 4, "motorised": 3, "guns": 2, "recon": 2, "hq": 2, "foot": 0}   # tonnes per size per hex
FUEL_RANGE = 30         # hexes of fuel a full unit carries
STORES_CAP = 300        # tonnes of stores per size a full unit carries


def is_vehicle(u):
    return u["type"] != "foot"                                  # 4.1.2


def is_hq(u):
    return u["type"] == "hq"                                    # 4.1.3


def is_hard(u):
    return u["type"] in ("armour", "recon")                     # 4.1.4


MEN_STEP, TANKS_STEP, GUNS_STEP = 800, 10, 12       # what a step stands for (20.4.1)
REAL = (("tanks", TANKS_STEP), ("men", MEN_STEP), ("guns", GUNS_STEP), ("cars", 15))


def real_of(spec):
    """A unit's real strength on the scenario's first day: [number, what], or None (20.4.1)."""
    for what, _ in REAL:
        if what in spec:
            return [spec[what], what]
    return None


def steps_of(spec):
    """A unit's steps: as given, or worked out from its real strength, to the nearest, at least one."""
    if "steps" in spec:
        return spec["steps"]
    for what, each in REAL:
        if what in spec:
            return max(1, (spec[what] + each // 2) // each)
    raise ValueError(f"unit {spec.get('id')} has neither steps nor a real strength")


def stacked(units):
    """The formations these units count as for the stacking limit: an HQ is a few hundred men
    and takes no ground, so only the others count (20.1.4)."""
    return {formation(u) for u in units if u["type"] != "hq"}


def formation(u):
    """What a unit belongs to: its division's HQ, or itself if it is independent (20.1.2)."""
    return u.get("parent") or u["id"]


def fuel_cap(u):
    return u["size"] * FUEL_HEX[u["type"]] * FUEL_RANGE         # 4.2.5


def stores_cap(u):
    return u["size"] * STORES_CAP                               # 4.2.5


def step_fuel(u):
    """Tonnes of fuel to enter one hex (9.7.1)."""
    return u["size"] * FUEL_HEX[u["type"]]
