# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# inspect_museum.py - Abnahme-Werkzeug fuer das Vesper-Museum OHNE Spiel.
#
# Rendert einen Raum (oder ein Rechteck) so, wie er im Spiel aussieht - Bodenkacheln, Museums-
# Objekte UND die echten Skeld-Sprites der umgesetzten Konsolen/Vents/Tueren (aus dem
# Nightfall-Survey der AU-Installation) - alles nach Standlinie sortiert wie im Spiel.
# Darueber optional die Diagnose-Ebene:
#   rot       = Wandkollider (Rand der begehbaren Flaeche)
#   orange    = blickdichte Hindernisse (Weg + Sicht)      cyan = Glas (nur Weg)
#   magenta   = Tuer-Slots (Rollgitter) mit Gruppe          gruen gestrichelt = offene Durchgaenge
#   gelb      = Konsolen: Punkt = Transform, Kreis = Nutzradius ~1 m, Beschriftung = Schluessel
#   lila      = Vents mit Netz,   weiss = Kameras,  rot = Notfallknopf/Spawn
#   1-m-Raster mit Koordinaten am Rand (fuer exakte Korrekturen in museum_layout.py /
#   AtlasMuseumLayout.cs).
#
#   python tools/inspect_museum.py foyer            ein Raum (Schluessel aus museum_layout.ROOMS)
#   python tools/inspect_museum.py all              alle Raeume + Gaenge -> tools/_inspect/*.png
#   python tools/inspect_museum.py -9 -14 9 3       Rechteck in Weltmetern
#   Optionen: --clean (ohne Diagnose-Ebene), --ppm 120 (Standard 120 px/m)
#
# Quelle der Kacheln: assets/museum_floor_*.jpg (vorher tools/gen_museum.py laufen lassen).

import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import museum_layout as L
import museum_art as A
import gen_museum as G

HERE = Path(__file__).resolve().parent
OUT_DIR = (G.ASSETS / "_inspect") if G._OUT else HERE / "_inspect"
LAYOUT_CS = G.PROJECT / "src" / "AtlasMuseumLayout.cs"
SURVEY_DIR = Path(r"C:\Users\moritz\Downloads\Among Us - 4.7.0\Among Us - 4.7.0\Nightfall")

BX0, BY0, BX1, BY1 = L.BOUNDS


def font(px):
    try:
        return ImageFont.truetype("arialbd.ttf", max(8, int(px)))
    except OSError:
        return ImageFont.load_default()


# ------------------------------------------------------------------ Layout.cs lesen

def parse_layout():
    src = LAYOUT_CS.read_text(encoding="utf-8")
    consoles = {m.group(1): (float(m.group(2)), float(m.group(3)))
                for m in re.finditer(r'\["([^"]+)"\]\s*=\s*new\((-?[\d.]+)f,\s*(-?[\d.]+)f\)', src)}
    named = {m.group(1): (float(m.group(2)), float(m.group(3)))
             for m in re.finditer(r'public static readonly Vector2 (\w+) = new\((-?[\d.]+)f,\s*(-?[\d.]+)f\)', src)}
    vents = {int(m.group(1)): (float(m.group(2)), float(m.group(3)))
             for m in re.finditer(r'\[(\d+)\]\s*=\s*new\((-?[\d.]+)f,\s*(-?[\d.]+)f\)', src)}
    nets = [list(map(int, re.findall(r"\d+", m.group(1))))
            for m in re.finditer(r"new\[\]\s*\{([\d,\s]+)\}", src)]
    doors = []
    for block, vertical in (("VerticalDoors", True), ("HorizontalDoors", False)):
        b = src[src.index(block + " ="):]
        b = b[:b.index("};")]
        for m in re.finditer(r'new\("([^"]+)",\s*(-?[\d.]+)f,\s*(-?[\d.]+)f,\s*([\d.]+)f,\s*SystemTypes\.(\w+)(,\s*seeThrough:\s*false)?\)', b):
            doors.append(dict(label=m.group(1), cx=float(m.group(2)), cy=float(m.group(3)), length=float(m.group(4)),
                              group=m.group(5), see=m.group(6) is None, vertical=vertical))
    cams_block = src[src.index("Cameras ="):]
    cams_block = cams_block[:cams_block.index("};")]
    cams = [(float(a), float(b)) for a, b in re.findall(r"new\((-?[\d.]+)f,\s*(-?[\d.]+)f\)", cams_block)]
    return consoles, named, vents, nets, doors, cams


# ------------------------------------------------------------------ Skeld-Sprites

class Skeld:
    """Echte Skeld-Sprites aus dem Nightfall-Survey, relativ zur Konsolen-Transform."""

    def __init__(self):
        self.ok = False
        try:
            ship = json.loads((SURVEY_DIR / "skeldship.json").read_text(encoding="utf-8"))
            props = json.loads((SURVEY_DIR / "skeldship_props.json").read_text(encoding="utf-8"))
            self.sheets = [Image.open(SURVEY_DIR / s["file"]).convert("RGBA") for s in props["sheets"]]
        except (OSError, ValueError) as e:
            print(f"[inspect] survey not available ({e}) - consoles drawn as markers only")
            return
        self.pieces = {}
        for p in props["pieces"]:
            self.pieces.setdefault(p["path"], []).append(p)
        self.console_path = {}
        for c in ship["consoles"]:
            key = f'{c["room"]}/{c["name"]}/{c["consoleId"]}'
            self.console_path[key] = (c["path"], c["position"][:2])
        self.vent_path = {}
        for v in ship["vents"]:
            for path in self.pieces:
                if path.endswith("/" + v["name"]):
                    self.vent_path[v["id"]] = (path, v["position"][:2])
        self.ok = True

    def sprites_for(self, path, origin, target):
        """Alle Teile unter path (inkl. Kinder), verschoben von origin (Skeld) nach target (Museum)."""
        out = []
        for p, parts in self.pieces.items():
            if p != path and not p.startswith(path + "/"):
                continue
            for q in parts:
                out.append((q, q["min"][0] - origin[0] + target[0], q["min"][1] - origin[1] + target[1]))
        return out

    def render(self, q, ppm):
        sx, sy, sw, sh = q["rect"]
        img = self.sheets[q["sheet"]].crop((sx, sy, sx + sw, sy + sh))
        w = max(1, int(round((q["max"][0] - q["min"][0]) * ppm)))
        h = max(1, int(round((q["max"][1] - q["min"][1]) * ppm)))
        return img.resize((w, h), Image.LANCZOS)


# ------------------------------------------------------------------ Rendern

def floor_region(x0, y0, x1, y1, ppm):
    """Bodenkacheln (160 px/m) ausschneiden und auf ppm skalieren."""
    fppm = G.FLOOR_PX_PER_M
    cols, _rows = G.FLOOR_TILES
    tiles = sorted(G.ASSETS.glob("museum_floor_*.jpg"), key=lambda p: int(p.stem.split("_")[-1]))
    first = Image.open(tiles[0])
    tw, th = first.size
    px0, py0 = int((x0 - BX0) * fppm), int((BY1 - y1) * fppm)
    px1, py1 = int((x1 - BX0) * fppm), int((BY1 - y0) * fppm)
    out = Image.new("RGBA", (px1 - px0, py1 - py0), A.VOID)
    for i, t in enumerate(tiles):
        tx, ty = (i % cols) * tw, (i // cols) * th
        im = Image.open(t)
        ix0, iy0 = max(px0, tx), max(py0, ty)
        ix1, iy1 = min(px1, tx + im.width), min(py1, ty + im.height)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        out.paste(im.crop((ix0 - tx, iy0 - ty, ix1 - tx, iy1 - ty)).convert("RGBA"), (ix0 - px0, iy0 - py0))
    if ppm != fppm:
        out = out.resize((int((x1 - x0) * ppm), int((y1 - y0) * ppm)), Image.LANCZOS)
    return out


def render(x0, y0, x1, y1, ppm=120, overlay=True, title=""):
    img = floor_region(x0, y0, x1, y1, ppm)

    def P(x, y):
        return ((x - x0) * ppm, (y1 - y) * ppm)

    consoles, named, vents, nets, doors, cams = parse_layout()
    skeld = Skeld()

    # Sprites sammeln: (Standlinie, Bild, Welt-x links, Welt-y unten)
    sprites = []
    for i, (kind, shape) in enumerate(A.all_props()):
        bx0, by0, bx1, by1 = A.shape_bounds(shape)
        if bx1 < x0 - 3 or bx0 > x1 + 3 or by1 < y0 - 6 or by0 > y1 + 1:
            continue
        im, wx, wy, base = A.draw_prop(kind, shape, i, ppm)
        sprites.append((base, im, wx, wy))
    missing = []
    # Eigene Task-Bloecke (museum_consoles.py) ersetzen die Skeld-Bilder, wo vorhanden.
    try:
        import museum_consoles as MC
        own = MC.render_all(ppm)
    except Exception as e:  # noqa: BLE001 - Vorschau soll nie am Konsolen-Code sterben
        print(f"[inspect] museum_consoles failed: {e}")
        own = {}
    allpos = dict(consoles)
    allpos.update({k: v for k, v in named.items() if k in ("EmergencyButton", "SurveillanceConsole", "AdminTable", "FreeplayLaptop")})
    for key, (im, ax, ay) in own.items():
        if key not in allpos:
            continue
        wx, wy = allpos[key]
        sprites.append((wy, im, wx - ax / ppm, wy - ay / ppm))
    if skeld.ok:
        for key, pos in consoles.items():
            if key in own:
                continue
            if key not in skeld.console_path:
                missing.append(key)
                continue
            path, origin = skeld.console_path[key]
            parts = skeld.sprites_for(path, origin, pos)
            if not parts:
                missing.append(key)
            for q, wx, wy in parts:
                sprites.append((pos[1], skeld.render(q, ppm), wx, wy))
        for vid, pos in vents.items():
            if vid in skeld.vent_path:
                path, origin = skeld.vent_path[vid]
                for q, wx, wy in skeld.sprites_for(path, origin, pos):
                    sprites.append((pos[1] + 5, skeld.render(q, ppm), wx, wy))   # Vents liegen am Boden
    sprites.sort(key=lambda t: -t[0])
    for _base, im, wx, wy in sprites:
        px, py = P(wx, wy)
        img.alpha_composite(im, (int(round(px)), int(round(py)) - im.height)) if px > -im.width and py > 0 else None

    if not overlay:
        return img, missing

    d = ImageDraw.Draw(img, "RGBA")
    f_small, f_mid = font(ppm * 0.16), font(ppm * 0.22)

    # Raster
    for gx in range(math.ceil(x0), math.floor(x1) + 1):
        d.line([P(gx, y0), P(gx, y1)], fill=(255, 255, 255, 28 if gx % 5 else 60), width=1)
        d.text((P(gx, y1)[0] + 2, 2), f"{gx}", font=f_small, fill=(255, 255, 255, 200))
    for gy in range(math.ceil(y0), math.floor(y1) + 1):
        d.line([P(x0, gy), P(x1, gy)], fill=(255, 255, 255, 28 if gy % 5 else 60), width=1)
        d.text((2, P(x0, gy)[1] + 2), f"{gy}", font=f_small, fill=(255, 255, 255, 200))

    walk = G.walkable_geometry()
    for ring in G.rings(walk):
        pts = [P(x, y) for x, y in ring]
        d.line(pts + [pts[0]], fill=(255, 40, 40, 230), width=max(2, ppm // 40))
    for shape, _c in L.OPAQUE:
        pts = [P(x, y) for x, y in L.shape_points(shape)]
        d.line(pts + [pts[0]], fill=(255, 150, 0, 240), width=max(2, ppm // 50))
    for shape in L.GLASS:
        pts = [P(x, y) for x, y in L.shape_points(shape)]
        d.line(pts + [pts[0]], fill=(0, 230, 255, 240), width=max(2, ppm // 50))
    for kind, poly in L.OPENINGS:
        if kind == "gap":
            pts = [P(x, y) for x, y in poly]
            for i in range(4):
                a, b = pts[i], pts[(i + 1) % 4]
                d.line([a, b], fill=(80, 255, 120, 160), width=1)
    for door in doors:
        hl = door["length"] / 2
        if door["vertical"]:
            r = (door["cx"] - 0.25, door["cy"] - hl, door["cx"] + 0.25, door["cy"] + hl)
        else:
            r = (door["cx"] - hl, door["cy"] - 0.25, door["cx"] + hl, door["cy"] + 0.25)
        a, b = P(r[0], r[3]), P(r[2], r[1])
        d.rectangle([a, b], outline=(255, 60, 255, 255), width=max(2, ppm // 40))
        d.text((a[0], a[1] - ppm * 0.22), f'{door["label"]} [{door["group"]}]{"" if door["see"] else " blickdicht"}',
               font=f_small, fill=(255, 120, 255, 255))

    def marker(pos, label, col, radius=None):
        px, py = P(*pos)
        if radius:
            r = radius * ppm
            d.ellipse([px - r, py - r, px + r, py + r], outline=col[:3] + (110,), width=1)
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=col, outline=(0, 0, 0, 255))
        tw = d.textlength(label, font=f_small)
        d.rectangle([px + 7, py - ppm * 0.1, px + 11 + tw, py + ppm * 0.1], fill=(0, 0, 0, 170))
        d.text((px + 9, py - ppm * 0.09), label, font=f_small, fill=col)

    for key, pos in consoles.items():
        marker(pos, key + ("  (kein Survey-Sprite)" if key in missing else ""), (255, 230, 60, 255), radius=1.0)
    for name, pos in named.items():
        if name in ("Spawn",):
            continue
        marker(pos, name, (255, 90, 90, 255), radius=1.0)
    net_of = {v: i for i, n in enumerate(nets) for v in n}
    for vid, pos in vents.items():
        marker(pos, f"Vent {vid} (Netz {net_of.get(vid, '?')})", (190, 120, 255, 255))
    for i, pos in enumerate(cams):
        marker(pos, f"Kamera K{i + 1}", (255, 255, 255, 255))
    sp = named.get("Spawn") or (0, -8)
    r = 3.2 * ppm
    c = P(*sp)
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(255, 90, 90, 160), width=2)

    if title:
        d.rectangle([0, img.height - ppm * 0.4, d.textlength(title, font=f_mid) + 20, img.height], fill=(0, 0, 0, 190))
        d.text((10, img.height - ppm * 0.36), title, font=f_mid, fill=(255, 255, 255, 255))
    return img, missing


def room_boxes():
    boxes = {}
    for key, _name, _sys, poly, _c in L.ROOMS:
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        boxes[key] = (min(xs) - 1.2, min(ys) - 1.2, max(xs) + 1.2, max(ys) + 2.2)
    boxes["gaenge_sued"] = (-23, -21, 22, -15)
    boxes["gaenge_nord"] = (-16, 8, 16, 19)
    return boxes


def main(argv):
    ppm = 120
    overlay = True
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--clean":
            overlay = False
        elif argv[i] == "--ppm":
            ppm = int(argv[i + 1]); i += 1
        else:
            args.append(argv[i])
        i += 1
    OUT_DIR.mkdir(exist_ok=True)
    boxes = room_boxes()
    jobs = []
    if args == ["all"]:
        jobs = list(boxes.items())
    elif len(args) == 1 and args[0] in boxes:
        jobs = [(args[0], boxes[args[0]])]
    elif len(args) == 4:
        jobs = [("rect", tuple(map(float, args)))]
    else:
        print("Raeume:", ", ".join(boxes))
        return
    for name, (x0, y0, x1, y1) in jobs:
        x0, y0 = max(x0, BX0), max(y0, BY0)
        x1, y1 = min(x1, BX1), min(y1, BY1)
        img, missing = render(x0, y0, x1, y1, ppm, overlay, title=f"{name}  [{x0:.1f},{y0:.1f}]-[{x1:.1f},{y1:.1f}]")
        out = OUT_DIR / f"{name}{'' if overlay else '_clean'}.png"
        img.convert("RGB").save(out)
        print(out, img.size, ("fehlende Survey-Sprites: " + ", ".join(missing)) if missing and name == jobs[0][0] else "")


if __name__ == "__main__":
    main(sys.argv[1:])
