# Desert Rats — Mechanics Reconstruction & Build Spec

A build-ready model of the game systems in CCS's *Desert Rats* (R.T. Smith, 1985 / 1986),
reconstructed from the original rules booklet. This is a clean-room restatement of the
**rules** (systems and parameters), expressed as an implementation spec. It is not a copy of
the manual's text.

---

## 0. Status: what's recovered vs. what still needs the binary

**Fully recovered from the booklet (you can implement these now):**

- The complete sequence of play and turn structure
- The full order set and what each order does
- The two-track supply *algorithm* (the heart of the game)
- The combat model as a set of nine contributing factors, with the **direction** of each effect
- All unit types and their qualitative combat characteristics
- All terrain types and their effects
- All 8 scenarios with dates, turn counts, and victory conditions
- Malta-status balance options
- Reinforcement / replacement / withdrawal rules
- Stacking rules and supply-range distances (both 48K and 128K values)

**Still locked in the Z80 binary (must disassemble or calibrate by playtesting):**

- Exact numeric constants (movement rates per unit type, supply-consumption values,
  the combat damage formula's weights, retreat thresholds)
- The "heavy losses / losses too severe" thresholds used for victory and draw judging
- Per-scenario order of battle: exact unit strengths, starting positions, reinforcement
  schedules, withdrawal timings
- The map itself (terrain layout per square)
- The single-player AI

Recommended build order: implement the systems below against placeholder constants, get the
supply + combat loop behaving qualitatively right, then disassemble for the numbers and map
data. The systems are the hard design work and they're already done for you here.

> Version note: two releases exist. The 48K original (1985) has 6 scenarios and a 624-turn
> campaign. The 128K version (1986) adds two opening scenarios and extends the campaign to
> 736 turns, with slightly different stacking and supply-range numbers. Differences are flagged
> inline as **[48K]** / **[128K]**.

---

## 1. Core data model

### Unit

| Field | Meaning | Notes |
|---|---|---|
| `side` | British (Allied) / Axis (German or Italian) | |
| `size` | division / brigade / battalion / HQ | Only Italian units are division-size; determines supply track + stacking cost + consumption rate |
| `type` | see §7 | Drives combat matchup |
| `division` | parent division, or `independent` | Independent HQs are "Corps HQs" |
| `str` | strength (men or tanks) | |
| `mps` | moves per turn over clear terrain | Reduced on rough terrain |
| `sup` | current supply level | Low ⇒ cannot attack; zero ⇒ takes double damage; flag for "can receive supply this turn" |
| `mor` | morale | Higher ⇒ less likely to retreat after combat |
| `atkMod` | attack modifier | Higher ⇒ more effective on attack |
| `eff` | efficiency | Reduced by combat fatigue; recovered by Hold; some units start low (poor training) |
| `frt` | fortification level | = number of turns spent fortifying = defensive strength |
| `order` | current order | Persists across turns until changed (see §3) |
| `dugIn` | bool | Set by having Held the previous turn; prerequisite for Fortify |
| `identified` | bool (per opposing side) | Enemy units show as "unidentified" until they fight (fog of war) |

### Square (map cell)

Grid of **rectangular cells** (not hexes). Fields: terrain type (§8), occupying units (a stack),
and edge flags. Movement and supply tracing both use 8-directional adjacency
(horizontal, vertical, diagonal).

### Side (per player)

- Off-map **supply pool** (replenished per scenario / Malta status)
- **Replacement pools**: armour (for tank units) and infantry (for everything else), German
  and Italian replacements tracked separately
- Supply points received per turn

---

## 2. Sequence of play

Each normal turn = one day. Quiet stretches collapse into **reorganisation phases** of 6 days
per turn.

```
TURN:
  1. British player issues orders to all units
  2. Axis player issues orders to all units
  3. All units move SIMULTANEOUSLY to execute orders
  4. Combat resolves between units that end adjacent
  5. Units forced to retreat move; units they were blocking may continue
  6. Advance date; next turn
```

- **Surprise rule:** on the first turn of each scenario, only the attacking side may order
  (the other side is frozen).
- **Dug-in stalemate:** a dug-in unit will not attack an enemy that is also dug in.
- Orders are *sticky*: pressing confirm without changing anything keeps the previous order, so a
  multi-turn move continues automatically until redirected. This is the basis of the
  "axis of advance" strategy (set an objective behind enemy lines; units pursue/attack/advance
  without re-orders).

---

## 3. Orders

| Order | Effect |
|---|---|
| **Move** | Travel toward a destination at normal speed. Persists across turns. Auto-assigned if you point away from a Hold/Fortify unit. |
| **Assault** | Like Move but aggressive: deals more damage in combat and takes more. Consumes ~2× the supply of Move in combat. |
| **Hold** | Stay put and dig in (protection, esp. vs armour). Recovers efficiency. Eligible to receive replacements. Very low supply use. |
| **Travel** | Move along road at **4× speed**. Only if on a road and not adjacent to an enemy. Cannot attack; very vulnerable while travelling. |
| **Go To Port** | One British unit per turn may move Alexandria ↔ Tobruk by sea. Requires Tobruk to be British-held. |
| **Fortify** | Strengthen position (mines, fox holes); effect grows with turns spent. Requires being already dug in (Held last turn). Tanks cannot fortify. All benefit lost if the unit moves. Consumes supply. |
| **Divide** | (Not an order) Temporarily split a stacked division so sub-units can be ordered separately. |
| **Report** | (Not an order) Show the unit's stats. |

---

## 4. Supply — the central system

Supply is consumed only when a unit **moves, fortifies, or fights** (the designer's deliberate
abstraction: petrol + ammunition, not food/water). Consumption scales with unit size
(division > brigade > battalion/HQ). Assault in combat costs ~2× Move; Hold costs very little.
A unit with insufficient supply **cannot attack**; a unit with zero supply takes **double damage**
when attacked.

Replenishment runs on **two separate tracks by unit size.**

### Track A — Battalions & brigades (last-mile)

A unit can draw supply only if it is **adjacent to or stacked with an HQ**, subject to:

- Any unit may draw from a **Corps HQ** (independent HQ).
- An **independent** unit may draw from **any** HQ.
- Otherwise a unit draws **only from its own divisional HQ**.

### Track B — Divisions & HQs (strategic line)

These trace supply back to their own board edge. Rules:

- Draw supply if within range of a **road** square, **provided the road is clear of enemy units
  all the way back to the map edge** — left edge for Axis, right edge for British.
- **Geometry constraint:** the unit must lie on the same **horizontal, vertical, or diagonal**
  line as the supply source. (This is the rule that makes the whole game positional — you often
  nudge a unit one square to get "in supply".)
- **Tracks** work like roads, if a clear route exists along the track back to a road and thence
  to the edge.
- **Ports** (Benghazi, Tobruk) work like a road square back to the edge.
- **No HQ may draw from another HQ.**
- **Transport cost:** supply is consumed in transit; the farther along the line, the less arrives.
  Port routes leak more than road routes.
- An enemy unit anywhere on the trace **blocks** it. ⇒ A single fast recce unit on a road behind
  the line can starve an entire force. This is the core offensive idea.

Range distances:

| | Straight | Diagonal |
|---|---|---|
| **[48K]** | 7 squares | 5 squares |
| **[128K]** | 10 squares | 7 squares |

**Implementation sketch (per side, each turn):**

```
for each division/HQ unit U on side S:
    inSupply[U] = exists a supply source X (road/track-to-road/port)
        such that:
            - U and X are colinear (H, V, or diagonal) AND within range
            - the path X -> ... -> S.boardEdge is clear of enemy units
    if inSupply[U]: deliver = poolDraw - transportLoss(distance, viaPort)

for each battalion/brigade unit U on side S:
    inSupply[U] = exists adjacent/stacked HQ H such that
        (H is CorpsHQ) or (U independent) or (H == U.division.hq)
```

The "can receive supply" flag in a unit's report is exactly `inSupply[U]`.

---

## 5. Combat

Combat occurs between units that **end movement adjacent**. Damage is a weighted function of
nine factors. The booklet documents the **direction** of each; the **weights/curve** are the
main thing to recover from the binary.

| # | Factor | Direction of effect |
|---|---|---|
| a | Attacker vs. defender **type matchup** | See §7 matchup notes |
| b | **Strengths** of both units | Higher attacker str ⇒ more damage |
| c | Attacker's **order** | Assault ⇒ more dealt + more taken; Move ⇒ baseline; Hold ⇒ little dealt |
| d | **Terrain** of the defender | Cover reduces damage (see §8) |
| e | Attacker's **attack modifier** and **efficiency** | Higher ⇒ more effective |
| f | Defender's **supply** | Zero supply ⇒ defender takes **double** damage |
| g | Defender **dug in / fortified** | Strongly reduces damage taken (esp. vs armour) |
| h | **Other units stacked** with the defender | Stack contributes to defence |
| i | Attacker on **escarpment attacking uphill** (away from the sea) | Reduces attacker effectiveness |

Outcome: if damage exceeds a threshold the unit **retreats** (likelihood gated by morale).
Retreats happen in step 5 of the turn and can free up units that were blocked.

---

## 6. Reinforcements, replacements, withdrawals

- **Replacements** arrive **monthly**, split into armour (tank units) and infantry (others);
  German and Italian pools tracked separately. Distributed automatically to under-strength
  units, but **only units on Hold orders receive them**. With enough accumulated, destroyed
  units can be **rebuilt**.
- **Reinforcements / withdrawals** happen automatically on a historical schedule; withdrawals
  are pre-warned.
- In the full campaign (scenario 8) or extended games, units can **change type, designation, or
  parent division** over time to mirror the historical reorganisations.

---

## 7. Unit types

| Type | Combat character |
|---|---|
| Medium tank | Powerful vs tanks, very strong vs infantry; weak vs dug-in; vulnerable to HQ / artillery / anti-tank |
| Light tank | Like medium but weaker and more vulnerable; slightly faster |
| Infantry tank | Very slow; weak vs tanks but very strong vs infantry; hard to kill |
| Recce | Deals/takes little; very fast; cuts supply lines & retreats; usually retreats when attacked |
| Motorised infantry | Weak attacker; vulnerable to tanks unless dug in; can fortify; good vs fortified/dug-in |
| Foot infantry | As motorised but slower |
| Support group | Infantry + artillery mix; better vs tanks than plain infantry, worse vs infantry |
| Artillery | Good vs tanks; vulnerable to infantry |
| Anti-tank | Effective vs tanks only; vulnerable to infantry |
| HQ | Admin + divisional artillery; useful vs tanks; very vulnerable — must be supported |

**Stacking points:** division = 7, brigade = 3, HQ = 1, battalion = 1.
Max per square: **[48K]** 13 · **[128K]** 10. (Rule of thumb: one full division stacks together.)

---

## 8. Terrain

| Terrain | Effect |
|---|---|
| Sea | Impassable |
| Salt marsh | Impassable |
| Steep escarpment | Impassable |
| Escarpment | Slows movement; **best** cover of the slowing types — benefit only if **behind** it, not on it |
| Ridge | Slows movement; some cover |
| Rough | Slows movement; some cover |
| Fortification square | Best protection; benefit only if **on** the square |
| Fort | Best protection; on-square; forts/fortifications around towns count alike but give different Fortify benefits |
| Road | Enables Travel (4× speed); primary supply artery |
| Track | Secondary supply route (must reach a road then the edge) |
| Town | Settlement square |
| Port | Benghazi, Tobruk — supply entry like a road back to the edge |

Escarpments interact with combat factor (i): attacking *up* an escarpment (away from the sea)
penalises the attacker.

---

## 9. Scenarios

**[128K]** scenario set (the 48K set is items 3–7 plus a 624-turn campaign):

| # | Scenario | Turns | Dates | Victory conditions |
|---|---|---|---|---|
| 1 | Operation Compass | 45 | 9 Dec 1940 – 22 Jan 1941 | **Br:** capture Bardia & Tobruk. **It:** hold Egypt; deny Derna to Br. |
| 2 | Beda Fomm | 15 | 24 Jan – 7 Feb 1941 | **Br:** capture Benghazi, destroy Italian army. **It:** frustrate, hold territory. |
| 3 | Enter Rommel | 31 | 31 Mar – 30 Apr 1941 | **Axis:** capture Tobruk or cut its road. **Br:** prevent. |
| 4 | Battleaxe | 7 | 15 – 21 Jun 1941 | **Br:** clear road to Tobruk of enemy. **Axis:** prevent. |
| 5 | Operation Crusader | 45 | 18 Nov 1941 – 1 Jan 1942 | **Br:** clear road to Tobruk and/or heavy Axis casualties. **Axis:** keep Tobruk besieged, hold Egyptian border. |
| 6 | Battle of Gazala | 39 | 26 May – 3 Jul 1942 | **Axis:** capture Tobruk, advance far. **Br:** hold Gazala or inflict heavy losses. |
| 7 | El Alamein | 19 | 23 Oct – 10 Nov 1942 | **Br:** advance to Libyan/Egyptian border, heavy Axis losses. **Axis:** hold as far forward as possible. |
| 8 | The Desert War (campaign) | 736 | 9 Dec 1940 – 14 Dec 1942 | Destroy all opposing units. |

**[48K]** campaign: 624 turns, 31 Mar 1941 – 14 Dec 1942.

**Draw rule (all scenarios):** meeting your victory conditions is not enough — if the engine
judges your own losses too severe, the result is a **draw**. (Threshold value: unknown → binary.)

**Extend Game:** when a scenario ends you may continue play to the end of the *next* scenario,
re-judged under that scenario's victory conditions; chainable onward.

---

## 10. Malta status (balance lever, in place of difficulty levels)

| Option | Effect |
|---|---|
| Historical | Baseline Axis supply (Malta interdiction as it really was). |
| Operation Herkules | Assumes Malta captured in summer 1942 ⇒ Axis gets greatly increased supply in the latter half of 1942. |
| Not used as base | Assumes Malta neutralised ⇒ Axis supply increased throughout the game. |

General balance note baked into the design: the **Axis player receives less supply** than the
British and must husband it carefully.

---

## 11. Disassembly checklist (the numbers to extract)

When you move to the binary, these are the specific unknowns to recover, roughly in priority
order for getting a faithful feel:

1. **Combat damage formula** — how factors a–i combine into a damage number, and the
   retreat threshold vs. morale roll.
2. **Supply consumption table** — supply cost per (size × action), and the assault-vs-move and
   hold multipliers.
3. **Transport-loss curve** — supply lost vs. distance along the line, and the port penalty.
4. **Movement rates** — `mps` per unit type on clear terrain, and per-terrain slow factors.
5. **Victory/draw thresholds** — the "heavy losses" and "losses too severe" cutoffs per scenario.
6. **Per-scenario order of battle** — strengths, types, divisions, starting squares,
   reinforcement and withdrawal schedules, Malta supply schedules.
7. **The map** — terrain per square, road/track/port topology, board dimensions, and the
   campaign-time unit reorganisations (scenario 8).
8. **AI** — target selection, axis-of-advance logic, when it assaults vs. holds, supply caution.

Tooling: the binaries are preserved (archive.org, World of Spectrum, Spectrum Computing); run
under an emulator (e.g. Fuse) with a debugger, or disassemble statically with a Z80-aware
tool. A 48K image is small enough that the data tables (OOB, map) are very likely contiguous
blocks you can locate and dump.

---

## 12. Legal note

Game **mechanics and rules** (everything in this document) are generally not copyrightable, so a
clean-room reimplementation is on solid ground. The original **code, manual text, box art, and
arguably the specific map/scenario data** are protected — reimplement and re-author rather than
copy them, and treat the "Desert Rats" name as a trademark question. The author, Robert T. Smith,
is a named individual; contacting him for permission would resolve most ambiguity at once.
