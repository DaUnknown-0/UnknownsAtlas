# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# vc_art.py - Grafik der sieben Zusatz-Sabotagen auf den Vanilla-Karten (Auftrag 2026-10-20, Teil 2):
#
#   engine    Skeld    Engine Failure     Schubhebel eines Triebwerks   Treibstoffpumpe        Raumschiff, Stahl, Warnstreifen
#   meteor    Skeld    Meteor Shower      Geschuetz nachfuehren         Schildgenerator laden  Raumschiff
#   blizzard  Polus    Blizzard           Windfahne der Wetterstation   Heizung aufziehen      Aussenstation, Schnee
#   lava      Polus    Lava Flood         Kuehlventil                   Kaltwasserpumpe        Polus, Lava-Rot
#   turb      Airship  Turbulence         Ballast trimmen               Gegengewicht winden    Luftschiff, Holz und Messing
#   blackout  alle     Blackout           Hauptschalter halten          (keine)                Sicherungskasten
#   comms     alle     Comms Chaos        Antenne nachstellen           (keine)                Funkgeraet
#
# Je Schluessel (100 px/m, Masse und Drehpunkte wie die Zugbilder in train_fx.py):
#   task_vc_<k>_panel.png 720 x 520, task_vc_<k>_lever.png 240 x 300 (Nabe bei 120|212),
#   task_vc_<k>_lever_arm.png 64 x 120 (Drehpunkt Unterkante Mitte), task_vc_<k>_gauge.png 160 x 160,
#   task_vc_<k>_needle.png 16 x 60 (Drehpunkt Unterkante Mitte), task_vc_<k>_wheel.png 220 x 220 (Mittelpunkt
#   Bildmitte, nur die fuenf mit Station 2), icon_vc_<k>.png 256 x 256 (Kartenknopf: heller Kreis, dunkler Rand).
# Effekte: fx_vc_meteor_flash.png 512 x 512, fx_vc_snow_near/far.png 256 x 256 nahtlos, fx_vc_heat.png 512 x 512
# nahtlos, fx_vc_noise.png 256 x 256 nahtlos.
#
#   python tools/vc_art.py   ->  assets/vanilla_crises/*.png, Uebersicht tools/_vc/preview.png

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_tasks import C, S, INK, BRASS, BRASS_L, BRASS_D, STEEL, STEEL_L, STEEL_D, CREAM, WHITE, mix, dark, light  # noqa: E402
from train_style import font  # noqa: E402
import train_fx  # noqa: E402

OUT = HERE.parent / "assets" / "vanilla_crises"
PREVIEW = HERE / "_vc"
TRANSP = (0, 0, 0, 0)
RED = (200, 56, 48, 255)
RED_L = (236, 96, 84, 255)
GREEN = (90, 200, 110, 255)
IRON, IRON_L = (58, 60, 68, 255), (96, 100, 110, 255)
WOOD, WOOD_L, WOOD_D = (150, 100, 58, 255), (184, 130, 80, 255), (108, 64, 36, 255)
ICE, ICE_L, ICE_D = (168, 196, 216, 255), (214, 232, 244, 255), (110, 140, 168, 255)
BASALT, BASALT_L, BASALT_D = (62, 54, 56, 255), (90, 80, 82, 255), (36, 30, 32, 255)
LAVA, LAVA_L = (255, 120, 40, 255), (255, 210, 90, 255)
OLIVE, OLIVE_L, OLIVE_D = (92, 104, 82, 255), (124, 138, 110, 255), (56, 64, 50, 255)
BOX, BOX_L, BOX_D = (120, 132, 118, 255), (154, 166, 150, 255), (78, 88, 76, 255)
ORANGE = (236, 150, 40, 255)
BLUE = (90, 170, 230, 255)

# Stil je Schluessel: Tafelmaterial, Grundtoene, Akzent (Lampen, Griffe), Beschriftungen, Rad-Art
STYLES = {
    "engine": dict(mat="steel", body=STEEL, body_l=STEEL_L, body_d=STEEL_D, frame=(48, 52, 62, 255), accent=ORANGE, grip=ORANGE,
                   lever="THROTTLE", gauge="THRUST", wheel="FUEL PUMP", wheel_kind="valve", wheel_col=RED, hazard=True, face=CREAM),
    "meteor": dict(mat="steel", body=(96, 104, 122, 255), body_l=(130, 138, 156, 255), body_d=(64, 70, 86, 255), frame=(44, 48, 62, 255),
                   accent=BLUE, grip=BLUE, lever="TURRET AIM", gauge="AIM", wheel="SHIELD CHARGE", wheel_kind="crank", wheel_col=STEEL_L, hazard=False, face=CREAM),
    "blizzard": dict(mat="ice", body=ICE, body_l=ICE_L, body_d=ICE_D, frame=(44, 70, 100, 255), accent=(255, 255, 255, 255), grip=(60, 120, 200, 255),
                     lever="WIND VANE", gauge="WIND", wheel="HEATER", wheel_kind="iron", wheel_col=(120, 128, 140, 255), hazard=False, face=(236, 244, 250, 255)),
    "lava": dict(mat="basalt", body=BASALT, body_l=BASALT_L, body_d=BASALT_D, frame=(120, 34, 30, 255), accent=LAVA, grip=(230, 70, 40, 255),
                 lever="COOLANT VALVE", gauge="HEAT", wheel="COLD WATER", wheel_kind="valve", wheel_col=(60, 130, 200, 255), hazard=False, face=(250, 232, 200, 255)),
    "turb": dict(mat="wood", body=WOOD, body_l=WOOD_L, body_d=WOOD_D, frame=(70, 40, 24, 255), accent=BRASS, grip=(160, 40, 40, 255),
                 lever="BALLAST TRIM", gauge="TRIM", wheel="COUNTERWEIGHT", wheel_kind="ship", wheel_col=WOOD_L, hazard=False, face=CREAM),
    "blackout": dict(mat="fusebox", body=BOX, body_l=BOX_L, body_d=BOX_D, frame=(50, 56, 50, 255), accent=(236, 196, 60, 255), grip=RED,
                     lever="MAIN BREAKER", gauge="POWER", wheel=None, wheel_kind=None, wheel_col=None, hazard=False, face=CREAM),
    "comms": dict(mat="radio", body=OLIVE, body_l=OLIVE_L, body_d=OLIVE_D, frame=(40, 46, 38, 255), accent=(90, 220, 120, 255), grip=(40, 40, 46, 255),
                  lever="ANTENNA", gauge="SIGNAL", wheel=None, wheel_kind=None, wheel_col=None, hazard=False, face=(216, 226, 200, 255)),
}
KEYS = list(STYLES)


def _text(c, x, y, s, px, fill=INK, kind="black", anchor="mm"):
    c.d.text((x * S, y * S), s, font=font(px * S, kind), fill=fill, anchor=anchor)


def _done(c):
    return c.img.resize((c.w, c.h), Image.LANCZOS)


def hazard_band(c, x0, y0, x1, y1, a=(236, 196, 60, 255), b=INK, step=28):
    m, md = c.mask()
    md.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=255)
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=a)
    x = x0 - (y1 - y0)
    while x < x1 + step:
        c.d.polygon([((x) * S, y1 * S), ((x + step / 2) * S, y1 * S), ((x + step / 2 + (y1 - y0)) * S, y0 * S), ((x + (y1 - y0)) * S, y0 * S)], fill=b)
        x += step
    # Rand ausserhalb des Bands wieder loeschen
    arr = np.asarray(c.img).copy()
    mm = np.asarray(m)
    outside = (mm == 0)
    # nur innerhalb des Rechtecks malen: die Diagonalen reichen darueber hinaus, deshalb hier zurueckholen
    return


def stripes(c, x0, y0, x1, y1, a=(236, 196, 60, 255), b=INK, step=28):
    """Warnstreifen in einem Rechteck (auf eigener Ebene gezeichnet und beschnitten)."""
    layer = Image.new("RGBA", c.img.size, TRANSP)
    d = ImageDraw.Draw(layer)
    h = y1 - y0
    x = x0 - h
    k = 0
    while x < x1 + step:
        d.polygon([(x * S, y1 * S), ((x + step / 2) * S, y1 * S), ((x + step / 2 + h) * S, y0 * S), ((x + h) * S, y0 * S)], fill=a if k % 2 == 0 else b)
        x += step / 2
        k += 1
    m = Image.new("L", c.img.size, 0)
    ImageDraw.Draw(m).rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=255)
    c.img.paste(layer, (0, 0), m)
    c.d = ImageDraw.Draw(c.img)


# ------------------------------------------------------------------ Tafeln 720 x 520

def panel(key):
    st = STYLES[key]
    c = C(720, 520)
    c.rrect(4, 4, 716, 516, 26, st["frame"], lw=8, sh=(0.12, 0.2))
    mat = st["mat"]
    ix0, iy0, ix1, iy1 = 28, 28, 692, 492
    if mat == "steel":
        c.rrect(ix0, iy0, ix1, iy1, 10, st["body"], lw=4, sh=(0.12, 0.2))
        c.brushed(0.05, seed=3)
        for r in range(2):                                              # genietete Platten 2 x 3
            for k in range(3):
                px0, py0 = ix0 + 10 + k * 218, iy0 + 10 + r * 228
                px1, py1 = px0 + 212, py0 + 220
                c.rrect(px0, py0, px1, py1, 6, mix(st["body"], st["body_l"], 0.12 * ((k + r) % 2)), lw=3, sh=(0.08, 0.14))
                for x in (px0 + 12, px1 - 12):
                    for y in (py0 + 12, py1 - 12):
                        c.rivet(x, y, 5, STEEL_L)
        if st["hazard"]:
            stripes(c, ix0 + 10, iy1 - 44, ix1 - 10, iy1 - 12)
            c.rrect(ix0 + 10, iy1 - 44, ix1 - 10, iy1 - 12, 3, None, lw=4)
        else:
            c.rrect(ix0 + 10, iy1 - 40, ix1 - 10, iy1 - 14, 4, st["accent"], lw=4, sh=(0.25, 0.3))
            for x in range(ix0 + 40, ix1 - 20, 60):
                c.ell(x, iy1 - 27, 5, 5, light(st["accent"], 0.5), lw=2)
        for k in range(6):                                              # Lueftungsschlitze rechts oben
            c.rrect(ix1 - 90, iy0 + 22 + k * 14, ix1 - 24, iy0 + 30 + k * 14, 3, st["body_d"], lw=2)
        c.vignette(0.22, ix0, iy0, ix1, iy1)
    elif mat == "ice":
        c.rrect(ix0, iy0, ix1, iy1, 10, st["body"], lw=4, sh=(0.1, 0.16))
        c.brushed(0.03, seed=5)
        for k in range(4):
            c.rrect(ix0 + 12 + k * 164, iy0 + 12, ix0 + 12 + k * 164 + 156, iy1 - 12, 6, mix(st["body"], st["body_l"], 0.1 * (k % 2)), lw=3, sh=(0.06, 0.12))
            for y in (iy0 + 24, iy1 - 24):
                c.rivet(ix0 + 12 + k * 164 + 14, y, 4, ICE_L)
                c.rivet(ix0 + 12 + k * 164 + 142, y, 4, ICE_L)
        rnd = random.Random(7)
        for (fx, fy, fr) in ((ix0 + 8, iy0 + 8, 70), (ix1 - 8, iy0 + 8, 60), (ix0 + 8, iy1 - 8, 80), (ix1 - 8, iy1 - 8, 64), (360, iy1 - 4, 50)):
            for i in range(14):                                         # Reif in den Ecken
                a = rnd.uniform(0, math.tau)
                r = rnd.uniform(0, fr)
                c.soft_poly([(fx + math.cos(a) * r - 10, fy + math.sin(a) * r - 6), (fx + math.cos(a) * r + 10, fy + math.sin(a) * r - 6),
                             (fx + math.cos(a) * r + 10, fy + math.sin(a) * r + 6), (fx + math.cos(a) * r - 10, fy + math.sin(a) * r + 6)], (255, 255, 255, 70), 6)
        for (sx, sy, ss) in ((120, 430, 16), (600, 120, 12), (640, 440, 10)):
            snowflake(c, sx, sy, ss, (255, 255, 255, 200), 2)
        for k in range(5):                                              # Eiszapfen an der Oberkante
            x = ix0 + 60 + k * 140
            c.poly([(x - 12, iy0 + 2), (x + 12, iy0 + 2), (x + 2, iy0 + 36 + 10 * (k % 2))], (226, 240, 250, 255), lw=3, sh=(0.1, 0.2))
        c.vignette(0.14, ix0, iy0, ix1, iy1)
    elif mat == "basalt":
        c.rrect(ix0, iy0, ix1, iy1, 10, st["body"], lw=4, sh=(0.1, 0.2))
        c.mottle(0.08, 18, seed=11)
        rnd = random.Random(3)
        for r in range(3):
            for k in range(4):
                px0, py0 = ix0 + 8 + k * 166, iy0 + 8 + r * 152
                c.rrect(px0, py0, px0 + 160, py0 + 146, 5, mix(st["body"], st["body_l"], rnd.uniform(0, 0.3)), lw=3, sh=(0.06, 0.16))
        cracks = [[(60, 480), (120, 400), (110, 330), (170, 250)], [(500, 490), (560, 420), (640, 400), (660, 330)], [(300, 480), (330, 440), (420, 430)]]
        for pts in cracks:                                              # gluehende Risse
            c.soft_poly([(x - 10, y - 10) for x, y in pts] + [(x + 10, y + 10) for x, y in pts[::-1]], (255, 120, 40, 90), 10)
            c.line(pts, (255, 90, 30, 255), 7)
            c.line(pts, (255, 220, 120, 255), 2.5)
        c.glow(360, iy1 + 20, 380, 60, (255, 120, 40, 110), 30)        # Lavaschein von unten
        c.rrect(ix0 + 10, iy1 - 34, ix1 - 10, iy1 - 14, 3, (120, 34, 30, 255), lw=3, sh=(0.2, 0.3))
        for x in range(ix0 + 40, ix1 - 20, 54):
            c.ell(x, iy1 - 24, 4, 4, LAVA, lw=2)
        c.vignette(0.26, ix0, iy0, ix1, iy1)
    elif mat == "wood":
        for i, y in enumerate(range(30, 492, 46)):
            col = mix(WOOD, WOOD_L, (i % 3) * 0.18)
            c.d.rectangle([ix0 * S, y * S, ix1 * S, (y + 44) * S], fill=col, outline=INK, width=3 * S)
            m, md = c.mask()
            md.rectangle([ix0 * S, y * S, ix1 * S, (y + 44) * S], fill=255)
            c.shade(m, 0.1, 0.2)
            c.grain(ix0, y, ix1, y + 44, 0.09, seed=10 + i, freq=0.5, mask=m)
            c.line([(ix0 + 4, y + 4), (ix1 - 4, y + 4)], (218, 166, 104, 90), 2)
        for x, sx in ((ix0, 1), (ix1, -1)):                             # Messingbeschlaege
            for y, sy in ((iy0, 1), (iy1, -1)):
                c.poly([(x, y), (x + sx * 70, y), (x + sx * 70, y + sy * 16), (x + sx * 16, y + sy * 16), (x + sx * 16, y + sy * 70), (x, y + sy * 70)],
                       BRASS, lw=4, sh=(0.25, 0.3))
                c.screw(x + sx * 48, y + sy * 8, 5, BRASS_L, rot=30)
                c.screw(x + sx * 8, y + sy * 48, 5, BRASS_L, rot=70)
        c.rrect(ix0 + 120, iy1 - 38, ix1 - 120, iy1 - 14, 4, BRASS, lw=4, sh=(0.25, 0.3))   # Messingleiste mit Nieten
        for x in range(ix0 + 140, ix1 - 120, 40):
            c.rivet(x, iy1 - 26, 4, BRASS_L)
        c.ell(ix1 - 70, iy0 + 70, 40, 40, (40, 60, 90, 255), lw=5, outline=BRASS_D)          # Bullauge mit Nachthimmel
        rnd = random.Random(4)
        for _ in range(14):
            a, r = rnd.uniform(0, math.tau), rnd.uniform(0, 34)
            c.ell(ix1 - 70 + math.cos(a) * r, iy0 + 70 + math.sin(a) * r, 1.5, 1.5, WHITE, lw=0)
        c.ell(ix1 - 70, iy0 + 70, 40, 40, None, lw=6, outline=BRASS)
        c.glint(ix1 - 84, iy0 + 52, 12, 6, 90, rot=35)
        c.vignette(0.3, ix0, iy0, ix1, iy1)
        c.glow(150, 90, 300, 230, (255, 200, 120, 34), 40)
    elif mat == "fusebox":
        c.rrect(ix0, iy0, ix1, iy1, 8, st["body"], lw=4, sh=(0.1, 0.2))
        c.brushed(0.03, seed=9)
        c.rrect(ix0 + 8, iy0 + 8, ix0 + 30, iy1 - 8, 4, st["body_d"], lw=3, sh=(0.1, 0.2))       # Scharnierleiste
        for y in range(iy0 + 40, iy1 - 30, 70):
            c.rrect(ix0 + 4, y, ix0 + 34, y + 30, 5, BOX_D, lw=3, sh=(0.2, 0.3))
            c.rivet(ix0 + 19, y + 15, 4, BOX_L)
        c.rrect(ix0 + 50, iy0 + 110, ix1 - 20, iy1 - 60, 6, st["body_d"], lw=4, sh=(0.1, 0.25))    # Sicherungsfeld
        for r in range(2):
            for k in range(8):
                x, y = ix0 + 90 + k * 72, iy0 + 160 + r * 130
                c.rrect(x - 18, y - 36, x + 18, y + 36, 4, (40, 44, 48, 255), lw=3)
                c.rrect(x - 11, y - 28, x + 11, y + 28, 3, CREAM, lw=3, sh=(0.15, 0.25))
                c.rrect(x - 13, y - 10, x + 13, y + 10, 2, BRASS, lw=2)
                c.ell(x, y + 48, 5, 5, GREEN if (k + r) % 5 else RED, lw=2, sh=(0.3, 0.3))
        c.rrect(ix0 + 60, iy1 - 50, ix1 - 30, iy1 - 20, 4, (236, 196, 60, 255), lw=3, sh=(0.2, 0.3))
        _text(c, (ix0 + 60 + ix1 - 30) / 2, iy1 - 35, "DANGER  HIGH VOLTAGE", 13, INK)
        c.poly([(ix1 - 60, iy0 + 20), (ix1 - 24, iy0 + 80), (ix1 - 96, iy0 + 80)], (236, 196, 60, 255), lw=4)
        c.poly([(ix1 - 56, iy0 + 38), (ix1 - 66, iy0 + 60), (ix1 - 58, iy0 + 60), (ix1 - 64, iy0 + 76), (ix1 - 50, iy0 + 54), (ix1 - 58, iy0 + 54)], INK, lw=0)
        c.vignette(0.2, ix0, iy0, ix1, iy1)
    elif mat == "radio":
        c.rrect(ix0, iy0, ix1, iy1, 10, st["body"], lw=4, sh=(0.12, 0.2))
        c.brushed(0.04, seed=12)
        c.rrect(ix0 + 16, iy0 + 110, ix0 + 300, iy1 - 24, 8, st["body_d"], lw=4, sh=(0.1, 0.2))     # Lautsprechergitter
        for y in range(iy0 + 124, iy1 - 34, 14):
            c.rrect(ix0 + 28, y, ix0 + 288, y + 7, 3, (34, 40, 30, 255), lw=1)
        for (kx, ky, lbl) in ((ix1 - 220, iy0 + 180, "GAIN"), (ix1 - 110, iy0 + 180, "SQUELCH")):   # Drehknoepfe
            c.ell(kx, ky, 44, 44, (40, 42, 46, 255), lw=4, sh=(0.2, 0.3))
            c.ell(kx, ky, 32, 32, OLIVE_L, lw=3, sh=(0.3, 0.3))
            c.line([(kx, ky), (kx + 20, ky - 22)], WHITE, 4)
            _text(c, kx, ky + 62, lbl, 11, CREAM)
        c.rrect(ix0 + 330, iy1 - 90, ix1 - 20, iy1 - 24, 6, (30, 36, 28, 255), lw=4)                # Frequenzskala
        c.rrect(ix0 + 338, iy1 - 82, ix1 - 28, iy1 - 32, 4, (60, 90, 60, 255), lw=0)
        for k in range(16):
            x = ix0 + 350 + k * 20
            c.line([(x, iy1 - 78), (x, iy1 - 78 + (14 if k % 4 == 0 else 8))], (190, 230, 180, 255), 2)
        c.line([(ix0 + 470, iy1 - 82), (ix0 + 470, iy1 - 32)], RED, 3)
        c.glow(ix0 + 470, iy1 - 57, 30, 24, (90, 220, 120, 60), 8)
        _text(c, (ix0 + 330 + ix1 - 20) / 2, iy1 - 40, "MHz", 9, (190, 230, 180, 255))
        for (lx, col) in ((ix1 - 60, GREEN), (ix1 - 36, RED)):
            c.ell(lx, iy0 + 56, 7, 7, col, lw=3, sh=(0.3, 0.3))
        c.vignette(0.24, ix0, iy0, ix1, iy1)
    return _done(c)


def snowflake(c, x, y, s, col, w):
    for k in range(3):
        a = math.radians(k * 60)
        dx, dy = math.cos(a) * s, math.sin(a) * s
        c.line([(x - dx, y - dy), (x + dx, y + dy)], col, w)
        for sgn in (-1, 1):
            for t in (0.5, 0.8):
                px, py = x + dx * t * sgn, y + dy * t * sgn
                for b in (a + math.radians(60), a - math.radians(60)):
                    c.line([(px, py), (px + math.cos(b) * s * 0.28 * sgn, py + math.sin(b) * s * 0.28 * sgn)], col, w * 0.8)


# ------------------------------------------------------------------ Hebelstand 240 x 300, Hebel 64 x 120

def lever(key):
    """Wie task_train_brake: Fussplatte, Korpus, Schlitz mit Kanten, Rasten links, Skala rechts, Nabe bei (120, 212)."""
    st = STYLES[key]
    body, body_l, body_d, acc = st["body"], st["body_l"], st["body_d"], st["accent"]
    if st["mat"] == "ice":
        body, body_l, body_d = ICE_D, ICE, (80, 104, 128, 255)
    if st["mat"] == "basalt":
        body, body_l, body_d = (84, 72, 74, 255), BASALT_L, BASALT_D
    c = C(240, 300)
    c.rrect(16, 282, 224, 298, 6, body_d, lw=5, sh=(0.1, 0.25))
    c.rrect(40, 40, 200, 290, 14, body_l, lw=6, sh=(0.14, 0.22))
    c.rrect(52, 52, 188, 278, 10, body, lw=4, sh=(0.1, 0.18))
    if st["mat"] == "wood":
        m, md = c.mask()
        md.rounded_rectangle([52 * S, 52 * S, 188 * S, 278 * S], 10 * S, fill=255)
        c.grain(52, 52, 188, 278, 0.08, seed=4, freq=0.4, mask=m)
    elif st["mat"] in ("steel", "fusebox", "radio", "ice"):
        c.brushed(0.04, seed=6)
    for y in (62, 268):
        for x in (64, 120, 176):
            c.rivet(x, y, 4, BRASS_L if st["mat"] == "wood" else STEEL_L)
    slot_rim = BRASS_D if st["mat"] == "wood" else body_d
    c.rrect(108, 56, 132, 216, 6, (22, 20, 26, 255), lw=4)
    c.rrect(100, 50, 140, 222, 8, None, lw=4, outline=slot_rim)
    c.line([(104, 54), (104, 218)], light(slot_rim, 0.4), 2)
    tick = BRASS if st["mat"] == "wood" else acc
    for i in range(8):
        y = 70 + i * 20
        c.line([(84, y), (100, y)], tick, 4)
        c.line([(140, y), (156, y)], tick, 3 if i % 2 else 5)
    top_lbl, bot_lbl = {"engine": ("IDLE", "FULL"), "meteor": ("LEFT", "RIGHT"), "blizzard": ("N", "S"), "lava": ("SHUT", "OPEN"),
                        "turb": ("BOW", "STERN"), "blackout": ("OFF", "ON"), "comms": ("LOW", "HIGH")}[key]
    _text(c, 72, 60, top_lbl, 11, light(tick, 0.3))
    _text(c, 72, 214, bot_lbl, 11, RED_L if key != "blackout" else GREEN)
    hub = BRASS if st["mat"] == "wood" else STEEL_L
    c.ell(120, 212, 16, 16, hub, lw=4, sh=(0.3, 0.3))
    c.ell(120, 212, 6, 6, INK, lw=0)
    plate = BRASS if st["mat"] == "wood" else (dark(acc, 0.9) if key == "blackout" else body_d)
    c.rrect(60, 234, 180, 258, 5, plate, lw=4, sh=(0.25, 0.3))
    _text(c, 120, 246, st["lever"], 9 if len(st["lever"]) > 9 else 11, INK if st["mat"] in ("wood",) or key == "blackout" else CREAM)
    c.ell(170, 246 + 24, 7, 7, acc if key in ("blizzard", "lava", "meteor") else RED, lw=3, sh=(0.3, 0.3))
    c.glint(168, 268, 2.5, 1.8, 170)
    c.vignette(0.18, 40, 40, 200, 290)
    return _done(c)


def lever_arm(key):
    st = STYLES[key]
    c = C(64, 120)
    pole = WOOD_D if st["mat"] == "wood" else STEEL
    c.capsule((32, 118), (32, 34), 12, pole, lw=4, sh=(0.2, 0.3))
    c.line([(29, 112), (29, 40)], light(pole, 0.3), 2)
    c.rrect(24, 60, 40, 72, 3, BRASS if st["mat"] in ("wood", "basalt") else STEEL_L, lw=3, sh=(0.3, 0.3))
    c.capsule((32, 36), (32, 10), 18, st["grip"], lw=4, sh=(0.22, 0.3))
    c.glint(28, 18, 3, 7, 140)
    return _done(c)


# ------------------------------------------------------------------ Anzeige 160 x 160, Zeiger 16 x 60

def gauge(key):
    st = STYLES[key]
    c = C(160, 160)
    cx, cy, r = 80, 80, 76
    rim = BRASS if st["mat"] in ("wood", "basalt") else (ICE_D if st["mat"] == "ice" else STEEL_D)
    c.ell(cx, cy, r, r, rim, lw=5, sh=(0.25, 0.3))
    c.ell(cx, cy, r * 0.84, r * 0.84, st["face"], lw=3, outline=dark(rim, 0.7))
    ri = r * 0.84

    def ang(v):
        return math.radians(225 - 270 * v / 100)
    bb = [(cx - ri * 0.9) * S, (cy - ri * 0.9) * S, (cx + ri * 0.9) * S, (cy + ri * 0.9) * S]
    g0, g1, r0 = {"engine": (55, 80, 92), "meteor": (45, 70, 90), "blizzard": (40, 65, 88), "lava": (0, 30, 85),
                  "turb": (40, 60, 88), "blackout": (70, 100, None), "comms": (70, 100, None)}[key]
    # PIL zeichnet im Uhrzeigersinn von start nach end (Winkel = -theta): Zone g0..g1 laeuft also von -theta(g0)
    # nach -theta(g1). Bis 20.10. vertauscht, dann lag Gruen auf dem Rest der Skala und Rot ueber fast allem.
    c.d.arc(bb, -(225 - 270 * g0 / 100), -(225 - 270 * g1 / 100), fill=GREEN, width=int(9 * S))
    if r0 is not None:
        c.d.arc(bb, -(225 - 270 * r0 / 100), -(225 - 270), fill=(230, 80, 70, 255), width=int(9 * S))
    ink = INK if st["mat"] != "basalt" else (60, 30, 20, 255)
    for v in range(0, 101, 10):
        a = ang(v)
        major = v % 20 == 0
        r_0, r_1 = ri * (0.78 if major else 0.84), ri * 0.94
        c.line([(cx + r_0 * math.cos(a), cy - r_0 * math.sin(a)), (cx + r_1 * math.cos(a), cy - r_1 * math.sin(a))], ink, 3 if major else 1.5)
        if major:
            _text(c, cx + ri * 0.64 * math.cos(a), cy - ri * 0.64 * math.sin(a), str(v), 10, ink, kind="bold")
    _text(c, cx, cy + 30, st["gauge"], 9, ink, kind="bold")
    c.ell(cx, cy, 7, 7, dark(rim, 0.8), lw=3, sh=(0.3, 0.3))
    c.glint(cx - r * 0.35, cy - r * 0.45, r * 0.25, r * 0.12, 60, rot=30)
    if st["mat"] == "ice":
        for (sx, sy) in ((cx - 50, cy + 44), (cx + 54, cy - 40)):
            snowflake(c, sx, sy, 7, (255, 255, 255, 230), 1.5)
    return _done(c)


def needle(key):
    st = STYLES[key]
    c = C(16, 60)
    col = RED if key not in ("blizzard", "meteor") else st["grip"]
    c.poly([(8, 2), (13, 56), (8, 60), (3, 56)], col, lw=2, sh=(0.2, 0.25))
    c.ell(8, 56, 4, 4, BRASS_D if st["mat"] in ("wood", "basalt") else STEEL_D, lw=2)
    return _done(c)


# ------------------------------------------------------------------ Rad 220 x 220 (Mittelpunkt Bildmitte)

def wheel(key):
    st = STYLES[key]
    kind, col = st["wheel_kind"], st["wheel_col"]
    c = C(220, 220)
    cx, cy, r = 110, 110, 100
    if kind == "valve":
        # Ventil-Handrad: Kranz, sechs Speichen, Nabe, Griffmulden
        c.ell(cx, cy, r, r, col, lw=6, sh=(0.25, 0.3))
        c.ell(cx, cy, r - 20, r - 20, TRANSP, lw=6)
        for k in range(6):
            a = math.radians(k * 60)
            c.capsule((cx + 14 * math.cos(a), cy + 14 * math.sin(a)), (cx + (r - 14) * math.cos(a), cy + (r - 14) * math.sin(a)), 12, col, lw=4, sh=(0.25, 0.3))
        for k in range(12):
            a = math.radians(k * 30 + 15)
            c.ell(cx + (r - 10) * math.cos(a), cy + (r - 10) * math.sin(a), 5, 5, dark(col, 0.7), lw=2)
        c.ell(cx, cy, 24, 24, STEEL_L, lw=5, sh=(0.3, 0.3))
        c.ell(cx, cy, 9, 9, INK, lw=0)
        c.glint(cx - 40, cy - 60, 24, 8, 60, rot=35)
    elif kind == "crank":
        # Ladekurbel des Schildgenerators: Scheibe mit Zahnkranz, Kurbelarm, Griff
        for k in range(24):
            a = math.radians(k * 15)
            c.rrect(cx + (r - 6) * math.cos(a) - 6, cy + (r - 6) * math.sin(a) - 6, cx + (r - 6) * math.cos(a) + 6, cy + (r - 6) * math.sin(a) + 6, 2, STEEL_D, lw=3)
        c.ell(cx, cy, r - 10, r - 10, STEEL, lw=6, sh=(0.2, 0.3))
        c.ell(cx, cy, r - 30, r - 30, STEEL_D, lw=4, sh=(0.15, 0.25))
        for k in range(8):
            a = math.radians(k * 45 + 22)
            c.line([(cx + 20 * math.cos(a), cy + 20 * math.sin(a)), (cx + 62 * math.cos(a), cy + 62 * math.sin(a))], STEEL_L, 3)
        c.capsule((cx, cy), (cx + 70, cy - 40), 14, STEEL_L, lw=4, sh=(0.25, 0.3))
        c.ell(cx + 70, cy - 40, 13, 13, BLUE, lw=4, sh=(0.25, 0.3))
        c.ell(cx, cy, 16, 16, BLUE, lw=4, sh=(0.3, 0.3))
        c.ell(cx, cy, 6, 6, INK, lw=0)
        c.glint(cx - 30, cy - 50, 20, 7, 60, rot=35)
    elif kind == "iron":
        # Aufziehrad der Heizung: Gusseisen mit vier breiten Speichen, Reif am Kranz, Holzknauf
        c.ell(cx, cy, r, r, col, lw=6, sh=(0.25, 0.3))
        c.ell(cx, cy, r - 18, r - 18, TRANSP, lw=6)
        for k in range(4):
            a = math.radians(k * 90 + 45)
            c.capsule((cx + 14 * math.cos(a), cy + 14 * math.sin(a)), (cx + (r - 12) * math.cos(a), cy + (r - 12) * math.sin(a)), 16, col, lw=4, sh=(0.25, 0.3))
        rnd = random.Random(5)
        for _ in range(20):
            a = rnd.uniform(0, math.tau)
            c.ell(cx + (r - 9) * math.cos(a), cy + (r - 9) * math.sin(a), rnd.uniform(3, 6), rnd.uniform(2, 4), (236, 244, 250, 220), lw=0)
        c.ell(cx, cy, 24, 24, (80, 86, 96, 255), lw=5, sh=(0.3, 0.3))
        c.ell(cx, cy, 8, 8, INK, lw=0)
        a = math.radians(45)
        c.ell(cx + (r - 8) * math.cos(a), cy + (r - 8) * math.sin(a), 11, 11, WOOD, lw=4, sh=(0.25, 0.3))
        c.glint(cx - 40, cy - 60, 24, 8, 60, rot=35)
    elif kind == "ship":
        # Schiffssteuerrad aus Holz mit Messingnabe und acht Griffen
        for k in range(8):
            a = math.radians(k * 45)
            c.capsule((cx + 60 * math.cos(a), cy + 60 * math.sin(a)), (cx + (r + 6) * math.cos(a), cy + (r + 6) * math.sin(a)), 14, WOOD, lw=4, sh=(0.25, 0.3))
            c.ell(cx + (r + 6) * math.cos(a), cy + (r + 6) * math.sin(a), 8, 8, WOOD_L, lw=3, sh=(0.3, 0.3))
        c.ell(cx, cy, 76, 76, WOOD, lw=6, sh=(0.25, 0.3))
        c.ell(cx, cy, 58, 58, TRANSP, lw=6)
        c.ell(cx, cy, 76, 76, None, lw=3, outline=BRASS_D)
        for k in range(8):
            a = math.radians(k * 45)
            c.capsule((cx + 18 * math.cos(a), cy + 18 * math.sin(a)), (cx + 60 * math.cos(a), cy + 60 * math.sin(a)), 10, WOOD_L, lw=4, sh=(0.25, 0.3))
        c.ell(cx, cy, 24, 24, BRASS, lw=5, sh=(0.3, 0.3))
        c.ell(cx, cy, 8, 8, INK, lw=0)
        c.glint(cx - 30, cy - 50, 20, 7, 60, rot=35)
    return _done(c)


# ------------------------------------------------------------------ Kartenknoepfe 256 x 256

def icon(key):
    """Runder Vanilla-Sabotageknopf: heller Kreis, dunkler Rand, Motiv in der Mitte (lesbar bei 40 px)."""
    ss = 4
    N = 256 * ss
    im = Image.new("RGBA", (N, N), TRANSP)
    d = ImageDraw.Draw(im)
    ink = (29, 27, 33, 255)
    lw = 9 * ss
    cx = cy = N / 2
    d.ellipse([12 * ss, 12 * ss, 244 * ss, 244 * ss], fill=(232, 234, 238, 255), outline=ink, width=12 * ss)
    d.ellipse([24 * ss, 24 * ss, 232 * ss, 232 * ss], outline=(200, 204, 212, 255), width=3 * ss)
    red = (210, 46, 40, 255)
    if key == "engine":
        # Triebwerksglocke mit Flamme, Riss in der Glocke
        d.polygon([(96 * ss, 70 * ss), (160 * ss, 70 * ss), (178 * ss, 150 * ss), (78 * ss, 150 * ss)], fill=(96, 104, 122, 255), outline=ink)
        d.line([(96 * ss, 70 * ss), (160 * ss, 70 * ss), (178 * ss, 150 * ss), (78 * ss, 150 * ss), (96 * ss, 70 * ss)], fill=ink, width=lw, joint="curve")
        d.rectangle([108 * ss, 44 * ss, 148 * ss, 72 * ss], fill=(60, 64, 76, 255), outline=ink, width=lw)
        d.line([(118 * ss, 90 * ss), (132 * ss, 112 * ss), (122 * ss, 132 * ss)], fill=ink, width=5 * ss)
        flame = [(84 * ss, 150 * ss), (172 * ss, 150 * ss), (160 * ss, 180 * ss), (142 * ss, 170 * ss), (128 * ss, 214 * ss), (114 * ss, 170 * ss), (96 * ss, 184 * ss)]
        d.polygon(flame, fill=ORANGE, outline=ink)
        d.line(flame + [flame[0]], fill=ink, width=6 * ss, joint="curve")
        d.polygon([(104 * ss, 152 * ss), (152 * ss, 152 * ss), (128 * ss, 192 * ss)], fill=(255, 230, 120, 255))
        _warn(d, ss, 188, 56, red, ink)
    elif key == "meteor":
        # Gestein mit Flammenschweif von links oben, Einschlagsterne
        for k, (x0, y0, w) in enumerate(((40, 48, 18), (56, 36, 12), (34, 72, 10))):
            d.line([(x0 * ss, y0 * ss), ((x0 + 60) * ss, (y0 + 60) * ss)], fill=(255, 190, 80, 255), width=w * ss)
        rock = [(128, 96), (176, 110), (196, 150), (176, 194), (128, 204), (96, 176), (90, 130)]
        d.polygon([(x * ss, y * ss) for x, y in rock], fill=(110, 96, 100, 255), outline=ink)
        d.line([(x * ss, y * ss) for x, y in rock] + [(128 * ss, 96 * ss)], fill=ink, width=lw, joint="curve")
        for (x, y, r) in ((140, 130, 12), (170, 160, 9), (120, 172, 8)):
            d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=(70, 60, 66, 255), outline=ink, width=4 * ss)
        d.polygon([(x * ss, y * ss) for x, y in ((100, 100), (128, 96), (90, 130))], fill=(255, 210, 110, 255))
        for (sx, sy) in ((208, 200), (222, 176), (200, 224)):
            d.line([((sx - 10) * ss, sy * ss), ((sx + 10) * ss, sy * ss)], fill=ink, width=5 * ss)
            d.line([(sx * ss, (sy - 10) * ss), (sx * ss, (sy + 10) * ss)], fill=ink, width=5 * ss)
    elif key == "blizzard":
        # grosse Schneeflocke mit Windlinien
        for k in range(3):
            a = math.radians(k * 60 + 90)
            dx, dy = math.cos(a) * 70 * ss, math.sin(a) * 70 * ss
            d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=ink, width=16 * ss)
            d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=(120, 190, 240, 255), width=8 * ss)
            for sgn in (-1, 1):
                for t in (0.5, 0.85):
                    px, py = cx + dx * t * sgn, cy + dy * t * sgn
                    for b in (a + math.radians(60), a - math.radians(60)):
                        ex, ey = px + math.cos(b) * 22 * ss * sgn, py + math.sin(b) * 22 * ss * sgn
                        d.line([(px, py), (ex, ey)], fill=ink, width=12 * ss)
                        d.line([(px, py), (ex, ey)], fill=(120, 190, 240, 255), width=5 * ss)
        d.ellipse([cx - 14 * ss, cy - 14 * ss, cx + 14 * ss, cy + 14 * ss], fill=(120, 190, 240, 255), outline=ink, width=5 * ss)
        for (y, ln) in ((60, 50), (196, 60)):
            d.line([(34 * ss, y * ss), ((34 + ln) * ss, y * ss)], fill=ink, width=7 * ss)
    elif key == "lava":
        # Lavawelle ueber dunklem Grund, Tropfen, Blasen
        d.rectangle([40 * ss, 160 * ss, 216 * ss, 200 * ss], fill=(60, 50, 52, 255), outline=ink, width=lw)
        wave = [(40, 150), (70, 120), (100, 140), (128, 96), (156, 136), (186, 112), (216, 148), (216, 170), (40, 170)]
        d.polygon([(x * ss, y * ss) for x, y in wave], fill=(255, 110, 40, 255), outline=ink)
        d.line([(x * ss, y * ss) for x, y in wave[:7]], fill=ink, width=lw, joint="curve")
        d.polygon([(x * ss, y * ss) for x, y in ((60, 150), (100, 146), (128, 112), (156, 142), (196, 148), (196, 166), (60, 166))], fill=(255, 190, 70, 255))
        for (x, y, r) in ((90, 60, 10), (150, 70, 8), (190, 86, 7)):
            d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=(255, 140, 50, 255), outline=ink, width=5 * ss)
        for (x, y, r) in ((110, 158, 7), (170, 156, 6)):
            d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=(255, 230, 140, 255), outline=ink, width=4 * ss)
    elif key == "turb":
        # schraeges Luftschiff mit Gondel und Wirbellinien
        env = Image.new("RGBA", (N, N), TRANSP)
        ed = ImageDraw.Draw(env)
        ed.ellipse([44 * ss, 92 * ss, 212 * ss, 160 * ss], fill=(196, 160, 96, 255), outline=ink, width=lw)
        ed.line([(60 * ss, 112 * ss), (196 * ss, 112 * ss)], fill=(150, 110, 60, 255), width=5 * ss)
        ed.rectangle([108 * ss, 160 * ss, 160 * ss, 184 * ss], fill=(110, 70, 40, 255), outline=ink, width=6 * ss)
        ed.polygon([(196 * ss, 118 * ss), (226 * ss, 100 * ss), (226 * ss, 150 * ss), (200 * ss, 136 * ss)], fill=(200, 60, 50, 255), outline=ink)
        ed.line([(196 * ss, 118 * ss), (226 * ss, 100 * ss), (226 * ss, 150 * ss), (200 * ss, 136 * ss)], fill=ink, width=6 * ss, joint="curve")
        env = env.rotate(18, resample=Image.BICUBIC, center=(cx, cy))
        im.alpha_composite(env)
        d = ImageDraw.Draw(im)
        for (x0, y0, x1, y1) in ((30, 70, 80, 60), (26, 190, 76, 200), (180, 206, 228, 212)):
            d.line([(x0 * ss, y0 * ss), (x1 * ss, y1 * ss)], fill=ink, width=7 * ss)
        d.arc([150 * ss, 30 * ss, 230 * ss, 90 * ss], 200, 340, fill=ink, width=7 * ss)
    elif key == "blackout":
        # Gluehbirne, dunkel, mit Riss und grossem Blitz
        d.ellipse([84 * ss, 40 * ss, 172 * ss, 128 * ss], fill=(70, 74, 84, 255), outline=ink, width=lw)
        d.polygon([(100 * ss, 110 * ss), (156 * ss, 110 * ss), (146 * ss, 150 * ss), (110 * ss, 150 * ss)], fill=(70, 74, 84, 255), outline=ink)
        d.line([(100 * ss, 110 * ss), (110 * ss, 150 * ss), (146 * ss, 150 * ss), (156 * ss, 110 * ss)], fill=ink, width=lw, joint="curve")
        d.rectangle([106 * ss, 150 * ss, 150 * ss, 178 * ss], fill=(150, 150, 156, 255), outline=ink, width=lw)
        d.rectangle([116 * ss, 178 * ss, 140 * ss, 192 * ss], fill=(60, 60, 68, 255), outline=ink, width=5 * ss)
        d.line([(112 * ss, 70 * ss), (126 * ss, 92 * ss), (116 * ss, 110 * ss)], fill=ink, width=5 * ss)
        bolt = [(150, 28), (122, 92), (146, 92), (118, 160), (178, 80), (152, 80), (176, 28)]
        d.polygon([(x * ss, y * ss) for x, y in bolt], fill=(236, 196, 60, 255), outline=ink)
        d.line([(x * ss, y * ss) for x, y in bolt] + [(150 * ss, 28 * ss)], fill=ink, width=7 * ss, joint="curve")
    elif key == "comms":
        # Antennenmast mit zerrissenen Funkwellen
        d.line([(128 * ss, 84 * ss), (128 * ss, 200 * ss)], fill=ink, width=14 * ss)
        d.line([(96 * ss, 200 * ss), (128 * ss, 120 * ss), (160 * ss, 200 * ss)], fill=ink, width=10 * ss, joint="curve")
        d.line([(100 * ss, 170 * ss), (156 * ss, 170 * ss)], fill=ink, width=8 * ss)
        d.rectangle([84 * ss, 196 * ss, 172 * ss, 214 * ss], fill=(90, 96, 110, 255), outline=ink, width=6 * ss)
        d.ellipse([116 * ss, 60 * ss, 140 * ss, 84 * ss], fill=(90, 220, 120, 255), outline=ink, width=6 * ss)
        for k, r in enumerate((44, 68, 92)):
            a0, a1 = 200, 340
            for seg_ in ((a0, a0 + 45), (a0 + 70, a0 + 100), (a0 + 120, a1)):
                d.arc([(128 - r) * ss, (72 - r) * ss, (128 + r) * ss, (72 + r) * ss], seg_[0], seg_[1], fill=ink, width=12 * ss)
                d.arc([(128 - r) * ss, (72 - r) * ss, (128 + r) * ss, (72 + r) * ss], seg_[0] + 2, seg_[1] - 2, fill=(90, 220, 120, 255), width=5 * ss)
        for (x, y) in ((60, 150), (196, 150), (72, 110)):
            d.line([((x - 8) * ss, (y - 8) * ss), ((x + 8) * ss, (y + 8) * ss)], fill=red, width=6 * ss)
            d.line([((x + 8) * ss, (y - 8) * ss), ((x - 8) * ss, (y + 8) * ss)], fill=red, width=6 * ss)
    return im.resize((256, 256), Image.LANCZOS)


def _warn(d, ss, x, y, red, ink):
    tri = [(x * ss, (y - 26) * ss), ((x + 26) * ss, (y + 20) * ss), ((x - 26) * ss, (y + 20) * ss)]
    d.polygon(tri, fill=(236, 196, 60, 255), outline=ink)
    d.line(tri + [tri[0]], fill=ink, width=6 * ss, joint="curve")
    d.rounded_rectangle([(x - 3) * ss, (y - 12) * ss, (x + 3) * ss, (y + 6) * ss], 2 * ss, fill=red)
    d.ellipse([(x - 4) * ss, (y + 9) * ss, (x + 4) * ss, (y + 17) * ss], fill=red)


# ------------------------------------------------------------------ Effekte

def fx_meteor_flash():
    """Einschlagsblitz 512 x 512: weisser Kern, gelb-oranger Schein, acht Strahlen, weicher Rand."""
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = cy = n / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (n / 2)
    ang = np.arctan2(yy - cy, xx - cx)
    rays = 0.55 + 0.45 * np.cos(ang * 8) ** 6
    fall = np.clip(1 - r / (0.55 + 0.45 * rays), 0, 1) ** 1.6
    core = np.clip(1 - r / 0.22, 0, 1) ** 1.2
    rgb = np.zeros((n, n, 3), np.float32)
    rgb[..., 0] = 255
    rgb[..., 1] = 150 + 105 * np.maximum(core, fall ** 2)
    rgb[..., 2] = 40 + 215 * core
    a = np.clip(fall * 0.9 + core, 0, 1)
    return Image.fromarray(np.concatenate([rgb, (a * 255)[..., None]], axis=2).astype(np.uint8), "RGBA")


def _wrapped_flakes(n, count, rmin, rmax, seed, blur, alpha):
    ss = 2
    img = Image.new("RGBA", (n * ss, n * ss), TRANSP)
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for _ in range(count):
        x, y, r = rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(rmin, rmax)
        a = rnd.randint(int(alpha * 0.6), alpha)
        for dx in (-n, 0, n):
            for dy in (-n, 0, n):
                d.ellipse([((x + dx - r) * ss), ((y + dy - r) * ss), ((x + dx + r) * ss), ((y + dy + r) * ss)], fill=(255, 255, 255, a))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur * ss))
    return img.resize((n, n), Image.LANCZOS)


def fx_snow_near():
    return _wrapped_flakes(256, 26, 4.0, 8.0, 21, 1.2, 240)


def fx_snow_far():
    return _wrapped_flakes(256, 90, 1.0, 2.6, 22, 0.5, 200)


def fx_heat():
    """Hitzeschimmer 512 x 512, nahtlos: orange, sehr transparent, wellige Baender aus periodischen Sinussummen."""
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n * 2 * math.pi
    v = np.zeros((n, n), np.float32)
    rnd = random.Random(31)
    for _ in range(6):
        kx, ky = rnd.randint(1, 4), rnd.randint(2, 7)
        v += np.sin(kx * xx + ky * yy + rnd.uniform(0, 6.3)) / math.sqrt(kx * kx + ky * ky)
    v = (v - v.min()) / (v.max() - v.min())
    a = (0.08 + 0.17 * v ** 2.2) * 255
    rgb = np.zeros((n, n, 3), np.float32)
    rgb[..., 0] = 255
    rgb[..., 1] = 120 + 60 * v
    rgb[..., 2] = 30 + 40 * v
    return Image.fromarray(np.concatenate([rgb, a[..., None]], axis=2).astype(np.uint8), "RGBA")


def fx_noise():
    """Funkrauschen 256 x 256, nahtlos: grau-gruenes Pixelrauschen mit Zeilenstreifen."""
    n = 256
    rng = np.random.default_rng(5)
    g = rng.uniform(0, 1, (n, n)).astype(np.float32)
    g = 0.6 * g + 0.4 * rng.uniform(0, 1, (n // 2, n)).repeat(2, axis=0)
    lines = 0.85 + 0.15 * np.sin(np.arange(n) / n * 2 * math.pi * 32)[:, None]
    v = np.clip(g * lines, 0, 1)
    rgb = np.zeros((n, n, 3), np.float32)
    rgb[..., 0] = 90 + 120 * v
    rgb[..., 1] = 120 + 130 * v
    rgb[..., 2] = 90 + 110 * v
    a = (110 + 120 * v)
    return Image.fromarray(np.concatenate([rgb, a[..., None]], axis=2).astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ Lieferung

def build_all():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(exist_ok=True)
    files = {}
    for k in KEYS:
        files[f"task_vc_{k}_panel.png"] = panel(k)
        files[f"task_vc_{k}_lever.png"] = lever(k)
        files[f"task_vc_{k}_lever_arm.png"] = lever_arm(k)
        files[f"task_vc_{k}_gauge.png"] = gauge(k)
        files[f"task_vc_{k}_needle.png"] = needle(k)
        if STYLES[k]["wheel_kind"]:
            files[f"task_vc_{k}_wheel.png"] = wheel(k)
        files[f"icon_vc_{k}.png"] = icon(k)
    files["fx_vc_meteor_flash.png"] = fx_meteor_flash()
    files["fx_vc_snow_near.png"] = fx_snow_near()
    files["fx_vc_snow_far.png"] = fx_snow_far()
    files["fx_vc_heat.png"] = fx_heat()
    files["fx_vc_noise.png"] = fx_noise()
    for name, im in files.items():
        im.save(OUT / name, optimize=True)
    # Uebersicht: je Schluessel eine Zeile (Tafel, Hebel, Arm, Anzeige, Zeiger, Rad, Knopf), darunter die Effekte
    rows = []
    for k in KEYS:
        row = [files[f"task_vc_{k}_panel.png"], files[f"task_vc_{k}_lever.png"], files[f"task_vc_{k}_lever_arm.png"],
               files[f"task_vc_{k}_gauge.png"], files[f"task_vc_{k}_needle.png"]]
        if STYLES[k]["wheel_kind"]:
            row.append(files[f"task_vc_{k}_wheel.png"])
        row.append(files[f"icon_vc_{k}.png"])
        ic = files[f"icon_vc_{k}.png"].resize((40, 40), Image.LANCZOS)
        row.append(ic)
        rows.append((k, row))
    fxs = [(n, files[n]) for n in ("fx_vc_meteor_flash.png", "fx_vc_snow_near.png", "fx_vc_snow_far.png", "fx_vc_heat.png", "fx_vc_noise.png")]
    pad = 16
    W = max(sum(im.width + pad for im in r) for _k, r in rows) + pad
    H = sum(max(im.height for im in r) + pad + 22 for _k, r in rows) + 512 + pad * 2 + 22 + 256 + 22
    sheet = Image.new("RGB", (W, H), (52, 54, 62))
    d = ImageDraw.Draw(sheet)
    for yy in range(0, H, 16):
        for xx in range(0, W, 16):
            if (xx // 16 + yy // 16) % 2 == 0:
                d.rectangle([xx, yy, xx + 15, yy + 15], fill=(60, 62, 70))
    f = font(14, "bold")
    y = pad
    for k, r in rows:
        x = pad
        hmax = max(im.height for im in r)
        for im in r:
            sheet.paste(im, (x, y), im)
            x += im.width + pad
        d.text((pad, y + hmax + 4), f"{k}: panel 720x520, lever 240x300, lever_arm 64x120, gauge 160x160, needle 16x60"
               + (", wheel 220x220" if STYLES[k]["wheel_kind"] else "") + ", icon 256 (und bei 40 px)", font=f, fill=(220, 224, 232))
        y += hmax + pad + 22
    x = pad
    for n, im in fxs:
        if im.width == 512:
            sheet.paste(im, (x, y), im)
            d.text((x, y + 516), n, font=f, fill=(220, 224, 232))
            x += 512 + pad
    y += 512 + pad + 22
    x = pad
    for n, im in fxs:
        if im.width == 256:
            tiled = Image.new("RGBA", (512, 256), (40, 40, 48, 255))
            tiled.alpha_composite(im, (0, 0)); tiled.alpha_composite(im, (256, 0))        # Nahtprobe
            sheet.paste(tiled, (x, y), tiled)
            d.text((x, y + 260), n + " (2x nebeneinander)", font=f, fill=(220, 224, 232))
            x += 512 + pad
    sheet.save(PREVIEW / "preview.png")
    print(f"vc_art: {len(files)} Dateien nach {OUT}, Uebersicht {PREVIEW / 'preview.png'} {sheet.size}")
    return files


if __name__ == "__main__":
    build_all()
