"""Unknown's Atlas - Grafik der Rauswurf- und Skip-Szenen des Moonlight Carnival (docs/PARK_KONZEPT.md).

Gleiches Raster wie gen_eject.py: 100 px pro Szenen-Einheit, Ursprung Bildmitte, y nach oben; Export mit
K = 1,8 (180 px pro Einheit). Alle Dateien heissen task_eject_pk_*, damit nichts mit Museum/Wald kollidiert.
Die Koordinaten, auf die sich eject_scenes.py verlaesst (Kanonenzapfen, Riesenrad-Nabe, Rinne, Maul,
Looping), stehen als Konstanten oben und werden dort importiert.

    python tools/gen_eject_park.py
"""

import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_tasks import C, S, INK, OUT, mix, dark, light, label  # noqa: E402
from gen_eject import BW, BH, ux, uy, save, save_bg, grad, rect, stars, moon  # noqa: E402

RED, RED_L, RED_D = (200, 56, 62, 255), (232, 98, 98, 255), (146, 36, 44, 255)
CREAM = (244, 232, 204, 255)
GOLD, GOLD_D = (236, 190, 70, 255), (170, 126, 40, 255)
PLUM, PLUM_D = (86, 56, 122, 255), (52, 34, 78, 255)
TEAL = (46, 146, 150, 255)
BULB = (255, 234, 170, 255)
TRANSP = (0, 0, 0, 0)

# ---- Kontrakte mit eject_scenes.py (Szenen-Einheiten)
GROUND = -1.25                              # Festplatz: Bodenlinie
MOON_FAIR = (-3.6, 2.1)                     # Mond der Kanonen-Szene
FERRIS_HUB, FERRIS_R = (-0.6, -2.6), 4.2     # Riesenrad (die oberste Gondel haengt an HUB + (0, R))
FLUME_Y, FLUME_EDGE, POOL_Y = 0.3, 1.4, -2.2  # Rinne: Wasserlinie, Kante, Becken
TRACK_Y = -1.6                              # Geisterbahn: Schiene
MAW_X = 2.2                                 # Geisterbahn: Vorderkante des Mauls
LOOP_C, LOOP_R = (0.3, 0.3), 1.9            # Looping (Schienenmitte)
LOOP_BASE = LOOP_C[1] - LOOP_R              # Schiene unten


def P(x, y):
    return ux(x), uy(y)


def bulb(c, x, y, r=4, a=120):
    c.glow(x, y, r * 2, r * 2, (255, 214, 130, a), r)
    c.ell(x, y, r, r, BULB, lw=0)


def string_lights(c, x0, y0, x1, y1, sag, n, seed=0):
    pts = [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * math.sin(math.pi * t)) for t in [i / (n * 2) for i in range(n * 2 + 1)]]
    c.line(pts, (30, 24, 34, 255), 2)
    rnd = random.Random(seed)
    for x, y in pts[1::2]:
        col = rnd.choice(((255, 226, 150, 255), (255, 170, 150, 255), (170, 230, 220, 255)))
        c.glow(x, y + 3, 9, 9, col[:3] + (110,), 4)
        c.ell(x, y + 3, 3.5, 3.5, col, lw=0)


def big_top(c, cx, base, w, h, col_a, col_b, dim=1.0):
    """Zirkuszelt als Kulisse (gedaempfte Farben)."""
    a, b = mix((20, 18, 30, 255), col_a, dim), mix((20, 18, 30, 255), col_b, dim)
    roof = [(cx - w / 2, base - h * 0.45), (cx, base - h), (cx + w / 2, base - h * 0.45)]
    body = [(cx - w / 2, base - h * 0.45), (cx + w / 2, base - h * 0.45), (cx + w / 2 - 10, base), (cx - w / 2 + 10, base)]
    c.poly(body, a, lw=4)
    for k in range(-4, 5):
        x = cx + k * w / 9
        c.poly([(x - w / 36, base - h * 0.45), (x + w / 36, base - h * 0.45), (x + w / 36, base), (x - w / 36, base)], b, lw=0)
    c.poly(body, None, lw=4)
    c.poly(roof, a, lw=4)
    for k in range(-4, 5, 2):
        c.poly([(cx, base - h), (cx + k * w / 9 - w / 18, base - h * 0.45), (cx + k * w / 9 + w / 18, base - h * 0.45)], b, lw=0)
    c.poly(roof, None, lw=4)
    for k in range(-4, 5):                                             # Volant
        c.ell(cx + k * w / 9, base - h * 0.45, w / 18, 10, a, lw=3)
    c.line([(cx, base - h), (cx, base - h - 40)], INK, 4)
    c.poly([(cx, base - h - 40), (cx + 34, base - h - 30), (cx, base - h - 20)], mix((20, 18, 30, 255), RED, dim), lw=3)
    c.poly([(cx - 30, base), (cx, base - 70), (cx + 30, base)], (16, 12, 18, 255), lw=3)    # Eingang


def ferris_silhouette(c, cx, cy, r, col, lights=True, n=16):
    c.line([(cx - r * 0.6, cy + r * 1.25), (cx, cy), (cx + r * 0.6, cy + r * 1.25)], col, 8)
    c.ell(cx, cy, r, r, None, lw=6, outline=col)
    c.ell(cx, cy, r * 0.93, r * 0.93, None, lw=2, outline=col)
    for k in range(n):
        a = math.radians(k * 360 / n)
        c.line([(cx, cy), (cx + math.cos(a) * r, cy + math.sin(a) * r)], col, 2)
        c.rrect(cx + math.cos(a) * r - 9, cy + math.sin(a) * r + 2, cx + math.cos(a) * r + 9, cy + math.sin(a) * r + 16, 4, col, lw=0)
    if lights:
        for k in range(n * 2):
            a = math.radians(k * 180 / n)
            bulb(c, cx + math.cos(a) * r, cy + math.sin(a) * r, 2.5, 90)


# ================================================================== Festplatz (Kanone, Karussell, Popcorn)

def fair():
    c = C(BW, BH)
    grad(c, (14, 12, 40), (74, 44, 90), 0, 470)
    stars(c, 90, 300, seed=61)
    moon(c, *P(*MOON_FAIR), 44)
    ferris_silhouette(c, 1030, 250, 150, (54, 40, 78, 255))
    big_top(c, 560, uy(GROUND), 520, 330, RED, CREAM, dim=0.55)
    for x0, x1 in ((0, 300), (820, 1200)):
        string_lights(c, x0, 300, x1, 320, 50, 9, seed=x0)
    for x in (170, 950):                                                # Budendaecher
        c.poly([(x - 110, 420), (x, 360), (x + 110, 420)], (70, 42, 70, 255), lw=4)
        c.rrect(x - 100, 420, x + 100, uy(GROUND), 3, (40, 30, 46, 255), lw=4)
        c.rrect(x - 80, 434, x + 80, 450, 3, (255, 214, 140, 255), lw=0)
        c.glow(x, 440, 110, 30, (255, 200, 120, 60), 16)
    y0 = uy(GROUND)
    grad(c, (92, 64, 44), (40, 28, 22), y0, BH)                          # Boden: festgetretene Erde, Saegemehl
    rnd = random.Random(62)
    for _ in range(420):
        x, y = rnd.uniform(0, BW), rnd.uniform(y0 + 4, BH)
        c.d.ellipse([x * S, y * S, (x + 3) * S, (y + 1.5) * S], fill=(170, 130, 86, 140))
    c.line([(0, y0), (BW, y0)], (30, 22, 20, 255), 4)
    c.glow(600, y0 + 40, 520, 60, (255, 200, 130, 28), 30)
    c.vignette(0.45)
    save_bg(c, "task_eject_pk_fair_bg.jpg")


def cannon():
    # Rohr zeigt nach LINKS (Muendung links), Zapfen bei x 231 (Pivot 0,68 / 0,5); Zuendschnur rechts oben
    c = C(340, 130)
    c.poly([(12, 30), (300, 16), (300, 114), (12, 100)], RED, lw=7, sh=(0.25, 0.35))
    for x in (60, 150, 250):
        t = x / 300
        h0, h1 = 30 - 14 * t, 100 + 14 * t
        c.rrect(x - 8, h0 - 4, x + 8, h1 + 4, 4, GOLD, lw=4, sh=(0.3, 0.3))
    for x in (100, 200):
        c.poly([(x - 10, 62), (x - 3, 58), (x, 50), (x + 3, 58), (x + 10, 62), (x + 4, 67), (x + 6, 75), (x, 70), (x - 6, 75), (x - 4, 67)], CREAM, lw=0)
    c.ell(300, 65, 26, 50, RED_D, lw=6, sh=(0.2, 0.3))                  # Verschluss
    c.ell(318, 65, 12, 20, GOLD, lw=4)
    c.rrect(2, 22, 22, 108, 6, GOLD, lw=5, sh=(0.3, 0.3))                # Muendungsring
    c.ell(12, 65, 7, 36, (20, 14, 18, 255), lw=3)
    c.line([(262, 22), (282, 8), (304, 6), (322, 18), (332, 40)], (190, 150, 90, 255), 5)   # Zuendschnur
    c.ell(262, 22, 5, 5, INK, lw=0)
    c.glint(80, 34, 60, 6, 110, rot=-3)
    save(c, "task_eject_pk_cannon.png")
    c = C(260, 150)                                                     # Lafette mit Speichenraedern, Zapfen bei (130, 30)
    c.poly([(50, 40), (210, 40), (230, 104), (30, 104)], (96, 60, 40, 255), lw=6, sh=(0.2, 0.3))
    c.ell(130, 30, 16, 16, GOLD, lw=5, sh=(0.3, 0.3))
    for wx in (70, 190):
        c.ell(wx, 104, 44, 44, RED_D, lw=6)
        c.ell(wx, 104, 34, 34, None, lw=4, outline=GOLD)
        for k in range(8):
            a = math.radians(k * 45)
            c.line([(wx, 104), (wx + math.cos(a) * 34, 104 + math.sin(a) * 34)], GOLD, 4)
        c.ell(wx, 104, 9, 9, GOLD, lw=3)
    save(c, "task_eject_pk_cannon_cart.png")
    c = C(16, 10)                                                       # Konfetti (weiss, wird eingefaerbt)
    c.d.rectangle([0, 0, 16 * S, 10 * S], fill=(255, 255, 255, 255))
    save(c, "task_eject_pk_confetti.png")


def carousel():
    c = C(640, 230)                                                     # Dach, Unterkante bei y 200
    c.poly([(20, 160), (320, 20), (620, 160)], RED, lw=6, sh=(0.2, 0.3))
    for k in range(-6, 7, 2):
        c.poly([(320, 20), (320 + k * 50 - 25, 160), (320 + k * 50 + 25, 160)], CREAM, lw=0)
    c.poly([(20, 160), (320, 20), (620, 160)], None, lw=6)
    c.rrect(10, 156, 630, 190, 6, GOLD, lw=5, sh=(0.3, 0.3))
    for k in range(16):
        x = 30 + k * 38.6
        c.ell(x + 19, 190, 19, 16, RED if k % 2 else CREAM, lw=4)
    for k in range(17):
        bulb(c, 30 + k * 36.25, 173, 4, 140)
    c.line([(320, 20), (320, 0)], INK, 5)
    c.ell(320, 6, 10, 10, GOLD, lw=4)
    save(c, "task_eject_pk_carousel_top.png")
    c = C(170, 300)                                                     # Mittelsaeule mit Spiegeln
    c.rrect(15, 0, 155, 300, 10, (110, 60, 90, 255), lw=6, shx=(0.2, 0.3))
    for y in range(20, 290, 60):
        c.rrect(35, y, 135, y + 44, 8, (170, 190, 214, 255), lw=4, sh=(0.3, 0.3))
        c.glint(60, y + 12, 18, 5, 140, rot=-20)
    c.rrect(5, 0, 165, 18, 4, GOLD, lw=4)
    c.rrect(5, 282, 165, 300, 4, GOLD, lw=4)
    save(c, "task_eject_pk_carousel_core.png")
    c = C(660, 110)                                                     # Plattform (Vorderkante)
    c.ell(330, 40, 320, 38, (120, 70, 60, 255), lw=6, sh=(0.1, 0.2))
    c.poly([(10, 40), (650, 40), (650, 80), (10, 80)], RED_D, lw=0)
    c.ell(330, 80, 320, 26, RED_D, lw=6)
    c.poly([(12, 40), (648, 40), (648, 80), (12, 80)], RED_D, lw=0)
    c.line([(10, 40), (10, 80)], INK, 6)
    c.line([(650, 40), (650, 80)], INK, 6)
    for k in range(12):
        bulb(c, 40 + k * 53, 62, 4, 120)
    c.ell(330, 40, 320, 38, None, lw=6)
    save(c, "task_eject_pk_carousel_base.png")
    c = C(200, 360)                                                     # Pferd (nach rechts) mit Messingstange, Pferderuecken bei y ~ 250
    c.rrect(94, 0, 106, 360, 5, GOLD, lw=4, shx=(0.3, 0.3))
    for y in (40, 120, 200, 300):
        c.line([(94, y), (106, y + 12)], GOLD_D, 3)
    horse = [(40, 250), (60, 226), (120, 222), (140, 196), (160, 170), (178, 176), (186, 200), (170, 214),
             (158, 232), (150, 262), (160, 300), (148, 306), (134, 270), (70, 276), (50, 310), (36, 306), (44, 270)]
    c.poly(horse, (246, 242, 234, 255), lw=6, sh=(0.1, 0.25))
    c.poly([(150, 174), (140, 162), (152, 160)], (246, 242, 234, 255), lw=4)            # Ohr
    c.poly([(126, 196), (144, 176), (152, 194), (134, 222)], (220, 90, 110, 255), lw=4)  # Maehne
    c.ell(168, 186, 3.5, 3.5, INK, lw=0)
    c.poly([(40, 250), (18, 258), (24, 290), (44, 270)], (220, 90, 110, 255), lw=4)      # Schweif
    c.rrect(80, 226, 124, 246, 6, TEAL, lw=4)                                            # Sattel
    c.line([(88, 246), (86, 272)], GOLD, 4)
    save(c, "task_eject_pk_horse.png")


def popcorn():
    c = C(640, 180)                                                     # Theke vorne
    c.rrect(10, 30, 630, 180, 8, RED, lw=6, sh=(0.1, 0.3))
    for x in range(30, 620, 60):
        c.d.rectangle([x * S, 40 * S, (x + 30) * S, 176 * S], fill=CREAM)
    c.rrect(10, 30, 630, 180, 8, None, lw=6)
    c.rrect(0, 10, 640, 40, 6, (110, 70, 46, 255), lw=6, sh=(0.3, 0.3))
    save(c, "task_eject_pk_counter.png")
    c = C(220, 270)                                                     # Popcornmaschine: Glaskasten (Fenster x 30..190, y 60..220 frei)
    c.rrect(10, 40, 210, 240, 8, (0, 0, 0, 0), lw=7)
    c.rrect(10, 0, 210, 48, 10, RED, lw=6, sh=(0.25, 0.3))
    label(c, 110, 25, "POPCORN", 22, CREAM)
    c.rrect(10, 232, 210, 270, 6, RED_D, lw=6)
    c.rrect(22, 60, 30, 220, 3, (255, 255, 255, 60), lw=0)
    c.rrect(26, 184, 194, 228, 4, (250, 230, 160, 255), lw=0)           # Popcornhaufen
    rnd = random.Random(7)
    for _ in range(60):
        x, y = rnd.uniform(34, 186), rnd.uniform(178, 222)
        c.ell(x, y, 7, 6, (252, 244, 214, 255), lw=2, outline=(200, 170, 110, 255))
    c.rrect(90, 64, 130, 84, 6, (150, 156, 168, 255), lw=4)               # Kessel
    c.line([(110, 48), (110, 64)], (100, 104, 112, 255), 4)
    c.rrect(10, 40, 210, 240, 8, None, lw=7)
    save(c, "task_eject_pk_popper.png")
    c = C(28, 24)                                                       # Popcorn-Flocke
    for x, y in ((10, 12), (17, 9), (15, 16), (9, 7)):
        c.ell(x, y, 6, 5, (252, 244, 214, 255), lw=2, outline=(190, 160, 100, 255))
    save(c, "task_eject_pk_kernel.png")
    c = C(170, 250)                                                     # Pappclown: Koerper mit Stuetze
    c.poly([(40, 250), (60, 110), (110, 110), (130, 250)], (90, 110, 200, 255), lw=6, sh=(0.1, 0.3))
    for y in (140, 180, 220):
        c.ell(85, y, 8, 8, GOLD, lw=3)
    c.poly([(60, 110), (85, 130), (110, 110), (85, 100)], RED, lw=4)                   # Kragen
    c.poly([(60, 120), (20, 170), (34, 180), (66, 140)], (90, 110, 200, 255), lw=5)
    c.ell(24, 176, 12, 12, CREAM, lw=4)
    c.poly([(110, 120), (150, 90), (160, 102), (116, 140)], (90, 110, 200, 255), lw=5)   # winkt
    c.ell(156, 94, 12, 12, CREAM, lw=4)
    save(c, "task_eject_pk_clown_body.png")
    c = C(130, 140)                                                     # Kopf (Pivot unten Mitte)
    for dx in (-1, 1):
        for k in range(3):
            c.ell(65 + dx * (46 + k * 3), 70 + k * 16, 13, 12, (240, 110, 40, 255), lw=4)
    c.ell(65, 80, 44, 50, (250, 244, 234, 255), lw=6, sh=(0.06, 0.2))
    c.poly([(36, 42), (65, 0), (94, 42)], PLUM, lw=5, sh=(0.2, 0.3))
    c.ell(65, 4, 7, 7, GOLD, lw=3)
    c.arc([36, 80, 94, 118], 20, 160, (200, 40, 50, 255), 6)
    c.ell(65, 86, 10, 10, (220, 40, 40, 255), lw=4)
    for x in (48, 82):
        c.ell(x, 66, 11, 12, (255, 255, 255, 255), lw=4)
    save(c, "task_eject_pk_clown_head.png")
    c = C(60, 20)                                                       # Pupillen (bewegen sich)
    for x in (13, 47):
        c.ell(x, 10, 6, 7, INK, lw=0)
    save(c, "task_eject_pk_clown_eyes.png")


# ================================================================== Riesenrad

def ferris():
    c = C(BW, BH)
    grad(c, (10, 10, 36), (60, 38, 84), 0, BH)
    stars(c, 120, 520, seed=71)
    moon(c, 1040, 110, 40)
    rnd = random.Random(72)
    for _ in range(80):                                                 # Parklichter tief unten (Bokeh)
        x, y = rnd.uniform(0, BW), rnd.uniform(600, BH)
        col = rnd.choice(((255, 200, 120), (255, 150, 140), (150, 220, 210)))
        c.glow(x, y, 12, 12, col + (90,), 6)
    hx, hy = P(*FERRIS_HUB)
    R = FERRIS_R * 100
    col, col_l = (96, 70, 130, 255), (140, 110, 170, 255)
    for k in range(24):                                                 # Speichen
        a = math.radians(90 + k * 15)
        c.line([(hx, hy), (hx + math.cos(a) * R, hy - math.sin(a) * R)], col, 6)
    for rr, w in ((R, 16), (R - 40, 8)):
        c.ell(hx, hy, rr, rr, None, lw=w, outline=col)
    c.ell(hx, hy, R, R, None, lw=4, outline=col_l)
    for k in range(48):                                                 # Lichter am Kranz
        a = math.radians(k * 7.5)
        x, y = hx + math.cos(a) * R, hy - math.sin(a) * R
        if y < BH + 20:
            c.glow(x, y, 10, 10, (255, 214, 130, 150), 5)
            c.ell(x, y, 4, 4, BULB, lw=0)
    for deg in (30, -30, 60, -60):                                      # die anderen Gondeln (gemalt)
        a = math.radians(90 - deg)
        px_, py_ = hx + math.cos(a) * R, hy - math.sin(a) * R
        gondola(c, px_, py_, 1.0, painted=True)
    c.ell(hx + math.cos(math.radians(90)) * R, hy - R, 10, 10, (70, 74, 84, 255), lw=4)   # Aufhaengebolzen oben
    c.vignette(0.4)
    save_bg(c, "task_eject_pk_ferris_bg.jpg")
    # oberste Gondel als eigene Teile: Aufhaengung oben bei (60, 0) = Pivot (0,5 / 1,0)
    g = C(120, 110)
    gondola(g, 60, 0, 1.0, part="back")
    save(g, "task_eject_pk_gondola_back.png")
    g = C(120, 110)
    gondola(g, 60, 0, 1.0, part="front")
    save(g, "task_eject_pk_gondola_front.png")


def gondola(c, x, y, s, painted=False, part=None):
    """Gondel, aufgehaengt bei (x, y): Buegel, Dach, Korb. part: back (Buegel, Dach, Rueckwand), front (Korbwand)."""
    body = (RED, TEAL, GOLD)[int(x) % 3] if painted else RED
    if part in (None, "back"):
        c.line([(x, y), (x, y + 30 * s)], (70, 74, 84, 255), 6 * s)
        c.poly([(x - 50 * s, y + 42 * s), (x, y + 24 * s), (x + 50 * s, y + 42 * s)], CREAM, lw=int(5 * s))
        c.rrect(x - 44 * s, y + 42 * s, x + 44 * s, y + 96 * s, 10 * s, dark(body, 0.6), lw=int(5 * s))
    if part in (None, "front"):
        c.rrect(x - 48 * s, y + 66 * s, x + 48 * s, y + 104 * s, 10 * s, body, lw=int(5 * s), sh=(0.2, 0.3))
        c.line([(x - 40 * s, y + 76 * s), (x + 40 * s, y + 76 * s)], light(body, 0.35), 3 * s)
        for k in (-1, 0, 1):
            c.ell(x + k * 28 * s, y + 90 * s, 4 * s, 4 * s, BULB, lw=0)


# ================================================================== Wildwasserbahn

def flume():
    c = C(BW, BH)
    grad(c, (12, 14, 40), (54, 50, 90), 0, 460)
    stars(c, 70, 260, seed=81)
    moon(c, 220, 110, 34)
    ferris_silhouette(c, 1060, 330, 120, (46, 40, 72, 255), lights=True, n=14)
    big_top(c, 480, 470, 360, 230, RED, CREAM, dim=0.4)
    rnd = random.Random(82)
    for x in range(-40, BW, 60):                                        # Baumkante dunkel
        h = rnd.uniform(40, 80)
        c.ell(x, 480 - h * 0.3, 50, h * 0.6, (24, 30, 40, 255), lw=0)
    rect(c, 0, 480, BW, BH, (22, 26, 36, 255))
    wl, ex = uy(FLUME_Y), ux(FLUME_EDGE)
    py = uy(POOL_Y)
    # Stuetzgeruest der Rinne
    for x in range(20, int(ex), 70):
        c.line([(x, wl + 30), (x, BH)], (80, 60, 44, 255), 8)
        c.line([(x, wl + 60), (x + 70, BH)], (70, 52, 38, 255), 4)
    # Rinne: Holzkasten, Wasser oben
    c.poly([(-10, wl - 10), (ex, wl - 10), (ex, wl + 34), (-10, wl + 34)], (140, 96, 60, 255), lw=6, sh=(0.2, 0.3))
    c.grain(0, wl - 10, ex, wl + 34, 0.1, seed=83)
    c.poly([(-10, wl - 10), (ex, wl - 10), (ex, wl - 2), (-10, wl - 2)], (96, 170, 210, 255), lw=0)
    # Abfahrt: gebogene Rutsche bis zum Becken
    pts_top, pts_bot = [], []
    for i in range(21):
        t = i / 20
        x = ex + (ux(3.3) - ex) * t
        y = wl + (py - wl) * (0.5 - 0.5 * math.cos(math.pi * t))
        pts_top.append((x, y - 10))
        pts_bot.append((x + 14, y + 34))
    c.poly(pts_top + pts_bot[::-1], (140, 96, 60, 255), lw=6, sh=(0.15, 0.3))
    c.line(pts_top, (120, 190, 226, 255), 7)
    for x, y in pts_bot[2::4]:
        c.line([(x, y), (x, BH)], (80, 60, 44, 255), 7)
    # Becken rechts
    c.poly([(ux(2.6), py), (BW + 10, py), (BW + 10, BH), (ux(2.6), BH)], (34, 90, 130, 255), lw=0)
    for k in range(8):
        y = py + 14 + k * 16
        c.line([(ux(2.8) + (k % 2) * 30, y), (BW, y)], (70, 140, 180, 160), 3)
    # Torbogen mit Schild
    ax = ux(-2.4)
    for x in (ax - 90, ax + 90):
        c.rrect(x - 10, wl - 180, x + 10, wl - 8, 4, (110, 76, 50, 255), lw=5)
    c.rrect(ax - 120, wl - 220, ax + 120, wl - 170, 10, RED, lw=6, sh=(0.2, 0.3))
    label(c, ax, wl - 195, "LOG FLUME", 26, CREAM)
    for k in range(9):
        bulb(c, ax - 110 + k * 27.5, wl - 170, 4, 150)
    c.vignette(0.45)
    save_bg(c, "task_eject_pk_flume_bg.jpg")
    b = C(200, 80)                                                      # Baumstammboot (Spieler sitzt dahinter)
    b.rrect(6, 16, 194, 74, 28, (150, 100, 58, 255), lw=6, sh=(0.2, 0.35))
    b.grain(10, 18, 190, 72, 0.12, seed=84)
    b.ell(186, 45, 12, 26, (196, 150, 96, 255), lw=5)
    b.ell(186, 45, 6, 14, (170, 122, 72, 255), lw=0)
    for x in (50, 120):
        b.line([(x, 20), (x - 6, 70)], (110, 70, 40, 255), 3)
    save(b, "task_eject_pk_log.png")
    f = C(560, 130)                                                     # Wasser vor dem Becken (verdeckt das Boot unten)
    for i, (y, colr) in enumerate(((20, (40, 100, 140, 235)), (50, (34, 90, 130, 255)))):
        pts = [(0, 130)] + [(x, y + 7 * math.sin(x / 22 + i)) for x in range(0, 561, 8)] + [(560, 130)]
        f.poly(pts, colr, lw=0)
    for x in range(10, 560, 60):
        f.line([(x, 26 + 7 * math.sin(x / 22)), (x + 26, 24 + 7 * math.sin((x + 26) / 22))], (170, 214, 236, 255), 3)
    save(f, "task_eject_pk_pool_fg.png")


# ================================================================== Geisterbahn

def ghost():
    c = C(BW, BH)
    grad(c, (22, 14, 36), (40, 24, 56), 0, BH)
    for i, x in enumerate(range(0, BW, 70)):                            # Bretterwand
        c.d.rectangle([x * S, 0, (x + 68) * S, uy(TRACK_Y) * S], fill=(46, 28, 60, 255) if i % 2 else (40, 24, 54, 255))
        c.line([(x + 68, 0), (x + 68, uy(TRACK_Y))], (24, 14, 32, 255), 3)
    c.mottle(0.08, 14, seed=91)
    rnd = random.Random(92)
    for _ in range(9):                                                  # gemalte Fledermaeuse
        x, y = rnd.uniform(60, 700), rnd.uniform(160, 380)
        s = rnd.uniform(0.7, 1.2)
        c.poly([(x, y), (x - 30 * s, y - 14 * s), (x - 22 * s, y + 2 * s), (x - 36 * s, y + 4 * s), (x - 12 * s, y + 10 * s),
                (x, y + 16 * s), (x + 12 * s, y + 10 * s), (x + 36 * s, y + 4 * s), (x + 22 * s, y + 2 * s), (x + 30 * s, y - 14 * s)],
               (20, 12, 26, 255), lw=0)
    c.rrect(60, 40, 560, 140, 14, (20, 40, 26, 255), lw=6)              # Schild
    label(c, 310, 90, "GHOST TRAIN", 52, (140, 230, 120, 255))
    for x in (120, 200, 310, 420, 500):
        c.line([(x, 112), (x + 2, 132 + (x % 30))], (120, 210, 100, 255), 5)   # Tropfen
    c.glow(310, 90, 260, 60, (120, 230, 120, 40), 20)
    # Maul (unterer Kiefer + Rachen); der Oberkiefer ist ein eigenes Sprite
    mx = ux(MAW_X)
    ty = uy(TRACK_Y)
    c.poly([(mx - 30, ty - 250), (BW + 20, ty - 300), (BW + 20, BH), (mx - 60, BH)], (70, 110, 70, 255), lw=8, sh=(0.1, 0.3))
    c.poly([(mx + 10, ty - 230), (BW + 20, ty - 270), (BW + 20, ty + 10), (mx + 10, ty + 10)], (10, 6, 12, 255), lw=6)   # Rachen
    c.glow(mx + 200, ty - 80, 200, 110, (120, 20, 30, 60), 30)
    rect(c, 0, ty, BW, BH, (26, 18, 30, 255))                            # Boden
    for x in range(0, BW, 40):                                          # Schwellen + Schienen
        c.rrect(x, ty + 10, x + 26, ty + 22, 2, (60, 44, 40, 255), lw=0)
    c.line([(0, ty + 6), (BW, ty + 6)], (150, 150, 160, 255), 5)
    c.line([(0, ty + 20), (BW, ty + 20)], (120, 120, 130, 255), 4)
    c.vignette(0.5)
    save_bg(c, "task_eject_pk_ghost_bg.jpg")
    # Unterlippe mit Zaehnen (vor dem Wagen), linke Oberkante = Maulrand
    l = C(460, 140)
    l.poly([(10, 40), (460, 20), (460, 140), (30, 140)], (84, 128, 80, 255), lw=7, sh=(0.15, 0.3))
    for k in range(8):
        x = 30 + k * 52
        l.poly([(x, 42 - k * 2.4), (x + 20, 6 - k * 2.4), (x + 40, 38 - k * 2.4)], (236, 230, 200, 255), lw=4)
    save(l, "task_eject_pk_maw_jaw.png")
    # Oberkiefer: Stirn, Augen, Hoerner, Zaehne unten; Scharnier rechts (Pivot 0,92 / 0,35)
    u = C(500, 330)
    u.poly([(10, 210), (60, 90), (200, 30), (420, 20), (500, 60), (500, 300), (30, 260)], (84, 128, 80, 255), lw=8, sh=(0.2, 0.35))
    u.poly([(120, 60), (100, -10), (160, 44)], (220, 210, 170, 255), lw=5)       # Horn
    u.poly([(330, 30), (340, -20), (380, 30)], (220, 210, 170, 255), lw=5)
    for ex_, ey in ((150, 130), (300, 110)):                            # Augen
        u.ell(ex_, ey, 44, 36, (250, 240, 200, 255), lw=6)
        u.ell(ex_ + 6, ey + 4, 16, 22, INK, lw=0)
    u.poly([(90, 90), (200, 70), (210, 90), (100, 110)], (50, 80, 50, 255), lw=4)   # Brauen
    u.poly([(240, 64), (360, 60), (350, 80), (240, 84)], (50, 80, 50, 255), lw=4)
    for k in range(8):
        x = 40 + k * 56
        u.poly([(x, 250 - k * 3), (x + 22, 310 - k * 3), (x + 44, 252 - k * 3)], (236, 230, 200, 255), lw=4)
    u.ell(60, 200, 14, 10, (40, 60, 40, 255), lw=0)                     # Nasenloch
    save(u, "task_eject_pk_maw_top.png")
    g = C(160, 110)                                                     # Geisterbahnwagen (Spieler dahinter)
    g.rrect(10, 40, 150, 96, 14, (60, 40, 90, 255), lw=6, sh=(0.2, 0.35))
    g.ell(128, 48, 30, 28, (236, 230, 210, 255), lw=5)                   # Totenkopf vorne
    for x in (118, 138):
        g.ell(x, 44, 7, 8, INK, lw=0)
    g.poly([(124, 60), (132, 60), (128, 66)], INK, lw=0)
    for x in (40, 110):
        g.ell(x, 98, 12, 12, (40, 40, 46, 255), lw=4)
    save(g, "task_eject_pk_ghostcar.png")
    b = C(80, 40)                                                       # Fledermaus (Partikel)
    b.poly([(40, 18), (8, 4), (16, 20), (2, 24), (24, 28), (40, 36), (56, 28), (78, 24), (64, 20), (72, 4)], (20, 12, 26, 255), lw=0)
    save(b, "task_eject_pk_bat.png")


# ================================================================== Looping

def loop():
    c = C(BW, BH)
    grad(c, (12, 12, 38), (70, 44, 92), 0, 560)
    stars(c, 110, 380, seed=101)
    moon(c, 1060, 100, 36)
    big_top(c, 170, 560, 300, 200, RED, CREAM, dim=0.4)
    ferris_silhouette(c, 1020, 360, 130, (46, 40, 72, 255), n=14)
    cx, cy = P(*LOOP_C)
    R = LOOP_R * 100
    by = uy(LOOP_BASE)
    frame = (74, 60, 100, 255)
    for x in range(int(cx - R - 40), int(cx + R + 60), 50):               # Gittergeruest
        c.line([(x, by + 8), (x, BH)], frame, 5)
    for k in range(10):
        a = math.radians(200 + k * 14)
        x, y = cx + math.cos(a) * R, cy - math.sin(a) * R
        c.line([(x, y), (x, by)], frame, 4)
    rect(c, 0, 560, BW, BH, (22, 18, 34, 255))
    c.line([(0, 560), (BW, 560)], (40, 30, 52, 255), 4)
    # Schiene: Kreis + Ein-/Ausfahrt unten
    rail, rail_l = (200, 60, 70, 255), (240, 120, 120, 255)
    c.line([(-10, by), (BW + 10, by)], rail, 12)
    c.line([(-10, by - 4), (BW + 10, by - 4)], rail_l, 3)
    c.ell(cx, cy, R, R, None, lw=12, outline=rail)
    c.ell(cx, cy, R - 4, R - 4, None, lw=3, outline=rail_l)
    for k in range(36):
        a = math.radians(k * 10)
        c.ell(cx + math.cos(a) * (R + 12), cy - math.sin(a) * (R + 12), 3, 3, BULB, lw=0)
    for x in range(0, BW, 30):
        c.line([(x, by + 6), (x + 14, by + 16)], (60, 44, 70, 255), 3)
    c.vignette(0.45)
    save_bg(c, "task_eject_pk_loop_bg.jpg")
    w = C(150, 80)                                                      # Achterbahnwagen (nach rechts), Spieler dahinter
    w.poly([(8, 30), (120, 30), (146, 50), (140, 70), (8, 70)], RED, lw=6, sh=(0.2, 0.35))
    w.line([(14, 40), (124, 40)], GOLD, 4)
    w.ell(128, 56, 8, 8, BULB, lw=3)
    for x in (30, 110):
        w.ell(x, 72, 8, 8, (50, 50, 56, 255), lw=3)
    save(w, "task_eject_pk_coaster.png")


if __name__ == "__main__":
    fair(); cannon(); carousel(); popcorn()
    ferris(); flume(); ghost(); loop()
