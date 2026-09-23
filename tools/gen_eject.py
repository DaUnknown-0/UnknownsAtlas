"""Unknown's Atlas - Grafiken der Rauswurf-Szenen (AtlasEject.cs).

Hintergruende 1100 x 620 px (100 px = 1 Einheit, Mitte = Szenenursprung) und bewegliche Teile.
Alle Dateien heissen task_eject_*; Hintergruende sind JPG (deckend), bewegliche Teile PNG.

    python tools/gen_eject.py
"""

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_tasks import C, S, INK, OUT, mix, dark, light  # noqa: E402

W, H = 1100, 620


def grad(c, top, bottom, y0=0, y1=None):
    """Senkrechter Farbverlauf ueber die ganze Flaeche (zwischen y0 und y1 in Zielpixeln)."""
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


def save_bg(c, name):
    """Deckende Hintergruende als JPG (q92, volle Farbaufloesung): optisch wie PNG, 60-80 % kleiner."""
    img = c.img.resize((c.w, c.h), Image.LANCZOS).convert("RGB")
    img.save(OUT / name, "JPEG", quality=92, optimize=True, progressive=True, subsampling=0)
    print(OUT / name, img.size)


def rect(c, x0, y0, x1, y1, col):
    c.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=col)


def stars(c, n, y1, seed=4):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y, r = rnd.uniform(0, c.w), rnd.uniform(0, y1), rnd.choice((1, 1, 1.5, 2))
        a = rnd.randint(120, 230)
        c.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(230, 236, 255, a))


def moon(c, x, y, r):
    c.glow(x, y, r * 3.2, r * 3.2, (170, 190, 255, 60), r * 1.2)
    c.ell(x, y, r, r, (238, 240, 226, 255), lw=0)
    c.ell(x + r * 0.3, y - r * 0.2, r * 0.22, r * 0.22, (214, 214, 196, 255), lw=0)
    c.ell(x - r * 0.35, y + r * 0.3, r * 0.15, r * 0.15, (214, 214, 196, 255), lw=0)


def tree_line(c, y, col, seed, h0=60, h1=140, step=(22, 44)):
    """Silhouetten von Nadelbaeumen entlang einer Linie."""
    rnd = random.Random(seed)
    x = -20
    while x < c.w + 40:
        h = rnd.uniform(h0, h1)
        wd = h * rnd.uniform(0.32, 0.42)
        pts = [(x, y)]
        for k in range(4):
            yy = y - h * (k + 1) / 4.4
            ww = wd * (1 - k / 4.6)
            pts = [(x - ww, yy + h * 0.1)] + pts + [(x + ww, yy + h * 0.1)]
            c.d.polygon(c.P([(x - ww, yy + h * 0.12), (x, yy - h * 0.2), (x + ww, yy + h * 0.12)]), fill=col)
        rect(c, x - 3, y - h * 0.15, x + 3, y + 4, col)
        x += rnd.uniform(*step)
    rect(c, 0, y, c.w, c.h, col)


def soft():
    """Weicher weisser Kreis (Staub, Schatten, Nebel, Abdunklung)."""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([24, 24, 232, 232], fill=(255, 255, 255, 255))
    img = img.filter(ImageFilter.GaussianBlur(28))
    img.save(OUT / "task_eject_soft.png")


def top_band():
    """Dunkler Verlauf hinter dem Rauswurf-Text."""
    img = Image.new("RGBA", (64, 160), (0, 0, 0, 0))
    a = np.zeros((160, 64, 4), np.uint8)
    a[..., 3] = (np.clip(1 - np.arange(160) / 160, 0, 1) ** 1.4 * 200).astype(np.uint8)[:, None]
    Image.fromarray(a, "RGBA").save(OUT / "task_eject_band.png")


# ================================================================== Museum 1: Sarkophag

def tomb():
    c = C(W, H)
    grad(c, (46, 38, 32), (20, 16, 14))
    # Steinquader
    for row in range(8):
        y = row * 52
        off = 0 if row % 2 else 60
        for x in range(-off, W, 120):
            col = mix((70, 58, 46, 255), (54, 44, 36, 255), random.Random(row * 31 + x).random())
            c.rrect(x + 3, y + 3, x + 117, y + 49, 6, col, lw=3, outline=(30, 24, 20, 255))
    c.mottle(0.1, cell=8, seed=7)
    # Hieroglyphen-Band
    rect(c, 0, 300, W, 340, (120, 92, 50, 255))
    for i, x in enumerate(range(20, W, 46)):
        k = i % 4
        col = (60, 40, 22, 255)
        if k == 0:
            c.ell(x + 10, 320, 9, 9, None, lw=3, outline=col)
            c.line([(x + 10, 310), (x + 10, 330)], col, 3)
        elif k == 1:
            c.line([(x, 332), (x + 10, 308), (x + 20, 332)], col, 3)
        elif k == 2:
            c.line([(x, 320), (x + 20, 320)], col, 3)
            c.ell(x + 10, 312, 5, 5, col, lw=0)
        else:
            c.line([(x + 4, 308), (x + 4, 332), (x + 18, 332)], col, 3)
    # Boden
    grad(c, (58, 48, 40), (30, 24, 20), 380, H)
    for x in range(-40, W, 140):
        c.line([(x, 380), (x - 80, H)], (36, 28, 24, 255), 3)
    c.line([(0, 380), (W, 380)], (34, 26, 22, 255), 4)
    c.line([(0, 470), (W, 470)], (40, 32, 26, 255), 3)
    # Fackeln mit Lichtkegel
    for x in (150, 950):
        c.glow(x, 200, 160, 160, (255, 170, 70, 70), 60)
        c.rrect(x - 8, 200, x + 8, 270, 3, (90, 64, 40, 255), lw=3)
        c.glow(x, 186, 24, 34, (255, 200, 90, 230), 8)
        c.ell(x, 190, 10, 18, (255, 236, 160, 255), lw=0)
    c.vignette(0.55)
    save_bg(c, "task_eject_tomb_bg.jpg")

    # Sarkophag-Wanne (Vorderwand deckt den Spieler unten ab)
    s = C(420, 200)
    s.poly([(20, 40), (400, 40), (380, 190), (40, 190)], (40, 64, 120, 255), lw=6, sh=(0.2, 0.35))
    s.poly([(20, 40), (400, 40), (392, 62), (28, 62)], (214, 172, 80, 255), lw=4)
    for i in range(7):
        x = 70 + i * 48
        s.rrect(x, 80, x + 30, 170, 6, (214, 172, 80, 255) if i % 2 else (180, 60, 50, 255), lw=3)
    s.save("task_eject_sarc_base.png")

    # Deckel mit Pharaonengesicht
    lid = C(440, 150)
    lid.rrect(10, 20, 430, 130, 40, (214, 172, 80, 255), lw=6, sh=(0.25, 0.35))
    lid.ell(90, 75, 46, 50, (46, 70, 130, 255), lw=4)
    lid.ell(90, 78, 30, 36, (200, 150, 90, 255), lw=4)
    for dy in (-8, 8):
        lid.line([(78, 70 + dy * 0.2), (86, 70 + dy * 0.2)], INK, 3)
    lid.ell(80, 70, 4, 3, INK, lw=0)
    lid.ell(100, 70, 4, 3, INK, lw=0)
    lid.line([(84, 92), (96, 92)], INK, 3)
    for i in range(6):
        x = 160 + i * 42
        lid.line([(x, 34), (x, 116)], (160, 120, 50, 255), 5)
    lid.glint(260, 40, 120, 8, 90)
    lid.save("task_eject_sarc_lid.png")


# ================================================================== Museum 2: Falltuer ins Depot

def depot():
    c = C(W, H)
    # Schachbrett-Fliesen von oben
    for yi in range(0, H, 80):
        for xi in range(0, W, 80):
            col = (226, 214, 190, 255) if (xi // 80 + yi // 80) % 2 == 0 else (178, 162, 138, 255)
            rect(c, xi, yi, xi + 80, yi + 80, col)
    c.mottle(0.05, cell=12, seed=3)
    # Kordel-Absperrung
    for x, y in ((290, 150), (810, 150), (290, 470), (810, 470)):
        c.ell(x, y, 18, 18, (196, 160, 82, 255), lw=4, sh=(0.3, 0.3))
    for a, b in (((290, 150), (810, 150)), ((290, 470), (810, 470)), ((290, 150), (290, 470)), ((810, 150), (810, 470))):
        c.line([a, b], (150, 30, 40, 255), 7)
    # Schacht: dunkler Verlauf in die Tiefe
    c.rrect(410, 200, 690, 420, 8, (20, 16, 18, 255), lw=10, outline=(90, 70, 50, 255))
    c.glow(550, 310, 90, 70, (0, 0, 0, 255), 30)
    for k in range(4):
        y = 230 + k * 50
        c.line([(440, y), (660, y)], (40, 34, 30, 255), 3)
    c.vignette(0.4)
    save_bg(c, "task_eject_depot_bg.jpg")

    leaf = C(140, 220)
    leaf.rrect(4, 4, 136, 216, 6, (150, 104, 60, 255), lw=6, sh=(0.2, 0.3))
    leaf.grain(4, 4, 136, 216, 0.1, seed=5)
    for y in (40, 110, 180):
        leaf.line([(14, y), (126, y)], (100, 68, 40, 255), 5)
    leaf.rivet(30, 110, 6)
    leaf.save("task_eject_trap_leaf.png")


# ================================================================== Museum 3: T-Rex

def hall():
    c = C(W, H)
    grad(c, (30, 34, 54), (16, 18, 30), 0, 440)
    # hohe Fenster mit Mondlicht
    for x in (120, 380, 640, 900):
        c.rrect(x, 40, x + 120, 330, 60, (70, 90, 140, 255), lw=8, outline=(40, 44, 60, 255))
        c.line([(x + 60, 40), (x + 60, 330)], (40, 44, 60, 255), 6)
        c.line([(x, 190), (x + 120, 190)], (40, 44, 60, 255), 6)
        c.soft_poly([(x, 330), (x + 120, 330), (x + 170, 620), (x - 40, 620)], (140, 170, 230, 40), 20)
    # Saeulen
    for x in (60, 320, 580, 840, 1060):
        c.rrect(x - 22, 20, x + 22, 440, 6, (84, 84, 96, 255), lw=5, shx=(0.15, 0.35))
    # polierter Boden
    grad(c, (48, 44, 50), (26, 24, 30), 440, H)
    c.line([(0, 440), (W, 440)], (20, 20, 26, 255), 5)
    c.rrect(430, 8, 670, 40, 8, (120, 40, 40, 255), lw=4)
    c.vignette(0.5)
    save_bg(c, "task_eject_hall_bg.jpg")

    # T-Rex-Schaedel (Oberkiefer) und Unterkiefer, Knochenfarbe
    bone, bone_d = (232, 222, 196, 255), (196, 182, 150, 255)
    h = C(560, 280)
    h.poly([(40, 150), (120, 70), (260, 40), (420, 50), (540, 110), (548, 160), (500, 170), (60, 180)], bone, lw=7, sh=(0.2, 0.35))
    h.ell(360, 100, 38, 30, (40, 34, 30, 255), lw=5)             # Augenhoehle
    h.ell(230, 110, 50, 36, (60, 52, 44, 255), lw=5)             # Schlaefenfenster
    h.ell(500, 118, 14, 10, (40, 34, 30, 255), lw=4)             # Nasenloch
    for i in range(12):
        x = 100 + i * 36
        h.poly([(x, 172), (x + 14, 172), (x + 7, 214)], (246, 240, 222, 255), lw=3)
    h.save("task_eject_trex_head.png")
    j = C(520, 140)
    j.poly([(20, 40), (480, 30), (510, 60), (470, 90), (60, 110)], bone_d, lw=7, sh=(0.2, 0.3))
    for i in range(11):
        x = 80 + i * 36
        j.poly([(x, 44), (x + 12, 44), (x + 6, 10)], (246, 240, 222, 255), lw=3)
    j.save("task_eject_trex_jaw.png")


# ================================================================== Museum 4: Hinausgeworfen

def night():
    c = C(W, H)
    grad(c, (14, 18, 34), (30, 36, 56), 0, 420)
    # Fassade links
    c.rrect(-20, 60, 420, 470, 0, (58, 56, 64, 255), lw=6)
    c.mottle(0.08, cell=10, seed=9)
    for x in (30, 130, 300, 390):
        c.rrect(x - 16, 90, x + 16, 440, 4, (80, 78, 88, 255), lw=4, shx=(0.12, 0.3))
    c.poly([(-20, 60), (200, 10), (440, 60)], (70, 68, 78, 255), lw=6)
    # Tueroeffnung warm
    c.glow(215, 330, 150, 150, (255, 190, 90, 80), 50)
    c.rrect(160, 220, 270, 440, 10, (255, 214, 140, 255), lw=8, outline=(34, 30, 34, 255))
    # Treppe und Pflaster
    for k in range(3):
        c.rrect(120 - k * 30, 440 + k * 18, 310 + k * 30, 458 + k * 18, 3, (90, 88, 96, 255), lw=4)
    grad(c, (34, 36, 44), (20, 22, 28), 494, H)
    rect(c, 420, 420, W, 494, (26, 28, 36, 255))
    # Laterne rechts
    c.line([(930, 180), (930, 494)], (30, 30, 36, 255), 10)
    c.glow(930, 170, 120, 120, (255, 220, 150, 60), 40)
    c.rrect(910, 150, 950, 190, 6, (255, 230, 170, 255), lw=5)
    # Pfuetzen mit Spiegelung
    for x, w in ((640, 150), (880, 110), (470, 90)):
        c.ell(x, 560, w, 18, (60, 70, 100, 255), lw=0)
        c.glint(x - w * 0.3, 556, w * 0.4, 4, 60)
    c.vignette(0.45)
    save_bg(c, "task_eject_night_bg.jpg")

    g = C(150, 200)
    g.ell(75, 120, 58, 72, (34, 44, 80, 255), lw=6, sh=(0.2, 0.3))            # Koerper
    g.rrect(40, 70, 118, 104, 16, (150, 190, 220, 255), lw=5)                  # Visier
    g.rrect(30, 30, 120, 62, 10, (24, 30, 56, 255), lw=5)                      # Muetze
    g.rrect(22, 56, 128, 66, 4, (18, 22, 40, 255), lw=4)                       # Schirm
    g.ell(75, 44, 10, 8, (214, 172, 80, 255), lw=3)                            # Abzeichen
    g.rrect(40, 176, 66, 198, 6, (24, 30, 56, 255), lw=4)
    g.rrect(84, 176, 110, 198, 6, (24, 30, 56, 255), lw=4)
    g.save("task_eject_guard.png")

    d = C(120, 230)
    d.rrect(4, 4, 116, 226, 8, (96, 60, 40, 255), lw=6, sh=(0.2, 0.3))
    d.grain(4, 4, 116, 226, 0.1, seed=11)
    d.rrect(18, 20, 102, 100, 6, (80, 50, 34, 255), lw=4)
    d.rrect(18, 120, 102, 210, 6, (80, 50, 34, 255), lw=4)
    d.ell(96, 118, 6, 6, (214, 172, 80, 255), lw=2)
    d.save("task_eject_door.png")


# ================================================================== Wald 1: Wildwasser

def river():
    c = C(W, H)
    grad(c, (12, 16, 32), (26, 34, 56), 0, 260)
    stars(c, 80, 220, seed=12)
    moon(c, 880, 90, 34)
    tree_line(c, 250, (16, 26, 30, 255), seed=5, h0=80, h1=170)
    # Fluss (Band), rechts Abbruchkante des Wasserfalls
    c.poly([(-10, 300), (840, 290), (860, 470), (-10, 470)], (40, 80, 110, 255), lw=0)
    for k in range(14):
        y = 310 + k * 11
        x0 = random.Random(k).uniform(0, 200)
        c.line([(x0, y), (x0 + 220, y - 2)], (90, 140, 170, 160), 3)
        c.line([(x0 + 360, y + 4), (x0 + 520, y + 2)], (90, 140, 170, 120), 3)
    # Wasserfall-Kante und Gischt
    c.poly([(840, 290), (870, 300), (880, 470), (860, 470)], (150, 190, 210, 255), lw=0)
    c.glow(960, 470, 180, 120, (220, 235, 245, 140), 40)
    rect(c, 860, 470, W, H, (18, 24, 30, 255))
    # Ufer
    tree_line(c, 510, (12, 18, 20, 255), seed=8, h0=40, h1=90)
    c.poly([(-10, 470), (860, 470), (880, 510), (-10, 510)], (30, 40, 34, 255), lw=0)
    c.vignette(0.45)
    save_bg(c, "task_eject_river_bg.jpg")

    k = C(360, 110)
    k.poly([(10, 30), (350, 30), (320, 80), (260, 100), (100, 100), (40, 80)], (170, 100, 56, 255), lw=6, sh=(0.25, 0.35))
    k.line([(20, 38), (340, 38)], (220, 160, 100, 255), 5)
    for x in (110, 250):
        k.line([(x, 38), (x, 92)], (120, 70, 40, 255), 5)
    k.save("task_eject_canoe.png")


# ================================================================== Wald 2: In den Wald gezerrt

def forest():
    c = C(W, H)
    grad(c, (8, 12, 20), (18, 26, 30), 0, 380)
    stars(c, 40, 180, seed=21)
    tree_line(c, 330, (14, 22, 24, 255), seed=13, h0=140, h1=260, step=(30, 60))
    tree_line(c, 420, (10, 16, 18, 255), seed=14, h0=100, h1=200, step=(40, 70))
    grad(c, (26, 36, 28), (14, 20, 16), 470, H)
    # Lichtung: schwacher Mondfleck in der Mitte
    c.glow(420, 520, 260, 60, (120, 140, 160, 60), 30)
    c.vignette(0.6)
    save_bg(c, "task_eject_forest_bg.jpg")

    b = C(520, 360)
    rnd = random.Random(3)
    for _ in range(26):
        x, y, r = rnd.uniform(40, 480), rnd.uniform(120, 340), rnd.uniform(50, 90)
        c2 = mix((14, 30, 20, 255), (30, 54, 34, 255), rnd.random())
        b.ell(x, y, r, r * 0.8, c2, lw=4, outline=(8, 14, 10, 255))
    b.save("task_eject_bushes.png")

    e = C(90, 40)
    for x in (22, 68):
        e.glow(x, 20, 18, 12, (255, 40, 30, 160), 6)
        e.ell(x, 20, 9, 6, (255, 70, 50, 255), lw=0)
        e.ell(x, 20, 3, 5, (60, 0, 0, 255), lw=0)
    e.save("task_eject_eyes.png")


# ================================================================== Wald 3: Vom Hochsitz

def valley():
    c = C(W, H)
    grad(c, (18, 22, 40), (54, 62, 84), 0, 360)
    stars(c, 60, 200, seed=31)
    moon(c, 760, 110, 40)
    # ferne Bergkaemme
    for k, (y, col) in enumerate(((300, (40, 48, 66, 255)), (350, (32, 40, 54, 255)))):
        rnd = random.Random(40 + k)
        pts = [(-10, H)]
        x = -10
        while x < W + 20:
            pts.append((x, y + rnd.uniform(-40, 30)))
            x += rnd.uniform(60, 120)
        pts.append((W + 20, H))
        c.poly(pts, col, lw=0)
    tree_line(c, 400, (22, 30, 38, 255), seed=33, h0=30, h1=60, step=(14, 24))
    # Talnebel
    for k in range(4):
        c.soft_poly([(-50, 420 + k * 40), (W + 50, 410 + k * 40), (W + 50, 470 + k * 50), (-50, 480 + k * 50)], (190, 200, 214, 90), 25)
    # Felskante links
    c.poly([(-10, 330), (240, 350), (300, 420), (330, H + 10), (-10, H + 10)], (34, 30, 30, 255), lw=6)
    c.mottle(0.08, cell=10, seed=34)
    c.vignette(0.45)
    save_bg(c, "task_eject_valley_bg.jpg")

    st = C(260, 420)
    wood = (120, 84, 50, 255)
    for x0, x1 in ((50, 20), (210, 240)):
        st.line([(x0 + 10, 150), (x1, 410)], wood, 14)
    st.line([(40, 300), (220, 300)], wood, 10)
    st.rrect(20, 130, 240, 160, 4, (140, 98, 58, 255), lw=5, sh=(0.2, 0.3))          # Plattform
    st.rrect(30, 40, 50, 140, 3, wood, lw=4)
    st.rrect(210, 40, 230, 140, 3, wood, lw=4)
    st.rrect(20, 30, 240, 50, 4, (104, 72, 44, 255), lw=5)                          # Dach
    st.rrect(30, 90, 230, 104, 3, (140, 98, 58, 255), lw=4)                          # Gelaender
    st.save("task_eject_stand.png")

    f = C(1100, 200)
    for k in range(5):
        f.soft_poly([(-60, 60 + k * 14), (1160, 50 + k * 16), (1160, 170), (-60, 180)], (200, 208, 222, 70), 22)
    f.save("task_eject_fog.png")


if __name__ == "__main__":
    soft()
    top_band()
    tomb()
    depot()
    hall()
    night()
    river()
    forest()
    valley()
