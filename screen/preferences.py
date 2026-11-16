"""Small presentation-only preferences, independent of game saves and rules."""
import json
import os
from pathlib import Path

DEFAULTS = {"symbols": "pictures", "sound": True, "weather_visible": True,
            "details_collapsed": False, "remind": True, "window": [1400, 860]}


def valid(data):
    out = dict(DEFAULTS)
    if not isinstance(data, dict):
        return out
    if data.get("symbols") in ("pictures", "nato"):
        out["symbols"] = data["symbols"]
    for name in ("sound", "weather_visible", "details_collapsed", "remind"):
        if type(data.get(name)) is bool:
            out[name] = data[name]
    size = data.get("window")
    if (isinstance(size, list) and len(size) == 2 and all(type(v) is int for v in size)
            and 900 <= size[0] <= 7680 and 560 <= size[1] <= 4320):
        out["window"] = size
    return out


def read(path):
    try:
        return valid(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return dict(DEFAULTS)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    part.write_text(json.dumps(valid(data), indent=2) + "\n", encoding="utf-8")
    os.replace(part, path)
