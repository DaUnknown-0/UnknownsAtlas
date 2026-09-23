# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_icons.py - die runden Kartensymbole fuer den Lobby-Kartenwaehler (GameOptionsMapPicker).
# Stil wie die Vanilla-Symbole: flache Flaechen mit zwei bis drei Tonstufen, Glanzkanten,
# dicke dunkle Kontur, transparenter Hintergrund (Kreis und Ring bringt der Vanilla-Knopf mit).
#
#   python tools/gen_icons.py   ->  assets/icon_museum.png, assets/icon_wald.png (256 x 256)

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets"
S = 4                      # Supersampling
N = 256 * S
INK = (29, 27, 33, 255)
LW = 9 * S                 # Konturbreite


class Icon:
    def __init__(self):
        self.img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def shade(self, pts, top=0.16, bottom=0.22):
        m = Image.new("L", (N, N), 0)
        ImageDraw.Draw(m).polygon(self.P(pts), fill=255)
        m = np.asarray(m, dtype=np.float32) / 255.0
        rows = np.nonzero(m.max(axis=1) > 0)[0]
        if rows.size == 0:
            return
        t = np.clip((np.arange(N) - rows[0]) / max(1, rows[-1] - rows[0]), 0, 1)[:, None]
        li = (top * np.clip(1 - 2.4 * t, 0, 1) * m)[..., None]
        da = (bottom * np.clip(2.4 * t - 1.4, 0, 1) * m)[..., None]
        arr = np.asarray(self.img).astype(np.float32)
        arr[..., :3] += (255 - arr[..., :3]) * li - arr[..., :3] * da
        self.img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        self.d = ImageDraw.Draw(self.img)

    def poly(self, pts, fill, lw=LW, sh=(0.14, 0.2)):
        p = self.P(pts)
        self.d.polygon(p, fill=fill)
        if sh:
            self.shade(pts, *sh)
        if lw:
            self.d.line(p + [p[0]], fill=INK, width=lw, joint="curve")
            for x, y in p:
                r = lw / 2
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=INK)

    def rect(self, x0, y0, x1, y1, fill, lw=LW, sh=(0.14, 0.2)):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, lw, sh)

    def line(self, pts, fill, w):
        self.d.line(self.P(pts), fill=fill, width=int(w * S), joint="curve")

    def glow(self, cx, cy, r, color, blur):
        g = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=color)
        self.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur * S)))
        self.d = ImageDraw.Draw(self.img)

    def save(self, name):
        img = self.img.resize((256, 256), Image.LANCZOS)
        img.save(OUT / name)
        print(OUT / name)


def museum():
    c = Icon()
    stone, shade, roof, gold = (238, 226, 194, 255), (198, 180, 140, 255), (216, 198, 154, 255), (232, 186, 74, 255)
    navy = (40, 54, 84, 255)
    # Stufen
    c.rect(34, 196, 222, 214, shade)
    c.rect(46, 180, 210, 198, stone)
    c.line([(50, 184), (206, 184)], (250, 244, 224, 255), 3)
    # dunkle Halle hinter den Saeulen
    c.rect(52, 114, 204, 182, navy, lw=0, sh=(0.0, 0.3))
    # Architrav
    c.rect(46, 96, 210, 114, roof)
    for x in range(56, 204, 12):                                          # Zahnschnitt
        c.d.rectangle([x * S, 108 * S, (x + 6) * S, 112 * S], fill=shade)
    # Saeulen mit Kanneluren und Kapitell
    for x in (58, 94, 130, 166):
        c.rect(x, 114, x + 24, 182, stone)
        for k in range(3):
            c.d.line([((x + 6 + k * 6) * S, 120 * S), ((x + 6 + k * 6) * S, 176 * S)], fill=shade, width=2 * S)
        c.d.rectangle([(x + 17) * S, 118 * S, (x + 21) * S, 178 * S], fill=shade)
        c.rect(x - 4, 112, x + 28, 120, roof, lw=6 * S)
        c.rect(x - 2, 176, x + 26, 182, roof, lw=5 * S)
    # Giebel mit Relief
    c.poly([(36, 98), (128, 40), (220, 98)], roof)
    c.poly([(70, 90), (128, 56), (186, 90)], shade, lw=6 * S, sh=(0.0, 0.1))
    c.glow(128, 76, 18, (255, 220, 120, 120), 6)
    cx, cy, r = 128 * S, 76 * S, 11 * S
    c.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=gold, outline=INK, width=6 * S)
    c.d.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], fill=(250, 220, 140, 255))
    c.save("icon_museum.png")


def forest():
    c = Icon()
    dark, green, light = (38, 104, 62, 255), (58, 146, 84, 255), (98, 186, 112, 255)
    wood, wood_d, roof = (170, 112, 62, 255), (126, 80, 42, 255), (150, 62, 48, 255)

    def pine(cx, base, h, w):
        c.rect(cx - 8, base - 4, cx + 8, base + 16, wood_d)
        for t in range(3):
            top = base - h + t * h * 0.26
            bot = base - h * 0.38 + t * h * 0.22
            half = w * (0.55 + t * 0.22)
            c.poly([(cx, top), (cx + half, bot), (cx - half, bot)], green if t % 2 == 0 else dark, sh=(0.12, 0.25))
            c.d.polygon([(cx * S, (top + 10) * S), ((cx - half + 14) * S, (bot - 6) * S), ((cx - 6) * S, (bot - 6) * S)], fill=light)

    pine(78, 196, 150, 58)
    pine(186, 186, 124, 48)
    # Blockhuette vorne
    c.rect(104, 160, 196, 214, wood)
    for y in (172, 186, 200):
        c.d.line([(108 * S, y * S), (192 * S, y * S)], fill=wood_d, width=5 * S)
        c.d.line([(108 * S, (y - 4) * S), (192 * S, (y - 4) * S)], fill=(206, 150, 96, 255), width=2 * S)
    c.poly([(94, 164), (150, 124), (206, 164)], roof, sh=(0.2, 0.25))
    c.line([(100, 160), (150, 128), (200, 160)], (190, 90, 70, 255), 3)
    c.rect(172, 130, 184, 150, wood_d, lw=6 * S)                          # Schornstein
    c.rect(136, 182, 160, 214, wood_d)
    c.d.ellipse([(154) * S, 196 * S, 158 * S, 200 * S], fill=(220, 190, 120, 255))
    c.glow(179, 182, 16, (255, 214, 120, 160), 6)
    c.rect(170, 174, 188, 190, (255, 220, 130, 255), lw=6 * S, sh=(0.0, 0.15))
    c.d.line([(179 * S, 176 * S), (179 * S, 188 * S)], fill=INK, width=2 * S)
    c.d.line([(172 * S, 182 * S), (186 * S, 182 * S)], fill=INK, width=2 * S)
    c.save("icon_wald.png")


if __name__ == "__main__":
    museum()
    forest()
