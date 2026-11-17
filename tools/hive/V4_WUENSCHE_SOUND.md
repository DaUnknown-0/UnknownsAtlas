# Sound an Layout/Spieltest, Amberhive V4

Die Klangkulisse ist implementiert. Among Us wurde vom Sound-Agenten nicht gestartet.
Bitte die folgenden Hoerpruefungen im ohnehin geplanten Spieltest ausfuehren.

## Einbau erhalten

- `src/AtlasAmberhiveSound.cs` gehoert dem Sound-Agenten.
- In `src/AtlasAmberhive.cs` stehen vier kleine, mit `Amberhive sound` markierte Einhaengepunkte: Feld, Aufbau, Tick und Dispose. Bitte beim Umbau der Mechaniken erhalten.
- Der Tick liest nur `dt`, Bruecke dreht, aktuelle Flutzone, `FloodLevel()` und lokale Rutschenfahrt. Keine neuen RPCs.
- `src/AtlasPlugin.cs`: eine markierte Zeile bindet lokale Einstellungen.
- `UnknownsAtlas.csproj`: ein markierter Import bindet `tools/hive/sound/AmberhiveSound.targets` ein. Dort liegen Ressourcen und Decoder-Pakete. Der Decoder wird beim Build in die Mod-DLL integriert.
- Raum- und Objektquellen folgen den generierten Kartendaten. Prop-Arten `queen_throne`, `brood_cradle`, `bellows_big`, `nectar_press`, `wax_cauldron` werden erkannt. Fehlen sie, gelten die Raumzentren als Ersatz.

## Einstellungen fuer jeden Client

In der lokalen `BepInEx/config/com.daunknown0.atlas.cfg`:

```ini
[Amberhive Sound]
Enabled = true
Volume = 60
```

`Volume` hat den Bereich 0 bis 100. `Enabled = false` oder `Volume = 0` macht nur diesen Client still.
Kein Host-Schalter, keine Netzwerkuebertragung. Die Effektlautstaerke des Spiels wirkt zusaetzlich ueber `SfxChannel`.
Config vor Spielstart bearbeiten oder mit einer vorhandenen Config-Oberflaeche neu laden. Reines Editieren der cfg bei laufendem Spiel loest von sich aus kein Reload aus.

## Hoerpruefung

1. Eine und zwei Etagen: Mead Hall verlassen, Brunnen umrunden, Queen's Chamber und Brutwaben besuchen. Das Summen soll dort dichter werden; Uebergaenge sollen weich sein. Auf der Krone sollen die Maschinen des Erdgeschosses nicht durchdringen.
2. Honey Well: leises, tiefes Honig-Blubbern. Bellows: pumpende Luft mit Holzknarzen. West/East Press: dumpfes Pressen. Wax Foundry: feines Brodeln. Mead Hall: seltene kleine Glockentoene, klar leiser und anders als der Notfallknopf.
3. Mindestens 30 Sekunden an einem Ort stehen: keine Knackser an der 12-Sekunden-Loopgrenze. Glockenschleife dauert 24 Sekunden.
4. Bruecke: mechanischer Klang nur waehrend der Drehung, kurzer weicher Ausklang. Keine zusaetzliche akustische Warnung vor der Drehung.
5. Flut: Geraeusch erst beim sichtbaren Anstieg, nicht waehrend der Warnphase. In der aktiven Flaeche gleichmaessig, mit Abstand zum Rand leiser. Anstieg/Abfluss folgen dem Wasserstand; danach still. Alle vier Zonen pruefen.
6. Rutsche mit zwei Etagen: weiches Rauschen nur waehrend der eigenen freigegebenen Fahrt mit kurzem Ausklang. Auch Host und Gast getrennt pruefen. Andere Spieler werden nicht akustisch verfolgt.
7. Meeting mitten in einer Drehung, Flut oder Fahrt: sofort vollstaendig still. Auch beim Rauswurf und beim Skip. Nach dem Meeting Klang wieder passend zur Position und zum aktuellen Mechanikzustand.
8. Rundenende waehrend eines Klangs: sofort still, kein Neustart im Ergebnisbildschirm oder in der Lobby. Anschliessend neue Runde und Kartenwechsel testen: keine alten Sounds oder Doppelungen.
9. Zwei Clients: Gast schaltet `Enabled` aus, Host hoert weiter. Danach Gast mit `Volume = 0`, 30, 60 und 100 testen. Optionen koennen nicht vom Host ueberschrieben werden.
10. Spiel-Effektlautstaerke auf 0: auch Amberhive still. Bei normaler Effektlautstaerke mit Voice-Chat, Aufgaben, Kill/Report und Sabotagealarm pruefen. Standard 60 soll deutlich im Hintergrund bleiben. Bei Bedarf nur den lokalen Regler reduzieren.

## Offene Rueckmeldung

- Subjektive Klangqualitaet und Lautstaerke im echten Spiel sind noch offen. Offline-Pruefung ersetzt das Hoeren im Spiel nicht.
- Keine zusaetzlichen Eingriffe in Grafik, Layout, Mechaniken oder reaktive Umgebung erforderlich.
