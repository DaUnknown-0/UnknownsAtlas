# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# hive_gpt.py - GPT-Fassung der Amberhive-Grafik (Vergleich mit den Blender-Fassungen, User 15.11.).
#   python hive_gpt.py refs            Vorlagenblaetter aus art/props und art/consoles (aktueller Stand) auf Magenta
#                                      -> _gpt/ref_NN.png + prompt_NN.txt + cells.json
#   python hive_gpt.py apply <ziel>    _gpt/gpt_NN.png schneiden und in Kopien der Sprites einpassen -> <ziel>/props, <ziel>/consoles
#                                      (gleiche Dateinamen, Groessen und JSON-Anker wie die Vorlage, der alte weiche Schatten bleibt)
# Blaetter: statische Objekte 4x3 (hohe 4x1), jede Animation (Objekt, Tuer H/V, Vent) ein eigenes Blatt mit ihren Bildern,
# damit GPT Stil und Massstab innerhalb der Folge haelt. Tueren: je Richtung ein Blatt, eingepasst in alle Tueren der Richtung.

import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"D:\KI\sdcpp\villa_qwen")
import angel_costume as A  # noqa: E402  (cut_cells)
import gpt_cut as G  # noqa: E402  (_trim, place_fill)
import map_gpt as M  # noqa: E402  (despill, place_foot)

ART = os.path.join(HERE, "art")
OUT = os.path.join(HERE, "_gpt")
SW, SH = 1536, 1024
THEME = ("a cosy beekeeping research station grown inside a giant living beehive (amber light, wax walls, honey, "
         "wood and brass, bees as big as a head)")
STYLE = ("Style: thick dark outlines, rich flat colours with soft cel shading (one darker and one lighter step), warm amber "
         "and honey tones with painted wood, brass and wax, friendly Among Us look.")
BG = ("Background: one solid flat magenta colour #FF00FF everywhere, no gradient, no floor, no cast shadows. Strictly no text, "
      "letters or numbers.")


def specs():
    props = {e["kind"]: e for e in json.load(open(os.path.join(HERE, "art_props.json"), encoding="utf-8"))}
    cons = json.load(open(os.path.join(HERE, "art_consoles.json"), encoding="utf-8"))
    return props, cons


def solid(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).copy()
    a[..., 3] = np.where(a[..., 3] < 110, 0, a[..., 3])
    out = Image.fromarray(a)
    bb = out.getbbox()
    return out.crop(bb) if bb else None


def jobs():
    """Liste der Blaetter: dict(kind, grid, cells=[dict(src=[dateien die diese Zelle fuellt], name, desc)])"""
    props, cons = specs()
    statics, talls, pages = [], [], []
    for k, e in props.items():
        if e["frames"] > 1:
            files = [os.path.join("props", f"{k}_f{i}.png") for i in range(e["frames"])]
            n = e["frames"]
            grid = [3, 2] if n == 6 else [n, 1]
            pages.append(dict(kind="anim", grid=grid, title=k, cells=[
                dict(src=[f], name=k, desc=f"frame {i + 1} of {n} of the looping animation of {e['desc']}") for i, f in enumerate(files)]))
            continue
        c = dict(src=[os.path.join("props", f"{k}.png")], name=k, desc=e["desc"])
        im = solid(os.path.join(ART, c["src"][0]))
        (talls if im.height / im.width >= 1.7 else statics).append(c)
    motifs = cons["motifs"]
    for m, d in motifs.items():
        statics.append(dict(src=[os.path.join("consoles", f"{m}.png")], name=m, desc=f"a task console: {d}"))
    statics.append(dict(src=[os.path.join("consoles", "camera_off.png")], name="camera_off", desc="a small security camera on a post, switched off"))
    statics.append(dict(src=[os.path.join("consoles", "camera_on.png")], name="camera_on", desc="the same camera as the previous cell, switched on (red lamp lit)"))
    for i in range(0, len(statics), 12):
        chunk = statics[i:i + 12]
        pages.append(dict(kind="static", grid=[4, 3] if len(chunk) > 4 else [4, 1], cells=chunk))
    for i in range(0, len(talls), 5):
        pages.append(dict(kind="static", grid=[max(4, len(talls[i:i + 5])), 1], cells=talls[i:i + 5]))
    # Tueren: Vorlage = laengste Tuer je Richtung, eingepasst in alle Tueren dieser Richtung
    for axis, tag in (("y", "H"), ("x", "V")):
        ds = [d for d in cons["doors"] if d["axis"] == axis]
        ref = max(ds, key=lambda d: d["length"])
        cells = []
        for f in range(6):
            cells.append(dict(src=[os.path.join("consoles", f"door_{d['label']}_{f}.png") for d in ds], tpl=os.path.join("consoles", f"door_{ref['label']}_{f}.png"),
                              name=f"door_{tag}", desc=f"frame {f + 1} of 6 of a honeycomb door (bulkhead) opening: frame 1 fully closed, frame 6 fully open"))
        pages.append(dict(kind="door", grid=[3, 2] if axis == "y" else [6, 1], title=f"door {tag}", cells=cells))
    pages.append(dict(kind="anim", grid=[3, 2], title="vent", cells=[
        dict(src=[os.path.join("consoles", f"vent_{f}.png")], name="vent", desc=f"frame {f + 1} of 6 of a floor vent (honeycomb grate) opening: 1 closed, 6 open")
        for f in range(6)]))
    return pages


def refs():
    os.makedirs(OUT, exist_ok=True)
    pages = jobs()
    for n, pg in enumerate(pages, 1):
        cols, rows = pg["grid"]
        cw, ch = SW / cols, SH / rows
        img = Image.new("RGBA", (SW, SH), (255, 0, 255, 255))
        ims = [solid(os.path.join(ART, c.get("tpl", c["src"][0]))) for c in pg["cells"]]
        # Animationsblaetter: ein gemeinsamer Massstab fuer alle Bilder der Folge
        common = min(min(cw * 0.84 / im.width, ch * 0.84 / im.height) for im in ims) if pg["kind"] != "static" else None
        for k, im in enumerate(ims):
            s = common or min(cw * 0.84 / im.width, ch * 0.84 / im.height)
            r = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            x0 = (k % cols) * cw + (cw - r.width) / 2
            y0 = (k // cols) * ch + (ch - r.height) / 2
            img.alpha_composite(r, (round(x0), round(y0)))
        img.convert("RGB").save(os.path.join(OUT, f"ref_{n:02d}.png"))
        grid = f"{cols} columns x {rows} row{'s' if rows > 1 else ''}"
        lines = " ".join(f"{k + 1}. {c['desc']}" for k, c in enumerate(pg["cells"]))
        if pg["kind"] != "static":
            d0 = pg["cells"][0]["desc"].split(" of the looping animation of ")[-1].split(" opening: ")[0]
            lines = (f"frames 1 to {len(pg['cells'])} of the animation of {d0}, in reading order, frame 1 = first, "
                     f"the last frame leads smoothly back to frame 1. The object (German description): {d0}.")
        if pg["kind"] == "static":
            head = (f"Create an image. I uploaded a sprite sheet ({grid}, flat magenta background) with game objects from {THEME}, for a "
                    f"top-down Among Us style game (seen from the front and slightly above). Redraw this sheet as a new image of "
                    f"the same size with a fresh, richer design. Keep for every object: the same position in its cell, the same "
                    f"overall size and footprint, the same orientation and perspective and the same purpose, so it still fits the "
                    f"same spot in the map. Everything else you may redesign freely: shapes of details, materials, ornaments, small "
                    f"items, lights, more character. ")
        else:
            head = (f"Create an image. I uploaded an animation sheet ({grid}, flat magenta background): the frames of ONE looping animation of "
                    f"an object from {THEME}, for a top-down Among Us style game (seen from the front and slightly above). Redraw "
                    f"the sheet as a new image of the same size in a fresh, richer design. All frames must show exactly the same "
                    f"object at exactly the same size and position in its cell; only the moving part changes from frame to frame, "
                    f"exactly like in the template, so the frames play back as a smooth animation. ")
        prompt = (head + STYLE + " Each object fully inside its own cell with a margin, nothing overlapping another cell. " + BG
                  + " Cells in reading order: " + lines)
        open(os.path.join(OUT, f"prompt_{n:02d}.txt"), "w", encoding="utf-8").write(prompt)
    json.dump(pages, open(os.path.join(OUT, "cells.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(pages)} Blaetter -> {OUT}")
    for n, pg in enumerate(pages, 1):
        print(f"  {n:02d} {pg['kind']:6s} {pg.get('title', '')} {len(pg['cells'])} Zellen")


def apply(target):
    pages = json.load(open(os.path.join(OUT, "cells.json"), encoding="utf-8"))
    for sub in ("props", "consoles"):
        shutil.copytree(os.path.join(ART, sub), os.path.join(target, sub), dirs_exist_ok=True)
    done = miss = 0
    for n, pg in enumerate(pages, 1):
        p = os.path.join(OUT, f"gpt_{n:02d}.png")
        if not os.path.exists(p):
            miss += len(pg["cells"])
            continue
        cols, rows = pg["grid"]
        cut = A.cut_cells(p, cols, rows)
        for c, im in zip(pg["cells"], cut):
            if im is None:
                miss += 1
                continue
            im = M.despill(im)
            for src in c["src"]:
                orig = Image.open(os.path.join(ART, src)).convert("RGBA")
                if pg["kind"] == "door":
                    out = G.place_fill(im, orig, False, False)
                else:
                    out = M.place_foot(im, orig, True, pg["kind"] != "static")
                if out is None:
                    miss += 1
                    continue
                out.save(os.path.join(target, src))
                done += 1
    for k, e in specs()[0].items():                       # Grundbild animierter Arten = erstes GPT-Bild (gleiche Leinwand)
        if e["frames"] > 1 and os.path.exists(os.path.join(target, "props", f"{k}_f0.png")):
            shutil.copy(os.path.join(target, "props", f"{k}_f0.png"), os.path.join(target, "props", f"{k}.png"))
    print(f"{done} Bilder eingesetzt, {miss} fehlen -> {target}")


# ------------------------------------------------------------------ Rauswurf-/Skip-Szenen
# Hintergruende (2160 x 1224) einzeln: auf 3:2 gepolstert (Spiegelung), GPT liefert 1536 x 1024, zurueck auf 2160 x 1440 und
# Polster ab. Ebenen je Szene auf einem Blatt, eingepasst in die alte Leinwand (place_fill). Die 19 Drehbilder der Bruecke
# bleiben aus Blender (eine so lange Folge haelt GPT nicht deckungsgleich).
EJ = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "amberhive"))
SCENES = {
    "swarm": ("the crown hall of the beehive station seen from inside (side view, like a film set): a big round window "
              "opening to the evening sky, wax walls, a floor", ["swarm_fg_l", "swarm_fg_r", "swarm_lamp", "bee", "bee_far", "wing"]),
    "well": ("a cross section of the honey well (side view): a stone and wax well ring, a honey lake, a swivel bridge mechanism",
             ["well_honey", "well_stream", "well_cog", "well_foam", "well_ripple", "well_bubble"]),
    "queen": ("the throne room of the bee queen (side view): a wax throne, velvet curtains, candles",
              ["queen_body", "queen_head_awake", "queen_head_yawn", "queen_head_sleep", "queen_arm", "queen_wing", "queen_crown",
               "queen_fan", "queen_flame", "queen_snot", "queen_z"]),
    "deck": ("the sun deck on top of the giant beehive (side view): wooden deck with railing, wax dome, the land far below, sky",
             ["deck_flower", "deck_stem", "deck_flag", "deck_cloud0", "deck_cloud1", "deck_cloud2", "deck_drop", "deck_splat"]),
}
LAYER_DESC = {
    "swarm_fg_l": "a foreground wall piece on the left", "swarm_fg_r": "a foreground piece on the right (wax pillar and shelf)",
    "swarm_lamp": "a hanging lantern", "bee": "a friendly bee flying, side view", "bee_far": "a smaller distant bee", "wing": "a single bee wing",
    "well_honey": "the honey surface in front (translucent golden honey)", "well_stream": "a thick vertical stream of honey",
    "well_cog": "a brass cog wheel", "well_foam": "a flat patch of honey foam", "well_ripple": "a ring ripple on honey", "well_bubble": "a honey bubble",
    "queen_body": "the bee queen sitting on her throne, body only without head (robe, striped abdomen)",
    "queen_head_awake": "the head of the queen, awake and bored", "queen_head_yawn": "the same head yawning widely",
    "queen_head_sleep": "the same head asleep", "queen_arm": "her waving arm", "queen_wing": "one of her wings", "queen_crown": "her small crown",
    "queen_fan": "a feather fan", "queen_flame": "a candle flame", "queen_snot": "a sleep bubble", "queen_z": "a letter Z for snoring",
    "deck_flower": "a big flower head", "deck_stem": "its stem with leaves in a pot", "deck_flag": "a small pennant flag",
    "deck_cloud0": "a fluffy cloud", "deck_cloud1": "a fluffy cloud", "deck_cloud2": "a small fluffy cloud", "deck_drop": "a honey drop",
    "deck_splat": "a small honey splash",
}


def eject_pages():
    pages = []
    for sc, (theme, layers) in SCENES.items():
        pages.append(dict(kind="ejectbg", scene=sc, theme=theme, cells=[dict(src=[f"task_eject_hive_{sc}_bg.jpg"], name=f"{sc}_bg")]))
        grid = [4, 3] if len(layers) > 8 else [4, 2] if len(layers) > 6 else [3, 2]
        pages.append(dict(kind="ejectlayers", scene=sc, theme=theme, grid=grid,
                          cells=[dict(src=[f"task_eject_hive_{n}.png"], name=n, desc=LAYER_DESC[n]) for n in layers]))
    return pages


def eject_refs(start):
    pages = eject_pages()
    for i, pg in enumerate(pages):
        n = start + i
        if pg["kind"] == "ejectbg":
            im = Image.open(os.path.join(EJ, pg["cells"][0]["src"][0])).convert("RGB")
            top = (1440 - im.height) // 2
            bot = 1440 - im.height - top
            arr = np.asarray(im)
            arr = np.concatenate([arr[top - 1::-1], arr, arr[:-bot - 1:-1]], axis=0)
            Image.fromarray(arr).resize((SW, SH), Image.LANCZOS).save(os.path.join(OUT, f"ref_{n:02d}.png"))
            prompt = (f"Create an image. I uploaded a background painting for a short cutscene of an Among Us style game: {pg['theme']}. Repaint it "
                      f"as a new image of the same size and framing with a fresh, richer and more beautiful design. Keep the overall "
                      f"layout: horizon, floor line, the big shapes and openings at the same places (animated layers sit on top of "
                      f"them). Everything else you may redesign: materials, ornaments, light, small details, atmosphere. " + STYLE
                      + " No characters, no bees, no text.")
        else:
            cols, rows = pg["grid"]
            cw, ch = SW / cols, SH / rows
            img = Image.new("RGBA", (SW, SH), (255, 0, 255, 255))
            for k, c in enumerate(pg["cells"]):
                im = solid(os.path.join(EJ, c["src"][0]))
                s = min(cw * 0.84 / im.width, ch * 0.84 / im.height)
                r = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
                img.alpha_composite(r, (round((k % cols) * cw + (cw - r.width) / 2), round((k // cols) * ch + (ch - r.height) / 2)))
            img.convert("RGB").save(os.path.join(OUT, f"ref_{n:02d}.png"))
            lines = " ".join(f"{k + 1}. {c['desc']}" for k, c in enumerate(pg["cells"]))
            prompt = (f"Create an image. I uploaded a sprite sheet ({cols} columns x {rows} rows, flat magenta background) with the separate layers of a "
                      f"short cutscene of an Among Us style game ({pg['theme']}, side view). Redraw the sheet as a new image of the "
                      f"same size with a fresh, richer design. Keep for every element the same position in its cell, the same size, "
                      f"pose and purpose (they are animated and combined in the game; heads must fit the same body). " + STYLE
                      + " Each element fully inside its own cell with a margin. " + BG + " Cells in reading order: " + lines)
        open(os.path.join(OUT, f"prompt_{n:02d}.txt"), "w", encoding="utf-8").write(prompt)
    json.dump(pages, open(os.path.join(OUT, "eject_cells.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(pages)} Szenenblaetter ab {start:02d}")


def eject_apply(target, start):
    pages = json.load(open(os.path.join(OUT, "eject_cells.json"), encoding="utf-8"))
    os.makedirs(target, exist_ok=True)
    for f in os.listdir(EJ):
        if f.startswith("task_eject_hive_"):
            shutil.copy(os.path.join(EJ, f), os.path.join(target, f))
    done = 0
    for i, pg in enumerate(pages):
        p = os.path.join(OUT, f"gpt_{start + i:02d}.png")
        if not os.path.exists(p):
            continue
        if pg["kind"] == "ejectbg":
            src = pg["cells"][0]["src"][0]
            orig = Image.open(os.path.join(EJ, src))
            big = Image.open(p).convert("RGB").resize((2160, 1440), Image.LANCZOS)
            top = (1440 - orig.height) // 2
            big.crop((0, top, 2160, top + orig.height)).save(os.path.join(target, src), quality=90)
            done += 1
            continue
        cols, rows = pg["grid"]
        for c, im in zip(pg["cells"], A.cut_cells(p, cols, rows)):
            if im is None:
                continue
            orig = Image.open(os.path.join(EJ, c["src"][0])).convert("RGBA")
            out = G.place_fill(M.despill(im), orig, False, False)
            if out is not None:
                out.save(os.path.join(target, c["src"][0]))
                done += 1
    print(f"{done} Szenenbilder eingesetzt -> {target}")


def _n_map_pages():
    return len(json.load(open(os.path.join(OUT, "cells.json"), encoding="utf-8")))


if __name__ == "__main__":
    if sys.argv[1] == "refs":
        refs()
        eject_refs(_n_map_pages() + 1)
    else:
        apply(sys.argv[2])
        eject_apply(os.path.join(sys.argv[2], "eject"), _n_map_pages() + 1)
