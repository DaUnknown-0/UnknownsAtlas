# UNKNOWN'S ATLAS PoC — Installation & In-Game-Testprotokoll

Stand: 2026-08-26 · Build: `UnknownsAtlas.dll` v0.1.0 · Ziel: AU **2024.11.26**, BepInEx
**6.0.0-be.697**, Reactor 2.3.1, Spiel-Installation
`C:\Users\moritz\Downloads\Among Us - 4.7.0\Among Us - 4.7.0\`

Die DLL liegt fertig gebaut in `UnknownsAtlas\dist\UnknownsAtlas.dll`
(Alternativ selbst bauen: `dotnet build -c Release` im Projektordner; mit
`-p:AtlasDeployToGame=true` kopiert der Build sie selbst ins Spiel.)

---

## A. Installation (2 Schritte)

1. `UnknownsAtlas.dll` nach `BepInEx\plugins\` kopieren.
   (Nur die DLL — die `deps.json` im bin-Ordner wird NICHT benötigt.)
2. Spiel normal starten (TOR/UC/Chance bleiben unverändert daneben liegen).

Deaktivieren ohne Löschen: `BepInEx\config\com.daunknown0.atlas.cfg` →
`General.Enabled = false`. Kein Konflikt-Risiko für andere Mods: ATLAS hängt nur an
`ShipStatus::Awake` und `ShipStatus::Begin` (beide Postfixe, try/catch-gekapselt) und ruft
keine Reactor-API auf.

## B. Erwartete Logzeilen beim Start

Datei: `BepInEx\LogOutput.log` (bzw. Konsole). Reihenfolge wie unten; die ersten vier
Zeilen müssen SOFORT nach dem Laden der Plugins stehen:

```
[Info : Unknown's Atlas] [Atlas] v0.1.0 loaded (com.daunknown0.atlas)
[Info : Unknown's Atlas] [Atlas] Registry: #20 'Forststation Nadelkamm'
[Info : Unknown's Atlas] [Atlas] Patches applied: ShipStatus::Awake (postfix), ShipStatus::Begin (prefix + postfix)
```

## C. Testdurchlauf

### C1 — GATE-FRAGE 1: Lädt die selbstregistrierte Karte? (Freeplay zuerst!)

Warum Freeplay: kein Netzwerk, sofortiger Neustart über den Kartenwechsel, kein Risiko für
Lobbys. Der Online-Nachweis folgt in C2.

1. Hauptmenü → **Freeplay** („Lokales Spiel" / Rolle frei wählen).
2. Im Freeplay-Menü Karte beliebig wählen (z. B. The Skeld).
3. Log prüfen — beim Laden der Karte MUSS erscheinen:

```
[Atlas] Awake: identity on '<Schiffsname>' -> Type=20, spawn=(x,y), lights min=2.0/max=10.0
[Atlas] task counts clamped to 0 for Begin() - normal(a/b/c) opts(...)
[Atlas] Begin postfix entered on '<Schiffsname>'
[Atlas] BEGIN BUILD 'Forststation Nadelkamm' over '<Schiffsname>' (type=20)
[Atlas] physics layer captured from '<Objektname>': <n>
[Atlas] detached MapPrefab/EmergencyButton/MedScanner ... -> ship root
[Atlas] wiped n top-level object(s): <Namen>   <- die Vanilla-Raeume MUESSEN hier stehen
[Atlas] kept 3 object(s): ..., remaining children under ship root: 3
[Atlas] floor texture 2800x2000 @ 40 px/u -> 70x50 u
[Atlas] floor built from grundriss v4
[Atlas] boundary on layer <n>: 8 closed chain(s), <n> points
[Atlas] area anchors: 13
[Atlas] teleported n player(s) onto the spawn ring
[Atlas] BUILD DONE 'Forststation Nadelkamm': 70x50 u, 13 areas, 8 boundary chain(s), ...
```

Reihenfolge beim Rundenstart: der Clamp meldet sich einmal vor dem Bau, dann kommt der
Postfix mit der Bau-Kette. `Awake` liefert nur noch die Identitätszeile, nicht mehr den Bau.

```
[Atlas] task counts clamped to 0 for Begin() - normal(a/b/c) opts(d/e/f) opts(...)
[Atlas] Begin postfix entered on '<Schiffsname>'
```

**ABGELESEN (Q1):** Wenn `BEGIN BUILD` + `BUILD DONE` stehen und die Szene unten
beschrieben aussieht → selbstregistrierte Karte lädt. ✅/❌ notieren (+ Schiffsname).

**MUSS-KRITERIUM (Regression vom 25.08.2026):** Im Log darf KEIN
`ArgumentOutOfRangeException ... at ShipStatus.AddTasksFromList` mehr stehen. Diese
Exception verließ `ShipStatus.Begin()`, unterband jeden Postfix darauf und war die Ursache
dafür, dass die Karte nie entstand. Verhindert wird sie allein dadurch, dass die
Task-Prefab-Arrays **gefüllt bleiben** (`ApplyEarlyIdentity`). Der Clamp im Begin-Prefix
reicht dafür nachweislich NICHT: im Lauf um 18:59 kam die Exception auch bei `0/0/0` in allen
erreichbaren Options-Instanzen.

**Nebenbefund zum Mitlesen:** Weichen die Tripel in der `task counts clamped`-Zeile
voneinander ab (`normal(0/0/0)` gegen `opts(1/2/1)`, genau so im Lauf um 18:59), sind
`GameOptionsManager.currentNormalGameOptions` und `GameManager.LogicOptions.currentGameOptions`
getrennte Objekte. Das erklärt, warum TORs Clamp auf die erste Instanz im Freeplay
wirkungslos blieb.

**Wipe-Kontrolle (Lauf 21:0x):** Die Zeilen `detached ... from '<Elternobjekt>'`, `wiped n
top-level object(s): <Namen>` und `kept n object(s): ..., remaining children under ship root: n`
sind das Prüfmittel dafür, ob die Vanilla-Karte wirklich gefallen ist. Vorher blieb die
komplette Cafeteria stehen, weil der EmergencyButton in ihr hängt und `WipeChildren` alles
verschonte, WORIN ein Referenzobjekt steckt. Die drei Objekte werden jetzt vor dem Wipe an
den Ship-Root umgehängt.

**Erwartete Nebenwirkung im Freeplay:** Der Taskbar-Dialog „Normally The Crew would have just
won because the task bar is full. For Practice, we issue new tasks instead." erscheint. Trotz
Clamp auf allen vier erreichbaren Options-Instanzen (`normal(1/2/1) opts(1/2/1) opts(1/2/1)
opts(1/2/1)` → alle auf 0) vergibt Freeplay weiterhin einen Task (beobachtet: „Electrical:
Divert Power to Lower Engine"). Die Freeplay-Task-Vergabe läuft also an den Options vorbei.
Für den PoC kosmetisch: die zugehörige Konsole ist weggewipt, der Task ist nicht erfüllbar.

**SOLL-BILD:** Fables Grundriss v4 als Welt: 13 Lichtungen, durch braune Pfade zu einem
Netz verbunden, dazwischen dunkles Dickicht. Nordklippe mit Klippenpfad, Höhlendurchgang
unter dem Felssporn, Bach in der Südostecke, Gebäude in Feldstation / Messbunker /
Probenlager / Generatorhaus / Pumpenhaus / Vorratslager. Spieler startet auf der
Lagerfeuer-Lichtung in der Mitte.

### C2 — GATE-FRAGE 2: Begehbar?

Im selben Freeplay-Lauf:

1. Laufen: Die Pfade müssen tragen und das Dickicht muss halten. Karte ist 70×50 u, also
   deutlich größer als Skeld: bis zum Pumpenhaus (Südosten) sind es ~26 u.
   Kritische Stellen: Höhlendurchgang (schmal), Steilpfad zur Klippe, Bachquerungen
   (Bachsteg und Trittsteine).
2. Spawn: Nach Kartenstart steht der Spieler auf der Lagerfeuer-Lichtung (Spawnring 2.4 u).
3. Kamera: folgt normal, kein Zoom-Ausreißer.
4. Minimap (Karte-Taste): öffnet OHNE Crash — zeigt aber NOCH das alte Vanilla-Bild
   (MapPrefab wurde absichtlich erhalten). Das ist dokumentierter PoC-Stand, kein Fehler.
5. Notfall-/MedScan-Referenzen: Knopf drücken darf nicht hart crashen (Overlay zeigt alte
   Grafik — ebenfalls erhaltene Referenz).

**ABGELESEN (Q2):** Kollider halten (ja/nein, wo), Spawn korrekt (ja/nein), Kamera ok
(ja/nein), Minimap-Crash (ja/nein).

### C3 — GATE-FRAGE 3: TOR + Unknown's Collection daneben unbeschädigt?

1. Log auf Exceptions durchsuchen: `Exception` / `Harmony` / `TOR` / `[UCVision]`.
   Erwartet: KEINE neuen Zeilen gegenüber einem Lauf ohne ATLAS.
2. Online-Host (klassisch, 2+ Spieler oder allein hosten): Lobby starten, Karte Skeld.
   Beim Rundenstart baut ATLAS um (gleiche Logzeilen wie C1). TOR-Rollenspawns laufen
   normal (Rollenzuweisung sichtbar), UC-Rollen-Handshake unverändert.
3. Gezielt eine TOR-Rolle mit Karten-Annahme testen: Security Guard (Kamera-Platzieren
   muss sauber „nicht möglich" reagieren — Buttons.cs fällt für unbekannte MapId auf
   generische Konsolensuche zurück und bricht friedlich ab), Lighter/Hacker kurz antesten.
4. Sabotage-Menue NICHT als Balance-Test nutzen (Dummy-Systeme sind registriert, Reparatur-
   Konsolen existieren aber nicht → Reaktor/O2-Sabotage würde unbehebbar laufen). Für den
   PoC: Sabotagen unerwünscht.

**ABGELESEN (Q3):** Exceptions ja/nein, Rollenverhalten unauffällig ja/nein,
MapId-Fall notiert: GameOptions-MapId bleibt VANILLA (Szenensicherheit), Identität läuft
über `ShipStatus.Type = 20`; alle TOR-`Helpers.isXxx()`-Checks fallen für 20/„unbekannt"
auf neutrale Defaults (Admin-Sprite → Polus-Fallback, Vent-Netzwerke → leer, Kamera-
Rotation → Standard). Submerged(6)/LevelImposter(7)-Belegung ist dokumentiert und
vermieden (ID-Registry.md).

### C4 — GATE-FRAGE 4: Lichtkette

Im Freeplay-Lauf (C1):

1. Log-Zeile `lights min=2.0/max=10.0` bestätigt unsere Felder.
2. Sichtprüfung: Crew-Sichtweite wirkt „Skeld-artig" (nicht Volllicht-weiß, nicht
   Tastatur-nah). Bei Lights-Sabotage würde die Sicht Richtung Min fallen — Sabotage im
   PoC laut C3.4 auslassen, Messung optional später.
3. UC-Seite: Werwolf/Scout/Beacon-Runde optional anstoßen und beobachten, dass deren
   Vision-Features auf der ATLAS-Karte normal wirken (sie lesen dieselben Felder).

Vollständige Kette + Begründung: `docs/lightradius_chain.md`. Kurzform:
TOR-Prefix liest Instanzfelder (+ SwitchSystem.Value) — UCVision-Postfix liest
`MaxLightRadius` instanzbasiert und komponiert nur — Chance multipliziert zuletzt.
ATLAS dockt AUSSCHLIESSLICH an den Instanzfeldern an; **kein vierter Patch**.

**ABGELESEN (Q4):** Felder gesetzt (Logzeile), Sicht plausibel (ja/nein), UC-Features
wirken (optional ja/nein).

## D. Bekannte Grenzen des PoC (absichtlich, keine Defekte)

| Grenze | Grund | Folge |
|---|---|---|
| Kein Use-Prompt an der Konsole | Keine Tasks zugewiesen (leere Task-Arrays schützen vor Broken-Consoles und Insta-Win) | Konsole ist Position/Pipeline-Nachweis; Verdrahtung = nächster Schritt |
| Minimap zeigt altes Bild | MapPrefab bewusst erhalten (Crash-Schutz) | Eigener Minimap-Bau später |
| Sabotage-Reparaturen nicht spielbar | Dummy-Systeme ohne Konsolen | Sabotage im PoC nicht auslösen |
| Online: Clients brauchen ATLAS | Bau läuft client-lokal in Begin; ohne Mod sieht Client Vanilla-Szene | Testprotokoll-C2.2 nur mit voller Mod-Gruppe |
| GameOptions-MapId bleibt vanilla | Unbekannte MapId würde Szenenauflösung brechen (Szene ≠ Typ) | Echte Lobby-Auswahl = Ausbaustufe (Submerged-Muster: eigene Szenenaufloesung) |

## E. Rollback

Einzelne Datei `BepInEx\plugins\UnknownsAtlas.dll` löschen — sonst nichts. ATLAS legt
keine Dateien außer seiner Config an und ändert keine anderen Plugins.
