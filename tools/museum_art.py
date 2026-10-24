# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# museum_art.py - das Vesper-Museum im Among-Us-Stil.
#
# Stilregeln (abgeleitet aus Skeld/Polus):
# - Kraeftige schwarze Umrisse (OUTLINE, ~6 cm) um alles, was Kante ist.
# - Flache Farbflaechen mit EINER hellen Kante oben und EINER dunklen unten statt Verlaeufen.
# - Schraege Aufsicht: ein Objekt zeigt Deckflaeche + Vorderseite. Hoehe h (m) steht auf dem
#   Bild als h * K nach oben; die Standlinie (Unterkante der Vorderseite) ist die Kollision.
# - Nordwaende zeigen ihre Stirnseite (in der Wandstaerke), alle anderen nur die Wandkrone.
# - Farben: Rollen aus docs/museum_map/museum_stil.md (Soll-Werte), fuer 2D angehoben (lift),
#   weil Among Us die Nacht ueber das Sichtfeld macht, nicht ueber die Textur.
#
# Alles arbeitet in Weltmetern. Zeichnen = Operationen in eine Liste (Boden) oder direkt in
# eine kleine Leinwand (Objekte); beides mit 2-fachem Supersampling fuer glatte Umrisse.

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter
from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union
from shapely.affinity import translate

import handdraw as HD
import museum_layout as L

K = 0.55            # Hoehe -> Bild-oben (schraege Aufsicht); 0,72 liess Tresen ganze Spieler schlucken
SS = 2              # Supersampling
OUT_W = 0.06        # Umrissbreite in m
OUTLINE = (14, 16, 20, 255)


# ------------------------------------------------------------------ Farben

def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def lift(h, f=1.45, a=255):
    """Soll-Wert fuer 2D anheben (Helligkeit x f, Saettigung bleibt)."""
    r, g, b, _ = hexc(h)
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)), a)


def shade(c, f):
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))), c[3] if len(c) > 3 else 255)


def alpha(c, a):
    return (c[0], c[1], c[2], a)


# Raumrollen: (Boden, Wand-Stirnseite)
ROOM_ROLE = {
    "rotunde": ("#6e6a62", "#6b6a66"),
    "foyer": ("#8a8275", "#7d7364"),
    "shop": ("#6f9a8c", "#8fb0a4"),
    "sicherheit": ("#2f3336", "#363b40"),
    "haustechnik": ("#4f4b44", "#595650"),
    "aegypten": ("#8a6f47", "#7a5f3e"),
    "galerie": ("#6a4a30", "#5b2430"),
    "planetarium": ("#23283a", "#2c3442"),
    "mineralien": ("#33383c", "#1f3d42"),
    "telefon": ("#a8562a", "#6b4a2e"),
    "technikhalle": ("#4d5258", "#5a5e63"),
    "werkstatt": ("#9aa3a6", "#a9adad"),
    "hof": ("#3a3c40", "#5a5e63"),
    "depot": ("#55534f", "#5d5b57"),
}
GANG_FLOOR = "#4a505c"
GANG_WALL = "#555c68"
WALL_TOP = (58, 64, 76, 255)
WALL_TOP_EDGE = (82, 90, 104, 255)
VOID = (16, 19, 25, 255)
NOTGRUEN = hexc("#57d98a")
WARM = hexc("#ffd9a0")
MOON = hexc("#b9cde0")


# ------------------------------------------------------------ Zeichenflaeche

class Canvas:
    """Leinwand in Weltmetern: Rechteck (x0,y0)-(x1,y1), ppm Pixel pro Meter (Endaufloesung)."""

    def __init__(self, x0, y0, x1, y1, ppm, bg=(0, 0, 0, 0)):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.ppm = ppm
        self.s = ppm * SS
        self.w = max(1, int(round((x1 - x0) * self.s)))
        self.h = max(1, int(round((y1 - y0) * self.s)))
        self.img = Image.new("RGBA", (self.w, self.h), bg)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def p(self, x, y):
        return ((x - self.x0) * self.s, (self.y1 - y) * self.s)

    def pts(self, pts):
        return [self.p(x, y) for x, y in pts]

    def px(self, m):
        return max(1, int(round(m * self.s)))

    # PIL mischt auf RGBA-Bildern NICHT: eine halbtransparente Fuellung ueberschreibt die Pixel
    # samt Alpha (Glas stanzte so Sockel und Exponat aus). Alles mit Alpha < 255 wird deshalb
    # auf einer eigenen Ebene gezeichnet und per alpha_composite ueberblendet.
    @staticmethod
    def _translucent(*colors):
        return any(c is not None and len(c) > 3 and c[3] < 255 for c in colors)

    def _layer(self, pxpts, pad, fn):
        xs = [p[0] for p in pxpts]; ys = [p[1] for p in pxpts]
        x0 = max(0, int(min(xs) - pad)); y0 = max(0, int(min(ys) - pad))
        x1 = min(self.w, int(max(xs) + pad) + 1); y1 = min(self.h, int(max(ys) + pad) + 1)
        if x1 <= x0 or y1 <= y0:
            return
        layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        fn(ImageDraw.Draw(layer), -x0, -y0)
        self.img.alpha_composite(layer, (x0, y0))

    def poly(self, pts, fill=None, outline=None, width=OUT_W):
        if len(pts) < 3:
            return
        pp = self.pts(pts)
        lw = self.px(width)

        def draw(d, ox, oy):
            q = [(x + ox, y + oy) for x, y in pp]
            if fill is not None:
                d.polygon(q, fill=fill)
            if outline is not None:
                d.line(q + [q[0]], fill=outline, width=lw, joint="curve")

        if self._translucent(fill, outline):
            self._layer(pp, lw + 2, draw)
        else:
            draw(self.d, 0, 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=OUT_W):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, width)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=OUT_W):
        a, b = self.p(cx - rx, cy + ry), self.p(cx + rx, cy - ry)
        lw = self.px(width) if outline is not None else 0

        def draw(d, ox, oy):
            d.ellipse([(a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy)], fill=fill, outline=outline, width=lw)

        if self._translucent(fill, outline):
            self._layer([a, b], lw + 2, draw)
        else:
            draw(self.d, 0, 0)

    def line(self, pts, fill, width=OUT_W):
        pp = self.pts(pts)
        lw = self.px(width)

        def draw(d, ox, oy):
            d.line([(x + ox, y + oy) for x, y in pp], fill=fill, width=lw, joint="curve")

        if self._translucent(fill):
            self._layer(pp, lw + 2, draw)
        else:
            draw(self.d, 0, 0)

    def soft_shadow(self, pts, alpha_v=90, blur=0.08):
        """Weicher Schlagschatten einer Grundflaeche (gaussisch verwischt)."""
        pp = self.pts(pts)
        pad = self.px(blur) * 3 + 2
        xs = [p[0] for p in pp]; ys = [p[1] for p in pp]
        x0 = int(min(xs) - pad); y0 = int(min(ys) - pad)
        w = int(max(xs) + pad) - x0 + 1; h = int(max(ys) + pad) - y0 + 1
        if w <= 0 or h <= 0:
            return
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in pp], fill=alpha_v)
        m = m.filter(ImageFilter.GaussianBlur(self.px(blur)))
        layer = Image.new("RGBA", (w, h), (8, 10, 16, 0))
        layer.putalpha(m)
        # auf die Leinwand zuschneiden
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(self.w, x0 + w), min(self.h, y0 + h)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        layer = layer.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0))
        self.img.alpha_composite(layer, (cx0, cy0))

    def glow(self, cx, cy, r, color, strength=0.5):
        """Weicher Lichtfleck (radial) - fuer Vitrinenschein, Mondflecken."""
        size = self.px(r * 2)
        if size < 4:
            return
        g = Image.new("L", (size, size), 0)
        gd = ImageDraw.Draw(g)
        steps = 24
        for i in range(steps):
            f = i / steps
            rr = (1 - f) * size / 2
            gd.ellipse([size / 2 - rr, size / 2 - rr, size / 2 + rr, size / 2 + rr],
                       fill=int(255 * strength * (f ** 1.6)))
        layer = Image.new("RGBA", (size, size), color[:3] + (0,))
        layer.putalpha(g)
        x, y = self.p(cx - r, cy + r)
        x, y = int(x), int(y)
        # am Leinwandrand zuschneiden (alpha_composite verlangt Ziel-Offsets >= 0)
        cx0, cy0 = max(0, x), max(0, y)
        cx1, cy1 = min(self.w, x + size), min(self.h, y + size)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        if (cx0, cy0, cx1, cy1) != (x, y, x + size, y + size):
            layer = layer.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
        self.img.alpha_composite(layer, (cx0, cy0))

    def text(self, x, y, s, size_m, fill, anchor="mm"):
        try:
            font = ImageFont.truetype("arialbd.ttf", self.px(size_m))
        except OSError:
            font = ImageFont.load_default()
        if self._translucent(fill):
            px_, py_ = self.p(x, y)
            r = self.px(size_m) * max(1, len(s))
            self._layer([(px_ - r, py_ - r), (px_ + r, py_ + r)], 2,
                        lambda d, ox, oy: d.text((px_ + ox, py_ + oy), s, font=font, fill=fill, anchor=anchor))
        else:
            self.d.text(self.p(x, y), s, font=font, fill=fill, anchor=anchor)

    def group(self, clip, ops):
        """Befehle eines Raums auf eigener Ebene zeichnen und auf clip (Weltflaeche) beschneiden."""
        bx0, by0, bx1, by1 = clip.bounds
        x0, y0 = max(bx0, self.x0), max(by0, self.y0)
        x1, y1 = min(bx1, self.x1), min(by1, self.y1)
        if x1 <= x0 or y1 <= y0:
            return
        # auf das Pixelraster der Leinwand legen, damit die Ebene ohne Versatz einrastet
        ox = int(math.floor((x0 - self.x0) * self.s)); oy = int(math.floor((self.y1 - y1) * self.s))
        ex = int(math.ceil((x1 - self.x0) * self.s)); ey = int(math.ceil((self.y1 - y0) * self.s))
        ox, oy = max(0, ox), max(0, oy)
        ex, ey = min(self.w, ex), min(self.h, ey)
        if ex <= ox or ey <= oy:
            return
        sub = Canvas.__new__(Canvas)
        sub.x0 = self.x0 + ox / self.s; sub.x1 = self.x0 + ex / self.s
        sub.y1 = self.y1 - oy / self.s; sub.y0 = self.y1 - ey / self.s
        sub.ppm, sub.s = self.ppm, self.s
        sub.w, sub.h = ex - ox, ey - oy
        sub.img = Image.new("RGBA", (sub.w, sub.h), (0, 0, 0, 0))
        sub.d = ImageDraw.Draw(sub.img, "RGBA")
        for (ax0, ay0, ax1, ay1), fn, args, kw in ops:
            if ay1 < sub.y0 or ay0 > sub.y1 or ax1 < sub.x0 or ax0 > sub.x1:
                continue
            getattr(sub, fn)(*args, **kw)
        mask = Image.new("L", (sub.w, sub.h), 0)
        md = ImageDraw.Draw(mask)
        for p in ([clip] if clip.geom_type == "Polygon" else [q for q in clip.geoms if q.geom_type == "Polygon"]):
            md.polygon(sub.pts(list(p.exterior.coords)), fill=255)
            for h in p.interiors:
                md.polygon(sub.pts(list(h.coords)), fill=0)
        sub.img.putalpha(ImageChops.multiply(sub.img.getchannel("A"), mask))
        self.img.alpha_composite(sub.img, (ox, oy))

    def finish(self):
        return self.img.resize((self.w // SS, self.h // SS), Image.LANCZOS)


class OpList:
    """Aufgezeichnete Zeichenbefehle mit Weltbox; wird streifenweise abgespielt (Speicher)."""

    def __init__(self):
        self.ops = []
        self._dx = self._dy = 0.0
        self._group = None
        self._clip = None

    # Kartenverkleinerung (docs/KARTEN_VERKLEINERUNG.md): ein Raum wird in seinen alten
    # Entwurfskoordinaten gezeichnet, um (dx, dy) an seinen neuen Platz verschoben und auf seine
    # neue Flaeche beschnitten (sonst malten Laeufer, Lichtflecken usw. auf die Wandkrone).
    def begin_room(self, clip, dx=0.0, dy=0.0):
        self._dx, self._dy = dx, dy
        self._group = []
        self._clip = clip

    def end_room(self):
        g, clip = self._group, self._clip
        self._group = None
        self._clip = None
        self._dx = self._dy = 0.0
        if g:
            self.ops.append((clip.bounds, "group", (clip, g), {}))

    def _t(self, pts):
        if not self._dx and not self._dy:
            return list(pts)
        return [(x + self._dx, y + self._dy) for x, y in pts]

    def add(self, bbox, fn, *args, **kw):
        (self._group if self._group is not None else self.ops).append((bbox, fn, args, kw))

    def poly(self, pts, fill=None, outline=None, width=OUT_W):
        pts = self._t(pts)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        self.add((min(xs), min(ys), max(xs), max(ys)), "poly", pts, fill, outline, width)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=OUT_W):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, width)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=OUT_W):
        cx, cy = cx + self._dx, cy + self._dy
        self.add((cx - rx, cy - ry, cx + rx, cy + ry), "ellipse", cx, cy, rx, ry, fill, outline, width)

    def line(self, pts, fill, width=OUT_W):
        pts = self._t(pts)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        self.add((min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width), "line", pts, fill, width)

    def glow(self, cx, cy, r, color, strength=0.5):
        cx, cy = cx + self._dx, cy + self._dy
        self.add((cx - r, cy - r, cx + r, cy + r), "glow", cx, cy, r, color, strength)

    def text(self, x, y, s, size_m, fill, anchor="mm"):
        x, y = x + self._dx, y + self._dy
        w = len(s) * size_m
        self.add((x - w, y - size_m, x + w, y + size_m), "text", x, y, s, size_m, fill, anchor)

    def geom(self, g, fill=None, outline=None, width=OUT_W):
        """Shapely-Flaeche (auch Multi) als Polygone (Loecher werden uebermalt: nur fuer Flaechen ohne)."""
        if g.is_empty:
            return
        parts = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
        for p in parts:
            self.poly(list(p.exterior.coords)[:-1], fill, outline, width)

    def render(self, x0, y0, x1, y1, ppm, bg, strip_m=3.0):
        full = Image.new("RGB", (int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))), bg[:3])
        y = y1
        while y > y0 + 1e-6:
            sy0 = max(y0, y - strip_m)
            pad = 0.6
            c = Canvas(x0, sy0 - pad, x1, y + pad, ppm, bg)
            for (bx0, by0, bx1, by1), fn, args, kw in self.ops:
                if by1 < sy0 - pad or by0 > y + pad:
                    continue
                getattr(c, fn)(*args, **kw)
            tile = c.finish().convert("RGB")
            cut_top = int(round(pad * ppm))
            h = int(round((y - sy0) * ppm))
            tile = tile.crop((0, cut_top, tile.width, cut_top + h))
            full.paste(tile, (0, int(round((y1 - y) * ppm))))
            y = sy0
        return full


# ---------------------------------------------------------------- Geometrie

def room_polys():
    """Stil -> WELT-Flaeche (fuer die Wand-Deko: wem gehoert die Wand?)."""
    out = {}
    for style, poly, _shift in L.ROOM_ART:
        if style == "hof":
            g = unary_union([Polygon(p) for p, _c in L.HOF_FLOORS])
        else:
            g = Polygon(poly)
        out[style] = unary_union([out[style], g]) if style in out else g
    return out


def tiles(ops, region, x0, y0, x1, y1, tw, th, colors, fuge, offset_rows=False, seed=1, fuge_w=0.03, bevel=True):
    """Plattenraster, auf region zugeschnitten. colors = Liste, per Zufall gestreut."""
    rnd = random.Random(seed)
    row = 0
    y = y0
    while y < y1:
        x = x0 - (tw / 2 if offset_rows and row % 2 else 0)
        while x < x1:
            t = sbox(x, y, x + tw, y + th).intersection(region)
            if not t.is_empty:
                ops.geom(t, fill=rnd.choice(colors))
                if bevel:
                    bw = min(tw, th) * 0.08
                    ops.geom(sbox(x, y + th - bw, x + tw, y + th).intersection(region), fill=(255, 255, 255, 34))
                    ops.geom(sbox(x, y + bw, x + bw, y + th - bw).intersection(region), fill=(255, 255, 255, 22))
                    ops.geom(sbox(x, y, x + tw, y + bw).intersection(region), fill=(0, 0, 0, 38))
                    ops.geom(sbox(x + tw - bw, y + bw, x + tw, y + th - bw).intersection(region), fill=(0, 0, 0, 26))
            x += tw
        y += th
        row += 1
    # Fugen als Linien (ueber alles, im Bereich zugeschnitten)
    y = y0
    row = 0
    while y <= y1 + 1e-6:
        seg = region.intersection(sbox(x0 - 1, y - fuge_w / 2, x1 + 1, y + fuge_w / 2))
        ops.geom(seg, fill=fuge)
        y += th
        row += 1
    rowy = y0
    row = 0
    while rowy < y1:
        x = x0 - (tw / 2 if offset_rows and row % 2 else 0)
        while x <= x1 + 1e-6:
            seg = region.intersection(sbox(x - fuge_w / 2, rowy, x + fuge_w / 2, rowy + th))
            ops.geom(seg, fill=fuge)
            x += tw
        rowy += th
        row += 1


def herringbone(ops, region, cx, cy, pw, n, cols, fuge, seed=1, angle=45.0):
    """Fischgraet-Parkett (Stilblatt): Staebe pw x n*pw in zwei Richtungen, lueckenlos (Zickzack-Reihen,
    Reihenversatz (1, 1) im achsparallelen Raster, dann um `angle` gedreht), auf region zugeschnitten.
    Jeder Stab eigener Ton, leichtes Zittern im Umriss, Lichtkante an der Nord-/Westseite."""
    rnd = random.Random(seed)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)

    def T(u, v):
        x, y = u * pw, v * pw
        return (cx + x * ca - y * sa, cy + x * sa + y * ca)

    x0, y0, x1, y1 = region.bounds
    reach = int(math.hypot(x1 - x0, y1 - y0) / pw / (n + 1)) + 3
    planks = []
    for k in range(-reach, reach + 1):
        for m in range(-reach * (n + 1), reach * (n + 1) + 1):
            ox, oy = m, m
            A = [(k * (n + 1) + ox, k * (1 - n) + oy), (k * (n + 1) + n + ox, k * (1 - n) + oy),
                 (k * (n + 1) + n + ox, k * (1 - n) + 1 + oy), (k * (n + 1) + ox, k * (1 - n) + 1 + oy)]
            B = [(k * (n + 1) + n + ox, k * (1 - n) + 1 - n + oy), ((k + 1) * (n + 1) + ox, k * (1 - n) + 1 - n + oy),
                 ((k + 1) * (n + 1) + ox, k * (1 - n) + 1 + oy), (k * (n + 1) + n + ox, k * (1 - n) + 1 + oy)]
            planks.append(A)
            planks.append(B)
    bbox = sbox(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5)
    i = 0
    for pl in planks:
        wpts = [T(u, v) for u, v in pl]
        g = Polygon(wpts)
        if not g.intersects(bbox):
            continue
        g = g.intersection(region)
        if g.is_empty:
            continue
        i += 1
        col = rnd.choice(cols)
        for part in ([g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]):
            pts = HD.wobble(list(part.exterior.coords)[:-1], amp=0.004, seed=seed * 100 + i, step=0.08, closed=True)
            ops.poly(pts, fill=col)
            ops.line(pts + [pts[0]], fill=fuge, width=0.018)
        # Lichtkante entlang der nordwestlichen Laengskante, Schattenkante gegenueber
        full = Polygon(wpts)
        for e in range(4):
            a_, b_ = wpts[e], wpts[(e + 1) % 4]
            if math.hypot(b_[0] - a_[0], b_[1] - a_[1]) < n * pw * 0.9:
                continue
            strip = Polygon(HD.edge_strip(wpts, e, pw * 0.14)).intersection(region)
            mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            north = (my - full.centroid.y) - (mx - full.centroid.x) > 0
            if not strip.is_empty and strip.geom_type == "Polygon":
                ops.poly(list(strip.exterior.coords)[:-1], fill=(255, 255, 255, 30) if north else (0, 0, 0, 34))


def painting(c, x0, y0, x1, y1, motif, rnd, frame=True):
    """Kleines Gemaelde im Among-Us-Look: Goldrahmen mit Zittern, erkennbares Motiv aus wenigen flachen
    Formen. c = OpList (Boden) oder Canvas (Objekt), beide haben rect/ellipse/poly/line."""
    if frame:
        fr = HD.wobble_rect(x0, y0, x1, y1, amp=0.004, seed=int(x0 * 100 + y0 * 7), step=0.04)
        c.poly(fr, fill=hexc("#c9a24c"), outline=OUTLINE, width=0.018)
        c.poly(HD.wobble_rect(x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03, amp=0.003, seed=int(x0 * 50), step=0.04), outline=hexc("#8a6a28"), width=0.01)
        x0, y0, x1, y1 = x0 + 0.045, y0 + 0.045, x1 - 0.045, y1 - 0.045
    w, h = x1 - x0, y1 - y0
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if motif == "berg":
        c.rect(x0, y0, x1, y1, fill=hexc("#5f8fc8"))
        c.rect(x0, y0 + h * 0.55, x1, y1, fill=hexc("#8fb8e0"))
        c.ellipse(x0 + w * 0.78, y0 + h * 0.78, w * 0.08, w * 0.08, fill=hexc("#fff3c4"))
        c.poly([(x0, y0 + h * 0.25), (mx - w * 0.05, y0 + h * 0.85), (x1, y0 + h * 0.3)], fill=hexc("#6a6f80"), outline=OUTLINE, width=0.01)
        c.poly([(mx - w * 0.2, y0 + h * 0.62), (mx - w * 0.05, y0 + h * 0.85), (mx + w * 0.12, y0 + h * 0.65), (mx + w * 0.02, y0 + h * 0.68), (mx - w * 0.08, y0 + h * 0.6)], fill=hexc("#f4f4f8"))
        c.rect(x0, y0, x1, y0 + h * 0.25, fill=hexc("#4f7f4a"))
    elif motif == "schiff":
        c.rect(x0, y0, x1, y1, fill=hexc("#d9b26a"))
        c.rect(x0, y0, x1, y0 + h * 0.45, fill=hexc("#2f5f8a"))
        c.line([(x0 + w * 0.1, y0 + h * 0.3), (x0 + w * 0.4, y0 + h * 0.32)], fill=hexc("#5f9fd0"), width=0.012)
        c.poly([(mx - w * 0.3, y0 + h * 0.45), (mx + w * 0.32, y0 + h * 0.45), (mx + w * 0.22, y0 + h * 0.3), (mx - w * 0.22, y0 + h * 0.3)], fill=hexc("#5a3a22"), outline=OUTLINE, width=0.01)
        c.line([(mx, y0 + h * 0.45), (mx, y0 + h * 0.92)], fill=OUTLINE, width=0.012)
        c.poly([(mx + 0.01, y0 + h * 0.5), (mx + w * 0.3, y0 + h * 0.55), (mx + 0.01, y0 + h * 0.88)], fill=hexc("#f4f0e4"), outline=OUTLINE, width=0.01)
        c.ellipse(x0 + w * 0.2, y0 + h * 0.8, w * 0.07, w * 0.07, fill=hexc("#fff3c4"))
    elif motif == "sonnenblume":
        c.rect(x0, y0, x1, y1, fill=hexc("#3f6fa0"))
        c.line([(mx, y0 + h * 0.1), (mx, y0 + h * 0.55)], fill=hexc("#4f8a3a"), width=0.02)
        c.ellipse(mx + w * 0.1, y0 + h * 0.28, w * 0.1, h * 0.06, fill=hexc("#4f8a3a"))
        for k in range(10):
            a = k * math.tau / 10
            c.ellipse(mx + math.cos(a) * w * 0.22, y0 + h * 0.62 + math.sin(a) * h * 0.2, w * 0.1, h * 0.07, fill=hexc("#f2c23a"), outline=OUTLINE, width=0.008)
        c.ellipse(mx, y0 + h * 0.62, w * 0.14, h * 0.13, fill=hexc("#6a4a22"), outline=OUTLINE, width=0.01)
    elif motif == "crew":
        col = rnd.choice([hexc("#c51111"), hexc("#132ed1"), hexc("#117f2d"), hexc("#ed54ba"), hexc("#f07613")])
        c.rect(x0, y0, x1, y1, fill=hexc("#2a2a36"))
        c.ellipse(mx, y0 + h * 0.3, w * 0.28, h * 0.32, fill=col, outline=OUTLINE, width=0.012)
        c.rect(mx - w * 0.28, y0, mx + w * 0.28, y0 + h * 0.3, fill=col)
        c.rect(mx - w * 0.4, y0 + h * 0.15, mx - w * 0.26, y0 + h * 0.5, fill=col, outline=OUTLINE, width=0.01)
        c.ellipse(mx + w * 0.1, y0 + h * 0.5, w * 0.18, h * 0.1, fill=hexc("#9ad6e8"), outline=OUTLINE, width=0.01)
    elif motif == "abstrakt":
        c.rect(x0, y0, x1, y1, fill=hexc("#f0ece0"))
        c.rect(x0, y0 + h * 0.5, mx - w * 0.1, y1, fill=hexc("#d33a2a"))
        c.rect(mx + w * 0.1, y0, x1, y0 + h * 0.45, fill=hexc("#2f4fa0"))
        c.rect(mx - w * 0.1, y0, mx + w * 0.1, y0 + h * 0.3, fill=hexc("#f2c23a"))
        c.line([(x0, y0 + h * 0.5), (x1, y0 + h * 0.5)], fill=OUTLINE, width=0.012)
        c.line([(mx - w * 0.1, y0), (mx - w * 0.1, y1)], fill=OUTLINE, width=0.012)
        c.line([(mx + w * 0.1, y0), (mx + w * 0.1, y0 + h * 0.5)], fill=OUTLINE, width=0.012)
    elif motif == "obst":
        c.rect(x0, y0, x1, y1, fill=hexc("#6a4a3a"))
        c.rect(x0, y0, x1, y0 + h * 0.35, fill=hexc("#a07a50"))
        c.poly([(mx - w * 0.32, y0 + h * 0.45), (mx + w * 0.32, y0 + h * 0.45), (mx + w * 0.22, y0 + h * 0.25), (mx - w * 0.22, y0 + h * 0.25)], fill=hexc("#d9d2c0"), outline=OUTLINE, width=0.01)
        for dx, col in ((-0.16, "#d33a2a"), (0.0, "#f2c23a"), (0.16, "#5fa040")):
            c.ellipse(mx + w * dx, y0 + h * 0.52, w * 0.1, h * 0.1, fill=hexc(col), outline=OUTLINE, width=0.01)
    elif motif == "nacht":
        c.rect(x0, y0, x1, y1, fill=hexc("#1c2448"))
        for _ in range(9):
            c.ellipse(rnd.uniform(x0 + 0.02, x1 - 0.02), rnd.uniform(y0 + 0.02, y1 - 0.02), 0.006, 0.006, fill=hexc("#e8f0ff"))
        c.ellipse(x0 + w * 0.7, y0 + h * 0.68, w * 0.12, w * 0.12, fill=hexc("#fff3c4"))
        c.ellipse(x0 + w * 0.76, y0 + h * 0.72, w * 0.1, w * 0.1, fill=hexc("#1c2448"))


    # Motive des vollen Passes (2026-10-01): Papyrus (Aegypten), Blaupause (Technik), Sternbild (Planetarium),
    # Saurier-Plakat (Foyer/Rotunde), Lehrtafel (Mineralien), Plakat (Telefon)
    if motif == "papyrus":
        c.rect(x0, y0, x1, y1, fill=hexc("#d8c79a"))
        c.rect(x0, y0, x1, y0 + h * 0.08, fill=hexc("#b8a070"))
        c.rect(x0, y1 - h * 0.08, x1, y1, fill=hexc("#b8a070"))
        for i in range(4):
            cx_ = x0 + w * (0.18 + i * 0.21)
            k = (i + int(x0 * 3)) % 3
            if k == 0:
                c.ellipse(cx_, my + h * 0.1, w * 0.05, h * 0.09, fill=hexc("#2f4f8a"), outline=OUTLINE, width=0.008)
                c.rect(cx_ - w * 0.02, y0 + h * 0.2, cx_ + w * 0.02, my, fill=hexc("#3f2e1c"))
            elif k == 1:
                c.poly([(cx_ - w * 0.06, y0 + h * 0.22), (cx_ + w * 0.06, y0 + h * 0.22), (cx_, y0 + h * 0.72)], fill=hexc("#b8843a"), outline=OUTLINE, width=0.008)
            else:
                c.line([(cx_, y0 + h * 0.2), (cx_, y0 + h * 0.75)], fill=hexc("#3f2e1c"), width=0.012)
                c.ellipse(cx_, y0 + h * 0.6, w * 0.04, h * 0.05, fill=hexc("#d33a2a"))
        c.line([(x0 + w * 0.08, y0 + h * 0.15), (x1 - w * 0.08, y0 + h * 0.15)], fill=hexc("#3f2e1c"), width=0.008)
    elif motif == "blaupause":
        c.rect(x0, y0, x1, y1, fill=hexc("#2f5f8a"))
        for i in range(1, 5):
            c.line([(x0 + w * i / 5, y0), (x0 + w * i / 5, y1)], fill=alpha(hexc("#8fb8e0"), 70), width=0.006)
            c.line([(x0, y0 + h * i / 5), (x1, y0 + h * i / 5)], fill=alpha(hexc("#8fb8e0"), 70), width=0.006)
        c.ellipse(mx + w * 0.12, my, w * 0.22, h * 0.3, outline=hexc("#dff3ff"), width=0.012)
        c.ellipse(mx + w * 0.12, my, w * 0.05, h * 0.07, outline=hexc("#dff3ff"), width=0.01)
        c.rect(x0 + w * 0.1, my - h * 0.12, mx - w * 0.1, my + h * 0.12, outline=hexc("#dff3ff"), width=0.012)
        c.line([(mx - w * 0.1, my), (mx - w * 0.1 + w * 0.08, my)], fill=hexc("#dff3ff"), width=0.012)
        c.line([(x0 + w * 0.1, y0 + h * 0.15), (x1 - w * 0.1, y0 + h * 0.15)], fill=hexc("#dff3ff"), width=0.008)
    elif motif == "sternbild":
        c.rect(x0, y0, x1, y1, fill=hexc("#1c2448"))
        pts = [(x0 + w * fx, y0 + h * fy) for fx, fy in ((0.15, 0.3), (0.3, 0.5), (0.45, 0.45), (0.6, 0.65), (0.8, 0.55), (0.72, 0.8), (0.9, 0.75))]
        c.line(pts, fill=alpha(hexc("#9fb8e8"), 200), width=0.008)
        for p in pts:
            c.ellipse(p[0], p[1], 0.012, 0.012, fill=hexc("#f4f8ff"))
        for _ in range(7):
            c.ellipse(rnd.uniform(x0 + 0.02, x1 - 0.02), rnd.uniform(y0 + 0.02, y1 - 0.02), 0.005, 0.005, fill=hexc("#cfe0ff"))
    elif motif == "saurier":
        c.rect(x0, y0, x1, y1, fill=hexc("#efe4c8"))
        c.rect(x0, y1 - h * 0.2, x1, y1, fill=hexc("#8e2f2f"))
        bone = hexc("#3b3630")
        c.line([(x0 + w * 0.12, y0 + h * 0.35), (x0 + w * 0.4, y0 + h * 0.5), (x0 + w * 0.65, y0 + h * 0.52), (x0 + w * 0.82, y0 + h * 0.66)], fill=bone, width=0.014)
        for i in range(5):
            tx = x0 + w * (0.3 + i * 0.08)
            c.line([(tx, y0 + h * 0.5), (tx + w * 0.02, y0 + h * 0.3)], fill=bone, width=0.008)
        c.ellipse(x0 + w * 0.84, y0 + h * 0.68, w * 0.09, h * 0.08, fill=bone)
        c.line([(x0 + w * 0.6, y0 + h * 0.5), (x0 + w * 0.56, y0 + h * 0.25)], fill=bone, width=0.012)
        c.line([(x0 + w * 0.4, y0 + h * 0.48), (x0 + w * 0.38, y0 + h * 0.25)], fill=bone, width=0.012)
    elif motif == "lehrtafel":
        c.rect(x0, y0, x1, y1, fill=hexc("#f0ece0"))
        c.rect(x0, y1 - h * 0.18, x1, y1, fill=hexc("#1f3d42"))
        for i, col in enumerate(("#9d6cc7", "#e0b04a", "#3f9e6e")):
            cx_ = x0 + w * (0.22 + i * 0.28)
            c.poly([(cx_ - w * 0.08, y0 + h * 0.25), (cx_ + w * 0.08, y0 + h * 0.25), (cx_ + w * 0.03, y0 + h * 0.62), (cx_ - w * 0.03, y0 + h * 0.62)], fill=hexc(col), outline=OUTLINE, width=0.008)
            c.line([(cx_ - w * 0.08, y0 + h * 0.16), (cx_ + w * 0.08, y0 + h * 0.16)], fill=hexc("#3b3630"), width=0.006)
    elif motif == "plakat":
        col = rnd.choice([hexc("#c8702e"), hexc("#2f4fa0"), hexc("#3f6b45")])
        c.rect(x0, y0, x1, y1, fill=hexc("#efd9a8"))
        c.ellipse(mx, my + h * 0.08, w * 0.3, h * 0.28, fill=col, outline=OUTLINE, width=0.01)
        c.ellipse(mx, my + h * 0.08, w * 0.16, h * 0.15, fill=hexc("#efd9a8"))
        c.ellipse(mx, my + h * 0.08, w * 0.06, h * 0.06, fill=col)
        c.rect(x0 + w * 0.12, y0 + h * 0.1, x1 - w * 0.12, y0 + h * 0.17, fill=hexc("#3b3630"))
        c.rect(x0 + w * 0.2, y0 + h * 0.2, x1 - w * 0.2, y0 + h * 0.24, fill=hexc("#3b3630"))


MOTIFS = ["berg", "schiff", "sonnenblume", "crew", "abstrakt", "obst", "nacht"]


# ------------------------------------------------------ Stilblatt-Helfer (voller Pass 2026-10-01)

def wobbly_tiles(ops, region, x0, y0, x1, y1, tw, th, cols, fuge, seed=1, bond=0.0, fuge_w=0.025, jitter=0.025,
                 checker=None, tone=0.06, chips=0.12, cracks=0.05, gaps=0.0, bevel=True, amp=0.004, crack_col=None,
                 vertical=False, knots=0.0, grain=0.0):
    """Plattenraster mit Hand-Unruhe (Stilblatt): Rasterlinien leicht verschoben (Nachbarn teilen sich die
    Fuge, nichts ueberlappt), jede Platte mit zittrigem Umriss, eigenem Ton, Lichtkante Nord/West und
    Schattenkante Sued/Ost, vereinzelt abgeschlagene Ecken, Risse und fehlende Platten (Fugenmoertel).
    checker = (A, B) wechselt im Schachbrett statt zufaellig; bond = Versatz je zweiter Reihe (0..1) oder
    "random" (Dielen: jede Reihe eigener Versatz); vertical = Reihen laufen senkrecht (Dielen quer);
    knots/grain = Anteil Platten mit Astknoten bzw. Maserungslinie (Holz)."""
    rnd = random.Random(seed)
    ops.geom(region, fill=fuge)
    if vertical:
        # im gedrehten Rahmen rechnen (u = y, v = x) und beim Zeichnen zuruecktauschen
        x0, y0, x1, y1 = y0, x0, y1, x1
    T = (lambda p: (p[1], p[0])) if vertical else (lambda p: p)
    rows = int(math.ceil((y1 - y0) / th)) + 1
    ncol = int(math.ceil((x1 - x0) / tw)) + 3
    waves = [HD.Noise1(seed * 11 + r, period=max(1.0, x1 - x0), waves=3, lo=1, hi=3) for r in range(rows + 1)]
    ys = [y0 + r * th + rnd.uniform(-jitter, jitter) * th for r in range(rows + 1)]
    wa = th * jitter * 0.6
    crack_col = crack_col or alpha(shade(fuge, 0.8), 200)
    for r in range(rows):
        off = rnd.uniform(0, tw) if bond == "random" else (bond * tw * (r % 2)) % tw
        xs = [x0 - tw + c * tw - off + rnd.uniform(-jitter, jitter) * tw for c in range(ncol + 1)]
        for c in range(ncol):
            xa, xb = xs[c], xs[c + 1]
            if xb < x0 - 0.01 or xa > x1 + 0.01:
                continue
            quad = [(xa, ys[r] + waves[r](xa - x0) * wa), (xb, ys[r] + waves[r](xb - x0) * wa),
                    (xb, ys[r + 1] + waves[r + 1](xb - x0) * wa), (xa, ys[r + 1] + waves[r + 1](xa - x0) * wa)]
            j = fuge_w / 2
            quad = [(quad[0][0] + j, quad[0][1] + j), (quad[1][0] - j, quad[1][1] + j),
                    (quad[2][0] - j, quad[2][1] - j), (quad[3][0] + j, quad[3][1] - j)]
            if gaps and rnd.random() < gaps:
                continue
            pts = HD.chip(quad, rnd, 0.2) if (chips and rnd.random() < chips) else quad
            wob = HD.wobble(pts, amp=amp, seed=seed * 1000 + r * 97 + c, step=0.06, closed=True)
            quad_w = [T(p) for p in quad]
            g = Polygon([T(p) for p in wob]).buffer(0).intersection(region)
            if g.is_empty:
                continue
            col = checker[(r + c) % 2] if checker else rnd.choice(cols)
            col = shade(col, 1 + rnd.uniform(-tone, tone))
            ops.geom(g, fill=col)
            if bevel:
                lw = min(tw, th) * 0.07
                for side, fcol in ((2, (255, 255, 255, 30)), (3, (255, 255, 255, 20)), (0, (0, 0, 0, 36)), (1, (0, 0, 0, 24))):
                    strip = Polygon(HD.edge_strip(quad_w, side, lw)).intersection(g)
                    if not strip.is_empty:
                        ops.geom(strip, fill=fcol)
            if cracks and rnd.random() < cracks:
                ln = LineString([T(p) for p in HD.crack(quad, rnd)]).intersection(g)
                if ln.geom_type == "LineString" and ln.length > 0.05:
                    ops.line(list(ln.coords), fill=crack_col, width=0.012)
            if knots and rnd.random() < knots:
                kx, ky = rnd.uniform(xa + 0.15, xb - 0.15), rnd.uniform(ys[r] + 0.06, ys[r + 1] - 0.06)
                kp = T((kx, ky))
                if g.contains(Point(kp)):
                    rk = min(0.05, th * 0.18)
                    ops.ellipse(kp[0], kp[1], rk if not vertical else rk * 0.7, rk * 0.7 if not vertical else rk, fill=alpha(shade(col, 0.55), 200))
                    ops.ellipse(kp[0], kp[1], rk * 0.5 if not vertical else rk * 0.35, rk * 0.35 if not vertical else rk * 0.5, fill=alpha(shade(col, 1.15), 200))
            if grain and rnd.random() < grain:
                gy = rnd.uniform(ys[r] + 0.05, ys[r + 1] - 0.05)
                gx0, gx1 = rnd.uniform(xa + 0.1, xa + (xb - xa) * 0.5), rnd.uniform(xa + (xb - xa) * 0.55, xb - 0.1)
                ln = LineString([T((gx0, gy)), T((gx1, gy + rnd.uniform(-0.02, 0.02)))]).intersection(g)
                if ln.geom_type == "LineString" and ln.length > 0.05:
                    ops.line(list(ln.coords), fill=alpha(shade(col, 0.72), 90), width=0.014)


def oil_stain(ops, cx, cy, rx, ry, seed=1, a=120):
    """Oelfleck (Stilblatt-Flaechenlogik): dunkler zittriger Fleck, dunklerer Kern, ein violetter Schimmerbogen."""
    ops.poly(HD.wobble_ellipse(cx, cy, rx, ry, amp=rx * 0.12, seed=seed), fill=alpha((18, 16, 22, 255), a))
    ops.poly(HD.wobble_ellipse(cx + rx * 0.1, cy - ry * 0.1, rx * 0.55, ry * 0.5, amp=rx * 0.08, seed=seed + 7),
             fill=alpha((10, 10, 14, 255), int(a * 0.7)))
    ops.line(HD.wobble([(cx - rx * 0.6, cy + ry * 0.35), (cx - rx * 0.2, cy + ry * 0.62), (cx + rx * 0.3, cy + ry * 0.5)],
                       amp=0.01, seed=seed + 3, step=0.05), fill=alpha(hexc("#8a7ab8"), 80), width=0.025)


def cable_duct(ops, pts, w=0.16, col=None, step=0.5):
    """Kabelkanal auf dem Boden: Blechprofil mit Umriss, Deckelfuge, Lichtkante und Schrauben alle `step` m."""
    col = col or lift("#5a6068", 1.25)
    ops.line(pts, fill=OUTLINE, width=w + 0.05)
    ops.line(pts, fill=col, width=w)
    ops.line(pts, fill=alpha(shade(col, 0.72), 220), width=0.012)
    ls = LineString(pts)
    s = 0.25
    while s < ls.length:
        p = ls.interpolate(s)
        ops.ellipse(p.x, p.y, 0.028, 0.028, fill=hexc("#2e3338"))
        ops.ellipse(p.x - 0.008, p.y + 0.008, 0.008, 0.008, fill=(255, 255, 255, 150))
        s += step


def dashed(ops, pts, col, width=0.06, dash=0.4, gap=0.3):
    """Gestrichelte Bodenmarkierung entlang einer Polylinie."""
    from shapely.ops import substring
    ls = LineString(pts)
    s = 0.0
    while s < ls.length:
        seg = substring(ls, s, min(ls.length, s + dash))
        if seg.geom_type == "LineString" and seg.length > 0.02:
            ops.line(list(seg.coords), fill=col, width=width)
        s += dash + gap


def plaque(ops, x0, y0, x1, y1, title="", brass=True, lines=2, size=0.075):
    """Beschriftungstafel (flach, auf Boden oder Stirnseite): Messing- oder Cremeplatte mit Umriss, Titel in
    Kapitaelchen (ASCII, HUD-Font) und angedeuteten Textzeilen."""
    fill_c = lift("#b08a3c", 1.25) if brass else hexc("#efe4c8")
    ink_c = hexc("#2a2420") if brass else hexc("#3b3630")
    ops.poly(HD.wobble_rect(x0, y0, x1, y1, amp=0.003, seed=int(x0 * 31 + y0 * 7), step=0.05), fill=fill_c, outline=OUTLINE, width=0.018)
    ops.line([(x0 + 0.02, y1 - 0.015), (x1 - 0.02, y1 - 0.015)], fill=alpha((255, 255, 255, 255), 90), width=0.01)
    mx, h = (x0 + x1) / 2, y1 - y0
    if title:
        ops.text(mx, y1 - h * 0.3, title, size, ink_c)
    for i in range(lines):
        ly = y0 + h * (0.42 - i * 0.16)
        if ly < y0 + 0.02:
            break
        ops.line([(x0 + 0.05 + (i % 2) * 0.03, ly), (x1 - 0.05 - (i % 2) * 0.05, ly)], fill=alpha(ink_c, 150), width=0.012)


def tool_wrench(ops, x, y, ang, L=0.32, col=None):
    """Schraubenschluessel flach auf dem Boden: Stiel, Maulkopf, Ringende."""
    col = col or hexc("#b8bcc0")
    ca, sa = math.cos(ang), math.sin(ang)
    p0 = (x - ca * L / 2, y - sa * L / 2)
    p1 = (x + ca * L / 2, y + sa * L / 2)
    r = L * 0.16
    ops.line([p0, p1], fill=OUTLINE, width=0.075)
    ops.line([p0, p1], fill=col, width=0.04)
    ops.ellipse(p1[0], p1[1], r, r, fill=col, outline=OUTLINE, width=0.015)
    kx, ky = p1[0] + ca * r * 0.75, p1[1] + sa * r * 0.75
    ops.poly([(kx - sa * r * 0.4, ky + ca * r * 0.4), (kx + sa * r * 0.4, ky - ca * r * 0.4), (p1[0] + ca * r * 0.1, p1[1] + sa * r * 0.1)],
             fill=shade(col, 0.45))
    ops.ellipse(p0[0], p0[1], r * 0.9, r * 0.9, fill=col, outline=OUTLINE, width=0.015)
    ops.ellipse(p0[0], p0[1], r * 0.4, r * 0.4, fill=shade(col, 0.45), outline=OUTLINE, width=0.01)
    ops.line([(p0[0] + ca * r, p0[1] + sa * r + 0.012), (p1[0] - ca * r, p1[1] - sa * r + 0.012)], fill=alpha((255, 255, 255, 255), 110), width=0.012)


def tool_rag(ops, x, y, seed=1, col=None):
    """Putzlappen: zittriger Fleck mit zwei Faltenlinien."""
    col = col or hexc("#c8503a")
    ops.poly(HD.wobble_ellipse(x, y, 0.2, 0.13, amp=0.03, seed=seed), fill=col, outline=OUTLINE, width=0.02)
    ops.line(HD.wobble([(x - 0.12, y + 0.02), (x + 0.1, y - 0.03)], amp=0.01, seed=seed + 1, step=0.04), fill=shade(col, 0.7), width=0.014)
    ops.line(HD.wobble([(x - 0.05, y + 0.08), (x + 0.04, y - 0.08)], amp=0.01, seed=seed + 2, step=0.04), fill=shade(col, 0.7), width=0.012)
    ops.ellipse(x - 0.06, y + 0.04, 0.05, 0.03, fill=alpha((255, 255, 255, 255), 50))


def tool_box(ops, x0, y0, w=0.46, d=0.22, h=0.2, col=None):
    """Werkzeugkiste mit Hoehe (K): Vorderseite, Deckel, Griffbuegel, Verschluss."""
    col = col or lift("#8a2a2a", 1.7)
    x1, y1 = x0 + w, y0 + d
    ft = y0 + h * K
    ops.rect(x0 + 0.04, y0 - 0.05, x1 + 0.06, y0 + 0.02, fill=(0, 0, 0, 70))
    ops.rect(x0, y0, x1, ft, fill=col, outline=OUTLINE, width=0.02)
    ops.rect(x0, ft, x1, y1 + h * K, fill=shade(col, 1.15), outline=OUTLINE, width=0.02)
    ops.rect(x0 + 0.02, y0 + 0.015, x1 - 0.02, y0 + 0.035, fill=alpha((0, 0, 0, 255), 60))
    ops.line([(x0 + 0.03, ft - 0.012), (x1 - 0.03, ft - 0.012)], fill=shade(col, 1.3), width=0.012)
    mx, my = (x0 + x1) / 2, (ft + y1 + h * K) / 2
    ops.line([(mx - 0.1, my), (mx - 0.1, my + 0.05), (mx + 0.1, my + 0.05), (mx + 0.1, my)], fill=OUTLINE, width=0.03)
    ops.rect(mx - 0.03, ft - 0.03, mx + 0.03, ft + 0.02, fill=hexc("#c0c8cc"), outline=OUTLINE, width=0.012)


def tool_bucket(ops, cx, cy, r=0.15, h=0.3, col=None):
    col = col or hexc("#7b8288")
    zt = cy + h * K
    ops.ellipse(cx + 0.05, cy - 0.03, r * 1.1, r * 0.6, fill=(0, 0, 0, 70))
    ops.ellipse(cx, cy, r * 0.9, r * 0.5, fill=shade(col, 0.8), outline=OUTLINE, width=0.02)
    ops.poly([(cx - r * 0.9, cy), (cx + r * 0.9, cy), (cx + r, zt), (cx - r, zt)], fill=col, outline=OUTLINE, width=0.02)
    ops.ellipse(cx, zt, r, r * 0.55, fill=shade(col, 1.15), outline=OUTLINE, width=0.02)
    ops.ellipse(cx, zt, r * 0.8, r * 0.4, fill=hexc("#2e3338"))
    ops.ellipse(cx - r * 0.2, zt + r * 0.08, r * 0.3, r * 0.12, fill=alpha(hexc("#8fc4e8"), 120))
    ops.line([(cx - r * 0.95, zt), (cx - r * 0.5, zt + r * 0.9), (cx + r * 0.5, zt + r * 0.9), (cx + r * 0.95, zt)], fill=OUTLINE, width=0.025)
    ops.line([(cx - r * 0.75, cy + h * K * 0.3), (cx - r * 0.75, zt - 0.02)], fill=alpha((255, 255, 255, 255), 90), width=0.015)


def tool_oilcan(ops, x, y, col=None):
    """Oelkanne: kleiner Zylinder mit Tuelle und Griff."""
    col = col or lift("#3b4046", 1.9)
    r, h = 0.09, 0.22
    zt = y + h * K
    ops.ellipse(x + 0.03, y - 0.02, r * 1.2, r * 0.6, fill=(0, 0, 0, 70))
    ops.poly([(x - r, y), (x + r, y), (x + r, zt), (x - r, zt)], fill=col, outline=OUTLINE, width=0.02)
    ops.ellipse(x, y, r, r * 0.5, fill=shade(col, 0.85), outline=OUTLINE, width=0.015)
    ops.ellipse(x, zt, r, r * 0.5, fill=shade(col, 1.2), outline=OUTLINE, width=0.02)
    ops.line([(x + r * 0.5, zt + 0.02), (x + r * 1.9, zt + 0.14)], fill=OUTLINE, width=0.04)
    ops.line([(x + r * 0.5, zt + 0.02), (x + r * 1.9, zt + 0.14)], fill=hexc("#c0c8cc"), width=0.02)
    ops.line([(x - r * 0.6, zt + 0.01), (x - r * 1.1, zt + 0.1), (x - r * 0.4, zt + 0.12)], fill=OUTLINE, width=0.02)
    ops.line([(x - r * 0.6, y + 0.04), (x - r * 0.6, zt - 0.02)], fill=alpha((255, 255, 255, 255), 100), width=0.012)


def floor_cable(ops, pts, seed=1, col=None, plug=True):
    """Kabel auf dem Boden: dunkle Ummantelung mit heller Kernlinie (liest sich sonst wie ein Riss),
    am Ende eine kleine Anschlussdose."""
    col = col or hexc("#2a2422")
    wob = HD.wobble(pts, amp=0.03, seed=seed, step=0.1)
    ops.line(wob, fill=OUTLINE, width=0.06)
    ops.line(wob, fill=col, width=0.04)
    ops.line([(x, y + 0.008) for x, y in wob], fill=alpha(shade(col, 2.2), 120), width=0.012)
    if plug:
        ex, ey = wob[-1]
        ops.rect(ex - 0.07, ey - 0.05, ex + 0.07, ey + 0.05, fill=hexc("#5a6068"), outline=OUTLINE, width=0.015)
        ops.ellipse(ex, ey, 0.018, 0.018, fill=hexc("#2e3338"))


def crack_line(ops, pts, col, seed=1, width=0.014):
    """Riss im Boden: zittrige Linie mit heller Kante darunter (Lichtkante der Bruchkante)."""
    wob = HD.wobble(pts, amp=0.02, seed=seed, step=0.08)
    ops.line([(x, y - 0.012) for x, y in wob], fill=alpha((255, 255, 255, 255), 50), width=width)
    ops.line(wob, fill=col, width=width)


def speckle(ops, region, n, colors, rmin, rmax, seed=3):
    rnd = random.Random(seed)
    minx, miny, maxx, maxy = region.bounds
    placed = 0
    tries = 0
    while placed < n and tries < n * 6:
        tries += 1
        x = rnd.uniform(minx, maxx); y = rnd.uniform(miny, maxy)
        if not region.contains(Point(x, y)):
            continue
        r = rnd.uniform(rmin, rmax)
        ops.ellipse(x, y, r, r, fill=rnd.choice(colors))
        placed += 1


# ------------------------------------------------------------- Bodenmuster

def floor_room(ops, key, region):
    """Bodenmuster je Raum (Entwurfskoordinaten). Voller Pass 2026-10-01: alle Raster mit Hand-Unruhe
    (wobbly_tiles), Ausstattung der Technikhalle und Werkstatt, Beschriftungstafeln in den Ausstellungsraeumen.
    Die Abnutzung entlang der Laufwege kommt als weiche Ebene nach dem Rendern (wear_lanes)."""
    fl, _wall = ROOM_ROLE[key]
    base = lift(fl, 1.0 if key == "telefon" else 1.45)
    x0, y0, x1, y1 = region.bounds
    ops.geom(region, fill=base)

    if key == "foyer":
        light, dark = lift("#9c948a"), lift("#8a8275", 1.32)
        # Schachbrett aus Marmorplatten 1,0 m, Raster leicht unruhig, Adern, abgeschlagene Ecken
        wobbly_tiles(ops, region, x0, y0, x1, y1, 1.0, 1.0, [light], lift("#6e675c", 1.1), seed=7, checker=(light, dark),
                     fuge_w=0.02, jitter=0.012, tone=0.035, chips=0.08, cracks=0.04)
        rnd = random.Random(7)
        for _ in range(60):
            ax, ay = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if region.buffer(-0.2).contains(Point(ax, ay)):
                ops.line(HD.wobble([(ax, ay), (ax + rnd.uniform(-0.3, 0.3), ay + rnd.uniform(0.3, 0.6))], amp=0.02, seed=int(ax * 13 + ay), step=0.08),
                         fill=alpha(lift("#5e584e"), 80), width=0.014)
        # roter Laeufer: Shop-Tuer -> Theke -> Rotunde, Kante zittrig, Messingband
        runner = lift("#5a2a2a", 1.6)
        ops.poly(HD.wobble_rect(-1.1, -13, 1.1, -3, amp=0.006, seed=71, step=0.1), fill=runner)
        ops.poly(HD.wobble_rect(-0.95, -13, 0.95, -3, amp=0.005, seed=72, step=0.1), outline=alpha(lift("#b08a3c"), 200), width=0.04)
        # Bodenplatte unter dem Notfallknopf (AtlasMuseumLayout.EmergencyButton, noerdlich der Theke)
        bx, by = 0.0, -5.4
        ops.ellipse(bx + 0.05, by - 0.06, 0.66, 0.52, fill=(0, 0, 0, 70))
        ops.ellipse(bx, by, 0.64, 0.5, fill=hexc("#d4b13c"), outline=OUTLINE, width=0.045)
        for i in range(12):
            a = i * math.pi / 6 + 0.2
            ops.line([(bx + 0.48 * math.cos(a), by + 0.37 * math.sin(a)), (bx + 0.62 * math.cos(a + 0.18), by + 0.48 * math.sin(a + 0.18))],
                     fill=hexc("#1e1e1e"), width=0.06)
        ops.ellipse(bx, by, 0.46, 0.35, fill=lift("#3b4046", 1.35), outline=OUTLINE, width=0.035)
        ops.ellipse(bx - 0.06, by + 0.05, 0.3, 0.2, fill=lift("#3b4046", 1.6))
        # Bodentafel am Eingang zur Rotunde ("THE VESPER COLLECTION") und Wegweiser-Pfeil
        plaque(ops, -2.4, -4.2, -1.4, -3.8, "VESPER", brass=True, lines=1, size=0.09)
        plaque(ops, 1.4, -4.2, 2.4, -3.8, "MUSEUM", brass=True, lines=1, size=0.09)
    elif key == "rotunde":
        speckle(ops, region, 2600, [lift("#8a8378"), lift("#55514a"), lift("#a8a094"), lift("#4e4a44")], 0.015, 0.035, seed=11)
        # Terrazzo-Intarsie: dunkler Ring zwischen zwei Messingbaendern (leicht zittrig), Kompassstrahlen, Rosetten
        brass = alpha(lift("#b08a3c", 1.1), 235)
        dark_ring = alpha(lift("#4e4a44", 1.25), 200)
        ring_o = HD.wobble_ellipse(0, 4, 5.6, 5.6, amp=0.012, seed=111)
        ring_i = HD.wobble_ellipse(0, 4, 4.9, 4.9, amp=0.012, seed=112)
        ops.geom(Polygon(ring_o, [list(reversed(ring_i))]).intersection(region), fill=dark_ring)
        for pts in (ring_o, ring_i):
            ops.line(pts + [pts[0]], fill=brass, width=0.06)
        for i in range(16):
            a = i * math.pi / 8
            ops.line([(math.cos(a) * 4.9, 4 + math.sin(a) * 4.9), (math.cos(a) * 5.6, 4 + math.sin(a) * 5.6)], fill=brass, width=0.045)
            if i % 4 == 0:
                rx_, ry_ = math.cos(a) * 5.25, 4 + math.sin(a) * 5.25
                ops.ellipse(rx_, ry_, 0.18, 0.18, fill=alpha(lift("#b08a3c", 1.1), 235))
                ops.ellipse(rx_, ry_, 0.08, 0.08, fill=alpha(lift("#4e4a44", 1.2), 220))
        # feine Terrazzo-Felder: unregelmaessige Plattenstoesse (Messing-Trennschienen) als Sechseck um das Podest
        for k in range(6):
            a0, a1 = k * math.pi / 3 + 0.2, (k + 1) * math.pi / 3 + 0.2
            ops.line(HD.wobble([(math.cos(a0) * 4.3, 4 + math.sin(a0) * 4.3), (math.cos(a1) * 4.3, 4 + math.sin(a1) * 4.3)], amp=0.006, seed=120 + k, step=0.1),
                     fill=alpha(lift("#b08a3c", 1.0), 110), width=0.02)
        # innerer Messingkreis um den Sockel
        ops.poly(HD.wobble_ellipse(0.5, 4, 3.0, 1.2, amp=0.008, seed=113), outline=alpha(lift("#b08a3c", 1.1), 200), width=0.04)   # Podest 5,4 x 1,8 m
        # Bodentafel vor dem Podest: Name des Exponats
        plaque(ops, -1.5, 2.55, -0.1, 2.95, "CRETACEOUS", brass=True, lines=2, size=0.085)
        # Mondfleck durch den Oculus
        ops.glow(-0.6, 3.4, 3.2, MOON, 0.35)
    elif key == "galerie":
        # Fischgraet-Parkett (Stilblatt): echte Zickzack-Reihen, Staebe 0,18 x 0,9, leicht zittrig
        cols = [lift("#63462d"), lift("#573d27"), lift("#7c5a3c"), lift("#6a4a30"), lift("#5e4228")]
        herringbone(ops, region, (x0 + x1) / 2, (y0 + y1) / 2, 0.18, 5, cols, alpha(lift("#3e2a18", 1.2), 220), seed=5)
        # Laeufer in der Achse, Kante leicht zittrig, Fransen
        run = HD.wobble_rect(x0, 3.2, x1, 4.8, amp=0.006, seed=21, step=0.1)
        ops.poly(run, fill=alpha(lift("#5b2430", 1.5), 235))
        ops.poly(HD.wobble_rect(x0, 3.32, x1, 4.68, amp=0.005, seed=22, step=0.1), outline=alpha(lift("#a8843c"), 200), width=0.035)
        ops.glow(-13.7, 4.0, 4.5, MOON, 0.22)
        # Bilderleuchten: warme Lichtkegel an den Stellwaenden
        for sx in (-17.3, -12.8):
            for sy in (1.6, 6.4):
                for side in (-0.55, 0.55):
                    ops.glow(sx + side, sy, 1.1, WARM, 0.2)
        # Bodentafel vor der Staffelei
        plaque(ops, -8.65, 6.5, -7.95, 6.76, "FOUNDER", brass=False, lines=1, size=0.065)
    elif key == "aegypten":
        cols = [lift("#8a7048"), lift("#8a6f47"), lift("#a0855a", 1.3)]
        wobbly_tiles(ops, region, x0, y0, x1, y1, 1.2, 0.8, cols, lift("#6a5436", 1.2), seed=9, bond=0.5, fuge_w=0.03,
                     jitter=0.03, tone=0.05, chips=0.14, cracks=0.07)
        # Mittelgang als Sandsteinband mit Ornament
        ops.poly(HD.wobble_rect(-27.0, y0, -26.2, y1, amp=0.006, seed=91, step=0.12), fill=alpha(lift("#b8843a", 1.1), 120))
        for yy in range(int(y0) + 1, int(y1)):
            ops.poly([(-26.6, yy - 0.25), (-26.35, yy), (-26.6, yy + 0.25), (-26.85, yy)], fill=alpha(lift("#3f2e1c", 1.3), 160))
        # Sandspuren an den Sarkophagen (hellere, zittrige Flecken) und Bodentafeln vor den Exponaten
        rnd = random.Random(92)
        for cx_, cy_ in ((-27.4, 4.5), (-27.4, -1.5), (-24.8, 5.9), (-24.8, 1.9), (-24.8, -2.1)):
            ops.poly(HD.wobble_ellipse(cx_ + rnd.uniform(-0.2, 0.2), cy_, 0.5, 0.25, amp=0.04, seed=93 + int(cy_ * 3)), fill=alpha(lift("#c9a46a", 1.1), 55))
        plaque(ops, -27.65, 2.75, -26.95, 3.05, "KV-7", brass=False, lines=1, size=0.08)
        plaque(ops, -27.65, -3.25 + 2.3, -26.95, -3.25 + 2.6, "KV-9", brass=False, lines=1, size=0.08)
        plaque(ops, -23.1, -0.3, -22.3, 0.0, "STELE", brass=False, lines=1, size=0.07)
        # warmes Grablicht an den Sarkophagen und der Sphinx
        for gx, gy in ((-28.1, 4.5), (-28.1, -1.5), (-25.7, 9.0)):
            ops.glow(gx, gy, 2.0, WARM, 0.3)
    elif key == "planetarium":
        speckle(ops, region, 900, [alpha(hexc("#cfe0ff"), 170), alpha(hexc("#cfe0ff"), 90)], 0.012, 0.03, seed=13)
        # Teppichringe (flach, begehbar): zwei Boegen mit Luecken nach S und E, Kanten leicht zittrig. Bewusst OHNE
        # Umriss und Sitz-Buckel, sonst lesen sie sich als Baenke, durch die man laufen kann.
        ring = alpha(lift("#2b3552", 1.5), 150)
        edge = alpha(lift("#6f86c8", 1.2), 170)
        for r in (2.4, 3.6):
            for a0, a1 in ((20, 250), (290, 330)):
                pts_o = [(-14.45 + (r + 0.25) * math.cos(math.radians(a)), 15.7 + (r + 0.25) * math.sin(math.radians(a))) for a in range(a0, a1 + 1, 5)]
                pts_i = [(-14.45 + (r - 0.25) * math.cos(math.radians(a)), 15.7 + (r - 0.25) * math.sin(math.radians(a))) for a in range(a1, a0 - 1, -5)]
                pts_o = HD.wobble(pts_o, amp=0.008, seed=130 + int(r * 10) + a0, step=0.1)
                pts_i = HD.wobble(pts_i, amp=0.008, seed=131 + int(r * 10) + a0, step=0.1)
                ops.poly(pts_o + pts_i, fill=ring)
                ops.line(pts_o, fill=edge, width=0.025)
                ops.line(pts_i, fill=edge, width=0.025)
                for a in range(a0 + 6, a1 - 2, 12):
                    sx = -14.45 + r * math.cos(math.radians(a)); sy = 15.7 + r * math.sin(math.radians(a))
                    ops.ellipse(sx, sy, 0.05, 0.05, fill=alpha(hexc("#cfe0ff"), 150))
        # Tierkreis-Zeichen als helle Bodenlinien um den Projektor (Sternbildlinien)
        rnd = random.Random(14)
        for k in range(5):
            a = k * math.tau / 5 + 0.4
            px_, py_ = -14.45 + 1.4 * math.cos(a), 15.7 + 1.4 * math.sin(a)
            pts = [(px_ + rnd.uniform(-0.3, 0.3), py_ + rnd.uniform(-0.3, 0.3)) for _ in range(4)]
            ops.line(pts, fill=alpha(hexc("#9fb8e8"), 120), width=0.012)
            for p in pts:
                ops.ellipse(p[0], p[1], 0.02, 0.02, fill=alpha(hexc("#f4f8ff"), 220))
        plaque(ops, -15.3, 13.45, -14.3, 13.85, "ORRERY", brass=False, lines=1, size=0.08)
        ops.glow(-14.45, 15.7, 2.0, hexc("#cfe0ff"), 0.25)
    elif key == "mineralien":
        cols = [lift("#33383c", 1.6), lift("#464c51", 1.35), lift("#2d3135", 1.7)]
        # Rautenmuster: diagonale Platten, jede mit leichtem Zittern und eigenem Ton
        rnd = random.Random(17)
        step = 1.0
        for i in range(-30, 30):
            for j in range(-30, 30):
                cx, cy = i * step, 11 + j * step
                cx2 = cx + (step / 2 if j % 2 else 0)
                d = step / 2
                raw = [(cx2, cy - d), (cx2 + d, cy), (cx2, cy + d), (cx2 - d, cy)]
                if not Polygon(raw).intersects(region):
                    continue
                q = Polygon(HD.wobble(raw, amp=0.005, seed=170 + i * 61 + j, step=0.07, closed=True)).buffer(0).intersection(region)
                if not q.is_empty:
                    ops.geom(q, fill=shade(rnd.choice(cols), 1 + rnd.uniform(-0.05, 0.05)), outline=alpha(lift("#22262a", 1.4), 255), width=0.025)
        for gx, gy in ((0, 15.5), (-4, 19.6), (0, 19.6), (4, 19.6), (-3, 12.8), (3, 12.8)):
            ops.glow(gx, gy - 0.6, 1.6, WARM, 0.3)
        plaque(ops, -0.7, 13.1, 0.7, 13.5, "TREASURY", brass=True, lines=1, size=0.08)
    elif key == "telefon":
        cols = [lift("#a05630", 1.0), lift("#a8562a", 0.95)]
        wobbly_tiles(ops, region, x0, y0, x1, y1, 2.0, 1.0, cols, lift("#8e4823", 1.1), seed=21, bond=0.5, fuge_w=0.025,
                     jitter=0.02, tone=0.04, chips=0.06, cracks=0.03)
        # Siebziger-Rundteppich (flach, begehbar) in der freien Raummitte: Ringe in Orange, Creme, Braun
        rcx, rcy = 15.0, 17.4
        for k, (r, col) in enumerate(((1.6, "#c8702e"), (1.4, "#efd9a8"), (1.22, "#8e4823"), (1.0, "#c8702e"), (0.75, "#efd9a8"), (0.5, "#8e4823"), (0.25, "#e0b04a"))):
            ops.poly(HD.wobble_ellipse(rcx, rcy, r, r, amp=0.008, seed=210 + k), fill=alpha(lift(col, 1.05), 215))
        ops.poly(HD.wobble_ellipse(rcx, rcy, 1.6, 1.6, amp=0.008, seed=210), outline=alpha(lift("#5a2a12", 1.2), 200), width=0.03)
        # kleine Kreise als Echo des Teppichs an den Waenden
        for cx_, cy_ in ((10.6, 14.0), (16.8, 14.1), (10.4, 18.6)):
            ops.ellipse(cx_, cy_, 0.5, 0.5, fill=alpha(lift("#c8702e", 1.2), 90))
            ops.ellipse(cx_, cy_, 0.28, 0.28, fill=alpha(lift("#efd9a8", 1.0), 110))
        # Telefonkabel am Boden (vom Vermittlungstisch zur Westwand) und Bodentafel
        floor_cable(ops, [(10.0, 16.0), (9.4, 16.3), (9.2, 17.2)], seed=212)
        plaque(ops, 11.5, 14.6, 12.5, 15.0, "EXCHANGE", brass=False, lines=1, size=0.07)
        ops.glow(rcx, rcy, 2.4, WARM, 0.22)
    elif key == "technikhalle":
        # Riffelblech-Platten 2,0 x 2,5 m mit zittrigen Stoessen, Rippen, Schrauben an den Platten-Ecken
        plate = [lift("#4d5258", 1.45), lift("#50555b", 1.42), lift("#4a4f55", 1.48)]
        wobbly_tiles(ops, region, x0, y0, x1, y1, 2.0, 2.5, plate, lift("#363a3f", 1.2), seed=23, bond=0.0, fuge_w=0.03,
                     jitter=0.006, tone=0.03, chips=0.0, cracks=0.0, amp=0.003)
        rib_a, rib_b = lift("#6a7178", 1.3), lift("#363a3f", 1.3)
        yy = y0 + 0.15
        r = 0
        while yy < y1:
            xx = x0 + 0.15
            c = 0
            while xx < x1:
                if (r + c) % 2 == 0:
                    ops.line([(xx - 0.06, yy - 0.03), (xx + 0.06, yy + 0.03)], fill=rib_a, width=0.035)
                else:
                    ops.line([(xx - 0.06, yy + 0.03), (xx + 0.06, yy - 0.03)], fill=rib_b, width=0.035)
                xx += 0.3; c += 1
            yy += 0.3; r += 1
        for px_ in range(9, 20, 2):
            for py_ in (3.5, 6.0, 8.5):
                if region.buffer(-0.1).contains(Point(px_, py_)):
                    ops.ellipse(px_, py_, 0.035, 0.035, fill=hexc("#2e3338"), outline=alpha(OUTLINE, 160), width=0.01)
                    ops.ellipse(px_ - 0.01, py_ + 0.01, 0.01, 0.01, fill=(255, 255, 255, 150))
        # Warnstreifen um Maschinen
        hazard(ops, 8.7, 4.6, 14.9, 4.9)
        hazard(ops, 14.7, 5.2, 19.3, 5.45)
        # Besucherweg: gelbe Bodenmarkierung (gestrichelt), Abzweige zum Rolltor, zur Werkstatt und zur Telefonzentrale
        mark = alpha(hexc("#d4b13c"), 200)
        dashed(ops, [(7.3, 3.6), (19.3, 3.6)], mark, width=0.06, dash=0.45, gap=0.3)
        dashed(ops, [(15.2, 3.4), (15.2, 1.15)], mark, width=0.06, dash=0.45, gap=0.3)
        dashed(ops, [(8.1, 3.8), (8.1, 8.6), (13.2, 8.6), (13.2, 9.35)], mark, width=0.06, dash=0.45, gap=0.3)
        for ax, ay, dx in ((11.0, 3.6, 1), (17.0, 3.6, -1)):
            ops.poly([(ax - 0.12 * dx, ay - 0.1), (ax + 0.12 * dx, ay), (ax - 0.12 * dx, ay + 0.1)], fill=mark)
        # Kabelkanaele: vom Schwungrad zur Suedwand, von der Turbine zur Ostwand
        cable_duct(ops, [(13.9, 4.55), (13.9, 1.05)])
        cable_duct(ops, [(18.5, 5.15), (18.5, 4.3), (19.45, 4.3)])
        # Oelflecken unter den Maschinen und vor der Turbine
        oil_stain(ops, 12.4, 4.2, 0.42, 0.22, seed=231, a=110)
        oil_stain(ops, 16.1, 4.65, 0.55, 0.26, seed=232, a=120)
        oil_stain(ops, 9.6, 8.1, 0.3, 0.18, seed=233, a=90)
        # Werkzeug am Boden: Kiste, Schluessel, Lappen, Eimer, Oelkanne
        tool_box(ops, 10.35, 4.0)
        tool_wrench(ops, 11.25, 3.95, -0.3)
        tool_rag(ops, 9.9, 3.85, seed=234)
        tool_oilcan(ops, 11.95, 4.15)
        tool_bucket(ops, 7.6, 7.3)
        tool_wrench(ops, 7.75, 6.6, 1.25, L=0.26)
        tool_rag(ops, 8.7, 9.0, seed=235, col=hexc("#9aa3a6"))
        # Beschriftungstafeln der Exponate (Messing, am Boden vor den Maschinen)
        plaque(ops, 10.3, 4.33, 11.9, 4.58, "STEAM ENGINE 1887", brass=True, lines=1, size=0.075)
        plaque(ops, 15.6, 4.9, 16.9, 5.15, "TURBINE", brass=True, lines=1, size=0.075)
        plaque(ops, 12.9, 7.4, 13.9, 7.65, "FLYWHEEL", brass=True, lines=1, size=0.07)
        # Ausstellungsbeleuchtung
        for gx, gy in ((11, 5.2), (16.2, -0.9), (17, 6.2)):
            ops.glow(gx, gy, 2.4, WARM, 0.28)
    elif key == "werkstatt":
        cols = [lift("#9aa3a6", 1.3), lift("#929a9d", 1.3), lift("#a0a8aa", 1.28)]
        wobbly_tiles(ops, region, x0, y0, x1, y1, 0.5, 0.5, cols, lift("#7b8488", 1.2), seed=23, fuge_w=0.02,
                     jitter=0.02, tone=0.03, chips=0.05, cracks=0.03, amp=0.003)
        # Scanner-Podest mit Klebeband-Markierung (gelb/schwarz gestrichelt) und Kabel zur Ostwand
        ops.poly(HD.wobble_rect(15, -9.5, 17, -7.5, amp=0.004, seed=241, step=0.1), fill=lift("#8b949a", 1.25), outline=OUTLINE, width=0.04)
        ops.ellipse(16, -8.5, 0.8, 0.8, outline=alpha(hexc("#6fd6ff"), 220), width=0.05)
        ops.glow(16, -8.5, 2.2, hexc("#d8e6ec"), 0.35)
        tape = alpha(hexc("#d4b13c"), 220)
        for pts in ([(14.6, -9.85), (14.6, -7.15), (17.4, -7.15)], [(17.4, -7.15), (17.4, -9.85), (14.6, -9.85)]):
            dashed(ops, pts, tape, width=0.05, dash=0.25, gap=0.12)
        floor_cable(ops, [(17.0, -8.3), (18.2, -8.0), (19.35, -8.1)], seed=242)
        # Restaurierungsplatz: Abdecktuch mit einem Gemaelde in Arbeit, Pinsel, Farbtoepfe, Farbtropfen
        cloth = HD.wobble_rect(9.5, -8.9, 11.9, -7.3, amp=0.02, seed=243, step=0.15)
        ops.poly(cloth, fill=lift("#d8cfb0", 1.0), outline=alpha(shade(lift("#d8cfb0"), 0.7), 220), width=0.02)
        ops.line(HD.wobble([(9.7, -8.1), (11.7, -8.0)], amp=0.02, seed=244, step=0.1), fill=alpha(shade(lift("#d8cfb0"), 0.8), 160), width=0.015)
        rnd = random.Random(245)
        for _ in range(14):
            px_, py_ = rnd.uniform(9.6, 11.8), rnd.uniform(-8.8, -7.4)
            ops.ellipse(px_, py_, rnd.uniform(0.02, 0.05), rnd.uniform(0.015, 0.04), fill=alpha(rnd.choice([hexc("#d33a2a"), hexc("#2f4fa0"), hexc("#f2c23a"), hexc("#4f8a3a")]), 180))
        painting(ops, 10.2, -8.65, 11.1, -7.95, "berg", rnd)
        ops.rect(10.55, -8.4, 10.8, -8.1, fill=alpha(lift("#d8cfb0"), 200))   # noch unrestaurierte Stelle
        for k, col in enumerate(("#d33a2a", "#2f4fa0", "#f2c23a")):
            ops.ellipse(11.4 + k * 0.17, -8.55, 0.07, 0.07, fill=hexc(col), outline=OUTLINE, width=0.015)
            ops.ellipse(11.4 + k * 0.17, -8.55, 0.04, 0.04, fill=shade(hexc(col), 1.25))
        for k in range(3):
            bx = 11.3 + k * 0.1
            ops.line([(bx, -7.75), (bx + 0.05, -7.45)], fill=hexc("#6b4a2e"), width=0.018)
            ops.line([(bx + 0.05, -7.45), (bx + 0.065, -7.37)], fill=rnd.choice([hexc("#d33a2a"), hexc("#2f4fa0")]), width=0.025)
        tool_wrench(ops, 13.4, -9.3, 0.9, L=0.24)
        tool_rag(ops, 12.1, -9.4, seed=246, col=hexc("#5f8fc8"))
        tool_bucket(ops, 18.9, -9.4, r=0.13, h=0.26)
        # Lupe und Pinsel am Boden vor dem Analysetisch
        ops.ellipse(13.9, -5.1, 0.1, 0.1, fill=alpha(hexc("#bfe3f5"), 120), outline=OUTLINE, width=0.02)
        ops.line([(13.98, -5.18), (14.2, -5.4)], fill=OUTLINE, width=0.035)
        plaque(ops, 15.4, -7.05, 16.6, -6.75, "SCAN STATION", brass=False, lines=1, size=0.07)
    elif key == "depot":
        speckle(ops, region, 1500, [lift("#66635e"), lift("#3e3c39", 1.4)], 0.01, 0.03, seed=29)
        for xx in (23.5, 26.5):
            ops.line(HD.wobble([(xx, y0), (xx, y1)], amp=0.006, seed=290 + int(xx), step=0.15), fill=lift("#423f3b", 1.3), width=0.03)
        for yy in range(-20, -6, 3):
            ops.line(HD.wobble([(x0, yy), (x1, yy)], amp=0.006, seed=300 + yy, step=0.15), fill=lift("#423f3b", 1.3), width=0.03)
        # Risse im Estrich, Gassenmarkierung, Reifenspuren vom Rolltor
        crack_line(ops, [(22.3, -12.8), (23.4, -12.2), (24.0, -11.7)], alpha(lift("#2e2c29", 1.2), 220), seed=291)
        crack_line(ops, [(26.9, -7.6), (26.2, -8.3)], alpha(lift("#2e2c29", 1.2), 220), seed=292)
        for gy in (-11.4, -15.4):
            ops.line(HD.wobble([(22.9, gy), (28.3, gy)], amp=0.005, seed=293 + int(gy), step=0.2), fill=alpha(hexc("#d4b13c"), 170), width=0.06)
        ops.line(HD.wobble([(21.9, -19.2), (21.9, -7.0)], amp=0.005, seed=294, step=0.2), fill=alpha(hexc("#d4b13c"), 170), width=0.06)
        for off in (-0.35, 0.35):
            ops.line(HD.wobble([(23.0 + off, -6.3), (23.2 + off, -8.0), (24.0 + off, -10.3), (25.0 + off, -12.2)], amp=0.03, seed=295 + int(off * 10), step=0.3),
                     fill=alpha((20, 20, 24, 255), 60), width=0.16)
        hazard(ops, 21.8, -19.95, 22.8, -19.6)
        plaque(ops, 22.2, -7.55, 23.3, -7.25, "LOADING DOCK", brass=False, lines=1, size=0.065)
    elif key == "sicherheit":
        # Noppenboden
        noppe = lift("#313539", 1.9)
        yy = y0 + 0.2
        while yy < y1:
            xx = x0 + 0.2
            while xx < x1:
                ops.ellipse(xx, yy, 0.05, 0.05, fill=noppe)
                xx += 0.4
            yy += 0.4
        # Kabel von der Monitorwand am Boden entlang, Kaffeering, Bodentafel
        floor_cable(ops, [(-28.9, -15.0), (-28.2, -15.3), (-27.4, -14.9), (-26.7, -15.2)], seed=251)
        floor_cable(ops, [(-28.9, -14.2), (-28.4, -14.6), (-27.9, -14.3)], seed=252, col=hexc("#2f4f8a"), plug=False)
        ops.ellipse(-25.6, -19.0, 0.07, 0.07, outline=alpha(hexc("#5a3a22"), 150), width=0.018)
        ops.glow(-28.5, -16.8, 2.2, hexc("#b7c4c8"), 0.3)
    elif key == "haustechnik":
        speckle(ops, region, 700, [lift("#5c574f"), lift("#433f39", 1.3)], 0.01, 0.03, seed=31)
        oil_stain(ops, -24.2, -9.3, 0.5, 0.32, seed=311, a=90)
        oil_stain(ops, -27.0, -11.4, 0.35, 0.22, seed=312, a=90)
        crack_line(ops, [(-28.0, -6.0), (-27.2, -6.5), (-26.9, -7.3)], alpha(lift("#2e2c29", 1.2), 220), seed=313)
        crack_line(ops, [(-23.5, -11.2), (-23.0, -10.5)], alpha(lift("#2e2c29", 1.2), 220), seed=314)
        hazard(ops, -28.6, -11.6, -28.3, -8.6, vertical=True)
        # Kabelkanal vom Schaltschrank zum Kessel, Sperrzone um den Kessel
        cable_duct(ops, [(-28.55, -10.1), (-27.5, -10.1), (-27.5, -9.1)], w=0.14)
        dashed(ops, [(-28.3, -7.7), (-26.7, -7.7), (-26.7, -9.3)], alpha(hexc("#d4b13c"), 180), width=0.05, dash=0.3, gap=0.2)
        ops.ellipse(-25.5, -9.5, 0.22, 0.22, fill=lift("#7b8288"), outline=OUTLINE, width=0.03)  # Gully
        for k in range(3):
            ops.line([(-25.65, -9.42 + k * 0.08 - 0.08), (-25.35, -9.42 + k * 0.08 - 0.08)], fill=hexc("#2e3338"), width=0.02)
        tool_bucket(ops, -23.2, -6.0, r=0.14, h=0.28)
        tool_rag(ops, -23.7, -5.7, seed=315, col=hexc("#9aa3a6"))
    elif key == "shop":
        cols = [lift("#7ea89a", 1.2), lift("#5a7f72", 1.35)]
        wobbly_tiles(ops, region, x0, y0, x1, y1, 0.6, 0.6, cols, lift("#4c6b60", 1.2), seed=37, checker=(cols[0], cols[1]),
                     fuge_w=0.02, jitter=0.02, tone=0.035, chips=0.05, cracks=0.02, amp=0.003)
        # Cafe-Bereich: Holzboden
        cafe = sbox(1.5, -20.4, 9, -16.2).intersection(region)
        ops.geom(cafe, fill=lift("#a08a68", 1.2))
        xx = 1.5
        while xx < 9:
            ops.line([(xx, -20.4), (xx, -16.2)], fill=lift("#7a5636", 1.2), width=0.02)
            xx += 0.25
        ops.glow(-6, -15.7, 2.0, WARM, 0.25)
        ops.glow(6.2, -15.7, 2.0, WARM, 0.25)
    elif key == "hof":
        speckle(ops, region, 1800, [lift("#474a4f", 1.2), lift("#2e3034", 1.4)], 0.01, 0.03, seed=41)
        mark = alpha(lift("#b8ac70"), 150)
        for yy in (-0.1, 6.4):    # Parkbucht des Lieferwagens (y 0,4..5,9)
            ops.line(HD.wobble([(26, yy), (29, yy)], amp=0.006, seed=410 + int(yy * 10), step=0.2), fill=mark, width=0.1)
        ops.line(HD.wobble([(27, -5.5), (27, -2.5)], amp=0.006, seed=411, step=0.2), fill=mark, width=0.1)
        # Reifenspuren vom Lieferwagen zum Rolltor-Vorplatz, Risse im Hofbeton
        for off in (-0.4, 0.4):
            ops.line(HD.wobble([(27.3 + off, 1.0), (26.8 + off, 7.2), (25.6 + off, 8.6)], amp=0.03, seed=412 + int(off * 10), step=0.3),
                     fill=alpha((20, 20, 24, 255), 55), width=0.18)
        crack_line(ops, [(25.3, 2.2), (25.9, 2.9), (26.1, 3.8)], alpha(lift("#2e2c29", 1.2), 220), seed=413)
        # Rampe (Deck 0): Betonrampe mit Rillen und Warnkante
        ops.rect(21.5, -2, 24.5, 8, fill=lift("#6a6864", 1.25))
        yy = -2
        while yy < 8:
            ops.line(HD.wobble([(21.5, yy), (24.5, yy)], amp=0.004, seed=420 + int(yy * 2), step=0.2), fill=lift("#5d5c58", 1.15), width=0.025)
            yy += 0.5
        ops.rect(21.5, -6, 24.5, -2, fill=lift("#5d5c58", 1.3))           # Karrenschraege
        for i in range(8):
            ops.line([(21.5, -6 + i * 0.5), (24.5, -6 + i * 0.5)], fill=lift("#4f4e4a", 1.2), width=0.03)
        hazard(ops, 24.3, -2, 24.55, 6, vertical=True)
        hazard(ops, 21.5, 7.8, 24.5, 8.05)
        oil_stain(ops, 23.0, 4.4, 0.3, 0.18, seed=414, a=80)
        # Treppe Rampe -> Hof
        for i in range(3):
            ops.rect(24.5 + i * 0.5, 6, 25.0 + i * 0.5, 8, fill=shade(lift("#6a6864", 1.2), 1 - i * 0.12), outline=OUTLINE, width=0.03)
        ops.glow(28.8, 10.5, 4.5, hexc("#ffb347"), 0.35)


def hazard(ops, x0, y0, x1, y1, vertical=False):
    ops.rect(x0, y0, x1, y1, fill=hexc("#d4b13c"))
    n = int(((y1 - y0) if vertical else (x1 - x0)) / 0.25) + 1
    for i in range(n):
        if vertical:
            a = y0 + i * 0.25
            ops.poly([(x0, a), (x1, a + 0.12), (x1, min(y1, a + 0.24)), (x0, min(y1, a + 0.12))], fill=hexc("#1e1e1e"))
        else:
            a = x0 + i * 0.25
            if a >= x1:
                break
            ops.poly([(a, y0), (min(x1, a + 0.12), y0), (min(x1, a + 0.24), y1), (min(x1, a + 0.12), y1)], fill=hexc("#1e1e1e"))
    ops.rect(x0, y0, x1, y1, outline=OUTLINE, width=0.025)


# ------------------------------------------------------------ Waende & Deko

def owner_of(pt, rooms):
    for key, poly in rooms.items():
        if poly.buffer(0.02).contains(pt):
            return key
    return None


def decor_outside(ops):
    # Lichthof: Rasen, Kies, Baum, Baenke (nicht begehbar, nur durch Fenster sichtbar)
    ops.rect(-21.5, -16, -8.5, -5, fill=hexc("#3f6b45"))
    speckle(ops, sbox(-21.5, -16, -8.5, -5), 900, [hexc("#4c7d52"), hexc("#355c3a")], 0.02, 0.06, seed=51)
    ops.poly([(-21.5, -11.2), (-8.5, -9.8), (-8.5, -9.0), (-21.5, -10.4)], fill=hexc("#9a9282"))
    for bx, by in ((-18.5, -7.2), (-11.5, -14.0)):
        ops.rect(bx - 0.9, by - 0.25, bx + 0.9, by + 0.25, fill=hexc("#8a8578"), outline=OUTLINE, width=0.04)
    for cx, cy, r in ((-15, -10.5, 2.6), (-19.8, -14.3, 1.1), (-9.8, -6.3, 1.0)):
        ops.ellipse(cx + 0.3, cy - 0.4, r, r * 0.9, fill=alpha((10, 20, 12, 255), 90))
        ops.ellipse(cx, cy, r, r * 0.92, fill=hexc("#2f6b3a"), outline=OUTLINE, width=0.06)
        ops.ellipse(cx - r * 0.3, cy + r * 0.3, r * 0.55, r * 0.5, fill=hexc("#3f8a4a"))
    ops.glow(-15, -10.5, 3.5, MOON, 0.25)
    # Nordhof hinter dem Zaun
    ops.rect(21.5, 12.5, 29.4, 20.4, fill=lift("#3a3c40", 1.15))
    for (x0, y0) in ((23, 14), (23, 17)):
        ops.rect(x0, y0, x0 + 2.5, y0 + 2, fill=lift("#2f4f7a", 1.4), outline=OUTLINE)
        ops.rect(x0, y0 + 1.6, x0 + 2.5, y0 + 2, fill=lift("#2f4f7a", 1.8), outline=OUTLINE, width=0.04)
    # Zaun
    for pts in (((21.5, 12.25), (30, 12.25)), ((29.9, -6.5), (29.9, 21)), ((21.5, -6.4), (29.9, -6.4))):
        ops.line(list(pts), fill=hexc("#8a9398"), width=0.07)
    for x in [21.5 + i * 1.25 for i in range(8)]:
        ops.ellipse(x, 12.25, 0.07, 0.07, fill=hexc("#6b7378"), outline=OUTLINE, width=0.02)
    ops.rect(26.5, 12.1, 29, 12.4, fill=hexc("#8a9196"), outline=OUTLINE, width=0.03)


WALL_OUT = 1.0       # Staerke der Aussenwand (Wandkrone um den Grundriss)
AO_PPM = 16          # Aufloesung der AO-Maske (px/m); wird weich hochskaliert
AO_SIGMA = 0.28      # Weichheit in m
AO_STRENGTH = 0.62   # Verdunklung bei voll umschlossenem Punkt (gerade Wand ~ halb, Innenecke ~ drei Viertel)
AO_COLOR = (4, 6, 12)


def walk_mask(walk, x0, y0, x1, y1, ppm, w, h):
    """L-Maske der begehbaren Flaeche (255 = begehbar, Loecher ausgespart)."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)

    def P(pts):
        return [((x - x0) * ppm, (y1 - y) * ppm) for x, y in pts]

    for p in ([walk] if walk.geom_type == "Polygon" else list(walk.geoms)):
        d.polygon(P(p.exterior.coords), fill=255)
        for hole in p.interiors:
            d.polygon(P(hole.coords), fill=0)
    return m


def ambient_occlusion(img, walk, x0, y0, x1, y1):
    """Weiche Verdunklung an allen Waenden, NACH dem Rendern auf das fertige Bodenbild.
    Feste Wandmasse klein rastern, gaussisch verwischen, weich hochskalieren und nur auf der
    begehbaren Flaeche abdunkeln: keine Segmentbaender, keine Stufen in Ecken, Stirnseiten
    und Wandkrone (beide auf der Wandmasse) bleiben unberuehrt."""
    lw, lh = max(1, int(round((x1 - x0) * AO_PPM))), max(1, int(round((y1 - y0) * AO_PPM)))
    solid = walk_mask(walk, x0, y0, x1, y1, AO_PPM, lw, lh).point(lambda v: 255 - v)
    solid = solid.filter(ImageFilter.GaussianBlur(AO_SIGMA * AO_PPM))
    solid = solid.resize(img.size, Image.BICUBIC)
    ppm = img.width / (x1 - x0)
    inside = walk_mask(walk, x0, y0, x1, y1, ppm, img.width, img.height)
    from PIL import ImageChops
    amount = ImageChops.multiply(solid, inside).point(lambda v: int(v * AO_STRENGTH))
    dark = Image.new(img.mode, img.size, AO_COLOR)
    return Image.composite(dark, img, amount)


def crown_rim(ops, walk, building):
    """Lichtkante auf der Wandkrone entlang jeder Raumkante (gibt der Wandmasse Volumen)."""
    polys = [walk] if walk.geom_type == "Polygon" else list(walk.geoms)
    for p in polys:
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            for i in range(len(ring) - 1):
                seg = LineString([ring[i], ring[i + 1]])
                if seg.length < 0.05:
                    continue
                band = seg.buffer(0.16, cap_style=2, join_style=2).difference(walk).intersection(building)
                for g in ([band] if band.geom_type == "Polygon" else [q for q in getattr(band, "geoms", []) if q.geom_type == "Polygon"]):
                    if len(g.interiors) == 0 and not g.is_empty:
                        ops.poly(list(g.exterior.coords)[:-1], fill=WALL_TOP_EDGE)


def wall_faces(ops, walk, rooms, corridors):
    """Stirnseiten der Nordwaende + Kontaktschatten + Kronenkante."""
    rings = []
    polys = [walk] if walk.geom_type == "Polygon" else list(walk.geoms)
    for p in polys:
        rings.append(list(p.exterior.coords))
        for h in p.interiors:
            rings.append(list(h.coords))
    solid = sbox(-40, -40, 40, 40).difference(walk)
    face_h = 0.95   # wird von der Wandmasse beschnitten: Innenwaende 0,5, Aussenwaende hoeher
    for ring in rings:
        for i in range(len(ring) - 1):
            (x0, y0), (x1, y1) = ring[i], ring[i + 1]
            dx, dy = x1 - x0, y1 - y0
            ln = math.hypot(dx, dy)
            if ln < 1e-6:
                continue
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            # Wand liegt noerdlich, wenn der Punkt knapp darueber fest und knapp darunter frei ist
            above = Point(mx, my + 0.05)
            below = Point(mx, my - 0.05)
            if not (solid.contains(above) and walk.contains(below)):
                continue
            if abs(dy) > abs(dx) * 1.5:
                continue  # fast senkrecht: keine sichtbare Stirnseite
            owner = owner_of(below, rooms)
            if owner:
                wall = lift(ROOM_ROLE[owner][1], 1.5)
            else:
                wall = lift(GANG_WALL, 1.3)
            # Oberkante der Stirnseite mit leichtem Zittern (Stilblatt); Innenwaende beschneidet die Wandmasse
            top_edge = HD.wobble([(x1, y1 + face_h), (x0, y0 + face_h)], amp=0.006, seed=int(abs(x0 * 7 + y0 * 3)), step=0.1)
            face = Polygon([(x0, y0), (x1, y1)] + top_edge).buffer(0).intersection(solid.buffer(0.001))
            if face.is_empty:
                continue
            ops.geom(face, fill=wall)
            # Gliederung: dunklere Sockelzone (Lambris) bis 0,32, Leiste, hellerer Putz darueber
            wains = Polygon([(x0, y0), (x1, y1), (x1, y1 + 0.32), (x0, y0 + 0.32)]).intersection(face)
            ops.geom(wains, fill=shade(wall, 0.84))
            rail = Polygon([(x0, y0 + 0.30), (x1, y1 + 0.30), (x1, y1 + 0.345), (x0, y0 + 0.345)]).intersection(face)
            ops.geom(rail, fill=shade(wall, 1.22))
            upper = Polygon([(x0, y0 + 0.6), (x1, y1 + 0.6), (x1, y1 + face_h), (x0, y0 + face_h)]).intersection(face)
            ops.geom(upper, fill=shade(wall, 1.08))
            # Sockelleiste + obere Kante
            base = Polygon([(x0, y0), (x1, y1), (x1, y1 + 0.08), (x0, y0 + 0.08)]).intersection(face)
            ops.geom(base, fill=shade(wall, 0.62))
            top = Polygon([(x0, y0 + face_h - 0.05), (x1, y1 + face_h - 0.05), (x1, y1 + face_h), (x0, y0 + face_h)]).intersection(face)
            ops.geom(top, fill=shade(wall, 1.25))
            # sichtbare Hoehe: Innenwaende (0,5 m) schneiden die Stirnseite; Deko darf nicht auf den
            # Boden des Nachbarraums ragen. Voller Pass: je Teilstueck gleicher Hoehe eigene Deko (ein
            # Segment kann aussen 0,95 und am Nachbarraum 0,5 m hoch sein; eine Tafel lag sonst im Planetarium)
            runs = []
            n = max(1, int(ln / 0.25))
            for k in range(n):
                t0, t1 = k / n, (k + 1) / n
                px_ = x0 + dx * (t0 + t1) / 2
                probe = LineString([(px_, my), (px_, my + face_h)]).intersection(solid)
                fh_k = round(min(face_h, probe.length) if not probe.is_empty else face_h, 2)
                if runs and abs(runs[-1][2] - fh_k) < 0.03:
                    runs[-1][1] = t1
                else:
                    runs.append([t0, t1, fh_k])
            for t0, t1, fh_k in runs:
                if (t1 - t0) * ln > 0.3:
                    face_decor(ops, owner, x0 + dx * t0, y0, x0 + dx * t1, y1, fh_k, wall)
            # Kontaktschatten auf dem Boden
            sh = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.28), (x0, y0 - 0.28)]).intersection(walk)
            ops.geom(sh, fill=(0, 0, 0, 55))
            sh2 = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.12), (x0, y0 - 0.12)]).intersection(walk)
            ops.geom(sh2, fill=(0, 0, 0, 45))


def wall_poster(ops, x, p0, w, p1, motif, rnd, label=True):
    """Gerahmtes Bild auf einer Stirnseite mit Schlagschatten, Bilderleuchte auf der Krone und kleinem
    Beschriftungsschild rechts daneben (Ausstellungsraeume, voller Pass)."""
    ops.rect(x + 0.02, p0 - 0.02, x + w + 0.02, p1 - 0.02, fill=(0, 0, 0, 60))
    painting(ops, x, p0, x + w, p1, motif, rnd)
    ops.glow(x + w / 2, p1 - 0.05, 0.35, WARM, 0.25)
    ops.rect(x + w / 2 - 0.06, p1 + 0.005, x + w / 2 + 0.06, p1 + 0.03, fill=hexc("#c9a24c"), outline=OUTLINE, width=0.01)
    if label:
        ops.rect(x + w + 0.05, p0 + 0.02, x + w + 0.2, p0 + 0.09, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.008)
        ops.line([(x + w + 0.07, p0 + 0.065), (x + w + 0.17, p0 + 0.065)], fill=alpha(hexc("#3b3630"), 170), width=0.008)
        ops.line([(x + w + 0.07, p0 + 0.04), (x + w + 0.14, p0 + 0.04)], fill=alpha(hexc("#3b3630"), 140), width=0.006)


def wall_pipe(ops, a, b, y, r=0.035, col=None, brackets=0.8):
    """Rohrleitung auf einer Stirnseite: Umriss, Lichtkante, Schellen."""
    col = col or lift("#7b8288", 1.3)
    ops.rect(a, y - r, b, y + r, fill=col, outline=OUTLINE, width=0.015)
    ops.line([(a, y + r * 0.45), (b, y + r * 0.45)], fill=shade(col, 1.3), width=0.014)
    xx = a + 0.3
    while xx < b - 0.1:
        ops.rect(xx - 0.03, y - r - 0.015, xx + 0.03, y + r + 0.015, fill=hexc("#3b4046"), outline=OUTLINE, width=0.01)
        xx += brackets


def wall_gauge(ops, x, y, r=0.07):
    ops.ellipse(x, y, r, r, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.018)
    ops.ellipse(x, y, r * 0.75, r * 0.75, outline=alpha(hexc("#3b3630"), 120), width=0.008)
    ops.line([(x, y), (x + r * 0.5, y + r * 0.45)], fill=hexc("#d33a2a"), width=0.014)
    ops.ellipse(x, y, r * 0.12, r * 0.12, fill=hexc("#3b3630"))


def wall_valve(ops, x, y, r=0.08):
    ops.ellipse(x, y, r, r, outline=OUTLINE, width=0.045)
    ops.ellipse(x, y, r, r, outline=hexc("#d33a2a"), width=0.028)
    for a in range(0, 180, 60):
        ca, sa = math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r
        ops.line([(x - ca, y - sa), (x + ca, y + sa)], fill=hexc("#d33a2a"), width=0.018)
    ops.ellipse(x, y, r * 0.22, r * 0.22, fill=hexc("#3b4046"), outline=OUTLINE, width=0.01)


def face_decor(ops, owner, x0, y0, x1, y1, fh, wall):
    if abs(y1 - y0) > 0.01:
        return  # nur waagerechte Stirnseiten bekommen Deko
    a, b = sorted((x0, x1))
    y = y0
    if owner == "galerie":
        # Stilblatt: gerahmte Gemaelde mit erkennbaren Motiven, dazwischen Bilderleuchten; die Stirnseite
        # ist nur 0,5 m hoch (Innenwand), die Bilder nutzen 0,34 m davon. Voller Pass: Schild je Bild.
        rnd = random.Random(int(a * 10))
        x = a + 0.55
        k = 0
        while x + 0.5 < b - 0.3:
            motif = MOTIFS[(k + int(a)) % len(MOTIFS)]
            w = 0.5 if motif != "crew" else 0.38
            p0, p1 = y + 0.09, y + min(fh - 0.06, 0.43)
            wall_poster(ops, x, p0, w, p1, motif, rnd, label=True)
            x += w + 0.45
            k += 1
    elif owner == "aegypten":
        ops.rect(a, y + 0.22, b, y + 0.36, fill=hexc("#b8843a"))
        x = a + 0.15
        i = 0
        while x < b - 0.1:
            if i % 3 == 0:
                ops.ellipse(x, y + 0.29, 0.04, 0.05, fill=hexc("#3f2e1c"))
            elif i % 3 == 1:
                ops.rect(x - 0.02, y + 0.24, x + 0.02, y + 0.34, fill=hexc("#3f2e1c"))
            else:
                ops.poly([(x - 0.05, y + 0.24), (x + 0.05, y + 0.24), (x, y + 0.34)], fill=hexc("#2f4f8a"))
            x += 0.18; i += 1
        # Papyrus-Bilder ueber dem Fries (nur an Aussenwaenden mit genug Hoehe), dazu eine Tafel
        if fh > 0.75:
            rnd = random.Random(int(a * 5))
            x = a + 0.6
            while x + 0.55 < b - 0.3:
                wall_poster(ops, x, y + 0.42, 0.55, y + fh - 0.1, "papyrus", rnd, label=False)
                x += 1.6
            plaque(ops, b - 0.75, y + 0.44, b - 0.25, y + 0.62, "DYNASTY", brass=False, lines=1, size=0.055)
    elif owner == "technikhalle" or owner == "hof":
        # Ziegelsockel
        yy = y + 0.08
        r = 0
        while yy < y + 0.3:
            xx = a + (0.12 if r % 2 else 0)
            while xx < b:
                ops.rect(xx, yy, min(b, xx + 0.24), yy + 0.1, fill=lift("#6e4a3a", 1.5), outline=lift("#7d7568", 1.3), width=0.012)
                xx += 0.24
            yy += 0.1; r += 1
        if owner == "technikhalle" and b - a > 0.8:
            # Dampfleitung mit Schellen, Ventilrad und Manometer ueber dem Sockel; an hohen Aussenwaenden eine
            # Blaupause im Rahmen und ein Schild mit der Hallennummer
            py = y + min(fh - 0.09, 0.405)
            wall_pipe(ops, a, b, py, r=0.035)
            if b - a > 2.0:
                wall_valve(ops, a + (b - a) * 0.3, py, r=0.07)
                wall_gauge(ops, a + (b - a) * 0.72, py + 0.01, r=0.06)
            if fh > 0.75:
                rnd = random.Random(int(a * 3))
                x = a + 0.5
                while x + 0.6 < b - 0.3:
                    wall_poster(ops, x, y + 0.52, 0.6, y + fh - 0.1, "blaupause", rnd, label=False)
                    x += 1.8
                if b - a > 1.5:
                    plaque(ops, b - 0.65, y + 0.56, b - 0.2, y + 0.74, "HALL 3", brass=False, lines=0, size=0.07)
        elif owner == "hof" and fh > 0.75:
            # Hof: Rohr, Nummernschild der Laderampe (nur am langen Wandstueck, sonst doppelt)
            wall_pipe(ops, a, b, y + 0.42, r=0.03, col=lift("#5a6068", 1.3))
            if b - a > 4.0:
                plaque(ops, a + 0.3, y + 0.55, a + 0.95, y + 0.75, "DOCK 1", brass=False, lines=0, size=0.07)
    elif owner == "werkstatt":
        # Lochwand mit Werkzeug-Silhouetten, Feuerloescher, Erste-Hilfe-Kasten
        ops.rect(a + 0.1, y + 0.1, b - 0.1, y + fh - 0.06, fill=lift("#8a8f93", 1.2), outline=OUTLINE, width=0.012)
        rnd = random.Random(int(a * 17))
        xx = a + 0.2
        while xx < b - 0.25:
            for py in (y + 0.16, y + 0.26, y + 0.36):
                if py < y + fh - 0.1:
                    ops.ellipse(xx, py, 0.008, 0.008, fill=shade(lift("#8a8f93", 1.2), 0.7))
            xx += 0.1
        tools = ["hammer", "zange", "saege", "schluessel", "pinsel"]
        xx = a + 0.3
        k = 0
        while xx + 0.2 < b - 0.5:
            t = tools[(k + int(a)) % len(tools)]
            t0, t1 = y + 0.13, y + min(fh - 0.1, 0.4)
            mid = (t0 + t1) / 2
            if t == "hammer":
                ops.line([(xx + 0.08, t0), (xx + 0.08, t1 - 0.04)], fill=hexc("#6b4a2e"), width=0.025)
                ops.rect(xx + 0.01, t1 - 0.08, xx + 0.15, t1 - 0.02, fill=hexc("#5a6068"), outline=OUTLINE, width=0.01)
            elif t == "zange":
                ops.line([(xx + 0.04, t0), (xx + 0.08, mid), (xx + 0.05, t1)], fill=hexc("#d33a2a"), width=0.022)
                ops.line([(xx + 0.12, t0), (xx + 0.08, mid), (xx + 0.11, t1)], fill=hexc("#d33a2a"), width=0.022)
                ops.line([(xx + 0.05, t1), (xx + 0.11, t1)], fill=hexc("#5a6068"), width=0.012)
            elif t == "saege":
                ops.poly([(xx, t1 - 0.02), (xx + 0.2, t1 - 0.02), (xx + 0.2, mid), (xx, mid + 0.03)], fill=hexc("#c0c8cc"), outline=OUTLINE, width=0.01)
                ops.rect(xx + 0.14, t0, xx + 0.2, mid, fill=hexc("#6b4a2e"), outline=OUTLINE, width=0.01)
            elif t == "schluessel":
                ops.line([(xx + 0.03, t0 + 0.02), (xx + 0.13, t1 - 0.03)], fill=OUTLINE, width=0.035)
                ops.line([(xx + 0.03, t0 + 0.02), (xx + 0.13, t1 - 0.03)], fill=hexc("#c0c8cc"), width=0.02)
                ops.ellipse(xx + 0.13, t1 - 0.03, 0.03, 0.03, fill=hexc("#c0c8cc"), outline=OUTLINE, width=0.01)
            else:
                ops.line([(xx + 0.08, t0), (xx + 0.08, mid + 0.02)], fill=hexc("#6b4a2e"), width=0.02)
                ops.rect(xx + 0.05, mid + 0.02, xx + 0.11, t1 - 0.02, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.01)
            xx += 0.32 if t == "saege" else 0.24
            k += 1
        # Feuerloescher und Erste-Hilfe-Kasten am Ostende
        ops.rect(b - 0.42, y + 0.09, b - 0.3, y + 0.33, fill=hexc("#d33a2a"), outline=OUTLINE, width=0.012)
        ops.rect(b - 0.4, y + 0.33, b - 0.32, y + 0.37, fill=hexc("#3b4046"))
        ops.line([(b - 0.4, y + 0.12), (b - 0.4, y + 0.3)], fill=alpha((255, 255, 255, 255), 90), width=0.012)
        ops.rect(b - 0.27, y + 0.18, b - 0.13, y + 0.32, fill=hexc("#f0f0ea"), outline=OUTLINE, width=0.012)
        ops.rect(b - 0.215, y + 0.21, b - 0.185, y + 0.29, fill=hexc("#d33a2a"))
        ops.rect(b - 0.24, y + 0.235, b - 0.16, y + 0.265, fill=hexc("#d33a2a"))
    elif owner == "shop":
        xx = a
        while xx < b:
            ops.line([(xx, y + 0.08), (xx, y + 0.3)], fill=shade(wall, 0.85), width=0.012)
            xx += 0.2
        ops.line([(a, y + 0.3), (b, y + 0.3)], fill=shade(wall, 0.85), width=0.015)
    elif owner == "telefon" or owner == "foyer":
        xx = a + 0.5
        while xx < b:
            ops.line([(xx, y + 0.1), (xx, y + fh - 0.06)], fill=shade(wall, 0.8), width=0.015)
            xx += 1.0
        # Plakate (Foyer: Saurier-Ausstellung, Telefon: Siebziger-Plakat) und Wanduhr in der Zentrale
        rnd = random.Random(int(a * 9 + y))
        x = a + 0.7
        k = 0
        while x + 0.42 < b - 0.4:
            motif = "saurier" if owner == "foyer" else ("plakat" if k % 2 == 0 else "crew")
            wall_poster(ops, x, y + 0.1, 0.42, y + min(fh - 0.07, 0.44), motif, rnd, label=False)
            x += 2.2
            k += 1
        if owner == "telefon" and b - a > 1.5:
            cx_ = b - 0.4
            ops.ellipse(cx_, y + 0.3, 0.1, 0.1, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.018)
            ops.line([(cx_, y + 0.3), (cx_, y + 0.37)], fill=hexc("#3b3630"), width=0.012)
            ops.line([(cx_, y + 0.3), (cx_ + 0.05, y + 0.28)], fill=hexc("#3b3630"), width=0.012)
        if owner == "foyer" and b - a > 2.5:
            plaque(ops, a + 0.15, y + 0.12, a + 0.55, y + 0.4, "INFO", brass=False, lines=3, size=0.06)
    elif owner == "planetarium":
        rnd = random.Random(99)
        for _ in range(int((b - a) * 3)):
            ops.ellipse(rnd.uniform(a, b), y + rnd.uniform(0.12, 0.42), 0.012, 0.012, fill=hexc("#cfe0ff"))
        x = a + 0.6
        while x + 0.5 < b - 0.4:
            wall_poster(ops, x, y + 0.1, 0.5, y + min(fh - 0.07, 0.44), "sternbild", rnd, label=True)
            x += 1.9
    elif owner == "rotunde":
        # Marmorfelder mit Messingrahmen auf der Bespannung, jedes zweite Feld ein Gemaelde
        brass = lift("#b08a3c", 1.2)
        marble = shade(wall, 1.1)
        rnd = random.Random(int(a * 4))
        xx = a + 0.15
        k = 0
        while xx + 0.5 < b - 0.1:
            w = min(0.7, b - 0.1 - xx)
            p0, p1 = y + 0.12, y + max(0.3, fh - 0.1)
            if k % 2 == 0 and w >= 0.5:
                wall_poster(ops, xx + 0.08, p0 + 0.02, w - 0.16, p1 - 0.04, ["saurier", "berg", "schiff"][(k + int(abs(a))) % 3], rnd, label=False)
            else:
                ops.rect(xx, p0, xx + w, p1, fill=marble, outline=brass, width=0.02)
                ops.line([(xx + 0.1, p0 + 0.04), (xx + w - 0.15, p1 - 0.05)], fill=alpha(shade(marble, 0.85), 160), width=0.015)
            xx += w + 0.12
            k += 1
    elif owner == "mineralien":
        # Schatzkammer (User 24.10.): die ganze Rueckwand ist ein Tresorgitter (Eisenstaebe mit Querband, dahinter
        # dunkel mit Goldschimmer: Truhen, Muenzhaufen, Kelche), in der Mitte eine runde Panzertuer in voller
        # Wandhoehe mit Bolzenkranz, Dreispeichenrad und Zahlenschloss, daneben zwei Wandleuchter.
        steel = hexc("#4a5058")
        brass = hexc("#c9a24a")
        gold = hexc("#e2b84a")
        mid = (a + b) / 2
        n0, n1 = y + 0.06, y + fh - 0.04
        hh = n1 - n0
        cyy = (n0 + n1) / 2
        rr = hh * 0.5 - 0.02
        door_w = rr + 0.16
        rs = random.Random(int(a * 13))
        # Kaefig: dunkler Hintergrund, Goldschimmer, Staebe, Querband, Rahmen
        ops.rect(a + 0.08, n0, b - 0.08, n1, fill=hexc("#17130f"), outline=OUTLINE, width=0.02)
        for k in range(int((b - a) / 1.3)):
            gx = a + 0.6 + k * 1.3
            if abs(gx - mid) < door_w + 0.5:
                continue
            ops.glow(gx, cyy - 0.1, 0.5, hexc("#ffd060"), 0.35)
            kind_ = rs.randrange(3)
            if kind_ == 0:                                                      # Truhe mit offenem Deckel
                ops.rect(gx - 0.22, n0 + 0.08, gx + 0.22, n0 + 0.32, fill=hexc("#6b4a2e"), outline=OUTLINE, width=0.012)
                ops.rect(gx - 0.22, n0 + 0.3, gx + 0.22, n0 + 0.34, fill=brass)
                ops.ellipse(gx, n0 + 0.36, 0.17, 0.06, fill=gold, outline=OUTLINE, width=0.01)
            elif kind_ == 1:                                                    # Muenzhaufen
                ops.ellipse(gx, n0 + 0.14, 0.3, 0.1, fill=gold, outline=OUTLINE, width=0.012)
                ops.ellipse(gx - 0.05, n0 + 0.22, 0.17, 0.07, fill=shade(gold, 1.1), outline=OUTLINE, width=0.01)
                for _ in range(5):
                    ops.ellipse(gx + rs.uniform(-0.25, 0.25), n0 + rs.uniform(0.08, 0.2), 0.035, 0.018, fill=shade(gold, 0.8))
            else:                                                               # Kelche und Barren
                for dx in (-0.15, 0.12):
                    ops.rect(gx + dx - 0.015, n0 + 0.12, gx + dx + 0.015, n0 + 0.28, fill=gold, outline=OUTLINE, width=0.01)
                    ops.ellipse(gx + dx, n0 + 0.3, 0.06, 0.03, fill=shade(gold, 1.15), outline=OUTLINE, width=0.01)
                    ops.ellipse(gx + dx, n0 + 0.1, 0.05, 0.02, fill=gold, outline=OUTLINE, width=0.01)
                ops.rect(gx - 0.04, n0 + 0.08, gx + 0.06, n0 + 0.16, fill=gold, outline=OUTLINE, width=0.01)
        for k in range(int((b - a - 0.4) / 0.22) + 1):
            bx = a + 0.2 + k * 0.22
            if abs(bx - mid) < door_w + 0.1:
                continue
            ops.line([(bx, n0), (bx, n1)], fill=OUTLINE, width=0.06)
            ops.line([(bx, n0), (bx, n1)], fill=steel, width=0.034)
            ops.line([(bx - 0.008, n0 + 0.02), (bx - 0.008, n1 - 0.02)], fill=shade(steel, 1.35), width=0.008)
        for by in (cyy, n0 + 0.1, n1 - 0.1):
            ops.rect(a + 0.08, by - 0.035, b - 0.08, by + 0.035, fill=shade(steel, 0.85), outline=OUTLINE, width=0.015)
        # Panzertuer: Rahmen, Ring, Blatt, Bolzen, Rad, Schloss, Scharniere
        ops.rect(mid - door_w, n0, mid + door_w, n1, fill=shade(steel, 0.75), outline=OUTLINE, width=0.025)
        for k in range(6):
            ops.ellipse(mid - door_w + 0.06, n0 + 0.08 + k * (hh - 0.16) / 5, 0.02, 0.02, fill=shade(steel, 1.4))
            ops.ellipse(mid + door_w - 0.06, n0 + 0.08 + k * (hh - 0.16) / 5, 0.02, 0.02, fill=shade(steel, 1.4))
        ops.ellipse(mid, cyy, rr, rr, fill=shade(steel, 0.6), outline=OUTLINE, width=0.03)
        ops.ellipse(mid, cyy, rr - 0.06, rr - 0.06, fill=steel, outline=OUTLINE, width=0.02)
        ops.ellipse(mid, cyy, rr - 0.13, rr - 0.13, fill=shade(steel, 1.12), outline=shade(steel, 0.6), width=0.012)
        ops.ellipse(mid - rr * 0.35, cyy + rr * 0.35, rr * 0.2, rr * 0.1, fill=alpha((255, 255, 255, 255), 50))
        for k in range(12):
            ang = k / 12 * 2 * math.pi
            ops.ellipse(mid + (rr - 0.095) * math.cos(ang), cyy + (rr - 0.095) * math.sin(ang), 0.025, 0.025, fill=shade(steel, 1.4), outline=OUTLINE, width=0.01)
        for ang in (90, 210, 330):
            q = (mid + rr * 0.5 * math.cos(math.radians(ang)), cyy + rr * 0.5 * math.sin(math.radians(ang)))
            ops.line([(mid, cyy), q], fill=OUTLINE, width=0.065)
            ops.line([(mid, cyy), q], fill=brass, width=0.038)
            ops.ellipse(q[0], q[1], 0.035, 0.035, fill=brass, outline=OUTLINE, width=0.012)
        ops.ellipse(mid, cyy, 0.06, 0.06, fill=shade(brass, 0.85), outline=OUTLINE, width=0.015)
        dq = (mid - rr * 0.6, cyy - rr * 0.1)
        ops.ellipse(dq[0], dq[1], 0.07, 0.07, fill=brass, outline=OUTLINE, width=0.015)
        ops.ellipse(dq[0], dq[1], 0.045, 0.045, fill=hexc("#1e2226"))
        ops.line([(dq[0], dq[1]), (dq[0] + 0.03, dq[1] + 0.025)], fill=brass, width=0.01)
        for hy in (cyy + rr * 0.55, cyy - rr * 0.55):
            ops.rect(mid + rr - 0.02, hy - 0.05, mid + rr + 0.14, hy + 0.05, fill=shade(steel, 1.2), outline=OUTLINE, width=0.015)
        # Wandleuchter beidseits der Tuer
        for lx in (mid - door_w - 0.3, mid + door_w + 0.3):
            ops.line([(lx, cyy - 0.08), (lx, cyy + 0.12)], fill=OUTLINE, width=0.04)
            ops.line([(lx, cyy - 0.08), (lx, cyy + 0.12)], fill=brass, width=0.022)
            ops.ellipse(lx, cyy + 0.18, 0.055, 0.075, fill=hexc("#ffe6a8"), outline=OUTLINE, width=0.012)
            ops.glow(lx, cyy + 0.18, 0.4, WARM, 0.5)
    elif owner is None and a > -22.1 and b < -8.4 and -17 < y < -16:
        # Suedgang West: Fensterband zum Lichthof (Rasen + Himmel im Glas)
        xx = max(a, -21.5) + 0.35
        while xx + 1.0 < b - 0.2:
            ops.rect(xx, y + 0.36, xx + 1.0, y + fh - 0.1, fill=hexc("#8a9398"), outline=OUTLINE, width=0.025)
            ops.rect(xx + 0.06, y + 0.4, xx + 0.94, y + fh - 0.14, fill=hexc("#3f6b45"))
            ops.rect(xx + 0.06, y + 0.62, xx + 0.94, y + fh - 0.14, fill=hexc("#4f7f8f"))
            ops.line([(xx + 0.5, y + 0.4), (xx + 0.5, y + fh - 0.14)], fill=hexc("#8a9398"), width=0.03)
            ops.line([(xx + 0.12, y + 0.46), (xx + 0.3, y + fh - 0.2)], fill=alpha((255, 255, 255, 255), 90), width=0.025)
            xx += 1.5
    elif owner is None:
        # andere Gaenge: Ausstellungsplakate in Rahmen
        rnd = random.Random(int(a * 7 + y))
        xx = a + 0.8
        while xx + 0.6 < b - 0.4:
            col = rnd.choice([hexc("#8e2f2f"), hexc("#2f4f8a"), hexc("#3f6b45"), hexc("#b0603a")])
            p0, p1 = y + max(0.12, fh - 0.57), y + fh - 0.12
            ops.rect(xx, p0, xx + 0.5, p1, fill=hexc("#2a2422"), outline=OUTLINE, width=0.02)
            ops.rect(xx + 0.04, p0 + 0.04, xx + 0.46, p1 - 0.04, fill=col)
            ops.rect(xx + 0.1, p0 + 0.08, xx + 0.4, p0 + 0.13, fill=hexc("#efe4c8"))
            ops.ellipse(xx + 0.25, (p0 + p1) / 2 + 0.06, 0.1, 0.07, fill=hexc("#efe4c8"))
            xx += 2.4
    elif owner == "haustechnik":
        # zwei Rohrleitungen mit Schellen + Kabeltrasse
        for py, col in ((y + fh * 0.5, lift("#7b8288", 1.3)), (y + fh * 0.74, lift("#8a2a2a", 1.5))):
            ops.rect(a, py - 0.045, b, py + 0.045, fill=col, outline=OUTLINE, width=0.015)
            ops.line([(a, py + 0.02), (b, py + 0.02)], fill=shade(col, 1.25), width=0.015)
            xx = a + 0.4
            while xx < b - 0.1:
                ops.rect(xx - 0.03, py - 0.06, xx + 0.03, py + 0.06, fill=hexc("#3b4046"))
                xx += 0.8
        ops.rect(a, y + fh - 0.07, b, y + fh - 0.02, fill=hexc("#2a2f35"))
        hz = y + 0.1
        xx = a
        while xx < b:
            ops.poly([(xx, hz), (min(b, xx + 0.1), hz), (min(b, xx + 0.2), hz + 0.08), (min(b, xx + 0.1), hz + 0.08)], fill=hexc("#d4b13c"))
            xx += 0.2
        if b - a > 2.0:
            wall_gauge(ops, a + (b - a) * 0.5, y + fh * 0.5 + 0.11, r=0.06)
            wall_valve(ops, a + (b - a) * 0.25, y + fh * 0.74, r=0.07)
    elif owner == "sicherheit":
        # Bildschirmleiste (Kamerabilder) + blaues Lichtband
        ops.rect(a, y + fh - 0.07, b, y + fh - 0.02, fill=hexc("#5f9bd0"))
        m0, m1 = y + fh * 0.3, y + fh - 0.11
        xx = a + 0.3
        while xx + 0.4 < b - 0.1:
            ops.rect(xx, m0, xx + 0.4, m1, fill=hexc("#1e2226"), outline=OUTLINE, width=0.02)
            ops.rect(xx + 0.04, m0 + 0.04, xx + 0.36, m1 - 0.04, fill=hexc("#8fb8c8"))
            ops.ellipse(xx + 0.2, (m0 + m1) / 2, 0.04, 0.04, fill=hexc("#4a5a60"))
            xx += 0.6
    elif owner == "depot":
        xx = a
        while xx < b:
            ops.rect(xx, y + 0.08, min(b, xx + 1.2), y + fh - 0.05, outline=shade(wall, 0.8), width=0.012)
            ops.ellipse(xx + 0.3, y + 0.28, 0.02, 0.02, fill=shade(wall, 0.6))
            xx += 1.2


def exit_signs(ops):
    """Gruene Notausgangsschilder: ueber jeder Oeffnung auf der Wandkrone (Stilbuch: drittes Licht)."""
    for _kind, poly in L.OPENINGS:
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if (x1 - x0) >= (y1 - y0):   # waagerechte Wand: Schild rechts neben der Oeffnung auf der Krone
            cx, cy = x1 + 0.35, (y0 + y1) / 2 + 0.05
        else:                        # senkrechte Wand: Schild oberhalb der Oeffnung
            cx, cy = (x0 + x1) / 2, y1 + 0.3
        ops.glow(cx, cy - 0.2, 0.9, NOTGRUEN, 0.25)
        ops.rect(cx - 0.17, cy - 0.09, cx + 0.17, cy + 0.09, fill=NOTGRUEN, outline=OUTLINE, width=0.025)
        ops.rect(cx - 0.12, cy - 0.05, cx - 0.04, cy + 0.05, fill=(255, 255, 255, 255))
        ops.poly([(cx - 0.02, cy - 0.04), (cx + 0.1, cy), (cx - 0.02, cy + 0.04)], fill=(255, 255, 255, 255))


def thresholds(ops):
    for kind, poly in L.OPENINGS:
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        col = hexc("#7b8288") if kind == "door" else hexc("#8c8474")
        ops.rect(x0, y0, x1, y1, fill=col)
        if kind == "door":
            if (x1 - x0) >= (y1 - y0):
                ops.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], fill=hexc("#3b4046"), width=0.05)
            else:
                ops.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=hexc("#3b4046"), width=0.05)


def build_floor_ops(walk):
    ops = OpList()
    rooms = room_polys()
    solid = sbox(L.BOUNDS[0], L.BOUNDS[1], L.BOUNDS[2], L.BOUNDS[3]).difference(walk)

    # Gebaeude-Grundflaeche (Wandkrone): folgt seit der Verkleinerung dem Grundriss (Aussenwand
    # WALL_OUT dick); eingeschlossene Luecken zwischen Raeumen werden Wandmasse, der Rest bleibt VOID.
    # Teilflaechen weiter als 2 x WALL_OUT auseinander ergeben ein MultiPolygon (ohne .exterior).
    crown = walk.buffer(WALL_OUT, join_style=2)
    building = Polygon(crown.exterior) if crown.geom_type == "Polygon" else unary_union([Polygon(g.exterior) for g in crown.geoms])
    ops.geom(building, fill=WALL_TOP)
    if L.DECOR:
        decor_outside(ops)

    # Gaenge
    for _k, poly in L.CORRIDORS:
        g = Polygon(poly)
        ops.geom(g, fill=lift(GANG_FLOOR, 1.25))
        x0, y0, x1, y1 = g.bounds
        seam = lift("#3a4050", 1.1)
        edge = alpha(lift("#8a94a4", 1.2), 200)
        if x1 - x0 > y1 - y0:
            my = (y0 + y1) / 2
            xx = x0 + 1.0
            while xx < x1 - 0.1:
                ops.line([(xx, y0), (xx, y1)], fill=seam, width=0.025)
                xx += 1.0
            ops.rect(x0, my - 0.45, x1, my + 0.45, fill=lift("#3a4050", 1.35))
            for yy in (my - 0.38, my + 0.38):
                ops.line([(x0, yy), (x1, yy)], fill=edge, width=0.03)
            for xx in range(int(x0) + 1, int(x1), 2):
                ops.glow(xx + 0.5, my, 0.9, hexc("#8f9fb4"), 0.22)
        else:
            mx = (x0 + x1) / 2
            yy = y0 + 1.0
            while yy < y1 - 0.1:
                ops.line([(x0, yy), (x1, yy)], fill=seam, width=0.025)
                yy += 1.0
            ops.rect(mx - 0.45, y0, mx + 0.45, y1, fill=lift("#3a4050", 1.35))
            for xx in (mx - 0.38, mx + 0.38):
                ops.line([(xx, y0), (xx, y1)], fill=edge, width=0.03)
    thresholds(ops)

    for style, poly, (dx, dy) in L.ROOM_ART:
        world = unary_union([Polygon(p) for p, _c in L.HOF_FLOORS]) if style == "hof" else Polygon(poly)
        ops.begin_room(world, dx, dy)
        floor_room(ops, style, translate(world, -dx, -dy))
        ops.end_room()

    crown_rim(ops, walk, building)
    wall_faces(ops, walk, rooms, L.CORRIDORS)

    # Kronenkante: Umriss entlang aller Raumkanten mit minimalem Zittern (Stilblatt: ca. 1 px), damit die
    # Wandkrone handgezeichnet wirkt; die Kollider bleiben die geraden Kanten (Abweichung 6 mm)
    k = 0
    for p in ([walk] if walk.geom_type == "Polygon" else list(walk.geoms)):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            wob = HD.wobble(ring, amp=0.006, seed=900 + k, step=0.1, closed=True)
            ops.line(wob + [wob[0]], fill=OUTLINE, width=0.09)
            k += 1
    for part in ([building] if building.geom_type == "Polygon" else list(building.geoms)):
        wob = HD.wobble(list(part.exterior.coords)[:-1], amp=0.008, seed=899, step=0.12, closed=True)
        ops.poly(wob, outline=OUTLINE, width=0.09)

    exit_signs(ops)
    return ops


# Abnutzung entlang der Laufwege (voller Pass): je Raum eine Spur von jeder Oeffnung zur Raummitte (oder zu
# einem festen Knoten), als weiche Ebene NACH dem Rendern. Helle Spuren = blank gelaufen (Metall, Parkett,
# Stein), dunkle Spuren = Schmutz (helle Boeden, Teppich).
WEAR_LIGHT = {"technikhalle", "sicherheit", "haustechnik", "planetarium", "mineralien", "depot", "hof", "galerie", "rotunde"}
WEAR_HUB = {"rotunde": (0.0, 1.6), "foyer": (0.0, -4.4), "planetarium": (-13.5, 11.8), "technikhalle": (8.4, 3.6),
            "galerie": (-11.0, 4.0), "aegypten": (-20.5, 2.0), "hof": (24.0, 4.5), "depot": (23.6, -3.5)}
GRAIN = 0.0           # Papierkorn (Stilblatt: 3 bis 5 %): Messung 01.10. bei JPEG q94: 3 % Korn (2 px) 4,5 -> 9,0 MB
                      # Kacheln (+80 %), 2 % mit 3-px-Korn bei q90 noch 6,0 MB; das 15-%-Budget der Bodenkacheln
                      # (Museum + Wald) laesst kein Korn zu, deshalb aus (Wert > 0 schaltet es wieder ein)


def wear_lanes(walk):
    """Rueckgabe: [(Punktliste in Weltmetern, hell?)] fuer alle Raeume, aus den Oeffnungen abgeleitet."""
    lanes = []
    openings = [Polygon(p) for _k, p in L.OPENINGS]
    seen = set()
    for key, name, _sys, poly, _c in L.ROOMS:
        style = L.ROOM_DEFS[key][2]
        g = unary_union([Polygon(p) for p, _c in L.HOF_FLOORS]) if key == "hof" else Polygon(poly)
        hub = WEAR_HUB.get(style, (g.representative_point().x, g.representative_point().y))
        light = style in WEAR_LIGHT
        for o in openings:
            if not o.buffer(0.05).intersects(g):
                continue
            c = o.centroid
            k = (round(c.x, 1), round(c.y, 1), key)
            if k in seen:
                continue
            seen.add(k)
            # Knick: erst senkrecht zur Oeffnung in den Raum, dann zum Knoten
            ox0, oy0, ox1, oy1 = o.bounds
            if ox1 - ox0 > oy1 - oy0:
                mid = (c.x, c.y + (1.2 if hub[1] > c.y else -1.2))
            else:
                mid = (c.x + (1.2 if hub[0] > c.x else -1.2), c.y)
            lanes.append(([(c.x, c.y), mid, hub], light))
    # Rotunde: Rundweg um das Podest
    ring = [(0.5 + 3.9 * math.cos(a * math.tau / 24), 4 + 2.1 * math.sin(a * math.tau / 24)) for a in range(25)]
    lanes.append((ring, True))
    # Gaenge: gerade durch
    for _k, poly in L.CORRIDORS:
        gx0, gy0, gx1, gy1 = Polygon(poly).bounds
        lanes.append(([(gx0, (gy0 + gy1) / 2), (gx1, (gy0 + gy1) / 2)], True))
    return lanes


def apply_wear(img, walk, x0, y0, x1, y1, lanes=None):
    """Weiche Abnutzungsspuren (lanes: [(Punkte, hell?)], Standard: wear_lanes des Museums) auf das fertige
    Bodenbild, nur innerhalb der begehbaren Flaeche. gen_wald nutzt dieselbe Ebene fuer die Huetten."""
    ppm = img.width / (x1 - x0)
    P = lambda x, y: ((x - x0) * ppm, (y1 - y) * ppm)
    layers = {True: Image.new("RGBA", img.size, (0, 0, 0, 0)), False: Image.new("RGBA", img.size, (0, 0, 0, 0))}
    draws = {k: ImageDraw.Draw(v, "RGBA") for k, v in layers.items()}
    rnd = random.Random(77)
    for i, (pts, light) in enumerate(lanes if lanes is not None else wear_lanes(walk)):
        wob = HD.wobble(pts, amp=0.12, seed=700 + i, step=0.4)
        col = (255, 240, 220, 34) if light else (20, 16, 12, 40)
        draws[light].line([P(*p) for p in wob], fill=col, width=int(1.3 * ppm), joint="curve")
        draws[light].line([P(*p) for p in wob], fill=col[:3] + (18,), width=int(0.6 * ppm), joint="curve")
        # Kratzer und Schlieren in Laufrichtung (kurze, feine Striche)
        ls = LineString(wob)
        for _ in range(int(ls.length * 2.5)):
            s = rnd.uniform(0, ls.length)
            p = ls.interpolate(s)
            q = ls.interpolate(min(ls.length, s + 0.3))
            dx, dy = q.x - p.x, q.y - p.y
            n = math.hypot(dx, dy) or 1.0
            off = rnd.uniform(-0.5, 0.5)
            a = (p.x - dy / n * off, p.y + dx / n * off)
            ln = rnd.uniform(0.08, 0.25)
            b = (a[0] + dx / n * ln, a[1] + dy / n * ln)
            draws[light].line([P(*a), P(*b)], fill=col[:3] + (rnd.randint(35, 70),), width=max(1, int(0.018 * ppm)))
    out = img.convert("RGBA")
    inside = walk_mask(walk, x0, y0, x1, y1, ppm, img.width, img.height)
    for light, layer in layers.items():
        layer = layer.filter(ImageFilter.GaussianBlur(0.22 * ppm))
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), inside))
        out.alpha_composite(layer)
    return out.convert("RGB")


def render_floor(walk, ppm):
    ops = build_floor_ops(walk)
    x0, y0, x1, y1 = L.BOUNDS
    img = ops.render(x0, y0, x1, y1, ppm, VOID)
    img = apply_wear(img, walk, x0, y0, x1, y1)
    img = ambient_occlusion(img, walk, x0, y0, x1, y1)
    return HD.paper_grain(img, GRAIN, seed=4, scale=2) if GRAIN else img


# ================================================================== Objekte

class Prop:
    """Ein Objekt-Sprite: Leinwand in Weltkoordinaten, Standlinie base_y (-> z-Sortierung)."""

    def __init__(self, x0, y0, x1, y1, h, ppm, base_y=None, pad=0.3):
        self.c = Canvas(x0 - pad, y0 - pad, x1 + pad, y1 + h * K + pad, ppm)
        self.base_y = y0 if base_y is None else base_y

    # --- Primitive in schraeger Aufsicht (z = Hoehe ueber Boden in m)
    def box(self, x0, y0, x1, y1, z0, h, top, front, ol=OUTLINE, w=OUT_W, glass=False):
        c = self.c
        fb, ft = y0 + z0 * K, y0 + (z0 + h) * K
        c.poly([(x0, fb), (x1, fb), (x1, ft), (x0, ft)], fill=front, outline=ol, width=w)
        c.poly([(x0, ft), (x1, ft), (x1, y1 + (z0 + h) * K), (x0, y1 + (z0 + h) * K)], fill=top, outline=ol, width=w)
        if not glass:
            # Schattenband unten an der Vorderseite (Kontakt zum Boden) + Lichtkante oben
            band = min((ft - fb) * 0.28, 0.14)
            if band > 0.02:
                c.rect(x0 + w * 0.5, fb + w * 0.5, x1 - w * 0.5, fb + band, fill=alpha((0, 0, 0, 255), 55))
            c.line([(x0 + w, ft - w * 0.8), (x1 - w, ft - w * 0.8)], fill=shade(front, 1.3), width=w * 0.6)
            # Deckflaeche: helle Hinterkante, dunkle Vorderkante
            tb = y1 + (z0 + h) * K
            c.line([(x0 + w, tb - w * 0.9), (x1 - w, tb - w * 0.9)], fill=shade(top, 1.18), width=w * 0.5)

    def cyl(self, cx, cy, r, z0, h, top, side, ol=OUTLINE, w=OUT_W, ry=None):
        c = self.c
        ry = r if ry is None else ry
        yb, yt = cy + z0 * K, cy + (z0 + h) * K
        c.ellipse(cx, yb, r, ry, fill=side, outline=ol, width=w)
        c.rect(cx - r, yb, cx + r, yt, fill=side)
        c.line([(cx - r, yb), (cx - r, yt)], fill=ol, width=w)
        c.line([(cx + r, yb), (cx + r, yt)], fill=ol, width=w)
        c.ellipse(cx, yt, r, ry, fill=top, outline=ol, width=w)

    def at(self, x, y, z=0):
        return (x, y + z * K)


def exhibit(p, kind, cx, cy, z, rnd):
    """Kleines Exponat auf Hoehe z (Vitrineninnenboden)."""
    c = p.c
    x, y = cx, cy + z * K
    if kind == "mineral":
        col = rnd.choice([hexc("#9d6cc7"), hexc("#e0b04a"), hexc("#d9e4ec"), hexc("#3f9e6e")])
        c.ellipse(x, y + 0.05, 0.22, 0.1, fill=hexc("#5a6068"), outline=OUTLINE, width=0.03)
        for dx, hh in ((-0.1, 0.28), (0.0, 0.4), (0.1, 0.3), (0.05, 0.22)):
            c.poly([(x + dx - 0.05, y + 0.05), (x + dx + 0.05, y + 0.05), (x + dx + 0.02, y + 0.05 + hh), (x + dx - 0.02, y + 0.05 + hh)],
                   fill=col, outline=OUTLINE, width=0.02)
            c.line([(x + dx - 0.02, y + 0.1), (x + dx - 0.01, y + hh - 0.02)], fill=shade(col, 1.35), width=0.015)
    elif kind == "urne":
        col = hexc("#b0603a")
        c.ellipse(x, y + 0.2, 0.17, 0.2, fill=col, outline=OUTLINE, width=0.03)
        c.rect(x - 0.08, y + 0.34, x + 0.08, y + 0.44, fill=col, outline=OUTLINE, width=0.025)
        c.line([(x - 0.14, y + 0.22), (x + 0.14, y + 0.22)], fill=hexc("#2a2422"), width=0.025)
    elif kind == "schaedel":
        c.ellipse(x, y + 0.2, 0.17, 0.15, fill=hexc("#d8cdb0"), outline=OUTLINE, width=0.03)
        c.rect(x - 0.09, y + 0.04, x + 0.09, y + 0.12, fill=hexc("#d8cdb0"), outline=OUTLINE, width=0.025)
        c.ellipse(x - 0.06, y + 0.19, 0.035, 0.04, fill=hexc("#2a2422"))
        c.ellipse(x + 0.06, y + 0.19, 0.035, 0.04, fill=hexc("#2a2422"))
    elif kind == "modell":
        c.rect(x - 0.22, y + 0.02, x + 0.22, y + 0.12, fill=hexc("#6b4a2e"), outline=OUTLINE, width=0.025)
        c.poly([(x - 0.15, y + 0.12), (x + 0.15, y + 0.12), (x, y + 0.45)], fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.025)
    elif kind == "papyrus":
        c.rect(x - 0.4, y + 0.02, x + 0.4, y + 0.22, fill=hexc("#d8c79a"), outline=OUTLINE, width=0.02)
        for i in range(6):
            c.line([(x - 0.33 + i * 0.12, y + 0.07), (x - 0.3 + i * 0.12, y + 0.17)], fill=hexc("#3f2e1c"), width=0.012)
    elif kind == "muenzen":
        c.ellipse(x, y + 0.1, 0.32, 0.14, fill=hexc("#5a2a2a"), outline=OUTLINE, width=0.02)
        for i in range(5):
            c.ellipse(x - 0.24 + i * 0.12, y + 0.1 + (i % 2) * 0.05, 0.05, 0.04, fill=hexc("#d9b25c"), outline=OUTLINE, width=0.015)
            c.ellipse(x - 0.24 + i * 0.12, y + 0.1 + (i % 2) * 0.05, 0.025, 0.02, outline=shade(hexc("#d9b25c"), 0.75), width=0.01)
    elif kind == "amphore":
        col = hexc("#b0603a")
        c.ellipse(x, y + 0.08, 0.1, 0.04, fill=hexc("#5a6068"), outline=OUTLINE, width=0.02)
        c.poly([(x - 0.07, y + 0.1), (x + 0.07, y + 0.1), (x + 0.17, y + 0.3), (x + 0.12, y + 0.45), (x - 0.12, y + 0.45), (x - 0.17, y + 0.3)],
               fill=col, outline=OUTLINE, width=0.025)
        c.rect(x - 0.08, y + 0.45, x + 0.08, y + 0.52, fill=col, outline=OUTLINE, width=0.02)
        for sx in (-1, 1):
            c.line([(x + sx * 0.12, y + 0.44), (x + sx * 0.22, y + 0.38), (x + sx * 0.16, y + 0.3)], fill=OUTLINE, width=0.05)
            c.line([(x + sx * 0.12, y + 0.44), (x + sx * 0.22, y + 0.38), (x + sx * 0.16, y + 0.3)], fill=col, width=0.025)
        c.line([(x - 0.13, y + 0.3), (x + 0.13, y + 0.3)], fill=hexc("#2a2422"), width=0.03)
        c.line([(x - 0.1, y + 0.36), (x + 0.1, y + 0.36)], fill=hexc("#2a2422"), width=0.015)
        c.line([(x - 0.1, y + 0.16), (x - 0.06, y + 0.4)], fill=(255, 255, 255, 70), width=0.02)
    elif kind == "fossil":
        slab = hexc("#8a8275")
        c.poly([(x - 0.32, y + 0.02), (x + 0.3, y + 0.04), (x + 0.34, y + 0.4), (x - 0.28, y + 0.42)], fill=slab, outline=OUTLINE, width=0.025)
        # Ammonit als Spirale
        pts = []
        for i in range(40):
            t = i / 39 * 4 * math.pi
            rr = 0.02 + 0.03 * t
            pts.append((x + rr * math.cos(t), y + 0.22 + rr * 0.8 * math.sin(t)))
        c.line(pts, fill=hexc("#3f3a34"), width=0.04)
        c.line(pts, fill=hexc("#c9b27a"), width=0.02)
    elif kind == "statue":
        col = hexc("#8fb0a4")
        c.rect(x - 0.12, y + 0.02, x + 0.12, y + 0.1, fill=hexc("#5a6068"), outline=OUTLINE, width=0.02)
        c.poly([(x - 0.08, y + 0.1), (x + 0.08, y + 0.1), (x + 0.06, y + 0.38), (x - 0.06, y + 0.38)], fill=col, outline=OUTLINE, width=0.02)
        c.ellipse(x, y + 0.44, 0.06, 0.07, fill=col, outline=OUTLINE, width=0.02)
        c.line([(x - 0.06, y + 0.32), (x - 0.14, y + 0.2)], fill=OUTLINE, width=0.05)
        c.line([(x - 0.06, y + 0.32), (x - 0.14, y + 0.2)], fill=col, width=0.025)
        c.line([(x + 0.06, y + 0.32), (x + 0.12, y + 0.42)], fill=OUTLINE, width=0.05)
        c.line([(x + 0.06, y + 0.32), (x + 0.12, y + 0.42)], fill=col, width=0.025)
    elif kind == "kaefer":
        c.rect(x - 0.3, y + 0.02, x + 0.3, y + 0.34, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.02)
        for i, col in enumerate(("#3f9e6e", "#2f4f8a", "#b0603a", "#e0b04a")):
            bx = x - 0.21 + i * 0.14
            c.ellipse(bx, y + 0.18, 0.045, 0.07, fill=hexc(col), outline=OUTLINE, width=0.015)
            c.ellipse(bx, y + 0.26, 0.025, 0.02, fill=OUTLINE)
            c.line([(bx, y + 0.12), (bx, y + 0.24)], fill=OUTLINE, width=0.01)
    elif kind == "kristallstufe":
        # grosse Amethyst-Druse auf grauer Matrix (Schatzkammer)
        rock = hexc("#5a5c62")
        c.poly([(x - 0.36, y + 0.02), (x + 0.34, y + 0.03), (x + 0.3, y + 0.16), (x + 0.1, y + 0.2), (x - 0.15, y + 0.19), (x - 0.34, y + 0.14)],
               fill=rock, outline=OUTLINE, width=0.025)
        c.poly([(x - 0.3, y + 0.05), (x + 0.28, y + 0.06), (x + 0.2, y + 0.12), (x - 0.2, y + 0.12)], fill=shade(rock, 0.75))
        rs = random.Random(23)
        for dx, hh, w_ in ((-0.26, 0.22, 0.07), (-0.14, 0.34, 0.09), (-0.02, 0.44, 0.1), (0.1, 0.36, 0.09), (0.21, 0.26, 0.08), (0.28, 0.16, 0.06), (-0.08, 0.18, 0.06), (0.04, 0.2, 0.05)):
            col = shade(hexc("#9d6cc7"), rs.uniform(0.9, 1.1))
            c.poly([(x + dx - w_, y + 0.12), (x + dx + w_, y + 0.12), (x + dx + w_ * 0.6, y + 0.12 + hh * 0.8), (x + dx, y + 0.12 + hh), (x + dx - w_ * 0.6, y + 0.12 + hh * 0.8)],
                   fill=col, outline=OUTLINE, width=0.018)
            c.poly([(x + dx - w_ * 0.3, y + 0.14), (x + dx + w_ * 0.1, y + 0.14), (x + dx - w_ * 0.05, y + 0.12 + hh * 0.85), (x + dx - w_ * 0.35, y + 0.12 + hh * 0.7)], fill=shade(col, 1.35))
            c.line([(x + dx + w_ * 0.3, y + 0.16), (x + dx + w_ * 0.5, y + 0.12 + hh * 0.6)], fill=shade(col, 0.7), width=0.01)
        c.rect(x - 0.1, y + 0.0, x + 0.1, y + 0.04, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.008)
    elif kind == "edelsteine":
        # Tablett mit geschliffenen Steinen auf dunklem Samt (Schatzkammer)
        c.rect(x - 0.42, y + 0.02, x + 0.42, y + 0.3, fill=hexc("#c9a24a"), outline=OUTLINE, width=0.02)
        c.rect(x - 0.39, y + 0.045, x + 0.39, y + 0.275, fill=hexc("#2a1a30"))
        gems = (("#d02e3a", 0.0), ("#2e8a4e", 0.0), ("#2f5fb0", 0.0), ("#e8f4ff", 0.0), ("#e0b04a", 0.0), ("#9d6cc7", 0.0))
        for k_, (col, _o) in enumerate(gems):
            gx = x - 0.32 + k_ * 0.128
            gy = y + 0.16 + (0.03 if k_ % 2 else -0.02)
            col = hexc(col)
            if k_ % 3 == 0:       # Brillant (rund)
                c.ellipse(gx, gy, 0.058, 0.052, fill=col, outline=OUTLINE, width=0.012)
                c.poly([(gx - 0.035, gy), (gx, gy + 0.035), (gx + 0.035, gy), (gx, gy - 0.035)], fill=shade(col, 1.45))
                c.ellipse(gx - 0.015, gy + 0.015, 0.01, 0.008, fill=(255, 255, 255, 230))
            elif k_ % 3 == 1:     # Smaragdschliff (achteckig)
                c.poly([(gx - 0.05, gy - 0.025), (gx - 0.035, gy - 0.04), (gx + 0.035, gy - 0.04), (gx + 0.05, gy - 0.025), (gx + 0.05, gy + 0.025),
                        (gx + 0.035, gy + 0.04), (gx - 0.035, gy + 0.04), (gx - 0.05, gy + 0.025)], fill=col, outline=OUTLINE, width=0.012)
                c.rect(gx - 0.025, gy - 0.018, gx + 0.025, gy + 0.018, fill=shade(col, 1.4))
                c.line([(gx - 0.04, gy + 0.03), (gx + 0.02, gy + 0.03)], fill=(255, 255, 255, 160), width=0.006)
            else:                 # Tropfen
                c.poly([(gx - 0.04, gy), (gx - 0.02, gy + 0.045), (gx + 0.02, gy + 0.045), (gx + 0.04, gy), (gx, gy - 0.055)], fill=col, outline=OUTLINE, width=0.012)
                c.poly([(gx - 0.015, gy + 0.01), (gx + 0.015, gy + 0.01), (gx, gy - 0.03)], fill=shade(col, 1.45))
            c.glow(gx, gy, 0.09, col, 0.25)
        c.rect(x - 0.1, y - 0.0, x + 0.1, y + 0.03, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.008)


EXHIBITS_TALL = ["mineral", "urne", "schaedel", "modell", "amphore", "statue"]
EXHIBITS_FLAT = ["papyrus", "muenzen", "fossil", "kaefer"]


def draw_vitrine(p, x0, y0, x1, y1, rnd, ex=None, low=False, treasury=False):
    """Vitrine: dunkler Sockel mit Lichtleiste, beleuchteter Innenboden, Exponat, Glaskoerper mit
    Alu-Rahmen. Glas bleibt durchsichtig (nur Alpha), damit Spieler dahinter sichtbar bleiben."""
    c = p.c
    sockel = 0.6 if low else 0.8
    glass_h = 0.35 if low else 0.8
    wood = lift("#4a3222", 1.55)
    p.box(x0, y0, x1, y1, 0, sockel, shade(wood, 1.12), wood)
    # Sockelfront: Fussleiste, Tuerfuge, kleines Schild
    c.rect(x0 + 0.02, y0 + 0.02, x1 - 0.02, y0 + 0.08, fill=shade(wood, 0.6))
    c.line([((x0 + x1) / 2, y0 + 0.1), ((x0 + x1) / 2, y0 + sockel * K - 0.1)], fill=shade(wood, 0.72), width=0.015)
    c.rect((x0 + x1) / 2 - 0.12, y0 + sockel * K * 0.45, (x0 + x1) / 2 + 0.12, y0 + sockel * K * 0.45 + 0.07, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.012)
    # LED-Kante + Lichtschein auf dem Innenboden
    c.line([(x0 + 0.05, y0 + sockel * K - 0.03), (x1 - 0.05, y0 + sockel * K - 0.03)], fill=WARM, width=0.03)
    zt0 = sockel * K
    c.poly([(x0 + 0.03, y0 + zt0), (x1 - 0.03, y0 + zt0), (x1 - 0.03, y1 + zt0), (x0 + 0.03, y1 + zt0)],
           fill=lift("#5a1a26", 1.55) if treasury else lift("#d8cfb0", 1.05))
    c.glow((x0 + x1) / 2, (y0 + y1) / 2 + zt0 + 0.05, max(0.5, (x1 - x0) * 0.6), WARM, 0.5)
    # Exponat
    ex = ex or rnd.choice(EXHIBITS_TALL)
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2 - 0.05
    exhibit(p, ex, cx, cy, sockel, rnd)
    # Glaskoerper mit Alu-Kanten
    glass = alpha(hexc("#bfe3f5"), 62)
    glass_top = alpha(hexc("#dff3ff"), 88)
    p.box(x0 + 0.03, y0, x1 - 0.03, y1, sockel, glass_h, glass_top, glass, ol=alpha(hexc("#e9f7ff"), 235), w=0.03, glass=True)
    zt = sockel + glass_h
    alu = hexc("#c9a24a") if treasury else hexc("#c0c8cc")
    for ex_ in (x0 + 0.03, x1 - 0.03):
        c.line([(ex_, y0 + sockel * K), (ex_, y0 + zt * K)], fill=alu, width=0.025)
    c.line([(x0 + 0.03, y1 + zt * K), (x1 - 0.03, y1 + zt * K)], fill=alu, width=0.025)
    c.line([(x0 + 0.03, y0 + zt * K), (x1 - 0.03, y0 + zt * K)], fill=alu, width=0.025)
    # Glanz
    c.line([(x0 + 0.12, y0 + (sockel + 0.1) * K), (x0 + 0.3, y0 + (zt - 0.1) * K)], fill=alpha((255, 255, 255, 255), 150), width=0.03)
    c.line([(x0 + 0.34, y0 + (sockel + 0.1) * K), (x0 + 0.42, y0 + (sockel + 0.4) * K)], fill=alpha((255, 255, 255, 255), 90), width=0.02)


PROP_H = {
    "infotheke": 1.0, "kasse": 1.9, "treppe": 1.4, "garderobe": 1.8,
    "tresen_kasse": 1.0, "regal_shop": 1.8, "regal_insel": 1.5, "tresen_cafe": 1.0,
    "monitorwand": 2.0, "spind": 1.9, "schaltschrank": 2.0, "klima": 1.2, "kessel": 1.8,
    "sarkophag": 0.9, "stele": 1.7, "sphinx": 1.0, "stellwand": 2.2, "projektor": 1.9,
    "vermittlung": 2.0, "funkregal": 1.8, "stuetze": 3.0, "dampfmaschine": 3.6,
    "schwungrad": 2.1, "oldtimer": 1.3, "turbine": 2.6, "werktisch": 0.9, "regal_werk": 1.8,
    "hochregal": 2.4, "kiste": 0.9, "co2": 1.6, "lieferwagen": 2.3, "fass": 0.9,
    "vitrine": 1.6, "tischvitrine": 1.0, "tresorvitrine": 2.1, "bank": 0.45, "cafetisch": 0.75,
    "trog": 0.6, "admintisch": 0.9, "vermittlungstisch": 0.8, "glaswand": 2.0, "resttisch": 0.9,
    "dino": 1.6, "dino_rex": 6.2, "lampe": 5.0,
    # "Rex erwacht" (25.09.): Kopf und Unterkiefer als eigene Sprites (beweglich), zwei Stationen
    "dino_rex_head": 6.2, "dino_rex_jaw": 6.2, "spieluhr": 1.3, "nachtlicht": 1.3,
    # Stilblatt: Staffelei mit dem Portraet in der Galerie (Augen folgen spaeter per Code)
    "staffelei": 1.9,
}

# Portraet auf der Staffelei (Stilblatt): Augenmitten in Weltkoordinaten der Bildebene, Halbachsen des
# Augenweiss und der Pupille; wird beim Zeichnen gefuellt, gen_museum schreibt es in AtlasMuseumData
# und legt das Pupillen-Sprite ab (assets/task_museum_pupil.png, task_* wird eingebettet).
PORTRAIT_EYES = {}

# Objekte, deren Sprite auf den sichtbaren Inhalt zugeschnitten wird (gen_museum.render_props): Kopf und
# Kiefer liegen auf der vollen 13,6-m-Leinwand des Skeletts, belegen davon aber nur einen kleinen Teil.
CROP_KINDS = {"dino_rex_head", "dino_rex_jaw"}

# Gelenkpunkte des Rex in Weltmetern (beim Zeichnen des Kopfes gefuellt, gen_museum schreibt sie in
# AtlasMuseumData): Halsgelenk (Drehpunkt Kopf), Kiefergelenk, Augenhoehle (Leuchten).
REX_RIG = {}


def shape_bounds(shape):
    kind = shape[0]
    if kind == "rect":
        return shape[1:5]
    if kind == "ellipse":
        _, cx, cy, rx, ry = shape
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    _, cx, cy, r = shape
    return (cx - r, cy - r, cx + r, cy + r)


LEGGED = {"bank", "cafetisch", "admintisch", "vermittlungstisch", "resttisch"}


def draw_prop(kind, shape, idx, ppm):
    """Zeichnet ein Objekt. Rueckgabe: (Bild, Welt-x links, Welt-y unten, Standlinie)."""
    x0, y0, x1, y1 = shape_bounds(shape)
    h = PROP_H.get(kind, 1.0)
    rnd = random.Random(idx * 7919 + hash(kind) % 1000)
    extra_w = 0.0
    if kind == "dino":
        extra_w = 0.6
    if kind == "schwungrad":
        extra_w = 0.9        # Pleuel nach Westen, Treibriemen nach Osten zum Dynamo
    if kind in ("dino_rex", "dino_rex_head", "dino_rex_jaw"):
        # Skelett als eigenes Objekt ueber dem Sockel (User 25.09.: "ragt wirklich in den Raum"): die
        # Leinwand reicht links bis zur Schnauze, rechts bis zur Schwanzspitze (REX_* unten)
        extra_w = 3.8
    p = Prop(x0 - extra_w, y0, x1 + extra_w, y1, h, ppm)
    c = p.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if kind not in LEGGED and kind not in ("glaswand", "dino_rex", "dino_rex_head", "dino_rex_jaw"):
        # weicher Schlagschatten nach Suedost (Licht von Nordwest, wie in Among Us)
        if shape[0] in ("circle", "ellipse"):
            rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
            pts = [(cx + 0.07 + rx * math.cos(t * math.pi / 12), cy - 0.07 + ry * math.sin(t * math.pi / 12)) for t in range(24)]
        else:
            pts = [(x0 + 0.07, y0 - 0.1), (x1 + 0.1, y0 - 0.1), (x1 + 0.1, y1 - 0.05), (x0 + 0.07, y1 - 0.05)]
        c.soft_shadow(pts, 95, 0.07)
    if kind in LEGGED:
        # Bodenschatten in Kollisionsgroesse: unter Beinmoebeln sieht man sonst Boden, wo man
        # nicht hinkommt (Test 22.09.: "hier geht's nicht weiter hoch").
        if shape[0] in ("circle", "ellipse"):
            c.soft_shadow([(cx + (x1 - cx) * math.cos(t * math.pi / 12), cy + (y1 - cy) * math.sin(t * math.pi / 12)) for t in range(24)], 110, 0.06)
        else:
            c.soft_shadow([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 110, 0.06)

    if kind == "vitrine":
        draw_vitrine(p, x0, y0, x1, y1, rnd)
    elif kind == "tischvitrine":
        if y0 > 10:
            # Schatzkammer (Nordnische): feste Exponate statt Zufall (User 24.10.): links die grosse
            # Amethyst-Kristallstufe, rechts das Tablett mit geschliffenen Edelsteinen
            draw_vitrine(p, x0, y0, x1, y1, rnd, ex="kristallstufe" if cx < 0 else "edelsteine", low=True, treasury=True)
        else:
            draw_vitrine(p, x0, y0, x1, y1, rnd, ex=rnd.choice(EXHIBITS_FLAT), low=True)
    elif kind == "tresorvitrine":
        # Tresorvitrine der Schatzkammer (User 24.10.: "eindeutig als Schatzkammer erkennbar"): Panzersockel mit
        # Nietband, Zahlenschloss und Dreispeichengriff, darauf rotes Samttuch mit der Krone auf dem Kissen,
        # Goldmuenzen, Barren, Kelch und Kette; Glashaube mit Messingkanten und Spot.
        steel = lift("#3f454c", 1.55)
        brass = hexc("#c9a24a")
        gold = hexc("#e2b84a")
        gold_d = shade(gold, 0.72)
        gold_l = hexc("#fff0b0")
        velvet = lift("#5a1a26", 1.55)
        sock = 0.7
        p.box(x0, y0, x1, y1, 0, sock, shade(steel, 1.15), steel)
        fb = y0
        c.rect(x0 + 0.03, fb + 0.02, x1 - 0.03, fb + 0.1, fill=shade(steel, 0.65))
        c.rect(x0 + 0.08, fb + 0.1, x1 - 0.08, fb + sock * K - 0.05, fill=shade(steel, 0.92), outline=shade(steel, 0.6), width=0.015)
        for i in range(int((x1 - x0) / 0.18)):
            rx = x0 + 0.12 + i * 0.18
            c.ellipse(rx, fb + sock * K - 0.025, 0.016, 0.016, fill=shade(steel, 1.4))
            c.ellipse(rx, fb + 0.13, 0.016, 0.016, fill=shade(steel, 1.4))
        dial = (cx - 0.68, fb + sock * K * 0.5)
        c.ellipse(dial[0], dial[1], 0.11, 0.11, fill=brass, outline=OUTLINE, width=0.02)
        c.ellipse(dial[0], dial[1], 0.08, 0.08, fill=hexc("#1e2226"), outline=OUTLINE, width=0.012)
        for a in range(0, 360, 30):
            c.line([(dial[0] + 0.055 * math.cos(math.radians(a)), dial[1] + 0.055 * math.sin(math.radians(a))),
                    (dial[0] + 0.07 * math.cos(math.radians(a)), dial[1] + 0.07 * math.sin(math.radians(a)))], fill=brass, width=0.008)
        c.line([(dial[0], dial[1]), (dial[0] + 0.05, dial[1] + 0.04)], fill=brass, width=0.012)
        hub = (cx + 0.62, fb + sock * K * 0.5)
        for a in (90, 210, 330):
            c.line([hub, (hub[0] + 0.15 * math.cos(math.radians(a)), hub[1] + 0.15 * math.sin(math.radians(a)))], fill=OUTLINE, width=0.05)
            c.line([hub, (hub[0] + 0.15 * math.cos(math.radians(a)), hub[1] + 0.15 * math.sin(math.radians(a)))], fill=brass, width=0.028)
            c.ellipse(hub[0] + 0.15 * math.cos(math.radians(a)), hub[1] + 0.15 * math.sin(math.radians(a)), 0.03, 0.03, fill=brass, outline=OUTLINE, width=0.012)
        c.ellipse(hub[0], hub[1], 0.045, 0.045, fill=shade(brass, 0.8), outline=OUTLINE, width=0.015)
        c.rect(cx - 0.32, fb + sock * K * 0.5 - 0.07, cx + 0.32, fb + sock * K * 0.5 + 0.07, fill=brass, outline=OUTLINE, width=0.015)
        c.rect(cx - 0.29, fb + sock * K * 0.5 - 0.05, cx + 0.29, fb + sock * K * 0.5 + 0.05, outline=shade(brass, 0.7), width=0.008)
        c.text(cx, fb + sock * K * 0.5, "TREASURY", 0.075, hexc("#2a2422"))
        # Samtflaeche mit Faltensaum und Spot
        zt0 = sock * K
        c.poly([(x0 + 0.04, y0 + zt0), (x1 - 0.04, y0 + zt0), (x1 - 0.04, y1 + zt0), (x0 + 0.04, y1 + zt0)], fill=velvet)
        c.rect(x0 + 0.04, y0 + zt0, x1 - 0.04, y0 + zt0 + 0.07, fill=shade(velvet, 1.25))
        for k_ in range(6):
            c.line([(x0 + 0.2 + k_ * 0.3, y0 + zt0 + 0.02), (x0 + 0.24 + k_ * 0.3, y0 + zt0 + 0.07)], fill=shade(velvet, 0.75), width=0.012)
        c.glow(cx, cy + zt0 + 0.1, 1.2, WARM, 0.55)
        # Krone auf dem Kissen (Mitte, hinten)
        kx, ky = cx, cy + zt0 + 0.25
        c.ellipse(kx, ky - 0.05, 0.42, 0.2, fill=shade(velvet, 1.3), outline=OUTLINE, width=0.025)        # Kissen
        c.ellipse(kx, ky - 0.03, 0.34, 0.14, fill=shade(velvet, 1.5))
        for sx in (-1, 1):
            c.ellipse(kx + sx * 0.42, ky - 0.05, 0.04, 0.03, fill=gold, outline=OUTLINE, width=0.012)        # Quasten
        c.rect(kx - 0.3, ky - 0.02, kx + 0.3, ky + 0.2, fill=gold, outline=OUTLINE, width=0.028)            # Reif
        c.rect(kx - 0.3, ky - 0.02, kx + 0.3, ky + 0.03, fill=gold_d)
        c.line([(kx - 0.26, ky + 0.17), (kx + 0.26, ky + 0.17)], fill=gold_l, width=0.015)
        for k_, col in enumerate((hexc("#d02e3a"), hexc("#2e8a4e"), hexc("#2f5fb0"), hexc("#d02e3a"), hexc("#2e8a4e"))):
            gx = kx - 0.24 + k_ * 0.12
            c.ellipse(gx, ky + 0.09, 0.035, 0.045, fill=col, outline=OUTLINE, width=0.012)
            c.ellipse(gx - 0.012, ky + 0.1, 0.01, 0.012, fill=(255, 255, 255, 230))
        for k_ in range(5):                                                                              # Zacken mit Perlen
            zx = kx - 0.24 + k_ * 0.12
            c.poly([(zx - 0.06, ky + 0.2), (zx + 0.06, ky + 0.2), (zx, ky + 0.38)], fill=gold, outline=OUTLINE, width=0.02)
            c.ellipse(zx, ky + 0.39, 0.025, 0.025, fill=hexc("#f4f0e6"), outline=OUTLINE, width=0.01)
        c.ellipse(kx, ky + 0.3, 0.2, 0.1, fill=shade(velvet, 1.35), outline=OUTLINE, width=0.015)          # Samtkappe
        for sx in (-1, 1):                                                                               # Buegel
            c.line([(kx + sx * 0.22, ky + 0.22), (kx + sx * 0.1, ky + 0.42), (kx, ky + 0.48)], fill=OUTLINE, width=0.05)
            c.line([(kx + sx * 0.22, ky + 0.22), (kx + sx * 0.1, ky + 0.42), (kx, ky + 0.48)], fill=gold, width=0.028)
        c.ellipse(kx, ky + 0.5, 0.04, 0.04, fill=gold, outline=OUTLINE, width=0.015)                      # Reichsapfel
        c.line([(kx, ky + 0.53), (kx, ky + 0.62)], fill=OUTLINE, width=0.04)
        c.line([(kx - 0.035, ky + 0.585), (kx + 0.035, ky + 0.585)], fill=OUTLINE, width=0.04)
        c.line([(kx, ky + 0.53), (kx, ky + 0.62)], fill=gold, width=0.02)
        c.line([(kx - 0.035, ky + 0.585), (kx + 0.035, ky + 0.585)], fill=gold, width=0.02)
        # Muenzstapel und Streumuenzen (links vorn), Barren (rechts vorn), Kelch, Kette
        def coin(x, y, r=0.06):
            c.ellipse(x, y, r, r * 0.55, fill=gold, outline=OUTLINE, width=0.014)
            c.ellipse(x, y, r * 0.65, r * 0.35, outline=gold_d, width=0.008)
        def stack(x, y, n):
            for k_ in range(n):
                c.rect(x - 0.06, y + k_ * 0.03, x + 0.06, y + k_ * 0.03 + 0.03, fill=gold_d, outline=OUTLINE, width=0.012)
            coin(x, y + n * 0.03 + 0.005)
        mx, my = cx - 0.6, cy + zt0 - 0.3
        stack(mx, my, 5); stack(mx + 0.15, my - 0.08, 3); stack(mx - 0.14, my - 0.1, 2)
        for dx, dy in ((0.3, -0.12), (0.36, 0.02), (-0.28, 0.02), (0.1, -0.2), (-0.05, -0.22)):
            coin(mx + dx, my + dy, 0.05)
        bx, by = cx + 0.55, cy + zt0 - 0.32
        for k_, (dx, dy) in enumerate(((0, 0), (0.17, 0.02), (0.085, 0.1))):
            p.box(bx + dx - 0.09, by + dy, bx + dx + 0.09, by + dy + 0.1, 0, 0.12, gold, gold_d, w=0.014)
        c.rect(bx + 0.085 - 0.06, by + 0.1 + 0.12 * K + 0.02, bx + 0.085 + 0.06, by + 0.1 + 0.12 * K + 0.06, outline=gold_d, width=0.008)
        gx, gy = cx - 0.55, cy + zt0 + 0.3                                                                # Kelch
        c.ellipse(gx, gy, 0.08, 0.035, fill=gold, outline=OUTLINE, width=0.014)
        c.rect(gx - 0.015, gy, gx + 0.015, gy + 0.14, fill=gold, outline=OUTLINE, width=0.012)
        c.poly([(gx - 0.09, gy + 0.14), (gx + 0.09, gy + 0.14), (gx + 0.07, gy + 0.3), (gx - 0.07, gy + 0.3)], fill=gold, outline=OUTLINE, width=0.014)
        c.ellipse(gx, gy + 0.3, 0.07, 0.03, fill=gold_l, outline=OUTLINE, width=0.012)
        c.ellipse(gx, gy + 0.21, 0.02, 0.025, fill=hexc("#d02e3a"), outline=OUTLINE, width=0.008)
        nx, ny = cx + 0.55, cy + zt0 + 0.3                                                                # Kette mit Anhaenger
        chain = [(nx - 0.25, ny + 0.25), (nx - 0.2, ny + 0.05), (nx, ny - 0.05), (nx + 0.2, ny + 0.05), (nx + 0.25, ny + 0.25)]
        c.line(chain, fill=OUTLINE, width=0.035)
        c.line(chain, fill=gold, width=0.018)
        for q in chain[1:4]:
            c.ellipse(q[0], q[1], 0.018, 0.018, fill=gold_l, outline=OUTLINE, width=0.006)
        c.poly([(nx - 0.05, ny - 0.03), (nx + 0.05, ny - 0.03), (nx, ny - 0.14)], fill=hexc("#2f5fb0"), outline=OUTLINE, width=0.012)
        c.poly([(nx - 0.02, ny - 0.04), (nx + 0.02, ny - 0.04), (nx, ny - 0.1)], fill=hexc("#9fc4ff"))
        # Glashaube mit Messingkanten
        glass_h = 1.3
        p.box(x0 + 0.04, y0, x1 - 0.04, y1, sock, glass_h, alpha(hexc("#dff3ff"), 62), alpha(hexc("#bfe3f5"), 40),
              ol=alpha(hexc("#e9f7ff"), 230), w=0.03, glass=True)
        zt = sock + glass_h
        for ex_ in (x0 + 0.04, x1 - 0.04):
            c.line([(ex_, y0 + sock * K), (ex_, y0 + zt * K)], fill=brass, width=0.03)
        c.line([(x0 + 0.04, y0 + zt * K), (x1 - 0.04, y0 + zt * K)], fill=brass, width=0.03)
        c.line([(x0 + 0.04, y1 + zt * K), (x1 - 0.04, y1 + zt * K)], fill=brass, width=0.03)
        c.line([(x0 + 0.2, y0 + (sock + 0.1) * K), (x0 + 0.5, y0 + (zt - 0.1) * K)], fill=alpha((255, 255, 255, 255), 140), width=0.04)
        c.line([(x0 + 0.6, y0 + (sock + 0.1) * K), (x0 + 0.75, y0 + (sock + 0.5) * K)], fill=alpha((255, 255, 255, 255), 80), width=0.03)
    elif kind == "bank":
        seat = lift("#4a3222", 1.9)
        p.box(x0, y0, x1, y1, 0.25, 0.12, shade(seat, 1.15), seat)
        for lx in (x0 + 0.1, x1 - 0.2):
            p.box(lx, y0 + 0.05, lx + 0.1, y0 + 0.12, 0, 0.25, hexc("#2a2422"), hexc("#2a2422"), w=0.03)
    elif kind == "cafetisch":
        r = y1 - cy     # Tischradius; die Kollisions-Ellipse ist breiter und schliesst die Stuehle ein
        top = lift("#a08a68", 1.3)
        p.cyl(cx, cy, 0.06, 0, 0.7, hexc("#3b4046"), hexc("#3b4046"), w=0.03)
        p.cyl(cx, cy, r, 0.7, 0.06, shade(top, 1.1), top)
        zt = cy + 0.76 * K
        c.ellipse(cx, zt, r - 0.1, r - 0.1, outline=alpha((255, 255, 255, 255), 70), width=0.025)
        seat_c = lift("#c8702e", 1.25)
        for side in (-1, 1):
            sx, sy = cx + side * (r + 0.28), cy
            c.soft_shadow([(sx - 0.2, sy - 0.22), (sx + 0.24, sy - 0.22), (sx + 0.24, sy + 0.16), (sx - 0.2, sy + 0.16)], 80, 0.05)
            # Beine, Sitz, Lehne (Lehne auf der tischabgewandten Seite)
            for lx in (sx - 0.15, sx + 0.12):
                c.rect(lx, sy - 0.18, lx + 0.03, sy - 0.18 + 0.45 * K, fill=hexc("#3b4046"))
            p.box(sx - 0.19, sy - 0.18, sx + 0.19, sy + 0.18, 0.42, 0.06, shade(seat_c, 1.1), shade(seat_c, 0.85), w=0.03)
            bx = sx + side * 0.15
            p.box(min(bx, bx + side * 0.06), sy - 0.18, max(bx, bx + side * 0.06), sy + 0.18, 0.48, 0.45, shade(seat_c, 1.2), seat_c, w=0.03)
        c.ellipse(cx + 0.12, cy + 0.76 * K + 0.05, 0.08, 0.06, fill=(240, 240, 235, 255), outline=OUTLINE, width=0.02)
    elif kind == "trog":
        p.box(x0, y0, x1, y1, 0, 0.45, lift("#5d4636", 1.5), lift("#4a3222", 1.6))
        for i, px_ in enumerate((x0 + 0.4, cx, x1 - 0.4)):
            for j in range(5):
                a = math.radians(40 + j * 25)
                c.poly([(px_, y1 + 0.45 * K - 0.1), (px_ + 0.45 * math.cos(a) - 0.2, y1 + 0.45 * K + 0.45 * math.sin(a)),
                        (px_ + 0.08, y1 + 0.45 * K)], fill=lift("#3f7a48", 1.5 + 0.1 * (j % 2)), outline=OUTLINE, width=0.02)
    elif kind in ("admintisch", "vermittlungstisch", "resttisch", "werktisch"):
        if kind == "werktisch":
            # massive Werkbank mit Schubladen statt Tisch auf Beinen
            steel = lift("#8b949a", 1.25)
            p.box(x0, y0, x1, y1, 0, 0.9, lift("#8b949a", 1.5), steel)
            nd = max(2, int((x1 - x0) / 0.75))
            for i in range(nd):
                dx0 = x0 + 0.08 + i * (x1 - x0 - 0.16) / nd
                dx1 = dx0 + (x1 - x0 - 0.16) / nd - 0.06
                c.rect(dx0, y0 + 0.08, dx1, y0 + 0.9 * K - 0.08, outline=shade(steel, 0.7), width=0.02)
                c.rect((dx0 + dx1) / 2 - 0.12, y0 + 0.9 * K - 0.2, (dx0 + dx1) / 2 + 0.12, y0 + 0.9 * K - 0.15, fill=hexc("#3b4046"))
            rnd2 = random.Random(idx)
            zt = y0 + 0.9 * K
            for i in range(4):
                tx = rnd2.uniform(x0 + 0.3, x1 - 0.3)
                c.rect(tx - 0.15, zt + 0.2, tx + 0.15, zt + 0.4,
                       fill=rnd2.choice([hexc("#c9b27a"), hexc("#7a8a4a"), hexc("#d8e6ec")]), outline=OUTLINE, width=0.02)
            return p.c.finish(), p.c.x0, p.c.y0, p.base_y
        if False:
            top, front = None, None
        elif kind == "vermittlungstisch":
            top, front = lift("#6b4a2e", 1.7), lift("#6b4a2e", 1.4)
        else:
            top, front = lift("#6b6f75", 1.6), lift("#4b5259", 1.5)
        hh = PROP_H[kind]
        p.box(x0, y0, x1, y1, hh - 0.08, 0.08, top, front)
        for lx in (x0 + 0.05, x1 - 0.13):
            p.box(lx, y0 + 0.05, lx + 0.08, y0 + 0.13, 0, hh - 0.08, hexc("#2a2422"), hexc("#3b4046"), w=0.03)
        ztop = hh
        if kind == "admintisch":
            c.rect(x0 + 0.2, y0 + ztop * K + 0.1, x1 - 0.2, y1 + ztop * K - 0.1, fill=hexc("#8fd0ff"), outline=OUTLINE, width=0.03)
            for gx in range(4):
                c.line([(x0 + 0.4 + gx * 0.45, y0 + ztop * K + 0.15), (x0 + 0.4 + gx * 0.45, y1 + ztop * K - 0.15)], fill=hexc("#4a8ac0"), width=0.02)
        elif kind == "vermittlungstisch":
            for i in range(3):
                tx = x0 + 0.7 + i * 1.3
                c.rect(tx - 0.2, y0 + ztop * K + 0.25, tx + 0.2, y0 + ztop * K + 0.55, fill=hexc("#2a2422"), outline=OUTLINE, width=0.025)
                c.ellipse(tx, y0 + ztop * K + 0.4, 0.09, 0.08, fill=hexc("#d8cfb0"))
        elif kind == "resttisch":
            c.rect(x0 + 0.3, y0 + ztop * K + 0.2, x1 - 0.6, y1 + ztop * K - 0.2, fill=hexc("#a8843c"), outline=OUTLINE, width=0.03)
            c.rect(x0 + 0.38, y0 + ztop * K + 0.27, x1 - 0.68, y1 + ztop * K - 0.27, fill=hexc("#3f6f9a"))
            c.ellipse(x1 - 0.35, y0 + ztop * K + 0.6, 0.12, 0.12, fill=hexc("#d8e6ec"), outline=OUTLINE, width=0.02)
        else:
            rnd2 = random.Random(idx)
            for i in range(4):
                tx = rnd2.uniform(x0 + 0.3, x1 - 0.3)
                c.rect(tx - 0.15, y0 + ztop * K + 0.25, tx + 0.15, y0 + ztop * K + 0.45,
                       fill=rnd2.choice([hexc("#c9b27a"), hexc("#7a8a4a"), hexc("#d8e6ec")]), outline=OUTLINE, width=0.02)
    elif kind == "glaswand":
        # Glastrennwand: Alu-Pfosten an den Enden, Fussschiene, Kopfschiene, Glas mit Streifen-Glanz
        alu = hexc("#c0c8cc")
        p.box(x0, y0, x1, y1, 0, 2.0, alpha(hexc("#dff3ff"), 110), alpha(hexc("#bfe3f5"), 70),
              ol=alpha(hexc("#e9f7ff"), 230), w=0.03, glass=True)
        c.rect(x0 - 0.03, y0, x1 + 0.03, y0 + 0.06, fill=hexc("#8b949a"), outline=OUTLINE, width=0.02)
        for py_ in (y0, y1):
            c.rect((x0 + x1) / 2 - 0.06, py_, (x0 + x1) / 2 + 0.06, py_ + 2.0 * K, fill=alu, outline=OUTLINE, width=0.02)
        c.rect(x0 - 0.02, y1 + 2.0 * K - 0.04, x1 + 0.02, y1 + 2.0 * K + 0.02, fill=alu, outline=OUTLINE, width=0.02)
        yy = y0 + 0.5
        while yy < y1 - 0.3:
            c.line([(x0 + 0.03, yy + 1.2 * K), (x0 + 0.03, yy + 1.7 * K)], fill=alpha((255, 255, 255, 255), 130), width=0.03)
            yy += 1.3
    elif kind == "dino":
        stone = lift("#5a5650", 1.65)
        rx, ry = x1 - cx, y1 - cy
        zt = 0.55 * K
        # Sockel-Ellipse: Wandung mit dunklem Fuss und heller Deckkante
        c.ellipse(cx, cy, rx, ry, fill=stone, outline=OUTLINE)
        c.rect(x0, cy, x1, cy + zt, fill=stone)
        c.line([(x0, cy), (x0, cy + zt)], fill=OUTLINE, width=OUT_W)
        c.line([(x1, cy), (x1, cy + zt)], fill=OUTLINE, width=OUT_W)
        # Fussband (dunkel) + Steinplattenfugen an der Wandung
        c.poly([(x0 + 0.03, cy + 0.02), (x1 - 0.03, cy + 0.02), (x1 - 0.03, cy + 0.11), (x0 + 0.03, cy + 0.11)], fill=shade(stone, 0.7))
        for fx in (f_ for f_ in (-3.2, -2.2, -1.1, 0, 1.1, 2.2, 3.2) if abs(f_) < rx - 0.2):
            yb = cy - ry * math.sqrt(max(0, 1 - (fx / rx) ** 2))
            c.line([(cx + fx, yb + 0.14), (cx + fx, yb + zt - 0.02)], fill=shade(stone, 0.78), width=0.025)
        c.ellipse(cx, cy + zt, rx, ry, fill=shade(stone, 1.18), outline=OUTLINE)
        c.ellipse(cx, cy + zt, rx - 0.05, ry - 0.05, outline=shade(stone, 1.35), width=0.03)
        # Sandbett mit Grabungsraster und Steinen
        sand = lift("#8a7048", 1.45)
        srx, sry = rx - 0.42, ry - 0.3
        c.ellipse(cx, cy + zt, srx, sry, fill=sand, outline=shade(sand, 0.65), width=0.045)
        c.ellipse(cx, cy + zt + 0.04, srx - 0.1, sry - 0.08, outline=shade(sand, 0.85), width=0.02)
        rs = random.Random(3)
        for _ in range(48):
            a, r = rs.uniform(0, 2 * math.pi), math.sqrt(rs.uniform(0, 1))
            sx, sy = cx + (srx - 0.2) * r * math.cos(a), cy + zt + (sry - 0.15) * r * math.sin(a)
            c.ellipse(sx, sy, 0.06, 0.04, fill=shade(sand, rs.choice([0.72, 0.85, 1.15, 1.25])), outline=shade(sand, 0.6), width=0.012)
        # Absperrpfosten hinten (vor dem Skelett gezeichnet) und vorne (danach)
        prx, pry = rx - 0.2, ry - 0.14
        draw_rope_posts(p, cx, cy + zt, prx, pry, 0, list(range(15, 166, 30)))
        draw_rope_posts(p, cx, cy + zt, prx, pry, 0, list(range(195, 346, 30)))
        # Plakette an der Sockelfront
        c.rect(cx - 0.55, cy + 0.14, cx + 0.55, cy + zt - 0.06, fill=hexc("#b08a3c"), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.5, cy + 0.18, cx + 0.5, cy + zt - 0.1, outline=shade(hexc("#b08a3c"), 1.3), width=0.015)
        c.text(cx, cy + (zt + 0.08) / 2, "TYRANNOSAURUS REX", 0.085, hexc("#2a2422"))
    elif kind in ("dino_rex", "dino_rex_head", "dino_rex_jaw"):
        # nur das Skelett (mit Stahlstuetzen), Standlinie wie der Sockel; Oberkante des Sockels = cy + 0,55 K.
        # Rumpf, Kopf und Unterkiefer sind getrennte Sprites, damit der Rex bei der Sabotage den Kopf
        # bewegen und das Maul aufreissen kann (AtlasRex).
        part = {"dino_rex": "body", "dino_rex_head": "head", "dino_rex_jaw": "jaw"}[kind]
        draw_skeleton(p, cx, cy + 0.55 * K, S=REX_SCALE, ox=REX_OFFSET, part=part)
    elif kind == "spieluhr":
        draw_spieluhr(p, cx, cy)
    elif kind == "nachtlicht":
        draw_nachtlicht(p, cx, cy)
    elif kind == "infotheke":
        wood = lift("#4a3222", 1.7)
        brass = lift("#b08a3c", 1.3)
        marble = lift("#9c948a", 1.5)
        rx, ry = x1 - cx, y1 - cy
        zt = cy + K
        # Ringtresen: Holzwandung mit dunklem Fuss, Paneelfugen und heller Oberkante
        c.ellipse(cx, cy, rx, ry, fill=wood, outline=OUTLINE)
        c.rect(x0, cy, x1, zt, fill=wood)
        c.line([(x0, cy), (x0, zt)], fill=OUTLINE, width=OUT_W)
        c.line([(x1, cy), (x1, zt)], fill=OUTLINE, width=OUT_W)
        c.poly([(x0 + 0.03, cy + 0.02), (x1 - 0.03, cy + 0.02), (x1 - 0.03, cy + 0.1), (x0 + 0.03, cy + 0.1)], fill=shade(wood, 0.65))
        for fx in (-1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75):
            yb = cy - ry * math.sqrt(max(0, 1 - (fx / rx) ** 2))
            c.line([(cx + fx, yb + 0.12), (cx + fx, yb + K - 0.1)], fill=shade(wood, 0.72), width=0.03)
            c.line([(cx + fx + 0.03, yb + 0.12), (cx + fx + 0.03, yb + K - 0.1)], fill=shade(wood, 1.15), width=0.015)
        # Messingleiste unter der Platte
        pts = [(cx + rx * math.cos(math.radians(a)), cy - ry * math.sin(math.radians(a)) + K - 0.05) for a in range(0, 181, 6)]
        c.line(pts, fill=brass, width=0.035)
        # Tresenplatte: Marmor mit Messingkante, innen der abgesenkte Arbeitsplatz
        c.ellipse(cx, zt, rx, ry, fill=brass, outline=OUTLINE)
        c.ellipse(cx, zt, rx - 0.08, ry - 0.08, fill=marble, outline=None)
        c.ellipse(cx, zt + 0.02, rx - 0.12, ry - 0.11, outline=(255, 255, 255, 90), width=0.02)
        well = lift("#6b6f75", 1.35)
        c.ellipse(cx, zt + 0.12, rx - 0.7, ry - 0.55, fill=well, outline=OUTLINE, width=0.035)
        c.ellipse(cx, zt + 0.12 - (ry - 0.55) * 0.35, rx - 0.85, (ry - 0.55) * 0.55, fill=shade(well, 0.86))
        c.ellipse(cx, zt + 0.12, rx - 0.75, ry - 0.6, outline=shade(well, 0.7), width=0.02)
        # Buerostuhl im Innenraum + Papierkorb
        c.ellipse(cx + 0.35, zt + 0.15, 0.22, 0.16, fill=hexc("#2a2f35"), outline=OUTLINE, width=0.025)
        c.ellipse(cx + 0.35, zt + 0.15, 0.13, 0.09, fill=hexc("#3f4a56"))
        c.ellipse(cx - 1.0, zt + 0.0, 0.1, 0.08, fill=hexc("#8b949a"), outline=OUTLINE, width=0.02)
        # Bildschirm (Nordwest) + Telefon + Klingel + Stiftbecher
        c.rect(cx - 1.0, zt + 0.45, cx - 0.45, zt + 0.8, fill=hexc("#2a2f35"), outline=OUTLINE, width=0.03)
        c.rect(cx - 0.95, zt + 0.5, cx - 0.5, zt + 0.75, fill=hexc("#8fd0ff"))
        c.rect(cx - 0.93, zt + 0.66, cx - 0.62, zt + 0.7, fill=hexc("#dff3ff"))
        c.rect(cx - 0.75, zt + 0.38, cx - 0.7, zt + 0.45, fill=hexc("#2a2f35"))
        c.rect(cx + 0.55, zt + 0.55, cx + 0.85, zt + 0.72, fill=hexc("#2a2f35"), outline=OUTLINE, width=0.025)
        c.ellipse(cx + 0.63, zt + 0.7, 0.05, 0.03, fill=hexc("#c0c8cc"))
        c.ellipse(cx + 1.1, zt + 0.3, 0.09, 0.065, fill=hexc("#d9b25c"), outline=OUTLINE, width=0.02)
        c.ellipse(cx + 1.1, zt + 0.32, 0.03, 0.02, fill=(255, 250, 230, 255))
        c.rect(cx + 1.35, zt + 0.35, cx + 1.47, zt + 0.48, fill=hexc("#3f6f9a"), outline=OUTLINE, width=0.02)
        # Prospektstapel + Lageplan auf dem Tresenring (vorne, gut lesbar)
        for bx, col in ((-1.55, "#3f6f9a"), (-1.3, "#b0603a"), (1.3, "#7a8a4a"), (1.55, "#c9b27a")):
            by = zt - ry * math.sqrt(max(0, 1 - (bx / rx) ** 2)) + 0.2
            c.rect(cx + bx - 0.1, by, cx + bx + 0.1, by + 0.14, fill=hexc(col), outline=OUTLINE, width=0.02)
            c.line([(cx + bx - 0.06, by + 0.1), (cx + bx + 0.06, by + 0.1)], fill=(240, 240, 235, 255), width=0.015)
        c.rect(cx - 0.4, zt - ry + 0.14, cx + 0.4, zt - ry + 0.34, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.02)
        c.rect(cx - 0.34, zt - ry + 0.18, cx - 0.05, zt - ry + 0.3, fill=hexc("#8fb0a4"))
        c.rect(cx + 0.0, zt - ry + 0.18, cx + 0.34, zt - ry + 0.3, fill=hexc("#c9a86a"))
        c.line([(cx - 0.3, zt - ry + 0.24), (cx + 0.3, zt - ry + 0.24)], fill=hexc("#8e2f2f"), width=0.02)
        # "i"-Schild an der Front
        c.ellipse(cx, cy - ry + 0.5 * K, 0.2, 0.2, fill=hexc("#2f4f8a"), outline=OUTLINE, width=0.03)
        c.text(cx, cy - ry + 0.5 * K, "i", 0.3, (255, 255, 255, 255))
    elif kind == "kasse":
        wood = lift("#4a3222", 1.7)
        brass = lift("#b08a3c", 1.3)
        # Kabine: Holzsockel, Glasfront, Messingdach mit Schild
        p.box(x0, y0, x1, y1, 0, 1.0, lift("#7a5636", 1.5), wood)
        for fx in (x0 + 0.45, x0 + 0.9):
            c.line([(fx, y0 + 0.08), (fx, y0 + K - 0.08)], fill=shade(wood, 0.75), width=0.02)
        # Kassierer-Innenraum hinter dem Glas: Kasse + Ticketrolle auf dem Tresen
        c.rect(cx - 0.3, y0 + K + 0.12, cx + 0.3, y0 + K + 0.42, fill=hexc("#2a2f35"), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.22, y0 + K + 0.28, cx + 0.22, y0 + K + 0.38, fill=hexc("#8fd0ff"))
        c.ellipse(x0 + 0.3, y0 + K + 0.3, 0.12, 0.09, fill=hexc("#e8d9a8"), outline=OUTLINE, width=0.02)
        p.box(x0 + 0.06, y0 + 0.05, x1 - 0.06, y1 - 0.05, 1.0, 0.85, alpha(hexc("#dff3ff"), 70), alpha(hexc("#bfe3f5"), 70),
              ol=alpha(hexc("#e9f7ff"), 220), w=0.03, glass=True)
        c.line([(x0 + 0.2, y0 + 1.1 * K), (x0 + 0.45, y0 + 1.75 * K)], fill=alpha((255, 255, 255, 255), 140), width=0.03)
        # Dach ueber der ganzen Kabine (Messing, dunkle Traufe) + Schild an der Front
        red = lift("#8e2f2f", 1.35)
        cream = hexc("#efe4c8")
        rx0, rx1, ry0, ry1 = x0 - 0.06, x1 + 0.06, y0 - 0.1, y1 + 0.02
        p.box(rx0, ry0, rx1, ry1, 1.85, 0.12, red, shade(brass, 0.78))
        # Markisenstreifen auf dem Dach (liest sich in der Aufsicht als Kassenhaeuschen)
        tz0, tz1 = ry0 + 1.97 * K, ry1 + 1.97 * K
        n = 7
        sw = (rx1 - rx0) / n
        for i in range(1, n, 2):
            c.rect(rx0 + i * sw, tz0 + 0.03, rx0 + (i + 1) * sw, tz1 - 0.03, fill=cream)
        c.rect(rx0, tz0, rx1, tz1, outline=OUTLINE, width=OUT_W)
        c.line([(rx0 + 0.05, tz1 - 0.06), (rx1 - 0.05, tz1 - 0.06)], fill=alpha((255, 255, 255, 255), 110), width=0.03)
        c.rect(x0 + 0.1, y0 + 1.97 * K - 0.02, x1 - 0.1, y0 + 1.97 * K + 0.22, fill=hexc("#5a2a2a"), outline=OUTLINE, width=0.025)
        c.text(cx, y0 + 1.97 * K + 0.1, "TICKETS", 0.15, hexc("#d9b25c"))
    elif kind == "treppe":
        carpet = lift("#5a2a2a", 1.7)
        marble = lift("#8a8275", 1.45)
        n = 6
        d = (y1 - y0) / n
        # Von Norden (hoch, hinten) nach Sueden (niedrig, vorne) zeichnen, sonst deckt jede
        # hoehere Stufe die vorderen zu und die Treppe liest sich als Block.
        for i in reversed(range(n)):
            yy = y0 + i * d
            z = (i + 1) * 0.22
            p.box(x0, yy, x1, yy + d, 0, z, marble, shade(marble, 0.85), w=0.035)
            c.rect(cx - 0.55, yy + z * K, cx + 0.55, yy + d + z * K, fill=carpet)
            c.line([(cx - 0.55, yy + d + z * K - 0.02), (cx + 0.55, yy + d + z * K - 0.02)], fill=hexc("#b08a3c"), width=0.025)
            c.line([(x0 + 0.04, yy + z * K + 0.03), (x1 - 0.04, yy + z * K + 0.03)], fill=shade(marble, 1.2), width=0.02)
            # Teppichstangen (Messing) an jeder Stufenkante
            c.line([(cx - 0.55, yy + z * K + 0.02), (cx + 0.55, yy + z * K + 0.02)], fill=hexc("#d9b25c"), width=0.02)
        # Messinggelaender an beiden Seiten mit Handlauf
        for gx in (x0 - 0.02, x1 - 0.1):
            p.box(gx, y0, gx + 0.12, y1, 0, 1.4, lift("#b08a3c", 1.3), lift("#b08a3c", 1.1), w=0.03)
            c.line([(gx + 0.02, y0 + 1.4 * K), (gx + 0.02, y1 + 1.4 * K)], fill=lift("#b08a3c", 1.6), width=0.02)
    elif kind == "garderobe":
        wood = lift("#4a3222", 1.6)
        # Rueckwand-Schrank an der Westwand + Kleiderstange mit Maenteln davor
        p.box(x0, y0, x0 + 0.22, y1, 0, 1.8, shade(wood, 1.15), wood)
        zt = 1.55
        c.line([(x0 + 0.35, y0 + 0.15 + zt * K), (x0 + 0.35, y1 - 0.1 + zt * K)], fill=hexc("#b08a3c"), width=0.05)
        cols = ["#3f6f9a", "#7a2a2a", "#3a3a3a", "#b0603a", "#2f4a3a", "#6b4a7a"]
        n = int((y1 - y0 - 0.3) / 0.55)
        for i in range(n):
            cyy = y1 - 0.4 - i * 0.55
            col = hexc(cols[i % len(cols)])
            top_y = cyy + zt * K
            c.poly([(x0 + 0.24, top_y - 0.05), (x0 + 0.47, top_y - 0.05), (x0 + 0.52, top_y - 0.75), (x0 + 0.19, top_y - 0.75)],
                   fill=col, outline=OUTLINE, width=0.025)
            c.line([(x0 + 0.355, top_y - 0.08), (x0 + 0.355, top_y - 0.7)], fill=shade(col, 0.7), width=0.015)
            c.ellipse(x0 + 0.355, top_y, 0.05, 0.03, fill=hexc("#b08a3c"), outline=OUTLINE, width=0.015)
        c.rect(x0 + 0.3, y0, x0 + 0.4, y0 + zt * K, fill=hexc("#b08a3c"), outline=OUTLINE, width=0.02)
    elif kind in ("tresen_kasse", "tresen_cafe"):
        wood = lift("#7a5636", 1.4)
        p.box(x0, y0, x1, y1, 0, 1.0, lift("#a08a68", 1.3), wood)
        for fx in range(1, int((x1 - x0) / 0.8) + 1):
            c.line([(x0 + fx * 0.8, y0 + 0.1), (x0 + fx * 0.8, y0 + K - 0.1)], fill=shade(wood, 0.75), width=0.025)
        zt = y0 + K
        if kind == "tresen_kasse":
            p.box(cx - 0.35, y0 + 0.3, cx + 0.35, y0 + 0.75, 1.0, 0.3, hexc("#2a2f35"), hexc("#3b4046"), w=0.03)
            c.rect(cx - 0.25, zt + 0.3 * K + 0.35, cx + 0.25, zt + 0.3 * K + 0.6, fill=hexc("#8fd0ff"), outline=OUTLINE, width=0.02)
            for i in range(5):
                bx = x0 + 0.35 + i * 0.25
                c.rect(bx, zt + 0.2, bx + 0.18, zt + 0.45, fill=hexc(["#b0603a", "#3f6f9a", "#c9b27a", "#7a8a4a", "#9d6cc7"][i]), outline=OUTLINE, width=0.015)
        else:
            p.box(x1 - 1.0, y0 + 0.3, x1 - 0.5, y0 + 0.8, 1.0, 0.5, hexc("#c0c8cc"), hexc("#8b949a"), w=0.03)
            for i in range(4):
                c.ellipse(x0 + 0.5 + i * 0.4, zt + 0.5, 0.1, 0.08, fill=(240, 240, 235, 255), outline=OUTLINE, width=0.02)
            c.rect(x0 + 1.9, zt + 0.35, x0 + 2.6, zt + 0.65, fill=hexc("#e0b04a"), outline=OUTLINE, width=0.02)
    elif kind in ("regal_shop", "regal_insel", "regal_werk", "funkregal", "spind", "schaltschrank", "monitorwand", "vermittlung"):
        palette = {
            "regal_shop": ("#7a5636", 1.4), "regal_insel": ("#7a5636", 1.4), "regal_werk": ("#8b949a", 1.25),
            "funkregal": ("#4a3220", 1.6), "spind": ("#3a3f46", 1.6), "schaltschrank": ("#7b8b8f", 1.35),
            "monitorwand": ("#1e2226", 1.8), "vermittlung": ("#4a3220", 1.7),
        }
        base, f = palette[kind]
        col = lift(base, f)
        hh = PROP_H[kind]
        p.box(x0, y0, x1, y1, 0, hh, shade(col, 1.15), col)
        fx0, fx1, fy0, fy1 = x0 + 0.06, x1 - 0.06, y0 + 0.06, y0 + hh * K - 0.06
        if kind in ("regal_shop", "regal_insel", "regal_werk", "funkregal"):
            levels = 4
            for i in range(levels):
                ly = fy0 + (fy1 - fy0) * i / levels
                c.line([(fx0, ly), (fx1, ly)], fill=shade(col, 0.7), width=0.03)
                xx = fx0 + 0.05
                while xx < fx1 - 0.15:
                    ww = rnd.uniform(0.12, 0.28)
                    hh2 = rnd.uniform(0.12, (fy1 - fy0) / levels - 0.05)
                    colr = rnd.choice([hexc("#b0603a"), hexc("#3f6f9a"), hexc("#c9b27a"), hexc("#7a8a4a"), hexc("#d8cfb0"), hexc("#2a2422")])
                    c.rect(xx, ly + 0.03, min(fx1, xx + ww), ly + 0.03 + hh2, fill=colr, outline=OUTLINE, width=0.015)
                    xx += ww + 0.04
        elif kind == "monitorwand":
            # Frontseite: Bedienpult mit Tastenreihen und Statuslampen
            for i in range(3):
                ly = fy0 + 0.06 + i * 0.14
                for j in range(4):
                    c.rect(fx0 + 0.04 + j * 0.08, ly, fx0 + 0.1 + j * 0.08, ly + 0.08, fill=hexc("#8b949a"), outline=OUTLINE, width=0.012)
            c.rect(fx0 + 0.02, fy1 - 0.3, fx1 - 0.02, fy1 - 0.05, fill=hexc("#8fb8c8"), outline=OUTLINE, width=0.02)
            c.ellipse(fx1 - 0.08, fy0 + 0.1, 0.025, 0.025, fill=hexc("#57d98a"))
            c.ellipse(fx1 - 0.08, fy0 + 0.2, 0.025, 0.025, fill=hexc("#e05a3a"))
            # Deckflaeche: Monitorreihe (Kamerabilder mit Gang, Spieler-Punkt, REC) entlang der Wand
            tz = hh * K
            c.rect(x0 + 0.03, y0 + tz + 0.06, x1 - 0.03, y1 + tz - 0.06, fill=hexc("#2a2f35"))
            rs = random.Random(idx)
            yy = y0 + tz + 0.2
            k = 0
            while yy < y1 + tz - 0.45:
                c.rect(x0 + 0.06, yy, x1 - 0.06, yy + 0.36, fill=hexc("#1e2226"), outline=OUTLINE, width=0.02)
                c.rect(x0 + 0.09, yy + 0.03, x1 - 0.09, yy + 0.33, fill=hexc("#6f8fa0") if k % 3 else hexc("#4a6a7a"))
                c.rect(x0 + 0.12, yy + 0.12, x1 - 0.12, yy + 0.24, fill=hexc("#8fb8c8"))
                if rs.random() < 0.5:
                    c.ellipse(rs.uniform(x0 + 0.14, x1 - 0.14), yy + 0.18, 0.03, 0.03, fill=hexc("#e05a3a"), outline=OUTLINE, width=0.01)
                c.ellipse(x1 - 0.11, yy + 0.3, 0.015, 0.015, fill=hexc("#e05a3a"))
                yy += 0.46; k += 1
            c.glow(cx, cy + tz, 1.6, hexc("#6f8fa0"), 0.3)
        elif kind == "vermittlung":
            # Schreibpult unten, darueber Klinkenfeld mit Lampenleiste und haengenden Stoepselschnueren
            ledge = fy0 + 0.28
            c.rect(fx0, fy0, fx1, ledge, fill=shade(col, 0.9), outline=OUTLINE, width=0.02)
            c.rect(fx0 - 0.02, ledge, fx1 + 0.02, ledge + 0.06, fill=shade(col, 1.3), outline=OUTLINE, width=0.02)
            px0, px1, py0, py1 = fx0 + 0.08, fx1 - 0.08, ledge + 0.14, fy1 - 0.04
            c.rect(px0, py0, px1, py1, fill=hexc("#2a2422"), outline=OUTLINE, width=0.025)
            nj = int((px1 - px0) / 0.2)
            for i in range(nj):
                jx = px0 + 0.12 + i * (px1 - px0 - 0.24) / max(1, nj - 1)
                c.ellipse(jx, py1 - 0.1, 0.035, 0.03, fill=hexc("#ffd9a0") if i % 3 else hexc("#e05a3a"))
                for j in (0.3, 0.5):
                    c.ellipse(jx, py1 - j, 0.03, 0.03, fill=hexc("#b0a890"))
            rs = random.Random(idx)
            for _ in range(7):
                ax = rs.uniform(px0 + 0.2, px1 - 0.2)
                bx = ax + rs.uniform(-0.8, 0.8)
                bx = min(px1 - 0.1, max(px0 + 0.1, bx))
                col_c = rs.choice([hexc("#e05a3a"), hexc("#e0b04a"), hexc("#3f9e6e"), hexc("#5f9bd0")])
                sag = ledge + 0.1
                c.line([(ax, py1 - 0.3), ((ax + bx) / 2, sag), (bx, py1 - 0.5)], fill=OUTLINE, width=0.05)
                c.line([(ax, py1 - 0.3), ((ax + bx) / 2, sag), (bx, py1 - 0.5)], fill=col_c, width=0.025)
        elif kind == "spind":
            # Spindreihe: Tueren mit Lueftungsschlitzen, Griff und Namensschild auf der Front
            n = max(1, int(round((x1 - x0) / 0.45)))
            dw = (fx1 - fx0) / n
            for i in range(n):
                dx0, dx1 = fx0 + i * dw + 0.02, fx0 + (i + 1) * dw - 0.02
                c.rect(dx0, fy0, dx1, fy1, fill=shade(col, 1.06 if i % 2 else 0.98), outline=OUTLINE, width=0.02)
                for j in range(3):
                    vy = fy1 - 0.12 - j * 0.06
                    c.line([(dx0 + 0.08, vy), (dx1 - 0.08, vy)], fill=shade(col, 0.6), width=0.02)
                c.rect(dx1 - 0.1, (fy0 + fy1) / 2 - 0.1, dx1 - 0.06, (fy0 + fy1) / 2 + 0.06, fill=hexc("#c0c8cc"))
                c.rect(dx0 + 0.08, fy1 - 0.4, dx0 + 0.24, fy1 - 0.32, fill=hexc("#efe4c8"))
        elif kind == "schaltschrank":
            # Schrankreihe entlang der Westwand: Tueren von oben mit Lueftungsschlitzen, Anzeigen und
            # Warnschild; Front (Sued) mit Manometer und Hebel
            tz = hh * K
            n = max(1, int(round((y1 - y0) / 1.0)))
            dh = (y1 - y0) / n
            for i in range(n):
                dy0, dy1 = y0 + tz + i * dh + 0.04, y0 + tz + (i + 1) * dh - 0.04
                c.rect(x0 + 0.05, dy0, x1 - 0.05, dy1, fill=shade(col, 1.04 if i % 2 else 0.96), outline=OUTLINE, width=0.02)
                for j in range(4):
                    vy = dy0 + 0.1 + j * 0.06
                    c.line([(x0 + 0.14, vy), (x1 - 0.14, vy)], fill=shade(col, 0.6), width=0.02)
                c.rect(x0 + 0.14, dy1 - 0.3, x1 - 0.14, dy1 - 0.1, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
                for j in range(3):
                    c.ellipse(x0 + 0.22 + j * 0.16, dy1 - 0.2, 0.03, 0.03, fill=[hexc("#57d98a"), hexc("#e0b04a"), hexc("#e05a3a")][(i + j) % 3])
                c.rect(x1 - 0.13, (dy0 + dy1) / 2 - 0.08, x1 - 0.09, (dy0 + dy1) / 2 + 0.08, fill=hexc("#c0c8cc"))
            wz = fy0 + 0.62
            c.poly([(cx - 0.14, wz), (cx + 0.14, wz), (cx, wz + 0.24)], fill=hexc("#d4b13c"), outline=OUTLINE, width=0.015)
            c.line([(cx - 0.03, wz + 0.05), (cx + 0.02, wz + 0.12), (cx - 0.02, wz + 0.12), (cx + 0.03, wz + 0.2)], fill=OUTLINE, width=0.02)
            c.ellipse(cx - 0.15, fy0 + 0.3, 0.09, 0.09, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.02)
            c.line([(cx - 0.15, fy0 + 0.3), (cx - 0.1, fy0 + 0.36)], fill=hexc("#e05a3a"), width=0.015)
            c.rect(cx + 0.1, fy0 + 0.15, cx + 0.16, fy0 + 0.45, fill=hexc("#e05a3a"), outline=OUTLINE, width=0.015)
            c.rect(fx0 + 0.02, fy1 - 0.16, fx1 - 0.02, fy1 - 0.06, fill=hexc("#d4b13c"))
    elif kind == "klima":
        col = lift("#7b8288", 1.45)
        p.box(x0, y0, x1, y1, 0, 1.2, shade(col, 1.12), col)
        zt = y0 + 1.2 * K
        c.ellipse(cx - 0.4, zt + 0.7, 0.45, 0.45, fill=shade(col, 0.7), outline=OUTLINE, width=0.03)
        for a in range(0, 360, 60):
            c.line([(cx - 0.4, zt + 0.7), (cx - 0.4 + 0.4 * math.cos(math.radians(a)), zt + 0.7 + 0.4 * math.sin(math.radians(a)))], fill=OUTLINE, width=0.03)
        for i in range(6):
            c.line([(x0 + 0.1, y0 + 0.15 + i * 0.12), (x1 - 0.1, y0 + 0.15 + i * 0.12)], fill=shade(col, 0.75), width=0.02)
    elif kind == "kessel":
        r = x1 - cx
        col = lift("#7b8288", 1.4)
        p.cyl(cx, cy, r, 0, 1.8, shade(col, 1.15), col)
        # Lichtkante links, Schattenkante rechts, zwei Messingbaender, Manometer, Ventil
        c.line([(cx - r + 0.07, cy + 0.1), (cx - r + 0.07, cy + 1.75 * K)], fill=shade(col, 1.25), width=0.04)
        c.line([(cx + r - 0.07, cy + 0.1), (cx + r - 0.07, cy + 1.75 * K)], fill=shade(col, 0.8), width=0.05)
        for zz in (0.55, 1.3):
            c.rect(cx - r, cy + zz * K, cx + r, cy + (zz + 0.12) * K, fill=hexc("#c8a032"), outline=OUTLINE, width=0.015)
        c.ellipse(cx, cy + 1.0 * K, 0.11, 0.11, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.025)
        c.line([(cx, cy + 1.0 * K), (cx + 0.05, cy + 1.0 * K + 0.07)], fill=hexc("#e05a3a"), width=0.015)
        c.rect(cx - 0.03, cy + 1.8 * K, cx + 0.03, cy + 2.0 * K + 0.05, fill=hexc("#3b4046"), outline=OUTLINE, width=0.015)
        c.ellipse(cx, cy + 2.0 * K + 0.05, 0.1, 0.06, fill=hexc("#a83636"), outline=OUTLINE, width=0.02)
        c.line([(cx + r - 0.05, cy + 0.4 * K), (cx + r + 0.25, cy + 0.4 * K), (cx + r + 0.25, cy - 0.05)], fill=OUTLINE, width=0.09)
        c.line([(cx + r - 0.05, cy + 0.4 * K), (cx + r + 0.25, cy + 0.4 * K), (cx + r + 0.25, cy - 0.05)], fill=hexc("#8b949a"), width=0.05)
    elif kind == "sarkophag":
        # Mumiensarkophag (User 24.10.: "neu, mehr Detail, realistischer"): Sandsteinsockel mit Stufe, mumienfoermiger
        # Deckel (Schultern breit, Fussende schmal, Kopf im Norden), Nemes-Kopftuch in Lapis und Gold, Gesicht mit
        # Kohl-Augen und Zeremonialbart, Uraeus, Usech-Kragen, gekreuzte Arme mit Krummstab und Geissel, Fluegel
        # der Nut ueber der Brust, Hieroglyphenkolumne bis zu den Fuessen, Federmuster, Kartusche am Fussende.
        gold = lift("#c89a3a", 1.3)
        gold_d = shade(gold, 0.72)
        gold_l = hexc("#ffe9a8")
        lapis = hexc("#2f4f9a")
        lapis_d = shade(lapis, 0.7)
        turq = hexc("#3fa8a0")
        carn = hexc("#b8402a")
        skin = hexc("#d9a860")
        stone_t, stone_f = lift("#8a7a5c", 1.45), lift("#8a7a5c", 1.2)
        kohl = hexc("#1e1a18")
        hw = (x1 - x0) / 2
        # Sockel (zwei Stufen)
        p.box(x0 - 0.12, y0 - 0.12, x1 + 0.12, y1 + 0.12, 0, 0.18, stone_t, stone_f)
        p.box(x0 - 0.04, y0 - 0.04, x1 + 0.04, y1 + 0.04, 0.18, 0.17, shade(stone_t, 1.05), shade(stone_f, 0.95))
        for i in range(3):
            c.line([(x0 - 0.1 + i * 0.3, y0 - 0.1), (x0 - 0.1 + i * 0.3, y0 - 0.12 + 0.17 * K)], fill=shade(stone_f, 0.75), width=0.012)
        zb = 0.35
        H = 0.55
        zt = zb + H
        tb0, tb1 = y0 + zt * K, y1 + zt * K          # Deckflaeche: Bild-y von Fuss (Sued) bis Kopf (Nord)
        L_ = tb1 - tb0
        # Fussende (Stirnseite) in Gold mit Hieroglyphenband
        fw = hw * 0.62
        c.poly([(cx - fw, y0 + zb * K), (cx + fw, y0 + zb * K), (cx + fw, tb0), (cx - fw, tb0)], fill=gold_d, outline=OUTLINE)
        c.rect(cx - fw + 0.04, y0 + zb * K + 0.06, cx + fw - 0.04, tb0 - 0.05, fill=lapis, outline=OUTLINE, width=0.012)
        for i in range(4):
            gx = cx - fw + 0.1 + i * (2 * fw - 0.2) / 3
            c.ellipse(gx, (y0 + zb * K + tb0) / 2, 0.025, 0.035, fill=gold_l)
        # Deckel-Umriss (Mumienform): Fuss schmal, Schultern breit, runder Kopf
        sh_y = tb1 - L_ * 0.3                          # Schulterlinie
        lid = [(cx - fw, tb0), (cx + fw, tb0), (cx + hw * 0.92, sh_y - 0.25), (cx + hw, sh_y), (cx + hw * 0.95, sh_y + 0.14),
               (cx + hw * 0.62, tb1 - 0.3), (cx + hw * 0.55, tb1 - 0.08), (cx + hw * 0.3, tb1), (cx - hw * 0.3, tb1), (cx - hw * 0.55, tb1 - 0.08),
               (cx - hw * 0.62, tb1 - 0.3), (cx - hw * 0.95, sh_y + 0.14), (cx - hw, sh_y), (cx - hw * 0.92, sh_y - 0.25)]
        c.poly(lid, fill=gold, outline=OUTLINE)
        c.poly([(q[0] * 0.92 + cx * 0.08, q[1]) for q in lid], outline=alpha(gold_d, 200), width=0.012)
        c.line([(cx - fw + 0.04, tb0 + 0.02), (cx + fw - 0.04, tb0 + 0.02)], fill=gold_l, width=0.012)
        # Federmuster (Rischi) auf dem Unterkoerper, Mittelkolumne mit Hieroglyphen
        body_y0, body_y1 = tb0 + 0.3, sh_y - 0.55
        col_w = 0.11
        c.rect(cx - col_w, body_y0 - 0.1, cx + col_w, body_y1 + 0.05, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
        c.line([(cx - col_w + 0.015, body_y0 - 0.08), (cx - col_w + 0.015, body_y1 + 0.03)], fill=lapis, width=0.012)
        c.line([(cx + col_w - 0.015, body_y0 - 0.08), (cx + col_w - 0.015, body_y1 + 0.03)], fill=lapis, width=0.012)
        yy = body_y0 - 0.04
        k_ = 0
        while yy < body_y1 - 0.02:
            gsym = k_ % 5
            if gsym == 0:                                     # Auge
                c.ellipse(cx, yy + 0.03, 0.045, 0.022, fill=lapis, outline=OUTLINE, width=0.008)
                c.ellipse(cx, yy + 0.03, 0.012, 0.012, fill=kohl)
            elif gsym == 1:                                   # Anch
                c.ellipse(cx, yy + 0.055, 0.02, 0.022, outline=kohl, width=0.01)
                c.line([(cx, yy + 0.035), (cx, yy)], fill=kohl, width=0.012)
                c.line([(cx - 0.03, yy + 0.028), (cx + 0.03, yy + 0.028)], fill=kohl, width=0.01)
            elif gsym == 2:                                   # Wasser (Zickzack)
                c.line([(cx - 0.04 + i * 0.02, yy + 0.03 + (0.015 if i % 2 else -0.015)) for i in range(5)], fill=lapis, width=0.01)
            elif gsym == 3:                                   # Vogel
                c.ellipse(cx + 0.01, yy + 0.025, 0.03, 0.018, fill=kohl)
                c.ellipse(cx + 0.035, yy + 0.05, 0.012, 0.012, fill=kohl)
                c.line([(cx - 0.02, yy + 0.005), (cx - 0.02, yy - 0.01)], fill=kohl, width=0.008)
            else:                                             # Sonnenscheibe
                c.ellipse(cx, yy + 0.03, 0.022, 0.022, fill=carn, outline=kohl, width=0.008)
            yy += 0.1
            k_ += 1
        for side in (-1, 1):                                  # Federn
            fx0 = cx + side * (col_w + 0.02)
            fx1 = cx + side * (hw * 0.78)
            fy = body_y0
            row = 0
            while fy < body_y1 - 0.05:
                n = 3
                for i in range(n):
                    t0, t1 = i / n, (i + 1) / n
                    ax, bx = fx0 + (fx1 - fx0) * t0, fx0 + (fx1 - fx0) * t1
                    off = 0.5 * (row % 2) * (fx1 - fx0) / n
                    ax, bx = ax + off * (1 if side > 0 else -1) * 0, bx
                    mx = (ax + bx) / 2
                    colr = lapis if (i + row) % 2 else turq
                    c.poly([(ax, fy), (bx, fy), (mx, fy + 0.11)], fill=colr, outline=alpha(OUTLINE, 220), width=0.008)
                fy += 0.085
                row += 1
        # Fluegel der Nut ueber der Brust (gespreizt, in Lapis und Gold)
        wy = sh_y - 0.5
        for side in (-1, 1):
            wing = [(cx + side * 0.08, wy - 0.02), (cx + side * hw * 0.9, wy + 0.08), (cx + side * hw * 0.88, wy + 0.16), (cx + side * 0.1, wy + 0.1)]
            c.poly(wing, fill=lapis, outline=OUTLINE, width=0.012)
            for i in range(5):
                t = (i + 0.5) / 5
                c.line([(cx + side * (0.1 + (hw * 0.78) * t), wy + 0.1 - 0.02 * t), (cx + side * (0.1 + (hw * 0.78) * t) + side * 0.03, wy - 0.005 + 0.08 * t)],
                       fill=gold_l, width=0.008)
        c.ellipse(cx, wy + 0.08, 0.05, 0.035, fill=carn, outline=OUTLINE, width=0.01)                     # Skarabaeus-Sonne
        # gekreuzte Arme mit Krummstab (Heka) und Geissel (Nechech)
        ay = sh_y - 0.18
        for s_ in (-1, 1):
            arm = [(cx + s_ * hw * 0.72, ay + 0.12), (cx - s_ * 0.16, ay - 0.1), (cx - s_ * 0.22, ay - 0.02), (cx + s_ * hw * 0.72, ay + 0.22)]
            c.poly(arm, fill=shade(gold, 1.08), outline=OUTLINE, width=0.022)
            c.line([(cx + s_ * hw * 0.6, ay + 0.17), (cx - s_ * 0.1, ay - 0.02)], fill=gold_l, width=0.01)
            c.ellipse(cx - s_ * 0.19, ay - 0.06, 0.05, 0.035, fill=skin, outline=OUTLINE, width=0.014)   # Faust
            for i in range(3):
                c.line([(cx - s_ * (0.16 + i * 0.015), ay - 0.08), (cx - s_ * (0.16 + i * 0.015), ay - 0.045)], fill=shade(skin, 0.7), width=0.006)
        crook = [(cx - 0.19, ay - 0.1), (cx - 0.24, ay + 0.18), (cx - 0.3, ay + 0.26), (cx - 0.36, ay + 0.2)]
        c.line(crook, fill=OUTLINE, width=0.045)
        c.line(crook, fill=gold, width=0.025)
        for i in range(4):
            c.line([(cx - 0.2 - i * 0.012, ay - 0.04 + i * 0.06), (cx - 0.2 - i * 0.012 - 0.02, ay - 0.04 + i * 0.06 + 0.01)], fill=lapis, width=0.012)
        c.line([(cx + 0.19, ay - 0.1), (cx + 0.26, ay + 0.1)], fill=OUTLINE, width=0.045)
        c.line([(cx + 0.19, ay - 0.1), (cx + 0.26, ay + 0.1)], fill=gold, width=0.025)
        for i in range(3):
            fl = [(cx + 0.26, ay + 0.1), (cx + 0.3 + i * 0.03, ay + 0.26 + i * 0.02)]
            c.line(fl, fill=OUTLINE, width=0.03)
            c.line(fl, fill=(lapis, gold, carn)[i], width=0.015)
        # Usech-Kragen (Ringe) unter dem Kopftuch
        ky = tb1 - 0.5
        for i, colr in enumerate((gold_d, lapis, turq, carn, gold)):
            c.ellipse(cx, ky - 0.05, hw * 0.78 - i * 0.07, 0.2 - i * 0.03, fill=colr, outline=OUTLINE if i == 0 else None, width=0.02)
        for i in range(10):
            ang = math.pi + i * math.pi / 9
            c.ellipse(cx + (hw * 0.6) * math.cos(ang), ky - 0.05 + 0.15 * math.sin(ang), 0.015, 0.012, fill=gold_l)
        # Nemes-Kopftuch: Lappen bis auf die Brust, Querstreifen Lapis/Gold, Gesicht, Uraeus, Bart
        hx, hy = cx, tb1 - 0.3
        nemes = [(hx - hw * 0.55, hy - 0.4), (hx - hw * 0.35, hy - 0.42), (hx - hw * 0.4, hy - 0.05), (hx - hw * 0.72, hy + 0.08),
                 (hx - hw * 0.62, hy + 0.2), (hx - hw * 0.3, hy + 0.28), (hx, hy + 0.3), (hx + hw * 0.3, hy + 0.28), (hx + hw * 0.62, hy + 0.2),
                 (hx + hw * 0.72, hy + 0.08), (hx + hw * 0.4, hy - 0.05), (hx + hw * 0.35, hy - 0.42), (hx + hw * 0.55, hy - 0.4)]
        c.poly(nemes, fill=lapis, outline=OUTLINE, width=0.025)
        for i in range(-3, 4):                                                                         # Goldstreifen
            c.line([(hx + i * hw * 0.18, hy + 0.26 - abs(i) * 0.02), (hx + i * hw * 0.2 - (0.02 if i else 0), hy - 0.4)], fill=gold, width=0.03)
        c.rect(hx - hw * 0.55, hy - 0.42, hx - hw * 0.35, hy - 0.12, fill=gold, outline=OUTLINE, width=0.012)   # Lappen
        c.rect(hx + hw * 0.35, hy - 0.42, hx + hw * 0.55, hy - 0.12, fill=gold, outline=OUTLINE, width=0.012)
        for sx in (-1, 1):
            for i in range(4):
                c.line([(hx + sx * hw * 0.37, hy - 0.4 + i * 0.07), (hx + sx * hw * 0.53, hy - 0.4 + i * 0.07)], fill=lapis_d, width=0.012)
        c.poly([(hx - 0.17, hy + 0.12), (hx - 0.14, hy - 0.08), (hx - 0.08, hy - 0.16), (hx + 0.08, hy - 0.16), (hx + 0.14, hy - 0.08), (hx + 0.17, hy + 0.12),
                (hx + 0.1, hy + 0.17), (hx - 0.1, hy + 0.17)], fill=skin, outline=OUTLINE, width=0.022)     # Gesicht
        c.rect(hx - 0.17, hy + 0.12, hx + 0.17, hy + 0.18, fill=gold, outline=OUTLINE, width=0.015)          # Stirnband
        c.poly([(hx - 0.02, hy + 0.18), (hx + 0.02, hy + 0.18), (hx + 0.03, hy + 0.26), (hx, hy + 0.3), (hx - 0.03, hy + 0.26)], fill=gold, outline=OUTLINE, width=0.012)   # Uraeus
        c.ellipse(hx, hy + 0.27, 0.012, 0.012, fill=carn)
        for ex_ in (-0.075, 0.075):                                                                    # Kohl-Augen
            c.ellipse(hx + ex_, hy + 0.04, 0.05, 0.028, fill=(250, 246, 236, 255), outline=kohl, width=0.012)
            c.ellipse(hx + ex_, hy + 0.04, 0.02, 0.02, fill=kohl)
            c.line([(hx + ex_ + (0.05 if ex_ > 0 else -0.05), hy + 0.04), (hx + ex_ + (0.09 if ex_ > 0 else -0.09), hy + 0.055)], fill=kohl, width=0.012)
            c.line([(hx + ex_ - 0.05, hy + 0.085), (hx + ex_ + 0.05, hy + 0.095)], fill=kohl, width=0.012)     # Braue
        c.line([(hx, hy + 0.02), (hx - 0.015, hy - 0.04), (hx + 0.015, hy - 0.04)], fill=shade(skin, 0.7), width=0.01)   # Nase
        c.line([(hx - 0.04, hy - 0.08), (hx + 0.04, hy - 0.08)], fill=shade(skin, 0.6), width=0.014)                      # Mund
        c.rect(hx - 0.03, hy - 0.3, hx + 0.03, hy - 0.15, fill=lapis, outline=OUTLINE, width=0.012)                        # Zeremonialbart
        for i in range(3):
            c.line([(hx - 0.025, hy - 0.18 - i * 0.04), (hx + 0.025, hy - 0.18 - i * 0.04)], fill=gold, width=0.008)
        c.poly([(hx - 0.03, hy - 0.3), (hx + 0.03, hy - 0.3), (hx + 0.045, hy - 0.34), (hx - 0.01, hy - 0.34)], fill=lapis, outline=OUTLINE, width=0.01)
        # Kartusche am Fussende, Glanzkante links
        c.ellipse(cx, tb0 + 0.14, 0.13, 0.055, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
        for i in range(3):
            c.ellipse(cx - 0.07 + i * 0.07, tb0 + 0.14, 0.015, 0.02, fill=(lapis, carn, kohl)[i])
        c.line([(cx - hw * 0.88, sh_y - 0.2), (cx - hw * 0.56, tb1 - 0.3)], fill=alpha(gold_l, 150), width=0.02)
    elif kind == "stele":
        sand = lift("#8a6f47", 1.55)
        p.box(x0, y0, x1, y1, 0, 0.3, lift("#4c4a46", 1.7), lift("#4c4a46", 1.5))
        p.box(cx - 0.25, cy - 0.1, cx + 0.25, cy + 0.1, 0.3, 1.4, shade(sand, 1.1), sand)
        for i in range(5):
            yy = cy - 0.1 + (0.5 + i * 0.22) * K
            c.line([(cx - 0.17, yy), (cx + 0.17, yy)], fill=hexc("#3f2e1c"), width=0.02)
    elif kind == "sphinx":
        sand = lift("#8a6f47", 1.55)
        gold, blue = hexc("#d9b25c"), hexc("#2f4f8a")
        p.box(x0, y0, x1, y1, 0, 0.3, lift("#4c4a46", 1.7), lift("#4c4a46", 1.5))
        c.rect(x0 + 0.03, y0 + 0.02, x1 - 0.03, y0 + 0.07, fill=lift("#4c4a46", 1.1))
        # liegender Loewenkoerper (Kopf nach Osten): Rumpf, Hinterschenkel, Vorderpranken, Schwanz
        by0, by1 = y0 + 0.12, y1 - 0.12
        p.box(x0 + 0.15, by0, x1 - 0.5, by1, 0.3, 0.34, shade(sand, 1.1), sand)
        c.ellipse(x0 + 0.38, by0 + 0.64 * K + 0.02, 0.2, 0.15, fill=shade(sand, 1.05), outline=OUTLINE, width=0.03)
        c.line([(x0 + 0.15, by0 + 0.3 * K + 0.12), (x0 + 0.02, by0 + 0.3 * K + 0.02), (x0 + 0.06, by1 + 0.3 * K - 0.05)], fill=OUTLINE, width=0.08)
        c.line([(x0 + 0.15, by0 + 0.3 * K + 0.12), (x0 + 0.02, by0 + 0.3 * K + 0.02), (x0 + 0.06, by1 + 0.3 * K - 0.05)], fill=sand, width=0.04)
        c.line([(x0 + 0.35, by0 + 0.3 * K + 0.06), (x1 - 0.62, by0 + 0.3 * K + 0.06)], fill=shade(sand, 0.75), width=0.02)
        for py_ in (by0 + 0.03, by1 - 0.22):
            p.box(x1 - 0.42, py_, x1 - 0.05, py_ + 0.19, 0.3, 0.12, shade(sand, 1.1), sand, w=0.03)
            for tx in (x1 - 0.14, x1 - 0.09):
                c.line([(tx, py_ + 0.3 * K), (tx, py_ + 0.42 * K)], fill=shade(sand, 0.7), width=0.015)
        # Kopf mit gestreiftem Nemes-Tuch, Gesicht nach Osten, Uraeus auf der Stirn
        hx0, hx1 = x1 - 0.7, x1 - 0.24
        p.box(hx0, y0 + 0.14, hx1, y1 - 0.14, 0.3, 0.74, gold, gold)
        fz0, fz1 = y0 + 0.14 + 0.3 * K, y0 + 0.14 + 1.04 * K
        for i in range(5):
            sx0 = hx0 + 0.03 + i * (hx1 - hx0 - 0.06) / 5
            if i % 2:
                c.rect(sx0, fz0 + 0.03, sx0 + (hx1 - hx0 - 0.06) / 5, fz1 - 0.03, fill=blue)
        c.rect(hx1 - 0.15, fz0 + 0.1, hx1 - 0.02, fz1 - 0.06, fill=sand, outline=OUTLINE, width=0.02)
        c.ellipse(hx1 - 0.085, fz1 - 0.16, 0.03, 0.022, fill=(250, 246, 236, 255), outline=OUTLINE, width=0.01)
        c.ellipse(hx1 - 0.085, fz1 - 0.16, 0.012, 0.012, fill=OUTLINE)
        c.line([(hx1 - 0.11, fz0 + 0.18), (hx1 - 0.06, fz0 + 0.18)], fill=shade(sand, 0.6), width=0.015)
        c.rect(hx0 + 0.02, fz1 + 0.02, hx1 - 0.02, fz1 + 0.06, fill=shade(gold, 1.2), outline=OUTLINE, width=0.015)
        c.ellipse((hx0 + hx1) / 2, fz1 + 0.09, 0.03, 0.04, fill=blue, outline=OUTLINE, width=0.012)
        c.rect(hx1 - 0.15, fz0 + 0.02, hx1 - 0.06, fz0 + 0.1, fill=blue, outline=OUTLINE, width=0.012)
    elif kind == "staffelei":
        # Stilblatt: Holzstaffelei mit grossem Portraet ("der Stifter"), Augenweiss ohne Pupille (die
        # Pupillen sind ein eigenes Sprite, bewegt per Code). Leinwand 1,0 x 1,2 m, leicht nach hinten
        # geneigt: im Bild 1,0 x 1,2 * K. Stand: drei Beine, Standlinie y0.
        wood = lift("#6a4a2a", 1.5)
        for lx in (x0 + 0.08, x1 - 0.12):
            c.line([(lx, y0 + 0.02), (cx, y0 + 1.9 * K)], fill=OUTLINE, width=0.07)
            c.line([(lx, y0 + 0.02), (cx, y0 + 1.9 * K)], fill=wood, width=0.04)
        c.line([(cx, y1 - 0.05), (cx, y0 + 1.9 * K)], fill=OUTLINE, width=0.06)
        c.line([(cx, y1 - 0.05), (cx, y0 + 1.9 * K)], fill=shade(wood, 0.85), width=0.035)
        c.rect(x0 - 0.02, y0 + 0.55 * K - 0.04, x1 + 0.02, y0 + 0.55 * K + 0.02, fill=wood, outline=OUTLINE, width=0.02)   # Ablageleiste
        cz0, cz1 = 0.55, 1.75
        py0, py1 = y0 + cz0 * K, y0 + cz1 * K
        px0, px1 = cx - 0.5, cx + 0.5
        c.soft_shadow([(px0 + 0.05, py0 - 0.06), (px1 + 0.08, py0 - 0.06), (px1 + 0.08, py1), (px0 + 0.05, py1)], 90, 0.05)
        fr = HD.wobble_rect(px0, py0, px1, py1, amp=0.005, seed=61, step=0.05)
        c.poly(fr, fill=hexc("#c9a24c"), outline=OUTLINE, width=0.03)
        c.poly(HD.wobble_rect(px0 + 0.035, py0 + 0.03, px1 - 0.035, py1 - 0.03, amp=0.004, seed=62, step=0.05), outline=hexc("#8a6a28"), width=0.015)
        ix0, iy0, ix1, iy1 = px0 + 0.07, py0 + 0.06, px1 - 0.07, py1 - 0.06
        iw, ih = ix1 - ix0, iy1 - iy0
        mx = (ix0 + ix1) / 2
        c.rect(ix0, iy0, ix1, iy1, fill=hexc("#3a3f30"))                                         # olivgruener Fond
        c.ellipse(mx, iy0 + ih * 0.55, iw * 0.42, ih * 0.5, fill=hexc("#2c3026"))                  # Vignette
        # Schultern mit Samtjacke, Spitzenkragen, Kopf, Hut, Schnurrbart, Augen (Weiss ohne Pupille)
        c.poly([(ix0 + iw * 0.12, iy0), (ix1 - iw * 0.12, iy0), (ix1 - iw * 0.2, iy0 + ih * 0.35), (mx, iy0 + ih * 0.42), (ix0 + iw * 0.2, iy0 + ih * 0.35)],
               fill=hexc("#5b2430"), outline=OUTLINE, width=0.015)
        c.poly([(mx - iw * 0.14, iy0 + ih * 0.38), (mx + iw * 0.14, iy0 + ih * 0.38), (mx + iw * 0.08, iy0 + ih * 0.3), (mx - iw * 0.08, iy0 + ih * 0.3)],
               fill=hexc("#f4efe0"), outline=OUTLINE, width=0.012)
        c.ellipse(mx, iy0 + ih * 0.6, iw * 0.2, ih * 0.22, fill=hexc("#e8c4a0"), outline=OUTLINE, width=0.015)   # Kopf
        c.ellipse(mx - iw * 0.21, iy0 + ih * 0.6, iw * 0.03, ih * 0.05, fill=hexc("#e8c4a0"), outline=OUTLINE, width=0.01)   # Ohren
        c.ellipse(mx + iw * 0.21, iy0 + ih * 0.6, iw * 0.03, ih * 0.05, fill=hexc("#e8c4a0"), outline=OUTLINE, width=0.01)
        c.rect(mx - iw * 0.3, iy0 + ih * 0.76, mx + iw * 0.3, iy0 + ih * 0.8, fill=hexc("#2a2422"), outline=OUTLINE, width=0.012)   # Hutkrempe
        c.rect(mx - iw * 0.18, iy0 + ih * 0.79, mx + iw * 0.18, iy1 - 0.02, fill=hexc("#2a2422"), outline=OUTLINE, width=0.012)    # Zylinder
        c.rect(mx - iw * 0.18, iy0 + ih * 0.82, mx + iw * 0.18, iy0 + ih * 0.85, fill=hexc("#8e2e36"))
        c.poly([(mx - iw * 0.12, iy0 + ih * 0.5), (mx - iw * 0.02, iy0 + ih * 0.53), (mx, iy0 + ih * 0.51), (mx + iw * 0.02, iy0 + ih * 0.53), (mx + iw * 0.12, iy0 + ih * 0.5),
                (mx + iw * 0.04, iy0 + ih * 0.46), (mx - iw * 0.04, iy0 + ih * 0.46)], fill=hexc("#3a2a22"), outline=OUTLINE, width=0.01)   # Schnurrbart
        c.ellipse(mx, iy0 + ih * 0.57, iw * 0.025, ih * 0.03, fill=hexc("#d8a888"), outline=OUTLINE, width=0.008)                 # Nase
        erx, ery = iw * 0.065, ih * 0.075
        eyes = []
        for ex in (mx - iw * 0.09, mx + iw * 0.09):
            ey = iy0 + ih * 0.64
            c.ellipse(ex, ey, erx, ery, fill=hexc("#fbfaf4"), outline=OUTLINE, width=0.012)
            c.line([(ex - erx, ey + ery), (ex + erx, ey + ery + 0.01)], fill=OUTLINE, width=0.014)       # Braue
            eyes.append((round(ex, 4), round(ey, 4)))
        PORTRAIT_EYES.update({"eyes": eyes, "rx": round(erx, 4), "ry": round(ery, 4), "pupil_rx": round(erx * 0.45, 4),
                              "pupil_ry": round(ery * 0.5, 4), "base_y": round(p.base_y, 4)})
        c.text(mx, iy0 + ih * 0.06, "THE FOUNDER", 0.05, hexc("#c9a24c"))
        c.rect(px0 + 0.1, py1 + 0.02, px1 - 0.1, py1 + 0.05, fill=hexc("#c9a24c"), outline=OUTLINE, width=0.01)   # Bilderleuchte
        c.glow(mx, py1 - 0.15, 0.6, WARM, 0.3)
    elif kind == "stellwand":
        felt = lift("#5b2430", 1.55)   # Bespannung wie die Galeriewaende
        # optisch etwas breiter als die Kollision (0,2 m), sonst liest sie sich als Stange
        vx0, vx1 = x0 - 0.06, x1 + 0.06
        p.box(vx0, y0, vx1, y1, 0, 2.2, shade(felt, 1.2), felt)
        zt = 2.2 * K
        # Stilblatt: ein hochformatiges Gemaelde auf der sichtbaren Suedseite der Stellwand
        painting(c, (vx0 + vx1) / 2 - 0.11, y0 + 0.45 * K, (vx0 + vx1) / 2 + 0.11, y0 + 1.75 * K, MOTIFS[idx % len(MOTIFS)], random.Random(idx))
        c.glow((vx0 + vx1) / 2, y0 + 1.6 * K, 0.3, WARM, 0.3)
        # Bilderrahmen seitlich angedeutet (Ostseite) + Bilderleuchten auf der Krone
        rnd2 = random.Random(idx)
        for fy in (y0 + 0.35, y0 + 1.2):
            col = rnd2.choice([hexc("#3f6f9a"), hexc("#7a8a4a"), hexc("#b0603a"), hexc("#c9b27a")])
            c.rect(vx1, fy + 0.9 * K, vx1 + 0.08, fy + 0.7 + 0.9 * K, fill=hexc("#a8843c"), outline=OUTLINE, width=0.02)
            c.rect(vx1 + 0.015, fy + 0.08 + 0.9 * K, vx1 + 0.065, fy + 0.62 + 0.9 * K, fill=col)
            c.ellipse((vx0 + vx1) / 2, fy + 0.35 + zt, 0.05, 0.05, fill=WARM, outline=OUTLINE, width=0.015)
        # Messingkappen an beiden Enden der Deckflaeche + Mittelnaht
        zt = 2.2 * K
        for ey in (y0 + zt, y1 + zt - 0.12):
            c.rect(vx0 + 0.02, ey, vx1 - 0.02, ey + 0.12, fill=hexc("#c9a24c"), outline=OUTLINE, width=0.02)
        c.line([((vx0 + vx1) / 2, y0 + zt + 0.15), ((vx0 + vx1) / 2, y1 + zt - 0.15)], fill=shade(felt, 0.8), width=0.02)
        c.rect(x0 - 0.2, y0, x0, y0 + 0.08, fill=hexc("#55585f"), outline=OUTLINE, width=0.02)
        c.rect(x1, y0, x1 + 0.2, y0 + 0.08, fill=hexc("#55585f"), outline=OUTLINE, width=0.02)
    elif kind == "projektor":
        # Sternenprojektor: Rundsockel mit blauem Leuchtring, Saeule, Hantel mit zwei Sternkugeln
        metal = lift("#3a4048", 1.8)
        star = hexc("#cfe0ff")
        c.glow(cx, cy + 0.2, 1.4, hexc("#6f86c8"), 0.35)
        p.cyl(cx, cy, 0.45, 0, 0.3, shade(metal, 1.15), metal)
        c.ellipse(cx, cy + 0.3 * K, 0.36, 0.36, outline=alpha(hexc("#8fd0ff"), 220), width=0.035)
        p.cyl(cx, cy, 0.3, 0.3, 0.25, shade(metal, 1.05), shade(metal, 0.85))
        p.cyl(cx, cy, 0.1, 0.55, 0.75, metal, metal, w=0.03)
        c.line([(cx - 0.04, cy + 0.6 * K), (cx - 0.04, cy + 1.25 * K)], fill=shade(metal, 1.3), width=0.02)
        # Hantel: Querstange, an den Enden die beiden Kugeln (Nord- und Suedhimmel)
        hz = cy + 1.35 * K
        c.line([(cx - 0.5, hz + 0.05), (cx + 0.5, hz + 0.05)], fill=OUTLINE, width=0.16)
        c.line([(cx - 0.5, hz + 0.05), (cx + 0.5, hz + 0.05)], fill=metal, width=0.1)
        c.ellipse(cx, hz + 0.05, 0.16, 0.16, fill=shade(metal, 1.25), outline=OUTLINE, width=0.03)
        c.ellipse(cx - 0.03, hz + 0.09, 0.05, 0.04, fill=(255, 255, 255, 120))
        for dx in (-0.5, 0.5):
            c.ellipse(cx + dx, hz + 0.05, 0.32, 0.32, fill=shade(metal, 1.1), outline=OUTLINE, width=0.045)
            c.ellipse(cx + dx - 0.08, hz + 0.13, 0.2, 0.18, fill=shade(metal, 1.3))
            for a in range(0, 360, 40):
                c.ellipse(cx + dx + 0.2 * math.cos(math.radians(a)), hz + 0.05 + 0.2 * math.sin(math.radians(a)), 0.035, 0.035, fill=OUTLINE)
                c.ellipse(cx + dx + 0.2 * math.cos(math.radians(a)), hz + 0.05 + 0.2 * math.sin(math.radians(a)), 0.02, 0.02, fill=star)
            for a in range(20, 360, 60):
                c.ellipse(cx + dx + 0.09 * math.cos(math.radians(a)), hz + 0.05 + 0.09 * math.sin(math.radians(a)), 0.02, 0.02, fill=star)
        # Objektivkranz am Suedende der Stange
        c.ellipse(cx, hz - 0.14, 0.1, 0.07, fill=hexc("#1e2226"), outline=OUTLINE, width=0.025)
        c.ellipse(cx, hz - 0.14, 0.04, 0.03, fill=hexc("#8fd0ff"))
    elif kind == "stuetze":
        steel = lift("#3b4046", 1.8)
        p.box(x0, y0, x1, y1, 0, 3.0, shade(steel, 1.2), steel)
        for i in range(1, 8):
            yy = y0 + i * 0.4
            c.line([(x0 + 0.05, yy), (x1 - 0.05, yy + 0.08)], fill=shade(steel, 0.7), width=0.02)
        c.rect(x0 - 0.05, y0, x1 + 0.05, y0 + 0.08, fill=hexc("#7a4a2c"))
    elif kind == "dampfmaschine":
        # Stationaere Dampfmaschine (User 24.10.: "Tanks/Maschinen neu, besser erkennbar"): Ziegelsattel mit
        # Feuertuer, liegender Nietkessel mit Messingbaendern, Dampfdom, Schornstein, Manometer, Dampfrohr mit
        # rotem Ventilrad, polierter Zylinder mit Kolbenstange nach Osten zum Schwungrad, Fliehkraftregler,
        # Typenschild. Flache Farben, eine Schattenstufe, kraeftige Umrisse.
        steel = lift("#3b4046", 1.8)
        brick = lift("#7a3f30", 1.75)
        iron = lift("#2a2d33", 1.9)
        green = lift("#2f4a3a", 1.9)
        brass = hexc("#c9a24a")
        chrome = hexc("#c8d0d4")
        red = hexc("#c0392b")
        p.box(x0, y0, x1, y1, 0, 0.3, shade(steel, 1.2), steel)
        for i in range(int((x1 - x0) / 0.3)):
            c.ellipse(x0 + 0.15 + i * 0.3, y0 + 0.08, 0.02, 0.02, fill=shade(steel, 1.35))
        # Ziegelsattel unter dem Kessel (West) mit Feuertuer und Glut
        sx0, sx1 = x0 + 0.2, x0 + 2.75
        p.box(sx0, y0 + 0.25, sx1, y1 - 0.25, 0.3, 0.75, shade(brick, 1.12), brick)
        fb0 = y0 + 0.25 + 0.3 * K
        for row in range(4):
            yy = fb0 + 0.04 + row * 0.095
            c.line([(sx0 + 0.02, yy), (sx1 - 0.02, yy)], fill=shade(brick, 0.7), width=0.012)
            for i in range(9):
                bx = sx0 + 0.12 + i * 0.3 + (0.15 if row % 2 else 0)
                if bx < sx1 - 0.05:
                    c.line([(bx, yy), (bx, yy + 0.09)], fill=shade(brick, 0.7), width=0.012)
        dx0, dx1 = sx0 + 0.3, sx0 + 0.9
        c.rect(dx0, fb0 + 0.07, dx1, fb0 + 0.36, fill=iron, outline=OUTLINE, width=0.025)
        c.rect(dx0 + 0.04, fb0 + 0.11, dx1 - 0.04, fb0 + 0.32, outline=shade(iron, 1.4), width=0.01)
        c.glow((dx0 + dx1) / 2, fb0 + 0.17, 0.3, hexc("#ff8a3c"), 0.55)
        c.rect(dx0 + 0.1, fb0 + 0.13, dx1 - 0.1, fb0 + 0.2, fill=hexc("#ff8a3c"), outline=OUTLINE, width=0.012)
        c.ellipse(dx1 - 0.1, fb0 + 0.28, 0.022, 0.022, fill=brass, outline=OUTLINE, width=0.01)
        c.line([(dx1 - 0.1, fb0 + 0.28), (dx1 + 0.02, fb0 + 0.34)], fill=brass, width=0.02)
        # Typenschild am Sattel
        c.rect(sx1 - 1.3, fb0 + 0.1, sx1 - 0.25, fb0 + 0.34, fill=brass, outline=OUTLINE, width=0.02)
        c.rect(sx1 - 1.26, fb0 + 0.13, sx1 - 0.29, fb0 + 0.31, outline=shade(brass, 0.7), width=0.01)
        c.text(sx1 - 0.775, fb0 + 0.225, "VESPER 1887", 0.085, hexc("#2a2422"))
        # liegender Kessel (Achse Ost-West): Band der Hoehe 2 R sqrt(1 + K^2) um die Bildmitte cy + zc K
        R = 0.6
        zc = 0.3 + 0.75 + R
        kx0, kx1 = sx0 + 0.05, sx1 - 0.05
        mid = cy + zc * K
        half = R * math.sqrt(1 + K * K)
        lo, hi = mid - half, mid + half
        c.rect(kx0, lo, kx1, hi, fill=green, outline=OUTLINE)
        c.rect(kx0 + 0.03, lo + 0.03, kx1 - 0.03, lo + (hi - lo) * 0.3, fill=shade(green, 0.72))
        c.rect(kx0 + 0.03, lo + (hi - lo) * 0.66, kx1 - 0.03, hi - 0.03, fill=shade(green, 1.2))
        c.line([(kx0 + 0.06, lo + (hi - lo) * 0.82), (kx1 - 0.06, lo + (hi - lo) * 0.82)], fill=shade(green, 1.45), width=0.035)
        for i in range(int((kx1 - kx0) / 0.2)):                                        # Nietreihen
            rx = kx0 + 0.12 + i * 0.2
            c.ellipse(rx, lo + 0.08, 0.016, 0.016, fill=shade(green, 1.4))
            c.ellipse(rx, hi - 0.1, 0.016, 0.016, fill=shade(green, 0.6))
        for bx in (kx0 + 0.55, kx0 + 1.3, kx0 + 2.05):                                  # Messingbaender
            c.rect(bx - 0.06, lo - 0.02, bx + 0.06, hi + 0.02, fill=brass, outline=OUTLINE, width=0.02)
            c.line([(bx - 0.03, lo + 0.05), (bx - 0.03, hi - 0.05)], fill=shade(brass, 1.35), width=0.012)
        # Kesselboden West (Nietflansch) und Stirnwand Ost
        c.ellipse(kx0, mid, 0.12, half, fill=shade(green, 0.85), outline=OUTLINE, width=0.035)
        c.ellipse(kx0, mid, 0.07, half - 0.1, fill=shade(green, 1.05), outline=shade(green, 0.6), width=0.015)
        for a in range(0, 360, 30):
            c.ellipse(kx0 + 0.09 * math.cos(math.radians(a)), mid + (half - 0.05) * math.sin(math.radians(a)), 0.014, 0.014, fill=shade(green, 1.4))
        c.rect(kx1 - 0.08, lo - 0.02, kx1 + 0.06, hi + 0.02, fill=shade(steel, 0.9), outline=OUTLINE, width=0.03)
        # Manometer an der Kesselfront
        gx, gy = kx0 + 1.68, mid + 0.02
        c.ellipse(gx, gy, 0.2, 0.2, fill=brass, outline=OUTLINE, width=0.025)
        c.ellipse(gx, gy, 0.15, 0.15, fill=hexc("#f2ecd8"), outline=OUTLINE, width=0.015)
        for a in range(-200, 30, 23):
            c.line([(gx + 0.12 * math.cos(math.radians(a)), gy + 0.12 * math.sin(math.radians(a))),
                    (gx + 0.14 * math.cos(math.radians(a)), gy + 0.14 * math.sin(math.radians(a)))], fill=hexc("#2a2422"), width=0.01)
        c.line([(gx + 0.1 * math.cos(math.radians(-40)), gy + 0.1 * math.sin(math.radians(-40))),
                (gx + 0.14 * math.cos(math.radians(-40)), gy + 0.14 * math.sin(math.radians(-40)))], fill=red, width=0.025)
        c.line([(gx, gy), (gx + 0.11 * math.cos(math.radians(-115)), gy + 0.11 * math.sin(math.radians(-115)))], fill=hexc("#2a2422"), width=0.015)
        c.ellipse(gx, gy, 0.02, 0.02, fill=brass, outline=OUTLINE, width=0.008)
        # Dampfdom mit Sicherheitsventil, Schornstein mit Krone (sitzen auf dem Kesselruecken)
        dome_x = kx0 + 1.3
        dz = zc + R - 0.12
        p.cyl(dome_x, cy, 0.26, dz, 0.4, shade(brass, 1.15), brass, ry=0.13)
        c.ellipse(dome_x, cy + (dz + 0.4) * K, 0.1, 0.05, fill=shade(brass, 0.8), outline=OUTLINE, width=0.015)
        c.line([(dome_x - 0.3, cy + (dz + 0.62) * K), (dome_x + 0.22, cy + (dz + 0.52) * K)], fill=OUTLINE, width=0.05)
        c.line([(dome_x - 0.3, cy + (dz + 0.62) * K), (dome_x + 0.22, cy + (dz + 0.52) * K)], fill=brass, width=0.025)
        c.ellipse(dome_x + 0.22, cy + (dz + 0.52) * K, 0.045, 0.045, fill=brass, outline=OUTLINE, width=0.015)
        ch_x = kx0 + 0.45
        p.cyl(ch_x, cy + 0.1, 0.2, dz, 1.55, iron, iron, ry=0.1)
        c.rect(ch_x - 0.24, cy + 0.1 + (dz + 1.4) * K, ch_x + 0.24, cy + 0.1 + (dz + 1.52) * K, fill=brass, outline=OUTLINE, width=0.025)
        c.ellipse(ch_x, cy + 0.1 + (dz + 1.55) * K, 0.2, 0.1, fill=hexc("#1e1e1e"), outline=OUTLINE, width=0.03)
        c.ellipse(ch_x, cy + 0.1 + (dz + 1.55) * K, 0.13, 0.06, fill=hexc("#0e0e10"))
        c.line([(ch_x - 0.12, cy + 0.1 + (dz + 0.1) * K), (ch_x - 0.12, cy + 0.1 + (dz + 1.35) * K)], fill=shade(iron, 1.5), width=0.02)
        # Dampfrohr vom Dom nach Osten zum Zylinder, mit rotem Ventilrad
        py_ = cy + (zc + R + 0.1) * K
        pipe = [(dome_x + 0.26, py_), (kx1 + 0.5, py_), (kx1 + 0.5, cy + 1.35 * K)]
        c.line(pipe, fill=OUTLINE, width=0.1)
        c.line(pipe, fill=shade(steel, 1.1), width=0.06)
        c.line([(dome_x + 0.3, py_ + 0.012), (kx1 + 0.46, py_ + 0.012)], fill=shade(steel, 1.5), width=0.012)
        vx_ = kx1 - 0.2
        c.ellipse(vx_, py_ + 0.15, 0.11, 0.11, fill=None, outline=OUTLINE, width=0.06)
        c.ellipse(vx_, py_ + 0.15, 0.11, 0.11, fill=None, outline=red, width=0.03)
        for a in range(0, 180, 60):
            c.line([(vx_ - 0.1 * math.cos(math.radians(a)), py_ + 0.15 - 0.1 * math.sin(math.radians(a))),
                    (vx_ + 0.1 * math.cos(math.radians(a)), py_ + 0.15 + 0.1 * math.sin(math.radians(a)))], fill=red, width=0.02)
        c.line([(vx_, py_), (vx_, py_ + 0.15)], fill=shade(steel, 0.8), width=0.03)
        c.ellipse(vx_, py_ + 0.15, 0.025, 0.025, fill=brass, outline=OUTLINE, width=0.01)
        # Zylinder auf Sockel (Ost), Kolbenstange und Kreuzkopffuehrung nach Osten
        zx0, zx1 = x1 - 1.35, x1 - 0.35
        p.box(zx0 - 0.1, y0 + 0.5, zx1 + 0.1, y1 - 0.5, 0.3, 0.3, shade(steel, 1.15), steel)
        Rz = 0.34
        zcz = 0.6 + Rz
        zmid = cy + zcz * K
        zh = Rz * math.sqrt(1 + K * K)
        c.rect(zx0, zmid - zh, zx1, zmid + zh, fill=chrome, outline=OUTLINE)
        c.rect(zx0 + 0.03, zmid - zh + 0.03, zx1 - 0.03, zmid - zh * 0.4, fill=shade(chrome, 0.72))
        c.line([(zx0 + 0.05, zmid + zh * 0.55), (zx1 - 0.05, zmid + zh * 0.55)], fill=(255, 255, 255, 255), width=0.03)
        for hx in (zx0, zx1):                                                               # Zylinderdeckel mit Schrauben
            c.rect(hx - 0.07, zmid - zh - 0.03, hx + 0.07, zmid + zh + 0.03, fill=shade(steel, 0.95), outline=OUTLINE, width=0.03)
            for k_ in range(5):
                c.ellipse(hx, zmid - zh + 0.05 + k_ * (2 * zh - 0.1) / 4, 0.018, 0.018, fill=shade(steel, 1.5))
        rod_y = zmid
        c.line([(zx1 + 0.07, rod_y), (x1 + 0.05, rod_y)], fill=OUTLINE, width=0.09)
        c.line([(zx1 + 0.07, rod_y), (x1 + 0.05, rod_y)], fill=chrome, width=0.05)
        c.rect(x1 - 0.3, rod_y - 0.1, x1 - 0.05, rod_y + 0.1, fill=shade(steel, 1.0), outline=OUTLINE, width=0.025)    # Kreuzkopf
        c.line([(x1 - 0.32, rod_y - 0.13), (x1 + 0.02, rod_y - 0.13)], fill=OUTLINE, width=0.035)             # Gleitbahn
        c.line([(x1 - 0.32, rod_y + 0.13), (x1 + 0.02, rod_y + 0.13)], fill=OUTLINE, width=0.035)
        # Fliehkraftregler auf dem Zylinder
        rgx = zx0 + 0.35
        rbase = zmid + zh
        c.line([(rgx, rbase), (rgx, rbase + 0.42)], fill=OUTLINE, width=0.045)
        c.line([(rgx, rbase), (rgx, rbase + 0.42)], fill=brass, width=0.022)
        for s in (-1, 1):
            c.line([(rgx, rbase + 0.4), (rgx + s * 0.16, rbase + 0.2)], fill=OUTLINE, width=0.035)
            c.line([(rgx, rbase + 0.4), (rgx + s * 0.16, rbase + 0.2)], fill=brass, width=0.015)
            c.ellipse(rgx + s * 0.16, rbase + 0.19, 0.055, 0.055, fill=brass, outline=OUTLINE, width=0.015)
            c.ellipse(rgx + s * 0.16 - 0.015, rbase + 0.21, 0.015, 0.012, fill=(255, 245, 210, 255))
        c.ellipse(rgx, rbase + 0.42, 0.03, 0.03, fill=brass, outline=OUTLINE, width=0.012)
        # Abdampfrohr hinten rechts
        c.line([(zx1 - 0.2, cy + 0.6 + zcz * K), (zx1 - 0.2, y1 + 1.5 * K), (zx1 + 0.3, y1 + 1.5 * K)], fill=OUTLINE, width=0.09)
        c.line([(zx1 - 0.2, cy + 0.6 + zcz * K), (zx1 - 0.2, y1 + 1.5 * K), (zx1 + 0.3, y1 + 1.5 * K)], fill=shade(steel, 1.0), width=0.05)
    elif kind == "schwungrad":
        # Grosses Schwungrad (User 24.10.: "Rad neu") zwischen zwei gusseisernen Lagerboecken, Achse Nord-Sued.
        # Die Scheibe steht in der Ost-West-Ebene; sie wird als Ellipse mit ry = 0,78 r gezeichnet (steiler
        # als die reine Projektion 0,55 r, damit das Rad als Rad lesbar bleibt). Kurbelzapfen mit Pleuel zum
        # Kreuzkopf der Dampfmaschine (Westen), Treibriemen zur Riemenscheibe des Dynamos (Osten).
        green = lift("#2f4a3a", 1.9)
        steel = lift("#3b4046", 1.8)
        iron = lift("#2a2d33", 1.9)
        brass = hexc("#c9a24a")
        chrome = hexc("#c8d0d4")
        leather = lift("#5a3a22", 1.7)
        r = x1 - cx - 0.06
        z0 = 1.05
        wy = cy + z0 * K
        ry = r * 0.78

        def pedestal(py0, py1, front=True):
            p.box(cx - 0.26, py0, cx + 0.26, py1, 0, z0 - 0.12, shade(iron, 1.2), iron, w=0.035)
            fb = py0
            c.poly([(cx - 0.3, fb + 0.02), (cx + 0.3, fb + 0.02), (cx + 0.3, fb + 0.1), (cx - 0.3, fb + 0.1)], fill=shade(iron, 0.75), outline=OUTLINE, width=0.02)
            c.poly([(cx - 0.2, fb + 0.1), (cx + 0.2, fb + 0.1), (cx + 0.12, fb + (z0 - 0.2) * K), (cx - 0.12, fb + (z0 - 0.2) * K)], fill=shade(iron, 0.85))
            c.ellipse(cx, fb + (z0 - 0.08) * K, 0.14, 0.11, fill=shade(iron, 1.15), outline=OUTLINE, width=0.03)   # Lagerschale
            if front:
                c.ellipse(cx, fb + (z0 - 0.08) * K, 0.07, 0.06, fill=brass, outline=OUTLINE, width=0.02)
                c.ellipse(cx - 0.02, fb + (z0 - 0.08) * K + 0.015, 0.02, 0.015, fill=(255, 245, 210, 255))
                c.ellipse(cx, fb + (z0 + 0.1) * K, 0.03, 0.03, fill=brass, outline=OUTLINE, width=0.012)           # Oeler

        pedestal(cy + 0.28, cy + 0.56, front=False)
        # Riemenscheibe des Dynamos (Osten) und Treibriemen, hinter dem Rad
        px_, pz = x1 + 0.72, 1.1
        pyy = cy + 0.75 + pz * K            # Dynamoachse: 1,25 m noerdlich der Turbosatz-Standlinie (y0 + 0,5 = cy - 0,5)
        pr = 0.3
        belt = alpha(leather, 255)
        c.poly([(cx, wy + ry - 0.02), (px_, pyy + pr * 0.78 - 0.015), (px_, pyy + pr * 0.78 + 0.05), (cx + 0.2, wy + ry + 0.06)], fill=belt, outline=OUTLINE, width=0.02)
        c.poly([(cx, wy - ry + 0.02), (px_, pyy - pr * 0.78 + 0.015), (px_, pyy - pr * 0.78 - 0.05), (cx + 0.2, wy - ry - 0.06)], fill=belt, outline=OUTLINE, width=0.02)
        c.ellipse(px_, pyy, pr, pr * 0.78, fill=steel, outline=OUTLINE, width=0.035)
        c.ellipse(px_, pyy, pr - 0.07, (pr - 0.07) * 0.78, fill=shade(steel, 0.8), outline=OUTLINE, width=0.015)
        c.ellipse(px_, pyy, 0.05, 0.04, fill=brass, outline=OUTLINE, width=0.012)
        # Rad: Felge, Speichen, Nabe
        c.ellipse(cx, wy, r, ry, fill=None, outline=OUTLINE, width=0.3)
        c.ellipse(cx, wy, r, ry, fill=None, outline=shade(green, 0.92), width=0.2)
        c.ellipse(cx, wy + 0.025, r - 0.02, ry - 0.02, fill=None, outline=shade(green, 1.22), width=0.03)
        c.ellipse(cx, wy - 0.025, r - 0.03, ry - 0.03, fill=None, outline=shade(green, 0.7), width=0.03)
        for a in range(0, 360, 45):
            ca, sa = math.cos(math.radians(a + 22)), math.sin(math.radians(a + 22))
            ex, ey = cx + (r - 0.12) * ca, wy + (ry - 0.1) * sa
            nx, ny = -sa * 0.045, ca * 0.045
            c.poly([(cx + nx * 0.6, wy + ny * 0.6), (ex + nx * 0.5, ey + ny * 0.5), (ex - nx * 0.5, ey - ny * 0.5), (cx - nx * 0.6, wy - ny * 0.6)],
                   fill=green, outline=OUTLINE, width=0.022)
            c.line([(cx + nx * 0.3, wy + ny * 0.3), (ex + nx * 0.25, ey + ny * 0.25)], fill=shade(green, 1.25), width=0.012)
        # Gegengewicht an der Felge (dem Kurbelzapfen gegenueber)
        ca_, sa_ = math.cos(math.radians(250)), math.sin(math.radians(250))
        c.poly([(cx + (r - 0.3) * math.cos(math.radians(235)), wy + (ry - 0.25) * math.sin(math.radians(235))),
                (cx + (r - 0.08) * math.cos(math.radians(235)), wy + (ry - 0.06) * math.sin(math.radians(235))),
                (cx + (r - 0.08) * math.cos(math.radians(265)), wy + (ry - 0.06) * math.sin(math.radians(265))),
                (cx + (r - 0.3) * math.cos(math.radians(265)), wy + (ry - 0.25) * math.sin(math.radians(265)))], fill=shade(green, 0.85), outline=OUTLINE, width=0.022)
        c.ellipse(cx, wy, 0.24, 0.2, fill=steel, outline=OUTLINE, width=0.035)
        c.ellipse(cx, wy, 0.17, 0.14, fill=shade(steel, 1.15), outline=shade(steel, 0.7), width=0.012)
        for a in range(0, 360, 60):
            c.ellipse(cx + 0.2 * math.cos(math.radians(a + 30)), wy + 0.17 * math.sin(math.radians(a + 30)), 0.018, 0.018, fill=shade(steel, 0.6))
        c.ellipse(cx, wy, 0.07, 0.06, fill=brass, outline=OUTLINE, width=0.02)
        c.ellipse(cx - 0.02, wy + 0.015, 0.02, 0.015, fill=(255, 245, 210, 255))
        # Kurbelzapfen und Pleuel nach Westen zum Kreuzkopf (x1 der Dampfmaschine = cx - 0,6)
        kx, ky = cx + (r - 0.22) * math.cos(math.radians(70)), wy + (ry - 0.18) * math.sin(math.radians(70))
        rod_end = (x0 - 0.05, cy + 0.94 * K)
        c.line([(kx, ky), rod_end], fill=OUTLINE, width=0.12)
        c.line([(kx, ky), rod_end], fill=chrome, width=0.07)
        c.line([(kx - 0.05, ky + 0.02), (rod_end[0] + 0.1, rod_end[1] + 0.02)], fill=(255, 255, 255, 255), width=0.015)
        c.ellipse(kx, ky, 0.08, 0.07, fill=steel, outline=OUTLINE, width=0.025)
        c.ellipse(kx, ky, 0.035, 0.03, fill=brass, outline=OUTLINE, width=0.012)
        pedestal(cy - 0.56, cy - 0.28, front=True)
        # Achsende vorn mit Mutter, Oelkanne am Fuss
        c.rect(cx - 0.34, cy - 0.6, cx + 0.34, cy - 0.5, fill=shade(iron, 0.8), outline=OUTLINE, width=0.025)
        tool_oilcan(c, cx + 0.5, cy - 0.5)
    elif kind == "oldtimer":
        # offener Tourenwagen, Kuehler nach Osten: Kabine mit Sitzbaenken, lange Motorhaube,
        # Windschutzscheibe, Speichenraeder mit Kotfluegeln auf der Suedseite
        red = lift("#7a2a2a", 1.9)
        dark = hexc("#2a2422")
        chrome = hexc("#d8dde0")
        leather = lift("#4a3222", 1.9)
        cab1 = x1 - 1.75
        p.box(x0 + 0.35, y0 + 0.3, x1 - 0.35, y1 - 0.3, 0.2, 0.12, dark, dark, w=0.035)
        p.box(x0 + 0.15, y0 + 0.2, cab1, y1 - 0.2, 0.3, 0.62, shade(red, 1.12), red)
        p.box(cab1, y0 + 0.4, x1 - 0.12, y1 - 0.4, 0.3, 0.46, shade(red, 1.12), red)
        # Sitzbaenke (von oben) + Reserverad am Heck
        zt = 0.92 * K
        for sx in (x0 + 0.4, x0 + 1.4):
            c.rect(sx, y0 + 0.36 + zt, sx + 0.75, y1 - 0.36 + zt, fill=leather, outline=OUTLINE, width=0.03)
            c.rect(sx, y0 + 0.36 + zt, sx + 0.16, y1 - 0.36 + zt, fill=shade(leather, 0.8), outline=OUTLINE, width=0.025)
            c.line([(sx + 0.3, y0 + 0.45 + zt), (sx + 0.3, y1 - 0.45 + zt)], fill=shade(leather, 0.75), width=0.02)
        c.ellipse(x0 + 0.12, cy + zt * 0.7, 0.12, 0.4, fill=hexc("#1e1e1e"), outline=OUTLINE, width=0.03)
        # Motorhaube: Luftschlitze, Mittelnaht, Kuehlergrill + Kuehlerfigur
        zh = 0.76 * K
        c.line([(cab1 + 0.1, cy + zh), (x1 - 0.3, cy + zh)], fill=shade(red, 0.75), width=0.025)
        for i in range(5):
            lx = cab1 + 0.3 + i * 0.18
            for side in (-1, 1):
                c.line([(lx, cy + zh + side * 0.25), (lx, cy + zh + side * 0.5)], fill=shade(red, 0.7), width=0.02)
        c.rect(x1 - 0.3, y0 + 0.4 + zh, x1 - 0.12, y1 - 0.4 + zh, fill=chrome, outline=OUTLINE, width=0.03)
        c.ellipse(x1 - 0.21, cy + zh + 0.05, 0.04, 0.06, fill=hexc("#d9b25c"), outline=OUTLINE, width=0.015)
        # Windschutzscheibe
        p.box(cab1 - 0.06, y0 + 0.35, cab1 + 0.04, y1 - 0.35, 0.92, 0.35, alpha(hexc("#dff3ff"), 120), alpha(hexc("#bfe3f5"), 110),
              ol=chrome, w=0.03, glass=True)
        # Zierleiste, Scheinwerfer
        c.line([(x0 + 0.2, y0 + 0.2 + 0.5 * K), (cab1, y0 + 0.2 + 0.5 * K)], fill=chrome, width=0.035)
        c.ellipse(x1 - 0.22, y0 + 0.4 + 0.62 * K, 0.11, 0.11, fill=hexc("#ffd9a0"), outline=OUTLINE, width=0.025)
        # Kotfluegel + Speichenraeder (Suedseite, vor der Karosserie)
        for wx in (x0 + 0.75, x1 - 0.85):
            c.ellipse(wx, y0 + 0.3, 0.44, 0.3, fill=shade(red, 0.8), outline=OUTLINE, width=0.035)
            c.ellipse(wx, y0 + 0.22, 0.33, 0.33, fill=hexc("#1e1e1e"), outline=OUTLINE, width=0.04)
            c.ellipse(wx, y0 + 0.22, 0.2, 0.2, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.02)
            for a in range(0, 180, 30):
                ca, sa = math.cos(math.radians(a)) * 0.19, math.sin(math.radians(a)) * 0.19
                c.line([(wx - ca, y0 + 0.22 - sa), (wx + ca, y0 + 0.22 + sa)], fill=hexc("#8a2a2a"), width=0.018)
            c.ellipse(wx, y0 + 0.22, 0.06, 0.06, fill=chrome, outline=OUTLINE, width=0.015)
    elif kind == "turbine":
        # Turbosatz (User 24.10.: "besser erkennbar"): auf dem Nietsockel steht westlich der Dynamo (dunkelgruener
        # Zylinder mit Kuehlrippen, Messingstirn, Riemenscheibe fuer den Treibriemen vom Schwungrad, Klemmbrett
        # mit Kabeln), gekuppelt an das Turbinengehaeuse (Stahlzylinder mit Schraubflansch, Schneckeneinlass
        # mit grossem Ventilrad, Abdampfkruemmer), davor Manometertafel, Steuerhebel und Typenschild.
        steel = lift("#7b8288", 1.35)
        dark = lift("#3b4046", 1.75)
        green = lift("#2f4a3a", 1.9)
        brass = hexc("#c9a24a")
        chrome = hexc("#c8d0d4")
        red = hexc("#c0392b")
        p.box(x0, y0, x1, y1, 0, 0.35, shade(dark, 1.12), dark)
        for i in range(int((x1 - x0) / 0.3)):
            c.ellipse(x0 + 0.15 + i * 0.3, y0 + 0.08, 0.02, 0.02, fill=shade(dark, 1.4))
        c.rect(x0 + 0.02, y0 + 0.02, x1 - 0.02, y0 + 0.11, fill=shade(dark, 0.7))
        hazard_y = y0 + 0.35 * K - 0.08
        for i in range(int((x1 - x0) / 0.24)):                                             # Warnstreifen am Sockelrand
            hx = x0 + 0.05 + i * 0.24
            c.poly([(hx, hazard_y), (hx + 0.12, hazard_y), (hx + 0.18, hazard_y + 0.06), (hx + 0.06, hazard_y + 0.06)], fill=hexc("#d4b13c"))
        # Dynamo (West); die Maschinenachse liegt 1,25 m noerdlich der Standlinie (nah am Schwungrad, der Treibriemen
        # aus dem Schwungrad-Sprite zielt auf die Riemenscheibe bei x0 + 0,72)
        cy = y0 + 1.25
        gx0, gx1 = x0 + 0.35, x0 + 2.0
        Rg = 0.55
        zg = 0.35 + 0.2 + Rg
        gmid = cy + zg * K
        gh = Rg * math.sqrt(1 + K * K)
        p.box(gx0 - 0.05, cy - 0.5, gx1 + 0.05, cy + 0.5, 0.35, 0.2, shade(dark, 1.15), dark, w=0.03)
        c.rect(gx0, gmid - gh, gx1, gmid + gh, fill=green, outline=OUTLINE)
        c.rect(gx0 + 0.03, gmid - gh + 0.03, gx1 - 0.03, gmid - gh * 0.42, fill=shade(green, 0.72))
        c.rect(gx0 + 0.03, gmid + gh * 0.35, gx1 - 0.03, gmid + gh - 0.03, fill=shade(green, 1.2))
        for i in range(int((gx1 - gx0 - 0.4) / 0.11)):                                     # Kuehlrippen
            fx = gx0 + 0.25 + i * 0.11
            c.line([(fx, gmid - gh + 0.06), (fx, gmid + gh - 0.06)], fill=shade(green, 0.6), width=0.018)
        c.line([(gx0 + 0.06, gmid + gh * 0.72), (gx1 - 0.06, gmid + gh * 0.72)], fill=shade(green, 1.45), width=0.03)
        for hx in (gx0, gx1):                                                               # Lagerschilde aus Messing
            c.rect(hx - 0.08, gmid - gh - 0.03, hx + 0.08, gmid + gh + 0.03, fill=brass, outline=OUTLINE, width=0.03)
            for k_ in range(4):
                c.ellipse(hx, gmid - gh + 0.08 + k_ * (2 * gh - 0.16) / 3, 0.02, 0.02, fill=shade(brass, 0.6))
        c.ellipse(gx0 - 0.08, gmid, 0.1, gh * 0.75, fill=shade(brass, 0.9), outline=OUTLINE, width=0.03)          # Stirnseite West
        c.ellipse(gx0 - 0.08, gmid, 0.05, gh * 0.4, fill=shade(green, 0.8), outline=OUTLINE, width=0.015)
        # Welle und Riemenscheibe (x0 + 0,72 = Riemenziel aus dem Schwungrad-Sprite)
        c.line([(gx0 - 0.15, gmid), (x0 + 0.6, gmid)], fill=OUTLINE, width=0.09)
        c.line([(gx0 - 0.15, gmid), (x0 + 0.6, gmid)], fill=chrome, width=0.05)
        # Klemmbrett oben mit zwei Messingklemmen und Kabeln zur Schalttafel vorn
        bz = zg + Rg - 0.1
        p.box(gx0 + 0.5, cy - 0.18, gx0 + 1.1, cy + 0.18, bz, 0.22, hexc("#1e1e22"), hexc("#2a2a30"), w=0.025)
        for tx in (gx0 + 0.66, gx0 + 0.94):
            c.ellipse(tx, cy - 0.18 + (bz + 0.22) * K + 0.05, 0.045, 0.03, fill=brass, outline=OUTLINE, width=0.015)
        cab0 = (gx0 + 0.66, cy - 0.18 + (bz + 0.22) * K + 0.05)
        cab1 = (gx0 + 0.94, cy - 0.18 + (bz + 0.22) * K + 0.05)
        panel_x0, panel_x1 = x0 + 0.5, x0 + 1.4
        panel_fb = y0 + 0.35 * K
        for cab, col, tx in ((cab0, hexc("#b03a2a"), panel_x0 + 0.2), (cab1, hexc("#2a2a30"), panel_x0 + 0.45)):
            pts = bezier(cab, (cab[0] - 0.35, cab[1] - 0.55), (tx, panel_fb + 0.62), 10)
            c.line(pts, fill=OUTLINE, width=0.045)
            c.line(pts, fill=col, width=0.025)
        # Marmor-Schalttafel vorn am Sockel: Messerschalter, zwei Messinstrumente
        c.rect(panel_x0, panel_fb + 0.02, panel_x1, panel_fb + 0.62, fill=hexc("#e4e0d6"), outline=OUTLINE, width=0.025)
        c.line([(panel_x0 + 0.1, panel_fb + 0.5), (panel_x1 - 0.2, panel_fb + 0.15)], fill=alpha(hexc("#9a9690"), 140), width=0.012)
        for mx in (panel_x0 + 0.24, panel_x0 + 0.66):
            c.ellipse(mx, panel_fb + 0.42, 0.11, 0.11, fill=brass, outline=OUTLINE, width=0.02)
            c.ellipse(mx, panel_fb + 0.42, 0.08, 0.08, fill=hexc("#f2ecd8"), outline=OUTLINE, width=0.012)
            c.line([(mx, panel_fb + 0.42), (mx + 0.055, panel_fb + 0.47)], fill=hexc("#2a2422"), width=0.012)
        c.rect(panel_x0 + 0.38, panel_fb + 0.12, panel_x0 + 0.52, panel_fb + 0.3, fill=hexc("#1e1e22"), outline=OUTLINE, width=0.015)
        c.line([(panel_x0 + 0.45, panel_fb + 0.14), (panel_x0 + 0.58, panel_fb + 0.3)], fill=OUTLINE, width=0.04)
        c.line([(panel_x0 + 0.45, panel_fb + 0.14), (panel_x0 + 0.58, panel_fb + 0.3)], fill=brass, width=0.02)
        c.ellipse(panel_x0 + 0.58, panel_fb + 0.3, 0.03, 0.03, fill=hexc("#1e1e22"), outline=OUTLINE, width=0.01)
        # Kupplung
        cx0 = gx1 + 0.1
        c.rect(cx0, gmid - 0.22, cx0 + 0.3, gmid + 0.22, fill=steel, outline=OUTLINE, width=0.03)
        for k_ in range(3):
            c.line([(cx0 + 0.05 + k_ * 0.1, gmid - 0.18), (cx0 + 0.05 + k_ * 0.1, gmid + 0.18)], fill=shade(steel, 0.65), width=0.015)
        # Turbinengehaeuse (Ost)
        tx0, tx1 = cx0 + 0.3, x1 - 0.25
        Rt = 0.72
        zt_ = 0.35 + Rt
        tmid = cy + zt_ * K
        th = Rt * math.sqrt(1 + K * K)
        c.rect(tx0, tmid - th, tx1, tmid + th, fill=steel, outline=OUTLINE)
        c.rect(tx0 + 0.03, tmid - th + 0.03, tx1 - 0.03, tmid - th * 0.45, fill=shade(steel, 0.75))
        c.rect(tx0 + 0.03, tmid + th * 0.4, tx1 - 0.03, tmid + th - 0.03, fill=shade(steel, 1.18))
        c.line([(tx0 + 0.06, tmid + th * 0.75), (tx1 - 0.06, tmid + th * 0.75)], fill=shade(steel, 1.4), width=0.035)
        c.rect(tx0 + 0.02, tmid - 0.06, tx1 - 0.02, tmid + 0.06, fill=shade(steel, 0.9), outline=OUTLINE, width=0.02)   # Teilfugenflansch
        for i in range(int((tx1 - tx0) / 0.17)):
            bx = tx0 + 0.1 + i * 0.17
            c.ellipse(bx, tmid, 0.025, 0.025, fill=shade(steel, 1.3), outline=OUTLINE, width=0.01)
        for fx in (tx0 + 0.1, (tx0 + tx1) / 2, tx1 - 0.1):                                    # Flanschringe
            c.rect(fx - 0.07, tmid - th - 0.04, fx + 0.07, tmid + th + 0.04, fill=shade(steel, 0.7), outline=OUTLINE, width=0.025)
            for k_ in range(5):
                c.ellipse(fx, tmid - th + 0.05 + k_ * (2 * th - 0.1) / 4, 0.02, 0.02, fill=chrome)
        c.ellipse(tx1, tmid, 0.14, th * 0.9, fill=shade(steel, 0.8), outline=OUTLINE, width=0.035)              # Stirnwand Ost
        c.ellipse(tx1, tmid, 0.07, th * 0.45, fill=shade(steel, 0.55), outline=OUTLINE, width=0.015)
        # Schneckeneinlass oben mit Ventilrad, Abdampfkruemmer nach hinten
        ix = (tx0 + tx1) / 2 - 0.15
        p.cyl(ix, cy, 0.3, zt_ + Rt - 0.15, 0.3, shade(steel, 1.1), shade(steel, 0.9), ry=0.15)
        pz = cy + (zt_ + Rt + 0.15) * K
        pipe = [(ix, pz), (ix, pz + 0.55), (ix + 0.9, pz + 0.55), (ix + 0.9, pz + 0.95)]
        c.line(pipe, fill=OUTLINE, width=0.16)
        c.line(pipe, fill=shade(steel, 1.0), width=0.11)
        c.line([(ix - 0.03, pz + 0.05), (ix - 0.03, pz + 0.5), (ix + 0.86, pz + 0.5)], fill=shade(steel, 1.4), width=0.018)
        c.rect(ix + 0.78, pz + 0.9, ix + 1.02, pz + 1.0, fill=shade(steel, 0.75), outline=OUTLINE, width=0.025)
        vx_, vy_ = ix + 0.45, pz + 0.55
        c.line([(vx_, vy_), (vx_, vy_ + 0.2)], fill=shade(steel, 0.8), width=0.04)
        c.ellipse(vx_, vy_ + 0.24, 0.16, 0.16, fill=None, outline=OUTLINE, width=0.07)
        c.ellipse(vx_, vy_ + 0.24, 0.16, 0.16, fill=None, outline=red, width=0.04)
        for a in range(0, 180, 45):
            c.line([(vx_ - 0.15 * math.cos(math.radians(a)), vy_ + 0.24 - 0.15 * math.sin(math.radians(a))),
                    (vx_ + 0.15 * math.cos(math.radians(a)), vy_ + 0.24 + 0.15 * math.sin(math.radians(a)))], fill=red, width=0.025)
        c.ellipse(vx_, vy_ + 0.24, 0.035, 0.035, fill=brass, outline=OUTLINE, width=0.012)
        ex_ = tx1 - 0.35
        c.line([(ex_, tmid + th), (ex_, y1 + 1.3 * K), (ex_ + 0.45, y1 + 1.3 * K)], fill=OUTLINE, width=0.12)
        c.line([(ex_, tmid + th), (ex_, y1 + 1.3 * K), (ex_ + 0.45, y1 + 1.3 * K)], fill=shade(steel, 0.9), width=0.08)
        # Manometertafel an der Turbinenfront, Typenschild, Steuerhebel
        mx = tx0 + 0.55
        c.rect(mx - 0.32, tmid - 0.5, mx + 0.32, tmid - 0.12, fill=hexc("#2a2a30"), outline=OUTLINE, width=0.02)
        for k_, gxx in enumerate((mx - 0.16, mx + 0.16)):
            c.ellipse(gxx, tmid - 0.31, 0.13, 0.13, fill=brass, outline=OUTLINE, width=0.02)
            c.ellipse(gxx, tmid - 0.31, 0.1, 0.1, fill=hexc("#f2ecd8"), outline=OUTLINE, width=0.012)
            for a in range(-200, 30, 30):
                c.line([(gxx + 0.08 * math.cos(math.radians(a)), tmid - 0.31 + 0.08 * math.sin(math.radians(a))),
                        (gxx + 0.095 * math.cos(math.radians(a)), tmid - 0.31 + 0.095 * math.sin(math.radians(a)))], fill=hexc("#2a2422"), width=0.008)
            ang = -60 if k_ == 0 else -130
            c.line([(gxx, tmid - 0.31), (gxx + 0.075 * math.cos(math.radians(ang)), tmid - 0.31 + 0.075 * math.sin(math.radians(ang)))], fill=red, width=0.014)
        c.rect(tx1 - 0.95, tmid - 0.42, tx1 - 0.3, tmid - 0.2, fill=brass, outline=OUTLINE, width=0.02)
        c.text(tx1 - 0.625, tmid - 0.31, "TURBINE No 2", 0.07, hexc("#2a2422"))
        lx_ = x1 - 0.18
        c.line([(lx_, y0 + 0.35 * K), (lx_ - 0.12, y0 + 0.35 * K + 0.5)], fill=OUTLINE, width=0.05)
        c.line([(lx_, y0 + 0.35 * K), (lx_ - 0.12, y0 + 0.35 * K + 0.5)], fill=steel, width=0.025)
        c.ellipse(lx_ - 0.12, y0 + 0.35 * K + 0.5, 0.045, 0.045, fill=hexc("#1e1e22"), outline=OUTLINE, width=0.012)
        c.ellipse(lx_, y0 + 0.35 * K, 0.08, 0.05, fill=shade(dark, 1.2), outline=OUTLINE, width=0.02)
    elif kind == "hochregal":
        steel = lift("#3f4a56", 1.7)
        p.box(x0, y0, x1, y1, 0, 2.4, alpha(shade(steel, 1.2), 255), steel)
        fy0, fy1 = y0 + 0.05, y0 + 2.4 * K - 0.05
        for lv in range(3):
            ly = fy0 + (fy1 - fy0) * lv / 3
            c.line([(x0, ly), (x1, ly)], fill=hexc("#d4b13c"), width=0.05)
            xx = x0 + 0.1
            while xx < x1 - 0.5:
                ww = rnd.uniform(0.5, 1.1)
                hh2 = rnd.uniform(0.35, (fy1 - fy0) / 3 - 0.1)
                wood = lift("#7a5a3a", rnd.uniform(1.4, 1.7))
                c.rect(xx, ly + 0.04, min(x1 - 0.1, xx + ww), ly + 0.04 + hh2, fill=wood, outline=OUTLINE, width=0.025)
                c.line([(xx + 0.05, ly + 0.04 + hh2 / 2), (min(x1 - 0.1, xx + ww) - 0.05, ly + 0.04 + hh2 / 2)], fill=shade(wood, 0.75), width=0.015)
                xx += ww + 0.08
        for sx in (x0, x0 + (x1 - x0) / 2, x1 - 0.08):
            c.rect(sx, y0, sx + 0.08, fy1 + 0.05, fill=hexc("#2a5a8a"), outline=OUTLINE, width=0.02)
    elif kind == "kiste":
        wood = lift("#7a5a3a", 1.55)
        p.box(x0, y0, x1, y1, 0, 0.9, shade(wood, 1.15), wood)
        c.line([(x0, y0), (x1, y0 + 0.9 * K)], fill=shade(wood, 0.75), width=0.05)
        c.line([(x1, y0), (x0, y0 + 0.9 * K)], fill=shade(wood, 0.75), width=0.05)
        c.text(cx, y1 + 0.9 * K - (y1 - y0) / 2, "FRAGILE", 0.13, alpha(hexc("#2e2a26"), 180))
    elif kind == "co2":
        red = lift("#8a2a2a", 1.8)
        n = 5
        w = (x1 - x0) / n
        for i in range(n):
            bx = x0 + w * (i + 0.5)
            p.cyl(bx, cy, w * 0.42, 0, 1.5, shade(red, 1.2), red, w=0.035)
            c.ellipse(bx, cy + 1.6 * K, 0.07, 0.07, fill=hexc("#c0c8cc"), outline=OUTLINE, width=0.02)
        c.text(cx, cy + 0.6 * K, "CO2", 0.2, (240, 240, 235, 255))
    elif kind == "lieferwagen":
        body = lift("#d9d6cc", 1.12)
        teal = hexc("#2f7f7a")
        glass = alpha(hexc("#8fd0ff"), 235)
        dark = hexc("#1e1e1e")
        cab_y = y1 - 1.3
        # Raeder (liegen am Boden, seitlich unter dem Aufbau)
        for wx in (x0 + 0.12, x1 - 0.12):
            for wy in (y0 + 0.7, y1 - 0.75):
                c.ellipse(wx, wy, 0.2, 0.36, fill=dark, outline=OUTLINE, width=0.03)
                c.ellipse(wx, wy, 0.08, 0.15, fill=hexc("#8b949a"))
        # Fahrerhaus (Nord, hinten): Haube niedriger, Kabine mit Windschutzscheibe nach Norden
        p.box(x0 + 0.1, y1 - 0.45, x1 - 0.1, y1, 0.35, 0.95, shade(body, 1.05), body)
        p.box(x0 + 0.1, cab_y, x1 - 0.1, y1 - 0.45, 0.35, 1.55, shade(body, 1.08), body)
        tzc = 1.9 * K
        c.poly([(x0 + 0.22, y1 - 0.45 + tzc), (x1 - 0.22, y1 - 0.45 + tzc), (x1 - 0.3, y1 - 0.05 + 1.3 * K), (x0 + 0.3, y1 - 0.05 + 1.3 * K)],
               fill=glass, outline=OUTLINE, width=0.03)
        c.line([(x0 + 0.35, y1 - 0.4 + tzc), (x0 + 0.55, y1 - 0.1 + 1.3 * K)], fill=(255, 255, 255, 120), width=0.03)
        for sx in (x0 + 0.02, x1 - 0.02):
            c.rect(sx - 0.06, cab_y + 0.75 + 1.2 * K, sx + 0.06, cab_y + 0.75 + 1.4 * K, fill=dark, outline=OUTLINE, width=0.02)
        # Laderaum (Sued, vorne): Kasten mit Hecktueren
        p.box(x0, y0, x1, cab_y, 0.35, 1.9, shade(body, 1.08), body)
        fb, ft = y0 + 0.35 * K, y0 + 2.25 * K
        c.line([(cx, fb + 0.06), (cx, ft - 0.05)], fill=shade(body, 0.7), width=0.025)
        for dx in (x0 + 0.12, cx + 0.12):
            c.rect(dx + 0.1, fb + 0.55, dx + (x1 - x0) / 2 - 0.22, ft - 0.12, fill=glass, outline=OUTLINE, width=0.025)
            c.line([(dx + 0.16, fb + 0.6), (dx + 0.3, ft - 0.18)], fill=(255, 255, 255, 110), width=0.025)
        for hx_ in (cx - 0.14, cx + 0.14):
            c.rect(hx_ - 0.02, fb + 0.3, hx_ + 0.02, fb + 0.48, fill=hexc("#8b949a"), outline=OUTLINE, width=0.015)
        for hx_ in (x0 + 0.06, x1 - 0.06):
            for hz_ in (fb + 0.25, fb + 0.7):
                c.rect(hx_ - 0.03, hz_, hx_ + 0.03, hz_ + 0.1, fill=hexc("#8b949a"), outline=OUTLINE, width=0.015)
        # Zierstreifen + Schriftzug, Stossstange, Kennzeichen, Ruecklichter
        c.rect(x0 + 0.02, fb + 0.4, x1 - 0.02, fb + 0.5, fill=teal)
        c.rect(x0 + 0.02, fb + 0.36, x1 - 0.02, fb + 0.4, fill=shade(teal, 0.7))
        c.text(cx, fb + 0.2, "VESPER MUSEUM", 0.13, teal)
        c.rect(x0 - 0.04, y0 + 0.04, x1 + 0.04, y0 + 0.16, fill=hexc("#3b4046"), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.22, fb + 0.02, cx + 0.22, fb + 0.12, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.015)
        for tx in (x0 + 0.05, x1 - 0.35):
            c.rect(tx, fb + 0.02, tx + 0.3, fb + 0.14, fill=hexc("#c8302c"), outline=OUTLINE, width=0.02)
            c.rect(tx + 0.02, fb + 0.09, tx + 0.28, fb + 0.12, fill=hexc("#ff7a5c"))
        # Dach: Laengsrippen, Dachluke, Dachkante
        tz = 2.25 * K
        for rx_ in (x0 + 0.5, x0 + 1.0, x1 - 1.0, x1 - 0.5):
            c.line([(rx_, y0 + tz + 0.25), (rx_, cab_y + tz - 0.2)], fill=shade(body, 0.85), width=0.02)
        c.rect(cx - 0.45, y0 + tz + 1.4, cx + 0.45, y0 + tz + 2.1, fill=shade(body, 0.92), outline=OUTLINE, width=0.025)
        c.rect(cx - 0.4, y0 + tz + 1.45, cx + 0.4, y0 + tz + 2.05, outline=shade(body, 0.75), width=0.015)
        c.line([(x0 + 0.08, cab_y + tz - 0.08), (x1 - 0.08, cab_y + tz - 0.08)], fill=shade(body, 0.75), width=0.03)
    elif kind == "fass":
        blue = lift("#2f4f7a", 1.6)
        p.cyl(cx, cy, x1 - cx, 0, 0.9, shade(blue, 1.2), blue)
        c.rect(cx - (x1 - cx), cy + 0.3 * K, cx + (x1 - cx), cy + 0.36 * K, fill=shade(blue, 0.7))
        c.rect(cx - (x1 - cx), cy + 0.6 * K, cx + (x1 - cx), cy + 0.66 * K, fill=shade(blue, 0.7))
    elif kind == "lampe":
        steel = hexc("#3b4046")
        c.rect(cx - 0.06, cy, cx + 0.06, cy + 4.8 * K, fill=steel, outline=OUTLINE, width=0.03)
        c.line([(cx, cy + 4.8 * K), (cx - 0.6, cy + 4.9 * K)], fill=steel, width=0.08)
        c.ellipse(cx - 0.65, cy + 4.85 * K, 0.25, 0.1, fill=hexc("#ffb347"), outline=OUTLINE, width=0.03)
    else:
        p.box(x0, y0, x1, y1, 0, h, (200, 0, 200, 255), (150, 0, 150, 255))

    return p.c.finish(), p.c.x0, p.c.y0, p.base_y


def bezier(p0, p1, p2, n=8):
    """Quadratische Bezier-Kurve als Punktliste (fuer runde Knochen und Kordeln)."""
    out = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        out.append((x, y))
    return out


REX_SCALE = 1.25      # 11 m statt 8,7 m
REX_OFFSET = -1.0     # Skelett-Ursprung links von der Podestmitte: die Fuesse (Modell-x 0,6..2,2) stehen mittig


def draw_skeleton(p, cx, base, S=1.0, ox=0.0, part="all"):
    """T.-rex-Skelett (Kopf nach Westen) auf der Sockeloberkante; base = Bild-y der Oberkante.

    Detailfassung (User 25.09.: "sehr viel detaillierter"). Seitenansicht in Modellkoordinaten
    (x entlang des Koerpers um die Sockelmitte, z = Hoehe ueber dem Sockel in m), gezeichnet in der
    schraegen Aufsicht (z * K). Aufbau hinten -> vorne: fernes Bein und ferner Arm, ferne Rippen,
    Stahlstuetzen der Montage, Wirbelsaeule (Wirbelkoerper, Dornfortsaetze, Chevrons), Halsrippen,
    Becken, nahe Rippen und Bauchrippen, nahes Bein, naher Arm, Schaedel mit Unterkiefer und Zaehnen.
    Knochen sind verjuengte Flaechen mit dunkler Unterseite und heller Oberkante (Licht von oben),
    fossile Toenung schwankt je Knochen leicht. Umriss wie bisher: Schnauze -4,15, Schwanz +4,6.

    part: "all", "body" (ohne Kopf), "head" (Oberschaedel) oder "jaw" (Unterkiefer). Es wird immer alles
    in derselben Reihenfolge gezeichnet (gleiche Zufallsfolge = gleiche Toenung); nicht gewuenschte
    Teile landen auf einer Wegwerf-Leinwand."""
    real = p.c
    scrap = Canvas(0.0, 0.0, 0.1, 0.1, 10)
    c = real if part in ("all", "body") else scrap
    rnd = random.Random(1887)
    OL = OUTLINE
    BONE = hexc("#e9dfc4")
    STEEL = hexc("#3b4046")
    STEEL_HI = hexc("#737b84")
    TOOTH = hexc("#f6f1e4")
    HOLE = hexc("#2f2820")
    HOLE_RIM = hexc("#5a4e3c")

    def tone(col, f):
        return shade(col, f)

    def near_set():
        b = tone(BONE, rnd.uniform(0.95, 1.03))
        return b, tone(b, 0.78), tone(b, 1.1)

    def far_set():
        b = tone(BONE, rnd.uniform(0.66, 0.72))
        return b, tone(b, 0.8), tone(b, 1.05)

    def P(x, z):
        return (cx + ox + S * x, base + S * z * K)

    def chaikin(pts, n=2):
        for _ in range(n):
            out = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
                out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
            out.append(pts[-1])
            pts = out
        return pts

    def sides(Q, w0, w1):
        n = len(Q)
        L_, R_ = [], []
        for i, (qx, qy) in enumerate(Q):
            a, b = Q[max(0, i - 1)], Q[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            w = (w0 + (w1 - w0) * (i / (n - 1) if n > 1 else 0)) / 2
            L_.append((qx + nx * w, qy + ny * w))
            R_.append((qx - nx * w, qy - ny * w))
        return L_, R_

    def bone(pts, w0, w1=None, cols=None, smooth=2, ow=0.026, bulge=0.0):
        """Verjuengter Knochen entlang pts (Modellkoordinaten); bulge verdickt die Enden (Gelenke)."""
        w1 = w0 if w1 is None else w1
        w0, w1 = w0 * S, w1 * S
        col, lo, hi = cols or near_set()
        Q = [P(x, z) for x, z in pts]
        if len(Q) == 2:
            Q = [(Q[0][0] + (Q[1][0] - Q[0][0]) * t / 8, Q[0][1] + (Q[1][1] - Q[0][1]) * t / 8) for t in range(9)]
        elif smooth:
            Q = chaikin(Q, smooth)
        n = len(Q)
        if bulge:
            ws = [(w0 + (w1 - w0) * i / (n - 1)) * (1 + bulge * (abs(2 * i / (n - 1) - 1) ** 6)) for i in range(n)]
            L_, R_ = [], []
            for i, (qx, qy) in enumerate(Q):
                a, b = Q[max(0, i - 1)], Q[min(n - 1, i + 1)]
                dx, dy = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / ln, dx / ln
                L_.append((qx + nx * ws[i] / 2, qy + ny * ws[i] / 2))
                R_.append((qx - nx * ws[i] / 2, qy - ny * ws[i] / 2))
        else:
            L_, R_ = sides(Q, w0, w1)
        poly = L_ + R_[::-1]
        c.poly(poly, fill=col)
        low, up = (R_, L_) if sum(y for _, y in R_) < sum(y for _, y in L_) else (L_, R_)
        lin, uin = sides(Q, w0 * 0.45, w1 * 0.45)
        lin, uin = (lin, uin) if low is L_ else (uin, lin)
        c.poly(low + lin[::-1], fill=lo)
        hl = [(a[0] * 0.6 + b[0] * 0.4, a[1] * 0.6 + b[1] * 0.4) for a, b in zip(up, uin)]
        c.line(hl, fill=hi, width=max(0.01, min(w0, w1) * 0.16))
        if max(w0, w1) > 0.11:                                   # Patina: ein paar dunkle Flecken auf grossen Knochen
            for _ in range(3):
                i = rnd.randrange(1, n - 1)
                c.ellipse(Q[i][0] + rnd.uniform(-0.02, 0.02), Q[i][1] + rnd.uniform(-0.015, 0.015),
                          rnd.uniform(0.012, 0.03), rnd.uniform(0.008, 0.018), fill=alpha(tone(col, 0.8), 160))
        c.poly(poly, outline=OL, width=ow)
        return Q

    def knob(x, z, rx, ry=None, cols=None, ow=0.022):
        col, lo, hi = cols or near_set()
        ry = rx if ry is None else ry
        rx, ry = rx * S, ry * S
        q = P(x, z)
        c.ellipse(q[0], q[1], rx, ry, fill=col)
        c.ellipse(q[0] + rx * 0.12, q[1] - ry * 0.25, rx * 0.8, ry * 0.65, fill=lo)
        c.ellipse(q[0] - rx * 0.1, q[1] + ry * 0.12, rx * 0.72, ry * 0.62, fill=col)
        c.ellipse(q[0] - rx * 0.3, q[1] + ry * 0.35, rx * 0.28, ry * 0.2, fill=hi)
        c.ellipse(q[0], q[1], rx, ry, outline=OL, width=ow)

    def blob(pts_model, cols=None, ow=0.03, smooth=2, closed=True):
        col, lo, hi = cols or near_set()
        Q = [P(x, z) for x, z in pts_model]
        if smooth:
            Q = chaikin(Q + [Q[0]], smooth)[:-1]
        c.poly(Q, fill=col)
        cyq = sum(y for _, y in Q) / len(Q)
        lower = [q for q in Q if q[1] < cyq]
        if len(lower) > 2:
            c.poly([(x, y) for x, y in lower] + [(lower[-1][0], cyq - (cyq - lower[-1][1]) * 0.3),
                                                  (lower[0][0], cyq - (cyq - lower[0][1]) * 0.3)], fill=lo)
        for _ in range(4):                                       # Patina
            i = rnd.randrange(len(Q))
            qx, qy = Q[i][0] * 0.7 + (sum(x for x, _ in Q) / len(Q)) * 0.3, Q[i][1] * 0.7 + cyq * 0.3
            c.ellipse(qx, qy, rnd.uniform(0.012, 0.03), rnd.uniform(0.008, 0.02), fill=alpha(tone(col, 0.8), 150))
        c.poly(Q, outline=OL, width=ow)
        return Q

    def claw(x, z, dx, dz, w, cols=None):
        """Gebogene Kralle: Wurzel (x, z), Spitze (x+dx, z+dz), Breite w an der Wurzel."""
        col, lo, hi = cols or near_set()
        w = w * S
        a = P(x, z)
        tip = P(x + dx, z + dz)
        mid = P(x + dx * 0.55, z + dz * 0.55 + abs(dx) * 0.18)
        c.poly([(a[0], a[1] + w / 2), mid, tip, (mid[0], mid[1] - w * 0.35), (a[0], a[1] - w / 2)],
               fill=tone(col, 0.82), outline=OL, width=0.018)

    # ---------------------------------------------------------------- Wirbelsaeule (Kurve)
    ctrl = [(-2.28, 3.42), (-2.12, 3.18), (-1.98, 2.97), (-1.78, 2.83), (-1.5, 2.74), (-1.1, 2.72),
            (-0.6, 2.76), (-0.1, 2.8), (0.4, 2.8), (0.9, 2.76), (1.4, 2.66), (1.9, 2.52), (2.5, 2.33),
            (3.1, 2.15), (3.7, 2.02), (4.2, 1.96), (4.6, 1.98)]
    curve = chaikin(ctrl, 3)

    def spine_at(x):
        for a, b in zip(curve, curve[1:]):
            if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
                t = (x - a[0]) / (b[0] - a[0])
                return (x, a[1] + (b[1] - a[1]) * t)
        return curve[0] if x < curve[0][0] else curve[-1]

    def tangent_img(x):
        a, b = P(*spine_at(x - 0.04)), P(*spine_at(x + 0.04))
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        return dx / ln, dy / ln

    def vertebra(x, size, spine_len, tilt, chev=0.0, cols=None, rib=0.0, spine_w=0.55):
        col, lo, hi = cols or near_set()
        size, spine_len, chev = size * S, spine_len * S, chev * S
        xz = spine_at(x)
        q = P(*xz)
        ux, uy = tangent_img(x)
        nx, ny = -uy, ux
        # Dornfortsatz: verjuengt, nach hinten (Schwanzrichtung) geneigt
        if spine_len > 0.015:
            dirx, diry = nx * math.cos(tilt) + ux * math.sin(tilt), ny * math.cos(tilt) + uy * math.sin(tilt)
            b0 = (q[0] + nx * size * 0.25, q[1] + ny * size * 0.25)
            t0 = (b0[0] + dirx * spine_len * K * 1.6, b0[1] + diry * spine_len * K * 1.6)
            wb, wt = size * spine_w, size * spine_w * 0.62
            poly = [(b0[0] - ux * wb / 2, b0[1] - uy * wb / 2), (t0[0] - ux * wt / 2, t0[1] - uy * wt / 2),
                    (t0[0] + ux * wt / 2, t0[1] + uy * wt / 2), (b0[0] + ux * wb / 2, b0[1] + uy * wb / 2)]
            c.poly(poly, fill=col)
            c.line([(b0[0] + ux * wb * 0.3, b0[1] + uy * wb * 0.3), (t0[0] + ux * wt * 0.3, t0[1] + uy * wt * 0.3)], fill=lo, width=wb * 0.22)
            c.poly(poly, outline=OL, width=0.018)
            c.ellipse(t0[0], t0[1], wt * 0.62, wt * 0.5, fill=hi, outline=OL, width=0.016)
        # Chevron (Haemalbogen) unter den Schwanzwirbeln
        if chev > 0.015:
            b0 = (q[0] - nx * size * 0.3, q[1] - ny * size * 0.3)
            dirx, diry = -nx * math.cos(0.5) + ux * math.sin(0.5), -ny * math.cos(0.5) + uy * math.sin(0.5)
            t0 = (b0[0] + dirx * chev * K * 1.6, b0[1] + diry * chev * K * 1.6)
            w = size * 0.3
            poly = [(b0[0] - ux * w / 2, b0[1] - uy * w / 2), (t0[0], t0[1]), (b0[0] + ux * w / 2, b0[1] + uy * w / 2)]
            c.poly(poly, fill=lo, outline=OL, width=0.016)
        # Querfortsatz (kleiner Knopf zur Betrachterseite)
        if rib > 0:
            c.ellipse(q[0] + ux * size * 0.1, q[1] - ny * size * 0.05, size * 0.2, size * 0.14, fill=lo, outline=OL, width=0.014)
        # Wirbelkoerper: Rechteck mit runden Ecken entlang der Kurve, Bandscheibenkante
        a, b = size * 0.5, size * 0.36
        pts = []
        for i in range(20):
            t = i / 20 * 2 * math.pi
            cs, sn = math.cos(t), math.sin(t)
            ex = math.copysign(abs(cs) ** 0.45, cs) * a
            ey = math.copysign(abs(sn) ** 0.45, sn) * b
            pts.append((q[0] + ux * ex + nx * ey, q[1] + uy * ex + ny * ey))
        c.poly(pts, fill=col)
        c.poly([(q[0] + ux * a * 0.9 - nx * b * 0.95, q[1] + uy * a * 0.9 - ny * b * 0.95),
                (q[0] - ux * a * 0.9 - nx * b * 0.95, q[1] - uy * a * 0.9 - ny * b * 0.95),
                (q[0] - ux * a * 0.9 - nx * b * 0.2, q[1] - uy * a * 0.9 - ny * b * 0.2),
                (q[0] + ux * a * 0.9 - nx * b * 0.2, q[1] + uy * a * 0.9 - ny * b * 0.2)], fill=lo)
        c.line([(q[0] - ux * a * 0.6 + nx * b * 0.55, q[1] - uy * a * 0.6 + ny * b * 0.55),
                (q[0] + ux * a * 0.6 + nx * b * 0.55, q[1] + uy * a * 0.6 + ny * b * 0.55)], fill=hi, width=size * 0.08)
        c.poly(pts, outline=OL, width=0.018)
        return q

    # ---------------------------------------------------------------- Rippen-Geometrie
    def belly(x):
        """Unterkante des Brustkorbs (Modell-z): am tiefsten mittig, zu Schulter und Huefte flacher."""
        return 1.42 + 0.42 * ((x + 0.3) / 1.05) ** 2

    rib_xs = [-1.32 + i * 0.18 for i in range(11)]

    def rib_pts(x, far=False):
        sx, sz = spine_at(x)
        zb = min(belly(x), sz - 0.55)
        d = 0.06 if far else 0.0
        return [(x + d, sz - 0.03 + d * 0.4), (x - 0.05 + d, sz - 0.26), (x - 0.03 + d, sz - 0.58),
                (x + 0.07 + d, (sz + zb) / 2 - 0.22), (x + 0.18 + d, zb + 0.14), (x + 0.26 + d, zb)]

    # ================================================================ hinten: fernes Bein, ferner Arm
    fl = far_set()
    bone([(1.55, 2.32), (1.72, 1.9), (1.86, 1.46)], 0.18, 0.15, fl, bulge=0.35)
    bone([(1.88, 1.42), (1.74, 1.0), (1.62, 0.6)], 0.13, 0.1, fl)
    knob(1.87, 1.44, 0.095, 0.085, fl)
    knob(1.62, 0.57, 0.07, 0.06, fl)
    for off in (-0.04, 0.0, 0.04):
        bone([(1.62 + off, 0.56), (1.84 + off * 1.5, 0.13)], 0.05, 0.045, fl, smooth=0)
    for dx_, ln_ in ((-0.02, 0.36), (0.02, 0.46), (0.06, 0.32)):
        x0 = 1.84 + dx_
        bone([(x0, 0.12), (x0 - ln_ * 0.5, 0.07), (x0 - ln_, 0.045)], 0.05, 0.035, fl, smooth=1)
        claw(x0 - ln_, 0.045, -0.12, -0.04, 0.04, fl)
    # ferner Arm (klein, halb verdeckt)
    fa = far_set()
    bone([(-1.36, 2.02), (-1.5, 1.8)], 0.05, 0.04, fa, smooth=0)
    bone([(-1.5, 1.8), (-1.36, 1.64)], 0.035, 0.03, fa, smooth=0)

    # ================================================================ ferne Rippen
    for x in rib_xs:
        bone(rib_pts(x, far=True), 0.048, 0.022, far_set(), smooth=2, ow=0.018)

    # ================================================================ Stahlstuetzen der Montage
    def rod(x, z_top):
        a, b = P(x, 0.0), P(x, z_top)
        c.ellipse(a[0], a[1], 0.13, 0.06, fill=tone(STEEL, 0.8), outline=OL, width=0.02)
        c.ellipse(a[0], a[1] + 0.012, 0.1, 0.045, fill=STEEL)
        c.rect(a[0] - 0.024, a[1], a[0] + 0.024, b[1], fill=STEEL, outline=OL, width=0.014)
        c.line([(a[0] - 0.008, a[1] + 0.02), (b[0] - 0.008, b[1] - 0.02)], fill=STEEL_HI, width=0.01)
        c.rect(b[0] - 0.07, b[1] - 0.035, b[0] + 0.07, b[1] + 0.01, fill=tone(STEEL, 1.2), outline=OL, width=0.014)

    rod(-1.3, spine_at(-1.3)[1] - 0.12)         # Halsansatz (Kopf und Hals tragen sich frei darueber hinaus)
    rod(-0.35, spine_at(-0.35)[1] - 0.12)       # Brustkorb
    rod(2.05, spine_at(2.05)[1] - 0.1)          # Schwanzansatz

    # ================================================================ Wirbelsaeule: Schwanz -> Hals
    xs = []
    x = 4.55
    while x > 1.62:                              # Schwanzwirbel, zur Spitze kleiner und dichter
        xs.append(("c", x))
        t = (x - 1.6) / 3.0
        x -= 0.11 + 0.07 * (1 - t)
    x = 1.55
    while x > 0.78:                              # Kreuzbein (vom Darmbein ueberdeckt)
        xs.append(("s", x))
        x -= 0.16
    x = 0.72
    while x > -1.48:                             # Rueckenwirbel
        xs.append(("d", x))
        x -= 0.18
    for kind_, x in xs:
        if kind_ == "c":
            t = (x - 1.6) / 3.0                  # 0 am Becken, 1 an der Spitze
            size = 0.15 - 0.105 * t
            vertebra(x, size, 0.24 * (1 - t) ** 1.5, 0.55, chev=0.34 * (1 - t) ** 1.3)
        elif kind_ == "s":
            vertebra(x, 0.16, 0.24, 0.2, spine_w=1.0)
        else:
            vertebra(x, 0.16, 0.3 + 0.1 * math.sin((x + 1.5) / 2.3 * math.pi), 0.32, rib=1, spine_w=0.95)
    # Halswirbel: S-Bogen vom Ruecken zum Schaedel, kurze Fortsaetze, Halsrippen nach hinten
    neck_xs = [-1.55 - i * 0.1 for i in range(8)]
    for i, x in enumerate(neck_xs):
        q = vertebra(x, 0.2 - i * 0.006, 0.1 - i * 0.007, 0.3, spine_w=0.8)
        ux, uy = tangent_img(x)
        c.line([(q[0] - uy * 0.05, q[1] + ux * -0.06), (q[0] + ux * 0.2 - uy * 0.05, q[1] + uy * 0.2 - 0.09)],
               fill=tone(BONE, 0.8), width=0.028)

    # ================================================================ Becken
    pc_ = near_set()
    bone([(1.35, 2.36), (1.66, 2.04), (1.97, 1.73)], 0.13, 0.07, pc_)                   # Sitzbein
    knob(1.98, 1.71, 0.055, 0.05, pc_)
    bone([(0.98, 2.38), (0.8, 1.85), (0.58, 1.3)], 0.15, 0.11, pc_)                      # Schambein
    blob([(0.2, 1.2), (0.52, 1.17), (0.98, 1.2), (0.93, 1.33), (0.62, 1.37), (0.38, 1.33)], pc_)   # "Stiefel"
    blob([(0.26, 2.5), (0.3, 2.74), (0.5, 2.9), (0.9, 2.98), (1.35, 2.99), (1.75, 2.9), (2.02, 2.72),
          (2.12, 2.56), (1.9, 2.52), (1.55, 2.5), (1.3, 2.44), (1.1, 2.47), (0.85, 2.44), (0.55, 2.5),
          (0.38, 2.44)], pc_, ow=0.032, smooth=1)                                            # Darmbein
    c.line([P(0.45, 2.84), P(0.9, 2.93), P(1.4, 2.94), P(1.85, 2.84)], fill=pc_[2], width=0.03)   # Oberkante hell
    c.line([P(0.85, 2.52), P(1.05, 2.62), P(1.3, 2.62), P(1.5, 2.54)], fill=OL, width=0.022)       # Kamm ueber der Pfanne
    c.line([P(0.85, 2.53), P(1.05, 2.63), P(1.3, 2.63), P(1.5, 2.55)], fill=pc_[2], width=0.012)
    for gx in (0.62, 0.95, 1.6, 1.85):                                                         # Muskelansaetze
        a, b = P(gx, 2.6), P(gx + 0.08, 2.86)
        c.line([a, b], fill=tone(pc_[0], 0.84), width=0.016)
    q = P(1.08, 2.36)
    c.ellipse(q[0], q[1], 0.085, 0.07, fill=HOLE, outline=OL, width=0.02)                    # Hueftpfanne

    # ================================================================ nahe Rippen + Bauchrippen
    for x in rib_xs:
        bone(rib_pts(x), 0.075, 0.03, near_set(), smooth=2, ow=0.02)
    gcol = near_set()
    gx = -1.0
    while gx < 0.8:
        zb = belly(gx) - 0.04
        a, m, b = P(gx - 0.09, zb + 0.03), P(gx, zb - 0.05), P(gx + 0.09, zb + 0.03)
        c.line([a, m, b], fill=OL, width=0.05)
        c.line([a, m, b], fill=gcol[1], width=0.026)
        gx += 0.17

    # ================================================================ nahes Bein
    lg = near_set()
    bone([(0.92, 1.3), (1.1, 0.92), (1.25, 0.6)], 0.05, 0.04, (tone(lg[0], 0.85), lg[1], lg[2]))   # Wadenbein
    bone([(1.12, 2.36), (0.96, 1.9), (0.79, 1.42)], 0.21, 0.17, lg, bulge=0.4)                    # Oberschenkel
    knob(1.13, 2.37, 0.11, 0.1, lg)                                                                # Oberschenkelkopf
    blob([(1.18, 2.2), (1.3, 2.28), (1.28, 2.08), (1.16, 2.05)], lg, ow=0.02)                      # grosser Rollhuegel
    for (a_, b_) in (((1.02, 2.1), (0.9, 1.75)), ((0.98, 1.95), (0.93, 1.72))):                    # Risse im Fossil
        c.line([P(*a_), P(*b_)], fill=tone(lg[0], 0.72), width=0.012)
    bone([(0.8, 1.37), (0.98, 0.96), (1.16, 0.59)], 0.16, 0.115, lg, bulge=0.3)                  # Schienbein
    knob(0.79, 1.4, 0.115, 0.1, lg)                                                                # Knie
    knob(1.17, 0.55, 0.08, 0.07, lg)                                                               # Sprunggelenk
    for off in (-0.045, 0.0, 0.045):                                                               # Mittelfuss
        bone([(1.17 + off, 0.54), (1.06 + off * 1.4, 0.12)], 0.055, 0.048, lg, smooth=0)
    bone([(1.21, 0.33), (1.29, 0.21)], 0.035, 0.03, lg, smooth=0)                                  # Afterzehe
    claw(1.29, 0.21, 0.05, -0.08, 0.03, lg)
    for dx_, ln_ in ((-0.05, 0.36), (0.0, 0.48), (0.05, 0.34)):                                   # Zehen mit Gliedern
        x0 = 1.06 + dx_ * 1.4
        pts = [(x0, 0.11), (x0 - ln_ * 0.38, 0.07), (x0 - ln_ * 0.72, 0.05), (x0 - ln_, 0.04)]
        bone(pts, 0.058, 0.04, lg, smooth=0)
        for k_ in (1, 2):
            q = P(*pts[k_])
            c.ellipse(q[0], q[1], 0.03, 0.026, fill=lg[2], outline=OL, width=0.012)
        claw(x0 - ln_, 0.04, -0.13, -0.045, 0.045, lg)

    # ================================================================ naher Arm (winzig)
    am = near_set()
    bone([(-1.05, 2.62), (-1.24, 2.32), (-1.38, 2.1)], 0.13, 0.08, am)                  # Schulterblatt
    knob(-1.4, 2.06, 0.055, 0.05, am)                                                    # Rabenbein
    bone([(-1.42, 2.05), (-1.6, 1.82)], 0.065, 0.055, am, smooth=0)                     # Oberarm
    bone([(-1.6, 1.82), (-1.44, 1.64)], 0.032, 0.028, am, smooth=0)                     # Speiche
    bone([(-1.62, 1.79), (-1.47, 1.61)], 0.028, 0.024, am, smooth=0)                    # Elle
    for dx_, dz_ in ((0.08, -0.1), (-0.05, -0.12)):                                      # zwei Finger
        bone([(-1.45, 1.62), (-1.45 + dx_, 1.62 + dz_)], 0.026, 0.022, am, smooth=0)
        claw(-1.45 + dx_, 1.62 + dz_, dx_ * 0.6, -0.07, 0.024, am)

    # ================================================================ Schaedel
    # In der Schraegsicht (z * K) wird der Kopf so flach, dass er wie ein Krokodil liest: der Schaedel
    # wird deshalb um die Zahnlinie senkrecht gestreckt (hoher Hinterkopf, tiefer Kiefer).
    # Neu 24.10. (User: "schoener und realistischer"): tiefer, kastiger Tyrannosaurus-Schaedel statt der
    # langen Schnauze, grosse Schluesselloch-Augenhoehle, Traenenbeinhoecker, dreieckiges Voraugenfenster,
    # Oberkieferfenster, Nasenloch, Schlaefenfenster, rugoser Nasenruecken, Zahnreihe mit Alveolen,
    # tiefer Unterkiefer mit Kronenfortsatz und Unterkieferfenster. Drehpunkte (Halsgelenk, Kiefergelenk,
    # Augenhoehle) bleiben an denselben Modellkoordinaten wie bisher.
    P0 = P

    def P(x, z):
        return P0(x, 3.12 + (z - 3.12) * 1.3)

    sk = near_set()
    sk_dark = tone(sk[0], 0.86)
    c = real if part in ("all", "jaw") else scrap
    if part == "head":
        REX_RIG["neck"] = P(-2.22, 3.5)
        REX_RIG["jaw"] = P(-2.38, 3.08)
        REX_RIG["eye"] = P(-2.88, 3.9)

    def hole(pts_model, smooth=1, rim=True):
        Q = [P(x, z) for x, z in pts_model]
        Q = chaikin(Q + [Q[0]], smooth)[:-1]
        cxq = sum(x for x, _ in Q) / len(Q)
        cyq = sum(y for _, y in Q) / len(Q)
        if rim:
            c.poly(Q, fill=HOLE_RIM)
            c.poly([(cxq + (x - cxq) * 0.8, cyq + (y - cyq) * 0.78 + 0.01) for x, y in Q], fill=HOLE)
        else:
            c.poly(Q, fill=HOLE)
        c.poly(Q, outline=OL, width=0.018)

    def patina(pts_model, n, seed):
        rs = random.Random(seed)
        for _ in range(n):
            i = rs.randrange(len(pts_model) - 1)
            t = rs.random()
            x = pts_model[i][0] * (1 - t) + pts_model[i + 1][0] * t
            z = pts_model[i][1] * (1 - t) + pts_model[i + 1][1] * t
            q = P(x, z)
            c.ellipse(q[0], q[1], rs.uniform(0.012, 0.03), rs.uniform(0.008, 0.02), fill=alpha(tone(sk[0], 0.78), 170))

    # ---- Unterkiefer (zuerst, liegt hinter dem Oberkiefer): in geschlossener Lage beschrieben und um das
    # Kiefergelenk (-2,38 / 3,08) um 0,2 rad nach unten gedreht (Maul offen), wie es AtlasRex spaeter weiter tut
    JP = (-2.38, 3.08)
    JA = 0.3

    def J(x, z):
        dx, dz = x - JP[0], z - JP[1]
        return (JP[0] + dx * math.cos(JA) - dz * math.sin(JA), JP[1] + dx * math.sin(JA) + dz * math.cos(JA))

    jaw_closed = [(-2.3, 3.14), (-2.34, 2.98), (-2.42, 2.8), (-2.55, 2.68), (-2.75, 2.62), (-3.0, 2.62), (-3.3, 2.68),
                  (-3.6, 2.78), (-3.8, 2.88), (-3.9, 2.98), (-3.88, 3.04), (-3.7, 3.02), (-3.3, 2.98), (-3.0, 2.98),
                  (-2.75, 3.0), (-2.6, 3.06), (-2.5, 3.14)]
    jaw_pts = [J(x, z) for x, z in jaw_closed]
    blob(jaw_pts, (tone(sk[0], 0.95), sk[1], sk[2]), ow=0.03, smooth=0)
    c.poly([P(*J(x, z)) for x, z in ((-2.4, 2.82), (-2.6, 2.7), (-3.0, 2.66), (-3.5, 2.78), (-3.72, 2.9), (-3.74, 2.98),
                                     (-3.5, 2.9), (-3.0, 2.78), (-2.6, 2.8), (-2.42, 2.92))], fill=alpha(sk[1], 200))   # dunkle Unterkante
    hole([J(x, z) for x, z in ((-2.56, 2.9), (-2.76, 2.93), (-2.9, 2.85), (-2.76, 2.74), (-2.56, 2.76))], smooth=2)     # Unterkieferfenster
    c.line([P(*J(-2.95, 2.92)), P(*J(-3.4, 2.88)), P(*J(-3.7, 2.94))], fill=alpha(sk[1], 230), width=0.014)         # Naht Dentale/Angulare
    for i in range(6):                                                                               # Gefaessloecher am Dentale
        q = P(*J(-3.7 + i * 0.18, 2.9 + 0.01 * (i % 2)))
        c.ellipse(q[0], q[1], 0.012, 0.009, fill=HOLE)
    patina(jaw_pts[2:10], 7, 31)
    for i in range(12):                                                                              # untere Zaehne
        tx = -3.8 + i * 0.1
        zz = 3.0 + (tx + 3.7) * 0.0
        ln = 0.07 + 0.08 * math.sin(min(1.0, (i + 1) / 8) * math.pi)
        a, b = P(*J(tx - 0.028, zz)), P(*J(tx + 0.028, zz))
        m = P(*J(tx - 0.01, zz + ln * 0.55))
        t_ = P(*J(tx - 0.02, zz + ln))
        c.poly([a, m, t_, b], fill=TOOTH, outline=OL, width=0.012)
        c.line([P(*J(tx + 0.012, zz + 0.01)), P(*J(tx + 0.0, zz + ln * 0.5))], fill=(255, 255, 255, 255), width=0.007)
    # ---- Oberschaedel
    c = real if part in ("all", "head") else scrap
    skull = [(-2.3, 3.2), (-2.22, 3.45), (-2.2, 3.8), (-2.25, 4.05), (-2.34, 4.24), (-2.5, 4.34), (-2.65, 4.38), (-2.8, 4.4),
             (-2.98, 4.4), (-3.05, 4.46), (-3.12, 4.4), (-3.32, 4.24), (-3.55, 4.04), (-3.76, 3.82), (-3.9, 3.6), (-3.98, 3.42),
             (-4.0, 3.28), (-3.96, 3.16), (-3.88, 3.08), (-3.76, 3.04), (-3.4, 3.0), (-3.0, 3.0), (-2.7, 3.04), (-2.5, 3.1), (-2.38, 3.14)]
    blob(skull, sk, ow=0.036, smooth=0)
    # Jochbein (dunkles Band ueber der Zahnreihe), Nasenruecken hell, Schaedeldach hell
    c.poly([P(-2.34, 3.14), P(-2.95, 3.08), P(-3.5, 3.07), P(-3.9, 3.12), P(-3.94, 3.3), P(-3.5, 3.28), P(-2.95, 3.32), P(-2.4, 3.36)], fill=sk_dark)
    c.poly([P(-2.42, 3.34), P(-2.7, 3.36), P(-2.7, 3.46), P(-2.42, 3.5)], fill=alpha(sk[1], 180))      # Quadratojugale, Schatten
    c.line([P(-2.5, 4.3), P(-2.75, 4.35), P(-2.95, 4.35), P(-3.3, 4.2), P(-3.55, 4.0), P(-3.76, 3.78), P(-3.9, 3.56)], fill=sk[2], width=0.03)
    for i in range(6):                                                                               # rugoser Nasenruecken
        q = P(-3.3 - i * 0.11, 4.2 - i * 0.1)
        c.ellipse(q[0], q[1] - 0.025, 0.028, 0.016, fill=alpha(sk[1], 200))
        c.ellipse(q[0] - 0.008, q[1] - 0.012, 0.018, 0.01, fill=sk[2])
    # Schaedelfenster
    hole([(-3.12, 3.42), (-3.1, 3.68), (-3.2, 3.9), (-3.42, 3.84), (-3.6, 3.62), (-3.62, 3.42), (-3.38, 3.34)])          # Voraugenfenster
    hole([(-3.7, 3.5), (-3.8, 3.54), (-3.84, 3.4), (-3.72, 3.34)], smooth=2)                                          # Oberkieferfenster
    hole([(-3.8, 3.72), (-3.9, 3.68), (-3.94, 3.56), (-3.86, 3.52), (-3.78, 3.6)], smooth=2)                          # Nasenloch
    hole([(-2.36, 4.06), (-2.52, 4.1), (-2.58, 3.8), (-2.54, 3.48), (-2.4, 3.4), (-2.3, 3.62)])                        # Schlaefenfenster
    c.line([P(-2.45, 4.0), P(-2.47, 3.52)], fill=alpha(OL, 120), width=0.012)                                         # Kante im Fenster
    # Augenhoehle (Schluesselloch): runder oberer Teil, schmaler Schlitz nach unten, Knochenring, kleiner Glanz
    eye = []
    for i in range(13):
        ang = math.pi * (1.0 - i / 12)                       # oben herum von links nach rechts
        eye.append((-2.87 + 0.1 * math.cos(ang), 3.95 + 0.1 * math.sin(ang)))
    eye += [(-2.78, 3.86), (-2.81, 3.68), (-2.84, 3.56), (-2.9, 3.56), (-2.93, 3.68), (-2.96, 3.86)]
    hole(eye, smooth=1)
    q = P(-2.87, 3.93)
    c.ellipse(q[0], q[1], 0.06, 0.055, fill=HOLE)
    c.ellipse(q[0] - 0.028, q[1] + 0.028, 0.02, 0.016, fill=(250, 244, 226, 255))
    # Traenenbeinhoecker und Postorbitale (Knochenwuelste), Augenbrauenkante
    for bx, bz, r in ((-3.05, 4.44, 0.055), (-2.62, 4.36, 0.045)):
        qq = P(bx, bz)
        c.ellipse(qq[0], qq[1], r, r * 0.75, fill=sk[2], outline=OL, width=0.02)
        c.ellipse(qq[0] + r * 0.2, qq[1] - r * 0.25, r * 0.6, r * 0.4, fill=alpha(sk[1], 160))
    c.line([P(-2.72, 4.14), P(-2.88, 4.2), P(-3.02, 4.16)], fill=OL, width=0.022)                      # Brauenkante
    c.line([P(-2.72, 4.15), P(-2.88, 4.21), P(-3.02, 4.17)], fill=sk[2], width=0.012)
    # Alveolenreihe und Gefaessloecher am Oberkiefer, Risse, Patina
    for i in range(13):
        q = P(-3.88 + i * 0.11, 3.09)
        c.ellipse(q[0], q[1], 0.012, 0.009, fill=HOLE)
    for i in range(5):
        q = P(-3.7 + i * 0.22, 3.3 + 0.03 * (i % 2))
        c.ellipse(q[0], q[1], 0.011, 0.009, fill=HOLE)
    c.line([P(-3.3, 4.08), P(-3.36, 3.96), P(-3.3, 3.86)], fill=tone(sk[0], 0.7), width=0.012)
    c.line([P(-2.33, 4.1), P(-2.4, 4.22)], fill=tone(sk[0], 0.7), width=0.012)
    patina(skull[1:16], 12, 47)
    # obere Zaehne: bananenfoermig, nach hinten gekruemmt, die groessten in der Kiefermitte
    for i in range(14):
        tx = -3.92 + i * 0.1
        zz = 3.05 - (tx + 3.92) * 0.012
        ln = 0.1 + 0.11 * math.sin(min(1.0, (i + 1) / 9) * math.pi) + (0.025 if i % 3 == 1 else 0)
        a, b = P(tx - 0.032, zz + 0.01), P(tx + 0.032, zz + 0.01)
        m = P(tx + 0.014, zz - ln * 0.55)
        t_ = P(tx + 0.034, zz - ln)
        c.poly([a, m, t_, b], fill=TOOTH, outline=OL, width=0.012)
        c.line([P(tx - 0.014, zz - 0.01), P(tx + 0.004, zz - ln * 0.5)], fill=(255, 255, 255, 255), width=0.008)


def draw_spieluhr(p, cx, cy):
    """Station der Sabotage "Rex erwacht": Spieluhr mit Kurbel auf einem Messingstaender (Rotunde)."""
    c = p.c
    brass = hexc("#c9a24c")
    wood = lift("#5a3620", 1.5)
    # Fuss, Saeule, Teller
    c.ellipse(cx, cy, 0.24, 0.11, fill=shade(brass, 0.7), outline=OUTLINE, width=0.025)
    c.ellipse(cx, cy + 0.02, 0.18, 0.08, fill=shade(brass, 0.95))
    c.rect(cx - 0.045, cy + 0.02, cx + 0.045, cy + 0.86 * K, fill=brass, outline=OUTLINE, width=0.02)
    c.line([(cx - 0.02, cy + 0.06), (cx - 0.02, cy + 0.84 * K)], fill=shade(brass, 1.35), width=0.015)
    for z in (0.3, 0.6):
        c.ellipse(cx, cy + z * K, 0.06, 0.025, fill=shade(brass, 1.15), outline=OUTLINE, width=0.015)
    c.rect(cx - 0.07, cy + 0.42 * K, cx + 0.07, cy + 0.5 * K, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.012)
    c.ellipse(cx, cy + 0.88 * K, 0.2, 0.09, fill=shade(brass, 1.1), outline=OUTLINE, width=0.02)
    # Kasten mit offenem Deckel: Walze und Kamm sichtbar
    x0, x1, y0, y1, z0, h = cx - 0.22, cx + 0.2, cy - 0.1, cy + 0.1, 0.92, 0.2
    p.box(x0, y0, x1, y1, z0, h, shade(wood, 1.25), wood)
    ft = y0 + (z0 + h) * K
    c.rect(x0 + 0.04, ft + 0.02, x1 - 0.04, ft + 0.15, fill=hexc("#241810"))
    c.rect(x0 + 0.06, ft + 0.05, x1 - 0.06, ft + 0.11, fill=brass, outline=OUTLINE, width=0.012)
    for i in range(9):
        c.ellipse(x0 + 0.08 + i * 0.033, ft + 0.08 + (0.015 if i % 2 else -0.015), 0.008, 0.008, fill=shade(brass, 0.55))
    c.line([(x0 + 0.06, ft + 0.13), (x1 - 0.06, ft + 0.13)], fill=hexc("#cfd6de"), width=0.02)
    # Deckel aufgeklappt nach hinten
    lid = [(x0, y1 + (z0 + h) * K), (x1, y1 + (z0 + h) * K), (x1 - 0.02, y1 + (z0 + h) * K + 0.26), (x0 + 0.02, y1 + (z0 + h) * K + 0.26)]
    c.poly(lid, fill=shade(wood, 1.1), outline=OUTLINE, width=0.02)
    c.poly([(q[0] * 0.8 + cx * 0.2, q[1] * 0.8 + (y1 + (z0 + h) * K + 0.13) * 0.2) for q in lid], fill=hexc("#6a2a3a"))
    # Kurbel an der rechten Seite
    ax, ay = x1 + 0.01, y0 + (z0 + h * 0.5) * K
    c.line([(ax, ay), (ax + 0.1, ay + 0.02), (ax + 0.14, ay + 0.14)], fill=OUTLINE, width=0.05)
    c.line([(ax, ay), (ax + 0.1, ay + 0.02), (ax + 0.14, ay + 0.14)], fill=brass, width=0.025)
    c.ellipse(ax + 0.14, ay + 0.15, 0.035, 0.035, fill=shade(brass, 1.2), outline=OUTLINE, width=0.015)


def draw_nachtlicht(p, cx, cy):
    """Station der Sabotage "Rex erwacht": Sternenprojektor auf einem Dreibein (Security Office)."""
    c = p.c
    brass = hexc("#c9a24c")
    dark = hexc("#3b3f46")
    top = (cx, cy + 0.82 * K)
    for fx, fy in ((-0.2, -0.04), (0.2, -0.04), (0.03, 0.14)):
        c.line([top, (cx + fx, cy + fy)], fill=OUTLINE, width=0.05)
        c.line([top, (cx + fx, cy + fy)], fill=dark, width=0.028)
        c.ellipse(cx + fx, cy + fy, 0.03, 0.018, fill=OUTLINE)
    c.rect(cx - 0.03, cy + 0.72 * K, cx + 0.03, cy + 0.9 * K, fill=dark, outline=OUTLINE, width=0.015)
    # Kugelkopf mit Sternloechern und Aequatorring
    hx, hy, r = cx, cy + 1.02 * K, 0.19
    c.glow(hx, hy + 0.05, 0.5, (255, 226, 150, 255), 0.35)
    c.ellipse(hx, hy, r, r, fill=brass, outline=OUTLINE, width=0.025)
    c.ellipse(hx + 0.04, hy - 0.05, r * 0.8, r * 0.75, fill=shade(brass, 0.85))
    c.ellipse(hx - 0.05, hy + 0.06, r * 0.45, r * 0.4, fill=shade(brass, 1.25))
    c.ellipse(hx, hy, r, r * 0.3, outline=shade(brass, 0.6), width=0.02)
    for dx, dy in ((-0.1, 0.07), (-0.02, 0.11), (0.08, 0.06), (0.11, -0.03), (0.02, -0.08), (-0.09, -0.06), (0.0, 0.02)):
        c.ellipse(hx + dx, hy + dy, 0.016, 0.016, fill=(255, 238, 180, 255))
    c.ellipse(hx, hy, r, r, outline=OUTLINE, width=0.025)
    # Kabel zum Boden
    c.line([(cx + 0.02, cy + 0.72 * K), (cx + 0.1, cy + 0.3 * K), (cx + 0.26, cy - 0.02)], fill=hexc("#1c1f24"), width=0.02)


def draw_rope_posts(p, cx, cy, rx, ry, z0, angles, rnd=None):
    """Messingpfosten mit Kordel auf einer Ellipse (Aussichtsabsperrung); angles in Grad."""
    c = p.c
    brass = hexc("#c9a24c")
    rope = lift("#7a1e2e", 1.4)
    pts = []
    for a in angles:
        x = cx + rx * math.cos(math.radians(a)); y = cy + ry * math.sin(math.radians(a))
        pts.append((x, y + z0 * K))
    # Kordel zuerst (haengt zwischen den Koepfen), dann Pfosten darueber
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        mx, my = (ax + bx) / 2, (ay + by) / 2 - 0.12
        c.line([(ax, ay + 0.85 * K), (mx, my + 0.85 * K), (bx, by + 0.85 * K)], fill=OUTLINE, width=0.06)
        c.line([(ax, ay + 0.85 * K), (mx, my + 0.85 * K), (bx, by + 0.85 * K)], fill=rope, width=0.03)
    for x, y in pts:
        c.ellipse(x, y, 0.09, 0.05, fill=shade(brass, 0.8), outline=OUTLINE, width=0.025)
        c.rect(x - 0.025, y, x + 0.025, y + 0.9 * K, fill=brass, outline=OUTLINE, width=0.02)
        c.ellipse(x, y + 0.9 * K, 0.05, 0.04, fill=shade(brass, 1.15), outline=OUTLINE, width=0.02)


# Stilblatt: Staffelei mit Portraet an der Nordwand der Galerie, oestlich der Weapons-Konsole (-10,5, 7,7)
# und westlich des Ost-Durchgangs. Ohne Kollider (begehbar, 0,4 m tief); ein GLASS-Eintrag in
# museum_layout.py waere der Geometrie-Wunsch fuer den vollen Pass.
ART_PROPS = [("staffelei", ("rect", -8.55, 7.0, -7.45, 7.4))]


def extra_props():
    """Objekte ohne eigenen Kollider-Eintrag (Deko mit Hoehe)."""
    return list(L.EXTRA_PROPS) + list(ART_PROPS)


def pupil_sprite(ppm):
    """Pupille des Staffelei-Portraets als eigenes Sprite (Mitte = Pivot), mit Glanzpunkt."""
    rx, ry = PORTRAIT_EYES.get("pupil_rx", 0.03), PORTRAIT_EYES.get("pupil_ry", 0.03)
    c = Canvas(-rx - 0.02, -ry - 0.02, rx + 0.02, ry + 0.02, ppm)
    c.ellipse(0, 0, rx, ry, fill=hexc("#2a2420"), outline=OUTLINE, width=0.008)
    c.ellipse(-rx * 0.3, ry * 0.3, rx * 0.25, ry * 0.25, fill=(255, 255, 255, 255))
    return c.finish()


def planetarium_sprites():
    """Laufzeit-Sprites der Planetariumsshow (Vertrag 01.10.): Sternenkuppel 512 x 512 px, rund, ausserhalb
    transparent, hell auf transparent (Laufzeit toent blaeulich und dreht), mit Milchstrasse und Sternbild-
    linien; drei Planeten 64 x 64 px (Ring, Baender, Krater), Mitte = Drehpunkt. Rueckgabe {Dateiname: Bild}."""
    out = {}
    rnd = random.Random(2026)
    S, ss = 512, 2
    W = S * ss
    cx = cy = W / 2
    R = W / 2 - 3 * ss
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    # Milchstrasse: weiches diagonales Band (zwei Striche, verwischt) + dichte feine Sterne entlang des Bands
    band = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band, "RGBA")
    a = math.radians(32)
    dx, dy = math.cos(a), math.sin(a)
    for wdt, al in ((int(W * 0.22), 38), (int(W * 0.11), 48)):
        bd.line([(cx - dx * W, cy - dy * W), (cx + dx * W, cy + dy * W)], fill=(255, 255, 255, al), width=wdt)
    bd.line([(cx - dx * W + dy * W * 0.03, cy - dy * W - dx * W * 0.03), (cx + dx * W + dy * W * 0.03, cy + dy * W - dx * W * 0.03)],
            fill=(0, 0, 0, 40), width=int(W * 0.025))   # dunkle Staubbahn
    band = band.filter(ImageFilter.GaussianBlur(W * 0.03))
    im.alpha_composite(band)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(1400):
        t = rnd.uniform(-1, 1) * W * 0.75
        off = rnd.gauss(0, W * 0.06)
        px_, py_ = cx + dx * t - dy * off, cy + dy * t + dx * off
        r = rnd.uniform(0.6, 1.6) * ss
        d.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=(255, 255, 255, rnd.randint(60, 150)))
    # Sterne ueber die ganze Kuppel, wenige grosse mit Glanzkreuz
    stars = []
    for _ in range(520):
        ang, rr = rnd.uniform(0, math.tau), math.sqrt(rnd.random()) * R * 0.98
        px_, py_ = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        r = rnd.choice([0.8, 1.0, 1.0, 1.2, 1.2, 1.6, 1.6, 2.2, 3.0]) * ss
        d.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=(255, 255, 255, rnd.randint(140, 255)))
        if r >= 3.0 * ss and rnd.random() < 0.5:
            for ddx, ddy in ((1, 0), (0, 1)):
                d.line([(px_ - ddx * r * 2.2, py_ - ddy * r * 2.2), (px_ + ddx * r * 2.2, py_ + ddy * r * 2.2)], fill=(255, 255, 255, 70), width=ss)
        stars.append((px_, py_, r))
    # Sternbilder: 7 Gruppen aus 4 bis 7 nahen hellen Sternen, verbunden mit duennen Linien
    for k in range(7):
        ang = k * math.tau / 7 + rnd.uniform(-0.3, 0.3)
        rr = rnd.uniform(0.3, 0.75) * R
        gx, gy = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        pts = []
        for _ in range(rnd.randint(4, 7)):
            pts.append((gx + rnd.uniform(-1, 1) * W * 0.09, gy + rnd.uniform(-1, 1) * W * 0.09))
        pts.sort(key=lambda p: p[0] + 0.3 * p[1])
        d.line(pts, fill=(255, 255, 255, 95), width=max(1, int(0.9 * ss)))
        if rnd.random() < 0.5:
            d.line([pts[0], pts[-1]], fill=(255, 255, 255, 60), width=max(1, int(0.8 * ss)))
        for px_, py_ in pts:
            r = 2.6 * ss
            d.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=(255, 255, 255, 255))
    # Kreisfenster: Alpha mit runder Maske multiplizieren, weicher Rand von 3 px, feiner heller Saum
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.5 * ss))
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(255, 255, 255, 70), width=int(1.2 * ss))
    out["task_museum_dome.png"] = im.resize((S, S), Image.LANCZOS)

    # Planeten 64 x 64: Among-Us-Look (Umriss, flache Flaechen, Lichtkante oben links, Schattenseite rechts)
    P, pss = 64, 4
    PW = P * pss

    def planet_canvas():
        return Image.new("RGBA", (PW, PW), (0, 0, 0, 0))

    def terminator(d, c, r):
        # Schattenseite: Halbmond rechts unten als eigene Ebene
        lay = Image.new("RGBA", (PW, PW), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.ellipse([c - r, c - r, c + r, c + r], fill=(0, 0, 0, 70))
        ld.ellipse([c - r * 1.25, c - r * 1.25, c + r * 0.75, c + r * 0.75], fill=(0, 0, 0, 0))
        return lay

    def highlight(im, box, col):
        # halbtransparentes Glanzlicht ueber eigene Ebene (PIL ueberschreibt sonst das Alpha)
        lay = Image.new("RGBA", (PW, PW), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse(box, fill=col)
        im.alpha_composite(lay)

    ol = max(2, int(0.7 * pss))
    c = PW / 2
    # 0: Ringplanet
    im = planet_canvas(); d = ImageDraw.Draw(im, "RGBA")
    r = PW * 0.3
    ring = Image.new("RGBA", (PW, PW), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring, "RGBA")
    rd.ellipse([c - r * 1.65, c - r * 0.55, c + r * 1.65, c + r * 0.55], outline=(14, 16, 20, 255), width=ol + int(r * 0.26))
    rd.ellipse([c - r * 1.65, c - r * 0.55, c + r * 1.65, c + r * 0.55], outline=(226, 200, 150, 255), width=int(r * 0.26))
    rd.ellipse([c - r * 1.45, c - r * 0.48, c + r * 1.45, c + r * 0.48], outline=(170, 140, 100, 255), width=max(1, int(r * 0.05)))
    ring = ring.rotate(-18, resample=Image.BICUBIC, center=(c, c))
    back = ring.copy()
    ImageDraw.Draw(back).rectangle([0, c, PW, PW], fill=(0, 0, 0, 0))
    front = ring.copy()
    ImageDraw.Draw(front).rectangle([0, 0, PW, c], fill=(0, 0, 0, 0))
    im.alpha_composite(back)
    d.ellipse([c - r, c - r, c + r, c + r], fill=(222, 170, 92, 255), outline=(14, 16, 20, 255), width=ol)
    for k, (fy, hh, col) in enumerate(((-0.55, 0.16, (200, 140, 70)), (-0.1, 0.12, (240, 200, 130)), (0.35, 0.18, (200, 140, 70)))):
        lay = Image.new("RGBA", (PW, PW), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle([c - r, c + fy * r, c + r, c + (fy + hh) * r], fill=col + (255,))
        m = Image.new("L", (PW, PW), 0)
        ImageDraw.Draw(m).ellipse([c - r + ol, c - r + ol, c + r - ol, c + r - ol], fill=255)
        lay.putalpha(ImageChops.multiply(lay.getchannel("A"), m))
        im.alpha_composite(lay)
    highlight(im, [c - r * 0.55, c - r * 0.75, c - r * 0.15, c - r * 0.45], (255, 240, 210, 130))
    im.alpha_composite(terminator(d, c, r - ol / 2))
    im.alpha_composite(front)
    out["task_museum_planet_0.png"] = im.resize((P, P), Image.LANCZOS)
    # 1: Gasriese mit Baendern und Sturmfleck
    im = planet_canvas(); d = ImageDraw.Draw(im, "RGBA")
    r = PW * 0.42
    d.ellipse([c - r, c - r, c + r, c + r], fill=(120, 160, 210, 255), outline=(14, 16, 20, 255), width=ol)
    m = Image.new("L", (PW, PW), 0)
    ImageDraw.Draw(m).ellipse([c - r + ol, c - r + ol, c + r - ol, c + r - ol], fill=255)
    lay = Image.new("RGBA", (PW, PW), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for fy, hh, col in ((-0.75, 0.2, (90, 120, 180)), (-0.35, 0.14, (170, 200, 235)), (0.0, 0.22, (90, 120, 180)), (0.4, 0.12, (170, 200, 235)), (0.65, 0.2, (80, 110, 170))):
        pts = [(c - r * 1.2, c + fy * r), (c + r * 1.2, c + (fy - 0.05) * r), (c + r * 1.2, c + (fy + hh - 0.05) * r), (c - r * 1.2, c + (fy + hh) * r)]
        ld.polygon(pts, fill=col + (255,))
    ld.ellipse([c + r * 0.1, c + r * 0.05, c + r * 0.6, c + r * 0.35], fill=(230, 120, 90, 255), outline=(14, 16, 20, 255), width=max(1, ol // 2))
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), m))
    im.alpha_composite(lay)
    highlight(im, [c - r * 0.6, c - r * 0.78, c - r * 0.2, c - r * 0.5], (255, 255, 255, 110))
    im.alpha_composite(terminator(d, c, r - ol / 2))
    out["task_museum_planet_1.png"] = im.resize((P, P), Image.LANCZOS)
    # 2: Felsplanet mit Kratern
    im = planet_canvas(); d = ImageDraw.Draw(im, "RGBA")
    r = PW * 0.36
    d.ellipse([c - r, c - r, c + r, c + r], fill=(196, 120, 92, 255), outline=(14, 16, 20, 255), width=ol)
    for kx, ky, kr in ((-0.35, -0.2, 0.22), (0.3, 0.1, 0.16), (-0.05, 0.45, 0.14), (0.35, -0.45, 0.1)):
        px_, py_, rr = c + kx * r, c + ky * r, kr * r
        d.ellipse([px_ - rr, py_ - rr, px_ + rr, py_ + rr], fill=(150, 88, 70, 255), outline=(14, 16, 20, 255), width=max(1, ol // 2))
        d.ellipse([px_ - rr * 0.7, py_ - rr * 0.7 + rr * 0.25, px_ + rr * 0.7, py_ + rr * 0.7 + rr * 0.25], fill=(176, 104, 82, 255))
    highlight(im, [c - r * 0.65, c - r * 0.75, c - r * 0.3, c - r * 0.5], (255, 230, 215, 110))
    im.alpha_composite(terminator(d, c, r - ol / 2))
    out["task_museum_planet_2.png"] = im.resize((P, P), Image.LANCZOS)
    return out


def all_props():
    items = []
    for (shape, _col), kind in zip(L.OPAQUE, L.OPAQUE_KINDS):
        if kind:
            items.append((kind, shape))
    for shape, kind in zip(L.GLASS, L.GLASS_KINDS):
        if kind:
            items.append((kind, shape))
    items += extra_props()
    return items


def pack(images, max_w=4096, max_h=4096):
    """Regal-Packer ueber mehrere Atlanten. images: Liste (id, PIL.Image).
    Rueckgabe: [Atlas-Bilder], {id: (atlas, x, y, w, h)} mit y von OBEN."""
    order = sorted(range(len(images)), key=lambda i: -images[i][1].height)
    placed = {}
    pages = [[]]
    x = y = shelf_h = 0
    for i in order:
        _id, im = images[i]
        if im.width > max_w or im.height > max_h:
            raise ValueError(f"sprite {_id} too large: {im.size}")
        if x + im.width + 2 > max_w:
            x = 0
            y += shelf_h + 2
            shelf_h = 0
        if y + im.height > max_h:
            pages.append([])
            x = y = shelf_h = 0
        page = len(pages) - 1
        placed[_id] = (page, x, y, im.width, im.height)
        pages[page].append((_id, im, x, y))
        x += im.width + 2
        shelf_h = max(shelf_h, im.height)
    atlases = []
    for page in pages:
        used_h = max(py + im.height for _i, im, _x, py in page)
        h = 1
        while h < used_h:
            h *= 2
        atlas = Image.new("RGBA", (max_w, h), (0, 0, 0, 0))
        for _id, im, px_, py in page:
            atlas.paste(im, (px_, py))
        atlases.append(atlas)
    return atlases, placed
