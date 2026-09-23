# Unknown's Atlas

Neue Karten für Among Us · Copyright (C) 2026 DaUnknown-0 · GPL-3.0-or-later

**Testversion.** Zwei spielbare Karten, auswählbar neben den Vanilla-Karten:

- **Vesper Museum**: ein Museum für Naturkunde und Technik nach Feierabend (14 Säle rund um eine
  Rotunde mit T.-Rex-Skelett, durchsichtige Brandschutz-Rollgitter als Türen).
- **Forest Station**: eine Forst- und Forschungsstation (acht begehbare Blockhütten, sechs
  Lichtungen, breite Waldwege; der dichte Wald ist die Wand).

Wiki: <https://daunknown-0.github.io/tor-mods-wiki/atlas.html>

## Installation

1. `UnknownsAtlas.dll` aus dem neuesten Release nach `BepInEx\plugins` legen.
2. Voraussetzungen: Among Us 2024.11.26, BepInEx 6 (be.697), Reactor 2.3.1. The Other Roles ist optional.
3. **Alle Spieler** brauchen Atlas. Wer es nicht hat, sieht die Skeld.

Im **Freeplay** stehen die Karten unter den Vanilla-Karten. In einer **Lobby** wählt der Host sie
in der Kartenauswahl der Spieleinstellungen; die Wahl wird per RPC 236 an alle übertragen.

## Wie es funktioniert

Beide Karten sitzen auf der Skeld (Relocate-in-Place): jede Konsole, jeder Vent, jede Tür, jede
Kamera und alle Systeme der Skeld bleiben dieselben Objekte und werden nur an ihre neuen Plätze
gesetzt. Neu sind Boden, Wände, Kollider, Objekte, Task-Blöcke, Minimap und Raumnamen. Dadurch
laufen Tasks, Sabotagen, Türen, Admin, Kameras und Vents online ohne eigenen Netzcode.

## Aufbau

```
src/AtlasMuseumBuilder.cs   Umbau der Skeld zur gewählten Karte (Kollider, Sicht, Konsolen, Vents,
                            Türen, Kameras, Minimap, Raumnamen)
src/AtlasMapDef.cs          eine Karte als Datensatz (Museum, Wald)
src/AtlasSelection.cs       Kartenwahl in Freeplay und Lobby, RPC 236
src/AtlasAssets.cs          Lader für die eingebetteten Bilder
src/AtlasMapShot.cs         Diagnose: Gesamtbild (F11) und Bildschirmfotos an Teststellen
src/Atlas*Data.cs, *Layout.cs  ERZEUGT von den Generatoren unten

tools/gen_museum.py         Museum: museum_layout.py -> Boden, Objekte, Task-Blöcke, Daten
tools/gen_wald.py           Wald: wald_layout.py + wald_geo.py -> dasselbe
tools/museum_art.py         gemeinsamer Zeichen-Baukasten (Among-Us-Stil)
tools/*_consoles.py         Task-Blöcke je Karte, tools/wald_vents.py eigene Vents
tools/gen_buttons.py        Logo-Knöpfe für das Freeplay-Menü
tools/inspect_museum.py, preview_wald.py, wald_plan.py, inspect_live.py
                            Abnahme ohne Spiel bzw. gegen den Live-Export (NightfallSurveyTool)
```

Neu erzeugen: `python tools/gen_museum.py` bzw. `python tools/gen_wald.py` (Python 3, Pillow,
shapely, numpy), danach `dotnet build -c Release`.

Releases entstehen allein durch einen Tag-Push (`vX.Y.Z` stable, `vX.Y.Z.W` Testversion); die CI
stempelt die Version aus dem Tag und hängt die DLL an.
