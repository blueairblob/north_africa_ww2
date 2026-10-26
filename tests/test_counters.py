"""The counter pictures (art/counters): the saved files are what countergen draws, and every unit has one."""
import glob
import os

import pygame

import countergen as C


def test_saved_drawings_are_what_the_generator_writes():
    for nation in C.NATIONS:
        for kind in C.KINDS:
            with open(C.path(nation, kind, "svg")) as f:
                assert f.read() == C.svg(nation, kind), (nation, kind)


def test_every_picture_is_the_size_of_the_canvas_on_a_clear_ground():
    for nation in C.NATIONS:
        for kind in C.KINDS:
            img = pygame.image.load(C.path(nation, kind, "png"))
            assert img.get_size() == (C.W, C.H), (nation, kind)
            box = img.get_bounding_rect()                               # the part that is not clear
            assert all(img.get_at(corner)[3] == 0 for corner in ((0, 0), (C.W - 1, 0), (0, C.H - 1), (C.W - 1, C.H - 1)))
            assert box.w <= C.WIDE + 2 * C.LINE and box.w >= C.W * 0.7, (nation, kind, box.w)
            assert abs(box.centerx - C.W / 2) <= 2 and abs(box.bottom - C.GROUND) <= C.LINE, (nation, kind, box)


def test_every_unit_in_every_scenario_has_a_picture():
    from engine import scenarios
    for name in scenarios.names():
        for u in scenarios.load(name)["units"]:
            nation = u.get("nation", "cw" if u["side"] == "cw" else "de")           # as screen.session has it
            assert os.path.exists(C.path(nation, u["type"], "png")), (name, u["id"])


def test_a_picture_from_the_artist_fits_the_same_canvas_and_stands_on_the_same_ground():
    from countergen import cut
    for name in sorted(glob.glob(os.path.join(cut.ARTIST, "*.png"))):
        img = pygame.image.load(name)
        box = img.get_bounding_rect()
        assert img.get_size() == (C.W, C.H) and os.path.basename(name)[:-4].split("_", 1)[1] in C.KINDS, name
        assert box.w <= C.WIDE and box.h <= C.HIGH and abs(box.centerx - C.W / 2) <= 2 and box.bottom == C.GROUND, (name, box)


def test_crusader_formations_choose_distinct_representative_armour_art():
    from engine import scenarios
    from helpers import GMAP
    from screen.app import App
    from screen.draw import Painter
    from screen.session import Session

    s = Session(scenarios.load("crusader"), GMAP, humans=["cw"])
    assert {uid: s.counter_art.get(uid) for uid in (306, 307, 311, 312, 313)} == {
        306: "matilda", 307: "matilda", 311: "stuart", 312: None, 313: None}
    assert Session.from_save(s.to_save(), GMAP).counter_art == s.counter_art
    legacy = s.to_save()
    for spec in legacy["scenario"]["units"]:
        spec.pop("counter_art", None)
    assert Session.from_save(legacy, GMAP).counter_art == s.counter_art
    painter = Painter(GMAP)
    sprites = {kind: painter.sprite("cw", "armour", (100, 60), kind) for kind in (None, "matilda", "stuart")}
    assert all(sprites.values())
    assert len({pygame.image.tostring(image, "RGBA") for image in sprites.values()}) == 3

    app = App(s, size=(900, 560))
    selected = []
    original = app.painter.sprite

    def record(nation, kind, size, variant=None):
        selected.append((nation, kind, variant))
        return original(nation, kind, size, variant)

    app.painter.sprite = record
    for uid, variant in ((306, "matilda"), (311, "stuart"), (312, None)):
        selected.clear()
        app.ui.selected = uid
        app.paint(pygame.Surface(app.size))
        assert ("cw", "armour", variant) in selected


def test_every_armour_variant_has_a_transparent_fitted_canvas():
    from pathlib import Path
    for name in ("art/counters/artist/cw_armour.png", "art/counters/artist/cw_guns.png",
                 "art/counters/variants/cw_matilda.png",
                 "art/counters/variants/cw_stuart.png"):
        im = pygame.image.load(str(Path(__file__).parent.parent / name))
        box = im.get_bounding_rect()
        assert im.get_size() == (C.W, C.H)
        assert box.w <= C.WIDE and box.h <= C.HIGH and abs(box.centerx - C.W / 2) <= 2
        assert box.bottom == C.GROUND
        assert im.get_at((0, 0)).a == 0


def test_sheet_cutter_protects_the_original_replacement_subjects():
    from countergen.cut import ORIGINAL
    assert ORIGINAL == {("cw", "armour"), ("cw", "guns")}
