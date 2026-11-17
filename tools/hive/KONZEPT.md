# Amberhive (Atlas-Karte, Auftrag 15.11.2026)

Auftrag (User 15.11.): neue Atlas-Karte, komplett eigene Idee, kreativ, keiner bestehenden aehnlich; hoechste Qualitaet,
durchdachtes Raumlayout, Groesse Skeld bis hoechstens Polus; Assets in Blender (selbst) oder per Opus-Subagent (effort high),
GPT-Referenzbilder erlaubt; alles Bewegte animiert; Rauswurf- und Skip-Animation in Blender; mindestens 2 Unikate;
mindestens 2 Etagen, die der Host zuschaltet; Sabotagen frei waehlbar; am Ende spielgetestet
vorfuehren.

## Idee

Eine Imkerei-Forschungsstation, in einen riesigen, lebenden Bienenstock hineingewachsen. Die Crew traegt Imkerkluft,
Bienen so gross wie ein Crewmate-Kopf summen durch die Gaenge. Warmes Bernsteinlicht faellt durch Wachswaende,
Honig fliesst in Rinnen, im Zentrum liegt der Honigbrunnen. Farben: Bernstein/Gold, Wachscreme, dunkles Propolisbraun
als Umriss, Moosgruen als Akzent, Abendhimmel durch die Kronenoeffnung.

Kein Vorbild unter den Karten (Skeld, Mira, Polus, Airship, Fungle, Museum, Forest, Carnival, Polaris,
und weitere Atlas-Karten).

## Raeume (Skeld-Systeme)

| Raum | System | Inhalt |
|---|---|---|
| Mead Hall | Cafeteria | Speisesaal, Koeniginnenglocke (Notfall), Spawn |
| Honey Well | Flur | Honigbrunnen mit Drehbruecke (Unikat 1) |
| Keeper's Office | Admin | Imkerbuero, Wabenkarte (Admin-Tisch), O2-Tastatur 2 |
| Jar Cellar | Storage | Honiglager, Glasregale |
| Lamphouse | Electrical | Gluehonig-Laternen (Licht-Sabotage) |
| Bellows | LifeSupp | Bienenfaecher-Geblaese (O2-Sabotage) |
| Queen's Chamber | Reactor | Thron der Koenigin (Reaktor = "Hive Fever") |
| Wax Foundry | Shields | Wachsgiesserei |
| Brood Nursery | MedBay | Brutwaben-Wiegen, Scanner |
| Guard Comb | Security | Wachstube, Kameras |
| Waggle Studio | Comms | Schwaenzeltanz-Buehne (Funk = "Dance Jam") |
| West Press / East Press | LowerEngine / UpperEngine | Nektarpressen |
| Wasp Watch | Weapons | Wespenwache (Asteroiden = Wespen) |
| Sun Compass | Nav | Sonnenkompass |
| Crown (nur 2 Etagen) | Nav/Weapons/Admin | Kronen-Etage: Sun Deck, Drone Dock, Royal Archive |

## Unikate

1. **Drehbruecke im Honigbrunnen**: eine Bruecke ueber dem Honigsee dreht sich (Host-Takt, alle Clients), verbindet
   abwechselnd Nord-Sued und West-Ost; waehrend der Drehung gesperrt.
2. **Honigflut**: in Abstaenden laeuft Honig in einen von vier Gaengen (Host waehlt), wer drin steht, wird langsamer;
   danach versickert er (Animation).
3. **Nektarrutsche** (nur 2 Etagen): Einbahn-Rutsche von der Krone hinunter in den Brunnenring.
4. Umgebung: fliegende Bienen, Honigtropfen, pumpende Blasebaelge, drehende Pressen, flackernde Wachskerzen.

## Etagen

Option "Amberhive Floors" (1 Floor / 2 Floors). Erdgeschoss in beiden Fassungen gleich; mit 2 Etagen kommt die Krone
(nordlich auf der Kartenflaeche) dazu, mit Treppen (AtlasStairs) und der Rutsche; einige Konsolen wandern nach oben.

## Sabotagen

Vanilla-Satz umgestaltet: Hive Fever (Reaktor, zwei Kuehlwaben im Thronsaal), Stale Air (O2, Bellows + Buero),
Glow Fade (Licht, Lamphouse), Dance Jam (Funk, Waggle Studio), Wabenschotten als Tueren (animiert).

## Animationen

Tueren (Wabenschott auf/zu), Vents (Wabengitter), Kameras, Bienen, Requisiten; Rauswurf: Bienenschwarm traegt den
Crewmate durch die Kronenoeffnung in den Abendhimmel; Skip: die Koenigin gaehnt, Honig tropft, niemand geht.

## Stand 15.11. nachmittags (Arbeitsprotokoll)

- Grundriss fertig (hive_layout.py): 14 Raeume Erdgeschoss (795 m2), Krone 3 Raeume (zusammen 959 m2), 7V/6H Tueren,
  11 Vents in 4 Netzen, 4 Kameras; asymmetrisch (Waggle Studio Sackgasse, Thronsaal 4 Zugaenge). Einrichtung in PROPS.
- Krone hat eigene Systeme (Records, ViewingDeck, CargoBay) und 6 Airship-Aufgaben (CROWN_TASKS, AtlasForeignTasks);
  Erdgeschoss in beiden Fassungen identisch (alle 46 Skeld-Konsolen).
- Generator: `python gen_hive.py build --art` (Blender-Boden ueber floor_geo.py + blender/floor_build.py, 100 px/m,
  weicher Wandschatten), Objekte/Konsolen aus art/ (art_pack.py), Laufzeitbilder art/fx (fx_geo.py + blender/fx_build.py),
  Logo/Symbol art/brand (blender/brand_build.py). Stil: blender/hive_style.py (Scherung K=0,59, flache Schattierung, Freestyle).
- Code: src/AtlasAmberhive.cs (Anmeldung, Option 1729 + Diagnostics.AmberhiveFloorsTest, Welt: Drehbruecke, Honigflut mit
  Verlangsamung, Rutsche, Objekt-Animationen, Bienen, Autotest TaskTest=hive), Netz AtlasWorld Op 24.
- Test: tools/hive/maptest.sh amberhive hive 45 mit EXTRA="Diagnostics.AmberhiveFloorsTest=1 Diagnostics.MapShot=false".
- Assets: Opus-Agent A (31 Requisiten -> art/props), Opus-Agent B (Konsolen, Tueren, Vents, Kameras -> art/consoles).
- Offen: Rauswurf- und Skip-Szenen (Agent C, eject_scenes.py, map "amberhive", Bilder task_eject_hive_*),
  Mehrspieler-Test (DuoTest), Minimap im Stil, Vorfuehrung.

## Stand 15.11. ~14:00

- Alle Grafiken der Karte fertig und eingebaut: 31 Requisiten (5 animiert), 34 Konsolen, 13 Tueren x 6 Bilder, Vent (6),
  Kamera (2), Bruecke, 4 Honiglachen, Bienen, Knoepfe, Logo. preview_hive.py setzt die Karte offline zusammen.
- Freeplay-Tests gruen (1 und 2 Etagen, keine Exceptions): Flut bremst auf 60 %, Rutsche landet am Ausgang, Bruecke
  dreht, Tueren animiert, Airship-Aufgaben der Krone laden (6 von 6, ~0,85 s).
- Zwei-Client-Test (DuoTest, plans/rounds_hive.txt, Lauf hive1): Host und Gast mit identischer Brueckenphase und
  Flutzone, Option 1729 kommt beim Gast an, Meeting und Rundenende ok.
- Offen: Rauswurf/Skip (Agent C laeuft), danach Szenen im Spiel pruefen (TaskTest eject:N / ejectskip:N), Vorfuehrung.

## Stand 15.11. ~14:30

- Rauswurf/Skip fertig (Agent C, Opus): hive_swarm (7,0 s), hive_well (7,2 s), hive_skip_queen (6,8 s), hive_skip_sundeck (6,6 s);
  33 Bilder task_eject_hive_* in assets/amberhive, Skripte blender/eject_*.py, Kontaktboegen art/eject/*_kontakt.png.
  Die Bilder werden zusaetzlich als UnknownsAtlas.Resources.* eingebettet (csproj), weil EjectEngine dort sucht.
- Aufnahme-Modi fuer die Vorfuehrung: TaskTest=hiveclip (Bruecke mit fester Kamera, Flut, Rundgang 14 Raeume, Krone, Rutsche)
  und eject:N:clip / ejectskip:N:clip (150 Bilder). Beide setzen Time.captureFramerate = 20, damit Screenshots die Zeit nicht
  verzerren. Ablauf: _show/eject_runs.sh, Videos per ffmpeg in _show/pub.
- Vorfuehrungsseite: _show/pub/amberhive.html (Artefakt), Bilder/Videos daneben.
- Vor einem Release: Boden/Objekte/Szenenbilder ins Asset-Repo auslagern (wie train), Minimap im Wabenstil pruefen.
- 15.11. abends: Szenen im Spiel geprueft (alle vier laden, Spieler/Text ok), Rundgang aller 17 Raeume, Vorfuehrung
  veroeffentlicht (Artefakt). Nektarpressen auf "glass" (offenes Gestell, blockiert Bewegung, nicht Sicht).
  ACHTUNG: gen_hive.py build ohne --art ueberschreibt die Boeden mit Graubau; immer mit --art bauen.

## Stand 15.11. spaet: drei Grafikfassungen

- A Opus (erste Fassung): _backup_v1 (art, blender, assets_amberhive). Vorfuehrung alter Account.
- B Fable (4 Fable-Agents, ca. 13,8 Mio. Einheiten): _variants/v2_fable, AKTIVER Stand in art/ und assets. Stil in art/STIL_V2.md.
  Vorfuehrung: https://claude.ai/artifact/NC8AcQHxzPT2chJZMjNnHL
- C GPT (22 ChatGPT-Blaetter aus B, hive_gpt.py refs/apply): _gpt/gpt_NN.png, eingesetzt in _variants/v3_gpt (props, consoles, eject).
  Boden, fx und die 19 Brueckenbilder bleiben aus B. Einspielen: Ordner nach art/ bzw. assets/amberhive kopieren, gen_hive --art.
- Vergleich mit Auswahl je Abschnitt (db-Sammlung "wahl"): https://claude.ai/artifact/QeeeXAPo5dvrP4woEkNVhz
