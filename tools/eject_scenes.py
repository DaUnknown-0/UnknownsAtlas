"""Unknown's Atlas - Regie der Rauswurf-Szenen -> assets/eject_scenes.json.

Eine Szene ist reine Daten: Objekte mit Keyframes, Partikel-Emitter, Kamera und Ereignisse. Das Spiel
(src/AtlasEject.cs) und das Vorschau-Kino (tools/eject_theater/index.html) spielen dieselbe Datei ab.

Einheiten: Szenen-Einheiten (1 = 180 px der Grafik), Ursprung Mitte des Hintergrunds, y nach oben.
Sichtbar sind bei Zoom 1 genau 11 x 6,2 Einheiten; die Kamera wird auf "bounds" begrenzt.

Keyframe:   [t, {x, y, rot, sx, sy, s, a, b, flip, arc}, ease]
            Jede Eigenschaft wird fuer sich zwischen ihren Keys interpoliert; ease gilt fuer das
            Stueck, das AN diesem Key endet. arc = Wurfbogen-Hoehe fuer y auf diesem Stueck.
            b = Helligkeit (multipliziert die Tint-Farbe), s = Gesamtgroesse (nur Spieler).
Ease:       lin, in, out, io, back (Ueberschwinger), inback (Ausholen), hold (springt am Key)
Objekt:     id, sprite, z (<0 hinter dem Spieler), pivot, depth (Parallax, 1 = Welt), parent
            ("player" = folgt dem Spieler samt Spiegelung), screen (Bildschirmebene), tint,
            keys, wobble [{p, amp, f, t0, t1, ph}], flicker {amp, f, t0, t1}
Emitter:    sprite, z, t0/t1 + rate ODER burst (Zeitpunkt) + n, area [x0,y0,x1,y1],
            vel [vx0,vy0,vx1,vy1], acc [ax,ay], drag, life, size, grow, spin, rot, tint, a,
            fade [ein, aus] (Anteile der Lebenszeit), stretch (entlang der Bewegung)
Objekt-Zusatz: screen = Bildschirmebene (ohne Kamera, Einheiten des Bildschirms 11 x 6,2).
Szene-Zusatz: textStyle "void" = violetter Glitch-Text (UC).
Ereignis:   {t, sound, vol} | {t, shake: [dauer, staerke]} | {t, flash: [farbe, alpha, dauer]}
Frequenzen (wobble.f, flicker.f) in Hz. skip: Szene fuer Skip/Gleichstand (niemand fliegt, kein Spieler).
FX (unten): zentrale Daempfung von Wackeln, Blitzen, Flackern, Leuchten, Partikeln, Vignette und Lautstaerke.

    python tools/eject_scenes.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "eject_scenes.json"


def key(t, ease="io", **p):
    return [t, p, ease]


def em(sprite, z, **kw):
    e = {"sprite": sprite, "z": z}
    e.update(kw)
    return e


def burst(sprite, z, t, n, **kw):
    return em(sprite, z, burst=t, n=n, **kw)


def ev(t, **kw):
    e = {"t": t}
    e.update(kw)
    return e


SCENES = []

# ============================================================================ Museum: Sarkophag
# Aufbau: Grabkammer, Fackeln flackern, Staub im Licht, der Spieler treibt kreiselnd herein.
# Spannung: der Deckel rattelt, gleitet auf, gruenes Leuchten, Sog zieht den Spieler hinein.
# Pointe: Deckel knallt zu (Ueberschwinger), Staubexplosion, Fackeln flammen auf.
# Nachklang: Sand rieselt, ein Lichtschein laeuft ueber das Hieroglyphenband.
SCENES.append({
    "id": "tomb", "map": "museum", "title": "Sarkophag", "length": 6.8, "text": [1.2, 2.8],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.04, x=-0.3, y=0.0), key(3.8, z=1.14, x=0.4, y=-0.35),
               key(4.15, "out", z=1.2, x=0.5, y=-0.5), key(6.8, z=1.1, x=0.3, y=-0.3)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_tomb_bg.jpg", "z": -100},
        {"id": "glowL", "sprite": "task_eject_glow.png", "z": -52, "x": -4.0, "y": 1.7, "sx": 5, "sy": 5, "tint": "#ff9a3c",
         "keys": [key(0, a=0.38), key(4.13, "hold", a=0.38), key(4.25, "out", a=0.75), key(4.9, a=0.15), key(6.2, a=0.36)],
         "flicker": {"amp": 0.35, "f": 7}},
        {"id": "glowR", "sprite": "task_eject_glow.png", "z": -52, "x": 4.0, "y": 1.7, "sx": 5, "sy": 5, "tint": "#ff9a3c",
         "keys": [key(0, a=0.38), key(4.13, "hold", a=0.38), key(4.25, "out", a=0.75), key(4.9, a=0.15), key(6.2, a=0.36)],
         "flicker": {"amp": 0.35, "f": 6.1}},
        {"id": "flameL", "sprite": "task_eject_flame.png", "z": -50, "x": -4.0, "y": 1.55, "pivot": [0.5, 0.1], "s": 0.9,
         "wobble": [{"p": "sx", "amp": 0.08, "f": 6}, {"p": "sy", "amp": 0.12, "f": 9.3}, {"p": "rot", "amp": 4, "f": 3.1}]},
        {"id": "flameR", "sprite": "task_eject_flame.png", "z": -50, "x": 4.0, "y": 1.55, "pivot": [0.5, 0.1], "s": 0.9,
         "wobble": [{"p": "sx", "amp": 0.08, "f": 5.3, "ph": 1}, {"p": "sy", "amp": 0.12, "f": 8.1, "ph": 2}, {"p": "rot", "amp": 4, "f": 2.7}]},
        {"id": "band", "sprite": "task_eject_glow.png", "z": -40, "y": 0.19, "sx": 2.4, "sy": 0.45, "tint": "#ffd27a",
         "keys": [key(0, "hold", x=-7, a=0), key(4.55, "hold", x=-7, a=0), key(4.7, a=0.6), key(5.9, "lin", x=7),
                  key(5.6, a=0.6), key(5.95, a=0)]},
        {"id": "base", "sprite": "task_eject_sarc_base.png", "z": 10, "x": 0.6, "y": -1.55, "s": 0.85},
        {"id": "spirit", "sprite": "task_eject_glow.png", "z": 11, "x": 0.6, "y": -0.85, "sx": 4.6, "sy": 1.8, "tint": "#6dff9a",
         "keys": [key(0, "hold", a=0), key(2.35, "hold", a=0), key(2.95, "out", a=0.75), key(3.95, a=0.75), key(4.2, "in", a=0)],
         "flicker": {"amp": 0.25, "f": 5}},
        {"id": "lid", "sprite": "task_eject_sarc_lid.png", "z": 12, "x": 0.6, "y": -0.72, "s": 0.85,
         "keys": [key(0, x=0.6, y=-0.72, rot=0), key(2.4, "hold", x=0.6, y=-0.72, rot=0), key(2.95, "out", x=1.5, y=0.75, rot=16),
                  key(3.95, "lin", x=1.55, y=0.8, rot=17), key(4.12, "in", x=0.6, y=-0.72, rot=0), key(4.22, "out", y=-0.6, rot=-2),
                  key(4.32, "in", y=-0.72, rot=0)],
         "wobble": [{"p": "rot", "amp": 2.5, "f": 13, "t0": 1.6, "t1": 2.35}, {"p": "x", "amp": 0.03, "f": 11, "t0": 1.6, "t1": 2.35},
                    {"p": "rot", "amp": 1.2, "f": 1.3, "t0": 2.95, "t1": 3.95}]},
        {"id": "pillarL", "sprite": "task_eject_tomb_pillar.png", "z": 40, "x": -5.25, "y": -0.3, "depth": 1.35},
        {"id": "pillarR", "sprite": "task_eject_tomb_pillar.png", "z": 40, "x": 5.25, "y": -0.3, "sx": -1, "depth": 1.35},
    ],
    "player": {"hide": 3.92, "keys": [
        key(0, "lin", x=-7.4, y=1.2, rot=35, s=0.9, sx=1, sy=1), key(2.2, "out", x=-2.4, y=0.55, rot=-20),
        key(3.0, "io", x=-1.6, y=0.45, rot=-5, s=0.9, sx=1, sy=1), key(3.55, "in", x=-0.2, y=0.1, rot=45, sx=0.78, sy=1.22),
        key(3.9, "in", x=0.6, y=-0.55, rot=90, s=0.75, sx=1.1, sy=0.85)],
        "wobble": [{"p": "y", "amp": 0.12, "f": 0.8, "t0": 0, "t1": 2.4}, {"p": "rot", "amp": 8, "f": 0.55, "t0": 0, "t1": 2.4}]},
    "emitters": [
        em("task_eject_mote.png", -45, t0=0, t1=6.8, rate=7, area=[-4.8, 0.8, -3.2, 2.6], vel=[-0.08, 0.05, 0.08, 0.22],
           life=[2.5, 4.5], size=[0.05, 0.12], tint="#ffd9a0", a=0.8),
        em("task_eject_mote.png", -45, t0=0, t1=6.8, rate=7, area=[3.2, 0.8, 4.8, 2.6], vel=[-0.08, 0.05, 0.08, 0.22],
           life=[2.5, 4.5], size=[0.05, 0.12], tint="#ffd9a0", a=0.8),
        em("task_eject_mote.png", 13, t0=2.5, t1=3.95, rate=26, area=[-0.9, -1.0, 2.1, -0.7], vel=[-0.3, 0.4, 0.3, 1.1],
           drag=0.6, life=[0.6, 1.2], size=[0.08, 0.2], grow=0.5, tint="#8bffb0", a=0.9),
        em("task_eject_streak.png", 5, t0=3.0, t1=3.9, rate=40, area=[-6, -1.2, -2, 1.8], vel=[3.5, -0.8, 5.5, -0.2],
           life=[0.4, 0.7], size=[0.25, 0.45], tint="#b8ffd0", a=0.5, stretch=True),
        burst("task_eject_puff.png", 14, 4.13, 28, area=[-1.4, -0.9, 2.6, -0.6], vel=[-1.6, 0.1, 1.6, 0.9], drag=1.6,
              life=[1.2, 2.2], size=[0.5, 1.0], grow=0.5, tint="#b89870", a=0.6, spin=[-40, 40]),
        em("task_eject_mote.png", -20, t0=4.3, t1=6.3, rate=30, area=[-1.5, 3.4, 2.5, 3.5], vel=[-0.05, -1.5, 0.05, -0.8],
           acc=[0, -2], life=[1.2, 2.0], size=[0.04, 0.08], tint="#d8b888", a=0.8),
    ],
    "events": [ev(1.6, sound="grind", vol=0.35), ev(2.4, sound="grind", vol=0.7), ev(2.9, sound="whoosh", vol=0.4),
               ev(3.2, sound="whoosh", vol=0.7), ev(4.13, sound="thud", vol=0.95), ev(4.13, sound="slam", vol=0.5),
               ev(4.13, shake=[0.4, 0.1]), ev(5.0, sound="grind", vol=0.15)],
})

# ============================================================================ Museum: Falltuer ins Depot
# Aufsicht. Ein Suchscheinwerfer streift, der Spieler bleibt auf der Luke stehen. Klick, Warnlampen,
# Rumpeln, Staub aus der Fuge. Die Klappen fallen, der Spieler haengt einen Moment in der Luft
# (Cartoon-Blick nach unten), dann der Sturz ins Dunkel. Ein dumpfer Aufprall weit unten, Staub
# steigt auf, die Klappen schlagen wieder zu.
posts = [(-2.5, 1.7), (2.5, 1.7), (-2.5, -1.7), (2.5, -1.7)]
SCENES.append({
    "id": "trapdoor", "map": "museum", "title": "Falltür ins Depot", "length": 6.6, "text": [1.1, 2.6],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.05, x=-0.6, y=0.1), key(2.4, z=1.12, x=0, y=0.1), key(3.3, "out", z=1.25, x=0, y=0.05),
               key(4.6, z=1.3, x=0, y=0), key(6.6, z=1.12, x=0, y=0.1)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_depot_bg.jpg", "z": -100},
        {"id": "spot", "sprite": "task_eject_glow.png", "z": -60, "sx": 4.5, "sy": 4.5, "tint": "#fff3d6",
         "keys": [key(0, "lin", x=-3.6, y=1.6, a=0.22), key(2.3, x=2.6, y=-1.2), key(2.75, "out", x=0, y=0.1, a=0.22),
                  key(2.9, a=0.4), key(5.6, a=0.4), key(6.4, a=0.15)]},
    ] + [
        {"id": f"lamp{i}", "sprite": "task_eject_glow.png", "z": -55, "x": px, "y": py, "sx": 1.3, "sy": 1.3, "tint": "#ff3030",
         "keys": [key(0, "hold", a=0), key(2.7, "hold", a=0.75), key(5.4, "hold", a=0.75), key(5.55, a=0)],
         "flicker": {"amp": 0.95, "f": 3.2 + i * 0.05}} for i, (px, py) in enumerate(posts)
    ] + [
        {"id": "leafL", "sprite": "task_eject_trap_leaf.png", "z": -10, "x": -1.4, "y": 0, "pivot": [0, 0.5],
         "keys": [key(0, sx=1, b=1), key(3.25, "hold", sx=1, b=1), key(3.42, "in", sx=0.06, b=0.45), key(5.25, "hold", sx=0.06, b=0.45),
                  key(5.5, "out", sx=1.08, b=1), key(5.58, "in", sx=1)],
         "wobble": [{"p": "x", "amp": 0.03, "f": 15, "t0": 2.75, "t1": 3.2}]},
        {"id": "leafR", "sprite": "task_eject_trap_leaf.png", "z": -10, "x": 1.4, "y": 0, "pivot": [1, 0.5],
         "keys": [key(0, sx=1, b=1), key(3.25, "hold", sx=1, b=1), key(3.42, "in", sx=0.06, b=0.45), key(5.25, "hold", sx=0.06, b=0.45),
                  key(5.5, "out", sx=1.08, b=1), key(5.58, "in", sx=1)],
         "wobble": [{"p": "x", "amp": 0.03, "f": 14, "t0": 2.75, "t1": 3.2, "ph": 1}]},
        {"id": "shade", "sprite": "task_eject_glow.png", "z": 5, "x": 0, "y": 0.1, "sx": 2.2, "sy": 2.2, "tint": "#000000",
         "keys": [key(0, "hold", a=0), key(3.4, "hold", a=0), key(4.3, "in", a=0.85), key(4.6, a=0)]},
    ],
    "player": {"hide": 4.45, "keys": [
        key(0, "lin", x=-7.2, y=0.45, rot=0, s=1, sx=1, sy=1, flip=1), key(2.3, "lin", x=-0.4, y=0.3), key(2.55, "out", x=0, y=0.15),
        key(2.7, "hold", flip=-1), key(2.95, "hold", flip=1), key(3.25, sx=1, sy=1), key(3.42, "out", sx=0.9, sy=1.12),
        key(3.55, "out", x=0, y=0.15, rot=0, s=1, sx=1.05, sy=0.95), key(4.4, "in", x=0, y=-0.1, rot=720, s=0.1, sx=1, sy=1)],
        "wobble": [{"p": "y", "amp": 0.06, "f": 2.2, "t0": 0, "t1": 2.3}, {"p": "x", "amp": 0.025, "f": 14, "t0": 3.0, "t1": 3.25}]},
    "emitters": [
        em("task_eject_mote.png", -9, t0=2.75, t1=3.25, rate=50, area=[-0.05, -1.0, 0.05, 1.0], vel=[-0.1, -0.1, 0.1, 0.1],
           life=[0.4, 0.8], size=[0.05, 0.12], grow=-0.6, tint="#5a4a3a", a=0.8),
        burst("task_eject_puff.png", -8, 3.28, 16, area=[-1.3, -1.0, 1.3, 1.0], vel=[-0.8, -0.8, 0.8, 0.8], drag=2,
              life=[0.6, 1.2], size=[0.4, 0.8], grow=0.8, tint="#a08c70", a=0.45),
        burst("task_eject_puff.png", -8, 4.7, 12, area=[-0.5, -0.5, 0.5, 0.5], vel=[-0.3, -0.3, 0.3, 0.3],
              life=[1.2, 2.0], size=[0.3, 0.6], grow=1.2, tint="#6a5a48", a=0.5),
        burst("task_eject_puff.png", -8, 5.5, 18, area=[-1.5, -1.2, 1.5, 1.2], vel=[-1, -1, 1, 1], drag=2,
              life=[0.8, 1.4], size=[0.4, 0.8], tint="#b0a080", a=0.45),
    ],
    "events": [ev(2.65, sound="click", vol=0.7), ev(2.75, shake=[0.45, 0.03]), ev(2.8, sound="grind", vol=0.3),
               ev(3.25, sound="slam", vol=0.5), ev(3.5, sound="whoosh", vol=0.6), ev(4.7, sound="thud", vol=0.3),
               ev(5.5, sound="slam", vol=0.8), ev(5.5, shake=[0.25, 0.06])],
})

# ============================================================================ Museum: T-Rex
# Halle bei Nacht, Mondstrahlen mit Staub. Der Spieler kommt mit Taschenlampe. Der Boden bebt, Brocken
# fallen, der Schatten eines Schaedels zieht ueber die Fenster. Der Spieler dreht sich um, die Lampe
# flackert - der Schaedel schnellt herein und schnappt zu. Die Taschenlampe faellt, rollt und erlischt.
REX_Y, REX_S = -0.05, 0.8
beams = [-4.05, -1.35, 1.35, 4.05]
SCENES.append({
    "id": "trex", "map": "museum", "title": "T-Rex", "length": 7.0, "text": [1.2, 2.6],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.12, x=-1.0, y=-0.35), key(2.3, z=1.14, x=-0.5, y=-0.4), key(3.0, "out", z=1.04, x=0.3, y=-0.2),
               key(3.48, "out", z=1.2, x=0.1, y=-0.45), key(4.6, z=1.1, x=0, y=-0.3), key(7.0, z=1.08, x=0.1, y=-0.3)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_hall_bg.jpg", "z": -100},
    ] + [
        {"id": f"beam{i}", "sprite": "task_eject_beam.png", "z": -60, "x": bx, "y": 0.6, "pivot": [0.5, 1], "rot": 14,
         "tint": "#b8cfff", "keys": [key(0, a=0.5), key(2.4, a=0.5), key(2.7, a=0.15), key(3.05, a=0.5)],
         "flicker": {"amp": 0.08, "f": 0.4 + i * 0.1}} for i, bx in enumerate(beams)
    ] + [
        {"id": "shadow", "sprite": "task_eject_trex_head.png", "z": -55, "y": 1.4, "s": 1.7, "tint": "#000000",
         "keys": [key(0, "hold", x=7, a=0), key(2.35, "hold", x=7, a=0), key(2.5, a=0.5), key(3.0, "lin", x=-7), key(2.85, a=0.5), key(3.0, a=0)]},
        {"id": "rex", "keys": [key(0, "hold", x=10.5, y=REX_Y, s=REX_S), key(2.95, "hold", x=10.5), key(3.3, "out", x=1.75),
                               key(3.95, "hold", x=1.75), key(4.8, "in", x=11)],
         "wobble": [{"p": "y", "amp": 0.03, "f": 12, "t0": 3.3, "t1": 3.95}]},
    ] + [
        {"id": f"vert{i}", "sprite": "task_eject_trex_vert.png", "parent": "rex", "z": 6, "x": vx, "y": vy, "s": 1.2 + i * 0.12}
        for i, (vx, vy) in enumerate([(3.0, 0.12), (3.75, -0.08), (4.55, -0.34), (5.4, -0.66), (6.3, -1.02)])
    ] + [
        {"id": "jaw", "sprite": "task_eject_trex_jaw.png", "parent": "rex", "z": 7, "x": 2.48, "y": -0.64,
         "pivot": [506 / 540, 1 - 44 / 150],
         "keys": [key(0, rot=-3.5), key(2.95, "hold", rot=-3.5), key(3.25, "out", rot=16), key(3.38, "hold", rot=16), key(3.48, "in", rot=-3.5)]},
        {"id": "head", "sprite": "task_eject_trex_head.png", "parent": "rex", "z": 8},
        {"id": "eye", "sprite": "task_eject_glow.png", "parent": "rex", "z": 9, "x": 0.93, "y": 0.53, "s": 0.7, "tint": "#ff3a2a",
         "keys": [key(0, "hold", a=0), key(2.9, "hold", a=0), key(3.1, a=0.9), key(3.9, a=0.9), key(4.5, a=0.4)],
         "flicker": {"amp": 0.3, "f": 6}},
        {"id": "torch", "sprite": "task_eject_flashlight.png", "parent": "player", "z": 2, "x": 0.3, "y": -0.12, "s": 0.75,
         "keys": [key(0, "hold", a=1), key(3.48, "hold", a=0)]},
        {"id": "cone", "sprite": "task_eject_cone.png", "parent": "player", "z": 1, "x": 0.56, "y": -0.1, "pivot": [0, 0.5], "s": 0.9,
         "tint": "#fff4d0", "keys": [key(0, "hold", a=0.45), key(3.48, "hold", a=0)],
         "flicker": {"amp": 0.7, "f": 9, "t0": 2.4, "t1": 3.45}},
        {"id": "dropTorch", "sprite": "task_eject_flashlight.png", "z": 3, "s": 0.75,
         "keys": [key(0, "hold", a=0, x=-0.2, y=-0.75, rot=40), key(3.48, "hold", a=1, x=-0.2, y=-0.75, rot=40), key(3.9, "in", x=-0.35, y=-1.12, rot=250),
                  key(4.1, "out", x=-0.25, y=-1.05, rot=300), key(4.3, "in", x=-0.15, y=-1.12, rot=330), key(5.2, "out", x=0.55, rot=540)]},
        {"id": "dropCone", "sprite": "task_eject_cone.png", "parent": "dropTorch", "z": 2, "x": 0.35, "y": 0, "pivot": [0, 0.5],
         "s": 1.2, "tint": "#fff4d0", "keys": [key(0, "hold", a=0), key(3.48, "hold", a=0.45), key(5.8, "hold", a=0.45), key(5.9, "hold", a=0)],
         "flicker": {"amp": 0.9, "f": 10, "t0": 4.6, "t1": 5.8}},
        {"id": "pshadow", "sprite": "task_eject_glow.png", "parent": "player", "z": -1, "x": 0, "y": -0.5, "sx": 1.1, "sy": 0.22, "tint": "#000000", "a": 0.55},
        {"id": "fg", "sprite": "task_eject_hall_fg.png", "z": 40, "y": -3.05, "depth": 1.3},
    ],
    "player": {"hide": 3.48, "keys": [
        key(0, "lin", x=-7, y=-0.7, s=1, sx=1, sy=1, flip=1), key(2.2, "out", x=-0.5), key(2.55, "hold", flip=-1),
        key(3.1, "hold", flip=1), key(3.1, sx=1, sy=1), key(3.2, "out", sx=1.12, sy=0.88), key(3.35, sx=0.95, sy=1.06)],
        "wobble": [{"p": "y", "amp": 0.05, "f": 2.2, "t0": 0, "t1": 2.2}, {"p": "x", "amp": 0.03, "f": 14, "t0": 2.5, "t1": 3.45}]},
    "emitters": [
        em("task_eject_mote.png", -58, t0=0, t1=7, rate=10, area=[-5, -1.2, 5, 0.8], vel=[-0.05, -0.08, 0.08, 0.05],
           life=[3, 5], size=[0.04, 0.09], tint="#cfe0ff", a=0.6),
        em("task_eject_rock.png", -30, t0=2.45, t1=3.4, rate=14, area=[-5, 3.5, 5, 3.6], vel=[-0.3, -1, 0.3, -0.4], acc=[0, -9],
           life=[0.8, 1.2], size=[0.08, 0.18], spin=[-300, 300], tint="#8a8278", a=1),
        em("task_eject_puff.png", -30, t0=2.45, t1=3.4, rate=6, area=[-5, 3.2, 5, 3.4], vel=[-0.1, -0.5, 0.1, -0.2],
           life=[1.0, 1.6], size=[0.3, 0.6], grow=0.5, tint="#7a7680", a=0.3),
        burst("task_eject_puff.png", 10, 3.48, 16, area=[-1, -1.2, 0.6, -0.4], vel=[-1.5, -0.2, 1, 1], drag=2,
              life=[0.8, 1.4], size=[0.3, 0.7], grow=0.6, tint="#d8d0bc", a=0.5),
    ],
    "events": [ev(2.4, sound="growl", vol=0.6), ev(2.4, shake=[0.9, 0.025]), ev(2.95, sound="roar", vol=0.9),
               ev(3.0, shake=[0.5, 0.07]), ev(3.48, sound="slam", vol=0.9), ev(3.48, shake=[0.35, 0.12]),
               ev(4.1, sound="click", vol=0.4), ev(4.3, sound="click", vol=0.25), ev(5.9, sound="click", vol=0.3)],
})

# ============================================================================ Museum: Hinausgeworfen
# Regennacht vor dem Museum. Zwei Waechter tragen den Spieler heraus, holen aus und werfen ihn im
# hohen Bogen in die Pfuetze (Stauchen beim Aufprall, Tropfen, Ringe). Sie klopfen sich die Haende ab,
# gehen hinein, die Tuer knallt, das warme Licht ist weg. Ein Blitz, Donner, ein letztes Zucken.
SCENES.append({
    "id": "thrown", "map": "museum", "title": "Hinausgeworfen", "length": 7.4, "text": [1.6, 2.6],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.14, x=-1.2, y=-0.3), key(1.3, z=1.14, x=-1.1, y=-0.35), key(2.4, z=1.1, x=0.1, y=-0.5),
               key(2.6, "out", z=1.16, x=0.3, y=-0.6), key(4.3, z=1.08, x=-0.5, y=-0.4), key(7.4, z=1.1, x=0, y=-0.45)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_night_bg.jpg", "z": -100},
        {"id": "spill", "sprite": "task_eject_glow.png", "z": -40, "x": -3.35, "y": -1.5, "sx": 5, "sy": 1.6, "tint": "#ffc070",
         "keys": [key(0, a=0.55), key(3.95, "hold", a=0.55), key(4.25, "in", a=0)]},
        {"id": "lampGlow", "sprite": "task_eject_glow.png", "z": -50, "x": 4.1, "y": 1.75, "s": 3, "tint": "#ffd9a0", "a": 0.45,
         "flicker": {"amp": 0.2, "f": 5}},
        {"id": "lampPool", "sprite": "task_eject_glow.png", "z": -50, "x": 4.1, "y": -2.3, "sx": 4, "sy": 0.8, "tint": "#ffd9a0", "a": 0.25},
        {"id": "door", "sprite": "task_eject_door.png", "z": -35, "x": -3.9, "y": -1.12, "pivot": [0, 0], "s": 0.95,
         "keys": [key(0, "hold", sx=0.05), key(3.95, "hold", sx=0.05), key(4.2, "in", sx=1.0), key(4.3, "out", sx=0.95)]},
        {"id": "guard1", "sprite": "task_eject_guard.png", "z": -2, "y": -0.5, "s": 0.62,
         "keys": [key(0, "hold", x=-3.9, a=1), key(0.2, "hold", x=-3.9), key(0.9, x=-3.4), key(1.2, "out", x=-3.55),
                  key(1.45, "out", x=-3.3), key(2.9, x=-3.35), key(3.6, x=-3.9), key(3.5, "hold", a=1), key(3.75, a=0)],
         "wobble": [{"p": "y", "amp": 0.03, "f": 4, "t0": 0.2, "t1": 0.9}, {"p": "rot", "amp": 4, "f": 7, "t0": 2.6, "t1": 3.1}]},
        {"id": "guard2", "sprite": "task_eject_guard.png", "z": 2, "y": -0.5, "s": 0.62, "sx": -1,
         "keys": [key(0, "hold", x=-2.8, a=1), key(0.2, "hold", x=-2.8), key(0.9, x=-2.3), key(1.2, "out", x=-2.45),
                  key(1.45, "out", x=-2.2), key(2.9, x=-2.25), key(3.6, x=-2.9), key(3.45, "hold", a=1), key(3.7, a=0)],
         "wobble": [{"p": "y", "amp": 0.03, "f": 4, "t0": 0.2, "t1": 0.9, "ph": 1.5}, {"p": "rot", "amp": 4, "f": 7, "t0": 2.7, "t1": 3.2}]},
    ],
    "player": {"keys": [
        key(0, "lin", x=-3.35, y=-0.35, rot=0, s=0.8, sx=1, sy=1, flip=1), key(0.9, x=-2.85, y=-0.3, rot=0),
        key(1.2, "out", x=-3.1, y=-0.1, rot=25, sx=0.95, sy=1.05), key(1.45, "in", x=-2.5, y=0.2, rot=-40, sx=0.85, sy=1.15),
        key(2.45, "lin", x=0.95, y=-1.95, rot=-630, sx=0.9, sy=1.1, arc=2.0),
        key(2.55, "out", x=1.05, y=-2.2, sx=1.35, sy=0.7), key(2.8, "out", x=1.25, y=-2.25, sx=1, sy=1),
        key(6.0, "hold", rot=-630), key(6.1, "out", rot=-615), key(6.25, "in", rot=-630)]},
    "emitters": [
        em("task_eject_streak.png", 30, t0=0, t1=7.4, rate=110, area=[-7, 3.8, 8, 4.2], vel=[-1.6, -11.5, -1.2, -10],
           life=[0.6, 0.75], size=[0.25, 0.4], tint="#b8cff0", a=0.45, stretch=True, fade=[0.05, 0.1]),
        em("task_eject_ripple.png", -20, t0=0, t1=7.4, rate=3, area=[-1.7, -2.55, 0.1, -2.45],
           life=[0.8, 1.2], size=[0.15, 0.3], grow=1.8, tint="#9fb8e0", a=0.5),
        em("task_eject_ripple.png", -20, t0=0, t1=7.4, rate=4, area=[-0.3, -2.55, 4.6, -2.45],
           life=[0.8, 1.2], size=[0.15, 0.3], grow=1.8, tint="#9fb8e0", a=0.5),
        burst("task_eject_droplet.png", 20, 2.5, 26, area=[0.7, -2.5, 1.3, -2.3], vel=[-2.4, 1.5, 2.4, 4.2], acc=[0, -12],
              life=[0.5, 0.9], size=[0.06, 0.14], tint="#cfe0ff", a=0.9, stretch=True),
        burst("task_eject_ripple.png", -19, 2.5, 3, area=[0.9, -2.5, 1.1, -2.45], life=[0.8, 1.4], size=[0.4, 0.6], grow=2.2,
              tint="#cfe0ff", a=0.7),
        burst("task_eject_puff.png", 19, 2.5, 6, area=[0.6, -2.45, 1.4, -2.3], vel=[-0.6, 0.2, 0.6, 0.8], drag=2,
              life=[0.6, 1.0], size=[0.3, 0.6], grow=0.8, tint="#c0d0ea", a=0.35),
    ],
    "events": [ev(0.2, sound="rush", vol=0.35), ev(1.45, sound="whoosh", vol=0.8), ev(2.5, sound="splash", vol=0.9),
               ev(2.5, shake=[0.2, 0.05]), ev(4.2, sound="slam", vol=0.8), ev(4.2, shake=[0.2, 0.04]),
               ev(5.2, flash=["#dfe8ff", 0.55, 0.45]), ev(5.45, flash=["#dfe8ff", 0.3, 0.25]), ev(5.7, sound="thunder", vol=0.7)],
})

# ============================================================================ Wald: Wildwasser
# Nacht am Fluss, Mondspiegelung, Gluehwuermchen. Der Spieler paddelt, die Stroemung wird schneller,
# das Paddel fliegt davon. Das Kanu kippt an der Kante, haengt einen Moment - der Spieler hebt vom
# Sitz ab - und stuerzt in die Tiefe. Gischtexplosion, Nebel, das Paddel treibt hinterher.
SCENES.append({
    "id": "rapids", "map": "wald", "title": "Wildwasser", "length": 7.2, "text": [1.4, 2.6],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.1, x=-0.8, y=-0.2), key(3.0, z=1.12, x=0.6, y=-0.3), key(4.1, z=1.2, x=1.2, y=-0.5),
               key(4.6, "out", z=1.14, x=1.15, y=-0.6), key(5.2, z=1.1, x=1.0, y=-0.55), key(7.2, z=1.08, x=0.7, y=-0.4)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_river_bg.jpg", "z": -100},
        {"id": "moonRef", "sprite": "task_eject_glow.png", "z": -60, "x": 3.0, "y": -0.35, "sx": 2.6, "sy": 0.22, "tint": "#dfe6ff", "a": 0.45,
         "wobble": [{"p": "sx", "amp": 0.25, "f": 0.6}], "flicker": {"amp": 0.3, "f": 1.1}},
        {"id": "boat", "keys": [key(0, "lin", x=-7, y=-0.55, rot=0), key(2.2, "lin", x=-2.6), key(3.7, "in", x=2.3, y=-0.55, rot=0),
                                key(4.05, "out", x=3.25, rot=-12), key(4.35, x=3.35, y=-0.55, rot=-24), key(5.05, "in", x=4.3, y=-4.6, rot=-75)],
         "wobble": [{"p": "y", "amp": 0.05, "f": 1.5, "t0": 0, "t1": 3.8}, {"p": "rot", "amp": 3, "f": 1.15, "t0": 0, "t1": 3.8}]},
        {"id": "paddle", "sprite": "task_eject_paddle.png", "parent": "boat", "z": 5, "x": 0.45, "y": 0.35, "pivot": [0.25, 0.5],
         "s": 0.6, "rot": -120, "keys": [key(0, "hold", a=1), key(3.2, "hold", a=0)],
         "wobble": [{"p": "rot", "amp": 25, "f": 0.6, "t0": 0, "t1": 3.2}]},
        {"id": "canoe", "sprite": "task_eject_canoe.png", "parent": "boat", "z": 6, "s": 0.72},
        {"id": "flyPaddle", "sprite": "task_eject_paddle.png", "z": 5, "s": 0.6,
         "keys": [key(0, "hold", a=0, x=0.03, y=-0.2, rot=-120), key(3.2, "hold", a=1, x=0.03, y=-0.2, rot=-120), key(3.6, "out", x=1.6, y=1.2, rot=200),
                  key(4.1, "in", x=2.6, y=-0.5, rot=520), key(6.4, "lin", x=3.6, y=-0.8, rot=545), key(6.5, "hold", a=0)]},
        {"id": "mist1", "sprite": "task_eject_mist.png", "z": 20, "x": 4.6, "y": -1.3, "s": 1.2, "a": 0.5,
         "wobble": [{"p": "x", "amp": 0.2, "f": 0.15}]},
        {"id": "mist2", "sprite": "task_eject_mist.png", "z": 20, "x": 5.2, "y": -0.9, "s": 1.0, "a": 0.35,
         "wobble": [{"p": "x", "amp": 0.25, "f": 0.12, "ph": 2}]},
        {"id": "reeds", "sprite": "task_eject_reeds.png", "z": 40, "y": -3.0, "depth": 1.3},
    ],
    "player": {"parent": "boat", "hide": 5.05, "keys": [
        key(0, "lin", x=0.1, y=0.42, rot=0, s=0.62, sx=1, sy=1, flip=1), key(3.3, sx=1, sy=1),
        key(3.45, "out", sx=1.12, sy=0.9), key(3.6, sx=1, sy=1), key(4.05, y=0.45, rot=0),
        key(4.35, "out", y=0.95, rot=25, sx=0.9, sy=1.12), key(4.7, "in", y=0.6, rot=40)],
        "wobble": [{"p": "rot", "amp": 5, "f": 0.6, "t0": 0, "t1": 3.2}]},
    "emitters": [
        em("task_eject_streak.png", -30, t0=0, t1=7.2, rate=30, area=[-6.5, -1.45, 3.4, 0.25], vel=[1.6, 0, 2.4, 0],
           life=[0.8, 1.4], size=[0.2, 0.4], tint="#9cc6e6", a=0.45, stretch=True),
        em("task_eject_streak.png", -30, t0=2.5, t1=7.2, rate=25, area=[0, -1.45, 3.5, 0.2], vel=[3.5, 0, 5, 0],
           life=[0.4, 0.8], size=[0.25, 0.45], tint="#cfe6f6", a=0.5, stretch=True),
        em("task_eject_firefly.png", -20, t0=0, t1=7.2, rate=3, area=[-6, 0.4, 3, 1.3], vel=[-0.2, -0.1, 0.2, 0.15],
           life=[2, 4], size=[0.15, 0.25], a=1),
        em("task_eject_puff.png", 21, t0=0, t1=7.2, rate=8, area=[3.6, -1.6, 4.4, -1.0], vel=[0.1, 0.3, 0.6, 0.9], drag=0.5,
           life=[1.5, 2.5], size=[0.6, 1.2], grow=0.3, tint="#dfe8f0", a=0.35),
        burst("task_eject_droplet.png", 7, 4.1, 12, area=[2.5, -0.55, 2.7, -0.45], vel=[-1, 1, 1, 3], acc=[0, -9],
              life=[0.4, 0.7], size=[0.05, 0.1], tint="#cfe6f6", a=0.9, stretch=True),
        burst("task_eject_puff.png", 22, 5.0, 30, area=[3.8, -1.6, 4.8, -1.2], vel=[-1.2, 0.8, 1.2, 3.5], drag=1.2,
              life=[1.2, 2.2], size=[0.6, 1.4], grow=0.6, tint="#e8f0f6", a=0.6),
        burst("task_eject_droplet.png", 23, 5.0, 30, area=[3.8, -1.5, 4.8, -1.2], vel=[-2, 2, 2, 6], acc=[0, -9],
              life=[0.5, 0.9], size=[0.05, 0.12], tint="#e8f0f6", a=0.9, stretch=True),
    ],
    "events": [ev(0, sound="rush", vol=0.45), ev(2.6, sound="rush", vol=0.5), ev(3.2, sound="whoosh", vol=0.5),
               ev(4.1, sound="splash", vol=0.5), ev(4.35, sound="creak", vol=0.5), ev(4.45, sound="whoosh", vol=0.7),
               ev(5.0, sound="splash", vol=1.0), ev(5.0, shake=[0.5, 0.1])],
})

# ============================================================================ Wald: In den Wald gezerrt
# Dunkler Wald, Nebelschwaden, Gluehwuermchen. Der Spieler mit Laterne auf dem Pfad. Ein Zweig knackt,
# die Gluehwuermchen fliehen, Augen oeffnen sich eins nach dem anderen, die Laterne flackert, Knurren.
# Ruck: der Spieler wird ins Gebuesch gerissen, Blaetter explodieren, die Laterne faellt und erlischt.
eyes = [((2.4, 0.1), 2.6, 5.3), ((3.9, 0.55), 2.85, 5.15), ((4.7, -0.3), 3.05, 5.0), ((1.6, 0.8), 3.25, 4.85), ((3.2, 1.2), 3.45, 4.7)]
SCENES.append({
    "id": "dragged", "map": "wald", "title": "In den Wald gezerrt", "length": 7.2, "text": [1.2, 2.6],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.12, x=-1.05, y=-0.5), key(2.3, z=1.14, x=-0.8, y=-0.5), key(3.9, z=1.24, x=-0.6, y=-0.55),
               key(4.2, "out", z=1.14, x=0.9, y=-0.5), key(7.2, z=1.1, x=0.6, y=-0.4)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_forest_bg.jpg", "z": -100},
    ] + [
        {"id": f"mist{i}", "sprite": "task_eject_mist.png", "z": -40, "x": mx, "y": my, "s": 1.4, "a": 0.22, "depth": 0.9,
         "wobble": [{"p": "x", "amp": 0.4, "f": 0.08 + i * 0.02, "ph": i}]} for i, (mx, my) in enumerate([(-3, -1.2), (1.5, -0.8), (4, -1.5)])
    ] + [
        {"id": f"eye{i}", "sprite": "task_eject_eyes.png", "z": -30, "x": p[0], "y": p[1], "s": 0.9,
         "keys": [key(0, "hold", a=0), key(t_in, "hold", a=0), key(t_in + 0.25, a=1), key(t_in + 0.9 + i * 0.1, "hold", a=1),
                  key(t_in + 0.95 + i * 0.1, "hold", a=0), key(t_in + 1.02 + i * 0.1, "hold", a=1), key(t_out, "hold", a=1),
                  key(t_out + 0.12, a=0)]} for i, (p, t_in, t_out) in enumerate(eyes)
    ] + [
        {"id": "bush", "sprite": "task_eject_bushes.png", "z": 20, "x": 3.6, "y": -2.25, "pivot": [0.5, 0.2], "s": 0.95,
         "keys": [key(0, rot=0, sx=1), key(3.95, "hold", rot=0), key(4.02, "out", rot=5, sx=1.05), key(4.12, rot=-4, sx=1),
                  key(4.22, rot=3), key(4.32, rot=-2), key(4.47, rot=1), key(4.62, rot=0)]},
        {"id": "lantern", "sprite": "task_eject_lantern.png", "parent": "player", "z": 3, "x": 0.42, "y": -0.15, "s": 0.6,
         "keys": [key(0, "hold", a=1), key(3.95, "hold", a=0)], "wobble": [{"p": "rot", "amp": 6, "f": 1.6, "t0": 0, "t1": 2.3}]},
        {"id": "lanternGlow", "sprite": "task_eject_glow.png", "parent": "player", "z": -5, "x": 0.42, "y": -0.05, "s": 3.2,
         "tint": "#ffcf7a", "keys": [key(0, "hold", a=0.5), key(3.95, "hold", a=0)],
         "flicker": {"amp": 0.18, "f": 9}},
        {"id": "lanternFlick", "sprite": "task_eject_glow.png", "parent": "player", "z": -5, "x": 0.42, "y": -0.05, "s": 3.2,
         "tint": "#000000", "keys": [key(0, "hold", a=0), key(2.6, "hold", a=0.4), key(3.95, "hold", a=0)],
         "flicker": {"amp": 1, "f": 8, "t0": 2.6, "t1": 3.95}},
        {"id": "dropLantern", "sprite": "task_eject_lantern.png", "z": 3, "s": 0.6,
         "keys": [key(0, "hold", a=0, x=-0.8, y=-1.55, rot=0), key(3.95, "hold", a=1, x=-0.88, y=-1.6, rot=0), key(4.3, "in", x=-0.6, y=-1.95, rot=70),
                  key(4.45, "out", x=-0.45, y=-1.85, rot=85), key(4.6, "in", x=-0.35, y=-1.95, rot=90)]},
        {"id": "dropGlow", "sprite": "task_eject_glow.png", "parent": "dropLantern", "z": -4, "y": 0.1, "s": 3.0, "tint": "#ffcf7a",
         "keys": [key(0, "hold", a=0), key(3.95, "hold", a=0.5), key(5.4, "hold", a=0.5), key(5.5, a=0)],
         "flicker": {"amp": 0.9, "f": 10, "t0": 4.4, "t1": 5.4}},
        {"id": "pshadow", "sprite": "task_eject_glow.png", "parent": "player", "z": -1, "x": 0, "y": -0.5, "sx": 1.1, "sy": 0.22, "tint": "#000000", "a": 0.55},
        {"id": "ferns", "sprite": "task_eject_ferns.png", "z": 40, "y": -3.15, "depth": 1.3},
    ],
    "player": {"hide": 4.22, "keys": [
        key(0, "lin", x=-7.3, y=-1.45, s=1, sx=1, sy=1, flip=1, rot=0), key(2.3, "out", x=-1.3), key(2.4, "hold", flip=-1),
        key(2.9, "hold", flip=1), key(3.55, sx=1, sy=1), key(3.65, "out", sx=1.12, sy=0.88), key(3.8, sx=0.97, sy=1.03),
        key(3.95, "hold", x=-1.3, y=-1.45, rot=0, sx=1, sy=1), key(4.22, "in", x=4.3, y=-1.3, rot=-40, sx=1.35, sy=0.8)],
        "wobble": [{"p": "y", "amp": 0.05, "f": 2.2, "t0": 0, "t1": 2.3}, {"p": "x", "amp": 0.03, "f": 14, "t0": 2.9, "t1": 3.9}]},
    "emitters": [
        em("task_eject_firefly.png", -25, t0=0, t1=2.4, rate=4, area=[-6, -1.5, 5, 1.2], vel=[-0.25, -0.15, 0.25, 0.2],
           life=[2, 4], size=[0.12, 0.22], a=1),
        burst("task_eject_firefly.png", -25, 2.4, 14, area=[-3, -1.4, 3, 0.8], vel=[-1.5, 0.6, 1.5, 2.2], drag=0.3,
              life=[1.2, 2.0], size=[0.12, 0.2], a=1),
        burst("task_eject_leaf.png", 25, 4.18, 34, area=[2.6, -1.8, 3.4, -0.4], vel=[0.5, 0.5, 3.5, 3.5], acc=[0, -3], drag=0.8,
              life=[1.2, 2.2], size=[0.12, 0.22], spin=[-400, 400], rot=[0, 360], tint="#3c6e46", a=1),
        em("task_eject_leaf.png", 25, t0=4.3, t1=5.5, rate=6, area=[2.4, 0, 4.6, 0.6], vel=[-0.3, -0.6, 0.3, -0.3], acc=[0, -0.6],
           spin=[-120, 120], rot=[0, 360], life=[2, 3], size=[0.1, 0.18], tint="#2e5a3a", a=1),
    ],
    "events": [ev(0.8, sound="owl", vol=0.25), ev(2.35, sound="twig", vol=0.8), ev(2.9, sound="growl", vol=0.45),
               ev(3.5, sound="growl", vol=0.8), ev(3.95, sound="whoosh", vol=0.9), ev(4.0, shake=[0.3, 0.06]),
               ev(4.1, sound="twig", vol=0.6), ev(4.3, sound="click", vol=0.35), ev(5.45, sound="click", vol=0.2),
               ev(6.3, sound="owl", vol=0.35)],
})

# ============================================================================ Wald: Vom Hochsitz
# Das Bild ist hoeher als der Bildschirm (12 x 10): oben der Hochsitz auf der Felsnase, unten das
# Nebeltal. Der Spieler schaut sich um, der Stand knarzt und schwankt, das Gelaenderbrett bricht, der
# Spieler faellt - und die Kamera faehrt mit ins Tal. Der Nebel schluckt ihn, spaeter fliegt eine Eule.
SX, SB, SS = -4.0, 0.6, 0.62                        # Hochsitz: x, Fussboden (Felskante), Groesse
DECK = SB + (470 - 152) / 100 * SS                  # Plattform-Oberkante
PLANK = (SX + (204 - 150) / 100 * SS, SB + (470 - 102) / 100 * SS)
SCENES.append({
    "id": "stand", "map": "wald", "title": "Vom Hochsitz", "length": 7.8, "text": [1.2, 2.6],
    "bounds": [12, 10],
    "camera": [key(0, "lin", z=1.3, x=-1.7, y=2.3), key(2.1, z=1.3, x=-1.6, y=2.25), key(2.4, "lin", z=1.26, x=-1.5, y=2.2),
               key(4.7, z=1.05, x=0.4, y=-1.8), key(5.0, "out", z=1.08, x=0.45, y=-1.85), key(7.8, z=1.05, x=0.5, y=-1.6)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_valley_bg.jpg", "z": -100},
        {"id": "fogBack", "sprite": "task_eject_fog0.png", "z": -20, "y": -2.4, "a": 0.8, "depth": 0.85,
         "wobble": [{"p": "x", "amp": 0.35, "f": 0.08}]},
        {"id": "stand", "sprite": "task_eject_stand.png", "z": -4, "x": SX, "y": SB, "pivot": [0.5, 0], "s": SS,
         "wobble": [{"p": "rot", "amp": 1.6, "f": 1.6, "t0": 1.4, "t1": 2.4}]},
        {"id": "plank", "sprite": "task_eject_plank.png", "z": -3, "s": SS,
         "keys": [key(0, "hold", x=PLANK[0], y=PLANK[1], rot=0, a=1), key(2.05, "hold", x=PLANK[0], y=PLANK[1], rot=0),
                  key(2.3, "out", x=PLANK[0] + 0.45, y=PLANK[1] + 0.12, rot=-40),
                  key(4.5, "in", x=0.2, y=-2.6, rot=-700), key(4.55, "hold", a=0)]},
        {"id": "owl", "sprite": "task_eject_owl.png", "z": -10, "s": 0.45,
         "keys": [key(0, "hold", x=7, y=0.8, a=0), key(5.6, "hold", x=7, y=0.8, a=1), key(7.8, "lin", x=-7, y=0.5)],
         "wobble": [{"p": "sy", "amp": 0.35, "f": 3}, {"p": "y", "amp": 0.1, "f": 0.5}]},
        {"id": "fogFront", "sprite": "task_eject_fog1.png", "z": 30, "y": -3.1, "depth": 1.15,
         "wobble": [{"p": "x", "amp": 0.5, "f": 0.1}]},
    ],
    "player": {"hide": 4.62, "keys": [
        key(0, "lin", x=SX - 0.35, y=DECK + 0.31, rot=0, s=0.62, sx=1, sy=1, flip=1), key(0.9, "hold", flip=-1),
        key(1.4, "hold", flip=1), key(1.9, x=SX - 0.3, y=DECK + 0.31, rot=0, sx=1, sy=1),
        key(2.1, "out", x=SX, y=DECK + 0.33, rot=-12, sx=0.95, sy=1.05), key(2.28, "out", x=SX + 0.45, y=DECK + 0.43, rot=-35, s=0.62),
        key(4.6, "in", x=0.6, y=-2.6, rot=-620, s=0.45, sx=0.9, sy=1.1, arc=0.6)]},
    "emitters": [
        em("task_eject_mote.png", -90, t0=0, t1=7.8, rate=3, area=[-6, 1, 6, 5], life=[1, 2], size=[0.05, 0.1],
           tint="#e8eeff", a=0.8, fade=[0.4, 0.5]),
        burst("task_eject_splinter.png", -2, 2.05, 12, area=[PLANK[0] - 0.3, PLANK[1] - 0.05, PLANK[0] + 0.2, PLANK[1] + 0.05],
              vel=[-1, 0.5, 2, 2.5], acc=[0, -8], spin=[-500, 500], rot=[0, 360], life=[0.8, 1.4], size=[0.12, 0.22], a=1),
        burst("task_eject_puff.png", 31, 4.62, 12, area=[0.2, -2.8, 1.0, -2.4], vel=[-0.8, 0.2, 0.8, 0.9], drag=1.2,
              life=[1.4, 2.2], size=[0.6, 1.2], grow=0.5, tint="#dfe6f0", a=0.6),
    ],
    "events": [ev(1.35, sound="creak", vol=0.5), ev(1.9, sound="creak", vol=0.7), ev(2.05, sound="slam", vol=0.4),
               ev(2.05, shake=[0.2, 0.03]), ev(2.2, sound="whoosh", vol=0.8), ev(3.3, sound="whoosh", vol=0.4),
               ev(4.62, sound="thud", vol=0.25), ev(6.0, sound="owl", vol=0.3)],
})


# ============================================================================ SKIP: Museum - Leere Vitrine
# Niemand fliegt. Ein Scheinwerfer auf einer leeren Vitrine mit eingedruecktem Samtkissen, Schild
# "EXHIBIT: VACANT". Eine Motte umkreist das Licht, eine Waechter-Taschenlampe streift die Wand, die
# Kamera faehrt langsam heran. Am Ende flackert der Scheinwerfer und klickt aus.
SCENES.append({
    "id": "skip_case", "map": "museum", "skip": True, "title": "Leere Vitrine", "length": 6.4, "text": [1.0, 2.8],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.02, x=0, y=0), key(5.0, z=1.16, x=0, y=-0.2), key(6.4, z=1.17, x=0, y=-0.2)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_gallery_bg.jpg", "z": -100},
        {"id": "sweep", "sprite": "task_eject_cone.png", "z": -60, "x": 6.2, "y": -0.2, "pivot": [0, 0.5], "s": 2.2, "tint": "#fff6dc",
         "keys": [key(0, "hold", rot=165, a=0), key(1.0, "hold", rot=165, a=0), key(1.2, a=0.3), key(2.2, rot=192),
                  key(2.5, a=0.3), key(2.8, rot=176), key(2.9, a=0)]},
        {"id": "beam", "sprite": "task_eject_beam.png", "z": -40, "x": 0, "y": 3.45, "pivot": [0.5, 1], "sx": 1.1, "tint": "#fff1d0",
         "keys": [key(0, a=0.42), key(5.2, "hold", a=0.42), key(5.25, "in", a=0.04)],
         "flicker": {"amp": 0.8, "f": 7, "t0": 4.85, "t1": 5.2}},
        {"id": "pool", "sprite": "task_eject_glow.png", "z": -38, "x": 0, "y": -1.95, "sx": 3.2, "sy": 0.6, "tint": "#ffe2b0",
         "keys": [key(0, a=0.38), key(5.2, "hold", a=0.38), key(5.25, "in", a=0)],
         "flicker": {"amp": 0.8, "f": 7, "t0": 4.85, "t1": 5.2}},
        {"id": "case", "sprite": "task_eject_case.png", "z": -20, "x": 0, "y": -1.9, "pivot": [0.5, 0], "s": 0.85},
        {"id": "glint", "sprite": "task_eject_glow.png", "z": -19, "s": 0.35, "tint": "#ffffff",
         "keys": [key(0, "hold", x=-0.5, y=0.6, a=0), key(2.4, "hold", x=-0.5, y=0.6, a=0), key(2.7, a=0.8), key(3.0, "lin", x=0.5, y=-0.2),
                  key(3.05, a=0)]},
        {"id": "placard", "sprite": "task_eject_placard.png", "z": -18, "x": 1.25, "y": -2.2, "pivot": [0.5, 0], "s": 0.75},
        {"id": "moth", "sprite": "task_eject_moth.png", "z": -10, "s": 1.0,
         "keys": [key(0, x=0.3, y=1.6), key(5.4, "hold", x=0.3, y=1.6), key(6.4, "in", x=5.5, y=2.8)],
         "wobble": [{"p": "x", "amp": 0.55, "f": 0.7, "t0": 0, "t1": 5.6}, {"p": "y", "amp": 0.35, "f": 1.1, "ph": 1, "t0": 0, "t1": 5.6},
                    {"p": "sy", "amp": 0.4, "f": 9}, {"p": "rot", "amp": 20, "f": 0.7}]},
        {"id": "dark", "sprite": "task_eject_px.png", "z": 30, "s": 100, "tint": "#000000",
         "keys": [key(0, "hold", a=0), key(5.2, "hold", a=0), key(5.3, "in", a=0.45)]},
    ],
    "player": {"keys": [key(0, "lin", x=0, y=0, s=1)]},
    "emitters": [
        em("task_eject_mote.png", -30, t0=0, t1=5.2, rate=9, area=[-0.5, -0.8, 0.5, 3.2], vel=[-0.06, -0.06, 0.06, 0.06],
           life=[2.5, 4], size=[0.04, 0.08], tint="#fff1d0", a=0.7),
    ],
    "events": [ev(1.0, sound="step", vol=0.2), ev(1.45, sound="step", vol=0.22), ev(1.9, sound="step", vol=0.22),
               ev(2.35, sound="step", vol=0.2), ev(2.8, sound="step", vol=0.16), ev(5.2, sound="click", vol=0.6)],
})

# ============================================================================ SKIP: Museum - Nachtschicht
# Ein Waechter laeuft Streife durch die Saurierhalle und leuchtet herum. Immer wenn er wegschaut, lugt
# der T-Rex-Schaedel herein - dreht er sich um, ist der Schaedel weg. Schulterzucken, weiter geht's.
GUARD_Y = -1.22
SCENES.append({
    "id": "skip_patrol", "map": "museum", "skip": True, "title": "Nachtschicht", "length": 6.9, "text": [1.0, 2.8],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.1, x=-1.0, y=-0.35), key(2.3, z=1.1, x=-0.6, y=-0.35), key(3.6, z=1.06, x=0.2, y=-0.3),
               key(4.3, z=1.08, x=0, y=-0.3), key(6.9, z=1.1, x=0.6, y=-0.3)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_hall_bg.jpg", "z": -100},
    ] + [
        {"id": f"beam{i}", "sprite": "task_eject_beam.png", "z": -60, "x": bx, "y": 0.6, "pivot": [0.5, 1], "rot": 14,
         "tint": "#b8cfff", "a": 0.5, "flicker": {"amp": 0.08, "f": 0.4 + i * 0.1}} for i, bx in enumerate(beams)
    ] + [
        {"id": "rex", "keys": [key(0, "hold", x=11, y=REX_Y, s=REX_S), key(3.5, "hold", x=11), key(3.9, "out", x=6.7),
                               key(4.2, "hold", x=6.7), key(4.35, "in", x=11)],
         "wobble": [{"p": "y", "amp": 0.04, "f": 1.5, "t0": 3.9, "t1": 4.2}]},
    ] + [
        {"id": f"vert{i}", "sprite": "task_eject_trex_vert.png", "parent": "rex", "z": 6, "x": vx, "y": vy, "s": 1.2 + i * 0.12}
        for i, (vx, vy) in enumerate([(3.0, 0.12), (3.75, -0.08), (4.55, -0.34), (5.4, -0.66), (6.3, -1.02)])
    ] + [
        {"id": "jaw", "sprite": "task_eject_trex_jaw.png", "parent": "rex", "z": 7, "x": 2.48, "y": -0.64,
         "pivot": [506 / 540, 1 - 44 / 150], "keys": [key(0, rot=-3.5), key(3.9, "hold", rot=-3.5), key(4.05, rot=6), key(4.2, rot=-3.5)]},
        {"id": "head", "sprite": "task_eject_trex_head.png", "parent": "rex", "z": 8},
        {"id": "guard", "sprite": "task_eject_guard.png", "z": 2, "y": GUARD_Y, "pivot": [0.5, 0.02], "s": 0.9,
         "keys": [key(0, "lin", x=-7, sx=1, sy=1), key(2.3, "out", x=-1.0), key(3.4, "hold", sx=-1), key(4.2, "hold", sx=1),
                  key(4.35, "hold", sx=1, sy=1), key(4.45, "out", sy=0.92), key(4.6, "out", sy=1.05), key(4.72, sy=1),
                  key(4.8, "hold", x=-1.0), key(6.9, "in", x=7.5)],
         "wobble": [{"p": "y", "amp": 0.04, "f": 2.2, "t0": 0, "t1": 2.3}, {"p": "y", "amp": 0.04, "f": 2.2, "t0": 4.8, "t1": 6.9}]},
        {"id": "gshadow", "sprite": "task_eject_glow.png", "parent": "guard", "z": 1, "x": 0, "y": 0.03, "sx": 1.4, "sy": 0.3,
         "tint": "#000000", "a": 0.5},
        {"id": "gcone", "sprite": "task_eject_cone.png", "parent": "guard", "z": 3, "x": 0.55, "y": 0.85, "pivot": [0, 0.5], "s": 1.5,
         "tint": "#fff4d0", "a": 0.42,
         "keys": [key(0, rot=-5), key(2.3, rot=-5), key(2.6, rot=20), key(3.0, rot=-15), key(3.25, rot=0),
                  key(3.6, rot=15), key(4.0, rot=-10), key(4.2, rot=0)],
         "flicker": {"amp": 0.12, "f": 2}},
        {"id": "fg", "sprite": "task_eject_hall_fg.png", "z": 40, "y": -3.05, "depth": 1.3},
    ],
    "player": {"keys": [key(0, "lin", x=0, y=0, s=1)]},
    "emitters": [
        em("task_eject_mote.png", -58, t0=0, t1=6.9, rate=10, area=[-5, -1.2, 5, 0.8], vel=[-0.05, -0.08, 0.08, 0.05],
           life=[3, 5], size=[0.04, 0.09], tint="#cfe0ff", a=0.6),
    ],
    "events": [ev(t, sound="step", vol=0.35) for t in (0.3, 0.8, 1.3, 1.8, 2.25, 4.95, 5.45, 5.95, 6.45)]
              + [ev(3.6, sound="growl", vol=0.25), ev(4.2, sound="whoosh", vol=0.3)],
})

# ============================================================================ SKIP: Wald - Stilles Lagerfeuer
# Das Feuer knistert, Funken steigen, Rauch zieht. Eine Eule landet auf dem Baumstamm, schaut sich um,
# blinzelt, ruft einmal und fliegt wieder los.
OWL = (-3.05, -1.3)
SCENES.append({
    "id": "skip_camp", "map": "wald", "skip": True, "title": "Stilles Lagerfeuer", "length": 6.8, "text": [1.0, 2.8],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.06, x=0, y=-0.3), key(2.2, z=1.12, x=-1.2, y=-0.5), key(4.5, z=1.16, x=-0.9, y=-0.5),
               key(6.8, z=1.08, x=0, y=-0.4)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_camp_bg.jpg", "z": -100},
        {"id": "fireGlow", "sprite": "task_eject_glow.png", "z": -30, "x": 0, "y": -1.9, "s": 4.5, "tint": "#ff9a3c", "a": 0.45,
         "flicker": {"amp": 0.3, "f": 4}},
        {"id": "flame1", "sprite": "task_eject_flame.png", "z": -28, "x": -0.12, "y": -2.2, "pivot": [0.5, 0.1], "s": 1.4,
         "wobble": [{"p": "sx", "amp": 0.1, "f": 5}, {"p": "sy", "amp": 0.15, "f": 7.3}, {"p": "rot", "amp": 5, "f": 2.1}]},
        {"id": "flame2", "sprite": "task_eject_flame.png", "z": -27, "x": 0.1, "y": -2.18, "pivot": [0.5, 0.1], "s": 1.8,
         "wobble": [{"p": "sx", "amp": 0.1, "f": 4.3, "ph": 1}, {"p": "sy", "amp": 0.15, "f": 6.1, "ph": 2}, {"p": "rot", "amp": 4, "f": 1.7}]},
        {"id": "flame3", "sprite": "task_eject_flame.png", "z": -26, "x": 0.27, "y": -2.22, "pivot": [0.5, 0.1], "s": 1.2,
         "wobble": [{"p": "sx", "amp": 0.1, "f": 5.7, "ph": 2}, {"p": "sy", "amp": 0.15, "f": 8.2, "ph": 1}, {"p": "rot", "amp": 6, "f": 2.6}]},
        {"id": "owlFly", "sprite": "task_eject_owl.png", "z": -12, "s": 0.8,
         "keys": [key(0, "hold", x=-7, y=2.0, a=0), key(1.0, "hold", x=-7, y=2.0, a=1), key(2.2, "out", x=OWL[0], y=OWL[1] + 0.6),
                  key(2.25, "hold", a=0), key(5.2, "hold", a=1, x=OWL[0], y=OWL[1] + 0.6), key(6.8, "in", x=3.5, y=2.8)],
         "wobble": [{"p": "sy", "amp": 0.35, "f": 4}]},
        {"id": "owl", "sprite": "task_eject_owl_sit.png", "z": -11, "x": OWL[0], "y": OWL[1], "pivot": [0.5, 0.02], "s": 1.05,
         "keys": [key(0, "hold", a=0), key(2.25, "hold", a=1, rot=0, sy=1), key(2.32, "out", sy=0.85), key(2.48, sy=1),
                  key(2.9, rot=14), key(3.5, rot=-14), key(4.0, rot=0), key(5.2, "hold", a=0)]},
        {"id": "owlEyes", "sprite": "task_eject_owl_eyes.png", "parent": "owl", "z": -10, "x": 0, "y": 0.72,
         "keys": [key(0, sy=1), key(4.4, "hold", sy=1), key(4.45, sy=0.1), key(4.52, sy=1), key(4.75, "hold", sy=1),
                  key(4.8, sy=0.1), key(4.87, sy=1)]},
    ],
    "player": {"keys": [key(0, "lin", x=0, y=0, s=1)]},
    "emitters": [
        em("task_eject_mote.png", -25, t0=0, t1=6.8, rate=14, area=[-0.3, -2.1, 0.3, -1.9], vel=[-0.3, 0.6, 0.3, 1.4], drag=0.3,
           life=[1.0, 2.0], size=[0.04, 0.08], tint="#ffb050", a=1),
        em("task_eject_puff.png", -29, t0=0, t1=6.8, rate=3, area=[-0.2, -1.7, 0.2, -1.5], vel=[-0.1, 0.4, 0.2, 0.7],
           life=[2, 3], size=[0.3, 0.6], grow=0.5, tint="#3a3a44", a=0.3),
        em("task_eject_firefly.png", -35, t0=0, t1=6.8, rate=2.5, area=[-6, -1.0, 6, 1.0], vel=[-0.2, -0.1, 0.2, 0.15],
           life=[2, 4], size=[0.12, 0.2], a=1),
    ],
    "events": [ev(0, sound="fire", vol=0.5), ev(1.0, sound="whoosh", vol=0.25), ev(3.0, sound="owl", vol=0.45),
               ev(5.2, sound="whoosh", vol=0.3)],
})

# ============================================================================ SKIP: Wald - Am Fluss
# Ein Reh trinkt am Ufer, ein Fisch springt. Das Reh hebt den Kopf, lauscht - ein Zweig knackt, und es
# springt davon. Der Fluss laeuft ruhig weiter.
DEER = (-2.2, -1.86)
SCENES.append({
    "id": "skip_river", "map": "wald", "skip": True, "title": "Am Fluss", "length": 6.6, "text": [1.0, 2.8],
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.1, x=-1.0, y=-0.4), key(3.0, z=1.16, x=-0.6, y=-0.5), key(4.3, z=1.16, x=-0.8, y=-0.5),
               key(6.6, z=1.08, x=-1.1, y=-0.4)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_river_bg.jpg", "z": -100},
        {"id": "moonRef", "sprite": "task_eject_glow.png", "z": -60, "x": 3.0, "y": -0.35, "sx": 2.6, "sy": 0.22, "tint": "#dfe6ff", "a": 0.45,
         "wobble": [{"p": "sx", "amp": 0.25, "f": 0.6}], "flicker": {"amp": 0.3, "f": 1.1}},
        {"id": "fish", "sprite": "task_eject_fish.png", "z": -40, "s": 0.8,
         "keys": [key(0, "hold", x=1.5, y=-0.8, rot=-30, a=0), key(2.6, "hold", x=1.5, y=-0.8, rot=-30, a=1),
                  key(3.2, "lin", x=2.3, y=-0.8, rot=40, arc=0.9), key(3.22, "hold", a=0)]},
        {"id": "deer", "keys": [key(0, "hold", x=DEER[0], y=DEER[1], s=0.75, sy=1), key(4.35, "hold", x=DEER[0], y=DEER[1], sy=1),
                                key(4.5, "out", sy=0.9), key(4.62, x=DEER[0], sy=1.05), key(5.2, "lin", x=-5.2, y=DEER[1], arc=0.9),
                                key(5.8, "lin", x=-8.2, y=DEER[1], arc=0.8)]},
        {"id": "deerBody", "sprite": "task_eject_deer_body.png", "parent": "deer", "z": -5, "pivot": [0.5, 0.02]},
        {"id": "deerHead", "sprite": "task_eject_deer_head.png", "parent": "deer", "z": -4, "x": -0.6, "y": 1.15,
         "pivot": [128 / 150, 1 - 146 / 160],
         "keys": [key(0, rot=60), key(3.25, "hold", rot=60), key(3.6, "out", rot=0), key(3.9, rot=-6), key(4.2, rot=4), key(4.35, rot=0)],
         "wobble": [{"p": "rot", "amp": 4, "f": 1.2, "t0": 0, "t1": 3.2}]},
        {"id": "dshadow", "sprite": "task_eject_glow.png", "parent": "deer", "z": -6, "x": 0, "y": 0.02, "sx": 2.6, "sy": 0.35,
         "tint": "#000000", "a": 0.45},
        {"id": "mist1", "sprite": "task_eject_mist.png", "z": 20, "x": 4.6, "y": -1.3, "s": 1.2, "a": 0.5,
         "wobble": [{"p": "x", "amp": 0.2, "f": 0.15}]},
        {"id": "reeds", "sprite": "task_eject_reeds.png", "z": 40, "y": -3.0, "depth": 1.3},
    ],
    "player": {"keys": [key(0, "lin", x=0, y=0, s=1)]},
    "emitters": [
        em("task_eject_streak.png", -30, t0=0, t1=6.6, rate=22, area=[-6.5, -1.45, 3.4, 0.25], vel=[1.0, 0, 1.6, 0],
           life=[1.0, 1.6], size=[0.2, 0.35], tint="#9cc6e6", a=0.4, stretch=True),
        em("task_eject_firefly.png", -20, t0=0, t1=6.6, rate=3, area=[-6, 0.4, 3, 1.3], vel=[-0.2, -0.1, 0.2, 0.15],
           life=[2, 4], size=[0.15, 0.25], a=1),
        em("task_eject_puff.png", 21, t0=0, t1=6.6, rate=6, area=[3.6, -1.6, 4.4, -1.0], vel=[0.1, 0.3, 0.6, 0.9], drag=0.5,
           life=[1.5, 2.5], size=[0.6, 1.2], grow=0.3, tint="#dfe8f0", a=0.3),
        em("task_eject_ripple.png", -41, t0=0, t1=3.2, rate=1.4, area=[-3.75, -1.49, -3.62, -1.45],
           life=[0.8, 1.2], size=[0.12, 0.2], grow=1.4, tint="#cfe6f6", a=0.6),
        burst("task_eject_droplet.png", -39, 2.6, 10, area=[1.4, -0.85, 1.6, -0.75], vel=[-0.8, 0.8, 0.8, 2.2], acc=[0, -8],
              life=[0.4, 0.7], size=[0.04, 0.08], tint="#cfe6f6", a=0.9, stretch=True),
        burst("task_eject_droplet.png", -39, 3.2, 10, area=[2.2, -0.85, 2.4, -0.75], vel=[-0.8, 0.8, 0.8, 2.2], acc=[0, -8],
              life=[0.4, 0.7], size=[0.04, 0.08], tint="#cfe6f6", a=0.9, stretch=True),
        burst("task_eject_ripple.png", -41, 3.2, 2, area=[2.25, -0.82, 2.35, -0.78], life=[0.8, 1.2], size=[0.25, 0.35], grow=1.6,
              tint="#cfe6f6", a=0.6),
    ],
    "events": [ev(0, sound="rush", vol=0.25), ev(2.6, sound="splash", vol=0.35), ev(3.2, sound="splash", vol=0.3),
               ev(4.3, sound="twig", vol=0.5), ev(4.45, sound="whoosh", vol=0.3)],
})


# ============================================================================ Unknown's Collection: Void
# Eigene Datei fuer UC (UnknownsCollection/Resources/eject_void.json), spielt auf jeder Karte.
# Der Rauswurf faellt durch den Void: der Spieler treibt ins violette Nichts, hinter ihm oeffnet sich ein
# Riss, die Stimmzettel fliegen auf ihn zu - und durch ihn hindurch (er glitcht, halb durchsichtig,
# Stoerstreifen), der Riss schluckt sie und kollabiert. Der Spieler bleibt, schaut sich um, treibt zurueck.
RIFT = (-1.45, 0.15)
VOID_SCENES = [{
    "id": "void", "map": "any", "title": "Void", "length": 6.4, "text": [1.0, 2.6], "textStyle": "void",
    "bounds": [12, 6.8],
    "camera": [key(0, "lin", z=1.05, x=0, y=0), key(2.4, z=1.12, x=-0.3, y=0), key(3.55, "out", z=1.2, x=-0.5, y=0.05),
               key(3.8, "out", z=1.08, x=-0.4, y=0), key(6.4, z=1.05, x=-0.6, y=0.05)],
    "objects": [
        {"id": "bg", "sprite": "task_eject_void_bg.jpg", "z": -100, "depth": 0.85},
        {"id": "neb1", "sprite": "task_eject_glow.png", "z": -90, "x": -2.5, "y": 1.2, "s": 6, "tint": "#7a2cff", "a": 0.22,
         "wobble": [{"p": "x", "amp": 0.3, "f": 0.07}], "depth": 0.9},
        {"id": "neb2", "sprite": "task_eject_glow.png", "z": -90, "x": 3.2, "y": -1.1, "s": 4.5, "tint": "#ff3fe6", "a": 0.14,
         "wobble": [{"p": "y", "amp": 0.25, "f": 0.09}], "depth": 0.9},
        {"id": "rift", "sprite": "task_eject_void_rift.png", "z": -20, "x": RIFT[0], "y": RIFT[1],
         "keys": [key(0, "hold", s=0, rot=0), key(2.2, "hold", s=0), key(2.75, "back", s=1.25), key(3.55, s=1.3),
                  key(3.78, "in", s=0), key(6.4, "lin", rot=-900)]},
        {"id": "riftGlow", "sprite": "task_eject_glow.png", "parent": "rift", "z": -21, "s": 3.2, "tint": "#ff3fe6", "a": 0.55,
         "flicker": {"amp": 0.35, "f": 3}},
        {"id": "shock", "sprite": "task_eject_ripple.png", "z": -18, "x": RIFT[0], "y": RIFT[1], "tint": "#ff8cf4",
         "keys": [key(0, "hold", s=0, a=0), key(3.76, "hold", s=0.4, a=0.8), key(4.3, "out", s=7, a=0)]},
        {"id": "band1", "sprite": "task_eject_px.png", "screen": True, "z": 5, "sx": 75, "sy": 0.9, "tint": "#ff3fe6",
         "keys": [key(0, "hold", a=0, y=0.8), key(2.65, "hold", a=0.22), key(2.9, "hold", y=-1.3), key(3.15, "hold", y=0.25),
                  key(3.4, "hold", y=1.6), key(3.62, "hold", a=0)]},
        {"id": "band2", "sprite": "task_eject_px.png", "screen": True, "z": 6, "sx": 75, "sy": 0.5, "tint": "#8a4dff",
         "keys": [key(0, "hold", a=0, y=-0.6), key(2.75, "hold", a=0.26), key(3.0, "hold", y=1.1), key(3.25, "hold", y=-2.0),
                  key(3.5, "hold", y=-0.1), key(3.62, "hold", a=0)]},
    ],
    "player": {"keys": [
        key(0, "lin", x=-7, y=0.8, rot=25, s=0.95, sx=1, sy=1, flip=1), key(2.2, "out", x=-0.4, y=0.2, rot=-15),
        key(2.6, x=0, y=0.15, rot=-5), key(3.72, "hold", x=0, y=0.15, rot=-5, sx=1, sy=1),
        key(3.8, "out", sx=1.14, sy=0.88), key(4.0, x=0.05, y=0.1, rot=0, sx=1, sy=1),
        key(4.4, "hold", flip=-1), key(5.0, "hold", flip=1), key(5.1, "hold", x=0.05, y=0.1, rot=0),
        key(6.4, "in", x=-6.8, y=0.9, rot=30)],
        "wobble": [{"p": "y", "amp": 0.08, "f": 0.6, "t0": 0, "t1": 2.6}, {"p": "x", "amp": 0.07, "f": 16, "t0": 2.6, "t1": 3.65},
                   {"p": "y", "amp": 0.03, "f": 13, "t0": 2.6, "t1": 3.65}, {"p": "y", "amp": 0.06, "f": 0.5, "t0": 4.0, "t1": 6.4}],
        "flicker": {"amp": 0.7, "f": 9, "t0": 2.6, "t1": 3.65}},
    "emitters": [
        em("task_eject_mote.png", -92, t0=0, t1=6.4, rate=4, area=[-6, -3.4, 6, 3.4], life=[1, 2], size=[0.05, 0.1],
           tint="#e8dcff", a=0.8, fade=[0.4, 0.5]),
        em("task_eject_void_ballot.png", 5, t0=1.5, t1=3.45, rate=9, area=[6.2, -0.7, 6.6, 1.1], vel=[-4.9, -0.25, -4.4, 0.25],
           life=[1.62, 1.72], size=[0.34, 0.44], spin=[-140, 140], rot=[0, 360], grow=-0.25, a=1, fade=[0.05, 0.22]),
        em("task_eject_mote.png", -19, t0=2.3, t1=3.7, rate=30, area=[RIFT[0] - 1.0, RIFT[1] - 1.0, RIFT[0] + 1.0, RIFT[1] + 1.0],
           vel=[-0.2, -0.2, 0.2, 0.2], life=[0.4, 0.7], size=[0.05, 0.1], grow=-1, tint="#ff9cf4", a=1),
        burst("task_eject_void_shard.png", -17, 3.76, 22, area=[RIFT[0] - 0.2, RIFT[1] - 0.2, RIFT[0] + 0.2, RIFT[1] + 0.2],
              vel=[-2.5, -2, 2.5, 2.5], drag=1.2, life=[0.5, 1.0], size=[0.1, 0.2], spin=[-500, 500], rot=[0, 360], tint="#ff3fe6", a=1),
    ],
    "events": [ev(1.5, sound="whoosh", vol=0.5), ev(2.2, sound="growl", vol=0.5), ev(2.2, shake=[0.6, 0.02]),
               ev(2.7, sound="zap", vol=0.5), ev(3.0, sound="zap", vol=0.4), ev(3.3, sound="zap", vol=0.5),
               ev(3.76, sound="thud", vol=0.7), ev(3.76, flash=["#ff3fe6", 0.5, 0.35]), ev(3.76, shake=[0.3, 0.06]),
               ev(5.8, sound="whoosh", vol=0.25)],
}]
UC_JSON = Path(__file__).resolve().parent.parent.parent / "UnknownsCollection" / "Resources" / "eject_void.json"


def lint():
    """Meldet Eigenschaften, deren Wert sich zwischen zwei Nennungen aendert, waehrend dazwischen andere
    Keys liegen - dann gleitet der Wert ueber die ganze Strecke, was selten gewollt ist."""
    for sc in SCENES:
        for o in sc["objects"] + [dict(sc.get("player", {}), id="player")]:
            ks = sorted(o.get("keys", []), key=lambda k: k[0])
            last = {}
            for i, (t, props, ease) in enumerate(ks):
                for pr, v in props.items():
                    if pr in ("arc", "flip"):
                        continue
                    if pr in last:
                        j, t0, v0 = last[pr]
                        if i - j > 2 and v != v0 and ease != "hold":
                            print(f"  pruefen: {sc['id']}/{o['id']}.{pr} gleitet {t0}s -> {t}s ({v0} -> {v})")
                    last[pr] = (i, t, v)


# Daempfung aller Effekte - hier nachregeln statt in den einzelnen Szenen.
FX = {"shake": 0.5, "flash": 0.5, "flicker": 0.6, "glow": 0.85, "rate": 0.7, "burst": 0.75, "palpha": 0.8,
      "vignette": 0.5, "volume": 0.55}
GLOWS = ("task_eject_glow.png", "task_eject_beam.png", "task_eject_cone.png")


def damp(sc):
    for e in sc["events"]:
        if "shake" in e:
            e["shake"] = [e["shake"][0], round(e["shake"][1] * FX["shake"], 4)]
        if "flash" in e:
            e["flash"] = [e["flash"][0], round(e["flash"][1] * FX["flash"], 3), e["flash"][2]]
        if "vol" in e:
            e["vol"] = round(e["vol"] * FX["volume"], 3)
    for o in sc["objects"]:
        if "flicker" in o:
            o["flicker"] = dict(o["flicker"], amp=round(o["flicker"]["amp"] * FX["flicker"], 3))
        if o.get("sprite") in GLOWS:
            if "a" in o:
                o["a"] = round(o["a"] * FX["glow"], 3)
            for k in o.get("keys", []):
                if "a" in k[1]:
                    k[1] = dict(k[1], a=round(k[1]["a"] * FX["glow"], 3))
    for em_ in sc["emitters"]:
        if "rate" in em_:
            em_["rate"] = round(em_["rate"] * FX["rate"], 2)
        if "n" in em_:
            em_["n"] = max(1, round(em_["n"] * FX["burst"]))
        em_["a"] = round(em_.get("a", 1) * FX["palpha"], 3)


def main():
    lint()
    for sc in SCENES:
        damp(sc)
    doc = {"version": 1, "ppu": 180, "cinema": {"top": 0.8, "bottom": 0.55, "in": 0.45, "vignette": FX["vignette"]}, "scenes": SCENES}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(OUT, f"{OUT.stat().st_size / 1024:.1f} KB, {len(SCENES)} scenes")
    for sc in VOID_SCENES:
        damp(sc)
    vdoc = dict(doc, scenes=VOID_SCENES)
    UC_JSON.write_text(json.dumps(vdoc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(UC_JSON, f"{UC_JSON.stat().st_size / 1024:.1f} KB, {len(VOID_SCENES)} scene(s)")


if __name__ == "__main__":
    main()
