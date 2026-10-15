// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasAssets - laedt die eingebetteten Kartenbilder. Nur eigene Assets werden
// gebuendelt (Projektvorgabe); AU-Prefabs holt der Builder zur Laufzeit.
//
// Ladeschema uebernommen aus UnknownsCollection/UCAssets.cs LoadTexture, inklusive der
// dort im Audit 2026-08-23 (L-19) gelernten Lektion: Stream.Read darf legitim weniger
// Bytes liefern als angefordert. Ein einzelner Read gibt dann ein abgeschnittenes Array
// an ImageConversion.LoadImage weiter, das entweder fehlschlaegt oder ein korruptes Bild
// dekodiert. Deshalb die Leseschleife.

using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasAssets
{
    // ------------------------------------------------------------ Relocate-Karten

    private static Sprite _consoleMarker;

    /// <summary>
    /// Speicher: der Prozess ist 32-Bit, und allein das Hut-Pack belegt ~600 MB. Boden und
    /// Objektatlanten werden deshalb nach dem Laden DXT-komprimiert und nicht lesbar gemacht.
    /// Museumstexturen laden MIT Mipmaps und trilinear (User 22.09.: feine Linien flimmerten beim
    /// Laufen), Kosten +33 % Speicher.
    /// Schnelle Kompression (false): die hochwertige brauchte im Hauptthread je Textur ein Mehrfaches und
    /// trug den groessten Teil der 12 s Rundenstart-Pause vom 09.10. (siehe AtlasPreload).
    /// </summary>
    private static void Shrink(Texture2D tex)
    {
        try { tex.Compress(false); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas] texture compress failed: {e.Message}"); }
        tex.Apply(false, true);
    }

    // Relocate-Karten (derzeit das Museum): Ressourcen "<praefix>_floor_{i}.jpg", "<praefix>_props_{k}.png",
    // "<praefix>_consoles_{k}.png", "<praefix>_minimap.png". Cache-Schluessel enthaelt den Praefix.
    private static readonly Dictionary<string, Texture2D> MapTextures = new();
    private static readonly Dictionary<string, Sprite> MapSprites = new();

    /// <summary>
    /// Gibt die Kartenpakete (Boden, Objekte, Konsolen, Minimap) aller ANDEREN Karten frei. Sie
    /// tragen HideAndDontSave und werden nie entladen: Museum, Wald und Park nacheinander in einer
    /// Sitzung hielten zusammen rund 235 MB im 32-Bit-Prozess. Aufgerufen beim Aufbau einer Karte;
    /// der Builder schneidet seine Sprites bei jedem Aufbau neu und haelt keine aus einer frueheren
    /// Runde, eine wieder gewaehlte Karte laedt ihr Paket einfach erneut.
    /// </summary>
    private static string _lastKey;

    public static void ReleaseOtherMaps(AtlasMapDef keep)
    {
        try
        {
            // A map pack is "<prefix>_floor_*", "_props_*", "_consoles_*" or "_minimap" (see above);
            // task art and buttons have other names and stay. Maps of other plugins carry their own
            // namespace ("<Plugin>.Resources.<prefix>_floor_0.jpg"), hence the open namespace part.
            string keepPrefix = Res(keep, $"{keep.ResourcePrefix}_");
            var pack = new System.Text.RegularExpressions.Regex(
                @"^[A-Za-z0-9_.]*\.Resources\.[A-Za-z0-9]+_(floor_|props_|consoles_|minimap)");
            // Minispiel- und Weltgrafik (task_*) haengt an der Karte (AtlasMapDef.TaskArt) und lag nach einem
            // Kartenwechsel weiter unkomprimiert im Speicher (Review 09.10.). Beim Wechsel wird sie mit
            // freigegeben und bei Bedarf neu geladen; beim Bau derselben Karte bleibt sie. Kein lebendes Objekt
            // haelt sie hier noch: die alte Runde ist zerstoert, AtlasUse prueft seine Symbole auf null.
            bool switching = _lastKey != null && _lastKey != keep.Key;
            _lastKey = keep.Key;
            const string taskPrefix = "UnknownsAtlas.Resources.task_";
            bool Other(string key) =>
                (!key.StartsWith(keepPrefix, StringComparison.Ordinal) && pack.IsMatch(key)) ||
                (switching && key.StartsWith(taskPrefix, StringComparison.Ordinal));
            int freed = 0;
            foreach (var key in new List<string>(Pending.Keys))
                if (Other(key)) Pending.Remove(key);              // laufende Tasks enden von selbst, das Ergebnis verfaellt
            foreach (var key in new List<string>(MapSprites.Keys))
                if (Other(key)) { var s = MapSprites[key]; if (s != null) UnityEngine.Object.Destroy(s); MapSprites.Remove(key); }
            foreach (var key in new List<string>(MapTextures.Keys))
                if (Other(key)) { var t = MapTextures[key]; if (t != null) { UnityEngine.Object.Destroy(t); freed++; } MapTextures.Remove(key); }
            if (freed > 0) AtlasPlugin.Logger.LogInfo($"[Atlas] released {freed} texture(s) of other maps.");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas] releasing other maps failed: {e.Message}"); }
    }

    /// <summary>Voller Ressourcenname einer Datei des Kartenpakets (Atlas oder ein anderes Plugin).</summary>
    private static string Res(AtlasMapDef m, string file) =>
        $"{(string.IsNullOrEmpty(m.ResourceNamespace) ? "UnknownsAtlas.Resources" : m.ResourceNamespace)}.{file}";

    // ------------------------------------------------------------ Vorkomprimierte Pakete (.atx)

    /// <summary>Im Hintergrund entpackte .atx, die auf das Hochladen im Hauptthread warten (Schluessel = Ressource).</summary>
    private static readonly Dictionary<string, Task<PackedTexture>> Pending = new();

    /// <summary>Zeitmessung fuer die Rundenstart-Diagnose: Hauptthread-Zeit fuer Kartentexturen seit ResetTiming.</summary>
    internal static int TexturesLoaded, TexturesPacked;
    internal static double TextureMs;

    internal static void ResetTiming() { TexturesLoaded = 0; TexturesPacked = 0; TextureMs = 0; }

    internal static bool IsLoaded(string res) => MapTextures.TryGetValue(res, out var t) && t != null;

    /// <summary>
    /// Startet das Entpacken einer .atx im Hintergrund (nur reine .NET-Arbeit, kein Unity-Aufruf). false, wenn die
    /// Karte fuer diese Textur kein Paket mitbringt (dann laedt MapTexture wie frueher PNG/JPG).
    /// </summary>
    internal static bool BeginPrepare(string res, Assembly asm)
    {
        asm ??= Assembly.GetExecutingAssembly();
        if (IsLoaded(res) || Pending.ContainsKey(res)) return true;
        if (!AtlasTexturePack.Has(asm, res)) return false;
        Pending[res] = Task.Run(() => AtlasTexturePack.Read(asm, res));
        return true;
    }

    /// <summary>true, wenn die Textur ohne Warten fertig werden kann (geladen, entpackt oder ohne Paket).</summary>
    internal static bool IsReady(string res) =>
        IsLoaded(res) || !Pending.TryGetValue(res, out var task) || task.IsCompleted;

    internal static string FloorRes(AtlasMapDef m, int i) => Res(m, $"{m.ResourcePrefix}_floor_{i}.jpg");
    internal static string PropsRes(AtlasMapDef m, int k) => Res(m, $"{m.ResourcePrefix}_props_{k}.png");
    internal static string ConsolesRes(AtlasMapDef m, int k) => Res(m, $"{m.ResourcePrefix}_consoles_{k}.png");

    private static Texture2D MapTexture(string res, Assembly asm)
    {
        if (MapTextures.TryGetValue(res, out var cached) && cached != null) return cached;
        asm ??= Assembly.GetExecutingAssembly();
        var sw = System.Diagnostics.Stopwatch.StartNew();
        Texture2D tex = null;
        bool packed = false;
        // Paket: entpacken (im Vorladen schon im Hintergrund geschehen, sonst hier), dann nur hochladen.
        PackedTexture pt = null;
        if (Pending.TryGetValue(res, out var task)) { Pending.Remove(res); pt = task.Result; }
        else if (AtlasTexturePack.Has(asm, res)) pt = AtlasTexturePack.Read(asm, res);
        if (pt != null)
        {
            try { tex = AtlasTexturePack.Upload(pt); packed = true; }
            catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas] packed texture upload failed ({res}): {e.Message}"); }
        }
        else if (AtlasTexturePack.Has(asm, res))
            AtlasPlugin.Logger.LogWarning($"[Atlas] packed texture unreadable, falling back: {res}");

        if (tex == null)
        {
            // Alter Weg (Karten ohne .atx): dekodieren, Mipmaps, DXT-Kompression, alles im Hauptthread.
            tex = LoadTexture(res, mips: true, asm: asm);
            if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
            Shrink(tex);
        }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Trilinear;
        MapTextures[res] = tex;
        TexturesLoaded++;
        if (packed) TexturesPacked++;
        TextureMs += sw.Elapsed.TotalMilliseconds;
        return tex;
    }

    /// <summary>Objektatlas k der Karte (Sprites schneidet der Builder aus AtlasMapDef.Props).</summary>
    public static Texture2D MapPropsTexture(AtlasMapDef m, int k) => MapTexture(PropsRes(m, k), m.ResourceAssembly);

    /// <summary>Atlas k der eigenen Task-Bloecke.</summary>
    public static Texture2D MapConsolesTexture(AtlasMapDef m, int k) => MapTexture(ConsolesRes(m, k), m.ResourceAssembly);

    /// <summary>Bodenkachel i, Pivot links unten, Massstab AtlasMapDef.FloorPixelsPerMeter.</summary>
    public static Sprite MapFloorTile(AtlasMapDef m, int i)
    {
        string res = FloorRes(m, i);
        if (MapSprites.TryGetValue(res, out var cached) && cached != null) return cached;
        var tex = MapTexture(res, m.ResourceAssembly);
        if (tex == null) return null;
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), Vector2.zero,
            m.FloorPixelsPerMeter, 0, SpriteMeshType.FullRect);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[res] = sprite;
        return sprite;
    }

    /// <summary>Logo-Knopf (Freeplay-Menue) in der Breite widthUnits (Lokalraum des Vanilla-Knopfs).
    /// asm/ns: Herkunft bei Karten anderer Plugins (null = Atlas).</summary>
    public static Sprite ButtonSprite(string file, float widthUnits, Assembly asm = null, string ns = null)
    {
        string res = $"{(string.IsNullOrEmpty(ns) ? "UnknownsAtlas.Resources" : ns)}.{file}";
        string key = $"{res}@{widthUnits:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        var tex = LoadTexture(res, mips: true, asm: asm);
        if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Trilinear;
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f),
            tex.width / Mathf.Max(0.01f, widthUnits));
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[key] = sprite;
        return sprite;
    }

    /// <summary>Ressource und Assembly einer Minispiel-Grafik: erst das Paket der angemeldeten Karte (seit 15.10.,
    /// damit Karten anderer Plugins ihre Minispiel-Bilder selbst mitbringen), sonst die eigenen Ressourcen.</summary>
    private static (string Res, Assembly Asm) TaskRes(string file)
    {
        file = AtlasTaskKit.Art(file);                                // Kartengrafik (AtlasMapDef.TaskArt)
        var m = AtlasMuseumBuilder.D;
        if (m != null && m.ResourceAssembly != null && !string.IsNullOrEmpty(m.ResourceNamespace))
        {
            string own = $"{m.ResourceNamespace}.{file}";
            try { if (m.ResourceAssembly.GetManifestResourceInfo(own) != null) return (own, m.ResourceAssembly); } catch { }
        }
        return ($"UnknownsAtlas.Resources.{file}", null);
    }

    /// <summary>Grafik eines eigenen Minispiels (assets/task_*.png), gecacht.</summary>
    public static Sprite TaskSprite(string file, float ppu, Vector2 pivot)
    {
        var (res, asm) = TaskRes(file);
        string key = $"{res}@{ppu:F1}@{pivot.x:F3},{pivot.y:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        if (!MapTextures.TryGetValue(res, out var tex) || tex == null)
        {
            tex = LoadTexture(res, asm: asm);
            if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.filterMode = FilterMode.Bilinear;
            tex.Apply(false, true);                                   // nicht lesbar: kein CPU-Abbild
            MapTextures[res] = tex;
        }
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), pivot, ppu);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[key] = sprite;
        return sprite;
    }

    /// <summary>Frische, LESBARE Kopie einer Minispiel-Textur (z. B. die Staubschicht, die man wegwischt).</summary>
    public static Texture2D TaskTextureCopy(string file)
    {
        var (res, asm) = TaskRes(file);
        return LoadTexture(res, asm: asm);
    }

    /// <summary>Minimap der Karte in Kartenraum-Einheiten (Weltmeter / MapScale).</summary>
    public static Sprite MapMinimapSprite(AtlasMapDef m, float mapScale)
    {
        string res = Res(m, string.IsNullOrEmpty(m.MinimapFile) ? $"{m.ResourcePrefix}_minimap.png" : m.MinimapFile);
        string key = $"{res}@{mapScale:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        var tex = LoadTexture(res, asm: m.ResourceAssembly);
        if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Bilinear;
        float ppu = tex.width / ((m.MaxX - m.MinX) / mapScale);
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), ppu);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[key] = sprite;
        // The texture is kept with the map's other textures, so ReleaseOtherMaps frees it with the
        // sprite (audit 04.10.: destroying the sprite left its 4-5 MB texture behind on every map
        // change). No CPU copy is needed once it is on the GPU.
        try { tex.Apply(false, true); } catch { }
        MapTextures[key] = tex;
        return sprite;
    }

    /// <summary>
    /// Graybox-Konsole (0,6 x 0,6 m): dunkles Gehaeuse, bernsteinfarbener Schirm, schwarzer
    /// Umriss wie bei Among-Us-Objekten. Prozedural, damit keine Datei noetig ist.
    /// </summary>
    public static Sprite ConsoleMarkerSprite()
    {
        if (_consoleMarker != null) return _consoleMarker;
        const int n = 48;
        var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
        var px = new Color32[n * n];
        var outline = new Color32(13, 15, 18, 255);
        var body = new Color32(74, 82, 94, 255);
        var screen = new Color32(207, 144, 54, 255);
        for (int y = 0; y < n; y++)
        for (int x = 0; x < n; x++)
        {
            bool inBody = x >= 4 && x < n - 4 && y >= 4 && y < n - 10;
            bool inOutline = x >= 1 && x < n - 1 && y >= 1 && y < n - 7;
            bool inScreen = x >= 11 && x < n - 11 && y >= 16 && y < n - 17;
            px[y * n + x] = inScreen ? screen : inBody ? body : inOutline ? outline : new Color32(0, 0, 0, 0);
        }
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Point;
        tex.Apply(false, false);
        tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        _consoleMarker = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.3f), n / 0.6f);
        _consoleMarker.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        return _consoleMarker;
    }

    private static Texture2D LoadTexture(string path, bool mips = false, Assembly asm = null)
    {
        try
        {
            asm ??= Assembly.GetExecutingAssembly();
            using Stream stream = asm.GetManifestResourceStream(path);
            if (stream == null) return null;

            var data = new byte[stream.Length];
            int read = 0;
            while (read < data.Length)
            {
                int n = stream.Read(data, read, data.Length - read);
                if (n <= 0) break;
                read += n;
            }
            if (read != data.Length) return null;

            var tex = new Texture2D(2, 2, TextureFormat.ARGB32, mips);
            if (!ImageConversion.LoadImage(tex, data, false)) return null;
            tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
            return tex;
        }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"[Atlas] texture load failed ({path}): {e.Message}");
            return null;
        }
    }
}
