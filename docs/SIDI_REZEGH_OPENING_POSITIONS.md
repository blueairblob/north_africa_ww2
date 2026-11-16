# Sidi Rezegh opening positions: confidence audit

The playable Sidi Rezegh scenario begins on **18 November 1941** and inherits
the opening order of battle and positions from `data/scenarios/crusader.json`.
The battle around Sidi Rezegh developed over the following days. These dates
must not be combined into one static deployment.

## What the official account supports

Source: Barton Maughan, *Tobruk and El Alamein*, Australian official history,
chapter 10, pp. 442–446:
https://www.awm.gov.au/collection/C1417191

- **18 November:** the Eighth Army advanced with little opposition beyond light
  screening detachments. The map on p. 442 places Ariete at Bir el Gubi. This
  supports Ariete's broad opening area, not an exact game hex.
- **19 November:** 7th Armoured Brigade seized the Sidi Rezegh airfield and
  captured 19 Italian aircraft. The airfield was therefore not defended by the
  full German infantry formation represented in the game's Sidi Rezegh hex.
- **20–21 November:** after the British advance was reported, General
  Suemmermann ordered Division z.b.V. Afrika to face south. The 361st Infantry
  Regiment held ground east of the airfield around Point 175, the 155th held
  high ground south-west of it, and an artillery group with a Bologna infantry
  battalion protected ground near Belhamed. These were separated positions,
  not a single force occupying the airfield.
- **19–20 November:** the German panzer divisions were mobile. The account
  places 15th Panzer on the coast east of Tobruk before it was ordered to link
  with 21st Panzer. Their later concentration and movement must not be treated
  as fixed positions on the morning of the 18th.

## Correction applied to the 18 November setup

Both `crusader` and `sidi_rezegh` use the same opening deployment. The latter
inherits the former's units and forts. The correction places the German
formation around the Tobruk siege ring, keeping the airfield and Belhamed
without a starting Axis counter. It also removes the unsourced opening fort at
Belhamed. The map is coarse, so these are **broad area representations**, not
claims of exact wartime coordinates.

| Counter | Revised game hex | Evidence and limit |
| --- | --- | --- |
| Division z.b.V. Afrika HQ, III./255 und III./347, divisional artillery | `[56,11]` | A staging position on the Tobruk side of the Sidi Rezegh airfield; exact location not verified. |
| Infantry Regiment 155 | `[56,12]` | A southern screening position near the siege ring; the regiment's subsequent position south-west of the airfield was established after the British advance. |
| Afrika Regiment 361 | `[58,12]` | Eastern part of the ring; its subsequent Point 175 position was established after the British advance. |
| Artillery Group Boettcher | `[57,11]` | Near the Bologna front, off Belhamed; the exact 18 November artillery position and gun count remain unverified. |
| Ariete | Bir el Gubi | Retained. Consistent with the dated official map and the 19 November battle there. |
| 15th and 21st Panzer | Existing broad areas | Retained. The official account supports 15th Panzer east of Tobruk and describes both divisions moving, but does not certify the exact game hexes. |

The game's `data/features.json` marks both Sidi Rezegh and Belhamed as
approximate places. The map uses 10 km hexes, too coarse to place the airfield,
Point 175, nearby ridges and Belhamed precisely. `docs/SOURCES.md` also states
that many unit personnel and gun counts are establishment estimates, not
opening strength returns.

## Remaining verification

The New Zealand official history, W. E. Murphy, *The Relief of Tobruk*,
https://www.22battalion.org.nz/publications/histories/tobruk.pdf, corroborates
the limited opposition on 18 November and Ariete at Bir el Gubi. The exact
18 November regimental and artillery positions should still be cross-checked
against dated Axis war diaries and period tactical maps. Strength returns,
fortifications, the 15th and 21st Panzer hexes, and the Italian infantry
regiments around Tobruk also need separate checks. A 10 km hex cannot show
the airfield, Point 175, nearby ridges and Belhamed with tactical precision.
