# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# floor_geo.py - erzeugt die Formen fuer Boden und Wachswaende einer Etage (CPython mit shapely), die blender/floor_build.py
# dann nur noch als Meshes aufbaut und rendert. Schreibt _out/floor_<etage>.json.
#
#   python floor_geo.py ground|crown
#
# Stil V2 (art/STIL_V2.md): Boeden ruhig und wenig gesaettigt (fl_*), Wandkrone dunkel mit hellem Wachskragen,
# Stirnseiten als warm leuchtendes Honigwachs. Raum- und Wandformen, Grenzen und Bildgroessen sind unveraendert.
#
# Formen: {"pts": [[x,y],..], "holes": [[[x,y],..],..], "z0": .., "z1": .., "mat": Palettenname, "coll": "floor"|"solid"|"deco"}
#   optional "tint" (Helligkeitsfaktor je Form). coll "floor": Belag ohne Linien, "decal": Teppich/See mit feiner Linie,
#   "solid": Wachsmasse (kraeftige Kontur), "deco": Relief/Leisten/Kragen, "flat": Waben auf der Wandkrone (ohne Linie).
#   {"light": [x, y, r], "color", "strength"}: weicher Lichtfleck. {"hexfront": [x, y, z, r], "mat"}: Wabenzelle an der Stirnseite.

import json
import math
import random
import sys

from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

import gen_hive as G
import hive_layout as L

WALL_H = 1.4          # Wandhoehe: Stirnseite 1,4 * K = 0,83 m im Bild

SHAPES = []
TINT = random.Random(77)      # Helligkeitsstreuung je Fliese/Diele (ruhig, +-5 %)


def no_holes(p):
    """Polygon mit Loechern in lochfreie Stuecke schneiden (senkrechter Schnitt durch jedes Loch). Blender fuellt lochfreie
    Vielecke zuverlaessig, sein Scanfill fuer Loecher laesst bei verwinkelten Formen Dreiecke aus."""
    if not p.interiors:
        return [p]
    c = Polygon(p.interiors[0]).representative_point()
    x0, y0, x1, y1 = p.bounds
    out = []
    for half in (box(x0 - 1, y0 - 1, c.x, y1 + 1), box(c.x, y0 - 1, x1 + 1, y1 + 1)):
        for q in G.parts(p.intersection(half)):
            if q.area > 1e-6:
                out += no_holes(q)
    return out


def add(geom, z0, z1, mat, coll, side=None, tint=None):
    pieces = []
    for p in G.parts(geom):
        if p.area < 1e-4:
            continue
        p = p.simplify(0.002, preserve_topology=True)
        pieces += [p] if coll == "solid" else no_holes(p)       # die Wachsmasse bleibt ein Stueck (Seitenwaende, Kontur)
    for p in pieces:
        p = orient(p, 1.0)                                      # aussen gegen den Uhrzeigersinn (Seitenwaende zeigen nach aussen)
        sh = {"pts": [[round(x, 4), round(y, 4)] for x, y in list(p.exterior.coords)[:-1]],
              "holes": [[[round(x, 4), round(y, 4)] for x, y in list(h.coords)[:-1]] for h in p.interiors],
              "z0": round(z0, 4), "z1": round(z1, 4), "mat": mat, "coll": coll, "side": side or mat}
        if tint is not None:
            sh["tint"] = round(tint, 3)
        SHAPES.append(sh)


def light(x, y, r, color="glow", strength=0.15, z=0.014):
    """Weicher Lichtfleck auf dem Boden (floor_build legt ihn als Lichthof ueber den Belag)."""
    SHAPES.append({"light": [round(x, 3), round(y, 3), round(r, 3)], "color": color, "strength": strength, "z": z, "coll": "light"})


def jit(span=0.055):
    return 1.0 + TINT.uniform(-span, span)


def hexagon(cx, cy, r):
    return Polygon([(cx + r * math.cos(math.pi / 3 * i), cy + r * math.sin(math.pi / 3 * i)) for i in range(6)])


def hex_grid(area, r, gap, mats, rnd, weights=None, z=0.0, pick=None):
    """Sechseckfliesen. pick(cx, cy, i, j) darf das Material je Zelle bestimmen (Muster), sonst Zufall/Reihe."""
    x0, y0, x1, y1 = area.bounds
    dx, dy = 1.5 * r, math.sqrt(3) * r
    i = 0
    x = x0 - r
    while x < x1 + r:
        y = y0 - r + (dy / 2 if i % 2 else 0)
        j = 0
        while y < y1 + r:
            cell = hexagon(x, y, r - gap)
            if cell.intersects(area):
                m = pick(x, y, i, j) if pick else None
                if m is None:
                    m = rnd.choices(mats, weights=weights)[0] if weights else mats[(i + j) % len(mats)]
                add(cell.intersection(area), z, z, m, "floor", tint=jit())
            y += dy
            j += 1
        x += dx
        i += 1


def planks(area, w, mats, rnd, angle=0.0, z=0.0):
    c = area.centroid
    a = rotate(area, -angle, origin=c)
    x0, y0, x1, y1 = a.bounds
    y = y0
    while y < y1:
        x = x0 - rnd.uniform(0, 1.2)
        while x < x1:
            ln = rnd.uniform(1.2, 2.6)
            pl = box(x + 0.008, y + 0.009, x + ln - 0.008, y + w - 0.009)
            pl = rotate(pl, angle, origin=c)
            if pl.intersects(area):
                add(pl.intersection(area), z, z, rnd.choice(mats), "floor", tint=jit(0.07))
            x += ln
        y += w


def slabs(area, sx, sy, mats, rnd, z=0.0, jitter=0.03, gap=0.02):
    x0, y0, x1, y1 = area.bounds
    y = y0
    r = 0
    while y < y1:
        x = x0 - (sx / 2 if r % 2 else 0)
        while x < x1:
            jx, jy = rnd.uniform(-jitter, jitter), rnd.uniform(-jitter, jitter)
            s = box(x + gap + jx, y + gap + jy, x + sx - gap, y + sy - gap).buffer(-0.03).buffer(0.03, 3)
            if s.intersects(area):
                add(s.intersection(area), z, z, rnd.choice(mats), "floor", tint=jit(0.06))
            x += sx
        y += sy
        r += 1


def rug(area, c, r, body, border="fl_cream", motif=None):
    """Sechseckiger Teppich: Rand, Feld, Wabenmotiv. Liegt als 'decal' knapp ueber dem Belag."""
    add(hexagon(c[0], c[1], r).intersection(area), 0.004, 0.004, border, "decal")
    add(hexagon(c[0], c[1], r * 0.93).intersection(area), 0.005, 0.005, body, "decal")
    add(hexagon(c[0], c[1], r * 0.80).difference(hexagon(c[0], c[1], r * 0.76)).intersection(area), 0.006, 0.006, border, "floor")
    if motif:
        for k in range(6):
            a = math.pi / 3 * k + math.pi / 6
            add(hexagon(c[0] + r * 0.46 * math.cos(a), c[1] + r * 0.46 * math.sin(a), r * 0.15).intersection(area), 0.006, 0.006,
                motif, "floor")
        add(hexagon(c[0], c[1], r * 0.2).intersection(area), 0.006, 0.006, border, "floor")
        add(hexagon(c[0], c[1], r * 0.13).intersection(area), 0.007, 0.007, motif, "floor")


def ringed(c, band, b):
    """Muster fuer Koeniginnen-Fliesen: Akzentzellen in Ringen um die Raummitte."""
    def pick(x, y, i, j):
        k = int(math.hypot(x - c[0], y - c[1]) / band)
        if k % 3 == 2 and (i + j) % 2 == 0:
            return b
        return None
    return pick


def sun_stone(area, c, rnd):
    add(area, 0, 0, "fl_sun", "floor")
    for i in range(24):                                  # Strahlenfelder als ruhige Keile
        a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 1) / 24
        seg = Polygon([(c[0], c[1]), (c[0] + 9 * math.cos(a0), c[1] + 9 * math.sin(a0)), (c[0] + 9 * math.cos(a1), c[1] + 9 * math.sin(a1))])
        add(seg.intersection(area).buffer(-0.012), 0.0005, 0.0005, "fl_sun" if i % 2 else "fl_sand", "floor", tint=jit(0.03))
    for r0, r1, m in ((0.0, 0.95, "fl_sand_b"), (1.2, 1.36, "fl_inlay"), (2.35, 2.47, "fl_inlay")):
        ring = Point(c).buffer(r1, 64).difference(Point(c).buffer(r0, 64)) if r0 > 0 else Point(c).buffer(r1, 64)
        add(ring.intersection(area), 0.001, 0.001, m, "floor")
    for i in range(12):
        a = math.pi * 2 * i / 12
        ray = Polygon([(c[0] + 1.42 * math.cos(a - 0.06), c[1] + 1.42 * math.sin(a - 0.06)),
                       (c[0] + 2.28 * math.cos(a), c[1] + 2.28 * math.sin(a)),
                       (c[0] + 1.42 * math.cos(a + 0.06), c[1] + 1.42 * math.sin(a + 0.06))])
        add(ray.intersection(area), 0.001, 0.001, "fl_inlay" if i % 3 == 0 else "fl_sand_b", "floor")


def floor_of(key, g, rnd):
    """Belag je Raum. Alle Boeden ruhig und wenig gesaettigt (fl_*-Farben), damit Figuren und Objekte davor stehen."""
    c = (g.centroid.x, g.centroid.y)
    if key == "mead":
        planks(g, 0.30, ["fl_plank", "fl_plank_b", "fl_plank_c"], rnd)
    elif key in ("sundeck", "dock"):
        planks(g, 0.28, ["fl_plank_c", "fl_plank", "fl_sand_b"], rnd)
    elif key == "wasp":
        planks(g, 0.26, ["fl_plank_dark", "fl_plank_b", "fl_plank_dark_b"], rnd)
    elif key == "guard":
        planks(g, 0.24, ["fl_slate", "fl_slate_b", "fl_slate_c"], rnd)
    elif key == "keeper":
        planks(g, 0.22, ["fl_plank_c", "fl_plank", "fl_plank_c"], rnd)
        rug(g, (c[0], c[1] - 0.6), 1.6, "fl_teal", motif="fl_teal_b")
    elif key in ("queen", "archive"):
        hex_grid(g, 0.42, 0.02, ["fl_lilac", "fl_lilac_b"], rnd, weights=[3, 2], pick=ringed(c, 1.1, "fl_violet"))
    elif key == "bellows":
        hex_grid(g, 0.45, 0.022, ["fl_sage", "fl_sage_b", "fl_mint"], rnd, weights=[4, 2, 1])
    elif key == "nursery":
        hex_grid(g, 0.36, 0.02, ["fl_cream", "fl_rose", "fl_mint"], rnd, weights=[5, 2, 1])
    elif key == "waggle":
        hex_grid(g, 0.40, 0.02, ["fl_mint", "fl_cream"], None)
    elif key == "cellar":
        slabs(g, 0.82, 0.6, ["fl_stone", "fl_stone_b", "fl_stone"], rnd)
    elif key == "lamp":
        slabs(g, 0.7, 0.55, ["fl_slate", "fl_slate_b", "fl_slate_c"], rnd)
    elif key in ("wpress", "epress"):
        slabs(g, 0.9, 0.65, ["fl_sand", "fl_sand_b", "fl_sand"], rnd)
    elif key == "foundry":
        slabs(g, 0.5, 0.5, ["fl_clay", "fl_clay_b", "fl_clay"], rnd, jitter=0.0, gap=0.014)
    elif key == "sun":
        sun_stone(g, c, rnd)
    else:
        hex_grid(g, 0.45, 0.022, ["fl_wax", "fl_wax_b", "fl_wax_c"], rnd, weights=[4, 2, 1])
    light(c[0], c[1], 0.52 * math.sqrt(g.area), "glow", 0.13)          # warmer Lichtfleck in der Raummitte


def decals(V, level, rnd):
    """Bodenschmuck ueber den Belaegen: Teppich, Honigflecken, Bluetenblaetter (flach, z leicht erhoeht)."""
    rooms = {k: g for k, (n, s_, g) in V.rooms.items()}
    if level == "ground":
        rug(rooms["mead"], (0.0, 9.6), 3.2, "fl_teal", motif="fl_teal_b")
        for key in ("wpress", "epress"):                              # Honigflecken vor den Pressen
            g = rooms[key]
            cx = g.centroid.x
            for _ in range(5):
                r = rnd.uniform(0.12, 0.3)
                p = Point(cx + rnd.uniform(-1.6, 1.6), -12.6 + rnd.uniform(-0.6, 0.4)).buffer(r, 16)
                add(p.intersection(g), 0.004, 0.004, "lake", "decal")
                add(translate(p.buffer(-r * 0.45), -r * 0.12, r * 0.12).intersection(g), 0.005, 0.005, "lake_light", "floor")
        for key, mats in (("waggle", ["petal_pink", "petal_white", "petal_blue"]), ("bellows", ["pollen", "petal_white"])):
            g = rooms[key].buffer(-0.4)
            x0, y0, x1, y1 = g.bounds
            for _ in range(18):
                p = Point(rnd.uniform(x0, x1), rnd.uniform(y0, y1))
                if not g.contains(p):
                    continue
                petal = rotate(Point(p.x, p.y).buffer(0.07, 8).union(Point(p.x + 0.06, p.y).buffer(0.05, 8)), rnd.uniform(0, 360))
                add(petal, 0.004, 0.004, rnd.choice(mats), "floor")
    else:
        g = rooms["sundeck"].buffer(-0.4)
        x0, y0, x1, y1 = g.bounds
        for _ in range(22):
            p = Point(rnd.uniform(x0, x1), rnd.uniform(y0, y1))
            if g.contains(p):
                add(rotate(Point(p.x, p.y).buffer(0.08, 8).union(Point(p.x + 0.06, p.y).buffer(0.05, 8)), rnd.uniform(0, 360)),
                    0.004, 0.004, rnd.choice(["petal_pink", "petal_white", "pollen"]), "floor")


def honey_lake(rnd):
    """Honigsee: dunkler Rand, helle Mitte, ziehende Schlieren und Glanzlichter; Wachskragen ringsum."""
    R = L.PIT[2]
    add(Point(0, 0).buffer(R + 0.30, 64).difference(Point(0, 0).buffer(R + 0.20, 64)), 0.001, 0.001, "wall_base", "decal")
    add(Point(0, 0).buffer(R + 0.20, 64).difference(Point(0, 0).buffer(R - 0.02, 64)), 0.002, 0.002, "wall_lip", "decal")
    for k, (r, m, t) in enumerate(((R, "lake_deep", 1.0), (R - 0.22, "lake", 0.9), (R - 0.6, "lake", 1.0), (R - 1.1, "lake", 1.1),
                                   (R - 1.65, "lake_light", 0.95))):
        add(Point(0, 0).buffer(r, 64), 0.003 + 0.001 * k, 0.003 + 0.001 * k, m, "decal" if k == 0 else "floor", tint=t)
    for k in range(9):                                               # Schlieren: schmale Sicheln auf Kreisbahnen
        r = rnd.uniform(0.6, R - 0.35)
        a0 = rnd.uniform(0, 2 * math.pi)
        span = rnd.uniform(0.5, 1.3)
        w = rnd.uniform(0.03, 0.06)
        pts = [(r * math.cos(a0 + span * i / 14), r * math.sin(a0 + span * i / 14)) for i in range(15)]
        add(LineString(pts).buffer(w, cap_style=1), 0.009, 0.009, "lake_light" if k % 3 else "glow", "floor")
    add(Point(-0.75, 0.8).buffer(0.34, 32), 0.010, 0.010, "glow", "floor")         # Glanzlicht
    add(Point(-1.2, 0.38).buffer(0.13, 24), 0.010, 0.010, "glow", "floor")
    add(Point(-0.8, 0.86).buffer(0.16, 24), 0.011, 0.011, "white", "floor")
    for _ in range(7):                                               # Blasen
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.4, R - 0.4)
        add(Point(r * math.cos(a), r * math.sin(a)).buffer(rnd.uniform(0.05, 0.09), 14), 0.010, 0.010, "lake_light", "decal")
    light(0.0, 0.0, R + 2.3, "honey_light", 0.26)                     # Bernsteinschein auf dem Brunnenring


def main(level):
    rnd = random.Random(1515)
    bounds = L.GROUND_BOUNDS if level == "ground" else L.CROWN_BOUNDS
    V = G.Variant(2)
    clip = box(*bounds)
    walk = V.walk.intersection(clip).buffer(0)
    # Boden: Raeume nach Art, Gaenge in Wachsfliesen, Brunnenring in Steinplatten
    add(box(bounds[0] - 2.0, bounds[1] - 2.0, bounds[2] + 2.0, bounds[3] + 2.0), -0.006, -0.006, "fl_joint", "floor")   # Fugengrund (ein Rechteck unter allem, keine Luecken)
    room_u = []
    for k, (n, s, g) in V.rooms.items():
        if not g.intersects(clip):
            continue
        room_u.append(g)
        floor_of(k, g.buffer(0), rnd)
    decals(V, level, rnd)
    halls = walk.difference(unary_union(room_u)).buffer(0)
    if level == "ground":
        well = Polygon(L.WELL).buffer(0)
        pit = Point(L.PIT[0], L.PIT[1]).buffer(L.PIT[2], 64)
        ring = well.difference(pit)
        halls = halls.difference(well).buffer(0)
        inner = Point(0, 0).buffer(3.9, 64)
        for i in range(24):                               # Brunnenring: radiale Steinplatten in zwei Kraenzen
            a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 1) / 24
            seg = Polygon([(0, 0), (8 * math.cos(a0), 8 * math.sin(a0)), (8 * math.cos(a1), 8 * math.sin(a1))])
            add(seg.intersection(ring).intersection(inner).buffer(-0.022), 0, 0, "fl_stone" if i % 2 else "fl_stone_b", "floor", tint=jit())
            add(seg.intersection(ring).difference(inner).buffer(-0.022), 0, 0, "fl_sand_b" if i % 2 else "fl_stone", "floor", tint=jit())
        honey_lake(rnd)
    hex_grid(halls, 0.45, 0.022, ["fl_wax", "fl_wax_b", "fl_wax_c"], rnd, weights=[4, 2, 1])
    # Wachsmasse: alles ausserhalb der Begehbarkeit, als Prisma. Obenauf dunkle, ruhige Waben (sie liegen im Sichtschatten
    # und sollen nicht lauter sein als die Raeume), heller Wachskragen an der Kante, einzelne Zellen voll leuchtendem Honig.
    solid = clip.buffer(2.0).difference(walk).buffer(0)
    add(solid, 0.0, WALL_H, "wall_top", "solid", side="wall_front")
    add(solid.difference(solid.buffer(-0.13)).intersection(walk.buffer(0.4)), WALL_H + 0.001, WALL_H + 0.001, "wall_lip", "deco")
    top = solid.buffer(-0.24)
    x0, y0, x1, y1 = top.bounds
    r = 0.42
    dx, dy = 1.5 * r, math.sqrt(3) * r
    near = walk.buffer(1.6)
    i = 0
    x = x0
    while x < x1 + r:
        y = y0 + (dy / 2 if i % 2 else 0)
        while y < y1 + r:
            cell = hexagon(x, y, r - 0.05)
            if top.contains(cell):
                m = rnd.choices(["wall_cell", "wall_cell_b", "wall_cell_c"], weights=[4, 4, 2])[0]
                lit = near.contains(Point(x, y)) and rnd.random() < 0.04
                add(cell, WALL_H + 0.002, WALL_H + 0.002, "wall_glow" if lit else m, "flat", tint=jit(0.08))
                if lit:
                    add(hexagon(x - 0.05, y + 0.06, r * 0.42), WALL_H + 0.003, WALL_H + 0.003, "lake_light", "flat")
                    light(x, y, 0.85, "honey_light", 0.22, z=WALL_H + 0.01)
            y += dy
        x += dx
        i += 1
    # Fussleiste an den Stirnseiten (Nordwaende): schmales dunkles Band am Wandfuss
    front_edges = []
    for p in G.parts(walk):
        for ring_ in [p.exterior] + list(p.interiors):
            cs = list(ring_.coords)
            for a, b in zip(cs, cs[1:]):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if solid.contains(Point(mx, my + 0.05)) and walk.contains(Point(mx, my - 0.05)) and abs(b[1] - a[1]) < 0.6 * abs(b[0] - a[0]) + 1e-6:
                    front_edges.append((a, b))
    for a, b in front_edges:
        seg = LineString([a, b])
        band = seg.buffer(0.05, cap_style=2).intersection(solid.buffer(0.06)).buffer(0)
        add(band, 0.0, 0.15, "wall_base", "deco")
        # Wabenrelief auf der Stirnseite: Zellen in kleinen Trauben, einige aus leuchtendem Bernstein
        n = int(seg.length / 0.5)
        for k in range(n):
            if rnd.random() < 0.5:
                continue
            t = (k + 0.5) / max(1, n)
            px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            zc = rnd.uniform(0.5, 1.05)
            rr = rnd.uniform(0.11, 0.16)
            glowing = rnd.random() < 0.3
            for q, (ox, oz) in enumerate(((0.0, 0.0), (1.6, 0.9), (-1.6, 0.9), (0.0, 1.8))[:rnd.choice([1, 2, 3, 3, 4])]):
                SHAPES.append({"hexfront": [round(px + ox * rr, 3), round(py - 0.01, 3), round(min(1.22, zc + oz * rr - 0.15), 3), round(rr, 3)],
                               "mat": "wall_glow" if (glowing and q == 0) else rnd.choice(["wall_front_b", "wall_lip", "wall_front_b"]),
                               "coll": "deco"})
    out = {"bounds": list(bounds), "wall_h": WALL_H, "shapes": SHAPES}
    (G.TMP / f"floor_{level}.json").write_text(json.dumps(out), encoding="utf-8")
    print(level, "shapes", len(SHAPES))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ground")
