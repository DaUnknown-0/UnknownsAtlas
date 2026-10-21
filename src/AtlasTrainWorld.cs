// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasTrainWorld - Welt-Mechanik "train" (Polaris Express, User 19.10.: "der Hintergrund soll sich bewegen, man ist
// in einem fahrenden Zug"). Kartendatei: "world": "train".
//
// - Fahrt: die Landschaft (Kartendatei "scroll": nahtlose Streifen, unter dem Boden; die Bodenkacheln sind ausserhalb
//   des Zugs durchsichtig) laeuft nach Westen. Geschwindigkeit in m/s, normal Cruise; Blown Dynamo (Licht) bremst auf
//   SlowFactor, Runaway Train (AtlasRunaway) beschleunigt mit dem Ueberdruck. Weiche Uebergaenge, leichtes Rattern der
//   Kamera, bei hoher Fahrt Funken; alles nur Optik, der Bildlauf ist nicht synchronisiert (die Geschwindigkeit
//   leitet sich aus geteiltem Zustand ab und ist damit ueberall fast gleich).
// - Dachluken der Rauch-Sabotage (AtlasSmoke): Props "dachluke_zu"/"dachluke_auf" an derselben Stelle, je Zustand
//   eines sichtbar; Rauchwolken und Feuerschein waehrend der Sabotage.
// - Sichtfaktor: Rauch (AtlasSmoke.VisionFactor).

using System;
using System.Collections.Generic;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal sealed class AtlasTrainWorld : IAtlasMapWorld
{
    private const string LogPrefix = "[Atlas/Train]";
    public const float Cruise = 6.0f, SlowFactor = 0.22f, Accel = 1.6f, Brake = 3.0f;

    private static AtlasMapDef D => AtlasMuseumBuilder.D;
    /// <summary>Aktuelle Fahrgeschwindigkeit in m/s (fuer Anzeigen und Effekte).</summary>
    public static float Speed { get; private set; } = Cruise;
    public static float SpeedFactor => Speed / Cruise;

    private sealed class Layer
    {
        public float Width, Parallax;
        public readonly List<Transform> Copies = new();
        public float Offset;
    }

    private readonly List<Layer> _layers = new();
    private readonly List<Sprite> _sprites = new();   // the scroll sprites of this round, destroyed with it
    private Transform _root;
    private readonly List<SpriteRenderer> _hatchClosed = new(), _hatchOpen = new();
    private readonly List<(SpriteRenderer R, float Life, Vector2 V, float Spin)> _fx = new();
    private Sprite _smokeSprite, _sparkSprite, _fireSprite, _softSprite;
    private SpriteRenderer _fire;
    private float _fxNext;

    // ------------------------------------------------------------------ Bau

    public void OnBuilt(Transform worldRoot)
    {
        Speed = Cruise;
        _layers.Clear(); _fx.Clear(); _hatchClosed.Clear(); _hatchOpen.Clear();
        var go = new GameObject("Atlas_Train") { layer = AtlasMuseumBuilder.LayerShip };
        go.transform.SetParent(worldRoot, false);
        _root = go.transform;
        BuildScroll();
        FindHatches();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: {_layers.Count} scroll layer(s), {_hatchClosed.Count} hatch prop(s)");
    }

    private void BuildScroll()
    {
        if (D == null || D.Scroll == null) return;
        float mapW = D.MaxX - D.MinX;
        foreach (var s in D.Scroll)
        {
            var tex = AtlasAssets.MapFileTexture(D, s.File);
            if (tex == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} scroll layer missing: {s.File}"); continue; }
            tex.wrapMode = TextureWrapMode.Clamp;
            float ppm = s.Ppm > 1f ? s.Ppm : 128f;
            float width = s.WidthM > 0.5f ? s.WidthM : tex.width / ppm;
            var sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), Vector2.zero, ppm, 0, SpriteMeshType.FullRect);
            sprite.hideFlags |= HideFlags.HideAndDontSave;
            _sprites.Add(sprite);
            var layer = new Layer { Width = width, Parallax = s.Parallax > 0f ? s.Parallax : 1f };
            int n = Mathf.CeilToInt(mapW / width) + 2;
            for (int i = 0; i < n; i++)
            {
                var c = new GameObject($"Scroll_{s.File}_{i}") { layer = AtlasMuseumBuilder.LayerShip };
                c.transform.SetParent(_root, false);
                var sr = c.AddComponent<SpriteRenderer>();
                sr.sprite = sprite;
                sr.sortingOrder = -1100 + _layers.Count;                      // spaetere Ebene (fern, nur Randbaender) ueber der naheren
                AtlasMuseumBuilder.Mask(sr);
                // hinter dem Boden (groesseres z = weiter hinten); Ebenen in Listenreihenfolge, die spaetere vorn
                c.transform.localPosition = new Vector3(D.MinX - width + i * width, s.Y0, AtlasMuseumBuilder.FloorZ + 0.4f - _layers.Count * 0.05f);
                layer.Copies.Add(c.transform);
            }
            _layers.Add(layer);
        }
    }

    private void FindHatches()
    {
        var ship = ShipStatus.Instance;
        if (ship == null) return;
        foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
        {
            if (sr == null) continue;
            string n = sr.name;
            if (n.StartsWith("Prop_dachluke_zu_", StringComparison.Ordinal)) _hatchClosed.Add(sr);
            else if (n.StartsWith("Prop_dachluke_auf_", StringComparison.Ordinal)) { _hatchOpen.Add(sr); sr.gameObject.SetActive(false); }
        }
        // Reihenfolge nach x, damit Index i zur Luke i der Kartendatei passt
        _hatchClosed.Sort((a, b) => a.transform.position.x.CompareTo(b.transform.position.x));
        _hatchOpen.Sort((a, b) => a.transform.position.x.CompareTo(b.transform.position.x));
    }

    // ------------------------------------------------------------------ Takt

    public void Tick(float dt)
    {
        SpeedTick(dt);
        ScrollTick(dt);
        ShakeTick();
        HatchTick();
        FxTick(dt);
    }

    private void SpeedTick(float dt)
    {
        float target = Cruise;
        if (AtlasRunaway.Active) target = Cruise * AtlasRunaway.SpeedFactor;
        else if (AtlasWorld.LightsOut()) target = Cruise * SlowFactor;
        bool meeting = MeetingHud.Instance != null || ExileController.Instance != null;
        if (meeting) target = Mathf.Min(target, Cruise);
        float rate = target > Speed ? Accel : Brake;
        Speed = Mathf.MoveTowards(Speed, target, rate * dt);
    }

    private void ScrollTick(float dt)
    {
        if (D == null) return;
        foreach (var l in _layers)
        {
            l.Offset = Mathf.Repeat(l.Offset + Speed * l.Parallax * dt, l.Width);
            for (int i = 0; i < l.Copies.Count; i++)
            {
                var t = l.Copies[i];
                if (t == null) continue;
                var p = t.localPosition;
                t.localPosition = new Vector3(D.MinX - l.Width - l.Offset + i * l.Width, p.y, p.z);
            }
        }
    }

    private void ShakeTick()
    {
        var cam = HudManager.InstanceExists ? HudManager.Instance.PlayerCam : null;
        if (cam == null || MeetingHud.Instance != null) return;
        // leichtes Rattern, waechst mit der Fahrt; steht der Zug fast, ist Ruhe
        float f = SpeedFactor;
        float amount = f < 0.4f ? 0f : 0.006f + 0.03f * Mathf.Clamp01((f - 0.4f) / 2.0f);
        cam.shakeAmount = amount;
        cam.shakePeriod = 25f + 20f * Mathf.Clamp01(f - 1f);
    }

    private void HatchTick()
    {
        for (int i = 0; i < _hatchClosed.Count; i++)
        {
            bool open = AtlasSmoke.Active ? AtlasSmoke.IsOpen(i) : false;
            var c = _hatchClosed[i];
            var o = i < _hatchOpen.Count ? _hatchOpen[i] : null;
            if (c != null && c.gameObject.activeSelf == open) c.gameObject.SetActive(!open);
            if (o != null && o.gameObject.activeSelf != open) o.gameObject.SetActive(open);
        }
    }

    // ------------------------------------------------------------------ Effekte (Funken, Rauch, Feuerschein)

    private Sprite Soft()
    {
        if (_softSprite != null) return _softSprite;
        const int N = 64;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Bilinear };
        var px = new Color32[N * N];
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float u = (x + 0.5f) / N * 2f - 1f, v = (y + 0.5f) / N * 2f - 1f;
                float d = Mathf.Sqrt(u * u + v * v);
                float a = Mathf.Clamp01(1f - d); a *= a;
                px[y * N + x] = new Color32(255, 255, 255, (byte)(a * 255f));
            }
        tex.SetPixels32(px); tex.Apply(false, true);
        _softSprite = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), N);
        _softSprite.hideFlags = HideFlags.HideAndDontSave;
        return _softSprite;
    }

    /// <summary>Erstes Teilbild einer Effektgrafik des Kartenpakets (Zeile mit frames Bildern) oder der weiche Punkt.</summary>
    private Sprite FxSprite(ref Sprite cache, string file, int frames, out int count)
    {
        count = 1;
        if (cache != null) { count = frames; return cache; }
        var tex = D != null && AtlasAssets.MapFileExists(D, file) ? AtlasAssets.MapFileTexture(D, file) : null;
        if (tex == null) return Soft();
        int w = tex.width / Mathf.Max(1, frames);
        cache = Sprite.Create(tex, new Rect(0, 0, w, tex.height), new Vector2(0.5f, 0.5f), Mathf.Max(1f, w / 1.0f));
        cache.hideFlags |= HideFlags.HideAndDontSave;
        count = frames;
        return cache;
    }

    private void Spawn(Sprite sprite, Vector2 at, Vector2 v, float size, Color col, float life, float spin)
    {
        if (_root == null || _fx.Count > 60) return;
        var go = new GameObject("fx") { layer = AtlasMuseumBuilder.LayerShip };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(at.x, at.y, AtlasMuseumBuilder.SortZ(at.y - 1.5f));
        go.transform.localScale = Vector3.one * size;
        go.transform.localRotation = Quaternion.Euler(0f, 0f, Random.Range(0f, 360f));
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite; sr.color = col; sr.sortingOrder = 50;
        _fx.Add((sr, life, v, spin));
    }

    private void FxTick(float dt)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || D == null) return;
        var me = lp.GetTruePosition();
        float now = Time.time;
        if (now >= _fxNext)
        {
            _fxNext = now + 0.12f;
            // Funken bei hoher Fahrt: am Gleisbett nahe dem Spieler, fliegen nach Westen
            if (AtlasRunaway.Active && SpeedFactor > 1.15f && Random.value < Mathf.Clamp01((SpeedFactor - 1.1f) * 1.2f))
            {
                var sp = FxSprite(ref _sparkSprite, "train_fx_spark.png", 4, out _);
                float x = me.x + Random.Range(-6f, 6f);
                float y = Random.value < 0.5f ? 0.2f : 6.3f;
                Spawn(sp, new Vector2(x, y), new Vector2(-Speed * 0.6f, Random.Range(0.6f, 1.6f) * (y < 3f ? -1f : 1f)),
                      Random.Range(0.35f, 0.7f), new Color(1f, 0.75f, 0.35f, 0.95f), Random.Range(0.35f, 0.7f), Random.Range(-300f, 300f));
            }
            // Rauch: aus dem Tender (Quelle) und entlang der Wagen, dichter mit der Rauchdichte
            if (AtlasSmoke.Active && AtlasSmoke.Density > 0.05f)
            {
                var sm = FxSprite(ref _smokeSprite, "train_fx_smoke.png", 4, out _);
                var src = D.SmokeSource;
                Spawn(sm, src + new Vector2(Random.Range(-0.6f, 0.6f), Random.Range(-0.4f, 0.4f)), new Vector2(Random.Range(-0.5f, 0.1f), Random.Range(0.15f, 0.45f)),
                      Random.Range(0.8f, 1.4f), new Color(0.55f, 0.55f, 0.58f, 0.55f * AtlasSmoke.Density), Random.Range(2.5f, 4f), Random.Range(-25f, 25f));
                if (Random.value < AtlasSmoke.Density)
                {
                    float x = me.x + Random.Range(-7f, 7f);
                    float y = me.y + Random.Range(-2.5f, 2.5f);
                    Spawn(sm, new Vector2(x, y), new Vector2(Random.Range(-0.4f, 0.4f), Random.Range(0.05f, 0.3f)),
                          Random.Range(1.0f, 1.8f), new Color(0.6f, 0.6f, 0.63f, 0.35f * AtlasSmoke.Density), Random.Range(3f, 5f), Random.Range(-15f, 15f));
                }
            }
        }
        // Feuerschein an der Quelle
        bool fire = AtlasSmoke.Active;
        if (fire && _fire == null)
        {
            var go = new GameObject("fire") { layer = AtlasMuseumBuilder.LayerShip };
            go.transform.SetParent(_root, false);
            go.transform.position = new Vector3(D.SmokeSource.x, D.SmokeSource.y, AtlasMuseumBuilder.SortZ(D.SmokeSource.y - 0.2f));
            _fire = go.AddComponent<SpriteRenderer>();
            _fire.sprite = FxSprite(ref _fireSprite, "train_fx_fire.png", 1, out _);
            _fire.sortingOrder = 40;
        }
        if (_fire != null)
        {
            if (_fire.gameObject.activeSelf != fire) _fire.gameObject.SetActive(fire);
            if (fire)
            {
                float fl = 0.85f + 0.15f * Mathf.Sin(now * 13f) * Mathf.Sin(now * 7.3f);
                _fire.color = new Color(1f, 0.6f, 0.25f, 0.8f * fl);
                _fire.transform.localScale = Vector3.one * (1.6f + 0.2f * fl);
            }
        }
        for (int i = _fx.Count - 1; i >= 0; i--)
        {
            var (r, life, v, spin) = _fx[i];
            life -= dt;
            if (r == null || life <= 0f) { if (r != null) Object.Destroy(r.gameObject); _fx.RemoveAt(i); continue; }
            var p = r.transform.position;
            r.transform.position = new Vector3(p.x + v.x * dt, p.y + v.y * dt, p.z);
            r.transform.Rotate(0f, 0f, spin * dt);
            var c = r.color; c.a = Mathf.Min(c.a, life); r.color = c;
            r.transform.localScale += Vector3.one * dt * 0.25f;
            _fx[i] = (r, life, v, spin);
        }
    }

    public float VisionFactor(Vector2 pos) => AtlasSmoke.VisionFactor;

    public void OnDestroy()
    {
        foreach (var (r, _, _, _) in _fx) if (r != null) Object.Destroy(r.gameObject);
        _fx.Clear(); _layers.Clear(); _hatchClosed.Clear(); _hatchOpen.Clear();
        // a new sprite per round, never freed before (audit 21.10.); the texture stays with the map pack
        foreach (var sp in _sprites) if (sp != null) Object.Destroy(sp);
        _sprites.Clear();
        _fire = null; _root = null;
        var cam = HudManager.InstanceExists ? HudManager.Instance.PlayerCam : null;
        if (cam != null) cam.shakeAmount = 0f;
        Speed = Cruise;
    }

    public static string DiagState() => $"train speed {Speed:F1} m/s";
}
