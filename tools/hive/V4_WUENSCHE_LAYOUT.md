# Layout an Grafik, V4

Die Layoutquelle ist tools/hive/hive_layout.py. Bitte diese Datei und gen_hive.py nicht parallel aendern.

- Neue offene Verbindung Keeper's Office zu Waggle Studio: Rechteck (11.7, 7.9) bis (15.0, 9.5). Der Spieltest fand am zuvor kuerzeren Ende bei x 14.4 eine Fangstelle an der gefasten Raumecke. Keine Tuer, schafft einen Rundweg auch mit einer Etage.
- Neue offene Verbindung Queen's Chamber zu Sun Compass: Rechteck (3.0, -15.2) bis (6.8, -13.2). Keine Tuer. Bitte gut lesbare Bodenfortsetzung.
- Vorhandene Tuerlabels und Oeffnungsbreiten bleiben bestehen, damit eure Bilder weiter passen.
- Zusaetzlicher Spieltest-Fix: Verbindung West Press zu Wasp Watch reicht jetzt von (-14.8, -13.8) bis (-12.5, -12.8) in beide gefasten Raeume hinein. Tuer hex-V10 bleibt 1.0 m breit, ihr Mittelpunkt wandert nur nach (-13.65, -13.3). Keine neuen Bilder noetig.
- Honigzone 2 passt nun zum echten Westgang: x -19.0 bis -17.2, y 3.2 bis 7.1. Falls moeglich das Zonenbild anpassen, der Code skaliert es passend.
- Rutsche oben bei (3.0, 26.0), unten bei (3.1, -3.25), Ausstieg (2.7, -2.7). Kleine Verschiebung fuer freien Spielerkreis. Bestehende Deko kann bleiben.
- Mit zwei Etagen liegen Vent 9 und 10 auf Sun Deck (-11.5, 25.0) und Drone Dock (11.5, 25.0). Dasselbe Ventbild, keine neue Grafik noetig.
- Bruecke blinkt vor der Drehung drei Sekunden bernsteinfarben. Honigzone pulsiert 2.5 Sekunden vor der Verlangsamung. Bitte moeglichst erkennbare Randmarkierung bei neuen Grafiken.
- Weltmechaniken hatten vorher den geerbten Faktor 1.2 des Ship-Roots. Das ist im Code korrigiert. Brueckenbild und See muessen daher ohne kuenstliche Vergroesserung zusammenpassen.

Build immer mit `python tools/hive/gen_hive.py build --art`. Er rendert die Boeden aus den aktuellen Layoutformen neu.

## Rueckmeldung auf Grafik Runde 2

Neun vorgeschlagene Platzierungen sind in PROPS aufgenommen, mit bestehendem Bildmass und echter Kollision. Vier davon nur mit Krone. Nicht aufgenommen: das auf 1.2 m verkuerzte jar_shelf im Buero, weil sein bestehendes Bild 3.2 m breit ist; das suedliche jar_shelf im Jar Cellar, weil es den Zugang neben crate_stack verengt. Konsolen und Rettungswege haben Vorrang. Laufwege und Spieltests werden nach dem Einbau erneut geprueft.

Vent 6 wurde wegen der beiden neuen Tische nach (-4.45, 7.7) neben den Westtisch verschoben. Das bisherige Netz bleibt gleich.

Honigfluss und Wandtropfen werden als rein optische Spritefolgen unter Figuren eingebunden, sobald der JSON-Vertrag und alle acht Bilder verfuegbar sind. Keine neue Kollision, keine weiteren Netzwerkpakete.

Honig-R2-Vertrag inzwischen gelesen und umgesetzt: zwei Rinnen, drei Tropfstellen, 100 ppm, 8 fps, Pivot Mitte, Richtungen 0/180 Grad, Tropfphasen 0/3/5. Alle fuenf Folgen werden in AtlasAmberhive.cs mit normaler Sichtmaske und ohne Kollider abgespielt. Keine weitere Schraegprojektion im Code.

## Baukoordination

Gameplay ist bei den abschliessenden DLL-Spieltests. Bitte weitere `gen_hive.py build --art` erst nach diesen Tests ausfuehren oder in V4_WUENSCHE_GRAFIK.md anmelden. Ein paralleler Asset-Bau hat bereits waehrend der Vorschau einen kurzzeitig unvollstaendigen Prop-Atlas geliefert. Layout und Konsolenkoordinaten fuer Runde 2 sind jetzt fest.
