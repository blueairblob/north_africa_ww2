# Historical simulation assessment

Assessment date: 1 November 2026. Scope: Operation Crusader and the five-turn
Sidi Rezegh scenario as currently implemented. Verdict: **playable operational
wargame with historical subject matter; not yet validated as a faithful
simulation of the November 1941 campaign.** This is a judgment about evidence
and calibration, not a claim that a particular outcome is impossible.

| Area | Present state | Confidence for historical simulation |
| --- | --- | --- |
| Sequence and objectives | The short scenario runs 18–27 November and judges a relief corridor, Sidi Rezegh and Belhamed. It captures the importance of a 27 November link. Ed Duda, where the historical junction occurred, is absent from the 10 km map and Belhamed stands in for it. | Moderate at operational scale; low at tactical scale. |
| Opening deployment | The German formation formerly stacked on Sidi Rezegh has been moved to the siege area, in line with the airfield's capture on 19 November. The replacement hexes and other unit positions remain broad approximations. | Partial verification only. See `SIDI_REZEGH_OPENING_POSITIONS.md`. |
| Order of battle and strengths | Formations are named, but many men and gun counts use establishment estimates; several tank allocations come from memory. Some strengths have no dated serviceable returns. | Low for quantitative comparison. See `SOURCES.md`. |
| Terrain and movement | Roads, rough ground, escarpments, passes and route costs affect movement. Sidi Rezegh and Belhamed coordinates are approximate, and 10 km hexes cannot resolve the airfield, Point 175, the mosque track and Ed Duda separately. | Useful operational abstraction; unvalidated tactical geography. See `MAP.md`. |
| Supply, attrition and combat | Fuel and stores are moved through routes, ports and HQs; shortages, losses and recovery have game effects. The combat and supply audit found those rules functioning in tested games. Opening stocks, lift, air effects and many combat constants are explicitly estimates or marked for tuning. | Functional rules; historical calibration incomplete. See `RULES.md` and `SIDI_REZEGH_COMBAT_SUPPLY_AUDIT.md`. |
| Air and weather | Each side chooses one air mission per turn; weather can stop air activity. There are no aircraft ranges, flight paths, heading, localized weather or sortie-level reconnaissance. | Deliberate strategic abstraction, not a close air operations simulation. |
| Outcome validation | After the deployment correction, Hard Commonwealth completed the short mission in 0/5 seeded games versus Easy Axis and 0/5 versus a passive Axis. Those are AI performance observations, not proof about a human player or the historical model. No documented replay with historically informed orders has yet shown the expected 27 November contact and subsequent vulnerabilities. | Not validated. See `SIDI_REZEGH_WINNABILITY.md`. |

## Evidence-based release threshold

Before calling the game a *historical simulation*, rather than a wargame
inspired by history:

1. Build a dated 18 November order of battle and position ledger with source,
   uncertainty and map hex for every formation. Prioritize Axis mobile groups,
   the Tobruk siege line, the Commonwealth corps and historical reinforcement
   and withdrawal dates. Use contemporary returns where available.
2. Validate the relief geography against period maps. Represent Ed Duda's role
   explicitly, or explain in the scenario that the 10 km map substitutes an
   operational corridor for the tactical junction.
3. Construct a **scripted historical replay** independent of computer AI.
   Check dated milestones: 19 November airfield capture, 21–23 November armoured
   battles, the 24 November Axis frontier counterstroke, 27 November contact,
   29 November loss of contact, and early December restoration and withdrawal.
   Record where the rules prevent or exaggerate those outcomes.
4. Calibrate movement, combat loss, recovery and supply constants against
   sourced ranges for several engagements and days, with uncertainty bands.
   Do not tune only to one final winner or to current AI behaviour.
5. Test multiple plausible human or scripted plans, including a successful
   relief, a failed relief and an Axis counterstroke. A credible simulation
   should make the historical path possible without forcing it, and should
   produce intelligible consequences when different decisions are made.

Historical anchors: Australian War Memorial, [Crusader Offensive](https://www.awm.gov.au/collection/E84737)
and Barton Maughan, [*Tobruk and El Alamein*, chapter 10](https://www.awm.gov.au/collection/C1417191);
W. E. Murphy, [*The Relief of Tobruk*](https://www.22battalion.org.nz/publications/histories/tobruk.pdf),
New Zealand official history.
