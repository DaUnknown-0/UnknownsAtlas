# Amberhive V4: Layout, Gameplay, Code und Spieltest

Arbeitsstand: 16.11.2026. Alle eigenen Quellen und Ergebnisse liegen in UnknownsAtlas_AmberhiveV4. Keine Subagents, Forks, Commits, Pushes oder Tags gestartet. Andere Projekte wurden ausschliesslich gelesen. Grafik-, Life- und Sound-Aenderungen der parallel arbeitenden Agents wurden erhalten.

## Schwaechen vorher

- Waggle Studio war ohne Krone eine Sackgasse. Comms war dadurch uebermaessig leicht abzuschneiden.
- Der Suedring hatte nur auf der Wasp-Seite einen direkten Zugang zum Thronsaal.
- Die Verbindung West Press zu Wasp Watch endete zu frueh in den abgeschraegten Raumecken. Der echte Bewegungstest blieb am Uebergang haengen.
- Amberhives Weltobjekte erbten die 1.2-fache Skalierung des Ship-Roots. Damit waren Seesperre und Effektbilder groesser als die erzeugten Kartenkoordinaten.
- Das Rutschenende lag teilweise ausserhalb der freien Fussflaeche. Reine Geschwindigkeitszuweisung konkurrierte beim Rutschen mit der normalen Spielerphysik.
- Bruecken- und Flutmeldungen enthielten nur Ereignisse ohne regelmaessigen Zustandsabgleich. Die Bruecke raeumte Spieler zum naechsten statt zum gemerkten Eintrittsufer.
- Die Generatorpruefung benutzte die gezeichnete Bodenflaeche, nicht die tatsaechliche Bewegungsbegrenzung. Lokale Diagnosewerte konnten die Etagenauswahl auch ausserhalb des Freeplay beeinflussen.
- maptest.sh verwies fest auf UnknownsAtlas und schrieb seine Ergebnisse ausserhalb der Kopie. Fehlende Original-Configs wurden beim Rueckbau nicht entfernt.

## Layout und Verteilung

- Neuer offener Zugang Keeper's Office zu Waggle Studio, bis in die abgeschraegte Waggle-Ecke hinein verlaengert. In beiden Etagenvarianten benutzbar.
- Neuer offener Zugang Queen's Chamber zu Sun Compass. Ausreichend Platz unterhalb der royal_cells.
- West Press zu Wasp Watch: Durchgang auf (-14.8,-13.8) bis (-12.5,-12.8) verlaengert. Die vorhandene 1.0-m-Tuer bleibt erhalten, Mittelpunkt nun (-13.65,-13.3). Der Bewegungstest erreicht jetzt die andere Raumseite.
- Neun zusaetzliche Platzierungen mit echter Kollision aus Grafik Runde 2 uebernommen: Tische, Blumen, Kiste, Buecherregal, Brutwaben und Honigfaesser. Vier nur mit Krone. Zwei Vorschlaege wegen unpassender Bildbreite beziehungsweise Engstelle abgelehnt, siehe V4_WUENSCHE_LAYOUT.md.
- Vent 6 nach (-4.45,7.7) neben den neuen Tisch verschoben. Elf vorhandene Skeld-Vents bleiben in vier getrennten Netzen. Mit zwei Etagen wird das bisherige diagonale Zweiernetz auf Sun Deck und Drone Dock verlegt. Keine nicht vorhandenen Vent-IDs erzeugt.
- Alle 46 Skeld-Konsolen bleiben erhalten. Die Krone ergaenzt sechs bestehende Airship-Aufgaben. Der Generator haelt Konsolen von Tueren, Requisiten, Treppen, Vents und anderen Benutzpunkten fern.
- Vier ausdrueckliche Kamerablickpunkte zeigen Brunnen, Westgang, Ostgang und den suedlichen Thronsaal statt automatisch entfernter Raummitten. Die Krone bleibt ein Bereich ohne Kameraabdeckung.
- Admin-Raumflaechen und eigene Crown-Systeme bleiben erhalten. Neue Verbindungen sind als Flure erfasst.

## Laufwege und Kollisionspruefung

validate_hive.py prueft die exportierten Bewegungswaende und Requisiten mit einem konservativen Spielerradius von 0.28 m auf einem 0.15-m-Raster. Drei Brueckenlagen und jede der sieben geschlossenen Tuergruppen ergeben zehn Szenarien je Etagenfassung. Treppen werden bidirektional, die Rutsche nur abwaerts verbunden. Die Messung modelliert keine dynamisch aus Konsolenbildern erzeugten Boxen; echte Physikproben ergaenzen sie im Spiel.

Gemessene Wege bei offener Nord-Sued-Bruecke, Meter, ohne Honigbremsung:

| Weg | Vorher | V4 |
|---|---:|---:|
| Keeper zu Waggle | 22.15 | 9.68 |
| Queen zu Sun | 14.82 | 11.22 |
| Spawn zu Comms, eine Etage | 32.60 | 21.74 |
| Zwischen beiden O2-Konsolen | 33.68 | 33.68 |
| Zwischen beiden Reaktorhaenden | 8.70 | 8.70 |

Ergebnisse: _out/v4_navigation_before.json und _out/v4_navigation.json. Alle Rettungswege zu O2, Reaktor, Licht und Comms bleiben in den geprueften Szenarien erreichbar. Geschlossene Raumgruppen koennen weiterhin die zugehoerigen Pressraeume oder Guard Comb voruebergehend einsperren. Keine Brueckenphase trennt den Grundriss. Nach der West-Press-Korrektur besitzt das Erdgeschoss auch mit konservativem Radius eine zusammenhaengende Flaeche; die Krone bildet die zweite, ueber Treppen verbundene Flaeche.

## Mechaniken und Synchronitaet

- Eigene Weltwurzel gleicht die Ship-Skalierung aus. Im Spiel passen Seesperre und Weltmeter zusammen.
- Bruecke: 22 s offen, 2.5 s Drehung, 3 s blinkende Vorwarnung. Vor dem Sperren werden die Fuesse samt Kolliderradius beruecksichtigt. Spieler werden zum zuletzt beobachteten Eintrittsufer geraeumt.
- Flut: 2.5 s Vorwarnung ohne Bremsung, 2 s Anstieg, 10 s Hochstand, 2.5 s Ablauf. Bewegung am Hochstand mit Faktor 0.70. Erste natuerliche Flut nach 40 s, danach 45 bis 65 s zwischen Starts. Keine direkte Zonenwiederholung. Zone 2 liegt jetzt voll im westlichen Verbindungsgang. Tote Spieler und Spieler im Vent werden nicht gebremst.
- Host schaltet weiterhin Bruecke und Flut. Zusaetzlich kommt alle zwei Sekunden ein Zustand mit Phase, Phasenalter, Flutzone, Flutalter und verbleibender Wartezeit. Clients setzen daraus ihre lokalen Zeitpunkte neu. Nicht vom Host stammende Zustandsmeldungen werden verworfen. Meetings und Exil pausieren die Mechanikuhr.
- Rutsche: Host prueft lebenden, beweglichen Spieler, Naehe, Ventzustand und Abklingzeit. Erst die Host-Freigabe startet die Fahrt. Das Ende liegt nun innerhalb der begehbaren Flaeche; die kurze Ausstiegsbewegung setzt den Physikkoerper gezielt und bestaetigt die Endlage per normalem Positions-RPC. Bewegung und Blende werden bei Abschluss oder Abbruch freigegeben.
- Option 1729 behaelt die vorhandene TOR-Synchronisierung. Ihr Diagnose-Override gilt nur noch im Freeplay. Welt-Diagnosen und Aufnahmen laufen ebenfalls ausschliesslich im Freeplay-Autotest.
- Grafikvertrag honey_r2_contract.json eingebunden: zwei Honigrinnen und drei Wandtropfstellen mit acht Bildern, 8 fps, 100 ppm, mittigem Pivot und den vereinbarten Tropfphasen. Rein optisch unter Figuren, normale Sichtmaske, keine Kollision oder eigenen Lichtquellen.
- Life-Subs 16 bis 19 und die markierten Sound-/Life-Einhaengepunkte bleiben erhalten. Die neuen eigenen Netzwerk-Subs 2 bis 4 kollidieren damit nicht.

## Build und Tests

- Mehrfach `python tools/hive/gen_hive.py build --art`, zuletzt mit 48 Prop-Platzierungen, 208 Konsolenreferenzen und ohne fehlende Bilder. Ein Aufruf ohne --art wird nun vor dem Schreiben abgewiesen.
- `dotnet build -c Release --nologo`: erfolgreich. Bekannte, unveraenderte Warnung CS0169 in AtlasAssetStore.cs.
- Python-Syntaxpruefung der eigenen geaenderten Werkzeuge erfolgreich. Alle PNGs im Amberhive-Paket vollstaendig lesbar.
- Letzte Zwei-Etagen-Physikpruefung: _out/v4_final_2f/amberhive.log, `diag done: 0 failure(s)`. Geprueft: Weltmass, Seesperre, begehbare Bruecke, Flutvorwarnung und Bremsung, sicheres Raeumen, Rutsche, unzulaessige Rutschenanfrage von unten, alle sechs Treppenrichtungen, beide neuen Rundwege in beide Richtungen und West Press zu Wasp Watch.
- Sabotagen: _out/v4_sabotages/amberhive.log, `sabotage diag done: 0 failure(s)`. Licht, Comms, O2 und Reaktor gestartet; alle vier echten Konsolen-Minispiele geoeffnet; Licht, Comms und O2 ueber ihre Systemmeldungen repariert. Beim Reaktor wurde im Freeplay das Ruecksetzprotokoll getestet, keine menschliche Zwei-Personen-Reparatur simuliert.
- Finale Ein-Etagen-Pruefung: _out/v4_final_1f/amberhive.log, `diag done: 0 failure(s)`, 13 bestandene Pruefungen. Zwei Etagen: 21 bestandene Pruefungen. Sabotagen: 16 bestandene Pruefungen. Der Ein-Etagen-Lauf verwendete zusaetzlich die Freeplay-Pollenoption und den beschleunigten Sonnenzyklus; Life meldete gueltige Host-/Sync-Zustaende. Das ist kein Nachweis der noch offenen Rollenfaelle.
- Vorlaeufige rote Proben bleiben unter _out/v4_test_2f*, _out/v4_test_1f_final und _out/v4_play_* als Fehlernachweis erhalten. Sie fuehrten zu den beschriebenen Anschlusskorrekturen. Ein zusaetzlicher falscher Zielpunkt mitten in einer Upload-Konsole wurde durch einen freien Laufpunkt ersetzt.

Selbst ausgewertete Bildbelege:

- _out/v4_final_2f/amberhive_shots/hive_well.png
- _out/v4_final_2f/amberhive_shots/hive_bridge_turn.png
- _out/v4_final_2f/amberhive_shots/hive_flood.png
- _out/v4_final_2f/amberhive_shots/hive_chute_exit.png
- _out/v4_final_2f/amberhive_shots/hive_keeper_waggle.png
- _out/v4_final_2f/amberhive_shots/hive_west_press_wasp.png
- _out/v4_sabotages/amberhive_shots/hive_well_lights_dark.png
- _out/v4_sabotages/amberhive_shots/hive_sab_oxygen.png
- _out/v4_final_2f/amberhive_shots/task_ejectskip_1_t2_081653.png
- _out/preview_2f.png

## Wiederherstellung und Testwerkzeug

maptest.sh loest seinen Ordner relativ zur Kopie auf und ruft maptest_runner.py auf. Ergebnisse und Sicherungen muessen innerhalb der Kopie liegen. Bei vorhandenem Among Us erfolgt Exit 3 ohne Testeinsatz. Der Test startet das Spiel normal ohne Parameter und beendet ausschliesslich die selbst gestartete Prozess-ID. DLLs, drei Configs und vorheriges Spiel-Log werden im finally-Block wiederhergestellt, zuvor fehlende Dateien wieder entfernt. Vorhandene AtlasShots werden auch zwischen C: und D: gesichert und zurueckverschoben. Fehler beim Sammeln der Testbilder verhindern die DLL-/Config-Wiederherstellung nicht.

Jeder abgeschlossene Lauf besitzt restore.json mit SHA256 vorher und nachher. Alle acht abgeschlossenen Laeufe stimmen ueberein, einschliesslich der vorher nicht installierten Zusatz-DLL. Das normale Spiel-Log ist ebenfalls zurueckgelegt. Nach dem letzten Ein-Etagen-Lauf wurden die aktuellen Dateien im Spielordner nochmals gegen diese Originalwerte geprueft. Keine Testsicherung und kein selbst gestarteter Spielprozess bleiben aktiv. Zusammenfassung: _out/v4_verification.json. Quell-/DLL-Pruefsummen: _out/v4_layout_sha256.json.

## Offene Punkte

- Der zusaetzliche Sonnendeck-Skip lud einschliesslich der neuen Rankenebene und wurde auf drei Bildern geprueft. Beim anschliessenden automatischen WrapUp entstand eine NullReferenceException in TheOtherRoles.Patches.ExileControllerWrapUpPatch.WrapUpPostfix. Vollstaendiger Stack in _out/v4_final_2f/amberhive_full.log. Die Welt-Physikpruefung davor war fehlerfrei. Dieser separate Abschlussfehler bleibt offen; TOR ausserhalb der Kopie wurde nicht veraendert.
- Kein Zwei-Client-Spiel gestartet. Hostwechsel, reale Netzverzoegerung, Meeting-Abbrueche unter Last und echte Zwei-Personen-Reaktorbedienung brauchen einen Mehrspielertest. Die regelmaessigen Zustandsmeldungen und Host-Pruefungen wurden implementiert und am Code kontrolliert, nicht als online verifiziert ausgegeben.
- Life-Rollenfaelle, Unsichtbarkeit, Pollen-Synchronitaet und Sichtschutzpruefungen mit Host und Gast bleiben gemaess V4_WUENSCHE_LIFE.md offen. Die hier enthaltenen Freeplay-Laeufe ersetzen diese Pruefung nicht.
- Vollstaendige Rundenbalance mit mehreren Menschen wurde nicht gemessen. Die Laufwege, Venttrennung und Rettungswege sind die belastbare Grundlage, keine Gewinnratenprognose.
