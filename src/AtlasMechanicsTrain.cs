// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Die Stationen der Zug-Sabotagen (AtlasRunaway, AtlasSmoke):
//
//   brakelever  Dampfbremse (Fuehrerstand): Hebel mit der Maus nach unten ziehen und im markierten Bereich halten;
//               er kriecht von selbst zurueck, die Anzeige zeigt den Ueberdruck. Meldet "im Bereich an/aus".
//   handbrake   Handbremse (hintere Plattform): Rad im Uhrzeigersinn kurbeln, zaehlt bei 0,6 bis 1,5 U/s.
//   hatchcrank  Dachluke: Kurbel drehen, nach CrankTurns Umdrehungen ist die Luke offen (AtlasSmoke.OpenHatch).
//
// Grafik aus dem Kartenpaket, wenn vorhanden (task_train_*.png des Grafik-Auftrags), sonst gezeichnete Formen;
// die Stationen schliessen immer ohne Task-Schritt (Leave).

using System;
using Random = UnityEngine.Random;
using TMPro;
using UnityEngine;

namespace UnknownsAtlas;

internal static class TrainKit
{
    public static void Panel(Transform root)
    {
        string panel = CrisisLink.Panel ?? (AtlasAssets.TaskArtExists("task_train_panel.png") ? "task_train_panel.png" : "task_wald_panel.png");
        AtlasTaskKit.Sprite(root, panel, 100f, Vector2.zero, 0);
    }

    /// <summary>Bild aus dem Kartenpaket oder null.</summary>
    public static SpriteRenderer Art(Transform root, string file, Vector2 pos, int order, Vector2? pivot = null) =>
        AtlasAssets.TaskArtExists(file) ? AtlasTaskKit.Sprite(root, file, 100f, pos, order, pivot) : null;

    public static (SpriteRenderer Fill, TextMeshPro Text) Bar(Transform root, Color col)
    {
        MatchKit.Box(root, new Vector2(0f, -2.05f), new Vector2(6.1f, 0.34f), new Color(0.05f, 0.06f, 0.09f, 0.95f), 6);
        var fill = MatchKit.Box(root, new Vector2(-3.0f, -2.05f), new Vector2(0.01f, 0.24f), col, 7);
        var text = MatchKit.Text(root, new Vector2(0f, -2.04f), "", 1.35f, Color.white, 8);
        return (fill, text);
    }

    public static void SetBar((SpriteRenderer Fill, TextMeshPro Text) bar, float frac, string text)
    {
        float w = Mathf.Max(0.01f, 6.0f * Mathf.Clamp01(frac));
        bar.Fill.transform.localScale = new Vector3(w / 0.16f, 0.24f / 0.16f, 1f);
        var p = bar.Fill.transform.localPosition;
        bar.Fill.transform.localPosition = new Vector3(-3.0f + w / 2f, p.y, p.z);
        bar.Text.text = text;
    }
}

// ================================================================== Dampfbremse

// ================================================================== Kopplung

/// <summary>
/// Welche Krise die beiden Halte-Stationen (Hebel, Kurbel) gerade bedienen: die Zug-Sabotage Runaway Train (Standard)
/// oder eine Krise auf einer Vanilla-Karte (AtlasVanillaCrisis). Gesetzt beim Oeffnen der Station.
/// </summary>
internal static class CrisisLink
{
    public static Func<bool> Active;
    public static Func<float> Over;
    public static Func<float> TimeLeft;
    public static Action<byte, bool> SetInput;
    public static string BarWord;
    public static string[] LeverMsgs, CrankMsgs;
    public static string LeverTitle, CrankTitle, LeverGauge, CrankGauge;
    public static string Panel;                 // Tafel der Minispiele; null = Zug- bzw. Wald-Tafel
    // Eigene Grafik einer Vanilla-Krise (task_vc_<ArtKey>_*.png, tools/vc_art.py); null = Zugbilder bzw. Formen.
    public static string ArtKey;
    // Anzeige der Krisen-Grafik (Skala 0..100): Wert bei Stoerung 0 (Mitte der gruenen Zone) und bei Stoerung 100.
    public static float GaugeCalm = 50f, GaugeCrit = 100f;

    /// <summary>Datei der Krisen-Grafik, wenn es sie gibt (sonst null).</summary>
    public static string VcArt(string part)
    {
        if (string.IsNullOrEmpty(ArtKey)) return null;
        string f = $"task_vc_{ArtKey}_{part}.png";
        return AtlasAssets.TaskArtExists(f) ? f : null;
    }

    static CrisisLink() => UseRunaway();

    public static void UseRunaway()
    {
        Active = () => AtlasRunaway.Active;
        Over = () => AtlasRunaway.Over;
        TimeLeft = () => AtlasRunaway.TimeLeft;
        SetInput = AtlasRunaway.SetInput;
        BarWord = "OVERSPEED";
        LeverMsgs = new[] { "GRAB THE LEVER", "PULL HARDER", "TOO HARD", "HOLDING" };
        CrankMsgs = new[] { "WIND CLOCKWISE", "FASTER", "TOO FAST", "BRAKING" };
        LeverTitle = "PULL THE STEAM BRAKE"; CrankTitle = "WIND THE HANDBRAKE";
        LeverGauge = "OVERSPEED"; CrankGauge = "TEMPO";
        Panel = null;
        ArtKey = null;
    }
}

internal sealed class BrakeLeverMechanic : IAtlasMechanic
{
    public string Name => "brakelever";
    static readonly Vector2 Stand = new(1.5f, -0.3f);            // Bremsstand, Schlitz senkrecht
    const float SlotTop = 1.1f, SlotBottom = -1.3f;             // Hebelgriff laeuft zwischen diesen y
    static readonly Vector2 Gauge = new(-1.6f, 0.35f);
    const float GaugeR = 0.75f;

    // Krisen-Grafik (task_vc_<k>_lever/_lever_arm): der Arm dreht an der Nabe (120|212 im 240 x 300-Bild) und kippt
    // beim Ziehen zum Betrachter, dargestellt als Verkuerzung (localScale.y 1 -> ArmMin); der Griff sitzt 0,97 m ueber
    // der Nabe. Anzeige task_vc_<k>_gauge (270-Grad-Skala 0..100) mit Zeiger task_vc_<k>_needle.
    static readonly Vector2 Hub = new(Stand.x, Stand.y - 0.62f);
    const float GripLen = 0.97f, ArmMin = 0.22f;
    private float _top = SlotTop, _bottom = SlotBottom;         // Griffweg (Formen: Schlitz, Grafik: Verkuerzung)
    private Transform _arm, _needleArt;

    private float _pull;                                        // 0 oben (los) .. 1 ganz gezogen
    private bool _grab;
    private float _grace, _st;
    private Transform _grip;
    private LineRenderer _needle, _lever;
    private TextMeshPro _msg;
    private (SpriteRenderer, TextMeshPro) _bar;
    public float Progress => 1f - CrisisLink.Over() / 100f;
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        TrainKit.Panel(root);
        MatchKit.Text(root, new Vector2(0f, 2.0f), CrisisLink.LeverTitle, 2.1f, Color.white, 6);
        string vcStand = CrisisLink.VcArt("lever"), vcArm = CrisisLink.VcArt("lever_arm");
        string vcGauge = CrisisLink.VcArt("gauge"), vcNeedle = CrisisLink.VcArt("needle");
        if (vcStand != null && vcArm != null)
        {
            AtlasTaskKit.Sprite(root, vcStand, 100f, Stand, 1);
            _arm = AtlasTaskKit.Sprite(root, vcArm, 100f, Hub, 7, new Vector2(0.5f, 2f / 120f)).transform;
            _top = Hub.y + GripLen; _bottom = Hub.y + GripLen * ArmMin;
            float zMin = Mathf.Lerp(_top, _bottom, AtlasRunaway.LeverMin), zMax = Mathf.Lerp(_top, _bottom, AtlasRunaway.LeverMax);
            MatchKit.Box(root, new Vector2(Stand.x + 0.95f, (zMin + zMax) / 2f), new Vector2(0.16f, Mathf.Abs(zMax - zMin)), new Color(0.43f, 0.81f, 0.49f, 0.85f), 4);
            MatchKit.Text(root, new Vector2(Stand.x + 1.45f, (zMin + zMax) / 2f), "HOLD", 1.1f, new Color(0.6f, 1f, 0.65f), 6);
            _grip = new GameObject("grip") { layer = 5 }.transform;
            _grip.SetParent(root, false);
        }
        // Bremsstand mit Schlitz (Grafik oder Formen)
        else if (TrainKit.Art(root, "task_train_brake.png", Stand, 1) == null)
        {
            MatchKit.Box(root, Stand, new Vector2(1.5f, 2.9f), new Color(0.12f, 0.12f, 0.14f), 1);
            MatchKit.Box(root, Stand, new Vector2(1.36f, 2.76f), new Color(0.28f, 0.28f, 0.32f), 2);
            MatchKit.Box(root, Stand, new Vector2(0.14f, 2.5f), new Color(0.06f, 0.06f, 0.07f), 3);
        }
        if (_arm == null)
        {
            // Haltebereich am Schlitz markieren
            float yMin = Mathf.Lerp(SlotTop, SlotBottom, AtlasRunaway.LeverMin), yMax = Mathf.Lerp(SlotTop, SlotBottom, AtlasRunaway.LeverMax);
            MatchKit.Box(root, new Vector2(Stand.x + 0.55f, (yMin + yMax) / 2f), new Vector2(0.18f, Mathf.Abs(yMax - yMin)), new Color(0.43f, 0.81f, 0.49f, 0.8f), 4);
            MatchKit.Text(root, new Vector2(Stand.x + 1.15f, (yMin + yMax) / 2f), "HOLD", 1.1f, new Color(0.6f, 1f, 0.65f), 6);
            // Hebel: Stange vom Fusspunkt zum Griff
            _lever = MatchKit.Line(root, new Color(0.62f, 0.5f, 0.22f), 0.13f, 7);
            _grip = MatchKit.Symbol(root, Vector2.zero, 2, 0.5f, new Color(0.8f, 0.22f, 0.18f), 8).transform;
            MatchKit.Symbol(root, Vector2.zero, 2, 0.2f, new Color(1f, 0.6f, 0.55f), 9).transform.SetParent(_grip, true);
        }
        // Druckanzeige: Krisen-Grafik mit Zeiger, Zug-Grafik oder Formen
        if (vcGauge != null && vcNeedle != null)
        {
            AtlasTaskKit.Sprite(root, vcGauge, 100f, Gauge, 2);
            _needleArt = AtlasTaskKit.Sprite(root, vcNeedle, 100f, Gauge, 6, new Vector2(0.5f, 4f / 60f)).transform;
        }
        else
        {
            if (TrainKit.Art(root, "task_train_gauge.png", Gauge, 2) == null)
            {
                MatchKit.Symbol(root, Gauge, 2, GaugeR * 2.2f, new Color(0.1f, 0.1f, 0.12f), 2);
                MatchKit.Symbol(root, Gauge, 2, GaugeR * 2.0f, new Color(0.93f, 0.9f, 0.82f), 3);
                RexKit.Arc(root, Gauge, GaugeR * 0.8f, 180f, 60f, new Color(0.43f, 0.81f, 0.49f), 0.1f, 4);
                RexKit.Arc(root, Gauge, GaugeR * 0.8f, 60f, 0f, new Color(0.9f, 0.3f, 0.25f), 0.1f, 4);
            }
            _needle = MatchKit.Line(root, new Color(0.2f, 0.1f, 0.1f), 0.06f, 6);
            MatchKit.Symbol(root, Gauge, 2, 0.16f, new Color(0.88f, 0.7f, 0.3f), 7);
            MatchKit.Text(root, Gauge + new Vector2(0f, -GaugeR - 0.25f), CrisisLink.LeverGauge, 1.1f, new Color(0.8f, 0.8f, 0.85f), 6);
        }
        _msg = MatchKit.Text(root, new Vector2(-1.6f, 1.55f), "", 1.7f, Color.white, 6);
        _bar = TrainKit.Bar(root, new Color(0.45f, 0.75f, 0.95f));
        Apply();
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!CrisisLink.Active() && AtlasMinigame.DiagStep < 0) { CrisisLink.SetInput(AtlasRunaway.Brake, false); Leave = true; return; }
        var gripPos = (Vector2)_grip.localPosition;
        if (pressed && Vector2.Distance(mouse, gripPos) < 0.6f) _grab = true;
        if (!down) _grab = false;
        if (_grab)
        {
            float t = Mathf.InverseLerp(_top, _bottom, mouse.y);
            _pull = Mathf.MoveTowards(_pull, Mathf.Clamp01(t), dt * 3.5f);
        }
        else _pull = Mathf.MoveTowards(_pull, 0f, dt * 0.45f);             // kriecht zurueck
        bool inZone = _pull >= AtlasRunaway.LeverMin && _pull <= AtlasRunaway.LeverMax;
        _grace = inZone ? 0.25f : _grace - dt;
        CrisisLink.SetInput(AtlasRunaway.Brake, _grace > 0f);
        _msg.text = !_grab && _pull < 0.05f ? CrisisLink.LeverMsgs[0] : _pull < AtlasRunaway.LeverMin ? CrisisLink.LeverMsgs[1] : _pull > AtlasRunaway.LeverMax ? CrisisLink.LeverMsgs[2] : CrisisLink.LeverMsgs[3];
        _msg.color = inZone ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 0.75f, 0.35f);
        Apply();
    }

    private void Apply()
    {
        float over = Mathf.Clamp01(CrisisLink.Over() / 100f);
        if (_arm != null)
        {
            float s = Mathf.Lerp(1f, ArmMin, _pull);
            _arm.localScale = new Vector3(1f + 0.12f * _pull, s, 1f);              // naeher am Betrachter etwas breiter
            _grip.localPosition = new Vector3(Hub.x, Hub.y + GripLen * s, -0.08f);
        }
        else
        {
            float y = Mathf.Lerp(SlotTop, SlotBottom, _pull);
            var foot = new Vector2(Stand.x, SlotBottom - 0.4f);
            var grip = new Vector2(Stand.x + 0.25f * (1f - _pull), y);
            MatchKit.Set(_lever, 0, foot, 7); MatchKit.Set(_lever, 1, grip, 7);
            _grip.localPosition = new Vector3(grip.x, grip.y, -0.08f);
        }
        if (_needleArt != null)
        {
            float v = Mathf.Lerp(CrisisLink.GaugeCalm, CrisisLink.GaugeCrit, over);
            _needleArt.localRotation = Quaternion.Euler(0f, 0f, 225f - 270f * v / 100f - 90f);
        }
        else
        {
            float a = Mathf.Lerp(180f, 0f, over) * Mathf.Deg2Rad;
            MatchKit.Set(_needle, 0, Gauge, 6);
            MatchKit.Set(_needle, 1, Gauge + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * (GaugeR * 0.78f), 6);
        }
        TrainKit.SetBar(_bar, 1f - CrisisLink.Over() / 100f, $"{CrisisLink.BarWord} {Mathf.RoundToInt(CrisisLink.Over())}%     {Mathf.CeilToInt(CrisisLink.TimeLeft())}s");
    }

    // Autotest: Griff fassen und in die Mitte des Haltebereichs ziehen
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float t = Mathf.Min(1f, _st / 0.8f) * (AtlasRunaway.LeverMin + AtlasRunaway.LeverMax) / 2f;
        mouse = new Vector2(Stand.x + 0.1f, Mathf.Lerp(_top, _bottom, t));
        if (_st < 0.1f) mouse = (Vector2)_grip.localPosition;
        down = true;
    }

    public void Dispose() => CrisisLink.SetInput(AtlasRunaway.Brake, false);
}

// ================================================================== Handbremse

internal sealed class HandbrakeMechanic : IAtlasMechanic
{
    public string Name => "handbrake";
    static readonly Vector2 C = new(0.9f, -0.2f);
    const float R = 1.05f;
    static readonly Vector2 G = new(-2.0f, 0.6f);
    const float GaugeR = 0.65f, GaugeMax = 2.2f;

    private float _ang, _omega, _last, _grace, _st;
    private bool _grab;
    private Transform _wheel;
    private LineRenderer _needle;
    private readonly LineRenderer[] _spokes = new LineRenderer[6];
    private TextMeshPro _msg;
    private (SpriteRenderer, TextMeshPro) _bar;
    public float Progress => 1f - CrisisLink.Over() / 100f;
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        TrainKit.Panel(root);
        MatchKit.Text(root, new Vector2(0f, 2.0f), CrisisLink.CrankTitle, 2.1f, Color.white, 6);
        string vcWheel = CrisisLink.VcArt("wheel");                 // Krisen-Grafik (220 x 220, Mitte = Drehpunkt)
        var art = vcWheel != null ? AtlasTaskKit.Sprite(root, vcWheel, 100f, C, 3) : TrainKit.Art(root, "task_train_wheel.png", C, 3);
        if (art != null) _wheel = art.transform;
        else
        {
            MatchKit.Symbol(root, C, 2, R * 2.3f, new Color(0.12f, 0.12f, 0.14f), 1);
            MatchKit.Symbol(root, C, 2, R * 2.1f, new Color(0.72f, 0.56f, 0.24f), 2);
            MatchKit.Symbol(root, C, 2, R * 1.75f, new Color(0.14f, 0.12f, 0.1f), 3);
            var w = new GameObject("wheel") { layer = 5 };
            w.transform.SetParent(root, false);
            w.transform.localPosition = new Vector3(C.x, C.y, -0.05f);
            _wheel = w.transform;
            for (int i = 0; i < 6; i++)
            {
                _spokes[i] = MatchKit.Line(_wheel, new Color(0.72f, 0.56f, 0.24f), 0.1f, 5);
                float a = i * 60f * Mathf.Deg2Rad;
                MatchKit.Set(_spokes[i], 0, Vector2.zero, 5);
                MatchKit.Set(_spokes[i], 1, new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * R * 0.95f, 5);
            }
            MatchKit.Symbol(_wheel, Vector2.zero, 2, 0.4f, new Color(0.85f, 0.68f, 0.32f), 6);
        }
        var arrow = MatchKit.Symbol(root, C + new Vector2(0f, R + 0.35f), 0, 0.28f, new Color(1f, 1f, 1f, 0.55f), 3);
        arrow.transform.localEulerAngles = new Vector3(0, 0, -90f);
        float A(float w) => 180f - Mathf.Clamp(w, 0f, GaugeMax) / GaugeMax * 180f;
        RexKit.Arc(root, G, GaugeR, A(0f), A(AtlasRunaway.CrankMin), new Color(0.35f, 0.38f, 0.45f), 0.13f, 4);
        RexKit.Arc(root, G, GaugeR, A(AtlasRunaway.CrankMin), A(AtlasRunaway.CrankMax), new Color(0.43f, 0.81f, 0.49f), 0.13f, 4);
        RexKit.Arc(root, G, GaugeR, A(AtlasRunaway.CrankMax), A(GaugeMax), new Color(0.9f, 0.3f, 0.25f), 0.13f, 4);
        _needle = MatchKit.Line(root, new Color(0.96f, 0.94f, 0.89f), 0.06f, 6);
        MatchKit.Symbol(root, G, 2, 0.16f, new Color(0.88f, 0.7f, 0.3f), 7);
        MatchKit.Text(root, G + new Vector2(0f, -0.2f), CrisisLink.CrankGauge, 1.1f, new Color(0.8f, 0.8f, 0.85f), 6);
        _msg = MatchKit.Text(root, new Vector2(-2.0f, 1.5f), "", 1.7f, Color.white, 6);
        _bar = TrainKit.Bar(root, new Color(0.45f, 0.75f, 0.95f));
        Apply();
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!CrisisLink.Active() && AtlasMinigame.DiagStep < 0) { CrisisLink.SetInput(AtlasRunaway.Handbrake, false); Leave = true; return; }
        var d = mouse - C;
        float dist = d.magnitude;
        if (pressed && dist > 0.2f && dist < R + 0.5f) { _grab = true; _last = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg; }
        if (!down) _grab = false;
        if (_grab)
        {
            float a = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg;
            float delta = Mathf.DeltaAngle(_last, a);
            _last = a;
            _ang += delta;
            float inst = -delta / 360f / Mathf.Max(dt, 0.001f);                  // im Uhrzeigersinn positiv
            _omega += (inst - _omega) * (1f - Mathf.Exp(-dt / 0.28f));
        }
        else { _omega *= Mathf.Exp(-1.6f * dt); _ang -= _omega * 360f * dt; }
        bool inZone = _omega >= AtlasRunaway.CrankMin && _omega <= AtlasRunaway.CrankMax;
        _grace = inZone ? 0.25f : _grace - dt;
        CrisisLink.SetInput(AtlasRunaway.Handbrake, _grace > 0f);
        _msg.text = _omega < 0.05f ? CrisisLink.CrankMsgs[0] : _omega < AtlasRunaway.CrankMin ? CrisisLink.CrankMsgs[1] : _omega > AtlasRunaway.CrankMax ? CrisisLink.CrankMsgs[2] : CrisisLink.CrankMsgs[3];
        _msg.color = inZone ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 0.75f, 0.35f);
        Apply();
    }

    private void Apply()
    {
        if (_wheel != null) _wheel.localRotation = Quaternion.Euler(0f, 0f, _ang);
        float na = (180f - Mathf.Clamp(_omega, 0f, GaugeMax) / GaugeMax * 180f) * Mathf.Deg2Rad;
        MatchKit.Set(_needle, 0, G, 6);
        MatchKit.Set(_needle, 1, G + new Vector2(Mathf.Cos(na), Mathf.Sin(na)) * (GaugeR - 0.05f), 6);
        TrainKit.SetBar(_bar, 1f - CrisisLink.Over() / 100f, $"{CrisisLink.BarWord} {Mathf.RoundToInt(CrisisLink.Over())}%     {Mathf.CeilToInt(CrisisLink.TimeLeft())}s");
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float a = (90f - _st * 1.0f * 360f) * Mathf.Deg2Rad;
        mouse = C + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * R * 0.9f;
        down = _st > 0.05f;
    }

    public void Dispose() => CrisisLink.SetInput(AtlasRunaway.Handbrake, false);
}

// ================================================================== Dachluke

internal sealed class HatchCrankMechanic : IAtlasMechanic
{
    public string Name => "hatchcrank";
    static readonly Vector2 Hatch = new(-0.6f, 0.2f);
    static readonly Vector2 Crank = new(2.3f, -0.6f);
    const float Arm = 0.7f;

    private readonly int _hatch = AtlasSmoke.PendingHatch;
    private float _turned, _ang = 90f, _last, _doneAt, _st;
    private bool _grab, _opened;
    private Transform _lid, _knob;
    private LineRenderer _arm;
    private SpriteRenderer _artClosed, _artOpen;
    private TextMeshPro _msg;
    private (SpriteRenderer, TextMeshPro) _bar;
    public float Progress => Mathf.Clamp01(_turned / (AtlasSmoke.CrankTurns * 360f));
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        TrainKit.Panel(root);
        MatchKit.Text(root, new Vector2(0f, 2.0f), "OPEN THE ROOF HATCH", 2.1f, Color.white, 6);
        _artClosed = TrainKit.Art(root, "task_train_hatch.png", Hatch, 2);
        _artOpen = TrainKit.Art(root, "task_train_hatch_open.png", Hatch, 2);
        if (_artOpen != null) _artOpen.gameObject.SetActive(false);
        if (_artClosed == null)
        {
            MatchKit.Box(root, Hatch, new Vector2(2.6f, 2.0f), new Color(0.1f, 0.1f, 0.12f), 1);
            MatchKit.Box(root, Hatch, new Vector2(2.4f, 1.8f), new Color(0.05f, 0.06f, 0.12f), 2);      // Nachthimmel
            for (int i = 0; i < 12; i++)
                MatchKit.Symbol(root, Hatch + new Vector2(Random.Range(-1.1f, 1.1f), Random.Range(-0.8f, 0.8f)), 2, 0.05f, new Color(1f, 1f, 0.9f), 3);
            var lid = new GameObject("lid") { layer = 5 };
            lid.transform.SetParent(root, false);
            lid.transform.localPosition = new Vector3(Hatch.x, Hatch.y - 0.9f, -0.04f);               // Scharnier unten
            _lid = lid.transform;
            MatchKit.Box(_lid, new Vector2(0f, 0.9f), new Vector2(2.4f, 1.8f), new Color(0.45f, 0.27f, 0.15f), 4);
            MatchKit.Box(_lid, new Vector2(0f, 0.9f), new Vector2(2.2f, 1.6f), new Color(0.55f, 0.35f, 0.2f), 5);
            MatchKit.Box(_lid, new Vector2(0f, 0.9f), new Vector2(0.12f, 1.6f), new Color(0.72f, 0.56f, 0.24f), 6);
        }
        // Kurbel
        MatchKit.Symbol(root, Crank, 2, 0.5f, new Color(0.2f, 0.2f, 0.23f), 5);
        _arm = MatchKit.Line(root, new Color(0.72f, 0.56f, 0.24f), 0.12f, 6);
        _knob = MatchKit.Symbol(root, Vector2.zero, 2, 0.4f, new Color(0.8f, 0.22f, 0.18f), 7).transform;
        var arrow = MatchKit.Symbol(root, Crank + new Vector2(0f, Arm + 0.3f), 0, 0.26f, new Color(1f, 1f, 1f, 0.55f), 5);
        arrow.transform.localEulerAngles = new Vector3(0, 0, -90f);
        _msg = MatchKit.Text(root, new Vector2(2.3f, 1.2f), "", 1.6f, Color.white, 6);
        _bar = TrainKit.Bar(root, new Color(0.95f, 0.75f, 0.35f));
        Apply();
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!AtlasSmoke.Active && AtlasMinigame.DiagStep < 0) { Leave = true; return; }
        if (_opened)
        {
            if (Time.time >= _doneAt) Leave = true;
            Apply();
            return;
        }
        var d = mouse - Crank;
        float dist = d.magnitude;
        if (pressed && dist > 0.15f && dist < Arm + 0.5f) { _grab = true; _last = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg; }
        if (!down) _grab = false;
        if (_grab)
        {
            float a = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg;
            float delta = Mathf.DeltaAngle(_last, a);
            _last = a;
            if (delta < 0f) { _ang += delta; _turned -= delta; }                  // nur im Uhrzeigersinn zaehlt
        }
        if (_turned >= AtlasSmoke.CrankTurns * 360f)
        {
            _opened = true;
            _doneAt = Time.time + 0.8f;
            AtlasSmoke.OpenHatch(_hatch);
        }
        _msg.text = _opened ? "OPEN" : _grab ? "KEEP WINDING" : "WIND CLOCKWISE";
        _msg.color = _opened ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 0.85f, 0.45f);
        Apply();
    }

    private void Apply()
    {
        float a = _ang * Mathf.Deg2Rad;
        var k = Crank + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Arm;
        MatchKit.Set(_arm, 0, Crank, 6); MatchKit.Set(_arm, 1, k, 6);
        _knob.localPosition = new Vector3(k.x, k.y, -0.08f);
        float t = Progress;
        if (_lid != null) _lid.localRotation = Quaternion.Euler(0f, 0f, 0f) * Quaternion.AngleAxis(-75f * t, Vector3.right);
        if (_artClosed != null && _artOpen != null)
        {
            bool open = t >= 0.999f;
            if (_artClosed.gameObject.activeSelf == open) _artClosed.gameObject.SetActive(!open);
            if (_artOpen.gameObject.activeSelf != open) _artOpen.gameObject.SetActive(open);
        }
        TrainKit.SetBar(_bar, t, $"HATCH {Mathf.RoundToInt(t * 100f)}%     SMOKE {Mathf.CeilToInt(AtlasSmoke.TimeLeft)}s");
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float a = (90f - _st * 1.4f * 360f) * Mathf.Deg2Rad;
        mouse = Crank + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Arm;
        down = _st > 0.05f;
    }

    public void Dispose() { }
}
