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

import handdraw as HD
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
    # Voller Pass 01.10.: Wege dunkler und roetlicher, Kies heller und grauer (im Stilblatt waren beide kaum
    # zu unterscheiden)
    "erde": hexc("#7a5433"),
    "erde2": hexc("#684628"),
    "erde_rand": hexc("#52361d"),
    "kiesel": hexc("#b6a688"),
    "kies": hexc("#8c846c"),
    "kies2": hexc("#776e56"),
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
    for ci, (cx, cy, r) in enumerate(crowns):   # Norden zuerst, suedliche Kronen liegen vorne
        # Stilblatt: Kronenumriss mit leichtem Zittern statt sauberem Kreis
        disk = Polygon(HD.wobble_ellipse(cx, cy, r, r, amp=r * 0.035, seed=1000 + ci)).buffer(0)
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

    # 2. Wasser (Stilblatt: Seeufer): Tiefenstufen, Wellenstruktur, Mondbahn, Seerosen; das Ufer selbst
    # (Uferband, Steine, Schilf) kommt in draw_shore NACH Gras und Kies, der Steg in draw_dock
    wx0, wy0, wx1, wy1 = water.bounds
    draw_water(ops, water, rnd)

    # 3. Aussenflaechen: Gras (Lichtungen), Kies (Hoefe), Erde (Wege). Stilblatt: Kiesrand, Lichtungsraender
    # und der Umriss am Ende laufen auf derselben leicht zittrigen Kante (walk_w); die Kollider bleiben gerade.
    walk_w = wobble_geom(walk, amp=0.03, seed=600, step=0.22)
    outdoor = walk_w.difference(unary_union([box(*b[3]) for b in W.BUILDINGS]).buffer(W.WALL + 0.02))
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
    clearing_polys = [wobble_geom(rooms[k][2], amp=0.04, seed=620 + i, step=0.25).intersection(walk_w) for i, (k, *_r) in enumerate(W.CLEARINGS)]
    grass = unary_union(clearing_polys)
    fill(ops, grass, C["gras"])
    # Grasrand: feine Halmsaeume entlang der zittrigen Kante (Lichtung geht in Kies ueber)
    for i, part in enumerate(geom_parts(grass)):
        ring = part.exterior
        s = 0.2
        while s < ring.length:
            p = ring.interpolate(s)
            if outdoor.buffer(-0.15).contains(p) and rnd.random() < 0.55:
                for k in range(3):
                    ops.line([(p.x + (k - 1) * 0.04, p.y), (p.x + (k - 1) * 0.08, p.y + 0.13)], fill=rnd.choice([C["halm"], C["gras3"]]), width=0.022)
            s += rnd.uniform(0.25, 0.6)
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
    paths = draw_paths(ops, paths, outdoor, grass, rnd)
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
    # Ufer (Stilblatt): Uferband mit welliger Wasserkante, Steine halb im Wasser, Schilfgruppen, Wurzeln
    # am Waldufer; danach der Steg mit Pfaehlen, Spiegelung und vertaeutem Ruderboot
    draw_shore(ops, water, walk, forest, rnd)
    draw_far_shore(ops, water, rnd)
    for dock in W.DOCKS:
        draw_dock(ops, water, rnd, dock)

    # 4. Gebaeude: Wandkrone (Blockbohlen) + Boden je Haus (hut_floor)
    for bi, (key, _n, _s, inner, _d) in enumerate(W.BUILDINGS):
        x0, y0, x1, y1 = inner
        shell = box(x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL)
        ops.poly(HD.wobble_rect(x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL, amp=0.008, seed=640 + bi, step=0.12),
                 fill=C["wand_krone"], outline=OUTLINE, width=0.07)
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
        hut_floor(ops, key, inner, rnd)
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
                    for hi in range(int((b - a) * 1.4)):
                        bx = rnd.uniform(a, b)
                        # Hecken/Buesche am Fuss der Waldfront: zittriger Umriss (Stilblatt)
                        ops.poly(HD.wobble_ellipse(bx, my + 0.12, rnd.uniform(0.2, 0.35), 0.18, amp=0.012, seed=int(bx * 10) + hi),
                                 fill=rnd.choice(C["krone"]), outline=OUTLINE, width=0.03)
                sh = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.3), (x0, y0 - 0.3)]).intersection(walk)
                fill(ops, sh, (0, 0, 0, 55))
    # Umriss der begehbaren Flaeche: dieselbe zittrige Kante wie Kies und Gras (walk_w)
    for p in geom_parts(walk_w):
        for ring in [p.exterior] + list(p.interiors):
            ops.line(list(ring.coords), fill=OUTLINE, width=0.08)
    return ops


def wobble_geom(g, amp, seed, step):
    """Alle Ringe einer Flaeche mit handdraw.wobble leicht zittern lassen (Stilblatt), Loecher bleiben Loecher."""
    parts = []
    for i, p in enumerate(geom_parts(g)):
        ext = HD.wobble(list(p.exterior.coords)[:-1], amp=amp, seed=seed + i * 7, step=step, closed=True)
        holes = [HD.wobble(list(h.coords)[:-1], amp=amp, seed=seed + i * 7 + 3 + j, step=step, closed=True) for j, h in enumerate(p.interiors)]
        q = Polygon(ext, holes).buffer(0)
        if not q.is_empty:
            parts.append(q)
    return unary_union(parts)


def hut_floor(ops, key, inner, rnd):
    """Boden je Huette (voller Pass 01.10.): Messe Dielen + Herdplatte, Feldstation Dielen + Flechtteppich
    + Papiere, Labor Linoleum-Schachbrett + Abfluss + Reinzone, Saegewerk breite Dielen quer + Saegemehl,
    Lager Estrich + Stellplatzmarkierung + Palette, Bootshaus Dielen mit breiten Fugen + Naesse + Tau +
    Rettungsring, Wachstube dunkle Dielen + Fussmatte + Kabel, Generator Estrich + Oel + Warnstreifen + Kanal.
    Alle Raster mit Hand-Unruhe (museum_art.wobbly_tiles)."""
    x0, y0, x1, y1 = inner
    region = box(*inner)
    t = PLANK_TINT.get(key, 1.0)
    cols = [shade(c, t) for c in C["diele"]]
    fuge = shade(C["diele_fuge"], t)
    seed = sum(ord(ch) for ch in key)

    def planks(pw=0.28, plen=1.6, vertical=False, fuge_w=0.025, tint=1.0):
        A.wobbly_tiles(ops, region, x0, y0, x1, y1, plen, pw, [shade(c, tint) for c in cols], shade(fuge, tint), seed=seed,
                       bond="random", fuge_w=fuge_w, jitter=0.02, tone=0.05, chips=0.0, cracks=0.0, amp=0.003,
                       vertical=vertical, knots=0.18, grain=0.35)

    def concrete(base, dark):
        ops.rect(x0, y0, x1, y1, fill=base)
        A.speckle(ops, region, int((x1 - x0) * (y1 - y0) * 28), [dark, shade(base, 1.08)], 0.01, 0.03, seed=seed)
        for k in range(3):
            ax, ay = rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 0.5, y1 - 0.5)
            pts = [(ax, ay), (ax + rnd.uniform(-0.5, 0.5), ay + rnd.uniform(-0.4, 0.4)), (ax + rnd.uniform(-0.9, 0.9), ay + rnd.uniform(-0.6, 0.6))]
            A.crack_line(ops, pts, alpha(shade(base, 0.6), 220), seed=seed + k)

    if key == "messe":
        planks()
        # Herdplatte: graue Steinplatten unter und vor dem Herd (Herd bei -4,4..-2,6 / -1,4..-0,3)
        slab = box(x0 + 0.25, y0 + 0.25, x0 + 2.9, y0 + 2.25)
        A.wobbly_tiles(ops, slab, x0 + 0.25, y0 + 0.25, x0 + 2.9, y0 + 2.25, 0.5, 0.4, [C["fels"], shade(C["fels"], 0.92), shade(C["fels"], 1.08)],
                       C["fels_dunkel"], seed=seed + 5, bond=0.5, fuge_w=0.03, jitter=0.04, tone=0.05, chips=0.1, cracks=0.08, amp=0.004)
        ops.rect(x0 + 0.25, y0 + 0.25, x0 + 2.9, y0 + 2.25, outline=OUTLINE, width=0.035)
        # Holzscheite neben dem Herd und Asche davor
        for k in range(4):
            lx, ly = x0 + 0.4 + (k % 2) * 0.3, y0 + 1.7 + (k // 2) * 0.22
            ops.line([(lx, ly), (lx + 0.45, ly + 0.03)], fill=OUTLINE, width=0.1)
            ops.line([(lx, ly), (lx + 0.45, ly + 0.03)], fill=C["stamm"], width=0.07)
            ops.ellipse(lx, ly, 0.035, 0.05, fill=C["stirnholz"], outline=OUTLINE, width=0.012)
        ops.poly(HD.wobble_ellipse(x0 + 1.4, y0 + 0.5, 0.35, 0.18, amp=0.03, seed=seed + 9), fill=alpha((40, 36, 34, 255), 90))
    elif key == "feldstation":
        planks()
        # Flechtteppich (oval, konzentrische Ringe) unter dem Kartentisch, Papiere am Boden
        rcx, rcy = (x0 + x1) / 2, y0 + 4.7
        for k, (rx, col) in enumerate(((2.35, "#8a6a4a"), (2.1, "#c9b27a"), (1.85, "#6b8c45"), (1.6, "#c9b27a"), (1.35, "#8a6a4a"), (1.1, "#c9b27a"), (0.85, "#a8403a"), (0.6, "#c9b27a"))):
            ops.poly(HD.wobble_ellipse(rcx, rcy, rx, rx * 0.62, amp=0.01, seed=seed + k), fill=alpha(hexc(col), 225))
        ops.poly(HD.wobble_ellipse(rcx, rcy, 2.35, 2.35 * 0.62, amp=0.01, seed=seed), outline=alpha(hexc("#5a3a22"), 200), width=0.03)
        for k, (px_, py_, ang) in enumerate(((x1 - 1.3, y0 + 0.9, 0.2), (x0 + 1.2, y0 + 0.5, -0.3), (x1 - 2.2, y0 + 1.3, 0.1))):
            ca, sa = math.cos(ang), math.sin(ang)
            w, h = 0.21, 0.3
            pts = [(px_ + dx * ca - dy * sa, py_ + dx * sa + dy * ca) for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
            ops.poly(pts, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.015)
            for j in range(4):
                a_ = (px_ + (-w + 0.04) * ca - (-h + 0.07 + j * 0.06) * sa, py_ + (-w + 0.04) * sa + (-h + 0.07 + j * 0.06) * ca)
                b_ = (px_ + (w - 0.04 - (j % 2) * 0.05) * ca - (-h + 0.07 + j * 0.06) * sa, py_ + (w - 0.04 - (j % 2) * 0.05) * sa + (-h + 0.07 + j * 0.06) * ca)
                ops.line([a_, b_], fill=alpha(hexc("#3b3630"), 150), width=0.01)
    elif key == "labor":
        # Linoleum-Schachbrett (Stilblatt-Raster), Abfluss, Reinzone um den Scanner, Gummimatte vor der Bank
        lino = (hexc("#d8dcd0"), hexc("#b4c6b2"))
        A.wobbly_tiles(ops, region, x0, y0, x1, y1, 0.5, 0.5, list(lino), hexc("#8a9488"), seed=seed, checker=lino,
                       fuge_w=0.015, jitter=0.015, tone=0.03, chips=0.04, cracks=0.03, amp=0.003)
        gx, gy = x1 - 1.5, y0 + 0.9
        ops.ellipse(gx, gy, 0.2, 0.2, fill=hexc("#7b8288"), outline=OUTLINE, width=0.03)
        for k in range(3):
            ops.line([(gx - 0.13, gy - 0.08 + k * 0.08), (gx + 0.13, gy - 0.08 + k * 0.08)], fill=hexc("#2e3338"), width=0.02)
        A.dashed(ops, [(x0 + 3.0, y0 + 0.4), (x0 + 3.0, y0 + 3.0), (x0 + 5.2, y0 + 3.0), (x0 + 5.2, y0 + 0.4), (x0 + 3.0, y0 + 0.4)],
                 alpha(hexc("#3f9e9e"), 200), width=0.05, dash=0.3, gap=0.15)
        mat = HD.wobble_rect(x0 + 0.5, y1 - 2.1, x0 + 2.3, y1 - 1.35, amp=0.005, seed=seed + 3, step=0.1)
        ops.poly(mat, fill=hexc("#3b4046"), outline=OUTLINE, width=0.025)
        for k in range(7):
            ops.line([(x0 + 0.6 + k * 0.25, y1 - 2.0), (x0 + 0.6 + k * 0.25, y1 - 1.45)], fill=alpha((255, 255, 255, 255), 40), width=0.02)
        ops.ellipse(x0 + 6.6, y0 + 2.4, 0.09, 0.09, fill=hexc("#d84a4a"), outline=OUTLINE, width=0.015)   # Warnmarke am Boden
        ops.ellipse(x0 + 6.6, y0 + 2.4, 0.04, 0.04, fill=hexc("#f0f0ea"))
    elif key == "saegewerk":
        planks(pw=0.34, plen=2.2, vertical=True, fuge_w=0.03, tint=0.95)
        # Saegemehl: weiche helle Haufen suedlich des Saegetischs, Spaene verstreut, Kreidelinie
        # Haufen dicht am Saegeblatt (Tischmitte), nach aussen kleiner und loser
        bx_ = x0 + 6.0
        for k in range(9):
            sx = bx_ + rnd.gauss(0, 1.4)
            sy = y0 + 2.45 + rnd.uniform(-0.15, 0.35) - abs(sx - bx_) * 0.08
            scale = max(0.35, 1.0 - abs(sx - bx_) * 0.22)
            ops.poly(HD.wobble_ellipse(sx, sy, rnd.uniform(0.25, 0.5) * scale, rnd.uniform(0.14, 0.26) * scale, amp=0.03, seed=seed + k), fill=alpha(hexc("#d8c08a"), 150))
            if k % 2 == 0:
                ops.poly(HD.wobble_ellipse(sx - 0.05, sy + 0.04, rnd.uniform(0.12, 0.25) * scale, rnd.uniform(0.07, 0.12) * scale, amp=0.02, seed=seed + 20 + k), fill=alpha(hexc("#e8d4a0"), 150))
        for _ in range(45):
            px_, py_ = rnd.uniform(x0 + 0.4, x1 - 0.4), rnd.uniform(y0 + 0.3, y0 + 3.5)
            ops.ellipse(px_, py_, rnd.uniform(0.02, 0.045), rnd.uniform(0.012, 0.025), fill=alpha(hexc("#d8b07a"), 200))
        ops.line(HD.wobble([(x0 + 0.5, y0 + 1.0), (x1 - 0.5, y0 + 1.05)], amp=0.01, seed=seed + 40, step=0.2), fill=alpha(hexc("#f0f0ea"), 150), width=0.02)
        A.oil_stain(ops, x1 - 1.4, y0 + 1.6, 0.3, 0.18, seed=seed + 41, a=90)
    elif key == "lager":
        concrete(hexc("#8c8880"), hexc("#6e6a62"))
        mark = alpha(hexc("#d4b13c"), 200)
        # Stellplatzmarkierungen um die Kistenstapel, Gassenlinie, Palette, Strichliste an der Wand
        for bx0, by0, bx1, by1 in ((x0 + 0.2, y0 + 0.4, x0 + 3.8, y0 + 2.0), (x1 - 3.8, y0 + 0.4, x1 - 0.2, y0 + 2.0), (x0 + 3.6, y0 + 2.6, x1 - 3.6, y0 + 4.4)):
            A.dashed(ops, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1), (bx0, by0)], mark, width=0.05, dash=0.35, gap=0.18)
        ops.line(HD.wobble([(x0 + 0.3, y1 - 1.4), (x1 - 0.3, y1 - 1.4)], amp=0.006, seed=seed + 2, step=0.3), fill=mark, width=0.06)
        px0, py0 = x1 - 3.2, y1 - 1.2
        ops.rect(px0, py0, px0 + 1.2, py0 + 0.8, fill=hexc("#9a7a52"), outline=OUTLINE, width=0.03)
        for k in range(5):
            ops.line([(px0 + 0.1 + k * 0.25, py0 + 0.05), (px0 + 0.1 + k * 0.25, py0 + 0.75)], fill=hexc("#6e5234"), width=0.03)
        ops.rect(px0 + 0.05, py0 + 0.36, px0 + 1.15, py0 + 0.44, fill=hexc("#6e5234"))
        for k in range(9):
            ops.line([(x0 + 0.4 + k * 0.08 + (k // 5) * 0.1, y1 - 0.5), (x0 + 0.4 + k * 0.08 + (k // 5) * 0.1, y1 - 0.3)], fill=alpha(hexc("#f0f0ea"), 160), width=0.015)
        A.tool_rag(ops, x0 + 1.6, y1 - 0.9, seed=seed + 3, col=hexc("#9aa3a6"))
    elif key == "bootshaus":
        planks(fuge_w=0.045, tint=0.97)
        # Naesse um das Boot (Boot bei 9,5..13,5 / -12,4..-10,2), Pfuetzen mit Lichtkante, Tau, Rettungsring
        wet = HD.wobble_ellipse(x0 + 3.5, y0 + 1.5, 2.9, 1.6, amp=0.1, seed=seed + 1)
        ops.poly(wet, fill=alpha(hexc("#2a3a44"), 42))
        for k, (px_, py_) in enumerate(((x0 + 6.3, y0 + 1.3), (x0 + 1.0, y0 + 3.4), (x1 - 1.4, y1 - 1.0))):
            rx, ry = rnd.uniform(0.2, 0.35), rnd.uniform(0.12, 0.2)
            ops.poly(HD.wobble_ellipse(px_, py_, rx, ry, amp=0.015, seed=seed + 10 + k), fill=alpha(hexc("#3d5a6e"), 150), outline=alpha(C["erde_rand"], 200), width=0.025)
            ops.line([(px_ - rx * 0.5, py_ + ry * 0.35), (px_ - rx * 0.1, py_ + ry * 0.35)], fill=alpha(C["wasser_licht"], 180), width=0.03)
        cx_, cy_ = x0 + 0.85, y0 + 0.75   # westlich des Boots (bei x1 - 1 sass der Vent darueber)
        spiral = [(cx_ + (0.05 + 0.028 * k) * math.cos(k * 0.5), cy_ + (0.05 + 0.028 * k) * 0.75 * math.sin(k * 0.5)) for k in range(26)]
        ops.line(spiral, fill=OUTLINE, width=0.075)
        ops.line(spiral, fill=hexc("#d8cfb0"), width=0.045)
        ops.line(spiral[-6:], fill=alpha(hexc("#8a7a5a"), 150), width=0.02)
        rcx, rcy = x0 + 0.8, y1 - 0.9
        ops.ellipse(rcx, rcy, 0.3, 0.3, fill=hexc("#e05040"), outline=OUTLINE, width=0.03)
        for a in (0, 90, 180, 270):
            ops.poly([(rcx + 0.3 * math.cos(math.radians(a - 15)), rcy + 0.3 * math.sin(math.radians(a - 15))),
                      (rcx + 0.3 * math.cos(math.radians(a + 15)), rcy + 0.3 * math.sin(math.radians(a + 15))),
                      (rcx + 0.14 * math.cos(math.radians(a + 15)), rcy + 0.14 * math.sin(math.radians(a + 15))),
                      (rcx + 0.14 * math.cos(math.radians(a - 15)), rcy + 0.14 * math.sin(math.radians(a - 15)))], fill=hexc("#f0f0ea"))
        ops.ellipse(rcx, rcy, 0.14, 0.14, fill=shade(cols[0], 0.9), outline=OUTLINE, width=0.025)
        ops.ellipse(rcx - 0.12, rcy + 0.12, 0.06, 0.04, fill=alpha((255, 255, 255, 255), 90))
        A.tool_bucket(ops, x1 - 0.7, y1 - 1.6, r=0.13, h=0.26)
    elif key == "wachstube":
        planks(tint=0.9)
        # Fussmatte an der Nordtuer (-24..-21,5), Kabel von der Monitorwand, Kaffeering
        mat = HD.wobble_rect(x0 + 2.65, y1 - 0.62, x0 + 4.35, y1 - 0.12, amp=0.005, seed=seed + 3, step=0.1)
        ops.poly(mat, fill=hexc("#5a4630"), outline=OUTLINE, width=0.025)
        for k in range(8):
            ops.line([(x0 + 2.8 + k * 0.2, y1 - 0.55), (x0 + 2.8 + k * 0.2, y1 - 0.2)], fill=alpha(hexc("#8a6a45"), 180), width=0.025)
        A.floor_cable(ops, [(x0 + 0.85, y0 + 2.2), (x0 + 1.4, y0 + 1.6), (x0 + 1.6, y0 + 0.9), (x0 + 2.3, y0 + 0.5)], seed=seed + 4)
        ops.ellipse(x0 + 5.6, y0 + 1.1, 0.07, 0.07, outline=alpha(hexc("#5a3a22"), 150), width=0.018)
    elif key == "generator":
        concrete(hexc("#6e6a62"), hexc("#55524c"))
        # Warnstreifen VOR dem Aggregat (-14,9..-11,9 / -11,4..-9,8; sein Sprite verdeckt den Boden noerdlich
        # der Standlinie), Oelflecken, Kabelkanal zum Sicherungskasten
        A.hazard(ops, x0 + 0.4, y0 + 0.3, x0 + 3.8, y0 + 0.55)
        A.oil_stain(ops, x0 + 4.6, y0 + 1.7, 0.45, 0.24, seed=seed + 1, a=120)
        A.oil_stain(ops, x0 + 4.9, y0 + 1.2, 0.3, 0.18, seed=seed + 2, a=100)
        A.cable_duct(ops, [(x0 + 3.5, y0 + 2.5), (x0 + 3.5, y0 + 3.8), (x0 + 0.55, y0 + 3.8)], w=0.14)
        for k in range(2):
            ops.ellipse(x1 - 1.0 - k * 0.5, y0 + 0.7, 0.18, 0.13, outline=alpha((20, 18, 16, 255), 90), width=0.03)
        A.tool_wrench(ops, x1 - 1.6, y0 + 2.0, 0.6, L=0.26)
        A.tool_rag(ops, x1 - 2.3, y0 + 1.4, seed=seed + 5, col=hexc("#a8403a"))
    else:
        planks()


def draw_far_shore(ops, water, rnd):
    """Gegenufer am Ostrand des Bachs (voller Pass): das Wasser reicht bis zum Kartenrand (x 25,5), rechts
    davon ist im Spiel Schwarz. Deshalb ab x ~24,8 ein schmales Uferband (Schlamm, Sand, Steine, Schilf,
    Wurzeln) und ab x ~25,1 Baumkronen, so weit BOUNDS reicht. Das Kanu (AtlasFerry) faehrt bis x 24,4 und
    bleibt frei."""
    wx0, wy0, wx1, wy1 = water.bounds
    sx = wx1 - 0.72
    line = HD.wobble([(sx, wy0 - 0.3), (sx, wy1 + 0.3)], amp=0.07, seed=610, step=0.25)
    band = Polygon([(wx1 + 0.5, wy0 - 0.3)] + line + [(wx1 + 0.5, wy1 + 0.3)])
    fill(ops, band, hexc("#5a4630"))
    inner = Polygon([(wx1 + 0.5, wy0 - 0.3)] + [(x + 0.16, y) for x, y in line] + [(wx1 + 0.5, wy1 + 0.3)])
    fill(ops, inner, alpha(hexc("#a28a68"), 200))
    A.speckle(ops, band.intersection(box(BX0, BY0, BX1, BY1)), 160, [alpha(hexc("#7c5e3c"), 180), alpha(hexc("#c9b088"), 150)], 0.015, 0.035, seed=611)
    ops.line(line, fill=alpha(hexc("#1b3f5c"), 255), width=0.07)
    ops.line([(x - 0.07, y) for x, y in line], fill=alpha(hexc("#8fc4e8"), 120), width=0.04)
    # Wurzeln am Gegenufer
    for i in range(int((wy1 - wy0) * 1.2)):
        py_ = rnd.uniform(wy0, wy1)
        px_ = sx + rnd.uniform(0.25, 0.5)
        ops.line([(px_, py_), (px_ - 0.2, py_ + rnd.uniform(-0.08, 0.08))], fill=C["wurzel"], width=0.05)
    # Kronen: Mitte ausserhalb der Karte, nur der Westrand ragt herein
    y = wy1 + 0.6
    ci = 0
    while y > wy0 - 0.8:
        r = rnd.uniform(0.9, 1.35)
        cx = wx1 - 0.38 + r + rnd.uniform(0.0, 0.25)
        col = rnd.choice(C["krone"])
        pts = HD.wobble_ellipse(cx, y, r, r, amp=r * 0.035, seed=700 + ci)
        ops.poly(pts, fill=col, outline=OUTLINE, width=0.05)
        ops.ellipse(cx - r * 0.55, y + r * 0.2, r * 0.3, r * 0.28, fill=alpha(C["krone_licht"], 130))
        y -= rnd.uniform(0.95, 1.25)
        ci += 1
    # Steine halb im Wasser und Schilf am Gegenufer
    yy = wy0 + 0.5
    i = 0
    while yy < wy1 - 0.3:
        if rnd.random() < 0.6:
            r = rnd.uniform(0.08, 0.16)
            px_ = sx + rnd.uniform(-0.12, 0.2)
            if px_ < sx + 0.02:
                ops.ellipse(px_, yy - 0.02, r * 1.7, r * 1.1, outline=alpha(hexc("#8fc4e8"), 140), width=0.025)
            ops.poly(HD.wobble_ellipse(px_, yy, r, r * 0.72, amp=0.006, seed=720 + i), fill=C["fels"], outline=OUTLINE, width=0.03)
            ops.ellipse(px_ - r * 0.3, yy + r * 0.22, r * 0.42, r * 0.26, fill=shade(C["fels"], 1.2))
        if rnd.random() < 0.5:
            cx_ = sx + rnd.uniform(-0.05, 0.25)
            n = rnd.randint(3, 6)
            for k in range(n):
                bx = cx_ + (k - n / 2) * 0.06 + rnd.uniform(-0.02, 0.02)
                h = rnd.uniform(0.3, 0.55)
                tip = (bx + rnd.uniform(-0.1, 0.1), yy + 0.3 + h)
                ops.line([(bx, yy + 0.3), ((bx + tip[0]) / 2 + rnd.uniform(-0.03, 0.03), yy + 0.3 + h * 0.5), tip],
                         fill=rnd.choice([C["schilf"], shade(C["schilf"], 0.85)]), width=0.026)
                if k % 2 == 1 and rnd.random() < 0.6:
                    ops.ellipse(tip[0], tip[1] - 0.05, 0.026, 0.065, fill=C["schilf_kolben"], outline=OUTLINE, width=0.01)
        yy += rnd.uniform(0.6, 1.1)
        i += 1


def draw_water(ops, water, rnd):
    """See (Stilblatt): flache Farbflaechen in drei Tiefenstufen mit welligen Grenzen, kurze Wellenstriche
    (hell oben, dunkel darunter), Mondbahn, Seerosen nahe am Ufer."""
    wx0, wy0, wx1, wy1 = water.bounds
    fill(ops, water, C["wasser"])
    # Tiefenstufen: flach (hell) am Westufer, tief (dunkel) im Osten, Grenzen wellig
    shallow = HD.wobble([(wx0 + 1.3, wy0 - 0.5), (wx0 + 1.3, wy1 + 0.5)], amp=0.35, seed=301, step=0.4)
    fill(ops, Polygon([(wx0 - 0.5, wy0 - 0.5)] + shallow + [(wx0 - 0.5, wy1 + 0.5)]).intersection(water), alpha(C["wasser_licht"], 60))
    deep = HD.wobble([(wx1 - 1.6, wy0 - 0.5), (wx1 - 1.6, wy1 + 0.5)], amp=0.3, seed=302, step=0.4)
    fill(ops, Polygon([(wx1 + 0.5, wy0 - 0.5)] + deep + [(wx1 + 0.5, wy1 + 0.5)]).intersection(water), alpha(hexc("#1b3f5c"), 110))
    # Mondbahn: laenglicher Schein mit hellen Querstrichen
    mx = wx0 + 3.0
    for k in range(3):
        ops.glow(mx, (wy0 + wy1) / 2 + (k - 1) * 1.6, 1.6, A.MOON, 0.16)
    # Wellen: kurze gebogene Striche, Licht oben + Schatten darunter (zwei Stufen, keine Verlaeufe)
    yy = wy0 + 0.35
    k = 0
    while yy < wy1 - 0.2:
        xx = wx0 + rnd.uniform(0.3, 1.0)
        while xx < wx1 - 0.3:
            ln = rnd.uniform(0.35, 0.9)
            near_moon = abs(xx + ln / 2 - mx) < 0.9
            pts = HD.wobble([(xx, yy), (xx + ln, yy)], amp=0.03, seed=k, step=0.08)
            if water.contains(Point(xx, yy)) and water.contains(Point(xx + ln, yy)):
                ops.line(pts, fill=alpha(hexc("#1b3f5c"), 150), width=0.045)
                ops.line([(x, y + 0.035) for x, y in pts], fill=alpha(C["wasser_licht"] if not near_moon else hexc("#dbe9f5"), 230 if near_moon else 200), width=0.04)
            xx += ln + rnd.uniform(0.6, 1.6)
            k += 1
        yy += rnd.uniform(0.45, 0.8)
    # Seerosen nahe am Ufer (Kreis mit Kerbe, Lichtkante, eine Bluete)
    for i in range(7):
        px_, py_ = wx0 + rnd.uniform(0.5, 1.5), rnd.uniform(wy0 + 0.6, wy1 - 0.6)
        if not water.buffer(-0.3).contains(Point(px_, py_)) or near_dock(py_, 1.3):
            continue
        r = rnd.uniform(0.14, 0.22)
        a0 = rnd.uniform(0, math.tau)
        pts = [(px_ + math.cos(a0 + t * (math.tau - 0.9) / 20 + 0.45) * r, py_ + math.sin(a0 + t * (math.tau - 0.9) / 20 + 0.45) * r * 0.85) for t in range(21)]
        pts = [(px_, py_)] + pts
        ops.poly(HD.wobble(pts, amp=0.006, seed=400 + i, step=0.05, closed=True), fill=hexc("#4f8a3a"), outline=OUTLINE, width=0.025)
        ops.ellipse(px_ - r * 0.3, py_ + r * 0.25, r * 0.35, r * 0.22, fill=alpha(hexc("#7ab85a"), 160))
        if i % 3 == 0:
            for t in range(6):
                a = t * math.tau / 6
                ops.ellipse(px_ + math.cos(a) * r * 0.3, py_ + r * 0.1 + math.sin(a) * r * 0.25, r * 0.16, r * 0.12, fill=hexc("#f8e8f0"), outline=OUTLINE, width=0.012)
            ops.ellipse(px_, py_ + r * 0.1, r * 0.1, r * 0.08, fill=hexc("#f2c23a"))


def near_dock(y, d):
    """Liegt die Hoehe y naeher als d an der Mitte eines Stegs (W.DOCKS)?"""
    return any(abs(y - (k[2] + k[4]) / 2) < d for k in W.DOCKS)


def draw_shore(ops, water, walk, forest, rnd):
    """Uferband (Stilblatt): wo Lichtung oder Hof an das Wasser stossen, ein schmaler Streifen Schlamm und
    Sand mit welliger Wasserkante, der in das Wasser hineinragt (die Kollision bleibt die gerade Kante
    bei x = 20,3: der Spieler haelt vor dem Schlamm). Steine halb im Wasser mit Ring, Schilfgruppen am
    Ufer und im Flachwasser, am Waldufer dunkle Wurzeln."""
    wx0, wy0, wx1, wy1 = water.bounds
    dock = unary_union([G.shape(k) for k in W.DOCKS])
    shore_x = wx0
    # welliger Verlauf der Wasserkante (langsame Welle + feine Unruhe), ueber die ganze Westkante
    line = HD.wobble([(shore_x + 0.32, wy0 - 0.3), (shore_x + 0.32, wy1 + 0.3)], amp=0.2, seed=310, step=0.25)
    band = Polygon([(shore_x - 0.08, wy0 - 0.3)] + line + [(shore_x - 0.08, wy1 + 0.3)]).difference(dock.buffer(0.02))
    mud = alpha(hexc("#5a4630"), 255)
    sand = hexc("#a28a68")
    # nur wo an Land tatsaechlich begehbare Flaeche liegt (Lichtung/Hof); am Waldufer Wurzeln statt Sand
    land = walk.buffer(0.6)
    sandy = band.intersection(land.buffer(0.3))
    rooty = band.difference(land)
    fill(ops, sandy, mud)
    inner = Polygon([(shore_x - 0.08, wy0 - 0.3)] + [(x - 0.12, y) for x, y in line] + [(shore_x - 0.08, wy1 + 0.3)]).difference(dock.buffer(0.02))
    fill(ops, inner.intersection(land.buffer(0.3)), alpha(sand, 200))
    A.speckle(ops, sandy, 160, [alpha(hexc("#7c5e3c"), 180), alpha(hexc("#c9b088"), 150)], 0.015, 0.035, seed=311)
    # nasser Schlamm: sparsame Schraffur als Akzent (Stilblatt)
    for seg in HD.hatch(sandy.difference(inner), spacing=0.09, angle=-30, seed=312, density=0.35, length=(0.06, 0.14)):
        ops.line(seg, fill=alpha(hexc("#3a2a18"), 110), width=0.015)
    fill(ops, rooty, alpha(hexc("#3a2a18"), 255))
    for part in geom_parts(rooty):
        for _ in range(int(part.area * 6)):
            px_, py_ = rnd.uniform(part.bounds[0], part.bounds[2]), rnd.uniform(part.bounds[1], part.bounds[3])
            if part.contains(Point(px_, py_)):
                ops.line([(px_ - 0.1, py_), (px_ + 0.15, py_ + rnd.uniform(-0.08, 0.08))], fill=C["wurzel"], width=0.05)
    # Wasserkante: dunkler Strich mit leicht schwankender Staerke, darunter ein heller Saum im Wasser
    for part in geom_parts(band):
        edge = [(x, y) for x, y in part.exterior.coords if x > shore_x + 0.02]
        if len(edge) > 3:
            ops.line(edge, fill=alpha(hexc("#1b3f5c"), 255), width=0.07)
            ops.line([(x + 0.07, y) for x, y in edge], fill=alpha(hexc("#8fc4e8"), 120), width=0.04)
    # Steine: am Ufer und halb im Wasser (Ring im Wasser), mit Lichtkante oben links
    yy = wy0 + 0.4
    i = 0
    while yy < wy1 - 0.3:
        if not near_dock(yy, 1.1) and land.contains(Point(shore_x - 0.3, yy)) and rnd.random() < 0.7:
            r = rnd.uniform(0.09, 0.2)
            sx = shore_x + rnd.uniform(0.0, 0.45)
            in_water = sx > shore_x + 0.25
            if in_water:
                ops.ellipse(sx, yy - 0.02, r * 1.7, r * 1.1, outline=alpha(hexc("#8fc4e8"), 140), width=0.025)
            ops.ellipse(sx + 0.03, yy - 0.04, r, r * 0.72, fill=alpha((10, 20, 30, 255), 110))
            ops.poly(HD.wobble_ellipse(sx, yy, r, r * 0.72, amp=0.006, seed=320 + i), fill=C["fels"], outline=OUTLINE, width=0.03)
            ops.ellipse(sx - r * 0.3, yy + r * 0.22, r * 0.42, r * 0.26, fill=shade(C["fels"], 1.2))
            ops.ellipse(sx + r * 0.3, yy - r * 0.2, r * 0.4, r * 0.2, fill=alpha(C["fels_dunkel"], 170))
            i += 1
        yy += rnd.uniform(0.45, 0.9)
    # Schilfgruppen: 4 bis 7 Halme, Kolben, teils im Flachwasser
    yy = wy0 + 0.3
    j = 0
    while yy < wy1 - 0.3:
        if not near_dock(yy, 1.0) and rnd.random() < 0.6:
            cx_ = shore_x + rnd.choice((-0.15, 0.1, 0.4, 0.55))
            if cx_ < shore_x and not land.contains(Point(cx_, yy)):
                yy += 0.5
                continue
            n = rnd.randint(4, 7)
            if cx_ > shore_x + 0.2:
                ops.ellipse(cx_, yy - 0.05, 0.3, 0.12, outline=alpha(hexc("#8fc4e8"), 110), width=0.02)
            for k in range(n):
                bx = cx_ + (k - n / 2) * 0.07 + rnd.uniform(-0.02, 0.02)
                h = rnd.uniform(0.35, 0.6)
                tip = (bx + rnd.uniform(-0.12, 0.12), yy + h)
                ops.line([(bx, yy - 0.04), ((bx + tip[0]) / 2 + rnd.uniform(-0.03, 0.03), yy + h * 0.5), tip], fill=rnd.choice([C["schilf"], shade(C["schilf"], 0.85), shade(C["schilf"], 1.15)]), width=0.028)
                if k % 2 == 1 and rnd.random() < 0.7:
                    ops.ellipse(tip[0], tip[1] - 0.05, 0.028, 0.07, fill=C["schilf_kolben"], outline=OUTLINE, width=0.01)
            j += 1
        yy += rnd.uniform(0.5, 1.0)


def draw_dock(ops, water, rnd, dock):
    """Bootssteg (ueber dem Wasser, begehbar): Schatten und Spiegelung im Wasser, Bohlen mit zittrigen
    Fugen und eigenem Ton, vier Pfaehle, Poller, Leine. Kein gemaltes Boot: das Kanu legt zur Laufzeit an
    (AtlasFerry "canoe", User 01.10.)."""
    dx0, dy0, dx1, dy1 = dock[1:5]
    wood, wood_d = hexc("#9a6a3e"), hexc("#6e4a2a")
    # Schatten + Spiegelung (Streifen unter dem Steg)
    ops.rect(dx0 + 0.1, dy0 - 0.16, dx1 + 0.1, dy1 - 0.1, fill=(0, 0, 0, 80))
    for k in range(5):
        ops.line([(dx0 + 0.4 + k * 0.6, dy0 - 0.22), (dx0 + 0.75 + k * 0.6, dy0 - 0.22)], fill=alpha(hexc("#8fc4e8"), 100), width=0.03)
    # Bohlen quer zum Steg
    ops.poly(HD.wobble_rect(dx0, dy0, dx1, dy1, amp=0.006, seed=330, step=0.1), fill=wood, outline=OUTLINE, width=0.06)
    xx = dx0 + 0.02
    k = 0
    while xx < dx1 - 0.05:
        w = rnd.uniform(0.24, 0.34)
        t = rnd.uniform(0.9, 1.08)
        ops.rect(xx, dy0 + 0.03, min(dx1 - 0.02, xx + w), dy1 - 0.03, fill=shade(wood, t))
        if k > 0:
            ops.line(HD.wobble([(xx, dy0 + 0.02), (xx, dy1 - 0.02)], amp=0.004, seed=340 + k, step=0.08), fill=wood_d, width=0.025)
        ops.line([(xx + 0.02, dy1 - 0.06), (min(dx1 - 0.02, xx + w) - 0.02, dy1 - 0.06)], fill=alpha(shade(wood, 1.25), 150), width=0.02)   # Lichtkante
        if rnd.random() < 0.3:
            ops.ellipse(xx + w / 2, rnd.uniform(dy0 + 0.3, dy1 - 0.3), 0.03, 0.02, fill=alpha(wood_d, 200))
        xx += w
        k += 1
    for px_ in (dx0 + 0.9, dx1 - 0.15):                                   # Pfaehle
        for py_ in (dy0 + 0.12, dy1 - 0.12):
            ops.ellipse(px_, py_, 0.12, 0.12, fill=hexc("#5a3d24"), outline=OUTLINE, width=0.03)
            ops.ellipse(px_, py_, 0.07, 0.07, fill=hexc("#c9a46a"))
            ops.ellipse(px_, py_, 0.035, 0.035, outline=alpha(wood_d, 200), width=0.012)
    ops.line([(dx1 - 0.35, dy0 + 0.4), (dx1 - 0.1, dy0 + 0.22), (dx1 - 0.18, dy0 + 0.1)], fill=hexc("#d8cfb0"), width=0.04)   # aufgeschossene Leine


def draw_paths(ops, paths, outdoor, grass, rnd):
    """Wege (Stilblatt): Erde mit welligem Rand (zittriger Umriss statt Buffer-Band), abgelaufene dunklere
    Mittelspur, Fahrspuren, Pfuetzen mit Lichtkante, Randsteine mit Umriss, Grasbueschel, die vom Rand
    hereinwachsen. Rueckgabe: die (gezitterte) Wegflaeche fuer die weiteren Schritte."""
    wob_parts = []
    for i, part in enumerate(geom_parts(paths)):
        pts = HD.wobble(list(part.exterior.coords)[:-1], amp=0.06, seed=500 + i, step=0.25, closed=True)
        g = Polygon(pts).buffer(0)
        if not g.is_empty:
            wob_parts.append(g)
    wob = unary_union(wob_parts).intersection(outdoor).buffer(0)
    fill(ops, wob.buffer(0.16).intersection(outdoor), C["erde_rand"])
    fill(ops, wob, C["erde"])
    # Umriss leicht zittrig und in der Staerke schwankend (Pen-Ersatz: zwei Linien verschiedener Breite)
    for i, part in enumerate(geom_parts(wob)):
        ring = list(part.exterior.coords)
        ops.line(ring, fill=alpha(shade(C["erde_rand"], 0.8), 220), width=0.04)
    A.speckle(ops, wob, 1400, [C["erde2"], C["kiesel"]], 0.02, 0.06, seed=9)
    # trockene, hellere Flecken (flach, zittriger Rand) und feuchte dunkle Senken
    for i in range(70):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if wob.buffer(-0.3).contains(p):
            rx, ry = rnd.uniform(0.25, 0.6), rnd.uniform(0.15, 0.3)
            dry = rnd.random() < 0.6
            ops.poly(HD.wobble_ellipse(p.x, p.y, rx, ry, amp=0.03, seed=540 + i),
                     fill=alpha(hexc("#a8865c"), 90) if dry else alpha(shade(C["erde2"], 0.8), 90))
    # abgelaufene Mitte: dunkler, festgetretener Streifen mit welligem Rand
    for i, pts in enumerate(W.PATHS):
        lane = HD.wobble(pts, amp=0.08, seed=520 + i, step=0.3)
        g = LineString(lane).buffer(0.42, 8).intersection(wob)
        fill(ops, g, alpha(shade(C["erde2"], 0.9), 150))
        # vereinzelt eine Wurzel quer ueber den Weg (Stilblatt: Schraffur nur als seltener Akzent)
        if i % 4 == 1:
            ls = LineString(pts)
            q = ls.interpolate(ls.length * 0.45)
            dx, dy = (pts[-1][0] - pts[0][0]), (pts[-1][1] - pts[0][1])
            n = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / n, dx / n
            root = HD.wobble([(q.x + nx * 1.1, q.y + ny * 1.1), (q.x - nx * 1.1, q.y - ny * 1.1)], amp=0.06, seed=560 + i, step=0.15)
            ops.line(root, fill=C["wurzel"], width=0.09)
            ops.line(root, fill=alpha(shade(C["wurzel"], 1.45), 200), width=0.03)
            for seg in HD.hatch(LineString(root).buffer(0.16).intersection(wob), spacing=0.07, angle=60, seed=i, density=0.5, length=(0.08, 0.16)):
                ops.line(seg, fill=alpha(C["wurzel"], 90), width=0.015)
    for pts in W.PATHS:   # Fahrspuren
        ls = LineString(pts)
        for off in (-0.45, 0.45):
            tr = ls.parallel_offset(off, "left") if ls.length > 0.5 else None
            if tr is not None and not tr.is_empty and tr.geom_type == "LineString":
                seg = tr.intersection(wob.buffer(-0.2))
                for q in ([seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))):
                    if q.geom_type == "LineString" and q.length > 0.3:
                        ops.line(HD.wobble(list(q.coords), amp=0.02, seed=int(q.length * 10), step=0.2), fill=alpha(shade(C["erde2"], 0.85), 200), width=0.12)
    # Pfuetzen mit heller Lichtkante
    for _ in range(10):
        p = Point(rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1))
        if wob.buffer(-0.5).contains(p):
            rx, ry = rnd.uniform(0.25, 0.45), rnd.uniform(0.15, 0.25)
            ops.poly(HD.wobble_ellipse(p.x, p.y, rx, ry, amp=0.015, seed=int(p.x * 7)), fill=alpha(hexc("#3d5a6e"), 160), outline=alpha(C["erde_rand"], 220), width=0.03)
            ops.line([(p.x - rx * 0.5, p.y + ry * 0.35), (p.x - rx * 0.1, p.y + ry * 0.35)], fill=alpha(C["wasser_licht"], 180), width=0.03)
    # Randsteine und Grasbueschel entlang des Wegrands
    for i, part in enumerate(geom_parts(wob)):
        ring = part.exterior
        s = 0.3
        while s < ring.length:
            p = ring.interpolate(s)
            if outdoor.buffer(-0.2).contains(p):
                if rnd.random() < 0.35:
                    r = rnd.uniform(0.05, 0.1)
                    ops.ellipse(p.x, p.y, r, r * 0.7, fill=rnd.choice([C["fels"], C["kiesel"]]), outline=alpha(C["erde_rand"], 230), width=0.02)
                    ops.ellipse(p.x - r * 0.25, p.y + r * 0.2, r * 0.4, r * 0.25, fill=alpha((255, 255, 255, 255), 70))
                elif rnd.random() < 0.5:
                    for k in range(3):
                        ops.line([(p.x + (k - 1) * 0.05, p.y), (p.x + (k - 1) * 0.1, p.y + 0.16)], fill=C["halm"], width=0.025)
            s += rnd.uniform(0.35, 0.8)
    return wob


GRAIN = 0.0   # Papierkorn (Stilblatt 3 bis 5 %): bei JPEG q93 kostet 3 % Korn rund +80 % Dateigroesse (Messung
              # 01.10. am Museum: 4,5 -> 9,0 MB), das sprengt das 15-%-Budget der Bodenkacheln; deshalb aus


def hut_lanes(doors):
    """Abnutzungsspuren in den Huetten: Trampelpfad von jeder Tuer 2 m in den Raum (bis zur Raummitte
    verschmierte es die Teppiche). Dielen und Estrich laufen sich hell (blank), Linoleum im Labor dunkel."""
    lanes = []
    for key, side, a, b, kind, o in doors:
        c = o.centroid
        end = {"N": (c.x, c.y - 2.0), "S": (c.x, c.y + 2.0), "E": (c.x - 2.0, c.y), "W": (c.x + 2.0, c.y)}[side]
        lanes.append(([(c.x, c.y), end], key != "labor"))
    return lanes


def render_floor(walk, water, shells, doors, rooms):
    ops = build_floor_ops(walk, water, shells, doors, rooms)
    img = ops.render(BX0, BY0, BX1, BY1, FLOOR_PPM, A.VOID)
    img = A.apply_wear(img, walk, BX0, BY0, BX1, BY1, lanes=hut_lanes(doors))
    img = A.ambient_occlusion(img, walk, BX0, BY0, BX1, BY1)
    if GRAIN:
        img = HD.paper_grain(img, GRAIN, seed=4, scale=2)
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
     "turm": 3.2, "mast": 4.2, "tank": 3.0, "pumpenhaus": 1.9, "hochsitz": 4.4, "hochsitz_front": 4.4, "hochsitz_roof": 4.4, "baum": 3.2,
     "bank": 0.45, "kartentisch": 0.85, "lagerfeuer": 0.5, "baumstamm": 0.45}
LEGGED = {"bank", "kartentisch", "tisch_lang"}

# Hochsitz (User 26.09.): begehbare Kanzel, oben laeuft man in alle Richtungen (AtlasLookout). Drei
# Sprites, damit die Figuren oben dazwischen einsortiert werden:
#   hochsitz       Beine, Leiter, Deck, hinteres Gelaender        (hinter den Figuren)
#   hochsitz_front vorderes + seitliche Gelaender, vier Eckpfosten (vor den Figuren; die Pfosten sind
#                  fuer den, der oben steht, auch Sichtblocker)
#   hochsitz_roof  Satteldach (ganz vorn; AtlasLookout blendet es aus, solange jemand oben ist)
# Masse in Metern ueber Grund; AtlasLookout rechnet mit denselben Werten (Deck, Pfosten, Klappe).
HS_KINDS = ("hochsitz", "hochsitz_front", "hochsitz_roof")
HS_FLOOR, HS_RAIL, HS_POST_TOP, HS_RIDGE = 2.2, 0.4, 3.5, 4.15
HS_OVER, HS_POST, HS_RAIL_T = 0.2, 0.14, 0.07
HS_LADDER = (0.25, 0.65)                     # Leiterholme relativ zu x0; darueber die Klappe im Frontgelaender


def draw_hochsitz(p, kind, x0, y0, x1, y1, wood, wood_d, grain, lantern):
    c, K = p.c, A.K
    dx0, dx1 = x0 - HS_OVER, x1 + HS_OVER
    lx0, lx1 = x0 + HS_LADDER[0], x0 + HS_LADDER[1]
    light, dark = shade(wood, 1.15), wood_d
    if kind == "hochsitz":
        # Streben, dann die vorderen Beine (die hinteren verdeckt das Deck), dann die Leiter
        zb = HS_FLOOR - 0.15
        c.line([(x0 + 0.25, y0 + zb * K), (x1 - 0.25, y0 + 0.2)], fill=alpha(wood_d, 220), width=0.05)
        c.line([(x1 - 0.25, y0 + zb * K), (x0 + 0.25, y0 + 0.2)], fill=alpha(wood_d, 160), width=0.04)
        for lx in (dx0 + 0.02, dx1 - 0.2):
            c.rect(lx, y0, lx + 0.18, y0 + zb * K, fill=wood_d, outline=OUTLINE, width=0.03)
        for sx in (lx0, lx1 - 0.05):
            c.rect(sx, y0 - 0.05, sx + 0.05, y0 + HS_FLOOR * K, fill=wood, outline=OUTLINE, width=0.02)
        for k in range(6):
            yy = y0 + 0.15 + k * (HS_FLOOR * K - 0.2) / 5
            c.line([(lx0 + 0.04, yy), (lx1 - 0.04, yy)], fill=wood, width=0.045)
        # Deck: Vorderkante + Bohlen; die Klappe ueber der Leiter ist offen
        p.box(dx0, y0, dx1, y1, HS_FLOOR - 0.15, 0.15, light, dark)
        top0, top1 = y0 + HS_FLOOR * K, y1 + HS_FLOOR * K
        yy = top0 + 0.22
        while yy < top1 - 0.05:
            c.line([(dx0 + 0.03, yy), (dx1 - 0.03, yy)], fill=alpha(shade(wood, 0.8), 200), width=0.02)
            yy += 0.22
        c.rect(lx0, top0 + 0.01, lx1, top0 + 0.34, fill=hexc("#241a12"), outline=OUTLINE, width=0.025)
        for sx in (lx0 + 0.02, lx1 - 0.07):
            c.rect(sx, top0 + 0.01, sx + 0.05, top0 + 0.3, fill=wood)
        # hinteres Gelaender (Innenseite sichtbar)
        p.box(dx0, y1 - HS_RAIL_T, dx1, y1, HS_FLOOR, HS_RAIL, light, wood)
        grain(dx0 + 0.03, y1 - HS_RAIL_T + HS_FLOOR * K + 0.03, dx1 - 0.03, y1 - HS_RAIL_T + (HS_FLOOR + HS_RAIL) * K - 0.03, wood, 0.08)
    elif kind == "hochsitz_front":
        post_h = HS_POST_TOP - HS_FLOOR
        # hinten: Eckpfosten, dann die Seitengelaender, vorn: Gelaender (mit Luecke ueber der Leiter) + Pfosten
        for px in (dx0, dx1 - HS_POST):
            p.box(px, y1 - HS_POST, px + HS_POST, y1, HS_FLOOR, post_h, light, wood_d)
        for rx in (dx0, dx1 - HS_RAIL_T):
            p.box(rx, y0, rx + HS_RAIL_T, y1, HS_FLOOR, HS_RAIL, light, wood)
        for ra, rb in ((dx0, lx0 - 0.03), (lx1 + 0.03, dx1)):
            p.box(ra, y0, rb, y0 + HS_RAIL_T, HS_FLOOR, HS_RAIL, light, wood)
            grain(ra + 0.03, y0 + HS_FLOOR * K + 0.03, rb - 0.03, y0 + (HS_FLOOR + HS_RAIL) * K - 0.03, wood, 0.08)
        for px in (dx0, dx1 - HS_POST):
            p.box(px, y0, px + HS_POST, y0 + HS_POST, HS_FLOOR, post_h, light, wood_d)
        lantern(dx1 + 0.04, y0 + (HS_FLOOR + 0.75) * K)
    else:  # hochsitz_roof
        rx0, rx1, ry0, ry1 = dx0 - 0.15, dx1 + 0.15, y0 - 0.2, y1 + 0.2
        cx = (rx0 + rx1) / 2
        et, rt = HS_POST_TOP, HS_RIDGE
        roof = hexc("#5b3b22")
        for xa in (rx0, rx1):
            c.poly([(xa, ry0 + et * K), (cx, ry0 + rt * K), (cx, ry1 + rt * K), (xa, ry1 + et * K)],
                   fill=shade(roof, 1.12 if xa == rx0 else 0.92), outline=OUTLINE, width=0.05)
            for t in (0.3, 0.6):
                xt = xa + (cx - xa) * t
                zt = et + (rt - et) * t
                c.line([(xt, ry0 + zt * K + 0.03), (xt, ry1 + zt * K - 0.03)], fill=alpha(shade(roof, 0.7), 200), width=0.025)
        c.poly([(rx0, ry0 + et * K), (rx1, ry0 + et * K), (cx, ry0 + rt * K)], fill=wood_d, outline=OUTLINE, width=0.05)
        c.rect(rx0 + 0.1, ry0 + et * K - 0.08, rx1 - 0.1, ry0 + et * K, fill=wood, outline=OUTLINE, width=0.03)


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
    ext = 1.2 if kind == "baum" else (0.9 if kind == "tank" else (0.5 if kind in HS_KINDS else 0.0))
    p = A.Prop(x0 - ext, y0, x1 + ext, y1, h + (1.0 if kind in ("baum", "tank") else 0.0), ppm)
    c = p.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wood, wood_d = hexc("#9a6a3e"), hexc("#6e4a2a")
    if kind not in LEGGED and kind not in ("lagerfeuer", "hochsitz_front", "hochsitz_roof"):
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
    elif kind in HS_KINDS:
        draw_hochsitz(p, kind, x0, y0, x1, y1, wood, wood_d, grain, lantern)
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
    # Hochsitz-Front und -Dach als eigene, zugeschnittene Sprites (vor den Figuren oben, siehe HS_KINDS)
    items += [(s, part) for s, k in W.OPAQUE + W.GLASS if k == "hochsitz" for part in ("hochsitz_front", "hochsitz_roof")]
    images, meta = [], []
    for i, (s, kind) in enumerate(items):
        im, wx, wy, base = draw_prop(kind, s, i, PROP_PPM)
        im = im.filter(ImageFilter.GaussianBlur(0.45))
        if kind in ("hochsitz_front", "hochsitz_roof"):
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
    a("    /// <summary>Kanu (AtlasFerry): Use-Punkte an den Stegen, Fahrweg von A (Bootssteg) nach B (Wasserwerk).</summary>")
    a(f"    public static readonly Vector2 CanoeA = {v2(W.CANOE_A)}, CanoeB = {v2(W.CANOE_B)};")
    a("    public static readonly Vector2[] CanoePath = new Vector2[] { " + ", ".join(v2(p) for p in W.CANOE_PATH) + " };")
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
        HD.paste_clipped(fl, im, int((wx - BX0) * ppm), int((BY1 - wy) * ppm) - im.height)
    d = ImageDraw.Draw(fl)
    for k, p in consoles.items():
        x, y = (p[0] - BX0) * ppm, (BY1 - p[1]) * ppm
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 230, 0), outline=(0, 0, 0))
    fl.save(PREVIEW / "preview.png")
    print(PREVIEW / "preview.png", fl.size)


if __name__ == "__main__":
    main()
