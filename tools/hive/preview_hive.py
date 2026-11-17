# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# preview_hive.py - setzt Amberhive aus dem Kartenpaket zusammen (wie im Spiel, ohne Licht): Boden, Objekte nach Standlinie,
# Konsolen-, Tuer-, Vent- und Kamerabilder an ihren Plaetzen, Bruecke ueber dem Honigsee.
#   python preview_hive.py [1|2] [ppm] [x0 y0 x1 y1]  -> _out/preview_<n>f.png

import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PKG = HERE.parent.parent / "assets" / "amberhive"


def main(argv):
    floors = int(argv[1]) if len(argv) > 1 else 2
    ppm = float(argv[2]) if len(argv) > 2 else 50
    d = json.loads((PKG / f"amberhive_{floors}f.json").read_text(encoding="utf-8"))
    bx0, by0, bx1, by1 = (float(v) for v in argv[3:7]) if len(argv) > 6 else (d["minX"], d["minY"], d["maxX"], d["maxY"])
    W, H = int((bx1 - bx0) * ppm), int((by1 - by0) * ppm)
    can = Image.new("RGBA", (W, H), (16, 10, 4, 255))
    P = lambda x, y: (int(round((x - bx0) * ppm)), int(round((by1 - y) * ppm)))
    fppm = d["floorPixelsPerMeter"]
    for t in d["floorTiles"]:
        im = Image.open(PKG / f"amberhive_floor_{t['index']}.jpg").convert("RGBA")
        x, y = P(t["x"], t["y"] + t["h"] / fppm)
        right, bottom = P(t["x"] + t["w"] / fppm, t["y"])
        w, h = right - x, bottom - y
        can.alpha_composite(im.resize((max(1, w), max(1, h)), Image.LANCZOS), (x, y))
    items = []
    atl = {}
    pp = d["propPixelsPerMeter"]
    for p in d["props"]:
        a = atl.setdefault(("p", p["atlas"]), Image.open(PKG / f"amberhive_props_{p['atlas']}.png").convert("RGBA"))
        top = a.height - p["y"] - p["h"]
        sp = a.crop((p["x"], top, p["x"] + p["w"], top + p["h"]))
        items.append((p["baseY"], sp, p["worldX"], p["worldY"]))
    cons = dict(d["consoles"])
    for k in ("emergencyButton", "surveillanceConsole", "adminTable", "freeplayLaptop"):
        cons[{"emergencyButton": "EmergencyButton", "surveillanceConsole": "SurveillanceConsole", "adminTable": "AdminTable",
              "freeplayLaptop": "FreeplayLaptop"}[k]] = d[k]
    for i, v in d["vents"].items():
        cons[f"Vent/{i}"] = v
    for s in d["verticalDoors"] + d["horizontalDoors"]:
        cons[f"Door/{s['label']}"] = [s["x"], s["y"]]
    for i, c in enumerate(d["cameras"]):
        cons[f"Camera/{i}"] = c
    for e in d["consoleSprites"]:
        if e["key"] not in cons:
            continue
        a = atl.setdefault(("c", e["atlas"]), Image.open(PKG / f"amberhive_consoles_{e['atlas']}.png").convert("RGBA"))
        top = a.height - e["y"] - e["h"]
        sp = a.crop((e["x"], top, e["x"] + e["w"], top + e["h"]))
        px, py = cons[e["key"]]
        wx = px - e["pivotX"] * e["w"] / pp
        wy = py - e["pivotY"] * e["h"] / pp
        floor = e["key"].startswith(("Vent/", "MedBay/MedScanner"))
        items.append((py + (50 if floor else 0), sp, wx, wy))
    br = PKG / "task_hive_bridge.png"
    if br.exists():
        b = Image.open(br).convert("RGBA").rotate(90, expand=True)
        items.append((99, b, -b.width / 100 / 2, -b.height / 100 / 2, 100))
    for it in sorted(items, key=lambda r: -r[0] if r[0] < 49 else 1e9 - r[0]):
        base, sp, wx, wy = it[:4]
        src_ppm = it[4] if len(it) > 4 else pp
        w, h = max(1, round(sp.width * ppm / src_ppm)), max(1, round(sp.height * ppm / src_ppm))
        x, y = P(wx, wy + sp.height / src_ppm)
        can.alpha_composite(sp.resize((w, h), Image.LANCZOS), (x, y)) if 0 <= x < W and 0 <= y < H or True else None
    out = HERE / "_out" / f"preview_{floors}f.png"
    can.save(out)
    print(out, can.size)


if __name__ == "__main__":
    main(sys.argv)
