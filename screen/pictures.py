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


AIR_EXAMPLES = {
    "cw": {"button": "hurricane", "support": "hurricane", "interdict": "blenheim", "recon": "boston"},
    "axis": {"button": "macchi", "support": "stuka", "interdict": "ju88", "recon": "observer"},
}
AIR_LABELS = {"hurricane": "Hurricane", "blenheim": "Blenheim", "boston": "Boston",
              "macchi": "Macchi C.200", "stuka": "Ju 87", "ju88": "Ju 88",
              "observer": "unspecified reconnaissance aircraft"}


def aircraft(surface, side, box, ink, pale, choice="button"):
    """Original top-view examples for pooled air effort, *not* one type per sortie.

    RAF Museum's 18 November 1941 Crusader entry documents the Allied models;
    AWM's contemporary recognition material documents the theatre's Axis types.
    'observer' is deliberately anonymous: no Axis reconnaissance type or unit
    has been verified for the scenario. No historical illustration is copied.
    """
    def pts(points):
        return [(round(box.x + x * box.w), round(box.y + y * box.h)) for x, y in points]

    model = AIR_EXAMPLES[side][choice]
    wings = {
        "hurricane": [(0.06, 0.49), (0.37, 0.35), (0.63, 0.35), (0.94, 0.49),
                      (0.94, 0.59), (0.62, 0.51), (0.38, 0.51), (0.06, 0.59)],
        "macchi": [(0.05, 0.43), (0.36, 0.37), (0.64, 0.37), (0.95, 0.43),
                   (0.93, 0.55), (0.62, 0.53), (0.38, 0.53), (0.07, 0.55)],
        "stuka": [(0.04, 0.48), (0.26, 0.43), (0.33, 0.34), (0.67, 0.34),
                  (0.74, 0.43), (0.96, 0.48), (0.96, 0.62), (0.7, 0.56),
                  (0.62, 0.5), (0.38, 0.5), (0.3, 0.56), (0.04, 0.62)],
        "blenheim": [(0.03, 0.43), (0.34, 0.38), (0.66, 0.38), (0.97, 0.43),
                     (0.97, 0.58), (0.65, 0.54), (0.35, 0.54), (0.03, 0.58)],
        "boston": [(0.04, 0.49), (0.36, 0.32), (0.64, 0.32), (0.96, 0.49),
                   (0.96, 0.57), (0.63, 0.53), (0.37, 0.53), (0.04, 0.57)],
        "ju88": [(0.03, 0.52), (0.37, 0.33), (0.63, 0.33), (0.97, 0.52),
                 (0.97, 0.61), (0.64, 0.51), (0.36, 0.51), (0.03, 0.61)],
        "observer": [(0.09, 0.44), (0.37, 0.38), (0.63, 0.38), (0.91, 0.44),
                     (0.91, 0.56), (0.63, 0.54), (0.37, 0.54), (0.09, 0.56)],
    }
    wing = wings[model]
    pygame.draw.polygon(surface, ink, pts(wing))
    twins = model in ("blenheim", "boston", "ju88", "observer")
    tail = (0.16, 0.84) if twins else (0.22, 0.86)
    pygame.draw.polygon(surface, ink, pts([(tail[0], tail[1]), (0.44, 0.82),
                                          (0.44, 0.19 if twins else 0.15), (0.5, 0.04),
                                          (0.56, 0.19 if twins else 0.15), (0.56, 0.82),
                                          (1 - tail[0], tail[1]), (1 - tail[0], 0.95),
                                          (tail[0], 0.95)]))
    if twins:
        for x in (0.29, 0.71):
            pygame.draw.ellipse(surface, ink, pygame.Rect(round(box.x + (x - 0.065) * box.w),
                                                          round(box.y + 0.17 * box.h),
                                                          max(3, round(0.13 * box.w)),
                                                          max(5, round(0.53 * box.h))))
    else:
        pygame.draw.polygon(surface, pale, pts([(0.47, 0.43), (0.5, 0.29),
                                               (0.53, 0.43), (0.52, 0.57), (0.48, 0.57)]))
    if model == "stuka":  # prominent fixed undercarriage
        for x in (0.35, 0.65):
            pygame.draw.ellipse(surface, ink, pygame.Rect(round(box.x + (x - 0.035) * box.w),
                                                          round(box.y + 0.56 * box.h),
                                                          max(2, round(0.07 * box.w)), max(3, round(0.15 * box.h))))
    if model == "macchi":  # radial-engined fighter's round nose, unlike the pointed Hurricane
        pygame.draw.circle(surface, ink, pts([(0.5, 0.16)])[0], max(2, round(box.w * 0.085)))
        pygame.draw.circle(surface, pale, pts([(0.5, 0.16)])[0], max(1, round(box.w * 0.027)))
    if model == "observer":  # anonymous reconnaissance, not a named aircraft
        pygame.draw.circle(surface, pale, pts([(0.5, 0.65)])[0], max(2, round(box.w * 0.095)), 1)
