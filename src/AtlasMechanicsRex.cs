// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Die beiden Stationen der Museum-Sabotage "Rex erwacht" (AtlasRex):
//
//   rexmusic  Spieluhr (Rotunde): Kurbel im Uhrzeigersinn drehen; das Wiegenlied spielt genau so
//             schnell, wie man kurbelt. Zaehlt bei 0,75 bis 1,35 Umdrehungen pro Sekunde.
//   rexlight  Nachtlicht (Security Office): Sternenprojektor drehen, bis die Sterne in den Ringen
//             liegen (hoechstens 9 Grad daneben). Die Ringe wandern, weil der Rex sich waelzt; daneben
//             laeuft das Kamerabild K1 der Rotunde mit.
//
// Beide melden nur "im Takt an/aus" (AtlasRex.SetInput); was daraus wird, rechnet der Host. Fehlbedienung
// schadet nie (User 25.09.: Impostor sollen hier nur helfen koennen). Die Minispiele schliessen ohne
// Task-Schritt (Leave), sobald der Rex schlaeft oder die Sabotage anders endet.

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class RexKit
{
    /// <summary>Schlafbalken mit Countdown unten im Minispiel.</summary>
    public static (SpriteRenderer Fill, TextMeshPro Text) SleepBar(Transform root)
    {
        MatchKit.Box(root, new Vector2(0f, -2.05f), new Vector2(6.1f, 0.34f), new Color(0.05f, 0.06f, 0.09f, 0.95f), 6);
        var fill = MatchKit.Box(root, new Vector2(-3.0f, -2.05f), new Vector2(0.01f, 0.24f), new Color(0.45f, 0.75f, 0.95f), 7);
        var text = MatchKit.Text(root, new Vector2(0f, -2.04f), "", 1.35f, Color.white, 8);
        return (fill, text);
    }

    public static void UpdateBar((SpriteRenderer Fill, TextMeshPro Text) bar)
    {
        float w = Mathf.Max(0.01f, 6.0f * Mathf.Clamp01(AtlasRex.Sleep / 100f));
        bar.Fill.transform.localScale = new Vector3(w / 0.16f, 0.24f / 0.16f, 1f);
        var p = bar.Fill.transform.localPosition;
        bar.Fill.transform.localPosition = new Vector3(-3.0f + w / 2f, p.y, p.z);
        bar.Text.text = $"REX ASLEEP {Mathf.FloorToInt(AtlasRex.Sleep)}%     {Mathf.CeilToInt(AtlasRex.TimeLeft)}s";
    }

    /// <summary>Bogen als Linienzug (Winkel in Grad, gegen den Uhrzeigersinn).</summary>
    public static LineRenderer Arc(Transform root, Vector2 c, float r, float a0, float a1, Color col, float width, int order)
    {
        int n = Mathf.Max(8, Mathf.CeilToInt(Mathf.Abs(a1 - a0) / 7.5f));
        var lr = MatchKit.Line(root, col, width, order, n + 1);
        for (int i = 0; i <= n; i++)
        {
            float a = Mathf.Lerp(a0, a1, i / (float)n) * Mathf.Deg2Rad;
            MatchKit.Set(lr, i, c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r, order);
        }
        return lr;
    }
}

// ================================================================== Spieluhr

internal sealed class MusicBoxMechanic : IAtlasMechanic
{
    public string Name => "rexmusic";
    static readonly Vector2 C = new(1.85f, -0.55f);           // Kurbelachse
    const float Arm = 0.95f;
    static readonly Vector2 G = new(-0.95f, 0.95f);          // Tempoanzeige
    const float GaugeR = 0.7f, GaugeMax = 2f;
    static readonly Vector2 Box = new(-0.95f, -0.55f);

    private float _ang = 90f, _omega, _last, _stun, _grace, _noteAcc;
    private bool _grab;
    private int _seenRoars;
    private LineRenderer _arm, _needle;
    private Transform _knob;
    private readonly List<(SpriteRenderer R, int Col, int Row)> _pins = new();
    private readonly List<(SpriteRenderer R, float Life)> _sparks = new();
    private TextMeshPro _msg;
    private (SpriteRenderer, TextMeshPro) _bar;
    private Transform _root;
    private float _st;
    public float Progress => AtlasRex.Sleep / 100f;
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _root = root;
        AtlasRex.LocalCranking = true;
        _seenRoars = AtlasRex.Roars;
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        MatchKit.Text(root, new Vector2(0.9f, 1.95f), "WIND THE MUSIC BOX", 2.1f, Color.white, 6);
        // Kasten: Holz, dunkles Fenster, Kamm und Walze
        MatchKit.Box(root, Box, new Vector2(3.7f, 2.0f), new Color(0.07f, 0.05f, 0.04f), 1);
        MatchKit.Box(root, Box, new Vector2(3.55f, 1.85f), new Color(0.45f, 0.27f, 0.15f), 2);
        MatchKit.Box(root, Box + new Vector2(0f, 0.05f), new Vector2(3.0f, 1.25f), new Color(0.1f, 0.07f, 0.05f), 3);
        MatchKit.Box(root, Box + new Vector2(0f, 0.5f), new Vector2(2.8f, 0.09f), new Color(0.72f, 0.76f, 0.8f), 5);
        for (int i = 0; i < 18; i++)
            MatchKit.Box(root, Box + new Vector2(-1.3f + i * 0.153f, 0.36f - (i % 4) * 0.015f), new Vector2(0.07f, 0.25f - (i % 4) * 0.03f), new Color(0.8f, 0.84f, 0.88f), 5);
        MatchKit.Box(root, Box + new Vector2(0f, -0.2f), new Vector2(2.85f, 0.6f), new Color(0.35f, 0.26f, 0.08f), 3);
        MatchKit.Box(root, Box + new Vector2(0f, -0.2f), new Vector2(2.75f, 0.5f), new Color(0.86f, 0.67f, 0.3f), 4);
        for (int col = 0; col < 18; col++)
            for (int row = 0; row < 3; row++)
                _pins.Add((MatchKit.Symbol(root, Vector2.zero, 2, 0.07f, new Color(0.35f, 0.25f, 0.05f), 5), col, row));
        // Achse durch die Seitenwand, Fuehrungskreis, Richtungspfeil
        MatchKit.Box(root, new Vector2((Box.x + 1.78f + C.x) / 2f, C.y), new Vector2(C.x - Box.x - 1.78f, 0.14f), new Color(0.62f, 0.5f, 0.22f), 3);
        var guide = RexKit.Arc(root, C, Arm, 0f, 360f, new Color(1f, 1f, 1f, 0.18f), 0.03f, 3);
        guide.loop = true;
        var arrow = MatchKit.Symbol(root, C + new Vector2(0f, Arm + 0.28f), 0, 0.28f, new Color(1f, 1f, 1f, 0.55f), 3);
        arrow.transform.localEulerAngles = new Vector3(0, 0, -90f);                   // oben nach rechts = im Uhrzeigersinn
        _arm = MatchKit.Line(root, new Color(0.85f, 0.68f, 0.32f), 0.16f, 6);
        MatchKit.Symbol(root, C, 2, 0.34f, new Color(0.72f, 0.56f, 0.24f), 7);
        _knob = MatchKit.Symbol(root, Vector2.zero, 2, 0.5f, new Color(0.95f, 0.78f, 0.38f), 8).transform;
        MatchKit.Symbol(root, Vector2.zero, 2, 0.2f, new Color(1f, 0.93f, 0.7f), 9).transform.SetParent(_knob, true);
        // Tempoanzeige: grauer, gruener, roter Bereich
        float A(float w) => 180f - Mathf.Clamp(w, 0f, GaugeMax) / GaugeMax * 180f;
        RexKit.Arc(root, G, GaugeR, A(0f), A(AtlasRex.CrankMin), new Color(0.35f, 0.38f, 0.45f), 0.14f, 4);
        RexKit.Arc(root, G, GaugeR, A(AtlasRex.CrankMin), A(AtlasRex.CrankMax), new Color(0.43f, 0.81f, 0.49f), 0.14f, 4);
        RexKit.Arc(root, G, GaugeR, A(AtlasRex.CrankMax), A(GaugeMax), new Color(0.9f, 0.3f, 0.25f), 0.14f, 4);
        _needle = MatchKit.Line(root, new Color(0.96f, 0.94f, 0.89f), 0.06f, 6);
        MatchKit.Symbol(root, G, 2, 0.16f, new Color(0.88f, 0.7f, 0.3f), 7);
        MatchKit.Text(root, G + new Vector2(0f, -0.2f), "TEMPO", 1.1f, new Color(0.8f, 0.8f, 0.85f), 6);
        _msg = MatchKit.Text(root, new Vector2(1.85f, 1.25f), "", 1.8f, Color.white, 6);
        _bar = RexKit.SleepBar(root);
        Apply();
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!AtlasRex.Active && AtlasMinigame.DiagStep < 0) { AtlasRex.SetInput(AtlasRex.Music, false); Leave = true; return; }
        // Bruellen: die Kurbel schlaegt zurueck, kurz nicht zu fassen
        if (AtlasRex.Roars != _seenRoars) { _seenRoars = AtlasRex.Roars; _omega = -0.45f; _ang += 70f; _stun = 0.35f; }
        _stun = Mathf.Max(0f, _stun - dt);
        var d = mouse - C;
        float dist = d.magnitude;
        if (pressed && dist > 0.15f && dist < 1.5f) { _grab = true; _last = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg; }
        if (!down) _grab = false;
        if (_grab)
        {
            float a = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg;
            float delta = Mathf.DeltaAngle(_last, a);
            _last = a;
            if (_stun <= 0f)
            {
                _ang += delta;
                float inst = -delta / 360f / Mathf.Max(dt, 0.001f);              // im Uhrzeigersinn = positiv
                _omega += (inst - _omega) * (1f - Mathf.Exp(-dt / 0.28f));
            }
        }
        if (!_grab || _stun > 0f)
        {
            _omega *= Mathf.Exp(-1.6f * dt);
            _ang -= _omega * 360f * dt;
        }
        bool inZone = _omega >= AtlasRex.CrankMin && _omega <= AtlasRex.CrankMax;
        _grace = inZone ? 0.25f : _grace - dt;
        AtlasRex.SetInput(AtlasRex.Music, _grace > 0f);
        // Wiegenlied: drei Noten je Umdrehung, zu schnell klingt schrill
        if (_omega > 0.05f)
        {
            _noteAcc += _omega * dt * 3f;
            while (_noteAcc >= 1f)
            {
                _noteAcc -= 1f;
                float pitch = _omega > AtlasRex.CrankMax ? 1f + (_omega - AtlasRex.CrankMax) * 0.35f
                            : _omega < AtlasRex.CrankMin ? 1f - (AtlasRex.CrankMin - _omega) * 0.12f : 1f;
                AtlasRex.PlayNextNote(0.55f, pitch);
                var s = MatchKit.Symbol(_root, Box + new Vector2(Random.Range(-1.2f, 1.2f), 0.55f), 2, 0.12f,
                                        inZone ? new Color(1f, 0.85f, 0.45f) : new Color(0.7f, 0.72f, 0.78f), 9);
                _sparks.Add((s, 1f));
            }
        }
        for (int i = _sparks.Count - 1; i >= 0; i--)
        {
            var (r, life) = _sparks[i];
            life -= dt * 0.9f;
            if (life <= 0f || r == null) { if (r != null) Object.Destroy(r.gameObject); _sparks.RemoveAt(i); continue; }
            var p = r.transform.localPosition;
            r.transform.localPosition = new Vector3(p.x + Mathf.Sin(life * 9f) * 0.004f, p.y + dt * 0.8f, p.z);
            var c = r.color; c.a = life; r.color = c;
            _sparks[i] = (r, life);
        }
        _msg.text = _stun > 0f ? "THE REX SHAKES IT!" : _omega < 0.05f ? "KEEP WINDING" : _omega < AtlasRex.CrankMin ? "FASTER"
                  : _omega > AtlasRex.CrankMax ? "TOO FAST" : "IN TIME";
        _msg.color = inZone ? new Color(0.5f, 1f, 0.6f) : _stun > 0f ? new Color(1f, 0.55f, 0.5f) : new Color(1f, 0.75f, 0.35f);
        Apply();
    }

    private void Apply()
    {
        float a = _ang * Mathf.Deg2Rad;
        var k = C + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Arm;
        MatchKit.Set(_arm, 0, C, 6);
        MatchKit.Set(_arm, 1, k, 6);
        _knob.localPosition = new Vector3(k.x, k.y, -0.08f);
        float na = (180f - Mathf.Clamp(_omega, 0f, GaugeMax) / GaugeMax * 180f) * Mathf.Deg2Rad;
        MatchKit.Set(_needle, 0, G, 6);
        MatchKit.Set(_needle, 1, G + new Vector2(Mathf.Cos(na), Mathf.Sin(na)) * (GaugeR - 0.05f), 6);
        // Walze dreht mit: Stifte laufen von oben nach unten durch
        float phase = -_ang / 360f;
        foreach (var (r, col, row) in _pins)
        {
            float y = Mathf.Repeat(row / 3f + phase + col * 0.137f, 1f);
            r.transform.localPosition = new Vector3(Box.x - 1.3f + col * 0.153f, Box.y - 0.2f + (y - 0.5f) * 0.44f, r.transform.localPosition.z);
            var c = r.color; c.a = y < 0.08f || y > 0.92f ? 0f : 1f; r.color = c;
        }
        RexKit.UpdateBar(_bar);
    }

    // Autotest: am Griff fassen und gleichmaessig im Wiegenlied-Tempo kurbeln
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float a = (90f - _st * 1.05f * 360f) * Mathf.Deg2Rad;
        mouse = C + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Arm;
        down = _st > 0.05f;
    }

    public void Dispose()
    {
        AtlasRex.SetInput(AtlasRex.Music, false);
        AtlasRex.LocalCranking = false;
    }
}

// ================================================================== Nachtlicht (Sternenprojektor)

internal sealed class NightLightMechanic : IAtlasMechanic
{
    public string Name => "rexlight";
    static readonly Vector2 Sky = new(-1.0f, 0.05f);
    const float SkyR = 1.85f;
    static readonly Vector2 Cam = new(2.05f, 0.55f);
    static readonly Vector2 CamSize = new(2.3f, 1.55f);
    // das Sternbild "Schlafender Rex" (Kopf links, Ruecken, Schwanz)
    static readonly Vector2[] Stars = { new(-1.15f, 0.35f), new(-0.7f, 0.6f), new(-0.2f, 0.5f), new(0.3f, 0.65f), new(0.8f, 0.4f), new(1.2f, 0.05f), new(0.35f, -0.25f) };
    static readonly int[] Links = { 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 3, 6 };

    private float _rot, _target, _tv, _grace;
    private int _seenRoars;
    private readonly List<Transform> _rings = new(), _stars = new();
    private readonly List<LineRenderer> _targetLines = new(), _starLines = new();
    private Rotary _drag;
    private TextMeshPro _msg, _dev;
    private (SpriteRenderer, TextMeshPro) _bar;
    private GameObject _camGo;
    private RenderTexture _rt;
    private Material _camMat;
    private float _simA = 90f;
    public float Progress => AtlasRex.Sleep / 100f;
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _seenRoars = AtlasRex.Roars;
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        MatchKit.Text(root, new Vector2(0f, 2.0f), "ALIGN THE NIGHT LIGHT", 2.1f, Color.white, 6);
        AtlasTaskKit.Sprite(root, "task_sky.png", 100f, Sky, 1).transform.localScale = Vector3.one * (SkyR * 2f / 4.4f);
        _target = Random.Range(-40f, 40f);
        _rot = _target + (Random.value < 0.5f ? -1f : 1f) * Random.Range(35f, 60f);
        for (int i = 0; i < Links.Length; i += 2)
        {
            _targetLines.Add(MatchKit.Line(root, new Color(0.56f, 0.79f, 0.86f, 0.35f), 0.03f, 2));
            _starLines.Add(MatchKit.Line(root, new Color(1f, 0.92f, 0.62f, 0.3f), 0.04f, 4));
        }
        foreach (var _ in Stars)
        {
            var ring = MatchKit.Symbol(root, Vector2.zero, 2, 0.36f, new Color(0.56f, 0.79f, 0.86f, 0.75f), 2).transform;
            MatchKit.Symbol(root, Vector2.zero, 2, 0.27f, new Color(0.07f, 0.1f, 0.2f, 1f), 3).transform.SetParent(ring, true);
            _rings.Add(ring);
            var st = AtlasTaskKit.Sprite(root, "task_star.png", 100f, Vector2.zero, 5).transform;
            st.localScale = Vector3.one * 0.42f;
            _stars.Add(st);
        }
        _drag = new Rotary(Sky, 0.1f, SkyR + 0.4f);
        // Kamerabild K1 (User 25.09.: "kleines Bild"): eine zweite Kamera rendert die Rotunde in eine Textur
        MatchKit.Box(root, Cam, CamSize + new Vector2(0.14f, 0.14f), new Color(0.04f, 0.05f, 0.06f), 2);
        MatchKit.Text(root, Cam + new Vector2(0f, CamSize.y / 2f + 0.2f), "CAM K1  ROTUNDA", 1.2f, new Color(0.75f, 0.85f, 0.8f), 6);
        BuildCamera(root);
        _dev = MatchKit.Text(root, Cam + new Vector2(0f, -1.25f), "", 1.7f, Color.white, 6);
        _msg = MatchKit.Text(root, Cam + new Vector2(0f, -1.7f), "", 1.5f, Color.white, 6);
        _bar = RexKit.SleepBar(root);
        Apply();
    }

    private void BuildCamera(Transform root)
    {
        try
        {
            var main = Camera.main;
            if (main == null) return;
            _rt = new RenderTexture(320, 216, 16) { name = "Atlas_RexCam" };
            // Die Kamera-Vorlage der Ueberwachung nehmen: eine selbst gebaute Kamera sah nur den Boden,
            // die Objekte (Sicht-maskiertes Material) fehlten (Autotest 25.09.)
            Camera prefab = null;
            foreach (var sc in Object.FindObjectsOfType<SystemConsole>())
            {
                var surv = sc != null && sc.MinigamePrefab != null ? sc.MinigamePrefab.TryCast<SurveillanceMinigame>() : null;
                if (surv != null && surv.CameraPrefab != null) { prefab = surv.CameraPrefab; break; }
            }
            Camera cam;
            if (prefab != null) { cam = Object.Instantiate(prefab); _camGo = cam.gameObject; }
            else
            {
                _camGo = new GameObject("Atlas_RexCamera");
                cam = _camGo.AddComponent<Camera>();
                cam.orthographic = true;
                int shadow = LayerMask.NameToLayer("Shadow");
                cam.cullingMask = main.cullingMask & ~(1 << 5) & (shadow >= 0 ? ~(1 << shadow) : ~0);
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = Color.black;
            }
            cam.orthographicSize = 2.3f;
            cam.targetTexture = _rt;
            cam.depth = main.depth - 5;
            var view = AtlasMuseumBuilder.D.CameraViews.TryGetValue(0, out var v) ? v : new Vector2(-2.8f, 5.6f);
            _camGo.transform.position = new Vector3(view.x, view.y, main.transform.position.z);
            // Bildflaeche: ein Viereck mit der Textur
            var q = new GameObject("camview") { layer = 5 };
            q.transform.SetParent(root, false);
            q.transform.localPosition = new Vector3(Cam.x, Cam.y, -0.03f);
            var mesh = new Mesh();
            float hx = CamSize.x / 2f, hy = CamSize.y / 2f;
            mesh.vertices = new[] { new Vector3(-hx, -hy), new Vector3(hx, -hy), new Vector3(-hx, hy), new Vector3(hx, hy) };
            mesh.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) };
            mesh.triangles = new[] { 0, 2, 1, 2, 3, 1 };
            q.AddComponent<MeshFilter>().mesh = mesh;
            var mr = q.AddComponent<MeshRenderer>();
            _camMat = new Material(Shader.Find("Sprites/Default")) { mainTexture = _rt };
            mr.sharedMaterial = _camMat;
            mr.sortingOrder = 3;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Rex] camera view: {e.Message}"); }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!AtlasRex.Active && AtlasMinigame.DiagStep < 0) { AtlasRex.SetInput(AtlasRex.Light, false); Leave = true; return; }
        float agit = 1f - AtlasRex.Sleep / 100f;
        // der Rex waelzt sich: die Zielringe wandern, je wacher er ist, desto schneller
        _tv += (Random.value - 0.5f) * 70f * dt * (0.35f + agit);
        _tv *= Mathf.Exp(-0.9f * dt);
        float vmax = 4f + 12f * agit;
        _tv = Mathf.Clamp(_tv, -vmax, vmax);
        _target += _tv * dt;
        if (_target > 60f) { _target = 60f; _tv = -Mathf.Abs(_tv); }
        if (_target < -60f) { _target = -60f; _tv = Mathf.Abs(_tv); }
        if (AtlasRex.Roars != _seenRoars)
        {
            _seenRoars = AtlasRex.Roars;
            float dir = _target > 30f ? -1f : _target < -30f ? 1f : (Random.value < 0.5f ? -1f : 1f);
            _target = Mathf.Clamp(_target + dir * Random.Range(25f, 40f), -60f, 60f);
        }
        _drag.Tick(mouse, down, pressed);
        _rot += _drag.Delta;
        if (!AtlasMinigame.DiagAuto)
        {
            if (Input.GetKey(KeyCode.LeftArrow) || Input.GetKey(KeyCode.A)) _rot += 70f * dt;
            if (Input.GetKey(KeyCode.RightArrow) || Input.GetKey(KeyCode.D)) _rot -= 70f * dt;
        }
        float dev = Mathf.Abs(Mathf.DeltaAngle(_rot, _target));
        bool inZone = dev < AtlasRex.ProjTol;
        _grace = inZone ? 0.25f : _grace - dt;
        AtlasRex.SetInput(AtlasRex.Light, _grace > 0f);
        _dev.text = $"OFF BY {Mathf.RoundToInt(dev)}";
        _dev.color = inZone ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 0.75f, 0.35f);
        _msg.text = inZone ? "STARS IN PLACE" : AtlasRex.WarnPhase > 0f ? "HE IS ABOUT TO ROAR" : "TURN THE PROJECTOR";
        _msg.color = inZone ? new Color(0.5f, 1f, 0.6f) : AtlasRex.WarnPhase > 0f ? new Color(1f, 0.55f, 0.5f) : Color.white;
        Apply();
    }

    private static Vector2 Rot(Vector2 p, float deg)
    {
        float a = deg * Mathf.Deg2Rad, c = Mathf.Cos(a), s = Mathf.Sin(a);
        return Sky + new Vector2(p.x * c - p.y * s, p.x * s + p.y * c);
    }

    private void Apply()
    {
        bool ok = Mathf.Abs(Mathf.DeltaAngle(_rot, _target)) < AtlasRex.ProjTol;
        for (int i = 0; i < Stars.Length; i++)
        {
            var t = Rot(Stars[i], _target); var s = Rot(Stars[i], _rot);
            _rings[i].localPosition = new Vector3(t.x, t.y, _rings[i].localPosition.z);
            _stars[i].localPosition = new Vector3(s.x, s.y, _stars[i].localPosition.z);
            _stars[i].localScale = Vector3.one * (ok ? 0.5f : 0.42f);
        }
        for (int k = 0; k < Links.Length / 2; k++)
        {
            int a = Links[2 * k], b = Links[2 * k + 1];
            MatchKit.Set(_targetLines[k], 0, Rot(Stars[a], _target), 2);
            MatchKit.Set(_targetLines[k], 1, Rot(Stars[b], _target), 2);
            MatchKit.Set(_starLines[k], 0, Rot(Stars[a], _rot), 4);
            MatchKit.Set(_starLines[k], 1, Rot(Stars[b], _rot), 4);
            var c = new Color(1f, 0.92f, 0.62f, ok ? 0.85f : 0.3f);
            _starLines[k].startColor = _starLines[k].endColor = c;
        }
        RexKit.UpdateBar(_bar);
    }

    // Autotest: mit der Maus am Himmel ziehen und dem wandernden Ziel folgen
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        float err = Mathf.DeltaAngle(_rot, _target);
        _simA += Mathf.Clamp(err, -80f * dt, 80f * dt);
        float a = _simA * Mathf.Deg2Rad;
        mouse = Sky + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * 1.3f;
        down = true;
    }

    public void Dispose()
    {
        AtlasRex.SetInput(AtlasRex.Light, false);
        if (_camGo != null) Object.Destroy(_camGo);
        if (_rt != null) { _rt.Release(); Object.Destroy(_rt); }
        if (_camMat != null) Object.Destroy(_camMat);
    }
}
