# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# consoles_common.py - Bausteine fuer die Amberhive-Konsolen, Tueren, Vents und Kameras (nur in Blender importieren).
# Stil V2 "Bernsteinlicht" (art/STIL_V2.md): Korpus im Anstrichton, Deckplatte Nussholz, Bedienteile Messing, Anzeigen als
# Leuchtflaeche mit Lichthof, weicher Bodenschatten. Baut auf hive_style.py auf (Scherung, Palette, Freestyle, render_sprite).
# Alle Teile landen in der Liste P; render() schert sie (finish), haengt Schatten und Lichthoefe an, rendert ein Sprite nach
# art/consoles und raeumt die Szene wieder leer. HIVE_CONSOLES_OUT=<ordner> lenkt die Ausgabe zum Probieren um.
# Transformationen wirken direkt auf die Mesh-Daten (keine Objektmatrizen), damit nichts verloren geht.
#
# Anker aller Sprites: Welt (0,0,0). Konsolen: Mitte der Vorderkante am Boden (scan_pad und Vent: Mitte), Tueren: Mitte der
# Oeffnung am Boden, Kamera: Pfostenfuss.

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hive_style as S  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("HIVE_CONSOLES_OUT") or os.path.normpath(os.path.join(HERE, "..", "art", "consoles"))
PPM = 120
K = S.K

# Zusatztoene der Konsolen (als Schluessel in der Palette, damit jede Farbe ihr eigenes Material und ihre Linie bekommt)
S.PALETTE.update({
    "ice": (0.66, 0.86, 0.98), "ice_light": (0.86, 0.96, 1.0), "ice_dark": (0.36, 0.60, 0.86),
    "shaft": (0.10, 0.07, 0.08), "screen": (0.12, 0.26, 0.29), "screen_glow": (0.56, 0.94, 0.84),
    "amber_red": (1.0, 0.36, 0.10), "lamp_off": (0.46, 0.30, 0.16), "lamp_green": (0.60, 0.92, 0.42),
    "cork": (0.80, 0.62, 0.42), "velvet": (0.66, 0.18, 0.34), "water": (0.56, 0.82, 0.93),
    "paint_coral_dark": (0.66, 0.33, 0.30), "paint_plum_dark": (0.36, 0.21, 0.37), "paint_mint_dark": (0.38, 0.58, 0.50),
})
S._KIND_OF.update({
    "ice": "wax", "ice_light": "wax", "ice_dark": "wax", "water": "gloss", "velvet": "cloth", "cork": "cloth",
    "screen": "gloss", "amber_red": "gloss", "lamp_off": "gloss", "lamp_green": "gloss",
})
ICE, ICE_LIGHT, ICE_DARK, SHAFT, SCREEN, AMBER_RED, LAMP_OFF = "ice", "ice_light", "ice_dark", "shaft", "screen", "amber_red", "lamp_off"

P = []            # Teile des aktuellen Bilds
SOFT = []         # Lichthoefe und Schatten (schon geschert, ohne Linie)
NOLINES = None


def setup():
    global NOLINES
    sc = S.reset()
    os.makedirs(OUT, exist_ok=True)
    NOLINES = S.nolines()          # Kleinteile hier bekommen keine Freestyle-Linie (Ziffern, Zeiger, Tintenstriche)
    return sc


def add(ob, nl=False):
    P.append(ob)
    if nl:
        NOLINES.objects.link(ob)
    return ob


def mark():
    return len(P)


def since(m):
    return P[m:]


def _list(obs):
    return list(obs) if isinstance(obs, (list, tuple)) else [obs]


def flat(obs):
    """Teile ohne Richtungslicht (Leuchtendes): reine Palettenfarbe."""
    for ob in _list(obs):
        ob["unlit"] = 1
    return obs


def xform(obs, M):
    for ob in _list(obs):
        ob.data.transform(M)
        ob.data.update()
    return obs


def rot(obs, rx=0.0, ry=0.0, rz=0.0, pivot=(0, 0, 0)):
    """Drehung in Grad (XYZ) um einen Punkt."""
    R = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix().to_4x4()
    T = Matrix.Translation(pivot)
    return xform(obs, T @ R @ T.inverted())


def move(obs, dx=0.0, dy=0.0, dz=0.0):
    return xform(obs, Matrix.Translation((dx, dy, dz)))


def scl(obs, sx=1.0, sy=1.0, sz=1.0, pivot=(0, 0, 0)):
    T = Matrix.Translation(pivot)
    D = Matrix.Diagonal((sx, sy, sz, 1.0))
    return xform(obs, T @ D @ T.inverted())


def orient(obs, p, d):
    """Teile, die entlang der lokalen z-Achse gebaut sind, in Richtung d drehen und nach p setzen."""
    q = Vector(d).normalized().to_track_quat("Z", "Y")
    return xform(obs, Matrix.Translation(p) @ q.to_matrix().to_4x4())


def _n():
    return f"p{len(P)}"


# ------------------------------------------------------------------ Grundformen

def bx(x0, y0, z0, x1, y1, z1, mat, bevel=0.0, nl=False):
    return add(S.box(_n(), min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1), mat, bevel=bevel), nl)


def bc(cx, cy, cz, w, d, h, mat, bevel=0.0, nl=False):
    """Quader um einen Mittelpunkt."""
    return bx(cx - w / 2, cy - d / 2, cz - h / 2, cx + w / 2, cy + d / 2, cz + h / 2, mat, bevel, nl)


def cyl(cx, cy, z0, z1, r, mat, seg=24, r_top=None, nl=False):
    return add(S.cylinder(_n(), cx, cy, z0, z1, r, mat, seg=seg, r_top=r_top), nl)


def cyly(cx, cz, y0, y1, r, mat, seg=24, r_back=None, nl=False):
    """Zylinder entlang y (Stirnflaeche nach Sueden), Radius r vorn (y0), r_back hinten (y1)."""
    L = y1 - y0
    ob = add(S.cylinder(_n(), 0, 0, 0, L, r if r_back is None else r_back, mat, seg=seg, r_top=r), nl)
    _floor_to_zero(ob)
    xform(ob, Matrix.Translation((cx, y1, cz)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    return ob


def _floor_to_zero(ob):
    zmin = min(v.co.z for v in ob.data.vertices)
    if abs(zmin) > 1e-6:
        move(ob, dz=-zmin)


def cylx(cy, cz, x0, x1, r, mat, seg=24, r_end=None, nl=False):
    """Zylinder entlang x."""
    ob = add(S.cylinder(_n(), 0, 0, 0, x1 - x0, r, mat, seg=seg, r_top=r_end), nl)
    _floor_to_zero(ob)
    perm = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    xform(ob, Matrix.Translation((x0, cy, cz)) @ perm)
    return ob


def tube(p0, p1, r, mat, seg=16, r1=None, nl=False):
    """Zylinder zwischen zwei Punkten."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    ob = add(S.cylinder(_n(), 0, 0, 0, d.length, r, mat, seg=seg, r_top=r1), nl)
    _floor_to_zero(ob)
    q = d.normalized().to_track_quat("Z", "Y")
    xform(ob, Matrix.Translation(a) @ q.to_matrix().to_4x4())
    return ob


def pipe(points, r, mat, seg=16, joints=True):
    out = []
    for i in range(len(points) - 1):
        out.append(tube(points[i], points[i + 1], r, mat, seg))
        if joints and i + 1 < len(points) - 1:
            out.append(sph(*points[i + 1], r, mat, seg=seg))
    return out


def sph(cx, cy, cz, r, mat, seg=20, sz=1.0, nl=False):
    return add(S.sphere(_n(), cx, cy, cz, r, mat, seg=seg, sz=sz), nl)


def ell(cx, cy, cz, rx, ry, rz, mat, seg=20, nl=False):
    ob = add(S.sphere(_n(), 0, 0, 0, 1.0, mat, seg=seg), nl)
    xform(ob, Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((rx, ry, rz, 1.0)))
    return ob


def tor(cx, cy, cz, R, r, mat, seg=32, ring=10, face="up", nl=False):
    """Torus; face 'up' = liegt waagerecht, 'south' = steht in der xz-Ebene."""
    ob = add(S.torus(_n(), 0, 0, 0, R, r, mat, seg=seg, ring=ring), nl)
    M = Matrix.Rotation(math.radians(90), 4, "X") if face == "south" else Matrix.Identity(4)
    xform(ob, Matrix.Translation((cx, cy, cz)) @ M)
    return ob


def prism(pts, z0, z1, mat, nl=False):
    ob = add(S.prism(_n(), pts, z0, z1, mat), nl)
    _fix_normals(ob)
    return ob


def prism_y(pts_xz, y0, y1, mat, nl=False):
    """Grundriss in der xz-Ebene (Punkte (x, z)), entlang y von y0 bis y1 extrudiert."""
    ob = add(S.prism(_n(), pts_xz, 0, y1 - y0, mat), nl)
    xform(ob, Matrix.Translation((0, y1, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    _fix_normals(ob)
    return ob


def prism_x(pts_yz, x0, x1, mat, nl=False):
    """Profil in der yz-Ebene (Punkte (y, z)), entlang x von x0 bis x1 extrudiert (Pulte, Schraegen)."""
    ob = add(S.prism(_n(), pts_yz, 0, x1 - x0, mat), nl)
    perm = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    xform(ob, Matrix.Translation((x0, 0, 0)) @ perm)
    _fix_normals(ob)
    return ob


def _fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def hexpts(cx, cy, r, flat=True, rot_deg=0.0):
    return S.hexagon_pts(cx, cy, r, flat=flat, rot=math.radians(rot_deg))


def hexz(cx, cy, r, z0, z1, mat, flat=True, nl=False, sy=1.0):
    """Liegendes Sechseck (Deckflaeche oben); sy staucht es in der Tiefe."""
    pts = hexpts(cx, cy, r, flat)
    if sy != 1.0:
        pts = [(x, cy + (y - cy) * sy) for x, y in pts]
    return prism(pts, z0, z1, mat, nl)


def hexy(cx, cz, r, y0, y1, mat, flat=True, nl=False):
    """Stehendes Sechseck (Stirn nach Sueden), flach oben/unten bei flat=True."""
    return prism_y(hexpts(cx, cz, r, flat), y0, y1, mat, nl)


def arch_pts(x0, x1, z0, z1, rise, n=12):
    """Rechteck mit Bogen oben (Scheitel rise ueber z1), Punkte gegen den Uhrzeigersinn in (x, z)."""
    pts = [(x0, z0), (x1, z0)]
    for i in range(n + 1):
        t = i / n
        x = x1 + (x0 - x1) * t
        pts.append((x, z1 + rise * math.sin(math.pi * t)))
    return pts


def arch_z(x, x0, x1, z1, rise):
    """Hoehe des Bogens aus arch_pts an der Stelle x."""
    t = (x1 - x) / (x1 - x0)
    return z1 + rise * math.sin(math.pi * max(0.0, min(1.0, t)))


def lathe(prof, cx, cy, mat, seg=28, nl=False, band=None, caps=True):
    """Drehkoerper aus Profil [(r, z), ...] von unten nach oben; r = 0 an den Enden schliesst.
    mat darf eine Liste sein, band nennt dann je Profilabschnitt den Materialindex. caps=False laesst offene Enden offen."""
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((cx, cy, z))])
        else:
            rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), z))
                          for i in range(seg)])
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        mi = band[k] if band else 0
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1:
                f = bm.faces.new((a[0], b[j], b[i]))
            elif len(b) == 1:
                f = bm.faces.new((a[i], a[j], b[0]))
            else:
                f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mi
    if caps and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = band[0] if band else 0
    if caps and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = band[-1] if band else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add(S._obj(_n(), bm, mat), nl)


def loft(loops, mat, caps=True, nl=False):
    """Haut ueber geschlossene Schleifen gleicher Punktzahl (3D)."""
    bm = bmesh.new()
    vl = [[bm.verts.new(p) for p in lp] for lp in loops]
    n = len(loops[0])
    for i in range(len(vl) - 1):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((vl[i][j], vl[i][k], vl[i + 1][k], vl[i + 1][j]))
    if caps:
        bm.faces.new(list(reversed(vl[0])))
        bm.faces.new(vl[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add(S._obj(_n(), bm, mat), nl)


def sweep(path, radius, mat, seg=12, nl=False):
    """Rohr entlang eines Pfads (Liste 3D-Punkte); radius Zahl oder Liste je Punkt."""
    pts = [Vector(p) for p in path]
    rs = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tans = []
    for i in range(len(pts)):
        tans.append((pts[min(len(pts) - 1, i + 1)] - pts[max(0, i - 1)]).normalized())
    n = tans[0].orthogonal().normalized()
    loops = []
    for i, p in enumerate(pts):
        t = tans[i]
        n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        loops.append([tuple(p + rs[i] * (math.cos(2 * math.pi * j / seg) * n + math.sin(2 * math.pi * j / seg) * b))
                      for j in range(seg)])
    return loft(loops, mat, nl=nl)


def curve(pts, n=6):
    """Weiche Kurve durch Stuetzpunkte (Catmull-Rom), n Zwischenschritte je Abschnitt."""
    P3 = [Vector(p) for p in pts]
    out = []
    for i in range(len(P3) - 1):
        p0, p1, p2, p3 = P3[max(0, i - 1)], P3[i], P3[i + 1], P3[min(len(P3) - 1, i + 2)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(P3[-1])
    return [tuple(p) for p in out]


def stripe_ring(cx, cy, z0, z1, r0, r1, n, mats, a_off=0.0):
    """Flacher Ring aus n Feldern in wechselnden Farben (Warnstreifen)."""
    out = []
    for i in range(n):
        a0 = a_off + 2 * math.pi * i / n
        a1 = a_off + 2 * math.pi * (i + 1) / n
        am = (a0 + a1) / 2
        pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in ((r0, a0), (r1, a0), (r1, am), (r1, a1), (r0, a1), (r0, am))]
        out.append(prism(pts, z0, z1, mats[i % len(mats)], nl=True))
    return out


def txt(s, cx, cy, cz, size, mat, face="south", extrude=0.003, nl=True):
    """Text als Mesh (Standardschrift), mittig. face 'south' = auf einer Stirnflaeche, 'up' = liegend."""
    cu = bpy.data.curves.new("t", "FONT")
    cu.body = s
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude
    tob = bpy.data.objects.new("t", cu)
    bpy.context.scene.collection.objects.link(tob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tob.evaluated_get(dg))
    bpy.data.objects.remove(tob, do_unlink=True)
    bpy.data.curves.remove(cu)
    ob = bpy.data.objects.new(_n(), me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.clear()
    me.materials.append(S.material(mat))
    for p in me.polygons:
        p.material_index = 0
    M = Matrix.Rotation(math.radians(90), 4, "X") if face == "south" else Matrix.Identity(4)
    xform(ob, Matrix.Translation((cx, cy, cz)) @ M)
    return add(ob, nl)


def clip_floor(obs, z=0.0):
    """Alles unter der Hoehe z abschneiden (Schotten, die im Boden versinken). Leere Teile verschwinden."""
    for ob in _list(obs):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_inner=True)
        n = len(bm.faces)
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
        if n == 0 and ob in P:
            P.remove(ob)
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)


# ------------------------------------------------------------------ Licht: Leuchtflaechen und Lichthoefe

def glow(x, y, z, r, color="glow", strength=0.5, lift=0.0):
    """Lichthof um etwas Leuchtendes (Koordinaten vor der Scherung). lift hebt die Scheibe an, ohne ihre Lage im Bild zu
    aendern: so liegt sie ueber Bauteilen, die hoeher sind als die Lichtquelle."""
    SOFT.append(S.halo(f"halo{len(SOFT)}", x, y - K * lift, z + lift, r, color, strength))


def lamp(x, y, z, r, color="glow", halo=2.8, strength=0.5, seg=14, sz=1.0, lift=0.0):
    """Leuchtkugel mit Lichthof."""
    ob = flat(sph(x, y, z, r, color, seg=seg, sz=sz))
    if halo:
        glow(x, y, z, r * halo, color, strength, lift)
    return ob


def _rx(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


def tilt_pt(alpha, base, p):
    """Wo ein Punkt p einer mit tilted() gekippten Gruppe landet."""
    q = _rx(p, -alpha)
    return (q[0] + base[0], q[1] + base[1], q[2] + base[2])


def slope_pt(alpha, base, p):
    """Wo ein Punkt p einer mit on_slope() gelegten Gruppe landet."""
    q = _rx(p, alpha)
    return (q[0] + base[0], q[1] + base[1], q[2] + base[2])


# ------------------------------------------------------------------ zusammengesetzte Teile

def cabinet(x0, x1, y0, y1, h, tone, top="wood", kick=0.07, over=0.03, top_t=0.05, bevel=0.014):
    """Gestrichener Korpus mit dunklem Sockel und ueberstehender Nussholzplatte."""
    bx(x0 + 0.015, y0 + 0.02, 0, x1 - 0.015, y1 - 0.01, kick, "wood_dark")
    body = bx(x0, y0, kick, x1, y1, h - top_t, tone, bevel=bevel)
    if top:
        bx(x0 - over, y0 - over, h - top_t, x1 + over, y1 + over * 0.5, h, top, bevel=0.012)
    return body


def panel(x0, x1, z0, z1, y, mat, depth=0.008, knob=None, nl=False):
    """Fuellung/Schubladenfront auf einer Suedflaeche (Ebene y), optional Messingknopf an Stelle knob = (x, z)."""
    o = bx(x0, y - depth, z0, x1, y, z1, mat, nl=nl)
    if knob:
        sph(knob[0], y - depth - 0.006, knob[1], 0.02, "brass", seg=10)
    return o


def badge(cx, cy, cz, r=0.055, face="south", color="wall_glow", halo=True):
    """Aufgabenwabe: Messingrahmen mit leuchtender Zelle. Das Erkennungszeichen aller Aufgabenpunkte.
    face 'south': cy = Ebene der Stirnflaeche; 'up': cz = Hoehe der Deckflaeche."""
    if face == "south":
        hexy(cx, cz, r, cy - 0.018, cy, "brass")
        flat(hexy(cx, cz, r * 0.66, cy - 0.024, cy - 0.018, color))
        if halo:
            glow(cx, cy - 0.03, cz, r * 2.6, color, 0.5, lift=0.25)
    else:
        hexz(cx, cy, r, cz, cz + 0.018, "brass")
        flat(hexz(cx, cy, r * 0.66, cz + 0.018, cz + 0.024, color))
        if halo:
            glow(cx, cy, cz + 0.03, r * 2.6, color, 0.5)


def gauge(cx, cz, y, r, ang, face="glow", n=7, sweep_deg=110, needle_mat="red"):
    """Zeigerinstrument auf einer Suedflaeche: Messingring, leuchtendes Blatt, Striche, Zeiger."""
    cyly(cx, cz, y - 0.03, y, r, "brass", seg=28)
    flat(cyly(cx, cz, y - 0.036, y - 0.03, r * 0.80, face, seg=28))
    for k in range(n):
        a = -sweep_deg + 2 * sweep_deg * k / max(1, n - 1)
        o = bx(cx - 0.005, y - 0.039, cz + r * 0.56, cx + 0.005, y - 0.036, cz + r * 0.74, "ink", nl=True)
        rot(o, ry=a, pivot=(cx, y, cz))
    needle(cx, cz, y - 0.039, r * 0.66, ang, needle_mat, w=max(0.012, r * 0.13))
    cyly(cx, cz, y - 0.048, y - 0.036, r * 0.16, "brass_dark", seg=10)


def needle(cx, cz, y, length, ang, mat="red", w=0.012):
    """Zeiger auf einer Stirnflaeche, Winkel 0 = nach oben, positiv = im Uhrzeigersinn."""
    o = bx(cx - w / 2, y - 0.004, cz, cx + w / 2, y, cz + length, mat, nl=True)
    rot(o, ry=ang, pivot=(cx, y, cz))
    return o


def comb_front(x0, x1, z0, z1, y, r, mat, alt=None, pattern=None, depth=0.008, nl=True, keep=None):
    """Wabenmuster auf einer Suedflaeche (Ebene y). keep(x, z) entscheidet, ob eine Zelle gesetzt wird."""
    h = math.sqrt(3) * r
    out, col, x = [], 0, x0 + r
    while x + r <= x1 + 1e-6:
        z = z0 + h / 2 + (h / 2 if col % 2 else 0)
        row = 0
        while z + h / 2 <= z1 + 1e-6:
            if keep is None or keep(x, z):
                m = alt if (alt and pattern and pattern(col, row)) else mat
                out.append(hexy(x, z, r * 0.84, y - depth, y, m, nl=nl))
            z += h
            row += 1
        x += 1.5 * r
        col += 1
    return out


def comb_top(x0, x1, y0, y1, z, r, mat, alt=None, pattern=None, t=0.008, nl=True, keep=None):
    """Wabenmuster auf einer Deckflaeche (Hoehe z)."""
    h = math.sqrt(3) * r
    out, col, x = [], 0, x0 + r
    while x + r <= x1 + 1e-6:
        y = y0 + h / 2 + (h / 2 if col % 2 else 0)
        row = 0
        while y + h / 2 <= y1 + 1e-6:
            if keep is None or keep(x, y):
                m = alt if (alt and pattern and pattern(col, row)) else mat
                out.append(hexz(x, y, r * 0.84, z, z + t, m, nl=nl))
            y += h
            row += 1
        x += 1.5 * r
        col += 1
    return out


def legs(x0, x1, y0, y1, h, t=0.06, mat="wood_dark", inset=0.02):
    out = []
    for x in (x0 + inset, x1 - inset - t):
        for y in (y0 + inset, y1 - inset - t):
            out.append(bx(x, y, 0, x + t, y + t, h, mat))
    return out


def flower_top(cx, cy, z, r, petal="petal_pink", center="pollen", n=5, nl=True):
    """Liegende Bluete (Bluetenblaetter als flache Scheiben), fuer Karten und Zeichnungen."""
    for i in range(n):
        a = 2 * math.pi * i / n + math.pi / 2
        cyl(cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a), z, z + 0.006, r * 0.5, petal, seg=10, nl=nl)
    cyl(cx, cy, z, z + 0.012, r * 0.4, center, seg=10, nl=nl)


def inkline(x0, y0, x1, y1, z, w=0.008, mat="ink", h=0.002):
    """Tintenstrich auf einer Deckflaeche."""
    L = math.hypot(x1 - x0, y1 - y0)
    o = bx(0, -w / 2, z, L, w / 2, z + h, mat, nl=True)
    rot(o, rz=math.degrees(math.atan2(y1 - y0, x1 - x0)))
    move(o, x0, y0)
    return o


def bee(cx, cy, cz, s=1.0, yaw=0.0):
    """Kleine Biene, sitzt mit dem Bauch auf Hoehe cz. Kopf zeigt bei yaw=0 nach Osten."""
    m = mark()
    prof = [(0, -0.15), (0.035, -0.125), (0.066, -0.08), (0.076, -0.025), (0.070, 0.03), (0.048, 0.075), (0, 0.09)]
    o = lathe(prof, 0, 0, ["bee_black", "bee_yellow"], seg=14, band=[0, 1, 0, 1, 0, 1])
    rot(o, ry=90)
    sph(0.115, 0, 0.008, 0.05, "bee_black", seg=12)
    for side in (-1, 1):
        sph(0.145, side * 0.028, 0.024, 0.014, "white", seg=8, nl=True)
        w = ell(-0.02, side * 0.07, 0.075, 0.07, 0.045, 0.01, "wing", seg=12)
        rot(w, rx=side * -22, rz=side * -18, pivot=(0, side * 0.02, 0.06))
    g = since(m)
    scl(g, s, s, s)
    rot(g, rz=yaw)
    move(g, cx, cy, cz + 0.076 * s)
    return g


def crown(cx, cy, z, r=0.085, mat="brass", jewel="red"):
    """Kleine Krone der Koenigin: Reif, fuenf Zacken mit Lichtperlen, Stein vorn."""
    h = 0.62 * r
    cyl(cx, cy, z, z + h, r, mat, seg=20)
    cyl(cx, cy, z, z + h * 0.3, r * 1.08, "brass_dark", seg=20)
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 2
        px, py = cx + r * 0.8 * math.cos(a), cy + r * 0.8 * math.sin(a)
        cyl(px, py, z + h, z + 1.6 * h, 0.3 * r, mat, seg=8, r_top=0.03 * r)
        flat(sph(px, py, z + 1.66 * h, 0.16 * r, "glow", seg=8, nl=True))
    sph(cx, cy - r, z + h * 0.55, 0.22 * r, jewel, seg=10, nl=True)


def tilted(m, alpha, base):
    """Teile seit mark m sind lokal an einer senkrechten Tafel gebaut (Stirn bei y <= 0, Fuss bei z = 0);
    nach hinten um alpha Grad kippen und an base = (x, y, z) setzen."""
    g = since(m)
    rot(g, rx=-alpha)
    move(g, *base)
    return g


def on_slope(m, alpha, base):
    """Teile seit mark m liegen lokal auf der Ebene z = 0 (y nach hinten); auf eine nach hinten ansteigende Schraege
    mit Winkel alpha legen, base = Punkt der Vorderkante."""
    g = since(m)
    rot(g, rx=alpha)
    move(g, *base)
    return g


# ------------------------------------------------------------------ Rendern

def clear():
    for ob in list(P) + list(SOFT):
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
    P.clear()
    SOFT.clear()


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
    lo, hi = half(pts), half(list(reversed(pts)))
    return lo[:-1] + hi[:-1]


def _prepare(shadow=True):
    """Teile scheren, Bodenschatten (Huelle der bodennahen Punkte) und Lichthoefe dazu. Liefert alle Objekte des Bilds."""
    low, zmax = set(), 0.0
    for ob in P:
        for v in ob.data.vertices:
            zmax = max(zmax, v.co.z)
            if v.co.z < 0.3:
                low.add((round(v.co.x, 2), round(v.co.y, 2)))
    for ob in P:
        S.finish(ob, shade=not ob.get("unlit"))
    if shadow and zmax >= 0.25:
        hull = _hull(list(low))
        if len(hull) >= 3:
            k = min(1.0, 0.5 + zmax * 0.3)
            hull = [(x + 0.03 * k, y - 0.03 * k) for x, y in hull]
            SOFT.append(S.soft_blob("shadow", hull, 0.06, (0.13, 0.07, 0.10), 0.38 * k, z=0.003))
    return list(P) + list(SOFT)


def _bounds(objs):
    xs, ys = [], []
    for ob in objs:
        for v in ob.data.vertices:
            xs.append(v.co.x)
            ys.append(v.co.y)
    return min(xs), min(ys), max(xs), max(ys)


def _pixels(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4), w, h


def _composite(base_png, over_png, out_png):
    """over_png (Lichthoefe) ueber base_png legen, beides mit gerader Deckkraft."""
    b, w, h = _pixels(base_png)
    o, _w, _h = _pixels(over_png)
    ao, ab = o[..., 3:4], b[..., 3:4]
    a = ao + ab * (1.0 - ao)
    rgb = (o[..., :3] * ao + b[..., :3] * ab * (1.0 - ao)) / np.maximum(a, 1e-6)
    img = bpy.data.images.new("hive_comp", w, h, alpha=True)
    img.pixels.foreach_set(np.concatenate([rgb, a], axis=2).ravel())
    img.filepath_raw = out_png
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def render(name, extra=None, shadow=True):
    """Bild rendern. Lichthoefe laufen in einem eigenen Durchgang ohne Linien und werden darueber gelegt: lagen sie in der
    Szene, verdeckten sie fuer Freestyle die Umrisse darunter (Probe 15.11.: gluehende Platten ohne Kontur)."""
    objs = _prepare(shadow)
    bb = _bounds(objs)
    if extra:
        bb = (min(bb[0], extra[0]), min(bb[1], extra[1]), max(bb[2], extra[2]), max(bb[3], extra[3]))
    halos = [o for o in SOFT if o.name.startswith("halo")]
    solid = [o for o in objs if o not in halos]
    out = os.path.join(OUT, name + ".png")
    meta = S.render_sprite(solid, out, ppm=PPM, extra_bounds=bb)
    if halos:
        sc = bpy.context.scene
        tmp = os.path.join(OUT, "_tmp_halo.png")
        sc.render.use_freestyle = False
        S.render_sprite(halos, tmp, ppm=PPM, extra_bounds=bb)
        sc.render.use_freestyle = True
        _composite(out, tmp, out)
        for f in (tmp, os.path.splitext(tmp)[0] + ".json"):
            if os.path.exists(f):
                os.remove(f)
    clear()
    print("OK", name, meta["w"], meta["h"])
    return meta


def frames(names, build, shadow=True):
    """Mehrere Bilder mit gleicher Groesse und gleichem Anker: erst alle Grenzen messen, dann mit der Vereinigung rendern."""
    bb = None
    for i in range(len(names)):
        build(i)
        b = _bounds(_prepare(shadow))
        bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
        clear()
    for i, nm in enumerate(names):
        build(i)
        render(nm, extra=bb, shadow=shadow)


def want(name, sel):
    return not sel or name in sel


def run(motifs, scope):
    """Alle Motive (oder die auf der Kommandozeile genannten) bauen und rendern. NO_SHADOW im Skript nennt flache Motive."""
    sel = set(S.args())
    setup()
    no_shadow = scope.get("NO_SHADOW", set())
    for name in motifs:
        if want(name, sel):
            scope[name]()
            render(name, shadow=name not in no_shadow)
