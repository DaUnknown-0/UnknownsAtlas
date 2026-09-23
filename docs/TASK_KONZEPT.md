# Eigene Tasks für die Atlas-Karten (Konzept)

Stand 2026-09-23. Gilt für das Vesper-Museum und die Forststation Nadelkamm (Wald v6).

Entschieden (User, 2026-09-23):
- **Deutlich mehr eigene Mechaniken:** fast jeder Task bekommt ein eigenes Minispiel (Stufe B).
  Reskins (Stufe A) nur dort, wo die Vanilla-Mechanik schon perfekt zur Fiktion passt oder
  der Task am Spieler sichtbar abläuft.
- **Dauer:** jedes eigene Minispiel dauert etwa so lange wie sein Skeld-Gegenstück (±20 %),
  damit Task-Balance und TOR-Zeitoptionen stimmen.

## Ausgangslage

Beide Karten entstehen per Relocate-in-Place aus der Skeld. Jede Konsole behält ihren
Skeld-Task. Neu sind bisher nur die Task-Blöcke in der Welt (`museum_consoles.py`,
`wald_consoles.py`) und die Raumnamen. Öffnet man eine Konsole, erscheint trotzdem das
Skeld-Minispiel: Asteroiden im Museum, Reaktor-Simon im Wald. Das ist der letzte große Bruch
mit der Fiktion der Karten.

Ziel: Jede Karte bekommt **eigene Task-Namen und eigene Minispiele**, ohne eigenen Netzcode
und ohne die Task-Verteilung anzufassen.

## Leitregeln

1. **Huckepack statt neuer TaskTypes.** Jeder Karten-Task reitet auf genau einem Skeld-Task:
   gleiche `TaskTypes`, gleiche Kategorie (Common/Short/Long), gleiche Schrittzahl und
   Konsolenkette. Verteilung, `RpcSetTasks`, `RpcCompleteTask`, Taskbalken und der
   server-autoritative Crew-Taskwin bleiben vanilla.
2. **Nur das Minispiel wird getauscht.** Name (Taskliste) und `MinigamePrefab` ändern sich,
   sonst nichts. Das Minispiel schließt den Schritt über `MyNormTask.NextStep()` ab, genau wie
   ein Vanilla-Minispiel. Mehrschrittige Tasks bekommen je Schritt einen eigenen Zustand.
3. **Zwei Ausbaustufen.**
   - **A, Reskin:** Vanilla-Minispiel, neue Grafik. Kopie des Skeld-Prefabs unter einem
     inaktiven Halter, Sprites getauscht.
   - **B, Eigene Mechanik:** eigenes `Minigame` per `ClassInjector`, prozedural aufgebautes
     Prefab, zusammengesetzt aus gemeinsamen Mechanik-Bausteinen (siehe unten).
4. **Visuelle Tasks bleiben Beweise.** Clear Asteroids, Prime Shields, Submit Scan und Empty
   Garbage haben Effekte, die andere Spieler sehen. Der Karten-Task liefert dafür einen
   passenden Welt-Effekt, damit die Beweiskraft erhalten bleibt.
5. **Namen englisch im Spiel**, wie die Raumnamen ("Museum Shop", "Ranger Office").
   Übersetzung später über UTS-Loc.

## Mechanik-Bausteine

Damit 30 eigene Minispiele nicht 30 Einzelcodes werden, setzt sich jedes B-Minispiel aus
wenigen wiederverwendbaren Bausteinen zusammen. Jeder Baustein bekommt genau einen
AutoPilot-Solver.

| Baustein | Eingabe | Genutzt von |
|---|---|---|
| **Rubbeln** | Wischen über eine Maske, Fortschritt = freigelegter Anteil | Dust the Skeleton |
| **Drehen** | Kreisbewegung um einen Mittelpunkt, Winkel rastet ein | Tomb Lock, Focus the Dome Projector, Open the Valves, Splice Field Cable (Schrauben), Focus the Binoculars |
| **Band halten** | Wert driftet, Eingabe stößt zurück, Ziel = Zeit im grünen Band | Stabilise Climate Control, Align the Flywheel, Align the Saw Blade / Trim the Outboard, Prime the Pump, Tune the Generator (Choke) |
| **Befüllen** | Halten öffnet, Loslassen stoppt, Ziel = Füllstrich ohne Überlauf | Stoke the Steam Engine, Refuel the Machines |
| **Pfad ziehen** | Punkt entlang einer Linie ziehen, Verlassen = zurück zum letzten Wegpunkt | Trace a Constellation, Plot the Patrol Route |
| **Klickziele** | bewegte Ziele treffen, Fehlziele vermeiden | Chase the Moths, Wildlife Census |
| **Zuordnen** | Objekte in Fächer ziehen oder Kabel zu Buchsen | Close Out the Till, Empty the Bins, Haul the Compost, Restore Exhibit Power, Route Generator Power, Repair Showcase Lighting |
| **Auswählen** | das eine abweichende Element unter mehreren finden, optional nach Timer | Pigment Analysis, Water Sample Analysis, Collect Trail Cam Footage, Sync the Audio Guide, Hieroglyph Sequence, Punch the Time Card |

Hinzu kommen zwei Sondermechaniken ohne eigenen Baustein: **Laserspiegel** (Arm the Vault
Showcase) und **Streichholz im Wind** (Light the Dock Lanterns).

## Museum: Vesper-Museum

Fiktion: Nachtschicht nach Museumsschluss. Die Crew ist Wachpersonal und Haustechnik.

| Skeld-Task (Kategorie, Schritte) | Museumstask | Räume | Stufe | Mechanik |
|---|---|---|---|---|
| Fix Wiring (Common, 3) | **Repair Showcase Lighting** | Foyer, Museum Shop, Security Office, Utilities, Planetarium, Depot | B | Lichtleiter-Weiche: 3x3-Feld aus Leiterstücken drehen, bis der Lichtstrahl alle drei Vitrinenspots erreicht. Jeder Schritt ein anderes Feld. |
| Swipe Card (Common, 1) | **Close Out the Till** | Museum Shop | B | Kassensturz: Der Bon zeigt einen Betrag, Münzen und Scheine in die Schale ziehen, bis die Summe stimmt. Zu viel öffnet die Rückgeld-Klappe, neu zählen. |
| Calibrate Distributor (Short, 1) | **Stabilise Climate Control** | Utilities | B | Drei driftende Regler (Temperatur, Feuchte, Lux) gleichzeitig 3 s im grünen Band halten. Werte driften weg, ein Klick stößt zurück. Nach Probelauf entschärft: Band 28 % der Skala, langsame Drift (halb so schnell im Band), Fortschritt verfällt beim Verlassen langsam statt sofort. |
| Chart Course (Short, 1) | **Trace a Constellation** | Planetarium | B | Eine Sternkarten-Tafel zeigt ein Sternbild. Am Kuppelhimmel (mit mehr Sternen) die passenden Sterne der Reihe nach verbinden, ohne die Linie abzusetzen. |
| Clean O2 Filter (Short, 1) | **Dust the Skeleton** | Rotunda | B | Staubschicht vom Dinosaurierskelett wegwischen. Fertig bei 95 % freigelegter Fläche, die Knochen glänzen kurz auf. |
| Divert Power (Short, 2) | **Restore Exhibit Power** | Utilities, dann Gallery, Planetarium, Mineral Cabinet, Switchboard, Machine Hall, Loading Dock, Rotunda oder Security Office | B | Schritt 1: im Sicherungskasten die durchgebrannte (dunkle) Sicherung finden und eine neue einsetzen. Schritt 2: Saalschalter umlegen, Lampen glimmen nach und nach auf. |
| Prime Shields (Short, 1, visuell) | **Arm the Vault Showcase** | Mineral Cabinet | B | Zwei Spiegel drehen, bis der Laser alle vier Empfänger der Tresorvitrine trifft. Welt-Effekt: das Laserraster leuchtet rot auf. |
| Stabilize Steering (Short, 1) | **Focus the Dome Projector** | Planetarium | B | Zwei Fokusringe (grob, fein) drehen, bis der Sternenhimmel scharf ist; eine Schärfeanzeige hilft. |
| Unlock Manifolds (Short, 1) | **Hieroglyph Sequence** | Egyptian Hall | B | Zehn Kartuschen in der Reihenfolge einer kleinen Legende drücken (Symbol statt Zahl). Falscher Druck setzt zurück. |
| Upload Data (Short, 2) | **Sync the Audio Guide** | Säle (Download), dann Museum Shop (Upload am Audioguide-Verleih) | B | Schritt 1: von drei Audiospuren die zum Saal passende wählen (Schild zeigt das Exponat), dann lädt sie. Schritt 2: Geräte in die Ladestation stecken, Übertragung läuft. |
| Align Engine Output (Long, 2) | **Align the Flywheel** | Machine Hall, Loading Dock | B | Fliehkraftregler: Hebel stellen, die Drehzahlnadel folgt träge; 3 s im Band halten. |
| Clear Asteroids (Long, 1, visuell) | **Chase the Moths** | Gallery | B | Motten flattern unstet vor den Gemälden. Mit der Taschenlampe (Cursor) anlocken und ins Fangglas ziehen, 12 Motten. Welt-Effekt: die Galerie-Spots flackern bei jedem Fang. |
| Empty Garbage (Long, 2, visuell) | **Empty the Bins** | Foyer oder Rotunda, dann Depot | B | Schritt 1: Abfall aus dem Besuchereimer in Papier, Glas, Rest sortieren. Schritt 2: Hebel am Depotcontainer halten. Welt-Effekt: der Container an der Laderampe schüttelt. |
| Fuel Engines (Long, 4) | **Stoke the Steam Engine** | Depot, Machine Hall, Depot, Loading Dock | B | Schritte 1 und 3: Wasserkanne am Hahn bis zum Strich füllen, Überlauf heißt neu. Schritte 2 und 4: in den Kessel gießen, bis das Schauglas grün zeigt. |
| Inspect Sample (Long, 1) | **Pigment Analysis** | Restoration | B | Fünf Farbproben einlegen, 60 s warten (Timer bleibt), dann die Probe wählen, deren Spektrallinie von der Referenz abweicht. |
| Start Reactor (Long, 1) | **Tomb Lock** | Egyptian Hall | B | Drei konzentrische Hieroglyphenringe drehen, bis das Schlüsselsymbol der Grabkammer in allen Ringen oben steht. Jeder Ring dreht einen Nachbarn ein Stück mit. |
| Submit Scan (Long, 1, visuell) | **Authenticity X-Ray** | Restoration | A | Im Röntgenrahmen stehen. Bleibt vanilla, weil der Scan am Spieler sichtbar abläuft. |

## Wald: Forststation Nadelkamm

Fiktion: Forst- und Rangerstation in der Nacht. Die Crew ist Stationspersonal.

| Skeld-Task (Kategorie, Schritte) | Waldtask | Bereiche | Stufe | Mechanik |
|---|---|---|---|---|
| Fix Wiring (Common, 3) | **Splice Field Cable** | Field Station, Mess Hall, Generator Shed, Lookout Rock, Ranger Office, Storehouse | B | Drei Adern an die farbgleichen Klemmen legen und jede Klemmschraube mit einer Kreisbewegung festdrehen. |
| Swipe Card (Common, 1) | **Punch the Time Card** | Field Station | B | Die eigene Karte aus dem Stempelkartenhalter ziehen (Name = Spielername) und den Hebel drücken, wenn der Minutenzeiger auf der vollen Stunde steht. |
| Calibrate Distributor (Short, 1) | **Tune the Generator** | Generator Shed | B | Choke in das grüne Feld stellen, dann am Seilzug ziehen (schnell nach unten). Springt nach 2 bis 3 Zügen an, bei falschem Choke säuft er ab. |
| Chart Course (Short, 1) | **Plot the Patrol Route** | Lookout Rock | B | Auf der Wanderkarte die Route vom Aussichtsfels über alle Wegmarken ziehen, ohne den Weg zu verlassen. |
| Clean O2 Filter (Short, 1) | **Clear the Intake Grate** | Water Tower | A | Laub und Zweige vom Ansauggitter in den Eimer ziehen. Bleibt Reskin, weil die Vanilla-Mechanik genau das schon ist. |
| Divert Power (Short, 2) | **Route Generator Power** | Generator Shed, dann Sawmill, Boathouse, Ranger Office, Lookout Rock, Radio Mast, Water Tower, Hunting Stand oder Creek Dock | B | Schritt 1: am Verteiler das Kabel mit dem Bereichsschild in die freie Buchse stecken. Schritt 2: Kippschalter am Verteilerkasten des Bereichs. |
| Prime Shields (Short, 1, visuell) | **Light the Dock Lanterns** | Creek Dock | B | Laterne öffnen, Streichholz anreißen (Wischgeste), ins Glas halten, schließen, bevor der Wind (Anzeige) das Streichholz ausbläst. Vier Laternen. Welt-Effekt: die Steglaternen glühen auf. |
| Stabilize Steering (Short, 1) | **Focus the Binoculars** | Lookout Rock | B | Fernglas über das Panorama schwenken, bis der Hirsch im Kreis steht, dann das Fokusrad drehen, bis er scharf ist. |
| Unlock Manifolds (Short, 1) | **Open the Valves** | Pump Station | B | Fünf Ventilräder in der Reihenfolge der Nummernschilder mit einer Kreisbewegung aufdrehen. Falsches Rad lässt Dampf ab und setzt zurück. |
| Upload Data (Short, 2) | **Collect Trail Cam Footage** | Radio Mast, Lookout Rock, Hunting Stand oder Generator Shed (SD-Karte holen), dann Field Station | B | Schritt 1: aus sechs Wildkamera-Fotos das eine mit einem Tier markieren, dann kopiert die Karte. Schritt 2: SD-Karte in den Stationsrechner stecken, Upload läuft. |
| Align Engine Output (Long, 2) | **Align the Saw Blade** / **Trim the Outboard** | Sawmill, Boathouse | B | Sägewerk: Anschlag verstellen, bis die Markierung am Stamm auf dem Sägeblatt liegt. Bootshaus: Trimmwinkel des Motors, bis die Bugwelle ruhig ist. Beides Band halten mit träger Anzeige. |
| Clear Asteroids (Long, 1, visuell) | **Wildlife Census** | Hunting Stand | B | Durchs Fernglas Rehe und Wildschweine zählen, die über die Lichtung laufen. Eulen nicht anklicken: ein Fehlklick setzt 2 Treffer zurück. Welt-Effekt: der Zählkasten am Hochsitz blinkt. |
| Empty Garbage (Long, 2, visuell) | **Haul the Compost** | Mess Hall oder Water Tower, dann Storehouse | B | Schritt 1: Küchenreste in den Kompost, Verpackung in den Sack sortieren. Schritt 2: Hebel an der Komposttonne halten. Welt-Effekt: die Tonne am Lager wackelt. |
| Fuel Engines (Long, 4) | **Refuel the Machines** | Storehouse, Sawmill, Storehouse, Boathouse | B | Schritte 1 und 3: Kanister am Fass bis zum Strich füllen. Schritte 2 und 4: mit dem Trichter tanken, bis das Schauglas voll ist. Gleicher Baustein wie Stoke the Steam Engine. |
| Inspect Sample (Long, 1) | **Water Sample Analysis** | Field Lab | B | Teststreifen in fünf Wasserproben tauchen, 60 s warten (Timer bleibt), dann den Streifen wählen, dessen Farbe nicht zur Trinkwasser-Skala passt. |
| Start Reactor (Long, 1) | **Prime the Pump** | Pump Station | B | Pumpenschwengel im Takt ziehen: der Druckbalken steigt nur bei gleichmäßigem Rhythmus, zu schnell heißt Überdruck und der Balken fällt zurück. Drei Stufen bis zum Anlaufen. |
| Submit Scan (Long, 1, visuell) | **Tick Check** | Field Lab | A | Auf der Untersuchungsplatte stehen. Bleibt vanilla, weil der Scan am Spieler sichtbar abläuft. |

Bilanz: Museum 16 von 17 Tasks mit eigener Mechanik, Wald 15 von 17.

## Technik

### Wo der Tausch greift

Nicht an den Prefabs in `ShipStatus.CommonTasks/ShortTasks/LongTasks` ansetzen. Das sind
Assets (vergleiche die `MapPrefab`-Falle): eine Änderung dort sickert in die nächste
Vanilla-Skeld-Runde.

Stattdessen an den **Task-Instanzen** jedes Spielers: nachdem `RpcSetTasks` bzw.
`PlayerControl.SetTasks` die Tasks angelegt hat, liegen in `myTasks` geklonte
`NormalPlayerTask`-Objekte. Dort `MinigamePrefab` auf das Karten-Prefab setzen. Rein lokal,
jede Runde neu, keine Rückwirkung auf die Skeld.

- Hook: Postfix auf `PlayerControl.SetTasks` (bzw. dessen Coroutine-Ende); zusätzlich ein
  günstiger Abgleich einmal pro Sekunde, weil andere Mods Tasks nachträglich ersetzen
  (UC Auditor per `RpcSetTasks` + Re-Complete, Role Control, Colorblind-Heiltask).
- Gate: nur wenn `UnknownsAtlas.ActiveMap` gesetzt ist.
- Keine Detours auf kleine Il2Cpp-Methoden wie `Minigame.Close(bool)` (Dedup-Falle). Das
  eigene Minispiel ruft `Close()` nur auf, es patcht nichts.

### Karten-Prefabs

- Einmal pro Karte beim Bau erzeugen, unter einem inaktiven Halter (`AtlasTaskPrefabs`).
- **Stufe A:** `Object.Instantiate(skeldMinigamePrefab, halter)`, dann die `SpriteRenderer`
  nach einer Tabelle `Pfad im Prefab -> Sprite-Key` umbelegen.
- **Stufe B:** eine Klasse `AtlasMinigame : Minigame` per `ClassInjector`. Sie liest aus einer
  Datentabelle (`AtlasTaskDef`: TaskTypes, Schritt, Baustein, Parameter, Sprite-Keys) und baut
  den passenden Baustein auf. Eingabe über `Controller` wie die Vanilla-Minispiele. Abschluss:
  `MyNormTask.NextStep()`, Erfolgs-Sound, `StartCoroutine(CoStartClose())`.
- Grafik aus Python-Generatoren (`tools/museum_tasks.py`, `tools/wald_tasks.py`) in eigene
  Atlanten `*_tasks_*.png`, wie bei den Konsolen-Blöcken; Vorschau `tools/preview_tasks.py`.
- Esc und X schließen wie vanilla; Teilfortschritt eines Schritts verfällt.
- Mehrschrittige Tasks (Fix Wiring 3, Divert Power 2, Upload Data 2, Align 2, Empty Garbage 2,
  Fuel 4) wählen den Zustand über `MyNormTask.taskStep`.

### Dauer (±20 %)

Jeder B-Task bekommt eine Solldauer aus seinem Skeld-Gegenstück. Parameter (Driftstärke,
Anzahl Ziele, Füllgeschwindigkeit) stehen in `AtlasTaskDef`, damit Balance ohne Codeänderung
nachgezogen werden kann. Ein Diagnose-Schalter loggt pro Minispiel die tatsächliche Dauer
(`[Atlas/Task] <name> step <n> <sekunden>`), Abnahme im Freeplay gegen die Skeld-Werte.

### Namen

`TranslationController.GetString(TaskTypes)` per Postfix, kartengesteuert, analog zum
schon bestehenden `SystemTypes`-Postfix. Bei geteilten Typen mit zwei Motiven (Align im Wald)
entscheidet der Raum der nächsten Konsole.

### Visuelle Effekte

Die Skeld-Effekte hängen an Objekten, die beim Relocate umgezogen oder geparkt werden
(Waffen-Animation, Schild-Lichter, Müllschacht). Für jeden visuellen Task prüft
`inspect_live.py`, ob der Effekt noch ausgelöst wird, und das Karten-Objekt (Laserraster,
Galerie-Spots, Container, Laternen, Zählkasten) hört auf dasselbe Signal.

### Wechselwirkungen mit anderen Mods

- **TOR/UC-Rollen, die Tasks sehen oder beeinflussen** (Snitch, Auditor, Colorblind): arbeiten
  auf TaskTypes und Task-Ids, bleiben unberührt.
- **AutoPilot:** braucht je Mechanik-Baustein einen Solver (8 Stück plus 2 Sondermechaniken),
  nicht je Task.
- **Online:** alle Spieler haben Atlas ohnehin (die Karte wird clientseitig gebaut).
  Ein Spieler, bei dem der Tausch nicht greift, sieht das Skeld-Minispiel und kann den Task
  trotzdem normal abschließen. Kein Desync-Risiko.

## Reihenfolge

1. **Namen:** `TaskTypes`-Postfix für beide Karten. Klein, sofort sichtbar in Taskliste und
   Karten-Overlay.
2. **Gerüst + zwei Prototypen:** `AtlasMinigame`, `AtlasTaskDef`, Instanz-Tausch,
   Dauer-Logging. Prototypen *Dust the Skeleton* (Rubbeln) und *Prime the Pump* (Band halten).
3. **Bausteine nacheinander**, jeweils mit allen Tasks, die ihn nutzen: Zuordnen, Drehen,
   Befüllen, Pfad ziehen, Klickziele, Auswählen. Nach jedem Baustein Freeplay-Abnahme beider
   Karten.
4. **Sondermechaniken:** Laserspiegel, Streichholz im Wind.
5. **Stufe A:** Clear the Intake Grate, Authenticity X-Ray, Tick Check.
6. **Welt-Effekte der visuellen Tasks.**
7. **AutoPilot-Solver** je Baustein.
8. Später: Aufgaben ohne Skeld-Gegenstück (z. B. *Water the Café Plants* aus dem
   Museum-Konzept). Das ginge nur über Prefabs anderer Karten (Polus/Airship per
   `AmongUsClient.ShipPrefabs` nachladen, wie LevelImposter) und bleibt bis dahin offen.

## Offene Punkte

- Konsolen-Räume bleiben wie gebaut. Themen folgen der Konsole, nicht umgekehrt
  (Bilderrahmen ausrichten wäre schön in der Galerie, dort steht aber keine Align-Konsole).
- Soundeffekte je Baustein: aus der bestehenden AssetGen-Pipeline oder neu.
