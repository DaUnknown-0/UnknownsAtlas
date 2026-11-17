"""Life-Pollenbereich gegen die vorhandenen Karten pruefen, ohne Among Us zu starten."""
import json
import math
from pathlib import Path


def inside(poly, point):
    x, y = point
    result = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            result = not result
        j = i
    return result


root = Path(__file__).resolve().parents[3]
for floors in (1, 2):
    data = json.loads((root / f"assets/amberhive/amberhive_{floors}f.json").read_text(encoding="utf-8"))
    flower = next(p for p in data["props"] if p["kind"] == "flower_pots")
    center = ((flower["footX0"] + flower["footX1"]) / 2 - 1.05, flower["baseY"] + .55)
    room = next(r["area"] for r in data["rooms"] if r["key"] == "waggle")
    blockers = data["opaque"] + data["glass"]
    probes = [center]
    for radius in (.25, .5, .75, .99):
        for i in range(48):
            a = i * 2 * math.pi / 48
            probes.append((center[0] + .8 * radius * math.cos(a), center[1] + .65 * radius * math.sin(a)))
    for point in probes:
        assert inside(room, point), (floors, "Pollenpunkt ausserhalb des Waggle Studio", point)
        assert not any(inside(poly, point) for poly in blockers), (floors, "Pollenpunkt im Moebel", point)
    for i in range(16):
        a = i * 2 * math.pi / 16
        point = (center[0] + .25 * math.cos(a), center[1] + .25 * math.sin(a))
        assert inside(room, point) and not any(inside(poly, point) for poly in blockers), "Spielerkreis im Pollenbereich blockiert"
    print(f"{floors} Etage(n): Pollenbereich ({center[0]:.2f} / {center[1]:.2f}), {len(probes) + 16} Geometriepruefungen erfolgreich.")

print("Konsolen-Kollider und die echte Spielerbewegung bleiben Teil des Spieltests.")
