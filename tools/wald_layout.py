# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_layout.py - Forststation Nadelkamm, Grundriss v7 (Kartenverkleinerung 24.09.).
#
# Leitidee (aus den Fehlern von v4 gelernt): Polus statt Wildnis. Die Station besteht aus
# BEGEHBAREN Holzgebaeuden mit Tueren (die 13 Skeld-Tueren sitzen in Gebaeuden, wie auf Polus)
# und offenen Lichtungen, verbunden durch kurze Waldwege. Der dichte Wald ist die Wand.
# Alle Zahlen in Weltmetern (Norden = +y), Zentrum = Messe.
#
# v7 (docs/KARTEN_VERKLEINERUNG.md Abschnitt 4): 64 x 44 m -> ca. 52 x 34 m. Raster 4 x 3:
#     [Lookout Rock]-[Sawmill]-[Radio Mast]-[Water Works]
#     [Field Lab]-[Field Station]-[Mess Hall]-[Hunting Stand]
#     [Ranger Office]-[Generator]-[Storehouse]-[Boathouse + Steg]
#   - Hoefe 1,5 m (statt 2,2-3; 1 m war nach Spielerabstand zu schmal), Wege meist unter 4 m, 2,8 m breit
#   - Pump Station geht in "Water Works" auf (Teilflaechen LifeSupp + Reactor einer Lichtung)
#   - Creek Dock wird der Vorplatz des Bootshauses (Teilflaeche Shields, Name "Boathouse")
#   - Aussichtsturm, Hochsitz, Funkmast, Wassertank, Aggregat sperren nur noch den Weg (GLASS);
#     Einzelbaeume sperren den Weg mit 0,8 m, die Sicht nur am Stamm (OPAQUE-Kern 0,3 m, ohne Sprite)
#
# 14 Bereiche = 14 Skeld-Systeme. Gebaeude mit Tueren sind genau die sieben Skeld-Tuergruppen
# (Cafeteria 3, Storage 3, UpperEngine 2, LowerEngine 2, Security 1, MedBay 1, Electrical 1);
# senkrechte Tueren (in O/W-Waenden) 7, waagerechte (N/S) 6 - wie die Skeld-Tuerbestaende.

BOUNDS = (-30.0, -16.5, 25.5, 20.5)
WALL = 0.5            # Wandstaerke der Holzgebaeude
PATH_W = 2.8          # Wegbreite
DOOR_W = 2.5          # Tuerbreite

# ------------------------------------------------------------------ Gebaeude
# key, Anzeigename, Skeld-System, Innenraum [x0,y0,x1,y1], Tueren [(Seite, von, bis, Art)]
#   Seite: "N","S","E","W"; von/bis entlang der Wand; Art "door" (Skeld-Tuer) oder "gap" (offen)
BUILDINGS = [
    ("messe", "Mess Hall", "Cafeteria", (-5, -2, 5, 6),
     [("W", 1.0, 3.5, "door"), ("E", 1.0, 3.5, "door"), ("S", -1.25, 1.25, "door"), ("N", -1.25, 1.25, "gap")]),
    ("feldstation", "Field Station", "Admin", (-15.5, -2, -8.5, 5),
     [("W", 0.25, 2.75, "gap"), ("E", 0.75, 3.25, "gap"), ("N", -11.0, -8.75, "gap"), ("S", -13.25, -10.75, "gap")]),
    ("labor", "Field Lab", "MedBay", (-26.5, -3, -18.5, 5),
     [("E", 0.25, 2.75, "door")]),
    ("saegewerk", "Sawmill", "UpperEngine", (-14.5, 10, -5, 17),
     [("S", -11.0, -8.5, "door"), ("E", 12.0, 14.5, "door")]),
    ("lager", "Storehouse", "Storage", (-5, -13, 5, -5.5),
     [("N", -1.25, 1.25, "door"), ("W", -10.0, -7.5, "door"), ("E", -10.0, -7.5, "door")]),
    ("bootshaus", "Boathouse", "LowerEngine", (8, -13, 15.5, -6),
     [("N", 10.5, 13.0, "door"), ("W", -11.0, -8.5, "door")]),
    ("wachstube", "Ranger Office", "Security", (-26, -12.5, -19, -5.5),
     [("N", -24.0, -21.5, "door")]),
    ("generator", "Generator Shed", "Electrical", (-15.5, -12, -8.5, -6),
     [("N", -13.25, -10.75, "door")]),
]

# ------------------------------------------------------------------ Lichtungen (offen)
# key, Anzeigename, Skeld-System, Flaeche [x0,y0,x1,y1] (abgerundet, Rundung CORNER)
CORNER = 2.0
CLEARINGS = [
    ("aussicht", "Lookout Rock", "Nav", (-27, 9, -18, 17)),
    ("funkmast", "Radio Mast", "Comms", (-2, 9, 6.5, 17)),
    ("wassertank", "Water Works", "LifeSupp", (9, 9, 14.5, 17)),
    ("pumpe", "Water Works", "Reactor", (14.5, 9, 20, 17)),
    ("hochsitz", "Hunting Stand", "Weapons", (8, -2.5, 16, 6.5)),
    ("bachsteg", "Boathouse", "Shields", (16.5, -13, 23, -5.5)),
]
# Lichtungen einer Gruppe bilden EINE gerundete Flaeche (Huelle ihrer Rechtecke); jede Teilflaeche
# ist dann diese Flaeche geschnitten mit ihrem eigenen Rechteck (je Skeld-System ein Raum).
CLEARING_GROUPS = {"wasserwerk": ("wassertank", "pumpe")}
# Hof um die Gebaeude: so weit wird Waldboden um jedes Gebaeude freigelassen
YARD = {"messe": 1.5, "feldstation": 1.5, "labor": 1.5, "saegewerk": 1.5, "lager": 1.5,
        "bootshaus": 1.5, "wachstube": 1.5, "generator": 1.5}   # 1 m blieb nach 0,3 m Spielerabstand zu schmal

# ------------------------------------------------------------------ Wege (Mittellinien)
PATHS = [
    [(5.5, 2.25), (8, 2.25)],                  # Messe O -> Hochsitz
    [(0, -2.5), (0, -5)],                      # Messe S -> Lager N
    [(0, 6.5), (0, 9)],                        # Messe N -> Funkmast
    [(-5.5, 2.25), (-8, 2.0)],                 # Messe W -> Feldstation O
    [(-16, 1.5), (-18, 1.5)],                  # Feldstation W -> Labor O
    [(-9.75, 5.5), (-9.75, 9.5)],              # Feldstation N -> Saegewerk S
    [(-12, -2.5), (-12, -5.5)],                # Feldstation S -> Generator N
    # Feldstation/Labor -> Spalt unter dem Labor -> Wachstube N-Tuer (der 1-m-Hof allein war nach Abzug
    # des Spielerabstands nur 0,25 m breit: Messung 24.09., Ranger Office 54 m statt ~25 m ab Spawn)
    [(-17.1, 0.5), (-17.1, -4.25), (-22.75, -4.25)],
    [(-22.5, 5.5), (-22.5, 9)],                # Labor -> Aussicht
    [(-18, 12), (-15, 12)],                    # Aussicht -> Saegewerk-Hof
    [(-4.5, 13.25), (-2, 13.25)],              # Saegewerk O -> Funkmast
    [(6.5, 13), (9, 13)],                      # Funkmast -> Wasserwerk
    [(12, 6.5), (12, 9)],                      # Hochsitz -> Wasserwerk
    [(-18.5, -9), (-16, -9)],                  # Wachstube-Hof -> Generator-Hof
    [(-8, -8.75), (-5.5, -8.75)],              # Generator-Hof -> Lager W
    [(5.5, -8.75), (7.5, -9.75)],              # Lager O -> Bootshaus W
    [(11.75, -2.5), (11.75, -5.5)],            # Hochsitz -> Bootshaus N
]

# ------------------------------------------------------------------ Spielpunkte
SPAWN = (0.0, 2.0)
SPAWN_RADIUS = 2.4
EMERGENCY = (0.0, 2.5)          # Messe: Glocke vor dem langen Tisch (Pfosten frei vom Tisch)
SURVEILLANCE = (-25.0, -9.0)    # Wachstube, vor der Monitorwand
ADMIN_TABLE = (-12.0, 1.3)      # Feldstation: Suedkante des Kartentischs
FREEPLAY = (3.8, -1.2)

# Sabotage-Stationen: Waldbrand (Reaktor) Wasserwerk NO + Aussicht NW, Trinkwasser (O2) Labor W + Steg SO
FIXED = {
    "Reactor/UpperHandConsole/0": (17.0, 15.9),     # A1 Wasserwerk (zwischen Tank und Pumpenhaus)
    "Reactor/LowerHandConsole/1": (-24.9, 16.3),    # A2 Aussicht (NW, hinter dem Turm; A1 im Wasserwerk NO)
    "LifeSupp/NoOxyConsole/0": (-25.8, 2.4),        # B1 Labor
    "Admin/NoOxyConsole/1": (18.0, -12.3),          # B2 Bootssteg
    "Electrical/SwitchConsole/0": (-15.1, -8.2),    # Sicherungen im Generatorhaus
    "Comms/FixCommsConsole/0": (2.4, 14.6),         # Funkgeraet neben dem Mast
    "MedBay/MedScanner/0": (-22.5, -1.2),           # Scanner im Labor
}

# Vents: Skeld-Id -> Platz, drei Netze (keins verbindet A1/A2 oder B1/B2)
VENTS = {
    11: (-19.8, 10.6), 3: (-9.3, -6.9), 5: (-19.8, -6.3),         # West: Aussicht, Generator, Wachstube
    7: (-5.8, 16.2), 6: (4.3, -6.3), 0: (-9.3, -1.3),             # Mitte: Saegewerk, Lager, Feldstation
    10: (5.0, 10.4), 4: (18.7, 10.5), 9: (14.7, -12.2),           # Ost: Funkmast, Wasserwerk, Bootshaus
}
VENT_NETS = [[11, 3, 5], [7, 6, 0], [10, 4, 9]]

# Kameras (4): Messe-Vorplatz, Hochsitz, Wasserwerk, Lager-Hof
CAMERAS = [(4.0, -3.0), (15.2, 5.5), (19.2, 16.2), (-5.9, -4.8)]

# ------------------------------------------------------------------ Hindernisse
# ("rect", x0, y0, x1, y1) | ("circle", cx, cy, r) | ("ellipse", cx, cy, rx, ry)
# OPAQUE: Weg + Sicht, GLASS: nur Weg. KINDS = Objektart fuer das Zeichnen; None = kein Sprite
# (Sichtkern in einer GLASS-Huelle, die das Sprite traegt).
OPAQUE = [
    (("rect", -15.4, 4.2, -13.4, 4.9), "regal"),           # Feldstation: Regal
    (("rect", -25.9, -2.6, -25.0, 1.0), "schrank"),        # Labor
    (("rect", -4.6, -12.4, -1.4, -11.2), "kisten"),        # Lager: gestapelte Kistenregale
    (("rect", 1.4, -12.4, 4.6, -11.2), "kisten"),
    (("rect", -1.2, -10.2, 1.2, -8.8), "kisten"),
    (("rect", -26.0, -11.4, -25.2, -7.4), "monitore"),     # Wachstube (Westwand)
    (("circle", -21.0, 14.6, 1.6), "fels"),                # Aussicht: Findling (NO)
    (("rect", 16.0, 11.8, 19.3, 14.8), "pumpenhaus"),      # Wasserwerk: Pumpe
    # Einzelbaeume: Sicht nur am Stamm (die Krone traegt der GLASS-Eintrag)
    (("circle", -0.3, 11.4, 0.3), None),
    (("circle", 18.6, -7.2, 0.3), None),
]
GLASS = [
    # niedrig: sperrt den Weg, nicht die Sicht (User 23.09.: ueber den langen Tisch muss man schauen koennen)
    (("rect", -3.5, 3.6, 3.5, 4.4), "tisch_lang"),         # Messe: langer Tisch
    (("rect", -4.4, -1.4, -2.6, -0.3), "herd"),            # Messe: Herd
    (("rect", -25.9, 3.8, -24.1, 4.9), "laborbank"),       # Labor
    (("rect", -11.5, 13.0, -5.5, 14.6), "saegetisch"),     # Saegewerk
    (("rect", -14.0, 10.6, -11.6, 12.0), "holzstapel"),
    (("rect", 9.5, -12.4, 13.5, -10.2), "boot"),           # Bootshaus
    (("rect", -3.8, 0.4, -2.0, 1.2), "bank"),              # Messe: Baenke
    (("rect", 2.0, 0.4, 3.8, 1.2), "bank"),
    (("rect", -13.6, 1.8, -10.4, 3.6), "kartentisch"),     # Feldstation
    (("rect", 10.0, -1.0, 15.0, -0.4), "baumstamm"),       # Hochsitz: Stamm-Sitz
    # Aussicht: Lagerfeuer (Kollider 0,55, gezeichnet 1,2) mit Sitzstamm
    (("circle", -24.6, 11.2, 0.55), "lagerfeuer"),
    (("rect", -26.9, 10.4, -25.3, 11.0), "baumstamm"),
    # auf Stelzen / Gitter / erhoeht: Weg gesperrt, Sicht frei (Plan Abschnitt 4, Durchsicht)
    (("rect", -26.4, 13.8, -23.4, 15.4), "turm"),          # Aussichtsturm-Fuss (NW)
    (("rect", -14.9, -11.4, -11.9, -9.8), "aggregat"),     # Generator: Stromaggregat (Brusthoehe)
    (("circle", 4.3, 14.3, 0.9), "mast"),                  # Funkmast (Gitter)
    (("circle", 12.0, 13.2, 2.2), "tank"),                 # Wassertank auf Beinen
    (("rect", 12.5, 2.6, 14.1, 4.2), "hochsitz"),          # Hochsitz auf Stelzen
    # Einzelbaeume: die Krone traegt das Sprite, der Kollider sperrt den Weg um den Stamm
    (("circle", -0.3, 11.4, 0.8), "baum"),
    (("circle", 18.6, -7.2, 0.8), "baum"),
]

# Wasser (sperrt Weg, nicht Sicht): Bach am Ostrand des Stegs
WATER = [("rect", 20.3, -16.0, 25.5, -3.8)]
# Bootssteg (begehbar, ragt ins Wasser)
DOCK = ("rect", 20.2, -10.2, 23.3, -8.6)
