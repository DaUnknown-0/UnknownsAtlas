# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_park_tasks.py - Minispiel-Grafik des Moonlight Carnival (docs/PARK_KONZEPT.md).
#
# Der Park nutzt die Bausteine von Museum und Wald; AtlasMapDef.TaskArt leitet deren Dateien auf die
# Bilder hier um ("gallery:task_deer.png" -> task_park_duck.png). Deshalb gelten die Kontrakte aus
# gen_tasks.py: gleiche Groesse, gleicher Drehpunkt, gleiche Fenster wie die Datei, die ersetzt wird.
# Stil wie gen_tasks.py (flache Toene, Glanz, dunkle Kontur), Palette heiter-gruselig:
# Budenrot, Creme, Gold, Mitternachtsblau, Pflaume, dazu warmes Gluehbirnenlicht.
#
#   python tools/gen_park_tasks.py   ->  assets/task_park_*.png, task_bin_food/recycle, task_trash_*

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gen_tasks import (C, S, OUT, INK, GOLD, CREAM, WHITE, BRASS, BRASS_L, BRASS_D, STEEL_L, STEEL_D,
                       mix, dark, light, label, frame_wood, dial_face)

RED, RED_L, RED_D = (200, 56, 62, 255), (232, 98, 98, 255), (146, 36, 44, 255)
PLUM, PLUM_L, PLUM_D = (86, 56, 122, 255), (120, 86, 160, 255), (56, 34, 84, 255)
NIGHT, NIGHT_L = (26, 28, 58, 255), (44, 46, 88, 255)
TEAL, TEAL_L, TEAL_D = (46, 146, 150, 255), (90, 192, 190, 255), (30, 100, 106, 255)
BULB = (255, 234, 170, 255)
TRANSP = (0, 0, 0, 0)


def bulb(c, x, y, r=5):
    """Gluehbirne der Budenbeleuchtung: warmer Schein, heller Kern."""
    c.glow(x, y, r * 1.8, r * 1.8, (255, 214, 130, 120), r * 0.9)
    c.ell(x, y, r, r, BULB, lw=2, sh=(0.1, 0.25))
    c.glint(x - r * 0.3, y - r * 0.35, r * 0.4, r * 0.3, 200)


def marquee(c, x0, y0, x1, y1, step=40, r=5):
    for x in range(int(x0), int(x1) + 1, step):
        bulb(c, x, y0, r)
        bulb(c, x, y1, r)
    for y in range(int(y0) + step, int(y1) - step // 2, step):
        bulb(c, x0, y, r)
        bulb(c, x1, y, r)


def star_pts(cx, cy, r0, r1, n=5, rot=-90):
    pts = []
    for k in range(n * 2):
        a = math.radians(rot + k * 180 / n)
        r = r0 if k % 2 == 0 else r1
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def sky(c, w, h, top, bottom, power=1.4, box=None):
    arr = np.zeros((h * S, w * S, 4), dtype=np.float32)
    t = (np.arange(h * S) / (h * S))[:, None, None]
    arr[..., :3] = np.array(top[:3], dtype=np.float32) * (1 - t) ** power + np.array(bottom[:3], dtype=np.float32) * (1 - (1 - t) ** power)
    arr[..., 3] = 255
    img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    if box is None:
        c.img = img
    else:
        mk = Image.new("L", c.img.size, 0)
        ImageDraw.Draw(mk).rounded_rectangle([v * S for v in box[:4]], box[4] * S, fill=255)
        c.img.paste(img, (0, 0), mk)
    c.d = ImageDraw.Draw(c.img)


def stars(c, rnd, n, x0, y0, x1, y1, a=210):
    for _ in range(n):
        r = rnd.choice((1.2, 1.5, 2.0))
        c.ell(rnd.uniform(x0, x1), rnd.uniform(y0, y1), r, r, (255, 250, 230, a), lw=0)


def moon(c, x, y, r, glow=True):
    if glow:
        c.glow(x, y, r * 2.2, r * 2.2, (255, 244, 210, 70), r * 0.8)
    c.ell(x, y, r, r, (250, 244, 214, 255), lw=0)
    for mx, my, mr in ((-0.3, -0.2, 0.22), (0.25, 0.3, 0.15), (0.1, -0.45, 0.1)):
        c.ell(x + mx * r, y + my * r, mr * r, mr * r, (226, 216, 186, 255), lw=0)


# ------------------------------------------------------------------ Tafeln

def park_panel():
    """Budenwand: Zeltbahn in Weinrot, Goldleiste, Gluehbirnen im Rahmen (720 x 520 wie alle Tafeln)."""
    c = C(720, 520)
    frame_wood(c, (72, 34, 50, 255))
    c.rrect(26, 26, 694, 494, 14, GOLD, lw=4, sh=(0.22, 0.3))
    c.rrect(34, 34, 686, 486, 10, RED_D, lw=4)
    for i, x in enumerate(range(38, 682, 36)):                          # Zeltbahnen
        c.d.rectangle([x * S, 38 * S, min(x + 36, 682) * S, 482 * S], fill=(128, 34, 46, 255) if i % 2 == 0 else (100, 27, 40, 255))
    m, md = c.mask()
    md.rectangle([38 * S, 38 * S, 682 * S, 482 * S], fill=255)
    for x in range(38, 682, 36):                                        # Stofffalten: Licht links, Schatten rechts
        c.soft_poly([(x + 3, 40), (x + 9, 40), (x + 9, 480), (x + 3, 480)], (255, 200, 190, 22), 3)
        c.soft_poly([(x + 30, 40), (x + 35, 40), (x + 35, 480), (x + 30, 480)], (0, 0, 0, 40), 3)
    c.mottle(0.06, 18, seed=71, mask=m)
    c.vignette(0.5, 34, 34, 686, 486)
    c.glow(360, 40, 320, 110, (255, 210, 140, 26), 40)                  # Budenlicht von oben
    # keine Wimpel oben: dort stehen die Minispiel-Texte (y ~ 2,1 Einheiten)
    c.rrect(34, 452, 686, 486, 6, (70, 26, 36, 255), lw=4, sh=(0.2, 0.2))   # Theke unten
    c.line([(38, 456), (682, 456)], (170, 70, 76, 255), 2)
    marquee(c, 15, 15, 705, 505, 40, 5)
    for x in (15, 705):
        for y in (15, 505):
            c.ell(x, y, 9, 9, GOLD, lw=3, sh=(0.3, 0.3))
    c.save("task_park_panel.png")


def park_machine():
    """Technik der Fahrgeschaefte: rot lackierter Rahmen, Mitternachtsblech mit Riffelung, Goldlinie."""
    c = C(720, 520)
    c.rrect(4, 4, 716, 516, 26, RED_D, lw=8, sh=(0.18, 0.24))
    c.rrect(14, 14, 706, 506, 20, None, lw=2, outline=RED_L)
    c.rrect(26, 26, 694, 494, 14, (40, 46, 72, 255), lw=4)
    m, md = c.mask()
    md.rounded_rectangle([28 * S, 28 * S, 692 * S, 492 * S], 14 * S, fill=255)
    c.brushed(0.04, seed=8, mask=m)
    c.shade(m, 0.08, 0.16)
    for r, y in enumerate(range(58, 470, 22)):                          # Traenenblech
        for x in range(58 + (r % 2) * 11, 668, 22):
            c.line([(x - 4, y + 3), (x + 4, y - 3)], (30, 34, 54, 255), 4)
            c.line([(x - 4, y + 2), (x + 4, y - 4)], (66, 74, 108, 255), 2)
    c.vignette(0.3, 26, 26, 694, 494)
    c.rrect(44, 44, 676, 476, 10, None, lw=3, outline=(176, 142, 62, 255))  # Goldlinie
    for x in (48, 672):
        for y in (48, 472):
            c.screw(x, y, 8, BRASS_L, rot=30 + (x + y) % 90)
    for x in range(60, 680, 60):                                        # Nieten im Rahmen
        c.rivet(x, 14, 3, BRASS_L)
        c.rivet(x, 506, 3, BRASS_L)
    for i in range(6):                                                  # Warnstreifen
        x = 560 + i * 20
        c.poly([(x, 466), (x + 10, 466), (x - 4, 480), (x - 14, 480)], (232, 192, 60, 255) if i % 2 == 0 else INK, lw=0)
    c.save("task_park_machine.png")


# ------------------------------------------------------------------ Clean the Cotton Candy Machine (Rubbeln)

def park_candy():
    """Zuckerwattemaschine (Kontrakt wie task_museum_dino: 560 x 300, liegt unter der Zuckerschicht)."""
    c = C(560, 300)
    c.rrect(70, 196, 490, 292, 12, RED, lw=6, sh=(0.14, 0.26))           # Wagen
    for x in range(90, 480, 44):
        c.d.rectangle([x * S, 202 * S, (x + 22) * S, 286 * S], fill=(236, 222, 196, 255))
    m, md = c.mask()
    md.rounded_rectangle([73 * S, 199 * S, 487 * S, 289 * S], 10 * S, fill=255)
    c.shade(m, 0.1, 0.25)
    c.rrect(70, 196, 490, 292, 12, None, lw=6)
    c.rrect(180, 222, 380, 262, 8, GOLD, lw=5, sh=(0.25, 0.3))           # Schild
    label(c, 280, 242, "COTTON CANDY", 19, (120, 30, 40, 255))
    c.rrect(60, 186, 500, 204, 6, RED_D, lw=5, sh=(0.25, 0.25))          # Wagenkante
    # Edelstahlschuessel (seitlich): Rand oben, Koerper nach unten schmaler
    c.poly([(36, 76), (524, 76), (446, 190), (114, 190)], (176, 184, 196, 255), lw=6, shx=(0.3, 0.32))
    for x in (150, 280, 410):
        c.line([(x, 92), (x + (280 - x) * 0.1, 182)], (206, 212, 222, 140), 3)
    c.ell(280, 76, 246, 30, (206, 212, 222, 255), lw=6, sh=(0.2, 0.2))   # Rand
    c.ell(280, 78, 226, 22, (120, 128, 142, 255), lw=3, sh=(-0.05, 0.2))  # Innenseite
    c.rrect(252, 40, 308, 86, 10, (150, 156, 168, 255), lw=5, shx=(0.3, 0.3))   # Spinnkopf
    c.ell(280, 40, 28, 9, RED, lw=4, sh=(0.3, 0.2))
    c.ell(280, 36, 8, 4, GOLD, lw=2)
    c.glint(120, 118, 50, 12, 90, rot=-12)
    c.glint(400, 70, 60, 6, 110)
    c.save("task_park_candy.png")


def park_sugar():
    """Zuckerkruste (280 x 150 bei 50 px/Einheit, wie task_museum_dust): rosa, klebrig, Faeden."""
    w, h = 280, 150
    rnd = np.random.default_rng(17)
    small = rnd.random((9, 16)).astype(np.float32)
    cloud = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255
    fine = rnd.random((h, w)).astype(np.float32)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4)), dtype=np.float32) / 255
    v = (cloud - 0.5) * 50 + (fine - 0.5) * 24
    rgb = np.stack([236 + v * 0.4, 150 + v, 192 + v * 0.7], axis=-1)
    a = np.full((h, w), 236, dtype=np.float32) - (cloud - 0.5) * 24
    ys = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    edge = np.minimum(np.minimum(xs, w - 1 - xs), np.minimum(ys, h - 1 - ys)).astype(np.float32)
    a *= np.clip(edge / 3.0 + (fine - 0.5) * 0.8, 0, 1)
    img = Image.fromarray(np.clip(np.concatenate([rgb, a[..., None]], axis=-1), 0, 255).astype(np.uint8), "RGBA")
    # Karamellflecken (angebrannter Zucker)
    kr = Image.new("RGBA", (w * 2, h * 2), TRANSP)
    kd = ImageDraw.Draw(kr)
    for _ in range(26):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        r = int(rnd.integers(5, 16))
        kd.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(196, 104, 92, 120))
    img.alpha_composite(kr.filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.LANCZOS))
    # Watte-Faeden: helle, geschwungene Linien
    fb = Image.new("RGBA", (w * 2, h * 2), TRANSP)
    fd = ImageDraw.Draw(fb)
    for _ in range(46):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        ang = rnd.random() * math.pi
        pts = [(x, y)]
        for k in range(1, 6):
            ang += (rnd.random() - 0.5) * 1.1
            pts.append((pts[-1][0] + math.cos(ang) * 16, pts[-1][1] + math.sin(ang) * 16))
        fd.line(pts, fill=(255, 214, 236, 150), width=2, joint="curve")
    img.alpha_composite(fb.filter(ImageFilter.GaussianBlur(0.8)).resize((w, h), Image.LANCZOS))
    # Zuckerkristalle
    cr = Image.new("RGBA", (w * 2, h * 2), TRANSP)
    cd = ImageDraw.Draw(cr)
    for _ in range(120):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        cd.rectangle([x, y, x + 2, y + 2], fill=(255, 255, 255, 200))
    img.alpha_composite(cr.resize((w, h), Image.LANCZOS))
    img.save(OUT / "task_park_sugar.png")
    print(OUT / "task_park_sugar.png", img.size)


# ------------------------------------------------------------------ Plan the Parade Route (Pfad)

def park_parademap():
    c = C(720, 520)
    c.rrect(40, 34, 680, 494, 20, (0, 0, 0, 100), lw=0)
    c.rrect(40, 30, 680, 490, 20, (240, 226, 196, 255), lw=8, sh=(0.04, 0.08))
    m, md = c.mask()
    md.rounded_rectangle([44 * S, 34 * S, 676 * S, 486 * S], 20 * S, fill=255)
    c.mottle(0.03, 22, seed=19, mask=m)
    c.rrect(52, 42, 668, 478, 12, None, lw=3, outline=(200, 92, 86, 255))
    c.rrect(58, 48, 662, 472, 10, None, lw=1, outline=(200, 92, 86, 255))
    faint = (214, 190, 150, 255)
    # Parkwege (breit, blass) und Gruen
    for pts in ([(60, 260), (200, 250), (360, 270), (520, 240), (660, 260)], [(360, 60), (350, 200), (370, 330), (360, 470)],
                [(120, 90), (200, 180), (220, 400)], [(540, 90), (560, 380), (620, 450)]):
        c.line(pts, (226, 208, 172, 255), 22)
    rnd = random.Random(12)
    for _ in range(30):
        x, y = rnd.uniform(80, 640), rnd.uniform(80, 440)
        c.ell(x, y, 9, 7, (176, 200, 150, 200), lw=0)
    c.ell(560, 170, 50, 26, (178, 206, 226, 255), lw=2, outline=faint)  # Teich
    # Fahrgeschaefte als blasse Symbole
    cx, cy = 150, 150                                                   # Riesenrad
    c.ell(cx, cy, 34, 34, None, lw=3, outline=faint)
    for k in range(8):
        a = math.radians(k * 45)
        c.line([(cx, cy), (cx + math.cos(a) * 34, cy + math.sin(a) * 34)], faint, 2)
    c.line([(cx - 20, cy + 50), (cx, cy), (cx + 20, cy + 50)], faint, 3)
    for tx, ty in ((460, 380), (250, 420)):                             # Zelte
        c.poly([(tx - 30, ty), (tx, ty - 34), (tx + 30, ty), (tx + 30, ty + 20), (tx - 30, ty + 20)], (232, 206, 180, 255), lw=2, outline=faint)
        c.line([(tx - 10, ty - 22), (tx - 10, ty + 20)], faint, 2)
        c.line([(tx + 10, ty - 22), (tx + 10, ty + 20)], faint, 2)
    loop = [(430 + 120 * t, 110 + 30 * math.sin(t * 9)) for t in [i / 30 for i in range(31)]]   # Achterbahn
    c.line(loop, faint, 4)
    moon(c, 628, 440, 16, glow=False)
    c.rrect(250, 452, 470, 478, 6, (200, 70, 70, 255), lw=3, sh=(0.2, 0.2))   # Titelband
    label(c, 360, 465, "MOONLIGHT CARNIVAL", 13, CREAM)
    c.save("task_park_parademap.png")
    c = C(70, 90)                                                       # Wimpel (Kontrakt wie task_flag: Stange x 20)
    c.line([(20, 84), (20, 8)], INK, 6)
    c.line([(21, 82), (21, 10)], (230, 206, 120, 255), 2)
    c.poly([(22, 8), (64, 22), (22, 38)], RED, lw=4, sh=(0.15, 0.25))
    c.poly([(24, 18), (44, 22), (24, 28)], CREAM, lw=0)
    c.poly([(22, 8), (64, 22), (22, 38)], None, lw=4)
    c.ell(20, 6, 5, 5, GOLD, lw=2)
    c.save("task_park_pennant.png")
    c = C(60, 60)                                                       # Paradewagen-Marke (Pauke von oben)
    c.ell(30, 32, 22, 22, (0, 0, 0, 90), lw=0)
    c.ell(30, 30, 22, 22, GOLD, lw=5, sh=(0.25, 0.3))
    c.ell(30, 30, 15, 15, RED, lw=3, sh=(0.2, 0.3))
    c.poly(star_pts(30, 30, 10, 4), CREAM, lw=0)
    c.glint(24, 22, 6, 3, 150, rot=35)
    c.save("task_park_float.png")


# ------------------------------------------------------------------ Aim the Tower Spotlights (Spiegel)

def park_spotlight():
    c = C(110, 110)                                                     # Kontrakt wie task_emitter: Strahl rechts
    c.poly([(30, 96), (40, 70), (52, 70), (62, 96)], STEEL_D, lw=4, sh=(0.2, 0.25))   # Fuss
    c.rrect(10, 30, 80, 78, 12, (72, 76, 88, 255), lw=5, shx=(0.3, 0.3))
    c.rrect(26, 30, 36, 78, 2, RED, lw=3)
    c.line([(16, 40), (72, 40)], (120, 126, 138, 255), 2)
    c.glow(94, 54, 18, 26, (255, 230, 150, 160), 6)
    c.ell(84, 54, 16, 28, (96, 100, 112, 255), lw=5, sh=(0.25, 0.3))
    c.ell(88, 54, 11, 21, (255, 240, 180, 255), lw=3)
    c.glint(86, 46, 4, 7, 220)
    c.save("task_park_spotlight.png")


# ------------------------------------------------------------------ Spot the Runaway Balloon (Fernglas)

def park_panorama():
    """Park bei Nacht (Kontrakt wie task_panorama: 1600 x 520, Ziel sitzt auf 0,4 Einheiten unter der Mitte)."""
    rnd = random.Random(8)
    c = C(1600, 520)
    sky(c, 1600, 520, (14, 14, 40), (86, 54, 104), 1.2)
    stars(c, rnd, 90, 0, 0, 1600, 220)
    moon(c, 260, 96, 38)
    # ferne Baumkante
    pts = [(0, 520)] + [(x, 360 + 14 * math.sin(x / 70) + 8 * math.sin(x / 23)) for x in range(0, 1601, 16)] + [(1600, 520)]
    c.poly(pts, (38, 30, 66, 255), lw=0)
    # Achterbahn-Gerippe links
    track = [(x, 250 + 70 * math.sin((x - 420) / 90) * (0.6 + 0.4 * math.sin(x / 210))) for x in range(420, 860, 8)]
    for x, y in track[::5]:
        c.line([(x, y), (x, 440)], (58, 44, 86, 255), 5)
    for (x0, y0), (x1, y1) in zip(track[::5], track[5::5]):
        c.line([(x0, y0 + 20), (x1, 440)], (58, 44, 86, 255), 3)
    c.line(track, (74, 56, 104, 255), 10)
    c.line(track, (110, 88, 140, 255), 3)
    # Zirkuszelt Mitte
    tx, ty = 980, 300
    c.poly([(tx - 130, ty + 20), (tx, ty - 110), (tx + 130, ty + 20), (tx + 120, 440), (tx - 120, 440)], (110, 44, 64, 255), lw=5)
    for k in range(-3, 4):
        c.line([(tx, ty - 110), (tx + k * 38, ty + 20), (tx + k * 36, 440)], (140, 110, 120, 255) if k % 2 else (90, 34, 52, 255), 12)
    c.poly([(tx - 130, ty + 20), (tx, ty - 110), (tx + 130, ty + 20), (tx + 120, 440), (tx - 120, 440)], None, lw=5)
    c.line([(tx, ty - 110), (tx, ty - 150)], INK, 4)
    c.poly([(tx, ty - 150), (tx + 30, ty - 140), (tx, ty - 130)], RED, lw=3)
    # Riesenrad rechts
    wx, wy, wr = 1300, 230, 150
    c.line([(wx - 90, 440), (wx, wy), (wx + 90, 440)], (60, 48, 90, 255), 12)
    c.ell(wx, wy, wr, wr, None, lw=8, outline=(70, 56, 100, 255))
    c.ell(wx, wy, wr - 16, wr - 16, None, lw=3, outline=(70, 56, 100, 255))
    for k in range(12):
        a = math.radians(k * 30)
        c.line([(wx, wy), (wx + math.cos(a) * wr, wy + math.sin(a) * wr)], (70, 56, 100, 255), 3)
    for k in range(12):
        a = math.radians(k * 30 + 15)
        gx, gy = wx + math.cos(a) * wr, wy + math.sin(a) * wr
        c.rrect(gx - 12, gy + 2, gx + 12, gy + 22, 5, ((150, 60, 70, 255), (60, 110, 120, 255), (160, 130, 60, 255))[k % 3], lw=3)
    for k in range(36):
        a = math.radians(k * 10)
        bulb(c, wx + math.cos(a) * wr, wy + math.sin(a) * wr, 3)
    c.ell(wx, wy, 14, 14, GOLD, lw=4)
    # Karussell ganz rechts und links ein Budendach
    for bx, bw in ((1520, 90), (130, 110)):
        c.poly([(bx - bw, 380), (bx, 320), (bx + bw, 380)], (96, 60, 110, 255), lw=4)
        for k in range(-2, 3):
            c.ell(bx + k * bw / 2.5, 384, bw / 5.5, 8, (130, 90, 140, 255), lw=3)
        c.rrect(bx - bw + 10, 386, bx + bw - 10, 440, 4, (48, 36, 70, 255), lw=4)
        for k in range(-3, 4):
            bulb(c, bx + k * bw / 3.6, 384, 3)
    # Lichterketten
    for x0, x1 in ((0, 420), (860, 1150), (1450, 1600)):
        pts = [(x0 + (x1 - x0) * t, 330 + 40 * math.sin(math.pi * t)) for t in [i / 24 for i in range(25)]]
        c.line(pts, (40, 30, 50, 255), 2)
        for x, y in pts[1::2]:
            bulb(c, x, y, 3)
    # Vordergrund: Boden, Zaun, Laternen
    c.poly([(0, 520), (0, 430)] + [(x, 432 + 6 * math.sin(x / 90)) for x in range(0, 1601, 40)] + [(1600, 520)], (22, 18, 36, 255), lw=0)
    for x in range(0, 1600, 26):
        c.line([(x, 470), (x, 440)], (40, 32, 56, 255), 4)
    c.line([(0, 448), (1600, 448)], (40, 32, 56, 255), 4)
    for x in (360, 740, 1160, 1480):
        c.line([(x, 470), (x, 390)], (30, 26, 44, 255), 6)
        c.glow(x, 386, 26, 26, (255, 214, 130, 90), 10)
        c.ell(x, 386, 8, 8, BULB, lw=3)
    c.vignette(0.25, 0, 0, 1600, 520)
    c.save("task_park_panorama.png")
    c = C(120, 160)                                                     # Ausreisser-Ballon
    c.ell(60, 64, 44, 54, RED, lw=6, sh=(0.18, 0.3))
    c.glint(44, 40, 12, 18, 150, rot=20)
    c.poly([(52, 118), (68, 118), (60, 108)], RED_D, lw=4)
    c.line([(60, 120), (54, 132), (64, 144), (58, 158)], INK, 3)
    c.save("task_park_balloon.png")


# ------------------------------------------------------------------ Unlock the Ride Keys (Reihenfolge)

def park_glyph(c, cx, cy, k, s=1.0, col=INK, w=7):
    """Zehn Park-Symbole (k = 0..9), Kontrakt wie glyph() in gen_tasks.py: einfarbig, der Code faerbt ein."""
    L = lambda pts, ww=w: c.line([(cx + x * s, cy + y * s) for x, y in pts], col, ww * s)
    F = lambda pts: c.poly([(cx + x * s, cy + y * s) for x, y in pts], col, lw=0)
    E = lambda x, y, rx, ry, fill=False, ww=w: c.ell(cx + x * s, cy + y * s, rx * s, ry * s, col if fill else None, lw=int(ww * s), outline=col)
    H = lambda x, y, rx, ry: c.d.ellipse([(cx + (x - rx) * s) * S, (cy + (y - ry) * s) * S, (cx + (x + rx) * s) * S, (cy + (y + ry) * s) * S], fill=TRANSP)
    if k == 0:   # Riesenrad
        E(0, -5, 19, 19)
        for a in range(0, 180, 45):
            r = math.radians(a)
            L([(math.cos(r) * 19, -5 + math.sin(r) * 19), (-math.cos(r) * 19, -5 - math.sin(r) * 19)], w - 3)
        L([(-15, 26), (0, -5), (15, 26)], w - 1)
    elif k == 1:   # Zelt
        F([(-25, 0), (0, -24), (25, 0)])
        L([(-20, 0), (-20, 24), (20, 24), (20, 0)], w - 1)
        F([(-7, 24), (0, 8), (7, 24)])
        L([(0, -24), (0, -31)], w - 3); F([(0, -32), (11, -28), (0, -24)])
    elif k == 2:   # Looping
        L([(-28, 22), (-4, 22)], w - 1); E(0, 4, 12, 14, ww=w - 1); L([(4, 22), (28, 22)], w - 1)
        F([(-24, 12), (-12, 12), (-12, 20), (-24, 20)])
    elif k == 3:   # Ballon
        E(0, -8, 14, 17, True); F([(-4, 11), (4, 11), (0, 5)]); L([(0, 11), (-5, 18), (3, 24), (0, 31)], w - 4)
    elif k == 4:   # Eintrittskarte
        F([(-26, -13), (26, -13), (26, -5), (21, 0), (26, 5), (26, 13), (-26, 13), (-26, 5), (-21, 0), (-26, -5)])
        H(10, -8, 2.2, 2.2); H(10, 0, 2.2, 2.2); H(10, 8, 2.2, 2.2)
        c.poly([(cx + x * s, cy + y * s) for x, y in star_pts(-6, 0, 8, 3.4)], TRANSP, lw=0)
    elif k == 5:   # Stern
        F(star_pts(0, 1, 25, 10))
    elif k == 6:   # Mondsichel
        E(0, 0, 21, 21, True); H(10, -7, 18, 18)
    elif k == 7:   # Ente
        F([(-22, 4), (-28, -8), (-14, 0)]); E(-2, 8, 19, 12, True); E(12, -9, 9, 9, True); F([(19, -12), (29, -8), (19, -4)])
        H(14, -11, 2.2, 2.2)
    elif k == 8:   # Gespenst
        pts = [(math.cos(math.radians(a)) * 18, -4 - math.sin(math.radians(a)) * 18) for a in range(0, 181, 15)]
        F(pts + [(-18, 24), (-12, 17), (-6, 24), (0, 17), (6, 24), (12, 17), (18, 24)])
        H(-7, -6, 3.5, 5); H(7, -6, 3.5, 5)
    elif k == 9:   # Eistuete
        F([(-13, 0), (13, 0), (0, 30)]); E(0, -9, 15, 12, True); E(0, -24, 4, 4, True)


def park_keys():
    c = C(120, 150)                                                     # Schluesselanhaenger (Kontrakt wie task_cartouche)
    c.rrect(8, 12, 112, 146, 22, (0, 0, 0, 80), lw=0)
    c.rrect(8, 8, 112, 142, 22, (246, 204, 96, 255), lw=6, sh=(0.14, 0.24))
    c.rrect(18, 34, 102, 130, 14, (252, 244, 222, 255), lw=3, sh=(0.03, 0.08))
    c.ell(60, 20, 8, 8, TRANSP, lw=4)
    c.d.ellipse([52 * S, 12 * S, 68 * S, 28 * S], fill=TRANSP)
    c.ell(60, 20, 8, 8, None, lw=4)
    c.arc([44, -2, 76, 30], 200, 340, (150, 154, 162, 255), 4)            # Ring
    c.glint(28, 18, 8, 3, 120)
    c.save("task_park_keytag.png")
    for k in range(10):
        c = C(80, 80)
        park_glyph(c, 40, 40, k, 1.2)
        c.save(f"task_park_glyph{k}.png")


# ------------------------------------------------------------------ Collect the Ride Photos (Auswahl + Stecken)

def park_photo():
    c = C(200, 150)                                                     # Fahrfoto mit leerem Wagen
    c.rrect(6, 6, 194, 144, 6, (244, 240, 230, 255), lw=5, sh=(0.03, 0.1))
    sky((c), 200, 150, (20, 20, 50), (70, 46, 90), 1.0, box=(16, 14, 184, 118, 3))
    rnd = random.Random(33)
    stars(c, rnd, 14, 18, 16, 182, 60, 200)
    for x in range(24, 184, 26):                                        # Gerippe
        c.line([(x, 70), (x, 118)], (70, 56, 100, 255), 3)
    c.line([(16, 72), (184, 64)], (90, 72, 120, 255), 4)
    c.glow(100, 70, 70, 36, (255, 250, 230, 60), 16)                    # Blitzlicht
    c.rrect(16, 106, 184, 118, 0, (40, 34, 50, 255), lw=0)               # Schiene
    c.poly([(30, 106), (166, 106), (176, 90), (22, 88)], RED, lw=4, sh=(0.2, 0.3))   # Wagen
    for x in (62, 108):
        c.rrect(x, 78, x + 30, 92, 5, RED_D, lw=3)                       # Sitzlehnen
    c.ell(170, 96, 6, 6, BULB, lw=2)
    c.rrect(16, 14, 184, 118, 3, None, lw=3)
    c.rrect(40, 124, 160, 136, 3, (226, 216, 200, 255), lw=0)
    c.line([(52, 130), (148, 130)], (190, 90, 90, 255), 3)
    c.save("task_park_photo.png")
    c = C(160, 130)                                                     # Fahrgast: Crewmate mit Buegel
    c.rrect(50, 30, 112, 118, 28, (70, 150, 220, 255), lw=6, sh=(0.14, 0.3))
    c.rrect(34, 58, 56, 104, 10, (52, 118, 186, 255), lw=5, sh=(0.1, 0.3))   # Rucksack
    c.rrect(76, 44, 126, 72, 14, (150, 214, 236, 255), lw=5, sh=(0.2, 0.3))  # Visier
    c.glint(96, 52, 14, 5, 200)
    for dx in (-1, 1):                                                  # Schreck-Striche
        c.line([(81 + dx * 34, 18), (81 + dx * 42, 6)], (250, 240, 200, 255), 4)
    c.line([(81, 14), (81, 2)], (250, 240, 200, 255), 4)
    c.rrect(24, 96, 140, 110, 6, (240, 200, 60, 255), lw=5, sh=(0.25, 0.3))  # Buegel
    c.save("task_park_rider.png")
    c = C(300, 240)                                                     # Fotokiosk (Kartenschlitz um y 196)
    c.rrect(10, 14, 290, 238, 16, (0, 0, 0, 90), lw=0)
    c.rrect(10, 10, 290, 234, 16, RED, lw=7, sh=(0.14, 0.26))
    c.rrect(22, 20, 278, 150, 8, GOLD, lw=4, sh=(0.2, 0.3))
    c.rrect(30, 28, 270, 142, 5, (30, 30, 60, 255), lw=4)
    for i in range(6):
        x, y = 44 + (i % 3) * 76, 36 + (i // 3) * 54
        c.rrect(x, y, x + 64, y + 46, 3, (236, 232, 222, 255), lw=2)
        c.rrect(x + 5, y + 4, x + 59, y + 36, 2, (50, 44, 80, 255), lw=0)
        c.poly([(x + 12, y + 34), (x + 52, y + 34), (x + 55, y + 26), (x + 9, y + 26)], RED_L, lw=0)
    c.glint(60, 40, 60, 10, 50, rot=10)
    c.rrect(22, 160, 278, 226, 8, RED_D, lw=4, sh=(0.1, 0.2))
    c.rrect(104, 190, 196, 204, 4, INK, lw=3)                            # Kartenschlitz
    c.ell(212, 197, 5, 5, (110, 220, 120, 255), lw=2)
    for x in (48, 74):
        c.ell(x, 196, 10, 10, GOLD, lw=4, sh=(0.25, 0.3))
    label(c, 150, 174, "RIDE PHOTOS", 13, CREAM)
    c.save("task_park_kiosk.png")


# ------------------------------------------------------------------ Shooting Gallery (Klickziele)

def park_booth():
    c = C(720, 520)
    frame_wood(c, (80, 36, 40, 255))
    sky(c, 720, 520, (22, 24, 58), (54, 38, 86), 1.0, box=(26, 26, 694, 494, 14))
    rnd = random.Random(44)
    for _ in range(18):                                                 # Pappsterne
        x, y = rnd.uniform(80, 640), rnd.uniform(90, 200)
        r = rnd.uniform(7, 13)
        c.poly(star_pts(x, y, r, r * 0.45, rot=rnd.uniform(-110, -70)), (236, 200, 90, 255), lw=3)
    mc = C(720, 520)                                                    # Pappmond: Sichel auf eigener Ebene
    mc.ell(600, 130, 36, 36, (240, 214, 120, 255), lw=4)
    mc.d.ellipse([(600 - 26) * S, (130 - 44) * S, (600 + 46) * S, (130 + 28) * S], fill=TRANSP)
    mc.arc([600 - 26, 130 - 44, 600 + 46, 130 + 28], 62, 221, INK, 4)  # Innenkante (Schnitt mit dem Mondkreis)
    c.img.alpha_composite(mc.img)
    c.d = ImageDraw.Draw(c.img)
    # Regalbrett zwischen Clown-Reihe und Enten-Reihe
    c.rrect(30, 214, 690, 232, 3, (120, 76, 48, 255), lw=4, sh=(0.25, 0.25))
    for x in range(70, 690, 90):
        c.rivet(x, 223, 3, BRASS_L)
    # Wellenbahn unten
    for i, (y, col) in enumerate(((388, (46, 92, 150, 255)), (424, (38, 76, 130, 255)), (458, (30, 60, 110, 255)))):
        pts = [(30, 494)] + [(x, y + 10 * math.sin(x / 26 + i * 1.7)) for x in range(30, 691, 6)] + [(690, 494)]
        c.poly(pts, col, lw=4)
        for x in range(40, 690, 52):
            c.line([(x + i * 17, y + 2 + 10 * math.sin((x + i * 17) / 26 + i * 1.7)), (x + 16 + i * 17, y + 10 * math.sin((x + 16 + i * 17) / 26 + i * 1.7))], (110, 160, 210, 255), 3)
    # Vorhaenge seitlich
    for x0, x1, sx in ((26, 70, 1), (650, 694, -1)):
        c.poly([(x0, 26), (x1, 26), (x1 - sx * 10, 300), (x1, 494), (x0, 494)], PLUM, lw=4, shx=(0.2, 0.3))
        for k in range(3):
            xx = x0 + (x1 - x0) * (k + 1) / 4
            c.line([(xx, 30), (xx - sx * 4, 490)], PLUM_D, 3)
    # Markise oben (Zaehler "0/12" steht weiss darauf: dunkle Streifen)
    for i, x in enumerate(range(26, 694, 40)):
        c.d.rectangle([x * S, 26 * S, min(x + 40, 694) * S, 70 * S], fill=RED if i % 2 == 0 else (120, 28, 38, 255))
    for x in range(26, 694, 40):
        c.ell(x + 20, 70, 20, 12, RED if (x - 26) // 40 % 2 == 0 else (120, 28, 38, 255), lw=4)
    c.line([(26, 70), (694, 70)], GOLD, 3)
    c.rrect(26, 26, 694, 494, 14, None, lw=4)
    c.vignette(0.3, 26, 26, 694, 494)
    marquee(c, 15, 15, 705, 505, 40, 5)
    c.save("task_park_booth.png")
    c = C(160, 130)                                                     # Blechente (schaut nach rechts)
    c.rrect(66, 96, 76, 130, 3, (120, 80, 50, 255), lw=3)
    c.poly([(26, 64), (8, 36), (40, 52)], (240, 196, 50, 255), lw=5, sh=(0.1, 0.25))
    c.ell(70, 70, 50, 30, (250, 208, 60, 255), lw=6, sh=(0.18, 0.3))
    c.poly([(48, 64), (86, 60), (74, 84)], (226, 176, 40, 255), lw=4)
    c.ell(116, 40, 22, 22, (250, 208, 60, 255), lw=6, sh=(0.18, 0.3))
    c.poly([(134, 36), (156, 42), (134, 50)], (240, 128, 40, 255), lw=4, sh=(0.2, 0.3))
    c.ell(122, 34, 4, 4, INK, lw=0)
    c.ell(64, 74, 13, 13, WHITE, lw=4)
    c.ell(64, 74, 6, 6, RED, lw=0)
    c.glint(58, 50, 16, 5, 120, rot=-10)
    c.save("task_park_duck.png")
    c = C(150, 100)                                                     # zweite Ente, blaugruen
    c.rrect(62, 78, 72, 100, 3, (120, 80, 50, 255), lw=3)
    c.poly([(24, 52), (8, 28), (36, 42)], TEAL_D, lw=5)
    c.ell(64, 56, 44, 24, TEAL, lw=6, sh=(0.18, 0.3))
    c.ell(106, 32, 18, 18, TEAL, lw=6, sh=(0.18, 0.3))
    c.poly([(120, 28), (144, 34), (120, 40)], (240, 128, 40, 255), lw=4)
    c.ell(110, 27, 3.5, 3.5, INK, lw=0)
    c.poly(star_pts(60, 58, 11, 4.5), CREAM, lw=3)
    c.save("task_park_duck2.png")
    c = C(100, 120)                                                     # Clown-Pappkopf (nicht treffen)
    c.rrect(46, 96, 54, 120, 3, (120, 80, 50, 255), lw=3)
    for dx in (-1, 1):
        for k in range(3):
            c.ell(50 + dx * (34 + k * 2), 50 + k * 14, 10, 9, (240, 110, 40, 255), lw=4)
    c.ell(50, 58, 32, 38, (250, 244, 234, 255), lw=6, sh=(0.08, 0.2))
    c.poly([(30, 30), (50, -2), (70, 30)], PLUM, lw=4, sh=(0.2, 0.3))
    c.ell(50, 0, 6, 6, GOLD, lw=3)
    for x in (38, 62):
        c.poly([(x, 38), (x + 6, 46), (x, 54), (x - 6, 46)], (80, 110, 200, 255), lw=2)
        c.ell(x, 46, 3, 3, INK, lw=0)
    c.arc([30, 56, 70, 88], 20, 160, (200, 40, 50, 255), 5)
    c.ell(50, 62, 8, 8, (220, 40, 40, 255), lw=3, sh=(0.3, 0.3))
    c.glint(47, 58, 3, 2, 200)
    c.save("task_park_clown.png")


# ------------------------------------------------------------------ Clear the Popcorn Bins (Sortieren + Hebel)

def park_bins():
    for key, col in (("food", (226, 120, 42, 255)), ("recycle", TEAL)):
        dk = dark(col, 0.78)
        c = C(170, 200)
        c.poly([(20, 50), (150, 50), (138, 194), (32, 194)], col, lw=6, sh=(0.14, 0.26))
        for x in (52, 85, 118):
            c.d.line([(x * S, 72 * S), (x * S, 176 * S)], fill=dk, width=4 * S)
        c.d.line([(30 * S, 66 * S), (140 * S, 66 * S)], fill=light(col, 0.25), width=3 * S)
        c.rrect(10, 30, 160, 56, 8, dk, lw=6, sh=(0.25, 0.2))
        c.rrect(60, 22, 110, 34, 4, dk, lw=4, sh=(0.3, 0.2))
        c.glint(36, 40, 14, 3, 90)
        if key == "recycle":                                            # Kreislaufpfeile
            for k in range(3):
                a = math.radians(k * 120 - 90)
                x, y = 85 + math.cos(a) * 20, 130 + math.sin(a) * 20
                c.arc([67, 146, 103, 182], k * 120 - 70, k * 120 + 10, CREAM, 5)
                b = math.radians(k * 120 + 10)
                tx, ty = 85 + math.cos(b) * 18, 164 + math.sin(b) * 18
                c.poly([(tx - 6, ty - 6), (tx + 6, ty - 2), (tx - 2, ty + 7)], CREAM, lw=0)
        else:                                                           # Gabel und Messer
            c.line([(74, 162), (74, 184)], CREAM, 6)                     # Gabel (unter der Beschriftung)
            c.line([(67, 162), (81, 162)], CREAM, 4)
            for dx in (-6, 0, 6):
                c.line([(74 + dx, 146), (74 + dx, 162)], CREAM, 3)
            c.poly([(92, 146), (102, 150), (100, 168), (96, 168), (96, 184), (92, 184)], CREAM, lw=0)   # Messer
        c.save(f"task_bin_{key}.png")


def park_trash():
    def item(name, fn):
        c = C(96, 96)
        fn(c)
        c.save(f"task_trash_{name}.png")

    def popcorn(c):
        for x, y in ((36, 26), (50, 20), (62, 28), (44, 34), (56, 36), (30, 36), (66, 38)):
            c.ell(x, y, 9, 8, (252, 244, 214, 255), lw=3, sh=(0.05, 0.2))
        c.poly([(24, 38), (72, 38), (64, 88), (32, 88)], WHITE, lw=5)
        for x0 in (30, 50):
            c.poly([(x0, 38), (x0 + 10, 38), (x0 + 7, 88), (x0 + 1, 88)], RED, lw=0)
        c.poly([(24, 38), (72, 38), (64, 88), (32, 88)], None, lw=5)

    def candy(c):
        c.line([(48, 60), (48, 92)], (230, 210, 170, 255), 5)
        for x, y, r in ((36, 36, 18), (58, 32, 18), (48, 20, 16), (48, 46, 16)):
            c.ell(x, y, r, r * 0.9, (246, 160, 206, 255), lw=4, sh=(0.1, 0.2))
        c.glint(40, 22, 8, 4, 130)

    def hotdog(c):
        c.capsule((16, 52), (80, 44), 22, (224, 170, 100, 255), 4, sh=(0.15, 0.25))
        c.capsule((12, 46), (84, 38), 12, (196, 80, 60, 255), 4, sh=(0.2, 0.3))
        c.line([(20, 42), (28, 38), (36, 44), (44, 38), (52, 42), (60, 36), (68, 40), (76, 36)], (250, 210, 60, 255), 3)

    def cup(c):
        c.poly([(26, 26), (70, 26), (64, 90), (32, 90)], WHITE, lw=5, sh=(0.05, 0.18))
        c.poly([(30, 44), (66, 44), (64, 62), (32, 62)], RED, lw=0)
        c.poly([(26, 26), (70, 26), (64, 90), (32, 90)], None, lw=5)
        c.rrect(22, 18, 74, 28, 4, (220, 220, 226, 255), lw=4)
        c.line([(52, 20), (62, 4)], (60, 150, 220, 255), 5)

    for n, f in (("popcorn", popcorn), ("candy", candy), ("hotdog", hotdog), ("cup", cup)):
        item(n, f)


def park_container():
    c = C(360, 300)                                                     # Popcorn-Container (Kontrakt wie task_container)
    c.rrect(20, 60, 300, 290, 12, RED, lw=7, sh=(0.14, 0.24))
    for x in range(50, 290, 44):
        c.d.rectangle([x * S, 66 * S, (x + 22) * S, 284 * S], fill=(244, 234, 214, 255))
    m, md = c.mask()
    md.rounded_rectangle([24 * S, 64 * S, 296 * S, 286 * S], 10 * S, fill=255)
    c.shade(m, 0.1, 0.25)
    c.rrect(20, 60, 300, 290, 12, None, lw=7)
    for x, y in ((60, 28), (90, 22), (120, 30), (220, 26), (250, 32), (160, 20), (190, 28)):
        c.ell(x, y, 12, 10, (252, 244, 214, 255), lw=4, sh=(0.05, 0.2))
    c.rrect(10, 40, 310, 76, 8, RED_D, lw=7, sh=(0.25, 0.2))
    for x in range(40, 300, 40):
        c.rivet(x, 58, 4, BRASS_L)
    c.rrect(110, 130, 210, 192, 10, GOLD, lw=5, sh=(0.2, 0.3))
    label(c, 160, 161, "POP", 30, RED_D)
    c.save("task_park_container.png")


# ------------------------------------------------------------------ Refuel / Tune / Pump

def park_tank():
    c = C(360, 400)                                                     # Tank (Kontrakt wie task_boiler: Einfuellstutzen oben Mitte)
    c.rrect(40, 60, 320, 390, 40, RED, lw=8, shx=(0.24, 0.3))
    for y in (140, 280):
        c.rrect(34, y, 326, y + 18, 6, GOLD, lw=4, sh=(0.25, 0.25))
        for x in range(60, 320, 40):
            c.rivet(x, y + 9, 4, BRASS_L)
    c.ell(180, 60, 140, 28, RED_L, lw=7, sh=(0.3, 0.2))
    c.rrect(160, 16, 200, 58, 6, (150, 156, 168, 255), lw=5, shx=(0.3, 0.3))
    c.rrect(152, 10, 208, 24, 5, (70, 74, 84, 255), lw=4)
    c.rrect(110, 176, 250, 250, 8, CREAM, lw=5, sh=(0.05, 0.15))
    label(c, 180, 213, "FUEL", 30, RED_D)
    c.ell(270, 330, 30, 30, (88, 94, 104, 255), lw=6, sh=(0.25, 0.3))
    c.ell(270, 330, 20, 20, CREAM, lw=3)
    c.line([(270, 330), (280, 318)], (206, 42, 42, 255), 3)
    c.save("task_park_tank.png")


def park_wheels():
    c = C(300, 300)                                                     # Karussellantrieb: Zahnrad mit Lichtern
    teeth = []
    for k in range(40):
        a = math.radians(k * 9)
        r = 142 if k % 2 == 0 else 126
        teeth.append((150 + math.cos(a) * r, 150 + math.sin(a) * r))
    c.ell(150, 154, 140, 140, (0, 0, 0, 90), lw=0)
    c.poly(teeth, RED, lw=6, sh=(0.18, 0.3))
    c.ell(150, 150, 112, 112, GOLD, lw=5, sh=(0.2, 0.3))
    c.ell(150, 150, 98, 98, RED_D, lw=4)
    for k in range(6):
        a = math.radians(k * 60)
        c.capsule((150 + math.cos(a) * 30, 150 + math.sin(a) * 30), (150 + math.cos(a) * 94, 150 + math.sin(a) * 94), 12, CREAM, 4, sh=(0.1, 0.25))
    for k in range(12):
        a = math.radians(k * 30 + 15)
        bulb(c, 150 + math.cos(a) * 105, 150 + math.sin(a) * 105, 5)
    c.ell(150, 150, 30, 30, BRASS, lw=6, sh=(0.25, 0.3))
    c.poly(star_pts(150, 150, 16, 7), BRASS_D, lw=0)
    c.save("task_park_gear.png")
    c = C(300, 300)                                                     # Autoscooter-Rad
    c.ell(150, 154, 142, 142, (0, 0, 0, 90), lw=0)
    c.ell(150, 150, 140, 140, (44, 44, 50, 255), lw=7, sh=(0.12, 0.25))
    for k in range(24):
        a = math.radians(k * 15)
        c.line([(150 + math.cos(a) * 110, 150 + math.sin(a) * 110), (150 + math.cos(a) * 134, 150 + math.sin(a) * 134)], (28, 28, 32, 255), 7)
    c.ell(150, 150, 96, 96, (196, 202, 212, 255), lw=6, sh=(0.25, 0.3))
    c.ell(150, 150, 70, 70, TEAL, lw=5, sh=(0.2, 0.3))
    for k in range(5):
        a = math.radians(k * 72 - 90)
        c.capsule((150, 150), (150 + math.cos(a) * 62, 150 + math.sin(a) * 62), 14, CREAM, 4)
    c.ell(150, 150, 22, 22, (196, 202, 212, 255), lw=5, sh=(0.25, 0.3))
    c.ell(150, 150, 7, 7, INK, lw=0)
    c.glint(104, 96, 26, 10, 110, rot=35)
    c.save("task_park_bumper.png")


def park_pump():
    c = C(260, 420)                                                     # Hydraulikpumpe (Kontrakt wie task_pump_body)
    c.rrect(40, 356, 220, 412, 8, (70, 62, 84, 255), lw=6, sh=(0.14, 0.22))
    c.line([(46, 362), (214, 362)], (120, 108, 136, 255), 3)
    c.rrect(84, 90, 176, 362, 20, RED, lw=7, shx=(0.22, 0.3))
    c.poly([(176, 170), (246, 184), (246, 206), (176, 214)], RED, lw=6, sh=(0.2, 0.3))
    c.ell(246, 195, 8, 12, RED_D, lw=5, sh=(0.1, 0.2))
    c.rrect(66, 58, 194, 100, 14, RED_D, lw=7, shx=(0.25, 0.25))
    c.ell(130, 58, 22, 14, GOLD, lw=6, sh=(0.3, 0.2))
    c.ell(130, 48, 8, 8, BRASS_L, lw=4, sh=(0.3, 0.3))
    for y in (130, 250, 330):
        c.rrect(78, y, 182, y + 14, 6, GOLD, lw=5, shx=(0.25, 0.25))
        for x in (96, 130, 164):
            c.rivet(x, y + 7, 3, BRASS_L)
    c.rrect(100, 170, 160, 226, 6, CREAM, lw=4)
    label(c, 130, 198, "HYD", 18, RED_D)
    c.save("task_park_pump.png")
    c = C(140, 180)                                                     # Hydraulikoel (Kontrakt wie task_water)
    oil, lt = (214, 150, 40, 232), (252, 216, 130, 255)
    c.poly([(10, 20), (50, 12), (74, 60), (86, 170), (48, 174), (40, 70)], oil, lw=5, sh=(0.1, 0.15))
    c.line([(30, 24), (52, 64), (62, 150)], lt, 5)
    for x, y, r in ((100, 150, 9), (116, 120, 6), (24, 150, 7), (110, 90, 5)):
        c.ell(x, y, r, r, oil, lw=3)
        c.glint(x - r * 0.3, y - r * 0.3, r * 0.4, r * 0.3, 150)
    c.save("task_park_oil.png")


# ------------------------------------------------------------------ Welt-Effekte der Visual Tasks (AtlasWorldFx)

def park_fx():
    c = C(120, 120)                                                     # Treffer-Stern
    c.poly(star_pts(60, 60, 54, 26, n=8, rot=-90), (255, 220, 80, 255), lw=5, sh=(0.15, 0.25))
    c.poly(star_pts(60, 60, 30, 16, n=8, rot=-67.5), (255, 250, 220, 255), lw=0)
    label(c, 60, 61, "POP", 20, RED_D)
    c.save("task_park_pop.png")
    c = C(140, 140)                                                     # Popcornwolke
    rnd = random.Random(6)
    for _ in range(12):
        x, y = rnd.uniform(24, 116), rnd.uniform(24, 116)
        c.ell(x, y, 12, 10, (252, 244, 214, 255), lw=3, sh=(0.05, 0.2))
    c.save("task_park_puff.png")
    w, h = 140, 260                                                     # Scheinwerferkegel (Fuss unten Mitte)
    img = Image.new("RGBA", (w * S, h * S), TRANSP)
    ImageDraw.Draw(img).polygon([(62 * S, 256 * S), (78 * S, 256 * S), (136 * S, 4 * S), (4 * S, 4 * S)], fill=(255, 246, 210, 255))
    img = img.filter(ImageFilter.GaussianBlur(5 * S))
    a = np.asarray(img, dtype=np.float32)
    t = (np.arange(h * S) / (h * S))[:, None]
    a[..., 3] *= (0.25 + 0.75 * t)                                      # oben blasser
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA").resize((w, h), Image.LANCZOS)
    img.save(OUT / "task_park_beam.png")
    print(OUT / "task_park_beam.png", img.size)


# ------------------------------------------------------------------ Sabotagen (AtlasMechanicsSabotage)

def park_sabotage():
    # Coaster Brake Failure: Bremspult (Kontrakt wie task_scanner, 300 x 340), die Bremsbacke wandert darueber
    c = C(300, 340)
    c.rrect(10, 10, 290, 330, 26, RED_D, lw=7, sh=(0.18, 0.28))
    c.rrect(34, 34, 266, 306, 16, (28, 26, 44, 255), lw=5)
    m, md = c.mask()
    md.rounded_rectangle([36 * S, 36 * S, 264 * S, 304 * S], 16 * S, fill=255)
    for y in range(44, 300, 22):                                        # Schwellen
        c.rrect(70, y, 230, y + 10, 2, (70, 52, 44, 255), lw=0)
    for x in (100, 200):                                                # Schienen
        c.rrect(x - 6, 36, x + 6, 304, 3, (150, 156, 168, 255), lw=3, shx=(0.3, 0.3))
    c.glow(150, 170, 110, 120, (255, 120, 90, 50), 18)
    for y in (70, 150, 230):                                            # Warnwinkel
        c.poly([(128, y), (150, y + 18), (172, y), (172, y + 12), (150, y + 30), (128, y + 12)], (240, 200, 60, 200), lw=0)
    for x, y in ((24, 24), (276, 24), (24, 316), (276, 316)):
        c.screw(x, y, 7, BRASS_L)
    c.glint(90, 60, 50, 12, 60, rot=-10)
    c.save("task_park_brakepad.png")
    c = C(60, 60)                                                       # Bremsbacke (Kontrakt wie task_marker)
    c.ell(30, 32, 22, 22, (0, 0, 0, 90), lw=0)
    c.ell(30, 30, 22, 22, (236, 128, 44, 255), lw=5, sh=(0.25, 0.3))
    for dx in (-8, 0, 8):
        c.line([(30 + dx, 18), (30 + dx, 42)], (170, 80, 30, 255), 3)
    c.ell(30, 30, 22, 22, None, lw=5)
    c.glint(23, 21, 6, 3, 150, rot=35)
    c.save("task_park_brakeknob.png")
    # Park Blackout: Gluehbirnen statt Sicherungen (Kontrakt wie task_fuse_*: 64 x 100)
    for name, glass, fil, glow in (("task_park_bulb_ok.png", (255, 226, 130, 255), (255, 250, 220, 255), True),
                                   ("task_park_bulb_dead.png", (74, 70, 70, 255), (40, 36, 36, 255), False),
                                   ("task_park_bulb_new.png", (214, 236, 246, 255), (150, 150, 150, 255), False)):
        c = C(64, 100)
        if glow:
            c.glow(32, 38, 30, 34, (255, 214, 120, 150), 8)
        c.ell(32, 38, 24, 28, glass, lw=5, sh=(0.1, 0.25))
        c.rrect(21, 58, 43, 70, 3, glass, lw=0)
        if "dead" in name:
            c.line([(24, 50), (30, 36), (34, 44)], fil, 3)
            c.line([(38, 34), (42, 48)], fil, 3)
            c.ell(24, 26, 6, 4, (40, 36, 36, 255), lw=0)                  # Russfleck
        else:
            c.line([(26, 56), (26, 40), (30, 34), (34, 40), (38, 34), (38, 56)], fil, 3)
        c.rrect(20, 66, 44, 94, 4, BRASS, lw=4, sh=(0.25, 0.3))
        for y in (74, 82):
            c.line([(21, y), (43, y + 3)], BRASS_D, 2)
        c.rrect(26, 92, 38, 98, 2, INK, lw=0)
        c.glint(24, 28, 4, 9, 170 if not "dead" in name else 60)
        c.save(name)
    # Speaker Feedback: Trichterlautsprecher (Kontrakt wie task_dish: 280 x 280, dreht um die Mitte)
    c = C(280, 280)
    c.rrect(126, 150, 154, 270, 6, STEEL_D, lw=5, shx=(0.2, 0.3))
    c.rrect(108, 128, 172, 162, 8, (70, 74, 84, 255), lw=5, sh=(0.25, 0.3))
    ax, ay = 110 / 127.3, -64 / 127.3                                   # Trichterachse, schraeg nach oben
    px, py = -ay, ax

    def rim(cx, cy, a, b):                                              # gedrehte Ellipse der Trichteroeffnung
        return [(cx + px * a * math.cos(t) + ax * b * math.sin(t), cy + py * a * math.cos(t) + ay * b * math.sin(t))
                for t in [k * math.pi / 18 for k in range(36)]]
    c.poly([(130 - px * 10, 150 - py * 10), (240 - px * 46, 86 - py * 46), (240 + px * 46, 86 + py * 46), (130 + px * 10, 150 + py * 10)],
           (224, 228, 234, 255), lw=6, sh=(0.2, 0.35))                   # Trichter weitet sich
    c.poly(rim(240, 86, 46, 14), (60, 62, 70, 255), lw=5)
    c.poly(rim(242, 85, 30, 8), (30, 30, 36, 255), lw=0)
    c.rrect(70, 136, 124, 166, 6, RED, lw=5, sh=(0.25, 0.3))                 # Treiber
    c.line([(40, 150), (66, 150)], INK, 5)
    for k in range(3):                                                  # Schallbogen
        c.arc([232 - 20 - k * 16, 60 - k * 16, 272 + k * 16, 120 + k * 16], -60, 20, (240, 214, 120, 255), 4)
    c.save("task_park_speaker.png")


# ------------------------------------------------------------------ Fahrzeuge des Welt-Systems (AtlasParkWorld)
# Reine Draufsicht, Fahrtrichtung +x (der Code dreht entlang des Weges), 100 px = 1 m.

def park_rides():
    c = C(360, 116)                                                     # Achterbahnzug: drei Wagen (3,6 x 1,15 m)
    for k in range(3):
        x0 = 6 + k * 118
        c.rrect(x0 + 4, 12, x0 + 110, 108, 18, (0, 0, 0, 90), lw=0)
        c.rrect(x0, 8, x0 + 106, 104, 18, RED, lw=5, sh=(0.2, 0.3))
        for sx in (x0 + 18, x0 + 58):                                   # Sitzreihen
            c.rrect(sx, 22, sx + 32, 90, 8, (70, 26, 34, 255), lw=3)
            c.rrect(sx + 4, 26, sx + 28, 86, 6, CREAM, lw=0)
            c.line([(sx + 30, 24), (sx + 30, 88)], GOLD, 4)               # Buegel
        c.line([(x0 + 8, 12), (x0 + 98, 12)], GOLD, 3)
        c.line([(x0 + 8, 100), (x0 + 98, 100)], GOLD, 3)
        if k < 2:
            c.rrect(x0 + 104, 50, x0 + 120, 62, 3, (60, 60, 70, 255), lw=2)
    c.ell(348, 58, 8, 14, BULB, lw=3)
    c.glow(356, 58, 20, 20, (255, 230, 150, 120), 6)
    c.save("task_park_train.png")
    c = C(220, 100)                                                     # Baumstammboot (2,2 x 1,0 m)
    c.ell(112, 54, 104, 44, (0, 0, 0, 80), lw=0)
    c.poly([(8, 50), (30, 12), (180, 10), (214, 50), (180, 90), (30, 88)], (150, 100, 58, 255), lw=6, sh=(0.2, 0.3))
    c.grain(20, 12, 200, 88, 0.12, seed=5)
    c.poly([(40, 50), (54, 26), (166, 24), (188, 50), (166, 76), (54, 74)], (96, 64, 36, 255), lw=4)
    for x in (80, 130):
        c.rrect(x - 8, 30, x + 8, 70, 3, (130, 88, 52, 255), lw=3)
    c.ell(204, 50, 8, 18, (196, 150, 96, 255), lw=3)
    c.save("task_park_boat.png")
    c = C(130, 66)                                                      # Geisterbahnwagen (1,3 x 0,66 m)
    c.rrect(6, 6, 118, 60, 14, (70, 44, 100, 255), lw=5, sh=(0.2, 0.3))
    c.rrect(20, 16, 70, 50, 8, (40, 26, 56, 255), lw=3)
    c.ell(100, 33, 18, 20, (236, 230, 210, 255), lw=4)                   # Totenkopf vorn
    for y in (26, 40):
        c.ell(104, y, 4, 4, INK, lw=0)
    c.glow(108, 33, 20, 20, (140, 255, 140, 70), 6)
    c.save("task_park_ghostcar.png")


if __name__ == "__main__":
    park_rides()
    park_sabotage()
    park_panel(); park_machine()
    park_candy(); park_sugar()
    park_parademap(); park_spotlight(); park_panorama(); park_keys(); park_photo(); park_booth()
    park_bins(); park_trash(); park_container(); park_tank(); park_wheels(); park_pump(); park_fx()
