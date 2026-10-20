# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_style.py - Palette, Schriften und gemeinsame Zeichenhelfer der Polaris-Express-Grafik
# (train_floor, train_props, train_consoles, train_extras).
#
# Stil wie museum_art.py / park_art.py: kraeftige dunkle Umrisse, flache Flaechen mit einer hellen Kante oben
# und einer dunklen unten, schraege Aufsicht K = 0,55. Palette "Nachtzug": Mahagoni, Messing, roter Samt,
# gruenes Leder, Riffelblech, Kohle, dazu Nacht, Schnee und warmes Lampenlicht. Farben fuer 2D angehoben
# (Among Us legt die Nacht ueber das Sichtfeld, nicht ueber die Textur).

import math
import os

from PIL import Image, ImageDraw, ImageFont

import museum_art as A
from museum_art import K, OUTLINE, OUT_W, alpha, shade

# ------------------------------------------------------------------ Schriften
# museum_art.Canvas.text und gen_train.font verlangen "arialbd.ttf" (Windows). Auf Linux gibt es die Datei
# nicht; ImageFont.load_default waere winzig. Deshalb wird ImageFont.truetype so ergaenzt, dass fehlende
# Schriften auf metrisch gleiche freie Schriften ausweichen (Liberation Sans = Arial-Metrik).

_FONT_DIRS = ["/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/crosextra", "C:/Windows/Fonts"]
_FONT_FILES = {
    # freie Schriften zuerst, damit Windows und Linux dieselben Bilder liefern (vorher griff auf Windows arialbd/
    # georgiab/impact, auf Linux Liberation/DejaVu/Inter; Textbreiten und Logo wichen ab)
    "bold": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    "regular": ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"],
    "serif": ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf", "georgiab.ttf", "timesbd.ttf"],
    "black": ["Inter-Black.otf", "Inter-ExtraBold.otf", "LiberationSans-Bold.ttf", "impact.ttf", "arialbd.ttf"],
    "mono": ["DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf", "consolab.ttf"],
}
_SUBST = {"arialbd.ttf": "bold", "arial.ttf": "regular", "segoeuib.ttf": "bold"}
_orig_truetype = ImageFont.truetype


def _find(name):
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def font_path(kind="bold"):
    for name in _FONT_FILES.get(kind, _FONT_FILES["bold"]):
        p = _find(name)
        if p:
            return p
    return None


def font(px, kind="bold"):
    """TrueType-Schrift in Pixeln; faellt auf die skalierbare Standardschrift zurueck."""
    p = font_path(kind)
    if p:
        return _orig_truetype(p, max(1, int(px)))
    try:
        return ImageFont.load_default(size=max(1, int(px)))
    except TypeError:
        return ImageFont.load_default()


def _patched_truetype(font_=None, size=10, *args, **kw):
    try:
        return _orig_truetype(font_, size, *args, **kw)
    except OSError:
        base = os.path.basename(str(font_)).lower()
        kind = _SUBST.get(base)
        if kind is None and base.endswith(".ttf"):
            kind = "bold" if "bd" in base or "bold" in base else "regular"
        p = font_path(kind or "bold")
        if p:
            return _orig_truetype(p, size, *args, **kw)
        raise


if ImageFont.truetype is not _patched_truetype:
    ImageFont.truetype = _patched_truetype


# ------------------------------------------------------------------ Palette

def rgba(r, g, b, a=255):
    return (r, g, b, a)


WOOD = (172, 98, 56, 255)            # Mahagoni-Vertaefelung
WOOD_L = (204, 132, 82, 255)
WOOD_D = (124, 66, 36, 255)
WOOD_X = (82, 42, 24, 255)           # Rahmenholz, fast schwarz-braun
OAK = (196, 150, 96, 255)            # helles Holz (Dielen, Tischplatten)
OAK_D = (142, 102, 60, 255)
BRASS = (224, 184, 94, 255)
BRASS_L = (248, 224, 152, 255)
BRASS_D = (156, 120, 54, 255)
VELVET = (170, 44, 58, 255)          # roter Samt
VELVET_L = (206, 76, 90, 255)
VELVET_D = (116, 28, 42, 255)
LEATHER = (60, 110, 76, 255)         # gruenes Leder / Teppich
LEATHER_L = (88, 142, 102, 255)
LEATHER_D = (38, 74, 50, 255)
CREAM = (240, 228, 198, 255)
CREAM_D = (204, 188, 150, 255)
PAPER = (236, 222, 182, 255)
STEEL = (116, 124, 138, 255)
STEEL_L = (156, 164, 178, 255)
STEEL_D = (74, 80, 92, 255)
IRON = (58, 60, 68, 255)
IRON_L = (92, 96, 106, 255)
COAL = (42, 40, 44, 255)
COAL_L = (78, 74, 80, 255)
NIGHT = (30, 36, 66, 255)            # Nachthimmel in den Fenstern
NIGHT_L = (54, 64, 108, 255)
SNOW = (186, 198, 220, 255)
SNOW_L = (226, 234, 246, 255)
SNOW_D = (150, 164, 192, 255)
STAR = (255, 250, 226, 255)
WARM = (255, 214, 140, 255)          # Lampenlicht
BULB = (255, 238, 186, 255)
RED_LAMP = (244, 72, 60, 255)
GREEN_LAMP = (90, 226, 120, 255)
TEAL = (82, 170, 176, 255)
GLASS = (176, 214, 236, 110)
WHITE = (250, 250, 248, 255)
INK = (34, 30, 34, 255)

# Wagenkaesten (von oben): Reisezugwagen nachtblau, Schlusswagen rot, Gepaeckwagen gruen, Tender/Lok schwarz
COACH = (58, 74, 128, 255)
COACH_L = (84, 102, 164, 255)
CABOOSE = (160, 52, 46, 255)
CABOOSE_L = (196, 78, 68, 255)
BAGGAGE = (66, 104, 82, 255)
BAGGAGE_L = (94, 136, 110, 255)
LOCO = (56, 58, 66, 255)
LOCO_L = (88, 90, 100, 255)
LINING = (226, 186, 96, 255)
GROUND = (168, 180, 202, 255)        # Schnee bei Nacht
BALLAST = (88, 86, 92, 255)
SLEEPER = (104, 80, 58, 255)
RAIL = (182, 186, 198, 255)
PANEL = (28, 32, 50, 255)            # Feld des Oberdecks


def body_colors(car_key):
    return {"caboose": (CABOOSE, CABOOSE_L), "baggage": (BAGGAGE, BAGGAGE_L),
            "tender": (LOCO, LOCO_L), "loco": (LOCO, LOCO_L)}.get(car_key, (COACH, COACH_L))


# ------------------------------------------------------------------ Leinwand mit eigener Schrift

class TCanvas(A.Canvas):
    """museum_art.Canvas plus Text in waehlbarer Schrift (Messingschilder in Serifen) und Bild-Einblendung."""

    def textf(self, x, y, s, size_m, fill, kind="bold", anchor="mm", angle=0.0):
        f = font(self.px(size_m), kind)
        px_, py_ = self.p(x, y)
        if not angle and (len(fill) < 4 or fill[3] >= 255):
            self.d.text((px_, py_), s, font=f, fill=fill, anchor=anchor)
            return
        bb = self.d.textbbox((0, 0), s, font=f, anchor="lt")
        w, h = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((2 - bb[0], 2 - bb[1]), s, font=f, fill=fill, anchor="lt")
        if angle:
            layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
        self.img.alpha_composite(layer, (int(px_ - layer.width / 2), int(py_ - layer.height / 2)))

    def image(self, img, x, y):
        """RGBA-Bild (schon im Massstab self.s) mit linker unterer Ecke bei (x, y) einblenden."""
        px_, py_ = self.p(x, y)
        ox, oy = int(round(px_)), int(round(py_ - img.height))
        cx0, cy0 = max(0, ox), max(0, oy)
        cx1, cy1 = min(self.w, ox + img.width), min(self.h, oy + img.height)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        if (cx0, cy0, cx1, cy1) != (ox, oy, ox + img.width, oy + img.height):
            img = img.crop((cx0 - ox, cy0 - oy, cx1 - ox, cy1 - oy))
        self.img.alpha_composite(img, (cx0, cy0))


class TProp(A.Prop):
    def __init__(self, x0, y0, x1, y1, h, ppm, base_y=None, pad=0.3):
        self.c = TCanvas(x0 - pad, y0 - pad, x1 + pad, y1 + h * K + pad, ppm)
        self.base_y = y0 if base_y is None else base_y


class TOps(A.OpList):
    def textf(self, x, y, s, size_m, fill, kind="bold", anchor="mm", angle=0.0):
        x, y = x + self._dx, y + self._dy
        w = len(s) * size_m
        self.add((x - w, y - size_m, x + w, y + size_m), "textf", x, y, s, size_m, fill, kind, anchor, angle)

    def soft_shadow(self, pts, alpha_v=90, blur=0.08):
        pts = self._t(pts)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        self.add((min(xs) - blur * 3, min(ys) - blur * 3, max(xs) + blur * 3, max(ys) + blur * 3), "soft_shadow", pts, alpha_v, blur)


# ------------------------------------------------------------------ Geometrie-Helfer

def rrect_pts(x0, y0, x1, y1, r, n=6):
    """Rechteck mit runden Ecken als Punktliste (gegen den Uhrzeigersinn)."""
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    out = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def ellipse_pts(cx, cy, rx, ry, n=32, a0=0.0, a1=360.0):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


# ------------------------------------------------------------------ Zeichenhelfer (auf Canvas oder OpList)

def gauge(c, cx, cy, r, needle=35.0, face=CREAM, rim=BRASS, red_zone=True, w=None):
    """Manometer: Messingring, cremefarbenes Zifferblatt, Teilstriche, rote Zone, Zeiger."""
    w = w or max(0.012, r * 0.18)
    c.ellipse(cx, cy, r, r, fill=rim, outline=OUTLINE, width=w)
    c.ellipse(cx, cy, r * 0.74, r * 0.74, fill=face, outline=shade(rim, 0.7), width=w * 0.6)
    for k in range(9):
        a = math.radians(200 - k * 220 / 8)
        r0, r1 = r * 0.56, r * 0.68
        c.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))],
               fill=INK, width=w * (0.6 if k % 2 == 0 else 0.35))
    if red_zone:
        pts = [(cx, cy)] + ellipse_pts(cx, cy, r * 0.66, r * 0.66, 6, -30, 5)
        c.poly(pts, fill=alpha(RED_LAMP, 190))
    a = math.radians(200 - needle)
    c.line([(cx - r * 0.12 * math.cos(a), cy - r * 0.12 * math.sin(a)), (cx + r * 0.6 * math.cos(a), cy + r * 0.6 * math.sin(a))],
           fill=(190, 40, 40, 255), width=w * 0.55)
    c.ellipse(cx, cy, r * 0.1, r * 0.1, fill=INK)
    c.ellipse(cx - r * 0.3, cy + r * 0.3, r * 0.16, r * 0.1, fill=alpha(WHITE, 120))


def handwheel(c, cx, cy, r, ry=None, col=BRASS, spokes=5, w=None, rot=0.0):
    """Ventil-Handrad (Ellipse, wenn liegend): Kranz, Speichen, Nabe."""
    ry = r if ry is None else ry
    w = w or max(0.014, r * 0.16)
    c.ellipse(cx, cy, r, ry, outline=OUTLINE, width=w * 2.2)
    c.ellipse(cx, cy, r, ry, outline=col, width=w)
    for k in range(spokes):
        a = math.radians(rot + 360 * k / spokes)
        c.line([(cx, cy), (cx + r * math.cos(a), cy + ry * math.sin(a))], fill=OUTLINE, width=w * 1.5)
        c.line([(cx, cy), (cx + r * math.cos(a), cy + ry * math.sin(a))], fill=col, width=w * 0.7)
    c.ellipse(cx, cy, r * 0.28, ry * 0.28, fill=shade(col, 0.85), outline=OUTLINE, width=w * 0.6)
    c.ellipse(cx, cy, r * 0.1, ry * 0.1, fill=INK)


def pipe(c, pts, r=0.05, col=BRASS, flange=True):
    """Rohrleitung: dunkler Umriss, Grundton, Lichtkante, Flansche an den Enden."""
    c.line(pts, fill=OUTLINE, width=r * 2 + OUT_W * 0.8)
    c.line(pts, fill=col, width=r * 2)
    hi = [(x, y + r * 0.45) for x, y in pts]
    c.line(hi, fill=alpha(shade(col, 1.3), 200), width=r * 0.5)
    if flange:
        for x, y in (pts[0], pts[-1]):
            c.rect(x - r * 0.5, y - r * 1.5, x + r * 0.5, y + r * 1.5, fill=shade(col, 0.9), outline=OUTLINE, width=OUT_W * 0.5)


def rivets(c, pts, r=0.02, col=STEEL_L):
    for x, y in pts:
        c.ellipse(x, y, r, r, fill=col, outline=shade(col, 0.55), width=r * 0.5)
        c.ellipse(x - r * 0.3, y + r * 0.3, r * 0.35, r * 0.3, fill=alpha(WHITE, 140))


def plate(c, cx, cy, w, h, text, size=None, col=BRASS, ink=WOOD_X, kind="serif"):
    """Messingschild mit Schrift und Schrauben in den Ecken."""
    c.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill=col, outline=OUTLINE, width=min(0.03, h * 0.2))
    c.line([(cx - w / 2 + 0.02, cy + h / 2 - 0.012), (cx + w / 2 - 0.02, cy + h / 2 - 0.012)], fill=shade(col, 1.25), width=h * 0.12)
    for sx in (-1, 1):
        c.ellipse(cx + sx * (w / 2 - h * 0.3), cy, h * 0.1, h * 0.1, fill=shade(col, 0.65))
    size = size or h * 0.62
    c.textf(cx, cy, text, size, ink, kind=kind) if hasattr(c, "textf") else c.text(cx, cy, text, size, ink)


def sconce(c, x, y, s=1.0, on=True, glow_r=0.7):
    """Messing-Wandlampe (Frontansicht): Arm, Glasschirm, warmer Schein."""
    if on:
        c.glow(x, y + 0.02 * s, glow_r * s, WARM, 0.55)
    c.line([(x, y - 0.14 * s), (x, y - 0.02 * s)], fill=OUTLINE, width=0.05 * s)
    c.line([(x, y - 0.14 * s), (x, y - 0.02 * s)], fill=BRASS, width=0.025 * s)
    c.ellipse(x, y - 0.14 * s, 0.045 * s, 0.03 * s, fill=BRASS, outline=OUTLINE, width=0.015 * s)
    lit = BULB if on else (120, 110, 90, 255)
    c.poly([(x - 0.09 * s, y + 0.1 * s), (x + 0.09 * s, y + 0.1 * s), (x + 0.07 * s, y - 0.04 * s), (x - 0.07 * s, y - 0.04 * s)],
           fill=lit, outline=OUTLINE, width=0.018 * s)
    c.poly([(x - 0.11 * s, y + 0.1 * s), (x + 0.11 * s, y + 0.1 * s), (x, y + 0.17 * s)], fill=BRASS, outline=OUTLINE, width=0.015 * s)
    if on:
        c.ellipse(x, y + 0.03 * s, 0.035 * s, 0.04 * s, fill=(255, 250, 230, 255))


def lantern(c, x, y, s=1.0, col=RED_LAMP, on=True):
    """Haengende Laterne (Zuglaterne, rot oder weiss): Gehaeuse, Glas, Buegel."""
    if on:
        c.glow(x, y, 0.5 * s, col, 0.5)
    c.line([(x, y + 0.14 * s), (x, y + 0.2 * s)], fill=OUTLINE, width=0.03 * s)
    c.rect(x - 0.07 * s, y - 0.12 * s, x + 0.07 * s, y + 0.12 * s, fill=IRON, outline=OUTLINE, width=0.015 * s)
    c.rect(x - 0.05 * s, y - 0.08 * s, x + 0.05 * s, y + 0.08 * s, fill=col if on else shade(col, 0.4), outline=OUTLINE, width=0.012 * s)
    c.ellipse(x - 0.015 * s, y + 0.02 * s, 0.015 * s, 0.025 * s, fill=alpha(WHITE, 170))
    c.rect(x - 0.08 * s, y + 0.12 * s, x + 0.08 * s, y + 0.15 * s, fill=IRON_L, outline=OUTLINE, width=0.012 * s)


def knife_switch(c, x, y, s=1.0, closed=True):
    c.rect(x - 0.05 * s, y - 0.09 * s, x + 0.05 * s, y + 0.09 * s, fill=(70, 50, 44, 255), outline=OUTLINE, width=0.012 * s)
    c.ellipse(x, y - 0.06 * s, 0.018 * s, 0.018 * s, fill=BRASS, outline=OUTLINE, width=0.008 * s)
    c.ellipse(x, y + 0.06 * s, 0.018 * s, 0.018 * s, fill=BRASS, outline=OUTLINE, width=0.008 * s)
    tip = (x, y + 0.07 * s) if closed else (x + 0.08 * s, y + 0.03 * s)
    c.line([(x, y - 0.06 * s), tip], fill=OUTLINE, width=0.03 * s)
    c.line([(x, y - 0.06 * s), tip], fill=BRASS, width=0.016 * s)
    c.ellipse(tip[0], tip[1], 0.014 * s, 0.014 * s, fill=INK)


def suitcase(c, x0, y0, x1, y1, col=(150, 96, 56, 255), rnd=None):
    """Koffer in Frontansicht (auf einem Regal): Lederkoerper, Messingecken, Griff, Reiseaufkleber."""
    c.rect(x0, y0, x1, y1, fill=col, outline=OUTLINE, width=0.02)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(col, 1.3), width=0.015)
    c.line([(x0 + 0.02, y0 + 0.02), (x1 - 0.02, y0 + 0.02)], fill=shade(col, 0.7), width=0.015)
    ym = (y0 + y1) / 2
    c.line([(x0 + 0.02, ym), (x1 - 0.02, ym)], fill=shade(col, 0.75), width=0.012)
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        c.rect(cx - 0.025, cy - 0.025, cx + 0.025, cy + 0.025, fill=BRASS, outline=OUTLINE, width=0.01)
    hx = (x0 + x1) / 2
    c.line([(hx - 0.05, y1), (hx - 0.04, y1 + 0.04), (hx + 0.04, y1 + 0.04), (hx + 0.05, y1)], fill=OUTLINE, width=0.03)
    c.line([(hx - 0.05, y1), (hx - 0.04, y1 + 0.04), (hx + 0.04, y1 + 0.04), (hx + 0.05, y1)], fill=shade(col, 0.6), width=0.014)
    if rnd is not None and rnd.random() < 0.7:
        sx, sy = rnd.uniform(x0 + 0.08, x1 - 0.08), rnd.uniform(y0 + 0.06, y1 - 0.06)
        c.rect(sx - 0.04, sy - 0.03, sx + 0.04, sy + 0.03, fill=rnd.choice([CREAM, TEAL, VELVET_L, (120, 160, 220, 255)]),
               outline=OUTLINE, width=0.008)


def night_window(c, x0, y0, x1, y1, rnd, frame=BRASS, curtain=True, moon=False):
    """Zugfenster bei Nacht: Messingrahmen, Nachthimmel, Schneehuegel, Sterne, Samtvorhaenge."""
    w, h = x1 - x0, y1 - y0
    c.rect(x0 - 0.03, y0 - 0.03, x1 + 0.03, y1 + 0.03, fill=frame, outline=OUTLINE, width=0.02)
    c.rect(x0, y0, x1, y1, fill=NIGHT)
    hy = y0 + h * 0.3
    pts = [(x0, y0), (x1, y0), (x1, hy + rnd.uniform(-0.02, 0.03))]
    n = max(2, int(w / 0.12))
    for k in range(n):
        t = 1 - (k + 1) / n
        pts.append((x0 + w * t, hy + 0.04 * math.sin(t * 6.0 + rnd.random()) + rnd.uniform(-0.01, 0.015)))
    c.poly(pts, fill=SNOW)
    c.poly([(x0, y0), (x1, y0), (x1, y0 + h * 0.08), (x0, y0 + h * 0.08)], fill=SNOW_D)
    for _ in range(int(w * h * 60) + 2):
        sx, sy = rnd.uniform(x0 + 0.02, x1 - 0.02), rnd.uniform(hy + 0.06, y1 - 0.02)
        r = rnd.choice((0.006, 0.008, 0.011))
        c.ellipse(sx, sy, r, r, fill=STAR)
    if moon:
        mx, my = x0 + w * 0.7, y0 + h * 0.75
        c.ellipse(mx, my, 0.05, 0.05, fill=(250, 244, 214, 255))
        c.ellipse(mx + 0.025, my + 0.012, 0.042, 0.042, fill=NIGHT)
    c.rect(x0, y0, x1, y1, outline=shade(frame, 0.7), width=0.012)
    c.line([(x0 + 0.02, y1 - 0.02), (x0 + 0.02, y0 + 0.06)], fill=alpha(WHITE, 90), width=0.012)
    if curtain:
        cw = min(0.12, w * 0.22)
        for sx, a, b in ((-1, x0 - 0.02, x0 + cw), (1, x1 - cw, x1 + 0.02)):
            c.poly([(a, y0 - 0.02), (b, y0 - 0.02), (b - sx * cw * 0.3, y1 + 0.02), (a + sx * cw * 0.0, y1 + 0.02)]
                   if sx > 0 else [(a, y0 - 0.02), (b, y0 - 0.02), (b, y1 + 0.02), (a, y1 + 0.02)],
                   fill=VELVET, outline=OUTLINE, width=0.015)
            for k in range(2):
                fx = a + (b - a) * (0.3 + 0.35 * k)
                c.line([(fx, y0), (fx, y1)], fill=VELVET_D, width=0.012)
            c.line([(a + 0.01, y0 + h * 0.4), (b - 0.01, y0 + h * 0.4)], fill=BRASS, width=0.02)
        c.line([(x0 - 0.06, y1 + 0.04), (x1 + 0.06, y1 + 0.04)], fill=OUTLINE, width=0.03)
        c.line([(x0 - 0.06, y1 + 0.04), (x1 + 0.06, y1 + 0.04)], fill=BRASS, width=0.016)
        for ex in (x0 - 0.06, x1 + 0.06):
            c.ellipse(ex, y1 + 0.04, 0.02, 0.02, fill=BRASS, outline=OUTLINE, width=0.01)


def paneling(c, x0, y0, x1, y1, pw=0.6, col=WOOD, dado=True, seed=1):
    """Holzvertaefelung in Frontansicht: Fuellungen mit Rahmen, Lambris mit Leiste unten."""
    c.rect(x0, y0, x1, y1, fill=col)
    h = y1 - y0
    d0 = y0 + h * 0.34 if dado else y0
    if dado:
        c.rect(x0, y0, x1, d0, fill=shade(col, 0.86))
        n = max(1, int(round((x1 - x0) / (pw * 0.75))))
        for k in range(n):
            a = x0 + (x1 - x0) * k / n + 0.04
            b = x0 + (x1 - x0) * (k + 1) / n - 0.04
            if b - a > 0.08:
                c.rect(a, y0 + 0.08, b, d0 - 0.05, fill=shade(col, 0.95), outline=shade(col, 0.6), width=0.012)
                c.line([(a + 0.01, d0 - 0.06), (b - 0.01, d0 - 0.06)], fill=shade(col, 1.2), width=0.01)
        c.rect(x0, d0 - 0.025, x1, d0 + 0.02, fill=shade(col, 1.28))
        c.line([(x0, d0 + 0.02), (x1, d0 + 0.02)], fill=shade(col, 0.55), width=0.01)
        c.rect(x0, y0, x1, y0 + 0.07, fill=shade(col, 0.55))
    n = max(1, int(round((x1 - x0) / pw)))
    for k in range(n):
        a = x0 + (x1 - x0) * k / n + 0.035
        b = x0 + (x1 - x0) * (k + 1) / n - 0.035
        if b - a > 0.08:
            c.rect(a, d0 + 0.07, b, y1 - 0.09, fill=shade(col, 1.06), outline=shade(col, 0.62), width=0.012)
            c.line([(a + 0.012, y1 - 0.1), (b - 0.012, y1 - 0.1)], fill=shade(col, 1.25), width=0.01)
            c.line([(a + 0.012, d0 + 0.08), (a + 0.012, y1 - 0.1)], fill=shade(col, 1.18), width=0.008)
    c.rect(x0, y1 - 0.06, x1, y1, fill=shade(col, 1.22))
    c.line([(x0, y1 - 0.06), (x1, y1 - 0.06)], fill=shade(col, 0.6), width=0.01)


def steel_wall(c, x0, y0, x1, y1, col=STEEL, plate_w=0.8, seed=1):
    """Genietete Stahlplatten in Frontansicht."""
    c.rect(x0, y0, x1, y1, fill=col)
    h = y1 - y0
    n = max(1, int(round((x1 - x0) / plate_w)))
    for k in range(n):
        a = x0 + (x1 - x0) * k / n
        b = x0 + (x1 - x0) * (k + 1) / n
        c.rect(a + 0.01, y0 + 0.01, b - 0.01, y1 - 0.01, fill=shade(col, 1.0 + 0.05 * ((k + seed) % 2)), outline=shade(col, 0.6), width=0.014)
        c.line([(a + 0.02, y1 - 0.03), (b - 0.02, y1 - 0.03)], fill=shade(col, 1.22), width=0.012)
        pts = [(a + 0.05 + i * 0.11, y1 - 0.06) for i in range(int((b - a - 0.1) / 0.11) + 1)]
        pts += [(a + 0.05 + i * 0.11, y0 + 0.06) for i in range(int((b - a - 0.1) / 0.11) + 1)]
        rivets(c, pts, 0.014, shade(col, 1.25))
    c.rect(x0, y0, x1, y0 + min(0.07, h * 0.12), fill=shade(col, 0.6))
