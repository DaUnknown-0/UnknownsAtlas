# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# preview_park.py - Ausschnitt des Moonlight Carnival wie im Spiel: Bodenkacheln (80 px/m, auf die
# Objektaufloesung 160 px/m hochskaliert) + Laternen-Lichtschein (wie AtlasParkWorld: radialer Fleck
# 4,6 m, warm, Alpha 0,3, unter allen Objekten) + Objekt-Sprites + Task-Bloecke + Laternenpfaehle,
# alles nach Standlinie sortiert. Vorher einmal tools/gen_park.py laufen lassen.
#   python tools/preview_park.py <raum>|all|x0 y0 x1 y1 [--figure x y] [--lamps-off] [--out name]
#   python tools/preview_park.py --full                  ganze Karte, 40 px/m
#   -> tools/_park/view_<name>.png
#   python tools/preview_park.py --vollpass vorher|nachher [raum ...]
#   -> tools/_vollpass_park/<raum>_<stage>.png (je Raum, 160 px/m, mit Spielerfigur) + gesamt_<stage>.png
#
# Die Vorschau liest Konsolen- und Laternenplaetze aus src/AtlasParkLayout.cs (das, was der Builder
# baut), nicht aus einer eigenen Rechnung.

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point
from shapely.ops import unary_union

import gen_park as GP
import handdraw as HD
import park_geo as G
import park_layout as L

OUT = Path(__file__).resolve().parent / "_park"
VOLLPASS = Path(__file__).resolve().parent / "_vollpass_park"
PPM = GP.PROP_PPM
FPPM = GP.FLOOR_PPM
BX0, BY0, BX1, BY1 = L.BOUNDS
LAMP_GLOW_W = 4.6                      # AtlasParkWorld.BuildLamps: Breite des Lichtflecks in m
LAMP_GLOW_RGBA = (255, 199, 122, 77)   # Color(1, 0.78, 0.48, 0.3)


def layout_cs():
    return (GP.PROJECT / "src" / "AtlasParkLayout.cs").read_text(encoding="utf-8")


def consoles_from_cs(src):
    pos = {m.group(1): (float(m.group(2)), float(m.group(3)))
           for m in re.finditer(r'\["([^"]+)"\] = new\((-?[\d.]+)f, (-?[\d.]+)f\)', src)}
    for n in ("EmergencyButton", "SurveillanceConsole", "AdminTable", "FreeplayLaptop"):
        m = re.search(n + r' = new\((-?[\d.]+)f, (-?[\d.]+)f\)', src)
        if m:
            pos[n] = (float(m.group(1)), float(m.group(2)))
    return pos


def lamps_from_cs(src):
    m = re.search(r"Lamps = new Vector2\[\] \{([^}]*)\}", src)
    pts = [(float(a), float(b)) for a, b in re.findall(r"new\((-?[\d.]+)f, (-?[\d.]+)f\)", m.group(1))] if m else []
    pv = re.search(r"LampPivot = new\((-?[\d.]+)f, (-?[\d.]+)f\)", src)
    pivot = (float(pv.group(1)), float(pv.group(2))) if pv else (0.5, 0.1)
    return pts, pivot


def floor(x0, y0, x1, y1, ppm):
    """Bodenkacheln aus assets/ zusammensetzen, Ausschnitt in Weltmetern, Ausgabe mit ppm px/m."""
    cols, _ = GP.FLOOR_TILES
    tiles = sorted(GP.ASSETS.glob("park_floor_*.jpg"), key=lambda p: int(p.stem.split("_")[-1]))
    tw, th = Image.open(tiles[0]).size
    px0, py0 = int((x0 - BX0) * FPPM), int((BY1 - y1) * FPPM)
    px1, py1 = int((x1 - BX0) * FPPM), int((BY1 - y0) * FPPM)
    out = Image.new("RGB", (px1 - px0, py1 - py0), GP.VOID)
    for i, t in enumerate(tiles):
        tx, ty = (i % cols) * tw, (i // cols) * th
        im = Image.open(t)
        a0, b0, a1, b1 = max(px0, tx), max(py0, ty), min(px1, tx + im.width), min(py1, ty + im.height)
        if a1 > a0 and b1 > b0:
            out.paste(im.crop((a0 - tx, b0 - ty, a1 - tx, b1 - ty)), (a0 - px0, b0 - py0))
    if ppm != FPPM:
        out = out.resize((int(round(out.width * ppm / FPPM)), int(round(out.height * ppm / FPPM))), Image.BICUBIC)
    return out.convert("RGBA")


def lamp_glow(img, x0, y1, ppm, lamps):
    """Lichtfleck je Laterne wie im Spiel (Make(64, 64): Alpha = (1 - r)^2), Alpha-Mischung auf dem Boden."""
    n = max(8, int(LAMP_GLOW_W * ppm))
    g = Image.new("L", (64, 64), 0)
    px = g.load()
    for yy in range(64):
        for xx in range(64):
            dx, dy = (xx - 31.5) / 32, (yy - 31.5) / 32
            a = max(0.0, 1 - (dx * dx + dy * dy) ** 0.5)
            px[xx, yy] = int(a * a * 255 * LAMP_GLOW_RGBA[3] / 255)
    g = g.resize((n, n), Image.BILINEAR)
    layer = Image.new("RGBA", (n, n), LAMP_GLOW_RGBA[:3] + (0,))
    layer.putalpha(g)
    for lx, ly in lamps:
        cx, cy = int(round((lx - x0) * ppm - n / 2)), int(round((y1 - ly) * ppm - n / 2))
        HD.paste_clipped(img, layer, cx, cy)


def render(x0, y0, x1, y1, ppm=PPM, figure=None, lamps_on=True, scale=1.0):
    src = layout_cs()
    img = floor(x0, y0, x1, y1, ppm)
    lamps, pivot = lamps_from_cs(src)
    if lamps_on:
        lamp_glow(img, x0, y1, ppm, lamps)
    sprites = []   # (Standlinie, Bild, Welt-x links, Welt-y unten)
    items = [(s, k) for s, k in L.OPAQUE if k] + [(s, k) for s, k in L.GLASS if k]
    for i, (s, kind) in enumerate(items):
        gx0, gy0, gx1, gy1 = G.shape(s).bounds
        if gx1 < x0 - 2 or gx0 > x1 + 2 or gy1 < y0 - 2 or gy0 > y1 + 8:
            continue
        im, wx, wy, base = GP.draw_block(kind, s, i)
        sprites.append((base, im, wx, wy))
    try:
        import park_consoles as PC
        pos = consoles_from_cs(src)
        own = PC.render_all(PPM, {k: v for k, v in pos.items() if "/" in k})
        for k, (im, ax, ay) in own.items():
            if k in pos:
                wx, wy = pos[k]
                sprites.append((wy, im, wx - ax / PPM, wy - ay / PPM))
    except ImportError:
        pass
    post = Image.open(GP.ASSETS / ("task_park_lamppost.png" if lamps_on else "task_park_lamppost_off.png")).convert("RGBA")
    for lx, ly in lamps:
        sprites.append((ly, post, lx - pivot[0] * post.width / PPM, ly - pivot[1] * post.height / PPM))
    if figure is not None:
        fx, fy = figure
        fim, fw, fh = HD.crewmate(PPM)
        sprites.append((fy + 0.001, fim, fx - fw / 2, fy - fh))
    sprites.sort(key=lambda t: -t[0])
    for _b, im, wx, wy in sprites:
        if ppm != PPM:
            im = im.resize((max(1, int(im.width * ppm / PPM)), max(1, int(im.height * ppm / PPM))), Image.LANCZOS)
        HD.paste_clipped(img, im, int(round((wx - x0) * ppm)), int(round((y1 - wy) * ppm)) - im.height)
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    return img


def stamp(img, text):
    """Beschriftung oben links (Abnahme-Bilder)."""
    d = ImageDraw.Draw(img, "RGBA")
    try:
        f = ImageFont.truetype("arialbd.ttf", 26)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle([0, 0, 16 + len(text) * 15, 40], fill=(0, 0, 0, 150))
    d.text((8, 6), text, font=f, fill=(255, 255, 255, 255))


def figure_spot(key, g, walk):
    """Standplatz der Massstabsfigur: frei von Hindernissen, moeglichst nah an der Raummitte."""
    obst = unary_union([G.shape(s) for s, _k in L.OPAQUE + L.GLASS]).buffer(0.6)
    free = g.intersection(walk).buffer(-0.5).difference(obst)
    c = g.centroid
    if free.is_empty:
        return (c.x, c.y)
    x0, y0, x1, y1 = g.bounds
    best, bd = (c.x, c.y), 1e9
    for i in range(25):
        for j in range(25):
            x, y = x0 + (x1 - x0) * i / 24, y0 + (y1 - y0) * j / 24
            if free.contains(Point(x, y)):
                dd = (x - c.x) ** 2 + (y - c.y) ** 2
                if dd < bd:
                    best, bd = (x, y), dd
    return best


def vollpass(stage, only=None):
    """Abnahme-Bilder des vollen Passes: je Raum ein Bild in 160 px/m mit Spielerfigur, dazu die Gesamtansicht."""
    VOLLPASS.mkdir(exist_ok=True)
    walk, *_ = G.build()
    rooms = G.rooms(walk)
    for key, (name, _s, g) in rooms.items():
        if only and key not in only:
            continue
        a, b, c, d = g.bounds
        x0, y0, x1, y1 = max(a - 1.5, BX0), max(b - 1.5, BY0), min(c + 1.5, BX1), min(d + 2.5, BY1)
        fig = figure_spot(key, g, walk)
        img = render(x0, y0, x1, y1, figure=fig).convert("RGB")
        stamp(img, f"{key} ({name}) {stage}, 160 px/m, {x1 - x0:.0f} x {y1 - y0:.0f} m")
        p = VOLLPASS / f"{key}_{stage}.png"
        img.save(p)
        print(p, img.size)
    if not only or "gesamt" in only:
        img = render(BX0, BY0, BX1, BY1, ppm=40).convert("RGB")
        stamp(img, f"gesamt {stage}, 40 px/m")
        p = VOLLPASS / f"gesamt_{stage}.png"
        img.save(p)
        print(p, img.size)


def main(argv):
    OUT.mkdir(exist_ok=True)
    figure = None
    lamps_on = True
    name = None
    rest = []
    i = 0
    if argv and argv[0] == "--vollpass":
        vollpass(argv[1] if len(argv) > 1 else "nachher", argv[2:] or None)
        return
    while i < len(argv):
        a = argv[i]
        if a == "--figure":
            figure = (float(argv[i + 1]), float(argv[i + 2]))
            i += 3
        elif a == "--lamps-off":
            lamps_on = False
            i += 1
        elif a == "--out":
            name = argv[i + 1]
            i += 2
        else:
            rest.append(a)
            i += 1
    walk, *_ = G.build()
    rooms = G.rooms(walk)
    jobs = []
    if rest == ["--full"]:
        im = render(BX0, BY0, BX1, BY1, ppm=40, lamps_on=lamps_on)
        im.convert("RGB").save(OUT / f"view_{name or 'full'}.png")
        print(OUT / f"view_{name or 'full'}.png", im.size)
        return
    if rest == ["all"]:
        for k, (_n, _s, g) in rooms.items():
            a, b, c, d = g.bounds
            jobs.append((k, (a - 1.5, b - 1.5, c + 1.5, d + 2.5)))
    elif len(rest) == 1:
        a, b, c, d = rooms[rest[0]][2].bounds
        jobs.append((rest[0], (a - 1.5, b - 1.5, c + 1.5, d + 2.5)))
    else:
        jobs.append((name or "rect", tuple(map(float, rest))))
    for nm, (x0, y0, x1, y1) in jobs:
        x0, y0, x1, y1 = max(x0, BX0), max(y0, BY0), min(x1, BX1), min(y1, BY1)
        im = render(x0, y0, x1, y1, figure=figure, lamps_on=lamps_on)
        im.convert("RGB").save(OUT / f"view_{name or nm}.png")
        print(OUT / f"view_{name or nm}.png", im.size)


if __name__ == "__main__":
    main(sys.argv[1:])
