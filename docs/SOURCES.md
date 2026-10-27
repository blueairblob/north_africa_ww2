# Sources

What the map and the orders of battle are built from. Facts (dates, places,
which formations fought where, their size and equipment) are not owned by
anyone; the *wording, selection and layout* of a particular book or website can
be. So: use several sources, record the facts in our own data format, and list
the sources here. Check each licence before using a dataset.

## Geography (the map generator's inputs)

| Data | Source | Licence | Used for |
| --- | --- | --- | --- |
| Coastline, land/sea | Natural Earth (naturalearthdata.com), 1:10m physical | public domain | the coast, sea hexes |
| Elevation | Terrain Tiles (the Mapzen "terrarium" tiles hosted as an AWS Open Data set), zoom 9, about 260 m per pixel; built from SRTM and other open elevation data | open data, **attribution required** (see below) | escarpments (steep drops across hex edges), rough ground, the Qattara Depression |
| Libya–Egypt frontier | Natural Earth, 1:10m boundary lines | public domain | the frontier line (the Wire) |
| Sand seas, depressions, oases | Natural Earth physical labels; outlines traced from public-domain period maps | public domain | impassable terrain; water |
| Roads, tracks, towns | U.S. Army Map Service / War Office 1940s survey sheets of Libya and Egypt (scans at e.g. the Perry–Castañeda Library, University of Texas — check each sheet's status) | public domain where published by the U.S. government; check others | the coast road, desert tracks, period place names, railway |
| Modern cross-check | OpenStreetMap | ODbL — **requires attribution**; a hex map produced from it is a "produced work" (attribution needed) | positions of towns and roads |

Attribution for the elevation data, as its publishers ask: *Terrain Tiles: data from
SRTM (NASA/USGS), GMTED2010 (USGS/NGA), ETOPO1 (NOAA) and other open sources,
assembled by Mapzen and hosted by Amazon Web Services Open Data.* Place coordinates
were cross-checked against OpenStreetMap (© OpenStreetMap contributors, ODbL).

Period maps used as a check on places and tracks (positions and names only;
the maps are not reproduced here): a map of Rommel's plan of attack at Gazala,
May 1942, from a history published in 1954; "Cyrenaica in March 1941" (Map 2
of a history published in 1956), for the edge of the Libyan Sand Sea and for
names; and "Diagram showing the lines of
advance of General Rommel's columns through Cyrenaica in April 1941" (Map 4 of
a published history, probably the same 1956 volume — to be confirmed). Two modern maps of Operation Compass (one a vector map, apparently from
Wikimedia Commons; one from a printed atlas) were used the same way, for the
Italian camps, the approach routes and the oases. A general map of the campaign
on the Desert Rats Association website was the model for the *look* of
`map.png` (relief shading, region names, the frontier), and the 1956 map for
its border and title block; nothing was copied from either.

Railway: the Western Desert Railway's westward extension (railhead dates) from
the official histories below.

## History (orders of battle, dates, positions)

| Source | Notes |
| --- | --- |
| *The Mediterranean and Middle East*, Vols I–IV (UK official history, Playfair et al., 1954–66) | the standard British account; orders of battle and dates. Check the current copyright status before reproducing any text or maps; the facts may be used. |
| Official histories of Australia, New Zealand, South Africa and India in the Second World War | detailed divisional histories; several are freely available online from their governments (check each) |
| U.S. Army publications on the North African campaign | U.S. government works are public domain |
| Wikipedia articles on each operation and their order-of-battle pages | convenient cross-checks; CC BY-SA text — use the facts, not the text |
| German and Italian official and divisional histories | for the Axis side |

Logistics figures (port capacities, consumption, truck haulage) to calibrate
`DESIGN.md` §6: the official histories above and the standard studies of
desert logistics — take the facts and set our own values.

Used for the supply constants in `docs/RULES.md` §6.12 (facts only, each
marked there):

| Source | Used for |
| --- | --- |
| M. van Creveld, *Supplying War* (1977), ch. 6, as quoted in the Wikipedia articles "Western Desert campaign" and "Operation Crusader" (CC BY-SA; facts only) | Tripoli's capacity; Tobruk's; a motorised division's 350 tons a day; lorries needed over 300 miles; fuel used by road transport; road distances |
| "Capacity of Tripoli and Benghazi Harbours, 1941", rommelsriposte.com (a research note quoting Italian naval staff returns) | tons actually unloaded at Tripoli and Benghazi, May–August 1941; the doubt about van Creveld's figure for Benghazi |
| *New Zealand Engineers, Middle East* (NZ official history), ch. 9, "The Western Desert Railway" (NZ Electronic Text Collection) | railhead dates, 1941–42 |

Not yet read at first hand: van Creveld and Playfair themselves.

Used for the strengths in `data/scenarios/crusader.json` (each unit carries a
source letter, explained in the file's `sources`):

| Source | Used for |
| --- | --- |
| Wikipedia, "Operation Crusader" and "Operation Crusader order of battle" (CC BY-SA; facts only) | the formations and their regiments and brigades; 7th Armoured Brigade's 129 tanks |
| historyofwar.org, "Operation Crusader, 18 November-20 December 1941" | 4th Armoured Brigade 166 Stuarts; 22nd Armoured Brigade 155; 1st Army Tank Brigade about 130; 249 German and 189 Italian medium tanks in all |

Not sourced: the men and guns of every unit are worked out from its
establishment (about 800 men to a battalion), not taken from a strength
return; the split of the German tanks between the two panzer regiments,
Ariete's share of the Italian tanks and 32nd Army Tank Brigade's strength are
from memory. All are marked in the scenario file, except for the separately cited Panzerregiment 5
research lead below; its scenario figure is not yet updated.

## The enemy's strength, and the weight of an HQ (RULES 14.4, 14.6, 10.4.5)

Read at first hand on 19 October 2026 in W. E. Murphy, *The Relief of
Tobruk* (New Zealand official history, 1961), from the PDF published by the
22nd Battalion association (22battalion.org.nz), searched as text. Chapter
numbers are the book's; page numbers are not given because the PDF's are not
the book's.

| Claim the rules rest on | What Murphy says | Where |
| --- | --- | --- |
| The British over-counted the German tanks knocked out | "the achievements of the British armour were shortly to be exaggerated, partly through overlapping reports" | ch. 6 |
| ... and acted on it | "Over-estimates of enemy tank losses made 4 and 22 Armoured Brigades only too ready to see the sudden disengagement of Africa Corps at Bir Gibni as a retreat"; later, "gross over-estimates of enemy tank losses, which remained uncorrected" | ch. 7 |
| The Germans misread British strength too | the British "superabundance (by Axis standards) of transport" gave "an exaggerated picture of British strength"; "German battle reports tend to over-estimate opposition" | chs. 7, 10 |
| ... and took the British as beaten on 23 November | 15th Panzer Division's diary for that evening claims "over 100 tanks destroyed"; Murphy: if its view "was correct there could not possibly be any sizable British forces left" | ch. 12 |
| The side holding the field got back what lay on it | 15th Panzer "planned to reorganise his forces next day and salvage the huge amount of equipment which now lay at his disposal"; Light Recovery Sections of the British armour repaired damaged tanks behind the line | chs. 12, 17 |
| An attack needs concentration and one command behind it | the Crusader plan was criticised as a "licence to ignore the principle of concentration of force"; the Jock Columns "needed some way of concentrating quickly under unified command ... and no such way was provided"; 21st Panzer was "committed piecemeal, largely without his knowledge" | chs. 4, 17, 19 |

Not found in Murphy, and so not used: that British artillery was centralised
under division and corps in 1942. The plan's note that the effect of an HQ
might differ by side and date rests on that, so the rules give both sides the
same `HQ_PCT`. Its size is not from any source.

## Luck in battle (RULES 10.4.7)

The owner asked on 19 October 2026 what share of a battle's result should be
luck, with 10 per cent as his guess, and named a role-playing game's combat
as an example of luck. That game was taken as background only (clean-room
rule); no number from it is used. Read at second hand, on the web, that day:

| Source | What it gives |
| --- | --- |
| The Dupuy Institute, "Validating Trevor Dupuy's Combat Models" (2017), on T. N. Dupuy, *Numbers, Predictions and War* (1979) | the QJM, a model fitted to historical battles, matched the outcome in 93 per cent of 81 engagements; in a later test of four outputs, about 85 per cent for success or failure, "40% or less" error in personnel casualties, 15 per cent in rates of advance |
| The Dupuy Institute, "AI and the 3-to-1 rule" (2026) | "wide variation in outcomes at all force ratios" in its data |
| M. Rotte and C. Schmidt, "On the production of victory", *Defence and Peace Economics* 14 (2003), abstract only | numerical superiority and the human factors (leadership, morale, surprise) both remain strong determinants of battle outcome, 1600 to 1973 |

What this gives: what the best model leaves unexplained is chance and every
unmeasured factor together, so it is a ceiling on luck, not a measure of it.
No source was found that separates luck from the rest. 10 per cent on the
attack is the owner's figure and is under that ceiling; it is marked to be
tuned. That a single uniform draw spreads results evenly, and that the sum of
two bunches them, is arithmetic, not a source.

## Dated events (arrivals, withdrawals, replacements)

Looked up on 8 October 2026 for `data/scenarios/crusader.json`. Each event in
the scenario carries the letter of its source (`docs/RULES.md` 12.7). Murphy's
*The Relief of Tobruk* (New Zealand official history, 1961) was read at first
hand, in the New Zealand Electronic Text Collection's edition; the others at
second hand, through the pages named. Chapter numbers are given for Murphy
because the electronic edition's pages are not those of the printed book.

Used:

| Date | Event | Source | How sure |
| --- | --- | --- | --- |
| 27 November 1941 | 7th Armoured Brigade leaves the battle | R. Palmer, *7 Armoured Division (1941-42)*, britishmilitaryhistory.co.uk (2020), note 6: "the surviving details of the brigade came under command of G.H.Q. Middle East Forces". Murphy ch. 7 and 10: 28 tanks left of 160-odd on 21 November, 10 or none on the 23rd | the date from one modern compilation; the wreck of the brigade from the official history |
| 27 November 1941 | 4th Armoured Brigade: 33 tanks | Murphy ch. 17: "4 Armoured Brigade, the latter with 37 tanks" on the night of 24 November; ch. 20: on the 27th "4 Armoured Brigade (with nearly seventy Stuarts)" | the two strengths are stated; the 33 is their difference. How many were new and how many repaired or rejoined is not stated |
| 1 December 1941 | 2nd New Zealand Division goes back to Egypt: its HQ, 4th and 6th Brigades and the field regiments | Murphy ch. 24: the column formed at 5.30 p.m. on 1 December, "3500 men and 700 vehicles"; ch. 25: "the rest of the New Zealand Division (other than 5 Brigade) had returned to Baggush" | stated. 5th Brigade and the Divisional Cavalry stayed and are left on the map |
| 2 December 1941 | 2nd South African Division comes up | Wikipedia, "2nd South African Infantry Division": it "took over responsibility for the Frontier area on 2 December 1941", having guarded the railway and the coast between Alexandria and Mersa Matruh | the date at second hand. That it enters at Buq Buq is this game's choice; whether all three brigades came on the one day was not found |
| 6 December 1941 | 4th Armoured Brigade: 38 tanks | Murphy ch. 25: "The tank strength of 4 Armoured Brigade on 4 December was 98; on the 6th it was 136", after "Weapons and equipment were similarly renewed" | the two strengths are stated; the 38 is their difference |
| 19 December 1941 | Panzer-Regiment 8: 22 tanks, through Benghazi | rommelsriposte.com, "German tank deliveries" pages, from shipping returns: 5 Panzer II and 17 Panzer III for 3./Pz.Rgt. 8, landed at Benghazi from the *Ankara* | the landing at second hand. That the tanks were with the regiment within the turn is assumed. historyofwar.org gives "fifteen new tanks" for 15. Panzer-Division on 19 December: the two do not agree |
| 22 December 1941 | 22nd Armoured Brigade: 60 tanks | Wikipedia, "22nd Armoured Brigade (United Kingdom)", citing Joslen pp. 168-9: by 22 December "80 Crusaders" and "30 M3 Stuart"; Murphy: fewer than 50 tanks in a composite regiment on 27 November | 110 on the day is stated; its strength just before was not found, so 60 is the least it can have been sent |
| 27 December 1941 | Panzer-Regiment 8: 23 tanks | the same pages: 6 Panzer II and 17 Panzer III for 7./Pz.Rgt. 8, landed at Tripoli on 19 December (the ship is named differently in two summaries). Murphy ch. 26: the Afrika Korps "with 70 tanks" struck 22nd Armoured Brigade after 27 December; Wikipedia, "Operation Crusader", citing Murphy p. 501: eight tanks fit on the 15th | the landing is dated; **the day the tanks reached the regiment was not found** and is taken as the 27th from the strength on the 28th |

For `data/scenarios/sidi_rezegh.json`, looked up on 10 October 2026. The
scenario is Crusader's first five turns, so it has Crusader's start; these
dates are why it ends where it does. Murphy was read at first hand again,
this time in a copy of the book on 22battalion.org.nz; the others are at
second hand.

| Date | Event | Source | How sure |
| --- | --- | --- | --- |
| 18 November 1941 | Eighth Army crosses the frontier | Wikipedia, "Operation Crusader": "Before dawn on 18 November, the Eighth Army advanced westwards"; historyofwar.org, "Operation Crusader" | two pages at second hand, which agree |
| 19 November 1941 | 7th Armoured Brigade takes the airfield at Sidi Rezegh | historyofwar.org: "capturing the airfield at Sidi Rezegh intact"; Wikipedia | the same two pages |
| 21 November 1941 | the garrison of Tobruk breaks out towards Ed Duda | Wikipedia: "The 70th Infantry Division was to break out from Tobruk on 21 November"; historyofwar.org | the same two pages |
| 23 November 1941 | Totensonntag: the armour's battle south of Sidi Rezegh | both pages; Murphy ch. 10 is named for it | the day is not in doubt |
| 24 November 1941 | Rommel's armour leaves for the frontier | historyofwar.org: "The 'dash to the wire' began at around midday on 24 November"; Wikipedia | the same two pages |
| dawn, 26 November 1941 | 4th New Zealand Brigade is on Belhamed | Murphy ch. 15: "Dawn of 26 November was unwelcome on the bald top of Belhamed" | stated. The hour it was taken, in the night before, was not read |
| night of 26 to 27 November 1941 | the New Zealand Division joins the garrison of Tobruk at Ed Duda: 44th Royal Tank Regiment and 19th Battalion | Murphy ch. 15: "At 9.30 p.m. the first wave of tanks drove off and a quarter of an hour later 19 Battalion set out"; "By 4 a.m. on 27 November the line was complete and Brennan reported that 19 Battalion was on Ed Duda". Ch. 16: Scobie at 2.30 p.m. on the 27th, "Corridor is open" | stated, at first hand |
| morning, 27 November 1941 | Sidi Rezegh is in 6th New Zealand Brigade's hands after a night attack | Murphy ch. 16, of the morning of the 27th: "Sidi Rezegh was ours" | stated. The hour was not read |
| 27 November 1941 | the Afrika Korps is ordered back to Tobruk | Murphy ch. 18: "Africa Corps had to return to the Tobruk front this day, 27 November" | stated. historyofwar.org has "By 28 November": a day apart |

So the scenario ends on the evening of 27 November, its fifth turn: the road
into Tobruk stood open that day, and the armour that would shut it had only
been ordered back. When it was shut again is outside the scenario and the
pages read do not agree: 1 December (Wikipedia, historyofwar.org) or 29
November (rommelsriposte.com, "So when did the siege of Tobruk end?").

Ed Duda, where the two forces met, is not a place on this game's map.
Belhamed, beside it, stands for the join. That is this game's choice.

Found and not used, each for the reason given:

- **Italian tanks.** The *Fabio Filzi* landed 10 M13/40 at Tripoli on 23
  November and the *Sebastiano Venier* 14 at Benghazi on 1 December (the
  Italian Navy's official history, vol. VIII, as given on rommelsriposte.com).
  Which regiment received them, and when, was not found.
- **4th Armoured Brigade's relief.** An Axis intelligence summary of 28
  December says it "has been relieved a few days ago". No date was found.
- **5th New Zealand Brigade** was told on 18 December that it would go back
  "as soon as other transport became available" (Murphy ch. 26). No date was
  found. The Divisional Cavalry left on 6 January 1942, after the scenario.
- **The amalgamation of the armoured brigades.** 22nd Armoured Brigade's
  composite regiment and 4th Armoured Brigade fought as one brigade from the
  night of 29 November (Murphy ch. 23). The game keeps them as two units.
- **7th Armoured Division's relief** by 1st Armoured Division, 1 January 1942
  (Palmer), and 2nd Armoured Brigade's arrival on 4 January (Murphy): after
  the scenario's last day.
- **Division z.b.V. Afrika** was renamed 90. leichte Afrika-Division during
  the battle. A change of name only; the date is from memory and unchecked.

Two of the withdrawals were the result of the fighting and not of a plan made
beforehand: 7th Armoured Brigade and the New Zealand Division left because
they had been wrecked. The game takes them off on the historical day whatever
state the player has kept them in. That is a decision of the owner's
("replacements: fixed historical", 7 October 2026) which he may wish to look
at again for these two.

Not found at all: how many replacement tanks Eighth Army issued in the whole
battle, and any dated replacement of men or guns for either side.

## Art

Generated for this game: hex terrain tiles drawn from the terrain types, and
unit symbols drawn from NATO military symbology (APP-6 / MIL-STD-2525, public
standards). No art from any other game.

The counter pictures in `art/counters/artist/`, cut from
`art/counters_sheet_1.png`, `art/counters_sheet_1_1.png` and
`art/WWII Desert Kübelwagen Icon.png` (no longer used) and the two cars in
`art/axis_hq_cars/` (added 20 October 2026): generated by an AI image tool for this
game, the owner said on 19 October 2026, and under no copyright. The tool and
its terms are not recorded. The briefs for the pictures still to come are
`art/art_required_*.md`.

The British/Commonwealth HQ staff-car sprite `art/counters/artist/cw_hq.png`
was generated for this project with OpenAI image generation on 24 October 2026,
using this game's British lorry and German HQ counter art as style references.
It was fitted to the game's 480 × 288 transparent counter canvas with the
existing `countergen.cut.fitted` routine. It depicts a generic period closed
staff car, not an identified or historically verified make or model.

## Counter and air-control visual sources (26 October 2026)

The Tank Museum documents the Cruiser Mk VI Crusader and its five large road
wheels in North Africa in 1941: https://tankmuseum.org/article/crusader-first-action/ .
A contemporary tank return discussed in *Scientia Militaria* 49(1), 2021,
pp. 95 ff. (using TNA WO 169/952 and WO 201/520) lists British cruisers,
M3 Stuarts, Matildas and Valentines at the outset of Crusader:
https://www.ajol.info/index.php/smsajms/article/download/217929/205533 .
The existing scenario sources name 4th Armoured's Stuarts and 22nd Armoured's
later mixed Crusaders and Stuarts. The 1st and 32nd Army Tank Brigades were
mixed formations; the Matilda is a representative, **not** their entire kit.
Bryan Perrett, *British Tanks in N. Africa 1940–42*, "The Tank Brigades",
identifies 8 RTR (1st Army Tank Brigade) with Valentines, 42 and 44 RTR
with Matildas; in 32nd Army Tank Brigade at Tobruk, 1 RTR had cruiser tanks
while 4 RTR and a squadron of 7 RTR had infantry tanks:
https://cartalana.com/026-04.php . A separate historical equipment
reconstruction, "Matilda Operation Crusader 1941", estimates 68 Matildas
and 28 cruisers plus light tanks within the Tobruk garrison brigade, but
these are *not* a verified brigade return and must not replace scenario
strengths: https://mikesresearch.com/2018/10/28/matilda-operation-crusader-1941/ .
The in-game picture hover notes for 306 and 307 describe composition, not
precise shares.

An online transcription of the Commander Royal Artillery Tobruk Fortress
war diary's **5 November 1941** order of battle records 64 25-pounders
out of 104 field and medium guns, plus 18-pounders, 4.5-inch howitzers and
guns, 60-pounders, and captured Italian 75/100/149 mm guns:
https://rommelsriposte.com/2014/05/08/ . The transcription explicitly
places some of those guns with the Polish brigade and Fortress command, so
it cannot establish 70th Division artillery unit 354's *own* 72-gun count.
The 25-pounder remains a representative icon; verify boundaries and dated
strengths against original war diaries before modifying the scenario.

A 2021 *Scientia Militaria* analysis by Andreas Biermann, drawing on German
formation and tank returns for **17–19 November 1941**, lists Panzerregiment
5 as 35 Panzer II, 68 Panzer III and 17 Panzer IV. Panzer III is therefore
a majority **representative**, not the whole regiment. Its 120 total
differs from scenario unit 121's unverified `tanks: 116`; do not change
strength or balance until the return's operational/allocated basis and
scenario interpretation have been reconciled. The same study identifies
A/B squadrons of the King's Dragoon Guards with South African-built
Marmon-Herrington Mk III armoured cars. This establishes a component of
composite unit 305, not its entire fleet or that the painted generic car
matches the exact Mk III chassis; its picture remains a candidate:
https://rommelsriposte.com/wp-content/uploads/2021/06/1319-article-text-3524-1-10-20210603.pdf .


The new 480 × 288 Commonwealth Crusader and Stuart sprites were generated
specifically for this project with OpenAI image generation on 26 October
2026, using only the project's own lorry, HQ and newly generated Crusader
art as style references. Their alpha-bounded silhouettes were fitted to the
existing counter canvas using `countergen.cut.fitted`; no external pictures
were traced or copied. The old Matilda sheet cut was later replaced with an original painted
variant (27 October 2026; see next paragraph). The Stuart was regenerated
once to make its four-wheel suspension and compact turret more distinct.
The Matilda II variant used for 1st and 32nd Army Tank Brigades was generated
with OpenAI image generation on **27 October 2026**, using only this game's
previous Matilda counter as a shape reference and its original Crusader
painting as a style reference. The selected new alpha image was trimmed and
fitted with `countergen.cut.fitted`, with no photograph traced or bundled.
The Tank Museum displays a restored Matilda II painted in a Caunter scheme;
this establishes the scheme as plausible Matilda *type-level* inspiration,
not the exact 18 November 1941 colours, stripe geometry or paintwork of
8/42/44 RTR or Tobruk's 1/4/7 RTR:
https://tankmuseum.org/tank-nuts/tank-collection/matilda-ii .
The three-tone pattern in `cw_matilda.png` is deliberately illustrative.
It must not be read as a documentary reconstruction of either brigade.

The Queen's Royal Hussars Museum's armoured-vehicle history reports that
A13 cruisers counted for roughly half of the 7th Armoured Brigade in
Operation Crusader, so the 7th now has a separate representative A13 sprite
instead of inheriting the Crusader of 22nd Armoured:
https://www.qrhmuseum.com/research/armoured-fighting-vehicles .
The National Army Museum describes the A13 Mark II/Cruiser Mk IV's extra
angled turret armour, and The Tank Museum identifies its distinctive large
Christie-suspension wheels:
https://collection.nam.ac.uk/detail.php?acc=1975-03-63-1-314 and
https://tankmuseum.org/tank-nuts/tank-collection/tank-cruiser-mark-iii-a13 .
The `cw_a13.png` variant was generated for this game with OpenAI image
generation on 26 October 2026. An initial candidate had an unusable vignette;
the selected second candidate has real transparency and was alpha-trimmed
and fitted using `countergen.cut.fitted`. The museum texts were used for the
vehicle's type and silhouette only: no photograph was traced, copied or
bundled. This remains one representative for a mixed brigade, not a claim
that every vehicle was an A13.
The replacement 25-pounder illustration is an original generation of
26 October 2026, matched to this game's lorry art, not copied from a photo.
An Australian War Memorial record photographs a 25-pounder in Tobruk on
16 October 1941 (accession 020970):
https://www.awm.gov.au/collection/C5312 . The steel-wheeled carriage, shield
and turntable identify the subject; this pictogram is not a scale drawing.

A 1991 Italian defence-history conference report, published by Italy's
Ministry of Defence, describes RECAM as including an armoured-car and L6
company in the 1941 Corpo d'Armata di Manovra but gives no car model:
https://www.difesa.it/assets/allegati/39410/02_convegno1991_italia_in_guerra_secondo_anno1941.pdf .
Fabio Fabbricatore, "Trasporti in divisa", *Rivista Italiana di Sanita
Militare* 75 (July-September 2018), p. 23 (PDF p. 24), identifies the
"Romolo Gessi" PAI battalion and an experimental "Nizza" cavalry platoon
as AB41-equipped contributors to RECAM from September 1941:
https://www.ansmi-presidenzanazionale.it/wp-content/uploads/2021/01/RISM-n.-75.pdf .
This is a published retrospective account, **not** an original dated
vehicle return. It supports the pictured AB41 as a documented example,
not all vehicles or the scenario's abstract `cars: 45`; the full mix and
strength on 18 November remain unresolved. The Ministry history also
mentions L6 light tanks but does not establish their arrival by 18 November.
A secondary AB41 account cites a November 1941 Sidi Rezegh photograph
attributed to the Archivio Centrale dello Stato depicting several AB41s and
an Autoblindo TL37 in RECAM. The original catalogue/photo has not been
verified; do not infer all RECAM equipment from this report:
https://tanks-encyclopedia.com/ww2/italy/autoblinda-ab41/ .

The RAF Museum's 18 November 1941 Crusader entry lists Commonwealth
Hurricanes, Tomahawks, Beaufighters, Blenheims, Marylands and Boston
reconnaissance aircraft. Its timeline also lists German Ju 87 and Ju 88,
Bf 109 and Bf 110 in the theatre:
https://www.rafmuseum.org.uk/research/research-enquiries/history-of-aviation-timeline/british-military-aviation/1941-2/ .
`screen/pictures.aircraft` draws original simplified Commonwealth Hurricane,
Tomahawk, Blenheim and Boston examples, and Axis Ju 87, Ju 88, Macchi C.200
and Bf 109 examples. AWM's transcription of its Australian military aircraft chart
documents Italian Macchi C.200 fighters and Ju 87 dive bombers in the region:
https://transcribe.awm.gov.au/transcription/item/awm20241164-2 .
For the **motorised Bersaglieri counter**, the Italian Army's Ariete history
lists 8th Bersaglieri in Ariete from 1938. Historical orders of battle for
**1 November 1941**, compiled from the Italian *Seconda Offensiva Britannica
in Africa Settentrionale*, list its V and XII motorised battalions and the
9th Bersaglieri in Trieste with motorised battalions and a motorcycle
battalion (the document also lists further/support companies and shortages):
https://www.esercito.difesa.it/en/organization/operational-land-forces-command/multinational-division-south-mnd-s/132nd-ariete-armoured-brigade/the-history/123632.html ;
https://www.generalstaff.org/NAF/Pt_I_1941-1942/941ikaa.pdf ;
https://www.generalstaff.org/NAF/Pt_I_1941-1942/941ikab.pdf . These
compiled inventories are not the original dated regimental vehicle returns.
The open-lorry `it_bersaglieri_motorised.png` is illustrative transport plus
Bersaglieri plumes, **not** an identification of either regiment's lorry
make, count, or claim that its motorcycle troops rode lorries. OpenAI image
generation, 27 October 2026, used only this project's own Italian lorry and
7th Bersaglieri sprites as reference; the generated alpha image was
trimmed, fitted with `countergen.cut.fitted` and added as an original asset.

The RAF Museum also lists Curtiss Tomahawks among Crusader fighters. The
German Federal Archives' Tessin unit-history volume records JG 27 in the
North African theatre in 1941 and Me 109 'trop' equipment for the formation:
https://www.bundesarchiv.de/assets/bundesarchiv/de/Downloads/Tessin/Bd_14_ocr.pdf .
Original simplified Tomahawk and Bf 109 shapes now appear as *secondary*
fighter examples alongside the Hurricane and Macchi on the air button. The
second silhouette is not a second air point or proof of a particular sortie.
At the small in-game size, the two fighter silhouettes cannot reliably be
identified by outline alone, so each has a named hover target; the air
choice remains shared across both icons.

The Italian Macchi is shown on the Axis menu button to avoid implying that
Axis air meant only the Luftwaffe. An original **23 November 1941**
Fliegerfuehrer Afrika operations report, transcribed and annotated by the
Crusader Project (its archival scan has not been independently inspected),
records Bf 110 and Ju 88 reconnaissance sorties over the Crusader theatre:
https://rommelsriposte.com/2011/03/20/a-day-in-the-life-of-the-luftwaffe-operations-report-by-fliegerfuehrer-afrika-23-nov-41/ .
The Bf 110 now illustrates Axis reconnaissance; this does **not** identify
the aircraft flown on 18 November, the exact 2.(H)/14 squadron fleet, or a
specific sortie purchased by air points. The RAF Museum documents the type
as twin-engined:
https://www.rafmuseum.org.uk/research/collections/messerschmitt-bf-110g-2/ .
The Ju 88 is an illustrative theatre type, not evidence of a particular
interdiction sortie. Air points still abstract several air arms and missions;
the silhouettes do not assert that these were the only aircraft, nor that
each example flew the mission pictured on a particular turn.

**Axis reconnaissance research lead, not a unit assignment:** a compiled
18 November 1941 Axis order of battle lists an Afrika Korps reconnaissance
Staffel as `2(H)/14`, without an aircraft inventory:
https://www.generalstaff.org/NAF/Pt_I_1941-1942/941gkmj.pdf .
A 2021 *Scientia Militaria* study describes this unit's morning
reconnaissance mission on **19 November 1941**, reporting sightings of
Commonwealth vehicles. This supports its active reconnaissance role during
Crusader, **not** a particular aircraft type or a claim that it flew on the
storm-hit opening day:
https://www.ajol.info/index.php/smsajms/article/download/217929/205533 .
The Australian War Memorial's catalogue of a wartime British recognition
film identifies the Henschel Hs 126 as an army-cooperation aircraft, not
specifically as this Staffel's aircraft on the Crusader opening date:
https://www.awm.gov.au/collection/F05045 .
The link between this named formation and an Hs 126 in this scenario still
requires a dated operational or strength return before being drawn as fact.

The New Zealand official history *Divisional Cavalry* (New Zealand Electronic
Text Collection, foreword, November–December 1941) describes its light tanks
and Bren carriers in the Crusader period. Unit 335 therefore has an original,
AI-generated open-topped tracked carrier illustration (`cw_carrier.png`), not
the wheeled armoured-car default. This depicts a representative part of a
mixed formation, not every vehicle; the `cars: 30` scenario strength has not
been verified against a vehicle return. The generated image was resized and
fitted using this project's `countergen.cut.fitted`; no historical image was
copied or traced. Official history edition:
https://www.22battalion.org.nz/publications/histories/divcav.pdf .

The U.S. War Department's *Handbook on German Military Forces*, TM-E 30-451
(15 March 1945), ch. VII, names the leFH 18 among Germany's standard
divisional howitzers from the start of the war and describes 8.8 cm Flak
variants on their deployed mounts:
https://www.ibiblio.org/hyperwar/Germany/HB/HB-7.html .
The British official history *The Mediterranean and Middle East*, vol. II,
ch. 8, describes dug-in 88-mm guns in the Halfaya area in 1941 and German
37- and 50-mm anti-tank guns:
https://www.ibiblio.org/hyperwar/UN/UK/UK-Med-II/UK-Med-2-8.html .
These support distinctive representative painted leFH 18 and 88 sprites;
they do not establish the exact equipment mix of the four 1941 field/mixed
artillery formations or the combined Panzerjäger battalions. The latter uses
a newly illustrated Panzerjäger I for Battalion 605, not a claim that
Battalion 39 carried the same gun. The Bundesarchiv-hosted *Tessin*, vol. 11,
entry for Panzerjäger-Abteilung 605, records its October 1940 conversion
to 4.7 cm self-propelled anti-tank guns and deployment to Africa in February
1941 (the OCR prints "Flak (Sfl.)"; check the scanned page before relying on
that specific calibre spelling):
https://www.bundesarchiv.de/assets/bundesarchiv/de/Downloads/Tessin/Bd_11_ocr.pdf .
A transcribed intercepted 21 November 1941 German report names 13
self-propelled anti-tank guns lost from 605 during Operation Crusader,
corroborating its equipment but not its strength on 18 November or its
exact command attachment:
https://rommelsriposte.com/2009/08/15/the-tobruk-breakout-from-the-other-side-of-the-hill/ .
Pier Paolo Battistelli, *Rommel's Afrika Korps: Tobruk to El Alamein*
(Osprey, 2006; 2013 e-book, "Weapons and equipment"), reconstructs Battalion 39's re-equipment with towed 5 cm Pak 38 guns, listing twelve by
20 September 1941, and separately describes 605's 4.7 cm Pak(t) on
Panzer I Ausf. B chassis. This is original historical research, **not** an
original 18 November war-diary return:
https://www.ospreypublishing.com/us/rommels-afrika-korps-9781472800411/ .
The in-game counter combines **two battalions**: neither the Panzerjäger I
image nor the scenario's `guns: 36` establishes the actual November mix
or strength. The new no-markings sprite was generated with OpenAI image
generation on 27 October 2026 using only this game's original German field
gun painting as a palette/style reference; the rejected first candidate
wrongly resembled a six-wheel Panzer III. The chosen five-road-wheel
Panzer-I-chassis candidate was alpha-trimmed and fitted with
`countergen.cut.fitted`. No historical photograph or other game art was
copied or traced; this replaces the former sheet-cut towed variant.

Reconnaissance art: the Australian War Memorial catalogue P08802.015 dates a
German Sd.Kfz. 222 armoured-car photograph to c. 1941:
https://www.awm.gov.au/collection/C1244584 .
For German reconnaissance battalions 3 (21st Panzer) and 33 (15th
Panzer), a compiled **30 December 1941** vehicle-availability table (citing
German Archives T314/16) explicitly lists Sd.Kfz. 222 alongside heavier
Sd.Kfz. 231 and 232 vehicles for **both** formations:
https://www.generalstaff.org/NAF/Pt_I_1941-1942/941glma.pdf .
This is a transcribed table, not an inspected archival return, and it is
six weeks **after** the scenario starts. The table contains apparent errors
(e.g. its 33rd Battalion Sd.Kfz. 222 row has `4` full strength but `7`
present); neither its row counts nor its December mix can be assigned to
18 November without checking the original T314/16 return. An independent
March 1941 reconstruction also describes a light/heavy mix for the 3rd:
https://www.historyofwar.org/articles/weapons_sd_kfz_222.html .
The Bundesarchiv-hosted *Tessin*, vol. 5, p. 27, confirms that the 33rd was
motorised and with 15th Panzer Division in Africa from May 1941, but does
not list its November car types:
https://www.bundesarchiv.de/assets/bundesarchiv/de/Downloads/Tessin/Bd_5_ocr.pdf .
The Sd.Kfz. 222 remains a **representative** sprite for both battalions;
it does not imply that every car in either counter was a 222 or that the
scenario's `cars: 30` for each is a documented inventory. Both units' hover
notes disclose the other car examples and their later date.

*21 Battalion* (New Zealand official history, ch. 8, 29 November 1941,
around the Point 175/von Ravenstein episode) describes expected South African
Marmon-Herrington cars as having high open turrets, but the actual approaching
column was German, so this does not establish the complete equipment of
scenario unit 305:
https://www.22battalion.org.nz/publications/histories/21battalion.pdf .
The Italian defence-history RECAM report above supports a mixed armoured-car
and light-tank unit, but does not identify its cars. The painted AB41 is a documented RECAM component example (2018
retrospective account above), but its full 18 November vehicle mix and the
original Archivio Centrale photograph remain unverified. Three
new recon images were generated originally for this project, fitted with
`countergen.cut.fitted`; historical catalogue images were consulted for
vehicle types and not traced, copied or bundled.

Three previous sheet-cut subjects were checked against period/museum evidence
before replacement. The Australian War Memorial records a Panzer III Ausf. G
at a captured German workshop in Libya, dated c. November 1941, and more
Panzer III wrecks photographed around Sidi Rezegh in December 1941:
https://www.awm.gov.au/collection/C36058 and
https://www.awm.gov.au/collection/011853 .
This corroborates a representative Panzer III, not that both represented
regiments consisted exclusively of one mark. The Polish Gryf military
technology museum describes its 1940 Opel Blitz 3-ton as a 4×2 two-axle
truck (the old sheet cut incorrectly had three axles):
https://muzeumgryf.pl/eksponaty/opel-blitz-3t/ .
The Australian War Memorial holds a 1939 Italian M33 helmet recovered during
North African service and identifies its domed shell and slight front lip:
https://www.awm.gov.au/collection/REL34875 .
Their replacement Panzer III, Opel and Italian infantry pictures are original
AI-generated illustrations for this project, trimmed and fitted to the
standard transparent canvas by `countergen.cut.fitted`; none of the source
photographs or object images was traced, copied or added to the repository.

The Australian War Memorial catalogues 1941 North African M13/40 tanks,
including a captured example photographed in February and another in
December; black-and-white photos do not establish the old sprite's striped
paint scheme. The replacement deliberately omits unit markings and stripes:
https://www.awm.gov.au/collection/C29732 and
https://www.awm.gov.au/collection/C6635 .
The Memorial also identifies a captured Italian 75/27 modello 06 field gun
at Tobruk on 27 August 1941:
https://www.awm.gov.au/collection/C4691 .
The Italian Army's history of the 21st Trieste Artillery Regiment notes both
75/27 and 100/17 guns, so the new 75/27 illustration is explicitly
representative rather than every Italian battery's documented calibre:
https://www.esercito.difesa.it/en/organization/the-chief-of-general-staff-of-the-army/comfoter/southern-operational-forces-command/pinerolo-mechanized-brigade/21st-trieste-land-artillery-regiment/the-history/123920.html .
The Royal Logistic Corps describes the Bedford OY as a 1939 British 3-ton
truck; its allocation to the seven composite motorised formations is not
confirmed by this source:
https://www.royallogisticcorps.co.uk/151-regt-gears-up-for-lord-mayors-show/ .
The Italian Army transport corps veterans' museum catalogue describes a
1939 Lancia 3Ro heavy truck, used on several fronts, without confirming
the precise trucks of these four scenario units:
https://www.anai.it/wp-content/uploads/2023/08/COPERTINA-MUSEO-III-PARTE.pdf .
The new British and Italian lorries and Italian gun/tank are originally
generated pictures, trimmed and fitted to the same transparent canvas;
photographs were not traced, copied or included.

The Italian Army's history of the 7th Bersaglieri Regiment confirms its
attachment to Trento from 22 January 1939 and its African service from
1941 through 1943:
https://www.esercito.difesa.it/en/organization/the-chief-of-general-staff-of-the-army/comfoter/southern-operational-forces-command/pinerolo-mechanized-brigade/7th-bersaglieri-regiment/the-history/123924.html .
The Army identifies the Bersaglieri's distinctive plumed headgear and its
official *Rivista Militare* depicts a desert-dressed Ariete Bersagliere with
dark feathers on his helmet (later 1942 context, **not** an individual
1941 Trento portrait):
https://www.esercito.difesa.it/en/equipment/militaria/decorations/infantry-and-specialties---bersaglieri/76680.html and
https://www.esercito.difesa.it/comunicazione/editoria/Rivista-Militare/archivio/Documents/2002/Rivista%20Militare%202002%20-%20Numero%206.pdf .
The three-soldier `it_bersaglieri.png` variant was generated for this project
with OpenAI image generation, using only this game's `it_foot.png` as an
editing reference, then fitted to the transparent counter canvas. No external
illustration was copied or bundled. The 8th and 9th motorised Bersaglieri
still need their vehicle mix checked before altering their lorry art.

The replacement British/Commonwealth and German infantry were generated for
this game using OpenAI image generation, trimmed, repeated three times, and
fitted to the 480 × 288 transparent canvas with `countergen.cut.fitted`.
Historical object and museum records were used to check the representative
1941 shapes and dress, not traced or copied into the pictures: the Australian
War Memorial records Lee–Enfield rifles used at Tobruk and a German Model 1941
tropical field cap, while the National Army Museum describes Commonwealth
desert uniform in its North Africa collections. These sources do not establish
the exact uniform of each aggregated infantry unit. The legacy AI tool and
terms for the older sheet and two Axis HQ cars remain unrecorded.

## Weather

Looked up on 7 October 2026 by web search, reading summaries and encyclopaedia
articles, not the official histories themselves. `docs/RULES.md` §21 is built
on it: the kinds of effect from the dated events below, the odds of rain from
the climate figures after them. These are the dated events found for the
map's area, with what each did. Check each against the source named before a
scenario relies on it.

| When | Where | What | Effect | Found in |
| --- | --- | --- | --- | --- |
| 9 December 1940 | Tummar West (Compass) | sandstorm | 7th Royal Tank Regiment's attack delayed | historyofwar.org, Operation Compass |
| 13 March 1941 | on the way to Sirte | sandstorm | Rommel's aircraft turned back; he went by car | historyofwar.org, Rommel's first offensive |
| night of 17/18 November 1941 | the coast, hardest on the Axis fields in the west | rainstorms and floods | aircraft of both sides grounded on the first day of Crusader; Axis air reconnaissance blind; British raids on Axis airfields cancelled; Axis signal cables washed out, men and stores lost in wadis; fields usable again by light aircraft on the 18th | Wikipedia, Operation Crusader, citing Playfair vol. III pp. 38–39; rommelsriposte.com |
| late January 1942 | Antelat and Msus | rain, sodden landing grounds | British aircraft grounded during Rommel's second offensive | historyofwar.org, Rommel's second offensive |
| 1–2 June 1942 | Gazala | sandstorms | British replies hampered; nothing seen | warfarehistorynetwork.com, Clash of Armor at Gazala |
| 13 June 1942 | Rigel Ridge (Gazala) | sandstorm | 21. Panzer-Division attacked under its cover | Wikipedia, Battle of Gazala |
| 1 July 1942 | El Alamein | sandstorm | 15. and 21. Panzer-Division delayed | Wikipedia, First Battle of El Alamein |
| afternoon of 6 November 1942 | east of Mersa Matruh | heavy rain | Eighth Army's pursuit bogged off the road; the Axis reached Matruh | historyofwar.org and others, Second Battle of El Alamein |

What the record suggests a weather rule would do: ground the air, shorten
sight, and slow or stop movement off the roads. Nothing found gives heat a
dated effect on a battle; the articles read do not mention it, though the
summer lulls and the midday haze are commonly described. That is from memory
and unchecked.

Within the Crusader scenario (18 November to 30 December 1941) one event is
dated: the storm of the night before it opened. The same source speaks of
"violent rainstorms in November and December" on the forward airfields without
dates.

Climate, for the odds by month (RULES 21.3.1), all at second hand:

- Days a month with 1 mm of rain or more at Tobruk, normals for 1991 to 2020
  (NOAA, as given in Wikipedia's article on Tobruk): January 5.9, February
  4.2, March 2.0, April 0.8, May 0.6, June 0.1, July and August 0, September
  0.4, October 2.0, November 2.7, December 5.2. Benghazi has more: January
  8.9, December 9.7, November 4.8 (Wikipedia, Benghazi, the same source). The
  rules use Tobruk, which is nearer the middle of the fighting.
- These are modern normals, not the weather of 1940 to 1942.
- The khamsin (Wikipedia, Khamsin): "usually arrives in April but occasionally
  can occur between March and May"; "rarely occurs more than once a week and
  lasts for just a few hours at a time". The same article says Allied and
  German troops "were several times forced to halt in mid-battle because of
  sandstorms". No count of storm days by month was found.
