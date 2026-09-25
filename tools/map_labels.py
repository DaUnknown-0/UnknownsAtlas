"""Beschriftung der Minimaps (Wald, Park): Raumnamen, die breiter als ihr Raum sind, zweizeilig setzen.

Liefert zugleich das Rechteck in Weltmetern, dem die Sabotage- und Tuerknoepfe im Builder ausweichen
(AtlasMapDef.MapLabels -> AtlasMuseumBuilder.AvoidLabels).
"""
from shapely.geometry import box

SPACING = 2


def _bbox(d, font, text):
    return d.multiline_textbbox((0, 0), text, font=font, anchor="mm", align="center", spacing=SPACING)


def _world_rect(cx, cy, bb, s):
    l_, t_, r_, b_ = bb
    x, y = cx + (l_ + r_) / 2 / s, cy - (t_ + b_) / 2 / s
    return x, y, (r_ - l_) / 2 / s, (b_ - t_) / 2 / s


def _fits(rect, area):
    x, y, hw, hh = rect
    return area.contains(box(x - hw, y - hh, x + hw, y + hh))


def place(d, font, name, cx, cy, area, s, P, fill, out):
    """Zeichnet `name` bei (cx, cy); passt er nicht in `area` (begehbare Flaeche, leicht gepuffert),
    wird an dem Leerzeichen umgebrochen, das die laengere Zeile am kuerzesten macht."""
    text = name
    rect = _world_rect(cx, cy, _bbox(d, font, text), s)
    if not _fits(rect, area) and " " in name:
        words = name.split(" ")
        best = None
        for i in range(1, len(words)):
            t = " ".join(words[:i]) + "\n" + " ".join(words[i:])
            bb = _bbox(d, font, t)
            if best is None or bb[2] - bb[0] < best[0]:
                best = (bb[2] - bb[0], t, bb)
        text = best[1]
        rect = _world_rect(cx, cy, best[2], s)
    d.multiline_text(P(cx, cy), text, font=font, fill=fill, anchor="mm", align="center", spacing=SPACING)
    out.append(rect)
    return text
