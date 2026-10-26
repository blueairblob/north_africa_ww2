"""Counter pictures cut from the artist's first sheets: a stopgap until the pictures come one to a
file (docs/COUNTERS.md). python -m countergen cut writes them to art/counters/artist, where the
screen takes a picture before it takes the drawn one."""
import os

import pygame

from . import GROUND, H, HIGH, OUT, ROOT, W, WIDE

ARTIST = os.path.join(OUT, "artist")
ROWS = ("de", "cw", "it")                                                   # a sheet's rows, top to bottom
COLS = ("foot", "light", "armour", "guns", "antitank", "motorised")         # and its columns
NEAR, SLACK = (190, 495, 825, 1070, 1335), 45       # about where one column ends and the next begins, in sheet pixels
SHEET = "counters_sheet_1_1.png"
KINDS = ("foot", "armour", "guns", "motorised")     # the sheets have no armoured car and no headquarters
ORIGINAL = frozenset({("cw", "armour"), ("cw", "guns")})  # do not recut the Matilda and wrong gun
SINGLE = {("de", "hq"): "axis_hq_cars/german_hq.png",         # one picture to a file
          ("it", "hq"): "axis_hq_cars/it_hq.png"}
OTHER = {("de", "foot"): ("counters_sheet_1.png", "foot"),      # the one German drawn in his own cap
         ("de", "guns"): (SHEET, "antitank")}                   # the sheet's German artillery is an assault gun, not a gun on a carriage


def spans(flags, gap):
    """The stretches where flags are set, joining those less than gap apart."""
    found, start, last = [], None, None
    for i, flag in enumerate(flags):
        if flag:
            if start is not None and i - last > gap:
                found.append((start, last + 1))
                start = i
            start, last = i if start is None else start, i
    return found + ([(start, last + 1)] if start is not None else [])


def largest(img):
    """The picture with all but its largest piece cleared, and trimmed: the sprites on a sheet
    touch, so a cut leaves the tip of a neighbour's gun."""
    step = 3
    ink = pygame.surfarray.array_alpha(img)[::step, ::step] > 40
    seen, best = set(), []
    for start in zip(*ink.nonzero()):
        if start in seen:
            continue
        seen.add(start)
        todo, piece = [start], []
        while todo:
            x, y = todo.pop()
            piece.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
                if 0 <= n[0] < ink.shape[0] and 0 <= n[1] < ink.shape[1] and ink[n] and n not in seen:
                    seen.add(n)
                    todo.append(n)
        best = max(best, piece, key=len)
    keep = ink & False
    for x, y in best:
        keep[max(0, x - 1):x + 2, max(0, y - 1):y + 2] = True
    out = img.copy()
    alpha = pygame.surfarray.pixels_alpha(out)
    alpha[~keep.repeat(step, 0).repeat(step, 1)[:alpha.shape[0], :alpha.shape[1]]] = 0
    del alpha
    return out.subsurface(out.get_bounding_rect()).copy()


def cells(name):
    """Every picture on a sheet, by nation and column."""
    sheet = pygame.image.load(os.path.join(ROOT, "art", name))
    ink = pygame.surfarray.array_alpha(sheet) > 150
    rows = [(y0, y1) for y0, y1 in spans(ink.any(axis=0), 6) if y1 - y0 >= 60]         # shorter: a line of labels
    found = {}
    for nation, (y0, y1) in zip(ROWS, rows):
        full = ink[:, y0:y1].sum(axis=1)
        cuts = [0] + [min(range(x - SLACK, x + SLACK), key=lambda c: (full[c], abs(c - x))) for x in NEAR] + [sheet.get_width()]
        for col, x0, x1 in zip(COLS, cuts, cuts[1:]):
            found[nation, col] = largest(sheet.subsurface((x0, y0, x1 - x0, y1 - y0)).copy())
    return found


def cut_out(name):
    """A picture alone in its file, trimmed to its largest piece. One on real transparency is taken
    as it is; on a pale checkerboard painted into the file, the pale ground joined to the edges
    is cleared first."""
    flat = pygame.image.load(os.path.join(ROOT, "art", name))
    img = pygame.Surface(flat.get_size(), pygame.SRCALPHA)
    img.blit(flat, (0, 0))
    w, h = img.get_size()
    corners = ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
    if all(img.get_at(c).a == 0 for c in corners):
        ground = pygame.mask.from_surface(img, 40)
    else:
        pale = pygame.mask.from_threshold(img, (246, 246, 246, 255), (22, 22, 22, 255))
        ground = pygame.mask.Mask(img.get_size())
        for corner in corners:
            if pale.get_at(corner) and not ground.get_at(corner):
                ground.draw(pale.connected_component(corner), (0, 0))
        ground.invert()
    pic = ground.connected_component().to_surface(setsurface=img, unsetcolor=(0, 0, 0, 0))
    return pic.subsurface(pic.get_bounding_rect()).copy()


def fitted(pic, kind):
    """A picture on the canvas the drawn ones use: as large as the room allows, centred, standing on
    the ground. One man is too small to read, so the infantry is three of him in file."""
    if kind == "foot":
        one, pic = pic, pygame.Surface((pic.get_width() * 3, pic.get_height()), pygame.SRCALPHA)
        for n in range(3):
            pic.blit(one, (n * one.get_width(), 0))
    k = min(WIDE / pic.get_width(), HIGH / pic.get_height())
    pic = pygame.transform.smoothscale(pic, (int(pic.get_width() * k), int(pic.get_height() * k)))
    canvas = pygame.Surface((W, H), pygame.SRCALPHA)
    canvas.blit(pic, pic.get_rect(midbottom=(W // 2, GROUND)))
    return canvas


def write():
    os.makedirs(ARTIST, exist_ok=True)
    sheets = {}
    for nation in ROWS:
        for kind in KINDS:
            if (nation, kind) in ORIGINAL:
                continue  # original painted Crusader and 25-pounder replace wrong-subject sheet cuts
            name, col = OTHER.get((nation, kind), (SHEET, kind))
            if name not in sheets:
                sheets[name] = cells(name)
            new = os.path.join(ARTIST, f"{nation}_{kind}.new.png")
            pygame.image.save(fitted(sheets[name][nation, col], kind), new)
            os.replace(new, os.path.join(ARTIST, f"{nation}_{kind}.png"))
    for (nation, kind), name in SINGLE.items():
        new = os.path.join(ARTIST, f"{nation}_{kind}.new.png")
        pygame.image.save(fitted(cut_out(name), kind), new)
        os.replace(new, os.path.join(ARTIST, f"{nation}_{kind}.png"))
    return ARTIST
