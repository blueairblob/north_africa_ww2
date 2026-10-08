"""Play a scenario at the screen.

    python -m screen crusader                       two players at one screen
    python -m screen crusader --axis nothing        you are the Commonwealth
    python -m screen crusader --shot frame.png      draw one frame to a file, with no window
    python -m screen crusader --log                 record what every click and key did, under logs/
    python -m screen crusader --seed 1941           the weather of an earlier game again; --seed 0 for none
    python -m screen --load                         go on with the game saved last (saves/)
    python -m screen --load saves/FILE.json         go on with that one
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
KINDS = ("human", "nothing", "attack", "retreat", "explore")


def main(argv):
    p = argparse.ArgumentParser(prog="python -m screen", description="Benghazi Handicap at the screen.")
    p.add_argument("scenario", nargs="?")
    p.add_argument("--axis", choices=KINDS, default="human")
    p.add_argument("--cw", choices=KINDS, default="human")
    p.add_argument("--load", metavar="FILE", nargs="?", const="", help="go on with a saved game: FILE, or with none "
                   "given the one saved last. The scenario and who plays come from the save")
    p.add_argument("--shot", metavar="FILE", help="draw one frame to FILE and stop")
    p.add_argument("--zoom", type=float, default=1.0, help="the zoom, for --shot (1 is 64 pixels to the hex)")
    p.add_argument("--at", default="Tobruk", help="the place to centre on, for --shot")
    p.add_argument("--overlay", default="", help="overlays for --shot: s, z or sz")
    p.add_argument("--select", type=int, help="the unit selected, for --shot")
    p.add_argument("--log", metavar="FILE", nargs="?", const="", help="record what every click and key did, to find a "
                   "fault; with no FILE, in a file named by the date and time under logs/")
    p.add_argument("--seed", type=int, help="the number the weather is drawn from: the same number gives the same "
                   "weather; 0 for no weather. With none given, one is taken from the clock")
    a = p.parse_args(argv)
    if a.load is None and not a.scenario:
        p.error("name a scenario, or go on with a saved game with --load")
    if a.shot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from engine import checker
    from engine.players import SCRIPTED as PLAYERS
    from engine.gamemap import GameMap

    from . import saves
    from .app import App
    from .session import Session

    gmap = GameMap(json.loads((DATA / "map.json").read_text()))
    if a.load is not None:                            # a saved game: the scenario, the players and the weather are in it
        path = Path(a.load) if a.load else saves.newest()
        if path is None:
            sys.exit(f"No games have been saved yet in {saves.FOLDER}")
        try:
            session = saves.read(path, gmap)
        except ValueError as e:
            sys.exit(f"{path}: {e}")
        kinds = {s: "human" if s in session.humans else session.to_save()["scripted"][s] for s in ("axis", "cw")}
        a.scenario, seed = session.scenario["id"], session.state["seed"]
        app = App(session)
        app.ui.message = "Loaded: " + saves.about(session.to_save()) + ".   " + app.left_words()
        print(f"Going on with {path}")
    else:
        scenario = json.loads((DATA / "scenarios" / f"{a.scenario}.json").read_text())
        wrong = checker.problems(scenario, gmap)
        if wrong:
            sys.exit("\n".join(wrong))
        kinds = {"axis": a.axis, "cw": a.cw}
        humans = [s for s in kinds if kinds[s] == "human"]
        if not humans:
            sys.exit("At least one side must be human. To watch two scripted players with no screen:\n"
                     f"    python -m engine {a.scenario} {a.axis} {a.cw}")
        seed = a.seed if a.seed is not None else 0 if a.shot else int(time.time() * 1000) % 2147483646 + 1
        session = Session(scenario, gmap, humans, {s: PLAYERS[k](gmap) for s, k in kinds.items() if k != "human"}, seed)
        app = App(session)
        if not a.shot:                                # the one thing not in the orders: say it, so the game can be had again
            print(f"Weather seed {seed}" + ("" if seed else ": no weather") + f"   (the same game again: --seed {seed})")
    if not a.shot:
        app.saves = saves.FOLDER                      # saved when asked, each time orders are handed in, and on leaving
    if a.log is not None:
        path = Path(a.log) if a.log else Path(__file__).parent.parent / "logs" / time.strftime("play-%Y%m%d-%H%M%S.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        app.log = open(path, "w", encoding="utf-8")
        app.log.write(f"scenario {a.scenario} | axis {kinds['axis']} | cw {kinds['cw']} | seed {seed}"
                      + (f" | loaded from {path}" if a.load is not None else "") + "\n")
        print(f"Recording this sitting in {path}")
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
