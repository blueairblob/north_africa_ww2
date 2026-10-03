import sys

from . import build, fetch, render


def main(argv):
    cmd = argv[0] if argv else "all"
    if cmd in ("fetch", "all"):
        fetch.fetch()
    if cmd in ("build", "all"):
        build.write(build.build())
        print(f"wrote {build.OUT}")
    if cmd in ("render", "all"):
        print(f"wrote {render.main()}")
    if cmd not in ("fetch", "build", "render", "all"):
        sys.exit("usage: python -m mapgen [fetch|build|render|all]")


main(sys.argv[1:])
