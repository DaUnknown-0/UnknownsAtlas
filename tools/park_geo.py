# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# park_geo.py - Geometrie der Parkkarte aus park_layout.py (shapely, Weltmeter).
# Wie wald_geo.py, dazu: die Achterbahn (RAIL) schneidet die begehbare Flaeche ausser an den
# Bahnuebergaengen, der Kanal (WATER) ebenso ausser an den Bruecken.

from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union

import park_layout as P


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
    t = P.WALL
    if side == "N":
        return box(a, y1 - 0.01, b, y1 + t + 0.01)
    if side == "S":
        return box(a, y0 - t - 0.01, b, y0 + 0.01)
    if side == "E":
        return box(x1 - 0.01, a, x1 + t + 0.01, b)
    return box(x0 - t - 0.01, a, x0 + 0.01, b)


def clearing(rect):
    x0, y0, x1, y1 = rect
    return box(x0 + P.CORNER, y0 + P.CORNER, x1 - P.CORNER, y1 - P.CORNER).buffer(P.CORNER, 16)


def rail_block():
    """Strecke ohne die Bahnuebergaenge: sperrt den Weg."""
    rail = unary_union([shape(s) for s in P.RAIL])
    return rail.difference(unary_union([shape(c) for _k, c, _d in P.CROSSINGS]))


def build():
    outdoor = [clearing(rect) for _k, _n, _s, rect in P.CLEARINGS]
    for key, _n, _s, inner, _d in P.BUILDINGS:
        x0, y0, x1, y1 = inner
        outdoor.append(box(x0 - P.WALL, y0 - P.WALL, x1 + P.WALL, y1 + P.WALL).buffer(P.YARD[key], 16))
    for pts in P.PATHS:
        outdoor.append(LineString(pts).buffer(P.PATH_W / 2, 16))
    outdoor = unary_union(outdoor).intersection(box(*P.BOUNDS))
    water = unary_union([shape(s) for s in P.WATER])
    bridges = unary_union([shape(s) for s in P.BRIDGES])
    outdoor = outdoor.difference(water.difference(bridges))
    outdoor = outdoor.difference(rail_block())

    shells, inners, openings, doors = [], [], [], []
    for key, _n, _s, inner, dl in P.BUILDINGS:
        x0, y0, x1, y1 = inner
        shells.append(box(x0 - P.WALL, y0 - P.WALL, x1 + P.WALL, y1 + P.WALL))
        inners.append(box(*inner))
        for side, a, b, kind in dl:
            o = opening_rect(inner, side, a, b)
            openings.append(o)
            doors.append((key, side, a, b, kind, o))
    walk = outdoor.difference(unary_union(shells))
    walk = unary_union([walk] + inners + openings).buffer(0)
    return walk, water.difference(bridges), shells, doors


def rooms(walk):
    out = {}
    for key, name, sysname, inner, _d in P.BUILDINGS:
        out[key] = (name, sysname, box(*inner))
    for key, name, sysname, rect in P.CLEARINGS:
        g = clearing(rect).intersection(walk)
        # Gebaeude liegen nie in einer offenen Flaeche; falls doch, gehoert die Flaeche dem Gebaeude
        g = g.difference(unary_union([box(*b[3]).buffer(P.WALL) for b in P.BUILDINGS]))
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda p: p.area)
        out[key] = (name, sysname, g)
    return out
