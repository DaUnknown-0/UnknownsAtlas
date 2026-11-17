# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_sundeck.py - Skip "Stilles Sonnendeck" (hive_skip_sundeck), Stil V2: das Sonnendeck oben auf dem Bienenstock.
# Links woelbt sich die Wachskuppel des Stocks mit Wabenrelief, Wulstringen, Wabenschott und dunkler Kronenkappe samt Wimpel,
# davor das Dielendeck (kuehle Dielen wie auf der Karte) mit Petrol-Gelaender, Sonnenuhr, Fernrohr und Bienenkaesten;
# dahinter weit unten das Land, Wolken auf Augenhoehe. Im Kuebel waechst die grosse Bluete, auf der die Biene landet.
# Erzeugt: deck_bg.jpg, deck_stem.png, deck_flower.png, deck_drop.png, deck_splat.png, deck_cloud0/1/2.png, deck_flag.png.
#   blender -b --factory-startup -P eject_sundeck.py

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eject_common as E  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

G = -2.3                 # Deck
YR = 2.4                 # Gelaender (hintere Deckkante)
DOME = (-4.9, 4.4)       # Achse der Kuppel
DR = 2.3                 # Radius der Kuppel am Fuss
POT = (1.2, 0.6)         # Blumenkuebel
S0 = (POT[0], POT[1], G + 0.6)                         # Stielfuss (Erde)
S1 = (POT[0] + 0.1, POT[1] - 0.06, G + 0.6 + 1.85)     # Bluetenmitte
TILT = math.radians(38)  # Bluete ist nach oben gekippt
E1, E2, EN = Vector((1, 0, 0)), Vector((0, math.sin(TILT), math.cos(TILT))), Vector((0, -math.cos(TILT), math.sin(TILT)))
TIP_A = math.radians(-42)                              # Blatt, an dem der Tropfen haengt
TIP = Vector(S1) + 0.6 * (math.cos(TIP_A) * E1 + math.sin(TIP_A) * E2)
FLAG = (DOME[0], DOME[1], G + 4.08)
SUN = (3.9, 2.35)

E.reset()
rnd = random.Random(31)


def cloud(cx, cz, s, y, seed, col="cloud"):
    """Haufenwolke aus weichen Ballen (Bildkoordinaten, ungeschert): flacher Boden, oben ungleich hohe Kuppen."""
    r2 = random.Random(seed)
    E.ellipsoid((cx, y + 0.3, cz + 0.14 * s), (s * 0.86, 0.3, s * 0.17), col, seg=28, shear=False)
    n = 7
    for k in range(n):
        t = k / (n - 1)
        r = s * (0.13 + 0.27 * math.sin(math.pi * t) ** 0.8 * (0.6 + 0.6 * r2.random()))
        E.ellipsoid((cx + (t - 0.5) * s * 1.6 + 0.05 * s * (r2.random() - 0.5), y + 0.1 + k * 0.01, cz + 0.12 * s + r * 0.62), (r * 1.15, 0.3, r), col,
                    seg=24, shear=False)
    for k in range(4):                                   # kleinere Ballen vorn unten
        t = (k + 0.5) / 4
        r = s * (0.12 + 0.1 * r2.random())
        E.ellipsoid((cx + (t - 0.5) * s * 1.5, y - 0.1 - k * 0.01, cz + 0.08 * s + r * 0.45), (r * 1.3, 0.3, r * 0.9), col, seg=20, shear=False)


# ------------------------------------------------------------------ Hintergrund: Himmel und Land weit unten (Bildkoordinaten)
def sky(x, z):
    c = E.ramp([(0.0, (0.93, 0.95, 0.93)), (0.25, (0.72, 0.87, 0.97)), (0.6, (0.50, 0.72, 0.95)), (1.0, (0.36, 0.58, 0.90))], (z + 0.1) / 3.5)
    d = math.hypot(x - SUN[0], z - SUN[1])
    return E.mix(c, (1.0, 0.97, 0.80), max(0.0, 1 - d / 2.6) ** 2 * 0.6)


E.grad_plane(-6.5, -1.6, 6.5, 3.5, 90.0, sky, nx=40, nz=30)
E.slab(E.ell_pts(SUN[0], SUN[1], 0.5, 0.5, 48), 88.0, 88.1, "sun", lit=False, shear=False, nl=True)
HZ = 0.72                                               # das Land liegt weit unten, der Horizont auf Augenhoehe
far = [(-6.5, -3.0), (6.5, -3.0), (6.5, -0.62 + HZ)] + [(x, HZ - 0.62 + 0.16 * math.sin(x * 0.55 + 1.0) + 0.07 * math.sin(x * 1.7)) for x in
                                                      [6.5 - 13 * i / 60 for i in range(61)]]
E.slab(far, 80.0, 80.1, "hill_far", lit=False, shear=False, nl=True, tint=(1.05, 1.08, 1.15))
for hx, hs in ((2.75, 0.5), (5.0, 0.34), (-1.3, 0.3)):   # ferne Stoecke auf den Huegeln (Schattenrisse)
    hz = HZ - 0.66 + 0.16 * math.sin(hx * 0.55 + 1.0)
    skep = [(hx - 0.42 * hs, hz), (hx + 0.42 * hs, hz)] + [(hx + 0.42 * hs * math.cos(a), hz + 0.3 * hs + 0.6 * hs * math.sin(a)) for a in
                                                         [math.pi * i / 14 for i in range(15)]]
    E.slab(skep, 79.0, 79.1, "hill_far", lit=False, shear=False, nl=True, tint=(0.93, 0.95, 1.06))
    E.slab([(hx - 0.01 * hs, hz + 0.9 * hs), (hx + 0.01 * hs, hz + 0.9 * hs), (hx + 0.01 * hs, hz + 1.2 * hs), (hx + 0.2 * hs, hz + 1.13 * hs),
            (hx + 0.01 * hs, hz + 1.05 * hs), (hx - 0.01 * hs, hz + 1.05 * hs)], 79.0, 79.1, "hill_far", lit=False, shear=False, nl=True, tint=(0.9, 0.92, 1.04))
mid = [(-6.5, -3.0), (6.5, -3.0), (6.5, -1.0 + HZ)] + [(x, HZ - 1.05 + 0.2 * math.sin(x * 0.42 - 0.6) + 0.06 * math.sin(x * 1.3 + 2)) for x in
                                                     [6.5 - 13 * i / 60 for i in range(61)]]
E.slab(mid, 70.0, 70.1, "hill_mid", lit=False, shear=False, nl=True, tint=(0.95, 1.0, 1.0))
near = [(-6.5, -3.0), (6.5, -3.0), (6.5, -1.3)] + [(x, -1.25 + 0.12 * math.sin(x * 0.7 + 2.0)) for x in [6.5 - 13 * i / 40 for i in range(41)]]
E.slab(near, 66.0, 66.1, "leaf", lit=False, shear=False, nl=True, tint=(0.92, 1.0, 0.9))
for k in range(34):                                      # Waeldchen
    tx = -6.2 + 12.4 * rnd.random()
    tz = HZ - 1.15 + 0.2 * math.sin(tx * 0.42 - 0.6) - 0.75 * rnd.random()
    r = 0.06 + 0.07 * rnd.random()
    E.ellipsoid((tx, 69.0 + tz, tz + r), (r * 1.2, 0.2, r), "leaf_dark" if k % 3 else "leaf", seg=14, shear=False, nl=True, tint=(0.9, 1.0, 0.95))
river = [(-6.5, -1.9 + HZ), (-4.0, -1.72 + HZ), (-2.2, -1.82 + HZ), (-0.6, -1.6 + HZ), (1.0, -1.68 + HZ), (2.4, -1.45 + HZ), (3.6, -1.38 + HZ),
         (4.4, -1.2 + HZ), (4.9, -1.1 + HZ)]
E.slab(E.band_pts([tuple(p) for p in E.catmull(river, 6)], 0.15, 0.02), 68.0, 68.1, "glass", lit=False, shear=False, nl=True, tint=(0.85, 0.95, 1.0))
cloud(-0.4, 0.62, 0.5, 85.0, 1)
cloud(4.7, 1.05, 0.4, 85.0, 2)
cloud(2.0, 0.42, 0.3, 85.0, 3)

# ------------------------------------------------------------------ Kuppel des Stocks
PROF = [(DR + 0.1, -1.6), (DR, 0.0), (DR, 1.05), (DR - 0.14, 1.75), (DR - 0.5, 2.45), (DR - 1.0, 2.95), (DR - 1.55, 3.3), (0.42, 3.5)]


def dome_r(h):
    for (ra, ha), (rb, hb) in zip(PROF, PROF[1:]):
        if h <= hb:
            return ra + (rb - ra) * (h - ha) / (hb - ha)
    return PROF[-1][0]


def dome_tint(u, v):
    k = 0.62 + 0.5 * E.smooth01(v / 2.9)
    return (k, k, k)


E.lathe([(r - (0.07 if h < 1.7 else 0.0), h) for r, h in PROF[:3] + [(DR - 0.13, 1.7)] + PROF[3:]], (DOME[0], DOME[1], G), "wall_front:wax", seg=64,
        tintfn=lambda co: dome_tint(0, co.z - G))
dcells = [(u, v) for u, v in E.hex_grid(-math.pi * DR, 0.3, 0.0, 1.7, 0.3) if 0.3 < v < 1.62]     # nur die geraden Ringe, oben glattes Wachs
E.hexfield(dcells, 0.3, lambda u, v, d: (DOME[0] + (dome_r(v) - d) * math.cos(u / DR), DOME[1] + (dome_r(v) - d) * math.sin(u / DR), G + v),
           ["wall_front:wax", "wall_front:wax", "wall_front_b", "comb"], pick=lambda i, u, v: rnd.choice([1, 1, 1, 2, 2, 3]),
           tintfn=dome_tint, var=0.05, depth=0.06)
for h in (0.12, 1.05, 1.75, 2.45):                       # Wulstringe wie bei einem Bienenkorb
    E.torus((DOME[0], DOME[1], G + h), dome_r(h) + 0.02, 0.1, "wall_lip", seg=64, ring=10, axis="z")
for a, v in ((-2.05, 1.4), (-1.15, 0.6), (-2.5, 0.62), (-1.62, 1.38)):   # Leuchtzellen
    r = dome_r(v) - 0.03
    c = Vector((DOME[0] + r * math.cos(a), DOME[1] + r * math.sin(a), G + v))
    rot = Matrix(((math.sin(a), -math.cos(a), 0), (math.cos(a), math.sin(a), 0), (0, 0, 1))).transposed()
    E.slab(E.hex_pts(0, 0, 0.22), -0.03, 0.03, "wall_glow", lit=False, nl=True, M=Matrix.Translation(c) @ rot.to_4x4())
# dunkle Kronenkappe mit Messingring (dort liegt die Kronenoeffnung), Wimpelmast
E.lathe([(DR - 1.5, 3.27), (DR - 1.6, 3.42), (0.6, 3.6), (0.4, 3.7), (0.0, 3.73)], (DOME[0], DOME[1], G), "wall_top", seg=48)
E.torus((DOME[0], DOME[1], G + 3.3), DR - 1.47, 0.07, "brass", seg=48, ring=8, axis="z")
E.cyl(DOME[0], DOME[1], G + 3.7, G + 4.25, 0.035, "wood_dark", seg=8)
E.ball((DOME[0], DOME[1], G + 4.29), 0.06, "brass", seg=12)
for a, ln, w in ((-2.3, 0.5, 0.12), (-1.75, 0.35, 0.1), (-1.3, 0.6, 0.13), (-0.8, 0.4, 0.1)):
    r = dome_r(2.45) + 0.1
    E.drip(DOME[0] + r * math.cos(a), DOME[1] + r * math.sin(a), G + 2.41, ln, w)

# Wabenschott zur Kuppel: kleiner Vorbau mit Wachsdach
VX, VY = -3.15, 2.3
E.box(VX - 0.72, VX + 0.72, VY, VY + 1.2, G, G + 1.75, "wall_front_b", bevel=0.05, tint=(0.8, 0.78, 0.75))
E.box(VX - 0.62, VX + 0.62, VY - 0.06, VY + 0.04, G, G + 1.52, "wood_dark", bevel=0.03)
E.box(VX - 0.5, VX + 0.5, VY - 0.08, VY - 0.04, G + 0.05, G + 1.4, "wall_front_b", bevel=0.01, tint=(0.72, 0.7, 0.68))
for i, (u, v) in enumerate(E.hex_grid(VX - 0.38, G + 0.22, VX + 0.38, G + 1.25, 0.17)):
    if abs(u - VX) < 0.44 and G + 0.16 < v < G + 1.3:
        E.slab(E.hex_pts(u, v, 0.145), VY - 0.105, VY - 0.075, "wall_glow" if i % 3 == 0 else ["wall_front:wax", "wall_front_b"][i % 2],
               bevel=0.02, seg=1, nl=True, lit=(i % 3 != 0))
roof = [(VX - 0.95, G + 1.72), (VX + 0.95, G + 1.72), (VX + 0.95, G + 1.82), (VX, G + 2.2), (VX - 0.95, G + 1.82)]
E.slab(roof, VY - 0.2, VY + 1.3, "wall_lip", bevel=0.04)
E.slab(E.hex_pts(VX, G + 1.9, 0.1), VY - 0.24, VY - 0.2, "brass", bevel=0.012)
E.gshadow(VX, VY + 0.1, 0.85, 0.3, G, 0.3)
E.fade(DOME[0] - DR, DOME[0] + DR + 0.4, YR - 0.2, YR - 0.9, E.PLUM, 0.3, plane="floor", at=G + 0.03)

# ------------------------------------------------------------------ Deck: kuehle Dielen, Wachskante, Petrol-Gelaender mit Nussholm
E.tiles(E.rect_tiles(-6.9, -3.9, 6.9, YR, 2.3, 0.3, jitter=0.25), G, ["fl_plank_c", "fl_plank", "fl_sand_b", "fl_plank_c"], var=0.05, gap=0.022,
        tintfn=lambda x, y: (0.9 + 0.1 * E.smooth01((1.5 - y) / 4.0),) * 3)
E.box(-2.75, 6.9, YR, YR + 0.16, G - 0.3, G + 0.07, "wall_lip", bevel=0.03)
for px in [-2.5 + 1.34 * i for i in range(8)]:
    E.box(px - 0.07, px + 0.07, YR + 0.01, YR + 0.15, G + 0.07, G + 0.95, "paint_teal", bevel=0.02)
    E.ball((px, YR + 0.08, G + 1.07), 0.075, "brass", seg=12)
    E.gshadow(px, YR, 0.1, 0.06, G, 0.25)
E.box(-2.6, 6.95, YR - 0.01, YR + 0.17, G + 0.95, G + 1.02, "wood", bevel=0.02)
E.box(-2.6, 6.95, YR + 0.04, YR + 0.12, G + 0.5, G + 0.56, "paint_teal_dark", bevel=0.015)
E.fade(-2.75, 6.9, YR - 0.02, YR - 0.4, E.PLUM, 0.22, plane="floor", at=G + 0.03)
for k in range(26):                                      # Bluetenblaetter auf dem Deck (wie auf der Karte)
    px, py = -2.0 + 8.5 * rnd.random(), -2.6 + 4.6 * rnd.random()
    a = rnd.random() * 3.14
    E.prism([(px + 0.07 * math.cos(a + t) * (1.0 if j % 2 else 0.55), py + 0.07 * math.sin(a + t) * (1.0 if j % 2 else 0.55))
             for j, t in enumerate([math.pi / 4 * q for q in range(8)])], G + 0.004, G + 0.008, rnd.choice(["petal_pink", "petal_white", "pollen"]),
            nl=True)
# Lueftungsgitter (Wabengitter) im Deck
vx, vy = -1.05, -0.9
E.prism([(vx + 0.55 * math.cos(math.pi / 3 * k), vy + 0.55 * math.sin(math.pi / 3 * k)) for k in range(6)], G, G + 0.03, "brass_dark", bevel=0.012)
E.prism([(vx + 0.45 * math.cos(math.pi / 3 * k), vy + 0.45 * math.sin(math.pi / 3 * k)) for k in range(6)], G + 0.03, G + 0.034, "black", nl=True)
for cx, cy in E.hex_grid(vx - 0.4, vy - 0.4, vx + 0.4, vy + 0.4, 0.13):
    if math.hypot(cx - vx, cy - vy) < 0.34:
        E.torus((cx, cy, G + 0.04), 0.1, 0.018, "brass", seg=6, ring=4, axis="z")


def hive_box(x, y, z, w, d, h, lid=True):
    E.box(x - w / 2, x + w / 2, y, y + d, z, z + h, "paint_teal", bevel=0.025)
    E.box(x - w / 2 - 0.03, x + w / 2 + 0.03, y - 0.03, y + d + 0.03, z + h * 0.42, z + h * 0.5, "paint_teal_dark", bevel=0.012)
    E.box(x - w * 0.22, x + w * 0.22, y - 0.012, y + 0.02, z + 0.06, z + 0.115, "black", bevel=0.01)
    E.slab(E.hex_pts(x, z + h * 0.74, 0.085), y - 0.02, y + 0.01, "brass", bevel=0.012)
    if lid:
        E.box(x - w / 2 - 0.06, x + w / 2 + 0.06, y - 0.06, y + d + 0.06, z + h, z + h + 0.09, "wood", bevel=0.025)
    return z + h


t1 = hive_box(4.75, 1.45, G, 0.95, 0.75, 0.6, lid=False)
hive_box(4.8, 1.5, t1, 0.9, 0.7, 0.55)
hive_box(5.75, 1.25, G, 0.8, 0.65, 0.5)
E.gshadow(5.1, 1.7, 1.1, 0.5, G)
# Sonnenuhr: Steinsockel, Messingscheibe mit Zeiger
sx_, sy_ = 3.35, 0.95
E.prism([(sx_ + 0.36 * math.cos(math.pi / 3 * k), sy_ + 0.36 * math.sin(math.pi / 3 * k)) for k in range(6)], G, G + 0.14, "stone_dark", bevel=0.025)
E.lathe([(0.22, 0.0), (0.16, 0.08), (0.14, 0.62), (0.24, 0.7), (0.24, 0.76)], (sx_, sy_, G + 0.14), "stone", seg=6)
E.cyl(sx_, sy_, G + 0.9, G + 0.95, 0.42, "brass", seg=32, bevel=0.012)
E.cyl(sx_, sy_, G + 0.95, G + 0.955, 0.33, "paint_cream", seg=32, nl=True)
for k in range(12):
    a = 2 * math.pi * k / 12
    E.ball((sx_ + 0.37 * math.cos(a), sy_ + 0.37 * math.sin(a), G + 0.955), 0.022, "brass_dark", seg=6, nl=True)
E.slab([(sx_ - 0.24, G + 0.955), (sx_ + 0.2, G + 0.955), (sx_ + 0.2, G + 1.3)], sy_ - 0.012, sy_ + 0.012, "brass_dark", bevel=0.004, seg=1)
E.gshadow(sx_, sy_, 0.42, 0.32, G)
# Fernrohr auf Dreibein (links neben der Bluete, schaut ueber das Land)
tx, ty = -0.75, 1.3
for a in (math.radians(90), math.radians(210), math.radians(330)):
    E.tube([(tx, ty, G + 1.15), (tx + 0.42 * math.cos(a), ty + 0.42 * math.sin(a), G)], 0.03, "wood", seg=8, r1=0.022)
E.ball((tx, ty, G + 1.17), 0.07, "brass_dark", seg=12)
tdir = Vector((-0.75, 0.25, 0.42)).normalized()
tc = Vector((tx, ty, G + 1.27))
E.tube([tc - tdir * 0.5, tc + tdir * 0.25], 0.07, "brass", seg=14, cap=False)
E.tube([tc + tdir * 0.25, tc + tdir * 0.7], 0.085, "brass", seg=14, cap=False)
E.tube([tc + tdir * 0.68, tc + tdir * 0.74], 0.098, "brass_dark", seg=14, cap=False)
E.tube([tc - tdir * 0.62, tc - tdir * 0.5], 0.05, "brass_dark", seg=12, cap=False)
E.gshadow(tx, ty, 0.42, 0.3, G, 0.26)
# Blumenkuebel (gestrichenes Holz mit Messingreifen), Giesskanne
E.lathe([(0.36, 0.0), (0.44, 0.52), (0.46, 0.54), (0.46, 0.6), (0.4, 0.6)], (POT[0], POT[1], G), "paint_teal", seg=28)
E.cyl(POT[0], POT[1], G + 0.54, G + 0.585, 0.4, "wood_dark", seg=28)
for hz in (0.12, 0.4):
    E.torus((POT[0], POT[1], G + hz), 0.375 + 0.15 * hz, 0.02, "brass", axis="z", seg=28, ring=6)
E.gshadow(POT[0], POT[1], 0.5, 0.36, G)
cx, cy = 2.15, 0.25
E.lathe([(0.17, 0.0), (0.2, 0.04), (0.2, 0.32), (0.15, 0.36)], (cx, cy, G), "brass", seg=20)
E.tube([(cx + 0.18, cy, G + 0.1), (cx + 0.42, cy, G + 0.34), (cx + 0.5, cy, G + 0.36)], 0.03, "brass", seg=8, sm=4)
E.lathe([(0.03, 0.0), (0.07, 0.05)], (cx + 0.5, cy, G + 0.36), "brass_dark", seg=10, axis="x")
E.torus((cx - 0.2, cy, G + 0.2), 0.11, 0.022, "brass_dark", seg=16, ring=6, axis="y")
E.gshadow(cx + 0.05, cy, 0.3, 0.2, G, 0.3)
# Wimpelkette von der Kuppel zum Gelaender rechts
A, B = Vector((DOME[0] + 1.14, DOME[1] - 1.52, G + 2.5)), Vector((6.2, YR + 0.08, G + 1.9))
line = [A + (B - A) * t + Vector((0, 0, -1.25 * math.sin(math.pi * t))) for t in [i / 40 for i in range(41)]]
E.tube(line, 0.012, "rope", seg=5, cap=False)
E.cyl(6.2, YR + 0.08, G + 0.07, G + 1.95, 0.04, "wood_dark", seg=8)
for k in range(13):
    p0, p1 = line[2 + k * 3], line[4 + k * 3]
    mid_ = (p0 + p1) / 2
    E.face([p0, p1, (mid_.x, mid_.y - 0.01, mid_.z - 0.3)], "awn_a" if k % 2 == 0 else "awn_b")

E.render_bg("deck_bg")

# ------------------------------------------------------------------ Ebenen
E.clear()                                               # Stiel mit Blaettern, Anker = Erde
stem = [S0, (S0[0] - 0.06, S0[1], S0[2] + 0.6), (S0[0] + 0.08, S0[1] - 0.02, S0[2] + 1.25), (S1[0], S1[1] + 0.05, S1[2] - 0.08)]
E.tube(stem, 0.05, "leaf", seg=10, sm=8, r1=0.035)
for sx, hz, ln in ((-1, 0.55, 0.62), (1, 0.95, 0.5)):
    bx = S0[0] + (-0.05 if sx < 0 else 0.03)

    def leaf(u, v, sx=sx, hz=hz, ln=ln, bx=bx):
        w = 0.17 * math.sin(math.pi * min(1.0, v)) ** 0.7
        return (bx + sx * (v * ln), S0[1] - 0.05 + (u - 0.5) * 2 * w * 0.9 - 0.1 * v, S0[2] + hz + 0.3 * math.sin(v * 2.2) + abs(u - 0.5) * 0.12)
    E.sheet(leaf, 8, 14, "leaf", thick=0.012)
m_stem = E.render_layer("deck_stem", pivot=S0)

E.clear()                                               # Bluete, Anker = Mitte
C = Vector(S1)
for ring, (n, rad, ln, wd, col, tint) in enumerate(((14, 0.4, 0.26, 0.105, "petal_pink", (1.0, 1.0, 1.0)), (14, 0.27, 0.2, 0.09, "petal_white", (1.0, 0.94, 0.95)))):
    for k in range(n):
        a = 2 * math.pi * (k + 0.5 * ring) / n
        d = math.cos(a) * E1 + math.sin(a) * E2
        ac = EN.cross(d)
        rot = Matrix((d, ac, EN)).transposed()
        E.ellipsoid(C + d * rad + EN * (0.03 + 0.05 * ring), (ln, wd, 0.035), col, seg=16, rot=rot, tint=tint)
E.ellipsoid(C + EN * 0.1, (0.2, 0.2, 0.1), "pollen", seg=24, rot=Matrix((E1, E2, EN)).transposed())
for k in range(14):
    a = 2.4 * k
    r = 0.035 * math.sqrt(k + 0.5)
    E.ball(C + (math.cos(a) * E1 + math.sin(a) * E2) * r + EN * (0.19 - 0.25 * r * r / 0.2), 0.022, "honey_deep", seg=6, nl=True)
m_flower = E.render_layer("deck_flower", pivot=S1)

E.clear()                                               # Honigtropfen, Anker = Aufhaengung oben
E.lathe([(0.0, -0.3), (0.07, -0.275), (0.1, -0.2), (0.085, -0.12), (0.04, -0.04), (0.012, 0.0)], (0, 0, 0), "honey", seg=18)
E.ellipsoid((-0.035, -0.09, -0.17), (0.02, 0.01, 0.035), "white", seg=8, lit=False, nl=True)
E.render_layer("deck_drop", pivot=(0, 0, 0))

E.clear()                                               # Honigklecks auf dem Deck, Anker = Mitte
pts = [(0.3 * (1 + 0.22 * math.sin(3 * a) + 0.12 * math.sin(5 * a + 1)) * math.cos(a), 0.2 * (1 + 0.22 * math.sin(3 * a) + 0.12 * math.sin(5 * a + 1)) * math.sin(a))
       for a in [2 * math.pi * i / 36 for i in range(36)]]
E.prism(pts, 0.0, 0.035, "honey", bevel=0.02)
E.prism([(x * 0.4 - 0.06, y * 0.35 + 0.04) for x, y in pts], 0.035, 0.04, "honey_light", nl=True, lit=False)
E.render_layer("deck_splat", pivot=(0, 0, 0), pad=0.03)

for i, (s, seed) in enumerate(((1.15, 5), (0.85, 8), (0.7, 11))):     # ziehende Wolken
    E.clear()
    cloud(0, 0, s, 0.0, seed)
    E.render_layer(f"deck_cloud{i}", line=0.02, inner=0.009)

E.clear()                                               # Wimpel am Mast, Anker = Mast


def flag(u, v):
    return (u * 0.95, 0.05 * math.sin(u * 7.0) * u, (0.5 - v) * 0.5 * (1 - u * 0.92) - 0.06 * u + 0.04 * math.sin(u * 7.0) * u)


E.sheet(flag, 20, 6, "awn_a", thick=0.01)
E.render_layer("deck_flag", pivot=(0, 0, 0))

TIPI = E.img(*TIP)
E.note("deck_pts", stem=list(E.img(*S0)), flower=list(E.img(*S1)), tip=[TIPI[0], TIPI[1]], splat=list(E.img(TIP.x, TIP.y, G)),
       land=list(E.img(S1[0] - 0.02, S1[1], S1[2] + 0.36)), flag=list(E.img(FLAG[0] + 0.03, FLAG[1], FLAG[2])), sun=list(SUN), deck=G,
       door=list(E.img(VX, VY, G + 0.8)))
