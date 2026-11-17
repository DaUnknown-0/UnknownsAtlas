# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_swarm.py - Rauswurf "Schwarm" (hive_swarm), Stil V2: Kronensaal mit kuehlem Wabenboden, Petrol-Teppich,
# leuchtender Wachswand und der runden Kronenoeffnung in den Abendhimmel; vorne dunkle Wabenmasse als Rahmen.
# Erzeugt: swarm_bg.jpg, swarm_fg_l.png, swarm_fg_r.png, swarm_lamp.png (haengt, schaukelt), shadow.png,
# dazu die gemeinsamen Bienenbilder bee.png, wing.png, bee_far.png.
#   blender -b --factory-startup -P eject_swarm.py

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eject_common as E  # noqa: E402

G = -2.6                 # Boden (Spieler steht in Tiefe 0)
YW = 2.6                 # Rueckwand
OC = (0.9, 0.85)         # Mitte der Kronenoeffnung im Bild
OR = 1.6                 # Radius der Oeffnung
OZ = E.zat(OC[1], YW)    # Modellhoehe der Oeffnungsmitte
LAMPS = ((-2.45, 2.72), (3.75, 2.42))     # Aufhaengepunkte der Laternen im Bild

E.reset()
rnd = random.Random(7)


def arch(x):
    """Bildhoehe der Gewoelbekante ueber der Rueckwand."""
    return 3.05 - 0.045 * x * x


# ------------------------------------------------------------------ Hintergrund
def sky(x, z):
    t = (z - (OC[1] - OR)) / (2 * OR)
    c = E.ramp([(0.0, (0.99, 0.80, 0.50)), (0.28, (1.0, 0.70, 0.42)), (0.48, (0.97, 0.52, 0.47)), (0.72, (0.72, 0.38, 0.60)),
                (1.0, (0.36, 0.27, 0.56))], t)
    d = math.hypot(x - 1.55, z - 0.42)
    return E.mix(c, (1.0, 0.90, 0.62), max(0.0, 1 - d / 1.5) ** 2 * 0.75)


E.grad_plane(OC[0] - OR - 0.2, OC[1] - OR - 0.2, OC[0] + OR + 0.2, OC[1] + OR + 0.2, 60.0, sky, nx=40, nz=40)
E.slab(E.ell_pts(1.55, 0.42, 0.62, 0.62, 48), 58.0, 58.1, "sun_eve", lit=False, shear=False, nl=True, tint=(1.0, 0.95, 0.80))
E.slab(E.ell_pts(1.55, 0.42, 0.44, 0.44, 48), 57.0, 57.1, "sun", lit=False, shear=False, nl=True)
for k, (cx, cz, s) in enumerate(((0.05, 1.75, 1.0), (1.9, 1.35, 0.7), (-0.2, 0.75, 0.55))):      # Abendwolken
    for j, (dx, dz, r) in enumerate(((-0.42, 0.0, 0.2), (-0.15, 0.1, 0.28), (0.18, 0.06, 0.24), (0.45, -0.02, 0.17), (0.0, -0.06, 0.2))):
        E.ellipsoid((cx + dx * s, 50.0 + j * 0.01, cz + dz * s), (r * s * 1.25, 0.2, r * s), "cloud_eve", seg=24, shear=False,
                    tint=(1.0, 0.86, 0.86))
hill = [(-1.2, -1.2), (3.0, -1.2), (3.0, 0.05), (2.5, 0.12), (1.9, 0.02), (1.3, -0.06), (0.6, 0.08), (0.0, 0.2), (-0.5, 0.12), (-1.2, 0.02)]
E.slab(hill, 45.0, 45.1, "hill_eve_b", shear=False, nl=True, lit=False)
hill2 = [(-1.2, -1.2), (3.0, -1.2), (3.0, -0.3), (2.2, -0.16), (1.4, -0.3), (0.5, -0.2), (-0.2, -0.34), (-1.2, -0.22)]
E.slab(hill2, 44.0, 44.1, "hill_eve", shear=False, nl=True, lit=False)
for k, (tx, tz, r) in enumerate(((0.1, 0.28, 0.1), (0.3, 0.2, 0.07), (2.3, 0.18, 0.09), (-0.4, 0.2, 0.06))):   # ferne Baeume
    E.ellipsoid((tx, 44.5, tz), (r, 0.05, r * 1.25), "hill_eve", seg=12, shear=False, nl=True, lit=False)

# Rueckwand: Wachsstirn mit Wabenrelief, Fuss satt und dunkel, nach oben hell; rund um die Oeffnung waermer
def wall_tint(u, v):
    zi = v + E.KZ * YW
    t = E.smooth01((zi + 1.82) / 3.6)
    k = 0.58 + 0.52 * t
    d = math.hypot(u - OC[0], zi - OC[1])
    w = max(0.0, 1 - (d - OR) / 2.2) * 0.16
    side = 1.0 - 0.22 * E.smooth01((abs(u) - 3.2) / 3.0)
    return (k * side * (1 + w), k * side * (1 + w * 0.75), k * side * (1 + w * 0.2))


cells = [(u, v) for u, v in E.hex_grid(-6.6, G, 6.6, E.zat(3.3, YW), 0.34)
         if math.hypot(u - OC[0], v - OZ) > OR + 0.36 and v + E.KZ * YW < arch(u) + 0.2]
E.annulus(OC[0], OZ, OR + 0.1, OR + 0.85, YW + 0.07, "wall_front_b", tintfn=lambda co: wall_tint(co.x, co.z))
glows = set(rnd.sample(range(len(cells)), 16))
E.hexfield(cells, 0.34, E.wall_place(YW), ["wall_front:wax", "wall_front:wax", "wall_front_b", "comb"],
           pick=lambda i, u, v: rnd.choice([1, 1, 1, 1, 2, 2, 3]), tintfn=wall_tint, var=0.05, depth=0.06)
for i in sorted(glows):                                  # Leuchtzellen (dazu im Spiel flackernde Lichthoefe)
    u, v = cells[i]
    zi = v + E.KZ * YW
    if zi < -1.3 or abs(u) > 5.2 or math.hypot(u - OC[0], zi - OC[1]) < OR + 0.75:
        continue
    E.slab(E.hex_pts(u, v, 0.25), YW + 0.015, YW + 0.06, "wall_glow", lit=False, nl=True)
    E.halo(u, v, 0.62, YW - 0.01, "glow", 0.42)
E.box(-6.8, 6.8, YW - 0.07, YW + 0.02, G, G + 0.2, "wall_base", bevel=0.025)

# Kronenoeffnung: Laibung (unten hell, man schaut hinein), Wachskragen, Messingring mit Nieten
E.lathe([(OR, 0.55), (OR, -0.1), (OR + 0.07, -0.17), (OR + 0.3, -0.17), (OR + 0.4, -0.09), (OR + 0.42, 0.0)], (OC[0], YW, OZ), "wall_lip",
        seg=72, axis="y", caps=False)
E.torus((OC[0], YW - 0.2, OZ), OR + 0.185, 0.055, "brass", seg=72, ring=10)
for k in range(16):
    a = 2 * math.pi * (k + 0.5) / 16
    E.ball((OC[0] + (OR + 0.185) * math.cos(a), YW - 0.25, OZ + (OR + 0.185) * math.sin(a)), 0.045, "brass_dark", seg=10)
for k, (a, ln, w) in enumerate(((-2.0, 0.42, 0.11), (-1.7, 0.7, 0.13), (-1.42, 0.3, 0.09), (-1.1, 0.55, 0.12), (-0.85, 0.26, 0.08))):
    E.drip(OC[0] + (OR + 0.2) * math.cos(a), YW - 0.2, OZ + (OR + 0.3) * math.sin(a) + 0.08, ln, w)

# Gewoelbe: dunkle Wabenkrone ueber der Wand, darunter der helle Kragen
top = [(x, E.zat(arch(x), YW - 0.3)) for x in [-6.8 + 13.6 * i / 40 for i in range(41)]]
E.slab([(6.8, E.zat(3.6, YW - 0.3)), (-6.8, E.zat(3.6, YW - 0.3))] + top, YW - 0.3, YW + 0.05, "wall_top", nl=True)
dcells = [(u, v) for u, v in E.hex_grid(-6.8, E.zat(1.2, YW - 0.3), 6.8, E.zat(3.6, YW - 0.3), 0.3) if v + E.KZ * (YW - 0.3) > arch(u) + 0.3]
E.hexfield(dcells, 0.3, E.wall_place(YW - 0.31), ["wall_top", "wall_cell", "wall_cell_b", "wall_cell_c"],
           pick=lambda i, u, v: rnd.choice([1, 1, 2, 2, 3]), depth=0.02, inset=0.9, inner=0.84, var=0.08)
E.tube([(x, YW - 0.34, z - 0.05) for x, z in top], 0.085, "wall_lip", seg=10, cap=False)
for k, (x, ln, w) in enumerate(((-5.1, 0.35, 0.1), (-3.6, 0.5, 0.12), (-1.2, 0.3, 0.09), (2.9, 0.3, 0.1), (4.7, 0.6, 0.12), (5.6, 0.3, 0.09))):
    E.drip(x, YW - 0.36, E.zat(arch(x), YW - 0.3) - 0.1, ln, w)

# Boden: kuehle Sechseckplatten, Petrol-Laeufer mit Messingkante, Fuge am Wandfuss
E.tiles(E.hex_tiles(-6.9, -3.2, 6.9, YW, 0.5), G, ["fl_sand", "fl_sand_b", "fl_stone", "fl_sand"], var=0.05,
        planes=[(0, 1, YW), (0, -1, 3.2), (1, 0, 6.9), (-1, 0, 6.9)], base=[(-6.9, -3.2), (6.9, -3.2), (6.9, YW), (-6.9, YW)],
        tintfn=lambda x, y: (0.9 + 0.1 * E.smooth01((1.5 - y) / 4.0),) * 3)
rug = [(-0.5 + 2.9 * math.cos(math.pi / 3 * k), 0.3 + 1.7 * math.sin(math.pi / 3 * k)) for k in range(6)]
E.prism(rug, G, G + 0.012, "fl_inlay", nl=True)
E.prism(E._inset(rug, 0.14), G + 0.012, G + 0.02, "fl_teal", nl=True)
E.prism(E._inset(rug, 0.5), G + 0.02, G + 0.024, "fl_teal_b", nl=True)
for cx, cy in E.hex_grid(-2.3, -0.6, 1.4, 1.1, 0.42):
    if abs(cx + 0.5) < 1.6 and abs(cy - 0.3) < 0.9:
        E.prism([(cx + 0.2 * math.cos(math.pi / 3 * k), cy + 0.2 * math.sin(math.pi / 3 * k)) for k in range(6)], G + 0.024, G + 0.027,
                "fl_inlay", nl=True, tint=(0.8, 0.9, 0.85))
E.fade(-6.9, 6.9, YW - 0.07, YW - 0.75, E.PLUM, 0.34, plane="floor", at=G + 0.03)

# Saeulen aus Wachs mit Messingreifen (tragen das Gewoelbe)
for sx, py in ((-4.45, 1.9), (4.7, 1.9)):
    hgt = E.zat(3.7, py) - G                             # laeuft oben aus dem Bild (traegt das Gewoelbe)
    E.lathe([(0.5, 0.0), (0.5, 0.14), (0.42, 0.24), (0.36, 0.34), (0.33, hgt * 0.5), (0.35, hgt)], (sx, py, G), "wax", seg=40)
    for hz in (0.42, 2.3, 4.1):
        E.torus((sx, py, G + hz), 0.355, 0.04, "brass", axis="z", seg=40)
    E.gshadow(sx, py, 0.55, 0.42, G, 0.36)
    E.wshadow(sx, G + hgt * 0.5, 0.32, hgt * 0.5, YW, 0.22, dx=0.2, dz=-0.05)

# Einrichtung links: gestrichene Bienenkaesten (Petrol) mit Nussholzdeckeln, Honigtoepfe
def hive_box(x, y, z, w, d, h, lid=True):
    E.box(x - w / 2, x + w / 2, y, y + d, z, z + h, "paint_teal", bevel=0.025)
    E.box(x - w / 2 - 0.03, x + w / 2 + 0.03, y - 0.03, y + d + 0.03, z + h * 0.42, z + h * 0.5, "paint_teal_dark", bevel=0.012)
    E.box(x - w * 0.22, x + w * 0.22, y - 0.012, y + 0.02, z + 0.06, z + 0.115, "black", bevel=0.01)          # Flugloch
    E.slab(E.hex_pts(x, z + h * 0.74, 0.085), y - 0.02, y + 0.01, "brass", bevel=0.012)
    if lid:
        E.box(x - w / 2 - 0.06, x + w / 2 + 0.06, y - 0.06, y + d + 0.06, z + h, z + h + 0.09, "wood", bevel=0.025)
    return z + h


def jar(x, y, z, r=0.15, h=0.3):
    E.lathe([(r * 0.8, 0.0), (r, 0.04), (r, h * 0.72), (r * 0.72, h * 0.86), (r * 0.72, h)], (x, y, z), "honey", seg=20)
    E.lathe([(r * 0.8, 0.0), (r * 0.8, 0.06), (r * 0.5, 0.075)], (x, y, z + h), "cloth_cream", seg=20)
    E.torus((x, y, z + h), r * 0.76, 0.014, "rope", axis="z", seg=20, ring=6)
    E.slab(E.round_rect(x - r * 0.55, z + h * 0.25, x + r * 0.55, z + h * 0.58, 0.02), y - r - 0.004, y - r + 0.03, "paper", nl=True)


t1 = hive_box(-2.95, 1.45, G, 0.95, 0.75, 0.62, lid=False)
hive_box(-2.9, 1.5, t1, 0.9, 0.7, 0.56)
hive_box(-1.95, 1.75, G, 0.8, 0.65, 0.5)
E.gshadow(-2.6, 1.8, 1.1, 0.5, G)
E.wshadow(-2.7, G + 0.6, 0.7, 0.65, YW, 0.2)
jar(-1.95, 2.05, G + 0.59, 0.14, 0.27)
jar(-3.75, 1.2, G, 0.17, 0.33)
jar(-3.42, 0.95, G, 0.13, 0.25)
E.gshadow(-3.6, 1.1, 0.34, 0.2, G, 0.3)

# Einrichtung rechts: Metfass auf Bock, Kiste mit Wabenrahmen, Blumentopf
bx, by = 3.2, 1.7
E.lathe([(0.36, 0.0), (0.43, 0.2), (0.46, 0.45), (0.43, 0.7), (0.36, 0.9)], (bx, by, G + 0.16), "wood", seg=32)
for hz in (0.1, 0.33, 0.57, 0.8):
    E.torus((bx, by, G + 0.16 + hz), 0.375 + 0.085 * math.sin(math.pi * hz / 0.9), 0.022, "brass", axis="z", seg=32, ring=8)
E.cyl(bx, by, G + 1.06, G + 1.085, 0.33, "wood_dark", seg=32)
E.box(bx - 0.45, bx + 0.45, by - 0.3, by + 0.3, G, G + 0.16, "paint_teal", bevel=0.02)
E.tube([(bx, by - 0.44, G + 0.42), (bx, by - 0.56, G + 0.42), (bx, by - 0.58, G + 0.33)], 0.03, "brass", seg=10, sm=3)
E.gshadow(bx, by, 0.55, 0.4, G)
E.wshadow(bx, G + 0.6, 0.45, 0.6, YW, 0.2)
cx0 = 4.05
E.box(cx0 - 0.42, cx0 + 0.42, 0.9, 1.5, G, G + 0.5, "wood", bevel=0.02)
for k in range(3):
    E.box(cx0 - 0.42, cx0 + 0.42, 0.885, 0.9, G + 0.04 + 0.16 * k, G + 0.15 + 0.16 * k, "wood_light", bevel=0.01)
for k in range(5):                                      # Wabenrahmen stecken in der Kiste
    fy = 0.98 + k * 0.11
    E.box(cx0 - 0.36, cx0 + 0.36, fy, fy + 0.035, G + 0.3, G + 0.62, "comb", bevel=0.008)
    E.box(cx0 - 0.39, cx0 + 0.39, fy - 0.005, fy + 0.04, G + 0.62, G + 0.66, "wood_light", bevel=0.008)
E.gshadow(cx0, 1.2, 0.5, 0.36, G)
px, py = 2.35, 0.95
E.lathe([(0.13, 0.0), (0.2, 0.3), (0.22, 0.32), (0.22, 0.37), (0.17, 0.37)], (px, py, G), "paint_teal", seg=20)
E.cyl(px, py, G + 0.33, G + 0.36, 0.17, "wood_dark", seg=20)
for k, (dx, hh, col) in enumerate(((-0.07, 0.34, "petal_pink"), (0.06, 0.44, "petal_white"), (0.0, 0.26, "petal_blue"))):
    E.tube([(px + dx * 0.4, py, G + 0.36), (px + dx, py - 0.02, G + 0.36 + hh)], 0.014, "leaf", seg=6)
    E.ellipsoid((px + dx, py - 0.04, G + 0.36 + hh), (0.075, 0.03, 0.075), col, seg=12)
    E.ball((px + dx, py - 0.07, G + 0.36 + hh), 0.03, "pollen", seg=8)
E.gshadow(px, py, 0.22, 0.16, G, 0.3)

E.render_bg("swarm_bg")

# ------------------------------------------------------------------ Laterne (haengt an der Kette, Anker = Aufhaengung)
E.clear()
E.tube([(0, 0, 0), (0, 0, -0.55)], 0.016, "brass_dark", seg=6, cap=False)
for k in range(6):
    E.torus((0, 0, -0.06 - k * 0.09), 0.028, 0.009, "brass_dark", seg=10, ring=5, axis="y" if k % 2 else "x")
E.lathe([(0.02, 0.0), (0.2, -0.12), (0.22, -0.16), (0.2, -0.16)], (0, 0, -0.52), "brass", seg=6)
E.lathe([(0.17, -0.5), (0.2, -0.3), (0.2, -0.05), (0.17, 0.0)], (0, 0, -0.68), "wall_glow", seg=6, lit=False, tint=(1.0, 0.95, 0.85))
for k in range(6):
    a = math.pi / 3 * k
    E.tube([(0.205 * math.cos(a), 0.205 * math.sin(a), -0.68), (0.205 * math.cos(a), 0.205 * math.sin(a), -1.0),
            (0.175 * math.cos(a), 0.175 * math.sin(a), -1.18)], 0.014, "brass", seg=6, cap=False)
E.lathe([(0.2, 0.0), (0.22, -0.04), (0.12, -0.1), (0.05, -0.2), (0.0, -0.21)], (0, 0, -1.16), "brass", seg=6)
E.ball((0, 0, -1.4), 0.035, "brass", seg=10)
E.render_layer("swarm_lamp", pivot=(0, 0, 0))

# ------------------------------------------------------------------ Vordergrund: dunkle Wabenmasse links und oben rechts
def mass(outline, y, seed, drips):
    r2 = random.Random(seed)
    E.slab(outline, y, y + 0.4, "wall_top", bevel=0.05)
    x0, x1 = min(p[0] for p in outline), max(p[0] for p in outline)
    z0, z1 = min(p[1] for p in outline), max(p[1] for p in outline)

    def inside(u, v):
        n = len(outline)
        c = False
        for i in range(n):
            (xa, za), (xb, zb) = outline[i], outline[(i + 1) % n]
            if (za > v) != (zb > v) and u < xa + (xb - xa) * (v - za) / (zb - za):
                c = not c
        return c
    cs = [(u, v) for u, v in E.hex_grid(x0, z0, x1, z1, 0.36)
          if all(inside(u + 0.4 * math.cos(a), v + 0.4 * math.sin(a)) for a in (0, 1.05, 2.1, 3.14, 4.2, 5.25))]
    E.hexfield(cs, 0.36, E.wall_place(y - 0.01), ["wall_top", "wall_cell", "wall_cell_b", "wall_cell_c"],
               pick=lambda i, u, v: r2.choice([1, 1, 2, 3, 3]), depth=0.03, inset=0.9, inner=0.82, var=0.16)
    for dx, dz, ln, w in drips:
        E.drip(dx, y + 0.1, dz + 0.16, ln + 0.16, w)
    E.tube([(u, y - 0.03, v) for u, v in outline[1:-1]], 0.06, "wall_lip", seg=8)      # heller Kragen wie an den Kartenwaenden


E.clear()
YF = -3.0
zf = lambda zi: E.zat(zi, YF)  # noqa: E731
left = [(-6.9, zf(-3.5)), (-5.5, zf(-3.5)), (-5.3, zf(-2.6)), (-5.55, zf(-1.9)), (-5.2, zf(-1.2)), (-5.45, zf(-0.3)), (-5.0, zf(0.5)),
        (-5.3, zf(1.3)), (-4.85, zf(2.1)), (-4.3, zf(2.6)), (-3.9, zf(3.5)), (-6.9, zf(3.5))]
mass(left, YF, 3, [(-5.15, zf(-1.3), 0.5, 0.12), (-4.95, zf(0.42), 0.4, 0.1), (-4.5, zf(2.4), 0.6, 0.13)])
E.render_layer("swarm_fg_l", pad=0.04, line=0.034)
E.clear()
right = [(6.9, zf(3.5)), (2.6, zf(3.5)), (3.0, zf(2.95)), (3.7, zf(2.75)), (4.1, zf(2.2)), (4.9, zf(2.0)), (5.2, zf(1.3)), (5.75, zf(1.05)),
         (5.9, zf(0.2)), (6.9, zf(-0.1))]
mass(right, YF, 5, [(3.2, zf(2.95), 0.45, 0.11), (4.4, zf(2.1), 0.7, 0.13), (5.4, zf(1.2), 0.4, 0.1), (6.0, zf(0.2), 0.55, 0.12)])
E.render_layer("swarm_fg_r", pad=0.04, line=0.034)

# ------------------------------------------------------------------ weicher Bodenschatten unter dem Spieler
E.clear()
E.soft(E.ell_pts(0, 0, 0.3, 0.3, 24), 0.22, E.PLUM, 0.5, plane="floor", at=0.0)
E.render_layer("shadow", pivot=(0, 0, 0), pad=0.02)

E.render_bee_set()
E.note("swarm_pts", opening=[OC[0], OC[1], OR], sun=[1.55, 0.42], lamps=[list(p) for p in LAMPS], floor=G)
