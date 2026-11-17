import bpy, sys
print("BLENDER", bpy.app.version_string)
sc = bpy.context.scene
print("engines", [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
print("freestyle attr", hasattr(sc.render, "use_freestyle"))
try:
    sc.render.use_freestyle = True
    print("freestyle ok", sc.view_layers[0].freestyle_settings is not None)
except Exception as e:
    print("freestyle FAIL", e)
