# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_museum.py - museum_layout.py -> Bodenbild, Minimap, AtlasMuseumData.cs.
#
#   python tools/gen_museum.py
#
# Graybox-Stufe: flache Raumfarben, Wandmasse mit hellem Frontband an Nordwaenden,
# Hindernisse als Flaechen. Das ist die SPIELBARKEITS-Fassung; die Gestaltung im
# Among-Us-Stil ersetzt nur render_floor(), Kollider und Daten bleiben.

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from shapely.geometry import Polygon, Point, box
from shapely.affinity import translate
from shapely.ops import unary_union

import museum_layout as L
import museum_art as A
import museum_consoles as MC

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
# ATLAS_OUT_DIR lenkt ALLE Ausgaben um (Assets + erzeugte C#-Daten), damit parallel an Grafik
# und Layout gearbeitet werden kann, ohne sich die echten assets/ zu ueberschreiben.
import os
_OUT = Path(os.environ["ATLAS_OUT_DIR"]) if os.environ.get("ATLAS_OUT_DIR") else None
ASSETS = _OUT if _OUT else PROJECT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
OUT_FLOOR = ASSETS / "museum_floor.jpg"      # nur Vorschau (volle Karte)
OUT_MINIMAP = ASSETS / "museum_minimap.png"
OUT_CS = (ASSETS / "AtlasMuseumData.cs") if _OUT else PROJECT / "src" / "AtlasMuseumData.cs"

FLOOR_PX_PER_M = 160
FLOOR_SOFTEN_PX = 0.7
PROP_SOFTEN_PX = 0.45
PROP_PX_PER_M = 160
FLOOR_TILES = (5, 4)   # Spalten x Zeilen; jede Kachel < 8192 und durch 4 teilbar (DXT)
MAP_PX_PER_M = 24

BX0, BY0, BX1, BY1 = L.BOUNDS
WALL_COLOR = "#262b33"
WALL_FRONT = "#3c4350"
OUTLINE = "#0d0f12"


def px(x, y, s):
    return ((x - BX0) * s, (BY1 - y) * s)


def poly_px(points, s):
    return [px(x, y, s) for x, y in points]


def walkable_geometry():
    parts = []
    for key, _name, _sys, poly, _col in L.ROOMS:
        if key == "hof":
            continue
        parts.append(Polygon(poly))
    parts += [Polygon(p) for p, _c in L.HOF_FLOORS]
    parts += [Polygon(p) for _k, p in L.CORRIDORS]
    parts += [Polygon(p) for _k, p in L.OPENINGS]
    return unary_union(parts).buffer(0)


def rings(geom):
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    out = []
    for p in polys:
        out.append(list(p.exterior.coords)[:-1])
        for hole in p.interiors:
            out.append(list(hole.coords)[:-1])
    return out


def render_floor_graybox(walk):
    s = FLOOR_PX_PER_M
    w, h = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGB", (w, h), WALL_COLOR)
    d = ImageDraw.Draw(img, "RGBA")

    for poly, col in L.DECOR:
        d.polygon(poly_px(poly, s), fill=col)

    # Boeden: Gaenge und Oeffnungen zuerst, Raeume darueber
    for _k, poly in L.CORRIDORS:
        d.polygon(poly_px(poly, s), fill=L.CORRIDOR_COLOR)
    for _kind, poly in L.OPENINGS:
        d.polygon(poly_px(poly, s), fill=L.CORRIDOR_COLOR)
    for key, _n, _sys, poly, col in L.ROOMS:
        if key == "hof":
            continue
        d.polygon(poly_px(poly, s), fill=col)
    for poly, col in L.HOF_FLOORS:
        d.polygon(poly_px(poly, s), fill=col)

    # Fliesenraster (1 m), nur innerhalb der Raeume, sehr zart
    grid = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(grid)
    for gx in range(math.ceil(BX0), math.floor(BX1) + 1):
        x = (gx - BX0) * s
        gd.line([(x, 0), (x, h)], fill=38, width=1)
    for gy in range(math.ceil(BY0), math.floor(BY1) + 1):
        y = (BY1 - gy) * s
        gd.line([(0, y), (w, y)], fill=38, width=1)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for key, _n, _sys, poly, _c in L.ROOMS:
        md.polygon(poly_px(poly, s), fill=255)
    from PIL import ImageChops
    grid = ImageChops.multiply(grid, mask)
    img.paste((0, 0, 0), (0, 0), grid)

    # Wand-Frontband: ueber jeder Kante, deren begehbare Seite im Sueden liegt,
    # zeigt die Wandmasse 0,45 m "Stirnseite" (Among-Us-Lesart: Nordwaende sieht man).
    for ring in rings(walk):
        n = len(ring)
        for i in range(n):
            (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
            if abs(y0 - y1) > 1e-6 or abs(x1 - x0) < 1e-6:
                continue
            probe = Point((x0 + x1) / 2, y0 - 0.05)
            if not walk.contains(probe):
                continue
            a, b = sorted((x0, x1))
            band = L.rect(a, y0, b, y0 + 0.45)
            d.polygon(poly_px(band, s), fill=WALL_FRONT)

    # Hindernisse
    for shape, col in L.OPAQUE:
        pts = poly_px(L.shape_points(shape), s)
        d.polygon(pts, fill=col, outline=OUTLINE, width=3)
    for shape in L.GLASS:
        pts = poly_px(L.shape_points(shape), s)
        d.polygon(pts, fill=(159, 191, 212, 110), outline=(200, 225, 240, 255), width=2)

    # Umriss der begehbaren Flaeche
    for ring in rings(walk):
        pts = poly_px(ring, s)
        d.line(pts + [pts[0]], fill=OUTLINE, width=6, joint="curve")

    OUT_FLOOR.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_FLOOR, optimize=True)
    print(f"floor  {OUT_FLOOR.name} {w}x{h}")


def render_floor(walk):
    """Boden in Kacheln (Unity-Grenze 8192 px). Rueckgabe: [(index, Welt-x0, Welt-y0, w, h)]."""
    img = A.render_floor(walk, FLOOR_PX_PER_M)
    # Anti-Flimmern: 1- bis 3-Texel-Details (Fugen, Sprenkel) pulsierten beim Laufen, weil die
    # Kamera sie in Bruchteilen von Pixeln verschiebt. Ein halber Pixel Weichzeichnung nimmt die
    # Spitzen, ohne dass das Bild weich wirkt.
    img = img.filter(ImageFilter.GaussianBlur(FLOOR_SOFTEN_PX))
    for old in ASSETS.glob("museum_floor_*.jpg"):
        old.unlink()
    cols, rows = FLOOR_TILES
    tw = (img.width // cols) // 4 * 4
    th = (img.height // rows) // 4 * 4
    tiles = []
    i = 0
    for r in range(rows):
        for c in range(cols):
            x0 = c * tw
            y0 = r * th
            x1 = img.width if c == cols - 1 else x0 + tw
            y1 = img.height if r == rows - 1 else y0 + th
            w = (x1 - x0) // 4 * 4
            h = (y1 - y0) // 4 * 4
            tile = img.crop((x0, y0, x0 + w, y0 + h))
            tile.save(ASSETS / f"museum_floor_{i}.jpg", quality=94, subsampling=0)
            wx = BX0 + x0 / FLOOR_PX_PER_M
            wy = BY1 - (y0 + h) / FLOOR_PX_PER_M
            tiles.append((i, wx, wy, w, h))
            i += 1
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(OUT_FLOOR, quality=90)
    print(f"floor  {img.width}x{img.height} in {len(tiles)} tiles")
    return tiles


def render_props():
    images, meta = [], []
    for i, (kind, shape) in enumerate(A.all_props()):
        im, wx, wy, base = A.draw_prop(kind, shape, i, PROP_PX_PER_M)
        im = im.filter(ImageFilter.GaussianBlur(PROP_SOFTEN_PX))
        if kind in A.CROP_KINDS:
            # auf den Inhalt zuschneiden (2 px Rand fuer die Weichzeichnung), Ecke links unten mitziehen
            l_, t_, r_, b_ = im.getchannel("A").getbbox()
            l_, t_ = max(0, l_ - 2), max(0, t_ - 2)
            r_, b_ = min(im.width, r_ + 2), min(im.height, b_ + 2)
            wx += l_ / PROP_PX_PER_M
            wy += (im.height - b_) / PROP_PX_PER_M
            im = im.crop((l_, t_, r_, b_))
        images.append((i, im))
        fx0, _fy0, fx1, _fy1 = A.shape_bounds(shape)
        meta.append((kind, wx, wy, base, fx0, fx1))
    atlases, placed = A.pack(images)
    for old in ASSETS.glob("museum_props_*.png"):
        old.unlink()
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"museum_props_{k}.png", optimize=True)
    print(f"props  {len(images)} sprites in {len(atlases)} atlas(es) {[a.size for a in atlases]}")
    out = []
    for i, (kind, wx, wy, base, fx0, fx1) in enumerate(meta):
        page, x, y, w, h = placed[i]
        out.append((kind, page, x, atlases[page].height - y - h, w, h, wx, wy, base, fx0, fx1))
    return out


def render_consoles():
    """Eigene Task-Bloecke (museum_consoles.py) in einen Atlas packen."""
    sprites = MC.render_all(PROP_PX_PER_M)
    for old in ASSETS.glob("museum_consoles_*.png"):
        old.unlink()
    if not sprites:
        print("consoles: none (Skeld-Bilder bleiben)")
        return []
    keys = sorted(sprites)
    images = [(i, sprites[k][0].filter(ImageFilter.GaussianBlur(PROP_SOFTEN_PX))) for i, k in enumerate(keys)]
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for k, atlas in enumerate(atlases):
        atlas.save(ASSETS / f"museum_consoles_{k}.png", optimize=True)
    out = []
    for i, key in enumerate(keys):
        page, x, y, w, h = placed[i]
        _im, ax, ay = sprites[key]
        out.append((key, page, x, atlases[page].height - y - h, w, h, ax / w, ay / h))
    print(f"consoles {len(out)} sprites in {len(atlases)} atlas(es)")
    return out


MAP_LABELS = []   # (x, y, halbe Breite, halbe Hoehe) in Weltmetern, fuer AvoidLabels im Builder


def render_minimap(walk):
    MAP_LABELS.clear()
    s = MAP_PX_PER_M
    w, h = int((BX1 - BX0) * s), int((BY1 - BY0) * s)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    polys = [walk] if walk.geom_type == "Polygon" else list(walk.geoms)
    for p in polys:
        d.polygon(poly_px(list(p.exterior.coords), s), fill=(222, 232, 240, 235))
        for hole in p.interiors:
            d.polygon(poly_px(list(hole.coords), s), fill=(0, 0, 0, 0))
    for ring in rings(walk):
        pts = poly_px(ring, s)
        d.line(pts + [pts[0]], fill=(20, 28, 40, 255), width=4, joint="curve")
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    # Teilflaechen eines Raums (gleicher Name, je Skeld-System eine) nur einmal beschriften.
    by_name = {}
    for key, name, _sys, poly, _c in L.ROOMS:
        by_name.setdefault(name, []).append(Polygon(poly))
    for name, polys in by_name.items():
        c = unary_union(polys).centroid
        lx, ly = L.LABEL_AT.get(name, (c.x, c.y))
        x, y = px(lx, ly, s)
        text = L.LABEL_TEXT.get(name, name)   # zu breite Namen zweizeilig (schmaler Raum)
        d.multiline_text((x, y), text, font=font, fill=(20, 28, 40, 255), anchor="mm", align="center", spacing=2)
        l_, t_, r_, b_ = d.multiline_textbbox((0, 0), text, font=font, anchor="mm", align="center", spacing=2)
        MAP_LABELS.append((lx + (l_ + r_) / 2 / s, ly - (t_ + b_) / 2 / s, (r_ - l_) / 2 / s, (b_ - t_) / 2 / s))
    img.save(OUT_MINIMAP, optimize=True)
    print(f"minimap {OUT_MINIMAP.name} {w}x{h}")


def v2(p):
    return f"new({p[0]:.3f}f, {p[1]:.3f}f)"


def chain_cs(points):
    return "new Vector2[] { " + ", ".join(v2(p) for p in points) + " }"


def emit_cs(walk, props=None, tiles=None, consoles=None):
    lines = []
    a = lines.append
    a("// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0")
    a("// Licensed under GPL-3.0-or-later. See LICENSE for details.")
    a("//")
    a("// AUTOMATISCH ERZEUGT von tools/gen_museum.py aus tools/museum_layout.py - NICHT VON HAND")
    a("// AENDERN. Koordinaten = Weltmeter (Museum (0,0) = Welt (0,0), Norden = +y).")
    a("")
    a("using UnityEngine;")
    a("")
    a("namespace UnknownsAtlas;")
    a("")
    a("public static class AtlasMuseumData")
    a("{")
    a(f"    public const float MinX = {BX0:.2f}f, MinY = {BY0:.2f}f, MaxX = {BX1:.2f}f, MaxY = {BY1:.2f}f;")
    a("")
    # Nordwaende (Test 22.09.): an der Wand verschwand der Oberkoerper des Spielers, weil die
    # Schattenkante auf der Wandunterkante lag und die Figur darueber hinausragt. Wie in der Skeld
    # liegt die SCHATTENkante deshalb oben auf der Stirnseite (+NORTH_SHADOW) und die
    # BEWEGUNGSkante etwas davor (-NORTH_STOP). Innenwaende sind 0,5 m dick: +0,45 verbindet nie
    # zwei Raeume.
    NORTH_SHADOW, NORTH_STOP = 0.45, 0.3
    solid = box(BX0 - 5, BY0 - 5, BX1 + 5, BY1 + 5).difference(walk)
    move = walk.difference(translate(solid, 0, -NORTH_STOP)).buffer(0)
    shadow = unary_union([walk, translate(walk, 0, NORTH_SHADOW)]).buffer(0)
    if len(rings(shadow)) != len(rings(walk)):
        print(f"WARN shadow ring count {len(rings(shadow))} != walk {len(rings(walk))} (Raeume verschmolzen?)")
    a("    /// <summary>Bewegungskanten (Ship): begehbare Flaeche, vor Nordwaenden um 0,3 m zurueckgenommen.</summary>")
    a("    public static readonly Vector2[][] Walls =")
    a("    {")
    for ring in rings(move):
        a(f"        {chain_cs(ring)},")
    a("    };")
    a("")
    a("    /// <summary>Schattenkanten (Shadow): begehbare Flaeche plus Stirnseite der Nordwaende.</summary>")
    a("    public static readonly Vector2[][] ShadowWalls =")
    a("    {")
    for ring in rings(shadow):
        a(f"        {chain_cs(ring)},")
    a("    };")
    a("")
    a("    /// <summary>Hindernisse, die Weg UND Sicht sperren (Ship + Shadow).</summary>")
    a("    public static readonly Vector2[][] Opaque =")
    a("    {")
    for shape, _c in L.OPAQUE:
        a(f"        {chain_cs(L.shape_points(shape))},")
    a("    };")
    a("")
    # Blickdichte Hindernisse, die an einer Wand stehen, werfen KEINEN eigenen Schatten: die Wand
    # sperrt die Sicht dort ohnehin, und ihre eigene Schattenkante verdunkelte sonst ihr Sprite
    # (Test 22.09.: Garderobe an der Foyer-Westwand).
    solid = walk.buffer(0).exterior if walk.geom_type == "Polygon" else None
    edges = unary_union([Polygon(r).exterior for r in rings(walk)])
    casts = []
    for shape, _c in L.OPAQUE:
        casts.append(Polygon(L.shape_points(shape)).distance(edges) > 0.08)
    a("    /// <summary>Wirft Hindernis j einen Schatten? (false = steht an einer Wand)</summary>")
    a("    public static readonly bool[] OpaqueCastsShadow = { " + ", ".join("true" if c else "false" for c in casts) + " };")
    a("")
    a("    /// <summary>Hindernisse, die nur den Weg sperren (ShortObjects, kein Schatten).</summary>")
    a("    public static readonly Vector2[][] Glass =")
    a("    {")
    for shape in L.GLASS:
        a(f"        {chain_cs(L.shape_points(shape))},")
    a("    };")
    a("")
    a("    /// <summary>Raeume: Schluessel, Anzeigename, SystemTypes-Traeger, Umriss.</summary>")
    a("    public static readonly (string Key, string Name, SystemTypes Room, Vector2[] Area)[] Rooms =")
    a("    {")
    for key, name, sys, poly, _c in L.ROOMS:
        a(f"        (\"{key}\", \"{name}\", SystemTypes.{sys}, {chain_cs(poly)}),")
    a("    };")
    a("")
    a(f"    public const float PropPixelsPerMeter = {PROP_PX_PER_M}f;")
    a("")
    a("    /// <summary>Objekt-Sprites: Art, Atlas-Rechteck (x, y von UNTEN, w, h), Welt-Ecke links unten,")
    a("    /// Standlinie (z-Sortierung wie Spieler: z = y / 1000).")
    a("    /// FootX0/FootX1 = Grundflaeche ohne Schattenrand (fuer die Durchsicht-Blende).</summary>")
    a("    public static readonly (string Kind, int Atlas, int X, int Y, int W, int H, float WorldX, float WorldY, float BaseY, float FootX0, float FootX1)[] Props =")
    a("    {")
    for kind, page, x, y, w, h, wx, wy, base, fx0, fx1 in (props or []):
        a(f"        (\"{kind}\", {page}, {x}, {y}, {w}, {h}, {wx:.3f}f, {wy:.3f}f, {base:.3f}f, {fx0:.3f}f, {fx1:.3f}f),")
    a("    };")
    a(f"    public const int PropAtlasCount = {1 + max((p[1] for p in (props or [(None, 0)])), default=0)};")
    a("")
    a(f"    public const float FloorPixelsPerMeter = {FLOOR_PX_PER_M}f;")
    a("")
    a("    /// <summary>Bodenkacheln: Ressourcen-Index, Welt-Ecke links unten, Pixelmasse.</summary>")
    a("    public static readonly (int Index, float WorldX, float WorldY, int W, int H)[] FloorTiles =")
    a("    {")
    for i, wx, wy, w, h in (tiles or []):
        a(f"        ({i}, {wx:.4f}f, {wy:.4f}f, {w}, {h}),")
    a("    };")
    a("")
    a("    /// <summary>Eigene Task-Bloecke: Schluessel, Atlas, Rechteck (y von UNTEN), Pivot normiert.</summary>")
    a("    public static readonly (string Key, int Atlas, int X, int Y, int W, int H, float PivotX, float PivotY)[] ConsoleSprites =")
    a("    {")
    for key, page, x, y, w, h, px_, py_ in (consoles or []):
        a(f"        (\"{key}\", {page}, {x}, {y}, {w}, {h}, {px_:.4f}f, {py_:.4f}f),")
    a("    };")
    a("")
    a("    /// <summary>Beschriftungen der Minimap (Weltmeter): Mitte, halbe Breite/Hoehe. Die Sabotage- und")
    a("    /// Tuerknoepfe weichen ihnen aus (AtlasMuseumBuilder.AvoidLabels).</summary>")
    a("    public static readonly (float X, float Y, float HalfW, float HalfH)[] MapLabels =\n    {")
    for lx, ly, hw, hh in MAP_LABELS:
        a(f"        ({lx:.3f}f, {ly:.3f}f, {hw:.3f}f, {hh:.3f}f),")
    a("    };")
    rig = A.REX_RIG
    if rig:
        a("    /// <summary>Gelenke des T. rex in Weltmetern (AtlasRex): Halsgelenk = Drehpunkt des Kopfes,")
        a("    /// Kiefergelenk, Augenhoehle.</summary>")
        a("    public static readonly Vector2 RexNeck = new(%.3ff, %.3ff), RexJaw = new(%.3ff, %.3ff), RexEye = new(%.3ff, %.3ff);"
          % (rig["neck"] + rig["jaw"] + rig["eye"]))
    a("    /// <summary>Gaenge als Hallway-Raeume (nur AllRooms, nicht FastRooms).</summary>")
    a("    public static readonly Vector2[][] Hallways =")
    a("    {")
    for _k, poly in L.CORRIDORS:
        a(f"        {chain_cs(poly)},")
    a("    };")
    a("}")
    OUT_CS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"data   {OUT_CS.name}: {len(rings(walk))} wall ring(s), {len(L.OPAQUE)} opaque, {len(L.GLASS)} glass")


def sanity(walk):
    # Jede Oeffnung muss zwei Boeden verbinden, sonst ist sie eine Sackgasse in die Wand.
    floors = [Polygon(p) for k, _n, _s, p, _c in L.ROOMS if k != "hof"]
    floors += [Polygon(p) for p, _c in L.HOF_FLOORS] + [Polygon(p) for _k, p in L.CORRIDORS]
    for kind, poly in L.OPENINGS:
        o = Polygon(poly)
        touching = sum(1 for f in floors if f.intersection(o.buffer(0.01)).area > 1e-4)
        if touching < 2:
            print(f"WARN opening {kind} {poly[0]} touches {touching} floor(s)")
    if walk.geom_type != "Polygon":
        print(f"WARN walkable area is split into {len(walk.geoms)} parts")
    # Hindernisse duerfen keine Oeffnung blockieren
    for shape, _c in L.OPAQUE:
        o = Polygon(L.shape_points(shape))
        for kind, poly in L.OPENINGS:
            if o.intersects(Polygon(poly).buffer(0.4)):
                print(f"WARN opaque {shape} near opening {poly[0]}")


def main():
    walk = walkable_geometry()
    sanity(walk)
    tiles = render_floor(walk)
    props = render_props()
    consoles = render_consoles()
    render_minimap(walk)
    emit_cs(walk, props, tiles, consoles)


if __name__ == "__main__":
    main()
