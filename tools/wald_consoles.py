# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_consoles.py - eigene Task-Bloecke (Konsolen-Sprites) der Forststation Nadelkamm.
#
# SCHNITTSTELLE (gen_wald.py und der C#-Builder verlassen sich darauf, identisch zu museum_consoles):
#   render_all(ppm) -> dict  schluessel -> (PIL.Image RGBA, anchor_x_px, anchor_y_px)
#     schluessel  = Konsolen-Schluessel aus wald_console_brief.json ("Room/Name/Id") oder einer der
#                   Sonderschluessel EmergencyButton, SurveillanceConsole, AdminTable, FreeplayLaptop
#     anchor      = Pixel im Bild (x von LINKS, y von UNTEN), das auf der Konsolen-Position landet.
#                   Standlinie des Blocks auf Hoehe des Ankers oder knapp darunter (z-Sortierung).
#   Fehlt ein Schluessel, behaelt die Konsole ihr Skeld-Bild.
#   Rand: mindestens 6 px transparenter Rand ringsum (das Hervorheben zeichnet eine Kontur).
#
# GESTALTUNG
# Gleiche schraege Aufsicht wie museum_art (Hoehe h steigt um h * K, Licht von Nordwest, schwarze
# Umrisse, flache Flaechen mit heller Ober- und dunkler Unterkante). Thema: Forschungs-/Forststation
# bei Nacht, Blockhuetten mit Dielenboden, Lichtungen mit Gras.
# Montagearten (Spalte "wall" in wald_console_brief.json):
#   Gebaeude  N  : Standschrank an der sichtbaren Nordwand, Bedienflaeche auf der VORDERSEITE
#             S  : flache Bodeneinheit vor der Suedwand, Bedienflaeche auf der DECKFLAECHE
#             E/W: schmaler Standschrank an der Seitenwand, Bedienflaeche als Pult (Deckflaeche)
#             -  : freistehendes Pult auf Holzpfosten
#   Lichtung  N  : Schautafel-Kasten auf zwei Pfosten vor dem Waldrand, Front nach Sueden, Erdsockel
#             sonst: Pfostenpult mit schraegem Kopf auf kleinem Erdsockel
# Designsprache je Task-Typ (in allen Raeumen gleich, nur Gehaeuse- und Zierfarbe je Bereich):
#   Divert Power      Holzkasten mit Messing-Messerschalter und Kontrolllampen
#   Download/Upload   robustes Feld-Datenterminal: Bernstein-Schirm, Antenne, Kippschalter
#   Fix Wiring        wetterfester Abzweigkasten (grau-gruen) mit offener Tuer und vier Adern
#   Garbage/Chute     Kompostklappe aus Holz mit Blattzeichen und Messinghebel
#   Swipe Card        Stations-Ausweisleser mit haengender Ausweiskarte
#   Fuel              Kanisterstation: Zapfsaeule mit Schlauch und rotem Kanister
#   Align/Calibrate   Messsaeule mit Rundinstrumenten
#   Chart Course      Kartentafel (Hoehenlinien, Route, Nadeln)
#   Stabilize         Theodolit auf Stativ mit Steuerkasten (Aussichtsfels)
#   Shields           Wetterstations-Panel (Sechseck-Taster, Barometer, Windfahne)
#   Clean Filter      Wasserfilter-Einheit (blaue Tonne, Rohre, Kurbel)
#   Inspect Sample    Feldmikroskop-Bank
#   MedScanner        Boden-Scannerring im Labor
#   Clear Asteroids   Spotter-Terminal (Fadenkreuz-Schirm, Joystick) am Hochsitz
#   Sabotage-Stationen rot/amber: Waldbrand-Handscanner, Wasser-Notfalltastaturen,
#   Sicherungsschrank mit Warnband, Funkgeraet am Mast.

import json
import math
from pathlib import Path

from PIL import Image

from museum_art import Canvas, Prop, OUTLINE, K, OUT_W, hexc, lift, shade, alpha

# ------------------------------------------------------------------ Farben
# Palette uebernommen aus gen_wald.C (Grundriss v6), damit die Bloecke zur Karte passen.
C = {
    "stamm": hexc("#5a3d24"), "stamm_dunkel": hexc("#3e2916"),
    "gras": hexc("#5d7d3c"), "gras3": hexc("#51702f"), "halm": hexc("#3f5e27"),
    "erde": hexc("#8a6a45"), "erde2": hexc("#7c5e3c"), "erde_rand": hexc("#6a4f33"), "kiesel": hexc("#a28a68"),
    "diele": hexc("#a8784a"), "diele_fuge": hexc("#6a4628"),
    "balken": hexc("#8a5d36"), "balken_dunkel": hexc("#6a4527"),
    "wasser": hexc("#2f6d9c"), "wasser_licht": hexc("#5b9fd0"),
    "fels": hexc("#7e8084"), "fels_dunkel": hexc("#5c5e62"),
    "metall": hexc("#6f7a82"), "rot": hexc("#a8403a"), "blech": hexc("#4f6f5a"),
}

WOOD = hexc("#9a6a3e")           # Objektholz (wie die Props in gen_wald)
WOOD_D = hexc("#6e4a2a")
WOOD_L = hexc("#c9a46a")         # frisches Holz / Schnittflaeche
AMBER = hexc("#e8a83c")
AMBER_DARK = hexc("#6e4612")
AMBER_HI = hexc("#ffd27a")
RED = hexc("#d84a4a")
RED_DARK = hexc("#7a2424")
GREEN = hexc("#57d98a")
GREEN_D = hexc("#3f9e6e")
BRASS = lift("#b08a3c", 1.3)
BRASS_HI = hexc("#e6c76a")
DARK = hexc("#2a2f35")
STEEL = hexc("#8b949a")
METAL = lift("#6f7a82", 1.25)    # wetterfestes Blech
OLIVE = lift("#4f5f3a", 1.35)    # Feldgeraete-Gehaeuse
BLUE = hexc("#3f7fb8")
WATER = lift("#2f6d9c", 1.35)
PAPER = hexc("#e8dcb4")
CREAM = hexc("#efe4c8")
WARN = hexc("#d4b13c")
WIRES = [hexc("#e05a3a"), hexc("#3f9fd8"), hexc("#e0b04a"), hexc("#e070b0")]

# Bereichstoene: Gehaeuse (body) und Zierfarbe (trim). Gebaeude = Holz, Lichtungen = Blech/Pfosten.
TINT = {
    "messe": (WOOD, hexc("#8a3a2e")),
    "feldstation": (WOOD, hexc("#6b8c45")),
    "labor": (lift("#b8bcc0", 1.1), hexc("#3f7fb8")),
    "saegewerk": (shade(WOOD, 0.92), WOOD_L),
    "lager": (hexc("#9a7a52"), hexc("#6e5234")),
    "bootshaus": (shade(WOOD, 0.97), hexc("#b8583a")),
    "wachstube": (shade(WOOD, 0.88), hexc("#3d5a6e")),
    "generator": (lift("#6f7a82", 1.15), WARN),
    "aussicht": (lift("#4f6f5a", 1.25), hexc("#8c9296")),
    "funkmast": (lift("#4f6f5a", 1.25), hexc("#b8bcc0")),
    "wassertank": (lift("#4f6f5a", 1.25), WATER),
    "hochsitz": (lift("#4f6f5a", 1.25), WOOD_D),
    "pumpe": (lift("#4f6f5a", 1.25), hexc("#e8e4da")),
    "bachsteg": (lift("#4f6f5a", 1.25), WATER),
    "-": (WOOD, BRASS),
}
CLEARINGS = {"aussicht", "funkmast", "wassertank", "hochsitz", "pumpe", "bachsteg"}


# ------------------------------------------------------------ Leinwand-Block

class Block:
    """Prop mit eigener, knapp bemessener Leinwand. Ursprung (0, 0) = Konsolen-Position."""

    PAD = 0.12
    PAD_SHADOW = 0.28

    def __init__(self, x0, y0, x1, y1, top_extra, ppm):
        self.p = Prop(x0, y0, x1, y1, 0, ppm)
        self.p.c = Canvas(x0 - self.PAD, y0 - self.PAD_SHADOW, x1 + self.PAD_SHADOW, y1 + top_extra + self.PAD, ppm)
        self.c = self.p.c
        self.ppm = ppm

    def box(self, *a, **kw):
        self.p.box(*a, **kw)

    def cyl(self, *a, **kw):
        self.p.cyl(*a, **kw)

    def shadow(self, x0, y0, x1, y1, a=90):
        self.c.soft_shadow([(x0 + 0.06, y0 - 0.08), (x1 + 0.09, y0 - 0.08), (x1 + 0.09, y1 - 0.04), (x0 + 0.06, y1 - 0.04)], a, 0.06)

    def result(self):
        img = self.c.finish()
        ax = (0 - self.c.x0) * self.ppm
        ay = (0 - self.c.y0) * self.ppm
        return img, int(round(ax)), int(round(ay))


def is_wood(col):
    """Holzgehaeuse bekommen Bretterfugen, Blech nicht."""
    r, g, b = col[:3]
    return r > g + 25 and g > b


def planks(c, r, col, step=0.11):
    """Waagerechte Bretterfugen auf einer Front- oder Deckflaeche."""
    x0, y0, x1, y1 = r
    yy = y0 + step
    while yy < y1 - 0.03:
        c.line([(x0 + 0.01, yy), (x1 - 0.01, yy)], fill=shade(col, 0.7), width=0.012)
        yy += step


def unit(b, x0, y0, x1, y1, h, body, w=OUT_W, shadow=True):
    """Standschrank: Schlagschatten, Kasten, Fussleiste, Bretterfugen bei Holz. Gibt (front, top)."""
    if shadow:
        b.shadow(x0, y0, x1, y1)
    b.box(x0, y0, x1, y1, 0, h, shade(body, 1.15), body, w=w)
    front_full = (x0 + 0.03, y0 + 0.07, x1 - 0.03, y0 + h * K - 0.03)
    if is_wood(body):
        planks(b.c, front_full, body)
    b.c.rect(x0 + 0.02, y0 + 0.015, x1 - 0.02, y0 + 0.06, fill=shade(body, 0.6))
    i = 0.04
    front = (x0 + i, y0 + 0.07, x1 - i, y0 + h * K - i)
    top = (x0 + i, y0 + h * K + i, x1 - i, y1 + h * K - i)
    return front, top


def base_patch(b, x0, y0, x1, y1):
    """Kleiner Erdsockel unter freistehenden Aussenbloecken (festgetretener Boden mit Kieseln)."""
    c = b.c
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    c.ellipse(cx + 0.05, cy - 0.04, rx, ry, fill=alpha((8, 10, 16, 255), 60))
    c.ellipse(cx, cy, rx, ry, fill=C["erde"], outline=C["erde_rand"], width=0.035)
    for i, (u, v) in enumerate(((-0.55, 0.3), (0.4, -0.35), (0.1, 0.55), (-0.2, -0.5), (0.6, 0.2))):
        c.ellipse(cx + u * rx, cy + v * ry, 0.025, 0.018, fill=C["kiesel"] if i % 2 else C["erde2"])


def post(b, px, py, h, col=WOOD_D, s=0.06):
    """Vierkant-Holzpfosten (Standflaeche s x s) mit heller Schnittflaeche oben."""
    b.box(px - s, py - s, px + s, py + s, 0, h, WOOD_L, col, w=0.03)


def bezel(c, r, fill=DARK, inset=0.0, w=0.025):
    x0, y0, x1, y1 = r
    c.rect(x0 + inset, y0 + inset, x1 - inset, y1 - inset, fill=fill, outline=OUTLINE, width=w)
    c.line([(x0 + inset + 0.02, y1 - inset - 0.02), (x1 - inset - 0.02, y1 - inset - 0.02)], fill=shade(fill, 1.4), width=0.012)


def lamp(c, x, y, r, col, on=True):
    c.ellipse(x, y, r, r, fill=col if on else shade(col, 0.35), outline=OUTLINE, width=0.012)
    if on:
        c.ellipse(x - r * 0.3, y + r * 0.3, r * 0.3, r * 0.3, fill=(255, 255, 255, 160))


def screen(c, r, base=AMBER_DARK, glowc=AMBER, strength=0.35):
    """Leuchtender Schirm mit Reflexstreifen."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=base, outline=OUTLINE, width=0.02)
    c.glow((x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 0.9, glowc, strength)
    c.line([(x0 + 0.03, y1 - 0.03), (x0 + 0.03 + (x1 - x0) * 0.3, y1 - 0.03)], fill=(255, 255, 255, 90), width=0.015)


def housing(c, r, col, w=0.025):
    """Gehaeuseplatte mit Lichtkante oben (Standard-Grund jeder Bedienflaeche)."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=col, outline=OUTLINE, width=w)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(col, 1.35), width=0.014)


def screws(c, r, col=STEEL):
    x0, y0, x1, y1 = r
    for px_, py_ in ((x0 + 0.03, y0 + 0.03), (x1 - 0.03, y0 + 0.03), (x0 + 0.03, y1 - 0.03), (x1 - 0.03, y1 - 0.03)):
        c.ellipse(px_, py_, 0.012, 0.012, fill=col, outline=OUTLINE, width=0.008)


def hazard_band(c, x0, y0, x1, y1):
    c.rect(x0, y0, x1, y1, fill=WARN)
    xx = x0
    while xx < x1:
        c.poly([(xx, y0), (min(x1, xx + 0.04), y0), (min(x1, xx + 0.08), y1), (min(x1, xx + 0.04), y1)], fill=hexc("#1e1e1e"))
        xx += 0.08
    c.rect(x0, y0, x1, y1, outline=OUTLINE, width=0.012)


def flame(c, x, y, s, col=hexc("#f08a2a")):
    """Kleines Flammensymbol (Waldbrand-Alarm)."""
    c.poly([(x - s, y - s), (x + s, y - s), (x + s * 0.4, y + s * 0.4), (x, y + s * 1.4), (x - s * 0.45, y + s * 0.3)],
           fill=col, outline=OUTLINE, width=0.01)
    c.poly([(x - s * 0.45, y - s * 0.9), (x + s * 0.45, y - s * 0.9), (x, y + s * 0.35)], fill=hexc("#ffd84a"))


def drop(c, x, y, s, col=hexc("#5b9fd0")):
    """Wassertropfen-Symbol."""
    c.poly([(x, y + s * 1.3), (x + s * 0.75, y + s * 0.2), (x + s * 0.55, y - s * 0.5), (x, y - s * 0.7),
            (x - s * 0.55, y - s * 0.5), (x - s * 0.75, y + s * 0.2)], fill=col, outline=OUTLINE, width=0.01)
    c.ellipse(x - s * 0.25, y - s * 0.1, s * 0.15, s * 0.2, fill=(255, 255, 255, 170))


def leaf(c, x, y, s, col=GREEN_D):
    c.poly([(x - s, y - s * 0.6), (x - s * 0.3, y + s * 0.5), (x + s * 0.6, y + s * 0.8), (x + s, y - s * 0.2), (x + s * 0.2, y - s * 0.9)],
           fill=col, outline=OUTLINE, width=0.01)
    c.line([(x - s * 0.8, y - s * 0.5), (x + s * 0.7, y + s * 0.6)], fill=shade(col, 0.6), width=0.01)


def shrink(r, dx, dy=None):
    dy = dx if dy is None else dy
    return (r[0] + dx, r[1] + dy, r[2] - dx, r[3] - dy)


def fit(r, w, h):
    """Rechteck w x h mittig in r."""
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    w = min(w, r[2] - r[0]); h = min(h, r[3] - r[1])
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


# ------------------------------------------------------- Bedienflaechen

def face_divert(c, r, body, trim):
    """Holz-Sicherungskasten: dunkle Tafel, Messing-Messerschalter mit rotem Knauf, Lampen, Schild."""
    x0, y0, x1, y1 = r
    housing(c, r, WOOD)
    planks(c, r, WOOD, 0.1)
    inner = shrink(r, 0.045)
    c.rect(*inner, fill=DARK, outline=OUTLINE, width=0.012)
    screws(c, inner, BRASS)
    ix0, iy0, ix1, iy1 = inner
    cx = (ix0 + ix1) / 2
    # Messerschalter: zwei Messingkontakte oben, Drehpunkt unten, Hebel schraeg (halb geschlossen)
    for dx in (-0.06, 0.06):
        c.rect(cx + dx - 0.02, iy1 - 0.07, cx + dx + 0.02, iy1 - 0.03, fill=BRASS, outline=OUTLINE, width=0.01)
    piv = (cx, iy0 + 0.07)
    c.ellipse(piv[0], piv[1], 0.028, 0.028, fill=BRASS, outline=OUTLINE, width=0.012)
    tip = (cx + 0.09, iy1 - 0.05)
    c.line([piv, tip], fill=OUTLINE, width=0.045)
    c.line([piv, tip], fill=BRASS_HI, width=0.024)
    c.ellipse(tip[0], tip[1], 0.03, 0.03, fill=RED, outline=OUTLINE, width=0.012)
    c.ellipse(tip[0] - 0.008, tip[1] + 0.008, 0.009, 0.009, fill=(255, 255, 255, 170))
    # Lampen links, Schild rechts
    lamp(c, ix0 + 0.04, iy0 + 0.045, 0.02, AMBER_HI)
    lamp(c, ix0 + 0.04, iy0 + 0.1, 0.02, GREEN, on=False)
    c.rect(ix1 - 0.11, iy0 + 0.03, ix1 - 0.03, iy0 + 0.075, fill=CREAM, outline=OUTLINE, width=0.01)
    c.line([(ix1 - 0.095, iy0 + 0.052), (ix1 - 0.045, iy0 + 0.052)], fill=RED, width=0.012)


def face_data(c, r, body, trim, upload=True):
    """Feld-Datenterminal: olivgruenes Gehaeuse, Bernstein-Schirm, Antenne, Kippschalter, LEDs."""
    x0, y0, x1, y1 = r
    housing(c, r, OLIVE)
    screws(c, r)
    s = (x0 + 0.05, y0 + (y1 - y0) * 0.38, x1 - 0.05, y1 - 0.06)
    screen(c, s)
    sx0, sy0, sx1, sy1 = s
    for i in range(3):
        yy = sy1 - 0.06 - i * 0.045
        c.line([(sx0 + 0.04, yy), (sx0 + 0.04 + (sx1 - sx0) * (0.55 - i * 0.12), yy)], fill=AMBER_HI, width=0.014)
    c.rect(sx0 + 0.04, sy0 + 0.04, sx1 - 0.04, sy0 + 0.085, fill=shade(AMBER_DARK, 0.6), outline=AMBER, width=0.01)
    c.rect(sx0 + 0.045, sy0 + 0.045, sx0 + 0.045 + (sx1 - sx0 - 0.09) * 0.6, sy0 + 0.08, fill=AMBER_HI)
    ax_, ay_ = sx1 - 0.075, sy1 - 0.085
    if upload:
        c.poly([(ax_ - 0.03, ay_ - 0.01), (ax_ + 0.03, ay_ - 0.01), (ax_, ay_ + 0.035)], fill=AMBER_HI)
    else:
        c.poly([(ax_ - 0.03, ay_ + 0.03), (ax_ + 0.03, ay_ + 0.03), (ax_, ay_ - 0.015)], fill=AMBER_HI)
    # Antenne oben rechts (ragt ueber das Gehaeuse)
    c.line([(x1 - 0.05, y1 - 0.02), (x1 - 0.02, y1 + 0.09)], fill=OUTLINE, width=0.03)
    c.line([(x1 - 0.05, y1 - 0.02), (x1 - 0.02, y1 + 0.09)], fill=STEEL, width=0.014)
    c.ellipse(x1 - 0.02, y1 + 0.09, 0.012, 0.012, fill=DARK, outline=OUTLINE, width=0.008)
    # Kippschalter + LEDs + Kartenschlitz
    ky = y0 + (y1 - y0) * 0.2
    for i in range(2):
        kx = x0 + 0.08 + i * 0.07
        c.ellipse(kx, ky, 0.022, 0.022, fill=DARK, outline=OUTLINE, width=0.01)
        c.line([(kx, ky), (kx + (0.018 if i else -0.018), ky + 0.035)], fill=STEEL, width=0.014)
    lamp(c, x1 - 0.07, ky + 0.02, 0.018, GREEN)
    lamp(c, x1 - 0.11, ky + 0.02, 0.018, RED, on=False)
    c.rect(x0 + 0.06, y0 + 0.03, x1 - 0.06, y0 + 0.055, fill=hexc("#101216"), outline=shade(DARK, 1.5), width=0.01)


def face_wiring(c, r, body, trim):
    """Abzweigkasten: grau-gruenes Blech, offene Tuer rechts, vier Adern mit Bruchstelle."""
    x0, y0, x1, y1 = r
    box_c = METAL
    housing(c, r, box_c)
    inner = shrink(r, 0.04)
    c.rect(*inner, fill=hexc("#1f2428"))
    ix0, iy0, ix1, iy1 = inner
    n = 4
    for i in range(n):
        yy = iy1 - (i + 0.5) * (iy1 - iy0) / n
        col = WIRES[i]
        c.line([(ix0 + 0.01, yy), (ix0 + (ix1 - ix0) * 0.42, yy)], fill=col, width=0.022)
        c.line([(ix0 + (ix1 - ix0) * 0.58, yy), (ix1 - 0.01, yy)], fill=WIRES[(i * 3 + 1) % n], width=0.022)
        c.ellipse(ix0 + (ix1 - ix0) * 0.42, yy, 0.014, 0.014, fill=shade(col, 1.25))
    dw = (x1 - x0) * 0.55
    c.poly([(x1, y0 + 0.01), (x1 + dw, y0 + 0.06), (x1 + dw, y1 - 0.06), (x1, y1 - 0.01)],
           fill=shade(box_c, 0.85), outline=OUTLINE, width=0.022)
    c.line([(x1 + 0.03, y1 - 0.02), (x1 + dw - 0.02, y1 - 0.07)], fill=shade(box_c, 1.2), width=0.012)
    c.rect(x1 + dw - 0.06, (y0 + y1) / 2 - 0.03, x1 + dw - 0.035, (y0 + y1) / 2 + 0.03, fill=DARK)
    tx, ty = x1 + dw / 2, (y0 + y1) / 2
    c.poly([(tx - 0.045, ty - 0.035), (tx + 0.045, ty - 0.035), (tx, ty + 0.045)], fill=WARN, outline=OUTLINE, width=0.012)
    c.line([(tx + 0.008, ty + 0.02), (tx - 0.008, ty - 0.002), (tx + 0.008, ty - 0.005), (tx - 0.006, ty - 0.025)], fill=DARK, width=0.008)


def face_garbage(c, r, body, trim):
    """Kompostklappe: Holzrahmen, dunkle Klappe mit Griff und Blattzeichen, Messinghebel mit rotem Knauf."""
    x0, y0, x1, y1 = r
    housing(c, r, WOOD)
    planks(c, r, WOOD, 0.1)
    fx1 = x1 - 0.16
    flap = (x0 + 0.05, y0 + 0.08, fx1, y1 - 0.06)
    c.rect(*flap, fill=hexc("#3a4046"), outline=OUTLINE, width=0.02)
    c.line([(flap[0] + 0.02, flap[3] - 0.02), (flap[2] - 0.02, flap[3] - 0.02)], fill=hexc("#5a636a"), width=0.012)
    c.rect(flap[0] + 0.04, flap[3] - 0.08, flap[2] - 0.04, flap[3] - 0.055, fill=hexc("#5a636a"), outline=OUTLINE, width=0.01)
    mx, my = (flap[0] + flap[2]) / 2, (flap[1] + flap[3]) / 2 - 0.03
    leaf(c, mx, my, 0.045)
    # Hebel in einer Kulisse
    hx = x1 - 0.085
    c.rect(hx - 0.02, y0 + 0.07, hx + 0.02, y1 - 0.07, fill=hexc("#1f2428"), outline=OUTLINE, width=0.012)
    c.line([(hx, y0 + 0.14), (hx + 0.045, y1 - 0.08)], fill=OUTLINE, width=0.05)
    c.line([(hx, y0 + 0.14), (hx + 0.045, y1 - 0.08)], fill=BRASS, width=0.028)
    c.ellipse(hx + 0.045, y1 - 0.08, 0.032, 0.032, fill=RED, outline=OUTLINE, width=0.015)
    c.ellipse(hx + 0.035, y1 - 0.07, 0.01, 0.01, fill=(255, 255, 255, 170))


def face_keypad(c, r, body, trim, red=False):
    """Zahlentastatur mit Display; rot = Wasser-Notfalltastatur (Sabotage), sonst Ventil-Freigabe."""
    x0, y0, x1, y1 = r
    housing(c, r, RED_DARK if red else DARK)
    h = y1 - y0
    disp = (x0 + 0.05, y1 - h * 0.28, x1 - 0.05, y1 - 0.05)
    screen(c, disp, base=AMBER_DARK, strength=0.3)
    for i in range(4):
        c.rect(disp[0] + 0.035 + i * 0.05, disp[1] + 0.03, disp[0] + 0.06 + i * 0.05, disp[3] - 0.03, fill=AMBER_HI)
    kx0, ky0, kx1, ky1 = x0 + 0.06, y0 + 0.05, x1 - 0.06, y1 - h * 0.32
    cw, ch = (kx1 - kx0) / 3, (ky1 - ky0) / 4
    for i in range(3):
        for j in range(4):
            kx, ky = kx0 + i * cw, ky0 + j * ch
            col = (RED if (i, j) == (2, 0) else (GREEN if (i, j) == (0, 0) else hexc("#e8e0d0")))
            c.rect(kx + 0.008, ky + 0.008, kx + cw - 0.008, ky + ch - 0.008, fill=col, outline=OUTLINE, width=0.01)
    if red:
        drop(c, x0 + 0.05, y1 - 0.035, 0.02)
        lamp(c, x1 - 0.045, y1 - 0.03, 0.02, RED)
        c.glow((x0 + x1) / 2, y1 - 0.03, 0.2, RED, 0.35)
    else:
        # Ventilrad-Symbol (Verteiler freigeben)
        vx, vy = x1 - 0.045, y1 - 0.035
        c.ellipse(vx, vy, 0.02, 0.02, outline=STEEL, width=0.008)
        for a in range(0, 180, 60):
            c.line([(vx - 0.02 * math.cos(math.radians(a)), vy - 0.02 * math.sin(math.radians(a))),
                    (vx + 0.02 * math.cos(math.radians(a)), vy + 0.02 * math.sin(math.radians(a)))], fill=STEEL, width=0.006)


def face_hand(c, r, body, trim):
    """Waldbrand-Alarm-Handscanner: rotes Gehaeuse, Flammenzeichen, Bernstein-Scheibe mit Handsilhouette."""
    x0, y0, x1, y1 = r
    housing(c, r, RED_DARK)
    s = (x0 + 0.045, y0 + 0.07, x1 - 0.045, y1 - 0.1)
    screen(c, s, base=hexc("#5a3a0e"), strength=0.4)
    sx0, sy0, sx1, sy1 = s
    cx = (sx0 + sx1) / 2
    hw = (sx1 - sx0) * 0.28
    palm_y = sy0 + (sy1 - sy0) * 0.36
    c.ellipse(cx, palm_y, hw, (sy1 - sy0) * 0.26, fill=AMBER_HI)
    for fx, fl in ((-0.75, 0.55), (-0.3, 0.95), (0.15, 1.0), (0.6, 0.85)):
        c.line([(cx + fx * hw, palm_y + 0.02), (cx + fx * hw * 1.05, palm_y + (sy1 - sy0) * 0.45 * fl)], fill=AMBER_HI, width=hw * 0.42)
    c.line([(cx - hw * 0.9, palm_y - 0.03), (cx - hw * 1.55, palm_y + (sy1 - sy0) * 0.18)], fill=AMBER_HI, width=hw * 0.4)
    c.line([(sx0 + 0.02, palm_y + 0.05), (sx1 - 0.02, palm_y + 0.05)], fill=(255, 255, 255, 130), width=0.012)
    lamp(c, (x0 + x1) / 2 - 0.05, y0 + 0.035, 0.02, RED)
    lamp(c, (x0 + x1) / 2 + 0.05, y0 + 0.035, 0.02, GREEN, on=False)
    flame(c, x0 + 0.055, y1 - 0.05, 0.022)
    c.rect(x0 + 0.1, y1 - 0.07, x1 - 0.04, y1 - 0.035, fill=RED, outline=OUTLINE, width=0.01)
    c.glow((x0 + x1) / 2, y1 - 0.05, 0.25, RED, 0.3)


def face_fuse(c, r, body, trim):
    """Sicherungsschrank (Licht-Sabotage): Blechfront mit rotem Rahmen, Warnband, Blitzschild, Griff."""
    x0, y0, x1, y1 = r
    col = METAL
    housing(c, r, col)
    c.rect(x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03, outline=RED, width=0.02)
    hazard_band(c, x0 + 0.05, y0 + 0.06, x1 - 0.05, y0 + 0.13)
    tx, ty = (x0 + x1) / 2, (y0 + y1) / 2 + 0.06
    c.poly([(tx - 0.075, ty - 0.06), (tx + 0.075, ty - 0.06), (tx, ty + 0.07)], fill=WARN, outline=OUTLINE, width=0.015)
    c.line([(tx + 0.014, ty + 0.03), (tx - 0.012, ty - 0.005), (tx + 0.012, ty - 0.01), (tx - 0.01, ty - 0.045)], fill=DARK, width=0.012)
    c.rect(x1 - 0.085, ty - 0.05, x1 - 0.06, ty + 0.05, fill=DARK, outline=OUTLINE, width=0.01)
    lamp(c, x0 + 0.08, y1 - 0.075, 0.02, RED)
    lamp(c, x0 + 0.135, y1 - 0.075, 0.02, AMBER_HI)
    c.glow(x0 + 0.1, y1 - 0.075, 0.18, RED, 0.35)


def face_gauges(c, r, body, trim):
    """Verteiler-Kalibrierung: drei Zeigerinstrumente auf Blech, Drehknoepfe, Bernstein-Anzeige."""
    x0, y0, x1, y1 = r
    housing(c, r, METAL)
    screws(c, r)
    n = 3
    gw = (x1 - x0) / n
    for i in range(n):
        gx = x0 + gw * (i + 0.5)
        gy = y1 - 0.12
        rr = min(gw * 0.36, 0.085)
        c.ellipse(gx, gy, rr, rr, fill=CREAM, outline=OUTLINE, width=0.018)
        for a in range(200, 341, 35):
            ang = math.radians(a)
            c.line([(gx + math.cos(ang) * rr * 0.65, gy - math.sin(ang) * rr * 0.65), (gx + math.cos(ang) * rr * 0.85, gy - math.sin(ang) * rr * 0.85)], fill=DARK, width=0.01)
        c.poly([(gx + math.cos(math.radians(300)) * rr * 0.4, gy - math.sin(math.radians(300)) * rr * 0.4),
                (gx - math.cos(math.radians(300)) * rr * 0.4, gy + math.sin(math.radians(300)) * rr * 0.4),
                (gx, gy + rr * 0.15)], fill=RED)
        ang = math.radians(215 + i * 55)
        c.line([(gx, gy), (gx + math.cos(ang) * rr * 0.8, gy - math.sin(ang) * rr * 0.8)], fill=DARK, width=0.014)
        c.ellipse(gx, gy, 0.012, 0.012, fill=DARK)
        c.ellipse(gx, y0 + 0.07, 0.03, 0.03, fill=DARK, outline=OUTLINE, width=0.012)
        c.line([(gx, y0 + 0.07), (gx + math.cos(ang) * 0.025, y0 + 0.07 + math.sin(ang) * 0.025)], fill=AMBER_HI, width=0.01)
    c.rect(x0 + 0.05, y0 + 0.13, x1 - 0.05, y0 + 0.19, fill=AMBER_DARK, outline=OUTLINE, width=0.012)
    c.line([(x0 + 0.07, y0 + 0.16), (x0 + 0.07 + (x1 - x0 - 0.14) * 0.55, y0 + 0.16)], fill=AMBER_HI, width=0.018)


def topo(c, r, route=True):
    """Kartenblatt: Papier mit Hoehenlinien, Bach, Route mit Nadeln, Nordpfeil."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=PAPER, outline=OUTLINE, width=0.015)
    w, h = x1 - x0, y1 - y0
    for k, (u, v, rx, ry) in enumerate(((0.3, 0.55, 0.22, 0.16), (0.3, 0.55, 0.15, 0.1), (0.3, 0.55, 0.08, 0.05),
                                        (0.75, 0.35, 0.18, 0.14), (0.75, 0.35, 0.1, 0.07))):
        c.ellipse(x0 + w * u, y0 + h * v, w * rx, h * ry, outline=hexc("#8a7a4a"), width=0.008)
    c.line([(x0 + 0.02, y0 + h * 0.15), (x0 + w * 0.4, y0 + h * 0.25), (x0 + w * 0.7, y0 + h * 0.1), (x1 - 0.02, y0 + h * 0.2)],
           fill=hexc("#5b9fd0"), width=0.012)
    for u, v in ((0.15, 0.8), (0.55, 0.7), (0.85, 0.75)):
        c.rect(x0 + w * u - 0.012, y0 + h * v - 0.01, x0 + w * u + 0.012, y0 + h * v + 0.01, fill=WOOD_D)
    if route:
        pts = [(x0 + w * 0.15, y0 + h * 0.8), (x0 + w * 0.4, y0 + h * 0.5), (x0 + w * 0.6, y0 + h * 0.6), (x0 + w * 0.85, y0 + h * 0.3)]
        c.line(pts, fill=RED, width=0.012)
        for i, (px_, py_) in enumerate(pts):
            c.ellipse(px_, py_, 0.014, 0.014, fill=RED if i in (0, 3) else AMBER, outline=OUTLINE, width=0.008)
    c.line([(x1 - 0.05, y1 - 0.09), (x1 - 0.05, y1 - 0.03)], fill=DARK, width=0.01)
    c.poly([(x1 - 0.065, y1 - 0.06), (x1 - 0.035, y1 - 0.06), (x1 - 0.05, y1 - 0.025)], fill=DARK)


def face_chart(c, r, body, trim):
    """Kartentafel (Chart Course): Holzrahmen mit Kartenblatt, Route, Nadeln."""
    x0, y0, x1, y1 = r
    housing(c, r, WOOD)
    planks(c, r, WOOD, 0.1)
    topo(c, shrink(r, 0.04))
    for px_, py_ in ((x0 + 0.06, y1 - 0.06), (x1 - 0.06, y1 - 0.06)):
        c.ellipse(px_, py_, 0.014, 0.014, fill=BRASS, outline=OUTLINE, width=0.008)


def face_spotter(c, r, body, trim):
    """Spotter-Terminal (Clear Asteroids): dunkler Schirm mit Fadenkreuz und Zielmarken, Joystick."""
    x0, y0, x1, y1 = r
    housing(c, r, OLIVE)
    screws(c, r)
    s = (x0 + 0.05, y0 + (y1 - y0) * 0.36, x1 - 0.05, y1 - 0.05)
    screen(c, s, base=hexc("#1e3a2a"), glowc=GREEN, strength=0.3)
    sx0, sy0, sx1, sy1 = s
    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    c.line([(cx, sy0 + 0.02), (cx, sy1 - 0.02)], fill=alpha(GREEN, 150), width=0.008)
    c.line([(sx0 + 0.02, cy), (sx1 - 0.02, cy)], fill=alpha(GREEN, 150), width=0.008)
    c.ellipse(cx, cy, 0.07, 0.06, outline=alpha(GREEN, 200), width=0.01)
    for u, v in ((0.25, 0.7), (0.7, 0.3), (0.8, 0.75)):
        bx, by = sx0 + (sx1 - sx0) * u, sy0 + (sy1 - sy0) * v
        c.line([(bx - 0.025, by), (bx, by + 0.012), (bx + 0.025, by)], fill=AMBER_HI, width=0.012)
    jx, jy = (x0 + x1) / 2, y0 + (y1 - y0) * 0.17
    c.ellipse(jx, jy, 0.05, 0.03, fill=hexc("#1f2428"), outline=OUTLINE, width=0.012)
    c.line([(jx, jy), (jx + 0.02, jy + 0.08)], fill=OUTLINE, width=0.035)
    c.line([(jx, jy), (jx + 0.02, jy + 0.08)], fill=STEEL, width=0.018)
    c.ellipse(jx + 0.02, jy + 0.09, 0.025, 0.025, fill=RED, outline=OUTLINE, width=0.012)
    for i in range(2):
        c.ellipse(x1 - 0.09 + i * 0.045, jy, 0.018, 0.018, fill=AMBER_HI if i else GREEN, outline=OUTLINE, width=0.01)


def face_weather(c, r, body, trim):
    """Wetterstations-Panel (Prime Shields): Sechseck-Taster (rot = offen), Barometer, Windfahne."""
    x0, y0, x1, y1 = r
    housing(c, r, METAL)
    screws(c, r)
    cx, cy = (x0 + x1) / 2 - 0.05, (y0 + y1) / 2 + 0.01
    rr = 0.036
    cells = [(0, 0)] + [(math.cos(math.radians(a)) * rr * 2.1, math.sin(math.radians(a)) * rr * 2.1) for a in range(0, 360, 60)]
    for i, (dx, dy) in enumerate(cells):
        hx, hy = cx + dx, cy + dy
        col = RED if i in (1, 3, 5) else AMBER_HI
        c.poly([(hx + rr * math.cos(math.radians(a + 30)), hy + rr * math.sin(math.radians(a + 30))) for a in range(0, 360, 60)],
               fill=col, outline=OUTLINE, width=0.012)
        c.ellipse(hx - rr * 0.25, hy + rr * 0.25, rr * 0.2, rr * 0.2, fill=(255, 255, 255, 140))
    # Barometer rechts oben, Windfahne rechts unten
    gx, gy = x1 - 0.075, y1 - 0.08
    c.ellipse(gx, gy, 0.04, 0.04, fill=CREAM, outline=OUTLINE, width=0.012)
    c.line([(gx, gy), (gx + 0.025, gy + 0.02)], fill=RED, width=0.01)
    c.ellipse(gx, gy, 0.008, 0.008, fill=DARK)
    wx, wy = x1 - 0.075, y0 + 0.075
    c.line([(wx - 0.035, wy - 0.02), (wx + 0.035, wy + 0.02)], fill=OUTLINE, width=0.02)
    c.poly([(wx + 0.035, wy + 0.02), (wx + 0.05, wy + 0.04), (wx + 0.055, wy + 0.015)], fill=STEEL, outline=OUTLINE, width=0.008)
    c.ellipse(wx, wy, 0.01, 0.01, fill=STEEL, outline=OUTLINE, width=0.008)


def face_radio(c, r, body, trim):
    """Funkgeraet: Frequenzskala, zwei Drehknoepfe, Lautsprechergitter, roter Stoerungsmelder."""
    x0, y0, x1, y1 = r
    housing(c, r, OLIVE)
    screws(c, r)
    disp = (x0 + 0.05, y1 - 0.13, x1 - 0.05, y1 - 0.05)
    screen(c, disp, strength=0.3)
    for i in range(8):
        xx = disp[0] + 0.03 + i * (disp[2] - disp[0] - 0.06) / 7
        c.line([(xx, disp[1] + 0.015), (xx, disp[1] + (0.04 if i % 2 == 0 else 0.028))], fill=AMBER_HI, width=0.008)
    c.line([(disp[0] + 0.03 + (disp[2] - disp[0] - 0.06) * 0.6, disp[1] + 0.01), (disp[0] + 0.03 + (disp[2] - disp[0] - 0.06) * 0.6, disp[3] - 0.01)], fill=RED, width=0.01)
    # Lautsprechergitter links unten, Knoepfe rechts unten
    g = (x0 + 0.05, y0 + 0.05, x0 + (x1 - x0) * 0.45, y1 - 0.17)
    c.rect(*g, fill=DARK, outline=OUTLINE, width=0.012)
    yy = g[1] + 0.025
    while yy < g[3] - 0.015:
        c.line([(g[0] + 0.015, yy), (g[2] - 0.015, yy)], fill=shade(OLIVE, 0.8), width=0.008)
        yy += 0.025
    for i, ang in enumerate((200, 320)):
        kx, ky = x0 + (x1 - x0) * 0.62 + i * 0.1, (g[1] + g[3]) / 2
        c.ellipse(kx, ky, 0.035, 0.035, fill=DARK, outline=OUTLINE, width=0.012)
        c.line([(kx, ky), (kx + math.cos(math.radians(ang)) * 0.028, ky + math.sin(math.radians(ang)) * 0.028)], fill=AMBER_HI, width=0.01)
    lamp(c, x1 - 0.06, y1 - 0.18, 0.02, RED)
    c.glow(x1 - 0.06, y1 - 0.18, 0.16, RED, 0.4)


FACES = {
    "divert": face_divert, "data": face_data, "wiring": face_wiring, "garbage": face_garbage,
    "keypad": face_keypad, "hand": face_hand, "fuse": face_fuse, "gauges": face_gauges,
    "chart": face_chart, "spotter": face_spotter, "weather": face_weather, "radio": face_radio,
}

FACE_SIZE = {
    "divert": (0.38, 0.34), "data": (0.42, 0.46), "wiring": (0.30, 0.30), "garbage": (0.44, 0.36),
    "keypad": (0.36, 0.44), "hand": (0.36, 0.46), "fuse": (0.50, 0.58), "gauges": (0.54, 0.40),
    "chart": (0.62, 0.48), "spotter": (0.5, 0.56), "weather": (0.44, 0.40), "radio": (0.56, 0.36),
}


# ------------------------------------------------------- Montage-Arten (Gebaeude)

def mount_n(b, kind, body, trim, dx=0.0, **kw):
    """Standschrank an der Nordwand: Front zeigt nach Sueden, Bedienflaeche auf der Front."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0
    w = fw + 0.12
    h = (fh + 0.18) / K
    x0, x1 = -w / 2 - extra / 2 + dx, w / 2 - extra / 2 + dx
    front, _top = unit(b, x0, 0.0, x1, 0.26, h, body)
    r = fit(front, fw, fh)
    r = (r[0], front[1] + 0.06, r[2], front[1] + 0.06 + fh)
    FACES[kind](b.c, r, body, trim, **kw)
    b.c.rect(x0 + 0.03, 0.26 + h * K - 0.08, x1 - 0.03, 0.26 + h * K - 0.04, fill=trim)


def mount_s(b, kind, body, trim, **kw):
    """Flache Bodeneinheit vor der Suedwand: Bedienflaeche auf der Deckflaeche."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0
    w = fw + 0.12
    d = fh + 0.1
    h = 0.55
    x0, x1 = -w / 2 - extra / 2, w / 2 - extra / 2
    y0, y1 = -0.14, -0.14 + d
    front, top = unit(b, x0, y0, x1, y1, h, body)
    b.c.rect((x0 + x1) / 2 - 0.05, front[1] + 0.08, (x0 + x1) / 2 + 0.05, front[1] + 0.1, fill=trim)
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


def mount_side(b, kind, body, trim, east=True, **kw):
    """Schmaler Standschrank an der Ost-/Westwand: Bedienflaeche als Pult (Deckflaeche)."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0
    w = fw + 0.12
    d = fh + 0.1
    h = 0.7
    if east:
        x0, x1 = 0.02, 0.02 + w
    else:
        x0, x1 = -0.02 - w, -0.02
    if kind == "wiring" and east:
        x0, x1 = 0.02 - extra, 0.02 - extra + w
    y0, y1 = -d / 2, d / 2
    front, top = unit(b, x0, y0, x1, y1, h, body)
    b.c.rect(front[0] + 0.05, front[1] + 0.08, front[2] - 0.05, front[1] + 0.105, fill=trim)
    b.c.rect((x0 + x1) / 2 - 0.03, front[1] + 0.17, (x0 + x1) / 2 + 0.03, front[1] + 0.19, fill=shade(body, 0.6))
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


def head_on_post(b, kind, body, trim, x0, x1, hy0, hy1, hp, **kw):
    """Pultkopf (Kasten 0,14 hoch) auf Hoehe hp, Bedienflaeche auf der Deckflaeche."""
    fw, fh = FACE_SIZE[kind]
    b.box(x0, hy0, x1, hy1, hp, 0.14, shade(body, 1.15), body)
    b.c.rect(x0 + 0.04, hy0 + hp * K + 0.03, x1 - 0.04, hy0 + hp * K + 0.055, fill=trim)
    top = (x0 + 0.04, hy0 + (hp + 0.14) * K + 0.04, x1 - 0.04, hy1 + (hp + 0.14) * K - 0.04)
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


def mount_free(b, kind, body, trim, **kw):
    """Freistehendes Pult im Gebaeude: Holzpfosten mit aufgesetztem Pultkopf."""
    fw, fh = FACE_SIZE[kind]
    w = fw + 0.12
    d = fh + 0.1
    hp = 0.72
    x0, x1 = -w / 2, w / 2
    b.shadow(x0, -0.24, x1, 0.28)
    post(b, 0.0, 0.0, hp, WOOD_D, 0.07)
    b.c.rect(-0.14, -0.05, 0.14, 0.02, fill=WOOD_D, outline=OUTLINE, width=0.02)
    head_on_post(b, kind, body, trim, x0, x1, -d / 2, d / 2, hp, **kw)


# ------------------------------------------------------- Montage-Arten (Lichtung)

def mount_post(b, kind, body, trim, **kw):
    """Pfostenpult im Freien: Erdsockel, Holzpfosten, Kopf mit Bedienflaeche oben."""
    fw, fh = FACE_SIZE[kind]
    w = fw + 0.12
    d = fh + 0.1
    hp = 0.75
    x0, x1 = -w / 2, w / 2
    base_patch(b, x0 - 0.08, -0.26, x1 + 0.08, 0.2)
    post(b, 0.0, -0.02, hp, WOOD_D, 0.07)
    head_on_post(b, kind, body, trim, x0, x1, -d / 2, d / 2, hp, **kw)


def mount_board(b, kind, body, trim, dx=0.0, **kw):
    """Schautafel-Kasten vor dem Waldrand: zwei Pfosten, Kasten mit Front nach Sueden, kleines Dach."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0
    w = fw + 0.14
    hb = (fh + 0.16) / K       # Kastenhoehe
    z0 = 0.35                  # Kasten beginnt ueber dem Boden (Pfosten sichtbar)
    x0, x1 = -w / 2 - extra / 2 + dx, w / 2 - extra / 2 + dx
    y0, y1 = 0.0, 0.22
    base_patch(b, x0 - 0.1, y0 - 0.2, x1 + 0.1, y1 + 0.1)
    for px_ in (x0 + 0.07, x1 - 0.07):
        post(b, px_, y0 + 0.1, z0 + hb, WOOD_D, 0.05)
    b.box(x0, y0, x1, y1, z0, hb, shade(body, 1.15), body)
    front = (x0 + 0.04, y0 + z0 * K + 0.04, x1 - 0.04, y0 + (z0 + hb) * K - 0.04)
    if is_wood(body):
        planks(b.c, front, body)
    r = fit(front, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)
    # kleines Pultdach (Schindeln) ueber der Deckflaeche
    zt = y1 + (z0 + hb) * K
    b.c.poly([(x0 - 0.05, zt - 0.02), (x1 + 0.05, zt - 0.02), (x1 + 0.02, zt + 0.06), (x0 - 0.02, zt + 0.06)],
             fill=C["stamm_dunkel"], outline=OUTLINE, width=0.025)
    b.c.line([(x0, zt + 0.045), (x1, zt + 0.045)], fill=shade(C["stamm_dunkel"], 1.5), width=0.012)


# seitlicher Versatz einzelner Bloecke (m), falls sie etwas streifen (Anker bleibt)
SHIFT_X = {}


def generic(kind, wall, room, ppm, dx=0.0, **kw):
    body, trim = TINT.get(room, TINT["-"])
    fw, fh = FACE_SIZE[kind]
    extra = 0.3 if kind == "wiring" else 0.0
    outdoor = room in CLEARINGS
    if outdoor:
        if wall == "N":
            w = fw + 0.14 + extra
            hb = (fh + 0.16) / K
            b = Block(-w / 2 - 0.14 + min(0, dx), -0.24, w / 2 + 0.14 + max(0, dx), 0.34, (0.35 + hb) * K + 0.08, ppm)
            mount_board(b, kind, body, trim, dx=dx, **kw)
        else:
            w = fw + 0.12 + extra
            d = fh + 0.1
            b = Block(-w / 2 - 0.12, -max(0.3, d / 2 + 0.04), w / 2 + 0.12, max(0.22, d / 2), 0.9 * K, ppm)
            mount_post(b, kind, body, trim, **kw)
    elif wall == "N":
        w = fw + 0.12 + extra
        h = (fh + 0.18) / K
        b = Block(-w / 2 - 0.1 + min(0, dx), -0.05, w / 2 + 0.1 + max(0, dx), 0.26, h * K, ppm)
        mount_n(b, kind, body, trim, dx=dx, **kw)
    elif wall == "S":
        w = fw + 0.12 + extra
        b = Block(-w / 2 - 0.1, -0.2, w / 2 + 0.1, fh + 0.1 - 0.14, 0.55 * K, ppm)
        mount_s(b, kind, body, trim, **kw)
    elif wall in ("E", "W"):
        w = fw + 0.12 + extra
        d = fh + 0.1
        if wall == "E":
            b = Block(-0.35 - extra, -d / 2 - 0.06, 0.1 + w, d / 2, 0.7 * K, ppm)
        else:
            b = Block(-0.1 - w, -d / 2 - 0.06, 0.1 + extra + 0.3, d / 2, 0.7 * K, ppm)
        mount_side(b, kind, body, trim, east=(wall == "E"), **kw)
    else:
        w = fw + 0.12 + extra
        d = fh + 0.1
        b = Block(-w / 2 - 0.1, -max(0.26, d / 2 + 0.02), w / 2 + 0.1, max(0.28, d / 2), 0.86 * K, ppm)
        mount_free(b, kind, body, trim, **kw)
    return b.result()


# ------------------------------------------------------- Sonderbloecke

def id_reader(ppm, room="feldstation"):
    """Stations-Ausweisleser an der Nordwand: Holzstaender, Lesegeraet mit Schlitz, haengende Karte."""
    body, trim = TINT[room]
    b = Block(-0.3, -0.06, 0.3, 0.24, 1.3 * K, ppm)
    c = b.c
    b.shadow(-0.16, 0.0, 0.16, 0.2)
    b.box(-0.16, 0.0, 0.16, 0.2, 0, 0.45, shade(body, 1.15), body)
    planks(c, (-0.13, 0.07, 0.13, 0.45 * K - 0.03), body)
    c.rect(-0.14, 0.015, 0.14, 0.06, fill=shade(body, 0.6))
    post(b, 0.0, 0.1, 1.25, WOOD_D, 0.05)
    # Lesegeraet auf Brusthoehe (Front)
    zr = 0.1 + 0.75 * K
    r = (-0.2, zr, 0.2, zr + 0.36)
    housing(c, r, DARK)
    screws(c, r)
    screen(c, (-0.16, zr + 0.2, 0.08, zr + 0.32), strength=0.3)
    c.line([(-0.13, zr + 0.27), (0.02, zr + 0.27)], fill=AMBER_HI, width=0.014)
    c.rect(-0.16, zr + 0.05, 0.16, zr + 0.085, fill=hexc("#101216"), outline=STEEL, width=0.01)
    lamp(c, 0.13, zr + 0.26, 0.02, GREEN)
    lamp(c, 0.13, zr + 0.2, 0.02, RED, on=False)
    for i in range(3):
        c.rect(-0.16 + i * 0.07, zr + 0.11, -0.11 + i * 0.07, zr + 0.15, fill=CREAM, outline=OUTLINE, width=0.01)
    c.rect(-0.2, zr + 0.36, 0.2, zr + 0.4, fill=trim, outline=OUTLINE, width=0.015)
    # Ausweiskarte am Band (haengt links am Kasten)
    c.line([(-0.19, zr + 0.34), (-0.27, zr + 0.16)], fill=hexc("#3f6f9a"), width=0.012)
    c.poly([(-0.33, zr + 0.16), (-0.21, zr + 0.16), (-0.21, zr + 0.0), (-0.33, zr + 0.0)], fill=CREAM, outline=OUTLINE, width=0.012)
    c.ellipse(-0.29, zr + 0.11, 0.022, 0.022, fill=hexc("#6b8c45"))
    c.line([(-0.31, zr + 0.055), (-0.23, zr + 0.055)], fill=DARK, width=0.01)
    c.line([(-0.31, zr + 0.03), (-0.25, zr + 0.03)], fill=DARK, width=0.01)
    # Schild oben am Pfosten
    c.rect(-0.12, 1.28 * K, 0.12, 1.28 * K + 0.09, fill=CREAM, outline=OUTLINE, width=0.012)
    c.line([(-0.08, 1.28 * K + 0.045), (0.08, 1.28 * K + 0.045)], fill=hexc("#6b8c45"), width=0.016)
    return b.result()


def camp_bell(ppm):
    """Lagerglocke (Notfall): Messingglocke unter einem Holzgalgen, Zugseil, Stein-Sockel."""
    b = Block(-0.42, -0.3, 0.42, 0.3, 1.9 * K, ppm)
    c = b.c
    c.soft_shadow([(-0.24, -0.26), (0.3, -0.26), (0.3, 0.14), (-0.24, 0.14)], 90, 0.06)
    # Steinsockel + zwei Pfosten + Querbalken
    c.ellipse(0, -0.02, 0.3, 0.2, fill=C["fels"], outline=OUTLINE, width=0.03)
    c.ellipse(-0.06, 0.03, 0.16, 0.09, fill=shade(C["fels"], 1.18))
    for px_ in (-0.2, 0.2):
        post(b, px_, 0.0, 1.55, WOOD_D, 0.045)
    zb = 1.55 * K
    c.rect(-0.28, zb - 0.02, 0.28, zb + 0.08, fill=WOOD, outline=OUTLINE, width=0.025)
    c.line([(-0.25, zb + 0.06), (0.25, zb + 0.06)], fill=shade(WOOD, 1.3), width=0.012)
    c.poly([(-0.3, zb + 0.08), (0.3, zb + 0.08), (0.24, zb + 0.16), (-0.24, zb + 0.16)], fill=C["stamm_dunkel"], outline=OUTLINE, width=0.025)
    # Glocke haengt am Balken
    c.line([(0, zb - 0.02), (0, zb - 0.1)], fill=DARK, width=0.03)
    gz = zb - 0.1
    bell = BRASS
    c.poly([(-0.06, gz), (0.06, gz), (0.13, gz - 0.24), (0.17, gz - 0.3), (-0.17, gz - 0.3), (-0.13, gz - 0.24)],
           fill=bell, outline=OUTLINE, width=0.025)
    c.ellipse(0, gz - 0.3, 0.17, 0.05, fill=shade(bell, 0.75), outline=OUTLINE, width=0.02)
    c.line([(-0.08, gz - 0.06), (-0.11, gz - 0.22)], fill=BRASS_HI, width=0.02)
    c.line([(-0.13, gz - 0.24), (0.13, gz - 0.24)], fill=shade(bell, 0.7), width=0.012)
    c.ellipse(0, gz - 0.33, 0.035, 0.035, fill=DARK, outline=OUTLINE, width=0.012)
    c.glow(0, gz - 0.15, 0.4, AMBER_HI, 0.25)
    # Zugseil rechts herunter mit rotem Griff
    c.line([(0.15, gz - 0.28), (0.26, gz - 0.28), (0.27, 0.45 * K)], fill=OUTLINE, width=0.03)
    c.line([(0.15, gz - 0.28), (0.26, gz - 0.28), (0.27, 0.45 * K)], fill=hexc("#c9a46a"), width=0.014)
    c.rect(0.245, 0.3 * K, 0.295, 0.45 * K, fill=RED, outline=OUTLINE, width=0.012)
    # Schild "ALARM" am linken Pfosten
    c.rect(-0.3, 0.6 * K, -0.1, 0.6 * K + 0.11, fill=CREAM, outline=OUTLINE, width=0.012)
    c.line([(-0.27, 0.6 * K + 0.055), (-0.13, 0.6 * K + 0.055)], fill=RED, width=0.025)
    return b.result()


def ranger_desk(ppm):
    """Ranger-Monitorpult (Kameras): Holztisch, drei Monitore auf dem Tisch mit Front nach Osten, Stuhl."""
    body, trim = TINT["wachstube"]
    b = Block(-0.65, -0.62, 0.75, 0.62, 1.3 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.55, -0.55, 0.15, 0.55
    b.shadow(x0, y0, x1, y1)
    b.box(x0, y0, x1, y1, 0, 0.78, shade(body, 1.15), body)
    planks(c, (x0 + 0.03, y0 + 0.07, x1 - 0.03, y0 + 0.78 * K - 0.03), body)
    c.rect(x0 + 0.03, y0 + 0.02, x1 - 0.03, y0 + 0.07, fill=shade(body, 0.6))
    for i in range(2):
        c.rect(x0 + 0.06 + i * 0.34, y0 + 0.12, x0 + 0.34 + i * 0.34, y0 + 0.34, outline=shade(body, 0.7), width=0.015)
        c.rect(x0 + 0.16 + i * 0.34, y0 + 0.22, x0 + 0.24 + i * 0.34, y0 + 0.25, fill=BRASS)
    zt = 0.78 * K
    mon_x0, mon_x1 = x0 + 0.06, x0 + 0.48
    for i, my in enumerate((y1 - 0.2, y1 - 0.6, y1 - 1.0)):
        mb = my + zt
        c.rect(mon_x0, mb - 0.02, mon_x1, mb + 0.32, fill=hexc("#1e2226"), outline=OUTLINE, width=0.02)
        c.rect(mon_x0 + 0.04, mb + 0.02, mon_x1 - 0.04, mb + 0.28, fill=hexc("#3a5a4a") if i == 1 else hexc("#4f7a62"))
        # Waldbild: Baumkronen + Weg
        c.ellipse(mon_x0 + 0.13 + i * 0.05, mb + 0.19, 0.06, 0.05, fill=hexc("#6fa070"))
        c.ellipse(mon_x0 + 0.28, mb + 0.17, 0.07, 0.05, fill=hexc("#6fa070"))
        c.poly([(mon_x0 + 0.16, mb + 0.03), (mon_x0 + 0.3, mb + 0.03), (mon_x0 + 0.26, mb + 0.14), (mon_x0 + 0.2, mb + 0.14)], fill=hexc("#a08a68"))
        c.ellipse(mon_x1 - 0.08, mb + 0.25, 0.014, 0.014, fill=RED)
    c.glow(x0 + 0.28, zt + 0.1, 0.55, hexc("#8fd0ff"), 0.25)
    # Tastatur, Funkgeraet, Becher
    c.rect(x0 + 0.54, y0 + 0.35 + zt, x1 - 0.06, y0 + 0.6 + zt, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
    for j in range(3):
        for i in range(3):
            c.rect(x0 + 0.565 + i * 0.04, y0 + 0.37 + j * 0.08 + zt, x0 + 0.595 + i * 0.04, y0 + 0.42 + j * 0.08 + zt, fill=STEEL)
    c.rect(x0 + 0.54, y1 - 0.32 + zt, x0 + 0.66, y1 - 0.14 + zt, fill=DARK, outline=OUTLINE, width=0.012)
    c.line([(x0 + 0.64, y1 - 0.14 + zt), (x0 + 0.67, y1 - 0.02 + zt)], fill=STEEL, width=0.012)
    lamp(c, x0 + 0.6, y1 - 0.18 + zt, 0.012, RED)
    c.ellipse(x1 - 0.1, y0 + 0.2 + zt, 0.045, 0.035, fill=CREAM, outline=OUTLINE, width=0.012)
    # Holzstuhl oestlich (Spieler steht oestlich, Nutzradius liegt dort)
    sx, sy = 0.45, 0.0
    c.soft_shadow([(sx - 0.18, sy - 0.22), (sx + 0.26, sy - 0.22), (sx + 0.26, sy + 0.18), (sx - 0.18, sy + 0.18)], 80, 0.05)
    for lx, ly in ((sx - 0.14, sy - 0.14), (sx + 0.14, sy - 0.14)):
        c.rect(lx - 0.02, ly, lx + 0.02, ly + 0.45 * K, fill=WOOD_D, outline=OUTLINE, width=0.015)
    b.box(sx - 0.18, sy - 0.16, sx + 0.18, sy + 0.16, 0.45, 0.06, shade(WOOD, 1.15), WOOD, w=0.025)
    b.box(sx + 0.12, sy - 0.16, sx + 0.18, sy + 0.16, 0.51, 0.45, shade(WOOD, 1.1), WOOD_D, w=0.025)
    return b.result()


def map_board(ppm):
    """Gebaeudeplan (Admin): Stehende Kartentafel auf Staffelei mit Stationsplan, Nadeln und Lampe."""
    body, trim = TINT["feldstation"]
    b = Block(-0.48, -0.3, 0.48, 0.24, 1.35 * K, ppm)
    c = b.c
    b.shadow(-0.3, -0.2, 0.3, 0.14)
    # A-Staffelei: zwei schraege Beine + Querstrebe
    for sx, ex in ((-0.3, -0.16), (0.3, 0.16)):
        c.line([(sx, -0.12), (ex, 1.2 * K)], fill=OUTLINE, width=0.06)
        c.line([(sx, -0.12), (ex, 1.2 * K)], fill=WOOD_D, width=0.035)
    c.line([(-0.24, 0.35 * K), (0.24, 0.35 * K)], fill=WOOD_D, width=0.03)
    # Tafel (leicht nach hinten geneigt: als Front gezeichnet)
    zb = 0.5 * K
    r = (-0.38, zb, 0.38, zb + 0.5)
    housing(c, r, WOOD)
    planks(c, r, WOOD, 0.1)
    m = shrink(r, 0.04)
    topo(c, m, route=False)
    # Stationsplan: Rechtecke = Huetten, Punkte = Spieler (Bernstein), Stern = Standort
    mx0, my0, mx1, my1 = m
    w, h = mx1 - mx0, my1 - my0
    for u, v, uw, vh in ((0.42, 0.55, 0.16, 0.16), (0.15, 0.55, 0.13, 0.14), (0.7, 0.55, 0.13, 0.14), (0.25, 0.15, 0.2, 0.14), (0.6, 0.15, 0.13, 0.13), (0.1, 0.85, 0.18, 0.1)):
        c.rect(mx0 + w * u, my0 + h * v, mx0 + w * (u + uw), my0 + h * (v + vh), fill=alpha(C["balken"], 200), outline=DARK, width=0.008)
    for u, v in ((0.5, 0.62), (0.2, 0.6), (0.65, 0.2), (0.3, 0.2)):
        c.ellipse(mx0 + w * u, my0 + h * v, 0.014, 0.014, fill=AMBER, outline=OUTLINE, width=0.006)
    c.ellipse(mx0 + w * 0.5, my0 + h * 0.62, 0.028, 0.028, outline=RED, width=0.01)
    for px_, py_ in ((mx0 + 0.04, my1 - 0.04), (mx1 - 0.04, my1 - 0.04), (mx0 + 0.04, my0 + 0.04), (mx1 - 0.04, my0 + 0.04)):
        c.ellipse(px_, py_, 0.012, 0.012, fill=RED, outline=OUTLINE, width=0.008)
    # Klemmlampe oben, warmer Schein auf der Karte
    c.line([(0.3, zb + 0.5), (0.34, zb + 0.62), (0.22, zb + 0.66)], fill=OUTLINE, width=0.03)
    c.line([(0.3, zb + 0.5), (0.34, zb + 0.62), (0.22, zb + 0.66)], fill=STEEL, width=0.014)
    c.poly([(0.16, zb + 0.6), (0.26, zb + 0.7), (0.2, zb + 0.74), (0.1, zb + 0.66)], fill=hexc("#3f6f5a"), outline=OUTLINE, width=0.015)
    c.glow(0.1, zb + 0.45, 0.35, AMBER_HI, 0.3)
    # Ablagebrett mit Stiften
    c.rect(-0.34, zb - 0.02, 0.34, zb + 0.03, fill=WOOD_D, outline=OUTLINE, width=0.015)
    for i, col in enumerate((RED, hexc("#3f9fd8"), GREEN_D)):
        c.rect(-0.28 + i * 0.05, zb - 0.01, -0.26 + i * 0.05, zb + 0.06, fill=col, outline=OUTLINE, width=0.008)
    return b.result()


def crate_laptop(ppm):
    """Freeplay-Laptop: robuster Laptop auf einer Holzkiste, Kaffeebecher daneben."""
    b = Block(-0.36, -0.3, 0.36, 0.24, 1.0 * K, ppm)
    c = b.c
    crate = hexc("#9a7a52")
    x0, y0, x1, y1 = -0.28, -0.2, 0.28, 0.16
    b.shadow(x0, y0, x1, y1)
    b.box(x0, y0, x1, y1, 0, 0.55, shade(crate, 1.15), crate)
    c.line([(x0 + 0.03, y0 + 0.05), (x1 - 0.03, y0 + 0.55 * K - 0.04)], fill=hexc("#6e5234"), width=0.03)
    c.line([(x1 - 0.03, y0 + 0.05), (x0 + 0.03, y0 + 0.55 * K - 0.04)], fill=hexc("#6e5234"), width=0.03)
    c.rect(x0 + 0.03, y0 + 0.05, x1 - 0.03, y0 + 0.55 * K - 0.04, outline=hexc("#6e5234"), width=0.02)
    zt = y0 + 0.55 * K + 0.12
    lp = OLIVE
    c.poly([(-0.17, zt - 0.08), (0.17, zt - 0.08), (0.19, zt + 0.06), (-0.19, zt + 0.06)], fill=lp, outline=OUTLINE, width=0.02)
    c.rect(-0.14, zt - 0.05, 0.14, zt + 0.02, fill=hexc("#1e2226"))
    c.rect(-0.03, zt - 0.075, 0.03, zt - 0.06, fill=hexc("#1e2226"))
    c.rect(-0.2, zt + 0.06, 0.2, zt + 0.34, fill=shade(lp, 0.9), outline=OUTLINE, width=0.02)
    screws(c, (-0.2, zt + 0.06, 0.2, zt + 0.34))
    screen(c, (-0.17, zt + 0.09, 0.17, zt + 0.31), strength=0.3)
    c.line([(-0.13, zt + 0.25), (0.02, zt + 0.25)], fill=AMBER_HI, width=0.014)
    c.line([(-0.13, zt + 0.2), (0.08, zt + 0.2)], fill=AMBER_HI, width=0.014)
    c.line([(-0.13, zt + 0.15), (-0.03, zt + 0.15)], fill=AMBER_HI, width=0.014)
    c.ellipse(0.11, zt + 0.14, 0.025, 0.025, fill=GREEN)
    c.ellipse(0.25, zt - 0.03, 0.035, 0.028, fill=hexc("#3b4046"), outline=OUTLINE, width=0.012)
    c.ellipse(0.25, zt - 0.03, 0.02, 0.014, fill=hexc("#6e4a2a"))
    return b.result()


def floor_scanner(ppm):
    """Boden-Scannerring im Labor: Stahlring mit Fussmarken, zwei Emittersaeulen mit gruenem Abtastlicht."""
    b = Block(-0.85, -0.7, 0.85, 0.7, 1.6 * K, ppm)
    c = b.c
    steel = lift("#8b949a", 1.35)
    rx, ry = 0.7, 0.48
    c.ellipse(0.05, -0.05, rx, ry, fill=alpha((8, 10, 16, 255), 70))
    c.ellipse(0, 0, rx, ry, fill=shade(steel, 0.8), outline=OUTLINE)
    c.rect(-rx, 0, rx, 0.08 * K, fill=shade(steel, 0.8))
    c.line([(-rx, 0), (-rx, 0.08 * K)], fill=OUTLINE, width=OUT_W)
    c.line([(rx, 0), (rx, 0.08 * K)], fill=OUTLINE, width=OUT_W)
    zt = 0.08 * K
    c.ellipse(0, zt, rx, ry, fill=steel, outline=OUTLINE)
    c.ellipse(0, zt, rx - 0.12, ry - 0.09, fill=hexc("#3a4046"), outline=OUTLINE, width=0.03)
    c.ellipse(0, zt, rx - 0.2, ry - 0.15, outline=alpha(GREEN, 220), width=0.035)
    c.ellipse(0, zt, rx - 0.34, ry - 0.25, outline=alpha(GREEN, 120), width=0.02)
    c.glow(0, zt, 0.7, GREEN, 0.35)
    for sx in (-0.07, 0.07):
        c.ellipse(sx, zt + 0.02, 0.035, 0.06, fill=alpha(GREEN, 200))
    hazard_band(c, -0.2, -0.02, 0.2, 0.08 * K - 0.01)

    def emitter(px, py, h):
        b.cyl(px, py, 0.07, 0.08, h, shade(steel, 1.15), shade(steel, 0.9), w=0.025, ry=0.05)
        c.ellipse(px, py + (0.08 + h) * K, 0.045, 0.03, fill=GREEN, outline=OUTLINE, width=0.012)
    emitter(-0.5, 0.28, 1.35); emitter(0.5, 0.28, 1.35)
    c.rect(-0.5, 0.28 + 1.43 * K - 0.04, 0.5, 0.28 + 1.43 * K + 0.06, fill=steel, outline=OUTLINE, width=0.025)
    c.line([(-0.45, 0.28 + 1.43 * K + 0.035), (0.45, 0.28 + 1.43 * K + 0.035)], fill=shade(steel, 1.3), width=0.015)
    for i in range(5):
        c.ellipse(-0.36 + i * 0.18, 0.28 + 1.43 * K + 0.01, 0.018, 0.014, fill=GREEN)
    c.rect(-0.12, 0.28 + 1.43 * K + 0.06, 0.12, 0.28 + 1.43 * K + 0.12, fill=DARK, outline=OUTLINE, width=0.012)
    lamp(c, 0, 0.28 + 1.43 * K + 0.09, 0.015, GREEN)
    emitter(-0.55, -0.3, 0.4); emitter(0.55, -0.3, 0.4)
    return b.result()


def microscope_bench(ppm):
    """Feldmikroskop-Bank (Inspect Sample): Holzbank mit Mikroskop, Petrischalen, Roehrchen, Notizbuch."""
    body, trim = TINT["labor"]
    b = Block(-0.5, -0.3, 0.5, 0.3, 1.45 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.22, 0.4, 0.22
    front, top = unit(b, x0, y0, x1, y1, 0.85, WOOD)
    # Front: Schublade + blaues Schild
    c.rect(x0 + 0.08, y0 + 0.14, x1 - 0.08, y0 + 0.36, outline=shade(WOOD, 0.7), width=0.015)
    c.rect(-0.05, y0 + 0.23, 0.05, y0 + 0.26, fill=BRASS)
    c.rect(x0 + 0.1, y0 + 0.4, x0 + 0.3, y0 + 0.44, fill=trim)
    # Deckflaeche: helle Arbeitsplatte
    c.rect(top[0], top[1], top[2], top[3], fill=lift("#b8bcc0", 1.1), outline=shade(WOOD, 0.7), width=0.012)
    zt = y0 + 0.85 * K
    # Mikroskop (rechts): Fuss, Saeule, Tubus, Okular
    mx = 0.2
    c.ellipse(mx, zt + 0.16, 0.09, 0.04, fill=DARK, outline=OUTLINE, width=0.015)
    c.rect(mx - 0.09, zt + 0.16, mx + 0.09, zt + 0.2, fill=DARK, outline=OUTLINE, width=0.015)
    c.line([(mx + 0.05, zt + 0.2), (mx + 0.07, zt + 0.5)], fill=OUTLINE, width=0.06)
    c.line([(mx + 0.05, zt + 0.2), (mx + 0.07, zt + 0.5)], fill=STEEL, width=0.035)
    c.rect(mx - 0.06, zt + 0.24, mx + 0.04, zt + 0.27, fill=CREAM, outline=OUTLINE, width=0.01)
    c.poly([(mx - 0.03, zt + 0.3), (mx + 0.03, zt + 0.3), (mx + 0.01, zt + 0.55), (mx - 0.05, zt + 0.55)], fill=DARK, outline=OUTLINE, width=0.015)
    c.ellipse(mx - 0.02, zt + 0.56, 0.035, 0.02, fill=STEEL, outline=OUTLINE, width=0.012)
    c.glow(mx - 0.01, zt + 0.27, 0.12, AMBER_HI, 0.4)
    # Petrischalen + Roehrchenstaender (links)
    c.ellipse(-0.25, zt + 0.12, 0.08, 0.045, fill=hexc("#bfe3f5"), outline=OUTLINE, width=0.012)
    c.ellipse(-0.25, zt + 0.12, 0.04, 0.022, fill=hexc("#7a8a4a"))
    c.ellipse(-0.1, zt + 0.08, 0.06, 0.035, fill=hexc("#bfe3f5"), outline=OUTLINE, width=0.012)
    c.ellipse(-0.1, zt + 0.08, 0.03, 0.017, fill=hexc("#c9a46a"))
    c.rect(-0.36, zt + 0.22, -0.14, zt + 0.27, fill=WOOD_D, outline=OUTLINE, width=0.012)
    for i, col in enumerate(("#3f9e6e", "#e05a3a", "#3f9fd8", "#e0b04a")):
        tx = -0.33 + i * 0.055
        c.rect(tx - 0.012, zt + 0.24, tx + 0.012, zt + 0.4, fill=hexc(col), outline=OUTLINE, width=0.01)
        c.rect(tx - 0.014, zt + 0.4, tx + 0.014, zt + 0.44, fill=CREAM, outline=OUTLINE, width=0.01)
    # Notizbuch
    c.poly([(0.0, zt + 0.32), (0.14, zt + 0.32), (0.16, zt + 0.42), (0.02, zt + 0.42)], fill=CREAM, outline=OUTLINE, width=0.012)
    c.line([(0.04, zt + 0.36), (0.12, zt + 0.36)], fill=DARK, width=0.008)
    c.line([(0.04, zt + 0.39), (0.1, zt + 0.39)], fill=DARK, width=0.008)
    return b.result()


def water_filter(ppm):
    """Wasserfilter-Einheit (Clean Filter): blaue Tonne mit Filterpatrone, Rohre, Manometer, Kurbel, Erdsockel."""
    b = Block(-0.5, -0.3, 0.5, 0.3, 1.5 * K, ppm)
    c = b.c
    base_patch(b, -0.42, -0.26, 0.42, 0.22)
    blue = WATER
    b.cyl(-0.1, 0.0, 0.24, 0, 0.95, shade(blue, 1.15), blue, ry=0.16)
    c.line([(-0.28, 0.1), (-0.28, 0.95 * K - 0.05)], fill=shade(blue, 1.35), width=0.03)
    for z in (0.3, 0.65):
        c.line([(-0.34, z * K), (0.14, z * K)], fill=shade(blue, 0.7), width=0.02)
    drop(c, -0.1, 0.45 * K, 0.06, hexc("#e8f4ff"))
    # Filterpatrone (weiss, Sichtfenster) rechts angeflanscht
    b.cyl(0.28, 0.0, 0.1, 0.25, 0.5, CREAM, shade(CREAM, 0.85), ry=0.07)
    c.rect(0.22, 0.35 * K, 0.34, 0.65 * K, fill=hexc("#5a6a3a"), outline=OUTLINE, width=0.012)
    c.rect(0.24, 0.55 * K, 0.32, 0.63 * K, fill=hexc("#9aa060"))
    # Rohre: Tonne -> Patrone, Patrone -> Boden
    c.line([(0.12, 0.7 * K), (0.28, 0.7 * K), (0.28, 0.75 * K)], fill=OUTLINE, width=0.05)
    c.line([(0.12, 0.7 * K), (0.28, 0.7 * K), (0.28, 0.75 * K)], fill=STEEL, width=0.028)
    c.line([(0.28, 0.25 * K), (0.28, 0.1), (0.42, 0.1)], fill=OUTLINE, width=0.05)
    c.line([(0.28, 0.25 * K), (0.28, 0.1), (0.42, 0.1)], fill=STEEL, width=0.028)
    # Manometer oben auf der Tonne + Kurbel links
    gz = 0.95 * K + 0.1
    c.ellipse(-0.1, gz + 0.08, 0.06, 0.06, fill=CREAM, outline=OUTLINE, width=0.015)
    c.rect(-0.02, gz + 0.06, 0.06, gz + 0.1, fill=DARK)
    c.line([(-0.1, gz + 0.08), (-0.07, gz + 0.12)], fill=RED, width=0.012)
    c.ellipse(-0.1, gz + 0.08, 0.01, 0.01, fill=DARK)
    c.line([(-0.34, 0.5 * K), (-0.44, 0.5 * K), (-0.44, 0.5 * K + 0.12)], fill=OUTLINE, width=0.04)
    c.line([(-0.34, 0.5 * K), (-0.44, 0.5 * K), (-0.44, 0.5 * K + 0.12)], fill=STEEL, width=0.02)
    c.ellipse(-0.44, 0.5 * K + 0.13, 0.025, 0.025, fill=RED, outline=OUTLINE, width=0.012)
    # Wasserhahn vorn mit Tropfen
    c.rect(-0.14, 0.15 * K, -0.06, 0.15 * K + 0.06, fill=BRASS, outline=OUTLINE, width=0.012)
    c.ellipse(-0.1, 0.02, 0.02, 0.028, fill=hexc("#5b9fd0"))
    return b.result()


def fuel_station(ppm, room):
    """Kanisterstation (Fuel Engines Teil 2): Zapfsaeule mit Zaehlwerk, Schlauch und rotem Kanister davor."""
    body, trim = TINT[room]
    b = Block(-0.5, -0.3, 0.5, 0.26, 1.35 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.22, -0.2, 0.22, 0.2
    front, top = unit(b, x0, y0, x1, y1, 1.2, METAL)
    s = (x0 + 0.06, y0 + 0.44, x1 - 0.06, y0 + 0.58)
    screen(c, s, strength=0.3)
    for i in range(3):
        c.rect(s[0] + 0.03 + i * 0.09, s[1] + 0.03, s[0] + 0.09 + i * 0.09, s[3] - 0.03, fill=AMBER_HI)
    c.rect(x0 + 0.08, y0 + 0.2, x1 - 0.08, y0 + 0.38, fill=RED, outline=OUTLINE, width=0.015)
    c.rect(x0 + 0.12, y0 + 0.38, x0 + 0.2, y0 + 0.41, fill=DARK)
    c.line([(x0 + 0.1, y0 + 0.36), (x1 - 0.1, y0 + 0.36)], fill=shade(RED, 1.3), width=0.012)
    hazard_band(c, x0 + 0.05, y0 + 0.1, x1 - 0.05, y0 + 0.16)
    lamp(c, x1 - 0.09, y0 + 0.64, 0.02, AMBER_HI)
    # Schlauch rechts herunter, Zapfpistole in der Halterung
    c.line([(x1 - 0.02, y0 + 0.62), (x1 + 0.12, y0 + 0.5), (x1 + 0.1, y0 + 0.2), (x1 - 0.02, y0 + 0.16)], fill=OUTLINE, width=0.055)
    c.line([(x1 - 0.02, y0 + 0.62), (x1 + 0.12, y0 + 0.5), (x1 + 0.1, y0 + 0.2), (x1 - 0.02, y0 + 0.16)], fill=hexc("#1e2226"), width=0.03)
    c.poly([(x1 - 0.03, y0 + 0.66), (x1 + 0.06, y0 + 0.66), (x1 + 0.06, y0 + 0.76), (x1 + 0.12, y0 + 0.78), (x1 + 0.12, y0 + 0.82), (x1 - 0.03, y0 + 0.82)],
           fill=RED, outline=OUTLINE, width=0.015)
    c.rect(top[0] + 0.02, top[1] + 0.02, top[2] - 0.02, top[3] - 0.02, fill=trim)
    # roter Kanister links vor der Saeule
    kx, ky = -0.36, -0.14
    b.box(kx - 0.1, ky - 0.06, kx + 0.1, ky + 0.06, 0, 0.32, shade(RED, 1.15), shade(RED, 0.9), w=0.025)
    c.rect(kx - 0.02, ky + 0.06 + 0.32 * K - 0.005, kx + 0.02, ky + 0.06 + 0.32 * K + 0.04, fill=DARK, outline=OUTLINE, width=0.012)
    c.line([(kx - 0.05, ky + 0.06 + 0.32 * K + 0.025), (kx + 0.05, ky + 0.06 + 0.32 * K + 0.025)], fill=OUTLINE, width=0.02)
    c.rect(kx - 0.07, ky - 0.06 + 0.1, kx + 0.07, ky - 0.06 + 0.15, fill=CREAM, outline=OUTLINE, width=0.01)
    return b.result()


def gauge_post(ppm, room):
    """Ausrichtung (Align Engine): Holzpfosten mit grossem Rundinstrument und Stellhebel."""
    body, trim = TINT[room]
    b = Block(-0.4, -0.3, 0.4, 0.24, 1.25 * K, ppm)
    c = b.c
    b.shadow(-0.2, -0.22, 0.2, 0.16)
    b.box(-0.14, -0.16, 0.14, 0.12, 0, 0.75, shade(body, 1.1), shade(body, 0.92))
    planks(c, (-0.11, -0.09, 0.11, -0.16 + 0.75 * K - 0.03), body)
    c.rect(-0.2, -0.18, 0.2, -0.12, fill=shade(body, 0.6), outline=OUTLINE, width=0.02)
    zt = -0.16 + 0.78 * K
    c.ellipse(0, zt + 0.02, 0.29, 0.29, fill=shade(METAL, 0.7), outline=OUTLINE, width=0.03)
    c.ellipse(0, zt + 0.04, 0.29, 0.29, fill=METAL, outline=OUTLINE, width=0.03)
    c.ellipse(0, zt + 0.04, 0.23, 0.23, fill=CREAM, outline=OUTLINE, width=0.02)
    for a in range(0, 181, 15):
        ang = math.radians(a)
        ln = 0.06 if a % 45 == 0 else 0.03
        c.line([(math.cos(ang) * (0.23 - ln), zt + 0.04 + math.sin(ang) * (0.23 - ln)), (math.cos(ang) * 0.21, zt + 0.04 + math.sin(ang) * 0.21)], fill=DARK, width=0.012)
    c.poly([(-0.03, zt + 0.25), (0.03, zt + 0.25), (0, zt + 0.19)], fill=GREEN, outline=OUTLINE, width=0.01)
    ang = math.radians(112)
    c.line([(0, zt + 0.04), (math.cos(ang) * 0.19, zt + 0.04 + math.sin(ang) * 0.19)], fill=RED, width=0.02)
    c.ellipse(0, zt + 0.04, 0.03, 0.03, fill=DARK, outline=OUTLINE, width=0.012)
    c.line([(-0.12, zt - 0.02), (0.12, zt - 0.02)], fill=trim, width=0.02)
    lamp(c, -0.1, zt - 0.1, 0.02, AMBER_HI)
    lamp(c, 0.1, zt - 0.1, 0.02, RED, on=False)
    c.line([(0.27, zt), (0.36, zt + 0.16)], fill=OUTLINE, width=0.05)
    c.line([(0.27, zt), (0.36, zt + 0.16)], fill=STEEL, width=0.025)
    c.ellipse(0.36, zt + 0.16, 0.035, 0.035, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
    return b.result()


def jerrycan_rack(ppm):
    """Kanister holen (Lager): Holzregal an der Nordwand mit roten Kanistern auf einer Tropfwanne."""
    body, trim = TINT["lager"]
    b = Block(-0.5, -0.24, 0.5, 0.3, 1.0 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.16, 0.4, 0.24
    b.shadow(x0, y0, x1, y1)
    b.box(x0, y0, x1, y1, 0, 0.08, WARN, WARN, w=0.025)
    for i in range(6):
        xx = x0 + 0.05 + i * 0.13
        c.poly([(xx, y0 + 0.005), (xx + 0.05, y0 + 0.005), (xx + 0.1, y0 + 0.08 * K - 0.005), (xx + 0.05, y0 + 0.08 * K - 0.005)], fill=hexc("#1e1e1e"))
    zt = 0.08 * K
    c.rect(x0 + 0.04, y0 + zt + 0.04, x1 - 0.04, y1 + zt - 0.04, fill=shade(body, 0.8))
    yy = y0 + zt + 0.06
    while yy < y1 + zt - 0.05:
        c.line([(x0 + 0.05, yy), (x1 - 0.05, yy)], fill=shade(body, 1.2), width=0.012)
        yy += 0.05

    def can(px, py, w, h, col):
        b.box(px - w / 2, py - 0.08, px + w / 2, py + 0.08, 0.08, h, shade(col, 1.15), col, w=0.025)
        c.line([(px - w / 2 + 0.03, py - 0.08 + 0.16 * K), (px + w / 2 - 0.03, py - 0.08 + 0.16 * K)], fill=shade(col, 0.7), width=0.012)
        c.rect(px - 0.02, py + 0.08 + (0.08 + h) * K - 0.005, px + 0.02, py + 0.08 + (0.08 + h) * K + 0.05, fill=DARK, outline=OUTLINE, width=0.012)
        c.line([(px - 0.05, py + 0.08 + (0.08 + h) * K + 0.03), (px + 0.05, py + 0.08 + (0.08 + h) * K + 0.03)], fill=OUTLINE, width=0.025)
        c.rect(px - w / 2 + 0.03, py - 0.08 + 0.4 * h * K, px + w / 2 - 0.03, py - 0.08 + 0.4 * h * K + 0.07, fill=CREAM, outline=OUTLINE, width=0.01)
    can(-0.12, 0.04, 0.3, 0.55, RED)
    can(0.22, 0.02, 0.2, 0.42, hexc("#3f4a56"))
    c.text(-0.12, 0.04 - 0.08 + 0.4 * 0.55 * K + 0.035, "FUEL", 0.05, DARK)
    # Holzpfosten des Regals hinten
    for px_ in (x0 + 0.03, x1 - 0.03):
        c.rect(px_ - 0.025, y1 + zt - 0.02, px_ + 0.025, y1 + zt + 0.9 * K, fill=WOOD_D, outline=OUTLINE, width=0.015)
    c.rect(x0, y1 + zt + 0.9 * K - 0.04, x1, y1 + zt + 0.9 * K + 0.02, fill=WOOD, outline=OUTLINE, width=0.02)
    return b.result()


def pump_terminal(ppm, room="pumpe"):
    """Start Reactor: Pumpen-Steuerschrank im Freien (Blech, grosse Manometer, zwei Handfelder auf dem Pult)."""
    body, trim = TINT[room]
    b = Block(-0.5, -0.5, 0.5, 0.44, 1.35 * K, ppm)
    c = b.c
    base_patch(b, -0.46, -0.48, 0.46, 0.4)
    x0, y0, x1, y1 = -0.36, -0.38, 0.36, 0.3
    front, top = unit(b, x0, y0, x1, y1, 1.15, body, shadow=False)
    c.rect(x0 + 0.06, y0 + 0.1, x1 - 0.06, y0 + 0.24, fill=shade(body, 0.7), outline=OUTLINE, width=0.015)
    for i in range(5):
        c.line([(x0 + 0.09, y0 + 0.12 + i * 0.025), (x1 - 0.09, y0 + 0.12 + i * 0.025)], fill=shade(body, 1.1), width=0.008)
    c.rect(x0 + 0.04, y0 + 0.3, x1 - 0.04, y0 + 0.58, fill=DARK, outline=OUTLINE, width=0.02)
    for i in range(2):
        gx = x0 + 0.16 + i * 0.28
        c.ellipse(gx, y0 + 0.44, 0.08, 0.08, fill=CREAM, outline=OUTLINE, width=0.015)
        ang = math.radians(200 + i * 60)
        c.line([(gx, y0 + 0.44), (gx + math.cos(ang) * 0.06, y0 + 0.44 - math.sin(ang) * 0.06)], fill=RED, width=0.012)
        c.ellipse(gx, y0 + 0.44, 0.01, 0.01, fill=DARK)
    lamp(c, x1 - 0.1, y0 + 0.36, 0.022, RED)
    lamp(c, x1 - 0.1, y0 + 0.52, 0.022, GREEN, on=False)
    drop(c, x1 - 0.1, y0 + 0.44, 0.02)
    tx0, ty0, tx1, ty1 = top
    c.rect(tx0, ty0, tx1, ty1, fill=shade(body, 0.85), outline=shade(body, 0.7), width=0.012)
    c.rect(tx0 + 0.02, ty1 - 0.06, tx1 - 0.02, ty1 - 0.035, fill=trim)
    s = (tx0 + 0.04, ty0 + 0.24, tx1 - 0.04, ty1 - 0.08)
    screen(c, s, strength=0.35)
    for i in range(4):
        yy = s[3] - 0.04 - i * 0.03
        c.line([(s[0] + 0.03, yy), (s[0] + 0.03 + (s[2] - s[0]) * (0.7 - 0.15 * i), yy)], fill=AMBER_HI, width=0.012)
    c.poly([(s[2] - 0.08, s[1] + 0.04), (s[2] - 0.03, s[1] + 0.04), (s[2] - 0.055, s[1] + 0.1)], fill=RED)
    for i in range(2):
        hx = tx0 + 0.16 + i * 0.3
        c.rect(hx - 0.1, ty0 + 0.03, hx + 0.1, ty0 + 0.2, fill=hexc("#5a3a0e"), outline=OUTLINE, width=0.012)
        c.ellipse(hx, ty0 + 0.09, 0.05, 0.04, fill=AMBER_HI)
        for fx in (-0.045, -0.015, 0.015, 0.045):
            c.line([(hx + fx, ty0 + 0.11), (hx + fx, ty0 + 0.17)], fill=AMBER_HI, width=0.02)
    # Rohr aus dem Schrank in den Boden
    c.line([(x1 - 0.02, y0 + 0.2), (x1 + 0.1, y0 + 0.2), (x1 + 0.1, y0 + 0.02)], fill=OUTLINE, width=0.06)
    c.line([(x1 - 0.02, y0 + 0.2), (x1 + 0.1, y0 + 0.2), (x1 + 0.1, y0 + 0.02)], fill=STEEL, width=0.035)
    return b.result()


def theodolite(ppm):
    """Stabilize Steering: Theodolit auf Holzstativ mit Steuerkasten (Joystick, Fadenkreuz-Anzeige)."""
    body, trim = TINT["aussicht"]
    b = Block(-0.5, -0.32, 0.5, 0.3, 1.5 * K, ppm)
    c = b.c
    base_patch(b, -0.42, -0.28, 0.42, 0.24)
    # Dreibein
    legs = ((-0.3, -0.18), (0.3, -0.18), (0.02, 0.2))
    for lx, ly in legs:
        c.line([(lx, ly), (0, 0.95 * K)], fill=OUTLINE, width=0.06)
        c.line([(lx, ly), (0, 0.95 * K)], fill=WOOD_D, width=0.035)
        c.ellipse(lx, ly, 0.03, 0.02, fill=STEEL, outline=OUTLINE, width=0.012)
    # Kopfplatte + Fernrohr (schraeg nach rechts oben)
    zh = 0.95 * K
    c.ellipse(0, zh, 0.09, 0.05, fill=BRASS, outline=OUTLINE, width=0.02)
    c.rect(-0.04, zh, 0.04, zh + 0.09, fill=DARK, outline=OUTLINE, width=0.015)
    c.line([(-0.12, zh + 0.06), (0.22, zh + 0.22)], fill=OUTLINE, width=0.1)
    c.line([(-0.12, zh + 0.06), (0.22, zh + 0.22)], fill=hexc("#3b4046"), width=0.065)
    c.line([(-0.1, zh + 0.085), (0.18, zh + 0.215)], fill=hexc("#6f7a82"), width=0.02)
    c.ellipse(0.23, zh + 0.225, 0.05, 0.04, fill=hexc("#bfe3f5"), outline=OUTLINE, width=0.015)
    c.ellipse(0.215, zh + 0.235, 0.015, 0.012, fill=(255, 255, 255, 170))
    c.ellipse(-0.13, zh + 0.055, 0.03, 0.03, fill=DARK, outline=OUTLINE, width=0.012)
    c.ellipse(0.05, zh + 0.03, 0.025, 0.025, fill=BRASS, outline=OUTLINE, width=0.01)
    # Steuerkasten am rechten Bein (Front nach Sueden)
    kb = (0.16, 0.25 * K, 0.42, 0.25 * K + 0.3)
    housing(c, kb, OLIVE)
    screws(c, kb)
    s = (kb[0] + 0.04, kb[1] + 0.14, kb[2] - 0.04, kb[3] - 0.04)
    screen(c, s, base=hexc("#1e3a2a"), glowc=GREEN, strength=0.3)
    cx, cy = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
    c.line([(cx, s[1] + 0.015), (cx, s[3] - 0.015)], fill=alpha(GREEN, 160), width=0.008)
    c.line([(s[0] + 0.015, cy), (s[2] - 0.015, cy)], fill=alpha(GREEN, 160), width=0.008)
    c.ellipse(cx + 0.03, cy + 0.02, 0.012, 0.012, fill=AMBER_HI)
    jx, jy = kb[0] + 0.08, kb[1] + 0.06
    c.ellipse(jx, jy, 0.03, 0.02, fill=hexc("#1f2428"), outline=OUTLINE, width=0.01)
    c.line([(jx, jy), (jx + 0.015, jy + 0.05)], fill=OUTLINE, width=0.028)
    c.line([(jx, jy), (jx + 0.015, jy + 0.05)], fill=STEEL, width=0.014)
    c.ellipse(jx + 0.015, jy + 0.055, 0.018, 0.018, fill=RED, outline=OUTLINE, width=0.01)
    lamp(c, kb[2] - 0.06, kb[1] + 0.06, 0.016, GREEN)
    c.line([(kb[0], kb[3] - 0.05), (0.06, zh - 0.1)], fill=DARK, width=0.014)
    return b.result()


def radio_set(ppm):
    """Funkgeraet am Mast (Comms-Sabotage): Feldkiste mit Funkgeraet, Hoerer abgelegt, Antenne, Erdsockel."""
    body, trim = TINT["funkmast"]
    b = Block(-0.55, -0.34, 0.55, 0.3, 1.5 * K, ppm)
    c = b.c
    base_patch(b, -0.5, -0.3, 0.5, 0.26)
    crate = hexc("#9a7a52")
    x0, y0, x1, y1 = -0.44, -0.22, 0.44, 0.2
    b.box(x0, y0, x1, y1, 0, 0.6, shade(crate, 1.15), crate)
    c.rect(x0 + 0.03, y0 + 0.05, x1 - 0.03, y0 + 0.6 * K - 0.04, outline=hexc("#6e5234"), width=0.02)
    c.line([(x0 + 0.03, y0 + 0.05), (x1 - 0.03, y0 + 0.6 * K - 0.04)], fill=hexc("#6e5234"), width=0.025)
    c.line([(x1 - 0.03, y0 + 0.05), (x0 + 0.03, y0 + 0.6 * K - 0.04)], fill=hexc("#6e5234"), width=0.025)
    zt = y0 + 0.6 * K
    # Funkgeraet: Kasten auf der Kiste, Front nach Sueden
    rb = (x0 + 0.04, zt + 0.06, x0 + 0.6, zt + 0.42)
    face_radio(c, rb, body, trim)
    c.rect(rb[0], rb[3], rb[2], rb[3] + 0.06, fill=shade(OLIVE, 0.85), outline=OUTLINE, width=0.02)
    # Antenne oben rechts am Geraet
    c.line([(rb[2] - 0.06, rb[3] + 0.06), (rb[2] - 0.02, rb[3] + 0.55)], fill=OUTLINE, width=0.035)
    c.line([(rb[2] - 0.06, rb[3] + 0.06), (rb[2] - 0.02, rb[3] + 0.55)], fill=STEEL, width=0.016)
    c.ellipse(rb[2] - 0.02, rb[3] + 0.55, 0.014, 0.014, fill=RED, outline=OUTLINE, width=0.008)
    # Hoerer liegt rechts daneben (abgehoben: Stoerung), Spiralkabel zum Geraet
    hx, hy = x1 - 0.16, zt + 0.16
    c.line([(hx - 0.09, hy), (hx + 0.09, hy)], fill=OUTLINE, width=0.06)
    c.line([(hx - 0.09, hy), (hx + 0.09, hy)], fill=DARK, width=0.035)
    c.ellipse(hx - 0.09, hy, 0.035, 0.03, fill=DARK, outline=OUTLINE, width=0.015)
    c.ellipse(hx + 0.09, hy, 0.035, 0.03, fill=DARK, outline=OUTLINE, width=0.015)
    pts = [(hx - 0.12, hy + 0.02)]
    for i in range(6):
        pts.append((hx - 0.14 - i * 0.025, hy + 0.05 + (0.03 if i % 2 else 0.0) + i * 0.01))
    pts.append((rb[2] - 0.01, rb[1] + 0.12))
    c.line(pts, fill=OUTLINE, width=0.028)
    c.line(pts, fill=hexc("#3b4046"), width=0.014)
    # Notizblock mit Frequenz
    c.poly([(x1 - 0.3, zt + 0.32), (x1 - 0.14, zt + 0.32), (x1 - 0.12, zt + 0.44), (x1 - 0.28, zt + 0.44)], fill=CREAM, outline=OUTLINE, width=0.012)
    c.line([(x1 - 0.26, zt + 0.4), (x1 - 0.16, zt + 0.4)], fill=RED, width=0.01)
    return b.result()


# ------------------------------------------------------- Zuordnung

def _kind_of(name):
    """Task-Typ aus dem Konsolennamen (Skeld-Name -> Forststation-Designsprache)."""
    if "DivertPower" in name:
        return "divert"
    if name in ("DataConsole", "UploadDataConsole"):
        return "data"
    if "FixWiring" in name:
        return "wiring"
    if name in ("GarbageConsole", "AirlockConsole"):
        return "garbage"
    if name in ("NoOxyConsole", "UnlockManifoldsConsole"):
        return "keypad"
    if name in ("UpperHandConsole", "LowerHandConsole"):
        return "hand"
    if name == "SwitchConsole":
        return "fuse"
    if name == "CalibrateConsole":
        return "gauges"
    if name == "ChartCourseConsole":
        return "chart"
    if name == "WeaponConsole":
        return "spotter"
    if name == "ShieldConsole":
        return "weather"
    return None


def render_all(ppm):
    brief = json.loads((Path(__file__).resolve().parent / "wald_console_brief.json").read_text(encoding="utf-8"))
    out = {}
    for key, _x, _y, room, _kind, wall, _task in brief:
        parts = key.split("/")
        name = parts[1] if len(parts) == 3 else key
        if key == "EmergencyButton":
            out[key] = camp_bell(ppm)
        elif key == "SurveillanceConsole":
            out[key] = ranger_desk(ppm)
        elif key == "AdminTable":
            out[key] = map_board(ppm)
        elif key == "FreeplayLaptop":
            out[key] = crate_laptop(ppm)
        elif name == "SwipeCardConsole":
            out[key] = id_reader(ppm, room)
        elif name == "MedScanner":
            out[key] = floor_scanner(ppm)
        elif name == "MedBayConsole":
            out[key] = microscope_bench(ppm)
        elif name == "CleanFilterConsole":
            out[key] = water_filter(ppm)
        elif name == "FuelEngineConsole":
            out[key] = fuel_station(ppm, room)
        elif name == "AlignEngineConsole":
            out[key] = gauge_post(ppm, room)
        elif name == "gasCanConsole":
            out[key] = jerrycan_rack(ppm)
        elif name == "StartReactorConsole":
            out[key] = pump_terminal(ppm, room)
        elif name == "StabilizeSteeringConsole":
            out[key] = theodolite(ppm)
        elif name == "FixCommsConsole":
            out[key] = radio_set(ppm)
        else:
            kind = _kind_of(name)
            if kind is None:
                continue
            kw = {}
            if kind == "keypad":
                kw = dict(red=(name == "NoOxyConsole"))
            if kind == "data":
                kw = dict(upload=(name != "DataConsole"))
            out[key] = generic(kind, wall, room, ppm, dx=SHIFT_X.get(key, 0.0), **kw)
    return out


def contact_sheet(ppm=160, path=None):
    """Alle Bloecke auf neutralem Grund mit Ankerkreuz (Vorschau, nicht Teil der Pipeline)."""
    from PIL import ImageDraw
    sprites = render_all(ppm)
    keys = sorted(sprites)
    cols = 8
    cw = max(im.width for im, _a, _b in sprites.values()) + 16
    ch = max(im.height for im, _a, _b in sprites.values()) + 34
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols, ch * rows), (96, 100, 110))
    d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        im, ax, ay = sprites[k]
        x, y = (i % cols) * cw + 8, (i // cols) * ch + 26
        sheet.paste(im, (x, y), im)
        px, py = x + ax, y + im.height - ay
        d.line([(px - 6, py), (px + 6, py)], fill=(255, 60, 60), width=2)
        d.line([(px, py - 6), (px, py + 6)], fill=(255, 60, 60), width=2)
        d.text((x - 4, y - 22), k.split("/")[1] if "/" in k else k, fill=(255, 255, 255))
        d.text((x - 4, y - 11), (k.split("/")[0] + "/" + k.split("/")[2]) if "/" in k else "", fill=(200, 200, 200))
    if path:
        sheet.save(path)
    return sheet


if __name__ == "__main__":
    import sys
    import time
    t = time.time()
    p = sys.argv[1] if len(sys.argv) > 1 else "_wald/contact.png"
    contact_sheet(160, p)
    print(p, f"{time.time() - t:.1f}s")
