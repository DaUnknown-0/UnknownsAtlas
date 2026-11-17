# Amberhive V4: Life-Implementierung

Stand: 16.11.2026. Ausschliesslich in `UnknownsAtlas_AmberhiveV4` gearbeitet. Among Us wurde nicht gestartet, nichts ins Spiel deployt. Kein Commit, Push oder Tag.

## Umsetzung

Die Implementierung liegt in `src/AtlasAmberhiveLife.cs`, die ohne Unity pruefbaren Zeit- und Bewegungsregeln in `src/AtlasAmberhiveLifeRules.cs`.

- Bienen weichen sichtbaren laufenden Spielern innerhalb von 1,65 m aus. Die Reaktion bleibt lokal und innerhalb des bisherigen Raum-Polygons. Sichtlinie zum Spieler, eigene Sichtlinie und eigener Lichtradius werden geprueft.
- Am Kerzenregal und Thron werden kleine Flammen und Lichtsaeume aufgebaut. Sichtbare vorbeilaufende Spieler erzeugen kurz staerkeres Flackern und eine Neigung der Flamme. Grundflackern laeuft unabhaengig von Spielern.
- In aktiven Honigfluten hinterlassen sichtbare Laeufer lokale, bernsteinfarbene Abdruecke fuer 1,25 Sekunden. Quelle und Abdruck muessen im eigenen Licht und ohne verdeckende Wand liegen. Beim Sichtverlust der Quelle werden die lokalen Abdruecke verworfen.
- Optionale Pollenmatte vor dem Blumenregal im Waggle Studio. Lage aus dem vorhandenen `flower_pots`-Prop abgeleitet, derzeit (18,60 / 8,15), Ellipsenradien 0,8 / 0,65 m. Sie ist nur bei eingeschalteter Host-Option sichtbar. Ohne dieses Prop entstehen keine Pollenspuren und es gibt eine Logmeldung, damit eine Layoutaenderung keine falsche Ersatzposition erzeugt.
- Wer den Bereich betritt, traegt bis sechs Sekunden nach dem Verlassen Pollen. Goldene Abdruecke leben jeweils sechs Sekunden. Schritte entstehen nur bei echter Positionsaenderung mit Mindestabstand und Frequenzbegrenzung. Alle Abdruecke haben dieselbe Farbe, ohne Spielerfarbe oder Rollenhinweis.
- Der Host erzeugt Position, Richtung und Zeit jedes Pollenabdrucks. Clients rekonstruieren keine Laufwege. Auch der Host nutzt dieselbe Zentimeter- und Winkelquantisierung wie die Clients. Die Welt-Sichtmaske bleibt aktiv; Spuren sind gemeinsame Weltobjekte, keine Sicht durch Waende.
- Ein weicher, gefaecherter Sonnenstrahl wandert und dreht sich am Honigbrunnen unter der Kronenoeffnung. Normaler Zyklus 600 Sekunden. Die Host-Uhr wird jede Sekunde abgeglichen und pausiert bei Meeting und Exil.
- Pro Raum eine Gluehonig-Laterne mit Lichthof. Glow Fade wird auf dem Host aus `AtlasWorld.LightsOut()` gelesen. Die Laternen erloeschen mit 0,13 Sekunden Abstand vom Lamphouse aus und blenden je 0,45 Sekunden ab. Reparatur funktioniert entsprechend. Eine Reparatur waehrend der laufenden Abschaltwelle uebernimmt die aktuelle Helligkeit jeder einzelnen Lampe. Vorhandene `glow_rack`-/`lantern_cart`-Sprites werden passend abgedunkelt; ihr Alpha bleibt unter Kontrolle der Moebel-Ausblendung.
- Keine Aenderung an Sichtweitenfaktoren, `VisionFactor`, Electrical-Switches oder LightSource. Es werden nur Sprite-Farben, Positionen und zusaetzliche maskierte Sprite-Renderer verwendet.

Die kleinen Sprite-Masken entstehen zur Laufzeit. Es gibt keine neuen Downloads, Shader oder Grafikdateien. Daher waren keine Aenderungen an `assets/amberhive`, der Projektdatei oder den Grafikwerkzeugen notwendig. Texturen, Sprites und Weltobjekte werden beim Zerstoeren der Kartenwelt freigegeben.

## Option und Netzwerk

Neue TOR-Option: **1730, Amberhive Pollen Trails**, Off / On, Standard **Off**. Anmeldung nutzt denselben Reflection-Mechanismus und dieselbe Verschiebung ans Listenende wie die bestehenden Atlas-Optionen. Ohne TOR gilt nur die Host-Config `[Amberhive] PollenTrails = false`; Gaeste uebernehmen den Host-Zustand ueber AtlasWorld.

Vor der Vergabe wurden die C#-Quellen aller Mods unter TOR Mod nach dem Bereich 1730 bis 1739 durchsucht. Es gab keine fremde Optionsbelegung von 1730. Die zentrale `ID-Registry.md` bestaetigt Atlas 1720 bis 1739 und bislang freie 1730 bis 1739. Sie liegt ausserhalb des Schreibbereichs und wurde nicht geaendert. Beim Zusammenfuehren nachtragen.

Bestehender Kanal: AtlasWorld RPC 237, Op 24 Hive. Die neuen Subs 16 bis 19 sind fuer Life dokumentiert; genutzt werden:

| Sub | Richtung | Inhalt |
|---|---|---|
| 16 | Host an alle | Protokollversion 1, Host-Uhr, Meeting-Generation, Pollenoption, Glow-Fade-Zustand, Startzeit und Ausgangshelligkeiten der Lampen |
| 17 | Host an alle | Generation, Host-Uhr, bis 40 Abdruecke mit Sequenznummer, x/y in Zentimetern, Winkelbyte und Geburtszeit |

Pakete mit 40 Abdruecken bleiben bei etwa 530 Bytes Life-Payload. Neue Schritte werden gesammelt etwa alle 0,1 Sekunden gesendet, bestehende Abdruecke jede Sekunde erneut abgeglichen. Maximal 320 Pollenabdruecke und 96 lokale Honigabdruecke gleichzeitig. Doppelte Sequenznummern werden ignoriert, Alter, Paketgroesse, Kartenbegrenzung und endliche Zahlen validiert. Life-Nachrichten von Nicht-Hosts werden verworfen. Subs 0 bis 4 und die bestehenden Weltmechaniken behalten ihren Vertrag.

Meeting und Exil entfernen Bepollung und Abdruecke; die Generation verhindert das Wiederherstellen alter Schritte durch Snapshot-Pakete. Beim Hostwechsel werden die lokalen Laufhistorien verworfen und die uebernommene Host-Uhr weiterverwendet.

## Sichtbarkeit und Transport

- Keine neuen Abdruecke oder Reaktionen fuer Tote, Disconnects, `!Visible`, inaktive Objekte, `inVent`, `walkingToVent`, Leitern, bewegte Plattformen oder durch AtlasFigure versetzte Figuren.
- Der echte Koerper-Renderer muss aktiv und fast vollstaendig deckend sein: Alpha mindestens 0,98. Das unterbindet Spuren auch fuer einen Host, der eine Unsichtbarkeitsrolle als schemenhafte Figur sehen darf. Die Grenze ist bewusst konservativ: Auch teilweise transparente Spieler erzeugen waehrenddessen keine neuen Spuren.
- Vanilla Phantom zusaetzlich direkt ueber `PhantomRole.IsInvisible` und `IsFading` ausgeschlossen. Beide APIs wurden in den verwendeten GameLibs nachgesehen und erfolgreich kompiliert.
- TOR Ninja zusaetzlich ueber den synchronisierten Status `TheOtherRoles.TheOtherRoles+Ninja.isInvisble` ausgeschlossen, mit optionalem Fallback fuer flache Typnamen. PropHunt ueber `invisPlayers`, Collection Scout ueber `abilityActive` ausgeschlossen. Die optionalen Assemblies werden per Reflection angesprochen.
- Verborgene Quellen verlieren ihre gesamte lokale Laufhistorie und Bepollung. Nach dem Auftauchen ist erneute Pollenaufnahme erforderlich. Schon vorher oeffentlich erzeugte Pollenabdruecke duerfen bis zu ihrem normalen Ablauf bestehen bleiben; sie zeigen ausschliesslich bereits erfolgte Schritte.
- Rutschenfreigaben sperren den betreffenden Spieler auf dem Host und den empfangenden Clients fuer drei Sekunden. Sowohl lokale als auch fremde Rutschende sind erfasst.
- Groessere Positionsspruenge und Bewegungen durch Schattenwaende loeschen die Bepollung und unterdruecken die weitere Erzeugung fuer 0,5 Sekunden. Ein Schritt verbindet niemals Start und Ende eines solchen Sprungs. Treppen liegen deutlich ausserhalb dieses Abstandslimits.

## Minimale Einhaengepunkte

Alle neuen Zeilen in fremden Dateien sind mit `AMBERHIVE LIFE` markiert.

`src/AtlasAmberhive.cs`:

1. Ein Feld `_life` fuer die eigene Instanz.
2. Aufbau nach `BuildBees`, mit einer Abfrage der bereits vorhandenen Honigflut.
3. `Dispose` in `OnDestroy`.
4. `Tick` nach den Objektanimationen und vor den Bienen.
5. Life-Empfang zu Beginn des bestehenden Hive-Empfaengers.
6. Transportsperre bei empfangener und hostseitig genehmigter Rutsche.
7. Eine Zeile zur Abstandskorrektur vor dem normalen Bienenflug.

`src/AtlasVanillaOptions.cs`:

1. Life-Konfiguration binden.
2. Option 1730 mit dem vorhandenen `Make` registrieren.
3. Life-Option in die vorhandene Verschiebung ans Listenende aufnehmen.

Keine Life-Aenderungen an AtlasWorld, AtlasPlugin, Layoutdateien, Sound oder Grafikwerkzeugen.

## Verifikation

- `dotnet build -p:AtlasDeployToGame=false -v:minimal` in der Arbeitskopie: erfolgreich, 0 Fehler. Eine bereits vorhandene Warnung CS0169 in `src/AtlasAssetStore.cs` wegen `_running`. Die Datei wurde nicht angefasst.
- `dotnet run --project tools/hive/life_tests/LifeRules.Tests.csproj -v:quiet`: **816 Pruefungen erfolgreich**. Getestet wird der tatsaechlich eingebundene Produktionscode aus `AtlasAmberhiveLifeRules.cs`, kein dupliziertes Modell. Aufnahme/Ablauf, Stillstand, Schrittfrequenz, alternierende Fuesse, Teleports, Wandquerung, ungueltige Zahlen, Zeitruecksprung, neue Laufhistorie ohne alte Bepollung und gestaffelte, unterbrechbare Lampenuebergaenge.
- `python tools/hive/life_tests/check_layout.py`: **209 Geometriepruefungen je Etagenfassung erfolgreich**. Pollenellipse und Spielerkreis in der Bereichsmitte liegen im Waggle Studio ausserhalb der bekannten Moebel-Kollisionen.
- Options-ID und Rollenstatus anhand der vorhandenen Mod-Quellen und der GameLibs kontrolliert.

## Offene Spieltests und Testschalter

Die vollstaendige Testanleitung steht in `tools/hive/V4_WUENSCHE_LIFE.md`. Freeplay-Schalter unter `[Diagnostics]`:

| Schluessel | Vorgabe | Testwert |
|---|---|---|
| AmberhivePollenTest | -1 | 1 schaltet Pollen im Freeplay ein, 0 aus |
| AmberhiveSunPeriodTest | 0 | 30 fuer einen schnellen Sonnenlauf |
| AmberhiveGlowTest | false | true fuer optische Abschaltung/Reparatur alle acht Sekunden |
| AmberhiveLifeLog | false | true fuer Zustandslogs alle zwei Sekunden, auch im Mehrspieler |

Offen sind die reale Sichtmasken-/Grafikabnahme, Konsolen-Kollider am Pollenbereich, Laufzeit mit allen genannten Rollen, Hostwechsel sowie der echte Zwei-Client-Abgleich. Der Life-Agent hat das Spiel auftragsgemaess nicht gestartet. Der optische Glow-Test ersetzt keine echte Licht-Sabotage. Vor einer Veroeffentlichung bitte insbesondere Host und Gast mit Ninja, Phantom, Scout, Chameleon, PropHunt, Vent und Rutsche pruefen.
