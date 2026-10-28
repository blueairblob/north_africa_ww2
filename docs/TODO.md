# To do

Everything known to be open, on 22 October 2026, at commit `f784f0d`. Each
item says where the detail is. The pictures, effects and sounds still wanted
are listed in full in `docs/BOM.md`; only the headline is here.

Marks: **[fix]** breaks a rule the project has set itself. **[owner]** a
decision that is the owner's, not a contributor's. **[build]** work agreed or
planned, not done. **[tune]** a number to set by play. **[check]** a fact
not yet confirmed in a source. **[future]** not to be started unasked.

## 1. Fixes

The owner's rule is that every action can be reached by a tap on something
visible (`PLAN.md`, "To keep it so"). One cannot:

- **[fix] In the playback**, going faster (F) and on to the next scene (Right
  arrow or N) are keys only; a click skips the whole playback.

## 2. Decisions for the owner

The game:

- **[owner]** The sizes of the three rules added on 19 October, after play:
  luck (`LUCK_PCT` 10, the owner's figure; the sources give only a ceiling),
  an HQ's weight (`HQ_PCT` 20, a guess) and the lines for the strength words
  (`STRONG_PCT` 66, `WORN_PCT` 33). `docs/RULES.md` 10.4.5, 10.4.7, 14.4.
- **[owner]** Whether a division's HQ should count for something in an attack
  too, and how the screen shows before an attack that an HQ will stand
  behind it (`PLAN.md`, idea 2).
- **[owner]** Whether the player is told a battle's luck. The view carries
  it; the screen does not say it (`PLAN.md`, idea 3).
- **[owner]** Whether reconnaissance earns a closer estimate of the enemy
  (`PLAN.md`, idea 1).
- **[owner]** Sidi Rezegh: whether losses should count for less than the aim,
  whether the aim is said when the game opens, and whether the objectives are
  marked on the map (`PLAN.md`, idea 4).
- **[owner]** 7th Armoured Brigade and the New Zealand Division leave on the
  historical day whatever state they are in. They left because they were
  wrecked; the owner may wish to look again at these two (`docs/SOURCES.md`,
  Dated events).
- **[owner]** Whether the two gentle escarpments east of Sofafi stay as
  barriers (`docs/MAP.md`, Known limitations).
- **[owner]** Where the computer opponent goes in the order of work
  (`PLAN.md`, "Open, for the owner").
- **[owner]** Whether `DESIGN.md` §12 to §15 are rewritten for the web plan,
  as `PLAN.md` ("DESIGN.md: what would change") proposes. Until then
  `DESIGN.md` describes the pygame game.

The art (historical verification deferred by the owner on 28 October 2026):

- **[check, deferred] Counter and aircraft historical verification:** all 91
  ground units have representative art, but the 27 depiction groups still
  have unit-level questions. Air points use labelled aircraft examples, not
  squadron counters. Resume from `docs/COUNTER_AUDIT.md` (*Resume plan* and
  unit-ID table), with source details in `docs/SOURCES.md`. Check dated
  inventories and visual accuracy before calling the set historically
  complete; keep uncertain equipment and counts labelled as such.

- **[owner]** The pennants on the two Axis HQ cars are black and tricolour;
  the briefs ask for red. Keep or redraw.
- **[owner]** Which AI tool made the pictures, and its terms. Not recorded
  (`docs/SOURCES.md`, Art). A commercial release will need it.
- **[owner]** The British and Italian staff cars: which cars. The briefs say
  this is unsettled.
- **[owner]** Files not in the repository: `art/cw_armour.png` (the first
  ChatGPT Matilda trial), the Meshy link, `art/axis_hq_cars.zip`. Keep out,
  or delete. And `art/WWII Desert Kübelwagen Icon.png`, now unused: keep or
  remove.
- **[owner]** Music or sounds for buttons: none exist and none is asked for.

Publishing:

- **[owner]** `docs/CLEAN_ROOM.md` has a checklist "Before publishing this
  project" with four boxes unticked, but the repository is already public.
  Each needs checking and ticking: the sources and their licences (the
  OpenStreetMap attribution is in `docs/SOURCES.md`; whether it must also be
  on the map picture is not checked), nothing from another game, the art's
  origin, and the history of the repository.
- **[owner]** `PLAN.md` asks "whether this file is published with the
  repository". It is: it has been committed since 8 October (`4958f46`).

## 3. Work planned, not done

- **[build]** The computer opponent (`DESIGN.md` §11, milestone 5). There are
  only scripted test players (`engine/players.py`). Not to be started until
  the owner says where it goes.
- **[build]** Levels of difficulty. None exist; luck applies to every game
  alike.
- **[build]** The front-line history overlay (F), in `DESIGN.md` §12. Not
  built.
- **[build]** The optional retro look, in `DESIGN.md` §12. Not built.
- **[build]** A plain Undo, and whether taking back a Join or Split restores
  the group (`PLAN.md`, kept for Full mode).
- **[build]** More scenarios, the campaign and the tutorial (`DESIGN.md`
  milestone 6). Bir Hakeim and the opening of Gazala, 26 May to 11 June 1942,
  is a candidate; its dates are from memory.
- **[build]** Recording golden games, then freezing the Python engine as the
  reference (`PLAN.md`, "Order of work", steps 3 and 4). Not begun.
- **[build]** Finish the historically checked counter subjects in
  `docs/COUNTER_AUDIT.md`: all 18 nation/kind defaults now have picture files
  and additional formation variants, but several pictured models, mixed-unit
  fleets and mixed-group guns still need dated evidence and additional
  representative subjects where warranted.
  A window icon and a title screen do not exist.

## 4. Numbers to tune

- **[tune]** 62 of the 93 named constants in `docs/RULES.md` are marked "to
  be tuned"; each section's table says which. Only four tank figures in
  Crusader are sourced.
- **[tune]** Sidi Rezegh's points, thresholds and par are first guesses. The
  scripted players are no test of balance (`PLAN.md`, idea 4).

## 5. History not yet confirmed

Each is marked where it is used; collected here.

- **[check]** Men and guns of every unit are worked out from establishment,
  not taken from a strength return. The split of the German tanks between
  the two panzer regiments, Ariete's share of the Italian tanks and 32nd Army
  Tank Brigade's strength are from memory (`docs/SOURCES.md`, History).
- **[check]** van Creveld and Playfair are quoted at second hand, through
  Wikipedia (`docs/SOURCES.md`).
- **[check]** Which regiment received the Italian tanks landed on 23 November
  and 1 December; when 4th Armoured Brigade was relieved; when 5th New
  Zealand Brigade went back; the date Division z.b.V. Afrika was renamed
  (`docs/SOURCES.md`, Dated events).
- **[check]** Any dated replacement of men or guns, and how many replacement
  tanks Eighth Army issued: not found.
- **[check]** The seasonal pattern of the weather is from memory
  (`docs/SOURCES.md`, Weather).
- **[check]** The British and German short names are those armies'
  abbreviations as remembered, not checked (`docs/COUNTERS.md`).
- **[check]** Flags: which flag the Indian Army served under was not found;
  Poland's and Italy's are from memory (`docs/COUNTERS.md`, The flags).
- **[check]** Vehicles: the Kübelwagen in Africa in 1941; the AB 41 in Libya
  by November 1941; the striped camouflage and the marks of tank on the
  artist's sheets.
- **[check]** The map: 26 of the 53 places are placed approximately
  (`approx` in `data/features.json`); tracks are joined from place to place,
  not traced; escarpments are checked against the elevation data, not period
  maps; the coastal salt marshes are not marked (`docs/MAP.md`).

## 6. Later, not to be started unasked

- **[future]** Simple mode, the short game for phones: on the shelf since 19
  October 2026.
- **[future]** The web version: the TypeScript engine, the web screen, the
  trial page (`PLAN.md`).
- **[future]** The living map: cloud shadows, sea, dust, moving weather
  (`PLAN.md`).
