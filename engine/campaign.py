"""Conservative handoff between contiguous, independently checked chapters.

This carries the played result. It deliberately refuses a gap: quiet periods
need their own dated turns or strategic resolver before they can be skipped.
"""
from copy import deepcopy
from datetime import date, timedelta

from . import checker, invariants, runner, state as S


def start(scenario, gmap, seed=0, campaign_id="north_africa"):
    """Begin a campaign at a chapter's historical opening, with its identity in the save."""
    if scenario.get("campaign_only"):
        raise ValueError("This interval must continue a played campaign chapter.")
    if checker.problems(scenario, gmap):
        raise ValueError("The opening chapter scenario fails the structural scenario checker.")
    state = S.new_game(scenario, gmap, seed)
    state["campaign"] = {"id": campaign_id, "history": []}
    return state


def play(chapters, gmap, players, seed=0, check=True, campaign_id="north_africa"):
    """Play contiguous chapters with the same players and the state actually earned.

    Returns the final state and per-chapter order records. A date gap or early
    chapter end is refused until strategic time passage has rules.
    """
    if not chapters:
        raise ValueError("A campaign needs at least one chapter.")
    state = start(chapters[0], gmap, seed, campaign_id)
    records = []
    for index, scenario in enumerate(chapters):
        if index:
            state = handoff(state, chapters[index - 1], scenario, gmap, campaign_id,
                            record=records[-1]["orders"])
        state, record = runner.play(scenario, gmap, players, check=check, initial_state=state)
        records.append({"scenario": scenario["id"], "orders": record})
    return state, records


def handoff(finished, current, following, gmap, campaign_id="north_africa", record=None):
    """Return the next chapter's initial state without rewriting the past.

    Both chapter scenarios must describe every continuing unit by the same id,
    side and type, and by the same name or an explicitly listed remnant name.
    Destroyed and withdrawn formations remain archived in
    the played state but can leave the next chapter's roster. The following
    scenario may introduce new formations.
    Its historical ownership, stocks and placements are for standalone starts;
    the campaign instead keeps the player's actual state. When supplied, the
    chapter's orders become part of the campaign save's history.
    """
    if not finished.get("over") or finished.get("scenario") != current["id"] or finished.get("result") is None:
        raise ValueError("The current chapter must be finished before it can continue.")
    if finished["turn"] != current["turns"] + 1:
        raise ValueError("An early chapter end leaves days that need a strategic time resolver.")
    expected = date.fromisoformat(current["start"]) + timedelta(days=S.turn_days(current) * current["turns"])
    if date.fromisoformat(following["start"]) != expected:
        raise ValueError("Campaign chapters must meet on the next turn; a gap needs its own resolver.")
    if invariants.check(finished, gmap):
        raise ValueError("The finished chapter state fails the engine invariants.")
    if checker.problems(following, gmap):
        raise ValueError("The following chapter scenario fails the structural scenario checker.")
    prior = finished.get("campaign")
    if prior is not None and prior.get("id") != campaign_id:
        raise ValueError("This save belongs to a different campaign.")
    old_specs = {u["id"]: u for u in current["units"]}
    new_specs = {u["id"]: u for u in following["units"]}
    played = {u["id"]: u for u in finished["units"]}
    if not set(old_specs) <= set(played) or any(
            u["id"] not in old_specs and u["status"] not in ("destroyed", "withdrawn")
            for u in finished["units"]):
        raise ValueError("The played roster does not match the chapter's continuing formations.")
    for uid, old in played.items():
        new = new_specs.get(uid)
        if new is None:
            if old["status"] not in ("destroyed", "withdrawn"):
                raise ValueError(f"Active formation {uid} must be described in the next chapter.")
            continue
        if (any(old[key] != new[key] for key in ("id", "side", "type"))
                or (old["name"] != new["name"] and old["name"] not in new.get("alternate_names", []))):
            raise ValueError(f"Formation {uid} changes identity between chapters.")

    next_state = deepcopy(finished)
    fresh = S.new_game(following, gmap, finished["seed"])
    for name, port in fresh["ports"].items():
        if name not in next_state["ports"]:
            next_state["ports"][name] = {"condition": port["condition"], "fuel": 0, "stores": 0}
    for unit in fresh["units"]:
        if unit["id"] in played:
            continue
        next_state["units"].append(unit)
        if unit["status"] == "on_map":
            next_state["sides"][unit["side"]]["brought"] += S.carried(unit)
    next_state["units"].sort(key=lambda u: u["id"])
    history = deepcopy(prior.get("history", [])) if prior else []
    chapter = {"scenario": current["id"], "result": deepcopy(finished["result"]),
               "ended": (expected - timedelta(days=1)).isoformat()}
    if record is not None:
        if not isinstance(record, list) or len(record) != current["turns"]:
            raise ValueError("The completed chapter needs one order record per turn.")
        chapter["orders"] = deepcopy(record)
    history.append(chapter)
    next_state.update(scenario=following["id"], turn=1, over=False, result=None,
                      weather="clear", log=[], mission_reached={},
                      campaign={"id": campaign_id, "history": history})
    next_state.pop("mission_baseline", None)
    baseline = S.mission_baseline(next_state, following)
    if baseline:
        next_state["mission_baseline"] = baseline
    for side in S.SIDES:
        next_state["sides"][side].update(vp=0, kills=0, air="support", interdiction=0, recon=0)
    bad = invariants.check(next_state, gmap)
    if bad:
        raise ValueError("Campaign handoff violates the engine invariants: " + "; ".join(bad))
    return next_state
