"""Erzeugt den Map-Auswahl-Button "the MUSEUM" im Stil der Vanilla-Logo-Buttons.

Ausgabe: assets/button_museum.png (1000 x 250, RGBA, transparent ausserhalb der Pille).
Gezeichnet wird vektorartig mit PIL bei 4-fachem Supersampling, danach herunterskaliert.
Aufruf: python tools/gen_buttons.py [--preview PFAD]
Mit --preview entsteht zusaetzlich ein Vergleichsbild (Vergleich mit Vanilla-Screenshot).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
FONTS = r"C:\Windows\Fonts"

W, H = 1000, 250       # Zielgroesse
SS = 4                 # Supersampling-Faktor
BORDER = 14            # weisser Rand in Zielpixeln
RADIUS = 40            # Eckenradius in Zielpixeln

# Farben (Gold/Messing-Schema fuer das Museum)
GOLD_TOP = (255, 236, 150)
GOLD_MID = (247, 196, 64)
GOLD_BOT = (196, 120, 20)
OUTLINE_DARK = (70, 36, 8)
WHITE = (255, 255, 255)
NIGHT = (24, 30, 70)
NIGHT_LIGHT = (48, 62, 130)
STONE = (222, 204, 160)
STONE_DARK = (176, 150, 100)
WINDOW = (255, 214, 90)

# Farben (Waldgruen-Schema fuer die Forststation)
FOREST_TOP = (214, 244, 150)
FOREST_MID = (96, 178, 74)
FOREST_BOT = (28, 98, 46)
FOREST_OUTLINE = (16, 44, 26)
PINE = (44, 110, 62)
PINE_DARK = (30, 80, 46)
PINE_LIGHT = (86, 150, 88)
TRUNK = (96, 62, 34)
LOG = (150, 100, 56)
LOG_DARK = (110, 72, 40)
ROOF = (86, 54, 34)
GROUND = (52, 92, 52)
GROUND_DARK = (36, 68, 40)


def s(v):
    """Skaliert einen Zielpixelwert auf Supersampling-Koordinaten."""
    return int(round(v * SS))


def gradient_v(size, stops):
    """Vertikaler Farbverlauf als RGBA-Bild. stops = [(pos 0..1, (r,g,b)), ...]."""
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        # passendes Segment suchen
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                u = (t - p0) / max(1e-6, p1 - p0)
                col = tuple(int(c0[k] + (c1[k] - c0[k]) * u) for k in range(3))
                break
        else:
            col = stops[-1][1]
        for x in range(w):
            px[x, y] = col + (255,)
    return img


def dilate(mask, radius):
    """Weitet eine L-Maske um radius Pixel (MaxFilter, ungerade Kernelgroesse)."""
    if radius <= 0:
        return mask
    k = 2 * int(radius) + 1
    return mask.filter(ImageFilter.MaxFilter(k))


def outlined_layer(shape_rgba, dark_w, white_w, dark_col=OUTLINE_DARK):
    """Legt um eine RGBA-Form eine dunkle und darum eine weisse Kontur (Among-Us-Logo-Look)."""
    alpha = shape_rgba.split()[3]
    dark = dilate(alpha, dark_w)
    white = dilate(dark, white_w)
    out = Image.new("RGBA", shape_rgba.size, (0, 0, 0, 0))
    out.paste(Image.new("RGBA", shape_rgba.size, WHITE + (255,)), (0, 0), white)
    out.paste(Image.new("RGBA", shape_rgba.size, dark_col + (255,)), (0, 0), dark)
    out.alpha_composite(shape_rgba)
    return out


def rounded(mask, radius):
    """Rundet Ecken einer L-Maske ab (Weichzeichnen + Schwellwert), wirkt wie Comic-Lettering."""
    if radius <= 0:
        return mask
    return mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: 255 if v >= 128 else 0)


def text_mask(size, font, text, xy, round_r=0):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).text(xy, text, font=font, fill=255)
    return rounded(m, round_r)


def draw_pill(size):
    """Schwarze Pille mit weissem Rand, transparent aussen."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=s(RADIUS), fill=WHITE + (255,))
    b = s(BORDER)
    d.rounded_rectangle((b, b, size[0] - 1 - b, size[1] - 1 - b), radius=s(RADIUS - BORDER * 0.6),
                        fill=(0, 0, 0, 255))
    return img


def draw_museum_icon(box):
    """Museumsfassade bei Nacht: dunkle Scheibe, Mond, Giebel, Saeulen, warm leuchtende Tuer.

    box = Zielgroesse (Breite, Hoehe) in Zielpixeln; Rueckgabe RGBA in SS-Aufloesung.
    """
    w, h = s(box[0]), s(box[1])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Nachthimmel als runde Scheibe (organischer als ein Kasten, passt zu Polus-Mond und Mira-Wolke)
    grad = gradient_v((w, h), [(0.0, NIGHT), (0.55, NIGHT), (1.0, NIGHT_LIGHT)])
    sky_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sky_mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    img.paste(grad, (0, 0), sky_mask)
    d = ImageDraw.Draw(img)

    # Sterne
    for (fx, fy, r) in [(0.22, 0.20, 0.018), (0.36, 0.12, 0.012), (0.14, 0.40, 0.012),
                        (0.86, 0.46, 0.013), (0.56, 0.14, 0.012)]:
        cx, cy, rr = fx * w, fy * h, r * w
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 250, 220, 255))

    # Mond (Sichel) oben rechts
    mx, my, mr = 0.72 * w, 0.24 * h, 0.12 * w
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=(255, 238, 170, 255))
    ox, oy = mx - 0.45 * mr, my - 0.25 * mr
    cut = Image.new("L", (w, h), 0)
    ImageDraw.Draw(cut).ellipse((ox - mr * 0.92, oy - mr * 0.92, ox + mr * 0.92, oy + mr * 0.92), fill=255)
    img.paste(grad, (0, 0), cut)
    d = ImageDraw.Draw(img)
    # Sterne, die vom Mondausschnitt verdeckt sein koennten, nochmal setzen
    for (fx, fy, r) in [(0.56, 0.14, 0.012)]:
        cx, cy, rr = fx * w, fy * h, r * w
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 250, 220, 255))

    # Fassade: Masse in Bruchteilen
    base_y = 0.86 * h
    step_h = 0.05 * h
    left, right = 0.20 * w, 0.80 * w
    ent_top = 0.44 * h          # Oberkante Gebaelk
    ent_h = 0.07 * h
    apex_y = 0.24 * h           # Giebelspitze
    line = max(2, int(0.016 * w))

    # Stufen (zwei Stufen)
    d.rectangle((left - 0.04 * w, base_y - step_h, right + 0.04 * w, base_y), fill=STONE_DARK + (255,),
                outline=OUTLINE_DARK + (255,), width=line)
    d.rectangle((left - 0.02 * w, base_y - 2 * step_h, right + 0.02 * w, base_y - step_h),
                fill=STONE + (255,), outline=OUTLINE_DARK + (255,), width=line)

    # Rueckwand hinter den Saeulen (dunkler Stein) mit leuchtender Tuer
    d.rectangle((left + 0.02 * w, ent_top + ent_h, right - 0.02 * w, base_y - 2 * step_h),
                fill=(92, 74, 48, 255))
    door_w = 0.16 * w
    dcx = (left + right) / 2
    d.rectangle((dcx - door_w / 2, ent_top + ent_h + 0.06 * h, dcx + door_w / 2, base_y - 2 * step_h),
                fill=WINDOW + (255,))
    # Schimmer auf den Stufen vor der Tuer
    d.polygon([(dcx - door_w / 2, base_y - 2 * step_h), (dcx + door_w / 2, base_y - 2 * step_h),
               (dcx + door_w * 0.85, base_y), (dcx - door_w * 0.85, base_y)], fill=(230, 190, 90, 110))

    # Saeulen (vier Stueck)
    n = 4
    col_w = 0.075 * w
    span = (right - left) - col_w
    for i in range(n):
        cx = left + col_w / 2 + span * i / (n - 1)
        top = ent_top + ent_h
        bot = base_y - 2 * step_h
        d.rectangle((cx - col_w / 2, top, cx + col_w / 2, bot), fill=STONE + (255,),
                    outline=OUTLINE_DARK + (255,), width=line)
        # Kapitell und Basis
        d.rectangle((cx - col_w * 0.7, top, cx + col_w * 0.7, top + 0.035 * h), fill=STONE + (255,),
                    outline=OUTLINE_DARK + (255,), width=line)
        d.rectangle((cx - col_w * 0.7, bot - 0.03 * h, cx + col_w * 0.7, bot), fill=STONE + (255,),
                    outline=OUTLINE_DARK + (255,), width=line)
        # Schattenkante rechts an der Saeule
        d.rectangle((cx + col_w * 0.15, top + 0.035 * h, cx + col_w / 2 - line, bot - 0.03 * h),
                    fill=STONE_DARK + (255,))

    # Gebaelk
    d.rectangle((left - 0.02 * w, ent_top, right + 0.02 * w, ent_top + ent_h), fill=STONE + (255,),
                outline=OUTLINE_DARK + (255,), width=line)
    # Giebel
    d.polygon([(left - 0.05 * w, ent_top), (right + 0.05 * w, ent_top), ((left + right) / 2, apex_y)],
              fill=STONE + (255,), outline=OUTLINE_DARK + (255,), width=line)
    # Giebelfeld (dunkler, mit kleinem goldenen Kreis als Emblem)
    inset = 0.045 * w
    d.polygon([(left + inset, ent_top - line), (right - inset, ent_top - line),
               ((left + right) / 2, apex_y + 0.075 * h)], fill=STONE_DARK + (255,))
    er = 0.035 * w
    ecx, ecy = (left + right) / 2, ent_top - 0.055 * h
    d.ellipse((ecx - er, ecy - er, ecx + er, ecy + er), fill=GOLD_MID + (255,),
              outline=OUTLINE_DARK + (255,), width=line)

    return img


def draw_wald_icon(box):
    """Forststation bei Nacht: Nachthimmel-Scheibe, Mond, Kiefern, Blockhuette mit Licht, Hochsitz.

    box = Zielgroesse (Breite, Hoehe) in Zielpixeln; Rueckgabe RGBA in SS-Aufloesung.
    """
    w, h = s(box[0]), s(box[1])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    line = max(2, int(0.016 * w))
    ol = FOREST_OUTLINE + (255,)

    # Nachthimmel als Scheibe (wie beim Museum), unten etwas heller
    grad = gradient_v((w, h), [(0.0, NIGHT), (0.5, NIGHT), (1.0, NIGHT_LIGHT)])
    sky_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sky_mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    img.paste(grad, (0, 0), sky_mask)
    d = ImageDraw.Draw(img)

    # Sterne + Vollmond oben rechts (ein paar Krater)
    for (fx, fy, r) in [(0.18, 0.22, 0.016), (0.32, 0.12, 0.011), (0.12, 0.42, 0.011),
                        (0.5, 0.16, 0.011), (0.88, 0.5, 0.012), (0.62, 0.3, 0.009)]:
        cx, cy, rr = fx * w, fy * h, r * w
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 250, 220, 255))
    mx, my, mr = 0.74 * w, 0.25 * h, 0.11 * w
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=(255, 238, 170, 255))
    for (ox, oy, orr) in [(-0.3, -0.2, 0.22), (0.35, 0.1, 0.16), (-0.05, 0.45, 0.13)]:
        cx, cy, rr = mx + ox * mr, my + oy * mr, orr * mr
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(236, 214, 140, 255))

    # Boden: Huegel im unteren Drittel der Scheibe (auf die Scheibe beschnitten)
    ground = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(ground)
    gd.ellipse((-0.2 * w, 0.68 * h, 1.2 * w, 1.5 * h), fill=GROUND + (255,))
    gd.ellipse((-0.2 * w, 0.68 * h, 1.2 * w, 1.5 * h), outline=ol, width=line)
    gd.ellipse((0.05 * w, 0.8 * h, 0.7 * w, 1.3 * h), fill=GROUND_DARK + (255,))
    ground.putalpha(Image.composite(ground.split()[3], Image.new("L", (w, h), 0), sky_mask))
    img.alpha_composite(ground)
    d = ImageDraw.Draw(img)

    def pine(cx, base_y, height, width):
        """Kiefer aus drei gestaffelten Dreiecken mit Lichtkante links."""
        d.rectangle((cx - width * 0.08, base_y - height * 0.2, cx + width * 0.08, base_y), fill=TRUNK + (255,),
                    outline=ol, width=line)
        tiers = [(0.0, 1.0), (0.3, 0.8), (0.55, 0.58)]
        for k, (lift, wid) in enumerate(tiers):
            y0 = base_y - height * 0.12 - lift * height
            y1 = y0 - height * (0.45 if k < 2 else 0.4)
            hw = width * wid / 2
            col = PINE if k % 2 == 0 else PINE_DARK
            d.polygon([(cx - hw, y0), (cx + hw, y0), (cx, y1)], fill=col + (255,), outline=ol, width=line)
            d.polygon([(cx - hw * 0.75, y0 - line), (cx - hw * 0.1, y0 - line), (cx - hw * 0.05, y1 + (y0 - y1) * 0.35)],
                      fill=PINE_LIGHT + (255,))

    # Hochsitz rechts hinter den Baeumen: zwei Stelzen, Kanzel, Pultdach
    hx, hb = 0.8 * w, 0.84 * h
    for lx in (hx - 0.06 * w, hx + 0.06 * w):
        d.rectangle((lx - 0.012 * w, hb - 0.34 * h, lx + 0.012 * w, hb), fill=TRUNK + (255,), outline=ol, width=line)
    d.line([(hx - 0.06 * w, hb - 0.04 * h), (hx + 0.06 * w, hb - 0.2 * h)], fill=TRUNK + (255,), width=line * 2)
    d.rectangle((hx - 0.1 * w, hb - 0.5 * h, hx + 0.1 * w, hb - 0.32 * h), fill=LOG + (255,), outline=ol, width=line)
    d.rectangle((hx - 0.065 * w, hb - 0.47 * h, hx + 0.065 * w, hb - 0.4 * h), fill=(30, 34, 46, 255))
    d.polygon([(hx - 0.13 * w, hb - 0.5 * h), (hx + 0.13 * w, hb - 0.5 * h), (hx, hb - 0.64 * h)],
              fill=ROOF + (255,), outline=ol, width=line)

    # Kiefern hinten (klein) und vorne links (gross)
    pine(0.3 * w, 0.82 * h, 0.5 * h, 0.22 * w)
    pine(0.13 * w, 0.9 * h, 0.66 * h, 0.3 * w)

    # Blockhuette in der Mitte vorne: Balkenfront, Satteldach, leuchtendes Fenster + Tuer
    cx, cb = 0.53 * w, 0.93 * h
    hw, hh = 0.2 * w, 0.24 * h
    d.rectangle((cx - hw, cb - hh, cx + hw, cb), fill=LOG + (255,), outline=ol, width=line)
    for k in range(4):
        yy = cb - hh + (k + 1) * hh / 5
        d.line([(cx - hw + line, yy), (cx + hw - line, yy)], fill=LOG_DARK + (255,), width=max(1, line // 2))
    d.polygon([(cx - hw - 0.04 * w, cb - hh), (cx + hw + 0.04 * w, cb - hh), (cx, cb - hh - 0.19 * h)],
              fill=ROOF + (255,), outline=ol, width=line)
    d.polygon([(cx - hw - 0.04 * w, cb - hh), (cx + hw + 0.04 * w, cb - hh), (cx, cb - hh - 0.19 * h)],
              outline=ol, width=line)
    d.line([(cx - hw + 0.01 * w, cb - hh - 0.01 * h), (cx - 0.01 * w, cb - hh - 0.165 * h)],
           fill=(120, 80, 50, 255), width=line)
    # Schornstein mit Rauch
    d.rectangle((cx + 0.09 * w, cb - hh - 0.16 * h, cx + 0.14 * w, cb - hh - 0.05 * h), fill=(110, 110, 118, 255),
                outline=ol, width=line)
    for k, (dx, dy, r) in enumerate([(0.0, 0.22, 0.02), (0.03, 0.27, 0.025), (0.07, 0.31, 0.03)]):
        cxs, cys, rr = cx + 0.115 * w + dx * w, cb - hh - dy * h, r * w
        d.ellipse((cxs - rr, cys - rr, cxs + rr, cys + rr), fill=(200, 200, 210, 150))
    # Fenster (leuchtend, Sprossenkreuz) und Tuer
    wx0, wy0, wx1, wy1 = cx - 0.13 * w, cb - hh * 0.78, cx - 0.03 * w, cb - hh * 0.4
    d.rectangle((wx0, wy0, wx1, wy1), fill=WINDOW + (255,), outline=ol, width=line)
    d.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], fill=ol, width=max(1, line // 2))
    d.line([(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)], fill=ol, width=max(1, line // 2))
    d.rectangle((cx + 0.04 * w, cb - hh * 0.72, cx + 0.13 * w, cb), fill=LOG_DARK + (255,), outline=ol, width=line)
    d.ellipse((cx + 0.105 * w, cb - hh * 0.4, cx + 0.12 * w, cb - hh * 0.34), fill=WINDOW + (255,))
    # warmer Schein vor dem Fenster
    d.polygon([(wx0, wy1), (wx1, wy1), (wx1 + 0.03 * w, cb + 0.02 * h), (wx0 - 0.05 * w, cb + 0.02 * h)],
              fill=(230, 190, 90, 70))

    return img


def render_button(big_text, icon_fn, stops, the_col, hi_col=(255, 250, 220), dark_col=OUTLINE_DARK):
    """Pille + Icon links + Schriftzug "the BIG_TEXT" mit Verlauf und doppelter Kontur.

    stops = Verlaufsstuetzen fuer die grossen Buchstaben, the_col = Farbe von "the",
    hi_col = Glanzstreifen oben in den Buchstaben, dark_col = dunkle Kontur (Icon und Schrift).
    """
    size = (s(W), s(H))
    img = draw_pill(size)

    # Icon links
    icon_box = 184
    icon = icon_fn((icon_box, icon_box))
    # Rand-Padding, damit die Konturen an der Leinwandkante nicht abgeschnitten werden
    pad = s(12)
    padded = Image.new("RGBA", (icon.size[0] + 2 * pad, icon.size[1] + 2 * pad), (0, 0, 0, 0))
    padded.alpha_composite(icon, (pad, pad))
    icon = outlined_layer(padded, dark_w=s(3), white_w=s(6), dark_col=dark_col)
    ix = s(30) - pad
    iy = (size[1] - icon.size[1]) // 2
    img.alpha_composite(icon, (ix, iy))

    # Schrift: "the" in Schreibschrift, grosser Name in Impact mit Verlauf
    gap = s(4)
    text_left = ix + icon.size[0] + s(18)
    text_right = size[0] - s(BORDER) - s(22)
    max_h = size[1] - 2 * s(BORDER) - 2 * s(15)   # Platz fuer Konturen oben/unten lassen

    # Schriftgroesse schrittweise verkleinern, bis der Textblock in Breite und Hoehe passt
    big_pt = 200
    while True:
        big_font = ImageFont.truetype(os.path.join(FONTS, "impact.ttf"), s(big_pt))
        the_font = ImageFont.truetype(os.path.join(FONTS, "segoescb.ttf"), s(int(big_pt * 0.36)))
        bb = big_font.getbbox(big_text)
        big_w, big_h = bb[2] - bb[0], bb[3] - bb[1]
        tb = the_font.getbbox("the")
        the_w, the_h = tb[2] - tb[0], tb[3] - tb[1]
        block_w = the_w + gap + big_w
        if (block_w <= text_right - text_left and big_h <= max_h) or big_pt <= 60:
            break
        big_pt -= 2

    # Textblock im verbleibenden Raum zentrieren
    start_x = text_left + (text_right - text_left - block_w) // 2

    # "MUSEUM" Maske, vertikal zentriert
    big_x = start_x + the_w + gap - bb[0]
    big_y = (size[1] - big_h) // 2 - bb[1]
    m_big = text_mask(size, big_font, big_text, (big_x, big_y), round_r=s(3))

    # "the" Maske: Unterkante auf die Grundlinie von MUSEUM, leicht schraeg wirkt es durch die Schrift
    the_x = start_x - tb[0]
    the_y = big_y + bb[3] - tb[3] - s(4)
    m_the = text_mask(size, the_font, "the", (the_x, the_y))

    # Verlauf nur ueber den Bereich der grossen Buchstaben
    top = big_y + bb[1]
    grad_full = gradient_v((size[0], big_h), stops)
    grad_img = Image.new("RGBA", size, (0, 0, 0, 0))
    grad_img.paste(grad_full, (0, top))

    letters = Image.new("RGBA", size, (0, 0, 0, 0))
    letters.paste(grad_img, (0, 0), m_big)
    # Glanzstreifen: die Maske nach oben verschoben und mit sich selbst geschnitten -> heller Rand oben
    shift = s(9)
    shifted = Image.new("L", size, 0)
    shifted.paste(m_big, (0, shift))
    inner = Image.eval(shifted, lambda v: 255 - v)
    highlight = Image.new("L", size, 0)
    highlight.paste(m_big, (0, 0), inner)
    # nur in der oberen Haelfte der Buchstaben
    hl_clip = Image.new("L", size, 0)
    ImageDraw.Draw(hl_clip).rectangle((0, top, size[0], top + big_h * 0.55), fill=255)
    highlight = Image.composite(highlight, Image.new("L", size, 0), hl_clip)
    letters.paste(Image.new("RGBA", size, hi_col + (255,)), (0, 0), highlight)

    # "the" in der Mittelfarbe des Verlaufs
    letters.paste(Image.new("RGBA", size, the_col + (255,)), (0, 0), m_the)

    letters = outlined_layer(letters, dark_w=s(4), white_w=s(6), dark_col=dark_col)
    img.alpha_composite(letters)

    return img.resize((W, H), Image.LANCZOS)


def render_museum():
    """"the MUSEUM": Gold/Messing, Fassaden-Icon (Ausgabe unveraendert gegenueber der ersten Fassung)."""
    return render_button("MUSEUM", draw_museum_icon,
                         [(0.0, GOLD_TOP), (0.30, GOLD_MID), (0.72, GOLD_MID), (1.0, GOLD_BOT)], GOLD_MID)


def render_wald():
    """"the FOREST": Waldgruen, Icon mit Kiefern, Blockhuette und Hochsitz unter Nachthimmel."""
    return render_button("FOREST", draw_wald_icon,
                         [(0.0, FOREST_TOP), (0.30, FOREST_MID), (0.72, FOREST_MID), (1.0, FOREST_BOT)],
                         FOREST_MID, hi_col=(226, 250, 190), dark_col=FOREST_OUTLINE)


def make_preview(button_paths, out_path):
    """Vergleichsbild: Vanilla-Buttons aus dem Screenshot neben den neuen Buttons (Museum, Wald)."""
    shot = r"C:\Users\moritz\Downloads\Among Us - 4.7.0\Among Us - 4.7.0\AtlasShots\ui_20260922_235515.png"
    if not os.path.exists(shot):
        print("Screenshot fehlt, kein Preview")
        return
    van = Image.open(shot).convert("RGBA").crop((1220, 600, 2300, 1080))
    btns = [Image.open(p).convert("RGBA") for p in button_paths]
    canvas = Image.new("RGBA", (van.size[0], van.size[1] + 160 + 220 * len(btns)), (40, 60, 90, 255))
    canvas.paste(van, (0, 0))
    bg = Image.open(shot).convert("RGBA").crop((1220, 600, 1710, 723))
    y = van.size[1] + 20
    for btn in btns:
        # Auf Vanilla-Groesse (ca. 490 px breit) skalieren und auf gleiche Art Hintergrund darunter legen
        small = btn.resize((490, 123), Image.LANCZOS)
        canvas.paste(bg, (20, y))
        canvas.alpha_composite(small, (20, y))
        # Screen-Groesse bei 1440p: ca. 310 x 80
        tiny = btn.resize((310, 78), Image.LANCZOS)
        canvas.alpha_composite(tiny, (560, y + 20))
        y += 150
    # groesste Ansicht des letzten Buttons
    big = btns[-1].resize((700, 175), Image.LANCZOS)
    canvas.alpha_composite(big, (190, y + 20))
    canvas.save(out_path)
    print("Preview:", out_path)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    outs = []
    for name, fn in (("button_museum.png", render_museum), ("button_wald.png", render_wald)):
        out = os.path.join(ASSETS, name)
        fn().save(out)
        print("Geschrieben:", out)
        outs.append(out)
    if "--preview" in sys.argv:
        i = sys.argv.index("--preview")
        target = sys.argv[i + 1] if len(sys.argv) > i + 1 else os.path.join(HERE, "_button_preview.png")
        make_preview(outs, target)


if __name__ == "__main__":
    main()
