# Polaris Express: Grafik fuer die Atlas-Zugkarte

Dieses Repo enthaelt alles, was fuer die 2D-Grafik der Karte **Polaris Express** (Unknown's Atlas, Among-Us-Mod)
gebraucht wird. Die Karte ist im Spiel bisher eine Graybox (flache Farbflaechen, keine Objekte). Gesucht ist die
echte Grafik im Among-Us-Stil, als **Python-Generator** `tools/train_art.py`, der aus den Kartendaten das Bodenbild,
die Objekt-Sprites, die Konsolen-Sprites, die Minimap und die Minispiel-Grafik erzeugt. Reproduzierbar, keine
Bilddateien von Hand.

## Auftrag in einem Satz

Schreibe `tools/train_art.py` so, dass `python tools/gen_train.py` statt der Graybox die fertige Grafik in
`assets/train/` schreibt: ein Nachtzug (Holzvertaefelung, Messing, Samt, Dampf, Schnee draussen) im Stil der
Among-Us-Karten, wie es Museum und Park in diesem Repo vormachen.

## Was die Karte ist

Lies zuerst `docs/TRAIN_KONZEPT.md` (Idee, Fahrzeuge, Raeume, Systeme, Sabotagen) und `docs/MAP_FORMAT.md`
(Kartendatei). Kurzfassung:

- Ein Nachtzug faehrt nach Osten, Grundriss von oben, Karte 62 x 17,6 m (`BOUNDS = (-31, -9, 31, 8.6)`),
  y nach Norden. Zeile 0 des Bodenbilds ist Norden.
- **Hauptebene** (Band A, y 1,0..5,5): sieben Fahrzeuge in einer Reihe, durch Faltenbaelge verbunden:
  Schlusswagen (Rear Platform, Conductor's Office), Schlafwagen unten (Luggage Room), Speisewagen (Dining Car),
  Aussichtswagen unten (Telegraph, Dynamo Room), Gepaeckwagen (Generator, Mail Room), Korridortender (Tender),
  Lok (Cab, Running Board).
- **Oberdeck** (Band B, y -7,0..-2,5): nur ueber den drei Doppelstockwagen, als eigener Grundriss suedlich der
  Wagen gezeichnet (eine Karte von oben kann keine Ebenen stapeln): Sleeper Car (zwei Abteile), Kitchen,
  Vista Dome. Treppen an beiden Wagenenden (Use-Knopf, Teleport), das Band ist auf der Karte als "UPPER DECK"
  beschriftet und per gestrichelten Linien den Wagen zugeordnet.
- Sabotage "Conductor's Round": zwei Fahrkarten-Lochzangen (Conductor's Office, Mail Room), Kartenknopf auf dem
  Gleisbett zwischen den Baendern.
- Alles Begehbare, alle Waende, Tueren, Konsolenlagen, Vents und Kameras stehen in `tools/gen_train.py`
  (Tabellen oben: CARS, ROOMS, GANGWAYS, VPARTS, HPARTS, VSOLID, STAIR_*, FIXED, VENTS, CAMERAS, OPAQUE, GLASS,
  TICKET). **Daran nichts aendern**: die Kollision ist festgelegt, die Grafik muss dazu passen.

## Vorlagen und Referenzen

| Was | Wo |
|---|---|
| Aktuelle Graybox der Karte (Draufsicht mit Konsolen gelb, Vents gruen, Kameras rot, Tueren blau, Treppen magenta) | `reference/preview.png`, `reference/preview_floor.jpg` |
| Fahrzeuge, Faltenbaelge, Treppen, Ebenen als Daten | `reference/layout.json` |
| 3D-Nachbau der Karte: Augenhoehe je Raum (so soll es innen aussehen: Einrichtung, Farben, Materialien) | `reference/3d/rooms_eye_level.jpg` |
| 3D-Nachbau: Draufsicht je Wagen (Stand Fassung 3, Raeume dort noch in alter Ebenenzuordnung, die Einrichtung je Raum gilt weiter) | `reference/3d/*_topdown.png` |
| Fertige Karte Park als Stilvorbild (Draufsicht klein, Bodenbild klein, Knoepfe) | `reference/park/` |
| Fertige Atlanten von Museum und Park (so sehen Objekt- und Konsolen-Sprites aus) | `assets/examples/*_props_*.png`, `*_consoles_0.png`, `*_minimap.png` |
| Minispiel-Grafik als Beispiel (Tafeln, Knopf, Karte, weisse Textur) | `assets/examples/task_*.png` |
| Zeichenbibliothek im Among-Us-Stil (Leinwand, Umrisse, Kacheln, Props in schraeger Aufsicht, Packer) | `tools/museum_art.py` (`Canvas`, `OpList`, `Prop`, `pack`), `tools/handdraw.py` |
| Fertige Generatoren zum Abschauen: Park (Boden, Objekte, Konsolen, Atlanten, map.json-Eintraege) | `tools/gen_park.py`, `tools/park_floor.py`, `tools/park_art.py`, `tools/park_decor.py` |
| Minispiel-Grafik-Generatoren (Museum, Park) | `tools/gen_tasks.py`, `tools/gen_park_tasks.py` |
| Das Minispiel der Lochzange (nutzt `task_wald_panel.png`; eigene Tafel per `taskArt`) | `src/AtlasMechanicsTicket.cs` |
| Alle Felder der Kartendefinition | `src/AtlasMapDef.cs` |

## Stilregeln (Among Us)

- Kraeftige, fast schwarze Umrisse (`OUTLINE`, etwa 6 cm = 10 px bei 160 px/m) um alles, was Kante ist.
- Flache Farbflaechen, eine helle Kante oben, eine dunkle unten, keine Verlaeufe, keine Fotos.
- **Schraege Aufsicht**: ein Objekt zeigt Deckflaeche plus Vorderseite (Suedseite). Eine Hoehe h (m) steht im
  Bild als `h * K` nach oben, `K = 0.55`. Die **Standlinie** (Unterkante der Vorderseite) ist die Kollision, sie
  gehoert genau auf die Kante aus `gen_train.py` (OPAQUE/GLASS-Rechtecke, Wandlinien).
- Waende: Wandkrone dunkel von oben; Nordwaende (die Wand noerdlich eines Raums) zeigen ihre Stirnseite in der
  Wandstaerke (`WALL = 0.4` m, Front 0,95 m sichtbar entspricht etwa 1,73 m Wandhoehe), alle anderen Waende nur
  die Krone. Aussen: Wagenkaesten mit abgeschnittenem Dach, Zierlinien, Puffer und Faltenbaelge, Nacht,
  Gleisbett, Schnee, Tannen am Rand (siehe Graybox `draw_ground`, `render_floor` in `gen_train.py`).
- Among Us legt die Nacht ueber das Sichtfeld, nicht ueber die Textur: Farben also eher kraeftig und hell
  (`museum_art.lift`), nicht duester.
- Lesbarkeit vor Detail: Spieler sind 1 m breit; Boeden ruhig (Holzdielen, Teppich, Riffelblech, Gitterrost),
  Objekte klar als Silhouette erkennbar, Konsolen deutlich als Geraete.

## Lieferumfang (Schnittstelle, in `gen_train.py` schon eingebaut)

`tools/train_art.py` mit einer Funktion `build(ctx) -> dict`. `ctx` liefert `gen_train.art_ctx(...)`:
`bounds`, `cars`, `rooms` (key, name, system, car, deck A/B, box), `walk` (shapely, begehbar), `room_geom`,
`decks`, `gangways`, `stairs` (Fussabdruecke main/upper, Absaetze a/b), `doors`, `vparts`, `hparts`, `vsolid`,
`boiler`, `opaque`, `glass`, `label_at`, `consoles` (Konsolen-Schluessel -> Lage), `vents`, `cameras`, `ticket`,
`spawn`, `emergency`, `surveillance`, `admin_table`, `freeplay`, `task_names`, `prop_ppm` (160), sowie die
Pixel-Helfer `P(x, y, s)` und `R(x0, y0, x1, y1, s)` und `geom_parts`.

Das Ergebnis-Dict:

| Schluessel | Inhalt |
|---|---|
| `floor` | PIL-Bild RGB, Groesse `(62 * floor_ppm, 17.6 * floor_ppm)`, deckt genau BOUNDS; gen_train schneidet es in Kacheln unter 2048 px |
| `floor_ppm` | Massstab des Bodenbilds, empfohlen 128 (wie Park) |
| `props_atlases` | Liste PIL-Bilder RGBA, je hoechstens 2048 x 2048 (`museum_art.pack`) |
| `props` | Liste Dicts nach `docs/MAP_FORMAT.md`: `kind`, `atlas`, `x`, `y`, `w`, `h` (Rechteck im Atlas, y von UNTEN wie in Unity), `worldX`, `worldY` (Weltlage der linken unteren Ecke des Sprites), `baseY` (Standlinie), `footX0`, `footX1` (Standflaeche in x). Jedes OPAQUE/GLASS-Rechteck aus gen_train braucht ein Prop, dazu die Lochzangen (`kind` "lochzange" an `ticket["stations"]`), Treppen, Sitze, Tische, Betten, Gepaeckkaefige, Herd, Telegraf, Dynamo, Generator, Sortiertisch, Kohlenhaufen, Kessel, Laternen und was die Raeume brauchen |
| `console_atlases`, `consoleSprites` | Atlanten und Eintraege (`key`, `atlas`, `x`, `y`, `w`, `h`, `pivotX`, `pivotY`) fuer ALLE Konsolen-Schluessel aus `ctx["consoles"]` (46 Stueck, Skeld-Schluessel wie `Cafeteria/DataConsole/2`); die Namen der Aufgaben stehen in `ctx["task_names"]` (z. B. UploadData = "Send a Telegram", also ein Telegraf, FuelEngines = "Shovel Coal") |
| `noFadeKinds` | Objektarten, die nie ausblenden (z. B. "kessel") |
| `minimap` | optional PIL RGBA, sonst bleibt die Graybox-Minimap |
| `files` | Dict Dateiname -> PIL-Bild fuer weitere Paketdateien: `button_train.png` (1000 x 250), `icon_train.png` (256 x 256), `task_train_panel.png` (Minispiel-Tafel, Holz und Messing, 100 px/m wie `task_wald_panel.png`), gern eine schoenere `task_ticket_button.png` (256 x 256, Fahrschein) und `task_stairs_button.png` |
| `taskArt` | Dict wie `AtlasMapDef.TaskArt`, z. B. `{"task_wald_panel.png": "task_train_panel.png"}` damit das Lochzangen-Minispiel die Zugtafel zeigt |
| `taskText` | optional, Texte im Minispiel |

Massstaebe: Props und Konsolen 160 px/m (`ctx["prop_ppm"]`), Boden 128 px/m. Umrissbreite 6 cm.

## Raeume (was hinein soll)

- **Rear Platform** (Shields): offene Plattform am Zugende, Gitterrost, Gelaender, rote Schlusslaternen (Shields-Konsole = Signallampen).
- **Conductor's Office** (Security): Schreibpult mit Monitoren (Ueberwachung), Fahrplan an der Wand, Lochzange.
- **Luggage Room** (Storage): zwei Gepaeckkaefige mit Gittertueren, Koffer, Kanister.
- **Dining Car** (Cafeteria, Start): Tische mit weissen Decken an beiden Fenstern, Bar, Notfallknopf (Glocke) in der Mitte, Speiseaufzug.
- **Telegraph** (Comms): Telegrafentisch, Morsetaste, Kabelbaum, Lampen. **Dynamo Room** (Electrical): Dynamo, Schalttafel, Sicherungen.
- **Generator** (UpperEngine): Maschinensatz an der Nordwand, Druckanzeigen. **Mail Room** (Admin): Sortierfaecher, Sortiertisch mit Streckenkarte (Admin-Tisch), Lochzange.
- **Tender** (LowerEngine): Gang an der Suedseite, Kohlenbunker mit zwei Luken, Kohlenhaufen.
- **Cab** (Reactor): Stehkessel mit zwei Ventilen, Hebel, Feuerloch. **Running Board**: Umlauf um den Kessel, Kessel mit Dampfdom und Schornstein, Laterne vorn.
- Oberdeck: **Sleeper Car** (MedBay): zwei Abteile mit Betten, Scanner im ersten Abteil (Fahrkartenkontrolle). **Kitchen** (LifeSupp): Herdzeile, Anrichte, Dunstabzug. **Vista Dome** (Nav): Sessel, Glaskuppel (Sterne), Karte und Steuerpult (Nav-Konsolen).

## Pruefen

1. `python tools/gen_train.py` muss durchlaufen (braucht PIL, shapely, numpy). Ergebnis in `assets/train/`,
   Vorschau mit allen Markierungen in `tools/_train/preview.png`, Bodenbild in `tools/_train/preview_floor.jpg`.
2. Sieh dir die Vorschau an (Bild oeffnen). Kein Prop darf begehbare Flaeche verdecken, ausser seine
   Standlinie liegt auf der Kollisionskante; Konsolen muessen an ihrer Lage als Geraet sichtbar sein.
3. Atlanten hoechstens 2048 px, Bodenkacheln unter 2048 px (macht gen_train), Dateigroesse im Rahmen von Park
   (Boden-JPGs zusammen unter 5 MB, Atlanten zusammen unter 6 MB).
4. Nichts an Kollision, Konsolenlagen oder Tabellen in `gen_train.py` aendern; wenn etwas nicht passt, im
   Abschlussbericht beschreiben.

## Abgabe

Alles in dieses Repo committen (Branch `main`): `tools/train_art.py` (und Hilfsmodule), die erzeugten Dateien in
`assets/train/`, die Vorschauen in `tools/_train/`. Abschlussbericht als `BERICHT.md`: was gebaut wurde, offene
Punkte, Vorschlaege. Keine Co-Authored-By- oder Session-Trailer in Commit-Messages.
