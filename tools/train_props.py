# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_props.py - Objekt-Sprites des Polaris Express (160 px/m, schraege Aufsicht K = 0,55).
#
# Jedes OPAQUE/GLASS-Rechteck aus gen_train bekommt ein Objekt, dessen Standlinie (Suedkante) genau auf der
# Kollisionskante liegt; dazu die Treppen (Schaechte sind aus der begehbaren Flaeche geschnitten), der Kessel der
# Lok und die beiden Fahrkarten-Lochzangen. draw() liefert (Bild, Welt-x links, Welt-y unten, Standlinie) wie
# park_art.draw.

import math
import random

from PIL import ImageFilter

import handdraw as HD
import museum_art as A
from museum_art import K, OUTLINE, OUT_W, alpha, shade
import train_style as S
from train_style import (BRASS, BRASS_D, BRASS_L, BULB, COAL, COAL_L, CREAM, CREAM_D, GLASS, GREEN_LAMP, INK, IRON,
                         IRON_L, LEATHER, LEATHER_D, LEATHER_L, OAK, OAK_D, PAPER, RED_LAMP, STEEL, STEEL_D, STEEL_L,
                         VELVET, VELVET_D, VELVET_L, WARM, WHITE, WOOD, WOOD_D, WOOD_L, WOOD_X, TProp)

PROP_H = {"generator": 1.6, "dynamo": 1.3, "bett": 0.7, "tisch_n": 1.05, "tisch_s": 1.05, "herd": 1.0, "anrichte": 0.95,
          "sessel_s": 0.95, "sessel_n": 0.95, "kohle": 1.1, "sortierfaecher": 1.0, "admintisch": 0.85, "bar": 1.0, "treppe_auf": 1.15, "treppe_ab": 0.95,
          "kessel": 2.8, "lochzange": 1.1,
          # Sabotage-Stationen (Runaway Train, Smoke in the Cars)
          "dampfbremse": 1.15, "handbremse": 0.95, "dachluke_zu": 0.3, "dachluke_auf": 0.75}
PROP_PAD = {"kessel": 0.9, "treppe_auf": 0.35, "generator": 0.4}
NO_SHADOW = {"treppe_ab", "lochzange", "dachluke_zu", "dachluke_auf"}


def classify(shape, ctx):
    """Objektart eines OPAQUE/GLASS-Rechtecks aus seiner Lage."""
    x0, y0, x1, y1 = shape[1:5]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    room = None
    for r in ctx["rooms"]:
        if ctx["room_geom"][r["key"]].buffer(0.05).contains(A.Point(cx, cy)):
            room = r["key"]
    ay0, ay1 = ctx["decks"]["A"]
    uy0, uy1 = ctx["decks"]["B"]
    # Lochzangen haben seit 20.10. ein GLASS-Rechteck (vorher frei begehbar)
    for tx, ty in ctx["ticket"]["stations"]:
        if x0 <= tx <= x1 and y0 <= ty <= y1:
            return "lochzange"
    if room == "generator":
        return "generator"
    if room == "dynamo":
        return "dynamo"
    if room == "sleeper":
        return "bett"
    if room == "dining":
        if y1 > ay1 - 0.05:
            return "tisch_n"
        return "bar" if x0 > -4.05 else "tisch_s"
    if room == "kitchen":
        return "herd" if y1 > uy1 - 0.05 else "anrichte"
    if room == "dome":
        return "sessel_n" if y1 > uy1 - 0.05 else "sessel_s"
    if room == "tender":
        return "kohle"
    if room == "mail":
        return "admintisch" if y1 > ay1 - 0.05 else "sortierfaecher"
    return "kiste"


def all_props(ctx):
    """Liste (kind, shape) aller Objekte: OPAQUE, GLASS, Treppen, Kessel, Lochzangen."""
    items = []
    for sh in ctx["opaque"] + ctx["glass"]:
        kind = classify(sh, ctx)
        if kind == "lochzange":
            # Kollision reicht ggf. bis an die Wand; das Objekt bleibt 0,44 x 0,32 um die Station
            x0, y0, x1, y1 = sh[1:5]
            tx, ty = next((t for t in ctx["ticket"]["stations"] if x0 <= t[0] <= x1 and y0 <= t[1] <= y1))
            sh = ("rect", tx - 0.22, ty - 0.16, tx + 0.22, ty + 0.16)
        items.append((kind, sh))
    for st in ctx["stairs"]:
        items.append(("treppe_auf", ("rect",) + tuple(st["main"])))
        items.append(("treppe_ab", ("rect",) + tuple(st["upper"])))
    items.append(("kessel", ("rect",) + tuple(ctx["boiler"])))
    # Runaway Train: Dampfbremse im Fuehrerstand, Handbremse auf der Plattform (Standlinie an der Station, 0,8 x 0,6 m)
    rw = ctx.get("runaway")
    if rw:
        bx, by = rw["brake"]
        items.append(("dampfbremse", ("rect", bx - 0.4, by, bx + 0.4, by + 0.6)))
        hx, hy = rw["handbrake"]
        items.append(("handbremse", ("rect", hx - 0.4, hy, hx + 0.4, hy + 0.6)))
    # Smoke in the Cars: drei Dachluken, je geschlossen und offen am selben Ort (0,9 x 0,7 m)
    sm = ctx.get("smoke")
    if sm:
        for hx, hy in sm["hatches"]:
            for kind in ("dachluke_zu", "dachluke_auf"):
                items.append((kind, ("rect", hx - 0.45, hy - 0.35, hx + 0.45, hy + 0.35)))
    return items


# ------------------------------------------------------------------ Bausteine

def bench(p, x0, y0, x1, y1, back_side, col=VELVET):
    """Sitzbank mit Rueckenlehne an der Seite back_side ('w' oder 'e'), Samt mit Messingknoepfen."""
    c = p.c
    p.box(x0, y0, x1, y1, 0, 0.42, shade(col, 1.05), shade(col, 0.8), w=0.035)
    if back_side == "w":
        p.box(x0, y0, x0 + 0.1, y1, 0.42, 0.55, shade(col, 1.15), col, w=0.035)
        bx = x0 + 0.05
    else:
        p.box(x1 - 0.1, y0, x1, y1, 0.42, 0.55, shade(col, 1.15), col, w=0.035)
        bx = x1 - 0.05
    zt = y0 + 0.42 * K
    c.line([(x0 + 0.03, zt + 0.02), (x1 - 0.03, zt + 0.02)], fill=alpha(shade(col, 1.3), 180), width=0.018)
    for k in range(3):
        c.ellipse(bx, y0 + 0.55 * K + 0.15 + k * 0.22, 0.012, 0.012, fill=BRASS)


def table_cloth(p, x0, y0, x1, y1, h=0.75, lamp=True):
    c = p.c
    p.box(x0 + 0.03, y0 + 0.08, x1 - 0.03, y1 - 0.04, 0, h - 0.05, OAK, OAK_D, w=0.03)
    top = y0 + h * K
    c.poly([(x0, top - 0.14), (x1, top - 0.14), (x1, top), (x0, top)], fill=WHITE, outline=OUTLINE, width=0.025)
    c.poly([(x0, top), (x1, top), (x1, y1 - 0.04 + h * K), (x0, y1 - 0.04 + h * K)], fill=WHITE, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.03, top - 0.12), (x1 - 0.03, top - 0.12)], fill=(210, 206, 196, 255), width=0.012)
    c.line([(x0 + 0.03, top - 0.06), (x1 - 0.03, top - 0.06)], fill=(220, 216, 206, 255), width=0.01)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + h * K
    c.ellipse(cx - 0.12, cy - 0.03, 0.07, 0.045, fill=(246, 246, 242, 255), outline=OUTLINE, width=0.015)      # Teller
    c.ellipse(cx - 0.12, cy - 0.03, 0.04, 0.025, fill=(230, 228, 220, 255))
    c.rect(cx + 0.02, cy - 0.08, cx + 0.06, cy + 0.03, fill=(170, 60, 60, 255), outline=OUTLINE, width=0.01)    # Glas
    if lamp:
        lx, ly = cx + 0.14, cy + 0.07
        c.glow(lx, ly + 0.1, 0.35, WARM, 0.5)
        c.line([(lx, ly), (lx, ly + 0.12)], fill=OUTLINE, width=0.03)
        c.line([(lx, ly), (lx, ly + 0.12)], fill=BRASS, width=0.014)
        c.ellipse(lx, ly, 0.03, 0.02, fill=BRASS, outline=OUTLINE, width=0.01)
        c.poly([(lx - 0.07, ly + 0.11), (lx + 0.07, ly + 0.11), (lx + 0.05, ly + 0.2), (lx - 0.05, ly + 0.2)],
               fill=RED_LAMP, outline=OUTLINE, width=0.015)
        c.ellipse(lx, ly + 0.14, 0.02, 0.025, fill=(255, 200, 190, 255))


def steam_puff(c, x, y, r, a=150):
    pts = HD.wobble_ellipse(x, y, r, r * 0.8, amp=r * 0.12, seed=int(x * 50 + y * 7) & 0xfff)
    c.poly(pts, fill=alpha((236, 240, 248, 255), a), outline=alpha((150, 160, 180, 255), a), width=0.02)
    c.ellipse(x - r * 0.3, y + r * 0.25, r * 0.35, r * 0.25, fill=alpha(WHITE, min(255, a + 40)))


# ------------------------------------------------------------------ Objekte

def draw(kind, shape, idx, ppm, ctx=None):
    x0, y0, x1, y1 = A.shape_bounds(shape)
    h = PROP_H.get(kind, 1.0)
    pad = PROP_PAD.get(kind, 0.3)
    extra = 1.3 if kind == "kessel" else 0.0
    p = TProp(x0, y0, x1 + extra, y1, h, ppm, pad=pad)
    c = p.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rnd = random.Random(idx * 131 + 7)
    if kind not in NO_SHADOW:
        c.soft_shadow([(x0 + 0.08, y0 - 0.12), (x1 + 0.12, y0 - 0.12), (x1 + 0.12, y1), (x0 + 0.08, y1)], 100, 0.09)

    if kind == "generator":
        # Maschinensatz: gruener Zylinder (Dampfmaschine) mit Schwungrad, Regler, Rohren; roter Dynamo am Ostende
        p.box(x0, y0, x1, y1, 0, 0.3, IRON_L, IRON, w=0.035)
        S.rivets(c, [(x0 + 0.1 + k * 0.2, y0 + 0.08) for k in range(int((x1 - x0) / 0.2))], 0.014)
        green = (74, 124, 92, 255)
        ex = x0 + 1.15
        p.cyl(x0 + 0.1 + 0.55, cy - 0.1, 0.42, 0.3, 0.9, shade(green, 1.15), green, ry=0.26)       # Zylinder liegend (Deckel)
        c.poly([(x0 + 0.1, cy - 0.1 + 0.3 * K), (ex, cy - 0.1 + 0.3 * K), (ex, cy - 0.1 + 1.2 * K + 0.26), (x0 + 0.1, cy - 0.1 + 1.2 * K + 0.26)],
               fill=green, outline=OUTLINE, width=0.035)
        c.line([(x0 + 0.14, cy - 0.1 + 1.2 * K + 0.2), (ex - 0.04, cy - 0.1 + 1.2 * K + 0.2)], fill=shade(green, 1.35), width=0.03)
        for k in range(3):                                              # Messingbaender
            bx = x0 + 0.3 + k * 0.32
            c.rect(bx - 0.02, cy - 0.1 + 0.3 * K, bx + 0.02, cy - 0.1 + 1.2 * K + 0.26, fill=BRASS, outline=OUTLINE, width=0.012)
        fx = x0 + 0.42                                                   # Schwungrad vorn (stehend, in Fahrtrichtung)
        c.ellipse(fx, y0 + 0.6 * K + 0.25, 0.3, 0.3, fill=IRON, outline=OUTLINE, width=0.04)
        c.ellipse(fx, y0 + 0.6 * K + 0.25, 0.22, 0.22, fill=STEEL_D, outline=OUTLINE, width=0.02)
        for k in range(6):
            a = math.radians(k * 60 + 15)
            c.line([(fx, y0 + 0.6 * K + 0.25), (fx + 0.22 * math.cos(a), y0 + 0.6 * K + 0.25 + 0.22 * math.sin(a))], fill=IRON, width=0.03)
        c.ellipse(fx, y0 + 0.6 * K + 0.25, 0.05, 0.05, fill=BRASS, outline=OUTLINE, width=0.015)
        gx = x0 + 0.95                                                   # Fliehkraftregler
        c.line([(gx, cy + 1.2 * K + 0.1), (gx, cy + 1.55 * K + 0.3)], fill=OUTLINE, width=0.04)
        c.line([(gx, cy + 1.2 * K + 0.1), (gx, cy + 1.55 * K + 0.3)], fill=BRASS, width=0.02)
        for sx in (-1, 1):
            c.line([(gx, cy + 1.5 * K + 0.3), (gx + sx * 0.1, cy + 1.3 * K + 0.22)], fill=BRASS, width=0.015)
            c.ellipse(gx + sx * 0.1, cy + 1.3 * K + 0.2, 0.035, 0.035, fill=BRASS, outline=OUTLINE, width=0.012)
        red = (176, 56, 48, 255)                                         # Dynamo
        p.cyl(x1 - 0.3, cy - 0.05, 0.26, 0.3, 0.65, shade(red, 1.1), red, ry=0.18)
        c.rect(x1 - 0.5, cy - 0.05 + 0.6 * K, x1 - 0.1, cy - 0.05 + 0.75 * K, fill=(200, 120, 60, 255), outline=OUTLINE, width=0.015)
        S.pipe(c, [(ex, cy + 0.9 * K + 0.1), (x1 - 0.3, cy + 0.9 * K + 0.1)], 0.035, BRASS_D, flange=True)
        S.gauge(c, x0 + 0.95, y0 + 0.9 * K + 0.08, 0.08, 50)
        S.gauge(c, x1 - 0.3, y0 + 1.0 * K + 0.12, 0.07, 30, red_zone=False)
        for k in range(3):
            steam_puff(c, x0 + 0.95 + k * 0.08, cy + 1.6 * K + 0.42 + k * 0.1, 0.07 + k * 0.02, 110 - k * 25)

    elif kind == "dynamo":
        # Dynamo: Sockel, Gehaeuse mit Kupferwicklung, Kollektor und Riemenscheibe, Messingschild
        p.box(x0, y0, x1, y1, 0, 0.22, IRON_L, IRON, w=0.035)
        body = (64, 70, 84, 255)
        p.cyl(cx, cy, 0.45, 0.22, 0.75, shade(body, 1.15), body, ry=0.3)
        c.rect(cx - 0.45, cy + 0.5 * K, cx + 0.45, cy + 0.72 * K, fill=(196, 120, 66, 255), outline=OUTLINE, width=0.02)
        for k in range(12):
            xx = cx - 0.42 + k * 0.077
            c.line([(xx, cy + 0.5 * K + 0.01), (xx, cy + 0.72 * K - 0.01)], fill=(150, 86, 46, 255), width=0.012)
        c.rect(cx - 0.45, cy + 0.6 * K - 0.02, cx + 0.45, cy + 0.6 * K + 0.02, fill=BRASS, outline=OUTLINE, width=0.01)
        c.ellipse(cx, cy + 0.97 * K, 0.42, 0.28, fill=shade(body, 1.1), outline=OUTLINE, width=0.035)
        c.ellipse(cx, cy + 0.97 * K, 0.16, 0.1, fill=BRASS, outline=OUTLINE, width=0.02)
        c.ellipse(cx, cy + 0.97 * K, 0.05, 0.035, fill=INK)
        c.ellipse(cx + 0.5, cy + 0.6 * K, 0.07, 0.14, fill=IRON, outline=OUTLINE, width=0.025)          # Riemenscheibe
        c.ellipse(cx + 0.5, cy + 0.6 * K, 0.03, 0.07, fill=STEEL_L)
        c.poly([(cx + 0.5, cy + 0.6 * K - 0.14), (cx + 0.5, cy + 0.6 * K + 0.14), (cx + 0.45, y1 + 1.3 * K), (cx + 0.3, y1 + 1.3 * K)],
               fill=alpha((40, 30, 30, 255), 200))
        S.plate(c, cx - 0.1, y0 + 0.12, 0.5, 0.09, "DYNAMO No 2", size=0.05)
        for k in range(3):
            c.glow(cx - 0.2 + k * 0.2, cy + 0.6 * K, 0.08, (120, 200, 255, 255), 0.5)
        c.ellipse(cx + 0.33, cy + 0.98 * K + 0.1, 0.02, 0.02, fill=RED_LAMP, outline=OUTLINE, width=0.008)

    elif kind == "bett":
        # Bett im Abteil: Holzrahmen, Matratze mit weissem Laken, rote Decke, Kissen am Westende
        p.box(x0, y0, x1, y1, 0, 0.35, OAK, OAK_D, w=0.03)
        zt = y0 + 0.35 * K
        c.poly([(x0 + 0.03, zt), (x1 - 0.03, zt), (x1 - 0.03, y1 - 0.02 + 0.35 * K + 0.08 * K), (x0 + 0.03, y1 - 0.02 + 0.35 * K + 0.08 * K)],
               fill=WHITE, outline=OUTLINE, width=0.025)
        bx0 = x0 + 0.5
        c.poly([(bx0, zt + 0.015), (x1 - 0.05, zt + 0.015), (x1 - 0.05, y1 + 0.42 * K - 0.04), (bx0 - 0.08, y1 + 0.42 * K - 0.04)],
               fill=VELVET, outline=OUTLINE, width=0.02)
        c.line([(bx0 + 0.03, zt + 0.06), (x1 - 0.08, zt + 0.06)], fill=VELVET_L, width=0.02)
        c.poly([(bx0 - 0.02, zt + 0.015), (bx0 + 0.12, zt + 0.015), (bx0 + 0.08, y1 + 0.42 * K - 0.04), (bx0 - 0.1, y1 + 0.42 * K - 0.04)],
               fill=(236, 232, 224, 255), outline=OUTLINE, width=0.015)
        c.ellipse(x0 + 0.26, y1 - 0.3 + 0.42 * K + 0.05, 0.19, 0.11, fill=(250, 250, 246, 255), outline=OUTLINE, width=0.02)
        c.ellipse(x0 + 0.24, y1 - 0.3 + 0.42 * K + 0.07, 0.1, 0.05, fill=(236, 236, 230, 255))
        c.rect(x0 + 0.03, zt - 0.02, x1 - 0.03, zt + 0.03, fill=OAK_D)
        c.ellipse(x1 - 0.12, y0 + 0.06, 0.03, 0.02, fill=BRASS, outline=OUTLINE, width=0.01)

    elif kind in ("tisch_n", "tisch_s"):
        # Speisewagen-Sitznische: zwei Samtbaenke, Tisch mit weisser Decke, Teller, Glas, rote Tischlampe
        bench(p, x0, y0 + 0.02, x0 + 0.3, y1 - 0.02, "w")
        bench(p, x1 - 0.3, y0 + 0.02, x1, y1 - 0.02, "e")
        # Suedwand-Nischen ohne Tischlampe: niedriger, verdecken Spieler dahinter weniger (Bericht Grafik-Agent)
        table_cloth(p, x0 + 0.32, y0, x1 - 0.32, y1, lamp=kind == "tisch_n")

    elif kind == "herd":
        # Herdzeile: Edelstahlfront mit Ofentueren, Kochfeld mit Ringen, Toepfe mit Dampf, Messingreling
        p.box(x0, y0, x1, y1, 0, 0.9, STEEL_L, STEEL, w=0.035)
        n = int((x1 - x0) / 0.9)
        for k in range(n):
            a = x0 + 0.08 + k * (x1 - x0 - 0.16) / n
            b = a + (x1 - x0 - 0.16) / n - 0.08
            c.rect(a, y0 + 0.08, b, y0 + 0.9 * K - 0.1, fill=STEEL_D, outline=OUTLINE, width=0.015)
            c.rect(a + 0.05, y0 + 0.3, b - 0.05, y0 + 0.38, fill=(50, 54, 64, 255), outline=OUTLINE, width=0.01)
            c.glow((a + b) / 2, y0 + 0.2, 0.25, (255, 150, 60, 255), 0.35)
            c.rect((a + b) / 2 - 0.12, y0 + 0.9 * K - 0.08, (a + b) / 2 + 0.12, y0 + 0.9 * K - 0.04, fill=BRASS, outline=OUTLINE, width=0.01)
            for kx in range(3):
                c.ellipse(a + 0.1 + kx * 0.08, y0 + 0.9 * K - 0.14, 0.018, 0.018, fill=INK)
        zt = y0 + 0.9 * K
        c.line([(x0, zt + 0.02), (x1, zt + 0.02)], fill=BRASS, width=0.03)
        c.line([(x0, zt + 0.02), (x1, zt + 0.02)], fill=OUTLINE, width=0.008)
        top_y = y1 + 0.9 * K
        rings = [(x0 + 0.45 + k * 0.75, (zt + top_y) / 2 + (0.1 if k % 2 else -0.08)) for k in range(int((x1 - x0) / 0.75))]
        for rx, ry in rings:
            c.ellipse(rx, ry, 0.17, 0.11, fill=(40, 40, 48, 255), outline=OUTLINE, width=0.015)
            c.ellipse(rx, ry, 0.11, 0.07, fill=(60, 60, 70, 255), outline=(30, 30, 36, 255), width=0.01)
        for k, (rx, ry) in enumerate(rings):
            if k % 3 == 1:
                c.glow(rx, ry, 0.15, (255, 120, 60, 255), 0.5)
                continue
            col = rnd.choice([(188, 100, 60, 255), (150, 160, 170, 255), (60, 70, 80, 255)])
            p.cyl(rx, ry - 0.02, 0.16, 0.0, 0.18, shade(col, 1.1), col, ry=0.1, w=0.02)
            c.ellipse(rx, ry - 0.02 + 0.18 * K, 0.12, 0.07, fill=(90, 70, 50, 255))
            c.line([(rx + 0.16, ry + 0.02), (rx + 0.28, ry + 0.04)], fill=OUTLINE, width=0.03)
            for j in range(2):
                steam_puff(c, rx + 0.04 + j * 0.08, ry + 0.22 + j * 0.12, 0.06 + j * 0.02, 120 - j * 40)

    elif kind == "anrichte":
        # Anrichte: Holzkorpus mit Schubladen, Arbeitsplatte mit Brett, Messer, Brot, Tellerstapel
        p.box(x0, y0, x1, y1, 0, 0.9, OAK, OAK_D, w=0.035)
        for k in range(3):
            a = x0 + 0.08 + k * (x1 - x0 - 0.16) / 3
            b = a + (x1 - x0 - 0.16) / 3 - 0.06
            c.rect(a, y0 + 0.08, b, y0 + 0.9 * K - 0.08, outline=shade(OAK_D, 0.8), width=0.015)
            c.rect((a + b) / 2 - 0.06, y0 + 0.9 * K - 0.22, (a + b) / 2 + 0.06, y0 + 0.9 * K - 0.18, fill=BRASS, outline=OUTLINE, width=0.01)
        zt = y0 + 0.9 * K
        c.rect(x0 + 0.15, zt + 0.06, x0 + 0.6, zt + 0.32, fill=(214, 176, 120, 255), outline=OUTLINE, width=0.02)
        c.line([(x0 + 0.2, zt + 0.12), (x0 + 0.52, zt + 0.26)], fill=STEEL_L, width=0.025)
        c.line([(x0 + 0.5, zt + 0.25), (x0 + 0.58, zt + 0.29)], fill=WOOD_D, width=0.035)
        c.ellipse(x0 + 0.95, zt + 0.2, 0.17, 0.1, fill=(206, 150, 80, 255), outline=OUTLINE, width=0.02)
        c.line([(x0 + 0.85, zt + 0.2), (x0 + 1.05, zt + 0.2)], fill=(160, 110, 60, 255), width=0.02)
        for k in range(4):
            c.ellipse(x1 - 0.4, zt + 0.12 + k * 0.03, 0.14, 0.08, fill=(246, 246, 242, 255), outline=OUTLINE, width=0.015)
        c.rect(x1 - 0.2, zt + 0.08, x1 - 0.1, zt + 0.3, fill=(120, 160, 80, 255), outline=OUTLINE, width=0.012)

    elif kind in ("sessel_s", "sessel_n"):
        # Clubsessel aus gruenem Leder: Rueckenlehne (Sueden beim Fenstersessel), Armlehnen, Sitzkissen, Messingnaegel
        back_s = kind == "sessel_s"
        col = LEATHER
        if back_s:
            p.box(x0 + 0.08, y0, x1 - 0.08, y0 + 0.25, 0, 0.95, shade(col, 1.15), shade(col, 0.9), w=0.035)
            seat_y0, seat_y1 = y0 + 0.25, y1 - 0.05
        else:
            seat_y0, seat_y1 = y0 + 0.05, y1 - 0.25
        for ax0, ax1 in ((x0, x0 + 0.16), (x1 - 0.16, x1)):
            p.box(ax0, seat_y0 - 0.02, ax1, seat_y1, 0, 0.6, shade(col, 1.2), col, w=0.03)
        p.box(x0 + 0.16, seat_y0, x1 - 0.16, seat_y1, 0, 0.42, shade(col, 1.08), shade(col, 0.85), w=0.03)
        if not back_s:
            p.box(x0 + 0.08, y1 - 0.25, x1 - 0.08, y1, 0, 0.95, shade(col, 1.15), shade(col, 0.9), w=0.035)
            c.rect(x0 + 0.2, y1 - 0.25 + 0.3 * K, x1 - 0.2, y1 - 0.25 + 0.85 * K, outline=alpha(shade(col, 1.35), 160), width=0.015)
            for k in range(4):
                c.ellipse(x0 + 0.26 + k * (x1 - x0 - 0.52) / 3, y1 - 0.25 + 0.88 * K, 0.012, 0.012, fill=BRASS)
        else:
            for k in range(4):
                c.ellipse(x0 + 0.26 + k * (x1 - x0 - 0.52) / 3, y0 + 0.88 * K, 0.012, 0.012, fill=BRASS)
            c.line([(x0 + 0.14, y0 + 0.5 * K), (x1 - 0.14, y0 + 0.5 * K)], fill=alpha(shade(col, 0.7), 200), width=0.015)
        cxs, cys = (x0 + x1) / 2, seat_y0 + 0.42 * K + 0.1
        c.ellipse(cxs, cys + 0.12, 0.16, 0.09, fill=alpha(shade(col, 1.25), 120))

    elif kind == "kohle":
        # Kohlenhaufen im Bunker: Huegel aus Brocken, oben Glanzlichter
        hill = HD.wobble([(x0, y0), (x1, y0), (x1 - 0.05, y1 + 0.5 * K), (cx + 0.3, y1 + 1.05 * K), (cx - 0.25, y1 + 1.1 * K), (x0 + 0.05, y1 + 0.45 * K)],
                         amp=0.03, seed=5, step=0.12, closed=True)
        c.poly(hill, fill=COAL, outline=OUTLINE, width=0.04)
        hp = A.Polygon(hill)
        for _ in range(90):
            lx, ly = rnd.uniform(x0, x1), rnd.uniform(y0, y1 + 1.1 * K)
            if not hp.contains(A.Point(lx, ly)):
                continue
            r = rnd.uniform(0.04, 0.1)
            pts = [(lx + r * math.cos(a) * rnd.uniform(0.75, 1.2), ly + r * math.sin(a) * rnd.uniform(0.75, 1.2)) for a in [k * math.tau / 6 for k in range(6)]]
            c.poly(pts, fill=rnd.choice([COAL, COAL_L, (30, 28, 32, 255)]), outline=OUTLINE, width=0.012)
            c.line([pts[3], pts[4]], fill=(130, 130, 142, 255), width=0.012)
        c.line([(x0 + 0.3, y0 + 0.1), (cx - 0.1, y1 + 0.3), (x1 - 0.2, y1 + 0.5)], fill=alpha(OUTLINE, 0), width=0.01)

    elif kind == "sortierfaecher":
        # Sortierfaecher an der Suedwand: Holzschrank mit Faechern voller Briefe und Pakete (seit 20.10. 0,95 statt
        # 1,3 hoch, verdeckte Spieler im Postraum zu stark)
        hb = h - 0.05
        p.box(x0, y0, x1, y1, 0, hb, shade(WOOD_D, 1.1), WOOD_D, w=0.035)
        rows, cols = 3, int((x1 - x0) / 0.36)
        fh = (hb * K - 0.14) / rows
        for r in range(rows):
            for col_ in range(cols):
                a = x0 + 0.06 + col_ * (x1 - x0 - 0.12) / cols
                b = a + (x1 - x0 - 0.12) / cols - 0.04
                ya = y0 + 0.07 + r * fh
                c.rect(a, ya, b, ya + fh - 0.035, fill=(54, 34, 22, 255), outline=OUTLINE, width=0.012)
                v = rnd.random()
                if v < 0.55:
                    for k in range(3):
                        c.rect(a + 0.03 + k * 0.012, ya + 0.02 + k * 0.025, b - 0.04, ya + 0.045 + k * 0.025, fill=PAPER, outline=INK, width=0.006)
                elif v < 0.8:
                    c.rect(a + 0.04, ya + 0.02, b - 0.05, ya + fh - 0.07, fill=(170, 134, 90, 255), outline=OUTLINE, width=0.01)
                    c.line([(a + 0.04, ya + fh / 2 - 0.02), (b - 0.05, ya + fh / 2 - 0.02)], fill=(110, 80, 50, 255), width=0.008)
        zt = y0 + hb * K
        c.rect(x0 + 0.1, zt + 0.04, x0 + 0.55, zt + 0.22, fill=(170, 134, 90, 255), outline=OUTLINE, width=0.015)
        c.ellipse(x1 - 0.4, zt + 0.14, 0.2, 0.1, fill=(188, 164, 118, 255), outline=OUTLINE, width=0.015)
        S.plate(c, cx, y0 + hb * K - 0.06, 0.6, 0.09, "SORTING", size=0.05)

    elif kind == "admintisch":
        # Sortiertisch an der Nordwand des Postraums (Admin-Karte): Eichenpult mit Schubladen und Messinggriffen,
        # darauf die aufgespannte Streckenkarte "POLARIS LINE" unter Glas, Briefwaage, Stempel mit Kissen,
        # Tintenfass, Briefstapel und eine Messinglampe mit gruenem Schirm
        ht = h - 0.07
        p.box(x0, y0, x1, y1, 0, ht, OAK, OAK_D, w=0.035)
        fb, ft = y0, y0 + ht * K
        nd = 4
        for k in range(nd):
            a_ = x0 + 0.07 + k * (x1 - x0 - 0.14) / nd
            b_ = a_ + (x1 - x0 - 0.14) / nd - 0.05
            c.rect(a_, fb + 0.06, b_, ft - 0.07, fill=shade(OAK_D, 1.08), outline=OUTLINE, width=0.014)
            c.line([(a_ + 0.012, ft - 0.085), (b_ - 0.012, ft - 0.085)], fill=shade(OAK, 1.3), width=0.01)
            c.rect((a_ + b_) / 2 - 0.045, (fb + ft) / 2 - 0.012, (a_ + b_) / 2 + 0.045, (fb + ft) / 2 + 0.012, fill=BRASS, outline=OUTLINE, width=0.008)
        c.line([(x0 + 0.02, ft - 0.025), (x1 - 0.02, ft - 0.025)], fill=shade(OAK, 1.35), width=0.015)
        tb = y1 + ht * K
        mx0, mx1, my0, my1 = x0 + 0.1, x1 - 0.5, ft + 0.04, tb - 0.04
        c.rect(mx0 - 0.02, my0 - 0.02, mx1 + 0.02, my1 + 0.02, fill=WOOD_X, outline=OUTLINE, width=0.014)
        c.rect(mx0, my0, mx1, my1, fill=PAPER)
        for k in range(1, 4):
            c.line([(mx0, my0 + (my1 - my0) * k / 4), (mx1, my0 + (my1 - my0) * k / 4)], fill=(206, 190, 146, 255), width=0.005)
        for k in range(1, 8):
            c.line([(mx0 + (mx1 - mx0) * k / 8, my0), (mx0 + (mx1 - mx0) * k / 8, my1)], fill=(206, 190, 146, 255), width=0.005)
        for k in range(3):                                                  # Fluss, Wald, Berge als Kartenzeichen
            c.ellipse(mx0 + 0.12 + k * 0.09, my0 + 0.05 + 0.02 * (k % 2), 0.025, 0.02, fill=(150, 180, 140, 255))
        c.line([(mx0 + 0.05, my1 - 0.03), (mx0 + 0.3, my1 - 0.08), (mx0 + 0.5, my1 - 0.03)], fill=(140, 180, 220, 255), width=0.012)
        pts = [(mx0 + 0.06, my0 + 0.05), (mx0 + 0.25, my0 + 0.12), (mx0 + 0.45, my0 + 0.08), (mx0 + 0.65, my0 + 0.17), (mx1 - 0.3, my0 + 0.12), (mx1 - 0.06, my1 - 0.1)]
        c.line(pts, fill=(160, 40, 44, 255), width=0.016)
        for q in pts:
            c.ellipse(q[0], q[1], 0.016, 0.012, fill=WHITE, outline=INK, width=0.007)
        c.ellipse(pts[3][0], pts[3][1], 0.02, 0.016, fill=RED_LAMP, outline=INK, width=0.007)
        c.textf((mx0 + mx1) / 2, my1 - 0.055, "POLARIS LINE", 0.035, INK, kind="serif")
        c.line([(mx0 + 0.02, my1 - 0.02), (mx0 + 0.35, my0 + 0.1)], fill=alpha(WHITE, 70), width=0.02)      # Glas
        # Briefwaage, Stempel, Tintenfass, Briefe rechts
        wx = x1 - 0.36
        c.line([(wx, ft + 0.06), (wx, ft + 0.2)], fill=OUTLINE, width=0.03)
        c.line([(wx, ft + 0.06), (wx, ft + 0.2)], fill=BRASS, width=0.015)
        c.ellipse(wx, ft + 0.06, 0.05, 0.025, fill=BRASS_D, outline=OUTLINE, width=0.01)
        c.line([(wx - 0.07, ft + 0.17), (wx + 0.07, ft + 0.2)], fill=OUTLINE, width=0.02)
        c.ellipse(wx - 0.07, ft + 0.15, 0.035, 0.015, fill=BRASS, outline=OUTLINE, width=0.008)
        c.ellipse(wx + 0.07, ft + 0.18, 0.035, 0.015, fill=BRASS, outline=OUTLINE, width=0.008)
        c.rect(x1 - 0.22, ft + 0.05, x1 - 0.1, ft + 0.1, fill=(60, 40, 90, 255), outline=OUTLINE, width=0.01)
        c.rect(x1 - 0.18, ft + 0.1, x1 - 0.14, ft + 0.19, fill=BRASS, outline=OUTLINE, width=0.008)
        c.ellipse(x1 - 0.16, ft + 0.2, 0.025, 0.018, fill=WOOD_D, outline=OUTLINE, width=0.01)
        c.ellipse(x1 - 0.08, ft + 0.08, 0.025, 0.018, fill=(40, 40, 60, 255), outline=OUTLINE, width=0.01)
        for k in range(4):
            c.rect(x1 - 0.45 + k * 0.008, ft + 0.24 + k * 0.014, x1 - 0.22 + k * 0.008, ft + 0.32 + k * 0.014, fill=PAPER, outline=INK, width=0.006)
        lx, ly = x1 - 0.14, tb - 0.1
        c.glow(lx, ly + 0.08, 0.45, WARM, 0.5)
        c.line([(lx, ly - 0.06), (lx, ly + 0.12)], fill=OUTLINE, width=0.035)
        c.line([(lx, ly - 0.06), (lx, ly + 0.12)], fill=BRASS, width=0.016)
        c.ellipse(lx, ly - 0.06, 0.04, 0.022, fill=BRASS, outline=OUTLINE, width=0.01)
        c.poly([(lx - 0.11, ly + 0.1), (lx + 0.11, ly + 0.1), (lx + 0.07, ly + 0.2), (lx - 0.07, ly + 0.2)],
               fill=(46, 112, 70, 255), outline=OUTLINE, width=0.015)
        c.line([(lx - 0.09, ly + 0.12), (lx + 0.09, ly + 0.12)], fill=(90, 160, 110, 255), width=0.012)
        c.ellipse(lx, ly + 0.09, 0.05, 0.02, fill=(255, 240, 200, 255))

    elif kind == "bar":
        # Bar am Ostende der Suedwand im Speisewagen: Mahagoni-Tresen mit Fuellungen, Messing-Fussreling, Marmorplatte;
        # darauf Flaschen, Glaeser, Shaker, Kasse und eine kleine Tischlampe
        ht = h
        p.box(x0, y0, x1, y1, 0, ht, (222, 214, 200, 255), WOOD, w=0.035)
        fb, ft = y0, y0 + ht * K
        n = 3
        for k in range(n):
            a_ = x0 + 0.06 + k * (x1 - x0 - 0.12) / n
            b_ = a_ + (x1 - x0 - 0.12) / n - 0.04
            c.rect(a_, fb + 0.12, b_, ft - 0.07, fill=shade(WOOD, 0.86), outline=OUTLINE, width=0.014)
            c.rect(a_ + 0.03, fb + 0.15, b_ - 0.03, ft - 0.1, fill=shade(WOOD, 1.08), outline=alpha(OUTLINE, 140), width=0.008)
            c.line([(a_ + 0.035, ft - 0.11), (b_ - 0.035, ft - 0.11)], fill=shade(WOOD, 1.3), width=0.008)
        c.line([(x0 + 0.03, fb + 0.07), (x1 - 0.03, fb + 0.07)], fill=OUTLINE, width=0.045)
        c.line([(x0 + 0.03, fb + 0.07), (x1 - 0.03, fb + 0.07)], fill=BRASS, width=0.024)
        for k in range(3):
            c.ellipse(x0 + 0.15 + k * (x1 - x0 - 0.3) / 2, fb + 0.07, 0.025, 0.02, fill=BRASS_D, outline=OUTLINE, width=0.008)
        c.rect(x0 - 0.02, ft - 0.05, x1 + 0.02, ft, fill=(222, 214, 200, 255), outline=OUTLINE, width=0.02)
        c.line([(x0, ft - 0.025), (x1, ft - 0.025)], fill=(200, 190, 176, 255), width=0.01)
        tb = y1 + ht * K
        c.line([(x0 + 0.1, ft + 0.08), (x0 + 0.45, tb - 0.05)], fill=(206, 196, 184, 255), width=0.012)   # Marmorader
        c.line([(x1 - 0.5, ft + 0.05), (x1 - 0.2, tb - 0.1)], fill=(206, 196, 184, 255), width=0.01)
        cols = [(70, 120, 60, 240), (150, 90, 40, 240), (120, 30, 40, 240), (60, 90, 130, 240)]
        bx = x0 + 0.08
        for k, col in enumerate(cols):
            by = ft + 0.1 + (k % 2) * 0.05
            c.rect(bx, by, bx + 0.065, by + 0.17, fill=col, outline=OUTLINE, width=0.012)
            c.rect(bx + 0.022, by + 0.17, bx + 0.043, by + 0.24, fill=shade(col, 0.8), outline=OUTLINE, width=0.01)
            c.rect(bx + 0.012, by + 0.05, bx + 0.053, by + 0.11, fill=CREAM, outline=INK, width=0.005)
            c.line([(bx + 0.012, by + 0.03), (bx + 0.012, by + 0.15)], fill=alpha(WHITE, 130), width=0.009)
            bx += 0.085
        for k in range(3):                                                  # Glaeser
            gx = x0 + 0.5 + k * 0.08
            c.poly([(gx - 0.025, ft + 0.08), (gx + 0.025, ft + 0.08), (gx + 0.035, ft + 0.17), (gx - 0.035, ft + 0.17)],
                   fill=alpha(GLASS, 170), outline=OUTLINE, width=0.01)
            c.line([(gx - 0.02, ft + 0.1), (gx - 0.02, ft + 0.15)], fill=alpha(WHITE, 160), width=0.006)
        sx = x1 - 0.3                                                       # Shaker
        c.poly([(sx - 0.04, ft + 0.06), (sx + 0.04, ft + 0.06), (sx + 0.03, ft + 0.26), (sx - 0.03, ft + 0.26)], fill=STEEL_L, outline=OUTLINE, width=0.012)
        c.rect(sx - 0.03, ft + 0.2, sx + 0.03, ft + 0.22, fill=STEEL_D)
        c.ellipse(sx, ft + 0.27, 0.02, 0.012, fill=STEEL_L, outline=OUTLINE, width=0.008)
        rx = x1 - 0.12                                                      # Registrierkasse
        p.box(rx - 0.1, y1 - 0.2, rx + 0.1, y1 - 0.04, ht, 0.22, BRASS_D, BRASS, w=0.015)
        for r_ in range(2):
            for c_ in range(3):
                c.ellipse(rx - 0.06 + c_ * 0.06, y1 - 0.2 + 0.04 + r_ * 0.05, 0.014, 0.012, fill=CREAM, outline=OUTLINE, width=0.006)
        c.rect(rx - 0.08, y1 - 0.04 + 0.22 * K, rx + 0.08, y1 - 0.04 + 0.22 * K + 0.05, fill=(40, 40, 50, 255), outline=OUTLINE, width=0.008)
        lx, ly = x0 + 0.78, tb - 0.08                                        # Tischlampe
        c.glow(lx, ly + 0.1, 0.35, WARM, 0.5)
        c.line([(lx, ly), (lx, ly + 0.12)], fill=OUTLINE, width=0.03)
        c.line([(lx, ly), (lx, ly + 0.12)], fill=BRASS, width=0.014)
        c.ellipse(lx, ly, 0.03, 0.018, fill=BRASS, outline=OUTLINE, width=0.01)
        c.poly([(lx - 0.07, ly + 0.11), (lx + 0.07, ly + 0.11), (lx + 0.05, ly + 0.2), (lx - 0.05, ly + 0.2)], fill=RED_LAMP, outline=OUTLINE, width=0.014)
        c.ellipse(lx, ly + 0.14, 0.02, 0.025, fill=(255, 200, 190, 255))
        S.plate(c, (x0 + x1) / 2, fb + ht * K * 0.5, 0.3, 0.07, "BAR", size=0.045)

    elif kind == "treppe_auf":
        # Treppe nach oben (Nordwand): Stufen steigen nach Norden, Wangen aus Holz, Messing-Handlaeufe, Schild UP
        n = 7
        rise = 0.15
        d = (y1 - y0) / n
        for k in range(n - 1, -1, -1):
            ya = y0 + k * d
            z = (k + 1) * rise
            p.box(x0 + 0.1, ya, x1 - 0.1, ya + d, 0, z, shade(OAK, 1.08 - 0.035 * k), shade(OAK_D, 0.9), w=0.03)
            c.line([(x0 + 0.12, ya + z * K + 0.012), (x1 - 0.12, ya + z * K + 0.012)], fill=BRASS, width=0.02)
        top = y1 + n * rise * K
        c.poly([(x0 + 0.1, top - d), (x1 - 0.1, top - d), (x1 - 0.1, top + 0.05), (x0 + 0.1, top + 0.05)], fill=OAK, outline=OUTLINE, width=0.03)
        for wx0, wx1 in ((x0, x0 + 0.1), (x1 - 0.1, x1)):                 # Wangen
            c.poly([(wx0, y0), (wx1, y0), (wx1, top + 0.08), (wx0, top + 0.08)], fill=WOOD_D, outline=OUTLINE, width=0.03)
            hx = (wx0 + wx1) / 2
            c.line([(hx, y0 + 0.45 * K + 0.05), (hx, top + 0.25)], fill=OUTLINE, width=0.06)
            c.line([(hx, y0 + 0.45 * K + 0.05), (hx, top + 0.25)], fill=BRASS, width=0.03)
            for k in range(4):
                c.ellipse(hx, y0 + 0.45 * K + 0.1 + k * (top + 0.1 - y0) / 4, 0.03, 0.03, fill=BRASS_D, outline=OUTLINE, width=0.012)
        c.glow(cx, top + 0.1, 0.5, WARM, 0.3)
        S.plate(c, cx, y0 + 0.06, 0.34, 0.1, "UP", size=0.07)

    elif kind == "treppe_ab":
        # Treppe nach unten (Oberdeck): Schacht mit Stufen, die nach Norden hinabfuehren, Gelaender rundum
        n = 7
        d = (y1 - y0) / n
        c.rect(x0, y0, x1, y1, fill=(22, 18, 18, 255))
        for k in range(n):
            ya = y0 + k * d
            t = k / (n - 1)
            col = shade(OAK, 0.95 - 0.6 * t)
            c.rect(x0 + 0.1, ya + 0.01, x1 - 0.1, ya + d - 0.015, fill=col, outline=shade(col, 0.5), width=0.012)
            c.line([(x0 + 0.12, ya + d - 0.03), (x1 - 0.12, ya + d - 0.03)], fill=alpha(BRASS, int(230 - 180 * t)), width=0.014)
        c.rect(x0, y0, x1, y1, outline=OUTLINE, width=0.04)
        for wx in (x0 + 0.04, x1 - 0.04):                                  # Gelaender Ost/West
            for k in range(4):
                yy = y0 + 0.1 + k * (y1 - y0 - 0.2) / 3
                c.line([(wx, yy), (wx, yy + 0.9 * K)], fill=OUTLINE, width=0.04)
                c.line([(wx, yy), (wx, yy + 0.9 * K)], fill=BRASS_D, width=0.02)
            c.line([(wx, y0 + 0.1 + 0.9 * K), (wx, y1 - 0.1 + 0.9 * K)], fill=OUTLINE, width=0.05)
            c.line([(wx, y0 + 0.1 + 0.9 * K), (wx, y1 - 0.1 + 0.9 * K)], fill=BRASS, width=0.028)
        c.line([(x0 + 0.04, y1 - 0.1 + 0.9 * K), (x1 - 0.04, y1 - 0.1 + 0.9 * K)], fill=OUTLINE, width=0.05)
        c.line([(x0 + 0.04, y1 - 0.1 + 0.9 * K), (x1 - 0.04, y1 - 0.1 + 0.9 * K)], fill=BRASS, width=0.028)
        S.plate(c, cx, y0 + 0.08, 0.5, 0.1, "DOWN", size=0.07)

    elif kind == "kessel":
        draw_boiler(p, x0, y0, x1, y1, extra, rnd)

    elif kind == "lochzange":
        # Fahrkarten-Lochzange auf Messingsaeule: Fuss, Saeule, Kasten mit Zange, Hebel, Schild STAMP
        c.soft_shadow([(cx - 0.2, y0 - 0.05), (cx + 0.25, y0 - 0.05), (cx + 0.25, y1), (cx - 0.2, y1)], 90, 0.06)
        c.ellipse(cx, y0 + 0.1, 0.17, 0.08, fill=BRASS_D, outline=OUTLINE, width=0.025)
        c.rect(cx - 0.04, y0 + 0.1, cx + 0.04, y0 + 0.95 * K, fill=BRASS, outline=OUTLINE, width=0.02)
        c.line([(cx - 0.015, y0 + 0.14), (cx - 0.015, y0 + 0.9 * K)], fill=BRASS_L, width=0.012)
        p.box(cx - 0.17, y0 + 0.02, cx + 0.17, y0 + 0.3, 0.95, 0.22, shade(IRON_L, 1.2), IRON_L, w=0.025)
        zt = y0 + 0.02 + 0.95 * K
        c.rect(cx - 0.17, zt + 0.02, cx + 0.17, zt + 0.07, fill=(40, 40, 46, 255))                       # Schlitz fuer den Fahrschein
        c.poly([(cx - 0.12, zt + 0.03), (cx + 0.04, zt + 0.03), (cx + 0.05, zt + 0.1), (cx - 0.11, zt + 0.1)], fill=PAPER, outline=OUTLINE, width=0.01)
        c.line([(cx - 0.1, zt + 0.07), (cx + 0.02, zt + 0.07)], fill=(170, 44, 50, 255), width=0.012)
        c.line([(cx + 0.1, zt + 0.12), (cx + 0.28, zt + 0.34)], fill=OUTLINE, width=0.05)             # Hebel
        c.line([(cx + 0.1, zt + 0.12), (cx + 0.28, zt + 0.34)], fill=BRASS, width=0.025)
        c.ellipse(cx + 0.28, zt + 0.34, 0.035, 0.035, fill=WOOD_D, outline=OUTLINE, width=0.012)
        c.ellipse(cx + 0.1, zt + 0.12, 0.025, 0.025, fill=BRASS_D, outline=OUTLINE, width=0.01)
        S.plate(c, cx, y0 + 0.02 + 0.42 * K + 0.05, 0.26, 0.07, "STAMP", size=0.045)
        c.glow(cx, zt + 0.2, 0.22, GREEN_LAMP, 0.4)
        c.ellipse(cx - 0.12, zt + 0.17, 0.018, 0.018, fill=GREEN_LAMP, outline=OUTLINE, width=0.008)

    elif kind == "dampfbremse":
        # Bremsstand aus Gusseisen: Fussplatte, Saeule, Quadrant mit Rasten, Messingskala, Hebel in der Raste, roter Griff
        p.box(x0, y0, x1, y1, 0, 0.12, IRON_L, IRON, w=0.03)
        S.rivets(c, [(x0 + 0.08 + k * 0.16, y0 + 0.04) for k in range(5)], 0.013)
        p.cyl(cx, cy, 0.09, 0.12, 0.5, IRON_L, IRON, ry=0.05, w=0.03)
        piv = (cx, cy + 0.62 * K + 0.02)
        rq = 0.42
        sector = [piv] + S.ellipse_pts(piv[0], piv[1], rq, rq * 0.9, 16, 15, 165)
        c.poly(sector, fill=IRON_L, outline=OUTLINE, width=0.035)
        c.poly([piv] + S.ellipse_pts(piv[0], piv[1], rq * 0.82, rq * 0.74, 16, 18, 162), fill=IRON)
        arc = S.ellipse_pts(piv[0], piv[1], rq * 0.9, rq * 0.81, 16, 15, 165)
        c.line(arc, fill=BRASS, width=0.035)
        for k in range(9):                                               # Rasten
            a = math.radians(20 + k * 17.5)
            c.line([(piv[0] + rq * 0.82 * math.cos(a), piv[1] + rq * 0.74 * math.sin(a)),
                    (piv[0] + rq * 0.98 * math.cos(a), piv[1] + rq * 0.88 * math.sin(a))], fill=INK, width=0.02 if k % 2 else 0.03)
        c.textf(piv[0] - rq * 0.95, piv[1] + 0.06, "OFF", 0.045, BRASS_L, kind="black")
        c.textf(piv[0] + rq * 0.95, piv[1] + 0.06, "FULL", 0.045, RED_LAMP, kind="black")
        a = math.radians(118)
        tip = (piv[0] + rq * 1.05 * math.cos(a), piv[1] + rq * 0.95 * math.sin(a))
        c.line([piv, tip], fill=OUTLINE, width=0.06)
        c.line([piv, tip], fill=STEEL_L, width=0.03)
        c.ellipse(tip[0], tip[1], 0.05, 0.05, fill=RED_LAMP, outline=OUTLINE, width=0.015)
        c.ellipse(tip[0] - 0.015, tip[1] + 0.015, 0.015, 0.012, fill=alpha(WHITE, 150))
        c.ellipse(piv[0], piv[1], 0.045, 0.04, fill=BRASS, outline=OUTLINE, width=0.015)
        S.gauge(c, cx + 0.28, cy + 0.28 * K + 0.02, 0.07, 70)
        S.plate(c, cx, y0 + 0.12 * K + 0.1, 0.5, 0.08, "STEAM BRAKE", size=0.048)

    elif kind == "handbremse":
        # Handbremse: Spindelsaeule auf Fussplatte, Messing-Handrad von oben mit sechs Speichen, Holzknauf, Schild
        p.box(x0 + 0.05, y0, x1 - 0.05, y1, 0, 0.1, IRON_L, IRON, w=0.03)
        p.cyl(cx, cy, 0.075, 0.1, 0.55, IRON_L, IRON, ry=0.04, w=0.03)
        c.rect(cx - 0.11, cy + 0.3 * K, cx + 0.11, cy + 0.34 * K, fill=BRASS_D, outline=OUTLINE, width=0.015)   # Ratsche
        wy = cy + 0.65 * K + 0.02
        c.ellipse(cx + 0.03, wy - 0.03, 0.34, 0.22, fill=(0, 0, 0, 50))
        S.handwheel(c, cx, wy, 0.33, 0.21, BRASS, spokes=6, w=0.035, rot=30)
        c.ellipse(cx, wy, 0.33, 0.21, outline=BRASS_L, width=0.012)
        a = math.radians(30)
        gx, gy = cx + 0.3 * math.cos(a), wy + 0.19 * math.sin(a)
        c.ellipse(gx, gy, 0.04, 0.035, fill=WOOD_D, outline=OUTLINE, width=0.015)
        S.plate(c, cx, y0 + 0.1 * K + 0.09, 0.36, 0.08, "BRAKE", size=0.05)

    elif kind in ("dachluke_zu", "dachluke_auf"):
        # Dachluke von oben: Messingrahmen, Deckel aus genietetem Blech mit zwei Scharnieren (Nordkante), Kurbel am
        # Suedrand; offen: Deckel nach Norden hochgeklappt (Unterseite sichtbar), dunkle Oeffnung
        fx0, fy0, fx1, fy1 = x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04
        c.rect(fx0 - 0.015, fy0 - 0.015, fx1 + 0.015, fy1 + 0.015, fill=(0, 0, 0, 60))
        c.poly(S.rrect_pts(fx0, fy0, fx1, fy1, 0.05), fill=BRASS, outline=OUTLINE, width=0.03)
        ix0, iy0, ix1, iy1 = fx0 + 0.07, fy0 + 0.07, fx1 - 0.07, fy1 - 0.07
        if kind == "dachluke_zu":
            c.rect(ix0, iy0, ix1, iy1, fill=STEEL, outline=OUTLINE, width=0.02)
            c.line([(cx, iy0 + 0.03), (cx, iy1 - 0.03)], fill=STEEL_D, width=0.015)
            c.line([(ix0 + 0.03, (iy0 + iy1) / 2), (ix1 - 0.03, (iy0 + iy1) / 2)], fill=STEEL_D, width=0.015)
            c.line([(ix0 + 0.02, iy1 - 0.02), (ix1 - 0.02, iy1 - 0.02)], fill=STEEL_L, width=0.012)
            S.rivets(c, [(ix0 + 0.05 + k * 0.14, iy1 - 0.04) for k in range(5)] + [(ix0 + 0.05 + k * 0.14, iy0 + 0.04) for k in range(5)], 0.011)
        else:
            c.rect(ix0, iy0, ix1, iy1, fill=(18, 16, 22, 255), outline=OUTLINE, width=0.02)
            c.rect(ix0 + 0.02, iy1 - 0.08, ix1 - 0.02, iy1 - 0.02, fill=(40, 36, 46, 255))
            c.glow(cx, (iy0 + iy1) / 2, 0.3, (120, 150, 220, 255), 0.18)
            lid = [(ix0, iy1 - 0.01), (ix1, iy1 - 0.01), (ix1 - 0.03, iy1 + 0.7 * K), (ix0 + 0.03, iy1 + 0.7 * K)]
            c.poly(lid, fill=STEEL_D, outline=OUTLINE, width=0.025)
            c.line([(ix0 + 0.05, iy1 + 0.7 * K - 0.025), (ix1 - 0.05, iy1 + 0.7 * K - 0.025)], fill=STEEL_L, width=0.012)
            c.line([(cx, iy1 + 0.02), (cx, iy1 + 0.7 * K - 0.03)], fill=(44, 46, 54, 255), width=0.012)
            S.rivets(c, [(ix0 + 0.06 + k * 0.14, iy1 + 0.06) for k in range(5)], 0.01, STEEL)
        for hx in (ix0 + 0.12, ix1 - 0.12):                               # Scharniere an der Nordkante
            c.rect(hx - 0.05, fy1 - 0.08, hx + 0.05, fy1 - 0.0, fill=BRASS_D, outline=OUTLINE, width=0.012)
            c.ellipse(hx, fy1 - 0.04, 0.012, 0.012, fill=BRASS_L)
        kx, ky = cx, fy0 + 0.05                                            # Kurbel am Suedrand
        c.ellipse(kx, ky, 0.045, 0.035, fill=IRON_L, outline=OUTLINE, width=0.015)
        c.line([(kx, ky), (kx + 0.16, ky + 0.09)], fill=OUTLINE, width=0.04)
        c.line([(kx, ky), (kx + 0.16, ky + 0.09)], fill=BRASS, width=0.02)
        c.ellipse(kx + 0.16, ky + 0.09, 0.028, 0.025, fill=WOOD_D, outline=OUTLINE, width=0.012)

    else:
        p.box(x0, y0, x1, y1, 0, h, shade(OAK, 1.1), OAK)

    return c.finish(), c.x0, c.y0, p.base_y


def draw_boiler(p, x0, y0, x1, y1, extra, rnd):
    """Lokkessel von der Feuerbuechse (Westen, am Fuehrerstand) bis zur Rauchkammer mit Schornstein und
    Scheinwerfer (Osten). Liegender Zylinder in schraeger Aufsicht: Grundrahmen, Kesselband, Dampfdom, Sanddom,
    Handlauf, Nieten, Dampf."""
    c = p.c
    r = 0.75
    yc = (y0 + y1) / 2
    xe = x1 + extra                                                       # Ostende (Pufferbohle der Lok)
    # Rahmen mit Zylindern und Radkaesten
    p.box(x0, y0, xe - 0.25, y1, 0, 0.35, IRON_L, IRON, w=0.035)
    for k in range(4):
        wx = x0 + 0.5 + k * 0.95
        c.ellipse(wx, y0 + 0.12, 0.32, 0.1, fill=(150, 44, 40, 255), outline=OUTLINE, width=0.03)
        c.ellipse(wx, y0 + 0.12, 0.08, 0.03, fill=BRASS, outline=OUTLINE, width=0.012)
    c.line([(x0 + 0.5, y0 + 0.12), (x0 + 0.5 + 3 * 0.95, y0 + 0.12)], fill=OUTLINE, width=0.05)       # Kuppelstange
    c.line([(x0 + 0.5, y0 + 0.12), (x0 + 0.5 + 3 * 0.95, y0 + 0.12)], fill=STEEL_L, width=0.028)
    # Feuerbuechse (kastenfoermig, westlich) und Kessel (Zylinder)
    ymin, ymax = yc - 0.59 * r, yc + 1.69 * r
    body = (40, 42, 50, 255)
    fx1 = x0 + 0.95
    c.poly([(x0, y0 + 0.35 * K), (fx1, y0 + 0.35 * K), (fx1, ymax + 0.08), (x0, ymax + 0.08)], fill=shade(body, 0.95), outline=OUTLINE, width=0.04)
    c.rect(x0 + 0.05, ymax - 0.25, fx1 - 0.05, ymax + 0.03, fill=shade(body, 1.3))
    S.rivets(c, [(x0 + 0.1 + k * 0.15, y0 + 0.35 * K + 0.08) for k in range(6)] + [(x0 + 0.1 + k * 0.15, ymax - 0.3) for k in range(6)], 0.014, STEEL_L)
    sx1 = xe - 0.35                                                       # Rauchkammer bis hier
    c.poly([(fx1, ymin), (sx1, ymin), (sx1, ymax), (fx1, ymax)], fill=body, outline=OUTLINE, width=0.04)
    c.poly([(fx1, yc + 0.15), (sx1, yc + 0.15), (sx1, ymax - 0.05), (fx1, ymax - 0.05)], fill=shade(body, 1.35))      # Lichtseite oben
    c.poly([(fx1, yc + 0.75), (sx1, yc + 0.75), (sx1, ymax - 0.25), (fx1, ymax - 0.25)], fill=shade(body, 1.6))
    c.poly([(fx1, ymin), (sx1, ymin), (sx1, ymin + 0.22), (fx1, ymin + 0.22)], fill=shade(body, 0.6))                 # Schattenseite unten
    for k in range(4):                                                    # Kesselbaender aus Messing
        bx = fx1 + 0.55 + k * 0.75
        if bx < sx1 - 0.2:
            c.rect(bx - 0.03, ymin, bx + 0.03, ymax, fill=BRASS, outline=OUTLINE, width=0.015)
            c.line([(bx - 0.01, ymin + 0.05), (bx - 0.01, ymax - 0.05)], fill=BRASS_L, width=0.01)
    c.line([(fx1 + 0.1, yc + 1.2), (sx1 - 0.1, yc + 1.2)], fill=OUTLINE, width=0.05)                                 # Handlauf
    c.line([(fx1 + 0.1, yc + 1.2), (sx1 - 0.1, yc + 1.2)], fill=BRASS, width=0.025)
    for k in range(5):
        c.ellipse(fx1 + 0.3 + k * 0.6, yc + 1.2, 0.025, 0.025, fill=BRASS_D, outline=OUTLINE, width=0.01)
    # Dampfdom mit Sicherheitsventil, Sanddom, Pfeife
    dx = fx1 + 1.2
    p.cyl(dx, yc + 0.2, 0.32, 1.5, 0.45, shade(BRASS_D, 1.1), BRASS_D, ry=0.16, w=0.03)
    c.line([(dx + 0.12, yc + 0.2 + 1.95 * K + 0.1), (dx + 0.12, yc + 0.2 + 1.95 * K + 0.35)], fill=OUTLINE, width=0.05)
    c.line([(dx + 0.12, yc + 0.2 + 1.95 * K + 0.1), (dx + 0.12, yc + 0.2 + 1.95 * K + 0.35)], fill=BRASS, width=0.025)
    p.cyl(dx + 1.0, yc + 0.2, 0.22, 1.5, 0.3, shade(body, 1.4), shade(body, 1.2), ry=0.12, w=0.03)
    p.cyl(dx - 0.55, yc + 0.3, 0.05, 1.5, 0.5, BRASS_L, BRASS, ry=0.03, w=0.015)
    # Rauchkammer (etwas groesser), Rauchkammertuer mit Messingring, Schornstein, Scheinwerfer
    c.poly([(sx1 - 0.3, ymin - 0.05), (xe - 0.1, ymin - 0.05), (xe - 0.1, ymax + 0.05), (sx1 - 0.3, ymax + 0.05)], fill=shade(body, 0.9), outline=OUTLINE, width=0.04)
    c.poly([(sx1 - 0.3, yc + 0.2), (xe - 0.1, yc + 0.2), (xe - 0.1, ymax), (sx1 - 0.3, ymax)], fill=shade(body, 1.25))
    c.ellipse(xe - 0.1, yc + 0.55 * r, 0.12, 1.14 * r, fill=shade(body, 0.8), outline=OUTLINE, width=0.04)         # Tuer (Stirn, gescherter Kreis)
    c.ellipse(xe - 0.1, yc + 0.55 * r, 0.1, 1.0 * r, outline=BRASS, width=0.02)
    c.ellipse(xe - 0.1, yc + 0.55 * r, 0.04, 0.12, fill=BRASS, outline=OUTLINE, width=0.012)
    chx = sx1 + 0.05
    p.cyl(chx, yc + 0.35, 0.2, 1.5, 0.85, (30, 30, 36, 255), (46, 46, 54, 255), ry=0.1, w=0.035)
    c.rect(chx - 0.26, yc + 0.35 + 2.35 * K - 0.04, chx + 0.26, yc + 0.35 + 2.35 * K + 0.04, fill=BRASS, outline=OUTLINE, width=0.015)
    hx, hy = xe - 0.25, yc + 0.35 + 1.55 * K + 0.12
    c.glow(hx + 0.15, hy, 0.75, WARM, 0.7)
    c.rect(hx - 0.14, hy - 0.12, hx + 0.14, hy + 0.14, fill=BRASS_D, outline=OUTLINE, width=0.025)
    c.ellipse(hx + 0.08, hy, 0.09, 0.1, fill=BULB, outline=OUTLINE, width=0.015)
    c.ellipse(hx + 0.1, hy + 0.02, 0.035, 0.04, fill=WHITE)
    c.line([(hx - 0.06, hy - 0.08), (hx - 0.06, hy + 0.1)], fill=BRASS_L, width=0.012)
    # Pufferbohle vorn ist Teil des Bodenbilds; hier noch die Nummer und Dampf
    S.plate(c, fx1 + 1.9, yc - 0.1, 0.46, 0.1, "No. 4", size=0.07)
    ct = yc + 0.35 + 2.35 * K                                             # Schornsteinoberkante
    for k, (ddx, ddy, rr) in enumerate(((-0.08, 0.26, 0.1), (-0.5, 0.6, 0.14), (-0.95, 0.88, 0.18), (-1.45, 1.04, 0.22), (-1.95, 1.14, 0.25))):
        steam_puff(c, chx + ddx, ct + ddy, rr, 180 - k * 28)
    steam_puff(c, dx + 0.25, yc + 0.2 + 1.95 * K + 0.55, 0.11, 130)
    steam_puff(c, dx + 0.42, yc + 0.2 + 1.95 * K + 0.72, 0.08, 90)
    # Feuerloch am Westende (zum Fuehrerstand): Schein
    c.glow(x0 - 0.05, yc, 0.4, (255, 140, 60, 255), 0.5)
    c.ellipse(x0 + 0.02, yc, 0.05, 0.14, fill=(255, 160, 70, 255), outline=OUTLINE, width=0.02)
