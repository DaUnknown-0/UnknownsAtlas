// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasPlanetarium - die Show im Planetarium des Vesper Museum (User 01.10.). Der Host startet alle
// 45 bis 75 s eine Vorfuehrung (RPC 237 Op 14); jeder Client spielt sie ab Empfang ab: 2 s Gong, dann
// 16 s Dunkelheit mit kreisendem Sternenhimmel und wandernden Planeten auf dem Kuppelboden.
// Spielwirkung: wer im Planetarium steht, sieht nur noch 45 % so weit (wie die Geisterbahn im Park,
// aber zeitgesteuert). Nie waehrend Meeting, Rauswurf, kritischer Sabotage oder "Rex erwacht".

using System;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class AtlasPlanetarium
{
    private const string LogPrefix = "[Atlas/Planetarium]";
    internal const byte OpShow = 14;
    private const float Announce = 2f, ShowTime = 16f, FadeT = 1.5f, Dark = 0.45f;
    private const int LayerObjects = 12;

    private static bool Museum => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "museum";
    private static float _t0 = -100f, _next = -1f, _level;
    private static Transform _root;
    private static SpriteRenderer _shade, _sky;
    private static readonly SpriteRenderer[] Planets = new SpriteRenderer[3];
    private static Bounds _room;
    private static bool _hasRoom;

    public static bool Running => Time.time - _t0 < Announce + ShowTime;

    public static void Reset()
    {
        _t0 = -100f; _next = -1f; _level = 0f;
        _root = null; _shade = _sky = null; _hasRoom = false;
        for (int i = 0; i < Planets.Length; i++) Planets[i] = null;
    }

    public static void Build(ShipStatus ship, Transform worldRoot)
    {
        Reset();
        if (!ship.FastRooms.ContainsKey(SystemTypes.Nav) || ship.FastRooms[SystemTypes.Nav].roomArea == null) return;
        _room = ship.FastRooms[SystemTypes.Nav].roomArea.bounds;
        _hasRoom = true;
        var go = new GameObject("Atlas_Planetarium") { layer = LayerObjects };
        go.transform.SetParent(worldRoot, false);
        var ls = worldRoot.lossyScale;
        go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f / ls.z);   // Meter sind Meter
        go.transform.position = Vector3.zero;
        _root = go.transform;

        var c = (Vector2)_room.center;
        // Abdunklung ueber dem Boden, darunter liegen nur der Boden selbst (z 9) und die Laternenscheine
        _shade = Spr("Shade", Px, c, 8.4f);
        _shade.transform.localScale = new Vector3(_room.size.x / Px.bounds.size.x, _room.size.y / Px.bounds.size.y, 1f);
        _shade.color = new Color(0.02f, 0.03f, 0.08f, 0f);
        float d = Mathf.Min(_room.size.x, _room.size.y) * 0.95f;
        // gezeichnete Kuppel (tools/museum_art, 512 px) hat Vorrang vor der prozeduralen
        var dome = AtlasAssets.TaskSprite("task_museum_dome.png", 100f, new Vector2(0.5f, 0.5f)) ?? Stars;
        _sky = Spr("Sky", dome, c, 8.35f);
        _sky.transform.localScale = Vector3.one * (d / dome.bounds.size.x);
        _sky.color = new Color(0.75f, 0.85f, 1f, 0f);
        var cols = new[] { new Color(1f, 0.62f, 0.35f), new Color(0.55f, 0.8f, 1f), new Color(0.95f, 0.85f, 0.55f) };
        for (int i = 0; i < Planets.Length; i++)
        {
            var drawn = AtlasAssets.TaskSprite($"task_museum_planet_{i}.png", 100f, new Vector2(0.5f, 0.5f));
            var ps = drawn ?? Disc;
            Planets[i] = Spr($"Planet_{i}", ps, c, 8.3f);
            Planets[i].transform.localScale = Vector3.one * (0.35f + 0.18f * i) * (drawn != null ? 1.5f : 1f) / ps.bounds.size.x;
            var col = drawn != null ? Color.white : cols[i];                       // gezeichnete Planeten nicht toenen
            Planets[i].color = new Color(col.r, col.g, col.b, 0f);
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: dome {_room.size.x:F1} x {_room.size.y:F1} m at {c.x:F1}/{c.y:F1}");
    }

    private static SpriteRenderer Spr(string name, Sprite s, Vector2 at, float z)
    {
        var go = new GameObject($"Atlas_Planetarium_{name}") { layer = LayerObjects };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(at.x, at.y, z);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = s;
        AtlasMuseumBuilder.Mask(sr);
        return sr;
    }

    // ------------------------------------------------------------------ Host und Netz

    public static void HostTick(bool critical)
    {
        if (!_hasRoom) return;
        float now = Time.time;
        if (_next < 0f) _next = now + Random.Range(30f, 45f);
        if (Running || now < _next) return;
        if (critical) { _next = now + 5f; return; }
        Start();
        AtlasWorld.Send(OpShow, null);
    }

    public static void Start()
    {
        _t0 = Time.time;
        _next = Time.time + Announce + ShowTime + Random.Range(45f, 75f);
        AtlasWeatherFx.Sfx("chime", Mathf.Lerp(0.45f, 0.08f, Mathf.Clamp01(DistToDome() / 25f)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} show starts");
    }

    private static float DistToDome()
    {
        var lp = PlayerControl.LocalPlayer;
        return lp != null && _hasRoom ? Vector2.Distance(lp.GetTruePosition(), _room.center) : 20f;
    }

    // ------------------------------------------------------------------ Ablauf

    public static void Tick(float dt)
    {
        if (!Museum || _root == null) return;
        try
        {
            float el = Time.time - _t0;
            bool meeting = MeetingHud.Instance != null || ExileController.Instance != null;
            if (meeting && Running) _t0 = -100f;                       // Meeting bricht die Vorfuehrung ab
            float target = 0f;
            if (Running && el >= Announce)
            {
                float a = Mathf.Clamp01((el - Announce) / FadeT), b = Mathf.Clamp01((Announce + ShowTime - el) / FadeT);
                target = Mathf.Min(a, b);
            }
            _level = Mathf.MoveTowards(_level, target, dt / FadeT * 1.5f);
            float t = Time.time;
            if (_shade != null) _shade.color = new Color(0.02f, 0.03f, 0.08f, 0.72f * _level);
            if (_sky != null)
            {
                _sky.color = new Color(0.75f, 0.85f, 1f, _level);
                _sky.transform.localEulerAngles = new Vector3(0f, 0f, t * 4f);     // der Himmel kreist langsam
            }
            var c = (Vector2)_room.center;
            float r0 = Mathf.Min(_room.size.x, _room.size.y) * 0.18f;
            for (int i = 0; i < Planets.Length; i++)
            {
                var p = Planets[i];
                if (p == null) continue;
                float ang = t * (0.35f - i * 0.09f) + i * 2.1f, r = r0 * (1f + i * 0.75f);
                p.transform.position = new Vector3(c.x + Mathf.Cos(ang) * r, c.y + Mathf.Sin(ang) * r * 0.8f, 8.3f);
                var col = p.color;
                p.color = new Color(col.r, col.g, col.b, _level);
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    /// <summary>Sichtfaktor (AtlasWorld.VisionFactor): im Planetarium waehrend der Show.</summary>
    public static float VisionFactor(Vector2 pos)
    {
        if (_level <= 0f || !_hasRoom) return 1f;
        var ship = ShipStatus.Instance;
        if (ship == null || !ship.FastRooms.ContainsKey(SystemTypes.Nav)) return 1f;
        var area = ship.FastRooms[SystemTypes.Nav].roomArea;
        return area != null && area.OverlapPoint(pos) ? Mathf.Lerp(1f, Dark, _level) : 1f;
    }

    public static string DiagState() => $"planetarium {(Running ? "show" : "idle")} level {_level:F2}";

    // ------------------------------------------------------------------ prozedurale Sprites

    private static Sprite _px, _stars, _disc;
    private static Sprite Px => _px ??= Make(4, 4, (x, y, _) => new Color32(255, 255, 255, 255));
    private static Sprite Disc => _disc ??= Make(48, 48, (x, y, _) =>
    {
        float dx = x - 23.5f, dy = y - 23.5f, r = Mathf.Sqrt(dx * dx + dy * dy);
        if (r > 23.5f) return new Color32(0, 0, 0, 0);
        if (r > 21f) return new Color32(30, 30, 50, 255);
        float lit = Mathf.Clamp01(0.55f + (-dx - dy) / 40f);                    // Licht von oben links
        byte v = (byte)(150 + 105 * lit);
        return new Color32(v, v, v, 255);
    });

    /// <summary>Sternenkuppel: runde Scheibe mit Sternen, Milchstrassenband und Sternbildlinien.</summary>
    private static Sprite Stars => _stars ??= Make(512, 512, StarPixel);

    private static Color32 StarPixel(int x, int y, System.Random rnd)
    {
        float dx = (x - 255.5f) / 256f, dy = (y - 255.5f) / 256f, r = Mathf.Sqrt(dx * dx + dy * dy);
        if (r > 1f) return new Color32(0, 0, 0, 0);
        float edge = Mathf.Clamp01((1f - r) * 12f);
        // Milchstrasse: weiches Band schraeg ueber die Kuppel
        float band = Mathf.Exp(-Mathf.Pow((dx * 0.6f + dy * 0.8f) * 4.5f, 2f)) * 0.35f;
        float a = band * (0.6f + 0.4f * Mathf.PerlinNoise(x * 0.03f, y * 0.03f));
        float star = 0f;
        double v = rnd.NextDouble();
        if (v < 0.006) star = 1f; else if (v < 0.02) star = 0.45f;
        a = Mathf.Max(a, star);
        return new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(a) * edge));
    }

    private static Sprite Make(int w, int h, Func<int, int, System.Random, Color32> f)
    {
        var rnd = new System.Random(4242);
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        var px = new Color32[w * h];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                px[y * w + x] = f(x, y, rnd);
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Bilinear;
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.Apply(false, true);                                                  // nicht lesbar: 32-Bit-Prozess
        tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var s = Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f);
        s.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        return s;
    }
}
