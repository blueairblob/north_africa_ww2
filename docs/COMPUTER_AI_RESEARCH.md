# Research: a stronger computer commander

30 October 2026. This is an implementation proposal for the current game, not a claim that any proposed method has already improved its results. The findings combine inspection of this repository with the linked primary research below.

## Assessment of the present opponent

The engine already has a strong foundation for better AI: a headless match runner, deterministic replays, three opponent levels, a restricted side view, and a single rules engine for human and computer orders. The intended design in [DESIGN.md](../DESIGN.md) calls for strategy, operations and tactics. The implementation in [engine/computer.py](../engine/computer.py) is still primarily a per-formation heuristic. It weighs public objective points against hex distance, sends each formation to a sector, and attacks a nearby visible enemy. Hard adds some objective defence and one planned desert raid. It does not evaluate a prospective battle or compare that raid's cost with holding its armour in reserve.

That distinction matters. Before the moving-HQ dump cost check was added, the raid on Crusader seed 1941 reached Sidi Rezegh and returned its HQ and division in the short replay, but the full match's Commonwealth result was **−174** against Standard Axis, compared with **−231** for the Hard planner with the raid disabled. Negative margins favour Commonwealth; both were decisive wins. One seed cannot establish which policy is stronger, but the example demonstrates why *executing a plausible manoeuvre* is insufficient evidence of better play. The original level-comparison script reports wins and mean margins, not paired policy differences, force preservation, or supply cost.

Specific gaps visible in the code and rules:

1. **No persistent operational aim for most of the army.** Every turn, `_sector` scores goals independently. Its assignment penalty spreads units but does not assign a corps, reserve or logistics support to a mission. The only multi-turn state is Hard's one-off flank.
2. **No meaningful attack decision.** The `threat` distance can trigger an attack irrespective of force ratio, terrain, fortification, air support, likely losses or retreat risk. `fighting` only checks whether at least one member has enough cohesion.
3. **Incomplete supply reasoning.** `traced` says that a depot is in reach even if it has no stock (Rules 6.6.4). A moving HQ discards dump stock above 300 tonnes per kind (Rules 6.11.4). The current planner checks reach and immediate fuel but not projected issue, lift, upkeep, route interdiction, dump loss or a safe return.
4. **No memory of unseen enemies.** The side view correctly exposes only spotted enemy counters, with only coarse strength information even then. An enemy disappearing from sight is effectively forgotten. Direct paths are mechanical; they do not price a likely enemy zone of control or the value of reconnaissance.
5. **Victory value is static.** `_objectives` uses `end + 3 × turn`, whereas the actual game pays turn points for every remaining turn and end points only on the final turn. The right objective therefore changes as the campaign develops.
6. **One air choice for the whole side is crude.** The present policy mostly selects support when any attack is ordered, interdiction when enemies are seen, and recon otherwise. It does not compare the expected value of spotting, combat support or next turn's lift reduction.

## Research findings and fit to this game

**Hierarchical planning is a good fit.** [Adversarial HTN planning](https://ijcai.org/proceedings/2015/236) addresses large action spaces by searching over strategic tasks instead of all low-level orders. [Hierarchical adversarial search](https://ojs.aaai.org/index.php/AIIDE/article/view/12714) similarly divides strategic and tactical decisions. A [modular RTS agent](https://ojs.aaai.org/index.php/AIIDE/article/view/13033) uses a central scheduler to arbitrate proposals from specialist modules. These are research results from other games; the inference here is that Crusader should choose a **mission** first, then issue a coordinated set of formation and HQ orders. Its existing `DESIGN.md` already calls for exactly these three levels.

**Search should be selective and local.** [Combining strategic choices with tactical search](https://ojs.aaai.org/index.php/AIIDE/article/view/12922) improved a research RTS agent relative to either component alone. [Asymmetric action abstraction](https://ojs.aaai.org/index.php/AAAI/article/view/11432) spends search effort where a few units have important decisions. For this game, compare perhaps 3–6 candidate packages around a battle or flank: attack now, concentrate then attack, threaten a supply road, screen, hold, or withdraw. Keep ordinary rear-area movement heuristic. A whole-map search over every unit order is unlikely to be worth its branching cost. Simulation accuracy matters: a [combat-search study](https://ojs.aaai.org/index.php/AIIDE/article/view/12962) found that search benefits depended heavily on how well its simulator matched the real game. Here the actual Python engine is available for offline benchmarks; any runtime approximation must be checked against it.

**Hidden information must stay hidden.** [Information-set MCTS](https://eprints.whiterose.ac.uk/id/eprint/75048/1/CowlingPowleyWhitehouse2012.pdf) treats hidden-information states as one information set and discusses the error of planning as though the player could distinguish unknown states. [POMCP](https://www.davidsilver.uk/wp-content/uploads/2020/03/pomcp.pdf) samples plausible states and plans from observations. The practical first step here is much simpler: persist last-seen enemy locations with turn and uncertainty, then test plans against a small set of plausible enemy positions. Runtime AI must **never** pass the actual hidden `state` to `finish_turn` to choose its order. Offline testing may inspect the real state only to judge predictions after the fact. Enemy location memory belongs in the computer player's saved state, alongside the flank plan.

**Playtesting needs varied opponents.** [AlphaStar's league](https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/) used a population of agents to expose weaknesses missed by self-play against one policy. That scale is inappropriate here, but the principle is useful: a small roster of scripted styles (static defender, fast objective rush, deep raid, supply interdiction, cautious reserve, old Hard) can test whether a candidate simply exploits Standard. [Restricted-play balance research](https://ojs.aaai.org/index.php/AIIDE/article/view/12513) also supports purpose-built opponents for diagnosing strategic weaknesses. These sources motivate a test roster, not neural-network training.

## Recommended architecture

### 1. Persistent operational plan

At the beginning of each turn, create or revise a side-level plan from its **view**, scenario timetable and saved beliefs. Choose one principal aim and one contingency, for example relieve Tobruk, hold the frontier, cut a road, raid a rear objective, or rebuild the mobile reserve. Represent each mission with a target, deadline, committed formations, supporting HQ, staging hexes, supply budget, expected duration, withdrawal condition, and reason for revision. Keep the plan for several turns unless it becomes infeasible. Save it with the computer player. This is a bounded task planner, not a fixed opening script.

Calculate objective value from remaining turns, end points, casualties and terrain/port effects. Compare a raid with the value of keeping the same formations on the main front. A deep strike should be allowed to decline when its projected supply cost or likely counterattack outweighs its gain.

### 2. Supply and route forecast

Give each proposed mission a two- to three-turn logistics estimate. Use the map's haul costs, blocked paths from **known or plausible** enemies, HQ reach and `REACH_FULL`, vehicle fuel per hex, stores upkeep/combat, available lift, and the 300-tonne HQ carrying limit. Return a range (optimistic/pessimistic), not a false precise answer about unknown enemy moves. Require a survivable retreat or resupply route for a mobile raid. In particular, do not equate `traced` with adequately supplied.

### 3. Local tactical evaluator

At contact, generate a small set of legal orders for each relevant group: attack from available axes, concentrate a second formation, rest, dig, screen, bypass, or withdraw. Estimate combat value using the same unit type, cohesion, terrain, fort, command HQ and air rules as the engine, then apply the luck range and coarse enemy-strength uncertainty. Score **expected net victory points and future position**, including the loss of a formation or HQ. Use the real checker to reject invalid packages. Avoid omniscient exact battle simulation at runtime.

### 4. Enemy memory and reconnaissance

Record sightings with age and a widening set of reachable hexes. Reduce certainty when a counter leaves view; clear impossible locations when friendly units observe them empty. Estimate threats to objectives and supply corridors from those beliefs. Allocate recon when its information can alter an imminent mission decision; otherwise compare support and interdiction by expected combat and lift effects. A cheap belief model should precede POMCP or information-set search.

### 5. Controlled strategic variety

Generate several *credible* plans and choose among near-equal plans using a saved, computer-owned random stream or a stable per-game seed. The game weather seed is secret from players and should not be read from hidden state by the AI. Variation should change plans within a quality band, never force a suicidal move. Easy can consider fewer missions, Standard can use the new supply and tactical checks, and Hard can search more candidate packages or sample more enemy beliefs. All levels retain identical information and rules.

## Implementation order and decision gates

| Priority | Deliverable | Evidence required before proceeding |
| --- | --- | --- |
| 1 | A paired benchmark harness that compares old and new policies on identical scenario/weather seeds, both sides, and a roster of opponent styles. Log margin differences, objective-turn points, own unit VP lost, supply shortfalls, HQ dump losses, invalid orders, turn time and mission outcomes. | Reproduce the 1941 raid regression and retain old Hard as a frozen baseline. Use at least dozens of paired seeds for decisions; report the distribution and uncertainty, not only an average. |
| 2 | Tactical attack/hold/retreat evaluator and supply forecast. | Tactical cases cover favourable and unfavourable attacks, HQ support, ZOC traps and supply failure; paired matches show fewer avoidable formation losses without a material margin regression. |
| 3 | Persistent operational missions with formation/HQ assignments and re-planning. | Replays show a coherent aim across turns, respond to lost routes or an enemy counterstroke, and preserve the mission through save/load. |
| 4 | Enemy memory, reconnaissance value and varied plans. | No hidden-state leaks; varied but reproducible plans; scouting changes decisions in seeded fog-of-war cases. |
| 5 | Optional bounded search over mission packages. | Only retain it if paired results improve over the simpler planner at an acceptable per-turn CPU cost. |

The first implementation should be **benchmark + tactical/supply evaluation**, before adding more scripted manoeuvres or machine learning. The current code already contains enough rules to make better local decisions; it lacks a measurement loop that rejects attractive but costly plans. Neural training or a full information-set tree search would add substantial engineering and explainability cost before that simpler opportunity is exhausted.

**Implementation note, 30 October 2026:** The paired harness and an experimental local tactical evaluator are now in the repository. See [COMPUTER_BENCHMARK.md](COMPUTER_BENCHMARK.md) for commands and initial results. The evaluator stays outside playable difficulty levels because the multi-opponent matches found regressions. The harness also exposed a costly opening raid; playable Hard now checks the moving HQ's discarded dump stock before committing. The next work is a coordinated, supply-aware evaluation of attack versus holding ground over a whole turn.

## Suggested player-facing standard

A credible opponent should have a recognizable operational aim, preserve a reserve, support attacks with HQs and supply, scout uncertainty, exploit a weak flank when conditions justify it, and withdraw when a raid has spent its advantage. It should occasionally surprise a human, while a replay and optional post-game explanation can identify the plan and the information it used. Stronger difficulty should come from decisions and planning depth, never extra knowledge or altered combat rules.
