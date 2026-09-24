# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_floor.py - Boden und Waende des Moonlight Carnival (Stil abgenommen 2026-09-23, siehe park_art.py).
#
# Anders als museum_art.py (Vektor-Operationen je Platte) arbeitet der Park mit Musterkacheln: jedes
# Material ist eine nahtlose 4-m-Kachel (Perioden sind Teiler der Kachel), die ueber die ganze Karte
# gelegt und durch die Raummaske gestanzt wird. 74 x 50 m bei 80 px/m bleiben so in Sekunden.
# Darauf: Schiene, Kanal, Bruecken, Uebergaenge, Drehkreuz-Pfeile, Wandkrone, Nordwand-Stirnseiten
# (Gebaeude: Holz/Zeltstoff/Ziegel, Lichtungen und Wege: Hecke), weicher Wandschatten, Laternenlicht.

import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import park_decor as DECOR
import park_geo as G
import park_layout as L

TILE_M = 4.0
VOID = (14, 12, 22)
WALL_TOP = (40, 30, 48)
WALL_RIM = (74, 58, 86)
OUTLINE = (14, 12, 18)


# ------------------------------------------------------------------ Musterkacheln (nahtlos)

def _wave(n, periods, seed, amp=1.0):
    """Periodisches Rauschen (Summe ganzzahliger Sinuswellen) auf einer n x n-Kachel, -1..1."""
    rnd = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n * 2 * math.pi
    v = np.zeros((n, n), np.float32)
    for p in periods:
        for _ in range(2):
            kx, ky = rnd.integers(-p, p + 1), rnd.integers(-p, p + 1)
            if kx == 0 and ky == 0:
                ky = p
            v += np.sin(kx * x + ky * y + rnd.uniform(0, 6.3)) / max(1, p) ** 0.6
    v /= max(1e-6, np.abs(v).max())
    return v * amp


def _img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _mottle(img, n, amount, seed, periods=(2, 3, 5)):
    a = np.asarray(img).astype(np.float32)
    f = 1 + _wave(n, periods, seed) * amount
    return _img(a * f[..., None])


def tile_pavers(ppm, base=(118, 108, 100), seed=1, sw=0.5, sh=0.25):
    n = int(TILE_M * ppm)
    img = Image.new("RGB", (n, n), (50, 44, 42))
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    rows, cols = int(TILE_M / sh), int(TILE_M / sw)
    j = max(1, int(0.03 * ppm))
    for r in range(rows):
        off = (sw / 2) if r % 2 else 0
        for c in range(cols + 1):
            x0 = (c * sw - off) * ppm
            y0 = r * sh * ppm
            k = rnd.uniform(0.85, 1.12)
            col = tuple(int(v * k) for v in base)
            for dx in (0, n):                                           # Umlauf fuer die Naht
                xa = x0 - dx
                d.rounded_rectangle([xa + j, y0 + j, xa + sw * ppm - j, y0 + sh * ppm - j], radius=j * 2, fill=col)
                d.line([(xa + 2 * j, y0 + 1.5 * j), (xa + sw * ppm - 2 * j, y0 + 1.5 * j)], fill=tuple(min(255, int(v * 1.18)) for v in col), width=j)
    return _mottle(img, n, 0.06, seed + 5)


def tile_boards(ppm, base=(122, 84, 54), seed=2, bh=0.25, bl=2.0):
    n = int(TILE_M * ppm)
    a = np.zeros((n, n, 3), np.float32)
    rnd = random.Random(seed)
    rows = int(TILE_M / bh)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    for r in range(rows):
        y0, y1 = int(r * bh * ppm), int((r + 1) * bh * ppm)
        k = rnd.uniform(0.86, 1.1)
        a[y0:y1] = np.array(base, np.float32) * k
        grain = np.sin(x[y0:y1] / n * 2 * math.pi * rnd.choice((6, 8, 10)) + (y[y0:y1] - y0) * 0.35 + rnd.uniform(0, 6)) * 0.05
        a[y0:y1] *= (1 + grain)[..., None]
        a[y0:y0 + max(1, int(0.02 * ppm))] *= 1.18
        a[y1 - max(1, int(0.025 * ppm)):y1] *= 0.55
        # Stossfugen
        off = rnd.uniform(0, bl)
        xs = [int(((off + i * bl) % TILE_M) * ppm) for i in range(int(TILE_M / bl))]
        for xx in xs:
            a[y0:y1, max(0, xx - 1):xx + 1] *= 0.5
    return _img(a)


def tile_checker(ppm, c1, c2, s=0.5, seed=3):
    n = int(TILE_M * ppm)
    y, x = np.mgrid[0:n, 0:n]
    q = ((x // int(s * ppm)) + (y // int(s * ppm))) % 2
    a = np.where(q[..., None] == 0, np.array(c1, np.float32), np.array(c2, np.float32))
    g = int(s * ppm)
    edge = ((x % g) < max(1, int(0.02 * ppm))) | ((y % g) < max(1, int(0.02 * ppm)))
    a[edge] *= 0.7
    return _mottle(_img(a), n, 0.05, seed)


def tile_tiles(ppm, base, grout, s=0.4, seed=4):
    n = int(TILE_M * ppm)
    rnd = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n]
    g = int(s * ppm)
    cells = int(TILE_M / s)
    var = rnd.uniform(0.94, 1.06, (cells + 1, cells + 1))
    a = np.array(base, np.float32)[None, None, :] * var[(y // g) % cells, (x // g) % cells][..., None]
    gw = max(1, int(0.025 * ppm))
    edge = ((x % g) < gw) | ((y % g) < gw)
    a[edge] = np.array(grout, np.float32)
    hi = ((y % g) >= gw) & ((y % g) < gw * 2)
    a[hi] *= 1.08
    return _img(a)


def tile_carpet(ppm, base, accent, seed=5):
    n = int(TILE_M * ppm)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    s = 0.5 * ppm
    dia = (np.abs(((x % s) - s / 2)) + np.abs(((y % s) - s / 2))) < s * 0.18
    a = np.where(dia[..., None], np.array(accent, np.float32), np.array(base, np.float32))
    return _mottle(_img(a), n, 0.07, seed, periods=(3, 7, 11))


def tile_concrete(ppm, base, seed=6, stains=True):
    n = int(TILE_M * ppm)
    a = np.ones((n, n, 3), np.float32) * np.array(base, np.float32)
    a *= (1 + _wave(n, (2, 4, 9, 17), seed) * 0.08)[..., None]
    img = _img(a)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    g = n // 2
    for k in (0, g):                                                    # Dehnfugen alle 2 m
        d.line([(k, 0), (k, n)], fill=(0, 0, 0, 70), width=max(1, int(0.03 * ppm)))
        d.line([(0, k), (n, k)], fill=(0, 0, 0, 70), width=max(1, int(0.03 * ppm)))
    if stains:
        for _ in range(2):
            cx, cy, r = rnd.uniform(0.2, 0.8) * n, rnd.uniform(0.2, 0.8) * n, rnd.uniform(0.3, 0.6) * ppm
            d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=(20, 18, 20, 28))
    return img


def tile_earth(ppm, base, seed=7):
    n = int(TILE_M * ppm)
    a = np.ones((n, n, 3), np.float32) * np.array(base, np.float32)
    a *= (1 + _wave(n, (2, 5, 11, 23), seed) * 0.1)[..., None]
    img = _img(a)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(int(TILE_M * TILE_M * 60)):                          # Saegemehl
        x, y = rnd.uniform(0, n), rnd.uniform(0, n)
        r = rnd.uniform(0.01, 0.025) * ppm
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(214, 176, 120, rnd.randint(60, 140)))
    return img


def tile_plate(ppm, base, seed=8):
    n = int(TILE_M * ppm)
    img = _img(np.ones((n, n, 3), np.float32) * np.array(base, np.float32))
    d = ImageDraw.Draw(img, "RGBA")
    s = 0.25 * ppm
    k = int(TILE_M / 0.25)
    for r in range(k):
        for c in range(k):
            x, y = c * s + (s / 2 if r % 2 else 0), r * s
            for dx in (0, -n):
                d.line([(x + dx - s * 0.18, y + s * 0.62), (x + dx + s * 0.18, y + s * 0.38)], fill=(255, 255, 255, 50), width=max(1, int(0.02 * ppm)))
                d.line([(x + dx - s * 0.18, y + s * 0.68), (x + dx + s * 0.18, y + s * 0.44)], fill=(0, 0, 0, 70), width=max(1, int(0.02 * ppm)))
    return _mottle(img, n, 0.05, seed)


def tile_grass(ppm, base, seed=9):
    n = int(TILE_M * ppm)
    a = np.ones((n, n, 3), np.float32) * np.array(base, np.float32)
    a *= (1 + _wave(n, (2, 3, 7, 13), seed) * 0.14)[..., None]
    img = _img(a)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(int(TILE_M * TILE_M * 90)):                          # Halme
        x, y = rnd.uniform(0, n), rnd.uniform(0, n)
        h = rnd.uniform(0.04, 0.09) * ppm
        col = (120, 170, 96, 110) if rnd.random() < 0.5 else (34, 60, 40, 110)
        d.line([(x, y), (x + rnd.uniform(-0.3, 0.3) * h, y - h)], fill=col, width=1)
    return img


def tile_water(ppm, seed=10):
    n = int(TILE_M * ppm)
    a = np.ones((n, n, 3), np.float32) * np.array((34, 78, 122), np.float32)
    w = _wave(n, (2, 4, 8), seed)
    a *= (1 + w * 0.12)[..., None]
    img = _img(a)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(90):
        x, y = rnd.uniform(0, n), rnd.uniform(0, n)
        l = rnd.uniform(0.2, 0.6) * ppm
        d.arc([x - l, y - l * 0.2, x + l, y + l * 0.2], 200, 340, fill=(150, 200, 230, 110), width=max(1, int(0.02 * ppm)))
    return img


# Material je Bereich (Schluessel aus park_layout BUILDINGS/CLEARINGS)
def materials(ppm):
    return {
        "_path": tile_pavers(ppm, (112, 104, 98), 11),
        "fairground": tile_earth(ppm, (118, 86, 58), 12),
        "workshop": tile_concrete(ppm, (96, 96, 98), 13),
        "carousel": tile_checker(ppm, (112, 60, 96), (214, 196, 170), 0.5, 14),
        "bumpercars": tile_plate(ppm, (96, 104, 118), 15),
        "security": tile_carpet(ppm, (46, 54, 76), (70, 80, 108), 16),
        "substation": tile_concrete(ppm, (104, 102, 90), 17),
        "firstaid": tile_tiles(ppm, (214, 222, 220), (150, 170, 170), 0.4, 18),
        "office": tile_boards(ppm, (140, 98, 62), 19, 0.2, 1.33),
        "coldstore": tile_tiles(ppm, (196, 214, 226), (130, 160, 180), 0.5, 20),
        "musicbooth": tile_carpet(ppm, (84, 50, 96), (126, 82, 140), 21),
        "shooting": tile_boards(ppm, (116, 74, 46), 22),
        "mirrors": tile_tiles(ppm, (150, 176, 196), (96, 120, 140), 0.8, 23),
        "ghosttrain": tile_boards(ppm, (58, 42, 66), 24),
        "ferriswheel": tile_grass(ppm, (58, 96, 62), 25),
        "lighttower": tile_grass(ppm, (64, 100, 60), 26),
        "coaster": tile_boards(ppm, (132, 92, 58), 27, 0.33, 2.0),
        "maingate": tile_checker(ppm, (150, 54, 60), (220, 200, 168), 0.4, 28),
        "logflume": tile_pavers(ppm, (84, 98, 108), 29, 0.4, 0.4),
        "_water": tile_water(ppm, 30),
        "_bridge": tile_boards(ppm, (146, 108, 70), 31, 0.3, 1.0),
    }


# Nordwand-Stirnseite je Bereich: (Art, Farbe)
FACE = {
    "fairground": ("stripes", (150, 44, 54), (226, 208, 176)),
    "carousel": ("stripes", (122, 60, 110), (220, 200, 170)),
    "firstaid": ("stripes", (220, 222, 216), (190, 60, 60)),
    "shooting": ("planks", (120, 70, 44), None),
    "workshop": ("brick", (110, 70, 58), None),
    "bumpercars": ("planks", (70, 82, 110), None),
    "security": ("brick", (76, 70, 82), None),
    "substation": ("brick", (96, 86, 70), None),
    "office": ("planks", (150, 110, 74), None),
    "coldstore": ("planks", (170, 186, 196), None),
    "musicbooth": ("planks", (90, 58, 104), None),
    "mirrors": ("glass", (130, 160, 190), None),
    "ghosttrain": ("planks", (48, 34, 60), None),
}
HEDGE = (32, 62, 40)


# ------------------------------------------------------------------ Zeichnen

class Floor:
    def __init__(self, ppm):
        self.ppm = ppm
        self.x0, self.y0, self.x1, self.y1 = L.BOUNDS
        self.w, self.h = int((self.x1 - self.x0) * ppm), int((self.y1 - self.y0) * ppm)
        self.img = Image.new("RGB", (self.w, self.h), VOID)

    def P(self, x, y):
        return ((x - self.x0) * self.ppm, (self.y1 - y) * self.ppm)

    def mask(self, g, grow=0.0):
        m = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(m)
        if grow:
            g = g.buffer(grow)
        for p in G_parts(g):
            d.polygon([self.P(*q) for q in p.exterior.coords], fill=255)
            for hole in p.interiors:
                d.polygon([self.P(*q) for q in hole.coords], fill=0)
        return m

    def fill_tile(self, tile, m):
        big = Image.new("RGB", (self.w, self.h))
        tw, th = tile.size
        # Kacheln am Welt-Raster ausrichten, damit benachbarte Flaechen fluchten
        for yy in range(0, self.h + th, th):
            for xx in range(0, self.w + tw, tw):
                big.paste(tile, (xx, yy))
        self.img.paste(big, (0, 0), m)

    def draw(self):
        return ImageDraw.Draw(self.img, "RGBA")


def G_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def render(walk, water, shells, doors, rooms, ppm):
    F = Floor(ppm)
    mats = materials(ppm)
    rnd = random.Random(5)
    # Void: die Nacht zwischen den Gebaeuden, leicht gefleckt
    vt = _mottle(Image.new("RGB", (int(TILE_M * ppm),) * 2, VOID), int(TILE_M * ppm), 0.25, 3)
    F.fill_tile(vt, Image.new("L", (F.w, F.h), 255))
    DECOR.void(F, walk)                                                 # Parklandschaft zwischen den Gebaeuden
    # Wege, dann Bereiche
    F.fill_tile(mats["_path"], F.mask(walk))
    for key, (_name, _s, g) in rooms.items():
        if key in mats:
            F.fill_tile(mats[key], F.mask(g.intersection(walk)))
    d = F.draw()
    # Wasser mit Ufer, Bruecken
    F.fill_tile(mats["_water"], F.mask(water))
    for p in G_parts(water):
        d.line([F.P(*q) for q in p.exterior.coords], fill=(20, 40, 60, 255), width=int(0.08 * ppm))
    for s in L.BRIDGES:
        g = G.shape(s)
        F.fill_tile(mats["_bridge"], F.mask(g))
        x0, y0, x1, y1 = g.bounds
        d = F.draw()
        for yy in (y0 + 0.05, y1 - 0.05):
            d.line([F.P(x0, yy), F.P(x1, yy)], fill=(70, 46, 30, 255), width=int(0.1 * ppm))
    # Achterbahn-Schiene: Schotter, Schwellen, zwei Schienen
    d = F.draw()
    for s in L.RAIL:
        g = G.shape(s)
        x0, y0, x1, y1 = g.bounds
        d.rectangle([*F.P(x0, y1), *F.P(x1, y0)], fill=(70, 64, 66, 255))
        vertical = (y1 - y0) > (x1 - x0)
        if vertical:
            yy = y0
            while yy < y1:
                d.rectangle([*F.P(x0 + 0.08, yy + 0.16), *F.P(x1 - 0.08, yy)], fill=(96, 66, 44, 255))
                yy += 0.4
            for xx in (x0 + 0.32, x1 - 0.32):
                d.line([F.P(xx, y0), F.P(xx, y1)], fill=(188, 190, 198, 255), width=int(0.07 * ppm))
        else:
            xx = x0
            while xx < x1:
                d.rectangle([*F.P(xx, y1 - 0.08), *F.P(xx + 0.16, y0 + 0.08)], fill=(96, 66, 44, 255))
                xx += 0.4
            for yy in (y0 + 0.32, y1 - 0.32):
                d.line([F.P(x0, yy), F.P(x1, yy)], fill=(188, 190, 198, 255), width=int(0.07 * ppm))
    for _k, s, direction in L.CROSSINGS:                                # Bahnuebergang: Pflaster + Warnstreifen
        g = G.shape(s)
        x0, y0, x1, y1 = g.bounds
        F.fill_tile(mats["_path"], F.mask(g))
        d = F.draw()
        if direction == "vertical":
            for xx in (x0 + 0.32, x1 - 0.32):
                d.line([F.P(xx, y0), F.P(xx, y1)], fill=(150, 150, 160, 255), width=int(0.06 * ppm))
            for yy in (y0 + 0.1, y1 - 0.1):
                stripes(d, F, x0, yy - 0.08, x1, yy + 0.08)
        else:
            for yy in (y0 + 0.32, y1 - 0.32):
                d.line([F.P(x0, yy), F.P(x1, yy)], fill=(150, 150, 160, 255), width=int(0.06 * ppm))
            for xx in (x0 + 0.1, x1 - 0.1):
                stripes(d, F, xx - 0.08, y0, xx + 0.08, y1)
    # Drehkreuze: Einbahn-Pfeile (Spielinformation)
    for kind, s in L.TURNSTILES:
        g = G.shape(s)
        c = g.centroid
        dy = 0.8 if kind == "in" else -0.8
        col = (80, 220, 200, 230)
        d.line([F.P(c.x, c.y - dy), F.P(c.x, c.y + dy)], fill=col, width=int(0.14 * ppm))
        d.polygon([F.P(c.x, c.y + dy * 1.45), F.P(c.x - 0.35, c.y + dy), F.P(c.x + 0.35, c.y + dy)], fill=col)
    DECOR.rooms(F, walk, rooms)                                         # Ausstattung je Bereich (park_decor.py)
    # Waende: Gebaeudehuellen ohne Innenraum und Oeffnungen -> Wandkrone
    openings = unary_union([o for *_r, o in doors])
    walls = unary_union([s.difference(box(*b[3])).difference(openings) for s, b in zip(shells, L.BUILDINGS)])
    ambient(F, walk)
    d = F.draw()
    for p in G_parts(walls):
        d.polygon([F.P(*q) for q in p.exterior.coords], fill=WALL_TOP + (255,))
    faces(F, walk, rooms, water)
    DECOR.walls(F, walk)
    # Kronenkante: an allen Raendern der begehbaren Flaeche (Licht oben)
    d = F.draw()
    for p in G_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([F.P(*q) for q in ring.coords], fill=OUTLINE + (255,), width=max(2, int(0.06 * ppm)))
    # Laternenlicht ist eine eigene Ebene im Spiel (AtlasParkWorld, geht bei Park Blackout aus)
    return F.img


def lamp_points(walk, rooms):
    """Laternen am Wegrand, etwa alle 7 m, abwechselnd links und rechts (nur auf Wegen, nicht in Bereichen)."""
    hall = walk.difference(unary_union([g for _n, _s, g in rooms.values()]))
    inner = walk.buffer(-0.3)
    out = []
    side = 1
    for pts in L.PATHS:
        ls = LineString(pts)
        k = 2.0
        while k <= ls.length - 1.0:
            a, b = ls.interpolate(max(0.0, k - 0.1)), ls.interpolate(min(ls.length, k + 0.1))
            dx, dy = b.x - a.x, b.y - a.y
            n = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / n, dx / n
            c = ls.interpolate(k)
            for sgn in (side, -side):
                p = Point(c.x + nx * 1.3 * sgn, c.y + ny * 1.3 * sgn)
                if inner.contains(p) and hall.buffer(0.2).contains(p) and all(p.distance(Point(q)) > 3.5 for q in out):
                    out.append((round(p.x, 2), round(p.y, 2)))
                    break
            side = -side
            k += 7.0
    return out


def stripes(d, F, x0, y0, x1, y1):
    d.rectangle([*F.P(x0, y1), *F.P(x1, y0)], fill=(230, 190, 50, 255))
    n = int(max(x1 - x0, y1 - y0) / 0.25) + 1
    horizontal = (x1 - x0) >= (y1 - y0)
    for i in range(0, n, 2):
        if horizontal:
            a = x0 + i * 0.25
            d.polygon([F.P(a, y0), F.P(min(x1, a + 0.25), y0), F.P(min(x1, a + 0.25), y1), F.P(a, y1)], fill=(30, 26, 30, 255))
        else:
            a = y0 + i * 0.25
            d.polygon([F.P(x0, a), F.P(x1, a), F.P(x1, min(y1, a + 0.25)), F.P(x0, min(y1, a + 0.25))], fill=(30, 26, 30, 255))


def ambient(F, walk):
    """Weicher Schatten an allen Raendern der begehbaren Flaeche (wie museum_art.ambient_occlusion)."""
    s = 8
    lw, lh = int((F.x1 - F.x0) * s), int((F.y1 - F.y0) * s)
    small = Image.new("L", (lw, lh), 255)
    d = ImageDraw.Draw(small)
    P = lambda x, y: ((x - F.x0) * s, (F.y1 - y) * s)
    for p in G_parts(walk):
        d.polygon([P(*q) for q in p.exterior.coords], fill=0)
        for h in p.interiors:
            d.polygon([P(*q) for q in h.coords], fill=255)
    small = small.filter(ImageFilter.GaussianBlur(0.35 * s)).resize((F.w, F.h), Image.BICUBIC)
    inside = F.mask(walk)
    amount = ImageChops.multiply(small, inside).point(lambda v: int(v * 0.55))
    F.img = Image.composite(Image.new("RGB", F.img.size, (6, 4, 10)), F.img, amount)


def owner(pt, rooms):
    for key, (_n, _s, g) in rooms.items():
        if g.buffer(0.3).contains(pt):
            return key
    return None


def faces(F, walk, rooms, water):
    """Stirnseiten der Nordwaende (0,9 m, in die Wandmasse hinein) + Kontaktschatten."""
    ppm = F.ppm
    solid = box(F.x0 - 5, F.y0 - 5, F.x1 + 5, F.y1 + 5).difference(walk)
    wet = water.buffer(0.05)
    d = F.draw()
    face_h = 0.9
    for p in G_parts(walk):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            for i in range(len(ring) - 1):
                (x0, y0), (x1, y1) = ring[i], ring[i + 1]
                dx, dy = x1 - x0, y1 - y0
                if math.hypot(dx, dy) < 0.05 or abs(dy) > abs(dx) * 1.5:
                    continue
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                if not (solid.contains(Point(mx, my + 0.05)) and walk.contains(Point(mx, my - 0.05))):
                    continue
                if wet.contains(Point(mx, my + 0.05)):
                    continue                                        # Ufer: kein Wandstueck ins Wasser
                key = owner(Point(mx, my - 0.3), rooms)
                face = Polygon([(x0, y0), (x1, y1), (x1, y1 + face_h), (x0, y0 + face_h)]).intersection(solid.buffer(0.001))
                if face.is_empty:
                    continue
                kind = FACE.get(key, ("hedge", HEDGE, None))
                draw_face(F, d, face, kind, min(x0, x1), max(x0, x1), min(y0, y1), face_h)
                sh = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.3), (x0, y0 - 0.3)]).intersection(walk)
                for q in G_parts(sh):
                    d.polygon([F.P(*c) for c in q.exterior.coords], fill=(0, 0, 0, 60))


def draw_face(F, d, face, kind, xa, xb, yb, fh):
    style, col, col2 = kind
    for q in G_parts(face):
        d.polygon([F.P(*c) for c in q.exterior.coords], fill=col + (255,))
    fx0, fy0, fx1, fy1 = face.bounds
    clip = face

    def band(x0, y0, x1, y1, c):
        g = box(x0, y0, x1, y1).intersection(clip)
        for q in G_parts(g):
            d.polygon([F.P(*cc) for cc in q.exterior.coords], fill=c)

    if style == "stripes":
        x = math.floor(fx0 / 0.5) * 0.5
        i = int(round(x / 0.5))
        while x < fx1:
            if i % 2:
                band(x, fy0, x + 0.5, fy1, col2 + (255,))
            x += 0.5
            i += 1
        for k in range(int((fx1 - fx0) / 0.5) + 2):                       # Volant oben
            cx = math.floor(fx0 / 0.5) * 0.5 + k * 0.5 + 0.25
            g = Point(cx, fy1 - 0.05).buffer(0.25).intersection(box(cx - 0.25, fy1 - 0.3, cx + 0.25, fy1 - 0.05)).intersection(clip)
            for q in G_parts(g):
                d.polygon([F.P(*cc) for cc in q.exterior.coords], fill=(200, 160, 60, 255))
    elif style == "planks":
        y = fy0
        k = 0
        while y < fy1:
            band(fx0, y, fx1, y + 0.18, tuple(int(v * (1.0 if k % 2 else 0.9)) for v in col) + (255,))
            band(fx0, y, fx1, y + 0.025, (0, 0, 0, 80))
            y += 0.18
            k += 1
    elif style == "brick":
        y = fy0
        r = 0
        while y < fy1:
            band(fx0, y, fx1, y + 0.02, (0, 0, 0, 90))
            x = fx0 - (0.2 if r % 2 else 0)
            while x < fx1:
                band(x, y, x + 0.02, y + 0.15, (0, 0, 0, 90))
                x += 0.4
            y += 0.15
            r += 1
    elif style == "glass":
        x = fx0
        while x < fx1:
            band(x, fy0, x + 0.04, fy1, (40, 50, 70, 255))
            band(x + 0.15, fy0 + 0.2, x + 0.25, fy1 - 0.1, (230, 240, 255, 90))
            x += 0.8
    else:                                                               # Hecke
        rnd = random.Random(int(fx0 * 100 + fy0 * 7))
        x = fx0
        while x < fx1 + 0.3:
            r = rnd.uniform(0.22, 0.34)
            g = Point(x, fy1 - r * 0.6).buffer(r).intersection(clip.buffer(0.08)).intersection(box(fx0, fy0, fx1, fy1 + 0.2))
            for q in G_parts(g):
                d.polygon([F.P(*cc) for cc in q.exterior.coords], fill=tuple(int(v * rnd.uniform(0.9, 1.25)) for v in col) + (255,))
            x += r * 1.2
    # Sockelschatten und Oberkante
    band(fx0, fy0, fx1, fy0 + 0.08, (0, 0, 0, 90))
    band(fx0, fy1 - 0.05, fx1, fy1, (255, 255, 255, 40))
