# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# Geometrie des Vesper-Museums in AU-Metern (Norden = +y, Kartenzentrum (0,0)).
# Quelle: docs/museum_map/museum_bauplan.md Abschnitt 3 und 6. Einzige Wahrheit fuer
# gen_museum.py (Boden, Kollider, Minimap). Die Objekt-Umsetzung der Skeld-Konsolen steht
# NICHT hier, sondern in src/AtlasMuseumLayout.cs, weil sie Laufzeit-Namen braucht.
#
# Abweichungen vom Bauplan (Moebel, die auf Vents/Tueren standen):
# - Sicherheit: Spind [-23.2,-20.4,-22.5,-17.4] lag auf Vent W3 -> an die Ostwand, y -16.6..-14.
# - Aegypten: Sphinx [-29.2,8.6,-27.6,9.3] lag auf Vent W1 -> nach Osten, x -26.5..-24.9.
# - Werkstatt: Regal [8.5,-9,9.1,-6] stand vor der Foyer-Tuer (y -10..-7.5) -> y -6.6..-4.8.
# - Haustechnik: Klimageraet stand vor der Sicherheits-Tuer -> Raummitte [-26,-7.4,-24.2,-6].
# - Foyer: Kassenhaeuschen endet bei y -10.9, Deko-Treppe bei x -2.6 (Tuer-/Oeffnungsabstand).
# - Shop: Wandregal stand vor der Westtuer -> [-9,-15.2,-8.3,-13.6]; Kassentresen ab x -7.4.
# - Shop: Pflanzentrog stand halb in der Foyer-Oeffnung -> x 2.8..5.3; Cafetische als Ellipsen
#   inkl. Stuehle, neu verteilt (Ostausgang frei).
# - Sicherheit: Gebaeudeplan-Tisch an die Suedwand [-27.8,-20.4,-25.2,-19.3], Spind in die SW-Ecke.
# - Rotunde: Vitrinen 0,3 m von den Diagonalwaenden abgerueckt.
# - Hof: Lieferwagen 0,6 m nach Sueden, der Treppenausgang (y 6..8) lief in das Fahrerhaus.

import math

# ------------------------------------------------------------------ Raeume
# (key, Anzeigename, SystemTypes-Traeger, Boden-Polygon oder Rechteck, Bodenfarbe)
# Der SystemTypes-Traeger ist die Skeld-Raum-ID, deren Konsolen im Raum stehen; die
# Anzeige ersetzt AtlasMuseum.RoomNames. Farben = Soll-Werte aus museum_stil.md (grob).

def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


ROTUNDE_POLY = [(2.69, -2.5), (6.5, 1.31), (6.5, 6.69), (2.69, 10.5),
                (-2.69, 10.5), (-6.5, 6.69), (-6.5, 1.31), (-2.69, -2.5)]

ROOMS = [
    ("rotunde", "Rotunda", "LifeSupp", ROTUNDE_POLY, "#b9b2a4"),
    ("foyer", "Foyer", "Cafeteria", rect(-8, -13, 8, -3), "#d8d2c4"),
    ("shop", "Museum Shop", "Admin", rect(-9, -20.4, 9, -13.5), "#8fc7b0"),
    ("sicherheit", "Security Office", "Security", rect(-29.4, -20.4, -22.5, -13), "#4f555e"),
    ("haustechnik", "Utilities", "Electrical", rect(-29.4, -12.5, -22, -4.5), "#8a8676"),
    ("aegypten", "Egyptian Hall", "Reactor", rect(-29.4, -4, -21, 9.5), "#c9a86a"),
    ("galerie", "Gallery", "Weapons", rect(-20.5, 0, -7, 8), "#9a6a45"),
    ("planetarium", "Planetarium", "Nav", rect(-20.4, 11, -8.5, 20.4), "#2c3a66"),
    ("mineralien", "Mineral Cabinet", "Shields", rect(-6, 11, 6, 20.4), "#3f6f73"),
    ("telefon", "Switchboard", "Comms", rect(9, 13, 18, 20.4), "#c98545"),
    ("technikhalle", "Machine Hall", "UpperEngine", rect(7, -3, 21, 9.5), "#7c8288"),
    ("werkstatt", "Restoration", "MedBay", rect(8.5, -13.5, 20.5, -3.5), "#e6ebee"),
    ("hof", "Loading Dock", "LowerEngine", rect(21.5, -6, 29.4, 12), "#55575b"),
    ("depot", "Depot", "Storage", rect(21.5, -20.4, 29.4, -6.5), "#8d8a84"),
]

# Laderampe: der Raum-Umriss oben ist die Admin-/Raumzaehlflaeche. Begehbar sind diese Teile:
HOF_FLOORS = [
    (rect(21.5, -2, 24.5, 8), "#8b877f"),     # Rampe (Deck 0)
    (rect(24.5, -6, 29.4, 12), "#55575b"),    # Hof (Deck -1)
    (rect(21.5, 8, 24.5, 12), "#55575b"),
    (rect(21.5, -6, 24.5, -2), "#7a766f"),    # Karrenschraege
]

CORRIDOR_COLOR = "#6d7480"
CORRIDORS = [
    ("gang_sw", rect(-22, -19.5, -9.5, -16.5)),
    ("gang_so", rect(9.5, -19.5, 21, -16.5)),
    ("gang_gp", rect(-15, 8.5, -12.5, 10.5)),
    ("gang_pm", rect(-8, 15, -6.5, 17.5)),
    ("gang_mt", rect(6.5, 15, 8.5, 17.5)),
    ("gang_tt", rect(12, 10, 14.5, 12.5)),
]

# Oeffnungen: Rechtecke durch die Wandstaerke. "door" bekommt ein Skeld-Tor (Layout.cs),
# "gap" bleibt offen. Farbe der Schwelle = hellerer Gangboden.
OPENINGS = [
    # Rotunde (Hauptachse ohne Gitter)
    ("gap", rect(-2, -3, 2, -2.5)),          # S -> Foyer
    ("gap", rect(-1.5, 10.5, 1.5, 11)),      # N -> Mineralien
    ("gap", rect(-7, 2, -6.5, 6)),           # W -> Galerie
    ("gap", rect(6.5, 2, 7, 6)),             # E -> Technikhalle
    # Foyer
    ("door", rect(8, -10, 8.5, -7.5)),       # E -> Werkstatt (Werkstatt-Gruppe)
    ("gap", rect(-2, -13.5, 2, -13)),        # S -> Shop
    # Shop
    ("gap", rect(-9.5, -19, -9, -17)),       # W -> Suedgang West
    ("gap", rect(9, -19, 9.5, -17)),         # E -> Suedgang Ost
    # Sicherheit
    ("door", rect(-22.5, -19, -22, -17)),    # E -> Suedgang West
    ("door", rect(-27, -13, -24.5, -12.5)),  # N -> Haustechnik
    # Haustechnik
    ("door", rect(-27, -4.5, -24.5, -4)),    # N -> Aegypten
    # Aegypten
    ("door", rect(-21, 3, -20.5, 5.5)),      # E -> Galerie
    # Galerie
    ("gap", rect(-15, 8, -12.5, 8.5)),       # N -> Gang G-P
    # Planetarium
    ("door", rect(-15, 10.5, -12.5, 11)),    # S -> Gang G-P
    ("door", rect(-8.5, 15, -8, 17.5)),      # E -> Gang P-M
    # Mineralien
    ("gap", rect(-6.5, 15, -6, 17.5)),       # W -> Gang P-M
    ("gap", rect(6, 15, 6.5, 17.5)),         # E -> Gang M-T
    # Telefonzentrale
    ("door", rect(8.5, 15, 9, 17.5)),        # W -> Gang M-T
    ("door", rect(12, 12.5, 14.5, 13)),      # S -> Gang T-Tech
    # Technikhalle
    ("gap", rect(12, 9.5, 14.5, 10)),        # N -> Gang T-Tech
    ("door", rect(14, -3.5, 16.5, -3)),      # S -> Werkstatt
    ("door", rect(21, 1, 21.5, 5)),          # E Rolltor -> Rampe
    # Depot
    ("door", rect(24, -6.5, 26.5, -6)),      # N -> Hof
    ("door", rect(21, -19, 21.5, -17)),      # W -> Suedgang Ost
]

# ------------------------------------------------------------------ Hindernisse
# OPAQUE sperrt Weg UND Sicht (Kollider auf Ship + Shadow).
# GLASS sperrt nur den Weg (Kollider auf ShortObjects, kein Schatten).
# Form: ("rect", x0, y0, x1, y1) | ("ellipse", cx, cy, rx, ry) | ("circle", cx, cy, r)
# Drittes Feld = Zeichenfarbe.

OPAQUE = [
    # Foyer
    (("ellipse", 0, -8, 2.2, 1.6), "#6b4a33"),          # Infotheke
    (("rect", 6.6, -12.6, 8, -10.9), "#6b4a33"),        # Kassenhaeuschen
    (("rect", -6, -13, -2.6, -10.5), "#8e2f2f"),        # Deko-Treppe
    (("rect", -8, -9.5, -7.4, -5), "#5d4636"),          # Garderobe
    # Shop
    (("rect", -7.4, -16.2, -4, -15.2), "#7a5436"),      # Kassentresen
    (("rect", -9, -15.2, -8.3, -13.6), "#7a5436"),      # Wandregal (verschoben)
    (("rect", -6, -19.5, -3, -18.7), "#7a5436"),        # Regal-Insel
    (("rect", 4, -16.2, 8.5, -15.2), "#7a5436"),        # Cafetresen
    # Sicherheit
    (("rect", -29.4, -19, -29, -14.5), "#2a2f35"),      # Monitorwand
    (("rect", -29.0, -20.4, -28.1, -19.8), "#3a3f46"),  # Spind (SW-Ecke; Suedwand gehoert dem Gebaeudeplan)
    # Haustechnik
    (("rect", -29.4, -11.6, -28.6, -8.6), "#5a5f55"),   # Schaltschraenke (verdeckten sonst den Sicherungskasten)
    (("rect", -26.0, -7.4, -24.2, -6.0), "#80868b"),    # Klimageraet (verschoben)
    (("circle", -27.5, -8.5, 0.45), "#80868b"),         # Kessel
    # Aegypten
    (("rect", -28.6, 3.4, -27.7, 5.6), "#b48a3c"),      # Sarkophag N
    (("rect", -28.6, -2.6, -27.7, -0.4), "#b48a3c"),    # Sarkophag S
    (("rect", -23.2, 0.4, -22.2, 1.4), "#a88c5c"),      # Stele
    (("rect", -26.5, 8.7, -24.9, 9.4), "#a88c5c"),      # Sphinx-Fragment (verschoben)
    # Galerie: Stellwaende
    (("rect", -17.4, 5.3, -17.2, 7.5), "#e8e0d0"),
    (("rect", -17.4, 0.5, -17.2, 2.7), "#e8e0d0"),
    (("rect", -12.9, 5.3, -12.7, 7.5), "#e8e0d0"),
    (("rect", -12.9, 0.5, -12.7, 2.7), "#e8e0d0"),
    # Planetarium
    (("circle", -14.45, 15.7, 0.45), "#5a6690"),        # Projektor
    # Telefonzentrale
    (("rect", 9.5, 19.4, 15.5, 20.4), "#4a3a2c"),       # Vermittlungsschrank
    (("rect", 17.4, 14, 18, 19), "#4a3a2c"),            # Funkgeraete-Regal
    # Technikhalle
    (("rect", 10.8, 2.3, 11.2, 2.7), "#4d5358"),        # Stuetzen
    (("rect", 16.8, 2.3, 17.2, 2.7), "#4d5358"),
    (("rect", 9, 5, 13, 7), "#3f6b4f"),                 # Dampfmaschine
    (("circle", 13.6, 6, 1.0), "#3f6b4f"),              # Schwungrad
    (("rect", 14, -1.5, 18.5, 0.5), "#a23a32"),         # Oldtimer
    (("rect", 15, 5.5, 19, 8.5), "#5e656b"),            # Turbine
    # Werkstatt
    (("rect", 9, -4.4, 13.5, -3.6), "#b9c0c4"),         # Arbeitstisch W
    (("rect", 17, -4.4, 20, -3.6), "#b9c0c4"),          # Arbeitstisch E
    (("rect", 8.5, -6.6, 9.1, -4.8), "#8a8f93"),        # Regal (verschoben)
    # Depot
    (("rect", 23, -10, 28.2, -8.8), "#6b5a45"),         # Hochregale
    (("rect", 23, -14, 28.2, -12.8), "#6b5a45"),
    (("rect", 23, -18, 28.2, -16.8), "#6b5a45"),
    (("rect", 21.7, -8.6, 23.1, -7.4), "#9a7a52"),      # Kisten
    (("rect", 21.7, -16, 22.9, -15), "#9a7a52"),
    (("rect", 27, -11.6, 28.2, -10.6), "#9a7a52"),
    (("rect", 26, -20.4, 29, -19.5), "#b53a32"),        # CO2-Flaschen
    # Hof
    (("rect", 26, 0.4, 28.6, 5.9), "#e4e4e0"),          # Lieferwagen (suedlich der Treppe, y 6..8 frei)
    (("circle", 27.6, -4.5, 0.4), "#3f6fb0"),           # Faesser
    (("circle", 28.5, -4.5, 0.4), "#3f6fb0"),
    (("circle", 28.05, -5.3, 0.4), "#3f6fb0"),
]

GLASS_COLOR = "#9fbfd4"
GLASS = [
    # Rotunde: Skelett-Sockel (User 22.09.: sperrt nur den Weg, nicht die Sicht)
    ("ellipse", 0, 4, 4.2, 1.6),
    # Rotunde: vier Vitrinen (von den Diagonalwaenden abgerueckt, sonst Taschen hinter dem Glas)
    ("rect", -4.8, 7.0, -3.6, 7.8), ("rect", 3.6, 7.0, 4.8, 7.8),
    ("rect", -4.8, 0.1, -3.6, 0.9), ("rect", 3.6, 0.1, 4.8, 0.9),
    # Foyer
    ("rect", -4.6, -4.2, -3.4, -3.4), ("rect", 3.4, -4.2, 4.6, -3.4),
    ("rect", -7, -5.2, -5.2, -4.7), ("rect", 5.2, -5.2, 7, -4.7),   # Baenke
    # Shop
    # Cafetische: Ellipse = Tisch (r 0,55) + Stuehle links/rechts; Ostausgang (y -19..-17) bleibt frei
    ("ellipse", 2.6, -18.0, 1.0, 0.55), ("ellipse", 5.2, -19.3, 1.0, 0.55), ("ellipse", 6.6, -17.5, 1.0, 0.55),
    ("rect", 2.8, -14.3, 5.3, -13.7),                                # Pflanzentrog (neben, nicht in der Foyer-Oeffnung)
    # Sicherheit: Gebaeudeplan-Tisch an der Suedwand (User 22.09.: "mitten im Raum" war falsch)
    ("rect", -27.8, -20.4, -25.2, -19.3),
    # Aegypten
    ("rect", -25.5, 6.5, -23.9, 7.3), ("rect", -25.5, 2.5, -23.9, 3.3), ("rect", -25.5, -1.5, -23.9, -0.7),
    ("rect", -22.4, -3.6, -21.2, -2.8), ("rect", -22.4, 7.2, -21.2, 8.0),
    # Galerie: Bank
    ("rect", -11.8, 3.75, -10, 4.25),
    # Mineralien
    ("rect", -1, 14.5, 1, 16.5),                                     # Tresorvitrine
    ("rect", -4.6, 19.2, -3.4, 20.0), ("rect", -0.6, 19.2, 0.6, 20.0), ("rect", 3.4, 19.2, 4.6, 20.0),
    ("rect", -5.8, 12.5, -5.0, 13.7), ("rect", -5.8, 18.3, -5.0, 19.5),
    ("rect", 5.0, 12.5, 5.8, 13.7), ("rect", 5.0, 18.3, 5.8, 19.5),
    ("rect", -3.8, 12.4, -2.2, 13.2), ("rect", 2.2, 12.4, 3.8, 13.2),
    # Telefonzentrale: Vermittlungstisch
    ("rect", 10, 15.5, 14, 16.5),
    # Werkstatt
    ("rect", 12.5, -11, 12.7, -7),                                   # Glastrennwand
    ("rect", 9.5, -12.8, 12, -11.6),                                 # Restaurierungstisch
    # Hof: Rampenkante (Deck 0 -> -1), offen an Schraege (Sued) und Treppe (Ost, y 6..8)
    ("rect", 24.45, -2, 24.55, 6),
    ("rect", 21.5, 7.95, 24.5, 8.05),
]

# Objektart je Eintrag (gleiche Reihenfolge wie OPAQUE / GLASS). museum_art.py zeichnet
# daraus die Sprites; None = kein Sprite (reine Kollision, z.B. die Rampenkante).
OPAQUE_KINDS = [
    "infotheke", "kasse", "treppe", "garderobe",
    "tresen_kasse", "regal_shop", "regal_insel", "tresen_cafe",
    "monitorwand", "spind",
    "schaltschrank", "klima", "kessel",
    "sarkophag", "sarkophag", "stele", "sphinx",
    "stellwand", "stellwand", "stellwand", "stellwand",
    "projektor",
    "vermittlung", "funkregal",
    "stuetze", "stuetze", "dampfmaschine", "schwungrad", "oldtimer", "turbine",
    "werktisch", "werktisch", "regal_werk",
    "hochregal", "hochregal", "hochregal", "kiste", "kiste", "kiste", "co2",
    "lieferwagen", "fass", "fass", "fass",
]

GLASS_KINDS = [
    "dino",
    "vitrine", "vitrine", "vitrine", "vitrine",
    "vitrine", "vitrine", "bank", "bank",
    "cafetisch", "cafetisch", "cafetisch", "trog",
    "admintisch",
    "tischvitrine", "tischvitrine", "tischvitrine", "vitrine", "vitrine",
    "bank",
    "tresorvitrine",
    "vitrine", "vitrine", "vitrine",
    "vitrine", "vitrine", "vitrine", "vitrine",
    "tischvitrine", "tischvitrine",
    "vermittlungstisch",
    "glaswand", "resttisch",
    None, None,
]

# Nicht begehbare Deko-Flaechen, die nur gezeichnet werden (Lichthof, Nordhof, Verwaltung).
DECOR = [
    (rect(-21.5, -16, -8.5, -5), "#1f3a2c"),   # Lichthof
    (rect(21.5, 12.5, 29.4, 20.4), "#33353a"), # Nordhof
]

# Kartengrenzen fuer Bild und Minimap (Meter).
BOUNDS = (-30.5, -21.5, 30.5, 21.5)


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
