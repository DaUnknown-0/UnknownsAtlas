# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_hall.py - Amberhive-Objekte aus Mead Hall, Queen's Chamber und Brood Nursery (Neubau V2-D, 15.11.2026).
#   blender -b --factory-startup -P props_hall.py -- [art ...]
# Formen: Tisch auf Mittelsaeule mit Dreibeinhockern, Daubenfass mit Zapfhahn, Wappenbanner an Messingstange,
# Wabenthron auf Stufenpodest, Weiselzellen im Messingring, Schaukelwiege mit Haube, Pflegewagen mit zwei Boeden.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from props_common import *  # noqa: E402,F401,F403
import hive_style as S  # noqa: E402

SQ3 = math.sqrt(3)


# ------------------------------------------------------------------ Mead Hall

def stool(x, y, top="teal"):
    for a in (90, 210, 330):
        r = math.radians(a)
        tube((x + math.cos(r) * 0.05, y + math.sin(r) * 0.05, 0.36), (x + math.cos(r) * 0.15, y + math.sin(r) * 0.13, 0.0), 0.03,
             "wood_dark", seg=8, r1=0.02)
    tor(x, y, 0.15, 0.09, 0.012, "brass_dark", seg=16, ring=5)
    cyl(x, y, 0.33, 0.385, 0.165, "wood", seg=20)
    lathe([(0.15, 0), (0.16, 0.022), (0.13, 0.055), (0, 0.066)], top, M=T(x, y, 0.385), seg=20)
    stud(x, y, 0.45, 0.022, "brass", "t")


def tankard(x, y, z, s=1.0, foam=True):
    """Daubenkrug mit Messingreifen, Henkel und Schaumkrone."""
    r, h = 0.065 * s, 0.15 * s
    lathe([(0, 0), (r * 1.1, 0), (r, h), (r * 0.84, h), (r * 0.84, h * 0.8), (0, h * 0.8)], ["wood_light", "wood", "wood_dark"],
          M=T(x, y, z), seg=14, band=[0, 0, 2, 2, 2], stripe=(0, 1))
    hoop(x, y, z + h * 0.2, r * 1.08, "brass", hh=0.024 * s, t=0.008, seg=14)
    hoop(x, y, z + h * 0.82, r * 1.02, "brass", hh=0.024 * s, t=0.008, seg=14)
    tor(x + r * 1.25, y, z + h * 0.5, h * 0.3, 0.014 * s, "wood_dark", seg=12, ring=5, M=R("X", 90))
    if foam:
        sph(x, y, z + h * 0.84, r * 0.86, "foam", seg=12, sz=0.7)
        sph(x - r * 0.5, y - r * 0.5, z + h * 0.95, r * 0.4, "foam", seg=8)
        sph(x + r * 0.45, y - r * 0.2, z + h * 1.0, r * 0.34, "foam", seg=8)


def mead_table(f, n):
    cy = 0.6
    top = [(-0.76, cy), (-0.47, cy - 0.28), (0.47, cy - 0.28), (0.76, cy), (0.47, cy + 0.28), (-0.47, cy + 0.28)]
    # Fusskreuz und gedrechselte Mittelsaeule
    bbox(-0.5, cy - 0.055, 0.0, 0.5, cy + 0.055, 0.09, "wood_dark", r=0.02)
    bbox(-0.055, cy - 0.25, 0.0, 0.055, cy + 0.25, 0.09, "wood_dark", r=0.02)
    for sx in (-1, 1):
        stud(sx * 0.44, cy, 0.09, 0.03, "brass", "t")
    lathe([(0, 0.09), (0.16, 0.09), (0.17, 0.13), (0.1, 0.2), (0.075, 0.4), (0.12, 0.47), (0.12, 0.52), (0.08, 0.58), (0.14, 0.64),
           (0, 0.64)], "wood", M=T(0, cy, 0), seg=16)
    hoop(0, cy, 0.495, 0.122, "brass", hh=0.03, t=0.008, seg=16)
    # Zarge und Konsolen
    prism(inset(top, 0.15), 0.62, 0.7, "wood_dark")
    for sx in (-1, 1):
        ext([(sx * 0.1, 0.63), (sx * 0.56, 0.63), (sx * 0.56, 0.59), (sx * 0.34, 0.53), (sx * 0.16, 0.38), (sx * 0.1, 0.38)],
            cy - 0.035, cy + 0.035, "wood")
    # Platte: dunkler Rand, helle Flaeche, gestrichenes Mittelfeld
    slab(top, 0.7, 0.765, "wood_dark", bev=0.016)
    slab(inset(top, 0.055), 0.765, 0.782, "wood", bev=0.006)
    hexp(0, cy, 0.25, 0.782, 0.786, "brass", sy=0.8)
    hexp(0, cy, 0.22, 0.786, 0.79, "teal", sy=0.8)
    for px, py in inset(top, 0.03):
        stud(px, py, 0.765, 0.022, "brass", "t")
    z = 0.782
    # Kruege
    tankard(-0.45, cy + 0.02, z, 1.2)
    tankard(0.56, cy - 0.03, z, 1.0)
    # Wabenbrot auf dem Brett, Honig laeuft heraus
    cyl(0.27, cy + 0.07, z, z + 0.022, 0.19, "wood_light", seg=24)
    hexp(0.27, cy + 0.08, 0.135, z + 0.022, z + 0.1, "comb")
    comb_top(0.15, 0.39, cy - 0.03, cy + 0.19, z + 0.1, 0.036, "honey", alt="wax_light", pattern=lambda c, r: (c + r) % 3 == 0)
    prism(ellipse_pts(0.3, cy - 0.07, 0.1, 0.045, 14), z + 0.022, z + 0.03, "honey")
    drip(0.3, cy - 0.04, z + 0.09, 0.05, 0.016, "honey")
    # Honigschale mit Loeffel, Kerze
    lathe([(0, 0), (0.05, 0), (0.08, 0.05), (0.074, 0.06), (0, 0.052)], ["brass", "honey"], M=T(-0.13, cy - 0.12, z), seg=14,
          band=[0, 0, 0, 1])
    tube((-0.13, cy - 0.12, z + 0.05), (-0.01, cy - 0.2, z + 0.13), 0.01, "wood_light", seg=6)
    cyl(-0.06, cy + 0.15, z, z + 0.015, 0.06, "brass", seg=14)
    candle(-0.06, cy + 0.15, z + 0.015, 0.11, 0.028, halo=0.3)
    # Hocker davor
    stool(-0.44, 0.18)
    stool(0.44, 0.18)


def mead_barrel(f, n):
    cx, cy, r = 0.0, 0.5, 0.385
    for sx in (-0.2, 0.2):
        bbox(cx + sx - 0.07, cy - 0.37, 0.0, cx + sx + 0.07, cy + 0.37, 0.085, "wood_dark", r=0.02)
    barrel(cx, cy, 0.07, 1.0, r, band="brass_dark")
    zl = 1.027
    # Wabenbrand auf dem Deckel, Spund, Holzhammer
    hexp(cx, cy, 0.19, zl, zl + 0.005, "honey_deep")
    hexp(cx, cy, 0.15, zl + 0.005, zl + 0.009, "wood_light")
    hexp(cx, cy, 0.07, zl + 0.009, zl + 0.013, "honey_deep")
    cyl(cx + 0.21, cy + 0.14, zl, zl + 0.05, 0.042, "wood_dark", seg=10)
    tube((cx - 0.27, cy - 0.02, zl + 0.03), (cx - 0.02, cy - 0.2, zl + 0.03), 0.017, "wood", seg=8)
    tube((cx - 0.31, cy - 0.08, zl + 0.05), (cx - 0.22, cy + 0.05, zl + 0.05), 0.05, "wood_dark", seg=10)
    # Zapfhahn
    yb = cy - barrel_r(r, 0.27)
    disc_y(cx, yb - 0.02, 0.34, 0.065, 0.03, "brass_dark", seg=12)
    tube((cx, yb, 0.34), (cx, yb - 0.14, 0.34), 0.028, "brass", seg=10)
    tube((cx, yb - 0.115, 0.35), (cx, yb - 0.115, 0.25), 0.022, "brass", seg=8)
    tube((cx, yb - 0.07, 0.34), (cx, yb - 0.07, 0.4), 0.013, "brass_dark", seg=6)
    tube((cx - 0.06, yb - 0.07, 0.4), (cx + 0.06, yb - 0.07, 0.4), 0.017, "brass_dark", seg=8)
    drip(cx, yb - 0.115, 0.25, 0.06, 0.016, "honey")
    cyl(cx, yb - 0.1, 0.0, 0.02, 0.075, "brass_dark", seg=14)
    cyl(cx, yb - 0.1, 0.02, 0.026, 0.05, "honey", seg=12)
    # Messingschild
    y2 = cy - barrel_r(r, 0.62) - 0.008
    hexplate(cx, 0.69, 0.11, y2 - 0.014, y2 + 0.03, "brass")
    hexplate(cx, 0.69, 0.075, y2 - 0.02, y2 - 0.014, "honey_deep")
    for a in range(6):
        stud(cx + math.cos(math.radians(a * 60)) * 0.092, y2 - 0.014, 0.69 + math.sin(math.radians(a * 60)) * 0.092, 0.011,
             "brass_dark")


def hive_banner(f, n):
    zr, yr = 1.5, 0.13
    tube((-0.86, yr, zr), (0.86, yr, zr), 0.022, "brass", seg=10)
    for sx in (-1, 1):
        sph(sx * 0.87, yr, zr, 0.048, "brass", seg=12)
        tube((sx * 0.9, yr, zr), (sx * 0.98, yr, zr), 0.03, "brass_dark", seg=8, r1=0.004)
        tube((sx * 0.66, 0.25, zr), (sx * 0.66, yr, zr), 0.018, "brass_dark", seg=8)
        disc_y(sx * 0.66, 0.21, zr, 0.055, 0.035, "brass_dark", seg=10)
    # Haupttuch: Cremerand, Petrolfeld, Spitze mit Quaste
    border = [(-0.5, 1.47), (-0.5, 0.54), (0.0, 0.26), (0.5, 0.54), (0.5, 1.47)]
    ext(border, 0.118, 0.136, "cloth_cream")
    ext(inset(border, 0.05), 0.108, 0.118, "teal_dark")
    ext(inset(border, 0.085), 0.1, 0.108, "teal")
    for x in (-0.4, -0.2, 0.0, 0.2, 0.4):
        bbox(x - 0.05, 0.1, 1.44, x + 0.05, 0.165, 1.54, "cloth_cream", r=0.015)
    lathe([(0, 0), (0.04, 0.03), (0.022, 0.1), (0, 0.11)], "honey", M=T(0, 0.127, 0.14), seg=10)
    sph(0, 0.127, 0.26, 0.03, "brass", seg=8)
    # Wappen: Wabe mit Biene
    zc = 0.99
    hexplate(0, zc, 0.31, 0.09, 0.1, "honey")
    hexplate(0, zc, 0.26, 0.084, 0.09, "honey_light")
    for sx in (-1, 1):
        w = [(sx * (0.13 + 0.12 * math.cos(a) * math.cos(0.6) - 0.055 * math.sin(a) * math.sin(0.6) * sx * sx),
              zc + 0.05 + 0.12 * math.cos(a) * math.sin(0.6) + 0.055 * math.sin(a) * math.cos(0.6))
             for a in [2 * math.pi * i / 16 for i in range(16)]]
        ext(w, 0.074, 0.084, "white")
    ext(ellipse_pts(0, zc - 0.03, 0.1, 0.14, 20), 0.066, 0.078, "bee_yellow")
    for z0, z1 in ((zc - 0.09, zc - 0.055), (zc - 0.015, zc + 0.02)):
        ext([(-0.088, z0), (0.088, z0), (0.088, z1), (-0.088, z1)], 0.06, 0.066, "bee_black")
    ext(ellipse_pts(0, zc + 0.14, 0.07, 0.065, 16), 0.066, 0.078, "bee_black")
    ext([(-0.025, zc - 0.165), (0.025, zc - 0.165), (0.0, zc - 0.215)], 0.066, 0.078, "bee_black")
    # Seitenwimpel mit Schwalbenschwanz
    for sx in (-1, 1):
        sh = [(sx * 0.6, 1.47), (sx * 0.86, 1.47), (sx * 0.86, 0.8), (sx * 0.73, 0.94), (sx * 0.6, 0.8)]
        ext(sh, 0.118, 0.134, "honey")
        hexplate(sx * 0.73, 1.22, 0.075, 0.11, 0.118, "teal_dark")
        for x in (sx * 0.66, sx * 0.8):
            bbox(x - 0.04, 0.1, 1.44, x + 0.04, 0.165, 1.54, "honey", r=0.015)


# ------------------------------------------------------------------ Queen's Chamber

def queen_throne(f, n):
    # Stufenpodest aus Wachs mit Laeufer
    d1 = [(-1.18, 0.03), (1.18, 0.03), (1.18, 0.82), (0.92, 1.08), (-0.92, 1.08), (-1.18, 0.82)]
    slab(d1, 0.0, 0.14, "wax", bev=0.022)
    comb_panel(-1.14, 1.14, 0.012, 0.118, 0.03, 0.046, "wax_light", depth=0.012)
    d2 = [(-0.84, 0.3), (0.84, 0.3), (0.84, 0.86), (0.66, 1.06), (-0.66, 1.06), (-0.84, 0.86)]
    slab(d2, 0.14, 0.27, "wax_light", bev=0.022)
    box(-0.31, 0.017, 0.0, 0.31, 0.31, 0.146, "honey")
    box(-0.27, 0.012, 0.0, 0.27, 0.31, 0.15, "plum_cloth")
    box(-0.31, 0.287, 0.14, 0.31, 0.56, 0.276, "honey")
    box(-0.27, 0.282, 0.14, 0.27, 0.56, 0.28, "plum_cloth")
    # Sitz, Kissen, Armlehnen mit Bernsteinkugeln
    bbox(-0.37, 0.52, 0.27, 0.37, 1.0, 0.6, "wax", r=0.03)
    hexplate(0, 0.44, 0.1, 0.5, 0.52, "brass")
    hexplate(0, 0.44, 0.07, 0.492, 0.5, "amber_glass")
    soft(0, 0.74, 0.64, 0.33, 0.22, 0.065, "plum_cloth", k=0.6)
    for sx in (-1, 1):
        bbox(sx * 0.37, 0.5, 0.27, sx * 0.56, 1.0, 0.85, "comb", r=0.045, seg=3)
        cyl(sx * 0.465, 0.56, 0.85, 0.885, 0.065, "brass", seg=14)
        sph(sx * 0.465, 0.56, 0.95, 0.09, "amber_glass", seg=16)
    # Lehne: Wabenbogen aus Wachszellen mit Bernsteinfenstern
    r = 0.13
    hh = SQ3 * r
    tops = {0: 2.14, 1: 2.0, 2: 1.74, 3: 1.38}
    lit = {(0, 6), (1, 4), (2, 3), (3, 1)}
    for k in range(-3, 4):
        x = k * 1.5 * r
        z = 0.66 + (hh / 2 if k % 2 else 0.0)
        i = 0
        while z + hh / 2 <= tops[abs(k)] + 1e-6:
            ext(S.hexagon_pts(x, z, r * 0.99), 0.985, 1.075, "wax")
            if (abs(k), i) in lit:
                flat(ext(S.hexagon_pts(x, z, r * 0.68), 0.97, 0.985, "glow"))
                glow(x, 0.95, z, 0.26, "glow", 0.42)
            else:
                ext(S.hexagon_pts(x, z, r * 0.68), 0.97, 0.985, ("honey", "amber_glass", "honey_deep")[(abs(k) + i) % 3])
            z += hh
            i += 1
    bbox(-0.29, 0.925, 0.68, 0.29, 0.99, 1.36, "plum_cloth", r=0.05, seg=3)
    for x, z in ((-0.13, 0.9), (0.13, 0.9), (-0.13, 1.16), (0.13, 1.16)):
        stud(x, 0.925, z, 0.022, "brass")
    # Krone auf dem Scheitel
    zc, yc = 2.15, 1.03
    lathe([(0.1, 0), (0.135, 0), (0.135, 0.07), (0.1, 0.07)], "brass", M=T(0, yc, zc), seg=16, loop=True)
    for i in range(6):
        a = math.radians(30 + 60 * i)
        tube((math.cos(a) * 0.118, yc + math.sin(a) * 0.118, zc + 0.06), (math.cos(a) * 0.15, yc + math.sin(a) * 0.15, zc + 0.19), 0.03,
             "brass", seg=6, r1=0.006)
        sph(math.cos(a) * 0.15, yc + math.sin(a) * 0.15, zc + 0.2, 0.022, "royal", seg=8)
    sph(0, yc - 0.135, zc + 0.035, 0.03, "jelly", seg=8)
    # Kerzenleuchter
    for sx in (-1, 1):
        lathe([(0, 0), (0.1, 0), (0.11, 0.03), (0.04, 0.09), (0.03, 0.5), (0.065, 0.56), (0.03, 0.62), (0.09, 0.7), (0.1, 0.725),
               (0, 0.725)], "brass", M=T(sx * 1.0, 0.64, 0.14), seg=14)
        candle(sx * 1.0, 0.64, 0.865, 0.3, 0.048, halo=0.42)
        drip(sx * 1.0 - 0.035, 0.6, 1.14, 0.1, 0.014, "wax_light")
    # Gelee-Royale-Schale (rechts) und Honigtopf (links) auf der ersten Stufe
    lathe([(0, 0), (0.1, 0), (0.1, 0.03), (0.05, 0.07), (0.045, 0.2), (0.08, 0.26), (0, 0.26)], "wax_dark", M=T(0.66, 0.17, 0.14),
          seg=6)
    lathe([(0, 0.26), (0.06, 0.26), (0.15, 0.33), (0.155, 0.36), (0.13, 0.36), (0, 0.34)], ["brass", "jelly"], M=T(0.66, 0.17, 0.14),
          seg=18, band=[0, 0, 0, 0, 1])
    flat(cyl(0.66, 0.17, 0.495, 0.5, 0.1, "jelly_light", seg=14))
    glow(0.66, 0.17, 0.5, 0.3, "jelly", 0.4)
    tube((0.7, 0.15, 0.5), (0.84, 0.1, 0.62), 0.011, "brass", seg=6)
    lathe([(0, 0), (0.09, 0), (0.125, 0.06), (0.13, 0.12), (0.115, 0.19), (0.085, 0.24), (0.09, 0.26), (0, 0.26)],
          ["brass", "brass_dark", "honey"], M=T(-0.66, 0.17, 0.14), seg=16, band=[0, 0, 1, 0, 1, 0, 2])
    tube((-0.66, 0.17, 0.4), (-0.56, 0.12, 0.56), 0.011, "wood_light", seg=6)
    lathe([(0, 0), (0.028, 0.012), (0.028, 0.05), (0, 0.06)], "wood_light", M=T(-0.56, 0.12, 0.54), seg=8)
    drip(-0.6, 0.085, 0.38, 0.08, 0.014, "honey")


def rcell(x, y, z, h, r, lx=0.0, ly=0.0, opened=False):
    """Weiselzelle: laenglicher, geringelter Wachszapfen; opened = Deckel ab, Gelee leuchtet."""
    prof = [(0, 0), (0.55, 0.0), (0.86, 0.07), (1.0, 0.2), (0.92, 0.3), (1.0, 0.42), (0.9, 0.53), (0.93, 0.62), (0.74, 0.76)]
    if opened:
        prof += [(0.6, 0.76), (0.56, 0.7), (0, 0.7)]
        band = [0, 1, 0, 1, 0, 1, 0, 1, 2, 2, 2]
    else:
        prof += [(0.5, 0.88), (0.26, 0.97), (0, 1.0)]
        band = [0, 1, 0, 1, 0, 1, 0, 1, 2, 2, 2]
    M = T(x, y, z) @ R("Y", lx) @ R("X", ly)
    lathe([(a * r, b * h) for a, b in prof], ["wax", "comb", "wax_dark"], M=M, seg=16, band=band)
    if opened:
        flat(lathe([(0, 0.7 * h), (0.54 * r, 0.7 * h), (0, 0.72 * h)], "jelly_light", M=M, seg=14))


def royal_cells(f, n):
    slab(rrect(-0.66, 0.05, 0.66, 0.75, 0.14), 0.0, 0.1, "paint_plum", bev=0.02)
    slab(rrect(-0.58, 0.1, 0.58, 0.7, 0.12), 0.1, 0.17, "wood_dark", bev=0.015)
    slab(rrect(-0.5, 0.15, 0.5, 0.65, 0.2), 0.17, 0.29, "wax", bev=0.05, rounded=True)
    comb_panel(-0.36, 0.36, 0.175, 0.26, 0.152, 0.036, "honey", depth=0.01)
    for x in (-0.5, -0.25, 0.25, 0.5):
        stud(x, 0.05, 0.05, 0.02, "brass")
    # Messingring auf vier Stuetzen haelt die Zapfen
    for a in (38, 142, 218, 322):
        x, y = math.cos(math.radians(a)) * 0.52, 0.4 + math.sin(math.radians(a)) * 0.3
        tube((x, y, 0.1), (x, y, 0.74), 0.02, "brass", seg=8)
        sph(x, y, 0.77, 0.034, "brass", seg=10)
    tor(0, 0.4, 0.7, 0.52, 0.02, "brass", seg=40, ring=6, M=SC(1.0, 0.58, 1.0))
    # Zapfen: drei hohe hinten, zwei vorn (einer geoeffnet)
    rcell(-0.31, 0.5, 0.26, 0.98, 0.155, lx=-7)
    rcell(0.02, 0.55, 0.26, 1.2, 0.17)
    rcell(0.33, 0.5, 0.26, 1.04, 0.155, lx=8)
    rcell(-0.17, 0.3, 0.26, 0.78, 0.14, lx=-4, ly=6, opened=True)
    rcell(0.2, 0.29, 0.26, 0.74, 0.135, lx=6, ly=8)
    glow(-0.21, 0.24, 0.84, 0.17, "jelly_light", 0.4)
    lathe([(0, 0), (0.09, 0), (0.07, 0.05), (0.03, 0.085), (0, 0.09)], "wax_dark", M=T(-0.52, 0.2, 0.1) @ R("Y", -25), seg=12)
    # Schleife mit Marke am Ring
    for sx in (-1, 1):
        sph(sx * 0.055, 0.092, 0.7, 0.05, "plum_cloth", seg=10, sx=1.1, sy=0.5, sz=0.75)
        ext([(sx * 0.01, 0.69), (sx * 0.05, 0.56), (sx * 0.1, 0.58), (sx * 0.04, 0.7)], 0.085, 0.095, "plum_cloth")
    sph(0, 0.085, 0.7, 0.028, "brass", seg=8)


# ------------------------------------------------------------------ Brood Nursery

def brood_cradle(f, n):
    R0 = 0.95

    def rocker(y0, y1):
        low = [(-0.5 + i * 0.1, R0 - math.sqrt(R0 * R0 - (-0.5 + i * 0.1) ** 2)) for i in range(11)]
        ext(low + [(x, z + 0.08) for x, z in reversed(low)], y0, y1, "wood")
        for sx in (-1, 1):
            sph(sx * 0.5, (y0 + y1) / 2, 0.185, 0.05, "wood_dark", seg=10)
            box(sx * 0.33 - 0.035, y0, 0.1, sx * 0.33 + 0.035, y1, 0.3, "wood")
    rocker(0.05, 0.115)
    rocker(0.585, 0.65)
    # Korb: unten schmal, oben weit, Cremerand
    loft([[(x, y, 0.22) for x, y in rrect(-0.4, 0.12, 0.4, 0.58, 0.08)], [(x, y, 0.5) for x, y in rrect(-0.47, 0.07, 0.47, 0.63, 0.1)]],
         "paint_mint")
    with xf(about(R("X", 10.1), (0, 0.12, 0.22))):
        comb_panel(-0.36, 0.36, 0.245, 0.49, 0.12, 0.046, "paint_cream", depth=0.012)
    slab(rrect(-0.495, 0.045, 0.495, 0.655, 0.115), 0.5, 0.545, "paint_cream", bev=0.016, rounded=True)
    prism(rrect(-0.43, 0.105, 0.43, 0.595, 0.08), 0.54, 0.55, "cloth_white")
    # Haube am Kopfende
    hood = []
    for x, k in ((-0.5, 0.45), (-0.47, 0.72), (-0.42, 0.9), (-0.35, 1.0), (-0.24, 1.0)):       # Viertelkuppel, nach rechts offen
        hood.append([(x, y, z) for y, z in arc(0.35, 0.53, 0.31 * k, 0, 180, 12, rz=0.37 * k) +
                     arc(0.35, 0.53, 0.27 * k, 180, 0, 12, rz=0.33 * k)])
    loft(hood, "paint_cream")
    ext(arc(0.35, 0.53, 0.325, 0, 180, 12, rz=0.385) + arc(0.35, 0.53, 0.29, 180, 0, 12, rz=0.35), -0.255, -0.215, "paint_mint_dark",
        axis="x")
    sph(-0.4, 0.35, 0.89, 0.04, "brass", seg=10)
    # Kissen, Larve (schlaeft), Decke
    soft(-0.07, 0.35, 0.575, 0.16, 0.2, 0.045, "cloth_white", k=0.55)
    sph(-0.05, 0.35, 0.655, 0.118, "larva", seg=16, sz=0.85)
    for sy in (-1, 1):
        sph(-0.085, 0.35 + sy * 0.048, 0.747, 0.024, "ink", seg=8, sx=0.35, sz=0.4)
        sph(-0.035, 0.35 + sy * 0.08, 0.722, 0.024, "petal_pink", seg=8, sz=0.4)
    soft(0.2, 0.35, 0.575, 0.275, 0.255, 0.105, "mint_cloth", k=0.45)
    soft(-0.01, 0.35, 0.6, 0.055, 0.245, 0.075, "cloth_white", k=0.5)
    for x, y, z in ((0.2, 0.35, 0.684), (0.35, 0.25, 0.662), (0.35, 0.45, 0.662), (0.08, 0.22, 0.664), (0.08, 0.48, 0.664)):
        noline(hexp(x, y, 0.042, 0.6, z, "paint_cream"))


def bottle(x, y, z, s=1.0, fill="honey_light"):
    """Saugflasche: Glas mit Nektar, Ring, Sauger."""
    lathe([(0, 0), (0.045 * s, 0), (0.05 * s, 0.02 * s), (0.05 * s, 0.11 * s), (0.05 * s, 0.14 * s), (0.032 * s, 0.17 * s),
           (0, 0.17 * s)], [fill, "glass"], M=T(x, y, z), seg=12, band=[0, 0, 0, 1, 1, 1])
    cyl(x, y, z + 0.165 * s, z + 0.19 * s, 0.038 * s, "paint_cream", seg=12)
    lathe([(0.03 * s, 0), (0.03 * s, 0.018 * s), (0.012 * s, 0.034 * s), (0.015 * s, 0.055 * s), (0, 0.062 * s)], "coral",
          M=T(x, y, z + 0.19 * s), seg=10)


def nurse_cart(f, n):
    x0, x1, y0, y1 = -0.46, 0.36, 0.07, 0.43
    for x in (x0 + 0.07, x1 - 0.07):
        for y in (y0 + 0.035, y1 - 0.035):
            disc_y(x, y - 0.02, 0.06, 0.06, 0.04, "wood_dark", seg=14)
            disc_y(x, y - 0.027, 0.06, 0.024, 0.008, "brass", seg=8)
            tube((x, y, 0.06), (x, y, 0.2), 0.016, "brass_dark", seg=6)
    for x in (x0 + 0.04, x1 - 0.04):
        for y in (y0 + 0.035, y1 - 0.035):
            tube((x, y, 0.16), (x, y, 0.78), 0.02, "brass", seg=8)
            sph(x, y, 0.8, 0.034, "brass", seg=10)
    for z in (0.2, 0.62):
        slab(rrect(x0, y0, x1, y1, 0.05), z, z + 0.045, "paint_cream", bev=0.012)
        box(x0 + 0.09, y0 - 0.006, z + 0.006, x1 - 0.09, y0 + 0.01, z + 0.036, "paint_mint")
        for y in (y0 + 0.035, y1 - 0.035):
            tube((x0 + 0.04, y, z + 0.125), (x1 - 0.04, y, z + 0.125), 0.011, "brass", seg=6)
    # Schiebegriff
    sweep([(x1 - 0.04, y0 + 0.035, 0.74), (x1 + 0.08, y0 + 0.035, 0.85), (x1 + 0.13, y0 + 0.07, 0.87), (x1 + 0.13, y1 - 0.07, 0.87),
           (x1 + 0.08, y1 - 0.035, 0.85), (x1 - 0.04, y1 - 0.035, 0.74)], 0.016, "brass", seg=8)
    tube((x1 + 0.13, y0 + 0.1, 0.87), (x1 + 0.13, y1 - 0.1, 0.87), 0.027, "wood", seg=10)
    zt = 0.665
    # oben: Pollenbrot, Flaeschchen, Pipetten, Geleeglas
    cyl(-0.31, 0.25, zt, zt + 0.016, 0.115, "wood_light", seg=16)
    soft(-0.31, 0.25, zt + 0.07, 0.095, 0.085, 0.06, "pollen", k=0.35)
    for dx in (-0.03, 0.03):
        box(-0.31 + dx - 0.005, 0.175, zt + 0.09, -0.31 + dx + 0.005, 0.325, zt + 0.132, "bread_dark")
    bottle(-0.12, 0.3, zt, 1.15)
    bottle(-0.03, 0.2, zt, 0.9, fill="petal_white")
    bbox(0.07, 0.2, zt, 0.22, 0.3, zt + 0.05, "wood", r=0.01)
    for i, c in enumerate(("jelly", "honey", "jelly")):
        x = 0.1 + i * 0.045
        tube((x, 0.25, zt + 0.03), (x, 0.25, zt + 0.17), 0.014, "glass", seg=8)
        tube((x, 0.25, zt + 0.03), (x, 0.25, zt + 0.11), 0.015, c, seg=8)
        sph(x, 0.25, zt + 0.19, 0.024, "coral", seg=8, sz=1.2)
    honeyjar(0.28, 0.3, zt, 0.055, 0.15, fill="jelly", cap="plum_cloth")
    # unten: Tuecher und Pollenschale
    zb = 0.245
    for i, c in enumerate(("cloth_white", "mint_cloth", "cloth_white")):
        bbox(-0.38, 0.13, zb + i * 0.045, -0.1, 0.37, zb + i * 0.045 + 0.042, c, r=0.016)
    lathe([(0, 0), (0.06, 0), (0.12, 0.07), (0.11, 0.08), (0, 0.07)], ["brass", "pollen"], M=T(0.14, 0.25, zb), seg=16,
          band=[0, 0, 0, 1])
    sph(0.14, 0.25, zb + 0.07, 0.085, "pollen", seg=12, sz=0.55)


BUILDERS = {
    "mead_table": mead_table, "mead_barrel": mead_barrel, "hive_banner": hive_banner, "queen_throne": queen_throne,
    "royal_cells": royal_cells, "brood_cradle": brood_cradle, "nurse_cart": nurse_cart,
}

if __name__ == "__main__":
    main(BUILDERS)
