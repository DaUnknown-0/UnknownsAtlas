# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_art.py - Moonlight Carnival im Among-Us-Stil (Stilblatt, docs/PARK_KONZEPT.md "Stil und Grafik").
#
# Gleiche Regeln wie museum_art.py (kraeftige Umrisse, flache Flaechen mit Licht- und Schattenkante,
# schraege Aufsicht K = 0,55, Standlinie = Kollision), dazu die Park-Palette: verblasstes Budenrot und
# Creme, Gold, Pflaume, warmes Gluehbirnenlicht und Leuchtreklame (Neon mit Lichthof).
#
# Stilblatt (Bude, Karussell, Kassenhaeuschen mit Leuchtreklame, Lichtturm) am 23.09. abgenommen, danach
# alle Park-Objekte in diesem Stil.

import math
import random

import museum_art as A
from museum_art import K, OUTLINE, Prop, alpha, hexc, lift, shade

RED = lift("#8e2e36", 1.55)
RED_D = shade(RED, 0.72)
CREAM = hexc("#eadcbc")
CREAM_D = shade(CREAM, 0.8)
GOLD = hexc("#e2b64a")
GOLD_D = shade(GOLD, 0.7)
PLUM = lift("#4a3060", 1.5)
WOOD = lift("#5a3e2a", 1.6)
BULB = hexc("#ffe6a8")
WARM = hexc("#ffd28a")
NEON = {"pink": hexc("#ff5fb8"), "cyan": hexc("#5fe8ff"), "gold": hexc("#ffd15f")}

KINDS = {"bude", "karussell", "kasse", "kassenhaeuschen", "turm", "tunnelwand", "radnabe", "riesenrad", "theke",
         "arena", "zaun", "mischpult", "liege", "spiegel", "kuehltruhe", "regal", "lautsprecher"}
PROP_H = {"bude": 3.2, "karussell": 4.6, "kasse": 3.0, "kassenhaeuschen": 3.0, "turm": 7.0, "tunnelwand": 2.4,
          "radnabe": 1.2, "riesenrad": 7.6, "theke": 1.6, "arena": 1.0, "zaun": 1.1, "mischpult": 1.3, "liege": 0.9,
          "spiegel": 2.5, "kuehltruhe": 1.0, "regal": 2.1, "lautsprecher": 2.3}
BOOTH_SIGNS = ["POPCORN", "HOT DOGS", "CANDY"]


def bulbs(c, pts, r=0.07, glow=0.35):
    for x, y in pts:
        c.glow(x, y, r * 4, BULB, glow)
    for x, y in pts:
        c.ellipse(x, y, r, r, fill=BULB, outline=shade(GOLD_D, 0.8), width=0.015)


def neon(c, x, y, text, size, col, frame=True):
    """Leuchtreklame: dunkles Schild, Lichthof, Schrift in Neonfarbe mit hellem Kern."""
    w = size * 0.62 * len(text) + size * 0.6
    h = size * 1.5
    if frame:
        c.poly([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)],
               fill=hexc("#1c1424"), outline=OUTLINE, width=0.05)
        c.line([(x - w / 2 + 0.05, y + h / 2 - 0.06), (x + w / 2 - 0.05, y + h / 2 - 0.06)], fill=hexc("#3a2a44"), width=0.03)
    c.glow(x, y, w * 0.62, col, 0.55)
    c.text(x, y, text, size, fill=col)
    c.text(x, y, text, size * 0.96, fill=alpha(shade(col, 1.5), 170))


def striped_quad(c, xa0, xa1, ya, xb0, xb1, yb, n, cols):
    """Viereck von Vorderkante (xa0..xa1 auf Hoehe ya) zu Hinterkante (xb0..xb1 auf yb) in n Bahnen."""
    for i in range(n):
        f0, f1 = i / n, (i + 1) / n
        pts = [(xa0 + (xa1 - xa0) * f0, ya), (xa0 + (xa1 - xa0) * f1, ya),
               (xb0 + (xb1 - xb0) * f1, yb), (xb0 + (xb1 - xb0) * f0, yb)]
        c.poly(pts, fill=cols[i % len(cols)])
    c.poly([(xa0, ya), (xa1, ya), (xb1, yb), (xb0, yb)], outline=OUTLINE, width=0.06)


def draw(kind, shape, idx, ppm):
    x0, y0, x1, y1 = A.shape_bounds(shape)
    h = PROP_H[kind]
    p = Prop(x0, y0, x1, y1, h, ppm)
    c = p.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rnd = random.Random(idx * 131 + 7)
    if shape[0] in ("circle", "ellipse"):
        rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
        c.soft_shadow([(cx + 0.1 + rx * math.cos(t * math.pi / 12), cy - 0.1 + ry * math.sin(t * math.pi / 12)) for t in range(24)], 100, 0.1)
    else:
        c.soft_shadow([(x0 + 0.1, y0 - 0.12), (x1 + 0.14, y0 - 0.12), (x1 + 0.14, y1), (x0 + 0.1, y1)], 100, 0.09)

    if kind == "bude":
        # Rueckwand, Theke mit Streifen, zwei Pfosten, gestreiftes Vordach mit Volant, Leuchtreklame
        p.box(x0 + 0.05, y1 - 0.35, x1 - 0.05, y1, 0, 2.3, shade(WOOD, 1.1), shade(RED_D, 0.8))
        c.glow(cx, y1 + 1.2 * K, 1.0, WARM, 0.5)
        for i in range(3):                                             # Ware im Regal
            c.rect(x0 + 0.3 + i * 0.5, y1 - 0.35 + 1.25 * K, x0 + 0.62 + i * 0.5, y1 - 0.35 + 1.55 * K,
                   fill=(GOLD, CREAM, lift("#b04a5a", 1.4))[i], outline=OUTLINE, width=0.02)
        p.box(x0, y0, x1, y0 + 0.7, 0, 1.05, shade(WOOD, 1.25), RED)
        n = 6
        for i in range(n):                                             # Streifen der Thekenfront
            if i % 2:
                xa = x0 + (x1 - x0) * i / n
                c.rect(xa, y0 + 0.03, xa + (x1 - x0) / n, y0 + 1.05 * K - 0.03, fill=CREAM)
        c.poly([(x0, y0), (x1, y0), (x1, y0 + 1.05 * K), (x0, y0 + 1.05 * K)], outline=OUTLINE, width=A.OUT_W)
        for px_ in (x0 + 0.04, x1 - 0.12):
            p.box(px_, y0 + 0.02, px_ + 0.08, y0 + 0.1, 1.05, 1.25, GOLD, GOLD_D, w=0.03)
        front, back = y0 - 0.1 + 2.3 * K, y1 + 2.7 * K
        striped_quad(c, x0 - 0.15, x1 + 0.15, front, x0, x1, back, 7, [RED, CREAM])
        for i in range(7):                                             # Volant
            xa = x0 - 0.15 + (x1 - x0 + 0.3) * (i + 0.5) / 7
            c.ellipse(xa, front, (x1 - x0 + 0.3) / 14, 0.1, fill=(RED if i % 2 == 0 else CREAM), outline=OUTLINE, width=0.03)
        bulbs(c, [(x0 - 0.15 + (x1 - x0 + 0.3) * i / 8, front - 0.12) for i in range(9)])
        neon(c, cx, back + 0.35, BOOTH_SIGNS[idx % len(BOOTH_SIGNS)], 0.26, (NEON["pink"], NEON["cyan"], NEON["gold"])[idx % 3])

    elif kind in ("kasse", "kassenhaeuschen"):
        # Haeuschen mit Fenster, warmem Licht, Spitzdach und "TICKETS" in Neon
        p.box(x0, y0, x1, y1, 0, 2.0, shade(CREAM, 1.05), CREAM)
        for i in range(int((x1 - x0) / 0.3)):                          # Bretterfugen
            xa = x0 + 0.3 * (i + 1)
            c.line([(xa, y0 + 0.05), (xa, y0 + 2.0 * K - 0.05)], fill=CREAM_D, width=0.02)
        c.rect(x0, y0, x1, y0 + 0.5 * K, fill=RED, outline=OUTLINE, width=0.04)
        wx0, wx1 = cx - min(0.7, (x1 - x0) * 0.3), cx + min(0.7, (x1 - x0) * 0.3)
        c.rect(wx0, y0 + 0.75 * K, wx1, y0 + 1.7 * K, fill=WARM, outline=OUTLINE, width=0.05)
        c.glow(cx, y0 + 1.2 * K, 0.9, WARM, 0.55)
        c.line([(cx, y0 + 0.75 * K), (cx, y0 + 1.7 * K)], fill=OUTLINE, width=0.03)
        c.rect(wx0 - 0.1, y0 + 0.7 * K, wx1 + 0.1, y0 + 0.78 * K, fill=GOLD, outline=OUTLINE, width=0.02)
        top = y1 + 2.0 * K
        c.poly([(x0 - 0.12, y0 + 2.0 * K), (x1 + 0.12, y0 + 2.0 * K), (x1 + 0.12, top), (x0 - 0.12, top)], fill=RED_D, outline=OUTLINE, width=0.05)
        c.poly([(x0 - 0.12, top), (x1 + 0.12, top), (cx, top + 0.9)], fill=RED, outline=OUTLINE, width=0.05)
        c.ellipse(cx, top + 0.95, 0.08, 0.08, fill=GOLD, outline=OUTLINE, width=0.02)
        neon(c, cx, top + 0.25, "TICKETS", 0.24, NEON["cyan"])

    elif kind == "karussell":
        r = (x1 - x0) / 2
        ry = r * 0.62
        p.cyl(cx, cy - r + ry, r, 0, 0.35, shade(WOOD, 1.2), RED, ry=ry)                 # Plattform
        bulbs(c, [(cx + r * math.cos(t), cy - r + ry + 0.2 * K + ry * math.sin(t)) for t in [math.pi + k * math.pi / 8 for k in range(9)]], 0.06, 0.25)
        base = cy - r + ry + 0.35 * K
        for k, a_ in enumerate((200, 250, 290, 340)):                  # hintere Pferde
            a = math.radians(a_ + 180)
            hx, hy = cx + r * 0.7 * math.cos(a), base + ry * 0.7 * math.sin(a)
            horse(c, hx, hy, 0.75, k % 2 == 0, dim=0.7)
        p.cyl(cx, base - 0.02 + ry * 0.05, 0.45, 0.35, 2.6, shade(PLUM, 1.1), PLUM)      # Mittelsaeule mit Spiegeln
        for k in range(3):
            c.rect(cx - 0.28, base + (0.6 + k * 0.7) * K, cx + 0.28, base + (1.0 + k * 0.7) * K,
                   fill=hexc("#b9cde0"), outline=OUTLINE, width=0.025)
        for k, a_ in enumerate((200, 250, 290, 340)):                  # vordere Pferde
            a = math.radians(a_)
            hx, hy = cx + r * 0.72 * math.cos(a), base + ry * 0.72 * math.sin(a)
            horse(c, hx, hy, 0.95, k % 2 == 1)
        # Dach: Kegel aus Bahnen ueber dem Volantring
        ring = base + 3.0 * K
        apex = ring + 1.4
        segs = 16
        for i in range(segs):
            t0 = math.pi + i * math.pi / segs
            t1 = math.pi + (i + 1) * math.pi / segs
            c.poly([(cx + (r + 0.2) * math.cos(t0), ring + ry * math.sin(t0) * 0.5), (cx + (r + 0.2) * math.cos(t1), ring + ry * math.sin(t1) * 0.5),
                    (cx, apex)], fill=(RED if i % 2 == 0 else CREAM))
        c.poly([(cx - r - 0.2, ring), (cx + r + 0.2, ring), (cx, apex)], outline=OUTLINE, width=0.07)
        for i in range(12):                                            # Volant
            t = math.pi + (i + 0.5) * math.pi / 12
            c.ellipse(cx + (r + 0.2) * math.cos(t), ring + ry * 0.5 * math.sin(t) - 0.12, 0.28, 0.16,
                      fill=(GOLD if i % 2 else RED), outline=OUTLINE, width=0.03)
        bulbs(c, [(cx + (r + 0.2) * math.cos(t), ring + ry * 0.5 * math.sin(t) + 0.04) for t in [math.pi + (k + 0.5) * math.pi / 12 for k in range(12)]])
        c.line([(cx, apex), (cx, apex + 0.35)], fill=OUTLINE, width=0.05)
        c.poly([(cx, apex + 0.35), (cx + 0.4, apex + 0.27), (cx, apex + 0.19)], fill=RED, outline=OUTLINE, width=0.03)

    elif kind == "turm":
        # Lichtturm: Gittermast, oben Plattform mit vier Scheinwerfern
        r = (x1 - x0) / 2
        p.cyl(cx, cy, r * 0.8, 0, 0.4, shade(CREAM, 0.9), shade(CREAM, 0.7), ry=r * 0.5)
        top = cy + 6.0 * K
        steel = hexc("#4a4e5a")
        for sx in (-1, 1):
            c.line([(cx + sx * 0.55, cy + 0.4 * K), (cx + sx * 0.25, top)], fill=OUTLINE, width=0.12)
            c.line([(cx + sx * 0.55, cy + 0.4 * K), (cx + sx * 0.25, top)], fill=steel, width=0.06)
        for k in range(7):                                             # Streben
            ya, yb = cy + (0.4 + k * 0.8) * K, cy + (1.2 + k * 0.8) * K
            wa, wb = 0.55 - 0.3 * k / 7, 0.55 - 0.3 * (k + 1) / 7
            c.line([(cx - wa, ya), (cx + wb, yb)], fill=steel, width=0.035)
            c.line([(cx + wa, ya), (cx - wb, yb)], fill=steel, width=0.035)
        c.rect(cx - 0.8, top - 0.1, cx + 0.8, top + 0.1, fill=RED, outline=OUTLINE, width=0.04)
        for k, sx in enumerate((-0.6, -0.2, 0.2, 0.6)):
            c.glow(cx + sx, top + 0.35, 0.55, BULB, 0.6)
            c.ellipse(cx + sx, top + 0.3, 0.16, 0.14, fill=hexc("#3a3e48"), outline=OUTLINE, width=0.03)
            c.ellipse(cx + sx, top + 0.3, 0.09, 0.08, fill=BULB)
    elif kind == "tunnelwand":
        # Geisterbahn-Trennwand: dunkle Bretter, aufgemalte Fledermaeuse, gruen gluehende Augen
        wood = lift("#2e2238", 1.5)
        p.box(x0, y0, x1, y1, 0, 2.2, shade(wood, 1.2), wood)
        for i in range(int((x1 - x0) / 0.35)):
            xa = x0 + 0.35 * (i + 1)
            c.line([(xa, y0 + 0.05), (xa, y0 + 2.2 * K - 0.05)], fill=shade(wood, 0.7), width=0.025)
        for k in range(int((x1 - x0) / 1.8)):
            bx, by = x0 + 0.9 + k * 1.8, y0 + 1.4 * K
            c.poly([(bx, by), (bx - 0.35, by + 0.15), (bx - 0.25, by - 0.02), (bx - 0.4, by - 0.05), (bx - 0.12, by - 0.1),
                    (bx, by - 0.18), (bx + 0.12, by - 0.1), (bx + 0.4, by - 0.05), (bx + 0.25, by - 0.02), (bx + 0.35, by + 0.15)],
                   fill=hexc("#120c18"))
        for k in range(int((x1 - x0) / 2.4)):
            ex = x0 + 1.6 + k * 2.4
            for dx in (-0.1, 0.1):
                c.glow(ex + dx, y0 + 0.8 * K, 0.25, hexc("#7dff8a"), 0.7)
                c.ellipse(ex + dx, y0 + 0.8 * K, 0.05, 0.035, fill=hexc("#c8ffc8"))

    elif kind == "radnabe":
        # Fuss des Riesenrads: runder Sockel mit Stufen und Lichtern
        r = (x1 - x0) / 2
        p.cyl(cx, cy, r, 0, 0.5, shade(CREAM, 0.95), RED, ry=r * 0.7)
        p.cyl(cx, cy, r * 0.55, 0.5, 0.6, GOLD, GOLD_D, ry=r * 0.4)
        bulbs(c, [(cx + r * math.cos(t), cy + 0.25 * K + r * 0.7 * math.sin(t)) for t in [math.pi + k * math.pi / 7 for k in range(8)]], 0.05, 0.25)

    elif kind == "riesenrad":
        # Das Rad steht aufrecht ueber dem runden Sockel (Glas: sperrt den Weg, nicht die Sicht)
        r = (x1 - x0) / 2
        c.ellipse(cx, cy, r, r * 0.5, outline=alpha(OUTLINE, 150), width=0.05)
        for k in range(24):                                            # Zaun um den Sockel
            t = math.pi + k * math.pi / 23
            fx, fy = cx + r * math.cos(t), cy + r * 0.5 * math.sin(t)
            c.line([(fx, fy), (fx, fy + 0.9 * K)], fill=shade(GOLD_D, 0.9), width=0.04)
        c.ellipse(cx, cy + 0.9 * K, r, r * 0.5, outline=GOLD_D, width=0.05)
        hub = (cx, cy + 4.2 * K + 1.3)
        R = 3.0
        steel = hexc("#6a5a8a")
        for sx in (-1, 1):                                              # A-Stuetzen
            c.line([(cx + sx * 1.6, cy - 0.2), hub], fill=OUTLINE, width=0.2)
            c.line([(cx + sx * 1.6, cy - 0.2), hub], fill=steel, width=0.12)
        for k in range(16):
            a = math.radians(k * 22.5)
            c.line([hub, (hub[0] + R * math.cos(a), hub[1] + R * math.sin(a))], fill=alpha(steel, 220), width=0.04)
        c.ellipse(hub[0], hub[1], R, R, outline=OUTLINE, width=0.14)
        c.ellipse(hub[0], hub[1], R, R, outline=steel, width=0.08)
        c.ellipse(hub[0], hub[1], R - 0.25, R - 0.25, outline=alpha(steel, 200), width=0.04)
        bulbs(c, [(hub[0] + R * math.cos(math.radians(k * 15)), hub[1] + R * math.sin(math.radians(k * 15))) for k in range(24)], 0.05, 0.3)
        for k in range(8):                                             # Gondeln unter den Aufhaengepunkten
            a = math.radians(k * 45 + 22.5)
            gx, gy = hub[0] + R * math.cos(a), hub[1] + R * math.sin(a)
            col = (RED, hexc("#3aa0a0"), GOLD)[k % 3]
            c.line([(gx, gy), (gx, gy - 0.25)], fill=OUTLINE, width=0.04)
            c.poly([(gx - 0.4, gy - 0.25), (gx + 0.4, gy - 0.25), (gx + 0.32, gy - 0.35), (gx - 0.32, gy - 0.35)], fill=CREAM, outline=OUTLINE, width=0.03)
            c.rect(gx - 0.34, gy - 0.8, gx + 0.34, gy - 0.35, fill=col, outline=OUTLINE, width=0.035)
            c.rect(gx - 0.26, gy - 0.55, gx + 0.26, gy - 0.4, fill=shade(col, 0.6))
        c.ellipse(hub[0], hub[1], 0.3, 0.3, fill=GOLD, outline=OUTLINE, width=0.04)

    elif kind == "theke":
        # Schiessbuden-Theke: gestreifte Front, Holzplatte, angekettete Luftgewehre
        p.box(x0, y0, x1, y1, 0, 1.1, shade(WOOD, 1.3), RED)
        n = int((x1 - x0) / 0.5)
        for i in range(n):
            if i % 2:
                xa = x0 + 0.5 * i
                c.rect(xa, y0 + 0.03, xa + 0.5, y0 + 1.1 * K - 0.03, fill=CREAM)
        c.poly([(x0, y0), (x1, y0), (x1, y0 + 1.1 * K), (x0, y0 + 1.1 * K)], outline=OUTLINE, width=A.OUT_W)
        top = y0 + 1.1 * K
        for k in range(int((x1 - x0) / 2.0)):
            gx = x0 + 1.0 + k * 2.0
            c.line([(gx - 0.5, top + 0.15), (gx + 0.45, top + 0.3)], fill=OUTLINE, width=0.07)
            c.line([(gx - 0.5, top + 0.15), (gx - 0.1, top + 0.22)], fill=WOOD, width=0.05)
            c.line([(gx - 0.1, top + 0.22), (gx + 0.45, top + 0.3)], fill=hexc("#5a5e68"), width=0.035)
        bulbs(c, [(x0 + 0.25 + i * 0.5, y0 + 0.08) for i in range(int((x1 - x0) / 0.5))], 0.045, 0.2)

    elif kind == "arena":
        # Autoscooter-Bahn: niedrige Bande mit Gummiprall, drei Wagen, Stromabnehmer-Masten
        plate = lift("#3c4252", 1.5)
        c.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=alpha(plate, 90))
        for (bx0, by0, bx1, by1) in ((x0, y1 - 0.2, x1, y1), (x0, y0, x0 + 0.2, y1), (x1 - 0.2, y0, x1, y1)):
            p.box(bx0, by0, bx1, by1, 0, 0.6, hexc("#26262c"), shade(GOLD, 0.95), w=0.04)
        for (ax, ay, col) in ((cx, y1 - 1.2, GOLD), (x1 - 1.3, y0 + 2.2, hexc("#3aa0a0")), (x0 + 1.1, y0 + 1.3, RED)):
            p.box(ax - 0.5, ay - 0.35, ax + 0.5, ay + 0.35, 0, 0.45, shade(col, 1.15), col, w=0.035)
            c.rect(ax - 0.4, ay - 0.35 + 0.45 * K, ax + 0.4, ay - 0.25 + 0.45 * K, fill=hexc("#1c1c22"))
            c.line([(ax, ay + 0.2), (ax, ay + 2.4 * K)], fill=hexc("#8a8e98"), width=0.03)
            c.glow(ax, ay + 2.4 * K, 0.2, hexc("#9fe8ff"), 0.6)
        p.box(x0, y0, x1, y0 + 0.2, 0, 0.6, hexc("#26262c"), shade(GOLD, 0.95), w=0.04)
        for (mx, my) in ((x0 + 0.1, y0 + 0.1), (x1 - 0.1, y0 + 0.1), (x0 + 0.1, y1 - 0.1), (x1 - 0.1, y1 - 0.1)):
            c.line([(mx, my), (mx, my + 3.0 * K)], fill=OUTLINE, width=0.09)
            c.line([(mx, my), (mx, my + 3.0 * K)], fill=hexc("#8a8e98"), width=0.05)

    elif kind == "zaun":
        # Metallgelaender am Drehkreuz
        steel = hexc("#8a8e98")
        c.line([(x0, y0 + 1.0 * K), (x1, y0 + 1.0 * K)], fill=OUTLINE, width=0.09)
        c.line([(x0, y0 + 1.0 * K), (x1, y0 + 1.0 * K)], fill=steel, width=0.05)
        for i in range(int((x1 - x0) / 0.15) + 1):
            xa = x0 + i * 0.15
            c.line([(xa, y0), (xa, y0 + 1.0 * K)], fill=OUTLINE, width=0.045)
            c.line([(xa, y0), (xa, y0 + 1.0 * K)], fill=steel, width=0.022)

    elif kind == "mischpult":
        p.box(x0, y0, x1, y1, 0, 0.85, hexc("#2c2a34"), lift("#3a2a48", 1.5))
        top = y0 + 0.85 * K
        rnd2 = random.Random(3)
        for i in range(int((x1 - x0) / 0.18)):
            xa = x0 + 0.15 + i * 0.18
            c.line([(xa, top + 0.08), (xa, y1 + 0.85 * K - 0.12)], fill=hexc("#101014"), width=0.02)
            ky = top + 0.1 + rnd2.uniform(0, y1 - y0 - 0.3)
            c.rect(xa - 0.04, ky, xa + 0.04, ky + 0.07, fill=(NEON["pink"], NEON["cyan"], CREAM)[i % 3])
        c.glow(cx, top + 0.3, 1.2, NEON["pink"], 0.25)

    elif kind == "liege":
        white = hexc("#e8ecea")
        for lx in (x0 + 0.1, x1 - 0.15):
            c.line([(lx, y0 + 0.25), (lx, y0 + 0.2 + 0.45 * K)], fill=hexc("#8a8e98"), width=0.04)
        p.box(x0, y0 + 0.2, x1, y1 - 0.2, 0.45, 0.18, white, shade(white, 0.8))
        c.ellipse(x0 + 0.35, y1 - 0.2 + 0.63 * K - 0.2, 0.22, 0.14, fill=hexc("#ffffff"), outline=OUTLINE, width=0.02)
        c.rect(x0 + 0.7, y0 + 0.2 + 0.63 * K, x1 - 0.1, y1 - 0.2 + 0.63 * K, fill=alpha(hexc("#6ab0c0"), 200))

    elif kind == "spiegel":
        # Zerrspiegel: Goldrahmen, spiegelnde Flaeche mit Glanzstreifen (Glas: Sicht bleibt frei)
        p.box(x0, y0, x1, y1, 0, 2.3, alpha(hexc("#cfe4f5"), 150), alpha(hexc("#b9d4ea"), 160), ol=GOLD_D, w=0.06, glass=True)
        if (y1 - y0) > (x1 - x0):
            for f in (0.2, 0.55, 0.85):
                yy = y0 + (y1 - y0) * f
                c.line([(x0 + 0.05, yy + 0.3), (x1 - 0.05, yy + 1.2)], fill=alpha((255, 255, 255, 255), 120), width=0.04)
        else:
            c.line([(x0 + 0.3, y0 + 0.3), (x0 + 0.8, y0 + 2.0 * K)], fill=alpha((255, 255, 255, 255), 130), width=0.05)
            c.line([(x0 + 0.9, y0 + 0.3), (x0 + 1.2, y0 + 1.3 * K)], fill=alpha((255, 255, 255, 255), 90), width=0.035)

    elif kind == "kuehltruhe":
        white = hexc("#e4ecf0")
        p.box(x0, y0, x1, y1, 0, 0.85, alpha(hexc("#bfe3f5"), 230), white)
        top = y0 + 0.85 * K
        for i, col in enumerate((hexc("#f0a0c0"), hexc("#fff0c0"), hexc("#a8e0a0"), hexc("#c89060"))):
            c.rect(x0 + 0.2 + i * 0.42, top + 0.15, x0 + 0.5 + i * 0.42, top + 0.45, fill=col, outline=OUTLINE, width=0.02)
        c.line([(x0 + 0.1, y0 + 0.4 * K), (x1 - 0.1, y0 + 0.4 * K)], fill=hexc("#8aa0ac"), width=0.03)
        c.text(cx, y0 + 0.2 * K, "ICE CREAM", 0.13, hexc("#3a8ab0"))

    elif kind == "regal":
        steel = hexc("#5a5e68")
        p.box(x0, y0, x1, y1, 0, 2.0, shade(steel, 1.2), hexc("#1e1e24"))
        rnd2 = random.Random(idx + 11)
        for lvl in range(4):
            yy = y0 + (0.1 + lvl * 0.5) * K
            c.rect(x0, yy, x1, yy + 0.05, fill=steel, outline=OUTLINE, width=0.02)
            xa = x0 + 0.05
            while xa < x1 - 0.3:
                wv = rnd2.uniform(0.2, 0.45)
                hv = rnd2.uniform(0.12, 0.2)
                col = rnd2.choice((hexc("#a67c52"), RED, GOLD, hexc("#3aa0a0"), CREAM))
                c.rect(xa, yy + 0.05, xa + wv, yy + 0.05 + hv, fill=col, outline=OUTLINE, width=0.02)
                xa += wv + 0.05
        ty0, ty1 = y0 + 2.0 * K, y1 + 2.0 * K                          # Kisten und Farbeimer oben drauf
        yy = ty0 + 0.1
        while yy < ty1 - 0.4:
            bw, bh = rnd2.uniform(0.4, 0.7), rnd2.uniform(0.3, 0.5)
            bx = rnd2.uniform(x0 + 0.05, max(x0 + 0.06, x1 - bw - 0.05))
            col = rnd2.choice((hexc("#a67c52"), hexc("#8a6440"), GOLD, CREAM))
            c.rect(bx, yy, bx + bw, yy + bh, fill=col, outline=OUTLINE, width=0.03)
            c.line([(bx + 0.05, yy + bh * 0.5), (bx + bw - 0.05, yy + bh * 0.5)], fill=shade(col, 0.75), width=0.02)
            yy += bh + 0.12

    elif kind == "lautsprecher":
        body = hexc("#26242c")
        p.box(x0, y0, x1, y1, 0, 2.1, shade(body, 1.4), body)
        for zz, rr in ((0.35, 0.3), (0.85, 0.22), (1.05, 0.1)):
            c.ellipse(cx, y0 + zz * K * 1.8 + 0.05, rr, rr * 0.9, fill=hexc("#101014"), outline=hexc("#5a5a66"), width=0.03)
            c.ellipse(cx, y0 + zz * K * 1.8 + 0.05, rr * 0.35, rr * 0.3, fill=hexc("#3a3a44"))
        c.glow(cx, y0 + 2.0 * K, 0.35, NEON["cyan"], 0.4)
    return p.c.finish(), p.c.x0, p.c.y0, p.base_y


def lamppost(ppm, on):
    """Laternenpfahl am Weg: Standlinie im Ursprung. Rueckgabe (Bild, Pivot-x, Pivot-y als Anteil)."""
    p = Prop(-0.3, -0.12, 0.3, 0.12, 3.2, ppm)
    c = p.c
    c.soft_shadow([(-0.08, -0.1), (0.14, -0.1), (0.14, 0.06), (-0.08, 0.06)], 90, 0.05)
    iron = hexc("#2c2830")
    c.ellipse(0, 0, 0.12, 0.06, fill=iron, outline=OUTLINE, width=0.02)
    top = 2.7 * K
    c.line([(0, 0), (0, top)], fill=OUTLINE, width=0.08)
    c.line([(0, 0), (0, top)], fill=iron, width=0.045)
    c.line([(0, top), (0.2, top + 0.08)], fill=OUTLINE, width=0.05)
    head = (0.2, top - 0.02)
    lit = BULB if on else hexc("#4a4438")
    if on:
        c.glow(head[0], head[1], 0.5, WARM, 0.7)
    c.poly([(head[0] - 0.09, head[1] + 0.05), (head[0] + 0.09, head[1] + 0.05), (head[0] + 0.07, head[1] - 0.14), (head[0] - 0.07, head[1] - 0.14)],
           fill=lit, outline=OUTLINE, width=0.02)
    c.poly([(head[0] - 0.12, head[1] + 0.05), (head[0] + 0.12, head[1] + 0.05), (head[0], head[1] + 0.14)], fill=RED, outline=OUTLINE, width=0.02)
    img = c.finish()
    return img, (0 - c.x0) / (c.x1 - c.x0), (0 - c.y0) / (c.y1 - c.y0)


def horse(c, x, y, s, up, dim=1.0):
    """Karussellpferd mit Stange (seitlich), up = Pferd gerade oben (Auf und Ab)."""
    dy = 0.18 if up else 0.0
    body = shade(hexc("#f2ede2"), dim)
    c.line([(x, y), (x, y + 2.9 * K)], fill=OUTLINE, width=0.07 * s)
    c.line([(x, y), (x, y + 2.9 * K)], fill=shade(GOLD, dim), width=0.04 * s)
    by = y + (0.55 + dy) * s
    pts = [(-0.35, 0.0), (0.25, 0.0), (0.4, 0.25), (0.5, 0.2), (0.45, -0.05), (0.3, -0.12), (0.28, -0.4), (0.2, -0.4),
           (0.18, -0.15), (-0.2, -0.15), (-0.3, -0.4), (-0.38, -0.4), (-0.34, -0.1)]
    c.poly([(x + px_ * s, by + py_ * s) for px_, py_ in pts], fill=body, outline=OUTLINE, width=0.035)
    c.poly([(x + (-0.35) * s, by), (x - 0.5 * s, by - 0.08 * s), (x - 0.4 * s, by + 0.1 * s)], fill=shade(hexc("#d05a78"), dim), outline=OUTLINE, width=0.025)
    c.rect(x - 0.1 * s, by - 0.02 * s, x + 0.12 * s, by + 0.06 * s, fill=shade(hexc("#3fb0b0"), dim), outline=OUTLINE, width=0.02)
