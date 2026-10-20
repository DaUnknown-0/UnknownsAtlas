# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_consoles.py - Konsolen-Sprites des Polaris Express: fuer jeden Skeld-Konsolen-Schluessel ein Geraet, das
# zur Aufgabe passt (gen_train.TASK_NAMES): Telegraf fuer "Send a Telegram", Dampfventile fuer "Divert Steam
# Power", Lampen-Anschlusskasten fuer "Repair the Lamp Wiring", Feuerloch fuer "Shovel Coal" usw.
#
# Jedes Geraet steht mit seiner Standlinie auf y = 0, Mitte x = 0 (Weltmeter), 160 px/m, schraege Aufsicht.
# render_all liefert {key: (Bild, Pivot-x px, Pivot-y px von unten)}; der Pivot ist der Fusspunkt des Geraets.

import math
import random

import museum_art as A
from museum_art import K, OUTLINE, OUT_W, alpha, shade
import train_style as S
from train_style import (BRASS, BRASS_D, BRASS_L, BULB, COAL, COAL_L, CREAM, CREAM_D, GLASS, GREEN_LAMP, INK, IRON,
                         IRON_L, LEATHER, LEATHER_D, OAK, OAK_D, PAPER, RED_LAMP, STEEL, STEEL_D, STEEL_L, TEAL, VELVET,
                         VELVET_D, WARM, WHITE, WOOD, WOOD_D, WOOD_L, WOOD_X, TProp)

# Farbton des Gestells je Skeld-System (wie Park/Museum: ein Blick sagt, in welchem Raum man steht)
ROOM_TINT = {
    "Cafeteria": VELVET, "Security": LEATHER, "Storage": OAK_D, "MedBay": CREAM_D, "LifeSupp": STEEL_L, "Comms": WOOD,
    "Electrical": STEEL, "Nav": TEAL, "Shields": IRON_L, "UpperEngine": (74, 124, 92, 255), "LowerEngine": IRON,
    "Reactor": (150, 44, 40, 255), "Weapons": IRON_L, "Admin": OAK,
}


def device_kind(key, sysname):
    """Geraet je Konsolen-Schluessel."""
    part = key.split("/")[1]
    if part in ("DataConsole", "UploadDataConsole"):
        return "telegraph_key" if sysname == "Comms" else "telegram_desk"
    if part == "FixWiringConsole":
        return "wirebox"
    if part == "GarbageConsole":
        return "ash_pan" if sysname == "LifeSupp" else "ash_bin"
    if part == "AirlockConsole":
        return "ash_chute"
    if part == "DivertPowerConsole":
        return "manifold" if sysname == "Electrical" else "steam_valve"
    return {
        "ShieldConsole": "signal_lamps", "gasCanConsole": "coal_scuttle", "FuelEngineConsole": "firebox",
        "AlignEngineConsole": "governor", "CalibrateConsole": "dynamo_ctrl", "SwitchConsole": "switchboard",
        "FixCommsConsole": "relay", "ChartCourseConsole": "route_map", "StabilizeSteeringConsole": "headlamp_ctrl",
        "SwipeCardConsole": "stamp_desk", "StartReactorConsole": "boiler_panel", "UnlockManifoldsConsole": "valves_panel",
        "UpperHandConsole": "bigvalve", "LowerHandConsole": "bigvalve", "WeaponConsole": "searchlight",
        "MedBayConsole": "tea_trolley", "MedScanner": "inspection_gate", "NoOxyConsole": "smoke_damper",
        "CleanFilterConsole": "hood_filter",
    }.get(part, "telegram_desk")


# ------------------------------------------------------------------ Bausteine

def stand(p, w, d, h, col, w_line=0.035):
    """Gestell/Sockel: Box w x d, Hoehe h, Standlinie y = 0. Rueckgabe: Oberkante (Welt-y der Deckflaeche vorn)."""
    p.box(-w / 2, 0, w / 2, d, 0, h, shade(col, 1.12), col, w=w_line)
    return h * K


def post(p, h, col=BRASS, r=0.035, foot=0.14):
    c = p.c
    c.ellipse(0, 0.08, foot, foot * 0.5, fill=shade(col, 0.8), outline=OUTLINE, width=0.025)
    c.rect(-r, 0.08, r, 0.08 + h * K, fill=col, outline=OUTLINE, width=0.02)
    c.line([(-r * 0.4, 0.12), (-r * 0.4, 0.06 + h * K)], fill=shade(col, 1.35), width=r * 0.4)
    return 0.08 + h * K


def panel(p, cx, cy, w, h, col=(60, 52, 48, 255), rim=BRASS, tilt=0.0):
    """Schraeg stehende Tafel (Frontansicht) mit Messingrahmen."""
    c = p.c
    c.rect(cx - w / 2 - 0.03, cy - 0.03, cx + w / 2 + 0.03, cy + h + 0.03, fill=rim, outline=OUTLINE, width=0.025)
    c.rect(cx - w / 2, cy, cx + w / 2, cy + h, fill=col, outline=shade(rim, 0.6), width=0.012)
    c.line([(cx - w / 2 + 0.02, cy + h - 0.015), (cx + w / 2 - 0.02, cy + h - 0.015)], fill=alpha(shade(col, 1.5), 180), width=0.012)
    for sx in (-1, 1):
        for sy in (0.03, h - 0.03):
            c.ellipse(cx + sx * (w / 2 - 0.03), cy + sy, 0.01, 0.01, fill=shade(rim, 0.6))


def lamp_small(c, x, y, col=RED_LAMP, r=0.02, on=True):
    if on:
        c.glow(x, y, r * 5, col, 0.5)
    c.ellipse(x, y, r, r, fill=col if on else shade(col, 0.4), outline=OUTLINE, width=0.01)
    c.ellipse(x - r * 0.3, y + r * 0.3, r * 0.3, r * 0.25, fill=alpha(WHITE, 160))


def wire(c, pts, col, w=0.016):
    c.line(pts, fill=OUTLINE, width=w + 0.012)
    c.line(pts, fill=col, width=w)


def tag(p, cy, text, w=None, size=0.045):
    S.plate(p.c, 0, cy, w or (0.06 * len(text) + 0.1), 0.075, text, size=size)


# ------------------------------------------------------------------ Geraete

def draw_device(kind, sysname, idx, ppm):
    rnd = random.Random(idx * 17 + 3)
    tint = ROOM_TINT.get(sysname, OAK)
    big = kind in ("inspection_gate", "manifold", "route_map", "searchlight", "tea_trolley", "signal_lamps")
    w, d, h = (1.3, 0.8, 1.5) if big else (0.9, 0.5, 1.4)
    p = TProp(-w / 2, 0, w / 2, d, h, ppm, pad=0.35)
    c = p.c
    if kind != "inspection_gate":
        c.soft_shadow([(-w * 0.3, -0.08), (w * 0.34, -0.08), (w * 0.34, d * 0.9), (-w * 0.3, d * 0.9)], 95, 0.08)

    if kind == "telegram_desk":
        # Schreibpult aus Holz: Formularblock, Feder, Messingglocke, Schild TELEGRAMS
        top = stand(p, 0.6, 0.4, 0.9, tint)
        c.poly([(-0.3, top), (0.3, top), (0.3, 0.4 + 1.05 * K), (-0.3, 0.4 + 1.05 * K)], fill=OAK, outline=OUTLINE, width=0.03)
        c.line([(-0.27, 0.4 + 1.05 * K - 0.02), (0.27, 0.4 + 1.05 * K - 0.02)], fill=shade(OAK, 1.3), width=0.015)
        c.rect(-0.2, top + 0.05, 0.05, top + 0.2, fill=PAPER, outline=OUTLINE, width=0.012)
        for k in range(3):
            c.line([(-0.17, top + 0.09 + k * 0.035), (0.02, top + 0.09 + k * 0.035)], fill=(120, 100, 70, 255), width=0.008)
        c.line([(-0.17, top + 0.165), (-0.1, top + 0.165)], fill=(170, 44, 50, 255), width=0.012)
        c.line([(0.1, top + 0.06), (0.22, top + 0.2)], fill=OUTLINE, width=0.03)
        c.line([(0.1, top + 0.06), (0.22, top + 0.2)], fill=(40, 36, 44, 255), width=0.015)
        c.ellipse(0.16, top + 0.04, 0.04, 0.025, fill=INK)
        c.ellipse(0.2, top + 0.14, 0.05, 0.05, fill=BRASS, outline=OUTLINE, width=0.015)
        c.ellipse(0.2, top + 0.16, 0.02, 0.012, fill=BRASS_L)
        tag(p, 0.45 * K, "TELEGRAMS", 0.5)

    elif kind == "telegraph_key":
        # Telegrafentisch: Morsetaste, Klopfer, Papierstreifen, Batterie, Kabel zur Wand
        top = stand(p, 0.8, 0.45, 0.8, WOOD)
        c.poly([(-0.4, top), (0.4, top), (0.4, 0.45 + 0.8 * K), (-0.4, 0.45 + 0.8 * K)], fill=OAK, outline=OUTLINE, width=0.03)
        kx = -0.15
        c.rect(kx - 0.1, top + 0.03, kx + 0.1, top + 0.15, fill=WOOD_X, outline=OUTLINE, width=0.015)
        c.line([(kx - 0.08, top + 0.1), (kx + 0.12, top + 0.2)], fill=OUTLINE, width=0.035)
        c.line([(kx - 0.08, top + 0.1), (kx + 0.12, top + 0.2)], fill=BRASS, width=0.018)
        c.ellipse(kx + 0.12, top + 0.2, 0.03, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.012)
        c.ellipse(kx - 0.05, top + 0.08, 0.02, 0.02, fill=BRASS, outline=OUTLINE, width=0.01)
        sx = 0.17
        c.rect(sx - 0.12, top + 0.04, sx + 0.12, top + 0.18, fill=(60, 52, 48, 255), outline=OUTLINE, width=0.015)
        c.rect(sx - 0.08, top + 0.18, sx - 0.02, top + 0.28, fill=BRASS, outline=OUTLINE, width=0.01)
        c.rect(sx + 0.02, top + 0.18, sx + 0.08, top + 0.28, fill=BRASS, outline=OUTLINE, width=0.01)
        c.line([(sx - 0.12, top + 0.3), (sx + 0.12, top + 0.25)], fill=OUTLINE, width=0.025)
        c.line([(sx - 0.12, top + 0.3), (sx + 0.12, top + 0.25)], fill=BRASS_L, width=0.012)
        c.ellipse(0.32, top + 0.26, 0.07, 0.07, fill=CREAM, outline=OUTLINE, width=0.012)
        c.line([(0.32, top + 0.26), (0.2, top + 0.14), (0.0, top + 0.1)], fill=CREAM, width=0.02)
        lamp_small(c, -0.32, top + 0.22, GREEN_LAMP, 0.022)
        for k, col in enumerate(((190, 40, 40, 255), (40, 60, 160, 255))):
            wire(c, [(0.3 + k * 0.05, top + 0.05), (0.42, top + 0.3 + k * 0.08), (0.46, 0.45 + 1.2 * K)], col, 0.012)
        tag(p, 0.4 * K, "TELEGRAPH", 0.52)

    elif kind == "wirebox":
        # Anschlusskasten der Lampenleitung: Holzkasten mit Messingklemmen, haengende Draehte, Lampe oben
        top = post(p, 0.55, BRASS_D)
        c.rect(-0.26, top, 0.26, top + 0.42, fill=WOOD_D, outline=OUTLINE, width=0.03)
        c.rect(-0.22, top + 0.04, 0.22, top + 0.38, fill=(50, 40, 34, 255), outline=shade(WOOD_D, 0.6), width=0.012)
        cols = [(230, 60, 60, 255), (70, 110, 230, 255), (240, 200, 60, 255), (240, 110, 200, 255)]
        for k, col in enumerate(cols):
            yy = top + 0.33 - k * 0.08
            c.rect(-0.21, yy - 0.025, -0.15, yy + 0.025, fill=BRASS, outline=OUTLINE, width=0.01)
            c.rect(0.15, yy - 0.025, 0.21, yy + 0.025, fill=BRASS, outline=OUTLINE, width=0.01)
            wire(c, [(-0.15, yy), (-0.06 + 0.02 * k, yy - 0.02)], col)
            tx = rnd.uniform(0.0, 0.1)
            wire(c, [(0.15, yy), (0.05 + tx * 0.3, yy + rnd.uniform(-0.04, 0.03))], col)
        c.ellipse(0.0, top + 0.21, 0.012, 0.012, fill=RED_LAMP)
        c.line([(-0.26, top + 0.42), (-0.26, top + 0.42 + 0.03), (0.26, top + 0.42 + 0.03), (0.26, top + 0.42)], fill=OUTLINE, width=0.025)
        S.sconce(c, 0.0, top + 0.58, 0.8, on=False, glow_r=0.0)
        c.line([(0.0, top + 0.42), (0.0, top + 0.47)], fill=(40, 36, 44, 255), width=0.014)
        tag(p, 0.08 + 0.3 * K, "LAMPS", 0.3)

    elif kind == "ash_bin":
        # Aschebehaelter aus Messing mit Deckel, Fusspedal
        p.cyl(0, 0.2, 0.22, 0, 0.7, shade(BRASS_D, 1.2), BRASS_D, ry=0.11)
        c.rect(-0.22, 0.2 + 0.25 * K, 0.22, 0.2 + 0.32 * K, fill=shade(BRASS_D, 0.75))
        c.rect(-0.22, 0.2 + 0.5 * K, 0.22, 0.2 + 0.56 * K, fill=shade(BRASS_D, 0.75))
        c.ellipse(0, 0.2 + 0.76 * K, 0.24, 0.12, fill=BRASS, outline=OUTLINE, width=0.025)
        c.ellipse(0, 0.2 + 0.76 * K + 0.03, 0.05, 0.03, fill=BRASS_D, outline=OUTLINE, width=0.012)
        c.rect(-0.12, 0.02, -0.02, 0.06, fill=IRON, outline=OUTLINE, width=0.015)
        c.rect(-0.1, 0.0, 0.14, 0.035, fill=IRON_L, outline=OUTLINE, width=0.015)
        tag(p, 0.2 + 0.4 * K, "ASH", 0.26)

    elif kind == "ash_chute":
        # Aschenrutsche: schraeger Blechtrichter in den Boden mit Klappe und Hebel
        p.box(-0.3, 0, 0.3, 0.45, 0, 0.5, IRON_L, IRON, w=0.035)
        c.poly([(-0.26, 0.5 * K + 0.05), (0.26, 0.5 * K + 0.05), (0.2, 0.45 + 0.5 * K - 0.03), (-0.2, 0.45 + 0.5 * K - 0.03)],
               fill=(30, 28, 32, 255), outline=OUTLINE, width=0.02)
        c.poly([(-0.26, 0.5 * K + 0.05), (0.26, 0.5 * K + 0.05), (0.26, 0.5 * K + 0.18), (-0.26, 0.5 * K + 0.18)], fill=STEEL, outline=OUTLINE, width=0.02)
        c.line([(0.22, 0.5 * K + 0.18), (0.36, 0.5 * K + 0.5)], fill=OUTLINE, width=0.04)
        c.line([(0.22, 0.5 * K + 0.18), (0.36, 0.5 * K + 0.5)], fill=BRASS, width=0.02)
        c.ellipse(0.36, 0.5 * K + 0.5, 0.03, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.012)
        A.hazard(c, -0.3, 0.02, 0.3, 0.08)
        for k in range(6):
            c.ellipse(rnd.uniform(-0.18, 0.18), 0.5 * K + 0.1 + rnd.uniform(0, 0.12), 0.012, 0.01, fill=(120, 116, 120, 255))
        tag(p, 0.5 * K - 0.06, "ASH CHUTE", 0.44)

    elif kind == "ash_pan":
        # Aschekasten des Herds: Eisenschublade mit Griff, graue Asche, kleiner Haufen davor
        p.box(-0.3, 0, 0.3, 0.4, 0, 0.42, IRON_L, IRON, w=0.035)
        c.rect(-0.26, 0.05, 0.26, 0.42 * K - 0.04, fill=STEEL_D, outline=OUTLINE, width=0.015)
        c.rect(-0.08, 0.1, 0.08, 0.15, fill=BRASS, outline=OUTLINE, width=0.012)
        c.poly([(-0.27, 0.42 * K + 0.02), (0.27, 0.42 * K + 0.02), (0.27, 0.4 + 0.42 * K), (-0.27, 0.4 + 0.42 * K)], fill=(150, 146, 150, 255))
        for k in range(10):
            c.ellipse(rnd.uniform(-0.22, 0.22), 0.42 * K + 0.06 + rnd.uniform(0, 0.3), rnd.uniform(0.02, 0.04), rnd.uniform(0.015, 0.03),
                      fill=rnd.choice([(190, 186, 190, 255), (110, 106, 110, 255)]))
        c.glow(0.05, 0.42 * K + 0.18, 0.12, (255, 120, 50, 255), 0.6)
        c.ellipse(0.05, 0.42 * K + 0.18, 0.025, 0.02, fill=(255, 150, 60, 255))
        tag(p, 0.42 * K - 0.02, "ASH PAN", 0.38)

    elif kind == "steam_valve":
        # Dampfventil: stehendes Messingrohr mit Handrad und Manometer, Sockel in Raumfarbe
        stand(p, 0.44, 0.3, 0.2, tint)
        S.pipe(c, [(0, 0.2 * K + 0.1), (0, 0.2 * K + 0.95)], 0.05, BRASS_D, flange=True)
        S.pipe(c, [(-0.22, 0.2 * K + 0.55), (0.22, 0.2 * K + 0.55)], 0.04, BRASS_D, flange=True)
        S.handwheel(c, 0, 0.2 * K + 0.55, 0.17, 0.17, (190, 50, 44, 255), spokes=5, w=0.022)
        S.gauge(c, 0, 0.2 * K + 1.02, 0.1, 50 + idx * 7 % 90)
        c.glow(0.12, 0.2 * K + 0.9, 0.1, WHITE, 0.35)
        tag(p, 0.2 * K + 0.22, "STEAM", 0.34)

    elif kind == "manifold":
        # Dampfverteiler (Quelle von Divert Steam Power): Sammelrohr mit vier Ventilen und Manometern
        top = stand(p, 1.2, 0.5, 0.3, tint)
        S.pipe(c, [(-0.55, top + 0.4), (0.55, top + 0.4)], 0.07, BRASS_D, flange=True)
        for k in range(4):
            x = -0.42 + k * 0.28
            S.pipe(c, [(x, top + 0.4), (x, top + 0.85)], 0.035, BRASS_D, flange=False)
            S.handwheel(c, x, top + 0.62, 0.09, 0.09, (190, 50, 44, 255) if k % 2 == 0 else (60, 110, 190, 255), spokes=4, w=0.014)
            S.gauge(c, x, top + 0.95, 0.065, 30 + k * 25, w=0.012)
        S.pipe(c, [(0.55, top + 0.4), (0.62, top + 0.4), (0.62, 0.05)], 0.05, BRASS_D, flange=False)
        lamp_small(c, -0.52, top + 0.15, GREEN_LAMP, 0.022)
        tag(p, top + 0.12, "STEAM  DISTRIBUTOR", 0.7, 0.04)

    elif kind == "signal_lamps":
        # Signallampen der hinteren Plattform: Pfosten mit zwei Laternen (rot/weiss) und Stellhebel
        top = post(p, 1.1, IRON_L, 0.04, 0.18)
        c.rect(-0.4, top - 0.08, 0.4, top, fill=IRON, outline=OUTLINE, width=0.025)
        S.lantern(c, -0.26, top + 0.12, 1.0, RED_LAMP, on=True)
        S.lantern(c, 0.26, top + 0.12, 1.0, (255, 240, 200, 255), on=False)
        c.ellipse(0, top + 0.1, 0.035, 0.035, fill=BRASS, outline=OUTLINE, width=0.012)
        c.line([(0.0, 0.3), (0.22, 0.65)], fill=OUTLINE, width=0.04)
        c.line([(0.0, 0.3), (0.22, 0.65)], fill=BRASS, width=0.02)
        c.ellipse(0.22, 0.65, 0.035, 0.035, fill=WOOD_D, outline=OUTLINE, width=0.012)
        tag(p, 0.42, "SIGNALS", 0.38)

    elif kind == "coal_scuttle":
        # Kohleneimer mit Schaufel und Kohlensack
        p.cyl(-0.12, 0.18, 0.18, 0, 0.42, shade(IRON_L, 1.2), IRON_L, ry=0.09)
        c.ellipse(-0.12, 0.18 + 0.42 * K, 0.17, 0.085, fill=COAL, outline=OUTLINE, width=0.015)
        for k in range(7):
            ca = rnd.uniform(0, math.tau)
            cr = rnd.uniform(0, 0.1)
            c.ellipse(-0.12 + cr * math.cos(ca), 0.18 + 0.42 * K + 0.03 + cr * 0.5 * math.sin(ca), 0.03, 0.025, fill=COAL_L, outline=OUTLINE, width=0.01)
        c.line([(-0.3, 0.18 + 0.42 * K), (-0.12, 0.18 + 0.75 * K + 0.1), (0.06, 0.18 + 0.42 * K)], fill=OUTLINE, width=0.035)
        c.line([(-0.3, 0.18 + 0.42 * K), (-0.12, 0.18 + 0.75 * K + 0.1), (0.06, 0.18 + 0.42 * K)], fill=IRON_L, width=0.018)
        c.poly([(0.08, 0.02), (0.36, 0.02), (0.4, 0.14), (0.36, 0.42), (0.3, 0.5), (0.14, 0.5), (0.08, 0.42), (0.04, 0.14)],
               fill=(150, 124, 86, 255), outline=OUTLINE, width=0.025)
        c.line([(0.1, 0.44), (0.34, 0.44)], fill=(100, 80, 54, 255), width=0.015)
        c.textf(0.22, 0.26, "COAL", 0.05, (80, 62, 40, 255), kind="black")
        c.line([(0.3, 0.5), (0.5, 0.95)], fill=OUTLINE, width=0.05)
        c.line([(0.3, 0.5), (0.5, 0.95)], fill=OAK_D, width=0.025)
        c.poly([(0.22, 0.56), (0.4, 0.46), (0.5, 0.62), (0.34, 0.74)], fill=IRON_L, outline=OUTLINE, width=0.02)

    elif kind == "firebox":
        # Feuerloch: Stirnwand aus Stahl mit runder Feuertuer (Glut), Kohlenhaufen und Schaufel davor
        p.box(-0.45, 0.1, 0.45, 0.5, 0, 1.1, STEEL_L, STEEL, w=0.035)
        S.rivets(c, [(-0.38 + k * 0.095, 0.1 + 1.05 * K) for k in range(9)] + [(-0.38 + k * 0.095, 0.16) for k in range(9)], 0.013)
        c.glow(0, 0.1 + 0.55 * K, 0.4, (255, 140, 50, 255), 0.6)
        c.ellipse(0, 0.1 + 0.55 * K, 0.2, 0.2, fill=IRON, outline=OUTLINE, width=0.03)
        c.ellipse(0, 0.1 + 0.55 * K, 0.14, 0.14, fill=(255, 150, 50, 255), outline=OUTLINE, width=0.015)
        c.ellipse(-0.02, 0.1 + 0.55 * K - 0.02, 0.07, 0.06, fill=(255, 220, 120, 255))
        c.line([(0.2, 0.1 + 0.55 * K), (0.34, 0.1 + 0.55 * K + 0.12)], fill=OUTLINE, width=0.035)
        c.line([(0.2, 0.1 + 0.55 * K), (0.34, 0.1 + 0.55 * K + 0.12)], fill=BRASS, width=0.018)
        S.gauge(c, -0.3, 0.1 + 0.9 * K, 0.07, 60)
        for k in range(8):
            c.ellipse(-0.3 + rnd.uniform(-0.12, 0.12), 0.02 + rnd.uniform(0, 0.08), 0.03, 0.022, fill=COAL, outline=OUTLINE, width=0.01)
        c.line([(0.3, 0.02), (0.5, 0.42)], fill=OUTLINE, width=0.05)
        c.line([(0.3, 0.02), (0.5, 0.42)], fill=OAK_D, width=0.025)
        c.poly([(0.2, 0.08), (0.38, -0.02), (0.48, 0.14), (0.32, 0.24)], fill=IRON_L, outline=OUTLINE, width=0.02)
        tag(p, 0.1 + 1.0 * K + 0.02, "FIREBOX", 0.4)

    elif kind == "governor":
        # Fliehkraftregler auf Saeule: Messingkugeln, Skala, Stellknopf
        top = stand(p, 0.5, 0.35, 0.5, tint)
        c.rect(-0.2, top + 0.02, 0.2, top + 0.14, fill=IRON, outline=OUTLINE, width=0.02)
        c.line([(0, top + 0.14), (0, top + 0.62)], fill=OUTLINE, width=0.04)
        c.line([(0, top + 0.14), (0, top + 0.62)], fill=BRASS, width=0.02)
        for sx in (-1, 1):
            c.line([(0, top + 0.58), (sx * 0.14, top + 0.32)], fill=OUTLINE, width=0.028)
            c.line([(0, top + 0.58), (sx * 0.14, top + 0.32)], fill=BRASS, width=0.014)
            c.line([(0, top + 0.2), (sx * 0.14, top + 0.32)], fill=BRASS, width=0.012)
            c.ellipse(sx * 0.14, top + 0.3, 0.05, 0.05, fill=BRASS, outline=OUTLINE, width=0.015)
            c.ellipse(sx * 0.14 - 0.015, top + 0.315, 0.015, 0.012, fill=BRASS_L)
        c.ellipse(0, top + 0.64, 0.04, 0.03, fill=BRASS_D, outline=OUTLINE, width=0.015)
        S.gauge(c, 0.0, top + 0.72 + 0.05, 0.09, 45 + 10 * (idx % 3))
        c.ellipse(-0.14, top + 0.08, 0.035, 0.035, fill=WOOD_D, outline=OUTLINE, width=0.012)
        c.line([(-0.14, top + 0.08), (-0.12, top + 0.11)], fill=BRASS_L, width=0.01)
        lamp_small(c, 0.14, top + 0.08, GREEN_LAMP, 0.018)
        tag(p, 0.3 * K, "GOVERNOR", 0.42)

    elif kind == "dynamo_ctrl":
        # Dynamo-Regler: Schalttafel mit grossem Instrument, zwei Drehknoepfen, Skala
        top = stand(p, 0.6, 0.35, 0.5, tint)
        panel(p, 0, top, 0.56, 0.5, (56, 50, 46, 255))
        S.gauge(c, 0, top + 0.3, 0.15, 70, red_zone=True)
        for sx in (-0.18, 0.18):
            c.ellipse(sx, top + 0.1, 0.04, 0.04, fill=BRASS, outline=OUTLINE, width=0.015)
            c.line([(sx, top + 0.1), (sx + 0.025, top + 0.13)], fill=INK, width=0.012)
        lamp_small(c, 0, top + 0.08, GREEN_LAMP, 0.018)
        tag(p, 0.25 * K, "BALANCE", 0.4)

    elif kind == "switchboard":
        # Schalttafel: dunkle Platte mit fuenf Messerschaltern und Lampen, Blitzschild
        top = stand(p, 0.8, 0.3, 0.3, tint)
        panel(p, 0, top, 0.76, 0.6, (60, 52, 48, 255))
        for k in range(5):
            x = -0.28 + k * 0.14
            S.knife_switch(c, x, top + 0.3, 1.0, closed=(k != 2))
            lamp_small(c, x, top + 0.52, GREEN_LAMP if k != 2 else RED_LAMP, 0.018)
        c.poly([(0.3, top + 0.12), (0.25, top + 0.03), (0.29, top + 0.05), (0.26, -0.02 + top), (0.33, top + 0.08), (0.29, top + 0.07)],
               fill=(240, 200, 60, 255))
        tag(p, 0.2 * K, "DYNAMO SWITCHES", 0.6, 0.04)

    elif kind == "relay":
        # Telegrafen-Relais: Holzschrank mit Spulen, Anker, roter Stoerlampe, Kabelbaum
        top = stand(p, 0.7, 0.4, 1.0, WOOD_D)
        c.rect(-0.3, 0.08, 0.3, 1.0 * K - 0.06, fill=(50, 40, 34, 255), outline=OUTLINE, width=0.02)
        for k, x in enumerate((-0.18, 0.0, 0.18)):
            c.rect(x - 0.06, 0.18, x + 0.06, 0.4, fill=(190, 120, 66, 255), outline=OUTLINE, width=0.012)
            for j in range(6):
                c.line([(x - 0.055, 0.2 + j * 0.033), (x + 0.055, 0.2 + j * 0.033)], fill=(150, 86, 46, 255), width=0.006)
            c.rect(x - 0.02, 0.4, x + 0.02, 0.47, fill=BRASS, outline=OUTLINE, width=0.008)
        c.line([(-0.22, 0.1), (0.22, 0.1)], fill=BRASS, width=0.02)
        lamp_small(c, 0.0, top - 0.02, RED_LAMP, 0.03)
        c.line([(-0.3, 1.0 * K + 0.1), (-0.3, 1.0 * K + 0.5), (0.3, 1.0 * K + 0.5), (0.3, 1.0 * K + 0.1)], fill=(40, 36, 44, 255), width=0.016)
        for k in range(4):
            c.ellipse(-0.3 + k * 0.2, 1.0 * K + 0.5, 0.02, 0.025, fill=CREAM, outline=OUTLINE, width=0.01)
        c.rect(-0.14, 1.0 * K + 0.08, 0.14, 1.0 * K + 0.3, fill=STEEL_D, outline=OUTLINE, width=0.02)
        c.line([(-0.1, 1.0 * K + 0.2), (0.1, 1.0 * K + 0.2)], fill=BRASS_L, width=0.02)
        c.line([(-0.1, 1.0 * K + 0.14), (0.1, 1.0 * K + 0.14)], fill=BRASS_L, width=0.02)
        tag(p, 1.0 * K + 0.36, "RELAY", 0.3)

    elif kind == "route_map":
        # Kartentisch: Holzgestell, aufgespannte Streckenkarte mit Routenlinie, Kompass, Zirkel
        top = stand(p, 1.1, 0.7, 0.8, OAK_D)
        c.poly([(-0.55, top), (0.55, top), (0.55, 0.7 + 0.8 * K), (-0.55, 0.7 + 0.8 * K)], fill=OAK, outline=OUTLINE, width=0.03)
        c.rect(-0.48, top + 0.05, 0.48, 0.7 + 0.8 * K - 0.05, fill=PAPER, outline=OUTLINE, width=0.015)
        for k in range(6):
            c.line([(-0.48, top + 0.09 + k * 0.05), (0.48, top + 0.09 + k * 0.05)], fill=(200, 184, 140, 255), width=0.006)
        for k in range(8):
            c.line([(-0.42 + k * 0.12, top + 0.05), (-0.42 + k * 0.12, 0.7 + 0.8 * K - 0.05)], fill=(200, 184, 140, 255), width=0.006)
        pts = [(-0.42, top + 0.1), (-0.2, top + 0.2), (0.02, top + 0.14), (0.22, top + 0.3), (0.42, top + 0.26)]
        c.line(pts, fill=(170, 44, 50, 255), width=0.02)
        for q in pts:
            c.ellipse(q[0], q[1], 0.018, 0.018, fill=CREAM, outline=INK, width=0.008)
        c.ellipse(0.36, top + 0.1, 0.05, 0.05, fill=CREAM, outline=INK, width=0.01)
        c.line([(0.36, top + 0.06), (0.36, top + 0.14)], fill=(170, 44, 50, 255), width=0.01)
        c.line([(-0.3, top + 0.28), (-0.22, top + 0.1)], fill=INK, width=0.012)
        c.line([(-0.3, top + 0.28), (-0.36, top + 0.1)], fill=INK, width=0.012)
        c.glow(0, top + 0.25, 0.5, WARM, 0.3)
        tag(p, 0.35 * K, "ROUTE", 0.3)

    elif kind == "headlamp_ctrl":
        # Scheinwerfer-Richtstand: Saeule mit Handrad, Zielkreuz-Scheibe und Lampenanzeige
        top = post(p, 0.7, BRASS_D, 0.04, 0.16)
        c.rect(-0.22, top, 0.22, top + 0.36, fill=IRON, outline=OUTLINE, width=0.025)
        c.ellipse(0, top + 0.19, 0.13, 0.13, fill=(40, 60, 90, 255), outline=BRASS, width=0.02)
        c.line([(-0.1, top + 0.19), (0.1, top + 0.19)], fill=(150, 220, 255, 255), width=0.01)
        c.line([(0, top + 0.09), (0, top + 0.29)], fill=(150, 220, 255, 255), width=0.01)
        c.ellipse(0.03, top + 0.22, 0.03, 0.03, fill=BULB, outline=OUTLINE, width=0.008)
        c.glow(0.03, top + 0.22, 0.12, WARM, 0.5)
        S.handwheel(c, 0.3, top + 0.12, 0.09, 0.09, BRASS, spokes=4, w=0.014, rot=20)
        S.handwheel(c, -0.3, top + 0.12, 0.09, 0.09, BRASS, spokes=4, w=0.014, rot=65)
        tag(p, top - 0.08, "HEADLAMP", 0.42)

    elif kind == "stamp_desk":
        # Poststempel-Pult: Holzpult, Stempelkissen, Datumsstempel, Postausweis im Schlitz
        top = stand(p, 0.6, 0.4, 0.9, tint)
        c.poly([(-0.3, top), (0.3, top), (0.3, 0.4 + 1.0 * K), (-0.3, 0.4 + 1.0 * K)], fill=OAK, outline=OUTLINE, width=0.03)
        c.rect(-0.22, top + 0.06, -0.04, top + 0.18, fill=(60, 40, 90, 255), outline=OUTLINE, width=0.012)
        c.rect(-0.2, top + 0.08, -0.06, top + 0.16, fill=(90, 60, 130, 255))
        c.rect(0.04, top + 0.04, 0.2, top + 0.1, fill=WOOD_X, outline=OUTLINE, width=0.012)
        c.rect(0.09, top + 0.1, 0.15, top + 0.24, fill=BRASS, outline=OUTLINE, width=0.012)
        c.ellipse(0.12, top + 0.26, 0.04, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.012)
        c.rect(-0.26, top + 0.22, 0.0, top + 0.3, fill=IRON, outline=OUTLINE, width=0.012)
        c.rect(-0.22, top + 0.24, -0.04, top + 0.42, fill=PAPER, outline=OUTLINE, width=0.01)
        c.rect(-0.2, top + 0.36, -0.06, top + 0.4, fill=(170, 44, 50, 255))
        c.ellipse(-0.13, top + 0.3, 0.025, 0.025, fill=(60, 40, 90, 255))
        tag(p, 0.45 * K, "MAIL PASS", 0.46)

    elif kind == "boiler_panel":
        # Kesselanlage anheizen: Messingtafel mit 3 x 3 Knoepfen, Manometer, Zuendlampe
        top = stand(p, 0.7, 0.35, 0.5, tint)
        panel(p, 0, top, 0.66, 0.6, (56, 50, 46, 255))
        for r in range(3):
            for col_ in range(3):
                x, y = -0.14 + col_ * 0.14, top + 0.1 + r * 0.13
                c.ellipse(x, y, 0.045, 0.045, fill=BRASS_D, outline=OUTLINE, width=0.012)
                c.ellipse(x, y, 0.03, 0.03, fill=(255, 190, 80, 255) if (r * 3 + col_) in (0, 4) else BRASS, outline=OUTLINE, width=0.008)
        S.gauge(c, 0.26, top + 0.48, 0.055, 40, w=0.01)
        lamp_small(c, -0.26, top + 0.48, RED_LAMP, 0.02)
        tag(p, 0.25 * K, "FIRE UP", 0.34)

    elif kind == "valves_panel":
        # Dampfventile oeffnen: Tafel mit zehn nummerierten Ventilgriffen
        top = stand(p, 0.8, 0.35, 0.5, tint)
        panel(p, 0, top, 0.76, 0.56, STEEL_D, rim=BRASS_D)
        n = 0
        for r in range(2):
            for col_ in range(5):
                x, y = -0.28 + col_ * 0.14, top + 0.16 + r * 0.24
                n += 1
                S.pipe(c, [(x, y - 0.08), (x, y + 0.08)], 0.018, BRASS_D, flange=False)
                S.handwheel(c, x, y, 0.045, 0.045, (190, 50, 44, 255) if n % 3 else (60, 110, 190, 255), spokes=4, w=0.008, rot=n * 23)
                c.textf(x, y - 0.11, str(n), 0.035, CREAM, kind="black")
        tag(p, 0.25 * K, "MANIFOLDS", 0.44)

    elif kind == "bigvalve":
        # Ueberdruck: grosses rotes Handrad an dickem Dampfrohr, Handabdruck-Schild, Warnlampe
        stand(p, 0.5, 0.3, 0.2, tint)
        S.pipe(c, [(0, 0.2 * K + 0.1), (0, 0.2 * K + 0.9)], 0.07, BRASS_D, flange=True)
        S.pipe(c, [(-0.3, 0.2 * K + 0.5), (0.3, 0.2 * K + 0.5)], 0.045, BRASS_D, flange=True)
        S.handwheel(c, 0, 0.2 * K + 0.5, 0.26, 0.26, (200, 50, 44, 255), spokes=6, w=0.03)
        c.rect(-0.1, 0.2 * K + 0.95, 0.1, 0.2 * K + 1.12, fill=CREAM, outline=OUTLINE, width=0.015)
        c.ellipse(0, 0.2 * K + 1.02, 0.05, 0.05, fill=(200, 50, 44, 255))
        for k in range(4):
            c.ellipse(-0.03 + k * 0.02, 0.2 * K + 1.08 + 0.01 * (k % 2), 0.008, 0.016, fill=(200, 50, 44, 255))
        lamp_small(c, 0.2, 0.2 * K + 1.0, RED_LAMP, 0.028)
        for k in range(3):
            c.ellipse(0.1 + k * 0.06, 0.2 * K + 0.86 + k * 0.05, 0.03 + k * 0.01, 0.025 + k * 0.01, fill=alpha(WHITE, 120 - k * 30))
        tag(p, 0.2 * K + 0.2, "PRESSURE", 0.42)

    elif kind == "searchlight":
        # Suchscheinwerfer am Umlauf: Messingsockel, Kurbel, Lampe mit Lichtkegel
        p.cyl(0, 0.25, 0.26, 0, 0.45, shade(IRON_L, 1.2), IRON_L, ry=0.13)
        c.rect(-0.05, 0.25 + 0.45 * K, 0.05, 0.25 + 0.95 * K, fill=BRASS, outline=OUTLINE, width=0.02)
        c.poly([(-0.22, 0.25 + 1.0 * K), (0.28, 0.25 + 1.0 * K), (0.3, 0.25 + 1.0 * K + 0.3), (-0.2, 0.25 + 1.0 * K + 0.3)],
               fill=IRON, outline=OUTLINE, width=0.03)
        c.glow(0.42, 0.25 + 1.0 * K + 0.15, 0.6, WARM, 0.6)
        c.ellipse(0.32, 0.25 + 1.0 * K + 0.15, 0.08, 0.17, fill=BULB, outline=OUTLINE, width=0.025)
        c.ellipse(0.34, 0.25 + 1.0 * K + 0.17, 0.03, 0.07, fill=WHITE)
        c.line([(-0.22, 0.25 + 1.0 * K + 0.28), (-0.32, 0.25 + 1.0 * K + 0.4)], fill=OUTLINE, width=0.035)
        c.line([(-0.22, 0.25 + 1.0 * K + 0.28), (-0.32, 0.25 + 1.0 * K + 0.4)], fill=BRASS, width=0.018)
        c.ellipse(-0.32, 0.25 + 1.0 * K + 0.4, 0.03, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.012)
        S.handwheel(c, -0.12, 0.25 + 0.6 * K, 0.08, 0.05, BRASS, spokes=4, w=0.012)
        tag(p, 0.25 + 0.22 * K, "LINE CLEAR", 0.44)

    elif kind == "tea_trolley":
        # Teewagen: zwei Ebenen auf Raedern, Teekanne, Tassen, Kuchen, Probierkarte
        for lx in (-0.42, 0.42):
            c.ellipse(lx, 0.1, 0.07, 0.04, fill=IRON, outline=OUTLINE, width=0.02)
        for lz in (0.4, 0.85):
            p.box(-0.5, 0.08, 0.5, 0.55, lz, 0.05, OAK, OAK_D, w=0.03)
        for lx in (-0.46, 0.46):
            c.line([(lx, 0.1), (lx, 0.55 + 0.9 * K)], fill=OUTLINE, width=0.035)
            c.line([(lx, 0.1), (lx, 0.55 + 0.9 * K)], fill=BRASS, width=0.018)
        top = 0.08 + 0.9 * K
        c.ellipse(-0.2, top + 0.12, 0.13, 0.1, fill=(230, 230, 236, 255), outline=OUTLINE, width=0.02)
        c.ellipse(-0.2, top + 0.2, 0.05, 0.03, fill=(230, 230, 236, 255), outline=OUTLINE, width=0.015)
        c.line([(-0.33, top + 0.14), (-0.42, top + 0.2)], fill=OUTLINE, width=0.03)
        c.line([(-0.07, top + 0.12), (0.0, top + 0.18)], fill=OUTLINE, width=0.025)
        for k in range(3):
            c.ellipse(0.1 + k * 0.13, top + 0.08 + 0.03 * (k % 2), 0.05, 0.035, fill=WHITE, outline=OUTLINE, width=0.015)
            c.ellipse(0.1 + k * 0.13, top + 0.08 + 0.03 * (k % 2), 0.03, 0.018, fill=(150, 100, 60, 255))
        c.rect(0.05, top + 0.2, 0.4, top + 0.3, fill=(214, 160, 90, 255), outline=OUTLINE, width=0.015)
        c.rect(0.05, top + 0.3, 0.4, top + 0.34, fill=(240, 220, 200, 255), outline=OUTLINE, width=0.01)
        lowt = 0.08 + 0.45 * K
        c.rect(-0.3, lowt + 0.06, 0.2, lowt + 0.18, fill=PAPER, outline=OUTLINE, width=0.012)
        c.textf(-0.05, lowt + 0.12, "TASTE TEST", 0.04, INK, kind="black")

    elif kind == "inspection_gate":
        # Fahrkartenkontrolle: Messingring am Boden, Torbogen mit Laterne, Schild "TICKETS PLEASE"
        c.soft_shadow([(-0.6, -0.05), (0.6, -0.05), (0.6, 0.5), (-0.6, 0.5)], 70, 0.08)
        gy = 0.2
        c.ellipse(0, gy, 0.58, 0.2, fill=(100, 70, 60, 255), outline=OUTLINE, width=0.035)
        c.ellipse(0, gy, 0.5, 0.16, fill=(150, 44, 56, 255), outline=BRASS, width=0.03)
        c.glow(0, gy, 0.5, (120, 220, 255, 255), 0.25)
        c.ellipse(0, gy, 0.2, 0.07, outline=alpha(BRASS, 180), width=0.015)
        for sx in (-1, 1):
            c.line([(sx * 0.5, gy), (sx * 0.5, gy + 1.3 * K)], fill=OUTLINE, width=0.07)
            c.line([(sx * 0.5, gy), (sx * 0.5, gy + 1.3 * K)], fill=BRASS, width=0.04)
            c.ellipse(sx * 0.5, gy, 0.08, 0.04, fill=BRASS_D, outline=OUTLINE, width=0.02)
        arch = S.ellipse_pts(0, gy + 1.3 * K, 0.5, 0.28, 24, 0, 180)
        c.line(arch, fill=OUTLINE, width=0.07)
        c.line(arch, fill=BRASS, width=0.04)
        S.lantern(c, 0, gy + 1.3 * K + 0.1, 0.9, (255, 240, 200, 255), on=True)
        S.plate(c, 0, gy + 1.3 * K - 0.08, 0.56, 0.09, "TICKETS PLEASE", size=0.05)

    elif kind == "smoke_damper":
        # Rauchklappe: Eisenkasten mit Kurbel, Zugkette, Rauch, rote Warnlampe, Schild VENT
        top = stand(p, 0.6, 0.35, 0.8, tint)
        c.rect(-0.24, 0.1, 0.24, 0.8 * K - 0.05, fill=IRON, outline=OUTLINE, width=0.02)
        for k in range(4):
            c.rect(-0.2, 0.15 + k * 0.08, 0.2, 0.19 + k * 0.08, fill=(30, 28, 32, 255))
        S.handwheel(c, 0.3, 0.28, 0.1, 0.07, BRASS, spokes=3, w=0.014)
        c.line([(-0.3, 0.12), (-0.3, 0.8 * K + 0.3)], fill=(90, 90, 100, 255), width=0.012)
        for k in range(8):
            c.ellipse(-0.3, 0.14 + k * 0.08, 0.012, 0.018, outline=(120, 120, 130, 255), width=0.006)
        c.ellipse(-0.3, 0.8 * K + 0.32, 0.03, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.012)
        lamp_small(c, 0.0, top + 0.06, RED_LAMP, 0.03)
        for k in range(3):
            c.ellipse(0.05 + k * 0.08, top + 0.2 + k * 0.1, 0.05 + k * 0.02, 0.04 + k * 0.015, fill=alpha((120, 120, 130, 255), 110 - k * 25))
        tag(p, 0.35 * K, "SMOKE VENT", 0.5)

    elif kind == "hood_filter":
        # Dunstabzug-Filter: Edelstahlrahmen mit Filtergitter, Fettspritzer, Buerste
        top = stand(p, 0.7, 0.3, 0.3, STEEL_L)
        panel(p, 0, top, 0.66, 0.5, STEEL_D, rim=STEEL_L)
        for r in range(2):
            for col_ in range(3):
                x0, y0 = -0.3 + col_ * 0.21, top + 0.05 + r * 0.22
                c.rect(x0, y0, x0 + 0.18, y0 + 0.18, fill=(60, 66, 76, 255), outline=OUTLINE, width=0.01)
                for k in range(6):
                    c.line([(x0 + 0.015, y0 + 0.02 + k * 0.028), (x0 + 0.165, y0 + 0.02 + k * 0.028)], fill=(130, 138, 150, 255), width=0.006)
        for k in range(8):
            c.ellipse(rnd.uniform(-0.28, 0.28), rnd.uniform(top + 0.06, top + 0.44), rnd.uniform(0.012, 0.03), rnd.uniform(0.01, 0.02),
                      fill=(150, 120, 60, 200))
        c.line([(0.38, 0.05), (0.52, 0.4)], fill=OUTLINE, width=0.045)
        c.line([(0.38, 0.05), (0.52, 0.4)], fill=OAK_D, width=0.022)
        c.rect(0.33, 0.0, 0.46, 0.08, fill=(200, 180, 120, 255), outline=OUTLINE, width=0.015)
        tag(p, 0.15 * K, "HOOD FILTER", 0.5)

    else:
        stand(p, 0.6, 0.4, 0.9, tint)
        tag(p, 0.45 * K, kind.upper(), 0.5)

    img = c.finish()
    return img, (0 - c.x0) * ppm, (0 - c.y0) * ppm


def render_all(ctx, ppm):
    out = {}
    for i, key in enumerate(sorted(ctx["consoles"])):
        sysname = key.split("/")[0]
        kind = device_kind(key, sysname)
        img, ax, ay = draw_device(kind, sysname, i, ppm)
        out[key] = (img, ax, ay)
    return out
