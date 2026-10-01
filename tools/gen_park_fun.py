# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_park_fun.py - Laufzeit-Sprites der Park-Attraktionen (User 01.10.: Hau den Lukas, Maskottchen-Kostuem,
# Riesenrad-Gondel, Achterbahn-Schnellreise) und ihre Use-Knopf-Symbole. Voller Pass 01.10.: alle Bilder
# im Among-Us-Stil (dicke dunkle Kontur, flache Flaechen mit Licht- und Schattenkante, Glanzpunkte).
#
# Bildvertrag (C#-Seite in AtlasParkFun.cs; wer die Bilder neu zeichnet, haelt Groesse und Drehpunkt ein):
#   task_park_lukas.png          140 x 340 px, 100 px/m, Drehpunkt unten Mitte auf der Standlinie (y 318)
#                                Puck-Bahn: Mitte x 70, von y 250 (unten) bis y 52 (Glocke)
#   task_park_lukas_puck.png     30 x 18 px, Drehpunkt Mitte
#   task_park_mascot_0/1.png     110 x 140 px, 100 px/m, Blick nach rechts, Fuesse auf y 134 (Drehpunkt)
#   task_park_wheel_ring.png     660 x 660 px, 100 px/m, Mitte = Nabe, Radius 3,0 m (Kranz bei 300 px)
#   task_park_gondola_{k}.png    90 x 100 px, Aufhaengepunkt (45, 6) = Drehpunkt, Rueckseite (hinter der Figur)
#   task_park_gondola_front_{k}.png  gleiche Geometrie, nur die Brustwehr (vor der Figur)
#   task_park_shuttle.png        130 x 116 px, 100 px/m, Draufsicht, Fahrtrichtung nach rechts
#   task_park_ridephoto.png      220 x 132 px, 100 px/m, Foto-Monitor der Geisterbahn (Bildflaeche x 14..206, y 22..106)
#   task_wald_canoe.png          280 x 90 px, 100 px/m, Draufsicht, Bug nach rechts (Forest-Kanu, AtlasFerry)
#   task_btn_*.png               256 x 256 px, Use-Knopf-Symbole (AtlasUse)
#
#   python tools/gen_park_fun.py              ->  assets/task_park_lukas*.png, task_park_mascot_*.png, ...
#   python tools/gen_park_fun.py --sheet NAME ->  tools/_vollpass_park/sprites_NAME.png (Abnahme-Blatt)

import math

from gen_tasks import C, INK, GOLD, CREAM, WHITE, STEEL_L, STEEL_D, dark, light, mix, label, font

RED, RED_L, RED_D = (200, 56, 62, 255), (232, 98, 98, 255), (146, 36, 44, 255)
PLUM, PLUM_L, PLUM_D = (106, 70, 150, 255), (142, 104, 186, 255), (70, 44, 104, 255)
TEAL, TEAL_D = (46, 146, 150, 255), (30, 100, 104, 255)
WOOD, WOOD_D, WOOD_L = (160, 104, 62, 255), (112, 70, 40, 255), (200, 146, 96, 255)
MOON, MOON_D, MOON_L = (250, 222, 120, 255), (214, 170, 70, 255), (255, 240, 180, 255)
BULB = (255, 234, 170, 255)
STEEL = (106, 90, 138, 255)
STEEL_LL = (150, 134, 186, 255)
GONDOLA = [RED, TEAL, GOLD]
SKY = (110, 180, 220, 255)


# ------------------------------------------------------------------ kleine Helfer (Mischen auf Ebenen)

def tpoly(c, pts, color):
    """Halbtransparentes Polygon (Licht-/Schattenband) korrekt gemischt (PIL-Falle: ohne Ebene stanzt es)."""
    c.soft_poly(pts, color, 0.01)


def trect(c, x0, y0, x1, y1, color):
    tpoly(c, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], color)


def tell(c, cx, cy, rx, ry, color):
    c.glow(cx, cy, rx, ry, color, 0.01)


def bulb(c, x, y, r=4, col=BULB, glow=True):
    if glow:
        c.glow(x, y, r * 3.2, r * 3.2, (255, 230, 150, 80), r * 1.2)
    c.ell(x, y, r, r, col, lw=max(2, r // 2))
    c.glint(x - r * 0.3, y - r * 0.3, r * 0.4, r * 0.3, 150)


# ------------------------------------------------------------------ Hau den Lukas

def lukas():
    """140 x 340: Holzsockel mit Schlagplatte (Puck ruht bei y 250), Turm mit Skala und Schiene (x 70),
    Glocke bei y 32 mit Lichthof, Seitenschild TEST YOUR STRENGTH, Gluehbirnen, Holzhammer angelehnt."""
    c = C(140, 340)
    c.ell(72, 324, 60, 11, (0, 0, 0, 80), lw=0)                                 # Bodenschatten
    # Sockel: Deckflaeche (K = 0,55) und rot/creme gestreifte Vorderseite, Standlinie y 318
    c.poly([(22, 248), (118, 248), (126, 270), (14, 270)], WOOD_L, lw=5)
    c.poly([(14, 270), (126, 270), (126, 318), (14, 318)], RED, lw=5, sh=(0.1, 0.25))
    for k in range(4):
        x0 = 18 + k * 27
        if k % 2:
            trect(c, x0, 273, x0 + 27, 315, (240, 230, 200, 230))
    c.line([(14, 270), (126, 270)], INK, 4)
    trect(c, 17, 272, 123, 278, (255, 255, 255, 70))                              # Lichtkante
    trect(c, 17, 310, 123, 316, (0, 0, 0, 70))                                    # Bodenschatten
    c.rrect(46, 251, 94, 267, 5, (46, 44, 52, 255), lw=4)                          # Schlagplatte
    c.ell(70, 259, 11, 4, (90, 88, 100, 255), lw=0)
    # Turm: Holzrahmen, cremefarbene Skalenflaeche, farbige Felder, Striche, Schiene
    c.rrect(50, 36, 90, 258, 6, WOOD_D, lw=5)
    c.rrect(56, 44, 84, 252, 3, CREAM, lw=3)
    bands = [(76, 196, 92, 255), (150, 206, 80, 255), (250, 210, 70, 255), (250, 150, 60, 255), RED]
    for k, col in enumerate(bands):
        y1 = 250 - k * 40
        c.rrect(59, y1 - 37, 81, y1 - 3, 2, col, lw=2)
    for k in range(10):
        y = 250 - k * 20
        c.line([(52, y), (58, y)], INK, 3)
        c.line([(82, y), (88, y)], INK, 3)
    label(c, 70, 62, "1000", 7, INK)
    label(c, 70, 242, "0", 7, INK)
    c.line([(70, 50), (70, 248)], (40, 36, 44, 255), 4)                            # Schiene
    c.line([(68, 50), (68, 248)], (255, 255, 255, 110), 1)
    for y in range(60, 250, 24):                                                   # Gluehbirnen am Rahmen
        bulb(c, 48, y, 3, glow=False)
        bulb(c, 92, y, 3, glow=False)
    # Glocke: Lichthof, Dom mit Lichtkante, Aufhaengung, Kloeppel
    c.glow(70, 32, 44, 36, (255, 226, 140, 110), 10)
    c.rrect(60, 4, 80, 16, 3, (70, 68, 78, 255), lw=4)
    c.ell(70, 30, 26, 20, GOLD, lw=5, sh=(0.12, 0.3))
    c.rrect(42, 42, 98, 52, 4, GOLD, lw=4)
    trect(c, 46, 44, 94, 47, (255, 255, 255, 90))
    c.ell(70, 52, 5, 4, (70, 68, 78, 255), lw=2)
    c.glint(60, 22, 9, 5, 150, rot=-20)
    # Seitenschild senkrecht
    c.rrect(14, 60, 46, 206, 6, PLUM, lw=4, sh=(0.1, 0.25))
    trect(c, 18, 64, 42, 68, (255, 255, 255, 60))
    for i, ch in enumerate("STRENGTH"):
        label(c, 30, 76 + i * 16, ch, 12, BULB)
    for yy in (62, 204):
        bulb(c, 30, yy, 3)
    # Hammer rechts angelehnt
    c.capsule((124, 314), (134, 212), 8, WOOD, lw=4, sh=(0.1, 0.3))
    c.rrect(114, 192, 140, 222, 5, (96, 96, 110, 255), lw=4, sh=(0.1, 0.3))
    c.glint(121, 199, 6, 3, 130, rot=-10)
    c.save("task_park_lukas.png")

    p = C(30, 18)
    p.rrect(2, 2, 28, 16, 5, RED_L, lw=3, sh=(0.12, 0.35))
    p.glint(9, 6, 6, 2, 170)
    p.save("task_park_lukas_puck.png")


# ------------------------------------------------------------------ Maskottchen "Moony"

def mascot(frame):
    """110 x 140, Fuesse auf y 134, Blick nach rechts: Plueschanzug in Crewmate-Form (Rucksack links),
    Mondsichel-Kopf mit Schlafmuetze, Sternknoepfe, Faeustlinge; frame 1 = Schritt (Beine versetzt, Hand winkt)."""
    c = C(110, 140)
    step = 6 if frame else 0
    c.ell(56, 134, 36, 6, (0, 0, 0, 80), lw=0)
    # Beine
    c.rrect(32 - step, 108, 52 - step, 134, 7, PLUM_D, lw=5)
    c.rrect(62 + step, 108, 82 + step, 134, 7, PLUM_D, lw=5)
    # Rucksack
    c.rrect(8, 60, 30, 110, 9, PLUM_D, lw=5, sh=(0.1, 0.25))
    # Koerper
    c.rrect(22, 44, 94, 122, 30, PLUM, lw=6, sh=(0.08, 0.28))
    c.mottle(0.05, cell=4, seed=7)
    tell(c, 58, 100, 18, 13, (170, 130, 210, 150))                                # heller Bauch
    for y in (78, 96):                                                              # Sternknoepfe
        pts = [(78 + math.cos(math.radians(90 + k * 36)) * (6 if k % 2 == 0 else 2.6), y - math.sin(math.radians(90 + k * 36)) * (6 if k % 2 == 0 else 2.6)) for k in range(10)]
        c.poly(pts, GOLD, lw=2)
    # Faeustlinge: rechts winkt im Schrittbild
    if frame:
        c.ell(98, 60, 9, 9, PLUM_L, lw=4)
    else:
        c.ell(96, 94, 9, 9, PLUM_L, lw=4)
    c.ell(14, 100, 8, 8, PLUM_L, lw=4)
    # Kopf: Mondsichel (offen nach rechts), Gesicht, Schlafmuetze mit Bommel
    c.ell(58, 40, 38, 34, MOON, lw=6, sh=(0.08, 0.28))
    c.ell(34, 32, 20, 24, (0, 0, 0, 0), lw=0)
    c.arc((14, 8, 54, 56), 40, 320, INK, 6)                                         # Innenkante der Sichel
    c.poly([(28, 16), (46, 4), (72, 14), (46, 24)], PLUM, lw=4, sh=(0.1, 0.2))      # Muetze
    c.ell(26, 14, 7, 7, WHITE, lw=3)
    c.arc((62, 28, 80, 40), 200, 340, INK, 4)                                       # geschlossenes Auge
    c.arc((58, 46, 90, 60), 20, 160, INK, 4)                                        # Grinsen
    tell(c, 84, 46, 7, 4, (255, 150, 150, 170))                                     # Wange
    c.glint(50, 20, 10, 5, 130, rot=-25)
    c.save(f"task_park_mascot_{frame}.png")


# ------------------------------------------------------------------ Riesenrad (dreht zur Laufzeit)

def wheel():
    """660 x 660: Doppelkranz (Aussenring bei 300 px, Innenring bei 272) mit Fachwerk dazwischen, 16 Speichen
    mit Zugring bei 150, 24 Gluehbirnen auf dem Aussenring, goldene Nabe. Ringe als Boegen (PIL-Falle)."""
    n, R, Ri = 660, 300, 272
    cx = cy = n // 2
    c = C(n, n)
    for k in range(16):                                                              # Speichen
        a = math.radians(k * 22.5)
        c.line([(cx, cy), (cx + Ri * math.cos(a), cy + Ri * math.sin(a))], INK, 8)
    for k in range(16):
        a = math.radians(k * 22.5)
        c.line([(cx, cy), (cx + Ri * math.cos(a), cy + Ri * math.sin(a))], STEEL, 4)
    c.arc((cx - 150, cy - 150, cx + 150, cy + 150), 0, 360, INK, 7)                   # Zugring
    c.arc((cx - 150, cy - 150, cx + 150, cy + 150), 0, 360, STEEL, 3)
    # Fachwerk zwischen den Kraenzen
    seg = 48
    pts = []
    for k in range(seg + 1):
        a = math.radians(k * 360 / seg)
        r = R - 3 if k % 2 == 0 else Ri + 3
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    c.line(pts, INK, 6)
    c.line(pts, STEEL, 3)
    for rr, w_ink, w_fill, col in ((R, 16, 9, STEEL), (Ri, 9, 4, STEEL)):
        c.arc((cx - rr, cy - rr, cx + rr, cy + rr), 0, 360, INK, w_ink)
        c.arc((cx - rr, cy - rr, cx + rr, cy + rr), 0, 360, col, w_fill)
    c.arc((cx - R - 1, cy - R - 1, cx + R + 1, cy + R + 1), 200, 340, STEEL_LL, 2)   # Lichtkante oben
    for k in range(24):                                                              # Gluehbirnen
        a = math.radians(k * 15)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        c.glow(x, y, 18, 18, (255, 230, 150, 90), 6)
    for k in range(24):
        a = math.radians(k * 15)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        c.ell(x, y, 6, 6, BULB, lw=3)
    c.ell(cx, cy, 34, 34, GOLD, lw=5, sh=(0.12, 0.3))                                 # Nabe
    c.ell(cx, cy, 10, 10, (70, 68, 78, 255), lw=3)
    c.glint(cx - 12, cy - 12, 8, 5, 150, rot=-30)
    c.save("task_park_wheel_ring.png")
    for k, col in enumerate(GONDOLA):
        g = C(90, 100)                                                               # Rueckseite
        g.line([(45, 6), (45, 30)], INK, 7)
        g.line([(45, 6), (45, 30)], STEEL, 3)
        g.ell(45, 6, 6, 6, GOLD, lw=3)
        g.poly([(6, 34), (84, 34), (76, 24), (14, 24)], CREAM, lw=4, sh=(0.1, 0.2))   # Dach
        g.rrect(28, 26, 62, 32, 2, RED, lw=2)
        g.rrect(12, 34, 78, 94, 7, dark(col, 0.7), lw=4)                              # Rueckwand
        g.rrect(18, 40, 72, 56, 4, mix(dark(col, 0.7), SKY, 0.45), lw=2)              # Fenster hinten
        g.rrect(16, 70, 74, 80, 3, dark(col, 0.55), lw=2)                             # Sitzbank
        g.rrect(10, 88, 80, 98, 5, dark(col, 0.5), lw=4)                              # Boden
        g.save(f"task_park_gondola_{k}.png")
        f = C(90, 100)                                                               # Brustwehr vor der Figur
        f.rrect(10, 58, 80, 96, 7, col, lw=4, sh=(0.12, 0.3))
        f.rrect(14, 60, 76, 68, 3, light(col, 0.3), lw=2)                             # Handlauf
        f.rrect(37, 74, 53, 88, 3, CREAM, lw=2)                                       # Nummernschild
        label(f, 45, 81, str(k + 1), 9, INK)
        f.glint(20, 64, 7, 2, 150)
        f.save(f"task_park_gondola_front_{k}.png")


# ------------------------------------------------------------------ Achterbahn-Pendelwagen

def shuttle():
    """130 x 116, Draufsicht, Fahrtrichtung rechts: Wagen mit Bugspitze, zwei Sitzmulden mit Buegeln,
    Scheinwerfer, Raeder an den Seiten, Zierstreifen, Startnummer."""
    c = C(130, 116)
    c.poly([(10, 14), (104, 14), (124, 58), (104, 102), (10, 102)], (0, 0, 0, 80), lw=0)
    for y0, y1 in ((4, 14), (102, 112)):                                            # Raeder
        for x in (26, 88):
            c.rrect(x - 9, y0, x + 9, y1, 3, (46, 44, 52, 255), lw=4)
    c.poly([(6, 10), (100, 10), (122, 56), (100, 102), (6, 102)], PLUM, lw=6, sh=(0.18, 0.3))
    tpoly(c, [(10, 14), (98, 14), (104, 26), (12, 26)], (255, 255, 255, 60))
    c.line([(12, 56), (104, 56)], GOLD, 3)                                           # Zierstreifen
    for x0, x1 in ((16, 54), (60, 96)):                                              # Sitzmulden
        c.rrect(x0, 24, x1, 90, 7, (46, 28, 66, 255), lw=4)
        c.rrect(x0 + 5, 30, x1 - 5, 84, 5, CREAM, lw=0)
        c.rrect(x0 + 6, 31, x1 - 6, 50, 4, (230, 220, 196, 255), lw=0)
        c.rrect(x0 + 8, 56, x1 - 8, 62, 2, (70, 68, 78, 255), lw=3)                  # Buegel
    c.ell(114, 56, 6, 12, BULB, lw=3)                                                # Scheinwerfer
    c.glow(124, 56, 18, 18, (255, 230, 150, 130), 6)
    c.rrect(100, 40, 110, 72, 3, RED, lw=3)                                           # Bugspitze
    label(c, 105, 56, "1", 10, CREAM)
    c.glint(20, 20, 14, 3, 120)
    c.save("task_park_shuttle.png")


# ------------------------------------------------------------------ Foto-Monitor der Geisterbahn

def ridephoto():
    """220 x 132: Roehrenmonitor in Pflaume, Bildflaeche x 14..206, y 22..106 bleibt dunkel (Figuren legt
    AtlasParkWorld darauf), Gluehbirnenrahmen oben, RIDE PHOTO unten mit Kamera-Symbol und REC-Punkt."""
    c = C(220, 132)
    c.rrect(4, 4, 216, 128, 12, PLUM_D, lw=6, sh=(0.1, 0.3))
    trect(c, 10, 8, 210, 14, (255, 255, 255, 50))
    c.rrect(12, 20, 208, 108, 6, (20, 18, 30, 255), lw=4)                             # Bildflaeche
    for y in range(26, 106, 4):                                                       # Scanlines
        trect(c, 15, y, 205, y + 1, (255, 255, 255, 9))
    tpoly(c, [(16, 24), (64, 24), (40, 40), (16, 40)], (255, 255, 255, 22))            # Glanz
    for x in range(22, 204, 20):                                                       # Gluehbirnenrahmen
        bulb(c, x, 12, 4, col=BULB if (x // 20) % 2 else (255, 170, 200, 255), glow=False)
    label(c, 110, 119, "RIDE PHOTO", 11, (255, 200, 120, 255))
    c.rrect(18, 113, 34, 125, 2, (60, 56, 70, 255), lw=3)                              # Kamera
    c.ell(26, 119, 4, 4, (120, 180, 220, 255), lw=2)
    c.ell(202, 119, 4, 4, RED, lw=2)                                                   # REC
    c.glow(202, 119, 9, 9, (255, 80, 80, 90), 3)
    c.save("task_park_ridephoto.png")


# ------------------------------------------------------------------ Kanu der Forest Station

def canoe():
    """280 x 90, Draufsicht, Bug rechts: Holzrumpf mit Dollbord, Spanten, drei Duchten, Paddel, Tauwerk."""
    c = C(280, 90)
    c.ell(142, 52, 132, 32, (0, 0, 0, 80), lw=0)
    hull = [(4, 45), (36, 16), (140, 8), (236, 14), (276, 45), (236, 76), (140, 82), (36, 74)]
    c.poly(hull, (176, 92, 52, 255), lw=6, sh=(0.18, 0.3))
    c.poly([(26, 45), (50, 24), (140, 20), (228, 24), (254, 45), (228, 66), (140, 70), (50, 66)], (122, 70, 40, 255), lw=4)
    c.grain(30, 22, 250, 68, 0.1, seed=11)
    for x in range(60, 240, 18):                                                       # Spanten
        c.line([(x, 24), (x, 66)], (104, 60, 34, 255), 2)
    tpoly(c, [(36, 18), (140, 10), (236, 16), (236, 22), (140, 16), (36, 24)], (255, 255, 255, 70))   # Dollbord-Lichtkante
    for x in (82, 140, 198):                                                           # Duchten
        c.rrect(x - 7, 22, x + 7, 68, 3, WOOD_L, lw=3)
        c.line([(x - 4, 26), (x - 4, 64)], (255, 255, 255, 80), 1)
    c.capsule((112, 30), (206, 62), 5, (212, 170, 110, 255), lw=3)                     # Paddel
    c.ell(214, 66, 13, 7, (212, 170, 110, 255), lw=3)
    for r in (10, 6):                                                                  # Tauwerk am Heck
        c.arc((40 - r, 45 - r, 40 + r, 45 + r), 0, 360, (236, 220, 180, 255), 3)
    c.glint(60, 28, 10, 3, 100)
    c.save("task_wald_canoe.png")


# ------------------------------------------------------------------ Use-Knopf-Symbole (256 px, Vanilla-Stil)

def btn_canoe():
    c = C(256, 256)
    for k in range(3):                                                                 # Wellen
        y = 196 + k * 18
        c.arc((20 + k * 10, y - 20, 236 - k * 10, y + 20), 200, 340, (110, 180, 220, 255), 9)
    c.poly([(14, 150), (58, 108), (198, 108), (242, 150), (198, 190), (58, 190)], (176, 92, 52, 255), lw=9, sh=(0.1, 0.3))
    c.poly([(52, 150), (78, 126), (178, 126), (204, 150), (178, 172), (78, 172)], (122, 70, 40, 255), lw=6)
    for x in (100, 156):
        c.rrect(x - 7, 128, x + 7, 170, 3, WOOD_L, lw=4)
    c.capsule((150, 30), (96, 176), 13, (212, 170, 110, 255), lw=8)
    c.ell(92, 194, 20, 34, (212, 170, 110, 255), lw=8)
    c.glint(62, 118, 12, 4, 130, rot=-15)
    c.save("task_btn_canoe.png")


def btn_lukas():
    c = C(256, 256)
    c.rrect(92, 36, 132, 226, 9, WOOD_D, lw=8)                                          # Turm
    c.rrect(100, 44, 124, 218, 4, CREAM, lw=4)
    for k, col in enumerate([(76, 196, 92, 255), (250, 210, 70, 255), RED]):
        c.rrect(103, 164 - k * 50, 121, 208 - k * 50, 3, col, lw=3)
    c.line([(112, 50), (112, 212)], (40, 36, 44, 255), 4)
    c.glow(112, 34, 46, 40, (255, 226, 140, 110), 10)
    c.ell(112, 34, 34, 26, GOLD, lw=8, sh=(0.12, 0.3))                                   # Glocke
    c.rrect(80, 46, 144, 60, 5, GOLD, lw=6)
    c.glint(98, 26, 11, 5, 150, rot=-20)
    c.rrect(60, 206, 164, 246, 8, RED, lw=8, sh=(0.1, 0.25))                              # Sockel
    c.rrect(100, 198, 124, 212, 3, RED_L, lw=4)                                            # Puck
    c.capsule((150, 238), (214, 112), 18, WOOD, lw=8, sh=(0.1, 0.25))                     # Hammer
    c.rrect(176, 72, 244, 122, 11, (100, 100, 116, 255), lw=8, sh=(0.1, 0.3))
    c.glint(190, 84, 12, 5, 140, rot=-10)
    c.save("task_btn_lukas.png")


def btn_costume():
    c = C(256, 256)
    c.line([(128, 10), (128, 38)], INK, 10)                                               # Buegelhaken
    c.arc((112, 2, 144, 34), 180, 360, INK, 9)
    c.rrect(56, 136, 200, 250, 44, PLUM, lw=9, sh=(0.08, 0.3))                             # Plueschkoerper
    for y in (190, 222):
        pts = [(166 + math.cos(math.radians(90 + k * 36)) * (11 if k % 2 == 0 else 4.6), y - math.sin(math.radians(90 + k * 36)) * (11 if k % 2 == 0 else 4.6)) for k in range(10)]
        c.poly(pts, GOLD, lw=3)
    c.ell(128, 96, 84, 76, MOON, lw=9, sh=(0.08, 0.3))                                     # Mondkopf
    c.ell(76, 82, 48, 58, (0, 0, 0, 0), lw=0)
    c.arc((28, 24, 124, 140), 40, 320, INK, 9)
    c.poly([(60, 40), (98, 18), (128, 48), (84, 54)], PLUM, lw=8, sh=(0.1, 0.2))           # Muetze
    c.ell(56, 36, 14, 14, WHITE, lw=7)
    c.arc((136, 74, 172, 100), 200, 340, INK, 8)
    c.arc((128, 112, 196, 144), 20, 160, INK, 8)
    tell(c, 188, 112, 12, 7, (255, 150, 150, 170))
    c.glint(104, 44, 14, 6, 140, rot=-25)
    c.save("task_btn_costume.png")


def btn_wheel():
    c = C(256, 256)
    cx, cy, R = 128, 110, 90
    c.line([(60, 248), (cx, cy)], INK, 18)
    c.line([(196, 248), (cx, cy)], INK, 18)
    c.line([(60, 248), (cx, cy)], STEEL, 9)
    c.line([(196, 248), (cx, cy)], STEEL, 9)
    for k in range(8):
        a = math.radians(k * 45)
        c.line([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))], INK, 10)
    for k in range(8):
        a = math.radians(k * 45)
        c.line([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))], STEEL, 5)
    c.arc((cx - R, cy - R, cx + R, cy + R), 0, 360, INK, 16)
    c.arc((cx - R, cy - R, cx + R, cy + R), 0, 360, STEEL, 8)
    c.arc((cx - R - 1, cy - R - 1, cx + R + 1, cy + R + 1), 200, 340, STEEL_LL, 3)
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        c.rrect(x - 17, y + 2, x + 17, y + 28, 6, GONDOLA[k % 3], lw=6, sh=(0.1, 0.3))
        c.rrect(x - 12, y + 4, x + 12, y + 10, 2, light(GONDOLA[k % 3], 0.3), lw=0)
    c.ell(cx, cy, 16, 16, GOLD, lw=6)
    c.glint(cx - 6, cy - 6, 5, 3, 150, rot=-30)
    c.save("task_btn_wheel.png")


def btn_coaster():
    c = C(256, 256)
    c.line([(12, 218), (244, 218)], STEEL_D, 14)                                            # Schiene
    for x in range(22, 244, 30):
        c.line([(x, 208), (x, 230)], WOOD_D, 9)
    c.poly([(150, 26), (226, 26), (226, 4), (254, 42), (226, 80), (226, 58), (150, 58)], GOLD, lw=8, sh=(0.1, 0.25))   # Pfeil
    c.rrect(36, 104, 212, 198, 28, RED, lw=9, sh=(0.1, 0.3))                                # Wagen
    c.rrect(44, 110, 204, 126, 6, RED_L, lw=0)
    for x0 in (62, 128):                                                                   # Sitze
        c.rrect(x0, 78, x0 + 56, 142, 12, (70, 26, 34, 255), lw=7)
        c.rrect(x0 + 8, 84, x0 + 48, 100, 5, CREAM, lw=0)
    c.line([(48, 160), (200, 160)], GOLD, 8)
    for x in (78, 174):
        c.ell(x, 206, 21, 21, (70, 70, 84, 255), lw=8)
        c.ell(x, 206, 7, 7, STEEL_L, lw=3)
    c.glint(60, 112, 14, 5, 120)
    c.save("task_btn_coaster.png")


SHEET = ["task_park_lukas.png", "task_park_lukas_puck.png", "task_park_mascot_0.png", "task_park_mascot_1.png",
         "task_park_wheel_ring.png", "task_park_gondola_0.png", "task_park_gondola_front_0.png", "task_park_gondola_1.png",
         "task_park_gondola_front_1.png", "task_park_gondola_2.png", "task_park_gondola_front_2.png", "task_park_shuttle.png",
         "task_park_ridephoto.png", "task_wald_canoe.png", "task_btn_lukas.png", "task_btn_costume.png", "task_btn_wheel.png",
         "task_btn_coaster.png", "task_btn_canoe.png"]


def sheet(stage="nachher"):
    """Abnahme-Blatt: alle Laufzeit-Sprites in Originalgroesse auf dunklem Grund (tools/_vollpass_park/)."""
    from PIL import Image, ImageDraw
    from gen_tasks import OUT
    out = OUT.parent / "tools" / "_vollpass_park"
    out.mkdir(exist_ok=True)
    ims = [(n, Image.open(OUT / n).convert("RGBA")) for n in SHEET if (OUT / n).exists()]
    pad, cols = 24, 6
    cw = max(im.width for _n, im in ims) + pad
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    W = cols * cw + pad
    H = sum(max(im.height for _n, im in r) + pad + 22 for r in rows) + pad
    bg = Image.new("RGBA", (W, H), (38, 36, 52, 255))
    d = ImageDraw.Draw(bg)
    f = font(13)
    y = pad
    for r in rows:
        rh = max(im.height for _n, im in r)
        for k, (n, im) in enumerate(r):
            x = pad + k * cw
            bg.alpha_composite(im, (x, y + rh - im.height))
            d.text((x, y + rh + 4), n.replace("task_", "").replace(".png", "") + f" {im.width}x{im.height}", font=f, fill=(200, 200, 210, 255))
        y += rh + pad + 22
    d.text((pad, 4), f"Laufzeit-Sprites ({stage}), Originalgroesse", font=f, fill=(255, 255, 255, 255))
    p = out / f"sprites_{stage}.png"
    bg.convert("RGB").save(p)
    print(p, bg.size)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--sheet":
        sheet(sys.argv[2])
        sys.exit(0)
    lukas()
    mascot(0); mascot(1)
    wheel()
    shuttle()
    canoe(); ridephoto()
    btn_lukas(); btn_costume(); btn_wheel(); btn_coaster(); btn_canoe()
    sheet("nachher")
