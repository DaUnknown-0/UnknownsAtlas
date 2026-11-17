# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# brand_build.py - Kartenknopf und Symbol von Amberhive (Stil V2): gepraegter Schriftzug mit Honigverlauf und Lichtkante,
# Wappen (Wabe mit Biene vor der Abendsonne im Messingring) und das frei stehende Symbol (Wabe + Biene).
#   blender -b --factory-startup -P brand_build.py -- <ausgabeordner>
# Ergebnis: brand_title.png (1120 x 230), brand_emblem.png (512 x 512), brand_icon.png (512 x 512, frei)

import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(__file__))
import hive_style as S  # noqa: E402

S.GROUND_FADE = False


def gradient_material(name, stops, axis="Y"):
    """Unbeleuchteter Farbverlauf ueber die Hoehe des Objekts. stops: [(Position 0..1, sRGB), ...] von unten nach oben."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    for i, (pos, col) in enumerate(stops):
        el = cr.elements[i] if i < 2 else cr.elements.new(pos)
        el.position = pos
        el.color = (*S.lin(col), 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs[axis], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def ortho(w_m, h_m, ppm, cx=0.0, cy=0.0):
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(w_m, h_m)
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (cx, cy, 30.0)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = int(w_m * ppm), int(h_m * ppm)
    sc.render.resolution_percentage = 100
    return cam


def lines(outer_px, inner_px):
    sc = bpy.context.scene
    sc.render.line_thickness = 1.0
    for ls in sc.view_layers[0].freestyle_settings.linesets:
        ls.linestyle.thickness = outer_px if ls.name == "outer" else inner_px


def title(out_dir):
    S.reset()
    sc = bpy.context.scene
    cu = bpy.data.curves.new("title", "FONT")
    cu.body = "AMBERHIVE"
    cu.font = bpy.data.fonts.load("C:/Windows/Fonts/impact.ttf")
    cu.size = 1.0
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.space_character = 1.06
    cu.extrude = 0.04
    tmp = bpy.data.objects.new("title_src", cu)
    sc.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bm = bmesh.new()                             # Punkte verschmelzen, sonst zieht Freestyle Striche in die Buchstaben
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("title", me)
    sc.collection.objects.link(ob)
    me.materials.clear()
    me.materials.append(gradient_material("titlegrad", [(0.10, (0.84, 0.42, 0.04)), (0.46, (0.99, 0.64, 0.10)), (0.54, (1.0, 0.80, 0.30)),
                                                        (0.90, (1.0, 0.94, 0.64))]))
    # Praegung: dunkler Block, nach rechts unten versetzt, unter dem Schriftzug
    back = bpy.data.objects.new("title_back", me.copy())
    sc.collection.objects.link(back)
    back.data.materials.clear()
    back.data.materials.append(S.material("honey_deep"))
    back.location = (0.035, -0.04, -0.1)
    S.finish(ob, shade=False, shear=False)
    S.finish(back, shade=False, shear=False)
    lines(7, 1.5)
    ortho(5.6, 1.15, 200)
    S.render_to(os.path.join(out_dir, "brand_title.png"))


def comb(parts, cx, cy, r, z, rows, mats, clip_r=0.86):
    for i in range(-rows, rows + 1):
        for j in range(-rows, rows + 1):
            x = cx + i * 1.5 * r
            y = cy + j * math.sqrt(3) * r + (math.sqrt(3) / 2 * r if i % 2 else 0)
            if (x - cx) ** 2 + (y - cy) ** 2 > (rows * r * 1.55) ** 2 or x * x + y * y > clip_r ** 2:
                continue
            k = (i * 7 + j * 3) % len(mats)
            m = mats[k]
            parts.append(S.prism(f"w{i}_{j}", S.hexagon_pts(x, y, r * 0.95), z, z + 0.03, "wax_dark"))        # Zellwand
            parts.append(S.prism(f"c{i}_{j}", S.hexagon_pts(x, y, r * 0.78), z + 0.03, z + 0.045, m))          # Fuellung
            if m in ("honey", "honey_light"):                                                              # Glanzpunkt
                g = S.sphere(f"g{i}_{j}", x - r * 0.28, y + r * 0.28, z + 0.05, r * 0.14, "white", seg=8, sz=0.3)
                S.nolines().objects.link(g)
                parts.append(g)


def bee_parts(cx, cy, s, z):
    p = []
    p.append(S.sphere("abd", cx + 0.09 * s, cy - 0.02 * s, z, 0.17 * s, "bee_yellow", seg=32, sz=0.9))
    for i, dx in enumerate((0.04, 0.15)):
        st = S.torus(f"st{i}", 0, 0, 0, (0.15 - 0.035 * i) * s, 0.026 * s, "bee_black", seg=32, ring=8)
        st.rotation_euler = (0, math.radians(90), 0)
        st.location = (cx + dx * s, cy - 0.02 * s, z)
        p.append(st)
    p.append(S.sphere("tho", cx - 0.12 * s, cy, z + 0.02, 0.12 * s, "propolis_light", seg=24))
    p.append(S.sphere("head", cx - 0.25 * s, cy + 0.02 * s, z + 0.03, 0.105 * s, "bee_yellow", seg=24))
    p.append(S.sphere("eye", cx - 0.31 * s, cy + 0.0 * s, z + 0.08, 0.04 * s, "black", seg=12))
    p.append(S.sphere("glint", cx - 0.325 * s, cy + 0.015 * s, z + 0.14, 0.014 * s, "white", seg=8))
    p.append(S.sphere("cheek", cx - 0.31 * s, cy - 0.05 * s, z + 0.07, 0.025 * s, "petal_pink", seg=10))
    for side in (-1, 1):
        w = S.sphere(f"w{side}", 0, 0, 0, 0.13 * s, "wing", seg=20, sz=0.25)
        w.scale = (0.8, 1.4, 1)
        w.rotation_euler = (math.radians(side * 20), 0, math.radians(-20))
        w.location = (cx - 0.02 * s, cy + side * 0.12 * s + 0.12 * s, z + 0.12)
        p.append(w)
    for ant in (-0.03, 0.05):
        a = S.cylinder(f"ant{ant}", 0, 0, 0, 0.14 * s, 0.012 * s, "bee_black", seg=6)
        a.rotation_euler = (math.radians(-70), 0, math.radians(35 + ant * 300))
        a.location = (cx - 0.3 * s, cy + (0.08 + ant) * s, z + 0.06)
        p.append(a)
    return p


def emblem(out_dir):
    S.reset()
    sc = bpy.context.scene
    parts = []
    disc = S.cylinder("disc", 0, 0, 0, 0.05, 1.0, "propolis", seg=64)
    disc.data.materials.clear()
    disc.data.materials.append(gradient_material("sky", [(0.0, (0.42, 0.17, 0.36)), (0.45, (0.86, 0.38, 0.30)), (0.75, (1.0, 0.66, 0.30)),
                                                         (1.0, (1.0, 0.86, 0.52))]))
    parts.append(disc)
    sun = S.cylinder("sun", 0.1, 0.3, 0.05, 0.055, 0.42, (1.0, 0.92, 0.62), seg=48)
    parts.append(sun)
    comb(parts, 0.0, -0.5, 0.19, 0.055, 3, ["comb", "honey", "honey_light", "wax", "honey_deep"])
    parts.append(S.torus("rim", 0, 0, 0.06, 1.0, 0.06, "brass", seg=96, ring=12))
    parts.append(S.torus("rim2", 0, 0, 0.09, 0.93, 0.012, "brass_dark", seg=96, ring=6))
    bee = bee_parts(0.12, 0.28, 1.45, 0.5)
    parts += bee
    for ob in parts:
        if ob.name != "disc":
            S.finish(ob, shade=ob.name != "sun", shear=False)
    glow = S.halo("sunglow", 0.1, 0.3, 0.058, 0.75, "glow", 0.55)
    lines(6, 2)
    ortho(2.2, 2.2, 233)
    S.render_to(os.path.join(out_dir, "brand_emblem.png"))
    # Symbol: nur Wabe + Biene, frei stehend
    for ob in list(bpy.data.objects):
        if ob.name in ("disc", "rim", "rim2", "sun", "sunglow") or ob.type == "CAMERA":
            bpy.data.objects.remove(ob, do_unlink=True)
    del glow
    ortho(2.2, 2.2, 233)
    S.render_to(os.path.join(out_dir, "brand_icon.png"))


def main():
    out_dir = S.args()[0]
    os.makedirs(out_dir, exist_ok=True)
    title(out_dir)
    emblem(out_dir)
    print("BRAND DONE")


main()
