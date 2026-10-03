# Handoff: milestone 2, the rules specification

Paste everything below the line as the first message of a new session started
in this folder.

---

You're picking up an original wargame project, "Benghazi Handicap: North Africa
1940–42", in this folder. Milestone 1 (the map) is done. Your job is milestone 2:
write the rules specification, docs/RULES.md. Don't write engine code yet.

## What the game is

A small operational wargame of the desert campaign on a hex map, for the public
repo github.com/blueairblob/north_africa_ww2 (branch master). The owner's aim,
in his words: the simplicity and playability of the small 8-bit desert wargames,
at division level, plus historical supply and reinforcements. He wants the
surface small (a few dozen counters, six orders) and the engine underneath
"very sophisticated", with rules solid enough that two computer players can
play each other with no screen. There is no randomness anywhere: same scenario
and same orders must always give the same result.

## Read first, in this order

1. DESIGN.md — the design. Sections 2, 4–9, 11, 13 and 14.1 (the complexity
   budget) matter most for the rules.
2. docs/ENGINEERING_NOTES.md — how to build and test; section 1 (determinism,
   stated tie-break orders) applies directly to how rules must be written.
3. docs/MAP.md and data/map.json — what the map actually contains: six terrain
   letters (~ sea, . desert, ^ rough, v depression, s sand sea, o oasis),
   escarpments on hexsides with a high side, passes, routes (road, track,
   rail), places, the frontier line. Flat-topped hexes, 10 km, 123 × 44.
4. docs/SOURCES.md — where historical facts come from.
5. docs/CLEAN_ROOM.md — the boundary below.

## The clean-room boundary (important)

This game must be original. The earlier contributor had studied a 1985 game's
code in detail and therefore could not write these rules; you can, because you
haven't. Keep it that way:

- Do not open, list or search any folder outside this repository, or anything
  under local/ in this folder.
- Take rules from DESIGN.md and from history, never from another game's
  tables, numbers or text. Where you need a figure (port capacity, fuel use,
  movement rates), derive it from the historical sources and say which.
- If I mention how an older game did something, treat it as background, not as
  a value to copy.

## What docs/RULES.md must be

DESIGN.md section 13 defines "solid": complete, written down, closed, checked,
replayable. Concretely:

- Numbered rules (e.g. 5.3.2), each one testable, so engine tests can cite them.
- Every situation has exactly one outcome. Cover the hard cases explicitly:
  two sides moving into the same hex, units swapping hexes, retreat with
  nowhere to go, a supply route cut partway through a turn, stacking limits,
  what happens when an ordered unit has no fuel, simultaneous attacks on one
  defender, ties of every kind (broken by a stated order such as unit id, then
  column, then row — never by chance).
- A legal-orders section: for each of the six orders, exactly when it is
  legal and what the engine replies when it isn't.
- The turn sequence as phases, each saying what state it may change.
- Supply in full: fuel and stores, ports and their capacity, the truck haul
  and its cost with distance, HQs, dumps, what shortage does. This is the
  heart of the game and should be the most thorough part.
- Reinforcements and withdrawals by date.
- Every number as a named constant with its meaning and its source, collected
  in one table per section. Mark each as "from source" or "to be tuned".
- A list of invariants that must hold after every turn.
- What each side can see (fog of war), since computer players are given only
  their side's view.
- A one-page "what the player must learn" summary at the end, to prove the
  complexity budget is met.

Units of measure: integers throughout; state how anything rounds.

## Decisions that are the owner's, not yours

Raise these as questions when you reach them, with your recommendation, and
carry on with the rest meanwhile:

- Whether the frontier wire is a rule or only drawn.
- Whether oases matter for supply (water) or are just terrain.
- How Tripoli and the Nile Delta, both off the map, feed supply onto it.
- Stacking: one counter per hex, or more.
- Whether the two gentle escarpments east of Sofafi stay as barriers
  (docs/MAP.md, "Known limitations").

## How to work here

- Python is in .venv; tests run with `.venv/bin/python -m pytest -q` (26 pass
  now); the map rebuilds with `.venv/bin/python -m mapgen all`.
- Commit only when I ask. When I do, push to origin master and end the commit
  message with: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
- The repo is public: nothing from local/ goes in it.
- I like short, plain summaries of what changed and what is still uncertain,
  and I'd rather hear "I'm not sure of this figure" than a confident guess.

Start by reading the five documents, then give me an outline of RULES.md
(section headings and the open questions) before writing it in full.
