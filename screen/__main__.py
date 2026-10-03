"""Play a scenario at the screen.

    python -m screen crusader                       two players at one screen
    python -m screen crusader --axis nothing        you are the Commonwealth
    python -m screen crusader --shot frame.png      draw one frame to a file, with no window
"""
import argparse
import json
import os
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
KINDS = ("human", "nothing", "attack", "retreat", "explore")


def main(argv):
    p = argparse.ArgumentParser(prog="python -m screen", description="Benghazi Handicap at the screen.")
    p.add_argument("scenario")
    p.add_argument("--axis", choices=KINDS, default="human")
    p.add_argument("--cw", choices=KINDS, default="human")
    p.add_argument("--shot", metavar="FILE", help="draw one frame to FILE and stop")
    p.add_argument("--zoom", type=float, default=1.0, help="the zoom, for --shot (1 is 64 pixels to the hex)")
    p.add_argument("--at", default="Tobruk", help="the place to centre on, for --shot")
    p.add_argument("--overlay", default="", help="overlays for --shot: s, z or sz")
    p.add_argument("--select", type=int, help="the unit selected, for --shot")
    a = p.parse_args(argv)
    if a.shot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from engine import checker
    from engine.players import SCRIPTED as PLAYERS
    from engine.gamemap import GameMap

    from .app import App
    from .session import Session

    gmap = GameMap(json.loads((DATA / "map.json").read_text()))
    scenario = json.loads((DATA / "scenarios" / f"{a.scenario}.json").read_text())
    wrong = checker.problems(scenario, gmap)
    if wrong:
        sys.exit("\n".join(wrong))
    kinds = {"axis": a.axis, "cw": a.cw}
    humans = [s for s in kinds if kinds[s] == "human"]
    if not humans:
        sys.exit("At least one side must be human. To watch two scripted players with no screen:\n"
                 f"    python -m engine {a.scenario} {a.axis} {a.cw}")
    session = Session(scenario, gmap, humans, {s: PLAYERS[k](gmap) for s, k in kinds.items() if k != "human"})
    app = App(session)
    if not a.shot:
        return app.run()
    pygame.init()
    app.ui.zoom = a.zoom
    app.ui.overlays, app.ui.selected = set(a.overlay), a.select
    app.centre_on(gmap.places[a.at]["hex"])
    surface = pygame.Surface(app.size)
    app.paint(surface)
    pygame.image.save(surface, a.shot)
    print(f"wrote {a.shot}")


main(sys.argv[1:])
