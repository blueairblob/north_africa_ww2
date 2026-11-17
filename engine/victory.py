"""Objectives, losses and the result (docs/RULES.md §13)."""
from . import state as S
from . import mission as M

LOSS_VP = 5             # points to the enemy per size of a unit destroyed (13.4)
GRADES = ("tactical", "major", "decisive")


def unit_lost(state, u):
    side = state["sides"][S.enemy(u["side"])]                                # 13.4
    side["vp"] += u["size"] * LOSS_VP
    side["kills"] += u["size"] * LOSS_VP


def par(scenario):
    """The Axis lead in points if both sides hold to the end what they hold at the start (13.6)."""
    lead = 0
    for obj in scenario["objectives"]:
        points = obj.get("turn", 0) * scenario["turns"] + obj.get("end", 0)
        lead += points if obj["place"] in scenario["owners"]["axis"] else -points
    return lead


def result_for(state, scenario, gmap=None):
    """Score the finished position; executable orders take precedence over points."""
    d = state["sides"]["axis"]["vp"] - state["sides"]["cw"]["vp"] - scenario.get("par", 0)
    grade = sum(abs(d) >= t for t in scenario["thresholds"])
    result = {"winner": None if grade == 0 else ("axis" if d > 0 else "cw"),
              "grade": "draw" if grade == 0 else GRADES[grade - 1], "margin": d}
    mission = scenario.get("mission", {})
    if mission:
        if gmap is None:
            raise ValueError("mission scoring needs the scenario map")
        checks = M.assessment(state, scenario, gmap)
        success = [side for side in S.SIDES if mission.get(side, {}).get("success_grade") and checks[side]["complete"]]
        contests = any(mission.get(side, {}).get("success_grade") for side in S.SIDES)
        if contests:
            winner = success[0] if len(success) == 1 else None
            points_winner, points_grade = result["winner"], result["grade"]
            result["winner"] = winner
            result["grade"] = "draw" if winner is None else GRADES[max(
                GRADES.index(mission[winner]["success_grade"]),
                GRADES.index(points_grade) if points_winner == winner else -1)]
        for side in S.SIDES:
            spec = mission.get(side, {})
            if spec.get("failure_grade") and not checks[side]["complete"]:
                winner = S.enemy(side)
                floor = GRADES.index(spec["failure_grade"])
                existing = GRADES.index(result["grade"]) if result["winner"] == winner else -1
                result.update(winner=winner, grade=GRADES[max(floor, existing)])
        result["mission"] = {"checks": checks, "decides": contests or any(
            mission.get(side, {}).get("failure_grade") and not checks[side]["complete"] for side in S.SIDES)}
    if scenario.get("campaign_finale") and state.get("campaign") and state["turn"] >= scenario["turns"]:
        result = campaign_result(state, result)
    return result


def campaign_result(state, chapter_result):
    """Judge the whole trial's final strategic position and report the played history."""
    result = dict(chapter_result)
    places = state["places"]
    egypt = all(places[name] == "cw" for name in ("Alexandria", "El Alamein"))
    if places["Alexandria"] == "axis":
        winner, grade, reason = "axis", "decisive", "Axis forces hold Alexandria."
    elif all(places[name] == "axis" for name in ("El Alamein", "Mersa Matruh")):
        winner, grade, reason = "axis", "major", "Axis forces hold the Alamein and Matruh approaches."
    elif egypt and all(places[name] == "cw" for name in ("Tobruk", "Sidi Barrani")):
        winner = "cw"
        grade = "decisive" if places["Benghazi"] == "cw" else "major"
        reason = ("Commonwealth forces secure Egypt, Tobruk and the frontier"
                  + (" and hold Benghazi." if grade == "decisive" else "."))
    elif egypt and places["Tobruk"] == "cw":
        winner, grade, reason = "cw", "tactical", "Commonwealth forces retain Egypt and Tobruk."
    elif places["Tobruk"] == places["Bardia"] == "axis":
        winner, grade, reason = "axis", "tactical", "Axis forces retain Tobruk and the Libyan frontier."
    else:
        winner, grade, reason = None, "draw", "Neither side holds all of its final strategic objectives."
    chapters = [h["result"] for h in state["campaign"].get("history", [])] + [chapter_result]
    missions = {side: sum(bool(r.get("mission", {}).get("checks", {}).get(side, {}).get("complete"))
                          for r in chapters) for side in S.SIDES}
    summary = {
        "reason": reason,
        "chapters": len(chapters),
        "missions_met": missions,
        "places": {name: places[name] for name in ("Alexandria", "El Alamein", "Mersa Matruh",
                                                  "Sidi Barrani", "Bardia", "Tobruk", "Benghazi", "El Agheila")},
        "surviving_steps": {side: sum(u["steps"] for u in S.on_map(state, side)) for side in S.SIDES},
        "supply_tonnes": {side: S.holdings(state, side) for side in S.SIDES},
    }
    result.update(winner=winner, grade=grade, campaign=summary)
    return result


def victory_phase(state, scenario, gmap=None):
    last = state["turn"] >= scenario["turns"]
    for obj in scenario["objectives"]:
        side = state["sides"][state["places"][obj["place"]]]
        side["vp"] += obj.get("turn", 0)                                     # 13.2
        if last:
            side["vp"] += obj.get("end", 0)                                  # 13.3
    gone = [s for s in S.SIDES if not any(u["side"] == s and u["status"] in ("on_map", "not_arrived")
                                          for u in state["units"])]
    if gmap is not None:
        M.record_reached(state, scenario, gmap)
    if last or (gone and not state.get("campaign")):                         # 13.5; linked chapters keep their dated boundary
        state["over"] = True
        state["result"] = result_for(state, scenario, gmap)                   # 13.6
    state["turn"] += 1                                                       # 13.7
