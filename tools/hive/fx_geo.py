# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# fx_geo.py - flache Formen fuer die Laufzeitbilder von Amberhive (gerendert von blender/fx_build.py):
#   bridge          Drehbruecke (Draufsicht, Laenge in x), task_hive_bridge.png
#   flood_<i>       Honiglache je Flutzone (genau so gross wie die Zone), task_hive_flood_<i>.png
# Schreibt _out/fx.json: [{"name", "bounds", "ppm", "shapes"}].

import json
import math
import random

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import gen_hive as G
from floor_geo import no_holes, orient
import hive_layout as L

ITEMS = []


def shapes_of(geom, z, mat, coll="floor", tint=None):
    out = []
    pieces = []
    for p in G.parts(geom):
        if p.area >= 1e-4:
            pieces += no_holes(p)
    for p in pieces:
        p = orient(p, 1.0)
        sh = {"pts": [[round(x, 4), round(y, 4)] for x, y in list(p.exterior.coords)[:-1]],
              "holes": [[[round(x, 4), round(y, 4)] for x, y in list(h.coords)[:-1]] for h in p.interiors],
              "z0": z, "z1": z, "mat": mat, "coll": coll, "side": mat}
        if tint is not None:
            sh["tint"] = round(tint, 3)
        out.append(sh)
    return out


def hexagon(cx, cy, r):
    return Polygon([(cx + r * math.cos(math.pi / 3 * i), cy + r * math.sin(math.pi / 3 * i)) for i in range(6)])


def bridge():
    """Drehbruecke (Stil V2): ruhige Dielen wie der Hallenboden, Messinggelaender mit Bernsteinknoepfen, Wabe in der Mitte.
    Das Bild dreht sich im Spiel, deshalb reine Draufsicht ohne gerichtetes Licht."""
    r = L.PIT[2]
    length = 2 * r + 1.4
    w = L.BRIDGE_W
    sh = []
    x0, x1 = -length / 2, length / 2
    sh += shapes_of(box(x0, -w / 2, x1, w / 2), 0.0, "wood_dark", "deco")
    rnd = random.Random(7)
    n = int((length - 0.24) / 0.30)
    step = (length - 0.24) / n
    for k in range(n):
        a = x0 + 0.12 + k * step + 0.012
        jy = rnd.uniform(-0.02, 0.02)
        sh += shapes_of(box(a, -w / 2 + 0.15 + jy, a + step - 0.024, w / 2 - 0.15 + jy), 0.01,
                        rnd.choice(["fl_plank", "fl_plank_c", "fl_plank_b"]), tint=1.0 + rnd.uniform(-0.07, 0.07))
    for ex in (x0, x1 - 0.12):                                    # Messingschwellen an den Enden
        sh += shapes_of(box(ex, -w / 2, ex + 0.12, w / 2), 0.012, "brass_dark", "decal")
    sh += shapes_of(hexagon(0, 0, 0.5), 0.02, "fl_inlay", "decal")            # Wabe in der Mitte
    sh += shapes_of(hexagon(0, 0, 0.4), 0.021, "fl_plank_c")
    sh += shapes_of(hexagon(0, 0, 0.17), 0.022, "lake", "decal")
    sh += shapes_of(Point(-0.04, 0.04).buffer(0.05, 12), 0.023, "lake_light")
    for side in (-1, 1):
        y = side * (w / 2 - 0.07)
        sh += shapes_of(LineString([(x0 + 0.1, y), (x1 - 0.1, y)]).buffer(0.04), 0.03, "brass", "deco")
        sh += shapes_of(LineString([(x0 + 0.12, y + 0.012), (x1 - 0.12, y + 0.012)]).buffer(0.01), 0.031, "wax_light")
        for k in range(5):
            px = x0 + 0.16 + k * (length - 0.32) / 4
            sh += shapes_of(hexagon(px, y, 0.1), 0.04, "brass_dark", "deco")
            sh += shapes_of(Point(px, y).buffer(0.052, 14), 0.041, "amber_glass")
            sh += shapes_of(Point(px - 0.016, y + 0.016).buffer(0.018, 8), 0.042, "white")
    ITEMS.append({"name": "task_hive_bridge", "bounds": [x0 - 0.05, -w / 2 - 0.1, x1 + 0.05, w / 2 + 0.1], "ppm": 100, "shapes": sh,
                  "grain": [1.0, 0.14, 1.0]})


def flood(i, zone):
    """Honiglache (Stil V2): dunkler Saum, satter Honig, helle Mitte, Schlieren, Glanzlichter und Blasen."""
    xs = [p[0] for p in zone]
    ys = [p[1] for p in zone]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    rnd = random.Random(100 + i)
    blobs = []
    w, h = bx1 - bx0, by1 - by0
    n = int(w * h / 0.9) + 6
    for _ in range(n):
        cx, cy = rnd.uniform(bx0 + 0.3, bx1 - 0.3), rnd.uniform(by0 + 0.3, by1 - 0.3)
        room = min(cx - bx0, bx1 - cx, cy - by0, by1 - cy) - 0.12
        r = min(rnd.uniform(0.45, 0.9), room)
        if r > 0.15:
            blobs.append(Point(cx, cy).buffer(r, 24))
    pool = unary_union(blobs).buffer(0.12).buffer(-0.12).buffer(0)          # ganz innerhalb der Zone, runde Raender
    sh = shapes_of(pool, 0.0, "lake_deep", "decal")
    sh += shapes_of(pool.buffer(-0.09), 0.002, "lake")
    sh += shapes_of(pool.buffer(-0.30).buffer(0.06), 0.003, "lake", tint=1.1)
    sh += shapes_of(pool.buffer(-0.52).buffer(0.12), 0.004, "lake_light", tint=0.96)
    inner = pool.buffer(-0.3)
    for _ in range(int(w * h / 1.2) + 3):                                    # Schlieren
        cx, cy = rnd.uniform(bx0 + 0.4, bx1 - 0.4), rnd.uniform(by0 + 0.4, by1 - 0.4)
        a0, rr, span = rnd.uniform(0, 6.28), rnd.uniform(0.35, 0.8), rnd.uniform(0.5, 1.2)
        pts = [(cx + rr * math.cos(a0 + span * k / 10), cy + rr * math.sin(a0 + span * k / 10)) for k in range(11)]
        sh += shapes_of(LineString(pts).buffer(rnd.uniform(0.025, 0.045), cap_style=1).intersection(inner), 0.006, "lake_light")
    for _ in range(int(w * h / 1.6) + 2):                                    # Glanzlichter
        cx, cy = rnd.uniform(bx0 + 0.4, bx1 - 0.4), rnd.uniform(by0 + 0.4, by1 - 0.4)
        rr = rnd.uniform(0.08, 0.18)
        sh += shapes_of(Point(cx, cy).buffer(rr, 16).intersection(inner), 0.008, "glow")
        sh += shapes_of(Point(cx - rr * 0.25, cy + rr * 0.25).buffer(rr * 0.38, 10).intersection(inner), 0.009, "white")
    for _ in range(int(w * h / 3.0) + 1):                                    # Blasen
        cx, cy = rnd.uniform(bx0 + 0.4, bx1 - 0.4), rnd.uniform(by0 + 0.4, by1 - 0.4)
        sh += shapes_of(Point(cx, cy).buffer(rnd.uniform(0.05, 0.09), 14).intersection(inner), 0.010, "lake_light", "decal")
    ITEMS.append({"name": f"task_hive_flood_{i}", "bounds": [bx0, by0, bx1, by1], "ppm": 60, "shapes": sh})


def buttons():
    """Benutzen-Knoepfe (256 px, Piktogramm wie bei der Zugkarte): Treppe aus Wachs, Honigrutsche mit Biene."""
    sh = []
    steps = [(0.3, 0.3)]
    n = 5
    for k in range(n):
        x = 0.3 + k * 0.38
        y = 0.3 + (k + 1) * 0.34
        steps += [(x, y), (x + 0.38, y)]
    poly = Polygon(steps + [(0.3 + n * 0.38, 0.3)])
    sh += shapes_of(poly.buffer(0.06, join_style=2), 0.0, "propolis", "deco")
    sh += shapes_of(poly, 0.01, "wax")
    for k in range(n):                                           # Stufenkanten hell
        x = 0.3 + k * 0.38
        y = 0.3 + (k + 1) * 0.34
        sh += shapes_of(box(x, y - 0.07, x + 0.38, y), 0.02, "wax_light")
    for k in range(3):
        cx, cy = 0.8 + k * 0.45, 0.55 + k * 0.18
        sh += shapes_of(Polygon([(cx + 0.11 * math.cos(math.pi / 3 * i), cy + 0.11 * math.sin(math.pi / 3 * i)) for i in range(6)]),
                        0.02, "comb")
    rail = LineString([(0.35, 0.85), (2.25, 2.4)])
    sh += shapes_of(rail.buffer(0.05), 0.03, "brass", "deco")
    for k in range(5):
        x = 0.45 + k * 0.42
        sh += shapes_of(LineString([(x, 0.3 + (k + 1) * 0.34 - 0.1), (x, 0.3 + (k + 1) * 0.34 + 0.33)]).buffer(0.03), 0.025, "brass_dark", "deco")
    ITEMS.append({"name": "task_stairs_button", "bounds": [0.0, 0.0, 2.56, 2.56], "ppm": 100, "shapes": sh})
    sh = []
    arc = [(0.4 + 1.75 * t, 2.15 - 1.65 * (1 - (1 - t) ** 2)) for t in [i / 24 for i in range(25)]]
    tube = LineString(arc)
    sh += shapes_of(tube.buffer(0.3, cap_style=1), 0.0, "propolis", "deco")
    sh += shapes_of(tube.buffer(0.24, cap_style=1), 0.01, "brass")
    sh += shapes_of(tube.buffer(0.13, cap_style=1), 0.02, "honey")
    sh += shapes_of(tube.parallel_offset(0.05, "left").buffer(0.03), 0.03, "honey_light")
    for k, (dx, r) in enumerate(((0.0, 0.11), (0.28, 0.08))):     # Tropfen am Rutschenende
        sh += shapes_of(Point(2.3 + dx, 0.28 - 0.06 * k).buffer(r, 16), 0.02, "honey_deep")
    t = 0.38
    bx, by = 0.4 + 1.75 * t, 2.15 - 1.65 * (1 - (1 - t) ** 2) + 0.3   # kleine Biene auf der Rutsche
    sh += shapes_of(Point(bx + 0.12, by).buffer(0.2, 24), 0.05, "bee_yellow", "deco")
    sh += shapes_of(box(bx + 0.02, by - 0.2, bx + 0.12, by + 0.2).intersection(Point(bx + 0.12, by).buffer(0.2, 24)), 0.06, "bee_black")
    sh += shapes_of(Point(bx - 0.13, by + 0.04).buffer(0.13, 20), 0.05, "bee_yellow", "deco")
    sh += shapes_of(Point(bx - 0.17, by + 0.07).buffer(0.035, 10), 0.07, "black")
    sh += shapes_of(Point(bx + 0.05, by + 0.27).buffer(0.13, 20), 0.07, "wing", "deco")
    ITEMS.append({"name": "task_hive_slide_button", "bounds": [0.0, 0.0, 2.56, 2.56], "ppm": 100, "shapes": sh})


def main():
    buttons()
    bridge()
    import gen_hive
    for i, z in enumerate(gen_hive.FLOOD_ZONES):
        flood(i, z)
    (G.TMP / "fx.json").write_text(json.dumps(ITEMS), encoding="utf-8")
    print("fx items", [it["name"] for it in ITEMS])


if __name__ == "__main__":
    main()
