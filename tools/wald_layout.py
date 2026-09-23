# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_layout.py - Forststation Nadelkamm, Grundriss v6 (Neubau nach dem Museums-Verfahren).
#
# Leitidee (aus den Fehlern von v4 gelernt): Polus statt Wildnis. Die Station besteht aus
# BEGEHBAREN Holzgebaeuden mit Tueren (die 13 Skeld-Tueren sitzen in Gebaeuden, wie auf Polus)
# und offenen Lichtungen, verbunden durch 3,2 m breite Waldwege. Der dichte Wald ist die Wand.
# Alle Zahlen in Weltmetern (Norden = +y), Karte 64 x 44 m, Zentrum = Messe.
#
# 14 Bereiche = 14 Skeld-Systeme. Gebaeude mit Tueren sind genau die sieben Skeld-Tuergruppen
# (Cafeteria 3, Storage 3, UpperEngine 2, LowerEngine 2, Security 1, MedBay 1, Electrical 1);
# senkrechte Tueren (in O/W-Waenden) 7, waagerechte (N/S) 6 - wie die Skeld-Tuerbestaende.

BOUNDS = (-32.0, -22.0, 32.0, 22.0)
WALL = 0.5            # Wandstaerke der Holzgebaeude
PATH_W = 3.2          # Wegbreite
DOOR_W = 2.5          # Tuerbreite

# ------------------------------------------------------------------ Gebaeude
# key, Anzeigename, Skeld-System, Innenraum [x0,y0,x1,y1], Tueren [(Seite, von, bis, Art)]
#   Seite: "N","S","E","W"; von/bis entlang der Wand; Art "door" (Skeld-Tuer) oder "gap" (offen)
BUILDINGS = [
    ("messe", "Mess Hall", "Cafeteria", (-5, -2, 5, 6),
     [("W", 1.0, 3.5, "door"), ("E", 1.0, 3.5, "door"), ("S", -1.25, 1.25, "door")]),
    ("feldstation", "Field Station", "Admin", (-17, -2, -9, 5),
     [("W", 0.25, 2.75, "gap"), ("E", 0.75, 3.25, "gap"), ("N", -14.25, -11.75, "gap")]),
    ("labor", "Field Lab", "MedBay", (-30, -3, -22, 5),
     [("E", 0.25, 2.75, "door")]),
    ("saegewerk", "Sawmill", "UpperEngine", (-15, 12, -3, 19),
     [("S", -10.0, -7.5, "door"), ("E", 14.0, 16.5, "door")]),
    ("lager", "Storehouse", "Storage", (-6, -19, 6, -11),
     [("N", -1.25, 1.25, "door"), ("W", -16.0, -13.5, "door"), ("E", -16.0, -13.5, "door")]),
    ("bootshaus", "Boathouse", "LowerEngine", (10, -19, 18, -12),
     [("N", 12.75, 15.25, "door"), ("W", -17.0, -14.5, "door")]),
    ("wachstube", "Ranger Office", "Security", (-30, -18, -23, -11),
     [("N", -27.75, -25.25, "door")]),
    ("generator", "Generator Shed", "Electrical", (-18, -18, -11, -12),
     [("N", -15.75, -13.25, "door")]),
]

# ------------------------------------------------------------------ Lichtungen (offen)
# key, Anzeigename, Skeld-System, Flaeche [x0,y0,x1,y1] (abgerundet, Rundung CORNER)
CORNER = 2.0
CLEARINGS = [
    ("aussicht", "Lookout Rock", "Nav", (-30, 9, -19, 19)),
    ("funkmast", "Radio Mast", "Comms", (1, 10, 12, 19)),
    ("wassertank", "Water Tower", "LifeSupp", (16, 9, 29, 19)),
    ("hochsitz", "Hunting Stand", "Weapons", (9, -3, 18, 7)),
    ("pumpe", "Pump Station", "Reactor", (21, -4, 30, 6)),
    ("bachsteg", "Creek Dock", "Shields", (21, -19, 30, -9)),
]
# Hof um die Gebaeude: so weit wird Waldboden um jedes Gebaeude freigelassen
YARD = {"messe": 3.0, "feldstation": 2.2, "labor": 2.2, "saegewerk": 2.4, "lager": 2.6,
        "bootshaus": 2.2, "wachstube": 2.2, "generator": 2.2}

# ------------------------------------------------------------------ Wege (Mittellinien)
PATHS = [
    [(5, 2.25), (9, 2.25)],                    # Messe O -> Hochsitz
    [(18, 2), (21, 2)],                        # Hochsitz -> Pumpe
    [(0, -2), (0, -11)],                       # Messe S -> Lager N
    [(-5, 2.25), (-9, 2.0)],                   # Messe W -> Feldstation O
    [(-17, 1.5), (-22, 1.5)],                  # Feldstation W -> Labor O
    [(-13, 5), (-13, 11)],                     # Feldstation N -> Saegewerk-Hof
    [(-26, 5), (-26, 9)],                      # Labor -> Aussicht
    [(-19, 11), (-15, 11)],                    # Aussicht -> Saegewerk-Hof
    [(-3, 15.25), (1, 15.25)],                 # Saegewerk O -> Funkmast
    [(12, 15), (16, 15)],                      # Funkmast -> Wassertank
    [(24, 9), (24, 6)],                        # Wassertank -> Pumpe
    [(10, 10), (12, 7)],                       # Funkmast -> Hochsitz
    [(-26, -3), (-26, -8.5)],                  # Labor -> Wachstube-Hof
    [(-23, -14.5), (-19.5, -14.5)],            # Wachstube-Hof -> Generator-Hof
    [(-11, -14.75), (-6, -14.75)],             # Generator-Hof -> Lager W
    [(6, -14.75), (10, -15.75)],               # Lager O -> Bootshaus W
    [(14, -12), (14, -3)],                     # Bootshaus N -> Hochsitz
    [(18, -14), (21, -14)],                    # Bootshaus-Hof -> Bachsteg
    [(25.5, -9), (25.5, -4)],                  # Bachsteg -> Pumpe
]

# ------------------------------------------------------------------ Spielpunkte
SPAWN = (0.0, 2.0)
SPAWN_RADIUS = 2.4
EMERGENCY = (0.0, 2.5)          # Messe: Glocke vor dem langen Tisch (Pfosten frei vom Tisch)
SURVEILLANCE = (-28.0, -15.0)   # Wachstube, vor der Monitorwand
ADMIN_TABLE = (-13.0, 1.3)      # Feldstation: Suedkante des Kartentischs
FREEPLAY = (3.8, -1.2)

# Sabotage-Stationen: Waldbrand (Reaktor) Wassertank NO + Aussicht NW, Trinkwasser (O2) Labor W + Bachsteg SO
FIXED = {
    "Reactor/UpperHandConsole/0": (25.5, 17.6),     # A1 Wassertank (neben, nicht unter dem Turmdach)
    "Reactor/LowerHandConsole/1": (-20.6, 16.5),    # A2 Aussicht (NW; A1 am Wassertank NO)
    "LifeSupp/NoOxyConsole/0": (-29.3, 2.4),        # B1 Labor
    "Admin/NoOxyConsole/1": (27.6, -17.8),          # B2 Bachsteg
    "Electrical/SwitchConsole/0": (-17.4, -15.0),   # Sicherungen im Generatorhaus
    "Comms/FixCommsConsole/0": (4.6, 17.6),         # Funkgeraet neben dem Mast
    "MedBay/MedScanner/0": (-26.0, -1.2),           # Scanner im Labor
}

# Vents: Skeld-Id -> Platz, drei Netze (keins verbindet A1/A2 oder B1/B2)
VENTS = {
    11: (-28.5, 10.5), 3: (-16.8, -12.8), 5: (-24.0, -11.6),      # West: Aussicht, Generator, Wachstube
    7: (-4.0, 18.3), 6: (4.0, -18.3), 0: (-8.0, -1.3),            # Mitte: Saegewerk, Lager, Feldstation
    10: (10.2, 11.0), 4: (27.8, 5.0), 9: (17.0, -18.3),           # Ost: Funkmast, Pumpe, Bootshaus
}
VENT_NETS = [[11, 3, 5], [7, 6, 0], [10, 4, 9]]

# Kameras (4): Messe-Vorplatz, Hochsitz, Wassertank, Lager-Hof
CAMERAS = [(4.0, -3.0), (17.0, 6.0), (27.5, 18.0), (-5.0, -9.0)]

# ------------------------------------------------------------------ Hindernisse
# ("rect", x0, y0, x1, y1) | ("circle", cx, cy, r) | ("ellipse", cx, cy, rx, ry)
# OPAQUE: Weg + Sicht, GLASS: nur Weg. KINDS = Objektart fuer das Zeichnen.
OPAQUE = [
    (("rect", -16.4, 4.2, -14.4, 4.9), "regal"),           # Feldstation: Regal
    (("rect", -29.4, -2.6, -28.5, 1.0), "schrank"),
    (("rect", -5.6, -18.4, -2.4, -17.2), "kisten"),        # Lager
    (("rect", 2.4, -18.4, 5.6, -17.2), "kisten"),
    (("rect", -1.2, -16.2, 1.2, -14.8), "kisten"),
    (("rect", -29.4, -17.4, -28.6, -13.4), "monitore"),    # Wachstube (endet unter dem Stromkasten)
    (("rect", -17.4, -17.4, -14.4, -15.8), "aggregat"),    # Generator
    (("circle", -24.5, 14.5, 1.6), "fels"),                # Aussicht: Felsen
    (("rect", -29.0, 17.0, -26.0, 18.6), "turm"),          # Aussichtsturm-Fuss
    (("circle", 6.5, 15.0, 0.9), "mast"),                  # Funkmast
    (("circle", 22.5, 14.0, 2.2), "tank"),                 # Wassertank
    (("rect", 24.5, -1.8, 27.8, 1.2), "pumpenhaus"),       # Pumpe
    (("rect", 13.0, 2.6, 14.6, 4.2), "hochsitz"),          # Hochsitz
    (("circle", 3.2, 13.2, 0.8), "baum"),                  # Einzelbaeume in Lichtungen
    (("circle", 19.0, 11.5, 0.8), "baum"),
    (("circle", 26.8, -13.6, 0.8), "baum"),                # frei vom Stromkasten an der Nordkante
]
GLASS = [
    # niedrig: sperrt den Weg, nicht die Sicht (User 23.09.: ueber den langen Tisch muss man schauen koennen)
    (("rect", -3.5, 3.6, 3.5, 4.4), "tisch_lang"),         # Messe: langer Tisch
    (("rect", -4.4, -1.4, -2.6, -0.3), "herd"),            # Messe: Herd
    (("rect", -29.4, 3.8, -27.6, 4.9), "laborbank"),       # Labor
    (("rect", -12.0, 15.0, -6.0, 16.6), "saegetisch"),     # Saegewerk
    (("rect", -14.4, 12.6, -12.0, 14.0), "holzstapel"),
    (("rect", 12.0, -18.4, 16.0, -16.2), "boot"),          # Bootshaus
    (("rect", -3.8, 0.4, -2.0, 1.2), "bank"),              # Messe: Baenke
    (("rect", 2.0, 0.4, 3.8, 1.2), "bank"),
    (("rect", -14.6, 1.8, -11.4, 3.6), "kartentisch"),     # Feldstation
    (("circle", 0.0, -6.8, 0.55), "lagerfeuer"),           # vor der Messe; nur die Feuerstelle sperrt, der Weg bleibt beidseits frei
    (("rect", -2.6, -8.6, -0.9, -8.0), "baumstamm"),           # Sitzstamm westlich, Weg nach Sueden bleibt frei (User 23.09.)
    (("rect", 11.0, -1.0, 16.0, -0.4), "baumstamm"),       # Hochsitz: Stamm-Sitz
]

# Wasser (sperrt Weg, nicht Sicht): Bach am Bachsteg und Teich am Bootshaus
WATER = [("rect", 28.4, -22.0, 32.0, -8.6)]   # Bach am Ostrand
# Bootssteg (begehbar, ragt ins Wasser; der Raum heisst danach)
DOCK = ("rect", 28.3, -15.2, 31.4, -13.6)
