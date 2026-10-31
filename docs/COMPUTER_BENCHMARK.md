# Paired computer-opponent benchmark

The offline harness at `scripts/benchmark_ai.py` compares two policies on the **same** scenario, side, opponent and weather seed. Each player receives only its normal side view. The harness checks view leaks, order replies and state invariants, then records the result. A positive `Δmargin` favours the candidate; a positive `Δloss` means more of its units were destroyed. The JSON mode includes the individual seed pairs, objective VP and turn points, supply and HQ dump losses, flank attempts and captures, shortages, untraced unit-turns, invalid orders and the candidate's order-calculation time. The table prints a descriptive paired-bootstrap interval; five seeds are a diagnostic sample, not a balance conclusion.

Examples from the repository root:

```sh
.venv/bin/python scripts/benchmark_ai.py sidi_rezegh --seeds 0 1 65 1941 2026 --sides axis cw --opponents standard easy hard
.venv/bin/python scripts/benchmark_ai.py crusader --candidate hard --baseline unrestricted --seeds 0 1 65 1941 2026 --sides cw --opponents standard --json
```

`baseline` is Hard before coordinated attack planning; `unrestricted` is the previous Hard raid policy before the moving-HQ dump cost check; `pre-flank` disables the desert raid. `tactical` is the experimental local attack filter and remains benchmark-only. `coordinated` and `hard` select the playable coordinated Hard policy.
These policy variants isolate the choices studied in this revision. Future changes to the shared planner should be compared against a fixed Git revision as well as these variants.

## Initial findings

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
