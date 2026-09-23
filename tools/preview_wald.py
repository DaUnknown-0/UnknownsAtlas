# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# preview_wald.py - Ausschnitt der Waldkarte wie im Spiel: Bodenkacheln + Objekte + Task-Bloecke
# (tools/wald_consoles.py) nach Standlinie sortiert. Vorher einmal tools/gen_wald.py laufen lassen.
#   python tools/preview_wald.py <raum>|all|x0 y0 x1 y1   -> tools/_wald/view_<name>.png (160 px/m)

import sys
from pathlib import Path
from PIL import Image
import gen_wald as GW
import wald_geo as G
import wald_layout as W

OUT = Path(__file__).resolve().parent / "_wald"
PPM = GW.FLOOR_PPM
BX0, BY0, BX1, BY1 = W.BOUNDS


def floor(x0, y0, x1, y1):
    cols, _ = GW.FLOOR_TILES
    tiles = sorted(GW.ASSETS.glob("wald_floor_*.jpg"), key=lambda p: int(p.stem.split("_")[-1]))
    tw, th = Image.open(tiles[0]).size
    px0, py0, px1, py1 = int((x0 - BX0) * PPM), int((BY1 - y1) * PPM), int((x1 - BX0) * PPM), int((BY1 - y0) * PPM)
    out = Image.new("RGBA", (px1 - px0, py1 - py0))
    for i, t in enumerate(tiles):
        tx, ty = (i % cols) * tw, (i // cols) * th
        im = Image.open(t)
        a0, b0, a1, b1 = max(px0, tx), max(py0, ty), min(px1, tx + im.width), min(py1, ty + im.height)
        if a1 > a0 and b1 > b0:
            out.paste(im.crop((a0 - tx, b0 - ty, a1 - tx, b1 - ty)).convert("RGBA"), (a0 - px0, b0 - py0))
    return out


def render(x0, y0, x1, y1):
    img = floor(x0, y0, x1, y1)
    sprites = []
    items = list(W.OPAQUE) + list(W.GLASS)
    for i, (s, kind) in enumerate(items):
        im, wx, wy, base = GW.draw_prop(kind, s, i, PPM)
        sprites.append((base, im, wx, wy))
    try:
        import re
        import wald_consoles as WC
        own = WC.render_all(PPM)
        src = (GW.PROJECT / "src" / "AtlasWaldLayout.cs").read_text(encoding="utf-8")
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r'\["([^"]+)"\] = new\((-?[\d.]+)f, (-?[\d.]+)f\)', src)}
        for n in ("EmergencyButton", "SurveillanceConsole", "AdminTable", "FreeplayLaptop"):
            m = re.search(n + r' = new\((-?[\d.]+)f, (-?[\d.]+)f\)', src)
            pos[n] = (float(m.group(1)), float(m.group(2)))
        for k, (im, ax, ay) in own.items():
            if k in pos:
                wx, wy = pos[k]
                sprites.append((wy, im, wx - ax / PPM, wy - ay / PPM))
    except ImportError:
        pass
    sprites.sort(key=lambda t: -t[0])
    for _b, im, wx, wy in sprites:
        img.alpha_composite(im, (int(round((wx - x0) * PPM)), int(round((y1 - wy) * PPM)) - im.height)) if (wx - x0) * PPM > -im.width else None
    return img


def overlay(img, x0, y0, x1, y1):
    """Diagnose-Ebene aus den ERZEUGTEN C#-Daten (das, was der Builder baut):
    rot = Bewegungskante, dunkelrot = Schattenkante, orange = blickdicht, cyan = Glas,
    magenta = Tuer-Slot, gelb = Konsole + 1-m-Nutzradius, lila = Vent, weiss = Kamera."""
    import re
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img, "RGBA")
    P = lambda x, y: ((x - x0) * PPM, (y1 - y) * PPM)
    data = (GW.PROJECT / "src" / "AtlasWaldData.cs").read_text(encoding="utf-8")
    lay = (GW.PROJECT / "src" / "AtlasWaldLayout.cs").read_text(encoding="utf-8")
    try:
        f = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        f = ImageFont.load_default()

    def block(name):
        i = data.index(name + " =")
        j = data.index("};", i)
        return data[i:j]

    def chains(txt):
        out = []
        for m in re.finditer(r"new Vector2\[\] \{([^}]*)\}", txt):
            pts = [(float(a), float(b)) for a, b in re.findall(r"new\((-?[\d.]+)f, (-?[\d.]+)f\)", m.group(1))]
            out.append(pts)
        return out

    for name, col, w in (("ShadowWalls", (140, 0, 0, 220), 2), ("Walls", (255, 40, 40, 255), 3),
                         ("Opaque", (255, 150, 0, 255), 3), ("Glass", (0, 230, 255, 255), 3)):
        for pts in chains(block(name)):
            q = [P(*p) for p in pts]
            d.line(q + [q[0]], fill=col, width=w)
    for m in re.finditer(r'new\("([^"]+)", (-?[\d.]+)f, (-?[\d.]+)f, ([\d.]+)f', lay):
        cx, cy, ln = float(m.group(2)), float(m.group(3)), float(m.group(4))
        vert = m.group(1).endswith(("-E", "-W"))
        hx, hy = (0.25, ln / 2) if vert else (ln / 2, 0.25)
        d.rectangle([P(cx - hx, cy + hy), P(cx + hx, cy - hy)], outline=(255, 60, 255, 255), width=3)
    for m in re.finditer(r'\["([^"]+)"\] = new\((-?[\d.]+)f, (-?[\d.]+)f\)', lay):
        x, y = P(float(m.group(2)), float(m.group(3)))
        d.ellipse([x - PPM, y - PPM, x + PPM, y + PPM], outline=(255, 230, 60, 120), width=2)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 230, 60, 255), outline=(0, 0, 0, 255))
        d.text((x + 8, y - 10), m.group(1).split("/")[1], font=f, fill=(255, 240, 120, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for m in re.finditer(r'\[(\d+)\] = new\((-?[\d.]+)f, (-?[\d.]+)f\)', lay):
        x, y = P(float(m.group(2)), float(m.group(3)))
        d.rectangle([x - 8, y - 5, x + 8, y + 5], fill=(190, 120, 255, 255), outline=(0, 0, 0, 255))
    cams = lay[lay.index("Cameras ="):]
    cams = cams[:cams.index("};")]
    for a, b in re.findall(r"new\((-?[\d.]+)f, (-?[\d.]+)f\)", cams):
        x, y = P(float(a), float(b))
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    for n in ("EmergencyButton", "SurveillanceConsole", "AdminTable", "FreeplayLaptop", "Spawn"):
        m = re.search(n + r" = new\((-?[\d.]+)f, (-?[\d.]+)f\)", lay)
        x, y = P(float(m.group(1)), float(m.group(2)))
        d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 90, 90, 255), width=3)
        d.text((x + 8, y + 4), n, font=f, fill=(255, 150, 150, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return img


def main(argv):
    ov = "--overlay" in argv
    argv = [a for a in argv if a != "--overlay"]
    walk, *_ = G.build()
    rooms = G.rooms(walk)
    jobs = []
    if argv == ["all"]:
        for k, (_n, _s, g) in rooms.items():
            a, b, c, d = g.bounds
            jobs.append((k, (a - 1.5, b - 1.5, c + 1.5, d + 2.5)))
    elif len(argv) == 1:
        a, b, c, d = rooms[argv[0]][2].bounds
        jobs.append((argv[0], (a - 1.5, b - 1.5, c + 1.5, d + 2.5)))
    else:
        jobs.append(("rect", tuple(map(float, argv))))
    for name, (x0, y0, x1, y1) in jobs:
        x0, y0, x1, y1 = max(x0, BX0), max(y0, BY0), min(x1, BX1), min(y1, BY1)
        im = render(x0, y0, x1, y1)
        if ov:
            im = overlay(im, x0, y0, x1, y1)
        im.convert("RGB").save(OUT / f"{'dbg' if ov else 'view'}_{name}.png")
        print(OUT / f"view_{name}.png", im.size)


if __name__ == "__main__":
    main(sys.argv[1:])
