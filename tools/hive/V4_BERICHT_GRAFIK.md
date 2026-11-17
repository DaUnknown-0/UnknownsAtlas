# Grafikbericht Amberhive V4

## Ergebnis

Die aktive Fable-Fassung wurde gezielt weiterentwickelt. Neue Oberflaechen, Wanddetails, Honigtechnik und zwei verfeinerte Kinoszenen sind im Kartenpaket eingebaut. Alle neuen Motive sind prozedural oder in Blender entstanden.

## Konkrete Schwaechen und Aenderungen

- Vorher: laute, gleichmaessige Waben ausserhalb der Raeume. Jetzt: toniger Propolishintergrund, kleine Moospolster mit einzelnen Blaettern, Wachsrippen und dunkle Messingfassungen.
- Vorher: grosse Fliesenfelder ohne klare Hierarchie. Jetzt: umlaufende Intarsien, ruhigerer Fliederbelag, eigener Thronlaeufer mit Bienenwappen, Archivmedaillon, botanische Bodenzeichnungen und Landemarkierung am Drone Dock.
- Technikraeume haben eingelassene Arbeitsfelder, Abflussgitter und Richtungskerben. Im Lamphouse ergaenzt ein dezentes Wabenschaltbild die freie Arbeitsflaeche.
- Vorher: Honigsee aus harten Farbringen. Jetzt: stetiger Bernsteinverlauf ueber Vertexfarben, dunkler Meniskus, asymmetrische Spiegelung, feine Schlieren, Blasen und segmentierter erhoehter Wachsrand mit Nieten.
- Bruecke: petrolfarbene Einfassung, verschraubte Holzdielen, einzelne Gebrauchsspuren und Einlaufmarken. Weltmasse und Drehvertrag bleiben erhalten.
- Biene: neuer segmentierter Koerper, zwei Fluegelpaare, sechs Beine und Fuehler. Beide Fluegelbilder besitzen identische Bildgrenzen und Anker. Das bisherige Huepfen durch unterschiedliche Frameanker entfaellt.
- Honigflut: alle vier Zonen neu gerendert, helle Eckmarken fuer die Vorwarnung. Zone 2 entspricht der neuen Westverbindung bei [-19.0, 3.2, -17.2, 7.1].
- Skip Sonnendeck: Abendhimmel von Pfirsich bis Mauve, warme Wolken, Streiflicht, Messingdetails, Rankgitter und eigene sanft pendelnde Rankenebene.
- Rauswurf Honigbrunnen: Manometer und genietete Wartungsklappen. Die bereits vorhandene echte Brueckendrehung mit 19 Winkelbildern bleibt erhalten.
- Schwarm-Rauswurf und Koenigin-Skip sowie die vorhandenen Konsolen, Tueren, Vents und 31 Fable-Requisiten wurden beibehalten und auf vollstaendige Einbindung geprueft. Kein pauschaler Austausch funktionierender Motive.

## Vorher und Nachher

Alle folgenden Pfade liegen relativ zur Arbeitskopie `UnknownsAtlas_AmberhiveV4`:

| Motiv | Vorher | Nachher |
|---|---|---|
| Karte mit Krone | `tools/hive/_v4/before/karte_2f.png` | `tools/hive/_v4/after/karte_2f.png` |
| Honigbrunnen | `tools/hive/_v4/before/brunnen.png` | `tools/hive/_v4/after/brunnen.png` |
| Thronsaal | `tools/hive/_v4/before/thronsaal.png` | `tools/hive/_v4/after/thronsaal.png` |
| Sonnendeck-Skip | `tools/hive/_v4/before/hive_skip_sundeck_kontakt.png` | `tools/hive/_v4/after/hive_skip_sundeck_kontakt.png` |
| Brunnen-Rauswurf | `tools/hive/_v4/before/hive_well_kontakt.png` | `tools/hive/_v4/after/hive_well_kontakt.png` |

Direkte Vergleichsboegen: `tools/hive/_v4/after/vergleich_brunnen_thron.png`, `tools/hive/_v4/after/vergleich_sonnendeck.png`, `tools/hive/_v4/after/bienen_frames.png`.

Weitere Detailbilder: `tools/hive/_v4/after/lampenhaus.png`, `tools/hive/_v4/after/archiv.png`, `tools/hive/_v4/after/karte_1f.png`.

Animationen: `tools/hive/_v4/after/biene.gif`, `tools/hive/_v4/after/sonnendeck_animation.gif`. Die Kino-Vorschau zeigt Keyframes und Ebenen mit Kameraumrandung; Partikel und Spieltext fehlen dort.

## Geaenderte Quellen und Reproduktion

- Boden: `tools/hive/floor_geo.py`, neu `tools/hive/v4_surfaces.py`, `tools/hive/blender/floor_build.py`, neu `tools/hive/blender/v4_palette.py`.
- Laufzeitgrafik: `tools/hive/fx_geo.py`, `tools/hive/blender/fx_build.py`, neu `tools/hive/blender/bee_v4.py`.
- Kino: `tools/hive/blender/eject_sundeck.py`, `tools/hive/blender/eject_well.py`, neu `tools/hive/blender/eject_v4_details.py`, `tools/eject_scenes.py`.
- Vorschau: `tools/hive/preview_hive.py`, neu `tools/hive/v4_review.py`. Gemeinsames Runden der Kachelecken beseitigt bei nichtganzzahligem Vorschaufaktor schwarze 1-Pixel-Naehte.
- Stilregeln: `tools/hive/art/STIL_V4.md`. Gameplay-Uebergabe: `tools/hive/V4_WUENSCHE_GRAFIK.md`.
- Ausgabe: `assets/amberhive/amberhive_floor_*.jpg`, die gepackten Kartenbilder und Karten-JSONs, `tools/hive/art/fx`, `assets/amberhive/task_hive_*`, `assets/amberhive/task_eject_hive_*`, `assets/eject_scenes.json`.

Aus dem Kopieordner:

1. `python tools/hive/fx_geo.py`, danach Blender headless mit `-P tools/hive/blender/fx_build.py -- <absoluter Pfad zu tools/hive/art/fx>`.
2. Blender headless jeweils mit `-P tools/hive/blender/eject_sundeck.py` und `-P tools/hive/blender/eject_well.py`.
3. `python tools/eject_scenes.py --amberhive-only` und `python tools/hive/blender/eject_kontakt.py`.
4. `python tools/hive/gen_hive.py build --art`.
5. `python tools/hive/preview_hive.py 2 44` und `python tools/hive/v4_review.py --animation`. Die gespeicherten Vergleichsboegen verwenden zusaetzlich die dokumentierten Detailausschnitte.

Der Szenengenerator hat jetzt einen Amberhive-Modus, der andere Szenen unveraendert uebernimmt. Die normale UC-Nebenausgabe wird unterdrueckt, wenn ihr Ziel ausserhalb dieser Arbeitskopie liegt. `gen_hive.py` verwendet bereits relative Projektpfade und wurde von mir nicht bearbeitet.

## Pruefung und Grenzen

- Mehrere Boden- und Detailrender kritisch angesehen, danach Moosformen, Bildanker und Vorschaukacheln korrigiert. Der letzte Lamphouse-Feinschliff wurde erneut gerendert.
- Letzter `build --art`: beide Etagen ohne gemeldete Layoutprobleme, 39 Requisitenplatzierungen, keine fehlenden Propbilder, 208 Konsolenreferenzen aus 90 eindeutigen Bildern, keine fehlenden Konsolenbilder.
- Python-Syntaxpruefung aller 13 geaenderten oder neuen Python-Quellen erfolgreich.
- `asset_pruefung.json`: 31 Requisitenarten, 23 bestehende animierte Propframes, identische Bienenanker, vier Amberhive-Szenen, keine Fehler.
- Andere Kinoszenen wurden mit dem unveraenderten Ausgangsprojekt verglichen. Ergebnis in `tools/hive/_v4/after/fremdszenen_pruefung.json`.
- Kein Among Us gestartet. Sichtmaske, Sabotagenlicht, Vorwarnung der Flut und neue Rankenressource muessen vom Gameplay-Agent im Spiel geprueft werden.
- Die Masse und Kollisionen stammen weiter ausschliesslich aus der Layoutquelle. `hive_layout.py`, `src/*.cs` und `maptest*` wurden von mir nicht bearbeitet. Kein Commit, Push oder Tag.
- Ein frueher FX-Aufruf loeste einen relativen Ausgabepfad unter `C:/tools/hive/art/fx` auf. Die neun erzeugten Bildsaetze wurden in die Arbeitskopie verschoben und die dadurch leeren Verzeichnisse bereinigt. Die Pipeline loest relative FX-Ziele inzwischen gegen den Kopieordner auf.
- Bewusste offene Ausbaustufe: separat animierte Kerzen und Wandtropfen benoetigen einen zusaetzlichen Laufzeitvertrag. Aktuell wurden die bereits eingebundenen Maschinenanimationen erhalten.

## Runde 2

### Ziel und Ausgangsbefund

Der zweite Durchgang vergroessert die Ausstattung und die raeumliche Tiefe sichtbar. Ausgang fuer alle Vergleiche ist unveraendert `tools/hive/_v4/after/karte_2f.png`. Die Befundliste wurde vor der Umsetzung mit sieben Ausschnitten angelegt: [Befund Runde 2](_v4/r2/BEFUND.md). Sie benennt insbesondere die leere Krone, fehlende Funktionsspuren in Buero, Keller und Nursery, isolierte Pressen, gleichfoermige Aussenwaben und schwache Gangorientierung.

### Umgesetzt

- **Ausstattung:** 41 wandmontierte Module mit Honig- und Becherregalen, Akten und Buechern, Brutfaechern, botanischen Faechern und Werkzeugen. Die Module sitzen auf bestehenden Wandfronten. Kleine vorstehende Regalbretter geben ihnen plastische Tiefe, der Wandfuss bleibt erkennbar. Konsolen beider Etagenfassungen und bestehende Propgrundflaechen werden bei der Platzierung ausgespart.
- **Echte Stellobjekte:** Nach konkreter Uebergabe in `V4_WUENSCHE_GRAFIK.md` hat der Layout-Agent neun vorhandene Props samt Kollision eingebaut: Tisch und Pflanzen auf dem Sun Deck, Kisten im Drone Dock, ein zusaetzliches Archivmoebel, zwei Tische in der Mead Hall, Brutwaben in der Nursery und Fassgruppen in beiden Pressen. Zwei konflikttraechtige Regale wurden gemeinsam verworfen. Vent 6 wurde vom Layout-Agenten neben den neuen Westtisch verschoben. Die Grafik hat keine Kollisions- oder Layoutdatei bearbeitet.
- **Wandtiefe:** Hoehe von 1.40 auf 1.85 m angehoben, entsprechend rund 1.09 m sichtbarer Vorderseite bei Scherung 0.59. Gestaffelter dunkler Sockel, geteilte Holz-, Salbei-, Pflaumen- und Blaupaneele, obere Metallfassung, Wachskragen und sichtbare Ablageoberseiten. Auch die oberen schraegen Raumflanken tragen Paneele.
- **Honigtechnik:** Zwei eingelassene, eingefasste Rinnen in den Hauptgaengen, mit Verbindungen zum oberen Brunnenrand. Acht prozedurale Glanzframes je Stroemung und acht Tropfenframes mit Wachstum, Abloesung, Fall und flachem Spritzer. Der Layout-Agent hat zwei Stroemungen und drei versetzte Tropfstellen als optische Schleifen mit 100 ppm, mittigem Pivot und 8 fps eingebunden. Beide Karten-JSONs enthalten alle fuenf Schleifen. Normale Sichtmaske, unter Figuren, keine neue Kollision und kein Gameplayeffekt.
- **Aussenstock:** 1583 einzeln aufgebaute Zellen in raeumlich zusammenhaengenden Gruppen. Versenkte offene Kerne, gedeckelte Wachsflaechen, koernige Pollenfuellungen, dunklere Honigmenisken, sparsame Reflexe und verzweigte Wachsnarben ersetzen das gleichmaessige Muster mit zufaelligen Volllichtern. Die endgueltigen Farben wurden nach dem ersten Render deutlich abgedunkelt.
- **Licht:** 30 kleine wandmontierte Laternen mit weichen warmen Lichtpfuetzen, leichte kontinuierliche Randabdunklung in allen 17 Raeumen und weiches diagonales Abendlicht in den drei Kronenraeumen. Die statische Farbgestaltung veraendert keine Sicht- oder Sabotageradien. Die bewegte Sonne und reaktiven Lampen bleiben beim Life-Agenten.
- **Boeden und Orientierung:** Flache gewebte Teppiche passend zu Aufenthalt, Archiv, Lager und Pflege; dezent eingezeichnete Packmarken. Westfluegel in gedaempftem Petrol mit zwei Kerben, Ostfluegel in Tonrot mit drei Kerben, Krone in Flieder. Farbstreifen folgen ausschliesslich echten Gangwaenden und zeichnen keine zusaetzlichen Hindernisse quer durch Oeffnungen.

### Renderkontrolle und Korrekturen

1. `schritt_1_karte.png`: Ausstattung, Wandpaneele, Rinnen und Aussenstock erstmals gemeinsam gerendert. Kritische Pruefung: Aussenstock zu kontrastreich; rechteckige Teppiche ueberlagerten Archivwappen und vorhandene Raumteppiche.
2. `schritt_2_karte.png`: Aussenfarben reduziert, Archivmotiv in einen einzigen groesseren Leseteppich integriert, Mead-Hall-Teppich nur mit Webdetails verfeinert und Buero-Laeufer seitlich versetzt. Neun abgestimmte Stellobjekte, Licht und Vignetten sind enthalten. Beide Etagenfassungen bei der Wandbelegung beruecksichtigt.
3. `schritt_3_karte.png`: Wandhoehe angehoben, sichtbare Regalbretter ergaenzt, Gangstreifen von offenen Raumanschluessen entfernt. Endgueltige Ein- und Zwei-Etagen-Vorschau sowie Kronen-, Nursery- und Gangdetails kritisch angesehen. Konsolen und Vents bleiben als eigene kraeftige Motive lesbar; breite Mittelwege bleiben ruhig.

Ein Vorschaulauf traf kurzzeitig auf einen parallel neu gebauten Bodensatz und wurde verworfen. Die Vorschau wurde nach abgeschlossenem Bau erneut erzeugt. Anschliessend wurde mit dem Layout-Agenten eine Baupause fuer dessen abschliessende Spieltests abgestimmt. Der abschliessend gepruefte Layout-Hash ist `ca316507fa13ba13e41f3f43aadf172cd85c70b8df4031a2db7f65cb0abe9bff`.

### Bilder und Vergleiche

Alle Pfade relativ zu `tools/hive/`:

| Motiv | Vorher | Nachher oder Vergleich |
|---|---|---|
| Gesamtkarte, zwei Etagen | `_v4/after/karte_2f.png` | `_v4/r2/karte_2f.png`, `_v4/r2/vergleich_karte.png` |
| Gesamtkarte, eine Etage | `_v4/after/karte_1f.png` | `_v4/r2/karte_1f.png` |
| Drei Kronenraeume | `_v4/r2/vorher_krone.png` | `_v4/r2/vergleich_krone.png` |
| Mead Hall | `_v4/r2/vorher_mead.png` | `_v4/r2/vergleich_mead.png` |
| Buero und Keller | `_v4/r2/vorher_buero_keller.png` | `_v4/r2/vergleich_buero_keller.png` |
| Brutpflege | `_v4/r2/vorher_nursery.png` | `_v4/r2/vergleich_nursery.png` |
| West Press | `_v4/r2/vorher_presse.png` | `_v4/r2/vergleich_presse.png` |
| Wand, Gang und Aussenstock | `_v4/r2/vorher_gang_waben.png` | `_v4/r2/vergleich_gang_waben.png` |
| Thron | `_v4/r2/vorher_thron.png` | `_v4/r2/vergleich_thron.png` |

Animationen: `_v4/r2/flow.gif`, `_v4/r2/drip.gif`, `_v4/r2/honigfluss_kontext.gif`. Kontaktboegen: `_v4/r2/flow_frames.png`, `_v4/r2/drip_frames.png`. Die Kontextanimation ist eine Offline-Komposition nach dem uebergebenen Vertrag, kein Nachweis der Unity-Laufzeit.

### Quellen und Reproduktion

Eigene neue Quellen:

- `tools/hive/v4_r2_surfaces.py`: Ausstattung, Stock, Teppiche, Lichtdaten und Wegsaeume.
- `tools/hive/blender/v4_r2_palette.py`: zurueckhaltende Farben fuer Zellen, Paneele und Arbeitsbereiche.
- `tools/hive/v4_r2_fx.py`: 16 registrierte Animationsframes und `art/fx/honey_r2_contract.json`.
- `tools/hive/v4_r2_review.py`: Befundausschnitte, Vergleiche und Kontextanimation.
- `tools/hive/v4_r2_check.py`: Asset-, Frame-, Anker- und exportierte Schleifenvertraege.

Eigene geaenderte Quellen: `tools/hive/floor_geo.py`, `tools/hive/blender/floor_build.py`. Dazu diese Dokumentation, Stilregeln und Wunschdatei. Generierte Grafikassets liegen in `tools/hive/art/fx/` und `assets/amberhive/`. Die vom Layout-Agenten geaenderten Dateien `hive_layout.py`, `gen_hive.py` und `src/AtlasAmberhive.cs` werden hier nur als integrierte Abhaengigkeiten genannt.

Reproduktion aus der erlaubten Arbeitskopie, Assetbau mit anderen Agenten koordinieren:

```text
python tools/hive/v4_r2_fx.py
python tools/hive/gen_hive.py build --art
python tools/hive/v4_r2_check.py
python tools/hive/preview_hive.py 1 44
python tools/hive/preview_hive.py 2 44
python tools/hive/v4_r2_review.py --after
```

### Pruefungen und Grenzen

- Drei vollstaendige Grafikbauten mit `build --art` und anschliessenden Renderkontrollen. Letzter Bau: beide Varianten mit 0 gemeldeten Layoutproblemen; 48 Props in der Zwei-Etagen-Fassung, 33 in der Ein-Etagen-Fassung; 208 Konsolenreferenzen aus 90 eindeutigen Bildern; keine fehlenden Prop- oder Konsolenbilder.
- Python-Syntaxpruefung aller sieben eigenen neuen oder geaenderten Python-Dateien erfolgreich.
- Bestehende Assetpruefung ohne Fehler: 31 Prop-Arten, 23 vorhandene animierte Propframes, identische Bienenanker, vier vollstaendige Amberhive-Kinoszenen.
- Runde-2-Pruefung ohne Fehler: 16 verschiedene neue RGBA-Frames, feste Bildgroessen und mittige Anker, 100 ppm, bytegleich im Kartenpaket; 41 Wandmodule, 30 Wandleuchten, 17 Raumvignetten und fuenf korrekt exportierte Honigschleifen pro Kartenfassung. Ergebnisse: `_v4/r2/asset_pruefung.json` und `_v4/r2/r2_pruefung.json`.
- Keine Among-Us-Spieltexturen verwendet. Die Grafiken sind ausschliesslich prozedural bzw. in Blender entstanden.
- Among Us durch Grafik nicht gestartet. Reale Spieler-, Leichen- und Sichtmaskenlesbarkeit sowie Sabotagenlicht bleiben im Spiel abzunehmen. Die Offline-Vorschau enthaelt keine Spieler und keine Unity-Sichtmaske. Laufzeit- und Spieltests anderer Agenten werden in deren Berichten dokumentiert.
- Keine fremden Quelldateien bearbeitet, keine eigene Kollision hinzugefuegt, keine Schreibzugriffe ausserhalb der Arbeitskopie. Kein Commit, Push oder Tag. Keine eigenen Subagents gestartet.

## Runde 3

### Ergebnis und Ausgangsbefund

Die acht kritisierten Räume haben zusätzliche Funktionsspuren und spezialisierte Wandausstattung. Fünf sparsam gesetzte Stellobjekte ergänzen den Bestand. Alle drei geänderten Verbindungen sind fertig ausgearbeitet und die beiden südlichen Engstellen grafisch freigelegt. Der vollständige Endstand liegt in `_v4/r3/karte_2f.png` und `_v4/r3/karte_1f.png`.

Vor der Umsetzung wurden die aktuellen Paketbilder mit dem fertigen Grundriss und 48 Props gesichert. Die Schwächenliste mit Bildverweisen steht in [_v4/r3/BEFUND.md](_v4/r3/BEFUND.md). Damit vergleicht Runde 3 denselben fertigen Grundriss vor und nach der Grafikarbeit. Der historische Runde-2-Vergleich wurde erhalten.

### Ausstattung und Raumfunktion

- **West Press und East Press:** Je ein neuer niedriger Filterkorb mit echter Kollision, herausgezogenem Wabenrahmen, eingefasste Sammelrinnen, flache Trittstege, matte Wachsreste und Drucktafeln. Die vorhandenen Fassgruppen und Maschinen bleiben die großen Silhouetten.
- **Sun Deck:** Neue Wachsliege mit echter Kollision und Stoffbahn. Drei Wandmodule zeigen bepflanzte Tröge mit Blüten und ein an die Wand gefaltetes Sonnensegel. Botanische Umrissintarsien ergänzen Teleskop, Bewässerung und Sitzgruppe. Der Vent bleibt frei.
- **Royal Archive:** Neues niedriges Schriftrollenmöbel mit echter Kollision, zehn hohlen Wabenfächern und sichtbaren Rollenmündern. Drei Wandmodule tragen gerollte Archivbestände. Leise Katalogstriche begleiten die Raumränder; Wappen und mittlere Laufzone bleiben lesbar.
- **Drone Dock:** Neue niedrige Werkzeugbank mit echter Kollision, zwei ruhenden Drohnenbienen, Schraubenschlüssel und Arbeitsblatt. Flache sechseckige Landezone um die vorhandene Station, Markierungen am Anflug und spezialisierte Werkzeugwände. Die Bank steht rechts am Rand, außerhalb des Treppen-Ausweichwegs und neben dem freien Vent.
- **Jar Cellar:** Voll belegte Gläserfächer mit Etiketten, Inventarzeichen und schmale Fassrollspuren. Die vorhandenen großen Glasregale und Fässer bleiben erhalten. Kein zusätzliches Regal im abgelehnten südlichen Engpass.
- **Guard Comb:** Schild- und Beobachtungsplanmodule, dazu eine matte Bodenintarsie mit vier Beobachtungsposten. Die Raummitte bleibt eine freie, gut erkennbare Besprechungsfläche.
- **Lamphouse:** Ersatzteil- und Anzeigenfächer, ein zusammenhängendes Prüfringdiagramm mit Leiterbahnen. Das ältere überlagerte Schema wurde entfernt.

Vier neue Prop-Arten ergeben fünf zusätzliche Platzierungen. Die Zwei-Etagen-Fassung enthält jetzt 53 Props, die Ein-Etagen-Fassung 35. Alle fünf neuen Grundflächen sind ausdrücklich als `glass` kollidierend eingetragen. Die 40 automatisch belegten Wandmodule bleiben erhalten; 19 davon haben spezialisierte Inhalte. Zwei kompakte Drucktafeln nutzen bisher zu kurze Wandstücke. Zusammen sind 21 spezialisierte Wandbelegungen dokumentiert. Fünf größere Wandmotive ergänzen die Raumerzählung oberhalb der Konsolen: Sonnensegel und Pflanztröge auf Sun Deck, Ersatzflügel und Werkzeug im Dock, Gläservorräte an der schrägen Kellerwand, Schutzschild und Stockplan im Guard Comb sowie Ersatzlampen und Wartungsstromkreis im Lamphouse. Weitere Dekoration dieses Durchgangs ist flach oder an bestehenden Wänden montiert.

### Verbindungen und eigene Korrekturen

Keeper zu Waggle, Queen zu Sun und West Press zu Wasp haben eingefasste statische Rinnen, Querstege und Formkerben. Die bestehenden Farbsäume und Wandpaneele folgen dem fertigen Gangpolygon. Die fünf animierten Honigschleifen aus Runde 2 bleiben vertragsgleich.

Eine zusätzliche Schwäche wurde erst im Spielzoom deutlich: Die 1.85 m hohe grafische Vorderwand schob sich durch die Scherung über den West-Wasp-Gang und einen Teil der Queen-Sun-Verbindung. Dort ist die grafische Vorderwand jetzt lokal auf ein Viertel der Höhe abgesenkt. Wandkragen, Wabenzellen und Moos werden gemeinsam abgesenkt. Die Schultern behalten einen sichtbaren Höhenwechsel. Die Bewegungskollision und die Unity-Sichtgrenze wurden nicht geändert. Die Rinnen liegen nun an der sichtbaren Nordseite.

Botanische Flächen wurden nach dem ersten Render in feinere Umrisse umgearbeitet. Weniger, gedämpftere Blüten verringern helle Kleinteile auf Laufwegen. Der Filterkorb bekam einen sichtbaren gezogenen Rahmen; geschlossene Archivwaben wurden zu tatsächlich hohlen Schalen.

### Renderdurchgänge und Spielzoom

1. `schritt_1/`: Erster vollständiger Bau und 23 Ausschnitte. Befunde: verdeckte Südgänge, zu kräftige Blatteinlagen, leere Korbanmutung und schlecht sichtbare Rollenmünder. Zwei neue Möbel verlängerten außerdem den Cafeteria-Ausweichweg durch die Krone von 23.11 auf 23.55 m.
2. `schritt_2/`: Werkbank an den rechten Dockrand versetzt, Schriftrollenmöbel erneut auf mehrere Randpositionen geprüft. Vorderwände abgesenkt, Rinnen nach Norden verschoben, Drucktafeln und gezogenen Filterrahmen ergänzt. Die abgelehnten Positionen bleiben nur in den Zwischenbildern.
3. Dritter Bau: Endgültige Archivposition im Südosten ohne Verlängerung des Ausweichwegs, hohle Schriftrollenfächer.
4. Vierter Bau: Doppeltes Lampenschema entfernt und Blüten beruhigt. Beide vollständigen Karten und alle Ausschnitte neu erzeugt und kritisch angesehen.
5. Finaler Bau: Die zusätzlichen Nordwandansichten zeigten, dass kleine Details teilweise hinter Konsolen verschwanden. Fünf größere Wandmotive ergänzt und den letzten vollständigen Paketstand erneut geprüft. Die Arbeit wurde nach einer Unterbrechung anhand der gespeicherten Quellen, Bauprotokolle und Bildstände fortgesetzt. Ein Prüflauf traf auf den kurzzeitig unvollständigen Bodensatz eines parallelen Assetbaus; die endgültige Prüfung und Vorschau wurden nach dessen Abschluss erneut ausgeführt.

Die endgültige Prüfung enthält **30 Positionen**, darunter alle 17 Räume, die drei geänderten Verbindungen, beide Hauptgänge, Brunnen und zusätzliche Nordwandansichten. Jeder Ausschnitt ist 1920 x 1080 Pixel groß, mit dokumentierter angenommener Sichtfläche von 10.5 x 5.90625 Weltmetern. Die Gesamtbilder zeigen die vorhandenen Konsolen-, Vent-, Tür- und Kamerasprites aus dem Paket.

Die ergänzenden `lesbarkeit_*.png` enthalten eigene schematische Figuren- und Leichenmarker als Farbkontrastprobe. Auf den ruhigen Mittelflächen bleiben beide Silhouetten gegenüber Bodenzeichnungen deutlich. Diese Marker werden über das Bild gezeichnet. Sie simulieren keine Figurensortierung, Unity-Sichtmaske, Sabotagenbeleuchtung oder echte Verdeckung durch Möbel. Entsprechende Spielprüfungen stehen im Abschnitt Runde 3 von `V4_WUENSCHE_GRAFIK.md`.

### Wichtigste Bilder

Alle Pfade relativ zu `tools/hive/`:

| Motiv | Bild |
|---|---|
| Gesamtvergleich | `_v4/r3/vergleich_karte.png` |
| Neue Gesamtkarte | `_v4/r3/karte_2f.png` |
| Ein-Etagen-Karte | `_v4/r3/karte_1f.png` |
| Alle 30 Spielzoom-Ansichten | `_v4/r3/nachher/spielzoom_kontakt.png` |
| Vorher im Spielzoom | `_v4/r3/vorher/spielzoom_kontakt.png` |
| Pressen | `_v4/r3/vergleich_west_press.png`, `_v4/r3/vergleich_east_press.png` |
| Krone | `_v4/r3/vergleich_sun_deck.png`, `_v4/r3/vergleich_archive_sued.png`, `_v4/r3/vergleich_drone_dock.png` |
| Wandausstattung | `_v4/r3/vergleich_cellar_nord.png`, `_v4/r3/vergleich_guard_nord.png`, `_v4/r3/vergleich_lamp_nord.png` |
| Neue Verbindungen | `_v4/r3/vergleich_keeper_waggle.png`, `_v4/r3/vergleich_queen_sun.png`, `_v4/r3/vergleich_west_wasp.png` |
| Farbkontrastproben | `_v4/r3/nachher/lesbarkeit_*.png` |

### Prüfungen und Reproduktion

- Finaler `gen_hive.py build --art`: beide Varianten mit 0 gemeldeten Layoutproblemen; 53 Props im vollständigen Atlas; 208 Konsolenreferenzen aus 90 eindeutigen Bildern; keine fehlenden Prop- oder Konsolenbilder.
- `validate_hive.py`: 20 Szenarien erfolgreich, konservativer Spielerradius 0.28 m. Alle erfassten Ergebnisse einschließlich Weglängen, abgeschnittener Räume, Komponenten und Landeprüfung stimmen **exakt** mit der gesicherten Basis aus `_out/v4_navigation.json` überein. Kein erfasster Rettungsweg wurde länger oder unerreichbar.
- Konsolenkoordinaten, Vents, Treppen, Türen und Bewegungswände stimmen mit beiden gesicherten Karten-JSONs überein. Neue Props stehen vollständig auf dem Boden, überlappen keine anderen Stellobjekte und halten mindestens 0.60 m Abstand zu den Konsolen- und Ventpunkten.
- Bestehende Assetverträge erfolgreich: 35 Prop-Arten, 23 animierte Propframes, vier Amberhive-Kinoszenen, identische Bienenanker sowie alle 16 Honigfluss- und Tropfenframes und fünf unveränderte Schleifen pro Fassung.
- Python-Syntaxprüfung der zehn neuen oder geänderten Python-Dateien erfolgreich. Bildprüfung der Bodenkacheln erfolgreich.
- Belege: `_v4/r3/r3_pruefung.json`, `_v4/r3/navigation_vergleich.json`, `_v4/r3/asset_pruefung.json`, `_v4/r3/r2_pruefung.json`, `_v4/r3/pruefung.log` und `_v4/r3/build_final.log`. Die historischen Berichte in `r2/` wurden nicht überschrieben.
- Der endgültig geprüfte Paketstand mit Quellen- und Paketprüfsummen ist in `_v4/r3/abschlussstand.json` gesichert. Die nach der Unterbrechung erneuerten Endbilder enthalten alle fünf großen Wandmotive. Die parallel geänderte `src/AtlasAmberhiveLife.cs` wurde nur erkannt und unverändert belassen.

Neue Quellen: `v4_r3_surfaces.py`, `v4_r3_review.py`, `v4_r3_check.py`, `blender/v4_r3_palette.py`, `blender/props_r3.py`. Geänderte Quellen: `floor_geo.py`, `v4_surfaces.py`, `v4_r2_surfaces.py`, `blender/floor_build.py`, `hive_layout.py` und `art_props.json`. Generierte Propbilder und Anker liegen in `art/props/`, das fertige Kartenpaket in `assets/amberhive/`.

Reproduktion aus dieser Arbeitskopie:

```text
<Blender> -b --factory-startup -P tools/hive/blender/props_r3.py
python tools/hive/gen_hive.py build --art
python tools/hive/v4_r3_check.py
python tools/hive/v4_r3_review.py vorher --reuse
python tools/hive/v4_r3_review.py nachher
```

Die gesicherte Vorher-Basis ist geschützt. `vorher --reuse` erzeugt Ausschnitte aus den alten Bildern, ohne die Basis mit aktuellen Assets zu überschreiben. Es wurden ausschließlich Dateien in `UnknownsAtlas_AmberhiveV4` geschrieben. Keine Among-Us-Spieltexturen verwendet, kein Among Us durch Grafik gestartet, keine C#-Dateien bearbeitet, keine eigenen Subagents oder Forks und kein Commit, Push oder Tag. Die vollständige Laufzeitabnahme bleibt beim parallel arbeitenden Test-Agenten.
