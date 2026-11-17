import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
import hive_style as S
S.reset()
OUT = os.path.join(os.path.dirname(__file__), "_test"); os.makedirs(OUT, exist_ok=True)
# Honigfass
parts = []
parts.append(S.cylinder("fass", 0, 0.45, 0, 1.0, 0.42, "wood", seg=28))
for z in (0.12, 0.88):
    parts.append(S.cylinder("reif", 0, 0.45, z - 0.04, z + 0.04, 0.435, "iron", seg=28))
parts.append(S.cylinder("deckel", 0, 0.45, 1.0, 1.03, 0.38, "honey", seg=28))
for ob in parts: S.finish(ob)
print(S.render_sprite(parts, os.path.join(OUT, "fass.png")))
for ob in parts: ob.hide_render = True
# Wabenkiste
parts2 = [S.box("kiste", -0.6, 0, 0, 0.6, 0.7, 0.55, "wood_light", bevel=0.02)]
for i, (cx, cz) in enumerate([(-0.3, 0.3), (0.0, 0.3), (0.3, 0.3)]):
    parts2.append(S.prism(f"wabe{i}", S.hexagon_pts(cx, -0.001, 0.13), 0.12, 0.42, "comb"))
for ob in parts2: S.finish(ob)
print(S.render_sprite(parts2, os.path.join(OUT, "kiste.png")))
