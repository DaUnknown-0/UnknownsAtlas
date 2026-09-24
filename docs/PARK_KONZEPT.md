# Atlas-Karte 3: Freizeitpark nach Ladenschluss (Konzept)

Name **Moonlight Carnival**. Stand 2026-09-23, Entwurf zur Abstimmung. Dritte Karte von Unknown's
Atlas, gebaut wie Museum und Wald per Relocate-in-Place aus der Skeld.

## Entscheidungen (2026-09-23)

- **Thema:** Freizeitpark nach Ladenschluss, Ton **heiter-gruselig**: bunter Rummel bei Nacht,
  Lichterketten, schiefe Musik, Pappfiguren. Unheimlich, aber nicht düster.
- **Größe:** **größer als das Museum.**
- **Bereiche:** 18, nämlich die 14 Skeld-Räume plus **vier Attraktionen**: Geisterbahn,
  Spiegelkabinett, Wildwasserbahn, Haupteingang.
- **Name:** Moonlight Carnival.
- **Drehkreuze:** echter **Einbahnweg** am Haupteingang (siehe Welt-System).
- **Blitzfoto der Geisterbahn:** nur am **Ausgangsmonitor** sichtbar; wer es sehen will, muss hin.
- **Menschenkanone:** nur Kulisse und Rauswurf-Szene, **kein** Transportmittel.
- **Grafik:** mit hohem Anspruch, von mir selbst (kein Subagent): gleiche Pipeline wie Museum, Wald und
  Rauswurf-Szenen, Bildabnahme im Spiel. User: "Gib dir viel Mühe beim Erstellen der Grafik".

## Achse: Ablenkung und wechselnde Wege

Jede Atlas-Karte hat eine eigene Spielachse:

| Karte | Achse | Träger |
|---|---|---|
| Vesper Museum | Überwachung und Information | Kameras, Laserprotokoll, Alarm |
| Forest Station | Sicht und Natur | Wetter, Nebel, Waldbrand, Sturmholz |
| **Moonlight Carnival** | **Ablenkung und wechselnde Wege** | Fahrgeschäfte springen an, sperren kurz Wege, lenken den Blick |

Among Us hat keine Schrittgeräusche. "Lärm" ist deshalb nur Stimmung; die Mechanik dahinter ist
**Ablenkung** (Bewegung, Licht, Musik ziehen den Blick) und **kurzes Sperren** (Schranken,
Drehkreuze, Karussell). Wer die Fahrpläne kennt, plant seine Wege; ein Impostor plant seinen Kill.

## Die Fiktion

Der Park hat geschlossen, morgen ist Saisoneröffnung. Die Crew ist die Nachtschicht: Techniker und
Security, die jedes Fahrgeschäft für den Morgen durchprüfen. Die Anlagen laufen zu Testzwecken von
selbst an, und nicht alle Pappfiguren stehen dort, wo sie abends standen.

## Bereiche (18)

Namen im Spiel englisch, wie bei Museum und Wald.

| Skeld-Raum | Bereich (im Spiel) | Rolle |
|---|---|---|
| Cafeteria | **Fairground** (Festplatz mit Buden) | Notfallknopf, Spawn, Mitte der Karte |
| Admin | **Park Office** (Verwaltung, Kassenhaus) | Admin-Tisch (Lageplan), O2-Tastenfeld 2 |
| Security | **Security Booth** | Kameras |
| Electrical | **Substation** (Umspannhaus) | Licht-Sabotage, Strom-Tasks |
| Reactor | **Coaster Station** (Achterbahn-Bahnhof) | kritische Sabotage, Achterbahn-Tasks |
| O2 | **Cold Store** (Kühlhaus der Imbissbuden) | kritische Sabotage |
| Comms | **Music Booth** (Musik- und Durchsagezentrale) | Comms-Sabotage |
| Navigation | **Ferris Wheel** (Riesenrad mit Steuerhaus) | Tasks |
| Weapons | **Shooting Gallery** (Schießbude) | visueller Task |
| Shields | **Light Tower** (Beleuchtungsturm) | visueller Task |
| MedBay | **First Aid Tent** (Sanitätszelt) | Scan, Proben |
| Storage | **Workshop** (Werkstatt und Lager) | Tasks, Müll |
| Upper Engine | **Carousel** (Karussell mit Antrieb) | Tasks, Fahrgeschäft |
| Lower Engine | **Bumper Cars** (Autoscooter-Halle) | Tasks |
| neu | **Ghost Train** (Geisterbahn) | dunkler Tunnel, Blitzfoto |
| neu | **Hall of Mirrors** (Spiegelkabinett) | Glaswände: Sicht ja, Durchgang nein |
| neu | **Log Flume** (Wildwasserbahn) | Kanal mit Brücken, Boote als Ereignis |
| neu | **Main Gate** (Haupteingang) | Portal, Drehkreuze |

Die vier Attraktionen tragen **keine Tasks**, dort spielt das Welt-System. Das hält die Tasks bei
den 14 Skeld-Räumen, deren Konsolen es gibt.

### Zusätzliche Räume: was technisch dazugehört (Prototyp zuerst)

Museum und Wald nutzen genau die 14 Skeld-Räume. Echte zusätzliche Räume (eigener Name in der
Standortanzeige, eigener Zähler auf dem Admin-Tisch) sind neu und werden **vor** dem Grundriss auf der
Museum-Graybox erprobt:

1. freie `SystemTypes`-Werte wählen (das Enum kennt die Räume aller Karten, etwa Kitchen, Lounge,
   Greenhouse, Laboratory); Namen über den vorhandenen `GetString(SystemTypes)`-Postfix
2. je Raum ein `PlainShipRoom` mit Fläche anlegen und in `ShipStatus.AllRooms` und `FastRooms` eintragen
   (Standortanzeige, Sichtsystem)
3. Admin-Tisch: je Raum einen `CounterArea` klonen und platzieren
4. prüfen, was sonst über die Räume läuft (Kameras, Sabotage-Karte, TOR-Rollen mit Raumbezug wie
   Tracker/Detective, UC-Rollen mit Raumbezug, Forgotten Fixes)

Klappt einer der Punkte nicht, fällt der betroffene Bereich auf "Kulisse" zurück: eigene Optik, aber
Standortanzeige und Admin zählen ihn zum Nachbarraum.

**Prototyp bestanden (2026-09-23, Autotest `TaskTest extraroom`, AtlasRoomDiag.cs):** im Museum wurde
ein Gang zu einem Raum vom Typ `Kitchen` ("Test Room"), den die Skeld nicht kennt.
- Standortanzeige: zeigt "Test Room" (Namen kommen jetzt aus `AtlasMuseumBuilder.RoomNames`, das jeden
  Raum-Typ kennt, nicht nur die 14 Skeld-Räume)
- Admin-Tisch: ein geklonter `CounterArea` sitzt an der Raummitte und zählt den Dummy darin (1)
- TOR: dessen Admin-Zählung läuft ohne Fehler, weil der Raum auch in `FastRooms` steht. Das ist
  Pflicht: TOR liest `FastRooms[RoomType]` für jeden Zähler, ein Zähler ohne Raum-Eintrag würde bei
  jedem Update werfen und den ganzen Admin-Tisch lahmlegen.
- Noch offen: der Raumname im Minimap-Bild (kommt bei der Parkkarte aus der Grafik-Pipeline) und ein
  Blick auf Rollen mit Raumbezug in einer echten Runde.

Umsetzung für den Park damit: Zusatzräume sind einfach weitere `Rooms`-Einträge mit einem freien
`SystemTypes`-Wert; Raum, Name, Mitte und Admin-Zähler entstehen automatisch.

### Topologie (Skizze, nicht maßstäblich)

```
                 [Ferris Wheel]        [Light Tower]
                       |                    |
 [Hall of Mirrors]--[Shooting Gallery]--[Music Booth]      ====== Achterbahn-Strecke ======
        |                  |                 |               umrundet den Norden und Osten,
 [Ghost Train]======[ FAIRGROUND ]------[Coaster Station]    zwei Bahnübergänge (X) mit Schranke
        |              |   |    |            X
 [Carousel]------[Park Office] |      [Cold Store]
        |              |       |            |
 [Workshop]------[Security Booth]  ~~~ Log Flume ~~~ (Kanal mit zwei Brücken)
        |                              |        |
 [Bumper Cars]---[Substation]    [First Aid Tent]
                       \              /
                        [ Main Gate ]   (Süden, Spawn-Nähe, Drehkreuze)
```

Leitgedanken für den Grundriss: der Festplatz als Mitte wie die Cafeteria; die Achterbahn und der
Wasserkanal als zwei Linien, die die Karte zerschneiden und nur an Übergängen (Schranke, Brücke)
passierbar sind; die Geisterbahn als Abkürzung durch das Dunkle.

## Welt-System: Fahrgeschäfte

Host-autoritativ wie das Wetter im Wald (neue Ops auf RPC 237), sichtbar für alle, nie während einer
kritischen Sabotage, jedes mit Abklingzeit. Ein kurzes Signal (Glocke, Hupe) kündigt jedes Ereignis
2 s vorher an, damit es fair bleibt.

| Ereignis | Was passiert | Spielwirkung |
|---|---|---|
| **Coaster Run** | Der Zug donnert über die Strecke, Schatten und Luftzug | Die Schranken an den Bahnübergängen schließen für etwa 5 s: Wege gesperrt |
| **Carousel Spin** | Das Karussell läuft an, Musik, Lichter | Der Durchgang am Karussell ist für etwa 10 s gesperrt; viel Bewegung im Bild |
| **Ghost Train Flash** | Ein Wagen fährt durch den Tunnel, am Ende ein Blitz | Das "Fahrtfoto" am Monitor des Tunnelausgangs zeigt alle, die gerade im Tunnel waren (Silhouetten in Spielerfarbe); sichtbar nur, wer vor dem Monitor steht, bis zum nächsten Blitz. Information mit Aufwand, wie das Laserprotokoll |
| **Log Flume Drop** | Ein Boot stürzt die Rinne hinunter, Gischt | Die Brücke an der Rinne ist kurz nass und gesperrt; das Boot verdeckt kurz die Sicht |
| **Turnstile Jam** | Die Drehkreuze am Haupteingang klemmen | Beide Drehkreuz-Reihen sperren für etwa 5 s ganz |

**Drehkreuze (Einbahnweg):** Der Haupteingang hat zwei Drehkreuz-Reihen. Die westliche lässt nur
in den Park hinein, die östliche nur hinaus zum Eingangsplatz. Der Eingangsplatz wird so zu einer
Schleife mit fester Richtung: wer flieht oder verfolgt, muss ihr folgen. Regeln, damit das fair bleibt:
- jede Einbahn-Stelle hat einen normalen Umweg; niemand kann eingesperrt werden (auch nicht bei
  Barrier Gates oder Turnstile Jam, dann öffnet ein Notausgang)
- Pfeile auf dem Boden und grüne/rote Lampen an den Drehkreuzen zeigen die Richtung
- Vents und Fähigkeiten (Morph, Portal, Sleepwalker) sind nicht betroffen

Technik: Bewegung ist in Among Us client-seitig, jeder Client bewegt nur den eigenen Spieler. Jedes
Drehkreuz bekommt deshalb einen Kollider, den jeder Client für seinen eigenen Spieler schaltet: aktiv,
sobald der Spieler auf der Ausgangsseite steht (zurück geht nicht), inaktiv auf der Eingangsseite
(durch geht). Die Positionen der anderen kommen übers Netz und werden davon nicht berührt. Muss auf der
Graybox mit Autotest geprüft werden, besonders gegen Durchrutschen bei hoher Geschwindigkeit (Scout,
Speed-Modifier) und beim Rundenstart.

Dazu ein Impostor-Werkzeug wie der Sturmholz-Knopf im Wald: **Ride Override** auf der Sabotage-Karte
startet ein Fahrgeschäft außer der Reihe (eigene Abklingzeit), etwa um die Schranken genau dann zu
schließen, wenn jemand flieht.

**Geisterbahn:** im Tunnel stark verringerter Sichtradius (wie Licht aus, nur dort), innen
Pappmaché-Monster, die aufleuchten. Ein Vent im Tunnel macht sie für Impostor gefährlich.

**Spiegelkabinett:** Glaswände wie die Vitrinen im Museum (sperren den Weg, nicht die Sicht), dazu
gespiegelte Kopien der Spieler als Deko, die in die falsche Richtung laufen.

## Sabotagen

| Skeld | Midnight Fair | Reparatur |
|---|---|---|
| Reactor (kritisch) | **Coaster Brake Failure** | zwei Bremshebel am Coaster Station gleichzeitig halten |
| O2 (kritisch) | **Ammonia Leak** | zwei Absperrventile: Cold Store und Park Office |
| Lights | **Park Blackout** | Umspannhaus; nur Leuchtreklamen und Notausgangsschilder bleiben |
| Comms | **Speaker Feedback** | Mischpult in der Music Booth; bis dahin keine Tasks sichtbar |
| Doors | **Barrier Gates** | Absperrgitter an den sieben Skeld-Türräumen |

Plus Ride Override (siehe Welt-System). Reparatur-Minispiele aus den vorhandenen Bausteinen.

## Tasks (Reskins auf Skeld-Tasks)

Regeln wie im Task-Konzept: jeder Park-Task reitet auf genau einem Skeld-Task, gleiche Kategorie,
Schritte und Konsolenkette; Dauer wie das Skeld-Gegenstück (±20 %). Vorschläge:

| Skeld-Task | Park-Task | Bereich | Baustein |
|---|---|---|---|
| Fix Wiring (Common, 3) | **Fix the Light Strings** | mehrere | Zuordnen (Lämpchenkette zu Steckern) |
| Swipe Card (Common, 1) | **Badge Through the Turnstile** | Park Office | Reskin (A) |
| Calibrate Distributor (Short) | **Balance the Carousel Motors** | Substation | Band halten |
| Chart Course (Short) | **Plan the Parade Route** | Ferris Wheel | Pfad ziehen |
| Clean O2 Filter (Short) | **Clean the Cotton Candy Machine** | Cold Store | Rubbeln |
| Divert Power (Short, 2) | **Power a Ride** | Substation, dann ein Bereich | Zuordnen |
| Prime Shields (Short, visuell) | **Screw In the Tower Bulbs** | Light Tower | Drehen; Welt-Effekt: der Turm funkelt |
| Stabilize Steering (Short) | **Level the Ferris Wheel** | Ferris Wheel | Band halten |
| Unlock Manifolds (Short) | **Unlock the Ride Keys** | Coaster Station | Auswählen (Reihenfolge am Schlüsselbrett) |
| Upload Data (Short, 2) | **Collect the Ride Photos** | Bereich, dann Park Office | Auswählen |
| Align Engine Output (Long, 2) | **Tune the Carousel Drive** / **Tune the Bumper Cars** | Carousel, Bumper Cars | Band halten |
| Clear Asteroids (Long, visuell) | **Shooting Gallery** | Shooting Gallery | Klickziele (Blechenten, Pappclowns nicht treffen); Welt-Effekt: Enten klappen um |
| Empty Garbage (Long, 2, visuell) | **Clear the Popcorn Bins** | Fairground, dann Workshop | Zuordnen, dann Hebel; Welt-Effekt: Container wackelt |
| Fuel Engines (Long, 4) | **Refuel the Ride Generators** | Workshop, Bumper Cars, Workshop, Carousel | Befüllen |
| Inspect Sample (Long) | **Allergen Test** | First Aid Tent | Auswählen mit 60-s-Timer |
| Start Reactor (Long) | **Test Run the Coaster** | Coaster Station | Reskin (A) oder eigene Reihenfolge am Stellpult |
| Submit Scan (Long, visuell) | **Height Check** ("You must be this tall") | First Aid Tent | Reskin (A), Scan bleibt sichtbar |

## Vents, Kameras, Admin

- **Vents (14):** Kanaldeckel, Wartungsluken, eine Falltür in der Geisterbahn, eine Luke unter der
  Achterbahn-Station. Drei bis vier Netze; mindestens ein Netz verbindet beide Seiten des Kanals.
- **Kameras (4):** Bahnübergang, Festplatz, Geisterbahn-Eingang, Wildwasser-Brücke.
- **Admin:** Lageplan im Park Office, mit Zählern für alle 18 Bereiche, falls der Prototyp klappt.

## Rauswurf- und Skip-Szenen

Mit der vorhandenen Engine (tools/eject_scenes.py):

- **Loop the Loop:** der Wagen hebt im Looping ab und fliegt über den Park davon
- **Human Cannon:** Zündschnur, Knall, der Spieler als kleiner Punkt am Mond (die Kanone steht als
  Kulisse im Park, ist aber kein Transportmittel)
- **Ferris Wheel:** die oberste Gondel klinkt aus
- **Log Flume Drop:** das Boot stürzt, unten taucht nur das Boot wieder auf
- **Ghost Train:** das Pappmaché-Maul am Tunnelende klappt zu
- Skip: das leere Karussell dreht sich allein weiter, die Popcornmaschine ploppt von selbst, ein
  Pappclown dreht den Kopf

## Stil und Grafik

Nachtblau, warme Lichterketten, gestreifte Zelte in verblassten Farben, Leuchtreklamen mit einzelnen
kaputten Buchstaben, Pappfiguren und Pappmaché. Among-Us-Linienstil wie Museum und Wald, gleiche
Pipeline (Generator-Skript `tools/gen_park.py`, `park_layout.py`).

Anspruch höher als bei Museum und Wald, ohne das Speicherbudget zu sprengen: die Qualität kommt aus
den Props und dem Licht, nicht aus der Bodenauflösung.
- Props mit Supersampling gezeichnet wie die Rauswurf-Grafik, mit echten Details: Glühbirnen der
  Lichterketten mit Lichthof, Zeltstoff mit Falten und Nähten, abgeblätterte Farbe, Schrauben an den
  Fahrgeschäften, Pappfiguren mit sichtbarer Stütze hinten
- Licht als eigene Ebene: Lichterketten, Leuchtreklamen und Notausgangsschilder bekommen Leuchtsprites,
  die bei Park Blackout gezielt ausgehen oder weiterleuchten
- bewegte Teile (Karussell, Riesenrad, Achterbahnzug, Boote, Schranken, Drehkreuze) als eigene Sprites,
  damit das Welt-System sie animieren kann
- vor dem Grafikbau ein Stilblatt mit drei, vier Musterprops (Bude, Zelt, Karussell, Leuchtreklame) im
  Spiel abnehmen, bevor alles in dem Stil entsteht

## Größe und Speicher

Museum und Wald bringen je etwa 10,5 bis 11 MB Grafik mit, die Atlas-DLL liegt bei 27,8 MB, und
Among Us läuft als 32-Bit-Prozess, der mit dem TOR-Hut-Pack schon knapp ist. Eine größere Karte darf
deshalb **nicht** proportional mehr Grafik kosten. Ziel: höchstens so viel wie das Museum.

- große, gleichförmige Flächen (Wege, Rasen, Pflaster, Wasser) als wiederholte Kacheln statt als ein
  durchgemaltes Bodenbild, niedrigere Auflösung für schlichten Boden
- Wiedererkennung über Props (Buden, Fahrgeschäfte), nicht über den Boden
- vor dem Grafikbau klären, ob die Grafik einer Karte erst beim Bau geladen und danach freigegeben
  wird oder dauerhaft im Speicher liegt

## Arbeitsreihenfolge

1. dieses Konzept abstimmen (offene Fragen unten)
2. ~~Prototyp zusätzliche Räume~~ bestanden (siehe oben)
3. ~~Grundriss als Graybox~~ steht (2026-09-23, siehe unten)
4. ~~Welt-System Fahrgeschäfte~~ steht (2026-09-23, siehe unten)
5. Tasks aus den Bausteinen
6. Grafik (`gen_park.py`), Konsolen, Vents, Lobby-Symbol
7. Sabotagen und Ride Override
8. Rauswurf- und Skip-Szenen im Rauswurf-Kino
9. Playtest

## Offene Fragen

1. **Häufigkeit der Fahrgeschäfte:** etwa ein Ereignis alle 20 bis 40 s? Zu oft nervt, zu selten
   verpufft die Achse. Am besten als Host-Option (selten / normal / oft).
2. **Richtung der Drehkreuze:** fest (Vorschlag oben) oder dreht ein seltenes Ereignis sie um?

## Stand Graybox (2026-09-23)

Pipeline wie beim Wald: `tools/park_layout.py` (Zahlen) -> `park_geo.py` (Geometrie, Achterbahn und
Kanal schneiden die Wege ausser an Uebergaengen und Bruecken) -> `gen_park.py` (Graybox-Boden 40 px/m,
Bloecke, Minimap, `src/AtlasParkData.cs` + `AtlasParkLayout.cs`) und `park_plan.py` (Nachrechnung).

- Karte 74 x 50 m, 2551 m2 begehbar, ein zusammenhaengendes Stueck, keine Sackgassen
- weitester Spielpunkt ab Spawn 43 m (etwa 17 s), Reaktor-Hebel 9 m auseinander, O2-Paar 29 m
- 13 Tueren (7 senkrecht, 6 waagerecht), 46 Konsolen alle platziert, 12 Vents in vier Dreier-Netzen,
  4 Kameras, 18 Admin-Zaehler (4 davon fuer die Attraktionen)
- im Spiel geprueft: Aufbau ohne Fehler, Standortanzeige auch fuer Ghost Train und Log Flume,
  Kamerabilder, Achterbahn sperrt den Weg und laesst die Sicht durch; Freeplay-Knopf "the CARNIVAL"
  (eigene Zeile unter Museum/Forest) startet den Park ohne Diagnose-Teleport
- Graybox-Grafik gesamt etwa 0,5 MB
- noch vanilla: Task-Namen und Minispiele, Sabotage-Namen, Rauswurf, kein Welt-System, kein Raumton;
  das Lobby-Symbol ist gezeichnet, der Lobby-Kartenwaehler mit drei Atlas-Symbolen ist noch nicht im
  Spiel angesehen

Ueberarbeitung nach dem ersten Ablaufen (User 23.09.: "Grundriss solide", aber keine Aussenbereiche
um die Gebaeude und zu wenig Bewegungspotential bei den Vents):
- keine Hoefe mehr: die Gebaeude stehen im Dunkeln, gerade Wege verbinden die Eingaenge; neu dafuer
  Karussell-Nordoeffnung mit Weg zur Schiessbude und ein Stichweg zum Umspannhaus
- alle 14 Skeld-Vents in drei langen Ringen (Nord 5, Mitte 4, Sued 5) plus zwei Querverbindungen ueber
  den dritten Nachbarn (Vent.Center, neu: `AtlasMapDef.VentBridges`): Riesenrad <-> Karussell,
  Bahnhof <-> Sanitaetszelt. Im Spiel geprueft, Verbindungen per Log bestaetigt.
- begehbar jetzt 2272 m2, weitester Spielpunkt 49 m (etwa 19,5 s); Umspannhaus und Sanitaetszelt haben
  nur einen Eingang (wie Electrical und MedBay auf der Skeld)

## Stand Welt-System (2026-09-23)

`src/AtlasParkWorld.cs`, Daten aus `park_layout.py` (Klasse `AtlasParkWorldData` in `AtlasParkLayout.cs`),
Netz ueber RPC 237 Op 10 [Art], Impostor-Knopf ueber Op 4 (Art 2 = Ride Override).
- Host startet alle 22 bis 38 s (erstes nach 20 s) eines von fuenf Fahrgeschaeften, nie bei Meeting,
  Rauswurf oder kritischer Sabotage; 2 s Vorwarnung (Glocke, Lampen), Geraeusche nach Entfernung leiser
- Coaster Run 6 s (3 Schranken, Zug faehrt die Runde), Carousel Spin 10 s (Scheibe dreht, Seile an
  Nord- und Westoeffnung), Ghost Flash (Wagen durch den Zickzack, Blitz, Foto am Monitor auf dem
  Vorplatz), Log Flume Drop (Boot den Kanal hinab, Ost-Bruecke 4 s gesperrt), Turnstile Jam 5 s
- Einbahn-Drehkreuze je Client fuer den eigenen Spieler; Geisterbahn innen dunkel (Sichtfaktor 0,35)
- Ride Override: roter Knopf auf der Sabotage-Karte auf der Strecke zwischen Parkbuero und Bahnhof,
  30 s Abklingzeit, abgelehnt waehrend eines laufenden Fahrgeschaefts
- im Spiel geprueft (Autotest): alle fuenf Ereignisse inkl. Gesamtbildern, Einbahn-Probe PASS,
  Blitzfoto zeigt den Dummy, Geisterbahn dunkel, Ride Override loest eine Fahrt aus
- Diagnose: TaskTest world:coaster|carousel|ghost|flume|jam|oneway (je mit Gesamtbild), world:sabmap/sabtap
- Weltschrift ist nicht sichtmaskiert und liegt ueber der HUD-Karte: deshalb hat der Monitor keine Schrift
- offen: Mehrspieler (Ablauf auf allen Clients gleich?), Einbahn beim echten Laufen (Logik geprueft,
  Kollider wie das Sturmholz), Balance der Haeufigkeit

## Stand Tasks, Sabotagen, Rauswurf (2026-09-23)

Tasks (Schritt 5): 15 eigene Minispiele aus den Bausteinen von Museum und Wald, Swipe Card und Submit
Scan bleiben vanilla (Badge Through the Turnstile, Height Check). Neu: `AtlasMapDef.TaskArt`/`TaskText`
leiten Grafik und Texte je Karte um ("datei" fuer alle Minispiele, "art:datei" nur fuer eine Baustein-Art),
zentral in `AtlasAssets.TaskSprite`/`TaskTextureCopy` und `MatchKit.Text`; Grafik aus
`tools/gen_park_tasks.py` (task_park_*, task_bin_food/recycle, task_trash_popcorn/candy/hotdog/cup).
Gegenueber der Tabelle oben geaendert, damit sich die Bausteine nicht wiederholen:
- Prime Shields: **Aim the Tower Spotlights** (Spiegel-Baustein, warmer Strahl; Welt-Effekt zwei
  Scheinwerferkegel am Lichtturm)
- Stabilize Steering: **Spot the Runaway Balloon** (Fernglas ueber dem naechtlichen Park)
- Align Engine Output: **Tune the Ride Motors** (Karussell-Zahnrad, dann Autoscooter-Rad)
- Start Reactor: **Pump the Coaster Brakes** (Pumpe mit Hydrauliköl)
- Welt-Effekte: Treffer-Stern ueber der Schiessbude, Popcornwolke am Container

Sabotagen (Schritt 7): Coaster Brake Failure (Bremsbacke verfolgen, Zwei-Personen-Regel vanilla),
Ammonia Leak (Ventile nach Plan), Park Blackout (durchgebrannte Gluehbirnen tauschen), Speaker Feedback
(Trichterlautsprecher ausrichten, Pegel). Barrier Gates: keine eigene Bezeichnung noetig (Tuersabotage
hat keinen Text).

Rauswurf (Schritt 8): `tools/gen_eject_park.py` (task_eject_pk_*) + Szenen in `eject_scenes.py`:
Menschenkanone (Spieler als Punkt am Mond), Riesenrad (Gondel klinkt aus), Wildwasserbahn (nur das Boot
taucht wieder auf), Geisterbahn (Maul klappt zu, der leere Wagen rollt zurueck), Looping (Wagen hebt ab).
Skip: leeres Karussell mit Drehorgel, Popcornmaschine und Pappclown, der den Kopf dreht. Neue Klaenge in
EjectSynth und im Kino: boom, pop, organ, sizzle, clack, chime.

Autotest: alle Minispiele (`tasktest.sh park "candy,motors,..."`), Sabotagen mit `@0` und `sab:lights`/
`sab:comms`, alle Szenen `eject:0..4`, `ejectskip:0..1` im Spiel geprueft. Ein nativer Absturz
(GameAssembly+0x10ac24e, Nullzeiger) trat einmal nach 13 Minispielen am Stueck auf und liess sich im
zweiten Lauf an derselben Stelle nicht wiederholen: beobachten.

## Stand Grafik (2026-09-23)

Stilblatt (Bude, Karussell, Kassenhaeuschen mit Leuchtreklame, Lichtturm) im Spiel vom User abgenommen,
danach alles in diesem Stil:
- `tools/park_floor.py`: Boden als nahtlose 4-m-Musterkacheln je Bereich (Pflaster, Saegemehl, Schachbrett,
  Dielen, Fliesen, Teppich, Beton, Traenenblech, Rasen), Schiene mit Schwellen, Kanal, Bruecken,
  Warnstreifen an den Uebergaengen, Einbahn-Pfeile, Wandkrone, Nordwaende je Bereich (Zeltstoff, Bretter,
  Ziegel, Spiegelglas, draussen Hecke), weicher Wandschatten. 80 px/m, 12 Kacheln, etwa 10 s.
- `tools/park_art.py`: alle 17 Objektarten (160 px/m wie Museum/Wald), Laternenpfahl an/aus.
- `tools/park_consoles.py`: 50 Konsolen aus dem Baukasten von wald_consoles.py mit Park-Farben; Montageart
  aus der Position im Grundriss; eigene Motive Zuckerwattewagen und Popcorn-Klappe.
- Lichtebene: 16 Laternen am Wegrand (`AtlasParkWorldData.Lamps`), Lichtfleck auf z 8,5; bei Park Blackout
  flackern sie aus, die Leuchtreklamen bleiben an. Diagnose `world:lamps`, `world:blackout`.
- Fahrzeuge (Zug, Boot, Geisterbahnwagen) gezeichnet in gen_park_tasks.py; die Karussellscheibe zeigt nur
  noch waehrend der Fahrt einen halbdurchsichtigen Wirbel ueber dem gezeichneten Karussell.
- Speicher: 45 Megapixel Kartengrafik (Museum 92), 5,5 MB auf der Platte.
Offen: eigener Raumton fuer den Park, Minimap noch im Graybox-Look, Playtest.
