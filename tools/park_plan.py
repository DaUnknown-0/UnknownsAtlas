# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_plan.py - Plan-Vorschau + Nachrechnung des Park-Grundrisses (wie wald_plan.py):
# Laufwege (Raster 0,25 m, Hindernisse abgezogen), Sabotage-Paare, Vent-Spruenge, Sackgassen,
# Erreichbarkeit aller Spielpunkte, Wege in den Nordost-Block nur ueber die Bahnuebergaenge.
#   python tools/park_plan.py   -> tools/_park/plan.png + plan_bericht.txt

import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from shapely.geometry import Point
from shapely.ops import unary_union

import park_layout as L
import park_geo as G

OUT = Path(__file__).resolve().parent / "_park"
PPM = 20
STEP = 0.25
SPEED = 2.5   # m/s wie im Wald-Bericht


def raster(walk):
    x0, y0, x1, y1 = L.BOUNDS
    nx, ny = int((x1 - x0) / STEP), int((y1 - y0) / STEP)
    img = Image.new("L", (nx, ny), 0)
    d = ImageDraw.Draw(img)
    polys = [walk] if walk.geom_type == "Polygon" else list(walk.geoms)
    f = lambda x, y: ((x - x0) / STEP, (y1 - y) / STEP)
    for p in polys:
        d.polygon([f(*q) for q in p.exterior.coords], fill=255)
        for h in p.interiors:
            d.polygon([f(*q) for q in h.coords], fill=0)
    img = img.filter(ImageFilter.MinFilter(3))   # Spielerradius
    return np.array(img) > 127


def dist_from(grid, start):
    x0, y0, x1, y1 = L.BOUNDS
    sx, sy = int((start[0] - x0) / STEP), int((y1 - start[1]) / STEP)
    h, w = grid.shape
    best = np.full(grid.shape, np.inf)
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
    x0, y0, x1, y1 = L.BOUNDS
    sx, sy = int((p[0] - x0) / STEP), int((y1 - p[1]) / STEP)
    r = 4
    sub = best[max(0, sy - r):sy + r + 1, max(0, sx - r):sx + r + 1]
    return float(sub.min())


def main():
    OUT.mkdir(exist_ok=True)
    walk, water, shells, doors = G.build()
    rooms = G.rooms(walk)
    obstacles = unary_union([G.shape(s) for s, _k in L.OPAQUE] + [G.shape(s) for s, _k in L.GLASS])
    free = walk.difference(obstacles).buffer(0)
    grid = raster(free)
    rep = [f"Flaeche begehbar {walk.area:.0f} m2, Teile {1 if walk.geom_type == 'Polygon' else len(walk.geoms)}"]
    spawn = dist_from(grid, L.SPAWN)
    far = 0.0
    for k, p in list(L.FIXED.items()) + [("Admin-Tisch", L.ADMIN_TABLE), ("Kameras", L.SURVEILLANCE)]:
        d = at(spawn, p)
        far = max(far, d if math.isfinite(d) else 0)
        rep.append(f"Spawn -> {k:32s} {d:5.1f} m  {d / SPEED:4.1f} s" + ("" if math.isfinite(d) else "   UNERREICHBAR"))
    for a, b in (("Reactor/UpperHandConsole/0", "Reactor/LowerHandConsole/1"),
                 ("LifeSupp/NoOxyConsole/0", "Admin/NoOxyConsole/1")):
        d = at(dist_from(grid, L.FIXED[a]), L.FIXED[b])
        rep.append(f"Paar {a} <-> {b}: {d:.1f} m ({d / SPEED:.1f} s)")
    for vid, p in L.VENTS.items():
        if not math.isfinite(at(spawn, p)):
            rep.append(f"UNERREICHBAR: Vent {vid} {p}")
    for i, p in enumerate(L.CAMERAS):
        if not math.isfinite(at(spawn, p)):
            rep.append(f"UNERREICHBAR: Kamera {i} {p}")
    for net in L.VENT_NETS:
        for i in range(len(net)):
            a, b = L.VENTS[net[i]], L.VENTS[net[(i + 1) % len(net)]]
            rep.append(f"Vent {net[i]}->{net[(i + 1) % len(net)]}: Luftlinie {math.dist(a, b):.1f} m")
    for va, vb in L.VENT_BRIDGES:
        rep.append(f"Vent-Bruecke {va}<->{vb}: Luftlinie {math.dist(L.VENTS[va], L.VENTS[vb]):.1f} m")
    for key, (name, _s, g) in rooms.items():
        c = g.intersection(free.buffer(-0.4)).representative_point()   # freier Punkt, nicht im Karussell
        d = at(spawn, (c.x, c.y))
        rep.append(f"Raum {name:18s} {g.area:6.0f} m2  ab Spawn {d:5.1f} m" + ("" if math.isfinite(d) else "   UNERREICHBAR"))
    for key, (name, _s, g) in rooms.items():
        ring = g.buffer(0.6).exterior
        cut = ring.intersection(walk.buffer(-0.05))
        n = 0 if cut.is_empty else (1 if cut.geom_type == "LineString" else len(cut.geoms))
        if n < 2:
            rep.append(f"SACKGASSE? {name}: {n} Ausgang")
    rep.append(f"weitester Spielpunkt ab Spawn: {far:.1f} m ({far / SPEED:.1f} s)")
    print("\n".join(rep))
    (OUT / "plan_bericht.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")

    # Plan-Bild
    x0, y0, x1, y1 = L.BOUNDS
    img = Image.new("RGB", (int((x1 - x0) * PPM), int((y1 - y0) * PPM)), (26, 28, 44))
    d = ImageDraw.Draw(img, "RGBA")
    Pt = lambda x, y: ((x - x0) * PPM, (y1 - y) * PPM)

    def poly(g, **kw):
        for p in [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", [])):
            if p.geom_type != "Polygon":
                continue
            d.polygon([Pt(*q) for q in p.exterior.coords], **kw)

    for p in [walk] if walk.geom_type == "Polygon" else list(walk.geoms):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=(150, 140, 120))
        for h in p.interiors:
            d.polygon([Pt(*q) for q in h.coords], fill=(26, 28, 44))
    for key, (name, _s, g) in rooms.items():
        col = (210, 170, 110, 90) if key in [b[0] for b in L.BUILDINGS] else (120, 170, 110, 80)
        poly(g, fill=col)
    poly(water, fill=(40, 90, 150))
    for s in L.RAIL:
        poly(G.shape(s), fill=(200, 110, 40, 200))
    for _k, s, _dir in L.CROSSINGS:
        poly(G.shape(s), fill=(255, 220, 0, 230))
    for _k, s in L.TURNSTILES:
        poly(G.shape(s), fill=(0, 230, 230, 230))
    for key, side, a, b, kind, o in doors:
        poly(o, fill=(255, 60, 255) if kind == "door" else (120, 255, 120))
    for s, kind in L.OPAQUE:
        poly(G.shape(s), fill=(60, 45, 35), outline=(0, 0, 0))
    for s, kind in L.GLASS:
        poly(G.shape(s), fill=(160, 200, 230, 120), outline=(200, 230, 255))
    try:
        f = ImageFont.truetype("arialbd.ttf", 15)
    except OSError:
        f = ImageFont.load_default()
    for key, (name, sysn, g) in rooms.items():
        c = g.representative_point()
        d.text(Pt(c.x, c.y), f"{name}\n({sysn})", font=f, fill=(255, 255, 255), anchor="mm", align="center")
    for k, p in L.FIXED.items():
        d.ellipse([Pt(*p)[0] - 6, Pt(*p)[1] - 6, Pt(*p)[0] + 6, Pt(*p)[1] + 6], fill=(230, 60, 40))
    for vid, p in L.VENTS.items():
        d.rectangle([Pt(*p)[0] - 7, Pt(*p)[1] - 5, Pt(*p)[0] + 7, Pt(*p)[1] + 5], fill=(170, 110, 255))
        d.text((Pt(*p)[0], Pt(*p)[1] - 12), str(vid), font=f, fill=(220, 190, 255), anchor="mm")
    for p in L.CAMERAS:
        d.ellipse([Pt(*p)[0] - 5, Pt(*p)[1] - 5, Pt(*p)[0] + 5, Pt(*p)[1] + 5], fill=(255, 255, 255))
    for p, col in ((L.SPAWN, (255, 220, 0)), (L.EMERGENCY, (255, 0, 0)), (L.ADMIN_TABLE, (0, 200, 255)),
                   (L.SURVEILLANCE, (0, 200, 255))):
        d.ellipse([Pt(*p)[0] - 7, Pt(*p)[1] - 7, Pt(*p)[0] + 7, Pt(*p)[1] + 7], outline=col, width=3)
    img.save(OUT / "plan.png")
    print(OUT / "plan.png", img.size)


if __name__ == "__main__":
    main()
