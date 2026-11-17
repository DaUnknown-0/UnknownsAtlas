# Amberhive V5

Stand: 16.11.2026. Arbeitskopie: `UnknownsAtlas_AmberhiveV5`.

## Zusammenstellung

V5 verwendet die vollständige Fable-Grafik mit genau vier Ausnahmen: `task_eject_hive_deck_bg.jpg`, `task_eject_hive_queen_bg.jpg`, `task_eject_hive_swarm_bg.jpg` und `task_eject_hive_well_bg.jpg` stammen aus `_variants/v3_gpt/eject`. Die V4-Funktionen bleiben erhalten.

Die Eingangskopie war ohne Buildausgaben bytegleich mit V4. Der aktive Originalstand stimmt in beiden Richtungen mit `_variants/v2_fable` überein: art, assets_amberhive, blender, floor_geo.py, fx_geo.py und eject_scenes.py. Es fehlen keine gesicherten Dateien; es gibt keine zusätzlichen aktiven Dateien. Nachweise: [_v5/v4_basisvergleich.json](_v5/v4_basisvergleich.json), [_v5/fable_aktivvergleich.json](_v5/fable_aktivvergleich.json), [_v5/fable_aktive_zusaetze.json](_v5/fable_aktive_zusaetze.json).

## Einordnung vor Umsetzung

Die vollständige Liste mit 3741 gegenüber dem Original geänderten, hinzugefügten oder fehlenden Dateien wurde vor der Umsetzung erstellt. Sie enthält auch historische Berichte, Videos und Vergleichsbilder. Buildausgaben, Git-Inhalte, Python-Caches und temporäre `_out`-Ordner sind ausgenommen.

- [Dateiliste mit Einordnung](_v5/einordnung_vorher.md)
- [Dateiliste mit SHA256](_v5/einordnung_vorher.json)
- [Gemischte Dateien nach Code-Stelle](_v5/einordnung_codestellen.md)
- [Quellvergleich Original gegen V4](_v5/quellvergleich.diff)
- [Tatsächliche C#-Änderung V4 gegen V5](_v5/code_v5_gegen_v4.diff)

| Bereich | Einordnung | Endzustand |
|---|---|---|
| Böden, See, Wandfronten, Außenwaben, Wandmodule, Paletten | Grafik von Sol: zurück auf Fable | Fable-floor_geo.py und Fable-Blender auf V4-Grundriss neu gerendert |
| Bienen, Brücke, Benutzen-Knöpfe, Flutbilder | Grafik von Sol: zurück auf Fable | Fable-Dateien; nur Flutbild 2 mit Fable-Generator für die geänderte funktionale V4-Zone neu gerendert |
| Requisiten und Platzierungen aus Runde 2 und 3 | Grafik von Sol: zurück auf Fable | 14 zusätzliche Platzierungen samt ihren Kollisionsflächen entfernt; PROPS entspricht exakt Fable |
| Honigrinnen und Wandtropfen | Grafik von Sol: zurück auf Fable | honey_r2_contract, Frames, HONEY_LOOPS, JSON-Export, Parser, Aufbau und Tick vollständig entfernt |
| V4-Szenendetails | Grafik von Sol: zurück auf Fable | Sonnendeck-Rankenebene, Brunnen-Manometer/Klappen und eject_v4_details entfernt |
| Figuren und Szenenebenen | Grafik von Sol: zurück auf Fable | Alle 51 Fable-Dateien einschließlich 19 Brückenframes bytegleich erhalten |
| Vier Szenenhintergründe | Ausdrückliche GPT-Ausnahme | Alle vier Dateien bytegleich aus v3_gpt |
| Layout | Funktion: bleibt | Räume, Gänge, neue Rundwege, verlängerte Westverbindung, Rutschenende, Vent 6, Kameras und Treppen exakt V4 |
| Laufzeitcode | Funktion: bleibt | Weltwurzel-Skalierung, Mechanikuhr, Hostabgleich, Brücke, Flut, Rutsche und Pollen-Serializer-Fix erhalten |
| Life und funktionale Effektgrafiken | Funktion: bleibt | Reaktive Bienen, Flammen, Honigabdrücke, Pollenoption 1730, wandernde Sonne und Glow Fade erhalten |
| Sound | Funktion: bleibt | AtlasAmberhiveSound.cs und alle zehn Ogg-Dateien unverändert |
| Generator, Vorschau, Testwerkzeuge | Funktion: bleibt | build-Schutz, Konsolenabstände, Bewegungsprüfung, relative Testpfade und Wiederherstellung erhalten |

Alle 73 anderen C#-Dateien sind bytegleich mit V4. `src/AtlasAmberhive.cs` unterscheidet sich ausschließlich durch die Entfernung der kosmetischen Honigschleifen. Netzwerkcode wurde nicht geändert; ein neuer Mehrspielertest war daher nicht erforderlich. Die funktionalen Life-Effekte werden weiterhin zur Laufzeit erzeugt und wurden nicht durch Fable-Dateien ersetzt.

Aktive Sol-Generatoren und Paletten sind entfernt, historische V4-Berichte und Vergleichsartefakte bleiben als Nachweis erhalten. `tools/eject_scenes.py` enthält die Fable-Regie mit der sicheren V4-main-Funktion: `--amberhive-only` und der Schreibbereichsschutz bleiben erhalten. Andere Karten und Szenen sind unverändert.

## Hintergründe und Anker

Alle vier Hintergründe haben exakt 2160 × 1224 Pixel bei 180 Pixeln je Szenenmeter. Seitenverhältnis, Skalierung und mittiger Hintergrundanker entsprechen Fable. Es wurde keine Skalierung, Beschneidung oder Verschiebung benötigt.

Geprüft wurden die gemeinsame Brunnenöffnung und das Lager aller Brückenwinkel, die Mittelachse und Sitzposition des Throns, die Bullaugenöffnung und der Schwarmflug sowie Topfposition, Blume und Flaggenmast auf dem Sonnendeck. Die Kontaktbögen zeigen jeweils drei Zeitpunkte mit den unveränderten Fable-Ebenen. Die goldenen Rahmen in diesen Offline-Bögen markieren den Kameraausschnitt und sind kein Spieleffekt. Die dortige rote Spielfigur ist ein Vorschauplatzhalter.

Vergleich: [_v5/hintergruende_vergleich.png](_v5/hintergruende_vergleich.png). Die Amberhive-Regie ist strukturell exakt Fable. Das fertige Paket unterscheidet sich von der Fable-Sicherung ausschließlich durch 20 neu gerenderte Erdgeschosskacheln, zwei Kartendateien, zwei Minikarten, das angepasste Flutbild 2 und die vier ausdrücklich gewünschten GPT-Hintergründe. Krone, Prop- und Konsolenatlanten bleiben sogar bytegleich mit Fable. [Paketvergleich](_v5/paket_abweichungen_fable.json).

Bytevergleich und Assetprüfung: [_v5/asset_funktionspruefung.json](_v5/asset_funktionspruefung.json).

## Build und Offline-Prüfungen

Release-DLL: [bin/Release/net6.0/UnknownsAtlas.dll](../../bin/Release/net6.0/UnknownsAtlas.dll). SHA256: `f964fa980b6158c0f2fb2c331a871f8457be051b20012ab65950fa1c57cd25fa`.

- `python tools/hive/gen_hive.py build --art`: erfolgreich, beide Etagenvarianten ohne Layoutproblem; 39 Props mit Krone, 28 ohne Krone; 208 Konsolenreferenzen aus 90 Bildern; keine fehlenden Bilder.
- `dotnet build -c Release --nologo`: erfolgreich, 0 Fehler. Eine bestehende Warnung CS0169 in `src/AtlasAssetStore.cs` wegen `_running`. [Buildlog](_v5/dotnet_release.log).
- `python tools/hive/validate_hive.py`: je zehn Szenarien mit 0,28 m Spielerradius, drei Brückenlagen und sieben geschlossenen Türgruppen erfolgreich. Keine verschlechterte Erreichbarkeit gegenüber V4, keine fehlerhaften Rutschenlandungen. [V4-Basis](_v5/navigation_v4.json), [V5](_v5/navigation_v5.json).
- Keeper zu Waggle: 9,68 m. Queen zu Sun: 11,22 m. Spawn zu Comms: 21,74 m. O2-Panels: 33,68 m. Reaktorhände: 8,70 m. Bei zwei geschlossenen Türszenarien verkürzt das Entfernen zusätzlicher Möbel einzelne Wege um 0,53 m.
- Keine Konsole einschließlich Notfallknopf, Admin, Kamera und Freeplay steht innerhalb einer Prop-Kollisionsfläche; 5 cm Sicherheitszugabe berücksichtigt. Alle PNGs im Amberhive-Paket sind vollständig lesbar.
- Generatoraufruf `build` ohne `--art` wird abgewiesen; alle Paketdateien bleiben dabei per SHA256 unverändert. [Nachweis](_v5/build_schutz.json).
- Life: 816 Regelprüfungen und 209 Geometrieprüfungen je Etagenfassung erfolgreich. [Regellog](_v5/life_rules.log).
- Sound: 8.339 Prüfungen erfolgreich, keine doppelten Clip-Stimmen, zehn unveränderte Ogg-Dateien. [Soundlog](_v5/sound_verify.log).
- Python-Syntax der aktiven Generator- und Testpipeline geprüft.

## Spieltests

Alle acht Läufe wurden aus V5 über `tools/hive/maptest.sh` ausgeführt. Vor jedem Lauf prüften Testhülle und Runner mit `tasklist`, dass kein Among-Us-Prozess lief. Der Runner beendete ausschließlich seine eigene gestartete Prozess-ID. Kein fremder Spielprozess wurde beendet.

| Lauf | Ergebnis | Nachweis |
|---|---|---|
| welt_1f_final | 13 bestanden, 0 Fehler | [Log](_v5/spieltests/welt_1f_final/amberhive_full.log), [Restore](_v5/spieltests/welt_1f_final/outer_restore.json) |
| welt_2f_final | 21 bestanden, 0 Fehler | [Log](_v5/spieltests/welt_2f_final/amberhive_full.log), [Restore](_v5/spieltests/welt_2f_final/outer_restore.json) |
| schwarm | 150 Bilder, Clip und Kontaktbogen; bekannter TOR-WrapUp-Fehler nach Szenenende | [Log](_v5/spieltests/schwarm/amberhive_full.log), [Restore](_v5/spieltests/schwarm/outer_restore.json) |
| brunnen | 150 Bilder, Clip und Kontaktbogen; bekannter TOR-WrapUp-Fehler nach Szenenende | [Log](_v5/spieltests/brunnen/amberhive_full.log), [Restore](_v5/spieltests/brunnen/outer_restore.json) |
| koenigin | 150 Bilder, Clip und Kontaktbogen; bekannter TOR-WrapUp-Fehler nach Szenenende | [Log](_v5/spieltests/koenigin/amberhive_full.log), [Restore](_v5/spieltests/koenigin/outer_restore.json) |
| sonnendeck | 150 Bilder, Clip und Kontaktbogen; bekannter TOR-WrapUp-Fehler nach Szenenende | [Log](_v5/spieltests/sonnendeck/amberhive_full.log), [Restore](_v5/spieltests/sonnendeck/outer_restore.json) |

Die finalen Weltprüfungen decken Weltmaß, Seesperre, begehbare Brücke, Flutvorwarnung und Bremsung, Rückkehr zum Eintrittsufer, beide Rundwege in beide Richtungen und West Press zu Wasp Watch ab. Mit zwei Etagen kommen Rutschenende, Freigabe der Bewegung, abgewiesene Anfrage von unten und alle sechs Treppenrichtungen dazu. Die Pollenoption war eingeschaltet, der Sonnenlauf auf 30 Sekunden beschleunigt; Life meldete gültigen Host-/Sync-Zustand.

Die ersten beiden Weltläufe (`welt_1f`: 11 bestanden, 2 fehlgeschlagen; `welt_2f`: 16 bestanden, 5 fehlgeschlagen) wurden durch die zugleich aktive automatische Fototour gestört. `AtlasMapShot` versetzte den Spieler an andere Fotopunkte und öffnete die Kameras, während die Mechanikdiagnose gezielte Positionen und Bewegungsfreigabe erwartete. Die Logs bleiben erhalten. Die Wiederholung setzte ausschließlich `Diagnostics.MapShot=false`; keine Gameplay- oder Netzwerkänderung war nötig. Danach bestehen dieselben Prüfungen mit 0 Fehlern.

Alle vier Szenen wurden anhand der echten Kontaktbögen visuell geprüft. Schwarm und Bullauge, Brückendrehung und Fall, Königin und Thronsitz sowie Blume, Biene und Sonnendeck stimmen zusammen. Je Szene liegen 150 PNG-Originalframes und ein daraus erzeugter stummer MP4-Clip mit 20 fps vor.

Nach jedem der acht Läufe wurden DLLs, drei Configs, das vorherige Spiel-Log und vorhandene AtlasShots durch maptest zurückgelegt. Die äußere Testhülle stellte zusätzlich die unmittelbar im Spiel-AppData-Ordner liegenden Dateien einschließlich Spielständen und Player-Logs wieder her. Sämtliche `restore.json` und `outer_restore.json` stimmen überein. Der abschließende Vergleich gegen den Zustand vor dem ersten Lauf bestätigt identische Installation und AppData sowie keinen laufenden Among-Us-Prozess. Die relevanten Original- und V4-Dateien sind gegenüber der vorab gespeicherten SHA256-Liste unverändert.

- [Vollständige Testauswertung](_v5/spieltest_auswertung.json)
- [Abschließende Verifikation](_v5/final_verification.json)

## Offene Punkte

Bei allen vier Szenen entsteht nach dem sichtbaren Szenenende die bereits in V4 dokumentierte `NullReferenceException` in `TheOtherRoles.Patches.ExileControllerWrapUpPatch.WrapUpPostfix`. Die vollständigen Stacks stehen in den jeweiligen `amberhive_full.log`-Dateien. Die Grafikaufnahme ist vollständig, der Abschluss der künstlich gestarteten Freeplay-Rauswurfszene ist deshalb nicht als fehlerfrei zu bewerten. TOR außerhalb von V5 wurde nicht verändert.

Die bekannten Harmony-Typwarnungen zur vorhandenen Il2Cppmscorlib/IMoniker-Kombination bleiben unverändert. Kein neuer Mehrspielertest, weil Netzwerkcode und Protokolle unverändert sind. Die bestehenden Grenzen der V4-Rollen- und Mehrspielerabnahme gelten weiter. Kein neuer kontrollierter Hörtest; Sounddateien und Soundcode sind unverändert, die Offline-Prüfung wurde erfolgreich wiederholt.


## Bilder

- [Alle vier Szenen im echten Spiel, gemeinsamer Kontaktbogen](_v5/szenen_gesamt_kontakt.png)

- [Gesamtkarte, eine Etage](_v5/karte_1f.png)
- [Gesamtkarte, zwei Etagen](_v5/karte_2f.png)
- [Schwarm-Kontaktbogen](_v5/hive_swarm_kontakt.png)
- [Brunnen-Kontaktbogen](_v5/hive_well_kontakt.png)
- [Königin-Kontaktbogen](_v5/hive_skip_queen_kontakt.png)
- [Sonnendeck-Kontaktbogen](_v5/hive_skip_sundeck_kontakt.png)

- [Schwarm, Spiel-Kontaktbogen](_v5/spiel_schwarm_kontakt.png), [MP4-Clip](_v5/spiel_schwarm.mp4)

- [Honigbrunnen, Spiel-Kontaktbogen](_v5/spiel_brunnen_kontakt.png), [MP4-Clip](_v5/spiel_brunnen.mp4)

- [Königin, Spiel-Kontaktbogen](_v5/spiel_koenigin_kontakt.png), [MP4-Clip](_v5/spiel_koenigin.mp4)

- [Sonnendeck, Spiel-Kontaktbogen](_v5/spiel_sonnendeck_kontakt.png), [MP4-Clip](_v5/spiel_sonnendeck.mp4)

## Reproduktion

Aus dem V5-Projektordner:

```text
python tools/eject_scenes.py --amberhive-only
python tools/hive/gen_hive.py build --art
python tools/hive/validate_hive.py
python tools/hive/_v5/verify_assets.py
dotnet build -c Release --nologo
python tools/hive/_v5/freeplay_suite.py
```

Die vier GPT-Hintergründe liegen bereits im Paket und werden vom Kartenbau nicht überschrieben. Werden die Fable-Szenen erneut in Blender gerendert, anschließend ausschließlich die vier `_bg.jpg` aus `_variants/v3_gpt/eject` wieder nach `assets/amberhive` kopieren. Die übrigen Fable-Ebenen unverändert lassen. Flutbild 2 wurde mit `python tools/hive/fx_geo.py` und Fable-`blender/fx_build.py` in den separaten Ordner `_v5/fx_render` gerendert und als einzige benötigte Layoutanpassung nach `art/fx` übernommen. Der vollständige FX-Neurender ersetzt nicht die gesicherten Fable-Bienen.

Keine eigenen Subagents, Forks, Commits, Pushes oder Tags. Projektdateien wurden ausschließlich in V5 geschrieben. Die echte Installation wurde nur durch das ausdrücklich angeforderte `maptest.sh` vorübergehend verwendet und wird je Lauf zurückgelegt; zusätzliche Spielstandssicherungen liegen innerhalb `_v5/spieltests`.


## Uebernahme ins Hauptrepo am 17.11.2026

Dieser Bericht beschreibt den historischen V5-Teststand. Die verlinkten Ordner `_v5`, `_variants` und
andere Arbeitsausgaben werden bewusst nicht versioniert. Die aktiven Generatoren, Blender-Skripte,
Sprite-Eingaben und dieses Dokument bleiben erhalten. Kontaktboegen sind Vorschauen und ausgeschlossen.
Die vier freigegebenen Szenenhintergruende liegen in `assets/amberhive`; ein erneutes Rendern der
Fable-Hintergruende ersetzt diese Auswahl und darf nicht ungeprueft uebernommen werden.

Release 1.2.0 nutzt Asset-Katalog v16. Nach einer absichtlichen Neuerzeugung der Kartengrafik:

```text
python tools/pack_textures.py assets/amberhive amberhive
python tools/pack_textures.py --check assets/amberhive amberhive
python tools/build_assets_repo.py v16
dotnet build -c Release -p:AtlasDeployToGame=false -p:AmongUsLatest=
```

Nur die fertigen `.atx` werden fuer Boden-, Objekt- und Konsolenatlanten versioniert. Die lokalen
JPG-/PNG-Quellen dieser Atlanten bleiben ignoriert. Die grossen Laufzeitbilder werden aus
UnknownsAtlas-Assets geladen, Szenen weiter unter `UnknownsAtlas.Resources.*`, die uebrigen
Kartenbilder unter `UnknownsAtlas.Maps.amberhive.*`. Kleine Klaenge bleiben wie bisher eingebettet.

`maptest.sh` verwendet nur die Atlas-DLL des aktuellen Projektordners. `ASSET_SOURCE` kann einen
lokalen HTTP-Testserver fuer den noch unveroeffentlichten Katalog angeben. `OUTDIR` liegt im Projekt
oder im freigegebenen Auditordner. Der Test sichert DLL, Config, Log, Asset-Cache, AtlasShots und die
Dateien unmittelbar im AppData-Spielordner und prueft die Wiederherstellung per SHA256. Er beendet
nur den selbst gestarteten Spielprozess. Neue Testnachweise liegen im separaten Audit vom 17.11.2026.
