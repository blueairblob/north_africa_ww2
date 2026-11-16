# To do

Everything known to be open on 28 October 2026. The original list was compiled
at commit `f784f0d`. Each item says where the detail is. The pictures, effects and sounds still wanted
are listed in full in `docs/BOM.md`; only the headline is here.

Marks: **[fix]** breaks a rule the project has set itself. **[owner]** a
decision that is the owner's, not a contributor's. **[build]** work agreed or
planned, not done. **[tune]** a number to set by play. **[check]** a fact
not yet confirmed in a source. **[future]** not to be started unasked.

## 1. Fixes

No known open fixes in this section. Playback now has small Back, Next,
Speed and Done controls in the footer, satisfying the owner's tap rule
(`PLAN.md`, "To keep it so").

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
- **[owner]** Whether `DESIGN.md` §12 to §15 are rewritten for the web plan,
  as `PLAN.md` ("DESIGN.md: what would change") proposes. Until then
  `DESIGN.md` describes the pygame game.

The art (historical verification deferred by the owner on 28 October 2026):

- **[check] Axis HQ formation signs:** all Axis HQs now use named markers by
  default instead of car art. The seven previews and the evidence by formation
  are in `docs/AXIS_HQ_ART_REVIEW.md`. Check the 15th Panzer-Division's original
  war-diary plate before adding its triangle sign to the detail card; seek dated
  evidence for the 21st Panzer and Italian formation signs before using Commons
  recreations. The explicit car variants remain available.

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

- **[build]** Directed air missions: command heading and distance, recon flight
  corridor and visible interdiction target. The current global air-point effects
  remain in place while the rules are designed. See `docs/AIR_REVIEW.md` for
  the playtest diagnosis, proposed first slice and decisions needed.
- **[build]** Improve the first playable computer opponent (`engine/computer.py`):
  playtest both sides in Sidi Rezegh and Crusader, assess sector choices,
  supply recovery and scenario balance, then tune its decisions. The owner
  placed this work next on 28 October 2026. Easy, Standard and Hard now use
  the same side view as a human; the first five-seed comparison is in
  `docs/COMPUTER_LEVELS.md`. Larger trials and scenario balance remain open.
  Hard now has a guarded one-turn coordinated attack check. Next, measure its
  interventions against human and varied scripted opponents; add a saved
  multi-turn mission with a reserve, HQ support, withdrawal condition and
  uncertainty about last-seen enemies before claiming an intelligence gain.
  All levels now use the executable High Command orders to garrison required
  places, clear visible corridor blockers and keep a route blocked. Continue
  developing active-opponent relief tactics: the first five-seed Standard
  sample still completed no Commonwealth missions against a point-only Axis.
  Hard also completed none against active Standard Axis and lost secondary
  point margin relative to point-only Hard. Improve coordinated assaults on
  both corridor places before claiming stronger active play. A fresh
  Easy Axis versus Hard Commonwealth five-seed audit also produced five Axis
  blockades; combat, supply and attrition were active, with no engine defect
  found in the sampled games (`docs/SIDI_REZEGH_COMBAT_SUPPLY_AUDIT.md`). Trace
  the Commonwealth's orders and test a joint assault plan before tuning the
  short scenario's duration or starting stock. After the dated opening
  deployment correction, playable Hard initially completed the five-turn
  Commonwealth mission in 0/5 sampled games against passive Axis and 0/5
  against Easy Axis. The 5 November view-based routing and assault update now
  completes it in 5/5 against passive Axis, but still 0/5 against Easy Axis
  (`docs/SIDI_REZEGH_WINNABILITY.md`). The first-contact safeguard now avoids
  throwing scouts into a visible panzer screen, but does not change those
  outcomes. Find and record a legal winning line
  against active defence before treating introductory-game balance as verified.
  A 32-policy concentration sweep in seed 1941 and five-seed 6/8/10-turn
  counterfactuals still found no complete relief mission against Easy Axis;
  inspect the dated Axis reaction and Commonwealth assault route before
  changing the scenario clock. The 18–26 November official-history sequence
  and bounded delayed-response/raid probes are in the winnability note; keep
  free-play balance separate from a dated historical reference playthrough.
  The AI benchmark now records each mission check by turn, so use partial
  progress as well as final wins.
  The short scenario's scored relief corridor now follows the map's vehicle
  track and road around the northern cliff; retain the 10 km map caveat and
  verify the Ed Duda alignment against a period tactical map before claiming
  a precise historical route.
- **[review]** Use the portable Windows ZIP for external playtests. Collect
  scenario/side/turn, screenshots and saves for GUI or rules problems, and
  track feedback before changing the rules or scenario balance. The launch
  flow and package checks are in `docs/REVIEW_RELEASE_PLAN.md`.
- **[build]** The front-line history overlay (F), in `DESIGN.md` §12. Not
  built.
- **[build]** The optional retro look, in `DESIGN.md` §12. Not built.
- **[build]** A plain Undo, and whether taking back a Join or Split restores
  the group (`PLAN.md`, kept for Full mode).
- **[build]** More scenarios, the campaign and the tutorial (`DESIGN.md`
  milestone 6). Bir Hakeim and the opening of Gazala, 26 May to 11 June 1942,
  is a candidate; its dates are from memory.
- **[design]** Keep the long campaign open. Historical dates may introduce
  independent arrivals or constraints, but they must never force captured
  ground, a siege or a retreat. Issue clear High Command aims that respond to
  the played position. Prototype bounded unit-level AI for route, rest and
  local reaction choices under those orders; seed and record variation so
  saves and replays stay exact (`docs/CAMPAIGN_ROADMAP.md`).
- **[campaign]** Follow the confirmed September 1940–November 1942 scope in
  `docs/CAMPAIGN_ROADMAP.md`. First vertical slice: a researched Compass start,
  a second dated chapter, and a continuity transition preserving the played
  state. The catalog and contiguous handoff core now exist and are tested on
  synthetic chapters. A Compass research draft now runs daily on the current
  map. One Hard computer match reached Sidi Barrani on 11 December, one day
  after the historical town capture; the Indian withdrawal is now dated
  14 December. Verify the battle sequence, strengths, stocks and daily
  budgets before listing it for review. A linked, daily **17 December–2
  January** research interval now follows the played Compass trial, with dated
  Australian arrivals and a Commonwealth-only Sollum seahead. One Hard/Hard
  seed reached the end with Sollum and Fort Capuzzo Commonwealth-held and
  Bardia Axis-held. Verify its entry hexes, strengths, seahead throughput,
  serviceability and Axis withdrawal before treating it as historical. The
  linked **3–5 January Bardia research assault** is now playable via Continue
  campaign. Three Hard/Hard seeds ended with Axis still holding Bardia; this
  is a diagnostic, not a balance or impossibility verdict. Verify assembly,
  serviceability, sector geometry and assault support before making a
  historical standalone start or listing it in New battle. Its operation
  order and map-scale limits are in `docs/BARDIA_OPENING_RESEARCH.md`. The
  seed 1940 trace isolated a cliff and full approach hex that blocked 7th RTR
  from the first assault. A map-scale western approach and persistent breach
  mission now yield a 3 January perimeter move and 4 January combined assault,
  still at inadequate odds. Model engineer work, garrison sectors and
  preparation before linked and human balance trials; do not tune an
  unsupported victory into the current draft. The linked research path now
  continues through Tobruk, Derna and Beda Fomm to 9 February 1941. Its
  western Axis counters, pursuit transport, Tobruk assault and Beda Fomm
  surrender need verification and modelling before promotion; see
  `docs/COMPASS_PURSUIT_RESEARCH.md`. A linked 10 February–31 March 1941
  Cyrenaica preparation chapter now schedules the historic relief and Axis
  build-up without resetting the played outcome; a daily April reversal
  follows through 11 April, then a linked 12 April–4 May opening siege chapter and 5–17 May frontier
  preparation, Brevity, Halfaya and Battleaxe chapters carry the played position through 17 June. The June tank reinforcement groups are estimated, not a serviceability model. An actual-strength preservation order now covers
  2nd Armoured, and a dated closure now stops Commonwealth Benghazi landings;
  these chapters still need a siege perimeter and attack model, transport and
  tank serviceability limits, and a separately verified opening; see
  `docs/CYRENAICA_1941_RESEARCH.md`.
  The bounded F6/Game-menu advance now resolves up to five ordinary campaign
  turns with autosaves and stops for contact, arrivals, combat, control or
  supply changes. The full 1 September 1940–30 November 1942 linked trial now
  has continuous dates and a strategic final assessment; see
  `docs/FULL_CAMPAIGN_TRIAL_1940_1942.md`.
  The Crusader chapter now inherits the played November result; validate its
  added formations, mission and battle outcomes next. The
  dated, conditional Tobruk garrison relief, October 22nd Armoured convoy and
  estimated November field availability, and repair/training evidence are in
  `docs/TOBRUK_PREPARATION_1941_RESEARCH.md`. Do not add repaired German tanks
  as unconditional fresh arrivals or replace a counterfactual garrison with
  its historical one.
  The 1942 trial now reaches November. Verify the winter and Gazala rosters,
  serviceability, repair, mines, fuel and Gazala fortifications before treating
  it as a historical simulation. X and XIII Corps, 5th Indian, 44th British and
  10th Armoured now have aggregate counters, but the late-1942 roster still
  lacks full brigade detail and dated serviceable equipment. See
  `docs/CYRENAICA_WINTER_1942_RESEARCH.md` and
  `docs/HISTORICAL_VALIDATION_LEDGER.md`.
  The 9–10 December trace and a tested local crossing are documented in
  `docs/COMPASS_OPENING_RESEARCH.md`; the crossing was restored because it
  exposed an immediate Axis response the draft cannot yet model. Recheck
  surprise, reserves, follow-through, tank serviceability and the map together.
- **[verify]** On the corrected vehicle-passable Sidi Rezegh relief route,
  Standard and Hard computers complete the full mission in **5/5** sampled
  games against passive Axis, but **0/5** against Easy Axis. The passive
  result is a legal winning witness, not evidence of balance against active
  defence. Diagnose the concentration needed to dislodge the Axis panzer
  formations at Sidi Rezegh and Belhamed; compare orders before changing the
  five-turn deadline. See `docs/SIDI_REZEGH_WINNABILITY.md`.
  Keep historical starts independent and old standalone saves readable.
- **[verify]** Calibrate the 10 km hex movement scale, two-day allowances,
  road advantage and fuel against dated unit marches. Travel orders now appear
  in computer games, but the 2:1 road to desert MP ratio is still a game
  estimate; see `docs/SCENARIO_PRESENTATION.md`.
- **[design]** Additional historical episodes and linked-campaign transitions
  need verified dated deployments and an explicit carry-forward schema. The
  Malta/sea selector currently tests aggregate Axis shipping sensitivity only;
  any fuller Mediterranean what-if needs separate, sourced air and sea effects.
- **[build]** Recording golden games, then freezing the Python engine as the
  reference (`PLAN.md`, "Order of work", steps 3 and 4). Not begun.

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
