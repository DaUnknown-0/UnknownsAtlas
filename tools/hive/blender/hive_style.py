# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# hive_style.py - gemeinsamer Blender-Stil fuer alle Amberhive-Grafiken (Boden, Waende, Objekte, Konsolen, Tueren, Szenen).
# Stil V2 "Bernsteinlicht" (15.11.2026), Beschreibung in art/STIL_V2.md.
# Nur in Blender (bpy) importieren:  blender -b --factory-startup -P <skript>.py -- <argumente>
#
# Among-Us-Schraegblick: die Karte ist eine Aufsicht, alles Hohe ragt nach Norden ins Bild. Umgesetzt als Scherung der fertigen
# Geometrie (y' = y + K * z) und eine senkrechte Orthokamera von oben. Damit liegen Boden und Fuss eines Objekts genau auf
# ihren Weltkoordinaten, Stirnseiten (Normale nach Sueden) werden sichtbar, Deckflaechen wandern um K * Hoehe nach Norden.
#
# Schattierung V2: weiches Cel-Licht, komplett im Material gerechnet (Emission, keine Lampen, kein Rauschen, reproduzierbar).
# finish() merkt sich die Normalen VOR der Scherung als eigene Normalen; das Material rechnet daraus
#   - drei weiche Lichtstufen (Licht von links-vorn-oben, Schatten ins Pflaumenbraune statt ins Graue),
#   - Glanzlicht (Metall, Honig, Glas), Randabdunklung an runden Koerpern, Umgebungsverschattung (AO) in Ritzen,
#   - Abdunklung zum Boden hin (nur Objekte) und eine leise Maserung (Holz laengs zum Bauteil, Wachs wolkig).
# Farben kommen aus PALETTE (je Farbe ein Material, damit Freestyle an Farbgrenzen eine feine Linie zieht).
# Umriss: Freestyle, aussen kraeftig (Propolis-Pflaume), innen fein und halb durchsichtig.
#
# Einheiten: 1 Blender-Einheit = 1 m = 1 Atlas-Welteinheit. Objekte stehen mit dem Fuss auf z = 0; ihr Ursprung (0,0,0) ist der
# Ankerpunkt (Mitte der Standlinie). render_sprite() schreibt PNG + JSON {w, h, ox, oy} (Pixel des Ankers, Zeile 0 = oben).

import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

K = 0.59                       # Schraegblick (Stirnhoehe 1 m -> 0,59 m im Bild), wie Skeld/BlenderMaps
LINE = (0.17, 0.085, 0.075)    # Umrisslinie (Propolis-Pflaume)
LINE_OUTER_M = 0.027           # Aussenkontur in Metern (bei 120 px/m gut 3 px)
LINE_INNER_M = 0.011           # Innenkanten
LINE_INNER_ALPHA = 0.62
SMOOTH_DEG = 38.0              # Kanten flacher als das werden weich schattiert (runde Koerper ohne Facetten)

LIGHT = Vector((-0.42, -0.30, 0.86)).normalized()      # Hauptlicht: von links (Westen), leicht von vorn, steil von oben
VIEW = Vector((0.0, -K, 1.0)).normalized()             # Blickrichtung des Schraegblicks (zum Betrachter)
GROUND_FADE = True             # Objekte dunkeln zum Boden hin ab; Boden-/Szenenskripte schalten das vor dem ersten Material aus
AO = os.environ.get("HIVE_AO", "1") != "0"   # Umgebungsverschattung im Material (HIVE_AO=0 schaltet sie zum Vergleich ab)

PALETTE = {
    # Wachs und Waben
    "wax": (0.95, 0.80, 0.50), "wax_light": (1.0, 0.90, 0.66), "wax_dark": (0.78, 0.58, 0.30), "comb": (0.92, 0.66, 0.24),
    "honey": (0.97, 0.58, 0.08), "honey_light": (1.0, 0.77, 0.28), "honey_deep": (0.74, 0.34, 0.05), "amber_glass": (1.0, 0.63, 0.16),
    "propolis": (0.30, 0.17, 0.12), "propolis_light": (0.46, 0.28, 0.17),
    # Holz, Metall, Stoff
    "wood": (0.58, 0.37, 0.22), "wood_light": (0.75, 0.53, 0.32), "wood_dark": (0.39, 0.23, 0.15),
    "brass": (0.92, 0.71, 0.30), "brass_dark": (0.64, 0.45, 0.18), "iron": (0.33, 0.34, 0.39), "iron_light": (0.57, 0.59, 0.64),
    "copper": (0.84, 0.47, 0.30), "glass": (0.74, 0.92, 0.95), "cloth_white": (0.96, 0.95, 0.90), "cloth_cream": (0.93, 0.87, 0.73),
    "rope": (0.77, 0.65, 0.45), "paper": (0.97, 0.93, 0.80), "ink": (0.19, 0.15, 0.17),
    # Natur und Akzente
    "leaf": (0.40, 0.64, 0.30), "leaf_dark": (0.24, 0.44, 0.22), "moss": (0.50, 0.66, 0.34), "petal_pink": (0.98, 0.60, 0.70),
    "petal_white": (0.99, 0.97, 0.92), "petal_blue": (0.45, 0.66, 0.97), "pollen": (1.0, 0.85, 0.20), "royal": (0.50, 0.24, 0.58),
    "royal_light": (0.70, 0.44, 0.76), "red": (0.84, 0.24, 0.20), "teal": (0.16, 0.60, 0.60), "black": (0.12, 0.10, 0.11),
    "white": (0.98, 0.97, 0.94), "bee_yellow": (1.0, 0.80, 0.14), "bee_black": (0.16, 0.13, 0.12), "wing": (0.86, 0.95, 1.0),
    "glow": (1.0, 0.88, 0.50),
    # neu in V2: Akzente
    "teal_light": (0.46, 0.80, 0.76), "teal_dark": (0.10, 0.40, 0.43), "verdigris": (0.44, 0.72, 0.62),
    "leather": (0.63, 0.34, 0.22), "leather_dark": (0.44, 0.22, 0.15), "stone": (0.63, 0.61, 0.60), "stone_dark": (0.44, 0.43, 0.45),
    "flame": (1.0, 0.52, 0.10), "flame_core": (1.0, 0.93, 0.60), "royal_dark": (0.34, 0.15, 0.42), "coral": (0.95, 0.47, 0.40),
    "larva": (0.99, 0.93, 0.84), "night": (0.16, 0.14, 0.24),
    # neu in V2: gestrichenes Holz (Bienenkaesten sind pastellfarben gestrichen), bricht das viele Braun
    "paint_teal": (0.34, 0.62, 0.62), "paint_teal_dark": (0.21, 0.42, 0.46), "paint_cream": (0.94, 0.89, 0.77),
    "paint_coral": (0.90, 0.53, 0.45), "paint_mint": (0.62, 0.81, 0.70), "paint_blue": (0.47, 0.63, 0.81),
    "paint_blue_dark": (0.30, 0.42, 0.62), "paint_plum": (0.52, 0.33, 0.50),
    # neu in V2: Boden (ruhig, wenig gesaettigt, hell genug fuer den Sichtschatten des Spiels) und Wandmasse
    "fl_joint": (0.50, 0.43, 0.37), "fl_wax": (0.80, 0.75, 0.65), "fl_wax_b": (0.76, 0.70, 0.60), "fl_wax_c": (0.84, 0.79, 0.69),
    "fl_plank": (0.68, 0.56, 0.45), "fl_plank_b": (0.63, 0.51, 0.41), "fl_plank_c": (0.72, 0.60, 0.48),
    "fl_plank_dark": (0.52, 0.45, 0.42), "fl_plank_dark_b": (0.47, 0.41, 0.39), "fl_slate": (0.50, 0.53, 0.58),
    "fl_slate_b": (0.45, 0.48, 0.54), "fl_slate_c": (0.55, 0.58, 0.62), "fl_stone": (0.67, 0.64, 0.60), "fl_stone_b": (0.61, 0.58, 0.55),
    "fl_sand": (0.77, 0.70, 0.59), "fl_sand_b": (0.71, 0.64, 0.54), "fl_clay": (0.72, 0.54, 0.46), "fl_clay_b": (0.66, 0.48, 0.42),
    "fl_sage": (0.67, 0.73, 0.63), "fl_sage_b": (0.60, 0.67, 0.58), "fl_mint": (0.74, 0.80, 0.73), "fl_cream": (0.87, 0.83, 0.76),
    "fl_rose": (0.85, 0.75, 0.73), "fl_lilac": (0.76, 0.71, 0.79), "fl_lilac_b": (0.70, 0.64, 0.75), "fl_violet": (0.56, 0.44, 0.63),
    "fl_teal": (0.40, 0.56, 0.55), "fl_teal_b": (0.33, 0.48, 0.49), "fl_inlay": (0.80, 0.66, 0.38), "fl_sun": (0.88, 0.82, 0.66),
    "wall_top": (0.26, 0.16, 0.13), "wall_cell": (0.33, 0.20, 0.15), "wall_cell_b": (0.29, 0.18, 0.15), "wall_cell_c": (0.38, 0.23, 0.15),
    "wall_lip": (0.88, 0.68, 0.34), "wall_front": (0.86, 0.60, 0.24), "wall_front_b": (0.74, 0.47, 0.17), "wall_base": (0.36, 0.20, 0.12),
    "wall_glow": (1.0, 0.72, 0.22), "lake": (0.93, 0.52, 0.06), "lake_deep": (0.70, 0.30, 0.04), "lake_light": (1.0, 0.72, 0.22),
}
SHADE = {"top": 1.0, "south": 0.80, "side": 0.90, "north": 0.72, "bottom": 0.65}     # V1, nur noch fuer alte Aufrufer

# Materialart je Palettenfarbe: spec (Glanzstaerke), gloss (Schaerfe), sss (Durchscheinen: hellt Schatten auf),
# rim (Randabdunklung), tex (Art der Maserung), amt (Staerke), scale (Groesse)
_KIND = {
    "matte": dict(spec=0.0, gloss=12, sss=0.0, rim=0.16, tex="cloud", amt=0.05, scale=5.0),
    "wood": dict(spec=0.05, gloss=10, sss=0.0, rim=0.16, tex="grain", amt=0.13, scale=7.0),
    "wax": dict(spec=0.16, gloss=14, sss=0.34, rim=0.12, tex="cloud", amt=0.05, scale=3.5),
    "metal": dict(spec=0.62, gloss=22, sss=0.0, rim=0.26, tex="cloud", amt=0.03, scale=9.0),
    "gloss": dict(spec=0.85, gloss=46, sss=0.55, rim=0.10, tex="none", amt=0.0, scale=1.0),
    "leaf": dict(spec=0.08, gloss=12, sss=0.25, rim=0.14, tex="cloud", amt=0.06, scale=8.0),
    "cloth": dict(spec=0.0, gloss=10, sss=0.12, rim=0.14, tex="cloud", amt=0.04, scale=10.0),
    "floor": dict(spec=0.0, gloss=10, sss=0.0, rim=0.0, tex="floor", amt=0.055, scale=1.1),
    "stone": dict(spec=0.04, gloss=10, sss=0.0, rim=0.16, tex="cloud", amt=0.08, scale=6.0),
    "wallfront": dict(spec=0.10, gloss=14, sss=0.45, rim=0.0, tex="cloud", amt=0.07, scale=2.2, zgrad=(0.0, 1.4, 0.56, 1.14)),
    "paint": dict(spec=0.10, gloss=12, sss=0.0, rim=0.16, tex="grain", amt=0.06, scale=7.0),
}
_KIND_OF = {
    "wood": "wood", "wood_light": "wood", "wood_dark": "wood", "propolis": "wood", "propolis_light": "wood",
    "wax": "wax", "wax_light": "wax", "wax_dark": "wax", "comb": "wax", "larva": "wax", "wall_lip": "wax", "wall_front": "wallfront",
    "wall_front_b": "wax",
    "brass": "metal", "brass_dark": "metal", "iron": "metal", "iron_light": "metal", "copper": "metal", "verdigris": "metal",
    "honey": "gloss", "honey_light": "gloss", "honey_deep": "gloss", "amber_glass": "gloss", "glass": "gloss", "wing": "gloss",
    "black": "gloss", "bee_black": "gloss", "lake": "gloss", "lake_deep": "gloss", "lake_light": "gloss", "wall_glow": "gloss",
    "leaf": "leaf", "leaf_dark": "leaf", "moss": "leaf", "petal_pink": "leaf", "petal_white": "leaf", "petal_blue": "leaf",
    "pollen": "leaf", "bee_yellow": "leaf",
    "cloth_white": "cloth", "cloth_cream": "cloth", "rope": "cloth", "paper": "cloth", "royal": "cloth", "royal_light": "cloth",
    "royal_dark": "cloth", "leather": "cloth", "leather_dark": "cloth",
    "stone": "stone", "stone_dark": "stone", "wall_top": "stone", "wall_cell": "stone", "wall_cell_b": "stone",
    "wall_cell_c": "stone", "wall_base": "stone",
}

BLENDER = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"


def kind_of(name):
    if not isinstance(name, str):
        return "matte"
    if name.startswith("fl_"):
        return "floor"
    if name.startswith("paint_"):
        return "paint"
    return _KIND_OF.get(name, "matte")


# ------------------------------------------------------------------ Szene

def nolines():
    """Sammlung fuer Teile ohne Freestyle-Linie (Schatten, Lichthoefe, Kleinstteile)."""
    sc = bpy.context.scene
    c = bpy.data.collections.get("nolines") or bpy.data.collections.new("nolines")
    if c.name not in sc.collection.children:
        sc.collection.children.link(c)
    return c


def reset():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.dither_intensity = 0.0
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    for attr, val in (("taa_render_samples", 24), ("use_gtao", True), ("gtao_distance", 0.45), ("fast_gi_distance", 0.45),
                      ("use_shadows", False), ("use_raytracing", False)):
        try:
            setattr(sc.eevee, attr, val)
        except (AttributeError, TypeError):
            pass
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0
    fs = sc.view_layers[0].freestyle_settings
    fs.crease_angle = math.radians(140)
    # zwei Linien: Aussenkontur (Silhouette, Rand) kraeftig, Innenkanten (Knick, Farbgrenze) fein und halb durchsichtig
    for old in list(fs.linesets):               # frisch anlegen (ein Skript kann vorher eigene Linien gesetzt haben)
        fs.linesets.remove(old)
    outer, inner = fs.linesets.new("outer"), fs.linesets.new("inner")
    nl = nolines()
    for ls in (outer, inner):
        ls.select_by_visibility = True
        ls.visibility = "VISIBLE"
        ls.select_by_edge_types = True
        ls.select_by_collection = True
        ls.collection = nl
        ls.collection_negation = "EXCLUSIVE"
        ls.linestyle.color = lin(LINE)
        ls.linestyle.alpha = 1.0
        ls.linestyle.thickness_position = "CENTER"
    inner.linestyle.alpha = LINE_INNER_ALPHA
    outer.select_silhouette, outer.select_border, outer.select_crease, outer.select_material_boundary = True, True, False, False
    inner.select_silhouette, inner.select_border, inner.select_crease, inner.select_material_boundary = False, False, True, True
    outer.name, inner.name = "outer", "inner"
    return sc


def lin(c):
    """sRGB (0..1) -> linear, damit die Palettenfarben im Bild genau so erscheinen (View Transform Standard)."""
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ------------------------------------------------------------------ Material (Cel-Licht in Knoten)

class _N:
    """Kleine Knoten-Fabrik: Zahlen und Ausgaenge mischen, ohne jede Verbindung einzeln zu schreiben."""

    def __init__(self, nt):
        self.nt = nt

    def _set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif isinstance(v, (tuple, list, Vector)):
            sock.default_value = tuple(v) if len(sock.default_value) == len(v) else (*v, 1.0)
        else:
            sock.default_value = v

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        self._set(n.inputs[0], a)
        self._set(n.inputs[1], b)
        self._set(n.inputs[2], c)
        return n.outputs[0]

    def vec(self, op, a, b=(0, 0, 0), scale=None):
        n = self.nt.nodes.new("ShaderNodeVectorMath")
        n.operation = op
        self._set(n.inputs[0], a)
        self._set(n.inputs[1], b)
        if scale is not None:
            self._set(n.inputs["Scale"], scale)
        return n.outputs["Value"] if op == "DOT_PRODUCT" else n.outputs["Vector"]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = blend
        n.clamp_factor = True
        self._set(n.inputs[0], fac)
        self._set(n.inputs[6], a)
        self._set(n.inputs[7], b)
        return n.outputs[2]

    def smooth(self, v, lo, hi, out0=0.0, out1=1.0):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        n.interpolation_type = "SMOOTHSTEP"
        self._set(n.inputs["Value"], v)
        n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = lo, hi
        n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = out0, out1
        return n.outputs["Result"]

    def attr(self, name):
        n = self.nt.nodes.new("ShaderNodeAttribute")
        n.attribute_name = name
        return n

    def noise(self, vec, scale, detail=2.0, rough=0.55):
        n = self.nt.nodes.new("ShaderNodeTexNoise")
        n.noise_dimensions = "3D"
        self.nt.links.new(vec, n.inputs["Vector"])
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        return n.outputs[0]


# Lichtstufen (linear): Position = halber Lambert (N.L * 0,5 + 0,5), Farbe = Faktor auf die Palettenfarbe.
# Deckflaechen (0,93) = 1,0; Stirnseiten nach Sueden (0,65) = 0,76; abgewandte Seiten = Pflaumenschatten.
_RAMP = ((0.00, (0.31, 0.25, 0.31)), (0.36, (0.38, 0.32, 0.37)), (0.47, (0.68, 0.63, 0.63)), (0.70, (0.76, 0.72, 0.70)),
         (0.84, (1.0, 1.0, 1.0)), (0.95, (1.0, 1.0, 1.0)), (1.00, (1.10, 1.07, 0.98)))


def _lit_tree(m, col, kind):
    p = _KIND[kind]
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N = _N(nt)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nrm = geo.outputs["Normal"]
    base = N.vec("MULTIPLY", (*col,), N.attr("tint").outputs["Color"])
    base = N.vec("MULTIPLY", base, N.attr("shade").outputs["Color"])       # V1-Attribut: eject_common schreibt hier eigene Stufen
    # Lichtstufen
    t = N.math("MULTIPLY_ADD", N.vec("DOT_PRODUCT", nrm, tuple(LIGHT)), 0.5, 0.5, clamp=True)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    for i, (pos, c) in enumerate(_RAMP):
        el = cr.elements[i] if i < 2 else cr.elements.new(pos)
        el.position = pos
        el.color = (*c, 1.0)
    nt.links.new(t, ramp.inputs[0])
    shade = ramp.outputs[0]
    if p["sss"] > 0:                                   # Durchscheinen: Schatten heller und waermer
        shade = N.mix(p["sss"] * 0.6, shade, (1.0, 0.94, 0.86, 1.0))
    lit = N.vec("MULTIPLY", base, shade)
    # Maserung auf den ungescherten Koordinaten
    if p["tex"] != "none" and p["amt"] > 0:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(sep.outputs["X"], comb.inputs["X"])
        nt.links.new(N.math("MULTIPLY_ADD", sep.outputs["Z"], -K, sep.outputs["Y"]), comb.inputs["Y"])
        nt.links.new(sep.outputs["Z"], comb.inputs["Z"])
        pos = comb.outputs[0]
        if p["tex"] == "grain":
            pos = N.vec("MULTIPLY", pos, N.attr("grain").outputs["Color"])
            f = N.noise(pos, p["scale"], 3.0, 0.6)
        elif p["tex"] == "floor":
            f = N.math("MULTIPLY_ADD", N.noise(pos, p["scale"], 2.0, 0.5), 0.7, N.math("MULTIPLY", N.noise(pos, 13.0, 1.0, 0.5), 0.3))
        else:
            f = N.noise(pos, p["scale"], 2.0, 0.55)
        lit = N.vec("SCALE", lit, scale=N.math("MULTIPLY_ADD", N.math("SUBTRACT", f, 0.5), 2.0 * p["amt"], 1.0))
        if kind != "floor":                            # dazu eine leise, grosse Wolke, damit grosse Flaechen nicht tot wirken
            f2 = N.noise(comb.outputs[0], 1.4, 1.0, 0.5)
            lit = N.vec("SCALE", lit, scale=N.math("MULTIPLY_ADD", N.math("SUBTRACT", f2, 0.5), 0.16, 1.0))
    # Umgebungsverschattung
    if AO:
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.35
        try:
            ao.samples = 16
        except AttributeError:
            pass
        a = N.math("MULTIPLY_ADD", ao.outputs["AO"], 0.55, 0.45)
        lit = N.mix(1.0, lit, N.mix(a, (0.50, 0.38, 0.46, 1.0), (1, 1, 1, 1)), blend="MULTIPLY")
    # Abdunklung zum Boden
    if GROUND_FADE and kind != "floor":
        sepz = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sepz.inputs[0])
        lit = N.vec("SCALE", lit, scale=N.smooth(sepz.outputs["Z"], 0.0, 0.32, 0.80, 1.0))
    if p.get("zgrad"):                               # Hoehenverlauf (Wandstirn: oben hell, zum Fuss satt und dunkel)
        z0, z1, m0, m1 = p["zgrad"]
        sepg = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sepg.inputs[0])
        lit = N.vec("SCALE", lit, scale=N.smooth(sepg.outputs["Z"], z0, z1, m0, m1))
    # Randabdunklung
    if p["rim"] > 0:
        f = N.math("SUBTRACT", 1.0, N.vec("DOT_PRODUCT", nrm, tuple(VIEW)))
        lit = N.vec("SCALE", lit, scale=N.math("SUBTRACT", 1.0, N.smooth(f, 0.62, 1.0, 0.0, p["rim"])))
    # Glanzlicht
    if p["spec"] > 0:
        h = (LIGHT + VIEW).normalized()
        s = N.math("POWER", N.math("MAXIMUM", N.vec("DOT_PRODUCT", nrm, tuple(h)), 0.0), float(p["gloss"]))
        lit = N.mix(N.smooth(s, 0.30, 0.72, 0.0, p["spec"]), lit, (1.0, 0.96, 0.84, 1.0))
    # unbeleuchtete Teile (Leuchtendes): reine Farbe
    res = N.mix(N.attr("lit").outputs["Fac"], base, lit)
    nt.links.new(res, em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs[0])


def material(name, kind=None):
    """Material einer Palettenfarbe (Name) oder eines sRGB-Tupels; kind ueberschreibt die Materialart (siehe _KIND)."""
    key = f"hive_{name}" + (f"_{kind}" if kind else "")
    m = bpy.data.materials.get(key)
    if m:
        return m
    col = lin(PALETTE[name] if isinstance(name, str) else name)
    m = bpy.data.materials.new(key)
    _lit_tree(m, col, kind or kind_of(name))
    m.diffuse_color = (*col, 1.0)
    return m


def soft_material(name, color, strength=1.0):
    """Durchscheinendes Material fuer Schatten und Lichthoefe: Deckkraft aus dem Punkt-Attribut 'a'."""
    key = f"hive_soft_{name}"
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N = _N(nt)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(color), 1.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(N.math("MULTIPLY", N.attr("a").outputs["Fac"], strength, clamp=True), mixs.inputs[0])
    nt.links.new(tr.outputs[0], mixs.inputs[1])
    nt.links.new(em.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    return m


def face_shade(n):
    """V1: Helligkeitsfaktor einer Flaeche nach ihrer Normalen. Nur noch fuer alte Aufrufer."""
    if n.z > 0.75:
        return SHADE["top"]
    if n.z < -0.75:
        return SHADE["bottom"]
    h = Vector((n.x, n.y, 0)).normalized() if (n.x or n.y) else Vector((0, -1, 0))
    south, north, side = max(0.0, -h.y), max(0.0, h.y), abs(h.x)
    f = (south * SHADE["south"] + north * SHADE["north"] + side * SHADE["side"]) / max(1e-6, south + north + side)
    if n.z > 0.15:
        f = f + (SHADE["top"] - f) * min(1.0, n.z / 0.75)
    return f


def _fill_attr(me, name, value, keep=False):
    a = me.color_attributes.get(name)
    if a is not None and keep:
        return
    if a is None:
        a = me.color_attributes.new(name, "FLOAT_COLOR", "CORNER")
    n = len(a.data)
    if n:
        a.data.foreach_set("color", list(value) * n)


def finish(ob, shade=True, shear=True, smooth=SMOOTH_DEG):
    """Transformationen anwenden, Normalen vor der Scherung merken, scheren (Schraegblick). Danach nicht mehr bewegen.
    shade=False: Teil bleibt unbeleuchtet (reine Palettenfarbe, fuer Leuchtendes)."""
    bpy.context.view_layer.update()          # gesetzte location/rotation/scale erst in matrix_world uebernehmen
    me = ob.data
    mw = ob.matrix_world.copy()
    me.transform(mw)
    ob.matrix_world.identity()
    me.update()
    n_loops = len(me.loops)
    if n_loops == 0:
        return ob
    # weich schattieren, Kanten ueber dem Grenzwinkel bleiben hart
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = math.radians(smooth)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        lf = e.link_faces
        e.smooth = len(lf) == 2 and e.calc_face_angle(0.0) < lim and lf[0].material_index == lf[1].material_index
    dims = [max(v.co[i] for v in bm.verts) - min(v.co[i] for v in bm.verts) for i in range(3)] if bm.verts else [1, 1, 1]
    bm.to_mesh(me)
    bm.free()
    me.update()
    normals = [0.0] * (n_loops * 3)
    me.corner_normals.foreach_get("vector", normals)
    # Attribute: beleuchtet?, Farbstich (bleibt, wenn der Aufrufer ihn schon gesetzt hat), Maserrichtung (laengste Achse)
    lit = 1.0 if shade else 0.0
    _fill_attr(me, "lit", (lit, lit, lit, 1.0))
    _fill_attr(me, "shade", (1.0, 1.0, 1.0, 1.0))        # V1-Vertrag: Helligkeitsfaktor je Flaeche, Aufrufer duerfen ihn ueberschreiben
    _fill_attr(me, "tint", (1.0, 1.0, 1.0, 1.0), keep=True)
    g = [1.0, 1.0, 1.0]
    g[dims.index(max(dims))] = 0.14
    _fill_attr(me, "grain", (*g, 1.0))
    if shear:
        for v in me.vertices:
            v.co.y += K * v.co.z
    me.normals_split_custom_set([tuple(normals[i:i + 3]) for i in range(0, len(normals), 3)])
    me.update()
    return ob


# ------------------------------------------------------------------ Bausteine (Weltmeter, Fuss auf z = 0)

REMAP = {}          # Farbtausch je Objekt (props_common.SKIN): Palettenname -> Palettenname


def _obj(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in (mat if isinstance(mat, list) else [mat]):
        me.materials.append(material(REMAP.get(m, m) if isinstance(m, str) else m))
    return ob


def box(name, x0, y0, z0, x1, y1, z1, mat, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES", profile=0.5)
    return _obj(name, bm, mat)


def cylinder(name, cx, cy, z0, z1, r, mat, seg=24, r_top=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r_top is None else r_top,
                          depth=z1 - z0)
    for v in bm.verts:
        v.co.x += cx; v.co.y += cy; v.co.z += (z0 + z1) / 2
    return _obj(name, bm, mat)


def prism(name, pts, z0, z1, mat):
    """Senkrechtes Prisma ueber einem Grundriss (Punkte gegen den Uhrzeigersinn)."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.normal_update()
    return _obj(name, bm, mat)


def hexagon_pts(cx, cy, r, flat=True, rot=0.0):
    a0 = 0.0 if flat else math.pi / 6
    return [(cx + r * math.cos(a0 + rot + math.pi / 3 * i), cy + r * math.sin(a0 + rot + math.pi / 3 * i)) for i in range(6)]


def sphere(name, cx, cy, cz, r, mat, seg=20, sz=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=r)
    for v in bm.verts:
        v.co.z *= sz
        v.co.x += cx; v.co.y += cy; v.co.z += cz
    return _obj(name, bm, mat)


def torus(name, cx, cy, cz, R, r, mat, seg=32, ring=10):
    bm = bmesh.new()
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(ring):
            b = 2 * math.pi * j / ring
            row.append(bm.verts.new((cx + (R + r * math.cos(b)) * math.cos(a), cy + (R + r * math.cos(b)) * math.sin(a),
                                     cz + r * math.sin(b))))
        verts.append(row)
    for i in range(seg):
        for j in range(ring):
            bm.faces.new((verts[i][j], verts[(i + 1) % seg][j], verts[(i + 1) % seg][(j + 1) % ring], verts[i][(j + 1) % ring]))
    bm.normal_update()
    return _obj(name, bm, mat)


# ------------------------------------------------------------------ Weiches: Bodenschatten und Lichthoefe (ohne Linie)

_FALL = ((0.0, 1.0), (0.3, 0.86), (0.55, 0.5), (0.8, 0.16), (1.0, 0.0))      # Abstand vom Kern (0..1) -> Deckkraft


def soft_blob(name, outline, grow, color, strength, z=0.004, center=None):
    """Weicher Fleck: Umriss (Liste x,y, konvex) voll deckend, laeuft ueber 'grow' Meter nach aussen auf null aus.
    Liegt flach auf Hoehe z (wird hier gleich geschert). Fuer Bodenschatten unter Objekten und Lichthoefe."""
    cx = center[0] if center else sum(p[0] for p in outline) / len(outline)
    cy = center[1] if center else sum(p[1] for p in outline) / len(outline)
    bm = bmesh.new()
    lay = bm.loops.layers.float_color.new("a")
    rings = []
    for t, a in _FALL:
        ring = []
        for x, y in outline:
            d = math.hypot(x - cx, y - cy) or 1e-6
            k = (d + grow * (t * 1.6 - 0.6)) / d if t > 0 else max(0.05, (d - grow * 0.6) / d)
            ring.append(bm.verts.new((cx + (x - cx) * k, cy + (y - cy) * k + K * z, z)))
        rings.append((ring, a))
    f = bm.faces.new(rings[0][0])
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
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(soft_material(f"{name}_{color}_{strength}", color if not isinstance(color, str) else PALETTE[color], strength))
    ob = bpy.data.objects.new(name, me)
    nolines().objects.link(ob)
    ob["hive_soft"] = True
    return ob


def ground_shadow(shape, w, d, height, name="shadow"):
    """Bodenschatten eines Objekts mit Grundflaeche w x d (shape 'rect' oder 'circle'), faellt nach rechts unten."""
    k = min(1.0, 0.45 + height * 0.35)
    ox, oy = 0.05 * k, -0.045 * k
    if shape == "circle":
        r = w / 2 * 0.93
        pts = [(ox + r * math.cos(2 * math.pi * i / 28), d / 2 + oy + r * math.sin(2 * math.pi * i / 28)) for i in range(28)]
    else:
        rad = min(0.16, w * 0.3, d * 0.45)
        x0, x1, y0, y1 = -w / 2 + 0.03, w / 2 - 0.03, 0.02, d - 0.04
        pts = []
        for cxk, cyk, a0 in ((x1 - rad, y1 - rad, 0), (x0 + rad, y1 - rad, 90), (x0 + rad, y0 + rad, 180), (x1 - rad, y0 + rad, 270)):
            for i in range(6):
                a = math.radians(a0 + 90 * i / 5)
                pts.append((cxk + rad * math.cos(a) + ox, cyk + rad * math.sin(a) + oy))
    return soft_blob(name, pts, 0.10 + 0.05 * k, (0.13, 0.07, 0.10), 0.42 * k, z=0.003)


def halo(name, cx, cy, cz, r, color="glow", strength=0.6):
    """Lichthof um etwas Leuchtendes: flache Scheibe auf Hoehe cz (ungeschert angeben), laeuft nach aussen aus."""
    core = r * 0.3
    pts = [(cx + core * math.cos(2 * math.pi * i / 24), cy + core * math.sin(2 * math.pi * i / 24)) for i in range(24)]
    return soft_blob(name, pts, (r - core) / 1.0, color, strength, z=cz, center=(cx, cy))


# ------------------------------------------------------------------ Rendern

def set_lines(ppm, line_m=LINE_OUTER_M, inner_m=LINE_INNER_M):
    sc = bpy.context.scene
    sc.render.line_thickness = 1.0
    for ls in sc.view_layers[0].freestyle_settings.linesets:
        ls.linestyle.thickness = max(1.0, (line_m if ls.name == "outer" else inner_m) * ppm)
        ls.linestyle.thickness_position = "CENTER"


def render_to(path):
    """Bild rendern. Vorher ein winziger Probelauf ohne Linien: EEVEE uebersetzt neue Materialien im Hintergrund, und ein
    Bild, das waehrenddessen entsteht, wird gleichmaessig zu dunkel (am 15.11. beobachtet, erster Lauf nach Materialaenderung)."""
    sc = bpy.context.scene
    keep = (sc.render.use_freestyle, sc.render.resolution_percentage, sc.eevee.taa_render_samples)
    sc.render.use_freestyle = False
    sc.render.resolution_percentage = max(1, min(100, int(6400 / max(sc.render.resolution_x, sc.render.resolution_y, 64))))
    sc.eevee.taa_render_samples = 1
    bpy.ops.render.render(write_still=False)
    sc.render.use_freestyle, sc.render.resolution_percentage, sc.eevee.taa_render_samples = keep
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_sprite(objects, out_png, ppm=120, margin=0.08, line_m=LINE_OUTER_M, inner_m=LINE_INNER_M, extra_bounds=None):
    """Objekte (schon mit finish() geschert) von oben rendern. Schreibt PNG und <name>.json mit Ankerpixel (Welt 0/0)."""
    sc = bpy.context.scene
    xs, ys = [], []
    for ob in objects:
        for v in ob.data.vertices:
            co = ob.matrix_world @ v.co
            xs.append(co.x); ys.append(co.y)
    if extra_bounds:
        xs += [extra_bounds[0], extra_bounds[2]]; ys += [extra_bounds[1], extra_bounds[3]]
    x0, x1 = min(xs) - margin, max(xs) + margin
    y0, y1 = min(ys) - margin, max(ys) + margin
    w_px = max(4, int(math.ceil((x1 - x0) * ppm / 4.0)) * 4)
    h_px = max(4, int(math.ceil((y1 - y0) * ppm / 4.0)) * 4)
    x1, y1 = x0 + w_px / ppm, y0 + h_px / ppm
    cam_data = bpy.data.cameras.new("hive_cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(x1 - x0, y1 - y0)
    cam_data.sensor_fit = "AUTO"
    cam = bpy.data.objects.new("hive_cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = ((x0 + x1) / 2, (y0 + y1) / 2, 60.0)
    cam.rotation_euler = (0, 0, 0)
    cam_data.clip_start, cam_data.clip_end = 1.0, 200.0
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w_px, h_px
    sc.render.resolution_percentage = 100
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1.0
    set_lines(ppm, line_m, inner_m)
    keep = set(ob.name for ob in objects)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.hide_render = ob.name not in keep
    render_to(out_png)
    meta = {"w": w_px, "h": h_px, "ox": round((0 - x0) * ppm, 2), "oy": round((y1 - 0) * ppm, 2), "ppm": ppm,
            "x0": round(x0, 4), "y0": round(y0, 4), "x1": round(x1, 4), "y1": round(y1, 4)}
    with open(os.path.splitext(out_png)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    return meta


def args():
    import sys
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
