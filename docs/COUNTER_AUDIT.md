# Operation Crusader counter-art audit

The scenario has **91 ground units** and no aircraft units. A unit's side,
`nation`, `type` and optional `counter_art` selector determine its picture
(`screen/session.py`, `screen/draw.py`). The 26 rows below are **all** current
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
| cw | armour | matilda | 306, 307 | original painted Matilda II representative; 1st also had 8 RTR Valentines; Tobruk 32nd included 1 RTR cruiser tanks (unit-specific art hover notes) | Dated strength by regiment; illustrative Caunter-inspired pattern is not unit-verified |
| cw | armour | stuart | 311 | M3 Stuart; 4th Armoured Brigade | losses and replenishment by type and date |
| cw | foot | default | 308, 341, 342, 343, 351, 352, 353, 361, 362, 363 | Brodie-helmeted tropical riflemen | Polish, Indian, South African and Tobruk kit/uniform by brigade |
| cw | guns | default | 323, 334, 344, 354, 364 | 25-pounder field gun; 5 November 1941 Tobruk artillery return lists 64 25-pounders out of 104 field/medium guns, with other types (354 has art hover note) | batteries by division; 354 aggregates mixed Tobruk artillery but its scenario `guns: 72` is not this return |
| cw | hq | default | 301, 302, 303, 310, 320, 330, 340, 350, 360 | generic closed staff car | period make and national HQ fleets, not shown as established type |
| cw | motorised | default | 304, 314, 321, 322, 331, 332, 333 | Bedford OY-pattern lorry | unit-specific transport, including mixed support group 314 |
| cw | recon | carrier | 335 | open-topped carrier for NZ Divisional Cavalry | light-tank share and `cars: 30` abstraction |
| cw | recon | default | 305 | Marmon-Herrington-pattern car; a 1941 study identifies Mk III cars in KDG A/B squadrons (art hover note) | Other regiments within composite unit, precise mix and sprite Mk III silhouette |
| de | armour | default | 111, 121 | six-wheel Panzer III, not an exclusive type; a dated return cited for Regiment 5 (121) lists 35 Panzer II, 68 III, 17 IV (art hover note) | Regiment 8 (111) mixture and dated marks; 5th scenario `tanks: 116` differs from study’s 120, not changed in art pass |
| de | foot | default | 131, 132, 133 | tropical-field-cap riflemen | dated dress of regular and composite Afrika regiments |
| de | guns | antitank | 125 | Panzerjäger I, tracked 4.7 cm gun representative of 605 (art hover note) | 39 also had towed Pak; verify combined strength, losses and command assignment |
| de | guns | default | 106, 113, 123, 134 | 10.5 cm leFH 18 field howitzer | Boettcher, 33, 155 and Division Afrika mixed batteries |
| de | guns | flak88 | 104 | deployed 8.8 cm Flak representative of Halfaya | garrison's actual mixture; sprite does not imply all 36 guns were 88s |
| de | hq | default | 101, 110, 120, 130 | Kübelwagen with black pennant | exact HQ vehicles and pennant colour |
| de | motorised | default | 112, 122 | two-axle Opel Blitz-pattern lorry | 115/104 Schützen transport fleets |
| de | recon | default | 114, 124 | Sd.Kfz. 222 representative; 30 December 1941 table also lists 231/232 in both battalions (dated art hover notes) | 18 November model mix, origin of each unit’s abstract `cars: 30` |
| it | armour | default | 151 | unmarked M13/40-type tank | 132nd tank regiment marks and fleet proportions |
| it | foot | bersaglieri | 183 | feathered-helmet infantry; Italian Army records 7th Bersaglieri with Trento | November uniform/transport of its battalions |
| it | foot | default | 105, 141, 142, 171, 172, 181, 182, 191, 192, 201, 202 | M33-helmeted riflemen | Bardia garrison and ten line regiments' exact kit |
| it | guns | default | 143, 153, 164, 173, 184, 193, 203 | 75/27 field gun, not every battery's calibre | divisional mixtures, particularly Ariete, Trieste and mobile 173 |
| it | hq | default | 102, 103, 140, 150, 160, 170, 180, 190, 200 | generic tourer with Italian pennant | exact staff cars and pennant colour |
| it | motorised | bersaglieri_motorised | 152, 163 | Open unmarked lorry with feathered Bersaglieri riders; representative motor transport only | 9th included a motorcycle battalion; lorry and motorcycle proportions by regiment and date |
| it | motorised | default | 161, 162 | Lancia 3Ro-pattern lorry | 65th/66th fleet |
| it | recon | default | 107 | AB41 car; 2018 account identifies AB41s in its Gessi/Nizza components (art hover note) | dated inventory, archived photograph and AB41/L6/other-vehicle proportions |

## Aircraft are pooled, not counter units

The scenario stores each side's air **points**, not plane counts or named air
squadrons. The menu shows *examples* chosen from the RAF Museum's 18 November
1941 Crusader entry and documented Axis theatre types (`docs/SOURCES.md`):
Commonwealth Hurricane and Tomahawk fighters, Blenheim and Boston examples;
Axis Macchi C.200 and Bf 109 fighters, Ju 87 and Ju 88 examples, and a
Bf 110 reconnaissance example. A transcribed 23 November 1941 operations
report records Bf 110 reconnaissance sorties in the Crusader theatre
(`docs/SOURCES.md`); it does **not** identify the aircraft flown on
18 November or establish the exact fleet of the `2(H)/14` reconnaissance
Staffel listed in the compiled opening-day order of battle. Actual air-unit
counters would require an aircraft order of battle, not merely a new image.

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
