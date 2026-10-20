# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_fx.py - Effekt- und Minispielgrafik der Zug-Sabotagen "Runaway Train" (AtlasRunaway, ersetzt den Reaktor)
# und "Smoke in the Cars" (AtlasSmoke, ersetzt O2), geliefert ueber das "files"-Dict von train_art.build.
#
# Effekte (Welt, mit Alpha): train_fx_spark.png (vier Funkenbuendel je 128 x 128 in einer Zeile),
#   train_fx_speed.png (weiche weisse Bewegungsstriche 512 x 128), train_fx_fire.png (Feuerschein 256 x 256),
#   train_fx_smoke.png (vier Rauchwolken je 256 x 256 in einer Zeile).
# Minispiele (100 px/m, Stil wie gen_tasks.py: flache Toene, Glanz, dunkle Kontur):
#   task_train_brake.png (Bremsstand 2,4 m mit senkrechtem Schlitz, ohne Hebel), task_train_brake_lever.png (Hebel,
#   Drehpunkt an der Unterkante, 1,2 m), task_train_gauge.png (Geschwindigkeitsanzeige 1,6 m, 0..120, gruen 20..40),
#   task_train_gauge_needle.png (Zeiger, Drehpunkt an der Unterkante), task_train_wheel.png (Handbremsrad von oben
#   2,2 m, Mitte = Bildmitte), task_train_hatch.png / task_train_hatch_open.png (Dachluke von unten, Kurbelachse in
#   der Bildmitte), task_train_crank.png (Kurbel, Drehpunkt in der Bildmitte, 0,9 m), dazu die Kartenknoepfe
#   task_train_runaway_button.png und task_train_smoke_button.png (256 x 256, Vanilla-Look).
# preview_sheet() legt alles als Uebersicht tools/_train/preview_fx.png ab.

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gen_tasks import C, S, INK, BRASS, BRASS_L, BRASS_D, STEEL, STEEL_L, STEEL_D, CREAM, WHITE, mix, dark, light
from train_style import font

IRON = (58, 60, 68, 255)
IRON_L = (96, 100, 110, 255)
RED = (200, 56, 48, 255)
RED_L = (236, 96, 84, 255)
GREEN = (90, 200, 110, 255)
NIGHT = (24, 30, 60, 255)
WOOD = (150, 100, 58, 255)
TRANSP = (0, 0, 0, 0)


def _text(c, x, y, s, px, fill=INK, kind="black", anchor="mm"):
    c.d.text((x * S, y * S), s, font=font(px * S, kind), fill=fill, anchor=anchor)


# ------------------------------------------------------------------ Effekte (Welt)

def fx_spark():
    """Vier Funkenbuendel je 128 x 128: Strahlen vom Fusspunkt unten, weisser Kern, orange Schweife, Glut."""
    ss = 2
    out = Image.new("RGBA", (512 * ss, 128 * ss), TRANSP)
    for k in range(4):
        rnd = random.Random(11 + k)
        cell = Image.new("RGBA", (128 * ss, 128 * ss), TRANSP)
        glow = Image.new("RGBA", cell.size, TRANSP)
        gd = ImageDraw.Draw(glow)
        d = ImageDraw.Draw(cell)
        ox, oy = 64 * ss, 112 * ss
        spread = (-150, -30) if k % 2 == 0 else (-170, -10)
        n = 11 + k * 2
        for i in range(n):
            a = math.radians(rnd.uniform(*spread))
            ln = rnd.uniform(36, 100) * ss
            ex, ey = ox + ln * math.cos(a), oy + ln * math.sin(a)
            w = rnd.uniform(2.5, 5) * ss
            gd.line([(ox, oy), (ex, ey)], fill=(255, 150, 40, 110), width=int(w * 3))
            d.line([(ox, oy), (ex, ey)], fill=(255, 140, 40, 230), width=int(w))
            d.line([(ox + (ex - ox) * 0.35, oy + (ey - oy) * 0.35), (ex, ey)], fill=(255, 230, 170, 255), width=max(1, int(w * 0.55)))
            r = rnd.uniform(2, 4) * ss
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(255, 250, 220, 255))
            for _ in range(2):                                                    # Glut, die abfaellt
                t = rnd.uniform(0.5, 1.15)
                px, py = ox + (ex - ox) * t + rnd.uniform(-6, 6) * ss, oy + (ey - oy) * t + rnd.uniform(0, 14) * ss
                rr = rnd.uniform(1, 2.5) * ss
                d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(255, 190, 90, 220))
        gd.ellipse([ox - 22 * ss, oy - 14 * ss, ox + 22 * ss, oy + 10 * ss], fill=(255, 200, 90, 160))
        glow = glow.filter(ImageFilter.GaussianBlur(5 * ss))
        glow.alpha_composite(cell)
        out.alpha_composite(glow, (k * 128 * ss, 0))
    return out.resize((512, 128), Image.LANCZOS)


def fx_speed():
    """Bewegungsstriche 512 x 128: weiche weisse Linien verschiedener Laenge, Enden ausgeblendet."""
    ss = 2
    img = Image.new("RGBA", (512 * ss, 128 * ss), TRANSP)
    d = ImageDraw.Draw(img)
    rnd = random.Random(5)
    ys = [10, 24, 36, 50, 62, 74, 88, 102, 116]
    for y in ys:
        x0 = rnd.uniform(0, 160)
        ln = rnd.uniform(140, 380)
        w = rnd.uniform(2, 5)
        a = rnd.randint(150, 230)
        d.line([(x0 * ss, y * ss), ((x0 + ln) * ss, y * ss)], fill=(255, 255, 255, a), width=int(w * ss))
        d.line([((x0 + ln * 0.75) * ss, y * ss), ((x0 + ln) * ss, y * ss)], fill=(255, 255, 255, 255), width=int(w * ss * 0.6))
    img = img.filter(ImageFilter.GaussianBlur(1.2 * ss))
    # Enden weich: Alpha mit waagerechtem Verlauf an beiden Seiten multiplizieren
    a = np.asarray(img.getchannel("A")).astype(np.float32)
    x = np.arange(img.width) / img.width
    ramp = np.clip(x / 0.12, 0, 1) * np.clip((1 - x) / 0.08, 0, 1)
    img.putalpha(Image.fromarray(np.clip(a * ramp[None, :], 0, 255).astype(np.uint8), "L"))
    return img.resize((512, 128), Image.LANCZOS)


def fx_fire():
    """Feuerschein 256 x 256: orange-gelber Schein mit weichem Rand und zwei Flammenzungen."""
    n = 256
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx, cy = n / 2, n * 0.56
    r = np.sqrt(((xx - cx) / (n * 0.46)) ** 2 + ((yy - cy) / (n * 0.42)) ** 2)
    fall = np.clip(1 - r, 0, 1) ** 1.7
    rgb = np.zeros((n, n, 3), np.float32)
    rgb[..., 0] = 255
    rgb[..., 1] = 120 + 130 * fall
    rgb[..., 2] = 30 + 170 * fall ** 2.2
    img = Image.fromarray(np.concatenate([rgb, (fall * 255)[..., None]], axis=2).astype(np.uint8), "RGBA")
    flame = Image.new("RGBA", (n * 2, n * 2), TRANSP)
    fd = ImageDraw.Draw(flame)
    for (fx, fy, fw, fh, col) in ((0.5, 0.55, 0.22, 0.42, (255, 170, 60, 200)), (0.42, 0.6, 0.12, 0.3, (255, 220, 120, 210)),
                                  (0.6, 0.62, 0.11, 0.26, (255, 210, 110, 200))):
        pts = [(fx * n * 2 - fw * n * 2, (fy + fh) * n * 2), (fx * n * 2 - fw * n * 1.2, fy * n * 2 + fh * n * 0.4),
               (fx * n * 2, (fy - fh) * n * 2), (fx * n * 2 + fw * n * 1.3, fy * n * 2 + fh * n * 0.5), (fx * n * 2 + fw * n * 2, (fy + fh) * n * 2)]
        fd.polygon(pts, fill=col)
    flame = flame.filter(ImageFilter.GaussianBlur(14)).resize((n, n), Image.LANCZOS)
    img.alpha_composite(flame)
    return img


def fx_smoke():
    """Vier Rauchwolken je 256 x 256: Haufen aus Kreisen, grau, oben heller, weicher Rand, verschiedene Formen."""
    ss = 2
    n = 256
    out = Image.new("RGBA", (n * 4, n), TRANSP)
    shapes = [[(0.5, 0.55, 0.3), (0.3, 0.62, 0.22), (0.7, 0.6, 0.24), (0.42, 0.4, 0.2), (0.6, 0.42, 0.18)],
              [(0.45, 0.6, 0.27), (0.68, 0.55, 0.25), (0.28, 0.58, 0.2), (0.55, 0.38, 0.22), (0.78, 0.4, 0.14), (0.35, 0.42, 0.14)],
              [(0.5, 0.5, 0.34), (0.26, 0.6, 0.18), (0.74, 0.62, 0.18), (0.5, 0.3, 0.16)],
              [(0.4, 0.62, 0.26), (0.62, 0.6, 0.26), (0.5, 0.42, 0.24), (0.3, 0.45, 0.16), (0.72, 0.4, 0.17), (0.5, 0.26, 0.12)]]
    for k, blobs in enumerate(shapes):
        m = Image.new("L", (n * ss, n * ss), 0)
        md = ImageDraw.Draw(m)
        for bx, by, br in blobs:
            md.ellipse([(bx - br) * n * ss, (by - br) * n * ss, (bx + br) * n * ss, (by + br) * n * ss], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(9 * ss))
        a = np.asarray(m).astype(np.float32) / 255
        a = np.clip((a - 0.25) / 0.6, 0, 1)                                     # weicher, aber definierter Rand
        yy = (np.arange(n * ss) / (n * ss))[:, None]
        shade = 1.0 - 0.35 * yy                                                   # oben heller
        rgb = np.zeros((n * ss, n * ss, 3), np.float32)
        base = np.array((176, 178, 188), np.float32)
        rgb[...] = base * shade[..., None] + 30 * (1 - a[..., None]) * 0.0
        cloud = Image.fromarray(np.concatenate([np.clip(rgb, 0, 255), (a * 235)[..., None]], axis=2).astype(np.uint8), "RGBA")
        # dunklere Unterseite: zweite, versetzte Maske
        m2 = m.transform(m.size, Image.AFFINE, (1, 0, 0, 0, 1, -10 * ss))
        a2 = np.clip((np.asarray(m2).astype(np.float32) / 255 - 0.25) / 0.6, 0, 1)
        under = np.clip(a - a2, 0, 1) * 0.5
        arr = np.asarray(cloud).astype(np.float32)
        arr[..., :3] *= (1 - under)[..., None]
        cloud = Image.fromarray(arr.astype(np.uint8), "RGBA").resize((n, n), Image.LANCZOS)
        out.alpha_composite(cloud, (k * n, 0))
    return out


# ------------------------------------------------------------------ Minispiel: Runaway Train

def task_brake():
    """Bremsstand 2,4 m breit (240 x 300): Gusseisen, senkrechter Schlitz mit Messingkanten, Rasten, Skala, Schild.
    Der Hebel (task_train_brake_lever) dreht um den Nabenpunkt unten am Schlitz (120, 212)."""
    c = C(240, 300)
    c.rrect(16, 282, 224, 298, 6, IRON, lw=5, sh=(0.1, 0.25))                   # Fussplatte
    c.rrect(40, 40, 200, 290, 14, IRON_L, lw=6, sh=(0.14, 0.22))                  # Korpus
    c.rrect(52, 52, 188, 278, 10, IRON, lw=4, sh=(0.1, 0.18))
    for y in (62, 268):
        for x in (64, 120, 176):
            c.rivet(x, y, 4, STEEL_L)
    c.rrect(108, 56, 132, 216, 6, (22, 20, 26, 255), lw=4)                       # Schlitz
    c.rrect(100, 50, 140, 222, 8, None, lw=4, outline=BRASS_D)
    c.line([(104, 54), (104, 218)], BRASS_L, 2)
    for i in range(8):                                                             # Rasten links, Skala rechts
        y = 70 + i * 20
        c.line([(84, y), (100, y)], BRASS, 4)
        c.line([(140, y), (156, y)], BRASS, 3 if i % 2 else 5)
    _text(c, 72, 60, "OFF", 11, BRASS_L)
    _text(c, 72, 214, "FULL", 11, RED_L)
    c.ell(120, 212, 16, 16, BRASS, lw=4, sh=(0.3, 0.3))                            # Nabe (Drehpunkt des Hebels)
    c.ell(120, 212, 6, 6, INK, lw=0)
    c.rrect(66, 234, 174, 258, 5, BRASS, lw=4, sh=(0.25, 0.3))
    _text(c, 120, 246, "STEAM BRAKE", 9, dark(INK, 1.0))
    c.ell(170, 246, 7, 7, RED, lw=3, sh=(0.3, 0.3))                                 # Kontrolllampe
    c.glint(168, 244, 2.5, 1.8, 170)
    c.vignette(0.18, 40, 40, 200, 290)
    return c.img.resize((240, 300), Image.LANCZOS)


def task_brake_lever():
    """Bremshebel 1,2 m (64 x 120): Stange aus Stahl mit Messingband, roter Griff oben; Drehpunkt an der Unterkante
    (32, 120)."""
    c = C(64, 120)
    c.capsule((32, 118), (32, 34), 12, STEEL, lw=4, sh=(0.2, 0.3))
    c.line([(29, 112), (29, 40)], STEEL_L, 2)
    c.rrect(24, 60, 40, 72, 3, BRASS, lw=3, sh=(0.3, 0.3))
    c.capsule((32, 36), (32, 10), 18, RED, lw=4, sh=(0.22, 0.3))
    c.glint(28, 18, 3, 7, 140)
    return c.img.resize((64, 120), Image.LANCZOS)


def _dial(c, cx, cy, r, ticks=True):
    c.ell(cx, cy, r, r, BRASS, lw=5, sh=(0.25, 0.3))
    c.ell(cx, cy, r * 0.84, r * 0.84, CREAM, lw=3, outline=BRASS_D)
    c.ell(cx, cy, r * 0.84, r * 0.84, None, lw=0)


def task_gauge():
    """Geschwindigkeitsanzeige 1,6 m (160 x 160): Skala 0..120 ueber 270 Grad, gruener Bereich 20..40, ohne Zeiger."""
    c = C(160, 160)
    cx, cy, r = 80, 80, 76
    _dial(c, cx, cy, r)
    ri = r * 0.84
    # Winkel: 0 km/h bei 225 Grad (links unten), 120 bei -45 Grad (rechts unten), im Uhrzeigersinn
    def ang(v):
        return math.radians(225 - 270 * v / 120)
    arc0, arc1 = 225 - 270 * 40 / 120, 225 - 270 * 20 / 120                       # PIL-Winkel laufen im Uhrzeigersinn
    bb = [(cx - ri * 0.9) * S, (cy - ri * 0.9) * S, (cx + ri * 0.9) * S, (cy + ri * 0.9) * S]
    c.d.arc(bb, -arc1, -arc0, fill=GREEN, width=int(9 * S))
    c.d.arc([(cx - ri * 0.9) * S, (cy - ri * 0.9) * S, (cx + ri * 0.9) * S, (cy + ri * 0.9) * S], -(225 - 270), -(225 - 270 * 100 / 120), fill=(230, 80, 70, 255), width=int(9 * S))
    for v in range(0, 121, 10):
        a = ang(v)
        major = v % 20 == 0
        r0, r1 = ri * (0.78 if major else 0.84), ri * 0.94
        c.line([(cx + r0 * math.cos(a), cy - r0 * math.sin(a)), (cx + r1 * math.cos(a), cy - r1 * math.sin(a))], INK, 3 if major else 1.5)
        if major:
            tx, ty = cx + ri * 0.64 * math.cos(a), cy - ri * 0.64 * math.sin(a)
            _text(c, tx, ty, str(v), 11, INK, kind="bold")
    _text(c, cx, cy + 30, "mph", 9, dark(INK, 1.0), kind="bold")
    c.ell(cx, cy, 7, 7, BRASS_D, lw=3, sh=(0.3, 0.3))
    c.glint(cx - r * 0.35, cy - r * 0.45, r * 0.25, r * 0.12, 60, rot=30)
    return c.img.resize((160, 160), Image.LANCZOS)


def task_gauge_needle():
    """Zeiger 0,6 m (16 x 60), rot, Drehpunkt an der Unterkante (8, 60)."""
    c = C(16, 60)
    c.poly([(8, 2), (13, 56), (8, 60), (3, 56)], RED, lw=2, sh=(0.2, 0.25))
    c.ell(8, 56, 4, 4, BRASS_D, lw=2)
    return c.img.resize((16, 60), Image.LANCZOS)


def task_wheel():
    """Handbremsrad von oben 2,2 m (220 x 220): Messingkranz, sechs Speichen, Nabe, Holzgriff; Mitte = Bildmitte."""
    c = C(220, 220)
    cx, cy, r = 110, 110, 100
    c.ell(cx, cy, r, r, BRASS, lw=6, sh=(0.25, 0.3))
    c.ell(cx, cy, r - 16, r - 16, TRANSP, lw=6)
    for k in range(6):
        a = math.radians(k * 60 + 30)
        c.capsule((cx + 14 * math.cos(a), cy + 14 * math.sin(a)), (cx + (r - 12) * math.cos(a), cy + (r - 12) * math.sin(a)), 10, BRASS, lw=4, sh=(0.25, 0.3))
    c.ell(cx, cy, 22, 22, BRASS_D, lw=5, sh=(0.3, 0.3))
    c.ell(cx, cy, 8, 8, INK, lw=0)
    a = math.radians(30)
    gx, gy = cx + (r - 8) * math.cos(a), cy + (r - 8) * math.sin(a)
    c.ell(gx, gy, 11, 11, WOOD, lw=4, sh=(0.25, 0.3))                               # Griffknauf
    c.glint(gx - 3, gy - 4, 3, 2, 150)
    c.glint(cx - 40, cy - 60, 24, 8, 60, rot=35)
    return c.img.resize((220, 220), Image.LANCZOS)


def _vanilla_button(draw_fn):
    ss = 4
    N = 256 * ss
    im = Image.new("RGBA", (N, N), TRANSP)
    d = ImageDraw.Draw(im)
    draw_fn(im, d, ss)
    return im.resize((256, 256), Image.LANCZOS)


def task_runaway_button():
    """Kartenknopf Runaway Train: Lok mit Bewegungslinien und rotem Warnzeichen (dicke dunkle Kontur)."""
    def fn(im, d, ss):
        ink = (29, 27, 33, 255)
        lw = 9 * ss
        # Bewegungslinien links
        for k, (y, ln) in enumerate(((110, 70), (134, 95), (158, 60))):
            d.line([(14 * ss, y * ss), ((14 + ln) * ss, y * ss)], fill=(240, 244, 250, 230), width=7 * ss)
        # Lok von der Seite: Rahmen, Kessel, Fuehrerhaus, Schornstein, Raeder
        d.rounded_rectangle([70 * ss, 150 * ss, 236 * ss, 176 * ss], 6 * ss, fill=(150, 44, 40, 255), outline=ink, width=lw)
        d.rounded_rectangle([170 * ss, 70 * ss, 234 * ss, 154 * ss], 8 * ss, fill=(60, 62, 72, 255), outline=ink, width=lw)
        d.rounded_rectangle([180 * ss, 84 * ss, 224 * ss, 112 * ss], 4 * ss, fill=(255, 224, 150, 255), outline=ink, width=5 * ss)
        d.rounded_rectangle([76 * ss, 96 * ss, 178 * ss, 154 * ss], 22 * ss, fill=(46, 48, 56, 255), outline=ink, width=lw)
        d.rectangle([92 * ss, 58 * ss, 112 * ss, 100 * ss], fill=(46, 48, 56, 255), outline=ink, width=lw)
        d.rectangle([86 * ss, 52 * ss, 118 * ss, 62 * ss], fill=(222, 182, 92, 255), outline=ink, width=5 * ss)
        d.ellipse([130 * ss, 82 * ss, 160 * ss, 100 * ss], fill=(222, 182, 92, 255), outline=ink, width=5 * ss)
        d.line([(80 * ss, 125 * ss), (174 * ss, 125 * ss)], fill=(222, 182, 92, 255), width=4 * ss)
        d.ellipse([62 * ss, 104 * ss, 84 * ss, 146 * ss], fill=(255, 240, 190, 255), outline=ink, width=5 * ss)   # Scheinwerfer
        for x, r in ((100, 22), (146, 22), (200, 16)):
            d.ellipse([(x - r) * ss, (178 - r) * ss, (x + r) * ss, (178 + r) * ss], fill=(150, 44, 40, 255), outline=ink, width=lw)
            d.ellipse([(x - r * 0.4) * ss, (178 - r * 0.4) * ss, (x + r * 0.4) * ss, (178 + r * 0.4) * ss], fill=(222, 182, 92, 255), outline=ink, width=4 * ss)
        # Dampf
        for (px, py, pr) in ((96, 36, 16), (72, 28, 20), (44, 34, 16)):
            d.ellipse([(px - pr) * ss, (py - pr) * ss, (px + pr) * ss, (py + pr) * ss], fill=(240, 244, 250, 255), outline=ink, width=5 * ss)
        # Warnzeichen
        tri = [(196 * ss, 18 * ss), (246 * ss, 100 * ss), (146 * ss, 100 * ss)]
        d.polygon(tri, fill=(236, 196, 60, 255), outline=ink)
        d.line(tri + [tri[0]], fill=ink, width=lw, joint="curve")
        d.rounded_rectangle([190 * ss, 42 * ss, 202 * ss, 76 * ss], 4 * ss, fill=(200, 40, 40, 255))
        d.ellipse([189 * ss, 82 * ss, 203 * ss, 96 * ss], fill=(200, 40, 40, 255))
    return _vanilla_button(fn)


# ------------------------------------------------------------------ Minispiel: Smoke in the Cars

def _hatch(c, open_):
    """Dachluke von unten 2,4 m (240 x 240): Messingrahmen, Deckel aus genieteten Blechen mit Scharnieren oben,
    Kurbelachse in der Bildmitte (120, 120); offen: Nachthimmel mit Sternen, Deckel als Streifen oben."""
    fx0, fy0, fx1, fy1 = 18, 36, 222, 212
    c.rrect(fx0 - 8, fy0 - 8, fx1 + 8, fy1 + 8, 10, IRON, lw=6, sh=(0.1, 0.22))
    c.rrect(fx0, fy0, fx1, fy1, 6, BRASS, lw=4, sh=(0.25, 0.3))
    ix0, iy0, ix1, iy1 = fx0 + 12, fy0 + 12, fx1 - 12, fy1 - 12
    if not open_:
        c.rrect(ix0, iy0, ix1, iy1, 4, STEEL, lw=4, sh=(0.14, 0.22))
        c.brushed(0.04, seed=4)
        c.line([(120, iy0 + 4), (120, iy1 - 4)], STEEL_D, 3)
        c.line([(ix0 + 4, 120), (ix1 - 4, 120)], STEEL_D, 3)
        for x in range(ix0 + 10, ix1, 24):
            c.rivet(x, iy0 + 8, 3.5, STEEL_L)
            c.rivet(x, iy1 - 8, 3.5, STEEL_L)
        for y in range(iy0 + 32, iy1 - 10, 24):
            c.rivet(ix0 + 8, y, 3.5, STEEL_L)
            c.rivet(ix1 - 8, y, 3.5, STEEL_L)
    else:
        m, md = c.mask()
        md.rounded_rectangle([ix0 * S, iy0 * S, ix1 * S, iy1 * S], 4 * S, fill=255)
        sky = Image.new("RGBA", c.img.size, NIGHT)
        c.img.paste(sky, (0, 0), m)
        c.d = ImageDraw.Draw(c.img)
        rnd = random.Random(8)
        for _ in range(60):
            x, y = rnd.uniform(ix0 + 4, ix1 - 4), rnd.uniform(iy0 + 4, iy1 - 4)
            r = rnd.choice((1.0, 1.5, 2.2))
            c.ell(x, y, r, r, (255, 250, 230, 255), lw=0)
        c.ell(ix1 - 36, iy0 + 34, 14, 14, (250, 244, 214, 255), lw=0)
        c.ell(ix1 - 30, iy0 + 29, 12, 12, NIGHT, lw=0)
        c.glow(120, 130, 70, 50, (120, 150, 230, 40), 20)
        c.rrect(ix0, iy0, ix1, iy0 + 26, 3, STEEL_D, lw=4, sh=(0.1, 0.3))          # hochgeklappter Deckel von unten
        c.line([(ix0 + 6, iy0 + 6), (ix1 - 6, iy0 + 6)], STEEL_L, 2)
        c.rrect(ix0, iy0, ix1, iy1, 4, None, lw=4, outline=BRASS_D)
    for x in (ix0 + 30, ix1 - 30):                                                  # Scharniere oben
        c.rrect(x - 12, fy0 + 2, x + 12, fy0 + 20, 3, BRASS_D, lw=3, sh=(0.3, 0.3))
        c.rivet(x, fy0 + 11, 3, BRASS_L)
    c.ell(120, 120, 18, 18, IRON_L, lw=4, sh=(0.2, 0.3))                             # Kurbelachse (Bildmitte)
    c.ell(120, 120, 8, 8, BRASS_D, lw=3, sh=(0.3, 0.3))
    c.ell(120, 120, 3, 3, INK, lw=0)
    c.rrect(84, fy1 + 10, 156, fy1 + 26, 4, BRASS, lw=3, sh=(0.25, 0.3))
    _text(c, 120, fy1 + 18, "ROOF HATCH", 9, INK)


def task_hatch(open_=False):
    c = C(240, 240)
    _hatch(c, open_)
    return c.img.resize((240, 240), Image.LANCZOS)


def task_crank():
    """Kurbel 0,9 m (90 x 90): Nabe in der Bildmitte, Arm nach rechts, Holzgriff; Drehpunkt (45, 45)."""
    c = C(90, 90)
    c.capsule((45, 45), (78, 45), 10, STEEL, lw=4, sh=(0.2, 0.3))
    c.line([(50, 42), (74, 42)], STEEL_L, 2)
    c.ell(45, 45, 13, 13, BRASS, lw=4, sh=(0.3, 0.3))
    c.ell(45, 45, 4, 4, INK, lw=0)
    c.ell(78, 45, 9, 9, WOOD, lw=4, sh=(0.25, 0.3))
    c.glint(76, 42, 3, 2, 150)
    return c.img.resize((90, 90), Image.LANCZOS)


def task_smoke_button():
    """Kartenknopf Smoke in the Cars: Reisezugwagen mit Rauchwolken aus den Fenstern und Warnzeichen."""
    def fn(im, d, ss):
        ink = (29, 27, 33, 255)
        lw = 9 * ss
        d.rounded_rectangle([24 * ss, 120 * ss, 232 * ss, 196 * ss], 12 * ss, fill=(58, 74, 128, 255), outline=ink, width=lw)
        d.line([(30 * ss, 186 * ss), (226 * ss, 186 * ss)], fill=(222, 182, 92, 255), width=4 * ss)
        for k in range(4):
            x = 44 + k * 48
            d.rounded_rectangle([x * ss, 134 * ss, (x + 30) * ss, 164 * ss], 4 * ss, fill=(255, 214, 120, 255), outline=ink, width=5 * ss)
        for x in (70, 186):
            d.ellipse([(x - 14) * ss, 190 * ss, (x + 14) * ss, 218 * ss], fill=(60, 62, 72, 255), outline=ink, width=lw)
        # Rauch aus den Fenstern nach oben
        for (px, py, pr) in ((60, 104, 18), (84, 86, 22), (116, 70, 26), (152, 62, 24), (186, 80, 20), (210, 100, 16)):
            d.ellipse([(px - pr) * ss, (py - pr) * ss, (px + pr) * ss, (py + pr) * ss], fill=(170, 172, 182, 255), outline=ink, width=5 * ss)
        for (px, py, pr) in ((84, 86, 22), (116, 70, 26), (152, 62, 24)):
            d.ellipse([(px - pr * 0.55) * ss, (py - pr * 0.75) * ss, (px + pr * 0.1) * ss, (py - pr * 0.1) * ss], fill=(214, 216, 224, 255))
        tri = [(198 * ss, 16 * ss), (246 * ss, 96 * ss), (150 * ss, 96 * ss)]
        d.polygon(tri, fill=(236, 196, 60, 255), outline=ink)
        d.line(tri + [tri[0]], fill=ink, width=lw, joint="curve")
        d.rounded_rectangle([192 * ss, 40 * ss, 204 * ss, 72 * ss], 4 * ss, fill=(200, 40, 40, 255))
        d.ellipse([191 * ss, 78 * ss, 205 * ss, 92 * ss], fill=(200, 40, 40, 255))
    return _vanilla_button(fn)


# ------------------------------------------------------------------ Lieferung und Uebersicht

def files():
    return {
        "train_fx_spark.png": fx_spark(), "train_fx_speed.png": fx_speed(), "train_fx_fire.png": fx_fire(), "train_fx_smoke.png": fx_smoke(),
        "task_train_brake.png": task_brake(), "task_train_brake_lever.png": task_brake_lever(),
        "task_train_gauge.png": task_gauge(), "task_train_gauge_needle.png": task_gauge_needle(), "task_train_wheel.png": task_wheel(),
        "task_train_runaway_button.png": task_runaway_button(),
        "task_train_hatch.png": task_hatch(False), "task_train_hatch_open.png": task_hatch(True), "task_train_crank.png": task_crank(),
        "task_train_smoke_button.png": task_smoke_button(),
    }


def preview_sheet(fx, path):
    """Alle Effekt- und Minispielgrafiken auf einem Blatt (Schachbrett fuer Alpha), Dateiname darunter."""
    names = list(fx)
    pad, lab = 24, 22
    f = font(14, "bold")
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    labels = {n: f"{n}  {fx[n].width}x{fx[n].height}" for n in names}
    cell = {n: max(fx[n].width, int(tmp.textlength(labels[n], font=f)) + 4) for n in names}   # Zelle mindestens so breit wie der Text
    rows = []
    row, x = [], 0
    for n in names:
        if row and x + cell[n] + pad > 1500:
            rows.append(row)
            row, x = [], 0
        row.append(n)
        x += cell[n] + pad
    if row:
        rows.append(row)
    W = max(sum(cell[n] + pad for n in r) for r in rows) + pad
    H = sum(max(fx[n].height for n in r) + pad + lab for r in rows) + pad
    sheet = Image.new("RGB", (W, H), (52, 54, 62))
    d = ImageDraw.Draw(sheet)
    for yy in range(0, H, 16):                                                    # Schachbrett
        for xx in range(0, W, 16):
            if (xx // 16 + yy // 16) % 2 == 0:
                d.rectangle([xx, yy, xx + 15, yy + 15], fill=(60, 62, 70))
    y = pad
    for r in rows:
        x = pad
        hmax = max(fx[n].height for n in r)
        for n in r:
            im = fx[n]
            sheet.paste(im, (x, y), im if im.mode == "RGBA" else None)
            d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(120, 124, 136))
            d.text((x, y + hmax + 4), labels[n], font=f, fill=(220, 224, 232))
            x += cell[n] + pad
        y += hmax + pad + lab
    sheet.save(path)
    return sheet
