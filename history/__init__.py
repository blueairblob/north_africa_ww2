"""Sourced historical context, kept separate from the playable campaign state."""
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data" / "history" / "north_africa_1940_1942.json"
BATTLES = ROOT / "data" / "history" / "battles_1940_1942.json"
DRAFTS = ROOT / "data" / "scenario_drafts"
EVENT_KINDS = {"arrival", "battle", "movement", "result", "withdrawal"}
BATTLE_CHAPTERS = {
    "italian_invasion_1940", "compass_opening", "bardia_assault", "tobruk_assault",
    "derna_pursuit", "beda_fomm_pursuit", "cyrenaica_reversal", "tobruk_siege_opening",
    "brevity_frontier", "halfaya_counterstroke", "battleaxe_frontier", "crusader_linked_1941",
    "axis_january_offensive_1942", "gazala_battle_1942", "egyptian_retreat_1942",
    "first_alamein_1942", "alam_halfa_1942", "second_alamein_1942",
    "november_pursuit_1942",
}


def load(path=FILE, battles_path=BATTLES):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    battle_record = json.loads(Path(battles_path).read_text(encoding="utf-8"))
    record["battles_format"] = battle_record.get("format")
    record["battles"] = battle_record.get("battles", [])
    return record


def for_chapter(chapter_id, record=None):
    """Prefer a battle account; preparation chapters use their period account."""
    record = record or load()
    battle = next((battle for battle in record.get("battles", [])
                   if chapter_id == battle.get("chapter")
                   or chapter_id in battle.get("scenario_aliases", [])), None)
    if battle:
        period = next((episode for episode in record["episodes"]
                       if episode["id"] == battle["period"]), None)
        return {**battle, "period_image": period.get("image") if period else None}
    return period_for_chapter(chapter_id, record)


def period_for_chapter(chapter_id, record=None):
    """Return the broader chronological account that contains a chapter."""
    record = record or load()
    return next((episode for episode in record["episodes"]
                 if chapter_id in episode["chapters"]
                 or chapter_id in episode.get("scenario_aliases", [])), None)


def problems(record=None, drafts=DRAFTS):
    """Check coverage, chronological boundaries, local notes and source keys."""
    from engine import scenarios

    record = record or load()
    errors = []
    if record.get("format") != 1:
        errors.append("history format must be 1")
    sources = record.get("sources", {})
    episodes = record.get("episodes", [])
    battles = record.get("battles", [])
    if (not isinstance(sources, dict) or not isinstance(episodes, list)
            or not isinstance(battles, list)):
        return ["sources must be an object; episodes and battles must be lists"]
    if record.get("battles_format") != 1:
        errors.append("battle record format must be 1")
    for key, source in sources.items():
        if not source.get("title") or not source.get("url", "").startswith("https://"):
            errors.append(f"source {key} needs a title and HTTPS URL")
    expected = []
    scenes = {}
    current = "italian_frontier_1940"
    while current:
        if current in expected:
            errors.append(f"chapter cycle at {current}")
            break
        expected.append(current)
        scene = scenarios.load(current, drafts)
        scenes[current] = scene
        current = scene.get("research_next")
    covered = []
    aliases = []
    def check_story(story, is_battle=False):
        sid = story.get("id", "<unnamed>")
        try:
            start_day = date.fromisoformat(story["start"])
            end_day = date.fromisoformat(story["end"])
            if start_day > end_day:
                errors.append(f"{sid}: start follows end")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{sid}: invalid date range")
            return
        if not story.get("title") or not story.get("limits"):
            errors.append(f"{sid}: title and limits are required")
        for note in story.get("research", []):
            if not (ROOT / note).is_file():
                errors.append(f"{sid}: missing research note {note}")
        for section, fields in (("pre", ("objective", "forces", "deployment")),
                                ("post", ("outcome", "why"))):
            item = story.get(section, {})
            if any(not item.get(field) for field in fields):
                errors.append(f"{sid}: incomplete {section}")
            for key in item.get("sources", []):
                if key not in sources:
                    errors.append(f"{sid}: unknown source {key}")
            if not item.get("sources"):
                errors.append(f"{sid}: unsourced {section}")
        events = story.get("timeline", [])
        dates = []
        for event in events:
            day = event.get("date", "")
            dates.append(day)
            try:
                event_day = date.fromisoformat(day)
            except (TypeError, ValueError):
                event_day = None
            if event_day is None or not start_day <= event_day <= end_day or not event.get("event"):
                errors.append(f"{sid}: invalid event {day}")
            if is_battle and event.get("kind") not in EVENT_KINDS:
                errors.append(f"{sid}: invalid event kind {day}")
            if not event.get("sources"):
                errors.append(f"{sid}: unsourced event {day}")
            for key in event.get("sources", []):
                if key not in sources:
                    errors.append(f"{sid}: unknown source {key}")
        if dates != sorted(dates):
            errors.append(f"{sid}: events are out of order")

    for episode in episodes:
        eid = episode.get("id", "<unnamed>")
        illustration = episode.get("image", {})
        if any(not illustration.get(key) for key in ("file", "caption", "credit", "source", "commons_file")):
            errors.append(f"{eid}: incomplete period image credit")
        elif (not illustration["file"].startswith("art/history/")
              or not illustration["source"].startswith("https://commons.wikimedia.org/wiki/File:")
              or not (ROOT / illustration["file"]).is_file()):
            errors.append(f"{eid}: missing or invalid period image")
        chapters = episode.get("chapters", [])
        if not chapters:
            errors.append(f"{eid}: no chapters")
            continue
        covered.extend(chapters)
        aliases.extend(episode.get("scenario_aliases", []))
        first, last = scenes[chapters[0]], scenes[chapters[-1]]
        last_day = date.fromisoformat(last["start"]) + timedelta(
            days=last["turn_days"] * last["turns"] - 1)
        if episode.get("start") != first["start"] or episode.get("end") != last_day.isoformat():
            errors.append(f"{eid}: dates do not match chapter boundaries")
        check_story(episode)
    if covered != expected:
        errors.append("episodes must cover all linked trial chapters exactly once, in order")
    if len(aliases) != len(set(aliases)) or any(
            not (scenarios.FOLDER / f"{alias}.json").is_file() for alias in aliases):
        errors.append("scenario aliases must name distinct shipped scenarios")
    periods = {episode["id"]: episode for episode in episodes}
    battle_chapters = []
    battle_aliases = []
    battle_ids = []
    for battle in battles:
        bid = battle.get("id", "<unnamed>")
        battle_ids.append(bid)
        chapter = battle.get("chapter")
        battle_aliases.extend(battle.get("scenario_aliases", []))
        period = periods.get(battle.get("period"))
        if period is None:
            errors.append(f"{bid}: unknown period")
        if chapter is not None:
            battle_chapters.append(chapter)
            if chapter not in scenes or period is None or chapter not in period["chapters"]:
                errors.append(f"{bid}: chapter is outside its period")
            else:
                scene = scenes[chapter]
                chapter_end = date.fromisoformat(scene["start"]) + timedelta(
                    days=scene["turn_days"] * scene["turns"] - 1)
                if not scene["start"] <= battle["start"] <= battle["end"] <= chapter_end.isoformat():
                    errors.append(f"{bid}: battle dates fall outside the trial chapter")
        elif not battle.get("scenario_aliases"):
            errors.append(f"{bid}: a battle needs a chapter or independent scenario")
        if period and not period["start"] <= battle["start"] <= battle["end"] <= period["end"]:
            errors.append(f"{bid}: battle dates fall outside its period")
        for dispute in battle.get("disputed", []):
            if not dispute.get("point") or len(dispute.get("accounts", [])) < 2:
                errors.append(f"{bid}: incomplete source dispute")
            for account in dispute.get("accounts", []):
                if not account.get("claim") or not account.get("sources"):
                    errors.append(f"{bid}: unsourced disputed claim")
                for key in account.get("sources", []):
                    if key not in sources:
                        errors.append(f"{bid}: unknown source {key}")
        check_story(battle, is_battle=True)
    if len(battle_ids) != len(set(battle_ids)):
        errors.append("battle ids must be unique")
    if set(battle_chapters) != BATTLE_CHAPTERS or len(battle_chapters) != len(BATTLE_CHAPTERS):
        errors.append("battle accounts must cover every named battle or pursuit chapter once")
    if set(battle_aliases) != {"crusader", "sidi_rezegh"} or len(battle_aliases) != 2:
        errors.append("independent battle accounts must cover Crusader and Sidi Rezegh once")
    return errors


def markdown(record=None):
    """Render a review copy; the JSON remains the single editable record."""
    record = record or load()
    sources = record["sources"]

    def refs(keys):
        return " ".join(f"[{key}]({sources[key]['url']})" for key in keys)

    lines = ["<!-- Generated from data/history/north_africa_1940_1942.json by python -m history. -->",
             "# North Africa historical story, 1940–42", "",
             "Historical reference only. Played results can differ. The linked research notes",
             "hold detailed evidence and the open validation questions.", ""]
    def add_story(story, level):
        pre, post = story["pre"], story["post"]
        lines.extend((f"{'#' * level} {story['title']} ({story['start']}–{story['end']})", ""))
        chapters = story.get("chapters") or ([story["chapter"]] if story.get("chapter") else [])
        if chapters:
            lines.extend((f"Trial chapters: {', '.join(chapters)}", ""))
        if story.get("scenario_aliases"):
            lines.extend((f"Independent battles: {', '.join(story['scenario_aliases'])}", ""))
        if image := story.get("image"):
            lines.extend((f"![{image['caption']}](../{image['file']})", "",
                          f"Archive image: {image['caption']} {image['credit']}. "
                          f"[Source and reuse record]({image['source']}).", ""))
        lines.extend((f"**Before — objective:** {pre['objective']}", "",
                      f"**Forces:** {pre['forces']}", "",
                      f"**Deployment:** {pre['deployment']}", "",
                      f"Opening evidence: {refs(pre['sources'])}", "",
                      "**Historical sequence:**", ""))
        lines.extend(f"- {event['date']}{' · ' + event['kind'] if event.get('kind') else ''}: "
                     f"{event['event']} {refs(event['sources'])}"
                     for event in story["timeline"])
        lines.extend(("", f"**After — result:** {post['outcome']}", "",
                      f"**Why (source-based interpretation):** {post['why']}", "",
                      f"Aftermath evidence: {refs(post['sources'])}", "",
                      f"**Evidence limits:** {story['limits']}", "",
                      "Research notes: " + ", ".join(
                          f"[{Path(note).name}]({Path(note).name})" for note in story["research"]), ""))
        for dispute in story.get("disputed", []):
            lines.extend((f"**Source discrepancy — {dispute['point']}:**", ""))
            lines.extend(f"- {account['claim']} {refs(account['sources'])}"
                         for account in dispute["accounts"])
            lines.append("")

    if record["episodes"]:
        lines.extend(("## Period summaries", ""))
        for episode in record["episodes"]:
            add_story(episode, 3)
    if record["battles"]:
        lines.extend(("## Battle and operation records", ""))
        for battle in record["battles"]:
            add_story(battle, 3)
    return "\n".join(lines)
