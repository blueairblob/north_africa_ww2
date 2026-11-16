"""Reviewer-facing menus, with scenario options embedded when play begins."""
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

import pygame

from engine import campaigns, scenarios, scenario_options

from . import theme as T
from .branding import icon as brand_icon
from .draw import wrap
from .paths import ROOT, display_user_root

PLAYER_CHOICES = (("human", "Human"), ("computer-easy", "Easy computer"),
                  ("computer", "Standard computer"), ("computer-hard", "Hard computer"),
                  ("nothing", "No orders"))


def campaign_opening():
    try:
        return campaigns.opening(campaigns.load())
    except (OSError, ValueError):
        return None


RESEARCH_FOLDER = scenarios.FOLDER.parent / "scenario_drafts"


def research_opening():
    try:
        name = campaigns.load().get("research_trial")
        return name if name and (RESEARCH_FOLDER / f"{name}.json").is_file() else None
    except (OSError, ValueError):
        return None


HELP = (
    ("THE FIRST TURN", (
        "Choose your scenario and commanders, then read the orders from High Command before starting.",
        "Click a friendly unit. Move or Attack chooses an order; click a destination hex to give it. Space takes you to the next unit. Units without orders hold their ground.",
        "Press End turn once all orders are ready. A reminder may ask a second time if you left units untouched. Watch the movement and battles, then give orders for the next turn.")),
    ("FIGHTING & SUPPLY", (
        "Attack moves towards a hex and fights visible enemies reached during the turn. Ground, fortifications, cohesion, multiple attack directions and nearby stationary HQs matter.",
        "Keep units supplied from ports and HQs. The Supply layer shows your reach, enemy ports as possible sources, and convoy traffic spotted locally by your reconnaissance units. Occupying a port or placing a unit near a route can disrupt supply next turn, but trucks may bypass it and HQs keep reserves. Dig in builds fieldworks; Rest recovers cohesion.",
        "Travel uses roads and tracks faster, but cannot cross open desert and is exposed if attacked. Use Attack near the enemy. Weather can ground aircraft and slow movement. The right panel shows unit details and the timetable.")),
    ("SCENARIOS & SEA DELIVERY", (
        "Choose a battle and read its High Command aims. History in setup and the Game menu gives historical context, separate from your result. The campaign research trial runs from September 1940 to November 1942 with estimated strengths and mechanics still under review.",
        "The default sea-delivery schedule is an estimate. The experimental settings add or subtract 15 percentage points from Axis sea delivery. They are sensitivity tests of shipping loss, not a simulated Malta invasion.",
        "A saved game keeps its chosen setting. A new game's setting is independent of the scenario and the player difficulty.")),
    ("CONTROLS & FEEDBACK", (
        "Drag to pan, scroll to zoom, and press Home to see the whole map. F3 swaps picture and NATO counters. The details chevron opens or closes the right panel.",
        "F2 shows Mission orders and green map targets. F5 saves; F6 advances up to five quiet campaign turns; F9 lists saves; F12 captures a screenshot. F1 opens this guide, Escape opens the menu, and the window X saves and exits. Options opens Game Files.",
        "For a playtest report, describe the scenario, side and turn. Include an F12 screenshot and the matching save file when possible. The result screen explains the victory outcome.")),
)


@dataclass
class Front:
    page: str = "home"
    back: str = "home"
    scenario: str = "sidi_rezegh"
    mode: str = "battle"
    campaign_start: str | None = field(default_factory=campaign_opening)
    research_start: str | None = field(default_factory=research_opening)
    shipping: str = "baseline"
    axis: str = "computer"
    cw: str = "human"
    help_page: int = 0
    history_page: int = 0
    history_episode: dict | None = None
    message: str = ""
    names: tuple = field(default_factory=lambda: tuple(scenarios.names()))

    def cycle(self, field, choices, step):
        values = tuple(choices)
        setattr(self, field, values[(values.index(getattr(self, field)) + step) % len(values)])


def card_rect(size):
    w, h = size
    box = pygame.Rect(0, 0, min(800, w - 32), min(648, h - 24))
    box.center = (w // 2, h // 2)
    return box


def controls(size, page):
    card = card_rect(size)
    cx = card.centerx
    if page == "home":
        names = ("new", "research", "campaign", "continue", "help", "options", "quit")
        top, step = (164, 44) if card.h < 620 else (178, 53)
        return {name: pygame.Rect(cx - 160, card.y + top + n * step, 320, 42) for n, name in enumerate(names)}
    if page == "setup":
        out = {}
        for n, key in enumerate(("scenario", "shipping", "cw", "axis")):
            y = card.y + 195 + n * 51
            out[key + "_prev"] = pygame.Rect(cx - 183, y, 42, 42)
            out[key + "_next"] = pygame.Rect(cx + 141, y, 42, 42)
        out["start"] = pygame.Rect(cx - 225, card.bottom - 60, 150, 44)
        out["history"] = pygame.Rect(cx - 65, card.bottom - 60, 160, 44)
        out["back"] = pygame.Rect(cx + 105, card.bottom - 60, 120, 44)
        return out
    if page == "pause":
        names = ("resume", "save", "load", "new", "history", "help", "options", "home", "quit")
        step = 42 if card.h >= 620 else 36
        high = 37 if card.h >= 620 else 34
        return {name: pygame.Rect(cx - 155, card.y + (174 if card.h >= 620 else 160) + n * step, 310, high)
                for n, name in enumerate(names)}
    if page == "options":
        compact = card.h < 620
        names = ("symbols", "sound", "weather_visible", "details_collapsed", "remind")
        out = {name: pygame.Rect(card.x + 64, card.y + (174 if compact else 176) + n * (43 if compact else 55),
                                card.w - 128, 38 if compact else 44)
               for n, name in enumerate(names)}
        out["game_files"] = pygame.Rect(cx - 125, card.y + (439 if compact else 515), 250, 34 if compact else 40)
        out["back"] = pygame.Rect(cx - 90, card.bottom - (51 if compact else 68), 180, 38 if compact else 40)
        return out
    if page in ("help", "history"):
        out = {"prev": pygame.Rect(cx - 202, card.bottom - 69, 116, 40),
                "next": pygame.Rect(cx - 58, card.bottom - 69, 116, 40),
                "back": pygame.Rect(cx + 86, card.bottom - 69, 116, 40)}
        if page == "history":
            out["image_source"] = pygame.Rect(card.x + 47, card.y + 225,
                                              card.w - 94, card.h - 380)
        return out
    return {}


def history_pages(episode):
    """Small readable screens for a historical reference, separate from played results."""
    if not episode:
        return [("HISTORICAL CONTEXT", ("No historical record is available for this scenario.",))]
    pre, post = episode["pre"], episode["post"]
    pages = [
        ("BEFORE · AIMS AND GROUND", (pre["objective"], pre["deployment"])),
        ("BEFORE · FORCES", (pre["forces"], "Selected formations; details and source links are in the historical story archive.")),
    ]
    if episode.get("period_image") or episode.get("image"):
        pages.append(("PERIOD · ARCHIVE IMAGE", ()))
    events = episode["timeline"]
    for offset in range(0, len(events), 2):
        pages.append(("WHAT HAPPENED · TIMELINE", tuple(
            f"{event['date']}: {event['event']}" for event in events[offset:offset + 2])))
    for dispute in episode.get("disputed", []):
        pages.append(("EVIDENCE · SOURCES DIFFER", (
            dispute["point"], *(account["claim"] for account in dispute["accounts"]))))
    pages.append(("AFTER · HISTORICAL RESULT", (
        post["outcome"], post["why"],
        "Historical reference. Your played battle can end differently.")))
    return pages


@lru_cache(maxsize=9)
def history_image(file):
    return pygame.image.load(str(ROOT / file))


def draw(surface, painter, ui, front, options, has_save=False):
    """Draw a complete, scalable menu over the game's map paper."""
    size = surface.get_size()
    surface.blit(painter.background(size, ui), (0, 0))
    shade = pygame.Surface(size, pygame.SRCALPHA)
    shade.fill((20, 28, 30, 198))
    surface.blit(shade, (0, 0))
    card = card_rect(size)
    pygame.draw.rect(surface, T.PAPER, card, border_radius=8)
    pygame.draw.rect(surface, T.INK, card, 3, border_radius=8)
    pygame.draw.rect(surface, T.COMMAND["cw"], (card.x + 3, card.y + 3, card.w - 6, 10))
    pygame.draw.rect(surface, T.COMMAND["axis"], (card.x + 3, card.bottom - 13, card.w - 6, 10))
    surface.blit(brand_icon(64), (card.centerx - 32, card.y + 19))
    painter.text(surface, "BENGHAZI HANDICAP", (card.centerx, card.y + 105), 34, T.INK, True, True, serif=True)
    painter.text(surface, "NORTH AFRICA 1940–42  ·  REVIEW BUILD", (card.centerx, card.y + 140), 13, T.DIM, True, True)
    buttons = controls(size, front.page)

    def button(name, label, enabled=True, selected=False):
        rect = buttons[name]
        hover = rect.collidepoint(ui.mouse)
        colour = T.BUTTON_ON if selected or hover and enabled else T.BUTTON if enabled else (214, 207, 190)
        pygame.draw.rect(surface, colour, rect, border_radius=5)
        pygame.draw.rect(surface, T.INK if enabled else T.DIM, rect, 1, border_radius=5)
        painter.text(surface, label, rect.center, 15, T.INK if enabled else T.DIM, True, True)

    if front.page == "home":
        for key, label in (("new", "New battle"), ("research", "Campaign research trial"),
                           ("campaign", "New campaign"), ("continue", "Continue saved game"),
                           ("help", "How to play"), ("options", "Options"), ("quit", "Quit")):
            button(key, label, (key != "continue" or has_save) and (key != "campaign" or front.campaign_start is not None)
                   and (key != "research" or front.research_start is not None))
        note = front.message or ("Linked research trial: September 1940–November 1942; historical validation continues."
                                 if front.campaign_start is None else "Choose a battle or begin the full campaign.")
        painter.text(surface, note, (card.centerx, card.bottom - 37), 12, T.DIM, centre=True)
    elif front.page == "setup":
        scene = scenarios.load(front.scenario, RESEARCH_FOLDER) if front.mode == "research" else scenarios.load(front.scenario)
        painter.text(surface, "CAMPAIGN RESEARCH TRIAL · ESTIMATED" if front.mode == "research" else
                     "NEW CAMPAIGN" if front.mode == "campaign" else "NEW BATTLE",
                     (card.centerx, card.y + 169), 15, T.DIM, True, True)
        for n, (key, label, value) in enumerate((
                ("scenario", "SCENARIO", scene["name"]),
                ("shipping", "MALTA / SEA", scenario_options.label(front.shipping)),
                ("cw", "COMMONWEALTH", dict(PLAYER_CHOICES)[front.cw]),
                ("axis", "AXIS", dict(PLAYER_CHOICES)[front.axis]))):
            y = card.y + 195 + n * 51
            painter.text(surface, label, (card.x + 64, y + 12), 12, T.DIM, True)
            painter.text(surface, value, (card.centerx, y + 23), 16, T.INK, True, True)
            enabled = (key != "scenario" or front.mode == "battle") and (key != "shipping" or front.mode != "research")
            button(key + "_prev", "‹", enabled)
            button(key + "_next", "›", enabled)
        aim = scene.get("aim", {})
        first = date.fromisoformat(scene["start"])
        span = "daily" if scene.get("turn_days", 2) == 1 else "two-day"
        painter.text(surface, f"Starts {first:%d %b %Y}  ·  {scene['turns']} {span} turns  ·  HIGH COMMAND ORDERS",
                     (card.centerx, card.y + 402), 11, T.DIM, True, True)
        for n, side in enumerate(("cw", "axis")):
            words = f"{T.SIDE_NAME[side]}: {aim.get(side, 'Take and hold the objectives.')}"
            for line_no, line in enumerate(wrap(painter.font(12), words, card.w - 96)[:2]):
                painter.text(surface, line, (card.x + 48, card.y + 417 + n * 31 + line_no * 13), 12, T.DIM)
        button("start", "Start trial" if front.mode == "research" else
               "Start campaign" if front.mode == "campaign" else "Start battle")
        button("history", "History")
        button("back", "Back")
    elif front.page == "pause":
        painter.text(surface, "GAME MENU", (card.centerx, card.y + 158), 15, T.DIM, True, True)
        for key, label in (("resume", "Resume battle"), ("save", "Save game"),
                           ("load", "Load game"), ("new", "New game"),
                           ("history", "Historical context"),
                           ("help", "How to play"), ("options", "Options"),
                           ("home", "Main menu"), ("quit", "Save and quit")):
            button(key, label, key != "load" or has_save)
    elif front.page == "options":
        compact = card.h < 620
        painter.text(surface, "OPTIONS", (card.centerx, card.y + 156), 15, T.DIM, True, True)
        labels = {"symbols": "Counters", "sound": "Battle sound", "weather_visible": "Weather marker",
                  "details_collapsed": "Details panel", "remind": "End-turn reminder"}
        values = {"symbols": "Pictures" if options["symbols"] == "pictures" else "NATO symbols",
                  "sound": "On" if options["sound"] else "Off",
                  "weather_visible": "Shown" if options["weather_visible"] else "Hidden",
                  "details_collapsed": "Hidden" if options["details_collapsed"] else "Shown",
                  "remind": "On" if options["remind"] else "Off"}
        for key in labels:
            rect = buttons[key]
            pygame.draw.rect(surface, T.BUTTON_ON if rect.collidepoint(ui.mouse) else T.BUTTON, rect, border_radius=5)
            pygame.draw.rect(surface, T.INK, rect, 1, border_radius=5)
            painter.text(surface, labels[key], (rect.x + 14, rect.centery - 9), 14, T.INK, True)
            painter.text(surface, values[key], (rect.right - 166, rect.centery - 9), 14, T.INK)
        painter.text(surface, "GAME FILES", (card.x + 64, card.y + (400 if compact else 468)), 12, T.DIM, True)
        painter.fitted(surface, front.message or display_user_root(),
                       (card.centerx, card.y + (422 if compact else 492)), 12,
                       T.ATTACK if front.message else T.INK, card.w - 128)
        button("game_files", "Open Game Files")
        button("back", "Back")
    elif front.page == "help":
        heading, paragraphs = HELP[front.help_page]
        painter.text(surface, heading, (card.centerx, card.y + 174), 17, T.INK, True, True)
        y = card.y + 207
        for paragraph in paragraphs:
            for line in wrap(painter.font(13), paragraph, card.w - 94):
                painter.text(surface, line, (card.x + 47, y), 13, T.INK)
                y += 19
            y += 17
        button("prev", "Previous", front.help_page > 0)
        button("next", "Next", front.help_page < len(HELP) - 1)
        button("back", "Back")
        painter.text(surface, f"{front.help_page + 1} / {len(HELP)}", (card.centerx, card.bottom - 86), 11, T.DIM, centre=True)
    elif front.page == "history":
        pages = history_pages(front.history_episode)
        heading, paragraphs = pages[front.history_page]
        episode_title = front.history_episode["title"] if front.history_episode else "No record"
        painter.fitted(surface, f"HISTORICAL REFERENCE · {episode_title}",
                       (card.centerx, card.y + 173), 14, T.DIM, card.w - 100)
        painter.text(surface, heading, (card.centerx, card.y + 202), 17, T.INK, True, True)
        if heading == "PERIOD · ARCHIVE IMAGE":
            illustration = front.history_episode.get("period_image") or front.history_episode["image"]
            picture = history_image(illustration["file"])
            max_w, max_h = card.w - 94, card.h - 390
            scale = min(max_w / picture.get_width(), max_h / picture.get_height())
            shown = pygame.transform.smoothscale(picture, (
                max(1, round(picture.get_width() * scale)),
                max(1, round(picture.get_height() * scale))))
            image_rect = shown.get_rect(midtop=(card.centerx, card.y + 225))
            surface.blit(shown, image_rect)
            y = image_rect.bottom + 8
            for line in wrap(painter.font(12), illustration["caption"], card.w - 94)[:2]:
                painter.text(surface, line, (card.x + 47, y), 12, T.INK)
                y += 15
            painter.fitted(surface, illustration["credit"], (card.centerx, y + 8), 11, T.DIM, card.w - 94)
            painter.text(surface, "Click image for the archive source and reuse record",
                         (card.centerx, y + 27), 10, T.DIM, centre=True)
        else:
            y = card.y + 234
            for paragraph in paragraphs:
                for line in wrap(painter.font(13), paragraph, card.w - 94):
                    if y > card.bottom - 102:
                        break
                    painter.text(surface, line, (card.x + 47, y), 13, T.INK)
                    y += 19
                y += 14
        button("prev", "Previous", front.history_page > 0)
        button("next", "Next", front.history_page < len(pages) - 1)
        button("back", "Back")
        painter.text(surface, f"{front.history_page + 1} / {len(pages)}", (card.centerx, card.bottom - 86), 11, T.DIM, centre=True)


def choice_at(size, page, pos):
    return next((name for name, rect in controls(size, page).items() if rect.collidepoint(pos)), None)
