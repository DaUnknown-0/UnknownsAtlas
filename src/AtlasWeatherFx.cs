// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasWeatherFx - Stimmung der Atlas-Karten: Wetterbild, Blitze, Waldbrand, Umgebungsklang.
//
// Rein lokal (der Zustand kommt aus AtlasWorld). Bildschirm-Effekte haengen an Camera.main
// (lokal z -30: ueber der Welt, unter Minigames bei -50). Alle Klaenge werden prozedural erzeugt
// (AudioClip.Create), damit die DLL klein bleibt: Wind, Grillen, Kauz, Regen, Donner, Feuerknistern
// im Wald; Raumton, Lueftung und Uhrticken im Museum.

using System;
using System.Collections.Generic;
using BepInEx.Unity.IL2CPP.Utils;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class AtlasWeatherFx
{
    private const int Rate = 22050;
    private static Transform _screen;
    private static SpriteRenderer _tint, _flash;
    private static readonly List<SpriteRenderer> Drops = new();
    private static readonly List<SpriteRenderer> Flames = new();
    private static AtlasWorld.Weather _weather;
    private static Color _tintNow = Color.clear;
    private static float _flashT;
    private static LineRenderer _bolt;
    private static float _boltT;
    private static readonly Dictionary<string, AudioClip> Clips = new();
    private static AudioSource _ambience, _rain, _fire;
    private static float _nextOneShot;
    private static bool _dropsPlaced;
    private static readonly List<(float At, float Vol)> ThunderQueue = new();

    public static void Reset()
    {
        _screen = null; _tint = _flash = null; _bolt = null; _dropsPlaced = false;
        Drops.Clear(); Flames.Clear(); ThunderQueue.Clear();
        _weather = AtlasWorld.Weather.Clear; _tintNow = Color.clear; _flashT = 0f; _boltT = 0f;
        StopLoop(ref _ambience); StopLoop(ref _rain); StopLoop(ref _fire);
    }

    public static void SetWeather(AtlasWorld.Weather w) => _weather = w;

    // ------------------------------------------------------------------ Bildschirm

    private static bool EnsureScreen()
    {
        if (_screen != null) return true;
        var cam = Camera.main;
        if (cam == null) return false;
        var go = new GameObject("Atlas_WeatherScreen") { layer = 5 };
        go.transform.SetParent(cam.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -30f);
        _screen = go.transform;
        _tint = Quad("tint", 0);
        _flash = Quad("flash", 2);
        for (int i = 0; i < 70; i++)
        {
            var d = new GameObject("drop") { layer = 5 };
            d.transform.SetParent(_screen, false);
            var sr = d.AddComponent<SpriteRenderer>();
            sr.sprite = AtlasAssets.TaskSprite("task_raindrop.png", 100f, new Vector2(0.5f, 0.5f));
            sr.color = new Color(0.75f, 0.85f, 1f, 0f);
            d.transform.localPosition = new Vector3(Random.Range(-7f, 7f), Random.Range(-4f, 4f), -0.01f);
            d.transform.localScale = Vector3.one * Random.Range(0.5f, 0.9f);
            d.transform.localEulerAngles = new Vector3(0f, 0f, 12f);
            Drops.Add(sr);
        }
        return true;
    }

    private static SpriteRenderer Quad(string name, int order)
    {
        var go = new GameObject(name) { layer = 5 };
        go.transform.SetParent(_screen, false);
        go.transform.localPosition = new Vector3(0f, 0f, -order * 0.01f);
        go.transform.localScale = new Vector3(30f / 0.16f, 20f / 0.16f, 1f);    // task_white = 16 px bei 100 ppu
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite("task_white.png", 100f, new Vector2(0.5f, 0.5f));
        sr.color = Color.clear;
        return sr;
    }

    public static void Strike(Vector2 p)
    {
        _flashT = 1f;
        var cam = Camera.main;
        var lp = PlayerControl.LocalPlayer;
        float dist = lp != null ? Vector2.Distance(lp.GetTruePosition(), p) : 10f;
        // Donner kommt mit der Entfernung spaeter und leiser (Schall: hier 1 m = 1 "Schritt" Verzoegerung)
        ThunderQueue.Add((Time.time + Mathf.Clamp(dist * 0.06f, 0.1f, 2.5f), Mathf.Lerp(0.9f, 0.35f, Mathf.Clamp01(dist / 30f))));
        if (cam == null || AtlasMuseumBuilder.D.Key != "wald") return;
        if (_bolt == null)
        {
            var go = new GameObject("Atlas_Bolt") { layer = 11 };
            go.transform.SetParent(ShipStatus.Instance.transform, false);
            _bolt = go.AddComponent<LineRenderer>();
            _bolt.useWorldSpace = true;
            _bolt.positionCount = 9;
            _bolt.sharedMaterial = new Material(Shader.Find("Sprites/Default")) { hideFlags = HideFlags.HideAndDontSave };
            _bolt.startWidth = 0.12f; _bolt.endWidth = 0.05f;
        }
        var top = p + new Vector2(Random.Range(-1.5f, 1.5f), 9f);
        for (int i = 0; i < 9; i++)
        {
            float k = i / 8f;
            var q = Vector2.Lerp(top, p, k) + (i > 0 && i < 8 ? new Vector2(Random.Range(-0.6f, 0.6f), 0f) : Vector2.zero);
            _bolt.SetPosition(i, new Vector3(q.x, q.y, -3f));
        }
        _boltT = 0.35f;
        _bolt.gameObject.SetActive(true);
        // Einschlagsstelle: kurzer Funkenregen
        for (int i = 0; i < 5; i++) SpawnSpark(p);
    }

    private static void SpawnSpark(Vector2 p)
    {
        var go = new GameObject("spark") { layer = 11 };
        go.transform.SetParent(ShipStatus.Instance.transform, false);
        go.transform.position = new Vector3(p.x + Random.Range(-0.4f, 0.4f), p.y + Random.Range(-0.2f, 0.4f), -2f);
        go.transform.localScale = Vector3.one * Random.Range(0.25f, 0.45f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite("task_flame.png", 100f, new Vector2(0.5f, 0.1f));
        Object.Destroy(go, Random.Range(0.4f, 0.9f));
    }

    // ------------------------------------------------------------------ Takt

    public static void Tick(float dt, bool wald)
    {
        if (!EnsureScreen()) return;
        var cam = Camera.main;
        // Kamera-Kind: lokale Einheiten koennen skaliert sein, also die Sichtflaeche in den lokalen Raum umrechnen
        float sc = Mathf.Max(0.01f, _screen.lossyScale.y);
        float halfH = (cam != null ? cam.orthographicSize : 3f) / sc, halfW = halfH * (cam != null ? cam.aspect : 1.78f);
        if (!_dropsPlaced)
        {
            _dropsPlaced = true;
            AtlasPlugin.Logger.LogInfo($"[Atlas/Fx] weather screen: ortho {(cam != null ? cam.orthographicSize : -1f):F2}, scale {sc:F3}");
            foreach (var d in Drops) d.transform.localPosition = new Vector3(Random.Range(-halfW, halfW), Random.Range(-halfH, halfH), -0.01f);
        }

        // Grundfarbe: Wald nachts leicht blau, Wetter legt nach
        Color want = wald ? new Color(0.02f, 0.04f, 0.12f, 0.12f) : Color.clear;
        if (wald)
            want = _weather switch
            {
                AtlasWorld.Weather.Rain => new Color(0.03f, 0.06f, 0.14f, 0.28f),
                AtlasWorld.Weather.Fog => new Color(0.72f, 0.76f, 0.82f, 0.30f),
                AtlasWorld.Weather.Storm => new Color(0.0f, 0.02f, 0.08f, 0.40f),
                _ => want,
            };
        _tintNow = Color.Lerp(_tintNow, want, Mathf.Clamp01(dt * 0.6f));
        _tint.color = _tintNow;

        // Blitz: zweimaliges Flackern
        if (_flashT > 0f)
        {
            _flashT = Mathf.Max(0f, _flashT - dt * 2.2f);
            float f = _flashT > 0.75f ? 0.85f : _flashT > 0.6f ? 0.1f : _flashT * 0.9f;
            _flash.color = new Color(0.9f, 0.95f, 1f, f);
        }
        else _flash.color = Color.clear;
        if (_bolt != null && _boltT > 0f)
        {
            _boltT -= dt;
            float a = Mathf.Clamp01(_boltT / 0.35f);
            _bolt.startColor = _bolt.endColor = new Color(0.85f, 0.9f, 1f, a);
            if (_boltT <= 0f) _bolt.gameObject.SetActive(false);
        }

        // Regen (Regen und Sturm; Sturm schraeger und dichter)
        bool raining = wald && (_weather == AtlasWorld.Weather.Rain || _weather == AtlasWorld.Weather.Storm);
        float slant = _weather == AtlasWorld.Weather.Storm ? 4f : 1.8f;
        int visible = raining ? (_weather == AtlasWorld.Weather.Storm ? Drops.Count : Drops.Count * 2 / 3) : 0;
        for (int i = 0; i < Drops.Count; i++)
        {
            var d = Drops[i];
            var c = d.color;
            float target = i < visible ? 0.55f : 0f;
            c.a = Mathf.MoveTowards(c.a, target, dt * 0.8f);
            d.color = c;
            if (c.a <= 0.001f) continue;
            var p = d.transform.localPosition;
            p += new Vector3(-slant * dt, -14f * dt, 0f);
            if (p.y < -halfH - 0.5f) { p.y += halfH * 2f + 1f + Random.Range(0f, 0.8f); p.x = Random.Range(-halfW - 1f, halfW + 3f); }
            if (p.x < -halfW - 1f) p.x += halfW * 2f + 2f;
            d.transform.localPosition = p;
            d.transform.localEulerAngles = new Vector3(0f, 0f, Mathf.Atan2(slant, 14f) * Mathf.Rad2Deg);
        }

        FireTick(dt, wald);
        AudioTick(dt, wald, raining);
    }

    // ------------------------------------------------------------------ Waldbrand

    private static void FireTick(float dt, bool wald)
    {
        var reactor = SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor);
        bool burning = wald && reactor != null && reactor.IsActive;
        if (burning && Flames.Count == 0)
        {
            foreach (var r in AtlasMuseumBuilder.D.Rooms)
            {
                if (r.Room != SystemTypes.Reactor) continue;
                float x0 = float.MaxValue, y0 = float.MaxValue, x1 = float.MinValue, y1 = float.MinValue;
                foreach (var q in r.Area) { x0 = Mathf.Min(x0, q.x); y0 = Mathf.Min(y0, q.y); x1 = Mathf.Max(x1, q.x); y1 = Mathf.Max(y1, q.y); }
                for (int i = 0; i < 16; i++)
                {
                    var p = new Vector2(Random.Range(x0 + 0.5f, x1 - 0.5f), Random.Range(y0 + 0.5f, y1 - 0.5f));
                    var go = new GameObject("Atlas_Fire") { layer = 11 };
                    go.transform.SetParent(ShipStatus.Instance.transform, false);
                    go.transform.position = new Vector3(p.x, p.y, (p.y + 0.36f) / 1000f - 0.003f);
                    go.transform.localScale = Vector3.one * Random.Range(0.4f, 0.8f);
                    var sr = go.AddComponent<SpriteRenderer>();
                    sr.sprite = AtlasAssets.TaskSprite("task_flame.png", 100f, new Vector2(0.5f, 0.1f));
                    Flames.Add(sr);
                }
            }
        }
        else if (!burning && Flames.Count > 0)
        {
            foreach (var f in Flames) if (f != null) Object.Destroy(f.gameObject);
            Flames.Clear();
        }
        for (int i = 0; i < Flames.Count; i++)
        {
            var f = Flames[i];
            if (f == null) continue;
            float k = Mathf.PerlinNoise(Time.time * 4f, i * 1.7f);
            // Regen daempft das Feuer sichtbar (und laesst dem Team mehr Zeit, siehe AtlasWorld)
            bool wet = _weather == AtlasWorld.Weather.Rain || _weather == AtlasWorld.Weather.Storm;
            f.color = new Color(1f, 0.75f + k * 0.25f, 0.5f, wet ? 0.55f + k * 0.2f : 0.85f + k * 0.15f);
            f.transform.localScale = new Vector3(1.1f + k * 0.4f, 1.0f + k * 0.8f, 1f) * (wet ? 0.8f : 1f);
            if (Random.value < dt * 0.6f) Smoke(f.transform.position);
        }
    }

    private static void Smoke(Vector3 at)
    {
        var go = new GameObject("smoke") { layer = 11 };
        go.transform.SetParent(ShipStatus.Instance.transform, false);
        go.transform.position = at + new Vector3(0f, 0.5f, -0.5f);
        go.transform.localScale = Vector3.one * 0.6f;
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite("task_steam.png", 100f, new Vector2(0.5f, 0.5f));
        sr.color = new Color(0.25f, 0.22f, 0.2f, 0.45f);
        ShipStatus.Instance.StartCoroutine(AtlasWorldFxRise(sr));
    }

    private static System.Collections.IEnumerator AtlasWorldFxRise(SpriteRenderer sr)
    {
        float t = 0f;
        var p0 = sr.transform.position;
        while (t < 2.5f && sr != null)
        {
            t += Time.deltaTime;
            float k = t / 2.5f;
            sr.transform.position = p0 + new Vector3(Mathf.Sin(t * 2f) * 0.15f, k * 1.8f, 0f);
            sr.transform.localScale = Vector3.one * (0.6f + k * 0.9f);
            sr.color = new Color(0.25f, 0.22f, 0.2f, 0.45f * (1f - k));
            yield return null;
        }
        if (sr != null) Object.Destroy(sr.gameObject);
    }

    // ------------------------------------------------------------------ Klang

    private static void AudioTick(float dt, bool wald, bool raining)
    {
        if (SoundManager.Instance == null) return;
        bool inGame = MeetingHud.Instance == null && ExileController.Instance == null;
        EnsureLoop(ref _ambience, wald ? "wald_bed" : "museum_bed", inGame ? (wald ? 0.35f : 0.28f) : 0f, dt);
        EnsureLoop(ref _rain, "rain", inGame && raining ? (_weather == AtlasWorld.Weather.Storm ? 0.55f : 0.4f) : 0f, dt);
        bool fire = Flames.Count > 0;
        float fireVol = 0f;
        if (fire && PlayerControl.LocalPlayer != null && Flames[0] != null)
            fireVol = Mathf.Lerp(0.45f, 0.05f, Mathf.Clamp01(Vector2.Distance(PlayerControl.LocalPlayer.GetTruePosition(), Flames[0].transform.position) / 18f));
        EnsureLoop(ref _fire, "fire", inGame ? fireVol : 0f, dt);

        for (int i = ThunderQueue.Count - 1; i >= 0; i--)
            if (Time.time >= ThunderQueue[i].At) { Play("thunder", ThunderQueue[i].Vol); ThunderQueue.RemoveAt(i); }

        // gelegentliche Einzelgeraeusche
        if (inGame && Time.time >= _nextOneShot)
        {
            _nextOneShot = Time.time + Random.Range(14f, 30f);
            if (wald && _weather != AtlasWorld.Weather.Storm) Play(Random.value < 0.6f ? "owl" : "twig", 0.3f);
            if (!wald) Play(Random.value < 0.5f ? "creak" : "clock", 0.22f);
        }
    }

    private static void EnsureLoop(ref AudioSource src, string clip, float vol, float dt)
    {
        try
        {
            if (src == null)
            {
                if (vol <= 0.001f) return;
                src = SoundManager.Instance.PlaySound(Clip(clip), true, 0f);
                if (src == null) return;
            }
            src.volume = Mathf.MoveTowards(src.volume, vol, dt * 0.35f);
        }
        catch { src = null; }
    }

    private static void StopLoop(ref AudioSource src)
    {
        try { if (src != null && SoundManager.Instance != null && src.clip != null) SoundManager.Instance.StopSound(src.clip); } catch { }
        src = null;
    }

    /// <summary>Einzelgeraeusch (auch fuer die Rauswurf-Szenen, AtlasEject).</summary>
    internal static void Sfx(string clip, float vol) => Play(clip, vol);

    private static void Play(string clip, float vol)
    {
        try { SoundManager.Instance.PlaySound(Clip(clip), false, vol); } catch { }
    }

    private static AudioClip Clip(string name)
    {
        if (Clips.TryGetValue(name, out var c) && c != null) return c;
        float[] s = name switch
        {
            "wald_bed" => WaldBed(),
            "museum_bed" => MuseumBed(),
            "rain" => Rain(),
            "fire" => Fire(),
            "thunder" => Thunder(),
            "owl" => Owl(),
            "twig" => Twig(),
            "creak" => Creak(),
            "whoosh" => Whoosh(),
            "thud" => Thud(),
            "splash" => Splash(),
            "slam" => Slam(),
            "roar" => Roar(),
            "grind" => Grind(),
            "growl" => Growl(),
            "rush" => Rush(),
            _ => Clock(),
        };
        c = AudioClip.Create("atlas_" + name, s.Length, 1, Rate, false);
        c.hideFlags |= HideFlags.HideAndDontSave;
        c.SetData(s, 0);
        Clips[name] = c;
        return c;
    }

    // --- Synthese (deterministisch, damit Schleifen nahtlos sind: Laenge = ganze Perioden)

    private static System.Random _rng = new(1234);
    private static float N() => (float)(_rng.NextDouble() * 2.0 - 1.0);

    /// <summary>Tiefpass-Rauschen; a = Glaettung (klein = dumpfer).</summary>
    private static float[] Brown(int n, float a, float gain)
    {
        var s = new float[n]; float y = 0f;
        for (int i = 0; i < n; i++) { y += a * (N() - y); s[i] = y * gain; }
        return s;
    }

    private static float[] Finish(float[] s, int fade)
    {
        for (int i = 0; i < fade; i++)
        {
            float k = (float)i / fade;
            s[i] = s[i] * k + s[s.Length - fade + i] * (1f - k);
        }
        var o = new float[s.Length - fade];
        Array.Copy(s, o, o.Length);
        return o;
    }

    private static float[] WaldBed()
    {
        int n = Rate * 12;
        var s = Brown(n, 0.02f, 3.0f);                                          // Wind
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            s[i] *= 0.55f + 0.45f * Mathf.Sin(t * 0.52f) * Mathf.Sin(t * 0.21f + 1f);   // Boeen
            // Grillen: 4,4 kHz-Zirpen, 3 Pulse, alle 0,8 s, zwei Tiere versetzt
            for (int k = 0; k < 2; k++)
            {
                float ph = (t + k * 0.37f) % 0.8f;
                if (ph < 0.18f && (ph % 0.06f) < 0.035f)
                    s[i] += Mathf.Sin(2f * Mathf.PI * (4400f + k * 350f) * t) * 0.05f * (k == 0 ? 1f : 0.6f);
            }
        }
        return Finish(s, Rate / 2);
    }

    private static float[] MuseumBed()
    {
        int n = Rate * 10;
        var s = Brown(n, 0.01f, 1.6f);                                          // Lueftung
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            s[i] += Mathf.Sin(2f * Mathf.PI * 50f * t) * 0.025f + Mathf.Sin(2f * Mathf.PI * 100f * t) * 0.012f;  // Netzbrummen
            float ph = t % 1f;                                                  // Wanduhr, 1 Hz
            if (ph < 0.012f) s[i] += Mathf.Sin(2f * Mathf.PI * 2600f * t) * 0.12f * (1f - ph / 0.012f);
        }
        return Finish(s, Rate / 2);
    }

    private static float[] Rain()
    {
        int n = Rate * 6;
        var s = Brown(n, 0.5f, 0.35f);
        for (int i = 0; i < n; i++) if (_rng.NextDouble() < 0.004) s[i] += N() * 0.5f;   // einzelne Tropfen
        return Finish(s, Rate / 3);
    }

    private static float[] Fire()
    {
        int n = Rate * 5;
        var s = Brown(n, 0.06f, 1.2f);
        for (int i = 0; i < n; i++)
            if (_rng.NextDouble() < 0.0015)
            {
                int len = 60 + _rng.Next(200);
                for (int j = 0; j < len && i + j < n; j++) s[i + j] += N() * 0.6f * (1f - (float)j / len);
            }
        return Finish(s, Rate / 3);
    }

    private static float[] Thunder()
    {
        int n = Rate * 4;
        var s = Brown(n, 0.015f, 6f);
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            float env = t < 0.05f ? t / 0.05f : Mathf.Exp(-(t - 0.05f) * 1.1f) * (0.7f + 0.3f * Mathf.Sin(t * 9f));
            s[i] = Mathf.Clamp(s[i] * env, -1f, 1f);
        }
        return s;
    }

    private static float[] Owl()
    {
        int n = (int)(Rate * 1.6f);
        var s = new float[n];
        void Hoot(float at, float len, float f)
        {
            for (int i = (int)(at * Rate); i < Mathf.Min(n, (int)((at + len) * Rate)); i++)
            {
                float t = i / (float)Rate - at, k = t / len;
                s[i] += Mathf.Sin(2f * Mathf.PI * f * (1f - 0.08f * k) * t) * Mathf.Sin(Mathf.PI * k) * 0.5f;
            }
        }
        Hoot(0f, 0.35f, 420f); Hoot(0.55f, 0.12f, 440f); Hoot(0.75f, 0.6f, 410f);
        return s;
    }

    private static float[] Twig()
    {
        int n = Rate / 3;
        var s = new float[n];
        for (int c = 0; c < 3; c++)
        {
            int at = c * Rate / 14;
            for (int j = 0; j < 400 && at + j < n; j++) s[at + j] += N() * (1f - j / 400f) * 0.6f;
        }
        return s;
    }

    private static float[] Creak()
    {
        int n = Rate;
        var s = new float[n];
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            float f = 90f + 40f * Mathf.Sin(t * 3f);
            float saw = (t * f) % 1f * 2f - 1f;
            s[i] = saw * 0.25f * Mathf.Sin(Mathf.PI * t);
        }
        return s;
    }

    private static float[] Whoosh()
    {
        int n = (int)(Rate * 0.7f);
        var s = new float[n]; float y = 0f;
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / n;
            float a = 0.02f + 0.25f * Mathf.Sin(Mathf.PI * t);        // Luftzug: Filter oeffnet und schliesst
            y += a * (N() - y);
            s[i] = y * 2.2f * Mathf.Sin(Mathf.PI * t);
        }
        return s;
    }

    private static float[] Thud()
    {
        int n = (int)(Rate * 0.6f);
        var s = Brown(n, 0.05f, 0.8f);
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            s[i] = (s[i] * 0.4f + Mathf.Sin(2f * Mathf.PI * (70f - 40f * t) * t)) * Mathf.Exp(-t * 9f) * 0.9f;
        }
        return s;
    }

    private static float[] Splash()
    {
        int n = Rate;
        var s = Brown(n, 0.35f, 0.9f);
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            s[i] *= Mathf.Exp(-t * 5f);
            if (_rng.NextDouble() < 0.0012) { float f = 600f + (float)_rng.NextDouble() * 900f;          // Blasen
                for (int j = 0; j < 500 && i + j < n; j++) s[i + j] += Mathf.Sin(2f * Mathf.PI * f * (1f + j / 900f) * j / Rate) * 0.12f * (1f - j / 500f); }
        }
        return s;
    }

    private static float[] Slam()
    {
        var s = Thud();
        for (int j = 0; j < 260; j++) s[j] += N() * 0.7f * (1f - j / 260f);
        return s;
    }

    private static float[] Roar()
    {
        int n = (int)(Rate * 1.6f);
        var s = Brown(n, 0.08f, 1.4f);
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            float f = 95f + 25f * Mathf.Sin(t * 3f) + 8f * Mathf.Sin(t * 37f);
            float saw = (t * f) % 1f * 2f - 1f;
            float env = Mathf.Clamp01(t / 0.15f) * Mathf.Clamp01((1.6f - t) / 0.6f);
            s[i] = Mathf.Clamp((saw * 0.55f + s[i] * 0.6f) * env, -1f, 1f);
        }
        return s;
    }

    private static float[] Grind()
    {
        int n = (int)(Rate * 0.9f);
        var s = Brown(n, 0.12f, 1.2f);
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            s[i] *= (0.6f + 0.4f * Mathf.Sin(t * 60f)) * Mathf.Sin(Mathf.PI * t / 0.9f);
        }
        return s;
    }

    private static float[] Growl()
    {
        int n = (int)(Rate * 1.2f);
        var s = new float[n];
        for (int i = 0; i < n; i++)
        {
            float t = (float)i / Rate;
            float f = 60f + 10f * Mathf.Sin(t * 5f);
            s[i] = (Mathf.Sin(2f * Mathf.PI * f * t) + 0.5f * Mathf.Sin(2f * Mathf.PI * f * 2.02f * t)) * 0.35f
                   * (0.6f + 0.4f * Mathf.Sin(t * 23f)) * Mathf.Sin(Mathf.PI * t / 1.2f);
        }
        return s;
    }

    private static float[] Rush()
    {
        var s = Brown(Rate * 4, 0.25f, 0.9f);
        for (int i = 0; i < s.Length; i++) s[i] *= Mathf.Clamp01(i / (float)Rate) * Mathf.Clamp01((s.Length - i) / (float)Rate);
        return s;
    }

    private static float[] Clock()
    {
        int n = Rate * 2;
        var s = new float[n];
        for (int c = 0; c < 2; c++)
            for (int j = 0; j < 300; j++) s[c * Rate + j] = Mathf.Sin(2f * Mathf.PI * (c == 0 ? 2600f : 2100f) * j / Rate) * (1f - j / 300f) * 0.5f;
        return s;
    }
}
