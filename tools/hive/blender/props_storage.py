# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_storage.py - Amberhive-Objekte fuer Lager, Buero, Archiv, Lamphouse und Wachsgiesserei (Neubau V2-D, 15.11.2026).
#   blender -b --factory-startup -P props_storage.py -- [art ...]
# Formen: Apothekerregal mit Schubladen und Bogengiebeln, Fasslager (liegend, stehend, Faesschen), Lattenkisten mit
# Wabenrahmen, Buecherschrank mit Unterbau, Archiv mit Wabenfaechern, Gluehhonig-Gestell, Laternenkarren, Kerzenzieh-Gestell,
# Smoker-Staender.

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from props_common import *  # noqa: E402,F401,F403
import hive_style as S  # noqa: E402

SQ3 = math.sqrt(3)
HONEYS = ("honey", "honey_light", "honey_deep", "amber_glass", "honey")
CAPS = ("cloth_cream", "paint_coral", "teal_light", "cloth_white")
BOOKC = ("paint_teal", "paint_coral", "paint_plum", "paint_blue", "paint_cream", "wood_dark", "royal", "teal_dark", "red",
         "paint_mint")


def rect(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def drawer(x0, x1, z0, z1, y, mat, label=True):
    """Schubladenfront auf der Suedflaeche y: gefaste Platte, Messinggriff, Etikett."""
    slab(rect(x0, z0, x1, z1), y - 0.018, y, mat, bev=0.012, axis="y")
    xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
    tube((xm - 0.05, y - 0.03, zm - 0.04), (xm + 0.05, y - 0.03, zm - 0.04), 0.013, "brass", seg=6)
    for sx in (-1, 1):
        stud(xm + sx * 0.05, y - 0.02, zm - 0.04, 0.016, "brass_dark")
    if label:
        box(xm - 0.06, y - 0.024, zm + 0.025, xm + 0.06, y - 0.018, zm + 0.075, "paper")


# ------------------------------------------------------------------ Honey Cellar

def crock(x, y, z, r, h, mat="stone", band="paint_teal_dark"):
    lathe([(0, 0), (r * 0.8, 0), (r, h * 0.15), (r, h * 0.72), (r * 0.78, h * 0.86), (r * 0.82, h * 0.92), (r * 0.6, h), (0, h)],
          [mat, band, "wood_light"], M=T(x, y, z), seg=16, band=[0, 0, 1, 0, 0, 2, 2])


def jar_shelf(f, n):
    rng = random.Random(7)
    W = 1.58
    box(-W, 0.05, 0.0, W, 0.5, 0.1, "paint_teal_dark")
    box(-W, 0.07, 0.1, W, 0.5, 0.42, "paint_teal")
    dw = (2 * W - 0.08) / 6
    for i in range(6):
        drawer(-W + 0.06 + i * dw, -W + 0.02 + (i + 1) * dw, 0.14, 0.39, 0.07, "paint_cream")
    slab(rrect(-1.6, 0.0, 1.6, 0.5, 0.05), 0.42, 0.47, "wood", bev=0.012)
    box(-W, 0.44, 0.47, W, 0.5, 1.7, "paint_teal_dark")
    posts = (-1.535, -0.515, 0.515, 1.535)
    for x in posts:
        box(x - 0.045, 0.08, 0.47, x + 0.045, 0.5, 1.7, "paint_teal")
        for z in (0.6, 1.1, 1.58):
            stud(x, 0.08, z, 0.018, "brass")
    for z in (0.88, 1.29):
        box(-W, 0.09, z, W, 0.46, z + 0.04, "wood")
    slab(rrect(-1.6, 0.03, 1.6, 0.5, 0.05), 1.7, 1.78, "paint_teal", bev=0.02)
    for xc in (-1.025, 0.0, 1.025):
        ext(arc(xc, 1.78, 0.5, 0, 180, 12, rz=0.16), 0.05, 0.12, "paint_teal_dark")
        hexplate(xc, 1.85, 0.06, 0.038, 0.05, "honey")
    # Glaeser
    for b in range(3):
        xa, xb = posts[b] + 0.06, posts[b + 1] - 0.06
        for li, z in enumerate((0.47, 0.92, 1.33)):
            k = 4 if li == 0 else 5
            for j in range(k):
                x = xa + (j + 0.5) * (xb - xa) / k
                r = (0.098 if li == 0 else 0.08) * rng.uniform(0.9, 1.04)
                h = (0.33 if li == 0 else 0.27) * rng.uniform(0.8, 1.0)
                honeyjar(x, 0.25, z, r, h, fill=rng.choice(HONEYS), cap=rng.choice(CAPS), label="paper" if rng.random() < 0.4 else None)
            tube((xa, 0.11, z + 0.075), (xb, 0.11, z + 0.075), 0.009, "brass", seg=5)
    # oben drauf: Steinguttoepfe, grosses Glas mit Loeffel, Korb mit Wabenstuecken
    zt = 1.78
    crock(-1.25, 0.33, zt, 0.13, 0.26)
    crock(-0.95, 0.3, zt, 0.1, 0.2, band="honey_deep")
    honeyjar(0.38, 0.32, zt, 0.12, 0.3, fill="honey", cap="paint_coral", label="paper")
    tube((0.6, 0.3, zt + 0.02), (0.82, 0.34, zt + 0.02), 0.012, "wood_light", seg=6)
    lathe([(0, 0), (0.03, 0.012), (0.03, 0.05), (0, 0.062)], "wood_light", M=T(0.56, 0.293, zt + 0.02) @ R("Y", 90), seg=8)
    lathe([(0, 0), (0.13, 0), (0.17, 0.12), (0.15, 0.12), (0, 0.1)], ["straw", "straw_dark"], M=T(1.2, 0.31, zt), seg=14,
          band=[0, 0, 1, 1], stripe=(0, 1))
    for dx, dy in ((-0.05, 0.0), (0.06, 0.03), (0.0, -0.05)):
        hexp(1.2 + dx, 0.31 + dy, 0.06, zt + 0.1, zt + 0.16, "comb")
        hexp(1.2 + dx, 0.31 + dy, 0.035, zt + 0.16, zt + 0.165, "honey")


def honey_barrels(f, n):
    # Lager (gestrichen) fuer das liegende Fass
    for y in (0.24, 0.7):
        ext([(-0.47, 0.0), (0.47, 0.0), (0.47, 0.3)] + arc(0, 0.5, 0.385, -31, -149, 10) + [(-0.47, 0.3)], y - 0.055, y + 0.055,
            "paint_teal")
        for sx in (-1, 1):
            stud(sx * 0.4, y - 0.055, 0.2, 0.02, "brass")
    box(-0.4, 0.2, 0.02, 0.4, 0.74, 0.09, "paint_teal_dark")
    M = T(0, 0.92, 0.5) @ R("X", 90)
    barrel(0, 0, 0, 0.84, 0.4, M=M)
    yl = 0.08 + 0.045
    hexplate(0, 0.55, 0.19, yl - 0.008, yl, "honey_deep")
    hexplate(0, 0.55, 0.15, yl - 0.014, yl - 0.008, "wood_light")
    hexplate(0, 0.55, 0.07, yl - 0.02, yl - 0.014, "honey_deep")
    # Zapfhahn unten am Boden des liegenden Fasses, Tropfen und Pfuetze
    disc_y(0, yl - 0.03, 0.28, 0.06, 0.03, "brass_dark", seg=12)
    tube((0, yl, 0.28), (0, yl - 0.12, 0.28), 0.026, "brass", seg=10)
    tube((0, yl - 0.1, 0.29), (0, yl - 0.1, 0.2), 0.02, "brass", seg=8)
    tube((-0.05, yl - 0.06, 0.33), (0.05, yl - 0.06, 0.33), 0.015, "brass_dark", seg=6)
    drip(0, yl - 0.1, 0.2, 0.07, 0.016, "honey")
    prism(ellipse_pts(0.0, 0.03, 0.12, 0.035, 16), 0.0, 0.012, "honey")
    drip(-0.2, yl - 0.012, 0.42, 0.1, 0.016, "honey")
    # stehendes Fass hinten, darauf ein Faesschen mit Honigloeffel
    barrel(0, 1.27, 0.0, 0.8, 0.4)
    barrel(0.04, 1.3, 0.755, 0.42, 0.26, wood="wood_light", wood2="wood", hoops=(0.14, 0.86), band="brass_dark", lid="honey", seg=16)
    zk = 0.755 + 0.42 - 0.045
    flat(noline(cyl(-0.02, 1.27, zk, zk + 0.004, 0.09, "honey_light", seg=12)))
    tube((0.08, 1.3, zk), (0.26, 1.2, zk + 0.2), 0.012, "wood_light", seg=6)
    lathe([(0, 0), (0.03, 0.012), (0.03, 0.05), (0, 0.062)], "wood_light", M=T(0.26, 1.2, zk + 0.19), seg=8)
    drip(0.04, 1.3 - 0.262, zk + 0.02, 0.16, 0.018, "honey")
    drip(-0.1, 1.3 - 0.245, zk + 0.02, 0.08, 0.015, "honey")
    for sx in (-1, 1):                      # Keile
        ext([(sx * 0.2, 0.0), (sx * 0.46, 0.0), (sx * 0.46, 0.12)], 1.5, 1.62, "paint_teal_dark")


def comb_frame(xa, xb, y, ztop, h=0.26):
    """Wabenraehmchen (Flaeche nach Sueden): Oberleiste mit Ohren, Seitenleisten, Wabe mit verdeckelten Zellen."""
    box(xa - 0.035, y - 0.02, ztop - 0.028, xb + 0.035, y + 0.02, ztop, "wood_light")
    box(xa, y - 0.014, ztop - h, xa + 0.022, y + 0.014, ztop - 0.028, "wood_light")
    box(xb - 0.022, y - 0.014, ztop - h, xb, y + 0.014, ztop - 0.028, "wood_light")
    box(xa, y - 0.014, ztop - h, xb, y + 0.014, ztop - h + 0.02, "wood_light")
    box(xa + 0.022, y - 0.007, ztop - h + 0.02, xb - 0.022, y + 0.007, ztop - 0.028, "comb")
    comb_panel(xa + 0.03, xb - 0.03, ztop - h + 0.028, ztop - 0.034, y - 0.007, 0.03, "honey", alt="wax_light",
               pattern=lambda c, r: r >= 3 or (c + r) % 5 == 0, depth=0.008)


def crate(x0, y0, z0, x1, y1, z1, paint, slats=3, open_top=False, seed=3):
    """Lattenkiste: dunkles Inneres, Latten nach Sueden mit Fugen, Eckleisten."""
    box(x0 + 0.03, y0 + 0.025, z0 + 0.02, x1 - 0.03, y1 - 0.03, z1 - (0.07 if open_top else 0.02), "soot")
    planks(x0, y0, z0 + 0.012, x1, y0 + 0.03, z1 - 0.012, paint, slats, axis="z", gap=0.036, bev=0.005, seed=seed)
    box(x0, y1 - 0.03, z0, x1, y1, z1, paint)
    box(x0, y0, z0, x0 + 0.03, y1, z1, paint)
    box(x1 - 0.03, y0, z0, x1, y1, z1, paint)
    for x in (x0 - 0.006, x1 - 0.06):
        box(x, y0 - 0.014, z0, x + 0.066, y0 + 0.034, z1, "wood")
        for z in (z0 + 0.07, z1 - 0.07):
            stud(x + 0.033, y0 - 0.014, z, 0.014, "iron_light")
    if not open_top:
        planks(x0 - 0.012, y0 - 0.012, z1, x1 + 0.012, y1 + 0.012, z1 + 0.032, paint, 4, axis="y", gap=0.006, seed=seed + 1)


def crate_stack(f, n):
    crate(-0.56, 0.08, 0.0, 0.56, 0.76, 0.48, "paint_coral", slats=3)
    hexplate(-0.12, 0.25, 0.1, 0.066, 0.08, "paint_cream")
    hexplate(-0.12, 0.25, 0.055, 0.06, 0.066, "paint_coral_dark")
    # Seilgriff vorn
    sweep([(0.18, 0.07, 0.3), (0.22, 0.045, 0.2), (0.3, 0.035, 0.17), (0.38, 0.045, 0.2), (0.42, 0.07, 0.3)], 0.016, "rope", seg=6)
    # obere Kiste, offen, mit haengenden Raehmchen; eines halb gezogen
    with xf(about(R("Z", -8), (0.05, 0.42, 0.0))):
        crate(-0.4, 0.17, 0.512, 0.44, 0.7, 0.84, "wood_light", slats=2, open_top=True, seed=5)
        for i, y in enumerate((0.25, 0.33, 0.41, 0.57, 0.64)):
            box(-0.4, y - 0.02, 0.815, 0.44, y + 0.02, 0.842, "wood_light")
            box(-0.36, y - 0.008, 0.76, 0.4, y + 0.008, 0.815, "comb")
        comb_frame(-0.34, 0.38, 0.49, 1.06)
        hexplate(0.02, 0.68, 0.075, 0.158, 0.17, "paint_coral")
    # Raehmchen lehnt vorn rechts an der unteren Kiste, Deckel lehnt links
    with xf(about(R("X", -13), (0.0, 0.02, 0.0))):
        comb_frame(0.2, 0.56, 0.035, 0.3, h=0.28)
    bee(0.2, 0.52, 1.085, s=0.42, yaw=160, wing_up=30)


# ------------------------------------------------------------------ Keeper's Office

def book_row(rng, xa, xb, z, hmax, y0, y1):
    x = xa
    while x < xb - 0.05:
        w = rng.uniform(0.05, 0.09)
        h = hmax * rng.uniform(0.72, 1.0)
        c = rng.choice(BOOKC)
        roll = rng.random()
        if roll < 0.1 and x + 0.2 < xb:                       # liegender Stapel
            for i in range(3):
                bbox(x, y0, z + i * 0.058, x + 0.19, y1, z + i * 0.058 + 0.054, rng.choice(BOOKC), r=0.008, seg=1)
            x += 0.2
            continue
        if x + w > xb:
            break
        lean = roll > 0.88 and x + w + h * 0.24 < xb
        if lean:
            with xf(about(R("Y", 13), (x + w, 0, z))):
                bbox(x, y0, z, x + w - 0.004, y1, z + h, c, r=0.008, seg=1)
            x += w + h * 0.24
            continue
        bbox(x, y0, z, x + w - 0.004, y1, z + h, c, r=0.008, seg=1)
        if rng.random() < 0.6:
            box(x + 0.006, y0 - 0.004, z + h * 0.68, x + w - 0.01, y0 + 0.004, z + h * 0.8, "brass" if rng.random() < 0.5 else "paper")
        x += w


def bookshelf(f, n):
    rng = random.Random(21)
    # Unterschrank mit Tueren und Schubladen
    box(-1.16, 0.07, 0.0, 1.16, 0.5, 0.1, "wood_dark")
    box(-1.18, 0.06, 0.1, 1.18, 0.5, 0.78, "wood")
    for sx in (-1, 1):
        xa, xb = (-1.12, -0.44) if sx < 0 else (0.44, 1.12)
        slab(rect(xa, 0.15, xb, 0.74), 0.042, 0.06, "wood_light", bev=0.014, axis="y")
        slab(rect(xa + 0.07, 0.22, xb - 0.07, 0.67), 0.03, 0.042, "paint_teal", bev=0.012, axis="y")
        hexplate((xa + xb) / 2, 0.445, 0.085, 0.022, 0.03, "paint_cream")
        sph(xb - 0.035 if sx < 0 else xa + 0.035, 0.03, 0.46, 0.028, "brass", seg=10)
    for i in range(3):
        drawer(-0.38, 0.38, 0.15 + i * 0.2, 0.33 + i * 0.2, 0.06, "wood_light", label=(i == 1))
    slab(rrect(-1.2, 0.0, 1.2, 0.5, 0.05), 0.78, 0.84, "wood_dark", bev=0.015)
    # Aufsatz
    box(-1.14, 0.44, 0.84, 1.14, 0.5, 1.72, "paint_teal_dark")
    for x in (-1.14, 1.14):
        box(x - 0.04, 0.22, 0.84, x + 0.04, 0.5, 1.72, "wood")
    for x in (-0.38, 0.38):
        box(x - 0.03, 0.24, 0.84, x + 0.03, 0.5, 1.72, "wood")
    for z in (1.13, 1.43):
        box(-1.1, 0.24, z, 1.1, 0.48, z + 0.035, "wood_light")
    rows = ((0.84, 0.25), (1.165, 0.23), (1.465, 0.22))
    for bi, (xa, xb) in enumerate(((-1.09, -0.42), (-0.34, 0.34), (0.42, 1.09))):
        for ri, (z, hm) in enumerate(rows):
            if bi == 1 and ri == 1:                           # Glaeser statt Buecher
                for j, x in enumerate((-0.22, 0.0, 0.22)):
                    honeyjar(x, 0.36, z, 0.075, 0.21, fill=HONEYS[j], cap=CAPS[j], label="paper" if j != 1 else None)
                continue
            book_row(rng, xa, xb, z, hm, 0.27, 0.46)
    slab(rrect(-1.2, 0.17, 1.2, 0.5, 0.05), 1.72, 1.8, "wood_dark", bev=0.02)
    ext(arc(0, 1.8, 0.62, 0, 180, 14, rz=0.17), 0.19, 0.26, "wood")
    hexplate(0, 1.875, 0.075, 0.178, 0.19, "honey")
    # oben: Schriftrollen, Topfpflanze
    zt = 1.8
    for i, (x, dz) in enumerate(((-0.9, 0.0), (-0.78, 0.0), (-0.84, 0.075))):
        tube((x - 0.02, 0.28, zt + 0.045 + dz), (x + 0.03, 0.47, zt + 0.045 + dz), 0.045, "paper", seg=10)
        hoop(0, 0, 0.1, 0.046, "red" if i == 2 else "teal", hh=0.03, t=0.006, M=T(x - 0.02, 0.28, zt + 0.045 + dz) @ aim((0.05, 0.19, 0)),
             seg=10)
    lathe([(0, 0), (0.07, 0), (0.1, 0.11), (0.11, 0.13), (0, 0.12)], ["terracotta", "leaf_dark"], M=T(0.86, 0.36, zt), seg=14,
          band=[0, 0, 0, 1])
    for a in range(7):
        r = math.radians(a * 51)
        sph(0.86 + math.cos(r) * 0.07, 0.36 + math.sin(r) * 0.06, zt + 0.17 + 0.03 * (a % 2), 0.065, "leaf", seg=8, sz=0.55)
    sph(0.86, 0.36, zt + 0.23, 0.06, "leaf", seg=8, sz=0.7)
    # auf der Ablage: Imkerhut, aufgeschlagenes Buch, Tintenfass mit Feder, Kerze
    zc = 0.84
    hat(-0.82, 0.115, zc, s=0.62)
    for sx in (-1, 1):
        with xf(about(R("Y", sx * -9), (0.0, 0, zc))):
            bbox(min(0, sx * 0.17), 0.03, zc, max(0, sx * 0.17), 0.2, zc + 0.03, "paper", r=0.008, seg=1)
    for z in (0.065, 0.1, 0.135):
        box(0.03, z - 0.004, zc + 0.045, 0.14, z + 0.004, zc + 0.05, "ink")
    cyl(0.5, 0.11, zc, zc + 0.07, 0.04, "ink", seg=10)
    tube((0.5, 0.11, zc + 0.06), (0.6, 0.15, zc + 0.3), 0.012, "petal_white", seg=6, r1=0.03)
    cyl(0.88, 0.11, zc, zc + 0.02, 0.06, "brass", seg=14)
    candle(0.88, 0.11, zc + 0.02, 0.13, 0.03, halo=0.3)


def hex_cubbies(xa, xb, z0, z1, rng, r=0.118):
    """Wabenfaecher: Holzwaben mit dunklem Inneren, in den meisten steckt eine Schriftrolle."""
    hh = SQ3 * r
    box(xa, 0.09, z0, xb, 0.36, z1, "paint_plum_dark")
    ncol = int((xb - xa - 2 * r) / (1.5 * r)) + 1
    x_off = (xb - xa - (2 * r + (ncol - 1) * 1.5 * r)) / 2
    for c in range(ncol):
        x = xa + x_off + r + c * 1.5 * r
        z = z0 + hh / 2 + (hh / 2 if c % 2 else 0.0)
        while z + hh / 2 <= z1 + 1e-6:
            ext(S.hexagon_pts(x, z, r * 0.98), 0.07, 0.3, "wood")
            ext(S.hexagon_pts(x, z, r * 0.78), 0.064, 0.07, "soot")
            roll = rng.random()
            if roll < 0.72:
                rr = r * rng.uniform(0.36, 0.5)
                dx, dz = rng.uniform(-0.015, 0.015), -r * 0.78 * 0.86 + rr + 0.004
                disc_y(x + dx, 0.035, z + dz, rr, 0.03, "paper", seg=12)
                disc_y(x + dx, 0.03, z + dz, rr * 0.38, 0.006, "rope", seg=8)
                if roll < 0.2:
                    box(x + dx - 0.012, 0.03, z + dz - rr - 0.05, x + dx + 0.012, 0.036, z + dz - rr * 0.6, rng.choice(("red", "teal")))
            z += hh


def tablet_row(rng, xa, xb, z, hmax):
    """Wachstafeln: stehend von der Kante gesehen, dazwischen einzelne mit der beschriebenen Flaeche nach vorn."""
    x = xa
    while x < xb - 0.04:
        if rng.random() < 0.2 and x + 0.26 < xb:
            w, h = 0.24, hmax * rng.uniform(0.8, 0.95)
            with xf(about(R("X", -8), (0, 0.12, z))):
                box(x, 0.12, z, x + w, 0.15, z + h, "wood_light")
                box(x + 0.022, 0.112, z + 0.022, x + w - 0.022, 0.12, z + h - 0.022, "wax")
                for i in range(3):
                    zz = z + h * (0.72 - i * 0.2)
                    box(x + 0.045, 0.108, zz, x + w - 0.045 - 0.05 * (i == 2), 0.112, zz + 0.014, "propolis_light")
            x += w + 0.015
            continue
        w = rng.uniform(0.034, 0.05)
        h = hmax * rng.uniform(0.7, 0.98)
        bbox(x, 0.12, z, x + w - 0.006, 0.34, z + h, rng.choice(("wood_light", "wood", "wax_dark", "wood_light")), r=0.006, seg=1)
        if rng.random() < 0.5:
            box(x + 0.006, 0.115, z + h * 0.6, x + w - 0.012, 0.12, z + h * 0.72, rng.choice(("red", "teal", "paper", "brass")))
        x += w


# ------------------------------------------------------------------ Archive

def archive_shelf(f, n):
    rng = random.Random(11)
    W = 2.18
    box(-W, 0.06, 0.0, W, 0.4, 0.1, "paint_plum_dark")
    box(-W, 0.07, 0.1, W, 0.4, 0.42, "paint_plum")
    box(-W, 0.36, 0.42, W, 0.4, 1.86, "paint_plum_dark")
    xs = (-2.135, -1.07, 0.0, 1.07, 2.135)
    for b in range(4):
        xa, xb = xs[b] + 0.065, xs[b + 1] - 0.065
        dw = (xb - xa) / 3
        for i in range(3):
            drawer(xa + i * dw + 0.012, xa + (i + 1) * dw - 0.012, 0.14, 0.39, 0.07, "wood")
    slab(rrect(-2.2, 0.01, 2.2, 0.4, 0.05), 0.42, 0.465, "wood_dark", bev=0.012)
    for b in range(4):
        xa, xb = xs[b] + 0.05, xs[b + 1] - 0.05
        if b % 2:
            hex_cubbies(xa, xb, 0.465, 1.86, rng)
        else:
            for z in (0.92, 1.39):
                box(xa, 0.09, z, xb, 0.38, z + 0.035, "wood")
                box(xa, 0.082, z - 0.004, xb, 0.09, z + 0.039, "brass_dark")
            for z, hm in ((0.465, 0.4), (0.955, 0.38), (1.425, 0.38)):
                tablet_row(rng, xa + 0.02, xb - 0.02, z, hm)
    for x in xs:
        box(x - 0.05, 0.035, 0.465, x + 0.05, 0.4, 1.86, "paint_plum")
        box(x - 0.065, 0.025, 1.76, x + 0.065, 0.4, 1.86, "paint_plum")
        hexplate(x, 1.62, 0.035, 0.025, 0.035, "brass")
    slab(rrect(-2.2, 0.0, 2.2, 0.4, 0.05), 1.86, 1.95, "paint_plum", bev=0.022)
    ext(arc(0, 1.95, 0.52, 0, 180, 14, rz=0.19), 0.03, 0.1, "paint_plum_dark")
    hexplate(0, 2.035, 0.09, 0.016, 0.03, "brass")
    hexplate(0, 2.035, 0.06, 0.01, 0.016, "honey")
    # oben drauf: Tafelstapel, Rollenkorb, Lampe, Siegelstempel
    zt = 1.95
    for i in range(4):
        bbox(-1.75 + 0.012 * i, 0.14, zt + i * 0.04, -1.42 + 0.012 * i, 0.36, zt + i * 0.04 + 0.036, ("wood_light", "wood")[i % 2],
             r=0.006, seg=1)
    box(-1.7, 0.16, zt + 0.16, -1.44, 0.34, zt + 0.165, "wax")
    lathe([(0, 0), (0.15, 0), (0.19, 0.16), (0.17, 0.16), (0, 0.13)], ["straw", "straw_dark"], M=T(1.5, 0.24, zt), seg=14,
          band=[0, 0, 1, 1], stripe=(0, 1))
    for dx, dy, lx in ((-0.06, 0.0, -14), (0.05, 0.03, 10), (0.0, -0.05, 2), (0.09, -0.04, 22)):
        ob = lathe([(0, 0), (0.04, 0), (0.04, 0.34), (0, 0.34)], "paper", M=T(1.5 + dx, 0.24 + dy, zt + 0.08) @ R("Y", lx), seg=10)
    lantern(0.75, 0.22, zt, 1.2, lit=True, halo=0.34)
    lathe([(0, 0), (0.05, 0), (0.05, 0.03), (0.02, 0.05), (0.02, 0.12), (0.045, 0.15), (0.045, 0.2), (0, 0.21)], ["brass", "red"],
          M=T(-0.75, 0.22, zt), seg=10, band=[0, 0, 0, 0, 0, 1, 1])


# ------------------------------------------------------------------ Lamphouse

def glow_flask(x, y, z, r, lvl):
    """Gluehhonig im Rundkolben; lvl 0..2 = Leuchtstufe."""
    body = ("glow_dim", "honey_light", "glow_hot")[lvl]
    prof = [(0, 0), (r * 0.6, 0), (r, r * 0.5), (r, r * 1.1), (r * 0.72, r * 1.7), (r * 0.36, r * 2.0), (r * 0.36, r * 2.45),
            (0, r * 2.45)]
    flat(lathe(prof, ["honey_deep", body, "glass"], M=T(x, y, z), seg=14, band=[0, 0, 1, 1, 1, 2, 2]))
    cyl(x, y, z + r * 2.45, z + r * 2.8, r * 0.3, "wood_light", seg=8)
    flat(noline(sph(x - r * 0.42, y - r * 0.7, z + r * 1.15, r * 0.17, "white", seg=6)))
    glow(x, y, z + r, (0.19, 0.25, 0.33)[lvl], "glow", (0.22, 0.4, 0.62)[lvl])


def glow_rack(f, n):
    D = 2.8
    for x in (-0.27, 0.27):
        for y in (0.045, D / 2, D - 0.045):
            cyl(x, y, 0.0, 0.03, 0.045, "iron", seg=10)
            tube((x, y, 0.0), (x, y, 1.98), 0.022, "iron", seg=8)
            sph(x, y, 2.01, 0.038, "brass", seg=10)
        tube((x, 0.045, 1.8), (x, D - 0.045, 1.8), 0.013, "brass", seg=6)
    for y in (0.045, D - 0.045):
        tube((-0.27, y, 1.8), (0.27, y, 1.8), 0.013, "brass", seg=6)
    levels = (0.1, 0.58, 1.06, 1.54)
    for li, z in enumerate(levels):
        bbox(-0.3, 0.02, z, 0.3, D - 0.02, z + 0.045, "wood_dark", r=0.01, seg=1)
        box(-0.3, 0.012, z + 0.006, 0.3, 0.02, z + 0.039, "brass_dark")
    # geschmiedeter Bogen mit Wabenschild an der Stirn
    sweep([(-0.27, 0.045, 1.2), (-0.2, 0.045, 1.36), (0.0, 0.045, 1.44), (0.2, 0.045, 1.36), (0.27, 0.045, 1.2)], 0.014, "iron", seg=6)
    hexplate(0, 1.4, 0.06, 0.02, 0.035, "brass")
    r = 0.105
    for li, z in enumerate(levels[:-1]):
        for c, x in enumerate((-0.135, 0.135)):
            glow_flask(x, 0.2, z + 0.045, r, (li + c - f) % 3)
    z = levels[-1] + 0.045
    for i in range(9):
        for c, x in enumerate((-0.135, 0.135)):
            glow_flask(x, 0.2 + i * 0.3, z, r, (i + c - f) % 3)


def lantern_cart(f, n):
    zb = 0.3
    wheel_y(0.14, 0.02, 0.26, 0.26, rim="wood_dark", spoke="wood", hub="brass", n=8, rot=11)
    wheel_y(0.14, 0.63, 0.26, 0.26, rim="wood_dark", spoke="wood", hub="brass", n=8, rot=11)
    tube((0.14, 0.05, 0.26), (0.14, 0.66, 0.26), 0.024, "iron", seg=8)
    # Pritsche und niedrige Bordwaende
    planks(-0.2, 0.11, zb, 0.44, 0.6, zb + 0.05, "paint_blue", 5, axis="y", gap=0.006, seed=2)
    for y0, y1 in ((0.1, 0.13), (0.58, 0.61)):
        box(-0.2, y0, zb + 0.09, 0.44, y1, zb + 0.16, "paint_blue_dark")
        for x in (-0.18, 0.12, 0.42):
            box(x - 0.022, y0 - 0.006, zb, x + 0.022, y1 + 0.006, zb + 0.2, "wood")
    # Griffholme nach links mit Quergriff, Stuetzbein
    for y in (0.16, 0.55):
        tube((-0.18, y, zb + 0.02), (-0.43, y, zb + 0.2), 0.022, "wood", seg=8)
    tube((-0.43, 0.13, zb + 0.2), (-0.43, 0.58, zb + 0.2), 0.026, "wood_dark", seg=8)
    tube((-0.14, 0.2, zb), (-0.2, 0.2, 0.0), 0.022, "wood", seg=8)
    # Ersatzlaternen (zwei brennen), Oelkanne
    zl = zb + 0.05
    lantern(-0.04, 0.46, zl, 1.3, lit=False, frame="iron_light")
    lantern(0.3, 0.46, zl, 1.4, lit=True)
    lantern(0.12, 0.27, zl, 1.05, lit=True, halo=0.3)
    lantern(-0.1, 0.24, zl, 0.95, lit=False)
    lantern(0.35, 0.25, zl, 0.9, lit=False, frame="iron_light")


# ------------------------------------------------------------------ Wax Foundry

def dipped(x, y, ztop, L, r, mat):
    """Gezogene Kerze am Docht: oben duenn, unten dick mit Tropfnase."""
    tube((x, y, ztop + 0.01), (x, y, ztop - 0.05), 0.006, "rope", seg=4)
    lathe([(0, -0.012), (r * 0.7, 0.008), (r, 0.05), (r * 0.6, L), (0, L + 0.012)], mat, M=T(x, y, ztop - 0.05 - L), seg=10)


def candle_rack(f, n):
    for sx in (-1, 1):
        x = sx * 0.63
        bbox(x - 0.06, 0.02, 0.0, x + 0.06, 0.38, 0.075, "paint_coral_dark", r=0.02)
        box(x - 0.04, 0.16, 0.075, x + 0.04, 0.24, 1.46, "paint_coral")
        lathe([(0.05, 0), (0.055, 0.02), (0.03, 0.045), (0.05, 0.09), (0.03, 0.13), (0, 0.14)], "brass", M=T(x, 0.2, 1.52), seg=10)
        box(x - 0.025, 0.24, 1.27, x + 0.025, 0.33, 1.32, "paint_coral_dark")
        box(x - 0.025, 0.07, 0.92, x + 0.025, 0.16, 0.97, "paint_coral_dark")
    bbox(-0.7, 0.15, 1.44, 0.7, 0.25, 1.52, "paint_coral", r=0.015, seg=1)
    box(-0.6, 0.18, 0.28, 0.6, 0.22, 0.35, "paint_coral_dark")
    tube((-0.66, 0.3, 1.34), (0.66, 0.3, 1.34), 0.015, "brass", seg=8)
    tube((-0.66, 0.09, 0.99), (0.66, 0.09, 0.99), 0.015, "brass", seg=8)
    back = ("wax_light", "wax_light", "wax", "wax", "comb", "honey")
    for i, c in enumerate(back):
        x = -0.5 + i * 0.2
        for dx in (-0.038, 0.038):
            dipped(x + dx, 0.3, 1.34, 0.3 + 0.012 * i, 0.022 + 0.003 * i, c)
    front = ("coral", "wax_light", "coral", "wax_light", "coral")
    for i, c in enumerate(front):
        x = -0.44 + i * 0.22
        for dx in (-0.04, 0.04):
            dipped(x + dx, 0.09, 0.99, 0.3, 0.03, c)
    # Tropfwanne mit Wachsflecken, Kerzenbuendel, Wachstopf
    slab(rrect(-0.57, 0.03, 0.57, 0.37, 0.03), 0.075, 0.125, "wood", bev=0.012)
    for x, y, r in ((-0.36, 0.12, 0.05), (-0.1, 0.1, 0.035), (0.14, 0.13, 0.055), (0.4, 0.1, 0.04), (-0.2, 0.3, 0.04), (0.3, 0.3, 0.05)):
        noline(cyl(x, y, 0.125, 0.131, r, "wax_light", seg=10))
    for i, dz in enumerate((0.0, 0.0, 0.05)):
        y = 0.2 + (i % 2) * 0.06 if i < 2 else 0.23
        tube((0.2, y, 0.155 + dz), (0.52, y, 0.155 + dz), 0.03, "wax_light", seg=8)
    box(0.33, 0.165, 0.126, 0.38, 0.3, 0.24, "teal")
    lathe([(0, 0), (0.07, 0), (0.09, 0.08), (0.08, 0.09), (0, 0.08)], ["brass", "wax"], M=T(-0.38, 0.24, 0.125), seg=12,
          band=[0, 0, 0, 1])


# ------------------------------------------------------------------ Keeper's Office

def smoker_stand(f, n):
    cx, cy = 0.0, 0.36
    for a in (90, 210, 330):
        r = math.radians(a)
        c, s = math.cos(r), math.sin(r)
        sweep([(cx, cy, 0.24), (cx + c * 0.11, cy + s * 0.11, 0.12), (cx + c * 0.26, cy + s * 0.24, 0.03)], [0.032, 0.03, 0.024],
              "paint_teal_dark", seg=8)
        sph(cx + c * 0.26, cy + s * 0.24, 0.03, 0.034, "brass", seg=8)
    leg(cx, cy, 0.18, 0.74, 0.045, "paint_teal")
    # runde Tischplatte mit Messingrand
    cyl(cx, cy, 0.74, 0.79, 0.24, "wood", seg=24)
    hoop(cx, cy, 0.765, 0.24, "brass", hh=0.035, t=0.008, seg=24)
    # Smoker oben auf dem Tisch: Blechkanne mit Messingreifen, Kegeldeckel mit Tuelle, Blasebalg, Rauch
    sx_, sy_, z = cx - 0.05, cy - 0.02, 0.79
    lathe([(0, 0), (0.115, 0), (0.115, 0.27), (0.1, 0.29), (0, 0.29)], "iron_light", M=T(sx_, sy_, z), seg=16)
    hoop(sx_, sy_, z + 0.045, 0.118, "brass", hh=0.035, t=0.008, seg=16)
    hoop(sx_, sy_, z + 0.23, 0.118, "brass", hh=0.035, t=0.008, seg=16)
    for i in range(3):                           # Luftloecher
        disc_y(sx_ - 0.05 + i * 0.05, sy_ - 0.118, z + 0.13, 0.014, 0.008, "soot", seg=6)
    lathe([(0.115, 0), (0.07, 0.08), (0.04, 0.12), (0, 0.12)], "iron", M=T(sx_, sy_, z + 0.27), seg=16)
    tube((sx_, sy_, z + 0.36), (sx_ - 0.15, sy_, z + 0.47), 0.042, "iron", seg=10, r1=0.024)
    ext([(sx_ + 0.115, z + 0.02), (sx_ + 0.27, z + 0.02), (sx_ + 0.2, z + 0.26), (sx_ + 0.115, z + 0.26)], sy_ - 0.08, sy_ + 0.08,
        "leather")
    with xf(about(R("Y", 16.3), (sx_ + 0.27, 0, z + 0.02))):
        box(sx_ + 0.27, sy_ - 0.09, z + 0.01, sx_ + 0.295, sy_ + 0.09, z + 0.28, "wood_light")
        stud(sx_ + 0.283, sy_ - 0.09, z + 0.15, 0.018, "brass")
    puff(sx_ - 0.2, sy_, z + 0.52, 0.05)
    puff(sx_ - 0.25, sy_, z + 0.63, 0.065)
    puff(sx_ - 0.18, sy_, z + 0.75, 0.04)
    # Imkerhut haengt vorn am Pfosten (Krempe zum Betrachter), Handschuh daneben
    tube((cx, cy, 0.52), (cx, cy - 0.2, 0.55), 0.012, "brass", seg=6)
    disc_y(cx, cy - 0.25, 0.42, 0.2, 0.022, "cloth_cream", seg=24)
    lathe([(0.105, 0), (0.1, 0.02), (0.09, 0.09), (0, 0.1)], ["wood_dark", "cloth_cream"], M=T(cx, cy - 0.25, 0.42) @ R("X", 90), seg=16,
          band=[0, 1, 1])
    soft(cx + 0.21, cy - 0.12, 0.44, 0.05, 0.035, 0.1, "leather", k=0.4)
    sph(cx + 0.255, cy - 0.12, 0.48, 0.028, "leather", seg=8, sz=1.4)
    box(cx + 0.16, cy - 0.155, 0.52, cx + 0.265, cy - 0.085, 0.555, "leather_dark")


BUILDERS = {
    "jar_shelf": jar_shelf, "honey_barrels": honey_barrels, "crate_stack": crate_stack, "bookshelf": bookshelf,
    "archive_shelf": archive_shelf, "glow_rack": glow_rack, "lantern_cart": lantern_cart, "candle_rack": candle_rack,
    "smoker_stand": smoker_stand,
}

if __name__ == "__main__":
    main(BUILDERS)
