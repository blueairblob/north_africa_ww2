"""Pictures for the counters, drawn here from a few shapes: a tank, a lorry, a soldier, a gun,
an armoured car, a flag. They are the default; NATO-style symbols are the option (F3).
A picture file in art/counters takes the place of either (docs/COUNTERS.md)."""
import pygame


def picture(surface, kind, box, ink, pale):
    """Draw the picture for a kind of unit inside box, in ink, with pale for wheels and gaps."""
    def p(x, y):
        return box.x + box.w * x, box.y + box.h * y

    def poly(*pts):
        pygame.draw.polygon(surface, ink, [p(x, y) for x, y in pts])

    def line(a, b, w):
        pygame.draw.line(surface, ink, p(*a), p(*b), max(1, int(box.h * w)))

    def wheel(x, y, r):
        pygame.draw.circle(surface, ink, p(x, y), max(2, box.h * r))
        if box.h * r > 4:
            pygame.draw.circle(surface, pale, p(x, y), box.h * r * 0.4)

    if kind == "armour":                                # a tank
        pygame.draw.rect(surface, ink, pygame.Rect(*p(0.06, 0.62), box.w * 0.88, box.h * 0.3), border_radius=int(box.h * 0.15))
        poly((0.1, 0.64), (0.2, 0.44), (0.84, 0.44), (0.94, 0.64))
        poly((0.34, 0.46), (0.38, 0.2), (0.62, 0.2), (0.68, 0.46))
        line((0.62, 0.3), (1.0, 0.3), 0.1)
        if box.h > 16:
            for x in (0.2, 0.36, 0.52, 0.68, 0.84):
                pygame.draw.circle(surface, pale, p(x, 0.78), box.h * 0.07)
    elif kind == "motorised":                           # a lorry
        poly((0.06, 0.26), (0.6, 0.26), (0.6, 0.72), (0.06, 0.72))
        poly((0.64, 0.72), (0.64, 0.4), (0.8, 0.4), (0.94, 0.56), (0.94, 0.72))
        wheel(0.24, 0.8, 0.17)
        wheel(0.76, 0.8, 0.17)
    elif kind == "foot":                                # a soldier with his rifle
        pygame.draw.circle(surface, ink, p(0.5, 0.17), max(2, box.h * 0.13))
        poly((0.4, 0.32), (0.6, 0.32), (0.62, 0.64), (0.38, 0.64))
        line((0.44, 0.62), (0.36, 0.98), 0.1)
        line((0.56, 0.62), (0.64, 0.98), 0.1)
        line((0.26, 0.7), (0.74, 0.14), 0.07)
    elif kind == "guns":                                # a gun on its carriage
        line((0.3, 0.6), (0.98, 0.26), 0.12)
        poly((0.38, 0.3), (0.5, 0.24), (0.54, 0.7), (0.42, 0.74))
        line((0.42, 0.74), (0.04, 0.94), 0.08)
        wheel(0.44, 0.76, 0.2)
    elif kind == "recon":                               # an armoured car
        poly((0.06, 0.7), (0.16, 0.44), (0.78, 0.44), (0.94, 0.58), (0.94, 0.7))
        poly((0.36, 0.46), (0.4, 0.24), (0.58, 0.24), (0.62, 0.46))
        line((0.58, 0.32), (0.84, 0.32), 0.07)
        wheel(0.26, 0.78, 0.17)
        wheel(0.74, 0.78, 0.17)
    else:                                               # a headquarters: a flag
        line((0.28, 0.06), (0.28, 0.98), 0.08)
        poly((0.3, 0.08), (0.86, 0.16), (0.7, 0.3), (0.86, 0.46), (0.3, 0.52))
