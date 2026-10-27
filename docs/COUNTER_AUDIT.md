# Operation Crusader counter-art audit

The scenario has **91 ground units** and no aircraft units. A unit's side,
`nation`, `type` and optional `counter_art` selector determine its picture
(`screen/session.py`, `screen/draw.py`). The 25 rows below are **all** current
combinations; `tests/test_counters.py` checks that their IDs and selectors
match the scenario and that their assets exist. This is coverage of the
**depiction**, not proof that each unit's equipment is historically verified.
Dates, references, art origin and outstanding historical doubts belong in
`docs/SOURCES.md`, `docs/BOM.md` and the `art/art_required_*.md` briefs. Do not
infer exact tank/gun numbers, aircraft squadrons or national uniform from one
painted counter. Source-backed type examples still require unit-specific
formation inventories for a definitive portrayal.

`default` means `art/counters/artist/<nation>_<type>.png`; a named variant means
`art/counters/variants/<nation>_<variant>.png`. All rows apply to the 18
November 1941 Crusader scenario as currently encoded; later re-equipment can
change the historical mixture without changing the sprite.

| Nation | Type | Variant | Unit IDs | Current depiction / evidence | Outstanding unit-level check |
| --- | --- | --- | --- | --- | --- |
| cw | armour | a13 | 312 | A13 cruiser; Queen's Royal Hussars Museum says it made up roughly half of 7th Armoured Brigade | A10 and Crusader proportions and changes by date |
| cw | armour | default | 313 | Crusader cruiser; representative for 22nd Armoured Brigade | later Crusader/Stuart re-equipment by date |
| cw | armour | matilda | 306, 307 | Matilda II; mixed army-tank brigades | Valentine share in 1st, Tobruk garrison/32nd returns; old sprite's striped camouflage |
| cw | armour | stuart | 311 | M3 Stuart; 4th Armoured Brigade | losses and replenishment by type and date |
| cw | foot | default | 308, 341, 342, 343, 351, 352, 353, 361, 362, 363 | Brodie-helmeted tropical riflemen | Polish, Indian, South African and Tobruk kit/uniform by brigade |
| cw | guns | default | 323, 334, 344, 354, 364 | 25-pounder field gun; photographed at Tobruk in 1941 | batteries by division; mixed/captured Tobruk guns, especially 354 |
| cw | hq | default | 301, 302, 303, 310, 320, 330, 340, 350, 360 | generic closed staff car | period make and national HQ fleets, not shown as established type |
| cw | motorised | default | 304, 314, 321, 322, 331, 332, 333 | Bedford OY-pattern lorry | unit-specific transport, including mixed support group 314 |
| cw | recon | carrier | 335 | open-topped carrier for NZ Divisional Cavalry | light-tank share and `cars: 30` abstraction |
| cw | recon | default | 305 | provisional Marmon-Herrington-pattern car | composite armoured-car regiments and exact fleet |
| de | armour | default | 111, 121 | six-wheel Panzer III, not an exclusive type | mixed Panzer II/III/IV and mark proportions by regiment |
| de | foot | default | 131, 132, 133 | tropical-field-cap riflemen | dated dress of regular and composite Afrika regiments |
| de | guns | antitank | 125 | towed anti-tank gun, not an assault gun | calibres and combined 39/605 inventory |
| de | guns | default | 106, 113, 123, 134 | 10.5 cm leFH 18 field howitzer | Boettcher, 33, 155 and Division Afrika mixed batteries |
| de | guns | flak88 | 104 | deployed 8.8 cm Flak representative of Halfaya | garrison's actual mixture; sprite does not imply all 36 guns were 88s |
| de | hq | default | 101, 110, 120, 130 | Kübelwagen with black pennant | exact HQ vehicles and pennant colour |
| de | motorised | default | 112, 122 | two-axle Opel Blitz-pattern lorry | 115/104 Schützen transport fleets |
| de | recon | default | 114, 124 | provisional Sd.Kfz. 222-pattern car | 33/3 reconnaissance battalion vehicle mix |
| it | armour | default | 151 | unmarked M13/40-type tank | 132nd tank regiment marks and fleet proportions |
| it | foot | bersaglieri | 183 | feathered-helmet infantry; Italian Army records 7th Bersaglieri with Trento | November uniform/transport of its battalions |
| it | foot | default | 105, 141, 142, 171, 172, 181, 182, 191, 192, 201, 202 | M33-helmeted riflemen | Bardia garrison and ten line regiments' exact kit |
| it | guns | default | 143, 153, 164, 173, 184, 193, 203 | 75/27 field gun, not every battery's calibre | divisional mixtures, particularly Ariete, Trieste and mobile 173 |
| it | hq | default | 102, 103, 140, 150, 160, 170, 180, 190, 200 | generic tourer with Italian pennant | exact staff cars and pennant colour |
| it | motorised | default | 152, 161, 162, 163 | Lancia 3Ro-pattern lorry | 8th and 9th Bersaglieri identity/transport; 65th/66th fleet |
| it | recon | default | 107 | provisional AB41 candidate for mixed RECAM | archived photograph and AB41/L6/other-vehicle proportions |

## Aircraft are pooled, not counter units

The scenario stores each side's air **points**, not plane counts or named air
squadrons. The menu shows *examples* chosen from the RAF Museum's 18 November
1941 Crusader entry and documented Axis theatre types (`docs/SOURCES.md`):
Commonwealth Hurricane, Blenheim, Boston; Axis Macchi C.200, Ju 87, Ju 88.
An **anonymous** Axis reconnaissance icon avoids an unsupported precise type.
The compiled 18 November Axis order of battle lists `2(H)/14` as a
reconnaissance Staffel, and a 2021 historical study describes its
reconnaissance on 19 November. An Hs 126 is an army-cooperation candidate,
but these records do not identify that day's aircraft. A dated unit return is needed before
replacing the icon with an identified model; actual air-unit counters would
require an aircraft order of battle, not merely a new image.

## Priorities from this audit

1. Establish **dated unit inventories** for mixed armour, artillery and
   reconnaissance rather than treating a representative sprite as proof of
   exclusive equipment.
2. Verify aircraft squadrons, roles and dates, especially Axis reconnaissance,
   before assigning any aircraft to a unit or turn. Do not equate air points to
   aircraft counts.
3. Check the Polish/Indian/South African and Bersaglieri uniforms and the
   mobile regiments' vehicles; add variants where a difference remains visible
   at the opening zoom.
4. Resolve the historical and commercial provenance gaps in `docs/TODO.md`
   before declaring the set complete.
