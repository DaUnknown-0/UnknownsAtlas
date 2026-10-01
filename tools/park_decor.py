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
#
# Stilblatt 2026-10-01 (tools/handdraw.py, "Among Us, leicht handgezeichnet"): die Werkstatt ist komplett
# neu ausgestattet (workshop_floor), der Zwischenraum bekommt ein Rummel-Hinterland aus Wohnwagen,
# Zeltruecken, Kabeltrommeln, Kisten und Faessern zwischen den Baumkronen (hinterland), Umrisse zittern
# leicht (Pen.ink). Die uebrigen Raeume folgen im vollen Pass.

import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import handdraw as HD
import park_geo as G
import park_layout as L

INK = (18, 14, 22, 255)
RED = (176, 52, 60, 255)
CREAM = (226, 210, 176, 255)
GOLD = (220, 176, 70, 255)
BULB = (255, 226, 150, 255)


def dim(col, f):
    """Farbe abdunkeln (Nacht im Zwischenraum), Alpha bleibt."""
    return tuple(int(v * f) for v in col[:3]) + (col[3] if len(col) > 3 else 255,)


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

    # --- handgezeichnet (Stilblatt): Flaeche mit zittrigem Umriss und schwankender Strichstaerke
    def hpoly(self, pts, fill=None, outline=INK, width=0.04, seed=0, amp=HD.AMP):
        q = HD.wobble(pts, amp=amp, seed=seed, step=0.06, closed=True)
        if fill:
            self.d.polygon([self.P(*p) for p in q], fill=fill)
        if outline:
            HD.ink(self.d, [self.P(*p) for p in q], outline, self.w(width), seed=seed, var=0.25, closed=True)

    def hrect(self, x0, y0, x1, y1, fill=None, outline=INK, width=0.04, seed=0, rot=0.0):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if rot:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            c, s = math.cos(rot), math.sin(rot)
            pts = [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]
        self.hpoly(pts, fill, outline, width, seed)

    def hell(self, cx, cy, rx, ry, fill=None, outline=INK, width=0.04, seed=0):
        q = HD.wobble_ellipse(cx, cy, rx, ry, seed=seed)
        if fill:
            self.d.polygon([self.P(*p) for p in q], fill=fill)
        if outline:
            HD.ink(self.d, [self.P(*p) for p in q], outline, self.w(width), seed=seed, var=0.25, closed=True)

    def hline(self, pts, fill, width=0.04, seed=0, amp=HD.AMP):
        q = HD.wobble(pts, amp=amp, seed=seed, step=0.06)
        HD.ink(self.d, [self.P(*p) for p in q], fill, self.w(width), seed=seed, var=0.3)

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
    """Zwischenraum: Rummel-Hinterland (Wohnwagen, Zeltruecken, Kabeltrommeln, Kisten, Faesser,
    Lichterketten) im Streifen hinter den Gebaeuden, dahinter dunkle Baumkronen. Voller Pass: heller und
    kontrastreicher als im Stilblatt (im Spiel war es kaum zu erkennen): Wiesengrund hinter den Waenden,
    hellere Baumkronen mit Lichtkante, kraeftigere Umrisse, mehr Lichterketten."""
    pen = Pen(F)
    rnd = random.Random(77)
    keep_out = walk.buffer(0.7)
    x0, y0, x1, y1 = L.BOUNDS
    items = hinterland_items(walk, rnd)
    taken = unary_union([g for _k, g, _a in items]).buffer(0.5) if items else Point(1e6, 1e6)
    # Wiesengrund im Streifen hinter den Waenden (dunkles Gruen, zur Nacht hin auslaufend)
    def meadow(d):
        for grow, col in ((6.0, (30, 44, 36, 90)), (3.5, (38, 54, 42, 120)), (1.6, (46, 64, 48, 150))):
            for p in G_parts_(walk.buffer(grow)):
                d.polygon([pen.P(*q) for q in p.exterior.coords], fill=col)
    pen.soft(meadow, 0.6)
    for _ in range(900):                                                # Grasbueschel und Blumen auf der Wiese
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if keep_out.contains(Point(x, y)) or not walk.buffer(5.0).contains(Point(x, y)):
            continue
        if rnd.random() < 0.08:
            pen.ell(x, y, 0.035, 0.035, rnd.choice(((230, 200, 90, 220), (220, 120, 150, 220), (210, 210, 240, 200))))
        else:
            for seg in HD.tuft(x, y, rnd, n=3, h=0.1):
                pen.line(seg, (70, 100, 66, 200), 0.015)
    # dunkle Baumkronen in Gruppen, nicht ueber dem Hinterland
    trees = []
    for _ in range(520):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        r = rnd.uniform(0.7, 1.5)
        if keep_out.contains(Point(x, y)) or taken.intersects(Point(x, y).buffer(r * 0.7)):
            continue
        trees.append((x, y, r))
    trees.sort(key=lambda t: -t[1])                                     # hinten zuerst
    for i, (x, y, r) in enumerate(trees):
        base = rnd.choice(((34, 56, 50), (40, 62, 54), (30, 48, 58)))
        pen.ell(x + 0.15, y - 0.2, r, r * 0.85, (4, 4, 8, 140))
        pen.hell(x, y, r, r * 0.9, base + (255,), (8, 10, 14, 255), 0.055, seed=i)
        pen.ell(x - r * 0.3, y + r * 0.3, r * 0.5, r * 0.4, tuple(min(255, int(v * 1.4)) for v in base) + (255,))
        pen.ell(x - r * 0.42, y + r * 0.42, r * 0.22, r * 0.16, tuple(min(255, int(v * 1.7)) for v in base) + (255,))
    # Hinterland darueber (steht frei zwischen den Baeumen)
    for i, (kind, g, ang) in enumerate(sorted(items, key=lambda t: -t[1].centroid.y)):
        draw_hinterland(pen, kind, g, ang, rnd, i)
    # Lichterketten ueber der Dunkelheit (warme Punkte), nur ausserhalb der Wege
    for _ in range(40):
        ax, ay = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        ang = rnd.uniform(0, math.pi)
        ln = rnd.uniform(4, 9)
        pts = [(ax + math.cos(ang) * ln * t, ay + math.sin(ang) * ln * t - 0.6 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
        if any(keep_out.contains(Point(p)) for p in pts):
            continue
        pen.line(pts, (30, 24, 30, 255), 0.03)
        for i, p in enumerate(pts[1::2]):
            col = ((255, 220, 140), (255, 140, 150), (150, 230, 220))[i % 3]
            pen.ell(p[0], p[1] - 0.05, 0.16, 0.16, col + (70,))
            pen.ell(p[0], p[1] - 0.05, 0.055, 0.055, col + (255,))


def G_parts_(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


HINTERLAND = [   # (Art, Laenge, Breite, Gewicht)
    ("wohnwagen", 2.6, 1.5, 3), ("zelt", 3.2, 2.2, 3), ("kabeltrommel", 0.9, 0.9, 3), ("kisten", 1.2, 0.8, 4),
    ("fass", 0.6, 0.6, 3), ("generator", 1.3, 0.8, 2), ("palette", 1.2, 0.9, 2), ("truck", 3.4, 1.7, 1),
]


def hinterland_items(walk, rnd):
    """Plaetze fuer das Rummel-Hinterland: im Streifen 1,2 bis 5,5 m hinter der begehbaren Flaeche, ohne
    Ueberlappung, dicht an den Gebaeuden eher Kleinkram, weiter draussen Wagen und Zelte."""
    x0, y0, x1, y1 = L.BOUNDS
    near = walk.buffer(5.5).difference(walk.buffer(1.2)).intersection(box(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5))
    inner = walk.buffer(1.2)
    items = []
    placed = []
    weights = [w for *_r, w in HINTERLAND]
    tries = 0
    while len(items) < 110 and tries < 4000:
        tries += 1
        kind, ln, wd, _w = rnd.choices(HINTERLAND, weights=weights)[0]
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        p = Point(x, y)
        if not near.contains(p):
            continue
        d = inner.distance(p)
        if kind in ("wohnwagen", "zelt", "truck") and d < 1.0:
            continue
        ang = rnd.choice((0.0, math.pi / 2)) + rnd.uniform(-0.12, 0.12)
        if kind in ("kisten", "fass", "kabeltrommel"):
            ang = rnd.uniform(0, math.pi)
        c, s = math.cos(ang), math.sin(ang)
        hx, hy = ln / 2, wd / 2
        g = Polygon([(x + c * dx - s * dy, y + s * dx + c * dy) for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))])
        if g.buffer(0.35).intersects(inner):
            continue
        if any(g.buffer(0.3).intersects(q) for q in placed):
            continue
        placed.append(g)
        items.append((kind, g, ang))
    return items


def draw_hinterland(pen, kind, g, ang, rnd, i):
    """Ein Hinterland-Objekt von oben (Nacht: gedaempfte Farben, dunkler Schlagschatten nach Suedost)."""
    c, s = math.cos(ang), math.sin(ang)
    cx, cy = g.centroid.x, g.centroid.y

    def T(dx, dy):
        return (cx + c * dx - s * dy, cy + s * dx + c * dy)

    def R(x0, y0, x1, y1):
        return [T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)]

    pts = list(g.exterior.coords)[:-1]
    pen.poly([(x + 0.2, y - 0.25) for x, y in pts], (4, 4, 8, 150))                      # Schlagschatten
    night = 0.82
    if kind == "wohnwagen":
        body = dim((214, 208, 196), night)
        pen.hpoly(pts, body, INK, 0.05, seed=i)
        pen.hpoly(R(-1.15, -0.55, 1.15, 0.55), dim((190, 184, 172), night), None, seed=i + 1)   # Dachwoelbung
        pen.hpoly(R(-1.2, 0.02, 1.2, 0.12), dim((150, 60, 70), night), None, seed=i + 2)          # Zierstreifen
        pen.hpoly(R(-0.5, -0.3, 0.0, 0.2), dim((90, 100, 110), night), INK, 0.03, seed=i + 3)             # Dachluke
        pen.hpoly(R(0.5, -0.28, 0.8, 0.0), dim((240, 220, 160), night * 1.4), INK, 0.025, seed=i + 4)      # Oberlicht
        pen.poly([T(1.3, -0.12), T(1.75, 0.0), T(1.3, 0.12)], dim((80, 80, 90), night), INK, 0.03)                 # Deichsel
        for sx in (-0.75, 0.75):
            pen.poly(R(sx - 0.2, -0.8, sx + 0.2, -0.72), dim((30, 30, 34), 1.0), INK, 0.02)                      # Raeder
            pen.poly(R(sx - 0.2, 0.72, sx + 0.2, 0.8), dim((30, 30, 34), 1.0), INK, 0.02)
    elif kind == "zelt":
        a, b = rnd.choice((((150, 48, 58), (226, 208, 176)), ((60, 50, 110), (210, 200, 220)), ((50, 90, 100), (200, 200, 180))))
        n = 6
        for k in range(n):
            x0 = -1.6 + 3.2 * k / n
            x1 = -1.6 + 3.2 * (k + 1) / n
            pen.poly(R(x0, 0.0, x1, 1.1), dim(a if k % 2 else b, night * 0.85), None)
            pen.poly(R(x0, -1.1, x1, 0.0), dim(a if k % 2 else b, night), None)
        pen.hpoly(pts, None, INK, 0.05, seed=i)
        pen.hline([T(-1.6, 0.0), T(1.6, 0.0)], dim((255, 240, 220), night * 0.9), 0.03, seed=i + 1)   # First
        for sx in (-1.9, 1.9):                                                                         # Abspannseile
            pen.line([T(sx * 0.84, 0.0), T(sx, 0.0)], (60, 54, 60, 255), 0.02)
            pen.ell(*T(sx, 0.0), 0.05, 0.05, (90, 80, 70, 255), INK, 0.015)
    elif kind == "truck":
        pen.hpoly(R(-1.7, -0.85, 0.6, 0.85), dim((200, 200, 204), night), INK, 0.05, seed=i)            # Koffer
        pen.hpoly(R(0.65, -0.75, 1.7, 0.75), dim((160, 60, 60), night), INK, 0.05, seed=i + 1)         # Fahrerhaus
        pen.poly(R(1.35, -0.6, 1.6, 0.6), dim((120, 170, 200), night * 1.2), INK, 0.025)                # Windschutzscheibe
        pen.line([T(-1.5, 0.0), T(0.4, 0.0)], dim((160, 160, 164), night), 0.02)
        for sx in (-1.2, 0.2, 1.2):
            for sy in (-0.95, 0.95):
                pen.poly(R(sx - 0.25, sy - 0.08, sx + 0.25, sy + 0.08), (28, 28, 32, 255), INK, 0.02)
    elif kind == "kabeltrommel":
        wood = dim((190, 140, 90), night)
        pen.hell(cx, cy, 0.45, 0.45, wood, INK, 0.05, seed=i)
        pen.hell(cx, cy, 0.14, 0.14, dim((120, 80, 50), night), INK, 0.03, seed=i + 1)
        for k in range(6):
            a = ang + k * math.pi / 3
            pen.line([(cx + math.cos(a) * 0.16, cy + math.sin(a) * 0.16), (cx + math.cos(a) * 0.42, cy + math.sin(a) * 0.42)], dim((130, 90, 55), night), 0.025)
        pen.line([(cx + 0.3, cy - 0.3), (cx + 0.9, cy - 0.5), (cx + 1.2, cy - 0.2)], (24, 22, 28, 255), 0.04)    # Kabel
    elif kind == "kisten":
        cols = ((170, 130, 90), (120, 100, 80), (160, 140, 110))
        for k, (dx, dy, w) in enumerate(((-0.3, 0.0, 0.55), (0.3, 0.05, 0.5), (0.05, -0.05, 0.4))):
            col = dim(cols[k % 3], night)
            pts2 = R(dx - w / 2, dy - w / 2, dx + w / 2, dy + w / 2)
            a2 = ang + rnd.uniform(-0.3, 0.3)
            c2, s2 = math.cos(a2 - ang), math.sin(a2 - ang)
            mx, my = T(dx, dy)
            pts2 = [(mx + (x - mx) * c2 - (y - my) * s2, my + (x - mx) * s2 + (y - my) * c2) for x, y in pts2]
            pen.hpoly(pts2, col, INK, 0.035, seed=i + k)
            pen.line([pts2[0], pts2[2]], dim((100, 80, 60), night), 0.02)
            pen.line([pts2[1], pts2[3]], dim((100, 80, 60), night), 0.02)
    elif kind == "fass":
        col = dim(rnd.choice(((70, 110, 170), (150, 60, 60), (120, 124, 130))), night)
        pen.hell(cx, cy, 0.3, 0.3, col, INK, 0.045, seed=i)
        pen.ell(cx, cy, 0.2, 0.2, None, dim((255, 255, 255), night * 0.8), 0.02)
        pen.ell(cx - 0.08, cy + 0.08, 0.06, 0.04, (255, 255, 255, 60))
    elif kind == "generator":
        body = dim((212, 177, 60), night)
        pen.hpoly(R(-0.65, -0.4, 0.65, 0.4), body, INK, 0.05, seed=i)
        pen.poly(R(-0.5, -0.25, 0.1, 0.25), dim((50, 50, 56), 1.0), INK, 0.025)
        for k in range(5):
            pen.line([T(-0.45 + k * 0.12, -0.2), T(-0.45 + k * 0.12, 0.2)], (30, 30, 34, 255), 0.02)
        pen.ell(*T(0.4, 0.0), 0.1, 0.1, dim((80, 80, 88), 1.0), INK, 0.02)
        pen.line([T(0.65, 0.2), T(0.95, 0.35)], (70, 70, 76, 255), 0.05)                                 # Auspuff
        pen.ell(*T(1.05, 0.4), 0.18, 0.12, (120, 120, 130, 70))
    elif kind == "palette":
        wood = dim((190, 150, 100), night)
        for k in range(5):
            y = -0.45 + k * 0.22
            pen.poly(R(-0.6, y, 0.6, y + 0.14), wood, INK, 0.025)
        pen.hpoly(pts, None, INK, 0.035, seed=i)


# ------------------------------------------------------------------ Bereiche

def R(key):
    for b in L.BUILDINGS:
        if b[0] == key:
            return b[3]
    for c in L.CLEARINGS:
        if c[0] == key:
            return c[3]
    raise KeyError(key)


K = 0.55            # schraege Aufsicht wie park_art (Hoehe h steht h * K nach oben)
STEEL = (110, 112, 124, 255)
WOODC = (176, 128, 80, 255)


# ------------------------------------------------------------------ Bausteine (flach, max. 0,5 m hoch)

def lowbox(pen, x0, y0, x1, y1, h, top, front=None, seed=0, ol=INK, w=0.03, shadow=True):
    """Niedrige Kiste in schraeger Aufsicht: Vorderseite y0..y0+h*K, Deckflaeche darueber, zittrige Umrisse."""
    front = front or dim(top, 0.72)
    if shadow:
        pen.poly([(x0 + 0.08, y0 - 0.1), (x1 + 0.1, y0 - 0.1), (x1 + 0.1, y1), (x0 + 0.08, y1)], (0, 0, 0, 70))
    pen.hpoly([(x0, y0), (x1, y0), (x1, y0 + h * K), (x0, y0 + h * K)], front, ol, w, seed=seed)
    pen.hpoly([(x0, y0 + h * K), (x1, y0 + h * K), (x1, y1 + h * K), (x0, y1 + h * K)], top, ol, w, seed=seed + 1)
    pen.rect(x0 + w, y0 + w, x1 - w, y0 + min(0.06, h * K * 0.3), (0, 0, 0, 50))             # Bodenschatten
    pen.line([(x0 + w, y1 + h * K - w), (x1 - w, y1 + h * K - w)], (255, 255, 255, 60), w * 0.7)   # Lichtkante


def rope_posts(pen, pts, col=(200, 40, 50, 255), post=GOLD):
    """Absperrung: Pfosten (Fuss + Stab 0,9 m + Knauf) und durchhaengende Seile dazwischen."""
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        rope = [(ax + (bx - ax) * t, ay + (by - ay) * t + 0.9 * K - 0.12 * math.sin(math.pi * t)) for t in [i / 10 for i in range(11)]]
        pen.line(rope, INK, 0.045)
        pen.line(rope, col, 0.028)
    for x, y in pts:
        pen.ell(x, y, 0.1, 0.05, (0, 0, 0, 70))
        pen.ell(x, y, 0.085, 0.045, dim(post, 0.8), INK, 0.015)
        pen.line([(x, y), (x, y + 0.9 * K)], INK, 0.05)
        pen.line([(x, y), (x, y + 0.9 * K)], post, 0.028)
        pen.ell(x, y + 0.9 * K, 0.04, 0.04, post, INK, 0.012)


def crate(pen, x, y, w, d, h, col, seed=0):
    """Holzkiste (Deckel mit Brettfuge und Diagonale)."""
    lowbox(pen, x - w / 2, y - d / 2, x + w / 2, y + d / 2, h, col, dim(col, 0.7), seed=seed)
    ty = y + h * K
    pen.line([(x - w / 2 + 0.03, ty), (x + w / 2 - 0.03, ty)], dim(col, 0.6), 0.015)
    pen.line([(x - w / 2 + 0.05, ty - d / 2 + 0.05), (x + w / 2 - 0.05, ty + d / 2 - 0.05)], dim(col, 0.6), 0.015)


def barrel(pen, x, y, r, col, seed=0):
    pen.ell(x + 0.05, y - 0.06, r, r, (0, 0, 0, 70))
    pen.hell(x, y, r, r, col, INK, 0.035, seed=seed)
    pen.ell(x, y, r * 0.68, r * 0.68, None, dim((255, 255, 255), 0.85), 0.018)
    pen.ell(x, y, r * 0.2, r * 0.2, dim(col, 0.6), INK, 0.012)
    pen.ell(x - r * 0.3, y + r * 0.3, r * 0.22, r * 0.14, (255, 255, 255, 70))


def tire(pen, x, y, r, seed=0):
    pen.ell(x + 0.04, y - 0.05, r, r, (0, 0, 0, 80))
    pen.hell(x, y, r, r, (34, 34, 38, 255), INK, 0.03, seed=seed)
    pen.ell(x, y, r * 0.5, r * 0.5, (62, 60, 66, 255), INK, 0.02)
    pen.ell(x - r * 0.3, y + r * 0.35, r * 0.25, r * 0.12, (255, 255, 255, 40))


def cone(pen, x, y, seed=0):
    """Verkehrshuetchen (0,6 m hoch): Fuss, Kegel mit weissem Band."""
    pen.ell(x + 0.03, y - 0.03, 0.17, 0.09, (0, 0, 0, 70))
    pen.hpoly([(x - 0.17, y - 0.07), (x + 0.17, y - 0.07), (x + 0.17, y + 0.06), (x - 0.17, y + 0.06)], (40, 36, 40, 255), INK, 0.02, seed=seed)
    pen.hpoly([(x - 0.11, y), (x + 0.11, y), (x + 0.03, y + 0.62 * K + 0.1), (x - 0.03, y + 0.62 * K + 0.1)], (240, 120, 40, 255), INK, 0.02, seed=seed + 1)
    pen.poly([(x - 0.075, y + 0.2), (x + 0.075, y + 0.2), (x + 0.06, y + 0.3), (x - 0.06, y + 0.3)], (240, 240, 236, 255))


def footprints(pen, pts, rnd, col=(0, 0, 0, 40), step=0.32):
    """Fussspuren entlang einer Polylinie: Paare kleiner Ovale, leicht versetzt."""
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ln = math.hypot(bx - ax, by - ay)
        n = max(1, int(ln / step))
        nx, ny = -(by - ay) / ln, (bx - ax) / ln
        for k in range(n):
            t = (k + 0.5) / n
            sgn = 1 if k % 2 else -1
            px, py = ax + (bx - ax) * t + nx * 0.09 * sgn, ay + (by - ay) * t + ny * 0.09 * sgn
            pen.ell(px, py, 0.05, 0.075, col)


def stencil(pen, x, y, text, size, col):
    """Schablonenschrift auf dem Boden (leicht verblasst)."""
    pen.text(x, y, text, size, col)


def paper(pen, x, y, rnd, col=(236, 232, 220, 230)):
    a = rnd.uniform(-0.4, 0.4)
    c, s_ = math.cos(a), math.sin(a)
    pts = [(x + c * dx - s_ * dy, y + s_ * dx + c * dy) for dx, dy in ((-0.11, -0.15), (0.11, -0.15), (0.11, 0.15), (-0.11, 0.15))]
    pen.poly(pts, col, (120, 120, 120, 180), 0.012)
    for k in range(3):
        f = 0.25 + k * 0.22
        pen.line([(pts[3][0] + (pts[0][0] - pts[3][0]) * f + 0.03, pts[3][1] + (pts[0][1] - pts[3][1]) * f),
                  (pts[2][0] + (pts[1][0] - pts[2][0]) * f - 0.03, pts[2][1] + (pts[1][1] - pts[2][1]) * f)], (160, 160, 170, 200), 0.01)


def balloon(pen, x, y, col, rnd):
    """Verlorener, halb schlaffer Luftballon mit Schnur."""
    pen.hell(x, y, 0.16, 0.12, col + (255,), INK, 0.02, seed=int(x * 10))
    pen.ell(x - 0.05, y + 0.04, 0.05, 0.03, (255, 255, 255, 90))
    pen.hline([(x + 0.14, y - 0.04), (x + 0.4, y - 0.2), (x + 0.5, y + 0.05), (x + 0.75, y - 0.1)], (60, 50, 60, 255), 0.012, seed=int(y * 10), amp=0.02)


def plush(pen, x, y, col, seed=0, s=1.0):
    """Plueschtier (Baerchen von vorn): Koerper, Kopf, Ohren, Gesicht."""
    pen.hell(x, y - 0.02 * s, 0.17 * s, 0.15 * s, col, INK, 0.022, seed=seed)
    for dx in (-0.1, 0.1):
        pen.ell(x + dx * s, y + 0.3 * s, 0.06 * s, 0.06 * s, col, INK, 0.018)
    pen.hell(x, y + 0.2 * s, 0.14 * s, 0.13 * s, col, INK, 0.022, seed=seed + 1)
    pen.ell(x, y + 0.14 * s, 0.07 * s, 0.05 * s, dim((255, 255, 255), 0.95))
    for dx in (-0.05, 0.05):
        pen.ell(x + dx * s, y + 0.23 * s, 0.018 * s, 0.018 * s, INK)
    pen.ell(x, y + 0.16 * s, 0.02 * s, 0.014 * s, INK)
    pen.ell(x, y - 0.05 * s, 0.07 * s, 0.06 * s, dim((255, 255, 255), 0.95))


def sawdust_pile(pen, x, y, r, seed=0):
    pen.hell(x, y, r, r * 0.6, (168, 136, 92, 255), (90, 68, 44, 255), 0.02, seed=seed)
    pen.ell(x - r * 0.25, y + r * 0.15, r * 0.4, r * 0.22, (200, 170, 120, 200))


def arrow_h(pen, x0, x1, y, col, w=0.14):
    """Waagerechter Pfeil von x0 nach x1 auf Hoehe y."""
    sgn = 1 if x1 > x0 else -1
    pen.poly([(x0, y - w / 2), (x1 - sgn * 0.2, y - w / 2), (x1 - sgn * 0.2, y - w), (x1, y), (x1 - sgn * 0.2, y + w), (x1 - sgn * 0.2, y + w / 2), (x0, y + w / 2)], col)


# ------------------------------------------------------------------ Bereiche

def rooms(F, walk, rooms_):
    pen = Pen(F)
    area = {k: g.intersection(walk) for k, (_n, _s, g) in rooms_.items()}
    obst = unary_union([G.shape(s).buffer(0.2) for s, _k in L.OPAQUE + L.GLASS])
    free = {k: a.difference(obst) for k, a in area.items()}
    fairground_floor(pen, free["fairground"])
    workshop_floor(pen, free["workshop"])
    carousel_floor(pen, free["carousel"])
    bumpercars_floor(pen, free["bumpercars"])
    security_floor(pen, free["security"])
    substation_floor(pen, free["substation"])
    firstaid_floor(pen, free["firstaid"])
    office_floor(pen, free["office"])
    coldstore_floor(pen, free["coldstore"])
    musicbooth_floor(pen, free["musicbooth"])
    shooting_floor(pen, free["shooting"])
    ghosttrain_floor(pen, free["ghosttrain"])
    ferriswheel_floor(pen, free["ferriswheel"])
    lighttower_floor(pen, free["lighttower"])
    coaster_floor(pen, free["coaster"])
    logflume_floor(pen, free["logflume"])
    # Wege: Konfetti, Laub, Popcorn, gelegentlich ein Kanaldeckel
    rest = walk.difference(unary_union([g for _n, _s, g in rooms_.values()]))
    scatter(pen, rest, 180, 201, confetti)
    scatter(pen, rest, 60, 202, leaf)
    scatter(pen, rest, 20, 203, popcorn)
    scatter(pen, rest.buffer(-0.6), 5, 204, lambda p, x, y, r: drain(p, x, y, 0.3))


def fairground_floor(pen, free):
    """Festplatz: gemalte Manege (rot/creme, handgezeichnet) mit Mondsichel in der Mitte und Stern
    unter dem Notknopf, Saegemehlhaufen, Absperrseile vor dem Kassenhaeuschen, Richtungsstencils an
    den Tueren, Konfetti, Popcorn, Tickets, ein verlorener Ballon, Fussspuren.
    Freizuhalten: Notknopf (0/3,4), Spawn (0/1,2), Buden NW/NO, Konsolen W/O/N, Laptop (5,2/-1,6),
    Kassenhaeuschen (-1,6..1,6/-3..-2,2), Drehkreuzspuren S."""
    fx0, fy0, fx1, fy1 = R("fairground")
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    rnd = random.Random(1201)
    rx, ry = 4.6, 3.6
    pen.ell(cx, cy, rx, ry, (150, 110, 70, 90))
    # Manegenrand: 36 Segmente rot/creme, jedes als zittriges Viereck
    for k in range(36):
        a0, a1 = k * math.tau / 36, (k + 1) * math.tau / 36
        col = (176, 52, 62, 255) if k % 2 == 0 else CREAM
        pts = [(cx + math.cos(a0) * (rx - 0.16), cy + math.sin(a0) * (ry - 0.16)), (cx + math.cos(a1) * (rx - 0.16), cy + math.sin(a1) * (ry - 0.16)),
               (cx + math.cos(a1) * (rx + 0.16), cy + math.sin(a1) * (ry + 0.16)), (cx + math.cos(a0) * (rx + 0.16), cy + math.sin(a0) * (ry + 0.16))]
        pen.hpoly(pts, col, None, seed=k)
    pen.hell(cx, cy, rx + 0.18, ry + 0.18, None, INK, 0.035, seed=2)
    pen.hell(cx, cy, rx - 0.18, ry - 0.18, None, INK, 0.035, seed=3)
    # Mondsichel in der Manege (Spawn-Mitte), Stern unter dem Notknopf
    pen.hell(cx, cy - 0.6, 1.1, 1.1, (236, 206, 110, 150), (120, 90, 40, 200), 0.03, seed=4)
    pen.ell(cx + 0.55, cy - 0.45, 0.9, 0.92, (150, 110, 70, 255))
    pen.ell(cx + 0.55, cy - 0.45, 0.9, 0.92, (118, 86, 58, 120))
    pen.hell(cx + 0.55, cy - 0.45, 0.9, 0.92, None, (120, 90, 40, 200), 0.03, seed=5)
    pen.star(cx, cy + 1.5, 0.9, 0.4, (220, 176, 70, 120))
    for sx, sy in ((cx - 2.6, cy + 1.9), (cx + 2.9, cy - 1.6), (cx - 2.2, cy - 2.1)):
        pen.star(sx, sy, 0.22, 0.09, (236, 206, 110, 120))
    # Saegemehlhaufen am Rand, Fussspuren quer durch
    for k, (sx, sy, r) in enumerate(((fx0 + 1.2, fy0 + 1.1, 0.5), (fx1 - 1.3, fy1 - 2.2, 0.42), (fx0 + 1.6, fy1 - 2.4, 0.38))):
        sawdust_pile(pen, sx, sy, r, seed=k)
    footprints(pen, [(fx0 + 0.6, 1.9), (cx - 2.0, 1.2), (cx + 2.2, 0.6), (fx1 - 0.6, 1.8)], rnd)
    footprints(pen, [(cx - 0.3, fy0 + 0.3), (cx - 0.6, cy - 0.6), (cx - 1.2, cy + 2.6), (cx - 1.0, fy1 - 0.7)], rnd)
    # Absperrseile vor dem Kassenhaeuschen (Schlange zum Fenster), Tuer-Stencils mit Pfeilen
    rope_posts(pen, [(-1.35, -1.9), (-1.35, -0.9)])
    rope_posts(pen, [(1.35, -1.9), (1.35, -0.9)])
    stencil(pen, fx1 - 1.1, 1.75, "RIDES", 0.28, (236, 206, 110, 150))
    arrow_h(pen, fx1 - 0.5, fx1 - 0.05, 1.35, (236, 206, 110, 150))
    stencil(pen, fx0 + 1.4, 1.75, "CAROUSEL", 0.24, (236, 206, 110, 150))
    arrow_h(pen, fx0 + 0.5, fx0 + 0.05, 1.35, (236, 206, 110, 150))
    balloon(pen, fx1 - 1.6, fy0 + 1.0, (90, 180, 220), rnd)
    scatter(pen, free, 160, 1, confetti)
    scatter(pen, free, 40, 2, popcorn)
    scatter(pen, free, 10, 3, ticket)


def carousel_floor(pen, free):
    """Karussell: Goldring-Einlage, Sterne in den Ecken (mit Schatten), Absperrseile vom Osttor zur
    Plattform, MIND THE STEP, Konfetti, ein Ballon. Freizuhalten: Plattform (-14/1,5 r 2,8), Konsolen N,
    Vent (-18,2/-2,2)."""
    ccx, ccy, cr = L.CAROUSEL
    pen.ring(ccx, ccy, cr + 0.6, 0.12, (200, 160, 60, 255))
    pen.ring(ccx, ccy, cr + 0.9, 0.04, INK)
    pen.ring(ccx, ccy, cr + 0.52, 0.015, (255, 240, 200, 120))
    x0, y0, x1, y1 = R("carousel")
    for sx, sy in ((x0 + 1.2, y0 + 1.2), (x1 - 1.2, y0 + 1.2), (x0 + 1.2, y1 - 1.2), (x1 - 1.2, y1 - 1.2)):
        pen.poly([(sx + 0.06 + math.cos(math.radians(90 + k * 36)) * (0.6 if k % 2 == 0 else 0.25),
                   sy - 0.06 + math.sin(math.radians(90 + k * 36)) * (0.6 if k % 2 == 0 else 0.25)) for k in range(10)], (0, 0, 0, 60))
        pen.star(sx, sy, 0.6, 0.25, (230, 190, 80, 230), INK)
    rope_posts(pen, [(-10.0, 0.25), (-11.0, 0.25), (-11.7, 0.6)])
    rope_posts(pen, [(-10.0, 3.25), (-11.0, 3.25), (-11.7, 2.9)])
    stencil(pen, -12.1, 4.55, "MIND THE STEP", 0.24, (236, 206, 110, 140))
    balloon(pen, x1 - 1.4, y1 - 2.6, (230, 90, 120), random.Random(21))
    scatter(pen, free, 30, 21, confetti)
    scatter(pen, free, 6, 22, ticket)


def bumpercars_floor(pen, free):
    """Autoscooter: Reifenspuren um die Bahn, Warnstreifen, Kabelkanal von der Nordwand zur Bahn,
    Reifenstapel, Wartebox WAIT HERE, loses Rad, Oelfleck. Freizuhalten: Bahn (-8,4..-3,6/-20,1..-15,3),
    Konsolen NW/S/NO, Vent (-2,2/-20,3)."""
    x0, y0, x1, y1 = R("bumpercars")
    ax0, ay0, ax1, ay1 = G.shape(L.ARENA).bounds
    acx, acy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    for k in range(5):
        r = 3.2 + k * 0.25
        pen.d.arc([pen.P(acx - r, acy + r), pen.P(acx + r, acy - r)], 200 + k * 20, 320 + k * 15, fill=(8, 8, 12, 80), width=pen.w(0.15))
    for xx in (x0 + 0.4, x1 - 0.4):
        y = y0 + 0.5
        k = 0
        while y < y1 - 0.5:
            pen.hpoly([(xx - 0.15, y), (xx + 0.15, y + 0.3), (xx + 0.15, y + 0.5), (xx - 0.15, y + 0.2)], (220, 180, 50, 200), None, seed=k)
            y += 0.8
            k += 1
    # Kabelkanal: Gummiwulst von der Nordwand zur Bahnmitte
    pen.hpoly([(-6.3, y1), (-5.7, y1), (-5.7, ay1 + 0.05), (-6.3, ay1 + 0.05)], (36, 34, 40, 255), INK, 0.03, seed=30)
    pen.line([(-6.0, y1 - 0.05), (-6.0, ay1 + 0.1)], (70, 68, 76, 255), 0.03)
    for k in range(5):
        pen.ell(-6.0, y1 - 0.15 - k * 0.16, 0.025, 0.025, (120, 120, 130, 255))
    # Reifenstapel und loses Rad an der Ostseite, Wartebox an der Westseite
    tire(pen, -2.45, -18.55, 0.32, seed=31)
    tire(pen, -2.3, -17.95, 0.3, seed=32)
    pen.hell(-2.9, -19.2, 0.17, 0.17, (40, 40, 44, 255), INK, 0.025, seed=33)
    pen.ell(-2.9, -19.2, 0.07, 0.07, (150, 150, 160, 255), INK, 0.015)
    pen.hrect(-10.2, -18.7, -8.8, -16.8, None, (220, 180, 50, 200), 0.06, seed=34)
    stencil(pen, -9.5, -17.3, "WAIT", 0.3, (220, 180, 50, 170))
    stencil(pen, -9.5, -17.95, "HERE", 0.3, (220, 180, 50, 170))
    pen.hell(-3.2, -16.5, 0.45, 0.25, (10, 8, 14, 120), None, seed=35)
    pen.ell(-3.35, -16.4, 0.14, 0.05, (120, 130, 160, 60))
    scatter(pen, free, 8, 36, ticket)


def security_floor(pen, free):
    """Security-Nebenraum: Teppich mit Rand, Kabelkanal zur Monitorwand, Fussmatte an der Nordtuer,
    Kaffeeringe, Donutkiste, Papierkorb mit Knuellpapier, Pylone. Freizuhalten: Monitorwand (4,1/-8,1),
    Konsolen SO/NO, Nordtuer x 3,75..6,25."""
    x0, y0, x1, y1 = R("security")
    rnd = random.Random(1301)
    pen.hrect(x0 + 2.0, y0 + 1.2, x1 - 1.2, y0 + 3.6, (70, 40, 50, 230), (160, 130, 60, 255), 0.06, seed=40)
    pen.hrect(x0 + 2.2, y0 + 1.4, x1 - 1.4, y0 + 3.4, None, (160, 130, 60, 200), 0.03, seed=41)
    pen.line([(x0 + 0.6, y1 - 0.8), (x0 + 0.6, y0 + 0.8), (x1 - 1.0, y0 + 0.6)], (20, 20, 26, 220), 0.1)
    pen.hrect(4.3, y1 - 0.75, 5.7, y1 - 0.12, (90, 70, 56, 255), INK, 0.025, seed=42)                  # Fussmatte
    for k in range(6):
        pen.line([(4.4 + k * 0.22, y1 - 0.7), (4.4 + k * 0.22, y1 - 0.17)], (70, 54, 42, 255), 0.02)
    stencil(pen, 5.0, y1 - 0.44, "STAFF", 0.2, (160, 130, 100, 200))
    for (mx, my) in ((5.3, -8.7), (5.55, -8.55)):                                                      # Kaffeeringe
        pen.ring(mx, my, 0.07, 0.015, (80, 50, 30, 160))
    pen.hell(5.15, -8.95, 0.07, 0.07, (240, 236, 230, 255), INK, 0.015, seed=43)                      # Becher
    pen.ell(5.15, -8.95, 0.04, 0.04, (90, 60, 40, 255))
    lowbox(pen, 5.8, -9.75, 6.4, -9.35, 0.12, (230, 200, 150, 255), seed=44)                           # Donutkiste
    for k in range(3):
        pen.ell(5.92 + k * 0.17, -9.55 + 0.12 * K, 0.065, 0.05, ((230, 120, 170), (120, 80, 50), (240, 220, 160))[k] + (255,), INK, 0.012)
        pen.ell(5.92 + k * 0.17, -9.55 + 0.12 * K, 0.02, 0.016, (230, 200, 150, 255))
    pen.hell(3.0, -11.0, 0.19, 0.19, (90, 94, 104, 255), INK, 0.025, seed=45)                           # Papierkorb
    pen.ell(3.0, -11.0, 0.13, 0.13, (50, 52, 60, 255))
    for k in range(3):
        pen.hell(3.0 + rnd.uniform(-0.3, 0.3), -10.6 + rnd.uniform(-0.1, 0.25), 0.06, 0.05, (236, 232, 220, 255), (150, 150, 150, 200), 0.012, seed=46 + k)
    cone(pen, 3.1, -7.1, seed=47)
    scatter(pen, free.difference(box(x0 + 1.5, y0 + 1.0, x1 - 1.0, y0 + 4.0)), 4, 48, lambda p, x, y, r: paper(p, x, y, r))


def substation_floor(pen, free):
    """Umspannhaus: Warnstreifen-Rahmen N/S, Transformator mit Kuehlrippen und Warnlabel, Kabelkanal zum
    Hauptschalter, Kabelbuendel zur Ostwand, Oellache, Brandfleck, HIGH VOLTAGE, Handschuhe, Klemmbrett.
    Freizuhalten: Konsolen N (1,66 / 4,69), O (5,95/-15,9), W Schalter (1,3/-17,2), S (3,22/-18,95),
    Vent (5,4/-17,4)."""
    x0, y0, x1, y1 = R("substation")
    for (a0, a1, b0, b1) in ((x0 + 0.3, x1 - 0.3, y0 + 0.3, y0 + 0.5), (x0 + 0.3, x1 - 0.3, y1 - 0.5, y1 - 0.3)):
        k = 0
        xa = a0
        while xa < a1:
            pen.poly([(xa, b0), (min(a1, xa + 0.2), b0), (min(a1, xa + 0.3), b1), (min(a1, xa + 0.1), b1)],
                     (220, 180, 50, 230) if k % 2 == 0 else (30, 28, 30, 230))
            xa += 0.2
            k += 1
    # Transformator: Oellache darunter, Kasten mit Kuehlrippen, Isolatoren oben, Warnlabel
    tx0, ty0, tx1, ty1 = 2.5, -18.3, 4.1, -17.3
    pen.hell(tx0 + 0.9, ty0 - 0.05, 0.7, 0.3, (10, 8, 14, 140), None, seed=50)
    pen.ell(tx0 + 0.6, ty0 - 0.0, 0.2, 0.05, (120, 130, 160, 70))
    lowbox(pen, tx0, ty0, tx1, ty1, 0.5, (96, 110, 100, 255), (66, 78, 70, 255), seed=51)
    for k in range(9):
        pen.line([(tx0 + 0.15 + k * 0.165, ty0 + 0.04), (tx0 + 0.15 + k * 0.165, ty0 + 0.5 * K - 0.04)], (40, 48, 44, 255), 0.03)
    for k in range(3):
        px_ = tx0 + 0.35 + k * 0.45
        pen.ell(px_, ty1 + 0.5 * K - 0.1, 0.08, 0.05, (120, 150, 140, 255), INK, 0.012)
        pen.ell(px_, ty1 + 0.5 * K - 0.02, 0.06, 0.035, (120, 150, 140, 255), INK, 0.012)
    pen.hrect(tx1 - 0.45, ty0 + 0.08, tx1 - 0.1, ty0 + 0.24, (236, 196, 50, 255), INK, 0.012, seed=52)
    pen.poly([(tx1 - 0.25, ty0 + 0.21), (tx1 - 0.31, ty0 + 0.14), (tx1 - 0.27, ty0 + 0.14), (tx1 - 0.3, ty0 + 0.1), (tx1 - 0.23, ty0 + 0.17), (tx1 - 0.27, ty0 + 0.17)], INK)
    # Kabelkanal zum Hauptschalter (W), Kabelbuendel zur FixWiring-Konsole (O, unter dem Vent vorbei)
    pen.hpoly([(1.55, -17.55), (tx0, -17.55), (tx0, -17.85), (1.55, -17.85)], (36, 34, 40, 255), INK, 0.025, seed=53)
    pen.line([(1.6, -17.7), (tx0 - 0.05, -17.7)], (70, 68, 76, 255), 0.03)
    for k, col in enumerate(((200, 60, 50), (60, 120, 200), (230, 190, 60))):
        off = k * 0.06
        pen.hline([(tx1, -17.75 - off), (4.8 + off, -18.55), (5.9 + off * 0.5, -18.4), (6.1 - off, -16.4)], col + (230,), 0.045, seed=54 + k, amp=0.012)
    # Brandfleck mit Funken-Kritzel beim Schalter, HIGH VOLTAGE, Handschuhe, Klemmbrett
    pen.hell(1.9, -16.6, 0.3, 0.2, (10, 8, 10, 110), None, seed=57)
    for a in (20, 70, 120, 160):
        pen.line([(1.9 + math.cos(math.radians(a)) * 0.2, -16.6 + math.sin(math.radians(a)) * 0.15), (1.9 + math.cos(math.radians(a)) * 0.38, -16.6 + math.sin(math.radians(a)) * 0.28)], (20, 16, 20, 120), 0.015)
    stencil(pen, 3.3, -15.7, "HIGH VOLTAGE", 0.24, (236, 196, 50, 150))
    for k, dx in enumerate((0.0, 0.26)):
        pen.hpoly([(1.3 + dx, -18.75), (1.5 + dx, -18.72), (1.55 + dx, -18.45), (1.45 + dx, -18.35), (1.28 + dx, -18.4)], (230, 130, 50, 255), INK, 0.015, seed=58 + k)
    pen.hrect(5.2, -19.1, 5.55, -18.65, (140, 100, 60, 255), INK, 0.015, seed=60)
    pen.rect(5.24, -19.05, 5.51, -18.72, (236, 232, 220, 255))
    pen.rect(5.32, -18.72, 5.43, -18.66, (90, 90, 100, 255))
    scatter(pen, free.difference(box(tx0 - 0.4, ty0 - 0.4, tx1 + 0.4, ty1 + 0.6)), 3, 61, lambda p, x, y, r: stain(p, x, y, r, (8, 8, 10, 40)))


def firstaid_floor(pen, free):
    """Sanitaetszelt: Matte mit rotem Kreuz, Vorhangschiene vor der Liege, Erste-Hilfe-Koffer, Trage an
    der Westwand, Verbandrollen, Flasche, QUIET PLEASE. Freizuhalten: Scanner (19,5/-18), Liege
    (19,9..21,7/-20,6..-19), Konsole NO (21,86/-15,05), Vent (18,2/-15,2), Westtuer y -19,5..-17."""
    x0, y0, x1, y1 = R("firstaid")
    mx, my = 20.0, -16.4
    pen.hrect(mx - 1.2, my - 1.0, mx + 1.2, my + 1.0, (230, 232, 228, 255), (150, 160, 160, 255), 0.05, seed=70)
    pen.rect(mx - 0.3, my - 0.8, mx + 0.3, my + 0.8, (200, 50, 50, 255))
    pen.rect(mx - 0.8, my - 0.3, mx + 0.8, my + 0.3, (200, 50, 50, 255))
    pen.line([(x0 + 0.5, -19.2), (x1 - 0.4, -19.2)], (120, 130, 140, 220), 0.05)                      # Vorhangschiene
    for k in range(7):
        pen.ell(x0 + 0.7 + k * 0.6, -19.2, 0.06, 0.06, (200, 205, 210, 255), INK, 0.015)
    pen.hpoly([(x0 + 0.5, -19.15), (x0 + 1.3, -19.15), (x0 + 1.25, -18.75), (x0 + 0.55, -18.75)], (150, 200, 210, 160), (90, 130, 140, 200), 0.015, seed=71)   # Vorhangbausch
    lowbox(pen, 17.75, -17.4, 18.3, -17.05, 0.22, (240, 240, 236, 255), (210, 210, 206, 255), seed=72)   # Koffer
    pen.rect(17.98, -17.33 + 0.22 * K, 18.07, -17.12 + 0.22 * K, (200, 50, 50, 255))
    pen.rect(17.92, -17.27 + 0.22 * K, 18.13, -17.18 + 0.22 * K, (200, 50, 50, 255))
    pen.hpoly([(17.65, -20.85), (18.25, -20.85), (18.25, -19.65), (17.65, -19.65)], (210, 200, 170, 255), INK, 0.025, seed=73)   # Trage
    for xx in (17.6, 18.3):
        pen.line([(xx, -21.0), (xx, -19.5)], (120, 80, 50, 255), 0.04)
    pen.line([(17.72, -20.3), (18.18, -20.3)], (150, 140, 110, 255), 0.015)
    for k, (bx, by) in enumerate(((18.9, -20.4), (19.2, -20.55))):                                       # Verbandrollen
        pen.hell(bx, by, 0.09, 0.09, (246, 244, 238, 255), INK, 0.015, seed=74 + k)
        pen.ell(bx, by, 0.035, 0.035, (210, 206, 196, 255))
        pen.line([(bx + 0.08, by), (bx + 0.3, by - 0.05)], (246, 244, 238, 255), 0.04)
    pen.hell(18.6, -16.0, 0.06, 0.1, (90, 150, 220, 255), INK, 0.015, seed=76)                          # Flasche
    pen.rect(18.56, -15.92, 18.64, -15.86, (240, 240, 240, 255))
    stencil(pen, 21.3, -17.7, "QUIET", 0.22, (150, 160, 160, 200))
    stencil(pen, 21.3, -18.05, "PLEASE", 0.22, (150, 160, 160, 200))


def office_floor(pen, free):
    """Parkbuero: Teppich mit Stern, abgelaufener Durchgangsstreifen N-S, Aktenschrank an der Westwand,
    Papierkorb, Topfpflanze, Kaffeebecher, Fundkiste, verstreute Papiere. Freizuhalten: Lageplan
    (-1,5/-8,3), Konsolen N (-5,45 / -3,65 / 1,2) und SO (1,45/-10,95), Vent (-5,3/-10,9), Gaenge x -3,5..-1."""
    x0, y0, x1, y1 = R("office")

    def lane(d):
        d.rectangle([pen.P(-3.0, y1), pen.P(-1.5, y0)], fill=(255, 240, 220, 26))
    pen.soft(lane, 0.3)
    pen.hrect(x0 + 1.5, y0 + 1.5, x1 - 1.5, y1 - 2.0, (120, 40, 50, 220), (200, 160, 70, 255), 0.08, seed=80)
    pen.hrect(x0 + 1.8, y0 + 1.8, x1 - 1.8, y1 - 2.3, None, (200, 160, 70, 200), 0.04, seed=81)
    pen.star((x0 + x1) / 2, (y0 + y1) / 2 - 0.2, 0.9, 0.38, (220, 180, 80, 200))
    lowbox(pen, -5.85, -9.45, -5.3, -8.6, 0.5, (150, 154, 164, 255), (104, 108, 118, 255), seed=82)       # Aktenschrank
    for k in range(3):
        pen.rect(-5.8, -9.4 + k * 0.08, -5.35, -9.37 + k * 0.08, (70, 72, 80, 255))
        pen.rect(-5.62, -9.42 + k * 0.08, -5.53, -9.39 + k * 0.08, (200, 200, 210, 255))
    pen.hell(-4.9, -8.0, 0.16, 0.16, (90, 94, 104, 255), INK, 0.025, seed=83)                             # Papierkorb
    pen.ell(-4.9, -8.0, 0.11, 0.11, (50, 52, 60, 255))
    pen.hell(-4.62, -8.18, 0.06, 0.05, (236, 232, 220, 255), (150, 150, 150, 200), 0.012, seed=84)
    pen.hell(1.55, -9.2, 0.2, 0.2, (150, 80, 50, 255), INK, 0.025, seed=85)                               # Topfpflanze
    pen.ell(1.55, -9.2, 0.15, 0.15, (70, 50, 36, 255))
    for a in range(0, 360, 45):
        pen.hell(1.55 + math.cos(math.radians(a)) * 0.16, -9.2 + math.sin(math.radians(a)) * 0.16, 0.11, 0.065, (60, 130, 70, 255), (30, 70, 40, 255), 0.012, seed=86 + a)
    pen.ell(1.55, -9.2, 0.07, 0.07, (80, 160, 90, 255), (30, 70, 40, 255), 0.012)
    pen.ring(-0.6, -9.35, 0.07, 0.015, (80, 50, 30, 160))                                                 # Kaffeering + Becher
    pen.hell(-0.45, -9.5, 0.07, 0.07, (240, 236, 230, 255), INK, 0.015, seed=90)
    pen.ell(-0.45, -9.5, 0.04, 0.04, (90, 60, 40, 255))
    lowbox(pen, -0.05, -11.2, 0.65, -10.75, 0.3, (190, 150, 100, 255), (140, 104, 66, 255), seed=91)       # Fundkiste
    pen.ell(0.12, -10.95 + 0.3 * K, 0.08, 0.07, (230, 120, 170, 255), INK, 0.012)
    pen.line([(0.3, -11.1 + 0.3 * K), (0.55, -10.85 + 0.3 * K)], (60, 60, 70, 255), 0.03)
    pen.ell(0.57, -10.84 + 0.3 * K, 0.04, 0.03, (200, 60, 60, 255), INK, 0.01)
    stencil(pen, 0.3, -10.65, "LOST+FOUND", 0.11, (90, 60, 40, 255))
    scatter(pen, free.difference(box(-3.6, y0, -0.9, y1)), 7, 92, lambda p, x, y, r: paper(p, x, y, r))


def coldstore_floor(pen, free):
    """Kuehlhaus: Frostflecken, Abfluss, Streifenvorhang am Nordtor, Eisstapel, Schmelzwasser, frostige
    Fussspuren von der Westtuer zur Truhe, Nass-Schild, Eimer mit Wischmopp, Eiskristalle in den Ecken.
    Freizuhalten: Truhe (9,4..11,4/-16,9..-15,5), Konsolen N (13,19) / O (14,45) / S (10/-19,8), Vent (14,3/-20,3)."""
    x0, y0, x1, y1 = R("coldstore")
    rnd = random.Random(41)

    def frost(d):
        for _ in range(16):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            r = rnd.uniform(0.4, 1.0)
            d.ellipse([pen.P(x - r, y + r), pen.P(x + r, y - r)], fill=(240, 250, 255, 70))
        for (px_, py_, r) in ((10.4, -17.5, 0.5), (12.3, -18.2, 0.4), (9.8, -18.6, 0.35)):
            d.ellipse([pen.P(px_ - r, py_ + r * 0.5), pen.P(px_ + r, py_ - r * 0.5)], fill=(120, 170, 210, 90))
    pen.soft(frost, 0.25)
    drain(pen, (x0 + x1) / 2, y0 + 3.0)
    for k in range(9):                                                                                     # Streifenvorhang
        xx = 10.65 + k * 0.28
        pen.rect(xx - 0.1, y1 - 0.75, xx + 0.1, y1, (230, 240, 250, 110), (180, 200, 220, 160), 0.01)
    pen.rect(10.5, y1 - 0.04, 13.0, y1, (120, 130, 150, 255))
    for k, (cx_, cy_, col) in enumerate(((12.85, -19.55, (250, 236, 220)), (13.35, -19.45, (236, 190, 210)), (13.1, -19.1, (210, 236, 220)))):   # Eisstapel
        lowbox(pen, cx_ - 0.3, cy_ - 0.2, cx_ + 0.3, cy_ + 0.2, 0.3, col + (255,), dim(col, 0.8), seed=100 + k)
        pen.rect(cx_ - 0.22, cy_ - 0.05 + 0.3 * K, cx_ + 0.22, cy_ + 0.02 + 0.3 * K, (90, 140, 190, 255))
    footprints(pen, [(9.1, -17.3), (9.9, -17.6), (10.6, -17.3)], rnd, (200, 230, 250, 90))
    pen.hpoly([(11.25, -19.05), (11.55, -19.05), (11.4, -18.55)], (236, 196, 50, 255), INK, 0.015, seed=104)      # Nass-Schild
    stencil(pen, 11.4, -18.86, "!", 0.14, INK)
    pen.hell(14.55, -19.0, 0.17, 0.17, (200, 60, 50, 255), INK, 0.025, seed=105)                               # Eimer + Mopp
    pen.ell(14.55, -19.0, 0.12, 0.12, (130, 170, 200, 255))
    pen.line([(14.5, -18.9), (14.1, -18.0)], (150, 110, 70, 255), 0.03)
    pen.hell(14.08, -17.95, 0.1, 0.07, (220, 220, 210, 255), INK, 0.012, seed=106)
    for (kx, ky, s_) in ((9.5, -20.5, 0.3), (14.4, -14.9, 0.22), (9.4, -15.0, 0.2)):                         # Eiskristalle
        for a in range(0, 360, 60):
            pen.line([(kx, ky), (kx + math.cos(math.radians(a)) * s_, ky + math.sin(math.radians(a)) * s_)], (230, 245, 255, 150), 0.018)
            for f in (0.5, 0.75):
                px_, py_ = kx + math.cos(math.radians(a)) * s_ * f, ky + math.sin(math.radians(a)) * s_ * f
                for da in (-35, 35):
                    pen.line([(px_, py_), (px_ + math.cos(math.radians(a + da)) * s_ * 0.2, py_ + math.sin(math.radians(a + da)) * s_ * 0.2)], (230, 245, 255, 130), 0.012)


def musicbooth_floor(pen, free):
    """Musikzentrale: runder DJ-Teppich mit Schallplattenmotiv, Kabel zu Lautsprecher und Mischpult,
    Plattenkisten, Mikrofonstaender, Klebeband-Kreuze, Kaffeebecher mit Setlist, Noten.
    Freizuhalten: Lautsprecher (16,4..18/9,9..11,1), Mischpult (18,8..21,8/9,9..10,9), Konsolen
    NW (16,7/16,25), O (21,95/11,56), NO (21,5/15,6), Vent (21,8/16,1), Westtor y 12..14,5."""
    x0, y0, x1, y1 = R("musicbooth")
    cx, cy = 19.25, 13.3
    pen.hell(cx, cy, 2.0, 2.0, (28, 24, 34, 255), (150, 90, 160, 255), 0.06, seed=110)
    for r in (1.7, 1.45, 1.2, 0.95):
        pen.ring(cx, cy, r, 0.012, (70, 60, 80, 255))
    pen.hell(cx, cy, 0.62, 0.62, (200, 60, 90, 255), INK, 0.03, seed=111)
    pen.ell(cx, cy, 0.09, 0.09, (28, 24, 34, 255), INK, 0.012)
    pen.poly([(cx - 1.5, cy + 1.2), (cx - 0.9, cy + 1.7), (cx - 1.0, cy + 1.5)], (255, 255, 255, 50))
    for k in range(2):                                                                                  # Kabel
        pen.hline([(x0 + 1.2 + k * 0.25, y0 + 1.7), (x0 + 1.6 + k * 0.25, y0 + 2.6), (x0 + 3.0, y0 + 2.8 + k * 0.2), (x0 + 4.6, y0 + 1.5 + k * 0.1)], (18, 16, 20, 220), 0.05, seed=112 + k, amp=0.02)
    pen.hline([(21.3, 15.1), (21.45, 13.6), (21.0, 11.0)], (18, 16, 20, 220), 0.05, seed=114, amp=0.03)
    for (nx, ny) in ((x0 + 1.5, y1 - 1.4), (x0 + 2.8, y1 - 0.9), (x1 - 1.4, y1 - 1.5)):                  # Noten
        pen.ell(nx, ny, 0.12, 0.09, (200, 160, 220, 150))
        pen.line([(nx + 0.1, ny), (nx + 0.1, ny + 0.4)], (200, 160, 220, 150), 0.03)
    for k, cx_ in enumerate((17.6, 18.3)):                                                              # Plattenkisten
        lowbox(pen, cx_ - 0.32, 15.3, cx_ + 0.32, 15.8, 0.35, (150, 110, 70, 255), (104, 74, 46, 255), seed=116 + k)
        for i in range(7):
            pen.line([(cx_ - 0.26 + i * 0.085, 15.34 + 0.35 * K), (cx_ - 0.26 + i * 0.085, 15.76 + 0.35 * K)], ((60, 60, 70), (200, 60, 90), (60, 120, 200), (230, 190, 60))[i % 4] + (255,), 0.04)
    pen.hell(21.0, 12.8, 0.2, 0.11, (60, 60, 68, 255), INK, 0.02, seed=118)                                # Mikrofonstaender
    pen.line([(21.0, 12.8), (21.0, 12.8 + 1.4 * K)], INK, 0.045)
    pen.line([(21.0, 12.8), (21.0, 12.8 + 1.4 * K)], (150, 150, 160, 255), 0.025)
    pen.ell(21.0, 12.8 + 1.4 * K + 0.06, 0.06, 0.08, (60, 60, 68, 255), INK, 0.015)
    for (tx, ty) in ((18.3, 11.9), (21.0, 11.9), (16.9, 14.9)):                                           # Klebeband-Kreuze
        for sgn in (1, -1):
            pen.line([(tx - 0.14, ty - 0.14 * sgn), (tx + 0.14, ty + 0.14 * sgn)], (240, 240, 230, 220), 0.04)
    pen.hell(20.0, 11.4, 0.07, 0.07, (240, 236, 230, 255), INK, 0.015, seed=119)                           # Becher + Setlist
    pen.ell(20.0, 11.4, 0.04, 0.04, (90, 60, 40, 255))
    paper(pen, 20.3, 11.5, random.Random(5))


def shooting_floor(pen, free):
    """Schiessbude: Preisregal hinter der Theke mit Plueschbaeren und Entenreihe auf dem Laufband,
    Standlinie STAND HERE vor der Theke mit Fussspuren, Preiskisten, Ballkorb, Huelsen und Popcorn.
    Freizuhalten: Theke (-19..-11/13,4..14,2), Hau den Lukas (-19,95..-19,05/11,1..11,75, Use -18,5/11,3),
    Konsolen N, Vent (-19,3/9,3), Suedtor x -16,5..-14, Osttor y 11..13,5."""
    x0, y0, x1, y1 = R("shooting")
    th = next(G.shape(s_) for s_, k_ in L.GLASS if k_ == "theke").bounds
    pen.hrect(x0 + 0.5, th[3] + 0.1, x1 - 0.5, y1 - 0.1, (90, 40, 40, 255), INK, 0.04, seed=120)
    pen.rect(x0 + 0.55, th[3] + 0.55, x1 - 0.55, th[3] + 0.6, (60, 26, 26, 255))                            # Regalbrett
    pen.rect(x0 + 0.55, y1 - 1.05, x1 - 0.55, y1 - 1.0, (60, 26, 26, 255))
    for k in range(int((x1 - x0 - 1.0) / 0.6)):                                                            # Baeren
        px_ = x0 + 0.8 + k * 0.6
        col = ((230, 120, 170), (120, 190, 230), (240, 210, 90), (160, 230, 140))[k % 4]
        plush(pen, px_, y1 - 0.95, col + (255,), seed=121 + k, s=0.95)
    # Entenreihe auf dem Laufband: ueber den Baeren (unter der Theke waere sie vom Thekensprite verdeckt)
    dy = y1 - 0.5
    pen.rect(x0 + 0.6, dy - 0.1, x1 - 0.6, dy + 0.1, (50, 46, 56, 255), INK, 0.015)
    for k in range(int((x1 - x0 - 1.4) / 0.5)):
        dx = x0 + 0.95 + k * 0.5
        pen.hell(dx, dy + 0.01, 0.11, 0.08, (236, 200, 60, 255), INK, 0.015, seed=130 + k)
        pen.ell(dx + 0.08, dy + 0.08, 0.06, 0.055, (236, 200, 60, 255), INK, 0.012)
        pen.poly([(dx + 0.13, dy + 0.08), (dx + 0.2, dy + 0.06), (dx + 0.13, dy + 0.04)], (230, 110, 50, 255))
        pen.ell(dx + 0.1, dy + 0.095, 0.012, 0.012, INK)
    for k, (bx, by, col) in enumerate(((x1 - 1.4, th[3] + 1.0, (200, 60, 90)), (x1 - 0.9, th[3] + 0.95, (60, 120, 200)))):   # Preiskisten
        crate(pen, bx, by, 0.42, 0.3, 0.3, col + (255,), seed=140 + k)
    xa, xb = th[0] + 0.5, th[2] - 0.5
    x = xa
    while x < xb:
        pen.hline([(x, th[1] - 0.55), (min(xb, x + 0.3), th[1] - 0.55)], (236, 206, 110, 170), 0.05, seed=int(x * 10))   # Standlinie
        x += 0.5
    stencil(pen, -13.0, th[1] - 0.95, "STAND HERE", 0.22, (236, 206, 110, 150))
    for k in range(4):
        px_ = th[0] + 1.6 + k * 1.6
        pen.ell(px_ - 0.1, th[1] - 0.82, 0.06, 0.09, (0, 0, 0, 45))
        pen.ell(px_ + 0.1, th[1] - 0.8, 0.06, 0.09, (0, 0, 0, 45))
    pen.hell(-10.9, 9.3, 0.3, 0.3, (120, 90, 60, 255), INK, 0.03, seed=150)                                  # Ballkorb
    pen.ell(-10.9, 9.3, 0.22, 0.22, (80, 58, 38, 255))
    for k, (dx, dy) in enumerate(((-0.08, 0.05), (0.08, 0.06), (0.0, -0.08), (-0.02, 0.0))):
        pen.ell(-10.9 + dx, 9.3 + dy, 0.07, 0.07, ((200, 60, 60), (60, 120, 200), (236, 200, 60), (240, 240, 230))[k] + (255,), INK, 0.012)
    stencil(pen, -12.7, 11.4, "WIN A PRIZE", 0.24, (236, 206, 110, 130))
    south = free.intersection(box(x0, y0, x1, th[1] - 0.3))
    scatter(pen, south, 30, 51, lambda p, x, y, r: p.ell(x, y, 0.03, 0.015, (210, 170, 70, 220)))
    scatter(pen, south, 14, 52, popcorn)


def ghosttrain_floor(pen, free):
    """Geisterbahn: Schmalspur mit Schwellen entlang der Fahrt, Spinnweben, Grabstein, Knochen, Skeletthand,
    Nebelschwaden, gruene Pfuetzen, Fledermausschatten. Freizuhalten: Tunnelwaende, Vent (-16,6/-5),
    Kamera (-13,4/-4,4), Fahrweg."""
    ride = L.GHOST_RIDE
    pen.line(ride, (40, 34, 48, 255), 0.56)
    for (ax, ay), (bx, by) in zip(ride, ride[1:]):                                                       # Schwellen
        ln = math.hypot(bx - ax, by - ay)
        n = max(1, int(ln / 0.32))
        nx, ny = -(by - ay) / ln, (bx - ax) / ln
        ux, uy = (bx - ax) / ln, (by - ay) / ln
        for k in range(n):
            t = (k + 0.5) / n
            px_, py_ = ax + (bx - ax) * t, ay + (by - ay) * t
            pen.hpoly([(px_ + nx * 0.24 - ux * 0.05, py_ + ny * 0.24 - uy * 0.05), (px_ + nx * 0.24 + ux * 0.05, py_ + ny * 0.24 + uy * 0.05),
                       (px_ - nx * 0.24 + ux * 0.05, py_ - ny * 0.24 + uy * 0.05), (px_ - nx * 0.24 - ux * 0.05, py_ - ny * 0.24 - uy * 0.05)],
                      (84, 60, 50, 255), (30, 20, 24, 255), 0.012, seed=k)
    for off in (-0.16, 0.16):
        pts = []
        for i in range(len(ride)):
            a = ride[max(0, i - 1)]; b = ride[min(len(ride) - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1
            pts.append((ride[i][0] - dy / n * off, ride[i][1] + dx / n * off))
        pen.line(pts, (30, 26, 34, 255), 0.07)
        pen.line(pts, (124, 120, 138, 255), 0.04)
    x0, y0, x1, y1 = R("ghosttrain")
    for (wx, wy, sx, sy) in ((x0, y1, 1, -1), (x1, y1, -1, -1), (x0, y0, 1, 1), (x1, y0, -1, 1)):          # Spinnweben
        for k in range(5):
            a = math.radians(k * 22.5)
            pen.line([(wx, wy), (wx + sx * math.cos(a) * 1.3, wy + sy * math.sin(a) * 1.3)], (200, 200, 210, 110), 0.015)
        for r in (0.4, 0.75, 1.1):
            pts = [(wx + sx * math.cos(math.radians(k * 22.5)) * r, wy + sy * math.sin(math.radians(k * 22.5)) * r) for k in range(5)]
            pen.hline(pts, (200, 200, 210, 100), 0.012, seed=int(r * 10), amp=0.01)
    for (ex, ey) in ((x0 + 0.5, y0 + 2.4), (x1 - 0.5, y1 - 0.8), (x0 + 0.6, y1 - 3.2)):                   # Augen
        pen.ell(ex, ey, 0.3, 0.2, (120, 255, 130, 40))
        for dx in (-0.09, 0.09):
            pen.ell(ex + dx, ey, 0.06, 0.04, (140, 255, 140, 200))
    # Grabstein, Knochen, Skeletthand, Fledermausschatten
    pen.hpoly([(-16.85, -6.95), (-16.45, -6.95), (-16.45, -6.7), (-16.5, -6.58), (-16.65, -6.52), (-16.8, -6.58), (-16.85, -6.7)], (110, 112, 120, 255), INK, 0.02, seed=160)
    stencil(pen, -16.65, -6.75, "RIP", 0.11, (40, 40, 48, 255))
    for (bx, by, a) in ((-16.5, -10.25, 0.3), (-13.6, -5.65, -0.5), (-13.4, -9.9, 1.1)):
        c, s_ = math.cos(a), math.sin(a)
        pen.line([(bx - c * 0.18, by - s_ * 0.18), (bx + c * 0.18, by + s_ * 0.18)], INK, 0.07)
        pen.line([(bx - c * 0.18, by - s_ * 0.18), (bx + c * 0.18, by + s_ * 0.18)], (226, 220, 200, 255), 0.04)
        for e in (-1, 1):
            for f in (-1, 1):
                pen.ell(bx + c * 0.19 * e - s_ * 0.035 * f, by + s_ * 0.19 * e + c * 0.035 * f, 0.035, 0.035, (226, 220, 200, 255), INK, 0.012)
    hx, hy = -13.25, -9.2
    for k, a in enumerate((150, 170, 190, 210, 235)):                                                    # Skeletthand aus der Ostwand
        ln = 0.28 if k in (1, 2, 3) else 0.2
        pen.line([(hx, hy), (hx + math.cos(math.radians(a)) * ln, hy + math.sin(math.radians(a)) * ln)], INK, 0.045)
        pen.line([(hx, hy), (hx + math.cos(math.radians(a)) * ln, hy + math.sin(math.radians(a)) * ln)], (226, 220, 200, 255), 0.025)
        pen.ell(hx + math.cos(math.radians(a)) * ln * 0.55, hy + math.sin(math.radians(a)) * ln * 0.55, 0.018, 0.018, INK)
    pen.hell(hx + 0.08, hy + 0.02, 0.1, 0.09, (226, 220, 200, 255), INK, 0.02, seed=161)
    for (bx, by) in ((-14.2, -8.05), (-15.9, -4.55)):
        pen.poly([(bx, by), (bx - 0.14, by + 0.06), (bx - 0.1, by - 0.01), (bx - 0.16, by - 0.03), (bx - 0.05, by - 0.05), (bx, by - 0.08),
                  (bx + 0.05, by - 0.05), (bx + 0.16, by - 0.03), (bx + 0.1, by - 0.01), (bx + 0.14, by + 0.06)], (8, 4, 12, 150))

    def fog(d):
        for (fx, fy, r) in ((-15.8, -8.0, 0.9), (-14.0, -5.9, 0.7), (-15.2, -10.3, 0.8)):
            d.ellipse([pen.P(fx - r, fy + r * 0.45), pen.P(fx + r, fy - r * 0.45)], fill=(200, 210, 230, 34))
        for (gx, gy, r) in ((-14.2, -6.9, 0.22), (-16.3, -10.4, 0.18)):
            d.ellipse([pen.P(gx - r, gy + r * 0.6), pen.P(gx + r, gy - r * 0.6)], fill=(90, 230, 110, 90))
    pen.soft(fog, 0.2)


def ferriswheel_floor(pen, free):
    """Riesenrad-Lichtung: Kopfsteinring unter dem Rad, Blumenbeete (handgezeichnet), Einstiegsmatte RIDE
    mit Absperrseilen, Bahnsteig B der Pendelbahn (NW), zwei Baenke, ausgetretene Graswege.
    Freizuhalten: Rad (-0,5/13 r 3,2), Nav-Konsolen (3,6/19,35, -2,9/19,35, 4,45/10,56, -2,18/9,05,
    -5,44/10,32), Vent (-4,3/16), Einstieg (0,4/9,2), Nordrand x -2..2,5 ruhig (hinter dem Radkranz)."""
    wx, wy = L.WHEEL

    def worn(d):
        for pts in (((0.0, 8.6), (0.0, 9.6)), ((4.9, 12.6), (3.6, 12.9)), ((-5.9, 12.25), (-4.5, 12.6))):
            d.line([pen.P(*p) for p in pts], fill=(40, 30, 20, 50), width=pen.w(1.0))
    pen.soft(worn, 0.3)
    pen.hell(wx, wy, 3.95, 3.95, (118, 110, 102, 255), INK, 0.05, seed=170)
    for k in range(30):                                                                                  # Kopfsteinring
        a0, a1 = k * math.tau / 30, (k + 1) * math.tau / 30
        pts = [(wx + math.cos(a0) * 3.25, wy + math.sin(a0) * 3.25), (wx + math.cos(a1) * 3.25, wy + math.sin(a1) * 3.25),
               (wx + math.cos(a1) * 3.9, wy + math.sin(a1) * 3.9), (wx + math.cos(a0) * 3.9, wy + math.sin(a0) * 3.9)]
        pen.hpoly([(x + (wx - x) * 0.03, y + (wy - y) * 0.03) for x, y in pts], (132 + (k % 3) * 8, 122 + (k % 3) * 6, 112, 255), (60, 52, 47, 255), 0.02, seed=171 + k)
    x0, y0, x1, y1 = R("ferriswheel")
    beds(pen, (x0 + 1.1, y0 + 1.0, x1 - 1.1, y1 - 1.3), 71)
    pen.hrect(-0.1, 8.85, 0.9, 9.55, (176, 52, 62, 255), (236, 206, 110, 255), 0.04, seed=180)               # Einstiegsmatte
    stencil(pen, 0.4, 9.2, "RIDE", 0.24, (236, 206, 110, 255))
    rope_posts(pen, [(-1.7, 8.8), (-1.7, 9.8)])
    rope_posts(pen, [(1.9, 8.8), (1.9, 9.8)])
    pen.hrect(-5.3, 19.0, -3.9, 19.55, (150, 110, 70, 255), INK, 0.03, seed=181)                           # Bahnsteig B
    for k in range(5):
        pen.line([(-5.2 + k * 0.28, 19.04), (-5.2 + k * 0.28, 19.51)], (104, 74, 46, 255), 0.015)
    pen.line([(-5.25, 19.45), (-3.95, 19.45)], (236, 206, 110, 255), 0.04)
    for (bx, by) in ((-5.2, 14.05), (4.3, 14.6)):                                                        # Baenke
        lowbox(pen, bx - 0.6, by - 0.22, bx + 0.6, by + 0.22, 0.45, (150, 110, 70, 255), (104, 74, 46, 255), seed=182)
        for k in range(3):
            pen.line([(bx - 0.55, by - 0.15 + k * 0.14 + 0.45 * K), (bx + 0.55, by - 0.15 + k * 0.14 + 0.45 * K)], (104, 74, 46, 255), 0.015)
    scatter(pen, free.difference(box(-2.5, 18.5, 3.0, 20)), 20, 183, confetti)


def lighttower_floor(pen, free):
    """Lichtturm-Hof: Pflasterkreis, Blumenring, Beete, Generator mit Kabel zum Turm, Sandsaecke, Bodenscheinwerfer.
    Freizuhalten: Turm (11,8/13,2 r 1,2), Konsolen O (14,45/11,08) und N (13,14/16,74), Vent (9,4/16,6)."""
    tx, ty = L.TOWER
    pen.hell(tx, ty, 2.2, 2.2, (120, 112, 104, 255), INK, 0.05, seed=190)
    for k in range(16):
        a = math.radians(k * 22.5)
        pen.hell(tx + math.cos(a) * 2.6, ty + math.sin(a) * 2.6, 0.22, 0.18, ((220, 90, 120), (240, 210, 90), (200, 200, 240))[k % 3] + (255,), INK, 0.02, seed=191 + k)
    beds(pen, R("lighttower"), 81)
    lowbox(pen, 13.6, 13.65, 14.8, 14.35, 0.5, (212, 177, 60, 255), (160, 128, 40, 255), seed=200)          # Generator
    pen.rect(13.7, 13.72, 14.2, 13.65 + 0.5 * K - 0.03, (50, 50, 56, 255), INK, 0.02)
    for k in range(5):
        pen.line([(13.75 + k * 0.1, 13.76), (13.75 + k * 0.1, 13.65 + 0.5 * K - 0.06)], (30, 30, 34, 255), 0.02)
    pen.ell(14.5, 13.9 + 0.5 * K, 0.08, 0.06, (80, 80, 88, 255), INK, 0.015)
    pen.hline([(13.6, 13.9), (12.9, 13.6), (12.3, 13.2)], (20, 20, 24, 220), 0.06, seed=201, amp=0.02)
    for k, (sx, sy) in enumerate(((13.5, 14.6), (13.95, 14.75), (14.45, 14.7))):                           # Sandsaecke
        pen.hell(sx, sy, 0.24, 0.13, (190, 170, 130, 255), INK, 0.02, seed=202 + k)
        pen.line([(sx - 0.15, sy), (sx + 0.15, sy)], (150, 130, 95, 255), 0.012)
    pen.hrect(10.0, 15.45, 10.4, 15.8, (60, 60, 68, 255), INK, 0.02, seed=206)                               # Bodenscheinwerfer
    pen.rect(10.05, 15.5, 10.35, 15.75, (255, 236, 180, 255))
    pen.poly([(10.4, 15.5), (11.6, 14.4), (11.6, 15.9), (10.4, 15.75)], (255, 230, 150, 40))


def coaster_floor(pen, free):
    """Bahnhof: Sicherheitsband am Bahnsteig, ENTRY/EXIT, Wartegang aus Seilen, Einstiegsfeld BOARD am
    Pendelwagen-Halt, Groessenschild, Werkzeugkiste mit losem Rad, verlorene Muetze, Tickets, Popcorn.
    Freizuhalten: Kasse (13,8..16,2/-1,5..0,3), Bremshebel (10,6 / 19,4 bei 4,9), Konsolen N (14,64/5,45)
    und W (9,55/-0,29), Vent (20,3/-2,3), Halt A (17,2/5,3)."""
    x0, y0, x1, y1 = R("coaster")
    xa, xb = x0 + 1.5, x1 - 1.5
    x = xa
    k = 0
    while x < xb:                                                                                         # Sicherheitsband
        pen.poly([(x, y1 - 1.05), (min(xb, x + 0.25), y1 - 1.05), (min(xb, x + 0.35), y1 - 0.8), (min(xb, x + 0.1), y1 - 0.8)],
                 (230, 190, 50, 255) if k % 2 == 0 else (30, 26, 30, 255))
        x += 0.25
        k += 1
    pen.hline([(xa, y1 - 0.8), (xb, y1 - 0.8)], INK, 0.025, seed=210)
    pen.hline([(xa, y1 - 1.05), (xb, y1 - 1.05)], INK, 0.025, seed=211)
    for k in range(int((xb - xa) / 0.5)):
        pen.ell(xa + 0.25 + k * 0.5, y1 - 1.3, 0.045, 0.045, (230, 190, 50, 220))
    for (ax, lbl) in ((x0 + 2.5, "ENTRY"), (x1 - 2.5, "EXIT")):
        stencil(pen, ax, y1 - 2.0, lbl, 0.45, (230, 200, 120, 200))
    pen.hrect(16.6, 4.3, 17.8, 4.75, (176, 52, 62, 255), (236, 206, 110, 255), 0.035, seed=212)             # BOARD
    stencil(pen, 17.2, 4.52, "BOARD", 0.2, (236, 206, 110, 255))
    pen.poly([(17.1, 4.85), (17.3, 4.85), (17.3, 4.95), (17.4, 4.95), (17.2, 5.12), (17.0, 4.95), (17.1, 4.95)], (236, 206, 110, 230))
    for k in range(3):                                                                                     # Wartegang
        yy = y0 + 2.0 + k * 1.2
        rope_posts(pen, [(x0 + 1.5, yy), (x0 + 3.5, yy), (x0 + 5.5, yy)])
    # Groessenschild: Pfosten mit Tafel, Crewmate-Silhouette und Messlinie
    sx, sy = 11.7, 2.3
    pen.ell(sx, sy, 0.12, 0.06, (60, 60, 68, 255), INK, 0.015)
    pen.line([(sx, sy), (sx, sy + 1.3 * K)], INK, 0.05)
    pen.line([(sx, sy), (sx, sy + 1.3 * K)], (110, 112, 124, 255), 0.03)
    ty = sy + 1.3 * K
    pen.hrect(sx - 0.32, ty, sx + 0.32, ty + 0.5, (236, 226, 200, 255), INK, 0.025, seed=213)
    pen.ell(sx - 0.14, ty + 0.22, 0.08, 0.1, (90, 180, 220, 255), INK, 0.015)
    pen.rect(sx - 0.21, ty + 0.06, sx - 0.07, ty + 0.22, (90, 180, 220, 255), INK, 0.015)
    pen.line([(sx - 0.26, ty + 0.3), (sx + 0.26, ty + 0.3)], (200, 50, 50, 255), 0.02)
    stencil(pen, sx + 0.1, ty + 0.4, "MIN", 0.1, INK)
    stencil(pen, sx + 0.1, ty + 0.14, "1 m", 0.1, INK)
    lowbox(pen, 18.6, -1.75, 19.2, -1.4, 0.3, (180, 50, 50, 255), (120, 30, 30, 255), seed=214)              # Werkzeugkiste
    pen.rect(18.78, -1.4 + 0.3 * K, 19.02, -1.36 + 0.3 * K, (60, 60, 66, 255), INK, 0.012)
    pen.hell(18.2, -1.1, 0.17, 0.17, (90, 92, 100, 255), INK, 0.025, seed=215)                                # loses Rad
    pen.ell(18.2, -1.1, 0.07, 0.07, (150, 150, 160, 255), INK, 0.015)
    pen.hell(12.4, 3.6, 0.14, 0.1, (200, 50, 50, 255), INK, 0.018, seed=216)                                   # Muetze
    pen.poly([(12.5, 3.55), (12.7, 3.5), (12.55, 3.62)], (200, 50, 50, 255), INK, 0.012)
    scatter(pen, free, 10, 217, ticket)
    scatter(pen, free, 10, 218, popcorn)


def logflume_floor(pen, free):
    """Wildwasserbahn: Pfuetzen und nasse Ufer, Seilpfosten mit Seil entlang des Kanals, Rettungsring,
    SPLASH ZONE, Eimer, Abfluss, Holzschild. Freizuhalten: Kanal (9,5..21,5/-8,7..-7,3), Bruecken 12..14 und
    17..19, Kamera (18,8/-6), Suedweg x 14,1..16,9."""
    x0, y0, x1, y1 = R("logflume")
    wx0, wy0, wx1, wy1 = unary_union([G.shape(w_) for w_ in L.WATER]).bounds
    br = [G.shape(b_).bounds for b_ in L.BRIDGES]
    rnd2 = random.Random(101)

    def puddles(d):
        for yy, h in ((wy0 - 0.5, 0.5), (wy1 + 0.4, 0.4)):
            d.rectangle([pen.P(max(wx0, x0) + 0.3, yy + h), pen.P(min(wx1, x1) - 0.3, yy - h)], fill=(60, 110, 160, 40))
        for _ in range(10):
            x, y = rnd2.uniform(x0 + 1, x1 - 1), rnd2.choice((rnd2.uniform(wy0 - 1.7, wy0 - 0.2), rnd2.uniform(wy1 + 0.1, wy1 + 0.8)))
            r = rnd2.uniform(0.3, 0.8)
            d.ellipse([pen.P(x - r, y + r * 0.5), pen.P(x + r, y - r * 0.5)], fill=(90, 150, 200, 80))
    pen.soft(puddles, 0.06)
    for yy in (wy0 - 0.2, wy1 + 0.2):
        xs = []
        x = max(wx0, x0) + 0.3
        while x < min(wx1, x1) - 0.3:
            if not any(b_[0] - 0.2 < x < b_[2] + 0.2 for b_ in br):
                xs.append(x)
            x += 1.0
        groups = []
        for x in xs:
            if groups and x - groups[-1][-1] < 1.2:
                groups[-1].append(x)
            else:
                groups.append([x])
        for g in groups:
            rope_posts(pen, [(x, yy) for x in g], col=(200, 40, 50, 255), post=(120, 80, 50, 255))
    pen.hell(12.0, -9.9, 0.3, 0.3, (240, 120, 40, 255), INK, 0.03, seed=220)                                 # Rettungsring
    for a in range(0, 360, 90):
        pen.d.arc([pen.P(11.7, -9.6), pen.P(12.3, -10.2)], a + 10, a + 35, fill=(240, 240, 236, 255), width=pen.w(0.1))
    pen.ell(12.0, -9.9, 0.14, 0.14, (84, 98, 108, 255), INK, 0.02)
    stencil(pen, 15.5, -6.45, "SPLASH ZONE", 0.3, (120, 190, 230, 150))
    pen.hell(18.5, -9.9, 0.17, 0.17, (90, 94, 104, 255), INK, 0.025, seed=221)                               # Eimer
    pen.ell(18.5, -9.9, 0.12, 0.12, (70, 130, 190, 255))
    drain(pen, 13.2, -10.4, 0.26)
    # Holzschild am Westufer: Pfosten + Brett "LOG FLUME"
    sx, sy = 12.4, -6.3
    pen.line([(sx, sy), (sx, sy + 1.1 * K)], INK, 0.05)
    pen.line([(sx, sy), (sx, sy + 1.1 * K)], (104, 74, 46, 255), 0.03)
    pen.hrect(sx - 0.55, sy + 1.1 * K, sx + 0.55, sy + 1.1 * K + 0.36, (150, 110, 70, 255), INK, 0.025, seed=222)
    stencil(pen, sx, sy + 1.1 * K + 0.18, "LOG FLUME", 0.14, (236, 226, 200, 255))


def workshop_floor(pen, free):
    """Werkstatt (Stilblatt-Muster): Stellplatz mit Warnmarkierung, aufgebockter Autoscooter mit
    abgenommenem Rad und Oellache, Karussellpferd auf der Plane beim Neuanstrich (Farbeimer, Pinsel),
    Reifenspuren von der Osttuer, Kabeltrommel, Werkzeugkasten, Gummimatte vor dem Regal, Schrauben,
    Kreidenotizen, Saegespaene. Alles flach im Bodenbild (max. 0,5 m hoch), keine Kollider.
    Freizuhalten: Nordtuer x -16,25..-13,75, Osttuer y -17,5..-15, Regal (West), Konsolen an S/O/N-Wand,
    Foto-Monitor an der Nordwand (x -19,9..-17,7, haengt bis y -13,26 in den Raum)."""
    x0, y0, x1, y1 = R("workshop")
    rnd = random.Random(1911)
    K = 0.55
    ink = INK
    # Reifenspuren: zwei leicht wellige Doppelspuren von der Osttuer zum Stellplatz
    for off in (-0.42, 0.42):
        pts = [(x1 - 0.2, -16.25 + off), (x1 - 2.2, -16.3 + off * 1.1), (x0 + 5.4, -16.5 + off * 1.2), (x0 + 3.4, -16.6 + off * 1.2)]
        pen.hline(pts, (12, 10, 14, 60), 0.2, seed=1, amp=0.03)
        pen.hline(pts, (12, 10, 14, 50), 0.08, seed=2, amp=0.03)
    # Stellplatz: gelbe Markierung, abgewetzt (zwei Striche, einer blasser), Ecken schraffiert
    bx0, by0, bx1, by1 = -19.2, -18.1, -15.6, -15.0
    pen.hrect(bx0, by0, bx1, by1, None, (222, 184, 56, 210), 0.09, seed=3, rot=0.0)
    pen.hrect(bx0 + 0.12, by0 + 0.12, bx1 - 0.12, by1 - 0.12, None, (222, 184, 56, 110), 0.05, seed=4)
    for k in range(5):
        a = bx0 + 0.25 + k * 0.5
        pen.hline([(a, by0 + 0.05), (a + 0.35, by0 + 0.4)], (222, 184, 56, 170), 0.07, seed=10 + k)
    pen.text((bx0 + bx1) / 2, by1 - 0.3, "BAY 1", 0.34, (222, 184, 56, 160))
    # Oellache unter dem Wagen (glaenzend: dunkel mit hellem Reflex)
    pen.hell(bx0 + 1.9, by0 + 1.2, 0.75, 0.42, (10, 8, 14, 150), None, seed=5)
    pen.hell(bx0 + 2.3, by0 + 1.05, 0.3, 0.16, (10, 8, 14, 150), None, seed=6)
    pen.ell(bx0 + 1.6, by0 + 1.32, 0.22, 0.06, (120, 130, 160, 70))
    # Autoscooter aufgebockt: Wagenheber (klein) unter der linken Seite, Karosserie 1,0 x 0,7, 0,45 hoch
    cx, cy = bx0 + 1.75, by0 + 1.55
    col = (60, 160, 160, 255)
    pen.poly([(cx - 0.62, cy - 0.3), (cx - 0.5, cy - 0.3), (cx - 0.5, cy - 0.02), (cx - 0.62, cy - 0.02)], (90, 90, 100, 255), ink, 0.03)   # Wagenheber
    front = [(cx - 0.5, cy - 0.35), (cx + 0.5, cy - 0.35), (cx + 0.5, cy - 0.35 + 0.45 * K), (cx - 0.5, cy - 0.35 + 0.45 * K)]
    pen.hpoly(front, (40, 110, 110, 255), ink, 0.04, seed=7)
    top = [(cx - 0.5, cy - 0.35 + 0.45 * K), (cx + 0.5, cy - 0.35 + 0.45 * K), (cx + 0.5, cy + 0.35 + 0.45 * K), (cx - 0.5, cy + 0.35 + 0.45 * K)]
    pen.hpoly(top, col, ink, 0.04, seed=8)
    pen.hpoly([(cx - 0.5, cy - 0.35), (cx + 0.5, cy - 0.35), (cx + 0.55, cy - 0.42), (cx - 0.55, cy - 0.42)], (28, 28, 32, 255), ink, 0.03, seed=9)   # Gummiwulst
    pen.poly([(cx - 0.32, cy - 0.05 + 0.45 * K), (cx + 0.32, cy - 0.05 + 0.45 * K), (cx + 0.26, cy + 0.26 + 0.45 * K), (cx - 0.26, cy + 0.26 + 0.45 * K)], (30, 30, 36, 255), ink, 0.03)   # Sitzmulde
    pen.ell(cx - 0.05, cy + 0.08 + 0.45 * K, 0.12, 0.05, (90, 90, 100, 255), ink, 0.02)                                  # Lenkrad
    pen.star(cx + 0.3, cy + 0.2 + 0.45 * K, 0.1, 0.045, GOLD)
    pen.line([(cx + 0.1, cy + 0.3 + 0.45 * K), (cx + 0.1, cy + 1.3)], (140, 144, 150, 255), 0.025)                           # Stromabnehmer
    pen.ell(cx + 0.1, cy + 1.3, 0.05, 0.05, (120, 230, 255, 255), ink, 0.015)
    # abgenommenes Rad liegt daneben, Radmuttern
    pen.hell(cx + 0.95, cy - 0.5, 0.22, 0.22, (30, 30, 34, 255), ink, 0.035, seed=11)
    pen.ell(cx + 0.95, cy - 0.5, 0.09, 0.09, (150, 150, 160, 255), ink, 0.02)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        pen.ell(cx + 1.3 + math.cos(a) * 0.08, cy - 0.45 + math.sin(a) * 0.08, 0.025, 0.025, (170, 170, 180, 255), ink, 0.01)
    # Gummimatte vor dem Regal (West), geriffelt
    mx0, my0, mx1, my1 = x0 + 1.55, y0 + 0.5, x0 + 2.5, y0 + 2.9
    pen.hrect(mx0, my0, mx1, my1, (66, 66, 74, 255), ink, 0.035, seed=12)
    yy = my0 + 0.12
    while yy < my1 - 0.08:
        pen.line([(mx0 + 0.06, yy), (mx1 - 0.06, yy)], (84, 84, 94, 255), 0.02)
        yy += 0.12
    # Plane mit Karussellpferd zum Neuanstrich (SO-Ecke), Farbeimer, Pinsel, Farbkleckse
    tx0, ty0, tx1, ty1 = x1 - 3.0, y0 + 0.25, x1 - 0.6, y0 + 1.55
    pen.hpoly([(tx0, ty0), (tx1 - 0.1, ty0 + 0.05), (tx1, ty1), (tx0 + 0.15, ty1 - 0.08)], (70, 110, 170, 255), ink, 0.035, seed=13)
    pen.line([(tx0 + 0.3, ty0 + 0.1), (tx0 + 0.3, ty1 - 0.15)], (90, 130, 190, 255), 0.02)                                  # Falten
    pen.line([(tx1 - 0.5, ty0 + 0.2), (tx1 - 0.4, ty1 - 0.1)], (90, 130, 190, 255), 0.02)
    hx, hy = (tx0 + tx1) / 2 + 0.1, (ty0 + ty1) / 2
    horse = [(-0.75, 0.0), (-0.55, 0.12), (-0.2, 0.14), (0.25, 0.1), (0.55, 0.26), (0.7, 0.2), (0.62, 0.0), (0.42, -0.08),
             (0.3, -0.3), (0.2, -0.3), (0.16, -0.1), (-0.2, -0.1), (-0.35, -0.3), (-0.45, -0.3), (-0.42, -0.08), (-0.7, -0.12)]
    pen.poly([(hx + px_ + 0.08, hy + py_ - 0.1) for px_, py_ in horse], (0, 0, 0, 70))
    pen.hpoly([(hx + px_, hy + py_) for px_, py_ in horse], (242, 236, 224, 255), ink, 0.035, seed=14)
    pen.poly([(hx - 0.75, hy), (hx - 0.9, hy - 0.08), (hx - 0.82, hy + 0.1)], (210, 90, 120, 255), ink, 0.025)             # Schweif
    pen.rect(hx - 0.15, hy - 0.04, hx + 0.12, hy + 0.08, (64, 176, 176, 255), ink, 0.02)                                   # Sattel
    pen.ell(hx + 0.58, hy + 0.17, 0.025, 0.025, ink)                                                                         # Auge
    pen.line([(hx - 0.05, hy - 0.2), (hx - 0.05, hy + 0.9)], (230, 190, 90, 255), 0.03)                                      # Stange (abgeschraubt)
    pen.rect(hx + 0.35, hy + 0.25, hx + 0.75, hy + 0.35, (120, 60, 140, 110))                                                  # frisch gestrichener Streifen
    for k, (px_, py_, col) in enumerate(((tx1 - 0.25, ty1 - 0.25, (200, 60, 90)), (tx1 - 0.55, ty1 - 0.22, (230, 190, 70)), (tx0 + 0.25, ty1 - 0.3, (64, 176, 176)))):
        pen.hell(px_, py_, 0.13, 0.13, (200, 200, 205, 255), ink, 0.025, seed=20 + k)                                        # Farbeimer
        pen.ell(px_, py_, 0.09, 0.09, col + (255,))
        pen.ell(px_ + 0.05, py_ - 0.17, 0.06, 0.035, col + (170,))                                                               # Klecks
    pen.line([(tx0 + 0.6, ty0 + 0.25), (tx0 + 0.95, ty0 + 0.35)], (120, 80, 50, 255), 0.03)                                     # Pinsel
    pen.line([(tx0 + 0.95, ty0 + 0.35), (tx0 + 1.1, ty0 + 0.4)], (200, 60, 90, 255), 0.045)
    # Kabeltrommel (NW, unter dem Sicherungskasten), Werkzeugkasten, Schrauben, Saegespaene, Kreide
    dx_, dy_ = x0 + 0.65, y1 - 1.35
    pen.hell(dx_, dy_, 0.38, 0.38, (190, 140, 90, 255), ink, 0.04, seed=30)
    pen.hell(dx_, dy_, 0.12, 0.12, (120, 80, 50, 255), ink, 0.025, seed=31)
    for k in range(6):
        a = k * math.pi / 3 + 0.2
        pen.line([(dx_ + math.cos(a) * 0.14, dy_ + math.sin(a) * 0.14), (dx_ + math.cos(a) * 0.35, dy_ + math.sin(a) * 0.35)], (130, 90, 55, 255), 0.025)
    # Kabel: eine lose Schlaufe neben der Trommel, das Ende haengt zum Sicherungskasten an der Wand
    pen.hline([(dx_ + 0.36, dy_ - 0.1), (dx_ + 0.7, dy_ - 0.35), (dx_ + 0.55, dy_ - 0.6), (dx_ + 0.2, dy_ - 0.5), (dx_ + 0.3, dy_ - 0.3)], (24, 22, 28, 255), 0.04, seed=32, amp=0.02)
    pen.hline([(dx_ - 0.1, dy_ + 0.36), (dx_ - 0.25, dy_ + 0.8), (x0 + 0.31, y1 + 0.02)], (24, 22, 28, 255), 0.04, seed=33, amp=0.015)
    kx, ky = bx1 + 0.45, by0 + 0.35
    pen.hrect(kx, ky, kx + 0.55, ky + 0.3, (180, 50, 50, 255), ink, 0.03, seed=33)                                               # Werkzeugkasten
    pen.rect(kx + 0.18, ky + 0.3, kx + 0.37, ky + 0.36, (60, 60, 66, 255), ink, 0.015)
    pen.rect(kx + 0.03, ky + 0.14, kx + 0.52, ky + 0.17, (120, 30, 30, 255))
    scatter(pen, free.intersection(box(bx0 - 0.4, by0 - 0.4, bx1 + 1.6, by1 + 0.6)), 18, 34,
            lambda p, x, y, r: p.poly([(x + math.cos(a) * 0.035, y + math.sin(a) * 0.035) for a in [k * math.pi / 3 for k in range(6)]], (150, 150, 160, 255), ink, 0.012))
    scatter(pen, free.intersection(box(tx0 - 0.5, ty0 - 0.1, tx1 + 0.5, ty1 + 0.6)), 50, 35, lambda p, x, y, r: p.ell(x, y, 0.03, 0.015, (190, 160, 110, 180)))
    chalk = (236, 232, 220, 150)
    pen.hline([(x0 + 3.0, y1 - 1.1), (x0 + 3.6, y1 - 0.75)], chalk, 0.03, seed=36)                                               # Kreide: Pfeil zum Stellplatz
    pen.hline([(x0 + 3.6, y1 - 0.75), (x0 + 3.0, y1 - 1.1), (x0 + 3.45, y1 - 1.15)], chalk, 0.03, seed=37)
    pen.text(x0 + 3.9, y1 - 0.65, "FIX ME", 0.26, chalk)
    # Abfluss in der Mitte, Oelflecken dezent
    drain(pen, x0 + 5.6, y0 + 3.6, 0.26)
    scatter(pen, free.difference(box(bx0 - 0.3, by0 - 0.3, bx1 + 0.3, by1 + 0.3)), 4, 38, lambda p, x, y, r: stain(p, x, y, r, (8, 8, 10, 50)))


def beds(pen, rect, seed):
    """Blumenbeete in den Ecken einer Lichtung (handgezeichnet): Erdoval mit zittrigem Rand und Lichtkante,
    Blueten mit fuenf Blaettern, ein paar Blaetter und Halme."""
    x0, y0, x1, y1 = rect
    rnd = random.Random(seed)
    for (cx, cy) in ((x0 + 2.2, y0 + 2.2), (x1 - 2.2, y0 + 2.2), (x0 + 2.2, y1 - 2.2), (x1 - 2.2, y1 - 2.2)):
        pen.hell(cx, cy, 1.0, 0.8, (60, 44, 34, 255), (30, 24, 20, 255), 0.04, seed=seed + int(cx * 3 + cy))
        pen.ell(cx - 0.2, cy + 0.25, 0.6, 0.35, (80, 60, 46, 120))
        for _ in range(7):
            lx, ly = cx + rnd.uniform(-0.8, 0.8), cy + rnd.uniform(-0.6, 0.6)
            pen.hell(lx, ly, 0.09, 0.05, (60, 120, 70, 255), (30, 70, 40, 255), 0.01, seed=int(lx * 10))
        for _ in range(11):
            fx, fy = cx + rnd.uniform(-0.8, 0.8), cy + rnd.uniform(-0.6, 0.6)
            col = rnd.choice(((230, 90, 120), (240, 210, 90), (210, 210, 250), (240, 150, 60)))
            for a in range(0, 360, 72):
                pen.ell(fx + math.cos(math.radians(a)) * 0.06, fy + math.sin(math.radians(a)) * 0.06, 0.045, 0.045, col + (255,), INK, 0.01)
            pen.ell(fx, fy, 0.035, 0.035, (250, 240, 200, 255), INK, 0.008)


# ------------------------------------------------------------------ Wanddeko (Nordwand-Stirnseiten)

def walls(F, walk):
    """Wanddeko, die nicht aus der Fassaden-Vorgabe (park_floor.FACADE) kommt: die Werkstatt-Werkzeugwand.
    Schilder, Poster, Zielscheiben, Wimpel, Totenkoepfe und Neon haengen seit dem vollen Pass an den
    Fassaden selbst (draw_facade), damit sie mit der Wandhoehe mitgehen."""
    pen = Pen(F)
    # Werkstatt (Stilblatt): Sicherungskasten links, Lochwand mit Werkzeug rechts vom Foto-Monitor
    # (der haengt per C# bei x -19,9..-17,7), Uhr auf dem kurzen Wandstueck oestlich der Tuer
    x0, y0, x1, y1 = R("workshop")
    pen.hrect(x0 + 0.1, y1 + 0.3, x0 + 0.52, y1 + 0.78, (112, 118, 128, 255), INK, 0.03, seed=40)       # Sicherungskasten
    pen.rect(x0 + 0.16, y1 + 0.36, x0 + 0.46, y1 + 0.72, None, (70, 74, 84, 255), 0.015)
    pen.ell(x0 + 0.24, y1 + 0.68, 0.03, 0.03, (255, 70, 60, 255), INK, 0.01)
    pen.ell(x0 + 0.24, y1 + 0.68, 0.08, 0.08, (255, 70, 60, 50))
    for k in range(2):
        pen.rect(x0 + 0.22 + k * 0.12, y1 + 0.44, x0 + 0.3 + k * 0.12, y1 + 0.56, (40, 40, 46, 255))
    pen.line([(x0 + 0.31, y1 + 0.3), (x0 + 0.31, y1 + 0.05)], (30, 30, 36, 255), 0.03)                   # Kabel zum Boden
    px0, px1 = -17.65, -16.4
    pen.hrect(px0, y1 + 0.12, px1, y1 + 0.82, (140, 108, 74, 255), INK, 0.03, seed=41)                  # Lochwand
    for k in range(18):
        pen.ell(px0 + 0.12 + (k % 6) * 0.2, y1 + 0.25 + (k // 6) * 0.22, 0.014, 0.014, (60, 44, 30, 255))
    pen.line([(px0 + 0.18, y1 + 0.28), (px0 + 0.18, y1 + 0.7)], (160, 160, 170, 255), 0.045)             # Schraubenschluessel
    pen.ell(px0 + 0.18, y1 + 0.72, 0.05, 0.04, (160, 160, 170, 255), INK, 0.012)
    pen.line([(px0 + 0.45, y1 + 0.26), (px0 + 0.45, y1 + 0.68)], (170, 120, 80, 255), 0.04)              # Hammer
    pen.rect(px0 + 0.36, y1 + 0.62, px0 + 0.54, y1 + 0.72, (110, 110, 120, 255), INK, 0.015)
    pen.poly([(px0 + 0.68, y1 + 0.3), (px0 + 1.05, y1 + 0.3), (px0 + 1.05, y1 + 0.42), (px0 + 0.68, y1 + 0.62)], (190, 190, 200, 255), INK, 0.015)   # Saege
    pen.rect(px0 + 1.0, y1 + 0.28, px0 + 1.12, y1 + 0.46, (120, 60, 40, 255), INK, 0.012)
    pen.line([(px0 + 0.72, y1 + 0.52), (px0 + 0.72, y1 + 0.75)], (230, 190, 60, 255), 0.04)              # Schraubendreher
    pen.hell(x1 - 0.62, y1 + 0.5, 0.2, 0.2, (240, 236, 220, 255), INK, 0.03, seed=42)                     # Uhr
    pen.line([(x1 - 0.62, y1 + 0.5), (x1 - 0.62, y1 + 0.64)], INK, 0.025)
    pen.line([(x1 - 0.62, y1 + 0.5), (x1 - 0.52, y1 + 0.46)], INK, 0.025)
