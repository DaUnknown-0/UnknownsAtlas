# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_well.py - Rauswurf "Honigbrunnen" (hive_well), Stil V2: der Brunnenring mit radialen Steinplatten, vorne aufgeschnitten.
# Man sieht in den runden Schacht: Wachswand mit Wabenrelief, Honigspiegel, davor der Schnitt durch Boden, Wabenmasse und Honig.
# Die Drehbruecke ist ein echtes 3D-Modell und wird in 19 Stellungen (0 bis 72 Grad) gerendert; die Szene blendet sie der Reihe
# nach ein (Daumenkino), dadurch dreht sie wirklich weg statt nur schmaler zu werden.
# Erzeugt: well_bg.jpg, well_br00..18.png, well_honey.png (Honig vor dem Spieler), well_stream.png, well_cog.png,
# well_bubble.png, well_ripple.png, well_foam.png.
#   blender -b --factory-startup -P eject_well.py

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eject_common as E  # noqa: E402

R = 2.65                 # Radius des Schachts
YC = 1.0                 # Tiefe der Schachtmitte (Drehachse der Bruecke)
HN = -1.5                # Honigspiegel (Boden und Brueckendeck liegen auf 0)
CUT = -0.8               # Schnittebene vorne
YB = 5.0                 # Rueckwand des Raums
WH = 1.75                # Wandhoehe
BR = 2.6                 # halbe Brueckenlaenge
PR = 1.5                 # Abstand des Spielers von der Drehachse
YS = -0.37               # Tiefe, in der der Spieler eintaucht (Bruecke bei 66 Grad)
STEP, NFR = 4, 19        # Brueckenbilder: alle 4 Grad
ACUT = math.asin((CUT - YC) / R)
XC = math.sqrt(R * R - (CUT - YC) ** 2)
SPOUT = (-1.35, 3.0, 0.95)                # Muendung des Honigrohrs
COG = (-3.95, 0.42, 0.62)                 # Zahnrad an der Winde (Mitte)
LAMP = (-4.75, 3.3, 1.55)                 # Laterne links

E.reset()
rnd = random.Random(11)
ARC = (ACUT, math.pi - ACUT)
ROOM = [(0, -1, -CUT), (0, 1, YB), (1, 0, 6.9), (-1, 0, 6.9)]


def honey_col(x, z):
    t = (HN + E.KZ * CUT - z) / 1.7
    return E.ramp([(0.0, (1.0, 0.70, 0.17)), (0.2, (0.97, 0.57, 0.08)), (0.65, (0.80, 0.38, 0.04)), (1.0, (0.58, 0.25, 0.03))], t)


def lake_tint(co):
    d = math.hypot(co.x, co.y - YC) / R
    k = 1.0 - 0.34 * E.smooth01((d - 0.45) / 0.55)                     # zum Rand dunkler und satter
    for cx, cy, f, amp in ((0.0, YC, 9.0, 0.07), (SPOUT[0], SPOUT[1], 12.0, 0.12)):
        dd = math.hypot(co.x - cx, co.y - cy)
        k *= 1.0 + amp * math.sin(dd * f) * max(0.0, 1 - dd / 1.6)
    k *= 1.0 + 0.04 * math.sin(co.x * 3.1 + co.y * 1.7)
    return (k, k * (0.93 + 0.07 * k), k * (0.7 + 0.3 * k))


def lake(y1):
    """Honigspiegel von der Schnittebene bis zur Tiefe y1."""
    def fn(u, v):
        x = -R * math.cos(math.pi * u) * 0.999
        h = math.sqrt(max(0.0, R * R - x * x))
        ya, yb = max(CUT, YC - h), min(y1, YC + h)
        return (x, ya + max(0.0, yb - ya) * v, HN)
    return E.sheet(fn, 72, 36, "lake_light", nl=True, tintfn=lake_tint)


def honey_front():
    """Schnitt durch den Honig: Verlauf in die Tiefe, eingesunkene Dinge, Lichtschlieren."""
    y = CUT
    top = HN + E.KZ * CUT
    E.grad_plane(-XC, -3.5, XC, top, y, honey_col, nx=8, nz=24)
    E.slab([(-XC, top - 0.035), (XC, top - 0.035), (XC, top), (-XC, top)], y - 0.01, y, "lake_light", lit=False, shear=False, nl=True,
           tint=(1.0, 0.98, 0.9))
    r2 = random.Random(4)
    for gx, gz, gw in ((-1.2, -2.05, 0.9), (0.5, -2.3, 0.6), (1.2, -1.95, 0.5), (-0.3, -2.75, 0.8), (-1.4, -3.0, 0.5)):
        E.slab(E.band_pts([(gx - gw / 2, gz), (gx, gz + 0.03), (gx + gw / 2, gz + 0.01)], 0.03, 0.01), y - 0.012, y - 0.01, "honey_light",
               lit=False, shear=False, nl=True)
    for k in range(9):
        bx, bz, br = r2.uniform(-XC + 0.2, XC - 0.2), r2.uniform(-3.2, -2.0), r2.uniform(0.035, 0.08)
        E.torus((bx, y - 0.02, bz), br, br * 0.22, "honey_light", seg=16, ring=6, lit=False, shear=False, nl=True)
    # eingesunken: Honigglas und ein Stueck Wabe, nur als dunklere Schemen
    E.slab(E.round_rect(1.05, -3.05, 1.5, -2.45, 0.08), y - 0.013, y - 0.011, "honey_deep", lit=False, shear=False, nl=True, tint=(1.0, 0.8, 0.6),
           M=E.about(E.R("Y", 24), (1.27, y, -2.75)))
    for k, (hx, hz) in enumerate(((-1.45, -2.62), (-1.19, -2.47), (-1.19, -2.77))):
        E.slab(E.hex_pts(hx, hz, 0.16), y - 0.013, y - 0.011, "honey_deep", lit=False, shear=False, nl=True, tint=(1.0, 0.8, 0.6))


def bridge(theta):
    """Drehbruecke um theta Grad gedreht (linkes Ende schwenkt nach vorn)."""
    M = E.about(E.R("Z", theta), (0, YC, 0))
    x = -BR + 0.06
    k = 0
    while x < BR - 0.07:
        w = min(0.26, BR - 0.06 - x)
        E.box(x + 0.006, x + w - 0.006, YC - 0.42, YC + 0.42, -0.08, 0.0, ["wood", "wood_light", "wood"][k % 3], bevel=0.012, M=M)
        x += w
        k += 1
    for sy in (-1, 1):
        E.box(-BR, BR, YC + sy * 0.5 - 0.05, YC + sy * 0.5 + 0.05, -0.17, 0.06, "paint_blue", bevel=0.02, M=M)
        for ex in (-1, 1):
            px = ex * (BR - 0.14)
            E.cyl(px, YC + sy * 0.5, 0.06, 0.36, 0.045, "wood_dark", seg=12, M=M)
            E.ball((px, YC + sy * 0.5, 0.4), 0.065, "brass", seg=14, M=M)
        if sy > 0:                                      # Gelaender nur hinten: vorn steht der Spieler davor und rutscht dort ab
            E.tube([(-BR + 0.14, YC + sy * 0.5, 0.3), (BR - 0.14, YC + sy * 0.5, 0.3)], 0.022, "brass", seg=8, cap=False, M=M)
            for px in (-1.3, 0.0, 1.3):
                E.cyl(px, YC + sy * 0.5, 0.06, 0.3, 0.025, "brass", seg=8, M=M)
    for ex in (-1, 1):
        E.box(ex * BR - 0.05, ex * BR + 0.05, YC - 0.57, YC + 0.57, -0.19, 0.08, "brass", bevel=0.02, M=M)
        E.tube([(ex * 2.05, YC, -0.17), (ex * 0.4, YC, -0.6)], 0.055, "paint_blue_dark", seg=10, M=M)
        E.tube([(ex * 2.05, YC - 0.4, -0.17), (ex * 0.42, YC - 0.2, -0.56)], 0.035, "brass_dark", seg=8, M=M)
        E.tube([(ex * 2.05, YC + 0.4, -0.17), (ex * 0.42, YC + 0.2, -0.56)], 0.035, "brass_dark", seg=8, M=M)
    E.box(-BR + 0.2, BR - 0.2, YC - 0.09, YC + 0.09, -0.24, -0.08, "wood_dark", bevel=0.015, M=M)
    E.cyl(0, YC, -0.26, -0.17, 0.66, "brass_dark", seg=40, bevel=0.02, M=M)
    E.cyl(0, YC, -0.72, -0.26, 0.5, "brass", seg=40, bevel=0.03, M=M)
    for i in range(20):                                  # Zahnkranz: an ihm sieht man die Drehung
        a = 360.0 * i / 20
        E.box(0.48, 0.6, YC - 0.045, YC + 0.045, -0.72, -0.56, "brass_dark", bevel=0.012, M=M @ E.about(E.R("Z", a), (0, YC, 0)))
    for i in range(4):
        a = 90.0 * i + 45
        E.ball((0.36, YC, -0.165), 0.045, "brass", seg=10, M=M @ E.about(E.R("Z", a), (0, YC, 0)))


# ------------------------------------------------------------------ Hintergrund
# Rueckwand des Raums mit Wabenrelief, Kragen und dunkler Krone (wie die Waende der Karte, nur von vorn)
def wall_tint(u, v):
    k = 0.58 + 0.56 * E.smooth01(v / WH)
    side = 1.0 - 0.2 * E.smooth01((abs(u) - 3.0) / 3.5)
    return (k * side, k * side, k * side)


cells = E.hex_grid(-7.0, 0.0, 7.0, WH, 0.31)
E.panel(-7.0, 0.0, 7.0, WH, YB + 0.07, "wall_front_b", nx=24, nz=6, nl=True, tintfn=lambda co: wall_tint(co.x, co.z))
E.hexfield(cells, 0.31, E.wall_place(YB), ["wall_front:wax", "wall_front:wax", "wall_front_b", "comb"],
           pick=lambda i, u, v: rnd.choice([1, 1, 1, 1, 2, 2, 3]), tintfn=wall_tint, var=0.05, depth=0.06)
for u, v in ((-5.58, 0.805), (-2.79, 1.074), (0.465, 0.805), (5.115, 1.074), (2.325, 0.537)):
    E.slab(E.hex_pts(u, v, 0.23), YB + 0.015, YB + 0.06, "wall_glow", lit=False, nl=True)
    E.halo(u, v, 0.55, YB - 0.01, "glow", 0.4)
E.box(-7.0, 7.0, YB - 0.07, YB + 0.02, 0.0, 0.17, "wall_base", bevel=0.025)
E.box(-7.0, 7.0, YB - 0.1, YB + 0.1, WH - 0.02, WH + 0.1, "wall_lip", bevel=0.035)
E.ground(-7.0, YB + 0.05, 7.0, YB + 6.0, WH + 0.05, "wall_top")
dc = E.hex_grid(-7.0, YB + 0.5, 7.0, YB + 6.0, 0.42)
E.hexfield(dc, 0.42, lambda u, v, d: (u, v, WH + 0.06 - d), ["wall_top", "wall_cell", "wall_cell_b", "wall_cell_c"],
           pick=lambda i, u, v: rnd.choice([1, 1, 2, 2, 3]), depth=0.02, inset=0.9, inner=0.84, var=0.08)
for x, ln, w in ((-6.0, 0.4, 0.1), (-3.9, 0.55, 0.12), (-0.4, 0.35, 0.1), (1.7, 0.6, 0.12), (4.6, 0.4, 0.1), (6.2, 0.5, 0.11)):
    E.drip(x, YB - 0.12, WH + 0.02, ln, w)

# Wabenschott in der Rueckwand (Rahmen dunkles Holz, Zellen wie die Wandstirn)
DX = 3.1
E.box(DX - 0.78, DX + 0.78, YB - 0.14, YB + 0.02, 0.0, 1.5, "wood_dark", bevel=0.03)
E.box(DX - 0.64, DX + 0.64, YB - 0.16, YB - 0.1, 0.06, 1.38, "wall_front_b", bevel=0.01, tint=(0.75, 0.72, 0.7))
for i, (u, v) in enumerate(E.hex_grid(DX - 0.5, 0.2, DX + 0.5, 1.25, 0.17)):
    if abs(u - DX) < 0.56 and 0.16 < v < 1.3:
        E.slab(E.hex_pts(u, v, 0.145), YB - 0.185, YB - 0.15, "wall_glow" if i % 4 == 0 else ["wall_front:wax", "wall_front_b"][i % 2],
               bevel=0.02, seg=1, nl=True, lit=(i % 4 != 0))
E.box(DX - 0.86, DX + 0.86, YB - 0.18, YB + 0.02, 1.5, 1.62, "wood_dark", bevel=0.03)
E.slab(E.hex_pts(DX, 1.56, 0.07), YB - 0.21, YB - 0.17, "brass", bevel=0.01)

# Boden: radiale Steinplatten in zwei Kraenzen um den Schacht (wie auf der Karte), Fugengrund darunter
E.flats(E.sector_tiles(0, YC, R + 0.2, 12.0, 48), -0.006, "fl_joint", planes=ROOM)
E.tiles(E.sector_tiles(0, YC, R + 0.3, 4.25, 24), 0.0, ["fl_stone", "fl_stone_b", "fl_stone"], planes=ROOM, base=[], var=0.05, seed=2)
E.tiles(E.sector_tiles(0, YC, 4.25, 9.5, 24, a_off=math.pi / 24, sub=6), 0.0, ["fl_sand_b", "fl_stone", "fl_stone_b"], planes=ROOM, base=[],
        var=0.05, seed=4)
E.fade(-6.9, 6.9, YB - 0.07, YB - 0.8, E.PLUM, 0.34, plane="floor", at=0.02)

# Schacht: Loch im Boden (dunkel), Wachswand mit Relief, Kragen am Rand, Honigspiegel
E.sheet(lambda u, v: ((R + 0.08) * math.cos(ARC[0] + (ARC[1] - ARC[0]) * u), YC + (R + 0.08) * math.sin(ARC[0] + (ARC[1] - ARC[0]) * u),
                      HN - 0.4 + (0.4 - HN) * v), 64, 4, "wall_front_b", nl=True,
        tintfn=lambda co: (0.5 + 0.5 * E.smooth01((co.z - HN) / -HN),) * 3)


def pit_tint(u, v):
    k = 0.55 + 0.6 * E.smooth01((v - HN) / -HN)
    return (k, k, k)


pc = [(u, v) for u, v in E.hex_grid(R * ARC[0], HN - 0.3, R * ARC[1], 0.0, 0.3) if R * ARC[0] + 0.3 < u < R * ARC[1] - 0.3 and v < -0.28]
E.hexfield(pc, 0.3, lambda u, v, d: ((R + d) * math.cos(u / R), YC + (R + d) * math.sin(u / R), v),
           ["wall_front:wax", "wall_front:wax", "wall_front_b", "comb"], pick=lambda i, u, v: rnd.choice([1, 1, 1, 2, 2, 3]),
           tintfn=pit_tint, var=0.05, depth=0.06)
E.lathe([(R - 0.03, -0.14), (R - 0.03, 0.04), (R + 0.02, 0.09), (R + 0.2, 0.09), (R + 0.26, 0.04), (R + 0.26, 0.0)], (0, YC, 0), "wall_lip",
        seg=72, arc=ARC)
E.sheet(lambda u, v: ((R + 0.26 + 0.1 * v) * math.cos(ARC[0] + (ARC[1] - ARC[0]) * u), YC + (R + 0.26 + 0.1 * v) * math.sin(ARC[0] + (ARC[1] - ARC[0]) * u),
                      0.004), 64, 1, "wall_base", nl=True)
for a, ln, w in ((0.5, 0.5, 0.12), (1.0, 0.3, 0.1), (1.35, 0.7, 0.13), (2.0, 0.4, 0.11), (2.45, 0.6, 0.12), (2.9, 0.3, 0.1)):
    E.drip((R - 0.06) * math.cos(a), YC + (R - 0.06) * math.sin(a), -0.1, ln, w)
lake(YC + R)
# Mittelpfosten, traegt die Bruecke
E.cyl(0, YC, HN - 0.5, -0.74, 0.3, "iron", seg=32)
for hz in (HN + 0.02, HN + 0.42):
    E.cyl(0, YC, hz, hz + 0.1, 0.36, "iron_light", seg=32, bevel=0.02)
E.cyl(0, YC, -0.86, -0.74, 0.42, "brass", seg=32, bevel=0.025)

# Gelaender am Schachtrand: Messingpfosten mit durchhaengendem Seil (Luecken an den Brueckenkoepfen)
RP = R + 0.5
for grp in ((22, 46, 70, 94, 118, 142, 166), (-12, -30), (192, 210)):
    pts = []
    for a in grp:
        ar = math.radians(a)
        px, py = RP * math.cos(ar), YC + RP * math.sin(ar)
        if py < CUT + 0.15:
            continue
        E.cyl(px, py, 0.0, 0.06, 0.09, "brass_dark", seg=12)
        E.cyl(px, py, 0.06, 0.74, 0.04, "brass", seg=12)
        E.ball((px, py, 0.79), 0.075, "brass", seg=14)
        E.gshadow(px, py, 0.1, 0.08, 0.0, 0.3)
        pts.append((px, py))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        E.tube([(ax, ay, 0.64), ((ax + bx) / 2, (ay + by) / 2, 0.5), (bx, by, 0.64)], 0.026, "rope", seg=8, sm=6, cap=False)

# Honigrohr: kommt aus der Rueckwand, Stuetze auf dem Ring, Muendung ueber dem Schacht
pipe = [(SPOUT[0] - 0.25, YB, 1.25), (SPOUT[0] - 0.2, 4.3, 1.42), (SPOUT[0] - 0.05, 3.5, 1.42), (SPOUT[0], 3.08, 1.3), (SPOUT[0], SPOUT[1], 1.0)]
E.tube(pipe, 0.17, "brass", seg=16, sm=6, cap=False)
E.cyl(SPOUT[0], SPOUT[1], SPOUT[2] - 0.04, SPOUT[2] + 0.1, 0.215, "brass_dark", seg=20, bevel=0.02)
E.torus((SPOUT[0] - 0.24, YB - 0.1, 1.27), 0.2, 0.05, "brass_dark", seg=20, ring=8, axis="y")
E.cyl(SPOUT[0] - 0.18, 4.15, 0.0, 1.25, 0.06, "paint_blue", seg=12)
E.box(SPOUT[0] - 0.42, SPOUT[0] + 0.06, 3.95, 4.35, 0.0, 0.1, "paint_blue_dark", bevel=0.02)
E.torus((SPOUT[0] - 0.18, 4.15, 1.42), 0.17, 0.035, "brass_dark", seg=16, ring=6, axis="y")
E.gshadow(SPOUT[0] - 0.18, 4.15, 0.3, 0.22, 0.0, 0.3)

# links: Laternenpfosten, Honigeimer, gestrichene Kiste; rechts: Winde der Bruecke (Zahnrad dreht als eigenes Bild)
E.cyl(LAMP[0], LAMP[1], 0.0, 0.1, 0.16, "brass_dark", seg=16, bevel=0.02)
E.cyl(LAMP[0], LAMP[1], 0.1, LAMP[2] - 0.3, 0.045, "brass", seg=12)
E.lathe([(0.05, 0.0), (0.2, 0.08), (0.2, 0.12)], (LAMP[0], LAMP[1], LAMP[2] - 0.34), "brass", seg=6)
E.lathe([(0.16, 0.0), (0.19, 0.14), (0.19, 0.32), (0.16, 0.42)], (LAMP[0], LAMP[1], LAMP[2] - 0.22), "wall_glow", seg=6, lit=False,
        tint=(1.0, 0.95, 0.85))
E.lathe([(0.21, 0.0), (0.22, 0.04), (0.1, 0.14), (0.0, 0.2)], (LAMP[0], LAMP[1], LAMP[2] + 0.2), "brass", seg=6)
E.gshadow(LAMP[0], LAMP[1], 0.2, 0.15, 0.0, 0.3)
for bx, by, s in ((3.75, 1.7, 1.0), (4.3, 1.25, 0.8)):
    E.lathe([(0.2 * s, 0.0), (0.26 * s, 0.42 * s), (0.25 * s, 0.42 * s)], (bx, by, 0.0), "wood", seg=20)
    E.cyl(bx, by, 0.36 * s, 0.39 * s, 0.24 * s, "honey", seg=20)
    for hz in (0.08, 0.3):
        E.torus((bx, by, hz * s), (0.2 + 0.06 * hz / 0.42) * s + 0.01, 0.016, "brass", axis="z", seg=20, ring=6)
    E.tube([(bx - 0.25 * s, by, 0.4 * s), (bx, by, 0.7 * s), (bx + 0.25 * s, by, 0.4 * s)], 0.014, "brass_dark", seg=6, sm=6, cap=False)
    E.gshadow(bx, by, 0.26 * s, 0.2 * s, 0.0)
E.box(4.6, 5.5, 3.2, 3.9, 0.0, 0.62, "paint_blue", bevel=0.025)
E.box(4.54, 5.56, 3.14, 3.96, 0.62, 0.71, "wood", bevel=0.025)
E.box(4.8, 5.3, 3.185, 3.2, 0.06, 0.11, "black", bevel=0.01)
E.slab(E.hex_pts(5.05, 0.42, 0.08), 3.17, 3.2, "brass", bevel=0.012)
E.gshadow(5.05, 3.55, 0.5, 0.38, 0.0)

wx, wy = COG[0], COG[1]
E.box(wx - 0.5, wx + 0.5, wy + 0.1, wy + 0.8, 0.0, 0.9, "paint_blue", bevel=0.03)
E.box(wx - 0.56, wx + 0.56, wy + 0.04, wy + 0.86, 0.9, 1.0, "wood", bevel=0.025)
E.cyl(wx, wy + 0.45, 1.0, 1.16, 0.09, "brass", seg=12)
E.tube([(wx, wy + 0.45, 1.16), (wx + 0.3, wy + 0.45, 1.3)], 0.03, "brass", seg=8)
E.ball((wx + 0.33, wy + 0.45, 1.33), 0.06, "wood_dark", seg=12)
E.tube([(wx, wy + 0.1, COG[2]), (wx, wy - 0.02, COG[2])], 0.07, "brass_dark", seg=12, cap=False)
E.tube([(wx + 0.5, wy + 0.45, 0.3), (-R - 0.1, YC - 0.3, 0.2), (-R + 0.1, YC - 0.2, -0.25)], 0.05, "brass_dark", seg=10, sm=5, cap=False)   # Welle zum Schacht
E.gshadow(wx, wy + 0.45, 0.62, 0.42, 0.0)

# Schnitt vorne: Steinplatte, Wachsfutter des Schachts, dunkle Wabenmasse; in der Mitte der Honig
for sx in (-1, 1):
    xa, xb = (-7.0, -XC) if sx < 0 else (XC, 7.0)
    E.box(xa, xb, CUT, CUT + 0.3, -3.6, -0.11, "wall_top", nl=True)
    E.box(xa, xb, CUT - 0.004, CUT + 0.3, -0.11, 0.0, "stone", bevel=0.0)
    la, lb = (-XC - 0.3, -XC) if sx < 0 else (XC, XC + 0.3)
    E.box(la, lb, CUT - 0.006, CUT + 0.2, -3.6, -0.11, "wall_front_b", tint=(0.8, 0.76, 0.72))
    E.fade(xa, xb, -0.11, -0.5, E.PLUM, 0.3, plane="wall", at=CUT - 0.012)
    sc = [(u, v) for u, v in E.hex_grid(xa, -3.6, xb, -0.3, 0.36) if xa + 0.5 < u < xb - 0.5 and v < -0.5
          and not (la - 0.45 < u < lb + 0.45)]
    E.hexfield(sc, 0.36, E.wall_place(CUT - 0.005), ["wall_top", "wall_cell", "wall_cell_b", "wall_cell_c"],
               pick=lambda i, u, v: rnd.choice([1, 1, 2, 3, 3]), depth=0.02, inset=0.9, inner=0.84, var=0.14)
honey_front()

E.render_bg("well_bg")

# ------------------------------------------------------------------ Ebenen
E.clear()
honey_front()
lake(YS)
E.render_layer("well_honey", pad=0.0, bounds=(-XC, -3.42, XC, HN + E.KZ * YS))

for i in range(NFR):
    E.clear()
    bridge(i * STEP)
    E.render_layer(f"well_br{i:02d}", pivot=(0, YC, 0))

E.clear()
st = []
n = 14
ln = SPOUT[2] - HN
E.tube([(SPOUT[0] + 0.012 * math.sin(i * 1.9), SPOUT[1], SPOUT[2] - ln * i / n) for i in range(n + 1)], 0.15, "honey", seg=16, cap=False,
       rfn=lambda u: 0.17 - 0.05 * math.sin(min(1.0, u * 1.3) * math.pi * 0.5) + 0.016 * math.sin(u * 19.0) + 0.05 * max(0.0, u - 0.85) / 0.15)
E.tube([(SPOUT[0] - 0.05, SPOUT[1] - 0.14, SPOUT[2] - 0.15), (SPOUT[0] - 0.035, SPOUT[1] - 0.12, SPOUT[2] - ln * 0.55),
        (SPOUT[0] - 0.05, SPOUT[1] - 0.14, HN + 0.25)], 0.022, "honey_light", seg=6, lit=False, nl=True)
E.render_layer("well_stream", pivot=SPOUT)

E.clear()                                               # Schaumkranz, wo der Strahl auftrifft (liegt auf dem Spiegel)
for k, (rr, w) in enumerate(((0.3, 0.05), (0.5, 0.035))):
    E.torus((0, 0, 0), rr, w, "honey_light", seg=40, ring=6, axis="z", scale=(1.0, 1.0), lit=False, nl=True,
            M=E.Matrix.Diagonal((1, 1, 0.1, 1)))
E.render_layer("well_foam", pivot=(0, 0, 0), pad=0.03)

E.clear()                                               # Zahnrad der Winde (dreht sich im Bild, steht dem Betrachter zugewandt)
CR, CT = 0.36, 12
pts = []
for i in range(CT * 4):
    a = 2 * math.pi * (i - 0.5) / (CT * 4)
    pts.append(((CR + (0.085 if (i // 2) % 2 == 0 else 0.0)) * math.cos(a), (CR + (0.085 if (i // 2) % 2 == 0 else 0.0)) * math.sin(a)))
E.slab(pts, -0.1, 0.0, "brass", bevel=0.02, seg=1)
E.lathe([(0.27, 0.0), (0.27, -0.03), (0.15, -0.03), (0.15, 0.0)], (0, -0.1, 0), "brass_dark", seg=32, axis="y", caps=False)
for k in range(6):
    a = math.pi / 3 * k
    E.lathe([(0.045, 0.0), (0.035, -0.025)], (0.2 * math.cos(a), -0.105, 0.2 * math.sin(a)), "wood_dark", seg=10, axis="y")
E.lathe([(0.1, 0.0), (0.09, -0.06), (0.05, -0.08)], (0, -0.1, 0), "brass", seg=16, axis="y")
E.render_layer("well_cog", pivot=(0, 0, 0))

E.clear()                                               # Blase: Kuppel auf dem Spiegel, Anker unten Mitte
E.lathe([(0.17, 0.0), (0.165, 0.05), (0.13, 0.12), (0.07, 0.17), (0.0, 0.185)], (0, 0, 0), "honey_light", seg=24)
E.ellipsoid((-0.06, -0.12, 0.11), (0.04, 0.02, 0.025), "white", seg=10, lit=False, nl=True)
E.render_layer("well_bubble", pivot=(0, 0, 0))

E.clear()                                               # Wellenring auf dem Spiegel
E.torus((0, 0, 0), 0.5, 0.045, "honey_light", seg=48, ring=6, axis="z", lit=False, nl=True, M=E.Matrix.Diagonal((1, 1, 0.1, 1)))
E.render_layer("well_ripple", pivot=(0, 0, 0), pad=0.03)

E.note("well_pts", axis=list(E.img(0, YC, 0)), yc=YC, kz=E.KZ, pr=PR, honey=HN, ys=YS, step=STEP, frames=NFR,
       spout=list(E.img(*SPOUT)), impact=list(E.img(SPOUT[0], SPOUT[1], HN)), cog=list(E.img(*COG)), lamp=list(E.img(*LAMP)),
       xc=XC, cut=CUT, glows=[list(E.img(u, YB, v)) for u, v in ((-5.58, 0.805), (-2.79, 1.074), (0.465, 0.805), (5.115, 1.074))])
