# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_vents.py - Vent (vent_0 zu .. vent_5 offen, Anker = Mitte) und Ueberwachungskamera (camera_off, camera_on,
# Anker = Pfostenfuss), Stil V2 "Bernsteinlicht".
# Aufruf:  blender -b --factory-startup -P consoles_vents.py -- [vent] [camera]
# Vent: sechseckiger Messingkragen im Boden, runder Schacht, runder Gitterdeckel mit Wabenlochung, Scharnier im Norden.
# Kamera: Waechterbiene, sechskantiges Gehaeuse in Bienenstreifen am Schwanenhals, Linse mit Leuchtring, Lampe am Fuehler.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consoles_common import *  # noqa: E402,F401,F403
import consoles_common as C  # noqa: E402

ANGLES = [0, 14, 34, 60, 88, 112]


def vent(f):
    hexz(0, 0, 0.45, 0, 0.035, "wood_dark")
    hexz(0, 0, 0.42, 0.035, 0.05, "brass")
    for k in range(6):
        a = math.radians(60 * k)
        cyl(0.375 * math.cos(a), 0.375 * math.sin(a), 0.05, 0.058, 0.016, "brass_dark", seg=8, nl=True)
    cyl(0, 0, 0.05, 0.053, 0.31, "propolis", seg=36)                 # Schachtwand, Boden nach Sueden versetzt
    cyl(0, -0.03, 0.053, 0.055, 0.25, "shaft", seg=32, nl=True)
    for y in (-0.10, 0.04):
        bx(-0.10, y - 0.012, 0.055, 0.10, y + 0.012, 0.057, "propolis_light", nl=True)     # Leitersprossen
    tor(0, 0, 0.06, 0.315, 0.026, "brass", seg=40, ring=8)
    hy = 0.33
    for s in (-1, 1):
        bx(s * 0.12 - 0.035, hy - 0.03, 0.05, s * 0.12 + 0.035, hy + 0.04, 0.11, "brass_dark", bevel=0.006)
    cylx(hy, 0.09, -0.16, 0.16, 0.016, "iron", seg=8)
    m = mark()
    cyl(0, 0, 0.066, 0.078, 0.27, "wood_dark", seg=32)               # Unterseite des Deckels
    cyl(0, 0, 0.078, 0.10, 0.305, "brass_dark", seg=36)
    tor(0, 0, 0.10, 0.275, 0.02, "brass", seg=36, ring=8)
    r = 0.052
    for ci in range(-4, 5):
        x = ci * 1.5 * r * 1.06
        for ri in range(-4, 5):
            y = ri * math.sqrt(3) * r * 1.06 + (math.sqrt(3) / 2 * r * 1.06 if ci % 2 else 0)
            if math.hypot(x, y) + r * 0.8 < 0.25 and (ci, ri) != (0, 0):
                hexz(x, y, r * 0.78, 0.10, 0.102, "shaft", nl=True)
    hexz(0, 0, 0.06, 0.10, 0.115, "brass")
    sph(0, 0, 0.125, 0.03, "honey", seg=12)
    rot(since(m), rx=-ANGLES[f], pivot=(0, hy, 0.09))


def camera(on):
    cyl(0, 0, 0, 0.04, 0.12, "wood_dark", seg=20)
    cyl(0, 0, 0.04, 0.08, 0.075, "brass_dark", seg=16)
    sweep(curve([(0, 0, 0.08), (0, 0.0, 0.50), (0, 0.03, 0.82), (0, 0.0, 1.00)]), 0.028, "brass", seg=10)
    cyl(0, 0, 0.42, 0.47, 0.044, "brass_dark", seg=12)
    hc = Vector((0, -0.01, 1.08))
    d = Vector((0, -0.92, -0.39)).normalized()
    eye = "amber_red" if on else "iron_light"
    m = mark()
    lathe([(0, -0.15), (0.075, -0.15), (0.105, -0.11), (0.105, -0.045), (0.105, 0.02), (0.105, 0.07), (0.085, 0.10), (0, 0.10)],
          0, 0, ["bee_yellow", "bee_black", "brass_dark"], seg=6, band=[1, 1, 0, 1, 0, 2, 2])
    lathe([(0, 0.10), (0.07, 0.10), (0.088, 0.16), (0.07, 0.16), (0.058, 0.115), (0, 0.115)], 0, 0, ["brass", "shaft"], seg=18,
          band=[0, 0, 0, 1, 1])
    o = lathe([(0.04, 0.118), (0.058, 0.118), (0.058, 0.124), (0.04, 0.124)], 0, 0, eye, seg=18)
    if on:
        flat(o)
    sph(0, 0, 0.125, 0.04, "black", seg=14, sz=0.6)
    for s in (-1, 1):
        w = ell(s * 0.15, 0, -0.03, 0.085, 0.012, 0.05, "wing", seg=12)
        rot(w, ry=s * 20, pivot=(s * 0.09, 0, -0.03))
    g = since(m)
    orient(g, hc, d)
    up = Vector((0, d.z, -d.y))        # senkrecht zur Blickrichtung, nach oben
    top = hc + up * 0.10 - d * 0.04
    tip = top + up * 0.14 + Vector((0.06, 0, 0))
    sweep(curve([tuple(top), tuple(top + up * 0.09), tuple(tip)]), 0.008, "bee_black", seg=6)
    if on:
        lamp(tip.x, tip.y, tip.z, 0.034, "amber_red", halo=3.4, strength=0.55)
        e = hc + d * 0.13
        glow(e.x, e.y, e.z, 0.12, "amber_red", 0.45)
    else:
        sph(tip.x, tip.y, tip.z, 0.034, "lamp_off", seg=12)


def main():
    sel = set(C.S.args())
    C.setup()
    if want("vent", sel):
        frames([f"vent_{i}" for i in range(6)], vent, shadow=False)
    if want("camera", sel):
        frames(["camera_off", "camera_on"], lambda i: camera(i == 1))


main()
