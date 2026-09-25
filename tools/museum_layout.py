# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# Geometrie des Vesper-Museums in AU-Metern (Norden = +y, Kartenzentrum (0,0)).
# Einzige Wahrheit fuer gen_museum.py (Boden, Kollider, Minimap). Die Umsetzung der Skeld-Konsolen
# steht NICHT hier, sondern in src/AtlasMuseumLayout.cs, weil sie Laufzeit-Namen braucht.
#
# KARTENVERKLEINERUNG (24.09., docs/KARTEN_VERKLEINERUNG.md Abschnitt 3): 61 x 43 m -> ca. 51 x 30 m.
# Jeder Raum wird in seinen ALTEN Entwurfskoordinaten beschrieben (so bleibt die ganze Gestaltung in
# museum_art.floor_room gueltig), auf einen Ausschnitt ZUGESCHNITTEN und um SHIFT an seinen neuen
# Platz verschoben. Objekte stehen je Raum in Entwurfskoordinaten und wandern mit.
#   - Shop -> Suedwestecke des Foyers (Teilflaeche Admin, Name "Foyer")
#   - Mineralienkabinett -> Nordnische der Rotunde (Teilflaeche Shields, Name "Rotunda")
#   - Laderampe + Depot -> "Depot & Loading Dock" (Teilflaechen LowerEngine + Storage)
#   - Sicherheit und Haustechnik direkt westlich ans Foyer, Lichthof/Nordhof/Suedgaenge entfallen
#   - Galerie, Aegypten, Planetarium, Telefon, Technikhalle (ohne Oldtimer), Werkstatt beschnitten
# Durchsicht (Abschnitt 3, Tabelle): Infotheke, Kassentresen, Klimageraet, Stele, Schwungrad,
# Werktische und die Depotkiste sind jetzt GLASS (sperren nur den Weg).

import math

from shapely.geometry import Polygon, box as sbox


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


ROTUNDE_POLY = [(2.69, -2.5), (6.5, 1.31), (6.5, 6.69), (2.69, 10.5),
                (-2.69, 10.5), (-6.5, 6.69), (-6.5, 1.31), (-2.69, -2.5)]

# ------------------------------------------------------------------ Raeume
# key: (Anzeigename, SystemTypes-Traeger, Grafikstil (museum_art.ROOM_ROLE), Zuschnitt in
#       ENTWURFSkoordinaten (Punktliste), Verschiebung (dx, dy))
# Raeume mit gleichem Namen sind Teilflaechen EINES Raums (je Skeld-System eine, ohne Wand dazwischen).
ROOM_DEFS = {
    "rotunde":      ("Rotunda", "LifeSupp", "rotunde", ROTUNDE_POLY, (0.0, 0.0)),
    "nische":       ("Rotunda", "Shields", "mineralien", rect(-4.5, 11, 4.5, 16.5), (0.0, 0.0)),
    "foyer":        ("Foyer", "Cafeteria", "foyer",
                     [(-8, -9.5), (-2.5, -9.5), (-2.5, -13), (8, -13), (8, -3), (-8, -3)], (0.0, 0.0)),
    "shop":         ("Foyer", "Admin", "shop", rect(-9, -16.5, -3.5, -13), (1.0, 3.5)),
    "sicherheit":   ("Security Office", "Security", "sicherheit", rect(-29.4, -20.4, -22.5, -13), (14.0, 12.5)),
    "haustechnik":  ("Utilities", "Electrical", "haustechnik", rect(-29.4, -12.5, -22, -4.5), (6.1, 1.0)),
    "aegypten":     ("Egyptian Hall", "Reactor", "aegypten", rect(-29.4, -3, -22, 8), (6.1, 0.0)),
    "galerie":      ("Gallery", "Weapons", "galerie", rect(-15.4, 0, -7, 8), (0.0, 0.0)),
    "planetarium":  ("Planetarium", "Nav", "planetarium", rect(-17.4, 11, -8.5, 19), (0.0, -2.5)),
    "telefon":      ("Switchboard", "Comms", "telefon", rect(9, 14, 18, 20.4), (0.0, -4.0)),
    "technikhalle": ("Machine Hall", "UpperEngine", "technikhalle", rect(7, 1, 19.5, 9.5), (0.0, 0.0)),
    "werkstatt":    ("Restoration", "MedBay", "werkstatt", rect(8.5, -10, 19.5, -3.5), (0.0, 4.0)),
    "hof":          ("Depot & Loading Dock", "LowerEngine", "hof", rect(21.5, 0.2, 29.4, 9.5), (-1.5, 0.0)),
    "depot":        ("Depot & Loading Dock", "Storage", "depot", rect(21.5, -13.6, 29.4, -6.5), (-1.5, 6.2)),
}


def mv(key, pts):
    dx, dy = ROOM_DEFS[key][4]
    return [(x + dx, y + dy) for x, y in pts]


def mv_shape(key, shape):
    dx, dy = ROOM_DEFS[key][4] if key else (0.0, 0.0)
    kind = shape[0]
    if kind == "rect":
        _, x0, y0, x1, y1 = shape
        return ("rect", x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    if kind == "ellipse":
        _, cx, cy, rx, ry = shape
        return ("ellipse", cx + dx, cy + dy, rx, ry)
    if kind == "circle":
        _, cx, cy, r = shape
        return ("circle", cx + dx, cy + dy, r)
    raise ValueError(kind)


# (key, Anzeigename, SystemTypes-Traeger, WELT-Flaeche, Bodenfarbe) - Format wie vor dem Umbau
ROOM_COLORS = {
    "rotunde": "#b9b2a4", "nische": "#3f6f73", "foyer": "#d8d2c4", "shop": "#8fc7b0",
    "sicherheit": "#4f555e", "haustechnik": "#8a8676", "aegypten": "#c9a86a", "galerie": "#9a6a45",
    "planetarium": "#2c3a66", "telefon": "#c98545", "technikhalle": "#7c8288", "werkstatt": "#e6ebee",
    "hof": "#55575b", "depot": "#8d8a84",
}
ROOMS = [(k, d[0], d[1], mv(k, d[3]), ROOM_COLORS[k]) for k, d in ROOM_DEFS.items()]

# Grafik je Teilflaeche: (Stil, Weltflaeche, Verschiebung). museum_art zeichnet den Stil in
# Entwurfskoordinaten (Weltflaeche minus Verschiebung) und beschneidet auf die Weltflaeche.
ROOM_ART = [(d[2], mv(k, d[3]), d[4]) for k, d in ROOM_DEFS.items()]

# Minimap-Beschriftung: ein Name je Raum; Ausnahmen, wo die Flaechenmitte auf einem Objekt laege.
LABEL_AT = {"Rotunda": (0.0, 8.6), "Foyer": (2.4, -11.2), "Depot & Loading Dock": (23.9, -4.4)}
# Minimap-Text, wo der Name breiter als der Raum waere
LABEL_TEXT = {"Depot & Loading Dock": "Depot &\nLoading Dock"}

# Laderampe (Entwurf -> zugeschnitten auf den Dock-Ausschnitt, dann verschoben). Der Raum-Umriss
# oben ist die Admin-/Raumzaehlflaeche; begehbar sind diese Teile:
_HOF_CUT = sbox(21.5, 0.2, 29.4, 9.5)
_HOF_DESIGN = [
    (rect(21.5, -2, 24.5, 8), "#8b877f"),     # Rampe (Deck 0)
    (rect(24.5, -6, 29.4, 12), "#55575b"),    # Hof (Deck -1)
    (rect(21.5, 8, 24.5, 12), "#55575b"),
]
HOF_FLOORS = []
for _poly, _col in _HOF_DESIGN:
    _g = Polygon(_poly).intersection(_HOF_CUT)
    if not _g.is_empty:
        HOF_FLOORS.append((mv("hof", list(_g.exterior.coords)[:-1]), _col))

CORRIDOR_COLOR = "#6d7480"
CORRIDORS = [
    ("gang_pn", rect(-8, 12.5, -5, 15)),     # Planetarium -> Rotunden-Nische
    ("gang_nt", rect(5, 12.5, 8.5, 15)),     # Rotunden-Nische -> Telefonzentrale
]

# Oeffnungen (WELT): Rechtecke durch die Wandstaerke. "door" bekommt ein Skeld-Tor (Layout.cs),
# "gap" bleibt offen. 7 senkrechte + 6 waagerechte Tore = genau die 13 Skeld-Tueren.
OPENINGS = [
    # Rotunde (Hauptachsen ohne Gitter)
    ("gap", rect(-2, -3, 2, -2.5)),          # S -> Foyer
    ("gap", rect(-1.5, 10.5, 1.5, 11)),      # N -> Nische
    ("gap", rect(-7, 2, -6.5, 6)),           # W -> Galerie
    ("gap", rect(6.5, 2, 7, 6)),             # E -> Technikhalle
    ("gap", rect(-8.5, 12.5, -8, 15)),       # Planetarium O -> Gang
    ("gap", rect(-5, 12.5, -4.5, 15)),       # Gang -> Nische W
    ("gap", rect(4.5, 12.5, 5, 15)),         # Nische O -> Gang
    # senkrechte Tore
    ("door", rect(-8.5, -6.25, -8, -3.75)),  # Foyer-West (Sicherheit)
    ("door", rect(8, -5.75, 8.5, -3.25)),    # Foyer-Ost (Werkstatt)
    ("door", rect(-15.9, -7.5, -15.4, -5)),  # Sicherheit-West (Haustechnik)
    ("door", rect(-15.9, 3, -15.4, 5.5)),    # Aegypten-Ost (Galerie)
    ("door", rect(8.5, 12.5, 9, 15)),        # Telefon-West (Gang)
    ("door", rect(19.5, 1, 20, 5)),          # Rolltor Technikhalle -> Rampe
    ("door", rect(19.5, -4.5, 20, -2)),      # Werkstatt-Ost (Depot)
    # waagerechte Tore
    ("door", rect(-11.5, -0.5, -9, 0)),      # Sicherheit-Nord (Galerie)
    ("door", rect(-20.9, -3.5, -18.4, -3)),  # Haustechnik-Nord (Aegypten)
    ("door", rect(-15, 8, -12.5, 8.5)),      # Planetarium-Sued (Galerie)
    ("door", rect(12, 9.5, 14.5, 10)),       # Telefon-Sued (Technikhalle)
    ("door", rect(14, 0.5, 16.5, 1)),        # Technikhalle-Sued (Werkstatt)
    ("door", rect(20.3, -0.3, 22.8, 0.2)),   # Depot-Nord (Rampe)
]

# ------------------------------------------------------------------ Hindernisse
# OPAQUE sperrt Weg UND Sicht (Kollider auf Ship + Shadow).
# GLASS sperrt nur den Weg (Kollider auf ShortObjects, kein Schatten).
# Form: ("rect", x0, y0, x1, y1) | ("ellipse", cx, cy, rx, ry) | ("circle", cx, cy, r)
# Je Eintrag: (Raum oder None = schon Welt, Form in Entwurfskoordinaten des Raums, [Farbe], Art)

_OPAQUE = [
    # Foyer
    ("foyer", ("rect", 6.6, -12.6, 8, -10.9), "#6b4a33", "kasse"),
    ("foyer", ("rect", -8, -9.4, -7.4, -6.7), "#5d4636", "garderobe"),     # gekuerzt: Foyer-West-Tor
    # Shop-Ecke
    ("shop", ("rect", -9, -15.2, -8.3, -13.6), "#7a5436", "regal_shop"),
    # Sicherheit (Monitorwand an der Westwand oberhalb des West-Tors)
    (None, ("rect", -15.4, -4.2, -15.0, -1.2), "#2a2f35", "monitorwand"),
    # Haustechnik
    ("haustechnik", ("rect", -29.4, -11.6, -28.6, -8.6), "#5a5f55", "schaltschrank"),
    ("haustechnik", ("circle", -27.5, -8.5, 0.45), "#80868b", "kessel"),
    # Aegypten
    ("aegypten", ("rect", -28.6, 3.4, -27.7, 5.6), "#b48a3c", "sarkophag"),
    ("aegypten", ("rect", -28.6, -2.6, -27.7, -0.4), "#b48a3c", "sarkophag"),
    # Galerie: die zwei oestlichen Stellwaende
    ("galerie", ("rect", -12.9, 5.3, -12.7, 7.5), "#e8e0d0", "stellwand"),
    ("galerie", ("rect", -12.9, 0.5, -12.7, 2.7), "#e8e0d0", "stellwand"),
    # Planetarium
    ("planetarium", ("circle", -14.45, 15.7, 0.45), "#5a6690", "projektor"),
    # Telefonzentrale
    ("telefon", ("rect", 9.5, 19.4, 15.5, 20.4), "#4a3a2c", "vermittlung"),
    ("telefon", ("rect", 17.4, 14, 18, 19), "#4a3a2c", "funkregal"),
    # Technikhalle
    ("technikhalle", ("rect", 10.8, 2.3, 11.2, 2.7), "#4d5358", "stuetze"),
    ("technikhalle", ("rect", 16.8, 2.3, 17.2, 2.7), "#4d5358", "stuetze"),
    ("technikhalle", ("rect", 9, 5, 13, 7), "#3f6b4f", "dampfmaschine"),
    ("technikhalle", ("rect", 15, 5.5, 19, 8.5), "#5e656b", "turbine"),
    # Werkstatt
    ("werkstatt", ("rect", 8.5, -6.6, 9.1, -4.8), "#8a8f93", "regal_werk"),
    # Depot
    ("depot", ("rect", 23, -10, 28.2, -8.8), "#6b5a45", "hochregal"),
    # Hof
    ("hof", ("rect", 26, 0.4, 28.6, 5.9), "#e4e4e0", "lieferwagen"),
]

GLASS_COLOR = "#9fbfd4"
_GLASS = [
    # Rotunde: Skelett-Sockel (User 22.09.: sperrt nur den Weg, nicht die Sicht) + vier Vitrinen
    # Podest 5,4 x 1,8 m unter Beinen und Rumpf (User 25.09.: "Fuesse auf dem Podium, Kopf deutlich
    # ausserhalb, wie in einem echten Museum"); das Skelett ist ein eigenes Objekt (EXTRA_PROPS dino_rex)
    ("rotunde", ("ellipse", 0.5, 4, 2.7, 0.9), "dino"),
    # Sabotage "Rex erwacht" (25.09.): Spieluhr vor dem Podest, Sternenprojektor im Security Office
    # (Entwurfskoordinaten; Sicherheit wird um (14, 12.5) verschoben -> Welt (-10.4, -3.6))
    ("rotunde", ("circle", 1.6, 2.2, 0.28), "spieluhr"),
    ("sicherheit", ("circle", -24.4, -16.1, 0.28), "nachtlicht"),
    # (Vitrine NW entfaellt: dort schwebt jetzt der Schaedel des T. rex)
    ("rotunde", ("rect", 3.6, 7.0, 4.8, 7.8), "vitrine"),
    ("rotunde", ("rect", -4.8, 0.1, -3.6, 0.9), "vitrine"), ("rotunde", ("rect", 3.6, 0.1, 4.8, 0.9), "vitrine"),
    # Nische (ehemals Mineralienkabinett)
    ("nische", ("rect", -1, 14.5, 1, 16.5), "tresorvitrine"),
    ("nische", ("rect", -3.8, 12.4, -2.2, 13.2), "tischvitrine"), ("nische", ("rect", 2.2, 12.4, 3.8, 13.2), "tischvitrine"),
    # Foyer
    ("foyer", ("ellipse", 0, -8, 2.2, 1.6), "infotheke"),
    ("foyer", ("rect", -4.6, -4.2, -3.4, -3.4), "vitrine"), ("foyer", ("rect", 3.4, -4.2, 4.6, -3.4), "vitrine"),
    ("foyer", ("rect", -7, -5.2, -5.2, -4.7), "bank"), ("foyer", ("rect", 5.2, -5.2, 7, -4.7), "bank"),
    # Shop-Ecke
    ("shop", ("rect", -7.4, -16.2, -4, -15.2), "tresen_kasse"),
    # Sicherheit: Gebaeudeplan-Tisch an der Suedwand
    ("sicherheit", ("rect", -27.8, -20.4, -25.2, -19.3), "admintisch"),
    # Haustechnik
    ("haustechnik", ("rect", -26.0, -7.4, -24.2, -6.0), "klima"),
    # Aegypten
    ("aegypten", ("rect", -25.5, 6.5, -23.9, 7.3), "tischvitrine"), ("aegypten", ("rect", -25.5, 2.5, -23.9, 3.3), "tischvitrine"),
    ("aegypten", ("rect", -25.5, -1.5, -23.9, -0.7), "tischvitrine"),
    ("aegypten", ("rect", -23.2, 0.4, -22.2, 1.4), "stele"),
    # Galerie: Bank
    ("galerie", ("rect", -11.8, 3.75, -10, 4.25), "bank"),
    # Telefonzentrale: Vermittlungstisch
    ("telefon", ("rect", 10, 15.5, 14, 16.5), "vermittlungstisch"),
    # Technikhalle
    ("technikhalle", ("circle", 13.6, 6, 1.0), "schwungrad"),
    # Werkstatt
    ("werkstatt", ("rect", 9, -4.4, 13.5, -3.6), "werktisch"),
    ("werkstatt", ("rect", 17, -4.4, 19.3, -3.6), "werktisch"),
    ("werkstatt", ("rect", 12.5, -10, 12.7, -7), "glaswand"),
    # Depot
    ("depot", ("rect", 27, -11.6, 28.2, -10.6), "kiste"),
    # Hof: Rampenkante (Deck 0 -> -1), offen an der Treppe (Ost, y 6..8)
    ("hof", ("rect", 24.45, 0.2, 24.55, 6), None),
    ("hof", ("rect", 21.5, 7.95, 24.5, 8.05), None),
]

OPAQUE = [(mv_shape(k, s), c) for k, s, c, _kind in _OPAQUE]
OPAQUE_KINDS = [kind for _k, _s, _c, kind in _OPAQUE]
GLASS = [mv_shape(k, s) for k, s, _kind in _GLASS]
GLASS_KINDS = [kind for _k, _s, kind in _GLASS]

# Objekte ohne eigenen Kollider-Eintrag (Deko mit Hoehe), WELT.
EXTRA_PROPS = [
    ("lampe", ("circle", 27.5, 6.9, 0.12)),
    # T.-rex-Skelett ueber dem Podest: 11 m lang, Hals und Kopf ragen ~3,5 m ueber die Podestkante, der
    # Schwanz ~2 m. Standlinie 2 cm vor der des Podests, damit es sicher darueber sortiert.
    ("dino_rex", ("ellipse", 0.5, 4, 2.7, 0.92)),
    # Kopf und Unterkiefer als eigene Sprites (AtlasRex bewegt sie); Tiefe setzt AtlasRex knapp davor
    ("dino_rex_jaw", ("ellipse", 0.5, 4, 2.7, 0.92)),
    ("dino_rex_head", ("ellipse", 0.5, 4, 2.7, 0.92)),
]

# Nicht begehbare Deko-Flaechen: mit dem Umbau entfallen (Lichthof, Nordhof).
DECOR = []

# Kartengrenzen fuer Bild und Minimap (Meter).
BOUNDS = (-24.5, -14.0, 29.0, 17.5)


def shape_points(shape, steps=40):
    kind = shape[0]
    if kind == "rect":
        _, x0, y0, x1, y1 = shape
        return rect(x0, y0, x1, y1)
    if kind == "ellipse":
        _, cx, cy, rx, ry = shape
        return [(cx + rx * math.cos(2 * math.pi * i / steps),
                 cy + ry * math.sin(2 * math.pi * i / steps)) for i in range(steps)]
    if kind == "circle":
        _, cx, cy, r = shape
        n = 16
        return [(cx + r * math.cos(2 * math.pi * i / n),
                 cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    raise ValueError(kind)


assert len(OPAQUE_KINDS) == len(OPAQUE), (len(OPAQUE_KINDS), len(OPAQUE))
assert len(GLASS_KINDS) == len(GLASS), (len(GLASS_KINDS), len(GLASS))
