"""Beeps and bangs, made here from sums: no sound files. Silent if there is no sound device
(docs/ENGINEERING_NOTES.md §7); the screen shows the same thing as a meter.

A strike is a harsh rattle of two tones by turns, like gunfire, and it lasts as long as the
damage was heavy: the length is the result. Each arm has its own pair of tones, so the ear
knows what is firing; guns do not rattle but sweep upwards, again and again."""
import math
from array import array

RATE = 22050
STEP_MS = 46            # each tone of a rattle lasts this long
SWEEP_MS = 230          # one rising sweep of the guns
TONES = {"armour": (150, 96), "motorised": (400, 290), "foot": (440, 310), "recon": (760, 560), "hq": (440, 310)}
VOLUME = {"armour": 0.42, "motorised": 0.34, "foot": 0.34, "recon": 0.24, "hq": 0.2, "guns": 0.36}


def wave(freq, ms, kind="square", volume=0.35, slide=1.0):
    """Samples for a tone: square for a beep, noise for a bang; slide bends the pitch."""
    n = int(RATE * ms / 1000)
    out, phase, seed = array("h"), 0.0, 12345
    for i in range(n):
        phase += freq * (slide ** (i / n)) / RATE
        fall = 1.0 - i / n
        if kind == "noise":
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            v = (seed / 0x3FFFFFFF - 1.0) * fall * fall
        else:
            v = (1.0 if math.sin(2 * math.pi * phase) >= 0 else -1.0) * (0.55 + 0.45 * fall)
        out.append(int(32767 * min(0.95, volume) * v))
    return out


def mix(a, b):
    """Two sounds at once."""
    if len(a) < len(b):
        a, b = b, a
    out = array("h", a)
    for i, v in enumerate(b):
        out[i] = max(-32767, min(32767, out[i] + v))
    return out


def fire(arm, ms):
    """The noise of a strike by this arm, lasting so many milliseconds."""
    out, volume = array("h"), VOLUME.get(arm, 0.3)
    if arm == "guns":                                   # rising sweeps
        while len(out) < RATE * ms // 1000:
            out += wave(220, SWEEP_MS, volume=volume, slide=4.2)
    else:                                               # two tones by turns, each begun with a click
        low, high = TONES.get(arm, TONES["foot"])
        n = 0
        while len(out) < RATE * ms // 1000:
            out += mix(wave(high if n % 2 == 0 else low, STEP_MS, volume=volume), wave(2000, 9, "noise", volume))
            n += 1
    return out[:RATE * ms // 1000]


class Sounds:
    def __init__(self):
        self.made, self.ok = {}, False
        try:
            import pygame
            pygame.mixer.init(RATE, -16, 1, 512)
            self.mixer, self.ok = pygame.mixer, True
        except Exception:                               # no device, no driver: play nothing
            pass

    def samples(self, name, amount=0):
        """The sound for a cue (screen/replay.py); amount is a strike's length in milliseconds."""
        if name.startswith("fire:"):
            return fire(name[5:], amount)
        if name == "boom":
            return mix(wave(90, 750, "noise", 0.6), wave(60, 600, volume=0.3, slide=0.4))
        if name == "fall":                              # a falling tone as the beaten give ground
            return wave(520, 520, volume=0.22, slide=0.33)
        if name == "alarm":
            return wave(620, 120, volume=0.2, slide=1.4)
        return wave(160, 18, "noise", 0.08)             # the tick of a column on the move

    def play(self, name, amount=0):
        if not self.ok:
            return
        if (name, amount) not in self.made:
            self.made[name, amount] = self.mixer.Sound(buffer=self.samples(name, amount).tobytes())
        self.made[name, amount].play()

    def stop(self):
        if self.ok:
            self.mixer.stop()
