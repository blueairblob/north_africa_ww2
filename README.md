# Benghazi Handicap: North Africa 1940–42

An original operational wargame of the North African campaign, 1940–1942:
small and neat like the 8-bit desert wargames, but with the real ground, the
real tempo of a desert battle and, above all, the real supply problem.

- **`DESIGN.md`** — the game: scale, map, units, sequence of play, supply,
  combat, orders, scenarios, the computer opponent, presentation.
- **`docs/SOURCES.md`** — where the map and the orders of battle come from.
- **`docs/CLEAN_ROOM.md`** — what this project may and may not use.

Status: design, plus the first milestone — the **map generator**.

## The map

![The generated map](map.png)

The map is not drawn by hand: `mapgen/` builds it from public geographic data.

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m mapgen all      # fetch the data, build data/map.json, draw map.png
.venv/bin/python -m pytest tests    # 15 checks
```

- **123 × 44 hexes of 10 km**, from west of El Agheila to Alexandria and from the
  Cyrenaican coast south to Siwa.
- **Terrain per hex**: sea, desert, rough going, deep depression (the Qattara
  Depression), sand sea — from the coastline and from elevation and slope.
- **Escarpments on hex edges**, found where the ground drops sharply across an
  edge; hills ringed by escarpments become rough ground.
- **Places and routes** from `data/features.json` (38 places; the coast road,
  desert tracks and the railway): each route finds its own way over the
  generated ground between the places it names, and where it has to climb an
  escarpment, that crossing becomes a **pass**.
- The result, `data/map.json`, is readable: one row of terrain letters per map row.

Known limitations of this first version (see `docs/MAP.md`):

- the Sollum–Halfaya escarpment is found only in part, so its passes are not yet
  placed by the generator;
- about 15 period sites have approximate coordinates, and the tracks are joined
  from place to place rather than traced from period maps;
- the sand sea outline is approximate; the coastal salt marshes are not marked.

## The name

**The Benghazi Handicap** was the soldiers' name — the Australians', first — for
the retreat from Benghazi to Tobruk in the spring of 1941, with Rommel close
behind. The race was run again, in both directions: Benghazi changed hands five
times in under two years, as each advance along the coast road ran out of supply
and was thrown back. The retreat from the Gazala line in June 1942 earned its
own name, the *Gazala Gallop*.

> **Etymology.** Named for the great speed of the retreat; *handicap* is in the
> horse-racing sense. The field was large, the going was firm to dusty, and the
> favourite changed at every meeting.

Why this name:

- **It says what the game is about.** The campaign was decided by distance and
  supply — how far an army could go before its trucks could no longer feed it —
  and that is the centre of this design (`DESIGN.md` §6).
- **It is historical and nobody's product.** It is a period nickname (it is the
  title of a chapter in the Australian official history), not a trademark. A few tabletop wargame supplements have used it as a subtitle; no
  computer game uses it as its title.
- **It stands apart from other games.** Plainer names were considered and
  dropped because they sit too close to existing titles: "Desert War" (Matrix
  Games' *Desert War 1940–1942*, and a scenario title in older games) and
  "Desert Rats" (CCS, 1985, the 8-bit game that inspired this one).
- **The subtitle says the rest.** "North Africa 1940–42" tells a newcomer the
  subject at a glance.

This is an original game. It shares a subject — a public piece of history —
with many other wargames, and nothing else: its map is generated from public
geographic data, its orders of battle are compiled from historical sources, and
its rules, text and art are its own (`docs/CLEAN_ROOM.md`).
