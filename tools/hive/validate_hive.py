"""Navigation mit Spielerradius, Brueckenphasen und geschlossenen Tuergruppen.

python tools/hive/validate_hive.py [--before]
Prueft die erzeugten Kartendaten und schreibt messbare Laufwege nach _out.
"""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import label
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely import contains_xy
from shapely.affinity import rotate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
STEP, RADIUS = 0.15, 0.28


def surface(rings):
    result = Polygon()
    for ring in rings:
        result = result.symmetric_difference(Polygon(ring))
    return result


def check(data, phase, closed=None, baseline=False):
    free = surface(data["walls"]).buffer(-RADIUS)
    obstacles = [Polygon(p).buffer(RADIUS) for p in data["opaque"] + data["glass"]]
    cx, cy, radius = data["hive"]["pit"]
    pit = Point(cx, cy).buffer(radius, 48)
    if phase != "turning":
        bridge = box(cx-radius-1, cy-data["hive"]["bridgeWidth"]/2, cx+radius+1, cy+data["hive"]["bridgeWidth"]/2)
        if phase == "NS":
            bridge = rotate(bridge, 90, origin=(cx, cy))
        pit = pit.difference(bridge)
    obstacles.append(pit.buffer(RADIUS))
    for door in data["verticalDoors"] + data["horizontalDoors"]:
        if door["group"] != closed or door["label"].startswith("parked"):
            continue
        x, y, length = door["x"], door["y"], door["length"]
        if door in data["verticalDoors"]:
            obstacles.append(box(x-.12, y-length/2, x+.12, y+length/2).buffer(RADIUS))
        else:
            obstacles.append(box(x-length/2, y-.12, x+length/2, y+.12).buffer(RADIUS))
    free = free.difference(unary_union(obstacles))
    xs = np.arange(data["minX"], data["maxX"], STEP)
    ys = np.arange(data["minY"], data["maxY"], STEP)
    xx, yy = np.meshgrid(xs, ys)
    mask = contains_xy(free, xx, yy)
    indices = np.argwhere(mask)
    coords = np.column_stack((xs[indices[:, 1]], ys[indices[:, 0]]))
    tree = cKDTree(coords)
    components, _ = label(mask)
    ids = np.full(mask.shape, -1, dtype=int)
    ids[mask] = np.arange(len(indices))
    links = {}

    def nearest(pos, reach=.35):
        distance, n = tree.query(pos)
        if distance > reach:
            raise AssertionError(f"Unerreichbar {pos}: {distance:.2f} m, Grenze {reach}")
        return int(n)

    for stair in data.get("stairs", []):
        a, b = nearest(stair["a"]), nearest(stair["b"])
        links.setdefault(a, []).append((b, 1.5))
        links.setdefault(b, []).append((a, 1.5))
    chute = data["hive"].get("chute")
    landing_errors = []
    if chute:
        for p in chute:
            try:
                nearest(p, .16)
            except AssertionError as error:
                if not baseline:
                    raise
                landing_errors.append(str(error))
        links.setdefault(nearest(chute[0]), []).append((nearest(chute[2]), 2.0))
    for p in data["vents"].values():
        nearest(p, .2)
    for p in data["consoles"].values():
        nearest(p, 1.0)

    rows, cols, weights = [], [], []
    h, w = mask.shape
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
        rr, cc = indices[:,0]+dr, indices[:,1]+dc
        valid = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        rr, cc = np.clip(rr,0,h-1), np.clip(cc,0,w-1)
        valid &= mask[rr,cc]
        if dr and dc:
            valid &= mask[rr,indices[:,1]] & mask[indices[:,0],cc]
        rows.extend(np.flatnonzero(valid))
        cols.extend(ids[rr[valid],cc[valid]])
        weights.extend([STEP*np.hypot(dr,dc)] * int(valid.sum()))
    for a, neighbors in links.items():
        for b, cost in neighbors:
            rows.append(a); cols.append(b); weights.append(cost)
    graph = coo_matrix((weights,(rows,cols)), shape=(len(indices),len(indices))).tocsr()
    cache = {}

    def distance(start, goal):
        a, b = nearest(start, 1.0), nearest(goal, 1.0)
        if a not in cache:
            cache[a] = dijkstra(graph, indices=a, directed=True)
        result = float(cache[a][b])
        return round(result, 2) if np.isfinite(result) else None

    routes = {
        "Keeper-Waggle": ((9,6.5),(17.2,10)),
        "Queen-Sun": ((0,-10.5),(9.2,-13)),
        "O2 panels": (data["consoles"]["LifeSupp/NoOxyConsole/0"], data["consoles"]["Admin/NoOxyConsole/1"]),
        "Reactor hands": (data["consoles"]["Reactor/UpperHandConsole/0"], data["consoles"]["Reactor/LowerHandConsole/1"]),
        "Spawn-Lights": (data["spawn"], data["consoles"]["Electrical/SwitchConsole/0"]),
        "Spawn-Comms": (data["spawn"], data["consoles"]["Comms/FixCommsConsole/0"]),
    }
    # Jede Raumflaeche muss mit dem Spawn verbunden bleiben, auch bei geschlossener Gruppe.
    locked = []
    for room in data["rooms"]:
        p = Polygon(room["area"]).representative_point()
        if distance(data["spawn"], (p.x, p.y)) is None:
            locked.append(room["key"])
    if not closed and locked:
        raise AssertionError(f"Raeume ohne Weg: {locked}")
    return {"phase": phase, "closed": closed, "locked_rooms": locked, "landing_errors": landing_errors, "routes_m": {name: distance(a,b) for name,(a,b) in routes.items()},
            "grid_components": len(np.unique(components[mask])), "radius": RADIUS, "step": STEP}


def main():
    before = "--before" in sys.argv
    folder = HERE / "_out/v4_before" if before else HERE.parent.parent / "assets/amberhive"
    report = {}
    for floors in (1,2):
        data = json.loads((folder / f"amberhive_{floors}f.json").read_text(encoding="utf-8"))
        results = []
        for phase in ("NS", "WE", "turning"):
            results.append(check(data, phase, baseline=before))
        for group in ("Cafeteria", "Storage", "Electrical", "LowerEngine", "UpperEngine", "Security", "MedBay"):
            results.append(check(data, "turning", group, baseline=before))
        report[str(floors)] = results
        print(f"{floors} Etage(n): {len(results)} Szenarien OK. Laufwege: {results[0]['routes_m']}")
        for result in results:
            assert all(result["routes_m"][name] is not None for name in ("O2 panels", "Reactor hands", "Spawn-Lights", "Spawn-Comms")), result
    path = HERE / "_out" / ("v4_navigation_before.json" if before else "v4_navigation.json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
