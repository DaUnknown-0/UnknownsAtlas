// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasAssetStore - Kartenbilder aus dem Asset-Repo statt aus der DLL (wie die Musik von Forgotten Fixes).
//
// Die grossen Grafiken (Boden-, Objekt- und Konsolenatlanten, Minispiel- und Rauswurfbilder; Liste in
// AtlasAssetCatalog.g.cs, erzeugt von tools/build_assets_repo.py) liegen nicht mehr in der DLL, sondern in
// BepInEx/atlas-assets. Sie werden automatisch geladen und gegen den Katalog geprueft:
//   - bei JEDEM Start: alle Dateien im Hintergrund auf Groesse und SHA-256 pruefen, was fehlt oder abweicht,
//     sofort neu laden (nur aus dem Asset-Repo am Katalog-Tag oder einem lokalen Testserver);
//   - bei Veraenderungen: ein FileSystemWatcher meldet geaenderte, geloeschte oder umbenannte Dateien, die
//     werden neu geprueft und bei Bedarf neu geladen; ausserdem prueft jeder Lesezugriff Groesse und Zeitstempel
//     gegen den zuletzt bestaetigten Stand (aendert sich etwas am Ort, wird erneut gehasht).
// Gelesen wird nur, was bestaetigt ist. Fehlt eine Datei, liefert Open null (Aufrufer melden "missing").
// Aufraeumen: beim Start loescht die Pruefung im Asset-Ordner alles, was der Katalog nicht kennt (alte Versionen,
// umbenannte Dateien, liegengebliebene .part-Reste); Katalogdateien mit falscher Pruefsumme werden ebenfalls
// geloescht und neu geladen. Nur Dateien direkt in BepInEx/atlas-assets, nie Unterordner oder andere Orte.

using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

namespace UnknownsAtlas;

internal static class AtlasAssetStore
{
    private const string LogPrefix = "[Atlas/Assets]";
    private const string ResPrefix0 = "UnknownsAtlas.";
    internal const string DefaultSourceBase = "https://raw.githubusercontent.com/DaUnknown-0/UnknownsAtlas-Assets/";
    private const int Parallel = 4;
    private const int MaxTries = 4;
    private static readonly float[] Backoff = { 0f, 10f, 30f, 60f };          // Wartezeit vor Versuch 1..4 (s)

    internal static string Folder => Path.Combine(BepInEx.Paths.BepInExRootPath, "atlas-assets");
    internal static string Source { get; private set; } = DefaultSourceBase + AtlasAssetCatalog.Tag + "/files/";

    private sealed class Entry
    {
        public string Name;
        public string Res;
        public long Size;
        public string Sha256;
        // bestaetigter Stand (Groesse + Zeitstempel der Datei, als sie zuletzt gehasht wurde); 0 = nicht bestaetigt
        public long OkLength;
        public long OkTicks;
        public int Tries;
        public float RetryAt;
    }

    private static readonly Dictionary<string, Entry> ByName =
        AtlasAssetCatalog.Files.ToDictionary(f => f.Name, f => new Entry { Name = f.Name, Res = f.Res, Size = f.Size, Sha256 = f.Sha256 },
            StringComparer.OrdinalIgnoreCase);
    // Ressourcenname (UnknownsAtlas.Resources.x, UnknownsAtlas.Maps.train.x) -> Eintrag
    private static readonly Dictionary<string, Entry> ByRes = ByName.Values.ToDictionary(e => e.Res, StringComparer.Ordinal);
    private static readonly object Gate = new();
    private static readonly ConcurrentQueue<string> Dirty = new();
    private static readonly List<string> Queue = new();
    private static FileSystemWatcher _watcher;
    private static MonoBehaviour _host;
    private static bool _running, _verifying;
    private static int _active;

    internal static int Total => ByName.Count;
    internal static int ReadyCount { get { lock (Gate) return ByName.Values.Count(e => e.OkLength > 0); } }
    internal static bool AllReady => ReadyCount == Total;
    internal static int Failed { get; private set; }
    internal static bool Busy => _verifying || _active > 0 || Queue.Count > 0;

    private static void Log(string s) => AtlasPlugin.Logger.LogInfo($"{LogPrefix} {s}");
    private static void Warn(string s) => AtlasPlugin.Logger.LogWarning($"{LogPrefix} {s}");

    /// <summary>Gehoert die Ressource zum Katalog? (dann kommt sie aus dem Asset-Ordner, nie aus der DLL)</summary>
    internal static bool Owns(Assembly asm, string res, out string file)
    {
        file = null;
        if (res == null || !res.StartsWith(ResPrefix0, StringComparison.Ordinal)) return false;
        if (asm != null && asm != typeof(AtlasAssetStore).Assembly) return false;
        if (!ByRes.TryGetValue(res, out var e)) return false;
        file = e.Name;
        return true;
    }

    /// <summary>Katalogdatei, die noch kommen kann (nicht bestaetigt, Download nicht aufgegeben)? Aufrufer warten dann
    /// still, statt "missing" zu melden oder auf Ersatz umzuschalten.</summary>
    internal static bool Waiting(Assembly asm, string res)
    {
        if (!Owns(asm, res, out var file) || Confirmed(file)) return false;
        int tries;
        lock (Gate) tries = ByName[file].Tries;
        if (tries < MaxTries || _verifying) return true;
        lock (Queue) return Queue.Contains(file);
    }

    /// <summary>Katalogeintraege unter einem Ressourcen-Namensraum (fuer den Inhalts-Hash der Kartendateien).</summary>
    internal static IEnumerable<(string Res, string Sha256)> UnderNamespace(string ns) =>
        ByRes.Values.Where(e => e.Res.StartsWith(ns + ".", StringComparison.Ordinal)).OrderBy(e => e.Res, StringComparer.Ordinal)
            .Select(e => (e.Res, e.Sha256));

    /// <summary>Stream einer Ressource: Katalogdateien aus dem Asset-Ordner (nur bestaetigt), alles andere eingebettet.</summary>
    internal static Stream Open(Assembly asm, string res)
    {
        asm ??= typeof(AtlasAssetStore).Assembly;
        if (!Owns(asm, res, out var file)) return asm.GetManifestResourceStream(res);
        return Confirmed(file) ? new FileStream(PathOf(file), FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete) : null;
    }

    /// <summary>Gibt es die Ressource (eingebettet oder bestaetigt im Asset-Ordner)?</summary>
    internal static bool Exists(Assembly asm, string res)
    {
        asm ??= typeof(AtlasAssetStore).Assembly;
        if (!Owns(asm, res, out var file))
        {
            try { return asm.GetManifestResourceInfo(res) != null; } catch { return false; }
        }
        return Confirmed(file);
    }

    /// <summary>Alle Katalogdateien einer Karte (Praefix wie "museum_") bestaetigt?</summary>
    internal static bool MapReady(string prefix)
    {
        lock (Gate)
            return ByName.Values.Where(e => e.Name.StartsWith(prefix + "_", StringComparison.OrdinalIgnoreCase)).All(e => e.OkLength > 0);
    }

    private static string PathOf(string file) => Path.Combine(Folder, file);

    /// <summary>Bestaetigt = beim letzten Hashen richtig UND seitdem weder Groesse noch Zeitstempel geaendert.</summary>
    private static bool Confirmed(string file)
    {
        Entry e;
        lock (Gate) { if (!ByName.TryGetValue(file, out e) || e.OkLength == 0) return false; }
        try
        {
            var fi = new FileInfo(PathOf(file));
            if (fi.Exists && fi.Length == e.OkLength && fi.LastWriteTimeUtc.Ticks == e.OkTicks) return true;
        }
        catch { }
        lock (Gate) e.OkLength = 0;                                   // am Ort veraendert: neu pruefen und laden
        Dirty.Enqueue(file);
        return false;
    }

    // ------------------------------------------------------------------ Start, Pruefen, Ueberwachen

    /// <summary>Beim Plugin-Start: Quelle festlegen, Ordner ueberwachen, alles pruefen, Fehlendes laden.</summary>
    internal static void Start(MonoBehaviour host, string sourceOverride)
    {
        _host = host;
        string s = sourceOverride?.Trim();
        if (!string.IsNullOrEmpty(s))
        {
            if (!s.EndsWith("/")) s += "/";
            if (s.StartsWith(DefaultSourceBase, StringComparison.Ordinal) || s.StartsWith("http://127.0.0.1:", StringComparison.Ordinal))
                Source = s;
            else Warn($"download source '{s}' ignored (only the asset repository or a local test server)");
        }
        try { Directory.CreateDirectory(Folder); } catch (Exception e) { Warn($"folder: {e.Message}"); }
        Watch();
        VerifyAll("start");
    }

    private static void Watch()
    {
        try
        {
            _watcher = new FileSystemWatcher(Folder) { IncludeSubdirectories = false, NotifyFilter =
                NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size };
            FileSystemEventHandler on = (_, a) => Touched(a.Name);
            _watcher.Changed += on;
            _watcher.Deleted += on;
            _watcher.Created += on;
            _watcher.Renamed += (_, a) => { Touched(a.OldName); Touched(a.Name); };
            _watcher.EnableRaisingEvents = true;
        }
        catch (Exception e) { Warn($"watching the folder failed ({e.Message}); changes are found on the next read"); }
    }

    private static void Touched(string name)
    {
        if (string.IsNullOrEmpty(name) || name.EndsWith(".part", StringComparison.OrdinalIgnoreCase)) return;
        if (ByName.ContainsKey(name)) Dirty.Enqueue(name);
    }

    /// <summary>Alle Katalogdateien im Hintergrund hashen; was fehlt oder abweicht, kommt in die Download-Warteschlange.</summary>
    internal static void VerifyAll(string why)
    {
        if (_verifying) return;
        _verifying = true;
        var names = ByName.Keys.ToList();
        Task.Run(() =>
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            if (why == "start") Cleanup();
            var bad = new List<string>();
            foreach (var n in names) if (!Check(n)) bad.Add(n);
            return (bad, sw.ElapsedMilliseconds);
        }).ContinueWith(t =>
        {
            _verifying = false;
            if (t.IsFaulted) { Warn($"check failed: {t.Exception?.GetBaseException().Message}"); return; }
            var (bad, ms) = t.Result;
            if (bad.Count == 0) Log($"{why}: all {Total} files present and verified ({ms} ms)");
            else
            {
                Log($"{why}: {Total - bad.Count}/{Total} verified, {bad.Count} missing or changed ({ms} ms), loading from {Source}");
                lock (Queue) foreach (var n in bad) if (!Queue.Contains(n)) Queue.Add(n);
            }
        });
    }

    /// <summary>Hintergrund, beim Start: im eigenen Ordner alles loeschen, was nicht im Katalog steht.</summary>
    private static void Cleanup()
    {
        try
        {
            var dir = new DirectoryInfo(Folder);
            if (!dir.Exists || !string.Equals(dir.Name, "atlas-assets", StringComparison.OrdinalIgnoreCase)) return;
            int n = 0;
            long bytes = 0;
            foreach (var f in dir.GetFiles())
            {
                if (ByName.ContainsKey(f.Name)) continue;
                try { long len = f.Length; f.Delete(); n++; bytes += len; }
                catch (Exception e) { Warn($"cleanup: {f.Name}: {e.Message}"); }
            }
            if (n > 0) Log($"cleanup: removed {n} file(s) not in catalog {AtlasAssetCatalog.Tag} ({bytes / 1024} KB)");
        }
        catch (Exception e) { Warn($"cleanup failed: {e.Message}"); }
    }

    /// <summary>Eine Datei gegen den Katalog pruefen (Groesse, dann SHA-256). Laeuft im Hintergrund.</summary>
    private static bool Check(string name)
    {
        var e = ByName[name];
        try
        {
            var fi = new FileInfo(PathOf(name));
            if (!fi.Exists) { lock (Gate) e.OkLength = 0; return false; }
            if (fi.Length != e.Size) { lock (Gate) e.OkLength = 0; Discard(fi); return false; }
            string hash;
            using (var fs = new FileStream(fi.FullName, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            using (var sha = SHA256.Create())
                hash = Convert.ToHexString(sha.ComputeHash(fs)).ToLowerInvariant();
            if (hash != e.Sha256) { lock (Gate) e.OkLength = 0; Discard(fi); return false; }
            fi.Refresh();
            lock (Gate) { e.OkLength = fi.Length; e.OkTicks = fi.LastWriteTimeUtc.Ticks; }
            return true;
        }
        catch { lock (Gate) e.OkLength = 0; return false; }
    }

    /// <summary>Katalogdatei mit falschem Inhalt (alte Version, beschaedigt) loeschen; der Download ersetzt sie.</summary>
    private static void Discard(FileInfo fi)
    {
        try { fi.Delete(); } catch { }
    }

    // ------------------------------------------------------------------ Takt: Meldungen abarbeiten, laden

    /// <summary>Aus dem Hauptthread (AtlasUpdater.Update): Aenderungen nachpruefen und Downloads starten.</summary>
    internal static void Tick()
    {
        if (_host == null) return;
        if (!Dirty.IsEmpty)
        {
            var batch = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            while (Dirty.TryDequeue(out var n)) batch.Add(n);
            lock (Queue) batch.RemoveWhere(n => Queue.Contains(n));   // the thread pool adds under this lock
            if (batch.Count > 0)
                Task.Run(() => batch.Where(n => !Check(n)).ToList()).ContinueWith(t =>
                {
                    if (t.IsFaulted) return;
                    foreach (var n in t.Result) lock (Queue) if (!Queue.Contains(n)) Queue.Add(n);
                });
        }
        AtlasMuseumBuilder.TryLateFill();
        lock (Queue)
        {
            // die gewaehlte (oder erzwungene) Karte zuerst
            string prefer = AtlasPlugin.CfgForceMap?.Value;
            if (string.IsNullOrEmpty(prefer)) prefer = AtlasSelection.CurrentKey;
            if (!string.IsNullOrEmpty(prefer) && Queue.Count > 1)
            {
                var first = Queue.Where(n => n.StartsWith(prefer + "_", StringComparison.OrdinalIgnoreCase)).ToList();
                if (first.Count > 0 && !Queue[0].StartsWith(prefer + "_", StringComparison.OrdinalIgnoreCase))
                {
                    Queue.RemoveAll(n => first.Contains(n));
                    Queue.InsertRange(0, first);
                }
            }
            int scanned = 0;
            while (_active < Parallel && Queue.Count > 0 && scanned < Queue.Count)
            {
                string n = Queue[0];
                var e = ByName[n];
                if (Time.realtimeSinceStartup < e.RetryAt) { Queue.RemoveAt(0); Queue.Add(n); scanned++; continue; }
                Queue.RemoveAt(0);
                if (e.Tries >= MaxTries) continue;
                e.Tries++;
                _active++;
                BepInEx.Unity.IL2CPP.Utils.MonoBehaviourExtensions.StartCoroutine(_host, Fetch(e));
            }
        }
    }

    private static int _loadedThisRun;

    private static IEnumerator Fetch(Entry e)
    {
        var www = new UnityWebRequest();
        www.SetMethod(UnityWebRequest.UnityWebRequestMethod.Get);
        www.SetUrl(Source + Uri.EscapeDataString(e.Name));
        www.SetRequestHeader("User-Agent", $"UnknownsAtlas/{AtlasPlugin.Version}");
        www.downloadHandler = new DownloadHandlerBuffer();
        www.timeout = 60;
        var op = www.SendWebRequest();
        while (!op.isDone) yield return null;
        byte[] data = null;
        string error = null;
        if (www.isNetworkError || www.isHttpError) error = $"HTTP {www.responseCode} {www.error}";
        else data = www.downloadHandler.data;
        www.downloadHandler.Dispose();
        www.Dispose();
        if (error == null)
        {
            var write = Task.Run(() => Store(e, data));
            while (!write.IsCompleted) yield return null;
            error = write.IsFaulted ? write.Exception?.GetBaseException().Message : write.Result;
        }
        _active--;
        if (error == null)
        {
            _loadedThisRun++;
            _failStreak = 0;
            if (_active == 0 && ReadyCount == Total) Log($"all {Total} files ready ({_loadedThisRun} downloaded since start)");
        }
        else
        {
            // still bei Fehlern: die erste Stoerung eine Zeile, danach nur zaehlen und am Ende eine Zusammenfassung
            _failStreak++;
            if (!_failWarned) { _failWarned = true; Warn($"download failed ({e.Name}: {error}); retrying in the background, further failures are only counted"); }
            if (_failStreak >= GiveUpStreak && _loadedThisRun == 0)
            {
                // Quelle nicht erreichbar: fuer diese Sitzung aufhoeren, statt jede Datei viermal anzufragen
                lock (Queue) { foreach (var n in Queue) lock (Gate) ByName[n].Tries = MaxTries; Queue.Clear(); }
                lock (Gate) e.Tries = MaxTries;
            }
            if (e.Tries < MaxTries)
            {
                e.RetryAt = Time.realtimeSinceStartup + Backoff[Math.Min(e.Tries, Backoff.Length - 1)];
                lock (Queue) Queue.Add(e.Name);
            }
        }
        bool idle;
        lock (Queue) idle = _active == 0 && Queue.Count == 0;
        if (idle && !_verifying && ReadyCount < Total && !_summaryLogged)
        {
            _summaryLogged = true;
            Failed = Total - ReadyCount;
            Warn($"{Failed}/{Total} files could not be downloaded from {Source}; maps and pictures using them stay incomplete until the next start");
        }
    }

    private const int GiveUpStreak = 12;
    private static int _failStreak;
    private static bool _failWarned, _summaryLogged;

    /// <summary>Hintergrund: Groesse und SHA-256 gegen den Katalog, daneben schreiben, dann an den Platz schieben.</summary>
    private static string Store(Entry e, byte[] data)
    {
        if (data == null || data.Length != e.Size) return $"size {data?.Length ?? 0} instead of {e.Size}";
        string hash;
        using (var sha = SHA256.Create()) hash = Convert.ToHexString(sha.ComputeHash(data)).ToLowerInvariant();
        if (hash != e.Sha256) return "checksum does not match";
        Directory.CreateDirectory(Folder);
        string path = PathOf(e.Name), tmp = path + ".part";
        File.WriteAllBytes(tmp, data);
        if (File.Exists(path)) File.Delete(path);
        File.Move(tmp, path);
        var fi = new FileInfo(path);
        lock (Gate) { e.OkLength = fi.Length; e.OkTicks = fi.LastWriteTimeUtc.Ticks; }
        return null;
    }

    private static string _shown;
    private static float _shownAt;

    /// <summary>Aus dem Lobby-Takt: Stand als Hinweis zeigen, solange etwas fehlt, und einmal "fertig".</summary>
    internal static void LobbyTick()
    {
        string s = Status();
        if (s == null && _shown == null) return;
        if (s == null) s = "Atlas: map images ready";
        if (s == _shown && (s.StartsWith("Atlas: map images ready") || Time.time - _shownAt < 20f)) return;
        if (s != _shown && s.StartsWith("Atlas: downloading") && _shown != null && _shown.StartsWith("Atlas: downloading")
            && Time.time - _shownAt < 20f) return;
        try
        {
            var hud = DestroyableSingleton<HudManager>.InstanceExists ? DestroyableSingleton<HudManager>.Instance : null;
            if (hud == null || hud.Notifier == null) return;
            hud.Notifier.AddDisconnectMessage(s);
            _shown = s;
            _shownAt = Time.time;
        }
        catch { }
    }

    /// <summary>Kurzfassung fuer Lobby und Log: "Atlas: Kartenbilder 120/367".</summary>
    internal static string Status()
    {
        int ready = ReadyCount;
        if (ready == Total) return null;
        return Failed > 0
            ? $"Atlas: {Total - ready} map images could not be downloaded (next start retries)"
            : $"Atlas: downloading map images {ready}/{Total}";
    }
}
