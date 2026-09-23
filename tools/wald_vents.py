# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_vents.py - eigene Vent-Sprites der Forststation Nadelkamm (ersetzen das Skeld-Bodengitter).
#
# SCHNITTSTELLE (wie wald_consoles.render_all):
#   render_all(ppm) -> dict  "Vent/<id>" -> (PIL.Image RGBA, anchor_x_px, anchor_y_px)
#     anchor = Pixel im Bild (x von LINKS, y von UNTEN), das auf der Vent-Position landet.
#              Die Vent-Position ist die MITTE der Oeffnung (dort springt der Spieler hinein).
#   Rand: mindestens 6 px transparenter Rand ringsum (das Spiel zeichnet beim Hervorheben eine
#   rote/gelbe Kontur um die Silhouette; deshalb ist jedes Sprite EINE zusammenhaengende Form).
#   Die Vent-Liste kommt aus wald_vent_brief.json ([id, x, y, raum, building|clearing]).
#
# GESTALTUNG
# Gleiche schraege Aufsicht wie museum_art / wald_consoles (Hoehe h steigt um h * K, Licht von
# Nordwest, schwarze Umrisse, flache Flaechen, helle Nord-/Westkante, dunkle Sued-/Ostkante).
# Die Ein-/Ausstiegsanimation des Spiels laeuft auf diesen Sprites nicht, deshalb sind sie
# statisch "offen" gezeichnet:
#   Lichtung  : hohler Baumstumpf, niedrig (0,22 m), mit Wurzelansaetzen, Moos und Grasbueschel
#               (auf Erdwegen Kiesel statt Gras); das dunkle Loch in der Schnittflaeche ist die
#               Oeffnung (ca. 0,55 x 0,40 m), Gesamtbreite unter 1,0 m.
#   Gebaeude  : Bodenluke im Dielenboden: Balkenrahmen, dunkler Schacht mit sichtbarer Sprosse an
#               der Rueckwand, hochgeklappter Bretterdeckel mit Eisenbaendern, Nieten und Ring.

import json
from pathlib import Path

from PIL import ImageChops, ImageFilter

from museum_art import Canvas, OUTLINE, K, OUT_W, hexc, shade, alpha

# ------------------------------------------------------------------ Farben
# Palette uebernommen aus gen_wald.C, damit die Sprites zur Karte passen.
C = {
    "stamm": hexc("#5a3d24"), "stamm_dunkel": hexc("#3e2916"),
    "gras": hexc("#5d7d3c"), "gras3": hexc("#51702f"), "halm": hexc("#3f5e27"),
    "erde": hexc("#8a6a45"), "erde2": hexc("#7c5e3c"), "erde_rand": hexc("#6a4f33"), "kiesel": hexc("#a28a68"),
    "diele": hexc("#a8784a"), "diele_fuge": hexc("#6a4628"),
    "balken": hexc("#8a5d36"), "balken_dunkel": hexc("#6a4527"),
}

WOOD_L = hexc("#c9a46a")          # Schnittflaeche / frisches Holz
RING = hexc("#a9834f")            # Jahresringe
BARK = C["stamm"]
BARK_D = C["stamm_dunkel"]
BARK_L = hexc("#74522f")
HOLE = hexc("#0b0d10")            # Schachtgrund (praktisch schwarz)
HOLE_WALL = hexc("#2a1c10")       # sichtbare Rueckwand des Lochs
MOSS = hexc("#6f9a3e")
MOSS_D = hexc("#4f7a2c")
IRON = hexc("#4a5056")
IRON_L = hexc("#6a7278")
IRON_D = hexc("#2c3136")
LID = hexc("#b0804a")             # Deckelbretter (heller als der Rahmen, Licht faellt auf die Front)
LID_D = hexc("#5a3a1e")           # Bretterfugen
LID_L = hexc("#d0a26a")
RUNG = hexc("#8a6a45")

MARGIN = 0.12                     # transparenter Rand in m (>= 6 px ab 50 px/m)


ALPHA_MIN = 64                    # darunter wird Alpha auf 0 gesetzt (Schattenfahnen, Lanczos-Ringing)


def _result(c, ppm):
    img = c.finish()
    # Alles unter ALPHA_MIN entfernen: die Konturhervorhebung des Spiels folgt der Alphamaske,
    # weiche Schattenraender wuerden sonst als losgeloeste Inseln aufblitzen.
    a = img.getchannel("A")
    mask = a.point(lambda v: 255 if v >= ALPHA_MIN else 0)
    # 3x3-Oeffnen der Maske: einzelne Splitter am Schattenrand verschwinden, Halme (>= 4 px) bleiben
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    img.putalpha(ImageChops.multiply(a, mask))
    ax = (0 - c.x0) * ppm
    ay = (0 - c.y0) * ppm
    return img, int(round(ax)), int(round(ay))


def _tuft(c, x, y, s, col):
    """Kleines Grasbueschel (drei Halme)."""
    for dx, dy in ((-0.6, 1.0), (0.0, 1.35), (0.6, 1.0)):
        c.line([(x, y), (x + dx * s, y + dy * s)], fill=col, width=s * 0.35)


def _mushroom(c, x, y, s):
    """Kleiner Pilz am Stumpffuss (Stiel + Hut), haengt an der Silhouette."""
    c.line([(x, y), (x, y + s * 1.1)], fill=OUTLINE, width=s * 0.75)
    c.line([(x, y), (x, y + s * 1.1)], fill=hexc("#e8dcb4"), width=s * 0.4)
    c.ellipse(x, y + s * 1.15, s * 0.9, s * 0.55, fill=hexc("#b8583a"), outline=OUTLINE, width=0.02)
    c.ellipse(x - s * 0.3, y + s * 1.25, s * 0.18, s * 0.12, fill=hexc("#efe4c8"))


# ----------------------------------------------------------- Lichtung: Stumpf

def stump(ppm, seed=0, dirt=False):
    """Hohler Baumstumpf. Oeffnung (Loch in der Schnittflaeche) mittig auf (0, 0)."""
    h = 0.22                       # Stumpfhoehe
    rx, ry = 0.39, 0.27            # Aussenmass der Schnittflaeche (Ellipse, schraege Aufsicht)
    hx, hy = 0.25, 0.175           # Loch: ca. 0,50 x 0,35 m (Schnittflaeche bleibt als Ring sichtbar)
    cy = -h * K                    # Fussmitte, damit das Loch oben auf (0, 0) liegt
    w = 0.52
    c = Canvas(-w - MARGIN, cy - ry - 0.16 - MARGIN, w + MARGIN, ry + 0.16 + MARGIN, ppm)

    # Bodenschatten nach Suedost
    c.soft_shadow([(-rx + 0.08, cy - ry - 0.06), (rx + 0.1, cy - ry - 0.06), (rx + 0.1, cy + ry), (-rx + 0.08, cy + ry)], 85, 0.07)

    # Wurzelansaetze: Lappen rund um den Fuss, alle mit dem Rumpf verbunden (eine Silhouette)
    roots = [(-0.42, -0.03, 0.14, 0.07), (0.41, -0.07, 0.15, 0.07), (-0.23, -0.23, 0.14, 0.06),
             (0.19, -0.24, 0.15, 0.06), (-0.37, 0.15, 0.11, 0.055), (0.35, 0.16, 0.1, 0.055)]
    if seed % 2:
        roots = [(-u, v, a, b) for u, v, a, b in roots]
    for u, v, a, b in roots:
        c.ellipse(u, cy + v, a, b, fill=BARK_D, outline=OUTLINE, width=OUT_W)
    for u, v, a, b in roots:
        c.ellipse(u, cy + v, a, b, fill=BARK_D)
        c.ellipse(u, cy + v + 0.02, a * 0.7, b * 0.5, fill=BARK)

    # Rumpf: Fussellipse + Mantel + Deckflaeche
    c.ellipse(0, cy, rx, ry, fill=BARK, outline=OUTLINE, width=OUT_W)
    c.rect(-rx, cy, rx, cy + h * K, fill=BARK)
    c.line([(-rx, cy), (-rx, cy + h * K)], fill=OUTLINE, width=OUT_W)
    c.line([(rx, cy), (rx, cy + h * K)], fill=OUTLINE, width=OUT_W)
    # Rindenfurchen (senkrecht), dunkle Suedkante am Boden, Lichtkante links
    for i, u in enumerate((-0.31, -0.2, -0.09, 0.02, 0.13, 0.23, 0.32)):
        c.line([(u, cy - ry * 0.75 + abs(u) * 0.35), (u + 0.01, cy + h * K - 0.02)], fill=BARK_D, width=0.028 if i % 2 else 0.02)
    c.rect(-rx + 0.03, cy - ry + 0.02, rx - 0.03, cy - ry + 0.09, fill=alpha((0, 0, 0, 255), 60))
    c.line([(-rx + 0.035, cy - 0.02), (-rx + 0.035, cy + h * K - 0.02)], fill=BARK_L, width=0.02)
    c.line([(rx - 0.035, cy - 0.02), (rx - 0.035, cy + h * K - 0.02)], fill=alpha((0, 0, 0, 255), 70), width=0.02)

    # Deckflaeche: Rindenring, Schnittflaeche mit Jahresringen
    top = cy + h * K
    c.ellipse(0, top, rx, ry, fill=BARK, outline=OUTLINE, width=OUT_W)
    c.ellipse(0, top, rx - 0.045, ry - 0.035, fill=WOOD_L, outline=BARK_D, width=0.015)
    for f in (0.9, 0.8, 0.7):
        c.ellipse(0, top, (rx - 0.045) * f, (ry - 0.035) * f, outline=RING, width=0.012)
    # helle Nordwestkante, dunkle Suedostkante der Schnittflaeche
    c.ellipse(-0.03, top + 0.02, rx - 0.09, ry - 0.06, outline=alpha((255, 255, 255, 255), 70), width=0.014)
    c.ellipse(0.02, top - 0.015, rx - 0.07, ry - 0.05, outline=alpha((0, 0, 0, 255), 45), width=0.014)

    # Das Loch: dunkler Rand, sichtbare Rueckwand oben, schwarzer Grund
    c.ellipse(0, 0, hx, hy, fill=HOLE_WALL, outline=OUTLINE, width=0.035)
    c.ellipse(0, -0.045, hx * 0.93, hy * 0.82, fill=HOLE)
    c.ellipse(0.01, 0.0, hx * 0.55, hy * 0.35, fill=HOLE)
    # feine Risse vom Loch in die Schnittflaeche
    c.line([(hx * 0.8, hy * 0.5), (rx - 0.09, ry - 0.1)], fill=BARK_D, width=0.012)
    c.line([(-hx * 0.9, -hy * 0.2), (-rx + 0.08, -0.03)], fill=BARK_D, width=0.012)

    # Moos auf der Nordwestseite der Rinde und der Deckflaeche
    mx = -1 if seed % 2 == 0 else 1
    for u, v, a, b in ((mx * 0.28, top - 0.03, 0.08, 0.045), (mx * 0.32, top + 0.06, 0.055, 0.03),
                       (mx * 0.22, cy + 0.03, 0.07, 0.04)):
        c.ellipse(u, v, a, b, fill=MOSS)
        c.ellipse(u + 0.01, v - 0.012, a * 0.7, b * 0.6, fill=MOSS_D)

    # Bodenbewuchs: Gras auf Wiese, Kiesel auf dem Erdweg; alles am Fuss angedockt
    if dirt:
        # Kiesel ueberlappen die Wurzellappen, damit die Silhouette zusammenhaengt
        for i, (u, v) in enumerate(((-0.45, -0.08), (0.46, -0.1), (0.13, -0.28), (-0.19, -0.27))):
            c.ellipse(u, cy + v, 0.03, 0.02, fill=C["kiesel"] if i % 2 else C["erde2"], outline=OUTLINE, width=0.012)
    else:
        tufts = ((-0.46, -0.04), (0.46, -0.1), (-0.1, -0.29), (0.3, -0.27), (0.44, 0.13), (-0.42, 0.11))
        for u, v in tufts:
            _tuft(c, u, cy + v, 0.07, C["halm"])
        for u, v in tufts:
            _tuft(c, u, cy + v, 0.055, C["gras"])
    if seed % 3 != 1:
        _mushroom(c, 0.4 * (-mx), cy - 0.17, 0.055)
    return _result(c, ppm)


# ----------------------------------------------------------- Gebaeude: Luke

def hatch(ppm, seed=0):
    """Bodenluke im Dielenboden, Deckel nach Norden hochgeklappt. Oeffnung mittig auf (0, 0)."""
    ow, oh = 0.55, 0.40            # Oeffnung
    fb = 0.09                      # Rahmenbalken
    ft = 0.035                     # Rahmenhoehe (liegt auf dem Boden auf)
    x0, y0, x1, y1 = -ow / 2 - fb, -oh / 2 - fb, ow / 2 + fb, oh / 2 + fb
    lid_h = 0.30                   # sichtbare Hoehe des hochgeklappten Deckels
    c = Canvas(x0 - MARGIN, y0 - ft * K - 0.06 - MARGIN, x1 + MARGIN, y1 + ft * K + lid_h + 0.05 + MARGIN, ppm)

    # Schlagschatten nach Suedost (Rahmen + Deckel)
    c.soft_shadow([(x0 + 0.06, y0 - 0.07), (x1 + 0.08, y0 - 0.07), (x1 + 0.08, y1), (x0 + 0.06, y1)], 80, 0.06)

    # Deckel zuerst (liegt hinter dem Rahmen): Bretter senkrecht, Eisenbaender, Ring
    lx0, lx1 = -ow / 2 - 0.03, ow / 2 + 0.03
    ly0 = y1 - fb * 0.5 + ft * K
    ly1 = ly0 + lid_h
    c.rect(lx0, ly0, lx1, ly1, fill=LID, outline=OUTLINE, width=OUT_W)
    n = 3                          # 3 Bretter: die Fugen liegen zwischen den Eisenbaendern
    pw = (lx1 - lx0) / n
    for i in range(n):
        px0 = lx0 + pw * i
        # jedes Brett: Fuge rechts, Lichtkante links, Maserung
        if i:
            c.line([(px0, ly0 + 0.015), (px0, ly1 - 0.015)], fill=LID_D, width=0.022)
        c.line([(px0 + 0.03, ly0 + 0.04), (px0 + 0.03, ly1 - 0.05)], fill=LID_L, width=0.012)
        c.line([(px0 + pw * 0.4, ly1 - 0.08 - (i % 2) * 0.07), (px0 + pw * 0.75, ly1 - 0.075 - (i % 2) * 0.07)], fill=shade(LID, 0.78), width=0.01)
    # helle Nordkante, dunkle Ostkante
    c.line([(lx0 + 0.035, ly1 - 0.035), (lx1 - 0.035, ly1 - 0.035)], fill=LID_L, width=0.018)
    c.line([(lx1 - 0.035, ly0 + 0.03), (lx1 - 0.035, ly1 - 0.03)], fill=alpha((0, 0, 0, 255), 70), width=0.014)
    # Eisenbaender vom Scharnier nach oben, mit Nieten
    for sx in (lx0 + 0.11, lx1 - 0.11):
        c.rect(sx - 0.04, ly0 + 0.01, sx + 0.04, ly1 - 0.09, fill=IRON, outline=OUTLINE, width=0.02)
        c.poly([(sx - 0.04, ly1 - 0.09), (sx + 0.04, ly1 - 0.09), (sx, ly1 - 0.04)], fill=IRON, outline=OUTLINE, width=0.02)
        c.line([(sx - 0.022, ly0 + 0.03), (sx - 0.022, ly1 - 0.1)], fill=IRON_L, width=0.01)
        for yy in (ly0 + 0.06, ly0 + 0.14, ly1 - 0.13):
            c.ellipse(sx, yy, 0.013, 0.013, fill=IRON_L, outline=IRON_D, width=0.008)
    # Zugring in der Deckelmitte (Beschlagplatte + haengender Ring)
    rcy = ly0 + lid_h * 0.55
    c.rect(-0.045, rcy - 0.025, 0.045, rcy + 0.025, fill=IRON, outline=OUTLINE, width=0.015)
    c.ellipse(0, rcy - 0.07, 0.055, 0.05, outline=OUTLINE, width=0.05)
    c.ellipse(0, rcy - 0.07, 0.055, 0.05, outline=IRON_L, width=0.022)
    # Deckelstirn (Dicke) unten am Scharnier
    c.rect(lx0, ly0 - 0.02, lx1, ly0 + 0.012, fill=LID_D, outline=OUTLINE, width=0.02)

    # Rahmen: flacher Balkenkranz mit Suedkante (Hoehe ft)
    c.rect(x0, y0, x1, y0 + ft * K, fill=C["balken_dunkel"], outline=OUTLINE, width=OUT_W)
    c.rect(x0, y0 + ft * K, x1, y1 + ft * K, fill=C["balken"], outline=OUTLINE, width=OUT_W)
    top_off = ft * K
    ix0, iy0, ix1, iy1 = -ow / 2, -oh / 2 + top_off, ow / 2, oh / 2 + top_off
    # Balkenfugen an den Ecken (Gehrung)
    for (ax, ay, bx, by) in ((x0, y0 + top_off, ix0, iy0), (x1, y0 + top_off, ix1, iy0), (x0, y1 + top_off, ix0, iy1), (x1, y1 + top_off, ix1, iy1)):
        c.line([(ax, ay), (bx, by)], fill=C["balken_dunkel"], width=0.014)
    # helle Nord-/Westkante, dunkle Sued-/Ostkante des Rahmens
    c.line([(x0 + 0.035, y1 + top_off - 0.03), (x1 - 0.035, y1 + top_off - 0.03)], fill=shade(C["balken"], 1.3), width=0.016)
    c.line([(x0 + 0.03, y0 + top_off + 0.03), (x0 + 0.03, y1 + top_off - 0.03)], fill=shade(C["balken"], 1.25), width=0.012)
    c.line([(x1 - 0.03, y0 + top_off + 0.03), (x1 - 0.03, y1 + top_off - 0.03)], fill=alpha((0, 0, 0, 255), 60), width=0.012)

    # Scharniere auf dem Nordbalken
    for sx in (lx0 + 0.11, lx1 - 0.11):
        c.rect(sx - 0.045, y1 + top_off - fb * 0.75, sx + 0.045, y1 + top_off - fb * 0.2, fill=IRON, outline=OUTLINE, width=0.02)
        c.ellipse(sx, y1 + top_off - fb * 0.48, 0.012, 0.012, fill=IRON_L, outline=IRON_D, width=0.008)

    # Schacht: Rueckwand oben (sichtbar in schraeger Aufsicht) mit Sprosse, darunter schwarz
    c.rect(ix0, iy0, ix1, iy1, fill=HOLE_WALL, outline=OUTLINE, width=0.035)
    c.rect(ix0 + 0.02, iy0 + 0.02, ix1 - 0.02, iy1 - 0.13, fill=HOLE)
    c.line([(ix0 + 0.03, iy1 - 0.13), (ix1 - 0.03, iy1 - 0.13)], fill=alpha((0, 0, 0, 255), 120), width=0.03)
    # Leitersprossen an der Rueckwand (eine hell, eine tief im Schatten)
    c.line([(-0.16, iy1 - 0.07), (0.16, iy1 - 0.07)], fill=OUTLINE, width=0.04)
    c.line([(-0.16, iy1 - 0.07), (0.16, iy1 - 0.07)], fill=RUNG, width=0.02)
    c.line([(-0.16, iy1 - 0.17), (0.16, iy1 - 0.17)], fill=shade(RUNG, 0.45), width=0.018)
    for sx in (-0.16, 0.16):
        c.line([(sx, iy1 - 0.02), (sx, iy1 - 0.2)], fill=shade(RUNG, 0.6), width=0.016)
    # Innenkante des Rahmens (Lichtkante links/oben im Loch)
    c.line([(ix0 + 0.015, iy0 + 0.02), (ix0 + 0.015, iy1 - 0.02)], fill=alpha(C["balken"], 90), width=0.012)
    return _result(c, ppm)


# ----------------------------------------------------------------- Einstieg

DIRT_VENTS = {0}                   # Vents auf dem Erdweg (Hof) statt Wiese: Kiesel statt Gras


def render_all(ppm):
    brief = json.loads((Path(__file__).resolve().parent / "wald_vent_brief.json").read_text(encoding="utf-8"))
    out = {}
    for vid, _x, _y, _room, kind in brief:
        if kind == "clearing":
            out[f"Vent/{vid}"] = stump(ppm, seed=vid, dirt=vid in DIRT_VENTS)
        else:
            out[f"Vent/{vid}"] = hatch(ppm, seed=vid)
    return out


if __name__ == "__main__":
    for k, (im, ax, ay) in render_all(160).items():
        print(k, im.size, ax, ay)
