using UnknownsAtlas;

int checks = 0;
void Check(bool ok, string label)
{
    if (!ok) throw new Exception("FEHLER: " + label);
    checks++;
}
void Close(float actual, float expected, string label) => Check(MathF.Abs(actual - expected) < .0001f, label);

AmberhivePollenWalker Loaded()
{
    var w = new AmberhivePollenWalker(0, 0, 0);
    Check(!w.Sample(.2f, 0, .26f, true, true, out _), "Aufnahme ohne erfundenen Schritt");
    Check(w.Sample(.6f, 0, .4f, true, true, out _), "Schritt im Pollenbereich");
    return w;
}

var bare = new AmberhivePollenWalker(0, 0, 0);
for (int i = 1; i <= 30; i++)
    Check(!bare.Sample(i * .5f, 0, i * .4f, false, true, out _), "Ohne Pollen keine Spur");

var still = Loaded();
for (int i = 1; i <= 20; i++)
    Check(!still.Sample(.6f, 0, .4f + i * .4f, false, true, out _), "Stillstand erzeugt keine Schritte");

var expiry = Loaded();
Check(expiry.Sample(1.2f, 0, 1f, false, true, out _), "Bepollung nach Verlassen aktiv");
Check(!expiry.Sample(1.25f, 0, 6.41f, false, true, out _), "Sechs Sekunden spaeter keine neue Spur");
Check(expiry.Sample(1.9f, 0, 6.9f, true, true, out _), "Neuer Eintritt nimmt Pollen erneut auf");

var jitter = Loaded();
Check(!jitter.Sample(.9f, 0, .8f, false, true, out _), "Netzwerkzittern unter Schrittabstand unterdrueckt");
Check(jitter.Sample(1.3f, 0, .9f, false, true, out var left), "Ausreichende Bewegung erzeugt Schritt");
Check(!jitter.Sample(1.8f, 0, 1f, false, true, out _), "Schrittfrequenz begrenzt");
Check(jitter.Sample(2.1f, 0, 1.4f, false, true, out var right), "Naechster regulaerer Schritt");
Check(left.Y * right.Y < 0, "Linker und rechter Fuss wechseln sich ab");
Close(right.Angle, -90f, "Richtung stimmt fuer Ostbewegung");

var teleport = Loaded();
Check(!teleport.Sample(20, 20, .5f, false, true, out _), "Teleport erzeugt keine Spur");
Check(!teleport.Sample(20.6f, 20, .8f, true, true, out _), "Teleport-Nachlauf gesperrt");
Check(!teleport.Sample(20.9f, 20, 1.1f, false, true, out _), "Teleport loescht alte Bepollung");
Check(teleport.Sample(21.5f, 20, 1.5f, true, true, out _), "Nach Teleport ist erneute Pollenaufnahme moeglich");

var wall = Loaded();
Check(!wall.Sample(.9f, 0, .8f, false, false, out _), "Wandquerung erzeugt keine Spur");
Check(!wall.Sample(1.5f, 0, 1.4f, false, true, out _), "Wandquerung loescht Bepollung");

// Unsichtbarkeit, Vent und Rutsche entfernen den Walker im Produktionscode komplett.
// Ein neuer Walker am Ausstieg darf daher keinen vorherigen Pollen mitbringen.
var exit = new AmberhivePollenWalker(10, 10, 8);
Check(!exit.Sample(10.5f, 10, 8.4f, false, true, out _), "Neuer Walker hat keine alte Bepollung");
Check(!exit.Sample(float.NaN, 10, 8.8f, true, true, out _), "NaN-Position abgelehnt");
Check(!exit.Sample(11, 10, float.PositiveInfinity, true, true, out _), "Unendliche Zeit abgelehnt");
Check(!exit.Sample(11, 10, 1f, true, true, out _), "Rueckwaertige Zeit abgelehnt");
Check(exit.Sample(11, 10, 8.9f, true, true, out _), "Gueltiger Schritt nach ungueltigen Eingaben");

for (int i = 0; i < 17; i++)
{
    Close(AmberhiveLifeRules.LampLevel(1f, true, i, -1f), 1f, "Lampen vor Sabotage an");
    Close(AmberhiveLifeRules.LampLevel(1f, true, i, 4f), 0f, "Lampen nach der Welle aus");
    Close(AmberhiveLifeRules.LampLevel(0f, false, i, 4f), 1f, "Lampen nach Reparatur an");
}
Close(AmberhiveLifeRules.LampLevel(1f, true, 1, .1f), 1f, "Zweite Lampe wartet auf Verzoegerung");
Check(AmberhiveLifeRules.LampLevel(1f, true, 0, .2f) < 1f, "Erste Lampe erlischt zuerst");
float mid = AmberhiveLifeRules.LampLevel(1f, true, 0, .2f);
Close(AmberhiveLifeRules.LampLevel(mid, false, 0, 0f), mid, "Fruehe Reparatur bleibt stetig");
Check(AmberhiveLifeRules.LampLevel(mid, false, 0, .2f) > mid, "Fruehe Reparatur hellt wieder auf");
for (int i = 0; i < 17; i++)
    for (int j = 0; j < 40; j++)
    {
        float value = AmberhiveLifeRules.LampLevel(.37f, j % 2 == 0, i, j * .1f);
        Check(value >= 0 && value <= 1, "Lampenhelligkeit bleibt begrenzt");
    }

Close(AmberhiveLifeRules.Lifetime, 6f, "Abdruck lebt sechs Sekunden");
Console.WriteLine($"Life-Regeltests erfolgreich: {checks} Pruefungen, kein Spiel gestartet.");
