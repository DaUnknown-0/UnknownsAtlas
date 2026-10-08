# Vorschau: Boden + Objekt-Sprites in Standlinien-Reihenfolge (wie im Spiel), ohne Spiel.
#   python tools/preview_museum.py                  ganze Karte, halbe Aufloesung (80 px/m)
#   python tools/preview_museum.py x0 y0 x1 y1      Ausschnitt in Spielaufloesung (160 px/m)
# render(x0, y0, x1, y1) liefert den Ausschnitt als RGBA-Bild (tools/stilblatt.py nutzt das).
import sys
from pathlib import Path
from PIL import Image
import museum_layout as L
import museum_art as A
import handdraw as HD
import gen_museum as G

bx0, by0, bx1, by1 = L.BOUNDS


def floor_full(ppm):
    if ppm == 80:
        return Image.open(G.OUT_FLOOR).convert("RGBA")
    floor = Image.new("RGBA", (int((bx1 - bx0) * ppm), int((by1 - by0) * ppm)))
    cols, rows = G.FLOOR_TILES
    tiles = sorted(G.ASSETS.glob("museum_floor_*.jpg"), key=lambda p: int(p.stem.split("_")[-1]))
    tw = th = None
    for i, t in enumerate(tiles):
        im = Image.open(t).convert("RGBA")
        if tw is None:
            tw, th = im.size
        floor.paste(im, ((i % cols) * tw, (i // cols) * th))
    return floor


def render(x0=None, y0=None, x1=None, y1=None, ppm=None):
    full = x0 is None
    ppm = ppm or (80 if full else G.FLOOR_PX_PER_M)
    floor = floor_full(ppm)
    props = []
    for i, (kind, shape) in enumerate(A.all_props()):
        im, wx, wy, base = A.draw_prop(kind, shape, i, ppm)
        props.append((base, im, wx, wy))
    props.sort(key=lambda t: -t[0])
    for base, im, wx, wy in props:
        HD.paste_clipped(floor, im, int(round((wx - bx0) * ppm)), int(round((by1 - wy) * ppm)) - im.height)
    if not full:
        floor = floor.crop((int((x0 - bx0) * ppm), int((by1 - y1) * ppm), int((x1 - bx0) * ppm), int((by1 - y0) * ppm)))
    return floor


if __name__ == "__main__":
    if len(sys.argv) == 5:
        img = render(*map(float, sys.argv[1:]))
    else:
        img = render()
    out = Path(__file__).resolve().parent / "_preview.png"
    img.save(out)
    print(out, img.size)
