import sys

from . import cut, write

if sys.argv[1:] == ["cut"]:
    print(f"wrote {cut.write()}")
elif sys.argv[1:]:
    sys.exit("usage: python -m countergen [cut]")
else:
    print(f"wrote {write()}")
