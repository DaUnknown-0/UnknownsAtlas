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
    fl, _wall = ROOM_ROLE[key]
    base = lift(fl, 1.0 if key == "telefon" else 1.45)
    x0, y0, x1, y1 = region.bounds
    ops.geom(region, fill=base)

    if key == "foyer":
        light, dark = lift("#9c948a"), lift("#8a8275", 1.32)
        # Schachbrett aus Marmorplatten, diagonal wirkt zu unruhig -> gerade 1,0 m
        rnd = random.Random(7)
        yy = y0
        i = 0
        while yy < y1:
            xx = x0
            j = 0
            while xx < x1:
                t = sbox(xx, yy, xx + 1, yy + 1).intersection(region)
                ops.geom(t, fill=light if (i + j) % 2 == 0 else dark)
                # Ader
                if rnd.random() < 0.35 and not t.is_empty:
                    ax = xx + rnd.uniform(0.1, 0.9)
                    ops.line([(ax, yy + 0.05), (ax + rnd.uniform(-0.3, 0.3), yy + 0.5), (ax + rnd.uniform(-0.2, 0.2), yy + 0.95)],
                             fill=alpha(lift("#5e584e"), 90), width=0.015)
                xx += 1; j += 1
            yy += 1; i += 1
        # roter Laeufer: Shop-Tuer -> Theke -> Rotunde
        runner = lift("#5a2a2a", 1.6)
        ops.rect(-1.1, -13, 1.1, -3, fill=runner)
        ops.rect(-0.95, -13, 0.95, -3, outline=alpha(lift("#b08a3c"), 200), width=0.04)
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
    elif key == "rotunde":
        speckle(ops, region, 2600, [lift("#8a8378"), lift("#55514a"), lift("#a8a094"), lift("#4e4a44")], 0.015, 0.035, seed=11)
        # Terrazzo-Intarsie: dunkler Ring zwischen zwei Messingbaendern, Kompassstrahlen, Rosetten
        brass = alpha(lift("#b08a3c", 1.1), 235)
        dark_ring = alpha(lift("#4e4a44", 1.25), 200)
        ring_pts_o = [(math.cos(math.radians(a)) * 5.6, 4 + math.sin(math.radians(a)) * 5.6) for a in range(0, 360, 4)]
        ring_pts_i = [(math.cos(math.radians(a)) * 4.9, 4 + math.sin(math.radians(a)) * 4.9) for a in range(360, 0, -4)]
        ops.geom(Polygon(ring_pts_o + ring_pts_i).intersection(region), fill=dark_ring)
        for r in (5.6, 4.9):
            ops.ellipse(0, 4, r, r, outline=brass, width=0.06)
        for i in range(16):
            a = i * math.pi / 8
            ops.line([(math.cos(a) * 4.9, 4 + math.sin(a) * 4.9), (math.cos(a) * 5.6, 4 + math.sin(a) * 5.6)], fill=brass, width=0.045)
            if i % 4 == 0:
                rx_, ry_ = math.cos(a) * 5.25, 4 + math.sin(a) * 5.25
                ops.ellipse(rx_, ry_, 0.18, 0.18, fill=alpha(lift("#b08a3c", 1.1), 235))
                ops.ellipse(rx_, ry_, 0.08, 0.08, fill=alpha(lift("#4e4a44", 1.2), 220))
        # innerer Messingkreis um den Sockel
        ops.ellipse(0.5, 4, 3.0, 1.2, outline=alpha(lift("#b08a3c", 1.1), 200), width=0.04)   # Podest 5,4 x 1,8 m
        # Mondfleck durch den Oculus
        ops.glow(-0.6, 3.4, 3.2, MOON, 0.35)
    elif key == "galerie":
        # Fischgraet vereinfacht: Staebe 0,18 x 0,9 in versetzten Reihen
        cols = [lift("#63462d"), lift("#573d27"), lift("#7c5a3c"), lift("#6a4a30")]
        tiles(ops, region, x0, y0, x1, y1, 0.9, 0.18, cols, lift("#4e3521", 1.2), offset_rows=True, seed=5, fuge_w=0.02)
        # Laeufer in der Achse
        ops.rect(x0, 3.2, x1, 4.8, fill=alpha(lift("#5b2430", 1.5), 235))
        ops.rect(x0, 3.3, x1, 4.7, outline=alpha(lift("#a8843c"), 200), width=0.035)
        ops.glow(-13.7, 4.0, 4.5, MOON, 0.22)
        # Bilderleuchten: warme Lichtkegel an den Stellwaenden
        for sx in (-17.3, -12.8):
            for sy in (1.6, 6.4):
                for side in (-0.55, 0.55):
                    ops.glow(sx + side, sy, 1.1, WARM, 0.2)
    elif key == "aegypten":
        cols = [lift("#8a7048"), lift("#8a6f47"), lift("#a0855a", 1.3)]
        tiles(ops, region, x0, y0, x1, y1, 1.2, 0.8, cols, lift("#6a5436", 1.2), offset_rows=True, seed=9)
        # Mittelgang als Sandsteinband mit Ornament
        ops.rect(-27.0, y0, -26.2, y1, fill=alpha(lift("#b8843a", 1.1), 120))
        for yy in range(int(y0) + 1, int(y1)):
            ops.poly([(-26.6, yy - 0.25), (-26.35, yy), (-26.6, yy + 0.25), (-26.85, yy)], fill=alpha(lift("#3f2e1c", 1.3), 160))
        # warmes Grablicht an den Sarkophagen und der Sphinx
        for gx, gy in ((-28.1, 4.5), (-28.1, -1.5), (-25.7, 9.0)):
            ops.glow(gx, gy, 2.0, WARM, 0.3)
    elif key == "planetarium":
        speckle(ops, region, 900, [alpha(hexc("#cfe0ff"), 170), alpha(hexc("#cfe0ff"), 90)], 0.012, 0.03, seed=13)
        # Teppichringe (flach, begehbar): zwei Boegen mit Luecken nach S und E. Bewusst OHNE
        # Umriss und Sitz-Buckel, sonst lesen sie sich als Baenke, durch die man laufen kann.
        ring = alpha(lift("#2b3552", 1.5), 150)
        edge = alpha(lift("#6f86c8", 1.2), 170)
        for r in (2.4, 3.6):
            for a0, a1 in ((20, 250), (290, 330)):
                pts_o = [(-14.45 + (r + 0.25) * math.cos(math.radians(a)), 15.7 + (r + 0.25) * math.sin(math.radians(a))) for a in range(a0, a1 + 1, 5)]
                pts_i = [(-14.45 + (r - 0.25) * math.cos(math.radians(a)), 15.7 + (r - 0.25) * math.sin(math.radians(a))) for a in range(a1, a0 - 1, -5)]
                ops.poly(pts_o + pts_i, fill=ring)
                ops.line(pts_o, fill=edge, width=0.025)
                ops.line(pts_i, fill=edge, width=0.025)
                for a in range(a0 + 6, a1 - 2, 12):
                    sx = -14.45 + r * math.cos(math.radians(a)); sy = 15.7 + r * math.sin(math.radians(a))
                    ops.ellipse(sx, sy, 0.05, 0.05, fill=alpha(hexc("#cfe0ff"), 150))
        ops.glow(-14.45, 15.7, 2.0, hexc("#cfe0ff"), 0.25)
    elif key == "mineralien":
        cols = [lift("#33383c", 1.6), lift("#464c51", 1.35), lift("#2d3135", 1.7)]
        # Rautenmuster: diagonale Platten
        rnd = random.Random(17)
        step = 1.0
        for i in range(-30, 30):
            for j in range(-30, 30):
                cx, cy = i * step, 11 + j * step
                cx2 = cx + (step / 2 if j % 2 else 0)
                d = step / 2
                q = Polygon([(cx2, cy - d), (cx2 + d, cy), (cx2, cy + d), (cx2 - d, cy)]).intersection(region)
                if not q.is_empty:
                    ops.geom(q, fill=rnd.choice(cols), outline=alpha(lift("#22262a", 1.4), 255), width=0.025)
        for gx, gy in ((0, 15.5), (-4, 19.6), (0, 19.6), (4, 19.6), (-3, 12.8), (3, 12.8)):
            ops.glow(gx, gy - 0.6, 1.6, WARM, 0.3)
    elif key == "telefon":
        cols = [lift("#a05630", 1.0), lift("#a8562a", 0.95)]
        tiles(ops, region, x0, y0, x1, y1, 2.0, 1.0, cols, lift("#8e4823", 1.1), seed=21)
        # Siebziger-Rundteppich (flach, begehbar) in der freien Raummitte: Ringe in Orange, Creme, Braun
        rcx, rcy = 15.0, 17.4
        for r, col in ((1.6, "#c8702e"), (1.4, "#efd9a8"), (1.22, "#8e4823"), (1.0, "#c8702e"), (0.75, "#efd9a8"), (0.5, "#8e4823"), (0.25, "#e0b04a")):
            ops.ellipse(rcx, rcy, r, r, fill=alpha(lift(col, 1.05), 215))
        ops.ellipse(rcx, rcy, 1.6, 1.6, outline=alpha(lift("#5a2a12", 1.2), 200), width=0.03)
        # kleine Kreise als Echo des Teppichs an den Waenden
        for cx_, cy_ in ((10.6, 14.0), (16.8, 14.1), (10.4, 18.6)):
            ops.ellipse(cx_, cy_, 0.5, 0.5, fill=alpha(lift("#c8702e", 1.2), 90))
            ops.ellipse(cx_, cy_, 0.28, 0.28, fill=alpha(lift("#efd9a8", 1.0), 110))
        ops.glow(rcx, rcy, 2.4, WARM, 0.22)
    elif key == "technikhalle":
        # Riffelblech: kurze diagonale Rippen
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
        # Plattenstoesse
        for xx in range(8, 21, 2):
            ops.line([(xx, y0), (xx, y1)], fill=lift("#363a3f", 1.2), width=0.03)
        # Warnstreifen um Maschinen
        hazard(ops, 8.7, 4.6, 14.9, 4.9)
        hazard(ops, 14.7, 5.2, 19.3, 5.45)
        # Ausstellungsbeleuchtung
        for gx, gy in ((11, 5.2), (16.2, -0.9), (17, 6.2)):
            ops.glow(gx, gy, 2.4, WARM, 0.28)
    elif key == "werkstatt":
        cols = [lift("#9aa3a6", 1.3), lift("#929a9d", 1.3)]
        tiles(ops, region, x0, y0, x1, y1, 0.5, 0.5, cols, lift("#7b8488", 1.2), seed=23, fuge_w=0.02)
        # Scanner-Podest
        ops.rect(15, -9.5, 17, -7.5, fill=lift("#8b949a", 1.25), outline=OUTLINE, width=0.04)
        ops.ellipse(16, -8.5, 0.8, 0.8, outline=alpha(hexc("#6fd6ff"), 220), width=0.05)
        ops.glow(16, -8.5, 2.2, hexc("#d8e6ec"), 0.35)
    elif key == "depot":
        speckle(ops, region, 1500, [lift("#66635e"), lift("#3e3c39", 1.4)], 0.01, 0.03, seed=29)
        for xx in (23.5, 26.5):
            ops.line([(xx, y0), (xx, y1)], fill=lift("#423f3b", 1.3), width=0.03)
        for yy in range(-20, -6, 3):
            ops.line([(x0, yy), (x1, yy)], fill=lift("#423f3b", 1.3), width=0.03)
        # Gassenmarkierung
        for gy in (-11.4, -15.4):
            ops.line([(22.9, gy), (28.3, gy)], fill=alpha(hexc("#d4b13c"), 170), width=0.06)
        ops.line([(21.9, -19.2), (21.9, -7.0)], fill=alpha(hexc("#d4b13c"), 170), width=0.06)
        hazard(ops, 21.8, -19.95, 22.8, -19.6)
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
        ops.glow(-28.5, -16.8, 2.2, hexc("#b7c4c8"), 0.3)
    elif key == "haustechnik":
        speckle(ops, region, 700, [lift("#5c574f"), lift("#433f39", 1.3)], 0.01, 0.03, seed=31)
        for (ox, oy, r) in ((-24.2, -9.3, 0.5), (-27.0, -11.4, 0.35)):
            ops.ellipse(ox, oy, r, r * 0.7, fill=alpha((20, 20, 24, 255), 70))
        hazard(ops, -28.6, -11.6, -28.3, -8.6, vertical=True)
        ops.ellipse(-25.5, -9.5, 0.22, 0.22, fill=lift("#7b8288"), outline=OUTLINE, width=0.03)  # Gully
    elif key == "shop":
        cols = [lift("#7ea89a", 1.2), lift("#5a7f72", 1.35)]
        rnd = random.Random(37)
        yy, i = y0, 0
        while yy < y1:
            xx, j = x0, 0
            while xx < x1:
                t = sbox(xx, yy, xx + 0.6, yy + 0.6).intersection(region)
                ops.geom(t, fill=cols[(i + j) % 2])
                xx += 0.6; j += 1
            yy += 0.6; i += 1
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
            ops.line([(26, yy), (29, yy)], fill=mark, width=0.1)
        ops.line([(27, -5.5), (27, -2.5)], fill=mark, width=0.1)
        # Rampe (Deck 0): Betonrampe mit Rillen und Warnkante
        ops.rect(21.5, -2, 24.5, 8, fill=lift("#6a6864", 1.25))
        yy = -2
        while yy < 8:
            ops.line([(21.5, yy), (24.5, yy)], fill=lift("#5d5c58", 1.15), width=0.025)
            yy += 0.5
        ops.rect(21.5, -6, 24.5, -2, fill=lift("#5d5c58", 1.3))           # Karrenschraege
        for i in range(8):
            ops.line([(21.5, -6 + i * 0.5), (24.5, -6 + i * 0.5)], fill=lift("#4f4e4a", 1.2), width=0.03)
        hazard(ops, 24.3, -2, 24.55, 6, vertical=True)
        hazard(ops, 21.5, 7.8, 24.5, 8.05)
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
            face = Polygon([(x0, y0), (x1, y1), (x1, y1 + face_h), (x0, y0 + face_h)]).intersection(solid.buffer(0.001))
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
            # Boden des Nachbarraums ragen
            probe = LineString([(mx, my), (mx, my + face_h)]).intersection(solid)
            fh_eff = min(face_h, probe.length) if not probe.is_empty else face_h
            face_decor(ops, owner, x0, y0, x1, y1, fh_eff, wall)
            # Kontaktschatten auf dem Boden
            sh = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.28), (x0, y0 - 0.28)]).intersection(walk)
            ops.geom(sh, fill=(0, 0, 0, 55))
            sh2 = Polygon([(x0, y0), (x1, y1), (x1, y1 - 0.12), (x0, y0 - 0.12)]).intersection(walk)
            ops.geom(sh2, fill=(0, 0, 0, 45))


def face_decor(ops, owner, x0, y0, x1, y1, fh, wall):
    if abs(y1 - y0) > 0.01:
        return  # nur waagerechte Stirnseiten bekommen Deko
    a, b = sorted((x0, x1))
    y = y0
    if owner == "galerie":
        # kleine goldgerahmte Bilder auf der Bespannung
        rnd = random.Random(int(a * 10))
        x = a + 0.6
        while x < b - 0.6:
            ops.rect(x - 0.25, y + 0.12, x + 0.25, y + 0.42, fill=hexc("#a8843c"), outline=OUTLINE, width=0.02)
            ops.rect(x - 0.19, y + 0.16, x + 0.19, y + 0.38, fill=rnd.choice([hexc("#3f6f9a"), hexc("#7a8a4a"), hexc("#b0603a"), hexc("#c9b27a")]))
            x += 1.6
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
    elif owner == "werkstatt" or owner == "shop":
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
    elif owner == "planetarium":
        rnd = random.Random(99)
        for _ in range(int((b - a) * 3)):
            ops.ellipse(rnd.uniform(a, b), y + rnd.uniform(0.12, 0.42), 0.012, 0.012, fill=hexc("#cfe0ff"))
    elif owner == "rotunde":
        # Marmorfelder mit Messingrahmen auf der Bespannung
        brass = lift("#b08a3c", 1.2)
        marble = shade(wall, 1.1)
        xx = a + 0.15
        while xx + 0.5 < b - 0.1:
            w = min(0.7, b - 0.1 - xx)
            p0, p1 = y + 0.12, y + max(0.3, fh - 0.1)
            ops.rect(xx, p0, xx + w, p1, fill=marble, outline=brass, width=0.02)
            ops.line([(xx + 0.1, p0 + 0.04), (xx + w - 0.15, p1 - 0.05)], fill=alpha(shade(marble, 0.85), 160), width=0.015)
            xx += w + 0.12
    elif owner == "mineralien":
        # beleuchtete Wandnischen mit Kristallstufen
        rnd = random.Random(int(a * 13))
        xx = a + 0.35
        while xx + 0.5 < b - 0.2:
            n0, n1 = y + 0.4, y + max(0.6, fh - 0.1)
            ops.rect(xx, n0, xx + 0.5, n1, fill=hexc("#1e2a2e"), outline=OUTLINE, width=0.02)
            ops.glow(xx + 0.25, (n0 + n1) / 2, 0.4, WARM, 0.35)
            col = rnd.choice([hexc("#9d6cc7"), hexc("#e0b04a"), hexc("#d9e4ec"), hexc("#3f9e6e"), hexc("#5f9bd0")])
            for dx, hh in ((0.15, 0.12), (0.25, 0.2), (0.33, 0.14)):
                ops.poly([(xx + dx - 0.04, n0 + 0.04), (xx + dx + 0.04, n0 + 0.04), (xx + dx + 0.01, n0 + 0.04 + hh), (xx + dx - 0.01, n0 + 0.04 + hh)],
                         fill=col, outline=OUTLINE, width=0.012)
            xx += 0.9
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
    building = Polygon(walk.buffer(WALL_OUT, join_style=2).exterior)
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

    # Kronenkante: helle Linie entlang der Oberkante der Stirnseiten gibt der Wand Volumen
    for p in ([walk] if walk.geom_type == "Polygon" else list(walk.geoms)):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            ops.line(ring, fill=OUTLINE, width=0.09)
    ops.poly(list(building.exterior.coords)[:-1], outline=OUTLINE, width=0.09)

    exit_signs(ops)
    return ops


def render_floor(walk, ppm):
    ops = build_floor_ops(walk)
    x0, y0, x1, y1 = L.BOUNDS
    img = ops.render(x0, y0, x1, y1, ppm, VOID)
    return ambient_occlusion(img, walk, x0, y0, x1, y1)


# ================================================================== Objekte

class Prop:
    """Ein Objekt-Sprite: Leinwand in Weltkoordinaten, Standlinie base_y (-> z-Sortierung)."""

    def __init__(self, x0, y0, x1, y1, h, ppm, base_y=None):
        pad = 0.3
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


EXHIBITS_TALL = ["mineral", "urne", "schaedel", "modell", "amphore", "statue"]
EXHIBITS_FLAT = ["papyrus", "muenzen", "fossil", "kaefer"]


def draw_vitrine(p, x0, y0, x1, y1, rnd, ex=None, low=False):
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
    c.poly([(x0 + 0.03, y0 + zt0), (x1 - 0.03, y0 + zt0), (x1 - 0.03, y1 + zt0), (x0 + 0.03, y1 + zt0)], fill=lift("#d8cfb0", 1.05))
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
    alu = hexc("#c0c8cc")
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
    "schwungrad": 2.1, "oldtimer": 1.3, "turbine": 1.9, "werktisch": 0.9, "regal_werk": 1.8,
    "hochregal": 2.4, "kiste": 0.9, "co2": 1.6, "lieferwagen": 2.3, "fass": 0.9,
    "vitrine": 1.6, "tischvitrine": 1.0, "tresorvitrine": 2.1, "bank": 0.45, "cafetisch": 0.75,
    "trog": 0.6, "admintisch": 0.9, "vermittlungstisch": 0.8, "glaswand": 2.0, "resttisch": 0.9,
    "dino": 1.6, "dino_rex": 6.2, "lampe": 5.0,
    # "Rex erwacht" (25.09.): Kopf und Unterkiefer als eigene Sprites (beweglich), zwei Stationen
    "dino_rex_head": 6.2, "dino_rex_jaw": 6.2, "spieluhr": 1.3, "nachtlicht": 1.3,
}

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
        draw_vitrine(p, x0, y0, x1, y1, rnd, ex=rnd.choice(EXHIBITS_FLAT), low=True)
    elif kind == "tresorvitrine":
        steel = lift("#4b5259", 1.5)
        p.box(x0, y0, x1, y1, 0, 0.6, shade(steel, 1.15), steel)
        # Stahlsockel: Nietenreihe, Schloss, Innenboden mit Samt und Spot
        for i in range(int((x1 - x0) / 0.25)):
            c.ellipse(x0 + 0.15 + i * 0.25, y0 + 0.08, 0.02, 0.02, fill=shade(steel, 1.3))
        c.ellipse(cx, y0 + 0.6 * K * 0.5, 0.06, 0.06, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
        zt0 = 0.6 * K
        c.poly([(x0 + 0.04, y0 + zt0), (x1 - 0.04, y0 + zt0), (x1 - 0.04, y1 + zt0), (x0 + 0.04, y1 + zt0)], fill=lift("#5a2a2a", 1.5))
        c.glow(cx, cy + zt0, 1.1, WARM, 0.55)
        exhibit(p, "mineral", cx, cy - 0.1, 0.6, random.Random(5))
        exhibit(p, "mineral", cx - 0.35, cy + 0.3, 0.6, random.Random(9))
        exhibit(p, "muenzen", cx + 0.3, cy + 0.45, 0.6, random.Random(4))
        p.box(x0 + 0.04, y0, x1 - 0.04, y1, 0.6, 1.5, alpha(hexc("#dff3ff"), 70), alpha(hexc("#bfe3f5"), 45),
              ol=steel, w=0.07, glass=True)
        c.line([(x0 + 0.2, y0 + 0.8 * K), (x0 + 0.5, y0 + 1.9 * K)], fill=alpha((255, 255, 255, 255), 140), width=0.04)
        c.line([(x0 + 0.6, y0 + 0.8 * K), (x0 + 0.75, y0 + 1.3 * K)], fill=alpha((255, 255, 255, 255), 80), width=0.03)
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
        c.text(cx, cy + (zt + 0.08) / 2, "T. REX", 0.11, hexc("#2a2422"))
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
        gold = lift("#b8923e", 1.35)
        blue, red, skin = hexc("#2f4f8a"), hexc("#a83636"), hexc("#d9b25c")
        stone_t, stone_f = lift("#4c4a46", 1.8), lift("#4c4a46", 1.5)
        p.box(x0 - 0.1, y0 - 0.1, x1 + 0.1, y1 + 0.1, 0, 0.35, stone_t, stone_f)
        # Mumienfoermiger Deckel: Kasten + gerundetes Kopfende, Kopf im Norden
        p.box(x0, y0, x1, y1 - 0.3, 0.35, 0.55, gold, shade(gold, 0.85))
        zt = 0.9
        top_y0, top_y1 = y0 + zt * K, y1 + zt * K
        hw = (x1 - x0) / 2
        c.ellipse(cx, top_y1 - 0.3, hw, 0.3, fill=gold, outline=OUTLINE)
        c.rect(x0, top_y1 - 0.5, x1, top_y1 - 0.3, fill=gold)
        c.line([(x0, top_y1 - 0.5), (x0, top_y1 - 0.3)], fill=OUTLINE, width=OUT_W)
        c.line([(x1, top_y1 - 0.5), (x1, top_y1 - 0.3)], fill=OUTLINE, width=OUT_W)
        # Nemes-Kopftuch (blau-gold gestreift) mit Gesicht und Zeremonialbart
        c.ellipse(cx, top_y1 - 0.34, hw - 0.06, 0.26, fill=blue, outline=OUTLINE, width=0.025)
        for i in range(-2, 3):
            c.line([(cx + i * 0.13, top_y1 - 0.62), (cx + i * 0.16, top_y1 - 0.14)], fill=gold, width=0.035)
        c.ellipse(cx, top_y1 - 0.36, 0.17, 0.2, fill=skin, outline=OUTLINE, width=0.025)
        for ex_ in (-0.07, 0.07):
            c.ellipse(cx + ex_, top_y1 - 0.31, 0.045, 0.028, fill=(250, 246, 236, 255), outline=OUTLINE, width=0.012)
            c.ellipse(cx + ex_, top_y1 - 0.31, 0.018, 0.018, fill=OUTLINE)
        c.line([(cx - 0.05, top_y1 - 0.44), (cx + 0.05, top_y1 - 0.44)], fill=shade(skin, 0.6), width=0.02)
        c.rect(cx - 0.03, top_y1 - 0.62, cx + 0.03, top_y1 - 0.53, fill=blue, outline=OUTLINE, width=0.015)
        # Halskragen (Usech) in Ringen, gekreuzte Arme mit Krummstab und Geissel
        for i, col in enumerate((blue, red, gold, blue)):
            c.ellipse(cx, top_y1 - 0.72, 0.36 - i * 0.07, 0.16 - i * 0.03, fill=col, outline=OUTLINE if i == 0 else None, width=0.02)
        c.line([(cx - 0.3, top_y1 - 1.0), (cx + 0.25, top_y1 - 1.25)], fill=OUTLINE, width=0.14)
        c.line([(cx + 0.3, top_y1 - 1.0), (cx - 0.25, top_y1 - 1.25)], fill=OUTLINE, width=0.14)
        c.line([(cx - 0.3, top_y1 - 1.0), (cx + 0.25, top_y1 - 1.25)], fill=shade(gold, 1.1), width=0.09)
        c.line([(cx + 0.3, top_y1 - 1.0), (cx - 0.25, top_y1 - 1.25)], fill=shade(gold, 1.1), width=0.09)
        c.line([(cx - 0.28, top_y1 - 1.28), (cx - 0.22, top_y1 - 0.92)], fill=blue, width=0.035)
        c.line([(cx + 0.28, top_y1 - 1.28), (cx + 0.22, top_y1 - 0.92), (cx + 0.32, top_y1 - 0.86)], fill=blue, width=0.035)
        # Koerperbaender bis zum Fussende
        yy = top_y1 - 1.45
        i = 0
        while yy > top_y0 + 0.12:
            c.rect(x0 + 0.06, yy - 0.07, x1 - 0.06, yy, fill=blue if i % 2 == 0 else red)
            yy -= 0.16; i += 1
        c.line([(cx, top_y1 - 1.4), (cx, top_y0 + 0.1)], fill=shade(gold, 0.75), width=0.02)
        # Hieroglyphenband an der Front
        fb = y0 + 0.35 * K
        for i in range(int((x1 - x0) / 0.14)):
            gx = x0 + 0.08 + i * 0.14
            if i % 2:
                c.ellipse(gx, fb + 0.16, 0.025, 0.035, fill=blue)
            else:
                c.rect(gx - 0.02, fb + 0.1, gx + 0.02, fb + 0.22, fill=blue)
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
    elif kind == "stellwand":
        felt = lift("#5b2430", 1.55)   # Bespannung wie die Galeriewaende
        # optisch etwas breiter als die Kollision (0,2 m), sonst liest sie sich als Stange
        vx0, vx1 = x0 - 0.06, x1 + 0.06
        p.box(vx0, y0, vx1, y1, 0, 2.2, shade(felt, 1.2), felt)
        zt = 2.2 * K
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
        green = lift("#2f4a3a", 1.9)
        steel = lift("#3b4046", 1.8)
        p.box(x0, y0, x1, y1, 0, 0.3, shade(steel, 1.2), steel)
        # liegender Kessel
        kr = 0.65
        ky0, ky1 = y0 + 0.3, y1 - 0.3
        c.rect(x0 + 0.2, ky0 + 0.3 * K, x1 - 1.2, ky0 + (0.3 + 2 * kr) * K, fill=green, outline=OUTLINE)
        c.rect(x0 + 0.2, ky0 + (0.3 + 2 * kr) * K, x1 - 1.2, ky1 + (0.3 + 2 * kr) * K - 0.2, fill=shade(green, 1.2), outline=OUTLINE)
        for bx in (x0 + 0.8, x0 + 1.8):
            c.rect(bx, ky0 + 0.3 * K, bx + 0.12, ky1 + (0.3 + 2 * kr) * K - 0.2, fill=hexc("#b08a3c"), outline=OUTLINE, width=0.02)
        # Zylinder + Kolben
        p.box(x1 - 1.2, y0 + 0.5, x1 - 0.3, y1 - 0.5, 0.3, 1.0, hexc("#c0c8cc"), lift("#3b4046", 1.9))
        c.line([(x1 - 0.3, y0 + 0.6 + 0.8 * K), (x1 + 0.3, y0 + 0.6 + 0.8 * K)], fill=hexc("#c0c8cc"), width=0.06)
        # Kamin
        p.cyl(x0 + 0.7, cy + 0.2, 0.18, 1.6, 2.0, OUTLINE, steel)
        c.ellipse(x0 + 0.7, cy + 0.2 + 3.6 * K, 0.18, 0.18, fill=(30, 30, 30, 255), outline=OUTLINE, width=0.03)
        c.text(cx - 0.4, ky0 + (0.3 + kr) * K, "1887", 0.25, hexc("#d9b25c"))
    elif kind == "schwungrad":
        # Rad steht in der Ost-West-Ebene (Kurbelwelle N-S, Kolben der Dampfmaschine laeuft E-W):
        # in der schraegen Aufsicht eine Ellipse rx = r, ry = r * K. Lagerboecke vor und hinter dem Rad.
        green = lift("#2f4a3a", 1.9)
        steel = lift("#3b4046", 1.8)
        brass = hexc("#b08a3c")
        r = x1 - cx - 0.08
        z0 = 1.05
        wy = cy + z0 * K
        p.box(cx - 0.22, cy + 0.2, cx + 0.22, cy + 0.5, 0, z0, shade(steel, 1.15), steel, w=0.035)
        # Felge (dick, mit Lichtkante), Speichen, Nabe
        c.ellipse(cx, wy, r, r * K, fill=alpha((0, 0, 0, 255), 40), outline=OUTLINE, width=0.24)
        c.ellipse(cx, wy, r, r * K, fill=None, outline=green, width=0.15)
        c.ellipse(cx, wy + 0.02, r - 0.03, r * K - 0.02, fill=None, outline=shade(green, 1.18), width=0.03)
        for a in range(0, 360, 60):
            ex, ey = cx + (r - 0.08) * math.cos(math.radians(a)), wy + (r * K - 0.06) * math.sin(math.radians(a))
            c.line([(cx, wy), (ex, ey)], fill=OUTLINE, width=0.1)
            c.line([(cx, wy), (ex, ey)], fill=green, width=0.05)
        c.ellipse(cx, wy, 0.18, 0.13, fill=steel, outline=OUTLINE, width=0.03)
        c.ellipse(cx, wy, 0.08, 0.06, fill=brass, outline=OUTLINE, width=0.02)
        # Kurbelzapfen + Pleuel nach Westen zum Zylinder
        px_, py_ = cx - 0.55, wy - 0.28
        c.line([(px_, py_), (cx - 1.25, wy - 0.12)], fill=OUTLINE, width=0.1)
        c.line([(px_, py_), (cx - 1.25, wy - 0.12)], fill=hexc("#c0c8cc"), width=0.05)
        c.ellipse(px_, py_, 0.06, 0.05, fill=brass, outline=OUTLINE, width=0.02)
        p.box(cx - 0.22, cy - 0.5, cx + 0.22, cy - 0.2, 0, z0 - 0.15, shade(steel, 1.15), steel, w=0.035)
        c.rect(cx - 0.3, cy - 0.52, cx + 0.3, cy - 0.44, fill=shade(steel, 0.8), outline=OUTLINE, width=0.025)
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
        # liegendes Turbinengehaeuse (Zylinder in Ost-West-Richtung) auf Sockel + Generator im Osten
        steel = lift("#7b8288", 1.35)
        base_c = lift("#3b4046", 1.7)
        p.box(x0, y0, x1, y1, 0, 0.35, shade(base_c, 1.12), base_c)
        R = (y1 - y0 - 0.7) / 2
        zc = 0.35 + R
        mid = cy + zc * K
        half = R * math.sqrt(1 + K * K)
        gx0 = x1 - 1.0
        tx0, tx1 = x0 + 0.35, gx0
        lo, hi = mid - half, mid + half
        c.rect(tx0, lo, tx1, hi, fill=steel, outline=OUTLINE)
        c.rect(tx0 + 0.03, lo + 0.03, tx1 - 0.03, lo + (hi - lo) * 0.3, fill=shade(steel, 0.8))
        c.rect(tx0 + 0.03, lo + (hi - lo) * 0.62, tx1 - 0.03, hi - 0.03, fill=shade(steel, 1.18))
        c.line([(tx0 + 0.05, lo + (hi - lo) * 0.8), (tx1 - 0.05, lo + (hi - lo) * 0.8)], fill=shade(steel, 1.35), width=0.04)
        # Flanschringe
        n = 4
        for i in range(n + 1):
            fx = tx0 + 0.1 + i * (tx1 - tx0 - 0.2) / n
            c.rect(fx - 0.06, lo - 0.04, fx + 0.06, hi + 0.04, fill=shade(steel, 0.7), outline=OUTLINE, width=0.025)
            for by in (lo + 0.1, hi - 0.1):
                c.ellipse(fx, by, 0.025, 0.025, fill=hexc("#c0c8cc"))
        # Einlass (Westende) mit Schaufelrad
        c.ellipse(tx0, mid, 0.22, half, fill=shade(steel, 0.6), outline=OUTLINE, width=0.04)
        for a in range(0, 360, 45):
            c.line([(tx0, mid), (tx0 + 0.18 * math.cos(math.radians(a)), mid + half * 0.85 * math.sin(math.radians(a)))], fill=shade(steel, 1.1), width=0.025)
        # Generatorblock mit Warnschild
        gen = lift("#2f4a3a", 1.9)
        p.box(gx0, y0 + 0.4, x1 - 0.1, y1 - 0.5, 0.35, 1.5, shade(gen, 1.15), gen)
        c.rect(gx0 + 0.2, y0 + 0.4 + 0.7 * K, x1 - 0.3, y0 + 0.4 + 1.2 * K, fill=hexc("#d4b13c"), outline=OUTLINE, width=0.02)
        c.poly([(gx0 + 0.35, y0 + 0.4 + 0.8 * K), (gx0 + 0.45, y0 + 0.4 + 1.1 * K), (gx0 + 0.55, y0 + 0.4 + 0.8 * K)], fill=hexc("#1e1e1e"))
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
        return [(x + d, sz - 0.03 + d * 0.4), (x - 0.03 + d, sz - 0.28), (x + 0.02 + d, sz - 0.62),
                (x + 0.12 + d, (sz + zb) / 2 - 0.25), (x + 0.22 + d, zb + 0.12), (x + 0.27 + d, zb)]

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
            vertebra(x, 0.16, 0.28 + 0.06 * math.sin((x + 1.4) / 2.2 * math.pi), 0.32, rib=1, spine_w=0.95)
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
        bone(rib_pts(x), 0.06, 0.026, near_set(), smooth=2, ow=0.02)
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
    P0 = P

    def P(x, z):
        return P0(x, 3.12 + (z - 3.12) * 1.45)

    sk = near_set()
    c = real if part in ("all", "jaw") else scrap
    if part == "head":
        REX_RIG["neck"] = P(-2.22, 3.5)
        REX_RIG["jaw"] = P(-2.38, 3.08)
        REX_RIG["eye"] = P(-2.88, 3.9)
    # Unterkiefer zuerst (liegt hinter dem Oberkiefer), Maul leicht geoeffnet
    jaw = blob([(-2.33, 3.14), (-2.4, 2.9), (-2.9, 2.8), (-3.5, 2.74), (-3.97, 2.72), (-4.03, 2.8),
                (-3.55, 2.93), (-3.0, 3.02), (-2.55, 3.1)], (tone(sk[0], 0.94), sk[1], sk[2]), ow=0.03)
    q = P(-2.8, 2.92)
    c.ellipse(q[0], q[1], 0.12, 0.035, fill=HOLE, outline=OL, width=0.016)                 # Unterkieferfenster
    for i in range(12):                                                                     # untere Zaehne
        tx = -3.92 + i * 0.085
        zz = 2.8 + (tx + 3.92) * 0.17
        ln = 0.07 + 0.05 * math.sin(i / 11 * math.pi)
        a, b, t_ = P(tx - 0.025, zz), P(tx + 0.025, zz), P(tx + 0.012, zz + ln)
        c.poly([a, t_, b], fill=TOOTH, outline=OL, width=0.012)
    # Oberschaedel
    c = real if part in ("all", "head") else scrap
    skull = [(-2.28, 3.92), (-2.4, 4.1), (-2.56, 4.17), (-2.74, 4.12), (-2.92, 4.08), (-3.06, 4.14),
             (-3.2, 4.04), (-3.46, 3.92), (-3.74, 3.74), (-3.98, 3.54), (-4.14, 3.34), (-4.16, 3.2),
             (-3.95, 3.13), (-3.45, 3.1), (-2.95, 3.07), (-2.55, 3.04), (-2.34, 3.1), (-2.22, 3.38), (-2.2, 3.66)]
    blob(skull, sk, ow=0.036, smooth=1)
    # Wangenknochen (Jochbein) als dunkleres Band, Nasenkante hell
    c.poly([P(-2.36, 3.13), P(-2.95, 3.12), P(-3.5, 3.15), P(-3.5, 3.24), P(-2.95, 3.25), P(-2.42, 3.3)], fill=sk[1])
    c.line([P(-2.6, 4.12), P(-3.06, 4.1), P(-3.5, 3.9), P(-3.92, 3.58)], fill=sk[2], width=0.03)
    # Schaedelfenster
    def hole(pts_model, smooth=1):
        Q = [P(x, z) for x, z in pts_model]
        Q = chaikin(Q + [Q[0]], smooth)[:-1]
        c.poly(Q, fill=HOLE_RIM)
        cxq = sum(x for x, _ in Q) / len(Q)
        cyq = sum(y for _, y in Q) / len(Q)
        c.poly([(cxq + (x - cxq) * 0.82, cyq + (y - cyq) * 0.8 + 0.008) for x, y in Q], fill=HOLE)
        c.poly(Q, outline=OL, width=0.018)
    hole([(-3.06, 3.74), (-3.28, 3.84), (-3.64, 3.6), (-3.56, 3.4), (-3.14, 3.38)])          # Voraugenfenster
    hole([(-3.72, 3.54), (-3.8, 3.5), (-3.76, 3.43), (-3.68, 3.46)])                         # Oberkieferfenster
    hole([(-2.44, 3.94), (-2.68, 3.9), (-2.72, 3.56), (-2.52, 3.46), (-2.4, 3.66)])          # Schlaefenfenster
    hole([(-3.95, 3.6), (-4.09, 3.45), (-4.03, 3.41), (-3.9, 3.54)])                          # Nasenloch
    # Augenhoehle (Schluesselloch) mit Knochenring und kleinem Glanz
    q = P(-2.88, 3.9)
    c.ellipse(q[0], q[1], 0.1, 0.095, fill=HOLE_RIM, outline=OL, width=0.018)
    c.poly([P(-2.95, 3.84), P(-2.82, 3.84), P(-2.88, 3.6)], fill=HOLE_RIM, outline=OL, width=0.016)
    c.ellipse(q[0], q[1], 0.075, 0.07, fill=HOLE)
    c.poly([P(-2.92, 3.82), P(-2.84, 3.82), P(-2.88, 3.66)], fill=HOLE)
    c.ellipse(q[0] - 0.025, q[1] + 0.025, 0.018, 0.015, fill=(250, 244, 226, 255))
    # Knochenhoecker ueber dem Auge (Postorbitale, Lacrimale)
    for bx, bz, r in ((-2.58, 4.15, 0.06), (-3.06, 4.13, 0.05)):
        q = P(bx, bz)
        c.ellipse(q[0], q[1], r, r * 0.8, fill=sk[2], outline=OL, width=0.018)
    # kleine Gefaessloecher am Oberkiefer
    for i in range(6):
        q = P(-3.9 + i * 0.16, 3.2 + 0.01 * (i % 2))
        c.ellipse(q[0], q[1], 0.013, 0.01, fill=HOLE)
    # obere Zaehne: bananenfoermig, nach hinten gekruemmt, vorn die grossen
    for i in range(14):
        tx = -4.08 + i * 0.095
        zz = 3.14 + (tx + 4.08) * 0.02
        ln = 0.1 + 0.09 * math.sin(min(1.0, (i + 1) / 9) * math.pi) + (0.02 if i % 3 == 1 else 0)
        a, b = P(tx - 0.03, zz + 0.01), P(tx + 0.03, zz + 0.01)
        m = P(tx + 0.012, zz - ln * 0.55)
        t_ = P(tx + 0.03, zz - ln)
        c.poly([a, m, t_, b], fill=TOOTH, outline=OL, width=0.012)
        c.line([P(tx - 0.012, zz - 0.01), P(tx + 0.005, zz - ln * 0.5)], fill=(255, 255, 255, 255), width=0.008)


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


def extra_props():
    """Objekte ohne eigenen Kollider-Eintrag (Deko mit Hoehe)."""
    return list(L.EXTRA_PROPS)


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
