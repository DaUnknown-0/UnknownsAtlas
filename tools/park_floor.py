# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_floor.py - Boden und Waende des Moonlight Carnival (Stil abgenommen 2026-09-23, siehe park_art.py).
#
# Anders als museum_art.py (Vektor-Operationen je Platte) arbeitet der Park mit Musterkacheln: jedes
# Material ist eine nahtlose 4-m-Kachel (Perioden sind Teiler der Kachel), die ueber die ganze Karte
# gelegt und durch die Raummaske gestanzt wird. 49 x 46 m bei 80 px/m bleiben so in Sekunden.
# Darauf: Schiene, Prellbock, Kanal, Bruecken, Uebergaenge, Drehkreuz-Pfeile, Wandkrone, Nordwand-
# Stirnseiten (Gebaeude: Fassaden, Lichtungen und Wege: Hecke), weicher Wandschatten.
#
# Stilblatt 2026-10-01 ("Among Us, leicht handgezeichnet", tools/handdraw.py), voller Pass 01.10.:
#   - alle Materialien sind handgezeichnet: unregelmaessige Fugen (stone_grid / jitter_grid), Zittern
#     im Umriss, Kantenlicht oben/links, Fugenschatten unten/rechts, Abnutzung (blank gelaufene Stellen,
#     Risse, abgeschlagene Ecken, fehlende Steine), zum Schluss Papierkorn ueber dem ganzen Bodenbild
#   - jedes Gebaeude hat eine FACADE-Vorgabe (draw_facade): Material, Markise, Gluehbirnen, Schilder
#     (auch Neon), Fenster mit Jalousie, Zielscheiben, Warnschilder, Kabel, rotes Kreuz, Totenkoepfe,
#     Poster, Wimpel. Die Stirnseite ist so hoch, wie die feste Masse ueber der Wand reicht
#     (Wandstaerke + Hinterland), hoechstens `h` der Vorgabe: an Gassen 0,5 m, am Hinterland bis 1,5 m.

import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

import handdraw as HD
import park_decor as DECOR
import park_geo as G
import park_layout as L

TILE_M = 4.0
VOID = (14, 12, 22)
WALL_TOP = (40, 30, 48)
WALL_RIM = (74, 58, 86)
OUTLINE = (14, 12, 18)
GRAIN = 0.03          # Papierkorn ueber dem Bodenbild (Anteil von 255); 0,04 kostete +1,1 MB JPEG in der DLL
OFFS = [(dx, dy) for dx in (-TILE_M, 0, TILE_M) for dy in (-TILE_M, 0, TILE_M)]


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


def _tone(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col[:3])


def _canvas(ppm, base, ss=2):
    """Supersampelte Kachel-Leinwand: (Bild, Draw, n Zielpixel, N Pixel, Massstab s)."""
    n = int(TILE_M * ppm)
    N = n * ss
    img = Image.new("RGB", (N, N), base)
    return img, ImageDraw.Draw(img, "RGBA"), n, N, ppm * ss


def _px(s, pts, dx=0.0, dy=0.0):
    return [((x + dx) * s, (y + dy) * s) for x, y in pts]


def _shrink(pts, m):
    """Polygon um m Meter zum Schwerpunkt hin verkleinern (Fuge)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        ln = math.hypot(dx, dy) or 1.0
        out.append((x - dx / ln * m, y - dy / ln * m))
    return out


def tile_pavers(ppm, base=(118, 108, 100), seed=1, sw=0.5, sh=0.25, joint=(60, 52, 47), ss=2):
    """Handgezeichnetes Pflaster (Stilblatt): unregelmaessiges Fugenraster (handdraw.stone_grid), jeder
    Stein mit eigenem Ton und leichtem Zittern im Umriss, Kantenlicht oben/links, Fugenschatten
    unten/rechts, einzelne Steine abgeschlagen, gesprungen, abgesackt oder blank gelaufen. Gezeichnet
    mit `ss`-fachem Supersampling, damit Zittern und Fugen bei 80 px/m weich bleiben. Nahtlos: jeder
    Stein wird an den neun Kachelversaetzen gezeichnet."""
    img, d, n, N, s = _canvas(ppm, joint, ss)
    rnd = random.Random(seed)
    stones = HD.stone_grid(0, 0, TILE_M, TILE_M, sw, sh, seed=seed, joint=0.045, jitter=0.16, tilt=0.045,
                           skip=0.02, split=0.08, merge=0.04, periodic=True, bond=None, rounding=0.1)
    tints = [(1, 1, 1)] * 7 + [(1.07, 1.0, 0.93), (0.96, 0.98, 1.05), (1.12, 0.98, 0.88), (1.0, 1.02, 0.97)]
    # Sandfugen: helle Koernchen im Fugengrund (die Steine decken sie wieder zu), damit die Fugen
    # nicht wie schwarze Linien lesen
    for _ in range(int(TILE_M * TILE_M * 60)):
        x, y = rnd.uniform(0, N), rnd.uniform(0, N)
        d.ellipse([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=(150, 134, 120, rnd.randint(50, 110)))
    for i, st in enumerate(stones):
        pts = st.chip or st.pts
        if st.gap:
            # fehlender Stein: festgetretener Sand mit ein paar Kieseln, etwas heller als die Fuge
            for dx, dy in OFFS:
                d.polygon(_px(s, pts, dx, dy), fill=(78, 68, 60))
                for _ in range(4):
                    gx, gy = rnd.uniform(st.x0 + 0.04, st.x1 - 0.04), rnd.uniform(st.y0 + 0.04, st.y1 - 0.04)
                    gr = rnd.uniform(0.012, 0.025)
                    d.ellipse([((gx - gr + dx) * s, (gy - gr + dy) * s), ((gx + gr + dx) * s, (gy + gr + dy) * s)],
                              fill=(120, 108, 96), outline=(40, 32, 30))
            continue
        tone = 1 + st.tone * 0.09
        tint = rnd.choice(tints)
        dark = 0.82 if st.sunk else 1.0
        col = tuple(max(0, min(255, int(base[k] * tone * tint[k] * dark))) for k in range(3))
        wob = HD.wobble(pts, amp=0.006, seed=seed * 1000 + i, step=0.06, closed=True)
        for dx, dy in OFFS:
            d.polygon(_px(s, [(x + 0.014, y + 0.016) for x, y in wob], dx, dy), fill=(18, 14, 12, 110))
        for dx, dy in OFFS:
            d.polygon(_px(s, wob, dx, dy), fill=col)
            if st.sunk:
                d.polygon(_px(s, HD.edge_strip(pts, 0, 0.02), dx, dy), fill=(0, 0, 0, 55))
                d.polygon(_px(s, HD.edge_strip(pts, 3, 0.02), dx, dy), fill=(0, 0, 0, 40))
                continue
            d.polygon(_px(s, HD.edge_strip(pts, 0, 0.022), dx, dy), fill=(255, 250, 240, 60))    # Lichtkante oben
            d.polygon(_px(s, HD.edge_strip(pts, 3, 0.018), dx, dy), fill=(255, 250, 240, 36))    # links
            d.polygon(_px(s, HD.edge_strip(pts, 2, 0.02), dx, dy), fill=(0, 0, 0, 50))           # Schattenkante unten
            d.polygon(_px(s, HD.edge_strip(pts, 1, 0.016), dx, dy), fill=(0, 0, 0, 34))          # rechts
            if st.worn:
                cx = (st.x0 + st.x1) / 2 + (st.x1 - st.x0) * 0.1 * st.tone
                cy = (st.y0 + st.y1) / 2 - (st.y1 - st.y0) * 0.08
                rx, ry = (st.x1 - st.x0) * 0.3, (st.y1 - st.y0) * 0.26
                d.ellipse([((cx - rx + dx) * s, (cy - ry + dy) * s), ((cx + rx + dx) * s, (cy + ry + dy) * s)],
                          fill=(255, 248, 236, 22))
            if st.crack:
                HD.ink(d, _px(s, st.crack, dx, dy), (30, 24, 22, 170), max(1, 0.012 * s), seed=i, var=0.35)
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.045, seed + 5)


def _cells(d, s, cells, seed, colfn, joint=0.012, light=(255, 250, 240, 50), shadow=(0, 0, 0, 55),
           worn=0.14, chip=0.06, crack=0.04, gap=0.0, gapcol=(52, 46, 46), rnd=None):
    """Gemeinsamer Zeichner fuer Fliesen und Schachbrett: Zellen aus jitter_grid mit Fuge, Zittern,
    Lichtkante oben/links, Schattenkante unten/rechts, Abnutzung."""
    rnd = rnd or random.Random(seed)
    for k, (r, c, pts) in enumerate(cells):
        if rnd.random() < gap:
            for dx, dy in OFFS:
                d.polygon(_px(s, pts, dx, dy), fill=gapcol)
                for _ in range(3):
                    gx, gy = rnd.uniform(pts[0][0] + 0.05, pts[1][0] - 0.05), rnd.uniform(pts[0][1] + 0.05, pts[3][1] - 0.05)
                    d.ellipse([((gx - 0.015 + dx) * s, (gy - 0.015 + dy) * s), ((gx + 0.015 + dx) * s, (gy + 0.015 + dy) * s)], fill=(80, 72, 70))
            continue
        col = colfn(r, c, rnd)
        inner = _shrink(pts, joint)
        if rnd.random() < chip:
            inner = HD.chip(inner, rnd, 0.18)
        wob = HD.wobble(inner, amp=0.004, seed=seed * 100 + k, step=0.05, closed=True)
        for dx, dy in OFFS:
            d.polygon(_px(s, wob, dx, dy), fill=col)
            d.polygon(_px(s, HD.edge_strip(inner, 0, 0.018), dx, dy), fill=light)
            d.polygon(_px(s, HD.edge_strip(inner, 3, 0.014), dx, dy), fill=(light[0], light[1], light[2], int(light[3] * 0.6)))
            d.polygon(_px(s, HD.edge_strip(inner, 2, 0.018), dx, dy), fill=shadow)
            d.polygon(_px(s, HD.edge_strip(inner, 1, 0.014), dx, dy), fill=(0, 0, 0, int(shadow[3] * 0.6)))
            if k % 7 == 3 and rnd.random() < worn:
                cx, cy = (pts[0][0] + pts[2][0]) / 2, (pts[0][1] + pts[2][1]) / 2
                rx, ry = (pts[1][0] - pts[0][0]) * 0.32, (pts[3][1] - pts[0][1]) * 0.26
                d.ellipse([((cx - rx + dx) * s, (cy - ry + dy) * s), ((cx + rx + dx) * s, (cy + ry + dy) * s)], fill=(255, 250, 240, 20))
            if rnd.random() < crack * 0.12:
                HD.ink(d, _px(s, HD.crack(inner, rnd), dx, dy), (30, 24, 22, 150), max(1, 0.01 * s), seed=k, var=0.35)


def tile_checker(ppm, c1, c2, s=0.5, seed=3, ss=2):
    """Schachbrett (Karussell): Fliesen mit gemeinsam verschobenen Ecken, je Fliese eigener Ton, Fugen
    dunkel, Kantenlicht, einzelne blank gelaufene oder angeschlagene Fliesen."""
    img, d, n, N, sc = _canvas(ppm, (44, 30, 42), ss)
    cells = HD.jitter_grid(0, 0, TILE_M, TILE_M, s, seed=seed, jitter=0.04, periodic=True)
    _cells(d, sc, cells, seed, lambda r, c, rnd: _tone(c1 if (r + c) % 2 == 0 else c2, 1 + rnd.uniform(-0.06, 0.06)),
           joint=0.014, light=(255, 250, 240, 55), shadow=(0, 0, 0, 60), worn=0.5, chip=0.05, crack=0.5)
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.04, seed)


def tile_tiles(ppm, base, grout, s=0.4, seed=4, ss=2, gap=0.015):
    """Fliesenboden (Kuehlhaus, Sanitaetszelt): leicht schiefe Fliesen, Fugen im Fugenton, je Fliese
    eigener Ton, Kantenlicht, einzelne fehlende, gesprungene oder abgeschlagene Fliesen."""
    img, d, n, N, sc = _canvas(ppm, grout, ss)
    cells = HD.jitter_grid(0, 0, TILE_M, TILE_M, s, seed=seed, jitter=0.035, periodic=True)
    _cells(d, sc, cells, seed, lambda r, c, rnd: _tone(base, 1 + rnd.uniform(-0.05, 0.05)),
           joint=0.016, light=(255, 255, 255, 60), shadow=(0, 0, 0, 40), worn=0.3, chip=0.06, crack=0.6, gap=gap,
           gapcol=_tone(grout, 0.8))
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.03, seed)


def tile_boards(ppm, base=(122, 84, 54), seed=2, bh=0.25, bl=2.0, ss=2):
    """Holzdielen (handgezeichnet): Reihen etwa bh hoch, Bretter etwa bl lang mit versetzten Stoessen,
    je Brett eigener Ton und zittriger Umriss, Lichtkante oben, dunkle Fuge unten, Astloecher, ein
    paar Maserungslinien, Nagelkoepfe an den Stoessen. Nahtlos."""
    img, d, n, N, s = _canvas(ppm, _tone(base, 0.45), ss)
    rnd = random.Random(seed)
    rows = max(1, int(round(TILE_M / bh)))
    bh = TILE_M / rows
    k = 0
    for r in range(rows):
        y0, y1 = r * bh, (r + 1) * bh
        # Stossfugen: ab einem Zufallsversatz etwa alle bl Meter, Reihe schliesst sich periodisch
        xs = [rnd.uniform(0, bl)]
        while xs[-1] + bl * 0.6 < TILE_M:
            xs.append(xs[-1] + bl * rnd.uniform(0.75, 1.25))
        xs = [x for x in xs if x < TILE_M] or [rnd.uniform(0, TILE_M)]
        for i, xa in enumerate(xs):
            xb = xs[i + 1] if i + 1 < len(xs) else xs[0] + TILE_M
            if xb - xa < 0.25:
                continue
            tone = 1 + rnd.uniform(-0.09, 0.09)
            col = _tone(base, tone)
            pts = [(xa + 0.012, y0 + 0.006), (xb - 0.012, y0 + 0.006), (xb - 0.012, y1 - 0.014), (xa + 0.012, y1 - 0.014)]
            wob = HD.wobble(pts, amp=0.005, seed=seed * 100 + k, step=0.08, closed=True)
            k += 1
            for dx, dy in OFFS:
                d.polygon(_px(s, wob, dx, dy), fill=col)
                d.polygon(_px(s, HD.edge_strip(pts, 0, 0.016), dx, dy), fill=(255, 240, 210, 55))
                d.polygon(_px(s, HD.edge_strip(pts, 2, 0.02), dx, dy), fill=(0, 0, 0, 70))
                d.polygon(_px(s, HD.edge_strip(pts, 1, 0.012), dx, dy), fill=(0, 0, 0, 60))
                # Maserung: zwei bis drei lange, leicht wellige Linien
                for g in range(rnd.randint(1, 3)):
                    gy = rnd.uniform(y0 + 0.04, y1 - 0.04)
                    line = HD.wobble([(xa + 0.08, gy), (xb - 0.08, gy)], amp=0.012, seed=seed * 7 + k * 3 + g, step=0.12)
                    d.line(_px(s, line, dx, dy), fill=_tone(col, 0.82) + (150,), width=max(1, int(0.008 * s)))
                if rnd.random() < 0.22:                                                   # Astloch
                    ax, ay = rnd.uniform(xa + 0.3, xb - 0.3), rnd.uniform(y0 + 0.05, y1 - 0.05)
                    ar = rnd.uniform(0.02, 0.035)
                    d.ellipse([((ax - ar * 1.4 + dx) * s, (ay - ar + dy) * s), ((ax + ar * 1.4 + dx) * s, (ay + ar + dy) * s)],
                              fill=_tone(col, 0.6), outline=_tone(col, 0.45))
                    d.ellipse([((ax - ar * 0.5 + dx) * s, (ay - ar * 0.4 + dy) * s), ((ax + ar * 0.5 + dx) * s, (ay + ar * 0.4 + dy) * s)], fill=_tone(col, 0.4))
                for nx in (xa + 0.05, xb - 0.05):                                       # Nagelkoepfe
                    for ny in (y0 + bh * 0.3, y1 - bh * 0.3):
                        d.ellipse([((nx - 0.009 + dx) * s, (ny - 0.009 + dy) * s), ((nx + 0.009 + dx) * s, (ny + 0.009 + dy) * s)],
                                  fill=(70, 62, 60), outline=(40, 34, 32))
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.04, seed + 3, periods=(2, 3, 7))


def tile_carpet(ppm, base, accent, seed=5, ss=2):
    """Teppich: Rautengitter aus leicht zittrigen Linien (periodisch), kleine Akzentrauten an den
    Kreuzungen, Gewebeflimmern, abgetretene hellere Stellen."""
    img, d, n, N, s = _canvas(ppm, base, ss)
    rnd = random.Random(seed)
    for k in range(8):                                                   # Diagonalen in beiden Richtungen
        a = k * 0.5
        for sgn in (1, -1):
            pts = [(a + sgn * (-6), -6), (a + sgn * 10, 10)]
            wob = HD.wobble(pts, amp=0.01, seed=seed * 10 + k * 2 + (sgn > 0), step=0.15)
            for dx, dy in OFFS:
                d.line(_px(s, wob, dx, dy), fill=accent + (170,), width=max(1, int(0.022 * s)))
    for i in range(8):                                                   # Akzentrauten
        for j in range(8):
            x, y = i * 0.5 + (0.25 if j % 2 else 0.0), j * 0.5
            r = 0.07
            pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
            for dx, dy in OFFS:
                d.polygon(_px(s, pts, dx, dy), fill=_tone(accent, 1.15) + (200,))
    for _ in range(6):                                                   # abgetretene Stellen
        x, y, r = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0.3, 0.7)
        for dx, dy in OFFS:
            d.ellipse([((x - r + dx) * s, (y - r * 0.6 + dy) * s), ((x + r + dx) * s, (y + r * 0.6 + dy) * s)], fill=(255, 245, 230, 14))
    a = np.asarray(img.resize((n, n), Image.LANCZOS)).astype(np.float32)
    weave = np.random.default_rng(seed).uniform(-1, 1, (n, n)).astype(np.float32) * 5
    a += weave[..., None]
    return _mottle(_img(a), n, 0.07, seed, periods=(3, 7, 11))


def tile_concrete(ppm, base, seed=6, stains=True, ss=2):
    """Betonplatten 2 x 2 m (Stilblatt): Dehnfugen als zittrige Striche mit Schattenkante, jede Platte
    eigener Ton, Haarrisse, abgeplatzte Fugenecken, feine Flecken. Nahtlos (Fugen an den Versaetzen)."""
    n = int(TILE_M * ppm)
    s = ppm * ss
    N = n * ss
    a = np.ones((N, N, 3), np.float32) * np.array(base, np.float32)
    a *= (1 + _wave(N, (2, 4, 9, 17), seed) * 0.07)[..., None]
    img = _img(a)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    half = TILE_M / 2
    for (px_, py_) in ((0, 0), (half, 0), (0, half), (half, half)):             # Plattentoene
        t = rnd.uniform(-0.05, 0.05)
        d.rectangle([px_ * s, py_ * s, (px_ + half) * s, (py_ + half) * s], fill=(255, 255, 255, int(40 * max(0, t) * 10)) if t > 0 else (0, 0, 0, int(40 * -t * 10)))
    for k in (0.0, half):                                                       # Dehnfugen
        for vert in (True, False):
            pts = [(k, 0), (k, TILE_M)] if vert else [(0, k), (TILE_M, k)]
            wob = HD.wobble(pts, amp=0.008, seed=seed * 3 + int(k * 10) + (1 if vert else 0), step=0.08)
            for dx, dy in OFFS:
                HD.ink(d, [((x + dx) * s, (y + dy) * s) for x, y in wob], (0, 0, 0, 90), max(1, int(0.03 * s)), seed=int(k), var=0.3)
                HD.ink(d, [((x + dx + (0.02 if vert else 0)) * s, (y + dy + (0 if vert else 0.02)) * s) for x, y in wob], (255, 255, 255, 30), max(1, int(0.015 * s)), seed=int(k) + 5, var=0.3)
    for _ in range(3):                                                          # Haarrisse
        x, y = rnd.uniform(0.3, TILE_M - 0.3), rnd.uniform(0.3, TILE_M - 0.3)
        pts = [(x, y)]
        ang = rnd.uniform(0, math.tau)
        for _k in range(4):
            ang += rnd.uniform(-0.7, 0.7)
            ln = rnd.uniform(0.15, 0.4)
            pts.append((pts[-1][0] + math.cos(ang) * ln, pts[-1][1] + math.sin(ang) * ln))
        for dx, dy in OFFS:
            HD.ink(d, [((px_ + dx) * s, (py_ + dy) * s) for px_, py_ in pts], (0, 0, 0, 80), max(1, int(0.012 * s)), seed=seed, var=0.4)
    if stains:
        for _ in range(3):
            cx, cy, r = rnd.uniform(0.2, 0.8) * N, rnd.uniform(0.2, 0.8) * N, rnd.uniform(0.3, 0.6) * s
            d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=(20, 18, 20, 24))
    for _ in range(int(TILE_M * TILE_M * 25)):                                  # Kiesel im Beton
        x, y = rnd.uniform(0, N), rnd.uniform(0, N)
        d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(255, 255, 255, rnd.randint(14, 30)))
    return img.resize((n, n), Image.LANCZOS)


def tile_earth(ppm, base, seed=7, ss=2):
    """Festplatz-Erde mit Saegemehl: fleckiger Grund, festgetretene dunklere Stellen, Fussspuren,
    Strohhalme, Kiesel, helle Saegemehlkoerner."""
    img, d, n, N, s = _canvas(ppm, base, ss)
    rnd = random.Random(seed)
    for _ in range(7):                                                   # festgetretene Stellen
        x, y, r = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0.3, 0.8)
        pts = HD.wobble_ellipse(x, y, r, r * rnd.uniform(0.5, 0.8), amp=0.03, seed=seed + int(x * 10))
        for dx, dy in OFFS:
            d.polygon(_px(s, pts, dx, dy), fill=(0, 0, 0, 22))
    for _ in range(14):                                                  # Fussspuren (Paare kleiner Ovale)
        x, y, a = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0, math.tau)
        for k in range(rnd.randint(2, 4)):
            px_, py_ = x + math.cos(a) * 0.3 * k, y + math.sin(a) * 0.3 * k
            ox, oy = -math.sin(a) * 0.08 * (1 if k % 2 else -1), math.cos(a) * 0.08 * (1 if k % 2 else -1)
            for dx, dy in OFFS:
                d.ellipse([((px_ + ox - 0.05 + dx) * s, (py_ + oy - 0.07 + dy) * s), ((px_ + ox + 0.05 + dx) * s, (py_ + oy + 0.07 + dy) * s)], fill=(0, 0, 0, 26))
    for _ in range(int(TILE_M * TILE_M * 70)):                          # Saegemehl
        x, y = rnd.uniform(0, N), rnd.uniform(0, N)
        r = rnd.uniform(0.01, 0.025) * s
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(214, 176, 120, rnd.randint(60, 140)))
    for _ in range(int(TILE_M * TILE_M * 6)):                           # Strohhalme
        x, y, a = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.08, 0.2)
        for dx, dy in OFFS:
            d.line(_px(s, [(x, y), (x + math.cos(a) * ln, y + math.sin(a) * ln)], dx, dy), fill=(226, 196, 130, 170), width=max(1, int(0.012 * s)))
    for _ in range(int(TILE_M * TILE_M * 4)):                           # Kiesel
        x, y = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M)
        r = rnd.uniform(0.015, 0.03)
        for dx, dy in OFFS:
            d.ellipse([((x - r + dx) * s, (y - r * 0.8 + dy) * s), ((x + r + dx) * s, (y + r * 0.8 + dy) * s)], fill=(140, 120, 100), outline=(60, 48, 40))
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.1, seed, periods=(2, 5, 11))


def tile_plate(ppm, base, seed=8, ss=2):
    """Riffelblech (Autoscooter): Traenen-Muster, Plattenstoesse jeden Meter als zittrige Fugen mit
    Nieten, Schrammen und Schmutzflecken."""
    img, d, n, N, s = _canvas(ppm, base, ss)
    rnd = random.Random(seed)
    g = 0.25
    kk = int(TILE_M / g)
    for r in range(kk):
        for c in range(kk):
            x, y = c * g + (g / 2 if r % 2 else 0), r * g
            for dx in (0, -TILE_M):
                d.line(_px(s, [(x + dx - g * 0.18, y + g * 0.62), (x + dx + g * 0.18, y + g * 0.38)]), fill=(255, 255, 255, 50), width=max(1, int(0.02 * s)))
                d.line(_px(s, [(x + dx - g * 0.18, y + g * 0.68), (x + dx + g * 0.18, y + g * 0.44)]), fill=(0, 0, 0, 70), width=max(1, int(0.02 * s)))
    for k in range(4):                                                   # Plattenstoesse
        for vert in (True, False):
            pts = [(k, 0), (k, TILE_M)] if vert else [(0, k), (TILE_M, k)]
            wob = HD.wobble(pts, amp=0.006, seed=seed * 5 + k * 2 + vert, step=0.1)
            for dx, dy in OFFS:
                HD.ink(d, _px(s, wob, dx, dy), (0, 0, 0, 120), max(1, int(0.025 * s)), seed=k, var=0.25)
                HD.ink(d, _px(s, [(x + (0.02 if vert else 0), y + (0 if vert else 0.02)) for x, y in wob], dx, dy), (255, 255, 255, 34), max(1, int(0.012 * s)), seed=k + 3, var=0.25)
    for i in range(4):                                                   # Nieten an den Kreuzungen
        for j in range(4):
            for ox, oy in ((0.07, 0.07), (-0.07, 0.07), (0.07, -0.07), (-0.07, -0.07)):
                x, y = i + ox, j + oy
                for dx, dy in OFFS:
                    d.ellipse([((x - 0.018 + dx) * s, (y - 0.018 + dy) * s), ((x + 0.018 + dx) * s, (y + 0.018 + dy) * s)], fill=_tone(base, 1.25), outline=(30, 30, 36))
    for _ in range(10):                                                  # Schrammen
        x, y, a = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(-0.6, 0.6)
        ln = rnd.uniform(0.2, 0.6)
        for dx, dy in OFFS:
            d.line(_px(s, [(x, y), (x + math.cos(a) * ln, y + math.sin(a) * ln)], dx, dy), fill=(255, 255, 255, 40), width=max(1, int(0.01 * s)))
    for _ in range(4):                                                   # Schmutz
        x, y, r = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0.15, 0.4)
        for dx, dy in OFFS:
            d.ellipse([((x - r + dx) * s, (y - r * 0.6 + dy) * s), ((x + r + dx) * s, (y + r * 0.6 + dy) * s)], fill=(8, 8, 12, 40))
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.05, seed)


def tile_grass(ppm, base, seed=9, ss=2):
    """Rasen: fleckiger Grund, Grasbueschel in zwei Gruentoenen, kahle Erdstellen, Klee, ein paar
    Gaensebluemchen."""
    img, d, n, N, s = _canvas(ppm, base, ss)
    rnd = random.Random(seed)
    for _ in range(5):                                                   # kahle Stellen
        x, y, r = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M), rnd.uniform(0.2, 0.5)
        pts = HD.wobble_ellipse(x, y, r, r * 0.6, amp=0.03, seed=seed + int(x * 7))
        for dx, dy in OFFS:
            d.polygon(_px(s, pts, dx, dy), fill=(70, 56, 40, 120))
    for _ in range(int(TILE_M * TILE_M * 26)):                          # Bueschel
        x, y = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M)
        col = _tone(base, 1.5) if rnd.random() < 0.5 else _tone(base, 0.62)
        for seg in HD.tuft(x, y, rnd, n=rnd.randint(3, 5), h=rnd.uniform(0.06, 0.11)):
            for dx, dy in OFFS:
                d.line(_px(s, [(seg[0][0], seg[0][1]), (seg[1][0], seg[0][1] - (seg[1][1] - seg[0][1]))], dx, dy),
                       fill=col + (170,), width=max(1, int(0.014 * s)))
    for _ in range(int(TILE_M * TILE_M * 3)):                           # Klee
        x, y = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M)
        for a in (90, 210, 330):
            cx, cy = x + math.cos(math.radians(a)) * 0.03, y + math.sin(math.radians(a)) * 0.03
            for dx, dy in OFFS:
                d.ellipse([((cx - 0.028 + dx) * s, (cy - 0.028 + dy) * s), ((cx + 0.028 + dx) * s, (cy + 0.028 + dy) * s)], fill=_tone(base, 1.35))
    for _ in range(4):                                                   # Gaensebluemchen
        x, y = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M)
        for dx, dy in OFFS:
            for a in range(0, 360, 60):
                px_, py_ = x + math.cos(math.radians(a)) * 0.035, y + math.sin(math.radians(a)) * 0.035
                d.ellipse([((px_ - 0.022 + dx) * s, (py_ - 0.022 + dy) * s), ((px_ + 0.022 + dx) * s, (py_ + 0.022 + dy) * s)], fill=(240, 240, 232))
            d.ellipse([((x - 0.02 + dx) * s, (y - 0.02 + dy) * s), ((x + 0.02 + dx) * s, (y + 0.02 + dy) * s)], fill=(250, 214, 80))
    img = img.resize((n, n), Image.LANCZOS)
    return _mottle(img, n, 0.12, seed, periods=(2, 3, 7, 13))


def tile_water(ppm, seed=10, ss=2):
    img, d, n, N, s = _canvas(ppm, (34, 78, 122), ss)
    rnd = random.Random(seed)
    for _ in range(70):
        x, y = rnd.uniform(0, TILE_M), rnd.uniform(0, TILE_M)
        ln = rnd.uniform(0.2, 0.6)
        pts = HD.wobble([(x - ln / 2, y), (x - ln / 4, y - ln * 0.08), (x + ln / 4, y - ln * 0.08), (x + ln / 2, y)], amp=0.008, seed=seed + int(x * 50 + y * 7), step=0.05)
        for dx, dy in OFFS:
            d.line(_px(s, pts, dx, dy), fill=(150, 200, 230, 120), width=max(1, int(0.022 * s)))
    img = img.resize((n, n), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    a *= (1 + _wave(n, (2, 4, 8), seed) * 0.12)[..., None]
    return _img(a)


# Material je Bereich (Schluessel aus park_layout BUILDINGS/CLEARINGS)
def materials(ppm):
    return {
        "_path": tile_pavers(ppm, (116, 108, 100), 11, 0.4, 0.3),
        "fairground": tile_earth(ppm, (118, 86, 58), 12),
        "workshop": tile_concrete(ppm, (96, 96, 98), 13),
        "carousel": tile_checker(ppm, (112, 60, 96), (214, 196, 170), 0.5, 14),
        "bumpercars": tile_plate(ppm, (96, 104, 118), 15),
        "security": tile_carpet(ppm, (46, 54, 76), (70, 80, 108), 16),
        "substation": tile_concrete(ppm, (104, 102, 90), 17),
        "firstaid": tile_tiles(ppm, (214, 222, 220), (150, 170, 170), 0.4, 18, gap=0.0),
        "office": tile_boards(ppm, (140, 98, 62), 19, 0.2, 1.33),
        "coldstore": tile_tiles(ppm, (196, 214, 226), (130, 160, 180), 0.5, 20, gap=0.012),
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


# ------------------------------------------------------------------ Fassaden-Vorgaben
# Nordwand-Stirnseite je Gebaeude (draw_facade). Schluessel:
#   mat      brick | planks | metal | canvas          col Grundton, seam Fugen-/Nahtton, sockel Sockelband
#   stripe   zweite Streifenfarbe bei canvas (Zeltstoff, senkrechte Bahnen 0,5 m)
#   h        Hoechsthoehe der Stirnseite in m (die feste Masse ueber der Wand begrenzt sie zusaetzlich)
#   awning   (Streifen A, Streifen B) Markise mit Volant; valance Zackenvolant an der Oberkante (Zelt)
#   bulbs    Gluehbirnenleiste unter der Markise bzw. Oberkante; pennants Wimpelkette (Farben)
#   signs    [(x, Text, Schildfarbe, Schriftfarbe[, Groesse[, neon]])]  Schilder an Stelle x
#   window_at/window_w/window_col/blinds   beleuchtete Fenster (blinds: halb geschlossene Jalousie)
#   targets  Zielscheiben [x], warn Warnschilder [x], cables Kabel mit Isolatoren, cross rotes Kreuz [x],
#   skulls   Totenkoepfe [x], posters [(x, Farbe, Motiv)], speaker Lautsprecherhorn [x], moon Mondsichel [x],
#   clock    Wanduhr [x], frost Reif, bolts Blitzsymbole [x]
FACADE = {
    # Werkstatt: Fenster links vom Foto-Monitor (C#, x -19,9..-17,7) und rechts der Tuer; Sicherungskasten,
    # Lochwand und Uhr kommen aus park_decor.walls
    "workshop": dict(mat="brick", col=(134, 82, 64), seam=(68, 44, 40), sockel=(72, 64, 64), h=1.2,
                     window_at=[-20.42], window_w=0.45, window_col=(255, 214, 140)),
    "coldstore": dict(mat="planks", col=(186, 202, 214), seam=(118, 146, 166), sockel=(96, 124, 146),
                      awning=((66, 128, 186), (236, 244, 250)), bulbs=True, frost=True,
                      signs=[(14.05, "COLD STORE", (28, 54, 86), (214, 240, 255), 0.24)]),
    # Festplatz: Zeltwand rot/creme, Zackenvolant, Gluehbirnen, Neon "MOONLIGHT" / "CARNIVAL" neben den Buden
    "fairground": dict(mat="canvas", col=(226, 208, 176), stripe=(176, 52, 62), seam=(120, 70, 60), sockel=(96, 52, 56),
                       h=1.5, valance=(222, 176, 70), bulbs=True, moon=[-2.4, 2.4],
                       signs=[(-2.35, "MOONLIGHT", (30, 22, 40), (255, 214, 120), 0.3, True),
                              (2.35, "CARNIVAL", (30, 22, 40), (255, 120, 190), 0.3, True)]),
    # Karussell: Zeltwand pflaume/creme, Goldvolant, Wimpel, Schild
    "carousel": dict(mat="canvas", col=(222, 200, 168), stripe=(122, 60, 110), seam=(90, 46, 84), sockel=(70, 40, 66),
                     h=1.4, valance=(226, 186, 76), bulbs=True, pennants=((226, 186, 76, 255), (120, 60, 110, 255)),
                     signs=[(-11.6, "CAROUSEL", (120, 60, 110), (255, 226, 150), 0.3)], stars=[-18.6, -17.2]),
    # Autoscooter: Wellblech blaugrau, Neon-Schriftzug, Blitze, Warnstreifen am Sockel
    "bumpercars": dict(mat="metal", col=(86, 98, 126), seam=(52, 60, 82), sockel=(40, 44, 56), hazard=True,
                       h=1.3, signs=[(-6.8, "BUMPER CARS", (24, 20, 40), (110, 230, 255), 0.3, True)], bolts=[-10.2, -4.6]),
    # Security-Nebenraum: dunkler Ziegel, Fenster mit Jalousie, STAFF ONLY
    "security": dict(mat="brick", col=(84, 80, 96), seam=(44, 40, 52), sockel=(50, 48, 58), h=1.2,
                     window_at=[6.35], window_w=0.45, window_col=(220, 230, 255), blinds=True,
                     signs=[(3.12, "STAFF", (180, 40, 40), (250, 240, 220), 0.2)]),
    # Umspannhaus: grauer Ziegel, DANGER-Schild, Warndreiecke, Kabel mit Isolatoren ueber der Wand
    "substation": dict(mat="brick", col=(118, 108, 92), seam=(62, 54, 48), sockel=(70, 66, 60), h=1.3,
                       signs=[(1.25, "DANGER", (230, 190, 50), (30, 26, 30), 0.24)], warn=[5.1, 6.0], cables=True),
    # Sanitaetszelt: Zeltstoff weiss/rot, rotes Kreuz, FIRST AID
    "firstaid": dict(mat="canvas", col=(228, 230, 224), stripe=(196, 60, 62), seam=(150, 120, 120), sockel=(120, 60, 60),
                     h=1.5, valance=(196, 60, 62), cross=[18.5], signs=[(20.6, "FIRST AID", (236, 236, 230), (190, 40, 40), 0.26)]),
    # Parkbuero: warmes Holz, Fenster mit Jalousie, Schild, Uhr
    "office": dict(mat="planks", col=(150, 110, 74), seam=(90, 62, 40), sockel=(70, 50, 36), h=1.2,
                   window_at=[-4.8, 1.42], window_w=0.45, window_col=(255, 214, 140), blinds=True,
                   signs=[(-0.05, "PARK OFFICE", (236, 226, 200), (60, 40, 30), 0.22)], clock=[-5.7]),
    # Musikzentrale: dunkle Bretter, Konzertposter, Neon SHOW CONTROL, Lautsprecherhorn
    "musicbooth": dict(mat="planks", col=(90, 58, 104), seam=(50, 30, 60), sockel=(40, 26, 48), h=1.3,
                       posters=[(17.5, (120, 60, 140), "star"), (18.2, (40, 80, 140), "dot"), (18.9, (160, 60, 60), "star")],
                       signs=[(20.0, "SHOW CONTROL", (24, 20, 40), (110, 230, 255), 0.26, True)], speaker=[22.05]),
    # Schiessbude: rotbraune Bretter, Markise rot/creme, Gluehbirnen, Zielscheiben, Schild
    "shooting": dict(mat="planks", col=(120, 70, 44), seam=(70, 40, 26), sockel=(60, 36, 24), h=1.5,
                     awning=((176, 52, 62), (226, 208, 176)), bulbs=True, targets=[-18.3, -17.3, -12.7, -11.7],
                     signs=[(-15.0, "SHOOTING GALLERY", (30, 20, 30), (255, 120, 190), 0.28, True)]),
    # Geisterbahn: fast schwarze Bretter, Totenkoepfe, Spinnweben, gruene Farbnasen
    "ghosttrain": dict(mat="planks", col=(48, 34, 60), seam=(22, 14, 30), sockel=(30, 20, 36), h=1.0,
                       skulls=[-16.62, -13.38], webs=True, drips=(120, 255, 130)),
}
HEDGE = (32, 62, 40)
_GLOWS = []     # (x0, y0, x1, y1, rgba) Neon-Lichthoefe, am Ende von faces() in einer weichen Ebene


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
    wear(F, walk, rooms)                                                # abgelaufene Mittelspur der Wege
    for key, (_name, _s, g) in rooms.items():
        if key in mats:
            F.fill_tile(mats[key], F.mask(g.intersection(walk)))
    d = F.draw()
    # Wasser mit Ufer, Bruecken
    F.fill_tile(mats["_water"], F.mask(water))
    for p in G_parts(water):
        pts = HD.wobble(list(p.exterior.coords), amp=0.015, seed=61, step=0.1, closed=True)
        HD.ink(d, [F.P(*q) for q in pts], (20, 40, 60, 255), int(0.08 * ppm), seed=61, var=0.25, closed=True)
        HD.ink(d, [F.P(x, y - 0.06) for x, y in pts], (170, 210, 235, 110), int(0.03 * ppm), seed=62, var=0.3, closed=True)   # Schaumsaum
    for s in L.BRIDGES:
        g = G.shape(s)
        F.fill_tile(mats["_bridge"], F.mask(g))
        x0, y0, x1, y1 = g.bounds
        d = F.draw()
        for yy in (y0 + 0.05, y1 - 0.05):
            pts = HD.wobble([(x0, yy), (x1, yy)], amp=0.006, seed=int(x0 * 10), step=0.08)
            HD.ink(d, [F.P(*q) for q in pts], (70, 46, 30, 255), int(0.1 * ppm), seed=int(x0), var=0.2)
    rails(F, mats)
    # Drehkreuze: Einbahn-Pfeile (Spielinformation)
    d = F.draw()
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
    # Kronenkante: an allen Raendern der begehbaren Flaeche (Licht oben), mit leichtem Zittern
    d = F.draw()
    for k, p in enumerate(G_parts(walk)):
        for j, ring in enumerate([p.exterior] + list(p.interiors)):
            pts = HD.wobble(list(ring.coords), amp=0.008, seed=900 + k * 50 + j, step=0.1, closed=True)
            HD.ink(d, [F.P(*q) for q in pts], OUTLINE + (255,), max(2, int(0.06 * ppm)), seed=k * 50 + j, var=0.2, closed=True)
    # Laternenlicht ist eine eigene Ebene im Spiel (AtlasParkWorld, geht bei Park Blackout aus)
    # Papierkorn ueber dem ganzen Bodenbild (Stilblatt: 3 bis 5 %)
    F.img = HD.paper_grain(F.img, GRAIN, seed=4)
    return F.img


def rails(F, mats):
    """Achterbahn: Schotterbett, Schwellen, zwei Schienen (handgezeichnet), Bahnuebergaenge mit
    Warnstreifen, Prellbock am Westende der Stichstrecke (x -5,8, y 20,4..21,4)."""
    ppm = F.ppm
    d = F.draw()
    pen = DECOR.Pen(F)
    rnd = random.Random(71)
    for s in L.RAIL:
        g = G.shape(s)
        x0, y0, x1, y1 = g.bounds
        d.rectangle([*F.P(x0, y1), *F.P(x1, y0)], fill=(64, 58, 60, 255))
        for _ in range(int((x1 - x0) * (y1 - y0) * 40)):                        # Schotter
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            r = rnd.uniform(0.02, 0.045)
            pen.ell(x, y, r, r * 0.8, rnd.choice(((86, 80, 82, 255), (54, 48, 50, 255), (100, 94, 96, 255))))
        vertical = (y1 - y0) > (x1 - x0)
        if vertical:
            yy = y0 + 0.1
            while yy < y1 - 0.05:
                pen.hrect(x0 + 0.1, yy, x1 - 0.1, yy + 0.18, (104, 72, 48, 255), (40, 26, 18, 255), 0.018, seed=int(yy * 10))
                yy += 0.42
            for xx in (x0 + 0.34, x1 - 0.34):
                pts = HD.wobble([(xx, y0), (xx, y1)], amp=0.005, seed=int(xx * 10), step=0.15)
                HD.ink(d, [F.P(*q) for q in pts], (30, 28, 32, 255), int(0.11 * ppm), seed=int(xx), var=0.1)
                HD.ink(d, [F.P(*q) for q in pts], (196, 198, 206, 255), int(0.06 * ppm), seed=int(xx), var=0.1)
                HD.ink(d, [F.P(x - 0.015, y) for x, y in pts], (240, 240, 246, 255), int(0.018 * ppm), seed=int(xx), var=0.1)
        else:
            xx = x0 + 0.1
            while xx < x1 - 0.05:
                pen.hrect(xx, y0 + 0.1, xx + 0.18, y1 - 0.1, (104, 72, 48, 255), (40, 26, 18, 255), 0.018, seed=int(xx * 10))
                xx += 0.42
            for yy in (y0 + 0.34, y1 - 0.34):
                pts = HD.wobble([(x0, yy), (x1, yy)], amp=0.005, seed=int(yy * 10), step=0.15)
                HD.ink(d, [F.P(*q) for q in pts], (30, 28, 32, 255), int(0.11 * ppm), seed=int(yy), var=0.1)
                HD.ink(d, [F.P(*q) for q in pts], (196, 198, 206, 255), int(0.06 * ppm), seed=int(yy), var=0.1)
                HD.ink(d, [F.P(x, y + 0.015) for x, y in pts], (240, 240, 246, 255), int(0.018 * ppm), seed=int(yy), var=0.1)
    for _k, s, direction in L.CROSSINGS:                                # Bahnuebergang: Pflaster + Warnstreifen
        g = G.shape(s)
        x0, y0, x1, y1 = g.bounds
        F.fill_tile(mats["_path"], F.mask(g))
        d = F.draw()
        if direction == "vertical":
            for xx in (x0 + 0.34, x1 - 0.34):
                d.line([F.P(xx, y0), F.P(xx, y1)], fill=(150, 150, 160, 255), width=int(0.06 * ppm))
            for yy in (y0 + 0.1, y1 - 0.1):
                stripes(d, F, x0, yy - 0.08, x1, yy + 0.08)
        else:
            for yy in (y0 + 0.34, y1 - 0.34):
                d.line([F.P(x0, yy), F.P(x1, yy)], fill=(150, 150, 160, 255), width=int(0.06 * ppm))
            for xx in (x0 + 0.1, x1 - 0.1):
                stripes(d, F, xx - 0.08, y0, xx + 0.08, y1)
    # Prellbock: am Westende der Stichstrecke (kleinstes x des westlichsten waagerechten Bandes)
    stub = min((G.shape(s).bounds for s in L.RAIL if (G.shape(s).bounds[2] - G.shape(s).bounds[0]) > (G.shape(s).bounds[3] - G.shape(s).bounds[1])),
               key=lambda b: b[0])
    bx, by0, by1 = stub[0], stub[1], stub[3]
    cy = (by0 + by1) / 2
    K = 0.55
    pen = DECOR.Pen(F)
    for yy in (by0 + 0.2, by1 - 0.2):                                     # zwei Stahlfuesse auf den Schienen
        pen.hrect(bx + 0.08, yy - 0.08, bx + 0.42, yy + 0.08, (60, 60, 68, 255), (20, 18, 22, 255), 0.02, seed=int(yy * 3))
    pen.poly([(bx + 0.1, cy - 0.12), (bx + 0.42, cy - 0.12), (bx + 0.42, cy - 0.12 + 0.5 * K), (bx + 0.1, cy - 0.12 + 0.5 * K)], (60, 60, 68, 255), (20, 18, 22, 255), 0.02)   # Bock
    beam = [(bx + 0.06, by0 + 0.08), (bx + 0.5, by0 + 0.08), (bx + 0.5, by1 - 0.08), (bx + 0.06, by1 - 0.08)]
    pen.hpoly([(x + 0.05, y - 0.05) for x, y in beam], (0, 0, 0, 90), None, seed=5)              # Schatten
    pen.hpoly(beam, (200, 52, 52, 255), (20, 18, 22, 255), 0.03, seed=6)                           # Balken rot/weiss
    n = 5
    for i in range(n):
        if i % 2:
            ya = by0 + 0.08 + (by1 - by0 - 0.16) * i / n
            pen.rect(bx + 0.09, ya, bx + 0.47, ya + (by1 - by0 - 0.16) / n, (236, 232, 224, 255))
    pen.rect(bx + 0.06, by0 + 0.08, bx + 0.5, by0 + 0.12, (255, 255, 255, 60))
    pen.hell(bx + 0.28, cy, 0.09, 0.09, (40, 38, 44, 255), (20, 18, 22, 255), 0.02, seed=7)        # Puffer
    pen.ell(bx + 0.28, cy, 0.035, 0.035, (120, 120, 130, 255))
    pen.hrect(bx - 0.08, by0 - 0.02, bx + 0.06, by1 + 0.02, (120, 86, 56, 255), (20, 18, 22, 255), 0.025, seed=8)   # Holzbohle dahinter


def wear(F, walk, rooms):
    """Abnutzung der Wege: eine hellere, blank gelaufene Mittelspur entlang jeder Wegachse und ein
    dunkler Schmutzsaum, wo Weg und Bereich aneinanderstossen (weiche Ebenen, nur auf den Wegen)."""
    pen = DECOR.Pen(F)
    rest = walk.difference(unary_union([g for _n, _s, g in rooms.values()]))
    mask = F.mask(rest)

    def lanes(d):
        for pts in L.PATHS:
            d.line([pen.P(*p) for p in pts], fill=(255, 238, 214, 30), width=pen.w(1.3), joint="curve")
    layer = Image.new("RGBA", F.img.size, (0, 0, 0, 0))
    lanes(ImageDraw.Draw(layer, "RGBA"))
    layer = layer.filter(ImageFilter.GaussianBlur(0.35 * F.ppm))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    base = F.img.convert("RGBA")
    base.alpha_composite(layer)
    F.img = base.convert("RGB")


def lamp_points(walk, rooms):
    """Laternen am Wegrand, etwa alle 5 m, abwechselnd links und rechts (nur auf Wegen, nicht in Bereichen).
    Seit der Kartenverkleinerung sind viele Wege nur 2-4 m lang: jeder bekommt dann eine Laterne in der Mitte."""
    hall = walk.difference(unary_union([g for _n, _s, g in rooms.values()]))
    inner = walk.buffer(-0.3)
    out = []
    side = 1
    for pts in L.PATHS:
        ls = LineString(pts)
        k = min(2.0, ls.length / 2)
        while k <= max(ls.length - 1.0, ls.length / 2):
            a, b = ls.interpolate(max(0.0, k - 0.1)), ls.interpolate(min(ls.length, k + 0.1))
            dx, dy = b.x - a.x, b.y - a.y
            n = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / n, dx / n
            c = ls.interpolate(k)
            for sgn in (side, -side):
                p = Point(c.x + nx * 1.0 * sgn, c.y + ny * 1.0 * sgn)   # Wege 2,8 m breit (Innenstreifen bis 1,1 m)
                if inner.contains(p) and hall.buffer(0.2).contains(p) and all(p.distance(Point(q)) > 3.5 for q in out):
                    out.append((round(p.x, 2), round(p.y, 2)))
                    break
            side = -side
            k += 5.0
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


def face_height(clip, x0, x1, y, hmax):
    """Hoehe der Stirnseite eines Wandstuecks: wie weit die feste Masse ueber der Wand reicht (abgetastet
    alle 0,1 m, unteres Drittel der Tiefen, damit Tuerlaibungen und Wegsaeume die Wand nicht druecken)."""
    xs = [x0 + 0.05 + k * 0.1 for k in range(max(1, int((x1 - x0 - 0.1) / 0.1) + 1))]
    depths = []
    for x in xs:
        h = 0.0
        while h + 0.1 <= hmax + 1e-6 and clip.contains(Point(x, y + h + 0.1 - 0.02)):
            h += 0.1
        depths.append(h)
    depths.sort()
    return max(0.3, min(hmax, depths[len(depths) // 3]))


def faces(F, walk, rooms, water):
    """Stirnseiten der Nordwaende (so hoch wie die feste Masse darueber, hoechstens FACADE h) + Kontaktschatten."""
    ppm = F.ppm
    solid = box(F.x0 - 5, F.y0 - 5, F.x1 + 5, F.y1 + 5).difference(walk)
    rail_u = unary_union([G.shape(s) for s in L.RAIL])
    clipper = solid.difference(rail_u.buffer(0.02)).difference(water.buffer(0.05)).buffer(0)
    pclip = prep(clipper)
    wet = water.buffer(0.05)
    d = F.draw()
    shadows = []                                                        # Kontaktschatten, am Ende weich
    _GLOWS.clear()
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
                spec = FACADE.get(key)
                hmax = spec.get("h", 0.9) if spec else 1.0
                fh = face_height(pclip, min(x0, x1), max(x0, x1), min(y0, y1), hmax)
                face = Polygon([(x0, y0), (x1, y1), (x1, y1 + fh), (x0, y0 + fh)]).intersection(clipper.buffer(0.001))
                if face.is_empty:
                    continue
                if spec:
                    draw_facade(F, d, face, spec, min(x0, x1), max(x0, x1), min(y0, y1), fh, seed=int(x0 * 10 + y0 * 3))
                else:
                    draw_hedge(F, d, face, min(x0, x1), max(x0, x1), min(y0, y1), fh)
                sh = Polygon([(x0, y0 + 0.05), (x1, y1 + 0.05), (x1, y1 - 0.28), (x0, y0 - 0.28)]).intersection(walk)
                shadows.extend(G_parts(sh))
    # Kontaktschatten weich (Stilblatt: Schatten weich, keine harten Rechtecke)
    pen = DECOR.Pen(F)

    def draw_shadows(dd):
        for q in shadows:
            dd.polygon([F.P(*c) for c in q.exterior.coords], fill=(0, 0, 0, 80))
    pen.soft(draw_shadows, 0.1)
    if _GLOWS:                                                          # Neon-Lichthoefe in einer weichen Ebene

        def draw_glows(dd):
            for gx0, gy0, gx1, gy1, col in _GLOWS:
                dd.rounded_rectangle([F.P(gx0, gy1), F.P(gx1, gy0)], radius=int(0.15 * ppm), fill=col)
        pen.soft(draw_glows, 0.14)


def draw_facade(F, d, face, spec, xa, xb, yb, fh, seed=0):
    """Gebaeudefassade nach FACADE-Vorgabe (siehe Tabelle oben). `face` ist das schon auf die feste Masse
    beschnittene Stirnseiten-Polygon des Wandstuecks xa..xb; fy1 - fy0 ist die Hoehe (0,5 m an Gassen,
    bis 1,5 m am Hinterland), die Ausstattung richtet sich danach (kurz: kompakt, Schild haengt am Rand)."""
    ppm = F.ppm
    rnd = random.Random(seed)
    pen = DECOR.Pen(F)
    fx0, fy0, fx1, fy1 = face.bounds
    H = fy1 - fy0
    tall = H >= 0.85
    col = spec["col"]
    seam = spec["seam"]
    clip = face.buffer(0.001)

    def P(x, y):
        return F.P(x, y)

    def shape(g, fill):
        for q in G_parts(g):
            d.polygon([P(*c) for c in q.exterior.coords], fill=fill)

    def band(x0, y0, x1, y1, c):
        shape(box(x0, y0, x1, y1).intersection(clip), c)

    sockel_h = 0.1 if tall else 0.07
    awn_h = (0.26 if tall else 0.18) if spec.get("awning") else 0.0
    val_h = (0.22 if tall else 0.14) if spec.get("valance") else 0.0
    top_y = fy1 - awn_h - val_h                                         # bis hier reicht das Material
    shape(face, col + (255,))
    mat = spec["mat"]
    if mat == "brick":
        # Ziegel in Reihen (0,13 m), Laeuferverband, jeder Ziegel eigener Ton, Fugen als zittrige Linien
        stones = HD.stone_grid(fx0, fy0, fx1, top_y, 0.3, 0.13, seed=seed, joint=0.022, jitter=0.07,
                               tilt=0.0, skip=0.0, split=0.05, merge=0.0, bond=0.5)
        shape(face, seam + (255,))
        for i, st in enumerate(stones):
            g = Polygon(st.pts).intersection(clip)
            if g.is_empty:
                continue
            t = 1 + st.tone * 0.1
            c = tuple(max(0, min(255, int(v * t))) for v in col)
            pts = HD.wobble(st.pts, amp=0.005, seed=seed + i, step=0.05, closed=True)
            shape(Polygon(pts).intersection(clip), c + (255,))
            shape(Polygon(HD.edge_strip(st.pts, 2, 0.018)).intersection(clip), (255, 240, 220, 45))   # Lichtkante oben (y+)
            shape(Polygon(HD.edge_strip(st.pts, 0, 0.016)).intersection(clip), (0, 0, 0, 45))         # Schatten unten
    elif mat == "planks":
        # senkrechte Bretter 0,22 m, Nahtlinien zittrig, je Brett eigener Ton, Astloecher
        shape(face, col + (255,))
        k = 0
        prev = fx0
        while prev < fx1:
            w = rnd.uniform(0.18, 0.26)
            nx = min(fx1, prev + w)
            t = 1 + rnd.uniform(-0.06, 0.06)
            c = tuple(max(0, min(255, int(v * t))) for v in col)
            band(prev, fy0, nx, top_y, c + (255,))
            band(prev, fy0, prev + 0.03, top_y, (255, 255, 255, 30))
            if k > 0:
                pts = HD.wobble([(prev, fy0), (prev, top_y)], amp=0.004, seed=seed + k, step=0.06)
                HD.ink(d, [P(*q) for q in pts], seam + (220,), max(1, int(0.018 * ppm)), seed=k, var=0.3)
            if rnd.random() < 0.3:
                ky = rnd.uniform(fy0 + 0.15, max(fy0 + 0.16, top_y - 0.1))
                pen.ell((prev + nx) / 2, ky, 0.022, 0.016, seam + (255,))
            prev = nx
            k += 1
    elif mat == "metal":
        # Wellblech: senkrechte Wellen (Licht/Schatten-Paare alle 0,1 m), zittrige Plattenstoesse jeden Meter
        x = fx0
        while x < fx1:
            band(x, fy0, x + 0.035, top_y, (255, 255, 255, 40))
            band(x + 0.05, fy0, x + 0.085, top_y, (0, 0, 0, 55))
            x += 0.1
        x = math.floor(fx0) + 1.0
        while x < fx1:
            pts = HD.wobble([(x, fy0), (x, top_y)], amp=0.004, seed=seed + int(x), step=0.06)
            HD.ink(d, [P(*q) for q in pts], seam + (255,), max(1, int(0.022 * ppm)), seed=int(x), var=0.3)
            for yy in (fy0 + 0.16, top_y - 0.1):
                if yy > fy0 + 0.1:
                    pen.ell(x, yy, 0.02, 0.02, (160, 168, 184, 255), OUTLINE + (255,), 0.01)
            x += 1.0
    elif mat == "canvas":
        # Zeltstoff: senkrechte Bahnen 0,5 m in zwei Farben, Naehte leicht zittrig, Falten als helle Striche
        a_, b_ = col, spec["stripe"]
        x = math.floor(fx0 / 0.5) * 0.5
        i = int(round(x / 0.5))
        while x < fx1:
            band(x, fy0, x + 0.5, top_y, (b_ if i % 2 else a_) + (255,))
            pts = HD.wobble([(x, fy0), (x, top_y)], amp=0.006, seed=seed + i, step=0.06)
            HD.ink(d, [P(*q) for q in pts], seam + (160,), max(1, int(0.014 * ppm)), seed=i, var=0.3)
            for f in (0.3, 0.7):                                                               # Falten
                pts = HD.wobble([(x + 0.5 * f, fy0 + 0.1), (x + 0.5 * f + 0.03, top_y - 0.05)], amp=0.01, seed=seed + i * 3 + int(f * 10), step=0.08)
                g = LineString(pts).buffer(0.008).intersection(clip)
                shape(g, (255, 255, 255, 28 if i % 2 else 18))
            x += 0.5
            i += 1
    # Sockel und Lichtkante
    band(fx0, fy0, fx1, fy0 + sockel_h, spec.get("sockel", (60, 56, 60)) + (255,))
    band(fx0, fy0 + sockel_h, fx1, fy0 + sockel_h + 0.025, (0, 0, 0, 70))
    band(fx0, fy0, fx1, fy0 + 0.03, (0, 0, 0, 90))
    if spec.get("hazard"):                                              # gelb/schwarze Schraege auf dem Sockel
        x = fx0
        k = 0
        while x < fx1:
            g = Polygon([(x, fy0 + 0.01), (x + 0.15, fy0 + 0.01), (x + 0.22, fy0 + sockel_h), (x + 0.07, fy0 + sockel_h)]).intersection(clip)
            shape(g, ((220, 180, 50, 255) if k % 2 == 0 else (30, 28, 30, 255)))
            x += 0.15
            k += 1
    # Fenster (beleuchtet, Kreuzsprosse, optional Jalousie)
    if spec.get("window") or spec.get("window_at"):
        wc = spec.get("window_col", (255, 214, 140))
        ww = spec.get("window_w", 0.5)
        if spec.get("window_at"):
            xs = [x for x in spec["window_at"] if fx0 + 0.1 <= x and x + ww <= fx1 - 0.1]
        else:
            xs = []
            x = fx0 + 0.6
            while x + ww < fx1 - 0.4:
                xs.append(x)
                x += spec["window"]
        for x in xs:
            if tall:
                wy0, wy1 = fy0 + 0.3, min(top_y - 0.12, fy0 + 0.78)
            else:
                wy0, wy1 = fy0 + sockel_h + 0.05, top_y - 0.06
            if wy1 - wy0 < 0.12:
                continue
            for grow, al in ((0.22, 22), (0.14, 30), (0.07, 40)):                          # Lichthof
                shape(box(x - grow, wy0 - grow, x + ww + grow, wy1 + grow).intersection(clip), wc + (al,))
            pen.hrect(x, wy0, x + ww, wy1, wc + (255,), OUTLINE + (255,), 0.03, seed=seed + int(x * 10))
            if spec.get("blinds"):
                # Jalousie: Lamellen ueber den oberen zwei Dritteln, Zugschnur rechts
                ly = wy1 - 0.03
                while ly > wy0 + (wy1 - wy0) * 0.3:
                    pen.rect(x + 0.02, ly - 0.012, x + ww - 0.02, ly, (90, 80, 70, 255))
                    pen.rect(x + 0.02, ly - 0.028, x + ww - 0.02, ly - 0.012, (236, 226, 200, 255))
                    ly -= 0.04
                pen.line([(x + ww - 0.05, wy1), (x + ww - 0.05, wy0 + 0.05)], (80, 70, 60, 255), 0.008)
                pen.ell(x + ww - 0.05, wy0 + 0.05, 0.012, 0.012, (200, 190, 160, 255))
            else:
                pen.line([(x + ww / 2, wy0), (x + ww / 2, wy1)], OUTLINE + (255,), 0.02)
                pen.line([(x, (wy0 + wy1) / 2), (x + ww, (wy0 + wy1) / 2)], OUTLINE + (255,), 0.02)
                pen.rect(x + 0.04, wy0 + 0.04, x + ww / 2 - 0.04, (wy0 + wy1) / 2 - 0.02, (255, 240, 200, 120))
            pen.rect(x - 0.04, wy0 - 0.05, x + ww + 0.04, wy0, (90, 70, 60, 255), OUTLINE + (255,), 0.015)   # Fensterbank
    # Markise: zwei Streifenfarben, Volant mit Bogenkante, Schattenband darunter
    if spec.get("awning"):
        a, b = spec["awning"]
        ay0 = fy1 - awn_h
        band(fx0, ay0 - 0.08, fx1, ay0, (0, 0, 0, 60))
        x = math.floor(fx0 / 0.4) * 0.4
        i = int(round(x / 0.4))
        while x < fx1:
            band(x, ay0, x + 0.4, fy1, (a if i % 2 else b) + (255,))
            x += 0.4
            i += 1
        x = math.floor(fx0 / 0.4) * 0.4
        i = int(round(x / 0.4))
        while x < fx1:
            g = Point(x + 0.2, ay0).buffer(0.2).intersection(box(x, ay0 - 0.2, x + 0.4, ay0)).intersection(box(fx0, fy0, fx1, fy1))
            for q in G_parts(g):
                if q.area < 1e-4:
                    continue
                pts = HD.wobble(list(q.exterior.coords), amp=0.004, seed=seed + i, step=0.04, closed=True)
                d.polygon([P(*c) for c in pts], fill=(a if i % 2 else b) + (255,))
                HD.ink(d, [P(*c) for c in pts], OUTLINE + (255,), max(1, int(0.02 * ppm)), seed=i, var=0.3, closed=True)
            x += 0.4
            i += 1
        pts = HD.wobble([(fx0, fy1 - 0.02), (fx1, fy1 - 0.02)], amp=0.004, seed=seed + 7, step=0.08)
        HD.ink(d, [P(*q) for q in pts], OUTLINE + (255,), max(1, int(0.025 * ppm)), seed=3, var=0.25)
        band(fx0, fy1 - 0.06, fx1, fy1 - 0.025, (255, 255, 255, 50))
    elif spec.get("valance"):
        # Zackenvolant (Zelt): Dreiecke haengen von der Oberkante, Goldband darueber
        vc = spec["valance"]
        band(fx0, fy1 - val_h, fx1, fy1, vc + (255,))
        band(fx0, fy1 - val_h - 0.06, fx1, fy1 - val_h, (0, 0, 0, 55))
        x = math.floor(fx0 / 0.3) * 0.3
        i = 0
        while x < fx1:
            g = Polygon([(x, fy1 - val_h), (x + 0.3, fy1 - val_h), (x + 0.15, fy1 - val_h - 0.16)]).intersection(box(fx0, fy0, fx1, fy1))
            for q in G_parts(g):
                if q.area < 1e-4:
                    continue
                pts = HD.wobble(list(q.exterior.coords), amp=0.004, seed=seed + i, step=0.04, closed=True)
                d.polygon([P(*c) for c in pts], fill=vc + (255,))
                HD.ink(d, [P(*c) for c in pts], OUTLINE + (255,), max(1, int(0.018 * ppm)), seed=i, var=0.3, closed=True)
            x += 0.3
            i += 1
        pts = HD.wobble([(fx0, fy1 - 0.03), (fx1, fy1 - 0.03)], amp=0.004, seed=seed + 7, step=0.08)
        HD.ink(d, [P(*q) for q in pts], OUTLINE + (255,), max(1, int(0.03 * ppm)), seed=3, var=0.25)
        band(fx0, fy1 - 0.07, fx1, fy1 - 0.03, (255, 255, 255, 60))
    else:
        band(fx0, fy1 - 0.05, fx1, fy1, (255, 255, 255, 40))
        pts = HD.wobble([(fx0, fy1 - 0.015), (fx1, fy1 - 0.015)], amp=0.004, seed=seed + 7, step=0.08)
        HD.ink(d, [P(*q) for q in pts], OUTLINE + (200,), max(1, int(0.02 * ppm)), seed=3, var=0.25)
    # Gluehbirnenleiste unter der Markise bzw. dem Volant (bzw. an der Oberkante)
    if spec.get("bulbs"):
        by = top_y - 0.04 if (awn_h or val_h) else fy1 - 0.12
        x = fx0 + 0.2
        while x < fx1 - 0.1:
            pen.line([(x - 0.2, by - 0.03), (x, by - 0.08), (x + 0.2, by - 0.03)], (40, 30, 30, 255), 0.012)
            x += 0.4
        x = fx0 + 0.2
        while x < fx1 - 0.1:
            for r, al in ((0.2, 35), (0.13, 55), (0.08, 90)):
                pen.ell(x, by - 0.08, r, r * 0.8, (255, 214, 140, al))
            pen.ell(x, by - 0.08, 0.035, 0.045, (255, 236, 180, 255), (120, 90, 40, 255), 0.012)
            x += 0.4
    # Wimpelkette ueber die ganze Wand (durchhaengend)
    if spec.get("pennants") and fx1 - fx0 > 0.8:
        cols = spec["pennants"]
        py = top_y - (0.12 if tall else 0.06)
        pts = [(fx0 + (fx1 - fx0) * t, py - 0.12 * math.sin(math.pi * t)) for t in [i / 20 for i in range(21)]]
        pen.line(pts, (40, 30, 30, 255), 0.015)
        for i, (px, py_) in enumerate(pts[:-1]):
            pen.hpoly([(px, py_), (px + (fx1 - fx0) / 20, py_), (px + (fx1 - fx0) / 40, py_ - 0.2)], cols[i % len(cols)], INK_, 0.012, seed=seed + i)
    # Reif: weisse Schlieren am Sockel, Eiszapfen unter der Markise
    if spec.get("frost"):
        for _ in range(int((fx1 - fx0) * 5)):
            x, y = rnd.uniform(fx0, fx1), rnd.uniform(fy0 + 0.08, fy0 + 0.3)
            pen.ell(x, y, rnd.uniform(0.06, 0.16), rnd.uniform(0.02, 0.05), (240, 250, 255, 70))
        if spec.get("awning"):
            x = fx0 + rnd.uniform(0.05, 0.3)
            while x < fx1 - 0.05:
                h = rnd.uniform(0.06, 0.16)
                pen.poly([(x - 0.025, fy1 - awn_h - 0.18), (x + 0.025, fy1 - awn_h - 0.18), (x, fy1 - awn_h - 0.18 - h)], (226, 242, 252, 230), (150, 190, 215, 255), 0.01)
                x += rnd.uniform(0.15, 0.4)
    # Kabel mit Isolatoren ueber der Wand (Umspannhaus)
    if spec.get("cables"):
        for k in range(3):
            yy = top_y - 0.06 - k * 0.06
            pts = [(fx0 + (fx1 - fx0) * t, yy - 0.05 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
            pen.hline(pts, (20, 18, 22, 255), 0.018, seed=seed + k, amp=0.004)
        for x in (fx0 + 0.3, (fx0 + fx1) / 2, fx1 - 0.3):
            pen.rect(x - 0.03, top_y - 0.26, x + 0.03, top_y - 0.03, (90, 94, 100, 255), OUTLINE + (255,), 0.012)
            for k in range(3):
                pen.ell(x, top_y - 0.08 - k * 0.06, 0.045, 0.02, (120, 150, 140, 255), OUTLINE + (255,), 0.01)
    # Warndreiecke (gelb, Blitz)
    for x in spec.get("warn", []):
        if fx0 + 0.2 <= x <= fx1 - 0.2:
            yc = fy0 + (0.42 if tall else 0.3)
            pen.hpoly([(x - 0.2, yc - 0.17), (x + 0.2, yc - 0.17), (x, yc + 0.18)], (236, 196, 50, 255), INK_, 0.025, seed=seed + int(x * 7))
            pen.poly([(x + 0.03, yc + 0.1), (x - 0.05, yc - 0.01), (x + 0.01, yc - 0.01), (x - 0.04, yc - 0.12), (x + 0.06, yc + 0.01), (x, yc + 0.01)], INK_)
    # Blitzsymbole (Autoscooter, neonblau)
    for x in spec.get("bolts", []):
        if fx0 + 0.2 <= x <= fx1 - 0.2:
            yc = fy0 + (0.5 if tall else 0.28)
            pen.hpoly([(x + 0.05, yc + 0.2), (x - 0.09, yc - 0.02), (x + 0.01, yc - 0.02), (x - 0.07, yc - 0.22), (x + 0.1, yc + 0.02), (x, yc + 0.02)], (110, 230, 255, 255), INK_, 0.02, seed=seed + int(x * 3))
            _GLOWS.append((x - 0.25, yc - 0.3, x + 0.25, yc + 0.28, (110, 230, 255, 70)))
    # Zielscheiben (Schiessbude)
    for x in spec.get("targets", []):
        if fx0 + 0.3 <= x <= fx1 - 0.3:
            yc = fy0 + (0.55 if tall else 0.3)
            r0 = 0.27 if tall else 0.17
            for r, c in ((r0, (240, 240, 230, 255)), (r0 * 0.68, (176, 52, 62, 255)), (r0 * 0.33, (240, 240, 230, 255))):
                pen.hell(x, yc, r, r, c, INK_ if r == r0 else None, 0.02, seed=seed + int(x * 10) + int(r * 100))
            pen.ell(x, yc, r0 * 0.1, r0 * 0.1, INK_)
            pen.line([(x - r0 * 0.5, yc - r0 * 1.15), (x, yc - r0 * 0.85), (x + r0 * 0.5, yc - r0 * 1.15)], (90, 60, 40, 255), 0.02)   # Halter
    # rotes Kreuz im weissen Kreis (Sanitaetszelt)
    for x in spec.get("cross", []):
        if fx0 + 0.4 <= x <= fx1 - 0.4:
            yc = fy0 + (0.62 if tall else 0.3)
            r = 0.36 if tall else 0.18
            pen.hell(x, yc, r, r, (246, 246, 240, 255), INK_, 0.025, seed=seed + 3)
            pen.rect(x - r * 0.22, yc - r * 0.65, x + r * 0.22, yc + r * 0.65, (200, 50, 50, 255))
            pen.rect(x - r * 0.65, yc - r * 0.22, x + r * 0.65, yc + r * 0.22, (200, 50, 50, 255))
    # Totenkoepfe mit Spinnweben (Geisterbahn)
    for x in spec.get("skulls", []):
        if fx0 + 0.3 <= x <= fx1 - 0.3:
            yc = fy0 + (0.55 if tall else 0.3)
            pen.hell(x, yc, 0.2, 0.22, (220, 214, 200, 255), INK_, 0.02, seed=seed + 5)
            pen.rect(x - 0.1, yc - 0.3, x + 0.1, yc - 0.14, (220, 214, 200, 255), INK_, 0.015)
            for dx in (-0.075, 0.075):
                pen.ell(x + dx, yc + 0.03, 0.05, 0.06, INK_)
                pen.ell(x + dx, yc + 0.04, 0.02, 0.02, (120, 255, 130, 255))
            pen.poly([(x, yc - 0.05), (x - 0.025, yc - 0.1), (x + 0.025, yc - 0.1)], INK_)
            for k in range(3):
                pen.line([(x - 0.06 + k * 0.06, yc - 0.16), (x - 0.06 + k * 0.06, yc - 0.26)], INK_, 0.012)
    if spec.get("webs"):
        for (wx, sx) in ((fx0, 1), (fx1, -1)):
            for k in range(4):
                a = math.radians(k * 30)
                pen.line([(wx, fy1), (wx + sx * math.cos(a) * 0.45, fy1 - math.sin(a) * 0.45)], (200, 200, 210, 120), 0.01)
            for r in (0.15, 0.3, 0.42):
                pts = [(wx + sx * math.cos(math.radians(k * 30)) * r, fy1 - math.sin(math.radians(k * 30)) * r) for k in range(4)]
                pen.line(pts, (200, 200, 210, 110), 0.008)
    if spec.get("drips"):
        dc = spec["drips"]
        x = fx0 + rnd.uniform(0.1, 0.3)
        while x < fx1 - 0.1:
            h = rnd.uniform(0.08, 0.3)
            pen.line([(x, fy1 - 0.02), (x, fy1 - h)], dc + (200,), 0.025)
            pen.ell(x, fy1 - h, 0.02, 0.025, dc + (220,))
            x += rnd.uniform(0.25, 0.7)
    # Poster (Musikzentrale, Buero)
    for (x, pc, motif) in spec.get("posters", []):
        if fx0 + 0.35 <= x <= fx1 - 0.35:
            y = fy0 + (0.2 if tall else 0.09)
            hh = 0.62 if tall else 0.36
            pen.hrect(x - 0.28, y, x + 0.28, y + hh, (236, 226, 200, 255), INK_, 0.02, seed=seed + int(x * 10))
            pen.rect(x - 0.22, y + 0.12, x + 0.22, y + hh - 0.06, pc + (255,))
            if motif == "star":
                pen.star(x, y + hh * 0.56, 0.14, 0.06, (250, 230, 120, 255))
            else:
                pen.ell(x, y + hh * 0.56, 0.1, 0.11, (250, 230, 120, 255))
            pen.rect(x - 0.18, y + 0.04, x + 0.18, y + 0.09, (60, 50, 60, 255))
    # Mondsichel (Festplatz) und Sterne (Karussell)
    for x in spec.get("moon", []):
        if fx0 + 0.3 <= x <= fx1 - 0.3:
            yc = fy0 + (0.55 if tall else 0.3)
            r = 0.22 if tall else 0.14
            pen.hell(x, yc, r, r, (250, 222, 120, 255), INK_, 0.02, seed=seed + 9)
            pen.ell(x + r * 0.5, yc + r * 0.15, r * 0.8, r * 0.82, col + (255,))
            pen.ell(x + r * 0.5, yc + r * 0.15, r * 0.8, r * 0.82, None, INK_, 0.02)
    for x in spec.get("stars", []):
        if fx0 + 0.25 <= x <= fx1 - 0.25:
            yc = fy0 + (0.55 if tall else 0.3)
            pen.star(x, yc, 0.2 if tall else 0.12, 0.09 if tall else 0.05, (250, 222, 120, 255), INK_)
    # Lautsprecherhorn (Musikzentrale)
    for x in spec.get("speaker", []):
        if fx0 + 0.3 <= x <= fx1 - 0.3:
            yc = top_y - 0.3
            pen.hpoly([(x - 0.12, yc - 0.08), (x + 0.12, yc - 0.08), (x + 0.22, yc + 0.14), (x - 0.22, yc + 0.14)], (70, 70, 80, 255), INK_, 0.02, seed=seed + 4)
            pen.ell(x, yc + 0.14, 0.22, 0.06, (40, 40, 48, 255), INK_, 0.015)
            pen.line([(x, yc - 0.08), (x, yc - 0.2)], (60, 60, 70, 255), 0.03)
    # Wanduhr (Buero)
    for x in spec.get("clock", []):
        if fx0 + 0.3 <= x <= fx1 - 0.3:
            yc = fy0 + (0.6 if tall else 0.3)
            r = 0.22 if tall else 0.15
            pen.hell(x, yc, r, r, (240, 236, 220, 255), INK_, 0.025, seed=seed + 2)
            pen.line([(x, yc), (x, yc + r * 0.6)], INK_, 0.025)
            pen.line([(x, yc), (x + r * 0.45, yc)], INK_, 0.025)
            pen.ell(x, yc, 0.02, 0.02, INK_)
    # Schilder: Text auf Schild, bei Neon mit Lichthof; kurze Waende: Schild sitzt auf dem Sockel und darf
    # bis 0,1 m ueber die Oberkante haengen (lesbar braucht es 0,26 m Schrift bei 80 px/m)
    signs = list(spec.get("signs", []))
    if spec.get("sign"):
        text, bg, fg = spec["sign"]
        signs.append((spec.get("sign_x", (fx0 + fx1) / 2), text, bg, fg, spec.get("sign_size", 0.26)))
    for sg in signs:
        sx, text, bg, fg = sg[:4]
        size = sg[4] if len(sg) > 4 else 0.26
        neon_ = sg[5] if len(sg) > 5 else False
        w = len(text) * size * 0.6 + 0.3
        if not (fx0 + 0.05 <= sx - w / 2 and sx + w / 2 <= fx1 - 0.05):
            continue
        sh = size * 1.6
        if tall:
            sy1 = top_y - (0.16 if spec.get("bulbs") else 0.06)
            sy0 = sy1 - sh
            if spec.get("targets") or spec.get("cross") or spec.get("moon"):
                sy0, sy1 = fy0 + 0.95, fy0 + 0.95 + sh                     # ueber den Motiven
                if sy1 > top_y - 0.05:
                    sy0, sy1 = top_y - 0.05 - sh, top_y - 0.05
        else:
            sy0 = fy0 + sockel_h + 0.01
            sy1 = min(sy0 + sh, fy1 + 0.1)
            size = min(size, (sy1 - sy0) / 1.6)
        pts = HD.wobble_rect(sx - w / 2, sy0, sx + w / 2, sy1, amp=0.004, seed=seed + 11, step=0.05)
        d.polygon([P(*q) for q in [(x + 0.02, y - 0.03) for x, y in pts]], fill=(0, 0, 0, 90))
        d.polygon([P(*q) for q in pts], fill=bg + (255,))
        HD.ink(d, [P(*q) for q in pts], OUTLINE + (255,), max(1, int(0.03 * ppm)), seed=seed, var=0.25, closed=True)
        pen.rect(sx - w / 2 + 0.04, sy1 - 0.06, sx + w / 2 - 0.04, sy1 - 0.035, (255, 255, 255, 45))
        if neon_:
            _GLOWS.append((sx - w / 2 + 0.05, sy0 + 0.05, sx + w / 2 - 0.05, sy1 - 0.05, fg + (110,)))
            pen.text(sx, (sy0 + sy1) / 2, text, size, fg + (255,))
            pen.text(sx, (sy0 + sy1) / 2, text, size, (255, 255, 255, 90))        # heller Roehrenkern, gleiche Groesse
            for hx in (sx - w / 2 + 0.06, sx + w / 2 - 0.06):                                 # Neonroehren-Halter
                pen.ell(hx, sy0 + 0.05, 0.015, 0.015, (120, 120, 130, 255))
        else:
            pen.text(sx, (sy0 + sy1) / 2, text, size, fg + (255,))
        for hx in (sx - w / 2 + 0.08, sx + w / 2 - 0.08):                                     # Aufhaengung
            pen.line([(hx, sy1), (hx, min(sy1 + 0.1, fy1 + 0.02))], (40, 30, 30, 255), 0.015)


INK_ = (18, 14, 22, 255)


def draw_hedge(F, d, face, xa, xb, yb, fh):
    """Hecke an den Nordraendern der Lichtungen und Wege: handgezeichnete Blaetterballen in zwei
    Gruentoenen mit zittrigem Umriss, Lichtkante oben, einzelne Beeren, dunkler Fuss."""
    fx0, fy0, fx1, fy1 = face.bounds
    clip = face
    rnd = random.Random(int(fx0 * 100 + fy0 * 7))
    pen = DECOR.Pen(F)
    for q in G_parts(face):
        d.polygon([F.P(*c) for c in q.exterior.coords], fill=(22, 44, 30, 255))
    blobs = []
    x = fx0 - 0.1
    while x < fx1 + 0.3:
        r = rnd.uniform(0.2, 0.34)
        cy = fy1 - r * 0.55 - rnd.uniform(0, max(0.0, fy1 - fy0 - r * 1.2))
        blobs.append((x, cy, r, rnd.uniform(0.85, 1.25)))
        x += r * 1.15
    blobs.sort(key=lambda b: b[1])
    for i, (bx, by, r, t) in enumerate(blobs):
        pts = HD.wobble_ellipse(bx, by, r, r * 0.9, amp=0.02, seed=i + int(fx0 * 10))
        g = Polygon(pts).intersection(clip.buffer(0.06)).intersection(box(fx0, fy0, fx1, fy1 + 0.2))
        for qq in G_parts(g):
            if qq.area < 1e-4:
                continue
            col = tuple(int(v * t) for v in HEDGE)
            d.polygon([F.P(*c) for c in qq.exterior.coords], fill=col + (255,))
            HD.ink(d, [F.P(*c) for c in qq.exterior.coords], (10, 22, 14, 255), max(1, int(0.025 * F.ppm)), seed=i, var=0.3, closed=True)
            hl = Polygon(HD.wobble_ellipse(bx - r * 0.25, by + r * 0.3, r * 0.5, r * 0.35, amp=0.01, seed=i + 7)).intersection(qq)
            for hq in G_parts(hl):
                d.polygon([F.P(*c) for c in hq.exterior.coords], fill=tuple(min(255, int(v * 1.35)) for v in col) + (255,))
        if rnd.random() < 0.25:
            for _ in range(3):
                pen.ell(bx + rnd.uniform(-r * 0.5, r * 0.5), by + rnd.uniform(-r * 0.4, r * 0.4), 0.022, 0.022, (200, 60, 70, 255), (60, 20, 24, 255), 0.01)
    # Fuss im Schatten
    for q in G_parts(box(fx0, fy0, fx1, fy0 + 0.1).intersection(clip)):
        d.polygon([F.P(*c) for c in q.exterior.coords], fill=(0, 0, 0, 110))
