# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# hive_layout.py - Amberhive: Grundriss (Quelle fuer gen_hive.py). Konzept: KONZEPT.md.
#
# Weltmeter, x nach Osten, y nach Norden. Das Erdgeschoss liegt um (0/0), die Krone (zweite Etage, nur mit der
# Host-Option "2 Floors") noerdlich davon als eigene Flaeche; verbunden nur ueber Treppen (AtlasStairs) und die Rutsche.
#
# Raeume sind Waben (Sechsecke, flache Ober- und Unterkante) oder gefaste Rechtecke. Alles, was nicht Raum, Gang oder
# Durchgang ist, ist Wachs (Wand). Tueren sitzen immer in achsparallelen Durchgaengen (Atlas kennt nur senkrechte und
# waagerechte Tueren).

import math

KEY = "amberhive"
DISPLAY_NAME = "Amberhive"
ICON_TEXT = "AH"

GROUND_BOUNDS = (-21.0, -17.5, 21.0, 15.5)
CROWN_BOUNDS = (-16.0, 18.5, 16.0, 28.5)


def hexagon(cx, cy, r, stretch=1.0, cut=0.0):
    """Wabe mit flacher Ober-/Unterkante. stretch > 1 zieht sie in x, cut kappt die Ost-/West-Spitzen (fuer Tueren)."""
    h = r * math.sqrt(3) / 2
    w = r * stretch
    pts = [(cx + w, cy), (cx + w - r / 2, cy + h), (cx - w + r / 2, cy + h), (cx - w, cy), (cx - w + r / 2, cy - h),
           (cx + w - r / 2, cy - h)]
    if cut > 0:
        k = cut
        pts = [(cx + w - k, cy - k * math.sqrt(3)), (cx + w - k, cy + k * math.sqrt(3)), (cx + w - r / 2, cy + h),
               (cx - w + r / 2, cy + h), (cx - w + k, cy + k * math.sqrt(3)), (cx - w + k, cy - k * math.sqrt(3)),
               (cx - w + r / 2, cy - h), (cx + w - r / 2, cy - h)]
    return [(round(x, 3), round(y, 3)) for x, y in pts]


def roundroom(cx, cy, r, n=20):
    return [(round(cx + r * math.cos(2 * math.pi * (i + 0.5) / n), 3), round(cy + r * math.sin(2 * math.pi * (i + 0.5) / n), 3))
            for i in range(n)]


def octagon(cx, cy, w, h, c=1.0):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


# ------------------------------------------------------------------ Erdgeschoss
# Raster: Mittelachse x = 0 (Mead Hall, Brunnen, Thronsaal), innere Waben x = +-9 (y = +-6,5), aeussere Raeume x = +-17,2,
# Suedreihe y = -14,2. Zwischen zwei Raeumen bleibt mindestens 1 m Wachs; jede Verbindung ist genau ein Durchgang.
# (key, Name, System, Polygon)
ROOMS = [
    ("mead", "Mead Hall", "Cafeteria", hexagon(0.0, 10.0, 5.6, 1.12, cut=0.9)),
    ("queen", "Queen's Chamber", "Reactor", hexagon(0.0, -10.5, 5.6, 1.12, cut=0.9)),
    ("cellar", "Jar Cellar", "Storage", hexagon(-9.0, 6.5, 3.9, 1.05, cut=0.7)),
    ("keeper", "Keeper's Office", "Admin", hexagon(9.0, 6.5, 3.9, 1.05, cut=0.7)),
    ("bellows", "Bellows", "LifeSupp", hexagon(-9.0, -6.5, 3.9, 1.05, cut=0.7)),
    ("nursery", "Brood Nursery", "MedBay", hexagon(9.0, -6.5, 3.9, 1.05, cut=0.7)),
    ("lamp", "Lamphouse", "Electrical", octagon(-17.2, 0.0, 6.6, 6.2, 1.4)),
    ("foundry", "Wax Foundry", "Shields", octagon(17.2, 0.0, 6.6, 6.2, 1.4)),
    ("guard", "Guard Comb", "Security", octagon(-17.2, 10.0, 6.0, 5.6, 1.2)),
    ("waggle", "Waggle Studio", "Comms", octagon(17.2, 10.0, 6.0, 5.6, 1.2)),
    ("wpress", "West Press", "LowerEngine", octagon(-17.2, -11.0, 6.0, 6.6, 1.2)),
    ("epress", "East Press", "UpperEngine", octagon(17.2, -11.0, 6.0, 6.6, 1.2)),
    ("wasp", "Wasp Watch", "Weapons", octagon(-9.4, -14.4, 7.6, 4.0, 1.0)),     # laenglich: Schiessstand
    ("sun", "Sun Compass", "Nav", roundroom(9.2, -14.0, 3.1)),                 # rund: Sonnenuhr in der Mitte
]

# Honigbrunnen: Wabe um den Honigsee (Flur, kein Raum). Der See ist begehbar angelegt; die Welt-Mechanik sperrt ihn bis auf
# die Drehbruecke (Unikat 1).
WELL = hexagon(0.0, 0.0, 5.4, 1.0)
PIT = (0.0, 0.0, 2.55)                 # Kreis: Mitte, Radius
BRIDGE_W = 1.7                         # Breite der Bruecke; Laenge = Seedurchmesser + Ueberstand

CORRIDORS = [
    (2.6, [(-13.9, 0.0), (-4.4, 0.0)]),        # West: Lamphouse - Brunnen
    (2.6, [(4.4, 0.0), (13.9, 0.0)]),          # Ost: Brunnen - Wachsgiesserei
]
# (x0, y0, x1, y1, Art, System der Tuer oder None). Hoeher als breit = Nord-Sued-Durchgang (waagerechte Tuer).
PASSAGES = [
    (-1.5, 4.4, 1.5, 5.4, "door", "Cafeteria"),             # Brunnen - Mead Hall
    (-1.5, -5.9, 1.5, -4.4, "gap", None),                   # Brunnen - Thronsaal
    (-5.8, 5.7, -4.1, 7.3, "door", "Storage"),              # Jar Cellar - Mead Hall
    (4.1, 5.7, 5.8, 7.3, "door", "Cafeteria"),              # Keeper - Mead Hall
    (-10.1, 1.0, -7.9, 3.4, "door", "Storage"),             # Jar Cellar - Westgang
    (7.9, 1.0, 10.1, 3.4, "gap", None),                     # Keeper - Ostgang
    (-10.1, -3.4, -7.9, -1.0, "gap", None),                 # Bellows - Westgang
    (7.9, -3.4, 10.1, -1.0, "door", "MedBay"),              # Nursery - Ostgang
    (-5.8, -7.3, -3.8, -5.7, "gap", None),                  # Bellows - Thronsaal
    (3.8, -7.3, 5.8, -5.7, "door", "MedBay"),               # Nursery - Thronsaal
    (-19.0, 3.0, -17.2, 7.3, "door", "Security"),           # Guard - Lamphouse (West, Nordwand der Lamphouse bleibt frei)
    (17.2, 3.0, 19.0, 7.3, "gap", None),                    # Waggle - Foundry
    (-14.4, 7.9, -11.7, 9.5, "door", "Security"),           # Guard - Jar Cellar
    (-18.2, -7.8, -16.2, -3.0, "door", "LowerEngine"),      # West Press - Lamphouse
    (16.2, -7.8, 18.2, -3.0, "door", "UpperEngine"),        # East Press - Foundry
    (-14.8, -13.95, -12.5, -12.65, "door", "LowerEngine"),    # Anschluss in beide gefasten Raeume, gleiche Tuerbreite
    (11.9, -13.4, 14.4, -12.0, "door", "UpperEngine"),      # East Press - Sun Compass
    (-10.1, -12.6, -7.9, -9.7, "gap", None),                # Wasp Watch - Bellows
    (8.1, -11.2, 10.3, -9.7, "gap", None),                  # Sun Compass - Nursery
    (-5.8, -15.2, -3.4, -13.8, "gap", None),                # Wasp Watch - Thronsaal
    (-14.0, -1.3, -13.8, 1.3, "door", "Electrical", "V"),   # Lamphouse - Westgang (an der Raumkante)
    (11.7, 7.9, 15.0, 9.5, "gap", None),                    # Anschluss ueber die gefaste Waggle-Ecke hinaus
    (3.0, -15.2, 6.8, -13.2, "gap", None),                  # Breiter Anschluss unterhalb der Kuehlwaben
]

# ------------------------------------------------------------------ Krone (zweite Etage)
CROWN_ROOMS = [
    # eigene Systeme der Airship, damit Taskliste und Raumanzeige die Krone nennen (Atlas benennt je System)
    ("sundeck", "Sun Deck", "ViewingDeck", hexagon(-10.5, 23.5, 4.2, 1.0, cut=0.7)),
    ("archive", "Royal Archive", "Records", hexagon(0.0, 23.5, 4.8, 1.08, cut=0.8)),
    ("dock", "Drone Dock", "CargoBay", hexagon(10.5, 23.5, 4.2, 1.0, cut=0.7)),
]
CROWN_CORRIDORS = [
    (2.4, [(-7.3, 23.5), (-4.1, 23.5)]),
    (2.4, [(4.1, 23.5), (7.3, 23.5)]),
]
CROWN_PASSAGES = []

# Treppen: (Absatz unten, Absatz oben, Knopf unten, Knopf oben)
STAIRS = [
    ((0.0, 13.7), (0.0, 20.2), "UP", "DOWN"),            # Mead Hall Nordwand - Royal Archive Suedwand
    ((-15.6, 11.7), (-10.5, 20.6), "UP", "DOWN"),        # Guard Comb - Sun Deck
    ((15.6, 11.7), (10.5, 20.6), "UP", "DOWN"),          # Waggle Studio - Drone Dock
]
CHUTE = ((3.0, 26.0), (3.1, -3.25))                      # Beide Landepunkte mit Platz fuer den Spielerkreis
CHUTE_EXIT = (2.7, -2.7)                                  # wohin man aus dem Rutschenende hinausrutscht

# ------------------------------------------------------------------ Systemkonsolen, Spawn, Vents, Kameras
SPAWN = (0.0, 9.0)
SPAWN_RADIUS = 1.6
EMERGENCY = (0.0, 11.2)                  # Koeniginnenglocke mitten in der Mead Hall
SURVEILLANCE = (-18.6, 11.6)
ADMIN_TABLE = (9.0, 7.0)
FREEPLAY = (-3.4, 12.8)

FIXED = {
    "Reactor/UpperHandConsole/0": (-4.4, -10.0),         # Hive Fever: Kuehlwabe West
    "Reactor/LowerHandConsole/1": (4.4, -10.0),          # Hive Fever: Kuehlwabe Ost
    "LifeSupp/NoOxyConsole/0": (-11.7, -6.5),            # Stale Air: Ventil an der Westspitze
    "Admin/NoOxyConsole/1": (11.4, 8.8),                 # Stale Air: Lueftungsklappe im Buero
    "Electrical/SwitchConsole/0": (-15.9, 2.4),          # Glow Fade
    "Comms/FixCommsConsole/0": (18.4, 12.3),             # Dance Jam
    "MedBay/MedScanner/0": (8.6, -7.0),
}

VENTS = {
    0: (-19.0, 8.6), 1: (-18.8, -1.6), 2: (-19.0, -12.8),           # West
    3: (19.0, 8.6), 4: (18.8, -1.6), 5: (19.0, -12.8),              # Ost
    6: (-4.45, 7.7), 7: (-3.5, -2.15), 8: (-1.6, -13.9),              # Vent 6 an der bewährten V4-Position
    9: (-10.6, 8.2), 10: (10.5, -8.25),
}
VENT_NETS = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10]]
VENT_BRIDGES = []
CAMERAS = [(0.0, 3.6), (-9.0, 0.9), (9.0, 0.9), (0.0, -14.6)]
CAMERA_VIEWS = {0: (0.0, 2.0), 1: (-9.0, 0.0), 2: (9.0, 0.0), 3: (0.0, -12.5)}
# Mit Krone wird das diagonale Zweiernetz nach oben verlegt. Keine neuen Vent-IDs erfinden:
# Atlas verschiebt die vorhandenen elf Skeld-Vents, statt weitere zu erzeugen.
CROWN_VENTS = {9: (-11.5, 25.0), 10: (11.5, 25.0)}
VIEW_SPOTS = [SPAWN, (0.0, 0.0), (-17.2, 0.0), (17.2, 0.0), (0.0, -10.5)]

SKELD_CONSOLES = {
    "Cafeteria": ["Cafeteria/DataConsole/2", "Cafeteria/FixWiringConsole/4", "Cafeteria/GarbageConsole/2"],
    "Admin": ["Admin/SwipeCardConsole/0", "Admin/UploadDataConsole/0", "Admin/FixWiringConsole/2"],
    "Security": ["Security/DivertPowerConsole/1", "Security/FixWiringConsole/5"],
    "Electrical": ["Electrical/CalibrateConsole/0", "Electrical/DivertPowerConsole/0",
                   "Electrical/UploadDataConsole/0", "Electrical/FixWiringConsole/0"],
    "Reactor": ["Reactor/StartReactorConsole/2", "Reactor/UnlockManifoldsConsole/2"],
    "Nav": ["Nav/ChartCourseConsole/0", "Nav/StabilizeSteeringConsole/0", "Nav/UploadDataConsole/0",
            "Nav/DivertPowerConsole/1", "Nav/FixWiringConsole/3"],
    "Shields": ["Shields/ShieldConsole/0", "Shields/DivertPowerConsole/1"],
    "Comms": ["Comms/UploadDataConsole/1", "Comms/DivertPowerConsole/1"],
    "UpperEngine": ["UpperEngine/AlignEngineConsole/0", "UpperEngine/FuelEngineConsole/0",
                    "UpperEngine/DivertPowerConsole/1"],
    "LowerEngine": ["LowerEngine/AlignEngineConsole/1", "LowerEngine/FuelEngineConsole/0",
                    "LowerEngine/DivertPowerConsole/1"],
    "MedBay": ["MedBay/MedBayConsole/0"],
    "Storage": ["Storage/gasCanConsole/0", "Storage/FixWiringConsole/1", "Storage/AirlockConsole/0"],
    "LifeSupp": ["LifeSupp/CleanFilterConsole/0", "LifeSupp/GarbageConsole/0", "LifeSupp/DivertPowerConsole/1"],
}
# Mit zwei Etagen: eigene Aufgaben der Krone aus der Airship (AtlasForeignTasks, Schiff 4). Raum-Schluessel -> (TaskType, Konsole)
CROWN_TASKS = {
    "archive": [("UnlockSafe", "Records/UnlockSafe/0"), ("PolishRuby", "Records/PolishRuby/0")],
    "sundeck": [("FixShower", "ViewingDeck/FixShower/0"), ("CleanToilet", "ViewingDeck/CleanToilet/0")],
    "dock": [("PutAwayPistols", "CargoBay/PutAwayPistols/0"), ("MakeBurger", "CargoBay/MakeBurger/0")],
}
CROWN_CONSOLES = {}
SKELD_CONSOLES["Weapons"] = ["Weapons/WeaponConsole/0", "Weapons/UploadDataConsole/1", "Weapons/DivertPowerConsole/1"]

TASK_NAMES = {
    "FixWiring": "Rethread the Comb Wires", "SwipeCard": "Stamp the Keeper's Log", "CalibrateDistributor": "Tune the Glow Jars",
    "ChartCourse": "Plot the Forage Route", "CleanO2Filter": "Brush the Bellows Filter", "DivertPower": "Route the Nectar Flow",
    "PrimeShields": "Seal the Wax Plates", "StabilizeSteering": "Align the Sun Compass", "UnlockManifolds": "Open the Royal Cells",
    "UploadData": "Copy the Dance Notes", "AlignEngineOutput": "Set the Press Screw", "ClearAsteroids": "Shoo the Wasps",
    "EmptyGarbage": "Empty the Wax Scraps", "EmptyChute": "Clear the Wax Chute", "FuelEngines": "Fill the Nectar Tanks", "InspectSample": "Taste the Honey",
    "StartReactor": "Warm the Queen's Comb", "SubmitScan": "Visit the Nursery",
    "ResetReactor": "Hive Fever", "RestoreOxy": "Stale Air", "FixLights": "Glow Fade", "FixComms": "Dance Jam",
    # Krone (Airship-Aufgaben)
    "UnlockSafe": "Open the Royal Vault", "PolishRuby": "Polish the Royal Amber", "FixShower": "Water the Sunflowers",
    "CleanToilet": "Refill the Dew Basin", "PutAwayPistols": "Rack the Drone Stingers", "MakeBurger": "Pack the Pollen Lunch",
}


# ------------------------------------------------------------------ Einrichtung
# (Art, Form, Modus): Form wie im Generator ("rect", x0, y0, x1, y1) | ("circle", x, y, r) | ("ellipse", x, y, rx, ry);
# Modus "opaque" (wirft Schatten), "glass" (sperrt, kein Schatten), "deco" (nur Bild). Die Form ist zugleich die Grundflaeche,
# auf der das Bild steht (Standlinie = Unterkante). "floors": nur in dieser Fassung (1 oder 2), sonst in beiden.
PROPS = [
    # Mead Hall
    ("mead_table", ("rect", -4.0, 9.2, -2.4, 10.1), "glass"),
    ("mead_table", ("rect", 2.4, 9.2, 4.0, 10.1), "glass"),
    ("mead_barrel", ("circle", -2.0, 14.15, 0.45), "opaque"),
    ("mead_barrel", ("circle", 2.0, 14.15, 0.45), "opaque"),
    ("hive_banner", ("rect", -0.9, 14.45, 0.9, 14.7), "deco", 1),
    # Koeniginnenkammer
    ("queen_throne", ("rect", -1.2, -13.3, 1.2, -12.2), "opaque"),
    ("royal_cells", ("rect", -3.8, -14.1, -2.4, -13.3), "glass"),
    ("royal_cells", ("rect", 2.4, -14.1, 3.8, -13.3), "glass"),
    # Jar Cellar
    ("jar_shelf", ("rect", -10.6, 9.35, -7.4, 9.85), "opaque"),
    ("honey_barrels", ("rect", -12.0, 5.6, -11.0, 7.3), "glass"),
    ("crate_stack", ("rect", -8.0, 3.3, -6.8, 4.1), "glass"),
    # Keeper's Office
    ("bookshelf", ("rect", 8.0, 9.35, 10.4, 9.85), "opaque"),
    ("smoker_stand", ("circle", 11.9, 5.4, 0.3), "glass"),
    # Bellows
    ("bellows_big", ("rect", -10.1, -7.4, -7.9, -6.4), "opaque"),
    # Brood Nursery
    ("brood_cradle", ("rect", 11.0, -5.6, 12.0, -4.9), "glass"),
    ("brood_cradle", ("rect", 11.0, -8.3, 12.0, -7.6), "glass"),
    ("nurse_cart", ("rect", 6.4, -9.4, 7.4, -8.9), "glass"),
    # Lamphouse
    ("glow_rack", ("rect", -20.2, -1.4, -19.6, 1.4), "opaque"),
    ("lantern_cart", ("rect", -15.4, -2.4, -14.5, -1.7), "glass"),
    # Wax Foundry
    ("wax_cauldron", ("circle", 17.4, 0.0, 0.75), "glass"),
    ("candle_rack", ("rect", 15.0, 2.55, 16.4, 2.95), "opaque"),
    # Guard Comb
    ("periscope", ("circle", -15.6, 8.2, 0.3), "glass"),
    # Waggle Studio
    ("dance_floor", ("rect", 15.8, 8.6, 18.6, 10.4), "deco"),
    ("flower_pots", ("rect", 19.4, 7.6, 19.9, 8.6), "glass"),
    # Pressen
    ("nectar_press", ("rect", -18.4, -12.2, -16.0, -11.2), "glass"),
    ("nectar_press", ("rect", 16.0, -12.2, 18.4, -11.2), "glass"),
    # Wasp Watch / Sun Compass
    ("target_board", ("rect", -12.6, -12.9, -11.4, -12.6), "opaque"),
    ("pollen_cannon", ("rect", -9.9, -16.2, -8.9, -15.6), "glass"),
    ("sundial", ("circle", 9.2, -14.2, 0.7), "glass"),
    # Krone (nur 2 Etagen)
    ("stair_up", ("rect", -0.8, 13.6, 0.8, 14.85), "deco", 2),
    ("stair_up", ("rect", -16.4, 11.6, -14.8, 12.6), "deco", 2),
    ("stair_up", ("rect", 14.8, 11.6, 16.4, 12.6), "deco", 2),
    ("stair_down", ("rect", -0.8, 19.4, 0.8, 20.0), "deco", 2),
    ("stair_down", ("rect", -11.3, 19.9, -9.7, 20.4), "deco", 2),
    ("stair_down", ("rect", 9.7, 19.9, 11.3, 20.4), "deco", 2),
    ("chute_top", ("circle", 3.0, 26.6, 0.55), "deco", 2),
    ("chute_exit", ("rect", 3.0, -4.4, 4.2, -3.7), "deco", 2),
    ("telescope", ("circle", -10.5, 24.6, 0.45), "glass", 2),
    ("archive_shelf", ("rect", -2.2, 27.2, 2.2, 27.6), "opaque", 2),
    ("drone_perch", ("circle", 10.5, 24.4, 0.6), "glass", 2),
]
