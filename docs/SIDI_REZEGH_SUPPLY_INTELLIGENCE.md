# Sidi Rezegh supply reconnaissance and raid check

1 November 2026. This is a mechanics and strategy check on the five-turn scenario, using the revised map and the ordinary rules in `docs/RULES.md` §§6, 7 and 14.

## What a Commonwealth commander can know

The map and ownership of Bardia, Derna and Benghazi are public. They are Axis ports at the start. A unit can spot enemy HQs, but cannot see their stock, whether they were supplied, their actual haul routes, or the Axis lift. A reconnaissance unit now reports a **local convoy sighting** if an enemy haul passed within two hexes during the current Supply phase. The sighting gives one hex only; repeated sightings at the same hex collapse. On the Supply layer enemy ports are marked as *possible* sources and local convoy sightings are marked separately. The exact source, destination, route and tonnage remain hidden. Air reconnaissance extends unit spotting of enemy forces; air interdiction reduces enemy lift in the following turn's Supply phase.

## Can one unit cut the line?

Yes, a unit's occupied hex and zone of control block an enemy supply path. The game recomputes hauls each Supply phase, so a move this turn changes delivery next turn. There is no single permanent Axis line: trucks may use another passable desert path, port or stored HQ dump. Taking Bardia denies that port as an Axis source and makes it a Commonwealth source, but it does not remove Derna, Benghazi or the Tripoli entry.

For a **counterfactual placement** at the opening of seed `1941`, moving Commonwealth reconnaissance unit 305 to `[66,13]` before the Supply phase reduced the haul to forward Axis HQ 101 from 2,000 tonnes to zero that phase. Axis hauls to other HQs were rerouted; this is a mechanical sensitivity check, not a legal opening move or a claim of total Axis starvation. A unit at `[56,12]`, the marked mission corridor's middle hex, did not cut the same forward HQ haul. The two objectives therefore demand different positions.

## Tested five-turn choices

Against playable Easy Axis on seeds `0`, `1`, `65`, `1941`, `2026`, forcing Hard Commonwealth's 4th Indian Division to attack Bardia captured the port in four of five games; forcing 1st Army Tank Brigade captured it in five of five; sending both also captured it in five of five. **All 15 games still ended in Axis mission victories.** In a traced seed `0` tank-brigade run, Bardia was captured only at the end of turn 4, too late to affect its earlier port hauls; the remaining Axis sources still served other HQs. These override policies were diagnostic only and are not the playable opponent.

In the 22-turn Crusader campaign, a prototype that added 150 objective weight to enemy ports kept three Commonwealth wins against Easy Axis (seeds `0`, `65`, `1941`), but its Commonwealth adjusted margins were `245`, `171`, `252`, versus `223`, `277`, `250` for the current Hard policy, and its shortage counts were higher in all three games. The simple port bonus was therefore **not adopted**.

## Strategic decision

For the five-turn Sidi Rezegh scenario, concentrate the main Commonwealth force on Sidi Rezegh, Belhamed and clearing the marked hexes. A Bardia raid is a valid operation and useful in a longer campaign, but the tested diversion sacrifices time and combat power without completing this short mission. Use observed convoy traffic and public port ownership to plan a supported raid when the game has enough turns for the supply effect to matter. A supply raid's success must be judged by its effect on the next Supply phase and the mission, not simply by reaching a road hex.

The current benchmark still has no Commonwealth win against Easy Axis in five sampled seeds. This report is evidence about the tested plans, not proof that a human win is impossible.
