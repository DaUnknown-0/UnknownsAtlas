Harte Regeln: Starte KEINE Subagents und KEINE Forks (kein Agent-Tool, kein Workflow). Starte nicht Among Us und keinen Browser, kein git. Keine Gedankenstriche (:) in Texten/Kommentaren. Alles in Blender (headless), keine Bild-KI.

Basisordner: `D:\programmieren\2025\Amogus\Tracker V2\Tracker\Mod stuff\TOR Mod\UnknownsAtlas\` (Pfade unten relativ dazu)

Ziel: Die Grafik der Among-Us-Karte "Amberhive" (Imkerei-Station in einem riesigen Bienenstock) komplett neu gestalten und in Blender neu rendern: neuer Stil, Boeden, alle 31 Einrichtungsobjekte (inkl. Animationsbilder), Laufzeitbilder (Bruecke, Honiglachen, Bienen, Knoepfe) und Logo. Du legst dabei den Stil fest, den spaeter auch Konsolen, Tueren und Rauswurf-Szenen uebernehmen.

Stil: frei. Die jetzige Fassung (Sicherung in `tools\hive\_backup_v1\`) darf komplett ersetzt werden. Ziel ist sichtbar hoehere Qualitaet: mehr Form, Material, Licht und Detail, stimmige Palette, klare Lesbarkeit. Feste Randbedingungen aus dem Spiel:
- Draufsicht mit leichter Schraegsicht (die Scherung in hive_style.finish: y' = y + 0,59 * z). Alle Atlas-Karten nutzen sie, bitte beibehalten.
- Crewmates (ca. 0,9 m hoch, kraeftige Spielerfarben, schwarze Umrisse) muessen sich auf jedem Boden klar abheben: Boeden ruhiger und weniger gesaettigt als Objekte und Figuren.
- Das Spiel legt Sicht-Schatten ueber alles ausserhalb des Lichtradius; sehr dunkle Boeden wirken dann schwarz.

Lies zuerst (sonst nur, was du zum Umbau wirklich brauchst):
- `tools\hive\KONZEPT.md` (Idee, Raeume)
- `tools\hive\_show\preview_2f.jpg` und einige `tools\hive\_show\pub\room_*.jpg` (so sieht es jetzt im Spiel aus)
- `tools\hive\blender\hive_style.py`, `tools\hive\blender\props_common.py` (Anker-Vertrag), eine Gruppe z. B. `props_machines.py`
- `tools\hive\art_props.json` (31 Arten mit Fussflaeche, Hoehe, Bildzahl, Beschreibung)
- `tools\hive\floor_geo.py` + `tools\hive\blender\floor_build.py` (Boden), `tools\hive\fx_geo.py` + `tools\hive\blender\fx_build.py`, `tools\hive\blender\brand_build.py`
- `tools\hive\art_pack.py` Zeilen 1-60 (wie die Bilder eingelesen werden)

Darfst schreiben: `tools\hive\blender\*.py` (umbauen oder neu), `tools\hive\art\props\`, `tools\hive\art\fx\`, `tools\hive\art\brand\`, `tools\hive\floor_geo.py` und `tools\hive\fx_geo.py` (nur Aussehen: Materialien, Muster, Dekor; Raum- und Wandformen, Grenzen und Bildgroessen bleiben), neue Datei `tools\hive\art\STIL_V2.md`. Durch den Pruefbau werden `assets\amberhive\*` neu geschrieben, das ist gewollt.
Nicht aendern: `hive_layout.py`, `gen_hive.py`, `art_pack.py`, `art_props.json`, alles in `src\`, `assets\amberhive\task_eject_*`, `blender\consoles_*.py`, `blender\eject_*.py`.

Vertraege, die gleich bleiben muessen (sonst bricht der Einbau):
- Requisiten: je Art `art\props\<art>.png` + `.json` aus `render_sprite` (ppm 120, Anker = Welt 0/0 wie in props_common: Grundflaeche x in [-w/2, w/2], y in [0, d], Fuss auf z = 0). Animierte Arten zusaetzlich `<art>_f<k>.png/.json` mit genau der Bildzahl aus art_props.json, alle Frames gleich gross mit gleichem Anker. Das Objekt soll seine Fussflaeche aus art_props.json fuellen (sie ist die Kollision).
- `hive_style.py` bleibt rueckwaertskompatibel: die Funktionen und Palettenschluessel, die `consoles_*.py` und `eject_*.py` benutzen, muessen weiter funktionieren (die werden spaeter von anderen auf deinen Stil umgestellt). Neues darfst du ergaenzen.
- Laufzeitbilder: gleiche Dateinamen, Grenzen und ppm wie heute aus fx_geo.py (task_hive_bridge, task_hive_flood_0..3, task_hive_bee_0/1, task_stairs_button, task_hive_slide_button). Brand: brand_title.png, brand_emblem.png, brand_icon.png.

Kontext:
- Blender: `C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P <skript> -- <args>`. EEVEE, Freestyle-Umrisse sind Teil des jetzigen Stils (darfst du anders loesen).
- Pruefbau der ganzen Karte: `python tools\hive\gen_hive.py build --art` (immer MIT --art, sonst entstehen Graubau-Boeden), danach `python tools\hive\preview_hive.py 2 44` -> `tools\hive\_out\preview_2f.png` (Gesamtbild wie im Spiel, ohne Licht). Einzelbilder pruefen: Kontaktbogen per `blender\props_sheet.py` oder PIL.

Liefere: neuer Stil, beschrieben in `art\STIL_V2.md` (hoechstens 40 Zeilen: Palette mit Werten, Licht/Schattierung, Linien, Materialien, Regeln fuer Konsolen/Tueren/Szenen, Beispielbilder), alle Bilder oben neu gerendert, Skripte reproduzierbar.

Pruefe einmal am Ende: Pruefbau laufen lassen, `_out\preview_2f.png` und einen Requisiten-Kontaktbogen ansehen (Read-Tool), offensichtliche Fehler beheben.

Bericht: hoechstens 12 Zeilen: Stil in zwei Saetzen, erzeugte/geaenderte Dateien (Anzahl), Annahmen, was du selbst fuer schwach haeltst.
