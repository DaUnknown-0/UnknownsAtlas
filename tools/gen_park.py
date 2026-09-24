# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_park.py - Moonlight Carnival, GRAYBOX (docs/PARK_KONZEPT.md, Schritt 3): park_layout.py ->
# Bodenkacheln, Objekte, Minimap, src/AtlasParkData.cs und src/AtlasParkLayout.cs (gleiches
# Format wie Museum und Wald).
#
#   python tools/gen_park.py
#
# Bewusst schlicht: flache Farbflaechen je Bereich, klare Waende, Namen auf dem Boden, Hindernisse
# als einfarbige Bloecke. Niedrige Aufloesung (40 px/m), damit die Graybox die DLL kaum vergroessert.
# Die eigentliche Grafik (Stilblatt, Props, Licht) kommt in Schritt 6 und ersetzt diese Datei.

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import Point, LineString, box
from shapely.affinity import translate
from shapely.ops import unary_union

import museum_art as A
import park_art as PA
import park_floor as PF
import park_layout as L
import park_geo as G

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ASSETS = PROJECT / "assets"
OUT_DATA = PROJECT / "src" / "AtlasParkData.cs"
OUT_LAYOUT = PROJECT / "src" / "AtlasParkLayout.cs"
PREVIEW = HERE / "_park"

FLOOR_PPM = 80                  # Park-Grafik (park_floor.py); Museum/Wald 160, der Park ist doppelt so gross
FLOOR_TILES = (4, 3)            # je Kachel unter 2048 px
LAMPS, LAMP_PIVOT = [], (0.5, 0.1)
PROP_PPM = 160                  # wie Museum und Wald (Stilblatt: echte Objekte)
BX0, BY0, BX1, BY1 = L.BOUNDS

VOID = (18, 20, 32)
GROUND = (112, 108, 100)       # Pflaster zwischen den Bereichen
WALL_TOP = (46, 40, 52)
RAIL_COL = (150, 84, 40)
CROSS_COL = (240, 200, 40)
WATER_COL = (44, 96, 150)
BRIDGE_COL = (140, 110, 80)
TURN_COL = (40, 200, 200)
ROOM_COL = {   # je Bereich eine eigene Graybox-Farbe
    "fairground": (176, 150, 112), "workshop": (130, 120, 104), "carousel": (170, 120, 150),
    "bumpercars": (120, 130, 160), "security": (110, 120, 130), "substation": (140, 140, 110),
    "firstaid": (190, 190, 190), "office": (160, 140, 110), "coldstore": (150, 180, 200),
    "musicbooth": (150, 110, 160), "shooting": (170, 130, 90), "mirrors": (160, 190, 200),
    "ghosttrain": (70, 60, 80), "ferriswheel": (120, 150, 110), "lighttower": (150, 150, 100),
    "coaster": (160, 110, 90), "maingate": (130, 150, 130), "logflume": (110, 150, 140),
}
KIND_COL = {
    "tunnelwand": (40, 34, 46), "bude": (190, 80, 70), "radnabe": (90, 90, 100), "turm": (200, 190, 120),
    "karussell": (200, 110, 170), "kasse": (180, 150, 90), "kassenhaeuschen": (180, 150, 90),
    "kuehltruhe": (200, 220, 235), "regal": (110, 90, 70), "lautsprecher": (60, 60, 70),
    "riesenrad": (170, 190, 210), "theke": (160, 110, 70), "arena": (100, 120, 170), "zaun": (150, 150, 160),
    "mischpult": (90, 80, 110), "liege": (230, 230, 230), "spiegel": (190, 225, 240),
}


def geom_parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def label_point(g, name=""):
    """Stelle fuer den Raumnamen: moeglichst nah an der Raummitte, der ganze Schriftzug frei von
    Hindernissen und Waenden (vorher lag "Carousel" unter dem Karussell bzw. in einer Ecke)."""
    obst = unary_union([G.shape(s) for s, _k in L.OPAQUE + L.GLASS]).buffer(0.3)
    free = g.buffer(-0.3).difference(obst)
    half_w, half_h = max(1.0, len(name) * 0.26), 0.55
    c = g.centroid
    best, best_d = None, 1e9
    x0, y0, x1, y1 = g.bounds
    steps = 40
    for i in range(steps + 1):
        for j in range(steps + 1):
            px, py = x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps
            if not free.contains(box(px - half_w, py - half_h, px + half_w, py + half_h)):
                continue
            dd = (px - c.x) ** 2 + (py - c.y) ** 2
            if dd < best_d:
                best, best_d = Point(px, py), dd
    return best if best is not None else g.representative_point()


# ------------------------------------------------------------------ Boden

def render_floor(walk, water, shells, doors, rooms):
    img = PF.render(walk, water, shells, doors, rooms, FLOOR_PPM)
    return save_floor(img)


def render_floor_graybox(walk, water, shells, doors, rooms):
    ww, hh = int((BX1 - BX0) * FLOOR_PPM), int((BY1 - BY0) * FLOOR_PPM)
    img = Image.new("RGB", (ww, hh), VOID)
    d = ImageDraw.Draw(img, "RGBA")
    Pt = lambda x, y: ((x - BX0) * FLOOR_PPM, (BY1 - y) * FLOOR_PPM)

    def poly(g, fill, outline=None, width=1):
        for p in geom_parts(g):
            d.polygon([Pt(*q) for q in p.exterior.coords], fill=fill, outline=outline)
            for h in p.interiors:
                d.polygon([Pt(*q) for q in h.coords], fill=VOID)

    poly(walk, GROUND)
    for key, (name, _s, g) in rooms.items():
        poly(g.intersection(walk), ROOM_COL.get(key, (140, 140, 140)))
    # Raster zur Orientierung (1 m)
    for x in range(int(BX0), int(BX1) + 1):
        d.line([Pt(x, BY0), Pt(x, BY1)], fill=(0, 0, 0, 22), width=1)
    for y in range(int(BY0), int(BY1) + 1):
        d.line([Pt(BX0, y), Pt(BX1, y)], fill=(0, 0, 0, 22), width=1)
    # Wasser, Bruecken, Strecke, Uebergaenge, Drehkreuze
    poly(water, WATER_COL)
    for s in L.BRIDGES:
        poly(G.shape(s), BRIDGE_COL)
    for s in L.RAIL:
        poly(G.shape(s), RAIL_COL)
    for _k, s, direction in L.CROSSINGS:
        g = G.shape(s)
        poly(g, CROSS_COL)
        x0, y0, x1, y1 = g.bounds
        # Schwellen quer zur Fahrtrichtung
        if direction == "vertical":
            for i in range(1, 4):
                y = y0 + (y1 - y0) * i / 4
                d.line([Pt(x0, y), Pt(x1, y)], fill=(40, 30, 20), width=3)
        else:
            for i in range(1, 4):
                x = x0 + (x1 - x0) * i / 4
                d.line([Pt(x, y0), Pt(x, y1)], fill=(40, 30, 20), width=3)
    for kind, s in L.TURNSTILES:
        g = G.shape(s)
        poly(g, TURN_COL)
        c = g.centroid
        dy = 0.9 if kind == "in" else -0.9       # Pfeil: hinein = nach Norden
        d.line([Pt(c.x, c.y - dy), Pt(c.x, c.y + dy)], fill=(255, 255, 255), width=4)
        d.polygon([Pt(c.x, c.y + dy * 1.5), Pt(c.x - 0.4, c.y + dy), Pt(c.x + 0.4, c.y + dy)], fill=(255, 255, 255))
    # Waende: Gebaeudehuellen ohne Innenraum und Oeffnungen
    openings = unary_union([o for *_r, o in doors])
    for s, (_k, _n, _sy, inner, _d) in zip(shells, L.BUILDINGS):
        wall = s.difference(box(*inner)).difference(openings)
        poly(wall, WALL_TOP)
    # Namen auf dem Boden
    try:
        font = ImageFont.truetype("arialbd.ttf", int(FLOOR_PPM * 0.9))
    except OSError:
        font = ImageFont.load_default()
    for key, (name, _s, g) in rooms.items():
        c = label_point(g, name)
        d.text(Pt(c.x, c.y), name, font=font, fill=(255, 255, 255, 110), anchor="mm")
    return save_floor(img)


def save_floor(img):
    PREVIEW.mkdir(exist_ok=True)
    img.save(PREVIEW / "floor_preview.jpg", quality=85)
    for old in ASSETS.glob("park_floor_*.jpg"):
        old.unlink()
    cols, rows = FLOOR_TILES
    tw = (img.width // cols) // 4 * 4
    th = (img.height // rows) // 4 * 4
    tiles = []
    i = 0
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * tw, r * th
            x1 = img.width if c == cols - 1 else x0 + tw
            y1 = img.height if r == rows - 1 else y0 + th
            w4, h4 = (x1 - x0) // 4 * 4, (y1 - y0) // 4 * 4
            img.crop((x0, y0, x0 + w4, y0 + h4)).save(ASSETS / f"park_floor_{i}.jpg", quality=85)
            tiles.append((i, BX0 + x0 / FLOOR_PPM, BY1 - (y0 + h4) / FLOOR_PPM, w4, h4))
            i += 1
    print(f"floor {img.width}x{img.height} in {len(tiles)} tiles")
    return tiles


# ------------------------------------------------------------------ Objekte (Graybox-Bloecke)

def draw_block(kind, s, idx=0):
    if kind in PA.KINDS:                     # Stilblatt: schon im Park-Stil gezeichnet (park_art.py)
        return PA.draw(kind, s, idx, PROP_PPM)
    g = G.shape(s)
    x0, y0, x1, y1 = g.bounds
    pad = 0.1
    w = max(1, int((x1 - x0 + 2 * pad) * PROP_PPM))
    h = max(1, int((y1 - y0 + 2 * pad) * PROP_PPM))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    Pt = lambda x, y: ((x - x0 + pad) * PROP_PPM, (y1 + pad - y) * PROP_PPM)
    col = KIND_COL.get(kind, (150, 150, 150))
    glass = any(k == kind for _s, k in L.GLASS)
    fill = col + ((150,) if glass else (255,))
    d.polygon([Pt(*q) for q in g.exterior.coords], fill=fill, outline=(20, 20, 26, 255))
    return im, x0 - pad, y0 - pad, y0


def render_props():
    items = [(s, k) for s, k in L.OPAQUE] + [(s, k) for s, k in L.GLASS]
    images, meta = [], []
    for i, (s, kind) in enumerate(items):
        im, wx, wy, base = draw_block(kind, s, i)
        images.append((i, im))
        fx0, _, fx1, _ = A.shape_bounds(s)
        meta.append((kind, wx, wy, base, fx0, fx1))
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for old in ASSETS.glob("park_props_*.png"):
        old.unlink()
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"park_props_{k}.png", optimize=True)
    out = []
    for i, (kind, wx, wy, base, fx0, fx1) in enumerate(meta):
        page, x, y, ww, hh = placed[i]
        out.append((kind, page, x, atlases[page].height - y - hh, ww, hh, wx, wy, base, fx0, fx1))
    print(f"props {len(out)} in {len(atlases)} atlas(es)")
    return out


# ------------------------------------------------------------------ Konsolen (wie gen_wald.py)

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


def place_consoles(walk, rooms, doors, obstacles):
    placed = {}
    free = walk.difference(unary_union(obstacles).buffer(0.5)).buffer(0)
    edge = walk.boundary
    taken = [Point(p) for p in list(L.FIXED.values()) + [L.EMERGENCY, L.SURVEILLANCE, L.ADMIN_TABLE, L.FREEPLAY, L.SPAWN]]
    taken += [Point(p) for p in L.VENTS.values()] + [Point(p) for p in L.CAMERAS]
    door_pts = [o.centroid for *_r, o in doors]
    ends = []
    clearing_keys = [c[0] for c in L.CLEARINGS]
    for pts in L.PATHS:
        ls = LineString(pts)
        for rk, (_n, _s, g) in rooms.items():
            if rk not in clearing_keys:
                continue
            ix = ls.intersection(g.exterior)
            ends.extend([ix] if ix.geom_type == "Point" else list(getattr(ix, "geoms", [])))
    path_ends = unary_union(ends) if ends else Point(1e6, 1e6)
    for key, (name, sysname, g) in rooms.items():
        keys = [k for k in SKELD_CONSOLES.get(sysname, []) if k not in L.FIXED]
        ring = g.buffer(-0.55)
        cands = []
        for part in geom_parts(ring):
            line = part.exterior
            n = max(16, int(line.length / 0.3))
            for i in range(n):
                p = line.interpolate(i / n, normalized=True)
                if edge.distance(p) > 0.75 or not free.contains(p):
                    continue
                if min([p.distance(q) for q in door_pts] + [99]) < 1.6:
                    continue
                if path_ends.distance(p) < 2.0:
                    continue
                cands.append(p)
        chosen = []
        for k in keys:
            best, score = None, -1e9
            for p in cands:
                dd = min([p.distance(q) for q in chosen + taken] + [99])
                if dd < 1.3:
                    continue
                sc = min(dd, 4.0) + 0.15 * (p.y - g.centroid.y)   # Nordwand bevorzugt
                if sc > score:
                    best, score = p, sc
            if best is None:
                best = g.representative_point()
                print(f"WARN no spot for {k} in {name}")
            chosen.append(best)
            placed[k] = (round(best.x, 2), round(best.y, 2))
        taken.extend(chosen)
    for k, p in L.FIXED.items():
        placed[k] = p
    return placed


# ------------------------------------------------------------------ Minimap

def render_consoles(consoles):
    """Task-Bloecke (park_consoles.py, Baukasten aus wald_consoles.py) in Atlanten packen."""
    import park_consoles as PC
    sprites = PC.render_all(PROP_PPM, consoles)
    for old in ASSETS.glob("park_consoles_*.png"):
        old.unlink()
    keys = sorted(sprites)
    images = [(i, sprites[k][0].filter(ImageFilter.GaussianBlur(0.45))) for i, k in enumerate(keys)]
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"park_consoles_{k}.png", optimize=True)
    out = []
    for i, key in enumerate(keys):
        page, x, y, w, h = placed[i]
        _im, ax, ay = sprites[key]
        out.append((key, page, x, atlases[page].height - y - h, w, h, ax / w, ay / h))
    print(f"consoles {len(out)} sprites in {len(atlases)} atlas(es)")
    return out


def minimap(walk, rooms):
    s = 24
    ww, hh = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    Pt = lambda x, y: ((x - BX0) * s, (BY1 - y) * s)
    for p in geom_parts(walk):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=(224, 214, 236, 235))
        for h in p.interiors:
            d.polygon([Pt(*q) for q in h.coords], fill=(0, 0, 0, 0))
    for p in geom_parts(walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([Pt(*q) for q in ring.coords], fill=(30, 22, 44, 255), width=4, joint="curve")
    try:
        font = ImageFont.truetype("arialbd.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for key, (name, _s, g) in rooms.items():
        c = label_point(g, name)
        d.text(Pt(c.x, c.y), name, font=font, fill=(30, 22, 44, 255), anchor="mm")
    img.save(ASSETS / "park_minimap.png", optimize=True)


# ------------------------------------------------------------------ C#

def v2(p):
    return f"new({p[0]:.3f}f, {p[1]:.3f}f)"


def chain(points):
    return "new Vector2[] { " + ", ".join(v2(p) for p in points) + " }"


def rings_of(g):
    out = []
    for p in geom_parts(g):
        out.append(list(p.exterior.coords)[:-1])
        for h in p.interiors:
            out.append(list(h.coords)[:-1])
    return out


def header(a, what):
    a("// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0")
    a("// Licensed under GPL-3.0-or-later. See LICENSE for details.")
    a("//")
    a("// AUTOMATISCH ERZEUGT von tools/gen_park.py aus tools/park_layout.py - NICHT VON HAND AENDERN.")
    a(f"// {what}")
    a("")
    a("using System.Collections.Generic;")
    a("using UnityEngine;")
    a("")
    a("namespace UnknownsAtlas;")
    a("")


def emit(walk, water, rooms, doors, tiles, props, consoles, console_sprites=()):
    full = box(BX0 - 5, BY0 - 5, BX1 + 5, BY1 + 5)
    solid = full.difference(walk)
    move = walk.difference(translate(solid, 0, -0.3)).buffer(0)
    # Wasser und Achterbahn sperren den Weg, nicht die Sicht
    rail = G.rail_block()
    shadow = unary_union([walk, translate(walk, 0, 0.45), water, rail]).buffer(0)
    opaque = [G.shape(s) for s, _k in L.OPAQUE]
    glass = [G.shape(s) for s, _k in L.GLASS]
    edges = unary_union([LineString(r + [r[0]]) for r in rings_of(walk)])
    casts = [p.distance(edges) > 0.08 for p in opaque]
    room_u = unary_union([g for _n, _s, g in rooms.values()])
    rest = walk.difference(room_u).buffer(0)
    halls = [g for g in geom_parts(rest) if g.area > 1.0]

    Ls = []
    a = Ls.append
    header(a, "Moonlight Carnival (Graybox): Geometrie, Raeume, Bodenkacheln, Objekte (Weltmeter).")
    a("public static class AtlasParkData")
    a("{")
    a(f"    public const float MinX = {BX0:.2f}f, MinY = {BY0:.2f}f, MaxX = {BX1:.2f}f, MaxY = {BY1:.2f}f;")
    for name, g in (("Walls", move), ("ShadowWalls", shadow)):
        a(f"    public static readonly Vector2[][] {name} =\n    {{")
        for r in rings_of(g):
            a(f"        {chain(r)},")
        a("    };")
    a("    public static readonly Vector2[][] Opaque =\n    {")
    for p in opaque:
        a(f"        {chain(list(p.exterior.coords)[:-1])},")
    a("    };")
    a("    public static readonly bool[] OpaqueCastsShadow = { " + ", ".join("true" if c else "false" for c in casts) + " };")
    a("    public static readonly Vector2[][] Glass =\n    {")
    for p in glass:
        a(f"        {chain(list(p.exterior.coords)[:-1])},")
    a("    };")
    a("    public static readonly (string Key, string Name, SystemTypes Room, Vector2[] Area)[] Rooms =\n    {")
    for key, (name, sysname, g) in rooms.items():
        a(f"        (\"{key}\", \"{name}\", SystemTypes.{sysname}, {chain(list(g.exterior.coords)[:-1])}),")
    a("    };")
    a("    public static readonly Vector2[][] Hallways =\n    {")
    for h in halls:
        a(f"        {chain(list(h.exterior.coords)[:-1])},")
    a("    };")
    a(f"    public const float FloorPixelsPerMeter = {FLOOR_PPM}f;")
    a("    public static readonly (int Index, float WorldX, float WorldY, int W, int H)[] FloorTiles =\n    {")
    for i, wx, wy, ww, hh in tiles:
        a(f"        ({i}, {wx:.4f}f, {wy:.4f}f, {ww}, {hh}),")
    a("    };")
    a(f"    public const float PropPixelsPerMeter = {PROP_PPM}f;")
    a("    public static readonly (string Kind, int Atlas, int X, int Y, int W, int H, float WorldX, float WorldY, float BaseY, float FootX0, float FootX1)[] Props =\n    {")
    for kind, page, x, y, ww, hh, wx, wy, base, fx0, fx1 in props:
        a(f"        (\"{kind}\", {page}, {x}, {y}, {ww}, {hh}, {wx:.3f}f, {wy:.3f}f, {base:.3f}f, {fx0:.3f}f, {fx1:.3f}f),")
    a("    };")
    a("    public static readonly (string Key, int Atlas, int X, int Y, int W, int H, float PivotX, float PivotY)[] ConsoleSprites =")
    a("    {")
    for key, page, x, y, ww, hh, px, py in console_sprites:
        a(f"        (\"{key}\", {page}, {x}, {y}, {ww}, {hh}, {px:.4f}f, {py:.4f}f),")
    a("    };")
    a("}")
    OUT_DATA.write_text("\n".join(Ls) + "\n", encoding="utf-8")

    group = {b[0]: b[2] for b in L.BUILDINGS}
    vert, hori = [], []
    for key, side, a0, b0, kind, o in doors:
        if kind != "door":
            continue
        c = o.centroid
        slot = (f"{key}-{side}", c.x, c.y, b0 - a0, group[key])
        (vert if side in "EW" else hori).append(slot)

    Ls = []
    a = Ls.append
    header(a, "Moonlight Carnival (Graybox): Plaetze der Skeld-Mechanik (Weltmeter).")
    a("internal static class AtlasParkLayout")
    a("{")
    a("    public static readonly Dictionary<string, Vector2> Consoles = new()\n    {")
    for k, p in sorted(consoles.items()):
        a(f"        [\"{k}\"] = {v2(p)},")
    a("    };")
    for name, p in (("EmergencyButton", L.EMERGENCY), ("SurveillanceConsole", L.SURVEILLANCE),
                    ("AdminTable", L.ADMIN_TABLE), ("FreeplayLaptop", L.FREEPLAY), ("Spawn", L.SPAWN)):
        a(f"    public static readonly Vector2 {name} = {v2(p)};")
    a(f"    public const float SpawnRadius = {L.SPAWN_RADIUS}f;")
    a("    public static readonly Dictionary<int, Vector2> Vents = new()\n    {")
    for vid, p in L.VENTS.items():
        a(f"        [{vid}] = {v2(p)},")
    a("    };")
    a("    public static readonly int[][] VentNetworks =\n    {")
    for net in L.VENT_NETS:
        a("        new[] { " + ", ".join(map(str, net)) + " },")
    a("    };")
    a("    public static readonly int[][] VentBridges =\n    {")
    for va, vb in L.VENT_BRIDGES:
        a(f"        new[] {{ {va}, {vb} }},")
    a("    };")
    for nm, lst in (("VerticalDoors", vert), ("HorizontalDoors", hori)):
        a(f"    public static readonly AtlasMuseumLayout.DoorSlot[] {nm} =\n    {{")
        for label, cx, cy, length, grp in lst:
            a(f"        new(\"{label}\", {cx:.3f}f, {cy:.3f}f, {length:.2f}f, SystemTypes.{grp}, seeThrough: false),")
        a("    };")
    a("    public static readonly Vector2[] Cameras =\n    {")
    for p in L.CAMERAS:
        a(f"        {v2(p)},")
    a("    };")
    a("    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()\n    {")
    done = set()
    for key, (name, sysname, g) in rooms.items():
        if sysname in ("Cafeteria", "Storage", "UpperEngine", "LowerEngine", "Security", "MedBay",
                       "Electrical", "Reactor", "LifeSupp", "Comms") and sysname not in done:
            c = g.representative_point()
            a(f"        [SystemTypes.{sysname}] = {v2((c.x, c.y + 0.8))},")
            done.add(sysname)
    a("    };")
    a("}")
    a("")
    # Welt-System (AtlasParkWorld): Sperrflaechen, Wege der Fahrgeschaefte, Monitor
    def mm(g):
        x0, y0, x1, y1 = g.bounds
        return f"(new({x0:.3f}f, {y0:.3f}f), new({x1:.3f}f, {y1:.3f}f))"
    a("/// <summary>Park-Welt-System (AtlasParkWorld): Sperrflaechen und Wege der Fahrgeschaefte.</summary>")
    a("internal static class AtlasParkWorldData")
    a("{")
    a("    public static readonly (Vector2 Min, Vector2 Max, bool Vertical)[] Crossings =")
    a("    {")
    for _k, s_, direction in L.CROSSINGS:
        x0, y0, x1, y1 = G.shape(s_).bounds
        a(f"        (new({x0:.3f}f, {y0:.3f}f), new({x1:.3f}f, {y1:.3f}f), {'true' if direction == 'vertical' else 'false'}),")
    a("    };")
    gates = []
    for bkey, side in L.CAROUSEL_GATES:
        b = next(b for b in L.BUILDINGS if b[0] == bkey)
        for sd, a0, b0, _kind in b[4]:
            if sd == side:
                gates.append(G.opening_rect(b[3], sd, a0, b0))
    a("    public static readonly (Vector2 Min, Vector2 Max)[] CarouselGates =")
    a("    {")
    for g in gates:
        a(f"        {mm(g)},")
    a("    };")
    a(f"    public static readonly Vector2 CarouselCenter = {v2(L.CAROUSEL[:2])};")
    a(f"    public const float CarouselRadius = {L.CAROUSEL[2]}f;")
    a(f"    public static readonly (Vector2 Min, Vector2 Max) FlumeBridge = {mm(G.shape(L.BRIDGES[L.FLUME_BRIDGE]))};")
    a("    public static readonly (Vector2 Min, Vector2 Max, bool Inward)[] Turnstiles =")
    a("    {")
    for kind, s_ in L.TURNSTILES:
        x0, y0, x1, y1 = G.shape(s_).bounds
        a(f"        (new({x0:.3f}f, {y0:.3f}f), new({x1:.3f}f, {y1:.3f}f), {'true' if kind == 'in' else 'false'}),")
    a("    };")
    for nm, pts in (("TrackLoop", L.TRACK_LOOP), ("CanalLine", L.CANAL_LINE), ("GhostRide", L.GHOST_RIDE)):
        a(f"    public static readonly Vector2[] {nm} = {chain(pts)};")
    a(f"    public static readonly Vector2 GhostMonitor = {v2(L.GHOST_MONITOR)};")
    a("    /// <summary>Laternen am Weg (Lichtebene, gehen bei Park Blackout aus); Bild task_park_lamppost(_off).png.</summary>")
    a(f"    public static readonly Vector2[] Lamps = {chain(LAMPS)};")
    a(f"    public static readonly Vector2 LampPivot = new({LAMP_PIVOT[0]:.4f}f, {LAMP_PIVOT[1]:.4f}f);")
    a(f"    public const float LampPixelsPerMeter = {PROP_PPM}f;")
    a("}")
    OUT_LAYOUT.write_text("\n".join(Ls) + "\n", encoding="utf-8")
    print(f"doors {len(vert)}V/{len(hori)}H, consoles {len(consoles)}, hallways {len(halls)}, rooms {len(rooms)}")


def main():
    walk, water, shells, doors = G.build()
    rooms = G.rooms(walk)
    obstacles = [G.shape(s) for s, _k in L.OPAQUE] + [G.shape(s) for s, _k in L.GLASS]
    consoles = place_consoles(walk, rooms, doors, obstacles)
    free = walk.difference(unary_union(obstacles).buffer(0.25))
    for k, p in list(consoles.items()) + [("Emergency", L.EMERGENCY), ("Surveillance", L.SURVEILLANCE),
                                          ("Admin", L.ADMIN_TABLE), ("Freeplay", L.FREEPLAY)] + \
                                         [(f"Vent{v}", p) for v, p in L.VENTS.items()] + [(f"Cam{i}", p) for i, p in enumerate(L.CAMERAS)]:
        dd = free.distance(Point(p))
        if dd > 0.6:
            print(f"WARN {k} at {p} not reachable ({dd:.2f} m)")
    tiles = render_floor(walk, water, shells, doors, rooms)
    props = render_props()
    console_sprites = render_consoles(consoles)
    lamps = PF.lamp_points(walk, rooms)
    for on in (True, False):
        im, px, py = PA.lamppost(PROP_PPM, on)
        im.save(ASSETS / f"task_park_lamppost{'' if on else '_off'}.png", optimize=True)
    print(f"lamps {len(lamps)} (pivot {px:.3f}, {py:.3f})")
    global LAMPS, LAMP_PIVOT
    LAMPS, LAMP_PIVOT = lamps, (px, py)
    minimap(walk, rooms)
    emit(walk, water, rooms, doors, tiles, props, consoles, console_sprites)

    fl = Image.open(PREVIEW / "floor_preview.jpg").convert("RGBA")
    d = ImageDraw.Draw(fl)
    for s, kind in L.OPAQUE + L.GLASS:
        g = G.shape(s)
        pts = [((x - BX0) * FLOOR_PPM, (BY1 - y) * FLOOR_PPM) for x, y in g.exterior.coords]
        d.polygon(pts, fill=KIND_COL.get(kind, (150, 150, 150)) + (255,), outline=(0, 0, 0))
    for k, p in consoles.items():
        x, y = (p[0] - BX0) * FLOOR_PPM, (BY1 - p[1]) * FLOOR_PPM
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 230, 0), outline=(0, 0, 0))
    fl.save(PREVIEW / "preview.png")
    print(PREVIEW / "preview.png", fl.size)


if __name__ == "__main__":
    main()
