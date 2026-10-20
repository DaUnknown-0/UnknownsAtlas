// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMapFile - Karten als Datei (2026-10-17).
//
// Eine Karte ist eine map.json (alle Felder von AtlasMapDef) plus ihr Kartenpaket (Boden, Objekte, Konsolen, Minimap,
// Logo, Symbol, Minispiel-Grafik) in einem Ordner. Atlas findet solche Karten
//   - als Ordner unter BepInEx/plugins/AtlasMaps/<name>/ (map.json + Dateien daneben) und
//   - eingebettet in Atlas selbst: Ressourcen "UnknownsAtlas.Maps.<key>.map.json" (+ "UnknownsAtlas.Maps.<key>.<datei>").
// Beide werden wie Karten anderer Plugins angemeldet (AtlasMaps.Register): sie erscheinen im Kartenwaehler, und der
// Handshake vergleicht ihren Inhalt (SHA-256 ueber map.json und alle Dateien), damit alle Spieler dieselbe Fassung haben.
//
// Die Dateien eines Ordners stellt eine AtlasFolderAssembly als "eingebettete Ressourcen" bereit; der gesamte Ladecode
// (AtlasAssets, AtlasTexturePack, Minispiel-Grafik) bleibt dadurch unveraendert.
//
// Code laesst sich nicht in eine Datei schreiben: Welt-Mechaniken waehlt eine Karte per Name ("world": "train"),
// eingebaute Atlas-Minispiele wie bisher ueber "customTasks" (Baustein-Art). Format: siehe docs/MAP_FORMAT.md.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using UnityEngine;

namespace UnknownsAtlas;

public static class AtlasMapFile
{
    private const string LogPrefix = "[Atlas/MapFile]";
    public const int FormatVersion = 1;
    internal const string EmbeddedPrefix = "UnknownsAtlas.Maps.";

    /// <summary>Welt-Mechaniken, die eine Kartendatei per Name waehlen kann ("world": name).</summary>
    public static readonly Dictionary<string, Func<IAtlasMapWorld>> Worlds = new(StringComparer.OrdinalIgnoreCase);

    // ------------------------------------------------------------------ Lesen

    /// <summary>Kartendaten aus JSON. res/ns: wo das Kartenpaket liegt (wie AtlasMapDef.ResourceAssembly/Namespace).</summary>
    public static AtlasMapDef Read(string json, Assembly res, string ns)
    {
        using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true });
        var r = doc.RootElement;
        int fmt = Int(r, "format", 1);
        if (fmt > FormatVersion) throw new InvalidDataException($"map format {fmt} is newer than this Atlas ({FormatVersion})");
        var d = new AtlasMapDef
        {
            Key = Str(r, "key"),
            DisplayName = Str(r, "displayName"),
            ResourcePrefix = Str(r, "resourcePrefix") ?? Str(r, "key"),
            ResourceAssembly = res,
            ResourceNamespace = ns,
            MinimapFile = Str(r, "minimapFile"),
            BuiltInEffects = Bool(r, "builtInEffects", false),
            MinX = Flt(r, "minX"), MinY = Flt(r, "minY"), MaxX = Flt(r, "maxX"), MaxY = Flt(r, "maxY"),
            Walls = Polys(r, "walls"), ShadowWalls = Polys(r, "shadowWalls"), Opaque = Polys(r, "opaque"),
            Glass = Polys(r, "glass"), Hallways = Polys(r, "hallways"),
            FloorPixelsPerMeter = Flt(r, "floorPixelsPerMeter"),
            PropPixelsPerMeter = Flt(r, "propPixelsPerMeter"),
            SpawnRadius = Flt(r, "spawnRadius"),
            EmergencyButton = V(r, "emergencyButton"), SurveillanceConsole = V(r, "surveillanceConsole"),
            AdminTable = V(r, "adminTable"), FreeplayLaptop = V(r, "freeplayLaptop"), Spawn = V(r, "spawn"),
            CameraColor = Col(r, "cameraColor"),
            MinLight = Flt(r, "minLight", 1f), MaxLight = Flt(r, "maxLight", 5f),
        };
        if (string.IsNullOrEmpty(d.Key)) throw new InvalidDataException("map without \"key\"");
        d.DisplayName ??= d.Key;

        d.OpaqueCastsShadow = Arr(r, "opaqueCastsShadow").Select(e => e.GetBoolean()).ToArray();
        if (d.OpaqueCastsShadow.Length != (d.Opaque?.Length ?? 0))
            d.OpaqueCastsShadow = Enumerable.Repeat(true, d.Opaque?.Length ?? 0).ToArray();

        d.Rooms = Arr(r, "rooms").Select(e => (Str(e, "key"), Str(e, "name"), Enum<SystemTypes>(e, "room"), Poly(Prop(e, "area")))).ToArray();
        d.FloorTiles = Arr(r, "floorTiles").Select(e => (Int(e, "index"), Flt(e, "x"), Flt(e, "y"), Int(e, "w"), Int(e, "h"))).ToArray();
        d.Props = Arr(r, "props").Select(e => (Str(e, "kind"), Int(e, "atlas"), Int(e, "x"), Int(e, "y"), Int(e, "w"), Int(e, "h"),
            Flt(e, "worldX"), Flt(e, "worldY"), Flt(e, "baseY"), Flt(e, "footX0"), Flt(e, "footX1"))).ToArray();
        d.ConsoleSprites = Arr(r, "consoleSprites").Select(e => (Str(e, "key"), Int(e, "atlas"), Int(e, "x"), Int(e, "y"), Int(e, "w"), Int(e, "h"),
            Flt(e, "pivotX"), Flt(e, "pivotY"))).ToArray();
        d.NoFadeKinds = new HashSet<string>(Arr(r, "noFadeKinds").Select(e => e.GetString()));
        d.Consoles = Obj(r, "consoles").ToDictionary(p => p.Name, p => Vec(p.Value));
        d.ForeignTasks = Arr(r, "foreignTasks").Select(e => (Enum<TaskTypes>(e, "type"), Int(e, "ship"), Str(e, "console"), Enum<SystemTypes>(e, "room"))).ToArray();
        d.Vents = Obj(r, "vents").ToDictionary(p => int.Parse(p.Name, CultureInfo.InvariantCulture), p => Vec(p.Value));
        d.VentNetworks = Ints2(r, "ventNetworks");
        d.VentBridges = Ints2(r, "ventBridges");
        d.VerticalDoors = Doors(r, "verticalDoors");
        d.HorizontalDoors = Doors(r, "horizontalDoors");
        d.Cameras = Arr(r, "cameras").Select(Vec).ToArray();
        d.CameraViews = Obj(r, "cameraViews").ToDictionary(p => int.Parse(p.Name, CultureInfo.InvariantCulture), p => Vec(p.Value));
        d.MapButtons = Obj(r, "mapButtons").ToDictionary(p => ParseEnum<SystemTypes>(p.Name), p => Vec(p.Value));
        d.MapLabels = Arr(r, "mapLabels").Select(e => (Flt(e, "x"), Flt(e, "y"), Flt(e, "halfW"), Flt(e, "halfH"))).ToArray();
        var trees = Arr(r, "treeSpots").Select(e => (Flt(e, "x"), Flt(e, "y"), Bool(e, "horizontal", true), Flt(e, "len"))).ToArray();
        d.TreeSpots = trees.Length > 0 ? trees : null;
        d.ViewSpots = Arr(r, "viewSpots").Select(Vec).ToArray();
        d.TaskNames = Obj(r, "taskNames").ToDictionary(p => ParseEnum<TaskTypes>(p.Name), p => p.Value.GetString());
        d.CustomTasks = Obj(r, "customTasks").ToDictionary(p => ParseEnum<TaskTypes>(p.Name), p => p.Value.GetString());
        d.TaskArt = Obj(r, "taskArt").ToDictionary(p => p.Name, p => p.Value.GetString());
        d.TaskText = Obj(r, "taskText").ToDictionary(p => p.Name, p => p.Value.GetString());
        if (Prop(r, "dummyRadius") is { ValueKind: JsonValueKind.Array } dr) d.DummyRadius = Vec(dr);
        // Treppen zwischen Ebenen (AtlasStairs); "levels" (3D-Lage der Ebenen) lesen nur Werkzeuge
        d.Stairs = Arr(r, "stairs").Select(e => (V(e, "a"), V(e, "b"), Str(e, "labelA") ?? "STAIRS", Str(e, "labelB") ?? "STAIRS")).ToArray();
        // Sabotage "Conductor's Round" (AtlasTicket): Lochzangen, Kartenknopf, Sekunden
        if (Prop(r, "ticket") is { ValueKind: JsonValueKind.Object } tk)
        {
            d.TicketSeconds = Flt(tk, "seconds", 60f);
            d.TicketButton = V(tk, "button");
            d.TicketStations = Arr(tk, "stations").Select(Vec).ToArray();
        }
        if (Prop(r, "runaway") is { ValueKind: JsonValueKind.Object } ra)
        {
            d.RunawaySeconds = Flt(ra, "seconds", 45f);
            d.RunawayButton = V(ra, "button"); d.RunawayBrake = V(ra, "brake"); d.RunawayHandbrake = V(ra, "handbrake");
        }
        if (Prop(r, "smoke") is { ValueKind: JsonValueKind.Object } sm)
        {
            d.SmokeSeconds = Flt(sm, "seconds", 60f);
            d.SmokeButton = V(sm, "button"); d.SmokeSource = V(sm, "source");
            d.SmokeHatches = Arr(sm, "hatches").Select(Vec).ToArray();
        }
        d.Scroll = Arr(r, "scroll").Select(e => (Str(e, "file"), Flt(e, "ppm", 128f), Flt(e, "y0"), Flt(e, "y1"), Flt(e, "width_m"), Flt(e, "parallax", 1f)))
                      .Where(e => !string.IsNullOrEmpty(e.Item1)).ToArray();

        string world = Str(r, "world");
        if (!string.IsNullOrEmpty(world))
        {
            if (Worlds.TryGetValue(world, out var make)) d.World = make();
            else AtlasPlugin.Logger.LogWarning($"{LogPrefix} {d.Key}: unknown world mechanics '{world}' - the map runs without them");
        }
        return d;
    }

    // ------------------------------------------------------------------ Schreiben (Export, Rundlauf-Test)

    public static string Write(AtlasMapDef d, string world = null)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms, new JsonWriterOptions { Indented = true }))
        {
            w.WriteStartObject();
            w.WriteNumber("format", FormatVersion);
            w.WriteString("key", d.Key);
            w.WriteString("displayName", d.DisplayName);
            w.WriteString("resourcePrefix", d.ResourcePrefix);
            if (d.MinimapFile != null) w.WriteString("minimapFile", d.MinimapFile);
            w.WriteBoolean("builtInEffects", d.BuiltInEffects);
            if (world != null) w.WriteString("world", world);
            Num(w, "minX", d.MinX); Num(w, "minY", d.MinY); Num(w, "maxX", d.MaxX); Num(w, "maxY", d.MaxY);
            PolysOut(w, "walls", d.Walls); PolysOut(w, "shadowWalls", d.ShadowWalls); PolysOut(w, "opaque", d.Opaque);
            PolysOut(w, "glass", d.Glass); PolysOut(w, "hallways", d.Hallways);
            w.WriteStartArray("opaqueCastsShadow"); foreach (var b in d.OpaqueCastsShadow ?? Array.Empty<bool>()) w.WriteBooleanValue(b); w.WriteEndArray();
            w.WriteStartArray("rooms");
            foreach (var x in d.Rooms ?? Array.Empty<(string, string, SystemTypes, Vector2[])>())
            {
                w.WriteStartObject(); w.WriteString("key", x.Key); w.WriteString("name", x.Name); w.WriteString("room", x.Room.ToString());
                w.WritePropertyName("area"); PolyOut(w, x.Area); w.WriteEndObject();
            }
            w.WriteEndArray();
            Num(w, "floorPixelsPerMeter", d.FloorPixelsPerMeter);
            w.WriteStartArray("floorTiles");
            foreach (var x in d.FloorTiles ?? Array.Empty<(int, float, float, int, int)>())
            { w.WriteStartObject(); w.WriteNumber("index", x.Index); Num(w, "x", x.WorldX); Num(w, "y", x.WorldY); w.WriteNumber("w", x.W); w.WriteNumber("h", x.H); w.WriteEndObject(); }
            w.WriteEndArray();
            Num(w, "propPixelsPerMeter", d.PropPixelsPerMeter);
            w.WriteStartArray("props");
            foreach (var x in d.Props ?? Array.Empty<(string, int, int, int, int, int, float, float, float, float, float)>())
            {
                w.WriteStartObject(); w.WriteString("kind", x.Kind); w.WriteNumber("atlas", x.Atlas); w.WriteNumber("x", x.X); w.WriteNumber("y", x.Y);
                w.WriteNumber("w", x.W); w.WriteNumber("h", x.H); Num(w, "worldX", x.WorldX); Num(w, "worldY", x.WorldY); Num(w, "baseY", x.BaseY);
                Num(w, "footX0", x.FootX0); Num(w, "footX1", x.FootX1); w.WriteEndObject();
            }
            w.WriteEndArray();
            w.WriteStartArray("consoleSprites");
            foreach (var x in d.ConsoleSprites ?? Array.Empty<(string, int, int, int, int, int, float, float)>())
            {
                w.WriteStartObject(); w.WriteString("key", x.Key); w.WriteNumber("atlas", x.Atlas); w.WriteNumber("x", x.X); w.WriteNumber("y", x.Y);
                w.WriteNumber("w", x.W); w.WriteNumber("h", x.H); Num(w, "pivotX", x.PivotX); Num(w, "pivotY", x.PivotY); w.WriteEndObject();
            }
            w.WriteEndArray();
            w.WriteStartArray("noFadeKinds"); foreach (var k in d.NoFadeKinds ?? new HashSet<string>()) w.WriteStringValue(k); w.WriteEndArray();
            w.WriteStartObject("consoles"); foreach (var kv in d.Consoles ?? new()) { w.WritePropertyName(kv.Key); VecOut(w, kv.Value); } w.WriteEndObject();
            w.WriteStartArray("foreignTasks");
            foreach (var x in d.ForeignTasks ?? Array.Empty<(TaskTypes, int, string, SystemTypes)>())
            { w.WriteStartObject(); w.WriteString("type", x.Type.ToString()); w.WriteNumber("ship", x.ShipId); w.WriteString("console", x.ConsoleKey); w.WriteString("room", x.Room.ToString()); w.WriteEndObject(); }
            w.WriteEndArray();
            w.WritePropertyName("emergencyButton"); VecOut(w, d.EmergencyButton);
            w.WritePropertyName("surveillanceConsole"); VecOut(w, d.SurveillanceConsole);
            w.WritePropertyName("adminTable"); VecOut(w, d.AdminTable);
            w.WritePropertyName("freeplayLaptop"); VecOut(w, d.FreeplayLaptop);
            w.WritePropertyName("spawn"); VecOut(w, d.Spawn);
            Num(w, "spawnRadius", d.SpawnRadius);
            w.WritePropertyName("dummyRadius"); VecOut(w, d.DummyRadius);
            w.WriteStartArray("stairs");
            foreach (var s in d.Stairs ?? Array.Empty<(Vector2, Vector2, string, string)>())
            {
                w.WriteStartObject(); w.WritePropertyName("a"); VecOut(w, s.A); w.WritePropertyName("b"); VecOut(w, s.B);
                w.WriteString("labelA", s.LabelA); w.WriteString("labelB", s.LabelB); w.WriteEndObject();
            }
            w.WriteEndArray();
            if (d.TicketStations != null && d.TicketStations.Length > 0)
            {
                w.WriteStartObject("ticket");
                Num(w, "seconds", d.TicketSeconds);
                w.WritePropertyName("button"); VecOut(w, d.TicketButton);
                w.WriteStartArray("stations"); foreach (var s in d.TicketStations) VecOut(w, s); w.WriteEndArray();
                w.WriteEndObject();
            }
            if (d.RunawaySeconds > 0f)
            {
                w.WriteStartObject("runaway");
                Num(w, "seconds", d.RunawaySeconds);
                w.WritePropertyName("button"); VecOut(w, d.RunawayButton);
                w.WritePropertyName("brake"); VecOut(w, d.RunawayBrake);
                w.WritePropertyName("handbrake"); VecOut(w, d.RunawayHandbrake);
                w.WriteEndObject();
            }
            if (d.SmokeHatches != null && d.SmokeHatches.Length > 0)
            {
                w.WriteStartObject("smoke");
                Num(w, "seconds", d.SmokeSeconds);
                w.WritePropertyName("button"); VecOut(w, d.SmokeButton);
                w.WritePropertyName("source"); VecOut(w, d.SmokeSource);
                w.WriteStartArray("hatches"); foreach (var s in d.SmokeHatches) VecOut(w, s); w.WriteEndArray();
                w.WriteEndObject();
            }
            w.WriteStartArray("scroll");
            foreach (var s in d.Scroll ?? Array.Empty<(string, float, float, float, float, float)>())
            {
                w.WriteStartObject(); w.WriteString("file", s.File); Num(w, "ppm", s.Ppm); Num(w, "y0", s.Y0); Num(w, "y1", s.Y1);
                Num(w, "width_m", s.WidthM); Num(w, "parallax", s.Parallax); w.WriteEndObject();
            }
            w.WriteEndArray();
            w.WriteStartObject("vents"); foreach (var kv in d.Vents ?? new()) { w.WritePropertyName(kv.Key.ToString(CultureInfo.InvariantCulture)); VecOut(w, kv.Value); } w.WriteEndObject();
            IntsOut(w, "ventNetworks", d.VentNetworks); IntsOut(w, "ventBridges", d.VentBridges);
            DoorsOut(w, "verticalDoors", d.VerticalDoors); DoorsOut(w, "horizontalDoors", d.HorizontalDoors);
            w.WriteStartArray("cameras"); foreach (var c in d.Cameras ?? Array.Empty<Vector2>()) VecOut(w, c); w.WriteEndArray();
            w.WriteStartObject("cameraViews"); foreach (var kv in d.CameraViews ?? new()) { w.WritePropertyName(kv.Key.ToString(CultureInfo.InvariantCulture)); VecOut(w, kv.Value); } w.WriteEndObject();
            w.WriteStartObject("mapButtons"); foreach (var kv in d.MapButtons ?? new()) { w.WritePropertyName(kv.Key.ToString()); VecOut(w, kv.Value); } w.WriteEndObject();
            w.WriteStartArray("mapLabels");
            foreach (var x in d.MapLabels ?? Array.Empty<(float, float, float, float)>())
            { w.WriteStartObject(); Num(w, "x", x.X); Num(w, "y", x.Y); Num(w, "halfW", x.HalfW); Num(w, "halfH", x.HalfH); w.WriteEndObject(); }
            w.WriteEndArray();
            w.WritePropertyName("cameraColor"); w.WriteStartArray(); Num(w, null, d.CameraColor.r); Num(w, null, d.CameraColor.g); Num(w, null, d.CameraColor.b); w.WriteEndArray();
            Num(w, "minLight", d.MinLight); Num(w, "maxLight", d.MaxLight);
            w.WriteStartArray("treeSpots");
            foreach (var x in d.TreeSpots ?? Array.Empty<(float, float, bool, float)>())
            { w.WriteStartObject(); Num(w, "x", x.X); Num(w, "y", x.Y); w.WriteBoolean("horizontal", x.Horizontal); Num(w, "len", x.Len); w.WriteEndObject(); }
            w.WriteEndArray();
            w.WriteStartArray("viewSpots"); foreach (var c in d.ViewSpots ?? Array.Empty<Vector2>()) VecOut(w, c); w.WriteEndArray();
            w.WriteStartObject("taskNames"); foreach (var kv in d.TaskNames ?? new()) w.WriteString(kv.Key.ToString(), kv.Value); w.WriteEndObject();
            w.WriteStartObject("customTasks"); foreach (var kv in d.CustomTasks ?? new()) w.WriteString(kv.Key.ToString(), kv.Value); w.WriteEndObject();
            w.WriteStartObject("taskArt"); foreach (var kv in d.TaskArt ?? new()) w.WriteString(kv.Key, kv.Value); w.WriteEndObject();
            w.WriteStartObject("taskText"); foreach (var kv in d.TaskText ?? new()) w.WriteString(kv.Key, kv.Value); w.WriteEndObject();
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    // ------------------------------------------------------------------ Suchen und anmelden

    /// <summary>Beim Laden des Plugins: eingebettete Kartendateien und Ordner unter plugins/AtlasMaps anmelden.</summary>
    internal static void RegisterAll()
    {
        // eingebettet in Atlas
        var asm = typeof(AtlasMapFile).Assembly;
        foreach (var name in asm.GetManifestResourceNames())
        {
            if (!name.StartsWith(EmbeddedPrefix, StringComparison.Ordinal) || !name.EndsWith(".map.json", StringComparison.Ordinal)) continue;
            string key = name.Substring(EmbeddedPrefix.Length, name.Length - EmbeddedPrefix.Length - ".map.json".Length);
            string ns = EmbeddedPrefix + key;
            TryRegister(() => ReadText(asm.GetManifestResourceStream(name)), asm, ns, HashEmbedded(asm, ns), "embedded");
        }
        // Ordner neben den Plugins
        string root = Path.Combine(BepInEx.Paths.PluginPath, "AtlasMaps");
        if (!Directory.Exists(root)) return;
        foreach (var dir in Directory.GetDirectories(root))
        {
            string file = Path.Combine(dir, "map.json");
            if (!File.Exists(file)) continue;
            var fa = new AtlasFolderAssembly(dir, "AtlasMaps." + Path.GetFileName(dir));
            TryRegister(() => File.ReadAllText(file), fa, fa.Namespace, HashFolder(dir), dir);
        }
    }

    private static void TryRegister(Func<string> json, Assembly res, string ns, string hash, string origin)
    {
        try
        {
            string text = json();
            var probe = Read(text, res, ns);                         // einmal pruefen, ob die Datei taugt
            string label = probe.DisplayName;
            bool ok = AtlasMaps.Register(probe.Key, label, () => Read(text, res, ns), res, ns,
                Exists(res, ns, $"button_{probe.Key}.png") ? $"button_{probe.Key}.png" : null,
                Exists(res, ns, $"icon_{probe.Key}.png") ? $"icon_{probe.Key}.png" : null,
                "file:" + hash);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {(ok ? "registered" : "skipped")} '{probe.Key}' ({label}) from {origin}, " +
                                       $"{probe.Rooms?.Length ?? 0} rooms, {probe.Props?.Length ?? 0} props, content {hash.Substring(0, 12)}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} map file from {origin} failed: {e.Message}"); }
    }

    private static bool Exists(Assembly a, string ns, string file)
    {
        try { return a.GetManifestResourceInfo($"{ns}.{file}") != null; } catch { return false; }
    }

    private static string ReadText(Stream s)
    {
        using (s) using (var r = new StreamReader(s, Encoding.UTF8)) return r.ReadToEnd();
    }

    private static string HashFolder(string dir)
    {
        using var sha = SHA256.Create();
        foreach (var f in Directory.GetFiles(dir).OrderBy(x => Path.GetFileName(x), StringComparer.Ordinal))
        {
            var name = Encoding.UTF8.GetBytes(Path.GetFileName(f));
            sha.TransformBlock(name, 0, name.Length, null, 0);
            var data = File.ReadAllBytes(f);
            sha.TransformBlock(data, 0, data.Length, null, 0);
        }
        sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
        return Convert.ToHexString(sha.Hash);
    }

    private static string HashEmbedded(Assembly asm, string ns)
    {
        using var sha = SHA256.Create();
        foreach (var n in asm.GetManifestResourceNames().Where(n => n.StartsWith(ns + ".", StringComparison.Ordinal)).OrderBy(n => n, StringComparer.Ordinal))
        {
            var name = Encoding.UTF8.GetBytes(n);
            sha.TransformBlock(name, 0, name.Length, null, 0);
            using var s = asm.GetManifestResourceStream(n);
            using var ms = new MemoryStream();
            s.CopyTo(ms);
            var data = ms.ToArray();
            sha.TransformBlock(data, 0, data.Length, null, 0);
        }
        // ausgelagerte Dateien des Pakets (AtlasAssetStore): Name und Pruefsumme aus dem Katalog
        foreach (var (res, hash) in AtlasAssetStore.UnderNamespace(ns))
        {
            var line = Encoding.UTF8.GetBytes(res + ":" + hash);
            sha.TransformBlock(line, 0, line.Length, null, 0);
        }
        sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
        return Convert.ToHexString(sha.Hash);
    }

    // ------------------------------------------------------------------ Diagnose (Diagnostics.MapFileTest)

    /// <summary>Exportiert Museum, Wald und Park, prueft den Rundlauf (schreiben, lesen, schreiben = gleich) und
    /// meldet das Museum aus seiner Datei als "museum_file" an (gleiche Grafik aus Atlas), fuer den Vergleich im Freeplay.</summary>
    internal static void DiagTest()
    {
        string dir = Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots", "maps");
        Directory.CreateDirectory(dir);
        var asm = typeof(AtlasMapFile).Assembly;
        foreach (var make in new Func<AtlasMapDef>[] { AtlasMapDef.Museum, AtlasMapDef.Wald, AtlasMapDef.Park })
        {
            var def = make();
            string a = Write(def);
            var back = Read(a, asm, "UnknownsAtlas.Resources");
            back.BuiltInEffects = def.BuiltInEffects;
            string b = Write(back);
            File.WriteAllText(Path.Combine(dir, def.Key + ".map.json"), a);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: {def.Key} exported ({a.Length / 1024} KB), round trip {(a == b ? "identical" : "DIFFERENT")}");
            if (a != b) File.WriteAllText(Path.Combine(dir, def.Key + ".roundtrip.json"), b);
        }
        // das Museum noch einmal, nur aus der Datei (Schluessel museum_file, Grafik weiter aus Atlas)
        string museum = File.ReadAllText(Path.Combine(dir, "museum.map.json"))
            .Replace("\"key\": \"museum\"", "\"key\": \"museum_file\"").Replace("\"displayName\": \"Vesper Museum\"", "\"displayName\": \"Museum (file)\"");
        AtlasMaps.Register("museum_file", "Museum (file)", () => Read(museum, asm, "UnknownsAtlas.Resources"), asm, "UnknownsAtlas.Resources",
            "button_museum.png", "icon_museum.png", "diag");
    }

    // ------------------------------------------------------------------ JSON-Helfer

    private static JsonElement? Prop(JsonElement e, string name) => e.ValueKind == JsonValueKind.Object && e.TryGetProperty(name, out var v) ? v : null;
    private static string Str(JsonElement e, string n) => Prop(e, n) is { ValueKind: JsonValueKind.String } v ? v.GetString() : null;
    private static float Flt(JsonElement e, string n, float def = 0f) => Prop(e, n) is { ValueKind: JsonValueKind.Number } v ? v.GetSingle() : def;
    private static int Int(JsonElement e, string n, int def = 0) => Prop(e, n) is { ValueKind: JsonValueKind.Number } v ? v.GetInt32() : def;
    private static bool Bool(JsonElement e, string n, bool def) => Prop(e, n) is { } v && (v.ValueKind == JsonValueKind.True || v.ValueKind == JsonValueKind.False) ? v.GetBoolean() : def;
    private static IEnumerable<JsonElement> Arr(JsonElement e, string n) => Prop(e, n) is { ValueKind: JsonValueKind.Array } v ? v.EnumerateArray().ToArray() : Array.Empty<JsonElement>();
    private static IEnumerable<JsonProperty> Obj(JsonElement e, string n) => Prop(e, n) is { ValueKind: JsonValueKind.Object } v ? v.EnumerateObject().ToArray() : Array.Empty<JsonProperty>();
    private static Vector2 Vec(JsonElement e) { var a = e.EnumerateArray().ToArray(); return new Vector2(a[0].GetSingle(), a[1].GetSingle()); }
    private static Vector2 V(JsonElement e, string n) => Prop(e, n) is { ValueKind: JsonValueKind.Array } v ? Vec(v) : Vector2.zero;
    private static Vector2[] Poly(JsonElement? e) => e is { ValueKind: JsonValueKind.Array } v ? v.EnumerateArray().Select(Vec).ToArray() : Array.Empty<Vector2>();
    private static Vector2[][] Polys(JsonElement e, string n) => Arr(e, n).Select(p => Poly(p)).ToArray();
    private static int[][] Ints2(JsonElement e, string n) => Arr(e, n).Select(a => a.EnumerateArray().Select(x => x.GetInt32()).ToArray()).ToArray();
    private static T ParseEnum<T>(string s) where T : struct => (T)System.Enum.Parse(typeof(T), s, true);
    private static T Enum<T>(JsonElement e, string n) where T : struct => ParseEnum<T>(Str(e, n));
    private static Color Col(JsonElement e, string n)
    {
        if (Prop(e, n) is not { ValueKind: JsonValueKind.Array } v) return Color.black;
        var a = v.EnumerateArray().Select(x => x.GetSingle()).ToArray();
        return new Color(a[0], a[1], a[2], a.Length > 3 ? a[3] : 1f);
    }
    private static AtlasMuseumLayout.DoorSlot[] Doors(JsonElement e, string n) =>
        Arr(e, n).Select(d => new AtlasMuseumLayout.DoorSlot(Str(d, "label"), Flt(d, "x"), Flt(d, "y"), Flt(d, "length"),
            Enum<SystemTypes>(d, "group"), Bool(d, "seeThrough", true))).ToArray();

    private static void Num(Utf8JsonWriter w, string n, float f)
    {
        // kurz und verlustfrei genug: Karten rechnen in Zentimetern
        double v = Math.Round(f, 4);
        if (n == null) w.WriteNumberValue(v); else w.WriteNumber(n, v);
    }
    private static void VecOut(Utf8JsonWriter w, Vector2 v) { w.WriteStartArray(); Num(w, null, v.x); Num(w, null, v.y); w.WriteEndArray(); }
    private static void PolyOut(Utf8JsonWriter w, Vector2[] p) { w.WriteStartArray(); foreach (var v in p ?? Array.Empty<Vector2>()) VecOut(w, v); w.WriteEndArray(); }
    private static void PolysOut(Utf8JsonWriter w, string n, Vector2[][] ps) { w.WriteStartArray(n); foreach (var p in ps ?? Array.Empty<Vector2[]>()) PolyOut(w, p); w.WriteEndArray(); }
    private static void IntsOut(Utf8JsonWriter w, string n, int[][] a)
    {
        w.WriteStartArray(n);
        foreach (var r in a ?? Array.Empty<int[]>()) { w.WriteStartArray(); foreach (var i in r) w.WriteNumberValue(i); w.WriteEndArray(); }
        w.WriteEndArray();
    }
    private static void DoorsOut(Utf8JsonWriter w, string n, AtlasMuseumLayout.DoorSlot[] ds)
    {
        w.WriteStartArray(n);
        foreach (var d in ds ?? Array.Empty<AtlasMuseumLayout.DoorSlot>())
        {
            w.WriteStartObject(); w.WriteString("label", d.Label); Num(w, "x", d.Center.x); Num(w, "y", d.Center.y); Num(w, "length", d.Length);
            w.WriteString("group", d.Group.ToString()); w.WriteBoolean("seeThrough", d.SeeThrough); w.WriteEndObject();
        }
        w.WriteEndArray();
    }
}

/// <summary>Dateien eines Ordners als "eingebettete Ressourcen" ("&lt;Namespace&gt;.&lt;Datei&gt;"), damit der Ladecode
/// von Atlas Kartendateien genauso liest wie eingebettete Karten.</summary>
public sealed class AtlasFolderAssembly : Assembly
{
    private readonly string _dir;
    public readonly string Namespace;

    public AtlasFolderAssembly(string dir, string ns) { _dir = dir; Namespace = ns; }

    private string PathOf(string name)
    {
        if (name == null || !name.StartsWith(Namespace + ".", StringComparison.Ordinal)) return null;
        string file = name.Substring(Namespace.Length + 1);
        if (file.IndexOfAny(new[] { '/', '\\' }) >= 0 || file.Contains("..")) return null;     // nur Dateien direkt im Ordner
        string p = Path.Combine(_dir, file);
        return File.Exists(p) ? p : null;
    }

    public override Stream GetManifestResourceStream(string name)
    {
        var p = PathOf(name);
        return p == null ? null : File.OpenRead(p);
    }

    public override ManifestResourceInfo GetManifestResourceInfo(string resourceName) =>
        PathOf(resourceName) == null ? null : new ManifestResourceInfo(this, Path.GetFileName(resourceName), ResourceLocation.Embedded);

    public override string[] GetManifestResourceNames() =>
        Directory.Exists(_dir) ? Directory.GetFiles(_dir).Select(f => Namespace + "." + Path.GetFileName(f)).ToArray() : Array.Empty<string>();

    public override string FullName => "AtlasMaps:" + Namespace;
}
