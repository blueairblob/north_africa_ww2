"""Content packs: swappable data layers over one generic engine.

Design (see NOTES.md "Content-pack seam"): the engine never hard-codes
WHAT it loads, only the SHAPES it loads (a 100x32 logic-type grid, an
order of battle, scenarios, deployments, UI strings, an optional render
model). A pack is a directory under content_packs/ with a pack.json
manifest:

    {
      "name": "default",
      "title": "North Africa 1941-42 (historical)",
      "inherits": "og",           # optional parent pack
      "legacy_data": false        # og-only: fall back to the repo data/ dir
    }

File resolution walks the pack, then its ancestors, then (if any pack in
the chain sets "legacy_data") the historical top-level data/ directory.
That legacy fallback exists so the OG pack can be a thin manifest over
the existing extracted data during the transition; the long-term shape
is OG generated entirely locally by the extraction tools (like
data/tiles_original.json already is) and the public repo shipping only
the engine plus clean packs.

The active pack defaults to "og" (full back-compat: every loader behaves
exactly as before the seam was cut) and is switched with
set_active_pack(), e.g. from main.py's --pack option.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = _REPO_ROOT / "content_packs"
LEGACY_DATA_DIR = _REPO_ROOT / "data"

DEFAULT_PACK = "og"


@dataclass(frozen=True)
class Pack:
    name: str
    title: str
    root: Path
    inherits: Optional["Pack"] = None
    legacy_data: bool = False

    def chain(self) -> List["Pack"]:
        packs, p = [], self
        while p is not None:
            packs.append(p)
            p = p.inherits
        return packs

    def resolve(self, filename: str) -> Optional[Path]:
        """Find `filename` in this pack, its ancestors, or (if the chain
        allows it) the legacy data/ directory. Returns None if absent
        everywhere, letting callers keep their own absent-file handling.
        """
        for p in self.chain():
            candidate = p.root / filename
            if candidate.exists():
                return candidate
        if any(p.legacy_data for p in self.chain()):
            candidate = LEGACY_DATA_DIR / filename
            if candidate.exists():
                return candidate
        return None


def available_packs() -> List[str]:
    if not PACKS_DIR.exists():
        return []
    return sorted(p.parent.name for p in PACKS_DIR.glob("*/pack.json"))


def load_pack(name: str, _seen: Optional[set] = None) -> Pack:
    _seen = _seen or set()
    if name in _seen:
        raise ValueError(f"content pack inheritance cycle at {name!r}")
    _seen.add(name)
    root = PACKS_DIR / name
    manifest_path = root / "pack.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"no such content pack {name!r} (looked for {manifest_path}); "
            f"available: {available_packs()}"
        )
    manifest = json.loads(manifest_path.read_text())
    parent = manifest.get("inherits")
    return Pack(
        name=manifest.get("name", name),
        title=manifest.get("title", name),
        root=root,
        inherits=load_pack(parent, _seen) if parent else None,
        legacy_data=bool(manifest.get("legacy_data", False)),
    )


_active: Optional[Pack] = None


def active_pack() -> Pack:
    global _active
    if _active is None:
        _active = load_pack(DEFAULT_PACK)
    return _active


def set_active_pack(name: str) -> Pack:
    global _active
    _active = load_pack(name)
    return _active
