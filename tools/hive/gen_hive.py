# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_hive.py - Amberhive im Atlas-Dateiformat (docs/MAP_FORMAT.md).
#
#   python gen_hive.py plan            nur Plan-Vorschau beider Fassungen (_out/plan_1f.png, plan_2f.png) + Pruefung
#   python gen_hive.py build --art    beide Kartendateien und Paketbilder nach assets/amberhive/
#
# Waende sind "ausgeschnitten": begehbar ist nur, was Raum, Gang oder Durchgang ist (hive_layout.py), der Rest ist Wachs.
# Der Honigsee im Brunnen ist begehbar angelegt; gesperrt wird er zur Laufzeit von der Welt-Mechanik (Drehbruecke).

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, Polygon, box
from shapely.affinity import translate
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ATLAS = HERE.parent.parent
sys.path.insert(0, str(HERE))
import hive_layout as L  # noqa: E402

OUT = ATLAS / "assets" / "amberhive"
TMP = HERE / "_out"
SKELD_DOORS = (7, 6)
DOOR_SYSTEMS = ("Cafeteria", "Storage", "Electrical", "LowerEngine", "UpperEngine", "Security", "MedBay")


def poly(p):
    return Polygon(p).buffer(0)


def corridor(w, pts):
    return LineString(pts).buffer(w / 2, cap_style=2, join_style=2)


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def rings(g):
    out = []
    for p in parts(g):
        out.append(list(p.exterior.coords)[:-1])
        for h in p.interiors:
            out.append(list(h.coords)[:-1])
    return out


def v2(p):
    return [round(p[0], 4), round(p[1], 4)]


def shape_geom(sh):
    if sh[0] == "rect":
        return box(*sh[1:5])
    if sh[0] == "circle":
        return Point(sh[1], sh[2]).buffer(sh[3], 24)
    if sh[0] == "ellipse":
        from shapely.affinity import scale as sscale
        return sscale(Point(sh[1], sh[2]).buffer(1.0, 32), sh[3], sh[4])
    raise ValueError(sh)


def props_for(floors):
    out = []
    for p in L.PROPS:
        kind, sh, mode = p[:3]
        only = p[3] if len(p) > 3 else None
        if only is None or only == floors:
            out.append((kind, sh, mode))
    return out


class Variant:
    def __init__(self, floors):
        self.floors = floors
        self.vents = dict(L.VENTS)
        if floors == 2:
            self.vents.update(L.CROWN_VENTS)
        gx0, gy0, gx1, gy1 = L.GROUND_BOUNDS
        if floors == 2:
            cx0, cy0, cx1, cy1 = L.CROWN_BOUNDS
            self.bounds = (min(gx0, cx0), gy0, max(gx1, cx1), cy1)
        else:
            self.bounds = L.GROUND_BOUNDS
        rooms = list(L.ROOMS) + (list(L.CROWN_ROOMS) if floors == 2 else [])
        self.rooms = {k: (n, s, poly(p)) for k, n, s, p in rooms}
        geoms = [g for _n, _s, g in self.rooms.values()]
        geoms.append(poly(L.WELL))
        geoms += [corridor(w, pts) for w, pts in L.CORRIDORS]
        self.base = unary_union(geoms).buffer(0)                  # ohne Durchgaenge: fuer die Tuerrichtung
        geoms += [box(*p[:4]) for p in L.PASSAGES]
        if floors == 2:
            geoms += [corridor(w, pts) for w, pts in L.CROWN_CORRIDORS]
            geoms += [box(*p[:4]) for p in L.CROWN_PASSAGES]
        self.walk = unary_union(geoms).buffer(0)
        self.pit = Point(L.PIT[0], L.PIT[1]).buffer(L.PIT[2], 48)
        self.doors = [p for p in L.PASSAGES if p[4] == "door"]
        self.props = props_for(floors)
        self.opaque = [shape_geom(sh) for k, sh, m in self.props if m == "opaque"]
        self.glass = [shape_geom(sh) for k, sh, m in self.props if m == "glass"]
        self.obst = self.opaque + self.glass

    # ------------------------------------------------------------------ Konsolen
    def console_plan(self):
        """Raum -> Konsolen-Schluessel. Erdgeschoss: alle Skeld-Konsolen; Krone (2 Etagen): Airship-Aufgaben (CROWN_TASKS)."""
        plan = {}
        for key, (_n, s, _g) in self.rooms.items():
            if key in L.CROWN_TASKS:
                plan[key] = [ck for _t, ck in L.CROWN_TASKS[key]] if self.floors == 2 else []
            else:
                plan[key] = [k for k in L.SKELD_CONSOLES.get(s, []) if k not in L.FIXED]
        return plan

    def place_consoles(self):
        placed = {}
        door_pts = [box(*p[:4]).centroid for p in L.PASSAGES] + [Point(0, 4.9), Point(0, -4.9)]
        taken = [Point(p) for p in list(L.FIXED.values()) + [L.EMERGENCY, L.SURVEILLANCE, L.ADMIN_TABLE, L.FREEPLAY, L.SPAWN]]
        taken += [Point(p) for p in self.vents.values()] + [Point(p) for p in L.CAMERAS]
        for s in L.STAIRS:
            taken += [Point(s[0]), Point(s[1])]
        taken += [Point(L.CHUTE[0]), Point(L.CHUTE[1])]
        edge = self.walk.boundary
        blocked = unary_union(self.obst).buffer(0.55) if self.obst else None
        for key, keys in self.console_plan().items():
            g = self.rooms[key][2]
            cands = []
            for part in parts(g.buffer(-0.6)):
                line = part.exterior
                n = max(24, int(line.length / 0.25))
                for i in range(n):
                    p = line.interpolate(i / n, normalized=True)
                    if edge.distance(p) > 0.8:
                        continue
                    if min([p.distance(q) for q in door_pts] + [99]) < 1.7:
                        continue
                    if blocked is not None and blocked.contains(p):
                        continue
                    cands.append(p)
            chosen = []
            for k in keys:
                best, score = None, -1e9
                for need in (1.6, 1.2, 0.9):
                    for p in cands:
                        dd = min([p.distance(q) for q in chosen + taken] + [99])
                        if dd < need:
                            continue
                        sc = min(dd, 4.0) + 0.15 * (p.y - g.centroid.y)     # lieber an der Nordwand
                        if sc > score:
                            best, score = p, sc
                    if best is not None:
                        break
                if best is None:
                    best = g.representative_point()
                    print(f"WARN no spot for {k} in {key}")
                chosen.append(best)
                placed[k] = (round(best.x, 2), round(best.y, 2))
            taken.extend(chosen)
        placed.update(L.FIXED)
        return placed

    # ------------------------------------------------------------------ Pruefung
    def check(self, consoles):
        free = self.movement_area().difference(self.pit).buffer(-0.28)
        if self.obst:
            free = free.difference(unary_union(self.obst).buffer(0.28))
        free = free.buffer(0)
        comps = sorted(parts(free), key=lambda g: -g.area)
        main = comps[0]
        bad = 0
        levels = [main]
        if self.floors == 2 and len(comps) > 1:
            levels.append(comps[1])
        def reach(pt):
            return min(lv.distance(pt) for lv in levels)
        for k, (n, s, g) in self.rooms.items():
            if max(g.intersection(lv).area for lv in levels) < 1.0:
                print(f"WARN room {n} not reachable"); bad += 1
        pts = [(k, Point(p)) for k, p in consoles.items()] + [(f"vent {v}", Point(p)) for v, p in self.vents.items()]
        pts += [("emergency", Point(L.EMERGENCY)), ("spawn", Point(L.SPAWN)), ("surveillance", Point(L.SURVEILLANCE)),
                ("admin", Point(L.ADMIN_TABLE)), ("freeplay", Point(L.FREEPLAY))]
        if self.floors == 2:
            for s in L.STAIRS:
                pts += [("stair low", Point(s[0])), ("stair up", Point(s[1]))]
            pts += [("chute top", Point(L.CHUTE[0])), ("chute bottom", Point(L.CHUTE[1]))]
        for name, pt in pts:
            if reach(pt) > 0.7:
                print(f"WARN not reachable: {name} ({reach(pt):.2f} m)"); bad += 1
        for p in L.PASSAGES:
            through = box(*p[:4]).buffer(0.05).intersection(free)
            if through.is_empty:
                print(f"WARN passage {p[:4]} blocked"); bad += 1
            elif through.area < 0.15:
                print(f"NOTE passage {p[:4]} narrow with conservative 0.28 m player radius")
        area = self.walk.difference(self.pit).area
        print(f"{self.floors} floor(s): walkable {area:.0f} m2, {len(comps)} component(s), {bad} problem(s)")
        return bad

    # ------------------------------------------------------------------ Tueren
    def door_slots(self):
        vert, hori = [], []
        for i, door in enumerate(self.doors):
            x0, y0, x1, y1, _k, sysname = door[:6]
            if sysname not in DOOR_SYSTEMS:
                raise SystemExit(f"door group {sysname}: the Skeld has no door system there")
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            ns = self.base.contains(Point(cx, y1 + 0.2)) and self.base.contains(Point(cx, y0 - 0.2))
            ew = self.base.contains(Point(x1 + 0.2, cy)) and self.base.contains(Point(x0 - 0.2, cy))
            if len(door) > 6:                   # ausdrueckliche Richtung ("V" senkrechte Tuer, "H" waagerechte)
                ns, ew = door[6] == "H", door[6] == "V"
            if ns == ew:
                raise SystemExit(f"door passage {(x0, y0, x1, y1)}: direction unclear (N-S {ns}, E-W {ew})")
            if ns:                              # Nord-Sued-Durchgang: waagerechte Tuer quer dazu
                hori.append({"label": f"hex-H{i}", "x": round((x0 + x1) / 2, 3), "y": round((y0 + y1) / 2, 3),
                             "length": round(x1 - x0, 2), "group": sysname, "seeThrough": False})
            else:
                vert.append({"label": f"hex-V{i}", "x": round((x0 + x1) / 2, 3), "y": round((y0 + y1) / 2, 3),
                             "length": round(y1 - y0, 2), "group": sysname, "seeThrough": False})
        if len(vert) > SKELD_DOORS[0] or len(hori) > SKELD_DOORS[1]:
            raise SystemExit(f"too many doors: {len(vert)}V/{len(hori)}H, the Skeld has {SKELD_DOORS}")
        bx1, by1 = self.bounds[2], self.bounds[3]
        for lst, n, tag in ((vert, SKELD_DOORS[0], "V"), (hori, SKELD_DOORS[1], "H")):
            for k in range(n - len(lst)):
                lst.append({"label": f"parked-{tag}{k}", "x": round(bx1 + 40.0 + k * 4.0, 3),
                            "y": round(by1 + 40.0 + (4.0 if tag == "H" else 0.0), 3), "length": 1.0, "group": "Storage",
                            "seeThrough": False})
        return vert, hori

    # ------------------------------------------------------------------ Kollision
    def movement_area(self):
        bx0, by0, bx1, by1 = self.bounds
        solid = box(bx0 - 5, by0 - 5, bx1 + 5, by1 + 5).difference(self.walk)
        return self.walk.difference(translate(solid, 0, -0.3)).buffer(0)

    def collision(self):
        opaque, glass = self.opaque, self.glass
        move = self.movement_area()
        shadow = unary_union([self.walk, translate(self.walk, 0, 0.45)]).buffer(0)
        room_u = unary_union([g for _n, _s, g in self.rooms.values()])
        halls = [g for g in parts(self.walk.difference(room_u).buffer(0)) if g.area > 1.0]
        edges = unary_union([LineString(r + [r[0]]) for r in rings(self.walk)])
        return {
            "walls": [[v2(q) for q in r] for r in rings(move)],
            "shadowWalls": [[v2(q) for q in r] for r in rings(shadow)],
            "opaque": [[v2(q) for q in list(p.exterior.coords)[:-1]] for p in opaque],
            "opaqueCastsShadow": [p.distance(edges) > 0.08 for p in opaque],
            "glass": [[v2(q) for q in list(p.exterior.coords)[:-1]] for p in glass],
            "hallways": [[v2(q) for q in list(h.exterior.coords)[:-1]] for h in halls],
            "rooms": [{"key": k, "name": n, "room": s, "area": [v2(q) for q in list(g.exterior.coords)[:-1]]}
                      for k, (n, s, g) in self.rooms.items()],
        }


# ------------------------------------------------------------------ Plan-Vorschau
def font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default()


def plan_png(V, consoles, path, s=28):
    bx0, by0, bx1, by1 = V.bounds
    W, H = int((bx1 - bx0) * s), int((by1 - by0) * s)
    im = Image.new("RGB", (W, H), (58, 40, 22))
    d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - bx0) * s, (by1 - y) * s)

    def fill(g, col, outline=None):
        for p in parts(g):
            d.polygon([P(*q) for q in p.exterior.coords], fill=col, outline=outline)
            for h in p.interiors:
                d.polygon([P(*q) for q in h.coords], fill=(58, 40, 22))
    fill(V.walk, (226, 196, 140))
    for k, (n, sname, g) in V.rooms.items():
        fill(g, (240, 214, 160), (150, 100, 40))
    fill(V.pit, (230, 150, 20))
    for x in range(int(bx0), int(bx1) + 1):
        d.line([P(x, by0), P(x, by1)], fill=(0, 0, 0) if x % 5 == 0 else (90, 70, 50), width=1 if x % 5 else 1)
    for p in L.PASSAGES:
        col = (200, 60, 60) if p[4] == "door" else (120, 160, 90)
        d.rectangle([P(p[0], p[3]), P(p[2], p[1])], outline=col, width=2)
    f, fs = font(14), font(11)
    for k, (n, sname, g) in V.rooms.items():
        c = g.representative_point()
        t = f"{n}\n({sname})"
        d.multiline_text(P(c.x, c.y + 0.6), t, fill=(60, 30, 0), font=f, anchor="mm", align="center")
    for k, p in consoles.items():
        x, y = P(*p)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(30, 90, 200))
    for v, p in L.VENTS.items():
        x, y = P(*p)
        d.rectangle([x - 6, y - 4, x + 6, y + 4], fill=(90, 90, 90)); d.text((x + 7, y - 6), str(v), fill=(0, 0, 0), font=fs)
    for p in L.CAMERAS:
        x, y = P(*p); d.polygon([(x, y - 6), (x - 6, y + 5), (x + 6, y + 5)], fill=(200, 0, 160))
    for nm, p, col in (("SOS", L.EMERGENCY, (220, 0, 0)), ("SPAWN", L.SPAWN, (0, 140, 0)), ("CAM", L.SURVEILLANCE, (120, 0, 120)),
                       ("ADM", L.ADMIN_TABLE, (0, 0, 120))):
        x, y = P(*p); d.text((x, y), nm, fill=col, font=fs, anchor="mm")
    for k, sh, m in V.props:
        g = shape_geom(sh)
        col = {"opaque": (150, 60, 30), "glass": (190, 90, 190), "deco": (120, 150, 120)}[m]
        d.polygon([P(*q) for q in g.exterior.coords], outline=col, fill=None, width=2)
        c = g.centroid
        d.text(P(c.x, c.y), k, fill=col, font=fs, anchor="mm")
    if V.floors == 2:
        for a, b, _la, _lb in L.STAIRS:
            d.line([P(*a), P(*b)], fill=(0, 120, 120), width=2)
        d.line([P(*L.CHUTE[0]), P(*L.CHUTE[1])], fill=(230, 120, 0), width=3)
    im.save(path)


# ------------------------------------------------------------------ Graubau-Grafik

FLOOR_PPM = 48
ROOM_TINT = {"Cafeteria": (236, 206, 150), "Reactor": (228, 186, 120), "Admin": (230, 214, 170), "Storage": (214, 190, 140),
             "Electrical": (232, 220, 150), "LifeSupp": (214, 222, 182), "Shields": (236, 200, 170), "MedBay": (240, 222, 196),
             "Security": (206, 196, 170), "Comms": (230, 196, 196), "LowerEngine": (210, 180, 130), "UpperEngine": (210, 180, 130),
             "Weapons": (220, 200, 150), "Nav": (242, 226, 160)}
HALL = (222, 192, 138)
WAX = (92, 58, 26)
FRONT = (176, 120, 52)
HONEY = (238, 156, 24)


def render_area(V, bounds, ppm):
    """Boden eines Rechtecks (Etage): Raeume, Gaenge, Wachswand mit Stirnseiten, Honigsee, Raumnamen."""
    bx0, by0, bx1, by1 = bounds
    W, H = int(round((bx1 - bx0) * ppm)) // 4 * 4, int(round((by1 - by0) * ppm)) // 4 * 4
    im = Image.new("RGB", (W, H), WAX)
    d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - bx0) * ppm, (by1 - y) * ppm)
    clip = box(*bounds)

    def fill(g, col):
        for q in parts(g.intersection(clip)):
            d.polygon([P(*c) for c in q.exterior.coords], fill=col)
            for h in q.interiors:
                d.polygon([P(*c) for c in h.coords], fill=WAX)
    fill(V.walk, HALL)
    for k, (n, sname, g) in V.rooms.items():
        fill(g, ROOM_TINT.get(sname, HALL))
    hexr = 0.55                                       # Wabenmuster auf dem Boden
    for i in range(int((bx1 - bx0) / (1.5 * hexr)) + 2):
        for j in range(int((by1 - by0) / (math.sqrt(3) * hexr)) + 2):
            cx = bx0 + i * 1.5 * hexr
            cy = by0 + j * math.sqrt(3) * hexr + (math.sqrt(3) / 2 * hexr if i % 2 else 0)
            if not V.walk.contains(Point(cx, cy)):
                continue
            pts = [P(cx + hexr * math.cos(math.pi / 3 * t), cy + hexr * math.sin(math.pi / 3 * t)) for t in range(7)]
            d.line(pts, fill=(200, 160, 100), width=1)
    front = translate(V.walk, 0, 0.9).difference(V.walk).buffer(0)       # Stirnseiten der Nordwaende
    fill(front, FRONT)
    for q in parts(front.intersection(clip)):
        d.line([P(*c) for c in q.exterior.coords], fill=(70, 40, 14), width=2)
    if V.pit.intersects(clip):
        fill(V.pit, HONEY)
        d.ellipse([P(-L.PIT[2] + 0.25, L.PIT[2] - 0.25), P(L.PIT[2] - 0.25, -L.PIT[2] + 0.25)], outline=(255, 200, 80), width=3)
    for q in parts(V.walk.intersection(clip)):
        for ring in [q.exterior] + list(q.interiors):
            d.line([P(*c) for c in ring.coords], fill=(40, 22, 8), width=3)
    f = font(int(ppm * 0.42))
    for k, (n, sname, g) in V.rooms.items():
        if not g.intersects(clip):
            continue
        c = g.representative_point()
        d.text(P(c.x, c.y), n.upper(), fill=(120, 80, 30), font=f, anchor="mm")
    return im


BLENDER = "C:/Users/moritz/AppData/Local/Programs/Blender Foundation/blender-5.2.2-windows-x64/blender.exe"
ART_PPM = 100


def blender_floor(V, level, bounds, ppm):
    """Boden + Wachswaende aus Blender (floor_geo.py -> blender/floor_build.py), dazu weiche Schatten am Wandfuss."""
    import subprocess
    import numpy as np
    from scipy import ndimage
    subprocess.run([sys.executable, str(HERE / "floor_geo.py"), level], check=True, cwd=str(HERE))
    out = TMP / f"blender_{level}.png"
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", str(HERE / "blender" / "floor_build.py"), "--", level, str(ppm), str(out)],
                       capture_output=True, text=True)
    if "FLOOR RENDERED" not in r.stdout:
        print(r.stdout[-3000:], r.stderr[-2000:])
        raise SystemExit(f"blender floor {level} failed")
    im = Image.open(out).convert("RGB")
    bx0, by0, bx1, by1 = bounds
    W, H = im.size
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    P = lambda x, y: ((x - bx0) * ppm, (by1 - y) * ppm)
    for q in parts(V.walk.intersection(box(*bounds))):
        d.polygon([P(*c) for c in q.exterior.coords], fill=255)
        for h in q.interiors:
            d.polygon([P(*c) for c in h.coords], fill=0)
    m = np.asarray(mask) > 0
    dist = ndimage.distance_transform_edt(m) / ppm
    f = np.where(m, 0.80 + 0.20 * np.clip(dist / 0.7, 0, 1) ** 0.7, 1.0)
    arr = (np.asarray(im).astype(np.float32) * f[:, :, None]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def tile(im, bounds, ppm, start, prefix):
    bx0, by0, bx1, by1 = bounds
    ww, hh = im.size
    cols, rows = math.ceil(ww / 1024), math.ceil(hh / 1024)
    tw, th = (ww // cols) // 4 * 4, (hh // rows) // 4 * 4
    out, i = [], start
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * tw, r * th
            x1 = ww if c == cols - 1 else x0 + tw
            y1 = hh if r == rows - 1 else y0 + th
            w4, h4 = (x1 - x0) // 4 * 4, (y1 - y0) // 4 * 4
            im.crop((x0, y0, x0 + w4, y0 + h4)).save(OUT / f"{prefix}_floor_{i}.jpg", quality=86)
            out.append({"index": i, "x": round(bx0 + x0 / ppm, 4), "y": round(by1 - (y0 + h4) / ppm, 4), "w": w4, "h": h4})
            i += 1
    return out


def minimap(V, name):
    import importlib
    sys.path.insert(0, str(ATLAS / "tools"))
    map_labels = importlib.import_module("map_labels")
    s = 24
    bx0, by0, bx1, by1 = V.bounds
    ww, hh = int((bx1 - bx0) * s), int((by1 - by0) * s)
    img = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    Pt = lambda x, y: ((x - bx0) * s, (by1 - y) * s)
    for p in parts(V.walk):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=(250, 226, 170, 235))
    for k, (n, sname, g) in V.rooms.items():                     # Raeume etwas waermer als die Gaenge
        for q in parts(g):
            d.polygon([Pt(*c) for c in q.exterior.coords], fill=(255, 236, 186, 240))
    hexr = 0.7
    for i in range(int((bx1 - bx0) / (1.5 * hexr)) + 2):
        for j in range(int((by1 - by0) / (math.sqrt(3) * hexr)) + 2):
            cx = bx0 + i * 1.5 * hexr
            cy = by0 + j * math.sqrt(3) * hexr + (math.sqrt(3) / 2 * hexr if i % 2 else 0)
            if not V.walk.contains(Point(cx, cy)):
                continue
            pts = [Pt(cx + hexr * math.cos(math.pi / 3 * t), cy + hexr * math.sin(math.pi / 3 * t)) for t in range(7)]
            d.line(pts, fill=(226, 196, 130, 200), width=1)
    for p in parts(V.pit):
        d.polygon([Pt(*q) for q in p.exterior.coords], fill=(238, 160, 40, 235))
    for p in parts(V.walk):
        for ring in [p.exterior] + list(p.interiors):
            d.line([Pt(*q) for q in ring.coords], fill=(70, 40, 12, 255), width=4, joint="curve")
    labels = []
    for key, (n, _s, g) in V.rooms.items():
        c = g.representative_point()
        map_labels.place(d, font(16), n, c.x, c.y, g.buffer(-0.2), s, Pt, (70, 40, 12, 255), labels)
    img.save(OUT / name, optimize=True)
    return labels


def simple_icons():
    """Graubau-Knoepfe und Laufzeitbilder (werden in der Grafikstufe ersetzt)."""
    def btn(name, text, col):
        b = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        dd = ImageDraw.Draw(b)
        dd.ellipse([8, 8, 248, 248], fill=col + (255,), outline=(60, 30, 0, 255), width=10)
        dd.text((128, 128), text, font=font(64), fill=(60, 30, 0), anchor="mm")
        b.save(OUT / name)
    btn("task_stairs_button.png", "UP", (250, 210, 120))
    btn("task_hive_slide_button.png", "SLIDE", (250, 180, 80))
    br = Image.new("RGBA", (640, 170), (150, 98, 44, 255))
    dd = ImageDraw.Draw(br)
    for x in range(0, 640, 40):
        dd.line([(x, 0), (x, 170)], fill=(110, 70, 30), width=4)
    dd.rectangle([0, 0, 639, 169], outline=(60, 30, 0), width=8)
    br.save(OUT / "task_hive_bridge.png")
    Image.new("RGBA", (256, 256), (236, 160, 30, 255)).save(OUT / "task_hive_flood.png")
    b = Image.new("RGBA", (1000, 250), (0, 0, 0, 0))
    dd = ImageDraw.Draw(b)
    dd.rounded_rectangle([10, 30, 990, 220], 40, fill=(70, 40, 12, 240), outline=(250, 200, 90), width=8)
    dd.text((500, 125), "AMBERHIVE", font=font(110), fill=(255, 220, 140), anchor="mm")
    b.save(OUT / "button_amberhive.png", optimize=True)
    i = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    dd = ImageDraw.Draw(i)
    dd.ellipse([8, 8, 248, 248], fill=(70, 40, 12, 255), outline=(250, 200, 90), width=8)
    dd.text((128, 128), "AH", font=font(96), fill=(255, 220, 140), anchor="mm")
    i.save(OUT / "icon_amberhive.png", optimize=True)


def brand():
    """Kartenknopf (1000 x 250) und Lobby-Symbol (256) aus den Blender-Bildern art/brand (blender/brand_build.py)."""
    from PIL import ImageFilter
    src = HERE / "art" / "brand"
    if not (src / "brand_title.png").exists():
        return
    title = Image.open(src / "brand_title.png").convert("RGBA")
    emblem = Image.open(src / "brand_emblem.png").convert("RGBA")
    icon = Image.open(src / "brand_icon.png").convert("RGBA")
    b = Image.new("RGBA", (1000, 250), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle([4, 4, 996, 246], 34, fill=(255, 255, 255, 255))
    d.rounded_rectangle([14, 14, 986, 236], 26, fill=(14, 10, 6, 255))
    e = emblem.crop(emblem.getbbox()).resize((206, 206), Image.LANCZOS)
    b.alpha_composite(e, (24, 22))
    t = title.crop(title.getbbox())
    k = min(700 / t.width, 170 / t.height)
    t = t.resize((int(t.width * k), int(t.height * k)), Image.LANCZOS)
    halo = Image.new("RGBA", t.size, (255, 255, 255, 0))
    halo.putalpha(t.getchannel("A").filter(ImageFilter.MaxFilter(9)))
    x, y = 250 + (720 - t.width) // 2, (250 - t.height) // 2
    pad = Image.new("RGBA", b.size, (0, 0, 0, 0))
    pad.alpha_composite(halo, (x, y))
    b.alpha_composite(pad)
    b.alpha_composite(t, (x, y))
    b.save(OUT / "button_amberhive.png", optimize=True)
    ic = icon.crop(icon.getbbox())
    k = 240 / max(ic.size)
    ic = ic.resize((int(ic.width * k), int(ic.height * k)), Image.LANCZOS)
    out = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    out.alpha_composite(ic, ((256 - ic.width) // 2, (256 - ic.height) // 2))
    out.save(OUT / "icon_amberhive.png", optimize=True)


FLOOD_ZONES = [
    [(-13.6, -1.3), (-6.0, -1.3), (-6.0, 1.3), (-13.6, 1.3)],          # Westgang
    [(6.0, -1.3), (13.6, -1.3), (13.6, 1.3), (6.0, 1.3)],              # Ostgang
    [(-19.0, 3.2), (-17.2, 3.2), (-17.2, 7.1), (-19.0, 7.1)],          # Guard - Lamphouse
    [(16.2, -7.6), (18.2, -7.6), (18.2, -3.2), (16.2, -3.2)],          # East Press - Foundry
]


def emit(V, cons, tiles, minimap_file, labels, ppm=FLOOR_PPM, props=(), sprites=(), anim=None):
    vert, hori = V.door_slots()
    col = V.collision()
    buttons = {}
    for key, (name, sysname, g) in V.rooms.items():
        if sysname in ("Cafeteria", "Storage", "UpperEngine", "LowerEngine", "Security", "MedBay", "Electrical", "Reactor",
                       "LifeSupp", "Comms") and sysname not in buttons:
            c = g.representative_point()
            buttons[sysname] = v2((c.x, c.y + 0.8))
    r = L.PIT[2]
    hive = {"pit": [L.PIT[0], L.PIT[1], r], "bridgeWidth": L.BRIDGE_W, "bridgeLength": round(2 * r + 1.4, 2),
            "openSeconds": 22, "turnSeconds": 2.5, "bridgeWarning": 3,
            "floodFirst": 40, "floodGapMin": 45, "floodGapMax": 65,
            "floodWarning": 2.5, "floodRise": 2, "floodHold": 10, "floodDrain": 2.5, "floodSlow": 0.7,
            "floodZones": [[v2(q) for q in z] for z in FLOOD_ZONES],
            "anim": anim or {}}
    data = {
        "format": 1, "key": L.KEY, "displayName": L.DISPLAY_NAME, "resourcePrefix": L.KEY, "builtInEffects": False,
        "minimapFile": minimap_file,
        "minX": V.bounds[0], "minY": V.bounds[1], "maxX": V.bounds[2], "maxY": V.bounds[3],
        **col,
        "floorPixelsPerMeter": ppm, "floorTiles": tiles,
        "propPixelsPerMeter": 120, "props": list(props), "consoleSprites": list(sprites),
        "noFadeKinds": ["dance_floor", "stair_down", "chute_top", "hive_banner"],
        "consoles": {k: v2(p) for k, p in sorted(cons.items())},
        "emergencyButton": v2(L.EMERGENCY), "surveillanceConsole": v2(L.SURVEILLANCE), "adminTable": v2(L.ADMIN_TABLE),
        "freeplayLaptop": v2(L.FREEPLAY), "spawn": v2(L.SPAWN), "spawnRadius": L.SPAWN_RADIUS,
        "vents": {str(k): v2(p) for k, p in V.vents.items()}, "ventNetworks": L.VENT_NETS, "ventBridges": L.VENT_BRIDGES,
        "verticalDoors": vert, "horizontalDoors": hori,
        "cameras": [v2(p) for p in L.CAMERAS], "cameraViews": {str(k): v2(p) for k, p in L.CAMERA_VIEWS.items()},
        "mapButtons": buttons,
        "mapLabels": [{"x": round(x, 3), "y": round(y, 3), "halfW": round(hw, 3), "halfH": round(hh, 3)} for x, y, hw, hh in labels],
        "cameraColor": [0.16, 0.10, 0.04], "minLight": 1.0, "maxLight": 5.0,
        "viewSpots": [v2(p) for p in L.VIEW_SPOTS],
        "taskNames": L.TASK_NAMES, "customTasks": {}, "taskArt": {}, "taskText": {},
        "foreignTasks": [{"type": t, "ship": 4, "console": ck, "room": V.rooms[rk][1]}
                         for rk, lst in L.CROWN_TASKS.items() if rk in V.rooms for t, ck in lst],
        "hive": hive,
    }
    if V.floors == 2:
        data["stairs"] = [{"a": v2(a), "b": v2(b), "labelA": la, "labelB": lb} for a, b, la, lb in L.STAIRS]
        top, bottom = L.CHUTE
        hive["chute"] = [v2(top), v2(bottom), v2(L.CHUTE_EXIT)]
        data["levels"] = [{"name": "Lower Comb", "z": 0.0, "offset": [0, 0], "areas": []},
                          {"name": "Crown", "z": 4.0, "offset": [0, -21.0], "areas": []}]
    name = f"{L.KEY}_{V.floors}f.json"
    (OUT / name).write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"{name}: rooms {len(V.rooms)}, doors {len(vert)}V/{len(hori)}H, consoles {len(cons)}, vents {len(L.VENTS)}, "
          f"tiles {len(tiles)}, hallways {len(col['hallways'])}")


def main(argv):
    TMP.mkdir(exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "plan"
    if cmd == "build" and "--art" not in argv:
        raise SystemExit("Amberhive: build braucht --art, damit die echten Boeden erhalten bleiben")
    variants = {f: Variant(f) for f in (1, 2)}
    consoles = {}
    bad = 0
    for floors, V in variants.items():
        cons = V.place_consoles()
        bad += V.check(cons)
        V.door_slots()
        plan_png(V, cons, TMP / f"plan_{floors}f.png")
        consoles[floors] = cons
    print("plan written to", TMP)
    if bad:
        raise SystemExit(f"{bad} layout problem(s); build stopped before changing assets")
    if cmd != "build":
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob(f"{L.KEY}_floor_*.jpg"):
        old.unlink()
    V2 = variants[2]
    art = "--art" in argv
    ppm = ART_PPM if art else FLOOR_PPM
    if art:
        ground = blender_floor(V2, "ground", L.GROUND_BOUNDS, ppm)
        crown = blender_floor(V2, "crown", L.CROWN_BOUNDS, ppm)
    else:
        ground = render_area(V2, L.GROUND_BOUNDS, ppm)
        crown = render_area(V2, L.CROWN_BOUNDS, ppm)
    ground.save(TMP / "floor_ground.jpg", quality=85)
    crown.save(TMP / "floor_crown.jpg", quality=85)
    gt = tile(ground, L.GROUND_BOUNDS, ppm, 0, L.KEY)
    ct = tile(crown, L.CROWN_BOUNDS, ppm, len(gt), L.KEY)
    simple_icons()
    brand()
    import shutil
    for f in (HERE / "art" / "fx").glob("*.png"):                # Blender-Laufzeitbilder ersetzen die Graubau-Bilder
        shutil.copyfile(f, OUT / f.name)
    if (OUT / "task_hive_flood_0.png").exists() and (OUT / "task_hive_flood.png").exists():
        (OUT / "task_hive_flood.png").unlink()
    import art_pack
    props2, anim = art_pack.props(V2, OUT, L.KEY)
    vert, hori = V2.door_slots()
    labels_d = [s["label"] for s in vert + hori if not s["label"].startswith("parked")]
    sprites = art_pack.consoles(V2, consoles[2], OUT, L.KEY, sorted(L.VENTS), len(L.CAMERAS), labels_d)
    for floors, V in variants.items():
        mm = f"{L.KEY}_{floors}f_minimap.png"
        labels = minimap(V, mm)
        mine = {(k, sh) for k, sh, _m in V.props}
        props = [{k: v for k, v in e.items() if k != "_src"} for e in props2 if (V2.props[e["_src"]][0], V2.props[e["_src"]][1]) in mine]
        emit(V, consoles[floors], gt + (ct if floors == 2 else []), mm, labels, ppm, props, sprites, anim)
    if bad:
        print(f"!! {bad} problem(s)")


if __name__ == "__main__":
    main(sys.argv)
