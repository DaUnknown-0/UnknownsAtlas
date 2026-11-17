# geo_export.py - Geometrie fuer den Blender-Boden (blender/floor_build.py): je Etage begehbare Flaeche, Raeume mit Bodenart,
# Honigsee. Schreibt _out/geo_<etage>.json.
import json
import sys
from pathlib import Path
from shapely.geometry import box, Point
import gen_hive as G
import hive_layout as L

FLOOR = {  # Raum-Schluessel -> Bodenart (floor_build.py)
    "mead": "planks_warm", "queen": "royal_tiles", "cellar": "planks_dark", "keeper": "planks_office", "bellows": "wax_tiles",
    "nursery": "cream_hex", "lamp": "stone_dark", "foundry": "clay_tiles", "guard": "planks_dark", "waggle": "dance_hex",
    "wpress": "stone_slab", "epress": "stone_slab", "wasp": "planks_warm", "sun": "sun_stone",
    "sundeck": "sun_planks", "archive": "royal_tiles", "dock": "sun_planks",
}


def polys(g):
    out = []
    for p in G.parts(g):
        out.append({"outer": [[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]],
                    "holes": [[[round(x, 3), round(y, 3)] for x, y in list(h.coords)[:-1]] for h in p.interiors]})
    return out


def main():
    V = G.Variant(2)
    for name, bounds in (("ground", L.GROUND_BOUNDS), ("crown", L.CROWN_BOUNDS)):
        clip = box(*bounds)
        walk = V.walk.intersection(clip)
        rooms = []
        for k, (n, s, g) in V.rooms.items():
            if g.intersects(clip):
                rooms.append({"key": k, "name": n, "floor": FLOOR.get(k, "wax_tiles"), "polys": polys(g)})
        halls = walk.difference(G.unary_union([g for _n, _s, g in V.rooms.values()])).buffer(0)
        data = {"bounds": list(bounds), "walk": polys(walk), "rooms": rooms, "halls": polys(halls),
                "pit": list(L.PIT) if name == "ground" else None, "well": [list(p) for p in L.WELL] if name == "ground" else None}
        (G.TMP / f"geo_{name}.json").write_text(json.dumps(data), encoding="utf-8")
        print(name, "walk parts", len(data["walk"]), "rooms", len(rooms))


if __name__ == "__main__":
    main()
