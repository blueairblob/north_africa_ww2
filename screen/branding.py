"""Small original hex emblem shared by the title card and operating-system window."""
import pygame

from . import theme as T


def icon(size=64):
    """Draw at four times display size for smooth Windows/taskbar edges."""
    n = size * 4
    art = pygame.Surface((n, n), pygame.SRCALPHA)
    points = [(n // 2, n // 18), (n * 17 // 18, n // 4),
              (n * 17 // 18, n * 3 // 4), (n // 2, n * 17 // 18),
              (n // 18, n * 3 // 4), (n // 18, n // 4)]
    pygame.draw.polygon(art, T.PAPER, points)
    pygame.draw.polygon(art, T.INK, points, n // 24)
    pygame.draw.line(art, T.SIDE["cw"], (n // 4, n * 3 // 4), (n // 4, n // 3), n // 12)
    pygame.draw.line(art, T.COMMAND["axis"], (n * 3 // 4, n // 4), (n * 3 // 4, n * 2 // 3), n // 12)
    pygame.draw.line(art, T.SCARP, (n // 4, n * 2 // 3), (n * 3 // 4, n // 3), n // 18)
    pygame.draw.circle(art, T.SHORT, (n // 2, n // 2), n // 10)
    pygame.draw.circle(art, T.PAPER, (n // 2, n // 2), n // 26)
    return pygame.transform.smoothscale(art, (size, size))
