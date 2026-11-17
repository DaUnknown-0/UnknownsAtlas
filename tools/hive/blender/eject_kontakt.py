# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_kontakt.py - Kontaktbogen der Amberhive-Szenen (normales Python mit PIL, kein Blender).
# Setzt Hintergrund + Ebenen zu Standbildern zusammen (t = 0 und zwei spaetere Zeitpunkte), Auswertung der Keys wie im
# Vorschau-Kino (tools/eject_theater/index.html, ohne Partikel). Der Spieler ist ein roter Platzhalter, der gelbe Rahmen
# zeigt den Kameraausschnitt.
#   python tools/hive/blender/eject_kontakt.py            -> tools/hive/art/eject/<id>_kontakt.png

import json
import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.path.join(ATLAS, "assets")
OUT = os.path.join(ATLAS, "tools", "hive", "art", "eject")
PPU = 180
EASE = {"lin": lambda u: u, "in": lambda u: u * u, "out": lambda u: 1 - (1 - u) ** 2, "io": lambda u: u * u * (3 - 2 * u),
        "back": lambda u: 1 + (u - 1) ** 2 * (2.70158 * (u - 1) + 1.70158), "inback": lambda u: u * u * (2.70158 * u - 1.70158)}
PROPS = ("x", "y", "rot", "sx", "sy", "s", "a", "b", "flip")
_cache = {}
TIMES = {"hive_swarm": [0.0, 2.2, 4.6], "hive_well": [0.0, 2.4, 4.9], "hive_skip_queen": [0.0, 2.3, 6.0],
         "hive_skip_sundeck": [0.0, 3.0, 4.8]}


def tracks(keys):
    tr = {}
    for t, p, e in keys or []:
        for k, v in p.items():
            if k in PROPS:
                tr.setdefault(k, []).append((t, v, e, p.get("arc", 0) if k == "y" else 0))
    return tr


def sample(track, t, d):
    if not track:
        return d
    if t <= track[0][0]:
        return track[0][1]
    for i in range(1, len(track)):
        nt, nv, ne, arc = track[i]
        if t < nt:
            pt, pv = track[i - 1][0], track[i - 1][1]
            u = (t - pt) / max(1e-6, nt - pt)
            if ne == "hold":
                return pv
            v = pv + (nv - pv) * EASE.get(ne, EASE["io"])(u)
            return v + arc * 4 * u * (1 - u)
    return track[-1][1]


def envelope(t, t0, t1):
    if t0 is None:
        return 1.0
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / 0.12) * min(1.0, (t1 - t) / 0.12)


def local(o, t):
    tr = tracks(o.get("keys"))
    L = {k: sample(tr.get(k), t, o.get(k, 1 if k in ("sx", "sy", "s", "a", "b", "flip") else 0)) for k in PROPS}
    for w in o.get("wobble", []):
        env = envelope(t, w.get("t0"), w.get("t1"))
        if env > 0:
            L[w["p"]] += w["amp"] * math.sin(2 * math.pi * w["f"] * t + w.get("ph", 0)) * env
    return L


def compose(L, P):
    W = {"x": L["x"], "y": L["y"], "rot": L["rot"], "sx": L["s"] * L["sx"] * (-1 if L["flip"] < 0 else 1), "sy": L["s"] * L["sy"],
         "a": L["a"], "b": L["b"]}
    if not P:
        return W
    r = math.radians(P["rot"])
    lx, ly = W["x"] * P["sx"], W["y"] * P["sy"]
    sgn = 1 if P["sx"] * P["sy"] >= 0 else -1
    return {"x": P["x"] + lx * math.cos(r) - ly * math.sin(r), "y": P["y"] + lx * math.sin(r) + ly * math.cos(r),
            "rot": P["rot"] + W["rot"] * sgn, "sx": W["sx"] * P["sx"], "sy": W["sy"] * P["sy"], "a": W["a"] * P["a"], "b": W["b"]}


def img(name):
    if name not in _cache:
        for d in (os.path.join(ASSETS, "amberhive"), ASSETS):
            p = os.path.join(d, name)
            if os.path.exists(p):
                _cache[name] = Image.open(p).convert("RGBA")
                break
        else:
            raise FileNotFoundError(name)
    return _cache[name]


def tint(im, hexcol, b):
    if not hexcol and b == 1:
        return im
    c = (1, 1, 1) if not hexcol else tuple(int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, bl, a = im.split()
    r = r.point(lambda v: int(v * c[0] * b))
    g = g.point(lambda v: int(v * c[1] * b))
    bl = bl.point(lambda v: int(v * c[2] * b))
    return Image.merge("RGBA", (r, g, bl, a))


def crew():
    im = Image.new("RGBA", (PPU, PPU), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = lambda x, y: (PPU / 2 + x * PPU, PPU / 2 - y * PPU)  # noqa: E731
    d.rounded_rectangle([u(-0.46, 0.24), u(-0.26, -0.2)], 12, fill=(150, 20, 30), outline=(16, 16, 20), width=6)
    d.rounded_rectangle([u(-0.28, -0.2), u(-0.08, -0.5)], 12, fill=(150, 20, 30), outline=(16, 16, 20), width=6)
    d.rounded_rectangle([u(0.08, -0.2), u(0.28, -0.5)], 12, fill=(200, 30, 40), outline=(16, 16, 20), width=6)
    d.rounded_rectangle([u(-0.33, 0.5), u(0.33, -0.34)], 40, fill=(200, 30, 40), outline=(16, 16, 20), width=7)
    d.rounded_rectangle([u(0.0, 0.34), u(0.42, 0.1)], 18, fill=(149, 202, 220), outline=(16, 16, 20), width=6)
    return im


def draw(canvas, im, W, pivot, origin):
    sx, sy = W["sx"], W["sy"]
    if abs(sx) < 1e-3 or abs(sy) < 1e-3 or W["a"] <= 0.01:
        return
    w, h = im.size
    nw, nh = max(1, int(round(w * abs(sx)))), max(1, int(round(h * abs(sy))))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    if sx < 0:
        im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
    px = pivot[0] if sx >= 0 else 1 - pivot[0]
    py = pivot[1] if sy >= 0 else 1 - pivot[1]
    # Pivot ins Zentrum eines groesseren Bildes legen, dann um den Pivot drehen
    R = int(math.hypot(nw, nh)) + 4
    big = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    big.paste(im2, (int(R - px * nw), int(R - (1 - py) * nh)))
    if W["rot"]:
        big = big.rotate(W["rot"], resample=Image.BICUBIC)
    if W["a"] < 0.999:
        a = big.split()[3].point(lambda v: int(v * max(0.0, min(1.0, W["a"]))))
        big.putalpha(a)
    cx = origin[0] + W["x"] * PPU
    cy = origin[1] - W["y"] * PPU
    canvas.alpha_composite(big, (int(cx - R), int(cy - R)))


def frame(sc, t):
    bw, bh = sc.get("bounds", [12, 6.8])
    W, H = int(bw * PPU), int(bh * PPU)
    canvas = Image.new("RGBA", (W, H), (30, 30, 30, 255))
    origin = (W / 2, H / 2)
    world = {}
    items = []
    for o in sc["objects"]:
        if o.get("parent") == "player":
            continue
        L = local(o, t)
        Wt = compose(L, world.get(o.get("parent")))
        world[o["id"]] = Wt
        if o.get("sprite"):
            items.append((o.get("z", 0), o, Wt))
    pl = sc.get("player", {})
    if not sc.get("skip"):
        L = local(pl, t)
        PW = compose(L, world.get(pl.get("parent")))
        if not (pl.get("hide") is not None and t >= pl["hide"]):
            items.append((0, {"id": "player", "sprite": None}, PW))
    items.sort(key=lambda it: it[0])
    for z, o, Wt in items:
        if o["id"] == "player":
            draw(canvas, crew(), Wt, (0.5, 0.5), origin)
            continue
        im = tint(img(o["sprite"]), o.get("tint"), Wt["b"])
        draw(canvas, im, Wt, o.get("pivot", (0.5, 0.5)), origin)
    ctr = {}
    for kt, p, e in sc["camera"]:
        for k, v in p.items():
            ctr.setdefault(k, []).append((kt, v, e, 0))
    cam = {k: sample(ctr.get(k), t, 1 if k == "z" else 0) for k in ("z", "x", "y")}
    vw, vh = 11 / cam["z"], 6.2 / cam["z"]
    hx, hy = max(0, bw / 2 - vw / 2), max(0, bh / 2 - vh / 2)
    cx, cy = max(-hx, min(hx, cam["x"])), max(-hy, min(hy, cam["y"]))
    d = ImageDraw.Draw(canvas)
    d.rectangle([origin[0] + (cx - vw / 2) * PPU, origin[1] - (cy + vh / 2) * PPU, origin[0] + (cx + vw / 2) * PPU,
                 origin[1] - (cy - vh / 2) * PPU], outline=(255, 230, 0, 255), width=5)
    d.text((20, 20), f"t = {t:.2f}", fill=(255, 255, 255, 255))
    return canvas


def main():
    doc = json.load(open(os.path.join(ASSETS, "eject_scenes.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    for sc in doc["scenes"]:
        if sc.get("map") != "amberhive":
            continue
        L = sc["length"]
        times = TIMES.get(sc["id"], [0.0, round(L * 0.45, 2), round(L * 0.8, 2)])
        frames = [frame(sc, t).resize((1080, 612), Image.LANCZOS) for t in times]
        sheet = Image.new("RGBA", (1080, 612 * len(frames) + 8 * (len(frames) - 1)), (0, 0, 0, 255))
        for i, f in enumerate(frames):
            sheet.alpha_composite(f, (0, i * 620))
        p = os.path.join(OUT, f"{sc['id']}_kontakt.png")
        sheet.convert("RGB").save(p)
        print(p, times)


if __name__ == "__main__":
    main()
