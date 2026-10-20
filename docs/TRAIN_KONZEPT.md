# Polaris Express (Zugkarte), Konzept

Stand 2026-10-19 (Fassung 4). Atlas-Karte im Dateiformat (docs/MAP_FORMAT.md), erzeugt von `tools/gen_train.py`.

## Idee

Ein Nachtzug faehrt nach Osten, als Grundriss von oben wie jede Atlas-Karte. Die Hauptebene laeuft unten auf
einer Hoehe durch alle sieben Fahrzeuge (Schlusswagen, Gepaeckraum des Schlafwagens, Speisewagen, Telegraf und
Dynamo des Aussichtswagens, Gepaeck- und Generatorwagen, Korridortender, Lok). Drei Doppelstockwagen (Schlaf-,
Speise-, Aussichtswagen) haben darueber ein Oberdeck: Schlafabteile, Kueche, Aussichtskuppel, jeweils eine
Sackgasse mit Treppen an beiden Wagenenden. Durch den Tender fuehrt ein Gang in den Fuehrerstand, wie bei den
Korridortendern der LNER von 1928.

Die Oberdecks liegen im Zug genau ueber der Hauptebene. Eine Karte von oben kann zwei Ebenen nicht stapeln,
deshalb stehen sie als eigener Grundriss suedlich der Wagen ("UPPER DECK"). Jeder Doppelstockwagen hat an beiden
Enden eine Treppe (`AtlasStairs`): Use-Knopf am Absatz ("UP"/"DOWN"), kurze Blende, man steht am anderen Absatz.
Fassung 3 hatte es andersherum (Oberdeck durchgehend wie beim Superliner, Unterdecks als Sackgassen); das war
fuer Spieler unintuitiv (User 19.10.: "waere es nicht logischer andersrum?"), deshalb Fassung 4 mit der
Hauptebene unten und den Knotenraeumen (Storage, Cafeteria, Comms, Electrical) dort; MedBay, LifeSupp und Nav sind
wie auf der Skeld Sackgassen.

Fassung 1 (17.10.) hatte zwei Zuege nebeneinander mit Laufstegen quer ueber das Gleis, Fassung 2 einen
Doppelstockzug in der Seitenansicht mit Treppen als Gaengen nach "oben" im Bild. Beides ergab im 3D-Nachbau
keinen Sinn (User 18.10.): Der Nachbau liest die Karte als Grundriss, die Seitenansicht wurde dort wieder zu
zwei Streifen nebeneinander. Seit Fassung 3 ist die Karte ein echter Grundriss; das Feld `levels` in map.json sagt
3D-Werkzeugen, auf welcher Hoehe jede Flaeche liegt (Hauptebene 1,2 m, Oberdeck 3,5 m und 8 m weiter noerdlich).

```
 Oberdeck:                      [Schlafabteile]  [Kueche]      [Aussichtskuppel]
                                  ^        ^    ^       ^      ^           ^
 Hauptebene:  [Plattform|Buero]=[Gepaeckraum]=[Speisewagen]=[Telegraf|Dynamo]=[Generator|Post]=[Tender]=[Lok]
 = Faltenbalg, ^ Treppe (Use-Knopf)
```

## Fahrzeuge, Raeume und Skeld-Systeme

| Fahrzeug | Hauptebene (unten) | Oberdeck |
|---|---|---|
| Caboose (Schlusswagen) | Rear Platform: Shields, Conductor's Office: Security (Lochzange) | |
| Sleeper Car | Luggage Room: Storage (zwei Gepaeckkaefige) | Sleeper Car: MedBay (zwei Abteile, Fahrkartenkontrolle) |
| Dining Car | Dining Car: Cafeteria (Start, Notfallknopf) | Kitchen: LifeSupp |
| Dome Car | Telegraph: Comms, Dynamo Room: Electrical | Vista Dome: Nav |
| Baggage Car | Generator: UpperEngine, Mail Room: Admin (Lochzange) | |
| Tender | Tender: LowerEngine (Gang + Kohlenbunker) | |
| Locomotive | Cab: Reactor, Running Board: Weapons (Umlauf um den Kessel) | |

## Tueren (13 Skeld-Tueren: 7 senkrecht, 6 waagerecht)

Senkrecht: Faltenbaelge Schlusswagen/Gepaeckraum (Security), Gepaeckraum/Speisewagen und Speisewagen/Aussichtswagen
(Cafeteria), Aussichtswagen/Gepaeckwagen (UpperEngine), Gepaeckwagen/Tender (LowerEngine), Trennwaende
Generator/Postraum (UpperEngine) und Telegraf/Dynamo (Electrical). Offen: Tender/Lok, Buero/Plattform.
Waagerecht: zwei Schlafabteile (MedBay), zwei Gepaeckkaefige (Storage), zwei Luken zum Kohlenbunker (LowerEngine).

## Vents (13, drei Netze)

- West: Zugfuehrerabteil, Gepaeckraum, Kueche (oben), Speisewagen (der Speiseaufzug)
- Mitte: hintere Plattform, Schlafabteile (oben), Telegraf, Aussichtskuppel (oben)
- Ost: Dynamo, Generator, Postraum, Tender, Umlauf der Lok

Kameras an vier Faltenbaelgen, Monitore im Zugfuehrerabteil.

## Sabotagen

- Blown Dynamo (Licht, Vanilla-Schalter): Dynamo Room. Seit 19.10. bremst der Dynamoausfall den Zug sichtbar
  (Welt-Mechanik train: Bildlauf auf etwa ein Viertel, kein Rattern, nach der Reparatur zieht er wieder an).
- Telegraph Down (Comms, Vanilla): Telegraph
- **Runaway Train** (eigene kritische Sabotage, `AtlasRunaway`, ersetzt den Reaktor; User 19.10.): der Regler klemmt,
  der Zug beschleunigt (Bildlauf, Rattern, Funken), Ueberdruck 0..100 steigt ab 30 mit 1,5/s, Countdown 45 s. Bremsen
  nur zu zweit gleichzeitig an beiden Zugenden: Dampfbremse im Cab (Minispiel `brakelever`: Hebel ziehen und im
  gruenen Bereich halten, er kriecht zurueck) und Handbremse auf der Rear Platform (Minispiel `handbrake`: Rad im
  Uhrzeigersinn kurbeln, 0,6..1,5 U/s). Beide im Takt: -6/s; nur einer: haelt; niemand: steigt. Bei 0 behoben, bei 100
  oder Countdown-Ende entgleist der Zug (Impostor gewinnen). Kartendatei `"runaway": {seconds, button, brake, handbrake}`,
  Props `dampfbremse`/`handbremse`. Diagnose `world:runaway`, `runawaybrake`, `runawaywheel`, `runawayboth`, `runawaylose`.
- **Smoke in the Cars** (eigene kritische Sabotage, `AtlasSmoke`, ersetzt O2; Variante A "Dachluken", User 19.10.):
  Kohlenfeuer im Tender (Feuerschein an `smoke.source`), Rauchwolken, Sicht sinkt mit der Rauchdichte bis auf 32 %
  (Dichte steigt 0,07/s auf den Anteil geschlossener Luken). Drei Dachluken (Luggage Room, Dining Car, Mail Room) je
  einmal aufkurbeln (Minispiel `hatchcrank`, 2,5 Umdrehungen); alle offen = behoben, Countdown 60 s um = Impostor
  gewinnen. Props `dachluke_zu`/`dachluke_auf` an derselben Stelle, das Spiel zeigt je Zustand eines. Kartendatei
  `"smoke": {seconds, button, source, hatches}`. Diagnose `world:smoke`, `smokehatch`, `smokeall`, `smokelose`.
- Die Vanilla-Knoepfe fuer Reaktor und O2 sind auf der Sabotagekarte ausgeblendet (AtlasMuseumBuilder), die eigenen
  Knoepfe liegen auf dem Gleisbett zwischen den Baendern (Runaway bei x 23, Smoke bei x 18, Ticket bei x -7).
- **Conductor's Round** (eigene kritische Sabotage, `AtlasTicket`, Idee User 19.10. nach den O2-Masken in
  Submerged): der Kartenknopf liegt auf dem Gleisbett zwischen den Baendern. Alle Lebenden (auch die Impostor)
  muessen binnen 60 s an einer der beiden Fahrkarten-Lochzangen (Zugfuehrerabteil, Postraum; Use-Knopf "STAMP",
  Minispiel `ticketpunch`: Griff 0,7 s halten) ihren Fahrschein stempeln. Wer es nicht schafft, fliegt aus dem
  Zug (Tod ohne Leiche wie am Meeting-Ende). Haben alle gestempelt, ist sie behoben; ein Meeting beendet sie.
  Rote Pfeile und Blinken nur fuer Spieler ohne Stempel; Restzeit und Zaehler stehen fuer alle (auch Gestempelte und
  Geister) oben in der Bildmitte (AtlasCrisisHud) und in der Aufgabenliste. Beim Ausloesen bekommen die anderen
  Sabotagen wie in Vanilla 30 s Abklingzeit, eingefroren bis zum Ende (gleiche Regel seit 19.10. beim Rex).
  Kartendatei: `"ticket": {"seconds", "button", "stations"}`. Diagnose `world:ticket`, `world:ticketstamp`,
  `world:ticketlose`.

## Geprueft

18.10. im Freeplay (`maptest.sh`, MAP=train, TaskTest `world:stairs,world:stairsback:3`): 46 Konsolen,
13 Vents, 13 Tueren ohne Zaehlfehler, 4 Kameras, Bau 292 ms. Treppe hinab (Schlafwagen -> Gepaeckraum) und
hinauf (Kueche -> Speisewagen) mit Blende, Use-Knopf zeigt am Absatz das Treppensymbol mit UP/DOWN.
Offen: Online-Runde (andere sehen den Wechsel nur ueber die Positionsuebertragung), echte Grafik.
19.10. Fassung 4 (Ebenen getauscht, Conductor's Round) gebaut und lokal deployt, im Spiel noch ungeprueft.

## Welt-Mechanik "train" (`AtlasTrainWorld`, Kartendatei `"world": "train"`, seit 19.10.)

- Fahrt: die Kartendatei nennt unter `scroll` nahtlos kachelbare Landschaftsstreifen (Datei, px/m, y0, Breite in m,
  Parallaxe). Sie liegen hinter dem Boden (z FloorZ + 0,4) und laufen nach Westen; die Bodenkacheln sind als PNG mit
  Alpha ausserhalb des Zugs durchsichtig (AtlasAssets.FloorRes nimmt `_floor_<i>.png` vor `.jpg`). Geschwindigkeit
  6 m/s, Dynamoausfall 22 %, Runaway bis 260 %; Rattern der Kamera waechst mit der Fahrt.
- Effekte: Funken bei hoher Fahrt, Rauchwolken und Feuerschein waehrend Smoke in the Cars (Dateien `train_fx_spark.png`,
  `train_fx_smoke.png`, `train_fx_fire.png` des Grafik-Auftrags; fehlen sie, weiche Punkte).
- Spaeter: Tunnelfahrten (kurze Dunkelheit, nur Wagenlampen), Fahrgeraeusch.

Die Grafik (Landschaftsstreifen, durchsichtige Kacheln, Props und Minispiel-Bilder der beiden Sabotagen) liefert der
Grafik-Auftrag im Repo polaris-express-art (docs/TRAIN_ART.md); die Mechanik laeuft auch ohne sie mit gezeichneten Formen.
