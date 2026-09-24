# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_layout.py - Moonlight Carnival (docs/PARK_KONZEPT.md), Grundriss v1 als Graybox.
#
# Gleiches Format wie wald_layout.py, dazu drei Park-Eigenheiten:
#   - RAIL: die Achterbahnstrecke. Sperrt den Weg, nicht die Sicht; passierbar nur an den
#     Bahnuebergaengen (CROSSINGS). Sie umschliesst den Nordost-Block (Light Tower, Music Booth).
#   - WATER + BRIDGES: der Kanal der Wildwasserbahn mit zwei Bruecken.
#   - TURNSTILES: zwei Drehkreuz-Oeffnungen zwischen Promenade und Haupteingang (Einbahn: West
#     nur hinein in den Park = nach Norden, Ost nur hinaus = nach Sueden; Welt-System, Schritt 4).
# Alle Zahlen in Weltmetern (Norden = +y), Karte 74 x 50 m (Museum 61 x 43), Zentrum = Festplatz.
#
# 18 Bereiche: 14 Skeld-Systeme + 4 Attraktionen mit Raum-Typen, die die Skeld nicht kennt
# (Prototyp "extraroom" bestanden, 23.09.). Die 13 Skeld-Tueren sitzen in den sieben
# Tuergruppen wie bei Museum und Wald: senkrecht (O/W-Waende) 7, waagerecht (N/S) 6.

BOUNDS = (-37.0, -25.0, 37.0, 25.0)
WALL = 0.5
PATH_W = 3.2
DOOR_W = 2.5

# ------------------------------------------------------------------ Gebaeude und Umzaeunungen
# key, Anzeigename, Raum-Typ, Innenraum [x0,y0,x1,y1], Oeffnungen [(Seite, von, bis, Art)]
#   Art "door" = Skeld-Tuer (Barrier Gate), "gap" = offen
BUILDINGS = [
    # Tuergruppen (Skeld): Cafeteria 3, Storage 3, UpperEngine 2, LowerEngine 2, Security 1, MedBay 1, Electrical 1
    ("fairground", "Fairground", "Cafeteria", (-8, -5, 8, 7),
     [("W", 0.5, 3.0, "door"), ("E", 0.5, 3.0, "door"), ("S", -1.25, 1.25, "door"), ("N", -3.0, 3.0, "gap")]),
    ("workshop", "Workshop", "Storage", (-33, -22, -24, -13),
     [("N", -30.0, -27.5, "door"), ("E", -18.75, -16.25, "door"), ("W", -18.75, -16.25, "door")]),
    ("carousel", "Carousel", "UpperEngine", (-24, -5, -13, 5),
     [("S", -19.75, -17.25, "door"), ("E", 0.5, 3.0, "door"), ("W", 0.0, 2.5, "gap"), ("N", -19.5, -17.0, "gap")]),
    ("bumpercars", "Bumper Cars", "LowerEngine", (-21, -23, -11, -14),
     [("N", -15.75, -13.25, "door"), ("W", -18.75, -16.25, "door"), ("E", -21.0, -18.5, "gap")]),
    ("security", "Security Booth", "Security", (10, -16, 17, -10),
     [("N", 12.25, 14.75, "door")]),
    ("substation", "Substation", "Electrical", (10, -24, 17, -20.5),
     [("N", 12.25, 14.75, "door")]),
    ("firstaid", "First Aid Tent", "MedBay", (31, -24, 36.5, -15),
     [("W", -20.75, -18.25, "door")]),
    # nur offene Durchgaenge
    ("office", "Park Office", "Admin", (11, -5, 20, 3),
     [("W", 0.5, 3.0, "gap"), ("E", -1.5, 1.0, "gap"), ("N", 14.5, 17.0, "gap"), ("S", 14.5, 17.0, "gap")]),
    ("coldstore", "Cold Store", "LifeSupp", (21, -24, 27, -14),
     [("N", 22.5, 25.0, "gap"), ("W", -21.0, -18.5, "gap")]),
    ("musicbooth", "Music Booth", "Comms", (25, 12, 33, 20),
     [("W", 14.5, 17.0, "gap"), ("S", 27.5, 30.0, "gap")]),
    ("shooting", "Shooting Gallery", "Weapons", (-23, 13, -13, 21),
     [("S", -19.5, -17.0, "gap"), ("E", 15.0, 17.5, "gap"), ("W", 15.0, 17.5, "gap")]),
    # Attraktionen (eigene Raum-Typen, keine Tasks)
    ("mirrors", "Hall of Mirrors", "Lounge", (-36, 12, -27, 23),
     [("E", 15.0, 17.5, "gap"), ("S", -33.5, -31.0, "gap")]),
    ("ghosttrain", "Ghost Train", "Laboratory", (-36, -5, -28, 8),
     [("N", -33.5, -31.0, "gap"), ("S", -33.5, -31.0, "gap"), ("E", 0.0, 2.5, "gap")]),
]

# ------------------------------------------------------------------ offene Flaechen
CORNER = 2.0
CLEARINGS = [
    ("ferriswheel", "Ferris Wheel", "Nav", (-7, 11, 6, 24)),
    ("lighttower", "Light Tower", "Shields", (12, 11, 22, 21)),
    ("coaster", "Coaster Station", "Reactor", (22, -5.5, 35, 7.5)),
    ("maingate", "Main Gate", "Kitchen", (-6, -25, 6, -18.4)),
    ("logflume", "Log Flume", "Greenhouse", (20, -13.5, 37, -6)),
]
# Kein Hof um die Gebaeude (User 23.09.: "die Aussenbereiche um die Gebaeude, hier nicht noetig"):
# die Gebaeude stehen im Dunkeln, nur die Wege verbinden die Eingaenge.
YARD = {k: 0.0 for k in ("fairground", "workshop", "carousel", "bumpercars", "security", "substation",
                         "firstaid", "office", "coldstore", "musicbooth", "shooting", "mirrors", "ghosttrain")}

# ------------------------------------------------------------------ Wege (Mittellinien)
PATHS = [
    [(-8, 1.75), (-13, 1.75)],                                    # Festplatz W -> Karussell O
    [(8, 1.75), (11, 1.75)],                                      # Festplatz O -> Parkbuero W
    [(0, -5), (0, -16.5)],                                        # Festplatz S -> Promenade
    [(-5, -16.5), (5, -16.5)],                                    # Vorplatz der Drehkreuze
    [(0, 7), (0, 12)],                                            # Festplatz N -> Riesenrad
    [(-7, 17), (-12.5, 16.25)],                                   # Riesenrad W -> Schiessbude O
    [(6, 17), (12.5, 16.5)],                                      # Riesenrad O -> Bahnuebergang C1 -> Lichtturm
    [(-23, 16.25), (-27, 16.25)],                                 # Schiessbude W -> Spiegelkabinett O
    [(-18.25, 12.5), (-18.25, 5.5)],                              # Schiessbude S -> Karussell N
    [(-32.25, 12), (-32.25, 8)],                                  # Spiegelkabinett S -> Geisterbahn N
    [(-30.0, 9.2), (-30.0, 10.8)],                                # ... zum Vorplatz verbreitert (Foto-Monitor)
    [(-28, 1.25), (-24, 1.25)],                                   # Geisterbahn O -> Karussell W
    [(-32.25, -5), (-32.25, -9.5), (-28.75, -9.5), (-28.75, -12.5)],  # Geisterbahn S -> Werkstatt N
    [(-33.5, -17.5), (-35.3, -17.5), (-35.3, -9.5), (-32.25, -9.5)],  # Werkstatt W -> West-Gasse
    [(-23.5, -17.5), (-21, -17.5)],                               # Werkstatt O -> Autoscooter W
    [(-18.5, -5.5), (-18.5, -9.5)],                               # Karussell S -> Mittelweg
    [(-28.75, -9.5), (21, -9.0)],                                 # Mittelweg (West bis Kanalspitze)
    [(-14.5, -9.5), (-14.5, -13.5)],                              # Mittelweg -> Autoscooter N
    [(-10.5, -19.75), (-6, -21.5)],                               # Autoscooter O -> Haupteingang
    [(6, -21.5), (9.2, -18.25), (19.5, -18.25), (20.5, -19.75)],  # Haupteingang -> Gasse -> Kuehlhaus W
    [(13.5, -18.25), (13.5, -20.0)],                              # Gasse -> Umspannhaus N
    [(15.75, -5.5), (15.75, -8)],                                 # Parkbuero S -> Mittelweg
    [(20, -0.25), (22.5, -0.25)],                                 # Parkbuero O -> Bahnhof
    [(15.75, 3.5), (15.75, 12)],                                  # Parkbuero N -> Bahnuebergang C2 -> Lichtturm
    [(22, 16), (24.5, 15.75)],                                    # Lichtturm -> Musikzentrale W
    [(28.75, 12), (29.2, 7.5)],                                   # Musikzentrale S -> Bahnuebergang C3 -> Bahnhof
    [(23.75, -13.5), (23.75, -14.5)],                             # Log Flume -> Kuehlhaus N
    [(29, -13.5), (29, -19.5), (30.5, -19.5)],                    # Log Flume -> Gasse -> Sanitaetszelt W
]

# ------------------------------------------------------------------ Achterbahn und Kanal
# Strecke als Baender (sperren den Weg, nicht die Sicht), Bahnuebergaenge als Luecken darin.
RAIL = [
    ("rect", 8.8, 8.0, 10.0, 25.0),      # West-Schenkel
    ("rect", 8.8, 8.0, 37.0, 9.2),       # Sued-Schenkel (am Bahnhof entlang)
    ("rect", 35.8, 9.2, 37.0, 25.0),     # Ost-Schenkel (Kartenrand)
    ("rect", 10.0, 23.8, 35.8, 25.0),    # Nord-Schenkel (Kartenrand)
]
CROSSINGS = [   # key, Luecke im Band (rect), Richtung der Schranke
    ("C1", ("rect", 8.8, 15.4, 10.0, 18.6), "vertical"),
    ("C2", ("rect", 14.2, 8.0, 17.4, 9.2), "horizontal"),
    ("C3", ("rect", 27.6, 8.0, 30.8, 9.2), "horizontal"),
]
WATER = [("rect", 21.5, -9.6, 37.0, -7.4)]
BRIDGES = [("rect", 24.0, -9.6, 26.5, -7.4), ("rect", 31.5, -9.6, 34.0, -7.4)]

# Drehkreuze (Welt-System spaeter): Zaun mit zwei Oeffnungen, Haeuschen dazwischen
TURNSTILES = [("in", ("rect", -4.5, -18.4, -2.0, -17.9)), ("out", ("rect", 2.0, -18.4, 4.5, -17.9))]

# ------------------------------------------------------------------ Spielpunkte
SPAWN = (0.0, 0.5)
SPAWN_RADIUS = 3.0
EMERGENCY = (0.0, 2.5)
SURVEILLANCE = (11.6, -11.6)    # Security Booth, Monitorwand NW
ADMIN_TABLE = (15.5, -1.8)      # Park Office, Lageplan
FREEPLAY = (5.0, -3.4)

FIXED = {
    # Coaster Brake Failure (Reaktor): Bremshebel an beiden Enden des Bahnsteigs
    "Reactor/UpperHandConsole/0": (23.6, 6.4),
    "Reactor/LowerHandConsole/1": (33.6, 6.4),
    # Ammonia Leak (O2): Kuehlhaus + Parkbuero
    "LifeSupp/NoOxyConsole/0": (22.0, -22.8),
    "Admin/NoOxyConsole/1": (19.2, 2.2),
    "Electrical/SwitchConsole/0": (10.8, -23.2),
    "Comms/FixCommsConsole/0": (32.0, 18.8),
    "MedBay/MedScanner/0": (33.5, -21.0),
}

# Vents: alle 14 Skeld-Vents in drei langen Ringen quer ueber die Karte (User 23.09.: "nicht genug
# Bewegungspotential"), dazu zwei Querverbindungen zwischen den Ringen ueber den dritten Nachbarn
# (Vent.Center). Per Vent kommt man ueber die ganze Karte, auch ueber Achterbahn und Kanal.
VENTS = {
    0: (-34.6, 21.4), 3: (-14.4, 19.6), 4: (4.6, 22.4), 12: (20.2, 12.8), 6: (26.6, 18.6),
    1: (-34.6, 6.6), 5: (-15.0, -3.6), 13: (19.2, -4.2), 7: (33.8, -4.2),
    2: (-31.6, -21.0), 9: (-12.4, -22.2), 10: (4.8, -23.8), 11: (16.2, -23.0), 8: (35.4, -16.4),
}
VENT_NETS = [
    [0, 3, 4, 12, 6],       # Nord: Spiegelkabinett, Schiessbude, Riesenrad, Lichtturm, Musikzentrale
    [1, 5, 13, 7],          # Mitte: Geisterbahn, Karussell, Parkbuero, Bahnhof
    [2, 9, 10, 11, 8],      # Sued: Werkstatt, Autoscooter, Haupteingang, Umspannhaus, Sanitaetszelt
]
VENT_BRIDGES = [(4, 5), (7, 8)]     # Riesenrad <-> Karussell, Bahnhof <-> Sanitaetszelt

# Kameras (4): Bahnuebergang C1, Festplatz-Nord, Geisterbahn-Nord, Kanalbruecke
CAMERAS = [(6.8, 18.0), (4.0, 12.6), (-34.1, 10.2), (28.8, -6.8)]   # Geisterbahn-Kamera links, rechts haengt der Foto-Monitor

# ------------------------------------------------------------------ Hindernisse
# OPAQUE: Weg + Sicht, GLASS: nur Weg.
OPAQUE = [
    (("rect", -36.0, -2.2, -30.5, -1.6), "tunnelwand"),        # Geisterbahn: Zickzack-Tunnel
    (("rect", -33.5, 3.6, -28.0, 4.2), "tunnelwand"),
    (("rect", -7.4, 4.6, -5.4, 6.4), "bude"),                  # Festplatz: Buden in den Ecken
    (("rect", 5.4, 4.6, 7.4, 6.4), "bude"),
    (("rect", -7.4, -4.4, -5.4, -2.6), "bude"),
    (("circle", -0.5, 18.6, 1.0), "radnabe"),                  # Riesenrad: Nabe/Stuetze
    (("circle", 17.0, 16.4, 1.2), "turm"),                     # Beleuchtungsturm
    (("circle", -18.5, 0.0, 2.8), "karussell"),                # Karussell (Dach)
    (("rect", 26.8, -4.0, 29.2, -2.2), "kasse"),               # Bahnhof: Kassenhaeuschen
    (("rect", -2.0, -18.6, 2.0, -17.4), "kassenhaeuschen"),    # Haupteingang zwischen den Drehkreuzen
    (("rect", 21.4, -16.4, 23.4, -15.0), "kuehltruhe"),        # Kuehlhaus
    (("rect", -26.0, -21.6, -24.5, -19.0), "regal"),           # Werkstatt
    (("rect", 25.4, 12.4, 27.0, 13.6), "lautsprecher"),        # Musikzentrale
]
GLASS = [
    (("circle", -0.5, 18.6, 3.2), "riesenrad"),                # Radkranz: sperrt den Weg, man sieht durch
    (("rect", -22.0, 18.4, -14.0, 19.2), "theke"),             # Schiessbude
    (("rect", -18.4, -21.4, -13.6, -16.6), "arena"),           # Autoscooter-Bahn
    (("rect", -6.0, -18.4, -4.5, -17.9), "zaun"),              # Drehkreuz-Zaun links
    (("rect", 4.5, -18.4, 6.0, -17.9), "zaun"),                # Drehkreuz-Zaun rechts
    (("rect", 29.6, 12.4, 32.6, 13.4), "mischpult"),           # Musikzentrale
    (("rect", 34.4, -23.6, 36.2, -22.0), "liege"),             # Sanitaetszelt
    (("rect", -34.2, 13.6, -33.6, 20.8), "spiegel"),           # Spiegelkabinett: Glaswand-Labyrinth
    (("rect", -31.2, 14.6, -30.6, 22.4), "spiegel"),
    (("rect", -33.6, 18.0, -31.2, 18.6), "spiegel"),
    (("rect", -30.6, 16.6, -28.4, 17.2), "spiegel"),
]

# ------------------------------------------------------------------ Welt-System (Schritt 4, AtlasParkWorld)
# Karussell-Fahrt: Seile sperren diese Oeffnungen (Nord zur Schiessbude, West zur Geisterbahn); das Karussell
# bleibt ueber seine zwei Tueren (Sued, Ost) erreichbar.
CAROUSEL_GATES = [("carousel", "N"), ("carousel", "W")]
CAROUSEL = (-18.5, 0.0, 2.8)            # Mitte + Radius (wie das OPAQUE-Karussell)
FLUME_BRIDGE = 1                        # BRIDGES-Index, den der Bootssturz kurz sperrt (Ost, an der Rinne)
TRACK_LOOP = [(36.4, 8.6), (9.4, 8.6), (9.4, 24.4), (36.4, 24.4), (36.4, 8.6)]   # Zugweg, Start am Bahnhof
CANAL_LINE = [(37.0, -8.5), (21.5, -8.5)]                                       # Bootsweg, Ost -> West
GHOST_RIDE = [(-32.2, -4.6), (-32.2, -3.2), (-29.3, -3.2), (-29.3, 2.9), (-34.8, 2.9), (-34.8, 5.4),
              (-32.2, 5.4), (-32.2, 7.8)]                                        # Wagen durch den Zickzack
GHOST_MONITOR = (-29.4, 10.0)           # Foto-Monitor auf dem Vorplatz am Nordausgang der Geisterbahn
