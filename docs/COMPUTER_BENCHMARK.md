# Paired computer-opponent benchmark

The offline harness at `scripts/benchmark_ai.py` compares two policies on the **same** scenario, side, opponent and weather seed. Each player receives only its normal side view. The harness checks view leaks, order replies and state invariants, then records the result. A positive `Δmargin` favours the candidate; a positive `Δloss` means more of its units were destroyed. The JSON mode includes the individual seed pairs, objective VP and turn points, supply and HQ dump losses, flank attempts and captures, shortages, untraced unit-turns, invalid orders and the candidate's order-calculation time. The table prints a descriptive paired-bootstrap interval; five seeds are a diagnostic sample, not a balance conclusion.

Examples from the repository root:

```sh
.venv/bin/python scripts/benchmark_ai.py sidi_rezegh --seeds 0 1 65 1941 2026 --sides axis cw --opponents standard easy hard
.venv/bin/python scripts/benchmark_ai.py crusader --candidate hard --baseline unrestricted --seeds 0 1 65 1941 2026 --sides cw --opponents standard --json
```

`baseline` is Hard before coordinated attack planning; `unrestricted` is the previous Hard raid policy before the moving-HQ dump cost check; `pre-flank` disables the desert raid. `tactical` is the experimental local attack filter and remains benchmark-only. `coordinated` and `hard` select the playable coordinated Hard policy.
`points-standard` and `points-hard` disable mission-aware decisions in the otherwise current Standard and Hard policies. Use them to isolate mission planning from other rule changes. Future changes to the shared planner should also be compared against a fixed Git revision.

## High Command mission planning, 31 October 2026

The playable levels now read their side's public High Command orders. They target required places, attack *visible* blockers on a clear route, occupy a deny route and keep a fighting formation on each held mission target. Hard no longer diverts the Commonwealth from the Sidi Rezegh relief mission to guard secondary Tobruk points; an explicit hold order still protects its named place. No policy sees hidden enemy positions. A place's point ownership alone does not satisfy an occupy order: the AI must leave a formation there.

Paired Sidi Rezegh runs use seeds `0 1 65 1941 2026`, both sides, and the same opponent for each policy pair. The table counts completed own missions and reports mean candidate margin relative to the point-only policy. Five seeds are a regression sample, not a difficulty ranking.

| Candidate | Opponent | Axis mission | CW mission | Mean Axis Δmargin | Mean CW Δmargin |
| --- | --- | ---: | ---: | ---: | ---: |
| Standard | Passive | 5→5 | 1→5 | +4.0 | −26.4 |
| Standard | Point-only Standard | 5→5 | 0→0 | +96.8 | −2.4 |
| Hard | Passive | 5→5 | 0→5 | 0.0 | +169.0 |
| Hard | Point-only Standard | 5→5 | 0→0 | −13.0 | +31.2 |

All candidate orders in these runs were legal. The lower Commonwealth point margin against a passive Axis under Standard is secondary to the now completed High Command mission, which determines the short scenario's verdict. Against an active point-only Axis, neither Commonwealth level completed all three orders in these five starts. Hard's Axis point margin varied from −57 to +67 across that pairing. Further work should improve the joint attack on Sidi Rezegh and Belhamed and test against human opponents before claiming stronger active play.

Against the playable Standard Axis, mission-aware Hard Commonwealth also completed 0/5 relief missions and averaged −118.4 point margin relative to point-only Hard; mission-aware Hard Axis kept its blockade at 5/5 but averaged −48.4 margin. This is an active-opponent regression in secondary points without an increase in mission completion. The mission-first rule is retained for the review build because it follows the stated orders, but the attacking policy needs a stronger joint battle plan. In Crusader, three seeds (`0 65 1941`) against point-only Standard were unchanged for both Hard sides, with no invalid orders.

## Initial findings

The following tactical, coordination and raid findings predate executable mission orders. Their numerical results describe that earlier policy and victory rules; use the mission-planning section above for current comparisons.

The first tactical filter estimates visible defenders by counter type and strength word, checks the attackers' stores, and holds or withdraws groups when an adjacent attack looks poor. It changed several decisions that looked sensible locally, such as a single Commonwealth brigade attacking a defended hex near Tobruk. However, the paired five-seed Sidi Rezegh tests showed material regressions:

| Candidate versus playable Hard | Axis vs Standard | CW vs Standard | CW vs Easy | CW vs Hard |
| --- | ---: | ---: | ---: | ---: |
| Mean `Δmargin`, five seeds | −68.4 | +7.2 | −45.2 | −14.4 |

The filter was therefore **not enabled** in playable Hard. A weak attack can still fix an enemy, affect the opponent's movement, and change where a later battle happens. An isolated attack/defence ratio does not value those effects. The next tactical design should compare coordinated order packages over at least one full turn, with an estimate of the opponent's possible response. A retreat should require a credible route and account for the objective it exposes.

## Coordinated attack planning, 31 October 2026

Playable Hard now compares its complete visible attack orders with up to twelve one-formation redirects toward enemy-held objectives. It considers the old target's remaining attack, the objective's current attack, the candidate's cohesion, stores, fuel, route, known enemy zones of control and held friendly objectives. The score estimates objective capture and losses across the visible battles; it never reads hidden state or simulates with omniscient information. It preserves the original order set unless the estimate improves by more than 0.5. A target already assessed at 1.2 attack/defence or better gets no extra formation, and the old target must retain at least 1.6 estimated odds. The conservative thresholds reflect uncertainty in visible enemy strength and future movement. A constructed visible state verifies that Hard can reinforce Sidi Rezegh when the old target has weak defenders; order legality, view immutability and save/replay are checked in tests.

The first permissive candidate exposed two failures: pulling an Axis group from the other attack at Sidi Rezegh cost a mean 28.8 margin points against Standard; reinforcing an already strong Commonwealth assault at Halfaya cost 28.4 against Standard in Crusader. The final guards removed those large regressions. In five paired seeds (`0 1 65 1941 2026`), the final Hard policy had **identical results** to the old Hard policy against Easy, Standard and Hard on both sides of Crusader. Sidi Rezegh was also identical except for a smaller Axis versus Standard effect at the intermediate 1.0 old-target threshold (mean −1.8); raising that threshold to 1.6 removed it in the affected five-seed pairing. These neutral scripted matches are a safety check, **not evidence that Hard now wins more often**. Human and varied-opponent playtests are still needed to measure how often the planner intervenes and whether its choices are useful.

The earlier 1941 Crusader comparison is reproducible with `--candidate hard --baseline unrestricted`: the cost-aware policy's Commonwealth margin is 57 points better and its unit-loss VP is 25 points lower against Standard Axis. Across five identical Crusader seeds against Standard Axis, the cost-aware policy averages **+31.2 margin points** and **−20.0 unit-loss VP** relative to the unrestricted raid. Its paired margin differences range from −36 to +67; the descriptive 95% paired-bootstrap interval is −6 to +59. The interval crosses zero, so this is a prudent risk reduction, **not proof** that Hard is generally stronger. Axis results were unchanged across these five starts because no Axis raid was selected. The cost check declines a low-value raid when moving the HQ would discard more than 600 tonnes of its dump; a more valuable objective or a lightly stocked HQ can still qualify.

An additional three-seed Crusader check (`0 65 1941`) gave the cost-aware Commonwealth policy **+54.3** mean margin against Easy Axis and **+76.7** against Hard Axis, with fewer unit-loss points in both pairings. These small samples support retaining the dump-cost gate. The detailed per-seed output is available with `--json`.

## Acceptance gate for a policy change

Before enabling a candidate in the game, compare it with the current Hard policy on both scenarios, both sides and the scripted opponent roster. Inspect the paired margin distribution, own unit losses, objective points, supply loss and representative replays. A result that helps one side but consistently damages another needs a narrower rule or separate operational doctrine. Save/load replay, hidden-information checks and legal orders remain mandatory. Expand the seed set before claiming a difficulty improvement.
