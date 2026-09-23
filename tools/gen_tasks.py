# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_tasks.py - Grafik der eigenen Minispiele (docs/TASK_KONZEPT.md) im Among-Us-Stil:
# flache Flaechen mit zwei bis drei Tonstufen (Licht oben, Schatten unten), Glanzpunkte,
# dezente Textur, dicke dunkle Kontur. 100 px = 1 Einheit im Minispiel (Staubschicht: 50 px).
#
# Palette je Karte:
#   Museum: dunkelblaue Waende, Messing, Sandstein, warmes Spotlicht
#   Wald:   warme Holzbretter, dunkelgruenes Eisen, Laternenlicht
#   Stahl:  gebuerstetes Blaugrau mit Schrauben (Technik beider Karten)
#
# Die Geometrie (Drehpunkte, Fenster, Rasterpositionen) ist im C#-Code fest verdrahtet und bleibt
# hier unveraendert; siehe die Kommentare "Kontrakt" an den betroffenen Stellen.
#
#   python tools/gen_tasks.py   ->  assets/task_*.png

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets"
S = 3                                    # Supersampling
INK = (30, 27, 33, 255)

# Palette
BRASS, BRASS_L, BRASS_D = (196, 160, 82, 255), (236, 206, 122, 255), (146, 112, 52, 255)
NAVY, NAVY_L, NAVY_D = (34, 46, 70, 255), (48, 64, 94, 255), (24, 32, 50, 255)
SAND, SAND_D, SAND_L = (222, 196, 140, 255), (180, 150, 96, 255), (240, 222, 178, 255)
GOLD = (236, 190, 70, 255)
WOOD, WOOD_L, WOOD_D = (160, 108, 62, 255), (196, 142, 84, 255), (118, 76, 42, 255)
IRON, IRON_L, IRON_D = (47, 90, 69, 255), (78, 128, 100, 255), (32, 62, 48, 255)
STEEL, STEEL_L, STEEL_D = (84, 92, 104, 255), (118, 126, 138, 255), (58, 64, 74, 255)
CREAM = (244, 238, 222, 255)
WHITE = (255, 255, 255, 255)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def dark(c, k=0.78):
    return tuple(int(v * k) for v in c[:3]) + (255,)


def light(c, k=0.25):
    return tuple(int(v + (255 - v) * k) for v in c[:3]) + (255,)


class C:
    """Zeichenflaeche mit Supersampling; Koordinaten in Zielpixeln."""

    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * S, h * S), bg)
        self.d = ImageDraw.Draw(self.img)

    def P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    # ---- Masken und Schattierung
    def mask(self):
        m = Image.new("L", self.img.size, 0)
        return m, ImageDraw.Draw(m)

    def _apply(self, fn):
        arr = np.asarray(self.img).astype(np.float32)
        fn(arr)
        self.img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        self.d = ImageDraw.Draw(self.img)

    def shade(self, mask, top=0.16, bottom=0.22, y0=None, y1=None):
        """Vertikaler Verlauf innerhalb der Maske: oben heller, unten dunkler."""
        m = np.asarray(mask, dtype=np.float32) / 255.0
        rows = np.nonzero(m.max(axis=1) > 0)[0]
        if rows.size == 0:
            return
        a, b = (rows[0], rows[-1]) if y0 is None else (y0 * S, y1 * S)
        t = np.clip((np.arange(m.shape[0]) - a) / max(1, b - a), 0, 1)[:, None]
        li = (top * np.clip(1 - 2.4 * t, 0, 1) * m)[..., None]
        da = (bottom * np.clip(2.4 * t - 1.4, 0, 1) * m)[..., None]

        def fn(arr):
            rgb = arr[..., :3]
            rgb += (255 - rgb) * li - rgb * da

        self._apply(fn)

    def shade_x(self, mask, left=0.16, right=0.22):
        """Horizontaler Verlauf (Zylinder): links heller, rechts dunkler."""
        m = np.asarray(mask, dtype=np.float32) / 255.0
        cols = np.nonzero(m.max(axis=0) > 0)[0]
        if cols.size == 0:
            return
        a, b = cols[0], cols[-1]
        t = np.clip((np.arange(m.shape[1]) - a) / max(1, b - a), 0, 1)[None, :]
        li = (left * np.clip(1 - 2.6 * np.abs(t - 0.32), 0, 1) * m)[..., None]
        da = (right * np.clip(2.4 * t - 1.5, 0, 1) * m)[..., None]

        def fn(arr):
            rgb = arr[..., :3]
            rgb += (255 - rgb) * li - rgb * da

        self._apply(fn)

    def mottle(self, amount=0.06, cell=10, seed=1, mask=None):
        """Weiche Fleckigkeit (Putz, Stein, Papier)."""
        rnd = np.random.default_rng(seed)
        h, w = self.img.height, self.img.width
        small = rnd.random((h // (cell * S) + 2, w // (cell * S) + 2)).astype(np.float32)
        n = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255
        f = 1 + (n - 0.5) * 2 * amount
        if mask is not None:
            m = np.asarray(mask, dtype=np.float32) / 255.0
            f = 1 + (f - 1) * m
        self._apply(lambda arr: arr.__setitem__((..., slice(0, 3)), arr[..., :3] * f[..., None]))

    def grain(self, x0, y0, x1, y1, amount=0.08, seed=2, freq=0.45, mask=None):
        """Holzmaserung: wellige Laengsstreifen im Rechteck (Zielpixel)."""
        rnd = random.Random(seed)
        h, w = self.img.height, self.img.width
        ys = np.arange(h)[:, None] / S
        xs = np.arange(w)[None, :] / S
        ph = rnd.random() * 10
        wave = np.sin(xs * 0.035 + ph) * 3 + np.sin(xs * 0.011 + ph * 2) * 5
        v = np.sin((ys + wave) * freq + ph) * 0.5 + np.sin((ys + wave * 0.5) * freq * 2.3 + ph) * 0.3
        f = 1 + v * amount
        box = np.zeros((h, w), dtype=np.float32)
        box[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)] = 1
        if mask is not None:
            box *= np.asarray(mask, dtype=np.float32) / 255.0
        f = 1 + (f - 1) * box
        self._apply(lambda arr: arr.__setitem__((..., slice(0, 3)), arr[..., :3] * f[..., None]))

    def brushed(self, amount=0.05, seed=3, mask=None):
        """Gebuerstetes Metall: feine waagerechte Streifen."""
        rnd = np.random.default_rng(seed)
        h, w = self.img.height, self.img.width
        rows = rnd.random((h // S + 1, 1)).astype(np.float32)
        rows = np.repeat(np.repeat(rows, S, axis=0)[:h], w, axis=1)
        f = 1 + (rows - 0.5) * 2 * amount
        if mask is not None:
            f = 1 + (f - 1) * np.asarray(mask, dtype=np.float32) / 255.0
        self._apply(lambda arr: arr.__setitem__((..., slice(0, 3)), arr[..., :3] * f[..., None]))

    def vignette(self, strength=0.35, x0=0, y0=0, x1=None, y1=None, power=2.2):
        """Dunkle Ecken (Zielpixel-Rechteck)."""
        x1 = self.w if x1 is None else x1
        y1 = self.h if y1 is None else y1
        h, w = self.img.height, self.img.width
        cx, cy = (x0 + x1) / 2 * S, (y0 + y1) / 2 * S
        rx, ry = (x1 - x0) / 2 * S, (y1 - y0) / 2 * S
        ys = np.arange(h)[:, None]
        xs = np.arange(w)[None, :]
        dd = np.sqrt(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2) / math.sqrt(2)
        f = 1 - strength * np.clip(dd, 0, 1) ** power
        self._apply(lambda arr: arr.__setitem__((..., slice(0, 3)), arr[..., :3] * f[..., None]))

    def glow(self, cx, cy, rx, ry, color, blur):
        g = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=color)
        self.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur * S)))
        self.d = ImageDraw.Draw(self.img)

    def soft_poly(self, pts, color, blur):
        g = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).polygon(self.P(pts), fill=color)
        self.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur * S)))
        self.d = ImageDraw.Draw(self.img)

    # ---- Grundformen (fill, optional Schattierung sh=(oben, unten), dann Kontur)
    def poly(self, pts, fill, lw=6, outline=INK, sh=None, shx=None):
        p = self.P(pts)
        if fill is not None:
            self.d.polygon(p, fill=fill)
            if sh or shx:
                m, md = self.mask()
                md.polygon(p, fill=255)
                if sh:
                    self.shade(m, *sh)
                if shx:
                    self.shade_x(m, *shx)
        if lw:
            self.d.line(p + [p[0]], fill=outline, width=lw * S, joint="curve")
            r = lw * S / 2
            for x, y in p:
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=outline)

    def rrect(self, x0, y0, x1, y1, r, fill, lw=6, outline=INK, sh=None, shx=None):
        box = [x0 * S, y0 * S, x1 * S, y1 * S]
        if fill is not None:
            self.d.rounded_rectangle(box, r * S, fill=fill)
            if sh or shx:
                m, md = self.mask()
                md.rounded_rectangle(box, r * S, fill=255)
                if sh:
                    self.shade(m, *sh)
                if shx:
                    self.shade_x(m, *shx)
        if lw:
            self.d.rounded_rectangle(box, r * S, outline=outline, width=lw * S)

    def ell(self, cx, cy, rx, ry, fill, lw=6, outline=INK, sh=None, shx=None):
        box = [(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S]
        if fill is not None:
            self.d.ellipse(box, fill=fill)
            if sh or shx:
                m, md = self.mask()
                md.ellipse(box, fill=255)
                if sh:
                    self.shade(m, *sh)
                if shx:
                    self.shade_x(m, *shx)
        if lw:
            self.d.ellipse(box, outline=outline, width=lw * S)

    def line(self, pts, fill, w):
        self.d.line(self.P(pts), fill=fill, width=int(w * S), joint="curve")

    def capsule(self, a, b, w, fill, lw=5, outline=INK, sh=None):
        """Knochen/Stab mit runden Enden und Kontur."""
        if lw:
            self.d.line(self.P([a, b]), fill=outline, width=int((w + 2 * lw) * S))
            for x, y in (a, b):
                r = (w / 2 + lw) * S
                self.d.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=outline)
        self.d.line(self.P([a, b]), fill=fill, width=int(w * S))
        for x, y in (a, b):
            r = w / 2 * S
            self.d.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=fill)
        if sh:
            m, md = self.mask()
            md.line(self.P([a, b]), fill=255, width=int(w * S))
            for x, y in (a, b):
                r = w / 2 * S
                md.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=255)
            self.shade(m, *sh)

    def arc(self, box, a0, a1, fill, w):
        self.d.arc([v * S for v in box], a0, a1, fill=fill, width=int(w * S))

    def glint(self, cx, cy, rx, ry, a=110, rot=0):
        """Weisser Glanzpunkt."""
        g = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        gd.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=(255, 255, 255, a))
        if rot:
            g = g.rotate(rot, center=(cx * S, cy * S), resample=Image.BICUBIC)
        self.img.alpha_composite(g)
        self.d = ImageDraw.Draw(self.img)

    def rivet(self, x, y, r=5, col=STEEL_L):
        self.ell(x, y, r, r, col, lw=max(2, r // 2), sh=(0.3, 0.4))
        self.glint(x - r * 0.3, y - r * 0.3, r * 0.35, r * 0.25, 140)

    def screw(self, x, y, r=7, col=STEEL_L, rot=30):
        self.ell(x, y, r, r, col, lw=3, sh=(0.3, 0.35))
        a = math.radians(rot)
        self.line([(x - math.cos(a) * r * 0.7, y - math.sin(a) * r * 0.7), (x + math.cos(a) * r * 0.7, y + math.sin(a) * r * 0.7)], INK, max(2, r * 0.3))

    def save(self, name):
        img = self.img.resize((self.w, self.h), Image.LANCZOS)
        img.save(OUT / name)
        print(OUT / name, img.size)
        return img


def font(px):
    for f in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        try:
            return ImageFont.truetype(f, px * S)
        except OSError:
            pass
    return ImageFont.load_default()


def label(c, x, y, text, px, fill=INK):
    f = font(px)
    b = c.d.textbbox((0, 0), text, font=f)
    c.d.text((x * S - (b[2] - b[0]) / 2 - b[0], y * S - (b[3] - b[1]) / 2 - b[1]), text, font=f, fill=fill)


# ------------------------------------------------------------------ gemeinsam

def close_button():
    c = C(72, 72)
    c.ell(36, 38, 31, 31, (120, 120, 128, 120), lw=0)                     # weicher Schatten
    c.ell(36, 36, 31, 31, (232, 232, 236, 255), lw=6, sh=(0.1, 0.18))
    c.line([(24, 24), (48, 48)], INK, 9)
    c.line([(48, 24), (24, 48)], INK, 9)
    c.glint(28, 24, 9, 5, 120, rot=35)
    c.save("task_close.png")


def frame_wood(c, col=(74, 52, 38, 255)):
    """Dunkler Holzrahmen aussen (alle 720 x 520 Tafeln)."""
    c.rrect(4, 4, 716, 516, 26, col, lw=8, sh=(0.12, 0.2))
    m, md = c.mask()
    md.rounded_rectangle([4 * S, 4 * S, 716 * S, 516 * S], 26 * S, fill=255)
    c.grain(4, 4, 716, 516, 0.07, seed=5, freq=0.3, mask=m)


# ------------------------------------------------------------------ Museum: Dust the Skeleton

def museum_panel():
    c = C(720, 520)
    frame_wood(c)
    c.rrect(26, 26, 694, 494, 14, BRASS, lw=4, sh=(0.22, 0.3))            # Messingleiste
    c.rrect(36, 36, 684, 484, 10, NAVY, lw=4)                             # Rueckwand
    # Tapete: schmale Streifen mit feinem Ornamentversatz
    for i, x in enumerate(range(52, 684, 40)):
        c.d.rectangle([x * S, 40 * S, (x + 18) * S, 480 * S], fill=NAVY_L if i % 2 == 0 else (40, 54, 80, 255))
    for y in range(64, 470, 48):
        for x in range(61, 684, 80):
            c.d.ellipse([(x - 4) * S, (y - 6) * S, (x + 4) * S, (y + 6) * S], fill=(56, 74, 108, 255))
    m, md = c.mask()
    md.rectangle([38 * S, 38 * S, 682 * S, 482 * S], fill=255)
    c.mottle(0.08, 22, seed=7, mask=m)
    c.vignette(0.45, 36, 36, 684, 484)
    # Spot oben mit warmem Lichtkegel
    c.soft_poly([(322, 44), (398, 44), (620, 430), (100, 430)], (255, 236, 190, 46), 18)
    c.soft_poly([(342, 44), (378, 44), (520, 430), (200, 430)], (255, 240, 200, 30), 10)
    c.rrect(330, 26, 390, 58, 8, STEEL_D, lw=5, sh=(0.2, 0.2))            # Strahlergehaeuse
    c.rrect(342, 52, 378, 62, 3, (255, 244, 200, 255), lw=3)
    c.glow(360, 60, 40, 14, (255, 240, 190, 120), 8)
    # Sandsteinsockel
    c.rrect(90, 420, 630, 470, 8, (214, 200, 168, 255), lw=6, sh=(0.14, 0.2))
    m, md = c.mask()
    md.rounded_rectangle([90 * S, 420 * S, 630 * S, 470 * S], 8 * S, fill=255)
    c.mottle(0.07, 9, seed=11, mask=m)
    c.d.rectangle([96 * S, 452 * S, 624 * S, 464 * S], fill=(178, 162, 128, 255))
    c.line([(96, 430), (624, 430)], (240, 232, 210, 255), 3)
    c.rrect(300, 426, 420, 446, 4, BRASS, lw=3, sh=(0.3, 0.3))            # Messingschild
    c.line([(310, 432), (410, 432)], BRASS_L, 2)
    for x in (48, 672):
        for y in (48, 472):
            c.rivet(x, y, 6, BRASS_L)
    c.save("task_museum_panel.png")


def museum_dino():
    c = C(560, 300)
    bone, bone_d = (240, 231, 208, 255), (206, 192, 158, 255)
    metal = (78, 84, 96, 255)
    B = lambda a, b, w, lw=5: c.capsule(a, b, w, bone, lw, sh=(0.12, 0.28))
    # Metallstuetzen
    for x, top in ((110, 178), (262, 150), (470, 128)):
        c.capsule((x, top), (x, 292), 7, metal, 4, sh=(0.2, 0.3))
        c.rrect(x - 16, 284, x + 16, 296, 3, metal, lw=4, sh=(0.2, 0.2))
    # Schwanz: Wirbel nach links kleiner werdend, leicht geschwungen
    tail = [(226 - i * 23, 118 + i * 5 + i * i * 0.5) for i in range(9)]
    c.line(tail, INK, 14)
    c.line(tail, bone_d, 8)
    for i, (x, y) in enumerate(tail):
        r = 12 - i * 0.8
        c.ell(x, y, r * 1.15, r, bone, lw=4, sh=(0.15, 0.3))
        if i < 8:
            c.line([(x, y - r), (x - 2, y - r - 9 + i * 0.5)], INK, 6)
            c.line([(x, y - r), (x - 2, y - r - 9 + i * 0.5)], bone, 3)
            c.line([(x, y + r), (x - 2, y + r + 8 - i * 0.6)], INK, 5)
            c.line([(x, y + r), (x - 2, y + r + 8 - i * 0.6)], bone, 2)
    # Wirbelsaeule und Hals (Bogen)
    spine = [(240, 110), (272, 100), (304, 94), (336, 92), (368, 94), (396, 96), (418, 90), (432, 76), (440, 60)]
    for i, (x, y) in enumerate(spine):
        rx = 15 if i < 6 else 12
        c.line([(x, y - 8), (x - 5, y - 32)], INK, 8)                    # Dornfortsatz
        c.line([(x, y - 8), (x - 5, y - 32)], bone, 4)
    # Rippenkorb
    for i, x in enumerate(range(276, 404, 16)):
        h = 78 - abs(i - 3.5) * 9
        box = [(x - 30), 96, (x + 24), 100 + h * 2]
        c.arc(box, 92, 195, INK, 9)
        c.arc(box, 92, 195, bone, 4)
    for i, (x, y) in enumerate(spine):
        rx = 15 if i < 6 else 12
        c.ell(x, y, rx, 11, bone, lw=4, sh=(0.15, 0.3))
    # Becken
    c.poly([(218, 100), (250, 92), (292, 98), (300, 122), (288, 146), (268, 156), (244, 152), (224, 136), (212, 118)], bone, lw=5, sh=(0.14, 0.3))
    c.ell(258, 126, 10, 9, bone_d, lw=3)
    c.line([(232, 112), (250, 104), (280, 108)], bone_d, 3)
    # Beine: Oberschenkel, Schienbein, Fuss mit drei Zehen (hinteres Bein etwas dunkler)
    for dx, bent, col in ((30, -1, bone_d), (0, 1, bone)):
        hip = (256 + dx, 142)
        knee = (232 + dx + 18 * bent, 200)
        ankle = (262 + dx, 250)
        c.capsule(hip, knee, 15, col, 5, sh=(0.12, 0.3))
        c.capsule(knee, ankle, 11, col, 5, sh=(0.12, 0.3))
        c.ell(knee[0], knee[1], 11, 10, col, lw=4, sh=(0.15, 0.3))
        for tx in (-14, 4, 22):
            c.capsule((ankle[0], ankle[1] + 4), (ankle[0] + tx + 6, 276), 7, col, 4)
            c.poly([(ankle[0] + tx + 2, 274), (ankle[0] + tx + 12, 274), (ankle[0] + tx + 9, 286)], WHITE, lw=3)
    # Aermchen mit zwei Krallen
    c.capsule((404, 118), (424, 142), 8, bone, 4)
    c.capsule((424, 142), (440, 138), 6, bone, 4)
    for dx in (0, 6):
        c.poly([(438 + dx, 134), (446 + dx, 134), (450 + dx, 146)], WHITE, lw=2)
    # Schaedel: T-Rex-Profil mit Schnauze nach rechts
    c.poly([(432, 62), (452, 40), (486, 30), (528, 34), (552, 52), (556, 74), (548, 92), (520, 96), (486, 98), (462, 104), (438, 96), (428, 80)],
           bone, lw=6, sh=(0.14, 0.3))
    c.poly([(466, 100), (548, 92), (556, 108), (528, 120), (486, 122), (462, 114)], bone_d, lw=5, sh=(0.1, 0.25))   # Unterkiefer
    for x in range(486, 548, 9):                                                                                    # Zaehne oben
        c.poly([(x, 96), (x + 6, 96), (x + 3, 108)], WHITE, lw=2)
    for x in range(490, 540, 10):                                                                                   # Zaehne unten
        c.poly([(x, 104), (x + 6, 104), (x + 3, 94)], WHITE, lw=2)
    c.poly([(456, 52), (484, 44), (490, 68), (466, 76)], INK, lw=0)                                                 # Augenhoehle
    c.ell(474, 60, 4, 4, (90, 84, 78, 255), lw=0)
    c.poly([(500, 44), (528, 42), (532, 64), (506, 70)], (72, 64, 56, 255), lw=0)                                  # Schaedelfenster
    c.ell(542, 58, 5, 4, INK, lw=0)                                                                                 # Nasenloch
    c.save("task_museum_dino.png")


def museum_dust():
    """Weicher grauer Museumsstaub mit Flusen (280 x 150 bei 50 px/Einheit)."""
    w, h = 280, 150
    rnd = np.random.default_rng(7)
    # Grundton: hellgrau mit sanften Wolken
    small = rnd.random((10, 18)).astype(np.float32)
    cloud = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255
    fine = rnd.random((h, w)).astype(np.float32)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), dtype=np.float32) / 255
    v = 168 + (cloud - 0.5) * 40 + (fine - 0.5) * 22
    rgb = np.stack([v + 4, v, v - 6], axis=-1)
    a = np.full((h, w), 232, dtype=np.float32) - (cloud - 0.5) * 30
    # ausgefranster Rand
    ys = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    edge = np.minimum(np.minimum(xs, w - 1 - xs), np.minimum(ys, h - 1 - ys)).astype(np.float32)
    a *= np.clip(edge / 3.0 + (fine - 0.5) * 0.8, 0, 1)
    img = Image.fromarray(np.clip(np.concatenate([rgb, a[..., None]], axis=-1), 0, 255).astype(np.uint8), "RGBA")
    # Flusen: weiche, helle Knaeuel
    fl = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fl)
    for _ in range(70):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        r = int(rnd.integers(3, 9))
        for k in range(4):
            ox, oy = rnd.integers(-r, r + 1), rnd.integers(-r, r + 1)
            fd.ellipse([x + ox - r, y + oy - r, x + ox + r, y + oy + r], fill=(226, 222, 214, 62))
    fl = fl.filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.LANCZOS)
    img.alpha_composite(fl)
    # feine Fasern (Spinnweb, sehr hell und zart)
    fb = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fb)
    for _ in range(26):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        ang = rnd.random() * math.pi
        pts = [(x, y)]
        for k in range(1, 5):
            ang += (rnd.random() - 0.5) * 0.9
            pts.append((pts[-1][0] + math.cos(ang) * 14, pts[-1][1] + math.sin(ang) * 14))
        fd.line(pts, fill=(238, 236, 230, 120), width=2, joint="curve")
    fb = fb.filter(ImageFilter.GaussianBlur(0.8)).resize((w, h), Image.LANCZOS)
    img.alpha_composite(fb)
    # ein paar dunklere Kruemel, klein und weich
    kr = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    kd = ImageDraw.Draw(kr)
    for _ in range(60):
        x, y = rnd.integers(0, w * 2), rnd.integers(0, h * 2)
        r = int(rnd.integers(1, 3))
        kd.ellipse([x - r, y - r, x + r, y + r], fill=(120, 112, 104, 110))
    kr = kr.filter(ImageFilter.GaussianBlur(0.9)).resize((w, h), Image.LANCZOS)
    img.alpha_composite(kr)
    img.save(OUT / "task_museum_dust.png")
    print(OUT / "task_museum_dust.png", img.size)


def museum_brush():
    c = C(120, 120)
    # Kontrakt: Griffende oben rechts, Borsten unten links (Pivot 0.3/0.27 im Code)
    c.capsule((110, 10), (60, 60), 10, WOOD_L, 4, sh=(0.2, 0.35))
    c.line([(104, 14), (66, 52)], (226, 178, 118, 255), 2)
    c.rrect(40, 52, 70, 72, 4, BRASS, lw=4, sh=(0.3, 0.3))                # Zwinge
    c.poly([(30, 62), (62, 62), (58, 104), (22, 108), (16, 86)], (241, 226, 190, 255), lw=5, sh=(0.1, 0.25))
    for x in (26, 34, 42, 50):
        c.line([(x + 6, 68), (x - 2, 102)], (214, 192, 150, 255), 2)
    c.save("task_brush.png")


# ------------------------------------------------------------------ Wald: Prime the Pump

def wald_panel():
    c = C(720, 520)
    frame_wood(c, (58, 40, 28, 255))
    rnd = random.Random(3)
    for i, y in enumerate(range(30, 492, 46)):                            # Bretter
        col = mix(WOOD, WOOD_L, (i % 3) * 0.18)
        c.d.rectangle([28 * S, y * S, 692 * S, (y + 44) * S], fill=col, outline=INK, width=3 * S)
        m, md = c.mask()
        md.rectangle([28 * S, y * S, 692 * S, (y + 44) * S], fill=255)
        c.shade(m, 0.1, 0.2)
        c.grain(28, y, 692, y + 44, 0.09, seed=10 + i, freq=0.5, mask=m)
        if rnd.random() < 0.5:                                            # Astloch
            kx = rnd.randrange(120, 600)
            c.ell(kx, y + 22, 9, 6, WOOD_D, lw=2, sh=(0.1, 0.3))
            c.ell(kx, y + 22, 4, 3, (92, 58, 32, 255), lw=0)
        c.line([(32, y + 4), (688, y + 4)], (218, 166, 104, 90), 2)       # Lichtkante
        for x in (48, 672):                                               # Naegel
            c.rivet(x, y + 22, 4, (90, 92, 96, 255))
    c.rrect(28, 470, 692, 492, 4, (70, 96, 60, 255), lw=4, sh=(0.2, 0.2))  # Moos-/Bodenleiste
    for x in range(40, 690, 26):
        c.ell(x, 474, 7, 4, (92, 128, 74, 255), lw=0)
    # Laternenlicht: warmer Schein oben links, Ecken dunkler
    c.vignette(0.32, 28, 28, 692, 492)
    c.glow(150, 90, 300, 230, (255, 200, 120, 34), 40)
    # Eisenwinkel in den Ecken
    for x, sx in ((28, 1), (692, -1)):
        for y, sy in ((28, 1), (492, -1)):
            c.poly([(x, y), (x + sx * 70, y), (x + sx * 70, y + sy * 16), (x + sx * 16, y + sy * 16), (x + sx * 16, y + sy * 70), (x, y + sy * 70)],
                   IRON, lw=4, sh=(0.2, 0.3))
            c.rivet(x + sx * 48, y + sy * 8, 4, IRON_L)
            c.rivet(x + sx * 8, y + sy * 48, 4, IRON_L)
    c.save("task_wald_panel.png")


def pump_body():
    c = C(260, 420)
    c.rrect(40, 356, 220, 412, 8, (130, 126, 118, 255), lw=6, sh=(0.14, 0.22))   # Steinsockel
    m, md = c.mask()
    md.rounded_rectangle([40 * S, 356 * S, 220 * S, 412 * S], 8 * S, fill=255)
    c.mottle(0.09, 6, seed=4, mask=m)
    c.line([(46, 362), (214, 362)], (190, 186, 178, 255), 3)
    c.rrect(84, 90, 176, 362, 20, IRON, lw=7, shx=(0.22, 0.3))                   # Saeule (Zylinder)
    c.poly([(176, 170), (246, 184), (246, 206), (176, 214)], IRON, lw=6, sh=(0.2, 0.3))   # Auslauf
    c.ell(246, 195, 8, 12, IRON_D, lw=5, sh=(0.1, 0.2))
    c.rrect(66, 58, 194, 100, 14, IRON_D, lw=7, shx=(0.25, 0.25))                # Kappe
    c.ell(130, 58, 22, 14, IRON, lw=6, sh=(0.3, 0.2))
    c.ell(130, 48, 8, 8, IRON_L, lw=4, sh=(0.3, 0.3))                             # Knauf
    for y in (130, 250, 330):                                                    # Ringe + Nieten
        c.rrect(78, y, 182, y + 14, 6, IRON_D, lw=5, shx=(0.25, 0.25))
        for x in (96, 130, 164):
            c.rivet(x, y + 7, 3, IRON_L)
    c.save("task_pump_body.png")


def pump_handle():
    c = C(320, 56)
    # Kontrakt: Drehpunkt (24, 28), Griff am rechten Ende
    c.rrect(6, 18, 250, 38, 10, (64, 68, 76, 255), lw=6, sh=(0.3, 0.3))     # Stange
    c.ell(24, 28, 18, 18, (92, 98, 108, 255), lw=6, sh=(0.25, 0.3))         # Drehpunkt
    c.ell(24, 28, 6, 6, INK, lw=0)
    c.rrect(236, 10, 314, 46, 16, WOOD_L, lw=6, sh=(0.2, 0.3))              # Holzgriff
    c.line([(248, 18), (302, 18)], (226, 178, 118, 255), 3)
    c.line([(248, 40), (302, 40)], WOOD_D, 2)
    c.save("task_pump_handle.png")


def dial_face(c, cx, cy, green_pil=None, scale_ticks=True):
    """Messinggehaeuse, cremefarbenes Zifferblatt, Skala 210 Grad (links unten) bis -30 Grad."""
    c.ell(cx, cy + 3, 128, 128, (0, 0, 0, 70), lw=0)
    c.ell(cx, cy, 128, 128, BRASS, lw=7, sh=(0.24, 0.3))
    c.ell(cx, cy, 116, 116, BRASS_D, lw=0)
    c.ell(cx, cy, 108, 108, CREAM, lw=4, sh=(0.06, 0.08))
    if green_pil:
        box = [cx - 92, cy - 92, cx + 92, cy + 92]
        c.arc(box, green_pil[0], green_pil[1], (70, 170, 90, 255), 11)
    def at(frac, r):
        a = math.radians(210 - frac * 240)
        return cx + math.cos(a) * r, cy - math.sin(a) * r
    for i in range(25):
        f = i / 24
        r0 = 84 if i % 4 else 76
        c.line([at(f, r0), at(f, 98)], INK, 4 if i % 4 else 6)
    for i in range(0, 25, 4):                                                # Zahlen
        x, y = at(i / 24, 64)
        label(c, x, y, str(i // 4 * 2), 13, (60, 56, 60, 255))
    c.ell(cx, cy, 14, 14, (92, 98, 108, 255), lw=5, sh=(0.3, 0.3))
    c.glint(cx - 50, cy - 60, 40, 22, 60, rot=35)                             # Glas


def gauge():
    c = C(280, 280)
    dial_face(c, 140, 140, green_pil=(-30, 30))                              # gruener Endbereich = letzte 25 %
    c.save("task_gauge.png")


def needle():
    c = C(120, 20)
    # Kontrakt: Drehpunkt bei x = 8
    c.poly([(8, 4), (116, 10), (8, 16)], (206, 42, 42, 255), lw=3, sh=(0.2, 0.3))
    c.ell(8, 10, 6, 6, (70, 74, 82, 255), lw=2)
    c.save("task_needle.png")


def lamps():
    for name, glass, glow in (("task_lamp_off.png", (64, 78, 72, 255), None),
                              ("task_lamp_on.png", (200, 255, 150, 255), (190, 255, 120, 120))):
        c = C(80, 80)
        if glow:
            c.glow(40, 40, 34, 34, glow, 8)
        c.ell(40, 40, 27, 27, (96, 102, 112, 255), lw=5, sh=(0.25, 0.3))     # Fassung
        c.ell(40, 40, 21, 21, glass, lw=4, sh=(0.1, 0.25))
        c.line([(23, 40), (57, 40)], INK, 3)
        c.line([(40, 23), (40, 57)], INK, 3)
        c.glint(33, 32, 7, 5, 190 if glow else 70)
        c.save(name)


def water():
    c = C(140, 180)
    blue, lt = (72, 152, 222, 232), (176, 224, 252, 255)
    c.poly([(10, 20), (50, 12), (74, 60), (86, 170), (48, 174), (40, 70)], blue, lw=5, sh=(0.1, 0.15))
    c.line([(30, 24), (52, 64), (62, 150)], lt, 5)
    for x, y, r in ((100, 150, 9), (116, 120, 6), (24, 150, 7), (110, 90, 5)):
        c.ell(x, y, r, r, blue, lw=3)
        c.glint(x - r * 0.3, y - r * 0.3, r * 0.4, r * 0.3, 150)
    c.save("task_water.png")


# ------------------------------------------------------------------ Baustein Zuordnen

def steel_panel():
    c = C(720, 520)
    c.rrect(4, 4, 716, 516, 26, STEEL_D, lw=8, sh=(0.14, 0.2))
    c.rrect(26, 26, 694, 494, 14, STEEL, lw=4)
    m, md = c.mask()
    md.rounded_rectangle([28 * S, 28 * S, 692 * S, 492 * S], 14 * S, fill=255)
    c.brushed(0.045, seed=3, mask=m)
    c.shade(m, 0.08, 0.14)
    c.vignette(0.22, 26, 26, 694, 494)
    c.rrect(44, 44, 676, 476, 10, None, lw=3, outline=(52, 58, 68, 255))       # Inneres Feld
    c.line([(46, 46), (674, 46)], (140, 148, 160, 120), 2)
    for y in range(70, 470, 24):                                                 # Riffelung
        c.d.line([(52 * S, y * S), (668 * S, y * S)], fill=(96, 104, 116, 255), width=2 * S)
    for x in (48, 672):
        for y in (48, 472):
            c.screw(x, y, 8, STEEL_L, rot=30 + (x + y) % 90)
    # Warnstreifen unten rechts
    for i in range(6):
        x = 560 + i * 20
        c.poly([(x, 466), (x + 10, 466), (x - 4, 480), (x - 14, 480)], (232, 192, 60, 255) if i % 2 == 0 else INK, lw=0)
    c.save("task_steel_panel.png")


def shop_panel():
    c = C(720, 520)
    c.rrect(4, 4, 716, 516, 26, (96, 62, 40, 255), lw=8, sh=(0.1, 0.2))
    for i, y in enumerate(range(26, 494, 52)):
        c.d.rectangle([26 * S, y * S, 694 * S, min(494, y + 52) * S], fill=mix((168, 116, 70, 255), (150, 100, 58, 255), i % 2),
                      outline=(120, 80, 48, 255), width=2 * S)
        m, md = c.mask()
        md.rectangle([26 * S, y * S, 694 * S, min(494, y + 52) * S], fill=255)
        c.grain(26, y, 694, min(494, y + 52), 0.07, seed=20 + i, freq=0.45, mask=m)
    c.vignette(0.2)
    c.rrect(60, 60, 660, 460, 20, (46, 104, 70, 255), lw=6, sh=(0.08, 0.16))    # Filzmatte
    m, md = c.mask()
    md.rounded_rectangle([62 * S, 62 * S, 658 * S, 458 * S], 20 * S, fill=255)
    c.mottle(0.06, 4, seed=8, mask=m)
    c.rrect(74, 74, 646, 446, 14, None, lw=2, outline=(70, 134, 96, 255))       # Steppnaht
    c.save("task_shop_panel.png")


def money():
    for name, val, col, dk in (("task_coin1.png", "1", (218, 220, 226, 255), (172, 176, 184, 255)),
                               ("task_coin2.png", "2", (234, 198, 92, 255), (198, 158, 62, 255))):
        c = C(84, 84)
        c.ell(42, 44, 36, 36, (0, 0, 0, 80), lw=0)
        c.ell(42, 42, 36, 36, col, lw=6, sh=(0.2, 0.28))
        c.ell(42, 42, 27, 27, dk, lw=2, sh=(0.1, 0.2))
        for k in range(24):                                                       # Randriffel
            a = math.radians(k * 15)
            c.line([(42 + math.cos(a) * 30, 42 + math.sin(a) * 30), (42 + math.cos(a) * 34, 42 + math.sin(a) * 34)], dark(col, 0.7), 2)
        label(c, 42, 42, val, 30)
        c.glint(30, 28, 9, 5, 120, rot=40)
        c.save(name)
    for name, val, col in (("task_note5.png", "5", (118, 178, 122, 255)),
                           ("task_note10.png", "10", (206, 110, 96, 255)),
                           ("task_note20.png", "20", (100, 140, 206, 255))):
        c = C(160, 84)
        c.rrect(6, 6, 154, 78, 8, col, lw=6, sh=(0.12, 0.2))
        c.rrect(14, 14, 146, 70, 5, None, lw=2, outline=dark(col, 0.75))
        c.ell(80, 42, 22, 22, light(col, 0.3), lw=2, outline=dark(col, 0.8))       # Rosette
        for k in range(8):
            a = math.radians(k * 45)
            c.line([(80, 42), (80 + math.cos(a) * 18, 42 + math.sin(a) * 18)], dark(col, 0.85), 2)
        c.ell(80, 42, 8, 8, dark(col, 0.8), lw=0)
        c.ell(80, 42, 4, 4, light(col, 0.5), lw=0)
        c.rrect(10, 10, 150, 74, 6, None, lw=1, outline=light(col, 0.5))
        label(c, 34, 30, val, 22)
        label(c, 126, 54, val, 22)
        c.save(name)
    c = C(380, 200)                                                    # Schale
    c.rrect(8, 30, 372, 192, 30, (184, 188, 194, 255), lw=7, sh=(0.2, 0.3))
    c.rrect(30, 52, 350, 172, 22, (136, 140, 148, 255), lw=4, sh=(-0.2, 0.15))
    c.line([(40, 60), (340, 60)], (110, 114, 122, 255), 4)
    c.glint(60, 42, 30, 5, 120)
    c.save("task_tray.png")
    c = C(200, 280)                                                    # Kassenbon (Textzonen bleiben frei)
    c.poly([(10, 10), (190, 10), (190, 250), (170, 270), (150, 250), (130, 270), (110, 250), (90, 270),
            (70, 250), (50, 270), (30, 250), (10, 270)], (250, 248, 238, 255), lw=5, sh=(0.02, 0.06))
    c.d.rectangle([10 * S, 10 * S, 190 * S, 30 * S], fill=(228, 222, 206, 255))
    for x in range(18, 190, 8):                                        # Perforationskante
        c.d.rectangle([x * S, 12 * S, (x + 4) * S, 14 * S], fill=(200, 194, 180, 255))
    c.rrect(56, 36, 144, 50, 3, (60, 58, 64, 255), lw=0)               # Kopfzeile "Logo"
    for y in (222, 232, 242):
        c.d.line([(30 * S, y * S), (150 * S, y * S)], fill=(206, 200, 188, 255), width=3 * S)
    c.d.line([(30 * S, 250 * S), (100 * S, 250 * S)], fill=(206, 200, 188, 255), width=3 * S)
    c.save("task_receipt.png")


def bins():
    spec = (("paper", (70, 120, 200, 255)), ("glass", (60, 150, 90, 255)), ("rest", (110, 112, 118, 255)),
            ("compost", (120, 84, 50, 255)), ("sack", (220, 190, 70, 255)))
    for key, col in spec:
        dk = dark(col, 0.78)
        c = C(170, 200)
        if key == "sack":
            c.poly([(30, 40), (140, 40), (160, 190), (10, 190)], col, lw=6, sh=(0.14, 0.26))
            c.poly([(40, 60), (130, 60), (140, 120), (30, 120)], light(col, 0.12), lw=0)   # Falte
            c.line([(60, 40), (85, 18), (110, 40)], INK, 6)
            c.line([(66, 40), (85, 24), (104, 40)], dk, 3)
            c.line([(30, 140), (150, 148)], dk, 3)
        else:
            c.poly([(20, 50), (150, 50), (138, 194), (32, 194)], col, lw=6, sh=(0.14, 0.26))
            for x in (52, 85, 118):
                c.d.line([(x * S, 72 * S), (x * S, 176 * S)], fill=dk, width=4 * S)
            c.d.line([(30 * S, 66 * S), (140 * S, 66 * S)], fill=light(col, 0.25), width=3 * S)
            c.rrect(10, 30, 160, 56, 8, dk, lw=6, sh=(0.25, 0.2))
            c.rrect(60, 22, 110, 34, 4, dk, lw=4, sh=(0.3, 0.2))                       # Deckelgriff
            c.glint(36, 40, 14, 3, 90)
        c.save(f"task_bin_{key}.png")


def trash():
    def item(name, fn):
        c = C(96, 96)
        fn(c)
        c.save(f"task_trash_{name}.png")

    def brochure(c):
        c.poly([(18, 20), (78, 14), (82, 80), (22, 84)], (240, 232, 204, 255), sh=(0.04, 0.1))
        c.rrect(28, 24, 72, 44, 2, (110, 160, 200, 255), lw=0)
        c.line([(30, 54), (70, 51)], (200, 80, 80, 255), 5)
        c.line([(30, 64), (70, 61)], (150, 150, 150, 255), 3)
        c.line([(30, 72), (58, 70)], (150, 150, 150, 255), 3)

    def ticket(c):
        c.rrect(12, 30, 84, 66, 6, (250, 214, 120, 255), sh=(0.05, 0.12))
        c.line([(60, 32), (60, 64)], INK, 2)
        c.rrect(20, 38, 52, 44, 1, (200, 150, 60, 255), lw=0)
        c.rrect(20, 50, 44, 56, 1, (200, 150, 60, 255), lw=0)
        c.ell(72, 48, 6, 6, (230, 90, 70, 255), lw=2)

    def bottle(c):
        c.poly([(40, 8), (56, 8), (56, 30), (68, 44), (68, 88), (28, 88), (28, 44), (40, 30)], (110, 190, 140, 255), sh=(0.1, 0.22))
        c.rrect(38, 4, 58, 14, 3, (60, 120, 80, 255), lw=3)
        c.rrect(32, 54, 64, 74, 3, (240, 240, 230, 255), lw=2)
        c.glint(36, 60, 3, 16, 130)

    def jar(c):
        c.rrect(26, 30, 70, 88, 10, (190, 220, 230, 255), sh=(0.08, 0.2))
        c.rrect(24, 18, 72, 32, 4, (200, 90, 60, 255), sh=(0.25, 0.2))
        c.rrect(32, 48, 64, 72, 2, (240, 210, 140, 255), lw=2)
        c.glint(34, 40, 3, 20, 120)

    def wrapper(c):
        c.poly([(14, 40), (30, 30), (66, 32), (84, 44), (70, 62), (28, 64)], (200, 90, 180, 255), sh=(0.15, 0.25))
        c.poly([(8, 34), (14, 40), (28, 64), (10, 60)], (170, 70, 150, 255), lw=4)
        c.poly([(84, 44), (92, 36), (90, 66), (70, 62)], (170, 70, 150, 255), lw=4)
        c.line([(34, 40), (66, 42)], (240, 200, 240, 255), 4)

    def apple(c):
        c.ell(48, 26, 16, 12, (222, 62, 52, 255), sh=(0.15, 0.25))
        c.rrect(42, 32, 54, 70, 4, (240, 230, 190, 255), sh=(0.05, 0.15))
        c.ell(48, 76, 16, 12, (222, 62, 52, 255), sh=(0.15, 0.25))
        c.line([(48, 14), (52, 6)], (90, 60, 30, 255), 3)
        c.ell(56, 8, 5, 3, (100, 170, 70, 255), lw=2)

    def peel(c):
        cx, cy = 48, 8
        outer = [(cx + 42 * math.cos(math.radians(a)), cy + 62 * math.sin(math.radians(a))) for a in range(20, 161, 10)]
        inner = [(cx + 34 * math.cos(math.radians(a)), cy + 44 * math.sin(math.radians(a))) for a in range(150, 29, -10)]
        c.poly(outer + inner, (244, 212, 70, 255), sh=(0.12, 0.25))
        c.line([(cx + 38 * math.cos(math.radians(a)), cy + 54 * math.sin(math.radians(a))) for a in range(40, 141, 10)], (214, 176, 40, 255), 4)
        c.ell(outer[0][0], outer[0][1], 5, 5, (90, 70, 40, 255), lw=3)
        c.ell(outer[-1][0], outer[-1][1], 4, 4, (90, 70, 40, 255), lw=3)

    def egg(c):
        c.poly([(20, 60), (34, 30), (48, 44), (60, 26), (76, 58), (48, 80)], (240, 232, 214, 255), sh=(0.06, 0.2))
        c.poly([(28, 58), (40, 44), (48, 54), (58, 40), (68, 58), (48, 70)], (250, 220, 120, 255), lw=0)

    def leaves(c):
        c.ell(40, 46, 24, 14, (120, 170, 70, 255), sh=(0.15, 0.25))
        c.line([(18, 46), (62, 46)], (80, 130, 50, 255), 2)
        c.ell(58, 58, 20, 12, (160, 150, 60, 255), sh=(0.15, 0.25))
        c.line([(40, 58), (76, 58)], (120, 110, 40, 255), 2)

    def can(c):
        c.rrect(28, 18, 68, 84, 8, (186, 62, 62, 255), shx=(0.25, 0.3))
        c.d.rectangle([30 * S, 40 * S, 66 * S, 52 * S], fill=(230, 230, 230, 255))
        c.rrect(28, 16, 68, 26, 3, (190, 194, 200, 255), lw=3, sh=(0.3, 0.2))
        c.ell(48, 20, 8, 3, (110, 114, 120, 255), lw=0)

    def carton(c):
        c.poly([(26, 30), (70, 30), (70, 86), (26, 86)], (230, 230, 240, 255), sh=(0.06, 0.18))
        c.poly([(26, 30), (48, 12), (70, 30)], (90, 150, 210, 255), sh=(0.2, 0.2))
        c.rrect(34, 44, 62, 70, 2, (90, 150, 210, 255), lw=2)
        c.ell(48, 56, 8, 8, (240, 240, 250, 255), lw=0)

    for n, f in (("brochure", brochure), ("ticket", ticket), ("bottle", bottle), ("jar", jar), ("wrapper", wrapper),
                 ("apple", apple), ("peel", peel), ("egg", egg), ("leaves", leaves), ("can", can), ("carton", carton)):
        item(n, f)


def lever_container():
    c = C(360, 300)
    c.rrect(20, 60, 300, 290, 12, (88, 114, 100, 255), lw=7, sh=(0.14, 0.24))
    for x in (80, 160, 240):
        c.d.line([(x * S, 90 * S), (x * S, 270 * S)], fill=(64, 86, 74, 255), width=6 * S)
        c.d.line([((x + 4) * S, 90 * S), ((x + 4) * S, 270 * S)], fill=(120, 150, 132, 255), width=2 * S)
    c.rrect(10, 40, 310, 76, 8, (64, 86, 74, 255), lw=7, sh=(0.25, 0.2))
    for x in range(40, 300, 40):
        c.rivet(x, 58, 4, (120, 150, 132, 255))
    c.rrect(200, 120, 280, 180, 6, (232, 200, 80, 255), lw=5, sh=(0.1, 0.2))      # Warnschild
    c.poly([(240, 130), (270, 172), (210, 172)], INK, lw=0)
    c.poly([(240, 140), (262, 168), (218, 168)], (232, 200, 80, 255), lw=0)
    c.line([(240, 150), (240, 160)], INK, 4)
    c.ell(240, 165, 2, 2, INK, lw=0)
    c.save("task_container.png")
    c = C(70, 230)                                                    # Hebel, Drehpunkt unten (Kontrakt y = 210)
    c.rrect(26, 30, 44, 210, 8, (70, 74, 82, 255), lw=5, shx=(0.3, 0.3))
    c.ell(35, 30, 26, 26, (206, 50, 50, 255), lw=6, sh=(0.25, 0.3))
    c.glint(28, 20, 8, 5, 130, rot=35)
    c.ell(35, 210, 14, 14, (96, 102, 110, 255), lw=5, sh=(0.25, 0.3))
    c.ell(35, 210, 4, 4, INK, lw=0)
    c.save("task_lever.png")


def fuses():
    c = C(560, 400)
    # Kontrakt: Schlitze bei (90 + k*126, 90 + r*110)
    c.rrect(6, 6, 554, 394, 20, (78, 84, 92, 255), lw=7, sh=(0.16, 0.22))
    c.rrect(26, 26, 534, 374, 12, (46, 50, 56, 255), lw=4, sh=(0.06, 0.1))
    for x in (40, 520):
        for y in (40, 360):
            c.screw(x, y, 6, STEEL_L, rot=45)
    for r in range(3):
        for k in range(4):
            x, y = 90 + k * 126, 90 + r * 110
            c.rrect(x - 34, y - 48, x + 34, y + 48, 8, (26, 28, 32, 255), lw=4)
            c.rrect(x - 30, y - 44, x + 30, y + 44, 6, None, lw=2, outline=(70, 76, 84, 255))
            c.rrect(x + 40, y - 6, x + 56, y + 6, 2, (200, 200, 190, 255), lw=2)   # kleines Etikett
            c.line([(x + 43, y), (x + 53, y)], (120, 120, 116, 255), 2)
    c.save("task_fusebox.png")
    for name, glass, cap, glow in (("task_fuse_ok.png", (250, 200, 90, 255), BRASS, True),
                                   ("task_fuse_dead.png", (58, 54, 50, 255), (120, 110, 90, 255), False),
                                   ("task_fuse_new.png", (170, 230, 250, 255), (222, 222, 228, 255), False)):
        c = C(64, 100)
        c.rrect(10, 16, 54, 84, 10, glass, lw=5, shx=(0.25, 0.3))
        c.rrect(8, 4, 56, 20, 4, cap, lw=5, sh=(0.3, 0.3))
        c.rrect(8, 80, 56, 96, 4, cap, lw=5, sh=(0.3, 0.3))
        if "dead" in name:
            c.line([(20, 30), (44, 70)], INK, 5)
            c.ell(28, 56, 8, 6, (30, 28, 26, 255), lw=0)                    # Russfleck
        else:
            c.line([(32, 22), (28, 50), (36, 78)], (255, 255, 255, 210), 3)
        c.glint(18, 40, 3, 18, 110)
        c.save(name)


def switch():
    c = C(180, 280)
    c.rrect(10, 10, 170, 270, 16, (206, 206, 212, 255), lw=7, sh=(0.12, 0.2))
    c.rrect(56, 60, 124, 220, 12, (70, 74, 82, 255), lw=5, sh=(-0.1, 0.1))
    c.rrect(64, 68, 116, 212, 8, (40, 42, 48, 255), lw=0)
    for x, y in ((28, 28), (152, 28), (28, 252), (152, 252)):
        c.screw(x, y, 7, STEEL_L, rot=20)
    c.ell(90, 40, 8, 8, (70, 170, 90, 255), lw=3, sh=(0.3, 0.3))
    c.ell(90, 240, 8, 8, (200, 60, 50, 255), lw=3, sh=(0.3, 0.3))
    label(c, 128, 40, "ON", 18)
    label(c, 128, 240, "OFF", 18)
    c.save("task_switch_plate.png")
    c = C(60, 150)                                                    # Kipphebel, Drehpunkt unten (Kontrakt y = 140)
    c.rrect(22, 20, 38, 140, 8, (64, 68, 76, 255), lw=5, shx=(0.3, 0.3))
    c.ell(30, 22, 20, 20, (240, 190, 60, 255), lw=6, sh=(0.25, 0.3))
    c.glint(24, 14, 6, 4, 140, rot=35)
    c.save("task_switch_lever.png")


def patch():
    c = C(84, 84)
    c.ell(42, 42, 34, 34, (44, 46, 52, 255), lw=6, sh=(0.2, 0.2))
    c.ell(42, 42, 26, 26, (30, 32, 36, 255), lw=0)
    c.ell(42, 42, 14, 14, (10, 10, 12, 255), lw=0)
    for k in range(3):
        a = math.radians(90 + k * 120)
        c.ell(42 + math.cos(a) * 20, 42 + math.sin(a) * 20, 4, 4, (200, 170, 90, 255), lw=2)
    c.save("task_socket.png")
    c = C(90, 70)
    c.rrect(6, 14, 64, 56, 10, (240, 180, 50, 255), lw=6, sh=(0.2, 0.3))
    c.rrect(60, 26, 86, 44, 4, (196, 196, 204, 255), lw=4, sh=(0.3, 0.3))
    c.line([(16, 24), (40, 24)], (255, 224, 140, 255), 3)
    c.line([(14, 32), (14, 42)], INK, 4)
    c.save("task_plug.png")


def light_tiles():
    c = C(120, 120)
    c.rrect(4, 4, 116, 116, 14, (36, 40, 52, 255), lw=5, sh=(0.1, 0.16))
    c.rrect(10, 10, 110, 110, 10, None, lw=2, outline=(60, 66, 84, 255))
    for x, y in ((16, 16), (104, 16), (16, 104), (104, 104)):
        c.ell(x, y, 3, 3, (90, 96, 116, 255), lw=0)
    c.save("task_tile_bg.png")
    # Kontrakt: Lichtstaebe reichen exakt bis zur Kantenmitte, Stab weiss (Code faerbt ein)
    rod = WHITE
    shapes = {"straight": [((0, 60), (120, 60))],
              "corner": [((60, 60), (120, 60)), ((60, 60), (60, 120))],
              "tee": [((0, 60), (120, 60)), ((60, 60), (60, 120))],
              "cross": [((0, 60), (120, 60)), ((60, 0), (60, 120))]}
    for name, segs in shapes.items():
        c = C(120, 120)
        for a, b in segs:
            c.line([a, b], (40, 40, 44, 255), 28)
        for a, b in segs:
            c.line([a, b], (208, 208, 214, 255), 16)
        c.ell(60, 60, 13, 13, (208, 208, 214, 255), lw=0)
        for a, b in segs:
            c.line([a, b], rod, 10)
        c.ell(60, 60, 10, 10, rod, lw=0)
        c.save(f"task_tile_{name}.png")
    c = C(120, 120)                                                   # Projektor (Lichtquelle)
    c.rrect(10, 30, 90, 90, 10, (72, 76, 86, 255), lw=6, sh=(0.2, 0.25))
    c.rrect(20, 40, 60, 80, 6, (52, 56, 64, 255), lw=3)
    for y in (48, 60, 72):
        c.line([(26, y), (54, y)], (96, 102, 112, 255), 3)
    c.poly([(90, 40), (116, 30), (116, 90), (90, 80)], (206, 206, 212, 255), lw=5, sh=(0.2, 0.3))
    c.rrect(104, 42, 114, 78, 3, (255, 244, 200, 255), lw=0)
    c.glow(114, 60, 10, 24, (255, 240, 180, 150), 5)
    c.save("task_light_source.png")


# ------------------------------------------------------------------ restliche Bausteine

def glyph(c, cx, cy, k, s=1.0, col=INK, w=7):
    """Zehn Hieroglyphen (k = 0..9), kraeftige Linien und gefuellte Flaechen."""
    L = lambda pts, ww=w: c.line([(cx + x * s, cy + y * s) for x, y in pts], col, ww * s)
    F = lambda pts: c.poly([(cx + x * s, cy + y * s) for x, y in pts], col, lw=0)
    E = lambda x, y, rx, ry, fill=False, ww=w: c.ell(cx + x * s, cy + y * s, rx * s, ry * s, col if fill else None, lw=int(ww * s), outline=col)
    if k == 0:   # Auge (Udjat)
        E(0, 0, 22, 11); E(0, 0, 7, 7, True)
        L([(-22, 0), (-30, 6)], w - 1); L([(6, 11), (10, 24)], w - 1); L([(10, 24), (18, 20)], w - 2)
    elif k == 1:   # Ankh
        E(0, -13, 9, 11); L([(0, -2), (0, 26)]); L([(-14, 4), (14, 4)])
    elif k == 2:   # Vogel (Ibis)
        F([(-20, 10), (-8, -6), (6, -8), (10, 2), (2, 14), (-16, 16)])
        L([(6, -8), (14, -18), (24, -20)], w - 1); E(14, -18, 3, 3, True)
        L([(-6, 14), (-6, 24)], w - 2); L([(2, 12), (4, 24)], w - 2)
    elif k == 3:   # Wasser
        L([(-22, -8), (-14, -15), (-6, -8), (2, -15), (10, -8), (18, -15), (24, -10)])
        L([(-22, 10), (-14, 3), (-6, 10), (2, 3), (10, 10), (18, 3), (24, 8)])
    elif k == 4:   # Sonne
        E(0, 0, 15, 15); E(0, 0, 5, 5, True)
        for a in range(0, 360, 45):
            r = math.radians(a)
            L([(math.cos(r) * 19, math.sin(r) * 19), (math.cos(r) * 26, math.sin(r) * 26)], w - 2)
    elif k == 5:   # Feder (Maat)
        F([(0, -26), (12, -12), (10, 8), (0, 20), (-10, 8), (-12, -12)])
        c.line([(cx, cy - 24 * s), (cx, cy + 26 * s)], (240, 230, 200, 255) if col == INK else (90, 70, 40, 255), 3 * s)
        L([(0, 18), (0, 28)], w - 1)
    elif k == 6:   # Schlange (Kobra)
        L([(-22, 12), (-12, 2), (-2, 12), (8, 2), (14, -10), (12, -22), (2, -22)])
        E(14, -16, 8, 9, True)
    elif k == 7:   # Schilfrohr
        L([(0, 26), (0, -8)]); F([(0, -8), (-12, -26), (0, -18), (12, -26)]); L([(-8, 6), (8, 6)], w - 2)
    elif k == 8:   # Hand
        F([(-14, 4), (14, 4), (16, 22), (-16, 22)])
        for fx in (-12, -4, 4, 12):
            L([(fx, 6), (fx, -20 if fx in (-4, 4) else -14)], w - 1)
        L([(-14, 12), (-26, 0)], w - 1)
    elif k == 9:   # Skarabaeus
        E(0, 4, 13, 15, True)
        L([(0, -10), (0, 18)], 3)
        L([(-13, -12), (-20, -22)], w - 2); L([(13, -12), (20, -22)], w - 2)
        L([(-13, 4), (-24, -2)], w - 2); L([(13, 4), (24, -2)], w - 2)
        L([(-12, 14), (-22, 22)], w - 2); L([(12, 14), (22, 22)], w - 2)


def tomb():
    # Kontrakt: Ringradien 260/190/120, Innenloch transparent, Goldglyphe (Schluessel) oben
    for i, R in enumerate((260, 190, 120)):
        size = R * 2 + 16
        c = C(size, size)
        m = size // 2
        base = SAND if i % 2 == 0 else (206, 178, 120, 255)
        c.ell(m, m + 4, R, R, (0, 0, 0, 90), lw=0)                                   # Schlagschatten
        c.ell(m, m, R, R, base, lw=7, sh=(0.1, 0.18))
        msk, md = c.mask()
        md.ellipse([(m - R) * S, (m - R) * S, (m + R) * S, (m + R) * S], fill=255)
        c.mottle(0.07, 8, seed=30 + i, mask=msk)
        c.ell(m, m, R - 8, R - 8, None, lw=3, outline=light(base, 0.4))                # Lichtkante aussen
        c.ell(m, m, R - 54, R - 54, None, lw=3, outline=dark(base, 0.8))               # Schattenkante innen
        c.ell(m, m, R - 62, R - 62, (0, 0, 0, 0), lw=6)
        c.d.ellipse([(m - R + 65) * S, (m - R + 65) * S, (m + R - 65) * S, (m + R - 65) * S], fill=(0, 0, 0, 0))
        for k in range(8):                                                             # Trennrillen
            a = math.radians(90 + k * 45 + 22.5)
            c.line([(m + math.cos(a) * (R - 58), m - math.sin(a) * (R - 58)), (m + math.cos(a) * (R - 6), m - math.sin(a) * (R - 6))], dark(base, 0.72), 4)
            c.line([(m + math.cos(a) * (R - 58) + 2, m - math.sin(a) * (R - 58)), (m + math.cos(a) * (R - 6) + 2, m - math.sin(a) * (R - 6))], light(base, 0.35), 2)
        for k in range(8):
            a = math.radians(90 + k * 45)
            gx, gy = m + math.cos(a) * (R - 31), m - math.sin(a) * (R - 31)
            if k == 0:
                c.ell(gx, gy, 25, 25, GOLD, lw=5, sh=(0.25, 0.3))
                glyph(c, gx, gy + 1, 1, 0.85, (120, 80, 20, 255))
            else:
                g = (k * 3 + i) % 10
                glyph(c, gx + 1.5, gy + 1.5, g, 0.78, light(base, 0.5))                # eingraviert: Licht unten rechts
                glyph(c, gx, gy, g, 0.78, (96, 72, 40, 255))
        c.save(f"task_tomb_ring{i}.png")
    c = C(140, 140)
    c.ell(70, 70, 60, 60, SAND_D, lw=7, sh=(0.12, 0.2))
    c.ell(70, 70, 50, 50, None, lw=3, outline=dark(SAND_D, 0.8))
    glyph(c, 72, 72, 9, 1.2, light(SAND_D, 0.5))
    glyph(c, 70, 70, 9, 1.2, (96, 72, 40, 255))
    c.save("task_tomb_center.png")
    c = C(60, 60)                                                      # Markierung oben
    c.poly([(30, 54), (8, 10), (52, 10)], GOLD, lw=5, sh=(0.2, 0.3))
    c.poly([(30, 40), (18, 16), (42, 16)], BRASS_L, lw=0)
    c.save("task_tomb_marker.png")


def cartouche():
    c = C(120, 150)
    c.rrect(8, 12, 112, 146, 50, (0, 0, 0, 80), lw=0)
    c.rrect(8, 8, 112, 142, 50, SAND, lw=6, sh=(0.12, 0.2))
    m, md = c.mask()
    md.rounded_rectangle([8 * S, 8 * S, 112 * S, 142 * S], 50 * S, fill=255)
    c.mottle(0.06, 6, seed=40, mask=m)
    c.rrect(20, 20, 100, 130, 40, (234, 212, 160, 255), lw=3, sh=(0.05, 0.1))
    c.rrect(26, 26, 94, 124, 34, None, lw=2, outline=(200, 176, 124, 255))
    c.line([(48, 134), (72, 134)], (150, 120, 70, 255), 4)                       # Kartuschenfuss
    c.save("task_cartouche.png")
    for k in range(10):
        c = C(80, 80)
        glyph(c, 40, 40, k, 1.2)
        c.save(f"task_glyph{k}.png")


def dome():
    rnd = random.Random(11)
    c = C(440, 440)
    c.ell(220, 220, 212, 212, (14, 18, 46, 255), lw=8)
    m, md = c.mask()
    md.ellipse([12 * S, 12 * S, 428 * S, 428 * S], fill=255)
    # Milchstrasse als weiches Band
    g = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.polygon(c.P([(60, 380), (120, 300), (300, 120), (400, 60), (420, 120), (330, 200), (160, 360), (100, 420)]), fill=(120, 130, 200, 60))
    g = g.filter(ImageFilter.GaussianBlur(30 * S))
    g.putalpha(Image.fromarray((np.asarray(g.getchannel(3), dtype=np.float32) * (np.asarray(m, dtype=np.float32) / 255)).astype(np.uint8)))
    c.img.alpha_composite(g)
    c.d = ImageDraw.Draw(c.img)
    c.vignette(0.3, 8, 8, 432, 432, power=3)
    for _ in range(160):
        x, y = rnd.uniform(30, 410), rnd.uniform(30, 410)
        if (x - 220) ** 2 + (y - 220) ** 2 > 196 ** 2:
            continue
        r = rnd.choice((1.2, 1.5, 2, 2, 2.5, 3.5))
        col = rnd.choice(((255, 250, 220, 255), (220, 230, 255, 255), (255, 240, 200, 255)))
        if r > 3:
            c.glow(x, y, 8, 8, col[:3] + (90,), 3)
        c.ell(x, y, r, r, col, lw=0)
    c.ell(220, 220, 212, 212, None, lw=8)
    c.ell(220, 220, 204, 204, None, lw=2, outline=(60, 70, 120, 255))
    c.save("task_sky.png")
    c = C(240, 240)                                                    # geriffelter Fokusring
    c.ell(120, 124, 112, 112, (0, 0, 0, 90), lw=0)
    c.ell(120, 120, 112, 112, (76, 80, 90, 255), lw=7, sh=(0.2, 0.25))
    for k in range(36):
        a = math.radians(k * 10)
        c.line([(120 + math.cos(a) * 88, 120 + math.sin(a) * 88), (120 + math.cos(a) * 110, 120 + math.sin(a) * 110)], (40, 42, 48, 255), 6)
        c.line([(120 + math.cos(a + 0.06) * 88, 120 + math.sin(a + 0.06) * 88), (120 + math.cos(a + 0.06) * 110, 120 + math.sin(a + 0.06) * 110)], (128, 132, 142, 255), 3)
    c.ell(120, 120, 86, 86, (0, 0, 0, 0), lw=6)
    c.d.ellipse([40 * S, 40 * S, 200 * S, 200 * S], fill=(0, 0, 0, 0))
    c.ell(120, 120, 80, 80, None, lw=6)
    c.ell(120, 120, 86, 86, None, lw=3, outline=(110, 114, 124, 255))
    c.ell(120, 18, 8, 8, GOLD, lw=3, sh=(0.3, 0.3))
    c.save("task_focus_ring.png")
    c = C(64, 64)
    c.glow(32, 32, 20, 20, (255, 240, 170, 110), 6)
    c.poly([(32, 4), (39, 25), (60, 25), (43, 38), (50, 60), (32, 47), (14, 60), (21, 38), (4, 25), (25, 25)], (255, 240, 170, 255), lw=4, sh=(0.15, 0.25))
    c.save("task_star.png")
    c = C(220, 180)
    c.rrect(6, 10, 214, 178, 12, (0, 0, 0, 90), lw=0)
    c.rrect(6, 6, 214, 174, 12, (240, 232, 206, 255), lw=6, sh=(0.05, 0.1))
    m, md = c.mask()
    md.rounded_rectangle([6 * S, 6 * S, 214 * S, 174 * S], 12 * S, fill=255)
    c.mottle(0.05, 8, seed=41, mask=m)
    for x in range(30, 200, 24):
        c.line([(x, 14), (x, 166)], (214, 204, 176, 255), 1)
    for y in range(30, 160, 24):
        c.line([(14, y), (206, y)], (214, 204, 176, 255), 1)
    c.rrect(14, 14, 206, 166, 8, None, lw=2, outline=(190, 176, 140, 255))
    c.save("task_card.png")


def valves():
    c = C(160, 160)
    red = (204, 52, 48, 255)
    c.ell(80, 80, 70, 70, red, lw=7, sh=(0.2, 0.28))
    c.ell(80, 80, 60, 60, None, lw=3, outline=(150, 36, 34, 255))
    c.d.ellipse([28 * S, 28 * S, 132 * S, 132 * S], fill=(0, 0, 0, 0))
    c.ell(80, 80, 52, 52, None, lw=6)
    for k in range(4):
        a = math.radians(k * 45)
        c.capsule((80 - math.cos(a) * 54, 80 - math.sin(a) * 54), (80 + math.cos(a) * 54, 80 + math.sin(a) * 54), 11, red, 4, sh=(0.2, 0.3))
    c.ell(80, 80, 17, 17, (156, 156, 164, 255), lw=5, sh=(0.3, 0.3))
    c.ell(80, 80, 6, 6, (90, 92, 100, 255), lw=2)
    c.glint(58, 30, 12, 6, 90, rot=30)
    c.save("task_valve.png")
    c = C(720, 520)                                                    # Rohrleitungen, transparent (Kontrakt: y 150/330, x 130..610)
    pipe, pipe_d = (124, 134, 140, 255), (94, 102, 108, 255)
    for x in (130, 250, 370, 490, 610):
        c.rrect(x - 16, 150, x + 16, 330, 12, pipe_d, lw=5, shx=(0.3, 0.3))
    for y in (150, 330):
        c.rrect(40, y - 18, 680, y + 18, 16, pipe, lw=6, sh=(0.3, 0.32))
    for x in (130, 250, 370, 490, 610):
        for y in (150, 330):
            c.rrect(x - 24, y - 24, x + 24, y + 24, 6, pipe_d, lw=5, sh=(0.25, 0.3))    # Flansche
            for bx, by in ((x - 16, y - 16), (x + 16, y - 16), (x - 16, y + 16), (x + 16, y + 16)):
                c.rivet(bx, by, 3, (160, 168, 176, 255))
    for x in (60, 660):
        c.rrect(x - 12, 126, x + 12, 174, 4, pipe_d, lw=5, sh=(0.25, 0.3))
        c.rrect(x - 12, 306, x + 12, 354, 4, pipe_d, lw=5, sh=(0.25, 0.3))
    c.save("task_pipes.png")
    c = C(200, 160)
    for x, y, r in ((60, 110, 40), (100, 70, 50), (150, 100, 38), (110, 120, 34)):
        c.glow(x, y, r + 10, r + 10, (236, 240, 244, 90), 10)
    for x, y, r in ((60, 110, 40), (100, 70, 50), (150, 100, 38), (110, 120, 34)):
        c.ell(x, y, r, r, (238, 242, 246, 220), lw=0, sh=(0.05, 0.12))
    c.save("task_steam.png")


def splice():
    c = C(130, 130)
    c.rrect(10, 20, 120, 110, 12, (62, 66, 74, 255), lw=6, sh=(0.18, 0.24))
    c.rrect(26, 36, 104, 94, 8, (206, 174, 72, 255), lw=4, sh=(0.2, 0.25))
    c.rrect(34, 44, 96, 86, 4, (176, 146, 56, 255), lw=0)
    for x, y in ((18, 28), (112, 28), (18, 102), (112, 102)):
        c.rivet(x, y, 3, STEEL_L)
    c.save("task_clamp.png")
    c = C(70, 70)
    c.ell(35, 35, 28, 28, (192, 196, 202, 255), lw=6, sh=(0.25, 0.3))
    c.ell(35, 35, 20, 20, None, lw=2, outline=(150, 154, 162, 255))
    c.line([(16, 35), (54, 35)], INK, 7)
    c.glint(24, 22, 8, 4, 120, rot=35)
    c.save("task_screw.png")
    c = C(70, 50)                                                     # Kabelende (weiss, Code faerbt ein)
    c.rrect(4, 10, 50, 40, 8, WHITE, lw=5, sh=(0.0, 0.18))
    c.rrect(46, 18, 68, 32, 3, (206, 170, 90, 255), lw=4, sh=(0.3, 0.3))
    c.line([(52, 25), (64, 25)], (150, 120, 60, 255), 2)
    c.save("task_wire_end.png")


def binoculars():
    rnd = random.Random(5)
    c = C(1600, 520)
    # Daemmerungshimmel
    arr = np.zeros((520 * S, 1600 * S, 4), dtype=np.float32)
    t = (np.arange(520 * S) / (520 * S))[:, None, None]
    top = np.array([24, 34, 70], dtype=np.float32)
    hor = np.array([230, 150, 90], dtype=np.float32)
    arr[..., :3] = top * (1 - t) ** 1.6 + hor * (1 - (1 - t) ** 1.6)
    arr[..., 3] = 255
    c.img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    c.d = ImageDraw.Draw(c.img)
    for _ in range(60):
        x, y = rnd.uniform(0, 1600), rnd.uniform(0, 160)
        c.ell(x, y, 1.5, 1.5, (255, 250, 230, 200), lw=0)
    c.glow(1180, 120, 34, 34, (255, 244, 210, 255), 2)
    c.glow(1180, 120, 60, 60, (255, 240, 200, 80), 20)
    layers = ((82, 96, 130, 255), (70, 98, 92, 255), (52, 92, 62, 255), (34, 68, 44, 255))
    for i, col in enumerate(layers):
        y0 = 190 + i * 62
        pts = [(0, 520)] + [(x, y0 + 30 * math.sin(x / (140 + i * 40) + i) + 12 * math.sin(x / 47 + i * 2)) for x in range(0, 1601, 20)] + [(1600, 520)]
        c.poly(pts, col, lw=4, sh=(0.1, 0.25))
        n = 18 + i * 12
        for _ in range(n):                                             # Tannen auf der Kammlinie
            x = rnd.uniform(0, 1600)
            base = y0 + 30 * math.sin(x / (140 + i * 40) + i) + 12 * math.sin(x / 47 + i * 2) + 8
            h = 30 + i * 18 + rnd.uniform(-8, 8)
            tcol = dark(col, 0.82)
            for k in range(3):
                yy = base - h + k * h * 0.28
                hw = (h * 0.22) * (0.55 + k * 0.28)
                c.poly([(x, yy), (x + hw, yy + h * 0.42), (x - hw, yy + h * 0.42)], tcol, lw=3 if i > 0 else 2)
    c.save("task_panorama.png")
    deer()
    img = Image.new("RGBA", (720 * S, 520 * S), (8, 8, 10, 255))       # Fernglas-Maske (Kontrakt: zwei Kreise r 150 bei x 270/450)
    d = ImageDraw.Draw(img)
    for cx in (270, 450):
        d.ellipse([(cx - 150) * S, 110 * S, (cx + 150) * S, 410 * S], fill=(0, 0, 0, 0))
    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    for cx in (270, 450):
        rd.ellipse([(cx - 150) * S, 110 * S, (cx + 150) * S, 410 * S], outline=(0, 0, 0, 140), width=14 * S)
    ring = ring.filter(ImageFilter.GaussianBlur(6 * S))
    hole = Image.new("L", img.size, 0)
    hd = ImageDraw.Draw(hole)
    for cx in (270, 450):
        hd.ellipse([(cx - 150) * S, 110 * S, (cx + 150) * S, 410 * S], fill=255)
    ring.putalpha(Image.fromarray((np.asarray(ring.getchannel(3), dtype=np.float32) * (np.asarray(hole, dtype=np.float32) / 255)).astype(np.uint8)))
    img.alpha_composite(ring)
    img = img.resize((720, 520), Image.LANCZOS)
    img.save(OUT / "task_binoc_overlay.png"); print(OUT / "task_binoc_overlay.png")


def deer():
    c = C(160, 130)
    b, bd, bl = (168, 116, 70, 255), (128, 86, 50, 255), (214, 178, 128, 255)
    # Beine (hinten dunkler)
    for x0, x1, col in ((44, 34, bd), (104, 112, bd), (52, 46, b), (96, 100, b)):
        c.capsule((x0, 84), (x1, 122), 8, col, 4, sh=(0.1, 0.25))
        c.rrect(x1 - 6, 118, x1 + 6, 127, 2, INK, lw=0)
    c.ell(76, 68, 42, 24, b, lw=5, sh=(0.16, 0.28))                                  # Rumpf
    c.poly([(34, 62), (40, 54), (46, 64)], (250, 240, 220, 255), lw=3)               # Spiegel/Schwanz
    c.ell(88, 74, 22, 12, bl, lw=0)                                                  # heller Bauch
    c.poly([(104, 56), (128, 30), (144, 40), (122, 70)], b, lw=5, sh=(0.14, 0.25))   # Hals
    c.poly([(126, 22), (152, 20), (160, 34), (152, 44), (132, 44), (122, 34)], b, lw=5, sh=(0.14, 0.25))   # Kopf
    c.ell(156, 36, 4, 3, (60, 40, 30, 255), lw=0)                                    # Nase
    c.ell(140, 30, 3, 3, INK, lw=0)                                                  # Auge
    c.glint(139, 29, 1, 1, 200)
    c.poly([(126, 20), (118, 8), (128, 14)], b, lw=4)                                # Ohr
    for x, sx in ((128, -1), (136, 1)):                                              # Geweih
        c.line([(x, 20), (x + sx * 6, 4)], INK, 6)
        c.line([(x, 20), (x + sx * 6, 4)], bl, 3)
        c.line([(x + sx * 3, 12), (x + sx * 11, 8)], INK, 5)
        c.line([(x + sx * 3, 12), (x + sx * 11, 8)], bl, 2)
        c.line([(x + sx * 5, 6), (x + sx * 2, 0)], INK, 4)
        c.line([(x + sx * 5, 6), (x + sx * 2, 0)], bl, 2)
    c.save("task_deer.png")


def band_parts():
    c = C(280, 280)
    dial_face(c, 140, 140, green_pil=(270 - 34, 270 + 34))                # gruenes Band oben (Kontrakt)
    c.save("task_gauge_band.png")
    c = C(110, 110)
    c.ell(55, 58, 48, 48, (0, 0, 0, 90), lw=0)
    c.ell(55, 55, 48, 48, (92, 96, 104, 255), lw=6, sh=(0.2, 0.3))
    c.ell(55, 55, 40, 40, (60, 64, 72, 255), lw=0)
    c.ell(55, 52, 36, 36, (214, 62, 58, 255), lw=5, sh=(0.25, 0.3))
    c.glint(42, 38, 12, 6, 130, rot=35)
    c.save("task_button.png")
    c = C(80, 420)
    c.rrect(24, 10, 56, 410, 14, (60, 64, 72, 255), lw=6, shx=(0.15, 0.25))
    c.rrect(34, 20, 46, 400, 5, (34, 36, 42, 255), lw=0)
    for y in range(40, 400, 40):
        c.line([(18, y), (24, y)], (140, 146, 156, 255), 3)
        c.line([(56, y), (62, y)], (140, 146, 156, 255), 3)
    c.save("task_slider_track.png")
    c = C(420, 80)
    c.rrect(10, 24, 410, 56, 14, (60, 64, 72, 255), lw=6, sh=(0.15, 0.25))
    c.rrect(20, 34, 400, 46, 5, (34, 36, 42, 255), lw=0)
    c.d.rectangle([250 * S, 30 * S, 330 * S, 50 * S], fill=(70, 170, 90, 255))   # Choke: gruenes Feld (Kontrakt x 250..330)
    c.d.rectangle([250 * S, 30 * S, 330 * S, 34 * S], fill=(120, 210, 130, 255))
    for x in range(40, 410, 40):
        c.line([(x, 18), (x, 24)], (140, 146, 156, 255), 3)
    c.save("task_choke_track.png")
    c = C(110, 70)
    c.rrect(6, 10, 104, 68, 14, (0, 0, 0, 90), lw=0)
    c.rrect(6, 6, 104, 64, 14, (232, 192, 62, 255), lw=6, sh=(0.2, 0.3))
    for x in (40, 55, 70):
        c.line([(x, 22), (x, 48)], (170, 130, 30, 255), 4)
        c.line([(x + 3, 22), (x + 3, 48)], (250, 226, 130, 255), 2)
    c.save("task_slider_knob.png")
    for name, fn in (("flywheel", 0), ("sawblade", 1), ("propeller", 2)):
        c = C(300, 300)
        if fn == 0:
            c.ell(150, 154, 140, 140, (0, 0, 0, 90), lw=0)
            c.ell(150, 150, 140, 140, (88, 94, 104, 255), lw=8, sh=(0.2, 0.28))
            c.ell(150, 150, 122, 122, None, lw=3, outline=(62, 66, 74, 255))
            c.ell(150, 150, 110, 110, (60, 64, 72, 255), lw=5, sh=(0.1, 0.15))
            for k in range(6):
                a = math.radians(k * 60)
                c.capsule((150 + math.cos(a) * 30, 150 + math.sin(a) * 30), (150 + math.cos(a) * 108, 150 + math.sin(a) * 108), 16, (124, 130, 140, 255), 4, sh=(0.2, 0.3))
            for k in range(12):
                a = math.radians(k * 30 + 15)
                c.rivet(150 + math.cos(a) * 128, 150 + math.sin(a) * 128, 4, STEEL_L)
            c.ell(150, 150, 28, 28, BRASS, lw=6, sh=(0.25, 0.3))
            c.ell(150, 150, 9, 9, BRASS_D, lw=3)
        elif fn == 1:
            pts = []
            for k in range(48):
                a = math.radians(k * 7.5)
                r = 140 if k % 2 == 0 else 120
                pts.append((150 + math.cos(a) * r, 150 + math.sin(a) * r))
            c.poly(pts, (204, 210, 218, 255), lw=5, sh=(0.15, 0.25))
            c.ell(150, 150, 100, 100, None, lw=3, outline=(160, 166, 176, 255))
            c.ell(150, 150, 70, 70, None, lw=3, outline=(160, 166, 176, 255))
            for k in range(4):
                a = math.radians(k * 90 + 45)
                c.ell(150 + math.cos(a) * 85, 150 + math.sin(a) * 85, 10, 10, (0, 0, 0, 0), lw=4)
                c.d.ellipse([(150 + math.cos(a) * 85 - 8) * S, (150 + math.sin(a) * 85 - 8) * S, (150 + math.cos(a) * 85 + 8) * S, (150 + math.sin(a) * 85 + 8) * S], fill=(0, 0, 0, 0))
            c.ell(150, 150, 30, 30, (124, 130, 140, 255), lw=5, sh=(0.25, 0.3))
            c.ell(150, 150, 10, 10, (60, 64, 72, 255), lw=3)
            c.glint(100, 80, 30, 10, 90, rot=35)
        else:
            for k in range(3):
                a = math.radians(k * 120)
                x, y = 150 + math.cos(a) * 80, 150 + math.sin(a) * 80
                g = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
                gd = ImageDraw.Draw(g)
                gd.ellipse([(150 - 70) * S, (150 + 80 - 34) * S, (150 + 70) * S, (150 + 80 + 34) * S], fill=(62, 124, 186, 255), outline=INK, width=6 * S)
                gd.ellipse([(150 - 50) * S, (150 + 80 - 20) * S, (150 + 50) * S, (150 + 80 + 20) * S], outline=(90, 160, 220, 255), width=3 * S)
                g = g.rotate(-(k * 120 - 90), center=(150 * S, 150 * S), resample=Image.BICUBIC)
                c.img.alpha_composite(g)
                c.d = ImageDraw.Draw(c.img)
            c.ell(150, 150, 30, 30, (204, 204, 210, 255), lw=6, sh=(0.25, 0.3))
            c.ell(150, 150, 12, 12, (140, 144, 152, 255), lw=3)
        c.save(f"task_{name}.png")
    c = C(300, 260)                                                    # Aggregat
    c.rrect(10, 44, 290, 254, 16, (0, 0, 0, 90), lw=0)
    c.rrect(10, 40, 290, 250, 16, (214, 122, 42, 255), lw=7, sh=(0.16, 0.24))
    c.rrect(40, 70, 180, 220, 10, (72, 76, 86, 255), lw=5, sh=(0.1, 0.16))
    for y in range(90, 210, 20):
        c.d.line([(50 * S, y * S), (170 * S, y * S)], fill=(110, 116, 124, 255), width=4 * S)
        c.d.line([(50 * S, (y + 4) * S), (170 * S, (y + 4) * S)], fill=(48, 52, 60, 255), width=2 * S)
    c.rrect(200, 10, 240, 60, 6, (88, 94, 104, 255), lw=5, shx=(0.3, 0.3))    # Auspuff
    c.rrect(200, 80, 270, 130, 8, (40, 42, 48, 255), lw=5)                    # Tank/Anzeige
    c.ell(235, 105, 16, 16, CREAM, lw=3)
    c.line([(235, 105), (244, 96)], (206, 42, 42, 255), 3)
    c.rrect(200, 150, 270, 220, 8, (232, 192, 62, 255), lw=5, sh=(0.15, 0.25))   # Warnaufkleber
    c.poly([(235, 160), (262, 208), (208, 208)], INK, lw=0)
    c.poly([(235, 170), (254, 204), (216, 204)], (232, 192, 62, 255), lw=0)
    c.line([(235, 180), (235, 194)], INK, 4)
    c.ell(235, 200, 2, 2, INK, lw=0)
    c.save("task_generator.png")
    c = C(90, 60)
    c.rrect(6, 10, 84, 50, 18, (44, 44, 48, 255), lw=6, sh=(0.25, 0.25))
    c.rrect(14, 18, 76, 26, 4, (90, 90, 96, 255), lw=0)
    c.save("task_cord.png")


def fill_parts():
    c = C(180, 240)                                                    # Kanister (Kontrakt: Fenster x 50..130, y 70..210 transparent)
    c.rrect(20, 40, 160, 230, 18, (144, 150, 158, 255), lw=7, sh=(0.16, 0.24))
    c.rrect(60, 14, 120, 44, 8, (112, 118, 126, 255), lw=6, sh=(0.25, 0.25))
    c.rrect(76, 4, 104, 20, 4, (206, 62, 52, 255), lw=4, sh=(0.3, 0.3))       # Verschluss
    c.rrect(30, 50, 150, 64, 3, (120, 126, 134, 255), lw=0)
    c.d.rounded_rectangle([50 * S, 70 * S, 130 * S, 210 * S], 10 * S, fill=(0, 0, 0, 0), outline=INK, width=5 * S)
    for y in (105, 140, 175):                                          # Fuellmarken
        c.line([(130, y), (144, y)], INK, 3)
    c.save("task_can.png")
    c = C(120, 360)                                                    # Schauglas (innen transparent)
    c.rrect(20, 10, 100, 350, 30, (0, 0, 0, 0), lw=7)
    c.rrect(28, 18, 34, 342, 3, (255, 255, 255, 70), lw=0)             # Glaskante
    c.rrect(10, 4, 110, 30, 8, (88, 94, 104, 255), lw=6, sh=(0.25, 0.3))
    c.rrect(10, 330, 110, 356, 8, (88, 94, 104, 255), lw=6, sh=(0.25, 0.3))
    c.save("task_sightglass.png")
    c = C(16, 16)
    c.d.rectangle([0, 0, 16 * S, 16 * S], fill=WHITE)
    c.save("task_white.png")
    c = C(220, 160)                                                    # Wasserhahn / Fass
    c.rrect(10, 20, 150, 70, 12, (152, 158, 166, 255), lw=6, sh=(0.3, 0.3))
    c.rrect(110, 60, 150, 120, 8, (152, 158, 166, 255), lw=6, shx=(0.3, 0.3))
    c.rrect(104, 116, 156, 130, 4, (120, 126, 134, 255), lw=5, sh=(0.25, 0.3))
    c.rrect(40, 4, 80, 24, 6, (206, 52, 48, 255), lw=5, sh=(0.25, 0.3))
    c.rrect(56, 20, 64, 34, 2, (100, 104, 112, 255), lw=3)
    c.ell(20, 45, 8, 8, (120, 126, 134, 255), lw=3, sh=(0.3, 0.3))
    c.save("task_tap.png")
    c = C(360, 400)                                                    # Kessel
    c.rrect(20, 40, 340, 390, 40, (62, 66, 74, 255), lw=8, shx=(0.2, 0.28))
    for y in (130, 250):
        c.rrect(30, y, 330, y + 18, 6, (52, 56, 64, 255), lw=4, sh=(0.25, 0.25))
        for x in range(50, 330, 40):
            c.rivet(x, y + 9, 4, STEEL_L)
    c.ell(180, 40, 150, 30, (88, 94, 104, 255), lw=7, sh=(0.3, 0.2))
    c.rrect(60, 120, 170, 230, 20, (206, 92, 42, 255), lw=6, sh=(0.1, 0.2))    # Feuerklappe
    c.rrect(80, 140, 150, 210, 12, (60, 26, 16, 255), lw=4)
    c.glow(115, 190, 30, 20, (255, 160, 60, 200), 8)
    c.poly([(95, 205), (105, 170), (115, 195), (125, 160), (135, 200), (140, 208)], (255, 190, 70, 255), lw=0)
    c.rrect(100, 224, 130, 236, 3, (120, 126, 134, 255), lw=3)                  # Griff
    c.ell(270, 300, 30, 30, (88, 94, 104, 255), lw=6, sh=(0.25, 0.3))          # Manometer-Stutzen
    c.ell(270, 300, 20, 20, CREAM, lw=3)
    c.line([(270, 300), (280, 288)], (206, 42, 42, 255), 3)
    c.save("task_boiler.png")


def path_parts():
    c = C(720, 520)
    c.rrect(40, 34, 680, 494, 20, (0, 0, 0, 100), lw=0)
    c.rrect(40, 30, 680, 490, 20, (232, 218, 176, 255), lw=8, sh=(0.04, 0.08))
    m, md = c.mask()
    md.rounded_rectangle([44 * S, 34 * S, 676 * S, 486 * S], 20 * S, fill=255)
    c.mottle(0.06, 12, seed=9, mask=m)
    rnd = random.Random(9)
    for k in range(7):                                                 # Hoehenlinien
        cx, cy = rnd.uniform(120, 600), rnd.uniform(120, 420)
        for r in range(1, 4):
            c.ell(cx, cy, 40 * r + rnd.uniform(-8, 8), 22 * r + rnd.uniform(-5, 5), None, lw=1, outline=(196, 176, 130, 255))
    stream = [(60, 120 + 40 * math.sin(x / 60)) for x in range(60, 661, 30)]
    stream = [(x, 100 + 30 * math.sin(x / 70) + 60 * (x / 700)) for x in range(60, 661, 30)]
    c.line(stream, (130, 170, 210, 255), 8)
    c.line(stream, (170, 204, 236, 255), 4)
    for _ in range(36):
        x, y = rnd.uniform(80, 640), rnd.uniform(90, 450)
        c.poly([(x, y - 16), (x + 10, y + 4), (x - 10, y + 4)], (110, 146, 96, 220), lw=2)
        c.poly([(x, y - 10), (x + 6, y + 2), (x - 6, y + 2)], (140, 176, 116, 220), lw=0)
    c.rrect(52, 60, 668, 478, 12, None, lw=2, outline=(190, 168, 120, 255))
    c.ell(630, 440, 26, 26, (240, 230, 200, 255), lw=3)               # Kompassrose
    c.poly([(630, 418), (636, 440), (630, 462), (624, 440)], (200, 60, 50, 255), lw=2)
    c.poly([(608, 440), (630, 434), (652, 440), (630, 446)], (120, 110, 90, 255), lw=2)
    c.save("task_trailmap.png")
    c = C(70, 90)
    c.line([(20, 84), (20, 8)], INK, 6)
    c.line([(21, 82), (21, 10)], (200, 200, 206, 255), 2)
    c.poly([(22, 10), (62, 22), (22, 36)], (222, 62, 52, 255), lw=4, sh=(0.15, 0.25))
    c.save("task_flag.png")
    c = C(60, 60)
    c.ell(30, 32, 22, 22, (0, 0, 0, 90), lw=0)
    c.ell(30, 30, 22, 22, (72, 142, 222, 255), lw=6, sh=(0.25, 0.3))
    c.ell(30, 30, 8, 8, (240, 246, 255, 255), lw=0)
    c.save("task_marker.png")


def click_parts():
    c = C(90, 70)                                                      # Motte
    for dx in (-1, 1):
        c.poly([(45, 35), (45 + dx * 40, 8), (45 + dx * 42, 40), (45 + dx * 24, 60)], (196, 182, 156, 255), lw=5, sh=(0.1, 0.2))
        c.ell(45 + dx * 26, 26, 6, 5, (120, 100, 80, 255), lw=2)
        c.line([(45 + dx * 10, 40), (45 + dx * 34, 50)], (150, 130, 100, 255), 2)
    c.rrect(38, 16, 52, 60, 7, (120, 100, 80, 255), lw=4, sh=(0.15, 0.25))
    for dx in (-1, 1):
        c.line([(45, 18), (45 + dx * 10, 6)], INK, 2)
    c.save("task_moth.png")
    c = C(720, 520)                                                    # Galerie
    frame_wood(c)
    c.rrect(26, 26, 694, 494, 14, (104, 38, 44, 255), lw=4)
    m, md = c.mask()
    md.rounded_rectangle([28 * S, 28 * S, 692 * S, 492 * S], 14 * S, fill=255)
    c.mottle(0.07, 20, seed=13, mask=m)
    for y in range(60, 400, 34):                                       # Damast-Andeutung
        for x in range(60, 680, 60):
            c.ell(x + (y // 34 % 2) * 30, y, 9, 5, (118, 48, 54, 255), lw=0)
    c.vignette(0.4, 26, 26, 694, 494)
    c.rrect(30, 400, 690, 490, 6, (86, 62, 44, 255), lw=4, sh=(0.12, 0.2))   # Wandtaefelung
    for x in range(60, 690, 120):
        c.rrect(x, 412, x + 100, 478, 4, None, lw=3, outline=(62, 42, 30, 255))
    c.line([(30, 400), (690, 400)], (130, 96, 66, 255), 6)
    c.line([(30, 62), (690, 62)], (150, 118, 80, 255), 5)               # Bilderschiene
    for x, w, kind in ((70, 180, 0), (300, 150, 1), (500, 160, 2)):
        h = w * 1.2
        c.rrect(x + 4, 96, x + w + 4, 96 + h, 6, (0, 0, 0, 110), lw=0)
        c.rrect(x, 90, x + w, 90 + h, 6, BRASS, lw=6, sh=(0.2, 0.3))
        c.rrect(x + 6, 96, x + w - 6, 84 + h, 3, None, lw=2, outline=BRASS_D)
        ix0, iy0, ix1, iy1 = x + 14, 104, x + w - 14, 76 + h
        if kind == 0:                                                   # Landschaft
            c.rrect(ix0, iy0, ix1, iy1, 3, (150, 180, 214, 255), lw=3)
            c.poly([(ix0, iy1), (ix0, iy0 + 90), (ix0 + 60, iy0 + 40), (ix0 + 110, iy0 + 80), (ix1, iy0 + 50), (ix1, iy1)], (70, 110, 80, 255), lw=0)
            c.poly([(ix0, iy1), (ix0, iy1 - 50), (ix0 + 80, iy1 - 70), (ix1, iy1 - 40), (ix1, iy1)], (54, 84, 60, 255), lw=0)
            c.ell(ix1 - 30, iy0 + 26, 12, 12, (255, 240, 200, 255), lw=0)
        elif kind == 1:                                                 # Portraet
            c.rrect(ix0, iy0, ix1, iy1, 3, (60, 44, 40, 255), lw=3)
            cx = (ix0 + ix1) / 2
            c.ell(cx, iy1 - 10, 44, 40, (90, 70, 110, 255), lw=0)
            c.ell(cx, iy0 + 60, 24, 30, (222, 190, 160, 255), lw=0)
            c.ell(cx, iy0 + 40, 26, 16, (70, 50, 40, 255), lw=0)
        else:                                                           # Stillleben
            c.rrect(ix0, iy0, ix1, iy1, 3, (180, 140, 90, 255), lw=3)
            c.rrect(ix0, iy1 - 50, ix1, iy1, 2, (110, 70, 40, 255), lw=0)
            c.ell(ix0 + 50, iy1 - 60, 24, 18, (200, 60, 50, 255), lw=0)
            c.ell(ix0 + 90, iy1 - 66, 20, 16, (230, 180, 60, 255), lw=0)
            c.rrect(ix0 + 100, iy0 + 40, ix0 + 124, iy1 - 52, 6, (60, 100, 130, 255), lw=0)
        c.glint(ix0 + 20, iy0 + 20, 40, 14, 30, rot=35)
    c.save("task_gallery.png")
    c = C(260, 260)
    c.glow(130, 130, 110, 110, (255, 240, 180, 80), 14)
    c.glow(130, 130, 70, 70, (255, 244, 200, 90), 12)
    c.save("task_torch.png")
    c = C(720, 520)                                                    # Lichtung bei Nacht
    frame_wood(c, (48, 36, 30, 255))
    arr = np.zeros((520 * S, 720 * S, 4), dtype=np.float32)
    t = (np.arange(520 * S) / (520 * S))[:, None, None]
    arr[..., :3] = np.array([18, 26, 52], dtype=np.float32) * (1 - t) + np.array([40, 70, 60], dtype=np.float32) * t
    arr[..., 3] = 255
    sky = Image.fromarray(arr.astype(np.uint8), "RGBA")
    mk = Image.new("L", c.img.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([26 * S, 26 * S, 694 * S, 494 * S], 14 * S, fill=255)
    c.img.paste(sky, (0, 0), mk)
    c.d = ImageDraw.Draw(c.img)
    rnd = random.Random(4)
    for _ in range(50):
        c.ell(rnd.uniform(40, 680), rnd.uniform(36, 150), 1.5, 1.5, (255, 250, 230, 220), lw=0)
    c.glow(600, 90, 60, 60, (255, 244, 200, 90), 20)
    c.ell(600, 90, 30, 30, (250, 244, 214, 255), lw=0)
    for mx, my, mr in ((590, 80, 6), (608, 98, 4), (598, 102, 3)):    # Krater
        c.ell(mx, my, mr, mr, (222, 214, 184, 255), lw=0)
    for i, (y0, col) in enumerate(((150, (24, 48, 40, 255)), (200, (30, 62, 44, 255)))):
        for x in range(30, 700, 24):
            h = rnd.uniform(60, 120) + i * 30
            for k in range(3):
                yy = y0 + 40 - h + k * h * 0.28
                hw = (h * 0.24) * (0.55 + k * 0.28)
                c.poly([(x, yy), (x + hw, yy + h * 0.44), (x - hw, yy + h * 0.44)], col, lw=3)
    c.rrect(30, 250, 690, 490, 6, (56, 96, 56, 255), lw=0)              # Wiese
    m, md = c.mask()
    md.rectangle([30 * S, 250 * S, 690 * S, 490 * S], fill=255)
    c.mottle(0.1, 12, seed=17, mask=m)
    c.shade(m, 0.08, 0.25)
    for _ in range(80):                                                # Grasbueschel
        x, y = rnd.uniform(40, 680), rnd.uniform(260, 480)
        for dx in (-5, 0, 5):
            c.line([(x, y), (x + dx, y - 10 - rnd.uniform(0, 6))], (78, 128, 72, 255), 2)
    c.line([(30, 250), (690, 250)], (74, 120, 70, 255), 4)
    c.rrect(26, 26, 694, 494, 14, None, lw=4)
    c.vignette(0.35, 26, 26, 694, 494)
    c.save("task_clearing.png")
    c = C(150, 100)                                                    # Wildschwein
    b, bd = (98, 72, 56, 255), (66, 48, 38, 255)
    for x0, x1, col in ((40, 34, bd), (104, 110, bd), (50, 46, b), (94, 98, b)):
        c.capsule((x0, 76), (x1, 94), 8, col, 4, sh=(0.1, 0.25))
        c.rrect(x1 - 5, 91, x1 + 5, 98, 2, INK, lw=0)
    c.rrect(20, 30, 120, 82, 26, b, lw=5, sh=(0.16, 0.28))
    c.poly([(30, 34), (60, 24), (100, 26), (116, 36), (100, 40), (60, 38)], bd, lw=3)   # Borstenkamm
    for x in range(40, 110, 12):
        c.line([(x, 30), (x + 3, 22)], bd, 3)
    c.poly([(110, 40), (146, 54), (144, 72), (112, 74)], b, lw=5, sh=(0.14, 0.25))    # Kopf/Ruessel
    c.ell(146, 63, 6, 7, (150, 110, 100, 255), lw=3)                                  # Ruesselscheibe
    c.ell(122, 52, 3, 3, INK, lw=0)
    c.poly([(118, 40), (112, 26), (126, 34)], b, lw=3)                                # Ohr
    c.line([(136, 70), (140, 60)], (240, 234, 220, 255), 4)                           # Hauer
    c.line([(20, 46), (10, 40)], bd, 3)                                               # Schwaenzchen
    c.save("task_boar.png")
    c = C(100, 120)                                                    # Eule
    b, bl = (150, 120, 90, 255), (200, 176, 140, 255)
    c.ell(50, 66, 40, 50, b, lw=6, sh=(0.14, 0.26))
    c.poly([(16, 40), (10, 70), (24, 100)], (120, 92, 66, 255), lw=4)                 # Fluegel
    c.poly([(84, 40), (90, 70), (76, 100)], (120, 92, 66, 255), lw=4)
    c.ell(50, 84, 22, 24, bl, lw=0)                                                   # Bauch
    for y in (76, 88, 100):
        for x in (40, 50, 60):
            c.poly([(x, y), (x + 5, y + 6), (x - 5, y + 6)], (170, 146, 110, 255), lw=0)
    c.poly([(18, 30), (26, 10), (38, 28)], b, lw=4)                                   # Federohren
    c.poly([(82, 30), (74, 10), (62, 28)], b, lw=4)
    c.ell(50, 48, 30, 22, bl, lw=0)                                                   # Gesichtsschleier
    for x in (34, 66):
        c.ell(x, 50, 14, 14, (250, 240, 200, 255), lw=4)
        c.ell(x, 50, 8, 8, (240, 190, 60, 255), lw=0)
        c.ell(x, 50, 4, 4, INK, lw=0)
        c.glint(x - 2, 47, 2, 1.5, 220)
    c.poly([(46, 60), (54, 60), (50, 72)], GOLD, lw=3)
    for x in (40, 60):
        c.line([(x, 112), (x - 5, 118)], (240, 190, 60, 255), 3)
        c.line([(x, 112), (x + 5, 118)], (240, 190, 60, 255), 3)
    c.save("task_owl.png")


def select_parts():
    c = C(70, 200)                                                     # Probenroehrchen (weiss, wird eingefaerbt)
    c.rrect(14, 10, 56, 190, 20, WHITE, lw=6, shx=(0.0, 0.14))
    c.rrect(8, 6, 62, 30, 6, (204, 204, 210, 255), lw=5, sh=(0.25, 0.2))
    c.rrect(20, 40, 24, 170, 2, (255, 255, 255, 255), lw=0)
    for y in (70, 100, 130, 160):
        c.line([(46, y), (54, y)], (180, 180, 190, 255), 2)
    c.save("task_vial.png")
    c = C(50, 220)                                                     # Teststreifen
    c.rrect(6, 6, 44, 214, 6, (250, 250, 246, 255), lw=5, sh=(0.0, 0.1))
    c.rrect(12, 150, 38, 206, 3, (236, 234, 226, 255), lw=2)
    c.save("task_strip.png")
    for k, name in enumerate(("dino", "mummy", "planet", "gem", "painting")):
        c = C(110, 110)
        c.rrect(6, 10, 104, 108, 16, (0, 0, 0, 90), lw=0)
        c.rrect(6, 6, 104, 104, 16, (240, 232, 206, 255), lw=5, sh=(0.06, 0.12))
        c.rrect(14, 14, 96, 96, 10, None, lw=2, outline=(206, 190, 150, 255))
        if name == "dino":
            c.poly([(20, 80), (40, 50), (70, 44), (86, 30), (94, 40), (78, 56), (84, 86), (70, 86), (60, 66), (44, 70), (34, 86)], (120, 160, 90, 255), lw=4, sh=(0.15, 0.25))
            c.ell(86, 36, 2, 2, INK, lw=0)
        elif name == "mummy":
            c.rrect(38, 18, 72, 94, 16, SAND, lw=4, sh=(0.1, 0.2))
            for y in (36, 50, 64, 78):
                c.line([(40, y), (70, y - 6)], SAND_D, 3)
            c.ell(50, 30, 2, 2, INK, lw=0); c.ell(60, 30, 2, 2, INK, lw=0)
        elif name == "planet":
            c.ell(55, 55, 26, 26, (220, 150, 80, 255), lw=4, sh=(0.2, 0.3))
            c.line([(34, 50), (76, 46)], (190, 120, 60, 255), 4)
            c.line([(36, 62), (74, 64)], (190, 120, 60, 255), 3)
            c.arc([14, 42, 96, 68], 160, 380, INK, 5)
            c.arc([16, 44, 94, 66], 170, 370, (230, 200, 150, 255), 2)
        elif name == "gem":
            c.poly([(55, 18), (86, 46), (55, 94), (24, 46)], (90, 170, 220, 255), lw=4, sh=(0.2, 0.3))
            c.poly([(40, 46), (70, 46), (55, 80)], (140, 200, 240, 255), lw=0)
            c.line([(24, 46), (86, 46)], (60, 130, 190, 255), 2)
        else:
            c.rrect(24, 24, 86, 86, 4, BRASS, lw=4, sh=(0.2, 0.3))
            c.rrect(32, 32, 78, 78, 2, (150, 180, 214, 255), lw=2)
            c.poly([(32, 78), (32, 60), (50, 46), (66, 62), (78, 54), (78, 78)], (70, 110, 80, 255), lw=0)
            c.ell(66, 42, 5, 5, (255, 240, 200, 255), lw=0)
        c.save(f"task_icon_{name}.png")
    c = C(120, 200)                                                    # Audioguide
    c.rrect(14, 14, 106, 194, 18, (0, 0, 0, 90), lw=0)
    c.rrect(14, 10, 106, 190, 18, (52, 56, 64, 255), lw=6, sh=(0.16, 0.22))
    c.rrect(28, 28, 92, 96, 8, (120, 200, 220, 255), lw=4, sh=(0.1, 0.2))
    for i in range(6):                                                  # Pegelbalken
        h = (10, 22, 16, 30, 18, 12)[i]
        c.rrect(36 + i * 9, 86 - h, 41 + i * 9, 88, 1, (40, 110, 130, 255), lw=0)
    for y in (126, 156):
        c.ell(44, y, 12, 12, (124, 128, 136, 255), lw=3, sh=(0.3, 0.3)); c.ell(76, y, 12, 12, (124, 128, 136, 255), lw=3, sh=(0.3, 0.3))
    c.poly([(40, 121), (48, 126), (40, 131)], INK, lw=0)
    c.rrect(72, 122, 80, 130, 1, INK, lw=0)
    c.rrect(50, 4, 70, 14, 3, (90, 94, 102, 255), lw=3)                # Kopfhoereranschluss
    c.save("task_audioguide.png")
    c = C(260, 120)                                                    # Ladestation / Dock
    c.rrect(10, 24, 250, 114, 14, (0, 0, 0, 90), lw=0)
    c.rrect(10, 20, 250, 110, 14, (88, 94, 104, 255), lw=6, sh=(0.18, 0.24))
    c.rrect(80, 36, 180, 60, 6, (22, 22, 26, 255), lw=4)
    c.rrect(84, 40, 176, 48, 2, (48, 48, 54, 255), lw=0)
    for i in range(3):
        c.ell(40 + i * 18, 88, 5, 5, (70, 170, 90, 255) if i < 2 else (200, 60, 50, 255), lw=2, sh=(0.3, 0.3))
    c.rrect(190, 76, 236, 98, 4, (40, 42, 48, 255), lw=3)
    c.line([(196, 87), (230, 87)], (120, 200, 220, 255), 3)
    c.save("task_dock.png")
    c = C(200, 150)                                                    # Wildkamera-Foto (Nachtsicht)
    c.rrect(6, 6, 194, 144, 8, (44, 66, 54, 255), lw=5, sh=(0.1, 0.16))
    rnd = random.Random(21)
    for x in (40, 90, 150, 120, 60):
        h = rnd.uniform(70, 100)
        c.poly([(x, 120 - h), (x + 22, 120), (x - 22, 120)], (32, 50, 40, 255), lw=0)
    c.rrect(10, 116, 190, 140, 3, (28, 44, 34, 255), lw=0)
    c.rrect(10, 128, 190, 140, 3, (20, 22, 24, 255), lw=0)
    for i in range(8):
        c.rrect(16 + i * 12, 131, 24 + i * 12, 137, 1, (180, 200, 190, 255), lw=0)
    c.ell(178, 22, 8, 8, (200, 60, 50, 255), lw=2)
    c.mottle(0.12, 3, seed=22)
    c.save("task_photo.png")
    c = C(70, 90)
    c.poly([(6, 6), (50, 6), (64, 20), (64, 84), (6, 84)], (42, 92, 172, 255), lw=5, sh=(0.15, 0.25))
    c.rrect(16, 60, 54, 78, 3, (206, 174, 72, 255), lw=3, sh=(0.2, 0.2))
    for x in range(20, 52, 8):
        c.line([(x, 62), (x, 76)], (150, 120, 50, 255), 2)
    c.rrect(14, 14, 44, 30, 2, (240, 240, 244, 255), lw=2)
    c.line([(18, 20), (40, 20)], (100, 100, 110, 255), 2)
    c.save("task_sdcard.png")
    c = C(300, 240)
    c.rrect(10, 14, 290, 194, 14, (0, 0, 0, 90), lw=0)
    c.rrect(10, 10, 290, 190, 14, (52, 56, 64, 255), lw=7, sh=(0.16, 0.22))
    c.rrect(30, 30, 270, 170, 6, (90, 170, 200, 255), lw=4, sh=(0.1, 0.25))
    c.rrect(40, 40, 260, 56, 3, (60, 120, 150, 255), lw=0)
    for i, w in enumerate((120, 80, 150, 60, 100)):
        c.rrect(44, 66 + i * 18, 44 + w, 74 + i * 18, 2, (200, 236, 250, 255), lw=0)
    c.rrect(200, 120, 250, 160, 4, (240, 246, 250, 255), lw=2)
    c.rrect(100, 190, 200, 230, 6, (88, 94, 104, 255), lw=5, sh=(0.25, 0.25))
    c.rrect(60, 226, 240, 238, 4, (70, 74, 82, 255), lw=4, sh=(0.25, 0.25))
    c.ell(150, 180, 4, 4, (70, 170, 90, 255), lw=0)
    c.save("task_pc.png")
    c = C(130, 200)                                                    # Stempelkarte (Namensfeld um y 40 bleibt frei)
    c.rrect(8, 12, 122, 196, 8, (0, 0, 0, 80), lw=0)
    c.rrect(8, 8, 122, 192, 8, (246, 236, 200, 255), lw=5, sh=(0.04, 0.08))
    c.rrect(8, 8, 122, 24, 8, (200, 80, 60, 255), lw=0)
    c.rrect(8, 18, 122, 24, 0, (200, 80, 60, 255), lw=0)
    c.d.rectangle([8 * S, 8 * S, 122 * S, 24 * S], outline=INK, width=3 * S)
    for y in (70, 100, 130, 160):
        c.d.line([(20 * S, y * S), (110 * S, y * S)], fill=(200, 190, 160, 255), width=3 * S)
        c.d.rectangle([20 * S, (y + 8) * S, 40 * S, (y + 18) * S], fill=(210, 200, 170, 255))
    c.rrect(52, 78, 84, 92, 2, (120, 160, 210, 255), lw=0)              # Stempel
    c.rrect(52, 108, 84, 122, 2, (120, 160, 210, 255), lw=0)
    c.save("task_timecard.png")
    c = C(300, 300)                                                    # Stechuhr
    c.ell(150, 154, 140, 140, (0, 0, 0, 90), lw=0)
    c.ell(150, 150, 140, 140, (88, 62, 42, 255), lw=8, sh=(0.16, 0.24))
    m, md = c.mask()
    md.ellipse([10 * S, 10 * S, 290 * S, 290 * S], fill=255)
    c.grain(10, 10, 290, 290, 0.08, seed=31, freq=0.35, mask=m)
    c.ell(150, 150, 126, 126, (60, 40, 26, 255), lw=0)
    c.ell(150, 150, 118, 118, (250, 246, 232, 255), lw=5, sh=(0.04, 0.08))
    for k in range(60):
        a = math.radians(k * 6)
        big = k % 5 == 0
        c.line([(150 + math.sin(a) * (100 if big else 106), 150 - math.cos(a) * (100 if big else 106)), (150 + math.sin(a) * 112, 150 - math.cos(a) * 112)],
               INK, 7 if k % 15 == 0 else (4 if big else 2))
    for k in range(12):
        a = math.radians(k * 30)
        label(c, 150 + math.sin(a) * 78, 150 - math.cos(a) * 78, str(12 if k == 0 else k), 17, (70, 60, 60, 255))
    c.ell(150, 150, 10, 10, INK, lw=0)
    c.glint(100, 80, 44, 22, 50, rot=35)
    c.save("task_clock.png")
    c = C(20, 130)
    c.rrect(4, 4, 16, 126, 6, (40, 40, 44, 255), lw=0)
    c.poly([(10, 2), (16, 14), (4, 14)], (40, 40, 44, 255), lw=0)
    c.rrect(7, 20, 9, 110, 1, (90, 90, 96, 255), lw=0)
    c.save("task_hand.png")


def special_parts():
    c = C(110, 110)
    c.rrect(8, 8, 102, 102, 12, (62, 66, 74, 255), lw=5, sh=(0.16, 0.22))
    c.line([(24, 86), (86, 24)], (206, 232, 242, 255), 16)
    c.line([(26, 84), (84, 26)], (150, 200, 230, 255), 6)
    c.line([(28, 82), (82, 28)], (240, 250, 255, 255), 2)
    c.line([(30, 90), (90, 30)], INK, 3)
    for x, y in ((18, 18), (92, 18), (18, 92), (92, 92)):
        c.rivet(x, y, 3, STEEL_L)
    c.save("task_mirror.png")
    c = C(110, 110)
    c.rrect(10, 20, 90, 90, 10, (88, 94, 104, 255), lw=6, sh=(0.2, 0.25))
    c.rrect(20, 30, 70, 80, 6, (52, 56, 64, 255), lw=3)
    for y in (42, 55, 68):
        c.line([(26, y), (64, y)], (110, 116, 124, 255), 3)
    c.glow(92, 55, 16, 16, (255, 60, 60, 140), 6)
    c.ell(90, 55, 14, 14, (222, 52, 52, 255), lw=4, sh=(0.25, 0.3))
    c.ell(90, 55, 5, 5, (255, 200, 200, 255), lw=0)
    c.save("task_emitter.png")
    c = C(720, 520)                                                    # Steg bei Nacht
    frame_wood(c, (48, 36, 30, 255))
    arr = np.zeros((520 * S, 720 * S, 4), dtype=np.float32)
    t = (np.arange(520 * S) / (520 * S))[:, None, None]
    arr[..., :3] = np.array([16, 26, 50], dtype=np.float32) * (1 - t) + np.array([36, 58, 90], dtype=np.float32) * t
    arr[..., 3] = 255
    sky = Image.fromarray(arr.astype(np.uint8), "RGBA")
    mk = Image.new("L", c.img.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([26 * S, 26 * S, 694 * S, 494 * S], 14 * S, fill=255)
    c.img.paste(sky, (0, 0), mk)
    c.d = ImageDraw.Draw(c.img)
    rnd = random.Random(6)
    for _ in range(60):
        c.ell(rnd.uniform(40, 680), rnd.uniform(36, 200), 1.5, 1.5, (255, 250, 230, 220), lw=0)
    c.glow(520, 70, 50, 50, (255, 244, 200, 80), 20)
    c.ell(520, 70, 26, 26, (250, 244, 214, 255), lw=0)
    for mx, my, mr in ((512, 62, 5), (528, 78, 3)):
        c.ell(mx, my, mr, mr, (222, 214, 184, 255), lw=0)
    for x in range(30, 700, 30):                                       # ferne Baeume
        h = rnd.uniform(40, 80)
        c.poly([(x, 230 - h), (x + 14, 236), (x - 14, 236)], (22, 34, 40, 255), lw=0)
    c.rrect(30, 232, 690, 300, 0, (30, 52, 80, 255), lw=0)              # See
    for _ in range(40):                                                # Wellen und Mondspiegel
        x, y = rnd.uniform(50, 670), rnd.uniform(240, 296)
        c.line([(x, y), (x + rnd.uniform(14, 40), y)], (60, 90, 130, 255), 2)
    for y in range(240, 300, 8):
        c.line([(520 - 24 + rnd.uniform(-6, 6), y), (520 + 24 + rnd.uniform(-6, 6), y)], (200, 200, 180, 90), 2)
    for i, y in enumerate(range(300, 500, 34)):                        # Stegbretter
        col = mix(WOOD_D, WOOD, (i % 2) * 0.3)
        c.rrect(30, y, 690, y + 30, 4, col, lw=3, sh=(0.1, 0.22))
        m, md = c.mask()
        md.rounded_rectangle([30 * S, y * S, 690 * S, (y + 30) * S], 4 * S, fill=255)
        c.grain(30, y, 690, y + 30, 0.08, seed=50 + i, freq=0.5, mask=m)
        for x in (60, 360, 660):
            c.rivet(x, y + 15, 4, (90, 92, 96, 255))
    for x in (60, 360, 660):                                           # Pfosten
        c.rrect(x - 14, 260, x + 14, 306, 4, WOOD_D, lw=4, shx=(0.25, 0.3))
    c.rrect(26, 26, 694, 494, 14, None, lw=4)
    c.vignette(0.3, 26, 26, 694, 494)
    c.save("task_dock_night.png")
    for name, glass, glow in (("task_lantern_off.png", (58, 68, 78, 255), None), ("task_lantern_on.png", (255, 214, 110, 255), (255, 200, 90, 130))):
        c = C(120, 170)
        if glow:
            c.glow(60, 90, 58, 66, glow, 12)
        c.rrect(30, 40, 90, 140, 10, glass, lw=6, sh=(0.12, 0.2) if glow else (0.1, 0.16))
        if glow:
            c.poly([(56, 118), (60, 84), (64, 96), (60, 120)], (255, 250, 220, 255), lw=0)    # Flamme
            c.glow(60, 106, 14, 20, (255, 240, 200, 160), 6)
        c.poly([(24, 44), (60, 14), (96, 44)], (54, 58, 66, 255), lw=6, sh=(0.2, 0.25))
        c.rrect(24, 136, 96, 156, 4, (54, 58, 66, 255), lw=5, sh=(0.25, 0.25))
        c.line([(60, 40), (60, 140)], INK, 3)
        c.line([(30, 90), (90, 90)], INK, 3)
        c.ell(60, 12, 6, 6, (80, 84, 92, 255), lw=3)                    # Aufhaengering
        c.glint(40, 60, 4, 14, 90 if glow else 50)
        c.save(name)
    c = C(200, 110)
    c.rrect(8, 24, 192, 104, 10, (0, 0, 0, 90), lw=0)
    c.rrect(8, 20, 192, 100, 10, (206, 62, 52, 255), lw=6, sh=(0.14, 0.24))
    c.rrect(8, 20, 40, 100, 6, (92, 72, 52, 255), lw=4, sh=(0.1, 0.2))        # Reibflaeche
    for y in range(28, 96, 6):
        c.line([(12, y), (36, y + 2)], (70, 52, 36, 255), 2)
    c.rrect(60, 34, 176, 86, 6, (240, 220, 150, 255), lw=3)                    # Etikett
    c.ell(118, 60, 14, 14, (206, 62, 52, 255), lw=3)
    c.poly([(118, 48), (124, 58), (118, 68), (112, 58)], (255, 200, 80, 255), lw=0)
    c.save("task_matchbox.png")
    c = C(40, 150)                                                     # Streichholz (Kontrakt: Drehpunkt y 132, Kuppe oben)
    c.rrect(14, 30, 26, 146, 4, (232, 202, 152, 255), lw=4, shx=(0.1, 0.25))
    c.ell(20, 26, 10, 14, (206, 52, 48, 255), lw=4, sh=(0.25, 0.3))
    c.glint(17, 20, 3, 4, 120)
    c.save("task_match.png")
    c = C(60, 90)
    c.glow(30, 46, 24, 34, (255, 160, 40, 110), 8)
    c.poly([(30, 4), (48, 44), (40, 80), (20, 80), (12, 44)], (255, 160, 40, 255), lw=4, sh=(0.1, 0.1))
    c.poly([(30, 30), (38, 56), (30, 76), (22, 56)], (255, 230, 120, 255), lw=0)
    c.poly([(30, 48), (34, 62), (30, 72), (26, 62)], (255, 250, 210, 255), lw=0)
    c.save("task_flame.png")
    c = C(560, 360)                                                    # Ansauggitter
    c.rrect(8, 8, 552, 352, 16, (88, 94, 104, 255), lw=7, sh=(0.16, 0.22))
    c.rrect(26, 26, 534, 334, 8, (30, 34, 40, 255), lw=4)
    for x in range(40, 540, 34):
        c.rrect(x - 5, 30, x + 5, 330, 3, (110, 116, 126, 255), lw=3, shx=(0.3, 0.3))
    for x, y in ((18, 18), (542, 18), (18, 342), (542, 342)):
        c.screw(x, y, 7, STEEL_L, rot=45)
    c.save("task_grate.png")
    c = C(110, 60)
    c.line([(8, 40), (60, 30), (102, 16)], INK, 14)
    c.line([(60, 30), (80, 50)], INK, 11)
    c.line([(8, 40), (60, 30), (102, 16)], (112, 78, 48, 255), 10)
    c.line([(60, 30), (80, 50)], (112, 78, 48, 255), 7)
    c.line([(12, 38), (58, 29), (98, 17)], (150, 108, 70, 255), 3)
    c.ell(40, 22, 7, 4, (120, 150, 70, 255), lw=2)
    c.save("task_twig.png")
    c.save("task_trash_twig.png")
    c = C(130, 160)                                                    # Fangglas
    c.rrect(20, 34, 110, 150, 18, (200, 230, 240, 150), lw=6, sh=(0.05, 0.1))
    c.rrect(28, 44, 36, 140, 3, (255, 255, 255, 120), lw=0)
    c.rrect(14, 16, 116, 38, 6, (172, 122, 72, 255), lw=5, sh=(0.25, 0.25))
    for x in range(20, 112, 8):
        c.line([(x, 20), (x, 34)], (140, 96, 56, 255), 2)
    c.save("task_jar.png")


# ------------------------------------------------------------------ Sabotagen und Welt

def sabotage_parts():
    # Handscanner (Alarmanlage / Loeschpumpe): Stahlrahmen, leuchtende Glasplatte, Handumriss
    c = C(300, 340)
    c.rrect(10, 10, 290, 330, 26, STEEL, lw=7, sh=(0.18, 0.28))
    c.rrect(34, 34, 266, 306, 16, (30, 70, 80, 255), lw=5)
    c.glow(150, 170, 110, 120, (80, 220, 230, 90), 18)
    hand = [(96, 280), (96, 180), (82, 120), (92, 112), (110, 160), (112, 92), (126, 88), (132, 150), (140, 76), (156, 76),
            (158, 150), (168, 92), (182, 96), (180, 160), (196, 128), (210, 136), (196, 200), (190, 280)]
    c.poly(hand, None, lw=5, outline=(150, 240, 245, 255))
    for x, y in ((24, 24), (276, 24), (24, 316), (276, 316)):
        c.screw(x, y, 7)
    c.glint(90, 60, 50, 12, 70, rot=-10)
    c.save("task_scanner.png")
    # Tastenfeld-Taste und Anzeige
    c = C(110, 100)
    c.rrect(8, 8, 102, 92, 16, (214, 216, 222, 255), lw=6, sh=(0.25, 0.35))
    c.glint(40, 26, 24, 7, 120)
    c.save("task_key.png")
    c = C(380, 100)
    c.rrect(6, 6, 374, 94, 12, STEEL_D, lw=6)
    c.rrect(22, 20, 358, 80, 6, (30, 60, 40, 255), lw=4)
    c.glint(120, 30, 90, 6, 50)
    c.save("task_display.png")
    # Bildrauschen (Monitor) und CRT-Rahmen mit durchsichtigem Schirm
    rnd = random.Random(21)
    img = Image.new("RGBA", (380, 260))
    px = img.load()
    for y in range(260):
        band = rnd.random() < 0.08
        for x in range(380):
            v = rnd.randint(40, 230) if not band else rnd.randint(170, 255)
            px[x, y] = (v, v, v, 255)
    img.save(OUT / "task_static.png")
    print(OUT / "task_static.png", img.size)
    c = C(460, 360)
    c.rrect(8, 8, 452, 330, 34, (58, 62, 70, 255), lw=8, sh=(0.18, 0.3))
    c.d.rounded_rectangle([40 * S, 40 * S, 420 * S, 300 * S], 20 * S, fill=(0, 0, 0, 0), outline=INK, width=6 * S)
    c.rrect(170, 326, 290, 354, 8, STEEL_D, lw=5)
    for x in (380, 404):
        c.ell(x, 316, 6, 6, (120, 200, 120, 255), lw=2)
    c.save("task_monitor.png")
    # Funkschuessel am Mast (Seitenansicht)
    c = C(280, 280)
    c.rrect(126, 150, 154, 270, 6, STEEL_D, lw=5, shx=(0.2, 0.3))
    c.poly([(60, 40), (230, 90), (200, 200), (40, 170)], (226, 230, 236, 255), lw=7, sh=(0.25, 0.35))
    c.line([(140, 120), (200, 118)], INK, 5)
    c.ell(204, 118, 10, 10, (220, 70, 60, 255), lw=4)
    c.save("task_dish.png")
    # Sturmholz: umgestuerzter Baum (Welt) und Handsaege
    c = C(420, 140)
    c.capsule((40, 80), (360, 70), 46, (120, 82, 50, 255), lw=6, sh=(0.2, 0.35))
    for x in range(70, 350, 40):
        c.line([(x, 62), (x + 18, 60)], (92, 60, 36, 255), 3)
    c.ell(376, 70, 26, 30, (190, 150, 100, 255), lw=6)
    c.ell(376, 70, 14, 16, (160, 120, 76, 255), lw=0)
    for bx, by, d in ((90, 50, -1), (170, 44, 1), (250, 50, -1), (300, 92, 1), (140, 100, 1)):
        c.line([(bx, by), (bx + 26 * d, by - 34 if by < 70 else by + 30)], (100, 70, 44, 255), 8)
        c.ell(bx + 30 * d, by - 40 if by < 70 else by + 36, 26, 18, (54, 104, 60, 255), lw=4, sh=(0.2, 0.3))
    c.save("task_fallen_tree.png")
    c = C(360, 110)
    c.poly([(20, 60), (250, 40), (250, 86), (20, 76)], (200, 206, 214, 255), lw=5, sh=(0.25, 0.3))
    for x in range(30, 250, 12):
        c.poly([(x, 76), (x + 6, 88), (x + 12, 76)], (200, 206, 214, 255), lw=2)
    c.rrect(246, 26, 340, 100, 22, (170, 60, 50, 255), lw=6, sh=(0.2, 0.3))
    c.d.rounded_rectangle([272 * S, 48 * S, 318 * S, 78 * S], 12 * S, fill=(0, 0, 0, 0))
    c.save("task_saw.png")
    # Regentropfen (Welt)
    c = C(12, 64)
    c.line([(6, 4), (6, 60)], (190, 210, 240, 200), 3)
    c.save("task_raindrop.png")


if __name__ == "__main__":
    sabotage_parts()
    tomb(); cartouche(); dome(); valves(); splice(); binoculars(); band_parts(); fill_parts()
    path_parts(); click_parts(); select_parts(); special_parts()
    close_button()
    museum_panel(); museum_dino(); museum_dust(); museum_brush()
    wald_panel(); pump_body(); pump_handle(); gauge(); needle(); lamps(); water()
    steel_panel(); shop_panel(); money(); bins(); trash(); lever_container(); fuses(); switch(); patch(); light_tiles()
