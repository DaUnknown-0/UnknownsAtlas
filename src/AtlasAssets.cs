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
    /// </summary>
    private static void Shrink(Texture2D tex)
    {
        try { tex.Compress(true); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas] texture compress failed: {e.Message}"); }
        tex.Apply(false, true);
    }

    // Relocate-Karten (derzeit das Museum): Ressourcen "<praefix>_floor_{i}.jpg", "<praefix>_props_{k}.png",
    // "<praefix>_consoles_{k}.png", "<praefix>_minimap.png". Cache-Schluessel enthaelt den Praefix.
    private static readonly Dictionary<string, Texture2D> MapTextures = new();
    private static readonly Dictionary<string, Sprite> MapSprites = new();

    private static Texture2D MapTexture(string res)
    {
        if (MapTextures.TryGetValue(res, out var cached) && cached != null) return cached;
        var tex = LoadTexture(res, mips: true);
        if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Trilinear;
        Shrink(tex);
        MapTextures[res] = tex;
        return tex;
    }

    /// <summary>Objektatlas k der Karte (Sprites schneidet der Builder aus AtlasMapDef.Props).</summary>
    public static Texture2D MapPropsTexture(AtlasMapDef m, int k) =>
        MapTexture($"UnknownsAtlas.Resources.{m.ResourcePrefix}_props_{k}.png");

    /// <summary>Atlas k der eigenen Task-Bloecke.</summary>
    public static Texture2D MapConsolesTexture(AtlasMapDef m, int k) =>
        MapTexture($"UnknownsAtlas.Resources.{m.ResourcePrefix}_consoles_{k}.png");

    /// <summary>Bodenkachel i, Pivot links unten, Massstab AtlasMapDef.FloorPixelsPerMeter.</summary>
    public static Sprite MapFloorTile(AtlasMapDef m, int i)
    {
        string res = $"UnknownsAtlas.Resources.{m.ResourcePrefix}_floor_{i}.jpg";
        if (MapSprites.TryGetValue(res, out var cached) && cached != null) return cached;
        var tex = MapTexture(res);
        if (tex == null) return null;
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), Vector2.zero,
            m.FloorPixelsPerMeter, 0, SpriteMeshType.FullRect);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[res] = sprite;
        return sprite;
    }

    /// <summary>Logo-Knopf (Freeplay-Menue) in der Breite widthUnits (Lokalraum des Vanilla-Knopfs).</summary>
    public static Sprite ButtonSprite(string file, float widthUnits)
    {
        string res = $"UnknownsAtlas.Resources.{file}";
        string key = $"{res}@{widthUnits:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        var tex = LoadTexture(res, mips: true);
        if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Trilinear;
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f),
            tex.width / Mathf.Max(0.01f, widthUnits));
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[key] = sprite;
        return sprite;
    }

    /// <summary>Grafik eines eigenen Minispiels (assets/task_*.png), gecacht.</summary>
    public static Sprite TaskSprite(string file, float ppu, Vector2 pivot)
    {
        file = AtlasTaskKit.Art(file);                                // Kartengrafik (AtlasMapDef.TaskArt)
        string res = $"UnknownsAtlas.Resources.{file}";
        string key = $"{res}@{ppu:F1}@{pivot.x:F3},{pivot.y:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        if (!MapTextures.TryGetValue(res, out var tex) || tex == null)
        {
            tex = LoadTexture(res);
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
    public static Texture2D TaskTextureCopy(string file) => LoadTexture($"UnknownsAtlas.Resources.{AtlasTaskKit.Art(file)}");

    /// <summary>Minimap der Karte in Kartenraum-Einheiten (Weltmeter / MapScale).</summary>
    public static Sprite MapMinimapSprite(AtlasMapDef m, float mapScale)
    {
        string res = $"UnknownsAtlas.Resources.{m.ResourcePrefix}_minimap.png";
        string key = $"{res}@{mapScale:F3}";
        if (MapSprites.TryGetValue(key, out var cached) && cached != null) return cached;
        var tex = LoadTexture(res);
        if (tex == null) { AtlasPlugin.Logger.LogError($"[Atlas] embedded resource missing: {res}"); return null; }
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Bilinear;
        float ppu = tex.width / ((m.MaxX - m.MinX) / mapScale);
        var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), ppu);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        MapSprites[key] = sprite;
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

    private static Texture2D LoadTexture(string path, bool mips = false)
    {
        try
        {
            var asm = Assembly.GetExecutingAssembly();
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
