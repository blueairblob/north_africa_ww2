"""The counter pictures (art/counters): the saved files are what countergen draws, and every unit has one."""
import glob
import os
from collections import defaultdict
from pathlib import Path

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


def test_three_painted_armoured_cars_are_distinct_from_carrier_and_each_other():
    from pathlib import Path
    from screen.draw import Painter
    from helpers import GMAP
    painter = Painter(GMAP)
    images = [painter.sprite(nation, "recon", (43, 26)) for nation in ("cw", "de", "it")]
    carrier = painter.sprite("cw", "recon", (43, 26), "carrier")
    assert all(images) and carrier is not None
    assert len({pygame.image.tostring(image, "RGBA") for image in images + [carrier]}) == 4
    root = Path(__file__).resolve().parent.parent / "art" / "counters" / "artist"
    for nation in ("cw", "de", "it"):
        image = pygame.image.load(str(root / f"{nation}_recon.png"))
        box = image.get_bounding_rect()
        assert image.get_size() == (C.W, C.H) and box.bottom == C.GROUND
        assert box.w <= C.WIDE and box.h <= C.HIGH and image.get_at((0, 0)).a == 0


def test_crusader_formations_choose_distinct_representative_armour_art():
    from engine import scenarios
    from helpers import GMAP
    from screen.app import App
    from screen.draw import Painter
    from screen.session import Session

    s = Session(scenarios.load("crusader"), GMAP, humans=["cw"])
    assert {uid: s.counter_art.get(uid) for uid in (306, 307, 311, 312, 313)} == {
        306: "matilda", 307: "matilda", 311: "stuart", 312: "a13", 313: None}
    assert Session.from_save(s.to_save(), GMAP).counter_art == s.counter_art
    legacy = s.to_save()
    for spec in legacy["scenario"]["units"]:
        spec.pop("counter_art", None)
    assert Session.from_save(legacy, GMAP).counter_art == s.counter_art
    assert s.counter_art[335] == "carrier"
    assert s.counter_art[183] == "bersaglieri"
    assert all(s.counter_art.get(uid) is None for uid in (141, 142, 152, 163, 171, 172))
    assert s.counter_art.get(305) is None  # wheeled British armoured cars are not carriers
    assert {uid: s.counter_art.get(uid) for uid in (104, 106, 113, 123, 125, 134)} == {
        104: "flak88", 106: None, 113: None, 123: None, 125: "antitank", 134: None}
    painter = Painter(GMAP)
    sprites = {kind: painter.sprite("cw", "armour", (100, 60), kind)
               for kind in (None, "matilda", "stuart", "a13")}
    assert all(sprites.values())
    assert len({pygame.image.tostring(image, "RGBA") for image in sprites.values()}) == 4
    carrier = painter.sprite("cw", "recon", (100, 60), "carrier")
    cars = painter.sprite("cw", "recon", (100, 60))
    assert carrier is not None and cars is not None
    assert pygame.image.tostring(carrier, "RGBA") != pygame.image.tostring(cars, "RGBA")
    axis_guns = {variant: painter.sprite("de", "guns", (100, 60), variant)
                 for variant in (None, "flak88", "antitank")}
    assert all(axis_guns.values())
    assert len({pygame.image.tostring(image, "RGBA") for image in axis_guns.values()}) == 3
    bersaglieri = painter.sprite("it", "foot", (100, 60), "bersaglieri")
    regular = painter.sprite("it", "foot", (100, 60))
    assert bersaglieri is not None and regular is not None
    assert pygame.image.tostring(bersaglieri, "RGBA") != pygame.image.tostring(regular, "RGBA")

    app = App(s, size=(900, 560))
    selected = []
    original = app.painter.sprite

    def record(nation, kind, size, variant=None):
        selected.append((nation, kind, variant))
        return original(nation, kind, size, variant)

    app.painter.sprite = record
    for uid, variant in ((306, "matilda"), (311, "stuart"), (312, "a13"), (313, None)):
        selected.clear()
        app.ui.selected = uid
        app.paint(pygame.Surface(app.size))
        assert ("cw", "armour", variant) in selected
    selected.clear()
    app.ui.selected = 335
    app.paint(pygame.Surface(app.size))
    assert ("cw", "recon", "carrier") in selected
    axis_app = App(Session(scenarios.load("crusader"), GMAP, humans=["axis"]), size=(900, 560))
    axis_app.painter.sprite = record
    for uid, variant in ((104, "flak88"), (113, None), (125, "antitank")):
        selected.clear()
        axis_app.ui.selected = uid
        axis_app.paint(pygame.Surface(axis_app.size))
        assert ("de", "guns", variant) in selected
    selected.clear()
    axis_app.ui.selected = 183
    axis_app.paint(pygame.Surface(axis_app.size))
    assert ("it", "foot", "bersaglieri") in selected


def test_every_painted_variant_has_a_transparent_fitted_canvas():
    from pathlib import Path
    for name in ("art/counters/artist/cw_armour.png", "art/counters/artist/cw_guns.png",
                 "art/counters/variants/cw_matilda.png",
                 "art/counters/variants/cw_stuart.png", "art/counters/variants/cw_a13.png",
                 "art/counters/variants/cw_carrier.png", "art/counters/variants/it_bersaglieri.png",
                 "art/counters/artist/de_guns.png", "art/counters/variants/de_flak88.png",
                 "art/counters/variants/de_antitank.png"):
        im = pygame.image.load(str(Path(__file__).parent.parent / name))
        box = im.get_bounding_rect()
        assert im.get_size() == (C.W, C.H)
        assert box.w <= C.WIDE and box.h <= C.HIGH and abs(box.centerx - C.W / 2) <= 2
        assert box.bottom == C.GROUND
        assert im.get_at((0, 0)).a == 0


def test_sheet_cutter_protects_the_original_replacement_subjects():
    from countergen.cut import ORIGINAL
    assert ORIGINAL == {("cw", "armour"), ("cw", "foot"), ("cw", "guns"), ("cw", "motorised"),
                        ("de", "armour"), ("de", "foot"), ("de", "guns"), ("de", "motorised"),
                        ("it", "armour"), ("it", "foot"), ("it", "guns"),
                        ("it", "motorised")}


def test_every_explicit_scenario_art_variant_has_an_asset():
    from pathlib import Path
    from engine import scenarios
    from screen.session import LEGACY_CRUSADER_ART

    artist = Path(__file__).resolve().parent.parent / "art" / "counters" / "artist"
    variants = Path(__file__).resolve().parent.parent / "art" / "counters" / "variants"
    for name in scenarios.names():
        for u in scenarios.load(name)["units"]:
            nation = u.get("nation", "cw" if u["side"] == "cw" else "de")
            assert (artist / f"{nation}_{u['type']}.png").exists(), (name, u["id"])
            if "counter_art" in u:
                assert (variants / f"{nation}_{u['counter_art']}.png").exists(), (name, u["id"])
    for (uid, unit_name), variant in LEGACY_CRUSADER_ART.items():
        unit = next(u for u in scenarios.load("crusader")["units"]
                    if (u["id"], u["name"]) == (uid, unit_name))
        nation = unit.get("nation", "cw" if unit["side"] == "cw" else "de")
        assert (variants / f"{nation}_{variant}.png").exists(), (uid, variant)


def test_counter_audit_accounts_for_each_crusader_unit_and_art_selector():
    """Audit coverage is checked; historical accuracy still needs dated sources."""
    from engine import scenarios

    expected = defaultdict(list)
    for u in scenarios.load("crusader")["units"]:
        nation = u.get("nation", "cw" if u["side"] == "cw" else "de")
        expected[nation, u["type"], u.get("counter_art", "default")].append(u["id"])

    audit = Path(__file__).resolve().parent.parent / "docs" / "COUNTER_AUDIT.md"
    actual = {}
    for line in audit.read_text().splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) != 8 or cells[1] not in C.NATIONS:
            continue
        nation, kind, variant = cells[1:4]
        assert kind in C.KINDS
        ids = [int(uid.strip()) for uid in cells[4].split(",")]
        key = nation, kind, variant
        assert key not in actual, key
        actual[key] = ids
    assert len(actual) == 25
    assert actual == dict(expected)
