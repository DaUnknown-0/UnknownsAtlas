// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasDusk - Daemmerung der Forest Station (User 01.10.): das Spiel beginnt am fruehen Abend und wird
// ueber sechs Minuten Nacht. Der Bildschirmschleier (AtlasWeatherFx) wird tiefblau, die Sicht sinkt auf
// 82 %, ueber den Lichtungen tauchen Gluehwuermchen auf. Uhr = Zeit seit dem Kartenbau; alle Clients bauen
// beim Rundenstart, ein Abgleich uebers Netz ist fuer eine so langsame Kurve nicht noetig.

using System;
using System.Collections.Generic;
using UnityEngine;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class AtlasDusk
{
    private const string LogPrefix = "[Atlas/Dusk]";
    private const float Start = 60f, Span = 300f, NightVision = 0.82f;
    private const int LayerObjects = 12, Count = 46;
    private static readonly SystemTypes[] Clearings =
        { SystemTypes.Nav, SystemTypes.Comms, SystemTypes.LifeSupp, SystemTypes.Reactor, SystemTypes.Weapons, SystemTypes.Shields };

    private static bool Wald => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "wald";
    private static float _built = -1f, _diagOffset;
    private static Transform _root;

    private sealed class Fly
    {
        public SpriteRenderer R;
        public Vector2 Home;
        public float Seed, Range;
    }

    private static readonly List<Fly> Flies = new();

    /// <summary>0 = Abend, 1 = Nacht.</summary>
    public static float Level
    {
        get
        {
            if (!Wald || _built < 0f) return 0f;
            float u = Mathf.Clamp01((Time.time - _built + _diagOffset - Start) / Span);
            return u * u * (3f - 2f * u);
        }
    }

    public static float VisionFactor => Mathf.Lerp(1f, NightVision, Level);

    public static void Reset()
    {
        _built = -1f; _diagOffset = 0f; _root = null;
        Flies.Clear();
    }

    public static void Build(ShipStatus ship, Transform worldRoot)
    {
        Reset();
        _built = Time.time;
        var go = new GameObject("Atlas_Dusk") { layer = LayerObjects };
        go.transform.SetParent(worldRoot, false);
        var ls = worldRoot.lossyScale;
        go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f / ls.z);
        go.transform.position = Vector3.zero;
        _root = go.transform;
        // Gluehwuermchen gleichmaessig auf die Lichtungen verteilt (Flaeche des Raum-Kolliders)
        var areas = new List<Collider2D>();
        foreach (var t in Clearings)
            if (ship.FastRooms.ContainsKey(t) && ship.FastRooms[t].roomArea != null) areas.Add(ship.FastRooms[t].roomArea);
        if (areas.Count == 0) return;
        var rnd = new System.Random(77);
        for (int i = 0; i < Count; i++)
        {
            var a = areas[i % areas.Count];
            var b = a.bounds;
            Vector2 p = b.center;
            for (int tries = 0; tries < 12; tries++)
            {
                var q = new Vector2(b.min.x + (float)rnd.NextDouble() * b.size.x, b.min.y + (float)rnd.NextDouble() * b.size.y);
                if (a.OverlapPoint(q)) { p = q; break; }
            }
            var f = new GameObject($"Atlas_Firefly_{i}") { layer = LayerObjects };
            f.transform.SetParent(_root, false);
            f.transform.position = new Vector3(p.x, p.y, -1.5f);                      // fliegt ueber allem
            var sr = f.AddComponent<SpriteRenderer>();
            sr.sprite = Glow;
            sr.color = new Color(0.85f, 1f, 0.45f, 0f);
            f.transform.localScale = Vector3.one * (0.5f + (float)rnd.NextDouble() * 0.25f) / Glow.bounds.size.x;
            AtlasMuseumBuilder.Mask(sr);
            Flies.Add(new Fly { R = sr, Home = p, Seed = (float)rnd.NextDouble() * 100f, Range = 0.6f + (float)rnd.NextDouble() * 1.2f });
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: {Flies.Count} firefl(ies) over {areas.Count} clearing(s)");
    }

    public static void Tick(float dt)
    {
        if (!Wald || _root == null) return;
        try
        {
            float lv = Level, t = Time.time;
            foreach (var f in Flies)
            {
                if (f.R == null) continue;
                float s = f.Seed;
                var off = new Vector2(Mathf.PerlinNoise(s, t * 0.12f) - 0.5f, Mathf.PerlinNoise(s + 31f, t * 0.12f) - 0.5f) * (2f * f.Range);
                f.R.transform.position = new Vector3(f.Home.x + off.x, f.Home.y + off.y, -1.5f);
                // Leuchten in Pulsen: an, kurz halten, aus
                float pulse = Mathf.Clamp01(Mathf.Sin(t * (1.1f + (s % 1f)) + s) * 1.6f - 0.3f);
                f.R.color = new Color(0.85f, 1f, 0.45f, Mathf.Clamp01(lv * 1.4f - 0.2f) * (0.35f + 0.65f * pulse));
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    /// <summary>Diagnose: die Uhr vorstellen (Sekunden), z. B. "dusk" = volle Nacht.</summary>
    public static void DiagAdvance(float seconds) => _diagOffset += seconds;

    public static string DiagState() => $"dusk {Level:F2}";

    private static Sprite _glow;
    private static Sprite Glow => _glow ??= MakeGlow();

    private static Sprite MakeGlow()
    {
        const int n = 32;
        var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
        var px = new Color32[n * n];
        for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
            {
                float dx = (x - 15.5f) / 16f, dy = (y - 15.5f) / 16f, r = Mathf.Sqrt(dx * dx + dy * dy);
                float a = Mathf.Clamp01(1f - r);
                a = Mathf.Max(a * a * a * 0.9f, Mathf.Clamp01((0.16f - r) * 14f)); // heller Kern, weicher Schein
                px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Bilinear;
        tex.Apply(false, true);
        tex.hideFlags |= HideFlags.HideAndDontSave;
        var s = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        s.hideFlags |= HideFlags.HideAndDontSave;
        return s;
    }
}
