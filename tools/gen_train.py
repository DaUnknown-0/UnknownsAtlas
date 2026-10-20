# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_train.py - Polaris Express (docs/TRAIN_KONZEPT.md), GRAYBOX. Erste Karte im Dateiformat (docs/MAP_FORMAT.md):
# schreibt map.json und das Kartenpaket (Bodenkacheln, Minimap, Treppensymbol) nach assets/train/. Eingebettet ist
# der Ordner als "UnknownsAtlas.Maps.train.*".
#
#   python tools/gen_train.py
#
# Fassung 4 (19.10.): ein Zug als Grundriss von oben, wie jede Atlas-Karte. Die HAUPTEBENE laeuft unten
# durch alle sieben Fahrzeuge auf einer Hoehe (Schlusswagen, Gepaeckraum, Speisewagen, Telegraf/Dynamo,
# Generator/Post, Korridortender, Lok). Drei Doppelstockwagen (Schlaf-, Speise-, Aussichtswagen) haben darueber
# ein OBERDECK (Schlafabteile, Kueche, Aussichtskuppel), je eine Sackgasse mit Treppen an beiden Wagenenden
# (AtlasStairs: Use-Knopf, kurze Blende). Weil eine Karte von oben zwei Ebenen nicht stapeln kann, stehen die
# Oberdecks als eigener Grundriss suedlich der Wagen. Das Kartenfeld "levels" sagt 3D-Werkzeugen, wo jede Flaeche
# wirklich liegt (Hoehe, Versatz des Oberdecks).
#
# Sabotage "Conductor's Round" (User 19.10., wie die O2-Masken in Submerged): alle Lebenden muessen binnen
# TICKET["seconds"] an einer der Fahrkarten-Lochzangen (Zugfuehrerabteil, Postraum) ihren Fahrschein stempeln,
# wer es nicht schafft, fliegt aus dem Zug (AtlasTicket). Kartenknopf auf dem Gleisbett zwischen den Baendern.
#
# Fassung 1 hatte zwei Zuege nebeneinander mit Laufstegen quer ueber das Gleis, Fassung 2 einen Doppelstockzug in
# der Seitenansicht (beides ergab im 3D-Nachbau keinen Sinn, User 18.10.), Fassung 3 das Oberdeck als
# durchgehende Ebene wie beim Superliner (fuer Spieler unintuitiv, User 19.10.: "waere es nicht logischer andersrum?").

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, LineString, box
from shapely.affinity import translate
from shapely.ops import unary_union

import map_labels

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
OUT = PROJECT / "assets" / "train"
PREVIEW = HERE / "_train"
KEY = "train"

FLOOR_PPM = 48                 # Graybox: grob, klein (echte Grafik: train_art liefert ihren eigenen Massstab)
PROP_PPM = 160                 # Objekt- und Konsolen-Atlanten wie bei Museum, Wald und Park
BOUNDS = (-31.0, -9.0, 31.0, 8.6)
BX0, BY0, BX1, BY1 = BOUNDS
WALL = 0.4

# ------------------------------------------------------------------ Zug
# Hauptebene (Band A): Innenraum der Wagen y 1,0..5,5 (4,5 m breit). Oberdecks (Band B): y -7,0..-2,5; im 3D
# liegen sie 8 m weiter noerdlich und 2,3 m hoeher, also genau ueber der Hauptebene der Doppelstockwagen.
AY0, AY1 = 1.0, 5.5
BY0B, BY1B = -7.0, -2.5
DECK_DY = AY0 - BY0B                        # Versatz Band B -> Band A (3D: Oberdeck liegt ueber der Hauptebene)
GANG = (2.35, 4.15)                         # Faltenbalg mittig
GANG_UP = (GANG[0] - DECK_DY, GANG[1] - DECK_DY)
TGANG = (1.1, 2.85)                         # Korridortender: Gang an der Suedseite (20.10.: 1,75 statt 1,55 m)
# Aussen-Laufsteg (User 20.10.: "richtig komplizierte Wege"): Trittbrett an der Suedseite ueber die ganze Zuglaenge,
# Abgaenge in der Mitte jeder Wagenluecke (neben den Faltenbalg-Tueren, damit geschlossene Tueren dicht bleiben) und
# an Schlussplattform und Lok-Umlauf. Ergibt einen zweiten Weg parallel zum Mittelgang und Schleifen.
RB_Y = (-0.55, 0.35)
RB_STEP_W = 0.8
RUNBOARD = []                               # von build() gefuellt: Steg + Abgaenge (fuer die Grafik)
Z_MAIN, Z_UPPER = 1.2, 3.5                  # Fussbodenhoehen ueber Schiene (3D): Hauptebene, Oberdeck

# Fahrzeuge von hinten (Westen) nach vorn (Osten = Fahrtrichtung): key, Name, Innenraum x0, x1, Bauart
CARS = [
    ("caboose", "Caboose", -29.0, -23.0, "single"),
    ("sleeper", "Sleeper Car", -21.4, -13.4, "dd"),
    ("dining", "Dining Car", -11.8, -2.8, "dd"),
    ("dome", "Dome Car", -1.2, 6.8, "dd"),
    ("baggage", "Baggage Car", 8.4, 14.9, "single"),
    ("tender", "Tender", 16.5, 20.1, "single"),
    ("loco", "Locomotive", 21.7, 28.7, "single"),
]
CAR = {c[0]: c for c in CARS}
CAR_KEYS = [c[0] for c in CARS]

# Raeume: key, Name, System, Fahrzeug, Ebene (A Hauptebene unten, B Oberdeck), x0, x1 (None = Wagenende)
ROOMS = [
    ("platform", "Rear Platform", "Shields", "caboose", "A", None, -26.6),
    ("office", "Conductor's Office", "Security", "caboose", "A", -26.6, None),
    ("luggage", "Luggage Room", "Storage", "sleeper", "A", None, None),
    ("sleeper", "Sleeper Car", "MedBay", "sleeper", "B", None, None),
    ("dining", "Dining Car", "Cafeteria", "dining", "A", None, None),
    ("kitchen", "Kitchen", "LifeSupp", "dining", "B", None, None),
    ("telegraph", "Telegraph", "Comms", "dome", "A", None, 2.8),
    ("dynamo", "Dynamo Room", "Electrical", "dome", "A", 2.8, None),
    ("dome", "Vista Dome", "Nav", "dome", "B", None, None),
    ("generator", "Generator", "UpperEngine", "baggage", "A", None, 11.6),
    ("mail", "Mail Room", "Admin", "baggage", "A", 11.6, None),
    ("tender", "Tender", "LowerEngine", "tender", "A", None, None),
    ("cab", "Cab", "Reactor", "loco", "A", None, 24.7),
    ("boards", "Running Board", "Weapons", "loco", "A", 24.7, None),
]
ROOM = {r[0]: r for r in ROOMS}

# Faltenbaelge: westliches Fahrzeug, Oeffnung (y), Tuer (Raum, an dessen Stirnwand sie sitzt) oder None = offen.
# 5 Tueren hier + 2 in Trennwaenden = die 7 senkrechten Skeld-Tueren.
GANGWAYS = [
    ("caboose", GANG, "office"),        # Schlusswagen -> Gepaeckraum (Security)
    ("sleeper", GANG, "dining"),        # Cafeteria
    ("dining", GANG, "dining"),         # Cafeteria
    ("dome", GANG, "generator"),        # UpperEngine
    ("baggage", TGANG, "tender"),       # LowerEngine
    ("tender", TGANG, None),            # durch den Tender in den Fuehrerstand
]
RAMPS = {}                                  # alle Faltenbaelge der Hauptebene liegen auf einer Hoehe (Fassung 4)

# Senkrechte Trennwaende: x, Ebene, Oeffnung (y), Tuer (Raum) oder None
# 20.10.: Engstellen geoeffnet (vorher alle GANG = 1,8 m): Plattform fast ganz offen, die zwei Tueren 2,7 m
VPARTS = [
    (-26.6, "A", (1.5, 5.0), None),      # Buero | hintere Plattform
    (11.6, "A", (1.9, 4.6), "generator"),  # Generator | Postraum
    (2.8, "A", (1.9, 4.6), "dynamo"),    # Telegraf | Dynamo (Hauptebene)
]
# Waagerechte Trennwaende mit Tueren: y, x0, x1, Dicke, [(x0, x1, Tuer-Raum)]. Die 6 waagerechten Skeld-Tueren.
HPARTS = [
    (-4.9, -19.4, -15.4, 0.2, [(-19.1, -17.8, "sleeper"), (-17.0, -15.7, "sleeper")]),    # Schlafabteile (Oberdeck)
    (3.6, -19.4, -15.4, 0.2, [(-19.0, -17.8, "luggage"), (-17.0, -15.8, "luggage")]),     # Gepaeckkaefige (Hauptebene)
    (2.9, 16.5, 20.1, 0.4, [(16.8, 17.9, "tender"), (18.7, 19.8, "tender")]),            # Kohlenbunker
]
# Waende ohne Oeffnung (senkrecht): x, y0, y1
VSOLID = [(-19.4, 3.6, AY1), (-17.4, 3.6, AY1), (-15.4, 3.6, AY1),
          (-19.4, -4.9, BY1B), (-17.4, -4.9, BY1B), (-15.4, -4.9, BY1B)]
BOILER = (24.7, 2.5, 28.0, 4.0)             # Kessel der Lok: Umlauf noerdlich und suedlich davon

# ------------------------------------------------------------------ Treppen (je Doppelstockwagen zwei)
STAIR_LEN, STAIR_DEPTH = 1.6, 1.2


def stairwells():
    """Treppenschaechte an beiden Wagenenden, jeweils an der Nordwand: Fussabdruck auf der Hauptebene (main) und
    auf dem Oberdeck (upper, gleiche Lage im 3D), Absatz davor."""
    out = []
    for key, _n, x0, x1, kind in CARS:
        if kind != "dd":
            continue
        for xa in (x0 + 0.2, x1 - 0.2 - STAIR_LEN):
            xc = xa + STAIR_LEN / 2
            main = box(xa, AY1 - STAIR_DEPTH, xa + STAIR_LEN, AY1)
            upper = box(xa, BY1B - STAIR_DEPTH, xa + STAIR_LEN, BY1B)
            out.append({"car": key, "main": main, "upper": upper,
                        "a": (round(xc, 3), round(AY1 - STAIR_DEPTH - 0.55, 3)),
                        "b": (round(xc, 3), round(BY1B - STAIR_DEPTH - 0.55, 3))})
    return out


# ------------------------------------------------------------------ Spielpunkte
SPAWN = (-7.3, 3.25)
SPAWN_RADIUS = 1.0
DUMMY_RADIUS = (3.4, 1.0)
EMERGENCY = (-7.3, 3.4)
SURVEILLANCE = (-24.6, 5.0)           # Zugfuehrerabteil: Monitore
ADMIN_TABLE = (13.25, 4.8)            # Postraum: Sortiertisch mit Streckenkarte
FREEPLAY = (-4.4, 2.9)                # Speisewagen, frei vor der Bar (Suedwand-Ostende)
FIXED = {
    "Reactor/UpperHandConsole/0": (23.4, 5.1),         # Boiler Overpressure: zwei Ventile am Stehkessel
    "Reactor/LowerHandConsole/1": (23.4, 1.4),
    "LifeSupp/NoOxyConsole/0": (-5.5, -6.6),            # Smoke in the Cars: Kueche + Postraum
    "Admin/NoOxyConsole/1": (14.4, 4.0),
    "Electrical/SwitchConsole/0": (6.3, 1.4),           # Blown Dynamo (Hauptebene)
    "Comms/FixCommsConsole/0": (-0.7, 1.4),             # Telegraph Down (Hauptebene)
    "MedBay/MedScanner/0": (-18.4, -3.5),               # Fahrkartenkontrolle im ersten Abteil (Oberdeck)
    # 20.10.: seit die Engstellen (VPARTS) offen sind, fand place_consoles in Generator und Postraum keinen Wandplatz
    # mehr (Rueckfall Raummitte). Beide stehen jetzt fest in Nischen abseits der Laufwege: Dampfventil in der Ecke
    # zwischen Maschinensatz und Trennwand (noerdlich der Tuer), Klemmenkasten in der Nordost-Ecke ueber der Rauchklappe.
    "UpperEngine/DivertPowerConsole/1": (11.03, 4.95),
    "Admin/FixWiringConsole/2": (14.47, 4.9),
}
# Sabotage "Conductor's Round" (AtlasTicket): Sekunden, Kartenknopf (Gleisbett zwischen den Baendern) und die
# Fahrkarten-Lochzangen: Zugfuehrerabteil (Suedwand, Ostteil) und Postraum (Nordwand, westlich des Sortiertischs).
TICKET = {"seconds": 60, "button": (-7.3, -1.45), "stations": [(-23.6, 1.5), (12.0, 4.9)]}
# Sabotage "Runaway Train" (AtlasRunaway, ersetzt den Reaktor): Regler klemmt, der Zug beschleunigt; zu zweit gleichzeitig
# bremsen: Dampfbremse im Fuehrerstand (Hebel halten) und Handbremse auf der hinteren Plattform (Kurbel).
RUNAWAY = {"seconds": 45, "button": (23.2, -1.45), "brake": (22.3, 4.9), "handbrake": (-27.6, 4.9)}
# Sabotage "Smoke in the Cars" (AtlasSmoke, ersetzt O2): Kohlenfeuer im Tender, Rauch zieht durch den Zug; drei Dachluken
# (Gepaeckraum, Speisewagen, Postraum) aufkurbeln, dann klart es auf.
SMOKE = {"seconds": 60, "button": (18.3, -1.45), "source": (18.2, 4.6),
         "hatches": [(-15.0, 2.2), (-10.6, 3.3), (14.2, 2.6)]}
VENTS = {
    0: (-25.8, 1.5), 1: (-17.4, 1.5), 2: (-7.0, -6.5), 3: (-11.3, 1.5),         # West
    5: (-28.4, 1.5), 6: (-17.4, -6.5), 7: (0.8, 1.5), 8: (6.2, -6.5),           # Mitte
    9: (4.8, 1.5), 10: (9.0, 1.5), 11: (12.1, 1.5), 12: (19.6, 5.0), 13: (28.3, 5.0),    # Ost
}
VENT_NETS = [
    [0, 1, 2, 3],               # Zugfuehrerabteil, Gepaeckraum, Kueche, Speisewagen (Speiseaufzug)
    [5, 6, 7, 8],               # hintere Plattform, Schlafwagen, Telegraf, Aussichtswagen
    [9, 10, 11, 12, 13],        # Dynamo, Generator, Postraum, Tender, Umlauf der Lok
]
VENT_BRIDGES = []
CAMERAS = [(-22.2, 3.25), (-12.6, 3.25), (7.6, 3.25), (21.3, 1.9)]   # Faltenbaelge

# ------------------------------------------------------------------ Hindernisse (Graybox)
# OPAQUE: Weg + Sicht, GLASS: nur Weg
OPAQUE = [
    ("rect", 8.8, 4.2, 10.6, 5.5),           # Generator: Maschinensatz an der Nordwand
    ("rect", 3.4, 1.6, 4.6, 2.8),            # Dynamo (Hauptebene)
]
GLASS = [
    ("rect", -19.2, -3.1, -17.6, -2.5),      # Schlafabteile: Betten (Oberdeck)
    ("rect", -17.2, -3.1, -15.6, -2.5),
    ("rect", -9.6, 4.6, -8.4, 5.5),          # Speisewagen: Tische an den Fenstern
    ("rect", -7.9, 4.6, -6.7, 5.5),
    ("rect", -6.2, 4.6, -5.0, 5.5),
    ("rect", -10.4, 1.0, -9.2, 1.9),
    ("rect", -8.7, 1.0, -7.5, 1.9),
    ("rect", -7.0, 1.0, -5.8, 1.9),
    ("rect", -5.3, 1.0, -4.1, 1.9),
    ("rect", -9.6, -3.3, -5.0, -2.5),        # Kueche: Herdzeile
    ("rect", -10.2, -7.0, -8.0, -6.4),       # Kueche: Anrichte
    ("rect", 0.0, -7.0, 1.4, -6.2),          # Aussichtskuppel: Sessel (Oberdeck)
    ("rect", 2.0, -7.0, 3.4, -6.2),
    ("rect", 4.0, -7.0, 5.4, -6.2),
    ("rect", 1.2, -3.3, 2.4, -2.5),
    ("rect", 3.0, -3.3, 4.2, -2.5),
    ("rect", 17.4, 4.1, 19.0, 5.5),          # Tender: Kohlenhaufen
    ("rect", 12.0, 1.0, 14.6, 1.4),          # Postraum: Sortierfaecher
    ("rect", 12.4, 5.0, 14.1, 5.5),          # Postraum: Sortiertisch mit Streckenkarte an der Nordwand (Admin)
    ("rect", -4.0, 1.0, -3.0, 1.6),          # Speisewagen: Bar am Suedwand-Ostende (Westende = Speiseaufzug, Vent 3)
]
# Fahrkarten-Lochzangen (Sabotage-Stationen) mit Kollision, Breite wie das Objekt (train_props "lochzange"). Steht
# die Zange nahe einer Laengswand, reicht das Rechteck bis an die Wand: ein Spalt von 0,3..0,4 m klemmte Spieler ein
# und drueckte sie im Test durch die Wand nach draussen.
GLASS += [("rect", x - 0.22, AY0 if y - AY0 < 0.8 else y - 0.16, x + 0.22, AY1 if AY1 - y < 0.8 else y + 0.16)
          for x, y in TICKET["stations"]]

# Raumnamen auf dem Boden, wo die Mitte verbaut ist (Abteile, Kaefige, Kessel)
LABEL_AT = {"sleeper": (-17.4, -6.0), "luggage": (-17.4, 2.4), "boards": (26.35, 4.75)}

SKELD_CONSOLES = {
    "Cafeteria": ["Cafeteria/DataConsole/2", "Cafeteria/FixWiringConsole/4", "Cafeteria/GarbageConsole/2"],
    "Admin": ["Admin/SwipeCardConsole/0", "Admin/UploadDataConsole/0", "Admin/FixWiringConsole/2"],
    "Security": ["Security/DivertPowerConsole/1", "Security/FixWiringConsole/5"],
    "Electrical": ["Electrical/CalibrateConsole/0", "Electrical/DivertPowerConsole/0",
                   "Electrical/UploadDataConsole/0", "Electrical/FixWiringConsole/0"],
    "Reactor": ["Reactor/StartReactorConsole/2", "Reactor/UnlockManifoldsConsole/2"],
    "Weapons": ["Weapons/WeaponConsole/0", "Weapons/UploadDataConsole/1", "Weapons/DivertPowerConsole/1"],
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

TASK_NAMES = {
    "FixWiring": "Repair the Lamp Wiring", "SwipeCard": "Stamp the Mail Pass", "CalibrateDistributor": "Balance the Dynamo",
    "ChartCourse": "Plot the Route", "CleanO2Filter": "Clean the Stove Hood", "DivertPower": "Divert Steam Power",
    "PrimeShields": "Set the Signal Lamps", "StabilizeSteering": "Aim the Headlamp", "UnlockManifolds": "Open the Steam Valves",
    "UploadData": "Send a Telegram", "AlignEngineOutput": "Balance the Steam Engine", "ClearAsteroids": "Clear the Line",
    "EmptyGarbage": "Empty the Ash Pan", "FuelEngines": "Shovel Coal", "InspectSample": "Taste Test",
    "StartReactor": "Fire Up the Boiler", "SubmitScan": "Ticket Inspection",
    "ResetReactor": "Boiler Overpressure", "RestoreOxy": "Smoke in the Cars", "FixLights": "Blown Dynamo",
    "FixComms": "Telegraph Down",
}

ROOM_COL = {
    "Security": (120, 104, 92), "MedBay": (150, 160, 170), "Cafeteria": (170, 132, 96), "Nav": (110, 130, 150),
    "Shields": (112, 116, 122), "UpperEngine": (112, 106, 98), "Reactor": (140, 96, 80), "Comms": (126, 116, 140),
    "Admin": (150, 132, 104), "Storage": (132, 112, 88), "LifeSupp": (150, 150, 140), "Electrical": (138, 138, 100),
    "LowerEngine": (92, 88, 86), "Weapons": (108, 104, 104),
}
BODY = {"caboose": (112, 38, 32), "baggage": (44, 66, 54), "tender": (34, 34, 38), "loco": (34, 34, 38)}
BODY_COACH = (30, 40, 78)
LINING = (200, 164, 84)
WALL_COL = (40, 32, 30)
BLOCK_COL = (34, 30, 34)
GLASS_COL = (78, 68, 62)
GANG_COL = (74, 72, 78)
EDGE = (20, 16, 16)


# ------------------------------------------------------------------ Geometrie

def shape(s):
    return box(*s[1:5])


def car_x(key):
    return CAR[key][2], CAR[key][3]


def next_car(key):
    return CAR_KEYS[CAR_KEYS.index(key) + 1]


def deck_y(deck):
    return (AY0, AY1) if deck == "A" else (BY0B, BY1B)


def room_box(r):
    _k, _n, _s, car, deck, a, b = r
    x0, x1 = car_x(car)
    y0, y1 = deck_y(deck)
    return box(x0 if a is None else a, y0, x1 if b is None else b, y1)


def gangway_box(west, yr):
    return box(car_x(west)[1] - 0.01, yr[0], car_x(next_car(west))[0] + 0.01, yr[1])


def build():
    rms = {r[0]: (r[1], r[2], room_box(r)) for r in ROOMS}
    parts, doors, cuts, mouths = [], [], [], []
    for key, _n, x0, x1, kind in CARS:
        parts.append(box(x0, AY0, x1, AY1))
        if kind == "dd":
            parts.append(box(x0, BY0B, x1, BY1B))
    gangs = []
    for west, yr, owner in GANGWAYS:
        g = gangway_box(west, yr)
        gangs.append((west, yr, owner, g))
        parts.append(g)
        x0g, _y0, x1g, _y1 = g.bounds
        mouths += [Point(x0g, sum(yr) / 2), Point(x1g, sum(yr) / 2)]
        if owner:
            east = next_car(west)
            on_west = ROOM[owner][3] == west
            x = car_x(west)[1] + WALL / 2 if on_west else car_x(east)[0] - WALL / 2
            doors.append({"label": f"{owner}-{'E' if on_west else 'W'}", "x": x, "y": sum(yr) / 2,
                          "length": yr[1] - yr[0], "group": ROOM[owner][2], "vertical": True})
    RUNBOARD.clear()
    xs, xe = CARS[0][2], CARS[-1][3]
    RUNBOARD.append(box(xs, RB_Y[0], xe, RB_Y[1]))
    for west, yr, owner, g in gangs:
        x0g, _y0, x1g, _y1 = g.bounds
        mx = (x0g + x1g) / 2
        RUNBOARD.append(box(mx - RB_STEP_W / 2, RB_Y[1] - 0.01, mx + RB_STEP_W / 2, yr[0] + 0.01))
    # Schlussplattform (Westende) und Lok-Umlauf (Ostende): Stufe von der Suedkante hinunter
    RUNBOARD.append(box(xs + 0.5, RB_Y[1] - 0.01, xs + 0.5 + RB_STEP_W, AY0 + 0.01))
    RUNBOARD.append(box(xe - 0.5 - RB_STEP_W, RB_Y[1] - 0.01, xe - 0.5, AY0 + 0.01))
    parts += RUNBOARD
    for x, deck, op, owner in VPARTS:
        y0, y1 = deck_y(deck)
        cuts.append(box(x - 0.15, y0 - 0.01, x + 0.15, y1 + 0.01).difference(box(x - 0.2, op[0], x + 0.2, op[1])))
        mouths.append(Point(x, sum(op) / 2))
        if owner:
            doors.append({"label": f"{owner}-part", "x": x, "y": sum(op) / 2, "length": op[1] - op[0],
                          "group": ROOM[owner][2], "vertical": True})
    for y, x0, x1, th, ops in HPARTS:
        wall = box(x0, y - th / 2, x1, y + th / 2)
        for a, b, owner in ops:
            wall = wall.difference(box(a, y - th, b, y + th))
            mouths.append(Point((a + b) / 2, y))
            doors.append({"label": f"{owner}-{a:.1f}", "x": (a + b) / 2, "y": y, "length": b - a,
                          "group": ROOM[owner][2], "vertical": False})
        cuts.append(wall)
    for x, y0, y1 in VSOLID:
        cuts.append(box(x - 0.1, y0, x + 0.1, y1 + 0.01))
    sw = stairwells()
    for s in sw:
        cuts += [s["main"], s["upper"]]
        mouths += [Point(*s["a"]), Point(*s["b"])]
    cuts.append(box(*BOILER))
    walk = unary_union(parts).difference(unary_union(cuts)).buffer(0)
    return walk, rms, gangs, doors, sw, mouths


def geom_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def rings_of(g):
    out = []
    for p in geom_parts(g):
        out.append(list(p.exterior.coords)[:-1])
        for h in p.interiors:
            out.append(list(h.coords)[:-1])
    return out


# ------------------------------------------------------------------ Konsolen (wie gen_park.place_consoles)

def place_consoles(walk, rms, door_pts, obstacles):
    """Konsolen an Waenden UND an Moebeln (im Speisewagen stehen die Tische an beiden Laengswaenden): Kandidaten
    auf einem 0,2-m-Raster, 0,45..0,8 m von der naechsten Kante, frei von Muendungen, Absaetzen und Spawn."""
    placed = {}
    obst = unary_union(obstacles)
    free = walk.difference(obst.buffer(0.4)).buffer(0)
    edge = unary_union([walk.boundary, obst.boundary])
    taken = [Point(p) for p in list(FIXED.values()) + [EMERGENCY, SURVEILLANCE, ADMIN_TABLE, FREEPLAY] + TICKET["stations"]
             + [RUNAWAY["brake"], RUNAWAY["handbrake"]] + SMOKE["hatches"]]
    taken += [Point(p) for p in VENTS.values()]
    spawn_zone = Point(SPAWN).buffer(SPAWN_RADIUS + 0.6)
    for key, (name, sysname, g) in rms.items():
        keys = [k for k in SKELD_CONSOLES.get(sysname, []) if k not in FIXED]
        area = g.intersection(walk)
        x0, y0, x1, y1 = area.bounds
        cands = []
        yy = y0 + 0.1
        while yy < y1:
            xx = x0 + 0.1
            while xx < x1:
                p = Point(xx, yy)
                if area.contains(p) and free.contains(p) and not spawn_zone.contains(p) and 0.45 <= edge.distance(p) <= 0.8:
                    if min([p.distance(q) for q in door_pts] + [99]) >= 1.2:
                        cands.append(p)
                xx += 0.2
            yy += 0.2
        chosen = []
        for k in keys:
            best, score = None, -1e9
            for need in (1.3, 1.0, 0.8):
                for p in cands:
                    dd = min([p.distance(q) for q in chosen + taken] + [99])
                    if dd < need:
                        continue
                    sc = min(dd, 4.0) - 0.3 * edge.distance(p)
                    if sc > score:
                        best, score = p, sc
                if best is not None:
                    break
            if best is None:
                best = area.representative_point()
                print(f"WARN no spot for {k} in {name}")
            chosen.append(best)
            placed[k] = (round(best.x, 2), round(best.y, 2))
        taken.extend(chosen)
    placed.update(FIXED)
    return placed


# ------------------------------------------------------------------ Bilder

def P(x, y, s):
    return ((x - BX0) * s, (BY1 - y) * s)


def R(x0, y0, x1, y1, s):
    return [(x0 - BX0) * s, (BY1 - y1) * s, (x1 - BX0) * s, (BY1 - y0) * s]


def font(size, bold=True):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def draw_ground(d, s):
    """Verschneite Ebene bei Nacht, Gleisbett unter dem Zug (sichtbar zwischen den Wagen)."""
    rnd = random.Random(5)
    d.rectangle(R(BX0, BY0, BX1, BY1, s), fill=(38, 44, 60))
    for _ in range(2600):
        x, y = rnd.uniform(BX0, BX1), rnd.uniform(BY0, BY1)
        v = rnd.randint(70, 120)
        px, py = P(x, y, s)
        d.point((px, py), fill=(v, v + 6, v + 18))
    # Gleisbett, Schwellen, Schienen
    d.rectangle(R(BX0, AY0 - 1.1, BX1, AY1 + 1.1, s), fill=(56, 54, 58))
    x = BX0
    while x < BX1:
        d.rectangle(R(x, AY0 - 0.7, x + 0.3, AY1 + 0.7, s), fill=(70, 54, 40))
        x += 0.62
    for yy in (2.1, 4.4):
        d.rectangle(R(BX0, yy - 0.05, BX1, yy + 0.05, s), fill=(150, 150, 160))
    # Baeume am Rand (von oben: dunkle Kronen mit Schnee)
    for _ in range(46):
        x = rnd.uniform(BX0, BX1)
        y = rnd.choice([rnd.uniform(7.3, BY1 + 0.5), rnd.uniform(BY0 - 0.5, -8.4)])
        r = rnd.uniform(0.5, 1.0)
        cx, cy = P(x, y, s)
        d.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], fill=(28, 46, 40))
        d.ellipse([cx - r * s * 0.55, cy - r * s * 0.6, cx + r * s * 0.3, cy + r * s * 0.2], fill=(150, 160, 175))


def draw_lower_panel(d, s):
    """Oberdeck als eigener Grundriss: dunkles Feld mit Beschriftung, gestrichelte Linien zeigen, ueber welchem
    Wagen es liegt."""
    dd = [c for c in CARS if c[4] == "dd"]
    x0, x1 = dd[0][2] - 1.0, dd[-1][3] + 1.0
    d.rounded_rectangle(R(x0, BY0B - 1.2, x1, BY1B + 1.2, s), radius=int(0.6 * s), fill=(22, 26, 38), outline=(96, 108, 140), width=3)
    d.text(P(x0 + 0.4, BY1B + 0.9, s), "UPPER DECK  (above the double-deck cars)", font=font(20), fill=(170, 182, 210), anchor="lm")
    for _k, _n, cx0, cx1, _kind in dd:
        for xx in (cx0 - WALL, cx1 + WALL):
            y = AY0 - 0.6
            while y > BY1B + 1.25:
                d.line([P(xx, y, s), P(xx, max(y - 0.35, BY1B + 1.25), s)], fill=(130, 140, 170), width=2)
                y -= 0.6


def draw_stairwell(d, s, poly, down):
    x0, y0, x1, y1 = poly.bounds
    d.rectangle(R(x0, y0, x1, y1, s), fill=(26, 22, 20))
    n = 8
    for i in range(n):
        t = i / n
        c = lerp((150, 120, 84), (60, 48, 36), t if down else 1 - t)
        xa = x0 + (x1 - x0) * i / n
        d.rectangle(R(xa, y0 + 0.05, xa + (x1 - x0) / n - 0.03, y1 - 0.05, s), fill=c)
    # Gelaender an drei Seiten, offen zum Absatz (Sueden)
    d.line([P(x0, y0, s), P(x0, y1, s), P(x1, y1, s), P(x1, y0, s)], fill=LINING, width=4)
    cx, cy = P((x0 + x1) / 2, (y0 + y1) / 2, s)
    d.text((cx, cy), "DOWN" if down else "UP", font=font(14), fill=(255, 255, 255, 200), anchor="mm")


def draw_gangway(d, s, g, ramp):
    x0, y0, x1, y1 = g.bounds
    d.rectangle(R(x0, y0, x1, y1, s), fill=GANG_COL)
    if ramp:
        n = 6
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n
            d.line([P(xx, y0, s), P(xx, y1, s)], fill=(46, 44, 50), width=3)
        d.rectangle(R(x0, y0, x1, y0 + 0.12, s), fill=LINING)
        d.rectangle(R(x0, y1 - 0.12, x1, y1, s), fill=LINING)
    else:
        x = x0 + 0.1
        while x < x1:
            d.line([P(x, y0, s), P(x, y1, s)], fill=(50, 48, 54), width=3)
            x += 0.22


def render_floor(walk, rms, gangs, sw):
    s = FLOOR_PPM
    ww, hh = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGB", (ww, hh), (38, 44, 60))
    d = ImageDraw.Draw(img, "RGBA")
    draw_ground(d, s)
    draw_lower_panel(d, s)
    # Wagenkaesten (Dach weggeschnitten): Hauptebene und Oberdecks
    for key, _n, x0, x1, kind in CARS:
        body = BODY.get(key, BODY_COACH)
        d.rounded_rectangle(R(x0 - WALL, AY0 - WALL, x1 + WALL, AY1 + WALL, s), radius=int(0.3 * s), fill=body)
        d.line([P(x0 - WALL, AY0 - WALL + 0.1, s), P(x1 + WALL, AY0 - WALL + 0.1, s)], fill=LINING, width=2)
        d.line([P(x0 - WALL, AY1 + WALL - 0.1, s), P(x1 + WALL, AY1 + WALL - 0.1, s)], fill=LINING, width=2)
        if kind == "dd":
            d.rounded_rectangle(R(x0 - WALL, BY0B - WALL, x1 + WALL, BY1B + WALL, s), radius=int(0.3 * s), fill=body)
    # Lok: Kessel von oben, Schornstein, Dampfdom, Pufferbohle mit Laterne
    bx0, by0, bx1, by1 = BOILER
    d.rounded_rectangle(R(bx0, by0, bx1 + 0.6, by1, s), radius=int(0.7 * s), fill=(28, 28, 32), outline=(10, 10, 12), width=3)
    for cx, r in ((27.3, 0.45), (25.9, 0.38)):
        px, py = P(cx, (by0 + by1) / 2, s)
        d.ellipse([px - r * s, py - r * s, px + r * s, py + r * s], fill=(18, 18, 20), outline=(90, 90, 96), width=2)
    hx, hy = P(28.95, (by0 + by1) / 2, s)
    d.polygon([(hx, hy - 8), (hx + 1.6 * s, hy - 26), (hx + 1.6 * s, hy + 26), (hx, hy + 8)], fill=(255, 230, 150, 50))
    d.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=(255, 236, 160))
    # Boeden je Raum
    for key, (name, sysname, g) in rms.items():
        base = ROOM_COL.get(sysname, (140, 140, 140))
        x0, y0, x1, y1 = g.bounds
        d.rectangle(R(x0, y0, x1, y1, s), fill=base)
        yy = y0 + 0.45
        while yy < y1:
            d.line([P(x0, yy, s), P(x1, yy, s)], fill=lerp(base, (0, 0, 0), 0.08), width=2)
            yy += 0.45
    # Aussenbereiche: hintere Plattform und Umlauf der Lok als Gitterrost mit Gelaender
    for key in ("platform", "boards"):
        _n, _s, g = rms[key]
        x0, y0, x1, y1 = g.bounds
        xx = x0
        while xx < x1:
            d.line([P(xx, y0, s), P(xx, y1, s)], fill=(80, 80, 86, 120), width=2)
            xx += 0.25
    for west, yr, _owner, g in gangs:
        draw_gangway(d, s, g, west in RAMPS)
    # Waende (alles Unbegehbare innerhalb der Wagenkaesten), Treppenschaechte
    for key, _n, x0, x1, kind in CARS:
        for y0, y1 in [(AY0, AY1)] + ([(BY0B, BY1B)] if kind == "dd" else []):
            inner = box(x0, y0, x1, y1).difference(walk)
            for p in geom_parts(inner):
                d.polygon([P(*q, s) for q in p.exterior.coords], fill=WALL_COL)
    d.rectangle(R(*BOILER, s), fill=(28, 28, 32))
    for st in sw:
        draw_stairwell(d, s, st["main"], False)
        draw_stairwell(d, s, st["upper"], True)
    for sh in OPAQUE:
        d.rectangle(R(sh[1], sh[2], sh[3], sh[4], s), fill=BLOCK_COL, outline=(10, 10, 10))
    for sh in GLASS:
        d.rectangle(R(sh[1], sh[2], sh[3], sh[4], s), fill=GLASS_COL, outline=(20, 20, 20))
    for p in geom_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([P(*q, s) for q in ring.coords], fill=EDGE, width=3)
    # Raumnamen; zu breite zweizeilig
    f = font(24)
    for key, (name, _s, g) in rms.items():
        c = Point(LABEL_AT[key]) if key in LABEL_AT else g.centroid
        x0, _y0, x1, _y1 = g.bounds
        text = name
        if d.textlength(name, font=f) > (x1 - x0 - 0.3) * s and " " in name:
            i = name.rfind(" ")
            text = name[:i] + "\n" + name[i + 1:]
        d.multiline_text(P(c.x, c.y, s), text, font=f, fill=(255, 255, 255, 95), anchor="mm", align="center")
    d.text(P(0.0, AY1 + 1.6, s), "POLARIS  EXPRESS", font=font(26), fill=LINING, anchor="mm")
    return img


def tile_floor(img, s):
    """Bodenbild (Massstab s px/m, deckt BOUNDS) in Kacheln unter 2048 px schneiden; liefert floorTiles."""
    ww, hh = img.size
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(exist_ok=True)
    img.convert("RGB").save(PREVIEW / "preview_floor.jpg", quality=88)
    cols = math.ceil(ww / 2000)
    rows = math.ceil(hh / 2000)
    for old in list(OUT.glob(f"{KEY}_floor_*.jpg")) + list(OUT.glob(f"{KEY}_floor_*.png")):
        old.unlink()
    tw, th = (ww // cols) // 4 * 4, (hh // rows) // 4 * 4
    tiles, i = [], 0
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * tw, r * th
            x1 = ww if c == cols - 1 else x0 + tw
            y1 = hh if r == rows - 1 else y0 + th
            w4, h4 = (x1 - x0) // 4 * 4, (y1 - y0) // 4 * 4
            tile = img.crop((x0, y0, x0 + w4, y0 + h4))
            if img.mode == "RGBA":
                tile.save(OUT / f"{KEY}_floor_{i}.png", optimize=True)
            else:
                tile.save(OUT / f"{KEY}_floor_{i}.jpg", quality=85)
            tiles.append((i, BX0 + x0 / s, BY1 - (y0 + h4) / s, w4, h4))
            i += 1
    print(f"floor {ww}x{hh} in {len(tiles)} tile(s)")
    return tiles


MAP_LABELS = []


def minimap(walk, rms, sw):
    s = 24
    ww, hh = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    Pt = lambda x, y: ((x - BX0) * s, (BY1 - y) * s)
    ln = (224, 214, 236, 120)
    for _k, _n, cx0, cx1, kind in CARS:                                  # Wagenumrisse
        d.rounded_rectangle([*Pt(cx0 - WALL, AY1 + WALL), *Pt(cx1 + WALL, AY0 - WALL)], radius=6, outline=ln, width=2)
        if kind == "dd":
            for xx in (cx0 - WALL, cx1 + WALL):                         # gestrichelt: Oberdeck liegt darueber
                y = AY0 - 0.6
                while y > BY1B + 0.6:
                    d.line([Pt(xx, y), Pt(xx, max(y - 0.35, BY1B + 0.6))], fill=ln, width=2)
                    y -= 0.6
    for p in geom_parts(walk):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=(224, 214, 236, 235))
        for h in p.interiors:
            d.polygon([Pt(*q) for q in h.coords], fill=(0, 0, 0, 0))
    for p in geom_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([Pt(*q) for q in ring.coords], fill=(30, 22, 44, 255), width=4, joint="curve")
    for st in sw:                                                       # Treppen: Dreiecke nach unten/oben
        for poly, down in ((st["main"], False), (st["upper"], True)):
            x0, y0, x1, y1 = poly.bounds
            cx, cy = Pt((x0 + x1) / 2, (y0 + y1) / 2)
            k = 7
            pts = [(cx - k, cy - k * 0.6), (cx + k, cy - k * 0.6), (cx, cy + k * 0.8)] if down else \
                  [(cx - k, cy + k * 0.6), (cx + k, cy + k * 0.6), (cx, cy - k * 0.8)]
            d.polygon(pts, fill=(30, 22, 44, 255))
    f = font(14)
    MAP_LABELS.clear()
    for key, (name, _s, g) in rms.items():
        area = g.intersection(walk)
        c = area.representative_point()
        map_labels.place(d, f, name, c.x, c.y, area.buffer(-0.15), s, Pt, (30, 22, 44, 255), MAP_LABELS)
    dd = [c for c in CARS if c[4] == "dd"]
    d.text(Pt(dd[0][2] - 0.4, BY0B - 0.9), "UPPER DECK", font=font(15), fill=(224, 214, 236, 255), anchor="lm")
    img.save(OUT / f"{KEY}_minimap.png", optimize=True)


def button_and_icon():
    """Freeplay-Logo 1000 x 250, Lobby-Symbol 256 x 256 und das Treppensymbol fuer den Use-Knopf."""
    b = Image.new("RGBA", (1000, 250), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle([10, 30, 990, 220], 40, fill=(26, 30, 52, 235), outline=(214, 176, 92), width=8)
    d.text((500, 125), "POLARIS EXPRESS", font=font(96), fill=(240, 214, 140), anchor="mm")
    b.save(OUT / f"button_{KEY}.png", optimize=True)
    i = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(i)
    d.ellipse([8, 8, 248, 248], fill=(26, 30, 52, 255), outline=(214, 176, 92), width=8)
    d.rectangle([48, 96, 208, 168], fill=(176, 60, 50))
    d.rectangle([150, 70, 196, 100], fill=(176, 60, 50))
    d.rectangle([64, 74, 84, 96], fill=(60, 60, 64))
    for x in (80, 128, 176):
        d.ellipse([x - 18, 156, x + 18, 192], fill=(40, 40, 44), outline=(214, 176, 92), width=4)
    i.save(OUT / f"icon_{KEY}.png", optimize=True)
    # Treppensymbol im Stil der Vanilla-Knoepfe: Stufen, Messinggelaender, dicke dunkle Kontur
    S, N = 4, 1024
    t = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    ink, lw = (29, 27, 33, 255), 10 * S
    steps = 5
    pts = [(40, 216)]
    for k in range(steps):
        x = 40 + k * 36
        y = 216 - (k + 1) * 34
        pts += [(x, y), (x + 36, y)]
    pts += [(220, 216)]
    poly = [(x * S, y * S) for x, y in pts]
    d.polygon(poly, fill=(190, 132, 74, 255))
    for k in range(steps):                                             # Trittkanten hell, Setzstufen dunkel
        x = (40 + k * 36) * S
        y = (216 - (k + 1) * 34) * S
        d.rectangle([x, y, x + 36 * S, y + 8 * S], fill=(226, 176, 112, 255))
        d.rectangle([x, y + 8 * S, x + 6 * S, y + 34 * S], fill=(128, 84, 44, 255))
    d.line(poly + [poly[0]], fill=ink, width=lw, joint="curve")
    rail = [(52 * S, 150 * S), (214 * S, 14 * S + 18 * S)]
    d.line(rail, fill=ink, width=16 * S)
    d.line(rail, fill=(214, 176, 92, 255), width=7 * S)
    for k in range(steps):
        x = (58 + k * 36) * S
        d.line([(x, (216 - (k + 1) * 34) * S), (x, (150 - k * 29) * S)], fill=ink, width=5 * S)
    t = t.resize((256, 256), Image.LANCZOS)
    t.save(OUT / "task_stairs_button.png", optimize=True)
    ticket_icon()


def ticket_icon():
    """Fahrschein mit Lochung fuer den Sabotage-Kartenknopf und den Use-Knopf an der Lochzange (Vanilla-Look:
    dicke dunkle Kontur, warmes Papier, gezackte Abrisskante)."""
    S, N = 4, 1024
    t = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    ink, lw = (29, 27, 33, 255), 10 * S
    # Fahrschein schraeg, als Polygon mit Zacken an der rechten Kante
    body = [(36, 92), (196, 60), (204, 72), (198, 84), (206, 96), (200, 108), (208, 120), (202, 132), (210, 144),
            (204, 156), (212, 168), (206, 180), (222, 190), (62, 222)]
    poly = [(x * S, y * S) for x, y in body]
    d.polygon(poly, fill=(236, 212, 150, 255))
    d.line(poly + [poly[0]], fill=ink, width=lw, joint="curve")
    # Streifen und "POLARIS" angedeutet als Balken
    d.polygon([(52 * S, 104 * S), (176 * S, 80 * S), (178 * S, 92 * S), (54 * S, 116 * S)], fill=(176, 60, 50, 255))
    for k in range(3):
        y0 = 128 + k * 18
        d.line([(60 * S, (y0 + 10) * S), (150 * S, (y0 - 8) * S)], fill=(120, 96, 60, 255), width=5 * S)
    # Lochung
    d.ellipse([(150 - 22) * S, (176 - 22) * S, (150 + 22) * S, (176 + 22) * S], fill=(0, 0, 0, 0), outline=ink, width=8 * S)
    t = t.resize((256, 256), Image.LANCZOS)
    t.save(OUT / "task_ticket_button.png", optimize=True)


# ------------------------------------------------------------------ map.json

def v2(p):
    return [round(p[0], 4), round(p[1], 4)]


def Polygon_bounds(pts):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


def poly_out(g):
    return [v2(q) for q in list(g.exterior.coords)[:-1]]


def levels(gangs):
    """Wo jede Flaeche im 3D wirklich liegt (nur fuer Werkzeuge wie den Blender-/Nightfall-Nachbau)."""
    main = [box(x0, AY0, x1, AY1) for _k, _n, x0, x1, kind in CARS]
    upper = [box(x0, BY0B, x1, BY1B) for _k, _n, x0, x1, kind in CARS if kind == "dd"]
    out = [{"name": "main", "z": Z_MAIN, "offset": [0, 0], "areas": [poly_out(g) for g in main]},
           {"name": "upper", "z": Z_UPPER, "offset": [0, DECK_DY], "areas": [poly_out(g) for g in upper]}]
    for west, _yr, _o, g in gangs:
        x0, _y0, x1, _y1 = g.bounds
        if west in RAMPS:
            z0, z1 = RAMPS[west]
            out.append({"name": "ramp", "offset": [0, 0], "areas": [poly_out(g)],
                        "ramp": {"axis": "x", "from": round(x0, 3), "to": round(x1, 3), "z0": z0, "z1": z1}})
        else:
            out.append({"name": "gangway", "z": Z_MAIN, "offset": [0, 0], "areas": [poly_out(g)]})
    return out


def emit(walk, rms, doors, tiles, consoles, sw, gangs, floor_ppm=FLOOR_PPM, art=None):
    art = art or {}
    full = box(BX0 - 5, BY0 - 5, BX1 + 5, BY1 + 5)
    solid = full.difference(walk)
    move = walk.difference(translate(solid, 0, -0.3)).buffer(0)
    shadow = unary_union([walk, translate(walk, 0, 0.45)]).buffer(0)
    opaque = [shape(s) for s in OPAQUE]
    glass = [shape(s) for s in GLASS]
    edges = unary_union([LineString(r + [r[0]]) for r in rings_of(walk)])
    room_u = unary_union([g for _n, _s, g in rms.values()])
    halls = [g for g in geom_parts(walk.difference(room_u).buffer(0)) if g.area > 1.0]

    vert, hori = [], []
    for dd in doors:
        slot = {"label": dd["label"], "x": round(dd["x"], 3), "y": round(dd["y"], 3), "length": round(dd["length"], 2),
                "group": dd["group"], "seeThrough": False}
        (vert if dd["vertical"] else hori).append(slot)

    buttons = {}
    for key, (name, sysname, g) in rms.items():
        # Reactor und LifeSupp haben eigene Sabotagen (Runaway Train, Smoke in the Cars): keine Vanilla-Knoepfe
        if sysname in ("Cafeteria", "Storage", "UpperEngine", "LowerEngine", "Security", "MedBay",
                       "Electrical", "Comms") and sysname not in buttons:
            c = g.intersection(walk).representative_point()
            buttons[sysname] = v2((c.x, c.y + 0.8))

    data = {
        "format": 1, "key": KEY, "displayName": "Polaris Express", "resourcePrefix": KEY, "builtInEffects": False,
        "world": "train",
        "minX": BX0, "minY": BY0, "maxX": BX1, "maxY": BY1,
        "walls": [[v2(q) for q in r] for r in rings_of(move)],
        "shadowWalls": [[v2(q) for q in r] for r in rings_of(shadow)],
        "opaque": [[v2(q) for q in list(p.exterior.coords)[:-1]] for p in opaque],
        "opaqueCastsShadow": [p.distance(edges) > 0.08 for p in opaque],
        "glass": [[v2(q) for q in list(p.exterior.coords)[:-1]] for p in glass],
        "hallways": [[v2(q) for q in list(h.exterior.coords)[:-1]] for h in halls],
        "rooms": [{"key": k, "name": n, "room": s_, "area": [v2(q) for q in list(g.exterior.coords)[:-1]]}
                  for k, (n, s_, g) in rms.items()],
        "floorPixelsPerMeter": floor_ppm,
        "floorTiles": [{"index": i, "x": round(wx, 4), "y": round(wy, 4), "w": w, "h": h} for i, wx, wy, w, h in tiles],
        "propPixelsPerMeter": PROP_PPM, "props": art.get("props", []), "consoleSprites": art.get("consoleSprites", []),
        "noFadeKinds": art.get("noFadeKinds", []),
        "consoles": {k: v2(p) for k, p in sorted(consoles.items())},
        "emergencyButton": v2(EMERGENCY), "surveillanceConsole": v2(SURVEILLANCE), "adminTable": v2(ADMIN_TABLE),
        "freeplayLaptop": v2(FREEPLAY), "spawn": v2(SPAWN), "spawnRadius": SPAWN_RADIUS,
        "dummyRadius": v2(DUMMY_RADIUS),
        "stairs": [{"a": v2(st["a"]), "b": v2(st["b"]), "labelA": "UP", "labelB": "DOWN"} for st in sw],
        "levels": levels(gangs),
        "ticket": {"seconds": TICKET["seconds"], "button": v2(TICKET["button"]), "stations": [v2(q) for q in TICKET["stations"]]},
        "runaway": {"seconds": RUNAWAY["seconds"], "button": v2(RUNAWAY["button"]), "brake": v2(RUNAWAY["brake"]),
                    "handbrake": v2(RUNAWAY["handbrake"])},
        "smoke": {"seconds": SMOKE["seconds"], "button": v2(SMOKE["button"]), "source": v2(SMOKE["source"]),
                  "hatches": [v2(q) for q in SMOKE["hatches"]]},
        "scroll": art.get("scroll", []),
        "vents": {str(k): v2(p) for k, p in VENTS.items()},
        "ventNetworks": VENT_NETS, "ventBridges": VENT_BRIDGES,
        "verticalDoors": vert, "horizontalDoors": hori,
        "cameras": [v2(p) for p in CAMERAS], "cameraViews": {},
        "mapButtons": buttons,
        "mapLabels": [{"x": round(x, 3), "y": round(y, 3), "halfW": round(hw, 3), "halfH": round(hh, 3)} for x, y, hw, hh in MAP_LABELS],
        "cameraColor": [0.08, 0.09, 0.14],
        "minLight": 1.0, "maxLight": 5.0,
        "viewSpots": [v2(SPAWN), v2((-7.3, -4.9)), v2((23.0, 3.25)), v2((-18.4, 3.75)), v2((2.8, 3.25)), v2((-17.4, -5.6))],
        "taskNames": TASK_NAMES, "customTasks": {}, "taskArt": art.get("taskArt", {}), "taskText": art.get("taskText", {}),
    }
    (OUT / "map.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"map.json: rooms {len(rms)}, doors {len(vert)}V/{len(hori)}H, consoles {len(consoles)}, vents {len(VENTS)}, "
          f"stairs {len(sw)}, hallways {len(halls)}")


def export_layout(gangs, sw, walk=None, rms=None):
    """Fahrzeuge, Faltenbaelge und Treppen fuer Doku und Vorschau (nicht Teil des Kartenpakets); dazu Boeden und
    Waende je Ebene fuer die 3D-Vorschau (begehbare Flaeche geschnitten mit den levels-Flaechen)."""
    floors, walls = [], []
    if walk is not None:
        for lv in levels(gangs):
            area = unary_union([box(*Polygon_bounds(a)) for a in lv["areas"]])
            for p in geom_parts(walk.intersection(area).buffer(0)):
                floors.append({"level": lv["name"], "z": lv.get("z"), "offset": lv["offset"], "ramp": lv.get("ramp"),
                               "outer": [v2(q) for q in list(p.exterior.coords)[:-1]],
                               "holes": [[v2(q) for q in list(h.coords)[:-1]] for h in p.interiors]})
            lines = walk.boundary.intersection(area.buffer(0.02))
            for ln_ in getattr(lines, "geoms", [lines]):
                if ln_.geom_type == "LineString" and ln_.length > 0.05:
                    walls.append({"level": lv["name"], "z": lv.get("z"), "offset": lv["offset"], "ramp": lv.get("ramp"),
                                  "pts": [v2(q) for q in ln_.coords]})
    data = {
        "floors": floors, "walls": walls,
        "rooms": [{"key": k, "name": n, "system": s_, "level": "upper" if ROOM[k][4] == "B" else "main",
                   "cx": round(g.centroid.x, 3), "cy": round(g.centroid.y, 3)} for k, (n, s_, g) in (rms or {}).items()],
        "z": {"main": Z_MAIN, "upper": Z_UPPER},
        "cars": [{"key": k, "name": n, "x0": x0, "x1": x1, "kind": kind} for k, n, x0, x1, kind in CARS],
        "decks": {"A": [AY0, AY1], "B": [BY0B, BY1B], "upperOffset": DECK_DY},
        "ticket": {"seconds": TICKET["seconds"], "button": v2(TICKET["button"]), "stations": [v2(q) for q in TICKET["stations"]]},
        "gangways": [{"west": w, "east": next_car(w), "door": o, "ramp": w in RAMPS, "box": [round(v, 3) for v in g.bounds]}
                     for w, _yr, o, g in gangs],
        "stairs": [{"car": st["car"], "a": v2(st["a"]), "b": v2(st["b"]), "main": [round(v, 3) for v in st["main"].bounds],
                    "upper": [round(v, 3) for v in st["upper"].bounds]} for st in sw],
    }
    (PREVIEW / "layout.json").write_text(json.dumps(data, indent=1), encoding="utf-8")


def art_ctx(walk, rms, gangs, sw, doors, consoles):
    """Alles, was die Grafik (train_art.build) ueber die Karte wissen muss. Koordinaten in Metern, y nach Norden;
    P(x, y, s) rechnet nach Bildpixeln (Zeile 0 = Norden), R(x0, y0, x1, y1, s) ein Rechteck fuer PIL."""
    return {
        "bounds": BOUNDS, "floor_ppm_graybox": FLOOR_PPM, "prop_ppm": PROP_PPM, "wall": WALL,
        "cars": [{"key": k, "name": n, "x0": x0, "x1": x1, "kind": kind} for k, n, x0, x1, kind in CARS],
        "rooms": [{"key": k, "name": n, "system": sys_, "car": car, "deck": deck, "box": list(rms[k][2].bounds)}
                  for k, n, sys_, car, deck, _a, _b in ROOMS],
        "walk": walk, "room_geom": {k: g for k, (_n, _s, g) in rms.items()},
        "decks": {"A": (AY0, AY1), "B": (BY0B, BY1B), "upperOffset": DECK_DY},
        "gangways": [{"west": w, "east": next_car(w), "door": o, "box": list(g.bounds), "opening": yr} for w, yr, o, g in gangs],
        "stairs": [{"car": st["car"], "main": list(st["main"].bounds), "upper": list(st["upper"].bounds), "a": st["a"], "b": st["b"]} for st in sw],
        "doors": doors, "vparts": VPARTS, "hparts": HPARTS, "vsolid": VSOLID, "boiler": BOILER, "runboard": list(RUNBOARD),
        "opaque": OPAQUE, "glass": GLASS, "label_at": LABEL_AT,
        "consoles": consoles, "vents": VENTS, "cameras": CAMERAS, "ticket": TICKET, "runaway": RUNAWAY, "smoke": SMOKE,
        "spawn": SPAWN, "emergency": EMERGENCY, "surveillance": SURVEILLANCE, "admin_table": ADMIN_TABLE, "freeplay": FREEPLAY,
        "task_names": TASK_NAMES, "skeld_consoles": SKELD_CONSOLES,
        "P": P, "R": R, "geom_parts": geom_parts, "out": OUT, "preview": PREVIEW,
    }


def main():
    walk, rms, gangs, doors, sw, mouth_pts = build()
    obstacles = [shape(s) for s in OPAQUE + GLASS]
    consoles = place_consoles(walk, rms, mouth_pts, obstacles)
    free = walk.difference(unary_union(obstacles).buffer(0.25))
    checks = list(consoles.items()) + [("Emergency", EMERGENCY), ("Surveillance", SURVEILLANCE), ("Admin", ADMIN_TABLE),
                                       ("Freeplay", FREEPLAY), ("Spawn", SPAWN)] + [(f"Vent{v}", p) for v, p in VENTS.items()] \
        + [(f"Ticket{i}", p) for i, p in enumerate(TICKET["stations"])] + [("Brake", RUNAWAY["brake"]), ("Handbrake", RUNAWAY["handbrake"])]         + [(f"Hatch{i}", p) for i, p in enumerate(SMOKE["hatches"])]
    checks += [(f"Stair{i}A", st["a"]) for i, st in enumerate(sw)] + [(f"Stair{i}B", st["b"]) for i, st in enumerate(sw)]
    for k, p in checks:
        dd = free.distance(Point(p))
        if dd > 0.6:
            print(f"WARN {k} at {p} not reachable ({dd:.2f} m)")
    for i, st in enumerate(sw):                                    # Absaetze frei von Konsolen und Vents
        for end in ("a", "b"):
            q = Point(st[end])
            near = [k for k, p in list(consoles.items()) + [(f"Vent{v}", p) for v, p in VENTS.items()] if q.distance(Point(p)) < 0.9]
            if near:
                print(f"WARN stair {i}{end} crowded by {near}")
    parts = geom_parts(walk)
    print(f"walk: {len(parts)} part(s) (Hauptebene + {len(parts) - 1} Oberdecks), {sum(len(p.interiors) for p in parts)} hole(s)")
    minimap(walk, rms, sw)
    button_and_icon()
    # Echte Grafik (tools/train_art.py, siehe docs/TRAIN_ART.md): liefert Bodenbild, Objekt- und Konsolen-Atlanten
    # samt map.json-Eintraegen; ohne das Modul bleibt es bei der Graybox.
    art, floor_ppm = {}, FLOOR_PPM
    try:
        import train_art
    except ImportError:
        train_art = None
    if train_art is not None:
        art = train_art.build(art_ctx(walk, rms, gangs, sw, doors, consoles))
        floor_ppm = art.get("floor_ppm", FLOOR_PPM)
        img = art["floor"]
        for i, im in enumerate(art.get("props_atlases", [])):
            im.save(OUT / f"{KEY}_props_{i}.png", optimize=True)
        for i, im in enumerate(art.get("console_atlases", [])):
            im.save(OUT / f"{KEY}_consoles_{i}.png", optimize=True)
        for name, im in art.get("files", {}).items():
            im.save(OUT / name, optimize=True)
        if art.get("minimap") is not None:
            art["minimap"].save(OUT / f"{KEY}_minimap.png", optimize=True)
        print(f"train_art: floor {img.size} @ {floor_ppm} px/m, props {len(art.get('props', []))}, "
              f"console sprites {len(art.get('consoleSprites', []))}, files {len(art.get('files', {}))}")
    else:
        img = render_floor(walk, rms, gangs, sw)
    tiles = tile_floor(img, floor_ppm)
    emit(walk, rms, doors, tiles, consoles, sw, gangs, floor_ppm, art)
    export_layout(gangs, sw, walk, rms)

    s = floor_ppm
    im = Image.open(PREVIEW / "preview_floor.jpg").convert("RGB")
    d = ImageDraw.Draw(im)
    for k, p in consoles.items():
        x, y = P(*p, s)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 230, 0), outline=(0, 0, 0))
    for v, p in VENTS.items():
        x, y = P(*p, s)
        d.rectangle([x - 9, y - 6, x + 9, y + 6], fill=(60, 200, 90), outline=(0, 0, 0))
        d.text((x, y), str(v), fill=(0, 0, 0), anchor="mm", font=font(12))
    for p in CAMERAS:
        x, y = P(*p, s)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(220, 60, 60), outline=(0, 0, 0))
    for dd in doors:
        hw, hh = (0.15, dd["length"] / 2) if dd["vertical"] else (dd["length"] / 2, 0.12)
        d.rectangle(R(dd["x"] - hw, dd["y"] - hh, dd["x"] + hw, dd["y"] + hh, s), fill=(60, 120, 255))
    for st in sw:
        for end in ("a", "b"):
            x, y = P(*st[end], s)
            d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=(255, 120, 255), width=3)
    for p, col in ((SPAWN, (255, 255, 255)), (EMERGENCY, (255, 60, 60)), (SURVEILLANCE, (0, 220, 255)),
                   (ADMIN_TABLE, (0, 220, 255)), (FREEPLAY, (255, 140, 0)), (TICKET["button"], (240, 200, 60)),
                   (TICKET["stations"][0], (240, 200, 60)), (TICKET["stations"][1], (240, 200, 60)),
                   (RUNAWAY["brake"], (255, 90, 90)), (RUNAWAY["handbrake"], (255, 90, 90)), (RUNAWAY["button"], (255, 90, 90)),
                   (SMOKE["button"], (160, 160, 170)), (SMOKE["source"], (160, 160, 170)), (SMOKE["hatches"][0], (160, 160, 170)),
                   (SMOKE["hatches"][1], (160, 160, 170)), (SMOKE["hatches"][2], (160, 160, 170))):
        x, y = P(*p, s)
        d.rectangle([x - 7, y - 7, x + 7, y + 7], outline=col, width=3)
    im.save(PREVIEW / "preview.png")
    print(PREVIEW / "preview.png", im.size)


if __name__ == "__main__":
    main()
