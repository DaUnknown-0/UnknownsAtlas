# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# props_common.py - gemeinsame Bausteine und Render-Ablauf fuer die Amberhive-Einrichtungsobjekte (art/props).
# Wird von props_<gruppe>.py importiert; die Gruppen rufen am Ende main(BUILDERS) auf.
#   blender -b --factory-startup -P props_<gruppe>.py -- [art1 art2 ...]     (ohne Arten: alle der Gruppe)
#
# Jede Bau-Funktion bekommt (frame, frames) und legt ihre Teile ueber die Helfer hier an (Weltmeter, Fuss auf z = 0,
# Grundflaeche x in [-w/2, w/2], y in [0, d]). Alle Teile landen in PARTS und werden vor dem Rendern mit finish() geschert.
# Animierte Arten: erst alle Frames vermessen, dann jedes Frame mit denselben Grenzen rendern (gleiche Bildgroesse, gleicher Anker).
#
# Stil V2 (art/STIL_V2.md): die Arten nennen ihre Anstrichtoene direkt (je Raum ein Ton), glow()/flame() setzen Lichthoefe,
# jedes Objekt ab 0,3 m Hoehe bekommt einen weichen Bodenschatten. HIVE_PROPS_OUT=<ordner> lenkt die Ausgabe zum Probieren um.

import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bmesh  # noqa: E402
import bpy  # noqa: E402,F401
from mathutils import Matrix, Vector  # noqa: E402

import hive_style as S  # noqa: E402

PAL = S.PALETTE
ART = os.environ.get("HIVE_PROPS_OUT") or os.path.normpath(os.path.join(HERE, "..", "art", "props"))
with open(os.path.join(HERE, "..", "art_props.json"), encoding="utf-8") as _f:
    SPECS = {e["kind"]: e for e in json.load(_f)}

PARTS = []          # (Objekt, schattieren?)
SOFT = []           # Lichthoefe (schon fertig geschert, ohne Linie)
_count = [0]


def _nm(p="p"):
    _count[0] += 1
    return f"{p}{_count[0]}"


def add(ob, shade=True):
    PARTS.append((ob, shade))
    return ob


def flat(ob):
    """Teil ohne Richtungs-Schattierung (Leuchtendes, Lichtpunkte)."""
    for i, (o, _) in enumerate(PARTS):
        if o is ob:
            PARTS[i] = (o, False)
    return ob


def glow(x, y, z, r, color="glow", strength=0.55):
    """Lichthof um etwas Leuchtendes (Weltkoordinaten vor der Scherung; nicht innerhalb von xf benutzen)."""
    SOFT.append(S.halo(_nm("h"), x, y, z, r, color, strength))


def flame(x, y, z, h=0.07, r=0.028, halo=0.3):
    """Kerzenflamme: Tropfen in zwei Toenen, unbeleuchtet, mit Lichthof."""
    flat(lathe([(0, 0), (r, h * 0.3), (r * 0.75, h * 0.6), (0, h * 1.25)], "flame", M=T(x, y, z), seg=10))
    flat(lathe([(0, 0), (r * 0.55, h * 0.25), (0, h * 0.75)], "flame_core", M=T(x, y - 0.004, z + h * 0.08), seg=8))
    if halo:
        glow(x, y, z + h * 0.5, halo, "glow", 0.5)


def mix(a, b, t):
    a = PAL[a] if isinstance(a, str) else a
    b = PAL[b] if isinstance(b, str) else b
    return tuple(round(a[i] + (b[i] - a[i]) * t, 3) for i in range(3))


# ------------------------------------------------------------------ Matrizen

def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def SC(x, y, z):
    m = Matrix.Identity(4)
    m[0][0], m[1][1], m[2][2] = x, y, z
    return m


def about(M, c):
    """Matrix M um den Punkt c anwenden."""
    return T(*c) @ M @ T(-c[0], -c[1], -c[2])


def aim(d):
    """Rotation, die die lokale z-Achse auf Richtung d dreht."""
    return Vector(d).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


class xf:
    """Alles, was im with-Block entsteht, wird beim Verlassen mit M transformiert (Meshdaten, verschachtelbar)."""

    def __init__(self, M):
        self.M = M

    def __enter__(self):
        self.i = len(PARTS)
        return self

    def __exit__(self, *a):
        for ob, _ in PARTS[self.i:]:
            ob.data.transform(self.M)
            ob.data.update()


# ------------------------------------------------------------------ Grundkoerper

def box(x0, y0, z0, x1, y1, z1, mat, bevel=0.0):
    return add(S.box(_nm("b"), min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1), mat, bevel))


def cyl(cx, cy, z0, z1, r, mat, seg=24, r_top=None):
    return add(S.cylinder(_nm("c"), cx, cy, z0, z1, r, mat, seg=seg, r_top=r_top))


def prism(pts, z0, z1, mat):
    """Senkrechtes Prisma; Umlaufsinn egal (Normalen werden neu berechnet)."""
    return ext(pts, z0, z1, mat, axis="z")


def hexp(cx, cy, r, z0, z1, mat, rot=0.0, sy=1.0):
    pts = S.hexagon_pts(cx, cy, r, True, rot)
    if sy != 1.0:
        pts = [(x, cy + (y - cy) * sy) for x, y in pts]
    return prism(pts, z0, z1, mat)


def sph(cx, cy, cz, r, mat, seg=16, sx=1.0, sy=1.0, sz=1.0):
    ob = add(S.sphere(_nm("s"), 0, 0, 0, r, mat, seg=seg))
    ob.data.transform(T(cx, cy, cz) @ SC(sx, sy, sz))
    return ob


def tor(cx, cy, cz, Rr, r, mat, seg=32, ring=8, M=None):
    ob = add(S.torus(_nm("t"), 0, 0, 0, Rr, r, mat, seg=seg, ring=ring))
    ob.data.transform(T(cx, cy, cz) @ (M or Matrix.Identity(4)))
    return ob


def _finish_bm(bm, mats, M=None):
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return add(S._obj(_nm("m"), bm, mats if isinstance(mats, list) else [mats]))


def lathe(prof, mats, M=None, seg=24, band=None, stripe=None, loop=False):
    """Drehkoerper um die lokale z-Achse. prof: [(r, h), ...]; band: Materialindex je Profilabschnitt;
    stripe: (a, b) wechselt Abschnitte mit Index a reihum zwischen a und b (Daubenlinien); loop: Profil geschlossen (Ring)."""
    bm = bmesh.new()
    rings = []
    for r, h in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, h))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), h))
                          for j in range(seg)])
    nseg = len(rings) if loop else len(rings) - 1
    for i in range(nseg):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        mi = band[i] if band else 0
        for j in range(seg):
            mj = mi
            if stripe and mi == stripe[0]:
                mj = stripe[j % 2]
            k = (j + 1) % seg
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                f = bm.faces.new((a[0], b[j], b[k]))
            elif len(b) == 1:
                f = bm.faces.new((a[j], a[k], b[0]))
            else:
                f = bm.faces.new((a[j], a[k], b[k], b[j]))
            f.material_index = mj
    if not loop:
        if len(rings[0]) > 1:
            f = bm.faces.new(list(reversed(rings[0])))
            f.material_index = band[0] if band else 0
        if len(rings[-1]) > 1:
            f = bm.faces.new(rings[-1])
            f.material_index = band[-1] if band else 0
    return _finish_bm(bm, mats, M)


def tube(p0, p1, r, mat, seg=12, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    return lathe([(0, 0), (r, 0), (r if r1 is None else r1, L), (0, L)], mat, M=T(*p0) @ aim(p1 - p0), seg=seg)


def ring_y(cx, cy, cz, ri, ro, t, mat, seg=32):
    """Flacher Ring (Felge) mit Achse y, Stirn nach Sueden, von cy bis cy + t."""
    return lathe([(ri, 0), (ro, 0), (ro, t), (ri, t)], mat, M=T(cx, cy + t, cz) @ R("X", 90), seg=seg, loop=True)


def disc_y(cx, cy, cz, r, t, mat, seg=28, r_back=None):
    """Scheibe mit Achse y (Stirn nach Sueden) von cy bis cy + t."""
    rb = r if r_back is None else r_back
    return lathe([(0, 0), (rb, 0), (r, t), (0, t)], mat, M=T(cx, cy + t, cz) @ R("X", 90), seg=seg)


def loft(loops, mats, band=None, caps=True):
    """Haut ueber geschlossene Schleifen gleicher Punktzahl (3D)."""
    bm = bmesh.new()
    vl = [[bm.verts.new(p) for p in lp] for lp in loops]
    n = len(loops[0])
    for i in range(len(vl) - 1):
        for j in range(n):
            k = (j + 1) % n
            f = bm.faces.new((vl[i][j], vl[i][k], vl[i + 1][k], vl[i + 1][j]))
            f.material_index = band[i] if band else 0
    if caps:
        f = bm.faces.new(list(reversed(vl[0])))
        f.material_index = band[0] if band else 0
        f = bm.faces.new(vl[-1])
        f.material_index = band[-1] if band else 0
    return _finish_bm(bm, mats)


def ext(pts, a0, a1, mat, axis="y"):
    """Prisma aus einem 2D-Umriss: axis 'y' -> pts = (x, z); 'x' -> pts = (y, z); 'z' -> pts = (x, y)."""
    def p3(u, v, a):
        return (u, a, v) if axis == "y" else ((a, u, v) if axis == "x" else (u, v, a))
    return loft([[p3(u, v, a0) for u, v in pts], [p3(u, v, a1) for u, v in pts]], mat)


def sweep(path, radius, mat, seg=16, band=None):
    """Rohr entlang eines Pfads (Liste 3D-Punkte); radius Zahl oder Liste je Punkt."""
    pts = [Vector(p) for p in path]
    rs = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tans = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tans.append((b - a).normalized())
    n = tans[0].orthogonal().normalized()
    loops = []
    for i, p in enumerate(pts):
        t = tans[i]
        n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        loops.append([tuple(p + rs[i] * (math.cos(2 * math.pi * j / seg) * n + math.sin(2 * math.pi * j / seg) * b))
                      for j in range(seg)])
    return loft(loops, mat, band=band)


def ellipse_pts(cx, cy, rx, ry, n=24, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


# ------------------------------------------------------------------ zusammengesetzte Kleinteile

def comb_panel(x0, x1, z0, z1, y, r, mat, alt=None, depth=0.014, pattern=None):
    """Wabenmuster auf einer Suedflaeche (Ebene y): sechseckige Zellen, die um depth nach Sueden vorstehen."""
    h = math.sqrt(3) * r
    out = []
    col = 0
    x = x0 + r
    while x + r <= x1 + 1e-6:
        z = z0 + h / 2 + (h / 2 if col % 2 else 0)
        row = 0
        while z + h / 2 <= z1 + 1e-6:
            m = mat
            if alt and pattern and pattern(col, row):
                m = alt
            out.append(ext(S.hexagon_pts(x, z, r * 0.84), y - depth, y, m))
            z += h
            row += 1
        x += 1.5 * r
        col += 1
    return out


def comb_top(x0, x1, y0, y1, z, r, mat, alt=None, pattern=None, t=0.012):
    """Wabenmuster auf einer Deckflaeche (Hoehe z)."""
    h = math.sqrt(3) * r
    out = []
    col = 0
    x = x0 + r
    while x + r <= x1 + 1e-6:
        y = y0 + h / 2 + (h / 2 if col % 2 else 0)
        row = 0
        while y + h / 2 <= y1 + 1e-6:
            m = mat
            if alt and pattern and pattern(col, row):
                m = alt
            out.append(hexp(x, y, r * 0.84, z, z + t, m))
            y += h
            row += 1
        x += 1.5 * r
        col += 1
    return out


def bee(x, y, z, s=1.0, yaw=0.0, wing_up=20.0):
    """Niedliche Biene, Laengsachse x (Kopf nach +x vor dem Drehen), Bauch auf Hoehe z."""
    with xf(T(x, y, z) @ R("Z", yaw) @ SC(s, s, s)):
        prof = [(0, -0.27), (0.045, -0.235), (0.085, -0.19), (0.112, -0.13), (0.125, -0.07), (0.122, -0.01), (0.10, 0.03),
                (0.0, 0.05)]
        lathe(prof, ["bee_black", "bee_yellow"], M=T(0, 0, 0.13) @ R("Y", 90), seg=20, band=[0, 0, 1, 0, 1, 0, 0])
        sph(0.09, 0, 0.14, 0.085, "propolis_light", seg=16)
        sph(0.185, 0, 0.13, 0.075, "bee_black", seg=16)
        sph(0.225, -0.035, 0.155, 0.022, "white", seg=8)
        sph(0.225, 0.035, 0.155, 0.022, "white", seg=8)
        for sgn in (-1, 1):
            tube((0.2, sgn * 0.03, 0.19), (0.27, sgn * 0.07, 0.29), 0.008, "bee_black", seg=6)
            sph(0.27, sgn * 0.07, 0.29, 0.02, "bee_black", seg=8)
            with xf(about(R("X", sgn * wing_up) @ R("Z", sgn * -25), (0.07, sgn * 0.02, 0.22))):
                sph(0.02, sgn * 0.12, 0.22, 0.13, "wing", seg=16, sx=0.75, sy=0.55, sz=0.08)


def jar(x, y, z, r, h, fill="honey", lid="wax", label=True, cloth=None):
    """Honigglas: Honig bis zur Schulter, Glas darueber, Deckel, optional Stoffhaube und Etikett."""
    prof = [(0, 0), (r * 0.9, 0), (r, 0.03), (r, h * 0.62), (r * 0.98, h * 0.72), (r * 0.78, h * 0.84), (r * 0.66, h * 0.86),
            (0, h * 0.86)]
    lathe(prof, [fill, "glass"], M=T(x, y, z), seg=20, band=[0, 0, 0, 0, 0, 1, 1])
    cyl(x, y, z + h * 0.84, z + h, r * 0.72, lid, seg=20)
    if cloth:
        cyl(x, y, z + h * 0.93, z + h * 1.02, r * 0.86, cloth, seg=20, r_top=r * 0.6)
    if label:
        box(x - r * 0.55, y - r - 0.006, z + h * 0.24, x + r * 0.55, y - r * 0.6, z + h * 0.52, "paper")


def hat(x, y, z, s=1.0, veil=False):
    """Imkerhut: Krempe, Kopf, Band, optional Schleier darunter."""
    if veil:
        lathe([(0, 0), (0.17 * s, 0), (0.2 * s, 0.2 * s), (0, 0.2 * s)], "cloth_white", M=T(x, y, z - 0.2 * s), seg=24)
    cyl(x, y, z, z + 0.025 * s, 0.24 * s, "cloth_cream", seg=28)
    cyl(x, y, z + 0.025 * s, z + 0.06 * s, 0.125 * s, "wood_dark", seg=24)
    cyl(x, y, z + 0.06 * s, z + 0.15 * s, 0.12 * s, "cloth_cream", seg=24, r_top=0.10 * s)


def wheel_y(cx, cy, cz, Rw, rim="wood_dark", spoke="wood", hub="brass", n=8, rot=0.0, t=0.05):
    """Speichenrad mit Achse y (Stirn nach Sueden), Vorderkante bei cy."""
    ring_y(cx, cy, cz, Rw * 0.82, Rw, t, rim)
    for i in range(n):
        a = math.radians(rot) + 2 * math.pi * i / n
        tube((cx, cy + t * 0.5, cz), (cx + math.cos(a) * Rw * 0.86, cy + t * 0.5, cz + math.sin(a) * Rw * 0.86), 0.018, spoke,
             seg=6)
    disc_y(cx, cy - 0.02, cz, Rw * 0.2, t + 0.04, hub, seg=16)


def flower(x, y, z, s=1.0, petal="petal_pink", n=6, stem=0.25):
    """Bluete auf Stiel: Stiel, zwei Blaetter, Bluetenblaetter im Kreis, Pollen-Mitte."""
    top = z + stem * s
    tube((x, y, z), (x, y, top), 0.012 * s, "leaf_dark", seg=6)
    for sgn in (-1, 1):
        sph(x + sgn * 0.05 * s, y, z + stem * s * 0.45, 0.05 * s, "leaf", seg=10, sx=1.0, sy=0.5, sz=0.35)
    for i in range(n):
        a = 2 * math.pi * i / n
        sph(x + math.cos(a) * 0.055 * s, y + math.sin(a) * 0.055 * s, top, 0.045 * s, petal, seg=10, sz=0.4)
    sph(x, y, top + 0.012 * s, 0.035 * s, "pollen", seg=10, sz=0.6)


# ------------------------------------------------------------------ Rendern

def _bounds(objs):
    xs, ys = [], []
    for ob in objs:
        for v in ob.data.vertices:
            xs.append(v.co.x)
            ys.append(v.co.y)
    return min(xs), min(ys), max(xs), max(ys)


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(reversed(pts))
    return lo[:-1] + hi[:-1]


def _make(build, f, n, kind=None):
    S.reset()
    PARTS.clear()
    SOFT.clear()
    S.REMAP = SKIN.get(kind, {})
    build(f, n)
    S.REMAP = {}
    low = []
    sp = SPECS.get(kind)
    if sp and sp["height"] >= 0.3 and kind not in NO_SHADOW:      # weicher Bodenschatten: Huelle der bodennahen Punkte
        for ob, _ in PARTS:
            mw = ob.matrix_world
            for v in ob.data.vertices:
                co = mw @ v.co
                if co.z < 0.3:
                    low.append((round(co.x, 2), round(co.y, 2)))
    for ob, sh in PARTS:
        S.finish(ob, sh)
    objs = [ob for ob, _ in PARTS] + list(SOFT)
    hull = _hull(low)
    if len(hull) >= 3:
        k = min(1.0, 0.5 + sp["height"] * 0.3)
        hull = [(x + 0.05 * k, y - 0.045 * k) for x, y in hull]
        objs.append(S.soft_blob("shadow", hull, 0.13, (0.13, 0.07, 0.10), 0.36 * k, z=0.003))
    return objs


NO_SHADOW = {"hive_banner", "stair_up", "stair_down", "chute_top", "chute_exit", "dance_floor"}


def render_kind(kind, build):
    n = int(SPECS[kind].get("frames", 1))
    os.makedirs(ART, exist_ok=True)
    bb = None
    for f in range(n):
        b = _bounds(_make(build, f, n, kind))
        bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
    metas = []
    for f in range(n):
        objs = _make(build, f, n, kind)
        name = kind if n == 1 else f"{kind}_f{f}"
        out = os.path.join(ART, name + ".png")
        meta = S.render_sprite(objs, out, ppm=120, extra_bounds=bb)
        metas.append(meta)
        if n > 1 and f == 0:
            shutil.copyfile(out, os.path.join(ART, kind + ".png"))
            shutil.copyfile(os.path.join(ART, name + ".json"), os.path.join(ART, kind + ".json"))
    print(f"[props] {kind}: {n} Bild(er) {metas[0]['w']}x{metas[0]['h']}")
    return metas


def main(builders):
    want = S.args() or list(builders)
    for kind in want:
        if kind in builders:
            render_kind(kind, builders[kind])


# ------------------------------------------------------------------ Neubau V2-D (15.11.2026): Palette und Bausteine
# Die Arten sind neu modelliert (props_hall/storage/machines/transit). Hier liegen die gemeinsamen Formen dafuer:
# gefaste Platten, weiche Koerper, Bretterlagen, Faesser, Drechselbeine, Beschlaege, Kerzen, Laternen, Dampf.

import random  # noqa: E402

S.PALETTE.update({
    "copper_dark": (0.62, 0.31, 0.20), "ember": (1.0, 0.36, 0.10), "soot": (0.23, 0.17, 0.18), "void": (0.10, 0.07, 0.09),
    "terracotta": (0.82, 0.46, 0.32), "terracotta_dark": (0.62, 0.32, 0.23), "straw": (0.91, 0.77, 0.43),
    "straw_dark": (0.74, 0.58, 0.28), "plum_cloth": (0.55, 0.31, 0.60), "mint_cloth": (0.66, 0.85, 0.75),
    "jelly": (0.86, 0.62, 0.96), "jelly_light": (0.96, 0.84, 1.0), "steam": (0.98, 0.96, 0.91),
    "paint_plum_dark": (0.36, 0.22, 0.37), "paint_coral_dark": (0.68, 0.35, 0.31), "paint_mint_dark": (0.40, 0.61, 0.53),
    "paint_cream_dark": (0.80, 0.72, 0.58), "glow_hot": (1.0, 0.97, 0.80), "glow_dim": (0.93, 0.60, 0.16),
    "bread": (0.86, 0.60, 0.27), "bread_dark": (0.66, 0.40, 0.17), "foam": (0.99, 0.97, 0.90),
})
S._KIND_OF.update({
    "copper_dark": "metal", "soot": "stone", "terracotta": "stone", "terracotta_dark": "stone", "straw": "cloth",
    "straw_dark": "cloth", "plum_cloth": "cloth", "mint_cloth": "cloth", "jelly": "gloss", "jelly_light": "gloss",
    "bread": "wax", "bread_dark": "wax", "foam": "cloth", "steam": "cloth",
})


def tint(ob, f):
    """Farbstich eines Teils (Zahl = Helligkeit, Tupel = RGB-Faktor); bleibt in finish() erhalten."""
    c = (f, f, f) if isinstance(f, (int, float)) else f
    me = ob.data
    a = me.color_attributes.get("tint") or me.color_attributes.new("tint", "FLOAT_COLOR", "CORNER")
    if len(a.data):
        a.data.foreach_set("color", [c[0], c[1], c[2], 1.0] * len(a.data))
    return ob


def noline(ob):
    """Teil ohne Freestyle-Linie (Dampf, Lichtpunkte, feine Aufmalungen)."""
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    S.nolines().objects.link(ob)
    return ob


def rrect(x0, y0, x1, y1, r, n=4):
    """Umriss eines Rechtecks mit runden Ecken (gegen den Uhrzeigersinn)."""
    r = max(0.001, min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4))
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def arc(cx, cz, r, a0, a1, n=12, rz=None):
    """Bogenpunkte (Grad), fuer Umrisse in der x/z- oder x/y-Ebene."""
    rz = r if rz is None else rz
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + rz * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def inset(pts, d):
    """Umriss um d nach innen versetzen (einfache Gehrung, fuer konvexe und fast konvexe Umrisse)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sg = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1, e2 = p1 - p0, p2 - p1
        if e1.length < 1e-9:
            e1 = e2
        if e2.length < 1e-9:
            e2 = e1
        n1 = Vector((-e1.y, e1.x)).normalized() * sg
        n2 = Vector((-e2.y, e2.x)).normalized() * sg
        m = n1 + n2
        if m.length < 1e-6:
            m = n1
        m.normalize()
        k = d / max(0.4, m.dot(n1))
        out.append((p1.x + m.x * k, p1.y + m.y * k))
    return out


def slab(pts, a0, a1, mat, bev=0.012, axis="z", both=False, rounded=False):
    """Platte ueber einem Umriss mit gefaster Kante. axis z: pts = (x, y), Fase oben (a1), both auch unten.
    axis y: pts = (x, z), a0 = Suedseite (gefast), a1 = Nordseite. axis x: pts = (y, z), Fase bei a1."""
    steps = ((0.5, 0.134), (0.866, 0.5), (1.0, 1.0)) if rounded else ((1.0, 1.0),)      # (Anteil Einzug, Anteil Hoehe)
    if axis == "y":
        a0, a1 = a1, a0                          # Fase liegt im Sueden, also von Norden her aufbauen
    sgn = 1.0 if a1 >= a0 else -1.0
    b = min(bev, abs(a1 - a0) * (0.45 if both else 0.9))
    lv = []
    if both:
        for fi, fh in reversed(steps):
            lv.append((b * fi, a0 + sgn * b * (1 - fh)))
        lv.append((0.0, a0 + sgn * b))
    else:
        lv.append((0.0, a0))
    lv.append((0.0, a1 - sgn * b))
    for fi, fh in steps:
        lv.append((b * fi, a1 - sgn * b * (1 - fh)))

    def p3(u, v, a):
        return (u, a, v) if axis == "y" else ((a, u, v) if axis == "x" else (u, v, a))
    loops = []
    for d, a in lv:
        q = inset(pts, d) if d > 0 else pts
        loops.append([p3(u, v, a) for u, v in q])
    return loft(loops, mat)


def bbox(x0, y0, z0, x1, y1, z1, mat, r=0.02, seg=2):
    """Quader mit runden Kanten (seg 1 = Fase, 2+ = weich)."""
    x0, x1, y0, y1, z0, z1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    r = min(r, 0.48 * min(x1 - x0, y1 - y0, z1 - z0))
    if r > 1e-4:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, affect="EDGES", profile=0.5)
    return add(S._obj(_nm("r"), bm, mat))


def soft(cx, cy, cz, rx, ry, rz, mat, k=0.5, seg=20):
    """Weicher Koerper zwischen Kugel (k = 0) und Quader (k = 1): Kissen, Saecke, Brotlaibe."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=1.0)
    for v in bm.verts:
        m = max(abs(v.co.x), abs(v.co.y), abs(v.co.z)) or 1.0
        p = v.co.lerp(v.co / m, k)
        v.co = Vector((cx + p.x * rx, cy + p.y * ry, cz + p.z * rz))
    return add(S._obj(_nm("o"), bm, mat))


def planks(x0, y0, z0, x1, y1, z1, mat, n, axis="x", gap=0.004, bev=0.006, var=0.07, seed=1):
    """Bretterlage: der Quader wird entlang axis in n Bretter geteilt, jedes leicht anders getoent."""
    rng = random.Random(seed)
    k = "xyz".index(axis)
    c = [min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1)]
    lo, hi = c[k], c[k + 3]
    w = (hi - lo) / n
    out = []
    for i in range(n):
        q = list(c)
        q[k], q[k + 3] = lo + i * w + gap / 2, lo + (i + 1) * w - gap / 2
        out.append(tint(box(*q, mat, bevel=bev), 1.0 + (rng.random() - 0.5) * 2 * var))
    return out


def stud(x, y, z, r=0.018, mat="brass", d="s"):
    """Nietkopf: s sitzt auf einer Suedflaeche, t auf einer Deckflaeche."""
    if d == "s":
        return sph(x, y, z, r, mat, seg=8, sy=0.6)
    return sph(x, y, z, r, mat, seg=8, sz=0.6)


def leg(x, y, z0, z1, r, mat="wood", seg=12, foot=None):
    """Gedrechseltes Bein: Fuss, Wulst, schlanker Schaft, Kopf."""
    h = z1 - z0
    prof = [(0, 0), (r * 0.62, 0), (r * 0.7, h * 0.1), (r * 1.1, h * 0.16), (r * 1.1, h * 0.2), (r * 0.72, h * 0.27),
            (r * 0.9, h * 0.62), (r * 1.15, h * 0.74), (r * 1.15, h * 0.79), (r * 0.8, h * 0.84), (r, h * 0.88), (r, h), (0, h)]
    ob = lathe(prof, mat, M=T(x, y, z0), seg=seg)
    if foot:
        cyl(x, y, z0, z0 + h * 0.06, r * 0.74, foot, seg=seg)
    return ob


def hoop(cx, cy, z, r, mat="iron", hh=0.05, t=0.014, M=None, seg=24):
    """Fassreifen / flacher Ring um die z-Achse; M = eigener Rahmen (dann zaehlen cx, cy nicht)."""
    return lathe([(r - t, -hh / 2), (r + t * 0.6, -hh / 2), (r + t * 0.6, hh / 2), (r - t, hh / 2)], mat,
                 M=(M if M is not None else T(cx, cy, 0)) @ T(0, 0, z), seg=seg, loop=True)


def barrel_r(r, t):
    """Fassradius auf relativer Hoehe t (Bauch in der Mitte)."""
    return r * (0.83 + 0.17 * math.sin(math.pi * min(1.0, max(0.0, t))) ** 0.8)


def barrel(cx, cy, z0, h, r, wood="wood", wood2="wood_light", band="iron", lid="wood_light", rim="wood_dark",
           hoops=(0.09, 0.33, 0.67, 0.91), seg=20, M=None):
    """Bauchiges Daubenfass mit eingelassenem Deckel und Reifen. Ohne M steht es bei (cx, cy, z0); mit M liegt die
    Fassachse auf der lokalen z-Achse (Deckel bei z = h)."""
    M = M if M is not None else T(cx, cy, z0)
    N = 8
    prof = [(barrel_r(r, i / N), h * i / N) for i in range(N + 1)]
    rt = prof[-1][0]
    full = [(0, 0)] + prof + [(rt - 0.04, h), (rt - 0.04, h - 0.045), (0, h - 0.045)]
    lathe(full, [wood, wood2, rim, lid], M=M, seg=seg, band=[0] * (N + 1) + [2, 2, 3], stripe=(0, 1))
    for t in hoops:
        hoop(0, 0, h * t, barrel_r(r, t) + 0.006, band, hh=0.07 if 0.2 < t < 0.8 else 0.08, t=0.02, M=M, seg=seg)
    return M


def chain(p0, p1, r=0.024, mat="iron"):
    p0, p1 = Vector(p0), Vector(p1)
    n = max(2, int((p1 - p0).length / (r * 2.4)))
    for i in range(n):
        c = p0.lerp(p1, (i + 0.5) / n)
        ob = add(S.torus(_nm("k"), 0, 0, 0, r, r * 0.34, mat, seg=10, ring=5))
        ob.data.transform(T(*c) @ aim(p1 - p0) @ R("Z", 90 * (i % 2)) @ R("X", 90) @ SC(1.0, 1.25, 1.0))


def candle(x, y, z, h, r=0.03, mat="wax_light", lit=True, halo=0.26):
    lathe([(0, 0), (r, 0), (r, h * 0.94), (r * 0.7, h), (0, h)], mat, M=T(x, y, z), seg=10)
    tube((x, y, z + h), (x, y, z + h + 0.022), 0.005, "ink", seg=4)
    if lit:
        flame(x, y, z + h + 0.016, h=0.075, r=0.027, halo=halo)


def lantern(x, y, z, s=1.0, lit=True, frame="brass", halo=0.36):
    """Sechseckige Laterne: Boden, Glaskoerper, sechs Stege, Dach, Tragring."""
    r = 0.085 * s
    hexp(x, y, r * 1.2, z, z + 0.03 * s, frame)
    g = hexp(x, y, r * 0.93, z + 0.03 * s, z + 0.2 * s, "amber_glass" if lit else "glass")
    if lit:
        flat(g)
        flat(lathe([(0, 0), (r * 0.36, 0.035 * s), (0, 0.12 * s)], "glow_hot", M=T(x, y - r * 0.95, z + 0.06 * s), seg=8))
    for px, py in S.hexagon_pts(x, y, r):
        tube((px, py, z + 0.03 * s), (px, py, z + 0.2 * s), 0.011 * s, frame, seg=5)
    lathe([(r * 1.3, 0), (r * 0.5, 0.075 * s), (r * 0.3, 0.085 * s), (0, 0.085 * s)], frame, M=T(x, y, z + 0.2 * s), seg=6)
    tor(x, y, z + 0.33 * s, 0.045 * s, 0.011 * s, frame, seg=12, ring=5, M=R("X", 90))
    if lit and halo:
        glow(x, y, z + 0.12 * s, halo * s, "glow", 0.5)


def puff(x, y, z, r, mat="steam"):
    """Dampf- oder Rauchwoelkchen aus drei Kugeln (unbeleuchtet)."""
    if r <= 0.005:
        return
    for dx, dz, k in ((0.0, 0.0, 1.0), (-0.75, -0.25, 0.68), (0.7, -0.18, 0.74)):
        flat(sph(x + dx * r, y, z + dz * r, r * k, mat, seg=10))


def drip(x, y, z, L, r=0.022, mat="honey"):
    """Tropfnase: Faden von z nach unten mit Tropfen."""
    tube((x, y, z), (x, y, z - L), r * 0.8, mat, seg=8, r1=r * 0.55)
    sph(x, y, z - L, r, mat, seg=8, sz=1.25)


def honeyjar(x, y, z, r, h, fill="honey", cap="cloth_cream", tie="rope", label=None):
    """Honigglas mit Schulter, Stoffhaube und Schnur; label = Farbe eines Etiketts oder None."""
    prof = [(0, 0), (r * 0.86, 0), (r, h * 0.08), (r, h * 0.58), (r * 0.92, h * 0.7), (r * 0.7, h * 0.78), (r * 0.7, h * 0.86),
            (0, h * 0.86)]
    lathe(prof, [fill, "glass"], M=T(x, y, z), seg=14, band=[0, 0, 0, 0, 1, 1, 1])
    lathe([(r * 0.92, h * 0.74), (r * 0.74, h * 0.84), (r * 0.8, h * 0.93), (r * 0.5, h), (0, h)], cap, M=T(x, y, z), seg=14)
    hoop(x, y, z + h * 0.84, r * 0.74, tie, hh=0.012, t=0.008, seg=14)
    if label:
        ext([(x - r * 0.5, z + h * 0.2), (x + r * 0.5, z + h * 0.2), (x + r * 0.5, z + h * 0.5), (x - r * 0.5, z + h * 0.5)],
            y - r - 0.004, y - r * 0.7, label)


def hexplate(x, z, r, y0, y1, mat, rot=0.0):
    """Sechseck-Schild auf einer Suedflaeche (von y0 bis y1)."""
    return ext(S.hexagon_pts(x, z, r, True, rot), y0, y1, mat)


def cyc(f, n):
    """0..1..0 ueber eine Schleife (nahtlos)."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * f / n)


# Farbkleid: die Neubauten nennen ihre Anstrichtoene direkt, ein Tausch je Art ist nicht mehr noetig.
SKIN = {}
