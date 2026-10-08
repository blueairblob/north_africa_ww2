"""Saved games: one file each, of plain text, under saves/ (not published). No pygame here.

A save is the whole game as it stands (Session.to_save): taken up again it goes on exactly as
it would have, in the middle of a turn's orders or at its start. It holds the number the
weather is drawn from, as it must; nothing on the screen shows it."""
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

from .session import Session

FOLDER = Path(__file__).parent.parent / "saves"
LISTED = 8              # how many saves the screen lists, newest first
SIDE = {"axis": "Axis", "cw": "Commonwealth"}


def about(data):
    """A save in a few words, for the list: the scenario, the turn and its date, who is to order."""
    scenario, state = data["scenario"], data["state"]
    day = date.fromisoformat(scenario["start"]) + timedelta(days=2 * (state["turn"] - 1))
    who = "the game is over" if state["over"] else f"{SIDE[data['waiting'][0]]} to order"
    return f"{scenario['name']}, turn {state['turn']} of {scenario['turns']}, {day.day} {day:%B %Y}: {who}"


def write(session, folder=FOLDER, auto=False):
    """Save the game; returns the file. An autosave replaces the last one of its scenario; a
    save the player asks for is kept under the turn and the time. The file is written whole
    or not at all."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    data = session.to_save()
    data["saved"], data["auto"] = time.strftime("%Y-%m-%d %H:%M"), auto
    stem = f"{session.scenario['id']}-turn{session.state['turn']:02d}-{time.strftime('%Y%m%d-%H%M%S')}"
    name, n = f"{session.scenario['id']}-autosave.json" if auto else stem + ".json", 1
    while not auto and (folder / name).exists():        # a second save in the same second is kept too
        name, n = f"{stem}-{n + 1}.json", n + 1
    part = folder / (name + ".part")
    part.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(part, folder / name)
    return folder / name


def read(path, gmap):
    """The game in a file, to go on with. ValueError, in words for the player, if it cannot be read."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("That file cannot be read as a saved game.") from None
    return Session.from_save(data, gmap)


def listing(folder=FOLDER):
    """[(file, words)] for the newest saves, newest first; a file that is no save is left out."""
    files = sorted(Path(folder).glob("*.json"), key=lambda f: (f.stat().st_mtime_ns, f.name), reverse=True)
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            words = about(data) + ("   (autosave)" if data.get("auto") else "") + f"   saved {data['saved']}"
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            continue
        out.append((f, words))
        if len(out) == LISTED:
            break
    return out


def newest(folder=FOLDER):
    """The file saved last, or None."""
    found = listing(folder)
    return found[0][0] if found else None
