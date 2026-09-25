# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# wald_geo.py - Geometrie der Waldkarte aus wald_layout.py (shapely, Weltmeter).

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

import wald_layout as W


def shape(s):
    k = s[0]
    if k == "rect":
        return box(*s[1:5])
    if k == "circle":
        return Point(s[1], s[2]).buffer(s[3], 24)
    if k == "ellipse":
        from shapely import affinity
        return affinity.scale(Point(s[1], s[2]).buffer(1, 32), s[3], s[4])
    raise ValueError(k)


def opening_rect(inner, side, a, b):
    x0, y0, x1, y1 = inner
    t = W.WALL
    if side == "N":
        return box(a, y1 - 0.01, b, y1 + t + 0.01)
    if side == "S":
        return box(a, y0 - t - 0.01, b, y0 + 0.01)
    if side == "E":
        return box(x1 - 0.01, a, x1 + t + 0.01, b)
    return box(x0 - t - 0.01, a, x0 + 0.01, b)


def rounded(rect):
    x0, y0, x1, y1 = rect
    return box(x0 + W.CORNER, y0 + W.CORNER, x1 - W.CORNER, y1 - W.CORNER).buffer(W.CORNER, 16)


def clearing_shape(key):
    """Gerundete Flaeche einer Lichtung; Mitglieder einer Gruppe teilen sich die Huelle aller Rechtecke."""
    rects = {k: r for k, _n, _s, r in W.CLEARINGS}
    for members in getattr(W, "CLEARING_GROUPS", {}).values():
        if key in members:
            rs = [rects[m] for m in members]
            return rounded((min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)))
    return rounded(rects[key])


def build():
    outdoor = []
    for key, _n, _s, _rect in W.CLEARINGS:
        outdoor.append(clearing_shape(key))
    for key, _n, _s, inner, _d in W.BUILDINGS:
        y = W.YARD[key]
        x0, y0, x1, y1 = inner
        outdoor.append(box(x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL).buffer(y, 16))
    for pts in W.PATHS:
        outdoor.append(LineString(pts).buffer(W.PATH_W / 2, 16))
    # Schliessen: Hoefe, die sich fast beruehren, liessen seit der Verkleinerung (1,5-m-Hoefe) schmale
    # Waldstreifen von 0-0,5 m stehen - sinnlose Kanten mitten im Weg. Luecken unter 1,2 m werden Hof.
    outdoor = unary_union(outdoor).buffer(0.6, 16).buffer(-0.6, 16)
    water = unary_union([shape(s) for s in W.WATER])
    outdoor = outdoor.difference(water)
    outdoor = unary_union([outdoor, shape(W.DOCK)])   # Steg ueber dem Wasser
    water = water.difference(shape(W.DOCK))

    shells, inners, openings, doors = [], [], [], []
    for key, _n, _s, inner, dl in W.BUILDINGS:
        x0, y0, x1, y1 = inner
        shells.append(box(x0 - W.WALL, y0 - W.WALL, x1 + W.WALL, y1 + W.WALL))
        inners.append(box(*inner))
        for side, a, b, kind in dl:
            o = opening_rect(inner, side, a, b)
            openings.append(o)
            doors.append((key, side, a, b, kind, o))
    walk = outdoor.difference(unary_union(shells))
    walk = unary_union([walk] + inners + openings).buffer(0)
    return walk, water, shells, doors


def rooms(walk):
    out = {}
    for key, name, sysname, inner, _d in W.BUILDINGS:
        out[key] = (name, sysname, box(*inner))
    for key, name, sysname, rect in W.CLEARINGS:
        g = clearing_shape(key).intersection(box(*rect)).intersection(walk)
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda p: p.area)
        out[key] = (name, sysname, g)
    return out
