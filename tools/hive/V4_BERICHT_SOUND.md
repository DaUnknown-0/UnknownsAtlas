# Amberhive V4: Bericht Klangkulisse

Stand: 16.11.2026. Implementierung in der Arbeitskopie `UnknownsAtlas_AmberhiveV4`.

## Ergebnis

Amberhive hat eine lokale, ortsabhaengige Klangkulisse mit zehn eigenen Vorbis-Loops.
Alle Sounds stammen aus deterministischer numpy-Synthese, ohne Samples aus Among Us, Aufnahmen oder fremde Klangquellen.
ACE-Step war nicht erforderlich. ffmpeg wurde ausschliesslich zum Kodieren verwendet, niemals zum Dekodieren oder zur Samplezahl-Pruefung.

Der Sound folgt der echten lokalen Spielerposition und den vorhandenen Raum-, Prop- und Mechanikdaten.
In der Brutwabenstube und nahe dem Thron verdichtet sich das Grundsummen durch einen zweiten, vielstimmigeren Loop.
Die Entfernungsdaempfung verlaeuft weich, mit voller Lautstaerke im Nahbereich und Null ausserhalb des Radius.
Kein Audio verfolgt andere Spieler, keine neuen Netzwerkpakete, keine Aenderung von Gameplay oder Host-Optionen.

## Klangliste

Alle Dateien liegen unter `assets/amberhive/sound/`. Format: Ogg Vorbis, mono, 24.000 Hz.
Alle ausser der Glocke enthalten 288.000 Frames und dauern 12 Sekunden.
Die Glocke enthaelt 576.000 Frames und dauert 24 Sekunden.
Die zehn Ogg-Dateien belegen zusammen 288.897 Bytes, rund 282 KiB.

| Datei | Klang / Quelle | Volle Naehe bis | Stumm ab |
|---|---|---|---|
| `hive_buzz.ogg` | Leises Grundsummen bei Raumzentren und Brunnen | 0 m | 9 m |
| `brood_buzz.ogg` | Dichteres Summen bei `queen_throne` und `brood_cradle` | 1,6 m | 7 m |
| `honey_well.ogg` | Tiefes Honig-Blubbern um die Brunnenmitte | 2,5 m | 8 m |
| `bellows.ogg` | Luftstoss und sanftes Holzknarzen bei `bellows_big` | 1,5 m | 6,5 m |
| `nectar_press.ogg` | Rhythmisches, dumpfes Pressen bei beiden `nectar_press` | 1,5 m | 6,5 m |
| `wax_foundry.ogg` | Feines Wachs-Brodeln bei `wax_cauldron` | 1,5 m | 6,5 m |
| `mead_chimes.ogg` | Drei seltene kleine Glockentoene am Mead-Hall-Glockenplatz | 1 m | 7 m |
| `bridge_turn.ogg` | Gedampfte Lager-/Holzbewegung waehrend der Drehung | 2,5 m | 8 m |
| `honey_flood.ogg` | Zaehes Stroemen waehrend Anstieg, Halten und Abfluss | 0,5 m vom Zonenrand | 6 m vom Zonenrand |
| `nectar_chute.ogg` | Weiches Rutschenrauschen bei eigener freigegebener Fahrt | Lokal am Fahrer | Nach Fahrt |

Die Flut nutzt Abstand zur Polygonflaeche, nicht zum Mittelpunkt. Innerhalb einer aktiven Zone gilt derselbe Naehepegel.
Die Flutlautstaerke folgt `FloodLevel()`. Die Warnphase bleibt still.
Bruecke und Rutsche werden erst mit Beginn der Bewegung hoerbar. Ihr Ausklang dauert hoechstens rund 0,24 Sekunden.
In einer Karte mit nur einer Etage bleibt der Rutschenklang aus.
Mehrere gleichartige Quellen nutzen das Maximum ihrer Entfernungspegel. Der Pressenclip laeuft deshalb auch beim schnellen Wechsel von West nach Ost niemals doppelt.

## Pegel und lokale Einstellungen

Die neuen Eintraege in der lokalen BepInEx-Konfiguration `com.daunknown0.atlas.cfg` sind:

```ini
[Amberhive Sound]
Enabled = true
Volume = 60
```

`Enabled = false` oder `Volume = 0` schaltet nur den eigenen Client ab.
`Volume` akzeptiert 0 bis 100 Prozent. Keine Synchronisierung mit dem Host.
Die Gesamtlautstaerke aller gleichzeitig aktiven Stimmen ist vor diesem Regler auf 0,24 begrenzt.
Beim Standardwert 60 ergibt das hoechstens 0,144 als Summe der AudioSource-Pegel, vor dem Effektmixer des Spiels.
Die Assets selbst sind leise, mit RMS etwa 0,076 bis 0,160 und ohne harte Transienten.
Alle Quellen laufen ueber `SoundManager.SfxChannel`; der Effektlautstaerkeregler des Spiels gilt weiterhin.
AudioSources haben niedrige Prioritaet 220. Keine Musikspur, kein Stereo-Ortungsvorteil und kein Doppler.

Aenderungen an den geladenen ConfigEntry-Werten wirken im naechsten Tick, auch ueber `Config.Reload()` oder eine vorhandene Config-Oberflaeche.
Die cfg wird nicht aktiv vom Soundcode ueberwacht. Fuer reines Dateieditieren empfiehlt sich die Aenderung vor dem Spielstart.

## Implementierung und Einhaengepunkte

- `src/AtlasAmberhiveSound.cs`: kompletter Laufzeitcode, Konfiguration, Ressourcenladen mit NVorbis, Distanzmischung, Lautstaerkedeckel und Lebenszyklus.
- `src/AtlasAmberhive.cs`: markiertes Feld `_sound`, Aufbau in `OnBuilt`, ein Aufruf am Ende der Mechanik-Ticks, Dispose in `OnDestroy`.
- `src/AtlasPlugin.cs`: eine markierte Zeile `AtlasAmberhiveSound.Bind(Config)`.
- `UnknownsAtlas.csproj`: ein markierter Import von `tools/hive/sound/AmberhiveSound.targets`.
- `tools/hive/sound/AmberhiveSound.targets`: Vorbis-Ressourcen und Paketverweise NVorbis 0.10.5 / ILRepack 2.0.34.2.
- `tools/hive/sound/AmberhiveVorbisMerge.targets`: Decoder wird aus der sauberen Zwischenassembly in die Mod-DLL integriert, sowohl bei Debug als auch Release, vor optionalem Deployment.
- `tools/hive/sound/LICENSE_NVORBIS.txt`: MIT-Hinweis fuer den Decoder, ebenfalls als `UnknownsAtlas.Licenses.NVorbis.txt` eingebettet.

SoundManager besitzt die AudioSources. Der Soundcode zerstoert diese nicht und spielt jeden eigenen Clip nur einmal gleichzeitig.
Die Clipdaten werden mit `ClipFill.SetData` in kleinen Il2Cpp-Bloecken uebertragen.
Dekodierung erfolgt erst bei tatsaechlich hoerbarer Quelle, gecacht bis zum Kartenabbau. Dann werden alle Clips freigegeben.
Ein defekter oder fehlender Clip erzeugt eine einzelne Warnung fuer diese Runde und wird nicht wiederholt geladen.

Eigene Harmony-Prefixe stoppen sofort bei `MeetingHud.Start` und `AmongUsClient.OnGameEnd`.
Ein zusaetzlicher Hud-Postfix prueft Karte, Config, Meeting, Rauswurf, Lobby und Spielzustand, auch wenn der Welt-Tick nicht mehr laeuft.
Nach Spielende verhindert ein gesetzter Rundenabschlussstatus jeden Neustart bis zur naechsten Weltinstanz.
Nach einem Meeting wird die Atmosphaere passend zur aktuellen Position neu eingeblendet.

## Reproduktion und Pruefung

```powershell
python tools/hive/sound/generate_sound.py
dotnet build
dotnet build -c Release
dotnet run --project tools/hive/sound/verify/Verify.csproj -c Release -- .
```

Der Generator braucht numpy und ffmpeg nur als Encoder. Der Offline-Pruefer benoetigt das lokal vorhandene .NET 8 SDK.
Die Mod selbst bleibt bei net6.0 und dem bestehenden BepInEx-/Il2Cpp-Stack.

- `tools/hive/sound/manifest.json`: erwartete Framezahlen und Pegel der Original-Synthese.
- `tools/hive/sound/verification.json`: gemessene Werte nach NVorbis-Dekodierung und Ergebnis der Offline-Pruefungen.
- Alle zehn Dateien: NVorbis liefert exakt die erwarteten Frames, einschliesslich des kompletten Endes. Keine Verkuerzung um 128 Frames.
- Alle dekodierten Samples sind endlich; Peak unter 0,85, RMS unter 0,2, Gleichspannungsanteil unter 0,005.
- Loopnaht: Samplesprung unter 0,04 und maximal 1,5-facher 99-Prozent-Wert regulaerer benachbarter Sampleschritte, mit 0,004 als Untergrenze. Alle zehn bestehen.
- Offline-Harness kompiliert den echten `src/AtlasAmberhiveSound.cs` gegen kleine Engine-Doubles und verwendet beide aktuellen Kartendateien.
- Abschliessender Offline-Lauf: 8.339 erfolgreiche Pruefungen einschliesslich der Pegelgrenze pro simuliertem Frame, null doppelte Clip-Starts.
- Geprueft: Raumwechsel, Summen-Hotspots, beide Pressen ohne Clip-Doppelung, alle vier Flutzonen, Rutsche in beiden Etagenvarianten, Gesamtpegel, Client-Schalter, Config 0, Meeting/Resume, Rauswurf, Lobby, Freeplay, Kartenwechsel, Spielende und Freigabe.
- Metadatenpruefung der Release-DLL: zehn eingebettete Ogg-Dateien, VorbisReader enthalten, kein externer Assembly-Verweis auf NVorbis.
- Normaler und Release-Build erfolgreich. Eine bereits vorhandene Warnung CS0169 in `src/AtlasAssetStore.cs` wegen `_running`; keine Sound-Warnungen.

## Offene Punkte

Der echte Hoertest fuer Klangcharakter, Voice-Chat-Vertraeglichkeit, Spiel-Effektmixer und Audio-Lebenszyklus steht noch aus.
Die Offline-Doubles testen nicht die echte Unity-/Il2Cpp-Ausfuehrung oder die Installation der Harmony-Patches.
Der Sound-Agent hat Among Us nicht gestartet und nichts ins Spielverzeichnis kopiert.
Die konkrete Checkliste fuer den Layout-/Spieltest-Agenten steht in `tools/hive/V4_WUENSCHE_SOUND.md`.
Keine weiteren Eingriffe in fremde Quelldateien angefordert. Kein Commit, Push oder Tag.
