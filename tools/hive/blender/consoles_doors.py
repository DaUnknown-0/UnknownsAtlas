# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_doors.py - Wabenschotten der Amberhive, Stil V2: je Tuer aus art_consoles.json 6 Bilder door_<label>_0 (zu) .. _5 (offen).
# Aufruf:  blender -b --factory-startup -P consoles_doors.py -- [label ...]
# Anker (0,0,0) = Mitte der Oeffnung am Boden (Wandmitte). Alle 6 Bilder einer Tuer haben gleiche Groesse und gleichen Anker.
# axis "y": Tuer in einer waagerechten Wand, von vorn gesehen, Oeffnung = length entlang x, Schott 1,6 m hoch.
# axis "x": Tuer in einer senkrechten Wand, von oben als niedrige Schwelle entlang y (Laenge = length, 0,3 m hoch).
# Rahmen in wood_dark (dunkel wie die Wandkrone) mit Wachskragen (wall_lip) an der Vorderkante, Zellen wie die Wandstirn
# (wall_front, wall_glow): das Schott liest als Teil der Wand.
# Bewegung: das Schott besteht aus Wabensaeulen, die im Boden versinken, die mittleren zuerst, die am Pfosten zuletzt.
# Die Wabenlampe am Sturz zeigt den Zustand: rot = zu, hell = in Bewegung, gruen = offen.

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consoles_common import *  # noqa: E402,F401,F403
import consoles_common as C  # noqa: E402

NF = 6
H = 1.60            # Hoehe des Schotts (axis y)
HT = 0.30           # Hoehe der Schwelle (axis x)
LAG = 0.38          # um so viel der Bewegung laufen die aeusseren Saeulen den mittleren hinterher


def ease(t):
    return t * t * (3 - 2 * t)


def lamp_color(f):
    return "amber_red" if f == 0 else ("lamp_green" if f == NF - 1 else "glow")


def drop(i, n, f):
    """Wie weit Saeule i von n versunken ist (0 = oben, 1 = ganz im Boden)."""
    t = f / (NF - 1)
    c = abs((i + 0.5) - n / 2) / (n / 2)
    return ease(max(0.0, min(1.0, (t - LAG * c) / (1.0 - LAG))))


def cell_mat(i, j):
    k = (i * 7 + j * 3) % 11
    return "wall_glow" if k == 0 else ("wall_lip" if k in (4, 8) else "wall_front")


def door_front(L, f):
    """axis y: von vorn gesehen."""
    n = max(4, int(round(L / 0.25)))
    w = L / n
    r = w / 1.5
    ch = math.sqrt(3) * r
    for s in (-1, 1):                                       # Pfosten
        x0, x1 = sorted((s * L / 2, s * (L / 2 + 0.13)))
        bx(x0, -0.12, 0, x1, 0.14, H + 0.04, "wood_dark", bevel=0.012)
        bx(x0 - 0.012, -0.132, 0, x1 + 0.012, 0.152, 0.10, "wood_dark", bevel=0.008)
        for z in (0.50, 1.05):
            hexy((x0 + x1) / 2, z, 0.04, -0.132, -0.12, "brass", nl=True)
    bx(-L / 2 - 0.16, -0.13, H, L / 2 + 0.16, 0.15, H + 0.20, "wood_dark", bevel=0.014)      # Sturz
    bx(-L / 2 - 0.17, -0.145, H + 0.15, L / 2 + 0.17, -0.095, H + 0.215, "wall_lip", bevel=0.006)        # Kragen wie an der Wand
    hexy(0, H + 0.10, 0.085, -0.148, -0.13, "brass")
    flat(hexy(0, H + 0.10, 0.056, -0.154, -0.148, lamp_color(f)))
    glow(0, -0.16, H + 0.10, 0.17, lamp_color(f), 0.5)
    bx(-L / 2, -0.06, 0, L / 2, 0.06, 0.02, "brass_dark")                                    # Bodenschiene mit Schlitz
    bx(-L / 2 + 0.01, -0.035, 0.02, L / 2 - 0.01, 0.035, 0.023, "shaft", nl=True)
    for i in range(n):
        d = drop(i, n, f)
        if d >= 0.999:
            continue
        xc = -L / 2 + w * (i + 0.5)
        m = mark()
        bx(xc - w / 2 + 0.003, -0.03, 0, xc + w / 2 - 0.003, 0.03, H, "wall_front_b")
        bx(xc - w / 2 + 0.003, -0.045, H - 0.05, xc + w / 2 - 0.003, 0.035, H, "wood_dark")
        zc = ch / 2 + 0.02 + (ch / 2 if i % 2 else 0.0)
        j = 0
        while zc + ch / 2 * 0.86 <= H - 0.05:
            mat = cell_mat(i, j)
            o = hexy(xc, zc, r * 0.86, -0.045, -0.03, mat)
            if mat == "wall_glow":
                flat(o)
            zc += ch
            j += 1
        g = since(m)
        if d > 0:
            move(g, dz=-d * (H + 0.02))
            clip_floor(g)


def door_top(L, f):
    """axis x: von oben gesehen, Schwelle entlang y."""
    n = max(3, int(round(L / 0.30)))
    w = L / n
    for s in (-1, 1):
        y0, y1 = sorted((s * L / 2, s * (L / 2 + 0.13)))
        yc = (y0 + y1) / 2
        bx(-0.21, y0, 0, 0.21, y1, HT + 0.06, "wood_dark", bevel=0.012)
        bx(-0.215, y0 - 0.004, HT + 0.06, 0.215, y1 + 0.004, HT + 0.085, "wall_lip", bevel=0.006)
        hexz(0, yc, 0.06, HT + 0.085, HT + 0.10, "brass", nl=True)
        flat(hexz(0, yc, 0.038, HT + 0.10, HT + 0.106, lamp_color(f), nl=True))
        glow(0, yc, HT + 0.11, 0.13, lamp_color(f), 0.45)
    bx(-0.08, -L / 2, 0, 0.08, L / 2, 0.02, "brass_dark")
    bx(-0.05, -L / 2 + 0.01, 0.02, 0.05, L / 2 - 0.01, 0.023, "shaft", nl=True)
    rr = min(w * 0.5, 0.16) * 0.88
    for i in range(n):
        d = drop(i, n, f)
        if d >= 0.999:
            continue
        yc = -L / 2 + w * (i + 0.5)
        m = mark()
        bx(-0.16, yc - w / 2 + 0.004, 0, 0.16, yc + w / 2 - 0.004, HT, "wall_lip", bevel=0.008)
        bx(-0.165, yc - w / 2 + 0.004, 0, -0.14, yc + w / 2 - 0.004, HT + 0.012, "wood_dark")
        bx(0.14, yc - w / 2 + 0.004, 0, 0.165, yc + w / 2 - 0.004, HT + 0.012, "wood_dark")
        mat = "wall_glow" if i % 3 == 1 else "wall_front_b"
        o = hexz(0, yc, rr, HT, HT + 0.012, mat, flat=False)
        if mat == "wall_glow":
            flat(o)
        g = since(m)
        if d > 0:
            move(g, dz=-d * (HT + 0.03))
            clip_floor(g)


def main():
    sel = set(C.S.args())
    with open(os.path.join(C.HERE, "..", "art_consoles.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    C.setup()
    for d in cfg["doors"]:
        lab, axis, L = d["label"], d["axis"], float(d["length"])
        if not want(lab, sel):
            continue
        names = [f"door_{lab}_{i}" for i in range(NF)]
        build = (lambda f, L=L: door_front(L, f)) if axis == "y" else (lambda f, L=L: door_top(L, f))
        frames(names, build, shadow=False)


main()
