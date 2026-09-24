// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Bausteine "Band halten", "Befuellen", "Pfad ziehen", "Klickziele", "Auswaehlen" und die
// Streichholz-Sondermechanik (docs/TASK_KONZEPT.md):
//
//   climate        Stabilise Climate Control   (Museum, Calibrate Distributor)
//   flywheel       Align the Flywheel          (Museum, Align Engine Output)
//   saw            Align the Saw Blade / Trim the Outboard (Wald, Align Engine Output)
//   generator      Tune the Generator          (Wald,   Calibrate Distributor)
//   steam/refuel   Stoke the Steam Engine / Refuel the Machines (Fuel Engines, 4 Schritte)
//   constellation  Trace a Constellation       (Museum, Chart Course)
//   patrol         Plot the Patrol Route       (Wald,   Chart Course)
//   moths          Chase the Moths             (Museum, Clear Asteroids; sichtbar)
//   census         Wildlife Census             (Wald,   Clear Asteroids; sichtbar)
//   pigment/water  Pigment / Water Sample Analysis (Inspect Sample, mit 60-s-Wartezeit)
//   audio          Sync the Audio Guide        (Museum, Upload Data)
//   trailcam       Collect Trail Cam Footage   (Wald,   Upload Data)
//   timecard       Punch the Time Card         (Wald,   Swipe Card)
//   lanterns       Light the Dock Lanterns     (Wald,   Prime Shields; sichtbar)
//   grate          Clear the Intake Grate      (Wald,   Clean O2 Filter)

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

// ================================================================== Stabilise Climate Control

internal sealed class ClimateMechanic : IAtlasMechanic
{
    public string Name => "climate";
    const float Band = 0.14f, Need = 3f;
    private readonly float[] _v = new float[3], _dir = new float[3];
    private readonly Transform[] _needles = new Transform[3];
    private readonly Vector2[] _buttons = new Vector2[3];
    private TextMeshPro _timer;
    private float _hold, _st, _nextTap;
    public float Progress => _hold / Need;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        string[] labels = { "TEMP", "HUMIDITY", "LIGHT" };
        for (int i = 0; i < 3; i++)
        {
            var g = new Vector2(-2.2f + i * 2.2f, 0.55f);
            AtlasTaskKit.Sprite(root, "task_gauge_band.png", 100f, g, 1).transform.localScale = Vector3.one * 0.68f;
            _needles[i] = AtlasTaskKit.Sprite(root, "task_needle.png", 100f, g, 2, new Vector2(8f / 120f, 0.5f)).transform;
            _needles[i].localScale = Vector3.one * 0.68f;
            _buttons[i] = new Vector2(g.x, -1.45f);
            AtlasTaskKit.Sprite(root, "task_button.png", 100f, _buttons[i], 1).transform.localScale = Vector3.one * 0.8f;
            MatchKit.Text(root, new Vector2(g.x, -0.72f), labels[i], 1.9f, Color.white, 3);
            _v[i] = Random.value < 0.5f ? Random.Range(0.08f, 0.3f) : Random.Range(0.7f, 0.92f);
            _dir[i] = _v[i] < 0.5f ? -1f : 1f;
        }
        _timer = MatchKit.Text(root, new Vector2(0f, 2.05f), "", 2.4f, new Color(0.6f, 1f, 0.6f), 3);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        bool all = true;
        for (int i = 0; i < 3; i++)
        {
            bool inBand = Mathf.Abs(_v[i] - 0.5f) < Band;
            if (!Done) _v[i] = Mathf.Clamp01(_v[i] + _dir[i] * (inBand ? 0.035f : 0.07f) * dt);
            if (Random.value < dt * 0.15f) _dir[i] = -_dir[i];
            if (pressed && !Done && Vector2.Distance(mouse, _buttons[i]) < 0.45f)
            {
                _v[i] += (0.5f - _v[i]) > 0 ? Mathf.Min(0.2f, 0.5f - _v[i] + 0.05f) : -Mathf.Min(0.2f, _v[i] - 0.5f + 0.05f);
                _dir[i] = -_dir[i];
            }
            all &= Mathf.Abs(_v[i] - 0.5f) < Band;
            _needles[i].localEulerAngles = new Vector3(0, 0, 210f - _v[i] * 240f);
        }
        if (Done) return;
        // Verlassen des Bands kostet nur langsam Fortschritt (nach Probelauf entschaerft)
        _hold = all ? _hold + dt : Mathf.Max(0f, _hold - dt * 0.5f);
        _timer.text = _hold > 0.05f ? $"{Mathf.CeilToInt(Need - _hold)}" : "";
        if (_hold >= Need) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        mouse = new Vector2(0f, 2f); down = false;
        if (_st < _nextTap) return;
        int worst = -1; float w = 0.07f;
        for (int i = 0; i < 3; i++) if (Mathf.Abs(_v[i] - 0.5f) > w) { w = Mathf.Abs(_v[i] - 0.5f); worst = i; }
        if (worst < 0) return;
        mouse = _buttons[worst];
        down = true;
        _nextTap = _st + 0.2f;
    }

    public void Dispose() { }
}

// ================================================================== Align the Flywheel / Saw Blade / Outboard

internal sealed class AlignMechanic : IAtlasMechanic
{
    public string Name => "align";
    const float Band = 0.14f, Need = 3f, TrackLen = 3.8f;
    static readonly Vector2 Track = new(-2.7f, -0.1f), Gauge = new(2.35f, 0.95f), Wheel = new(0.15f, -0.2f);
    private readonly string _panel, _wheel, _label;
    private Transform _knob, _needle, _wheelT;
    private TextMeshPro _timer;
    private float _s, _r, _target, _hold;
    private bool _drag;
    private InputScript _script;
    public float Progress => _hold / Need;
    public bool Done { get; private set; }

    public AlignMechanic(string panel, string wheel, string label) { _panel = panel; _wheel = wheel; _label = label; }

    private Vector2 KnobPos(float s) => Track + new Vector2(0f, (s - 0.5f) * TrackLen);

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _panel, 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_slider_track.png", 100f, Track, 1);
        _knob = AtlasTaskKit.Sprite(root, "task_slider_knob.png", 100f, KnobPos(0f), 3).transform;
        _wheelT = AtlasTaskKit.Sprite(root, _wheel, 100f, Wheel, 1).transform;
        _wheelT.localScale = Vector3.one * 0.95f;
        AtlasTaskKit.Sprite(root, "task_gauge_band.png", 100f, Gauge, 2).transform.localScale = Vector3.one * 0.62f;
        _needle = AtlasTaskKit.Sprite(root, "task_needle.png", 100f, Gauge, 3, new Vector2(8f / 120f, 0.5f)).transform;
        _needle.localScale = Vector3.one * 0.62f;
        MatchKit.Text(root, new Vector2(2.35f, -0.25f), _label, 2f, Color.white, 3);
        _timer = MatchKit.Text(root, new Vector2(2.35f, -0.75f), "", 2.4f, new Color(0.6f, 1f, 0.6f), 3);
        _target = Random.Range(0.35f, 0.8f);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (pressed && Vector2.Distance(mouse, _knob.localPosition) < 0.5f) _drag = true;
        if (!down) _drag = false;
        if (_drag && !Done) _s = Mathf.Clamp01((mouse.y - Track.y) / TrackLen + 0.5f);
        _knob.localPosition = new Vector3(Track.x, KnobPos(_s).y, _knob.localPosition.z);
        _r += (_s - _r) * Mathf.Min(1f, 1.3f * dt);                        // die Drehzahl folgt traege
        _wheelT.localEulerAngles += new Vector3(0, 0, -_r * 900f * dt);
        _needle.localEulerAngles = new Vector3(0, 0, 90f - Mathf.Clamp((_r - _target) * 240f, -120f, 120f));
        if (Done) return;
        _hold = Mathf.Abs(_r - _target) < Band ? _hold + dt : Mathf.Max(0f, _hold - dt * 0.7f);
        _timer.text = _hold > 0.05f ? $"{Mathf.CeilToInt(Need - _hold)}" : "";
        if (_hold >= Need) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Drag(KnobPos(0f), KnobPos(_target), 0.5f).Wait(KnobPos(_target), Need + 2.5f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Tune the Generator

internal sealed class GeneratorMechanic : IAtlasMechanic
{
    public string Name => "generator";
    const float TrackLen = 4.0f;
    static readonly Vector2 Choke = new(-0.3f, 1.85f), Body = new(0.9f, -0.55f), CordHome = new(-2.3f, 0.2f);
    const float GreenLo = 0.595f, GreenHi = 0.786f;
    private Transform _knob, _handle, _body;
    private LineRenderer _cord;
    private TextMeshPro _msg;
    private float _choke = 0.1f, _pullStartY, _pullT, _shake;
    private int _pulls, _need;
    private bool _dragKnob, _dragCord;
    private InputScript _script;
    public float Progress => _need == 0 ? 0f : _pulls / (float)_need;
    public bool Done { get; private set; }

    private Vector2 KnobPos(float s) => Choke + new Vector2((s - 0.5f) * TrackLen, 0f);

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_choke_track.png", 100f, Choke, 1).transform.localScale = new Vector3(TrackLen / 4.2f, 1f, 1f);
        MatchKit.Text(root, Choke + new Vector2(-2.6f, 0f), "CHOKE", 2f, Color.white, 3);
        _knob = AtlasTaskKit.Sprite(root, "task_slider_knob.png", 100f, KnobPos(_choke), 3).transform;
        _body = AtlasTaskKit.Sprite(root, "task_generator.png", 100f, Body, 1).transform;
        _cord = MatchKit.Line(root, new Color(0.15f, 0.15f, 0.17f), 0.06f, 2);
        _handle = AtlasTaskKit.Sprite(root, "task_cord.png", 100f, CordHome, 4).transform;
        _msg = MatchKit.Text(root, new Vector2(0.9f, -2.1f), "", 2.2f, Color.white, 3);
        _need = Random.Range(2, 4);
        UpdateCord();
    }

    private void UpdateCord()
    {
        MatchKit.Set(_cord, 0, Body + new Vector2(-1.3f, 0.3f), 2);
        MatchKit.Set(_cord, 1, _handle.localPosition, 2);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _shake = Mathf.Max(0f, _shake - dt);
        var s = Done ? new Vector2(Mathf.Sin(Time.time * 60f), Mathf.Cos(Time.time * 47f)) * 0.03f : Vector2.zero;
        _body.localPosition = new Vector3(Body.x + s.x, Body.y + s.y, _body.localPosition.z);
        if (Done) return;
        if (pressed)
        {
            if (Vector2.Distance(mouse, _knob.localPosition) < 0.5f) _dragKnob = true;
            else if (Vector2.Distance(mouse, _handle.localPosition) < 0.5f) { _dragCord = true; _pullStartY = mouse.y; _pullT = 0f; }
        }
        if (!down)
        {
            _dragKnob = false;
            if (_dragCord) { _dragCord = false; _handle.localPosition = new Vector3(CordHome.x, CordHome.y, _handle.localPosition.z); }
        }
        if (_dragKnob) _choke = Mathf.Clamp01((mouse.x - Choke.x) / TrackLen + 0.5f);
        _knob.localPosition = new Vector3(KnobPos(_choke).x, Choke.y, _knob.localPosition.z);
        if (_dragCord)
        {
            _pullT += dt;
            float y = Mathf.Clamp(mouse.y, CordHome.y - 2.2f, CordHome.y);
            _handle.localPosition = new Vector3(CordHome.x, y, _handle.localPosition.z);
            if (_pullStartY - mouse.y > 1.4f)
            {
                // ein kraeftiger Zug (schnell genug) - mit falschem Choke saeuft er ab
                if (_pullT > 0.6f) _msg.text = "PULL HARDER";
                else if (_choke < GreenLo || _choke > GreenHi) { _pulls = 0; _msg.text = "FLOODED"; }
                else { _pulls++; _msg.text = _pulls >= _need ? "RUNNING" : "..."; if (_pulls >= _need) Done = true; }
                _dragCord = false;
                _handle.localPosition = new Vector3(CordHome.x, CordHome.y, _handle.localPosition.z);
            }
        }
        UpdateCord();
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript().Drag(KnobPos(_choke), KnobPos((GreenLo + GreenHi) / 2f), 0.4f);
            for (int i = 0; i < 3; i++) _script.Drag(CordHome, CordHome + new Vector2(0f, -1.9f), 0.25f).Wait(CordHome, 0.2f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Stoke the Steam Engine / Refuel the Machines

internal sealed class FillMechanic : IAtlasMechanic
{
    public string Name => "fill";
    const float LineLo = 0.75f, LineHi = 0.9f;
    static readonly Vector2 Button = new(2.6f, -1.5f);
    private readonly bool _pour, _wald;
    private SpriteRenderer _fill, _stream;
    private Vector2 _fillBase;
    private float _fillH, _level, _red;
    private bool _holding, _wasHolding;
    private TextMeshPro _msg;
    private InputScript _script;
    public float Progress => _level;
    public bool Done { get; private set; }

    public FillMechanic(bool pour, bool wald) { _pour = pour; _wald = wald; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _wald ? "task_wald_panel.png" : "task_steel_panel.png", 100f, Vector2.zero, 0);
        Color liquid = _wald ? new Color(0.85f, 0.65f, 0.15f) : new Color(0.35f, 0.6f, 0.95f);
        if (!_pour)
        {
            AtlasTaskKit.Sprite(root, "task_tap.png", 100f, new Vector2(-0.5f, 1.55f), 2);
            var can = new Vector2(-0.1f, -0.75f);
            _fillBase = can + new Vector2(0f, -0.2f - 0.7f);
            _fillH = 1.4f;
            _fill = MatchKit.Box(root, _fillBase, new Vector2(0.8f, 0.01f), liquid, 1);
            AtlasTaskKit.Sprite(root, "task_can.png", 100f, can, 2);
            MatchKit.Box(root, _fillBase + new Vector2(0f, _fillH * (LineLo + LineHi) / 2f), new Vector2(1.0f, 0.04f), new Color(0.9f, 0.2f, 0.2f), 3);
            _stream = MatchKit.Box(root, new Vector2(-0.1f, 0.55f), new Vector2(0.12f, 1.2f), liquid, 1);
        }
        else
        {
            AtlasTaskKit.Sprite(root, "task_boiler.png", 100f, new Vector2(-1.2f, -0.3f), 1);
            var glass = new Vector2(1.1f, -0.1f);
            _fillBase = glass + new Vector2(0f, -1.7f);
            _fillH = 3.4f;
            _fill = MatchKit.Box(root, _fillBase, new Vector2(0.8f, 0.01f), liquid, 1);
            AtlasTaskKit.Sprite(root, "task_sightglass.png", 100f, glass, 2);
            MatchKit.Box(root, _fillBase + new Vector2(0f, _fillH), new Vector2(1.0f, 0.05f), new Color(0.3f, 0.85f, 0.4f), 3);
            _stream = MatchKit.Box(root, new Vector2(-1.2f, 1.8f), new Vector2(0.14f, 0.7f), liquid, 2);
        }
        AtlasTaskKit.Sprite(root, "task_button.png", 100f, Button, 2);
        MatchKit.Text(root, Button + new Vector2(0f, 0.75f), "HOLD", 2f, Color.white, 3);
        _msg = MatchKit.Text(root, new Vector2(0f, 2.1f), "", 2.4f, Color.white, 3);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        _holding = !Done && down && Vector2.Distance(mouse, Button) < 0.55f;
        if (_holding) _level += (_pour ? 0.3f : 0.36f) * dt;
        _stream.enabled = _holding;
        if (!_pour)
        {
            if (_level > 1f) { _level = 0f; _red = 1f; _msg.text = "OVERFLOW"; }
            if (_wasHolding && !_holding && !Done)
            {
                if (_level >= LineLo && _level <= LineHi) { Done = true; _msg.text = ""; }
                else if (_level > LineHi) { _level = 0f; _red = 1f; _msg.text = "TOO MUCH"; }
            }
        }
        else if (_level >= 1f) { _level = 1f; Done = true; }
        _wasHolding = _holding;
        float h = Mathf.Max(0.01f, _level * _fillH);
        _fill.transform.localScale = new Vector3(0.8f / 0.16f, h / 0.16f, 1f);
        _fill.transform.localPosition = new Vector3(_fillBase.x, _fillBase.y + h / 2f, _fill.transform.localPosition.z);
        _fill.color = new Color(_fill.color.r, _fill.color.g, _fill.color.b, 1f - _red * 0.6f);
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Hold(Button, _pour ? 3.6f : (LineLo + LineHi) / 2f / 0.36f).Wait(Button, 0.4f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Trace a Constellation

internal sealed class ConstellationMechanic : IAtlasMechanic
{
    public string Name => "constellation";
    static readonly Vector2 SkyC = new(0.9f, -0.05f);
    const float SkyR = 2.1f, Snap = 0.26f;
    private static readonly Vector2[][] Shapes =
    {
        new Vector2[] { new(-1f, 0.6f), new(-0.4f, 0.1f), new(0.2f, 0.35f), new(0.7f, -0.3f), new(1.1f, 0.4f) },
        new Vector2[] { new(-0.9f, -0.6f), new(-0.5f, 0.5f), new(0f, -0.1f), new(0.5f, 0.6f), new(0.9f, -0.5f) },
        new Vector2[] { new(-1f, 0f), new(-0.3f, 0.6f), new(0.4f, 0.5f), new(0.8f, -0.2f), new(0.1f, -0.7f) },
        new Vector2[] { new(-0.8f, 0.7f), new(-0.8f, -0.3f), new(0f, -0.6f), new(0.6f, 0f), new(1f, 0.7f) },
    };
    private readonly List<Vector2> _pattern = new(), _decoys = new();
    private readonly List<LineRenderer> _locked = new();
    private LineRenderer _live;
    private Transform _root;
    private int _reached = -1;
    private InputScript _script;
    public float Progress => Mathf.Max(0, _reached) / 4f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _root = root;
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_sky.png", 100f, SkyC, 1).transform.localScale = Vector3.one * (SkyR * 2f / 4.4f);
        var shape = Shapes[Random.Range(0, Shapes.Length)];
        float sc = Random.Range(1.2f, 1.45f), rot = Random.Range(-25f, 25f);
        var q = Quaternion.Euler(0, 0, rot);
        foreach (var p in shape) _pattern.Add(SkyC + (Vector2)(q * (Vector3)(p * sc)));
        // Vorlagenkarte links
        var card = new Vector2(-2.55f, 1.2f);
        AtlasTaskKit.Sprite(root, "task_card.png", 100f, card, 2).transform.localScale = Vector3.one * 0.8f;
        var cl = MatchKit.Line(root, new Color(0.3f, 0.3f, 0.4f), 0.035f, 3, shape.Length);
        for (int i = 0; i < shape.Length; i++)
        {
            var mp = card + shape[i] * 0.55f;
            MatchKit.Set(cl, i, mp, 3);
            AtlasTaskKit.Sprite(root, "task_star.png", 100f, mp, 4).transform.localScale = Vector3.one * 0.3f;
        }
        // Lockvoegel: weit genug von allen Sternen und Verbindungslinien
        for (int tries = 0; tries < 400 && _decoys.Count < 10; tries++)
        {
            var d = SkyC + Random.insideUnitCircle * (SkyR - 0.3f);
            bool ok = true;
            foreach (var p in _pattern) if (Vector2.Distance(p, d) < 0.5f) ok = false;
            foreach (var p in _decoys) if (Vector2.Distance(p, d) < 0.45f) ok = false;
            for (int i = 0; i + 1 < _pattern.Count && ok; i++) if (SegDist(d, _pattern[i], _pattern[i + 1]) < 0.4f) ok = false;
            if (ok) _decoys.Add(d);
        }
        foreach (var p in _pattern) AtlasTaskKit.Sprite(root, "task_star.png", 100f, p, 3).transform.localScale = Vector3.one * 0.5f;
        foreach (var p in _decoys) AtlasTaskKit.Sprite(root, "task_star.png", 100f, p, 3).transform.localScale = Vector3.one * 0.5f;
        _live = MatchKit.Line(root, new Color(1f, 0.95f, 0.6f, 0.8f), 0.05f, 5);
        _live.enabled = false;
    }

    private static float SegDist(Vector2 p, Vector2 a, Vector2 b)
    {
        var ab = b - a;
        float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
        return Vector2.Distance(p, a + ab * t);
    }

    private void Reset()
    {
        foreach (var l in _locked) Object.Destroy(l.gameObject);
        _locked.Clear();
        _reached = -1;
        _live.enabled = false;
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (Done) return;
        if (pressed && Vector2.Distance(mouse, _pattern[0]) < Snap) { Reset(); _reached = 0; }
        if (_reached < 0) return;
        if (!down) { Reset(); return; }                        // abgesetzt: von vorn
        _live.enabled = true;
        MatchKit.Set(_live, 0, _pattern[_reached], 5);
        MatchKit.Set(_live, 1, mouse, 5);
        var next = _pattern[_reached + 1];
        if (Vector2.Distance(mouse, next) < Snap)
        {
            var l = MatchKit.Line(_root, new Color(1f, 0.95f, 0.6f), 0.06f, 4);
            MatchKit.Set(l, 0, _pattern[_reached], 4);
            MatchKit.Set(l, 1, next, 4);
            _locked.Add(l);
            _reached++;
            if (_reached >= _pattern.Count - 1) { Done = true; _live.enabled = false; }
            return;
        }
        foreach (var d in _decoys) if (Vector2.Distance(mouse, d) < Snap * 0.8f) { Reset(); return; }
        for (int i = _reached + 2; i < _pattern.Count; i++) if (Vector2.Distance(mouse, _pattern[i]) < Snap * 0.8f) { Reset(); return; }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Path(_pattern, 0.35f).Wait(Vector2.zero, 0.3f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Plot the Patrol Route

internal sealed class PatrolMechanic : IAtlasMechanic
{
    public string Name => "patrol";
    const float Tol = 0.32f;
    private readonly List<Vector2> _pts = new();
    private readonly List<SpriteRenderer> _flags = new();
    private Transform _marker;
    private int _reached;
    private bool _drag;
    private InputScript _script;
    public float Progress => _reached / (float)(_pts.Count - 1);
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_trailmap.png", 100f, Vector2.zero, 0);
        for (int i = 0; i < 6; i++)
            _pts.Add(new Vector2(-2.6f + i * 1.05f, (i % 2 == 0 ? 1 : -1) * Random.Range(0.4f, 1.5f)));
        var path = MatchKit.Line(root, new Color(0.55f, 0.38f, 0.22f), 0.2f, 1, _pts.Count);
        for (int i = 0; i < _pts.Count; i++)
        {
            MatchKit.Set(path, i, _pts[i], 1);
            var f = AtlasTaskKit.Sprite(root, "task_flag.png", 100f, _pts[i] + new Vector2(0.12f, 0.35f), 2);
            f.transform.localScale = Vector3.one * 0.7f;
            _flags.Add(f);
        }
        _marker = AtlasTaskKit.Sprite(root, "task_marker.png", 100f, _pts[0], 4).transform;
        MatchKit.Text(root, new Vector2(0f, 2.2f), "PATROL ROUTE", 2.2f, new Color(0.3f, 0.22f, 0.12f), 3);
    }

    private float DistToPath(Vector2 p)
    {
        float best = float.MaxValue;
        for (int i = 0; i + 1 < _pts.Count; i++)
        {
            var a = _pts[i]; var ab = _pts[i + 1] - a;
            float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
            best = Mathf.Min(best, Vector2.Distance(p, a + ab * t));
        }
        return best;
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        for (int i = 0; i < _flags.Count; i++) _flags[i].color = i <= _reached ? new Color(0.5f, 1f, 0.5f) : Color.white;
        if (Done) return;
        if (pressed && Vector2.Distance(mouse, _marker.localPosition) < 0.45f) _drag = true;
        if (!down) _drag = false;
        if (!_drag) return;
        if (DistToPath(mouse) > Tol)
        {
            // vom Weg abgekommen: zurueck zur letzten Wegmarke
            _drag = false;
            _marker.localPosition = new Vector3(_pts[_reached].x, _pts[_reached].y, _marker.localPosition.z);
            return;
        }
        _marker.localPosition = new Vector3(mouse.x, mouse.y, _marker.localPosition.z);
        if (_reached + 1 < _pts.Count && Vector2.Distance(mouse, _pts[_reached + 1]) < 0.3f)
        {
            _reached++;
            if (_reached == _pts.Count - 1) Done = true;
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Path(_pts, 0.3f).Wait(Vector2.zero, 0.3f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Chase the Moths / Wildlife Census (Klickziele)

internal sealed class TargetsMechanic : IAtlasMechanic
{
    public string Name => _census ? "census" : "moths";
    const int Goal = 12;
    private readonly bool _census;
    private Transform _root, _torch;
    private readonly List<(Transform T, Vector2 Vel, bool Bad, float Phase)> _live = new();
    private readonly List<(Transform T, float T0, Vector2 From)> _caught = new();
    private TextMeshPro _count;
    private int _hits;
    private float _spawn, _red, _st, _nextTap;
    private SpriteRenderer _bg;
    public float Progress => _hits / (float)Goal;
    public bool Done { get; private set; }

    public TargetsMechanic(bool census) { _census = census; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _root = root;
        _bg = AtlasTaskKit.Sprite(root, _census ? "task_clearing.png" : "task_gallery.png", 100f, Vector2.zero, 0);
        if (!_census)
        {
            AtlasTaskKit.Sprite(root, "task_jar.png", 100f, new Vector2(2.9f, -1.8f), 2);
            _torch = AtlasTaskKit.Sprite(root, "task_torch.png", 100f, Vector2.zero, 6).transform;
        }
        _count = MatchKit.Text(root, new Vector2(-2.7f, 2.15f), $"0/{Goal}", 2.6f, Color.white, 7);
        for (int i = 0; i < (_census ? 2 : 5); i++) Spawn();
    }

    private void Spawn()
    {
        if (_census)
        {
            bool owl = Random.value < 0.25f;
            bool left = Random.value < 0.5f;
            var file = owl ? "task_owl.png" : (Random.value < 0.5f ? "task_deer.png" : "task_boar.png");
            float y = owl ? Random.Range(0.6f, 1.8f) : Random.Range(-1.9f, 0.2f);
            var t = AtlasTaskKit.Sprite(_root, file, 100f, new Vector2(left ? -4f : 4f, y), 3).transform;
            t.localScale = new Vector3(left ? 0.8f : -0.8f, 0.8f, 1f);
            _live.Add((t, new Vector2((left ? 1 : -1) * Random.Range(1.6f, 2.6f), 0f), owl, 0f));
        }
        else
        {
            var p = new Vector2(Random.Range(-3f, 3f), Random.Range(-1.8f, 1.9f));
            var t = AtlasTaskKit.Sprite(_root, "task_moth.png", 100f, p, 4).transform;
            t.localScale = Vector3.one * 0.8f;
            _live.Add((t, Random.insideUnitCircle.normalized * 1.2f, false, Random.value * 10f));
        }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        _bg.color = Color.Lerp(Color.white, new Color(1f, 0.6f, 0.6f), _red * 0.6f);
        if (_torch != null) _torch.localPosition = new Vector3(mouse.x, mouse.y, _torch.localPosition.z);
        for (int i = _live.Count - 1; i >= 0; i--)
        {
            var (t, v, bad, ph) = _live[i];
            if (!_census)
            {
                // Flattern: Richtung dreht staendig, vom Rand zurueck
                ph += dt;
                v = (Vector2)(Quaternion.Euler(0, 0, Mathf.Sin(ph * 3.1f) * 220f * dt) * (Vector3)v);
                var np = (Vector2)t.localPosition + v * dt;
                if (Mathf.Abs(np.x) > 3.2f) v.x = -v.x;
                if (np.y > 2.1f || np.y < -2.0f) v.y = -v.y;
                t.localPosition = new Vector3(np.x, np.y, t.localPosition.z);
                t.localEulerAngles = new Vector3(0, 0, Mathf.Sin(ph * 20f) * 12f);
                _live[i] = (t, v, bad, ph);
            }
            else
            {
                t.localPosition += (Vector3)(v * dt);
                // nur innerhalb des Felds zeichnen (Tiere starten ausserhalb und laufen herein)
                var sr = t.GetComponent<SpriteRenderer>();
                if (sr != null) sr.enabled = Mathf.Abs(t.localPosition.x) < 3.2f;
                if (Mathf.Abs(t.localPosition.x) > 4.3f) { Object.Destroy(t.gameObject); _live.RemoveAt(i); }
            }
        }
        for (int i = _caught.Count - 1; i >= 0; i--)
        {
            var c = _caught[i];
            float k = (Time.time - c.T0) / 0.45f;
            if (k >= 1f) { Object.Destroy(c.T.gameObject); _caught.RemoveAt(i); continue; }
            var to = _census ? c.From + new Vector2(0f, 0.6f) : new Vector2(2.9f, -1.8f);
            var p = Vector2.Lerp(c.From, to, k);
            c.T.localPosition = new Vector3(p.x, p.y, c.T.localPosition.z);
            c.T.localScale = c.T.localScale * (1f - dt * 2f);
        }
        if (Done) return;
        _spawn -= dt;
        int want = _census ? 3 : 5;
        if (_spawn <= 0f && _live.Count < want) { Spawn(); _spawn = _census ? Random.Range(0.4f, 0.8f) : 0.2f; }
        if (!pressed) return;
        int best = -1; float bd = _census ? 0.7f : 0.4f;
        for (int i = 0; i < _live.Count; i++)
        {
            float d = Vector2.Distance(mouse, _live[i].T.localPosition);
            if (d < bd) { bd = d; best = i; }
        }
        if (best < 0) return;
        var hit = _live[best];
        _live.RemoveAt(best);
        if (hit.Bad) { _hits = Mathf.Max(0, _hits - 2); _red = 1f; Object.Destroy(hit.T.gameObject); }
        else
        {
            _hits++;
            _caught.Add((hit.T, Time.time, hit.T.localPosition));
            MatchKit.PlayVisual(TaskTypes.ClearAsteroids);
        }
        _count.text = $"{_hits}/{Goal}";
        if (_hits >= Goal) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        mouse = new Vector2(0f, 2.3f); down = false;
        if (_st < _nextTap) return;
        foreach (var l in _live)
        {
            if (l.Bad) continue;
            var p = (Vector2)l.T.localPosition;
            if (Mathf.Abs(p.x) > 3.3f) continue;
            mouse = p + l.Vel * 0.02f;
            down = true;
            _nextTap = _st + (_census ? 0.5f : 0.4f);
            return;
        }
    }

    public void Dispose() { }
}

// ================================================================== Pigment / Water Sample Analysis (mit Wartezeit)

internal sealed class SampleMechanic : IAtlasMechanic
{
    public string Name => _water ? "water" : "pigment";
    const float Wait = 60f;
    private readonly bool _water;
    private AtlasTaskCtx _ctx;
    private int _state;                      // 0 = nichts gestartet, 1 = laeuft, 2 = fertig -> auswaehlen
    private readonly List<(Vector2 P, SpriteRenderer R)> _samples = new();
    private int _odd;
    private TextMeshPro _msg;
    private static readonly Vector2 Start = new(2.5f, -1.6f);
    private float _red;
    private InputScript _script;
    public float Progress => _state / 2f;
    public bool Done { get; private set; }
    public bool Leave { get; private set; }

    public SampleMechanic(bool water) { _water = water; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _ctx = ctx;
        AtlasTaskKit.Sprite(root, _water ? "task_wald_panel.png" : "task_steel_panel.png", 100f, Vector2.zero, 0);
        var t = ctx.Task;
        if (AtlasMinigame.DiagStep >= 0) _state = AtlasMinigame.DiagStep;
        else if (t != null) _state = t.TimerStarted == NormalPlayerTask.TimerState.NotStarted ? 0 : t.TimerStarted == NormalPlayerTask.TimerState.Started ? 1 : 2;
        _msg = MatchKit.Text(root, new Vector2(0f, 2.1f), "", 2.5f, Color.white, 4);
        _odd = Random.Range(0, 5);
        // Referenz: Pigment = Spektrum aus vier Farbbalken; Wasser = Trinkwasser-Farbskala
        Color[] refCols = _water
            ? new[] { new Color(0.95f, 0.9f, 0.4f), new Color(0.75f, 0.9f, 0.35f), new Color(0.45f, 0.85f, 0.4f), new Color(0.3f, 0.7f, 0.45f) }
            : new[] { new Color(0.85f, 0.2f, 0.2f), new Color(0.95f, 0.7f, 0.2f), new Color(0.3f, 0.6f, 0.9f), new Color(0.3f, 0.75f, 0.4f) };
        if (_state == 2)
        {
            for (int k = 0; k < 4; k++) MatchKit.Box(root, new Vector2(-1.2f + k * 0.8f, 1.35f), new Vector2(0.7f, 0.35f), refCols[k], 2);
            MatchKit.Text(root, new Vector2(-2.6f, 1.35f), "REF", 2f, Color.white, 3);
        }
        for (int i = 0; i < 5; i++)
        {
            var p = new Vector2(-2.4f + i * 1.2f, -0.35f);
            var r = AtlasTaskKit.Sprite(root, _water ? "task_strip.png" : "task_vial.png", 100f, p, 2);
            r.transform.localScale = Vector3.one * 0.85f;
            _samples.Add((p, r));
            if (_state != 2) { r.color = new Color(0.85f, 0.85f, 0.9f); continue; }
            if (_water)
            {
                // eine Streifenfarbe passt nicht zur Skala
                var c = i == _odd ? new Color(0.65f, 0.35f, 0.75f) : refCols[Random.Range(0, 4)];
                MatchKit.Box(root, p + new Vector2(0f, 0.55f), new Vector2(0.3f, 0.3f), c, 3);
            }
            else
            {
                // Spektrallinie unter dem Roehrchen; die abweichende Probe hat einen Balken vertauscht
                var cols = (Color[])refCols.Clone();
                if (i == _odd) (cols[1], cols[2]) = (cols[2], cols[1]);
                for (int k = 0; k < 4; k++) MatchKit.Box(root, p + new Vector2(-0.3f + k * 0.2f, -1.25f), new Vector2(0.18f, 0.3f), cols[k], 3);
                r.color = Color.Lerp(Color.white, cols[0], 0.3f);
            }
        }
        if (_state == 0)
        {
            AtlasTaskKit.Sprite(root, "task_button.png", 100f, Start, 2);
            MatchKit.Text(root, Start + new Vector2(0f, 0.75f), "START", 2f, Color.white, 3);
            _msg.text = "INSERT SAMPLES";
        }
        if (_state == 2) _msg.text = "PICK THE ANOMALY";
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        var t = _ctx.Task;
        if (_state == 1)
        {
            float left = t != null ? t.TaskTimer : 0f;
            _msg.text = $"ANALYSING  {Mathf.CeilToInt(Mathf.Max(0f, left))}s";
            for (int i = 0; i < _samples.Count; i++) _samples[i].R.transform.localEulerAngles = new Vector3(0, 0, Mathf.Sin(Time.time * 8f + i) * 4f);
            return;
        }
        foreach (var s in _samples) s.R.color = _state == 2 ? Color.Lerp(s.R.color, new Color(1f, 0.5f, 0.5f), _red * 0.2f) : s.R.color;
        if (Done || Leave || !pressed) return;
        if (_state == 0 && Vector2.Distance(mouse, Start) < 0.55f)
        {
            if (t != null && AtlasMinigame.DiagStep < 0)
            {
                t.TimerStarted = NormalPlayerTask.TimerState.Started;
                t.TaskTimer = Wait;
            }
            Leave = true;
            return;
        }
        if (_state != 2) return;
        for (int i = 0; i < _samples.Count; i++)
        {
            if (!MatchKit.In(mouse, _samples[i].P, new Vector2(0.45f, 1.0f))) continue;
            if (i == _odd) Done = true;
            else
            {
                // falsch: Messung verworfen, neu starten
                _red = 1f;
                _msg.text = "WRONG - RESTART";
                if (t != null && AtlasMinigame.DiagStep < 0) t.TimerStarted = NormalPlayerTask.TimerState.NotStarted;
                Leave = true;
            }
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= _state == 0 ? new InputScript().Wait(Start, 0.3f).Tap(Start) : new InputScript().Wait(Vector2.zero, 0.5f).Tap(_samples[_odd].P);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Sync the Audio Guide / Collect Trail Cam Footage

internal sealed class TransferMechanic : IAtlasMechanic
{
    public string Name => _wald ? "trailcam" : "audio";
    const float Duration = 6.5f;
    private readonly bool _wald;
    private int _step, _answer = -1;
    private readonly List<(Vector2 P, SpriteRenderer R, bool Ok)> _choices = new();
    private Transform _item;
    private Vector2 _itemHome, _slot;
    private bool _drag, _running;
    private float _t, _red;
    private SpriteRenderer _bar;
    private TextMeshPro _msg;
    private InputScript _script;
    public float Progress => _running ? 0.5f + 0.5f * _t / Duration : 0f;
    public bool Done { get; private set; }

    public TransferMechanic(bool wald) { _wald = wald; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _step = ctx.Step;
        AtlasTaskKit.Sprite(root, _wald ? "task_wald_panel.png" : "task_museum_panel.png", 100f, Vector2.zero, 0);
        _msg = MatchKit.Text(root, new Vector2(0f, 2.1f), "", 2.4f, Color.white, 4);
        MatchKit.Box(root, new Vector2(0f, -2.0f), new Vector2(5.2f, 0.3f), new Color(0.15f, 0.15f, 0.18f), 2);
        _bar = MatchKit.Box(root, new Vector2(-2.6f, -2.0f), new Vector2(0.01f, 0.24f), new Color(0.35f, 0.85f, 0.45f), 3);
        if (_step == 0)
        {
            if (_wald)
            {
                _msg.text = AtlasTaskKit.T("FIND THE ANIMAL");
                _answer = Random.Range(0, 6);
                for (int i = 0; i < 6; i++)
                {
                    var p = new Vector2(-2.2f + (i % 3) * 2.2f, 0.9f - (i / 3) * 1.65f);
                    var r = AtlasTaskKit.Sprite(root, "task_photo.png", 100f, p, 2);
                    if (i == _answer)
                    {
                        var d = AtlasTaskKit.Sprite(root, "task_deer.png", 100f, p + new Vector2(Random.Range(-0.4f, 0.4f), -0.15f), 3);
                        d.transform.localScale = Vector3.one * 0.45f;
                        d.color = new Color(0.75f, 0.85f, 0.75f);
                    }
                    _choices.Add((p, r, i == _answer));
                }
            }
            else
            {
                string[] icons = { "dino", "mummy", "planet", "gem", "painting" };
                int exhibit = Random.Range(0, icons.Length);
                MatchKit.Text(root, new Vector2(-2.5f, 1.55f), "EXHIBIT", 1.8f, Color.white, 3);
                AtlasTaskKit.Sprite(root, $"task_icon_{icons[exhibit]}.png", 100f, new Vector2(-2.5f, 0.6f), 2);
                var opts = new List<int> { exhibit };
                while (opts.Count < 3) { int k = Random.Range(0, icons.Length); if (!opts.Contains(k)) opts.Add(k); }
                for (int i = 2; i > 0; i--) { int j = Random.Range(0, i + 1); (opts[i], opts[j]) = (opts[j], opts[i]); }
                _msg.text = "PICK THE MATCHING TRACK";
                for (int i = 0; i < 3; i++)
                {
                    var p = new Vector2(-0.4f + i * 1.45f, 0.4f);
                    var r = AtlasTaskKit.Sprite(root, $"task_icon_{icons[opts[i]]}.png", 100f, p, 2);
                    MatchKit.Text(root, p + new Vector2(0f, -0.8f), $"TRACK {i + 1}", 1.6f, Color.white, 3);
                    _choices.Add((p, r, opts[i] == exhibit));
                }
            }
        }
        else
        {
            _itemHome = new Vector2(-2.2f, 0.3f);
            _slot = _wald ? new Vector2(1.6f, -0.15f) : new Vector2(1.6f, -0.5f);
            AtlasTaskKit.Sprite(root, _wald ? "task_pc.png" : "task_dock.png", 100f, _wald ? new Vector2(1.6f, 0.6f) : _slot, 1);
            _item = AtlasTaskKit.Sprite(root, _wald ? "task_sdcard.png" : "task_audioguide.png", 100f, _itemHome, 4).transform;
            _msg.text = AtlasTaskKit.T(_wald ? "INSERT THE SD CARD" : "DOCK THE AUDIO GUIDE");
        }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        foreach (var c in _choices) c.R.color = Color.Lerp(Color.white, new Color(1f, 0.5f, 0.5f), c.Ok ? 0f : _red);
        if (_running)
        {
            _t += dt;
            float w = 5.2f * Mathf.Clamp01(_t / Duration);
            _bar.transform.localScale = new Vector3(Mathf.Max(0.01f, w) / 0.16f, 0.24f / 0.16f, 1f);
            _bar.transform.localPosition = new Vector3(-2.6f + w / 2f, -2.0f, _bar.transform.localPosition.z);
            if (_t >= Duration) Done = true;
            return;
        }
        if (_step == 0)
        {
            if (!pressed) return;
            foreach (var c in _choices)
                if (MatchKit.In(mouse, c.P, new Vector2(0.9f, 0.7f)))
                {
                    if (c.Ok) { _running = true; _msg.text = AtlasTaskKit.T(_wald ? "COPYING" : "DOWNLOADING"); }
                    else _red = 1f;
                }
            return;
        }
        if (pressed && Vector2.Distance(mouse, _item.localPosition) < 0.6f) _drag = true;
        if (!_drag) return;
        _item.localPosition = new Vector3(mouse.x, mouse.y, _item.localPosition.z);
        if (down) return;
        _drag = false;
        if (Vector2.Distance(mouse, _slot) < 0.7f)
        {
            _item.localPosition = new Vector3(_slot.x, _slot.y + (_wald ? -0.2f : 0.4f), _item.localPosition.z);
            _running = true;
            _msg.text = "UPLOADING";
        }
        else _item.localPosition = new Vector3(_itemHome.x, _itemHome.y, _item.localPosition.z);
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            if (_step == 0) _script.Tap(_choices.Find(c => c.Ok).P);
            else _script.Drag(_itemHome, _slot, 0.45f);
            _script.Wait(Vector2.zero, Duration + 1f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Punch the Time Card

internal sealed class TimecardMechanic : IAtlasMechanic
{
    public string Name => "timecard";
    static readonly Vector2 Clock = new(1.3f, 0.45f), Lever = new(1.3f, -1.75f);
    const float Period = 2.4f;
    private readonly List<(Vector2 P, Transform T, bool Own)> _cards = new();
    private Transform _hand;
    private bool _inserted;
    private float _a, _red;
    private SpriteRenderer _clockR;
    private TextMeshPro _msg;
    private InputScript _script;
    private float _st;
    public float Progress => _inserted ? 0.5f : 0f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        _clockR = AtlasTaskKit.Sprite(root, "task_clock.png", 100f, Clock, 1);
        _clockR.transform.localScale = Vector3.one * 0.95f;
        _hand = AtlasTaskKit.Sprite(root, "task_hand.png", 100f, Clock, 3, new Vector2(0.5f, 0.08f)).transform;
        AtlasTaskKit.Sprite(root, "task_button.png", 100f, Lever, 2);
        MatchKit.Text(root, Lever + new Vector2(0.95f, 0f), "PUNCH", 2f, Color.white, 3);
        string own = "YOU";
        try { own = PlayerControl.LocalPlayer.Data.PlayerName; } catch { }
        var names = new List<string> { own, "RANGER", "WARDEN", "SCOUT" };
        var order = new List<int> { 0, 1, 2, 3 };
        for (int i = 3; i > 0; i--) { int j = Random.Range(0, i + 1); (order[i], order[j]) = (order[j], order[i]); }
        for (int i = 0; i < 4; i++)
        {
            var p = new Vector2(-2.85f + (i % 2) * 1.35f, 1.05f - (i / 2) * 2.1f);
            var c = AtlasTaskKit.Sprite(root, "task_timecard.png", 100f, p, 2).transform;
            c.localScale = Vector3.one * 0.85f;
            var tx = MatchKit.Text(c, new Vector2(0f, 0.6f), names[order[i]], 1.4f, Color.black, 3);
            _cards.Add((p, c, order[i] == 0));
        }
        _msg = MatchKit.Text(root, new Vector2(1.3f, 2.2f), "TAKE YOUR CARD", 2.2f, Color.white, 4);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        _clockR.color = Color.Lerp(Color.white, new Color(1f, 0.5f, 0.5f), _red);
        if (!Done) _a = (_a + 360f / Period * dt) % 360f;
        _hand.localEulerAngles = new Vector3(0, 0, -_a);
        if (Done || !pressed) return;
        if (!_inserted)
        {
            foreach (var c in _cards)
                if (MatchKit.In(mouse, c.P, new Vector2(0.55f, 0.85f)))
                {
                    if (c.Own)
                    {
                        _inserted = true;
                        c.T.localPosition = new Vector3(Clock.x - 1.35f, Clock.y - 0.2f, c.T.localPosition.z);
                        _msg.text = "PUNCH AT THE FULL HOUR";
                    }
                    else _red = 1f;
                }
            return;
        }
        if (Vector2.Distance(mouse, Lever) < 0.55f)
        {
            float off = Mathf.Abs(Mathf.DeltaAngle(_a, 0f));
            if (off < 20f) { Done = true; _msg.text = "PUNCHED"; }
            else _red = 1f;
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        if (!_inserted) { _script ??= new InputScript().Tap(_cards.Find(c => c.Own).P); _script.Next(dt, out mouse, out down); return; }
        // auf die volle Stunde warten, dann druecken
        float off = Mathf.Abs(Mathf.DeltaAngle(_a, 0f));
        mouse = Lever;
        down = off < 8f && ((int)(_st * 10f) % 2 == 0);
    }

    public void Dispose() { }
}

// ================================================================== Light the Dock Lanterns (Streichholz im Wind)

internal sealed class LanternsMechanic : IAtlasMechanic
{
    public string Name => "lanterns";
    const float Burn = 4.5f, HoldIn = 0.35f;
    static readonly Vector2 Box = new(-2.3f, -1.75f), Gauge = new(2.6f, -1.55f);
    private readonly List<(Vector2 P, SpriteRenderer R)> _lanterns = new();
    private readonly bool[] _lit = new bool[4];
    private readonly float[] _in = new float[4];
    private Sprite _on;
    private Transform _match, _needle;
    private SpriteRenderer _flame;
    private bool _drag, _burning;
    private float _strike, _burn, _wind, _gust, _st;
    private Vector2 _strikeStart;
    private TextMeshPro _msg;
    private InputScript _script;
    public float Progress { get { int n = 0; foreach (var l in _lit) if (l) n++; return n / 4f; } }
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_dock_night.png", 100f, Vector2.zero, 0);
        _on = AtlasAssets.TaskSprite("task_lantern_on.png", 100f, new Vector2(0.5f, 0.5f));
        for (int i = 0; i < 4; i++)
        {
            var p = new Vector2(-2.4f + i * 1.6f, 1.2f);
            _lanterns.Add((p, AtlasTaskKit.Sprite(root, "task_lantern_off.png", 100f, p, 2)));
        }
        AtlasTaskKit.Sprite(root, "task_matchbox.png", 100f, Box, 2);
        _match = AtlasTaskKit.Sprite(root, "task_match.png", 100f, Box + new Vector2(0.6f, 0.35f), 5, new Vector2(0.5f, 0.12f)).transform;
        _match.localEulerAngles = new Vector3(0, 0, 90f);
        _flame = AtlasTaskKit.Sprite(_match, "task_flame.png", 100f, new Vector2(0f, 1.55f), 6);
        _flame.enabled = false;
        AtlasTaskKit.Sprite(root, "task_gauge.png", 100f, Gauge, 2).transform.localScale = Vector3.one * 0.45f;
        _needle = AtlasTaskKit.Sprite(root, "task_needle.png", 100f, Gauge, 3, new Vector2(8f / 120f, 0.5f)).transform;
        _needle.localScale = Vector3.one * 0.45f;
        MatchKit.Text(root, Gauge + new Vector2(0f, -0.8f), "WIND", 1.8f, Color.white, 3);
        _msg = MatchKit.Text(root, new Vector2(0f, 2.25f), "STRIKE A MATCH", 2.2f, Color.white, 4);
    }

    private Vector2 Tip => (Vector2)_match.localPosition + (Vector2)(Quaternion.Euler(0, 0, _match.localEulerAngles.z) * new Vector3(0f, 1.3f, 0f)) * 1f;

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        // Wind: ruhiges Grundrauschen, ab und zu eine Boe
        _gust -= dt;
        if (_gust <= 0f) _gust = Random.Range(2.5f, 5f);
        float gustK = _gust < 0.8f ? Mathf.Sin(_gust / 0.8f * Mathf.PI) : 0f;
        _wind = Mathf.Clamp01(0.25f + 0.15f * Mathf.Sin(Time.time * 1.7f) + gustK * 0.7f);
        _needle.localEulerAngles = new Vector3(0, 0, 210f - _wind * 240f);
        for (int i = 0; i < 4; i++) if (_lit[i]) _lanterns[i].R.sprite = _on;
        if (Done) return;
        if (pressed && Vector2.Distance(mouse, Tip) < 0.7f || pressed && Vector2.Distance(mouse, _match.localPosition) < 0.6f)
        {
            _drag = true;
            _strikeStart = mouse;
            _strike = 0f;
        }
        if (!down && _drag)
        {
            _drag = false;
            _burning = false; _flame.enabled = false;               // losgelassen: Streichholz zurueck, aus
            _match.localPosition = new Vector3(Box.x + 0.6f, Box.y + 0.35f, _match.localPosition.z);
            _match.localEulerAngles = new Vector3(0, 0, 90f);
            _msg.text = "STRIKE A MATCH";
        }
        if (!_drag) return;
        // die Kuppe sitzt genau unter dem Mauszeiger (Test 23.09.: mit Versatz traf man die Laternen nicht)
        _match.localEulerAngles = new Vector3(0, 0, 20f);
        var stick = (Vector2)(Quaternion.Euler(0, 0, 20f) * new Vector3(0f, 1.3f, 0f));
        _match.localPosition = new Vector3(mouse.x - stick.x, mouse.y - stick.y, _match.localPosition.z);
        var tip = Tip;
        if (!_burning)
        {
            // Reiben: mit der Kuppe ueber die Reibflaeche der Schachtel
            if (MatchKit.In(tip, Box, new Vector2(1.0f, 0.45f))) _strike += Mathf.Abs(mouse.x - _strikeStart.x);
            _strikeStart = mouse;
            if (_strike > 1.0f) { _burning = true; _burn = Burn; _flame.enabled = true; _msg.text = "LIGHT THE LANTERNS"; }
            return;
        }
        _burn -= dt;
        int inside = -1;
        for (int i = 0; i < 4; i++) if (!_lit[i] && Vector2.Distance(tip, _lanterns[i].P) < 0.55f) inside = i;
        // eine Boe blaest das Streichholz aus, ausser es steckt schon in der Laterne
        if (_burn <= 0f || (inside < 0 && _wind > 0.8f))
        {
            _burning = false; _flame.enabled = false;
            _msg.text = _burn <= 0f ? "BURNT OUT" : "BLOWN OUT";
            return;
        }
        _flame.transform.localScale = Vector3.one * (0.8f + 0.2f * Mathf.Sin(Time.time * 25f));
        for (int i = 0; i < 4; i++)
        {
            if (i == inside) _in[i] += dt; else _in[i] = 0f;
            if (!_lit[i] && _in[i] >= HoldIn) _lit[i] = true;
        }
        if (Array.TrueForAll(_lit, l => l)) { Done = true; MatchKit.PlayVisual(TaskTypes.PrimeShields); }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script != null && _script.Finished && !Done) _script = null;   // von einer Boe ausgeblasen: neu ansetzen
        if (_script == null)
        {
            // Streichholz greifen, zweimal ueber die Reibflaeche, dann die Laternen abgehen
            var grab = (Vector2)_match.localPosition;
            var pts = new List<Vector2> { grab };
            // die Kuppe folgt dem Mauszeiger direkt
            Vector2 M(Vector2 tip) => tip;
            pts.Add(M(Box + new Vector2(-0.7f, 0f))); pts.Add(M(Box + new Vector2(0.7f, 0f))); pts.Add(M(Box + new Vector2(-0.7f, 0f)));
            _script = new InputScript();
            _script.Seg(grab, grab, 0.05f, false).Seg(grab, grab, 0.05f, true);
            for (int i = 1; i < pts.Count; i++) _script.Seg(pts[i - 1], pts[i], 0.2f, true);
            var last = pts[^1];
            for (int li = 0; li < _lanterns.Count; li++)
            {
                if (_lit[li]) continue;
                var m = M(_lanterns[li].P);
                _script.Seg(last, m, 0.3f, true).Seg(m, m, HoldIn + 0.15f, true);
                last = m;
            }
            _script.Seg(last, last, 0.1f, false);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}
