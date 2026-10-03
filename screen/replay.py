"""The last turn, played back: what a side saw happen, as scenes with a clock. No pygame here.

The engine has already decided everything; this only performs it (DESIGN.md §12). A turn is
told from the side's view before it and the view after it, and the events the side was told
of (docs/RULES.md 14.6). Its own units move hex by hex as they did; an enemy is only ever
shown where the side saw it.

The scenes: the movement; then the strikes, one at a time; then the outcome.

A strike is one formation attacking: the map goes to it, the units it hits burn, and a
rattle plays for as long as the damage was heavy. Every strike takes at least the same beat,
so a short rattle is followed by silence, and the silence says the attack was feeble. When
a battle's attackers have all struck, the defenders reply the same way. Nothing is settled
until every strike of the turn has been shown; then, in the outcome, the beaten fall back,
the destroyed burst, and the rest are seen to have held.
"""
from engine.movement import IMPULSES

IMPULSE_MS = 110        # one impulse of movement
LEAD_MS = 600           # the map arrives and the striker is pointed out before it fires
RATTLE_MS = 250         # the rattle of a strike that does the least damage
DAMAGE_MS = 45          # added to the rattle for each point of cohesion the strike costs its targets
RATTLE_MAX = 3000       # no rattle is longer than this
BEAT_MS = 2600          # every strike takes at least this long
TAIL_MS = 400           # quiet after a rattle, before the next strike
FLICKER_MS = 60         # a burning unit changes between yellow and red this often
HOLD_MS = 700           # the outcome: a breath before anyone moves
FALL_MS = 900           # falling back and following up
BURST_MS = 800          # a unit destroyed
PAUSE_MS = 300          # between scenes
MARCH_SCALE = 0.5       # a unit on a road march is drawn at half its side: a quarter of its area


def rattle_ms(damage):
    """How long a strike rattles: the heavier the damage, the longer, up to a limit."""
    return min(RATTLE_MAX, RATTLE_MS + DAMAGE_MS * damage) if damage > 0 else 0


def strikes(battle, kinds):
    """A battle's strikes, in order: each attacker on the defenders, with its share of the
    cohesion they lost, by its share of the attack; then the defenders' reply on the attackers."""
    attackers, defenders = battle["attackers"], battle["defenders"]
    av = {int(i): v for i, v in battle["av"].items()}
    total = sum(av.values()) or 1
    out = [{"by": [a], "arm": kinds.get(a, "foot"), "on": list(defenders), "reply": False,
            "damage": max(1, battle["cld"] * av[a] // total) if av[a] else 0} for a in attackers]
    lead = max(defenders, key=lambda i: (kinds.get(i) != "hq", -i))
    out.append({"by": list(defenders), "arm": kinds.get(lead, "foot"), "on": list(attackers),
                "reply": True, "damage": battle["cla"]})
    for s in out:
        s["rattle"] = rattle_ms(s["damage"])
        s["long"] = max(BEAT_MS, LEAD_MS + s["rattle"] + TAIL_MS)
    return out


def script(before, after):
    """The scenes of the turn between two views of one side."""
    events = after["events"]
    mine = {u["id"]: u for u in before["units"] if u["status"] == "on_map"}
    foes = {e["id"]: e for e in before["enemy"]}
    now = {u["id"]: u for u in after["units"]}
    now_foes = {e["id"]: e for e in after["enemy"]}
    cast = {**{i: (u, True) for i, u in mine.items()}, **{i: (e, False) for i, e in foes.items()}}
    for i, e in now_foes.items():
        cast.setdefault(i, (e, False))                   # an enemy first seen this turn
    kinds = {i: u["type"] for i, (u, _) in cast.items()}
    battles = [e for e in events if e["event"] == "battle"]
    fought_at = {int(i): tuple(h) for b in battles for i, h in b["where"].items()}

    tracks = {}                                          # movement: (impulse, hex) points per unit
    for e in events:
        if e["event"] == "step" and e["unit"] in mine:
            t = tracks.setdefault(e["unit"], {"points": [(0, tuple(mine[e["unit"]]["hex"]))], "march": e["march"]})
            t["points"].append((e["impulse"], tuple(e["to"])))
    for i, e in foes.items():                            # an enemy seen before and after, or met in battle
        end = fought_at.get(i) or (tuple(now_foes[i]["hex"]) if i in now_foes else None)
        if end and end != tuple(e["hex"]):
            tracks[i] = {"points": [(0, tuple(e["hex"])), (IMPULSES, end)], "march": False, "glide": True}
    place = {i: tuple(u["hex"]) for i, (u, _) in cast.items() if u.get("hex")}
    for i, t in tracks.items():
        place[i] = t["points"][-1][1]
    place.update(fought_at)

    scenes = []
    if tracks:
        scenes.append({"kind": "move", "tracks": tracks})
    for b in battles:                                    # one strike at a time, battle by battle
        for s in strikes(b, kinds):
            scenes.append(dict(s, kind="strike", hex=tuple(b["hex"]), at=place.get(s["by"][0], tuple(b["hex"]))))
    fought = sorted({i for b in battles for i in b["attackers"] + b["defenders"]})
    burst = {i for b in battles for i in b["destroyed"]} | {e["unit"] for e in events if e["event"] == "destroyed"}
    slides, gone = {}, set()
    for i, (u, own) in cast.items():
        if own:
            end = tuple(now[i]["hex"]) if now[i]["status"] == "on_map" else None
        else:
            end = tuple(now_foes[i]["hex"]) if i in now_foes else None
        if end is None:
            gone.add(i)
        elif i in place and end != place[i]:
            slides[i] = (place[i], end)
    if slides or gone or fought:
        scenes.append({"kind": "outcome", "slides": slides, "gone": sorted(gone), "burst": sorted(burst & gone),
                       "held": [i for i in fought if i not in slides and i not in gone]})
    return {"cast": cast, "start": {i: (fought_at.get(i) if i not in mine and i not in foes else tuple(u["hex"]))
                                    for i, (u, _) in cast.items() if i in mine or i in foes or i in fought_at},
            "scenes": scenes}


class Playback:
    """The script on a clock. stage(t) says what to draw at t milliseconds; cues(t0, t1) says
    which sounds begin between two times."""
    def __init__(self, before, after):
        self.script = script(before, after)
        self.timeline, t = [], 0
        for scene in self.script["scenes"]:
            if scene["kind"] == "move":
                long = max(p[0] for tr in scene["tracks"].values() for p in tr["points"]) * IMPULSE_MS
            elif scene["kind"] == "strike":
                long = scene["long"]
            else:
                long = HOLD_MS + max(FALL_MS if scene["slides"] else 0, BURST_MS if scene["gone"] else 0, 300)
            self.timeline.append((t, t + long, scene))
            t += long + (PAUSE_MS if scene["kind"] != "strike" else 0)
        self.length = t

    def done(self, t):
        return t >= self.length

    def cues(self, t0, t1):
        """The sounds that begin in [t0, t1): (name, amount). A strike's sound is named for
        the arm striking, and its amount is how many milliseconds it rattles."""
        out = []

        def at(when, name, amount=0):
            if t0 <= when < t1:
                out.append((name, amount))
        for start, end, scene in self.timeline:
            if scene["kind"] == "move":
                for k in range(0, int((end - start) // IMPULSE_MS), 2):
                    at(start + k * IMPULSE_MS, "tick")
            elif scene["kind"] == "strike":
                at(start, "alarm")
                if scene["rattle"]:
                    at(start + LEAD_MS, "fire:" + scene["arm"], scene["rattle"])
            else:
                if scene["slides"]:
                    at(start + HOLD_MS, "fall")
                if scene["burst"]:
                    at(start + HOLD_MS, "boom")
        return out

    def stage(self, t):
        """What to draw at time t: for each unit its place (a hex, or two hexes and how far
        between them), its scale, how solid it is and how it is lit. A unit is lit "firing"
        as it strikes, "fire0" or "fire1" (yellow, red) as it burns, "held" when it is seen to
        have stood. Also: the hex to bring into view, the hex ringed, the line of the strike,
        how far the rattle has run (the meter), and bursts."""
        place = dict(self.script["start"])
        scale, fade, lit, shake, bursts = {}, {}, {}, set(), []
        title, focus, ring, line, meter = "", None, None, None, None
        for start, end, scene in self.timeline:
            if t < start:
                break
            local, over = t - start, t >= end
            if scene["kind"] == "move":
                title = "" if over else "Movement"
                clock = local / IMPULSE_MS
                for i, tr in scene["tracks"].items():
                    pts = tr["points"]
                    place[i] = pts[-1][1]
                    for (i0, h0), (i1, h1) in zip(pts, pts[1:]):
                        if clock < i1:                   # it stands, then takes the step in its impulse
                            begin = i0 if tr.get("glide") else i1 - 1
                            place[i] = (h0, h1, max(0.0, min(1.0, (clock - begin) / (i1 - begin))))
                            break
                    if tr["march"] and clock < pts[-1][0]:
                        scale[i] = MARCH_SCALE
            elif scene["kind"] == "strike" and not over:
                title = "The reply" if scene["reply"] else "Assault"
                focus, ring = scene["at"], scene["hex"]
                target = place.get(scene["on"][0])
                line = (scene["at"], target if target and len(target) == 2 else scene["hex"])
                for i in scene["by"]:
                    lit[i] = "firing"
                burning = LEAD_MS <= local < LEAD_MS + scene["rattle"]
                if burning:                              # the damage shows on the other side
                    flame = "fire%d" % (int((local - LEAD_MS) // FLICKER_MS) % 2)
                    for i in scene["on"]:
                        lit[i] = flame
                        shake.add(i)
                if local >= LEAD_MS:
                    meter = (min(local - LEAD_MS, scene["rattle"]) / RATTLE_MAX, burning)
            elif scene["kind"] == "outcome":
                title = "" if over else "The outcome"
                part = max(0.0, min(1.0, (local - HOLD_MS) / max(1, end - start - HOLD_MS)))
                for i in scene["held"]:
                    if not over and local >= HOLD_MS:
                        lit[i] = "held"
                for i, (a, b) in scene["slides"].items():
                    place[i] = b if over else (a, b, min(1.0, max(0.0, (local - HOLD_MS) / FALL_MS)))
                for i in scene["gone"]:
                    fade[i] = 1.0 - part
                    if i in scene["burst"] and 0 < part < 1 and i in place:
                        bursts.append((place[i], part))
        units = [(i, u, own, place[i], scale.get(i, 1.0), fade.get(i, 1.0), lit.get(i), i in shake)
                 for i, (u, own) in sorted(self.script["cast"].items()) if place.get(i) and fade.get(i, 1.0) > 0.02]
        return {"units": units, "title": title, "focus": focus, "ring": ring, "line": line, "meter": meter,
                "bursts": bursts}
