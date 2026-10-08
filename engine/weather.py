"""The weather: the one thing in the game that is drawn by chance (docs/RULES.md §21).

It is drawn from a seed fixed when the game begins, so a game is still its scenario, its
seed and its orders, and replays the same. Nobody is shown the seed, so nobody knows the
weather of a later turn: a side is told the weather of the turn it is ordering, and one
word about the next that is often wrong.

The numbers come from a generator small enough to write down and to work by hand
(21.2.2): no product in it passes 2 to the power 47, so it gives the same numbers in any
language that has whole numbers of 53 bits."""
from datetime import date, timedelta

from . import state as S

KINDS = ("clear", "rain", "sandstorm")                  # in the order they are drawn (21.3.2)
MODULUS = 2147483647    # the generator: x becomes x times MULTIPLIER, modulo MODULUS
MULTIPLIER = 48271
WARM = 8                # numbers thrown away first, so that a small seed gives no small first draw
ODDS = {                # month -> per cent of turns with (rain, sandstorm) (21.3.1)
    1: (12, 3), 2: (10, 3), 3: (4, 8), 4: (2, 14), 5: (1, 10), 6: (0, 6),
    7: (0, 4), 8: (0, 3), 9: (1, 3), 10: (4, 3), 11: (6, 3), 12: (11, 3),
}
OUTLOOK_HIT = 80        # per cent of bad turns the outlook before them called unsettled
OUTLOOK_FALSE = 15      # per cent of clear turns the outlook before them called unsettled
STORM_SIGHT = 1         # hexes at which any unit spots in a sandstorm
STORM_MOVE_PCT = 50     # per cent of its allowance a unit has in a sandstorm
RAIN_COST_PCT = 200     # per cent of its cost a vehicle pays in rain for a step not along a road


def draws(seed, turn):
    """The turn's two numbers from 0 to 99: the first settles its weather, the second what
    the outlook says of it the turn before (21.2.2)."""
    x = seed
    for _ in range(WARM + 2 * turn - 1):
        x = x * MULTIPLIER % MODULUS
    return x * 100 // MODULUS, x * MULTIPLIER % MODULUS * 100 // MODULUS


def odds(scenario, turn):
    """Per cent of turns with (rain, sandstorm) at this turn's date: the scenario's own table
    if it has one, else the table for the month (21.3.1)."""
    own = S.value_at(scenario, scenario.get("weather", []), turn, None)
    if own is not None:
        return own.get("rain", 0), own.get("sandstorm", 0)
    day = date.fromisoformat(scenario["start"]) + timedelta(days=2 * (turn - 1))
    return ODDS[day.month]


def of(seed, turn, scenario):
    """The weather of a turn (21.3.2). With no seed there is no weather: every turn is clear."""
    if seed == 0:
        return "clear"
    rain, storm = odds(scenario, turn)
    n = draws(seed, turn)[0]
    return "rain" if n < rain else "sandstorm" if n < rain + storm else "clear"


def outlook(seed, turn, scenario):
    """What is said during this turn of the next: "fair" or "unsettled" (21.5)."""
    if seed == 0:
        return "fair"
    bad = of(seed, turn + 1, scenario) != "clear"
    return "unsettled" if draws(seed, turn + 1)[1] < (OUTLOOK_HIT if bad else OUTLOOK_FALSE) else "fair"


def weather_step(state, scenario):
    """The turn's weather is settled, before the Supply phase (21.3.3)."""
    state["weather"] = of(state["seed"], state["turn"], scenario)


def flying(kind):
    """Whether aircraft fly (21.4.1)."""
    return kind == "clear"


def sight(kind, hexes):
    """How far a unit that spots at so many hexes spots in this weather (21.4.2)."""
    return min(hexes, STORM_SIGHT) if kind == "sandstorm" else hexes


def allowance(kind, mp):
    """A movement allowance in this weather (21.4.3)."""
    return mp * STORM_MOVE_PCT // 100 if kind == "sandstorm" else mp
