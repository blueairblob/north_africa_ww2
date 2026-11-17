# Tobruk to Beda Fomm: linked research chapters

**Status, 7 November 2026:** The Tobruk and western-pursuit portion of the Compass trial has seven contiguous chapters from 9 December 1940 through 9 February 1941, followed by linked Cyrenaica chapters through 11 April. These are playable continuations, not reviewed historical standalone starts. Their opening placements and owners in JSON are checker placeholders. A campaign handoff retains the actual played map, forces, losses, stocks and fortifications.

## Historical anchors

- [Australian official history, *To Benghazi*, chapter 9](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-9.html) describes Tobruk's preparation, the 6th Australian Division assault, and the Italian XXII Corps and 61st Sirte presence. Approximately 25,000 men and more than 200 guns are aggregate estimates; they cannot be mapped directly to individual game counters. The assault began on 21 January and Tobruk fell on 22 January.
- [Chapter 10, *The Engagement at Derna*](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-10.html) records the westward move beginning 22–23 January, armoured movement toward Mechili, the Derna rearguard, and Commonwealth entry into Derna on 30 January. Its discussion of the 60th Sabratha and Babini group includes contemporary intelligence estimates, not a complete dated strength return.
- [Chapter 11, *Beda Fomm and Benghazi*](https://www.ibiblio.org/hyperwar/UN/Australia/Bengazi/Benghazi-11.html) describes the Italian withdrawal detected on 3 February, the 7th Armoured Division's move from Mechili, the road block near Beda Fomm and surrender by the morning of 7 February. It also describes the Australian transport shortage: a brigade could be lifted at a time by collecting vehicles. That restriction is not yet in the game.

## Current abstractions and checks

The [Australian official history's Tobruk attack map and account](https://s3-ap-southeast-2.amazonaws.com/awm-media/collection/RCDIG1070231/document/5519529.PDF)
identify a planned breakthrough on the **southern** perimeter on 21 January,
followed by the 16th Brigade and then the 19th Brigade moving through the
opening toward different objectives. The map distinguishes the start line,
perimeter, interior gun positions and town. The account records artillery and
engineer preparation and **18 working infantry tanks** for that attack; this
is a serviceability count, not a new pool of replacement tanks. The source
supports a staged southern crossing and exploitation in the trial, but has not
been registered against the 10 km game grid. As at Bardia, capturing an empty
fort hex by movement would not model the crossing. The new intact perimeter
proxy at `[56,11]` requires a player-ordered supplied infantry Attack to
open; it remains closed if the played force cannot make that approach. The
stores threshold and coordinate are game estimates, and the rule does not
yet represent the historical engineer or artillery preparation. Check
Tobruk's perimeter and current counters together before changing combat
values.

Tobruk has a town fort and a southeastern-perimeter proxy one hex away. The model's 10 km hexes cannot resolve the actual ditch, individual posts, wire, minefield lanes, engineer crossings or naval and air preparation. The four Italian Tobruk counters have game-estimate strengths and have been present since the opening chapter. They are not introduced as a surprise reinforcement on 6 January.

The Derna chapter runs **23 January–2 February** daily; the Beda Fomm chapter runs **3–9 February** daily. Three western Axis counters enter the *modelled order of battle* on 23 January: 60th Sabratha near Derna, Babini armour near Mechili, and a provisional Benghazi security counter. This does **not** mean the formations historically arrived in Libya on that day. The model currently lacks a researched 9 December western roster; the entries prevent an empty western map in the pursuit. The Sabratha 6,000 men, Babini 60 tanks and Benghazi 2,000 men are research or game estimates, not verified strength returns. The security counter's exact formation identity is unresolved.

High Command orders are executable: reach Mechili and hold Derna, then reach Beda Fomm and hold Benghazi. Axis orders require physical occupation of Derna or Benghazi. Reaching Beda Fomm is a coarse marker for cutting the retreat; the current engine does **not** trap or surrender an army because a road hex has been reached. If the earlier assault fails, the actual Axis control can remain in place and the later chapters proceed as a counterfactual pursuit attempt.

The Hard-vs-Hard seed `1940` trace completes all seven chapters with checked invariants and leaves Bardia, Tobruk, Derna and Benghazi Axis-held. That is a continuity test, not evidence that the historical Commonwealth offensive is represented well or that a human cannot win. Before these chapters are promoted, check the Tobruk perimeter map, garrison returns and Australian serviceability; implement engineer, bombardment and surrender effects; verify Derna/Mechili positions and the Benghazi rear counter; represent transport limits; and test plausible outcomes for both sides.
