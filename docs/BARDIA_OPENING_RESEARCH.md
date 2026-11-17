# Bardia: next Compass chapter research gate

**Status, 5 November 2026:** `data/scenario_drafts/compass_interval.json`
covers **17 December–2 January** and `data/scenario_drafts/bardia_assault.json`
covers **3–5 January**. Both are daily, opt-in **linked research chapters**:
the first accepts the played Compass result, and the second accepts the
played interval. Neither is a validated historical scenario or a standalone
battle. `engine/campaign.py` still rejects any jump over unmodeled days.

## Dated facts and operational aim

- The [6th Australian Division operation order of 1 January](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-B.html)
  orders an attack on the central and southern Bardia defences on **3 January**.
  Phase I starts at 05:30 with **16th Australian Infantry Brigade**, 7th RTR,
  engineers and artillery; 2/6th Battalion demonstrates against the southern
  perimeter. Phase II starts at 11:30 with **17th Australian Infantry Brigade**,
  7th RTR and supporting arms. **19th Australian Infantry Brigade** covers
  and relieves assembly positions. The order also assigns RAF 208 Squadron
  tactical reconnaissance. These are tasks and timings, not counter strengths.
- The [Australian War Memorial battle account](https://www.awm.gov.au/collection/E84311)
  dates the breach to **3 January**, the capture of Bardia town to late
  **4 January**, and the end of southern perimeter resistance to the morning
  of **5 January**. It describes a **29 km** defended arc. At the game's
  approximately 10 km per hex scale, the posts, ditch, minefields, town and
  inner defences cannot be resolved as a single ordinary city hex.
- The [UK official history, volume I, chapter XV](https://www.ibiblio.org/hyperwar/UN/UK/UK-Med-I/UK-Med-I-15.html)
  says Bergonzoli gathered all or parts of the **1st and 2nd Blackshirt,
  62nd Marmarica, 63rd Cirene and 64th Catanzaro** divisions, with fortress
  and frontier troops: approximately **45,000 men and over 400 guns** in the
  Bardia perimeter. Contemporary British estimates were much lower. It says
  **7th RTR had 23 serviceable tanks** for the assault; this is an availability
  count, not necessarily the regiment's total surviving vehicles. The
  **16th British** Brigade was *not* used in the assault; distinguish it from
  the attacking **16th Australian** Brigade.

The chapter's Commonwealth operational order should be **breach the western
perimeter, capture Bardia town, and eliminate or contain the remaining southern
garrison**. The Axis order is **hold the perimeter and deny the harbour**.
Town ownership alone cannot indicate that the southern defences have yielded;
the 4–5 January sequence is a direct counterexample. A mission could track a
coarse west/south sector plus Bardia, but the sector geometry must first be
checked against the 1:50,000 Bardia North and South sheets cited in the
operation order. Any chosen hexes will be approximate.

## The interval is part of the operation

The [Australian official history, *Before Bardia*](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-7.html)
places 16th Australian Brigade between Sidi Barrani and Buq Buq on
**17 December**, at Sollum on **18 December**, and on the Halfaya route into
Cyrenaica on **19 December**. Mackay took command of the Sollum area on
**21 December**; 7th Armoured screened the Bardia–Tobruk approaches while
Australian brigades gathered. These are strategic moves and reliefs, not 17
days of motionless counters. The UK official history says Sollum port fell on
**16 December** and helped sustain the advance, but water, fuel, unloading and
ammunition remained binding constraints; late ammunition delayed the planned
assault by a day. Naval and air bombardment occurred before the ground attack.

The gap resolver should advance the actual played state **one day at a time**
or by bounded dated events, with player orders for movement/screening and
explicit arrivals, withdrawals, supply, fuel, water and tank serviceability.
It must preserve earlier combat losses and place control. It must not reset a
player's surviving 7th RTR to a historical total of 23 or teleport a defeated
Italian division back to full strength. A standalone Bardia start can use a
historical reference state; campaign continuation should carry the earned one.
The existing handoff contract already enforces this distinction for contiguous
chapters.

The engine now accepts a scenario-specific `landing_points` entry for Sollum.
It makes Sollum a supply outlet only in scenarios that use it, leaving the
permanent map and older saves alone. The amount landed remains an **estimate**
to validate: the interval currently uses **200 tonnes per two-day equivalent**,
or 100 tonnes on a clear full-condition day, and restricts new landings to
Commonwealth ownership. This capability does not yet model the historical
shortages of water, vehicles or unloading gear separately.

The interval keeps surviving Compass units and all actual places, stocks and
losses. Its copied opening placements are checker placeholders: they are never
used for a linked run and should not be interpreted as a 17 December order of
battle. The 6th Australian Division HQ and 16th Brigade enter on 17 December,
the 17th Brigade and artillery on 22 December, and the 19th Brigade on
1 January. The published history supports movement or forward-area dates;
the exact entry hexes and counter strength are estimates. Italian XXIII Corps
HQ and 1st/2nd Blackshirt counters enter on 17 December to model a garrison
already gathered at Bardia; their **6,000 and 4,800 men are game estimates**,
not strength returns. The interval gives no proof that the full roughly
45,000-man fortress is represented at the proper local strength.

The Compass draft now carries a Bardia fortification at the town and two
adjacent perimeter hexes, so the linked chapters retain those defences. The
fort levels are **game estimates**; a 10 km hex cannot represent the separate
posts, ditch, mines and prepared gun positions. The interval marks
southwestern and southern assembly hexes for the Commonwealth and instructs
the computer not to assault Bardia before 3 January. Human players retain
the choice to attack earlier. The Bardia mission requires both occupation of
the town and clearance of a short, vehicle-passable **southern sector proxy**
through the adjacent hexes to Fort Capuzzo. This is a scoring abstraction,
not the documented course of a road or the exact defensive line. If the town
falls but an Axis unit holds that proxy, neither side earns a mission victory.

One Hard/Hard seed `1940` linked run completed the first 25 daily turns with
engine invariants intact. It finished the interval with Commonwealth control
of Sollum, Axis control and occupation of Bardia, and all five Australian
counters arrived. The three-chapter run to 5 January was legal in seeds
`1940`, `1` and `65`; the Axis held Bardia at the deadline in all three.
No linked Hard computer win is established. The Australian counters in those
traces were often scattered or low in cohesion by 3 January, and the engine
cannot yet distinguish the 7th RTR's working tanks from temporarily
unserviceable ones. These are continuity and model diagnostics, **not**
historical validation, balance results, or evidence that Bardia is impossible
for a human. The current engine also continues
ordinary Axis sea landing at Bardia; the extent of actual resupply under
Royal Navy bombardment needs evidence before changing port throughput.

### Assault diagnosis and first route correction (seed 1940)

Run `.venv/bin/python scripts/trace_bardia.py --seed 1940` to see each day's
orders, position, stores, cohesion, battles and odds across all three linked
chapters. This is a diagnostic, not a benchmark. In the **original map and
mission trace**, at the start of 3 January,
7th RTR is at `[66,14]`, with 5/5 abstract steps but cohesion 45; the
Australians are nearby but 16th Brigade has cohesion 51 and 17th Brigade 66.
The tank regiment is ordered to attack Bardia at `[67,13]`, yet the direct
edge is a cliff for vehicles. Its path passes through `[67,14]`, which fills
with other Commonwealth formations first. The movement log records `no room`
and then `no enemy in reach` for 7th RTR. The first battle is therefore an
infantry assault without that regiment: attack 1,658 against defence 5,727,
no retreat, and the attackers lose 60 cohesion. On 4 January 7th RTR does
join a second attack, but the Australian assault force is already broken;
that battle is 539 against 4,580. These figures are **game combat values**,
not historical headcounts or casualty estimates.

The [Australian War Memorial battle account](https://www.awm.gov.au/collection/E84311)
places the 16th Brigade's breach on the western face on 3 January, followed
by the 17th Brigade's action in the south. The [6th Division operation
order](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-B.html)
assigns 7th RTR to Phase I. The simulated town assault bypasses that
sequence. At this map scale, `[66,13]` is a fortified west-side hex, while
the current assembly markers point to `[66,14]` and `[67,14]`. Simply moving
the markers forward is not a sound fix: `[67,14]` is itself an Axis fortified
perimeter hex, so the variant puts troops inside it before the dated breach.
Comparison runs of that marker-only variant with seeds `1940`, `1` and `65`
also ended Axis tactical. It is an inference from the game trace and the
published sequence that a dated western breach, tank access, artillery and
engineer preparation, and the following southern phase must be represented
before balancing the town fight. Do not reduce the garrison or fort levels
solely to force a Commonwealth win.

The draft now marks a persistent western-perimeter breach at `[66,13]`. The
computer treats that as a required approach before attacking the town; human
players retain their choice of attack order. The shared map's western edge
from `[66,14]` to `[66,13]` is a **map-scale vehicle pass**, because the
[UK official history, chapter XV](https://www.ibiblio.org/hyperwar/UN/UK/UK-Med-I/UK-Med-I-15.html)
describes the selected western ground as suitable for tanks *after* the
engineers made crossings through the ditch and mines. The pass represents
terrain access, not a permanent gap in the Italian works. A second named
crossing preserves the coast-road approach south of town. These coordinates
remain approximate until the operation map plates are checked against the
shared 10 km grid.

In a fresh seed `1940` linked run, 7th RTR and 17th Brigade reach the marked
western hex on 3 January. On 4 January, the town assault includes 7th RTR,
other armour, and all three Australian brigades: game attack 2,307 against
defence 5,386. It still fails. The added mission step fixes the *sequence*
and the route error, but does not yet represent engineers' breaching work,
concentrated artillery preparation, Italian command collapse, or the actual
distribution of the garrison among the perimeter, town and southern posts.
Linked Hard/Hard seeds `1` and `65` also reached the breach objective but did
not capture the town. The three-day linked scenario is therefore still
research-only.

## Roster translation and unresolved figures

| Formation | Link to Compass trial | Bardia treatment |
| --- | --- | --- |
| Western Desert Force HQ, 7th Armoured Division, 7th RTR | Continuing Commonwealth identities | Carry played losses, fuel and position. Western Desert Force became XIII Corps on 1 January in the UK official history; decide how to show the renamed HQ without breaking identity in saved games. |
| 6th Australian Division, 16th/17th/19th Australian Brigades | New arrivals | Date their entry and assembly through the interval. Do not give 19th Brigade the Phase I assault role. |
| 16th British Infantry Brigade | Present in Compass trial | Present near Sollum, but not part of the Bardia assault. |
| Italian 62nd/63rd/64th Divisions | Continuing Axis identities | Carry played losses and withdrawal from the frontier; do not recreate destroyed counters merely to fit the historical order of battle. |
| Italian 1st/2nd Blackshirt and fortress troops | Need additional or reclassified counters | Verify which existing Compass counters represent their remnants, then add only genuinely new identities. |

The official counts above are aggregate or serviceability figures. Brigade
manpower, local sector garrisons, stock tonnages, tank repair rates and exact
counter positions are **unverified**. The current `engine/recovery.py` has no
separate pool for temporarily unserviceable vehicles, so a Bardia trial that
sets 7th RTR to 23 tanks would conflate working tanks with losses unless this
is addressed or clearly labelled as a standalone snapshot. The same problem
already affects the Compass opening trial.

## Source-map check, 17 November 2026

The Australian War Memorial's [Berryman wallet 30](https://www.awm.gov.au/collection/C2741629)
contains two contemporary overview drawings (PDF pages 3–4) of the first
and last assault phases. The first shows the 16th Australian Brigade
entering the western face and fanning north, toward Bardia town, and south;
the 17th Brigade crosses farther south while the 2/6th Battalion makes its
separate diversion near the southern posts. The last-phase drawing keeps
the town, western breach and southern pocket distinct. The War Memorial's
[17th Brigade map wallet](https://s3-ap-southeast-2.amazonaws.com/awm-media/collection/RCDIG1021202/bundled/RCDIG1021202.pdf)
(pages 3–4) shows positions on a Bardia 1:50,000 grid, including dispositions
marked for 1–2 January and zero hour on 3 January. The
[division operation order](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-B.html)
assigns the first breach to 16th Brigade, engineers and 7th RTR, with a later
17th Brigade phase. Together these support the *sequence and relative sectors*
in the mission; the overview drawings do not locate a game hex or reproduce
the engineer traces, and the detailed map has not yet been registered against
our generated 10 km grid. Keep `[66,13]` and `[67,14]` explicitly approximate.

The reproducible seed `1940` Hard/Hard trace exposes a sharper model problem.
On 3 January Commonwealth units **move** into `[66,13]`, the western
fortification proxy, without a battle there. That hex has no Axis garrison in
the played state; `engine/board.py` removes an enemy fort when the first unit
enters it, and `engine/movement.py` charges only extra movement points. No
engineer task, mine or ditch crossing is checked. On 4 January the town fight
at `[67,13]` instead puts all three visible defenders into one battle and
totals 2,307 attack against 5,386 defence; on 5 January the assault has
collapsed. This is a **game trace**, not evidence for historical numbers.
The map and order explain why the current automatic capture cannot stand for
the recorded first-phase breach. Avoid weakening the town garrison or
awarding a dated breach to force a win: a counterfactual attack may arrive
late, lack engineers or supplies, or face a different defending position.

## Perimeter crossing trial, 17 November 2026

The Compass opening now marks three intact fortification proxies: Bardia's
western and southern approaches at `[66,13]` and `[67,14]`, and Tobruk's
southeastern approach at `[56,11]`. An empty enemy perimeter blocks ordinary
movement. A player may order a foot or motorised formation to **Attack** the
hex if it has at least 50 tonnes of stores per formation size; the entry
spends those stores, opens the perimeter and removes the fort. An occupied
perimeter still requires a battle, followed by the advance of a surviving
infantry formation that paid its normal combat stores. The player controls
the order and timing. A failed approach or missing stores leaves the work
intact, and a later linked chapter carries that actual state forward.

The 50-tonne threshold and the 10 km crossing hexes are **game estimates**.
There is no separate engineer counter, mine clearance time, artillery
programme or serviceability pool yet. The action therefore represents a
prepared crossing at operational scale, not a claim that infantry alone
cleared the historical works. The interval computer now stages at `[66,14]`
and `[67,15]`, outside the mapped Bardia works, and is instructed to avoid
attacking the town and either perimeter before 3 January. Human orders remain
unrestricted.

In the revised seed `1940` Hard/Hard trace, a Commonwealth formation opens
the western proxy on 3 January while Bardia town stays Axis-held. The town
fight is still lost by 5 January, and 7th RTR does not reliably support it.
This verifies the crossing sequence and persistence in one reproducible
computer run; it does not validate the assault balance. The Berryman and
17th Brigade plates still need registration against the generated grid, and
the garrison distribution, engineer support and tank serviceability remain
open research gates.

The next modelling decision is how a player prepares and opens a defended
perimeter *using orders available in the game*. It needs an explicit crossing
condition and visible progress, then a way for the remaining garrison to
hold the southern sector after the town falls. Choose any movement and combat
costs from play and evidence rather than treating the 1:50,000 posts as
individual 10 km hexes. Apply the same contract to Tobruk only after its
perimeter map has been checked. A complete linked trial must then show the
first-phase crossing, second-phase town and southern-sector outcomes as
separate events, preserving the actual played losses and position.

## Build and validation sequence

1. Register the located 1:50,000 Bardia map and the first/last-phase drawings
   against the shared campaign map; locate the western breach, southern posts,
   approach roads and 6th Australian assembly areas. Record uncertainty where
   10 km hexes cannot resolve them. The source maps are now identified, but the
   exact game-hex correspondence remains unverified.
2. Audit the linked interval's actual positions, Australian transport and
   serviceability, Axis frontier withdrawal, Sollum throughput, water and
   Bardia port access against dated records. The first legal trace above is
   only a structural check; repeat with human play and multiple seeds.
3. Compare the linked assault's daily events with the operation order and
   4–5 January record. Diagnose why the computer cannot assemble a fit assault
   force. Improve the perimeter, engineer breach, artillery preparation and
   tank serviceability models before tuning strengths to force an outcome.
4. Build a separate **standalone historical reference start** only after its
   3 January deployment, garrison sectors and stocks can be checked. Then run
   human and seeded trials before listing Bardia in the normal battle menu.
