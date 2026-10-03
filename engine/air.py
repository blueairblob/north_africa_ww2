"""The air effort: one choice per side per turn (docs/RULES.md §7)."""
from . import state as S

AIR_SUPPORT_PCT = 5     # per cent on combat totals per air point
AIR_INTERDICT_PCT = 5   # per cent off enemy lift per air point
AIR_RECON_HEXES = 1     # extra spotting range per air point


def air_phase(state, scenario, ctx):
    for side in S.SIDES:
        choice = ctx["air"][side]
        points = S.side_value(scenario, side, "air", state["turn"])          # 7.2
        state["sides"][side]["air"] = choice
        ctx["support"][side] = AIR_SUPPORT_PCT * points if choice == "support" else 0            # 7.3
        state["sides"][S.enemy(side)]["interdiction"] = (
            AIR_INTERDICT_PCT * points if choice == "interdict" else 0)                          # 7.4
        state["sides"][side]["recon"] = AIR_RECON_HEXES * points if choice == "recon" else 0     # 7.5
