"""Objectives, losses and the result (docs/RULES.md §13)."""
from . import state as S

LOSS_VP = 2             # points to the enemy per size of a unit destroyed (13.4)
GRADES = ("tactical", "major", "decisive")


def unit_lost(state, u):
    state["sides"][S.enemy(u["side"])]["vp"] += u["size"] * LOSS_VP          # 13.4


def victory_phase(state, scenario):
    last = state["turn"] >= scenario["turns"]
    for obj in scenario["objectives"]:
        side = state["sides"][state["places"][obj["place"]]]
        side["vp"] += obj.get("turn", 0)                                     # 13.2
        if last:
            side["vp"] += obj.get("end", 0)                                  # 13.3
    gone = [s for s in S.SIDES if not any(u["side"] == s and u["status"] in ("on_map", "not_arrived")
                                          for u in state["units"])]
    if last or gone:                                                         # 13.5
        state["over"] = True
        d = state["sides"]["axis"]["vp"] - state["sides"]["cw"]["vp"]        # 13.6
        grade = sum(abs(d) >= t for t in scenario["thresholds"])
        state["result"] = {"winner": None if grade == 0 else ("axis" if d > 0 else "cw"),
                           "grade": "draw" if grade == 0 else GRADES[grade - 1], "margin": d}
    state["turn"] += 1                                                       # 13.7
