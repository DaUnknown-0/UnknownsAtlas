Harte Regeln: Starte KEINE Subagents und KEINE Forks (kein Agent-Tool, kein Workflow). Starte nicht Among Us und keinen Browser, kein git (auch nicht lesend). Keine Gedankenstriche (:) in Texten/Kommentaren. Alles in Blender (headless), keine Bild-KI.

Basisordner: `D:\programmieren\2025\Amogus\Tracker V2\Tracker\Mod stuff\TOR Mod\UnknownsAtlas\` (Pfade unten relativ dazu)

Ziel: Alle 31 Einrichtungsobjekte der Among-Us-Karte "Amberhive" (Imkerei-Station in einem Bienenstock) NEU MODELLIEREN und in Blender rendern, im neuen Kartenstil. Der Stil (art/STIL_V2.md) steht schon; die Objekte wurden darin aber nur neu eingefaerbt, ihre Formen sind die alten und wirken grob und kastig. Du baust jede Form neu: bessere Silhouetten, glaubwuerdige Konstruktion (Holzverbindungen, Messingbeschlaege, Wachs, Glas, Stoff), mehr Tiefe und Detail, wo es auf Spielgroesse lesbar bleibt, und deutlich bessere Animationen (Blasebalg pumpt, Presse dreht, Kessel brodelt, Tanzboden pulsiert, Gluehonig flackert). Jedes Objekt soll auf den ersten Blick zeigen, was es ist.

Lies zuerst (sonst nur, was du wirklich brauchst):
- `tools\hive\art\STIL_V2.md` (verbindlich) und `tools\hive\art\props\_beispiel_raum.jpg`
- `tools\hive\art\props\_sheet.png` (jetziger Stand aller 31 Arten) und `tools\hive\_out\preview_2f.png` (Karte im neuen Stil)
- `tools\hive\art_props.json` (Fussflaeche, Hoehe, Bildzahl, Beschreibung, Modus je Art)
- `tools\hive\blender\hive_style.py`, `tools\hive\blender\props_common.py` (Anker, Frames, SKIN), dann `props_hall.py`, `props_machines.py`, `props_storage.py`, `props_transit.py`, `props_sheet.py`

Darfst schreiben: `tools\hive\blender\props_*.py` (umbauen oder neu), `tools\hive\art\props\`. Durch den Pruefbau werden `assets\amberhive\*` neu geschrieben, das ist gewollt. `hive_style.py` nur importieren (Erweiterungen in props_common.py).
Nicht aendern: alles andere (`hive_layout.py`, `gen_hive.py`, `art_pack.py`, `art_props.json`, `art\consoles`, `art\fx`, `blender\consoles_*.py`, `blender\eject_*.py`, `assets\amberhive\task_eject_*`, `src\`).

Vertraege, die gleich bleiben muessen:
- Je Art `art\props\<art>.png` + `.json` aus render_sprite (ppm 120, Anker = Welt 0/0: Grundflaeche x in [-w/2, w/2], y in [0, d], Fuss auf z = 0). Das Objekt fuellt seine Fussflaeche aus art_props.json (sie ist die Kollision) und haelt die Hoehe ungefaehr ein.
- Animierte Arten: `<art>_f<k>.png/.json` mit genau der Bildzahl aus art_props.json, alle Frames gleich gross, gleicher Anker; die Schleife muss nahtlos laufen (letztes Bild geht fluessig ins erste ueber).
- Modus "glass"/"opaque"/"deco" bleibt; ein Objekt mit Modus "glass" darf durchsichtig wirken (offenes Gestell), "opaque" soll massiv wirken.

Kontext:
- Blender: `C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P <skript> -- <args>`.
- Pruefbau: `python tools\hive\gen_hive.py build --art` (immer MIT --art), danach `python tools\hive\preview_hive.py 2 44` -> `tools\hive\_out\preview_2f.png`. Kontaktbogen: `blender\props_sheet.py`.
- Parallel arbeitet evtl. noch jemand an `art\consoles` oder an den Rauswurf-Szenen; deren Dateien nicht anfassen.

Pruefe einmal am Ende: Pruefbau laufen lassen, Kontaktbogen und `_out\preview_2f.png` ansehen (Read-Tool), offensichtliche Fehler beheben. Fuer jede animierte Art einmal alle Frames nebeneinander ansehen.

Bericht: hoechstens 12 Zeilen: erzeugte/geaenderte Dateien (Anzahl), Arten mit deutlich geaenderter Wirkung, Annahmen, was du selbst fuer schwach haeltst.
