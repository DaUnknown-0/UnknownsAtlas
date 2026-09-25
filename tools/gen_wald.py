# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_wald.py - Forststation Nadelkamm (Grundriss v6): wald_layout.py -> Bodenkacheln, Objekte,
# Minimap, src/AtlasWaldData.cs und src/AtlasWaldLayout.cs (gleiches Format wie das Museum).
#
#   python tools/gen_wald.py
#
# Zeichnen mit den Werkzeugen aus museum_art.py (OpList, Prop, Umrisse, AO) im Among-Us-Stil:
# Wald = dichte Baumkronen als Wandmasse, Nordkanten zeigen Stamm-/Blockhausfront, Holzgebaeude
# ohne Dach (Draufsicht in den Raum wie Polus), Lichtungen Gras, Wege Erde, Hoefe Kies.

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import translate
from shapely.ops import unary_union

import museum_art as A
import wald_layout as W
import wald_geo as G
import map_labels

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ASSETS = PROJECT / "assets"
OUT_DATA = PROJECT / "src" / "AtlasWaldData.cs"
OUT_LAYOUT = PROJECT / "src" / "AtlasWaldLayout.cs"
PREVIEW = HERE / "_wald"

FLOOR_PPM = 160
FLOOR_TILES = (5, 4)
PROP_PPM = 160
BX0, BY0, BX1, BY1 = W.BOUNDS

OUTLINE = A.OUTLINE
lift, shade, alpha, hexc = A.lift, A.shade, A.alpha, A.hexc

# ------------------------------------------------------------------ Palette (Rollen)
C = {
    "wald_grund": hexc("#16301f"),
    "krone": [hexc("#2c5636"), hexc("#325f3a"), hexc("#28502f"), hexc("#386843")],
    "krone_licht": hexc("#4d8a55"),
    "stamm": hexc("#5a3d24"),
    "stamm_dunkel": hexc("#3e2916"),
    "gras": hexc("#5d7d3c"),
    "gras2": hexc("#6a8a44"),
    "gras3": hexc("#51702f"),
    "halm": hexc("#3f5e27"),
    "erde": hexc("#8a6a45"),
    "erde2": hexc("#7c5e3c"),
    "erde_rand": hexc("#6a4f33"),
    "kiesel": hexc("#a28a68"),
    "kies": hexc("#76694a"),
    "kies2": hexc("#66593c"),
    "diele": [hexc("#a8784a"), hexc("#9c6f44"), hexc("#b0804f")],
    "diele_fuge": hexc("#6a4628"),
    "wand_krone": hexc("#5b3b22"),
    "wand_krone_kante": hexc("#7a5231"),
    "balken": hexc("#8a5d36"),
    "balken_dunkel": hexc("#6a4527"),
    "wasser": hexc("#2f6d9c"),
    "wasser_licht": hexc("#5b9fd0"),
    "fels": hexc("#7e8084"),
    "fels_dunkel": hexc("#5c5e62"),
    "metall": hexc("#6f7a82"),
    "rot": hexc("#a8403a"),
    "blech": hexc("#4f6f5a"),
    # Texturpass: Nadelstreu am Waldrand, Wurzeln, Moos, Astknoten, Stirnholz der Blockecken
    "nadeln": hexc("#6b5a35"),
    "nadeln2": hexc("#7d6a3c"),
    "wurzel": hexc("#4a3320"),
    "moos": hexc("#4f7a3e"),
    "knoten": hexc("#5e3d22"),
    "stirnholz": hexc("#c9a46a"),
    "schilf": hexc("#7f9a3c"),
    "schilf_kolben": hexc("#6a4527"),
}
# Dielenton je Gebaeude (leichte Identitaet)
PLANK_TINT = {"messe": 1.0, "feldstation": 0.95, "labor": 1.08, "saegewerk": 0.9, "lager": 0.93,
              "bootshaus": 0.97, "wachstube": 0.85, "generator": 0.8}


def geom_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def fill(ops, g, col, outline=None, width=A.OUT_W):
    """Flaeche mit Loechern: Aussenring fuellen, Loecher erneut mit dem, was darunter liegt,
    geht in OpList nicht - deshalb Loecher vorher per Zerlegung vermeiden (Streifen)."""
    for p in geom_parts(g):
        if len(p.interiors) == 0:
            ops.poly(list(p.exterior.coords)[:-1], fill=col, outline=outline, width=width)
        else:
            x0, y0, x1, y1 = p.bounds
            n = max(2, int((y1 - y0) / 2.0))
            for i in range(n):
                band = box(x0 - 1, y0 + (y1 - y0) * i / n, x1 + 1, y0 + (y1 - y0) * (i + 1) / n)
                for q in geom_parts(p.intersection(band)):
                    if len(q.interiors) == 0:
                        ops.poly(list(q.exterior.coords)[:-1], fill=col)
            if outline is not None:
                for ring in [p.exterior] + list(p.interiors):
                    ops.line(list(ring.coords), fill=outline, width=width)


# ------------------------------------------------------------------ Boden

def build_floor_ops(walk, water, shells, doors, rooms):
    ops = A.OpList()
    rnd = random.Random(20260923)
    full = box(BX0, BY0, BX1, BY1)
    shell_u = unary_union(shells)
    forest = full.difference(walk).difference(shell_u).difference(water)

    # 1. Waldgrund und Kronendach (Wandmasse)
    fill(ops, full, C["wald_grund"])
    crowns = []
    y = BY1 + 1.0
    while y > BY0 - 1.5:
        x = BX0 - 1.0 + rnd.uniform(0, 1.2)
        while x < BX1 + 1.0:
            r = rnd.uniform(0.95, 1.55)
            c = Point(x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3))
            if forest.buffer(0.55).contains(c):
                crowns.append((c.x, c.y, r))
            x += rnd.uniform(1.25, 1.75)
        y -= rnd.uniform(1.05, 1.35)
    clip = forest.buffer(0.18)   # Kronen haengen minimal ueber den Rand
    for cx, cy, r in crowns:   # Norden zuerst, suedliche Kronen liegen vorne
        disk = Point(cx, cy).buffer(r, 20)
        g = disk.intersection(clip)
        if g.is_empty:
            continue
        col = rnd.choice(C["krone"])
        fill(ops, g, col, outline=OUTLINE, width=0.05)
        hl = Point(cx - r * 0.28, cy + r * 0.28).buffer(r * 0.45, 16).intersection(g)
        fill(ops, hl, alpha(C["krone_licht"], 150))
        # Schattenseite (Suedost) fuer mehr Volumen der Krone
        lo = Point(cx + r * 0.32, cy - r * 0.34).buffer(r * 0.5, 16).intersection(g)
        fill(ops, lo, alpha(shade(col, 0.72), 120))
        for _ in range(3):
            a = rnd.uniform(0, math.tau)
            p = Point(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55)
            if g.contains(p):
                ops.ellipse(p.x, p.y, r * 0.16, r * 0.12, fill=alpha(shade(col, 0.7), 200))

    # 2. Wasser
    fill(ops, water, C["wasser"])
    wx0, wy0, wx1, wy1 = water.bounds
    yy = wy0 + 0.4
    while yy < wy1:
        xx = wx0 + rnd.uniform(0.2, 0.8)
        while xx < wx1 - 0.4:
            ops.line([(xx, yy), (xx + 0.5, yy + 0.04)], fill=alpha(C["wasser_licht"], 180), width=0.05)
            xx += rnd.uniform(0.9, 1.5)
        yy += rnd.uniform(0.6, 1.0)
    # Uferzone: flaches helles Wasser am Westufer, tiefes dunkles Wasser im Osten, Mondspiegelung
    fill(ops, water.intersection(box(wx0, wy0, wx0 + 0.6, wy1)), alpha(C["wasser_licht"], 70))
    fill(ops, water.intersection(box(wx1 - 1.4, wy0, wx1, wy1)), alpha(hexc("#1b3f5c"), 90))
    ops.glow(wx0 + 1.6, (W.DOCK[2] + W.DOCK[4]) / 2, 2.6, A.MOON, 0.22)
    ops.line(list(water.exterior.coords), fill=alpha(hexc("#1b3f5c"), 255), width=0.12)

    # 3. Aussenflaechen: Gras (Lichtungen), Kies (Hoefe), Erde (Wege)
    outdoor = walk.difference(unary_union([box(*b[3]) for b in W.BUILDINGS]).buffer(W.WALL + 0.02))
    fill(ops, outdoor, C["kies"])
    A.speckle(ops, outdoor, 5000, [C["kies2"], shade(C["kies"], 1.12), C["kiesel"]], 0.02, 0.05, seed=5)
    A.speckle(ops, outdoor, 900, [alpha(C["gras3"], 200), alpha(C["halm"], 200)], 0.06, 0.16, seed=6)   # Grasflecken im Waldboden
    # feuchte Senken und groessere Steine im Kies (mit Umriss, damit sie als Steine lesen)
    for _ in range(60):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if outdoor.buffer(-0.5).contains(p):
            ops.ellipse(p.x, p.y, rnd.uniform(0.4, 0.9), rnd.uniform(0.25, 0.5), fill=alpha(C["kies2"], 90))
    for _ in range(170):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if outdoor.buffer(-0.35).contains(p):
            r = rnd.uniform(0.05, 0.11)
            ops.ellipse(p.x, p.y, r, r * 0.72, fill=rnd.choice([C["fels"], C["kiesel"]]), outline=alpha(C["erde_rand"], 220), width=0.02)
            ops.ellipse(p.x - r * 0.25, p.y + r * 0.2, r * 0.4, r * 0.25, fill=alpha((255, 255, 255, 255), 60))
    # Nadelstreu am Waldrand (brauner Saum, der in den Kies auslaeuft)
    litter = outdoor.intersection(forest.buffer(1.1)).buffer(0)
    A.speckle(ops, litter, 2600, [alpha(C["nadeln"], 150), alpha(C["nadeln2"], 130)], 0.03, 0.08, seed=12)
    clearing_polys = [rooms[k][2] for k, *_ in W.CLEARINGS]
    grass = unary_union(clearing_polys)
    fill(ops, grass, C["gras"])
    A.speckle(ops, grass, 2500, [C["gras2"], C["gras3"]], 0.08, 0.22, seed=7)
    # Moosflecken (weich, ohne Umriss) und Nadelstreu unter den Kronen der Lichtung
    for _ in range(90):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if grass.buffer(-0.5).contains(p):
            rr = rnd.uniform(0.3, 0.7)
            ops.ellipse(p.x, p.y, rr, rr * 0.7, fill=alpha(C["moos"], 70))
    A.speckle(ops, grass.intersection(forest.buffer(0.9)).buffer(0), 1400, [alpha(C["nadeln"], 120), alpha(C["nadeln2"], 110)], 0.03, 0.07, seed=14)
    for g in clearing_polys:     # Grasbueschel und ein paar Blumen
        x0, y0, x1, y1 = g.bounds
        for _ in range(int(g.area * 0.9)):
            p = Point(rnd.uniform(x0, x1), rnd.uniform(y0, y1))
            if not g.buffer(-0.3).contains(p):
                continue
            for k in range(3):
                ops.line([(p.x + (k - 1) * 0.05, p.y), (p.x + (k - 1) * 0.09, p.y + 0.17)], fill=C["halm"], width=0.025)
        for _ in range(int(g.area * 0.12)):
            p = Point(rnd.uniform(x0, x1), rnd.uniform(y0, y1))
            if g.buffer(-0.4).contains(p):
                ops.ellipse(p.x, p.y, 0.05, 0.05, fill=rnd.choice([hexc("#e8d96a"), hexc("#e8e8f0"), hexc("#d27ab0")]))
    paths = unary_union([LineString(pts).buffer(W.PATH_W / 2 - 0.35, 16) for pts in W.PATHS]).intersection(outdoor)
    fill(ops, paths.buffer(0.18).intersection(outdoor), C["erde_rand"])
    fill(ops, paths, C["erde"])
    A.speckle(ops, paths, 1600, [C["erde2"], C["kiesel"]], 0.02, 0.06, seed=9)
    for pts in W.PATHS:   # Fahrspuren
        ls = LineString(pts)
        for off in (-0.45, 0.45):
            tr = ls.parallel_offset(off, "left") if ls.length > 0.5 else None
            if tr is not None and not tr.is_empty and tr.geom_type == "LineString":
                seg = tr.intersection(paths.buffer(-0.2))
                for q in ([seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))):
                    if q.geom_type == "LineString" and q.length > 0.3:
                        ops.line(list(q.coords), fill=alpha(C["erde2"], 200), width=0.12)
    # Pfuetzen auf den Wegen und Wurzeln, die vom Waldrand in Weg und Kies kriechen
    for _ in range(8):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if paths.buffer(-0.5).contains(p):
            rx, ry = rnd.uniform(0.25, 0.45), rnd.uniform(0.15, 0.25)
            ops.ellipse(p.x, p.y, rx, ry, fill=alpha(hexc("#3d5a6e"), 150), outline=alpha(C["erde_rand"], 200), width=0.03)
            ops.line([(p.x - rx * 0.5, p.y + ry * 0.35), (p.x - rx * 0.1, p.y + ry * 0.35)], fill=alpha(C["wasser_licht"], 170), width=0.03)
    edge_zone = outdoor.intersection(forest.buffer(1.0)).buffer(0)
    fedge = forest.boundary
    for _ in range(70):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if not edge_zone.contains(p):
            continue
        # Wurzel: kurze Kette aus drei Segmenten, vom naechsten Waldrand weg gerichtet
        q = fedge.interpolate(fedge.project(p))
        dx, dy = p.x - q.x, p.y - q.y
        n = math.hypot(dx, dy) or 1.0
        dx, dy = dx / n, dy / n
        pts = [(q.x, q.y)]
        for k in range(3):
            a = rnd.uniform(-0.5, 0.5)
            step = rnd.uniform(0.25, 0.45)
            pts.append((pts[-1][0] + (dx * math.cos(a) - dy * math.sin(a)) * step, pts[-1][1] + (dx * math.sin(a) + dy * math.cos(a)) * step))
        if all(outdoor.contains(Point(x, y)) for x, y in pts[1:]):
            ops.line(pts, fill=C["wurzel"], width=0.09)
            ops.line(pts[:3], fill=shade(C["wurzel"], 1.45), width=0.03)
    # Ufersteine und Schilf entlang der Westkante des Bachs (auf der Grasseite, nach dem Gras gezeichnet)
    yy = wy0 + 0.5
    while yy < wy1 - 0.4:
        if walk.contains(Point(wx0 - 0.3, yy)):
            if rnd.random() < 0.45:
                r = rnd.uniform(0.08, 0.16)
                ops.ellipse(wx0 - 0.22, yy, r, r * 0.7, fill=C["fels"], outline=OUTLINE, width=0.03)
                ops.ellipse(wx0 - 0.26, yy + r * 0.25, r * 0.45, r * 0.3, fill=shade(C["fels"], 1.18))
            else:
                for k in range(3):
                    bx = wx0 - 0.2 + (k - 1) * 0.07
                    ops.line([(bx, yy - 0.05), (bx + (k - 1) * 0.04, yy + 0.32)], fill=C["schilf"], width=0.03)
                    if k == 1:
                        ops.ellipse(bx, yy + 0.3, 0.025, 0.06, fill=C["schilf_kolben"])
        yy += rnd.uniform(0.5, 0.9)

    # 3b. Bootssteg (ueber dem Wasser, begehbar)
    dx0, dy0, dx1, dy1 = W.DOCK[1:5]
    ops.rect(dx0, dy0 - 0.12, dx1, dy1, fill=(0, 0, 0, 70))
    ops.rect(dx0, dy0, dx1, dy1, fill=hexc("#9a6a3e"), outline=OUTLINE, width=0.06)
    xx = dx0 + 0.3
    while xx < dx1:
        ops.line([(xx, dy0), (xx, dy1)], fill=hexc("#6e4a2a"), width=0.03)
        xx += 0.3
    for px_ in (dx0 + 0.9, dx1 - 0.15):
        for py_ in (dy0 + 0.12, dy1 - 0.12):
            ops.ellipse(px_, py_, 0.12, 0.12, fill=hexc("#5a3d24"), outline=OUTLINE, width=0.03)
    ops.line([(dx1 - 0.35, dy0 + 0.4), (dx1 + 0.4, dy0 + 0.1)], fill=hexc("#d8cfb0"), width=0.04)   # Leine

    # 4. Gebaeude: Wandkrone (Blockbohlen) + Dielenboden
    for key, _n, _s, inner, _d in W.BUILDINGS:
        x0, y0, x1, y1 = inner
        shell = box(x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL)
        fill(ops, shell, C["wand_krone"], outline=OUTLINE, width=0.07)
        # Wandkrone = oberster Blockbalken: Lichtkante an Nord- und Westseite, Schattenkante an Sued/Ost,
        # dazu eine feine Laengsfaser in der Bandmitte
        wx0, wy0, wx1, wy1 = x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL
        ops.line([(wx0 + 0.08, wy1 - 0.1), (wx1 - 0.08, wy1 - 0.1)], fill=C["wand_krone_kante"], width=0.06)
        ops.line([(wx0 + 0.1, wy0 + 0.08), (wx0 + 0.1, wy1 - 0.08)], fill=C["wand_krone_kante"], width=0.06)
        ops.line([(wx0 + 0.08, wy0 + 0.1), (wx1 - 0.08, wy0 + 0.1)], fill=shade(C["wand_krone"], 0.75), width=0.06)
        ops.line([(wx1 - 0.1, wy0 + 0.08), (wx1 - 0.1, wy1 - 0.08)], fill=shade(C["wand_krone"], 0.75), width=0.06)
        for (a, b) in (((wx0 + 0.3, (y1 + wy1) / 2), (wx1 - 0.3, (y1 + wy1) / 2)), ((wx0 + 0.3, (y0 + wy0) / 2), (wx1 - 0.3, (y0 + wy0) / 2)),
                       (((x0 + wx0) / 2, wy0 + 0.3), ((x0 + wx0) / 2, wy1 - 0.3)), (((x1 + wx1) / 2, wy0 + 0.3), ((x1 + wx1) / 2, wy1 - 0.3))):
            ops.line([a, b], fill=alpha(shade(C["wand_krone"], 0.85), 200), width=0.025)
        # Blockecken: ueberstehende Balkenkoepfe mit Stirnholz (Jahresringe)
        for cx_, cy_ in ((wx0 + W.WALL / 2, wy0 + W.WALL / 2), (wx1 - W.WALL / 2, wy0 + W.WALL / 2),
                         (wx0 + W.WALL / 2, wy1 - W.WALL / 2), (wx1 - W.WALL / 2, wy1 - W.WALL / 2)):
            ops.ellipse(cx_, cy_, 0.3, 0.3, fill=C["balken"], outline=OUTLINE, width=0.05)
            ops.ellipse(cx_, cy_, 0.22, 0.22, fill=C["stirnholz"])
            for rr in (0.16, 0.1, 0.05):
                ops.ellipse(cx_, cy_, rr, rr, outline=alpha(C["balken_dunkel"], 200), width=0.02)
            ops.ellipse(cx_ - 0.07, cy_ + 0.07, 0.07, 0.05, fill=alpha((255, 255, 255, 255), 50))
        t = PLANK_TINT.get(key, 1.0)
        cols = [shade(c, t) for c in C["diele"]]
        A.tiles(ops, box(*inner), x0, y0, x1, y1, 1.6, 0.28, cols, shade(C["diele_fuge"], t),
                offset_rows=True, seed=hash(key) % 97, fuge_w=0.025)
        # Astknoten und Maserung in den Dielen
        area = (x1 - x0) * (y1 - y0)
        for _ in range(int(area * 0.35)):
            kx, ky = rnd.uniform(x0 + 0.2, x1 - 0.2), rnd.uniform(y0 + 0.1, y1 - 0.1)
            ops.ellipse(kx, ky, 0.05, 0.035, fill=alpha(shade(C["knoten"], t), 190))
            ops.ellipse(kx, ky, 0.025, 0.017, fill=alpha(shade(C["diele"][0], t * 1.1), 200))
        for _ in range(int(area * 0.6)):
            gx, gy = rnd.uniform(x0 + 0.3, x1 - 0.6), rnd.uniform(y0 + 0.1, y1 - 0.1)
            ops.line([(gx, gy), (gx + rnd.uniform(0.3, 0.7), gy + rnd.uniform(-0.03, 0.03))], fill=alpha(shade(C["diele_fuge"], t), 70), width=0.015)
        # Teppich/Laeufer in Messe und Wachstube (mit Fransen an den Schmalseiten)
        if key == "messe":
            ops.rect(-3.8, -1.6, 3.8, 3.2, fill=alpha(hexc("#8a3a2e"), 230), outline=alpha(hexc("#d9b25c"), 220), width=0.06)
            ops.rect(-3.5, -1.3, 3.5, 2.9, outline=alpha(hexc("#d9b25c"), 160), width=0.03)
            for fy in [ -1.5 + i * 0.2 for i in range(24)]:
                ops.line([(-3.85, fy), (-4.0, fy)], fill=alpha(hexc("#d9b25c"), 200), width=0.03)
                ops.line([(3.85, fy), (4.0, fy)], fill=alpha(hexc("#d9b25c"), 200), width=0.03)
        if key == "wachstube":
            # relativ zum Innenraum (seit der Verkleinerung wandert die Wachstube)
            rx0, ry0, rx1, ry1 = x0 + 2.5, y0 + 1.0, x0 + 6.0, y0 + 5.5
            ops.rect(rx0, ry0, rx1, ry1, fill=alpha(hexc("#3d5a6e"), 200), outline=alpha(hexc("#8fb0c8"), 160), width=0.04)
            for fx in [rx0 + 0.1 + i * 0.2 for i in range(17)]:
                ops.line([(fx, ry0 - 0.05), (fx, ry0 - 0.2)], fill=alpha(hexc("#8fb0c8"), 180), width=0.03)
                ops.line([(fx, ry1 + 0.05), (fx, ry1 + 0.2)], fill=alpha(hexc("#8fb0c8"), 180), width=0.03)
    # Tuerschwellen
    for key, side, a, b, kind, o in doors:
        fill(ops, o, shade(C["diele"][0], 0.8))
        x0, y0, x1, y1 = o.bounds
        if kind == "door":
            if side in "NS":
                ops.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], fill=hexc("#3b4046"), width=0.06)
            else:
                ops.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=hexc("#3b4046"), width=0.06)
        # Fussmatte / Trittbrett vor jeder Oeffnung (aussen), dunkler festgetretener Boden
        mw = 0.45
        if side == "N":
            mat = box(x0 + 0.3, y1, x1 - 0.3, y1 + mw)
        elif side == "S":
            mat = box(x0 + 0.3, y0 - mw, x1 - 0.3, y0)
        elif side == "E":
            mat = box(x1, y0 + 0.3, x1 + mw, y1 - 0.3)
        else:
            mat = box(x0 - mw, y0 + 0.3, x0, y1 - 0.3)
        mat = mat.intersection(walk)
        fill(ops, mat, alpha(C["erde_rand"], 170))
        if not mat.is_empty:
            mx0, my0, mx1, my1 = mat.bounds
            step = 0.12
            if side in "NS":
                xx = mx0 + 0.1
                while xx < mx1 - 0.05:
                    ops.line([(xx, my0 + 0.05), (xx, my1 - 0.05)], fill=alpha(C["erde2"], 150), width=0.03)
                    xx += step
            else:
                yy = my0 + 0.1
                while yy < my1 - 0.05:
                    ops.line([(mx0 + 0.05, yy), (mx1 - 0.05, yy)], fill=alpha(C["erde2"], 150), width=0.03)
                    yy += step

    # 5. Nordkanten: Blockhausfront innen, Stamm-/Buschfront am Waldrand
    solid = full.difference(walk)
    for p in geom_parts(walk):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            for i in range(len(ring) - 1):
                (x0, y0), (x1, y1) = ring[i], ring[i + 1]
                if abs(y1 - y0) > abs(x1 - x0) * 1.5 or math.hypot(x1 - x0, y1 - y0) < 0.05:
                    continue
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                if not (solid.contains(Point(mx, my + 0.05)) and walk.contains(Point(mx, my - 0.05))):
                    continue
                if water.buffer(0.02).contains(Point(mx, my + 0.1)):
                    continue   # Stegkante zum Wasser: keine Waldfront
                in_building = shell_u.contains(Point(mx, my + 0.1))
                fh = W.WALL if in_building else 0.8
                face = Polygon([(x0, y0), (x1, y1), (x1, y1 + fh), (x0, y0 + fh)]).intersection(solid.buffer(0.001))
                if face.is_empty:
                    continue
                if in_building:
                    fill(ops, face, C["balken"])
                    # vier Rundbalken: Fuge unten, Lichtkante oben je Balken, dazu Moos/Lehmfuge
                    for k in range(4):
                        yb = k * fh / 4
                        if k > 0:
                            ops.line([(x0, y0 + yb), (x1, y1 + yb)], fill=C["balken_dunkel"], width=0.035)
                            ops.line([(x0, y0 + yb + 0.015), (x1, y1 + yb + 0.015)], fill=alpha(C["stirnholz"], 60), width=0.012)
                        ops.line([(x0, y0 + yb + fh / 4 - 0.03), (x1, y1 + yb + fh / 4 - 0.03)], fill=alpha(shade(C["balken"], 1.25), 200), width=0.02)
                    a, b = sorted((x0, x1))
                    for _ in range(int((b - a) * 0.8)):
                        kx = rnd.uniform(a + 0.2, b - 0.2)
                        ky = my + rnd.choice([0.06, 0.19, 0.31, 0.44])
                        ops.ellipse(kx, ky, 0.03, 0.025, fill=alpha(C["knoten"], 200))
                else:
                    fill(ops, face, C["stamm_dunkel"])
                    a, b = sorted((x0, x1))
                    xx = a + rnd.uniform(0.1, 0.5)
                    while xx < b - 0.1:
                        w = rnd.uniform(0.16, 0.26)
                        ops.rect(xx - w / 2, my, xx + w / 2, my + fh, fill=C["stamm"], outline=OUTLINE, width=0.03)
                        # Rinde: dunkle Laengsfurche und heller Streifen links
                        ops.line([(xx + w * 0.15, my + 0.08), (xx + w * 0.1, my + fh - 0.08)], fill=C["stamm_dunkel"], width=0.02)
                        ops.line([(xx - w * 0.3, my + 0.1), (xx - w * 0.3, my + fh - 0.1)], fill=alpha(shade(C["stamm"], 1.3), 180), width=0.02)
                        xx += rnd.uniform(0.45, 0.9)
                    for _ in range(int((b - a) * 1.4)):
                        bx = rnd.uniform(a, b)
                        ops.ellipse(bx, my + 0.12, rnd.uniform(0.2, 0.35), 0.18, fill=rnd.choice(C["krone"]), outline=OUTLINE, width=0.03)
                sh = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.3), (x0, y0 - 0.3)]).intersection(walk)
                fill(ops, sh, (0, 0, 0, 55))
    # Umriss der begehbaren Flaeche
    for p in geom_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            ops.line(list(ring.coords), fill=OUTLINE, width=0.08)
    return ops


def render_floor(walk, water, shells, doors, rooms):
    ops = build_floor_ops(walk, water, shells, doors, rooms)
    img = ops.render(BX0, BY0, BX1, BY1, FLOOR_PPM, A.VOID)
    img = A.ambient_occlusion(img, walk, BX0, BY0, BX1, BY1)
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    PREVIEW.mkdir(exist_ok=True)
    img.resize((img.width // 4, img.height // 4), Image.LANCZOS).save(PREVIEW / "floor_preview.jpg", quality=88)
    for old in ASSETS.glob("wald_floor_*.jpg"):
        old.unlink()
    cols, rows = FLOOR_TILES
    tw = (img.width // cols) // 4 * 4
    th = (img.height // rows) // 4 * 4
    tiles = []
    i = 0
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * tw, r * th
            x1 = img.width if c == cols - 1 else x0 + tw
            y1 = img.height if r == rows - 1 else y0 + th
            ww, hh = (x1 - x0) // 4 * 4, (y1 - y0) // 4 * 4
            img.crop((x0, y0, x0 + ww, y0 + hh)).save(ASSETS / f"wald_floor_{i}.jpg", quality=93, subsampling=0)
            tiles.append((i, BX0 + x0 / FLOOR_PPM, BY1 - (y0 + hh) / FLOOR_PPM, ww, hh))
            i += 1
    print(f"floor {img.width}x{img.height} in {len(tiles)} tiles")
    return tiles


# ------------------------------------------------------------------ Objekte

H = {"tisch_lang": 0.8, "herd": 1.0, "regal": 1.9, "laborbank": 1.0, "schrank": 1.9, "saegetisch": 1.0,
     "holzstapel": 1.1, "kisten": 1.1, "boot": 0.8, "monitore": 1.8, "aggregat": 1.3, "fels": 1.2,
     "turm": 3.2, "mast": 4.2, "tank": 3.0, "pumpenhaus": 1.9, "hochsitz": 3.0, "hochsitz_front": 3.0, "baum": 3.2,
     "bank": 0.45, "kartentisch": 0.85, "lagerfeuer": 0.5, "baumstamm": 0.45}
LEGGED = {"bank", "kartentisch", "tisch_lang"}


def bounds(s):
    return A.shape_bounds(s)


def draw_prop(kind, s, idx, ppm):
    x0, y0, x1, y1 = bounds(s)
    if kind == "lagerfeuer":
        # Bild = ganzer Steinring (1,2 m), Kollider = nur die Feuerstelle (wald_layout)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        x0, y0, x1, y1 = mx - 1.2, my - 1.2, mx + 1.2, my + 1.2
    h = H.get(kind, 1.0)
    rnd = random.Random(idx * 131 + len(kind))
    ext = 1.2 if kind == "baum" else (0.9 if kind == "tank" else 0.0)
    p = A.Prop(x0 - ext, y0, x1 + ext, y1, h + (1.0 if kind in ("baum", "tank") else 0.0), ppm)
    c = p.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wood, wood_d = hexc("#9a6a3e"), hexc("#6e4a2a")
    if kind not in LEGGED and kind not in ("lagerfeuer", "hochsitz_front"):
        if s[0] == "rect":
            pts = [(x0 + 0.07, y0 - 0.1), (x1 + 0.1, y0 - 0.1), (x1 + 0.1, y1 - 0.05), (x0 + 0.07, y1 - 0.05)]
        else:
            r = (x1 - x0) / 2
            pts = [(cx + 0.08 + r * math.cos(t * math.pi / 12), cy - 0.08 + r * 0.9 * math.sin(t * math.pi / 12)) for t in range(24)]
        c.soft_shadow(pts, 95, 0.07)
    if kind in LEGGED:
        c.soft_shadow([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 100, 0.06)

    def grain(rx0, ry0, rx1, ry1, col, step=0.12):
        """Bretterfugen auf einer Front- oder Deckflaeche."""
        yy = ry0 + step
        while yy < ry1 - 0.03:
            c.line([(rx0 + 0.02, yy), (rx1 - 0.02, yy)], fill=shade(col, 0.72), width=0.015)
            yy += step

    def lantern(lx, ly, glow=True):
        """Kleine Petroleumlaterne (Deckflaeche): Fuss, Glaskoerper, Buegel, warmer Schein."""
        if glow:
            c.glow(lx, ly + 0.1, 0.8, hexc("#ffb347"), 0.4)
        c.ellipse(lx, ly, 0.08, 0.04, fill=hexc("#3b4046"), outline=OUTLINE, width=0.02)
        c.rect(lx - 0.06, ly, lx + 0.06, ly + 0.18, fill=hexc("#ffd27a"), outline=OUTLINE, width=0.02)
        c.rect(lx - 0.03, ly + 0.03, lx + 0.03, ly + 0.14, fill=hexc("#f08a2a"))
        c.ellipse(lx, ly + 0.2, 0.06, 0.03, fill=hexc("#3b4046"), outline=OUTLINE, width=0.02)
        c.line([(lx - 0.05, ly + 0.2), (lx, ly + 0.3), (lx + 0.05, ly + 0.2)], fill=OUTLINE, width=0.02)

    if kind in ("tisch_lang", "kartentisch", "bank"):
        top = wood if kind != "kartentisch" else hexc("#8a6a4a")
        zt = h
        p.box(x0, y0, x1, y1, zt - 0.08, 0.08, shade(top, 1.15), shade(top, 0.85))
        for lx in (x0 + 0.08, x1 - 0.16):
            p.box(lx, y0 + 0.06, lx + 0.08, y0 + 0.14, 0, zt - 0.08, wood_d, wood_d, w=0.03)
        # Bretterfugen der Platte (laengs)
        ty0, ty1 = y0 + zt * A.K + 0.02, y1 + zt * A.K - 0.02
        yy = ty0 + (ty1 - ty0) / 3
        while yy < ty1 - 0.05:
            c.line([(x0 + 0.03, yy), (x1 - 0.03, yy)], fill=alpha(shade(top, 0.75), 200), width=0.02)
            yy += (ty1 - ty0) / 3
        if kind == "tisch_lang":
            for i in range(6):
                tx = x0 + 0.5 + i * (x1 - x0 - 1.0) / 5
                c.ellipse(tx, y0 + zt * A.K + 0.35, 0.12, 0.09, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.02)
                c.ellipse(tx, y0 + zt * A.K + 0.35, 0.07, 0.05, fill=hexc("#d5cfc2"))
                c.rect(tx + 0.15, y0 + zt * A.K + 0.25, tx + 0.22, y0 + zt * A.K + 0.45, fill=hexc("#c9c9cf"))
                if i % 2 == 0:
                    c.ellipse(tx - 0.2, y0 + zt * A.K + 0.5, 0.05, 0.04, fill=hexc("#b8583a"), outline=OUTLINE, width=0.015)
            lantern(cx, y0 + zt * A.K + 0.42)
        if kind == "bank":
            c.line([(x0 + 0.05, cy + zt * A.K), (x1 - 0.05, cy + zt * A.K)], fill=alpha(shade(top, 0.7), 220), width=0.025)
        if kind == "kartentisch":
            c.rect(x0 + 0.2, y0 + zt * A.K + 0.15, x1 - 0.2, y1 + zt * A.K - 0.15, fill=hexc("#e8dcb4"), outline=OUTLINE, width=0.025)
            for i in range(5):
                c.line([(x0 + 0.4 + i * 0.5, y0 + zt * A.K + 0.3), (x0 + 0.6 + i * 0.45, y1 + zt * A.K - 0.4)], fill=hexc("#6b8c45"), width=0.03)
            for k, (ex, ey, rx, ry) in enumerate(((0.35, 0.55, 0.5, 0.3), (0.35, 0.55, 0.3, 0.17), (0.7, 0.4, 0.35, 0.22))):
                c.ellipse(x0 + (x1 - x0) * ex, y0 + zt * A.K + (y1 - y0) * ey, rx, ry, outline=hexc("#8a7a4a"), width=0.015)
            c.line([(x0 + 0.5, y0 + zt * A.K + 0.4), (x0 + 1.4, y0 + zt * A.K + 1.1), (x1 - 0.7, y0 + zt * A.K + 0.7)], fill=hexc("#a8403a"), width=0.025)
            c.ellipse(cx, cy + zt * A.K, 0.12, 0.12, fill=hexc("#a8403a"), outline=OUTLINE, width=0.02)
            # Kompass, Bleistift, Becher
            c.ellipse(x1 - 0.45, y1 + zt * A.K - 0.4, 0.13, 0.13, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.02)
            c.line([(x1 - 0.45, y1 + zt * A.K - 0.32), (x1 - 0.45, y1 + zt * A.K - 0.48)], fill=hexc("#a8403a"), width=0.02)
            c.line([(x0 + 0.5, y0 + zt * A.K + 0.25), (x0 + 0.95, y0 + zt * A.K + 0.2)], fill=hexc("#e0b04a"), width=0.035)
            c.ellipse(x0 + 0.35, y1 + zt * A.K - 0.35, 0.09, 0.07, fill=hexc("#3f5a6e"), outline=OUTLINE, width=0.02)
    elif kind == "herd":
        body = hexc("#3b3f44")
        p.box(x0, y0, x1, y1, 0, h, body, hexc("#2c3034"))
        zt = y0 + h * A.K
        # Ofenrohr hinten links, Feuerklappe mit Glut vorn, Griffstange, Kochstellen mit Topf und Pfanne
        p.cyl(x0 + 0.3, y1 - 0.3, 0.12, h, 0.9, hexc("#5a6068"), hexc("#3b4046"), w=0.025, ry=0.08)
        c.rect(x0 + 0.2, y0 + 0.1, x0 + 0.75, y0 + 0.42, fill=hexc("#1c1e20"), outline=hexc("#6f7a82"), width=0.025)
        c.rect(x0 + 0.25, y0 + 0.14, x0 + 0.7, y0 + 0.34, fill=hexc("#cf7a36"))
        c.glow(x0 + 0.47, y0 + 0.25, 0.6, hexc("#ffb347"), 0.4)
        for k in range(4):
            c.line([(x0 + 0.28 + k * 0.11, y0 + 0.14), (x0 + 0.28 + k * 0.11, y0 + 0.34)], fill=hexc("#1c1e20"), width=0.02)
        c.line([(x0 + 0.15, y0 + h * A.K - 0.12), (x1 - 0.15, y0 + h * A.K - 0.12)], fill=hexc("#8c9296"), width=0.035)
        c.rect(x1 - 0.7, y0 + 0.1, x1 - 0.2, y0 + 0.42, fill=hexc("#2c3034"), outline=hexc("#6f7a82"), width=0.02)
        c.ellipse(x1 - 0.45, y0 + 0.26, 0.05, 0.05, fill=hexc("#8c9296"), outline=OUTLINE, width=0.015)
        for ox in (0.45, 1.25):
            c.ellipse(x0 + ox, zt + 0.5, 0.22, 0.16, fill=hexc("#1c1e20"), outline=hexc("#6f7a82"), width=0.02)
        c.ellipse(x0 + 0.45, zt + 0.5, 0.18, 0.13, fill=hexc("#6f7a82"), outline=OUTLINE, width=0.02)
        c.ellipse(x0 + 0.45, zt + 0.5, 0.11, 0.08, fill=hexc("#8c9296"))
        c.line([(x0 + 0.62, zt + 0.5), (x0 + 0.85, zt + 0.42)], fill=OUTLINE, width=0.04)
        c.ellipse(x0 + 1.25, zt + 0.5, 0.17, 0.12, fill=hexc("#5a4a3a"), outline=OUTLINE, width=0.02)
        c.ellipse(x0 + 1.25, zt + 0.5, 0.11, 0.07, fill=hexc("#7a5636"))
        c.ellipse(x1 - 0.2, zt + 0.25, 0.1, 0.07, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.02)
    elif kind in ("regal", "schrank", "monitore"):
        body = {"regal": wood, "schrank": hexc("#d8d8d0"), "monitore": hexc("#2c3136")}[kind]
        p.box(x0, y0, x1, y1, 0, h, shade(body, 1.12), body)
        fy1 = y0 + h * A.K - 0.06
        if kind == "regal":
            for lv in range(4):
                ly = y0 + 0.06 + (fy1 - y0) * lv / 4
                c.line([(x0, ly), (x1, ly)], fill=wood_d, width=0.03)
                xx = x0 + 0.08
                while xx < x1 - 0.2:
                    ww = rnd.uniform(0.12, 0.25)
                    col = rnd.choice([hexc("#b0603a"), hexc("#3f6f9a"), hexc("#c9b27a"), hexc("#6b8c45")])
                    hh = rnd.uniform(0.12, 0.2)
                    c.rect(xx, ly + 0.03, xx + ww, ly + hh, fill=col, outline=OUTLINE, width=0.015)
                    c.line([(xx + 0.02, ly + hh - 0.03), (xx + ww - 0.02, ly + hh - 0.03)], fill=shade(col, 1.3), width=0.012)
                    if ww > 0.2:
                        c.rect(xx + 0.03, ly + 0.06, xx + ww - 0.03, ly + 0.09, fill=hexc("#e8e4da"))
                    xx += ww + 0.05
            # oben: Laterne, Probenglaeser, Seilrolle
            zt = y0 + h * A.K
            lantern(x0 + 0.3, zt + 0.25)
            for k in range(3):
                c.rect(x0 + 0.7 + k * 0.2, zt + 0.2, x0 + 0.82 + k * 0.2, zt + 0.42, fill=hexc("#bfe3f5"), outline=OUTLINE, width=0.015)
                c.rect(x0 + 0.7 + k * 0.2, zt + 0.25, x0 + 0.82 + k * 0.2, zt + 0.32, fill=[hexc("#6b8c45"), hexc("#c9a46a"), hexc("#a8403a")][k])
            c.ellipse(x1 - 0.35, zt + 0.32, 0.17, 0.12, fill=hexc("#c9a46a"), outline=OUTLINE, width=0.02)
            c.ellipse(x1 - 0.35, zt + 0.32, 0.06, 0.04, fill=wood_d)
        elif kind == "schrank":
            # Medizinschrank: zwei Tueren mit Griffen, rotes Kreuz auf Weiss, kleine Fusszeile
            c.line([(cx, y0 + 0.05), (cx, fy1)], fill=hexc("#9a9a92"), width=0.02)
            c.rect(x0 + 0.05, y0 + 0.1, x1 - 0.05, fy1 - 0.05, outline=hexc("#b8b8b0"), width=0.015)
            for gx in (cx - 0.08, cx + 0.08):
                c.rect(gx - 0.02, cy - 0.15, gx + 0.02, cy + 0.15, fill=hexc("#6f7a82"), outline=OUTLINE, width=0.012)
            cr = (y0 + 0.62 * (fy1 - y0))
            c.rect(cx - 0.3, cr - 0.3, cx + 0.3, cr + 0.3, fill=hexc("#f0f0ea"), outline=OUTLINE, width=0.02)
            c.rect(cx - 0.07, cr - 0.22, cx + 0.07, cr + 0.22, fill=hexc("#a8403a"))
            c.rect(cx - 0.22, cr - 0.07, cx + 0.22, cr + 0.07, fill=hexc("#a8403a"))
            zt = y0 + h * A.K
            c.rect(x0 + 0.1, zt + 0.2, x1 - 0.1, y1 + h * A.K - 0.2, fill=hexc("#c8c8c0"), outline=alpha(OUTLINE, 120), width=0.015)
        else:
            # Monitorwand: Bildschirme mit Waldbild, Kamera-Nummer und rotem Aufnahmepunkt
            yy = y0 + h * A.K + 0.2
            k = 0
            while yy < y1 + h * A.K - 0.3:
                c.rect(x0 + 0.08, yy, x1 - 0.08, yy + 0.4, fill=hexc("#2b3e34") if k % 3 == 1 else hexc("#3d5a4a"), outline=OUTLINE, width=0.02)
                c.ellipse(x0 + 0.25 + (k % 2) * 0.1, yy + 0.24, 0.1, 0.07, fill=hexc("#6fa070"))
                c.ellipse(x0 + 0.5, yy + 0.2, 0.12, 0.08, fill=hexc("#6fa070"))
                c.poly([(x0 + 0.3, yy + 0.03), (x0 + 0.55, yy + 0.03), (x0 + 0.5, yy + 0.16), (x0 + 0.36, yy + 0.16)], fill=hexc("#a08a68"))
                c.ellipse(x1 - 0.16, yy + 0.33, 0.025, 0.025, fill=hexc("#e05040"))
                c.line([(x0 + 0.12, yy + 0.36), (x0 + 0.3, yy + 0.36)], fill=(255, 255, 255, 110), width=0.015)
                yy += 0.55
                k += 1
            c.glow(cx, cy + h * A.K, 1.6, hexc("#8fd0ff"), 0.22)
    elif kind == "laborbank":
        body = hexc("#b8bcc0")
        p.box(x0, y0, x1, y1, 0, h, hexc("#e0e2e4"), body)
        zt = y0 + h * A.K
        # Front: zwei Schubladen mit Griffen; oben: Spuele mit Hahn, Flaschen, Probenstaender, Mikroskop klein
        for k in range(2):
            fx = x0 + 0.15 + k * (x1 - x0 - 0.3) / 2
            c.rect(fx, y0 + 0.12, fx + (x1 - x0 - 0.3) / 2 - 0.1, y0 + h * A.K - 0.12, outline=hexc("#9aa0a4"), width=0.015)
            c.rect(fx + 0.18, y0 + 0.24, fx + 0.34, y0 + 0.27, fill=hexc("#6f7a82"))
        c.ellipse(x1 - 0.45, zt + 0.5, 0.28, 0.2, fill=hexc("#9aa0a4"), outline=OUTLINE, width=0.02)
        c.ellipse(x1 - 0.45, zt + 0.5, 0.2, 0.13, fill=hexc("#5b9fd0"))
        c.line([(x1 - 0.45, zt + 0.72), (x1 - 0.45, zt + 0.88), (x1 - 0.6, zt + 0.88)], fill=OUTLINE, width=0.05)
        c.line([(x1 - 0.45, zt + 0.72), (x1 - 0.45, zt + 0.88), (x1 - 0.6, zt + 0.88)], fill=hexc("#c0c8cc"), width=0.025)
        for i, col in enumerate(("#6fb86a", "#4a8ac0", "#d27ab0")):
            bx = x0 + 0.3 + i * 0.3
            c.rect(bx, zt + 0.25, bx + 0.15, zt + 0.6, fill=hexc(col), outline=OUTLINE, width=0.015)
            c.rect(bx + 0.04, zt + 0.6, bx + 0.11, zt + 0.68, fill=hexc("#3b4046"))
            c.rect(bx + 0.03, zt + 0.35, bx + 0.12, zt + 0.48, fill=hexc("#e8e4da"))
        c.rect(x0 + 1.25, zt + 0.3, x0 + 1.6, zt + 0.38, fill=wood_d, outline=OUTLINE, width=0.015)
        for k in range(3):
            c.rect(x0 + 1.3 + k * 0.1, zt + 0.36, x0 + 1.35 + k * 0.1, zt + 0.6, fill=hexc("#bfe3f5"), outline=OUTLINE, width=0.012)
    elif kind == "saegetisch":
        p.box(x0, y0, x1, y1, 0, h, shade(wood, 1.15), wood)
        grain(x0 + 0.03, y0 + 0.06, x1 - 0.03, y0 + h * A.K - 0.04, wood, 0.14)
        zt = y0 + h * A.K
        # Saegeblatt mit Zaehnen, Schutzhaube, halb geschnittener Stamm, Saegemehl
        c.ellipse(cx + 0.35, zt + 0.55, 0.9, 0.35, fill=alpha(hexc("#d8c08a"), 150))
        c.ellipse(cx, zt + 0.8, 0.5, 0.5, fill=hexc("#c0c8cc"), outline=OUTLINE, width=0.04)
        for k in range(16):
            a = k * math.tau / 16
            c.line([(cx + 0.48 * math.cos(a), zt + 0.8 + 0.48 * math.sin(a)), (cx + 0.56 * math.cos(a + 0.12), zt + 0.8 + 0.56 * math.sin(a + 0.12))], fill=OUTLINE, width=0.035)
        c.ellipse(cx, zt + 0.8, 0.12, 0.12, fill=hexc("#3b4046"))
        c.poly([(cx - 0.55, zt + 0.85), (cx + 0.55, zt + 0.85), (cx + 0.45, zt + 1.3), (cx - 0.45, zt + 1.3)], fill=hexc("#a8403a"), outline=OUTLINE, width=0.03)
        c.line([(cx - 0.4, zt + 1.22), (cx + 0.4, zt + 1.22)], fill=shade(hexc("#a8403a"), 1.3), width=0.02)
        c.rect(x0 + 0.3, zt + 0.35, x1 - 0.3, zt + 0.55, fill=hexc("#c9a46a"), outline=OUTLINE, width=0.02)
        c.ellipse(x0 + 0.3, zt + 0.45, 0.08, 0.1, fill=hexc("#d8b07a"), outline=OUTLINE, width=0.02)
        c.line([(x0 + 0.5, zt + 0.42), (x1 - 0.5, zt + 0.42)], fill=hexc("#8a6a4a"), width=0.02)
        c.rect(x1 - 0.8, zt + 0.15, x1 - 0.3, zt + 0.3, fill=hexc("#3b4046"), outline=OUTLINE, width=0.02)
        c.ellipse(x1 - 0.45, zt + 0.22, 0.04, 0.04, fill=hexc("#e05040"))
    elif kind in ("holzstapel", "baumstamm"):
        n = int((y1 - y0) / 0.35) if kind == "holzstapel" else 1
        rows = 3 if kind == "holzstapel" else 1
        for r in range(rows):
            z = r * 0.35
            p.box(x0, y0, x1, y1, z, 0.35, shade(wood, 1.1), wood, w=0.035)
            xx = x0 + 0.2
            while xx < x1 - 0.1 and kind == "holzstapel":
                c.ellipse(xx, y0 + (z + 0.17) * A.K, 0.12, 0.1, fill=hexc("#d8b07a"), outline=OUTLINE, width=0.02)
                c.ellipse(xx, y0 + (z + 0.17) * A.K, 0.06, 0.05, outline=hexc("#a8865a"), width=0.012)
                xx += 0.28
        if kind == "baumstamm":
            # Rinde: Laengsfurchen, Aststummel, Stirnholz mit Ringen
            for k in range(3):
                yy = y0 + 0.08 + k * 0.1
                c.line([(x0 + 0.25, yy), (x1 - 0.15, yy + 0.02)], fill=alpha(wood_d, 200), width=0.02)
            c.line([(x0 + 0.1, y1 + 0.35 * A.K - 0.05), (x1 - 0.1, y1 + 0.35 * A.K - 0.06)], fill=alpha(shade(wood, 1.2), 200), width=0.025)
            c.ellipse(x0 + (x1 - x0) * 0.6, y1 + 0.35 * A.K + 0.06, 0.09, 0.06, fill=wood_d, outline=OUTLINE, width=0.025)
            c.ellipse(x0, cy + 0.12, 0.18, 0.2, fill=hexc("#d8b07a"), outline=OUTLINE, width=0.03)
            for rr in (0.12, 0.06):
                c.ellipse(x0, cy + 0.12, rr, rr * 1.1, outline=hexc("#a8865a"), width=0.015)
        else:
            c.rect(x0 - 0.06, y0 + 0.02, x0 + 0.02, y0 + 1.05 * A.K + 0.1, fill=wood_d, outline=OUTLINE, width=0.025)
            c.rect(x1 - 0.02, y0 + 0.02, x1 + 0.06, y0 + 1.05 * A.K + 0.1, fill=wood_d, outline=OUTLINE, width=0.025)
    elif kind == "kisten":
        crate = hexc("#9a7a52")
        p.box(x0, y0, x1, y1, 0, h, shade(crate, 1.15), crate)
        # Kistenstapel: Frontflaeche in Einzelkisten teilen (Kreuzbretter), Schablonenaufdruck, Seil obendrauf
        fy1 = y0 + h * A.K
        n = max(1, int(round((x1 - x0) / 1.1)))
        cw = (x1 - x0) / n
        for k in range(n):
            kx0, kx1 = x0 + k * cw, x0 + (k + 1) * cw
            c.rect(kx0 + 0.04, y0 + 0.04, kx1 - 0.04, fy1 - 0.04, outline=hexc("#6e5234"), width=0.03)
            c.line([(kx0 + 0.04, y0 + 0.04), (kx1 - 0.04, fy1 - 0.04)], fill=hexc("#6e5234"), width=0.03)
            c.line([(kx1 - 0.04, y0 + 0.04), (kx0 + 0.04, fy1 - 0.04)], fill=hexc("#6e5234"), width=0.03)
            c.rect(kx0 + cw * 0.3, y0 + 0.16, kx1 - cw * 0.3, y0 + 0.28, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.012)
            c.line([(kx0 + cw * 0.35, y0 + 0.22), (kx1 - cw * 0.35, y0 + 0.22)], fill=hexc("#3b4046"), width=0.03)
        c.line([(x0 + 0.1, fy1 + (y1 - y0) * 0.5), (x1 - 0.1, fy1 + (y1 - y0) * 0.5)], fill=hexc("#c9a46a"), width=0.05)
        c.line([(x0 + 0.1, fy1 + (y1 - y0) * 0.5), (x1 - 0.1, fy1 + (y1 - y0) * 0.5)], fill=alpha(hexc("#6e5234"), 120), width=0.02)
        c.rect(x0 + 0.02, fy1 - 0.02, x1 - 0.02, fy1 + 0.04, fill=hexc("#3b4046"))
        c.rect(x0 + 0.02, fy1 + (y1 - y0) * 0.5 - 0.15, x1 - 0.02, fy1 + (y1 - y0) * 0.5 - 0.09, fill=alpha(hexc("#3b4046"), 160))
    elif kind == "boot":
        for lx in (x0 + 0.5, x1 - 0.7):
            p.box(lx, y0 + 0.2, lx + 0.2, y1 - 0.2, 0, 0.4, wood_d, wood_d, w=0.03)
        hull = hexc("#b8583a")
        c.ellipse(cx, cy + 0.4 * A.K + 0.15, (x1 - x0) / 2, (y1 - y0) / 2 - 0.1, fill=hull, outline=OUTLINE, width=0.06)
        c.ellipse(cx, cy + 0.4 * A.K + 0.1, (x1 - x0) / 2 - 0.1, (y1 - y0) / 2 - 0.25, fill=shade(hull, 0.85))
        c.ellipse(cx, cy + 0.4 * A.K + 0.2, (x1 - x0) / 2 - 0.3, (y1 - y0) / 2 - 0.4, fill=hexc("#6e4a2a"))
        # Plankenlinien im Rumpf, Sitzbretter, Ruder, Bug-Reling
        for k in range(3):
            yy = cy + 0.4 * A.K + 0.2 + (k - 1) * 0.22
            c.line([(cx - 1.3, yy), (cx + 1.3, yy)], fill=alpha(wood_d, 160), width=0.02)
        for sx in (cx - 0.9, cx - 0.1, cx + 0.7):
            c.rect(sx - 0.1, cy + 0.4 * A.K - 0.2, sx + 0.1, cy + 0.4 * A.K + 0.6, fill=wood, outline=OUTLINE, width=0.025)
        c.line([(cx - 0.8, cy + 0.4 * A.K + 0.2), (cx + 0.8, cy + 0.4 * A.K + 0.2)], fill=wood, width=0.08)
        c.line([(cx + 0.3, cy + 0.4 * A.K + 0.7), (cx + 1.5, cy + 0.4 * A.K + 1.05)], fill=OUTLINE, width=0.06)
        c.line([(cx + 0.3, cy + 0.4 * A.K + 0.7), (cx + 1.5, cy + 0.4 * A.K + 1.05)], fill=hexc("#c9a46a"), width=0.035)
        c.ellipse(cx + 1.5, cy + 0.4 * A.K + 1.05, 0.12, 0.06, fill=hexc("#c9a46a"), outline=OUTLINE, width=0.025)
        c.ellipse(x1 - 0.3, cy + 0.4 * A.K + 0.15, 0.06, 0.06, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.02)
        c.ellipse(x0 + 0.5, cy + 0.4 * A.K + 0.75, 0.22, 0.12, fill=hexc("#e0b04a"), outline=OUTLINE, width=0.025)
    elif kind == "aggregat":
        body = hexc("#d4b13c")
        p.box(x0, y0, x1, y1, 0, h, body, hexc("#b09028"))
        zt = y0 + h * A.K
        # Lueftungsgitter, Bedienfeld mit Lampen, Warnband, Auspuff mit Abgaswolke, Tankdeckel
        c.rect(x0 + 0.2, y0 + 0.2, x0 + 1.0, y0 + 0.55, fill=hexc("#2c3136"), outline=OUTLINE, width=0.02)
        for k in range(6):
            c.line([(x0 + 0.25, y0 + 0.24 + k * 0.055), (x0 + 0.95, y0 + 0.24 + k * 0.055)], fill=hexc("#4f565c"), width=0.015)
        c.rect(x1 - 1.1, y0 + 0.2, x1 - 0.3, y0 + 0.55, fill=hexc("#2c3136"), outline=OUTLINE, width=0.02)
        for k, col in enumerate(("#57d98a", "#ffd27a", "#d84a4a")):
            c.ellipse(x1 - 0.95 + k * 0.22, y0 + 0.44, 0.045, 0.045, fill=hexc(col), outline=OUTLINE, width=0.012)
        c.rect(x1 - 1.0, y0 + 0.26, x1 - 0.4, y0 + 0.33, fill=hexc("#6e4612"), outline=hexc("#e8a83c"), width=0.01)
        c.rect(x0 + 0.1, y0 + 0.06, x1 - 0.1, y0 + 0.14, fill=hexc("#1e1e1e"))
        xx = x0 + 0.1
        while xx < x1 - 0.1:
            c.poly([(xx, y0 + 0.06), (min(x1 - 0.1, xx + 0.1), y0 + 0.06), (min(x1 - 0.1, xx + 0.2), y0 + 0.14), (min(x1 - 0.1, xx + 0.1), y0 + 0.14)], fill=body)
            xx += 0.2
        c.ellipse(x1 - 0.5, zt + 0.4, 0.25, 0.2, fill=hexc("#3b4046"), outline=OUTLINE, width=0.03)
        c.ellipse(x1 - 0.5, zt + 0.4, 0.12, 0.09, fill=hexc("#1c1e20"))
        p.cyl(x0 + 0.5, y1 - 0.4, 0.1, h, 0.6, hexc("#5a6068"), hexc("#3b4046"), w=0.025, ry=0.07)
        for k, (dx, dz, r) in enumerate(((0.05, 0.72, 0.1), (0.16, 0.86, 0.13), (0.3, 1.0, 0.15))):
            c.ellipse(x0 + 0.5 + dx, y1 - 0.4 + (h + dz) * A.K, r, r * 0.8, fill=alpha(hexc("#9aa0a4"), 130))
        c.ellipse(x0 + 1.4, zt + 0.55, 0.12, 0.09, fill=hexc("#a8403a"), outline=OUTLINE, width=0.025)
    elif kind == "fels":
        r = (x1 - x0) / 2
        c.ellipse(cx, cy + 0.3, r, r * 0.8, fill=C["fels"], outline=OUTLINE, width=0.06)
        c.ellipse(cx - r * 0.25, cy + 0.55, r * 0.55, r * 0.4, fill=shade(C["fels"], 1.18))
        c.ellipse(cx + r * 0.3, cy + 0.05, r * 0.4, r * 0.25, fill=C["fels_dunkel"])
        # Risse, Flechten, Moos oben
        c.line([(cx - r * 0.5, cy + 0.2), (cx - r * 0.2, cy + 0.45), (cx - r * 0.1, cy + 0.7)], fill=alpha(C["fels_dunkel"], 220), width=0.03)
        c.line([(cx + r * 0.55, cy + 0.6), (cx + r * 0.3, cy + 0.45)], fill=alpha(C["fels_dunkel"], 220), width=0.03)
        for k, (dx, dy, rr) in enumerate(((0.45, 0.35, 0.18), (-0.55, -0.05, 0.14), (0.1, -0.2, 0.12))):
            c.ellipse(cx + dx * r, cy + 0.3 + dy * r, rr, rr * 0.7, fill=alpha(hexc("#9aa070"), 150))
        c.ellipse(cx + r * 0.2, cy + r * 0.8, r * 0.35, r * 0.18, fill=hexc("#5e7f3e"))
        c.ellipse(cx + r * 0.1, cy + r * 0.85, r * 0.18, r * 0.09, fill=hexc("#6f9a4a"))
    elif kind == "turm":
        for lx in (x0 + 0.1, x1 - 0.3):
            p.box(lx, y0 + 0.1, lx + 0.2, y0 + 0.3, 0, h - 0.6, wood_d, wood_d, w=0.03)
        c.line([(x0 + 0.2, y0 + 0.3), (x1 - 0.2, y0 + (h - 0.8) * A.K)], fill=wood_d, width=0.06)
        c.line([(x1 - 0.2, y0 + 0.3), (x0 + 0.2, y0 + (h - 0.8) * A.K)], fill=wood_d, width=0.06)
        # Leiter an der Front, Kanzel mit Bretterfugen und Gelaender, Dach mit Firstlinie und Schindelreihen
        for k in range(6):
            yy = y0 + 0.4 + k * (h - 0.8) * A.K / 6
            c.line([(cx - 0.18, yy), (cx + 0.18, yy)], fill=wood, width=0.05)
        c.line([(cx - 0.2, y0 + 0.25), (cx - 0.2, y0 + (h - 0.7) * A.K)], fill=wood_d, width=0.05)
        c.line([(cx + 0.2, y0 + 0.25), (cx + 0.2, y0 + (h - 0.7) * A.K)], fill=wood_d, width=0.05)
        p.box(x0 - 0.2, y0, x1 + 0.2, y1, h - 0.6, 0.6, shade(wood, 1.15), wood)
        grain(x0 - 0.17, y0 + (h - 0.6) * A.K + 0.05, x1 + 0.17, y0 + h * A.K - 0.05, wood, 0.11)
        c.rect(x0 - 0.1, y0 + (h - 0.35) * A.K, x1 + 0.1, y0 + (h - 0.15) * A.K, fill=hexc("#1c1e20"))
        for k in range(5):
            xx = x0 - 0.1 + k * (x1 - x0 + 0.2) / 4
            c.line([(xx, y0 + (h - 0.35) * A.K), (xx, y0 + (h - 0.15) * A.K)], fill=wood_d, width=0.03)
        c.poly([(x0 - 0.4, y0 + h * A.K), (x1 + 0.4, y0 + h * A.K), (cx, y1 + (h + 0.9) * A.K)], fill=hexc("#8a3a2e"), outline=OUTLINE, width=0.05)
        for k in range(1, 4):
            t = k / 4
            lx, rx = x0 - 0.4 + (cx - x0 + 0.4) * t, x1 + 0.4 - (x1 + 0.4 - cx) * t
            yy = y0 + h * A.K + (y1 - y0 + 0.9 * A.K) * t
            c.line([(lx, yy), (rx, yy)], fill=alpha(shade(hexc("#8a3a2e"), 0.7), 220), width=0.03)
        c.line([(cx, y0 + h * A.K), (cx, y1 + (h + 0.9) * A.K)], fill=alpha(shade(hexc("#8a3a2e"), 1.25), 200), width=0.03)
    elif kind == "mast":
        p.cyl(cx, cy, 0.35, 0, 0.3, hexc("#8c9296"), hexc("#6f7a82"))
        top = cy + h * A.K
        # Abspannseile, Gittermast mit Diagonalen, Geraetekasten mit LEDs, rotes Gipfellicht mit Schein
        for sx in (-1.0, 1.0):
            c.line([(cx + sx * 0.9, cy - 0.05), (cx + sx * 0.06, top - 0.5)], fill=alpha(hexc("#b8bcc0"), 200), width=0.02)
            c.ellipse(cx + sx * 0.9, cy - 0.05, 0.06, 0.04, fill=hexc("#6f7a82"), outline=OUTLINE, width=0.02)
        c.line([(cx - 0.3, cy + 0.1), (cx, top)], fill=hexc("#b8bcc0"), width=0.06)
        c.line([(cx + 0.3, cy + 0.1), (cx, top)], fill=hexc("#b8bcc0"), width=0.06)
        for k in range(1, 6):
            yy = cy + 0.1 + k * (top - cy - 0.1) / 6
            half = 0.3 * (1 - k / 6)
            yy2 = cy + 0.1 + (k + 1) * (top - cy - 0.1) / 6
            half2 = 0.3 * (1 - (k + 1) / 6)
            c.line([(cx - half, yy), (cx + half, yy)], fill=hexc("#b8bcc0"), width=0.03)
            c.line([(cx - half, yy), (cx + half2, yy2)], fill=alpha(hexc("#b8bcc0"), 180), width=0.02)
        c.glow(cx, top, 0.6, hexc("#e05040"), 0.5)
        c.ellipse(cx, top, 0.12, 0.12, fill=hexc("#e05040"), outline=OUTLINE, width=0.03)
        c.ellipse(cx - 0.04, top + 0.04, 0.035, 0.035, fill=(255, 255, 255, 170))
        bx0, by0 = cx - 0.38, cy + (top - cy) * 0.7
        c.rect(bx0, by0, bx0 + 0.28, by0 + 0.3, fill=hexc("#dcdcdc"), outline=OUTLINE, width=0.02)
        for k, col in enumerate(("#57d98a", "#ffd27a")):
            c.ellipse(bx0 + 0.07 + k * 0.08, by0 + 0.22, 0.02, 0.02, fill=hexc(col))
        c.rect(bx0 + 0.04, by0 + 0.06, bx0 + 0.24, by0 + 0.15, fill=hexc("#3b4046"))
        c.rect(cx - 0.55, cy - 0.15, cx - 0.2, cy + 0.05, fill=hexc("#8c9296"), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.5, cy - 0.1, cx - 0.25, cy + 0.0, fill=hexc("#d4b13c"))
    elif kind == "tank":
        r = (x1 - x0) / 2
        for a in (200, 250, 290, 340):
            lx, ly = cx + r * 0.75 * math.cos(math.radians(a)), cy + r * 0.6 * math.sin(math.radians(a))
            c.rect(lx - 0.08, ly, lx + 0.08, ly + 1.6 * A.K, fill=wood_d, outline=OUTLINE, width=0.03)
            c.line([(lx - 0.05, ly + 0.05), (lx - 0.05, ly + 1.6 * A.K - 0.05)], fill=alpha(shade(wood_d, 1.3), 150), width=0.02)
        c.line([(cx - r * 0.5, cy + 0.5 * A.K), (cx + r * 0.55, cy + 0.9 * A.K)], fill=wood_d, width=0.05)
        c.line([(cx + r * 0.55, cy + 0.5 * A.K), (cx - r * 0.5, cy + 0.9 * A.K)], fill=wood_d, width=0.05)
        tankc = hexc("#5a7a90")
        p.cyl(cx, cy, r * 0.9, 1.6, 1.5, shade(hexc("#6a8aa0"), 1.15), tankc, ry=r * 0.8)
        # Rostlaeufer, Lichtkante links, Nietbaender, Leiter, Ablaufrohr, Dach mit Firstkante
        c.rect(cx - r * 0.9 + 0.08, cy + 1.65 * A.K, cx - r * 0.9 + 0.16, cy + 3.05 * A.K, fill=alpha(hexc("#8fb0c8"), 140))
        for k in range(3):
            yy = cy + (1.8 + k * 0.45) * A.K
            c.line([(cx - r * 0.9, yy), (cx + r * 0.9, yy)], fill=hexc("#3f5a6e"), width=0.04)
            xx = cx - r * 0.85
            while xx < cx + r * 0.85:
                c.ellipse(xx, yy, 0.018, 0.018, fill=hexc("#8fb0c8"))
                xx += 0.3
        for k, dx in enumerate((0.45, -0.25)):
            c.line([(cx + dx * r, cy + 1.62 * A.K), (cx + dx * r + 0.02, cy + 1.62 * A.K - 0.4 - k * 0.2)], fill=alpha(hexc("#7a5a3a"), 140), width=0.05)
        lx = cx + r * 0.62
        c.line([(lx - 0.09, cy + 1.62 * A.K - 0.1), (lx - 0.09, cy + 3.1 * A.K + 0.1)], fill=hexc("#8c9296"), width=0.035)
        c.line([(lx + 0.09, cy + 1.62 * A.K - 0.1), (lx + 0.09, cy + 3.1 * A.K + 0.1)], fill=hexc("#8c9296"), width=0.035)
        for k in range(7):
            yy = cy + 1.62 * A.K + k * (1.48 * A.K) / 6
            c.line([(lx - 0.09, yy), (lx + 0.09, yy)], fill=hexc("#8c9296"), width=0.03)
        c.line([(cx - r * 0.6, cy + 1.62 * A.K), (cx - r * 0.6, cy + 0.1)], fill=OUTLINE, width=0.09)
        c.line([(cx - r * 0.6, cy + 1.62 * A.K), (cx - r * 0.6, cy + 0.1)], fill=hexc("#6f7a82"), width=0.05)
        c.ellipse(cx - r * 0.6, cy + 0.9 * A.K, 0.07, 0.07, fill=hexc("#a8403a"), outline=OUTLINE, width=0.02)
        c.poly([(cx - r * 0.95, cy + 3.1 * A.K), (cx + r * 0.95, cy + 3.1 * A.K), (cx, cy + 3.1 * A.K + 1.0)], fill=hexc("#7a8c96"), outline=OUTLINE, width=0.05)
        c.poly([(cx - r * 0.95, cy + 3.1 * A.K), (cx, cy + 3.1 * A.K + 1.0), (cx, cy + 3.1 * A.K)], fill=alpha(hexc("#9aacb6"), 120))
        c.text(cx, cy + 2.3 * A.K, "H2O", 0.35, hexc("#e8eef2"))
    elif kind == "pumpenhaus":
        p.box(x0, y0, x1, y1, 0, h, shade(C["blech"], 1.2), C["blech"])
        zt = y0 + h * A.K
        # Blechfront mit Sicken, Rolltor, Warnschild, Rohr mit Ventilrad, Dachluefter und Manometer oben
        xx = x0 + 0.25
        while xx < x1 - 0.2:
            c.line([(xx, y0 + 0.08), (xx, y0 + h * A.K - 0.08)], fill=alpha(shade(C["blech"], 0.8), 200), width=0.02)
            xx += 0.35
        c.rect(cx - 0.4, y0 + 0.05, cx + 0.4, y0 + 1.3 * A.K, fill=hexc("#3b3f44"), outline=OUTLINE, width=0.03)
        for k in range(5):
            c.line([(cx - 0.36, y0 + 0.15 + k * 0.12), (cx + 0.36, y0 + 0.15 + k * 0.12)], fill=hexc("#5a6068"), width=0.02)
        c.rect(x1 - 0.7, y0 + 0.4, x1 - 0.3, y0 + 0.75, fill=hexc("#d4b13c"), outline=OUTLINE, width=0.02)
        c.poly([(x1 - 0.5, y0 + 0.7), (x1 - 0.62, y0 + 0.47), (x1 - 0.38, y0 + 0.47)], fill=hexc("#1e1e1e"))
        c.line([(x1, cy), (x1 + 0.5, cy)], fill=OUTLINE, width=0.16)
        c.line([(x1, cy), (x1 + 0.5, cy)], fill=hexc("#6f7a82"), width=0.1)
        c.ellipse(x1 + 0.28, cy + 0.15, 0.1, 0.1, fill=hexc("#a8403a"), outline=OUTLINE, width=0.025)
        c.line([(x1 + 0.28, cy + 0.05), (x1 + 0.28, cy + 0.15)], fill=hexc("#6f7a82"), width=0.03)
        c.ellipse(x0 + 0.5, zt + 0.6, 0.25, 0.25, fill=hexc("#e8e4da"), outline=OUTLINE, width=0.03)
        c.line([(x0 + 0.5, zt + 0.6), (x0 + 0.62, zt + 0.75)], fill=hexc("#a8403a"), width=0.025)
        c.ellipse(x0 + 0.5, zt + 0.6, 0.03, 0.03, fill=hexc("#3b4046"))
        p.cyl(x1 - 0.6, y1 - 0.5, 0.18, h, 0.35, hexc("#8c9296"), hexc("#6f7a82"), w=0.025, ry=0.12)
        c.ellipse(x1 - 0.6, y1 - 0.5 + (h + 0.35) * A.K, 0.1, 0.06, fill=hexc("#3b4046"))
    elif kind == "hochsitz":
        for lx in (x0 + 0.05, x1 - 0.25):
            c.rect(lx, y0, lx + 0.2, y0 + (h - 0.8) * A.K, fill=wood_d, outline=OUTLINE, width=0.03)
        for k in range(5):
            yy = y0 + 0.2 + k * 0.28
            c.line([(x0 + 0.25, yy), (x0 + 0.65, yy)], fill=wood, width=0.05)
        c.line([(x0 + 0.25, y0 + (h - 0.9) * A.K), (x1 - 0.25, y0 + 0.2)], fill=alpha(wood_d, 220), width=0.05)
        p.box(x0 - 0.2, y0, x1 + 0.2, y1, h - 0.8, 0.8, shade(wood, 1.15), wood)
        grain(x0 - 0.17, y0 + (h - 0.8) * A.K + 0.05, x1 + 0.17, y0 + h * A.K - 0.05, wood, 0.1)
        # grosses Fenster: wer oben steht, schaut mit dem Oberkoerper heraus (AtlasLookout); die Frontwand
        # darunter und der Rahmen kommen zusaetzlich als "hochsitz_front" VOR die Figur
        wy0, wy1 = y0 + (h - 0.62) * A.K, y0 + (h - 0.1) * A.K
        c.rect(x0 + 0.12, wy0, x1 - 0.12, wy1, fill=hexc("#1c1e20"))
        c.rect(x0 + 0.12, wy1 - 0.06, x1 - 0.12, wy1, fill=hexc("#2c2a26"))
        c.poly([(x0 - 0.35, y0 + h * A.K), (x1 + 0.35, y0 + h * A.K), (cx, y1 + (h + 0.6) * A.K)], fill=hexc("#5b3b22"), outline=OUTLINE, width=0.05)
        c.line([(x0 - 0.1, y0 + h * A.K + 0.15), (x1 + 0.1, y0 + h * A.K + 0.15)], fill=alpha(shade(hexc("#5b3b22"), 0.7), 220), width=0.03)
        lantern(x1 + 0.1, y0 + (h - 0.45) * A.K + 0.05)
    elif kind == "hochsitz_front":
        # nur die Teile der Kabinenfront um das Fenster: Bruestung, Pfosten, Sturz (gleiche Farben wie "hochsitz")
        yF, yT = y0 + (h - 0.8) * A.K, y0 + h * A.K
        wy0, wy1 = y0 + (h - 0.62) * A.K, y0 + (h - 0.1) * A.K
        xa, xb, xwa, xwb = x0 - 0.2, x1 + 0.2, x0 + 0.12, x1 - 0.12
        for r in ((xa, yF, xb, wy0), (xa, wy0, xwa, yT), (xwb, wy0, xb, yT), (xwa, wy1, xwb, yT)):
            c.rect(*r, fill=wood)
        grain(xa + 0.03, yF + 0.03, xb - 0.03, wy0 - 0.02, wood, 0.05)
        c.rect(xa, yF, xb, yT, outline=OUTLINE, width=0.03)
        c.rect(xwa, wy0, xwb, wy1, outline=OUTLINE, width=0.025)
        c.line([(xwa, wy0 + 0.012), (xwb, wy0 + 0.012)], fill=shade(wood, 1.25), width=0.02)
        lantern(x1 + 0.1, y0 + (h - 0.45) * A.K + 0.05, glow=False)
    elif kind == "baum":
        c.rect(cx - 0.18, cy, cx + 0.18, cy + 1.2 * A.K + 0.3, fill=C["stamm"], outline=OUTLINE, width=0.04)
        c.line([(cx + 0.06, cy + 0.1), (cx + 0.04, cy + 1.2 * A.K + 0.2)], fill=C["stamm_dunkel"], width=0.03)
        c.line([(cx - 0.11, cy + 0.1), (cx - 0.11, cy + 1.2 * A.K + 0.2)], fill=alpha(shade(C["stamm"], 1.3), 180), width=0.025)
        for k, sx in enumerate((-0.3, 0.32)):
            c.line([(cx + sx, cy - 0.02), (cx + sx * 0.5, cy + 0.18)], fill=C["wurzel"], width=0.07)
        for i, (dx, dz, r) in enumerate(((0, 2.3, 1.2), (-0.5, 1.8, 0.8), (0.55, 1.9, 0.8), (0, 3.0, 0.8))):
            col = C["krone"][i % len(C["krone"])]
            c.ellipse(cx + dx, cy + dz * A.K + 0.3, r, r * 0.85, fill=col, outline=OUTLINE, width=0.05)
            c.ellipse(cx + dx - r * 0.3, cy + dz * A.K + 0.3 + r * 0.25, r * 0.4, r * 0.3, fill=alpha(C["krone_licht"], 160))
            c.ellipse(cx + dx + r * 0.3, cy + dz * A.K + 0.3 - r * 0.3, r * 0.45, r * 0.3, fill=alpha(shade(col, 0.72), 120))
    elif kind == "lagerfeuer":
        r = (x1 - x0) / 2
        c.ellipse(cx, cy, r * 0.75, r * 0.6, fill=alpha(hexc("#2a2420"), 160))
        for i in range(10):
            a = i * math.tau / 10
            sx, sy = cx + r * 0.8 * math.cos(a), cy + r * 0.8 * math.sin(a)
            c.ellipse(sx, sy, 0.18, 0.14, fill=C["fels"], outline=OUTLINE, width=0.025)
            c.ellipse(sx - 0.05, sy + 0.04, 0.07, 0.04, fill=shade(C["fels"], 1.18))
        c.glow(cx, cy + 0.2, 2.5, hexc("#ffb347"), 0.45)
        for dx in (-0.2, 0, 0.2):
            c.line([(cx - 0.35, cy - 0.1 + dx), (cx + 0.35, cy + 0.1 + dx)], fill=wood_d, width=0.09)
        c.poly([(cx - 0.3, cy), (cx + 0.3, cy), (cx + 0.1, cy + 0.55), (cx, cy + 0.85), (cx - 0.12, cy + 0.5)], fill=hexc("#f08a2a"), outline=OUTLINE, width=0.03)
        c.poly([(cx - 0.14, cy + 0.05), (cx + 0.14, cy + 0.05), (cx, cy + 0.45)], fill=hexc("#ffd84a"))
        for k, (dx, dy) in enumerate(((0.25, 0.9), (-0.3, 0.8), (0.05, 1.15))):
            c.ellipse(cx + dx, cy + dy, 0.03, 0.03, fill=alpha(hexc("#ffd84a"), 200 - k * 40))
        # Dreibein mit Kessel ueber dem Feuer
        for sx in (-0.75, 0.75):
            c.line([(cx + sx, cy - 0.3), (cx, cy + 1.6)], fill=OUTLINE, width=0.05)
            c.line([(cx + sx, cy - 0.3), (cx, cy + 1.6)], fill=wood_d, width=0.03)
        c.line([(cx, cy + 1.6), (cx, cy + 1.3)], fill=hexc("#3b4046"), width=0.025)
        c.ellipse(cx, cy + 1.15, 0.2, 0.14, fill=hexc("#3b4046"), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.2, cy + 1.15, cx + 0.2, cy + 1.32, fill=hexc("#3b4046"))
        c.ellipse(cx, cy + 1.32, 0.2, 0.08, fill=hexc("#4f565c"), outline=OUTLINE, width=0.02)
    else:
        p.box(x0, y0, x1, y1, 0, h, (200, 0, 200, 255), (150, 0, 150, 255))
    return p.c.finish(), p.c.x0, p.c.y0, p.base_y


def render_props():
    # kind None = Sichtkern ohne eigenes Sprite (Baumstamm; die Krone kommt aus dem GLASS-Eintrag)
    items = [(s, k) for s, k in W.OPAQUE if k] + [(s, k) for s, k in W.GLASS if k]
    # Hochsitz-Front als eigenes, zugeschnittenes Sprite (vor der Figur, die oben im Fenster steht)
    items += [(s, "hochsitz_front") for s, k in W.OPAQUE + W.GLASS if k == "hochsitz"]
    images, meta = [], []
    for i, (s, kind) in enumerate(items):
        im, wx, wy, base = draw_prop(kind, s, i, PROP_PPM)
        im = im.filter(ImageFilter.GaussianBlur(0.45))
        if kind == "hochsitz_front":
            l_, t_, r_, b_ = im.getchannel("A").getbbox()
            l_, t_, r_, b_ = max(0, l_ - 2), max(0, t_ - 2), min(im.width, r_ + 2), min(im.height, b_ + 2)
            wx += l_ / PROP_PPM
            wy += (im.height - b_) / PROP_PPM
            im = im.crop((l_, t_, r_, b_))
        images.append((i, im))
        fx0, _, fx1, _ = bounds(s)
        meta.append((kind, wx, wy, base, fx0, fx1))
    atlases, placed = A.pack(images)
    for old in ASSETS.glob("wald_props_*.png"):
        old.unlink()
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"wald_props_{k}.png", optimize=True)
    out = []
    for i, (kind, wx, wy, base, fx0, fx1) in enumerate(meta):
        page, x, y, ww, hh = placed[i]
        out.append((kind, page, x, atlases[page].height - y - hh, ww, hh, wx, wy, base, fx0, fx1))
    print(f"props {len(out)} in {len(atlases)} atlas(es)")
    return out, images, meta


# ------------------------------------------------------------------ Konsolen

SKELD_CONSOLES = {
    "Cafeteria": ["Cafeteria/DataConsole/2", "Cafeteria/FixWiringConsole/4", "Cafeteria/GarbageConsole/2"],
    "Admin": ["Admin/SwipeCardConsole/0", "Admin/UploadDataConsole/0", "Admin/FixWiringConsole/2"],
    "Security": ["Security/DivertPowerConsole/1", "Security/FixWiringConsole/5"],
    "Electrical": ["Electrical/CalibrateConsole/0", "Electrical/DivertPowerConsole/0",
                   "Electrical/UploadDataConsole/0", "Electrical/FixWiringConsole/0"],
    "Reactor": ["Reactor/StartReactorConsole/2", "Reactor/UnlockManifoldsConsole/2"],
    "Weapons": ["Weapons/WeaponConsole/0", "Weapons/UploadDataConsole/1", "Weapons/DivertPowerConsole/1"],
    "Nav": ["Nav/ChartCourseConsole/0", "Nav/StabilizeSteeringConsole/0", "Nav/UploadDataConsole/0",
            "Nav/DivertPowerConsole/1", "Nav/FixWiringConsole/3"],
    "Shields": ["Shields/ShieldConsole/0", "Shields/DivertPowerConsole/1"],
    "Comms": ["Comms/UploadDataConsole/1", "Comms/DivertPowerConsole/1"],
    "UpperEngine": ["UpperEngine/AlignEngineConsole/0", "UpperEngine/FuelEngineConsole/0",
                    "UpperEngine/DivertPowerConsole/1"],
    "LowerEngine": ["LowerEngine/AlignEngineConsole/1", "LowerEngine/FuelEngineConsole/0",
                    "LowerEngine/DivertPowerConsole/1"],
    "MedBay": ["MedBay/MedBayConsole/0"],
    "Storage": ["Storage/gasCanConsole/0", "Storage/FixWiringConsole/1", "Storage/AirlockConsole/0"],
    "LifeSupp": ["LifeSupp/CleanFilterConsole/0", "LifeSupp/GarbageConsole/0", "LifeSupp/DivertPowerConsole/1"],
}


def place_consoles(walk, rooms, doors, obstacles):
    placed = {}
    free = walk.difference(unary_union(obstacles).buffer(0.5)).buffer(0)
    edge = walk.boundary
    taken = [Point(p) for p in list(W.FIXED.values()) + [W.EMERGENCY, W.SURVEILLANCE, W.ADMIN_TABLE, W.FREEPLAY, W.SPAWN]]
    taken += [Point(p) for p in W.VENTS.values()] + [Point(p) for p in W.CAMERAS]
    door_pts = [o.centroid for *_r, o in doors]
    # Stellen, an denen ein Weg in einen Raum muendet: Wegmittellinie x Raumrand
    ends = []
    for pts in W.PATHS:
        ls = LineString(pts)
        for rk, (_n, _s, g) in rooms.items():
            if rk not in [c[0] for c in W.CLEARINGS]:
                continue   # Gebaeude haben Tueren, dort gilt der Tuerabstand
            ix = ls.intersection(g.exterior)
            ends.extend([ix] if ix.geom_type == "Point" else list(getattr(ix, "geoms", [])))
    path_ends = unary_union(ends) if ends else Point(1e6, 1e6)
    for key, (name, sysname, g) in rooms.items():
        keys = [k for k in SKELD_CONSOLES.get(sysname, []) if k not in W.FIXED]
        ring = g.buffer(-0.55)
        cands = []
        for part in geom_parts(ring):
            line = part.exterior
            n = max(16, int(line.length / 0.3))
            for i in range(n):
                p = line.interpolate(i / n, normalized=True)
                if edge.distance(p) > 0.75 or not free.contains(p):
                    continue
                if min([p.distance(d) for d in door_pts] + [99]) < 1.6:
                    continue
                # nicht in Wegeinmuendungen (Durchreview 23.09.: Hochsitz, Pumpe)
                if path_ends.distance(p) < 2.0:
                    continue
                cands.append(p)
        chosen = []
        for k in keys:
            best, score = None, -1e9
            for p in cands:
                d = min([p.distance(q) for q in chosen + taken] + [99])
                if d < 1.3:
                    continue
                sc = min(d, 4.0) + 0.15 * (p.y - g.centroid.y)   # Nordwand bevorzugt (sichtbar)
                if sc > score:
                    best, score = p, sc
            if best is None:
                best = g.representative_point()
                print(f"WARN no spot for {k} in {name}")
            chosen.append(best)
            placed[k] = (round(best.x, 2), round(best.y, 2))
        taken.extend(chosen)
    for k, p in W.FIXED.items():
        placed[k] = p
    return placed


def update_brief(consoles, rooms):
    """wald_console_brief.json an die platzierten Konsolen anpassen (Kartenverkleinerung 24.09.):
    Position, Raum, Gebaeude/Lichtung und die Wandseite, an der der Block steht. Die Wandseite folgt
    der naechsten Raumkante (unter 0,9 m), sonst "-". Freistehende Bloecke ("-") bleiben freistehend."""
    import json
    path = HERE / "wald_console_brief.json"
    brief = json.loads(path.read_text(encoding="utf-8"))
    special = {"EmergencyButton": W.EMERGENCY, "SurveillanceConsole": W.SURVEILLANCE,
               "AdminTable": W.ADMIN_TABLE, "FreeplayLaptop": W.FREEPLAY}
    buildings = {b[0] for b in W.BUILDINGS}
    for row in brief:
        key = row[0]
        p = consoles.get(key) or special.get(key)
        if p is None:
            continue
        row[1], row[2] = round(p[0], 2), round(p[1], 2)
        pt = Point(p)
        owner = min(rooms, key=lambda k: rooms[k][2].distance(pt))
        row[3] = owner
        row[4] = "building" if owner in buildings else "clearing"
        if row[5] == "-" or key in special:
            continue
        g = rooms[owner][2]
        q = g.exterior.interpolate(g.exterior.project(pt))
        dx, dy = q.x - pt.x, q.y - pt.y
        if math.hypot(dx, dy) > 0.9:
            row[5] = "-"
        elif abs(dx) > abs(dy):
            row[5] = "E" if dx > 0 else "W"
        else:
            row[5] = "N" if dy > 0 else "S"
    path.write_text(json.dumps(brief, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ Task-Bloecke

def render_consoles():
    """Eigene Task-Bloecke (tools/wald_consoles.py, Fable) in Atlanten packen."""
    try:
        import wald_consoles as WC
    except ImportError:
        print("consoles: wald_consoles.py fehlt (Skeld-Bilder bleiben)")
        return []
    sprites = WC.render_all(PROP_PPM)
    try:
        import wald_vents as WV   # Fable: Baumstuempfe / Bodenluken, Keys "Vent/<id>"
        sprites.update(WV.render_all(PROP_PPM))
    except ImportError:
        pass
    for old in ASSETS.glob("wald_consoles_*.png"):
        old.unlink()
    if not sprites:
        return []
    keys = sorted(sprites)
    images = [(i, sprites[k][0].filter(ImageFilter.GaussianBlur(0.45))) for i, k in enumerate(keys)]
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"wald_consoles_{k}.png", optimize=True)
    out = []
    for i, key in enumerate(keys):
        page, x, y, w, h = placed[i]
        _im, ax, ay = sprites[key]
        out.append((key, page, x, atlases[page].height - y - h, w, h, ax / w, ay / h))
    print(f"consoles {len(out)} sprites in {len(atlases)} atlas(es)")
    return out


# ------------------------------------------------------------------ Minimap

MAP_LABELS = []   # (x, y, halbe Breite, halbe Hoehe) in Weltmetern, fuer AvoidLabels im Builder


def minimap(walk, rooms):
    s = 24
    ww, hh = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - BX0) * s, (BY1 - y) * s)
    for p in geom_parts(walk):
        d.polygon([P(*q) for q in p.exterior.coords], fill=(214, 232, 216, 235))
        for h in p.interiors:
            d.polygon([P(*q) for q in h.coords], fill=(0, 0, 0, 0))
    for p in geom_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            pts = [P(*q) for q in ring.coords]
            d.line(pts, fill=(18, 36, 28, 255), width=4, joint="curve")
    try:
        font = ImageFont.truetype("arialbd.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    # Teilflaechen eines Raums (gleicher Name) nur einmal beschriften
    by_name = {}
    for key, (name, _s, g) in rooms.items():
        by_name.setdefault(name, []).append(g)
    MAP_LABELS.clear()
    area = walk.buffer(0.15)
    for name, gs in by_name.items():
        c = unary_union(gs).representative_point()
        map_labels.place(d, font, name, c.x, c.y, area, s, P, (18, 36, 28, 255), MAP_LABELS)
    img.save(ASSETS / "wald_minimap.png", optimize=True)


# ------------------------------------------------------------------ C#

def v2(p):
    return f"new({p[0]:.3f}f, {p[1]:.3f}f)"


def chain(points):
    return "new Vector2[] { " + ", ".join(v2(p) for p in points) + " }"


def rings_of(g):
    out = []
    for p in geom_parts(g):
        out.append(list(p.exterior.coords)[:-1])
        for h in p.interiors:
            out.append(list(h.coords)[:-1])
    return out


def header(a, what):
    a("// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0")
    a("// Licensed under GPL-3.0-or-later. See LICENSE for details.")
    a("//")
    a("// AUTOMATISCH ERZEUGT von tools/gen_wald.py aus tools/wald_layout.py - NICHT VON HAND AENDERN.")
    a(f"// {what}")
    a("")
    a("using System.Collections.Generic;")
    a("using UnityEngine;")
    a("")
    a("namespace UnknownsAtlas;")
    a("")


def emit(walk, water, rooms, doors, tiles, props, consoles, blocks=()):
    full = box(BX0 - 5, BY0 - 5, BX1 + 5, BY1 + 5)
    solid = full.difference(walk)
    move = walk.difference(translate(solid, 0, -0.3)).buffer(0)
    shadow = unary_union([walk, translate(walk, 0, 0.45), water]).buffer(0)
    opaque = [G.shape(s) for s, _k in W.OPAQUE]
    glass = [G.shape(s) for s, _k in W.GLASS]
    edges = unary_union([LineString(r + [r[0]]) for r in rings_of(walk)])
    casts = [p.distance(edges) > 0.08 for p in opaque]
    room_u = unary_union([g for _n, _s, g in rooms.values()])
    rest = walk.difference(room_u).buffer(0)
    halls = [g for g in geom_parts(rest) if g.area > 1.0]
    # Sturmholz-Stellen quer ueber jeden Weg. Frueher leitete AtlasWorld sie aus schmalen Flur-
    # flaechen ab; seit den 1-m-Hoefen der Verkleinerung verschmelzen Wege und Hoefe zu wenigen
    # grossen Flaechen (Autotest 24.09.: 0 statt 5 Stellen). Deshalb stehen sie jetzt als Daten hier.
    trees = []
    for pts in W.PATHS:
        ls = LineString(pts)
        c = ls.interpolate(0.5, normalized=True)
        (ax, ay), (bx, by) = pts[0], pts[-1]
        trees.append((c.x, c.y, abs(bx - ax) > abs(by - ay), W.PATH_W + 0.8))

    L = []
    a = L.append
    header(a, "Forststation Nadelkamm: Geometrie, Raeume, Bodenkacheln, Objekte (Weltmeter).")
    a("public static class AtlasWaldData")
    a("{")
    a(f"    public const float MinX = {BX0:.2f}f, MinY = {BY0:.2f}f, MaxX = {BX1:.2f}f, MaxY = {BY1:.2f}f;")
    for name, g in (("Walls", move), ("ShadowWalls", shadow)):
        a(f"    public static readonly Vector2[][] {name} =\n    {{")
        for r in rings_of(g):
            a(f"        {chain(r)},")
        a("    };")
    a("    public static readonly Vector2[][] Opaque =\n    {")
    for p in opaque:
        a(f"        {chain(list(p.exterior.coords)[:-1])},")
    a("    };")
    a("    public static readonly bool[] OpaqueCastsShadow = { " + ", ".join("true" if c else "false" for c in casts) + " };")
    a("    public static readonly Vector2[][] Glass =\n    {")
    for p in glass:
        a(f"        {chain(list(p.exterior.coords)[:-1])},")
    a("    };")
    a("    public static readonly (string Key, string Name, SystemTypes Room, Vector2[] Area)[] Rooms =\n    {")
    for key, (name, sysname, g) in rooms.items():
        a(f"        (\"{key}\", \"{name}\", SystemTypes.{sysname}, {chain(list(g.exterior.coords)[:-1])}),")
    a("    };")
    a("    public static readonly Vector2[][] Hallways =\n    {")
    for h in halls:
        a(f"        {chain(list(h.exterior.coords)[:-1])},")
    a("    };")
    a("    /// <summary>Sturmholz-Stellen: Wegmitte, Weg laeuft waagerecht?, Stammlaenge (quer zum Weg).</summary>")
    a("    public static readonly (float X, float Y, bool Horizontal, float Len)[] TreeSpots =\n    {")
    for x, y, hor, ln in trees:
        a(f"        ({x:.3f}f, {y:.3f}f, {'true' if hor else 'false'}, {ln:.2f}f),")
    a("    };")
    a("    /// <summary>Beschriftungen der Minimap (Weltmeter): Mitte, halbe Breite/Hoehe. Die Sabotage- und")
    a("    /// Tuerknoepfe weichen ihnen aus (AtlasMuseumBuilder.AvoidLabels).</summary>")
    a("    public static readonly (float X, float Y, float HalfW, float HalfH)[] MapLabels =\n    {")
    for lx, ly, hw, hh in MAP_LABELS:
        a(f"        ({lx:.3f}f, {ly:.3f}f, {hw:.3f}f, {hh:.3f}f),")
    a("    };")
    a(f"    public const float FloorPixelsPerMeter = {FLOOR_PPM}f;")
    a("    public static readonly (int Index, float WorldX, float WorldY, int W, int H)[] FloorTiles =\n    {")
    for i, wx, wy, ww, hh in tiles:
        a(f"        ({i}, {wx:.4f}f, {wy:.4f}f, {ww}, {hh}),")
    a("    };")
    a(f"    public const float PropPixelsPerMeter = {PROP_PPM}f;")
    a("    public static readonly (string Kind, int Atlas, int X, int Y, int W, int H, float WorldX, float WorldY, float BaseY, float FootX0, float FootX1)[] Props =\n    {")
    for kind, page, x, y, ww, hh, wx, wy, base, fx0, fx1 in props:
        a(f"        (\"{kind}\", {page}, {x}, {y}, {ww}, {hh}, {wx:.3f}f, {wy:.3f}f, {base:.3f}f, {fx0:.3f}f, {fx1:.3f}f),")
    a("    };")
    a("    public static readonly (string Key, int Atlas, int X, int Y, int W, int H, float PivotX, float PivotY)[] ConsoleSprites =")
    a("    {")
    for key, page, x, y, w, h, px_, py_ in blocks:
        a(f"        (\"{key}\", {page}, {x}, {y}, {w}, {h}, {px_:.4f}f, {py_:.4f}f),")
    a("    };")
    a("}")
    OUT_DATA.write_text("\n".join(L) + "\n", encoding="utf-8")

    # Tuer-Slots aus den "door"-Oeffnungen
    group = {b[0]: b[2] for b in W.BUILDINGS}
    vert, hori = [], []
    for key, side, a0, b0, kind, o in doors:
        if kind != "door":
            continue
        c = o.centroid
        slot = (f"{key}-{side}", c.x, c.y, b0 - a0, group[key])
        (vert if side in "EW" else hori).append(slot)

    L = []
    a = L.append
    header(a, "Forststation Nadelkamm: Plaetze der Skeld-Mechanik (Weltmeter).")
    a("internal static class AtlasWaldLayout")
    a("{")
    a("    public static readonly Dictionary<string, Vector2> Consoles = new()\n    {")
    for k, p in sorted(consoles.items()):
        a(f"        [\"{k}\"] = {v2(p)},")
    a("    };")
    for name, p in (("EmergencyButton", W.EMERGENCY), ("SurveillanceConsole", W.SURVEILLANCE),
                    ("AdminTable", W.ADMIN_TABLE), ("FreeplayLaptop", W.FREEPLAY), ("Spawn", W.SPAWN)):
        a(f"    public static readonly Vector2 {name} = {v2(p)};")
    a(f"    public const float SpawnRadius = {W.SPAWN_RADIUS}f;")
    a("    public static readonly Dictionary<int, Vector2> Vents = new()\n    {")
    for vid, p in W.VENTS.items():
        a(f"        [{vid}] = {v2(p)},")
    a("    };")
    a("    public static readonly int[][] VentNetworks =\n    {")
    for net in W.VENT_NETS:
        a("        new[] { " + ", ".join(map(str, net)) + " },")
    a("    };")
    for nm, lst in (("VerticalDoors", vert), ("HorizontalDoors", hori)):
        a(f"    public static readonly AtlasMuseumLayout.DoorSlot[] {nm} =\n    {{")
        for label, cx, cy, length, grp in lst:
            a(f"        new(\"{label}\", {cx:.3f}f, {cy:.3f}f, {length:.2f}f, SystemTypes.{grp}, seeThrough: false),")
        a("    };")
    a("    public static readonly Vector2[] Cameras =\n    {")
    for p in W.CAMERAS:
        a(f"        {v2(p)},")
    a("    };")
    a("    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()\n    {")
    done = set()
    for key, (name, sysname, g) in rooms.items():
        if sysname in ("Cafeteria", "Storage", "UpperEngine", "LowerEngine", "Security", "MedBay",
                       "Electrical", "Reactor", "LifeSupp", "Comms") and sysname not in done:
            c = g.representative_point()
            a(f"        [SystemTypes.{sysname}] = {v2((c.x, c.y + 0.8))},")
            done.add(sysname)
    a("    };")
    a("}")
    OUT_LAYOUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"doors {len(vert)}V/{len(hori)}H, consoles {len(consoles)}, hallways {len(halls)}")


def main():
    walk, water, shells, doors = G.build()
    rooms = G.rooms(walk)
    obstacles = [G.shape(s) for s, _k in W.OPAQUE] + [G.shape(s) for s, _k in W.GLASS]
    consoles = place_consoles(walk, rooms, doors, obstacles)
    update_brief(consoles, rooms)
    free = walk.difference(unary_union(obstacles).buffer(0.25))
    for k, p in list(consoles.items()) + [("Emergency", W.EMERGENCY), ("Surveillance", W.SURVEILLANCE),
                                          ("Admin", W.ADMIN_TABLE), ("Freeplay", W.FREEPLAY)] + \
                                         [(f"Vent{v}", p) for v, p in W.VENTS.items()] + [(f"Cam{i}", p) for i, p in enumerate(W.CAMERAS)]:
        dd = free.distance(Point(p))
        if dd > 0.6:
            print(f"WARN {k} at {p} not reachable ({dd:.2f} m)")
    tiles = render_floor(walk, water, shells, doors, rooms)
    props, images, meta = render_props()
    minimap(walk, rooms)
    blocks = render_consoles()
    emit(walk, water, rooms, doors, tiles, props, consoles, blocks)

    # Vorschau: Boden (1/4) + Objekte + Konsolenpunkte
    fl = Image.open(PREVIEW / "floor_preview.jpg").convert("RGBA")
    ppm = fl.width / (BX1 - BX0)
    order = sorted(range(len(images)), key=lambda i: -meta[i][3])
    for i in order:
        im = images[i][1]
        im = im.resize((max(1, int(im.width * ppm / PROP_PPM)), max(1, int(im.height * ppm / PROP_PPM))), Image.LANCZOS)
        kind, wx, wy, base, _a, _b = meta[i]
        fl.alpha_composite(im, (int((wx - BX0) * ppm), int((BY1 - wy) * ppm) - im.height))
    d = ImageDraw.Draw(fl)
    for k, p in consoles.items():
        x, y = (p[0] - BX0) * ppm, (BY1 - p[1]) * ppm
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 230, 0), outline=(0, 0, 0))
    fl.save(PREVIEW / "preview.png")
    print(PREVIEW / "preview.png", fl.size)


if __name__ == "__main__":
    main()
