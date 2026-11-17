# Grafik an Gameplay, Stand V4

Die Grafikaenderungen sind ohne neue Laufzeitlogik nutzbar. Bitte beim Spieltest pruefen:

- Bienen: beide Bilder besitzen jetzt identische Groesse und Anker. Die bestehende Umschaltung kann bleiben. Bitte Flug vor hellen und dunklen Boeden ansehen.
- Bruecke: neue Einlaufmarken und Messingverschraubungen. Bitte beide Endstellungen und die Drehphase mit Spieler pruefen.
- Sonnendeck-Skip: neue Ebene `task_eject_hive_deck_vine.png`, in `assets/eject_scenes.json` eingebunden. Bitte Ressourcenladung und sanftes Pendeln pruefen.
- Bodenkanten, Moos und Wartungseinlagen sind reine Grafik. Es wurden von mir keine Kollisionen geaendert.
- Bitte den Honig-Tiefenverlauf bei kleiner Sichtweite und waehrend der Flut pruefen. Die Offline-Vorschau enthaelt keine Laufzeit-Sichtmaske.

Optional fuer eine spaetere Ausbaustufe: getrennte Animationslagen fuer Thronkerzen und tropfende Wandzellen. Dafuer waere ein eigener Laufzeitvertrag sinnvoll. Die jetzigen statischen Requisiten habe ich nicht durch ungenutzte Frames erweitert.

Immer `python tools/hive/gen_hive.py build --art` verwenden. Der Szenengenerator kann mit `python tools/eject_scenes.py --amberhive-only` ausschliesslich Amberhive aktualisieren.

Rueckmeldung auf `V4_WUENSCHE_LAYOUT.md`: beide neuen offenen Verbindungen sind im aktuellen Bodenrender enthalten. Honigzone 2 wurde auf [-19.0, 3.2, -17.2, 7.1] neu gerendert. Alle vier Honigzonen besitzen jetzt helle Eckmarkierungen fuer die Vorwarnung. Die Bruecke verwendet unveraenderte Weltmasse und braucht keinen kuenstlichen Vergroesserungsfaktor.

## Runde 2

Grafik arbeitet an `v4_r2_surfaces.py`, `v4_r2_review.py`, `v4_r2_fx.py`, `blender/v4_r2_palette.py`, `floor_geo.py`, `blender/floor_build.py` und Grafikassets. Keine Aenderung an Layout, C# oder maptest. Wandmontierte Ausstattung bleibt innerhalb der vorhandenen Wachsmasse. Teppiche, Gitter und Wegmarken sind flach.

### An Layout

Fuer deutlich mehr glaubwuerdige Ausstattung bitte folgende zusaetzliche vorhandene Props samt echter Kollision pruefen und bei Eignung in hive_layout.py aufnehmen. Koordinaten sind Vorschlaege; Konsolen haben Vorrang. Nicht blind aufnehmen, bei Konflikt verschieben oder ablehnen. Grafik baut diese Objekte nicht eigenmaechtig ein.

| Raum | Art | gewuenschte Grundflaeche | Modus |
|---|---|---|---|
| Sun Deck | flower_pots | rect -13.5,22.0,-13.0,23.0 | glass |
| Sun Deck | mead_table | rect -11.3,21.7,-9.7,22.6 | glass |
| Drone Dock | crate_stack | rect 12.1,21.6,13.3,22.4 | glass |
| Royal Archive | bookshelf | rect -3.6,24.3,-1.2,24.8 | opaque |
| Mead Hall | mead_table | rect -3.8,7.5,-2.2,8.4 | glass |
| Mead Hall | mead_table | rect 2.2,7.5,3.8,8.4 | glass |
| Keeper's Office | jar_shelf | rect 6.5,8.8,7.7,9.3 | opaque |
| Jar Cellar | jar_shelf | rect -10.3,4.4,-7.1,4.9 | opaque |
| Brood Nursery | royal_cells | rect 6.1,-5.1,7.5,-4.3 | glass |
| West Press | honey_barrels | rect -19.3,-10.2,-18.3,-8.5 | glass |
| East Press | honey_barrels | rect 18.4,-10.2,19.4,-8.5 | glass |

### An Life oder Layout: Honigfluss

Grafik liefert `art/fx/task_hive_flow_0.png` bis `_7.png` als transparente animierte Glanzlagen einer eingelassenen Rinne, identische Groesse 600 x 64 Pixel, native Breite 6 m, Hoehe 0.64 m, 100 ppm, Pivot Mitte. Statische Rohrfassung wird im Boden integriert. Zwei gerade Rinnen: West Mittelpunkt (-8.6,0.82), Ost (8.6,0.82), jeweils Laenge 6.0 m. West fliesst nach Osten (Rotation 0), Ost nach Westen (Rotation 180 Grad). Bilder mit 8 fps in normaler Welt-Sichtmaske abspielen; keine Lichter oder spielerspezifischen Informationen. Z nur knapp ueber dem Boden, unter Figuren. Koordinaten werden in `art/fx/honey_r2_contract.json` geliefert.

Zusaetzlich `task_hive_drip_0.png` bis `_7.png`: 64 x 160 Pixel, 100 ppm, Pivot Mitte, 8 fps. Gewuenschte drei Tropfstellen an bestehenden Nordwaenden, Bildmitten (-11.3,1.45), (11.3,1.45), (0.9,-5.9). Tropfen rein optisch, keine Kollision und keine Verlangsamung. Exakte Positionen und Projektionsvertrag in derselben JSON. Assets gelangen durch build --art automatisch nach assets/amberhive. Bitte Umsetzung oder verbleibenden offenen Punkt in dieser Datei rueckmelden.

### Grafikstatus Runde 2

Die 16 PNGs und `art/fx/honey_r2_contract.json` liegen jetzt vor. `python tools/hive/v4_r2_fx.py` reproduziert sie. Beide Sequenzen haben acht Frames mit festem Anker; Kontaktboegen und GIFs in `_v4/r2/flow_frames.png`, `drip_frames.png`, `flow.gif`, `drip.gif`. Bitte die angekuendigte rein optische Einbindung jetzt vornehmen.

Rueckmeldung an Layout gelesen: neun reale Stellobjekte akzeptiert, zwei konflikttraechtige Regale abgelehnt. Die Ablehnungen sind sinnvoll. Grafik baut hier keine Ersatzkollision ein. Wandregale umgehen automatisch Konsolen beider Fassungen und vorhandene Propgrundflaechen. Letzter Durchgang erfolgt nach erneutem Einlesen des Layouts.

### Baukoordination Grafik

Der bereits laufende dritte Grafikbau ist jetzt fertig: `build --art` erfolgreich, 48 Props, 208 Konsolenreferenzen, keine fehlenden Bilder, Wandhoehe 1.85. Ab jetzt kein weiterer Assetbau durch Grafik waehrend der abschliessenden Gameplay-Tests. Es folgen nur lesende Assetpruefung, Vorschaubilder und Bericht. Der voruebergehend fehlende Bodensatz beim zweiten Vorschaulauf kam durch gleichzeitigen Neubau; die Vorschau wurde danach neu erzeugt.

### Abschluss Grafik Runde 2

Alle Grafiken und Vergleiche sind fertig. Siehe Abschnitt Runde 2 in `V4_BERICHT_GRAFIK.md`. Abschliessender Assetbau erfolgreich, anschliessend nur noch Vorschau und Pruefdateien erzeugt. `r2_pruefung.json`: 0 Fehler, beide Karten mit fuenf vertragsgleichen Honigschleifen, 41 Wandmodule, 30 Wandleuchten, feste Frameanker. Finale Bilder in `_v4/r2/karte_2f.png`, `vergleich_karte.png`, `vergleich_krone.png`, `vergleich_gang_waben.png`.

Grafik-Wandhoehe ist nun 1.85 m. Spielkollision bleibt unveraendert. Bitte die Sichtbarkeit der Wandausstattung, Rinnen, Tropfen und Spieler an den Nordwaenden in den ohnehin laufenden Tests kontrollieren. Grafik startet Among Us nicht und baut waehrend eurer Tests keine Assets mehr neu.

## Runde 3

Die neue Grafikrunde wurde vom Auftraggeber beauftragt. Grafik bearbeitet ausschliesslich diese Arbeitskopie, keine C#-Dateien und startet Among Us nicht. Assetbau erfolgt mit `gen_hive.py build --art`; waehrend eines Baus kann der gepackte Kartensatz kurz unvollstaendig sein. Fuer den Mehrspielertest bitte erst den hier dokumentierten abgeschlossenen finalen Bau verwenden.

Neue echte Kollisionen: Wachsliege auf Sun Deck, niedrige Drohnen-Werkbank im Drone Dock, niedriges Schriftrollenmoebel im Royal Archive und je ein Filterkorb in West Press und East Press. Die abgelehnten Suedregale aus Runde 2 bleiben verworfen. Konsolen und Vents behalten ihre bisherigen Koordinaten.

Im Spiel bitte pruefen:

- Bei normaler und kleiner Sichtweite Figuren und Leichen vor neuen Wandfaechern, Schriftrollen, ruhenden Drohnenbienen und Presskoerben erkennen. Die statischen Bienen auf der Werkbank sind Dekoration und sollen nicht wie Spieler oder aktive Aufgaben wirken.
- Vor und hinter den fuenf neuen niedrigen Props laufen, Leichen dort melden und richtige Tiefensortierung beim Vorbeigehen pruefen. Nur diese Stellobjekte bekommen neue Kollision; Bodenzeichnungen und Wandmontagen bleiben frei.
- Alle Aufgaben, beide Kronenvents, drei Treppen und die Rutsche weiterhin bedienen. Besonders Treppe im Drone Dock und Vent neben der Wachsliege auf Sun Deck kontrollieren.
- Keeper's Office zu Waggle Studio, Queen's Chamber zu Sun Compass sowie West Press zu Wasp Watch in beiden Richtungen durchlaufen. Rinnen, Wandfronten und Farbstreifen muessen an den Anschluessen lueckenlos aussehen, Tueren und Flutvorwarnung muessen lesbar bleiben.
- Guard-Comb-Beobachtungsplan und Lamphouse-Pruefringe sind statische Dekoration. Sie duerfen nicht als benutzbare Konsole missverstanden werden. Echte Konsolen behalten ihre kraeftigere Silhouette.
- Bei Glow Fade, Pollen und wechselndem Sonnenlicht den Bodenkontrast sowie Sichtmasken an den neuen Wanddetails pruefen. Offline-Bilder enthalten keine Unity-Sichtmaske.

Bildbelege nach finalem Bau: `_v4/r3/nachher/spielzoom_kontakt.png`, einzelne `zoom_*.png` und `lesbarkeit_*.png` im selben Ordner. Lesbarkeitsmarker sind eigene schematische Zeichnungen, keine Spielaufnahmen.

### Abschluss Runde 3

Der finale Assetbau ist abgeschlossen. Keine weiteren Grafikbauten vorgesehen. Beide Varianten haben 0 gemeldete Layoutprobleme, 53 beziehungsweise 35 Props und keine fehlenden Bilder. `r3_pruefung.json` meldet 0 Fehler. Alle 20 Navigationsszenarien und ihre erfassten Wegwerte stimmen exakt mit der gesicherten Basis aus `_out/v4_navigation.json` überein. Konsolen, Vents, Treppen, Türen und Bewegungswände sind unverändert.

Endgültige neue Grundflächen in Weltmetern:

| Objekt | Grundfläche | Fassung |
|---|---|---|
| Wachsliege | rect -13.1,24.1,-12.4,25.45 | 2 Etagen |
| Drohnen-Werkbank | rect 12.1,24.1,13.5,24.75 | 2 Etagen |
| Schriftrollenarchiv | rect 1.4,20.5,3.0,20.95 | 2 Etagen |
| Filterkorb West | rect -16.7,-10.3,-15.7,-9.65 | beide |
| Filterkorb Ost | rect 15.5,-10.4,16.5,-9.75 | beide |

Zusätzlicher Spielprüfpunkt: Die grafische Vorderwand an West Press zu Wasp Watch und Queen zu Sun ist nun lokal niedriger, damit die Schrägprojektion den Gang nicht überdeckt. Die unveränderte Unity-Sichtkollision kann sich anders verhalten als diese statische Grafik. Bitte Figuren und Leichen an den beiden Schultern, hinter den niedrigen Wänden und unmittelbar an den Türen prüfen. Alle 30 Offline-Ansichten und Farbkontrastproben sind fertig; sie simulieren keine Verdeckung durch Vordergrundobjekte.

Abschließender Ausbau: Fünf größere Wandmotive oberhalb der Konsolen ergänzen die kleinen Module in Sun Deck, Drone Dock, Jar Cellar, Guard Comb und Lamphouse. Bitte Ressourcen für den Spieltest aus dem vollständigen aktuellen Paket neu bauen beziehungsweise laden. Die alten Bildstände vor dem letzten Bau enthalten diese Motive noch nicht. Die Zahl und Position der fünf neuen kollidierenden Props bleiben gleich.
