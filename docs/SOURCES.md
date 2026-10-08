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

## Art

Generated for this game: hex terrain tiles drawn from the terrain types, and
unit symbols drawn from NATO military symbology (APP-6 / MIL-STD-2525, public
standards). No art from any other game.

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
