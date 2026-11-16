# Sidi Rezegh: combat, attrition and supply audit

Audit date: 1 November 2026. Question: why does Easy Axis repeatedly beat Hard Commonwealth in the five-turn short scenario, and are combat and supply applying their rules?

## Reproduction

Ran the current playable `ComputerEasy` as Axis and `ComputerHard` as Commonwealth through the engine's ordinary side views for seeds `0`, `1`, `65`, `1941`, `2026`. Each turn ran weather, supply, orders, air, movement, combat, recovery, reinforcement and victory. All orders were accepted, neither side saw hidden state, and engine invariants plus phase-change audits passed at the start and end of every turn.

| Seed | Final winner | Grade | CW mission complete | Axis blockade complete |
| --- | --- | --- | --- | --- |
| 0 | Axis | Tactical | No | Yes |
| 1 | Axis | Tactical | No | Yes |
| 65 | Axis | Major | No | Yes |
| 1941 | Axis | Tactical | No | Yes |
| 2026 | Axis | Tactical | No | Yes |

Five seeds reproduce the complaint; they do not establish a general win probability or human difficulty. In seed `1941`, the adjusted point margin was **−10 from the Axis perspective**, yet Axis received a tactical win because it still had a unit blocking the route at the deadline. That is the explicit mission rule, not a score arithmetic error.

## What the trace shows

Seed `1941` had 5, 9, 8, 6 and 4 battles across turns 1–5. The Commonwealth's mean cohesion among on-map units fell from about 100 at the opening to about 50 at the end; Axis cohesion fell to about 74. Battle reports show step losses and retreats on both sides. Commonwealth made no progress on any of its three required final checks in this run, while Axis held the blockade each turn. The German and Italian starting positions, particularly Sidi Rezegh's rough hex and the Axis fortification at Belhamed, give the defence strong terrain. These observations point to a difficult assault and the Commonwealth computer's attack plan as the main causes, rather than an unprocessed combat phase.

Supply was active. In seed `1941`, Axis units received 4,437, 4,983, 5,914 and 4,345 tonnes in turns 2–5; Commonwealth units received 3,514, 4,418, 3,862 and 3,127 tonnes. Port landing is larger than frontline issue and must not be read as immediate combat supply. At the start of turns 2, 3 and 5, one Commonwealth unit was untraced, but no unit on either side failed to pay upkeep. The combat-store check found **seven Axis battle participants short of stores in turn 3**, receiving the rule's half-efficiency penalty; Commonwealth had none in this seed. Thus supply costs can weaken an engagement even when the upkeep indicator still reads “in supply.”

Do not confuse the turn-five fall in Commonwealth on-map steps with battle losses. In seed `1941`, the scheduled 27 November withdrawal of 7th Armoured Brigade removed its remaining steps from the map. The turn-five battle reports show only one Commonwealth step lost in combat. The turn-five Axis losses include Savona HQ and two of its units destroyed after a battle. In other seeds, the same scheduled withdrawal also inflates a simple before/after on-map-strength comparison.

## Rule and test check

`engine/combat.py` applies the documented stores bill before values, uses half efficiency for a unit short of combat stores, combines attacker values with flanking, air and command support, combines defender values with terrain and fortification, then applies simultaneous cohesion and step losses before retreat and advance. `engine/supply.py` issues stock through reachable sources and HQs, charges upkeep, and lowers cohesion on shortages. The existing worked battle, retreat, stacking, supply route, interdiction and attrition tests passed. A new end-to-end combat test verifies that an otherwise identical attack with no stores has about half the supplied attack value and suffers at least as much cohesion loss.

No combat arithmetic or supply-flow defect was found in this audit. This is a bounded finding: the five sampled games and tests cannot prove every combination correct.

## Follow-up

The next useful work is a **Commonwealth Hard order-by-order review** against active Axis Easy and Standard. Count how many formations reach each mission hex, where attacks are spent, how often assaults are split between Sidi Rezegh and Belhamed, and which unit blocks the corridor at turn five. Then test a candidate joint attack plan against the same seeds and human play. Scenario stock, terrain, fortifications and five-turn timing are design choices to tune only after that comparison; several opening stocks and lift numbers are marked as first guesses in `data/scenarios/crusader.json`.
