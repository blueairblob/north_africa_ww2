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
from memory. All are marked in the scenario file.

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
