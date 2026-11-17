# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# fx_build.py - Laufzeitbilder von Amberhive rendern (Stil V2):
#   - flache Teile aus _out/fx.json (Bruecke, Honiglachen, Knoepfe; fx_geo.py) in reiner Draufsicht
#   - Bienen (3D, Schraegblick) in zwei Fluegelstellungen: task_hive_bee_0.png / _1.png
#   blender -b --factory-startup -P fx_build.py -- <ausgabeordner>

import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import hive_style as S  # noqa: E402
import floor_build as FB  # noqa: E402


def render_bounds(bounds, ppm, out_png):
    sc = bpy.context.scene
    x0, y0, x1, y1 = bounds
    w_px, h_px = max(4, int(round((x1 - x0) * ppm)) // 4 * 4), max(4, int(round((y1 - y0) * ppm)) // 4 * 4)
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
    bpy.data.objects.remove(cam, do_unlink=True)


def linesets(ppm):
    fs = bpy.context.scene.view_layers[0].freestyle_settings
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    FB.lineset("deco", "deco", {"silhouette", "border", "crease", "material"}, 0.03 * ppm, S.LINE)
    FB.lineset("decal", "decal", {"border", "material"}, 0.016 * ppm, S.LINE, 0.7)


def flat_items(out_dir):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    items = json.load(open(os.path.join(here, "_out", "fx.json"), encoding="utf-8"))
    for it in items:
        S.reset()
        objs = FB.build_groups(it["shapes"])
        if it.get("grain"):                                   # Maserrichtung vorgeben (Dielen der Bruecke laufen quer)
            for ob in objs.values():
                S._fill_attr(ob.data, "grain", (*it["grain"], 1.0))
        linesets(it["ppm"])
        render_bounds(it["bounds"], it["ppm"], os.path.join(out_dir, it["name"] + ".png"))
        print("FX", it["name"])


def bee(out_dir):
    """Biene, Blick schraeg von vorn-oben, Kopf nach Westen; zwei Fluegelstellungen. Etwa so gross wie ein Crewmate-Kopf."""
    for k, up in enumerate((True, False)):
        S.reset()
        parts = []
        parts.append(S.sphere("abdomen", 0.09, 0.0, 0.3, 0.17, "bee_yellow", seg=28, sz=0.85))
        for i, dx in enumerate((0.04, 0.15)):
            st = S.torus(f"stripe{i}", 0.0, 0.0, 0.0, 0.14 - 0.03 * i, 0.032, "bee_black", seg=28, ring=8)
            st.rotation_euler = (0, math.radians(90), 0)
            st.location = (dx, 0.0, 0.3)
            parts.append(st)
        parts.append(S.sphere("thorax", -0.12, 0.0, 0.32, 0.12, "propolis_light", seg=20))
        parts.append(S.sphere("head", -0.25, 0.0, 0.32, 0.1, "bee_yellow", seg=20))
        parts.append(S.sphere("eye", -0.3, -0.06, 0.35, 0.04, "black", seg=12))
        parts.append(S.sphere("glint", -0.315, -0.085, 0.37, 0.014, "white", seg=8))
        parts.append(S.sphere("cheek", -0.31, -0.06, 0.29, 0.022, "petal_pink", seg=10))
        for side in (-1, 1):
            w = S.sphere(f"wing{side}", 0.0, 0.0, 0.0, 0.13, "wing", seg=18, sz=0.3)
            w.scale = (0.75, 1.35, 1.0)
            w.rotation_euler = (math.radians(side * (35 if up else -10)), 0, 0)
            w.location = (-0.06, side * 0.13, 0.47 if up else 0.4)
            parts.append(w)
        for ant in (-0.04, 0.04):
            a = S.cylinder(f"ant{ant}", 0.0, 0.0, 0.0, 0.12, 0.01, "bee_black", seg=6)
            a.rotation_euler = (0, math.radians(-35), 0)
            a.location = (-0.3, ant, 0.39)
            parts.append(a)
        for ob in parts:
            S.finish(ob)
        S.render_sprite(parts, os.path.join(out_dir, f"task_hive_bee_{k}.png"), ppm=120, line_m=0.022, inner_m=0.011)
        print("FX bee", k)


def main():
    out_dir = S.args()[0]
    os.makedirs(out_dir, exist_ok=True)
    flat_items(out_dir)
    bee(out_dir)


main()
