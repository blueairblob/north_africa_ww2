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

## Art

Generated for this game: hex terrain tiles drawn from the terrain types, and
unit symbols drawn from NATO military symbology (APP-6 / MIL-STD-2525, public
standards). No art from any other game.
