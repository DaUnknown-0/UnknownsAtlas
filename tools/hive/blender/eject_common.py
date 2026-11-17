# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# eject_common.py - Bausteine fuer die Amberhive-Rauswurf- und Skip-Szenen im Stil V2 "Bernsteinlicht" (art/STIL_V2.md).
# Nur in Blender importieren (ueber die eject_<szene>.py-Skripte).
#
# Kino-Schraegblick: die Szenen sind Seitenansichten, aber wie die Karte leicht von oben gesehen. Modelliert wird in
# Metern (x = rechts, y = Tiefe nach hinten, z = Hoehe); fin() schert jedes Teil mit z' = z + KZ * y und merkt sich die
# Normalen davor (wie hive_style.finish fuer die Karte). Dadurch sieht man Boeden und Deckflaechen (kuehle Boeden wie auf
# der Karte), Senkrechtes bleibt unverzerrt. Die Kamera steht vorne (Ortho, schaut nach +y).
# Bildkoordinaten = Szenen-Einheiten (1 = 180 px): Bild-x = x, Bild-y = z + KZ * y; img() rechnet um.
# Licht und Material kommen aus hive_style (Cel-Licht aus den Normalen, Pflaumenschatten, Glanz, AO); das Licht ist fuer
# den flacheren Blick nach vorn gekippt (Deckflaechen 1,0, Stirnseiten knapp 0,9, abgewandte Seiten Pflaume).
# render_layer()/render_bg() schreiben die Bilder nach assets/amberhive und die Lage nach art/eject/<name>.json;
# tools/eject_scenes.py liest diese Dateien (Positionen und Anker der Szenen).

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hive_style as H  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ASSETS = os.environ.get("HIVE_EJECT_OUT") or os.path.join(ATLAS, "assets", "amberhive")
ART = os.environ.get("HIVE_EJECT_OUT") or os.path.join(ATLAS, "tools", "hive", "art", "eject")
PPU = 180
KZ = 0.30                       # Kino-Schraegblick: 1 m Tiefe hebt das Bild um 0,30 Einheiten
LINE_OUT, LINE_IN = 0.024, 0.0095
BG_OUT, BG_IN = 0.019, 0.008
PLUM = (0.13, 0.07, 0.10)       # Schattenfarbe (wie hive_style.ground_shadow)
P = H.PALETTE

# Szenenskripte stellen den Stil fuer den Schraegblick von vorn ein, bevor das erste Material entsteht (STIL_V2.md)
H.GROUND_FADE = False
H.LIGHT = Vector((-0.42, -0.55, 0.72)).normalized()
H.VIEW = Vector((0.0, -1.0, KZ)).normalized()

# Toene, die nur die Szenen brauchen (Himmel, Ferne, Koenigin)
P.update({
    "cloud": (0.99, 0.96, 0.92), "cloud_eve": (1.0, 0.80, 0.74), "hill_far": (0.56, 0.70, 0.62), "hill_mid": (0.50, 0.68, 0.42),
    "hill_eve": (0.48, 0.32, 0.50), "hill_eve_b": (0.60, 0.38, 0.50), "sun": (1.0, 0.95, 0.72), "sun_eve": (1.0, 0.86, 0.56),
    "fur": (0.99, 0.96, 0.88), "blush": (0.97, 0.52, 0.52), "mouth": (0.62, 0.16, 0.20), "tongue": (0.96, 0.50, 0.55),
    "awn_a": (0.34, 0.62, 0.62), "awn_b": (0.94, 0.89, 0.77), "terracotta": (0.80, 0.45, 0.32),
})
H._KIND_OF.update({"cloud": "cloth", "cloud_eve": "cloth", "hill_far": "matte", "hill_mid": "leaf", "hill_eve": "matte",
                   "hill_eve_b": "matte", "fur": "cloth", "blush": "cloth", "mouth": "matte", "tongue": "wax", "awn_a": "cloth",
                   "awn_b": "cloth", "terracotta": "stone"})

OBJS = []                       # alle Teile seit dem letzten clear()
XF = [None]                     # XF[0] = Matrix: wird auf jedes neue Teil angewandt (ganze Baugruppen skalieren oder drehen)
_n = [0]


def nm(p="e"):
    _n[0] += 1
    return f"{p}{_n[0]}"


def img(x, y, z):
    """Modellpunkt -> Bildpunkt (Szenen-Einheiten)."""
    return (x, z + KZ * y)


def zat(zi, y):
    """Modellhoehe, die in Tiefe y auf der Bildhoehe zi erscheint."""
    return zi - KZ * y


def reset():
    sc = H.reset()
    os.makedirs(ART, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    del OBJS[:]
    return sc


def clear():
    """Alle Mesh-Objekte entfernen (zwischen zwei Ebenen eines Skripts)."""
    for ob in list(bpy.data.objects):
        if ob.type == "MESH":
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
    del OBJS[:]


def mark():
    return len(OBJS)


def since(m):
    return OBJS[m:]


# ------------------------------------------------------------------ Objekt anlegen, schattieren, scheren

def _mat(spec):
    if isinstance(spec, str) and ":" in spec:
        name, kind = spec.split(":")
        return H.material(name, kind)
    return H.material(spec)


def mk(name, bm, mats, nl=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (H.nolines() if nl else bpy.context.scene.collection).objects.link(ob)
    for m in (mats if isinstance(mats, (list, tuple)) and not _is_rgb(mats) else [mats]):
        me.materials.append(_mat(m))
    OBJS.append(ob)
    return ob


def _is_rgb(m):
    return isinstance(m, tuple) and len(m) == 3 and all(isinstance(v, (int, float)) for v in m)


def fin(ob, lit=True, tint=None, tintfn=None, smooth=H.SMOOTH_DEG, shear=True):
    """Farbstich setzen (tint = RGB-Faktor, tintfn(co) -> RGB je Punkt), Cel-Licht vorbereiten, scheren."""
    me = ob.data
    if tint is not None or tintfn is not None:
        a = me.color_attributes.get("tint")
        old = None
        if a is None:
            a = me.color_attributes.new("tint", "FLOAT_COLOR", "CORNER")
        else:
            old = [0.0] * (len(me.loops) * 4)
            a.data.foreach_get("color", old)
        vals = []
        for i, lp in enumerate(me.loops):
            c = tintfn(me.vertices[lp.vertex_index].co) if tintfn else tint
            if old:
                c = (c[0] * old[i * 4], c[1] * old[i * 4 + 1], c[2] * old[i * 4 + 2])
            vals.extend((c[0], c[1], c[2], 1.0))
        a.data.foreach_set("color", vals)
    H.finish(ob, shade=lit, shear=False, smooth=smooth)
    n = len(me.loops)
    if shear and n:
        normals = [0.0] * (n * 3)
        me.corner_normals.foreach_get("vector", normals)
        co = [0.0] * (len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        for i in range(0, len(co), 3):
            co[i + 2] += KZ * co[i + 1]
        me.vertices.foreach_set("co", co)
        me.normals_split_custom_set([tuple(normals[i:i + 3]) for i in range(0, len(normals), 3)])
        me.update()
    return ob


def _done(name, bm, mats, kw):
    nl = kw.pop("nl", False)
    M = kw.pop("M", None)
    if XF[0] is not None:
        M = XF[0] @ M if M is not None else XF[0]
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bm.normal_update()
    return fin(mk(name or nm(), bm, mats, nl), **kw)


def _tl(bm):
    return bm.loops.layers.float_color.get("tint") or bm.loops.layers.float_color.new("tint")


def _settint(f, lay, c):
    for lp in f.loops:
        lp[lay] = (c[0], c[1], c[2], 1.0)


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def about(M, c):
    return Matrix.Translation(c) @ M @ Matrix.Translation(-Vector(c))


def mix(a, b, t):
    a = P[a] if isinstance(a, str) else a
    b = P[b] if isinstance(b, str) else b
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ramp(stops, t):
    """stops = [(t, rgb), ...] aufsteigend."""
    if t <= stops[0][0]:
        return stops[0][1]
    for (ta, ca), (tb, cb) in zip(stops, stops[1:]):
        if t <= tb:
            return mix(ca, cb, (t - ta) / max(1e-6, tb - ta))
    return stops[-1][1]


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ Umrisse (2D)

def hex_pts(cx, cz, r, rot=0.0, flat=True):
    a0 = 0.0 if flat else math.pi / 6
    return [(cx + r * math.cos(a0 + rot + math.pi / 3 * i), cz + r * math.sin(a0 + rot + math.pi / 3 * i)) for i in range(6)]


def arc_pts(cx, cz, r, a0, a1, n, rz=None):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / (n - 1)), cz + (rz or r) * math.sin(a0 + (a1 - a0) * i / (n - 1)))
            for i in range(n)]


def ell_pts(cx, cz, rx, rz, n=32):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cz + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]


def round_rect(x0, z0, x1, z1, r, n=5):
    r = min(r, (x1 - x0) / 2, (z1 - z0) / 2)
    pts = []
    for cx, cz, a0 in ((x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180), (x1 - r, z0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def band_pts(pts, w, w1=None):
    """Polylinie zu einer Flaeche der Breite w (am Ende w1)."""
    left, right = [], []
    n = len(pts)
    for i, (x, z) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dz) or 1.0
        ww = w if w1 is None else w + (w1 - w) * i / (n - 1)
        nx, nz = -dz / ln * ww / 2, dx / ln * ww / 2
        left.append((x + nx, z + nz))
        right.append((x - nx, z - nz))
    return left + list(reversed(right))


def catmull(pts, n):
    """Punkte (beliebige Dimension) weich verbinden, n Stuecke je Abschnitt."""
    pts = [Vector(p) for p in pts]
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(0, i - 1)], pts[i], pts[i + 1], pts[min(len(pts) - 1, i + 2)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out


# ------------------------------------------------------------------ Koerper

def slab(pts, y0, y1, mat, bevel=0.0, seg=2, name=None, **kw):
    """Umriss (x, z) als Platte zwischen den Tiefen y0 (vorne) und y1 (hinten); bevel rundet die Vorderkante."""
    bm = bmesh.new()
    f = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    ff = bm.faces.new(f)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], b[i], b[j], f[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(ff.edges), offset=bevel, segments=seg, affect="EDGES", profile=0.5)
    return _done(name, bm, mat, kw)


def prism(pts, z0, z1, mat, bevel=0.0, seg=2, name=None, **kw):
    """Grundriss (x, y) als senkrechtes Prisma; bevel rundet die Oberkante."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(lo)
    ft = bm.faces.new(list(reversed(hi)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], hi[i], hi[j], lo[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(ft.edges), offset=bevel, segments=seg, affect="EDGES", profile=0.5)
    return _done(name, bm, mat, kw)


def box(x0, x1, y0, y1, z0, z1, mat, bevel=0.0, seg=2, name=None, **kw):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=seg, affect="EDGES", profile=0.5)
    return _done(name, bm, mat, kw)


def ellipsoid(c, r, mat, seg=32, matfn=None, rot=None, name=None, **kw):
    """Ellipsoid um c mit Radien r (Zahl oder Tripel). matfn(Einheitspunkt) -> Materialindex. rot = Matrix (um c)."""
    if not isinstance(r, (tuple, list)):
        r = (r, r, r)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=1.0)
    if matfn:
        for fc in bm.faces:
            fc.material_index = matfn(fc.calc_center_median())
    M = Matrix.Diagonal((r[0], r[1], r[2], 1.0))
    if rot is not None:
        M = rot.to_4x4() @ M
    M = Matrix.Translation(c) @ M
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return _done(name, bm, mat, kw)


def ball(c, r, mat, seg=24, **kw):
    return ellipsoid(c, r, mat, seg, **kw)


def lathe(prof, c, mat, seg=32, axis="z", matfn=None, scale=(1.0, 1.0), caps=True, arc=None, name=None, **kw):
    """Drehkoerper: prof = [(Radius, Hoehe)], c = Fusspunkt. axis z: steht; y: Achse in die Tiefe; x: liegt quer.
    matfn(i, r, h) -> Materialindex je Profilstueck. scale = Stauchung der beiden Radialrichtungen.
    arc = (a0, a1) dreht nur ueber diesen Winkelbereich (offen, ohne Deckel)."""
    bm = bmesh.new()
    rings = []
    ncol = seg + 1 if arc else seg
    if arc:
        caps = False
    for r, h in prof:
        ring = []
        for k in range(ncol):
            a = arc[0] + (arc[1] - arc[0]) * k / seg if arc else 2 * math.pi * k / seg
            u, v = max(r, 1e-4) * math.cos(a) * scale[0], max(r, 1e-4) * math.sin(a) * scale[1]
            if axis == "z":
                p = (c[0] + u, c[1] + v, c[2] + h)
            elif axis == "y":
                p = (c[0] + u, c[1] + h, c[2] + v)
            else:
                p = (c[0] + h, c[1] + u, c[2] + v)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for i in range(len(rings) - 1):
        mi = matfn(i, prof[i][0], prof[i][1]) if matfn else 0
        for k in range(seg):
            j = k + 1 if arc else (k + 1) % seg
            f = bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
            f.material_index = mi
    if caps:
        f0 = bm.faces.new(list(reversed(rings[0])))
        f1 = bm.faces.new(rings[-1])
        if matfn:
            f0.material_index = matfn(0, prof[0][0], prof[0][1])
            f1.material_index = matfn(len(prof) - 2, prof[-1][0], prof[-1][1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    else:                                               # offener Ring: Normalen von der Profilmitte weg
        bm.normal_update()
        mr = sum(r for r, h in prof) / len(prof)
        mh = sum(h for r, h in prof) / len(prof)
        for f in bm.faces:
            cc = f.calc_center_median()
            if axis == "z":
                rr, hh, rad = math.hypot(cc.x - c[0], cc.y - c[1]), cc.z - c[2], Vector((cc.x - c[0], cc.y - c[1], 0))
                ax = Vector((0, 0, 1))
            elif axis == "y":
                rr, hh, rad = math.hypot(cc.x - c[0], cc.z - c[2]), cc.y - c[1], Vector((cc.x - c[0], 0, cc.z - c[2]))
                ax = Vector((0, 1, 0))
            else:
                rr, hh, rad = math.hypot(cc.y - c[1], cc.z - c[2]), cc.x - c[0], Vector((0, cc.y - c[1], cc.z - c[2]))
                ax = Vector((1, 0, 0))
            out = rad.normalized() * (rr - mr) + ax * (hh - mh)
            if f.normal.dot(out) < 0:
                f.normal_flip()
    return _done(name, bm, mat, kw)


def cyl(cx, cy, z0, z1, r, mat, seg=24, r1=None, bevel=0.0, **kw):
    """Stehender Zylinder oder Kegelstumpf, bevel bricht Ober- und Unterkante."""
    r1 = r if r1 is None else r1
    b = min(bevel, (z1 - z0) / 2)
    prof = [(r - b, 0.0), (r, b), (r1, z1 - z0 - b), (r1 - b, z1 - z0)] if b > 0 else [(r, 0.0), (r1, z1 - z0)]
    return lathe(prof, (cx, cy, z0), mat, seg=seg, **kw)


def tube(pts, r, mat, seg=10, r1=None, rfn=None, sm=0, cap=True, name=None, **kw):
    """Schlauch entlang der Punkte (3D). sm > 0 glaettet (Catmull-Rom), rfn(u) -> Radius, cap = runde Enden."""
    pts = [Vector(p) for p in pts]
    if sm:
        pts = catmull(pts, sm)
    n = len(pts)

    def rad(u):
        return rfn(u) if rfn else r + ((r if r1 is None else r1) - r) * u
    st = [(pts[i], rad(i / (n - 1))) for i in range(n)]
    if cap:
        t0 = (pts[0] - pts[1]).normalized()
        t1 = (pts[-1] - pts[-2]).normalized()
        pre = [(pts[0] + t0 * st[0][1] * math.sin(a), st[0][1] * math.cos(a)) for a in (1.45, 1.0, 0.5)]
        post = [(pts[-1] + t1 * st[-1][1] * math.sin(a), st[-1][1] * math.cos(a)) for a in (0.5, 1.0, 1.45)]
        st = pre + st + post
    m = len(st)
    bm = bmesh.new()
    rings = []
    nrm = None
    prev_t = None
    for i in range(m):
        t = (st[min(i + 1, m - 1)][0] - st[max(i - 1, 0)][0]).normalized()
        if nrm is None:
            ref = Vector((0, 1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(ref).normalized()
        else:
            ax = prev_t.cross(t)
            if ax.length > 1e-7:
                nrm = Matrix.Rotation(prev_t.angle(t), 3, ax.normalized()) @ nrm
            nrm = (nrm - t * nrm.dot(t)).normalized()
        prev_t = t
        bn = t.cross(nrm).normalized()
        c, rr = st[i]
        rings.append([bm.verts.new(c + (nrm * math.cos(2 * math.pi * k / seg) + bn * math.sin(2 * math.pi * k / seg)) * rr)
                      for k in range(seg)])
    for i in range(m - 1):
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _done(name, bm, mat, kw)


def torus(c, Rr, r, mat, seg=40, ring=10, axis="y", scale=(1.0, 1.0), name=None, **kw):
    """Ring um die Achse (y = Ring steht dem Betrachter zugewandt, z = liegt flach)."""
    bm = bmesh.new()
    vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(ring):
            b = 2 * math.pi * j / ring
            u, v, w = (Rr + r * math.cos(b)) * math.cos(a) * scale[0], (Rr + r * math.cos(b)) * math.sin(a) * scale[1], r * math.sin(b)
            p = (c[0] + u, c[1] + w, c[2] + v) if axis == "y" else ((c[0] + u, c[1] + v, c[2] + w) if axis == "z"
                                                                    else (c[0] + w, c[1] + u, c[2] + v))
            row.append(bm.verts.new(p))
        vs.append(row)
    for i in range(seg):
        for j in range(ring):
            bm.faces.new((vs[i][j], vs[(i + 1) % seg][j], vs[(i + 1) % seg][(j + 1) % ring], vs[i][(j + 1) % ring]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _done(name, bm, mat, kw)


def sheet(fn, nu, nv, mat, thick=0.0, matfn=None, name=None, **kw):
    """Flaeche aus fn(u, v) -> (x, y, z), u und v in 0..1 (Vorhaenge, Blaetter, Fluegel). thick > 0 gibt ihr Staerke."""
    bm = bmesh.new()
    g = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
            if matfn:
                f.material_index = matfn((i + 0.5) / nu, (j + 0.5) / nv)
    bm.normal_update()
    if sum(f.normal.y - KZ * f.normal.z for f in bm.faces) > 0:        # zur Kamera drehen
        for f in bm.faces:
            f.normal_flip()
    if thick > 0:
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thick)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _done(name, bm, mat, kw)


def face(pts3, mat, name=None, **kw):
    """Ebenes Vieleck aus 3D-Punkten, dem Betrachter zugewandt."""
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new(p) for p in pts3])
    bm.normal_update()
    if f.normal.y - KZ * f.normal.z > 0:
        f.normal_flip()
    return _done(name, bm, mat, kw)


def panel(x0, z0, x1, z1, y, mat, nx=1, nz=1, name=None, **kw):
    """Senkrechte Wandflaeche (fuer Verlaeufe ueber tintfn fein genug unterteilen)."""
    return sheet(lambda u, v: (x0 + (x1 - x0) * u, y, z0 + (z1 - z0) * v), nx, nz, mat, name=name, **kw)


def ground(x0, y0, x1, y1, z, mat, nx=1, ny=1, name=None, **kw):
    """Waagrechte Flaeche (Boden, Seespiegel)."""
    kw.setdefault("nl", True)
    return sheet(lambda u, v: (x0 + (x1 - x0) * u, y0 + (y1 - y0) * v, z), nx, ny, mat, name=name, **kw)


def drip(x, y, z, ln, w, mat="honey", seg=14, **kw):
    """Honignase: haengt von z nach unten (Laenge ln bis zur Tropfenmitte), endet in einem Tropfen der Breite w."""
    r = w / 2
    ln = max(ln, 3.2 * r)
    prof = [(0.0, -ln - r), (0.72 * r, -ln - 0.7 * r), (r, -ln), (0.8 * r, -ln + 0.7 * r), (0.5 * r, -ln + 1.5 * r),
            (0.42 * r, -ln * 0.5), (0.62 * r, -ln * 0.16), (1.25 * r, 0.0)]
    return lathe(prof, (x, y, z), mat, seg=seg, **kw)


# ------------------------------------------------------------------ Waben, Boeden

def hex_grid(u0, v0, u1, v1, r):
    """Mittelpunkte flach liegender Sechsecke (Spitzen links und rechts), die das Rechteck ueberdecken."""
    out = []
    dx, dz = 1.5 * r, math.sqrt(3) * r
    i = 0
    u = u0
    while u < u1 + r:
        v = v0 + (dz / 2 if i % 2 else 0.0)
        while v < v1 + dz / 2:
            out.append((u, v))
            v += dz
        u += dx
        i += 1
    return out


def hexfield(cells, r, place, mats, pick=None, inset=0.86, inner=0.74, depth=0.05, tintfn=None, var=0.0, seed=1, flat_n=None,
             name=None, **kw):
    """Wabenrelief: je Zelle ein Rand (mats[0]) und ein vertiefter Zellboden (pick(i, u, v) -> Index in mats).
    place(u, v, d) -> 3D-Punkt (d = Tiefe der Vertiefung). tintfn(u, v) -> Farbstich, var = Helligkeitsstreuung je Zelle."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = _tl(bm)
    for i, (cu, cv) in enumerate(cells):
        o = [(cu + r * math.cos(math.pi / 3 * k), cv + r * math.sin(math.pi / 3 * k)) for k in range(6)]
        a = [(cu + r * inset * math.cos(math.pi / 3 * k), cv + r * inset * math.sin(math.pi / 3 * k)) for k in range(6)]
        b = [(cu + r * inner * math.cos(math.pi / 3 * k), cv + r * inner * math.sin(math.pi / 3 * k)) for k in range(6)]
        vo = [bm.verts.new(place(u, v, 0.0)) for u, v in o]
        va = [bm.verts.new(place(u, v, 0.0)) for u, v in a]
        vb = [bm.verts.new(place(u, v, depth)) for u, v in b]
        t = tintfn(cu, cv) if tintfn else (1.0, 1.0, 1.0)
        k2 = 1.0 + (rnd.random() - 0.5) * 2 * var
        tc = (t[0] * k2, t[1] * k2, t[2] * k2)
        mi = pick(i, cu, cv) if pick else min(1, len(mats) - 1)
        for k in range(6):
            j = (k + 1) % 6
            f = bm.faces.new((vo[k], vo[j], va[j], va[k]))
            _settint(f, lay, t)
            f = bm.faces.new((va[k], va[j], vb[j], vb[k]))
            f.material_index = mi
            _settint(f, lay, tc)
        f = bm.faces.new(vb)
        f.material_index = mi
        _settint(f, lay, tc)
    bm.normal_update()
    ref = flat_n or Vector((0, -1, KZ))
    if sum(f.normal.dot(ref) for f in bm.faces) < 0:
        for f in bm.faces:
            f.normal_flip()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    kw.setdefault("nl", True)
    return _done(name, bm, mats, kw)


def wall_place(y):
    """place-Funktion fuer hexfield: senkrechte Wand in Tiefe y (u = x, v = z)."""
    return lambda u, v, d: (u, y + d, v)


def clip_poly(pts, planes):
    """Vieleck (x, y) auf den Schnitt der Halbebenen a*x + b*y <= c kuerzen."""
    for a, b, c in planes:
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            dp, dq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
            if dp <= 0:
                out.append(p)
            if (dp < 0 < dq) or (dq < 0 < dp):
                t = dp / (dp - dq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        pts = out
        if len(pts) < 3:
            return []
    return pts


def _inset(pts, d):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for x, y in pts:
        ln = math.hypot(x - cx, y - cy) or 1.0
        k = max(0.0, (ln - d) / ln)
        out.append((cx + (x - cx) * k, cy + (y - cy) * k))
    return out


def tiles(polys, z, mats, joint="fl_joint", gap=0.03, var=0.06, seed=3, planes=None, base=None, tintfn=None, name=None, **kw):
    """Bodenbelag ohne Linien: Fliesen (Liste von Vielecken x, y) mit Fugenabstand, Helligkeitsstreuung je Fliese,
    darunter der Fugengrund (base = Vieleck, sonst das Rechteck um alle Fliesen)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    lay = _tl(bm)
    allp = []
    for poly in polys:
        if planes:
            poly = clip_poly(poly, planes)
        if len(poly) < 3:
            continue
        allp += poly
        k = 1.0 + (rnd.random() - 0.5) * 2 * var
        mi = 1 + rnd.randrange(len(mats))
        cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
        t = tintfn(cx, cy) if tintfn else (1.0, 1.0, 1.0)
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in _inset(poly, gap * 0.5 * 1.3)])
        f.material_index = mi
        _settint(f, lay, (t[0] * k, t[1] * k, t[2] * k))
    if not allp:
        bm.free()
        return None
    if base is None:
        x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp)
        y0, y1 = min(p[1] for p in allp), max(p[1] for p in allp)
        base = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if base:
        n = 8
        bx0, bx1 = min(p[0] for p in base), max(p[0] for p in base)
        by0, by1 = min(p[1] for p in base), max(p[1] for p in base)
        for i in range(n):                                  # Fugengrund in Streifen, damit tintfn auch ihn faerbt
            for j in range(n):
                q = [(bx0 + (bx1 - bx0) * i / n, by0 + (by1 - by0) * j / n), (bx0 + (bx1 - bx0) * (i + 1) / n, by0 + (by1 - by0) * j / n),
                     (bx0 + (bx1 - bx0) * (i + 1) / n, by0 + (by1 - by0) * (j + 1) / n), (bx0 + (bx1 - bx0) * i / n, by0 + (by1 - by0) * (j + 1) / n)]
                q = clip_poly(q, _planes_of(base))
                if len(q) < 3:
                    continue
                f = bm.faces.new([bm.verts.new((x, y, z - 0.006)) for x, y in q])
                t = tintfn(sum(p[0] for p in q) / len(q), sum(p[1] for p in q) / len(q)) if tintfn else (1.0, 1.0, 1.0)
                _settint(f, lay, t)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    kw.setdefault("nl", True)
    return _done(name, bm, [joint] + list(mats), kw)


def _planes_of(poly):
    """Halbebenen eines konvexen Vielecks (beliebiger Umlaufsinn)."""
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    sgn = 1.0 if area > 0 else -1.0
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a, b = (q[1] - p[1]) * sgn, -(q[0] - p[0]) * sgn
        out.append((a, b, a * p[0] + b * p[1]))
    return out


def flats(polys, z, mat, planes=None, tintfn=None, name=None, **kw):
    """Flache Vielecke (x, y) auf Hoehe z in einem Netz (Fugengrund, Einlagen), optional auf Halbebenen gekuerzt."""
    bm = bmesh.new()
    lay = _tl(bm)
    for poly in polys:
        if planes:
            poly = clip_poly(poly, planes)
        if len(poly) < 3:
            continue
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in poly])
        cx, cy = sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)
        _settint(f, lay, tintfn(cx, cy) if tintfn else (1.0, 1.0, 1.0))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    kw.setdefault("nl", True)
    return _done(name, bm, mat, kw)


def sector_tiles(cx, cy, r0, r1, n, a_off=0.0, sub=4):
    """Radiale Platten eines Kranzes um (cx, cy)."""
    out = []
    for i in range(n):
        a0, a1 = a_off + 2 * math.pi * i / n, a_off + 2 * math.pi * (i + 1) / n
        inner = [(cx + r0 * math.cos(a0 + (a1 - a0) * k / sub), cy + r0 * math.sin(a0 + (a1 - a0) * k / sub)) for k in range(sub + 1)]
        outer = [(cx + r1 * math.cos(a1 - (a1 - a0) * k / sub), cy + r1 * math.sin(a1 - (a1 - a0) * k / sub)) for k in range(sub + 1)]
        out.append(inner + outer)
    return out


def hex_tiles(x0, y0, x1, y1, r):
    return [[(cx + r * math.cos(math.pi / 3 * k), cy + r * math.sin(math.pi / 3 * k)) for k in range(6)]
            for cx, cy in hex_grid(x0, y0, x1, y1, r)]


def rect_tiles(x0, y0, x1, y1, tw, td, stagger=0.5, jitter=0.0, seed=5):
    """Steinplatten oder Dielen: Reihen der Tiefe td, Platten der Laenge tw (jitter streut die Laenge)."""
    rnd = random.Random(seed)
    out = []
    y = y0
    row = 0
    while y < y1 - 1e-6:
        x = x0 - (tw * stagger * (row % 2)) - rnd.random() * tw * jitter
        while x < x1:
            w = tw * (1.0 + (rnd.random() - 0.5) * 2 * jitter)
            a, b = max(x, x0), min(x + w, x1)
            if b - a > 0.02:
                out.append([(a, y), (b, y), (b, min(y + td, y1)), (a, min(y + td, y1))])
            x += w
        y += td
        row += 1
    return out


# ------------------------------------------------------------------ Weiches: Schatten und Lichthoefe (ohne Linie)

_FALL = ((0.0, 1.0), (0.3, 0.86), (0.55, 0.5), (0.8, 0.16), (1.0, 0.0))


def soft(outline, grow, color, strength, plane="wall", at=0.0, center=None, name=None):
    """Weicher Fleck. plane 'wall': Umriss (x, z) in Tiefe at; plane 'floor': Umriss (x, y) auf Hoehe at.
    Kern deckt voll, laeuft ueber grow nach aussen auf null aus. Liegt in der Sammlung nolines."""
    cx = center[0] if center else sum(p[0] for p in outline) / len(outline)
    cy = center[1] if center else sum(p[1] for p in outline) / len(outline)
    bm = bmesh.new()
    lay = bm.loops.layers.float_color.new("a")

    def P3(u, v):
        return (u, at, v + KZ * at) if plane == "wall" else (u, v, at + KZ * v)
    rings = []
    for t, a in _FALL:
        ring = []
        for x, y in outline:
            d = math.hypot(x - cx, y - cy) or 1e-6
            k = (d + grow * (t * 1.6 - 0.6)) / d if t > 0 else max(0.05, (d - grow * 0.6) / d)
            ring.append(bm.verts.new(P3(cx + (x - cx) * k, cy + (y - cy) * k)))
        rings.append((ring, a))
    f = bm.faces.new(list(reversed(rings[0][0])))
    for lp in f.loops:
        lp[lay] = (1, 1, 1, 1)
    n = len(outline)
    for (r0, a0), (r1, a1) in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            for lp, a in zip(f.loops, (a0, a0, a1, a1)):
                lp[lay] = (a, a, a, 1)
    bm.normal_update()
    name = name or nm("soft")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    col = P[color] if isinstance(color, str) else color
    me.materials.append(H.soft_material(f"ej_{col}_{strength}", col, strength))
    ob = bpy.data.objects.new(name, me)
    H.nolines().objects.link(ob)
    OBJS.append(ob)
    return ob


def fade(x0, x1, v0, v1, color, strength, plane="floor", at=0.0, n=6, name=None):
    """Weicher Streifen von x0 bis x1: volle Deckkraft an der Kante v0, null bei v1.
    plane 'floor': v = Tiefe y auf Hoehe at; plane 'wall': v = Hoehe z in Tiefe at."""
    bm = bmesh.new()
    lay = bm.loops.layers.float_color.new("a")

    def P3(u, v):
        return (u, at, v + KZ * at) if plane == "wall" else (u, v, at + KZ * v)
    rows = [(bm.verts.new(P3(x0, v0 + (v1 - v0) * i / n)), bm.verts.new(P3(x1, v0 + (v1 - v0) * i / n)), (1 - i / n) ** 2)
            for i in range(n + 1)]
    for (a0, b0, al0), (a1, b1, al1) in zip(rows, rows[1:]):
        f = bm.faces.new((a0, b0, b1, a1))
        for lp, al in zip(f.loops, (al0, al0, al1, al1)):
            lp[lay] = (al, al, al, 1)
    name = name or nm("fade")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    col = P[color] if isinstance(color, str) else color
    me.materials.append(H.soft_material(f"ej_{col}_{strength}", col, strength))
    ob = bpy.data.objects.new(name, me)
    H.nolines().objects.link(ob)
    OBJS.append(ob)
    return ob


def annulus(cx, cz, r0, r1, y, mat, seg=64, nr=3, name=None, **kw):
    """Flacher Ring auf einer Wand in Tiefe y (u. a. als Fuellung hinter Wabenrelief rund um eine Oeffnung)."""
    kw.setdefault("nl", True)
    return sheet(lambda u, v: (cx + (r0 + (r1 - r0) * v) * math.cos(2 * math.pi * u), y, cz + (r0 + (r1 - r0) * v) * math.sin(2 * math.pi * u)),
                 seg, nr, mat, name=name, **kw)


def gshadow(cx, cy, rx, ry, z, strength=0.36, grow=None):
    """Bodenschatten: Ellipse auf Hoehe z, faellt nach rechts vorn."""
    pts = [(cx + 0.06 + rx * math.cos(2 * math.pi * i / 24), cy - 0.05 + ry * math.sin(2 * math.pi * i / 24)) for i in range(24)]
    return soft(pts, grow or min(rx, ry) * 0.9 + 0.08, PLUM, strength, plane="floor", at=z + 0.004)


def wshadow(cx, cz, rx, rz, y, strength=0.28, grow=None, dx=0.12, dz=-0.1):
    """Schatten auf einer Wand in Tiefe y (knapp davor), faellt nach rechts unten."""
    pts = ell_pts(cx + dx, cz + dz, rx, rz, 24)
    return soft(pts, grow or min(rx, rz) * 0.9 + 0.1, PLUM, strength, plane="wall", at=y - 0.004)


def halo(cx, cz, r, y, color="glow", strength=0.5, rz=None):
    """Lichthof auf einer senkrechten Ebene in Tiefe y."""
    core = 0.3
    pts = ell_pts(cx, cz, r * core, (rz or r) * core, 24)
    return soft(pts, r * (1 - core), color, strength, plane="wall", at=y, center=(cx, cz))


# ------------------------------------------------------------------ Verlaeufe (Himmel, Honigtiefe): unbeleuchtet, ungeschert

def grad_material():
    m = bpy.data.materials.get("ej_grad")
    if m:
        return m
    m = bpy.data.materials.new("ej_grad")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "col"
    nt.links.new(attr.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def grad_plane(x0, z0, x1, z1, y, colfn, nx=24, nz=24, clip=None, name=None):
    """Senkrechte Flaeche in Tiefe y in BILD-Koordinaten (wird nicht geschert), Farbe je Ecke aus colfn(x, z) -> sRGB."""
    name = name or nm("grad")
    bm = bmesh.new()
    grid = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y, z0 + (z1 - z0) * j / nz)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz):
            if clip and not clip(x0 + (x1 - x0) * (i + 0.5) / nx, z0 + (z1 - z0) * (j + 0.5) / nz):
                continue
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    H.nolines().objects.link(ob)
    me.materials.append(grad_material())
    attr = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            attr.data[li].color = (*H.lin(colfn(co.x, co.z)), 1.0)
    me.update()
    OBJS.append(ob)
    return ob


# ------------------------------------------------------------------ Biene (Seitenansicht, schaut nach +x)

def bee(s=1.0, o=(0.0, 0.0, 0.0), eye=True, legs=True):
    """Arbeitsbiene ohne Fluegel. Ursprung = Mitte des Bruststuecks. Laenge etwa 0,95 * s."""
    def Q(x, y, z):
        return (o[0] + x * s, o[1] + y * s, o[2] + z * s)

    n = 30
    prof = []
    for i in range(n + 1):
        t = -1 + 2 * i / n
        prof.append((0.225 * s * math.sqrt(max(0.0, 1 - t * t)) * (0.86 + 0.14 * t), 0.31 * s * (t + 1)))

    def stripes(i, r, h):
        t = -1 + 2 * (i + 0.5) / n
        return 1 if t < -0.84 or -0.56 < t < -0.26 or 0.04 < t < 0.34 else 0
    tilt = about(R("Y", -13), Q(-0.02, 0.0, -0.02))     # Hinterleib haengt leicht nach unten
    lathe(prof, Q(-0.64, 0.0, -0.04), ["bee_yellow", "bee_black"], seg=32, axis="x", matfn=stripes, M=tilt)
    lathe([(0.04 * s, 0.0), (0.026 * s, 0.05 * s), (0.0, 0.12 * s)], Q(-0.63, 0.0, -0.04), "bee_black", seg=10, axis="x",
          M=tilt @ about(R("Y", 180), Q(-0.63, 0.0, -0.04)))
    ellipsoid(Q(0.02, 0.0, 0.03), (0.185 * s, 0.18 * s, 0.185 * s), "bee_yellow", seg=32, tint=(1.0, 0.86, 0.62))     # Pelz
    for k in range(7):                                   # Pelzkragen am Hals
        a = math.radians(-75 + 25 * k)
        ball(Q(0.135 + 0.025 * math.cos(a), -0.105 + 0.04 * abs(math.sin(a)), 0.035 + 0.15 * math.sin(a)), 0.042 * s, "fur", seg=10)
    ellipsoid(Q(0.28, -0.01, 0.07), (0.165 * s, 0.16 * s, 0.17 * s), "bee_black", seg=32)
    if eye:
        ellipsoid(Q(0.33, -0.135, 0.095), (0.082 * s, 0.035 * s, 0.092 * s), "white", seg=24, lit=False)
        ellipsoid(Q(0.355, -0.165, 0.09), (0.045 * s, 0.018 * s, 0.056 * s), "black", seg=18)
        ball(Q(0.372, -0.19, 0.118), 0.017 * s, "white", seg=10, lit=False)
        ellipsoid(Q(0.27, -0.15, 0.0), (0.04 * s, 0.015 * s, 0.026 * s), "blush", seg=12, lit=False)
    for k, dy in enumerate((-0.07, 0.07)):
        tube([Q(0.30, dy, 0.21), Q(0.33, dy, 0.32), Q(0.42, dy, 0.39), Q(0.50, dy, 0.38)], 0.015 * s, "bee_black", seg=8, sm=4)
        ball(Q(0.50, dy, 0.38), 0.034 * s, "bee_black", seg=12)
    if legs:
        for k, (lx, dy, fw) in enumerate(((-0.08, -0.1, -0.04), (0.03, -0.11, 0.0), (0.13, -0.1, 0.07))):
            tube([Q(lx, dy, -0.10), Q(lx + fw * 0.4, dy - 0.03, -0.22), Q(lx + fw + 0.03, dy - 0.03, -0.31)], 0.019 * s, "bee_black",
                 seg=8, r1=0.013 * s, sm=3)
            ball(Q(lx + fw + 0.04, dy - 0.03, -0.32), 0.026 * s, "bee_black", seg=10)


def wing(s=1.0, o=(0.0, 0.0, 0.0), rot=0.0):
    """Senkrechter Fluegel, Wurzel bei o, zeigt nach oben (rot in Grad gegen den Uhrzeigersinn)."""
    ra = math.radians(rot)

    def tr(px, pz):
        return (o[0] + (px * math.cos(ra) - pz * math.sin(ra)) * s, o[2] + (px * math.sin(ra) + pz * math.cos(ra)) * s)
    pts = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        px, pz = 0.115 * math.cos(a), 0.22 + 0.22 * math.sin(a)
        px *= 0.55 + 0.75 * (pz / 0.44)                 # Tropfenform: an der Wurzel schmal
        pts.append(tr(px, pz))
    slab(pts, o[1], o[1] + 0.012, "wing", bevel=0.004, seg=1, tint=(1.0, 1.0, 1.0))
    for (a, b) in (((0.0, 0.03), (0.0, 0.38)), ((0.0, 0.14), (0.07, 0.33)), ((0.0, 0.12), (-0.065, 0.31))):
        slab(band_pts([tr(*a), tr(*b)], 0.011 * s, 0.006 * s), o[1] - 0.004, o[1], "iron_light", nl=True, lit=False)


def bee_far():
    """Ferne Biene samt Fluegeln (Partikelbild)."""
    bee(legs=False)
    wing(o=(0.0, -0.02, 0.14), rot=24)
    wing(s=0.82, o=(-0.07, 0.2, 0.13), rot=46)


def render_bee_set():
    """Gemeinsame Bienenbilder: Koerper (schaut nach rechts, links per flip), Fluegel, ferne Biene."""
    clear()
    bee()
    render_layer("bee", pivot=(0.0, 0.0, 0.0))
    clear()
    wing()
    render_layer("wing", pivot=(0.0, 0.0, 0.0), line=0.017, inner=0.008)
    clear()
    bee_far()
    render_layer("bee_far", pivot=(0.0, 0.0, 0.0), line=0.03, inner=0.012)
    clear()


# ------------------------------------------------------------------ Rendern

def _bounds(objs):
    xs, zs = [], []
    for ob in objs:
        for v in ob.data.vertices:
            xs.append(v.co.x)
            zs.append(v.co.z)
    return min(xs), min(zs), max(xs), max(zs)


def _camera(cx, cz, w, h):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("ej_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w, h)
    cd.sensor_fit = "AUTO"
    cd.clip_start, cd.clip_end = 1.0, 600.0
    cam = bpy.data.objects.new("ej_cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (cx, -200.0, cz)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    sc.camera = cam
    return cam, cd


def _lines(line, inner):
    sc = bpy.context.scene
    sc.render.line_thickness = 1.0
    for ls in sc.view_layers[0].freestyle_settings.linesets:
        ls.linestyle.thickness = max(1.0, (line if ls.name == "outer" else inner) * PPU)


def _show(objs):
    keep = set(o.name for o in objs)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.hide_render = ob.name not in keep


def render_layer(name, objs=None, pad=0.06, line=LINE_OUT, inner=LINE_IN, pivot=None, bounds=None):
    """Ebene (PNG mit Alpha) nach assets/amberhive/task_eject_hive_<name>.png. pivot = Modellpunkt (x, y, z) des Ankers.
    bounds = (x0, y0, x1, y1) im Bild erzwingt den Ausschnitt (gleiche Groesse fuer Bildfolgen)."""
    sc = bpy.context.scene
    objs = list(OBJS) if objs is None else objs
    x0, z0, x1, z1 = bounds if bounds else _bounds(objs)
    if not bounds:
        x0, z0, x1, z1 = x0 - pad, z0 - pad, x1 + pad, z1 + pad
    w_px = max(4, int(math.ceil((x1 - x0) * PPU / 2.0 - 1e-6)) * 2)
    h_px = max(4, int(math.ceil((z1 - z0) * PPU / 2.0 - 1e-6)) * 2)
    x1, z1 = x0 + w_px / PPU, z0 + h_px / PPU
    cam, cd = _camera((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w_px, h_px, 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.compression = 90
    _lines(line, inner)
    _show(objs)
    path = os.path.join(ASSETS, f"task_eject_hive_{name}.png")
    H.render_to(path)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cd)
    meta = {"sprite": os.path.basename(path), "w": w_px, "h": h_px, "x0": round(x0, 4), "y0": round(z0, 4), "x1": round(x1, 4),
            "y1": round(z1, 4), "cx": round((x0 + x1) / 2, 4), "cy": round((z0 + z1) / 2, 4)}
    if pivot is not None:
        px, py = img(*pivot)
        meta["pivot"] = [round((px - x0) / (x1 - x0), 4), round((py - z0) / (z1 - z0), 4)]
        meta["px"], meta["py"] = round(px, 4), round(py, 4)
    with open(os.path.join(ART, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    print("EJECT", name, w_px, h_px)
    return meta


def render_bg(name, objs=None, w=12.0, h=6.8, line=BG_OUT, inner=BG_IN, quality=91):
    """Hintergrund (JPG, 12 x 6,8 Einheiten = 2160 x 1224 px), Mitte = Szenen-Ursprung."""
    sc = bpy.context.scene
    objs = list(OBJS) if objs is None else objs
    cam, cd = _camera(0.0, 0.0, w, h)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = int(w * PPU), int(h * PPU), 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.quality = quality
    _lines(line, inner)
    _show(objs)
    path = os.path.join(ASSETS, f"task_eject_hive_{name}.jpg")
    H.render_to(path)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cd)
    with open(os.path.join(ART, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump({"sprite": os.path.basename(path), "w": int(w * PPU), "h": int(h * PPU), "cx": 0, "cy": 0}, fh)
    print("EJECT", name, "bg")


def note(name, **kw):
    """Zusatzangaben fuer die Regie (Punkte im Bild, Abstaende) nach art/eject/<name>.json."""
    with open(os.path.join(ART, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(kw, fh)
