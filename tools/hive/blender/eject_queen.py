# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_queen.py - Skip "Die Koenigin gaehnt" (hive_skip_queen), Stil V2: Thronsaal mit fliederfarbenem Wabenboden, violettem
# Laeufer, Wachsstufen, Wabenthron (Nussholz, Pflaumen-Anstrich, Messing), Samtvorhaengen und Kerzenleuchtern.
# Die Koenigin ist als Figur modelliert (Hinterleib, Pelz, Hermelinkragen, Umhang, Zepter) und in Teilen gerendert:
# queen_body, queen_arm (winkt), queen_wing, queen_head_awake / _yawn / _sleep, queen_crown, dazu queen_snot, queen_z,
# queen_flame (Kerzen), queen_fan (Faecher des Dieners) und queen_bg.jpg.
#   blender -b --factory-startup -P eject_queen.py

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eject_common as E  # noqa: E402

G = -2.45                # Boden
YW = 3.0                 # Rueckwand
Z1 = G + 0.44            # Oberkante der zweiten Stufe
ZS = Z1 + 0.66           # Sitzflaeche (Kissen)
YQ = 2.05                # Tiefe der Koenigin
HEAD = (0.0, YQ - 0.12, ZS + 1.78)       # Kopfmitte
HR = 0.47                # Kopfradius
NECK = (0.0, YQ - 0.1, ZS + 1.36)
HS = 1.16                # Vergroesserung des Kopfes um den Hals
SHOULDER = (0.44, YQ - 0.22, ZS + 1.16)
CANDLE = [(sx * 3.35 + dx, 1.0, G + hz) for sx in (-1, 1) for dx, hz in ((-0.42, 2.3), (0.0, 2.62), (0.42, 2.3))]

E.reset()
rnd = random.Random(21)


# ------------------------------------------------------------------ Hintergrund
def wall_tint(u, v):
    zi = v + E.KZ * YW
    k = 0.56 + 0.5 * E.smooth01((zi + 1.55) / 3.4)
    d = math.hypot(u, (zi - 0.6) * 0.8)
    w = max(0.0, 1 - d / 3.4) * 0.2                                    # hinter dem Thron heller
    side = 1.0 - 0.25 * E.smooth01((abs(u) - 2.6) / 3.2)
    return (k * side * (1 + w), k * side * (1 + w * 0.8), k * side * (1 + w * 0.3))


cells = E.hex_grid(-6.8, G, 6.8, E.zat(3.6, YW), 0.34)
E.panel(-6.9, G, 6.9, E.zat(3.6, YW), YW + 0.07, "wall_front_b", nx=24, nz=12, nl=True, tintfn=lambda co: wall_tint(co.x, co.z))
E.hexfield(cells, 0.34, E.wall_place(YW), ["wall_front:wax", "wall_front:wax", "wall_front_b", "comb"],
           pick=lambda i, u, v: rnd.choice([1, 1, 1, 1, 2, 2, 3]), tintfn=wall_tint, var=0.05, depth=0.06)
GLOW = []
for i, (u, v) in enumerate(cells):                                        # Leuchtzellen als Bogen um den Thron
    zi = v + E.KZ * YW
    d = math.hypot(u, (zi + 0.6) * 0.72)
    if 2.2 < d < 2.62 and zi > -0.9 and i % 3 != 1:
        E.slab(E.hex_pts(u, v, 0.25), YW + 0.015, YW + 0.06, "wall_glow", lit=False, nl=True)
        E.halo(u, v, 0.6, YW - 0.01, "glow", 0.4)
        GLOW.append([round(u, 3), round(zi, 3)])
E.box(-6.9, 6.9, YW - 0.07, YW + 0.02, G, G + 0.2, "wall_base", bevel=0.025)

# Boden: fliederfarbene Sechsecke mit violetten Akzentringen um den Thron (wie auf der Karte), Fuge darunter
polys, accent = [], []
for cx, cy in E.hex_grid(-6.9, -3.3, 6.9, YW, 0.46):
    d = math.hypot(cx, cy - 1.9)
    pl = [(cx + 0.46 * math.cos(math.pi / 3 * k), cy + 0.46 * math.sin(math.pi / 3 * k)) for k in range(6)]
    (accent if int(d / 0.95) % 3 == 2 and int((math.atan2(cy - 1.9, cx) + 7) * 6 / math.pi) % 2 == 0 else polys).append(pl)
FL = [(0, 1, YW), (0, -1, 3.3), (1, 0, 6.9), (-1, 0, 6.9)]
E.tiles(polys, G, ["fl_lilac", "fl_lilac", "fl_lilac_b"], planes=FL, base=[(-6.9, -3.3), (6.9, -3.3), (6.9, YW), (-6.9, YW)], var=0.045,
        tintfn=lambda x, y: (0.9 + 0.1 * E.smooth01((1.2 - y) / 4.0),) * 3)
E.tiles(accent, G, ["fl_violet"], planes=FL, base=[], var=0.04)
E.fade(-6.9, 6.9, YW - 0.07, YW - 0.75, E.PLUM, 0.34, plane="floor", at=G + 0.03)

# Stufen aus Wachs, violetter Laeufer mit Messingkante
S1 = [(-2.4, 0.85), (2.4, 0.85), (2.85, 1.3), (2.85, YW), (-2.85, YW), (-2.85, 1.3)]
S2 = [(-1.75, 1.22), (1.75, 1.22), (2.2, 1.67), (2.2, YW), (-2.2, YW), (-2.2, 1.67)]
E.soft([(-2.5, 0.7), (2.6, 0.7), (3.05, 1.2), (3.05, 2.6), (-2.9, 2.6), (-2.9, 1.2)], 0.3, E.PLUM, 0.3, plane="floor", at=G + 0.004)
E.prism(S1, G, G + 0.22, "wax", bevel=0.035)
E.prism(S2, G + 0.22, Z1, "wax_light", bevel=0.035)
for (xa, xb, col, dz) in ((-0.82, 0.82, "fl_inlay", 0.0), (-0.7, 0.7, "royal", 0.004)):
    E.box(xa, xb, -3.3, 0.85, G + 0.004 + dz, G + 0.014 + dz, col, nl=True)
    E.box(xa, xb, 0.845 - dz, 0.86, G, G + 0.228 + dz, col, nl=True)
    E.box(xa, xb, 0.85, 1.22, G + 0.22, G + 0.228 + dz, col, nl=True)
    E.box(xa, xb, 1.215 - dz, 1.23, G + 0.22, Z1 + 0.008 + dz, col, nl=True)
    E.box(xa, xb, 1.22, YQ - 0.5, Z1, Z1 + 0.008 + dz, col, nl=True)
for k in range(8):                                       # eingewebte Waben im Laeufer
    E.prism([(0.2 * math.cos(math.pi / 3 * j), -2.9 + k * 0.46 + 0.2 * math.sin(math.pi / 3 * j)) for j in range(6)],
            G + 0.018, G + 0.021, "royal_light", nl=True)

# Thron: Sockel mit Pflaumen-Anstrich, Samtkissen, Nussholz-Armlehnen mit Messingknaeufen, Wabenlehne im Spitzbogen
TY0, TY1 = YQ - 0.5, YQ + 0.45
E.box(-0.86, 0.86, TY0, TY1, Z1, ZS - 0.13, "paint_plum", bevel=0.035)
E.box(-0.62, 0.62, TY0 - 0.02, TY0 + 0.02, Z1 + 0.1, ZS - 0.24, "royal_dark", bevel=0.015)
E.slab(E.hex_pts(0, (Z1 + ZS) / 2 - 0.03, 0.13), TY0 - 0.05, TY0 - 0.01, "brass", bevel=0.015)
E.box(-0.78, 0.78, TY0 - 0.03, TY1 - 0.05, ZS - 0.15, ZS, "royal", bevel=0.065, seg=3)
for sx in (-1, 1):
    E.box(sx * 0.86 - 0.02 if sx > 0 else -1.2, 1.2 if sx > 0 else sx * 0.86 + 0.02, TY0 - 0.06, TY1, Z1, ZS + 0.42, "wood", bevel=0.04)
    E.box(sx * 1.03 - 0.2, sx * 1.03 + 0.2, TY0 - 0.1, TY1, ZS + 0.42, ZS + 0.5, "wood_dark", bevel=0.03)
    E.ball((sx * 1.03, TY0 - 0.06, ZS + 0.58), 0.12, "brass", seg=20)
    E.slab(E.hex_pts(sx * 1.03, Z1 + 0.55, 0.11), TY0 - 0.085, TY0 - 0.05, "brass", bevel=0.012)
BY = TY1                                                # Lehne
back = [(-1.3, Z1), (1.3, Z1), (1.3, ZS + 1.75)] + [(1.3 * math.cos(a), ZS + 1.75 + 1.25 * math.sin(a) ** 0.8) for a in
                                                     [math.pi * i / 16 for i in range(1, 16)]] + [(-1.3, ZS + 1.75)]
E.slab(back, BY, BY + 0.28, "wood_dark", bevel=0.05)
inner = [(x * 0.86, Z1 + 0.1 + (z - Z1 - 0.1) * 0.93) for x, z in back]
E.slab(inner, BY - 0.02, BY + 0.05, "paint_plum", bevel=0.02)
tc = [(u, v) for u, v in E.hex_grid(-1.0, ZS + 0.3, 1.0, ZS + 2.9, 0.2)
      if abs(u) < 0.95 and (v < ZS + 1.7 or (u / 1.0) ** 2 + ((v - ZS - 1.7) / 1.05) ** 2 < 1.0)]
E.hexfield(tc, 0.2, E.wall_place(BY - 0.03), ["brass", "comb", "wax", "honey", "wax_light"], pick=lambda i, u, v: rnd.choice([1, 1, 2, 3, 4]),
           depth=0.035, inset=0.84, inner=0.7, var=0.06, nl=False)
for sx in (-1, 1):
    E.lathe([(0.1, 0.0), (0.13, 0.08), (0.06, 0.16), (0.1, 0.26), (0.0, 0.4)], (sx * 1.3, BY + 0.14, ZS + 1.75), "brass", seg=16)
E.lathe([(0.12, 0.0), (0.16, 0.06), (0.08, 0.14), (0.14, 0.3), (0.0, 0.5)], (0, BY + 0.14, ZS + 2.98), "brass", seg=16)
E.ball((0, BY + 0.14, ZS + 3.2), 0.085, "royal_light", seg=14)
E.wshadow(0, ZS + 1.3, 1.3, 1.7, YW, 0.26, dx=0.22, dz=-0.1)
E.gshadow(0, YQ, 1.35, 0.6, Z1, 0.3)

# Amphoren mit Blumen neben dem Thron
for sx in (-1, 1):
    ax, ay = sx * 2.3, 2.35
    E.lathe([(0.16, 0.0), (0.2, 0.04), (0.3, 0.3), (0.32, 0.5), (0.22, 0.78), (0.14, 0.88), (0.19, 0.98), (0.15, 0.98)], (ax, ay, G + 0.22),
            ["wax_light", "paint_plum"], seg=28, matfn=lambda i, r, h: 1 if i in (2, 3) else 0)
    for k, (dx, hh, col) in enumerate(((-0.14, 0.42, "petal_pink"), (0.12, 0.5, "petal_white"), (0.0, 0.64, "petal_pink"), (-0.05, 0.3, "petal_white"))):
        E.tube([(ax + dx * 0.3, ay, G + 1.18), (ax + dx, ay - 0.04, G + 1.2 + hh)], 0.018, "leaf", seg=6)
        for j in range(6):
            a = math.pi / 3 * j
            E.ellipsoid((ax + dx + 0.085 * math.cos(a), ay - 0.07, G + 1.2 + hh + 0.085 * math.sin(a)), (0.06, 0.02, 0.06), col, seg=10)
        E.ball((ax + dx, ay - 0.1, G + 1.2 + hh), 0.045, "pollen", seg=10)
    E.gshadow(ax, ay, 0.3, 0.2, G + 0.22, 0.3)

# Samtvorhaenge links und rechts (gerafft), Schabracke mit Messingstange oben
CT = E.zat(3.02, YW - 0.4)


def curtain(sx):
    hgt = CT - G - 0.05

    def fn(u, v):
        pinch = 1.0 - 0.62 * math.exp(-((v - 0.52) / 0.2) ** 2)
        x = sx * (6.3 - 3.2 * u * pinch)
        y = YW - 0.4 + 0.11 * math.sin(u * 19.0) * (0.5 + 0.5 * pinch) - 0.1 * u
        return (x, y, CT - v * hgt - 0.12 * math.sin(u * math.pi) * (1 - pinch))
    E.sheet(fn, 60, 40, "royal", tintfn=lambda co: (0.82 + 0.25 * E.smooth01((co.z - G) / 4.0),) * 3)
    tz = CT - 0.52 * hgt
    E.torus((sx * 5.45, YW - 0.47, tz), 0.36, 0.045, "brass", seg=28, ring=8, axis="z", scale=(1.6, 0.45))
    E.tube([(sx * 4.95, YW - 0.62, tz), (sx * 4.9, YW - 0.66, tz - 0.25), (sx * 4.95, YW - 0.66, tz - 0.55)], 0.03, "brass", seg=8, sm=4)
    E.lathe([(0.02, 0.0), (0.09, -0.06), (0.07, -0.3), (0.1, -0.34)], (sx * 4.95, YW - 0.66, tz - 0.55), "brass_dark", seg=12)
    E.fade(sx * 6.9, sx * 3.0, YW - 0.5, YW - 1.2, E.PLUM, 0.3, plane="floor", at=G + 0.03)


curtain(-1)
curtain(1)


def scallop(x):
    return 0.62 + 0.42 * abs(math.sin(x * math.pi / 2.3))


def valance(u, v):
    x = -6.9 + 13.8 * u
    return (x, YW - 0.85 + 0.07 * math.sin(x * 9.0), E.zat(3.5, YW - 0.85) - v * scallop(x))


E.sheet(valance, 120, 6, "royal_dark")
E.tube([(-6.9 + 13.8 * i / 120, YW - 0.93, E.zat(3.5, YW - 0.85) - scallop(-6.9 + 13.8 * i / 120)) for i in range(121)], 0.035, "brass",
       seg=6, cap=False)                                # Messingborte am Saum

# Kerzenleuchter (Messing) mit Wachskerzen, die Flammen sind eigene Bilder
for sx in (-1, 1):
    cx, cy = sx * 3.35, 1.0
    E.lathe([(0.34, 0.0), (0.34, 0.05), (0.2, 0.12), (0.07, 0.2), (0.05, 0.9), (0.1, 0.96), (0.05, 1.04), (0.045, 1.8), (0.1, 1.86),
             (0.05, 1.94), (0.04, 2.3), (0.12, 2.36), (0.12, 2.4)], (cx, cy, G), "brass", seg=20)
    for dx in (-0.42, 0.42):
        E.tube([(cx, cy, G + 1.86), (cx + dx * 0.5, cy, G + 1.7), (cx + dx, cy, G + 1.86), (cx + dx, cy, G + 2.06)], 0.03, "brass", seg=8, sm=5)
        E.lathe([(0.04, 0.0), (0.11, 0.05), (0.11, 0.08)], (cx + dx, cy, G + 2.04), "brass", seg=14)
    for (dx, dy, hz) in ((-0.42, 0.0, 2.3), (0.0, -0.06, 2.62), (0.42, 0.0, 2.3)):
        E.cyl(cx + dx, cy, G + (2.1 if dx else 2.4), G + hz - 0.02, 0.055, "wax_light", seg=12)
        E.tube([(cx + dx, cy, G + hz - 0.02), (cx + dx, cy, G + hz + 0.03)], 0.008, "black", seg=4, cap=False)
    E.gshadow(cx, cy, 0.36, 0.26, G, 0.32)

E.render_bg("queen_bg")


# ------------------------------------------------------------------ Koenigin
def body():
    # Umhang: faellt von den Schultern ueber die Armlehnen
    def cape(u, v):
        w = 0.5 + 0.72 * E.smooth01(v * 1.2)
        x = (u * 2 - 1) * w
        return (x, YQ + 0.22 - 0.25 * v * abs(u * 2 - 1) + 0.05 * math.sin(u * 22.0) * v, ZS + 1.36 - v * 1.3 - 0.12 * (u * 2 - 1) ** 2)
    E.sheet(cape, 40, 16, "royal", tintfn=lambda co: (0.85 + 0.2 * E.smooth01((co.z - ZS) / 1.3),) * 3)
    for sx in (-1, 1):                                    # Hermelinsaum
        for k in range(9):
            v = k / 8
            w = 0.5 + 0.72 * E.smooth01(v * 1.2)
            E.ball((sx * w, YQ - 0.03 - 0.25 * v, ZS + 1.24 - v * 1.3), 0.085, "fur", seg=10)
    # Beine mit Samtpantoffeln
    for sx in (-1, 1):
        E.tube([(sx * 0.27, YQ - 0.45, ZS - 0.02), (sx * 0.3, YQ - 0.62, ZS - 0.1), (sx * 0.31, YQ - 0.66, ZS - 0.5)], 0.06, "bee_black", seg=10, sm=4)
        E.ellipsoid((sx * 0.32, YQ - 0.76, ZS - 0.56), (0.13, 0.2, 0.1), "royal", seg=16)
        E.ball((sx * 0.32, YQ - 0.95, ZS - 0.52), 0.05, "brass", seg=10)
    # Hinterleib: grosse gestreifte Kugel, ruht auf dem Kissen
    n = 26
    prof = [(0.66 * math.sqrt(max(0.0, 1 - (-1 + 2 * i / n) ** 2)) * (0.92 + 0.08 * (-1 + 2 * i / n)), 0.56 * (2 * i / n)) for i in range(n + 1)]

    def stripes(i, r, h):
        t = (i + 0.5) / n
        return 1 if t < 0.1 or 0.26 < t < 0.42 or 0.58 < t < 0.74 else 0
    E.lathe(prof, (0, YQ - 0.3, ZS - 0.08), ["bee_yellow", "bee_black"], seg=40, matfn=stripes, scale=(1.0, 0.92),
            M=E.about(E.R("X", 16), (0, YQ - 0.3, ZS + 0.5)))
    # Brust im Pelz, Hermelinkragen mit schwarzen Tupfen, Messing-Medaillon
    E.ellipsoid((0, YQ - 0.14, ZS + 0.98), (0.47, 0.4, 0.44), "bee_yellow", seg=36, tint=(1.0, 0.86, 0.62))
    for k in range(11):
        a = math.radians(-200 + 22 * k)
        px, py = 0.36 * math.cos(a), YQ - 0.16 + 0.3 * math.sin(a)
        E.ball((px, py, ZS + 1.3 - 0.05 * math.sin(a)), 0.13, "fur", seg=14)
        if k % 2 == 0:
            E.ball((px * 1.08, py - 0.11, ZS + 1.3 - 0.05 * math.sin(a)), 0.028, "black", seg=8)
    E.slab(E.hex_pts(0, ZS + 1.02, 0.1), YQ - 0.58, YQ - 0.53, "brass", bevel=0.015)
    E.ball((0, YQ - 0.6, ZS + 1.02), 0.04, "royal_light", seg=10)
    # mittlere Arme, im Schoss gefaltet
    for sx in (-1, 1):
        E.tube([(sx * 0.36, YQ - 0.4, ZS + 0.82), (sx * 0.34, YQ - 0.62, ZS + 0.66), (sx * 0.1, YQ - 0.78, ZS + 0.62)], 0.055, "bee_black", seg=10, sm=4)
        E.ball((sx * 0.07, YQ - 0.8, ZS + 0.62), 0.085, "white", seg=14)
    # linker Arm (im Bild links) haelt das Zepter
    hx, hy, hz = -0.86, YQ - 0.52, ZS + 0.98
    E.tube([(-SHOULDER[0], SHOULDER[1], SHOULDER[2]), (-0.74, YQ - 0.32, ZS + 0.82), (hx + 0.02, hy + 0.06, hz - 0.04)], 0.065, "bee_black", seg=10, sm=5)
    E.tube([(hx, hy, Z1 + 0.02), (hx, hy, ZS + 1.72)], 0.032, "brass", seg=10)
    E.lathe([(0.03, 0.0), (0.075, 0.03), (0.03, 0.06)], (hx, hy, ZS + 1.36), "brass_dark", seg=12)
    E.lathe([(0.03, 0.0), (0.07, 0.04), (0.07, 0.07)], (hx, hy, Z1), "brass_dark", seg=12)
    E.ball((hx, hy, ZS + 1.88), 0.15, "honey", seg=20)                                 # Honigtropfen als Knauf
    E.torus((hx, hy, ZS + 1.88), 0.155, 0.022, "brass", seg=24, ring=6, axis="y")
    E.lathe([(0.05, 0.0), (0.07, 0.03), (0.0, 0.14)], (hx, hy, ZS + 2.03), "brass", seg=10)
    E.ball((hx, hy - 0.03, hz), 0.105, "white", seg=14)


def arm():
    """Rechter Arm (im Bild rechts), ruht auf der Armlehne; Anker = Schulter."""
    E.tube([SHOULDER, (0.74, YQ - 0.32, ZS + 0.9), (0.96, YQ - 0.5, ZS + 0.66)], 0.065, "bee_black", seg=10, sm=5)
    E.ball((0.99, YQ - 0.54, ZS + 0.64), 0.115, "white", seg=16)
    for k, (dx, dz) in enumerate(((0.1, 0.02), (0.1, -0.05), (0.05, -0.1))):
        E.ellipsoid((0.99 + dx, YQ - 0.58, ZS + 0.64 + dz), (0.05, 0.045, 0.04), "white", seg=10)
    E.torus((0.9, YQ - 0.46, ZS + 0.72), 0.075, 0.022, "brass", seg=14, ring=6, axis="y", M=E.about(E.R("Y", 42), (0.9, YQ - 0.46, ZS + 0.72)))


def face_pt(x, z, lift=0.0):
    """Punkt auf der Kopfkugel vorn (x, z relativ zur Kopfmitte)."""
    d = math.sqrt(max(0.0, HR * HR - x * x - z * z))
    return (HEAD[0] + x, HEAD[1] - d - lift, HEAD[2] + z)


def head(expr):
    E.XF[0] = E.about(E.Matrix.Scale(HS, 4), NECK)       # Kopf etwas groesser als modelliert (Ausdruck lesbar)
    _head(expr)
    E.XF[0] = None


def _head(expr):
    E.ellipsoid(HEAD, (HR, HR * 0.95, HR * 0.97), "bee_black", seg=40)
    E.ellipsoid((HEAD[0], HEAD[1] - 0.2, HEAD[2] - 0.12), (0.34, 0.3, 0.3), "bee_black", seg=24)       # Schnauze
    for sx in (-1, 1):                                    # Fuehler
        if expr == "sleep":
            pts = [(sx * 0.2, 0.0, 0.4), (sx * 0.42, -0.04, 0.6), (sx * 0.68, -0.06, 0.52), (sx * 0.78, -0.06, 0.32)]
        elif expr == "yawn":
            pts = [(sx * 0.2, 0.0, 0.4), (sx * 0.3, -0.04, 0.72), (sx * 0.42, -0.06, 0.95), (sx * 0.62, -0.06, 1.0)]
        else:
            pts = [(sx * 0.2, 0.0, 0.4), (sx * 0.34, -0.04, 0.68), (sx * 0.56, -0.06, 0.82), (sx * 0.74, -0.06, 0.72)]
        pts = [(HEAD[0] + a, HEAD[1] + b, HEAD[2] + c) for a, b, c in pts]
        E.tube(pts, 0.03, "bee_black", seg=8, sm=5)
        E.ball(pts[-1], 0.07, "bee_black", seg=14)
        # Augen
        ex, ez = sx * 0.2, 0.07
        E.ellipsoid(face_pt(ex, ez, 0.0), (0.15, 0.06, 0.18), "white", seg=24, lit=False)
        if expr == "awake":                               # gelangweilt: Lider halb zu, Blick zur Seite
            E.ellipsoid(face_pt(ex + 0.04, ez - 0.05, 0.05), (0.07, 0.03, 0.085), "black", seg=16)
            E.ball(face_pt(ex + 0.065, ez - 0.02, 0.085), 0.022, "white", seg=8, lit=False)
            E.ellipsoid(face_pt(ex, ez + 0.1, 0.03), (0.17, 0.07, 0.12), "royal_light", seg=24)
            lash_z, curve = ez + 0.0, -0.02
        else:
            E.ellipsoid(face_pt(ex, ez, 0.03), (0.165, 0.07, 0.19), "royal_light", seg=24)
            lash_z, curve = (ez - 0.06, 0.07) if expr == "yawn" else (ez - 0.1, -0.06)
        if expr != "awake":                               # geschlossenes Auge: Wimpernlinie
            lash = [face_pt(ex + dx, lash_z + curve * (1 - (dx / 0.15) ** 2), 0.085) for dx in (-0.15, -0.075, 0.0, 0.075, 0.15)]
            E.tube(lash, 0.016, "black", seg=6, sm=3, nl=True)
        for k in range(3):                                # Wimpern aussen
            a = math.radians(20 + 28 * k)
            p0 = face_pt(ex + sx * 0.13, lash_z + 0.01 + k * 0.03, 0.08)
            E.tube([p0, (p0[0] + sx * 0.1 * math.cos(a), p0[1] - 0.01, p0[2] + 0.1 * math.sin(a))], 0.014, "black", seg=5, r1=0.005, nl=True)
        E.ellipsoid(face_pt(sx * 0.3, -0.14, 0.02), (0.085, 0.03, 0.055), "blush", seg=14, lit=False, nl=True)
        if expr == "yawn":                                # Braue hochgezogen
            E.tube([face_pt(ex - sx * 0.12, ez + 0.3, 0.02), face_pt(ex, ez + 0.34, 0.02), face_pt(ex + sx * 0.12, ez + 0.28, 0.02)], 0.018,
                   "royal_light", seg=6, sm=3, nl=True)
    my = HEAD[1] - 0.5
    if expr == "awake":                                   # Schmollmund
        E.tube([(-0.09, my, HEAD[2] - 0.25), (0.0, my - 0.01, HEAD[2] - 0.215), (0.09, my, HEAD[2] - 0.25)], 0.024, "coral", seg=8, sm=4)
    elif expr == "yawn":                                  # weit offen: Rachen, Zunge, zwei Zaehnchen
        E.ellipsoid((0, my + 0.03, HEAD[2] - 0.22), (0.2, 0.06, 0.25), "mouth", seg=24, lit=False)
        E.torus((0, my + 0.0, HEAD[2] - 0.22), 0.2, 0.026, "coral", seg=28, ring=6, axis="y", scale=(1.0, 1.25))
        E.ellipsoid((0, my - 0.03, HEAD[2] - 0.34), (0.12, 0.03, 0.09), "tongue", seg=16)
        for sx in (-1, 1):
            E.box(sx * 0.07 - 0.035, sx * 0.07 + 0.035, my - 0.04, my - 0.01, HEAD[2] - 0.06, HEAD[2] + 0.0, "white", bevel=0.012, nl=True)
    else:                                                 # schlaeft: kleiner offener Mund
        E.ellipsoid((0.02, my + 0.03, HEAD[2] - 0.25), (0.05, 0.03, 0.06), "mouth", seg=14, lit=False)
        E.torus((0.02, my + 0.01, HEAD[2] - 0.25), 0.055, 0.018, "coral", seg=16, ring=6, axis="y", scale=(1.0, 1.2))


def crown():
    c = (0.0, 0.0, 0.0)
    E.lathe([(0.3, 0.0), (0.33, 0.03), (0.33, 0.1), (0.3, 0.13), (0.28, 0.13), (0.28, 0.0)], c, "brass", seg=40, caps=False)
    for k in range(10):
        a = 2 * math.pi * k / 10 + math.pi / 10
        big = k % 2 == 0
        px, py = 0.305 * math.cos(a), 0.305 * math.sin(a)
        E.lathe([(0.075, 0.0), (0.06, 0.1), (0.02, (0.34 if big else 0.22)), (0.0, (0.36 if big else 0.24))], (px, py, 0.1), "brass", seg=8)
        E.ball((px, py, 0.5 if big else 0.3), 0.045 if big else 0.032, "brass", seg=10)
        if py < 0.05:
            E.ball((px * 1.07, py * 1.07 - 0.01, 0.065), 0.04, ["royal_light", "red", "teal_light"][k % 3], seg=10)
    E.sheet(lambda u, v: (0.27 * math.cos(2 * math.pi * u) * (1 - 0.5 * v), 0.27 * math.sin(2 * math.pi * u) * (1 - 0.5 * v), 0.1 + 0.16 * math.sin(v * math.pi / 2)),
            24, 4, "royal")


# Koerper: Anker = Sitz (Mitte), daran haengen in der Szene Kopf, Arm und Fluegel
PIV = (0.0, YQ, ZS - 0.1)
E.clear()
body()
m_body = E.render_layer("queen_body", pivot=PIV)
E.clear()
arm()
E.render_layer("queen_arm", pivot=SHOULDER)
for expr in ("awake", "yawn", "sleep"):
    E.clear()
    head(expr)
    E.render_layer(f"queen_head_{expr}", pivot=NECK)
E.clear()
crown()
E.render_layer("queen_crown", pivot=(0, 0, 0))
E.clear()
E.wing(s=2.5)
E.render_layer("queen_wing", pivot=(0, 0, 0), line=0.02, inner=0.009)

# ------------------------------------------------------------------ Kleinteile
E.clear()                                               # Kerzenflamme, Anker = Docht
E.lathe([(0.0, 0.0), (0.06, 0.07), (0.07, 0.14), (0.045, 0.24), (0.0, 0.36)], (0, 0, 0), "flame", seg=14, lit=False)
E.lathe([(0.0, 0.0), (0.03, 0.05), (0.035, 0.1), (0.0, 0.2)], (0, -0.08, 0.03), "flame_core", seg=10, lit=False, nl=True)
E.render_layer("queen_flame", pivot=(0, 0, 0), line=0.016, inner=0.008)

E.clear()                                               # Rotzblase, Anker = Mitte
E.ball((0, 0, 0), 0.2, "glass", seg=28)
E.ellipsoid((-0.07, -0.17, 0.08), (0.05, 0.02, 0.035), "white", seg=10, lit=False, nl=True)
E.render_layer("queen_snot", pivot=(0, 0, 0), line=0.016, inner=0.008)

E.clear()                                               # Z
zp = [(-0.14, 0.17), (0.14, 0.17), (0.14, 0.1), (-0.04, -0.1), (0.14, -0.1), (0.14, -0.17), (-0.14, -0.17), (-0.14, -0.1), (0.04, 0.1), (-0.14, 0.1)]
E.slab(zp, 0.0, 0.08, "cloth_white", bevel=0.012)
E.render_layer("queen_z", pivot=(0, 0.04, 0))

E.clear()                                               # Faecher des Dieners: Blatt am Stiel, Anker = Stielende


def leaf(u, v):
    w = 0.3 * math.sin(math.pi * min(1.0, v * 1.02)) ** 0.75 * (1.0 - 0.25 * v)
    x = (u * 2 - 1) * w
    return (x, -0.05 * abs(u * 2 - 1) - 0.04 * math.sin(v * 3.0), 0.3 + v * 0.75)


E.sheet(leaf, 12, 20, "leaf", thick=0.012)
E.tube([(0, 0, 0), (0, -0.02, 0.5), (0, -0.05, 1.03)], 0.026, "leaf_dark", seg=8, r1=0.01)
for k in range(5):
    zz = 0.42 + k * 0.12
    for sx in (-1, 1):
        E.tube([(0, -0.035, zz), (sx * 0.2 * math.sin(math.pi * (zz - 0.3) / 0.78) ** 0.75, -0.075, zz + 0.1)], 0.009, "leaf_dark", seg=5, nl=True)
E.render_layer("queen_fan", pivot=(0, 0, 0))

E.note("queen_pts", seat=list(E.img(*PIV)), neck=list(E.img(*NECK)), shoulder=list(E.img(*SHOULDER)), head=list(E.img(*HEAD)),
       head_r=HR, crown=list(E.img(HEAD[0], HEAD[1], NECK[2] + (HEAD[2] + HR * 0.84 - NECK[2]) * HS)), wing=[list(E.img(sx * 0.42, YQ + 0.1, ZS + 1.22)) for sx in (-1, 1)],
       candles=[list(E.img(*c)) for c in CANDLE], glows=GLOW, mouth=list(E.img(0.05, HEAD[1] - 0.6, NECK[2] + (HEAD[2] - 0.25 - NECK[2]) * HS)), floor=G)
