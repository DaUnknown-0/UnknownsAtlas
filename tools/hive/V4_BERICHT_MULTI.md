# Amberhive V4: Mehrspielerpruefung

Stand: 16.11.2026, Abschluss nach vier Dreierlaeufen und zwei Freeplay-Gegenproben. Arbeitskopie: UnknownsAtlas_AmberhiveV4. Host A und Gaeste B/C ueber DuoTest und lokale Netzwerkspiele. Keine eigenen Subagents, Forks, Commits, Pushes oder Tags. Originalprojekte UnknownsAtlas, DuoTest und TheOtherRoles nicht veraendert.

## Bestaetigter Fehler und Korrektur

Pollenspuren wurden nur auf dem Host angezeigt. In beiden Etagenfassungen erzeugte der Host beim kontrollierten Weg aus der Pollenmatte drei Abdruecke, beide Gaeste erhielten keinen. Option 1730, Life-Zustand und Meeting-Generation waren dabei synchron.

Ursache in `src/AtlasAmberhiveLife.cs`, `SendPrints`: Die verwendete Hazel-Version besitzt keine Ueberladung `MessageWriter.Write(short)`. C# waehlte `Write(int)`. Der Sender schrieb deshalb vier Byte je Koordinate, waehrend der Empfaenger `ReadInt16` mit zwei Byte benutzte. Die folgenden Felder waren verschoben und das Paket wurde als ungueltig verworfen. Das trat ohne Atlas-Warnung auf.

Die beiden Koordinaten werden jetzt als `unchecked((ushort)(short)...)` geschrieben. Das Zweierkomplement bleibt fuer `ReadInt16` erhalten. Das Paket hat die vorgesehenen 13 Byte je Abdruck. Eine Pruefung der tatsaechlich gebauten Release-DLL mit Mono.Cecil bestaetigt zweimal `Write(UInt16)` und nur den vorgesehenen `Write(Int32)` fuer die Generation. Nachweis: [wire_verification.json](duo_v4/wire_verification.json). Keine Aenderung an Optionen, Kanal oder Empfaengerformat.

## Laeufe und belastbare Grenzen

| Lauf | Inhalt | Ergebnis |
|---|---|---|
| v4_multi_01 | Erster Dreierlauf, eine Etage und Beginn der naechsten Runde | Erkundung. Physikbewegung des Treibers unzureichend, zweite Runde wegen fehlendem Client abgebrochen. Kein Freigabenachweis fuer Pollen oder zwei Etagen. |
| v4_multi_02 | Plan hivev4, Host plus zwei Gaeste, 929 Sekunden | Beide Amberhive-Etagen, alle Sabotagen, echte Meetings und Museum-Kontrolle abgeschlossen. Pollenfehler vor Korrektur reproduziert. Gast-Rutschenaufruf des Treibers fehlerhaft. |
| v4_multi_03 | Plan hivefollow, frisch erzeugte Grafik-Runde 3 und korrigierte DLL, 520 Sekunden | Pollen auf allen drei Instanzen identisch, reale Gast-Rutsche und Reaktor-Konsolen erfolgreich. Scout/Phantom bestaetigt. Ninja-Testdauer vor Laufbewegung abgelaufen; geplantes Meeting lag erst nach Fahrtende. Diese beiden Proben zaehlen nicht als bestanden. |
| v4_multi_04 | Gezielter Plan hiveninja, 198 Sekunden | Ninja als Host und Gast auf A/B/C waehrend aktiver Unsichtbarkeit ausgeschlossen, keine neuen Abdruecke. Gast-Rutsche vor Meeting aktiv am oberen Start, kein Erreichen des Ausstiegs vor Meeting, danach Fahrt beendet und Bewegung freigegeben. |

Alle Mehrspieler-Spieldaten bleiben unter `%LOCALAPPDATA%/DuoTest/runs/<Tag>`. Vollstaendige Kopien, Bilder und zusaetzliche Messdateien liegen unter `tools/hive/duo_v4/_out/<Tag>/`. Je Instanz enthalten `A`, `B`, `C` die `LogOutput.log`, `player.log`, `v4_state.tsv`, `v4_life.tsv` und `shots`. `logs/log_A.log` bis `log_C.log` sowie `logs/snap_*.tsv` sind die regulaeren DuoTest-Artefakte.

Vor dem letzten Mehrspieler-Nachtest wurde gemaess Auftrag `python tools/hive/gen_hive.py build --art` ausgefuehrt: 0 Layoutprobleme in beiden Fassungen, 53 Props im Gesamtatlas, keine fehlenden Prop- oder Konsolenbilder, 46 beziehungsweise 52 Konsolenpositionen. Danach `dotnet build -c Release -p:AtlasDeployToGame=false` und Build des lokalen Testtreibers erfolgreich. Einzige Atlas-Buildwarnung: bestehendes CS0169 in AtlasAssetStore.cs.

Die Tests verwenden die bestehenden Testfunktionen von DuoTest: Unterdrueckung des vorzeitigen Rundenendes bei drei Spielern, kontrollierte Rollenvergabe, Positions-RPCs zur Vorbereitung und echte Physikbewegung auf den eigentlichen Laufstrecken. Die Ergebnisse pruefen den lokalen Mehrspielerbetrieb, keine Internetlatenz oder Rundenbalance mit einer vollen Lobby.

## Testmatrix

| Punkt | Ergebnis und Nachweis |
|---|---|
| Option 1729, eine und zwei Etagen | In v4_multi_02 auf allen drei Instanzen dieselbe Fassung und dieselben Bauzahlen. Zwei Etagen mit Rutsche, eine Etage ohne. |
| Bruecke, Phasen und Meeting | v4_multi_02: Phasen auf allen Instanzen, Zustandsuhr waehrend Meeting und Exil angehalten. Punktuelle Abweichungen bei halbsekundigen Stichproben an Phasenwechseln sind zeitversetzte Messungen. Gezielter Nachtest in v4_multi_03. |
| Flut, vier Zonen | v4_multi_02: Warnung, Anstieg, Hochstand und Ablauf auf allen Instanzen. Automatische Flut im ersten Erkundungslauf ueberlagerte manuelle Proben; im lokalen Testtreiber korrigiert. Bewegung und lokale Honigspuren im Nachtest. |
| Rutsche Host | v4_multi_02: Host erreicht (2.7,-2.7), Bewegung wieder freigegeben. |
| Rutsche Gast, unzulaessige Anfrage, Meeting-Abbruch | v4_multi_03: B durchlaeuft (3,26), die Fahrt und (2.7,-2.7); danach `CanMove=True`. Anfrage vom unteren Ende verworfen, B bleibt unten. v4_multi_04: Fahrt am Start nachgewiesen aktiv, Meeting nach 0.12 Sekunden, kein Ausstieg vor Meeting; danach `_chuteT0=-1` und `CanMove=True`. Nachweis: `ninja_abort.json`. |
| Pollenoption 1730 aus/an | v4_multi_02: alle Instanzen uebernehmen die echte Hostoption. Standard aus, eingeschaltet vor Aufnahme. Nach Ausschalten keine Abdruecke. |
| Pollenpositionen und Lebensdauer | v4_multi_03: je drei Abdruecke in beiden Etagen, auf A/B/C identische IDs, Zentimeterpositionen, Winkel und Geburtszeiten. Nach Ablauf verschwunden; Meeting entfernt Spuren, keine Wiederherstellung aus alten Snapshots. `audit.json`, `summary.json`, `v4_state.tsv`. |
| Unsichtbarkeit Ninja und Scout | Scout als Host und Gast in v4_multi_03: auf allen Instanzen waehrend der Laufbewegung als Quelle ausgeschlossen, keine neuen Abdruecke. Ninja nach korrigierter Testdauer in v4_multi_04 ebenfalls auf A/B/C ausgeschlossen, keine neuen Abdruecke. Bereits zuvor oeffentlich erzeugte Schritte duerfen regulaer auslaufen. |
| Phantom | v4_multi_03: echte Phantom-Rolle mit Vanish/Appear als Host und Gast, auf allen Instanzen waehrend verborgener Bewegung ausgeschlossen, keine neuen Abdruecke. |
| Chameleon und kompletter PropHunt-Modus | Offen. Keine vollstaendige Laufzeitpruefung dieser beiden Modi behauptet. |
| Vent und Transportspuren | v4_multi_02: Vent-Eintritt/-Austritt und Transportsperren beobachtet. Nachtest fuer die korrigierten uebertragenen Spuren und Rutsche in v4_multi_03. |
| Reaktive Bienen, Kerzen, Honigspuren | v4_multi_03: in jeder der vier Flutzonen lokale Honigabdruecke auf A/B/C nach sichtbarer Bewegung erfasst. Lokale Reaktionen sind absichtlich von eigener Sicht und Licht abhaengig. Vollstaendige Bienen-/Kerzen-Sichtmaskenabnahme mit verdeckten Spielern bleibt offen. |
| Wandernde Sonne | Host-/Gast-Life-Uhren, Sonnenposition und Winkel in v4_life.tsv. Zeitlich korrigierter Uhrenvergleich in v4_multi_03: 95 Prozent der Abweichungen unter 0.016 Sekunden, Maximum rund 0.189 Sekunden. Normaler 600-Sekunden-Zyklus, keine Freeplay-Beschleunigung im Mehrspieler. Meeting pausiert. |
| Glow Fade | v4_multi_02: echte Licht-Sabotage und Reparatur auf allen drei Instanzen. v4_multi_03: zweimal nach 0.8 Sekunden repariert, Zwischenhelligkeiten der Laternen erfasst, kein Atlas-Fehler. Kein Eingriff in echte Sichtweiten. |
| Licht, Comms, O2, Reaktor | v4_multi_02: alle vier starten in beiden Fassungen, Reparaturen erfolgreich. Reaktor bleibt nach einer Hand aktiv und ist nach zwei verschiedenen Spielern an zwei Hand-IDs repariert. Nachtest oeffnet zusaetzlich echte Konsolen an deren Kartenpositionen. |
| Tueren | v4_multi_02: Cafeteria-Tuergruppe ueber normalen Systemaufruf geschlossen, danach regulaerer Ablauf. Keine Vollpruefung jeder einzelnen Tuergruppe. |
| Kill, Leiche melden, Rauswurf, Skip | v4_multi_02: in beiden Fassungen durchgefuehrt, Rueckkehr in Lobby und weitere Runde. Beide Skip-Szenen und Amberhive-Rauswurfszenen auf Host und Gaesten geladen. |
| Spaeter Beitritt | v4_multi_03: C verlaesst und verbindet erneut zur laufenden Runde; Ergebnis `NotJoined False`, Beitritt abgewiesen. Keine erfolgreich aufgebaute Welt eines spaeten Gastes, daher deren Zustandsabgleich offen. |
| Host verlaesst | v4_multi_03: A verlaesst allein, B wird noch rund 35 Sekunden beobachtet. B wechselt von Started nach NotJoined, keine fortgesetzte LAN-Runde und kein neuer Host. Kein Atlas-Absturz. Hostuebernahme in einer laufenden Serverrunde bleibt offen. |
| Grafik-Runde 3, Laufwege | v4_multi_03: alle drei Anschluesse mit echter Physik durchlaufen, Zielabstaende 0.206 m, 0.020 m und 0.036 m. Stabile Wasp-Aufnahme zeigt den Spieler. Keeper-/Queen-Aufnahmen treffen bereits den naechsten Teleport und sind fuer Figurenlesbarkeit nicht belastbar. Leichen, alle neuen Props und jede Sichtmaskenkante bleiben offen. |
| Klangkulisse | Reale AudioSource-Pegel in v4_state.tsv. Lokale Lautstaerken 0/30/60/100 in v4_multi_02. v4_multi_03: Gast B nach Abschalten 0, A/C weiter 0.0966; B blendet danach wieder ein. Alle Amberhive-Quellen bei Meeting/Exil 0. Hoerpruefung siehe unten. |

## Offener WrapUp-Fehler aus dem Freeplay-Bericht

**Ergebnis: generisches Artefakt des kuenstlichen Freeplay-Skips ohne echtes Meeting, kein nachgewiesener Amberhive-Mehrspielerfehler.**

v4_multi_02 und v4_multi_03 enthalten auf keiner Instanz einen Aufrufstack mit `WrapUpPostfix`. Echte Skips auf Amberhive, darunter Sonnendeck, und ein echtes Meeting auf der unveraenderten Atlas-Karte Museum wurden abgeschlossen.

Gegenprobe `v4_control_museum_long`: normale Installation ausschliesslich ueber maptest.sh temporaer mit der V4-DLL gestartet, unveraenderte Karte Museum, `TaskTest=ejectskip:0`, 55 Sekunden Beobachtung nach Kartenbau. Derselbe `NullReferenceException`-Stack in `TheOtherRoles.Patches.ExileControllerWrapUpPatch.WrapUpPostfix`, gefolgt von `diag: ejectskip:0 finished` und `diag: all done`. Beleg: [museum_full.log](duo_v4/_out/v4_control_museum_long/museum_full.log), Zeilen 468 bis 477. Die erste kurze Museum-Probe endete vor dem WrapUp und wird fuer diese Schlussfolgerung nicht benutzt.

Die Gegenprobe reproduziert den Fehler ohne Amberhive-Szenen und ohne Amberhive-Welt. Deshalb keine Aenderung an TOR oder an normalen Rauswurf-Abschluessen. Der kuenstliche Diagnosepfad bleibt mit diesem bekannten Fehler behaftet; er wird nicht als repariert ausgegeben.

## Logauswertung und Testtreiber

`audit.json` und `analysis.json` halten die Messungen fest. Bekannte Harmony-Typwarnungen zu Il2Cppmscorlib werden getrennt gezaehlt. Die Boot-Selbsttests erzeugen absichtlich fehlerhafte Pakete fuer andere Mods; deren Meldungen sind keine aus Amberhive-Spielaktionen abgeleiteten Befunde.

v4_multi_02: keine Atlas-Warnung oder Atlas-Exception waehrend der beiden regulaeren Amberhive-Runden. Zwei Gast-Rutschenaufrufe scheiterten im lokalen Testtreiber, nicht in Atlas. Beim abschliessenden Verlassen erschienen in A und B Vanilla-Stacks in `ControllerManager.OpenOverlayMenu` und `DisconnectPopup.DoShow`. v4_multi_03: B und C ohne Laufzeitfehler; A mit demselben Vanilla-Abschlussstack. v4_multi_04: derselbe Abschlussstack einmal je Instanz. In beiden Nachtests keine Atlas-Warnung, Atlas-Exception oder WrapUp-Exception. TheOtherRoles und Vanilla wurden nicht umgebaut.

Weitere lokale Treiberkorrekturen: Physikbewegung als Postfix von PlayerPhysics.FixedUpdate, Warten auf alle zurueckgekehrten Lobbyspieler, gezielte Fraktionsangleichung nach der Role-Control-Warnung, Unterdruecken konkurrierender automatischer Fluten bei manuell gesteuerten Zonentests. Der Original-DuoTest-Quelltext bleibt erhalten.

## Bildbelege

Eigenstaendig angesehene Spielaufnahmen des Nachtests:

- [Pollen im Waggle Studio, Host](duo_v4/_out/v4_multi_03/A/shots/folge_1f_pollen_A.png).
- [West Press zu Wasp Watch, niedrigere Vorderwand und Spieler](duo_v4/_out/v4_multi_03/A/shots/folge_weg_west_wasp_A.png).
- [Keeper zu Waggle](duo_v4/_out/v4_multi_03/A/shots/folge_weg_keeper_waggle_A.png) und [Queen zu Sun](duo_v4/_out/v4_multi_03/A/shots/folge_weg_queen_sun_A.png): nur Umgebungsbelege. Der Spieler wurde vor der Bildspeicherung schon zum naechsten Weg versetzt; kein Nachweis fuer Figurenlesbarkeit. Der lokale Treiber wartet kuenftig nach der Aufnahme vor dem naechsten Teleport.
- [Reaktor-Konsole links](duo_v4/_out/v4_multi_03/A/shots/folge_reaktor_konsolen_A.png) und [Reaktor-Konsole rechts](duo_v4/_out/v4_multi_03/C/shots/folge_reaktor_konsolen_C.png).
- [Gast am Rutschenende](duo_v4/_out/v4_multi_03/B/shots/folge_rutsche_gast_B.png).

Diese Einzelbilder bestaetigen nicht jede moegliche Leichenposition, Sichtweite oder Verdeckung. Die Sichtmaskenpruefung an allen neuen Props bleibt deshalb ausdruecklich offen.

## Verbleibende Pruefungen

- Chameleon und vollstaendiger PropHunt-Modus mit Host und Gast; Geistersicht als gesonderte Beobachterrolle. Ninja, Scout und Phantom wurden nicht stellvertretend als Nachweis dieser anderen Rollen ausgegeben.
- Erfolgreicher Beitritt in eine bereits laufende Runde und anschliessender Snapshot-Abgleich. Das lokale Spiel weist den Beitritt ab. Auch eine fortgesetzte Runde nach Hostuebernahme ist durch den LAN-Abgang nicht geprueft.
- Vollstaendige Wand-, Dunkelheits- und Leichensichtpruefung aller neuen Props, beide Kronenvents und jede Treppenrichtung mit dem finalen Grafikpaket. Die alten Freeplay-Physikpruefungen und die unveraenderte Offline-Navigation ersetzen das nicht.
- Der Ventlauf in v4_multi_02 lag vor der Pollen-Serializerkorrektur. Der Quellenausschluss wurde beobachtet, eine erneute durchgaengige Vent-/Treppen-Pollenaufnahme auf allen Gaesten nach der Korrektur wurde nicht ausgefuehrt.
- Subjektive Klangabnahme und Spiel-Effektmixer gemaess Hoerliste. Die Pegelmessungen bestaetigen keine gehoerte Qualitaet oder Voice-Chat-Vertraeglichkeit.

## Hoerpruefung durch den User

- Beide Etagen ablaufen: weiche Raumuebergaenge, dichteres Summen an Thron und Brutwaben, keine Erdgeschossmaschinen auf der Krone.
- Brunnenblubbern, Blasebalg, beide Pressen, Wachskessel und kleine Mead-Hall-Glocken auf Charakter und Hintergrundlautstaerke pruefen.
- Mindestens 30 Sekunden stehen bleiben: keine Knackser an Loopgrenzen, Glocken deutlich von Notfallknopf unterscheiden.
- Bruecke nur bei Drehung hoerbar; Flut waehrend Vorwarnung still, dann passend zum Wasserstand; eigene Rutsche ohne Verfolgung fremder Spieler.
- Meeting, Skip, Rauswurf, Rundenende und naechste Runde: kein nachlaufender oder doppelter Klang.
- Effektlautstaerke des Spiels auf 0, danach mit Voice-Chat, Aufgaben und Sabotagealarm testen. Standard 60 soll im Hintergrund bleiben.

## Wiederherstellung

`restore.json` aller vier Mehrspielerlaeufe bestaetigt identische AppData-Dateien, identische echte Installation und wiederhergestellte Testkopien. v4_multi_03 und v4_multi_04 bestaetigen zusaetzlich unveraenderte Assets waehrend der Laeufe. `outer_restore.json` beider Museum-Gegenproben bestaetigt identische AppData und Installation; der innere maptest-Nachweis prueft alle temporaer ersetzten DLLs, Configs und das vorherige Spiel-Log einzeln. Zuvor fehlende Zusatz-DLL wurde wieder entfernt.

Alle Dateien unmittelbar im gemeinsamen AppData-Spielordner wurden je Lauf gesichert und per SHA256 wiederhergestellt, einschliesslich urspruenglicher DUO-Spielstaende und Player-Logs. Die Nachweise beziehen sich auf die jeweiligen Originale vor dem Lauf; nach der Unterbrechung wurden keine alten AppData-Staende ueber moegliche neue Benutzeraenderungen gelegt.

Die Mehrspieler-Skripte verwenden keine echte Installation als Deploymentziel. Die Freeplay-Gegenproben haben diese ausschliesslich ueber tools/hive/maptest.sh mit dessen eigener Sicherung beruehrt. Abschliessend keine Among-Us-Prozesse aktiv. Die detaillierte Endpruefung liegt in [final_verification.json](duo_v4/final_verification.json).
