# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_climb_button.py - Symbol fuer den Use-Knopf am Forest-Hochsitz (AtlasLookout): Holzleiter mit
# Fernglas, im Stil der Vanilla-Aktionsknoepfe (flache Flaechen, zwei Tonstufen, Glanzkante, dicke
# dunkle Kontur). Die Beschriftung ("CLIMB") setzt das Spiel darunter wie bei "SECURITY".
#
#   python tools/gen_climb_button.py   ->  assets/task_climb_button.png (256 x 256)

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "task_climb_button.png"
S = 4
N = 256 * S
INK = (29, 27, 33, 255)
LW = 10 * S

WOOD = (190, 132, 74, 255)
WOOD_D = (128, 84, 44, 255)
WOOD_L = (226, 176, 112, 255)
METAL = (78, 88, 104, 255)
METAL_D = (48, 54, 66, 255)
METAL_L = (132, 146, 166, 255)
GLASS = (150, 212, 236, 255)
GLASS_L = (228, 248, 255, 255)


def P(pts):
    return [(x * S, y * S) for x, y in pts]


img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(img)


def poly(pts, fill, lw=LW):
    d.polygon(P(pts), fill=fill)
    d.line(P(pts + [pts[0]]), fill=INK, width=lw, joint="curve")


def rail(x0, y0, x1, y1, w):
    # schraeger Holm als Viereck mit Schattenseite und Glanzkante
    dx, dy = x1 - x0, y1 - y0
    ln = (dx * dx + dy * dy) ** 0.5
    nx, ny = -dy / ln * w / 2, dx / ln * w / 2
    pts = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    d.polygon(P(pts), fill=WOOD)
    d.polygon(P([pts[2], pts[3], (x0 - nx * 0.2, y0 - ny * 0.2), (x1 - nx * 0.2, y1 - ny * 0.2)]), fill=WOOD_D)
    d.line(P([(x0 + nx * 0.45, y0 + ny * 0.45), (x1 + nx * 0.45, y1 + ny * 0.45)]), fill=WOOD_L, width=4 * S)
    d.line(P(pts + [pts[0]]), fill=INK, width=LW, joint="curve")


# Leiter: zwei Holme, leicht nach rechts geneigt, fuenf Sprossen
L0, L1 = (62, 238), (104, 22)      # linker Holm unten -> oben
R0, R1 = (132, 238), (170, 22)     # rechter Holm
for k in range(5):
    t = 0.14 + k * 0.18
    a = (L0[0] + (L1[0] - L0[0]) * t, L0[1] + (L1[1] - L0[1]) * t)
    b = (R0[0] + (R1[0] - R0[0]) * t, R0[1] + (R1[1] - R0[1]) * t)
    poly([(a[0], a[1] - 8), (b[0], b[1] - 8), (b[0], b[1] + 8), (a[0], a[1] + 8)], WOOD_D, lw=8 * S)
    d.line(P([(a[0] + 4, a[1] - 3), (b[0] - 4, b[1] - 3)]), fill=WOOD_L, width=3 * S)
rail(*L0, *L1, 22)
rail(*R0, *R1, 22)

# Fernglas unten rechts vor der Leiter
def barrel(cx, cy):
    poly([(cx - 26, cy - 34), (cx + 26, cy - 34), (cx + 30, cy + 30), (cx - 30, cy + 30)], METAL)
    d.polygon(P([(cx + 6, cy - 34), (cx + 26, cy - 34), (cx + 30, cy + 30), (cx + 10, cy + 30)]), fill=METAL_D)
    d.line(P([(cx - 16, cy - 28), (cx - 18, cy + 22)]), fill=METAL_L, width=5 * S)
    d.line(P([(cx - 26, cy - 34), (cx + 26, cy - 34), (cx + 30, cy + 30), (cx - 30, cy + 30), (cx - 26, cy - 34)]), fill=INK, width=LW, joint="curve")
    # Linse unten
    d.ellipse(P([(cx - 26, cy + 18), (cx + 26, cy + 44)]), fill=GLASS, outline=INK, width=8 * S)
    d.ellipse(P([(cx - 14, cy + 23), (cx - 2, cy + 31)]), fill=GLASS_L)


barrel(150, 176)
barrel(210, 176)
poly([(171, 158), (189, 158), (189, 196), (171, 196)], METAL_D, lw=8 * S)   # Steg
d.ellipse(P([(169, 144), (191, 166)]), fill=METAL_L, outline=INK, width=7 * S)  # Drehrad

img = img.resize((256, 256), Image.LANCZOS)
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, optimize=True)
print("ok", OUT.name, img.size)
