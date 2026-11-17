# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_sheet.py - Uebersichtsbild aller Konsolen-, Tuer-, Vent- und Kamerabilder (normales Python mit Pillow, kein Blender).
# Aufruf:  python consoles_sheet.py [--scale 1.0] [--out <png>] [--only <praefix> ...]
# Dunkelgrauer Grund, je Bild Beschriftung und ein kleines Kreuz am Ankerpixel (aus der JSON).

import argparse
import glob
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, "..", "art", "consoles"))


def load_font(size):
    for f in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def group_of(name):
    if name.startswith("door_"):
        return "Tueren (je 6 Bilder: zu .. offen)", name.rsplit("_", 1)[0]
    if name.startswith("vent_"):
        return "Vent", "vent"
    if name.startswith("camera_"):
        return "Kameras", "camera"
    return "Konsolen", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--out", default=os.path.join(ART, "_sheet.png"))
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--cols", type=int, default=8)
    a = ap.parse_args()
    files = sorted(f for f in glob.glob(os.path.join(ART, "*.png")) if not os.path.basename(f).startswith("_"))
    if a.only:
        files = [f for f in files if any(os.path.basename(f).startswith(p) for p in a.only)]
    font, big = load_font(14), load_font(22)
    sc = a.scale
    sections = {}
    order = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        sec, row = group_of(name)
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        sections[sec].append((name, f, row))
    pad, label_h, W = 14, 20, 0
    blocks = []   # (section, rows[[items]])
    for sec in sorted(order, key=lambda s: ["Konsolen", "Tueren (je 6 Bilder: zu .. offen)", "Vent", "Kameras"].index(s)):
        items = sections[sec]
        rows = []
        if sec == "Konsolen":
            for i in range(0, len(items), a.cols):
                rows.append(items[i:i + a.cols])
        else:
            cur, key = [], None
            for it in items:
                if it[2] != key and cur:
                    rows.append(cur)
                    cur = []
                key = it[2]
                cur.append(it)
            if cur:
                rows.append(cur)
        blocks.append((sec, rows))
    # Masse
    layout, y = [], pad
    for sec, rows in blocks:
        layout.append(("title", sec, pad, y))
        y += 32
        for row in rows:
            x, rh = pad, 0
            for name, f, _ in row:
                im = Image.open(f)
                w, h = int(im.width * sc), int(im.height * sc)
                cw = max(w, 120)
                layout.append(("img", (name, f, w, h), x, y))
                x += cw + pad
                rh = max(rh, h)
            W = max(W, x)
            y += rh + label_h + pad
        y += 10
    sheet = Image.new("RGBA", (W + pad, y + pad), (52, 52, 56, 255))
    d = ImageDraw.Draw(sheet)
    for kind, data, x, y0 in layout:
        if kind == "title":
            d.text((x, y0), data, fill=(255, 214, 120, 255), font=big)
            continue
        name, f, w, h = data
        im = Image.open(f).convert("RGBA")
        if (w, h) != im.size:
            im = im.resize((w, h), Image.LANCZOS)
        d.rectangle([x - 1, y0 - 1, x + w, y0 + h], outline=(80, 80, 86, 255))
        sheet.alpha_composite(im, (x, y0))
        meta = os.path.splitext(f)[0] + ".json"
        if os.path.exists(meta):
            m = json.load(open(meta, encoding="utf-8"))
            ax, ay = x + m["ox"] * sc, y0 + m["oy"] * sc
            d.line([ax - 5, ay, ax + 5, ay], fill=(0, 230, 255, 255), width=1)
            d.line([ax, ay - 5, ax, ay + 5], fill=(0, 230, 255, 255), width=1)
        d.text((x, y0 + h + 3), name.replace("door_", ""), fill=(235, 235, 235, 255), font=font)
    sheet.save(a.out)
    print("sheet", a.out, sheet.size)


main()
