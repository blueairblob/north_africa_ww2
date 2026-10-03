# Benghazi Handicap — Rules specification

This is the one rules document the engine follows and its tests cite, rule by
rule (`DESIGN.md` §13). It is written from `DESIGN.md` and from history
(`docs/SOURCES.md`), and from no other game (`docs/CLEAN_ROOM.md`).

**Status: draft 2.** The engine in `engine/` follows it and the tests in
`tests/test_engine_*.py` cite it. No number in it has been play-tested. Every constant is
marked *from source* (a historical or design fact), *derived* (worked out here
from a stated fact, and open to tuning) or *to be tuned* (a first guess).
Historical figures marked **unverified**, **unsure** or **not known** have
not been confirmed and must be checked before they are relied on. Those
without such a mark were checked on the web against the sources listed in
`docs/SOURCES.md`, mostly at second hand, not against the books themselves.
Section 18 lists the decisions the owner has taken.

The player does not need this document. What the player must learn is section 17.

---

## 1. Conventions

**1.1 Integers.** Every quantity is an integer. `floor(a / b)` is integer
division of non-negative integers, rounding down. `ceil(a / b)` is
`floor((a + b − 1) / b)`. Where a formula has several factors, they are all
multiplied first and divided once, at the end, with the rounding the rule
states. `clamp(x, lo, hi)` is `lo` if `x < lo`, `hi` if `x > hi`, otherwise `x`.

**1.2 Percentages** are integers 0–100 (or more, where a rule says so) and are
applied as `floor(x × p / 100)`.

**1.3 Hexes.** A hex is `(col, row)`, `0 ≤ col ≤ 122`, `0 ≤ row ≤ 43`. Hexes
are flat-topped; odd columns sit half a hex lower. Directions are numbered
0 N, 1 NE, 2 SE, 3 S, 4 SW, 5 NW. The neighbour of `(c, r)`:

| Direction | `c` even | `c` odd |
| --- | --- | --- |
| 0 N | `(c, r−1)` | `(c, r−1)` |
| 1 NE | `(c+1, r−1)` | `(c+1, r)` |
| 2 SE | `(c+1, r)` | `(c+1, r+1)` |
| 3 S | `(c, r+1)` | `(c, r+1)` |
| 4 SW | `(c−1, r)` | `(c−1, r+1)` |
| 5 NW | `(c−1, r−1)` | `(c−1, r)` |

A neighbour outside the map does not exist. Two hexes are *adjacent* if one is
a neighbour of the other.

**1.4 Distance** between two hexes is the number of steps between them on an
empty hex grid (the standard hex distance), ignoring terrain.

**1.5 Hexsides.** A hexside is named `(col, row, direction)` with direction 1,
2 or 3, as in `data/map.json`. The side of a hex in direction 0, 4 or 5 is the
neighbour's side in direction 3, 1 or 2.

**1.6 Sides.** There are two sides: `axis` and `cw` (Commonwealth). The
*enemy* of one is the other. The **priority side** is `axis` on odd-numbered
turns and `cw` on even-numbered turns; it is used only to break ties between
the sides (9.5.3).

**1.7 Units** have an integer id, unique in the scenario and never reused.

**1.8 Standard orders.** Wherever a rule processes or chooses among several
things and names no other order, it uses:

- units: ascending id;
- hexes: ascending column, then ascending row;
- directions: 0 to 5;
- sides: the priority side first.

No rule depends on the order in which a program happens to store things.

**1.9 Turns and dates.** A scenario has a start date. Turn 1 covers the start
date and the day after; turn `t` covers days `2(t−1)` and `2(t−1)+1` after the
start date. A scenario event dated `D` belongs to turn
`floor((D − start) / 2) + 1`, with `D − start` in days. An event dated before
the start belongs to turn 1.

**1.10 Tonnes.** Supply is counted in whole tonnes.

---

## 2. Game state

**2.1** The game state is one structure that serialises to JSON. It holds, and
the rules read and change, nothing else:

- the scenario id and the turn number;
- for each unit: id, side, name, type, size, experience, steps, maximum
  steps, hex, cohesion, fuel, stores, the flags `out_of_stores`, `traced` and
  `stationary`, and the unit's status (`on_map`, `not_arrived`, `withdrawn`,
  `destroyed`);
- for each place: its owner;
- for each port: its condition (0–100) and its stock (fuel, stores);
- for each HQ: its dump stock (fuel, stores);
- the Tripoli pipeline (6.3.5) and the Tripoli stock;
- for each hex with a fortification: its level and the side that owns it;
- for each side: victory points, the last air choice, and the running totals
  the invariants need (tonnes landed, issued, burnt, lost);
- the event log of the turn just played.

**2.2** The map (`data/map.json`) and the scenario file are fixed data, not
state. Schedules in the scenario (reinforcements, lift, air points, sea
percentage, fuel percentage, railhead) are looked up by turn number.

**2.3** A game is its scenario plus, for each turn, each side's submitted
orders. Replaying them gives the identical state (section 15, invariant I-1).

---

## 3. The map

### 3.1 Terrain

**3.1.1** Each hex has one terrain: sea `~`, desert `.`, rough `^`,
depression `v`, sand sea `s`, oasis `o`.

**3.1.2** Sea, depression and sand sea are **impassable**: no unit may ever be
in such a hex, and no supply passes through one. (See 18.2 for sand sea.)

**3.1.3** Desert, rough and oasis are **passable**. Oasis behaves as desert in
every rule.

### 3.2 Hexsides

**3.2.1 Escarpment.** A hexside listed in `escarpments` is an escarpment. Its
high side is the hex the data names.

**3.2.2 Pass.** An escarpment hexside listed in `passes` is a pass.

**3.2.3** An escarpment hexside that is not a pass is a **cliff**. Vehicles
(4.1.2) cannot cross a cliff. Foot units can, at a cost (9.3). No zone of
control (9.6), attack (10.2.3) or supply path (6.4) crosses a cliff.

### 3.3 Routes

**3.3.1** Each route in `routes` has a kind (road, track, rail) and an ordered
list of hexes. Each pair of consecutive hexes in a road or track route is a
**link** of that kind. If a pair is linked by both a road and a track, it is a
road link.

**3.3.2** Rail routes make no links. The railway matters only through the
railhead (6.2.4).

### 3.4 Places

**3.4.1** Each place in `places` has a kind: port, town, oasis or site. A hex
holding a place of kind port or town is a **town hex** for combat (10.4.5).

**3.4.2 Ownership.** Each place has an owner (a side), set by the scenario at
the start. Whenever, at the end of the Movement phase or the end of the Combat
phase, units of one side are in the place's hex, that side becomes the owner.
Otherwise the owner does not change.

**3.4.3** When a port's owner changes, its stock is destroyed (counted as
*lost* by the old owner) and its condition becomes `PORT_CAPTURE_PCT`.

### 3.5 Off-map bases

**3.5.1 Tripoli** is off the map. It is joined to the map at the **west entry
hex**, the first hex of the coast road, `(3, 30)` (El Agheila). It supplies
only the Axis (6.2.2).

**3.5.2** The Commonwealth base is **Alexandria**, the port at `(121, 20)`, on
the map. The **east entry hex** is Alexandria's hex.

**3.5.3** A side's **base hex** is its entry hex: `(3, 30)` for the Axis,
`(121, 20)` for the Commonwealth.

### 3.6 Constants

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `HEX_KM` | 10 | width of a hex | from source (`DESIGN.md` §2) |
| `TURN_DAYS` | 2 | days in a turn | from source (`DESIGN.md` §2) |
| `PORT_CAPTURE_PCT` | 25 | condition of a port just captured | to be tuned |

---

## 4. Units

### 4.1 Types

**4.1.1** A unit has one type: `armour`, `motorised`, `foot`, `guns`
(anti-tank and artillery groups), `recon` or `hq`.

**4.1.2** `foot` units are **foot**. All others are **vehicles**.

**4.1.3** `hq` units are **HQs**. All others are **combat units**.

**4.1.4** `armour` and `recon` are **hard** targets. All others are **soft**.

### 4.2 What a unit carries

**4.2.1 Steps.** Strength in steps, from 1 to the unit's maximum. An armour
step is about ten running tanks; an infantry step is a battalion; a guns step
is a battery group; a recon step is a squadron; an HQ has one step. A unit at
0 steps is destroyed and leaves the map.

**4.2.2 Size.** 1 to 4, fixed, in brigade-equivalents: a brigade, regiment or
HQ is 1, a division usually 3. Size sets what the unit consumes and carries.

**4.2.3 Cohesion.** 0 to 100. Any rule that changes cohesion clamps the
result to that range.

**4.2.4 Experience.** `green`, `regular` or `veteran`, fixed for the scenario.

**4.2.5 Fuel and stores.** Tonnes held, from 0 to the unit's capacity:

- fuel capacity = `size × FUEL_HEX[type] × FUEL_RANGE`;
- stores capacity = `size × STORES_CAP`.

Foot units have fuel capacity 0 and never need fuel.

### 4.3 Stacking

**4.3.1** A hex may hold at most `STACK_COMBAT` combat units and `STACK_HQ`
HQs, all of one side.

**4.3.2** No hex ever holds units of both sides.

**4.3.3** The scenario's starting position and every rule that puts a unit in
a hex obey 4.3.1 and 4.3.2; where a rule would break them, that rule says
what happens instead.

### 4.4 Constants

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `STACK_COMBAT` | 2 | combat units in a hex | owner's decision (18.1) |
| `STACK_HQ` | 1 | HQs in a hex | to be tuned |
| `FUEL_HEX` | armour 4, motorised 3, guns 2, recon 2, hq 2, foot 0 | tonnes of fuel per size to enter one hex | derived: a division's fuel for 100 km taken as roughly 100 tonnes (**unverified**) |
| `FUEL_RANGE` | 30 | hexes of fuel a full unit carries | to be tuned |
| `STORES_CAP` | 300 | tonnes of stores per size a full unit carries | to be tuned |

---

## 5. The turn

**5.1** A turn is eight phases in this order. Each phase may change only the
state listed for it; anything else is a defect in the engine.

| # | Phase | May change |
| --- | --- | --- |
| 1 | Supply (§6) | port condition and stock, Tripoli pipeline and stock, HQ dumps, unit fuel and stores, the flags `out_of_stores` and `traced`, cohesion; by starvation only: steps, unit status and hex, victory points |
| 2 | Orders (§8) | the orders and air choice for this turn; nothing else |
| 3 | Air (§7) | each side's air effect for this turn |
| 4 | Movement (§9) | unit hexes, fuel, cohesion, the `stationary` flag, HQ dumps (9.9), place owners, port condition and stock (on capture), fortification (on capture) |
| 5 | Combat (§10) | steps, cohesion, stores, unit hexes (retreat, advance), unit status, what a destroyed unit held, HQ dumps, the `stationary` flag, victory points, place owners, port condition and stock, fortification |
| 6 | Recovery (§11) | steps (recovered tanks), cohesion, stores (digging), fortification |
| 7 | Reinforcement and withdrawal (§12) | unit status, hexes of arriving units, steps (replacements), what a withdrawn unit held, the `stationary` flag, an enemy fortification where a unit arrives |
| 8 | Victory (§13) | victory points, the turn number, whether the game has ended |

Any phase may also add to the event log and to the sides' running supply
totals.

**5.2** Players are shown their view (§14) once, at the start of the Orders
phase, and give orders once. They do nothing in any other phase.

**5.3** Within a phase, both sides are handled by the same rules at the same
time. Where a rule must take things one after another, it states the order.

**5.4** This order differs from `DESIGN.md` §5 in one place: Orders comes
before Air, because the air choice is given with the orders (18.6).

---

## 6. Supply

Supply is fuel and stores, in tonnes. It is landed at **sources**, carried by
truck to **HQs**, and drawn by **units** from HQs and sources within reach.
Two things limit the trucks: their total **lift**, and the **fuel they burn**.
Both grow with distance. The Supply phase does all of this once a turn, in the
steps of 6.3 to 6.10, in that order. The two sides do not interact in this
phase except through the positions of their units, which do not change in it.

### 6.1 Fuel and stores

**6.1.1** Fuel is spent by vehicles entering hexes (9.7) and by trucks hauling
(6.5). Stores are spent by existing (6.9), fighting (10.3) and digging (11.3).

**6.1.2** Every stock (port, Tripoli, HQ dump, unit) holds fuel and stores as
two separate numbers. Neither is ever converted into the other.

### 6.2 Sources and outlets

**6.2.1 Ports.** Every port a side owns is a source for that side, with its
own stock.

**6.2.2 Tripoli.** Tripoli is an Axis source, with its own stock, which no
rule can take from the Axis. It issues supply only at the west entry hex
(3.5.1), and every haul from it costs `TRIPOLI_HAUL` on top of the path from
that hex.

**6.2.3 Alexandria** is a port like any other (6.2.1), with a capacity large
enough that the base is not what limits the Commonwealth.

**6.2.4 Railhead.** The scenario gives, by turn, a railhead: an index into the
hex list of the rail route, counted from Alexandria. The **effective
railhead** is the furthest rail hex, at or before that index, such that no
rail hex from Alexandria up to and including it is blocked (6.4.2) for the
Commonwealth. While the Commonwealth owns Alexandria and the effective
railhead is not Alexandria's hex, the effective railhead is a second place
where Alexandria's stock is issued. No more than `RAIL_CAP` tonnes (fuel and
stores together) leave by the railhead in one Supply phase. The railway
carries supply to the railhead at no cost in lift or fuel. Only the
Commonwealth uses the railway (18.8).

**6.2.5 Outlets.** An **outlet** is a hex where a source's stock is issued:
the west entry hex (Tripoli), each owned port's hex, and the effective
railhead (Alexandria's stock). Outlets are ordered: Tripoli, then the
railhead, then ports by hex in standard order.

### 6.3 Landing

**6.3.1 Repair.** Each port's condition rises by `PORT_REPAIR`, to at most 100.

**6.3.2 Port landing.** Each port lands
`floor(capacity × condition × sea_pct / 10000)` tonnes for its owner, where
`capacity` is from the table in 6.12 and `sea_pct` is the owner's scenario
value for this turn (0–100; it stands for Malta and the convoy war on the
Axis side, and is 100 for the Commonwealth unless a scenario says otherwise).

**6.3.3 Tripoli landing.** Tripoli lands
`floor(TRIPOLI_CAP × sea_pct / 100)` tonnes for the Axis.

**6.3.4 Fuel share.** Of any landing of `L` tonnes,
`floor(L × fuel_pct / 100)` is fuel and the rest is stores; `fuel_pct` is the
side's scenario value for this turn.

**6.3.5 Tripoli delay.** A port's landing joins its stock at once. Tripoli's
landing joins the Tripoli pipeline and joins Tripoli's stock in the Supply
phase `TRIPOLI_DELAY` turns later, before 6.4.

**6.3.6** Each side's *landed* total rises by what it landed (for Tripoli,
when it lands, not when it leaves the pipeline).

### 6.4 The network

**6.4.1 Haul cost.** The haul cost of stepping from one passable hex to an
adjacent passable hex is:

| Step | Cost |
| --- | --- |
| along a road link | 2 |
| along a track link | 3 |
| otherwise, into desert or oasis | 4 |
| otherwise, into rough | 8 |
| crossing a pass, in addition | +2 |
| crossing a cliff | not allowed |

**6.4.2 Blocked hexes.** A hex is blocked for a side if an enemy unit is in
it, or if it is in an enemy zone of control (9.6) and no unit of that side is
in it.

**6.4.3 Supply path.** A supply path for a side is a chain of adjacent
passable hexes, none of them blocked for that side. Its cost is the sum of
its steps' haul costs. The **haul distance** between two hexes is the least
cost of any supply path between them; if there is none, the hexes are not
connected. The haul distance from a hex to itself is 0.

**6.4.4** Supply paths are found in the Supply phase, from where the units are
then. Nothing that happens later in the turn changes what was delivered
(6.11).

### 6.5 The truck haul

**6.5.1 Lift.** Each side has, each turn, a lift of
`floor(lift × (100 − interdiction) / 100)` tonne-units, where `lift` is its
scenario value for this turn and `interdiction` is set by the enemy's air
choice of the previous turn (7.4). Lift not used is not carried over.

**6.5.2 A haul** carries `f` tonnes of fuel and `s` tonnes of stores from an
outlet to an HQ at haul distance `H` (for Tripoli, `H` is `TRIPOLI_HAUL` plus
the haul distance from the west entry hex). It:

- uses `(f + s) × H` of the side's lift;
- burns `ceil((f + s) × H / HAUL_BURN_DIV)` tonnes of fuel, taken from the
  source's fuel stock and counted as *burnt*;
- takes `f` and `s` from the source's stock and adds them to the HQ's dump.

**6.5.3 A haul is allowed** only if the lift left is at least `(f + s) × H`,
the source's stores are at least `s`, the source's fuel is at least `f` plus
the fuel burnt, and (for the railhead) the tonnes left under `RAIL_CAP` are
at least `f + s`.

**6.5.4 Size of a haul.** Given a wanted amount of stores `ws` and of fuel
`wf`: `s` is the largest whole number not above `ws` for which a haul of
`(0, s)` is allowed; then `f` is the largest whole number not above `wf` for
which a haul of `(f, s)` is allowed. Stores are settled first (18.9).

**6.5.5** When `H` is 0 (the HQ is in the outlet's hex) a haul uses no lift
and burns nothing.

### 6.6 HQs and reach

**6.6.1 Depots.** A side's depots are its HQs (issuing from their dumps) and
its outlets (issuing from their sources' stocks).

**6.6.2 Reach.** A unit is **in reach** of a depot if the haul distance from
the depot's hex to the unit's hex is at most `REACH`. Tripoli's outlet counts
its extra `TRIPOLI_HAUL`, so no unit is in reach of it: Tripoli feeds HQs
only.

**6.6.3** A unit's depots in reach are ordered by haul distance, then HQs
before outlets, then HQ id, then outlet order (6.2.5). The first is its
**first depot**. An HQ is in reach of itself at distance 0 and may be its own
first depot.

**6.6.4 Traced.** A unit's `traced` flag is set if it has at least one depot
in reach, whatever that depot holds, and cleared otherwise.

**6.6.5 Fill.** How full a depot can make a unit falls with the haul distance
`d` between them. Up to `REACH_FULL` the fill is 100 per cent. Beyond it the
fill is
`100 − floor((100 − REACH_FILL_PCT) × (d − REACH_FULL) / (REACH − REACH_FULL))`
per cent, which is `REACH_FILL_PCT` at `REACH`.

**6.6.6 Demand.** A unit's demand for fuel from a depot is
`floor(fuel capacity × fill / 100)` less its fuel held, or 0 if that is
negative; likewise stores. A unit far from its depot is therefore kept only
part full.

### 6.7 Hauls to HQs, and dumps

**6.7.1 Service order.** HQs are served in order of their least haul distance
to any outlet (counting `TRIPOLI_HAUL`), nearest first, then by id. An HQ
connected to no outlet is not served.

**6.7.2 Needs pass.** For each HQ in service order: its need for stores is
the sum of the stores demands on it (6.6.6) of all units whose first depot it is, less the
stores in its dump, or 0 if that is negative; likewise fuel. The HQ takes
hauls (6.5.4) from its connected outlets in order of haul distance, nearest
first, then outlet order, each haul wanting what is still needed, until its
need is met or the outlets are exhausted.

**6.7.3 Dump pass.** After the needs pass, for each HQ in the same order
whose `stationary` flag is set: it wants stores up to `DUMP_CAP` in its dump
beyond its need in 6.7.2, and fuel likewise, and takes hauls in the same way.

**6.7.4** No haul raises a dump above its need plus `DUMP_CAP`, for fuel or
for stores. A dump already above that (because its units' demands fell)
keeps what it holds.

### 6.8 Issue to units

**6.8.1** Units draw in order of
`floor(100 × stores held / stores capacity)`, lowest first, then by id.

**6.8.2** A unit, in its turn, goes through its depots in reach in the order
of 6.6.3. From each it takes stores and then fuel: as much as its demand on
that depot (6.6.6, worked out from what it then holds), the depot's stock
and, for the railhead, `RAIL_CAP` allow.

**6.8.3** Issue uses no lift and burns no fuel: the last leg is the unit's
own transport. What is drawn is added to the side's *issued* total.

### 6.9 Consumption

**6.9.1 Upkeep.** After issue, every unit on the map pays
`size × UPKEEP` tonnes of stores. If it holds less, it pays what it holds and
its `out_of_stores` flag is set; otherwise the flag is cleared.

**6.9.2** Fuel is spent only by movement (9.7) and hauls (6.5). Stores are
also spent by combat (10.3) and digging (11.3).

### 6.10 What shortage does

**6.10.1 Out of fuel.** A vehicle holding less fuel than a step costs cannot
take that step (9.5.1). It may still be given any order, defend, and attack
an adjacent hex.

**6.10.2 Out of stores.** A unit whose `out_of_stores` flag is set:

- if its cohesion is 0, loses one step (and is destroyed at 0 steps);
- otherwise loses `STARVE_COHESION` cohesion;
- fights at half value until the flag is cleared (10.4.2);
- recovers no cohesion (11.2).

This is applied at the end of the Supply phase, after 6.9.1.

**6.10.3 Not traced.** A unit that is not traced draws nothing. It suffers
nothing further until its own stores and fuel run out.

### 6.11 A route cut during the turn

**6.11.1** Supply is traced and moved only in the Supply phase. A route cut
later in the turn, by movement or combat, changes nothing in that turn: units
keep what they hold and dumps keep what they hold. The cut takes effect at
the next Supply phase.

**6.11.2** A route reopened later in the turn likewise delivers nothing until
the next Supply phase.

**6.11.3** Supply does not exist on the map between a source and an HQ: it is
either in the stock it left or in the dump it reached. There is nothing in
transit to capture or destroy. (The Tripoli pipeline is off the map.)

**6.11.4** When an HQ enters a hex (by movement, retreat or advance), any
fuel in its dump above `HQ_CARRY`, and any stores above `HQ_CARRY`, are left
behind and destroyed (counted as *lost*). When an HQ is destroyed or
withdrawn, its whole dump is lost. Supply is never captured (18.10).

### 6.12 Constants

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `TRIPOLI_CAP` | 3000 | tonnes landed at Tripoli per turn | from source: about 45,000 tons a month, 1,500 a day (van Creveld, *Supplying War*, ch. 6). Italian returns for May–August 1941 show 981 to 1,734 tons a day actually unloaded, so the figure is of the right size |
| port capacity: Benghazi | 1500 | tonnes per turn | from source: 597 to 918 tons a day actually unloaded, May–August 1941 (Italian returns), and 700–800 in practice by van Creveld. His theoretical 2,700 a day is disputed and not used; the staffs of the time assumed 1,000 as realistic |
| port capacity: Tobruk | 1200 | tonnes per turn | from source: 1,500 tons a day in theory, rarely above 600 in practice (van Creveld) |
| port capacity: Derna | 300 | tonnes per turn | **not known**; a small harbour; to be found in the official histories |
| port capacity: Bardia | 300 | tonnes per turn | **not known**; as Derna |
| port capacity: Mersa Matruh | 600 | tonnes per turn | **not known**; to be found in Playfair |
| port capacity: Alexandria | 20000 | tonnes per turn | to be tuned: set high so the base does not limit the Commonwealth |
| `RAIL_CAP` | 8000 | tonnes per turn issued at the railhead | **unsure**: one figure found, 4,200 long tons a day, and it is not clear whether that is all freight or water only; to be checked in Playfair |
| `TRIPOLI_HAUL` | 140 | haul cost from Tripoli to the west entry hex | derived: Tripoli to Benghazi is about 970 km by road; the map has 28 road hexes from El Agheila to Benghazi, leaving about 690 km, at 2 per 10 km |
| `TRIPOLI_DELAY` | 2 | turns from landing at Tripoli to being available | derived: 690 km at 200–250 km a day by lorry; to be tuned |
| `PORT_REPAIR` | 5 | condition regained per turn | to be tuned |
| `HAUL_BURN_DIV` | 2000 | tonne-units hauled per tonne of fuel burnt | derived, to be tuned: road transport used 30 to 50 per cent of fuel deliveries in July–October 1941, with the front at Tobruk and the frontier (van Creveld, pp. 182–187). From Tripoli to Tobruk the haul cost is 290, which at this value burns 14.5% of the tonnage, or 36% of the fuel when fuel is 40% of the cargo |
| `REACH` | 20 | haul distance within which a unit draws from a depot (10 road hexes, 5 desert hexes) | to be tuned |
| `REACH_FULL` | 8 | haul distance within which a depot fills a unit completely (4 road hexes, 2 desert hexes) | to be tuned |
| `REACH_FILL_PCT` | 50 | how full a depot can make a unit at `REACH` | to be tuned |
| `DUMP_CAP` | 3000 | tonnes of each kind an HQ dump may hold beyond current need | to be tuned |
| `HQ_CARRY` | 300 | tonnes of each kind a moving HQ keeps | to be tuned |
| `UPKEEP` | 50 | tonnes of stores per size per turn | derived, to be tuned: with combat and movement, a division at full effort uses about 300 tonnes a day, against 350 tons a day for a German motorised division (van Creveld) |
| `STARVE_COHESION` | 10 | cohesion lost per turn out of stores | to be tuned |

The scenario gives, per side and by turn: `lift`, `sea_pct`, `fuel_pct`
(first value 40, to be tuned), and for the Commonwealth the railhead index.
As a guide to `lift`: the German army staff reckoned that keeping one
motorised division supplied 300 miles (480 km) from its port took 1,170
two-ton lorries, each making four or five round trips a month (van Creveld).
That is 350 tons a day over a haul cost of 96, or 67,200 tonne-units a turn
for the division, and about 57 a turn for each lorry (derived).

The railhead schedule is scenario data. The dates found so far: Misheifa,
November 1941; Capuzzo, February 1942; Belhamed, June 1942; lost in the
retreat to Alamein that month; reopened to El Daba on 9 November 1942, Mersa
Matruh on the 13th, Capuzzo on the 20th and Tobruk on 1 December (New Zealand
official history, the engineers' volume, ch. 9). The map's railway runs from
Alexandria through Mersa Matruh, Misheifa and Fort Capuzzo to Belhamed; a
scenario names the place the line is open to.

A warning for scenario work: along the coast road the map counts more hexes
than the real road has tens of kilometres. Benghazi to El Alamein is 108
road hexes on the map and about 810 km by the one road figure found (Tripoli
to El Alamein 1,780 km, Tripoli to Benghazi 970 km). If that holds, hauls on
the map cost up to a third more than they should, and `lift` must allow for
it. **Unsure**: it rests on two figures from one secondary source.

---

## 7. Air

**7.1** Each side gives one air choice with its orders: `support`,
`interdict` or `recon`. A missing or unknown choice is `support`, and the
reply says so (8.5.4).

**7.2** The scenario gives each side, by turn, its **air points**, 0 to 3.

**7.3 Support.** In this turn's Combat phase, the side's attack totals and
defence totals are raised by `AIR_SUPPORT_PCT × points` per cent (10.4).

**7.4 Interdict.** In the next turn's Supply phase, the enemy's lift is
reduced by `AIR_INTERDICT_PCT × points` per cent (6.5.1).

**7.5 Recon.** In the view given at the next turn's Orders phase, every unit
of the side spots `AIR_RECON_HEXES × points` hexes further (14.3).

**7.6** With 0 air points every choice has no effect.

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `AIR_SUPPORT_PCT` | 5 | per cent on combat totals per air point | to be tuned |
| `AIR_INTERDICT_PCT` | 5 | per cent off enemy lift per air point | to be tuned |
| `AIR_RECON_HEXES` | 1 | extra spotting range per air point | to be tuned |

---

## 8. Orders

### 8.1 The six orders

**8.1.1** Each unit on the map has exactly one order each turn: `move`,
`attack`, `hold`, `dig_in`, `road_march` or `rest`.

**8.1.2** An order is a record: the unit id, the order name, and, for `move`,
`attack` and `road_march`, a destination hex `to` and optionally a list `via`
of up to `VIA_MAX` hexes to pass through in the order given.

**8.1.3** A unit given no order, or whose order is rejected, has the order
`hold`.

**8.1.4** Orders for a whole corps are a convenience of the screen. The engine
receives one order per unit.

### 8.2 Submission

**8.2.1** A side submits one list of orders and one air choice per turn. The
engine checks each order by 8.3 and 8.4 and replies to each: accepted, or
rejected with one code from 8.5. It never alters an order.

**8.2.2** A player may ask for the same check without submitting, any number
of times. The check changes no state.

**8.2.3** Orders are checked against the state at the start of the Orders
phase, and against nothing the side cannot see: an order is never rejected
because of an enemy unit.

**8.2.4** The enemy never sees orders or replies.

### 8.3 Checks on every order

In this sequence; the first failure gives the reply.

1. The order is a record with a whole-number unit id and one of the six
   order names. Else `E_ORDER`.
2. The unit id is a unit of the scenario. Else `E_UNIT`.
3. The unit belongs to the side submitting. Else `E_NOT_YOURS`.
4. The unit's status is `on_map`. Else `E_NOT_ON_MAP`.
5. No earlier order in the same list names the unit. Else `E_DUPLICATE` (the
   earlier order stands).

### 8.4 Checks by order

**8.4.1 Hold, Dig in, Rest.** Must have no `to` and no `via`; else `E_DEST`.
`dig_in` by an HQ is `E_HQ`. Otherwise legal, whatever the unit's supply,
cohesion or neighbours.

**8.4.2 Move.** In sequence:

1. `to` is given; else `E_NO_DEST`.
2. `to` and every `via` hex are hexes on the map (a pair of whole numbers
   within it); else `E_OFF_MAP`.
3. `via` has at most `VIA_MAX` hexes; else `E_VIA`.
4. `to` is not the unit's hex; else `E_SAME_HEX`.
5. `to` and every `via` hex are passable; else `E_IMPASSABLE`.
6. A path exists (9.2); else `E_NO_PATH`.

A move is legal whatever fuel the unit holds (9.7.2) and however far `to` is:
the unit goes as far as the turn allows.

**8.4.3 Attack.** The checks of 8.4.2, and before them:

- the unit is not an HQ; else `E_HQ`;
- the unit's cohesion is at least `ATTACK_MIN`; else `E_COHESION`.

**8.4.4 Road march.** The checks of 8.4.2, with two more:

- before them: the unit is a vehicle; else `E_FOOT`;
- between checks 5 and 6: the unit's hex, `to` and every `via` hex are each
  on a road or track link; else `E_NOT_ON_ROUTE`.

The path of check 6 is the road-march path (9.2.3).

### 8.5 Replies

**8.5.1** A reply is the unit id, `ok` true or false, and when false a code
and a fixed English sentence.

| Code | Sentence |
| --- | --- |
| `E_ORDER` | That is not one of the six orders. |
| `E_UNIT` | There is no such unit. |
| `E_NOT_YOURS` | That unit is not yours. |
| `E_NOT_ON_MAP` | That unit is not on the map. |
| `E_DUPLICATE` | That unit already has an order this turn. |
| `E_DEST` | That order takes no destination. |
| `E_NO_DEST` | That order needs a destination. |
| `E_OFF_MAP` | The destination is off the map. |
| `E_VIA` | Too many points on the way. |
| `E_SAME_HEX` | The unit is already there. |
| `E_IMPASSABLE` | The unit cannot enter that ground. |
| `E_NO_PATH` | There is no way there for this unit. |
| `E_HQ` | A headquarters cannot do that. |
| `E_COHESION` | The unit is too disorganised to attack. |
| `E_FOOT` | Foot infantry cannot road march. |
| `E_NOT_ON_ROUTE` | A road march must start, pass and end on a road or track. |
| `E_AIR` | That is not an air mission; support is flown. |

**8.5.2** A rejected order changes nothing; the unit holds (8.1.3).

**8.5.3** An accepted order that later cannot be carried out in full (no
fuel, an enemy in the way, a full hex) is not an error. What happens is in
sections 9 and 10, and is reported in the event log.

**8.5.4** An air choice that is missing or unknown is replied to with
`E_AIR`, and `support` is flown (7.1).

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `VIA_MAX` | 4 | points on the way in one order | to be tuned |
| `ATTACK_MIN` | 40 | least cohesion to be given, or to carry out, an attack | to be tuned |

---

## 9. Movement

### 9.1 Allowance

**9.1.1** Each unit has a movement allowance in movement points (MP) per
turn, by type (9.10). Cohesion and supply do not change it.

**9.1.2** Units ordered `hold`, `dig_in` or `rest` do not move in the Movement
phase.

### 9.2 The path

**9.2.1** The path of a `move` or `attack` order is found once, at the start
of the Movement phase, and never changed. It runs from the unit's hex through
each `via` hex in turn to `to`. Each leg is the least-cost chain of adjacent
hexes by the unit's step costs (9.3), ignoring every unit and every
fortification. A leg whose two ends are the same hex is empty.

**9.2.2 Ties.** Among legs of equal cost: the one with fewer hexes; then the
one whose list of hexes comes first when compared hex by hex from the start,
by column then row.

**9.2.3** The path of a `road_march` order is found the same way, using only
steps along road and track links.

### 9.3 Step costs

The MP cost of a step into a passable hex:

| Step | Vehicle, `move` or `attack` | Vehicle, `road_march` | Foot |
| --- | --- | --- | --- |
| along a road link | 4 | 2 | 4 |
| along a track link | 4 | 3 | 4 |
| otherwise, into desert or oasis | 4 | not allowed | 4 |
| otherwise, into rough | 8 | not allowed | 4 |
| crossing a pass, in addition | +2 | +2 | +2 |
| crossing a cliff, in addition | not allowed | not allowed | +8 |
| into a hex with an enemy fortification, in addition | +2 per level | +2 per level | +2 per level |

Path-finding (9.2) ignores the fortification cost; it is paid when the step is
taken.

### 9.4 Impulses

**9.4.1** The Movement phase is `IMPULSES` impulses, numbered from 1. In each,
every unit takes at most one step.

**9.4.2** By the end of impulse `i` a unit with allowance `A` has earned
`floor(A × i / IMPULSES)` MP. A unit may take a step in impulse `i` only if
the MP it has earned, less the MP it has spent, are at least the step's cost.

**9.4.3** A unit that has **stopped** takes no more steps this phase.

### 9.5 One impulse

The steps of an impulse are settled in this sequence, for both sides at once,
from the positions at the start of the impulse.

**9.5.1 Who tries.** A unit tries its next step if it has not stopped, has a
next hex on its path, and has earned the MP (9.4.2). Then, in sequence:

1. If the next hex holds an enemy unit, the unit stops (**contact**).
2. If the unit's hex and the next hex are both in an enemy zone of control,
   judged from the positions at the start of the impulse, the unit stops.
3. If the unit is a vehicle and holds less fuel than the step costs (9.7.1),
   the unit stops (**out of fuel**).

A unit that reaches the end of its path has stopped.

**9.5.2 Enemy-held hexes.** A hex that held an enemy unit at the start of the
impulse cannot be entered in that impulse, even if that enemy is leaving it.
(So two enemy units trying to change places both stop, by 9.5.1.)

**9.5.3 Both sides into one hex.** If units of both sides try to enter the
same hex, one side enters and the other's units stop where they are:

- if exactly one side has a unit ordered `attack` among those trying, that
  side enters;
- otherwise the priority side (1.6) enters.

**9.5.4 Full hexes.** A hex cannot end the impulse over the stacking limit
(4.3.1). Assume first that every unit still trying moves. Then, for each hex
in standard order that would be over the limit, the units trying to enter it
are refused, highest id first (combat units for the combat limit, HQs for the
HQ limit), until it is not. A refused unit stays where it is, which may put
another hex over the limit; repeat until no hex is over. A refused unit has
not stopped: it keeps its MP and tries again in the next impulse.

**9.5.5 The steps happen.** Every unit still trying enters its next hex, and
spends the MP and fuel.

**9.5.6 Entering.** When a unit enters a hex with an enemy fortification, the
fortification is removed. Place ownership is settled at the end of the phase
(3.4.2).

**9.5.7 Contact after moving.** Every unit that took a step in this impulse
and is now in an enemy zone of control, judged from the positions after
9.5.5, stops.

### 9.6 Zones of control

**9.6.1** A hex is in a side's zone of control if it is passable, it is
adjacent to a combat unit of that side, and the hexside between them is not a
cliff. HQs have no zone of control.

**9.6.2** A unit that starts an impulse in an enemy zone of control may step
out of it, into a hex that is not in one (9.5.1).

**9.6.3** A unit entering an enemy zone of control stops (9.5.7).

**9.6.4** A friendly unit in a hex does not cancel an enemy zone of control
for movement. It does for supply paths (6.4.2) and for retreats (10.6.2).

### 9.7 Fuel

**9.7.1** A vehicle pays `size × FUEL_HEX[type]` tonnes of fuel for each hex
it enters in the Movement phase. Foot units pay none.

**9.7.2** A vehicle ordered to move with too little fuel for its first step
stops in impulse 1 without moving. Its order was legal; the event log records
"out of fuel". If its order is `attack` and it stands next to its target, it
still attacks (10.2).

**9.7.3** Retreats and advances after combat (10.6, 10.7) cost no fuel and no
MP.

### 9.8 Cohesion

**9.8.1** At the end of the Movement phase each unit loses
`floor(MP spent / MOVE_COHESION_DIV)` cohesion.

### 9.9 HQs

**9.9.1** An HQ's `stationary` flag is cleared when it enters a hex for any
reason, and set at the end of any Combat phase of a turn in which it entered
none.

**9.9.2** When an HQ enters a hex its dump is cut down by 6.11.4.

### 9.10 Constants

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `IMPULSES` | 24 | impulses in a Movement phase; also the most hexes a unit can move | to be tuned |
| allowance: `foot` | 16 | 4 hexes: 20 km a day | derived from a marching day of about 20–25 km; to be tuned |
| allowance: `armour` | 32 | 8 desert hexes, 16 by road march | derived from advances of 40–80 km a day by mobile formations; to be tuned |
| allowance: `guns` | 32 | as armour | to be tuned |
| allowance: `motorised` | 40 | 10 desert hexes, 20 by road march | as armour; to be tuned |
| allowance: `hq` | 40 | as motorised | to be tuned |
| allowance: `recon` | 48 | 12 desert hexes, 24 by road march | to be tuned |
| `MOVE_COHESION_DIV` | 4 | MP spent per point of cohesion lost | to be tuned |

---

## 10. Combat

### 10.1 Battles

**10.1.1** A **battle** is fought for one hex, the **battle hex**, held by the
**defenders** (every unit in it), against the **attackers** (every unit
attacking it, from one or more hexes). There is one battle per hex attacked,
however many units attack it.

**10.1.2** All battles of a turn are worked out from the state at the start
of the Combat phase, and their losses are applied together (10.5.6). A unit
may be an attacker in one battle and a defender in another in the same phase.
It is never an attacker in two.

### 10.2 Who attacks what

**10.2.1** A unit attacks if its order is `attack`, it is a combat unit, its
cohesion at the start of the Combat phase is at least `ATTACK_MIN`, and it has
a target (10.2.2). Otherwise it does not attack, and the event log says why.

**10.2.2 Target.** The unit's target is:

1. the next hex on its path, if that hex holds an enemy unit and can be
   attacked (10.2.3);
2. otherwise, of the adjacent hexes that hold an enemy unit and can be
   attacked, the one nearest the unit's destination `to` (1.4), then in
   standard hex order;
3. otherwise none.

**10.2.3** A hex can be attacked by a unit if it is adjacent to the unit's
hex and the hexside between them is not a cliff.

**10.2.4** No unit attacks under any other order. A unit under `move` or
`road_march` that stops in contact fights only if attacked.

### 10.3 Stores

**10.3.1** Before values are worked out, each attacker pays
`size × ATTACK_STORES` tonnes of stores and each defender
`size × DEFEND_STORES`. A unit that is both pays both, the attack first. A
unit that holds less pays what it holds and is **short** for that battle.

### 10.4 Values

**10.4.1** Let `Sd` and `Hd` be the soft and hard steps among the defenders,
and `Sa` and `Ha` among the attackers (4.1.4).

**10.4.2 Efficiency.** For each unit in a battle:

- `CF = 50 + floor(cohesion / 2)`;
- `XP` = 80 green, 100 regular, 120 veteran;
- `SF` = 50 if the unit is short for this battle (10.3.1) or its
  `out_of_stores` flag is set, otherwise 100.

**10.4.3 Attack value** of an attacker with `n` steps and the type values
`AS`, `AH` of 10.9:

`av = floor(10 × n × (AS × Sd + AH × Hd) × CF × XP × SF × UP / ((Sd + Hd) × 100000000))`

where `UP` is `UPHILL_PCT` if the unit attacks across a pass from the low
side to the high side, otherwise 100.

**10.4.4 Defence value** of a defender with `n` steps and the type values
`DS`, `DH`:

`dv = floor(10 × n × (DS × Sa + DH × Ha) × CF × XP × SF × PP / ((Sa + Ha) × 100000000))`

where `PP` is `REST_PCT` if the unit's order is `rest`, `COLUMN_PCT` if it is
`road_march`, otherwise 100.

**10.4.5 Totals.** With `k` the number of different hexes the attackers
attack from, and `air` the side's support percentage this turn (7.3, else 0):

- `Att = floor(sum of av × (100 + FLANK_PCT × (k − 1)) × (100 + air) / 10000)`
- `Def = floor(sum of dv × (100 + ground) × (100 + air) / 10000)`, and at
  least 1,

where `ground` is the sum of: `ROUGH_PCT` if the battle hex is rough;
`TOWN_PCT` if it is a town hex (3.4.1); `FORT_PCT` times the level of the
defenders' fortification in the hex.

**10.4.6** If `Att` is 0 the battle is not fought: no losses, no retreat. The
stores already paid are not returned.

### 10.5 Losses

**10.5.1 Cohesion.** Every defender loses
`CLd = clamp(floor(COH_LOSS × Att / Def), COH_MIN, COH_MAX)` cohesion. Every
attacker loses `CLa = clamp(floor(COH_LOSS × Def / Att), COH_MIN, COH_MAX)`.

**10.5.2 Steps.** The defenders together lose
`floor(defender steps × min(STEP_MAX, floor(STEP_LOSS × Att / Def)) / 100)`
steps. The attackers together lose
`floor(attacker steps × min(STEP_MAX, floor(STEP_LOSS × Def / Att)) / 100)`.

**10.5.3 Which units.** A side's step losses in a battle are taken one at a
time, each from the combat unit of that side in the battle that then has the
most steps left (ties: lowest id), counting only losses in this battle. An HQ
loses its step only when every combat unit of its side in the battle has
none left.

**10.5.4** A unit in two battles takes the losses of both. Its step losses are
worked out separately in each from its steps at the start of the phase, then
added, and cannot exceed the steps it has.

**10.5.5 Wrecks.** The engine records, for each battle and each armour unit,
the steps that unit lost in it (for 11.1).

**10.5.6** All losses of all battles are then applied together. A unit at 0
steps is destroyed.

### 10.6 Retreat

**10.6.1 Who retreats.** In a battle where `CLd ≥ CLa + RETREAT_MARGIN`, every surviving
defender retreats: two hexes if its cohesion is now below `ROUT_COHESION`,
otherwise one. In every other battle nobody retreats. Attackers never
retreat as attackers.

**10.6.2 Where.** A retreating unit may step into an adjacent hex that:

- is passable, and not across a cliff if the unit is a vehicle;
- holds no enemy unit;
- is not in an enemy zone of control, unless a friendly unit is in it;
- is not a hex from which its battle hex was attacked;
- would not be over the stacking limit.

**10.6.3 Which.** Of those hexes: the one with the greatest sum of distances
(1.4) to the hexes its battle hex was attacked from; then the one nearest its
side's base hex (3.5.3); then by direction 0 to 5.

**10.6.4 Through a full hex.** If no hex qualifies, but some adjacent hex
fails only the stacking test, the unit may pass through such a hex to a hex
beyond it that qualifies in full (counting as its whole retreat, of one hex or
two). The through-hexes are tried in the order of 10.6.3; the first that has
a qualifying hex beyond it is used, and the hex beyond is chosen by 10.6.3.

**10.6.5 Nowhere to go.** If there is still no hex, the unit **surrenders**:
it is destroyed.

**10.6.6 Second hex.** A unit retreating two hexes takes the first by
10.6.2–10.6.5 and then the second by 10.6.2–10.6.3 from its new hex. If no
hex qualifies for the second, it stays after the first; it does not
surrender. The second hex is never its battle hex.

**10.6.7 Order.** Retreats are taken one at a time, against the positions as
they then stand: battles in standard order of battle hex; within a battle,
units by id.

### 10.7 Advance

**10.7.1** After all retreats, for each battle in standard order of battle
hex: if no unit of the defending side is in the battle hex, the attackers of
that battle that survived and did not retreat this phase enter it, in id
order, each only if the hexside is not a cliff for it and the stacking limit
allows.

**10.7.2** An advancing unit ignores zones of control. Entering removes an
enemy fortification (9.5.6) and cuts down an HQ's dump (6.11.4).

**10.7.3** Place ownership is then settled (3.4.2).

### 10.8 Cases

**10.8.1 Several units attacking one hex** are one battle (10.1.1): their
attack values are added, and each extra hex they attack from adds
`FLANK_PCT`.

**10.8.2 Two units attacking each other** make two battles, one for each
unit's hex. Both are worked out from the starting state. Either, both or
neither defender may retreat. A unit that retreats does not advance.

**10.8.3 A unit attacked while it attacks** defends its own hex at full
value; attacking does not weaken its defence.

**10.8.4 An HQ alone in a hex** is a defender with the values of 10.9.

**10.8.5 A hex attacked from every side** leaves a retreating defender no hex
under 10.6.2, and it surrenders.

**10.8.6 A retreat into a hex another battle emptied** is allowed if the hex
qualifies; then no enemy advances into it (10.7.1).

### 10.9 Constants

Per step, by type:

| Type | Target | `AS` attack on soft | `AH` attack on hard | `DS` defence against soft | `DH` defence against hard |
| --- | --- | --- | --- | --- | --- |
| `armour` | hard | 6 | 6 | 4 | 6 |
| `motorised` | soft | 12 | 6 | 18 | 9 |
| `foot` | soft | 9 | 3 | 18 | 6 |
| `guns` | soft | 12 | 12 | 12 | 30 |
| `recon` | hard | 2 | 1 | 2 | 2 |
| `hq` | soft | 0 | 0 | 3 | 3 |

All to be tuned. The shape is from `DESIGN.md` §7: armour is punished by guns
(`DH` 30), does well against infantry in the open, and an attack that mixes
soft and hard steps lowers the defenders' best value.

The values allow for the steps being of different sizes (4.2.1): a battalion
is set against roughly thirty tanks. Checked by hand, before any ground or
fortification: an armoured brigade of 15 steps attacking a foot brigade of 3
in the open has 900 against 180, five to one; against a foot division of 9
steps, 900 against 540; against a gun group of 4 steps, 900 against 1,200,
and the tanks lose. Because soft and hard steps are counted alike in 10.4.1,
a mixed force with many tanks counts as mostly hard; that is a known
roughness.

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `ATTACK_STORES` | 100 | tonnes of stores per size to attack | derived with `UPKEEP` (6.12); to be tuned |
| `DEFEND_STORES` | 50 | tonnes of stores per size to defend | to be tuned |
| `UPHILL_PCT` | 50 | attack value across a pass, uphill | to be tuned |
| `REST_PCT` | 75 | defence value of a resting unit | to be tuned |
| `COLUMN_PCT` | 50 | defence value of a unit on a road march | to be tuned |
| `FLANK_PCT` | 15 | added per extra hex attacked from | to be tuned |
| `ROUGH_PCT` | 50 | added to defence in rough | to be tuned |
| `TOWN_PCT` | 50 | added to defence in a port or town | to be tuned |
| `FORT_PCT` | 25 | added to defence per fortification level | to be tuned |
| `COH_LOSS` | 20 | cohesion lost by each side at even odds | to be tuned |
| `COH_MIN`, `COH_MAX` | 5, 60 | least and most cohesion lost in a battle | to be tuned |
| `STEP_LOSS` | 10 | per cent of steps lost at even odds | to be tuned |
| `STEP_MAX` | 40 | most per cent of steps lost in a battle | to be tuned |
| `RETREAT_MARGIN` | 5 | how much more cohesion the defenders must lose than the attackers to be driven back | to be tuned |
| `ROUT_COHESION` | 20 | below this a retreating unit goes two hexes | to be tuned |

---

## 11. Recovery

### 11.1 Tanks

**11.1.1** For each battle fought this turn, the side that **holds the
field** is the attacking side if the defenders retreated (10.6.1) or none of
them survived, and otherwise the defending side. (A defender that left its
hex only by advancing in another battle still holds this field.)

**11.1.2** Each surviving armour unit of that side gets back
`floor(steps it lost in that battle × RECOVER_PCT / 100)` steps, up to its
maximum. The other side gets nothing back from that battle.

### 11.2 Cohesion

**11.2.1** A unit gains `REST_GAIN` cohesion if its order was `rest`, or
`HOLD_GAIN` if it was `hold`, provided that this turn it was traced (6.6.4),
its `out_of_stores` flag is clear, and it was in no battle.

**11.2.2** No other order restores cohesion.

### 11.3 Fortification

**11.3.1** A hex's fortification has a level, 0 to `FORT_MAX`, and belongs to
one side. It stands for diggings, wire and mines together. Scenarios may
start with fortifications in place.

**11.3.2 Hold.** If a combat unit ordered `hold` is in a hex with no
fortification and did not retreat this turn, the hex gets its side's
fortification at level 1.

**11.3.3 Dig in.** If one or more combat units ordered `dig_in` are in a hex
and did not retreat this turn, the lowest-id one that holds at least
`size × DIG_STORES` tonnes of stores pays that, and the hex's fortification
rises by one level. If none can pay, or the level is already `FORT_MAX`,
nothing is paid and nothing is built.

**11.3.4** A hex gains at most one level a turn.

**11.3.5** At the end of the Recovery phase a fortification of level 1 in a
hex with no unit is removed. One of level 2 or more stays when its hex is
empty, and goes only when an enemy unit enters (9.5.6).

### 11.4 Constants

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `RECOVER_PCT` | 50 | share of its lost tank steps the field's holder gets back | to be tuned; that recovery mattered is from source (`DESIGN.md` §5), the share is **not known** |
| `REST_GAIN` | 20 | cohesion regained by resting | to be tuned |
| `HOLD_GAIN` | 5 | cohesion regained by holding | to be tuned |
| `FORT_MAX` | 4 | highest fortification level | to be tuned |
| `DIG_STORES` | 50 | tonnes of stores per size to raise a level | to be tuned |

---

## 12. Reinforcement and withdrawal

**12.1** The scenario lists, by date (1.9): **arrivals** (a unit and its entry
place or hex), **withdrawals** (a unit) and **replacements** (a unit and a
number of steps). Each is handled in the Reinforcement phase of its turn, in
the order withdrawals, replacements, arrivals, and within each by unit id.

**12.2 Withdrawal.** The unit, if on the map, is removed wherever it is and
whatever it is doing; its status becomes `withdrawn`. It does not count as
destroyed. What it holds, and an HQ's dump, are lost (6.11.4). A unit that
has not yet arrived never does. A unit already destroyed is not affected.

**12.3 Replacement.** The unit, if on the map and traced, gains the steps, up
to its maximum. Otherwise the replacement is lost.

**12.4 Arrival.** The unit arrives with full fuel and stores and the cohesion
the scenario gives, at the first of these that is possible:

1. its entry hex, if its side owns every place there (or the hex is its
   side's base hex), no enemy unit is in it, and the stacking limit allows;
2. the nearest other hex within `ARRIVE_RADIUS` of the entry hex (1.4, then standard
   hex order) that is passable, holds no enemy unit, is not in an enemy zone
   of control, and is within the stacking limit;
3. its side's base hex, by the same tests as 1, then its neighbours by 2;
4. otherwise it does not arrive, and tries again next turn.

**12.5** An arriving unit has the order `hold` until the next Orders phase.

**12.6** Scenario values that change by date (lift, air points, `sea_pct`,
`fuel_pct`, railhead) take effect from the Supply phase of the turn their
date belongs to.

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `ARRIVE_RADIUS` | 3 | how far from its entry hex a unit may arrive | to be tuned |

Arrival and withdrawal dates are scenario data, each from the sources in
`docs/SOURCES.md`; none is fixed in this document.

---

## 13. Victory

**13.1** The scenario lists **objectives**: a place, points per turn, and
points at the end.

**13.2** In each Victory phase, each side gains the per-turn points of every
objective it owns (3.4.2).

**13.3** In the Victory phase of the last turn, each side also gains the
end points of every objective it owns.

**13.4** Whenever a unit is destroyed (in combat, by surrender or by
starvation) the enemy gains `size × LOSS_VP` points.

**13.5 End.** The game ends after the Victory phase of the scenario's last
turn, or of any turn in which a side has no unit on the map and none still to
arrive.

**13.6 Result.** Let `d` be the Axis points less the Commonwealth points. The
scenario gives three thresholds `T1 < T2 < T3`. If `|d| < T1` the game is a
draw. Otherwise the side ahead has a tactical victory (`|d| < T2`), a major
victory (`|d| < T3`) or a decisive victory.

**13.7** The Victory phase then adds 1 to the turn number.

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `LOSS_VP` | 2 | points to the enemy per size of a unit destroyed | to be tuned |

---

## 14. What each side can see

**14.1** A player is given only its side's **view**, built at the start of the
Orders phase. Computer players get exactly this and nothing else.

**14.2 Always in the view:** the map; the turn and date; everything about the
side's own units, ports, dumps, Tripoli stock and pipeline, lift, air points
and fortifications; the owner of every place; both sides' victory points;
the scenario's schedule for the side's own arrivals and withdrawals; the
objectives.

**14.3 Spotted enemy units.** An enemy unit is spotted if it is within
`SPOT_RANGE` hexes (1.4) of any unit of the side, or within
`SPOT_RANGE_RECON` of a `recon` unit, each raised by air recon (7.5).

**14.4** For a spotted enemy unit the view gives its id, name, type, hex and
experience. If it is adjacent to a unit of the side, it also gives its steps.
It never gives its cohesion, fuel, stores, order, size or flags.

**14.5** The view gives an enemy fortification's level if its hex is within
spotting range by 14.3.

**14.6** The view gives the events of the last turn that the side took part
in: for each battle with its units, the battle hex, both sides' units in it,
both sides' step losses, who retreated, surrendered and advanced; and the
replies and events for its own units. It gives no other enemy event.

**14.7** The view holds no memory of earlier turns. A player may keep its own.

**14.8** Never in the view: enemy orders, enemy supply of any kind, enemy
lift, enemy schedules, unspotted enemy units.

| Name | Value | Meaning | Status |
| --- | --- | --- | --- |
| `SPOT_RANGE` | 2 | hexes at which any unit spots | to be tuned |
| `SPOT_RANGE_RECON` | 4 | hexes at which a recon unit spots | to be tuned |

---

## 15. Invariants

These hold after every phase unless a narrower point is named, and are
asserted after every turn of every test game.

- **I-1 Replay.** The same scenario and the same submitted orders give the
  same state, byte for byte when serialised.
- **I-2** No hex holds units of both sides.
- **I-3** No hex holds more than `STACK_COMBAT` combat units or `STACK_HQ`
  HQs.
- **I-4** Every unit on the map is in a passable hex on the map.
- **I-5** Every unit on the map has steps from 1 to its maximum; no destroyed
  or withdrawn unit is on the map.
- **I-6** Cohesion is from 0 to 100.
- **I-7** A unit's fuel and stores are from 0 to its capacities; a foot unit's
  fuel is 0.
- **I-8** No stock (port, Tripoli, pipeline, dump) is negative.
- **I-9 Supply is conserved.** For each side: the starting stocks and
  holdings and what arriving units brought, plus all it has landed, equal its
  present stocks, pipeline, dumps and unit holdings, plus all its units have
  spent, plus all burnt, plus all lost.
- **I-10** In each Supply phase, a side's lift used is at most its lift, and
  the tonnes issued at the railhead are at most `RAIL_CAP`.
- **I-11** What a side's units draw in a Supply phase is at most what its
  depots held after the hauls.
- **I-12** A port's condition is from 0 to 100.
- **I-13** A fortification's level is from 1 to `FORT_MAX`, it has one owner,
  and no unit of the other side is in its hex.
- **I-14** Every place has exactly one owner.
- **I-15** Every unit on the map has exactly one order in every Movement
  phase.
- **I-16** No unit moves more than `IMPULSES` hexes in a Movement phase, nor
  spends more MP than its allowance.
- **I-17** A side's view contains nothing listed in 14.8.
- **I-18** No phase changes state outside its list in 5.1.

I-10, I-11, I-15, I-16 and I-18 are about what happens inside a turn, so the
engine notes any breach as the turn runs; the rest are checked on the state
after it.

---

## 16. Where the constants are

| Subject | Table |
| --- | --- |
| Map | 3.6 |
| Units and stacking | 4.4 |
| Supply | 6.12 |
| Air | 7.6 (table after it) |
| Orders | 8.5 (table after it) |
| Movement | 9.10 |
| Combat | 10.9 |
| Recovery | 11.4 |
| Reinforcement | 12 (table at its end) |
| Victory | 13 (table at its end) |
| Fog of war | 14 (table at its end) |

In the engine each table is one block of named constants in the module for
that subject (`docs/ENGINEERING_NOTES.md` §4).

---

## 17. What the player must learn

*This page is the whole of it. Everything else the machine does and shows.*

**The turn.** A turn is two days. You give every formation one order. Both
sides' orders then run at the same time. Nothing is left to chance.

**The six orders.**

- **Move** — go to a hex, across country.
- **Attack** — go there and attack what you meet. One hex is attacked by
  everything you send at it, and it counts for more from several sides.
- **Hold** — stay; scrape a first line of defences; recover a little.
- **Dig in** — stay and build defences, up to four levels. It costs stores.
- **Road march** — far and fast along roads and tracks. Caught in column, you
  fight at half strength.
- **Rest** — stay and recover. A resting unit defends less well.

Each turn you also send the air force to one job: support the battle, raid
the enemy's supply road, or look.

**A counter** shows its strength, how far it can move, a supply bar and a
cohesion bar. A tired or hungry unit fights badly. Below 40% cohesion it
cannot attack.

**The ground.** Desert is open. Rough ground slows vehicles and helps the
defender. Sand sea, depression and sea cannot be entered. Vehicles cross an
escarpment only at a pass. Towns and dug-in positions are hard to take.

**Fighting.** Tanks beat infantry in the open and lose to guns. Send infantry
or guns with your tanks. The loser falls back; a unit with nowhere to fall
back to surrenders. Whoever holds the field gets half its lost tanks back.

**Supply — the thing to watch.** Fuel moves vehicles. Stores feed and arm
everyone. Both land at your ports and are trucked to your headquarters;
units draw from a headquarters or a port close by, and the further from it
or from the road they stand, the less they get. The trucks can only carry
so much, and they burn fuel themselves: twice as far is less than half as
much. An enemy across the road stops it. A headquarters that stays put builds
up a dump for the next push. Out of fuel, you do not move. Out of stores, you
fall apart. Press **S** to see all of it.

**Winning.** Hold the named places, turn after turn, and do not lose
formations.

---

## 18. Decisions taken

These were the owner's to take, and the owner accepted all of them as
written here on 3 October 2026. Each is in the rules above, and each can
still be changed in one place if play shows it wrong.

- **18.1 Stacking:** two combat units and one HQ in a hex (4.3). One counter a
  hex cannot hold the Alamein line, which is about six hexes for some twenty
  divisions.
- **18.2 Sand sea** is impassable to every unit (3.1.2). `DESIGN.md` §3.1 says
  impassable to vehicles; foot divisions did not cross the dunes either, and
  one rule is simpler.
- **18.3 The frontier wire** is drawn only. It is not in these rules.
- **18.4 Oases** are desert with a name (3.1.3). Water is part of stores.
- **18.5 Off-map bases:** Tripoli is off the map and feeds the hex at El
  Agheila at a fixed haul cost and delay (6.2.2). The Commonwealth base is
  Alexandria itself, which is on the map (6.2.3).
- **18.6 Air** is one choice per side per turn, given with the orders (7), so
  the Orders phase comes before the Air phase (5.4). Air superiority comes
  from the scenario date only; airfields are not in the map data and not in
  these rules.
- **18.7 The Sofafi escarpments** are kept as they are in the map, with no
  separate "gentle" kind. To be judged from computer-against-computer games
  of Compass.
- **18.8 The railway** serves only the Commonwealth (6.2.4).
- **18.9 Priority when supply is short:** nearest HQ first (6.7.1), stores
  before fuel (6.5.4), neediest unit first (6.8.1). The player has no order
  to change this. **Settled by the owner:** supply falls off as in life, both
  with distance along the road and with distance from it. The first is the
  lift and the fuel burnt (6.5); the second is the doubled haul cost off the
  road (6.4.1) and the falling fill (6.6.5). It may starve the spearhead;
  that is intended, and is the first thing to watch in test games.
- **18.10 No captured supply** (6.11.4), though captured dumps mattered in
  1942.
- **18.11 Minefields** are not separate from fortification (11.3.1), and the
  map has no minefield data.
- **18.12 Towns** are places, not a terrain: the defence bonus belongs to
  hexes with a port or town (3.4.1).
- **18.13 Withdrawal** removes a unit on its date even if it is in contact
  (12.2).

---

## 19. Worked by hand

Figures worked through these rules by hand, as anchors for the engine's
tests. If a rule or a constant changes, these change with it.

**19.1 Haul distances** (6.4.3) on the map as it stands, with no unit on it:

| From | To | Haul distance |
| --- | --- | --- |
| Tobruk | Gambut | 12 |
| Bardia | Fort Capuzzo | 8 |
| Derna | Gazala | 22 |
| Benghazi | Tobruk | 98 |
| El Agheila | Tobruk | 150 (so 290 from Tripoli) |
| Mersa Matruh | Sollum | 52 |
| Alexandria | El Alamein | 22 |

**19.2 A meeting of armour.** A Commonwealth armoured brigade `A` (13 steps,
size 1, regular) and an Axis armoured division `B` (12 steps, size 3,
regular), both at cohesion 100 with full stores and both ordered `attack`,
meet in open desert with no fortification and no air support. `A` has spent
20 MP and `B` 16, so by 9.8.1 `A` is at cohesion 95 and `B` at 96. They stop
adjacent, and each is the other's target: two battles (10.8.2).

- Stores (10.3.1): `A` pays 100 to attack and 50 to defend, leaving 150 of
  300. `B` pays 300 and 150, leaving 450 of 900. Neither is short.
- Efficiency (10.4.2): `CF` is 97 for `A` and 98 for `B`.
- Values: `A` attacks with 756 and defends with 756; `B` attacks with 705
  and defends with 705.
- Battle for `B`'s hex: `Att` 756, `Def` 705. `CLd` 21, `CLa` 18. Each side
  loses 1 step.
- Battle for `A`'s hex: `Att` 705, `Def` 756. `CLd` 18, `CLa` 21. Each side
  loses 1 step.
- Together: `A` ends with 11 steps and cohesion 59; `B` with 10 steps and
  cohesion 54.
- Retreat (10.6.1): in neither battle do the defenders lose 5 more cohesion
  than the attackers, so both stand.
- Recovery (11.1): each side holds the field of the battle it defended, and
  gets back half of the 1 step it lost there, which rounds down to none.

