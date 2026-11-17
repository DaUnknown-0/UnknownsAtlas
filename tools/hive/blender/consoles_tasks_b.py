# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_tasks_b.py - Aufgaben-Konsolen der Amberhive, Teil 2 (14 Motive aus art_consoles.json), Stil V2 "Bernsteinlicht".
# Teil 1 steht in consoles_tasks.py, die Kronen-Etage in consoles_crown.py.
# Aufruf:  blender -b --factory-startup -P consoles_tasks_b.py -- [motiv ...]     (ohne Motiv: alle)
# Anker (0,0,0) = Mitte der Vorderkante am Boden; scan_pad hat den Anker in der Mitte (man steht darauf).
# queen_bell, gramophone und periscope_desk ragen etwas ueber 1,4 m (Joch, Trichter, Sehrohre).

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consoles_common import *  # noqa: E402,F401,F403
import consoles_common as C  # noqa: E402

NO_SHADOW = {"scan_pad"}


def _churn(cx, cy, h, closed):
    """Honigkanne (Milchkannenform) mit Reifen, Tragringen und Wabenetikett."""
    z0 = 0.105

    def Z(t):
        return z0 + (h - z0) * t
    if closed:
        prof = [(0, z0), (0.16, z0), (0.17, Z(0.05)), (0.17, Z(0.60)), (0.15, Z(0.72)), (0.09, Z(0.84)), (0.09, Z(0.92)),
                (0.115, Z(0.93)), (0.115, Z(1.0)), (0, Z(1.0))]
        lathe(prof, cx, cy, ["paint_teal", "brass"], seg=24, band=[0, 0, 0, 0, 0, 1, 1, 1, 1])
        ell(cx + 0.05, cy - 0.10, Z(0.90), 0.022, 0.014, 0.05, "honey", seg=10, nl=True)
    else:
        prof = [(0, z0), (0.16, z0), (0.17, Z(0.05)), (0.17, Z(0.60)), (0.15, Z(0.72)), (0.10, Z(0.86)), (0.112, Z(1.0)),
                (0.085, Z(1.0)), (0.08, Z(0.93)), (0, Z(0.93))]
        lathe(prof, cx, cy, ["paint_teal", "brass", "honey"], seg=24, band=[0, 0, 0, 0, 0, 1, 1, 2, 2])
        tube((cx + 0.01, cy, Z(0.93)), (cx + 0.09, cy + 0.03, Z(1.0) + 0.15), 0.012, "wood", seg=8)
        sph(cx + 0.095, cy + 0.032, Z(1.0) + 0.17, 0.028, "wood_light", seg=10)
        glow(cx, cy, Z(1.0), 0.17, "wall_glow", 0.4)
    for t in (0.12, 0.55):
        tor(cx, cy, Z(t), 0.173, 0.014, "brass_dark", seg=28, ring=6)
    for s in (-1, 1):
        tor(cx + s * 0.175, cy, Z(0.40), 0.04, 0.013, "brass_dark", seg=14, ring=6, face="south")
    hexy(cx, Z(0.33), 0.075, cy - 0.182, cy - 0.165, "wax_light")
    hexy(cx, Z(0.33), 0.042, cy - 0.188, cy - 0.182, "honey", nl=True)


def honey_cans():
    """Honigkannen holen (Keller): zwei bauchige Kannen auf einer Palette, eine offen mit Honigloeffel."""
    for x in (-0.33, 0.0, 0.33):
        bx(x - 0.05, 0.04, 0, x + 0.05, 0.46, 0.07, "wood_dark")
    for k in range(4):
        y = 0.03 + k * 0.112
        bx(-0.40, y, 0.07, 0.40, y + 0.10, 0.105, "wood")
    _churn(-0.18, 0.26, 0.74, True)
    _churn(0.19, 0.27, 0.62, False)
    tor(0.005, 0.085, 0.12, 0.05, 0.016, "rope", seg=18, ring=6)


def chute_hatch():
    """Abfallschacht leeren (Keller): Bodenplatte mit runder Gitterluke im Warnring, Hebelkasten mit rotem Knauf."""
    pts = [(-0.40, 0.06), (-0.34, 0.0), (0.34, 0.0), (0.40, 0.06), (0.40, 0.44), (0.34, 0.50), (-0.34, 0.50), (-0.40, 0.44)]
    prism(pts, 0, 0.04, "iron")
    ins = [(-0.37, 0.07), (-0.33, 0.03), (0.33, 0.03), (0.37, 0.07), (0.37, 0.43), (0.33, 0.47), (-0.33, 0.47), (-0.37, 0.43)]
    prism(ins, 0.04, 0.046, "paint_teal_dark")
    for (x, y) in ((-0.34, 0.06), (0.34, 0.06), (-0.34, 0.44), (0.34, 0.44)):
        cyl(x, y, 0.046, 0.054, 0.016, "brass", seg=8, nl=True)
    hx, hy = -0.12, 0.25
    stripe_ring(hx, hy, 0.046, 0.05, 0.16, 0.212, 16, ["bee_yellow", "bee_black"])
    lathe([(0.165, 0.046), (0.165, 0.09), (0.135, 0.09), (0.135, 0.052), (0, 0.052)], hx, hy, ["brass", "shaft"], seg=32,
          band=[0, 0, 0, 1])
    r = 0.04
    for ci in range(-3, 4):
        for ri in range(-3, 4):
            x = ci * 1.5 * r
            y = ri * math.sqrt(3) * r + (math.sqrt(3) / 2 * r if ci % 2 else 0)
            if math.hypot(x, y) + r * 0.7 < 0.135:
                hexz(hx + x, hy + y, r * 0.92, 0.06, 0.08, "brass_dark", nl=True)
                hexz(hx + x, hy + y, r * 0.56, 0.08, 0.082, "shaft", nl=True)
    for s in (-1, 1):
        bx(hx + s * 0.07 - 0.03, hy + 0.15, 0.046, hx + s * 0.07 + 0.03, hy + 0.20, 0.10, "brass_dark", bevel=0.006)
    cylx(hy + 0.175, 0.10, hx - 0.11, hx + 0.11, 0.014, "iron", seg=8)
    bx(0.19, 0.12, 0.04, 0.37, 0.38, 0.14, "paint_teal", bevel=0.012)
    bx(0.268, 0.15, 0.14, 0.292, 0.35, 0.144, "shaft", nl=True)
    tube((0.28, 0.27, 0.12), (0.28, 0.14, 0.46), 0.02, "brass", seg=10)
    sph(0.28, 0.13, 0.49, 0.052, "red", seg=14)
    lamp(0.33, 0.33, 0.155, 0.028, "glow", halo=4.0, strength=0.5)


def bellows_filter():
    """Luftfilter reinigen (Blasebalg): Schrank mit rundem Wabenfilter voller Pollen, obenauf ein kleiner Blasebalg."""
    cabinet(-0.44, 0.44, 0.09, 0.46, 0.94, "paint_teal", over=0.025)
    fx, fz, R = -0.10, 0.50, 0.29
    cyly(fx, fz, 0.07, 0.09, R + 0.035, "brass", seg=36)
    cyly(fx, fz, 0.062, 0.07, R, "shaft", seg=36)
    comb_front(fx - R, fx + R, fz - R, fz + R, 0.062, 0.055, "wax_dark", alt="pollen",
               pattern=lambda c, r: (c * 3 + r * 5) % 7 < 2, depth=0.008, keep=lambda x, z: math.hypot(x - fx, z - fz) < R - 0.05)
    ell(fx - 0.12, 0.05, fz - R + 0.035, 0.08, 0.025, 0.04, "pollen", seg=12)
    ell(fx + 0.09, 0.05, fz - R + 0.02, 0.06, 0.02, 0.03, "pollen", seg=12)
    ell(-0.22, 0.03, 0.0, 0.09, 0.05, 0.035, "pollen", seg=12)
    ell(0.04, 0.02, 0.0, 0.06, 0.04, 0.025, "pollen", seg=12)
    badge(0.32, 0.09, 0.74, r=0.06)
    bx(0.295, 0.082, 0.22, 0.345, 0.09, 0.56, "shaft")
    cyly(0.32, 0.44, 0.04, 0.09, 0.022, "brass", seg=10)
    sph(0.32, 0.035, 0.44, 0.046, "red", seg=12)
    bx(-0.30, 0.14, 0.94, 0.24, 0.44, 0.97, "wood_dark")
    for k in range(4):
        w = 0.26 if k % 2 == 0 else 0.235
        e = 0.012 * (k % 2)
        bx(-0.03 - w, 0.155 + e, 0.97 + k * 0.035, -0.03 + w, 0.425 - e, 1.005 + k * 0.035,
           "leather" if k % 2 == 0 else "leather_dark")
    bx(-0.30, 0.14, 1.11, 0.24, 0.44, 1.14, "wood", bevel=0.006)
    hexz(-0.03, 0.29, 0.07, 1.14, 1.15, "brass")
    tube((0.24, 0.29, 1.04), (0.40, 0.29, 1.04), 0.04, "brass", seg=12, r1=0.02)
    for x in (-0.20, 0.14):
        tube((x, 0.40, 1.14), (x, 0.44, 1.26), 0.014, "brass_dark", seg=8)
    cylx(0.44, 1.26, -0.24, 0.18, 0.02, "wood", seg=10)


def sample_table():
    """Probe untersuchen (Kinderstube): Labortisch mit Reagenzglaesern, eines leuchtet, Kolben und Lupe am Schwenkarm."""
    cabinet(-0.42, 0.42, 0.09, 0.46, 0.76, "paint_mint", over=0.035)
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.38, s * 0.02))
        panel(x0, x1, 0.13, 0.64, 0.09, "paint_mint_dark", knob=(s * 0.08, 0.40))
    T = 0.76
    for x in (-0.40, -0.04):
        bx(x, 0.30, T, x + 0.03, 0.40, T + 0.20, "wood")
    bx(-0.40, 0.30, T + 0.14, -0.01, 0.40, T + 0.17, "wood")
    fills = [0.10, 0.20, 0.15, 0.23, 0.08]
    cols = ["honey_light", "honey", "glow", "amber_glass", "honey_deep"]
    for k, x in enumerate((-0.335, -0.27, -0.205, -0.14, -0.075)):
        cyl(x, 0.35, T + 0.02, T + 0.30, 0.026, "glass", seg=12)
        o = cyl(x, 0.35, T + 0.02, T + 0.02 + fills[k], 0.029, cols[k], seg=12)
        cyl(x, 0.35, T + 0.30, T + 0.33, 0.03, "cork", seg=10)
        if cols[k] == "glow":
            flat(o)
            glow(x, 0.33, T + 0.10, 0.16, "glow", 0.5, lift=0.3)
    lathe([(0, T), (0.06, T), (0.085, T + 0.03), (0.085, T + 0.08), (0.03, T + 0.15), (0.03, T + 0.21), (0.042, T + 0.215),
           (0, T + 0.215)], -0.24, 0.15, ["honey", "glass"], seg=16, band=[0, 0, 0, 1, 1, 1, 1])
    cyl(0.28, 0.37, T, T + 0.03, 0.07, "brass_dark", seg=16)
    sweep(curve([(0.28, 0.37, T + 0.03), (0.29, 0.37, T + 0.22), (0.24, 0.31, T + 0.30), (0.17, 0.22, T + 0.27)]), 0.014,
          "brass", seg=8)
    cyl(0.12, 0.16, T, T + 0.02, 0.095, "cloth_white", seg=24)
    cyl(0.12, 0.16, T + 0.02, T + 0.024, 0.07, "honey_light", seg=20, nl=True)
    m = mark()
    tor(0, 0, 0, 0.10, 0.017, "brass", seg=28, ring=8)
    cyl(0, 0, -0.006, 0.006, 0.095, "glass", seg=28)
    ell(-0.035, 0.035, 0.008, 0.03, 0.014, 0.002, "white", seg=10, nl=True)
    g = since(m)
    rot(g, rx=25)
    move(g, 0.13, 0.18, T + 0.25)
    bx(-0.10, 0.06, T, 0.0, 0.20, T + 0.006, "paper")
    for k in range(3):
        inkline(-0.085, 0.17 - k * 0.04, -0.015 - (k % 2) * 0.03, 0.17 - k * 0.04, T + 0.006, w=0.013)


def scan_pad():
    """Koerperscan (Kinderstube): sechseckige Bodenplatte mit leuchtendem Wabenring und Lichtperlen an den Ecken."""
    hexz(0, 0, 0.55, 0, 0.03, "wood_dark")
    hexz(0, 0, 0.52, 0.03, 0.045, "brass")
    hexz(0, 0, 0.45, 0.045, 0.052, "paint_teal_dark")
    flat(hexz(0, 0, 0.36, 0.052, 0.056, "glow"))
    hexz(0, 0, 0.30, 0.056, 0.060, "paint_teal")
    for k in range(6):
        o = bx(0.13, -0.014, 0.060, 0.30, 0.014, 0.066, "brass", nl=True)
        rot(o, rz=30 + 60 * k)
    hexz(0, 0, 0.14, 0.060, 0.07, "brass")
    flat(hexz(0, 0, 0.10, 0.07, 0.074, "wall_glow"))
    for k in range(6):
        a = math.radians(60 * k)
        flat(sph(0.485 * math.cos(a), 0.485 * math.sin(a), 0.045, 0.027, "glow", seg=10))
    glow(0, 0, 0.08, 0.50, "glow", 0.3)


def wasp_cannon_seat():
    """Wespen abwehren (Wespenwache): Pollenkanone mit Trichterlauf auf Drehsockel, Ledersitz, Munitionskiste."""
    px_, py = -0.02, 0.29
    cyl(px_, py, 0, 0.05, 0.20, "wood_dark", seg=32)
    cyl(px_, py, 0.05, 0.09, 0.17, "paint_teal", seg=32)
    cyl(px_, py, 0.09, 0.74, 0.05, "brass_dark", seg=14)
    cyl(px_, py, 0.70, 0.78, 0.09, "brass", seg=18)
    yaw, el = math.radians(52), math.radians(30)
    d = Vector((math.cos(el) * math.sin(yaw), math.cos(el) * math.cos(yaw), math.sin(el)))
    n = Vector((-math.sin(el) * math.sin(yaw), -math.sin(el) * math.cos(yaw), math.cos(el)))
    sd = Vector((math.cos(yaw), -math.sin(yaw), 0))
    p = Vector((px_, py, 0.94))
    for sg in (-1, 1):
        q = p + sd * 0.11 * sg
        tube((q.x, q.y, 0.78), q, 0.022, "brass_dark", seg=8)
    tube(p - sd * 0.13, p + sd * 0.13, 0.024, "iron", seg=10)
    prof = [(0, -0.24), (0.06, -0.24), (0.09, -0.19), (0.09, 0.06), (0.075, 0.08), (0.068, 0.28), (0.10, 0.38), (0.125, 0.40),
            (0.10, 0.40), (0.06, 0.32), (0, 0.32)]
    o = lathe(prof, 0, 0, ["brass", "paint_teal", "brass_dark", "shaft"], seg=20, band=[0, 0, 1, 0, 0, 0, 2, 2, 3, 3])
    orient(o, p, d)
    sph(*(p + d * 0.35), 0.058, "pollen", seg=12)
    hb = p - 0.07 * d + n * 0.08
    o = lathe([(0, 0), (0.03, 0), (0.035, 0.02), (0.10, 0.11), (0.11, 0.115), (0.09, 0.115), (0, 0.06)], 0, 0, "brass", seg=16)
    orient(o, hb, n)
    for (a, b) in ((-0.03, -0.02), (0.035, 0.01), (0.0, 0.035)):
        sph(*(hb + n * 0.11 + d * a + sd * b), 0.034, "pollen", seg=10)
    m = mark()
    flat(tor(0, 0, 0, 0.04, 0.01, "glow", seg=14, ring=6))
    orient(since(m), p + 0.22 * d + n * 0.12, d)
    tube(p + 0.22 * d + n * 0.06, p + 0.22 * d + n * 0.085, 0.01, "brass_dark", seg=6)
    for sg in (-1, 1):
        e = p - 0.33 * d + sd * 0.09 * sg - n * 0.03
        tube(p - 0.22 * d, e, 0.016, "wood_dark", seg=8)
        sph(*e, 0.034, "red", seg=10)
    cyl(0.15, 0.13, 0, 0.04, 0.09, "wood_dark", seg=18)                           # Sitz
    cyl(0.15, 0.13, 0.04, 0.40, 0.03, "brass_dark", seg=10)
    cyl(0.15, 0.13, 0.40, 0.44, 0.13, "wood", seg=22)
    ell(0.15, 0.13, 0.45, 0.115, 0.115, 0.035, "leather", seg=18)
    bx(-0.45, 0.08, 0, -0.25, 0.34, 0.20, "paint_teal", bevel=0.012)              # Munitionskiste
    for i in range(2):
        for j in range(3):
            sph(-0.40 + 0.10 * i, 0.125 + 0.085 * j, 0.235, 0.045, "pollen", seg=10)
    badge(-0.35, 0.08, 0.10, r=0.05)


def cooling_comb():
    """Stockfieber kuehlen (Thronsaal, zweimal): Wabensaeule mit Kuehlschlange, schraege Eisplatte mit leuchtender Hand."""
    cy = 0.27
    hexz(0, cy, 0.23, 0, 0.07, "wood_dark")
    hexz(0, cy, 0.18, 0.07, 0.74, "paint_plum")
    for z in (0.20, 0.33, 0.46, 0.59):
        tor(0, cy, z, 0.19, 0.024, "verdigris", seg=28, ring=8)
    for s in (-1, 1):
        sweep(curve([(s * 0.19, cy, 0.20), (s * 0.24, cy, 0.18), (s * 0.27, cy, 0.10), (s * 0.27, cy, 0.0)]), 0.024, "verdigris",
              seg=8)
        cyl(s * 0.27, cy, 0, 0.035, 0.045, "brass_dark", seg=12)
    hexz(0, cy, 0.25, 0.74, 0.80, "brass")
    for x, L in ((-0.15, 0.10), (-0.05, 0.15), (0.06, 0.08), (0.15, 0.12)):
        cyl(x, cy - 0.215, 0.74 - L, 0.74, 0.002, "ice_light", seg=6, r_top=0.02, nl=True)
    m = mark()
    hexz(0, 0, 0.25, 0, 0.05, "ice")
    hexz(0, 0, 0.20, 0.05, 0.056, "ice_dark", nl=True)
    hand = [ell(0, -0.045, 0.058, 0.062, 0.068, 0.003, "white", seg=18, nl=True)]
    for x, a in ((-0.048, -12), (-0.016, -4), (0.016, 4), (0.048, 12)):
        o = ell(0, 0.035, 0.058, 0.017, 0.048, 0.003, "white", seg=10, nl=True)
        rot(o, rz=-a)
        move(o, x, 0.025)
        hand.append(o)
    o = ell(0, 0.03, 0.058, 0.016, 0.04, 0.003, "white", seg=10, nl=True)
    rot(o, rz=55)
    move(o, -0.078, -0.06)
    hand.append(o)
    flat(hand)
    g = since(m)
    rot(g, rx=24)
    move(g, 0, cy, 0.89)
    glow(0, cy, 0.92, 0.27, "ice_light", 0.45)


def air_keypad():
    """Stickluft, Code eingeben (Blasebalg, Buero): Bogentafel auf Staender mit Luefterrad und leuchtender Code-Anzeige."""
    bx(-0.30, 0.06, 0, 0.30, 0.46, 0.06, "wood_dark", bevel=0.01)
    bx(-0.09, 0.22, 0.06, 0.09, 0.36, 0.56, "wood")
    al, base = 18, (0, 0.12, 0.46)
    m = mark()
    prism_y(arch_pts(-0.34, 0.34, 0, 0.60, 0.17), 0, 0.08, "paint_teal")
    fz = 0.56
    cyly(0, fz, -0.012, 0, 0.20, "brass", seg=32)
    cyly(0, fz, -0.016, -0.012, 0.17, "shaft", seg=32)
    for k in range(6):
        o = prism_y([(-0.02, fz + 0.03), (0.02, fz + 0.03), (0.06, fz + 0.155), (-0.045, fz + 0.155)], -0.03, -0.02, "verdigris")
        rot(o, ry=60 * k, pivot=(0, -0.025, fz))
    cyly(0, fz, -0.046, -0.016, 0.045, "brass", seg=12)
    bx(-0.29, -0.008, 0.04, 0.29, 0, 0.31, "paint_teal_dark")
    bx(-0.26, -0.014, 0.215, 0.26, -0.008, 0.29, "screen")
    flat(txt("4815", 0.0, -0.017, 0.2525, 0.062, "screen_glow"))
    for i in range(5):
        for j in range(2):
            col = "wax_light"
            if i == 4:
                col = "red" if j == 0 else "lamp_green"
            bc(-0.21 + 0.105 * i, -0.02, 0.085 + 0.072 * j, 0.08, 0.024, 0.052, col, bevel=0.006)
    tilted(m, al, base)
    glow(*tilt_pt(al, base, (0, -0.03, 0.2525)), 0.21, "screen_glow", 0.4)


def lamp_switches():
    """Leuchtwaben schalten (Lampenhaus): Schaltpult mit fuenf Hebeln, dahinter fuenf Gluehonig-Lampen, zwei sind aus."""
    bx(-0.35, 0.10, 0, 0.35, 0.46, 0.07, "wood_dark")
    bx(-0.36, 0.08, 0.07, 0.36, 0.47, 0.60, "paint_blue", bevel=0.014)
    bx(-0.49, 0.04, 0.60, 0.49, 0.49, 0.66, "paint_blue", bevel=0.012)
    panel(-0.30, 0.30, 0.14, 0.52, 0.08, "paint_blue_dark")
    hexy(0, 0.35, 0.075, 0.058, 0.072, "brass")
    hexy(0, 0.35, 0.045, 0.052, 0.058, "honey", nl=True)
    prism_x([(0.02, 0.66), (0.49, 0.66), (0.49, 0.88), (0.02, 0.72)], -0.49, 0.49, "wood")
    al = math.degrees(math.atan2(0.16, 0.47))
    base = (0, 0.02, 0.72)
    states = [True, False, True, True, False]
    xs = (-0.36, -0.18, 0.0, 0.18, 0.36)
    m = mark()
    for k, x in enumerate(xs):
        bx(x - 0.06, 0.05, 0, x + 0.06, 0.42, 0.012, "brass")
        bx(x - 0.016, 0.09, 0.012, x + 0.016, 0.38, 0.016, "shaft", nl=True)
        yk = 0.32 if states[k] else 0.14
        tube((x, 0.235, 0.01), (x, yk, 0.10), 0.018, "brass_dark", seg=8)
        sph(x, yk, 0.115, 0.042, "red", seg=12)
    on_slope(m, al, base)
    bx(-0.49, 0.43, 0.88, 0.49, 0.50, 0.95, "paint_blue_dark", bevel=0.008)
    for k, x in enumerate(xs):
        cyl(x, 0.465, 0.95, 1.0, 0.036, "brass", seg=12)
        if states[k]:
            lamp(x, 0.465, 1.07, 0.066, "glow", halo=2.7, strength=0.45)
        else:
            sph(x, 0.465, 1.07, 0.066, "lamp_off", seg=14)


def gramophone():
    """Funk reparieren (Tanzstudio): Grammophon mit sechseckigem Wabentrichter, der von innen leuchtet, auf Plattenschrank."""
    cabinet(-0.27, 0.27, 0.10, 0.46, 0.63, "paint_teal", over=0.03)
    bx(-0.21, 0.092, 0.14, 0.21, 0.10, 0.50, "shaft")
    cols = ["black", "coral", "black", "paint_cream", "black", "royal", "black"]
    for i in range(7):
        x = -0.185 + i * 0.053
        bx(x, 0.084, 0.15, x + 0.03, 0.10, 0.46 - (i % 3) * 0.035, cols[i])
    T = 0.63
    bx(-0.22, 0.13, T, 0.18, 0.44, T + 0.10, "wood_dark", bevel=0.01)
    cyl(-0.04, 0.285, T + 0.10, T + 0.115, 0.135, "black", seg=32)
    tor(-0.04, 0.285, T + 0.116, 0.085, 0.003, "iron_light", seg=28, ring=4, nl=True)
    cyl(-0.04, 0.285, T + 0.115, T + 0.12, 0.045, "coral", seg=14, nl=True)
    cylx(0.28, T + 0.05, 0.18, 0.25, 0.014, "brass", seg=8)
    tube((0.25, 0.28, T + 0.05), (0.25, 0.21, T + 0.01), 0.012, "brass", seg=8)
    sph(0.25, 0.20, T + 0.0, 0.026, "wood", seg=10)
    tube((0.11, 0.40, T + 0.13), (0.0, 0.26, T + 0.13), 0.012, "brass", seg=8)
    cyl(0.0, 0.26, T + 0.115, T + 0.145, 0.026, "brass_dark", seg=10)
    cyl(0.11, 0.41, T + 0.10, T + 0.30, 0.026, "brass", seg=12)
    sph(0.11, 0.41, T + 0.30, 0.036, "brass", seg=12)
    hb = Vector((0.11, 0.41, T + 0.30))
    d = Vector((-0.55, -0.35, 0.75)).normalized()
    o = lathe([(0, 0), (0.03, 0), (0.034, 0.10), (0.06, 0.22), (0.12, 0.33), (0.23, 0.41), (0.28, 0.44), (0.265, 0.446)], 0, 0,
              ["brass", "brass_dark"], seg=6, band=[0, 0, 0, 0, 0, 0, 1], caps=False)
    orient(o, hb, d)
    o = lathe([(0, 0.20), (0.045, 0.23), (0.105, 0.335), (0.21, 0.415), (0.265, 0.446)], 0, 0, ["honey_deep", "honey", "honey_light"],
              seg=6, band=[0, 1, 2, 2], caps=False)
    orient(o, hb, d)
    c = hb + d * 0.40
    glow(c.x, c.y, c.z, 0.34, "wall_glow", 0.4)


def queen_bell():
    """Notfallknopf (Mead Hall): grosse Messingglocke der Koenigin im Bogenjoch, rotes Zugseil mit Griffring."""
    cy = 0.26
    hexz(0, cy, 0.50, 0, 0.06, "wood_dark", sy=0.5)
    hexz(0, cy, 0.46, 0.06, 0.09, "paint_teal", sy=0.5)
    for s in (-1, 1):
        bx(s * 0.38 - 0.04, cy - 0.04, 0.09, s * 0.38 + 0.04, cy + 0.04, 1.34, "wood", bevel=0.006)
        tube((s * 0.38, cy, 1.02), (s * 0.20, cy, 1.36), 0.022, "wood_dark", seg=8)
        cyl(s * 0.38, cy, 0.09, 0.15, 0.065, "brass_dark", seg=12)

    def zl(x):
        return 1.28 + 0.10 * math.cos(math.pi * x / 0.96)
    xs = [-0.46 + 0.92 * i / 14 for i in range(15)]
    pts = [(x, zl(x)) for x in xs] + [(x, zl(x) + 0.11) for x in reversed(xs)]
    prism_y(pts, cy - 0.06, cy + 0.06, "wood_dark")
    crown(0, cy, 1.49, r=0.08)
    bx(-0.035, cy - 0.03, 1.30, 0.035, cy + 0.03, 1.40, "iron")
    lathe([(0, 0.84), (0.25, 0.84), (0.265, 0.87), (0.215, 0.95), (0.175, 1.07), (0.155, 1.19), (0.115, 1.28), (0.05, 1.325),
           (0, 1.33)], 0, cy, "brass", seg=36)
    tor(0, cy, 0.875, 0.262, 0.016, "brass_dark", seg=36, ring=8)
    tor(0, cy, 1.10, 0.17, 0.012, "brass_dark", seg=32, ring=6)
    hexy(0, 1.0, 0.055, cy - 0.215, cy - 0.19, "honey")
    sph(0, cy, 0.82, 0.045, "iron", seg=12)
    cyl(0, cy, 0.36, 0.80, 0.02, "red", seg=10)
    for z in (0.50, 0.62):
        sph(0, cy, z, 0.03, "red", seg=10)
    tor(0, cy, 0.30, 0.06, 0.022, "red", seg=20, ring=8, face="south")
    glow(0, cy - 0.1, 1.05, 0.40, "wall_glow", 0.3)
    bee(0.30, cy, 1.375, s=0.75, yaw=200)


def periscope_desk():
    """Ueberwachung (Wachwabe): Wachpult mit vier sechseckigen Leuchtfenstern in einer Haube und zwei Sehrohren."""
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.64, s * 0.24))
        bx(x0 + 0.012, 0.08, 0, x1 - 0.012, 0.45, 0.07, "wood_dark")
        bx(x0, 0.06, 0.07, x1, 0.46, 0.74, "paint_teal", bevel=0.014)
        for z in (0.23, 0.53):
            panel(x0 + 0.035, x1 - 0.035, z - 0.11, z + 0.11, 0.06, "paint_teal_dark", knob=((x0 + x1) / 2, z))
    bx(-0.24, 0.38, 0.14, 0.24, 0.44, 0.74, "paint_teal_dark")
    bx(-0.67, 0.02, 0.74, 0.67, 0.49, 0.79, "wood", bevel=0.012)
    bx(-0.56, 0.05, 0.79, -0.36, 0.19, 0.815, "red", bevel=0.004)
    bx(-0.55, 0.06, 0.815, -0.37, 0.18, 0.825, "paper", nl=True)
    cyl(0.50, 0.11, 0.79, 0.88, 0.042, "paint_cream", seg=14)
    cyl(0.50, 0.11, 0.875, 0.882, 0.034, "honey", seg=12, nl=True)
    al, base = 26, (0, 0.20, 0.79)
    m = mark()
    hood = [(-0.62, 0), (0.62, 0), (0.62, 0.30), (0.52, 0.42), (-0.52, 0.42), (-0.62, 0.30)]
    prism_y(hood, 0, 0.12, "paint_teal")
    spots = []
    for k, x in enumerate((-0.42, -0.14, 0.14, 0.42)):
        zc = 0.21
        col = "amber_red" if k == 1 else "screen_glow"
        hexy(x, zc, 0.135, -0.014, 0, "brass")
        hexy(x, zc, 0.108, -0.02, -0.014, "screen")
        flat(hexy(x - 0.032, zc - 0.012, 0.034, -0.024, -0.02, col, nl=True))
        flat(hexy(x + 0.022, zc + 0.02, 0.034, -0.024, -0.02, col, nl=True))
        flat(bx(x - 0.055, -0.024, zc - 0.072, x + 0.055, -0.02, zc - 0.058, col, nl=True))
        flat(sph(x, -0.012, 0.375, 0.02, "amber_red" if k == 1 else "glow", seg=8))
        spots.append((x, -0.03, zc, col))
    tilted(m, al, base)
    for (x, y, z, col) in spots:
        glow(*tilt_pt(al, base, (x, y, z)), 0.19, col, 0.32)
    for s in (-1, 1):
        x = s * 0.52
        cyl(x, 0.44, 0.95, 1.36, 0.04, "brass", seg=14)
        cyl(x, 0.44, 1.10, 1.14, 0.05, "brass_dark", seg=14)
        sph(x, 0.44, 1.38, 0.05, "brass", seg=14)
        cyly(x, 1.38, 0.28, 0.44, 0.055, "brass_dark", seg=16)
        cyly(x, 1.38, 0.272, 0.28, 0.042, "glass", seg=14)


def hive_map_table():
    """Admin-Karte (Buero): langer Tisch mit sechseckigen Enden, darauf die Wabenkarte des Stocks, der Brunnen leuchtet."""
    top = [(-0.90, 0.25), (-0.78, 0.02), (0.78, 0.02), (0.90, 0.25), (0.78, 0.48), (-0.78, 0.48)]

    def inset(d):
        return [(-0.90 + d * 1.2, 0.25), (-0.78 + d * 0.5, 0.02 + d), (0.78 - d * 0.5, 0.02 + d), (0.90 - d * 1.2, 0.25),
                (0.78 - d * 0.5, 0.48 - d), (-0.78 + d * 0.5, 0.48 - d)]
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.80, s * 0.58))
        bx(x0 + 0.012, 0.11, 0, x1 - 0.012, 0.41, 0.07, "wood_dark")
        bx(x0, 0.10, 0.07, x1, 0.42, 0.66, "paint_teal", bevel=0.012)
        panel(x0 + 0.03, x1 - 0.03, 0.14, 0.58, 0.10, "paint_teal_dark", knob=((x0 + x1) / 2, 0.36))
    bx(-0.58, 0.23, 0.24, 0.58, 0.28, 0.32, "wood_dark")
    prism(inset(0.05), 0.66, 0.72, "paint_teal_dark")
    prism(top, 0.72, 0.78, "wood")
    prism(inset(0.035), 0.78, 0.788, "brass")
    prism(inset(0.06), 0.788, 0.792, "paper")
    r, st = 0.052, 0.0858
    hstep = math.sqrt(3) * r * 1.1
    tone = {(6, 1): None, (2, 1): "paint_blue", (10, 1): "paint_coral", (4, 2): "paint_teal", (8, 2): "wood_light",
            (4, 0): "paint_mint", (8, 0): "paint_cream", (6, 0): "paint_plum", (6, 2): "wood", (0, 1): "paint_teal_dark",
            (12, 1): "paint_teal"}
    cells = {}
    for ci in range(13):
        rows = (0, 1, 2) if ci % 2 == 0 else (0, 1)
        for ri in rows:
            x = (ci - 6) * st
            y = 0.25 + ((ri - 1) if ci % 2 == 0 else (ri - 0.5)) * hstep
            cells[(ci, ri)] = (x, y)
            if (ci, ri) == (6, 1):
                flat(hexz(x, y, r * 0.92, 0.792, 0.806, "wall_glow"))
            else:
                hexz(x, y, r * 0.92, 0.792, 0.802, tone.get((ci, ri), "comb"))
    for key, mat in (((2, 1), "red"), ((10, 1), "teal_dark"), ((8, 0), "royal"), ((4, 2), "pollen")):
        x, y = cells[key]
        cyl(x, y, 0.802, 0.86, 0.007, "iron", seg=6)
        sph(x, y, 0.87, 0.024, mat, seg=10)
    x, y = cells[(6, 0)]
    crown(x, y, 0.802, r=0.032)
    glow(0, 0.25, 0.82, 0.20, "wall_glow", 0.5)
    bee(0.66, 0.25, 0.792, s=0.7, yaw=160)


def keeper_notebook():
    """Freies Spiel (Mead Hall): aufgeschlagenes Imkerbuch auf gedrechseltem Lesepult mit Leselampe."""
    cy = 0.27
    hexz(0, cy, 0.22, 0, 0.05, "wood_dark")
    lathe([(0, 0.05), (0.10, 0.05), (0.11, 0.08), (0.05, 0.16), (0.045, 0.48), (0.07, 0.54), (0.045, 0.60), (0.045, 0.72),
           (0.09, 0.78), (0, 0.78)], 0, cy, "paint_teal", seg=16)
    tor(0, cy, 0.54, 0.07, 0.014, "brass", seg=16, ring=6)
    al, base = 30, (0, 0.04, 0.80)
    m = mark()
    bx(-0.30, 0, -0.03, 0.30, 0.46, 0.0, "wood", bevel=0.008)
    bx(-0.30, -0.02, -0.03, 0.30, 0.02, 0.05, "wood_dark")
    bx(-0.27, 0.04, 0, 0.27, 0.44, 0.012, "red", bevel=0.004)
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.255, s * 0.008))
        bx(x0, 0.05, 0.012, x1, 0.43, 0.035, "paper", bevel=0.006)
    for k in range(6):
        inkline(-0.23, 0.11 + k * 0.05, -0.05 - (k % 3) * 0.04, 0.11 + k * 0.05, 0.035, w=0.014)
    flower_top(0.13, 0.31, 0.036, 0.065, "petal_pink")
    inkline(0.13, 0.25, 0.12, 0.15, 0.036, w=0.012, mat="leaf_dark")
    for k in range(2):
        inkline(0.04, 0.09 + k * 0.045, 0.22 - k * 0.06, 0.09 + k * 0.045, 0.035, w=0.014)
    bx(-0.014, -0.03, 0.035, 0.014, 0.44, 0.039, "teal", nl=True)
    on_slope(m, al, base)
    sweep(curve([(0.24, 0.44, 0.98), (0.27, 0.45, 1.16), (0.22, 0.42, 1.27), (0.13, 0.36, 1.25)]), 0.012, "brass", seg=8)
    hd = Vector((-0.5, -0.4, -0.75)).normalized()
    hp = Vector((0.13, 0.36, 1.25))
    o = lathe([(0, 0), (0.025, 0), (0.035, 0.02), (0.08, 0.09), (0.08, 0.10), (0, 0.10)], 0, 0, "brass_dark", seg=14)
    orient(o, hp, hd)
    lp = hp + hd * 0.10
    lamp(lp.x, lp.y, lp.z, 0.04, "glow", halo=4.5, strength=0.5)


MOTIFS = ["honey_cans", "chute_hatch", "bellows_filter", "sample_table", "scan_pad", "wasp_cannon_seat", "cooling_comb",
          "air_keypad", "lamp_switches", "gramophone", "queen_bell", "periscope_desk", "hive_map_table", "keeper_notebook"]

C.run(MOTIFS, globals())
