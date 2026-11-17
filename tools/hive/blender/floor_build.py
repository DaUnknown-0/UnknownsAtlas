# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# floor_build.py - Boden und Wachswaende einer Amberhive-Etage aus _out/floor_<etage>.json (floor_geo.py) bauen und rendern.
#   blender -b --factory-startup -P floor_build.py -- <ground|crown> <ppm> <ausgabe.png>
#
# Stil V2: der Belag ("floor") und die Waben auf der Wandkrone ("flat") haben keine Linien, die Fugen entstehen aus dem
# dunkleren Fugengrund und der Helligkeitsstreuung je Fliese (Attribut "tint"). Linien gibt es nur fuer die Wachsmasse
# ("solid", kraeftig), fuer Relief, Leisten und Wachskragen ("deco", fein) und fuer Teppiche und den Honigsee ("decal", fein
# und halb durchsichtig). Lichtflecke ("light") liegen als weiche Hoefe ueber dem Belag.

import json
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(__file__))
import hive_style as S  # noqa: E402

S.GROUND_FADE = False          # der Boden ist kein Objekt: keine Abdunklung zum Boden hin (gilt auch fuer fx_build.py)


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def ring_edges(bm, pts, z):
    vs = [bm.verts.new((x, y, z)) for x, y in pts]
    es = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    return vs, es


def build(shapes, coll_name, mats, merge):
    bm = bmesh.new()
    tint = bm.loops.layers.float_color.new("tint")
    mat_index = {m: i for i, m in enumerate(mats)}

    def paint(f, mat, t=1.0):
        f.material_index = mat_index[mat]
        for lp in f.loops:
            lp[tint] = (t, t, t, 1.0)

    for sh in shapes:
        if "hexfront" in sh:
            px, py, zc, r = sh["hexfront"]
            ring = [(px + r * math.cos(math.pi / 3 * i + math.pi / 6), zc + r * math.sin(math.pi / 3 * i + math.pi / 6)) for i in range(6)]
            front = [bm.verts.new((px + (x - px) * 0.8, py - 0.04, zc + (z - zc) * 0.8)) for x, z in ring]
            back = [bm.verts.new((x, py + 0.01, z)) for x, z in ring]
            paint(bm.faces.new(front), sh["mat"])
            for i in range(6):
                j = (i + 1) % 6
                paint(bm.faces.new((front[i], front[j], back[j], back[i])), sh["mat"])
            continue
        z0, z1 = sh["z0"], sh["z1"]
        rings = [sh["pts"]] + sh.get("holes", [])
        tops = []
        if len(rings) == 1 and len(rings[0]) >= 3:          # lochfrei: ein Vieleck (Blender fuellt es zuverlaessig)
            vs = [bm.verts.new((x, y, z1)) for x, y in rings[0]]
            tops.append(vs)
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            f.normal_update()
            if f.normal.z < 0:
                f.normal_flip()
            paint(f, sh["mat"], sh.get("tint", 1.0))
        else:                                               # mit Loechern (nur die Wachsmasse): Scanfill
            edges = []
            for pts in rings:
                vs, es = ring_edges(bm, pts, z1)
                edges += es
                tops.append(vs)
            res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=True, edges=edges, normal=(0, 0, 1))
            for f in res["geom"]:
                if isinstance(f, bmesh.types.BMFace):
                    paint(f, sh["mat"], sh.get("tint", 1.0))
                    if f.normal.z < 0:
                        f.normal_flip()
        if z1 > z0 + 1e-4:                                  # Prisma: senkrechte Seiten nach unten
            for vs in tops:
                n = len(vs)
                low = [bm.verts.new((v.co.x, v.co.y, z0)) for v in vs]
                for i in range(n):
                    j = (i + 1) % n
                    paint(bm.faces.new((vs[i], low[i], low[j], vs[j])), sh.get("side", sh["mat"]))
    if merge:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0015)
    bm.normal_update()
    me = bpy.data.meshes.new(coll_name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(S.material(m))
    ob = bpy.data.objects.new(coll_name, me)
    coll(coll_name).objects.link(ob)
    return ob


def lineset(name, cname, types, thick_px, color, alpha=1.0):
    fs = bpy.context.scene.view_layers[0].freestyle_settings
    ls = fs.linesets.new(name)
    ls.select_by_visibility = True
    ls.visibility = "VISIBLE"
    ls.select_by_edge_types = True
    ls.select_by_collection = True
    ls.collection = coll(cname)
    ls.collection_negation = "INCLUSIVE"
    ls.select_silhouette = "silhouette" in types
    ls.select_border = "border" in types
    ls.select_crease = "crease" in types
    ls.select_material_boundary = "material" in types
    ls.linestyle.color = S.lin(color)
    ls.linestyle.alpha = alpha
    ls.linestyle.thickness = max(1.0, thick_px)
    ls.linestyle.thickness_position = "CENTER"
    return ls


def build_groups(shapes):
    """Formen nach Sammlung bauen und fertigstellen; Lichtflecke als Hoefe. Gibt {Sammlung: Objekt} zurueck."""
    groups, lights = {}, []
    for sh in shapes:
        if "light" in sh:
            lights.append(sh)
        else:
            groups.setdefault(sh["coll"], []).append(sh)
    objs = {}
    for name, shs in groups.items():
        mats = sorted({s["mat"] for s in shs} | {s.get("side", s["mat"]) for s in shs})
        objs[name] = build(shs, name, mats, merge=(name in ("floor", "decal")))
    for ob in objs.values():
        S.finish(ob)
    for i, sh in enumerate(lights):
        x, y, r = sh["light"]
        S.halo(f"light{i}", x, y, sh.get("z", 0.014), r, sh.get("color", "glow"), sh.get("strength", 0.15))
    return objs


def main():
    level, ppm, out_png = S.args()[0], float(S.args()[1]), S.args()[2]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = json.load(open(os.path.join(here, "_out", f"floor_{level}.json"), encoding="utf-8"))
    sc = S.reset()
    build_groups(data["shapes"])
    # Linien je Sammlung
    fs = sc.view_layers[0].freestyle_settings
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    lineset("solid", "solid", {"silhouette", "border", "crease"}, 0.034 * ppm, S.LINE)
    lineset("deco", "deco", {"silhouette", "border", "crease", "material"}, 0.012 * ppm, S.LINE, 0.8)
    lineset("decal", "decal", {"border", "material"}, 0.013 * ppm, S.LINE, 0.55)
    # Kamera genau ueber die Etagengrenzen
    x0, y0, x1, y1 = data["bounds"]
    w_px, h_px = int(round((x1 - x0) * ppm)) // 4 * 4, int(round((y1 - y0) * ppm)) // 4 * 4
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(w_px, h_px) / ppm
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (x0 + w_px / ppm / 2, y1 - h_px / ppm / 2, 60.0)
    cam_data.clip_start, cam_data.clip_end = 1.0, 200.0
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w_px, h_px
    sc.render.resolution_percentage = 100
    sc.render.line_thickness = 1.0
    S.render_to(out_png)
    print("FLOOR RENDERED", out_png, w_px, h_px)


if __name__ == "__main__" and S.args() and S.args()[0] in ("ground", "crown"):
    main()
