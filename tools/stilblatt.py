# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# stilblatt.py - Abnahme-Bilder des Stilblatts "Among Us, leicht handgezeichnet" (2026-10-01).
# Rendert je Musterstueck einen Ausschnitt (ca. 12 x 7 m) in Spielaufloesung aus den ERZEUGTEN Assets,
# mit Spielerfigur-Silhouette als Massstab, nach tools/_stilblatt/<name>_<vorher|nachher>.png.
#   python tools/stilblatt.py vorher      (vor dem Umbau, mit den alten Generatoren)
#   python tools/stilblatt.py nachher     (nach gen_park / gen_museum / gen_wald)
# Vorher die Generatoren laufen lassen; die Vorschau liest assets/ und src/*Layout.cs.

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import handdraw as HD

OUT = Path(__file__).resolve().parent / "_stilblatt"
PPM = 160

# name, Karte, Ausschnitt (x0, y0, x1, y1), Figur (x, Standlinie y) oder None
PIECES = [
    ("park_pflaster", "park", (-8.0, -16.0, 4.0, -9.0), (-3.0, -12.3)),
    ("park_workshop", "park", (-22.0, -20.5, -10.0, -11.0), (-15.5, -16.5)),
    ("park_fassade_coldstore", "park", (6.0, -17.5, 18.0, -10.5), (12.0, -13.4)),
    ("park_hinterland", "park", (-23.0, -12.0, -11.0, -5.0), None),
    ("park_laternen", "park", (0.0, -9.5, 12.0, -2.5), (8.0, -5.2)),
    ("museum_galerie", "museum", (-16.5, 1.0, -4.5, 9.0), (-9.6, 3.0)),
    ("wald_seeufer", "wald", (14.0, -14.5, 26.0, -7.5), (19.2, -10.5)),
    ("wald_weg", "wald", (-19.0, -7.5, -7.0, -0.5), (-12.0, -4.2)),
]


def label(img, text):
    d = ImageDraw.Draw(img, "RGBA")
    try:
        f = ImageFont.truetype("arialbd.ttf", 26)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle([0, 0, 16 + len(text) * 15, 40], fill=(0, 0, 0, 150))
    d.text((8, 6), text, font=f, fill=(255, 255, 255, 255))


def figure_on(img, x0, y1, fx, fy):
    fim, fw, fh = HD.crewmate(PPM)
    HD.paste_clipped(img, fim, int(round((fx - fw / 2 - x0) * PPM)), int(round((y1 - fy) * PPM)) - fim.height)


def render_piece(name, karte, rect, fig):
    x0, y0, x1, y1 = rect
    if karte == "park":
        import preview_park as PP
        img = PP.render(x0, y0, x1, y1, figure=fig)
    elif karte == "museum":
        import preview_museum as PM
        img = PM.render(x0, y0, x1, y1)
        if fig:
            figure_on(img, x0, y1, *fig)
    else:
        import preview_wald as PW
        img = PW.render(x0, y0, x1, y1)
        if fig:
            figure_on(img, x0, y1, *fig)
    return img


def main(argv):
    OUT.mkdir(exist_ok=True)
    stage = argv[0] if argv else "nachher"
    only = argv[1:] if len(argv) > 1 else None
    for name, karte, rect, fig in PIECES:
        if only and name not in only:
            continue
        img = render_piece(name, karte, rect, fig).convert("RGB")
        label(img, f"{name} ({stage}), 160 px/m, Ausschnitt {rect[2] - rect[0]:.0f} x {rect[3] - rect[1]:.0f} m")
        p = OUT / f"{name}_{stage}.png"
        img.save(p)
        print(p, img.size)
    if not only or "park_gesamt" in only:
        import preview_park as PP
        img = PP.render(*PP.L.BOUNDS, ppm=40).convert("RGB")
        label(img, f"park_gesamt ({stage}), 40 px/m")
        p = OUT / f"park_gesamt_{stage}.png"
        img.save(p)
        print(p, img.size)


if __name__ == "__main__":
    main(sys.argv[1:])
