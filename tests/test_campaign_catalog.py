"""Campaign research windows never masquerade as playable scenarios."""
from copy import deepcopy

from engine import campaigns, scenarios


def test_catalog_covers_original_scope_and_only_lists_installed_starts():
    catalog = campaigns.load()
    assert catalog["scope"] == "1940-09/1942-11"
    assert catalog["chapters"][0]["id"] == "frontier_1940"
    assert catalog["chapters"][-1]["id"] == "second_alamein"
    assert campaigns.playable(catalog) == ["crusader", "sidi_rezegh"]
    assert set(campaigns.playable(catalog)) == set(scenarios.names())
    assert next(ch for ch in catalog["chapters"] if ch["id"] == "compass")["status"] == "research"
    assert campaigns.opening(catalog) is None


def test_catalog_rejects_a_draft_chapter_claiming_an_installed_scenario():
    catalog = campaigns.load()
    draft = deepcopy(catalog)
    draft["chapters"][1]["scenario"] = "crusader"
    assert "research chapter cannot claim" in str(campaigns.check(draft))
    draft = deepcopy(catalog)
    draft["chapters"][1]["period"] = "1941-11/1941-12"
    assert "without overlap" in str(campaigns.check(draft))


def test_following_only_uses_the_immediately_adjacent_installed_primary_chapter():
    catalog = campaigns.load()
    assert campaigns.following(catalog, "crusader") is None
    assert campaigns.following(catalog, "sidi_rezegh") is None
    linked = deepcopy(catalog)
    linked["chapters"][5]["status"] = "review"
    linked["chapters"][5]["scenario"] = "next_operation"
    assert campaigns.following(linked, "crusader") == "next_operation"
    assert campaigns.following(linked, "sidi_rezegh") is None


def test_campaign_opening_requires_the_first_chapter_to_be_reviewed():
    catalog = campaigns.load()
    linked = deepcopy(catalog)
    linked["chapters"][0]["status"] = "review"
    linked["chapters"][0]["scenario"] = "frontier_start"
    assert campaigns.opening(linked) == "frontier_start"
