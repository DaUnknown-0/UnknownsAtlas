# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_consoles.py - Task-Bloecke (Konsolen-Sprites) des Moonlight Carnival.
#
# Nutzt den Baukasten von wald_consoles.py (gleiche Schnittstelle wie dort: render_all -> dict
# schluessel -> (Bild, Anker-x, Anker-y)), mit Park-Farben je Bereich. Die Montageart (Nord-, Sued-,
# Seitenwand, freistehend, Lichtung) ergibt sich aus der Konsolenposition im Grundriss statt aus
# einer Hand-Tabelle. Eigene Motive, wo der Wald nicht passt: Zuckerwattewagen (Clean Filter) und
# Popcorn statt Laub auf der Muellklappe.

import math

import park_layout as L
import wald_consoles as WC
from museum_art import OUTLINE, K, hexc, lift, shade, alpha

RED = lift("#8e2e36", 1.5)
GOLD = hexc("#e2b64a")
PLUM = lift("#4a3060", 1.6)
CREAM = hexc("#eadcbc")
PINK = hexc("#ff7fc4")

# Gehaeuse (body) und Zierfarbe (trim) je Bereich
TINT = {
    "fairground": (RED, GOLD), "workshop": (WC.METAL, WC.WARN), "carousel": (PLUM, GOLD),
    "bumpercars": (lift("#3c4a66", 1.5), hexc("#5fe8ff")), "security": (lift("#2e3850", 1.5), WC.BLUE),
    "substation": (WC.METAL, WC.WARN), "firstaid": (hexc("#e4e8e6"), hexc("#c84040")),
    "office": (WC.WOOD, GOLD), "coldstore": (hexc("#d8e6ee"), WC.BLUE), "musicbooth": (PLUM, PINK),
    "shooting": (WC.WOOD, RED), "mirrors": (hexc("#b8c4d0"), GOLD), "ghosttrain": (lift("#2e2238", 1.6), hexc("#7dff8a")),
    "ferriswheel": (RED, CREAM), "lighttower": (RED, GOLD), "coaster": (WC.WOOD, RED),
    "maingate": (RED, GOLD), "logflume": (lift("#3c5a66", 1.5), CREAM), "-": (RED, GOLD),
}
CLEARINGS = {"ferriswheel", "lighttower", "coaster", "maingate", "logflume", "-"}

INNER = {b[0]: b[3] for b in L.BUILDINGS}
INNER.update({c[0]: c[3] for c in L.CLEARINGS})


def room_of(p):
    for key, (x0, y0, x1, y1) in INNER.items():
        if x0 - 0.3 <= p[0] <= x1 + 0.3 and y0 - 0.3 <= p[1] <= y1 + 0.3:
            return key
    return "-"


def wall_of(p, room):
    if room not in INNER:
        return "-"
    x0, y0, x1, y1 = INNER[room]
    d = {"N": y1 - p[1], "S": p[1] - y0, "E": x1 - p[0], "W": p[0] - x0}
    side = min(d, key=d.get)
    if room in CLEARINGS:
        return "N" if d["N"] < 1.4 else "-"
    return side if d[side] < 1.0 else "-"


def popcorn(c, x, y, s, col=None):
    """Ersetzt das Blatt auf der Muellklappe: drei Popcornflocken."""
    for dx, dy in ((-0.5, -0.2), (0.4, -0.3), (0.0, 0.4)):
        c.ellipse(x + dx * s, y + dy * s, s * 0.55, s * 0.45, fill=hexc("#fff4d6"), outline=OUTLINE, width=0.01)


def candy_cart(ppm):
    """Zuckerwattewagen (Clean Filter): gestreifter Wagen, Edelstahlschuessel, rosa Watte am Stab."""
    b = WC.Block(-0.5, -0.3, 0.5, 0.3, 1.5 * K, ppm)
    c = b.c
    b.shadow(-0.42, -0.22, 0.42, 0.2)
    b.box(-0.4, -0.2, 0.4, 0.2, 0, 0.7, shade(RED, 1.1), RED)
    for i in range(5):
        if i % 2:
            xa = -0.4 + i * 0.16
            c.rect(xa, -0.18, xa + 0.16, -0.2 + 0.7 * K - 0.02, fill=CREAM)
    c.rect(-0.4, -0.2, 0.4, -0.2 + 0.7 * K, outline=OUTLINE, width=0.025)
    for wx in (-0.3, 0.3):
        c.ellipse(wx, -0.2, 0.07, 0.07, fill=WC.DARK, outline=OUTLINE, width=0.015)
    top = 0.2 + 0.7 * K
    c.ellipse(0.0, top - 0.02, 0.3, 0.1, fill=hexc("#c8ced8"), outline=OUTLINE, width=0.025)
    c.ellipse(0.0, top - 0.0, 0.22, 0.06, fill=hexc("#8a929e"))
    for dx, dy, r in ((-0.05, 0.25, 0.12), (0.08, 0.3, 0.1), (0.0, 0.38, 0.1)):
        c.ellipse(dx, top + dy, r, r * 0.9, fill=PINK, outline=OUTLINE, width=0.015)
    c.line([(0.0, top + 0.05), (0.0, top + 0.2)], fill=CREAM, width=0.02)
    return b.result()


def brief(consoles):
    pts = dict(consoles)
    pts["EmergencyButton"] = L.EMERGENCY
    pts["SurveillanceConsole"] = L.SURVEILLANCE
    pts["AdminTable"] = L.ADMIN_TABLE
    pts["FreeplayLaptop"] = L.FREEPLAY
    out = []
    for key, p in sorted(pts.items()):
        room = room_of(p)
        out.append((key, p[0], p[1], room, wall_of(p, room)))
    return out


def render_all(ppm, consoles):
    WC.TINT.update(TINT)
    WC.CLEARINGS = CLEARINGS
    WC.leaf = popcorn
    out = {}
    for key, _x, _y, room, wall in brief(consoles):
        parts = key.split("/")
        name = parts[1] if len(parts) == 3 else key
        if key == "EmergencyButton":
            out[key] = WC.camp_bell(ppm)
        elif key == "SurveillanceConsole":
            out[key] = WC.ranger_desk(ppm)
        elif key == "AdminTable":
            out[key] = WC.map_board(ppm)
        elif key == "FreeplayLaptop":
            out[key] = WC.crate_laptop(ppm)
        elif name == "SwipeCardConsole":
            out[key] = WC.id_reader(ppm, room)
        elif name == "MedScanner":
            out[key] = WC.floor_scanner(ppm)
        elif name == "MedBayConsole":
            out[key] = WC.microscope_bench(ppm)
        elif name == "CleanFilterConsole":
            out[key] = candy_cart(ppm)
        elif name == "FuelEngineConsole":
            out[key] = WC.fuel_station(ppm, room)
        elif name == "AlignEngineConsole":
            out[key] = WC.gauge_post(ppm, room)
        elif name == "gasCanConsole":
            out[key] = WC.jerrycan_rack(ppm)
        elif name == "StartReactorConsole":
            out[key] = WC.pump_terminal(ppm, room)
        elif name == "StabilizeSteeringConsole":
            out[key] = WC.theodolite(ppm)
        elif name == "FixCommsConsole":
            out[key] = WC.radio_set(ppm)
        else:
            kind = WC._kind_of(name)
            if kind is None:
                continue
            kw = {}
            if kind == "keypad":
                kw = dict(red=(name == "NoOxyConsole"))
            if kind == "data":
                kw = dict(upload=(name != "DataConsole"))
            out[key] = WC.generic(kind, wall, room, ppm, **kw)
    return out
