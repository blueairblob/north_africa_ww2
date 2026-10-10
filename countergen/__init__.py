"""The counter pictures: one for each nation and kind of unit, drawn from a few shapes
(docs/COUNTERS.md). Each is a side view facing right, in a few flat tones with one bold outline,
made to be told from the others at 36 pixels wide. python -m countergen writes them to
art/counters, as an SVG drawing and as the PNG the screen loads."""
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "counters")
W, H = 480, 288             # the canvas: 5:3, the top of a counter
GROUND = 248                # the line that wheels, tracks and boots stand on
WIDE, HIGH = 410, 214       # the most of the canvas a picture may fill
LINE = 9                    # the outline, the same on every picture
INK = "#2c2014"
NATIONS = ("cw", "de", "it")
KINDS = ("armour", "foot", "guns", "motorised", "recon", "hq")
# plain colours, no camouflage and no markings: Commonwealth pale sand, German yellow-brown, Italian sand
TONES = {"cw": {"base": "#d8c08a", "light": "#ead7a6", "shade": "#b39a62"},
         "de": {"base": "#b9954f", "light": "#cfae69", "shade": "#8f7038"},
         "it": {"base": "#c4b47a", "light": "#d9cb96", "shade": "#968a54"}}
COMMON = {"dark": "#3a3128", "glass": "#4a4f52", "skin": "#d8a06c", "wood": "#4a3220", "flag": "#c23b2a"}


class Pic:
    """A picture being drawn: x to the right and heights up from the ground, in any unit, for
    fitted() to scale. Later shapes cover earlier ones."""

    def __init__(self):
        self.shapes = []

    def poly(self, tone, *pts, edge=True):
        self.shapes.append(("poly", tone, [(x, -h) for x, h in pts], edge))

    def box(self, tone, x, h, w, t, edge=True):
        self.poly(tone, (x, h), (x, h + t), (x + w, h + t), (x + w, h), edge=edge)

    def bar(self, tone, a, b, t):
        """A straight bar from a to b, t thick: a barrel, a trail, an arm."""
        (ax, ah), (bx, bh) = a, b
        k = t / 2 / math.hypot(bx - ax, bh - ah)
        dx, dh = (bh - ah) * k, (ax - bx) * k
        self.poly(tone, (ax + dx, ah + dh), (bx + dx, bh + dh), (bx - dx, bh - dh), (ax - dx, ah - dh))

    def disc(self, tone, x, h, r):
        self.shapes.append(("disc", tone, (x, -h), r))

    def stroke(self, tone, a, b, t):
        """A line with round ends and no outline: a rifle, an aerial, a spoke."""
        self.shapes.append(("stroke", tone, [(a[0], -a[1]), (b[0], -b[1])], t))

    def wheel(self, x, r):
        """A road wheel on its tyre, standing on the ground."""
        self.disc("dark", x, r, r)
        self.disc("base", x, r, r * 0.42)

    def roller(self, x, h, r):
        """A tank's wheel, inside its track."""
        self.disc("base", x, h, r)
        if r > 10:
            self.disc("shade", x, h, r * 0.34)

    def track(self, length, top, lift):
        """A tank's track as one dark band, rising at each end to the sprocket and the idler."""
        self.poly("dark", (lift, 0), (length - lift, 0), (length, lift), (length - 10, top), (10, top), (0, lift))

    def pennant(self, x, foot, top):
        """What marks a headquarters: one thick aerial with a plain pennant."""
        self.stroke("wood", (x, foot), (x, top), 9)
        self.poly("flag", (x, top), (x + 58, top - 15), (x, top - 30))


def armour(p, nation):
    if nation == "cw":          # Crusader: long and low, five large wheels, a low angular turret, a short thin gun
        p.track(400, 76, 34)
        p.roller(30, 50, 18)
        p.roller(370, 50, 18)
        for x in (76, 138, 200, 262, 324):
            p.roller(x, 37, 31)
        p.poly("base", (4, 78), (14, 112), (300, 112), (372, 100), (398, 78))
        p.box("shade", -2, 74, 404, 11)
        p.box("shade", 22, 112, 62, 12)
        p.bar("base", (290, 137), (366, 137), 11)
        p.poly("light", (150, 112), (128, 136), (152, 164), (262, 164), (292, 136), (268, 112))
        p.poly("base", (278, 124), (278, 150), (298, 147), (298, 127))
    elif nation == "de":        # Panzer III: six small wheels, three return rollers, a boxy turret, the short 50 mm gun
        p.track(400, 80, 36)
        p.roller(30, 48, 19)
        p.roller(368, 52, 22)
        for x in (120, 200, 280):
            p.roller(x, 66, 8)
        for x in (76, 126, 176, 226, 276, 326):
            p.roller(x, 27, 23)
        p.poly("base", (6, 80), (16, 104), (372, 104), (396, 80))
        p.box("shade", -2, 76, 404, 10)
        p.poly("base", (20, 104), (28, 122), (140, 122), (140, 104))
        p.poly("base", (140, 104), (140, 138), (318, 138), (334, 104))
        p.bar("base", (306, 158), (374, 158), 12)
        p.poly("light", (170, 138), (176, 178), (280, 178), (304, 160), (304, 138))
        p.box("shade", 190, 178, 44, 14)
        p.box("base", 298, 144, 16, 28)
    else:                       # M13/40: short and tall, eight small wheels in four pairs, a small turret
        p.track(360, 82, 38)
        p.roller(28, 50, 19)
        p.roller(330, 54, 22)
        for x in (100, 180, 260):
            p.roller(x, 68, 7)
        for a, b in ((66, 94), (134, 162), (206, 234), (274, 302)):
            p.poly("shade", (a - 6, 28), ((a + b) / 2, 52), (b + 6, 28))
            p.roller(a, 17, 13)
            p.roller(b, 17, 13)
        p.poly("base", (6, 82), (14, 104), (336, 104), (356, 82))
        p.box("shade", -2, 78, 364, 10)
        p.poly("base", (70, 104), (70, 152), (262, 152), (300, 128), (300, 104))
        p.bar("base", (240, 171), (302, 171), 11)
        p.poly("light", (120, 152), (126, 192), (216, 192), (238, 172), (238, 152))
        p.box("base", 232, 158, 14, 26)


def soldier(p, x, nation):
    """One marching rifleman. The nations differ by helmet, and the Commonwealth man wears shorts."""
    legs = "skin" if nation == "cw" else "base"
    p.poly(legs, (x + 36, 100), (x + 58, 100), (x + 30, 14), (x + 8, 14))
    p.poly("dark", (x + 4, 16), (x + 32, 16), (x + 30, 0), (x - 6, 0))
    p.poly(legs, (x + 46, 100), (x + 70, 100), (x + 96, 14), (x + 74, 14))
    p.poly("dark", (x + 72, 16), (x + 98, 16), (x + 112, 0), (x + 74, 0))
    if nation == "cw":
        p.poly("base", (x + 34, 104), (x + 72, 104), (x + 82, 68), (x + 24, 68))
    p.box("shade", x + 14, 120, 24, 52)                                                 # his pack
    p.poly("base", (x + 34, 98), (x + 32, 176), (x + 44, 184), (x + 70, 184), (x + 78, 176), (x + 76, 98))
    p.stroke("wood", (x + 80, 120), (x + 26, 236), 9)                                   # the rifle, at the slope
    p.bar("base", (x + 60, 168), (x + 78, 122), 15)
    p.disc("skin", x + 58, 202, 20)
    if nation == "cw":          # a wide flat brim
        p.poly("shade", (x + 26, 212), (x + 90, 212), (x + 80, 220), (x + 70, 232), (x + 46, 232), (x + 36, 220))
    elif nation == "de":        # a short peak, and a skirt flared over the neck
        p.poly("shade", (x + 34, 196), (x + 38, 220), (x + 46, 232), (x + 70, 232), (x + 80, 222),
               (x + 90, 210), (x + 72, 213), (x + 50, 213), (x + 46, 196))
    else:                       # a round dome with no brim
        p.poly("shade", (x + 37, 212), (x + 39, 224), (x + 47, 234), (x + 69, 234), (x + 77, 224), (x + 79, 212))


def foot(p, nation):
    for x in (0, 138, 276):     # three in file, to fill the width: one man alone is too small to read
        soldier(p, x, nation)


def guns(p, nation):
    if nation == "cw":          # 25-pounder: a box trail, a steel wheel on a tyre, a shield, no muzzle brake in 1941
        p.poly("shade", (0, 0), (-6, 18), (186, 76), (204, 50))
        p.disc("dark", 205, 42, 42)
        p.disc("base", 205, 42, 18)
        p.bar("shade", (190, 104), (330, 104), 14)
        p.bar("light", (150, 122), (400, 122), 18)
        p.box("base", 132, 108, 36, 28)
        p.poly("base", (218, 66), (204, 154), (224, 158), (240, 70))
    elif nation == "de":        # 88 mm Flak, down on its cross-shaped mount, the barrel raised a little
        p.box("dark", -6, 0, 32, 10)
        p.box("dark", 338, 0, 32, 10)
        p.box("shade", 0, 8, 364, 16)
        p.poly("base", (140, 24), (156, 98), (214, 98), (230, 24))
        p.bar("light", (150, 114), (424, 178), 17)
        p.bar("base", (108, 104), (166, 118), 32)
        p.poly("base", (150, 98), (150, 126), (232, 144), (238, 100))
        p.poly("base", (232, 72), (216, 192), (236, 198), (254, 78))
    else:                       # 75 mm field gun of 1911: a pole trail, a large wooden spoked wheel, a short barrel
        p.bar("shade", (0, 6), (204, 58), 15)
        p.disc("shade", 210, 52, 52)
        p.disc("light", 210, 52, 38)
        for turn in (0, 45, 90, 135):
            dx, dh = 36 * math.cos(math.radians(turn)), 36 * math.sin(math.radians(turn))
            p.stroke("wood", (210 - dx, 52 - dh), (210 + dx, 52 + dh), 6)
        p.disc("base", 210, 52, 12)
        p.bar("shade", (200, 102), (300, 102), 12)
        p.bar("light", (172, 118), (372, 118), 15)
        p.box("base", 154, 104, 30, 28)
        p.poly("base", (228, 76), (216, 152), (234, 156), (248, 80))


def motorised(p, nation):
    if nation == "cw":          # Bedford 3-ton: a snub sloping bonnet and a high canvas cover
        p.box("shade", 20, 34, 360, 12)
        p.box("base", 14, 46, 222, 46)
        p.poly("light", (10, 92), (10, 160), (22, 172), (228, 172), (240, 160), (240, 92))
        p.poly("base", (250, 46), (250, 150), (318, 150), (336, 108), (336, 46))
        p.poly("glass", (262, 112), (262, 140), (312, 140), (324, 112))
        p.poly("base", (336, 46), (336, 108), (392, 96), (400, 46))
        p.wheel(90, 30)
        p.wheel(346, 30)
    elif nation == "de":        # Opel Blitz: a long bonnet, a rounded cab, a low flat cover
        p.box("shade", 20, 34, 370, 12)
        p.box("base", 10, 46, 210, 40)
        p.box("light", 8, 86, 214, 62)
        p.poly("base", (232, 46), (232, 138), (244, 152), (290, 152), (310, 112), (310, 46))
        p.poly("glass", (244, 114), (244, 142), (286, 142), (300, 114))
        p.poly("base", (310, 46), (310, 112), (396, 100), (404, 84), (404, 46))
        p.wheel(96, 30)
        p.wheel(350, 30)
    else:                       # Lancia 3Ro: a tall flat-fronted cab, large wheels, an open body with slatted sides
        p.box("shade", 20, 38, 364, 12)
        p.box("base", 10, 50, 240, 64)
        p.box("shade", 16, 68, 228, 7, edge=False)
        p.box("shade", 16, 90, 228, 7, edge=False)
        p.poly("base", (262, 50), (262, 170), (350, 170), (358, 152), (358, 50))
        p.box("glass", 292, 120, 54, 36)
        p.box("base", 358, 50, 36, 54)
        p.wheel(92, 34)
        p.wheel(330, 34)


def recon(p, nation):
    if nation == "cw":          # Marmon-Herrington: a tall boxy hull, a small turret
        p.poly("base", (10, 40), (10, 122), (40, 152), (250, 152), (292, 114), (380, 100), (392, 40))
        p.bar("base", (214, 174), (280, 174), 9)
        p.poly("light", (120, 152), (130, 194), (212, 194), (224, 152))
        p.wheel(84, 34)
        p.wheel(318, 34)
    elif nation == "de":        # SdKfz 222: a low hull sloped in every way, a low open turret
        p.poly("base", (4, 70), (40, 128), (150, 144), (270, 144), (352, 104), (398, 68), (372, 40), (30, 40))
        p.poly("shade", (4, 70), (398, 68), (372, 40), (30, 40))
        p.bar("base", (262, 162), (348, 162), 9)
        p.poly("light", (160, 144), (172, 178), (262, 178), (274, 144))
        p.wheel(92, 34)
        p.wheel(312, 34)
    else:                       # AB 41: a long hull, large wheels, the spare wheel carried on the side
        p.poly("base", (6, 44), (6, 112), (60, 140), (280, 140), (340, 116), (398, 90), (398, 44))
        p.bar("base", (246, 168), (332, 168), 9)
        p.poly("light", (140, 140), (150, 184), (236, 184), (256, 160), (256, 140))
        p.wheel(80, 36)
        p.wheel(326, 36)
        p.disc("dark", 203, 80, 27)
        p.disc("base", 203, 80, 11)


def hq(p, nation):
    if nation == "cw":          # a boxy staff car
        p.pennant(34, 146, 204)
        p.poly("base", (6, 36), (6, 140), (16, 148), (212, 148), (246, 100), (332, 90), (344, 36))
        p.box("glass", 26, 104, 84, 32)
        p.poly("glass", (122, 104), (122, 136), (204, 136), (228, 104))
        p.wheel(70, 27)
        p.wheel(280, 27)
    elif nation == "de":        # Kubelwagen: a flat ribbed tub, open, the hood folded at the back
        p.pennant(24, 116, 200)
        p.poly("base", (232, 96), (246, 142), (257, 142), (247, 96))
        p.poly("base", (10, 38), (10, 96), (250, 96), (336, 72), (344, 38))
        p.box("shade", 22, 60, 216, 6, edge=False)
        p.box("shade", 22, 76, 216, 6, edge=False)
        p.poly("shade", (0, 96), (0, 118), (58, 118), (66, 96))
        p.wheel(66, 27)
        p.wheel(286, 27)
    else:                       # a small Fiat staff car with its canvas roof up
        p.pennant(30, 144, 204)
        p.poly("base", (10, 38), (10, 100), (200, 100), (226, 96), (318, 88), (332, 70), (332, 38))
        p.poly("light", (14, 100), (22, 146), (170, 146), (196, 100))
        p.poly("glass", (40, 104), (44, 134), (160, 134), (176, 104))
        p.wheel(64, 26)
        p.wheel(276, 26)


DRAW = {"armour": armour, "foot": foot, "guns": guns, "motorised": motorised, "recon": recon, "hq": hq}


def fitted(pic):
    """The shapes on the canvas: as large as WIDE and HIGH allow, centred, the ground on GROUND."""
    xs, top = [], 0
    for shape in pic.shapes:
        pad = shape[3] if shape[0] == "disc" else shape[3] / 2 if shape[0] == "stroke" else 0
        for x, y in ([shape[2]] if shape[0] == "disc" else shape[2]):
            xs += [x - pad, x + pad]
            top = min(top, y - pad)
    k = min(WIDE / (max(xs) - min(xs)), HIGH / -top)
    dx = W / 2 - k * (min(xs) + max(xs)) / 2

    def at(point):
        return round(k * point[0] + dx, 1), round(k * point[1] + GROUND, 1)

    return [(what, tone, at(where) if what == "disc" else [at(q) for q in where], round(k * size, 1) if what != "poly" else size)
            for what, tone, where, size in pic.shapes]


def svg(nation, kind):
    """The picture as an SVG drawing, the same text every time."""
    tones = dict(COMMON, **TONES[nation])
    pic = Pic()
    DRAW[kind](pic, nation)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<g stroke="{INK}" stroke-width="{LINE}" stroke-linejoin="round" stroke-linecap="round">']
    for what, tone, where, size in fitted(pic):
        fill = tones[tone]
        if what == "poly":
            points = " ".join(f"{x:g},{y:g}" for x, y in where)
            out.append(f'<polygon points="{points}" fill="{fill}"' + ("" if size else ' stroke="none"') + "/>")
        elif what == "disc":
            out.append(f'<circle cx="{where[0]:g}" cy="{where[1]:g}" r="{size:g}" fill="{fill}"/>')
        else:
            (x1, y1), (x2, y2) = where
            out.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{fill}" stroke-width="{size:g}"/>')
    return "\n".join(out + ["</g>", "</svg>", ""])


def path(nation, kind, ending):
    return os.path.join(OUT, f"{nation}_{kind}.{ending}")


def write():
    """Write every picture as an SVG, and as the PNG made from it."""
    import pygame

    os.makedirs(OUT, exist_ok=True)
    for nation in NATIONS:
        for kind in KINDS:
            with open(path(nation, kind, "svg"), "w", newline="\n") as f:
                f.write(svg(nation, kind))
            new = path(nation, kind, "new.png")                 # a viewer may hold the old file open: write beside it, then replace
            pygame.image.save(pygame.image.load(path(nation, kind, "svg")), new)
            os.replace(new, path(nation, kind, "png"))
    return OUT
