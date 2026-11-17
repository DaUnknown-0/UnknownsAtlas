# Life an Layout, Grafik und Spieltest

## Vertrag und Pollenbereich

- Eigene Implementierung: `src/AtlasAmberhiveLife.cs`. TOR-Option 1730 `Amberhive Pollen Trails`, Off/On, Standard Off. Suche nach 1730 bis 1739 in allen C#-Quellen unter TOR Mod: keine fremde Optionsbelegung von 1730, Atlas reserviert 1720 bis 1739.
- Keine Bluetenkammer vorhanden. Festgelegter Ersatz: Pollenmatte vor dem Blumenregal im Waggle Studio. Mittelpunkt relativ zum bestehenden `flower_pots`-Prop: 1,05 m westlich der Grundflaechenmitte, 0,55 m noerdlich der Standlinie. Ellipse mit Radien 0,8 m / 0,65 m. Beim jetzigen Layout ungefaehr (18,6 / 8,15), in beiden Etagenfassungen vorhanden. Der Abstand zur unteren Raumwand wurde beim Offline-Test beruecksichtigt. Bitte bei Layoutaenderung die freie Begehbarkeit erhalten oder die Lage abstimmen. Life zeichnet dort eine dezente goldene Pollenmatte, nur bei eingeschalteter Option.
- Die Fuesse werden fuer sechs Sekunden nach dem Verlassen bepollt. Jeder goldene Abdruck bleibt sechs Sekunden. Anonyme, fuer alle Rollen gleiche Farbe, Host erzeugt und uebertraegt Position, Richtung und Zeit. Normale Sichtmaske bleibt aktiv.
- Bitte `src/AtlasAmberhiveLife.cs` nicht parallel aendern. Fremde Dateien erhalten nur mit `AMBERHIVE LIFE` markierte kurze Einhaengepunkte.
- Netzvertrag: AtlasWorld Op 24, neue Hive-Subs 16 bis 19 fuer Life reserviert. Bestehende Subs 0 bis 4 bleiben erhalten.

## Einhaengepunkte fuer Layout-Agent

In `AtlasAmberhive.cs`: Life nach `BuildBees` aufbauen, nach normalem Welt-Tick ticken, beim Zerstoeren entsorgen, Life-Subs vor bestehendem Receive behandeln, bei genehmigter Rutsche Spieler fuer Spuren sperren, Bienen vor Bewegung mit sichtbarem Spielerabstand korrigieren. Die wenigen Aufrufe sind markiert. Bitte bei spaeteren Ueberarbeitungen erhalten.

## Spieltest, noch auszufuehren

Among Us wird durch den Life-Agenten nicht gestartet.

1. Eine und zwei Etagen: Bienen weichen einem sichtbaren laufenden Spieler aus, bleiben im Raum. Kerzen am candle_rack und Thron flackern im Vorbeigehen. Niemand hinter einer Wand oder ausserhalb des Lichtradius darf eine Reaktion ausloesen.
2. Honigflut betreten: kurze lokale, bernsteinfarbene Fussabdruecke. Unsichtbare Spieler, Vents, tote Spieler und Spieler ausserhalb eigener Sicht erzeugen keine lokalen Reaktionen. Nach Verlassen des Blickfeldes werden Honigabdruecke verborgen, beim Wiederbetreten darf keine fremde Bewegung im Dunkeln rekonstruiert werden.
3. Host-Option 1730 Standard Off kontrollieren, danach On. Zwei Clients: Pollenmatte im Waggle Studio betreten, anschliessend sechs Sekunden Spuren, jeder Abdruck sechs Sekunden Lebensdauer. Gleiche Positionen, Reihenfolge und Zeit auf Host und Gast, kein Spielerfarbcode.
4. Pollen vor Vent/Rutsche/Treppe aufnehmen. Keine Spuren im Vent, auf der Rutsche, zwischen Etagen oder entlang eines Teleports. Nach verborgener Fortbewegung muss der Pollen neu aufgenommen werden. Ninja, Phantom, Scout, Chameleon und PropHunt-Unsichtbarkeit jeweils als Host UND Gast testen, auch Host mit Impostor-/Geistersicht. Verbleibende alte Abdruecke duerfen nur bereits sichtbare Schritte zeigen.
5. Meeting, Exil, Tod, Disconnect, neue Runde und Hostwechsel pruefen. Meeting entfernt Spuren und Bepollung. Keine alten Zeitstempel in der naechsten Runde.
6. Sonnenfleck am Honigbrunnen vergleichen: kontinuierlicher Wandel ueber die Rundenzeit, gleicher Stand auf Host und Gast. Meetings pausieren die Rundenzeit. Licht-Radien muessen mit und ohne Life identisch bleiben.
7. Glow Fade ausloesen und reparieren: Lampen erloeschen nacheinander vom Lamphouse aus und gehen nacheinander wieder an. Schnell hintereinander sabotieren und reparieren: weicher Uebergang, kein Sprung. Sichtweitenreduktion tritt weiterhin gemaess Vanilla sofort ein. Auch mit einer und zwei Etagen testen.

## Testschalter

Die folgenden Schluessel liegen in der BepInEx-Config von Atlas. Die ersten drei sind ausschliesslich im Freeplay wirksam. Der Life-Agent veraendert keine Spiel-Config ausserhalb der Arbeitskopie.

```ini
[Diagnostics]
AmberhivePollenTest = 1
AmberhiveSunPeriodTest = 30
AmberhiveGlowTest = true
AmberhiveLifeLog = true
```

- `AmberhivePollenTest`: -1 folgt der Host-Option, 0 aus, 1 an. Vorgabe -1. Im Mehrspieler stattdessen die echte Host-Option 1730 umschalten.
- `AmberhiveSunPeriodTest`: 0 nutzt den normalen 600-Sekunden-Zyklus; ab 30 verkuerzter Freeplay-Zyklus.
- `AmberhiveGlowTest`: alle acht Sekunden optisch zwischen Glow Fade und Reparatur wechseln. Aendert weder die echte Sabotage noch die Sichtweite. Echte Licht-Sabotage zusaetzlich testen.
- `AmberhiveLifeLog`: alle zwei Sekunden `[Atlas/Life]` mit Host-Uhr, Sync-Status, Pollenoption, Abdruckzahl, lokalen Honigabdruecken, sichtbaren Laeufern, Glow Fade und Meeting-Generation. Auch im Multiplayer verfuegbar. Kleine Netzwerkverzoegerungen zwischen den Clients sind zu erwarten.

Vorhandene Diagnosen des Layout-Agenten bleiben zustaendig fuer Honigflut, Rutsche und echte Sabotagen. Fuer manuelle Sichttests `TaskTest` leer lassen, damit kein automatischer Rundgang den Spieler versetzt. Freeplay-Etagen wie bisher mit `AmberhiveFloorsTest = 0` bzw. `1` testen.

Nach dem Test Life-Schalter auf -1 / 0 / false / false zurueckstellen.

## Freigabe vor einer Veroeffentlichung

- Rollen- und Zwei-Client-Pruefungen oben sind noch offen. Der erfolgreiche Build und die Offline-Regeltests bestaetigen keine Unity-Sichtmasken oder fremden Rollen-RPCs.
- Sonnenstrahl, Kerzen und Laternen werden aus kleinen lokalen Sprite-Masken aufgebaut. Bitte optische Einpassung zu den neuen Grafiken abnehmen. Es werden keine fremden Grafikdateien ersetzt.
- Die zentrale `ID-Registry.md` liegt ausserhalb der erlaubten Arbeitskopie und wurde nur gelesen. Beim Zusammenfuehren dort Option 1730 und Hive-Subs 16/17 nachtragen.
