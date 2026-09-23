# Lichtkette: `ShipStatus.CalculateLightRadius` — Analyse und Andockpunkt für UNKNOWN'S ATLAS

Stand: PoC-Durchgang 2026-08-26 · Ziel-Stack: AU 2024.11.26 · BepInEx be.697 · Reactor 2.3.1
Autoren-Basis: Original-Quelltexte NUR GELESEN (CLAUDE.md-Regel): TOR `ShipStatusPatch.cs`, UC `UCVision.cs`, UC `Werewolf.cs` (Auszüge), TOR `Helpers.cs`.

---

## 1. Die Pipeline in der Reihenfolge, wie Harmony sie ausführt

```
Aufruf: ship.CalculateLightRadius(NetworkedPlayerInfo player)
        │
        ▼
[0] VANILLA BODY (nativ)
        liest: this.Systems.ContainsKey(SystemTypes.Electrical), MinLightRadius,
               MaxLightRadius, SwitchSystem.Value, Crew-/ImpostorLightMod
        │
        ▼
[1] TOR PREFIX   (TheOtherRoles/Patches/ShipStatusPatch.cs, Zeile 15-81)
        kann Original abschalten (return false) und __result selbst setzen
        │
        ▼
[2] UC POSTFIX   (UnknownsCollection/UCVision.cs, Pipeline.Postfix, Zeile 56-77)
        komponiert AUF __result weiter (Dämpfer ×, Grants Max, Werewolf-Override)
        │
        ▼
[3] CHANCE POSTFIX  (ChanceMod, eigener Patch mit Priority.Last)
        rein multiplikativ (__result * vis) → reihenfolgenunabhängig
```

Postfixes laufen in Harmony auch dann, wenn ein Prefix mit `return false` das Original
abwürgt — genau darauf ist UCVisions Design gebaut (Datei-Kommentar, Zeile 24-25:
„TOR patches CalculateLightRadius with a PREFIX that returns false, so a postfix is the
only place that can have the last word").

---

## 2. Liest der TOR-Prefix die Instanz-Felder? → JA

`ShipStatusPatch.Prefix` (Zeile 17):

```csharp
if ((!__instance.Systems.ContainsKey(SystemTypes.Electrical) && !Helpers.isFungle())
    || GameOptionsManager.Instance.currentGameOptions.GameMode == GameModes.HideNSeek)
    return true;                       // ← Vanilla darf laufen (liest ebenfalls Felder)
```

Zwei Zweige, beide instanzbasiert:

1. **Abstinenz-Zweig:** Hat die Karte KEIN Electrical-System im `Systems`-Dictionary
   (und ist nicht Fungle), macht TOR gar nichts (`return true`) — der Vanilla-Body
   berechnet und liest dabei dieselben Instanz-Felder.
2. **Übernahme-Zweig:** Sonst setzt TOR `__result` über `GetNeutralLightRadius(__instance, …)`
   (Zeile 83-96):

```csharp
if (isImpostor) return shipStatus.MaxLightRadius * …ImpostorLightMod;
…
lerpValue = switchSystem.Value / 255f;
return Mathf.Lerp(shipStatus.MinLightRadius, shipStatus.MaxLightRadius, lerpValue)
       * …CrewLightMod;
```

Auch die Rollen-Sonderfälle im Prefix (Lighter Zeile 43-44, Hunter 48-51, Trickster 63,
Lawyer 68-69, PropHunt 23-27) lerpen ausschließlich gegen `__instance.Min/MaxLightRadius`.
**Keine hartkodierten Radien, keine Map-spezifischen Konstanten.**
Einziger Fremd-Pfad: `SubmergedCompatibility.GetSubmergedNeutralLightRadius` (Zeile 84-85) —
greift nur bei `map.Type == 6`, betrifft ATLAS (#20) nicht.

## 3. Liest der UCVision-Postfix die Instanz-Felder? → JA

`UCVision.Pipeline.Postfix` (UCVision.cs Zeile 56-77) verändert nie eine Konstante, sondern
komponiert auf dem hereinkommenden `__result`:

- Stufe 1 (Dämpfer): `__result *= Poltergeist.VisionDamp(p)` — multiplikativ.
- Stufe 2 (Grants): `__result = Mathf.Max(__result, FullCrewRadius(__instance))`
  mit `FullCrewRadius(ship) = ship.MaxLightRadius * CrewLightMod` (Zeile 51-52)
  → **liest `MaxLightRadius` als Instanzfeld.**
- Stufe 3 (Werewolf-Nacht): `Werewolf.ApplyNightOverride(ref __result, __instance, p)`
  (Werewolf.cs ~982-1021) leitet alles aus `ship.MaxLightRadius * mod` ab
  → **ebenfalls Instanzfeld**, keine festen Zahlen.

Der Datei-Kopf (Zeile 38-39) ist bindende Hausregel von UC:
*„Adding a new vision feature: put a predicate on the role … - do NOT add another
CalculateLightRadius patch."* Hintergrund: Audit 2026-08-11 M-5 (fünf konkurrierende
Postfixe mit absoluten `__result`-Zuweisungen vor der Konsolidierung).

ChanceMod bleibt bewusst AUSSERHALB (Priority.Last, rein multiplikativ — Kommentar
UCVision.cs Zeile 17-20).

---

## 4. Antwort: Wo dockt der ATLAS-Radius an?

**An den Instanz-Feldern — und sonst nirgends.**

Beide fremden Stufen lesen `MinLightRadius` / `MaxLightRadius` von der ShipStatus-Instanz
und hardcodieren nichts. Der ATLAS-PoC setzt therefore in `AtlasBuilder.ApplyEarlyIdentity`
(Awake-Postfix, also bevor irgendein Leser läuft):

```
ship.MinLightRadius = 2.0f;    // AtlasForest.MinLightRadius
ship.MaxLightRadius = 10.0f;   // AtlasForest.MaxLightRadius
```

Damit gilt automatisch, ohne eigenen Patch:

| Zustand | Ergebnis |
|---|---|
| Lichter an (`SwitchSystem.Value = 255`) | Crew ≈ `Lerp(2, 10, 1) * CrewLightMod` |
| Lichter sabotage (`Value → 0`) | Crew fällt Richtung `Min = 2` — TOR-Prefix liefert die Formel |
| Impostor | `Max * ImpostorLightMod` (TOR-Prefix) |
| UC-Rollen (Scout/Beacon/Poltergeist-Grants, Werwolf-Nacht) | komponieren auf unseren Werten via Max/Multiplikation |

**Kein vierter Patch auf CalculateLightRadius** — weder Prefix noch Postfix, auch nicht
mit „hohem Priority". Die Pipeline hat oben TOR und unten Chance fixe Plätze; UC hat die
Mitte als bewusste Eigentumszone (M-5). Ein ATLAS-Eingriff dort wäre exakt der Fehler,
den M-5 dokumentiert.

### Falls ATLAS später pro-Spieler-Vision braucht (Feature-Vorbehalt)

Der korrekte Weg wäre eine **Stufe in der UCVision-Pipeline** (Predikat + Max/Multiplikator
in Stufe 1 oder 2) — das heißt: Änderung in UC upstream planen (UC-Hausregel erlaubt neue
Features nur DORT), nicht einen parallelen Patch seitens ATLAS. Bis dahin decken die
Instanz-Felder + Electrical-Switch alles Standardverhalten ab; dynamische Nachtwerte sind
über `SwitchSystem.Value` (das TOR aus unseren Feldern lerpt) steuerbar.

## 5. Randbefund für den PoC (Q2/Q4-Schnitt)

- Ohne registriertes Electrical-System würde TOR abstinent bleiben und Vanilla lieferte
  dauerhaft `MaxLightRadius` (volle Helligkeit). ATLAS registriert deshalb wie LevelImposter
  (`li_src/MapBuilder.cs`, ResetMap) einen echten `SwitchSystem` unter
  `SystemTypes.Electrical` — damit ist die Kette sabotierbar/dunkelbar und TORs Lerp aktiv.
- `MapUtilities.Systems[SystemTypes.Electrical].CastFast<SwitchSystem>()` (TOR, Zeile 91)
  wirft still (try/catch) wenn das System fehlt — mit unserem Set sauber.

## 6. Warum es „kein RegisterCustomShipStatus" gibt (Q1-Vorbefund)

Die Annahme, Reactor 2.3.1 stelle `RegisterCustomShipStatus` / `MapSelection` bereit,
hat sich im Binaerscan der installierten DLL (`BepInEx\plugins\Reactor.dll`, v2.3.1)
nicht bestätigt: Identifier-Zähle gegen den UTF-8-Metadaten-Heap —

| Suchmuster | Treffer |
|---|---|
| `RegisterCustomShipStatus` | 0 |
| `CustomShipStatus` | 0 |
| `MapSelection` | 0 |
| `ShipStatus` (überhaupt) | 0 |
| `GetMapById` / `RegisterMap` | 0 |
| Kontrolle: `Reactor` | 43 |
| Kontrolle: `RegisterCustomRpc` | 1 |

Methode validiert (Kontrollmuster treffen; Scan über ASCII-Rohbytes funktioniert, weil der
.NET-#Strings-Heap UTF-8 ist). Folgerung: Registrierung ist Eigenleistung des Mods — ATLAS
fährt das bewiesene Replace-in-Place (LevelImposter-Muster) mit eigener Registry; Submergeds
Weg (injizierte ShipStatus-Subclass + eigene Szenenaufloesung) bleibt die Referenz für eine
spätere Ausbaustufe mit echter Lobby-Auswahl.
