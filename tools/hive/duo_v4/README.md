# Amberhive V4 Mehrspielertest

Diese Kopie erweitert DuoTest ausschliesslich unter UnknownsAtlas_AmberhiveV4. Das Originalprojekt DuoTest wird weder veraendert noch gebaut. Die Spielkopien A, B und C bleiben auf C. session.py ersetzt ihre Atlas-DLL durch die Release-DLL dieser V4-Kopie und stellt ihre zuvor gesicherten DLLs und Configs nach dem Lauf wieder her.

Vorbereitung im V4-Projektordner:

```powershell
python tools/hive/gen_hive.py build --art
dotnet build -c Release -p:AtlasDeployToGame=false
dotnet build tools/hive/duo_v4/DuoTest.csproj -c Release
pwsh -NoProfile -File tools/hive/duo_v4/verify_wire.ps1
```

Gezielte Nachpruefung:

```powershell
python tools/hive/duo_v4/session.py NEUER_EINDEUTIGER_TAG hivefollow
```

Der erste Plan hivev4 prueft beide Etagen und die Kontrollkarte Museum. hivefollow prueft die korrigierte Pollenuebertragung beider Etagen, neue Verbindungsstellen, lokale Soundoptionen, Glow-Fade-Umkehr, Rollen, Flutzonen mit lokalen Honigspuren, Reaktor-Konsolen, Gast-Rutsche, Meeting-Abbruch, spaeten Beitritt und Host-Abgang. Diese kleinen Testspiele unterdruecken die regulaere Siegpruefung ueber die vorhandene Bypass-Testmod. Das ist keine Balancepruefung.

Der kurze Plan hiveninja prueft Ninja mit ausdruecklich zehn Sekunden Unsichtbarkeit und einen Meeting-Aufruf 0.12 Sekunden nach der Gast-Rutschenanfrage. v4_multi_04 bestaetigt beide Faelle. Die frueheren gleichnamigen Proben in hivefollow trafen diese Zeitfenster nicht und werden im Bericht entsprechend eingeschraenkt.

## Sicherung und Prozessbesitz

session.py verweigert den Start, sobald tasklist einen bestehenden Among-Us-Prozess meldet. Vor jedem weiteren Clientstart prueft die lokale run.ps1 auf ein fremdes Spiel. Nur die im eigenen Lauf gestarteten DuoTest-Kopien werden zum Abschluss beendet. Keine fremden Prozesse beenden. Keine Aenderung der echten Installation durch diese Mehrspielerlaeufe.

Die Originale saemtlicher Dateien unmittelbar im AppData-Spielordner werden separat je Lauf gesichert. Nach dem Lauf werden zusaetzlich entstandene Dateien entfernt und alle Originaldateien mit SHA256 nachgeprueft. Auch zuvor vorhandene Duo-Speicherstaende und Spiel-Logs werden zurueckgelegt. Die vorhandenen DuoTest-Sicherungen appdata_pristine und appdata_backup werden nicht als Ursprung dieser V4-Sitzung vorausgesetzt.

Ergebnisse liegen sowohl unter LocalAppData/DuoTest/runs/TAG als auch hier unter _out/TAG. before.json enthaelt die urspruenglichen AppData- und Installationspruefsummen, deployment.json den Atlas-DLL-Hash jeder Instanz und restore.json das Wiederherstellungsergebnis. Bei einem extern abgebrochenen Steuerprozess zuerst die dazugehoerige backup/appdata-Sicherung verwenden. Keinen neuen Lauf ueber veraenderte AppData sichern.

## Beobachtungen

v4_state.tsv zeichnet Mechanikuhr, Phasen, Flut, Life-Uhr, Generation, quantisierte Pollenabdruecke und reale AudioSource-Pegel auf. v4_life.tsv ergaenzt die zugelassenen Spurenquellen, Sonne, Laternenhelligkeit und lokale Honigspuren. Alle Proben sind Testcode, nicht Bestandteil der veroeffentlichten Atlas-DLL.

Die Messpunkte werden etwa alle 0,5 Sekunden erfasst. Ein Zeitversatz der Bildaufnahme oder ein Vergleich unmittelbar an einer Phasengrenze ist keine bestaetigte Desynchronisierung. Mechanikphasen anhand ihres Alters vergleichen; die lokalen Weltuhren koennen wegen des unterschiedlichen Kartenaufbaus verschiedene Nullpunkte besitzen.

```powershell
python tools/hive/duo_v4/audit.py tools/hive/duo_v4/_out/TAG
python tools/hive/duo_v4/analyze.py tools/hive/duo_v4/_out/TAG
```

diagnose_control.py verwendet fuer die Freeplay-Gegenprobe ausschliesslich tools/hive/maptest.sh und sichert AppData zusaetzlich aussen herum. Dieser Aufruf darf erst nach Abschluss aller Mehrspielerprozesse erfolgen.
