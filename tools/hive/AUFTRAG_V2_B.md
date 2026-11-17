Harte Regeln: Starte KEINE Subagents und KEINE Forks (kein Agent-Tool, kein Workflow). Starte nicht Among Us und keinen Browser, kein git. Keine Gedankenstriche (:) in Texten/Kommentaren. Alles in Blender (headless), keine Bild-KI.

Basisordner: `D:\programmieren\2025\Amogus\Tracker V2\Tracker\Mod stuff\TOR Mod\UnknownsAtlas\` (Pfade unten relativ dazu)

Ziel: Alle Konsolen, Tueren, Vents und Kameras der Among-Us-Karte "Amberhive" (Imkerei-Station in einem Bienenstock) im NEUEN Stil der Karte neu gestalten und in Blender neu rendern. Den Stil hat bereits jemand festgelegt und Boeden und Einrichtung damit neu gemacht; deine Bilder muessen dazu passen, als kaemen sie aus einer Hand. Ziel ist sichtbar hoehere Qualitaet als die jetzige Fassung (Form, Material, Detail, Lesbarkeit: man muss im Spiel sofort sehen, was ein Aufgabenpunkt ist).

Lies zuerst (sonst nur, was du zum Umbau wirklich brauchst):
- `tools\hive\art\STIL_V2.md` (der neue Stil, verbindlich) und die dort genannten Beispielbilder
- `tools\hive\_out\preview_2f.png` (Gesamtbild der Karte im neuen Stil, Konsolen darin noch alt)
- `tools\hive\art_consoles.json` (welche Konsole welches Motiv bekommt, Motivbeschreibungen, Tueren mit Achse und Laenge, Vents, Kameras)
- `tools\hive\blender\hive_style.py`, `tools\hive\blender\consoles_common.py` (Anker, render, frames), dann die Gruppen `consoles_tasks.py`, `consoles_crown.py`, `consoles_doors.py`, `consoles_vents.py`, `consoles_sheet.py`
- `tools\hive\art_pack.py` Zeilen 85-130 (wie die Bilder eingelesen werden)

Darfst schreiben: `tools\hive\blender\consoles_*.py` (umbauen oder neu), `tools\hive\art\consoles\`. Durch den Pruefbau werden `assets\amberhive\*` neu geschrieben, das ist gewollt. `hive_style.py` nur importieren (Erweiterungen in consoles_common.py).
Nicht aendern: alles andere (`hive_layout.py`, `gen_hive.py`, `art_pack.py`, `art_consoles.json`, `art\props`, `art\fx`, `src\`).

Vertraege, die gleich bleiben muessen:
- Gleiche Dateinamen: je Motiv `art\consoles\<motiv>.png/.json` (render_sprite, ppm 120, gleicher Anker wie heute laut consoles_common.py), Tueren `door_<label>_0..5` (0 zu, 5 offen, alle 6 gleich gross, gleicher Anker), Vents `vent_0..5` (0 zu, 5 offen), Kameras `camera_off` / `camera_on`.
- Groesse etwa wie heute (Breite und Tiefe je Motiv hoechstens +-15 %): das Spiel leitet aus den Bildgrenzen Kollisionsflaechen ab. Wandgeraete bleiben Wandgeraete, Bodengeraete bleiben Bodengeraete.
- Tueren: Oeffnung = length aus art_consoles.json; geschlossen muss die Tuer die Oeffnung sichtbar ganz verschliessen; die 6 Bilder ergeben eine fluessige Auf-Bewegung.

Kontext:
- Blender: `C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P <skript> -- <args>`.
- Pruefbau der Karte: `python tools\hive\gen_hive.py build --art` (immer MIT --art), danach `python tools\hive\preview_hive.py 2 44` -> `tools\hive\_out\preview_2f.png`. Kontaktbogen: `blender\consoles_sheet.py` oder PIL.

Liefere: alle Bilder in `art\consoles\` neu, Skripte reproduzierbar.

Pruefe einmal am Ende: Pruefbau laufen lassen, `_out\preview_2f.png` und einen Kontaktbogen (inkl. einer Tuer in allen 6 Phasen) ansehen (Read-Tool), offensichtliche Fehler beheben.

Bericht: hoechstens 12 Zeilen: erzeugte/geaenderte Dateien (Anzahl), Motive mit deutlich geaenderter Groesse, Annahmen, was du selbst fuer schwach haeltst.
