"""One structural check keeps the historical story tied to all trial chapters."""
from pathlib import Path

from history import BATTLE_CHAPTERS, for_chapter, load, markdown, period_for_chapter, problems


def test_history_covers_every_trial_chapter_with_sourced_pre_and_post_context():
    record = load()
    assert problems(record) == []
    assert len({chapter for episode in record["episodes"]
                for chapter in episode["chapters"]}) == 33
    assert {battle["chapter"] for battle in record["battles"] if battle["chapter"]} == BATTLE_CHAPTERS
    assert for_chapter("bardia_assault", record)["id"] == "bardia_1941"
    assert len(for_chapter("tobruk_assault", record)["disputed"][0]["accounts"]) == 2
    assert for_chapter("sidi_rezegh", record)["id"] == "sidi_rezegh_1941"
    assert for_chapter("november_pursuit_1942", record)["id"] == "november_pursuit_1942"
    assert period_for_chapter("bardia_assault", record)["id"] == "compass"
    assert for_chapter("italian_camps_1940", record)["id"] == "frontier_1940"
    assert for_chapter("bardia_assault", record)["period_image"] == period_for_chapter("bardia_assault", record)["image"]
    assert len({episode["image"]["file"] for episode in record["episodes"]}) == 9
    review = markdown(record)
    assert review.count("Source and reuse record") == 9
    assert review.count("**Before — objective:**") == len(record["episodes"]) + len(record["battles"])
    assert review.count("**After — result:**") == len(record["episodes"]) + len(record["battles"])
    review_file = Path(__file__).resolve().parents[1] / "docs" / "HISTORICAL_STORY_REVIEW.md"
    assert review_file.read_text(encoding="utf-8") == review + "\n"
