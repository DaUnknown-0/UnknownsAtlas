# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_plan.py - Plan-Vorschau + Nachrechnung des Wald-Grundrisses (wie beim Museum-Bauplan):
# Laufwege (Rasterweg, 0,25 m), Sabotage-Paare, Vent-Spruenge, Sackgassen.
#   python tools/wald_plan.py   -> tools/_wald/plan.png + Textbericht

import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point

import wald_layout as W
import wald_geo as G

OUT = Path(__file__).resolve().parent / "_wald"
PPM = 20
STEP = 0.25


def raster(walk):
    x0, y0, x1, y1 = W.BOUNDS
    nx, ny = int((x1 - x0) / STEP), int((y1 - y0) / STEP)
    img = Image.new("L", (nx, ny), 0)
    d = ImageDraw.Draw(img)
    polys = [walk] if walk.geom_type == "Polygon" else list(walk.geoms)
    f = lambda x, y: ((x - x0) / STEP, (y1 - y) / STEP)
    for p in polys:
        d.polygon([f(*q) for q in p.exterior.coords], fill=255)
        for h in p.interiors:
            d.polygon([f(*q) for q in h.coords], fill=0)
    # Spielerradius: 0,3 m Abstand zu Waenden
    from PIL import ImageFilter
    img = img.filter(ImageFilter.MinFilter(3))
    return np.array(img) > 127


def dist_from(grid, start):
    x0, y0, x1, y1 = W.BOUNDS
    sx, sy = int((start[0] - x0) / STEP), int((y1 - start[1]) / STEP)
    h, w = grid.shape
    best = np.full(grid.shape, np.inf)
    # naechste begehbare Zelle
    if not grid[sy, sx]:
        ys, xs = np.nonzero(grid)
        k = np.argmin((xs - sx) ** 2 + (ys - sy) ** 2)
        sx, sy = xs[k], ys[k]
    best[sy, sx] = 0
    pq = [(0.0, sx, sy)]
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while pq:
        dcur, x, y = heapq.heappop(pq)
        if dcur > best[y, x]:
            continue
        for dx, dy, c in nb:
            u, v = x + dx, y + dy
            if 0 <= u < w and 0 <= v < h and grid[v, u]:
                nd = dcur + c * STEP
                if nd < best[v, u]:
                    best[v, u] = nd
                    heapq.heappush(pq, (nd, u, v))
    return best


def at(best, p):
    x0, y0, x1, y1 = W.BOUNDS
    sx, sy = int((p[0] - x0) / STEP), int((y1 - p[1]) / STEP)
    r = 4
    sub = best[max(0, sy - r):sy + r + 1, max(0, sx - r):sx + r + 1]
    return float(sub.min())


def main():
    walk, water, shells, doors = G.build()
    rooms = G.rooms(walk)
    grid = raster(walk)
    rep = []
    spawn = dist_from(grid, W.SPAWN)
    for k, p in W.FIXED.items():
        rep.append(f"Spawn -> {k:32s} {at(spawn, p):5.1f} m  {at(spawn, p) / 2.5:4.1f} s")
    for a, b in (("Reactor/UpperHandConsole/0", "Reactor/LowerHandConsole/1"),
                 ("LifeSupp/NoOxyConsole/0", "Admin/NoOxyConsole/1")):
        d = at(dist_from(grid, W.FIXED[a]), W.FIXED[b])
        rep.append(f"Paar {a} <-> {b}: {d:.1f} m ({d / 2.5:.1f} s)")
    for net in W.VENT_NETS:
        for i in range(len(net)):
            a, b = W.VENTS[net[i]], W.VENTS[net[(i + 1) % len(net)]]
            rep.append(f"Vent {net[i]}->{net[(i + 1) % len(net)]}: Luftlinie {math.dist(a, b):.1f} m")
    # Erreichbarkeit aller Raeume
    for key, (name, _s, g) in rooms.items():
        c = g.representative_point()
        d = at(spawn, (c.x, c.y))
        if not math.isfinite(d):
            rep.append(f"UNERREICHBAR: {name}")
    # Ausgaenge je Raum (Oeffnungen + Wege, die den Raumrand kreuzen)
    for key, (name, _s, g) in rooms.items():
        ring = g.buffer(0.6).exterior
        cut = ring.intersection(walk.buffer(-0.05))
        n = 0 if cut.is_empty else (1 if cut.geom_type == "LineString" else len(cut.geoms))
        if n < 2:
            rep.append(f"SACKGASSE? {name}: {n} Ausgang")
    print("\n".join(rep))
    (OUT / "plan_bericht.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")

    # Plan-Bild
    x0, y0, x1, y1 = W.BOUNDS
    img = Image.new("RGB", (int((x1 - x0) * PPM), int((y1 - y0) * PPM)), (22, 40, 30))
    d = ImageDraw.Draw(img, "RGBA")
    P = lambda x, y: ((x - x0) * PPM, (y1 - y) * PPM)
    for p in [walk] if walk.geom_type == "Polygon" else list(walk.geoms):
        d.polygon([P(*q) for q in p.exterior.coords], fill=(120, 92, 60))
        for h in p.interiors:
            d.polygon([P(*q) for q in h.coords], fill=(22, 40, 30))
    for key, (name, _s, g) in rooms.items():
        col = (190, 150, 100, 90) if key in [b[0] for b in W.BUILDINGS] else (110, 150, 80, 80)
        d.polygon([P(*q) for q in g.exterior.coords], fill=col)
    for s in shells:
        pass
    wp = [water] if water.geom_type == "Polygon" else list(water.geoms)
    for p in wp:
        d.polygon([P(*q) for q in p.exterior.coords], fill=(40, 80, 130))
    for key, side, a, b, kind, o in doors:
        d.polygon([P(*q) for q in o.exterior.coords], fill=(255, 60, 255) if kind == "door" else (120, 255, 120))
    for s, kind in W.OPAQUE:
        g = G.shape(s)
        d.polygon([P(*q) for q in g.exterior.coords], fill=(60, 45, 35), outline=(0, 0, 0))
    for s, kind in W.GLASS:
        g = G.shape(s)
        d.polygon([P(*q) for q in g.exterior.coords], fill=(160, 200, 230, 120), outline=(200, 230, 255))
    try:
        f = ImageFont.truetype("arialbd.ttf", 16)
        fs = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        f = fs = ImageFont.load_default()
    for key, (name, sysn, g) in rooms.items():
        c = g.representative_point()
        d.text(P(c.x, c.y), f"{name}\n({sysn})", font=f, fill=(255, 255, 255), anchor="mm", align="center")
    for k, p in W.FIXED.items():
        d.ellipse([P(*p)[0] - 6, P(*p)[1] - 6, P(*p)[0] + 6, P(*p)[1] + 6], fill=(230, 60, 40))
    for vid, p in W.VENTS.items():
        d.rectangle([P(*p)[0] - 6, P(*p)[1] - 4, P(*p)[0] + 6, P(*p)[1] + 4], fill=(170, 110, 255))
    for p in W.CAMERAS:
        d.ellipse([P(*p)[0] - 5, P(*p)[1] - 5, P(*p)[0] + 5, P(*p)[1] + 5], fill=(255, 255, 255))
    for p, col in ((W.SPAWN, (255, 220, 0)), (W.EMERGENCY, (255, 0, 0)), (W.ADMIN_TABLE, (0, 200, 255)),
                   (W.SURVEILLANCE, (0, 200, 255))):
        d.ellipse([P(*p)[0] - 7, P(*p)[1] - 7, P(*p)[0] + 7, P(*p)[1] + 7], outline=col, width=3)
    img.save(OUT / "plan.png")
    print(OUT / "plan.png", img.size)


if __name__ == "__main__":
    main()
