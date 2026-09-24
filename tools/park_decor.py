# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_decor.py - Ausstattung des Moonlight Carnival im Bodenbild (User 24.09.: "Gehe nochmal jeden Raum
# durch und verbessere die Grafik").
#
# Alles hier liegt flach im Bodenbild oder auf den Nordwand-Stirnseiten: keine neuen Kollider, Konsolen,
# Vents und Wege bleiben, wo sie waren. Drei Durchgaenge, aufgerufen aus park_floor.render:
#   void(F, walk)          dunkle Parklandschaft zwischen den Gebaeuden (Baumkronen, Zeltdaecher, Zaeune,
#                          Lichterketten) - vor dem Weg-Fuellen, die Wege stanzen sie wieder aus
#   rooms(F, walk, rooms)  je Bereich Bodenmalerei, Flecken, Teppiche, Markierungen, Kleinkram
#   walls(F, walk)         Wanddeko auf den Nordwaenden (Wimpel, Schilder, Poster, Werkzeugwand)

import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

import park_geo as G
import park_layout as L

INK = (18, 14, 22, 255)
RED = (176, 52, 60, 255)
CREAM = (226, 210, 176, 255)
GOLD = (220, 176, 70, 255)
BULB = (255, 226, 150, 255)


def _font(px):
    try:
        return ImageFont.truetype("arialbd.ttf", max(6, int(px)))
    except OSError:
        return ImageFont.load_default()


class Pen:
    """Zeichnen in Weltmetern auf das Bodenbild (RGBA-Mischung)."""

    def __init__(self, F):
        self.F = F
        self.ppm = F.ppm
        self.d = ImageDraw.Draw(F.img, "RGBA")

    def P(self, x, y):
        return self.F.P(x, y)

    def w(self, m):
        return max(1, int(round(m * self.ppm)))

    def poly(self, pts, fill=None, outline=None, width=0.04):
        self.d.polygon([self.P(*p) for p in pts], fill=fill)
        if outline:
            q = [self.P(*p) for p in pts]
            self.d.line(q + [q[0]], fill=outline, width=self.w(width), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0.04):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, width)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=0.04):
        a, b = self.P(cx - rx, cy + ry), self.P(cx + rx, cy - ry)
        self.d.ellipse([a, b], fill=fill, outline=outline, width=self.w(width) if outline else 0)

    def ring(self, cx, cy, r, width, fill):
        a, b = self.P(cx - r, cy + r), self.P(cx + r, cy - r)
        self.d.ellipse([a, b], outline=fill, width=self.w(width))

    def line(self, pts, fill, width=0.04):
        self.d.line([self.P(*p) for p in pts], fill=fill, width=self.w(width), joint="curve")

    def text(self, x, y, s, size_m, fill, anchor="mm"):
        self.d.text(self.P(x, y), s, font=_font(size_m * self.ppm), fill=fill, anchor=anchor)

    def star(self, cx, cy, r0, r1, fill, outline=None, n=5, rot=90):
        pts = []
        for k in range(n * 2):
            a = math.radians(rot + k * 180 / n)
            r = r0 if k % 2 == 0 else r1
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        self.poly(pts, fill, outline, 0.03)

    def soft(self, draw_fn, blur_m, alpha=255):
        """Weiche Ebene (Pfuetzen, Lichtschein, Frost): draw_fn(ImageDraw, Pen-P) auf eigener Ebene, verwischt."""
        layer = Image.new("RGBA", self.F.img.size, (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(layer, "RGBA"))
        layer = layer.filter(ImageFilter.GaussianBlur(blur_m * self.ppm))
        base = self.F.img.convert("RGBA")
        base.alpha_composite(layer)
        self.F.img = base.convert("RGB")
        self.d = ImageDraw.Draw(self.F.img, "RGBA")


def scatter(pen, region, n, seed, fn):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = region.bounds
    placed, tries = 0, 0
    while placed < n and tries < n * 8:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if region.contains(Point(x, y)):
            fn(pen, x, y, rnd)
            placed += 1


# ------------------------------------------------------------------ Kleinkram (verstreut)

def confetti(pen, x, y, rnd):
    col = rnd.choice(((230, 70, 90, 200), (240, 200, 70, 200), (90, 200, 200, 200), (240, 240, 230, 200), (160, 90, 210, 200)))
    a = rnd.uniform(0, math.pi)
    dx, dy = math.cos(a) * 0.05, math.sin(a) * 0.05
    pen.poly([(x - dx, y - dy), (x + dx, y + dy), (x + dx + 0.02, y + dy - 0.02), (x - dx + 0.02, y - dy - 0.02)], col)


def popcorn(pen, x, y, rnd):
    for k in range(rnd.randint(1, 3)):
        pen.ell(x + rnd.uniform(-0.06, 0.06), y + rnd.uniform(-0.05, 0.05), 0.035, 0.03, (250, 238, 200, 230), (150, 120, 70, 200), 0.01)


def ticket(pen, x, y, rnd):
    a = rnd.uniform(0, math.pi)
    c, s = math.cos(a), math.sin(a)
    pts = [(x + c * dx - s * dy, y + s * dx + c * dy) for dx, dy in ((-0.1, -0.05), (0.1, -0.05), (0.1, 0.05), (-0.1, 0.05))]
    pen.poly(pts, (236, 196, 110, 220), (120, 80, 40, 200), 0.012)


def leaf(pen, x, y, rnd):
    col = rnd.choice(((120, 80, 40, 150), (150, 100, 50, 150), (90, 70, 40, 150)))
    pen.ell(x, y, 0.06, 0.035, col)


def stain(pen, x, y, rnd, col=(10, 8, 12, 60)):
    r = rnd.uniform(0.25, 0.6)
    pen.ell(x, y, r, r * rnd.uniform(0.5, 0.8), col)
    pen.ell(x + r * 0.5, y - r * 0.2, r * 0.35, r * 0.25, col)


def drain(pen, x, y, r=0.28):
    pen.ell(x, y, r, r, (56, 58, 64, 255), INK, 0.03)
    for k in range(-2, 3):
        pen.line([(x + k * r * 0.3, y - r * 0.8), (x + k * r * 0.3, y + r * 0.8)], (26, 26, 30, 255), 0.025)


# ------------------------------------------------------------------ Parklandschaft (Void)

def void(F, walk):
    pen = Pen(F)
    rnd = random.Random(77)
    keep_out = walk.buffer(0.7)
    x0, y0, x1, y1 = L.BOUNDS
    # dunkle Baumkronen in Gruppen
    trees = []
    for _ in range(420):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if keep_out.contains(Point(x, y)):
            continue
        trees.append((x, y, rnd.uniform(0.7, 1.5)))
    trees.sort(key=lambda t: -t[1])                                     # hinten zuerst
    for x, y, r in trees:
        base = rnd.choice(((22, 34, 34), (26, 38, 36), (20, 30, 38)))
        pen.ell(x + 0.15, y - 0.2, r, r * 0.85, (6, 6, 10, 120))
        pen.ell(x, y, r, r * 0.9, base + (255,), (10, 12, 16, 255), 0.05)
        pen.ell(x - r * 0.3, y + r * 0.3, r * 0.5, r * 0.4, tuple(min(255, int(v * 1.3)) for v in base) + (255,))
    # Zeltdaecher und Budenrueckseiten dazwischen
    for _ in range(26):
        x, y = rnd.uniform(x0 + 1, x1 - 1), rnd.uniform(y0 + 1, y1 - 1)
        w = rnd.uniform(1.6, 3.0)
        if keep_out.buffer(w * 0.6).contains(Point(x, y)) or keep_out.intersects(Point(x, y).buffer(w * 0.7)):
            continue
        cols = rnd.choice((((110, 40, 50), (160, 140, 120)), ((60, 50, 100), (140, 130, 150)), ((50, 80, 90), (150, 150, 130))))
        segs = 8
        for k in range(segs):
            a0, a1 = k * 2 * math.pi / segs, (k + 1) * 2 * math.pi / segs
            pen.poly([(x, y), (x + math.cos(a0) * w / 2, y + math.sin(a0) * w / 2), (x + math.cos(a1) * w / 2, y + math.sin(a1) * w / 2)],
                     cols[k % 2] + (255,))
        pen.ell(x, y, w / 2, w / 2, None, INK, 0.05)
        pen.ell(x, y, 0.1, 0.1, GOLD)
    # Lichterketten ueber der Dunkelheit (warme Punkte), nur ausserhalb der Wege
    for _ in range(18):
        ax, ay = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        ang = rnd.uniform(0, math.pi)
        ln = rnd.uniform(4, 9)
        pts = [(ax + math.cos(ang) * ln * t, ay + math.sin(ang) * ln * t - 0.6 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
        if any(keep_out.contains(Point(p)) for p in pts):
            continue
        pen.line(pts, (30, 24, 30, 255), 0.03)
        for i, p in enumerate(pts[1::2]):
            col = ((255, 220, 140), (255, 140, 150), (150, 230, 220))[i % 3]
            pen.ell(p[0], p[1] - 0.05, 0.12, 0.12, col + (60,))
            pen.ell(p[0], p[1] - 0.05, 0.05, 0.05, col + (255,))


# ------------------------------------------------------------------ Bereiche

def R(key):
    for b in L.BUILDINGS:
        if b[0] == key:
            return b[3]
    for c in L.CLEARINGS:
        if c[0] == key:
            return c[3]
    raise KeyError(key)


def rooms(F, walk, rooms_):
    pen = Pen(F)
    area = {k: g.intersection(walk) for k, (_n, _s, g) in rooms_.items()}
    obst = unary_union([G.shape(s).buffer(0.2) for s, _k in L.OPAQUE + L.GLASS])

    # Festplatz: gemalte Manege in der Mitte, Saegemehl-Wege, Konfetti und Popcorn
    cx, cy = 0.0, 1.0
    pen.ell(cx, cy, 4.6, 3.6, (150, 110, 70, 90))
    pen.d.ellipse([pen.P(cx - 4.6, cy + 3.6), pen.P(cx + 4.6, cy - 3.6)], outline=(170, 50, 60, 255), width=pen.w(0.32))
    for k in range(36):                                               # Manegenrand rot-creme
        if k % 2:
            a0, a1 = math.degrees(k * 2 * math.pi / 36), math.degrees((k + 1) * 2 * math.pi / 36)
            pen.d.arc([pen.P(cx - 4.6, cy + 3.6), pen.P(cx + 4.6, cy - 3.6)], a0, a1, fill=CREAM, width=pen.w(0.32))
    pen.d.ellipse([pen.P(cx - 4.9, cy + 3.9), pen.P(cx + 4.9, cy - 3.9)], outline=INK, width=pen.w(0.04))
    pen.d.ellipse([pen.P(cx - 4.3, cy + 3.3), pen.P(cx + 4.3, cy - 3.3)], outline=INK, width=pen.w(0.04))
    pen.star(cx, cy + 1.5, 0.9, 0.4, (220, 176, 70, 120))
    scatter(pen, area["fairground"], 160, 1, confetti)
    scatter(pen, area["fairground"].difference(obst), 40, 2, popcorn)
    scatter(pen, area["fairground"].difference(obst), 10, 3, ticket)

    # Werkstatt: Oelflecken, gelb markierte Stellflaeche, Reifenspuren, Saegespaene
    x0, y0, x1, y1 = R("workshop")
    scatter(pen, area["workshop"].difference(obst), 7, 11, lambda p, x, y, r: stain(p, x, y, r, (8, 8, 10, 70)))
    pen.rect(x0 + 1.0, y0 + 1.0, x0 + 4.2, y0 + 4.2, None, (220, 180, 50, 200), 0.1)
    for k in range(6):
        a = x0 + 1.0 + k * 0.55
        pen.line([(a, y0 + 1.0), (a + 0.4, y0 + 1.4)], (220, 180, 50, 160), 0.08)
    for off in (0.0, 0.9):
        pen.line([(x0 + 0.6, y0 + 5.5 + off), (x0 + 3.5, y0 + 6.0 + off), (x1 - 3.0, y0 + 5.2 + off)], (10, 10, 12, 70), 0.18)
    scatter(pen, area["workshop"], 60, 12, lambda p, x, y, r: p.ell(x, y, 0.03, 0.015, (190, 160, 110, 180)))

    # Karussell: Goldring-Einlage um die Plattform, Sterne in den Ecken
    ccx, ccy, cr = L.CAROUSEL
    pen.ring(ccx, ccy, cr + 0.6, 0.12, (200, 160, 60, 255))
    pen.ring(ccx, ccy, cr + 0.9, 0.04, INK)
    x0, y0, x1, y1 = R("carousel")
    for sx, sy in ((x0 + 1.2, y0 + 1.2), (x1 - 1.2, y0 + 1.2), (x0 + 1.2, y1 - 1.2), (x1 - 1.2, y1 - 1.2)):
        pen.star(sx, sy, 0.6, 0.25, (230, 190, 80, 230), INK)
    scatter(pen, area["carousel"].difference(obst), 30, 21, confetti)

    # Autoscooter: Reifenspuren um die Bahn, Warnstreifen am Rand, Stromschild
    x0, y0, x1, y1 = R("bumpercars")
    for k in range(5):
        r = 3.2 + k * 0.25
        pen.d.arc([pen.P(-16.0 - r, -19.0 + r), pen.P(-16.0 + r, -19.0 - r)], 200 + k * 20, 320 + k * 15, fill=(8, 8, 12, 80), width=pen.w(0.15))
    for xx in (x0 + 0.4, x1 - 0.4):
        y = y0 + 0.5
        while y < y1 - 0.5:
            pen.poly([(xx - 0.15, y), (xx + 0.15, y + 0.3), (xx + 0.15, y + 0.5), (xx - 0.15, y + 0.2)], (220, 180, 50, 200))
            y += 0.8

    # Security Booth: Teppich, Kabelkanal, Schild
    x0, y0, x1, y1 = R("security")
    pen.rect(x0 + 2.0, y0 + 1.2, x1 - 1.2, y0 + 3.6, (70, 40, 50, 230), (160, 130, 60, 255), 0.06)
    pen.rect(x0 + 2.2, y0 + 1.4, x1 - 1.4, y0 + 3.4, None, (160, 130, 60, 200), 0.03)
    pen.line([(x0 + 0.6, y1 - 0.8), (x0 + 0.6, y0 + 0.8), (x1 - 1.0, y0 + 0.6)], (20, 20, 26, 220), 0.1)

    # Umspannhaus: Warnstreifen-Rahmen, Bodengitter, Kabelbuendel
    x0, y0, x1, y1 = R("substation")
    for (a0, a1, b0, b1) in ((x0 + 0.3, x1 - 0.3, y0 + 0.3, y0 + 0.5), (x0 + 0.3, x1 - 0.3, y1 - 0.5, y1 - 0.3)):
        k = 0
        xa = a0
        while xa < a1:
            pen.poly([(xa, b0), (min(a1, xa + 0.2), b0), (min(a1, xa + 0.3), b1), (min(a1, xa + 0.1), b1)],
                     (220, 180, 50, 230) if k % 2 == 0 else (30, 28, 30, 230))
            xa += 0.2
            k += 1
    pen.rect(x0 + 2.4, y0 + 1.0, x0 + 4.4, y0 + 2.4, (60, 62, 68, 255), INK, 0.04)
    for k in range(9):
        pen.line([(x0 + 2.5 + k * 0.22, y0 + 1.05), (x0 + 2.5 + k * 0.22, y0 + 2.35)], (30, 30, 34, 255), 0.04)
    for k, col in enumerate(((200, 60, 50), (60, 120, 200), (230, 190, 60))):
        pen.line([(x1 - 0.8 - k * 0.15, y1 - 0.6), (x1 - 1.6 - k * 0.15, y0 + 1.2), (x0 + 5.0, y0 + 0.9 + k * 0.12)], col + (220,), 0.06)

    # Sanitaetszelt: rotes Kreuz auf der Matte, Vorhangschiene
    x0, y0, x1, y1 = R("firstaid")
    mx, my = (x0 + x1) / 2, y0 + 5.0
    pen.rect(mx - 1.4, my - 1.4, mx + 1.4, my + 1.4, (230, 232, 228, 255), (150, 160, 160, 255), 0.05)
    pen.rect(mx - 0.35, my - 1.0, mx + 0.35, my + 1.0, (200, 50, 50, 255))
    pen.rect(mx - 1.0, my - 0.35, mx + 1.0, my + 0.35, (200, 50, 50, 255))
    pen.line([(x0 + 0.4, y1 - 3.0), (x1 - 0.4, y1 - 3.0)], (120, 130, 140, 200), 0.05)
    for k in range(8):
        xx = x0 + 0.6 + k * 0.6
        pen.ell(xx, y1 - 3.0, 0.06, 0.06, (200, 205, 210, 255), INK, 0.015)

    # Parkbuero: Teppich mit Rand, verstreute Papiere
    x0, y0, x1, y1 = R("office")
    pen.rect(x0 + 1.5, y0 + 1.5, x1 - 1.5, y1 - 2.0, (120, 40, 50, 220), (200, 160, 70, 255), 0.08)
    pen.rect(x0 + 1.8, y0 + 1.8, x1 - 1.8, y1 - 2.3, None, (200, 160, 70, 200), 0.04)
    pen.star((x0 + x1) / 2, (y0 + y1) / 2 - 0.2, 0.9, 0.38, (220, 180, 80, 200))
    scatter(pen, area["office"].difference(obst), 8, 31, lambda p, x, y, r: p.poly(
        [(x, y), (x + 0.22, y + 0.04), (x + 0.2, y + 0.3), (x - 0.02, y + 0.26)], (236, 232, 220, 230), (120, 120, 120, 180), 0.012))

    # Kuehlhaus: Frostflecken, Abfluss, Tropfspur
    x0, y0, x1, y1 = R("coldstore")
    rnd = random.Random(41)

    def frost(d):
        for _ in range(16):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            r = rnd.uniform(0.4, 1.0)
            d.ellipse([pen.P(x - r, y + r), pen.P(x + r, y - r)], fill=(240, 250, 255, 70))
    pen.soft(frost, 0.25)
    drain(pen, (x0 + x1) / 2, y0 + 3.0)

    # Musikzentrale: Teppich, Kabel zu den Lautsprechern, Noten auf dem Boden
    x0, y0, x1, y1 = R("musicbooth")
    pen.ell((x0 + x1) / 2, (y0 + y1) / 2, 2.6, 1.8, (40, 30, 50, 220), (150, 90, 160, 255), 0.06)
    for k in range(2):                                                # Kabel vom Lautsprecher zum Mischpult
        pen.line([(26.2 + k * 0.25, 13.7), (26.6 + k * 0.25, 14.6), (28.0, 14.8 + k * 0.2), (29.6, 13.5 + k * 0.1)], (18, 16, 20, 200), 0.06)
    for k, (nx, ny) in enumerate(((27.0, 17.2), (28.2, 17.8), (30.6, 17.0))):
        pen.ell(nx, ny, 0.12, 0.09, (200, 160, 220, 150))
        pen.line([(nx + 0.1, ny), (nx + 0.1, ny + 0.4)], (200, 160, 220, 150), 0.03)

    # Schiessbude: Buehne hinter der Theke (Preisregal), Huelsen und Popcorn davor
    x0, y0, x1, y1 = R("shooting")
    pen.rect(x0 + 0.5, 19.3, x1 - 0.5, y1 - 0.1, (90, 40, 40, 255), INK, 0.04)
    for k in range(int((x1 - x0 - 1.0) / 0.6)):
        px = x0 + 0.8 + k * 0.6
        col = ((230, 120, 170), (120, 190, 230), (240, 210, 90), (160, 230, 140))[k % 4]
        pen.ell(px, y1 - 0.8, 0.2, 0.22, col + (255,), INK, 0.025)          # Plueschtiere
        pen.ell(px - 0.08, y1 - 0.62, 0.07, 0.07, col + (255,), INK, 0.02)
        pen.ell(px + 0.08, y1 - 0.62, 0.07, 0.07, col + (255,), INK, 0.02)
    scatter(pen, area["shooting"].intersection(box(x0, y0, x1, 18.2)), 30, 51,
            lambda p, x, y, r: p.ell(x, y, 0.03, 0.015, (210, 170, 70, 220)))
    scatter(pen, area["shooting"].intersection(box(x0, y0, x1, 18.2)), 14, 52, popcorn)

    # Spiegelkabinett: Glanzfunken im Rautenboden
    x0, y0, x1, y1 = R("mirrors")
    scatter(pen, area["mirrors"], 40, 61, lambda p, x, y, r: p.star(x, y, 0.1, 0.03, (255, 255, 255, 170), None, 4))

    # Geisterbahn: Schiene entlang der Fahrt, Spinnweben in den Ecken, Knochenhand
    ride = L.GHOST_RIDE
    pen.line(ride, (48, 40, 58, 255), 0.5)
    for off in (-0.16, 0.16):
        pts = []
        for i in range(len(ride)):
            a = ride[max(0, i - 1)]; b = ride[min(len(ride) - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1
            pts.append((ride[i][0] - dy / n * off, ride[i][1] + dx / n * off))
        pen.line(pts, (104, 100, 118, 255), 0.05)
    x0, y0, x1, y1 = R("ghosttrain")
    for (wx, wy, sx, sy) in ((x0, y1, 1, -1), (x1, y1, -1, -1), (x0, y0, 1, 1), (x1, y0, -1, 1)):
        for k in range(5):
            a = math.radians(k * 22.5)
            pen.line([(wx, wy), (wx + sx * math.cos(a) * 1.3, wy + sy * math.sin(a) * 1.3)], (200, 200, 210, 110), 0.015)
        for r in (0.4, 0.75, 1.1):
            pts = [(wx + sx * math.cos(math.radians(k * 22.5)) * r, wy + sy * math.sin(math.radians(k * 22.5)) * r) for k in range(5)]
            pen.line(pts, (200, 200, 210, 100), 0.012)
    for (ex, ey) in ((-35.0, -1.0), (-30.0, 6.2), (-33.8, 0.5)):
        for dx in (-0.09, 0.09):
            pen.ell(ex + dx, ey, 0.06, 0.04, (140, 255, 140, 200))

    # Riesenrad-Lichtung: gepflasterter Kreis unter dem Rad, Blumenbeete, Trittsteine
    wx, wy = -0.5, 18.6
    pen.ell(wx, wy, 3.9, 3.9, (120, 112, 104, 255), INK, 0.05)
    for k in range(24):
        a0 = k * 15
        pen.d.arc([pen.P(wx - 3.9, wy + 3.9), pen.P(wx + 3.9, wy - 3.9)], a0, a0 + 7, fill=(150, 140, 128, 255), width=pen.w(0.2))
    beds(pen, R("ferriswheel"), 71)

    # Lichtturm-Lichtung: Pflasterkreis, Blumenring, Kabel
    tx, ty = 17.0, 16.4
    pen.ell(tx, ty, 2.2, 2.2, (120, 112, 104, 255), INK, 0.05)
    for k in range(16):
        a = math.radians(k * 22.5)
        pen.ell(tx + math.cos(a) * 2.6, ty + math.sin(a) * 2.6, 0.22, 0.18, ((220, 90, 120), (240, 210, 90), (200, 200, 240))[k % 3] + (255,), INK, 0.02)
    pen.line([(tx, ty - 2.2), (tx + 1.2, ty - 3.8), (tx + 3.0, ty - 4.5)], (20, 20, 24, 220), 0.07)
    beds(pen, R("lighttower"), 81)

    # Bahnhof: gelbe Sicherheitslinie am Bahnsteig, gemalte Pfeile ENTRY/EXIT
    x0, y0, x1, y1 = R("coaster")
    pen.line([(x0 + 1.5, y1 - 0.9), (x1 - 1.5, y1 - 0.9)], (230, 190, 50, 255), 0.14)
    for k in range(int((x1 - x0 - 3) / 0.5)):
        pen.ell(x0 + 1.7 + k * 0.5, y1 - 1.15, 0.05, 0.05, (230, 190, 50, 220))
    for (ax, lbl) in ((x0 + 2.5, "ENTRY"), (x1 - 2.5, "EXIT")):
        pen.text(ax, y1 - 2.0, lbl, 0.45, (230, 200, 120, 200))
    for k in range(3):                                               # Wartegang aus Seilen
        yy = y0 + 2.0 + k * 1.2
        pen.line([(x0 + 1.5, yy), (x0 + 5.5, yy)], (200, 40, 50, 200), 0.05)
        for px in (x0 + 1.5, x0 + 3.5, x0 + 5.5):
            pen.ell(px, yy, 0.09, 0.09, GOLD, INK, 0.02)

    # Haupteingang: Mosaikstern, WELCOME, Ticketschnipsel
    x0, y0, x1, y1 = R("maingate")
    mx, my = (x0 + x1) / 2, y0 + 2.6
    pen.star(mx, my, 1.4, 0.6, (236, 196, 80, 255), INK)
    pen.star(mx, my, 0.8, 0.35, (200, 60, 70, 255))
    pen.text(mx, my + 1.95, "WELCOME", 0.55, (240, 225, 190, 220))
    scatter(pen, area["maingate"], 18, 91, ticket)

    # Wildwasserbahn: Pfuetzen und Spritzer am Kanal, Seilpfosten
    x0, y0, x1, y1 = R("logflume")
    rnd2 = random.Random(101)

    def puddles(d):
        for _ in range(10):
            x, y = rnd2.uniform(x0 + 1, x1 - 1), rnd2.choice((rnd2.uniform(-11.5, -9.8), rnd2.uniform(-7.2, -6.5)))
            r = rnd2.uniform(0.3, 0.8)
            d.ellipse([pen.P(x - r, y + r * 0.5), pen.P(x + r, y - r * 0.5)], fill=(90, 150, 200, 80))
    pen.soft(puddles, 0.06)
    for yy in (-9.75, -7.25):
        x = 21.8
        while x < 36.8:
            if not (24.0 < x < 26.5 or 31.5 < x < 34.0):
                pen.ell(x, yy, 0.08, 0.08, (120, 80, 50, 255), INK, 0.02)
            x += 1.0

    # Wege: Konfetti, Laub, Popcorn, gelegentlich ein Kanaldeckel
    rest = walk.difference(unary_union([g for _n, _s, g in rooms_.values()]))
    scatter(pen, rest, 180, 201, confetti)
    scatter(pen, rest, 60, 202, leaf)
    scatter(pen, rest, 20, 203, popcorn)
    scatter(pen, rest.buffer(-0.6), 5, 204, lambda p, x, y, r: drain(p, x, y, 0.3))


def beds(pen, rect, seed):
    """Blumenbeete in den Ecken einer Lichtung."""
    x0, y0, x1, y1 = rect
    rnd = random.Random(seed)
    for (cx, cy) in ((x0 + 2.2, y0 + 2.2), (x1 - 2.2, y0 + 2.2), (x0 + 2.2, y1 - 2.2), (x1 - 2.2, y1 - 2.2)):
        pen.ell(cx, cy, 1.0, 0.8, (60, 44, 34, 255), (30, 24, 20, 255), 0.04)
        for _ in range(12):
            fx, fy = cx + rnd.uniform(-0.8, 0.8), cy + rnd.uniform(-0.6, 0.6)
            col = rnd.choice(((230, 90, 120), (240, 210, 90), (210, 210, 250), (240, 150, 60)))
            pen.ell(fx, fy, 0.09, 0.09, col + (255,), INK, 0.015)


# ------------------------------------------------------------------ Wanddeko (Nordwand-Stirnseiten)

def walls(F, walk):
    """Wimpelketten, Schilder und Poster auf den sichtbaren Nordwaenden (0,9 m ueber der Wandlinie)."""
    pen = Pen(F)

    def pennants(x0, x1, y, cols):
        pts = [(x0 + (x1 - x0) * t, y + 0.62 - 0.15 * math.sin(math.pi * t)) for t in [i / 20 for i in range(21)]]
        pen.line(pts, (40, 30, 30, 255), 0.02)
        for i, (px, py) in enumerate(pts[:-1]):
            c = cols[i % len(cols)]
            pen.poly([(px, py), (px + (x1 - x0) / 20, py), (px + (x1 - x0) / 40, py - 0.22)], c, INK, 0.012)

    def sign(x, y, w, text, bg, fg, neon=False):
        pen.rect(x - w / 2, y + 0.2, x + w / 2, y + 0.7, bg, INK, 0.03)
        if neon:
            pen.soft(lambda d: d.rectangle([pen.P(x - w / 2, y + 0.75), pen.P(x + w / 2, y + 0.15)], fill=fg[:3] + (90,)), 0.12)
        pen.text(x, y + 0.45, text, 0.3, fg)

    def poster(x, y, col, motif):
        pen.rect(x - 0.3, y + 0.15, x + 0.3, y + 0.78, (236, 226, 200, 255), INK, 0.025)
        pen.rect(x - 0.24, y + 0.3, x + 0.24, y + 0.72, col)
        if motif == "star":
            pen.star(x, y + 0.51, 0.16, 0.07, (250, 230, 120, 255))
        elif motif == "wheel":
            pen.ring(x, y + 0.51, 0.13, 0.03, (250, 230, 120, 255))
        else:
            pen.ell(x, y + 0.51, 0.1, 0.12, (250, 230, 120, 255))

    # Festplatz: Wimpel ueber den Nordwand-Stuecken, Banner in der Mitte fehlt (Durchgang)
    x0, y0, x1, y1 = R("fairground")
    for a, b in ((x0 + 0.2, -3.2), (3.2, x1 - 0.2)):
        pennants(a, b, y1, (RED, CREAM, GOLD, (90, 190, 190, 255)))
    # Karussell
    x0, y0, x1, y1 = R("carousel")
    pennants(x0 + 0.2, -19.7, y1, (GOLD, (120, 60, 110, 255)))
    pennants(-16.8, x1 - 0.2, y1, (GOLD, (120, 60, 110, 255)))
    # Schiessbude: Leuchtschild und Zielscheiben
    x0, y0, x1, y1 = R("shooting")
    sign(-21.0, y1, 2.6, "3 SHOTS 1$", (30, 20, 30, 255), (255, 120, 190, 255), neon=True)
    for k, tx in enumerate((-17.0, -15.8, -14.6)):
        for r, c in ((0.28, (240, 240, 230, 255)), (0.19, RED), (0.09, (240, 240, 230, 255))):
            pen.ell(tx, y1 + 0.45, r, r, c, INK if r == 0.28 else None, 0.02)
    # Werkstatt: Werkzeugwand
    x0, y0, x1, y1 = R("workshop")
    pen.rect(x0 + 0.6, y1 + 0.12, x0 + 2.6, y1 + 0.8, (120, 96, 70, 255), INK, 0.03)
    for k in range(12):
        pen.ell(x0 + 0.75 + (k % 6) * 0.35, y1 + 0.3 + (k // 6) * 0.3, 0.02, 0.02, (40, 30, 20, 255))
    pen.line([(x0 + 0.9, y1 + 0.25), (x0 + 0.9, y1 + 0.7)], (160, 160, 170, 255), 0.05)      # Schraubenschluessel
    pen.line([(x0 + 1.5, y1 + 0.3), (x0 + 1.8, y1 + 0.7)], (200, 60, 50, 255), 0.06)        # Hammer
    pen.line([(x0 + 2.2, y1 + 0.25), (x0 + 2.2, y1 + 0.72)], (230, 190, 60, 255), 0.05)
    # Autoscooter: Neon-Schild
    x0, y0, x1, y1 = R("bumpercars")
    sign(x0 + 2.5, y1, 3.0, "BUMPER CARS", (24, 20, 40, 255), (110, 230, 255, 255), neon=True)
    # Security: Poster "STAFF ONLY"
    x0, y0, x1, y1 = R("security")
    sign(x1 - 1.2, y1, 1.6, "STAFF ONLY", (180, 40, 40, 255), (250, 240, 220, 255))
    # Umspannhaus: DANGER
    x0, y0, x1, y1 = R("substation")
    sign(x0 + 1.2, y1, 1.6, "DANGER", (230, 190, 50, 255), (30, 26, 30, 255))
    # Parkbuero: Lageplan-Poster und Uhr
    x0, y0, x1, y1 = R("office")
    poster(x0 + 1.0, y1, (70, 110, 80, 255), "wheel")
    pen.ell(x1 - 1.0, y1 + 0.45, 0.28, 0.28, (240, 236, 220, 255), INK, 0.03)
    pen.line([(x1 - 1.0, y1 + 0.45), (x1 - 1.0, y1 + 0.62)], INK, 0.03)
    pen.line([(x1 - 1.0, y1 + 0.45), (x1 - 0.88, y1 + 0.45)], INK, 0.03)
    # Musikzentrale: Konzertposter
    x0, y0, x1, y1 = R("musicbooth")
    for k, (col, m) in enumerate((((120, 60, 140, 255), "star"), ((40, 80, 140, 255), "dot"), ((160, 60, 60, 255), "star"))):
        poster(x0 + 1.0 + k * 0.8, y1, col, m)
    # Kuehlhaus: Temperaturschild
    x0, y0, x1, y1 = R("coldstore")
    sign(x1 - 1.2, y1, 1.4, "-18 C", (60, 110, 150, 255), (230, 245, 255, 255))
    # Geisterbahn: gemalte Totenkoepfe
    x0, y0, x1, y1 = R("ghosttrain")
    for tx in (x0 + 1.2, x1 - 1.2):
        pen.ell(tx, y1 + 0.45, 0.22, 0.24, (220, 214, 200, 255), INK, 0.02)
        for dx in (-0.08, 0.08):
            pen.ell(tx + dx, y1 + 0.47, 0.05, 0.06, INK)
