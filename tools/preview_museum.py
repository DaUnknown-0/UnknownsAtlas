# Vorschau: Boden + Objekt-Sprites in Standlinien-Reihenfolge (wie im Spiel), ohne Spiel.
#   python tools/preview_museum.py                  ganze Karte, halbe Aufloesung (80 px/m)
#   python tools/preview_museum.py x0 y0 x1 y1      Ausschnitt in Spielaufloesung (160 px/m)
import sys
from pathlib import Path
from PIL import Image
import museum_layout as L
import museum_art as A
import gen_museum as G

bx0, by0, bx1, by1 = L.BOUNDS
full = len(sys.argv) != 5
PPM = 80 if full else G.FLOOR_PX_PER_M
if full:
    floor = Image.open(G.OUT_FLOOR).convert("RGBA")
else:
    floor = Image.new("RGBA", (int((bx1 - bx0) * PPM), int((by1 - by0) * PPM)))
    cols, rows = G.FLOOR_TILES
    tiles = sorted(G.ASSETS.glob("museum_floor_*.jpg"), key=lambda p: int(p.stem.split("_")[-1]))
    tw = th = None
    for i, t in enumerate(tiles):
        im = Image.open(t).convert("RGBA")
        if tw is None:
            tw, th = im.size
        floor.paste(im, ((i % cols) * tw, (i // cols) * th))
props = []
for i, (kind, shape) in enumerate(A.all_props()):
    im, wx, wy, base = A.draw_prop(kind, shape, i, PPM)
    props.append((base, im, wx, wy))
props.sort(key=lambda t: -t[0])
for base, im, wx, wy in props:
    floor.alpha_composite(im, (int(round((wx - bx0) * PPM)), int(round((by1 - wy) * PPM)) - im.height))
if not full:
    x0, y0, x1, y1 = map(float, sys.argv[1:])
    floor = floor.crop((int((x0 - bx0) * PPM), int((by1 - y1) * PPM), int((x1 - bx0) * PPM), int((by1 - y0) * PPM)))
out = Path(__file__).resolve().parent / "_preview.png"
floor.save(out)
print(out, floor.size)
