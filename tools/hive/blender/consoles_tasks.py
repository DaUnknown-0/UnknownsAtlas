# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_tasks.py - Aufgaben-Konsolen der Amberhive, Teil 1 (14 Motive aus art_consoles.json), Stil V2 "Bernsteinlicht".
# Teil 2 steht in consoles_tasks_b.py, die Kronen-Etage in consoles_crown.py.
# Aufruf:  blender -b --factory-startup -P consoles_tasks.py -- [motiv ...]     (ohne Motiv: alle)
# Anker (0,0,0) = Mitte der Vorderkante am Boden; die Konsole reicht hoechstens 0,5 m nach hinten (Norden).
# Farbregel: ein Anstrichton je Motiv plus Nussholz und Messing; was leuchtet, ist die Stelle, an der man die Aufgabe bedient.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consoles_common import *  # noqa: E402,F401,F403
import consoles_common as C  # noqa: E402


def notice_board():
    """Cafeteria Download: Pinnwand mit Bogen auf einer Staffelei, Tanznotizen, Ablage."""
    for s in (-1, 1):
        bx(s * 0.43 - 0.06, 0.04, 0, s * 0.43 + 0.06, 0.20, 0.05, "wood_dark", bevel=0.01)
        tube((s * 0.43, 0.12, 0.05), (s * 0.40, 0.37, 1.34), 0.03, "wood", seg=10)
        sph(s * 0.40, 0.37, 1.36, 0.042, "brass", seg=12)
    bx(-0.05, 0.40, 0, 0.05, 0.49, 0.05, "wood_dark", bevel=0.01)
    tube((0, 0.45, 0.05), (0, 0.38, 1.05), 0.026, "wood_dark", seg=10)
    al, base = 14, (0, 0.15, 0.40)
    m = mark()
    prism_y(arch_pts(-0.46, 0.46, 0, 0.78, 0.11), 0, 0.05, "paint_teal")
    prism_y(arch_pts(-0.405, 0.405, 0.055, 0.735, 0.085), -0.008, 0, "cork")
    bx(-0.45, -0.11, -0.025, 0.45, 0.0, 0.02, "wood", bevel=0.008)                 # Ablage
    notes = [(-0.22, 0.55, 0.25, 0.27, -6, "paper", "dance"), (0.06, 0.60, 0.20, 0.20, 5, "paint_cream", "hex"),
             (0.25, 0.33, 0.22, 0.25, -4, "paper", "text"), (-0.13, 0.24, 0.27, 0.19, 4, "paper", "text"),
             (0.27, 0.64, 0.13, 0.11, 9, "coral", None)]
    pins = ["red", "teal", "royal", "pollen", "teal_dark"]
    for i, (cx, cz, w, h, ang, mat, kind) in enumerate(notes):
        n0 = mark()
        bx(cx - w / 2, -0.016, cz - h / 2, cx + w / 2, -0.009, cz + h / 2, mat)
        if kind == "dance":      # Schwaenzeltanz: Acht mit Wackelstrecke
            for sx in (-1, 1):
                tor(cx + sx * 0.045, -0.018, cz - 0.02, 0.042, 0.007, "ink", seg=18, ring=6, face="south", nl=True)
            for k in range(4):
                dx = 0.012 if k % 2 else -0.012
                bx(cx - 0.008 + dx, -0.022, cz - 0.07 + k * 0.026, cx + 0.008 + dx, -0.018, cz - 0.05 + k * 0.026, "red", nl=True)
        elif kind == "hex":
            hexy(cx, cz, 0.065, -0.021, -0.016, "comb", nl=True)
            hexy(cx, cz, 0.036, -0.024, -0.021, "honey", nl=True)
        elif kind == "text":
            for k in range(3):
                bx(cx - w / 2 + 0.03, -0.020, cz + 0.045 - k * 0.05, cx + w / 2 - 0.03 - (k % 2) * 0.06, -0.016,
                   cz + 0.06 - k * 0.05, "ink", nl=True)
        sph(cx, -0.024, cz + h / 2 - 0.035, 0.024, pins[i], seg=10)
        rot(since(n0), ry=ang, pivot=(cx, -0.013, cz))
    cylx(-0.055, 0.052, -0.36, -0.08, 0.032, "paper", seg=12)                    # Schriftrolle auf der Ablage
    cylx(-0.055, 0.052, -0.25, -0.21, 0.036, "red", seg=12)
    lathe([(0, 0.02), (0.05, 0.02), (0.058, 0.04), (0.058, 0.10), (0.04, 0.125), (0.04, 0.14), (0, 0.14)], 0.02, -0.055,
          ["honey", "wax_light"], seg=14, band=[0, 0, 0, 0, 1, 1])
    hexy(0, 0.845, 0.062, -0.018, 0.0, "brass")
    flat(hexy(0, 0.845, 0.041, -0.024, -0.018, "wall_glow"))
    bee(0.27, -0.055, 0.02, s=0.75, yaw=200)
    tilted(m, al, base)
    glow(*tilt_pt(al, base, (0, -0.04, 0.845)), 0.16, "wall_glow", 0.5, lift=0.2)


def comb_wirebox():
    """Wachsdraehte flicken (sechs Raeume): zellenfoermiger Sicherungskasten auf Messingpfosten, Fluegel offen."""
    hexz(0, 0.35, 0.17, 0, 0.05, "wood_dark")
    cyl(0, 0.35, 0.05, 0.11, 0.07, "brass_dark", seg=16)
    cyl(0, 0.35, 0.11, 0.66, 0.04, "brass", seg=14)
    cyl(0, 0.35, 0.60, 0.67, 0.062, "brass_dark", seg=16)
    case = [(-0.25, 0.75), (0.0, 0.63), (0.25, 0.75), (0.25, 1.21), (0.0, 1.34), (-0.25, 1.21)]
    prism_y(case, 0.30, 0.46, "paint_coral")
    zc = 0.985
    inner = [(x * 0.84, zc + (z - zc) * 0.86) for x, z in case]
    prism_y(inner, 0.292, 0.30, "shaft")
    comb_front(-0.20, 0.20, 0.72, 1.26, 0.292, 0.05, "propolis", depth=0.004,
               keep=lambda x, z: abs(x) < 0.14 and 0.80 < z < 1.18)
    zs = [0.83, 0.93, 1.03, 1.13]
    cols = ["red", "petal_blue", "pollen", "leaf"]
    perm = [2, 0, 3, 1]
    for i in range(4):
        for x in (-0.165, 0.165):
            cyly(x, zs[i], 0.268, 0.292, 0.028, "brass", seg=12)
        z0, z1 = zs[i], zs[perm[i]]
        if i == 1:      # gerissen: zwei Enden haengen herab
            sweep(curve([(-0.165, 0.27, z0), (-0.09, 0.265, z0 - 0.02), (-0.05, 0.265, z0 - 0.09)]), 0.02, cols[i], seg=8, nl=True)
            sweep(curve([(0.165, 0.27, z1), (0.10, 0.265, z1 - 0.03), (0.07, 0.265, z1 - 0.11)]), 0.02, cols[i], seg=8, nl=True)
        else:
            mid = (z0 + z1) / 2 - 0.03
            sweep(curve([(-0.165, 0.27, z0), (-0.07, 0.262, z0 - 0.02), (0.0, 0.258, mid), (0.07, 0.262, z1 - 0.02),
                         (0.165, 0.27, z1)]), 0.02, cols[i], seg=8, nl=True)
    for s in (-1, 1):
        m = mark()
        half = [(0.0, 0.63), (0.25, 0.75), (0.25, 1.21), (0.0, 1.34)]
        prism_y([(s * x, z) for x, z in half] if s > 0 else [(-x, z) for x, z in reversed(half)], 0.272, 0.30, "paint_coral_dark")
        sph(s * 0.04, 0.265, 0.985, 0.022, "brass", seg=10)
        rot(since(m), rz=s * 108, pivot=(s * 0.25, 0.30, 0))
    hexy(0, 1.37, 0.06, 0.28, 0.33, "brass")
    flat(hexy(0, 1.37, 0.04, 0.274, 0.28, "wall_glow"))
    glow(0, 0.27, 1.37, 0.16, "wall_glow", 0.5, lift=0.2)


def scroll_desk():
    """Upload (fuenf Raeume): Schreibsekretaer mit Wabenfaechern voller Schriftrollen und leuchtender Rohrpost."""
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.39, s * 0.15))
        bx(x0 + 0.012, 0.09, 0, x1 - 0.012, 0.45, 0.06, "wood_dark")
        bx(x0, 0.07, 0.06, x1, 0.46, 0.70, "paint_teal", bevel=0.012)
        for z in (0.19, 0.39, 0.58):
            panel(x0 + 0.03, x1 - 0.03, z - 0.075, z + 0.075, 0.07, "paint_teal_dark", knob=((x0 + x1) / 2, z))
    bx(-0.15, 0.38, 0.12, 0.15, 0.44, 0.70, "paint_teal_dark")
    prism_x([(0.0, 0.70), (0.38, 0.70), (0.38, 0.86), (0.0, 0.76)], -0.43, 0.43, "wood")
    al = math.degrees(math.atan2(0.10, 0.38))
    m = mark()
    bx(-0.43, -0.012, -0.02, 0.43, 0.02, 0.03, "wood_dark")
    bx(-0.24, 0.06, 0, 0.20, 0.34, 0.006, "paper")
    cylx(0.06, 0.022, -0.27, 0.23, 0.022, "paper", seg=10)
    cylx(0.34, 0.022, -0.27, 0.23, 0.022, "paper", seg=10)
    for k in range(5):
        inkline(-0.20, 0.105 + k * 0.045, 0.14 - (k % 3) * 0.07, 0.105 + k * 0.045, 0.006, w=0.014)
    cyl(0.13, 0.11, 0.006, 0.016, 0.034, "red", seg=12, nl=True)
    on_slope(m, al, (0, 0, 0.76))
    bx(-0.43, 0.37, 0.70, 0.43, 0.50, 1.16, "paint_teal", bevel=0.01)             # Aufsatz
    bx(-0.45, 0.35, 1.16, 0.45, 0.51, 1.20, "wood", bevel=0.008)
    for i, x in enumerate((-0.30, -0.15, 0.0, 0.15)):
        hexy(x, 1.02, 0.072, 0.362, 0.37, "shaft")
        if i != 2:
            cyly(x, 1.008, 0.345, 0.37, 0.042, "paper", seg=12)
            cyly(x, 1.008, 0.341, 0.345, 0.018, "cloth_cream", seg=8, nl=True)
    hexy(0.33, 1.02, 0.066, 0.356, 0.37, "brass")                                # Einwurf der Rohrpost
    hexy(0.33, 1.02, 0.04, 0.35, 0.356, "shaft", nl=True)
    cyl(0.33, 0.43, 1.20, 1.26, 0.05, "brass", seg=16)
    flat(cyl(0.33, 0.43, 1.26, 1.36, 0.04, "glow", seg=16))
    cyl(0.33, 0.43, 1.36, 1.40, 0.05, "brass", seg=16)
    sph(0.33, 0.43, 1.40, 0.05, "brass_dark", seg=14, sz=0.6)
    glow(0.33, 0.43, 1.31, 0.19, "glow", 0.5)
    cyl(-0.30, 0.43, 1.20, 1.26, 0.045, "ink", seg=14)                          # Tintenfass mit Feder
    cyl(-0.30, 0.43, 1.26, 1.27, 0.03, "brass", seg=12)
    q = ell(-0.27, 0.43, 1.37, 0.022, 0.03, 0.12, "petal_white", seg=12)
    rot(q, ry=16, pivot=(-0.30, 0.43, 1.26))


def nectar_valve():
    """Nektar umleiten (acht Raeume): Messingbuegel aus dem Boden mit rotem Handrad und leuchtendem Honig-Schauglas."""
    cy = 0.27
    for x in (-0.13, 0.13):
        cyl(x, cy, 0, 0.045, 0.075, "brass_dark", seg=18)
        cyl(x, cy, 0.045, 0.80, 0.05, "brass", seg=16)
        cyl(x, cy, 0.30, 0.36, 0.064, "brass_dark", seg=16)
        sph(x, cy, 0.80, 0.05, "brass", seg=16)
    cylx(cy, 0.80, -0.13, 0.13, 0.05, "brass", seg=16)
    bc(0, cy, 0.80, 0.17, 0.17, 0.17, "brass_dark", bevel=0.025)
    cyly(0, 0.80, 0.10, 0.19, 0.032, "brass_dark", seg=14)
    tor(0, 0.105, 0.80, 0.15, 0.026, "red", seg=32, ring=8, face="south")
    for a in (0, 60, 120):
        o = bx(-0.13, 0.095, 0.80 - 0.013, 0.13, 0.115, 0.80 + 0.013, "red")
        rot(o, ry=a, pivot=(0, 0.105, 0.80))
    cyly(0, 0.80, 0.07, 0.11, 0.042, "brass", seg=14)
    cyl(0, cy, 0.885, 0.93, 0.055, "brass_dark", seg=16)
    sph(0, cy, 1.03, 0.105, "honey", seg=20)
    ell(-0.04, cy - 0.085, 1.07, 0.022, 0.008, 0.03, "white", seg=10, nl=True)
    cyl(0, cy, 1.12, 1.16, 0.045, "brass", seg=14)
    sph(0, cy, 1.17, 0.03, "brass_dark", seg=10)
    glow(0, cy, 1.03, 0.25, "wall_glow", 0.5)
    gauge(0.13, 0.55, cy - 0.05, 0.07, 35, n=5)


def scrap_bin():
    """Wachsreste leeren (Cafeteria, Blasebalg): bauchiger Kuebel mit Messingreifen, hochgeklappter Deckel, Pedal."""
    cy = 0.27

    def rr(z):
        return 0.195 + 0.085 * z / 0.76
    lathe([(0, 0), (0.195, 0), (0.28, 0.76), (0.295, 0.80), (0.255, 0.80), (0.25, 0.70), (0, 0.70)], 0, cy,
          ["paint_teal", "brass", "shaft"], seg=28, band=[0, 0, 1, 1, 2, 2])
    for z in (0.16, 0.58):
        tor(0, cy, z, rr(z) + 0.004, 0.02, "brass_dark", seg=32, ring=8)
    scraps = [(-0.10, 0.24, 0.085, 20, 15, "wax", 0.72), (0.09, 0.30, 0.075, -25, 10, "comb", 0.74),
              (0.0, 0.17, 0.065, 35, -20, "wax_light", 0.75), (0.13, 0.19, 0.055, 10, 30, "honey", 0.72),
              (-0.08, 0.36, 0.06, -15, -25, "wax_dark", 0.73), (0.02, 0.27, 0.07, 50, 20, "comb", 0.80)]
    for (x, y, r, a, b, mat, z) in scraps:
        o = hexz(x, y, r, z, z + 0.07, mat)
        rot(o, rx=a, ry=b, pivot=(x, y, z + 0.035))
    m = mark()
    cyl(0, cy, 0.80, 0.84, 0.30, "wood", seg=28)
    cyl(0, cy, 0.785, 0.80, 0.25, "wood_light", seg=28)
    rot(since(m), rx=-66, pivot=(0, cy + 0.29, 0.80))
    cylx(cy + 0.29, 0.80, -0.11, 0.11, 0.024, "brass_dark", seg=10)
    badge(0, cy - rr(0.40), 0.40, r=0.075)
    bx(-0.08, -0.05, 0, 0.08, 0.06, 0.04, "brass_dark", bevel=0.008)


def stamp_desk():
    """Ausweis stempeln (Buero): Schrank mit Logbuch, Stempel und leuchtendem Kartenschlitz."""
    cabinet(-0.31, 0.31, 0.09, 0.45, 0.78, "paint_teal", over=0.04)
    panel(-0.26, 0.26, 0.13, 0.66, 0.09, "paint_teal_dark", knob=(0.18, 0.40))
    T = 0.78
    bx(-0.31, 0.10, T, 0.03, 0.36, T + 0.012, "red", bevel=0.004)                 # Logbuch
    bx(-0.30, 0.11, T + 0.012, -0.145, 0.35, T + 0.03, "paper")
    bx(-0.135, 0.11, T + 0.012, 0.02, 0.35, T + 0.03, "paper")
    for k in range(5):
        inkline(-0.285, 0.31 - k * 0.042, -0.17 - (k % 2) * 0.03, 0.31 - k * 0.042, T + 0.03, w=0.013)
    hexz(-0.058, 0.23, 0.055, T + 0.03, T + 0.032, "red", nl=True)
    hexz(-0.058, 0.23, 0.036, T + 0.032, T + 0.034, "paper", nl=True)
    hexz(-0.058, 0.23, 0.016, T + 0.034, T + 0.036, "red", nl=True)
    bx(0.10, 0.28, T, 0.30, 0.42, T + 0.03, "brass_dark", bevel=0.006)            # Stempelkissen
    bx(0.118, 0.298, T + 0.03, 0.282, 0.402, T + 0.036, "royal")
    hexz(0.20, 0.14, 0.065, T, T + 0.04, "brass")                                # Stempel
    cyl(0.20, 0.14, T + 0.04, T + 0.13, 0.03, "wood", seg=12)
    sph(0.20, 0.14, T + 0.17, 0.055, "honey", seg=16)
    bx(-0.28, 0.39, T, -0.08, 0.46, T + 0.16, "brass", bevel=0.01)                # Kartenleser
    flat(bx(-0.25, 0.382, T + 0.085, -0.11, 0.39, T + 0.115, "glow"))
    bx(-0.225, 0.415, T + 0.16, -0.135, 0.43, T + 0.25, "cloth_white")
    bx(-0.225, 0.412, T + 0.20, -0.135, 0.415, T + 0.225, "coral", nl=True)
    glow(-0.18, 0.37, T + 0.10, 0.17, "glow", 0.5, lift=0.2)


def glow_dials():
    """Verteiler kalibrieren (Lampenhaus): Bogentafel mit drei leuchtenden Zeigerinstrumenten auf einem Bock."""
    for s in (-1, 1):
        bx(s * 0.36 - 0.045, 0.06, 0, s * 0.36 + 0.045, 0.46, 0.06, "wood_dark", bevel=0.01)
        bx(s * 0.36 - 0.035, 0.24, 0.06, s * 0.36 + 0.035, 0.33, 0.66, "wood")
    bx(-0.36, 0.265, 0.24, 0.36, 0.305, 0.31, "wood_dark")
    al, base = 12, (0, 0.17, 0.58)
    m = mark()
    prism_y(arch_pts(-0.46, 0.46, 0, 0.50, 0.14), 0, 0.22, "paint_blue")
    prism_y(arch_pts(-0.41, 0.41, 0.045, 0.47, 0.12), -0.008, 0, "paint_blue_dark")
    spots = []
    for i, x in enumerate((-0.27, 0.0, 0.27)):
        zc = 0.40 if i == 1 else 0.36
        gauge(x, zc, -0.008, 0.115, [-45, 15, 50][i])
        cyly(x, zc - 0.21, -0.035, -0.008, 0.036, "brass", seg=14)
        bx(x - 0.007, -0.04, zc - 0.21, x + 0.007, -0.035, zc - 0.178, "ink", nl=True)
        spots.append((x, -0.05, zc))
    tilted(m, al, base)
    for p in spots:
        glow(*tilt_pt(al, base, p), 0.19, "glow", 0.42, lift=0.3)


def royal_keypad():
    """Reaktor starten (Thronsaal): Lesepult auf Wabensaeule, schraege Platte mit Wachsknoepfen und Wabenanzeige."""
    bx(-0.45, 0.06, 0, 0.45, 0.48, 0.07, "wood_dark", bevel=0.012)
    hexz(0, 0.28, 0.20, 0.07, 0.74, "paint_plum")
    hexz(0, 0.28, 0.22, 0.07, 0.13, "brass_dark")
    bx(-0.075, 0.095, 0.17, 0.075, 0.107, 0.60, "royal_light")
    hexy(0, 0.42, 0.055, 0.083, 0.095, "brass")
    prism_x([(0.0, 0.74), (0.50, 0.74), (0.50, 1.02), (0.0, 0.80)], -0.46, 0.46, "paint_plum")
    al = math.degrees(math.atan2(0.22, 0.50))
    base = (0, 0, 0.80)
    m = mark()
    bx(-0.43, 0.03, 0, 0.43, 0.52, 0.012, "wood")
    for i in range(3):
        for j in range(3):
            lit = (i, j) == (1, 1)
            o = cyl(-0.31 + 0.105 * i, 0.14 + 0.125 * j, 0.012, 0.04, 0.042, "glow" if lit else "wax_light", seg=12)
            if lit:
                flat(o)
    dx0, dy0, rr = 0.19, 0.275, 0.06
    hexz(dx0, dy0, 0.20, 0.012, 0.022, "brass")
    hexz(dx0, dy0, 0.178, 0.022, 0.026, "royal_dark", nl=True)
    cells = [(0.0, 0.0)] + [(math.sqrt(3) * rr * math.cos(math.radians(30 + 60 * k)), math.sqrt(3) * rr * math.sin(math.radians(30 + 60 * k)))
                            for k in range(6)]
    for k, (dx, dy) in enumerate(cells):
        on = k in (0, 2, 5)
        o = hexz(dx0 + dx, dy0 + dy, rr * 0.86, 0.026, 0.034, "glow" if on else "paint_plum_dark", nl=not on)
        if on:
            flat(o)
    on_slope(m, al, base)
    glow(*slope_pt(al, base, (dx0, dy0, 0.05)), 0.24, "glow", 0.42)
    bx(-0.46, 0.44, 1.02, 0.46, 0.50, 1.09, "paint_plum_dark", bevel=0.008)
    crown(0, 0.47, 1.09, r=0.075)


def royal_cells_panel():
    """Weiselzellen entriegeln (Thronsaal): Bogentafel mit zehn haengenden Weiselzellen und Nummernschildern."""
    for s in (-1, 1):
        bx(s * 0.38 - 0.06, 0.04, 0, s * 0.38 + 0.06, 0.48, 0.06, "wood_dark", bevel=0.01)
        tube((s * 0.38, 0.44, 0.06), (s * 0.38, 0.34, 0.95), 0.03, "wood", seg=10)
        tube((s * 0.38, 0.10, 0.06), (s * 0.38, 0.15, 0.50), 0.03, "wood", seg=10)
    al, base = 24, (0, 0.09, 0.42)
    m = mark()
    prism_y(arch_pts(-0.45, 0.45, 0, 0.74, 0.16), 0, 0.05, "paint_plum")
    prism_y(arch_pts(-0.40, 0.40, 0.05, 0.70, 0.14), -0.008, 0, "paint_plum_dark")
    nums = [3, 7, 1, 9, 5, 10, 2, 6, 8, 4]
    lit, spot = 6, None
    prof = [(0, -0.17), (0.022, -0.165), (0.045, -0.12), (0.055, -0.07), (0.05, -0.025), (0.035, 0.0), (0, 0.0)]
    for k in range(10):
        x = -0.31 + 0.155 * (k % 5)
        zt = 0.60 if k < 5 else 0.27
        cyly(x, zt + 0.075, -0.02, -0.008, 0.046, "brass", seg=14)
        cyly(x, zt + 0.075, -0.024, -0.02, 0.036, "paper", seg=14, nl=True)
        txt(str(nums[k]), x, -0.026, zt + 0.075, 0.058 if nums[k] < 10 else 0.046, "ink")
        o = lathe([(r, zt + z) for r, z in prof], x, -0.055, ["brass", "glow" if k == lit else "wax"], seg=14,
                  band=[0, 1, 1, 1, 1, 1])
        if k == lit:
            flat(o)
            spot = (x, -0.09, zt - 0.08)
    crown(0, 0.02, 0.89, r=0.07)
    tilted(m, al, base)
    glow(*tilt_pt(al, base, spot), 0.19, "glow", 0.45, lift=0.3)


def route_table():
    """Kurs abstecken (Sonnenkompass): schraeger Kartentisch auf Boecken mit Flugroute, Blueten und leuchtendem Ziel."""
    for s in (-1, 1):
        x = s * 0.42
        bx(x - 0.05, 0.03, 0, x + 0.05, 0.49, 0.05, "wood_dark", bevel=0.01)
        tube((x, 0.08, 0.05), (x, 0.22, 0.74), 0.032, "paint_teal", seg=10)
        tube((x, 0.45, 0.05), (x, 0.30, 0.80), 0.032, "paint_teal", seg=10)
    cylx(0.26, 0.36, -0.42, 0.42, 0.026, "paint_teal_dark", seg=10)
    prism_x([(0.0, 0.72), (0.50, 0.84), (0.50, 0.89), (0.0, 0.77)], -0.50, 0.50, "wood")
    al = math.degrees(math.atan2(0.12, 0.50))
    base = (0, 0, 0.77)
    m = mark()
    bx(-0.50, -0.012, -0.03, 0.50, 0.025, 0.03, "wood_dark")
    bx(-0.43, 0.05, 0, 0.43, 0.49, 0.006, "paper")
    tube((-0.45, 0.05, 0.022), (-0.45, 0.49, 0.022), 0.022, "paper", seg=10)
    tube((0.45, 0.05, 0.022), (0.45, 0.49, 0.022), 0.022, "paper", seg=10)
    z = 0.006
    for (x, y, rx, ry, mat) in [(-0.22, 0.20, 0.14, 0.08, "moss"), (0.18, 0.36, 0.16, 0.07, "moss"), (0.26, 0.15, 0.10, 0.05, "leaf")]:
        ell(x, y, z, rx, ry, 0.002, mat, seg=18, nl=True)
    path = [(-0.34, 0.14), (-0.12, 0.35), (0.08, 0.18), (0.32, 0.38)]
    for (ax, ay), (bx_, by_) in zip(path, path[1:]):
        n = max(2, int(math.hypot(bx_ - ax, by_ - ay) / 0.055))
        for k in range(n):
            t0, t1 = (k + 0.25) / n, (k + 0.75) / n
            inkline(ax + (bx_ - ax) * t0, ay + (by_ - ay) * t0, ax + (bx_ - ax) * t1, ay + (by_ - ay) * t1, z + 0.002, w=0.018,
                    mat="red")
    hexz(-0.34, 0.14, 0.055, z, z + 0.03, "honey")
    flower_top(-0.12, 0.35, z + 0.002, 0.055, "petal_pink")
    flower_top(0.08, 0.18, z + 0.002, 0.055, "petal_blue")
    flat(hexz(0.32, 0.38, 0.05, z, z + 0.012, "glow"))
    for a, mat in ((0, "red"), (90, "ink"), (180, "ink"), (270, "ink")):
        o = prism([(0, -0.014), (0.065, 0), (0, 0.014)], z, z + 0.003, mat, nl=True)
        rot(o, rz=a + 90)
        move(o, -0.33, 0.39)
    o = bx(-0.16, -0.012, z, 0.16, 0.012, z + 0.012, "brass")
    rot(o, rz=-24)
    move(o, 0.02, 0.10)
    on_slope(m, al, base)
    glow(*slope_pt(al, base, (0.32, 0.38, 0.03)), 0.15, "glow", 0.5)


def compass_wheel():
    """Steuer stabilisieren (Sonnenkompass): sechseckiges Kompasshaus mit leuchtender Sonnenscheibe, davor das Steuerrad."""
    cy = 0.30
    hexz(0, cy, 0.18, 0, 0.07, "wood_dark")
    lathe([(0, 0.07), (0.145, 0.07), (0.15, 0.11), (0.11, 0.20), (0.095, 0.62), (0.13, 0.76), (0.175, 0.82), (0, 0.82)], 0, cy,
          "paint_teal", seg=6)
    cyl(0, cy, 0.82, 0.88, 0.19, "brass", seg=32)
    flat(cyl(0, cy, 0.88, 0.886, 0.16, "glow", seg=32))
    for k in range(12):
        a = math.radians(30 * k)
        L = 0.05 if k % 3 == 0 else 0.028
        inkline(0.15 * math.sin(a), cy + 0.15 * math.cos(a), (0.15 - L) * math.sin(a), cy + (0.15 - L) * math.cos(a), 0.886,
                w=0.014, mat="red" if k == 0 else "ink")
    cyl(0, cy, 0.886, 0.895, 0.04, "honey", seg=12, nl=True)
    prism_x([(cy - 0.05, 0.886), (cy + 0.15, 0.886), (cy + 0.15, 1.08)], -0.016, 0.016, "brass")
    glow(0, cy, 0.90, 0.30, "glow", 0.4)
    for s in (-1, 1):
        tube((s * 0.16, cy, 0.80), (s * 0.27, cy, 0.84), 0.018, "brass_dark", seg=8)
        sph(s * 0.27, cy, 0.89, 0.055, "coral" if s < 0 else "teal", seg=14)
    cyly(0, 0.54, 0.08, 0.22, 0.03, "brass_dark", seg=12)
    m = mark()
    tor(0, 0, 0, 0.25, 0.028, "wood", seg=36, ring=8, face="south")
    for k in range(6):
        g0 = mark()
        bx(-0.014, -0.014, 0.05, 0.014, 0.014, 0.25, "wood_dark")
        tube((0, 0, 0.27), (0, 0, 0.33), 0.022, "wood", seg=10)
        sph(0, 0, 0.34, 0.028, "brass", seg=10)
        rot(since(g0), ry=60 * k + 30)
    cyly(0, 0, -0.04, 0.03, 0.07, "brass", seg=6)
    hexy(0, 0, 0.04, -0.047, -0.04, "honey")
    g = since(m)
    rot(g, rx=-15)
    move(g, 0, 0.08, 0.54)


def wax_plates():
    """Wachsplatten anwaermen (Giesserei): Imker-Raehmchen mit sieben sechseckigen Platten auf einer Kommode, vier gluehen."""
    bx(-0.44, 0.13, 0, 0.44, 0.45, 0.07, "wood_dark", bevel=0.01)
    bx(-0.42, 0.14, 0.07, 0.42, 0.44, 0.36, "paint_coral", bevel=0.014)
    bx(-0.45, 0.11, 0.36, 0.45, 0.47, 0.41, "wood", bevel=0.01)
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.38, s * 0.03))
        panel(x0, x1, 0.12, 0.31, 0.14, "paint_coral_dark", knob=((x0 + x1) / 2, 0.215))
    al, base = 22, (0, 0.20, 0.41)
    m = mark()
    for s in (-1, 1):
        bx(s * 0.43, -0.03, 0, s * 0.37, 0.03, 0.80, "wood")
    bx(-0.47, -0.035, 0.78, 0.47, 0.035, 0.85, "wood_dark", bevel=0.006)
    bx(-0.43, -0.03, 0, 0.43, 0.03, 0.06, "wood_dark")
    bx(-0.37, 0.0, 0.06, 0.37, 0.02, 0.78, "wall_front_b")
    r = 0.118
    d = math.sqrt(3) * r * 1.04
    pos = [(0.0, 0.42)] + [(d * math.cos(math.radians(30 + 60 * k)), 0.42 + d * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    lit = {0, 2, 3, 5}
    spots = []
    for k, (px_, pz) in enumerate(pos):
        hexy(px_, pz, r, -0.025, 0.0, "brass")
        o = hexy(px_, pz, r * 0.78, -0.035, -0.025, "glow" if k in lit else "wax_dark")
        if k in lit:
            flat(o)
            spots.append((px_, -0.05, pz))
    tilted(m, al, base)
    for p in spots:
        glow(*tilt_pt(al, base, p), 0.17, "glow", 0.38, lift=0.3)
    for s in (-1, 1):
        tube((s * 0.40, 0.44, 0.41), (s * 0.40, 0.44, 0.92), 0.018, "brass_dark", seg=8)


def press_dial():
    """Presse ausrichten (beide Pressen): kleine Spindelpresse mit grossem Zifferblatt und Hebel."""
    bx(-0.32, 0.08, 0, 0.32, 0.46, 0.08, "wood_dark", bevel=0.012)
    for s in (-1, 1):
        bx(s * 0.24 - 0.04, 0.20, 0.08, s * 0.24 + 0.04, 0.34, 0.70, "paint_coral", bevel=0.008)
    bx(-0.30, 0.18, 0.64, 0.30, 0.36, 0.75, "paint_coral", bevel=0.012)
    bx(-0.15, 0.17, 0.08, 0.15, 0.37, 0.20, "comb", bevel=0.01)
    comb_front(-0.15, 0.15, 0.085, 0.20, 0.17, 0.034, "honey", depth=0.005)
    ell(0.08, 0.165, 0.075, 0.03, 0.012, 0.05, "honey", seg=10, nl=True)
    bx(-0.18, 0.15, 0.20, 0.18, 0.39, 0.26, "wood", bevel=0.006)
    cyl(0, 0.27, 0.26, 0.64, 0.035, "iron", seg=12)
    for z in (0.32, 0.39, 0.46, 0.53, 0.60):
        tor(0, 0.27, z, 0.04, 0.012, "iron_light", seg=14, ring=6)
    bx(-0.05, 0.24, 0.75, 0.05, 0.32, 0.86, "brass_dark")
    al, base = 18, (0, 0.25, 1.04)
    m = mark()
    cyly(0, 0, -0.03, 0.05, 0.235, "brass", seg=36)
    cyly(0, 0, -0.036, -0.03, 0.20, "paper", seg=36)
    pts = [(0.0, 0.0)] + [(0.185 * math.sin(math.radians(a)), 0.185 * math.cos(math.radians(a))) for a in range(60, 19, -5)]
    flat(prism_y(pts, -0.04, -0.036, "wall_glow", nl=True))
    for k in range(11):
        a = -120 + 24 * k
        o = bx(-0.006, -0.04, 0.15, 0.006, -0.036, 0.19, "ink", nl=True)
        rot(o, ry=a, pivot=(0, 0, 0))
    needle(0, 0, -0.042, 0.17, -38, "red", w=0.024)
    cyly(0, 0, -0.056, -0.036, 0.032, "brass_dark", seg=12)
    g = since(m)
    rot(g, rx=-al)
    move(g, *base)
    tube((0.28, 0.27, 0.75), (0.33, 0.17, 1.04), 0.02, "brass", seg=10)
    sph(0.33, 0.165, 1.07, 0.046, "red", seg=14)
    lamp(-0.25, 0.27, 0.79, 0.045, "glow", halo=3.0, strength=0.5)


def nectar_tank_valve():
    """Nektar tanken (beide Pressen): Glastank mit Honigspiegel im gestrichenen Sockel, Trichter, Schlauch mit Zapfduese."""
    tx, ty = -0.06, 0.27
    bx(-0.28, 0.08, 0, 0.17, 0.46, 0.07, "wood_dark", bevel=0.01)
    bx(-0.27, 0.10, 0.07, 0.16, 0.44, 0.20, "paint_teal", bevel=0.014)
    lathe([(0, 0.20), (0.19, 0.20), (0.20, 0.23), (0.20, 0.48), (0.20, 0.74), (0.185, 0.79), (0, 0.79)], tx, ty,
          ["brass", "honey", "glass"], seg=28, band=[0, 0, 1, 2, 0, 0])
    tor(tx, ty, 0.235, 0.203, 0.016, "brass_dark", seg=32, ring=6)
    tor(tx, ty, 0.74, 0.203, 0.016, "brass_dark", seg=32, ring=6)
    ell(tx - 0.10, ty - 0.178, 0.60, 0.018, 0.006, 0.07, "white", seg=10, nl=True)
    lathe([(0, 0.79), (0.12, 0.79), (0.10, 0.85), (0.045, 0.89), (0.045, 0.93), (0, 0.93)], tx, ty, "brass_dark", seg=20)
    lathe([(0.03, 0.91), (0.04, 0.95), (0.15, 1.09), (0.165, 1.10), (0.15, 1.115), (0.05, 1.0), (0, 1.0)], tx, ty, "brass", seg=24)
    cyl(tx, ty, 1.06, 1.066, 0.11, "honey", seg=20, nl=True)
    glow(tx, ty - 0.21, 0.36, 0.22, "wall_glow", 0.35, lift=0.3)
    cyly(tx - 0.13, 0.135, 0.05, 0.10, 0.026, "brass", seg=10)
    tor(tx - 0.13, 0.045, 0.135, 0.045, 0.012, "red", seg=18, ring=6, face="south")
    cyl(0.14, 0.24, 0.24, 0.32, 0.036, "brass", seg=12)
    sweep(curve([(0.14, 0.24, 0.29), (0.23, 0.22, 0.34), (0.285, 0.17, 0.24), (0.285, 0.10, 0.08), (0.22, 0.05, 0.035),
                 (0.12, 0.04, 0.035)]), 0.026, "leather", seg=10)
    tube((0.12, 0.04, 0.035), (0.0, 0.04, 0.035), 0.032, "brass", seg=12, r1=0.016)


MOTIFS = ["notice_board", "comb_wirebox", "scroll_desk", "nectar_valve", "scrap_bin", "stamp_desk", "glow_dials", "royal_keypad",
          "royal_cells_panel", "route_table", "compass_wheel", "wax_plates", "press_dial", "nectar_tank_valve"]

C.run(MOTIFS, globals())
