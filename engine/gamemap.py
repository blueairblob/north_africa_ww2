"""The map as the rules see it (docs/RULES.md §3), read from data/map.json."""
from mapgen.hexgrid import distance, neighbour, side

IMPASSABLE = "~vs"                  # sea, depression, sand sea (3.1.2)
ROUGH = "^"
ROAD, TRACK = 2, 3                  # a link's kind is its haul cost (6.4.1)
WEST_ENTRY = (3, 30)                # El Agheila, where Tripoli joins the map (3.5.1)
BASE = {"axis": WEST_ENTRY}         # the Commonwealth's is Alexandria, set from the map (3.5.3)

__all__ = ["GameMap", "distance", "neighbour", "side"]


class GameMap:
    def __init__(self, data):
        self.cols, self.rows = data["cols"], data["rows"]
        self.terrain = data["terrain"]
        scarps = {(c, r, d): high for c, r, d, high in data["escarpments"]}
        self.passes = {(p["col"], p["row"], p["side"]) for p in data["passes"]}
        self.cliffs = set(scarps) - self.passes                                   # 3.2.3
        self.high = {s: ((s[0], s[1]) if high == 0 else neighbour(*s)) for s, high in scarps.items()}
        self.links = {}                                                           # 3.3.1
        self.rail = []
        for route in data["routes"]:
            hexes = [tuple(h) for h in route["hexes"]]
            if route["kind"] == "rail":
                self.rail = hexes                                                 # 3.3.2
                continue
            kind = ROAD if route["kind"] == "road" else TRACK
            for a, b in zip(hexes, hexes[1:]):
                self.links[a, b] = self.links[b, a] = min(kind, self.links.get((a, b), TRACK))
        self.on_route = {a for a, _ in self.links}
        self.places = {p["name"]: dict(p, hex=(p["col"], p["row"])) for p in data["places"]}
        self.ports = sorted((p["hex"], name) for name, p in self.places.items() if p["kind"] == "port")
        self.town_hexes = {p["hex"] for p in self.places.values() if p["kind"] in ("port", "town")}   # 3.4.1
        self.base = dict(BASE, cw=self.places["Alexandria"]["hex"])
        self.path_cache = {}

    def on_map(self, h):
        return 0 <= h[0] < self.cols and 0 <= h[1] < self.rows

    def passable(self, h):
        return self.on_map(h) and self.terrain[h[1]][h[0]] not in IMPASSABLE      # 3.1.2, 3.1.3

    def rough(self, h):
        return self.terrain[h[1]][h[0]] == ROUGH

    def around(self, h):
        """(direction, neighbour, hexside) for each passable neighbour, directions 0 to 5 (1.8)."""
        out = []
        for d in range(6):
            n = neighbour(h[0], h[1], d)
            if self.passable(n):
                out.append((d, n, side(h[0], h[1], d)))
        return out

    def side_between(self, a, b):
        for d in range(6):
            if neighbour(a[0], a[1], d) == b:
                return side(a[0], a[1], d)
        return None

    def cliff_between(self, a, b):
        return self.side_between(a, b) in self.cliffs
