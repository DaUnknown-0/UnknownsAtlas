# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# art_pack.py - bindet die Blender-Bilder aus art/props und art/consoles in das Kartenpaket ein (von gen_hive.py gerufen).
#   props(V, out)    -> Liste fuer map.json "props" + Objekt-Atlanten amberhive_props_<k>.png
#                       + Animationsbilder task_hive_anim_<art>_<k>.png (AmberhiveWorld tauscht sie zur Laufzeit)
#   consoles(..)     -> Liste fuer "consoleSprites" + amberhive_consoles_<k>.png (Konsolen, Tueren, Vents, Kameras)
# Jedes Bild hat eine JSON daneben (blender/hive_style.render_sprite): w, h, ox, oy = Ankerpixel von oben links, ppm.

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import museum_art as A  # noqa: E402  (pack)

ART = HERE / "art"
PROP_PPM = 120


def _load(path):
    meta_p = path.with_suffix(".json")
    if not path.exists() or not meta_p.exists():
        return None
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    im = Image.open(path).convert("RGBA")
    if abs(meta.get("ppm", PROP_PPM) - PROP_PPM) > 0.01:
        raise SystemExit(f"{path.name}: ppm {meta.get('ppm')} != {PROP_PPM}")
    return im, meta


def _shape_anchor(sh):
    """Mitte der Vorderkante (Standlinie) einer Layout-Form."""
    if sh[0] == "rect":
        return (sh[1] + sh[3]) / 2, sh[2], sh[1], sh[3]
    if sh[0] == "circle":
        return sh[1], sh[2] - sh[3], sh[1] - sh[3], sh[1] + sh[3]
    return sh[1], sh[2] - sh[4], sh[1] - sh[3], sh[1] + sh[3]


def props(V, out, key):
    images, meta, missing, anim = [], [], [], set()
    for i, (kind, sh, _mode) in enumerate(V.props):
        r = _load(ART / "props" / f"{kind}.png")
        if r is None:
            missing.append(kind)
            continue
        im, m = r
        cx, base, fx0, fx1 = _shape_anchor(sh)
        wx = cx - m["ox"] / PROP_PPM
        wy = base - (m["h"] - m["oy"]) / PROP_PPM
        images.append((len(images), im))
        meta.append((kind, wx, wy, base, fx0, fx1, i))
        if (ART / "props" / f"{kind}_f1.png").exists():
            anim.add(kind)
    for old in out.glob(f"{key}_props_*.png"):
        old.unlink()
    for old in out.glob("task_hive_anim_*.png"):
        old.unlink()
    if not images:
        print("props: no art yet")
        return [], {}
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for k, atlas in enumerate(atlases):
        atlas.save(out / f"{key}_props_{k}.png", optimize=True)
    res = []
    for i in range(len(images)):
        kind, wx, wy, base, fx0, fx1, src = meta[i]
        page, x, y, ww, hh = placed[i]
        res.append({"kind": kind, "atlas": page, "x": x, "y": atlases[page].height - y - hh, "w": ww, "h": hh,
                    "worldX": round(wx, 4), "worldY": round(wy, 4), "baseY": round(base, 4),
                    "footX0": round(fx0, 4), "footX1": round(fx1, 4), "_src": src})
    res.sort(key=lambda e: e["_src"])
    frames = {}
    for kind in sorted(anim):
        n = 0
        while (ART / "props" / f"{kind}_f{n}.png").exists():
            Image.open(ART / "props" / f"{kind}_f{n}.png").save(out / f"task_hive_anim_{kind}_{n}.png", optimize=True)
            n += 1
        frames[kind] = n
    print(f"props {len(res)} in {len(atlases)} atlas(es), animated {frames}, missing {sorted(set(missing))}")
    return res, frames


def consoles(V, cons, out, key, vents, n_cameras, door_labels):
    spec = json.loads((HERE / "art_consoles.json").read_text(encoding="utf-8"))
    folder = ART / "consoles"
    sprites, missing = {}, []

    def take(name, sprite_key):
        r = _load(folder / f"{name}.png")
        if r is None:
            missing.append(name)
            return False
        im, m = r
        sprites[sprite_key] = (im, m["ox"], m["h"] - m["oy"])
        return True
    for ckey in list(cons) + ["EmergencyButton", "SurveillanceConsole", "AdminTable", "FreeplayLaptop"]:
        motif = spec["consoles"].get(ckey)
        if motif:
            take(motif, ckey)
    for vid in vents:
        if take("vent_0", f"Vent/{vid}"):
            for k in range(1, 6):
                take(f"vent_{k}", f"Vent/{vid}/{k}")
    for label in door_labels:
        if take(f"door_{label}_0", f"Door/{label}"):
            for k in range(1, 6):
                take(f"door_{label}_{k}", f"Door/{label}/{k}")
    for i in range(n_cameras):
        take("camera_off", f"Camera/{i}")
        take("camera_on", f"Camera/{i}/on")
    for old in out.glob(f"{key}_consoles_*.png"):
        old.unlink()
    if not sprites:
        print("consoles: no art yet")
        return []
    by_content = {}
    for k in sorted(sprites):
        im, ax, ay = sprites[k]
        h = (im.size, round(ax, 2), round(ay, 2), hashlib.md5(im.tobytes()).hexdigest())
        by_content.setdefault(h, []).append(k)
    uniq = list(by_content.items())
    images = [(i, sprites[keys[0]][0]) for i, (_h, keys) in enumerate(uniq)]
    atlases, placed = A.pack(images, max_w=2048, max_h=2048)
    for k, atlas in enumerate(atlases):
        atlas.save(out / f"{key}_consoles_{k}.png", optimize=True)
    res = []
    for i, (_h, keys) in enumerate(uniq):
        page, x, y, w, hh = placed[i]
        _im, ax, ay = sprites[keys[0]]
        for k in keys:
            res.append({"key": k, "atlas": page, "x": x, "y": atlases[page].height - y - hh, "w": w, "h": hh,
                        "pivotX": round(ax / w, 4), "pivotY": round(ay / hh, 4)})
    res.sort(key=lambda e: e["key"])
    print(f"console sprites {len(res)} ({len(uniq)} unique) in {len(atlases)} atlas(es), missing {sorted(set(missing))[:12]}")
    return res
