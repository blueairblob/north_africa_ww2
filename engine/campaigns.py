"""Chapter catalog for the proposed continuous campaign.

Periods are broad research windows, not turn boundaries or orders of battle.
Only chapters naming a checked scenario are currently playable on their own.
"""
import json
from datetime import date
from pathlib import Path

from . import scenarios

FOLDER = Path(__file__).parent.parent / "data" / "campaigns"
STATUSES = {"research", "review"}


def load(name="north_africa", folder=FOLDER):
    catalog = json.loads((Path(folder) / f"{name}.json").read_text(encoding="utf-8"))
    problems = check(catalog)
    if problems:
        raise ValueError("Invalid campaign catalog: " + "; ".join(problems))
    return catalog


def check(catalog, scenario_names=None):
    """Validate catalog shape and chronology without implying chapters can link yet."""
    known = set(scenarios.names()) if scenario_names is None else set(scenario_names)
    if not isinstance(catalog, dict) or catalog.get("format") != 1 or not catalog.get("id"):
        return ["format 1 and a campaign id are required"]
    chapters = catalog.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return ["at least one chapter is required"]
    problems, seen, last = [], set(), None
    if "research_trial" in catalog and (not isinstance(catalog["research_trial"], str)
                                        or not catalog["research_trial"]):
        problems.append("research_trial must name a research opening")
    for chapter in chapters:
        if not isinstance(chapter, dict):
            problems.append("chapter must be an object")
            continue
        identity = chapter.get("id")
        if not identity or identity in seen:
            problems.append(f"duplicate or missing chapter id: {identity}")
        seen.add(identity)
        period = chapter.get("period", "")
        try:
            start, end = period.split("/")
            if len(start) != 7 or len(end) != 7:
                raise ValueError("bad month")
            date.fromisoformat(start + "-01")
            date.fromisoformat(end + "-01")
            if end < start or last is not None and start <= last:
                problems.append(f"chapter {identity}: periods must rise without overlap")
            last = end
        except (ValueError, TypeError, AttributeError):
            problems.append(f"chapter {identity}: period must be YYYY-MM/YYYY-MM")
        status = chapter.get("status")
        if status not in STATUSES:
            problems.append(f"chapter {identity}: unknown status")
        linked = [chapter.get("scenario")] if chapter.get("scenario") else []
        linked += chapter.get("short_scenarios", [])
        if any(name not in known for name in linked):
            problems.append(f"chapter {identity}: scenario is not installed")
        if status == "review" and not chapter.get("scenario"):
            problems.append(f"chapter {identity}: review needs a playable scenario")
        if status == "research" and linked:
            problems.append(f"chapter {identity}: research chapter cannot claim a playable scenario")
    first = chapters[0].get("period", "") if isinstance(chapters[0], dict) else ""
    final = chapters[-1].get("period", "") if isinstance(chapters[-1], dict) else ""
    expected = f"{first.split('/')[0]}/{final.split('/')[-1]}" if isinstance(first, str) and isinstance(final, str) else ""
    if not catalog.get("scope") or catalog["scope"] != expected:
        problems.append("campaign scope must match its first and last chapter")
    return problems


def playable(catalog):
    """Standalone scenario names in chronology, never a claim of continuity."""
    return [name for chapter in catalog["chapters"] if chapter["status"] == "review"
            for name in [chapter["scenario"], *chapter.get("short_scenarios", [])]]


def opening(catalog):
    """The whole-war start exists only when the first chapter is installed for review."""
    first = catalog["chapters"][0]
    return first.get("scenario") if first.get("status") == "review" else None


def following(catalog, scenario_id):
    """The next installed primary chapter, if it immediately follows this one."""
    chapters = catalog["chapters"]
    for index, chapter in enumerate(chapters[:-1]):
        if chapter.get("scenario") == scenario_id:
            successor = chapters[index + 1]
            return successor.get("scenario") if successor.get("status") == "review" else None
    return None
