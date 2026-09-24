// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Baustein "Drehen" (Kreisbewegung, Ringe, Raeder) und die Knobel-Minispiele (docs/TASK_KONZEPT.md):
//
//   tomb        Tomb Lock                 (Museum, Start Reactor)
//   projector   Focus the Dome Projector  (Museum, Stabilize Steering)
//   hiero       Hieroglyph Sequence       (Museum, Unlock Manifolds)
//   vault       Arm the Vault Showcase    (Museum, Prime Shields; Laserspiegel)
//   valves      Open the Valves           (Wald,   Unlock Manifolds)
//   splice      Splice Field Cable        (Wald,   Fix Wiring)
//   binoculars  Focus the Binoculars      (Wald,   Stabilize Steering)

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

// ================================================================== Tomb Lock

internal sealed class TombMechanic : IAtlasMechanic
{
    public string Name => "tomb";
    static readonly Vector2 C = new(0f, -0.1f);
    const float Scale = 0.8f;
    static readonly (float r0, float r1)[] Bands = { (1.55f, 2.1f), (1.0f, 1.54f), (0.45f, 0.99f) };
    private readonly int[] _pos = new int[3];                 // Klicks seit "Schluessel oben", 0..7
    private readonly Transform[] _rings = new Transform[3];
    private readonly float[] _shown = new float[3];
    private float _glow;
    private InputScript _script;
    public float Progress { get { int ok = 0; foreach (var p in _pos) if (p == 0) ok++; return ok / 3f; } }
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        for (int i = 0; i < 3; i++)
        {
            _rings[i] = AtlasTaskKit.Sprite(root, $"task_tomb_ring{i}.png", 100f, C, 1 + i).transform;
            _rings[i].localScale = Vector3.one * Scale;
        }
        AtlasTaskKit.Sprite(root, "task_tomb_center.png", 100f, C, 4).transform.localScale = Vector3.one * Scale;
        AtlasTaskKit.Sprite(root, "task_tomb_marker.png", 100f, C + new Vector2(0f, 2.25f), 5).transform.localScale = Vector3.one * 0.7f;
        do { for (int i = 0; i < 3; i++) _pos[i] = Random.Range(0, 8); } while (_pos[0] + _pos[1] + _pos[2] < 6);
        for (int i = 0; i < 3; i++) _shown[i] = -_pos[i] * 45f;
    }

    // Ring i dreht eine Stufe im Uhrzeigersinn und nimmt den naechstinneren Ring mit
    private void Click(int i)
    {
        _pos[i] = (_pos[i] + 1) % 8;
        if (i < 2) _pos[i + 1] = (_pos[i + 1] + 1) % 8;
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        for (int i = 0; i < 3; i++)
        {
            _shown[i] = Mathf.MoveTowardsAngle(_shown[i], -_pos[i] * 45f, 360f * dt);
            _rings[i].localEulerAngles = new Vector3(0, 0, _shown[i]);
            _rings[i].GetComponent<SpriteRenderer>().color = _pos[i] == 0 ? new Color(1f, 0.95f, 0.75f) : Color.white;
        }
        if (Done) return;
        if (pressed)
        {
            float d = Vector2.Distance(mouse, C);
            for (int i = 0; i < 3; i++) if (d >= Bands[i].r0 && d <= Bands[i].r1) Click(i);
        }
        if (_pos[0] == 0 && _pos[1] == 0 && _pos[2] == 0) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            var p = (int[])_pos.Clone();
            for (int i = 0; i < 3; i++)
                while (p[i] != 0)
                {
                    p[i] = (p[i] + 1) % 8;
                    if (i < 2) p[i + 1] = (p[i + 1] + 1) % 8;
                    float r = (Bands[i].r0 + Bands[i].r1) / 2f;
                    _script.Tap(C + new Vector2(r * 0.7f, r * 0.7f)).Wait(C, 0.12f);
                }
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Focus the Dome Projector

internal sealed class ProjectorMechanic : IAtlasMechanic
{
    public string Name => "projector";
    static readonly Vector2 Sky = new(-1.1f, -0.05f), Coarse = new(2.0f, 0.95f), Fine = new(2.0f, -1.2f);
    private Rotary _coarse, _fine;
    private Transform _ghost, _coarseT, _fineT, _needle;
    private SpriteRenderer _ghostR;
    private float _err, _hold;
    private InputScript _script;
    public float Progress => Mathf.Clamp01(1f - Mathf.Abs(_err));
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_sky.png", 100f, Sky, 1).transform.localScale = Vector3.one * 1.05f;
        _ghostR = AtlasTaskKit.Sprite(root, "task_sky.png", 100f, Sky, 2);
        _ghost = _ghostR.transform;
        _ghost.localScale = Vector3.one * 1.05f;
        _coarseT = AtlasTaskKit.Sprite(root, "task_focus_ring.png", 100f, Coarse, 2).transform;
        _coarseT.localScale = Vector3.one * 0.72f;
        _fineT = AtlasTaskKit.Sprite(root, "task_focus_ring.png", 100f, Fine, 2).transform;
        _fineT.localScale = Vector3.one * 0.5f;
        MatchKit.Text(root, Coarse + new Vector2(0f, 0.02f), "COARSE", 1.6f, Color.white, 3);
        MatchKit.Text(root, Fine + new Vector2(0f, 0.02f), "FINE", 1.4f, Color.white, 3);
        _coarse = new Rotary(Coarse, 0.45f, 0.95f);
        _fine = new Rotary(Fine, 0.25f, 0.7f);
        _err = (Random.value < 0.5f ? -1f : 1f) * Random.Range(0.55f, 1f);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _coarse.Tick(mouse, down, pressed);
        _fine.Tick(mouse, down, pressed);
        if (!Done)
        {
            _err += _coarse.Delta / 360f + _fine.Delta / 1440f;
            _coarseT.localEulerAngles += new Vector3(0, 0, _coarse.Delta);
            _fineT.localEulerAngles += new Vector3(0, 0, _fine.Delta);
        }
        // Unschaerfe = versetzte Doppelbelichtung
        _ghost.localPosition = new Vector3(Sky.x + _err * 0.55f, Sky.y + _err * 0.2f, _ghost.localPosition.z);
        _ghostR.color = new Color(1f, 1f, 1f, Mathf.Clamp01(Mathf.Abs(_err) * 3f) * 0.55f);
        if (Done) return;
        _hold = Mathf.Abs(_err) < 0.04f ? _hold + dt : 0f;
        if (_hold > 0.35f) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            // grob auf etwa 5 % heran, der Rest mit dem Feinring
            float coarse = -_err * 360f * 0.95f;
            float rest = -_err * 0.05f * 1440f;
            _script = new InputScript().Arc(Coarse, 0.7f, 0f, coarse, 1.0f).Arc(Fine, 0.48f, 0f, rest, 0.6f).Wait(Fine, 0.6f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Hieroglyph Sequence

internal sealed class HieroMechanic : IAtlasMechanic
{
    public string Name => "hiero";
    private readonly int[] _order = new int[10];
    private readonly List<(Vector2 P, int Glyph, SpriteRenderer R)> _buttons = new();
    private readonly List<SpriteRenderer> _legend = new();
    private int _next;
    private float _red;
    private InputScript _script;
    public float Progress => _next / 10f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        var perm = new List<int> { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
        for (int i = 9; i > 0; i--) { int j = Random.Range(0, i + 1); (perm[i], perm[j]) = (perm[j], perm[i]); }
        for (int i = 0; i < 10; i++) _order[i] = perm[i];
        // Legende oben: die Reihenfolge
        MatchKit.Box(root, new Vector2(0f, 1.85f), new Vector2(6.1f, 0.72f), new Color(0.87f, 0.77f, 0.55f), 1);
        for (int i = 0; i < 10; i++)
        {
            var g = AtlasTaskKit.Sprite(root, $"task_glyph{_order[i]}.png", 100f, new Vector2(-2.7f + i * 0.6f, 1.85f), 2);
            g.transform.localScale = Vector3.one * 0.62f;
            _legend.Add(g);
        }
        // Kartuschen: gleiche Zeichen, andere Anordnung
        for (int i = 9; i > 0; i--) { int j = Random.Range(0, i + 1); (perm[i], perm[j]) = (perm[j], perm[i]); }
        for (int i = 0; i < 10; i++)
        {
            var p = new Vector2(-2.4f + (i % 5) * 1.2f, 0.45f - (i / 5) * 1.75f);
            var r = AtlasTaskKit.Sprite(root, "task_cartouche.png", 100f, p, 2);
            AtlasTaskKit.Sprite(root, $"task_glyph{perm[i]}.png", 100f, p, 3);
            _buttons.Add((p, perm[i], r));
        }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2.5f);
        for (int i = 0; i < _buttons.Count; i++)
        {
            int idx = Array.IndexOf(_order, _buttons[i].Glyph);
            var baseC = idx < _next ? new Color(1f, 0.85f, 0.35f) : Color.white;
            _buttons[i].R.color = Color.Lerp(baseC, new Color(1f, 0.45f, 0.45f), _red);
        }
        for (int i = 0; i < _legend.Count; i++) _legend[i].color = i < _next ? new Color(0.75f, 0.45f, 0.1f) : Color.black;
        if (Done || !pressed) return;
        foreach (var b in _buttons)
        {
            if (!MatchKit.In(mouse, b.P, new Vector2(0.5f, 0.72f))) continue;
            if (b.Glyph == _order[_next]) { if (++_next >= 10) Done = true; }
            else if (Array.IndexOf(_order, b.Glyph) >= _next) { _next = 0; _red = 1f; }   // falsch: alles zurueck
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var g in _order) _script.Tap(_buttons.Find(b => b.Glyph == g).P);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Arm the Vault Showcase (Laserspiegel)

internal sealed class VaultMechanic : IAtlasMechanic
{
    public string Name => "vault";
    const int Cols = 5, Rows = 4;
    const float Cell = 0.95f;
    static readonly Vector2 Origin = new(-1.6f, 1.45f);       // Mitte Zelle (0,0), Zeile nach unten
    private int _row0;
    private readonly Dictionary<(int, int), bool> _mirror = new();   // true = '/', false = '\'
    private readonly Dictionary<(int, int), bool> _solution = new();
    private readonly Dictionary<(int, int), Transform> _mirrorT = new();
    private readonly List<(int r, int c, SpriteRenderer R)> _recv = new();
    private Sprite _on, _off;
    private LineRenderer _beam;
    private int _hit;
    private InputScript _script;
    public float Progress => _recv.Count == 0 ? 0f : _hit / (float)_recv.Count;
    public bool Done { get; private set; }

    private static Vector2 P(int r, int c) => Origin + new Vector2(c * Cell, -r * Cell);

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        for (int r = 0; r < Rows; r++)
            for (int c = 0; c < Cols; c++)
                MatchKit.Box(root, P(r, c), new Vector2(Cell - 0.06f, Cell - 0.06f), new Color(0.2f, 0.22f, 0.27f), 1);
        Generate();
        AtlasTaskKit.Sprite(root, "task_emitter.png", 100f, P(_row0, 0) + new Vector2(-Cell * 1.05f, 0f), 3).transform.localScale = Vector3.one * 0.8f;
        _on = AtlasAssets.TaskSprite("task_lamp_on.png", 100f, new Vector2(0.5f, 0.5f));
        _off = AtlasAssets.TaskSprite("task_lamp_off.png", 100f, new Vector2(0.5f, 0.5f));
        foreach (var (r, c) in _recvCells)
        {
            var s = AtlasTaskKit.Sprite(root, "task_lamp_off.png", 100f, P(r, c), 3);
            s.transform.localScale = Vector3.one * 0.6f;
            _recv.Add((r, c, s));
        }
        foreach (var kv in _mirror)
        {
            var t = AtlasTaskKit.Sprite(root, "task_mirror.png", 100f, P(kv.Key.Item1, kv.Key.Item2), 4).transform;
            t.localScale = Vector3.one * 0.8f;
            _mirrorT[kv.Key] = t;
        }
        // Museum: roter Laser; Park: warmer Scheinwerferstrahl
        _beam = MatchKit.Line(root, ctx.Map == "park" ? new Color(1f, 0.88f, 0.45f, 0.9f) : new Color(1f, 0.2f, 0.2f, 0.9f),
                              ctx.Map == "park" ? 0.11f : 0.07f, 5, 16);
        Trace();
    }

    private List<(int, int)> _recvCells = new();

    private void Generate()
    {
        for (int tries = 0; tries < 200; tries++)
        {
            _mirror.Clear(); _solution.Clear();
            _row0 = Random.Range(0, Rows);
            int r = _row0, c = 0, dr = 0, dc = 1;
            var path = new List<(int, int)>();
            var used = new HashSet<(int, int)>();
            bool ok = true;
            for (int m = 0; m < 3 && ok; m++)
            {
                int run = Random.Range(1, 3);
                for (int k = 0; k < run; k++)
                {
                    if (r < 0 || r >= Rows || c < 0 || c >= Cols || used.Contains((r, c))) { ok = false; break; }
                    path.Add((r, c)); used.Add((r, c));
                    r += dr; c += dc;
                }
                if (!ok || r < 0 || r >= Rows || c < 0 || c >= Cols || used.Contains((r, c))) { ok = false; break; }
                // Spiegel: waagerecht -> senkrecht oder umgekehrt
                int ndr, ndc;
                if (dr == 0) { ndr = Random.value < 0.5f ? -1 : 1; ndc = 0; } else { ndr = 0; ndc = 1; }
                bool slash = (dc == 1 && ndr == -1) || (dr == -1 && ndc == 1) || (dc == -1 && ndr == 1) || (dr == 1 && ndc == -1);
                _mirror[(r, c)] = slash; _solution[(r, c)] = slash; used.Add((r, c));
                dr = ndr; dc = ndc; r += dr; c += dc;
            }
            if (!ok) continue;
            while (r >= 0 && r < Rows && c >= 0 && c < Cols && !used.Contains((r, c))) { path.Add((r, c)); used.Add((r, c)); r += dr; c += dc; }
            if (path.Count < 5) continue;
            _recvCells = new List<(int, int)>();
            var cand = new List<(int, int)>(path);
            cand.RemoveAt(0);                                        // nicht direkt vor dem Sender
            for (int i = 0; i < 4 && cand.Count > 0; i++) { int j = Random.Range(0, cand.Count); _recvCells.Add(cand[j]); cand.RemoveAt(j); }
            if (_recvCells.Count < 4) continue;
            // verstellen: mindestens zwei Spiegel falsch
            var keys = new List<(int, int)>(_mirror.Keys);
            int flips = 0;
            foreach (var k in keys) if (Random.value < 0.7f) { _mirror[k] = !_mirror[k]; flips++; }
            if (flips < 2) { _mirror[keys[0]] = !_solution[keys[0]]; _mirror[keys[1]] = !_solution[keys[1]]; }
            return;
        }
    }

    private void Trace()
    {
        var pts = new List<Vector2> { P(_row0, 0) + new Vector2(-Cell * 0.7f, 0f) };
        var lit = new HashSet<(int, int)>();
        int r = _row0, c = 0, dr = 0, dc = 1;
        for (int step = 0; step < 40; step++)
        {
            if (r < 0 || r >= Rows || c < 0 || c >= Cols) { pts.Add(P(r - dr, c - dc) + new Vector2(dc, -dr) * Cell * 0.5f); break; }
            lit.Add((r, c));
            if (_mirror.TryGetValue((r, c), out bool slash))
            {
                pts.Add(P(r, c));
                // '/': E->N, N->E, W->S, S->W  |  '\': E->S, S->E, W->N, N->W   (dr<0 = nach oben)
                (dr, dc) = slash ? (-dc, -dr) : (dc, dr);
            }
            r += dr; c += dc;
        }
        _beam.positionCount = pts.Count;
        for (int i = 0; i < pts.Count; i++) MatchKit.Set(_beam, i, pts[i], 5);
        _hit = 0;
        foreach (var (rr, cc, R) in _recv) { bool on = lit.Contains((rr, cc)); R.sprite = on ? _on : _off; if (on) _hit++; }
        foreach (var kv in _mirrorT) kv.Value.localEulerAngles = new Vector3(0, 0, _mirror[kv.Key] ? 0f : 90f);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (Done || !pressed) return;
        foreach (var k in new List<(int, int)>(_mirror.Keys))
            if (MatchKit.In(mouse, P(k.Item1, k.Item2), new Vector2(Cell / 2f, Cell / 2f)))
            {
                _mirror[k] = !_mirror[k];
                Trace();
            }
        if (_hit == _recv.Count) { Done = true; MatchKit.PlayVisual(TaskTypes.PrimeShields); }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var kv in _solution) if (_mirror[kv.Key] != kv.Value) _script.Tap(P(kv.Key.Item1, kv.Key.Item2));
            _script.Wait(Vector2.zero, 0.3f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Open the Valves

internal sealed class ValvesMechanic : IAtlasMechanic
{
    public string Name => "valves";
    const float Need = 200f;
    private readonly List<(Vector2 P, int Num, Transform T, Rotary Rot)> _valves = new();
    private readonly float[] _turn = new float[5];
    private int _next;
    private SpriteRenderer _steam;
    private float _steamA;
    private InputScript _script;
    public float Progress => _next / 5f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_pipes.png", 100f, Vector2.zero, 1);
        var nums = new List<int> { 1, 2, 3, 4, 5 };
        for (int i = 4; i > 0; i--) { int j = Random.Range(0, i + 1); (nums[i], nums[j]) = (nums[j], nums[i]); }
        (float x, float y)[] px = { (130, 150), (250, 330), (370, 150), (490, 330), (610, 150) };
        for (int i = 0; i < 5; i++)
        {
            var p = new Vector2((px[i].x - 360f) / 100f, (260f - px[i].y) / 100f);
            var t = AtlasTaskKit.Sprite(root, "task_valve.png", 100f, p, 2).transform;
            t.localScale = Vector3.one * 0.85f;
            MatchKit.Box(root, p + new Vector2(0f, 0.95f), new Vector2(0.5f, 0.42f), new Color(0.95f, 0.92f, 0.8f), 3);
            MatchKit.Text(root, p + new Vector2(0f, 0.93f), nums[i].ToString(), 2.6f, Color.black, 4);
            _valves.Add((p, nums[i], t, new Rotary(p, 0.15f, 0.8f)));
        }
        _steam = AtlasTaskKit.Sprite(root, "task_steam.png", 100f, Vector2.zero, 6);
        _steam.color = new Color(1, 1, 1, 0);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _steamA = Mathf.Max(0f, _steamA - dt * 1.5f);
        _steam.color = new Color(1, 1, 1, _steamA);
        for (int i = 0; i < _valves.Count; i++)
        {
            var v = _valves[i];
            v.Rot.Tick(mouse, down, pressed);
            if (Done || v.Rot.Delta == 0f) continue;
            float d = Mathf.Max(0f, v.Rot.Delta);                    // aufdrehen = gegen den Uhrzeigersinn
            if (v.Num - 1 < _next) continue;                         // schon offen
            if (v.Num - 1 != _next)
            {
                // falsches Rad: Dampf, alles wieder zu
                if (d > 0f)
                {
                    _turn[i] += d;
                    if (_turn[i] > 40f)
                    {
                        _next = 0;
                        Array.Clear(_turn, 0, _turn.Length);
                        _steam.transform.localPosition = new Vector3(v.P.x, v.P.y + 0.6f, _steam.transform.localPosition.z);
                        _steamA = 1f;
                    }
                }
                continue;
            }
            _turn[i] += d;
            v.T.localEulerAngles = new Vector3(0, 0, _turn[i]);
            if (_turn[i] >= Need) { _next++; if (_next >= 5) Done = true; }
        }
        for (int i = 0; i < _valves.Count; i++)
            _valves[i].T.GetComponent<SpriteRenderer>().color = _valves[i].Num - 1 < _next ? new Color(0.6f, 1f, 0.6f) : Color.white;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            for (int n = 1; n <= 5; n++) { var v = _valves.Find(x => x.Num == n); _script.Arc(v.P, 0.5f, -60f, Need + 20f, 0.55f); }
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Splice Field Cable

internal sealed class SpliceMechanic : IAtlasMechanic
{
    public string Name => "splice";
    const float Need = 180f;
    private static readonly Color[] Palette = { new(0.9f, 0.2f, 0.2f), new(0.2f, 0.45f, 0.95f), new(0.95f, 0.8f, 0.15f), new(0.2f, 0.8f, 0.35f), new(0.9f, 0.5f, 0.1f) };
    private readonly List<(Vector2 Home, Color Col, Transform End, LineRenderer Wire, int Clamp)> _wires = new();
    private readonly List<(Vector2 P, Color Col, Transform Screw, Rotary Rot)> _clamps = new();
    private readonly float[] _screw = new float[3];
    private readonly bool[] _attached = new bool[3];
    private int _drag = -1, _done;
    private InputScript _script;
    static readonly float AnchorX = -3.3f;
    public float Progress => _done / 3f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        // je Schritt andere Farben
        int off = ctx.Step % Palette.Length;
        var cols = new[] { Palette[off], Palette[(off + 1) % Palette.Length], Palette[(off + 3) % Palette.Length] };
        var order = new List<int> { 0, 1, 2 };
        for (int i = 2; i > 0; i--) { int j = Random.Range(0, i + 1); (order[i], order[j]) = (order[j], order[i]); }
        for (int i = 0; i < 3; i++)
        {
            var cp = new Vector2(2.1f, 1.3f - i * 1.3f);
            AtlasTaskKit.Sprite(root, "task_clamp.png", 100f, cp, 2);
            MatchKit.Box(root, cp + new Vector2(0.72f, 0f), new Vector2(0.22f, 0.8f), cols[order[i]], 2);
            var screw = AtlasTaskKit.Sprite(root, "task_screw.png", 100f, cp + new Vector2(0f, 0f), 6).transform;
            screw.gameObject.SetActive(false);
            _clamps.Add((cp, cols[order[i]], screw, new Rotary(cp, 0f, 0.55f)));
        }
        for (int i = 0; i < 3; i++)
        {
            var home = new Vector2(-2.2f, 1.3f - i * 1.3f);
            var wire = MatchKit.Line(root, cols[i], 0.14f, 3);
            var end = AtlasTaskKit.Sprite(root, "task_wire_end.png", 100f, home, 5);
            end.color = cols[i];
            int clamp = _clamps.FindIndex(c => c.Col == cols[i]);
            _wires.Add((home, cols[i], end.transform, wire, clamp));
            MatchKit.Set(wire, 0, new Vector2(AnchorX, home.y), 3);
            MatchKit.Set(wire, 1, home, 3);
        }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (Done) return;
        if (pressed && _drag < 0)
            for (int i = 0; i < 3; i++)
                if (!_attached[i] && Vector2.Distance(mouse, _wires[i].End.localPosition) < 0.45f) _drag = i;
        if (_drag >= 0)
        {
            var w = _wires[_drag];
            w.End.localPosition = new Vector3(mouse.x, mouse.y, w.End.localPosition.z);
            MatchKit.Set(w.Wire, 1, mouse, 3);
            if (!down)
            {
                var cl = _clamps[w.Clamp];
                if (Vector2.Distance(mouse, cl.P) < 0.6f)
                {
                    _attached[_drag] = true;
                    var tip = cl.P + new Vector2(-0.45f, 0f);
                    w.End.localPosition = new Vector3(tip.x, tip.y, w.End.localPosition.z);
                    MatchKit.Set(w.Wire, 1, tip, 3);
                    cl.Screw.gameObject.SetActive(true);
                }
                else
                {
                    w.End.localPosition = new Vector3(w.Home.x, w.Home.y, w.End.localPosition.z);
                    MatchKit.Set(w.Wire, 1, w.Home, 3);
                }
                _drag = -1;
            }
            return;
        }
        // angeklemmte Adern festschrauben (Kreisbewegung, egal welche Richtung)
        for (int i = 0; i < 3; i++)
        {
            int wi = _wires.FindIndex(w => w.Clamp == i);
            var cl = _clamps[i];
            cl.Rot.Tick(mouse, down, pressed);
            if (!_attached[wi] || _screw[i] >= Need) continue;
            _screw[i] += Mathf.Abs(cl.Rot.Delta);
            cl.Screw.localEulerAngles = new Vector3(0, 0, -_screw[i]);
            if (_screw[i] >= Need) { cl.Screw.GetComponent<SpriteRenderer>().color = new Color(0.7f, 1f, 0.7f); if (++_done >= 3) Done = true; }
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var w in _wires) _script.Drag(w.Home, _clamps[w.Clamp].P, 0.35f);
            foreach (var c in _clamps) _script.Arc(c.P, 0.35f, 90f, -(Need + 30f), 0.5f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Focus the Binoculars

internal sealed class BinocularsMechanic : IAtlasMechanic
{
    public string Name => "binoculars";
    static readonly Vector2 Ring = new(2.75f, -1.85f);
    const float Limit = 5.2f;
    private Transform _pano, _deer, _ghost, _ringT;
    private SpriteRenderer _ghostR;
    private float _offset, _deerX, _err, _hold;
    private Rotary _ring;
    private bool _pan;
    private Vector2 _panLast;
    private InputScript _script;
    public float Progress => Mathf.Abs(_offset + _deerX) < 0.35f ? 0.5f + 0.5f * Mathf.Clamp01(1f - Mathf.Abs(_err)) : 0f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        _pano = AtlasTaskKit.Sprite(root, "task_panorama.png", 100f, Vector2.zero, 1).transform;
        _deerX = Random.Range(-5.5f, 5.5f);
        if (Mathf.Abs(_deerX) < 2f) _deerX = 2f * Mathf.Sign(_deerX == 0 ? 1 : _deerX);
        _deer = AtlasTaskKit.Sprite(_pano, "task_deer.png", 100f, new Vector2(_deerX, -0.4f), 2).transform;
        _ghostR = AtlasTaskKit.Sprite(_pano, "task_deer.png", 100f, new Vector2(_deerX, -0.4f), 3);
        _ghost = _ghostR.transform;
        AtlasTaskKit.Sprite(root, "task_binoc_overlay.png", 100f, Vector2.zero, 8);
        _ringT = AtlasTaskKit.Sprite(root, "task_focus_ring.png", 100f, Ring, 9).transform;
        _ringT.localScale = Vector3.one * 0.5f;
        _ring = new Rotary(Ring, 0.2f, 0.7f);
        _err = (Random.value < 0.5f ? -1f : 1f) * Random.Range(0.5f, 0.9f);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _ring.Tick(mouse, down, pressed);
        if (!Done && _ring.Active)
        {
            _err += _ring.Delta / 360f;
            _ringT.localEulerAngles += new Vector3(0, 0, _ring.Delta);
        }
        else if (!Done)
        {
            if (pressed && !_ring.Active && Vector2.Distance(mouse, Ring) > 0.8f) { _pan = true; _panLast = mouse; }
            if (!down) _pan = false;
            if (_pan) { _offset = Mathf.Clamp(_offset + (mouse.x - _panLast.x), -Limit - 1f, Limit + 1f); _panLast = mouse; }
        }
        _pano.localPosition = new Vector3(_offset, 0f, _pano.localPosition.z);
        _ghost.localPosition = new Vector3(_deerX + _err * 0.35f, -0.4f + _err * 0.1f, _ghost.localPosition.z);
        _ghostR.color = new Color(1f, 1f, 1f, Mathf.Clamp01(Mathf.Abs(_err) * 3f) * 0.6f);
        if (Done) return;
        bool centered = Mathf.Abs(_offset + _deerX) < 0.35f;
        _hold = centered && Mathf.Abs(_err) < 0.05f ? _hold + dt : 0f;
        if (_hold > 0.35f) Done = true;
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            float need = -_deerX;                                   // Panorama-Versatz, der den Hirsch mittig bringt
            float moved = 0f;
            while (Mathf.Abs(need - moved) > 0.05f)
            {
                float step = Mathf.Clamp(need - moved, -2.5f, 2.5f);
                _script.Drag(new Vector2(-step / 2f, 0.5f), new Vector2(step / 2f, 0.5f), 0.3f);
                moved += step;
            }
            _script.Arc(Ring, 0.45f, 0f, -_err * 360f, 0.6f).Wait(Ring, 0.6f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}
