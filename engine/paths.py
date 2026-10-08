"""What a step costs and the least-cost way (docs/RULES.md §6.4, §9.2, §9.3)."""
import heapq

from .gamemap import ROAD
from .weather import RAIN_COST_PCT

PASS_COST = 2           # crossing a pass, in addition
FOOT_CLIFF_COST = 8     # a foot unit crossing a cliff, in addition
OPEN_COST = 4           # into desert or oasis; along any link for a vehicle not on a road march
ROUGH_COST = 8          # a vehicle into rough, off a link

FOOT_ROAD_COST = 3      # a foot unit on a road march, along a road link
FOOT_TRACK_COST = 4     # ...and along a track link: no faster than the open desert

VEHICLE, MARCH, FOOT, HAUL, FOOT_MARCH = "vehicle", "march", "foot", "haul", "foot_march"
MUD = {"vehicle_mud": VEHICLE, "march_mud": MARCH}      # a vehicle's two ways of going, in rain (21.4.4)
IN_RAIN = {dry: wet for wet, dry in MUD.items()}


def step_cost(gmap, a, b, hexside, mode):
    """The cost of the step from a into the adjacent passable hex b, or None if it cannot be made.
    9.3 for units (MP), 6.4.1 for supply (haul cost)."""
    link = gmap.links.get((a, b))
    if mode in MUD:                                      # rain: off the road a vehicle is in mud
        cost = step_cost(gmap, a, b, hexside, MUD[mode])
        return cost if cost is None or link == ROAD else cost * RAIN_COST_PCT // 100
    if hexside in gmap.cliffs:
        if mode != FOOT:
            return None
        return OPEN_COST + FOOT_CLIFF_COST
    extra = PASS_COST if hexside in gmap.passes else 0
    if mode == FOOT:
        return OPEN_COST + extra
    if mode == MARCH:
        return None if link is None else link + extra
    if mode == FOOT_MARCH:                               # on the march: by road or track, never across country
        return None if link is None else (FOOT_ROAD_COST if link == 2 else FOOT_TRACK_COST) + extra
    if link is not None:
        return (link if mode == HAUL else OPEN_COST) + extra
    return (ROUGH_COST if gmap.rough(b) else OPEN_COST) + extra


def least_path(gmap, start, goal, mode):
    """The hexes after start on the least-cost way to goal, or None (9.2.1).
    Ties: fewer hexes, then the list that comes first hex by hex (9.2.2)."""
    if start == goal:
        return []
    key = (start, goal, mode)
    if key not in gmap.path_cache:                    # the way depends on the map alone
        gmap.path_cache[key] = _least_path(gmap, start, goal, mode)
    path = gmap.path_cache[key]
    return None if path is None else list(path)


def _least_path(gmap, start, goal, mode):
    best = {start: (0, 0, ())}
    heap = [(0, 0, (), start)]
    while heap:
        cost, n, path, cur = heapq.heappop(heap)
        if best[cur] != (cost, n, path):
            continue
        if cur == goal:
            return list(path)
        for _, nxt, hexside in gmap.around(cur):
            c = step_cost(gmap, cur, nxt, hexside, mode)
            if c is None:
                continue
            label = (cost + c, n + 1, path + (nxt,))
            if nxt not in best or label < best[nxt]:
                best[nxt] = label
                heapq.heappush(heap, label + (nxt,))
    return None


def route(came, goal):
    """The hexes from the start to goal along the paths haul_distances found."""
    out = [goal]
    while came.get(out[-1]) is not None:
        out.append(came[out[-1]])
    return out[::-1]


def haul_distances(gmap, start, blocked=frozenset(), limit=None, came=None):
    """Haul distance from start to every hex a supply path reaches (6.4.3).
    No path enters a blocked hex; a blocked start reaches nothing.
    Given a dict as came, it is filled with each hex's previous hex on its least path."""
    if start in blocked or not gmap.passable(start):
        return {}
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, cur = heapq.heappop(heap)
        if d > dist[cur]:
            continue
        for _, nxt, hexside in gmap.around(cur):
            if nxt in blocked:
                continue
            c = step_cost(gmap, cur, nxt, hexside, HAUL)
            if c is None or (limit is not None and d + c > limit):
                continue
            if d + c < dist.get(nxt, 1 << 60):
                dist[nxt] = d + c
                if came is not None:
                    came[nxt] = cur
                heapq.heappush(heap, (d + c, nxt))
    return dist
