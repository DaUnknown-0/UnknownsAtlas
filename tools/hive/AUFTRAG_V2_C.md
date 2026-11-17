Harte Regeln: Starte KEINE Subagents und KEINE Forks (kein Agent-Tool, kein Workflow). Starte nicht Among Us und keinen Browser, kein git. Keine Gedankenstriche (:) in Texten/Kommentaren. Alles in Blender (headless), keine Bild-KI.

Basisordner: `D:\programmieren\2025\Amogus\Tracker V2\Tracker\Mod stuff\TOR Mod\UnknownsAtlas\` (Pfade unten relativ dazu)

Ziel: Die vier Rauswurf- und Skip-Szenen der Among-Us-Karte "Amberhive" (Imkerei-Station in einem Bienenstock) im NEUEN Stil der Karte neu gestalten und in Blender neu rendern, mit sichtbar hoeherer Qualitaet. Den Stil hat bereits jemand festgelegt und die Karte damit neu gemacht; die Szenen sind Seitenansichten (Kino), sollen aber erkennbar aus derselben Welt stammen.

Die Szenen gibt es schon (ids, Ablauf und Laenge duerfen bleiben oder besser werden):
- `hive_swarm` (Rauswurf): Bienen heben den Crewmate im Kronensaal hoch und tragen ihn durch die runde Oeffnung in den Abendhimmel.
- `hive_well` (Rauswurf): Querschnitt des Honigbrunnens, Drehbruecke dreht weg, er rutscht ab, versinkt im Honig, letzte Blase ploppt. Schwach: die Bruecke "dreht" sich nur, indem sie schmaler wird; Simse flach, Honigstrahl duenn.
- `hive_skip_queen` (Skip): Bienenkoenigin gaehnt auf dem Thron, winkt ab, schlaeft ein.
- `hive_skip_sundeck` (Skip): Biene landet auf einer Bluete, nippt, Tropfen faellt. Schwach: recht schlicht, wirkt nicht wie ein Deck auf einem Bienenstock.

Lies zuerst (sonst nur, was du wirklich brauchst):
- `tools\hive\art\STIL_V2.md` (der neue Stil, verbindlich) und die dort genannten Beispielbilder
- `tools\eject_scenes.py` Zeilen 1-60 (Format, Hilfsfunktionen) und die Szenen mit "map": "amberhive" (suche nach `hive_`), Zeilen 1040 bis Ende (lint/main)
- `tools\hive\blender\eject_common.py` und die vier `tools\hive\blender\eject_*.py`, `tools\hive\blender\eject_kontakt.py`
- `tools\hive\art\eject\*_kontakt.png` (so sehen die Szenen jetzt aus)

Darfst schreiben: `tools\hive\blender\eject_*.py`, `tools\hive\art\eject\`, `assets\amberhive\task_eject_hive_*` (ersetzen, neue mit diesem Praefix anlegen, nicht mehr benutzte loeschen), in `tools\eject_scenes.py` NUR die Szenen mit "map": "amberhive". `hive_style.py` nur importieren.
Nicht aendern: alles andere (andere Szenen, Karte, Konsolen, `src\`, csproj).

Kontext:
- Blender: `C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe -b --factory-startup -P <skript> -- <args>`.
- Szenen-Einheiten: 1 Einheit = 180 px; Hintergrund fuer bounds [12, 6.8] = 2160 x 1224 px (JPG). Ebenen als PNG mit Alpha. Der Crewmate wird von der Engine gezeichnet (Objekt "player", ca. 1 Einheit hoch, Mitte als Anker); Skip-Szenen haben keinen Spieler.
- Bildnamen MUESSEN mit `task_eject_hive_` beginnen und in `assets\amberhive\` liegen (das Projekt bettet sie unter dem Namen ein, den die Engine sucht). Allgemeine Bilder duerfen mitbenutzt werden: task_eject_glow.png, task_eject_px.png, task_eject_puff.png, task_eject_mote.png, task_eject_droplet.png, task_eject_vignette.png.
- Klaenge nur aus: boom chime clack click creak fire grind growl organ owl pop roar rush sizzle slam splash step thud thunder twig whoosh zap.
- Alles, was sich bewegt, braucht Bewegung (Keys, wobble, flicker, Emitter). Bienenfluegel schlagen.
- Danach `python tools\eject_scenes.py` ausfuehren (muss ohne Fehler durchlaufen, schreibt assets\eject_scenes.json).

Pruefe einmal: je Szene einen Kontaktbogen mit drei Zeitpunkten (`eject_kontakt.py`) ansehen (Read-Tool) und offensichtliche Fehler beheben.

Bericht: hoechstens 12 Zeilen: Szenen-ids mit Laenge, erzeugte Dateien (Anzahl), Annahmen, was du selbst fuer schwach haeltst.
