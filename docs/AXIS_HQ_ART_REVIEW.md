# Axis headquarters art review (Operation Crusader, 18 November 1941)

The seven in-game previews below show the **adopted default**, initially rendered by setting `counter_art` to `hq_label` for Axis HQs. The small map counter uses the existing nationality marker, `HQ`, and a short formation name. The detail card uses the marker and full formation name. Italy's marker is the Kingdom of Italy tricolour with Savoy arms; Germany's is the black vehicle recognition cross, **not** a German national flag. The footer keeps the same identification cue. NATO mode still uses its existing symbols.

| HQ in scenario | Preview | Period evidence and recommendation |
| --- | --- | --- |
| Panzergruppe Afrika | [101](gui-concepts/24-axis-hq-preview-101.png) | Keep named fallback. A common Afrika Korps palm marking would not uniquely identify this HQ. |
| XXI Corpo d'Armata | [102](gui-concepts/24-axis-hq-preview-102.png) | Keep Italian flag and full corps name. No dated corps sign established in this review. |
| Corpo d'Armata di Manovra | [103](gui-concepts/24-axis-hq-preview-103.png) | Keep Italian flag and full corps name. The long name needs the two-line card treatment shown. |
| 15. Panzer-Division | [110](gui-concepts/24-axis-hq-preview-110.png) | Strongest candidate for a separate formation sign: a triangle with a vertical stroke, illustrated in the division's war diary covering April–18 November 1941, though that copy was reconstructed in 1942 after the original was lost. A North African vehicle photograph is also reported. Draw a clean vector based on the documented shape after checking the original war-diary plate. |
| 21. Panzer-Division | [120](gui-concepts/24-axis-hq-preview-120.png) | A simple divisional mark appears on Commons, but that upload is an undated 2008 self-drawn file with no contemporary source. Use named fallback until a dated 1941 record or photograph confirms the exact mark. |
| Division z.b.V. Afrika | [130](gui-concepts/24-axis-hq-preview-130.png) | Keep its November 1941 name and named fallback. The formation was later known as 90th Light; its later badge should not be assigned back to this date without evidence. |
| Savona, Ariete, Trieste, Brescia, Trento, Pavia, Bologna | [Ariete 150](gui-concepts/24-axis-hq-preview-150.png) | Use Italian flag and named fallback for all seven. Commons hosts attractive division coats of arms, but at least the Savona and Trieste files are uploader-created artwork dated 2017 with no period source cited. Treat them as visual leads, not verified 1941 formation signs. |

## Source check

- [Panzerworld German unit-insignia catalogue](https://panzerworld.com/german-unit-insignia), 15. Panzer-Division entry. It identifies the triangle/stroke and cites the reconstructed 1941 war diary as NARA T315 R665; verify the underlying plate before finalising the badge.
- [Wikimedia Commons, 21st Panzer Division logo](https://commons.wikimedia.org/wiki/File:21st_Panzer_Division_logo.svg): described as a World War II mark, but the file's source is the artist's own work.
- [Wikimedia Commons, Trieste coat of arms](https://commons.wikimedia.org/wiki/File:101a_Divisione_Motorizzata_Trieste.png) and [Savona insignia](https://commons.wikimedia.org/wiki/File:55a_Divisione_Fanteria_Savona.png): each file states “Own work”, dated March 2017.
- [90th Light Infantry Division formation history](https://en.wikipedia.org/wiki/90th_Light_Infantry_Division) and [Lexikon der Wehrmacht history](https://www.lexikon-der-wehrmacht.de/Gliederungen/leichte%20Panzerdivisionen/90leDivR.htm): the name change followed the scenario opening; exact later redesignations vary among sources.

## Implementation and next research step

`hq_label` is now the default for Axis and Commonwealth HQs, retaining explicit per-scenario art overrides. A verified 15th Panzer sign can be added to the detail card after checking the original war-diary plate. Keep the candidate Italian crests out of the shipped game until dated evidence is found.
