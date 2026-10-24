# Handoff: a brief for a reviewer

Written 22 October 2026, at commit `f784f0d`, for a review of the whole
project by someone, or something, that has not worked on it.

## What the game is

*Benghazi Handicap: North Africa 1940–42* is an original hex wargame of the
desert campaign, at the scale of divisions and their brigades and regiments.
The aim, in the owner's words: the simplicity and playability of the small
8-bit desert wargames, with historical supply and reinforcements underneath.
A turn is two days; a hex is 10 km; the map is 123 × 44 hexes, generated from
public geographic data. One full scenario, Operation Crusader (18 November
to 27 December 1941, 22 turns, 91 units), and one short one cut from it,
Sidi Rezegh (five turns, one aim).

It is to be a commercial product. The work now is to make the pygame version
good to play. A web and phone version is planned for later and is not begun.

## Read first, in this order

1. `README.md`: what is built and how to run it.
2. `DESIGN.md`: the design. Where it and the rules differ, the rules are right.
3. `docs/RULES.md`: the rules, numbered, every constant named with its source
   or marked "to be tuned". The engine cites these numbers.
4. `docs/TODO.md`: everything known to be open.
5. `docs/BOM.md`: every picture, effect and sound, and what is still wanted.
6. `PLAN.md`: the owner's decisions by date, and the plan for later.
7. `docs/SOURCES.md`: where every fact and date comes from, and what is unsure.
8. `docs/CLEAN_ROOM.md`: what the project may and may not use. Read it before
   suggesting any change.
9. As needed: `docs/COUNTERS.md` (counters, tiles, art, flags), `docs/MAP.md`
   (the map generator), `docs/ENGINEERING_NOTES.md` (how it is built and
   tested).

## The rules of the project

These bind a reviewer as much as a contributor.

- **Clean room.** The game must be original. Do not open, list or search any
  folder outside this repository, or anything under `local/`. Take rules from
  `DESIGN.md` and from history, never from another game's tables, numbers or
  text. Where a figure is needed, derive it from a historical source and say
  which. A mention of how an older game did something is background, not a
  value to copy.
- **Dates are the backbone.** Every dated event has a real date and a named
  source, and the unsure ones say so.
- **Say what is uncertain.** "I'm not sure of this figure" is wanted; a
  confident guess is not.
- **Every action by a tap** on something visible, as well as any key.
- **Determinism.** The same scenario, seed and orders give the same game.
  Chance comes only from the seed, by a generator written out in the rules
  (weather, §21; a battle's luck, 10.4.7).
- **The repository is public.** Nothing from `local/` goes in it, nor any
  picture or text of another game.

## How to run it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                        # 301 tests, about 150 s
.venv/bin/python -m engine crusader attack nothing   # a whole game, no screen
.venv/bin/python -m screen sidi_rezegh --axis attack # play the short scenario
SDL_VIDEODRIVER=dummy .venv/bin/python -m screen crusader --shot frame.png   # one frame, no window
```

## Where the code is

| Folder | What | Lines |
| --- | --- | --- |
| `engine/` | the rules: pure Python, integers, no input or output but reading a scenario | about 2,300 |
| `screen/` | the pygame screen; `session.py` and `replay.py` hold its behaviour and have no pygame in them | about 4,100 |
| `mapgen/` | builds `data/map.json` and the map picture from public data | |
| `countergen/` | draws the fallback counter pictures and cuts the artist's | |
| `data/` | the map, the places and routes, the two scenarios | |
| `tests/` | 19 files; each test names the rule it checks | |

## Where things stand

Built: the map generator; the rules; the engine (movement, zones of control,
supply by truck haul from ports and the railhead, combat with retreat and
advance, recovery, fortification, morale, groups, reinforcement and
withdrawal on sourced dates, weather, a battle's luck, the weight of an HQ,
the enemy seen as an estimate, victory); the screen (orders, overlays, the
group shown as an order of battle, reports, the Timetable, the playback with
sound, saved games). Scripted test players only.

Not built: the computer opponent; levels of difficulty; most of the art
(`docs/BOM.md`). The three controls that can be reached only by a key are
listed as fixes at the top of `docs/TODO.md`.

## What the review should look at

- Whether the rules are complete and closed: every situation one outcome,
  every tie broken by a stated order (`DESIGN.md` §13).
- Whether the engine does what `docs/RULES.md` says, and the tests check it.
- Whether the history is right and its sources are named; the doubtful
  points are listed in `docs/TODO.md` §5.
- Whether the game is easy and gratifying to play: the owner's test of
  "good enough" (`PLAN.md`).
- Whether anything in the repository could breach the clean room.

## Working with the owner

- Commit only when asked. When asked, push to `origin master` and end the
  commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Short, plain summaries of what changed and what is still uncertain.
- Pygame first. Do not start the web version, the trial page, Simple mode or
  the living map unasked.
