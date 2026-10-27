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

The art:

- **[build] Finish mismatched counter art:** verify the three new painted
  recon types against formation inventories (`docs/COUNTER_AUDIT.md` lists
  all 91 scenario units by sprite), especially the composite CW
  armoured-car unit and the unverified original RECAM AB41 photo (a 2018
  military-history article does independently identify AB41s in component
  units); verify the new
  infantry artwork and all representative vehicles
  against formation equipment returns. German 10.5 cm field
  howitzer, Halfaya 88 mm and one towed
  Panzerjäger I variant are now distinct. Verify the gun marks, losses,
  command attachment and mixture in the Halfaya, Boettcher, Division Afrika
  and combined 39/605 formations before treating each picture as definitive.
  The painted NZ Divisional Cavalry carrier variant is representative only:
  the official history also mentions light tanks; verify the scenario's
  `cars: 30` strength abstraction separately (it is not 30 armoured cars).
  Mixed-equipment picture hover notes now identify 8 RTR Valentines in 1st
  Army Tank Brigade, 1 RTR cruisers in 32nd and other Tobruk artillery types;
  the 5 November 1941 fortress artillery return cannot establish unit 354's
  scenario count of 72 guns or its exact command boundaries. Verify those
  against original war diaries.
  A dated German tank return analysed in *Scientia Militaria* supports the
  Panzer III as a majority picture for Panzerregiment 5, but its 120 tanks
  differ from the scenario's remembered 116; resolve counting basis before
  changing gameplay. Marmon-Herrington Mk III cars are documented in KDG
  squadrons, not proven for all of composite unit 305 or the painted model.
  German reconnaissance battalions 3 and 33 are listed with both Sd.Kfz. 222
  and heavier cars by 30 December 1941, but that later table has an
  inconsistent vehicle count; inspect the archived return and 18 November
  strengths before assigning exact car proportions.
  The original painted Matilda replaces the old sheet cut, but its
  Caunter-inspired paint has not been confirmed for either brigade.
  Counter art for mixed Matilda/Valentine and later Crusader/Stuart brigades
  still represents only a predominant/typical type; 7th Armoured Brigade now
  shows an A13 rather than a generic Crusader, but also included A10s and
  Crusaders. Confirm equipment by formation and date before claiming every
  unit is depicted exactly.
  The 7th Bersaglieri has its own feathered-helmet infantry variant;
  8th and 9th now have an open-lorry variant with feathered riders. The
  vehicle is illustrative. Verify each regiment's dated lorry/motorcycle
  mix: a single counter cannot claim all its troops rode either type.
- **[build] Air visuals:** the selector illustrates RAF and Axis fighter,
  bomber and reconnaissance choices using representative silhouettes, but
  its air points pool multiple aircraft, national air arms and missions.
  The Axis recon icon now illustrates a Bf 110 from a 23 November 1941
  operations report; it is not a unit assignment or an 18 November sortie.
  A compiled 18 November order of battle names `2(H)/14`, and a study
  describes its 19 November reconnaissance without verifying aircraft type.
  The Hs 126 is a plausible army-cooperation candidate, but these sources
  do not establish that Staffel's dated aircraft inventory
  (`docs/SOURCES.md`, Art). Research dated unit allocations before
  adding any aircraft counters; do not mistake examples for sortie records.

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
