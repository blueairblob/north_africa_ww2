# Computer opponent difficulty

Each side can use `computer-easy`, `computer` (Standard), or `computer-hard` independently. The levels all receive the same side view, use legal orders, and face the same weather, combat and victory rules. A save records each side's selected level.

All levels read the public scenario mission. They seek unoccupied required places, attack visible units blocking a clear route, occupy a deny route, and keep a fighting formation on each held mission target. Hard guards other high-value places only when that does not conflict with an explicit mission. These are local decisions each turn, not a campaign-wide plan.

| Level | Planning behaviour |
| --- | --- |
| Easy | Chooses nearby objectives, rests sooner, builds only basic fieldworks, and uses basic safe road Travel. |
| Standard | Weighs objective value against distance, spreads assignments, and uses road marches and air interdiction. |
| Hard | Gives the Sidi Rezegh corridor more weight, protects held high-value objectives under threat, and can build level 4 fieldworks. It compares nearby, visible attack packages before redirecting a formation to an objective, retaining a strong second attack. In the longer campaign it may send one mobile formation and a command HQ on a supply-aware desert raid, then withdraw both. |

All levels can now take a safe road or track leg toward a distant enemy objective before switching to Attack at contact. The planner considers only visible enemy positions and avoids visible zones of control; an unseen enemy can still surprise a column. It will enter a nearby road from open desert only when the detour saves a substantial movement cost. Commonwealth formations near Sidi Rezegh often start off route, and a direct desert approach may be faster than joining the modeled road network. Travel lowers movement points per road hex but uses the same fuel per hex and makes an attacked column vulnerable. This is a tactical route choice, not a guarantee of a historically accurate two-day distance: allowances and road geometry still require calibration.

The flank is a deliberate operation chosen from public objectives and enemy units the computer can see. It checks fuel, supply, a safe approach and a second command HQ for the main force. Moving an HQ destroys dump stock above 300 tonnes of each kind, so Hard declines low-value raids that would discard a large dump. The earlier unrestricted policy sent 7th Armoured Division and XXX Corps HQ south of Sidi Rezegh on Crusader seed 1941; the cost-aware policy declines that opening but will plan the raid when XXX Corps HQ carries a lighter dump. It does not use hidden enemy positions or extra movement allowances. Hard does not attempt a deep raid in the five-turn Sidi Rezegh scenario.

The coordinated attack check is deliberately narrow. It can redirect one supplied formation from a visible, well-covered fight to an under-supported attack on an enemy-held objective. It protects a formation on a held objective and the active flank plan. It is a one-turn comparison of orders, not a persistent multi-turn mission planner. The tested scripted openings were essentially unchanged, so this feature has not yet shown a measurable difficulty gain; see [COMPUTER_BENCHMARK.md](COMPUTER_BENCHMARK.md).

## Formation-level AI direction

A later computer revision should give each formation a small, deterministic local policy under a side-wide command plan. The commander assigns an objective, posture and supply priority; the formation chooses a legal move, scout, hold, rest or withdrawal using only its side's visible information. A formation should report when its order is infeasible because of fuel, cohesion, route blockage or an unseen contact. The commander must still coordinate shared objectives, road capacity, attack packages, HQ coverage and reserves; independently greedy counters would fight each other for the same hex and abandon the wider mission. Save the commander plan and each formation's intent so a resumed game makes the same decisions. Test that local policies improve mission completion and force preservation in paired seeded matches before making them the default. This is a design direction, not a current game feature.

## First Sidi Rezegh comparison (before mission orders)

This table records the earlier point-only AI and victory rules. It is historical and cannot be reproduced from the current game because the scenario now grades explicit High Command orders. Every pairing used the same five weather seeds and played all five turns. The adjusted margin was relative to the starting position; positive favoured Axis. Current paired mission checks are in [COMPUTER_BENCHMARK.md](COMPUTER_BENCHMARK.md).

| Axis | Commonwealth | Axis wins | Draws | Commonwealth wins | Mean adjusted margin |
| --- | --- | ---: | ---: | ---: | ---: |
| Easy | Easy | 3 | 2 | 0 | +27.0 |
| Easy | Standard | 1 | 4 | 0 | +31.8 |
| Easy | Hard | 0 | 1 | 4 | -41.4 |
| Standard | Easy | 0 | 1 | 4 | -60.2 |
| Standard | Standard | 1 | 1 | 3 | -24.8 |
| Standard | Hard | 0 | 5 | 0 | -16.8 |
| Hard | Easy | 0 | 4 | 1 | -10.0 |
| Hard | Standard | 3 | 2 | 0 | +70.4 |
| Hard | Hard | 0 | 1 | 4 | -63.4 |

These are exploratory matches, not proof of balanced difficulty. The Axis begins with both corridor objectives, and a passive opponent can leave the adjusted score near a draw. Hard changes decision quality and priorities, but it cannot guarantee a win from either side. The next tuning pass should include more seeds in both scenarios and playtest observations about supply and sector choices.

## Full Crusader smoke match

Before the desert flank was added, `scripts/compare_computers.py crusader --seeds 1941` completed all nine level pairings over 22 turns with the engine invariants intact. On that seed, Hard Commonwealth won against all three Axis levels; Hard Axis lost against all three Commonwealth levels. The paired benchmark now compares the cost-aware raid policy with that unrestricted version over several Crusader seeds; see [COMPUTER_BENCHMARK.md](COMPUTER_BENCHMARK.md). These small samples are not a difficulty ranking. More seeds and order-by-order playtesting are needed before tuning Crusader-specific strategy.
