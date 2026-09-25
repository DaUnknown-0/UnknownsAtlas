# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_layout.py - Moonlight Carnival (docs/PARK_KONZEPT.md), Grundriss v2 (Kartenverkleinerung 24.09.).
#
# Gleiches Format wie wald_layout.py, dazu die Park-Eigenheiten:
#   - RAIL: die Achterbahnstrecke. Sperrt den Weg, nicht die Sicht; passierbar nur an den
#     Bahnuebergaengen (CROSSINGS). Sie umschliesst "Show Control" (Lichtturm-Hof + Musikzentrale).
#   - WATER + BRIDGES: der Kanal der Wildwasserbahn mit zwei Bruecken (Log-Flume-Durchgang).
#   - TURNSTILES: zwei Drehkreuz-Oeffnungen in der Suedwand des Festplatzes (Einbahn: West nur
#     hinein = nach Norden, Ost nur hinaus = nach Sueden; Welt-System AtlasParkWorld).
#
# v2 (docs/KARTEN_VERKLEINERUNG.md Abschnitt 5): 74 x 50 m, 18 Bereiche -> ca. 46 x 41 m, 12 Raeume
# (davon drei aus Teilflaechen) + 2 Durchgaenge. Leitsatz: Attraktionen ohne Tasks werden Durchgaenge.
#     [Shooting Gallery]-[Ferris Wheel]=X=[Show Control]        X = Bahnuebergang
#     [Carousel]------[FAIRGROUND]------[Coaster Station]
#     ~Ghost Train~     Drehkreuze         ~Log Flume~
#          |          [Park Office]             |
#     [Workshop]-[Bumper Cars]-[Substation]-[Cold Store]-[First Aid]
#   - Hall of Mirrors und Main Gate entfallen (Drehkreuze -> Suedausgang des Festplatzes)
#   - Light Tower + Music Booth = "Show Control" (Teilflaechen Shields + Comms)
#   - Security Booth = Nebenraum des Park Office (Teilflaechen Admin + Security, Name "Park Office")
#   - Durchsicht: Riesenrad-Nabe, Lichtturm, Kuehltruhe GLASS; Karussell: Weg ueber die ganze Scheibe
#     gesperrt (GLASS), Sicht nur am Mittelgehaeuse (OPAQUE-Kern ohne Sprite)
#
# Die 13 Skeld-Tueren: senkrecht (O/W-Waende) 7, waagerecht (N/S) 6. Eine Oeffnung darf mit einem
# fuenften Feld ihre Tuergruppe selbst angeben (Kuehlhaus-Westtor gehoert zur Storage-Gruppe).

BOUNDS = (-23.0, -23.0, 26.0, 20.5)
WALL = 0.5
PATH_W = 2.8
DOOR_W = 2.5

# ------------------------------------------------------------------ Gebaeude und Umzaeunungen
# key, Anzeigename, Raum-Typ, Innenraum [x0,y0,x1,y1], Oeffnungen [(Seite, von, bis, Art[, Tuergruppe])]
#   Art "door" = Skeld-Tuer (Barrier Gate), "gap" = offen
BUILDINGS = [
    # Tuergruppen (Skeld): Cafeteria 3, Storage 3, UpperEngine 2, LowerEngine 2, Security 1, MedBay 1, Electrical 1
    ("fairground", "Fairground", "Cafeteria", (-6, -3, 6, 6),
     [("W", 0.5, 3.0, "door"), ("E", 0.5, 3.0, "door"), ("N", -1.25, 1.25, "door"),
      ("S", -4.5, -2.0, "gap"), ("S", 2.0, 4.5, "gap")]),                          # Drehkreuze
    ("workshop", "Workshop", "Storage", (-21, -19, -12.5, -12),
     [("N", -16.25, -13.75, "door"), ("E", -17.5, -15.0, "door")]),
    ("carousel", "Carousel", "UpperEngine", (-19, -3, -9, 6),
     [("S", -16.25, -13.75, "door"), ("E", 0.5, 3.0, "door"), ("N", -16.5, -14.0, "gap")]),
    ("bumpercars", "Bumper Cars", "LowerEngine", (-10.5, -21, -1.5, -14.5),
     [("N", -4.25, -1.75, "door"), ("W", -17.5, -15.0, "door")]),
    ("security", "Park Office", "Security", (2.5, -11.5, 7.5, -6.5),
     [("N", 3.75, 6.25, "door")]),
    ("substation", "Substation", "Electrical", (0.5, -19.5, 6.5, -14.5),
     [("N", 2.0, 4.5, "door")]),
    ("firstaid", "First Aid Tent", "MedBay", (17.5, -21, 22.5, -14.5),
     [("W", -19.5, -17.0, "door")]),
    ("office", "Park Office", "Admin", (-6, -11.5, 2, -6.5),
     [("N", -3.5, -1.0, "gap"), ("S", -3.5, -1.0, "gap")]),
    ("coldstore", "Cold Store", "LifeSupp", (9, -21, 15, -14.5),
     [("N", 10.5, 13.0, "gap"), ("W", -18.5, -16.0, "door", "Storage")]),
    ("musicbooth", "Show Control", "Comms", (16, 9.5, 22.5, 16.8),
     [("W", 12.0, 14.5, "gap")]),
    ("shooting", "Shooting Gallery", "Weapons", (-20, 8.5, -10, 16),
     [("S", -16.5, -14.0, "gap"), ("E", 11.0, 13.5, "gap")]),
    # Durchgang mit Mechanik (eigener Raum-Typ, keine Tasks): Zickzack-Tunnel Karussell -> Werkstatt
    ("ghosttrain", "Ghost Train", "Laboratory", (-17, -11, -13, -4),
     [("N", -16.25, -13.75, "gap"), ("S", -16.25, -13.75, "gap")]),
]

# ------------------------------------------------------------------ offene Flaechen
CORNER = 2.0
CLEARINGS = [
    ("ferriswheel", "Ferris Wheel", "Nav", (-6, 8.5, 5, 17.5)),
    ("lighttower", "Show Control", "Shields", (8.5, 9, 15, 17.3)),
    ("coaster", "Coaster Station", "Reactor", (9, -3, 21, 6)),
    # Durchgang mit Mechanik: Kanal mit zwei Bruecken zwischen Bahnhof und Kuehlhaus
    ("logflume", "Log Flume", "Greenhouse", (11, -11, 20, -5)),
]
# Kein Hof um die Gebaeude (User 23.09.): die Wege verbinden die Eingaenge.
YARD = {k: 0.0 for k in ("fairground", "workshop", "carousel", "bumpercars", "security", "substation",
                         "firstaid", "office", "coldstore", "musicbooth", "shooting", "ghosttrain")}

# ------------------------------------------------------------------ Wege (Mittellinien)
PATHS = [
    [(-8.5, 1.75), (-6.5, 1.75)],                  # Karussell O -> Festplatz W
    [(6.5, 1.75), (9, 1.75)],                      # Festplatz O -> Bahnhof
    [(0, 6.5), (0, 8.5)],                          # Festplatz N -> Riesenrad
    [(-9.5, 12.25), (-6, 12.25)],                  # Schiessbude O -> Riesenrad
    [(-15.25, 6.5), (-15.25, 8.0)],                # Karussell N -> Schiessbude S
    [(5, 12.6), (8.5, 12.6)],                      # Riesenrad O -> Bahnuebergang C1 -> Lichtturm-Hof
    [(12.1, 6), (12.1, 9)],                        # Bahnhof N -> Bahnuebergang C2 -> Lichtturm-Hof
    [(15, 13.25), (16, 13.25)],                    # Lichtturm-Hof -> Musikzentrale
    [(-6.5, -4.75), (12, -4.75)],                  # Vorplatz vor den Drehkreuzen (Buero, Security, Kanal)
    [(15, -3), (15, -5)],                          # Bahnhof S -> Log Flume
    [(-11.5, -12.75), (16, -12.75)],               # Gasse: Autoscooter, Buero S, Umspannhaus, Kuehlhaus
    [(-12, -16.25), (-11, -16.25)],                # Werkstatt O -> Autoscooter W
    [(15.5, -11), (15.5, -12.5)],                  # Log Flume S -> Gasse
    [(7.75, -12.75), (7.75, -17.25)],              # Gasse -> Kuehlhaus W-Tor
    [(16.25, -12.75), (16.25, -18.25)],            # Gasse -> Sanitaetszelt W-Tor
]

# ------------------------------------------------------------------ Achterbahn und Kanal
# Strecke als Baender (sperren den Weg, nicht die Sicht), Bahnuebergaenge als Luecken darin.
RAIL = [
    ("rect", 6.8, 7.3, 8.0, 19.0),       # West-Schenkel
    ("rect", 6.8, 7.3, 24.5, 8.5),       # Sued-Schenkel (am Bahnhof entlang)
    ("rect", 23.3, 8.5, 24.5, 19.0),     # Ost-Schenkel
    ("rect", 8.0, 17.8, 23.3, 19.0),     # Nord-Schenkel
]
CROSSINGS = [   # key, Luecke im Band (rect), Richtung der Schranke
    ("C1", ("rect", 6.8, 11.0, 8.0, 14.2), "vertical"),
    ("C2", ("rect", 10.5, 7.3, 13.7, 8.5), "horizontal"),
]
WATER = [("rect", 9.5, -8.7, 21.5, -7.3)]
BRIDGES = [("rect", 12.0, -8.7, 14.0, -7.3), ("rect", 17.0, -8.7, 19.0, -7.3)]

# Drehkreuze: die zwei Suedoeffnungen des Festplatzes
TURNSTILES = [("in", ("rect", -4.5, -3.5, -2.0, -3.0)), ("out", ("rect", 2.0, -3.5, 4.5, -3.0))]

# ------------------------------------------------------------------ Spielpunkte
SPAWN = (0.0, 1.2)
SPAWN_RADIUS = 2.4
EMERGENCY = (0.0, 3.4)
SURVEILLANCE = (4.1, -8.1)      # Park Office, Security-Nebenraum: Monitorwand NW
ADMIN_TABLE = (-1.5, -8.3)      # Park Office, Lageplan
FREEPLAY = (5.2, -1.6)

FIXED = {
    # Coaster Brake Failure (Reaktor): Bremshebel an beiden Enden des Bahnsteigs
    "Reactor/UpperHandConsole/0": (10.6, 4.9),
    "Reactor/LowerHandConsole/1": (19.4, 4.9),
    # Ammonia Leak (O2): Kuehlhaus + Parkbuero
    "LifeSupp/NoOxyConsole/0": (10.0, -19.8),
    "Admin/NoOxyConsole/1": (1.2, -7.3),
    "Electrical/SwitchConsole/0": (1.3, -17.2),
    "Comms/FixCommsConsole/0": (21.5, 15.6),
    "MedBay/MedScanner/0": (19.5, -18.0),
}

# Vents: drei Ringe quer ueber die Karte, dazu zwei Querverbindungen ueber den dritten Nachbarn
# (Vent.Center). Vent 4 entfaellt mit dem Spiegelkabinett (faellt dem Wipe zu).
VENTS = {
    0: (-19.3, 9.3), 3: (-4.3, 16.0), 12: (9.4, 16.6), 6: (21.8, 16.1),
    1: (-16.6, -5.0), 5: (-18.2, -2.2), 13: (-5.3, -10.9), 7: (20.3, -2.3),
    2: (-20.3, -18.3), 9: (-2.2, -20.3), 10: (5.4, -17.4), 11: (14.3, -20.3), 8: (18.2, -15.2),
}
VENT_NETS = [
    [0, 3, 12, 6],          # Nord: Schiessbude, Riesenrad, Lichtturm-Hof, Musikzentrale
    [1, 5, 13, 7],          # Mitte: Geisterbahn, Karussell, Parkbuero, Bahnhof
    [2, 9, 10, 11, 8],      # Sued: Werkstatt, Autoscooter, Umspannhaus, Kuehlhaus, Sanitaetszelt
]
VENT_BRIDGES = [(3, 5), (7, 8)]     # Riesenrad <-> Karussell, Bahnhof <-> Sanitaetszelt

# Kameras (4): Bahnuebergang C1, Festplatz-Nord, Geisterbahn-Einfahrt, Kanalbruecke
CAMERAS = [(4.2, 14.6), (2.8, 5.7), (-13.4, -4.4), (18.8, -6.0)]

# ------------------------------------------------------------------ Hindernisse
# OPAQUE: Weg + Sicht, GLASS: nur Weg. Art None = Sichtkern ohne eigenes Sprite.
WHEEL = (-0.5, 13.0)                    # Riesenrad-Mitte
TOWER = (11.8, 13.2)                    # Lichtturm
ARENA = ("rect", -8.4, -20.1, -3.6, -15.3)
OPAQUE = [
    (("rect", -17.0, -6.3, -14.3, -5.8), "tunnelwand"),        # Geisterbahn: Zickzack-Tunnel
    (("rect", -15.7, -8.9, -13.0, -8.4), "tunnelwand"),
    (("rect", -5.6, 4.2, -3.6, 5.7), "bude"),                  # Festplatz: Buden in den Nordecken
    (("rect", 3.6, 4.2, 5.6, 5.7), "bude"),
    (("circle", -14.0, 1.5, 0.8), None),                       # Karussell: Mittelgehaeuse sperrt die Sicht
    (("rect", 13.8, -1.5, 16.2, 0.3), "kasse"),                # Bahnhof: Kassenhaeuschen
    (("rect", -1.6, -3.0, 1.6, -2.2), "kassenhaeuschen"),      # Festplatz: zwischen den Drehkreuzen
    (("rect", -20.9, -18.6, -19.4, -16.0), "regal"),           # Werkstatt
    (("rect", 16.4, 9.9, 18.0, 11.1), "lautsprecher"),         # Musikzentrale
]
GLASS = [
    (("circle", WHEEL[0], WHEEL[1], 3.2), "riesenrad"),        # Radkranz: sperrt den Weg, man sieht durch
    (("circle", WHEEL[0], WHEEL[1], 1.0), "radnabe"),          # Nabe: niedriges Podest (Plan: GLASS)
    (("circle", TOWER[0], TOWER[1], 1.2), "turm"),             # Beleuchtungsturm: Gitterturm (Plan: GLASS)
    (("circle", -14.0, 1.5, 2.8), "karussell"),                # Karussell: Weg ueber die ganze Scheibe gesperrt
    (("rect", -19.0, 13.4, -11.0, 14.2), "theke"),             # Schiessbude
    (ARENA, "arena"),                                          # Autoscooter-Bahn
    (("rect", 18.8, 9.9, 21.8, 10.9), "mischpult"),            # Musikzentrale
    (("rect", 19.9, -20.6, 21.7, -19.0), "liege"),             # Sanitaetszelt
    (("rect", 9.4, -16.9, 11.4, -15.5), "kuehltruhe"),         # Kuehlhaus: Eistruhe, Hueftrhoehe (Plan: GLASS)
]

# ------------------------------------------------------------------ Welt-System (AtlasParkWorld)
# Karussell-Fahrt: Seile sperren die Nordoeffnung (zur Schiessbude); das Karussell bleibt ueber seine
# zwei Tueren (Sued zur Geisterbahn, Ost zum Festplatz) erreichbar.
CAROUSEL_GATES = [("carousel", "N")]
CAROUSEL = (-14.0, 1.5, 2.8)            # Mitte + Radius (wie die GLASS-Scheibe)
FLUME_BRIDGE = 1                        # BRIDGES-Index, den der Bootssturz kurz sperrt (Ost)
TRACK_LOOP = [(23.9, 7.9), (7.4, 7.9), (7.4, 18.4), (23.9, 18.4), (23.9, 7.9)]   # Zugweg, Start am Bahnhof
CANAL_LINE = [(21.5, -8.0), (9.5, -8.0)]                                         # Bootsweg, Ost -> West
GHOST_RIDE = [(-15.0, -4.2), (-15.0, -5.0), (-13.6, -5.0), (-13.6, -7.3), (-16.4, -7.3), (-16.4, -9.8),
              (-15.0, -9.8), (-15.0, -10.9)]                                     # Wagen durch den Zickzack
GHOST_MONITOR = (-18.8, -12.6)          # Foto-Monitor an der Werkstatt-Nordwand, westlich des Tunnelausgangs
