# Historical story archive

The editable [period record](../data/history/north_africa_1940_1942.json)
covers all 33 linked research-trial chapters from 1 September 1940 to 30
November 1942. The [battle record](../data/history/battles_1940_1942.json)
adds 20 specific battles and operations, including the independent Sidi Rezegh
game. Each record gives objectives, selected forces and deployment before play;
dated events; and the historical result and reasons after play. The [generated review copy](HISTORICAL_STORY_REVIEW.md) is easier
to read and annotate. Regenerate it with:

```bash
python -m history > docs/HISTORICAL_STORY_REVIEW.md
python -m history --chapter bardia_assault
```

The two JSON files are the editable records; `python -m history` combines them
only when rendering. `history.for_chapter(id)` chooses a specific battle record
when one exists and otherwise returns the broader period account. The setup screen's **History** button shows the opening context; the
Game menu's **Historical context** opens the same record during or after play,
including its historical aftermath. That aftermath is labelled separately
from the result the player actually achieved.
Each period has one archival photograph in `art/history`. The battle view shows
its parent period's photograph on a separate page. The caption states what the
photograph depicts and when; the credit identifies the archive and reuse status.
Click the photograph to open its source and reuse record. The generated review
copy also embeds each image and links to that record. A period illustration is
context, not evidence that the pictured event occurred in every battle in the
period. `python scripts/fetch_history_images.py` can retrieve the documented
Commons copies again if the local artwork needs restoring.
The `timeline` lists selected dated anchors, not scripted game events. Battle
events also carry a kind such as movement, battle, withdrawal or result. Each
`post.why` is a source-based interpretation, not a quotation or an independently
verified mechanism. Where sources disagree on a date, `disputed` keeps both
claims and their citations; the History screen shows that disagreement.

The linked `research` notes retain the detailed source comparisons, force
figures, map questions, withdrawals, proposed mechanics and play traces. The
story record deliberately calls selected formations a summary where a full
dated order of battle has not been verified. Its `limits` fields identify the
main unresolved work for each record. Game scenario JSON remains the source
for *modelled* unit strengths, schedules, positions and aims. Those values
must never be silently copied into the historical story as fact.

For a new historical assertion, add a direct source in `sources`, attach its
key to the relevant `pre`, `timeline` or `post` field, and keep the event date
within the period or battle. Record contradictory or uncertain evidence in the linked
research note before summarising it here. Run `python -m pytest -q
tests/test_history.py` after editing: it checks sources, notes, dates, complete
coverage of the 33 chapter chain and one battle account for each named battle
or pursuit chapter. The broader
[validation ledger](HISTORICAL_VALIDATION_LEDGER.md) still governs when the
research trial may be called a historical simulation.
