# Engineering notes

Working practice for building this game's engine. These come from earlier
work on a deterministic turn-based game engine and from building the map
generator here. They are about *how to build and test*; the rules themselves
come from `DESIGN.md` and the sources in `docs/SOURCES.md`.

## 1. Determinism first

- No random numbers anywhere but the weather, and none from a library even
  there: the weather comes from a generator written out in the rules
  (`docs/RULES.md` 21.2.2) and a seed kept in the state. The same scenario,
  seed and orders must give the same state, on any machine, every time.
- Every choice the engine makes between equals needs a **stated order**: units
  by id, hexes by column then row, directions 0–5. "Whichever comes first in
  the dictionary" is not a rule. Never iterate over a `set` where order matters.
- Use integers for everything that feeds a decision. If a fraction is needed,
  say how it rounds.
- A test that plays the same game twice and compares the final states belongs
  in the suite from the first day.

## 2. State you can compare

- Keep the whole game state in one plain structure that serialises to JSON.
  Then two runs can be diffed, a game can be saved by writing it out, and a bug
  report is a file.
- A game is its scenario plus the list of orders each side gave. Store that,
  and replaying it is the regression test.

## 3. Test with players, not only with cases

- Write **scripted players**: small objects that are shown their side's view
  and return orders. Useful ones: *do nothing*, *always attack*, *always
  retreat*, and above all **explore** — a player that deliberately tries every
  legal order, including pointless ones. It reaches the code a sensible player
  never does.
- Run a **matrix**: every scenario × each side × each option, to the end,
  without a screen. Most rare bugs are found here, not in unit tests.
- After every turn of every such game, assert the **things that must always
  hold** (no two enemy units in one hex, strength never negative, supply
  delivered never more than supply landed, every unit on a passable hex).
- When a rule is changed, the matrix says at once which games changed and on
  which turn.

## 4. One rule, one place, one test

- Number the rules in the specification. Each engine function says which rule
  it implements; each test says which rule it checks.
- One module per subject, each short enough to read in a sitting. A complete
  operational wargame with a computer opponent fits in **well under 10,000
  lines** of Python; if a module is growing past a thousand, the rule behind it
  is probably too complicated.
- Constants are named, in one place per subject, with a comment saying what
  they mean — as `mapgen/build.py` does.

## 5. Where the mistakes are

Experience says the bugs are rarely misunderstandings. They are:

| Kind | Guard |
| --- | --- |
| Periodic rules ("every N turns", "on day D") off by one | test the turn before, the turn, and the turn after |
| Two code paths for the same thing (a special case for roads, for ports, for HQs) | one general rule wherever possible |
| A side effect in the wrong phase | each phase in its own function; state what it may change |
| Data in the wrong place (an objective on the wrong hex) | a **scenario checker** that asserts every place, unit and objective is on the map, on passable ground and where its name says, and that every arrival, withdrawal and replacement names the source of its date and falls inside the game (RULES 12.7) |
| Ties resolved by accident | see section 1 |

## 6. Data people can read

- Game data in JSON, one record per line, with names beside ids. If a person
  cannot find a unit in the file, it will not get checked.
- A test that the saved file is exactly what the writer produces (as
  `tests/test_map.py` does for the map), so hand edits to generated files are
  caught.
- Check positions against more than one source. In the map work, laying three
  period maps over the generated one found a town 30 km out, a site 25 km out
  and a track through the wrong place — after a gazetteer had agreed with all
  three.

## 7. The front end is separate, and has its own traps

- The engine does no input or output. The screen is one kind of player.
- Sound must fall back to silence when no audio device works.
- Latch key presses until the game has read them, or quick taps are lost.
- Sleep while idle, not while the player is waiting.
- Writing a picture to a Windows drive can fail while a viewer has it open:
  write to a temporary file and replace, with a retry.

## 8. Before building, ask what the thing is for

Two expensive mistakes to avoid repeating: building one kind of deliverable
when another was wanted, and assuming a repository was clean of third-party
material without checking it. Say what will be built, in one paragraph, before
building it; and read what is in a folder before publishing it.
