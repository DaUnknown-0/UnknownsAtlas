# Atlas-Kartenformat (map.json)

Seit 2026-10-17 kann eine Atlas-Karte eine Datei sein statt C#-Code. Atlas laedt sie zur Laufzeit
(`src/AtlasMapFile.cs`) und baut sie genauso wie Museum, Wald und Park (Relocate-in-Place auf der Skeld).

## Wo Atlas Karten findet

- **Ordner:** `BepInEx/plugins/AtlasMaps/<name>/map.json`, alle Dateien des Kartenpakets direkt daneben
  (keine Unterordner). Gut zum Entwickeln: Datei aendern, Spiel neu starten, fertig.
- **Eingebettet in Atlas:** Ressource `UnknownsAtlas.Maps.<key>.map.json`, das Paket als
  `UnknownsAtlas.Maps.<key>.<datei>`.

Beide erscheinen im Kartenwaehler (Freeplay und Lobby). Der Handshake vergleicht einen SHA-256 ueber
`map.json` und alle Paketdateien; der Host startet erst, wenn alle Spieler dieselbe Fassung haben.

## Kartenpaket (Dateinamen wie bei den eingebauten Karten)

| Datei | Inhalt |
|---|---|
| `<prefix>_floor_<i>.jpg` / `.png` / `.atx` | Bodenkacheln (`floorTiles[].index`); PNG mit Alpha, wenn darunter etwas liegt (`scroll`) |
| `<prefix>_props_<k>.png` / `.atx` | Objekt-Atlanten (`props[].atlas`) |
| `<prefix>_consoles_<k>.png` / `.atx` | Konsolen-Atlanten (`consoleSprites[].atlas`) |
| `<prefix>_minimap.png` | Minimap (oder `minimapFile`) |
| `button_<key>.png` | Freeplay-Logo 1000 x 250 (optional) |
| `icon_<key>.png` | Lobby-Symbol 256 x 256 (optional) |
| `task_*.png` | eigene Minispiel-Grafik, ueber `taskArt` zugeordnet |

`.atx` (vorkomprimiert, `tools/pack_textures.py`) laedt deutlich schneller als `.jpg`/`.png`.

## Felder

Alle Felder von `AtlasMapDef`, Namen in camelCase. Vektoren als `[x, y]` in Metern, Polygone als Liste
von Vektoren, Aufzaehlungen (`SystemTypes`, `TaskTypes`) als Namen.

| Feld | Bedeutung |
|---|---|
| `format` | Formatversion (1) |
| `key`, `displayName`, `resourcePrefix` | Schluessel, Anzeigename, Praefix der Paketdateien |
| `world` | Name einer eingebauten Welt-Mechanik (`AtlasMapFile.Worlds`), optional |
| `minX`..`maxY` | Kartengrenzen |
| `walls`, `shadowWalls`, `opaque`, `glass`, `hallways` | Kollision, Sichtschatten, Glas, Flure |
| `opaqueCastsShadow` | je `opaque`-Polygon: wirft Schatten |
| `rooms[]` | `key`, `name`, `room` (SystemTypes), `area` (Polygon) |
| `floorPixelsPerMeter`, `floorTiles[]` | `index`, `x`, `y`, `w`, `h` |
| `propPixelsPerMeter`, `props[]` | `kind`, `atlas`, `x`, `y`, `w`, `h`, `worldX`, `worldY`, `baseY`, `footX0`, `footX1` |
| `consoleSprites[]` | `key`, `atlas`, `x`, `y`, `w`, `h`, `pivotX`, `pivotY` |
| `noFadeKinds` | Objektarten, die nie ausblenden |
| `consoles` | Konsolen-Schluessel (Skeld-Konsole) -> Lage |
| `foreignTasks[]` | `type`, `ship` (Index in ShipPrefabs, 4 = Airship), `console`, `room` |
| `emergencyButton`, `surveillanceConsole`, `adminTable`, `freeplayLaptop`, `spawn`, `spawnRadius` | Systemkonsolen |
| `dummyRadius` | Halbachsen `[x, y]` der Ellipse, auf der die Freeplay-Dummies um den Spawn stehen (Standard `[3.6, 3.6]`) |
| `stairs[]` | Treppen zwischen Ebenen (`AtlasStairs`): `a`, `b` (Absaetze), `labelA`, `labelB` (Knopftext dort). Der Use-Knopf an `a` bringt einen nach `b` und umgekehrt, mit kurzer Blende |
| `runaway` | Sabotage "Runaway Train" (`AtlasRunaway`, ersetzt den Reaktor-Knopf): `seconds`, `button`, `brake`, `handbrake` |
| `smoke` | Sabotage "Smoke in the Cars" (`AtlasSmoke`, ersetzt den O2-Knopf): `seconds`, `button`, `source`, `hatches[]` |
| `scroll[]` | Bewegte Hintergrund-Ebenen der Welt-Mechanik `train`: `file`, `ppm`, `y0`, `y1`, `width_m`, `parallax` |
| `ticket` | Sabotage "Conductor's Round" (`AtlasTicket`): `seconds`, `button` (Kartenknopf), `stations` (Lochzangen). Fehlt das Feld, hat die Karte die Sabotage nicht |
| `levels[]` | Nur fuer 3D-Werkzeuge, Atlas liest es nicht: `name`, `z` (Bodenhoehe in m), `offset` `[dx, dy]` (so weit liegt die Flaeche im 3D vom Kartenbild entfernt), `areas` (Polygone), optional `ramp` `{axis, from, to, z0, z1}` fuer Stufen/Rampen |
| `vents` (Nr -> Lage), `ventNetworks`, `ventBridges` | Vents |
| `verticalDoors[]`, `horizontalDoors[]` | `label`, `x`, `y`, `length`, `group` (SystemTypes), `seeThrough` |
| `cameras`, `cameraViews` (Nr -> Blickpunkt) | Kameras |
| `mapButtons` (SystemTypes -> Lage), `mapLabels[]` | Minimap |
| `cameraColor` | `[r, g, b]` 0..1 |
| `minLight`, `maxLight` | Sichtweite |
| `treeSpots[]`, `viewSpots` | Sturmholz (Wald), Autotest-Fotos |
| `taskNames`, `customTasks`, `taskArt`, `taskText` | Aufgaben-Namen, Minispiel-Bausteine, Grafik, Texte |

## Mehrere Ebenen

Eine Karte von oben kann zwei Ebenen nicht uebereinander zeigen. Jede Ebene ist deshalb ein eigener Grundriss
auf der Karte (Polaris Express: Oberdecks suedlich der Wagen). Verbunden sind sie nur ueber `stairs`; ein Weg
durch die Flaeche zwischen zwei Ebenen waere im 3D-Nachbau ein Gang ins Nichts. `levels` sagt dem 3D-Nachbau,
auf welcher Hoehe und an welcher Stelle jede Flaeche wirklich liegt, damit er die Ebenen wieder stapeln kann.

## Pruefen

`Diagnostics.MapFileTest = true` (Atlas-Config) exportiert Museum, Wald und Park nach
`<Spiel>/AtlasShots/maps/<key>.map.json`, prueft den Rundlauf (schreiben, lesen, schreiben = gleich)
und meldet das Museum zusaetzlich aus seiner Datei als `museum_file` an. Erster Test 2026-10-17: alle drei
Rundlaeufe identisch, `museum_file` im Freeplay gebaut wie das Museum.
