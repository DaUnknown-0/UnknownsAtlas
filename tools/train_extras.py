# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# train_extras.py - Minimap, Freeplay-Logo (button_train.png), Lobby-Symbol (icon_train.png), Minispiel-Tafel
# (task_train_panel.png, Holz und Messing, 720 x 520 wie task_wald_panel.png) und der Fahrschein fuer den
# Use-Knopf der Lochzange (task_ticket_button.png, 256 x 256).

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import map_labels
import train_style as S
from train_style import font

MM_S = 24                     # Minimap: Pixel je Meter (wie gen_train.minimap)
MM_FILL = (224, 214, 236, 235)
MM_INK = (30, 22, 44, 255)
MM_LINE = (224, 214, 236, 120)


# ------------------------------------------------------------------ Minimap

def minimap(ctx):
    """Minimap wie gen_train.minimap (gleiche Schrift, gleicher Massstab), mit Wagenumrissen, Treppenpfeilen und
    Beschriftung; liefert (Bild, Label-Rechtecke fuer AtlasMapDef.MapLabels)."""
    bx0, by0, bx1, by1 = ctx["bounds"]
    s = MM_S
    ww, hh = int((bx1 - bx0) * s), int((by1 - by0) * s)
    img = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    Pt = lambda x, y: ((x - bx0) * s, (by1 - y) * s)
    wall = ctx["wall"]
    ay0, ay1 = ctx["decks"]["A"]
    uy0, uy1 = ctx["decks"]["B"]
    for c in ctx["cars"]:
        d.rounded_rectangle([*Pt(c["x0"] - wall, ay1 + wall), *Pt(c["x1"] + wall, ay0 - wall)], radius=6, outline=MM_LINE, width=2)
        if c["kind"] == "dd":
            d.rounded_rectangle([*Pt(c["x0"] - wall, uy1 + wall), *Pt(c["x1"] + wall, uy0 - wall)], radius=6, outline=MM_LINE, width=2)
            for xx in (c["x0"] - wall, c["x1"] + wall):
                y = ay0 - 0.6
                while y > uy1 + 0.6:
                    d.line([Pt(xx, y), Pt(xx, max(y - 0.35, uy1 + 0.6))], fill=MM_LINE, width=2)
                    y -= 0.6
    # Lok-Silhouette: Kessel als Umriss, Schornstein
    bx0_, by0_, bx1_, by1_ = ctx["boiler"]
    d.rounded_rectangle([*Pt(bx0_, by1_), *Pt(bx1_ + 0.8, by0_)], radius=8, fill=(90, 80, 110, 160), outline=MM_LINE, width=2)
    walk = ctx["walk"]
    for p in ctx["geom_parts"](walk):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=MM_FILL)
        for h in p.interiors:
            d.polygon([Pt(*q) for q in h.coords], fill=(0, 0, 0, 0))
    for p in ctx["geom_parts"](walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([Pt(*q) for q in ring.coords], fill=MM_INK, width=4, joint="curve")
    for st in ctx["stairs"]:
        for key, down in (("main", False), ("upper", True)):
            x0, y0, x1, y1 = st[key]
            cx, cy = Pt((x0 + x1) / 2, (y0 + y1) / 2)
            k = 7
            pts = [(cx - k, cy - k * 0.6), (cx + k, cy - k * 0.6), (cx, cy + k * 0.8)] if down else \
                  [(cx - k, cy + k * 0.6), (cx + k, cy + k * 0.6), (cx, cy - k * 0.8)]
            d.polygon(pts, fill=MM_INK)
    f = font(14, "bold")
    labels = []
    for r in ctx["rooms"]:
        area = ctx["room_geom"][r["key"]].intersection(walk)
        c = area.representative_point()
        if r["key"] in ctx["label_at"]:
            lx, ly = ctx["label_at"][r["key"]]
            c = type(c)(lx, ly)
        map_labels.place(d, f, r["name"], c.x, c.y, area.buffer(-0.15), s, Pt, MM_INK, labels)
    dd = [c for c in ctx["cars"] if c["kind"] == "dd"]
    d.text(Pt(dd[0]["x0"] - 0.4, uy0 - 0.9), "UPPER DECK", font=font(15, "bold"), fill=(224, 214, 236, 255), anchor="lm")
    tb = ctx["ticket"]["button"]
    d.ellipse([*Pt(tb[0] - 0.35, tb[1] + 0.35), *Pt(tb[0] + 0.35, tb[1] - 0.35)], outline=(240, 200, 60, 200), width=2)
    return img, labels


# ------------------------------------------------------------------ Text mit Verlauf, Kontur und Schatten

def fancy_text(text, size, kind, top, bottom, outline=(255, 255, 255, 255), ow=8, shadow=(40, 20, 10, 255), sh=(0, 10), ss=2):
    f = font(size * ss, kind)
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    bb = tmp.textbbox((0, 0), text, font=f, anchor="lt", stroke_width=ow * ss)
    w, h = bb[2] - bb[0] + 8 * ss, bb[3] - bb[1] + 8 * ss + abs(sh[1]) * ss
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    org = (4 * ss - bb[0], 4 * ss - bb[1])
    d.text((org[0] + sh[0] * ss, org[1] + sh[1] * ss), text, font=f, fill=shadow, anchor="lt", stroke_width=ow * ss, stroke_fill=shadow)
    d.text(org, text, font=f, fill=outline, anchor="lt", stroke_width=ow * ss, stroke_fill=outline)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text(org, text, font=f, fill=255, anchor="lt")
    rows = np.nonzero(np.asarray(mask).max(axis=1) > 0)[0]
    y0, y1 = (rows[0], rows[-1]) if rows.size else (0, h - 1)
    t = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    grad = np.array(top[:3], np.float32) * (1 - t) + np.array(bottom[:3], np.float32) * t
    g = np.zeros((h, w, 4), np.uint8)
    g[..., :3] = np.broadcast_to(grad, (h, w, 3)).astype(np.uint8)
    g[..., 3] = np.asarray(mask)
    gi = Image.fromarray(g, "RGBA")
    gl = ImageDraw.Draw(gi)
    layer.alpha_composite(gi)
    # Glanzband oben
    gloss = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.rectangle([0, y0, w, y0 + (y1 - y0) * 0.42], fill=(255, 255, 255, 70))
    gloss.putalpha(Image.fromarray(np.minimum(np.asarray(gloss.getchannel("A")), np.asarray(mask)), "L"))
    layer.alpha_composite(gloss)
    return layer.resize((w // ss, h // ss), Image.LANCZOS)


# ------------------------------------------------------------------ Freeplay-Logo und Lobby-Symbol

def loco_badge(size, ss=3):
    """Rundes Abzeichen: Nachthimmel mit Mond, Schneehuegel, Lokfront mit Scheinwerfer, Tannen, Schneeflocken."""
    N = size * ss
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = N / 2 - 4 * ss
    cx = cy = N / 2
    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    sky = np.zeros((N, N, 4), np.uint8)
    t = (np.arange(N) / N)[:, None]
    for k, (a, b) in enumerate(((22, 90), (28, 110), (70, 180))):
        sky[..., k] = (a + (b - a) * t).astype(np.uint8)
    sky[..., 3] = 255
    im.paste(Image.fromarray(sky, "RGBA"), (0, 0), mask)
    d = ImageDraw.Draw(im)
    rnd = random.Random(9)
    for _ in range(40):
        a = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0, r * 0.95)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        if y < cy + r * 0.2:
            sr = rnd.choice((1.5, 2, 3)) * ss
            d.ellipse([x - sr, y - sr, x + sr, y + sr], fill=(255, 250, 230, 230))
    mx, my, mr = cx - r * 0.45, cy - r * 0.45, r * 0.2
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(250, 244, 210, 255))
    d.ellipse([mx - mr * 0.6, my - mr * 1.1, mx + mr * 1.4, my + mr * 0.9], fill=(26, 32, 70, 255))
    # Schneehuegel und Tannen
    hills = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hills)
    hd.ellipse([cx - r * 1.4, cy + r * 0.35, cx + r * 0.5, cy + r * 1.8], fill=(196, 208, 230, 255))
    hd.ellipse([cx - r * 0.2, cy + r * 0.45, cx + r * 1.6, cy + r * 1.9], fill=(214, 224, 240, 255))
    hills.putalpha(Image.fromarray(np.minimum(np.asarray(hills.getchannel("A")), np.asarray(mask)), "L"))
    im.alpha_composite(hills)
    d = ImageDraw.Draw(im)
    for tx, th in ((cx - r * 0.75, r * 0.45), (cx - r * 0.55, r * 0.6), (cx + r * 0.72, r * 0.5), (cx + r * 0.88, r * 0.35)):
        ty = cy + r * 0.55
        for k in range(3):
            w_ = th * (0.55 - k * 0.12)
            yk = ty - th * (0.3 * k)
            d.polygon([(tx - w_, yk), (tx + w_, yk), (tx, yk - th * 0.55)], fill=(34, 70, 54, 255), outline=(14, 16, 20, 255), width=2 * ss)
            d.polygon([(tx - w_ * 0.55, yk - th * 0.18), (tx + w_ * 0.55, yk - th * 0.18), (tx, yk - th * 0.5)], fill=(210, 222, 240, 255))
    # Lok von vorn: Pufferbohle, Rauchkammer, Tuer, Scheinwerfer, Schornstein, Dampf
    lx, ly, lr = cx + r * 0.05, cy + r * 0.2, r * 0.42
    ink = (14, 16, 20, 255)
    ow = int(3.5 * ss)
    d.rectangle([lx - lr * 1.25, ly + lr * 0.7, lx + lr * 1.25, ly + lr * 1.0], fill=(176, 46, 42, 255), outline=ink, width=ow)
    for sx in (-1, 1):
        d.ellipse([lx + sx * lr * 1.0 - lr * 0.14, ly + lr * 0.72, lx + sx * lr * 1.0 + lr * 0.14, ly + lr * 0.98], fill=(120, 124, 136, 255), outline=ink, width=ow)
    d.polygon([(lx - lr * 1.2, ly + lr * 1.0), (lx + lr * 1.2, ly + lr * 1.0), (lx + lr * 0.5, ly + lr * 1.45), (lx - lr * 0.5, ly + lr * 1.45)],
              fill=(60, 62, 72, 255), outline=ink, width=ow)
    d.rectangle([lx - lr * 0.28, ly - lr * 1.75, lx + lr * 0.28, ly - lr * 0.8], fill=(44, 46, 54, 255), outline=ink, width=ow)
    d.rectangle([lx - lr * 0.36, ly - lr * 1.85, lx + lr * 0.36, ly - lr * 1.65], fill=(222, 182, 92, 255), outline=ink, width=ow)
    d.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(50, 52, 60, 255), outline=ink, width=ow)
    d.ellipse([lx - lr * 0.8, ly - lr * 0.8, lx + lr * 0.8, ly + lr * 0.8], fill=(38, 40, 48, 255), outline=(222, 182, 92, 255), width=ow)
    d.ellipse([lx - lr * 0.12, ly - lr * 0.12, lx + lr * 0.12, ly + lr * 0.12], fill=(222, 182, 92, 255), outline=ink, width=2 * ss)
    d.rectangle([lx - lr * 0.3, ly + lr * 0.3, lx + lr * 0.3, ly + lr * 0.5], fill=(222, 182, 92, 255), outline=ink, width=2 * ss)
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([lx - lr * 0.75, ly - lr * 1.5, lx + lr * 0.75, ly - lr * 0.1], fill=(255, 220, 140, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(10 * ss))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    d.ellipse([lx - lr * 0.22, ly - lr * 1.0, lx + lr * 0.22, ly - lr * 0.55], fill=(255, 240, 190, 255), outline=ink, width=ow)
    d.ellipse([lx - lr * 0.1, ly - lr * 0.92, lx + lr * 0.08, ly - lr * 0.72], fill=(255, 255, 250, 255))
    for k, (px, py, pr) in enumerate(((lx - lr * 0.1, ly - lr * 2.05, lr * 0.28), (lx - lr * 0.5, ly - lr * 2.35, lr * 0.36), (lx - lr * 1.0, ly - lr * 2.55, lr * 0.42))):
        if math.hypot(px - cx, py - cy) + pr < r:
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(236, 240, 248, 230), outline=(160, 170, 190, 255), width=2 * ss)
            d.ellipse([px - pr * 0.45, py - pr * 0.55, px + pr * 0.15, py - pr * 0.05], fill=(255, 255, 255, 255))
    d.rectangle([lx - lr * 0.95, ly - lr * 0.98, lx + lr * 0.95, ly - lr * 0.84], fill=(226, 234, 246, 255))     # Schnee auf der Rauchkammer
    for _ in range(16):                                                                                            # Schneeflocken
        a = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0, r * 0.95)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        sr = rnd.uniform(2, 4) * ss
        d.ellipse([x - sr, y - sr, x + sr, y + sr], fill=(255, 255, 255, 200))
    ring = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 255), width=int(5 * ss))
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    out.alpha_composite(ring)
    return out.resize((size, size), Image.LANCZOS)


def button():
    """Freeplay-Logo 1000 x 250: schwarze Tafel mit weissem Rand (wie button_park.png), Abzeichen links,
    POLARIS EXPRESS in Gold mit weisser Kontur rechts."""
    b = Image.new("RGBA", (1000, 250), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle([8, 8, 992, 242], 36, fill=(8, 8, 12, 255), outline=(255, 255, 255, 255), width=7)
    badge = loco_badge(206)
    b.alpha_composite(badge, (28, 22))
    gold_top, gold_bot = (255, 240, 190), (196, 140, 40)
    t1 = fancy_text("POLARIS", 122, "black", gold_top, gold_bot, ow=7, sh=(0, 8))
    t2 = fancy_text("EXPRESS", 72, "black", (240, 244, 250), (150, 170, 200), ow=6, sh=(0, 6))
    x = 258 + (720 - t1.width) // 2
    b.alpha_composite(t1, (x, 22))
    b.alpha_composite(t2, (258 + (720 - t2.width) // 2, 148))
    rnd = random.Random(4)
    for _ in range(14):
        sx, sy = rnd.uniform(270, 970), rnd.uniform(26, 225)
        r = rnd.uniform(2, 4)
        d = ImageDraw.Draw(b)
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, rnd.randint(120, 220)))
    return b


def icon():
    """Lobby-Symbol 256 x 256: Lokfront im Schnee (ohne Kreis, wie icon_park.png)."""
    ss = 4
    N = 256 * ss
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ink = (14, 16, 20, 255)
    ow = 5 * ss
    cx, cy, lr = N * 0.52, N * 0.56, N * 0.2
    rnd = random.Random(2)
    # Mond und Schneehuegel hinter der Lok
    d.ellipse([N * 0.14, N * 0.1, N * 0.34, N * 0.3], fill=(250, 244, 210, 255), outline=ink, width=ow)
    d.ellipse([N * 0.2, N * 0.07, N * 0.38, N * 0.25], fill=(0, 0, 0, 0))
    moon_mask = Image.new("L", (N, N), 0)
    md = ImageDraw.Draw(moon_mask)
    md.ellipse([N * 0.14, N * 0.1, N * 0.34, N * 0.3], fill=255)
    md.ellipse([N * 0.205, N * 0.065, N * 0.385, N * 0.245], fill=0)
    moon = Image.new("RGBA", (N, N), (250, 244, 210, 255))
    base = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    base.paste(moon, (0, 0), moon_mask)
    im = base
    d = ImageDraw.Draw(im)
    d.ellipse([N * 0.0, N * 0.62, N * 0.7, N * 1.2], fill=(206, 216, 236, 255), outline=ink, width=ow)
    d.ellipse([N * 0.4, N * 0.66, N * 1.1, N * 1.25], fill=(222, 230, 244, 255), outline=ink, width=ow)
    for tx, th in ((N * 0.12, N * 0.3), (N * 0.9, N * 0.26)):
        ty = N * 0.75
        for k in range(3):
            w_ = th * (0.5 - k * 0.11)
            yk = ty - th * 0.28 * k
            d.polygon([(tx - w_, yk), (tx + w_, yk), (tx, yk - th * 0.5)], fill=(34, 70, 54, 255), outline=ink, width=ow)
            d.polygon([(tx - w_ * 0.5, yk - th * 0.16), (tx + w_ * 0.5, yk - th * 0.16), (tx, yk - th * 0.45)], fill=(214, 226, 242, 255))
    # Lok
    d.polygon([(cx - lr * 1.35, cy + lr * 1.05), (cx + lr * 1.35, cy + lr * 1.05), (cx + lr * 0.6, cy + lr * 1.55), (cx - lr * 0.6, cy + lr * 1.55)],
              fill=(60, 62, 72, 255), outline=ink, width=ow)
    for k in range(4):
        x = cx - lr * 1.0 + k * lr * 0.66
        d.line([(x, cy + lr * 1.08), (x + lr * 0.25, cy + lr * 1.5)], fill=(176, 46, 42, 255), width=3 * ss)
    d.rectangle([cx - lr * 1.3, cy + lr * 0.75, cx + lr * 1.3, cy + lr * 1.05], fill=(176, 46, 42, 255), outline=ink, width=ow)
    for sx in (-1, 1):
        d.ellipse([cx + sx * lr * 1.05 - lr * 0.15, cy + lr * 0.76, cx + sx * lr * 1.05 + lr * 0.15, cy + lr * 1.04], fill=(130, 134, 146, 255), outline=ink, width=ow)
    d.rectangle([cx - lr * 0.3, cy - lr * 1.9, cx + lr * 0.3, cy - lr * 0.8], fill=(44, 46, 54, 255), outline=ink, width=ow)
    d.rectangle([cx - lr * 0.4, cy - lr * 2.02, cx + lr * 0.4, cy - lr * 1.78], fill=(222, 182, 92, 255), outline=ink, width=ow)
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill=(50, 52, 60, 255), outline=ink, width=ow)
    d.ellipse([cx - lr * 0.78, cy - lr * 0.78, cx + lr * 0.78, cy + lr * 0.78], fill=(38, 40, 48, 255), outline=(222, 182, 92, 255), width=ow)
    d.ellipse([cx - lr * 0.14, cy - lr * 0.14, cx + lr * 0.14, cy + lr * 0.14], fill=(222, 182, 92, 255), outline=ink, width=3 * ss)
    d.line([(cx - lr * 0.5, cy), (cx + lr * 0.5, cy)], fill=(222, 182, 92, 255), width=3 * ss)
    plate = [cx - lr * 0.34, cy + lr * 0.32, cx + lr * 0.34, cy + lr * 0.56]
    d.rectangle(plate, fill=(222, 182, 92, 255), outline=ink, width=3 * ss)
    d.text(((plate[0] + plate[2]) / 2, (plate[1] + plate[3]) / 2), "4", font=font(int(lr * 0.26), "serif"), fill=ink, anchor="mm")
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - lr * 0.9, cy - lr * 1.7, cx + lr * 0.9, cy - lr * 0.1], fill=(255, 220, 140, 170))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16 * ss)))
    d = ImageDraw.Draw(im)
    d.ellipse([cx - lr * 0.26, cy - lr * 1.12, cx + lr * 0.26, cy - lr * 0.6], fill=(255, 240, 190, 255), outline=ink, width=ow)
    d.ellipse([cx - lr * 0.12, cy - lr * 1.02, cx + lr * 0.1, cy - lr * 0.8], fill=(255, 255, 250, 255))
    for px, py, pr in ((cx + lr * 0.1, cy - lr * 2.3, lr * 0.3), (cx + lr * 0.55, cy - lr * 2.55, lr * 0.38), (cx + lr * 1.15, cy - lr * 2.6, lr * 0.3)):
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(236, 240, 248, 240), outline=ink, width=ow)
        d.ellipse([px - pr * 0.5, py - pr * 0.6, px + pr * 0.1, py - pr * 0.05], fill=(255, 255, 255, 255))
    d.rounded_rectangle([cx - lr * 0.95, cy - lr * 1.02, cx + lr * 0.95, cy - lr * 0.82], radius=6 * ss, fill=(226, 234, 246, 255), outline=ink, width=3 * ss)
    for _ in range(14):
        x, y = rnd.uniform(N * 0.05, N * 0.95), rnd.uniform(N * 0.05, N * 0.95)
        r = rnd.uniform(3, 6) * ss
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 210), outline=(200, 210, 230, 255), width=ss)
    return im.resize((256, 256), Image.LANCZOS)


# ------------------------------------------------------------------ Minispiel-Grafik

def task_panel():
    """Tafel 720 x 520 (100 px/m): Mahagoni-Vertaefelung mit Messingbeschlaegen, Lampenschein oben links."""
    from gen_tasks import C, S as SS, INK, frame_wood, mix
    WOOD, WOOD_L, WOOD_D = (150, 86, 50, 255), (184, 114, 70, 255), (108, 60, 34, 255)
    BRASS, BRASS_L, BRASS_D = (214, 176, 92, 255), (240, 214, 140, 255), (150, 112, 50, 255)
    c = C(720, 520)
    frame_wood(c, (64, 36, 24, 255))
    c.rrect(26, 26, 694, 494, 10, WOOD_D, lw=4)
    m, md = c.mask()
    md.rectangle([30 * SS, 30 * SS, 690 * SS, 490 * SS], fill=255)
    c.grain(30, 30, 690, 490, 0.08, seed=7, freq=0.35, mask=m)
    # Fuellungen: fuenf Felder mit erhabenem Rahmen, Lambris unten
    for i, x in enumerate(range(44, 660, 128)):
        x1 = min(x + 116, 676)
        c.rrect(x, 44, x1, 356, 6, WOOD, lw=4, sh=(0.1, 0.18))
        c.line([(x + 4, 48), (x1 - 4, 48)], (210, 150, 100, 110), 3)
        c.rrect(x + 14, 58, x1 - 14, 342, 4, mix(WOOD, WOOD_L, 0.25), lw=3, sh=(0.08, 0.2))
        m2, md2 = c.mask()
        md2.rounded_rectangle([(x + 14) * SS, 58 * SS, (x1 - 14) * SS, 342 * SS], 4 * SS, fill=255)
        c.grain(x + 14, 58, x1 - 14, 342, 0.1, seed=20 + i, freq=0.45, mask=m2)
        c.line([(x + 18, 62), (x1 - 18, 62)], (220, 170, 120, 90), 2)
    c.rrect(36, 366, 684, 380, 3, BRASS, lw=3, sh=(0.3, 0.3))                   # Messingleiste (Lambris-Kante)
    for i, x in enumerate(range(44, 660, 128)):
        x1 = min(x + 116, 676)
        c.rrect(x, 390, x1, 476, 5, WOOD_D, lw=4, sh=(0.1, 0.2))
        c.rrect(x + 12, 400, x1 - 12, 466, 3, mix(WOOD_D, WOOD, 0.4), lw=3, sh=(0.08, 0.2))
        m3, md3 = c.mask()
        md3.rectangle([(x + 12) * SS, 400 * SS, (x1 - 12) * SS, 466 * SS], fill=255)
        c.grain(x + 12, 400, x1 - 12, 466, 0.08, seed=40 + i, freq=0.5, mask=m3)
    c.rrect(36, 478, 684, 490, 3, (70, 40, 26, 255), lw=3)
    # Messingbeschlaege in den Ecken
    for x, sx in ((30, 1), (690, -1)):
        for y, sy in ((30, 1), (490, -1)):
            c.poly([(x, y), (x + sx * 64, y), (x + sx * 64, y + sy * 14), (x + sx * 14, y + sy * 14), (x + sx * 14, y + sy * 64), (x, y + sy * 64)],
                   BRASS, lw=4, sh=(0.25, 0.3))
            c.screw(x + sx * 44, y + sy * 7, 5, BRASS_L, rot=30)
            c.screw(x + sx * 7, y + sy * 44, 5, BRASS_L, rot=70)
    c.vignette(0.3, 28, 28, 692, 492)
    c.glow(160, 80, 300, 220, (255, 200, 120, 40), 40)
    return c.img.resize((720, 520), Image.LANCZOS)


def ticket_button():
    """Fahrschein 256 x 256 fuer Kartenknopf und Use-Knopf: Vanilla-Look (dicke Kontur), cremefarbenes Papier mit
    rotem Streifen POLARIS EXPRESS, Perforation, Lochung."""
    ss = 4
    N = 256 * ss
    ink = (29, 27, 33, 255)
    tw, th = 176 * ss, 108 * ss
    layer = Image.new("RGBA", (tw + 60 * ss, th + 60 * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = 30 * ss, 30 * ss
    body = [(ox, oy), (ox + tw - 14 * ss, oy)]
    k = 0
    y = oy
    while y < oy + th:                                                     # Zacken rechts
        body.append((ox + tw - (14 if k % 2 == 0 else 6) * ss, y))
        y += 9 * ss
        k += 1
    body += [(ox + tw - 14 * ss, oy + th), (ox, oy + th)]
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 6 * ss, y + 8 * ss) for x, y in body], fill=(0, 0, 0, 90))
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4 * ss)))
    d = ImageDraw.Draw(layer)
    d.polygon(body, fill=(240, 220, 162, 255))
    d.line(body + [body[0]], fill=ink, width=9 * ss, joint="curve")
    d.rectangle([ox + 10 * ss, oy + 10 * ss, ox + tw - 26 * ss, oy + th - 10 * ss], outline=(196, 160, 90, 255), width=2 * ss)
    d.rectangle([ox + 12 * ss, oy + 18 * ss, ox + tw - 28 * ss, oy + 40 * ss], fill=(176, 56, 48, 255))
    d.text(((ox + 12 * ss + ox + tw - 28 * ss) / 2, oy + 29 * ss), "POLARIS EXPRESS", font=font(15 * ss, "black"), fill=(255, 236, 200, 255), anchor="mm")
    f = font(9 * ss, "serif")
    d.text((ox + 16 * ss, oy + 50 * ss), "VALID FOR ONE JOURNEY", font=f, fill=(110, 86, 50, 255), anchor="lm")
    d.text((ox + 16 * ss, oy + 64 * ss), "No. 0417     1st CLASS", font=f, fill=(110, 86, 50, 255), anchor="lm")
    for i in range(2):
        yy = oy + 80 * ss + i * 10 * ss
        d.line([(ox + 16 * ss, yy), (ox + 96 * ss, yy)], fill=(150, 124, 80, 255), width=2 * ss)
    hx, hy, hr = ox + 136 * ss, oy + 78 * ss, 13 * ss
    d.ellipse([hx - hr - 4 * ss, hy - hr - 4 * ss, hx + hr + 4 * ss, hy + hr + 4 * ss], fill=(224, 200, 140, 255))
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(0, 0, 0, 0), outline=ink, width=6 * ss)
    pts = [(hx + (hr * 0.75 if j % 2 == 0 else hr * 0.3) * math.cos(math.radians(-90 + j * 36)),
            hy + (hr * 0.75 if j % 2 == 0 else hr * 0.3) * math.sin(math.radians(-90 + j * 36))) for j in range(10)]
    d.polygon(pts, fill=ink)
    d.ellipse([ox + 150 * ss, oy + 44 * ss, ox + 162 * ss, oy + 56 * ss], outline=(176, 56, 48, 255), width=2 * ss)
    layer = layer.rotate(12, resample=Image.BICUBIC, expand=True)
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.alpha_composite(layer, ((N - layer.width) // 2, (N - layer.height) // 2))
    return out.resize((256, 256), Image.LANCZOS)


def files(ctx):
    return {"button_train.png": button(), "icon_train.png": icon(), "task_train_panel.png": task_panel(),
            "task_ticket_button.png": ticket_button()}
