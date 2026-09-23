# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# museum_consoles.py - eigene Task-Bloecke (Konsolen-Sprites) des Vesper-Museums.
#
# SCHNITTSTELLE (gen_museum.py und der C#-Builder verlassen sich darauf):
#   render_all(ppm) -> dict  schluessel -> (PIL.Image RGBA, anchor_x_px, anchor_y_px)
#     schluessel  = Konsolen-Schluessel aus console_brief.json ("Room/Name/Id") oder einer der
#                   Sonderschluessel EmergencyButton, SurveillanceConsole, AdminTable, FreeplayLaptop
#     anchor      = Pixel im Bild (x von LINKS, y von UNTEN), das auf der Konsolen-Position
#                   (Welt-Transform) landet. Die Standlinie des Blocks sollte auf Hoehe des Ankers
#                   oder knapp darunter liegen: danach wird sortiert (vor/hinter Spielern).
#   Fehlt ein Schluessel, behaelt die Konsole ihr Skeld-Bild.
#   Rand: mindestens 6 px transparenter Rand ringsum (das Hervorheben zeichnet eine Kontur).
#
# GESTALTUNG
# Jeder Block wird in lokalen Weltmetern um die Konsolen-Position (0, 0) gezeichnet, in der
# schraegen Aufsicht von museum_art (Hoehe h steigt auf dem Bild um h * K, Licht von Nordwest,
# schwarze Umrisse, flache Flaechen mit heller Ober- und dunkler Unterkante).
# Montagearten (Spalte "wall" in console_brief.json):
#   N  : Standschrank an der sichtbaren Nordwand, Bedienflaeche auf der VORDERSEITE
#   S  : flache Bodeneinheit vor der (unsichtbaren) Suedwand, Bedienflaeche auf der DECKFLAECHE
#   E/W: schmaler Standschrank an der Seitenwand, Bedienflaeche als schraeges Pult (Deckflaeche)
#   -  : freistehendes Pult / Sockel / Tisch
# Designsprache je Task-Typ (in allen Raeumen gleich, nur Gehaeuse- und Zierfarbe je Raum):
#   Divert Power      Messing-Sicherungstafel mit Drehhebel und Kontrolllampen
#   Download/Upload   Datenterminal: Bernstein-Schirm mit Fortschrittsbalken, Kartenschlitz
#   Fix Wiring        Kabelkasten mit offener Tuer und vier unterbrochenen Adern
#   Empty Garbage     Muellschacht-Klappe mit Messinghebel
#   Sabotage-Stationen leuchten rot/amber (Loeschgas-Abbruch, Einbruchalarm-Handscanner,
#   Sicherungskasten, Vermittlungspult), Rest bleibt warnamber (Hausstil).

import math

from PIL import Image

from museum_art import Canvas, Prop, OUTLINE, K, OUT_W, hexc, lift, shade, alpha, WARM

# ------------------------------------------------------------------ Farben

AMBER = hexc("#e8a83c")          # warnamber, fuer 2D angehoben
AMBER_DARK = hexc("#6e4612")     # Schirmgrund
AMBER_HI = hexc("#ffd27a")       # Schirm-Text, Lampen
RED = hexc("#d84a4a")            # signalrot, angehoben
RED_DARK = hexc("#7a2424")
GREEN = hexc("#57d98a")
BRASS = lift("#b08a3c", 1.3)
BRASS_HI = hexc("#e6c76a")
DARK = hexc("#2a2f35")           # darkTrim (Konsolensockel, Bezel)
STEEL = hexc("#8b949a")
CHROME = hexc("#c0c8cc")
CCTV = hexc("#b7c4c8")
XRAY = hexc("#d8e6ec")
STARS = hexc("#cfe0ff")
WIRES = [hexc("#e05a3a"), hexc("#3f9fd8"), hexc("#e0b04a"), hexc("#e070b0")]

# Raumtoene: Gehaeuse (body) und Zierfarbe (trim), abgeleitet aus museum_stil.md
TINT = {
    "rotunde": (lift("#4c4a46", 1.7), BRASS),
    "foyer": (lift("#4a3222", 1.7), BRASS),
    "shop": (lift("#7a5636", 1.4), lift("#8fb0a4", 1.15)),
    "sicherheit": (lift("#363b40", 1.6), STEEL),
    "haustechnik": (lift("#7b8b8f", 1.3), hexc("#d4b13c")),
    "aegypten": (lift("#7a5f3e", 1.55), lift("#2f4f8a", 1.6)),
    "galerie": (lift("#5b2430", 1.55), hexc("#c9a04a")),
    "planetarium": (lift("#3a4048", 1.55), STARS),
    "mineralien": (lift("#4b5259", 1.55), lift("#2c555c", 1.6)),
    "telefon": (lift("#6b4a2e", 1.5), hexc("#c8702e")),
    "technikhalle": (lift("#2f4a3a", 1.7), CHROME),
    "werkstatt": (lift("#8b949a", 1.3), XRAY),
    "hof": (lift("#2f4f7a", 1.5), hexc("#b8bcbd")),
    "depot": (lift("#3f4a56", 1.55), lift("#7a5a3a", 1.4)),
    "-": (DARK, BRASS),
}


# ------------------------------------------------------------ Leinwand-Block

class Block:
    """Prop mit eigener, knapp bemessener Leinwand. Ursprung (0, 0) = Konsolen-Position."""

    PAD = 0.12       # transparenter Rand in m (>= 6 px ab 50 px/m)
    PAD_SHADOW = 0.28  # rechts/unten laeuft der weiche Schlagschatten aus (Versatz + Unschaerfe)

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


def unit(b, x0, y0, x1, y1, h, body, w=OUT_W, shadow=True):
    """Standschrank: Schlagschatten, Kasten, Fussleiste. Gibt (front, top) Rechtecke zurueck."""
    if shadow:
        b.shadow(x0, y0, x1, y1)
    b.box(x0, y0, x1, y1, 0, h, shade(body, 1.15), body, w=w)
    b.c.rect(x0 + 0.02, y0 + 0.015, x1 - 0.02, y0 + 0.06, fill=shade(body, 0.6))
    i = 0.04
    front = (x0 + i, y0 + 0.07, x1 - i, y0 + h * K - i)
    top = (x0 + i, y0 + h * K + i, x1 - i, y1 + h * K - i)
    return front, top


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


def shrink(r, dx, dy=None):
    dy = dx if dy is None else dy
    return (r[0] + dx, r[1] + dy, r[2] - dx, r[3] - dy)


def fit(r, w, h):
    """Rechteck w x h mittig in r (Bedienflaeche kleiner als die Gehaeuseflaeche)."""
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    w = min(w, r[2] - r[0]); h = min(h, r[3] - r[1])
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


# ------------------------------------------------------- Bedienflaechen

def face_divert(c, r, body, trim):
    """Messing-Sicherungstafel: Drehhebel, drei Lampen, Beschriftungsschild."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=BRASS, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=BRASS_HI, width=0.015)
    inner = shrink(r, 0.045)
    c.rect(*inner, fill=shade(BRASS, 0.72))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rr = min(x1 - x0, y1 - y0) * 0.26
    # Drehhebel mit Skalenpunkten
    for a in (-60, -20, 20, 60):
        ang = math.radians(90 + a)
        c.ellipse(cx + math.cos(ang) * rr * 1.35, cy + 0.02 + math.sin(ang) * rr * 1.35, 0.012, 0.012, fill=DARK)
    c.ellipse(cx, cy + 0.02, rr, rr, fill=DARK, outline=OUTLINE, width=0.02)
    c.ellipse(cx, cy + 0.02, rr * 0.7, rr * 0.7, fill=BRASS_HI, outline=OUTLINE, width=0.015)
    ang = math.radians(115)
    c.line([(cx - math.cos(ang) * rr * 0.45, cy + 0.02 - math.sin(ang) * rr * 0.45),
            (cx + math.cos(ang) * rr * 0.95, cy + 0.02 + math.sin(ang) * rr * 0.95)], fill=DARK, width=0.03)
    # Lampenreihe unten
    ly = y0 + 0.07
    for i, col in enumerate((AMBER_HI, AMBER_HI, RED)):
        lamp(c, x0 + 0.08 + i * 0.09, ly, 0.022, col, on=(i != 1))
    # Schild
    c.rect(x1 - 0.17, y0 + 0.045, x1 - 0.05, y0 + 0.095, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
    c.line([(x1 - 0.15, y0 + 0.07), (x1 - 0.07, y0 + 0.07)], fill=DARK, width=0.012)


def face_data(c, r, body, trim, upload=True):
    """Datenterminal: Bernstein-Schirm mit Balken, Kartenschlitz, Status-LED."""
    x0, y0, x1, y1 = r
    bezel(c, r, DARK)
    s = (x0 + 0.05, y0 + (y1 - y0) * 0.38, x1 - 0.05, y1 - 0.05)
    screen(c, s)
    sx0, sy0, sx1, sy1 = s
    # Datenzeilen + Fortschrittsbalken + Pfeil (hoch = Upload, runter = Download)
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
    # Kartenschlitz + LED + Tastenpaar
    sl = y0 + (y1 - y0) * 0.2
    c.rect(x0 + 0.06, sl - 0.012, x1 - 0.14, sl + 0.012, fill=hexc("#101216"), outline=shade(DARK, 1.5), width=0.01)
    lamp(c, x1 - 0.08, sl, 0.02, GREEN)
    for i in range(2):
        c.rect(x0 + 0.06 + i * 0.07, y0 + 0.03, x0 + 0.11 + i * 0.07, y0 + 0.065, fill=STEEL, outline=OUTLINE, width=0.01)


def face_wiring(c, r, body, trim):
    """Kabelkasten: graues Gehaeuse, offene Tuer rechts, vier Adern mit Bruchstelle."""
    x0, y0, x1, y1 = r
    box_c = lift("#7b8288", 1.25)
    c.rect(x0, y0, x1, y1, fill=box_c, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(box_c, 1.3), width=0.014)
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
    # offene Tuer (nach rechts geklappt, verjuengt)
    dw = (x1 - x0) * 0.55
    c.poly([(x1, y0 + 0.01), (x1 + dw, y0 + 0.06), (x1 + dw, y1 - 0.06), (x1, y1 - 0.01)],
           fill=shade(box_c, 0.85), outline=OUTLINE, width=0.022)
    c.line([(x1 + 0.03, y1 - 0.02), (x1 + dw - 0.02, y1 - 0.07)], fill=shade(box_c, 1.2), width=0.012)
    c.rect(x1 + dw - 0.06, (y0 + y1) / 2 - 0.03, x1 + dw - 0.035, (y0 + y1) / 2 + 0.03, fill=DARK)
    # Warnschild auf der Tuer
    tx, ty = x1 + dw / 2, (y0 + y1) / 2
    c.poly([(tx - 0.045, ty - 0.035), (tx + 0.045, ty - 0.035), (tx, ty + 0.045)], fill=hexc("#d4b13c"), outline=OUTLINE, width=0.012)
    c.line([(tx + 0.008, ty + 0.02), (tx - 0.008, ty - 0.002), (tx + 0.008, ty - 0.005), (tx - 0.006, ty - 0.025)], fill=DARK, width=0.008)


def face_garbage(c, r, body, trim):
    """Muellschacht: dunkle Klappe mit Griff, Messinghebel mit rotem Knauf, Pfeile."""
    x0, y0, x1, y1 = r
    steel = lift("#6f7a7f", 1.3)
    c.rect(x0, y0, x1, y1, fill=steel, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(steel, 1.3), width=0.014)
    fx1 = x1 - 0.16
    flap = (x0 + 0.05, y0 + 0.08, fx1, y1 - 0.06)
    c.rect(*flap, fill=hexc("#3a4046"), outline=OUTLINE, width=0.02)
    c.line([(flap[0] + 0.02, flap[3] - 0.02), (flap[2] - 0.02, flap[3] - 0.02)], fill=hexc("#5a636a"), width=0.012)
    c.rect(flap[0] + 0.04, flap[3] - 0.08, flap[2] - 0.04, flap[3] - 0.055, fill=hexc("#5a636a"), outline=OUTLINE, width=0.01)
    mx = (flap[0] + flap[2]) / 2
    c.poly([(mx - 0.035, flap[1] + 0.09), (mx + 0.035, flap[1] + 0.09), (mx, flap[1] + 0.04)], fill=hexc("#d4b13c"))
    c.rect(mx - 0.012, flap[1] + 0.09, mx + 0.012, flap[1] + 0.13, fill=hexc("#d4b13c"))
    # Hebel in einer Kulisse
    hx = x1 - 0.085
    c.rect(hx - 0.02, y0 + 0.07, hx + 0.02, y1 - 0.07, fill=hexc("#1f2428"), outline=OUTLINE, width=0.012)
    c.line([(hx, y0 + 0.14), (hx + 0.045, y1 - 0.08)], fill=OUTLINE, width=0.05)
    c.line([(hx, y0 + 0.14), (hx + 0.045, y1 - 0.08)], fill=BRASS, width=0.028)
    c.ellipse(hx + 0.045, y1 - 0.08, 0.032, 0.032, fill=RED, outline=OUTLINE, width=0.015)
    c.ellipse(hx + 0.035, y1 - 0.07, 0.01, 0.01, fill=(255, 255, 255, 170))


def face_keypad(c, r, body, trim, red=False, label="CO2"):
    """Zahlentastatur mit kleinem Display; rot = Loeschgas-Abbruch (Sabotage-Station)."""
    x0, y0, x1, y1 = r
    housing = RED_DARK if red else DARK
    c.rect(x0, y0, x1, y1, fill=housing, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(housing, 1.5), width=0.014)
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
        # Loeschgas-Symbol: roter Ring mit Balken ueber dem Display
        lamp(c, x1 - 0.045, y1 - 0.03, 0.02, RED)
        lamp(c, x0 + 0.045, y1 - 0.03, 0.02, RED)


def face_hand(c, r, body, trim):
    """Einbruchalarm-Handscanner: Bernstein-Scheibe mit Handsilhouette, rote Alarmlampe."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=DARK, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(DARK, 1.6), width=0.014)
    s = (x0 + 0.045, y0 + 0.07, x1 - 0.045, y1 - 0.09)
    screen(c, s, base=hexc("#5a3a0e"), strength=0.4)
    sx0, sy0, sx1, sy1 = s
    cx = (sx0 + sx1) / 2
    hw = (sx1 - sx0) * 0.28
    palm_y = sy0 + (sy1 - sy0) * 0.36
    c.ellipse(cx, palm_y, hw, (sy1 - sy0) * 0.26, fill=AMBER_HI)
    fingers = ((-0.75, 0.55), (-0.3, 0.95), (0.15, 1.0), (0.6, 0.85))
    for fx, fl in fingers:
        c.line([(cx + fx * hw, palm_y + 0.02), (cx + fx * hw * 1.05, palm_y + (sy1 - sy0) * 0.45 * fl)], fill=AMBER_HI, width=hw * 0.42)
    c.line([(cx - hw * 0.9, palm_y - 0.03), (cx - hw * 1.55, palm_y + (sy1 - sy0) * 0.18)], fill=AMBER_HI, width=hw * 0.4)
    # Scanlinie
    c.line([(sx0 + 0.02, palm_y + 0.05), (sx1 - 0.02, palm_y + 0.05)], fill=(255, 255, 255, 130), width=0.012)
    lamp(c, (x0 + x1) / 2 - 0.05, y0 + 0.035, 0.02, RED)
    lamp(c, (x0 + x1) / 2 + 0.05, y0 + 0.035, 0.02, GREEN, on=False)
    c.rect(x0 + 0.05, y1 - 0.065, x1 - 0.05, y1 - 0.03, fill=RED, outline=OUTLINE, width=0.01)


def face_fuse(c, r, body, trim):
    """Sicherungskasten (Licht-Sabotage): Schrankfront mit Warnband, Blitzschild, Griff."""
    x0, y0, x1, y1 = r
    col = lift("#7b8b8f", 1.35)
    c.rect(x0, y0, x1, y1, fill=col, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(col, 1.3), width=0.014)
    c.rect(x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04, outline=shade(col, 0.72), width=0.015)
    # Warnband unten
    by0, by1 = y0 + 0.06, y0 + 0.13
    c.rect(x0 + 0.05, by0, x1 - 0.05, by1, fill=hexc("#d4b13c"))
    xx = x0 + 0.05
    while xx < x1 - 0.05:
        c.poly([(xx, by0), (min(x1 - 0.05, xx + 0.04), by0), (min(x1 - 0.05, xx + 0.08), by1), (min(x1 - 0.05, xx + 0.04), by1)], fill=hexc("#1e1e1e"))
        xx += 0.08
    c.rect(x0 + 0.05, by0, x1 - 0.05, by1, outline=OUTLINE, width=0.012)
    # Blitz-Warndreieck
    tx, ty = (x0 + x1) / 2, (y0 + y1) / 2 + 0.06
    c.poly([(tx - 0.075, ty - 0.06), (tx + 0.075, ty - 0.06), (tx, ty + 0.07)], fill=hexc("#d4b13c"), outline=OUTLINE, width=0.015)
    c.line([(tx + 0.014, ty + 0.03), (tx - 0.012, ty - 0.005), (tx + 0.012, ty - 0.01), (tx - 0.01, ty - 0.045)], fill=DARK, width=0.012)
    c.rect(x1 - 0.085, ty - 0.05, x1 - 0.06, ty + 0.05, fill=DARK, outline=OUTLINE, width=0.01)
    lamp(c, x0 + 0.08, y1 - 0.075, 0.02, RED)
    lamp(c, x0 + 0.135, y1 - 0.075, 0.02, AMBER_HI)


def face_gauges(c, r, body, trim):
    """Verteiler-Kalibrierung: drei Zeigerinstrumente, Drehknoepfe, Bernstein-Anzeige."""
    x0, y0, x1, y1 = r
    col = lift("#7b8b8f", 1.3)
    c.rect(x0, y0, x1, y1, fill=col, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(col, 1.3), width=0.014)
    n = 3
    gw = (x1 - x0) / n
    for i in range(n):
        gx = x0 + gw * (i + 0.5)
        gy = y1 - 0.12
        rr = min(gw * 0.36, 0.085)
        c.ellipse(gx, gy, rr, rr, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.018)
        for a in range(200, 341, 35):
            ang = math.radians(a)
            c.line([(gx + math.cos(ang) * rr * 0.65, gy - math.sin(ang) * rr * 0.65), (gx + math.cos(ang) * rr * 0.85, gy - math.sin(ang) * rr * 0.85)], fill=DARK, width=0.01)
        c.poly([(gx + math.cos(math.radians(300)) * rr * 0.4, gy - math.sin(math.radians(300)) * rr * 0.4),
                (gx - math.cos(math.radians(300)) * rr * 0.4, gy + math.sin(math.radians(300)) * rr * 0.4),
                (gx, gy + rr * 0.15)], fill=RED)
        ang = math.radians(215 + i * 55)
        c.line([(gx, gy), (gx + math.cos(ang) * rr * 0.8, gy - math.sin(ang) * rr * 0.8)], fill=DARK, width=0.014)
        c.ellipse(gx, gy, 0.012, 0.012, fill=DARK)
        # Drehknopf unter jedem Instrument
        c.ellipse(gx, y0 + 0.07, 0.03, 0.03, fill=DARK, outline=OUTLINE, width=0.012)
        c.line([(gx, y0 + 0.07), (gx + math.cos(ang) * 0.025, y0 + 0.07 + math.sin(ang) * 0.025)], fill=AMBER_HI, width=0.01)
    c.rect(x0 + 0.05, y0 + 0.13, x1 - 0.05, y0 + 0.19, fill=AMBER_DARK, outline=OUTLINE, width=0.012)
    c.line([(x0 + 0.07, y0 + 0.16), (x0 + 0.07 + (x1 - x0 - 0.14) * 0.55, y0 + 0.16)], fill=AMBER_HI, width=0.018)


def face_stars(c, r, body, trim):
    """Sternkarte: kalter Schirm (Planetarium-Ausnahme) mit Sternbild und Kurslinie."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=hexc("#1e2230"), outline=OUTLINE, width=0.025)
    s = shrink(r, 0.04)
    screen(c, s, base=hexc("#141a2c"), glowc=STARS, strength=0.35)
    sx0, sy0, sx1, sy1 = s
    pts = [(0.15, 0.7), (0.32, 0.55), (0.5, 0.6), (0.62, 0.35), (0.8, 0.28), (0.3, 0.25), (0.72, 0.75), (0.88, 0.6), (0.45, 0.85), (0.2, 0.4)]
    wpts = [(sx0 + (sx1 - sx0) * u, sy0 + (sy1 - sy0) * v) for u, v in pts]
    c.line(wpts[:5], fill=alpha(STARS, 170), width=0.012)
    for i, (px_, py_) in enumerate(wpts):
        rr = 0.016 if i < 5 else 0.01
        c.ellipse(px_, py_, rr, rr, fill=STARS)
    # Zielkreis + Kurspfeil (Bernstein, die eine warme Markierung)
    tx, ty = wpts[4]
    c.ellipse(tx, ty, 0.04, 0.04, outline=AMBER_HI, width=0.012)
    c.line([(wpts[0][0], wpts[0][1]), (tx - 0.03, ty + 0.01)], fill=AMBER_HI, width=0.01)


def face_frames(c, r, body, trim):
    """Galerie-Terminal (Bilderrahmen ausrichten): Schirm mit schiefen Goldrahmen, Joystick."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=DARK, outline=OUTLINE, width=0.025)
    s = (x0 + 0.05, y0 + (y1 - y0) * 0.36, x1 - 0.05, y1 - 0.05)
    screen(c, s, base=hexc("#4a1e26"), glowc=WARM, strength=0.3)
    sx0, sy0, sx1, sy1 = s
    gold = hexc("#c9a04a")
    for i, (u, v, rot) in enumerate(((0.28, 0.5, 12), (0.68, 0.5, -8))):
        fx, fy = sx0 + (sx1 - sx0) * u, sy0 + (sy1 - sy0) * v
        w, h = (sx1 - sx0) * 0.3, (sy1 - sy0) * 0.55
        ang = math.radians(rot)
        corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        rc = [(fx + a * math.cos(ang) - b * math.sin(ang), fy + a * math.sin(ang) + b * math.cos(ang)) for a, b in corners]
        c.poly(rc, fill=gold, outline=OUTLINE, width=0.012)
        inner = [(fx + (a * 0.6) * math.cos(ang) - (b * 0.6) * math.sin(ang), fy + (a * 0.6) * math.sin(ang) + (b * 0.6) * math.cos(ang)) for a, b in corners]
        c.poly(inner, fill=hexc("#d9d2c0") if i else hexc("#3f6f9a"))
    # Joystick + zwei Tasten
    jx, jy = (x0 + x1) / 2, y0 + (y1 - y0) * 0.17
    c.ellipse(jx, jy, 0.05, 0.03, fill=hexc("#1f2428"), outline=OUTLINE, width=0.012)
    c.line([(jx, jy), (jx + 0.02, jy + 0.08)], fill=OUTLINE, width=0.035)
    c.line([(jx, jy), (jx + 0.02, jy + 0.08)], fill=STEEL, width=0.018)
    c.ellipse(jx + 0.02, jy + 0.09, 0.025, 0.025, fill=RED, outline=OUTLINE, width=0.012)
    for i in range(2):
        c.ellipse(x1 - 0.09 + i * 0.045, jy, 0.018, 0.018, fill=AMBER_HI if i else GREEN, outline=OUTLINE, width=0.01)


def face_shield(c, r, body, trim):
    """Tresorvitrinen-Sicherung: Feld aus Sechseck-Tastern (rot = offen), Schluesselschalter."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=DARK, outline=OUTLINE, width=0.025)
    c.line([(x0 + 0.02, y1 - 0.02), (x1 - 0.02, y1 - 0.02)], fill=shade(DARK, 1.6), width=0.014)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 0.02
    rr = 0.038
    cells = [(0, 0)] + [(math.cos(math.radians(a)) * rr * 2.1, math.sin(math.radians(a)) * rr * 2.1) for a in range(0, 360, 60)]
    for i, (dx, dy) in enumerate(cells):
        hx, hy = cx + dx, cy + dy
        col = RED if i in (1, 3, 5) else AMBER_HI
        c.poly([(hx + rr * math.cos(math.radians(a + 30)), hy + rr * math.sin(math.radians(a + 30))) for a in range(0, 360, 60)],
               fill=col, outline=OUTLINE, width=0.012)
        c.ellipse(hx - rr * 0.25, hy + rr * 0.25, rr * 0.2, rr * 0.2, fill=(255, 255, 255, 140))
    # Schluesselschalter
    kx, ky = x1 - 0.07, y0 + 0.07
    c.ellipse(kx, ky, 0.03, 0.03, fill=STEEL, outline=OUTLINE, width=0.012)
    c.line([(kx - 0.018, ky - 0.012), (kx + 0.018, ky + 0.012)], fill=DARK, width=0.012)


def face_switchboard(c, r, body, trim):
    """Telefonanlage: Klinkenfeld mit Lampen und Stoepselschnueren, roter Stoerungsmelder."""
    x0, y0, x1, y1 = r
    c.rect(x0, y0, x1, y1, fill=hexc("#2a2422"), outline=OUTLINE, width=0.025)
    nx, ny = 5, 3
    cw, ch = (x1 - x0 - 0.08) / nx, (y1 - y0 - 0.1) / ny
    for i in range(nx):
        for j in range(ny):
            jx, jy = x0 + 0.04 + cw * (i + 0.5), y0 + 0.05 + ch * (j + 0.5)
            c.ellipse(jx, jy, 0.018, 0.018, fill=hexc("#b0a890"), outline=OUTLINE, width=0.01)
            c.ellipse(jx, jy, 0.007, 0.007, fill=DARK)
            if j == ny - 1:
                lamp(c, jx, jy + ch * 0.42, 0.012, RED if i % 2 else AMBER_HI, on=(i != 2))
    for (i0, j0, i1, j1, col) in ((0, 2, 3, 0, hexc("#e05a3a")), (4, 1, 1, 0, hexc("#3f9e6e"))):
        ax_, ay_ = x0 + 0.04 + cw * (i0 + 0.5), y0 + 0.05 + ch * (j0 + 0.5)
        bx_, by_ = x0 + 0.04 + cw * (i1 + 0.5), y0 + 0.05 + ch * (j1 + 0.5)
        c.line([(ax_, ay_), ((ax_ + bx_) / 2, min(ay_, by_) - 0.03), (bx_, by_)], fill=OUTLINE, width=0.03)
        c.line([(ax_, ay_), ((ax_ + bx_) / 2, min(ay_, by_) - 0.03), (bx_, by_)], fill=col, width=0.016)


# ------------------------------------------------------- Montage-Arten

FACES = {
    "divert": face_divert, "data": face_data, "wiring": face_wiring, "garbage": face_garbage,
    "keypad": face_keypad, "hand": face_hand, "fuse": face_fuse, "gauges": face_gauges,
    "stars": face_stars, "frames": face_frames, "shield": face_shield, "switchboard": face_switchboard,
}

# Bedienflaechen-Groesse (Breite, Hoehe) je Typ; die Gehaeuse werden darum herum bemessen
FACE_SIZE = {
    "divert": (0.38, 0.34), "data": (0.42, 0.46), "wiring": (0.30, 0.30), "garbage": (0.44, 0.36),
    "keypad": (0.36, 0.44), "hand": (0.36, 0.46), "fuse": (0.50, 0.58), "gauges": (0.54, 0.40),
    "stars": (0.62, 0.48), "frames": (0.56, 0.60), "shield": (0.40, 0.40), "switchboard": (0.6, 0.36),
}


def mount_n(b, kind, body, trim, dx=0.0, **kw):
    """Standschrank an der Nordwand: Front zeigt nach Sueden, Bedienflaeche auf der Front.
    dx verschiebt den Schrank seitlich (Anker bleibt), wenn er sonst ein Schild streift."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0     # Platz fuer die offene Tuer
    w = fw + 0.12
    h = (fh + 0.18) / K
    x0, x1 = -w / 2 - extra / 2 + dx, w / 2 - extra / 2 + dx
    front, _top = unit(b, x0, 0.0, x1, 0.26, h, body)
    r = fit(front, fw, fh)
    r = (r[0], front[1] + 0.06, r[2], front[1] + 0.06 + fh)
    FACES[kind](b.c, r, body, trim, **kw)
    # Zierleiste in Raumfarbe auf der Deckflaeche
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
    b.c.rect(front[0] + 0.02, front[1] + 0.02, front[2] - 0.02, front[3] - 0.02, outline=shade(body, 0.72), width=0.015)
    b.c.rect((x0 + x1) / 2 - 0.05, front[1] + 0.08, (x0 + x1) / 2 + 0.05, front[1] + 0.1, fill=trim)
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


def mount_side(b, kind, body, trim, east=True, **kw):
    """Schmaler Standschrank an der Ost-/Westwand: Bedienflaeche als schraeges Pult (Deckflaeche)."""
    fw, fh = FACE_SIZE[kind]
    extra = 0.22 if kind == "wiring" else 0.0
    w = fw + 0.12
    d = fh + 0.1
    h = 0.7
    if east:
        x0, x1 = 0.02, 0.02 + w
    else:
        x0, x1 = -0.02 - w, -0.02
    if kind == "wiring":
        # offene Tuer klappt nach rechts (Osten); im Westen Platz lassen
        if east:
            x0, x1 = 0.02 - extra, 0.02 - extra + w
    y0, y1 = -d / 2, d / 2
    front, top = unit(b, x0, y0, x1, y1, h, body)
    b.c.rect(front[0] + 0.02, front[1] + 0.02, front[2] - 0.02, front[3] - 0.02, outline=shade(body, 0.72), width=0.015)
    b.c.rect(front[0] + 0.05, front[1] + 0.08, front[2] - 0.05, front[1] + 0.105, fill=trim)
    b.c.rect((x0 + x1) / 2 - 0.03, front[1] + 0.17, (x0 + x1) / 2 + 0.03, front[1] + 0.19, fill=shade(body, 0.6))
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


def mount_free(b, kind, body, trim, **kw):
    """Freistehendes Pult: Saeule mit aufgesetztem Pultkopf, Bedienflaeche oben."""
    fw, fh = FACE_SIZE[kind]
    w = fw + 0.12
    d = fh + 0.1
    hp = 0.72
    x0, x1 = -w / 2, w / 2
    y0, y1 = -0.18, 0.18
    b.shadow(x0, y0 - 0.06, x1, y1 + 0.1)
    pw = min(0.3, w * 0.6)
    b.box(-pw / 2, y0 + 0.05, pw / 2, y1 - 0.05, 0, hp, shade(body, 1.1), shade(body, 0.92))
    b.c.rect(-pw / 2 - 0.04, y0 + 0.03, pw / 2 + 0.04, y0 + 0.09, fill=shade(body, 0.6), outline=OUTLINE, width=0.02)
    hy0, hy1 = -d / 2, d / 2
    b.box(x0, hy0, x1, hy1, hp, 0.14, shade(body, 1.15), body)
    b.c.rect(x0 + 0.04, hy0 + hp * K + 0.03, x1 - 0.04, hy0 + hp * K + 0.055, fill=trim)
    top = (x0 + 0.04, hy0 + (hp + 0.14) * K + 0.04, x1 - 0.04, hy1 + (hp + 0.14) * K - 0.04)
    r = fit(top, fw, fh)
    FACES[kind](b.c, r, body, trim, **kw)


# seitlicher Versatz einzelner Nordwand-Schraenke (m), damit sie kein Notausgangsschild streifen
SHIFT_X = {"LifeSupp/DivertPowerConsole/1": 0.14, "Electrical/CalibrateConsole/0": 0.12}


def generic(kind, wall, room, ppm, dx=0.0, **kw):
    body, trim = TINT.get(room, TINT["-"])
    fw, fh = FACE_SIZE[kind]
    extra = 0.3 if kind == "wiring" else 0.0
    if wall == "N":
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
        b = Block(-w / 2 - 0.1, -max(0.24, d / 2 + 0.02), w / 2 + 0.1, max(0.2, d / 2), 0.86 * K, ppm)
        mount_free(b, kind, body, trim, **kw)
    return b.result()


# ------------------------------------------------------- Sonderbloecke

def swipe_card(ppm, room="shop"):
    """Museumskasse: Kartenleser-Terminal auf Holzsaeule mit Quittungsrolle."""
    body, trim = TINT[room]
    b = Block(-0.34, -0.26, 0.34, 0.2, 0.95 * K, ppm)
    c = b.c
    b.shadow(-0.22, -0.22, 0.22, 0.16)
    b.box(-0.16, -0.16, 0.16, 0.12, 0, 0.8, shade(body, 1.1), body)
    c.rect(-0.2, -0.18, 0.2, -0.12, fill=shade(body, 0.6), outline=OUTLINE, width=0.02)
    # Pultkopf mit Display, Kartenschlitz (Messing) und Tastenfeld
    b.box(-0.26, -0.2, 0.26, 0.14, 0.8, 0.14, shade(body, 1.15), body)
    ty = -0.2 + 0.94 * K
    top = (-0.22, ty + 0.04, 0.22, 0.14 + 0.94 * K - 0.04)
    bezel(c, top, DARK)
    screen(c, (-0.18, ty + 0.16, 0.05, ty + 0.3), strength=0.3)
    c.line([(-0.15, ty + 0.25), (-0.02, ty + 0.25)], fill=AMBER_HI, width=0.014)
    c.line([(-0.15, ty + 0.2), (0.0, ty + 0.2)], fill=AMBER_HI, width=0.014)
    c.rect(0.09, ty + 0.14, 0.19, ty + 0.31, fill=BRASS, outline=OUTLINE, width=0.015)
    c.rect(0.115, ty + 0.17, 0.165, ty + 0.29, fill=hexc("#101216"))
    for i in range(3):
        for j in range(2):
            c.rect(-0.17 + i * 0.07, ty + 0.06 + j * 0.04, -0.12 + i * 0.07, ty + 0.09 + j * 0.04, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.01)
    lamp(c, 0.14, ty + 0.08, 0.02, GREEN)
    # Ticketkarte steckt halb im Schlitz
    c.poly([(0.1, ty + 0.3), (0.18, ty + 0.3), (0.2, ty + 0.4), (0.12, ty + 0.4)], fill=hexc("#3f6f9a"), outline=OUTLINE, width=0.012)
    c.line([(0.13, ty + 0.36), (0.18, ty + 0.36)], fill=hexc("#e8e0d0"), width=0.012)
    return b.result()


def emergency_button(ppm):
    """Notfallknopf: Messingsaeule auf der gelb-schwarzen Bodenplatte, roter Pilztaster unter Glas."""
    b = Block(-0.34, -0.3, 0.34, 0.3, 1.2 * K, ppm)
    c = b.c
    brass = BRASS
    c.soft_shadow([(-0.2 + 0.05, -0.28), (0.2 + 0.09, -0.28), (0.2 + 0.09, 0.12), (-0.2 + 0.05, 0.12)], 90, 0.06)
    b.cyl(0, 0, 0.26, 0, 0.08, shade(brass, 0.95), shade(brass, 0.75), ry=0.18)
    b.cyl(0, 0, 0.16, 0.08, 0.72, shade(brass, 1.05), brass, ry=0.11)
    # Saeulenglanz + Rillen
    c.line([(-0.1, 0.1 * K + 0.02), (-0.1, 0.78 * K - 0.02)], fill=BRASS_HI, width=0.025)
    for z in (0.3, 0.55):
        c.line([(-0.16, z * K), (0.16, z * K)], fill=shade(brass, 0.7), width=0.015)
    # Kopfplatte mit rotem Ring
    b.cyl(0, 0, 0.24, 0.8, 0.07, shade(brass, 1.1), shade(brass, 0.85), ry=0.17)
    zt = 0.87 * K
    c.ellipse(0, zt, 0.2, 0.14, fill=RED_DARK, outline=OUTLINE, width=0.02)
    c.ellipse(0, zt, 0.16, 0.11, fill=DARK)
    # Pilztaster
    c.ellipse(0, zt + 0.02, 0.13, 0.09, fill=shade(RED, 0.75), outline=OUTLINE, width=0.02)
    c.rect(-0.13, zt + 0.02, 0.13, zt + 0.1, fill=shade(RED, 0.75))
    c.line([(-0.13, zt + 0.02), (-0.13, zt + 0.1)], fill=OUTLINE, width=0.02)
    c.line([(0.13, zt + 0.02), (0.13, zt + 0.1)], fill=OUTLINE, width=0.02)
    c.ellipse(0, zt + 0.1, 0.13, 0.09, fill=RED, outline=OUTLINE, width=0.02)
    c.ellipse(-0.04, zt + 0.13, 0.05, 0.03, fill=(255, 255, 255, 150))
    c.glow(0, zt + 0.08, 0.35, RED, 0.35)
    # Glashaube (durchsichtig) mit Messingring
    c.ellipse(0, zt + 0.05, 0.19, 0.16, fill=alpha(hexc("#bfe3f5"), 55), outline=alpha(hexc("#e9f7ff"), 200), width=0.02)
    c.line([(-0.13, zt + 0.06), (-0.09, zt + 0.17)], fill=(255, 255, 255, 140), width=0.02)
    # Schild an der Saeule
    c.rect(-0.1, 0.35 * K, 0.1, 0.5 * K, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
    c.line([(-0.07, 0.43 * K), (0.07, 0.43 * K)], fill=RED, width=0.03)
    return b.result()


def surveillance(ppm):
    """Kamerapult der Sicherheitszentrale: Tisch nach Westen mit drei CCTV-Monitoren, Stuhl im Osten."""
    body, trim = TINT["sicherheit"]
    b = Block(-0.9, -0.62, 0.8, 0.62, 1.3 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.75, -0.55, -0.05, 0.55
    b.shadow(x0, y0, x1, y1)
    desk = lift("#3a3f46", 1.6)
    b.box(x0, y0, x1, y1, 0, 0.78, shade(desk, 1.15), desk)
    c.rect(x0 + 0.03, y0 + 0.02, x1 - 0.03, y0 + 0.07, fill=shade(desk, 0.6))
    # Schubladen an der Front
    for i in range(2):
        c.rect(x0 + 0.05 + i * 0.34, y0 + 0.12, x0 + 0.34 + i * 0.34, y0 + 0.36, outline=shade(desk, 0.7), width=0.015)
        c.rect(x0 + 0.15 + i * 0.34, y0 + 0.22, x0 + 0.24 + i * 0.34, y0 + 0.25, fill=STEEL)
    zt = 0.78 * K
    # Monitorreihe am Westrand (auf dem Tisch, nach Osten gedreht: als Frontflaechen gezeichnet)
    mon_x0, mon_x1 = x0 + 0.06, x0 + 0.5
    for i, my in enumerate((y1 - 0.2, y1 - 0.62, y1 - 1.04)):
        mb = my + zt
        c.rect(mon_x0, mb - 0.02, mon_x1, mb + 0.34, fill=hexc("#1e2226"), outline=OUTLINE, width=0.02)
        c.rect(mon_x0 + 0.04, mb + 0.02, mon_x1 - 0.04, mb + 0.3, fill=hexc("#4a6a7a") if i == 1 else hexc("#6f8fa0"))
        c.rect(mon_x0 + 0.07, mb + 0.12, mon_x1 - 0.07, mb + 0.22, fill=CCTV)
        c.ellipse(mon_x0 + 0.15 + i * 0.1, mb + 0.17, 0.025, 0.025, fill=hexc("#e05a3a"), outline=OUTLINE, width=0.01)
        c.ellipse(mon_x1 - 0.08, mb + 0.27, 0.014, 0.014, fill=RED)
    c.glow(x0 + 0.3, zt + 0.1, 0.55, CCTV, 0.3)
    # Tastatur, Maus, Kaffeebecher, Funkgeraet
    c.rect(x0 + 0.56, y0 + 0.35 + zt, x1 - 0.08, y0 + 0.62 + zt, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
    for j in range(3):
        for i in range(6):
            c.rect(x0 + 0.585 + i * 0.045, y0 + 0.37 + j * 0.08 + zt, x0 + 0.615 + i * 0.045, y0 + 0.42 + j * 0.08 + zt, fill=STEEL)
    c.ellipse(x1 - 0.14, y0 + 0.25 + zt, 0.035, 0.05, fill=hexc("#1e2226"), outline=OUTLINE, width=0.012)
    c.ellipse(x1 - 0.12, y1 - 0.15 + zt, 0.05, 0.04, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
    c.rect(x0 + 0.56, y1 - 0.3 + zt, x0 + 0.72, y1 - 0.12 + zt, fill=DARK, outline=OUTLINE, width=0.012)
    lamp(c, x0 + 0.68, y1 - 0.16 + zt, 0.012, RED)
    # Buerostuhl oestlich vom Pult (dort steht der Spieler nicht: Nutzradius liegt oestlich)
    sx, sy = 0.3, 0.0
    c.soft_shadow([(sx - 0.22, sy - 0.25), (sx + 0.3, sy - 0.25), (sx + 0.3, sy + 0.2), (sx - 0.22, sy + 0.2)], 80, 0.05)
    for a in range(0, 360, 72):
        c.line([(sx, sy), (sx + 0.2 * math.cos(math.radians(a)), sy + 0.14 * math.sin(math.radians(a)))], fill=OUTLINE, width=0.05)
        c.line([(sx, sy), (sx + 0.2 * math.cos(math.radians(a)), sy + 0.14 * math.sin(math.radians(a)))], fill=hexc("#3b4046"), width=0.025)
    b.cyl(sx, sy, 0.035, 0, 0.45, hexc("#3b4046"), hexc("#2a2f35"), w=0.02, ry=0.025)
    b.cyl(sx, sy, 0.22, 0.45, 0.08, hexc("#3f4a56"), hexc("#2a2f35"), w=0.025, ry=0.16)
    b.box(sx + 0.16, sy - 0.18, sx + 0.24, sy + 0.18, 0.53, 0.5, hexc("#3f4a56"), hexc("#2a2f35"), w=0.025)
    return b.result()


def admin_lectern(ppm):
    """Gebaeudeplan-Pult vor dem Admin-Tisch: Stehpult mit Bernstein-Grundriss und Standortpunkten."""
    body, trim = TINT["sicherheit"]
    b = Block(-0.42, -0.3, 0.42, 0.24, 1.25 * K, ppm)
    c = b.c
    b.shadow(-0.3, -0.22, 0.3, 0.16)
    b.box(-0.12, -0.14, 0.12, 0.1, 0, 0.85, shade(body, 1.1), shade(body, 0.92))
    c.rect(-0.2, -0.16, 0.2, -0.1, fill=shade(body, 0.6), outline=OUTLINE, width=0.02)
    b.box(-0.36, -0.24, 0.36, 0.2, 0.85, 0.12, shade(body, 1.15), body)
    c.rect(-0.32, -0.24 + 0.85 * K + 0.03, 0.32, -0.24 + 0.85 * K + 0.055, fill=STEEL)
    ty0 = -0.24 + 0.97 * K
    top = (-0.32, ty0 + 0.04, 0.32, 0.2 + 0.97 * K - 0.04)
    bezel(c, top, DARK)
    s = shrink(top, 0.04)
    screen(c, s, strength=0.35)
    sx0, sy0, sx1, sy1 = s
    # stilisierter Grundriss: Raster aus Raeumen, Hauptachse, Rotunde als Kreis
    line = AMBER
    for u in (0.25, 0.5, 0.75):
        c.line([(sx0 + (sx1 - sx0) * u, sy0 + 0.02), (sx0 + (sx1 - sx0) * u, sy1 - 0.02)], fill=line, width=0.01)
    for v in (0.33, 0.66):
        c.line([(sx0 + 0.02, sy0 + (sy1 - sy0) * v), (sx1 - 0.02, sy0 + (sy1 - sy0) * v)], fill=line, width=0.01)
    c.rect(sx0 + 0.02, sy0 + 0.02, sx1 - 0.02, sy1 - 0.02, outline=line, width=0.012)
    cx, cy = (sx0 + sx1) / 2, sy0 + (sy1 - sy0) * 0.66
    c.ellipse(cx, cy, 0.05, 0.04, fill=shade(AMBER_DARK, 0.7), outline=AMBER_HI, width=0.012)
    for (u, v) in ((0.15, 0.2), (0.62, 0.5), (0.85, 0.8), (0.4, 0.85)):
        c.ellipse(sx0 + (sx1 - sx0) * u, sy0 + (sy1 - sy0) * v, 0.014, 0.014, fill=AMBER_HI)
    c.text(sx1 - 0.06, sy0 + 0.05, "N", 0.07, AMBER_HI)
    return b.result()


def freeplay_laptop(ppm):
    """Freeplay-Laptop auf einem kleinen Stehtisch (Messing-Fuss, Holzplatte)."""
    b = Block(-0.34, -0.3, 0.34, 0.24, 1.1 * K, ppm)
    c = b.c
    c.soft_shadow([(-0.16, -0.24), (0.24, -0.24), (0.24, 0.12), (-0.16, 0.12)], 80, 0.06)
    b.cyl(0, -0.02, 0.2, 0, 0.04, shade(BRASS, 0.9), shade(BRASS, 0.7), ry=0.14)
    b.cyl(0, -0.02, 0.03, 0.04, 0.7, BRASS, shade(BRASS, 0.8), w=0.02, ry=0.02)
    top = lift("#7a5636", 1.5)
    b.cyl(0, -0.02, 0.28, 0.74, 0.05, shade(top, 1.1), top, ry=0.2)
    zt = -0.02 + 0.79 * K
    # Laptop: Unterteil (Tastatur) + hochgeklappter Deckel mit Schirm
    lp = hexc("#6b7378")
    c.poly([(-0.17, zt - 0.08), (0.17, zt - 0.08), (0.19, zt + 0.06), (-0.19, zt + 0.06)], fill=lp, outline=OUTLINE, width=0.02)
    c.rect(-0.14, zt - 0.05, 0.14, zt + 0.02, fill=hexc("#1e2226"))
    c.rect(-0.03, zt - 0.075, 0.03, zt - 0.06, fill=hexc("#1e2226"))
    c.rect(-0.2, zt + 0.06, 0.2, zt + 0.34, fill=shade(lp, 0.9), outline=OUTLINE, width=0.02)
    screen(c, (-0.17, zt + 0.09, 0.17, zt + 0.31), strength=0.3)
    c.line([(-0.13, zt + 0.25), (0.02, zt + 0.25)], fill=AMBER_HI, width=0.014)
    c.line([(-0.13, zt + 0.2), (0.08, zt + 0.2)], fill=AMBER_HI, width=0.014)
    c.line([(-0.13, zt + 0.15), (-0.03, zt + 0.15)], fill=AMBER_HI, width=0.014)
    c.ellipse(0.11, zt + 0.14, 0.025, 0.025, fill=GREEN)
    # Kaffeebecher
    c.ellipse(0.24, zt - 0.03, 0.035, 0.028, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.012)
    return b.result()


def med_scanner(ppm):
    """Roentgen-Echtheitsscanner: Bodenring aus Edelstahl mit vier Emittern und hinterem Portalbogen."""
    b = Block(-0.85, -0.7, 0.85, 0.7, 1.7 * K, ppm)
    c = b.c
    steel = lift("#8b949a", 1.35)
    rx, ry = 0.72, 0.5
    c.ellipse(0.05, -0.05, rx, ry, fill=alpha((8, 10, 16, 255), 70))
    # flacher Ring (Plattform 8 cm)
    c.ellipse(0, 0, rx, ry, fill=shade(steel, 0.8), outline=OUTLINE)
    c.rect(-rx, 0, rx, 0.08 * K, fill=shade(steel, 0.8))
    c.line([(-rx, 0), (-rx, 0.08 * K)], fill=OUTLINE, width=OUT_W)
    c.line([(rx, 0), (rx, 0.08 * K)], fill=OUTLINE, width=OUT_W)
    zt = 0.08 * K
    c.ellipse(0, zt, rx, ry, fill=steel, outline=OUTLINE)
    c.ellipse(0, zt, rx - 0.12, ry - 0.09, fill=hexc("#3a4046"), outline=OUTLINE, width=0.03)
    c.ellipse(0, zt, rx - 0.2, ry - 0.15, outline=alpha(XRAY, 220), width=0.035)
    c.ellipse(0, zt, rx - 0.34, ry - 0.25, outline=alpha(XRAY, 120), width=0.02)
    c.glow(0, zt, 0.7, XRAY, 0.4)
    # Fusssymbole in der Mitte (wo man sich hinstellt)
    for sx in (-0.07, 0.07):
        c.ellipse(sx, zt + 0.02, 0.035, 0.06, fill=alpha(XRAY, 200))
    # vier Emitter: hinten hoch mit Portalbogen, vorn niedrig
    def post(px, py, h, r=0.07):
        b.cyl(px, py, r, 0.08, h, shade(steel, 1.15), shade(steel, 0.9), w=0.025, ry=r * 0.7)
        c.ellipse(px, py + (0.08 + h) * K, r * 0.6, r * 0.42, fill=XRAY, outline=OUTLINE, width=0.012)
    post(-0.5, 0.28, 1.4); post(0.5, 0.28, 1.4)
    c.rect(-0.5, 0.28 + 1.48 * K - 0.04, 0.5, 0.28 + 1.48 * K + 0.06, fill=steel, outline=OUTLINE, width=0.025)
    c.line([(-0.45, 0.28 + 1.48 * K + 0.035), (0.45, 0.28 + 1.48 * K + 0.035)], fill=shade(steel, 1.3), width=0.015)
    for i in range(5):
        c.ellipse(-0.36 + i * 0.18, 0.28 + 1.48 * K + 0.01, 0.018, 0.014, fill=XRAY)
    c.rect(-0.12, 0.28 + 1.48 * K + 0.06, 0.12, 0.28 + 1.48 * K + 0.12, fill=DARK, outline=OUTLINE, width=0.012)
    lamp(c, 0, 0.28 + 1.48 * K + 0.09, 0.015, GREEN)
    post(-0.55, -0.3, 0.45); post(0.55, -0.3, 0.45)
    return b.result()


def sample_analyzer(ppm):
    """Analysegeraet der Werkstatt: Edelstahlschrank, Probenkammer mit Glas, Schirm, Reagenzroehrchen."""
    body, trim = TINT["werkstatt"]
    b = Block(-0.5, -0.3, 0.5, 0.3, 1.55 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.22, 0.4, 0.22
    front, top = unit(b, x0, y0, x1, y1, 0.95, body)
    # Frontseite: Probenkammer (Glasklappe) links, Schirm rechts
    ch = (x0 + 0.06, y0 + 0.12, x0 + 0.36, y0 + 0.44)
    c.rect(*ch, fill=hexc("#1e2226"), outline=OUTLINE, width=0.02)
    for i in range(5):
        tx = ch[0] + 0.05 + i * 0.05
        col = [hexc("#3f9e6e"), hexc("#e05a3a"), hexc("#3f9fd8"), hexc("#e0b04a"), hexc("#9d6cc7")][i]
        c.rect(tx - 0.012, ch[1] + 0.05, tx + 0.012, ch[1] + 0.2, fill=col, outline=OUTLINE, width=0.01)
        c.rect(tx - 0.014, ch[1] + 0.2, tx + 0.014, ch[1] + 0.24, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.01)
    c.rect(ch[0] + 0.02, ch[1] + 0.02, ch[2] - 0.02, ch[3] - 0.02, fill=alpha(hexc("#bfe3f5"), 55), outline=alpha(hexc("#e9f7ff"), 200), width=0.015)
    c.line([(ch[0] + 0.05, ch[1] + 0.06), (ch[0] + 0.09, ch[3] - 0.06)], fill=(255, 255, 255, 120), width=0.018)
    s = (x0 + 0.44, y0 + 0.2, x1 - 0.06, y0 + 0.44)
    screen(c, s, base=hexc("#1e3a2a"), glowc=GREEN, strength=0.3)
    pts = [(s[0] + 0.02 + i * (s[2] - s[0] - 0.04) / 8, s[1] + 0.06 + [0.02, 0.09, 0.03, 0.14, 0.05, 0.1, 0.02, 0.07, 0.03][i]) for i in range(9)]
    c.line(pts, fill=GREEN, width=0.012)
    for i in range(3):
        c.ellipse(x0 + 0.48 + i * 0.09, y0 + 0.13, 0.02, 0.02, fill=[GREEN, AMBER_HI, RED][i], outline=OUTLINE, width=0.01)
    # Deckflaeche: Mikroskop-Kopf und Probenschale
    c.rect(top[0] + 0.05, top[1] + 0.02, top[2] - 0.05, top[3] - 0.02, fill=shade(body, 1.05), outline=shade(body, 0.75), width=0.012)
    mx, my = x0 + 0.62, (top[1] + top[3]) / 2
    b.cyl(mx, my - 0.02, 0.06, 0.95, 0.2, DARK, hexc("#3b4046"), w=0.02, ry=0.04)
    c.poly([(mx - 0.03, my + 0.2 * K), (mx + 0.03, my + 0.2 * K), (mx + 0.06, my + 0.2 * K + 0.16), (mx, my + 0.2 * K + 0.16)], fill=hexc("#3b4046"), outline=OUTLINE, width=0.015)
    c.ellipse(x0 + 0.2, my, 0.1, 0.06, fill=hexc("#e8e0d0"), outline=OUTLINE, width=0.015)
    c.ellipse(x0 + 0.2, my, 0.05, 0.03, fill=hexc("#7a8a4a"))
    return b.result()


def clean_station(ppm):
    """Skelett abstauben: Pflegewagen mit Staubwedel, Eimer, Tuechern und Hinweisschild."""
    body, trim = TINT["rotunde"]
    b = Block(-0.5, -0.32, 0.5, 0.3, 1.5 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.2, 0.3, 0.2
    b.shadow(x0, y0, x1, y1)
    wood = lift("#7a5636", 1.4)
    # Wagen: zwei Boeden auf Rollen
    for wx in (x0 + 0.08, x1 - 0.12):
        for wy in (y0 + 0.04, y1 - 0.08):
            c.ellipse(wx, wy, 0.035, 0.025, fill=hexc("#1e2226"), outline=OUTLINE, width=0.012)
    for z in (0.08, 0.5):
        b.box(x0, y0, x1, y1, z, 0.05, shade(wood, 1.15), wood, w=0.025)
    for px_ in (x0 + 0.03, x1 - 0.06):
        for py_ in (y0 + 0.02, y1 - 0.05):
            c.rect(px_, py_ + 0.13 * K, px_ + 0.03, py_ + 0.5 * K, fill=BRASS, outline=OUTLINE, width=0.015)
    zt = 0.55 * K
    # unteres Fach: Eimer + Flaschen (Front)
    c.ellipse(x0 + 0.2, y0 + 0.13 * K + 0.04, 0.09, 0.03, fill=hexc("#3f6f9a"), outline=OUTLINE, width=0.012)
    c.rect(x0 + 0.11, y0 + 0.13 * K + 0.04, x0 + 0.29, y0 + 0.13 * K + 0.2, fill=hexc("#3f6f9a"))
    c.line([(x0 + 0.11, y0 + 0.13 * K + 0.04), (x0 + 0.11, y0 + 0.13 * K + 0.2)], fill=OUTLINE, width=0.015)
    c.line([(x0 + 0.29, y0 + 0.13 * K + 0.04), (x0 + 0.29, y0 + 0.13 * K + 0.2)], fill=OUTLINE, width=0.015)
    c.ellipse(x0 + 0.2, y0 + 0.13 * K + 0.2, 0.09, 0.03, fill=shade(hexc("#3f6f9a"), 1.2), outline=OUTLINE, width=0.012)
    for i, col in enumerate(("#e05a3a", "#3f9e6e")):
        bx = x1 - 0.2 + i * 0.09
        c.rect(bx - 0.03, y0 + 0.13 * K + 0.04, bx + 0.03, y0 + 0.13 * K + 0.19, fill=hexc(col), outline=OUTLINE, width=0.012)
        c.rect(bx - 0.015, y0 + 0.13 * K + 0.19, bx + 0.015, y0 + 0.13 * K + 0.23, fill=DARK)
    # obere Platte: gefaltete Tuecher, Pinselbecher, Staubwedel (Federn) aufrecht
    c.rect(x0 + 0.05, y0 + zt + 0.12, x0 + 0.3, y0 + zt + 0.3, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.015)
    c.rect(x0 + 0.05, y0 + zt + 0.2, x0 + 0.3, y0 + zt + 0.3, fill=hexc("#d8cfb0"), outline=OUTLINE, width=0.015)
    b.cyl(x1 - 0.18, y0 + 0.2, 0.05, 0.55, 0.12, hexc("#3b4046"), hexc("#2a2f35"), w=0.015, ry=0.035)
    for i in range(4):
        c.line([(x1 - 0.2 + i * 0.015, y0 + 0.2 + 0.67 * K), (x1 - 0.24 + i * 0.03, y0 + 0.2 + 0.67 * K + 0.12)], fill=hexc("#7a5636"), width=0.012)
    # Staubwedel: Stiel + Federbusch
    sx, sy = x0 + 0.12, y0 + zt + 0.2
    c.line([(sx, sy), (sx + 0.05, sy + 0.42)], fill=OUTLINE, width=0.04)
    c.line([(sx, sy), (sx + 0.05, sy + 0.42)], fill=BRASS, width=0.02)
    for i in range(7):
        ang = math.radians(60 + i * 12)
        col = [hexc("#e05a3a"), hexc("#e0b04a"), hexc("#3f9e6e"), hexc("#9d6cc7")][i % 4]
        c.line([(sx + 0.05, sy + 0.42), (sx + 0.05 + math.cos(ang) * 0.16, sy + 0.42 + math.sin(ang) * 0.16)], fill=OUTLINE, width=0.045)
        c.line([(sx + 0.05, sy + 0.42), (sx + 0.05 + math.cos(ang) * 0.16, sy + 0.42 + math.sin(ang) * 0.16)], fill=col, width=0.025)
    # Hinweisschild "Pflege" am Wagen
    c.rect(x1 - 0.02, y0 + 0.1, x1 + 0.16, y0 + 0.36, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.015)
    c.line([(x1 + 0.02, y0 + 0.28), (x1 + 0.12, y0 + 0.28)], fill=DARK, width=0.012)
    c.line([(x1 + 0.02, y0 + 0.22), (x1 + 0.1, y0 + 0.22)], fill=DARK, width=0.012)
    c.line([(x1 + 0.02, y0 + 0.16), (x1 + 0.12, y0 + 0.16)], fill=RED, width=0.012)
    return b.result()


def fuel_pump(ppm, room):
    """Tankstutzen: Zapfsaeule in Raumfarbe mit Zaehlwerk, Schlauch und Zapfpistole."""
    body, trim = TINT[room]
    b = Block(-0.44, -0.3, 0.44, 0.26, 1.4 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.22, -0.2, 0.22, 0.2
    front, top = unit(b, x0, y0, x1, y1, 1.25, body)
    c.rect(front[0] + 0.02, front[1] + 0.02, front[2] - 0.02, front[3] - 0.02, outline=shade(body, 0.72), width=0.015)
    # Zaehlwerk (Bernstein) + Kanister-Symbol + Warnband
    s = (x0 + 0.06, y0 + 0.44, x1 - 0.06, y0 + 0.58)
    screen(c, s, strength=0.3)
    for i in range(3):
        c.rect(s[0] + 0.03 + i * 0.09, s[1] + 0.03, s[0] + 0.09 + i * 0.09, s[3] - 0.03, fill=AMBER_HI)
    c.rect(x0 + 0.08, y0 + 0.2, x1 - 0.08, y0 + 0.38, fill=RED, outline=OUTLINE, width=0.015)
    c.rect(x0 + 0.12, y0 + 0.38, x0 + 0.2, y0 + 0.41, fill=DARK)
    c.line([(x0 + 0.1, y0 + 0.36), (x1 - 0.1, y0 + 0.36)], fill=shade(RED, 1.3), width=0.012)
    c.rect(x0 + 0.05, y0 + 0.1, x1 - 0.05, y0 + 0.16, fill=hexc("#d4b13c"), outline=OUTLINE, width=0.01)
    for i in range(4):
        xx = x0 + 0.06 + i * 0.09
        c.poly([(xx, y0 + 0.1), (xx + 0.035, y0 + 0.1), (xx + 0.07, y0 + 0.16), (xx + 0.035, y0 + 0.16)], fill=hexc("#1e1e1e"))
    lamp(c, x1 - 0.09, y0 + 0.64, 0.02, AMBER_HI)
    # Schlauch rechts herunter, Zapfpistole in der Halterung
    c.line([(x1 - 0.02, y0 + 0.62), (x1 + 0.12, y0 + 0.5), (x1 + 0.1, y0 + 0.2), (x1 - 0.02, y0 + 0.16)], fill=OUTLINE, width=0.055)
    c.line([(x1 - 0.02, y0 + 0.62), (x1 + 0.12, y0 + 0.5), (x1 + 0.1, y0 + 0.2), (x1 - 0.02, y0 + 0.16)], fill=hexc("#1e2226"), width=0.03)
    c.poly([(x1 - 0.03, y0 + 0.66), (x1 + 0.06, y0 + 0.66), (x1 + 0.06, y0 + 0.76), (x1 + 0.12, y0 + 0.78), (x1 + 0.12, y0 + 0.82), (x1 - 0.03, y0 + 0.82)],
           fill=RED, outline=OUTLINE, width=0.015)
    # Deckflaeche: Chrom-Leiste in Raumzierfarbe
    c.rect(top[0] + 0.02, top[1] + 0.02, top[2] - 0.02, top[3] - 0.02, fill=trim)
    return b.result()


def align_gauge(ppm, room):
    """Ausrichtung (Align Engine): Messsaeule mit grossem Rundinstrument und Stellhebel."""
    body, trim = TINT[room]
    b = Block(-0.4, -0.3, 0.4, 0.24, 1.25 * K, ppm)
    c = b.c
    b.shadow(-0.2, -0.22, 0.2, 0.16)
    b.box(-0.14, -0.16, 0.14, 0.12, 0, 0.75, shade(body, 1.1), shade(body, 0.92))
    c.rect(-0.2, -0.18, 0.2, -0.12, fill=shade(body, 0.6), outline=OUTLINE, width=0.02)
    # Instrumentenkopf: grosse Scheibe mit Skala, Zeiger, Sollmarke, seitlicher Hebel
    zt = -0.16 + 0.78 * K
    c.ellipse(0, zt + 0.02, 0.29, 0.29, fill=shade(body, 0.7), outline=OUTLINE, width=0.03)
    c.ellipse(0, zt + 0.04, 0.29, 0.29, fill=body, outline=OUTLINE, width=0.03)
    c.ellipse(0, zt + 0.04, 0.23, 0.23, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.02)
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
    # Stellhebel rechts
    c.line([(0.27, zt), (0.36, zt + 0.16)], fill=OUTLINE, width=0.05)
    c.line([(0.27, zt), (0.36, zt + 0.16)], fill=STEEL, width=0.025)
    c.ellipse(0.36, zt + 0.16, 0.035, 0.035, fill=hexc("#1e2226"), outline=OUTLINE, width=0.015)
    return b.result()


def gas_can_rack(ppm):
    """Kanister holen (Depot): Stahlregalbrett an der Suedwand mit rotem Kanister und Tropfwanne."""
    body, trim = TINT["depot"]
    b = Block(-0.5, -0.24, 0.5, 0.3, 0.9 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.16, 0.4, 0.24
    b.shadow(x0, y0, x1, y1)
    # Tropfwanne (flach, gelb-schwarz) und Gitterboden darueber
    b.box(x0, y0, x1, y1, 0, 0.08, hexc("#d4b13c"), hexc("#d4b13c"), w=0.025)
    for i in range(6):
        xx = x0 + 0.05 + i * 0.13
        c.poly([(xx, y0 + 0.005), (xx + 0.05, y0 + 0.005), (xx + 0.1, y0 + 0.08 * K - 0.005), (xx + 0.05, y0 + 0.08 * K - 0.005)], fill=hexc("#1e1e1e"))
    zt = 0.08 * K
    c.rect(x0 + 0.04, y0 + zt + 0.04, x1 - 0.04, y1 + zt - 0.04, fill=shade(body, 0.8))
    yy = y0 + zt + 0.06
    while yy < y1 + zt - 0.05:
        c.line([(x0 + 0.05, yy), (x1 - 0.05, yy)], fill=shade(body, 1.2), width=0.012)
        yy += 0.05
    # roter Kanister (Hauptmotiv) + kleiner Reservekanister
    def can(px, py, w, h, col):
        b.box(px - w / 2, py - 0.08, px + w / 2, py + 0.08, 0.08, h, shade(col, 1.15), col, w=0.025)
        c.line([(px - w / 2 + 0.03, py - 0.08 + 0.16 * K), (px + w / 2 - 0.03, py - 0.08 + 0.16 * K)], fill=shade(col, 0.7), width=0.012)
        c.rect(px - 0.02, py + 0.08 + (0.08 + h) * K - 0.005, px + 0.02, py + 0.08 + (0.08 + h) * K + 0.05, fill=DARK, outline=OUTLINE, width=0.012)
        c.line([(px - 0.05, py + 0.08 + (0.08 + h) * K + 0.03), (px + 0.05, py + 0.08 + (0.08 + h) * K + 0.03)], fill=OUTLINE, width=0.025)
        c.rect(px - w / 2 + 0.03, py - 0.08 + 0.4 * h * K, px + w / 2 - 0.03, py - 0.08 + 0.4 * h * K + 0.07, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.01)
    can(-0.12, 0.04, 0.3, 0.55, RED)
    can(0.22, 0.02, 0.2, 0.42, hexc("#3f4a56"))
    c.text(-0.12, 0.04 - 0.08 + 0.4 * 0.55 * K + 0.035, "FUEL", 0.05, DARK)
    return b.result()


def climate_terminal(ppm, room="aegypten"):
    """Start Reactor: grosses Klimasteuerungs-Terminal an der Westwand (Sandstein-Gehaeuse, Lapis-Zier)."""
    body, trim = TINT[room]
    b = Block(-0.72, -0.5, 0.2, 0.44, 1.35 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.62, -0.4, -0.02, 0.36
    front, top = unit(b, x0, y0, x1, y1, 1.2, body)
    # Frontseite: Lueftungsgitter + zwei Instrumente + grosser Startknopf
    c.rect(x0 + 0.06, y0 + 0.1, x1 - 0.06, y0 + 0.24, fill=shade(body, 0.7), outline=OUTLINE, width=0.015)
    for i in range(5):
        c.line([(x0 + 0.09, y0 + 0.12 + i * 0.025), (x1 - 0.09, y0 + 0.12 + i * 0.025)], fill=shade(body, 1.1), width=0.008)
    c.rect(x0 + 0.04, y0 + 0.3, x1 - 0.04, y0 + 0.6, fill=DARK, outline=OUTLINE, width=0.02)
    for i in range(2):
        gx = x0 + 0.15 + i * 0.3
        c.ellipse(gx, y0 + 0.45, 0.08, 0.08, fill=hexc("#efe4c8"), outline=OUTLINE, width=0.015)
        ang = math.radians(200 + i * 60)
        c.line([(gx, y0 + 0.45), (gx + math.cos(ang) * 0.06, y0 + 0.45 - math.sin(ang) * 0.06)], fill=RED, width=0.012)
        c.ellipse(gx, y0 + 0.45, 0.01, 0.01, fill=DARK)
    lamp(c, x1 - 0.1, y0 + 0.36, 0.022, RED)
    lamp(c, x1 - 0.1, y0 + 0.54, 0.022, GREEN, on=False)
    # Deckflaeche: Pult mit zwei Handflaechen-Feldern (das Reaktor-Minispiel hat zwei Haende) + Schirm
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
        hx = tx0 + 0.16 + i * 0.28
        c.rect(hx - 0.1, ty0 + 0.03, hx + 0.1, ty0 + 0.2, fill=hexc("#5a3a0e"), outline=OUTLINE, width=0.012)
        c.ellipse(hx, ty0 + 0.09, 0.05, 0.04, fill=AMBER_HI)
        for fx in (-0.045, -0.015, 0.015, 0.045):
            c.line([(hx + fx, ty0 + 0.11), (hx + fx, ty0 + 0.17)], fill=AMBER_HI, width=0.02)
    return b.result()


def projector_desk(ppm):
    """Projektor-Steuerpult (Stabilize Steering): Schreibpult mit Fadenkreuz-Schirm und Joystick."""
    body, trim = TINT["planetarium"]
    b = Block(-0.5, -0.32, 0.5, 0.3, 1.25 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.4, -0.2, 0.4, 0.2
    front, top = unit(b, x0, y0, x1, y1, 0.85, body)
    c.rect(front[0] + 0.02, front[1] + 0.02, front[2] - 0.02, front[3] - 0.02, outline=shade(body, 0.72), width=0.015)
    c.rect(front[0] + 0.1, front[1] + 0.14, front[2] - 0.1, front[1] + 0.17, fill=trim)
    tx0, ty0, tx1, ty1 = top
    c.rect(tx0, ty0, tx1, ty1, fill=shade(body, 0.85), outline=shade(body, 0.7), width=0.012)
    # Schirm mit Fadenkreuz und driftendem Punkt (kalt: Planetarium-Ausnahme)
    s = (tx0 + 0.04, ty0 + 0.04, tx0 + 0.44, ty1 - 0.04)
    screen(c, s, base=hexc("#141a2c"), glowc=STARS, strength=0.35)
    cx, cy = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
    c.line([(cx, s[1] + 0.02), (cx, s[3] - 0.02)], fill=alpha(STARS, 150), width=0.008)
    c.line([(s[0] + 0.02, cy), (s[2] - 0.02, cy)], fill=alpha(STARS, 150), width=0.008)
    c.ellipse(cx, cy, 0.07, 0.06, outline=alpha(STARS, 200), width=0.01)
    c.ellipse(cx + 0.06, cy - 0.04, 0.018, 0.018, fill=AMBER_HI)
    # Joystick + Tastenreihe + Schieberegler
    jx, jy = tx1 - 0.16, cy
    c.ellipse(jx, jy, 0.06, 0.04, fill=hexc("#1f2428"), outline=OUTLINE, width=0.012)
    c.line([(jx, jy), (jx + 0.03, jy + 0.1)], fill=OUTLINE, width=0.04)
    c.line([(jx, jy), (jx + 0.03, jy + 0.1)], fill=STEEL, width=0.02)
    c.ellipse(jx + 0.03, jy + 0.11, 0.03, 0.03, fill=RED, outline=OUTLINE, width=0.012)
    for i in range(3):
        c.rect(tx1 - 0.25 + i * 0.06, ty0 + 0.03, tx1 - 0.21 + i * 0.06, ty0 + 0.06, fill=[GREEN, AMBER_HI, STEEL][i], outline=OUTLINE, width=0.01)
    c.rect(tx1 - 0.08, ty0 + 0.03, tx1 - 0.06, ty1 - 0.03, fill=hexc("#101216"))
    c.rect(tx1 - 0.095, cy + 0.02, tx1 - 0.045, cy + 0.05, fill=STEEL, outline=OUTLINE, width=0.01)
    return b.result()


def switchboard_desk(ppm):
    """Telefonanlage (Comms-Sabotage): Vermittlungspult mit Klinkenfeld, Hoerer und Bakelit-Telefon."""
    body, trim = TINT["telefon"]
    b = Block(-0.6, -0.34, 0.6, 0.3, 1.1 * K, ppm)
    c = b.c
    x0, y0, x1, y1 = -0.5, -0.22, 0.5, 0.22
    front, top = unit(b, x0, y0, x1, y1, 0.8, body)
    c.rect(front[0] + 0.02, front[1] + 0.02, front[2] - 0.02, front[3] - 0.02, outline=shade(body, 0.72), width=0.015)
    c.rect(front[0] + 0.06, front[1] + 0.12, front[2] - 0.06, front[1] + 0.16, fill=trim)
    for i in range(2):
        c.rect(front[0] + 0.1 + i * 0.44, front[1] + 0.2, front[0] + 0.4 + i * 0.44, front[1] + 0.34, outline=shade(body, 0.7), width=0.012)
        c.rect(front[0] + 0.22 + i * 0.44, front[1] + 0.26, front[0] + 0.28 + i * 0.44, front[1] + 0.285, fill=BRASS)
    tx0, ty0, tx1, ty1 = top
    c.rect(tx0, ty0, tx1, ty1, fill=shade(body, 0.85), outline=shade(body, 0.7), width=0.012)
    # Klinkenfeld links, Telefon rechts, Hoerer daneben abgelegt (Schnur zum Feld)
    face_switchboard(c, (tx0 + 0.04, ty0 + 0.04, tx0 + 0.6, ty1 - 0.04), body, trim)
    ph = hexc("#2a2422")
    px, py = tx1 - 0.2, (ty0 + ty1) / 2 - 0.02
    c.poly([(px - 0.12, py - 0.09), (px + 0.12, py - 0.09), (px + 0.09, py + 0.08), (px - 0.09, py + 0.08)], fill=ph, outline=OUTLINE, width=0.02)
    c.ellipse(px, py - 0.01, 0.06, 0.05, fill=hexc("#d8cfb0"), outline=OUTLINE, width=0.012)
    for a in range(0, 360, 36):
        c.ellipse(px + math.cos(math.radians(a)) * 0.042, py - 0.01 + math.sin(math.radians(a)) * 0.035, 0.007, 0.007, fill=ph)
    # Hoerer liegt neben dem Telefon (abgehoben: Stoerung!)
    hx, hy = px + 0.02, py + 0.16
    c.line([(hx - 0.1, hy), (hx + 0.1, hy)], fill=OUTLINE, width=0.06)
    c.line([(hx - 0.1, hy), (hx + 0.1, hy)], fill=ph, width=0.035)
    c.ellipse(hx - 0.1, hy, 0.035, 0.03, fill=ph, outline=OUTLINE, width=0.015)
    c.ellipse(hx + 0.1, hy, 0.035, 0.03, fill=ph, outline=OUTLINE, width=0.015)
    c.line([(hx - 0.13, hy - 0.02), (hx - 0.2, hy - 0.08), (px - 0.1, py - 0.06)], fill=OUTLINE, width=0.03)
    c.line([(hx - 0.13, hy - 0.02), (hx - 0.2, hy - 0.08), (px - 0.1, py - 0.06)], fill=hexc("#c8702e"), width=0.015)
    lamp(c, tx1 - 0.06, ty1 - 0.06, 0.025, RED)
    c.glow(tx1 - 0.06, ty1 - 0.06, 0.16, RED, 0.4)
    return b.result()


# ------------------------------------------------------- Zuordnung

def _kind_of(name):
    """Task-Typ aus dem Konsolennamen (Skeld-Name -> Museums-Designsprache)."""
    if "DivertPower" in name:
        return "divert"
    if name in ("DataConsole", "UploadDataConsole"):
        return "data"
    if "FixWiring" in name:
        return "wiring"
    if name in ("GarbageConsole", "AirlockConsole"):
        return "garbage"
    if name == "NoOxyConsole":
        return "keypad"
    if name in ("UpperHandConsole", "LowerHandConsole"):
        return "hand"
    if name == "SwitchConsole":
        return "fuse"
    if name == "CalibrateConsole":
        return "gauges"
    if name == "ChartCourseConsole":
        return "stars"
    if name == "WeaponConsole":
        return "frames"
    if name == "ShieldConsole":
        return "shield"
    if name == "UnlockManifoldsConsole":
        return "keypad"
    return None


def render_all(ppm):
    import json
    from pathlib import Path
    brief = json.loads((Path(__file__).resolve().parent / "console_brief.json").read_text(encoding="utf-8"))
    out = {}
    for key, _x, _y, room, wall, _task in brief:
        parts = key.split("/")
        name = parts[1] if len(parts) == 3 else key
        if key == "EmergencyButton":
            out[key] = emergency_button(ppm)
        elif key == "SurveillanceConsole":
            out[key] = surveillance(ppm)
        elif key == "AdminTable":
            out[key] = admin_lectern(ppm)
        elif key == "FreeplayLaptop":
            out[key] = freeplay_laptop(ppm)
        elif name == "SwipeCardConsole":
            out[key] = swipe_card(ppm, room)
        elif name == "MedScanner":
            out[key] = med_scanner(ppm)
        elif name == "MedBayConsole":
            out[key] = sample_analyzer(ppm)
        elif name == "CleanFilterConsole":
            out[key] = clean_station(ppm)
        elif name == "FuelEngineConsole":
            out[key] = fuel_pump(ppm, room)
        elif name == "AlignEngineConsole":
            out[key] = align_gauge(ppm, room)
        elif name == "gasCanConsole":
            out[key] = gas_can_rack(ppm)
        elif name == "StartReactorConsole":
            out[key] = climate_terminal(ppm, room)
        elif name == "StabilizeSteeringConsole":
            out[key] = projector_desk(ppm)
        elif name == "FixCommsConsole":
            out[key] = switchboard_desk(ppm)
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
    p = sys.argv[1] if len(sys.argv) > 1 else "_consoles_preview/contact.png"
    contact_sheet(160, p)
    print(p, f"{time.time() - t:.1f}s")
