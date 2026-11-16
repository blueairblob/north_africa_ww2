# Sidi Rezegh winnability check

## Traversable corridor correction, 5 November 2026

The marked relief corridor now follows `[56,13]` Sidi Rezegh → `[57,12]`
Belhamed → `[57,11]` → `[56,11]` → `[55,10]` Tobruk. These edges are the
map's existing track and road, and all admit vehicle movement. The previous
route scored `[56,12]` and then crossed the impassable vehicle cliff to
`[56,11]`. `engine/mission.py` now rejects a corridor whose adjacent edges
vehicles cannot traverse. This corrects the mission's map representation;
it does not claim a precise historical road alignment at 10 km per hex.
The [New Zealand government's campaign timeline](https://nzhistory.govt.nz/war/the-north-african-campaign/timeline)
records the division's capture of both Sidi Rezegh and Belhamed and its
Tobruk linkup on 26 November. The [Australian War Memorial's Belhamed note](https://www.awm.gov.au/collection/E84402)
places Belhamed east of Ed Duda. These support the named places and date, not
the exact map hexes of the connecting track.

On the corrected route, the Commonwealth planner must attack the visible
Axis unit at `[57,11]` once it holds both relief places. It previously chose
an equally near unit at `[56,12]`, off the scored route. Standard and Hard
again complete the full mission in **5/5** sampled games against passive Axis
after route-blocker priority was added. Both still complete **0/5** against
Easy Axis. The route change and planner correction were measured together;
the earlier outcomes below refer to the old scored route unless stated.

## 5 November 2026 computer routing and assault update

The Standard and Hard Commonwealth planners now move a spare formation away
from a full friendly stack when that stack blocks the first step of an attack
on a required held place. In seed 1941, the move lets 7th Armoured Division
pass through Sidi Rezegh and take Belhamed on turn 3. The chosen Sidi Rezegh
guard joins that assault when the visible combined odds are adequate. On turn
4, another formation holds Belhamed while the armoured group attacks the Axis
blocker in the then-marked corridor. Hard's objective guard now
recognizes the existing Belhamed garrison and permits that attack. These are
view-based planning rules; movement, combat, map terrain and the deadline are
unchanged.

In five deterministic seeds (`0`, `1`, `65`, `1941`, `2026`) against a passive
Axis, Standard and Hard each completed the **entire** Commonwealth mission and
won **5/5** games. The seed 1941 order record is a legal five-turn winning
witness on the corrected deployment and current map. Against playable Easy
Axis, both planners completed the mission in **0/5** and lost all five. The
passive result establishes that a win is possible under the current rules; it
does not validate balance or establish a winning line against active defence.
The earlier 5 November routing-only figures (both places held, corridor still
blocked) are superseded by this assault update.

## Active Axis contact check, 5 November 2026

In seed 1941, Easy Axis moves 21st Panzer-Division onto Sidi Rezegh and 15th
Panzer-Division onto Belhamed on turn 1. On turn 2, the old Commonwealth orders
sent formations 304 and 305 through Sidi Rezegh into the visible 21st Panzer
screen. Their combined visible-odds estimate was about **0.07**; both were
destroyed that turn. The route matters: a long attack order can make first
contact before its named destination. A trial of Hard's broad adjacent-attack
filter lost all five passive wins, so it was not adopted.

The planner now checks the first *visible* hostile hex on each attack path. If
the combined attack estimate is below 0.4 against visible armour, small
formations hold instead of attacking alone. This uses only the side's view.
In the same five seeds, Standard and Hard still win **5/5** against passive
Axis and **0/5** against Easy Axis. Hard's final on-map Commonwealth steps in
seed 1941 rose from 116 to 119, but none of the three Commonwealth mission
checks was met against Easy Axis. This is casualty avoidance, not an active
winning witness. The decisive open problem is assembling enough force against
the two panzer divisions at the relief places before the fifth turn ends.

### Concentration and deadline probes

A 32-policy seed 1941 sweep varied Hard's threat radius (`0`–`3`), formation
assignment penalty (`0`, `4`, `8`, `20`) and road-objective weight (`4`, `8`).
All policies used the same legal side-view order interface against Easy Axis.
None met any Commonwealth final order. Some placed the major formations nearer
the relief places, but priority weights alone did not break the defence.

As a counterfactual, the current Standard and Hard planners were given 6, 8 or
10 turns against Easy Axis on the same five seeds. Neither completed the full
mission at any duration. At eight turns, Standard occupied Sidi Rezegh in seed
1; Hard occupied Sidi Rezegh in seeds 1 and 65 and Belhamed in seed 65. At ten
turns, Standard held both places in seed 1, while Hard held Sidi Rezegh in seed
1. The corridor remained blocked in every run. These are AI diagnostics, not
support for changing the historical scenario deadline.

`scripts/benchmark_ai.py --json` now reports each named mission check at the
end of the game and which checks were met after each turn. This exposes partial
progress that a win-only benchmark hides. The next candidate should be judged
on legal orders, route and supply continuity, and simultaneous place-and-route
progress against the active defence.

### Historical reaction is a separate test

The [US Army's Crusader case study](https://www.armyupress.army.mil/Portals/7/combat-studies-institute/csi-books/deep-maneuver-lsco-volume-5.pdf)
describes an Axis command surprised by the 18 November advance: the 7th
Armoured Brigade took the Sidi Rezegh airfield against light resistance on 19
November; Rommel ordered the main panzer attack toward Sidi Rezegh for 21
November; and the Afrika Korps raided east from 24 to 26 November (pp. 16–20).
The [National Army Museum's account](https://www.nam.ac.uk/explore/sale-collection-operation-crusader)
also places the two panzer divisions' advance toward Sidi Rezegh on the night
of 20 November. In the seed 1941 Easy Axis game, 21st Panzer was already on
Sidi Rezegh and 15th Panzer on Belhamed at the end of turn 1. That is a legal
alternate Axis choice, not a replay of the dated command sequence.

Two bounded counterfactuals kept the rest of Easy Axis's legal orders: (a)
order both panzer divisions toward Bardia from turn 4, and (b) also hold both
in their start hexes on turn 1. With the current Standard and Hard Commonwealth
planners, neither produced a complete Commonwealth mission in five seeds. The
first allowed Sidi Rezegh occupation in seeds 0, 1941 and 2026; the second
allowed both relief places in seed 65. The corridor remained blocked in every
case. These scripted moves are coarse probes, not a reconstruction of Rommel's
raid or a reason to force historical decisions on a free-playing opponent.
The scenario still needs a dated reference playthrough and a separate active
opponent balance assessment.

1 November 2026. This check asks a narrow question: can the Commonwealth complete all three High Command orders within five two-day turns, and what changes when the Axis reacts?

The initial five-seed results below were measured before the Sidi Rezegh pass was added later that day. The revised-map rerun follows here. Both tables below predate the 18 November deployment correction.

## After the 18 November deployment correction

With the corrected Axis opening positions in `data/scenarios/crusader.json`, the
playable Hard Commonwealth computer completed the mission in **0/5** games
against Easy Axis and **0/5** against passive Axis, using seeds `0`, `1`, `65`,
`1941`, `2026`. All ten games completed with no invalid orders; the benchmark
checked invariants before and after each turn. These figures predate the
5 November planning update above and no longer describe the current AI.

## Revised-map rerun, 1 November 2026

Used the same playable `ComputerHard` Commonwealth, `ComputerEasy` Axis, passive `DoNothing` Axis, scenario deadline, and weather seeds `0`, `1`, `65`, `1941`, `2026`. The engine ran full turns with ordinary side views and invariant checks; all submitted orders were legal. `Standard` Commonwealth and the benchmark `Coordinated`, `Tactical`, `Baseline`, and point-focused Hard variants were also tried against Easy Axis on the same five seeds.

| Commonwealth policy | Axis policy | CW missions complete | CW wins | Seeds with a CW win |
| --- | --- | ---: | ---: | --- |
| Playable Hard, original map | Passive | 5/5 | 5/5 | 0, 1, 65, 1941, 2026 |
| Playable Hard, revised map | Passive | 2/5 | 2/5 | 1, 1941 |
| Playable Hard, original map | Easy | 0/5 | 0/5 | — |
| Playable Hard, revised map | Easy | 0/5 | 0/5 | — |
| Playable Standard, revised map | Easy | 0/5 | 0/5 | — |
| Four benchmark Hard variants, revised map | Easy | 0/20 | 0/20 | — |

An intermediate map containing **only** the newly named pass, with all original road, track and rail traces retained, reproduced the revised map's 2/5 passive and 0/5 Easy results. The change comes from the new crossing, not from the regenerated Tobruk–El Adem track or railway. In passive seed `0`, the old route led the Commonwealth to occupy both Sidi Rezegh and Belhamed, while the pass drew several formations toward Sidi Rezegh; at the deadline they held Sidi Rezegh but had not occupied Belhamed or cleared the corridor. In all five revised-map Hard-versus-Easy games, none of the three Commonwealth mission checks was met at the deadline; Axis Easy retained a blocking unit in the marked corridor.

**Interpretation:** the revised scenario is still demonstrably possible against passive opposition, but these computer policies produced no legal winning example against an active Easy Axis. The sample does not prove that a human win is impossible. It does show that the new pass is an AI routing and scenario-balance regression worth addressing before presenting this scenario as a fair introductory Commonwealth battle. One next experiment is a mission-aware plan that concentrates on Belhamed and the middle clearance hex while guarding the Sidi Rezegh hold; compare its order transcript with the failed seeds before changing combat or the deadline.

The [supply reconnaissance and raid check](SIDI_REZEGH_SUPPLY_INTELLIGENCE.md) found that a Bardia diversion can capture the port, but did not win any of 15 tested five-turn games against Easy Axis. It should not replace the mission-focused assault in this short scenario.

## Original-map findings

- Before the pass was added, the playable Hard Commonwealth computer completed the mission in **5/5** games against a passive Axis that gave no orders (seeds `0`, `1`, `65`, `1941`, `2026`). This is a legal five-turn winning witness for each seed. It rules out a scenario that is impossible under *all* Axis play.
- The same Hard Commonwealth completed it in **0/5** against playable Axis Easy on those seeds; Axis won all five. See `docs/SIDI_REZEGH_COMBAT_SUPPLY_AUDIT.md` for combat and supply traces.
- Standard, Hard, AlwaysAttack, point-only Hard and point-only Standard Commonwealth policies all failed against Axis Easy in seeds `0` and `1941`.
- Four fixed two-target assault allocations and fifty additional random fixed allocations of nine Commonwealth formations all failed against Axis Easy in seed `0`. The best achieved only one of the three required Commonwealth checks. These policies gave legal orders, but are simplistic; their failure is **not a proof of impossibility**.
- Merely extending the existing Hard-vs-Easy game to 6, 7, 8 or 10 turns did not complete the mission in seeds `0` or `1941`. This is a counterfactual check of the current planner, not a historical scenario recommendation.

The mission requires a Commonwealth unit on Sidi Rezegh, a Commonwealth unit on Belhamed, and **no Axis unit on any hex** of the five-hex corridor at the end of the game. The Axis needs only one friendly unit on that corridor to fulfil its blockade order. This deliberately creates a high burden for the attacker. The fixed corridor is a modeled link; an alternate physical link would not count. In the seed `0` Easy-vs-Hard trace, Axis Easy moved Brescia and Trento into the corridor's middle hex and left Artillery Group Boettcher, later joined by the Bardia garrison, at Belhamed. Sidi Rezegh became empty on turn 3, but the Commonwealth Hard planner did not occupy and hold it; its attacks were split across the wider front. The final corridor remained blocked.

**Map/mission finding and subsequent correction:** the original displayed corridor joined Sidi Rezegh `[56,13]` directly to Belhamed `[57,12]` across a cliff hexside, then joined `[56,12]` to `[56,11]` across another cliff. Original vehicle movement detoured six steps between Sidi Rezegh and Belhamed. The official New Zealand histories describe a track down the Sidi Rezegh escarpment, gullies usable by vehicles with difficulty, and a narrow valley exposed to fire. On 1 November an approximate pass was added at the first edge, allowing direct vehicle movement and attacks there with the pass penalty. The second edge remains a cliff; on 5 November the scored route was moved through `[57,11]`, following existing track and road around it. The mission overlay now marks the traversable scored route. This is a coarse interpretation at 10 km per hex, not a precise reconstruction of the mosque track.

**Conclusion for the original map:** the scenario was demonstrably winnable against passive Axis. Whether a human can beat Axis Easy in five turns remained unproven. The sampled active-opponent results were poor enough that Sidi Rezegh should **not** be presented as a validated introductory or balanced Commonwealth game. The evidence pointed at Commonwealth AI planning, a demanding mission, and the original corridor depiction. No combat or supply engine defect was found in the prior audit. See the revised-map rerun above for the current results.

## Next verification

1. Build a search or scripted opponent that can choose orders anew each turn and focus the Tobruk garrison, 7th Armoured, New Zealand and South African formations on a joint assault, including the middle corridor hex. Search for at least one legal Commonwealth win against **playable Axis Easy** on a fixed seed. Save the complete order transcript if found.
2. Compare any winning witness with Hard's orders and improve the planner without leaking hidden Axis state. If no witness is found after a substantial search, test one scenario change at a time: starting positions and stocks, defender fortification, path representation, or deadline. Keep the historical 27 November endpoint explicit if a shorter variant remains. Check the approximate Sidi Rezegh pass against a georeferenced period survey sheet when available.
3. Verify the result with human play and more seeds before describing any difficulty level as balanced. The five-seed observations here are diagnostics, not estimates of human win rate.
