# Air orders: playtest review (28 October 2026)

The owner's screenshot `C:\Users\si_wh\Documents\a.png` shows **AIR · INTERDICT** selected. The selection is real, but the present rules give it no map target or visible flight. This note records the current behaviour and the proposed directed-flight design. It does not change the rules.

## What the game does now

Each side assigns its entire pool of 0–3 air points to one mission. Support raises attack and defence totals in the current turn by 5% per point. Interdict reduces the enemy's **truck haul capacity in the following turn's supply phase** by 5% per point; it does not attack a counter or paint a route on the map. Recon adds one spotting hex per point around *every friendly ground unit* at the next orders phase. Rain and sandstorms ground all aircraft. See `docs/RULES.md` §7, `engine/air.py`, `engine/supply.py` 6.5.1, and `engine/view.py` 14.3.

The engine sets the enemy's `interdiction` after the air choice and the next supply phase multiplies its truck lift by `(100 - interdiction) / 100`. `tests/test_engine_weather.py::test_in_bad_weather_nothing_flies` checks the air result, including the 15% value for three points in clear weather. `tests/test_engine_supply.py::test_interdiction_reduces_the_next_supply_phases_actual_haul` checks that the same 15% reduces a real haul from 300 to 255 tonnes. The screen previously showed only the selected mission name and “−5% enemy lift / point,” so a player could reasonably think it had failed. The GUI now says **truck lift, next turn** and gives the actual percentage when selected.

## Directed-flight proposal from the playtest

The owner proposes a command heading and flight distance for each air force, limited by aircraft range and weather. A scout flight would progressively reveal a corridor of terrain and possible enemies along its path. Interdict would need a selected route or area and an observable result, rather than a global percentage. This would make aircraft a map action that a player can understand and watch.

To build that faithfully, first decide:

1. **Origin and range:** whether flights start at a scenario airfield, map edge, or off-map command point; whether the pooled aircraft share one range or have per-type ranges. Current air icons are illustrative and points pool types, so no range data exists.
2. **Information:** terrain is currently always visible. Decide whether the map gains an unexplored layer, or the flight reveals *enemy positions only*. The latter fits the existing map and avoids hiding known geography.
3. **Timing:** decide whether a recon flight reveals as the turn plays and remains in the following orders phase, and what an enemy moving after the flight may leave visible. The present engine reveals only from ground units at the next orders phase.
4. **Interdict target:** choose a road/track corridor, supply route, or area; define how a successful flight reduces enemy haul on that route. The current truck-lift rule has no local route modifier.
5. **Weather and opposition:** state which weather cancels or shortens a flight and how, if at all, interception or anti-air fire is resolved. Keep outcomes deterministic from the scenario seed and orders.

Recommended first playable slice: **one visible recon flight path per side**, with a chosen heading and bounded distance, revealing enemy counters in a narrow corridor during playback and in the next orders view. Keep terrain visible. Once that is testable, use the same path control for targeted interdiction. The air popup should preview the route and its range before the player commits. This is a rules and information-model change, so the engine, view leak checks, replay, save format, and scenario air data must change together.
