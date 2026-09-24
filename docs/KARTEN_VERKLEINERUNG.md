# Karten verkleinern: Analyse aller Räume (Museum, Wald, Park)

Stand 2026-09-24. Reine Analyse, **noch nichts geändert**. Ziel: jede Karte bleibt in ihrem Stil
bestehen, ist aber für 10 Spieler gebaut und höchstens so groß wie **Polus**.

Messwerte aus `tools/*_layout.py` (Rasterweg 0,25 m, 0,3 m Wandabstand wie `wald_plan.py`),
Laufgeschwindigkeit 2,5 m/s. Polus/Skeld aus den Spieldaten des Impostor-Servers
(`Impostor.Api/Innersloth/Data/maps/*`) und den Raummitten aus TownOfHost; einige Raummitten sind
geschätzt, Laufzeiten dort ebenfalls (keine veröffentlichten Messungen).

## 1. Befund: die Karten sind nicht ein bisschen, sondern deutlich zu groß

| | Skeld | Polus | Museum | Wald | Park |
|---|---|---|---|---|---|
| Ausdehnung (m) | ≈ 41 × 20 | ≈ 40 × 26 | 61 × 43 | 64 × 44 | 74 × 50 |
| begehbare Fläche (m²) | – | – | 1719 | 2024 | 2279 |
| davon Wege/Gänge/Höfe | – | – | 125 (7 %) | 918 (45 %) | 605 (27 %) |
| Bereiche | 14 | ≈ 13–15 | 14 | 14 | 18 |
| Ø Raumfläche (m²) | ≈ 50 | ≈ 60 | 114 | 79 | 93 |
| Ø Abstand zweier Räume, Luftlinie (m) | 16,6 | 17,5 | 28,0 | 29,3 | 35,0 |
| größter Raumabstand, Luftlinie (m) | 37 | 38 | 55 | 57 | 75 |
| Ø Abstand zweier Räume, Laufweg (m) | – | – | 30,0 | 32,8 | 39,8 |
| weitester Punkt ab Spawn, Laufweg | ≈ 10–11 s | ≈ 16 s | 42 m / 17 s | 47 m / 19 s | 52 m / 21 s |
| größter Raumabstand, Laufweg | – | – | 63 m / 25 s | 66 m / 26 s | 83 m / 33 s |

Der aussagekräftigste Wert ist der mittlere Raumabstand (Luftlinie, direkt vergleichbar): Museum
1,6×, Wald 1,7×, Park 2,0× Polus. Um auf Polus zu kommen, muss jede Karte **linear** auf etwa
63 % (Museum), 60 % (Wald) bzw. 50 % (Park) schrumpfen, also auf 40 %, 35 % bzw. 25 % der Fläche.

**Ehrliche Einschätzung:** Räume rauswerfen allein reicht dafür nicht. Selbst wenn man je Karte drei
bis sechs Räume streicht, bleiben die übrigen doppelt so groß wie Skeld-Räume und die Wege zu lang.
Nötig sind drei Hebel zusammen:

1. **Räume streichen oder zusammenlegen** (Abschnitte 3–5)
2. **Räume verkleinern**: Zielgröße 40–90 m², nur der Treffpunkt (Spawn/Notfallknopf) und ein
   Wahrzeichen-Raum je Karte dürfen um 110 m² haben
3. **Leerraum raus**: tote Innenhöfe (Museum), Höfe und lange Waldwege (Wald), lange Promenaden
   und Aufgabenlose Plätze (Park)

### Zielwerte je Karte (Polus-Maß)

- Ausdehnung höchstens ≈ 44 × 30 m
- begehbar ≈ 850–1000 m²
- Ø Raumabstand Luftlinie ≤ 19 m, größter Raumabstand Laufweg ≤ 50 m (20 s)
- weitester Punkt ab Spawn ≤ 40 m (16 s); Security, Electrical und Admin nicht am Kartenrand
- 11–12 Räume mit Tasks, dazu höchstens zwei kleine Sonderbereiche

## 2. Technische Randbedingungen (gelten für alle drei Karten)

Die Karten sitzen per Relocate-in-Place auf der Skeld. Daraus folgt für jede Streichung:

- **Keine Konsole darf wegfallen.** Alle 60 Skeld-Konsolen (14 Systeme) müssen irgendwo stehen,
  sonst bekommt ein Spieler einen unerfüllbaren Task (siehe INSTALL_TESTPROTOKOLL, gewipte Konsole).
  "Raum löschen" heißt also immer: seine Konsolen **in einen Nachbarraum umziehen**.
- **Ortsangabe der Tasks:** die Taskliste zeigt `RoomNames[Console.Room]`. Zieht z. B. Weapons in
  die Rotunde, muss der Weapons-Typ dort eine eigene Teilfläche mit dem Namen der Rotunde bekommen
  (oder der Name wird umgebogen). Admin zeigt dann zwei Zähler für einen Raum: einer wird
  ausgeblendet oder beide liegen im Raum. TOR verlangt für jeden sichtbaren Zähler einen
  `FastRooms`-Eintrag (Park-Prototyp).
- **Türen:** 13 Skeld-Türen in 7 Gruppen, 7 senkrecht / 6 waagerecht. Bei weniger Räumen tragen
  einzelne Räume mehr Türen. Ob sich Türen parken lassen (statt verteilen), ist ungetestet.
- **Sabotage-Paare** (Reaktor-Hände, O2-Tastenfelder) brauchen weiterhin zwei getrennte Orte.
- Vents, Kameras, Minimap, Raumnamen und Boden werden ohnehin je Karte neu erzeugt.

## 3. Vesper Museum (14 → 11 Räume)

Aufbau heute: Foyer (Spawn) in der Mitte unten, Rotunde mit T.-Rex darüber, Ring aus Sälen außen
herum, Südgang zu Sicherheit und Depot. Größte Verschwendung: der **Lichthof** (13 × 11 m, nicht
begehbar) im Südwesten und der **Nordhof** im Nordosten. Beide nur Deko, sie schieben Sicherheit und
Haustechnik an den Rand (31 bzw. 38 m ab Spawn) und machen die Südgänge 12 m lang.

### Raum für Raum

| Raum (System) | Fläche | Zweck, warum hier? | Entscheidung |
|---|---|---|---|
| **Foyer** (Cafeteria) | 160 | Spawn, Notfallknopf, 3 Tasks; Drehscheibe zu Shop, Rotunde, Werkstatt | **Behalten, verkleinern** auf ≈ 120 m² inkl. Shop-Ecke |
| **Museum Shop** (Admin) | 124 | Kasse (Swipe), Upload, Wiring; nur Verbindungsstück zu den Südgängen, 7,5 m vom Foyer | **Zusammenlegen mit Foyer.** Museumsshops liegen im Foyer; Kassentresen und Regal kommen in die Foyer-Ecke. Die Südgänge entfallen |
| **Rotunde** (O2) | 140 | Wahrzeichen (T.-Rex), 3 Tasks, Knoten zwischen allen Achsen | **Behalten**, ≈ 110 m², nimmt die Tresorvitrine auf |
| **Mineral Cabinet** (Shields) | 113 | nur 2 Konsolen (Tresorvitrine, Divert) in 113 m²; eigentlich nur Durchgang Planetarium ↔ Telefon | **Streichen.** Tresorvitrine + Divert in die Rotunde (Nordnische). Das Glasvitrinen-Thema lebt in Rotunde und Ägypten weiter |
| **Gallery** (Weapons) | 108 | Motten-Task, Download, Divert, Stellwände als Sichtbrecher | **Behalten**, ≈ 65 m², zwei statt vier Stellwände |
| **Egyptian Hall** (Reactor) | 113 | Grabschloss, Hieroglyphen; stärkstes Ausstellungsthema | **Behalten**, ≈ 70 m² |
| **Planetarium** (Nav) | 112 | 5 Konsolen (Sternbild, Projektor, Download, Divert, Wiring) | **Behalten**, ≈ 65 m² |
| **Switchboard** (Comms) | 67 | Comms-Sabotage (CCTV) + 2 Tasks | **Behalten**, ≈ 45 m² |
| **Machine Hall** (Upper Engine) | 175 | Dampfmaschine, Schwungrad, Oldtimer, Turbine; größter Raum der Karte | **Behalten, stark verkleinern** auf ≈ 85 m²: Oldtimer oder Turbine raus (beide ohne Task) |
| **Restoration** (MedBay) | 120 | Scan, Probe | **Behalten**, ≈ 60 m² |
| **Loading Dock** (Lower Engine) | 142 | Align/Fuel am Lieferwagen, Alarm A2, Rampe mit zwei Ebenen | **Zusammenlegen mit Depot** zu "Depot & Loading Dock": beides Hinterbühne/Logistik. Rampe (kleiner) bleibt als Stil-Element |
| **Depot** (Storage) | 110 | Kanister, Wiring, Müllschacht, Löschgas G2 | **Behalten** als Teil des zusammengelegten Raums (≈ 90 m² zusammen) |
| **Security Office** (Security) | 51 | Kameras **und** Admin-Tisch, Alarm A1 | **Behalten**, aber **nach innen** direkt westlich ans Foyer (heute 31 m, Ziel ≤ 15 m) |
| **Utilities** (Electrical) | 59 | Licht-Sabotage + 4 Tasks + Löschgas G1 | **Behalten**, neben Security (heute 38 m, weitester Raum der Karte; Ziel ≤ 20 m) |
| Lichthof, Nordhof (Deko) | – | nur Bild, nicht begehbar | **Streichen** |

Ergebnis-Skizze (nicht maßstäblich):

```
 [Planetarium]---[   Rotunde    ]---[Switchboard]
       |          T.-Rex, Tresor          |
 [Egyptian]--[Gallery]    |       [Machine Hall]--[Depot & Dock]
       |                  |             |               |
 [Utilities]-[Security]-[Foyer + Shop]-[Restoration]----+
```

Schätzung: ≈ 800 m² Räume + ≈ 60 m² Gänge, Ausdehnung ≈ 44 × 28 m. Sabotagen: Alarm A1 (Security)
und A2 (Dock) bleiben weit auseinander, Löschgas G1 (Utilities) und G2 (Depot) ebenso.

### Durchsicht: jedes Objekt

Regel: Wer über ein Objekt hinwegsehen kann (Tisch-, Theken-, Brusthöhe) oder durch es hindurch
(Glas, Gitter, Stelzen, Speichen), bekommt **GLASS** (sperrt nur den Weg). Alles über Kopfhöhe und
geschlossen (Säule, Schrank, Fahrzeug, Maschine, Wand) bleibt **OPAQUE**.

| Objekt | heute | Entscheidung | Begründung |
|---|---|---|---|
| Infotheke (Foyer) | OPAQUE | **→ GLASS** | runde Theke, Tischhöhe; genau das Beispiel aus der Aufgabe |
| Kassenhäuschen (Foyer) | OPAQUE | OPAQUE | Häuschen mit Dach |
| Deko-Treppe (Foyer) | OPAQUE | OPAQUE | steigt über Kopfhöhe an |
| Garderobe | OPAQUE | OPAQUE | Mäntel auf Kopfhöhe, liegt an der Wand |
| Kassentresen (Shop) | OPAQUE | **→ GLASS** | Theke |
| Cafétresen (Shop) | OPAQUE | **→ GLASS** | Theke |
| Wandregal, Regal-Insel (Shop) | OPAQUE | OPAQUE | Regale über Augenhöhe |
| Monitorwand, Spind (Security) | OPAQUE | OPAQUE | an der Wand, hoch |
| Schaltschränke, Kessel (Utilities) | OPAQUE | OPAQUE | hoch und geschlossen |
| Klimagerät (Utilities) | OPAQUE | **→ GLASS** | Bild zeigt eine Außeneinheit mit Lüfter oben (≈ 1 m); steht mitten im 59-m²-Raum und erzeugt dort grundlos einen toten Winkel |
| Sarkophage (Ägypten) | OPAQUE | OPAQUE | stehen aufrecht, Mannshöhe |
| Stele (Ägypten) | OPAQUE | **→ GLASS** | Bild: kleine Tafel auf niedrigem Sockel |
| Sphinx-Fragment (Ägypten) | OPAQUE | **→ GLASS** | Bruchstück auf flachem Podest |
| Stellwände (Galerie) | OPAQUE | OPAQUE | Ausstellungswände, bewusst Sichtbrecher |
| Projektor (Planetarium) | OPAQUE | OPAQUE | hohes Gerät, kleiner Fuß, kleiner Schatten |
| Vermittlungsschrank, Funkregal (Switchboard) | OPAQUE | OPAQUE | an der Wand, hoch |
| Stützen (Machine Hall) | OPAQUE | OPAQUE | Säulen, wie in der Aufgabe beschrieben |
| Dampfmaschine, Turbine, Oldtimer | OPAQUE | OPAQUE | große Maschinen/Fahrzeug über Kopfhöhe |
| Schwungrad (Machine Hall) | OPAQUE | **→ GLASS** | Bild: Speichenrad liegend auf einer Säule in Hüfthöhe |
| Werktische (Restoration) | OPAQUE | **→ GLASS** | Tische |
| Regal (Restoration), Hochregale (Depot) | OPAQUE | OPAQUE | hohe Regale |
| Kisten (Depot) | OPAQUE | **→ GLASS** | einzelne Kiste, Brusthöhe (nicht gestapelt) |
| CO2-Flaschen (Depot) | OPAQUE | OPAQUE | stehende Flaschen, an der Wand |
| Lieferwagen (Hof) | OPAQUE | OPAQUE | Fahrzeug |
| Fässer (Hof) | OPAQUE | **→ GLASS** | ≈ 1 m hoch |
| T.-Rex-Sockel, Vitrinen, Tischvitrinen, Tresorvitrine, Bänke, Cafétische, Pflanzentrog, Gebäudeplan-Tisch, Vermittlungstisch, Glastrennwand, Restaurierungstisch | GLASS | GLASS | Glas oder Tischhöhe, stimmt so |

## 4. Forest Station (14 → 12 Bereiche)

Das Problem des Waldes sind weniger die Räume als der Raum **zwischen** ihnen: 918 m² (45 %) sind
3,2 m breite Wege und 2,2–3 m breite Höfe um jedes Gebäude. Die Gebäude selbst (42–96 m²) haben
schon fast Zielgröße; die Lichtungen (75–127 m²) sind zu groß.

### Raum für Raum

| Bereich (System) | Fläche | Zweck, warum hier? | Entscheidung |
|---|---|---|---|
| **Mess Hall** (Cafeteria) | 80 | Spawn, Notfallglocke, 3 Tasks, 3 Türen | **Behalten** |
| **Field Station** (Admin) | 56 | Admin-Kartentisch, Stempeluhr, Upload, Wiring | **Behalten**, direkt neben der Messe |
| **Field Lab** (MedBay) | 64 | Scan, Probe, O2-Feld B1 | **Behalten** |
| **Sawmill** (Upper Engine) | 84 | Säge, Tanken, Divert | **Behalten**, ≈ 70 m² |
| **Storehouse** (Storage) | 96 | Kanister, Wiring, Kompost; 3 Türen | **Behalten**, ≈ 80 m² |
| **Boathouse** (Lower Engine) | 56 | Außenborder, Tanken, Divert | **Behalten, übernimmt Creek Dock** |
| **Creek Dock** (Shields) | 75 | Laternen (Shields), Divert, O2-Feld B2; Bach und Steg | **Zusammenlegen mit Boathouse**: Steg und Bach werden der Vorplatz des Bootshauses. Wasser-Thema bleibt, eine Lichtung fällt weg |
| **Ranger Office** (Security) | 49 | Kameras | **Behalten**, näher an die Messe (heute 37 m, weitester Raum) |
| **Generator Shed** (Electrical) | 42 | Licht-Sabotage + 4 Tasks | **Behalten** |
| **Lookout Rock** (Nav) | 107 | 5 Nav-Konsolen, Reaktor-Hand A2, Fels und Aussichtsturm | **Behalten** (Wahrzeichen), ≈ 70 m² |
| **Radio Mast** (Comms) | 96 | Comms-Sabotage, Download, Divert | **Behalten**, ≈ 60 m² |
| **Water Tower** (O2) | 127 | Ansauggitter, Divert, Kompost, Reaktor-Hand A1 | **Behalten, übernimmt Pump Station** als "Water Works" |
| **Pump Station** (Reactor) | 87 | nur 2 Tasks (Pumpe, Ventile), Pumpenhaus | **Zusammenlegen mit Water Tower**: Pumpe und Wasserturm gehören sachlich zusammen |
| **Hunting Stand** (Weapons) | 87 | Wildzählung, Download, Divert; nahe der Messe | **Behalten**, ≈ 60 m² |

Dazu, wichtiger als jede Streichung:
- **Höfe** um die Gebäude auf ≈ 1 m vor den Eingängen kürzen (der Park hat sie schon ganz gestrichen)
- **Wege** höchstens ≈ 4 m lang und 2,8 m breit; heute bis 9 m (Messe → Lager, Bootshaus → Hochsitz)
- der dichte Wald als Wand bleibt; der Stil hängt an den Blockhütten und Lichtungen, nicht an der Weglänge

Ergebnis-Skizze:

```
 [Lookout Rock]--[Sawmill]--[Radio Mast]--[Water Works]
       |             |            |              |
 [Field Lab]--[Field Station]-[Mess Hall]-[Hunting Stand]
       |                         |               |
 [Ranger Office]-[Generator]-[Storehouse]-[Boathouse + Steg]
```

Schätzung: ≈ 750 m² Bereiche + ≈ 200 m² Wege, Ausdehnung ≈ 44 × 30 m. Reaktor-Hände A1 (Water
Works) und A2 (Lookout) liegen an entgegengesetzten Enden, O2 B1 (Lab) und B2 (Bootshaus-Steg) ebenso.

### Durchsicht: jedes Objekt

| Objekt | heute | Entscheidung | Begründung |
|---|---|---|---|
| Regal (Field Station), Schrank (Lab) | OPAQUE | OPAQUE | hoch, an der Wand |
| Kisten (Storehouse) | OPAQUE | OPAQUE | gestapelte Kistenregale |
| Monitore (Ranger Office) | OPAQUE | OPAQUE | an der Wand |
| Aggregat (Generator) | OPAQUE | **→ GLASS** | niedriges Stromaggregat, Brusthöhe |
| Fels (Lookout) | OPAQUE | OPAQUE | großer Findling, über Kopfhöhe |
| Aussichtsturm (Lookout) | OPAQUE | **→ GLASS** | steht auf Stelzen, man sieht zwischen den Beinen durch; der Weg bleibt gesperrt |
| Hochsitz (Hunting Stand) | OPAQUE | **→ GLASS** | ebenfalls Stelzen |
| Funkmast (Radio Mast) | OPAQUE | **→ GLASS** | Gittermast |
| Wassertank (Water Tower) | OPAQUE | **→ GLASS** | Tank steht erhöht auf Beinen |
| Pumpenhaus | OPAQUE | OPAQUE | kleines Gebäude |
| Einzelbäume | OPAQUE | OPAQUE, aber **nur der Stamm** (Schatten-Radius ≈ 0,3 statt 0,8 m) | der Stamm ist eine Säule, unter der Krone sieht man durch |
| langer Tisch, Herd, Bänke, Laborbank, Sägetisch, Kartentisch, Boot, Lagerfeuer, Baumstämme | GLASS | GLASS | Tisch-/Sitzhöhe, stimmt so |
| Holzstapel (Sawmill) | GLASS | GLASS (knapp) | Schulterhöhe; ein Crewmate sieht gerade noch drüber |

## 5. Moonlight Carnival (18 → 12 Räume + 2 Durchgänge)

Der Park ist die größte Karte (doppelt Polus), obwohl die Konzeptvorgabe "größer als das Museum"
lautete. Die Größe kommt aus drei Stellen: vier Attraktionen ohne Tasks (380 m²), drei übergroße
Plätze (Fairground, Ferris Wheel, Coaster Station je 166–192 m²) und die lange Promenade von West
nach Ost. Leitsatz für den Umbau: **Attraktionen ohne Tasks werden Durchgänge mit Mechanik, keine
Plätze.**

### Raum für Raum

| Raum (System) | Fläche | Zweck, warum hier? | Entscheidung |
|---|---|---|---|
| **Fairground** (Cafeteria) | 192 | Spawn, Notfallknopf, 3 Tasks, 3 Buden | **Behalten**, ≈ 110 m², übernimmt die Drehkreuze |
| **Main Gate** (Attraktion) | 76 | keine Tasks; Drehkreuze (Einbahn), Vent; Sackgasse im Süden, 42 m ab Spawn | **Streichen als Raum.** Die Drehkreuz-Reihe wird zum Südausgang des Fairground (Einbahn hinein/hinaus + normaler Umweg bleibt Pflicht). Mechanik und Turnstile Jam bleiben erhalten |
| **Hall of Mirrors** (Attraktion) | 99 | keine Tasks, kein Welt-Ereignis, nur Glaswand-Labyrinth; Nordwestecke, 41 m ab Spawn | **Streichen.** Trägt keine Mechanik, bläht die Ecke auf |
| **Ghost Train** (Attraktion) | 104 | keine Tasks; Ghost Flash mit Foto-Monitor (einzige Info-Mechanik des Parks) | **Behalten als Tunnel-Durchgang** (≈ 3 m breit, Zickzack) zwischen Carousel und Workshop, Monitor am Ausgang, Raumname bleibt |
| **Log Flume** (Attraktion) | 101 | keine Tasks; Kanal mit zwei Brücken, Log Flume Drop | **Behalten als Kanal-Durchgang** (≈ 30 m²) zwischen zwei Räumen, eine Brücke sperrt beim Bootssturz, die andere bleibt |
| **Carousel** (Upper Engine) | 110 | Tasks + Carousel Spin | **Behalten**, ≈ 80 m² |
| **Bumper Cars** (Lower Engine) | 90 | Tasks, Arena | **Behalten** |
| **Workshop** (Storage) | 81 | Kanister, Wiring, Müll; 3 Türen; heute 40 m ab Spawn | **Behalten**, näher heran |
| **Shooting Gallery** (Weapons) | 80 | Schießbude-Task | **Behalten** |
| **Ferris Wheel** (Nav) | 166 | 5 Nav-Konsolen, Riesenrad | **Behalten**, ≈ 80 m² (Rad bleibt, Platz darum schrumpft) |
| **Coaster Station** (Reactor) | 166 | Bremshebel (Reaktor-Paar), 2 Tasks | **Behalten**, ≈ 90 m² |
| **Light Tower** (Shields) | 97 | nur 2 Konsolen (Scheinwerfer, Divert) | **Zusammenlegen mit Music Booth** zu "Show Control" (Licht und Ton); der Turm steht im Hof des Musikhauses |
| **Music Booth** (Comms) | 64 | Comms-Sabotage, 2 Tasks | **Behalten**, übernimmt den Lichtturm |
| **Park Office** (Admin) | 72 | Admin-Tisch, O2-Feld 2 | **Behalten, übernimmt Security Booth** als Nebenraum mit Monitorwand (Admin-Tisch und Kameras an entgegengesetzten Enden, wie im Museum schon Admin + Kameras in einem Raum) |
| **Security Booth** (Security) | 42 | Kameras | **Zusammenlegen mit Park Office** (liegen heute 11 m auseinander) |
| **Substation** (Electrical) | 24 | Licht-Sabotage + 4 Tasks; Sackgasse, 46 m ab Spawn (!) | **Behalten, zentral legen** (Ziel ≤ 20 m) |
| **First Aid Tent** (MedBay) | 50 | Scan, Probe; Sackgasse, 44 m ab Spawn | **Behalten**, näher heran |
| **Cold Store** (O2) | 60 | 3 Tasks, O2-Feld 1 | **Behalten** |

Achterbahn: die Schleife umschließt heute Light Tower und Music Booth (27 × 17 m). Nach dem
Zusammenlegen umschließt sie nur noch "Show Control" und wird entsprechend kürzer; zwei statt drei
Bahnübergänge reichen.

Ergebnis-Skizze:

```
 [Shooting Gallery]--[Ferris Wheel]==X==[Show Control]      X = Bahnübergang
        |                  |                 X
 [Carousel]--------[ FAIRGROUND ]------[Coaster Station]
     |                |  Drehkreuze         |
 ~Ghost Train~   [Park Office+Security]  ~Log Flume~
     |                |                     |
 [Workshop]-[Bumper Cars]-[Substation]-[Cold Store]-[First Aid]
```

Schätzung: ≈ 900 m² Räume + ≈ 70 m² Durchgänge + ≈ 100 m² Wege, Ausdehnung ≈ 46 × 30 m. Das ist
knapp über dem Ziel; wenn es im Test zu groß wirkt, ist der nächste Kandidat das Zusammenlegen von
Cold Store und First Aid Tent (beide im Südosten).

### Durchsicht: jedes Objekt

| Objekt | heute | Entscheidung | Begründung |
|---|---|---|---|
| Buden (Fairground) | OPAQUE | OPAQUE | Bude mit Dach |
| Tunnelwände (Ghost Train) | OPAQUE | OPAQUE | Wände |
| Riesenrad-Nabe | OPAQUE | **→ GLASS** | Bild: niedriges Podest, das Rad selbst ist Speichen |
| Beleuchtungsturm | OPAQUE | **→ GLASS** | Gitterturm auf flachem Sockel |
| Karussell | OPAQUE (ganze Scheibe, Ø 5,6 m) | **aufteilen**: Weg gesperrt auf ganzer Scheibe, Sicht nur am Mittelgehäuse (Ø ≈ 1,6 m) | Dach über Kopfhöhe, Pferde und Stangen sind dünn; nur der Kern ist geschlossen. Heute ein riesiger toter Winkel mitten im Raum |
| Kassenhaus (Coaster), Kassenhäuschen (Main Gate) | OPAQUE | OPAQUE | Häuschen |
| Kühltruhe (Cold Store) | OPAQUE | **→ GLASS** | Eistruhe, Hüfthöhe |
| Regal (Workshop) | OPAQUE | OPAQUE | hohes Regal |
| Lautsprecher (Music Booth) | OPAQUE | OPAQUE | Boxenturm über Kopfhöhe |
| Radkranz Riesenrad, Theke, Autoscooter-Arena, Zaun, Mischpult, Liege, Schiene, Wasser | GLASS | GLASS | stimmt so |
| Spiegel (Hall of Mirrors) | GLASS | entfällt mit dem Raum | falls er doch bleibt: echte Spiegel sind undurchsichtig, dann **OPAQUE** oder in "Glass Maze" umbenennen |

## 6. Zusammenfassung

| Karte | Räume heute → neu | gestrichen / zusammengelegt | Durchsicht geändert |
|---|---|---|---|
| Museum | 14 → 11 | Shop → Foyer, Mineral Cabinet → Rotunde, Loading Dock + Depot; Licht- und Nordhof weg | 10 Objekte → GLASS |
| Wald | 14 → 12 | Creek Dock → Boathouse, Pump Station → Water Tower; Höfe und Wege kürzen | 5 Objekte → GLASS, Bäume nur Stamm |
| Park | 18 → 12 + 2 Durchgänge | Hall of Mirrors weg, Main Gate → Fairground, Light Tower → Music Booth, Security → Park Office; Ghost Train und Log Flume als Durchgänge | 3 Objekte → GLASS, Karussell geteilt |

Reihenfolge für den Umbau (Vorschlag): Museum zuerst (am nächsten am Ziel, einfachster
Grundriss), dann Wald (vor allem Wege/Höfe), dann Park (größter Umbau). Je Karte zuerst Graybox mit
`*_plan.py` nachrechnen und erst dann die Grafik neu erzeugen.
