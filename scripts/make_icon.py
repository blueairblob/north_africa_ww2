"""Build the Windows icon from the existing in-game hex emblem."""
import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from screen.branding import icon  # noqa: E402

def main():
    pygame.init()
    surface = icon(256)
    image = Image.frombytes("RGBA", surface.get_size(), pygame.image.tostring(surface, "RGBA"))
    target = ROOT / "art" / "icon.ico"
    image.save(target, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    pygame.quit()
    print(target)


if __name__ == "__main__":
    main()
