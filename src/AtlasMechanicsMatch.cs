// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Baustein "Zuordnen" (docs/TASK_KONZEPT.md): Objekte in Faecher ziehen, Kabel zu Buchsen,
// dazu die kurzen Zweitschritte (Hebel halten, Schalter umlegen) und das Lichtleiter-Puzzle.
//
//   till     Close Out the Till       (Museum, Swipe Card)
//   bins     Empty the Bins           (Museum, Empty Garbage: sortieren, dann Hebel)
//   compost  Haul the Compost         (Wald,   Empty Garbage: sortieren, dann Hebel)
//   fuse     Restore Exhibit Power    (Museum, Divert Power: Sicherung, dann Saalschalter)
//   route    Route Generator Power    (Wald,   Divert Power: Kabel stecken, dann Kippschalter)
//   light    Repair Showcase Lighting (Museum, Fix Wiring: Lichtleiter drehen, je Schritt neu)

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

/// <summary>Was eine Mechanik ueber ihren Task wissen darf.</summary>
internal sealed class AtlasTaskCtx
{
    public NormalPlayerTask Task;
    public int Step;
    public string Map;                  // "museum" / "wald"
    public SystemTypes Target;          // Divert Power: Zielraum
}

/// <summary>Scripted input for Simulate: tap, drag, hold.</summary>
internal sealed class InputScript
{
    private readonly List<(Vector2 a, Vector2 b, float t, bool down)> _segs = new();
    private int _i;
    private float _e;
    public bool Empty => _segs.Count == 0;
    public bool Finished => _i >= _segs.Count;

    public InputScript Seg(Vector2 a, Vector2 b, float t, bool down) { _segs.Add((a, b, t, down)); return this; }
    public InputScript Wait(Vector2 p, float t) => Seg(p, p, t, false);
    public InputScript Tap(Vector2 p) => Seg(p, p, 0.06f, false).Seg(p, p, 0.08f, true).Seg(p, p, 0.12f, false);
    public InputScript Drag(Vector2 a, Vector2 b, float t = 0.35f) =>
        Seg(a, a, 0.06f, false).Seg(a, a, 0.06f, true).Seg(a, b, t, true).Seg(b, b, 0.05f, true).Seg(b, b, 0.12f, false);
    public InputScript Hold(Vector2 p, float t) => Seg(p, p, 0.06f, false).Seg(p, p, t, true).Seg(p, p, 0.1f, false);

    /// <summary>Kreisbewegung um c mit Radius r, von a0 um da Grad (positiv = gegen den Uhrzeigersinn).</summary>
    public InputScript Arc(Vector2 c, float r, float a0, float da, float t)
    {
        Vector2 P(float a) => c + new Vector2(Mathf.Cos(a * Mathf.Deg2Rad), Mathf.Sin(a * Mathf.Deg2Rad)) * r;
        int n = Mathf.Max(1, Mathf.CeilToInt(Mathf.Abs(da) / 12f));
        Seg(P(a0), P(a0), 0.05f, false).Seg(P(a0), P(a0), 0.05f, true);
        for (int i = 0; i < n; i++) Seg(P(a0 + da * i / n), P(a0 + da * (i + 1) / n), t / n, true);
        var e = P(a0 + da);
        return Seg(e, e, 0.05f, true).Seg(e, e, 0.1f, false);
    }

    /// <summary>Mit gedrueckter Taste durch mehrere Punkte ziehen.</summary>
    public InputScript Path(IList<Vector2> pts, float perSeg)
    {
        if (pts.Count == 0) return this;
        Seg(pts[0], pts[0], 0.05f, false).Seg(pts[0], pts[0], 0.06f, true);
        for (int i = 1; i < pts.Count; i++) Seg(pts[i - 1], pts[i], perSeg, true);
        return Seg(pts[^1], pts[^1], 0.05f, true).Seg(pts[^1], pts[^1], 0.1f, false);
    }

    public void Next(float dt, out Vector2 mouse, out bool down)
    {
        if (Finished) { var l = _segs.Count > 0 ? _segs[^1].b : Vector2.zero; mouse = l; down = false; return; }
        var s = _segs[_i];
        _e += dt;
        float k = s.t <= 0f ? 1f : Mathf.Clamp01(_e / s.t);
        mouse = Vector2.Lerp(s.a, s.b, k);
        down = s.down;
        if (_e >= s.t) { _i++; _e = 0f; }
    }
}

internal static class MatchKit
{
    public static TextMeshPro Text(Transform parent, Vector2 pos, string text, float size, Color color, int order)
    {
        var go = new GameObject("text") { layer = 5 };
        go.transform.SetParent(parent, false);
        go.transform.localPosition = new Vector3(pos.x, pos.y, -order * 0.01f);
        var t = go.AddComponent<TextMeshPro>();
        TextMeshPro src = null;
        try { src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null; } catch { }
        if (src == null) src = Object.FindObjectOfType<TextMeshPro>();
        if (src != null) { t.font = src.font; t.fontSharedMaterial = src.fontSharedMaterial; }
        t.text = text;
        t.fontSize = size;
        t.color = color;
        t.alignment = TextAlignmentOptions.Center;
        t.enableWordWrapping = false;
        t.rectTransform.sizeDelta = new Vector2(6f, 1f);
        var mr = go.GetComponent<MeshRenderer>();
        if (mr != null) mr.sortingOrder = order;
        return t;
    }

    public static string RoomName(SystemTypes s)
    {
        try { return TranslationController.Instance.GetString(s); } catch { return s.ToString(); }
    }

    public static bool In(Vector2 p, Vector2 c, Vector2 half) => Mathf.Abs(p.x - c.x) <= half.x && Mathf.Abs(p.y - c.y) <= half.y;

    public static void SetZ(Transform t, int order) { var p = t.localPosition; t.localPosition = new Vector3(p.x, p.y, -order * 0.01f); }

    private static Material _lineMat;
    public static LineRenderer Line(Transform parent, Color c, float width, int order, int points = 2)
    {
        var go = new GameObject("line") { layer = 5 };
        go.transform.SetParent(parent, false);
        var lr = go.AddComponent<LineRenderer>();
        lr.useWorldSpace = false;
        lr.positionCount = points;
        lr.startWidth = lr.endWidth = width;
        if (_lineMat == null) _lineMat = new Material(Shader.Find("Sprites/Default")) { hideFlags = HideFlags.HideAndDontSave };
        lr.sharedMaterial = _lineMat;
        lr.startColor = lr.endColor = c;
        lr.sortingOrder = order;
        lr.numCapVertices = 4;
        return lr;
    }

    public static void Set(LineRenderer lr, int i, Vector2 p, int order) => lr.SetPosition(i, new Vector3(p.x, p.y, -order * 0.01f));

    /// <summary>Farbiges Rechteck (Balken, Fuellstand) aus einer weissen Textur.</summary>
    public static SpriteRenderer Box(Transform parent, Vector2 center, Vector2 size, Color c, int order)
    {
        var sr = AtlasTaskKit.Sprite(parent, "task_white.png", 100f, center, order);
        sr.transform.localScale = new Vector3(size.x / 0.16f, size.y / 0.16f, 1f);
        sr.color = c;
        return sr;
    }

    /// <summary>Sichtbarer Beweis fuer andere Spieler (Visual Tasks), wie die Vanilla-Minispiele.</summary>
    public static void PlayVisual(TaskTypes t)
    {
        try { PlayerControl.LocalPlayer?.RpcPlayAnimation((byte)t); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Task] visual {t}: {e.Message}"); }
    }
}

/// <summary>Drehen per Kreisbewegung um einen Mittelpunkt (Baustein "Drehen").</summary>
internal sealed class Rotary
{
    public Vector2 C;
    public float R0, R1;
    public float Delta { get; private set; }      // Grad in diesem Frame, positiv = gegen den Uhrzeigersinn
    public bool Active { get; private set; }
    private float _last;
    public Rotary(Vector2 c, float r0, float r1) { C = c; R0 = r0; R1 = r1; }
    private float Ang(Vector2 m) => Mathf.Atan2(m.y - C.y, m.x - C.x) * Mathf.Rad2Deg;
    public void Tick(Vector2 m, bool down, bool pressed)
    {
        Delta = 0f;
        float d = Vector2.Distance(m, C);
        if (pressed && d >= R0 && d <= R1) { Active = true; _last = Ang(m); }
        if (!down) Active = false;
        if (!Active) return;
        float a = Ang(m);
        Delta = Mathf.DeltaAngle(_last, a);
        _last = a;
    }
}

// ================================================================== Close Out the Till

internal sealed class TillMechanic : IAtlasMechanic
{
    public string Name => "till";
    private static readonly (string File, int Value, Vector2 Pos, float R)[] Money =
    {
        ("task_coin1.png", 1, new(1.2f, 1.55f), 0.42f), ("task_coin2.png", 2, new(2.4f, 1.55f), 0.42f),
        ("task_note5.png", 5, new(1.8f, 0.55f), 0.8f), ("task_note10.png", 10, new(1.8f, -0.45f), 0.8f),
        ("task_note20.png", 20, new(1.8f, -1.45f), 0.8f),
    };
    static readonly Vector2 TrayC = new(-1.05f, -1.15f), TrayHalf = new(1.7f, 0.72f);

    private Transform _root;
    private SpriteRenderer _tray;
    private TextMeshPro _sumText;
    private readonly List<GameObject> _inTray = new();
    private GameObject _dragging;
    private int _dragValue, _target, _sum;
    private float _red;
    private InputScript _script;
    public float Progress => Mathf.Clamp01(_sum / (float)Mathf.Max(1, _target));
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _root = root;
        AtlasTaskKit.Sprite(root, "task_shop_panel.png", 100f, Vector2.zero, 0);
        _tray = AtlasTaskKit.Sprite(root, "task_tray.png", 100f, TrayC, 1);
        AtlasTaskKit.Sprite(root, "task_receipt.png", 100f, new Vector2(-2.3f, 1.05f), 1);
        foreach (var m in Money) AtlasTaskKit.Sprite(root, m.File, 100f, m.Pos, 2);
        do _target = Random.Range(13, 40); while (_target % 5 == 0);
        MatchKit.Text(root, new Vector2(-2.3f, 1.75f), "TOTAL", 2.2f, new Color(0.2f, 0.2f, 0.22f), 3);
        MatchKit.Text(root, new Vector2(-2.3f, 1.25f), _target.ToString(), 4.2f, new Color(0.1f, 0.1f, 0.12f), 3);
        _sumText = MatchKit.Text(root, new Vector2(-2.3f, 0.5f), "0", 3f, new Color(0.25f, 0.45f, 0.3f), 3);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        _tray.color = Color.Lerp(Color.white, new Color(1f, 0.5f, 0.5f), _red);
        if (Done) return;
        if (pressed && _dragging == null)
        {
            foreach (var m in Money)
                if (Vector2.Distance(mouse, m.Pos) < m.R)
                {
                    _dragging = AtlasTaskKit.Sprite(_root, m.File, 100f, mouse, 6).gameObject;
                    _dragValue = m.Value;
                    break;
                }
        }
        if (_dragging != null)
        {
            _dragging.transform.localPosition = new Vector3(mouse.x, mouse.y, _dragging.transform.localPosition.z);
            if (!down)
            {
                if (MatchKit.In(mouse, TrayC, TrayHalf))
                {
                    MatchKit.SetZ(_dragging.transform, 2 + _inTray.Count % 3);
                    _dragging.GetComponent<SpriteRenderer>().sortingOrder = 2 + _inTray.Count % 3;
                    _inTray.Add(_dragging);
                    _sum += _dragValue;
                    if (_sum > _target)
                    {
                        // zu viel: die Rueckgeld-Klappe gibt alles zurueck, neu zaehlen
                        foreach (var g in _inTray) Object.Destroy(g);
                        _inTray.Clear();
                        _sum = 0; _red = 1f;
                    }
                    else if (_sum == _target) Done = true;
                }
                else Object.Destroy(_dragging);
                _dragging = null;
                _sumText.text = _sum.ToString();
            }
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            int rest = _target;
            for (int i = Money.Length - 1; i >= 0; i--)
                while (rest >= Money[i].Value)
                {
                    rest -= Money[i].Value;
                    _script.Drag(Money[i].Pos, TrayC + new Vector2(Random.Range(-1f, 1f), Random.Range(-0.4f, 0.4f)));
                }
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== sortieren (Empty the Bins / Haul the Compost)

internal sealed class SortMechanic : IAtlasMechanic
{
    public string Name => "sort";
    private readonly (string Key, string Label, string[] Items)[] _bins;
    private readonly string _panel;
    private readonly List<(Transform T, int Bin, Vector2 Home)> _items = new();
    private readonly List<(SpriteRenderer R, Vector2 C)> _binRends = new();
    private int _drag = -1, _placed, _total;
    private Vector2 _grabOff;
    private float[] _red;
    private InputScript _script;
    public float Progress => _total == 0 ? 0f : _placed / (float)_total;
    public bool Done { get; private set; }

    private readonly bool _grate;

    public SortMechanic(bool wald, bool grate = false)
    {
        _grate = grate;
        _panel = wald ? "task_wald_panel.png" : "task_museum_panel.png";
        _bins = grate
            ? new[] { ("compost", "BUCKET", new[] { "leaves", "twig" }) }
            : wald
            ? new[] { ("compost", "COMPOST", new[] { "apple", "peel", "egg", "leaves" }), ("sack", "PACKAGING", new[] { "can", "carton", "wrapper" }) }
            : new[] { ("paper", "PAPER", new[] { "brochure", "ticket" }), ("glass", "GLASS", new[] { "bottle", "jar" }), ("rest", "OTHER", new[] { "wrapper", "apple" }) };
    }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _panel, 100f, Vector2.zero, 0);
        if (_grate) AtlasTaskKit.Sprite(root, "task_grate.png", 100f, new Vector2(-0.8f, 0.35f), 1);
        float gap = _bins.Length == 3 ? 2.2f : 2.6f;
        for (int b = 0; b < _bins.Length; b++)
        {
            var c = _grate ? new Vector2(2.55f, -1.2f) : new Vector2((b - (_bins.Length - 1) / 2f) * gap, -1.3f);
            _binRends.Add((AtlasTaskKit.Sprite(root, $"task_bin_{_bins[b].Key}.png", 100f, c, 2), c));
            MatchKit.Text(root, c + new Vector2(0f, -0.2f), _bins[b].Label, 1.8f, Color.white, 3);
        }
        _red = new float[_bins.Length];
        // vier Teile, jede Tonne mindestens eins
        var pick = new List<(string item, int bin)>();
        for (int b = 0; b < _bins.Length; b++) pick.Add((_bins[b].Items[Random.Range(0, _bins[b].Items.Length)], b));
        int count = _grate ? 6 : 4;
        while (pick.Count < count) { int b = Random.Range(0, _bins.Length); pick.Add((_bins[b].Items[Random.Range(0, _bins[b].Items.Length)], b)); }
        for (int i = 0; i < pick.Count; i++)
        {
            var home = _grate
                ? new Vector2(-2.9f + (i % 3) * 1.1f + Random.Range(-0.2f, 0.2f), 1.0f - (i / 3) * 1.2f + Random.Range(-0.2f, 0.2f))
                : new Vector2(-2.4f + i * 1.6f + Random.Range(-0.2f, 0.2f), 1.25f + Random.Range(-0.3f, 0.3f));
            var r = AtlasTaskKit.Sprite(root, $"task_trash_{pick[i].item}.png", 100f, home, 4 + i);
            r.transform.localEulerAngles = new Vector3(0, 0, Random.Range(-35f, 35f));
            r.transform.localScale = Vector3.one * 1.25f;
            _items.Add((r.transform, pick[i].bin, home));
        }
        _total = _items.Count;
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        for (int b = 0; b < _red.Length; b++)
        {
            _red[b] = Mathf.Max(0f, _red[b] - dt * 2f);
            _binRends[b].R.color = Color.Lerp(Color.white, new Color(1f, 0.45f, 0.45f), _red[b]);
        }
        if (Done) return;
        if (pressed && _drag < 0)
        {
            float best = 0.55f;
            for (int i = 0; i < _items.Count; i++)
            {
                if (_items[i].T == null) continue;
                float d = Vector2.Distance(mouse, _items[i].T.localPosition);
                if (d < best) { best = d; _drag = i; _grabOff = (Vector2)_items[i].T.localPosition - mouse; }
            }
        }
        if (_drag < 0) return;
        var it = _items[_drag];
        var p = mouse + _grabOff;
        it.T.localPosition = new Vector3(p.x, p.y, it.T.localPosition.z);
        if (down) return;
        int hit = -1;
        for (int b = 0; b < _binRends.Count; b++) if (MatchKit.In(p, _binRends[b].C, new Vector2(0.85f, 1.1f))) hit = b;
        if (hit == it.Bin)
        {
            Object.Destroy(it.T.gameObject);
            _items[_drag] = (null, it.Bin, it.Home);
            if (++_placed >= _total) Done = true;
        }
        else
        {
            if (hit >= 0) _red[hit] = 1f;
            it.T.localPosition = new Vector3(it.Home.x, it.Home.y, it.T.localPosition.z);
        }
        _drag = -1;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var it in _items) _script.Drag(it.Home, _binRends[it.Bin].C + new Vector2(0f, 0.3f), 0.4f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Hebel halten (Zweitschritt Empty Garbage)

internal sealed class HoldLeverMechanic : IAtlasMechanic
{
    public string Name => "lever";
    const float Need = 2.2f;
    static readonly Vector2 Pivot = new(-2.5f, -1.6f);
    private readonly string _panel;
    private Transform _lever, _container;
    private TextMeshPro _pct;
    private float _held, _angle;
    private Vector2 _c0;
    private InputScript _script;
    public float Progress => Mathf.Clamp01(_held / Need);
    public bool Done { get; private set; }

    public HoldLeverMechanic(bool wald) { _panel = wald ? "task_wald_panel.png" : "task_museum_panel.png"; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _panel, 100f, Vector2.zero, 0);
        _c0 = new Vector2(0.7f, -0.4f);
        _container = AtlasTaskKit.Sprite(root, "task_container.png", 100f, _c0, 2).transform;
        _lever = AtlasTaskKit.Sprite(root, "task_lever.png", 100f, Pivot, 3, new Vector2(0.5f, 20f / 230f)).transform;
        _pct = MatchKit.Text(root, new Vector2(0.7f, 1.7f), "HOLD THE LEVER", 2.6f, Color.white, 4);
    }

    private Vector2 Knob => Pivot + (Vector2)(Quaternion.Euler(0, 0, _angle) * new Vector3(0f, 2.0f, 0f));

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        bool holding = down && Vector2.Distance(mouse, Pivot) < 2.6f && mouse.x < Pivot.x + 1.4f;
        _angle = Mathf.MoveTowards(_angle, holding ? -40f : 0f, 220f * dt);
        _lever.localEulerAngles = new Vector3(0, 0, _angle);
        if (Done) return;
        if (holding && _angle <= -35f)
        {
            _held += dt;
            var s = new Vector2(Mathf.Sin(Time.time * 55f), Mathf.Cos(Time.time * 43f)) * 0.05f;
            _container.localPosition = new Vector3(_c0.x + s.x, _c0.y + s.y, _container.localPosition.z);
        }
        else _container.localPosition = new Vector3(_c0.x, _c0.y, _container.localPosition.z);
        _pct.text = _held > 0f ? $"{Mathf.RoundToInt(Progress * 100f)}%" : "HOLD THE LEVER";
        if (_held >= Need) { Done = true; MatchKit.PlayVisual(TaskTypes.EmptyGarbage); }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Hold(Pivot + new Vector2(0f, 1.9f), Need + 0.8f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Sicherung tauschen (Restore Exhibit Power 1)

internal sealed class FuseMechanic : IAtlasMechanic
{
    public string Name => "fuse";
    static readonly Vector2 Box = new(-0.8f, 0f), Tray = new(2.7f, -0.2f);
    private Transform _root;
    private readonly List<SpriteRenderer> _slots = new();
    private readonly List<Vector2> _pos = new();
    private int _dead;
    private bool _removed, _dragging;
    private Transform _new, _old;
    private float _oldT, _shake;
    private int _shakeIdx = -1;
    private InputScript _script;
    public float Progress => _removed ? 0.5f : 0f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _root = root;
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_fusebox.png", 100f, Box, 1);
        _dead = Random.Range(0, 12);
        for (int r = 0; r < 3; r++)
            for (int k = 0; k < 4; k++)
            {
                var p = Box + new Vector2((90 + k * 126 - 280) / 100f, (200 - (90 + r * 110)) / 100f);
                _pos.Add(p);
                _slots.Add(AtlasTaskKit.Sprite(root, _slots.Count == _dead ? "task_fuse_dead.png" : "task_fuse_ok.png", 100f, p, 2));
            }
        _new = AtlasTaskKit.Sprite(root, "task_fuse_new.png", 100f, Tray, 5).transform;
        MatchKit.Text(root, new Vector2(2.7f, 1.2f), "SPARE", 2.2f, Color.white, 3);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _shake = Mathf.Max(0f, _shake - dt * 3f);
        if (_shakeIdx >= 0)
        {
            var p = _pos[_shakeIdx];
            _slots[_shakeIdx].transform.localPosition = new Vector3(p.x + Mathf.Sin(Time.time * 60f) * 0.04f * _shake, p.y, -0.02f);
        }
        if (_old != null)
        {
            _oldT += dt;
            _old.localPosition += new Vector3(1.8f * dt, 3f * dt - 9f * _oldT * dt, 0f);
            _old.localEulerAngles = new Vector3(0, 0, _oldT * 400f);
            if (_oldT > 1f) { Object.Destroy(_old.gameObject); _old = null; }
        }
        if (Done) return;
        if (pressed)
        {
            for (int i = 0; i < _pos.Count; i++)
            {
                if (!MatchKit.In(mouse, _pos[i], new Vector2(0.34f, 0.48f))) continue;
                if (i == _dead && !_removed) { _removed = true; _old = _slots[i].transform; _slots[i] = null; }
                else if (_slots[i] != null) { _shakeIdx = i; _shake = 1f; }
            }
            if (_removed && Vector2.Distance(mouse, _new.localPosition) < 0.5f) _dragging = true;
        }
        if (!_dragging) return;
        _new.localPosition = new Vector3(mouse.x, mouse.y, _new.localPosition.z);
        if (down) return;
        _dragging = false;
        if (Vector2.Distance(mouse, _pos[_dead]) < 0.5f)
        {
            _new.localPosition = new Vector3(_pos[_dead].x, _pos[_dead].y, -0.02f);
            foreach (var s in _slots) if (s != null) s.color = new Color(1f, 1f, 0.8f);
            Done = true;
        }
        else _new.localPosition = new Vector3(Tray.x, Tray.y, _new.localPosition.z);
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Tap(_pos[_dead]).Wait(_pos[_dead], 0.2f).Drag(Tray, _pos[_dead], 0.45f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Schalter umlegen (Zweitschritt Divert Power)

internal sealed class SwitchMechanic : IAtlasMechanic
{
    public string Name => "switch";
    static readonly Vector2 Pivot = new(-1.6f, -0.2f);
    private readonly string _panel;
    private Transform _lever;
    private readonly List<SpriteRenderer> _lamps = new();
    private Sprite _on;
    private float _angle = 180f, _lampT = -1f;              // 0 = oben (ON), +-180 = unten (OFF)
    private bool _grab;
    private InputScript _script;
    public float Progress => _lampT < 0f ? 0f : 0.5f;
    public bool Done { get; private set; }

    public SwitchMechanic(bool wald) { _panel = wald ? "task_wald_panel.png" : "task_steel_panel.png"; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _panel, 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_switch_plate.png", 100f, Pivot, 1);
        _lever = AtlasTaskKit.Sprite(root, "task_switch_lever.png", 100f, Pivot, 2, new Vector2(0.5f, 10f / 150f)).transform;
        _on = AtlasAssets.TaskSprite("task_lamp_on.png", 100f, new Vector2(0.5f, 0.5f));
        for (int i = 0; i < 5; i++)
            _lamps.Add(AtlasTaskKit.Sprite(root, "task_lamp_off.png", 100f, new Vector2(0.4f + i * 0.72f, -0.2f), 2));
        string room = ctx.Target != 0 ? MatchKit.RoomName(ctx.Target) : "";
        MatchKit.Text(root, new Vector2(1.85f, 1.3f), room.ToUpperInvariant(), 3f, Color.white, 3);
    }

    private Vector2 Tip => Pivot + (Vector2)(Quaternion.Euler(0, 0, _angle) * new Vector3(0f, 1.3f, 0f));

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (_lampT >= 0f)
        {
            _lampT += dt;
            int n = Mathf.Min(_lamps.Count, (int)(_lampT / 0.14f));
            for (int i = 0; i < n; i++) _lamps[i].sprite = _on;
            if (n >= _lamps.Count) Done = true;
            return;
        }
        if (pressed && Vector2.Distance(mouse, Tip) < 0.6f) _grab = true;
        if (!down) _grab = false;
        if (_grab)
        {
            var d = mouse - Pivot;
            // ueber links oder rechts hochziehen, beides geht
            _angle = Mathf.DeltaAngle(0f, Mathf.Atan2(-d.x, d.y) * Mathf.Rad2Deg);
        }
        else if (Mathf.Abs(_angle) > 20f) _angle = Mathf.MoveTowards(_angle, _angle >= 0f ? 180f : -180f, 400f * dt);
        _lever.localEulerAngles = new Vector3(0, 0, _angle);
        if (Mathf.Abs(_angle) <= 20f) { _angle = 0f; _lever.localEulerAngles = Vector3.zero; _lampT = 0f; }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Drag(Pivot + new Vector2(0f, -1.3f), Pivot + new Vector2(0.3f, 1.3f), 0.5f).Wait(Pivot, 1.2f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Kabel stecken (Route Generator Power 1)

internal sealed class RouteMechanic : IAtlasMechanic
{
    public string Name => "route";
    static readonly Vector2 Anchor = new(-3.0f, -2.2f), PlugHome = new(-2.4f, -0.9f);
    private static readonly SystemTypes[] Candidates =
    {
        SystemTypes.Weapons, SystemTypes.Shields, SystemTypes.LifeSupp, SystemTypes.Nav, SystemTypes.Security,
        SystemTypes.Comms, SystemTypes.UpperEngine, SystemTypes.LowerEngine,
    };
    private Transform _plug;
    private LineRenderer _cable;
    private readonly List<(Vector2 P, SystemTypes S, SpriteRenderer R)> _sockets = new();
    private SystemTypes _target;
    private bool _drag;
    private float _red;
    private int _redIdx = -1;
    private InputScript _script;
    public float Progress => 0f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        _target = ctx.Target != 0 ? ctx.Target : Candidates[Random.Range(0, Candidates.Length)];
        var pool = new List<SystemTypes>();
        foreach (var s in Candidates) if (s != _target) pool.Add(s);
        for (int i = pool.Count - 1; i > 0; i--) { int j = Random.Range(0, i + 1); (pool[i], pool[j]) = (pool[j], pool[i]); }
        var chosen = new List<SystemTypes> { _target };
        chosen.AddRange(pool.GetRange(0, 5));
        for (int i = chosen.Count - 1; i > 0; i--) { int j = Random.Range(0, i + 1); (chosen[i], chosen[j]) = (chosen[j], chosen[i]); }
        for (int i = 0; i < 6; i++)
        {
            var p = new Vector2(-0.3f + (i % 3) * 1.45f, 0.55f - (i / 3) * 1.6f);
            _sockets.Add((p, chosen[i], AtlasTaskKit.Sprite(root, "task_socket.png", 100f, p, 2)));
            MatchKit.Text(root, p + new Vector2(0f, -0.62f), MatchKit.RoomName(chosen[i]), 1.7f, Color.white, 3);
        }
        MatchKit.Text(root, new Vector2(0.4f, 1.85f), "ROUTE POWER TO  " + MatchKit.RoomName(_target).ToUpperInvariant(), 2.4f, new Color(1f, 0.85f, 0.4f), 3);
        _plug = AtlasTaskKit.Sprite(root, "task_plug.png", 100f, PlugHome, 6, new Vector2(0.1f, 0.5f)).transform;
        var go = new GameObject("cable") { layer = 5 };
        go.transform.SetParent(root, false);
        _cable = go.AddComponent<LineRenderer>();
        _cable.useWorldSpace = false;
        _cable.positionCount = 2;
        _cable.startWidth = _cable.endWidth = 0.14f;
        _cable.material = new Material(Shader.Find("Sprites/Default"));
        _cable.startColor = _cable.endColor = new Color(0.12f, 0.12f, 0.14f);
        _cable.sortingOrder = 5;
        UpdateCable();
    }

    private void UpdateCable()
    {
        _cable.SetPosition(0, new Vector3(Anchor.x, Anchor.y, -0.05f));
        _cable.SetPosition(1, new Vector3(_plug.localPosition.x, _plug.localPosition.y, -0.05f));
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        if (_redIdx >= 0) _sockets[_redIdx].R.color = Color.Lerp(Color.white, new Color(1f, 0.4f, 0.4f), _red);
        if (Done) return;
        if (pressed && Vector2.Distance(mouse, (Vector2)_plug.localPosition + new Vector2(0.3f, 0f)) < 0.55f) _drag = true;
        if (_drag)
        {
            _plug.localPosition = new Vector3(mouse.x - 0.3f, mouse.y, _plug.localPosition.z);
            if (!down)
            {
                _drag = false;
                int hit = -1;
                for (int i = 0; i < _sockets.Count; i++) if (Vector2.Distance(mouse, _sockets[i].P) < 0.5f) hit = i;
                if (hit >= 0 && _sockets[hit].S == _target)
                {
                    _plug.localPosition = new Vector3(_sockets[hit].P.x - 0.62f, _sockets[hit].P.y, _plug.localPosition.z);
                    _sockets[hit].R.color = new Color(0.7f, 1f, 0.7f);
                    Done = true;
                }
                else
                {
                    if (hit >= 0) { _redIdx = hit; _red = 1f; }
                    _plug.localPosition = new Vector3(PlugHome.x, PlugHome.y, _plug.localPosition.z);
                }
            }
        }
        UpdateCable();
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            var t = _sockets.Find(s => s.S == _target).P;
            _script = new InputScript().Drag(PlugHome + new Vector2(0.3f, 0f), t, 0.5f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { if (_cable != null && _cable.material != null) Object.Destroy(_cable.material); }
}

// ================================================================== Lichtleiter (Repair Showcase Lighting)

internal sealed class LightMechanic : IAtlasMechanic
{
    public string Name => "light";
    const int E = 1, N = 2, Wd = 4, S = 8;
    const float Cell = 1.2f;
    static readonly Vector2 Origin = new(-1.0f, 1.1f);            // Mitte der Kachel (Zeile 0, Spalte 0)
    private readonly int[,] _mask = new int[3, 3];               // Loesung
    private readonly int[,] _rot = new int[3, 3];                // aktuelle Drehung relativ zur Loesung (0..3, Vierteldrehungen gegen den Uhrzeigersinn)
    private readonly SpriteRenderer[,] _tiles = new SpriteRenderer[3, 3];
    private readonly float[,] _shown = new float[3, 3];
    private readonly List<SpriteRenderer> _targets = new();
    private Sprite _lampOn, _lampOff;
    private int _src;
    private int _lit;
    private InputScript _script;
    public float Progress => _lit / 3f;
    public bool Done { get; private set; }

    private static Vector2 CellPos(int r, int c) => Origin + new Vector2(c * Cell, -r * Cell);
    private static int Rot(int m, int k)
    {
        for (int i = 0; i < ((k % 4) + 4) % 4; i++)
            m = ((m & E) != 0 ? N : 0) | ((m & N) != 0 ? Wd : 0) | ((m & Wd) != 0 ? S : 0) | ((m & S) != 0 ? E : 0);
        return m;
    }
    private static int Bits(int m) => ((m & 1) + ((m >> 1) & 1) + ((m >> 2) & 1) + ((m >> 3) & 1));

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        Generate();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++)
            {
                AtlasTaskKit.Sprite(root, "task_tile_bg.png", 100f, CellPos(r, c), 1);
                var (file, baseRot) = Piece(_mask[r, c]);
                var t = AtlasTaskKit.Sprite(root, file, 100f, CellPos(r, c), 2);
                t.transform.localScale = Vector3.one * 0.98f;
                t.gameObject.name = baseRot.ToString();
                _tiles[r, c] = t;
            }
        AtlasTaskKit.Sprite(root, "task_light_source.png", 100f, CellPos(_src, 0) + new Vector2(-1.1f, 0f), 2);
        _lampOn = AtlasAssets.TaskSprite("task_lamp_on.png", 100f, new Vector2(0.5f, 0.5f));
        _lampOff = AtlasAssets.TaskSprite("task_lamp_off.png", 100f, new Vector2(0.5f, 0.5f));
        for (int r = 0; r < 3; r++) _targets.Add(AtlasTaskKit.Sprite(root, "task_lamp_off.png", 100f, CellPos(r, 2) + new Vector2(1.05f, 0f), 2));
        // verdrehen, bis es sicher nicht geloest ist (mindestens vier Klicks Arbeit)
        int work;
        do
        {
            work = 0;
            for (int r = 0; r < 3; r++)
                for (int c = 0; c < 3; c++)
                {
                    int sym = Symmetry(_mask[r, c]);
                    _rot[r, c] = Random.Range(0, 4) % sym;
                    work += _rot[r, c];                            // Klicks im Uhrzeigersinn bis zur Loesung
                }
        } while (work < 4 || Lit() == 3);
        for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++) _shown[r, c] = _rot[r, c] * 90f;
        Refresh();
    }

    private static int Symmetry(int m) => m == 15 ? 1 : (m == (E | Wd) || m == (N | S)) ? 2 : 4;

    private void Generate()
    {
        _src = Random.Range(0, 3);
        for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++) _mask[r, c] = 0;
        _mask[_src, 0] |= Wd;
        void Link(int r1, int c1, int r2, int c2)
        {
            if (r2 == r1 && c2 == c1 + 1) { _mask[r1, c1] |= E; _mask[r2, c2] |= Wd; }
            else if (r2 == r1 + 1) { _mask[r1, c1] |= S; _mask[r2, c2] |= N; }
            else if (r2 == r1 - 1) { _mask[r1, c1] |= N; _mask[r2, c2] |= S; }
        }
        for (int t = 0; t < 3; t++)
        {
            int turn = Random.Range(0, 3), r = _src, c = 0;
            while (c < turn) { Link(r, c, r, c + 1); c++; }
            while (r != t) { int nr = r + (t > r ? 1 : -1); Link(r, c, nr, c); r = nr; }
            while (c < 2) { Link(r, c, r, c + 1); c++; }
            _mask[t, 2] |= E;
        }
        // unbenutzte Felder: Deko (gerade oder Ecke), damit das Raster voll ist
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++)
                if (_mask[r, c] == 0) _mask[r, c] = Random.value < 0.5f ? (E | Wd) : (E | S);
                else if (Bits(_mask[r, c]) == 1) _mask[r, c] |= Rot(_mask[r, c], 2);   // Sackgasse -> gerade
    }

    // Kachelbild und Grunddrehung, deren Oeffnungen = Maske
    private static (string, int) Piece(int m)
    {
        (string f, int b)[] pieces = { ("task_tile_straight.png", E | Wd), ("task_tile_corner.png", E | S), ("task_tile_tee.png", E | Wd | S), ("task_tile_cross.png", 15) };
        foreach (var (f, b) in pieces)
            for (int k = 0; k < 4; k++)
                if (Rot(b, k) == m) return (f, k);
        return ("task_tile_cross.png", 0);
    }

    private int Open(int r, int c) => Rot(_mask[r, c], _rot[r, c]);

    private int Lit()
    {
        var seen = new bool[3, 3];
        var q = new Queue<(int, int)>();
        if ((Open(_src, 0) & Wd) != 0) { seen[_src, 0] = true; q.Enqueue((_src, 0)); }
        while (q.Count > 0)
        {
            var (r, c) = q.Dequeue();
            int o = Open(r, c);
            void Go(int bit, int nr, int nc, int back)
            {
                if ((o & bit) == 0 || nr < 0 || nr > 2 || nc < 0 || nc > 2 || seen[nr, nc]) return;
                if ((Open(nr, nc) & back) == 0) return;
                seen[nr, nc] = true; q.Enqueue((nr, nc));
            }
            Go(E, r, c + 1, Wd); Go(Wd, r, c - 1, E); Go(N, r - 1, c, S); Go(S, r + 1, c, N);
        }
        int lit = 0;
        for (int r = 0; r < 3; r++)
        {
            bool on = seen[r, 2] && (Open(r, 2) & E) != 0;
            if (_targets.Count > r) _targets[r].sprite = on ? _lampOn : _lampOff;
            if (on) lit++;
            for (int c = 0; c < 3; c++)
                if (_tiles[r, c] != null) _tiles[r, c].color = seen[r, c] ? new Color(1f, 0.92f, 0.55f) : new Color(0.55f, 0.58f, 0.66f);
        }
        return lit;
    }

    private void Refresh() => _lit = Lit();

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++)
            {
                int baseRot = int.Parse(_tiles[r, c].gameObject.name);
                float target = (baseRot + _rot[r, c]) * 90f;
                _shown[r, c] = Mathf.MoveTowardsAngle(_shown[r, c], target, 900f * dt);
                _tiles[r, c].transform.localEulerAngles = new Vector3(0, 0, _shown[r, c]);
            }
        if (Done || !pressed) return;
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++)
                if (MatchKit.In(mouse, CellPos(r, c), new Vector2(Cell / 2f, Cell / 2f)))
                {
                    _rot[r, c] = (_rot[r, c] + 3) % 4;                  // eine Vierteldrehung im Uhrzeigersinn
                    Refresh();
                    if (_lit == 3) Done = true;
                }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            for (int r = 0; r < 3; r++)
                for (int c = 0; c < 3; c++)
                {
                    int sym = Symmetry(_mask[r, c]);
                    int clicks = _rot[r, c] % sym;
                    for (int i = 0; i < clicks; i++) _script.Tap(CellPos(r, c));
                }
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}
