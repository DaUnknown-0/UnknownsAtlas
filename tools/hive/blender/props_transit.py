# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_transit.py - Amberhive-Etagenwechsel (Neubau V2-D, 15.11.2026): Treppe hinauf (in die Nordwand), Treppenoeffnung
# hinab, Rutscheneinstieg im Boden und Rutschenende aus der Wand.
#   blender -b --factory-startup -P props_transit.py -- [art ...]
# Formen: Holzstufen auf Wachssockeln mit Wabenrelief und Messinggelaender unter einem Wachsbogen; Schacht mit Steinkranz
# und gedrechseltem Gelaender; echter Trichter unter Bodenhoehe (man sieht die Nordwand der Roehre); Messingrohr mit
# Flanschen und Trichtermuendung.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from props_common import *  # noqa: E402,F401,F403
import hive_style as S  # noqa: E402


def circle3(cx, cy, r, z, n=32, ry=None):
    ry = r if ry is None else ry
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n), z) for i in range(n)]


def stair_up(f, n):
    steps, depth, rise = 8, 1.25 / 8, 0.2
    # Wachssockel je Stufe mit Wabenrelief, Holztritt mit Nase; oben wird es dunkel (Durchgang)
    for k in range(steps):
        y0 = k * depth
        z0, z1 = k * rise, (k + 1) * rise
        dark = k >= 6
        box(-0.63, y0, z0, 0.63, 1.25, z1 - 0.045, "wax_dark" if dark else "wax")
        if not dark:
            comb_panel(-0.52, 0.52, z0 + 0.02, z1 - 0.05, y0, 0.042, "wax_light", alt="honey",
                       pattern=lambda c, r, k=k: (c + k * 2) % 5 == 0, depth=0.008)
        bbox(-0.65, y0 - 0.022, z1 - 0.045, 0.65, y0 + depth + 0.004, z1, ("wood_dark" if k == 7 else "wood") if dark else "wood_light",
             r=0.014, seg=2)
    # Wangen aus Wachs mit heller Abdeckung
    for x0, x1 in ((-0.8, -0.65), (0.65, 0.8)):
        ext([(0.0, 0.0), (1.25, 0.0), (1.25, 1.82), (0.0, 0.32)], x0, x1, "wax", axis="x")
        ext([(0.0, 0.32), (1.25, 1.82), (1.25, 1.88), (0.0, 0.38)], x0 - 0.012, x1 + 0.012, "wax_light", axis="x")
        hexplate((x0 + x1) / 2, 0.17, 0.055, -0.008, 0.0, "honey")
    # Gelaender: gedrechselte Antrittspfosten mit Bernsteinkugel, Messingstaebe, Handlauf
    for sx in (-0.725, 0.725):
        leg(sx, 0.07, 0.36, 1.06, 0.05, "wood_dark")
        sph(sx, 0.07, 1.11, 0.07, "amber_glass", seg=14)
        for y in (0.42, 0.78, 1.14):
            zb = 0.38 + 1.5 * y / 1.25
            tube((sx, y, zb - 0.02), (sx, y, zb + 0.56), 0.017, "brass", seg=6)
        tube((sx, 0.07, 0.96), (sx, 1.25, 0.96 + 1.5 * 1.18 / 1.25), 0.03, "brass", seg=10)
    # Durchgang in der Wand: Pfeiler, Bogen mit Schlussstein, dunkle Oeffnung, Wachsnasen
    box(-0.65, 1.2, 1.6, 0.65, 1.3, 2.32, "void")
    for sx in (-1, 1):
        bbox(min(sx * 0.65, sx * 0.92), 1.13, 0.0, max(sx * 0.65, sx * 0.92), 1.34, 2.32, "wax", r=0.02, seg=1)
        box(min(sx * 0.64, sx * 0.94), 1.115, 2.2, max(sx * 0.64, sx * 0.94), 1.34, 2.32, "wax_light")
        comb_panel(min(sx * 0.68, sx * 0.9), max(sx * 0.68, sx * 0.9), 1.84, 2.18, 1.13, 0.046, "comb", depth=0.01)
        lantern(sx * 0.785, 1.07, 1.52, 0.9, lit=True, halo=0.3)
        box(sx * 0.785 - 0.02, 1.07, 1.84, sx * 0.785 + 0.02, 1.13, 1.87, "brass_dark")
    inner = arc(0, 2.32, 0.65, 0, 180, 12, rz=0.34)
    outer = arc(0, 2.32, 0.94, 180, 0, 12, rz=0.56)
    ext(inner + outer, 1.13, 1.34, "wax")
    ext([(0.65, 2.32)] + inner[1:-1] + [(-0.65, 2.32)], 1.24, 1.3, "void")
    for i in range(1, 12, 2):                    # Fugen der Bogensteine
        a = math.radians(180 * i / 12)
        tube((0.67 * math.cos(a), 1.128, 2.32 + 0.35 * math.sin(a)), (0.92 * math.cos(a), 1.128, 2.32 + 0.55 * math.sin(a)), 0.008,
             "wax_dark", seg=4)
    hexplate(0, 2.77, 0.12, 1.1, 1.13, "brass")
    flat(hexplate(0, 2.77, 0.08, 1.09, 1.1, "glow"))
    glow(0, 1.08, 2.77, 0.24, "glow", 0.45)
    for x, Ld in ((-0.42, 0.15), (-0.12, 0.24), (0.28, 0.12), (0.5, 0.18)):
        z = 2.32 + 0.34 * math.sqrt(max(0.0, 1 - (x / 0.65) ** 2))
        drip(x, 1.15, z + 0.01, Ld, 0.03, "wax")


def stair_down(f, n):
    # Steinkranz um den Schacht (Sueden offen, Messingkante am Antritt)
    for x0, x1 in ((-0.8, -0.64), (0.64, 0.8)):
        bbox(x0, 0.0, 0.0, x1, 0.6, 0.06, "stone_dark", r=0.015, seg=1)
    bbox(-0.8, 0.52, 0.0, 0.8, 0.6, 0.06, "stone_dark", r=0.015, seg=1)
    box(-0.64, 0.0, 0.0, 0.64, 0.04, 0.025, "brass")
    # Stufen hinab: Holztritte, nach Norden dunkler und schmaler, darunter Schwarz
    cols = (("wood_light", "wood_dark"), ("wood", "wood_dark"), ("wood_dark", "propolis"), ("propolis", "void"), ("soot", "void"))
    d = 0.4 / len(cols)
    for k, (c, edge) in enumerate(cols):
        y0 = 0.04 + k * d
        ins = 0.022 * k
        noline(box(-0.64 + ins, y0, 0.0, 0.64 - ins, y0 + d - 0.016, 0.012, c))
        noline(box(-0.64 + ins, y0 + d - 0.016, 0.0, 0.64 - ins, y0 + d, 0.012, edge))
    noline(box(-0.56, 0.44, 0.0, 0.56, 0.52, 0.012, "void"))
    for sx in (-1, 1):
        noline(prism([(sx * 0.64, 0.04), (sx * 0.64, 0.52), (sx * 0.53, 0.52)], 0.0, 0.014, "propolis"))
    # Gelaender an drei Seiten: gedrechselte Pfosten, Handlauf, Zwischenholm
    posts = ((-0.72, 0.06), (-0.72, 0.56), (0.72, 0.06), (0.72, 0.56), (0.0, 0.56))
    for x, y in posts:
        leg(x, y, 0.06, 0.56, 0.04, "paint_teal")
        sph(x, y, 0.6, 0.05 if y < 0.1 else 0.04, "amber_glass" if y < 0.1 else "brass", seg=12)
    for sx in (-0.72, 0.72):
        tube((sx, 0.06, 0.52), (sx, 0.56, 0.52), 0.027, "wood_light", seg=10)
        tube((sx, 0.06, 0.3), (sx, 0.56, 0.3), 0.016, "paint_teal_dark", seg=8)
    tube((-0.72, 0.56, 0.52), (0.72, 0.56, 0.52), 0.027, "wood_light", seg=10)
    tube((-0.72, 0.56, 0.3), (0.72, 0.56, 0.3), 0.016, "paint_teal_dark", seg=8)
    # Schild mit Pfeil nach unten am Nordholm
    hexplate(0.36, 0.41, 0.085, 0.525, 0.54, "honey")
    ext([(0.31, 0.44), (0.41, 0.44), (0.36, 0.36)], 0.518, 0.525, "propolis")


def chute_top(f, n):
    cx, cy = 0.0, 0.55
    # Steinkranz als Ring (Sechseck aussen, Kreis innen), damit der Trichter darunter sichtbar bleibt
    hexring = []
    for i in range(36):
        a = 2 * math.pi * i / 36
        rad = 0.55 * math.cos(math.pi / 6) / math.cos((a % (math.pi / 3)) - math.pi / 6)
        hexring.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    loft([[(x, y, 0.0) for x, y in hexring], [(x, y, 0.035) for x, y in hexring], circle3(cx, cy, 0.385, 0.035, 36)], "stone_dark",
         caps=False)
    for i in range(6):
        a = math.pi / 3 * i + math.pi / 6
        hexp(cx + math.cos(a) * 0.435, cy + math.sin(a) * 0.435, 0.085, 0.035, 0.05, "stone")
    # Trichter unter Bodenhoehe: Honigfilm oben, nach unten dunkler; durch den Schraegblick sieht man die Nordwand
    # (jeder Ring bleibt mit r + 0,59 * Tiefe unter dem Oeffnungsradius, sonst ragt er im Bild unter den Suedrand)
    rings = ((0.385, 0.1), (0.37, 0.0), (0.3, -0.1), (0.22, -0.22), (0.15, -0.34), (0.1, -0.42))
    flat(loft([circle3(cx, cy, r, z, 36) for r, z in rings], ["honey_light", "honey", "honey_deep", "propolis", "void"],
              band=[0, 1, 2, 3, 4], caps=False))
    flat(cyl(cx, cy, -0.43, -0.42, 0.1, "void", seg=24))
    for a, Ld in ((66, 0.14), (93, 0.24), (120, 0.12)):          # Honig laeuft an der Nordwand hinab
        r = math.radians(a)
        x, y = cx + math.cos(r) * 0.37, cy + math.sin(r) * 0.37
        flat(tube((x, y, 0.07), (cx + (x - cx) * 0.72, cy + (y - cy) * 0.72, 0.07 - Ld), 0.024, "glow_hot", seg=6, r1=0.012))
    # Messingkragen mit Schrauben
    lathe([(0.385, 0.035), (0.49, 0.035), (0.49, 0.1), (0.45, 0.135), (0.385, 0.11)], "brass", M=T(cx, cy, 0), seg=40, loop=True)
    for i in range(12):
        a = 2 * math.pi * i / 12
        stud(cx + math.cos(a) * 0.455, cy + math.sin(a) * 0.455, 0.115, 0.018, "brass_dark", "t")
    # Haltebuegel ueber dem Nordrand
    path = [(cx + 0.3 * math.cos(math.pi * i / 10), cy + 0.43, 0.1 + 0.28 * math.sin(math.pi * i / 10)) for i in range(11)]
    sweep(path, 0.026, "brass", seg=10)
    for sx in (-1, 1):
        cyl(cx + sx * 0.3, cy + 0.43, 0.035, 0.11, 0.045, "brass_dark", seg=10)
    # Schild: Pfeil nach unten
    tube((cx - 0.48, cy - 0.3, 0.0), (cx - 0.48, cy - 0.3, 0.36), 0.02, "wood_dark", seg=8)
    hexplate(cx - 0.48, 0.42, 0.1, cy - 0.335, cy - 0.31, "honey")
    ext([(cx - 0.53, 0.46), (cx - 0.43, 0.46), (cx - 0.48, 0.37)], cy - 0.342, cy - 0.335, "propolis")


def chute_exit(f, n):
    r = 0.24
    # Wandplatte
    hexplate(0, 0.62, 0.44, 0.66, 0.72, "stone_dark")
    hexplate(0, 0.62, 0.35, 0.645, 0.66, "stone")
    for i in range(6):
        a = math.pi / 3 * i
        stud(0.39 * math.cos(a), 0.645, 0.62 + 0.39 * math.sin(a), 0.024, "brass")
    # Messingrohr im Bogen aus der Wand, Flansche an den Stoessen, Trichtermuendung
    path = [(0, 0.72, 0.62), (0, 0.62, 0.62), (0, 0.55, 0.6), (0, 0.49, 0.56), (0, 0.44, 0.5), (0, 0.4, 0.43), (0, 0.36, 0.36),
            (0, 0.32, 0.31), (0, 0.27, 0.28), (0, 0.22, 0.27), (0, 0.17, 0.265)]
    rad = [r] * 8 + [r + 0.02, r + 0.05, r + 0.075]
    sweep(path, rad, ["brass", "brass_dark"], seg=24, band=[0, 0, 0, 1, 0, 0, 0, 0, 0, 0])
    for (y, z, tilt) in ((0.6, 0.615, 8), (0.42, 0.465, 52)):
        tor(0, y, z, r + 0.012, 0.03, "brass_dark", seg=28, ring=6, M=R("X", 90 - tilt))
        for i in range(8):
            a = 2 * math.pi * i / 8
            p = T(0, y, z) @ R("X", 90 - tilt) @ Vector(((r + 0.014) * math.cos(a), (r + 0.014) * math.sin(a), -0.03))
            sph(p.x, p.y, p.z, 0.017, "brass", seg=6)
    tor(0, 0.165, 0.265, r + 0.075, 0.032, "brass", seg=32, ring=8, M=R("X", 90))
    flat(disc_y(0, 0.166, 0.265, r + 0.05, 0.012, "soot", seg=28))
    flat(disc_y(0, 0.164, 0.245, 0.17, 0.006, "void", seg=24))
    # Honig laeuft aus der Muendung in eine Pfuetze, Tropfen
    ext([(-0.2, 0.03), (0.2, 0.03), (0.15, 0.1), (0.1, 0.13), (-0.1, 0.13), (-0.15, 0.1)], 0.15, 0.17, "honey")
    prism(ellipse_pts(0.0, 0.11, 0.33, 0.1, n=28), 0.0, 0.03, "honey")
    noline(prism(ellipse_pts(0.09, 0.115, 0.13, 0.04, n=18), 0.03, 0.034, "honey_light"))
    sph(-0.4, 0.09, 0.0, 0.055, "honey", seg=10, sz=0.4)
    sph(0.44, 0.16, 0.0, 0.04, "honey", seg=10, sz=0.4)
    drip(0.14, 0.15, 0.1, 0.05, 0.022, "honey")
    drip(-0.24, 0.16, 0.2, 0.07, 0.02, "honey")
    # Sattel mit Messingband unter dem Rohr
    bbox(-0.32, 0.36, 0.0, 0.32, 0.47, 0.13, "wood_dark", r=0.015, seg=1)
    for sx in (-1, 1):
        box(sx * 0.27 - 0.03, 0.35, 0.0, sx * 0.27 + 0.03, 0.36, 0.3, "brass_dark")


BUILDERS = {"stair_up": stair_up, "stair_down": stair_down, "chute_top": chute_top, "chute_exit": chute_exit}

if __name__ == "__main__":
    main(BUILDERS)
