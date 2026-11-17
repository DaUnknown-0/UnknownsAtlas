# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_crown.py - sechs Motive der Kronen-Etage der Amberhive (Archiv, Sonnendeck, Drohnendock), Stil V2 "Bernsteinlicht".
# Aufruf:  blender -b --factory-startup -P consoles_crown.py -- [motiv ...]
# Anker (0,0,0) = Mitte der Vorderkante am Boden, frei stehend, hoechstens 0,5 m Tiefe.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consoles_common import *  # noqa: E402,F401,F403
import consoles_common as C  # noqa: E402


def royal_vault():
    """Tresor oeffnen (Archiv): Panzerschrank mit schraeger Front, runde Messingtuer mit Sechsspeichenrad, leuchtende Nabe."""
    bx(-0.39, 0.07, 0, 0.39, 0.47, 0.07, "brass_dark", bevel=0.01)
    prism_x([(0.09, 0.07), (0.46, 0.07), (0.46, 0.84), (0.30, 0.84)], -0.37, 0.37, "paint_plum")
    al = math.degrees(math.atan2(0.21, 0.77))
    base = (0, 0.09, 0.07)
    L = math.hypot(0.21, 0.77)
    m = mark()
    for s in (-1, 1):
        xa, xb = sorted((s * 0.375, s * 0.30))
        bx(xa, -0.012, 0, xb, 0.02, L, "brass")
        for z in (0.12, 0.40, 0.68):
            sph(s * 0.3375, -0.016, z, 0.018, "brass_dark", seg=8)
    bx(-0.375, -0.012, L - 0.07, 0.375, 0.02, L, "brass")
    zc = 0.37
    cyly(0, zc, -0.035, 0.0, 0.25, "brass", seg=36)
    cyly(0, zc, -0.045, -0.035, 0.20, "paint_plum_dark", seg=36)
    for k in range(3):
        o = bx(-0.18, -0.062, zc - 0.015, 0.18, -0.045, zc + 0.015, "brass")
        rot(o, ry=60 * k + 30, pivot=(0, -0.05, zc))
    for k in range(6):
        a = math.radians(60 * k + 30)
        sph(0.18 * math.cos(a), -0.058, zc + 0.18 * math.sin(a), 0.032, "honey", seg=10)
    hexy(0, zc, 0.075, -0.08, -0.045, "brass_dark")
    flat(hexy(0, zc, 0.048, -0.086, -0.08, "wall_glow"))
    for z in (zc - 0.13, zc + 0.13):
        cylx(-0.02, z, -0.29, -0.23, 0.026, "brass_dark", seg=10)
    tilted(m, al, base)
    glow(*tilt_pt(al, base, (0, -0.09, zc)), 0.19, "wall_glow", 0.5)
    bx(-0.39, 0.28, 0.84, 0.39, 0.48, 0.88, "wood", bevel=0.008)
    crown(0, 0.38, 0.88, r=0.085)


def amber_polish():
    """Bernstein polieren (Archiv): geschliffener Bernstein auf Samtkissen und Wabensaeule, Poliertuch, Dose am Arm."""
    cy = 0.26
    hexz(0, cy, 0.24, 0, 0.06, "wood_dark")
    hexz(0, cy, 0.14, 0.06, 0.62, "paint_plum")
    hexz(0, cy, 0.165, 0.06, 0.12, "brass_dark")
    hexz(0, cy, 0.165, 0.56, 0.62, "brass")
    hexz(0, cy, 0.23, 0.62, 0.68, "wood")
    ell(0, cy, 0.71, 0.19, 0.17, 0.055, "velvet", seg=22)
    for dx in (-0.17, 0.17):
        sph(dx, cy - 0.11, 0.70, 0.03, "pollen", seg=10)
    lathe([(0, 0.75), (0.085, 0.82), (0.135, 0.92), (0.09, 1.03), (0, 1.07)], 0, cy, "amber_glass", seg=6)
    ell(-0.05, cy - 0.10, 0.97, 0.03, 0.01, 0.025, "white", seg=10, nl=True)
    ell(0.02, cy - 0.12, 0.90, 0.022, 0.008, 0.014, "propolis", seg=8, nl=True)
    glow(0, cy, 0.92, 0.30, "wall_glow", 0.45)
    bx(0.05, cy - 0.225, 0.58, 0.20, cy - 0.16, 0.70, "cloth_white", bevel=0.012)
    tube((0.10, cy, 0.42), (0.30, cy, 0.42), 0.016, "brass_dark", seg=8)
    cyl(0.30, cy, 0.42, 0.44, 0.07, "brass", seg=18)
    cyl(0.30, cy, 0.44, 0.52, 0.055, "paint_plum_dark", seg=18)
    cyl(0.30, cy, 0.52, 0.535, 0.058, "brass", seg=18)


def _bloom(x, y, z0, zh, tilt, petal, n=12, r=0.075, center="propolis_light", plen=0.055):
    """Blume auf Stiel: Bluetenkopf zeigt nach Sueden und ist um tilt Grad nach oben gekippt."""
    tube((x, y + 0.04, z0), (x, y, zh - 0.02), 0.018, "leaf_dark", seg=8)
    for (t, s) in ((0.4, 1), (0.65, -1)):
        zz = z0 + (zh - z0) * t
        lf = ell(x + s * 0.07, y + 0.02, zz, 0.07, 0.03, 0.016, "leaf", seg=12)
        rot(lf, ry=-s * 25, pivot=(x, y, zz))
    m = mark()
    for k in range(n):
        p = ell(0, -0.005, r + plen * 0.55, 0.026, 0.008, plen, petal, seg=10)
        rot(p, ry=360 / n * k)
    cyly(0, 0, -0.022, 0.01, r, center, seg=20)
    g = since(m)
    rot(g, rx=-tilt)
    move(g, x, y, zh)


def flower_sprinkler():
    """Blumendusche richten (Sonnendeck): Pflanztrog auf Beinen mit drei Blumen, Schwanenhals-Brause aus Messing, Tropfen."""
    for sx in (-0.44, 0.44):
        for y in (0.10, 0.40):
            bx(sx - 0.035, y, 0, sx + 0.035, y + 0.06, 0.20, "wood_dark")
    bx(-0.50, 0.08, 0.18, 0.50, 0.46, 0.44, "paint_mint", bevel=0.016)
    bx(-0.52, 0.06, 0.44, 0.52, 0.48, 0.49, "wood", bevel=0.008)
    bx(-0.47, 0.10, 0.49, 0.47, 0.44, 0.496, "propolis", nl=True)
    panel(-0.44, 0.44, 0.23, 0.39, 0.08, "paint_mint_dark")
    badge(0, 0.072, 0.31, r=0.055)
    _bloom(0.0, 0.33, 0.49, 1.12, 28, "bee_yellow", n=14, r=0.08)
    _bloom(-0.30, 0.24, 0.49, 0.90, 35, "petal_pink", n=7, r=0.05, center="pollen", plen=0.06)
    _bloom(0.25, 0.20, 0.49, 0.84, 35, "petal_white", n=10, r=0.045, center="pollen", plen=0.05)
    for (x, y) in ((-0.14, 0.16), (0.12, 0.38), (-0.40, 0.38)):
        ell(x, y, 0.50, 0.045, 0.04, 0.022, "moss", seg=10)
    cyl(0.45, 0.42, 0.49, 1.26, 0.022, "brass", seg=10)
    sweep(curve([(0.45, 0.42, 1.26), (0.44, 0.41, 1.36), (0.36, 0.39, 1.43), (0.25, 0.36, 1.42), (0.17, 0.34, 1.36)]), 0.022,
          "brass", seg=10)
    hd = Vector((-0.55, -0.15, -0.82)).normalized()
    hp = Vector((0.17, 0.34, 1.36))
    o = lathe([(0, 0), (0.025, 0), (0.03, 0.02), (0.095, 0.11), (0.10, 0.12), (0, 0.12)], 0, 0, ["brass", "brass_dark"], seg=18,
              band=[0, 0, 0, 0, 1])
    orient(o, hp, hd)
    side = Vector((0.82, 0, -0.55))
    for k, (a, b) in enumerate(((0.20, -0.05), (0.27, 0.04), (0.34, -0.02), (0.41, 0.06), (0.24, 0.07))):
        q = hp + hd * a + side * b
        ell(q.x, q.y, q.z, 0.013, 0.013, 0.024, "water", seg=8, nl=True)
    cyly(0.45, 0.80, 0.36, 0.42, 0.014, "brass_dark", seg=8)
    tor(0.45, 0.36, 0.80, 0.05, 0.014, "red", seg=18, ring=6, face="south")


def dew_basin():
    """Taubecken putzen (Sonnendeck): sechseckiges Steinbecken auf Saeule, Messinghahn mit leuchtendem Tropfen, Puempel."""
    cy = 0.27
    hexz(0, cy, 0.21, 0, 0.07, "stone_dark", sy=0.9)
    hexz(0, cy, 0.13, 0.07, 0.50, "stone")
    m = mark()
    lathe([(0, 0.48), (0.14, 0.48), (0.33, 0.64), (0.42, 0.72), (0.42, 0.77), (0.36, 0.77), (0.34, 0.72), (0, 0.72)], 0, 0,
          ["stone", "paint_mint", "water"], seg=6, band=[0, 0, 0, 1, 1, 2, 2])
    scl(since(m), 1.0, 0.56, 1.0)
    move(since(m), 0, cy, 0)
    ell(-0.13, cy - 0.04, 0.722, 0.075, 0.014, 0.002, "white", seg=10, nl=True)
    ell(-0.02, cy + 0.07, 0.722, 0.04, 0.01, 0.002, "white", seg=10, nl=True)
    cyl(0.10, cy + 0.02, 0.72, 0.727, 0.06, "leaf", seg=12, nl=True)
    flower_top(0.11, cy + 0.03, 0.728, 0.034, "petal_pink")
    cyl(0.24, 0.44, 0.74, 0.79, 0.04, "brass_dark", seg=12)
    sweep(curve([(0.24, 0.44, 0.78), (0.25, 0.45, 0.96), (0.19, 0.41, 1.06), (0.10, 0.34, 1.03)]), 0.022, "brass", seg=10)
    sph(0.10, 0.34, 1.03, 0.028, "brass_dark", seg=10)
    tor(0.25, 0.42, 0.90, 0.032, 0.011, "red", seg=14, ring=6, face="south")
    flat(ell(0.085, 0.325, 0.955, 0.022, 0.022, 0.034, "ice_light", seg=10))
    glow(0.085, 0.325, 0.955, 0.13, "ice_light", 0.5)
    bx(-0.33, cy - 0.20, 0.77, -0.17, cy - 0.13, 0.80, "wood", bevel=0.008)            # Schrubber auf dem Rand
    bx(-0.32, cy - 0.195, 0.74, -0.18, cy - 0.135, 0.77, "coral")
    ell(0.10, 0.10, 0.0, 0.05, 0.03, 0.026, "moss", seg=10)
    bee(0.30, cy + 0.02, 0.77, s=0.65, yaw=-120)


def _stinger(x, h, y0=0.20, y1=0.33):
    a, b = Vector((x, y0, 0.20)), Vector((x, y1, h))
    d = (b - a).normalized()
    tip0 = b - 0.26 * d
    tube(a, tip0, 0.022, "wood", seg=10)
    tube(a + 0.20 * d, a + 0.34 * d, 0.03, "leather", seg=10)
    tube(tip0 - 0.04 * d, tip0, 0.036, "brass", seg=12)
    tube(tip0, b, 0.034, "bee_black", seg=12, r1=0.003)
    for k in (0.3, 0.55):
        q = tip0 + (b - tip0) * k
        for sx in (-1, 1):
            tube(q, q - 0.05 * d + Vector((sx * 0.03, 0, 0)), 0.007, "bee_black", seg=6)


def stinger_rack():
    """Stachel einraeumen (Drohnendock): Lanzenstaender mit drei aufrechten Stachellanzen, vorn der Drohnenschild."""
    bx(-0.45, 0.08, 0, 0.45, 0.46, 0.08, "wood_dark", bevel=0.01)
    bx(-0.42, 0.11, 0.08, 0.42, 0.43, 0.22, "paint_teal", bevel=0.012)
    for s in (-1, 1):
        bx(s * 0.40 - 0.035, 0.34, 0.22, s * 0.40 + 0.035, 0.42, 1.10, "paint_teal")
        sph(s * 0.40, 0.38, 1.13, 0.045, "brass", seg=12)
    bx(-0.40, 0.35, 0.50, 0.40, 0.40, 0.56, "paint_teal_dark")
    bx(-0.44, 0.31, 0.84, 0.44, 0.40, 0.92, "wood", bevel=0.006)
    for x, h in ((-0.24, 1.30), (0.0, 1.44), (0.24, 1.24)):
        _stinger(x, h)
        bx(x - 0.045, 0.285, 0.85, x + 0.045, 0.31, 0.91, "brass_dark")
    prism_y([(0.025, 1.04), (0.17, 1.10), (0.025, 1.16)], 0.30, 0.306, "coral")
    hexy(0, 0.38, 0.17, 0.085, 0.11, "brass")
    hexy(0, 0.38, 0.145, 0.079, 0.085, "bee_yellow")
    for dz in (-0.078, 0.078):
        bx(-0.095, 0.075, 0.38 + dz - 0.02, 0.095, 0.079, 0.38 + dz + 0.02, "bee_black", nl=True)
    flat(hexy(0, 0.38, 0.045, 0.073, 0.079, "wall_glow"))
    glow(0, 0.06, 0.38, 0.16, "wall_glow", 0.5)


def pollen_lunch():
    """Pollenbrot belegen (Drohnendock): Kuechenwagen mit grossem Pollenburger auf dem Brett, Honigtopf, Teller."""
    bx(-0.36, 0.10, 0.14, 0.36, 0.44, 0.62, "paint_teal", bevel=0.014)
    panel(-0.30, 0.30, 0.22, 0.54, 0.10, "paint_teal_dark")
    bx(-0.26, 0.084, 0.34, -0.08, 0.092, 0.60, "cloth_white")
    for z in (0.40, 0.47):
        bx(-0.26, 0.08, z, -0.08, 0.084, z + 0.035, "coral", nl=True)
    for s in (-1, 1):
        x = s * 0.25
        tor(x, 0.075, 0.14, 0.11, 0.028, "wood_dark", seg=24, ring=8, face="south")
        for a in (0, 60, 120):
            o = bx(x - 0.10, 0.068, 0.14 - 0.011, x + 0.10, 0.082, 0.14 + 0.011, "wood")
            rot(o, ry=a, pivot=(x, 0.075, 0.14))
        cyly(x, 0.14, 0.05, 0.08, 0.03, "brass", seg=10)
    bx(-0.40, 0.05, 0.62, 0.40, 0.48, 0.67, "wood", bevel=0.01)
    T = 0.67
    bxc, byc = -0.13, 0.25
    cyl(bxc, byc, T, T + 0.02, 0.17, "wood_dark", seg=24)
    cyl(bxc, byc, T + 0.02, T + 0.08, 0.125, "wood_light", seg=20)                 # Brot unten
    cyl(bxc, byc, T + 0.08, T + 0.14, 0.135, "propolis_light", seg=20)             # Pollenbratling
    o = bx(-0.125, -0.125, T + 0.14, 0.125, 0.125, T + 0.16, "pollen")             # Wachskaese
    rot(o, rz=45)
    move(o, bxc, byc)
    cyl(bxc, byc, T + 0.16, T + 0.18, 0.15, "leaf", seg=9)
    lathe([(0, T + 0.18), (0.125, T + 0.18), (0.13, T + 0.22), (0.10, T + 0.28), (0.045, T + 0.31), (0, T + 0.315)], bxc, byc,
          "wood_light", seg=20)
    for (dx, dy) in ((-0.04, -0.06), (0.03, -0.08), (0.07, -0.02), (-0.01, -0.01), (-0.08, -0.01)):
        ell(bxc + dx, byc + dy, T + 0.298 - 4.0 * (dx * dx + dy * dy), 0.013, 0.009, 0.006, "paint_cream", seg=6, nl=True)
    tube((bxc, byc, T + 0.30), (bxc, byc, T + 0.44), 0.007, "wood", seg=6)
    prism_y([(bxc + 0.007, T + 0.36), (bxc + 0.10, T + 0.40), (bxc + 0.007, T + 0.44)], byc - 0.003, byc + 0.003, "coral")
    lathe([(0, T), (0.06, T), (0.085, T + 0.04), (0.09, T + 0.11), (0.065, T + 0.15), (0.07, T + 0.16), (0, T + 0.16)], 0.25, 0.35,
          ["wax", "honey"], seg=20, band=[0, 0, 0, 0, 1, 1])
    tube((0.26, 0.35, T + 0.16), (0.32, 0.38, T + 0.30), 0.009, "wood", seg=6)
    ell(0.325, 0.382, T + 0.31, 0.022, 0.022, 0.028, "wood_light", seg=10)
    cyl(0.20, 0.15, T, T + 0.012, 0.10, "cloth_white", seg=24)
    cyl(0.20, 0.15, T + 0.012, T + 0.016, 0.07, "paint_cream", seg=20, nl=True)
    bx(0.15, 0.12, T + 0.016, 0.21, 0.18, T + 0.05, "pollen", bevel=0.008)
    bx(0.20, 0.13, T + 0.016, 0.26, 0.19, T + 0.04, "honey_light", bevel=0.008)
    cyl(0.04, 0.41, T, T + 0.09, 0.04, "paint_cream", seg=14)
    cyl(0.04, 0.41, T + 0.085, T + 0.092, 0.032, "honey", seg=12, nl=True)
    badge(0.17, 0.10, 0.40, r=0.05)


MOTIFS = ["royal_vault", "amber_polish", "flower_sprinkler", "dew_basin", "stinger_rack", "pollen_lunch"]

C.run(MOTIFS, globals())
