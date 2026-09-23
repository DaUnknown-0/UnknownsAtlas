"""Unknown's Atlas - Grafiken der Rauswurf-Szenen (v3, 180 px pro Einheit).

Gezeichnet wird in einem Raster von 100 px pro Szenen-Einheit (Ursprung Bildmitte bei Hintergruenden,
y nach oben in der Szene), mit 3x Supersampling; exportiert wird mit K = 1,8, also 180 px pro Einheit.
Die Szenen selbst (Zeitleisten, Partikel, Kamera) stehen in assets/eject_scenes.json und werden vom
Spiel (AtlasEject.cs) und vom Vorschau-Kino (tools/eject_theater) gleich abgespielt.

Hintergruende: deckend, JPG (q90, volle Farbaufloesung), 12 x 6,8 Einheiten (Rand fuer Kamerafahrten),
das Tal 12 x 10 fuer die Fahrt nach unten. Alles andere PNG mit Alpha.

    python tools/gen_eject.py
"""

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_tasks import C, S, INK, OUT, mix, dark, light, label  # noqa: E402

K = 1.8                                   # Export: 180 px pro Einheit
BW, BH = 1200, 680                        # Standard-Hintergrund 12 x 6,8
BONE, BONE_D, BONE_L = (232, 222, 196, 255), (190, 176, 146, 255), (246, 240, 224, 255)
HOLE = (46, 38, 34, 255)


def ux(x, w=BW):
    return w / 2 + x * 100


def uy(y, h=BH):
    return h / 2 - y * 100


def save(c, name):
    img = c.img.resize((round(c.w * K), round(c.h * K)), Image.LANCZOS)
    img.save(OUT / name, optimize=True)
    print(name, img.size)


def save_bg(c, name):
    img = c.img.resize((round(c.w * K), round(c.h * K)), Image.LANCZOS).convert("RGB")
    img.save(OUT / name, "JPEG", quality=90, optimize=True, progressive=True, subsampling=0)
    print(name, img.size)


def grad(c, top, bottom, y0=0, y1=None):
    y1 = c.h if y1 is None else y1
    h, w = c.img.height, c.img.width
    t = np.clip((np.arange(h)[:, None] / S - y0) / max(1, y1 - y0), 0, 1)
    top, bottom = np.array(top[:3], np.float32), np.array(bottom[:3], np.float32)
    rgb = top[None, None, :] * (1 - t[..., None]) + bottom[None, None, :] * t[..., None]
    arr = np.asarray(c.img).astype(np.float32)
    band = np.zeros((h, 1), np.float32)
    band[int(y0 * S):int(y1 * S)] = 1
    arr[..., :3] = arr[..., :3] * (1 - band[..., None]) + np.repeat(rgb, w, axis=1) * band[..., None]
    arr[..., 3] = np.maximum(arr[..., 3], 255 * band)
    c.img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
    c.d = ImageDraw.Draw(c.img)


def rect(c, x0, y0, x1, y1, col):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=col)


def stars(c, n, y1, seed=4, x1=None):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y, r = rnd.uniform(0, x1 or c.w), rnd.uniform(0, y1), rnd.choice((0.8, 1, 1, 1.4, 2))
        a = rnd.randint(110, 240)
        c.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(230, 236, 255, a))
        if r >= 2:
            c.glow(x, y, 6, 6, (200, 215, 255, 70), 3)


def moon(c, x, y, r):
    c.glow(x, y, r * 4, r * 4, (160, 185, 255, 45), r * 1.6)
    c.glow(x, y, r * 1.8, r * 1.8, (220, 230, 255, 70), r * 0.6)
    c.ell(x, y, r, r, (238, 240, 226, 255), lw=0)
    for dx, dy, rr in ((0.3, -0.2, 0.22), (-0.35, 0.3, 0.15), (0.1, 0.45, 0.1), (-0.3, -0.35, 0.09)):
        c.ell(x + r * dx, y + r * dy, r * rr, r * rr, (214, 214, 198, 255), lw=0)


def tree_line(c, y, col, seed, h0=60, h1=140, step=(22, 44), x0=-20, x1=None):
    rnd = random.Random(seed)
    x = x0
    x1 = c.w + 40 if x1 is None else x1
    while x < x1:
        h = rnd.uniform(h0, h1)
        wd = h * rnd.uniform(0.32, 0.42)
        for k in range(5):
            yy = y - h * (k + 1) / 5.2
            ww = wd * (1 - k / 5.4)
            c.d.polygon(c.P([(x - ww, yy + h * 0.1), (x - ww * 0.3, yy - h * 0.02), (x, yy - h * 0.18),
                             (x + ww * 0.3, yy - h * 0.02), (x + ww, yy + h * 0.1)]), fill=col)
        rect(c, x - 3, y - h * 0.12, x + 3, y + 4, col)
        x += rnd.uniform(*step)
    rect(c, 0, y, c.w, c.h, col)


def leaf(c, x, y, length, width, ang, col):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    up, lo = [], []
    for i in range(9):
        u = i / 8
        w = math.sin(math.pi * u) ** 0.8 * width / 2
        up.append((u * length, -w))
        lo.append((u * length, w))
    pts = up + lo[::-1]
    c.d.polygon(c.P([(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]), fill=col)


def radial(size, stops, name, squash=1.0):
    """Radialer Verlauf als Alpha (weiss), stops = [(r 0..1, alpha 0..1), ...]; fuer Glows/Vignette."""
    n = size * S
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.sqrt(((xx - n / 2) / (n / 2)) ** 2 + ((yy - n / 2) / (n / 2 * squash)) ** 2)
    rs, as_ = zip(*stops)
    a = np.interp(r, rs, as_)
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(img, "RGBA").resize((round(size * K), round(size * K)), Image.LANCZOS)
    im.save(OUT / name, optimize=True)
    print(name, im.size)


# ================================================================== Partikel, Licht, Allgemeines

def common():
    radial(128, [(0, 1), (0.35, 0.55), (1, 0)], "task_eject_glow.png")
    radial(24, [(0, 1), (0.5, 0.6), (1, 0)], "task_eject_mote.png")
    # Vignette (Bildschirm): Mitte frei, Raender dunkel
    n = 220
    yy, xx = np.mgrid[0:n * S, 0:n * S].astype(np.float32)
    r = np.sqrt(((xx - n * S / 2) / (n * S / 2)) ** 2 + ((yy - n * S / 2) / (n * S / 2)) ** 2) / math.sqrt(2)
    a = np.clip((r - 0.45) / 0.55, 0, 1) ** 1.6 * 0.85
    img = np.zeros((n * S, n * S, 4), np.uint8)
    img[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").resize((round(n * K), round(n * K)), Image.LANCZOS).save(OUT / "task_eject_vignette.png", optimize=True)

    # Staubwolke: unregelmaessiger, weicher Ballen (besser als ein Kreis)
    c = C(120, 120)
    rnd = random.Random(5)
    for _ in range(14):
        x, y, r = rnd.uniform(35, 85), rnd.uniform(38, 82), rnd.uniform(16, 30)
        c.ell(x, y, r, r * 0.85, (255, 255, 255, 120), lw=0)
    c.img = c.img.filter(ImageFilter.GaussianBlur(6 * S))
    c.d = ImageDraw.Draw(c.img)
    save(c, "task_eject_puff.png")

    # Nebelschwade: lang, weich, ausgefranst
    c = C(400, 120)
    rnd = random.Random(6)
    for _ in range(26):
        x, y = rnd.uniform(40, 360), rnd.uniform(45, 75)
        c.ell(x, y, rnd.uniform(30, 70), rnd.uniform(14, 28), (255, 255, 255, 70), lw=0)
    c.img = c.img.filter(ImageFilter.GaussianBlur(10 * S))
    c.d = ImageDraw.Draw(c.img)
    save(c, "task_eject_mist.png")

    # Streifen (Regen, Wasserlauf, Sog): zur Spitze hin heller
    c = C(8, 70)
    for i in range(70):
        a = int(40 + 200 * (i / 69) ** 1.5)
        c.d.rectangle([2 * S, i * S, 6 * S, (i + 1) * S], fill=(255, 255, 255, a))
    save(c, "task_eject_streak.png")

    c = C(24, 30)                                                                                # Wassertropfen
    c.d.polygon(c.P([(12, 2), (19, 16), (12, 28), (5, 16)]), fill=(255, 255, 255, 230))
    c.ell(12, 19, 7, 8, (255, 255, 255, 230), lw=0)
    c.glint(9, 16, 2, 3, 200)
    save(c, "task_eject_droplet.png")

    c = C(120, 50)                                                                               # Ring (Pfuetze)
    c.d.ellipse([6 * S, 6 * S, 114 * S, 44 * S], outline=(255, 255, 255, 220), width=4 * S)
    save(c, "task_eject_ripple.png")

    c = C(40, 20)                                                                                # Blatt
    leaf(c, 3, 10, 34, 13, 0, (255, 255, 255, 255))
    c.line([(4, 10), (34, 10)], (200, 200, 200, 255), 1.5)
    save(c, "task_eject_leaf.png")

    c = C(40, 12)                                                                                # Holzsplitter
    c.poly([(2, 6), (14, 2), (38, 5), (16, 10)], (190, 140, 88, 255), lw=2)
    save(c, "task_eject_splinter.png")

    c = C(28, 24)                                                                                # Gesteinsbrocken
    c.poly([(3, 12), (9, 3), (21, 4), (26, 14), (16, 22), (6, 20)], (120, 112, 104, 255), lw=3, sh=(0.3, 0.4))
    save(c, "task_eject_rock.png")

    c = C(30, 30)                                                                                # Gluehwuermchen
    c.glow(15, 15, 13, 13, (210, 255, 140, 200), 4)
    c.ell(15, 15, 3, 3, (250, 255, 220, 255), lw=0)
    save(c, "task_eject_firefly.png")

    # Lichtkegel (Taschenlampe), Spitze links (Pivot 0 / 0,5)
    n_w, n_h = 360, 180
    yy, xx = np.mgrid[0:n_h * S, 0:n_w * S].astype(np.float32)
    u = xx / (n_w * S)
    half = 0.08 + 0.42 * u
    v = np.abs(yy / (n_h * S) - 0.5)
    edge = np.clip(1 - v / np.maximum(half, 1e-3), 0, 1) ** 0.7
    a = edge * (1 - u) ** 1.1 * 0.8
    img = np.zeros((n_h * S, n_w * S, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").resize((round(n_w * K), round(n_h * K)), Image.LANCZOS).save(OUT / "task_eject_cone.png", optimize=True)

    # Lichtschacht (Mondstrahl): nach unten breiter, oben kraeftiger
    n_w, n_h = 160, 420
    yy, xx = np.mgrid[0:n_h * S, 0:n_w * S].astype(np.float32)
    t = yy / (n_h * S)
    half = 0.18 + 0.32 * t
    v = np.abs(xx / (n_w * S) - 0.5)
    a = np.clip(1 - v / half, 0, 1) ** 1.2 * (1 - t) ** 0.8 * 0.55
    img = np.zeros((n_h * S, n_w * S, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").resize((round(n_w * K), round(n_h * K)), Image.LANCZOS).save(OUT / "task_eject_beam.png", optimize=True)

    c = C(40, 64)                                                                                # Fackelflamme
    c.glow(20, 38, 16, 24, (255, 150, 40, 170), 5)
    c.poly([(20, 4), (30, 30), (32, 46), (20, 60), (8, 46), (10, 30)], (255, 170, 50, 255), lw=0)
    c.poly([(20, 22), (26, 38), (26, 48), (20, 56), (14, 48), (14, 38)], (255, 236, 150, 255), lw=0)
    save(c, "task_eject_flame.png")

    # Taschenlampe (liegt nach rechts), Laterne, Paddel, Eule
    c = C(70, 26)
    c.rrect(4, 7, 46, 19, 5, (60, 64, 72, 255), lw=3, sh=(0.3, 0.3))
    c.poly([(46, 5), (64, 2), (64, 24), (46, 21)], (80, 86, 96, 255), lw=3)
    c.rrect(62, 2, 67, 24, 2, (250, 240, 190, 255), lw=2)
    c.rrect(20, 5, 26, 9, 1, (200, 60, 50, 255), lw=1)
    save(c, "task_eject_flashlight.png")

    c = C(50, 70)
    c.arc([13, 2, 37, 24], 180, 360, (40, 36, 34, 255), 4)
    c.rrect(10, 14, 40, 20, 3, (60, 50, 40, 255), lw=3)
    c.rrect(12, 20, 38, 58, 6, (255, 214, 120, 255), lw=4, outline=(50, 42, 34, 255))
    c.glow(25, 39, 10, 14, (255, 250, 210, 230), 4)
    for x in (12, 38):
        c.line([(x, 20), (x, 58)], (50, 42, 34, 255), 4)
    c.rrect(8, 58, 42, 66, 3, (60, 50, 40, 255), lw=3)
    save(c, "task_eject_lantern.png")

    c = C(170, 30)
    c.line([(6, 15), (120, 15)], (150, 104, 60, 255), 7)
    c.poly([(116, 15), (132, 4), (166, 6), (166, 24), (132, 26)], (170, 118, 66, 255), lw=3, sh=(0.25, 0.3))
    c.rrect(2, 11, 16, 19, 3, (90, 60, 36, 255), lw=2)
    save(c, "task_eject_paddle.png")

    c = C(150, 70)                                                                               # Eule im Flug (Silhouette)
    col = (18, 20, 30, 255)
    c.poly([(75, 30), (40, 12), (6, 22), (30, 34), (60, 40)], col, lw=0)
    c.poly([(75, 30), (110, 12), (144, 22), (120, 34), (90, 40)], col, lw=0)
    c.ell(75, 40, 16, 20, col, lw=0)
    c.ell(75, 26, 12, 11, col, lw=0)
    c.poly([(66, 18), (68, 10), (72, 18)], col, lw=0)
    c.poly([(78, 18), (82, 10), (84, 18)], col, lw=0)
    save(c, "task_eject_owl.png")

    c = C(16, 16)                                                                                # Voll-Quadrat fuer Balken/Blitze
    c.d.rectangle([0, 0, 16 * S, 16 * S], fill=(255, 255, 255, 255))
    save(c, "task_eject_px.png")


# ================================================================== Museum 1: Sarkophag

def tomb():
    c = C(BW, BH)
    grad(c, (52, 42, 34), (22, 17, 15))
    rnd = random.Random(7)
    for row in range(9):                                                                         # Steinquader
        y = row * 50
        off = 0 if row % 2 else 64
        for x in range(-off, BW, 128):
            col = mix((74, 61, 48, 255), (56, 46, 37, 255), rnd.random())
            c.rrect(x + 3, y + 3, x + 125, y + 47, 5, col, lw=3, outline=(30, 24, 20, 255))
            if rnd.random() < 0.25:
                c.line([(x + rnd.uniform(20, 100), y + 6), (x + rnd.uniform(20, 100), y + 40)], (40, 32, 26, 255), 2)
    c.mottle(0.1, cell=7, seed=7)
    # Relief-Tafeln mit Goetterfiguren (Silhouetten, eingelassen)
    for cx in (330, 870):
        c.rrect(cx - 110, 40, cx + 110, 280, 8, (64, 52, 42, 255), lw=5, outline=(36, 28, 22, 255))
        c.rrect(cx - 98, 52, cx + 98, 268, 6, (86, 70, 54, 255), lw=3, outline=(40, 32, 26, 255))
        fig = (58, 46, 36, 255)
        c.ell(cx - 30, 110, 14, 16, fig, lw=0)                                                   # Kopf (Schakal)
        c.poly([(cx - 40, 104), (cx - 64, 110), (cx - 40, 116)], fig, lw=0)
        c.poly([(cx - 26, 96), (cx - 22, 80), (cx - 18, 98)], fig, lw=0)
        c.poly([(cx - 44, 126), (cx - 16, 126), (cx - 10, 200), (cx - 50, 200)], fig, lw=0)
        c.line([(cx - 44, 200), (cx - 48, 250)], fig, 7)
        c.line([(cx - 18, 200), (cx - 12, 250)], fig, 7)
        c.line([(cx - 16, 140), (cx + 30, 150)], fig, 6)
        c.ell(cx + 36, 150, 8, 8, None, lw=3, outline=fig)                                       # Ankh
        c.line([(cx + 36, 158), (cx + 36, 190)], fig, 4)
        c.line([(cx + 26, 166), (cx + 46, 166)], fig, 4)
        for j in range(5):
            c.rrect(cx + 60, 70 + j * 36, cx + 84, 94 + j * 36, 3, None, lw=2, outline=fig)
    rect(c, 0, 300, BW, 342, (128, 98, 54, 255))                                                  # Hieroglyphen-Band
    c.line([(0, 300), (BW, 300)], (92, 70, 38, 255), 3)
    c.line([(0, 342), (BW, 342)], (92, 70, 38, 255), 3)
    for i, x in enumerate(range(16, BW, 44)):
        k, col = i % 5, (62, 42, 22, 255)
        if k == 0:
            c.ell(x + 10, 321, 9, 9, None, lw=3, outline=col)
            c.line([(x + 10, 311), (x + 10, 331)], col, 3)
        elif k == 1:
            c.line([(x, 333), (x + 10, 309), (x + 20, 333)], col, 3)
        elif k == 2:
            c.line([(x, 321), (x + 20, 321)], col, 3)
            c.ell(x + 10, 313, 5, 5, col, lw=0)
        elif k == 3:
            c.line([(x + 4, 309), (x + 4, 333), (x + 18, 333)], col, 3)
        else:
            c.arc([x, 309, x + 20, 333], 200, 340, col, 3)
            c.ell(x + 10, 326, 3, 3, col, lw=0)
    grad(c, (66, 54, 44), (28, 22, 19), 400, BH)                                                  # Boden
    for x in range(-60, BW + 100, 150):
        c.line([(x, 400), (x - 120, BH)], (38, 30, 25, 255), 3)
    for y in (400, 470, 560):
        c.line([(0, y), (BW, y)], (36, 28, 24, 255), 3 if y > 400 else 5)
    for _ in range(9):                                                                           # Sandwehen
        x, y = rnd.uniform(0, BW), rnd.uniform(430, 660)
        c.soft_poly([(x - 80, y + 10), (x, y - 8), (x + 90, y + 12)], (150, 120, 84, 90), 6)
    for x, h in ((300, 70), (336, 58), (870, 64), (910, 76)):                                     # Kanopen
        c.ell(x, 470 - h * 0.45, 16, h * 0.45, (156, 124, 82, 255), lw=4, sh=(0.2, 0.35))
        c.ell(x, 470 - h * 0.95, 12, 11, (176, 144, 94, 255), lw=4)
    c.rrect(80, 440, 190, 470, 4, (90, 72, 52, 255), lw=4)                                        # Opfertisch
    c.ell(110, 438, 14, 6, (200, 170, 90, 255), lw=3)
    c.ell(160, 436, 10, 8, (170, 60, 50, 255), lw=3)
    for x in (200, 1000):                                                                         # Fackelhalter
        c.glow(x, 190, 190, 170, (255, 160, 60, 60), 70)
        c.poly([(x - 14, 204), (x + 14, 204), (x + 8, 222), (x - 8, 222)], (90, 70, 48, 255), lw=3)
        c.rrect(x - 5, 222, x + 5, 280, 2, (80, 62, 42, 255), lw=3)
    c.vignette(0.5)
    save_bg(c, "task_eject_tomb_bg.jpg")

    col = (30, 24, 20, 255)                                                                       # Vordergrund-Saeule
    p = C(170, 760)
    p.rrect(40, 60, 130, 760, 6, col, lw=0)
    p.poly([(10, 60), (160, 60), (140, 10), (30, 10)], col, lw=0)
    for k in range(4):
        p.ell(85, 10 + k * 12, 70 - k * 10, 14, col, lw=0)
    p.glint(60, 300, 6, 200, 18)
    save(p, "task_eject_tomb_pillar.png")

    gold, gold_d, lapis, red = (214, 172, 80, 255), (170, 128, 52, 255), (38, 62, 128, 255), (160, 52, 44, 255)
    s = C(440, 210)
    s.rrect(10, 170, 430, 206, 6, (96, 84, 72, 255), lw=5, sh=(0.2, 0.35))
    s.poly([(26, 40), (414, 40), (400, 172), (40, 172)], gold, lw=6, sh=(0.18, 0.3))
    s.poly([(26, 40), (414, 40), (410, 62), (30, 62)], gold_d, lw=4)
    for y0 in (78, 146):
        s.poly([(34, y0), (406, y0), (404, y0 + 12), (36, y0 + 12)], lapis, lw=3)
    for i in range(8):
        x = 60 + i * 44
        for j in range(3):
            s.ell(x + 10, 102 + j * 13, 9, 5, red if (i + j) % 2 else lapis, lw=2)
    for x in (48, 392):
        s.rrect(x - 12, 70, x + 12, 164, 3, (236, 206, 122, 255), lw=3)
        for j in range(4):
            s.ell(x, 84 + j * 22, 5, 5, None, lw=2, outline=(90, 60, 30, 255))
    s.glint(220, 48, 170, 4, 90)
    save(s, "task_eject_sarc_base.png")

    lid = C(460, 150)
    lid.poly([(20, 70), (40, 34), (100, 22), (330, 32), (420, 44), (446, 66), (440, 108), (400, 120),
              (100, 126), (40, 116)], gold, lw=6, sh=(0.25, 0.35))
    for i, y0 in enumerate(range(30, 124, 12)):
        lid.line([(28, y0 + 4), (118, y0)], lapis if i % 2 else gold_d, 5)
    lid.ell(80, 74, 30, 34, (196, 146, 88, 255), lw=4, sh=(0.2, 0.3))
    lid.ell(70, 66, 5, 3, INK, lw=0)
    lid.ell(90, 66, 5, 3, INK, lw=0)
    lid.line([(62, 60), (76, 60)], INK, 2)
    lid.line([(84, 60), (98, 60)], INK, 2)
    lid.line([(74, 90), (86, 90)], (120, 60, 50, 255), 3)
    lid.rrect(74, 104, 86, 122, 4, (60, 40, 30, 255), lw=2)
    for k, x in enumerate(range(128, 200, 12)):
        lid.line([(x, 30), (x + 4, 122)], (lapis, red, gold_d)[k % 3], 7)
    for x in (246, 300, 354):
        lid.line([(x, 34), (x, 118)], lapis, 6)
        lid.line([(x + 10, 36), (x + 10, 116)], gold_d, 3)
    lid.ell(430, 84, 14, 26, gold_d, lw=4)
    lid.glint(260, 40, 140, 6, 90)
    save(lid, "task_eject_sarc_lid.png")


# ================================================================== Museum 2: Falltuer ins Depot

def depot():
    c = C(BW, BH)
    for yi in range(-20, BH, 80):                                                                # Marmor-Schachbrett
        for xi in range(-20, BW, 80):
            light_tile = ((xi + 20) // 80 + (yi + 20) // 80) % 2 == 0
            col = (228, 218, 196, 255) if light_tile else (172, 156, 132, 255)
            rect(c, xi, yi, xi + 80, yi + 80, col)
            rnd = random.Random(xi * 7 + yi)
            for _ in range(2):                                                                   # Marmoradern
                x0, y0 = xi + rnd.uniform(0, 80), yi + rnd.uniform(0, 80)
                c.line([(x0, y0), (x0 + rnd.uniform(-30, 30), y0 + rnd.uniform(10, 40))], dark(col, 0.9), 1.5)
    c.mottle(0.05, cell=12, seed=3)
    for x in range(-20, BW, 80):
        c.line([(x, 0), (x, BH)], (140, 126, 106, 255), 1.5)
    for y in range(-20, BH, 80):
        c.line([(0, y), (BW, y)], (140, 126, 106, 255), 1.5)
    # Vitrinen von oben (Sockel mit Glas) links und rechts
    for cx, cy in ((150, 140), (1050, 540), (1060, 130)):
        c.ell(cx + 6, cy + 8, 70, 70, (0, 0, 0, 60), lw=0)
        c.ell(cx, cy, 66, 66, (96, 90, 84, 255), lw=5)
        c.ell(cx, cy, 52, 52, (170, 200, 214, 180), lw=3, outline=(80, 96, 106, 255))
        c.glint(cx - 18, cy - 20, 20, 8, 120, rot=35)
    # Absperrung
    posts = ((350, 170), (850, 170), (350, 510), (850, 510))
    for (x0, y0), (x1, y1) in ((posts[0], posts[1]), (posts[2], posts[3]), (posts[0], posts[2]), (posts[1], posts[3])):
        c.line([(x0, y0), (x1, y1)], (60, 10, 20, 90), 11)
        c.line([(x0, y0), (x1, y1)], (160, 34, 44, 255), 7)
    for x, y in posts:
        c.ell(x + 4, y + 5, 20, 20, (0, 0, 0, 70), lw=0)
        c.ell(x, y, 18, 18, (204, 168, 88, 255), lw=4, sh=(0.3, 0.3))
        c.glint(x - 6, y - 6, 6, 4, 150)
    label(c, 600, 590, "STAFF ONLY  -  DEPOT", 18, (120, 40, 36, 255))
    c.rrect(420, 572, 780, 608, 6, None, lw=3, outline=(150, 50, 44, 255))
    # Schacht: Waende laufen in die Tiefe, unten das Depot mit Kisten und Licht
    c.rrect(460, 230, 740, 450, 8, (24, 18, 18, 255), lw=12, outline=(96, 74, 52, 255))
    for (x0, y0), (x1, y1) in (((466, 236), (556, 296)), ((734, 236), (644, 296)), ((466, 444), (556, 384)), ((734, 444), (644, 384))):
        c.line([(x0, y0), (x1, y1)], (44, 36, 32, 255), 3)
    c.rrect(556, 296, 644, 384, 2, (18, 14, 14, 255), lw=2, outline=(34, 28, 26, 255))
    for x, y, w in ((566, 330, 22), (596, 348, 18), (620, 316, 14), (580, 364, 12)):
        c.rrect(x, y, x + w, y + w, 2, (66, 50, 32, 255), lw=1, outline=(20, 16, 14, 255))
    c.glow(600, 340, 30, 30, (255, 220, 150, 50), 12)
    for k in range(6):
        y = 250 + k * 12
        c.line([(488 + k * 12, y), (508 + k * 12, y)], (80, 66, 52, 255), 3)
    c.glow(600, 340, 150, 110, (0, 0, 0, 150), 34)
    c.vignette(0.35)
    save_bg(c, "task_eject_depot_bg.jpg")

    l = C(140, 220)
    l.rrect(4, 4, 136, 216, 6, (154, 108, 62, 255), lw=6, sh=(0.2, 0.3))
    l.grain(4, 4, 136, 216, 0.1, seed=5)
    for y in (40, 110, 180):
        l.line([(14, y), (126, y)], (100, 68, 40, 255), 5)
        l.rivet(20, y, 5)
        l.rivet(120, y, 5)
    l.rrect(60, 96, 80, 124, 4, (70, 70, 76, 255), lw=3)
    save(l, "task_eject_trap_leaf.png")


# ================================================================== Museum 3: T-Rex

def triceratops(c, x0, yb, s, col, ink):
    def P(x, y):
        return (x0 + x * s, yb - y * s)
    c.rrect(x0 - 150 * s, yb, x0 + 190 * s, yb + 26 * s, 4, (70, 66, 74, 255), lw=4, outline=ink)
    for hx, fx in ((-40, -50), (0, 10), (90, 80), (130, 140)):
        c.line([P(hx, 70), P(hx + 6, 36), P(fx, 0)], col, 7 * s)
    c.line([P(-150, 40), P(-100, 62), P(-50, 86), P(20, 100), P(90, 96), P(140, 84)], col, 9 * s)
    for k in range(9):
        x = -30 + k * 17
        c.arc([x0 + (x - 14) * s, yb - 100 * s, x0 + (x + 14) * s, yb - 36 * s], 20, 160, col, 4 * s)
    c.ell(*P(185, 110), 42 * s, 48 * s, None, lw=int(6 * s), outline=col)
    c.line([P(150, 84), P(205, 72), P(236, 60)], col, 12 * s)
    c.line([P(200, 96), P(250, 122)], col, 5 * s)
    c.line([P(214, 90), P(262, 108)], col, 5 * s)
    c.line([P(232, 66), P(250, 80)], col, 4 * s)


def hall():
    c = C(BW, BH)
    grad(c, (30, 34, 56), (15, 17, 29), 0, 460)
    for x in (130, 400, 670, 940):                                                               # Fenster
        c.rrect(x, 50, x + 130, 350, 64, (70, 92, 146, 255), lw=8, outline=(40, 44, 60, 255))
        c.glow(x + 65, 150, 60, 90, (150, 180, 240, 60), 30)
        c.line([(x + 65, 50), (x + 65, 350)], (40, 44, 60, 255), 6)
        c.line([(x, 200), (x + 130, 200)], (40, 44, 60, 255), 6)
    for x in (60, 330, 600, 870, 1140):                                                          # Saeulen
        c.rrect(x - 24, 16, x + 24, 460, 6, (86, 86, 98, 255), lw=5, shx=(0.15, 0.35))
        c.rrect(x - 32, 16, x + 32, 40, 4, (96, 96, 108, 255), lw=4)
    moonbone, ink = (126, 130, 150, 255), (30, 32, 44, 255)
    cx, cy = 760, 130                                                                            # Flugsaurier an Draehten
    c.line([(cx - 70, 0), (cx - 60, cy - 6)], (70, 72, 86, 255), 2)
    c.line([(cx + 70, 0), (cx + 60, cy - 6)], (70, 72, 86, 255), 2)
    c.line([(cx - 130, cy - 10), (cx - 60, cy - 4), (cx, cy + 6), (cx + 60, cy - 4), (cx + 130, cy - 10)], moonbone, 5)
    for d in (-1, 1):
        c.line([(cx + d * 60, cy - 4), (cx + d * 118, cy + 22)], moonbone, 3)
    c.line([(cx, cy + 6), (cx + 26, cy - 8), (cx + 58, cy - 2)], moonbone, 5)
    grad(c, (50, 46, 54), (24, 22, 28), 460, BH)
    c.line([(0, 460), (BW, 460)], (18, 18, 24, 255), 5)
    for x in (130, 400, 670, 940):                                                               # Spiegelung der Fenster
        c.soft_poly([(x + 10, 470), (x + 120, 470), (x + 150, 640), (x - 20, 640)], (120, 150, 210, 30), 16)
    triceratops(c, 290, 444, 0.95, moonbone, ink)
    c.rrect(200, 452, 380, 474, 3, (170, 140, 80, 255), lw=3)
    label(c, 290, 463, "TRICERATOPS", 11, (40, 30, 20, 255))
    c.rrect(520, 362, 800, 404, 6, (120, 40, 40, 255), lw=4)
    label(c, 660, 383, "HALL OF GIANTS", 20, (240, 214, 150, 255))
    c.vignette(0.45)
    save_bg(c, "task_eject_hall_bg.jpg")

    col = (14, 12, 18, 255)                                                                       # Vordergrund: Absperrpfosten
    f = C(1300, 140)
    for x in (80, 520, 1220):
        f.rrect(x - 9, 30, x + 9, 140, 4, col, lw=0)
        f.ell(x, 30, 16, 12, col, lw=0)
    f.arc([80, 20, 520, 120], 20, 160, col, 9)
    save(f, "task_eject_hall_fg.png")

    h = C(600, 300)
    outline = [(28, 150), (52, 122), (120, 100), (210, 74), (300, 50), (380, 40), (452, 50), (520, 76),
               (562, 112), (578, 160), (566, 206), (544, 222), (470, 204), (380, 188), (250, 180), (130, 174), (46, 166)]
    h.poly(outline, BONE, lw=7, sh=(0.2, 0.35))
    h.mottle(0.05, cell=6, seed=21)
    h.poly([(236, 100), (300, 84), (340, 108), (318, 146), (252, 150), (224, 128)], HOLE, lw=5)
    h.poly([(372, 70), (404, 62), (420, 96), (402, 132), (380, 120), (366, 94)], HOLE, lw=5)
    h.poly([(450, 86), (500, 90), (520, 140), (492, 176), (456, 160), (440, 120)], HOLE, lw=5)
    h.ell(66, 132, 14, 9, HOLE, lw=4)
    h.line([(140, 112), (220, 90), (300, 70)], BONE_D, 4)
    h.line([(356, 150), (430, 150), (470, 176)], BONE_D, 4)
    h.glint(300, 58, 120, 6, 110, rot=-8)
    rnd = random.Random(8)
    for i in range(13):
        x = 52 + i * 27
        L = 22 + 16 * math.sin(math.pi * min(1, i / 11))
        h.poly([(x, 172 - i * 0.6), (x + 14, 173 - i * 0.6), (x + 5 + rnd.uniform(-2, 2), 172 + L)], BONE_L, lw=3)
    save(h, "task_eject_trex_head.png")

    j = C(540, 150)
    j.poly([(14, 40), (60, 32), (200, 28), (360, 26), (452, 24), (500, 30), (528, 56), (518, 98), (470, 122),
            (380, 112), (250, 88), (120, 68), (38, 58)], BONE_D, lw=7, sh=(0.18, 0.32))
    j.mottle(0.05, cell=6, seed=22)
    j.ell(416, 70, 34, 14, HOLE, lw=4)
    j.ell(506, 44, 15, 15, BONE, lw=5)
    for i in range(12):
        x = 34 + i * 29
        L = 16 + 12 * math.sin(math.pi * min(1, i / 10))
        j.poly([(x, 33 - i * 0.3), (x + 12, 33 - i * 0.3), (x + 5, 33 - L)], BONE_L, lw=3)
    save(j, "task_eject_trex_jaw.png")

    v = C(120, 110)
    v.rrect(20, 52, 100, 88, 16, BONE_D, lw=5, sh=(0.2, 0.3))
    v.poly([(46, 54), (60, 10), (74, 54)], BONE_D, lw=4)
    v.line([(24, 70), (4, 84)], BONE_D, 8)
    v.line([(96, 70), (116, 84)], BONE_D, 8)
    save(v, "task_eject_trex_vert.png")


# ================================================================== Museum 4: Hinausgeworfen

def night():
    c = C(BW, BH)
    grad(c, (12, 16, 32), (30, 36, 58), 0, 430)
    stars(c, 40, 200, seed=41, x1=BW)
    for x, h in ((560, 150), (660, 220), (760, 170), (860, 250), (980, 190), (1100, 240)):         # ferne Stadt
        rect(c, x, 430 - h, x + 90, 430, (22, 26, 42, 255))
        rnd = random.Random(x)
        for _ in range(10):
            wx, wy = x + rnd.uniform(8, 78), 430 - rnd.uniform(20, h - 10)
            if rnd.random() < 0.5:
                rect(c, wx, wy, wx + 7, wy + 9, (230, 190, 110, 200))
    c.rrect(-20, 70, 470, 480, 0, (60, 58, 66, 255), lw=6)                                        # Fassade
    c.mottle(0.08, cell=10, seed=9)
    for x in (30, 140, 330, 440):
        c.rrect(x - 17, 104, x + 17, 452, 4, (82, 80, 90, 255), lw=4, shx=(0.12, 0.3))
    c.poly([(-20, 70), (225, 16), (470, 70)], (72, 70, 80, 255), lw=6)
    label(c, 225, 56, "VESPER MUSEUM", 17, (206, 196, 166, 255))
    c.glow(265, 350, 170, 170, (255, 190, 90, 70), 56)
    c.rrect(210, 236, 320, 452, 10, (255, 214, 140, 255), lw=8, outline=(34, 30, 34, 255))
    for k in range(3):
        c.rrect(170 - k * 30, 452 + k * 18, 360 + k * 30, 470 + k * 18, 3, (92, 90, 98, 255), lw=4)
    grad(c, (36, 38, 46), (18, 20, 26), 506, BH)                                                  # Pflaster
    rnd = random.Random(12)
    for y in range(510, BH, 26):
        for x in range(-20, BW, 44):
            c.rrect(x + (y // 26 % 2) * 22, y, x + 40 + (y // 26 % 2) * 22, y + 22, 5, None, lw=2, outline=(28, 30, 36, 255))
    rect(c, 470, 430, BW, 506, (28, 30, 38, 255))
    c.line([(1010, 190), (1010, 506)], (30, 30, 36, 255), 10)                                     # Laterne
    c.rrect(988, 150, 1032, 196, 6, (255, 230, 170, 255), lw=5)
    c.poly([(980, 150), (1040, 150), (1010, 130)], (30, 30, 36, 255), lw=0)
    for x, w in ((700, 160), (960, 120), (520, 96)):                                              # Pfuetzen + Spiegelung
        c.ell(x, 590, w, 20, (54, 64, 96, 255), lw=0)
        c.glint(x - w * 0.3, 586, w * 0.4, 4, 60)
    c.soft_poly([(1000, 520), (1020, 520), (1030, 640), (990, 640)], (255, 220, 150, 70), 6)
    c.vignette(0.45)
    save_bg(c, "task_eject_night_bg.jpg")

    g = C(150, 200)                                                                               # Waechter
    g.ell(40, 110, 18, 40, (26, 34, 64, 255), lw=5)                                               # Rucksack
    g.ell(80, 120, 58, 72, (34, 44, 80, 255), lw=6, sh=(0.2, 0.3))
    g.rrect(58, 72, 132, 106, 16, (150, 190, 220, 255), lw=5)
    g.glint(80, 80, 18, 5, 140)
    g.rrect(34, 30, 124, 62, 10, (24, 30, 56, 255), lw=5)
    g.rrect(26, 56, 132, 66, 4, (18, 22, 40, 255), lw=4)
    g.ell(79, 44, 10, 8, (214, 172, 80, 255), lw=3)
    g.rrect(44, 176, 70, 198, 6, (24, 30, 56, 255), lw=4)
    g.rrect(88, 176, 114, 198, 6, (24, 30, 56, 255), lw=4)
    save(g, "task_eject_guard.png")

    d = C(120, 230)
    d.rrect(4, 4, 116, 226, 8, (96, 60, 40, 255), lw=6, sh=(0.2, 0.3))
    d.grain(4, 4, 116, 226, 0.1, seed=11)
    d.rrect(18, 20, 102, 100, 6, (80, 50, 34, 255), lw=4)
    d.rrect(18, 120, 102, 210, 6, (80, 50, 34, 255), lw=4)
    d.ell(96, 118, 6, 6, (214, 172, 80, 255), lw=2)
    save(d, "task_eject_door.png")


# ================================================================== Wald 1: Wildwasser

def river():
    c = C(BW, BH)
    grad(c, (10, 14, 30), (28, 36, 60), 0, 280)
    stars(c, 90, 230, seed=12)
    moon(c, 960, 96, 36)
    tree_line(c, 250, (22, 34, 40, 255), seed=4, h0=60, h1=120, step=(18, 30))
    tree_line(c, 280, (15, 25, 30, 255), seed=5, h0=90, h1=190)
    c.poly([(-10, 320), (960, 308), (980, 490), (-10, 490)], (38, 78, 108, 255), lw=0)            # Fluss
    for k in range(18):
        y = 330 + k * 9
        x0 = random.Random(k).uniform(0, 240)
        c.line([(x0, y), (x0 + 240, y - 2)], (86, 136, 168, 150), 3)
        c.line([(x0 + 420, y + 4), (x0 + 600, y + 2)], (86, 136, 168, 110), 3)
    for x, y in ((230, 380), (560, 440), (760, 350)):
        c.ell(x, y, 30, 13, (54, 60, 66, 255), lw=4, sh=(0.3, 0.3))
    c.poly([(960, 308), (990, 318), (1000, 490), (980, 490)], (150, 190, 212, 255), lw=0)          # Kante
    c.glow(1080, 500, 200, 130, (220, 235, 245, 150), 40)
    rect(c, 980, 490, BW, BH, (18, 24, 30, 255))
    tree_line(c, 530, (12, 18, 20, 255), seed=8, h0=40, h1=90)
    c.poly([(-10, 490), (980, 490), (1000, 530), (-10, 530)], (30, 40, 34, 255), lw=0)
    c.vignette(0.45)
    save_bg(c, "task_eject_river_bg.jpg")

    f = C(1300, 200)                                                                              # Schilf vorne
    rnd = random.Random(14)
    col = (10, 16, 14, 255)
    for x0, x1 in ((0, 260), (1020, 1300)):
        for _ in range(40):
            x = rnd.uniform(x0, x1)
            hgt = rnd.uniform(60, 190)
            f.line([(x, 200), (x + rnd.uniform(-20, 20), 200 - hgt)], col, rnd.uniform(3, 6))
            if rnd.random() < 0.3:
                f.ell(x, 200 - hgt * 0.8, 5, 16, col, lw=0)
    save(f, "task_eject_reeds.png")

    k = C(360, 110)
    k.poly([(10, 30), (350, 30), (320, 80), (260, 100), (100, 100), (40, 80)], (174, 102, 56, 255), lw=6, sh=(0.25, 0.35))
    k.line([(20, 38), (340, 38)], (222, 162, 100, 255), 5)
    for x in (110, 250):
        k.line([(x, 38), (x, 92)], (120, 70, 40, 255), 5)
    k.glint(180, 36, 120, 3, 90)
    save(k, "task_eject_canoe.png")


# ================================================================== Wald 2: In den Wald gezerrt

def forest():
    c = C(BW, BH)
    grad(c, (10, 14, 26), (22, 30, 40), 0, 400)
    stars(c, 40, 170, seed=21)
    c.glow(620, 60, 280, 120, (120, 140, 190, 40), 60)
    tree_line(c, 330, (24, 34, 40, 255), seed=13, h0=150, h1=280, step=(30, 60))
    for x in (420, 700):                                                                           # Mondschaechte
        c.soft_poly([(x - 20, 0), (x + 30, 0), (x + 120, 500), (x - 40, 500)], (150, 170, 210, 26), 18)
    c.soft_poly([(-40, 300), (1240, 290), (1240, 350), (-40, 360)], (120, 140, 150, 46), 18)
    tree_line(c, 440, (12, 18, 20, 255), seed=14, h0=110, h1=220, step=(40, 70))
    grad(c, (30, 40, 30), (14, 20, 16), 480, BH)
    c.soft_poly([(-20, 540), (320, 506), (640, 488), (820, 484), (820, 498), (640, 518), (320, 560), (-20, 610)], (72, 76, 64, 150), 8)
    c.glow(380, 520, 300, 50, (140, 160, 180, 46), 30)
    c.vignette(0.6)
    save_bg(c, "task_eject_forest_bg.jpg")

    f = C(1300, 180)                                                                              # Farne vorne
    rnd = random.Random(16)
    for x0 in (0, 80, 180, 1060, 1160, 1250):
        base = 180
        for i in range(7):
            ang = -150 + i * 20 + rnd.uniform(-8, 8)
            a = math.radians(ang)
            L = rnd.uniform(90, 150)
            for j in range(10):
                u = j / 9
                px, py = x0 + math.cos(a) * u * L, base + math.sin(a) * u * L
                for side in (-1, 1):
                    leaf(f, px, py, 22 * (1 - u * 0.6), 7, ang + side * 62, (8, 16, 10, 255))
    save(f, "task_eject_ferns.png")

    b = C(560, 380)
    rnd = random.Random(3)
    cx, base = 280, 372

    def top(x):
        return base - 300 * max(0.0, math.sin(math.pi * (x - 20) / 520)) ** 0.6 - 20 * math.sin(x / 37)

    b.d.polygon(b.P([(x, top(x)) for x in range(20, 541, 10)] + [(540, base), (20, base)]), fill=(10, 20, 14, 255))
    for layer, (n, col0, col1, size) in enumerate(((260, (12, 26, 16), (22, 44, 26), 26), (220, (20, 42, 24), (34, 66, 38), 24),
                                                    (140, (34, 64, 38), (70, 104, 80), 20))):
        for _ in range(n):
            x = rnd.uniform(30, 530)
            t0 = top(x)
            y = rnd.uniform(t0 + 6, base - 10) if layer < 2 else rnd.uniform(t0 - 6, t0 + 60)
            ang = math.degrees(math.atan2(y - 380, x - cx)) + rnd.uniform(-35, 35)
            col = mix(col0 + (255,), col1 + (255,), rnd.random())
            leaf(b, x, y, size * rnd.uniform(0.8, 1.3), size * 0.42, ang, col)
    for x0, y0, ang in ((40, 250, 200), (520, 230, -20), (150, 110, 250), (420, 100, 290)):
        a = math.radians(ang)
        for i in range(10):
            u = i / 9
            px, py = x0 + math.cos(a) * u * 90, y0 + math.sin(a) * u * 90
            for side in (-1, 1):
                leaf(b, px, py, 22 * (1 - u * 0.6), 7, ang + side * 60, (40, 78, 46, 255))
    save(b, "task_eject_bushes.png")

    e = C(90, 40)
    for x in (22, 68):
        e.glow(x, 20, 18, 12, (255, 40, 30, 160), 6)
        e.ell(x, 20, 9, 6, (255, 70, 50, 255), lw=0)
        e.ell(x, 20, 3, 5, (60, 0, 0, 255), lw=0)
    save(e, "task_eject_eyes.png")


# ================================================================== Wald 3: Vom Hochsitz (hohes Bild: 12 x 10)

VW, VH = 1200, 1000


def valley():
    c = C(VW, VH)
    grad(c, (12, 16, 34), (58, 66, 90), 0, 620)
    stars(c, 140, 520, seed=31)
    moon(c, 860, 200, 44)
    for k, (y, col) in enumerate(((560, (40, 48, 68, 255)), (640, (32, 40, 56, 255)))):         # Bergkaemme
        rnd = random.Random(40 + k)
        pts = [(-10, VH)]
        x = -10
        while x < VW + 20:
            pts.append((x, y + rnd.uniform(-60, 40)))
            x += rnd.uniform(60, 120)
        pts.append((VW + 20, VH))
        c.poly(pts, col, lw=0)
    tree_line(c, 700, (22, 30, 40, 255), seed=33, h0=30, h1=60, step=(14, 24))
    for k in range(5):                                                                            # Talnebel
        c.soft_poly([(-50, 720 + k * 50), (VW + 50, 710 + k * 50), (VW + 50, 780 + k * 55), (-50, 790 + k * 55)], (190, 200, 216, 90), 26)
    tree_line(c, 930, (30, 38, 48, 255), seed=35, h0=40, h1=90, step=(20, 36))                    # Wipfel im Nebel
    c.soft_poly([(-50, 900), (VW + 50, 890), (VW + 50, VH + 20), (-50, VH + 20)], (180, 190, 206, 150), 22)
    # Felsnase links, Oberkante y 440 (-> Hochsitz-Fuss in eject_scenes.json: unit y 0,6)
    c.poly([(-10, 432), (220, 440), (282, 452), (318, 482), (336, 560), (300, 700), (340, 860), (-10, 1000)], (40, 36, 38, 255), lw=6)
    c.mottle(0.08, cell=10, seed=34)
    for x in (30, 90, 250):
        for k in range(5):
            c.line([(x + k * 4, 438), (x + k * 4 + (k - 2) * 3, 418)], (36, 46, 36, 255), 3)
    c.vignette(0.4)
    save_bg(c, "task_eject_valley_bg.jpg")

    wood, wood_l, wood_d = (132, 92, 56, 255), (162, 114, 68, 255), (84, 58, 36, 255)
    st = C(300, 470)
    for a, b in (((74, 170), (44, 466)), ((226, 170), (256, 466))):
        st.line([a, b], wood_d, 13)
    st.line([(58, 260), (240, 420)], wood_d, 6)
    st.line([(242, 260), (60, 420)], wood_d, 6)
    for a, b in (((92, 176), (62, 466)), ((208, 176), (238, 466))):
        st.capsule(a, b, 14, wood, lw=4)
    for y in (300, 404):
        st.capsule((80 - (y - 176) * 0.1, y), (220 + (y - 176) * 0.1, y), 8, wood_l, lw=3)
    for x0, x1 in ((128, 112), (172, 188)):
        st.line([(x0, 178), (x1, 466)], wood_l, 7)
    for k in range(9):
        y = 204 + k * 30
        f = (y - 178) / 288
        st.line([(128 - 16 * f, y), (172 + 16 * f, y)], wood_d, 5)
    st.rrect(36, 152, 264, 176, 4, wood_l, lw=5, sh=(0.2, 0.3))
    st.grain(36, 152, 264, 176, 0.12, seed=36)
    for x in (48, 150, 252):
        st.rrect(x - 6, 76, x + 6, 156, 2, wood, lw=3)
    st.rrect(42, 96, 156, 108, 3, wood_l, lw=3)
    st.rrect(42, 126, 258, 136, 3, wood, lw=3)
    st.poly([(24, 78), (276, 78), (256, 44), (44, 44)], wood_d, lw=5, sh=(0.15, 0.3))
    for x in range(60, 250, 26):
        st.line([(x, 46), (x - 4, 76)], (66, 46, 30, 255), 3)
    save(st, "task_eject_stand.png")

    pl = C(112, 18)
    pl.rrect(3, 3, 109, 15, 3, wood_l, lw=3)
    pl.grain(3, 3, 109, 15, 0.14, seed=37)
    save(pl, "task_eject_plank.png")

    for i, alpha in enumerate((70, 110)):                                                         # Nebelbaender (Parallax)
        f = C(1400, 220)
        for k in range(6):
            f.soft_poly([(-60, 70 + k * 14), (1460, 60 + k * 16), (1460, 190), (-60, 200)], (200, 208, 224, alpha // 2 + 10), 24)
        save(f, f"task_eject_fog{i}.png")


# ================================================================== Skip-Szenen (niemand fliegt)

def gallery():
    """Museum, Skip: Galerie mit leerer Vitrine im Scheinwerfer."""
    c = C(BW, BH)
    grad(c, (96, 32, 40), (58, 20, 27), 0, 420)
    c.mottle(0.07, cell=9, seed=51)
    rect(c, 0, 26, BW, 48, (150, 118, 62, 255))                                                   # Stuckleiste
    c.line([(0, 48), (BW, 48)], (90, 66, 34, 255), 3)
    grad(c, (84, 56, 38), (60, 40, 28), 400, 474)                                                 # Wandvertaefelung
    for x in range(20, BW, 150):
        c.rrect(x, 410, x + 130, 464, 4, None, lw=3, outline=(46, 30, 20, 255))
    c.line([(0, 400), (BW, 400)], (40, 26, 18, 255), 5)
    grad(c, (104, 70, 44), (58, 38, 24), 474, BH)                                                 # Parkett
    for y in range(474, BH, 22):
        off = (y // 22) % 2 * 40
        for x in range(-80 + off, BW, 80):
            c.line([(x, y), (x + 40, y + 22)], (70, 46, 30, 255), 2)
    c.line([(0, 474), (BW, 474)], (30, 20, 14, 255), 5)

    def frame(x0, y0, x1, y1):
        c.rrect(x0 - 16, y0 - 16, x1 + 16, y1 + 16, 4, (176, 136, 60, 255), lw=4, sh=(0.25, 0.35))
        c.rrect(x0 - 6, y0 - 6, x1 + 6, y1 + 6, 2, (120, 88, 36, 255), lw=3)
        c.glow((x0 + x1) / 2, y0 - 40, (x1 - x0) / 2 + 30, 60, (255, 214, 150, 60), 24)          # Bilderleuchte
        c.rrect((x0 + x1) / 2 - 40, y0 - 44, (x0 + x1) / 2 + 40, y0 - 34, 4, (190, 150, 70, 255), lw=3)

    x0, y0, x1, y1 = 130, 120, 330, 320                                                           # Landschaft
    frame(x0, y0, x1, y1)
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=(120, 150, 190, 255))
    c.poly([(x0, 260), (180, 190), (230, 240), (280, 170), (x1, 250), (x1, y1), (x0, y1)], (70, 96, 84, 255), lw=0)
    c.poly([(x0, 290), (x1, 280), (x1, y1), (x0, y1)], (90, 130, 160, 255), lw=0)
    c.ell(290, 160, 16, 16, (250, 230, 170, 255), lw=0)
    x0, y0, x1, y1 = 870, 110, 1070, 330                                                          # Portraet (Crewmate mit Halskrause)
    frame(x0, y0, x1, y1)
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=(34, 30, 38, 255))
    c.rrect(930, 180, 1010, 300, 36, (150, 40, 40, 255), lw=4)
    c.rrect(960, 200, 1004, 226, 12, (150, 200, 220, 255), lw=3)
    for k in range(7):
        c.ell(935 + k * 12, 300, 10, 8, (236, 230, 214, 255), lw=2)
    rect(c, x0, 312, x1, 330, (30, 26, 34, 255))
    for x in (420, 780):                                                                          # Absperrpfosten
        c.ell(x + 4, 594, 22, 7, (0, 0, 0, 90), lw=0)
        c.rrect(x - 7, 500, x + 7, 590, 3, (190, 150, 70, 255), lw=3, shx=(0.2, 0.3))
        c.ell(x, 498, 11, 9, (210, 172, 86, 255), lw=3)
    c.arc([420, 470, 780, 560], 25, 155, (150, 30, 40, 255), 8)
    c.vignette(0.4)
    save_bg(c, "task_eject_gallery_bg.jpg")

    v = C(240, 330)                                                                               # Vitrine auf Marmorsockel
    v.rrect(66, 176, 174, 326, 4, (220, 214, 204, 255), lw=5, shx=(0.18, 0.32))
    v.mottle(0.05, cell=5, seed=52)
    v.rrect(46, 316, 194, 330, 3, (200, 194, 184, 255), lw=4)
    v.rrect(46, 160, 194, 180, 3, (210, 204, 194, 255), lw=4)
    v.rrect(52, 14, 188, 162, 3, (200, 226, 240, 44), lw=0)                                      # Glas (zuerst: PIL mischt nicht)
    v.rrect(62, 126, 178, 160, 20, (150, 34, 44, 255), lw=4, sh=(0.25, 0.3))                      # Samtkissen ...
    v.ell(120, 132, 26, 6, (110, 22, 32, 255), lw=0)                                             # ... mit Delle
    v.rrect(52, 14, 188, 162, 3, None, lw=4, outline=(120, 132, 144, 255))                        # Glashaube
    v.rrect(48, 6, 192, 18, 3, (140, 150, 160, 255), lw=3)
    for a, b in (((70, 30), (110, 120)), ((96, 26), (120, 70)), ((150, 40), (176, 100))):
        v.line([a, b], (255, 255, 255, 120), 4)
    save(v, "task_eject_case.png")

    pl = C(170, 110)                                                                              # Schild
    pl.line([(85, 60), (85, 108)], (60, 50, 40, 255), 6)
    pl.rrect(10, 8, 160, 64, 5, (196, 160, 82, 255), lw=4, sh=(0.25, 0.35))
    label(pl, 85, 24, "EXHIBIT", 11, (70, 50, 20, 255))
    label(pl, 85, 45, "VACANT", 20, (50, 32, 12, 255))
    save(pl, "task_eject_placard.png")

    m = C(44, 30)                                                                                 # Motte
    m.ell(13, 13, 11, 8, (170, 150, 120, 255), lw=2)
    m.ell(31, 13, 11, 8, (170, 150, 120, 255), lw=2)
    m.ell(14, 21, 7, 5, (150, 130, 104, 255), lw=2)
    m.ell(30, 21, 7, 5, (150, 130, 104, 255), lw=2)
    m.rrect(19, 6, 25, 26, 3, (90, 76, 60, 255), lw=1)
    save(m, "task_eject_moth.png")


def camp():
    """Wald, Skip: Lagerfeuer an der Station, Baumstamm-Bank, Zelt."""
    c = C(BW, BH)
    grad(c, (10, 14, 30), (24, 32, 50), 0, 380)
    stars(c, 80, 260, seed=61)
    moon(c, 980, 90, 32)
    tree_line(c, 330, (20, 30, 36, 255), seed=62, h0=120, h1=220, step=(30, 54))
    tree_line(c, 420, (13, 20, 22, 255), seed=63, h0=80, h1=160, step=(40, 70))
    grad(c, (40, 44, 34), (20, 22, 18), 440, BH)                                                  # Lichtung
    c.glow(600, 560, 330, 150, (255, 150, 60, 70), 50)                                            # Feuerschein am Boden
    c.poly([(840, 470), (960, 340), (1090, 470)], (70, 84, 60, 255), lw=5, sh=(0.1, 0.4))         # Zelt
    c.poly([(960, 340), (940, 470), (980, 470)], (30, 36, 28, 255), lw=3)
    c.line([(960, 340), (960, 318)], (60, 50, 40, 255), 4)
    # Baumstamm-Bank (Eule landet bei x ~300, Oberkante y ~470)
    c.capsule((160, 500), (520, 492), 52, (110, 76, 46, 255), lw=5, sh=(0.2, 0.4))
    c.ell(522, 492, 22, 26, (170, 130, 86, 255), lw=4)
    c.ell(522, 492, 12, 14, (140, 100, 64, 255), lw=0)
    for x in range(200, 500, 40):
        c.line([(x, 480), (x + 22, 478)], (84, 56, 34, 255), 3)
    for k in range(9):                                                                            # Feuerstelle
        a = math.pi * 2 * k / 9
        c.ell(600 + math.cos(a) * 70, 568 + math.sin(a) * 22, 20, 13, (96, 92, 90, 255), lw=4, sh=(0.3, 0.4))
    c.capsule((560, 566), (646, 556), 16, (80, 54, 32, 255), lw=3)
    c.capsule((566, 552), (640, 570), 16, (92, 62, 36, 255), lw=3)
    c.glow(600, 560, 60, 20, (255, 120, 40, 160), 10)
    c.vignette(0.5)
    save_bg(c, "task_eject_camp_bg.jpg")

    o = C(100, 120)                                                                               # sitzende Eule
    brown, light_b = (112, 84, 58, 255), (170, 138, 100, 255)
    o.ell(50, 74, 34, 40, brown, lw=5, sh=(0.2, 0.3))
    o.ell(50, 44, 30, 28, brown, lw=5)
    o.poly([(26, 26), (22, 8), (36, 22)], brown, lw=3)
    o.poly([(74, 26), (78, 8), (64, 22)], brown, lw=3)
    o.ell(50, 46, 24, 18, light_b, lw=0)
    o.poly([(46, 52), (54, 52), (50, 62)], (220, 170, 60, 255), lw=2)
    for k in range(4):
        o.arc([30, 70 + k * 8, 70, 90 + k * 8], 20, 160, (86, 62, 42, 255), 3)
    for x in (40, 60):
        o.line([(x, 112), (x, 118)], (220, 170, 60, 255), 4)
    save(o, "task_eject_owl_sit.png")

    e = C(60, 26)                                                                                 # Eulenaugen (Blinzeln)
    for x in (16, 44):
        e.ell(x, 13, 11, 11, (250, 200, 60, 255), lw=3)
        e.ell(x, 13, 5, 6, (20, 16, 12, 255), lw=0)
        e.glint(x - 3, 9, 2, 2, 220)
    save(e, "task_eject_owl_eyes.png")


def deer():
    """Wald, Skip: Reh am Fluss (Koerper und Kopf getrennt, Kopf dreht um den Halsansatz)."""
    brown, dark_b, belly = (150, 102, 62, 255), (96, 64, 40, 255), (206, 172, 132, 255)
    b = C(240, 200)
    for x0, x1 in ((64, 58), (92, 94), (176, 170), (200, 206)):                                   # Beine
        b.line([(x0, 120), (x1, 188)], dark_b if x0 in (92, 200) else brown, 9)
        b.ell(x1, 190, 6, 5, (40, 30, 24, 255), lw=0)
    b.ell(130, 100, 90, 42, brown, lw=5, sh=(0.2, 0.35))
    b.ell(130, 118, 60, 18, belly, lw=0)
    b.ell(222, 86, 12, 16, (240, 236, 226, 255), lw=3)                                            # Spiegel
    for x, y in ((110, 80), (140, 74), (170, 84), (120, 100)):
        b.ell(x, y, 5, 4, (220, 190, 150, 255), lw=0)
    save(b, "task_eject_deer_body.png")

    h = C(150, 160)                                                                               # Hals + Kopf
    h.poly([(108, 152), (148, 140), (104, 54), (58, 62)], brown, lw=5, sh=(0.1, 0.3))
    h.ell(58, 48, 32, 22, brown, lw=5, sh=(0.2, 0.3))
    h.poly([(30, 44), (4, 56), (10, 64), (34, 58)], brown, lw=4)
    h.ell(8, 58, 5, 4, (30, 24, 20, 255), lw=0)
    h.ell(46, 40, 5, 5, (20, 16, 14, 255), lw=0)
    h.glint(44, 38, 2, 2, 220)
    h.poly([(66, 30), (78, 4), (88, 30)], brown, lw=4)
    h.poly([(80, 34), (98, 12), (100, 36)], dark_b, lw=4)
    save(h, "task_eject_deer_head.png")

    f = C(70, 34)                                                                                 # Fisch
    f.ell(30, 17, 24, 11, (170, 186, 196, 255), lw=4, sh=(0.3, 0.3))
    f.poly([(52, 17), (68, 5), (68, 29)], (150, 166, 176, 255), lw=4)
    f.ell(16, 14, 3, 3, INK, lw=0)
    save(f, "task_eject_fish.png")


# ================================================================== Unknown's Collection: Void (eigenes Repo)

UC_RES = Path(__file__).resolve().parent.parent.parent / "UnknownsCollection" / "Resources"
VOID_SHARED = ("task_eject_glow.png", "task_eject_mote.png", "task_eject_ripple.png", "task_eject_px.png",
               "task_eject_vignette.png", "task_eject_puff.png")


def void_art():
    """Void-Szene fuer UC: Leere, Riss, Stimmzettel, Splitter. Ausgabe direkt nach UnknownsCollection/Resources,
    dazu Kopien der allgemeinen Partikel/Kino-Sprites (UC laedt nur aus seinen eigenen Ressourcen)."""
    import shutil
    global OUT
    keep = OUT
    OUT = UC_RES
    try:
        c = C(BW, BH)
        n_h, n_w = BH * S, BW * S
        yy, xx = np.mgrid[0:n_h, 0:n_w].astype(np.float32)
        r = np.sqrt(((xx - n_w * 0.42) / (n_w * 0.6)) ** 2 + ((yy - n_h * 0.5) / (n_h * 0.75)) ** 2)
        t = np.clip(r, 0, 1)[..., None]
        inner, outer = np.array([46, 12, 72], np.float32), np.array([6, 3, 12], np.float32)
        arr = np.zeros((n_h, n_w, 4), np.float32)
        arr[..., :3] = inner * (1 - t) + outer * t
        arr[..., 3] = 255
        c.img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
        c.d = ImageDraw.Draw(c.img)
        rnd = random.Random(71)
        for _ in range(9):                                                                        # Nebel magenta/violett
            x, y = rnd.uniform(100, 1100), rnd.uniform(80, 600)
            col = rnd.choice([(150, 40, 220, 40), (255, 60, 220, 28), (90, 30, 170, 45)])
            c.soft_poly([(x - 220, y), (x - 60, y - 70), (x + 200, y - 30), (x + 140, y + 60), (x - 120, y + 50)], col, 40)
        stars(c, 160, BH, seed=72)
        for _ in range(14):                                                                       # Staubwirbel-Bogen
            cx, cy, rr = 500, 340, rnd.uniform(160, 520)
            a0 = rnd.uniform(0, 360)
            c.arc([cx - rr, cy - rr * 0.45, cx + rr, cy + rr * 0.45], a0, a0 + rnd.uniform(20, 70), (200, 90, 255, 20), 2)
        c.vignette(0.55)
        save_bg(c, "task_eject_void_bg.jpg")

        # Riss: Spiralarme um ein schwarzes Loch, heller Rand
        n = 320
        img = np.zeros((n * S, n * S, 4), np.float32)
        yy, xx = np.mgrid[0:n * S, 0:n * S].astype(np.float32)
        dx, dy = (xx - n * S / 2) / (n * S / 2), (yy - n * S / 2) / (n * S / 2)
        rr = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx)
        spiral = 0.5 + 0.5 * np.sin(ang * 3 + rr * 14)
        ring = np.exp(-((rr - 0.55) / 0.22) ** 2)
        glow = np.clip(1 - rr, 0, 1) ** 1.5
        mag, vio = np.array([255, 70, 230], np.float32), np.array([120, 40, 230], np.float32)
        colr = mag * spiral[..., None] + vio * (1 - spiral[..., None])
        a = np.clip(ring * (0.45 + 0.55 * spiral) + glow * 0.35, 0, 1) * (rr < 1)
        core = np.clip(1 - rr / 0.28, 0, 1)
        colr = colr * (1 - core[..., None]) + np.array([8, 2, 16], np.float32) * core[..., None]
        a = np.maximum(a, core)
        img[..., :3] = colr
        img[..., 3] = a * 255
        Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA").resize((round(n * K), round(n * K)), Image.LANCZOS) \
            .save(OUT / "task_eject_void_rift.png", optimize=True)

        b = C(64, 46)                                                                             # Stimmzettel
        b.rrect(4, 4, 60, 42, 4, (246, 244, 250, 255), lw=3, outline=(80, 60, 110, 255))
        for y in (14, 22, 30):
            b.line([(12, y), (36, y)], (190, 180, 210, 255), 2)
        b.line([(40, 24), (46, 32), (56, 12)], (150, 40, 220, 255), 4)
        save(b, "task_eject_void_ballot.png")

        s = C(26, 22)                                                                             # Glitch-Splitter
        s.poly([(2, 20), (13, 2), (24, 16)], (255, 255, 255, 255), lw=0)
        save(s, "task_eject_void_shard.png")

        for f in VOID_SHARED:                                                                     # allgemeine Sprites mitgeben
            shutil.copyfile(keep / f, OUT / f)
            print("copy", f)
    finally:
        OUT = keep


if __name__ == "__main__":
    common()
    tomb()
    depot()
    hall()
    night()
    river()
    forest()
    valley()
    gallery()
    camp()
    deer()
    void_art()
