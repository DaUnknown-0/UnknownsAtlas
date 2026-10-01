# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# handdraw.py - gemeinsame Hilfen fuer den Stil "Among Us, leicht handgezeichnet" (Stilblatt 2026-10-01),
# fuer alle drei Generatoren (Park: park_floor/park_decor/park_art, Museum: museum_art, Wald: gen_wald).
#
# Regeln, die hier umgesetzt sind:
#   - Umrisse mit minimalem Zittern (ca. 0,5 px in Spielaufloesung), Linienstaerke leicht schwankend,
#     keine doppelten Skizzenstriche: wobble() und ink()
#   - Fugen und Plattenkanten unregelmaessig: stone_grid() liefert Steine mit versetzten, gekippten,
#     geteilten oder fehlenden Steinen; chip() und crack() fuer abgeschlagene Ecken und Risse
#   - leichtes Papierkorn 3 bis 5 % ueber dem Bodenbild: paper_grain()
#   - Schraffur nur als seltener Akzent: hatch()
#   - Massstab fuer Abnahme-Bilder: crewmate() (Spielerfigur-Silhouette in Originalgroesse)
# Alles deterministisch (feste Seeds), alle Masse in Weltmetern, sofern nicht "px" im Namen steht.

import math
import random

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Point, Polygon, box

AMP = 0.006          # Standard-Zittern in m (ca. 1 px bei 180 px/m, 0,5 px bei 80 px/m)
STEP = 0.08          # Stuetzpunktabstand beim Zittern in m


# ------------------------------------------------------------------ Rauschen

class Noise1:
    """Glattes 1D-Rauschen (Summe weniger Sinuswellen) auf -1..1, periodisch mit Periode `period`."""

    def __init__(self, seed, period=1.0, waves=4, lo=1, hi=5):
        rnd = random.Random(seed)
        self.period = period
        self.terms = [(rnd.randint(lo, hi), rnd.uniform(0, math.tau), rnd.uniform(0.5, 1.0)) for _ in range(waves)]
        self.norm = sum(a for _k, _p, a in self.terms) or 1.0

    def __call__(self, t):
        x = t / self.period * math.tau
        return sum(a * math.sin(k * x + p) for k, p, a in self.terms) / self.norm


# ------------------------------------------------------------------ Zittern und Strich

def wobble(pts, amp=AMP, seed=0, step=STEP, closed=False):
    """Polylinie (oder Polygon, closed=True) in Weltmetern mit minimalem Zittern: alle `step` m ein
    Stuetzpunkt, senkrecht zur Linie um ein glattes Rauschen der Amplitude `amp` verschoben. Ecken
    bleiben Ecken (die Verschiebung dort ist klein), die Linie bekommt aber die leichte Unruhe einer
    Hand. Rueckgabe: Punktliste (bei closed ohne Wiederholung des ersten Punkts)."""
    pts = list(pts)
    if closed and len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 2:
        return pts
    segs = list(zip(pts, pts[1:] + ([pts[0]] if closed else [])))
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs) or 1.0
    slow = Noise1(seed, period=total, waves=5, lo=2, hi=9)
    fast = Noise1(seed + 101, period=total, waves=4, lo=max(3, int(total / 0.25)), hi=max(4, int(total / 0.12)))
    out = []
    s = 0.0
    for i, (a, b) in enumerate(segs):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        if ln < 1e-9:
            continue
        nx, ny = -dy / ln, dx / ln
        n = max(1, int(ln / step))
        for k in range(n):
            t = k / n
            x, y = a[0] + dx * t, a[1] + dy * t
            # an den Ecken (t = 0) nur ein Drittel der Amplitude, sonst reissen rechte Winkel auf
            f = 1.0 if k > 0 else 0.35
            d = (slow(s) * 0.7 + fast(s) * 0.3) * amp * f
            out.append((x + nx * d, y + ny * d))
            s += ln / n
    if not closed:
        out.append(pts[-1])
    return out


def wobble_rect(x0, y0, x1, y1, amp=AMP, seed=0, step=STEP):
    return wobble([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], amp, seed, step, closed=True)


def wobble_ellipse(cx, cy, rx, ry, amp=AMP, seed=0, n=None):
    n = n or max(12, int((rx + ry) * math.pi / STEP))
    pts = [(cx + rx * math.cos(k * math.tau / n), cy + ry * math.sin(k * math.tau / n)) for k in range(n)]
    return wobble(pts, amp, seed, step=STEP / 2, closed=True)


def ink(d, pxpts, fill, width_px, seed=0, var=0.25, closed=False):
    """Strich mit leicht schwankender Staerke auf einem PIL-ImageDraw (Pixelkoordinaten): je Segment
    eine Breite aus einem glatten Rauschen (+-var), runde Gelenke, damit nichts aufreisst."""
    pxpts = list(pxpts)
    if closed and len(pxpts) > 1:
        pxpts = pxpts + [pxpts[0]]
    if len(pxpts) < 2:
        return
    nz = Noise1(seed, period=max(1, len(pxpts) - 1), waves=3, lo=1, hi=4)
    for i in range(len(pxpts) - 1):
        w = max(1, int(round(width_px * (1 + var * nz(i)))))
        a, b = pxpts[i], pxpts[i + 1]
        d.line([a, b], fill=fill, width=w)
        if w >= 3:
            r = w / 2 - 0.5
            d.ellipse([b[0] - r, b[1] - r, b[0] + r, b[1] + r], fill=fill)


# ------------------------------------------------------------------ Fugenraster

class Stone:
    __slots__ = ("pts", "x0", "y0", "x1", "y1", "tone", "sunk", "chip", "crack", "worn", "gap", "row", "col")

    def __init__(self, pts, tone, row, col):
        self.pts = pts
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.x0, self.y0, self.x1, self.y1 = min(xs), min(ys), max(xs), max(ys)
        self.tone = tone
        self.sunk = False
        self.chip = None
        self.crack = None
        self.worn = False
        self.gap = False        # fehlender Stein: die Flaeche ist Fugensand
        self.row = row
        self.col = col


def _rot(pts, cx, cy, a):
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def stone_grid(x0, y0, x1, y1, sw, sh, seed=1, joint=0.03, jitter=0.1, tilt=0.03, skip=0.03, split=0.1,
               merge=0.05, periodic=False, bond=0.5, rounding=0.0):
    """Unregelmaessiges Fugenraster in Weltmetern. Reihen etwa `sh` hoch, Steine etwa `sw` breit,
    Laeuferverband (Versatz `bond` je Reihe, bond=None: zufaelliger Versatz). Rueckgabe: Liste von
    Stone (Polygon ohne Fugen).
      jitter   Anteil, um den Reihenhoehen und Steinbreiten schwanken
      tilt     maximale Kippung eines Steins (rad)
      skip     Anteil fehlender Steine (die Luecke bleibt Fugensand)
      split    Anteil halbierter Steine, merge Anteil doppelt breiter Steine
      rounding alle Ecken leicht abfasen (0..0.3 der Kantenlaenge): Kopfstein statt Klinker
      periodic=True: die Kanten des Rechtecks sind Nahtstellen (Kachel), Reihen und Spalten gehen auf
    Reihenkanten sind leicht wellig, so dass benachbarte Steine nicht auf einer Geraden sitzen."""
    rnd = random.Random(seed)
    W, H = x1 - x0, y1 - y0
    rows = max(1, int(round(H / sh)))
    hs = [sh * rnd.uniform(1 - jitter, 1 + jitter) for _ in range(rows)]
    f = H / sum(hs)
    hs = [h * f for h in hs]
    edges = [y0]
    for h in hs:
        edges.append(edges[-1] + h)
    edges[-1] = y1
    waves = [Noise1(seed * 7 + r, period=W, waves=3, lo=1, hi=3) for r in range(rows + 1)]
    wamp = sh * jitter * 0.35

    def edge_y(r, x):
        if periodic and (r == 0 or r == rows):
            return edges[r]
        return edges[r] + waves[r]((x - x0)) * wamp

    stones = []
    for r in range(rows):
        if bond is None:
            off = rnd.uniform(0.15, 0.85) * sw
        else:
            off = (bond * sw * (r % 2)) + rnd.uniform(-0.15, 0.15) * sw
        widths = []
        total = 0.0
        while total < W + sw:
            w = sw * rnd.uniform(1 - jitter, 1 + jitter)
            u = rnd.random()
            if u < split:
                w *= 0.5
            elif u < split + merge:
                w *= 1.8
            widths.append(w)
            total += w
        if periodic:
            # Breiten so skalieren, dass die Reihe genau aufgeht (Naht)
            k = int(round(W / sw))
            widths = widths[:max(1, k)]
            f = W / sum(widths)
            widths = [w * f for w in widths]
        x = x0 - off
        c = 0
        for w in widths:
            xa, xb = x, x + w
            x = xb
            c += 1
            if xb <= x0 and not periodic:
                continue
            if xa >= x1 and not periodic:
                break
            ya0, ya1 = edge_y(r, xa), edge_y(r, xb)
            yb0, yb1 = edge_y(r + 1, xa), edge_y(r + 1, xb)
            j = joint / 2
            pts = [(xa + j, ya0 + j), (xb - j, ya1 + j), (xb - j, yb1 - j), (xa + j, yb0 - j)]
            cx, cy = (xa + xb) / 2, (ya0 + yb0) / 2
            if rnd.random() < skip:
                st = Stone(pts, 0.0, r, c)
                st.gap = True
                stones.append(st)
                continue
            if tilt:
                pts = _rot(pts, cx, cy, rnd.uniform(-tilt, tilt))
            if rounding:
                pts = round_corners(pts, rnd, rounding)
            st = Stone(pts, rnd.uniform(-1, 1), r, c)
            u = rnd.random()
            st.sunk = u < 0.05
            st.worn = u > 0.86
            if rnd.random() < 0.14:
                st.chip = chip(pts, rnd)
            if rnd.random() < 0.07:
                st.crack = crack(pts, rnd)
            stones.append(st)
    return stones


def jitter_grid(x0, y0, x1, y1, s, seed=1, jitter=0.06, periodic=True, sy=None):
    """Fliesen- oder Schachbrettraster s x s (sy: eigene Hoehe) mit GEMEINSAM verschobenen Eckpunkten:
    jede Ecke wandert um bis zu jitter * s, die Fliesen sitzen dadurch leicht schief, bleiben aber
    lueckenlos. periodic=True: die Kanten des Rechtecks sind Nahtstellen (gleiche Verschiebung an
    beiden Raendern). Rueckgabe: Liste (row, col, [4 Punkte])."""
    sy = s if sy is None else sy
    rnd = random.Random(seed)
    W, H = x1 - x0, y1 - y0
    nx, ny = max(1, int(round(W / s))), max(1, int(round(H / sy)))
    sx, sy = W / nx, H / ny
    jit = {}
    for j in range(ny + 1):
        for i in range(nx + 1):
            ii, jj = (i % nx, j % ny) if periodic else (i, j)
            if (ii, jj) not in jit:
                jit[(ii, jj)] = (rnd.uniform(-jitter, jitter) * sx, rnd.uniform(-jitter, jitter) * sy)
    def corner(i, j):
        dx, dy = jit[(i % nx, j % ny) if periodic else (i, j)]
        return (x0 + i * sx + dx, y0 + j * sy + dy)
    out = []
    for j in range(ny):
        for i in range(nx):
            out.append((j, i, [corner(i, j), corner(i + 1, j), corner(i + 1, j + 1), corner(i, j + 1)]))
    return out


def tuft(cx, cy, rnd, n=4, h=0.08, spread=0.05):
    """Grasbueschel: n kurze Striche (je 2 Punkte) in Weltmetern, faecherfoermig nach oben."""
    out = []
    for k in range(n):
        a = math.radians(rnd.uniform(55, 125))
        ln = h * rnd.uniform(0.6, 1.2)
        x = cx + rnd.uniform(-spread, spread)
        out.append([(x, cy), (x + math.cos(a) * ln, cy + math.sin(a) * ln)])
    return out


def round_corners(pts, rnd, f=0.12):
    """Alle Ecken eines Polygons leicht abfasen (je Ecke zufaellig 0,5..1,5 x f der Kantenlaenge)."""
    n = len(pts)
    out = []
    for k in range(n):
        a, b, c = pts[k - 1], pts[k], pts[(k + 1) % n]
        s1 = f * rnd.uniform(0.5, 1.5)
        s2 = f * rnd.uniform(0.5, 1.5)
        out.append((b[0] + (a[0] - b[0]) * s1, b[1] + (a[1] - b[1]) * s1))
        out.append((b[0] + (c[0] - b[0]) * s2, b[1] + (c[1] - b[1]) * s2))
    return out


def chip(pts, rnd, size=0.22):
    """Eine Ecke des Vierecks abschlagen: Rueckgabe des neuen Polygons (Fase an einer Zufallsecke)."""
    k = rnd.randrange(len(pts))
    a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
    s = rnd.uniform(0.12, size)
    p1 = (b[0] + (a[0] - b[0]) * s, b[1] + (a[1] - b[1]) * s)
    p2 = (b[0] + (c[0] - b[0]) * s, b[1] + (c[1] - b[1]) * s)
    out = pts[:k] + [p1, p2] + pts[k + 1:]
    return out


def crack(pts, rnd):
    """Riss quer durch einen Stein: Polylinie von einer Kante zur gegenueberliegenden mit 2 bis 3 Knicken."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    if rnd.random() < 0.5:
        a = (rnd.uniform(x0 + 0.1 * (x1 - x0), x1 - 0.1 * (x1 - x0)), y1)
        b = (rnd.uniform(x0 + 0.1 * (x1 - x0), x1 - 0.1 * (x1 - x0)), y0)
    else:
        a = (x0, rnd.uniform(y0 + 0.1 * (y1 - y0), y1 - 0.1 * (y1 - y0)))
        b = (x1, rnd.uniform(y0 + 0.1 * (y1 - y0), y1 - 0.1 * (y1 - y0)))
    n = rnd.randint(2, 3)
    line = [a]
    for k in range(1, n + 1):
        t = k / (n + 1)
        line.append((a[0] + (b[0] - a[0]) * t + rnd.uniform(-0.08, 0.08) * (x1 - x0),
                     a[1] + (b[1] - a[1]) * t + rnd.uniform(-0.08, 0.08) * (y1 - y0)))
    line.append(b)
    return line


def edge_strip(pts, side, width):
    """Streifen entlang einer Kante eines konvexen Vierecks (side 0 = pts[0]-pts[1], ...), `width` m nach
    innen. Fuer Lichtkante oben/links und Schattenkante unten/rechts."""
    n = len(pts)
    a, b = pts[side % n], pts[(side + 1) % n]
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / ln, dx / ln
    # Normale zeigt nach innen (zum Schwerpunkt)
    if (cx - a[0]) * nx + (cy - a[1]) * ny < 0:
        nx, ny = -nx, -ny
    return [a, b, (b[0] + nx * width, b[1] + ny * width), (a[0] + nx * width, a[1] + ny * width)]


# ------------------------------------------------------------------ Papierkorn und Schraffur

def paper_grain(img, amount=0.04, seed=1, scale=1):
    """Leichtes Papierkorn: monochromes Rauschen von +-amount (Anteil von 255) ueber ein RGB-Bild.
    scale > 1 macht die Koerner groeber (Rauschen klein erzeugen und hochziehen). Deterministisch."""
    rng = np.random.default_rng(seed)
    w, h = img.size
    sw, sh = max(1, w // scale), max(1, h // scale)
    n = rng.uniform(-1, 1, (sh, sw)).astype(np.float32)
    n = (n + rng.uniform(-1, 1, (sh, sw)).astype(np.float32)) * 0.5     # Dreiecksverteilung: weniger Ausreisser
    if scale > 1:
        n = np.asarray(Image.fromarray(((n + 1) * 127.5).astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.float32) / 127.5 - 1
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    a += (n * amount * 255)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def hatch(region, spacing=0.08, angle=45.0, seed=1, jitter=0.35, length=(0.15, 0.4), density=0.5):
    """Sparsame Schraffur in einer shapely-Flaeche (Weltmeter): kurze, leicht unregelmaessige parallele
    Striche. Rueckgabe: Liste von Linien (je 2 Punkte), zum Zeichnen mit ink() oder Canvas.line()."""
    rnd = random.Random(seed)
    out = []
    if region.is_empty:
        return out
    x0, y0, x1, y1 = region.bounds
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    diag = math.hypot(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    k = -diag / 2
    while k < diag / 2:
        base = (cx + nx * k, cy + ny * k)
        t = -diag / 2
        while t < diag / 2:
            ln = rnd.uniform(*length)
            if rnd.random() < density:
                p = (base[0] + dx * t, base[1] + dy * t)
                q = (p[0] + dx * ln, p[1] + dy * ln)
                seg = LineString([p, q]).intersection(region)
                if seg.geom_type == "LineString" and seg.length > 0.04:
                    out.append(list(seg.coords))
            t += ln + rnd.uniform(0.05, 0.25)
        k += spacing * rnd.uniform(1 - jitter, 1 + jitter)
    return out


# ------------------------------------------------------------------ Bildhilfen

def paste_clipped(dst, src, x, y):
    """alpha_composite mit Zuschnitt: erlaubt negative Offsets und Ueberstand am Rand."""
    cx0, cy0 = max(0, x), max(0, y)
    cx1, cy1 = min(dst.width, x + src.width), min(dst.height, y + src.height)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    if (cx0, cy0, cx1, cy1) != (x, y, x + src.width, y + src.height):
        src = src.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y))
    dst.alpha_composite(src, (cx0, cy0))


def crewmate(ppm, body=(72, 76, 88, 255), visor=(150, 200, 225, 255), outline=(14, 16, 20, 255)):
    """Spielerfigur-Silhouette in Originalgroesse (ca. 0,8 m breit, 1,05 m hoch, Standlinie unten) als
    Massstab fuer Abnahme-Bilder. Rueckgabe (RGBA-Bild, Breite m, Hoehe m)."""
    w_m, h_m = 0.84, 1.08
    ss = 2
    s = ppm * ss
    im = Image.new("RGBA", (int(w_m * s), int(h_m * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda x, y: ((x + 0.42) * s, (h_m - y) * s)      # x um die Mitte, y = Hoehe ueber der Standlinie
    ow = max(2, int(0.045 * s))
    # Beine
    for lx in (-0.21, 0.03):
        d.rounded_rectangle([P(lx, 0.22), P(lx + 0.19, 0.0)], radius=int(0.05 * s), fill=body, outline=outline, width=ow)
    # Rucksack
    d.rounded_rectangle([P(-0.42, 0.78), P(-0.22, 0.28)], radius=int(0.07 * s), fill=body, outline=outline, width=ow)
    # Koerper: Kapsel
    d.rounded_rectangle([P(-0.26, 1.04), P(0.3, 0.12)], radius=int(0.22 * s), fill=body, outline=outline, width=ow)
    d.ellipse([P(-0.26, 1.08), P(0.3, 0.62)], fill=body, outline=outline, width=ow)
    d.rounded_rectangle([P(-0.26, 0.9), P(0.3, 0.12)], radius=int(0.16 * s), fill=body)
    d.line([P(-0.26, 0.9), P(-0.26, 0.26)], fill=outline, width=ow)
    d.line([P(0.3, 0.9), P(0.3, 0.26)], fill=outline, width=ow)
    # Visier
    d.rounded_rectangle([P(0.0, 0.92), P(0.36, 0.66)], radius=int(0.1 * s), fill=visor, outline=outline, width=ow)
    d.rounded_rectangle([P(0.06, 0.88), P(0.24, 0.8)], radius=int(0.03 * s), fill=(220, 240, 250, 255))
    return im.resize((im.width // ss, im.height // ss), Image.LANCZOS), w_m, h_m
