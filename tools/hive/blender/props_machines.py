# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_machines.py - Amberhive-Objekte mit Mechanik und Aussenposten (Neubau V2-D, 15.11.2026): Blasebalg, Wachskessel,
# Nektarpresse, Tanzbuehne, Periskop, Teleskop, Sonnenuhr, Zielscheibe, Pollenkanone, Blumentreppe, Drohnen-Landeplatz.
#   blender -b --factory-startup -P props_machines.py -- [art ...]
# Animationen (Bildzahl aus art_props.json, Schleifen nahtlos):
#   bellows_big 6: vier Bilder aufziehen, zwei Bilder ausblasen; Wippbalken, Kette, Gegengewicht, Windbaender und Luftstoss.
#   wax_cauldron 4: Blasen wachsen und platzen versetzt, Flammen in der Feuertuer, Dampf und Rauch steigen.
#   nectar_press 6: Handrad dreht 15 Grad je Bild (vier Speichen), Gewinde wandert, Nektar tropft in den Trog.
#   dance_floor 4: Lichtring laeuft ueber die Glaswaben nach aussen, Lauflicht auf der Tanzfigur und am Rand.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from props_common import *  # noqa: E402,F401,F403
import hive_style as S  # noqa: E402
from mathutils import Vector  # noqa: E402

SQ3 = math.sqrt(3)


def trough(pts, z0, z1, wall, depth, mat, fill=None, fill_h=0.03):
    """Hohler Trog ueber einem Umriss: Wand, Innenboden um depth tiefer, optional gefuellt."""
    inner = inset(pts, wall)
    loft([[(x, y, z0) for x, y in pts], [(x, y, z1) for x, y in pts], [(x, y, z1) for x, y in inner],
          [(x, y, z1 - depth) for x, y in inner]], mat)
    if fill:
        return prism(inset(pts, wall + 0.002), z1 - depth, z1 - depth + fill_h, fill)


def pot(x, y, z, r, h, mat="terracotta", rim="terracotta_dark", soil=True):
    """Tontopf mit Wulstrand und Erde."""
    lathe([(0, 0), (r * 0.68, 0), (r * 0.95, h * 0.78), (r * 1.12, h * 0.8), (r * 1.12, h), (r * 0.9, h), (0, h * 0.94)],
          [mat, rim, "propolis"], M=T(x, y, z), seg=16, band=[0, 0, 1, 1, 1, 2 if soil else 0])


# ------------------------------------------------------------------ Bellows

def bellows_big(f, n):
    cy = 0.5
    t = f / n
    if t < 2 / 3 - 1e-9:                        # vier Bilder aufziehen, zwei Bilder ausblasen
        u = t / (2 / 3)
        p = u * u * (3 - 2 * u)
    else:
        v = (t - 2 / 3) * 3
        p = 1 - v * v * (3 - 2 * v)
    wind = (0.85, 0.4, 0.12, 0.0, 0.0, 1.0)[f % 6] if n == 6 else (1.0 if t >= 2 / 3 else 0.0)
    a = 3.5 + 14.5 * p
    # Schlitten: zwei Laengskufen, drei Querriegel mit durchgesteckten Zapfen
    for y0, y1 in ((0.04, 0.19), (0.81, 0.96)):
        bbox(-1.08, y0, 0.0, 1.08, y1, 0.13, "paint_teal_dark", r=0.02, seg=1)
    for x in (-0.82, -0.12, 0.6):
        bbox(x - 0.07, 0.02, 0.06, x + 0.07, 0.98, 0.18, "paint_teal", r=0.015, seg=1)
        box(x - 0.03, 0.008, 0.09, x + 0.03, 0.02, 0.15, "wood_light")
    for x in (-0.5, 0.26):
        box(x - 0.06, 0.24, 0.18, x + 0.06, 0.76, 0.38, "wood_dark")
    xh, zb, L = 0.58, 0.45, 1.5

    def plan(sc=1.0):
        pts = []
        for i in range(19):
            d = L * i / 18
            if d <= 1.08:
                w = 0.11 + 0.28 * math.sin(math.pi / 2 * d / 1.08) ** 1.15
            else:
                w = 0.39 * math.sqrt(max(0.0, 1 - ((d - 1.08) / (L - 1.08)) ** 2))
            pts.append((d, w))
        right = [(xh - d * sc, cy - w * sc) for d, w in pts]
        left = [(xh - d * sc, cy + w * sc) for d, w in reversed(pts)]
        return right + left[1:-1]

    hinge = about(R("Y", a), (xh, 0, zb))
    slab(plan(), zb - 0.075, zb, "wood", bev=0.014)
    # Lederbalg in Falten: aussen breite Rippen, innen tiefe Falten
    m = 8
    loops = []
    for k in range(m + 1):
        sc = 0.985 if k % 2 == 0 else 0.86
        Mk = about(R("Y", a * k / m), (xh, 0, zb))
        loops.append([tuple(Mk @ Vector((x, y, zb))) for x, y in plan(sc)])
    loft(loops, ["leather", "leather_dark"], band=[(i // 1) % 2 for i in range(m)])
    # Deckbrett mit Messingventil, Nagelreihe, Griffklotz
    with xf(hinge):
        slab(plan(), zb, zb + 0.075, "wood", bev=0.014)
        slab(inset(plan(), 0.09), zb + 0.075, zb + 0.09, "wood_light", bev=0.008)
        hexp(xh - 0.82, cy, 0.17, zb + 0.09, zb + 0.105, "brass")
        hexp(xh - 0.82, cy, 0.11, zb + 0.105, zb + 0.115, "soot")
        for i in range(3):
            box(xh - 0.9, cy - 0.06 + i * 0.05, zb + 0.115, xh - 0.74, cy - 0.04 + i * 0.05, zb + 0.122, "brass")
        for px, py in inset(plan(), 0.045)[::2]:
            stud(px, py, zb + 0.075, 0.017, "brass", "t")
        bbox(xh - 1.5, cy - 0.13, zb + 0.075, xh - 1.36, cy + 0.13, zb + 0.14, "wood_dark", r=0.015, seg=1)
        tor(xh - 1.43, cy, zb + 0.19, 0.055, 0.016, "iron", seg=12, ring=5, M=R("X", 90))
    att = hinge @ Vector((xh - 1.43, cy, zb + 0.24))
    # Scharnierklotz, Messingduese
    bbox(xh - 0.05, cy - 0.17, zb - 0.075, xh + 0.1, cy + 0.17, zb + 0.1, "wood_dark", r=0.02, seg=1)
    for sy in (-1, 1):
        stud(xh + 0.03, cy + sy * 0.12, zb + 0.1, 0.022, "brass", "t")
    lathe([(0, 0), (0.085, 0), (0.07, 0.06), (0.045, 0.3), (0.06, 0.34), (0.06, 0.37), (0.04, 0.37), (0, 0.35)],
          ["brass", "brass_dark", "soot"], M=T(xh + 0.1, cy, zb + 0.01) @ R("Y", 90), seg=14, band=[0, 0, 0, 1, 1, 1, 2])
    tip = (xh + 0.47, cy, zb + 0.01)
    # Windbaender an der Duese: haengen in Ruhe, stehen beim Ausblasen waagerecht
    for i, (dy, c) in enumerate(((-0.05, "coral"), (0.0, "paint_cream"), (0.05, "coral"))):
        ang = math.radians(-78 + 80 * wind + (6 * math.sin(2 * math.pi * (t + i / 3))))
        path = []
        for j in range(6):
            s = 0.045 * j
            wob = 0.018 * math.sin(j * 1.3 + 2 * math.pi * t * 2 + i) * (0.3 + wind)
            path.append((tip[0] + math.cos(ang) * s - math.sin(ang) * wob, tip[1] + dy * (1 + 0.25 * j),
                         tip[2] + 0.04 + math.sin(ang) * s + math.cos(ang) * wob))
        sweep(path, [0.016, 0.02, 0.02, 0.018, 0.015, 0.008], c, seg=6)
    if wind > 0.3:                              # Luftstoss
        drift = 0.05 * (1.0 - wind) / 0.6      # der Stoss wandert ein Stueck und loest sich auf
        for j, (dx, r0) in enumerate(((0.08, 0.04), (0.16, 0.055), (0.25, 0.04))):
            puff(tip[0] + dx + drift, cy + 0.03 * (j - 1), tip[2] + 0.02 + 0.05 * j * (1 - wind), r0 * (0.35 + 0.75 * wind))
    # Galgen: zwei Pfosten mit Kopfbaendern, Achse, Wippbalken mit Kette und Gegengewicht
    px, pz = -0.12, 1.26
    for y in (0.115, 0.885):
        box(px - 0.055, y - 0.055, 0.13, px + 0.055, y + 0.055, pz + 0.1, "paint_teal")
        ext([(px - 0.42, 0.13), (px - 0.3, 0.13), (px - 0.055, 0.5), (px - 0.055, 0.66)], y - 0.035, y + 0.035, "paint_teal_dark")
        ext([(px + 0.42, 0.13), (px + 0.3, 0.13), (px + 0.055, 0.5), (px + 0.055, 0.66)], y - 0.035, y + 0.035, "paint_teal_dark")
        lathe([(0.05, 0), (0.07, 0.03), (0.04, 0.07), (0, 0.09)], "brass", M=T(px, y, pz + 0.1), seg=10)
    tube((px, 0.06, pz), (px, 0.94, pz), 0.032, "iron", seg=10)
    la, lb, ch = 0.8, 0.58, 0.3
    th = math.degrees(math.asin(max(-0.9, min(0.9, (pz - (att.z + ch)) / la))))
    lever = about(R("Y", -th), (px, cy, pz))
    with xf(lever):
        bbox(px - la - 0.06, cy - 0.05, pz - 0.045, px + lb + 0.06, cy + 0.05, pz + 0.045, "wood", r=0.015, seg=1)
        for x in (px - la, px, px + lb):
            box(x - 0.035, cy - 0.056, pz - 0.05, x + 0.035, cy + 0.056, pz + 0.05, "iron")
        disc_y(px, cy - 0.075, pz, 0.05, 0.02, "brass", seg=10)
    pl = lever @ Vector((px - la, cy, pz - 0.05))
    pr = lever @ Vector((px + lb, cy, pz - 0.05))
    chain((pl.x, cy, pl.z), (att.x, cy, att.z - 0.03), 0.026, "iron")
    chain((pr.x, cy, pr.z), (pr.x, cy, pr.z - 0.2), 0.026, "iron")
    lathe([(0, 0), (0.1, 0), (0.12, 0.05), (0.12, 0.2), (0.07, 0.26), (0.03, 0.27), (0, 0.27)], ["stone_dark", "iron"],
          M=T(pr.x, cy, pr.z - 0.47), seg=6, band=[0, 0, 0, 0, 1, 1])


# ------------------------------------------------------------------ Wax Foundry

def wax_cauldron(f, n):
    cx, cy = 0.0, 0.75
    t = f / n
    # gemauerter Feuerring: zwei versetzte Steinlagen, Abdeckring
    for i, (z0, z1) in enumerate(((0.0, 0.2), (0.2, 0.4))):
        lathe([(0.42, z0), (0.69 - 0.01 * i, z0), (0.69 - 0.01 * i, z1), (0.42, z1)], ["stone", "stone_dark"],
              M=T(cx, cy, 0) @ R("Z", 12.86 * i + 6), seg=14, band=[0, 0, 0, 0], stripe=(0, 1), loop=True)
    lathe([(0.44, 0.4), (0.7, 0.4), (0.7, 0.45), (0.66, 0.47), (0.44, 0.47)], "stone_dark", M=T(cx, cy, 0), seg=28, loop=True)
    # Feuertuer im Sueden: Eisenbogen, Glut, zuengelnde Flammen
    yd = cy - 0.7
    ext([(-0.26, 0.0)] + arc(0, 0.16, 0.26, 180, 0, 10, rz=0.2) + [(0.26, 0.0)], yd - 0.02, yd + 0.1, "iron")
    flat(ext([(-0.19, 0.0)] + arc(0, 0.15, 0.19, 180, 0, 10, rz=0.15) + [(0.19, 0.0)], yd - 0.026, yd - 0.02, "void"))
    for sx in (-1, 1):
        stud(sx * 0.225, yd - 0.02, 0.06, 0.016, "iron_light")
        stud(sx * 0.2, yd - 0.02, 0.24, 0.016, "iron_light")
    for i, (dx, h0) in enumerate(((-0.11, 0.2), (0.0, 0.27), (0.11, 0.21), (-0.05, 0.15), (0.06, 0.16))):
        h = h0 * (0.82 + 0.3 * (0.5 + 0.5 * math.sin(2 * math.pi * (t + i * 0.37))))
        sway = 0.025 * math.sin(2 * math.pi * (t + i * 0.21))
        for k, (mat, sc) in enumerate((("red", 1.0), ("flame", 0.72), ("flame_core", 0.42))):
            w = 0.055 * sc
            sh = [(dx - w, 0.0), (dx + w, 0.0), (dx + w * 0.9 + sway * 0.4, h * sc * 0.45), (dx + sway, h * sc),
                  (dx - w * 0.9 + sway * 0.4, h * sc * 0.45)]
            flat(noline(ext(sh, yd - 0.03 - 0.003 * k - 0.001 * i, yd - 0.027 - 0.003 * k - 0.001 * i, mat)))
    glow(cx, yd - 0.1, 0.1, 0.5, "flame", 0.4 + 0.08 * math.sin(2 * math.pi * t))
    for i, (x, y) in enumerate(((-0.1, yd - 0.12), (0.07, yd - 0.16), (0.16, yd - 0.09))):
        flat(noline(sph(x, y, 0.012, 0.018, ("flame", "flame_core", "ember")[(i + f) % 3], seg=6, sz=0.5)))
    # Kupferkessel im Ring: Bauch, Messingband mit Nieten, gerollter Rand, Tragringe
    prof = [(0, 0.3), (0.3, 0.3), (0.5, 0.4), (0.6, 0.55), (0.62, 0.66), (0.62, 0.72), (0.585, 0.88), (0.555, 0.95), (0.6, 0.97),
            (0.61, 1.0), (0.57, 1.015), (0.53, 0.99), (0.53, 0.95), (0, 0.95)]
    lathe(prof, ["copper", "brass_dark", "brass", "wax_light", "copper_dark"], M=T(cx, cy, 0), seg=32,
          band=[0, 0, 0, 0, 1, 0, 0, 2, 2, 2, 2, 4, 3])
    for i in range(14):
        a = math.radians(193 + i * 11.8)
        stud(cx + math.cos(a) * 0.625, cy + math.sin(a) * 0.625, 0.69, 0.016, "brass")
    for sg in (-1, 1):
        box(cx + sg * 0.59, cy - 0.04, 0.82, cx + sg * 0.67, cy + 0.04, 0.88, "brass_dark")
        tor(cx + sg * 0.67, cy, 0.76, 0.085, 0.02, "iron", seg=16, ring=6, M=R("X", 90))
    # Wachsspiegel: Ruehrspur, heller Kern, Tropfnasen ueber den Rand
    zs = 0.95
    noline(tor(cx - 0.03, cy + 0.02, zs, 0.33, 0.012, "wax", seg=32, ring=5))
    noline(cyl(cx - 0.1, cy + 0.06, zs, zs + 0.004, 0.2, "glow_hot", seg=24))
    for a, Ld in ((252, 0.14), (281, 0.24), (300, 0.1), (232, 0.08)):
        r = math.radians(a)
        x, y = cx + math.cos(r) * 0.6, cy + math.sin(r) * 0.6
        drip(x, y - 0.01, 0.99, Ld, 0.026, "wax_light")
    # Blasen: wachsen in drei Schritten, das vierte Bild platzt (Ring und Spritzer); jede Blase versetzt
    for i, (bx, by) in enumerate(((-0.24, 0.02), (0.16, 0.2), (0.1, -0.22), (-0.06, 0.3), (0.3, -0.02), (-0.2, -0.24))):
        ph = (f + i * 3) % n if n == 4 else (f + i) % 4
        x, y = cx + bx, cy + by
        if ph == 3:
            noline(tor(x, y, zs + 0.004, 0.085, 0.012, "wax", seg=14, ring=5))
            for k in range(3):
                a = math.radians(40 + 120 * k + 30 * i)
                sph(x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, zs + 0.07 + 0.02 * k, 0.018, "wax_light", seg=6)
        else:
            r = (0.04, 0.065, 0.09)[ph]
            sph(x, y, zs, r, "wax", seg=14, sz=0.85)
            flat(noline(sph(x - r * 0.35, y - r * 0.25, zs + r * 0.6, r * 0.26, "white", seg=6)))
    # Ruehrholz lehnt im Kessel
    tube((cx + 0.18, cy + 0.1, zs), (cx + 0.5, cy + 0.34, 1.42), 0.028, "wood_light", seg=8)
    sph(cx + 0.5, cy + 0.34, 1.43, 0.045, "wood_dark", seg=10)
    # Dampf ueber dem Wachs (steigt, waechst, vergeht)
    for c, (sx, sy) in enumerate(((-0.14, 0.12), (0.2, -0.02))):
        for k in range(2):
            q = ((k + t + 0.25 * c) / 2) % 1.0
            puff(cx + sx + 0.05 * math.sin(2 * math.pi * q + c), cy + sy, 1.05 + 0.42 * q, 0.075 * math.sin(math.pi * q) ** 0.8)
    # Rauchrohr hinten mit Hut, Rauch
    tube((cx, cy + 0.6, 0.3), (cx, cy + 0.6, 1.18), 0.075, "copper", seg=14)
    for z in (0.62, 1.1):
        hoop(cx, cy + 0.6, z, 0.078, "copper_dark", hh=0.05, t=0.012, seg=14)
    lathe([(0.14, 0), (0.05, 0.1), (0, 0.11)], "copper_dark", M=T(cx, cy + 0.6, 1.24), seg=12)
    for k in range(2):
        q = ((k + t) / 2) % 1.0
        puff(cx + 0.03 + 0.12 * q, cy + 0.6, 1.36 + 0.3 * q, 0.07 * math.sin(math.pi * q) ** 0.8, "paint_cream_dark")
    # Scheite vor dem Ofen
    for (x0, y0, x1, y1, z) in ((0.36, 0.1, 0.66, 0.26, 0.055), (0.3, 0.2, 0.62, 0.3, 0.055), (0.38, 0.16, 0.64, 0.3, 0.15)):
        tube((x0, y0, z), (x1, y1, z), 0.055, "wood", seg=8)
        d = Vector((x1 - x0, y1 - y0, 0)).normalized()
        lathe([(0, 0), (0.05, 0), (0, 0.004)], "wood_light", M=T(x0, y0, z) @ aim(-d) @ T(0, 0, 0.001), seg=8)


# ------------------------------------------------------------------ Waggle Studio

def dance_floor(f, n):
    cx, cy = 0.0, 0.9
    sy = 0.9 / (1.4 * math.sin(math.pi / 3))

    def sq(pts):
        return [(x, cy + (y - cy) * sy) for x, y in pts]
    prism(sq(S.hexagon_pts(cx, cy, 1.4)), 0.0, 0.02, "paint_teal_dark")
    prism(sq(S.hexagon_pts(cx, cy, 1.31)), 0.02, 0.027, "brass")
    prism(sq(S.hexagon_pts(cx, cy, 1.25)), 0.027, 0.032, "teal_dark")
    # Glaswaben: Lichtring wandert von der Mitte nach aussen (Ring = Abstand in Waben)
    rr = 0.148
    Rin = 1.25 - rr * 0.95
    for q in range(-7, 8):
        for r in range(-7, 8):
            u, v = 1.5 * rr * q, SQ3 * rr * (r + q / 2)
            if abs(v) > Rin * math.sin(math.pi / 3) + 1e-6 or abs(u) + abs(v) / SQ3 > Rin + 1e-6:
                continue
            ring = max(abs(q), abs(r), abs(q + r))
            lvl = (ring - f) % n
            pts = sq(S.hexagon_pts(cx + u, cy + v, rr * 0.87))
            if ring == 0:
                continue
            if lvl == 0:
                flat(prism(pts, 0.032, 0.04, "glow_hot"))
                glow(cx + u, cy + v * sy, 0.045, 0.18, "glow", 0.18)
            elif lvl == 1:
                flat(prism(pts, 0.032, 0.04, "honey_light"))
            else:
                prism(pts, 0.032, 0.04, "paint_cream" if (q - r) % 3 else "teal_light")
    # Mitte: Messingwabe mit Honigkern
    prism(sq(S.hexagon_pts(cx, cy, rr * 0.95)), 0.032, 0.044, "brass")
    flat(prism(sq(S.hexagon_pts(cx, cy, rr * 0.6)), 0.044, 0.048, "glow_hot" if f % 2 == 0 else "honey"))
    # Schwaenzeltanz-Figur als Lauflicht: Mittellauf, dann abwechselnd linker und rechter Bogen
    path = [(-0.66 + 1.32 * i / 8, 0.0) for i in range(9)]
    path += [(0.66 * math.cos(math.pi * i / 10), 0.6 * math.sin(math.pi * i / 10)) for i in range(1, 10)]
    path += [(0.66 * math.cos(math.pi * i / 10), -0.6 * math.sin(math.pi * i / 10)) for i in range(1, 10)]
    for k, (u, v) in enumerate(path):
        ph = (k - f) % n if k < 9 else (k - 9 - f) % n
        x, y = cx + u, cy + v * sy
        if ph == 0:
            flat(cyl(x, y, 0.04, 0.052, 0.05, "glow_hot", seg=12))
            glow(x, y, 0.06, 0.16, "glow", 0.5)
        else:
            flat(noline(cyl(x, y, 0.04, 0.046, 0.03, "brass" if ph == 1 else "brass_dark", seg=10)))
    # Randlichter, laufen gegenlaeufig
    for i in range(24):
        a = 2 * math.pi * i / 24
        rad = 1.355 * math.cos(math.pi / 6) / math.cos((a % (math.pi / 3)) - math.pi / 6)
        x, y = cx + math.cos(a) * rad, cy + math.sin(a) * rad * sy
        on = (i + f) % n == 0
        if on:
            glow(x, y, 0.04, 0.12, "glow", 0.5)
        flat(cyl(x, y, 0.02, 0.036, 0.036, "glow_hot" if on else "honey_deep", seg=10))


def flower_pots(f, n):
    # Blumentreppe: zwei Wangen, drei Stufenbretter, Lattenrueckwand je Stufe
    steps = ((0.02, 0.35, 0.16), (0.35, 0.67, 0.4), (0.67, 0.99, 0.64))
    for sx in (-1, 1):
        x0, x1 = (-0.25, -0.215) if sx < 0 else (0.215, 0.25)
        ext([(0.03, 0.0), (0.98, 0.0), (0.98, 0.7), (0.88, 0.7), (0.1, 0.14), (0.03, 0.14)], x0, x1, "paint_cream", axis="x")
    zp = 0.0
    for y0, y1, z in steps:
        slab(rrect(-0.25, y0, 0.25, y1, 0.03), z - 0.035, z, "paint_mint", bev=0.01)
        box(-0.2, y0 + 0.01, zp, 0.2, y0 + 0.03, z - 0.035, "paint_cream_dark")
        for x in (-0.12, 0.0, 0.12):
            box(x - 0.045, y0 + 0.004, zp + 0.01, x + 0.045, y0 + 0.012, z - 0.04, "paint_cream")
        zp = z
    # unten: Duftproben im Staender, kleine Giesskanne
    z = 0.16
    bbox(-0.2, 0.06, z, 0.03, 0.17, z + 0.05, "wood", r=0.01, seg=1)
    for i, c in enumerate(("petal_pink", "petal_blue", "pollen", "royal_light")):
        x = -0.17 + i * 0.057
        tube((x, 0.115, z + 0.03), (x, 0.115, z + 0.19), 0.022, "glass", seg=8)
        tube((x, 0.115, z + 0.03), (x, 0.115, z + 0.13), 0.023, c, seg=8)
        cyl(x, 0.115, z + 0.19, z + 0.22, 0.02, "wood_light", seg=8)
    lathe([(0, 0), (0.06, 0), (0.07, 0.1), (0.05, 0.11), (0, 0.11)], "verdigris", M=T(0.14, 0.2, z), seg=12)
    tube((0.18, 0.2, z + 0.04), (0.25, 0.14, z + 0.14), 0.014, "verdigris", seg=6)
    tor(0.1, 0.24, z + 0.07, 0.04, 0.01, "verdigris", seg=10, ring=5, M=R("X", 90) @ R("Y", 40))
    # Mitte: Lavendel und Margeriten
    z = 0.4
    pot(-0.12, 0.5, z, 0.085, 0.15)
    for i, (dx, dy, hh) in enumerate(((-0.04, 0.0, 0.3), (0.03, 0.02, 0.36), (0.0, -0.03, 0.26), (0.05, -0.02, 0.3))):
        tube((-0.12 + dx * 0.5, 0.5 + dy, z + 0.14), (-0.12 + dx * 1.6, 0.5 + dy, z + 0.14 + hh * 0.6), 0.008, "leaf_dark", seg=5)
        lathe([(0, 0), (0.026, 0.02), (0.022, 0.1), (0, 0.14)], "royal_light", M=T(-0.12 + dx * 1.6, 0.5 + dy, z + 0.14 + hh * 0.55), seg=8)
    pot(0.12, 0.5, z, 0.08, 0.14, mat="paint_cream", rim="paint_mint_dark")
    flower(0.09, 0.5, z + 0.13, s=0.9, petal="petal_white", stem=0.18)
    flower(0.16, 0.53, z + 0.13, s=0.8, petal="petal_white", stem=0.27)
    # oben: Sonnenblume im grossen Topf, Tulpe daneben
    z = 0.64
    pot(-0.02, 0.83, z, 0.12, 0.18)
    top = z + 0.5
    tube((-0.02, 0.83, z + 0.16), (-0.02, 0.83, top), 0.017, "leaf_dark", seg=8)
    for sg in (-1, 1):
        sph(-0.02 + sg * 0.085, 0.83, z + 0.3 + 0.04 * sg, 0.075, "leaf", seg=10, sy=0.5, sz=0.4)
    for i in range(12):
        a = 2 * math.pi * i / 12
        sph(-0.02 + math.cos(a) * 0.1, 0.83 + math.sin(a) * 0.1, top, 0.055, "pollen", seg=8, sz=0.35)
    sph(-0.02, 0.83, top + 0.015, 0.075, "propolis_light", seg=14, sz=0.45)
    tube((0.17, 0.9, z), (0.17, 0.9, z + 0.3), 0.01, "leaf_dark", seg=5)
    lathe([(0, 0), (0.04, 0.03), (0.045, 0.08), (0.03, 0.11), (0, 0.1)], "petal_pink", M=T(0.17, 0.9, z + 0.28), seg=8)
    pot(0.17, 0.9, z, 0.055, 0.09)
    # Duftfahne: zwei Bluetenblaetter in der Luft
    sph(0.14, 0.72, top + 0.13, 0.026, "petal_pink", seg=8, sz=0.6)
    sph(0.2, 0.6, top + 0.02, 0.022, "petal_white", seg=8, sz=0.6)


# ------------------------------------------------------------------ Guard Comb / Sun Deck

def periscope(f, n):
    cx, cy = 0.0, 0.32
    slab(S.hexagon_pts(cx, cy, 0.3), 0.0, 0.055, "stone_dark", bev=0.012)
    cyl(cx, cy, 0.055, 0.1, 0.2, "brass_dark", seg=24)
    for i in range(6):
        a = math.pi / 3 * i + 0.3
        stud(cx + math.cos(a) * 0.16, cy + math.sin(a) * 0.16, 0.1, 0.024, "brass", "t")
    # gestrichenes Standrohr, Messingrohr mit Bunden, Deckenmanschette
    lathe([(0, 0.1), (0.13, 0.1), (0.115, 0.16), (0.105, 0.72), (0.12, 0.74), (0.12, 0.8), (0, 0.8)], "paint_teal", M=T(cx, cy, 0),
          seg=20)
    cyl(cx, cy, 0.8, 1.86, 0.075, "brass", seg=20)
    for z in (0.74, 1.0, 1.46):
        hoop(cx, cy, z + 0.03, 0.09 if z > 0.8 else 0.125, "brass_dark", hh=0.06, t=0.014, seg=20)
    lathe([(0.075, 0), (0.15, 0.07), (0.15, 0.11), (0.1, 0.11), (0, 0.1)], ["brass_dark", "soot"], M=T(cx, cy, 1.84), seg=20,
          band=[0, 0, 0, 1])
    # Sichtkopf mit Okular nach Sueden, zwei Klappgriffe
    bbox(cx - 0.135, cy - 0.17, 1.04, cx + 0.135, cy + 0.09, 1.31, "brass", r=0.035, seg=2)
    box(cx - 0.14, cy - 0.175, 1.16, cx + 0.14, cy + 0.095, 1.19, "brass_dark")
    tube((cx, cy - 0.16, 1.17), (cx, 0.03, 1.17), 0.055, "brass_dark", seg=16)
    disc_y(cx, -0.005, 1.17, 0.07, 0.04, "soot", seg=16)
    flat(disc_y(cx, -0.012, 1.17, 0.04, 0.008, "glass", seg=12))
    for sg in (-1, 1):
        tube((cx + sg * 0.12, cy - 0.04, 1.1), (cx + sg * 0.26, cy - 0.04, 1.02), 0.018, "brass_dark", seg=8)
        tube((cx + sg * 0.21, cy - 0.04, 1.05), (cx + sg * 0.33, cy - 0.04, 0.98), 0.036, "wood_dark", seg=10)
    # Druckuhr, Stellrad, Trittstufe
    disc_y(cx, cy - 0.15, 0.5, 0.08, 0.05, "brass", seg=20)
    disc_y(cx, cy - 0.156, 0.5, 0.06, 0.008, "paper", seg=20)
    ext([(cx - 0.008, 0.495), (cx + 0.045, 0.535), (cx + 0.008, 0.49)], cy - 0.162, cy - 0.156, "red")
    tor(cx + 0.14, cy - 0.07, 0.3, 0.06, 0.016, "red", seg=14, ring=5, M=R("X", 90) @ R("Y", 35))
    bbox(-0.31, 0.01, 0.0, -0.07, 0.2, 0.12, "paint_teal_dark", r=0.02, seg=1)
    box(-0.32, 0.0, 0.12, -0.06, 0.21, 0.15, "wood")


def telescope(f, n):
    cx, cy = 0.0, 0.45
    apex = Vector((cx, cy, 0.96))
    # Holzdreibein mit Messingschuhen und Gelenken, Ablage mit Okularen
    for a in (210, 330, 90):
        r = math.radians(a)
        foot = Vector((cx + math.cos(r) * 0.42, cy + math.sin(r) * 0.42, 0.0))
        tube(tuple(apex), tuple(foot), 0.03, "wood", seg=10, r1=0.036)
        tube(tuple(foot.lerp(apex, 0.12)), tuple(foot), 0.04, "brass_dark", seg=10, r1=0.02)
        mid = apex.lerp(foot, 0.5)
        hoop(0, 0, 0, 0.04, "brass", hh=0.05, t=0.012, M=T(*mid) @ aim(foot - apex), seg=10)
    prism([(cx + math.cos(math.radians(a)) * 0.2, cy + math.sin(math.radians(a)) * 0.2) for a in (210, 330, 90)], 0.44, 0.47, "wood_dark")
    for dx, c in ((-0.05, "brass"), (0.04, "brass_dark")):
        cyl(cx + dx, cy - 0.03, 0.47, 0.54, 0.028, c, seg=8)
    cyl(cx, cy, 0.93, 1.02, 0.085, "brass", seg=16)
    # Gabelmontierung
    for sg in (-1, 1):
        box(cx + sg * 0.12 - 0.02, cy - 0.04, 1.02, cx + sg * 0.12 + 0.02, cy + 0.04, 1.24, "brass_dark")
    box(cx - 0.14, cy - 0.05, 1.0, cx + 0.14, cy + 0.05, 1.05, "brass_dark")
    yaw, el = math.radians(-24), math.radians(36)
    d = Vector((math.sin(yaw) * math.cos(el), math.cos(yaw) * math.cos(el), math.sin(el)))
    pv = Vector((cx, cy, 1.2))
    Mt = T(*pv) @ aim(d)
    # Rohr: Okularauszug, Hauptrohr mit Bunden, Taukappe, Linse
    prof = [(0, -0.6), (0.04, -0.6), (0.04, -0.54), (0.03, -0.54), (0.03, -0.42), (0.055, -0.42), (0.055, -0.32), (0.085, -0.3),
            (0.092, 0.36), (0.11, 0.36), (0.115, 0.6), (0.095, 0.6), (0.095, 0.57), (0, 0.57)]
    lathe(prof, ["soot", "brass_dark", "brass", "glass"], M=Mt, seg=20, band=[0, 0, 0, 1, 1, 1, 1, 2, 1, 1, 1, 1, 3])
    for tt in (-0.26, 0.02, 0.3):
        hoop(0, 0, tt, 0.092, "brass_dark", hh=0.045, t=0.012, M=Mt, seg=20)
    # Sucher und Fokusknopf
    side = d.cross(Vector((0, 0, 1))).normalized()
    upv = side.cross(d).normalized()
    q0, q1 = pv + d * -0.1 + upv * 0.13, pv + d * 0.26 + upv * 0.13
    tube(tuple(q0), tuple(q1), 0.028, "brass", seg=10)
    tube(tuple(q1), tuple(q1 + d * 0.015), 0.022, "glass", seg=8)
    for tt in (-0.02, 0.18):
        tube(tuple(pv + d * tt + upv * 0.08), tuple(pv + d * tt + upv * 0.13), 0.012, "brass_dark", seg=6)
    kn = pv + d * -0.36 - side * 0.07
    sph(kn.x, kn.y, kn.z, 0.03, "wood_dark", seg=8)
    # Sternkarte lehnt am Bein
    with xf(about(R("X", -62), (cx + 0.26, 0.12, 0.0))):
        tube((cx + 0.14, 0.12, 0.045), (cx + 0.42, 0.12, 0.045), 0.042, "paper", seg=12)
        hoop(0, 0, 0.14, 0.044, "royal", hh=0.03, t=0.006, M=T(cx + 0.14, 0.12, 0.045) @ R("Y", 90), seg=12)


def sundial(f, n):
    cx, cy = 0.0, 0.7
    # Steinsockel in zwei Stufen, Baluster, Tisch mit Messingreif
    slab(S.hexagon_pts(cx, cy, 0.7), 0.0, 0.09, "stone_dark", bev=0.018)
    slab(S.hexagon_pts(cx, cy, 0.54), 0.09, 0.17, "stone", bev=0.018)
    for px, py in S.hexagon_pts(cx, cy, 0.61):
        stud(px, py, 0.09, 0.03, "brass", "t")
    lathe([(0, 0.17), (0.3, 0.17), (0.28, 0.23), (0.17, 0.3), (0.13, 0.42), (0.17, 0.56), (0.13, 0.62), (0.2, 0.68), (0.36, 0.73),
           (0.38, 0.77), (0, 0.77)], "stone", M=T(cx, cy, 0), seg=20)
    hoop(cx, cy, 0.62, 0.135, "brass", hh=0.035, t=0.01, seg=20)
    cyl(cx, cy, 0.77, 0.83, 0.62, "stone", seg=40)
    hoop(cx, cy, 0.8, 0.622, "brass", hh=0.04, t=0.01, seg=40)
    zt = 0.83
    cyl(cx, cy, zt, zt + 0.006, 0.57, "paint_cream", seg=40)
    # Stundenring aus Messing mit Marken, Strahlenkranz, Sonnenscheibe
    lathe([(0.43, 0), (0.54, 0), (0.54, 0.007), (0.43, 0.007)], "brass", M=T(cx, cy, zt + 0.006), seg=40, loop=True)
    for i in range(12):
        a = 2 * math.pi * i / 12
        big = i % 3 == 0
        r0, w = (0.445, 0.02) if big else (0.47, 0.011)
        c, s = math.cos(a), math.sin(a)
        prism([(cx + c * r0 - s * w, cy + s * r0 + c * w), (cx + c * r0 + s * w, cy + s * r0 - c * w),
               (cx + c * 0.53 + s * w, cy + s * 0.53 - c * w), (cx + c * 0.53 - s * w, cy + s * 0.53 + c * w)], zt + 0.013, zt + 0.017,
              "propolis")
    star = []
    for i in range(32):
        a = math.pi / 2 + 2 * math.pi * i / 32
        r = (0.4 if i % 8 == 0 else 0.3) if i % 4 == 0 else (0.23 if i % 2 == 0 else 0.12)
        star.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    prism(star, zt + 0.006, zt + 0.012, "honey")
    cyl(cx, cy, zt + 0.012, zt + 0.02, 0.1, "brass", seg=20)
    # Zeiger: Messingschwinge, nach Nordwesten gedreht, damit die helle Flanke zu sehen ist; Schatten faellt nach Osten
    noline(prism([(cx + 0.0, cy - 0.02), (cx + 0.5, cy + 0.2), (cx + 0.47, cy + 0.27), (cx - 0.01, cy + 0.03)], zt + 0.012, zt + 0.015,
                 "paint_cream_dark"))
    with xf(about(R("Z", 38), (cx, cy, 0.0))):
        ext([(cy - 0.14, zt + 0.012), (cy + 0.44, zt + 0.012), (cy + 0.46, zt + 0.44), (cy + 0.4, zt + 0.42), (cy + 0.3, zt + 0.2),
             (cy + 0.12, zt + 0.1)], cx - 0.022, cx + 0.022, "brass", axis="x")
        sph(cx, cy + 0.45, zt + 0.46, 0.04, "amber_glass", seg=10)
        sph(cx, cy - 0.14, zt + 0.03, 0.03, "brass_dark", seg=8)


# ------------------------------------------------------------------ Wasp Watch

def arrow(p0, dv, L=0.24, fl="red"):
    """Pfeil: steckt bei p0, Schaft zeigt entlang dv zurueck, zwei Federn am Ende."""
    p0, dv = Vector(p0), Vector(dv).normalized()
    p1 = p0 + dv * L
    tube(tuple(p0), tuple(p1), 0.011, "wood_light", seg=6)
    for sg in (-1, 1):
        ob = sph(0, 0, 0, 0.034, fl, seg=8, sx=0.4, sy=0.14, sz=1.5)
        ob.data.transform(T(*(p1 - dv * 0.035)) @ aim(dv) @ R("Z", 45 * sg + 45))


def target_board(f, n):
    # Staffelei: zwei Vorderbeine, Hinterbein, Auflageleiste, Messingkappe, Wimpel
    for sx in (-1, 1):
        tube((sx * 0.54, 0.17, 0.0), (sx * 0.14, 0.28, 1.36), 0.035, "paint_teal", seg=8)
        sph(sx * 0.54, 0.17, 0.02, 0.045, "paint_teal_dark", seg=8)
        box(sx * 0.4 - 0.03, 0.06, 0.27, sx * 0.4 + 0.03, 0.2, 0.31, "paint_teal_dark")
    bbox(-0.46, 0.015, 0.27, 0.46, 0.1, 0.33, "paint_teal_dark", r=0.012, seg=1)
    lathe([(0, 0), (0.07, 0), (0.075, 0.05), (0.03, 0.09), (0.03, 0.2), (0, 0.21)], "brass", M=T(0, 0.28, 1.32), seg=10)
    ext([(0.02, 1.53), (0.26, 1.47), (0.02, 1.41)], 0.27, 0.29, "red")
    # Strohscheibe, 9 Grad zurueckgelehnt vor den Beinen: gewickelter Rand, Ringe in Wespenfarben, rotes Zentrum
    zc = 0.84
    lean = about(R("X", -9), (0, 0.08, 0.33))
    with xf(lean):
        disc_y(0, 0.06, zc, 0.51, 0.1, "straw", seg=40)
        for r in (0.5, 0.43):
            tor(0, 0.06, zc, r, 0.022, "straw_dark", seg=40, ring=5, M=R("X", 90))
        rings = (("bee_yellow", 0.4), ("bee_black", 0.32), ("bee_yellow", 0.24), ("bee_black", 0.16), ("red", 0.085))
        for i, (c, r) in enumerate(rings):
            disc_y(0, 0.052 - i * 0.004, zc, r, 0.012, c, seg=36)
    for (dx, dz, yaw, pit, fl) in ((-0.03, 0.02, 20, 30, "red"), (0.2, -0.17, -15, 25, "cloth_white"), (-0.2, 0.25, 12, 40, "red")):
        p0 = lean @ Vector((dx, 0.03, zc + dz))
        dv = (math.sin(math.radians(yaw)), -math.cos(math.radians(pit)), math.sin(math.radians(pit)))
        arrow(p0, dv, 0.26, fl)
    # Bogen lehnt links, Koecher haengt rechts
    bow = [(-0.57, 0.04, 0.02 + 1.06 * i / 10) for i in range(11)]
    bow = [(x + 0.11 * math.sin(math.pi * i / 10), y, z) for i, (x, y, z) in enumerate(bow)]
    sweep(bow, [0.012, 0.018, 0.022, 0.024, 0.028, 0.03, 0.028, 0.024, 0.022, 0.018, 0.012], "wood", seg=8)
    tube(bow[0], bow[-1], 0.005, "rope", seg=4)
    with xf(about(R("Y", 10), (0.48, 0.06, 0.2))):
        lathe([(0, 0), (0.06, 0), (0.075, 0.42), (0.065, 0.42), (0, 0.4)], ["leather", "leather_dark"], M=T(0.48, 0.04, 0.16), seg=12,
              band=[0, 0, 1, 1])
        hoop(0.48, 0.04, 0.5, 0.075, "brass", hh=0.04, t=0.01, seg=12)
        for dx, fl in ((-0.03, "red"), (0.0, "cloth_white"), (0.03, "red")):
            arrow((0.48 + dx, 0.04, 0.5), (dx * 3, 0, 1), 0.3, fl)


def pollen_cannon(f, n):
    # Lafette: zwei Stufenwangen, Riegel, vier Scheibenraeder mit Eisenreif
    cheek = [(-0.44, 0.12), (0.3, 0.12), (0.3, 0.47), (0.1, 0.47), (0.1, 0.39), (-0.1, 0.39), (-0.1, 0.31), (-0.28, 0.31), (-0.28, 0.23),
             (-0.44, 0.23)]
    for y0, y1 in ((0.11, 0.17), (0.43, 0.49)):
        ext(cheek, y0, y1, "paint_teal")
    ext([(-0.44, 0.12), (0.3, 0.12), (0.3, 0.16), (-0.44, 0.16)], 0.104, 0.11, "iron")
    for x, z in ((0.26, 0.41), (0.06, 0.33), (-0.14, 0.25), (-0.4, 0.19)):
        stud(x, 0.104, z, 0.018, "brass")
    box(-0.4, 0.17, 0.12, 0.26, 0.43, 0.2, "paint_teal_dark")
    box(0.18, 0.17, 0.2, 0.26, 0.43, 0.4, "paint_teal_dark")
    for x, rw in ((0.16, 0.13), (-0.3, 0.11)):
        tube((x, 0.03, rw), (x, 0.57, rw), 0.025, "iron", seg=8)
        for y in (0.03, 0.51):
            disc_y(x, y, rw, rw, 0.06, "wood", seg=20)
            ring_y(x, y - 0.004, rw, rw * 0.84, rw + 0.006, 0.068, "iron", seg=20)
            disc_y(x, y - 0.014, rw, rw * 0.3, 0.02, "brass", seg=10)
    # Messingrohr mit Trichtermuendung, Pollenkugel geladen
    pv = (0.1, 0.3, 0.52)
    Mb = T(*pv) @ R("Y", 68)
    prof = [(0, -0.46), (0.035, -0.45), (0.045, -0.42), (0.025, -0.39), (0.09, -0.37), (0.118, -0.33), (0.118, -0.06), (0.1, -0.06),
            (0.094, 0.24), (0.11, 0.26), (0.13, 0.35), (0.155, 0.4), (0.135, 0.42), (0.09, 0.42), (0.09, 0.36), (0, 0.36)]
    lathe(prof, ["brass", "brass_dark", "soot"], M=Mb, seg=20, band=[1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 2, 2])
    for tt in (-0.3, -0.14, 0.1):
        hoop(0, 0, tt, 0.118 if tt < -0.06 else 0.1, "brass_dark", hh=0.035, t=0.012, M=Mb, seg=20)
    ob = sph(0, 0, 0.39, 0.085, "pollen", seg=12)
    ob.data.transform(Mb)
    tube((pv[0], 0.14, pv[2]), (pv[0], 0.46, pv[2]), 0.04, "brass_dark", seg=10)
    for y in (0.104, 0.49):
        box(pv[0] - 0.06, y - 0.004, pv[2] - 0.05, pv[0] + 0.06, y + 0.006, pv[2] + 0.02, "iron")
    # Zuendloch mit Glut, Richtkeil
    tp = Mb @ Vector((0, 0, -0.26)) + Vector((0, 0, 0.125))
    flat(sph(tp.x, tp.y, tp.z, 0.022, "ember", seg=6))
    glow(tp.x, tp.y, tp.z, 0.1, "flame", 0.4)
    ext([(-0.26, 0.31), (-0.02, 0.31), (-0.02, 0.37)], 0.24, 0.36, "wood")
    # Pollenkugeln im Dreieck, Wischer lehnt hinten
    for x, y, z in ((0.37, 0.06, 0.07), (0.5, 0.09, 0.07), (0.42, 0.17, 0.07), (0.43, 0.1, 0.175)):
        sph(x, y, z, 0.07, "pollen", seg=12)
        flat(noline(sph(x - 0.025, y - 0.03, z + 0.04, 0.016, "glow_hot", seg=6)))
    tube((-0.5, 0.33, 0.0), (-0.4, 0.33, 0.78), 0.016, "wood_light", seg=6)
    soft(-0.395, 0.33, 0.82, 0.05, 0.05, 0.075, "cloth_white", k=0.3, seg=12)


# ------------------------------------------------------------------ Drone Dock

def drone_perch(f, n):
    cx, cy = 0.0, 0.6
    # Pflanzring am Fuss: sechseckiger Kasten mit Erde und Blumen
    slab(S.hexagon_pts(cx, cy, 0.5), 0.0, 0.17, "paint_cream", bev=0.015)
    prism(S.hexagon_pts(cx, cy, 0.43), 0.17, 0.175, "propolis")
    for px, py in S.hexagon_pts(cx, cy, 0.5):
        tube((px * 0.985 + cx * 0.015, py * 0.985 + cy * 0.015, 0.0), (px * 0.985 + cx * 0.015, py * 0.985 + cy * 0.015, 0.19), 0.028,
             "paint_teal_dark", seg=6)
    for i, c in enumerate(("petal_pink", "petal_blue", "petal_white", "royal_light", "pollen", "petal_pink", "petal_white")):
        a = math.radians(195 + i * 25)
        flower(cx + math.cos(a) * 0.33, cy + math.sin(a) * 0.33, 0.17, s=0.85, petal=c, stem=0.14 + 0.05 * (i % 2))
        sph(cx + math.cos(a + 0.2) * 0.3, cy + math.sin(a + 0.2) * 0.3, 0.18, 0.06, "moss", seg=8, sz=0.5)
    # gedrechselter Pfosten, drei Kopfbaender
    lathe([(0, 0.17), (0.12, 0.17), (0.13, 0.22), (0.08, 0.28), (0.07, 0.6), (0.1, 0.66), (0.1, 0.7), (0.075, 0.74), (0.09, 0.95),
           (0, 0.95)], "wood", M=T(cx, cy, 0), seg=14)
    hoop(cx, cy, 0.68, 0.102, "brass", hh=0.035, t=0.008, seg=14)
    for a in (215, 325, 90):
        r = math.radians(a)
        c, s = math.cos(r), math.sin(r)
        sweep([(cx + c * 0.07, cy + s * 0.07, 0.72), (cx + c * 0.2, cy + s * 0.2, 0.8), (cx + c * 0.4, cy + s * 0.4, 0.95)],
              [0.03, 0.028, 0.03], "wood_dark", seg=8)
    # Landeteller: Bretter, gestrichener Rand, Landekreis, Wabe in der Mitte, Leuchtpunkte
    cyl(cx, cy, 0.95, 1.02, 0.57, "wood_light", seg=40)
    hoop(cx, cy, 0.985, 0.575, "paint_teal_dark", hh=0.075, t=0.02, seg=40)
    zt = 1.02
    noline(cyl(cx, cy, zt, zt + 0.004, 0.5, "paint_cream", seg=40))
    lathe([(0.34, 0), (0.42, 0), (0.42, 0.004), (0.34, 0.004)], "paint_teal", M=T(cx, cy, zt + 0.004), seg=40, loop=True)
    hexp(cx, cy, 0.2, zt + 0.004, zt + 0.012, "honey")
    hexp(cx, cy, 0.13, zt + 0.012, zt + 0.016, "paint_cream")
    for i in range(6):
        a = math.pi / 3 * i + math.pi / 6
        x, y = cx + math.cos(a) * 0.5, cy + math.sin(a) * 0.5
        on = i in (1, 4)
        flat(cyl(x, y, zt, zt + 0.025, 0.035, "glow_hot" if on else "honey_deep", seg=10))
        if on:
            glow(x, y, zt + 0.03, 0.14, "glow", 0.5)
    # Windsack am Mast, Drohne ist gelandet
    tube((cx + 0.4, cy + 0.34, zt), (cx + 0.4, cy + 0.34, zt + 0.42), 0.014, "brass", seg=6)
    sph(cx + 0.4, cy + 0.34, zt + 0.43, 0.025, "brass", seg=8)
    lathe([(0.065, 0), (0.058, 0.07), (0.05, 0.14), (0.04, 0.21), (0.028, 0.28)], ["coral", "paint_cream"],
          M=T(cx + 0.4, cy + 0.34, zt + 0.36) @ R("Y", 104), seg=10, band=[0, 1, 0, 1])
    bee(cx - 0.1, cy + 0.02, zt + 0.016, s=1.0, yaw=205, wing_up=30)


# ------------------------------------------------------------------ West Press / East Press

def nectar_press(f, n):
    cy = 0.66
    t = f / n
    # Schwellen und Bett
    for x in (-0.72, 0.72):
        bbox(x - 0.12, 0.3, 0.0, x + 0.12, 1.0, 0.11, "wood_dark", r=0.02, seg=1)
    bbox(-1.0, cy - 0.2, 0.05, 1.0, cy + 0.2, 0.2, "wood_dark", r=0.015, seg=1)
    # Pressbett aus Stein mit Rinne und Messingschnabel
    lathe([(0, 0.2), (0.43, 0.2), (0.45, 0.24), (0.45, 0.33), (0.41, 0.33), (0.4, 0.3), (0, 0.3)], ["stone", "stone_dark"],
          M=T(0, cy, 0), seg=28, band=[0, 0, 0, 0, 1, 1])
    lathe([(0, 0), (0.05, 0), (0.035, 0.16), (0.02, 0.16), (0, 0.14)], ["brass", "honey"], M=T(0, cy - 0.43, 0.285) @ R("X", 98),
          seg=10, band=[0, 0, 0, 1])
    ys = cy - 0.59
    # Korb: Dauben mit Fugen, zwei Eisenreifen, Bluetenmaische
    lathe([(0, 0.3), (0.35, 0.3), (0.36, 0.5), (0.35, 0.7), (0.31, 0.7), (0.31, 0.66), (0, 0.66)],
          ["wood", "wood_light", "wood_dark", "petal_pink"], M=T(0, cy, 0), seg=22, band=[0, 0, 0, 2, 2, 3], stripe=(0, 1))
    for z in (0.38, 0.6):
        hoop(0, cy, z, 0.362, "iron", hh=0.05, t=0.014, seg=22)
    for i, (dx, dy, c) in enumerate(((-0.2, -0.12, "pollen"), (0.2, -0.14, "petal_white"), (-0.16, 0.14, "petal_blue"),
                                     (0.19, 0.12, "leaf"), (0.0, -0.24, "pollen"), (-0.25, 0.02, "petal_white"))):
        sph(dx, cy + dy, 0.665, 0.045, c, seg=8, sz=0.55)
    # Pressdeckel mit Kreuzholz
    cyl(0, cy, 0.67, 0.73, 0.25, "wood_light", seg=22)
    bbox(-0.26, cy - 0.05, 0.73, 0.26, cy + 0.05, 0.8, "wood_dark", r=0.012, seg=1)
    bbox(-0.05, cy - 0.26, 0.73, 0.05, cy + 0.26, 0.8, "wood_dark", r=0.012, seg=1)
    # Holzspindel: Gewindegaenge wandern eine Steigung je Schleife
    cyl(0, cy, 0.8, 1.96, 0.058, "wood", seg=14)
    pitch = 0.11
    k = 0
    while True:
        z = 0.82 + (k + t) * pitch
        if z > 1.4:
            break
        ob = add(S.torus("gw", 0, 0, 0, 0.066, 0.022, "wood_light", seg=14, ring=6))
        ob.data.transform(T(0, cy, z) @ R("X", 9) @ R("Y", 5))
        k += 1
    # Pfosten mit Kopfbaendern, gewoelbtes Joch mit Messingmutter und Holznaegeln
    for sx in (-1, 1):
        x = sx * 0.72
        bbox(x - 0.085, cy - 0.11, 0.11, x + 0.085, cy + 0.11, 1.5, "wood", r=0.015, seg=1)
        ext([(sx * 0.635, 1.08), (sx * 0.635, 1.24), (sx * 0.36, 1.45), (sx * 0.24, 1.45)], cy - 0.04, cy + 0.04, "wood_light")
        for z in (0.3, 0.9):
            stud(x, cy - 0.11, z, 0.024, "brass")
    yoke = [(-0.95, 1.42), (0.95, 1.42), (0.95, 1.6)] + arc(0, 1.6, 0.95, 0, 180, 14, rz=0.16)[1:-1] + [(-0.95, 1.6)]
    slab(yoke, cy - 0.14, cy + 0.14, "wood_dark", bev=0.016, axis="y")
    for sx in (-1, 1):
        for dz in (0.0, 0.09):
            stud(sx * 0.72 + 0.0, cy - 0.14, 1.48 + dz, 0.02, "wood_light")
    hexp(0, cy, 0.15, 1.74, 1.83, "brass")
    hexplate(0, 1.56, 0.1, cy - 0.155, cy - 0.14, "brass")
    hexplate(0, 1.56, 0.065, cy - 0.162, cy - 0.155, "honey")
    # Handrad aus Messing: vier Speichen, vier Holzgriffe, 15 Grad je Bild
    zw = 1.96
    cyl(0, cy, zw - 0.07, zw + 0.05, 0.085, "brass_dark", seg=14)
    tor(0, cy, zw, 0.5, 0.036, "brass", seg=48, ring=8)
    rot = 90.0 * t + 12
    for k in range(4):
        a = math.radians(rot + 90 * k)
        ex, ey = math.cos(a) * 0.5, math.sin(a) * 0.5
        tube((0, cy, zw), (ex, cy + ey, zw), 0.024, "brass", seg=8)
        lathe([(0.022, 0), (0.034, 0.03), (0.038, 0.1), (0.028, 0.15), (0, 0.16)], "wood_dark", M=T(ex, cy + ey, zw + 0.02), seg=10)
        a2 = a + math.pi / 4
        stud(math.cos(a2) * 0.5, cy + math.sin(a2) * 0.5, zw + 0.03, 0.026, "brass_dark", "t")
    lathe([(0.05, 0), (0.06, 0.03), (0.03, 0.06), (0, 0.065)], "brass", M=T(0, cy, zw + 0.05), seg=12)
    # Trog davor: hohl, Nektar darin; Strahl und Tropfen, Wellenring
    tr = rrect(-0.92, 0.02, 0.92, 0.26, 0.1)
    trough(tr, 0.0, 0.2, 0.04, 0.09, "wood", fill="honey_light")
    for x in (-0.6, 0.6):
        box(x - 0.03, 0.012, 0.0, x + 0.03, 0.02, 0.2, "iron")
    zn = 0.14
    tube((0, ys + 0.02, 0.265), (0, ys, zn), 0.012, "honey_light", seg=6)
    for k in range(2):
        q = ((k + t) / 2) % 1.0
        sph(0, ys, 0.26 - (0.26 - zn - 0.02) * q * q, 0.024 * (0.6 + 0.5 * q), "honey", seg=8, sz=1.3)
    for k in range(2):
        q = ((k + t * 1.0) / 2 + 0.25) % 1.0
        noline(tor(0, ys, zn + 0.002, 0.03 + 0.1 * q, 0.009 * (1 - q) + 0.001, "honey", seg=16, ring=4, M=SC(1.0, 0.6, 1.0)))
    # links Bluetensack und Korb, rechts zwei Nektarkruege
    soft(-1.02, 0.6, 0.2, 0.17, 0.17, 0.21, "cloth_cream", k=0.35)
    hoop(-1.02, 0.6, 0.38, 0.075, "rope", hh=0.03, t=0.012, seg=10)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.4
        sph(-1.02 + math.cos(a) * 0.06, 0.6 + math.sin(a) * 0.05, 0.43, 0.045, ("petal_pink", "petal_white")[k % 2], seg=8, sz=0.5)
    sph(-1.02, 0.6, 0.45, 0.03, "pollen", seg=8)
    for x, y, s in ((1.0, 0.68, 1.0), (1.06, 0.44, 0.8)):
        lathe([(0, 0), (0.08 * s, 0), (0.13 * s, 0.1 * s), (0.13 * s, 0.2 * s), (0.07 * s, 0.3 * s), (0.085 * s, 0.34 * s),
               (0.06 * s, 0.34 * s), (0, 0.32 * s)], ["terracotta", "terracotta_dark", "honey"], M=T(x, y, 0), seg=14,
              band=[0, 0, 1, 0, 0, 0, 2])
        tor(x + 0.11 * s, y, 0.24 * s, 0.05 * s, 0.014 * s, "terracotta_dark", seg=10, ring=5, M=R("X", 90))


BUILDERS = {
    "bellows_big": bellows_big, "wax_cauldron": wax_cauldron, "dance_floor": dance_floor, "periscope": periscope,
    "telescope": telescope, "sundial": sundial, "target_board": target_board, "pollen_cannon": pollen_cannon,
    "flower_pots": flower_pots, "drone_perch": drone_perch, "nectar_press": nectar_press,
}

if __name__ == "__main__":
    main(BUILDERS)
