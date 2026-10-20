# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_art.py - Polaris Express: die echte 2D-Grafik (statt Graybox) fuer gen_train.py.
#
# build(ctx) bekommt den Kontext aus gen_train.art_ctx und liefert Bodenbild, Objekt- und Konsolen-Atlanten,
# Minimap und Paketdateien (README "Lieferumfang"). Teile:
#   train_style.py     Palette, Schriften, gemeinsame Zeichenhelfer
#   train_floor.py     Bodenbild 128 px/m
#   train_props.py     Objekt-Sprites (OPAQUE/GLASS-Rechtecke, Treppen, Kessel, Lochzangen ...)
#   train_consoles.py  Konsolen-Sprites fuer alle 46 Skeld-Schluessel
#   train_extras.py    Minimap, button_train.png, icon_train.png, Minispiel-Tafel, Fahrschein, Treppensymbol
#
# Zusaetzlich schreibt build() tools/_train/preview_art.jpg: Landschaft, Boden, Objekte und Konsolen zusammengesetzt,
# wie es im Spiel aussieht (gen_train.preview.png zeigt nur den Boden mit Markierungen), und preview_scroll.jpg
# (der Landschaftsstreifen dreimal nebeneinander als Nahtprobe).
#
# Fahrender Zug (zweiter Auftrag): die Bodenkacheln sind RGBA und ausserhalb des Zugs durchsichtig; darunter laufen
# die "scroll"-Ebenen (train_scroll_0.png nah, train_scroll_far_0.png fern mit Parallaxe 0,5) nach Westen.

import sys

from PIL import Image, ImageDraw, ImageFilter

import museum_art as A
import train_style  # noqa: F401  (Schrift-Ersatz fuer arialbd.ttf wird beim Import eingerichtet)
import train_floor
import train_props

FLOOR_PPM = 128
ATLAS = 2048


def render_props(ctx, ppm):
    items = train_props.all_props(ctx)
    images, meta = [], []
    for i, (kind, sh) in enumerate(items):
        im, wx, wy, base = train_props.draw(kind, sh, i, ppm, ctx)
        images.append((i, im))
        fx0, _y0, fx1, _y1 = A.shape_bounds(sh)
        meta.append((kind, wx, wy, base, fx0, fx1, im))
    atlases, placed = A.pack(images, max_w=ATLAS, max_h=ATLAS)
    props = []
    for i, (kind, wx, wy, base, fx0, fx1, im) in enumerate(meta):
        page, x, y, w, h = placed[i]
        props.append({"kind": kind, "atlas": page, "x": x, "y": atlases[page].height - y - h, "w": w, "h": h,
                      "worldX": round(wx, 4), "worldY": round(wy, 4), "baseY": round(base, 4),
                      "footX0": round(fx0, 4), "footX1": round(fx1, 4)})
    print(f"train_art: props {len(props)} in {len(atlases)} atlas(es)")
    return atlases, props, [(m[6], m[1], m[2], m[3]) for m in meta]


def render_consoles(ctx, ppm):
    import train_consoles
    sprites = train_consoles.render_all(ctx, ppm)             # key -> (Bild, pivot_x_px, pivot_y_px von unten)
    keys = sorted(sprites)
    images = [(i, sprites[k][0].filter(ImageFilter.GaussianBlur(0.4))) for i, k in enumerate(keys)]
    atlases, placed = A.pack(images, max_w=ATLAS, max_h=ATLAS)
    out = []
    for i, key in enumerate(keys):
        page, x, y, w, h = placed[i]
        _im, ax, ay = sprites[key]
        out.append({"key": key, "atlas": page, "x": x, "y": atlases[page].height - y - h, "w": w, "h": h,
                    "pivotX": round(ax / w, 4), "pivotY": round(ay / h, 4)})
    print(f"train_art: console sprites {len(out)} in {len(atlases)} atlas(es)")
    return atlases, out, sprites


def scroll_backdrop(ctx, near, far):
    """Scroll-Ebenen ueber die ganze Kartenbreite gekachelt (Stellung 0), wie das Spiel sie unter die Kacheln legt."""
    bx0, by0, bx1, by1 = ctx["bounds"]
    w, h = int(round((bx1 - bx0) * FLOOR_PPM)), int(round((by1 - by0) * FLOOR_PPM))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    for layer in (near, far):
        if layer is None:
            continue
        x = 0
        while x < w:
            img.alpha_composite(layer.convert("RGBA").crop((0, 0, min(layer.width, w - x), min(layer.height, h))), (x, 0))
            x += layer.width
    return img


def preview_scroll(ctx, near, far):
    """Nahtprobe: der Streifen dreimal nebeneinander (ferne Ebene darueber), tools/_train/preview_scroll.jpg."""
    img = Image.new("RGBA", (near.width * 3, near.height), (0, 0, 0, 255))
    for k in range(3):
        img.alpha_composite(near.convert("RGBA"), (k * near.width, 0))
        if far is not None:
            img.alpha_composite(far, (k * far.width, 0))
    d = ImageDraw.Draw(img)
    for k in (1, 2):
        d.line([(k * near.width, 0), (k * near.width, 40)], fill=(255, 60, 60, 255), width=3)
        d.line([(k * near.width, img.height - 40), (k * near.width, img.height)], fill=(255, 60, 60, 255), width=3)
    img.convert("RGB").save(ctx["preview"] / "preview_scroll.jpg", quality=80)


def preview(ctx, floor, prop_imgs, consoles, console_imgs, ppm, backdrop=None):
    """Scroll-Ebenen + Boden + Objekte + Konsolen zusammengesetzt (Sprites von 160 auf 128 px/m skaliert, nach
    Standlinie sortiert): so sieht die Karte im Spiel aus (Stellung 0 der Landschaft)."""
    bx0, by0, bx1, by1 = ctx["bounds"]
    f = FLOOR_PPM / ppm
    img = floor.convert("RGBA")
    if backdrop is not None:
        base = backdrop.copy()
        base.alpha_composite(img)
        img = base
    layers = []
    for im, wx, wy, base in prop_imgs:
        layers.append((base, im, wx, wy))
    for key, (im, ax, ay) in console_imgs.items():
        x, y = consoles[key]
        wx = x - ax / ppm
        wy = y - ay / ppm
        layers.append((y, im, wx, wy))
    layers.sort(key=lambda t: -t[0])
    for _base, im, wx, wy in layers:
        sm = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.LANCZOS)
        px = int(round((wx - bx0) * FLOOR_PPM))
        py = int(round((by1 - wy) * FLOOR_PPM)) - sm.height
        A.HD.paste_clipped(img, sm, px, py)
    img.convert("RGB").save(ctx["preview"] / "preview_art.jpg", quality=88)


def build(ctx):
    ppm = ctx["prop_ppm"]
    out = {"floor_ppm": FLOOR_PPM, "noFadeKinds": ["kessel", "treppe_auf", "treppe_ab", "kohle"],
           "files": {}, "taskArt": {}, "taskText": {}}
    print("train_art: props ...")
    out["props_atlases"], out["props"], prop_imgs = render_props(ctx, ppm)
    print("train_art: consoles ...")
    try:
        out["console_atlases"], out["consoleSprites"], console_imgs = render_consoles(ctx, ppm)
    except ImportError:
        out["console_atlases"], out["consoleSprites"], console_imgs = [], [], {}
    print("train_art: floor ...")
    out["floor"] = train_floor.render(ctx, FLOOR_PPM)
    print("train_art: scroll ...")
    bx0, by0, bx1, by1 = ctx["bounds"]
    near = train_floor.render_scroll(ctx, FLOOR_PPM)
    far = train_floor.render_scroll_far(ctx, FLOOR_PPM)
    out["scroll"] = [
        {"file": "train_scroll_0.png", "ppm": FLOOR_PPM, "y0": by0, "y1": by1, "width_m": train_floor.SCROLL_W, "parallax": 1.0},
        {"file": "train_scroll_far_0.png", "ppm": FLOOR_PPM, "y0": by0, "y1": by1, "width_m": train_floor.SCROLL_W, "parallax": 0.5},
    ]
    print("train_art: minimap, files ...")
    import train_extras
    out["minimap"], labels = train_extras.minimap(ctx)
    # gen_train.minimap() hat MAP_LABELS schon mit seiner (hier evtl. ersatzweisen) Schrift berechnet; die
    # Rechtecke zur Minimap hier gehoeren zu diesem Bild, deshalb werden sie vor emit() ausgetauscht.
    main = sys.modules.get("__main__")
    if main is not None and getattr(main, "KEY", None) == "train" and isinstance(getattr(main, "MAP_LABELS", None), list):
        main.MAP_LABELS[:] = labels
    out["files"] = train_extras.files(ctx)
    out["files"]["train_scroll_0.png"] = near
    out["files"]["train_scroll_far_0.png"] = far
    print("train_art: fx ...")
    import train_fx
    fx = train_fx.files()                                        # Effekte und Minispielgrafik der Zug-Sabotagen
    out["files"].update(fx)
    train_fx.preview_sheet(fx, ctx["preview"] / "preview_fx.png")
    out["taskArt"] = {"task_wald_panel.png": "task_train_panel.png"}
    preview_scroll(ctx, near, far)
    preview(ctx, out["floor"], prop_imgs, ctx["consoles"], console_imgs, ppm, scroll_backdrop(ctx, near, far))
    return out
