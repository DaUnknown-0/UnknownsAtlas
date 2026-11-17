# Amberhive Stil V2 "Bernsteinlicht" (15.11.2026)

Leitidee: ruhige, kühle Böden, darauf kräftige Objekte in gestrichenem Holz, Messing und Honig; die Wachswände leuchten warm,
ihre Krone bleibt dunkel. Alles steht in `blender/hive_style.py` (Palette, Material, Linien, `render_sprite`, `render_to`).
## Palette (sRGB 0..1, Schlüssel in `PALETTE`)
- Boden (`fl_*`, Sättigung unter 0,25, Helligkeit 0,45 bis 0,88): Gang `fl_wax` 0,80/0,75/0,65, Dielen `fl_plank` 0,68/0,56/0,45,
  Schiefer `fl_slate` 0,50/0,53/0,58, Stein `fl_stone` 0,67/0,64/0,60, Sand `fl_sand` 0,77/0,70/0,59, Ton `fl_clay` 0,72/0,54/0,46,
  Salbei `fl_sage` 0,67/0,73/0,63, Flieder `fl_lilac` 0,76/0,71/0,79 mit `fl_violet` 0,56/0,44/0,63, Teppich `fl_teal` 0,40/0,56/0,55, Fuge `fl_joint` 0,50/0,43/0,37.
- Wand: Krone `wall_top` 0,26/0,16/0,13 mit Zellen `wall_cell*`, Kragen `wall_lip` 0,88/0,68/0,34, Stirn `wall_front` 0,86/0,60/0,24,
  Fußleiste `wall_base` 0,36/0,20/0,12, Leuchtzelle `wall_glow` 1,0/0,72/0,22. Honigsee `lake` 0,93/0,52/0,06 (`lake_deep`, `lake_light`).
- Objekte: gestrichenes Holz `paint_teal` 0,34/0,62/0,62, `paint_cream` 0,94/0,89/0,77, `paint_coral` 0,90/0,53/0,45, `paint_mint`,
  `paint_blue`, `paint_plum`; Nussholz `wood` 0,58/0,37/0,22; Messing `brass` 0,92/0,71/0,30; Honig `honey` 0,97/0,58/0,08;
  Wachs `wax` 0,95/0,80/0,50; Leder `leather`; Stein `stone`; Akzente `royal` 0,50/0,24/0,58, `teal`, `coral`, `red`; Licht `glow`, `flame`.
- Regel: höchstens ein Anstrichton plus Nussholz je Objekt, je Raum ein Ton (Keller Petrol, Kinderstube Mint/Creme, Lampenhaus Blau,
  Gießerei Koralle, Thron und Archiv Violett). Zuordnung je Art: `SKIN` in `blender/props_common.py`.
## Licht und Schattierung
- Kein Lampenlicht, kein Rauschen: das Material rechnet weiches Cel-Licht aus den Normalen vor der Scherung (`finish()`).
  Licht von links-vorn-oben (-0,42/-0,30/0,86). Drei Stufen (linear): Deckfläche 1,0, Stirn nach Süden 0,76, abgewandt 0,38;
  Schatten kippen ins Pflaumenbraune (0,38/0,32/0,37), nie ins Graue. Höchstlicht 1,10 nur auf Flächen zum Licht.
- Dazu: Glanzlicht (Metall, Honig, Glas), Randabdunklung an runden Körpern, AO in Ritzen, Abdunklung der untersten 0,3 m (nur Objekte).
- Jedes Objekt wirft einen weichen Bodenschatten (Hülle der bodennahen Punkte, 0,05 m nach rechts unten, Deckkraft bis 0,36).
- Leuchtendes ist unbeleuchtet (`finish(shade=False)`, in den Requisiten `flat()`) und bekommt einen Lichthof (`halo`, in den Requisiten `glow()`/`flame()`).
- Scherung y' = y + 0,59 z bleibt. Wandhöhe 1,4 m, Stirn läuft von 0,56 (Fuß) nach 1,14 (Kante).
## Linien (Freestyle) und Materialien
- Farbe 0,17/0,085/0,075. Außenkontur 0,027 m (gut 3 px bei 120 px/m), Innenkanten und Farbgrenzen 0,011 m mit Deckkraft 0,62.
- Bodenbelag und Wandkrone ohne Linien (Fugen aus Fugengrund und Helligkeitsstreuung je Fliese), Wachsmasse 0,034 m,
  Relief und Kragen 0,012 m, Teppiche und See 0,013 m halb durchsichtig. Schatten und Lichthöfe liegen in der Sammlung `nolines`.
- Materialien (`_KIND`): Holz und Anstrich mit Maserung längs zum Bauteil, Wachs wolkig und durchscheinend (Schatten heller), Metall mit hartem Glanz,
Honig/Glas mit kleinem scharfem Glanzpunkt, Stoff/Leder matt, Stein körnig, Boden mit großer leiser Wolke.
## Regeln für Konsolen, Türen und Szenen
- Nur `S.material(name)` aus der Palette nehmen; neue Töne als Schlüssel ergänzen, keine Tupel für große Flächen.
- Konsolen: Korpus im Anstrichton des Raums, Deckplatte Nussholz, Bedienteile Messing, Anzeigen als Leuchtfläche mit Lichthof.
  Böden sind hell und kühl, deshalb Konsolen nicht in Creme oder Hellgrau, sonst verschwinden sie.
- Türen (Wabenschott): Rahmen `wood_dark`, Zellen `wall_front`/`wall_glow` wie die Wandstirn, damit sie als Teil der Wand lesen.
- Szenen (Rauswurf): eigene Stufen über das Attribut `shade` gehen weiter (V1-Vertrag); für den neuen Stil `finish()` mit
  `shade=True` und Schatten in Pflaume statt Schwarz. Rendern immer über `S.render_to()` (Probelauf, sonst wird der erste Lauf nach einer
  Materialänderung zu dunkel).
## Beispielbilder
`art/props/_sheet.png` (alle 31 Requisiten), `art/props/_beispiel_raum.jpg` (Lampenhaus, Keller, Gang), `_out/preview_2f.png` (Karte),
`art/brand/brand_emblem.png`. Neu bauen: `blender/props_<gruppe>.py`, `blender/fx_build.py`, `blender/brand_build.py`, `gen_hive.py build --art`.
