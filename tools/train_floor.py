# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_floor.py - Bodenbild des Polaris Express (128 px/m), gebaut aus dem Kontext von gen_train.art_ctx.
#
# Aufbau (wie park_floor.py): Grundbild 1x mit nahtlosen Materialkacheln je Raum (Maske aus der begehbaren
# Flaeche), darueber eine Ebene aus aufgezeichneten Zeichenbefehlen (museum_art.OpList, 2x supersampelt und
# streifenweise gerendert) fuer alles mit Kante: Wagenkaesten-Zierlinien, Wandkronen-Lichtkante, die
# Stirnseiten der Nordwaende (Holzvertaefelung, Fenster bei Nacht, Lampen, Einrichtung je Raum), Faltenbaelge,
# Umrisse, Baeume und Masten draussen. Zum Schluss Verdunklung an allen Waenden und leichtes Papierkorn.
#
# Seit dem zweiten Auftrag faehrt der Zug: die Bodenkachel ist RGBA und ausserhalb von Zug und Oberdeck-Feld
# durchsichtig; die Landschaft (Schnee, Gleisbett, Baeume, Masten) liegt im waagerecht nahtlosen Scroll-Streifen
# train_scroll_0.png (render_scroll, 32 m) und zieht im Spiel nach Westen vorbei; eine ferne Ebene
# train_scroll_far_0.png (render_scroll_far, Berge und Waldrand am Nord- und Suedrand) laeuft halb so schnell.
#
# Nordwaende: Stirnseite FACE_H = 0,95 m hoch (etwa 1,73 m Wand bei K = 0,55). Die Wand ist nur 0,4 m dick,
# deshalb reicht der gezeichnete Wagenkasten im Norden um FACE_H weiter als die Kollision; die begehbare
# Flaeche bleibt unberuehrt.

import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

import handdraw as HD
import museum_art as A
import park_floor as PF
from museum_art import K, OUTLINE, OUT_W, alpha, shade
import train_style as S
from train_style import (BRASS, BRASS_D, BRASS_L, BULB, COAL, COAL_L, CREAM, CREAM_D, GLASS, GREEN_LAMP, INK, IRON,
                         IRON_L, LEATHER, LEATHER_D, LINING, NIGHT, NIGHT_L, OAK, OAK_D, PANEL, PAPER, RED_LAMP, SNOW,
                         SNOW_D, SNOW_L, STAR, STEEL, STEEL_D, STEEL_L, TEAL, VELVET, VELVET_D, VELVET_L, WARM, WHITE,
                         WOOD, WOOD_D, WOOD_L, WOOD_X, TOps, TCanvas)

FACE_H = 0.95
GRAIN = 0.0            # Papierkorn: aus, seit die Kacheln PNG sind (Korn kostete +70 % Dateigroesse); > 0 schaltet es ein
AO_STRENGTH = 0.42

# Nordwand-Material je Raum
FACE_MAT = {
    "platform": "rail", "office": "wood", "luggage": "wood", "sleeper": "wood", "dining": "wood", "kitchen": "tile",
    "telegraph": "wood", "dynamo": "steel", "dome": "glass", "generator": "steel", "mail": "wood", "tender": "steel",
    "cab": "steel", "boards": "rail", "gangway": "bellows",
}
# feste Fensterlagen (Mitte x) je Raum; sonst automatisch alle 1,7 m
WINDOWS_AT = {"dining": [-9.0, -7.3, -5.6], "office": [-23.75], "cab": [22.75], "mail": [], "generator": [11.05],
              "dynamo": [], "luggage": [], "telegraph": [1.95], "sleeper": [-18.4, -16.4], "kitchen": [], "tender": []}
LAMPS = []          # (x, y) Wandlampen auf den Stirnseiten -> Lichtflecken auf dem Boden
NAMES = {"platform": "REAR PLATFORM", "office": "CONDUCTOR", "luggage": "LUGGAGE", "sleeper": "SLEEPING CAR",
         "dining": "DINING CAR", "kitchen": "KITCHEN", "telegraph": "TELEGRAPH", "dynamo": "DYNAMO", "dome": "VISTA DOME",
         "generator": "GENERATOR", "mail": "MAIL ROOM", "tender": "TENDER", "cab": "CAB", "boards": ""}


# ------------------------------------------------------------------ Grundbild

class Floor:
    def __init__(self, bounds, ppm, rgba=True):
        self.x0, self.y0, self.x1, self.y1 = bounds
        self.ppm = ppm
        self.w, self.h = int(round((self.x1 - self.x0) * ppm)), int(round((self.y1 - self.y0) * ppm))
        # Bodenkachel: durchsichtig, deckend werden nur Zug und Oberdeck-Feld (der Scroll-Streifen scheint durch)
        self.img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0)) if rgba else Image.new("RGB", (self.w, self.h), (30, 34, 48))

    def P(self, x, y):
        return ((x - self.x0) * self.ppm, (self.y1 - y) * self.ppm)

    def R(self, x0, y0, x1, y1):
        return [self.P(x0, y1), self.P(x1, y0)]

    def mask(self, g, grow=0.0):
        m = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(m)
        if grow:
            g = g.buffer(grow)
        for p in parts(g):
            d.polygon([self.P(*q) for q in p.exterior.coords], fill=255)
            for hole in p.interiors:
                d.polygon([self.P(*q) for q in hole.coords], fill=0)
        return m

    def fill_tile(self, tile, m):
        big = Image.new("RGB", (self.w, self.h))
        if self.img.mode == "RGBA":
            big = big.convert("RGBA")
        tw, th = tile.size
        for yy in range(0, self.h + th, th):
            for xx in range(0, self.w + tw, tw):
                big.paste(tile, (xx, yy))
        self.img.paste(big, (0, 0), m)

    def draw(self):
        return ImageDraw.Draw(self.img, "RGBA")


def parts(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


# ------------------------------------------------------------------ Materialkacheln

def tile_snow(ppm, seed=21):
    n = int(PF.TILE_M * ppm)
    base = np.ones((n, n, 3), np.float32) * np.array(S.GROUND[:3], np.float32)
    base *= (1 + PF._wave(n, (2, 3, 5, 9), seed) * 0.05)[..., None]
    img = PF._img(base)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    s = ppm
    for _ in range(14):                                                 # Verwehungen: weiche helle Bahnen
        x, y, r = rnd.uniform(0, 4), rnd.uniform(0, 4), rnd.uniform(0.5, 1.2)
        for dx, dy in PF.OFFS:
            d.ellipse([((x - r + dx) * s, (y - r * 0.35 + dy) * s), ((x + r + dx) * s, (y + r * 0.35 + dy) * s)], fill=(236, 242, 250, 26))
    for _ in range(90):                                                 # Glitzern
        x, y = rnd.uniform(0, 4), rnd.uniform(0, 4)
        for dx, dy in PF.OFFS:
            d.point(((x + dx) * s, (y + dy) * s), fill=(255, 255, 255, 170))
    return img


def tile_grating(ppm, base=(78, 82, 92), seed=22):
    img, d, n, N, s = PF._canvas(ppm, base, 2)
    g = 0.25                                                            # Traegerraster, Schlitze 0,06 breit
    for r in range(int(PF.TILE_M / g)):
        for c in range(int(PF.TILE_M / 0.1)):
            x, y = c * 0.1, r * g
            for dx, dy in PF.OFFS:
                d.rectangle([((x + 0.02 + dx) * s, (y + 0.04 + dy) * s), ((x + 0.08 + dx) * s, (y + g - 0.04 + dy) * s)], fill=(26, 28, 34))
                d.line([((x + 0.02 + dx) * s, (y + 0.04 + dy) * s), ((x + 0.08 + dx) * s, (y + 0.04 + dy) * s)], fill=(140, 146, 158), width=max(1, int(0.008 * s)))
    for r in range(int(PF.TILE_M / g) + 1):                             # Querstege
        for dx, dy in PF.OFFS:
            d.line([((0 + dx) * s, (r * g + dy) * s), ((4 + dx) * s, (r * g + dy) * s)], fill=PF._tone(base, 1.25), width=max(1, int(0.03 * s)))
    img = img.resize((n, n), Image.LANCZOS)
    return PF._mottle(img, n, 0.05, seed)


def tile_coal(ppm, seed=23):
    img, d, n, N, s = PF._canvas(ppm, (44, 42, 46), 2)
    rnd = random.Random(seed)
    for _ in range(260):
        x, y, r = rnd.uniform(0, 4), rnd.uniform(0, 4), rnd.uniform(0.04, 0.12)
        pts = [(x + r * math.cos(a) * rnd.uniform(0.7, 1.2), y + r * math.sin(a) * rnd.uniform(0.7, 1.2)) for a in [k * math.tau / 6 for k in range(6)]]
        col = rnd.choice([(30, 28, 32), (52, 50, 56), (40, 38, 44)])
        for dx, dy in PF.OFFS:
            d.polygon(PF._px(s, pts, dx, dy), fill=col, outline=(18, 16, 20))
            d.line(PF._px(s, [pts[3], pts[4]], dx, dy), fill=(110, 110, 122), width=max(1, int(0.012 * s)))
    img = img.resize((n, n), Image.LANCZOS)
    return PF._mottle(img, n, 0.08, seed)


def materials(ppm):
    def carpet(*a):
        # das Gewebeflimmern (Pixelrauschen) der Park-Teppichkachel minimal glaetten: PNG-Kacheln werden sonst gross
        return PF.tile_carpet(*a).filter(ImageFilter.GaussianBlur(0.6))

    return {
        "platform": tile_grating(ppm, (74, 78, 88), 31),
        "boards": tile_grating(ppm, (84, 86, 94), 32),
        "office": carpet(ppm, (50, 92, 66), (124, 146, 84), 33),
        "luggage": PF.tile_boards(ppm, (112, 76, 48), 34, 0.22, 1.6),
        "sleeper": carpet(ppm, (138, 44, 56), (196, 150, 84), 35),
        "dining": carpet(ppm, (144, 42, 52), (204, 156, 84), 36),
        "kitchen": PF.tile_checker(ppm, (46, 46, 54), (222, 220, 210), 0.4, 37),
        "telegraph": carpet(ppm, (54, 96, 74), (132, 152, 92), 38),
        "dynamo": PF.tile_plate(ppm, (100, 106, 118), 39),
        "dome": carpet(ppm, (48, 100, 92), (124, 166, 150), 40),
        "generator": PF.tile_tiles(ppm, (80, 84, 94), (44, 46, 54), 0.5, 41, gap=0.012),
        "mail": PF.tile_boards(ppm, (164, 112, 66), 42, 0.2, 1.33),
        "tender": PF.tile_plate(ppm, (78, 80, 88), 43),
        "bunker": tile_coal(ppm, 44),
        "cab": PF.tile_plate(ppm, (94, 98, 110), 45),
        "runboard": PF.tile_boards(ppm, (118, 82, 48), 46, 0.3, 1.8),
        "_snow": tile_snow(ppm),
    }


# ------------------------------------------------------------------ Ebene aus Zeichenbefehlen

def render_ops(base, ops, bounds, ppm, strip_m=3.0, pad=1.0):
    """Ops (2x supersampelt) streifenweise ueber das Grundbild blenden."""
    x0, y0, x1, y1 = bounds
    out = base.convert("RGBA")
    y = y1
    while y > y0 + 1e-6:
        sy0 = max(y0, y - strip_m)
        c = TCanvas(x0, sy0 - pad, x1, y + pad, ppm)
        for (bx0, by0, bx1, by1), fn, args, kw in ops.ops:
            if by1 < sy0 - pad or by0 > y + pad:
                continue
            getattr(c, fn)(*args, **kw)
        tile = c.finish()
        cut = int(round(pad * ppm))
        h = int(round((y - sy0) * ppm))
        tile = tile.crop((0, cut, min(tile.width, out.width), cut + h))
        out.alpha_composite(tile, (0, int(round((y1 - y) * ppm))))
        y = sy0
    return out


# ------------------------------------------------------------------ Oberdeck-Feld und Kartenknopf (bleiben auf der Bodenkachel)

def panel_and_pad(F, ops, ctx):
    """Das Feld des Oberdecks (eigener Grundriss suedlich der Wagen) mit gestrichelten Linien zu den Wagen und die
    Steinplatte unter dem Kartenknopf der Sabotage: feste Teile der Karte, deshalb deckend auf der Bodenkachel."""
    ay0, ay1 = ctx["decks"]["A"]
    uy0, uy1 = ctx["decks"]["B"]
    wall = ctx["wall"]
    d = F.draw()
    dd = [c for c in ctx["cars"] if c["kind"] == "dd"]
    px0, px1 = dd[0]["x0"] - 1.0, dd[-1]["x1"] + 1.0
    py0, py1 = uy0 - 1.3, uy1 + wall + FACE_H + 0.3
    d.rounded_rectangle(F.R(px0, py0, px1, py1), radius=int(0.6 * F.ppm), fill=PANEL)
    ops.poly(S.rrect_pts(px0, py0, px1, py1, 0.6), outline=(110, 122, 160, 255), width=0.05)
    ops.textf(px0 + 0.6, py0 + 0.42, "UPPER DECK", 0.4, (190, 200, 230, 255), kind="black", anchor="lm")
    ops.textf(px0 + 4.1, py0 + 0.4, "above the double-deck cars, stairs at both ends", 0.24, (150, 160, 196, 255), kind="regular", anchor="lm")
    for c in dd:                                                        # gestrichelte Zuordnung zu den Wagen
        for xx in (c["x0"] - wall, c["x1"] + wall):
            y = ay0 - wall - 0.3
            while y > py1 + 0.3:
                ops.line([(xx, y), (xx, max(y - 0.35, py1 + 0.3))], fill=(130, 142, 180, 255), width=0.05)
                y -= 0.6
    # Sabotageknoepfe auf dem Gleisbett (Conductor's Round, Runaway Train, Smoke in the Cars): je eine feste
    # Steinplatte, weil der Boden darunter vorbeizieht
    buttons = [ctx["ticket"]["button"]]
    for key in ("runaway", "smoke"):
        if ctx.get(key) and ctx[key].get("button"):
            buttons.append(ctx[key]["button"])
    for tx, ty in buttons:
        ops.soft_shadow([(tx - 0.55, ty - 0.6), (tx + 0.65, ty - 0.6), (tx + 0.65, ty + 0.5), (tx - 0.55, ty + 0.5)], 80, 0.1)
        ops.ellipse(tx, ty, 0.6, 0.6, fill=(96, 94, 104, 255), outline=OUTLINE, width=0.05)
        ops.ellipse(tx, ty, 0.46, 0.46, outline=BRASS_D, width=0.03)
        ops.ellipse(tx, ty, 0.6, 0.6, outline=alpha(SNOW_L, 120), width=0.08)


def shadow_band(F, ctx):
    """Weiches, halbtransparentes Schattenband unter Wagen und Faltenbaelgen, damit sie sich vom Gleis abheben."""
    layer = Image.new("RGBA", F.img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for c in ctx["cars"]:
        for deck in ["A"] + (["B"] if c["kind"] == "dd" else []):
            x0, y0, x1, y1 = car_rect(c, deck, ctx)
            ld.rounded_rectangle(F.R(x0 - 0.3, y0 - 0.5, x1 + 0.3, y1 + 0.1), radius=int(0.5 * F.ppm), fill=(8, 8, 18, 150))
    for g in ctx["gangways"]:
        x0, y0, x1, y1 = g["box"]
        ld.rectangle(F.R(x0, y0 - 0.35, x1, y1 + 0.2), fill=(8, 8, 18, 120))
    for r in ctx.get("runboard", []):
        x0, y0, x1, y1 = r.bounds
        ld.rectangle(F.R(x0, y0 - 0.45, x1, y1 + 0.05), fill=(8, 8, 18, 130))
    layer = layer.filter(ImageFilter.GaussianBlur(0.22 * F.ppm))
    F.img.alpha_composite(layer)


# ------------------------------------------------------------------ Scroll-Streifen (Landschaft, zieht nach Westen vorbei)

SCROLL_W = 32.0                     # Breite des nahtlosen Streifens in m (4096 px bei 128 px/m)
FAR_N = (7.95, 8.6)                 # ferne Ebene: Baender am Nord- und Suedrand (y)
FAR_S = (-9.0, -8.3)
WRAP = (-SCROLL_W, 0.0, SCROLL_W)   # jedes Objekt dreimal: so passt die Kante exakt


def scroll_objects(ctx):
    """Feste, unregelmaessig verteilte Objekte des Streifens (lokale x in 0..32). Deterministisch."""
    rnd = random.Random(2026)
    ay0, ay1 = ctx["decks"]["A"]
    wall = ctx["wall"]
    g0, g1 = ay0 - 1.1, ay1 + 1.1                                        # Gleisbett y -0,1 .. 6,6
    objs = []
    poles = [1.7, 9.9, 17.3, 26.1]                                        # Telegrafenmasten, Abstaende 8,2 / 7,4 / 8,8 / 7,6
    for x in poles:
        objs.append(("pole", x, 7.2, {}))
    objs.append(("wires", 0, 7.55, {"poles": poles}))
    trees = []

    def place(n, y_lo, y_hi, r_lo, r_hi, tries=400, keep_out=()):
        k = 0
        while k < n and tries > 0:
            tries -= 1
            x, y, r = rnd.uniform(0, SCROLL_W), rnd.uniform(y_lo, y_hi), rnd.uniform(r_lo, r_hi)
            if any(abs(x - tx) < 2.0 and abs(y - ty) < 1.6 for tx, ty in keep_out):
                continue
            ok = True
            for tx, ty, tr in trees:
                ddx = min(abs(x - tx), SCROLL_W - abs(x - tx))
                if math.hypot(ddx, y - ty) < (r + tr) * 0.8:
                    ok = False
                    break
            if ok:
                trees.append((x, y, r))
                k += 1

    place(9, 6.95, 7.4, 0.3, 0.46, keep_out=[(p, 7.2) for p in poles])     # Nordband zwischen Gleis und ferner Ebene
    keep = [(12.5, -3.4), (27.8, -2.6), (5.2, -6.9), (20.4, -6.9)]            # Signal, Pfeifpfosten, Schneemann, Teich
    place(26, g0 - 7.2, g0 - 0.5, 0.45, 0.95, keep_out=keep)                  # Sueden, dichter, groessere Kronen
    for x, y, r in trees:
        objs.append(("tree", x, y, {"r": r}))
    objs += [("signal", 12.5, -2.3, {}), ("whistle", 27.8, -1.9, {}), ("snowman", 5.2, -6.9, {}),
             ("pond", 20.4, -6.9, {"rx": 2.2, "ry": 1.1}), ("log", 15.1, -5.4, {"len": 1.6, "a": 0.35}),
             ("tracks", 2.0, -4.2, {"n": 44}), ("tracks", 23.6, -0.9, {"n": 26})]
    for _ in range(7):
        objs.append(("rock", rnd.uniform(0, SCROLL_W), rnd.uniform(g0 - 7.4, g0 - 0.6), {"r": rnd.uniform(0.12, 0.3)}))
    for _ in range(6):
        objs.append(("bush", rnd.uniform(0, SCROLL_W), rnd.uniform(g0 - 7.4, g0 - 0.4), {"r": rnd.uniform(0.18, 0.3)}))
    for _ in range(5):
        objs.append(("drift", rnd.uniform(0, SCROLL_W), rnd.uniform(g1 + 0.2, 7.6), {"r": rnd.uniform(0.5, 1.1)}))
    for _ in range(8):
        objs.append(("drift", rnd.uniform(0, SCROLL_W), rnd.uniform(g0 - 7.6, g0 - 0.3), {"r": rnd.uniform(0.6, 1.4)}))
    return objs


def scroll_base(F, ctx, mats):
    """1x-Grund des Streifens: Schnee, Gleisbett mit Schotter, Schwellen und beiden Schienen (nahtlos)."""
    ay0, ay1 = ctx["decks"]["A"]
    F.fill_tile(mats["_snow"], Image.new("L", (F.w, F.h), 255))
    d = F.draw()
    rnd = random.Random(7)
    g0, g1 = ay0 - 1.1, ay1 + 1.1
    d.rectangle(F.R(F.x0, g0, F.x1, g1), fill=S.BALLAST)
    for _ in range(int((F.x1 - F.x0) * (g1 - g0) * 55)):
        x, y = rnd.uniform(F.x0, F.x1), rnd.uniform(g0, g1)
        v = rnd.randint(-22, 26)
        for dx in WRAP:
            px, py = F.P(x + dx, y)
            d.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=(88 + v, 86 + v, 92 + v, 255))
    d.rectangle(F.R(F.x0, g0, F.x1, g0 + 0.12), fill=(206, 214, 230, 255))     # Schneekante am Schotter
    d.rectangle(F.R(F.x0, g1 - 0.12, F.x1, g1), fill=(206, 214, 230, 255))
    n = 52                                                                      # Schwellen: Teiler der Streifenbreite
    pitch = SCROLL_W / n
    for k in range(n):
        x = k * pitch + 0.05
        d.rectangle(F.R(x, ay0 - 0.75, x + 0.26, ay1 + 0.75), fill=S.SLEEPER)
        d.rectangle(F.R(x, ay0 - 0.75, x + 0.26, ay0 - 0.71), fill=(140, 110, 80, 255))
    for yy in (ay0 - 0.55, ay1 + 0.55):
        d.rectangle(F.R(F.x0, yy - 0.06, F.x1, yy + 0.06), fill=(60, 60, 66, 255))
        d.rectangle(F.R(F.x0, yy - 0.035, F.x1, yy + 0.035), fill=S.RAIL)


def scroll_ops(ops, ctx, objs):
    """Objekte des Streifens, jedes dreimal (x - 32, x, x + 32), damit die Kante exakt zusammenpasst."""
    rnd = random.Random(9)
    for kind, x, y, prm in sorted(objs, key=lambda o: -o[2]):
        for dx in WRAP:
            xx = x + dx
            if kind == "tree":
                tree(ops, xx, y, prm["r"], random.Random(int(x * 100 + y * 10)))
            elif kind == "pole":
                pole(ops, xx, y)
            elif kind == "wires":
                poles = prm["poles"]
                for i in range(len(poles)):
                    a = poles[i] + dx
                    b = (poles[i + 1] if i + 1 < len(poles) else poles[0] + SCROLL_W) + dx
                    for k in range(3):
                        ops.line([(a, y + 0.06 * k), ((a + b) / 2, y - 0.06 + 0.06 * k), (b, y + 0.06 * k)], fill=(40, 42, 50, 200), width=0.02)
            elif kind == "signal":
                signal(ops, xx, y)
            elif kind == "whistle":
                whistle_post(ops, xx, y)
            elif kind == "snowman":
                snowman(ops, xx, y)
            elif kind == "pond":
                pond(ops, xx, y, prm["rx"], prm["ry"])
            elif kind == "log":
                fallen_log(ops, xx, y, prm["len"], prm["a"])
            elif kind == "tracks":
                fx, fy = xx, y
                for k in range(prm["n"]):
                    fx += 0.28
                    fy += 0.05 * math.sin(k * 0.4 + x)
                    ops.ellipse(fx, fy + (0.1 if k % 2 else -0.1), 0.035, 0.045, fill=(120, 134, 160, 200))
            elif kind == "rock":
                rock(ops, xx, y, prm["r"], rnd)
            elif kind == "bush":
                bush(ops, xx, y, prm["r"], rnd)
            elif kind == "drift":
                ops.ellipse(xx, y, prm["r"], prm["r"] * 0.35, fill=(236, 242, 250, 40))
                ops.ellipse(xx - prm["r"] * 0.2, y + prm["r"] * 0.08, prm["r"] * 0.6, prm["r"] * 0.16, fill=(255, 255, 255, 40))


def tree(ops, x, y, r, rnd):
    seed = int(x * 13 + y * 7) & 0xffff
    ops.soft_shadow([(x - r * 0.6 + 0.25, y - r * 0.6 - 0.25), (x + r * 0.6 + 0.25, y - r * 0.6 - 0.25),
                     (x + r * 0.6 + 0.25, y + r * 0.6 - 0.25), (x - r * 0.6 + 0.25, y + r * 0.6 - 0.25)], 70, 0.15)
    crown = HD.wobble_ellipse(x, y, r, r * 0.92, amp=r * 0.08, seed=seed)
    ops.poly(crown, fill=(36, 70, 52, 255), outline=OUTLINE, width=0.06)
    inner = HD.wobble_ellipse(x - r * 0.18, y + r * 0.2, r * 0.62, r * 0.55, amp=r * 0.1, seed=seed + 5)
    ops.poly(inner, fill=(212, 224, 240, 255), outline=(60, 90, 80, 255), width=0.03)
    for k in range(5):
        a = math.radians(rnd.uniform(0, 360))
        ops.line([(x, y), (x + r * 0.85 * math.cos(a), y + r * 0.8 * math.sin(a))], fill=(28, 54, 42, 220), width=0.04)
    ops.ellipse(x, y, r * 0.1, r * 0.1, fill=(40, 30, 26, 255))


def pole(ops, x, py):
    ops.soft_shadow([(x - 0.1, py - 0.35), (x + 0.5, py - 0.35), (x + 0.5, py + 0.05), (x - 0.1, py + 0.05)], 70, 0.08)
    ops.rect(x - 0.08, py - 0.45, x + 0.08, py + 0.4, fill=(110, 84, 56, 255), outline=OUTLINE, width=0.03)
    ops.rect(x - 0.3, py + 0.32, x + 0.3, py + 0.4, fill=(90, 68, 44, 255), outline=OUTLINE, width=0.025)
    for ix in (-0.22, 0.0, 0.22):
        ops.ellipse(x + ix, py + 0.41, 0.035, 0.035, fill=CREAM, outline=OUTLINE, width=0.015)


def signal(ops, x, y):
    ops.soft_shadow([(x - 0.1, y - 0.2), (x + 0.5, y - 0.2), (x + 0.5, y), (x - 0.1, y)], 70, 0.08)
    ops.rect(x - 0.06, y, x + 0.06, y + 1.8, fill=IRON_L, outline=OUTLINE, width=0.03)
    ops.poly([(x, y + 1.5), (x + 0.75, y + 1.62), (x + 0.75, y + 1.42)], fill=(220, 50, 50, 255), outline=OUTLINE, width=0.03)
    ops.poly([(x + 0.3, y + 1.5), (x + 0.6, y + 1.55), (x + 0.6, y + 1.47)], fill=WHITE)
    ops.glow(x - 0.12, y + 1.3, 0.3, GREEN_LAMP, 0.6)
    ops.ellipse(x - 0.12, y + 1.3, 0.07, 0.07, fill=GREEN_LAMP, outline=OUTLINE, width=0.02)
    ops.ellipse(x - 0.12, y + 1.1, 0.07, 0.07, fill=(90, 40, 40, 255), outline=OUTLINE, width=0.02)
    ops.rect(x - 0.4, y, x + 0.4, y + 0.14, fill=IRON, outline=OUTLINE, width=0.03)


def whistle_post(ops, x, y):
    ops.soft_shadow([(x - 0.1, y - 0.2), (x + 0.4, y - 0.2), (x + 0.4, y), (x - 0.1, y)], 70, 0.08)
    ops.rect(x - 0.05, y, x + 0.05, y + 1.0, fill=(110, 84, 56, 255), outline=OUTLINE, width=0.03)
    ops.poly(S.rrect_pts(x - 0.3, y + 0.75, x + 0.3, y + 1.15, 0.05), fill=CREAM, outline=OUTLINE, width=0.035)
    ops.textf(x, y + 0.95, "W", 0.3, INK, kind="black")


def snowman(ops, x, y):
    ops.soft_shadow([(x - 0.4, y - 0.3), (x + 0.5, y - 0.3), (x + 0.5, y + 0.3), (x - 0.4, y + 0.3)], 80, 0.1)
    ops.ellipse(x, y, 0.42, 0.34, fill=SNOW_L, outline=OUTLINE, width=0.04)
    ops.ellipse(x, y + 0.42, 0.32, 0.27, fill=SNOW_L, outline=OUTLINE, width=0.04)
    ops.ellipse(x, y + 0.78, 0.22, 0.2, fill=SNOW_L, outline=OUTLINE, width=0.04)
    ops.ellipse(x - 0.06, y + 0.52, 0.03, 0.03, fill=INK)
    ops.ellipse(x + 0.08, y + 0.46, 0.03, 0.03, fill=INK)
    ops.poly([(x - 0.05, y + 0.8), (x + 0.22, y + 0.74), (x - 0.05, y + 0.7)], fill=(230, 120, 50, 255), outline=OUTLINE, width=0.015)
    ops.ellipse(x - 0.1, y + 0.84, 0.03, 0.03, fill=INK)
    ops.ellipse(x + 0.02, y + 0.88, 0.03, 0.03, fill=INK)
    ops.line([(x + 0.3, y + 0.45), (x + 0.75, y + 0.7)], fill=(70, 50, 36, 255), width=0.03)
    ops.line([(x - 0.3, y + 0.42), (x - 0.7, y + 0.55)], fill=(70, 50, 36, 255), width=0.03)
    ops.rect(x - 0.2, y + 0.95, x + 0.2, y + 1.0, fill=INK)
    ops.rect(x - 0.13, y + 1.0, x + 0.13, y + 1.2, fill=INK)
    ops.line([(x - 0.24, y + 0.33), (x + 0.26, y + 0.3)], fill=(190, 40, 50, 255), width=0.05)


def pond(ops, x, y, rx, ry):
    pts = HD.wobble_ellipse(x, y, rx, ry, amp=0.08, seed=77)
    ops.poly(pts, fill=(150, 184, 214, 255), outline=OUTLINE, width=0.05)
    inner = HD.wobble_ellipse(x, y, rx * 0.8, ry * 0.75, amp=0.05, seed=78)
    ops.poly(inner, fill=(170, 206, 232, 255))
    for k in range(5):
        a = math.radians(20 + k * 30)
        ops.line([(x + rx * 0.2 * math.cos(a), y + ry * 0.2 * math.sin(a)), (x + rx * 0.7 * math.cos(a), y + ry * 0.7 * math.sin(a))],
                 fill=(220, 236, 248, 200), width=0.02)
    ops.ellipse(x + rx * 0.5, y + ry * 0.4, rx * 0.2, ry * 0.15, fill=(255, 255, 255, 110))


def fallen_log(ops, x, y, ln, a):
    dx, dy = math.cos(a) * ln / 2, math.sin(a) * ln / 2
    ops.soft_shadow([(x - dx, y - dy - 0.2), (x + dx, y + dy - 0.2), (x + dx, y + dy), (x - dx, y - dy)], 70, 0.08)
    ops.line([(x - dx, y - dy), (x + dx, y + dy)], fill=OUTLINE, width=0.3)
    ops.line([(x - dx, y - dy), (x + dx, y + dy)], fill=(96, 68, 44, 255), width=0.22)
    ops.line([(x - dx, y - dy + 0.06), (x + dx, y + dy + 0.06)], fill=(226, 234, 246, 255), width=0.07)
    ops.ellipse(x + dx, y + dy, 0.09, 0.12, fill=(190, 150, 100, 255), outline=OUTLINE, width=0.02)


def rock(ops, x, y, r, rnd):
    pts = [(x + r * math.cos(a) * rnd.uniform(0.7, 1.2), y + r * math.sin(a) * rnd.uniform(0.6, 1.0)) for a in [k * math.tau / 7 for k in range(7)]]
    ops.poly(pts, fill=(96, 100, 112, 255), outline=OUTLINE, width=0.035)
    ops.poly([(px, py + r * 0.18) for px, py in pts[2:6]], fill=(226, 234, 246, 255))


def bush(ops, x, y, r, rnd):
    pts = HD.wobble_ellipse(x, y, r, r * 0.8, amp=r * 0.15, seed=int(x * 31) & 0xfff)
    ops.poly(pts, fill=(46, 84, 62, 255), outline=OUTLINE, width=0.035)
    ops.ellipse(x - r * 0.2, y + r * 0.2, r * 0.5, r * 0.3, fill=(212, 224, 240, 255))


def render_scroll(ctx, ppm=128):
    """Nahe Landschaftsebene: 32 m breiter, waagerecht nahtloser Streifen ueber die volle Kartenhoehe (RGB)."""
    bx0, by0, bx1, by1 = ctx["bounds"]
    bounds = (0.0, by0, SCROLL_W, by1)
    F = Floor(bounds, ppm, rgba=False)
    scroll_base(F, ctx, {"_snow": tile_snow(ppm)})
    ops = TOps()
    scroll_ops(ops, ctx, scroll_objects(ctx))
    img = render_ops(F.img, ops, bounds, ppm).convert("RGB")
    return HD.paper_grain(img, GRAIN, seed=5, scale=2)


def _periodic_ridge(n, seed, base, amp, smooth=3):
    """Periodische Hoehenlinie (n Stuetzpunkte ueber 32 m): Summe von Sinuswellen mit ganzzahligen Perioden plus
    geglaettetes Zufallsrauschen, erster und letzter Punkt gleich."""
    rnd = random.Random(seed)
    waves = [(rnd.randint(1, 6), rnd.uniform(0, math.tau), rnd.uniform(0.3, 1.0)) for _ in range(4)]
    noise = [rnd.uniform(-1, 1) for _ in range(n)]
    out = []
    for i in range(n):
        t = i / n
        v = sum(w * math.sin(k * math.tau * t + ph) for k, ph, w in waves) / 2.0
        nz = sum(noise[(i + j) % n] for j in range(-smooth, smooth + 1)) / (2 * smooth + 1)
        out.append(base + amp * (0.7 * v + 0.6 * nz))
    return out


def render_scroll_far(ctx, ppm=128):
    """Ferne Ebene (halbe Geschwindigkeit): Berge mit Schneegipfeln und Waldsilhouette als Baender am Nord- und
    Suedrand, dazwischen durchsichtig. Horizontal nahtlos (periodische Hoehenlinien, Baeume dreifach)."""
    bx0, by0, bx1, by1 = ctx["bounds"]
    bounds = (0.0, by0, SCROLL_W, by1)
    F = Floor(bounds, ppm, rgba=True)
    ops = TOps()
    n = 128
    step = SCROLL_W / n
    for (b0, b1), sign, seed in ((FAR_N, 1, 31), (FAR_S, -1, 47)):
        # Berge (hinten): zwei Ketten, Schneegipfel; Wald (vorn): dunkle Zacken mit heller Kante
        near_edge, far_edge = (b0, b1) if sign > 0 else (b1, b0)       # near_edge: zur Karte hin
        for k, (col, hfrac, amp) in enumerate((((96, 112, 150, 255), 1.0, 0.16), ((76, 92, 130, 255), 0.75, 0.14))):
            ridge = _periodic_ridge(n, seed + k, hfrac, amp, smooth=4)
            for dx in WRAP:
                pts = [(dx + i * step, near_edge + sign * (b1 - b0) * min(1.0, max(0.25, ridge[i % n]))) for i in range(n + 1)]
                poly = pts + [(dx + SCROLL_W, near_edge), (dx, near_edge)]
                ops.poly(poly, fill=col, outline=OUTLINE, width=0.05)
                caps = []
                for i in range(1, n):
                    if ridge[i % n] > ridge[(i - 1) % n] and ridge[i % n] >= ridge[(i + 1) % n] and ridge[i % n] > 0.7:
                        caps.append(i)
                for i in caps:
                    cx, cy = pts[i]
                    ops.poly([(cx - 0.35, cy - sign * 0.22), (cx + 0.35, cy - sign * 0.22), (cx + 0.1, cy), (cx - 0.1, cy)], fill=(226, 234, 246, 255))
        forest = _periodic_ridge(n, seed + 9, 0.42, 0.1, smooth=2)
        for dx in WRAP:
            pts = []
            for i in range(n + 1):
                x = dx + i * step
                h = near_edge + sign * (b1 - b0) * forest[i % n]
                pts.append((x, h))
                pts.append((x + step * 0.5, h - sign * 0.18))              # Zacken der Tannenspitzen
            poly = pts + [(dx + SCROLL_W, near_edge), (dx, near_edge)]
            ops.poly(poly, fill=(30, 50, 46, 255), outline=OUTLINE, width=0.05)
            edge = [(x, h + sign * 0.06) for x, h in pts]
            ops.line(edge, fill=(120, 160, 150, 120), width=0.03)
            ops.line([(dx, near_edge), (dx + SCROLL_W, near_edge)], fill=OUTLINE, width=0.06)
    img = render_ops(F.img, ops, bounds, ppm)
    return img


def grain_rgba(img, amount, seed=4, scale=2):
    """Papierkorn nur auf den Farbkanaelen, Alpha bleibt."""
    if amount <= 0:
        return img
    a = img.getchannel("A")
    rgb = HD.paper_grain(img.convert("RGB"), amount, seed=seed, scale=scale)
    rgb = rgb.convert("RGBA")
    rgb.putalpha(a)
    return rgb


# ------------------------------------------------------------------ Wagenkaesten

def car_rect(c, deck, ctx):
    wall = ctx["wall"]
    y0, y1 = ctx["decks"][deck]
    return c["x0"] - wall, y0 - wall, c["x1"] + wall, y1 + wall + FACE_H


def bodies(F, ops, ctx):
    d = F.draw()
    wall = ctx["wall"]
    for c in ctx["cars"]:
        body, body_l = S.body_colors(c["key"])
        decks = ["A"] + (["B"] if c["kind"] == "dd" else [])
        for deck in decks:
            x0, y0, x1, y1 = car_rect(c, deck, ctx)
            d.rounded_rectangle(F.R(x0, y0, x1, y1), radius=int(0.3 * F.ppm), fill=body)
            # Zierlinien auf der Suedseite (sichtbarer Wagenkasten) und am Nordrand
            for yy in (y0 + 0.1, y0 + 0.3):
                ops.line([(x0 + 0.35, yy), (x1 - 0.35, yy)], fill=LINING, width=0.03)
            ops.line([(x0 + 0.35, y1 - 0.12), (x1 - 0.35, y1 - 0.12)], fill=LINING, width=0.03)
            for xx in (x0 + 0.1, x1 - 0.1):
                ops.line([(xx, y0 + 0.4), (xx, y1 - 0.25)], fill=alpha(LINING, 200), width=0.03)
            # Dachkante nord: helle Kante (Lichtkante der Wagendecke)
            ops.line([(x0 + 0.3, y1 - 0.02), (x1 - 0.3, y1 - 0.02)], fill=alpha(body_l, 220), width=0.05)
    # Faltenbaelge zwischen den Wagen (Grundflaeche, Rest kommt als Stirnseite)
    for g in ctx["gangways"]:
        x0, y0, x1, y1 = g["box"]
        d.rectangle(F.R(x0, y0, x1, y1), fill=(52, 50, 56, 255))
        n = int((x1 - x0) / 0.18)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / max(1, n)
            ops.line([(xx, y0), (xx, y1)], fill=(36, 34, 40, 255), width=0.03)
        ops.rect(x0, y0, x1, y0 + 0.1, fill=STEEL_D)
        ops.rect(x0, y1 - 0.1, x1, y1, fill=STEEL_D)
        ops.rect(x0, (y0 + y1) / 2 - 0.3, x1, (y0 + y1) / 2 + 0.3, fill=(64, 62, 68, 255))
    # Treppenschaechte: dunkle Grube (die Treppe selbst ist ein Objekt-Sprite)
    for st in ctx["stairs"]:
        for key in ("main", "upper"):
            x0, y0, x1, y1 = st[key]
            d.rectangle(F.R(x0, y0, x1, y1), fill=(24, 20, 20, 255))
    # Kessel der Lok: dunkle Grundflaeche (Objekt-Sprite darueber)
    bx0, by0, bx1, by1 = ctx["boiler"]
    d.rectangle(F.R(bx0, by0, bx1, by1), fill=(34, 34, 40, 255))


def couplers(ops, ctx):
    """Puffer, Kupplung und Bremsschlaeuche in den Luecken zwischen den Wagen; Schneepflug und Pufferbohle vorn,
    Schlussleuchten hinten."""
    wall = ctx["wall"]
    ay0, ay1 = ctx["decks"]["A"]
    cars = ctx["cars"]
    for i in range(len(cars) - 1):
        a, b = cars[i], cars[i + 1]
        xa, xb = a["x1"] + wall, b["x0"] - wall
        g = next(gg for gg in ctx["gangways"] if gg["west"] == a["key"])
        gy0, gy1 = g["opening"]
        for yy in (gy0 - 0.55, gy1 + 0.55):
            if yy < ay0 - 0.25 or yy > ay1 + 0.25:
                continue
            for xx, sgn in ((xa, 1), (xb, -1)):                           # Puffer
                ops.rect(min(xx, xx + sgn * 0.3), yy - 0.1, max(xx, xx + sgn * 0.3), yy + 0.1, fill=IRON, outline=OUTLINE, width=0.025)
                ops.ellipse(xx + sgn * 0.33, yy, 0.05, 0.15, fill=IRON_L, outline=OUTLINE, width=0.025)
        my = (gy0 + gy1) / 2
        ops.line([(xa, my - 0.95), (xb, my - 0.95)], fill=OUTLINE, width=0.09)      # Kupplungsstange unter dem Balg
        ops.line([(xa, my - 0.95), (xb, my - 0.95)], fill=IRON_L, width=0.05)
        ops.line([(xa + 0.05, my - 1.15), ((xa + xb) / 2, my - 1.3), (xb - 0.05, my - 1.15)], fill=(140, 40, 40, 255), width=0.035)
    # Lok: Pufferbohle, Schneepflug, Lichtkegel des Scheinwerfers auf dem Schnee
    loco = cars[-1]
    fx = loco["x1"] + wall
    cy = (ay0 + ay1) / 2
    ops.rect(fx, ay0 - 0.2, fx + 0.22, ay1 + 0.2, fill=(170, 44, 40, 255), outline=OUTLINE, width=0.035)
    for yy in (ay0 + 0.45, ay1 - 0.45):
        ops.ellipse(fx + 0.3, yy, 0.08, 0.16, fill=IRON_L, outline=OUTLINE, width=0.025)
    ops.poly([(fx + 0.2, ay0 - 0.1), (fx + 0.95, cy - 0.5), (fx + 1.15, cy), (fx + 0.95, cy + 0.5), (fx + 0.2, ay1 + 0.1)],
             fill=IRON, outline=OUTLINE, width=0.04)
    for k in range(5):
        t = (k + 0.5) / 5
        ops.line([(fx + 0.25, ay0 - 0.1 + (ay1 - ay0 + 0.2) * t), (fx + 0.95 + 0.2 * (1 - abs(2 * t - 1)), cy + (t - 0.5) * 1.0)],
                 fill=(130, 40, 40, 255), width=0.03)
    ops.poly([(fx + 0.6, cy - 0.45), (fx + 3.2, cy - 1.6), (fx + 3.2, cy + 1.6), (fx + 0.6, cy + 0.45)], fill=(255, 232, 160, 60))
    ops.poly([(fx + 0.6, cy - 0.3), (fx + 2.4, cy - 0.9), (fx + 2.4, cy + 0.9), (fx + 0.6, cy + 0.3)], fill=(255, 240, 190, 50))
    # Schlusswagen: Pufferbohle, Puffer, rote Schlussleuchten (Schein auf dem Schnee)
    cab = cars[0]
    rx = cab["x0"] - wall
    ops.rect(rx - 0.22, ay0 - 0.2, rx, ay1 + 0.2, fill=(120, 36, 34, 255), outline=OUTLINE, width=0.035)
    for yy in (ay0 + 0.45, ay1 - 0.45):
        ops.ellipse(rx - 0.3, yy, 0.08, 0.16, fill=IRON_L, outline=OUTLINE, width=0.025)
        ops.glow(rx - 0.15, yy + (0.55 if yy < cy else -0.55), 0.45, RED_LAMP, 0.55)
    ops.line([(rx - 0.05, cy - 0.6), (rx - 0.6, cy)], fill=IRON_L, width=0.05)


# ------------------------------------------------------------------ Raumboeden

def floors(F, ctx, mats):
    walk = ctx["walk"]
    for r in ctx["rooms"]:
        g = ctx["room_geom"][r["key"]].intersection(walk)
        if r["key"] == "tender":
            hp = next(h for h in ctx["hparts"] if 16 < h[1] < 21)
            corridor = g.intersection(box(-99, -99, 99, hp[0]))
            bunker = g.difference(box(-99, -99, 99, hp[0]))
            F.fill_tile(mats["tender"], F.mask(corridor))
            F.fill_tile(mats["bunker"], F.mask(bunker))
            continue
        F.fill_tile(mats.get(r["key"], mats["dining"]), F.mask(g))


def runboard_floor(F, ctx, mats):
    """Aussen-Laufsteg (Trittbrett) samt Abgaengen: Holzbohlen laengs zum Zug, deckend auf der Bodenkachel."""
    rb = ctx.get("runboard") or []
    if not rb:
        return
    g = unary_union(rb).intersection(ctx["walk"])
    rooms = unary_union([ctx["room_geom"][r["key"]] for r in ctx["rooms"]])
    F.fill_tile(mats["runboard"], F.mask(g.difference(rooms)))


def runboard_ops(ops, ctx, rnd):
    """Trittbrett im Detail: Eisenwinkel mit Nieten an beiden Kanten, Halterungen zum Wagenkasten, Haltestangen an
    den Wagenecken, kleine Laternen, Stufen mit Kanten an den Abgaengen, Kontaktschatten unter dem Wagenkasten."""
    rb = ctx.get("runboard") or []
    if not rb:
        return
    main, steps = rb[0], rb[1:]
    x0, y0, x1, y1 = main.bounds
    ay0 = ctx["decks"]["A"][0]
    wall = ctx["wall"]
    step_x = [(s.bounds[0], s.bounds[2]) for s in steps]

    def in_step(x, margin=0.0):
        return any(a - margin <= x <= b + margin for a, b in step_x)

    # Schatten des Wagenkastens auf den Bohlen (Nordkante) und Fugenkante
    ops.rect(x0, y1 - 0.22, x1, y1, fill=(0, 0, 0, 55))
    ops.rect(x0, y1 - 0.08, x1, y1, fill=(0, 0, 0, 45))
    # Eisenwinkel an der Suedkante (durchgehend) und an der Nordkante (zwischen den Abgaengen)
    ops.rect(x0, y0, x1, y0 + 0.08, fill=IRON)
    ops.line([(x0, y0 + 0.08), (x1, y0 + 0.08)], fill=IRON_L, width=0.014)
    ops.line([(x0, y0 + 0.03), (x1, y0 + 0.03)], fill=(30, 30, 36, 255), width=0.01)
    cuts = sorted(step_x)
    xa = x0
    for a, b in cuts + [(x1, x1)]:
        if a - xa > 0.1:
            ops.rect(xa, y1 - 0.06, a, y1, fill=IRON)
            ops.line([(xa, y1 - 0.06), (a, y1 - 0.06)], fill=IRON_L, width=0.012)
        xa = b
    x = x0 + 0.22
    while x < x1:                                                       # Nieten auf beiden Winkeln
        S.rivets(ops, [(x, y0 + 0.04)], 0.016, STEEL_L)
        if not in_step(x, 0.05):
            S.rivets(ops, [(x + 0.2, y1 - 0.03)], 0.014, STEEL_L)
        x += 0.45
    # Halterungen: Gusswinkel zwischen Steg und Wagenkasten (Luecke y 0,35..0,6), je Wagen unregelmaessig
    for c in ctx["cars"]:
        cx0, cx1 = c["x0"] - wall + 0.35, c["x1"] + wall - 0.35
        n = max(2, int((cx1 - cx0) / 1.45))
        for k in range(n + 1):
            bx = cx0 + (cx1 - cx0) * k / n + (0.08 if k % 2 else -0.06)
            if in_step(bx, 0.25):
                continue
            ops.poly([(bx - 0.09, y1 - 0.02), (bx + 0.09, y1 - 0.02), (bx + 0.07, ay0 - wall + 0.03), (bx - 0.07, ay0 - wall + 0.03)],
                     fill=IRON_L, outline=OUTLINE, width=0.025)
            ops.line([(bx - 0.06, y1 + 0.02), (bx - 0.06, ay0 - wall)], fill=STEEL_L, width=0.012)
            S.rivets(ops, [(bx, y1 + 0.1)], 0.016, STEEL_L)
    # Haltestangen an den Wagenecken: Messingstange steht an der Suedkante, Knauf oben
    posts = []
    for c in ctx["cars"]:
        for px in (c["x0"] - wall + 0.14, c["x1"] + wall - 0.14):
            if x0 + 0.1 <= px <= x1 - 0.1:
                posts.append(px)
    for px in posts:
        ops.ellipse(px + 0.04, y0 + 0.14, 0.06, 0.03, fill=(0, 0, 0, 70))
        ops.ellipse(px, y0 + 0.14, 0.05, 0.03, fill=IRON, outline=OUTLINE, width=0.015)
        top = y0 + 0.14 + 1.05 * K
        ops.line([(px, y0 + 0.14), (px, top)], fill=OUTLINE, width=0.065)
        ops.line([(px, y0 + 0.14), (px, top)], fill=BRASS, width=0.035)
        ops.line([(px - 0.008, y0 + 0.2), (px - 0.008, top - 0.05)], fill=BRASS_L, width=0.01)
        ops.ellipse(px, top, 0.04, 0.04, fill=BRASS, outline=OUTLINE, width=0.015)
    # Laternen alle paar Meter (unregelmaessig), nicht an Pfosten oder Abgaengen; warmer Schein auf den Bohlen
    x = x0 + 2.6
    k = 0
    while x < x1 - 1.0:
        if not in_step(x, 0.5) and all(abs(x - p) > 0.6 for p in posts):
            S.lantern(ops, x, y0 + 0.36, 0.65, (255, 226, 160, 255), on=True)
            ops.line([(x, y0 + 0.5), (x, y0 + 0.62)], fill=OUTLINE, width=0.03)
            ops.line([(x, y0 + 0.62), (x + 0.12, y0 + 0.62)], fill=OUTLINE, width=0.03)
        x += (4.1, 5.3, 4.6, 5.9)[k % 4]
        k += 1
    # Abgaenge: Bohlenweg mit Eisenkanten, Stufenkante am Steg und am Faltenbalg; kurze Abgaenge an den Enden als Stufen
    for s in steps:
        sx0, sy0, sx1, sy1 = s.bounds
        sy0 = max(sy0, y1 - 0.02)
        for ex in (sx0, sx1 - 0.05):
            ops.rect(ex, sy0, ex + 0.05, sy1, fill=IRON)
            ops.line([(ex + 0.05 if ex == sx0 else ex, sy0 + 0.03), (ex + 0.05 if ex == sx0 else ex, sy1 - 0.03)], fill=IRON_L, width=0.01)
        short = sy1 - sy0 < 1.0
        n = 2 if short else 1
        for i in range(n):
            ya = sy0 + (sy1 - sy0) * i / n
            ops.rect(sx0, ya - 0.02, sx1, ya + 0.05, fill=IRON, outline=OUTLINE, width=0.015)
            ops.line([(sx0 + 0.05, ya + 0.05), (sx1 - 0.05, ya + 0.05)], fill=(240, 232, 210, 110), width=0.014)
            ops.rect(sx0 + 0.05, ya + 0.05, sx1 - 0.05, ya + 0.14, fill=(0, 0, 0, 55))
        ops.rect(sx0, sy1 - 0.06, sx1, sy1, fill=IRON, outline=OUTLINE, width=0.015)
        S.rivets(ops, [(sx0 + 0.12, sy0 + 0.25 + k * 0.5) for k in range(int((sy1 - sy0 - 0.3) / 0.5) + 1)] +
                 [(sx1 - 0.12, sy0 + 0.25 + k * 0.5) for k in range(int((sy1 - sy0 - 0.3) / 0.5) + 1)], 0.014, STEEL_L)
        if not short:                                                   # Handlauf-Kette zwischen den Wagen
            for ex in (sx0 - 0.1, sx1 + 0.1):
                ops.line([(ex, sy0 + 0.1), (ex, sy1 - 0.1)], fill=(40, 40, 46, 200), width=0.02)
                for cy in (sy0 + 0.1, sy1 - 0.1):
                    ops.ellipse(ex, cy, 0.03, 0.03, fill=IRON_L, outline=OUTLINE, width=0.012)


def floor_decor(ops, ctx, rnd):
    walk = ctx["walk"]
    geom = ctx["room_geom"]
    # Speisewagen: Laeufer in der Mitte, Medaillon unter der Notfallglocke
    x0, y0, x1, y1 = geom["dining"].bounds
    runner(ops, x0 + 0.1, 2.65, x1 - 0.1, 3.85, VELVET_D, BRASS_D)
    ex, ey = ctx["emergency"]
    ops.ellipse(ex, ey, 0.75, 0.75, fill=(112, 30, 42, 255), outline=BRASS, width=0.05)
    ops.ellipse(ex, ey, 0.55, 0.55, outline=alpha(BRASS, 160), width=0.02)
    for k in range(8):
        a = math.radians(k * 45)
        ops.line([(ex + 0.2 * math.cos(a), ey + 0.2 * math.sin(a)), (ex + 0.5 * math.cos(a), ey + 0.5 * math.sin(a))], fill=alpha(BRASS, 150), width=0.02)
    # Schlafwagen (Oberdeck): Laeufer im Gang; Gepaeckraum: Kreidelinien vor den Kaefigen
    x0, y0, x1, y1 = geom["sleeper"].bounds
    runner(ops, x0 + 0.1, y0 + 0.55, x1 - 0.1, y0 + 1.55, VELVET_D, BRASS_D)
    x0, y0, x1, y1 = geom["luggage"].bounds
    for xx in (-19.4, -17.4, -15.4):
        ops.line([(xx, 1.1), (xx, 3.4)], fill=(236, 230, 200, 70), width=0.03)
    # Dynamo-Raum: Kabel vom Dynamo zur Schalttafel; Oelflecken in Generator- und Fuehrerstand
    dyn = ctx["opaque"][1]
    sw = ctx["consoles"].get("Electrical/SwitchConsole/0", (6.3, 1.4))
    A.floor_cable(ops, [(dyn[3] - 0.1, dyn[2] + 0.2), (dyn[3] + 0.7, dyn[2] - 0.1), (sw[0] - 0.3, sw[1] + 0.05)], seed=3, col=(40, 36, 44, 255))
    A.oil_stain(ops, 9.6, 3.3, 0.55, 0.3, seed=4, a=90)
    A.oil_stain(ops, 22.6, 3.0, 0.4, 0.25, seed=6, a=80)
    A.oil_stain(ops, 4.2, 3.9, 0.35, 0.2, seed=8, a=70)
    # Tender: Kohlenstaub vor den Luken, ein paar Brocken im Gang
    for h in ctx["hparts"]:
        if 16 < h[1] < 21:
            for a, b, _o in h[4]:
                cx = (a + b) / 2
                ops.ellipse(cx, h[1] - 0.45, 0.6, 0.3, fill=(20, 18, 20, 70))
                for _ in range(5):
                    lx, ly = cx + rnd.uniform(-0.5, 0.5), h[1] - rnd.uniform(0.3, 0.9)
                    coal_lump(ops, lx, ly, rnd.uniform(0.04, 0.08), rnd)
    # Fuehrerstand: Kohlenschaufel lehnt am Boden, Kreideschrift "No 4"
    ops.line([(22.1, 2.2), (22.9, 1.75)], fill=OUTLINE, width=0.07)
    ops.line([(22.1, 2.2), (22.9, 1.75)], fill=OAK_D, width=0.04)
    ops.poly([(22.85, 1.95), (23.3, 1.75), (23.15, 1.4), (22.75, 1.6)], fill=IRON_L, outline=OUTLINE, width=0.025)
    # Kueche: Matte vor dem Herd; Postraum: verstreute Briefe
    ops.poly(S.rrect_pts(-9.2, -4.2, -5.4, -3.45, 0.1), fill=(70, 60, 56, 255), outline=(40, 34, 32, 255), width=0.025)
    for k in range(6):
        lx, ly = rnd.uniform(12.4, 14.6), rnd.uniform(1.7, 2.6)
        a = rnd.uniform(-0.5, 0.5)
        pts = [(lx + 0.14 * math.cos(a) - 0.1 * math.sin(a), ly + 0.14 * math.sin(a) + 0.1 * math.cos(a)),
               (lx - 0.14 * math.cos(a) - 0.1 * math.sin(a), ly - 0.14 * math.sin(a) + 0.1 * math.cos(a)),
               (lx - 0.14 * math.cos(a) + 0.1 * math.sin(a), ly - 0.14 * math.sin(a) - 0.1 * math.cos(a)),
               (lx + 0.14 * math.cos(a) + 0.1 * math.sin(a), ly + 0.14 * math.sin(a) - 0.1 * math.cos(a))]
        ops.poly(pts, fill=PAPER, outline=OUTLINE, width=0.012)
        ops.line([pts[0], ((pts[0][0] + pts[2][0]) / 2, (pts[0][1] + pts[2][1]) / 2), pts[1]], fill=CREAM_D, width=0.01)
    # Plattform: gelbe Warnkante am Zugende; Umlauf der Lok: Warnstreifen am Kesselrand
    px0, py0, px1, py1 = geom["platform"].bounds
    ops.rect(px0 + 0.05, py0 + 0.05, px0 + 0.2, py1 - 0.05, fill=(230, 190, 60, 200))
    bx0, by0, bx1, by1 = ctx["boiler"]
    for yy in (by0 - 0.12, by1 + 0.12):
        A.hazard(ops, bx0, yy - 0.06, bx1, yy + 0.06)
    # Tuerschwellen aus Messing
    for dd in ctx["doors"]:
        if dd["vertical"]:
            ops.rect(dd["x"] - 0.05, dd["y"] - dd["length"] / 2, dd["x"] + 0.05, dd["y"] + dd["length"] / 2, fill=BRASS_D, outline=OUTLINE, width=0.015)
        else:
            ops.rect(dd["x"] - dd["length"] / 2, dd["y"] - 0.05, dd["x"] + dd["length"] / 2, dd["y"] + 0.05, fill=BRASS_D, outline=OUTLINE, width=0.015)
    # Gangoeffnungen ohne Tuer (Buero/Plattform, Tender/Lok): Schwelle
    for x, deck, op, owner in ctx["vparts"]:
        if owner is None:
            ops.rect(x - 0.05, op[0], x + 0.05, op[1], fill=BRASS_D, outline=OUTLINE, width=0.015)
    for g in ctx["gangways"]:
        if g["door"] is None:
            x0, y0, x1, y1 = g["box"]
            for xx in (x0 + 0.2, x1 - 0.2):
                ops.rect(xx - 0.05, y0, xx + 0.05, y1, fill=BRASS_D, outline=OUTLINE, width=0.015)
    # Absaetze der Treppen: Messingkante mit "UP"/"DOWN"-Pfeil auf dem Boden
    for st in ctx["stairs"]:
        for key, pt, up in (("main", st["a"], True), ("upper", st["b"], False)):
            x0, y0, x1, y1 = st[key]
            ops.rect(x0, y0 - 0.08, x1, y0, fill=BRASS, outline=OUTLINE, width=0.015)
            ax, ay = pt
            if up:
                ops.poly([(ax - 0.18, ay - 0.1), (ax + 0.18, ay - 0.1), (ax, ay + 0.18)], fill=(255, 240, 200, 120))
            else:
                ops.poly([(ax - 0.18, ay + 0.18), (ax + 0.18, ay + 0.18), (ax, ay - 0.1)], fill=(255, 240, 200, 120))


def runner(ops, x0, y0, x1, y1, col, edge):
    ops.rect(x0, y0, x1, y1, fill=col)
    ops.rect(x0 + 0.05, y0 + 0.05, x1 - 0.05, y1 - 0.05, outline=edge, width=0.03)
    ops.rect(x0 + 0.14, y0 + 0.14, x1 - 0.14, y1 - 0.14, outline=alpha(edge, 120), width=0.015)
    x = x0 + 0.5
    while x < x1 - 0.4:
        ops.ellipse(x, (y0 + y1) / 2, 0.05, 0.05, fill=alpha(edge, 140))
        x += 0.5


def coal_lump(ops, x, y, r, rnd):
    pts = [(x + r * math.cos(a) * rnd.uniform(0.75, 1.2), y + r * math.sin(a) * rnd.uniform(0.75, 1.2)) for a in [k * math.tau / 6 for k in range(6)]]
    ops.poly(pts, fill=COAL, outline=OUTLINE, width=0.012)
    ops.line([pts[3], pts[4]], fill=(120, 120, 132, 255), width=0.012)


# ------------------------------------------------------------------ Wandkronen, Stirnseiten, Umrisse

def owner_of(pt, ctx):
    for r in ctx["rooms"]:
        if ctx["room_geom"][r["key"]].buffer(0.05).contains(pt):
            return r["key"]
    for g in ctx["gangways"]:
        if box(*g["box"]).buffer(0.05).contains(pt):
            return "gangway"
    return None


def inner_walls(ops, ctx):
    """Gepaeckkaefige (Hauptebene) als Eisengitter mit Messingpfosten, Schlafabteile (Oberdeck) als Holzwaende:
    die duennen Trennwaende aus VSOLID/HPARTS von oben."""
    walk = ctx["walk"]
    pieces = []
    for x, y0, y1 in ctx["vsolid"]:
        pieces.append((box(x - 0.1, y0, x + 0.1, y1), y0 > 0))
    for y, x0, x1, th, ops_ in ctx["hparts"]:
        if th > 0.3:
            continue                                                    # Kohlenbunker: bleibt Stahl in Wagenfarbe
        g = box(x0, y - th / 2, x1, y + th / 2)
        for a, b, _o in ops_:
            g = g.difference(box(a, y - th, b, y + th))
        pieces.append((g, y > 0))
    for g, cage in pieces:
        g = g.difference(walk)
        for p in parts(g):
            pts = list(p.exterior.coords)[:-1]
            ops.poly(pts, fill=IRON if cage else WOOD_D)
            x0, y0, x1, y1 = p.bounds
            if x1 - x0 > y1 - y0:                                       # waagerecht: Pfosten entlang x
                x = x0 + 0.25
                while x < x1 - 0.1:
                    ops.ellipse(x, (y0 + y1) / 2, 0.055, 0.055, fill=BRASS_D if cage else WOOD_X, outline=OUTLINE, width=0.015)
                    x += 0.5
                if cage:
                    ops.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], fill=STEEL_L, width=0.02)
            else:
                y = y0 + 0.25
                while y < y1 - 0.1:
                    ops.ellipse((x0 + x1) / 2, y, 0.055, 0.055, fill=BRASS_D if cage else WOOD_X, outline=OUTLINE, width=0.015)
                    y += 0.5
                if cage:
                    ops.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=STEEL_L, width=0.02)


def crown_rim(ops, ctx):
    """Lichtkante auf der Wandkrone entlang jeder Raumkante (Volumen der Wandmasse)."""
    walk = ctx["walk"]
    inside = unary_union([box(*car_rect(c, dk, ctx)) for c in ctx["cars"] for dk in (["A"] + (["B"] if c["kind"] == "dd" else []))])
    inside = inside.union(unary_union([box(*g["box"]).buffer(0.3) for g in ctx["gangways"]]))
    for p in parts(walk):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            for i in range(len(ring) - 1):
                seg = LineString([ring[i], ring[i + 1]])
                if seg.length < 0.05:
                    continue
                band = seg.buffer(0.13, cap_style=2, join_style=2).difference(walk).intersection(inside)
                for g in parts(band):
                    if not g.interiors and not g.is_empty:
                        mx, my = seg.centroid.x, seg.centroid.y
                        key = None
                        for c in ctx["cars"]:
                            if c["x0"] - 0.5 <= mx <= c["x1"] + 0.5:
                                key = c["key"]
                        ops.poly(list(g.exterior.coords)[:-1], fill=alpha(S.body_colors(key)[1], 230))


def faces(ops, ctx):
    """Stirnseiten der Nordwaende: so hoch wie die feste Masse darueber reicht (hoechstens FACE_H)."""
    walk = ctx["walk"]
    bx0, by0, bx1, by1 = ctx["bounds"]
    solid = box(bx0 - 5, by0 - 5, bx1 + 5, by1 + 5).difference(walk).buffer(0)
    psolid = prep(solid)
    stair_edges = [(st[k][0], st[k][1], st[k][2]) for st in ctx["stairs"] for k in ("main", "upper")]
    boiler = ctx["boiler"]
    rnd = random.Random(11)
    LAMPS.clear()
    segs = []
    for p in parts(walk):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            for i in range(len(ring) - 1):
                (x0, y0), (x1, y1) = ring[i], ring[i + 1]
                if math.hypot(x1 - x0, y1 - y0) < 0.05 or abs(y1 - y0) > abs(x1 - x0) * 0.5:
                    continue
                xa, xb, yb = min(x0, x1), max(x0, x1), (y0 + y1) / 2
                mx = (xa + xb) / 2
                if not (psolid.contains(Point(mx, yb + 0.04)) and walk.contains(Point(mx, yb - 0.04))):
                    continue
                if any(abs(yb - sy) < 0.02 and xa >= sx0 - 0.02 and xb <= sx1 + 0.02 for sx0, sy, sx1 in stair_edges):
                    continue
                if abs(yb - boiler[1]) < 0.02 and xa >= boiler[0] - 0.02 and xb <= boiler[2] + 0.02:
                    continue
                segs.append((xa, xb, yb))
    # Zusammenhaengende Stuecke gleicher Hoehe mergen (ein Ring liefert die Nordwand in mehreren Teilen)
    segs.sort(key=lambda s: (round(s[2], 3), s[0]))
    merged = []
    for xa, xb, yb in segs:
        if merged and abs(merged[-1][2] - yb) < 0.01 and abs(merged[-1][1] - xa) < 0.02:
            merged[-1] = (merged[-1][0], xb, yb)
        else:
            merged.append((xa, xb, yb))
    plates = {}
    for xa, xb, yb in merged:
        owner = owner_of(Point((xa + xb) / 2, yb - 0.12), ctx)
        fh = PF.face_height(psolid, xa, xb, yb, FACE_H)
        face = box(xa, yb, xb, yb + fh).intersection(solid.buffer(0.001))
        if face.is_empty:
            continue
        mat = FACE_MAT.get(owner, "wood")
        draw_face(ops, ctx, owner, mat, xa, xb, yb, fh, face, rnd)
        if owner and fh > 0.8 and (xb - xa) > (plates.get(owner, (0, 0, 0, 0))[1] - plates.get(owner, (0, 0, 0, 0))[0]):
            plates[owner] = (xa, xb, yb, fh)
    for owner, (xa, xb, yb, fh) in plates.items():
        name = NAMES.get(owner, "")
        if not name or xb - xa < 1.2 or FACE_MAT.get(owner) in ("rail", "bellows", "glass"):
            continue
        w = 0.075 * len(name) + 0.16
        S.plate(ops, (xa + xb) / 2, yb + fh - 0.085, w, 0.11, name, size=0.068)


def draw_face(ops, ctx, owner, mat, xa, xb, yb, fh, face, rnd):
    """Eine Stirnseite: Material, Fenster, Lampen, Einrichtung je Raum. z = Hoehe im Bild (0..fh) ueber yb."""
    w = xb - xa
    z = lambda v: yb + v                      # Bildhoehe -> Welt-y
    if fh < 0.45:                              # niedrige Innenwaende (Kaefige, Abteile, Kohlenbunker): schlichtes Band
        col = {"steel": STEEL, "tile": CREAM, "wood": WOOD}.get(mat, WOOD)
        if owner == "tender":
            S.steel_wall(ops, xa, yb, xb, yb + fh, col=IRON_L, plate_w=1.1)
        elif owner in ("luggage",):
            ops.rect(xa, yb, xb, yb + fh, fill=IRON)
            x = xa + 0.06
            while x < xb:
                ops.line([(x, yb + 0.02), (x, yb + fh - 0.02)], fill=IRON_L, width=0.02)
                x += 0.12
            ops.rect(xa, yb + fh - 0.05, xb, yb + fh, fill=STEEL_L)
        else:
            ops.rect(xa, yb, xb, yb + fh, fill=shade(col, 0.9))
            ops.rect(xa, yb + fh - 0.05, xb, yb + fh, fill=shade(col, 1.25))
            ops.rect(xa, yb, xb, yb + 0.05, fill=shade(col, 0.55))
        ops.rect(xa, yb - 0.12, xb, yb, fill=(0, 0, 0, 50))
        return
    # Material
    if mat == "wood":
        S.paneling(ops, xa, yb, xb, yb + fh, pw=0.62, col=WOOD, seed=int(xa * 10))
    elif mat == "steel":
        S.steel_wall(ops, xa, yb, xb, yb + fh, col=STEEL, plate_w=0.85, seed=int(xa))
        if owner in ("generator", "dynamo", "cab"):
            S.pipe(ops, [(xa + 0.05, z(0.87)), (xb - 0.05, z(0.87))], 0.04, BRASS_D, flange=w > 1.0)
    elif mat == "tile":
        tiles_wall(ops, xa, yb, xb, yb + fh)
    elif mat == "glass":
        dome_glass(ops, xa, yb, xb, yb + fh, rnd)
    elif mat == "rail":
        railing_face(ops, xa, yb, xb, yb + fh, rnd, low=(owner == "boards"))
    elif mat == "bellows":
        bellows_face(ops, ctx, xa, yb, xb, yb + fh)
    # Fenster und Lampen (nur an Aussenwaenden in voller Hoehe)
    lamps = []
    if fh > 0.8 and mat in ("wood", "steel", "tile"):
        wins = WINDOWS_AT.get(owner)
        if wins is None:
            wins = []
            x = xa + 0.85
            while x + 0.55 < xb - 0.2:
                wins.append(x)
                x += 1.7
        wins = [x for x in wins if xa + 0.5 <= x <= xb - 0.5]
        ww, wz0, wz1 = (0.9, 0.36, 0.84) if mat == "wood" else (0.6, 0.44, 0.8)
        for i, x in enumerate(wins):
            S.night_window(ops, x - ww / 2, z(wz0), x + ww / 2, z(wz1), rnd, curtain=(mat == "wood"), moon=(owner == "dining" and i == 1))
        edges = [xa] + wins + [xb]
        for i in range(len(edges) - 1):
            lx = (edges[i] + edges[i + 1]) / 2
            if edges[i + 1] - edges[i] > 1.0 and owner not in ("generator",):
                lamps.append(lx)
    # Einrichtung je Raum auf der Stirnseite
    fn = ROOM_FACE.get(owner)
    if fn and fh > 0.8:
        fn(ops, ctx, xa, xb, yb, fh, rnd, lamps)
    for lx in lamps:
        S.sconce(ops, lx, z(0.7), 1.0)
        LAMPS.append((lx, yb))
    # Kontaktschatten auf dem Boden
    ops.rect(xa, yb - 0.26, xb, yb, fill=(0, 0, 0, 40))
    ops.rect(xa, yb - 0.1, xb, yb, fill=(0, 0, 0, 50))


def tiles_wall(ops, x0, y0, x1, y1):
    ops.rect(x0, y0, x1, y1, fill=(224, 226, 222, 255))
    top = y0 + 0.62
    s = 0.17
    r = 0
    y = y0 + 0.06
    while y < top - 0.01:
        x = x0 + (s / 2 if r % 2 else 0)
        while x < x1:
            ops.rect(max(x0, x) + 0.008, y + 0.008, min(x1, x + s) - 0.008, min(top, y + s) - 0.008, fill=(238, 240, 236, 255), outline=(150, 160, 164, 255), width=0.008)
            x += s
        y += s
        r += 1
    ops.rect(x0, y0, x1, y0 + 0.06, fill=(60, 72, 76, 255))
    ops.rect(x0, top - 0.02, x1, top + 0.04, fill=(68, 120, 112, 255))
    ops.rect(x0, top + 0.04, x1, y1, fill=(200, 208, 204, 255))
    ops.rect(x0, y1 - 0.05, x1, y1, fill=(232, 236, 232, 255))


def dome_glass(ops, x0, y0, x1, y1, rnd):
    ops.rect(x0, y0, x1, y1, fill=NIGHT)
    h = y1 - y0
    pts = [(x0, y0), (x1, y0)]
    n = int((x1 - x0) / 0.15)
    for k in range(n + 1):
        t = 1 - k / n
        pts.append((x0 + (x1 - x0) * t, y0 + h * 0.2 + 0.05 * math.sin(t * 9 + 1) + 0.03 * math.sin(t * 23)))
    ops.poly(pts, fill=SNOW)
    ops.rect(x0, y0, x1, y0 + 0.05, fill=SNOW_D)
    # Polarlicht: weiche gruene Baender
    for k in range(3):
        yy = y0 + h * (0.55 + 0.12 * k)
        ops.line([(x0, yy), (x0 + (x1 - x0) * 0.3, yy + 0.08), (x0 + (x1 - x0) * 0.65, yy - 0.05), (x1, yy + 0.06)], fill=(110, 230, 170, 40 + 20 * k), width=0.12)
    for _ in range(int((x1 - x0) * 14)):
        sx, sy = rnd.uniform(x0 + 0.03, x1 - 0.03), rnd.uniform(y0 + h * 0.3, y1 - 0.04)
        r = rnd.choice((0.006, 0.009, 0.012))
        ops.ellipse(sx, sy, r, r, fill=STAR)
    mx = x0 + (x1 - x0) * 0.72
    ops.ellipse(mx, y1 - 0.2, 0.09, 0.09, fill=(250, 244, 214, 255))
    ops.ellipse(mx + 0.04, y1 - 0.18, 0.075, 0.075, fill=NIGHT)
    x = x0
    while x <= x1 + 0.01:                                               # Messingsprossen
        ops.line([(x, y0), (x, y1)], fill=OUTLINE, width=0.05)
        ops.line([(x, y0), (x, y1)], fill=BRASS_D, width=0.028)
        x += 0.55
    for yy in (y0 + 0.02, y0 + h * 0.5, y1 - 0.03):
        ops.line([(x0, yy), (x1, yy)], fill=OUTLINE, width=0.045)
        ops.line([(x0, yy), (x1, yy)], fill=BRASS, width=0.025)
    ops.rect(x0, y0, x1, y0 + 0.12, fill=WOOD_D)
    ops.line([(x0, y0 + 0.12), (x1, y0 + 0.12)], fill=BRASS, width=0.02)


def railing_face(ops, x0, y0, x1, y1, rnd, low=False):
    h = y1 - y0
    ops.rect(x0, y0, x1, y1, fill=NIGHT_L)
    pts = [(x0, y0), (x1, y0)]
    n = max(2, int((x1 - x0) / 0.15))
    for k in range(n + 1):
        t = 1 - k / n
        pts.append((x0 + (x1 - x0) * t, y0 + h * 0.42 + 0.06 * math.sin(t * 7 + 2)))
    ops.poly(pts, fill=SNOW)
    for _ in range(int((x1 - x0) * 8)):
        sx, sy = rnd.uniform(x0, x1), rnd.uniform(y0 + h * 0.55, y1)
        ops.ellipse(sx, sy, 0.008, 0.008, fill=STAR)
    tx = x0 + 0.3
    while tx < x1:
        tr = rnd.uniform(0.12, 0.2)
        ops.poly([(tx - tr, y0 + h * 0.42), (tx + tr, y0 + h * 0.42), (tx, y0 + h * 0.42 + tr * 2.6)], fill=(36, 62, 50, 255))
        tx += rnd.uniform(0.35, 0.7)
    top = y0 + (0.42 if low else 0.6)
    ops.rect(x0, y0, x1, y0 + 0.08, fill=IRON, outline=OUTLINE, width=0.02)
    x = x0 + 0.1
    while x < x1:
        ops.line([(x, y0 + 0.04), (x, top)], fill=OUTLINE, width=0.05)
        ops.line([(x, y0 + 0.04), (x, top)], fill=BRASS_D, width=0.025)
        x += 0.42
    for yy in (top, y0 + (0.22 if low else 0.3)):
        ops.line([(x0, yy), (x1, yy)], fill=OUTLINE, width=0.06)
        ops.line([(x0, yy), (x1, yy)], fill=BRASS, width=0.032)
    ops.line([(x0, top + 0.012), (x1, top + 0.012)], fill=alpha(BRASS_L, 200), width=0.012)


def bellows_face(ops, ctx, x0, y0, x1, y1):
    ops.rect(x0, y0, x1, y1, fill=(50, 48, 54, 255))
    x = x0
    k = 0
    while x < x1:
        ops.rect(x, y0, min(x1, x + 0.09), y1, fill=(64, 62, 68, 255) if k % 2 == 0 else (38, 36, 42, 255))
        x += 0.09
        k += 1
    ops.rect(x0, y1 - 0.07, x1, y1, fill=(80, 78, 86, 255))
    ops.rect(x0, y0, x1, y0 + 0.05, fill=(28, 26, 30, 255))
    wall = ctx["wall"]
    for xx in (x0 + wall / 2, x1 - wall / 2):                           # Tuerzargen in den Wagenwaenden
        ops.rect(xx - wall / 2, y0, xx + wall / 2, y1, fill=STEEL_D)
        ops.rect(xx - wall / 2 + 0.05, y0 + 0.05, xx + wall / 2 - 0.05, y1 - 0.05, fill=IRON, outline=BRASS_D, width=0.02)


# --- Einrichtung je Raum auf der Nordwand (x in Welt, z als Bildhoehe ueber yb)

def face_office(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    # Fahrplan an der Wand
    bx = -25.65
    ops.rect(bx - 0.42, z(0.4), bx + 0.42, z(0.86), fill=WOOD_X, outline=OUTLINE, width=0.02)
    ops.rect(bx - 0.38, z(0.44), bx + 0.38, z(0.82), fill=PAPER, outline=OUTLINE, width=0.012)
    ops.rect(bx - 0.38, z(0.74), bx + 0.38, z(0.82), fill=(170, 44, 50, 255))
    ops.textf(bx, z(0.78), "TIMETABLE", 0.05, CREAM, kind="black")
    for k in range(5):
        yy = z(0.69 - k * 0.05)
        ops.line([(bx - 0.33, yy), (bx - 0.05, yy)], fill=INK, width=0.012)
        ops.line([(bx + 0.02, yy), (bx + 0.33, yy)], fill=(120, 100, 70, 255), width=0.012)
    # Ueberwachungspult: drei Monitore auf einem Sims (Security-Konsole liegt davor)
    sx, sy = ctx["surveillance"]
    ops.rect(sx - 0.62, z(0.3), sx + 0.62, z(0.38), fill=OAK_D, outline=OUTLINE, width=0.02)
    for k, mx in enumerate((sx - 0.4, sx, sx + 0.4)):
        ops.rect(mx - 0.18, z(0.4), mx + 0.18, z(0.7), fill=IRON, outline=OUTLINE, width=0.025)
        ops.rect(mx - 0.15, z(0.43), mx + 0.15, z(0.66), fill=(60, 120, 150, 255))
        ops.glow(mx, z(0.55), 0.3, (120, 220, 255, 255), 0.35)
        ops.line([(mx - 0.12, z(0.5 + 0.03 * k)), (mx - 0.02, z(0.6)), (mx + 0.06, z(0.47)), (mx + 0.12, z(0.58))], fill=(170, 240, 255, 255), width=0.01)
        ops.rect(mx - 0.04, z(0.38), mx + 0.04, z(0.4), fill=IRON)
    ops.textf(sx, z(0.26), "CAMERAS", 0.045, BRASS, kind="black")
    # Wanduhr
    cx = -23.1
    ops.ellipse(cx, z(0.62), 0.11, 0.11, fill=BRASS, outline=OUTLINE, width=0.02)
    ops.ellipse(cx, z(0.62), 0.085, 0.085, fill=CREAM, outline=BRASS_D, width=0.01)
    ops.line([(cx, z(0.62)), (cx, z(0.69))], fill=INK, width=0.012)
    ops.line([(cx, z(0.62)), (cx + 0.05, z(0.6))], fill=INK, width=0.012)


def face_luggage(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    if xb - xa < 1.0:
        return
    for sz in (0.3, 0.6):                                                # zwei Regalboeden mit Koffern
        ops.rect(xa + 0.05, z(sz), xb - 0.05, z(sz + 0.04), fill=OAK_D, outline=OUTLINE, width=0.015)
        x = xa + 0.1
        while x < xb - 0.3:
            cw = rnd.uniform(0.3, 0.5)
            ch = rnd.uniform(0.16, 0.24)
            col = rnd.choice([(150, 96, 56, 255), (110, 70, 44, 255), (88, 96, 110, 255), (160, 130, 90, 255)])
            S.suitcase(ops, x, z(sz + 0.045), min(xb - 0.1, x + cw), z(sz + 0.045 + ch), col, rnd)
            x += cw + 0.06
    for sx in (xa + 0.2, xb - 0.2):
        ops.line([(sx, z(0.1)), (sx, z(0.88))], fill=OUTLINE, width=0.04)
        ops.line([(sx, z(0.1)), (sx, z(0.88))], fill=BRASS_D, width=0.02)


def face_dining(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    # Speisekarte und Weinregal am Westende, Ablage mit Flaschen am Ostende
    if xa < -9.8:
        ops.rect(xa + 0.08, z(0.45), xa + 0.3, z(0.8), fill=WOOD_X, outline=OUTLINE, width=0.015)
        ops.rect(xa + 0.1, z(0.47), xa + 0.28, z(0.78), fill=PAPER)
        ops.textf(xa + 0.19, z(0.73), "MENU", 0.03, INK, kind="black")
        for k in range(4):
            ops.line([(xa + 0.12, z(0.68 - k * 0.05)), (xa + 0.26, z(0.68 - k * 0.05))], fill=CREAM_D, width=0.008)
    if xb > -4.8:
        ops.rect(xb - 0.38, z(0.42), xb - 0.05, z(0.46), fill=OAK_D, outline=OUTLINE, width=0.015)
        for k, col in enumerate(((60, 110, 70, 255), (120, 30, 40, 255), (190, 160, 70, 255))):
            bx = xb - 0.32 + k * 0.1
            ops.rect(bx - 0.025, z(0.46), bx + 0.025, z(0.62), fill=col, outline=OUTLINE, width=0.01)
            ops.rect(bx - 0.012, z(0.62), bx + 0.012, z(0.68), fill=col, outline=OUTLINE, width=0.008)


def face_telegraph(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    if xb - xa < 1.5:
        return
    # Kabelbaum mit Porzellanisolatoren
    for k in range(4):
        yy = z(0.9 - k * 0.02)
        ops.line([(xa + 0.05, yy), (xb - 0.05, yy)], fill=(40, 36, 44, 255), width=0.012)
    x = xa + 0.25
    while x < xb - 0.2:
        ops.ellipse(x, z(0.91), 0.025, 0.03, fill=CREAM, outline=OUTLINE, width=0.01)
        x += 0.45
    # Sims mit Klopfer (Sounder) und Papierstreifen-Spule
    sx = xa + 0.55
    ops.rect(xa + 0.1, z(0.3), xa + 1.2, z(0.36), fill=OAK_D, outline=OUTLINE, width=0.015)
    ops.rect(sx - 0.2, z(0.36), sx + 0.2, z(0.5), fill=WOOD_X, outline=OUTLINE, width=0.015)
    ops.rect(sx - 0.12, z(0.5), sx - 0.04, z(0.6), fill=BRASS, outline=OUTLINE, width=0.012)
    ops.rect(sx + 0.04, z(0.5), sx + 0.12, z(0.6), fill=BRASS, outline=OUTLINE, width=0.012)
    ops.line([(sx - 0.18, z(0.62)), (sx + 0.16, z(0.56))], fill=OUTLINE, width=0.03)
    ops.line([(sx - 0.18, z(0.62)), (sx + 0.16, z(0.56))], fill=BRASS_L, width=0.015)
    for k in range(3):
        ops.line([(sx - 0.15 + k * 0.1, z(0.5)), (sx - 0.1 + k * 0.1, z(0.88))], fill=(40, 36, 44, 255), width=0.01)
    rx = xa + 1.0
    ops.ellipse(rx, z(0.46), 0.1, 0.1, fill=CREAM, outline=OUTLINE, width=0.015)
    ops.ellipse(rx, z(0.46), 0.03, 0.03, fill=BRASS, outline=OUTLINE, width=0.01)
    ops.line([(rx + 0.1, z(0.46)), (rx + 0.35, z(0.38)), (rx + 0.6, z(0.4))], fill=CREAM, width=0.025)
    # Plakat "TELEGRAMS"
    ops.rect(xb - 0.5, z(0.4), xb - 0.08, z(0.6), fill=(34, 56, 110, 255), outline=OUTLINE, width=0.015)
    ops.textf(xb - 0.29, z(0.5), "TELEGRAMS", 0.045, CREAM, kind="black")


def face_dynamo(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    if xb - xa < 1.2:
        return
    # Sicherungstafel: dunkle Platte mit Keramiksicherungen
    fx = xa + 0.55
    ops.rect(fx - 0.4, z(0.36), fx + 0.4, z(0.82), fill=(60, 52, 48, 255), outline=OUTLINE, width=0.025)
    for r in range(3):
        for c in range(4):
            cx, cy = fx - 0.3 + c * 0.2, z(0.72 - r * 0.14)
            ops.rect(cx - 0.05, cy - 0.04, cx + 0.05, cy + 0.04, fill=CREAM, outline=OUTLINE, width=0.01)
            ops.rect(cx - 0.06, cy - 0.015, cx - 0.045, cy + 0.015, fill=BRASS)
            ops.rect(cx + 0.045, cy - 0.015, cx + 0.06, cy + 0.015, fill=BRASS)
            if (r + c) % 5 == 1:
                ops.ellipse(cx, cy, 0.012, 0.012, fill=RED_LAMP)
    ops.textf(fx, z(0.4), "FUSES", 0.04, BRASS, kind="black")
    # Messerschalter und zwei Instrumente
    sx = xa + 1.45
    ops.rect(sx - 0.35, z(0.36), sx + 0.35, z(0.82), fill=(72, 64, 60, 255), outline=OUTLINE, width=0.025)
    for k in range(3):
        S.knife_switch(ops, sx - 0.22 + k * 0.22, z(0.5), 0.9, closed=(k != 1))
    S.gauge(ops, sx - 0.15, z(0.72), 0.07, 40)
    S.gauge(ops, sx + 0.15, z(0.72), 0.07, 80)
    # Warnschild
    if xb - xa > 2.0:
        ops.rect(xb - 0.5, z(0.5), xb - 0.1, z(0.7), fill=(236, 196, 60, 255), outline=OUTLINE, width=0.02)
        ops.poly([(xb - 0.3, z(0.68)), (xb - 0.38, z(0.55)), (xb - 0.22, z(0.55))], fill=INK)
        ops.line([(xb - 0.3, z(0.64)), (xb - 0.3, z(0.59))], fill=(236, 196, 60, 255), width=0.012)
        ops.textf(xb - 0.3, z(0.53), "HIGH VOLTAGE", 0.028, INK, kind="black")


def face_generator(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    S.gauge(ops, 10.85, z(0.66), 0.09, 55)
    S.gauge(ops, 11.3, z(0.66), 0.09, 25)
    S.pipe(ops, [(10.85, z(0.57)), (10.85, z(0.4)), (11.3, z(0.4)), (11.3, z(0.57))], 0.025, BRASS_D, flange=False)
    ops.rect(8.6, z(0.4), 8.78, z(0.84), fill=(60, 52, 48, 255), outline=OUTLINE, width=0.015)
    for k in range(4):
        ops.ellipse(8.69, z(0.46 + k * 0.1), 0.025, 0.025, fill=(RED_LAMP if k == 0 else GREEN_LAMP), outline=OUTLINE, width=0.008)


def face_mail(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    # Ueber dem Sortiertisch (Objekt "admintisch" vor der Wand): Sortierregal mit Faechern voller Briefe, darueber
    # ein Schild "MAIL ROOM" und eine Messingleiste mit Haken fuer Postsaecke
    ax, ay = ctx["admin_table"]
    rx0, rx1 = ax - 0.85, ax + 0.85
    ops.rect(rx0, z(0.4), rx1, z(0.86), fill=WOOD_X, outline=OUTLINE, width=0.025)
    for r in range(3):
        for c in range(7):
            cx0 = rx0 + 0.04 + c * (rx1 - rx0 - 0.08) / 7
            cx1 = cx0 + (rx1 - rx0 - 0.08) / 7 - 0.03
            cy0 = z(0.43 + r * 0.14)
            ops.rect(cx0, cy0, cx1, cy0 + 0.11, fill=(50, 32, 22, 255), outline=OUTLINE, width=0.008)
            v = rnd.random()
            if v < 0.6:
                for k in range(3):
                    ops.rect(cx0 + 0.02 + k * 0.01, cy0 + 0.015 + k * 0.02, cx1 - 0.02, cy0 + 0.035 + k * 0.02, fill=PAPER, outline=INK, width=0.005)
            elif v < 0.8:
                ops.rect(cx0 + 0.03, cy0 + 0.015, cx1 - 0.03, cy0 + 0.08, fill=(170, 134, 90, 255), outline=OUTLINE, width=0.008)
    ops.rect(rx0, z(0.84), rx1, z(0.9), fill=WOOD_D, outline=OUTLINE, width=0.015)
    ops.line([(rx0 + 0.05, z(0.38)), (rx1 - 0.05, z(0.38))], fill=BRASS, width=0.025)
    for k in range(5):
        hx = rx0 + 0.25 + k * (rx1 - rx0 - 0.5) / 4
        ops.line([(hx, z(0.38)), (hx, z(0.33))], fill=BRASS_D, width=0.015)
    # Faecher am Ostende, Postsaecke am Westende
    px0, px1 = xb - 0.62, xb - 0.08
    ops.rect(px0, z(0.36), px1, z(0.86), fill=WOOD_D, outline=OUTLINE, width=0.02)
    for r in range(4):
        for c in range(3):
            cx0 = px0 + 0.03 + c * 0.18
            cy0 = z(0.39 + r * 0.12)
            ops.rect(cx0, cy0, cx0 + 0.15, cy0 + 0.09, fill=(50, 32, 22, 255), outline=OUTLINE, width=0.008)
            if (r * 3 + c) % 3 != 1:
                ops.rect(cx0 + 0.02, cy0 + 0.01, cx0 + 0.12, cy0 + 0.05, fill=PAPER, outline=INK, width=0.006)
    for k, bx in enumerate((xa + 0.25, xa + 0.6)):
        ops.ellipse(bx, z(0.75), 0.02, 0.02, fill=BRASS, outline=OUTLINE, width=0.01)
        ops.poly([(bx - 0.03, z(0.73)), (bx + 0.03, z(0.73)), (bx + 0.14, z(0.42)), (bx + 0.1, z(0.33)), (bx - 0.1, z(0.33)), (bx - 0.14, z(0.42))],
                 fill=(188, 164, 118, 255), outline=OUTLINE, width=0.018)
        ops.line([(bx - 0.03, z(0.7)), (bx + 0.03, z(0.7))], fill=(120, 90, 60, 255), width=0.015)
        ops.textf(bx, z(0.48), "MAIL", 0.035, (120, 90, 60, 255), kind="black")


def face_cab(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    S.gauge(ops, 23.95, z(0.66), 0.1, 62)
    S.gauge(ops, 24.4, z(0.66), 0.1, 30)
    S.pipe(ops, [(23.95, z(0.56)), (23.95, z(0.42)), (24.4, z(0.42)), (24.4, z(0.56))], 0.025, BRASS_D, flange=False)
    # Regler-Hebel und Pfeifenzug
    lx = 22.15
    ops.rect(lx - 0.08, z(0.36), lx + 0.08, z(0.46), fill=IRON, outline=OUTLINE, width=0.015)
    ops.line([(lx, z(0.42)), (lx + 0.22, z(0.8))], fill=OUTLINE, width=0.05)
    ops.line([(lx, z(0.42)), (lx + 0.22, z(0.8))], fill=BRASS, width=0.025)
    ops.ellipse(lx + 0.22, z(0.8), 0.035, 0.035, fill=WOOD_D, outline=OUTLINE, width=0.012)
    ops.line([(23.3, z(0.95)), (23.3, z(0.7))], fill=(40, 36, 44, 255), width=0.012)
    ops.ellipse(23.3, z(0.68), 0.03, 0.03, fill=WOOD_D, outline=OUTLINE, width=0.01)
    S.plate(ops, 23.45, z(0.46), 0.5, 0.1, "No. 4  POLARIS", size=0.055)


def face_tender(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    ops.rect(xa, yb, xb, z(0.5), fill=(0, 0, 0, 70))
    for _ in range(int((xb - xa) * 10)):
        coal_lump(ops, rnd.uniform(xa + 0.1, xb - 0.1), z(rnd.uniform(0.05, 0.3)), rnd.uniform(0.04, 0.09), rnd)
    ops.textf((xa + xb) / 2, z(0.72), "COAL  8 t", 0.12, (200, 200, 210, 160), kind="black")


def face_sleeper(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    if xb - xa < 1.0:
        return
    # Gepaecknetz links, Leselampe rechts
    nx0, nx1 = xa + 0.1, xa + 0.6
    ops.rect(nx0, z(0.72), nx1, z(0.88), fill=(60, 52, 48, 255), outline=OUTLINE, width=0.015)
    for k in range(7):
        ops.line([(nx0 + k * 0.08, z(0.72)), (nx0 + k * 0.08 + 0.16, z(0.88))], fill=(140, 130, 110, 255), width=0.008)
        ops.line([(nx0 + k * 0.08 + 0.16, z(0.72)), (nx0 + k * 0.08, z(0.88))], fill=(140, 130, 110, 255), width=0.008)
    ops.rect(nx0 + 0.08, z(0.74), nx0 + 0.3, z(0.84), fill=(150, 96, 56, 255), outline=OUTLINE, width=0.012)
    ops.rect(nx0 + 0.32, z(0.74), nx0 + 0.45, z(0.8), fill=(120, 140, 110, 255), outline=OUTLINE, width=0.012)
    S.sconce(ops, xb - 0.3, z(0.74), 0.7)
    LAMPS.append((xb - 0.3, yb))
    ops.rect(xa + 0.12, z(0.45), xa + 0.3, z(0.68), fill=GLASS[:3] + (255,), outline=BRASS, width=0.015)    # Spiegel
    ops.line([(xa + 0.15, z(0.5)), (xa + 0.27, z(0.65))], fill=alpha(WHITE, 140), width=0.012)


def face_kitchen(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    # Dunstabzug ueber der Herdzeile (Herd ist das GLASS-Objekt davor)
    hx0, hx1 = -9.6, -5.0
    hx0, hx1 = max(xa + 0.05, hx0), min(xb - 0.05, hx1)
    ops.poly([(hx0 - 0.1, z(0.62)), (hx1 + 0.1, z(0.62)), (hx1 - 0.2, z(0.82)), (hx0 + 0.2, z(0.82))], fill=STEEL, outline=OUTLINE, width=0.025)
    ops.rect(hx0 + 0.2, z(0.82), hx1 - 0.2, z(0.95), fill=STEEL_D, outline=OUTLINE, width=0.02)
    ops.line([(hx0 - 0.05, z(0.64)), (hx1 + 0.05, z(0.64))], fill=BRASS, width=0.02)
    x = hx0 + 0.3
    while x < hx1 - 0.25:                                                # Filtergitter
        ops.rect(x, z(0.66), x + 0.3, z(0.76), fill=(60, 66, 76, 255), outline=OUTLINE, width=0.012)
        for k in range(5):
            ops.line([(x + 0.02, z(0.675 + k * 0.02)), (x + 0.28, z(0.675 + k * 0.02))], fill=(120, 128, 140, 255), width=0.006)
        x += 0.36
    for lx in (hx0 + 0.6, (hx0 + hx1) / 2, hx1 - 0.6):
        ops.glow(lx, z(0.6), 0.45, WARM, 0.5)
        ops.ellipse(lx, z(0.61), 0.05, 0.03, fill=BULB, outline=OUTLINE, width=0.012)
    # Regal mit Toepfen und Gewuerzen links, Uhr rechts
    if xa < hx0 - 0.3:
        ops.rect(xa + 0.05, z(0.5), hx0 - 0.1, z(0.54), fill=OAK_D, outline=OUTLINE, width=0.015)
        ops.rect(xa + 0.08, z(0.54), xa + 0.26, z(0.68), fill=(190, 80, 60, 255), outline=OUTLINE, width=0.012)
    for k in range(3):
        ops.rect(xb - 0.3 + k * 0.08, z(0.4), xb - 0.25 + k * 0.08, z(0.52), fill=rnd.choice([(190, 140, 60, 255), (120, 160, 80, 255), (200, 80, 70, 255)]), outline=OUTLINE, width=0.008)
    cx = xb - 0.22
    ops.ellipse(cx, z(0.74), 0.09, 0.09, fill=IRON, outline=OUTLINE, width=0.015)
    ops.ellipse(cx, z(0.74), 0.07, 0.07, fill=CREAM)
    ops.line([(cx, z(0.74)), (cx, z(0.8))], fill=INK, width=0.01)
    ops.line([(cx, z(0.74)), (cx + 0.04, z(0.72))], fill=INK, width=0.01)


def face_platform(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    z = lambda v: yb + v
    S.lantern(ops, xa + 0.3, z(0.55), 0.9, RED_LAMP)
    S.lantern(ops, xb - 0.3, z(0.55), 0.9, RED_LAMP)
    LAMPS.append((xa + 0.3, yb))


def face_boards(ops, ctx, xa, xb, yb, fh, rnd, lamps):
    pass


ROOM_FACE = {"office": face_office, "luggage": face_luggage, "dining": face_dining, "telegraph": face_telegraph,
             "dynamo": face_dynamo, "generator": face_generator, "mail": face_mail, "cab": face_cab, "tender": face_tender,
             "sleeper": face_sleeper, "kitchen": face_kitchen, "platform": face_platform, "boards": face_boards}


def railings_top(ops, ctx):
    """Gelaender der offenen Plattform und des Umlaufs von oben: Messinglinie mit Pfosten auf der Wandkrone."""
    g = ctx["room_geom"]["platform"]
    x0, y0, x1, y1 = g.bounds
    wall = ctx["wall"]
    for pts in ([(x0 - 0.2, y0 - 0.2), (x0 - 0.2, y1 + 0.2)], [(x0 - 0.2, y0 - 0.2), (x1, y0 - 0.2)]):
        ops.line(pts, fill=OUTLINE, width=0.07)
        ops.line(pts, fill=BRASS, width=0.035)
    k = 0
    for pts in ([(x0 - 0.2, y0 - 0.2), (x0 - 0.2, y1 + 0.2)], [(x0 - 0.2, y0 - 0.2), (x1, y0 - 0.2)]):
        ln = LineString(pts)
        d = 0.0
        while d <= ln.length:
            p = ln.interpolate(d)
            ops.ellipse(p.x, p.y, 0.045, 0.045, fill=BRASS_D, outline=OUTLINE, width=0.015)
            d += 0.45
            k += 1
    # Umlauf der Lok: Handlauf an der Suedkante
    b = ctx["room_geom"]["boards"]
    x0, y0, x1, y1 = b.bounds
    ops.line([(x0, y0 - 0.2), (x1 + 0.1, y0 - 0.2)], fill=OUTLINE, width=0.06)
    ops.line([(x0, y0 - 0.2), (x1 + 0.1, y0 - 0.2)], fill=BRASS, width=0.03)
    x = x0 + 0.2
    while x < x1:
        ops.ellipse(x, y0 - 0.2, 0.04, 0.04, fill=BRASS_D, outline=OUTLINE, width=0.015)
        x += 0.5


def outlines(ops, ctx):
    walk = ctx["walk"]
    k = 0
    for p in parts(walk):
        for ring in [list(p.exterior.coords)] + [list(h.coords) for h in p.interiors]:
            wob = HD.wobble(ring, amp=0.006, seed=900 + k, step=0.1, closed=True)
            ops.line(wob + [wob[0]], fill=OUTLINE, width=0.075)
            k += 1
    for c in ctx["cars"]:
        for deck in ["A"] + (["B"] if c["kind"] == "dd" else []):
            x0, y0, x1, y1 = car_rect(c, deck, ctx)
            ops.poly(HD.wobble(S.rrect_pts(x0, y0, x1, y1, 0.3), amp=0.008, seed=int(x0 * 3) & 0xff, step=0.12, closed=True),
                     outline=OUTLINE, width=0.085)
    for g in ctx["gangways"]:
        x0, y0, x1, y1 = g["box"]
        ops.line([(x0, y0), (x1, y0)], fill=OUTLINE, width=0.075)
        ops.line([(x0, y1), (x1, y1)], fill=OUTLINE, width=0.075)


def glows(ops, ctx):
    for x, y in LAMPS:
        ops.glow(x, y - 0.55, 1.15, WARM, 0.34)
        ops.ellipse(x, y - 0.5, 0.55, 0.3, fill=alpha(WARM, 26))
    # Kuppel: Mondlicht auf dem Teppich
    g = ctx["room_geom"]["dome"].bounds
    for xx in (1.5, 3.4):
        ops.glow(xx, g[3] - 1.1, 1.4, (190, 220, 255, 255), 0.22)
    # Kessel: Feuerschein am Feuerloch im Fuehrerstand
    bx0, by0, bx1, by1 = ctx["boiler"]
    ops.glow(bx0 - 0.25, (by0 + by1) / 2, 1.0, (255, 150, 70, 255), 0.4)


# ------------------------------------------------------------------ Nachbearbeitung

def ambient(img, walk, bounds, ppm):
    x0, y0, x1, y1 = bounds
    s = 8
    lw, lh = int((x1 - x0) * s), int((y1 - y0) * s)
    small = Image.new("L", (lw, lh), 255)
    d = ImageDraw.Draw(small)
    P = lambda x, y: ((x - x0) * s, (y1 - y) * s)
    for p in parts(walk):
        d.polygon([P(*q) for q in p.exterior.coords], fill=0)
        for h in p.interiors:
            d.polygon([P(*q) for q in h.coords], fill=255)
    small = small.filter(ImageFilter.GaussianBlur(0.32 * s)).resize(img.size, Image.BICUBIC)
    inside = A.walk_mask(walk, x0, y0, x1, y1, ppm, img.width, img.height)
    amount = ImageChops.multiply(small, inside).point(lambda v: int(v * AO_STRENGTH))
    rgb = Image.composite(Image.new("RGB", img.size, (6, 4, 10)), img.convert("RGB"), amount)
    if img.mode != "RGBA":
        return rgb
    out = rgb.convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


# ------------------------------------------------------------------ Hauptfunktion

def render(ctx, ppm=128):
    """Bodenkachel (RGBA): deckend sind Wagenkaesten samt Innenraeumen, Faltenbaelge, Puffer und das Oberdeck-Feld;
    alles draussen bleibt durchsichtig fuer den Scroll-Streifen (render_scroll). Lichtkegel und Schlussleuchten-
    Schein bleiben halbtransparent auf der Kachel, unter den Wagen liegt ein weiches Schattenband."""
    F = Floor(ctx["bounds"], ppm, rgba=True)
    mats = materials(ppm)
    rnd = random.Random(3)
    ops_ground = TOps()
    shadow_band(F, ctx)
    panel_and_pad(F, ops_ground, ctx)
    bodies(F, ops_ground, ctx)
    floors(F, ctx, mats)
    runboard_floor(F, ctx, mats)
    ops_walls = TOps()
    faces(ops_walls, ctx)                      # fuellt LAMPS
    railings_top(ops_walls, ctx)
    runboard_ops(ops_walls, ctx, rnd)
    outlines(ops_walls, ctx)
    couplers(ops_walls, ctx)
    ops_floor = TOps()
    floor_decor(ops_floor, ctx, rnd)
    glows(ops_floor, ctx)
    crown_rim(ops_floor, ctx)
    inner_walls(ops_floor, ctx)
    ops = TOps()
    ops.ops = ops_ground.ops + ops_floor.ops + ops_walls.ops
    img = render_ops(F.img, ops, ctx["bounds"], ppm)
    img = ambient(img, ctx["walk"], ctx["bounds"], ppm)
    return grain_rgba(img, GRAIN, seed=4, scale=2)
