# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_sheet.py - Uebersichtsbild aller Amberhive-Einrichtungsobjekte (art/props/_sheet.png) zum Pruefen.
# Laeuft mit normalem Python + Pillow (nicht in Blender):  python props_sheet.py [massstab]
# Je Art: Bild auf dunkelgrauem Grund, Name darunter, Grundflaeche als feiner tuerkiser Rahmen, Anker als roter Punkt.
# Animierte Arten zeigen alle Frames nebeneinander.

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, "..", "art", "props"))
SPECS = json.load(open(os.path.join(HERE, "..", "art_props.json"), encoding="utf-8"))
SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
BG, CELL_BG, FG = (52, 52, 58), (64, 64, 72), (235, 225, 200)
SHEET_W = 2400


def font(sz):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def tile(spec):
    kind, n = spec["kind"], int(spec.get("frames", 1))
    names = [kind] if n == 1 else [f"{kind}_f{i}" for i in range(n)]
    frames = []
    for nm in names:
        p = os.path.join(ART, nm + ".png")
        if not os.path.exists(p):
            return None
        im = Image.open(p).convert("RGBA")
        meta = json.load(open(os.path.join(ART, nm + ".json"), encoding="utf-8"))
        bg = Image.new("RGBA", im.size, CELL_BG + (255,))
        d = ImageDraw.Draw(bg)
        ppm = meta["ppm"]
        fx0 = meta["ox"] - spec["foot_w"] / 2 * ppm
        fx1 = meta["ox"] + spec["foot_w"] / 2 * ppm
        fy1 = meta["oy"]
        fy0 = meta["oy"] - spec["foot_d"] * ppm
        d.rectangle([fx0, fy0, fx1, fy1], outline=(70, 200, 210, 255), width=2)
        bg.alpha_composite(im)
        d = ImageDraw.Draw(bg)
        d.ellipse([meta["ox"] - 4, meta["oy"] - 4, meta["ox"] + 4, meta["oy"] + 4], fill=(230, 60, 60, 255))
        w, h = max(1, int(bg.width * SCALE)), max(1, int(bg.height * SCALE))
        frames.append(bg.resize((w, h), Image.LANCZOS))
    gap = 6
    W = sum(f.width for f in frames) + gap * (len(frames) - 1)
    H = max(f.height for f in frames)
    f_lab = font(18)
    t = Image.new("RGBA", (max(W, 150), H + 30), BG + (255,))
    x = 0
    for fr in frames:
        t.alpha_composite(fr, (x, H - fr.height))
        x += fr.width + gap
    lab = kind + (f"  ({n} Bilder)" if n > 1 else "")
    ImageDraw.Draw(t).text((2, H + 5), lab, fill=FG, font=f_lab)
    return t


def main():
    tiles = [t for t in (tile(s) for s in SPECS) if t is not None]
    pad = 24
    rows, row, rw = [], [], pad
    for t in tiles:
        if row and rw + t.width + pad > SHEET_W:
            rows.append(row)
            row, rw = [], pad
        row.append(t)
        rw += t.width + pad
    if row:
        rows.append(row)
    H = pad + sum(max(t.height for t in r) + pad for r in rows) + 40
    sheet = Image.new("RGBA", (SHEET_W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), f"Amberhive Einrichtung: {len(tiles)} Arten (Massstab {SCALE:g}, Rahmen = Grundflaeche, Punkt = Anker)",
           fill=FG, font=font(22))
    y = pad + 30
    for r in rows:
        rh = max(t.height for t in r)
        x = pad
        for t in r:
            sheet.alpha_composite(t, (x, y + rh - t.height))
            x += t.width + pad
        y += rh + pad
    out = os.path.join(ART, "_sheet.png")
    sheet.convert("RGB").save(out)
    print(out, sheet.size, len(tiles))


if __name__ == "__main__":
    main()
