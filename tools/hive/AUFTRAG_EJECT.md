Harte Regeln: Starte KEINE Subagents und KEINE Forks (kein Agent-Tool, kein Workflow). Starte nicht Among Us und keinen Browser. Schreibe nur in `UnknownsAtlas\assets\amberhive\` (nur neue Dateien `task_eject_hive_*`), `UnknownsAtlas\tools\hive\blender\eject_*.py`, `UnknownsAtlas\tools\hive\art\eject\` (Zwischenstand) und in `UnknownsAtlas\tools\eject_scenes.py` (nur NEUE Szenen mit "map": "amberhive" anhaengen, bestehende Szenen nicht anfassen). `hive_style.py` nur importieren. Keine Gedankenstriche (:) in Texten/Kommentaren. Nichts committen.
Basisordner: `D:\programmieren\2025\Amogus\Tracker V2\Tracker\Mod stuff\TOR Mod\UnknownsAtlas\`

Ziel: Rauswurf- und Skip-Szenen fuer die neue Among-Us-Karte "Amberhive" (Imkerei-Station in einem riesigen Bienenstock), alle Grafiken in Blender modelliert und gerendert, als Daten-Szenen fuer Atlas' Szenen-Engine.

Lies (sonst nichts):
- `tools\eject_scenes.py` Zeilen 1-60 (Format, Hilfsfunktionen key/em/burst/ev), 640-707 (Beispiel Rauswurf "cannon"), 905-960 (Beispiele Skip), Zeilen 1040-1081 (lint/main)
- `tools\hive\blender\hive_style.py` (Stil: Palette, flache Schattierung, Freestyle-Linien; fuer Szenen KEINE Scherung noetig: `finish(ob, shear=False)`, eigene Kamera)
- `tools\hive\KONZEPT.md`, und als Stilvorlage der Karte `tools\hive\_out\preview_1f.png` (ansehen)

Kontext:
- Blender: `C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P <skript> -- <args>`.
- Szenen-Einheiten: 1 Einheit = 180 px. Hintergrund fuer bounds [12, 6.8] = 2160 x 1224 px (JPG). Ebenen als PNG mit Alpha, jeweils so gross wie noetig. Szenen sind Seitenansichten (Kino), keine Kartenaufsicht.
- Bildnamen MUESSEN mit `task_eject_hive_` beginnen und liegen in `assets\amberhive\` (Atlas laedt sie dort aus dem Kartenpaket). Vorhandene allgemeine Bilder duerfen mitbenutzt werden: task_eject_glow.png, task_eject_px.png, task_eject_puff.png, task_eject_mote.png, task_eject_droplet.png, task_eject_vignette.png.
- Klaenge nur aus: boom chime clack click creak fire grind growl organ owl pop roar rush sizzle slam splash step thud thunder twig whoosh zap.
- Der Spieler wird von der Engine gezeichnet (Objekt "player", Keys wie in "cannon"); Skip-Szenen haben keinen Rauswurf, nur Stimmung.
- Alles, was sich bewegt, braucht Bewegung (Keys, wobble, flicker, Emitter). Bienenfluegel: schnelles wobble auf sy oder zwei Bilder im Wechsel.

Liefere:
- Mindestens 2 Rauswurf-Szenen und 2 Skip-Szenen, je 6,4 bis 7,4 s, "map": "amberhive", ids `hive_*`. Vorschlaege (darfst verbessern):
  1. Rauswurf "Schwarm": Kronensaal von unten, runde Oeffnung zum Abendhimmel. Bienen sammeln sich, heben den Crewmate hoch und tragen ihn durch die Oeffnung davon, er wird klein am Himmel.
  2. Rauswurf "Honigbrunnen": Querschnitt des Brunnens, der Crewmate steht auf der Drehbruecke, sie dreht sich knarrend, er rutscht ab, faellt in den Honig, versinkt langsam mit Blasen, die letzte Blase ploppt.
  3. Skip "Die Koenigin gaehnt": Bienenkoenigin auf dem Thron, gaehnt gross, winkt gelangweilt ab, schlaeft ein.
  4. Skip "Stilles Sonnendeck": eine Biene landet auf einer Bluete, nippt, ein Honigtropfen faellt, sonst passiert nichts.
- Blender-Skripte `tools\hive\blender\eject_<szene>.py`, die alle Bilder reproduzierbar erzeugen.
- Danach `python tools\eject_scenes.py` ausfuehren (muss ohne Fehler durchlaufen, schreibt assets\eject_scenes.json).

Prüfe einmal: fuer jede Szene ein Standbild-Kontaktbogen `tools\hive\art\eject\<id>_kontakt.png` (Hintergrund + Ebenen an ihren Startpositionen per PIL zusammengesetzt) ansehen (Read-Tool) und offensichtliche Fehler beheben.

Bericht: hoechstens 12 Zeilen: Szenen-ids mit Laenge, erzeugte Dateien (Anzahl), Annahmen, Dinge, die du selbst fuer schwach haeltst.
