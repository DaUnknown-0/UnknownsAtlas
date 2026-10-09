# Unknown's Atlas

Neue Karten für Among Us · Copyright (C) 2026 DaUnknown-0 · GPL-3.0-or-later

Drei vollständig spielbare Karten, auswählbar neben den Vanilla-Karten, jede mit eigenen Räumen, eigenen
Minispielen für die Tasks, eigenen Sabotagen, eigenen Rauswurf-Szenen und einer Welt, die sich während der
Runde bewegt:

- **Vesper Museum**: ein Museum für Naturkunde und Technik nach Feierabend. Säle rund um eine Rotunde mit
  T.-Rex-Skelett, Ägyptischer Saal, Galerie, Planetarium, Maschinenhalle, Restaurierung, Depot mit Laderampe,
  Sicherheitsbüro. Die Türen sind durchsichtige Brandschutz-Rollgitter.
- **Forest Station**: eine Forst- und Forschungsstation. Begehbare Blockhütten (Messe, Försterei,
  Feldlabor, Sägewerk, Bootshaus, Lager ...), Lichtungen, breite Waldwege, ein Bach mit Stegen. Der dichte
  Wald ist die Wand.
- **Moonlight Carnival**: ein Freizeitpark nach Ladenschluss, heiter-gruselig. Festplatz, Karussell,
  Riesenrad, Achterbahn-Bahnhof, Geisterbahn, Wildwasserbahn, Schießbude, Autoscooter, Show Control und mehr,
  dazu zusätzliche Räume, die es auf der Skeld nicht gibt.

Wiki: <https://daunknown-0.github.io/tor-mods-wiki/atlas.html>

## Installation

1. `UnknownsAtlas.dll` aus dem neuesten Release nach `BepInEx\plugins` legen.
2. Voraussetzungen: Among Us 2024.11.26, BepInEx 6 (be.697), Reactor 2.3.1. The Other Roles ist optional;
   TOR-Rollen laufen auf den Atlas-Karten wie auf der Skeld.
3. **Alle Spieler** brauchen dieselbe Atlas-Version. Ist eine Atlas-Karte gewählt und passt das bei
   jemandem nicht, sperrt Atlas den Start und nennt über dem Startknopf, wer fehlt oder veraltet ist. Mit
   TOR - Forgotten Fixes erscheint Atlas zusätzlich als Spalte im Mod-Check.

Im **Freeplay** stehen die drei Karten als eigene Knöpfe unter den Vanilla-Karten. In einer **Lobby**
wählt der Host sie in der Kartenauswahl der Spieleinstellungen; Banner und Übersicht zeigen dann das Logo
der Atlas-Karte. Atlas aktualisiert sich selbst (Hauptmenü und Mod Manager von Forgotten Fixes).

## Was die Karten können

### Tasks

Jede Karte benennt alle Tasks um und ersetzt die meisten Minispiele durch eigene: Skelett abstauben,
Kasse abrechnen, Grabschloss-Ringe drehen, Hieroglyphen in Reihenfolge tippen, Lichtleiter-Puzzle,
Laserspiegel in der Vitrine, Sternbild nachziehen, Motten fangen, Pigment- und Wasserproben mit Wartezeit,
Pumpe im Takt, Stempeluhr zur vollen Stunde, Laternen mit Streichhölzern im Wind anzünden, Fernglas und
Projektor scharfstellen, Ventile in Reihenfolge, Generator mit Choke und Seilzug und vieles mehr. Der Park
nutzt dieselben Bausteine mit eigener Grafik und eigenen Texten (Zuckerwatte-Maschine, Paradewagen,
Fahrgeschäft-Motoren, Schießbude ...). Kabel-Tasks tragen Formsymbole für Farbenblinde. Verteilung, Fortschritt
und Taskwin bleiben vanilla.

### Sabotagen

- **Museum:** Sicherheitsalarm (Fingerabdruck verfolgen, zwei Personen), Klimaausfall (Code auf vertauschtem
  Tastenfeld), Sicherungen tauschen (Licht), Kamerabild einstellen (Comms) und **Rex erwacht**: das Skelett
  wacht auf und brüllt. Spieluhr in der Rotunde kurbeln und Nachtlicht im Sicherheitsbüro ausrichten, beides
  gleichzeitig, sonst schläft er nicht rechtzeitig wieder ein. Impostor können an den Stationen nur helfen.
- **Forest Station:** Waldbrand (Flammen mit dem Schlauch treffen), Wasserversorgung (Ventile nach Plan),
  Leistungsschalter (Licht), Funkmast ausrichten (Comms) und **Sturmholz**: Bäume stürzen quer über die Wege
  und müssen zersägt werden.
- **Moonlight Carnival:** Achterbahn-Bremsversagen, Ammoniak-Leck, Park Blackout (die Laternen gehen aus,
  die Leuchtreklamen bleiben an), Lautsprecher-Rückkopplung und **Ride Override** (Achterbahnfahrt sofort,
  die Schranken an den Bahnübergängen schließen).
- Türen lassen sich wie auf Polus und Airship auch während einer Sabotage schließen.

### Welt

- **Museum:** Laserschranken in den Durchgängen, jeder Durchgang erscheint im Laserprotokoll am Kamerapult.
  Planetariums-Show mit dunkler Kuppel. Die Augen der Galerie-Porträts folgen dir.
- **Forest Station:** Wetter (Regen, Nebel, Sturm mit Blitzen; Regen verlangsamt den Waldbrand), Dämmerung
  über die Runde mit Glühwürmchen, ein begehbarer Hochsitz mit weiterer Sicht und ein Kanu auf dem Bach.
- **Moonlight Carnival:** Fahrgeschäfte starten von selbst (Achterbahn mit Schranken, Karussell mit Seil,
  Geisterbahn mit Blitzfoto am Ausgangsmonitor, Wildwasserbahn mit nasser Brücke, klemmende Drehkreuze).
  Die Drehkreuze am Eingang sind Einbahn, die Geisterbahn ist dunkel. Zum Benutzen: Hau den Lukas (die
  Glocke hört die ganze Karte), das Maskottchen-Kostüm „Moony“ (verdeckt Farbe, Hut und Namen),
  Riesenrad-Gondel mit Weitblick und ein Pendelwagen auf der Achterbahnstrecke.
- Steht jemand in einem Durchgang, wenn sich eine Sperre schließt, kommt er auf der Seite heraus, von der er
  kam.

### Rauswürfe

Jede Karte hat eigene Rauswurf-Szenen und eigene Szenen für „niemand fliegt“, etwa Sarkophag, Falltür ins
Depot und T-Rex im Museum, Wildwasser und Hochsitz im Wald, Menschenkanone, Riesenrad und Looping im Park.
Der Host wählt die Szene, alle sehen dieselbe.

### Klang

Raumton je Karte (Lüftung und Wanduhr im Museum, Wind und Grillen im Wald, Nachtwind, Leuchtreklamen und eine
ferne Drehorgel im Park), dazu Wetter, Brüllen, Fahrgeschäfte und Attraktionen.

## Wie es funktioniert

Alle drei Karten sitzen auf der Skeld (Relocate-in-Place): jede Konsole, jeder Vent, jede Tür, jede Kamera und
alle Systeme der Skeld bleiben dieselben Objekte und werden nur an ihre neuen Plätze gesetzt. Neu sind Boden,
Wände, Kollider, Objekte, Task-Blöcke, Minimap, Raumnamen und alles Gezeigte. Dadurch laufen Tasks,
Sabotagen, Türen, Admin, Kameras und Vents online ohne eigenen Netzcode. Was Atlas selbst hinzufügt (Wetter,
Fahrgeschäfte, Rex, Attraktionen, Rauswurf-Szenen, Kartenwahl), entscheidet der Host und sendet es über
RPC 236 (Kartenwahl) und RPC 237 (Welt). `ShipStatus.Type` bleibt `Ship`; andere Mods erkennen die gebaute
Karte am AppDomain-Eintrag `UnknownsAtlas.ActiveMap` (`museum`, `wald`, `park`).

## Aufbau

```
src/AtlasMuseumBuilder.cs   Umbau der Skeld zur gewählten Karte (Kollider, Sicht, Konsolen, Vents,
                            Türen, Kameras, Minimap, Raumnamen)
src/AtlasMapDef.cs          eine Karte als Datensatz (Museum, Wald, Park), Task-Namen und Minispiele
src/AtlasSelection.cs       Kartenwahl in Freeplay und Lobby, RPC 236
src/AtlasHandshake.cs       Versionsabgleich, Startsperre, Selbsttest
src/AtlasWorld.cs           Welt-System (RPC 237), Wetter, Laser, Sturmholz, Kartenknöpfe
src/AtlasMinigame.cs, AtlasMechanics*.cs   eigene Minispiele und Sabotage-Reparaturen
src/AtlasRex.cs, AtlasParkWorld.cs, AtlasParkFun.cs, AtlasFerry.cs, AtlasLookout.cs, ...
                            Rex, Fahrgeschäfte, Attraktionen, Fahrzeuge, Hochsitz
src/AtlasEject.cs, EjectEngine.cs   Rauswurf-Szenen (assets/eject_scenes.json)
src/Atlas*Data.cs, *Layout.cs  ERZEUGT von den Generatoren unten

tools/gen_museum.py, gen_wald.py, gen_park.py   Karte aus *_layout.py -> Boden, Objekte, Task-Blöcke, Daten
tools/museum_art.py, handdraw.py, park_*.py      Zeichen-Baukasten (Among-Us-Stil)
tools/gen_tasks.py, gen_park_tasks.py, gen_eject*.py   Minispiel- und Szenengrafik
tools/preview_*.py, inspect_*.py                 Abnahme ohne Spiel
```

Neu erzeugen: `python tools/gen_museum.py`, `gen_wald.py` bzw. `gen_park.py` (Python 3, Pillow, shapely,
numpy; mit `PYTHONHASHSEED=0` für gleiche Ergebnisse), danach `dotnet build -c Release`.

Releases entstehen allein durch einen Tag-Push (`vX.Y.Z` stable, `vX.Y.Z.W` Testversion); die CI stempelt die
Version aus dem Tag und hängt die DLL an.
