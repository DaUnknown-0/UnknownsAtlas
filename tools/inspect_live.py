# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# inspect_live.py - Abgleich gegen die LAUFZEIT-Wahrheit aus dem Spiel.
#
# Quelle: der NightfallSurveyTool-Export einer Museumsrunde (<AU>\Nightfall\museum.json +
# museum_atlas.png/.txt). Das Plugin schreibt unter dem Schluessel "museum", sobald Atlas den
# AppDomain-Eintrag "UnknownsAtlas.ActiveMap" setzt; die echten skeldship.*-Dateien bleiben unberuehrt.
#
# Hintergrund = das Spielfoto (MapCapture), darueber die exportierten Kollider nach Layer und die
# tatsaechlichen Positionen von Konsolen, Vents und Tueren. Dazu ein Textbericht mit allem, was vom
# Soll (src/AtlasMuseumLayout.cs, tools/museum_layout.py) abweicht.
#
#   python tools/inspect_live.py <raum>|all|x0 y0 x1 y1 [--ppm 120]
#   Ausgabe: tools/_inspect/live_<raum>.png, tools/_inspect/live_report.txt
#
#   rot = Ship (9, Bewegung)    dunkelrot = Shadow (10, Sicht)    orange = Objects (11)
#   cyan = ShortObjects (12, fest)    gelb = Konsole (Ist)   lila = Vent (Ist)   magenta = Tuer (Ist)

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import inspect_museum as I

LIVE_DIR = I.SURVEY_DIR
KEY = __import__("os").environ.get("ATLAS_LIVE_KEY", "museum")


def load():
    js = LIVE_DIR / f"{KEY}.json"
    if not js.exists():
        raise SystemExit(f"kein Export gefunden: {js} (Museumsrunde mit NightfallSurveyTool laufen lassen)")
    data = json.loads(js.read_text(encoding="utf-8"))
    photo = None
    meta = LIVE_DIR / f"{KEY}_atlas.txt"
    if meta.exists():
        w, h, x0, y0, x1, y1 = meta.read_text().split()
        photo = (Image.open(LIVE_DIR / f"{KEY}_atlas.png").convert("RGBA"), float(x0), float(y0), float(x1), float(y1))
    return data, photo


def background(photo, x0, y0, x1, y1, ppm):
    w, h = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    if photo is None:
        return Image.new("RGBA", (w, h), (16, 19, 25, 255))
    img, px0, py0, px1, py1 = photo
    sx = img.width / (px1 - px0)
    sy = img.height / (py1 - py0)
    crop = img.crop((int((x0 - px0) * sx), int((py1 - y1) * sy), int((x1 - px0) * sx), int((py1 - y0) * sy)))
    return crop.resize((w, h), Image.LANCZOS)


LAYER_COL = {9: (255, 40, 40, 230), 10: (150, 0, 0, 200), 11: (255, 150, 0, 230), 12: (0, 230, 255, 230)}


def render(data, photo, x0, y0, x1, y1, ppm, title):
    img = background(photo, x0, y0, x1, y1, ppm)
    d = ImageDraw.Draw(img, "RGBA")
    f = I.font(ppm * 0.16)

    def P(x, y):
        return ((x - x0) * ppm, (y1 - y) * ppm)

    for c in data.get("colliders", []):
        if not c.get("enabled", True) or c.get("trigger"):
            continue
        col = LAYER_COL.get(c.get("layer"))
        if col is None:
            continue
        b = c.get("bounds", [0, 0, 0, 0])
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        for path in c.get("paths", []):
            pts = [P(path[i], path[i + 1]) for i in range(0, len(path) - 1, 2)]
            if c.get("closed") and len(pts) > 2:
                pts = pts + [pts[0]]
            if len(pts) > 1:
                d.line(pts, fill=col, width=max(2, ppm // 45) if c.get("layer") != 10 else 1)

    def mark(pos, label, col):
        px, py = P(pos[0], pos[1])
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=col, outline=(0, 0, 0, 255))
        tw = d.textlength(label, font=f)
        d.rectangle([px + 7, py - ppm * 0.1, px + 11 + tw, py + ppm * 0.1], fill=(0, 0, 0, 170))
        d.text((px + 9, py - ppm * 0.09), label, font=f, fill=col)

    for c in data.get("consoles", []):
        mark(c["position"], f'{c["room"]}/{c["name"]}/{c["consoleId"]}', (255, 230, 60, 255))
    for v in data.get("vents", []):
        mark(v["position"], f'Vent {v["id"]} L{v.get("left")} R{v.get("right")}', (190, 120, 255, 255))
    for dr in data.get("doors", []):
        mark(dr["position"], f'Tuer {dr["name"]} [{dr["room"]}]', (255, 60, 255, 255))
    if title:
        d.rectangle([0, img.height - ppm * 0.35, d.textlength(title, font=f) + 20, img.height], fill=(0, 0, 0, 190))
        d.text((10, img.height - ppm * 0.32), title, font=f, fill=(255, 255, 255, 255))
    return img


def report(data):
    consoles, named, vents, nets, doors, cams = I.parse_layout()
    lines = []
    live = {f'{c["room"]}/{c["name"]}/{c["consoleId"]}': c["position"] for c in data.get("consoles", [])}
    for key, pos in consoles.items():
        if key not in live:
            lines.append(f"FEHLT   Konsole {key} (Soll {pos}) nicht im Export")
            continue
        lp = live[key]
        dist = math.hypot(lp[0] - pos[0], lp[1] - pos[1])
        if dist > 0.05:
            lines.append(f"VERSATZ Konsole {key}: Soll {pos} Ist ({lp[0]:.2f},{lp[1]:.2f}) d={dist:.2f}")
    for key in live:
        if key not in consoles and "Vent" not in key:
            lines.append(f"EXTRA   Konsole {key} im Export, aber ohne Museumsplatz: {live[key]}")
    lv = {v["id"]: v for v in data.get("vents", [])}
    for vid, pos in vents.items():
        v = lv.get(vid)
        if v is None:
            lines.append(f"FEHLT   Vent {vid}")
            continue
        dist = math.hypot(v["position"][0] - pos[0], v["position"][1] - pos[1])
        if dist > 0.05:
            lines.append(f"VERSATZ Vent {vid}: Soll {pos} Ist {v['position'][:2]} d={dist:.2f}")
    for vid in lv:
        if vid not in vents:
            lines.append(f"EXTRA   Vent {vid} lebt noch ({lv[vid]['position'][:2]})")
    for dr in data.get("doors", []):
        p = dr["position"]
        best = min(doors, key=lambda s: math.hypot(s["cx"] - p[0], s["cy"] - p[1]))
        dist = math.hypot(best["cx"] - p[0], best["cy"] - p[1])
        lines.append(f"{'OK     ' if dist < 0.3 else 'VERSATZ'} Tuer {dr['name']} [{dr['room']}] Ist ({p[0]:.2f},{p[1]:.2f}) -> Slot {best['label']} d={dist:.2f}")
    left = [c["path"] for c in data.get("colliders", [])
            if c.get("path", "").startswith("SkeldShip(Clone)/") and "/Atlas_" not in c.get("path", "")
            and c.get("layer") in (9, 10, 11) and not c.get("trigger")]
    for p in left:
        lines.append(f"REST    Skeld-Kollider nach dem Umbau: {p}")
    return lines


def main(argv):
    ppm = 120
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--ppm":
            ppm = int(argv[i + 1]); i += 1
        else:
            args.append(argv[i])
        i += 1
    data, photo = load()
    I.OUT_DIR.mkdir(exist_ok=True)
    rep = report(data)
    (I.OUT_DIR / "live_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"Bericht: {len(rep)} Zeilen -> {I.OUT_DIR / 'live_report.txt'}")
    boxes = I.room_boxes()
    if args == ["all"]:
        jobs = list(boxes.items())
    elif len(args) == 1 and args[0] in boxes:
        jobs = [(args[0], boxes[args[0]])]
    elif len(args) == 4:
        jobs = [("rect", tuple(map(float, args)))]
    else:
        jobs = []
    for name, (x0, y0, x1, y1) in jobs:
        img = render(data, photo, x0, y0, x1, y1, ppm, f"LIVE {name}")
        out = I.OUT_DIR / f"live_{name}.png"
        img.convert("RGB").save(out)
        print(out, img.size)


if __name__ == "__main__":
    main(sys.argv[1:])
