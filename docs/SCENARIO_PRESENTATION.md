# Scenario presentation and strategic assumptions

The private Desert Rats port showed a useful *structure*: several episodes of a larger campaign, a concise setup choice before play, a strategic Mediterranean assumption separate from the battle, and a debrief that can lead into a later episode. Benghazi Handicap uses that structure as design guidance only. No original game text, code, map, unit data, art, or numerical settings are reused; see [CLEAN_ROOM.md](CLEAN_ROOM.md).

## Available now

- **Sidi Rezegh**, 18–27 November 1941, five two-day turns: a short operational episode with executable relief and blockade orders.
- **Operation Crusader**, 18 November–30 December 1941, 22 two-day turns: the longer campaign on the same map and opening order of battle.
- Setup shows the period, duration, each side's High Command aim, and player selection. The Malta/sea setting is a separate choice. CLI launches can use `--shipping baseline|less_interdiction|more_interdiction`.
- The baseline uses the scenario's current Axis `sea_pct` schedule, already marked as an estimate in the scenario data. The two experimental choices add or subtract **15 percentage points** from that schedule, clamped to 0–100. This is a sensitivity control for aggregate shipping loss, not an isolated Malta effect or a simulation of Operation Herkules. It changes no air or land forces. The choice is embedded in saves and variant autosaves have distinct names.

## Next scenario work

The owner has confirmed the larger September 1940–November 1942 campaign as the direction. The chapter sequence, continuity work and acceptance checks are in [CAMPAIGN_ROADMAP.md](CAMPAIGN_ROADMAP.md). Create additional dated episodes only after their opening dispositions, arrivals, objectives, supply and plausible victory conditions are verified. Do not split the current Crusader state at an arbitrary turn and call the result a historical opening position.

A checked core handoff now carries a finished chapter's surviving formations, losses, place control and stockpiles into an immediately following chapter while adding newly introduced formations. It retains a chapter-result history and saves separately from a standalone battle. The catalog marks all unresearched periods as unavailable. There is not yet a second historically prepared chapter, a gap resolver or a campaign screen, so the continuous campaign cannot be started from the review menu. Standalone historical starts remain separate.

## Movement calibration still needed

The modeled road and track costs give vehicles 2 and 3 MP per hex on Travel, against 4 MP per hex for ordinary movement; foot Travel costs 3 and 4 MP. The AI formerly almost never issued Travel because it marked any enemy-held destination as Attack, even from far away. It now uses safe road approach legs before attacking. This fixes the order-selection gap, but does not validate real distance covered in two days. The hex scale, road geometry, unit allowances, weather and fuel rates need a separate historical movement calibration against documented marches.

At the map's 10 km per hex, a 32 MP armour formation can cover up to 80 km by ordinary movement or 160 km by road Travel in a clear two-day turn, before terrain, contact, fuel and traffic intervene. A 40 MP motorised formation can cover up to 100 or 200 km respectively. These are game ceilings, not observed divisional marches. Full computer games on seed 1941 issued six Axis Travel orders in the five-turn Sidi Rezegh episode, and six Axis plus one Commonwealth Travel order over the 22-turn Crusader campaign. Many Commonwealth opening formations are off road, and their modeled road detour is often longer than a direct desert route.

The [US Army's official North Africa account](https://history.army.mil/portals/143/Images/Publications/catalog/72-13.pdf) describes infantry following the coastal road while mechanized forces maneuvered in open desert. The [British commander's published Crusader dispatch](https://www.ibiblio.org/hyperwar/UN/UK/LondonGazette/38177.pdf) describes New Zealand troops advancing along the Trigh Capuzzo toward Point 175. These support route use as an option for some formations and desert movement for others; they do not establish the current 2:1 MP ratio or any unit's two-day allowance.
