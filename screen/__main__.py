"""Play a scenario at the screen.

    python -m screen crusader                       two players at one screen
    python -m screen crusader --axis nothing        you are the Commonwealth
    python -m screen sidi_rezegh --axis computer    command the Commonwealth against the computer
    python -m screen sidi_rezegh --cw computer      command the Axis against the computer
    python -m screen sidi_rezegh --axis computer --cw computer   watch both computers play
    python -m screen sidi_rezegh --axis computer-easy --cw computer-hard   compare difficulty levels
    python -m screen crusader --shot frame.png      draw one frame to a file, with no window
    python -m screen crusader --log                 record what every click and key did, under logs/
    python -m screen crusader --seed 1941           the weather of an earlier game again; --seed 0 for none
    python -m screen --load                         go on with the game saved last (saves/)
    python -m screen --load saves/FILE.json         go on with that one
    python -m screen --trial compass_opening --axis computer-hard   review the 1940 research draft
    python -m screen                                open the review menu
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from .paths import ROOT, user_folder
from . import theme as T

DATA = ROOT / "data"
DRAFTS = DATA / "scenario_drafts"
KINDS = ("human", "computer-easy", "computer", "computer-hard", "nothing", "attack", "retreat", "explore")


def main(argv):
    p = argparse.ArgumentParser(prog="python -m screen", description="Benghazi Handicap at the screen.")
    p.add_argument("scenario", nargs="?")
    p.add_argument("--trial", metavar="NAME", help="open a research draft for playtesting; linked drafts are outside New battle")
    p.add_argument("--axis", choices=KINDS, default="human")
    p.add_argument("--cw", choices=KINDS, default="human")
    p.add_argument("--shipping", choices=("baseline", "less_interdiction", "more_interdiction"),
                   default="baseline", help="experimental Axis sea-delivery assumption")
    p.add_argument("--load", metavar="FILE", nargs="?", const="", help="go on with a saved game: FILE, or with none "
                   "given the one saved last. The scenario and who plays come from the save")
    p.add_argument("--shot", metavar="FILE", help="draw the menu, or a named scenario frame, to FILE and stop")
    p.add_argument("--zoom", type=float, default=1.0, help="the zoom, for --shot (1 is 64 pixels to the hex)")
    p.add_argument("--at", default="Tobruk", help="the place to centre on, for --shot")
    p.add_argument("--overlay", default="", help="overlays for --shot: s, z or sz")
    p.add_argument("--select", type=int, help="the unit selected, for --shot")
    p.add_argument("--log", metavar="FILE", nargs="?", const="", help="record what every click and key did, to find a "
                   "fault; with no FILE, in a file named by the date and time under logs/")
    p.add_argument("--seed", type=int, help="the number the weather is drawn from: the same number gives the same "
                   "weather; 0 for no weather. With none given, one is taken from the clock")
    a = p.parse_args(argv)
    if a.trial and (a.scenario or a.load is not None):
        p.error("--trial cannot be combined with a named scenario or --load")
    review_menu = a.load is None and a.scenario is None and a.trial is None
    if review_menu:
        a.scenario, a.axis, a.cw = "sidi_rezegh", "computer", "human"
    if a.shot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from engine import campaign, checker, scenarios, scenario_options
    from engine.players import SCRIPTED as PLAYERS
    from engine.gamemap import GameMap

    from . import saves
    from . import preferences
    from .app import App
    from .session import Session

    gmap = GameMap(json.loads((DATA / "map.json").read_text()))
    options = preferences.read(user_folder("preferences.json")) if not a.shot else dict(preferences.DEFAULTS)
    window_size = tuple(options["window"]) if not a.shot else None
    loaded_from = None
    if a.load is not None:                            # a saved game: the scenario, the players and the weather are in it
        path = Path(a.load) if a.load else saves.newest()
        if path is None:
            sys.exit(f"No games have been saved yet in {saves.FOLDER}")
        try:
            session = saves.read(path, gmap)
        except ValueError as e:
            sys.exit(f"{path}: {e}")
        kinds = {s: "human" if s in session.humans else session.to_save()["scripted"][s] for s in ("axis", "cw")}
        loaded_from = path
        a.scenario, seed = session.scenario["id"], session.state["seed"]
        app = App(session, size=window_size or T.WINDOW)
        app.ui.message = "Loaded: " + saves.about(session.to_save()) + ".   " + app.left_words()
        print(f"Going on with {path}")
    else:
        if a.trial:
            if a.trial not in scenarios.names(DRAFTS):
                sys.exit(f"no research trial {a.trial}; there are: {', '.join(scenarios.names(DRAFTS))}")
            a.scenario = a.trial
            selected = scenarios.load(a.trial, DRAFTS)
        else:
            if a.scenario not in scenarios.names():
                sys.exit(f"no scenario {a.scenario}; there are: {', '.join(scenarios.names())}")
            selected = scenarios.load(a.scenario)
        if selected.get("campaign_only"):
            sys.exit(f"{selected['name']} must continue a played campaign chapter")
        scenario = scenario_options.apply(selected, a.shipping)
        wrong = checker.problems(scenario, gmap)
        if wrong:
            sys.exit("\n".join(wrong))
        kinds = {"axis": a.axis, "cw": a.cw}
        humans = [s for s in kinds if kinds[s] == "human"]
        seed = a.seed if a.seed is not None else 0 if a.shot else int(time.time() * 1000) % 2147483646 + 1
        initial = campaign.start(scenario, gmap, seed) if a.trial and scenario.get("research_next") else None
        session = Session(scenario, gmap, humans, {s: PLAYERS[k](gmap) for s, k in kinds.items() if k != "human"},
                          seed, initial_state=initial)
        app = App(session, size=window_size or T.WINDOW,
                  review_menu=review_menu)
        if not a.shot:                                # the one thing not in the orders: say it, so the game can be had again
            print(f"Weather seed {seed}" + ("" if seed else ": no weather") + f"   (the same game again: --seed {seed})")
    if not a.shot:
        app.saves = saves.FOLDER                      # saved when asked, each time orders are handed in, and on leaving
        app.settings_path = user_folder("preferences.json")
        app.apply_options(options)
    if a.log is not None:
        path = Path(a.log) if a.log else user_folder("logs") / time.strftime("play-%Y%m%d-%H%M%S.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        app.log = open(path, "w", encoding="utf-8")
        app.log.write(f"scenario {a.scenario} | axis {kinds['axis']} | cw {kinds['cw']} | seed {seed}"
                      + (f" | loaded from {loaded_from}" if loaded_from is not None else "") + "\n")
        print(f"Recording this sitting in {path}")
    if not a.shot:
        app.title = not review_menu
        return app.run()
    pygame.init()
    app.ui.zoom = a.zoom
    app.ui.overlays, app.ui.selected = set(a.overlay), a.select
    app.centre_on(gmap.places[a.at]["hex"])
    surface = pygame.Surface(app.size)
    app.paint(surface)
    pygame.image.save(surface, a.shot)
    print(f"wrote {a.shot}")


if __name__ == "__main__":
    main(sys.argv[1:])
