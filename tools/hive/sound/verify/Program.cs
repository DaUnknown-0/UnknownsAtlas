using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;
using BepInEx.Configuration;
using UnityEngine;
using UnknownsAtlas;

var root = Path.GetFullPath(args.Length > 0 ? args[0] : ".");
int checks = 0;
void Check(bool ok, string message)
{
    if (!ok) throw new Exception("FEHLER: " + message);
    checks++;
}
var measurements = new List<object>();
using (var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "tools/hive/sound/manifest.json"))))
foreach (var item in manifest.RootElement.GetProperty("clips").EnumerateObject())
{
    using var decoder = new NVorbis.VorbisReader(Path.Combine(root, "assets/amberhive/sound", item.Name));
    int expected = item.Value.GetProperty("frames").GetInt32();
    Check(decoder.TotalSamples == expected && decoder.Channels == 1 && decoder.SampleRate == 24000, item.Name + " Format/Granule");
    var samples = new float[expected + 4096];
    int read = 0, n;
    while ((n = decoder.ReadSamples(samples, read, samples.Length - read)) > 0) read += n;
    Check(read == expected, item.Name + " NVorbis-Samplezahl");
    samples = samples.Take(read).ToArray();
    Check(samples.All(float.IsFinite), item.Name + " endliche Samples");
    float peak = samples.Max(x => MathF.Abs(x));
    double rms = Math.Sqrt(samples.Average(x => (double)x * x));
    double dc = samples.Average(x => (double)x);
    float seam = MathF.Abs(samples[0] - samples[^1]);
    var differences = Enumerable.Range(1, read - 1).Select(i => MathF.Abs(samples[i] - samples[i - 1])).OrderBy(x => x).ToArray();
    float p99 = differences[(int)(differences.Length * .99)];
    Check(peak < .85 && rms > .01 && rms < .2 && Math.Abs(dc) < .005, item.Name + " Pegel/DC");
    Check(seam < .04 && seam < Math.Max(.004, p99 * 1.5), item.Name + $" Loopnaht {seam:F6}, P99 {p99:F6}");
    measurements.Add(new { file = item.Name, frames = read, rate = decoder.SampleRate, channels = decoder.Channels,
        peak, rms, dc, seam_step = seam, ordinary_step_p99 = p99 });
    Console.WriteLine($"NVorbis OK: {item.Name}, {read} Frames, RMS {rms:F4}, Naht {seam:F6}");
}

// Das auslieferbare Artefakt lesen, ohne Unity oder Among Us zu laden.
using (var file = File.OpenRead(Path.Combine(root, "bin/Release/net6.0/UnknownsAtlas.dll")))
using (var pe = new PEReader(file))
{
    var md = pe.GetMetadataReader();
    var resources = md.ManifestResources.Select(h => md.GetString(md.GetManifestResource(h).Name)).ToArray();
    Check(resources.Count(n => n.StartsWith(AtlasAmberhive.Ns + ".sound.") && n.EndsWith(".ogg")) == 10, "10 Clips in Release-DLL");
    Check(!md.AssemblyReferences.Any(h => md.GetString(md.GetAssemblyReference(h).Name) == "NVorbis"), "Keine externe Decoder-Abhaengigkeit");
    Check(md.TypeDefinitions.Any(h => md.GetString(md.GetTypeDefinition(h).Name) == "VorbisReader"), "NVorbis in DLL enthalten");
}

var config = new ConfigFile();
AtlasAmberhiveSound.Bind(config);
var enabled = (ConfigEntry<bool>)config.Entries["Enabled"];
var volume = (ConfigEntry<int>)config.Entries["Volume"];
void Hook(string name) => typeof(AtlasAmberhiveSound).GetNestedType("Lifecycle", BindingFlags.NonPublic)
    .GetMethod(name, BindingFlags.Static | BindingFlags.NonPublic).Invoke(null, null);
float Level(string name) => SoundManager.Instance.Active.Values.Where(s => s.clip.name.EndsWith("_" + name)).Sum(s => s.volume);

foreach (int floor in new[] { 1, 2 })
{
    using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, $"assets/amberhive/amberhive_{floor}f.json")));
    var data = json.RootElement;
    Vector2 V(JsonElement e) => new(e[0].GetSingle(), e[1].GetSingle());
    var map = new AtlasMapDef
    {
        EmergencyButton = V(data.GetProperty("emergencyButton")),
        Rooms = data.GetProperty("rooms").EnumerateArray().Select(r =>
            (r.GetProperty("key").GetString(), r.GetProperty("area").EnumerateArray().Select(V).ToArray())).ToArray(),
        Props = data.GetProperty("props").EnumerateArray().Select(p =>
            (p.GetProperty("kind").GetString(), p.GetProperty("worldX").GetSingle(), p.GetProperty("baseY").GetSingle(),
             p.GetProperty("footX0").GetSingle(), p.GetProperty("footX1").GetSingle())).ToArray()
    };
    AtlasMuseumBuilder.D = map;
    var hd = data.GetProperty("hive");
    var hive = new HiveData { PitCenter = V(hd.GetProperty("pit")), HasChute = floor == 2 };
    hive.FloodZones.AddRange(hd.GetProperty("floodZones").EnumerateArray().Select(p => p.EnumerateArray().Select(V).ToArray()));
    using var sound = new AtlasAmberhiveSound(map, hive, floor == 2);
    void Walk(Vector2 pos, bool bridge = false, int zone = -1, float flood = 0, bool slide = false)
    {
        PlayerControl.LocalPlayer.Position = pos;
        for (int frame = 0; frame < 100; frame++)
        {
            sound.Tick(.05f, bridge, zone, flood, slide);
            Check(SoundManager.Instance.Active.Values.Sum(s => s.volume) <= .24001f, "Gesamtlautstaerke beim Gehen");
        }
    }
    Walk(new Vector2(0, 0));
    Check(Level("honey_well") > .03f && Level("bridge_turn") == 0, "Brunnen, ruhende Bruecke");
    Walk(new Vector2(0, 0), bridge: true);
    Check(Level("bridge_turn") > 0, "Drehbruecke hoerbar");
    Walk(new Vector2(100, 100));
    Check(SoundManager.Instance.Active.Count == 0, "Entfernung blendet alles aus");
    Walk(new Vector2(0, -12));
    Check(Level("brood_buzz") > .03f && Level("honey_well") == 0, "Summen am Thron");
    Walk(new Vector2(11.5f, -6));
    Check(Level("brood_buzz") > .03f, "Summen an Brutwaben");
    Walk(new Vector2(-9, -7));
    Check(Level("bellows") > .03f, "Blasebaelge");
    Walk(new Vector2(17.4f, 0));
    Check(Level("wax_foundry") > .03f, "Wachs");
    Walk(map.EmergencyButton);
    Check(Level("mead_chimes") > 0, "Glocke");
    for (int j = 0; j < 12; j++) Walk(new Vector2(j % 2 == 0 ? -17.2f : 17.2f, -11.7f));
    Check(Level("nectar_press") > 0 && SoundManager.Instance.DuplicatePlays == 0, "Beide Pressen ohne doppelte Clip-Stimme");
    foreach (var zone in hive.FloodZones)
    {
        var mid = zone.Aggregate(Vector2.zero, (a, b) => a + b) / zone.Length;
        Check(AtlasAmberhiveSound.DistanceToArea(mid, zone) == 0, "Flut enthaelt Mittelpunkt");
        Check(AtlasAmberhiveSound.DistanceToArea(zone[0] - new Vector2(2, 0), zone) > 0, "Abstand zur Flutflaeche");
        Walk(mid, zone: hive.FloodZones.IndexOf(zone), flood: 1);
        Check(Level("honey_flood") > .03f, "Flut hoerbar in aktiver Zone");
        Walk(mid, zone: hive.FloodZones.IndexOf(zone), flood: 0);
        Check(Level("honey_flood") == 0, "Keine Warn- oder Restschleife");
    }
    Walk(new Vector2(3, 26), slide: true);
    Check((Level("nectar_chute") > 0) == (floor == 2), "Rutsche nur bei zwei Etagen");
    Walk(new Vector2(3, -3), slide: false);
    Check(Level("nectar_chute") == 0, "Rutsche nach Fahrt still");
    volume.Value = 100;
    Walk(new Vector2(0, 0), bridge: true, zone: 0, flood: 1);
    Check(SoundManager.Instance.Active.Count > 0, "Lautstaerke 100 mit mehreren Quellen");
    volume.Value = 0;
    Hook("Watchdog");
    Check(SoundManager.Instance.Active.Count == 0, "Lautstaerke 0 sofort still");
    volume.Value = 60;
    Walk(new Vector2(0, 0));
    enabled.Value = false;
    Hook("Watchdog");
    Check(SoundManager.Instance.Active.Count == 0, "Client-Schalter sofort still");
    enabled.Value = true;
    Walk(new Vector2(0, 0));
    Hook("Meeting");
    Check(SoundManager.Instance.Active.Count == 0, "Meeting-Prefix sofort still");
    MeetingHud.Instance = new();
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Meeting bleibt still");
    MeetingHud.Instance = null;
    Walk(new Vector2(0, 0));
    Check(Level("honey_well") > 0, "Nach Meeting wieder Klang");
    ExileController.Instance = new();
    Hook("Watchdog");
    Check(SoundManager.Instance.Active.Count == 0, "Rauswurf still");
    ExileController.Instance = null;
    AtlasMuseumBuilder.Active = false;
    Hook("Watchdog");
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Ungebaute Karte still");
    AtlasMuseumBuilder.Active = true;
    map.Key = "museum";
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Kartenwechsel still");
    map.Key = "amberhive";
    AmongUsClient.Instance.GameState = InnerNet.InnerNetClient.GameStates.Ended;
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Ended-Zustand auch ohne End-Hook still");
    AmongUsClient.Instance.GameState = InnerNet.InnerNetClient.GameStates.Joined;
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Lobby still");
    AmongUsClient.Instance.NetworkMode = NetworkModes.FreePlay;
    Walk(new Vector2(0, 0));
    Check(Level("honey_well") > 0, "Freeplay unterstuetzt");
    Hook("End");
    Check(SoundManager.Instance.Active.Count == 0, "Spielende-Prefix sofort still");
    Walk(new Vector2(0, 0));
    Check(SoundManager.Instance.Active.Count == 0, "Kein Neustart nach Spielende im Freeplay");
    AmongUsClient.Instance.GameState = InnerNet.InnerNetClient.GameStates.Started;
    AmongUsClient.Instance.NetworkMode = NetworkModes.LocalGame;
    sound.Dispose();
    Check(AudioClip.Created.All(c => c.Destroyed), "Alle dekodierten Clips freigegeben");
    Console.WriteLine($"Offline OK: {floor} Etage(n), Raumwechsel, Mechaniken, Client-Regler, Meeting, Spielende, Freigabe");
}
Check(AtlasAmberhiveSound.Falloff(2, 1, 7) > AtlasAmberhiveSound.Falloff(5, 1, 7), "Entfernung monoton");
Check(AtlasAmberhiveSound.Falloff(1, 1, 7) == 1 && AtlasAmberhiveSound.Falloff(7, 1, 7) == 0, "Endpunkte der Reichweite");
File.WriteAllText(Path.Combine(root, "tools/hive/sound/verification.json"), JsonSerializer.Serialize(new
{ decoder = "NVorbis 0.10.5", checks, duplicate_plays = SoundManager.Instance.DuplicatePlays, clips = measurements }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"Erfolgreich: {checks} Pruefungen, keine doppelten Clip-Stimmen. Kein Spiel gestartet.");
