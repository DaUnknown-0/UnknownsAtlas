// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Reparatur-Minispiele der Karten-Sabotagen. Sie sprechen exakt das Netzprotokoll der Skeld-Systeme
// (ShipStatus.RpcUpdateSystem mit den Operations-Konstanten der Systeme), nur die Bedienung ist
// eigen und verlangt Geschick statt eines Knopfdrucks (User 23.09.: "nicht nur die oeden draufdruecken"):
//
//   alarm       Museum, Reaktor-Typ: wandernden Fingerabdruck auf dem Scanner verfolgen
//   fire        Wald,   Reaktor-Typ: mit dem Schlauch die gerade auflodernde Flamme treffen
//   climatefail Museum, O2-Typ: Code vom Sensorzettel auf vertauschtem Tastenfeld eingeben
//   waterworks  Wald,   O2-Typ: vier Ventile nach dem Schaltplan des Pults stellen
//   fusebox     Museum, Licht: durchgebrannte Sicherungen erkennen und Ersatz hineinziehen
//   breakers    Wald,   Licht: Leistungsschalter per Zug umlegen, bis alle Lampen gruen sind
//   cctv        Museum, Comms: zwei Regler, bis das Kamerabild ruhig und klar ist
//   antenna     Wald,   Comms: Schuessel drehen und Frequenz einstellen, bis das Signal voll ist
//
// Reaktor-Typ: solange man trifft, zaehlt man als "am Pult" (AddUserOp|Konsole), sonst nicht
// (RemoveUserOp|Konsole) - die Zwei-Personen-Regel bleibt damit vanilla. Das Minispiel schliesst,
// sobald das System repariert ist, egal von wem.

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class SabKit
{
    public static T Sys<T>(SystemTypes s) where T : Il2CppSystem.Object
    {
        try
        {
            var ship = ShipStatus.Instance;
            if (ship == null || !ship.Systems.ContainsKey(s)) return null;
            return ship.Systems[s].TryCast<T>();
        }
        catch { return null; }
    }

    public static void Send(SystemTypes s, int amount)
    {
        try { ShipStatus.Instance?.RpcUpdateSystem(s, (byte)amount); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Sab] update {s} {amount}: {e.Message}"); }
    }
}

// ================================================================== Reaktor-Typ (Alarm, Waldbrand)

internal sealed class HoldTrackMechanic : IAtlasMechanic
{
    public string Name => _fire ? "fire" : "alarm";
    private readonly bool _fire;
    private int _console;
    private bool _engaged;
    private float _grace, _t, _switchT;
    private Transform _target, _cursor;
    private LineRenderer _hose;
    private readonly List<SpriteRenderer> _flames = new();
    private int _active;
    private TextMeshPro _msg;
    private Vector2 _center;
    private SpriteRenderer _targetR;
    public float Progress => _engaged ? 0.5f : 0f;
    public bool Done { get; private set; }

    public HoldTrackMechanic(bool fire) { _fire = fire; }

    private ReactorSystemType Reactor => SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor);

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _console = ctx.ConsoleId;
        if (_fire)
        {
            AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
            MatchKit.Box(root, new Vector2(0f, -0.1f), new Vector2(6.4f, 3.8f), new Color(0.14f, 0.1f, 0.08f), 1);
            for (int i = 0; i < 4; i++)
            {
                var f = AtlasTaskKit.Sprite(root, "task_flame.png", 100f, new Vector2(-2.3f + i * 1.55f, Random.Range(-1.2f, 0.9f)), 2);
                f.transform.localScale = Vector3.one * 2.2f;
                _flames.Add(f);
            }
            _hose = MatchKit.Line(root, new Color(0.45f, 0.7f, 1f, 0.85f), 0.12f, 4);
            _cursor = AtlasTaskKit.Sprite(root, "task_marker.png", 100f, Vector2.zero, 5).transform;
            _active = Random.Range(0, 4);
        }
        else
        {
            AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
            _center = new Vector2(-0.6f, -0.1f);
            AtlasTaskKit.Sprite(root, "task_scanner.png", 100f, _center, 1).transform.localScale = Vector3.one * 1.2f;
            _targetR = AtlasTaskKit.Sprite(root, "task_marker.png", 100f, _center, 3);
            _target = _targetR.transform;
            _target.localScale = Vector3.one * 1.4f;
        }
        _msg = MatchKit.Text(root, new Vector2(_fire ? 0f : 2.3f, _fire ? 2.15f : 0.2f), "", 2.1f, Color.white, 6);
    }

    private float _diagHeld;

    private void SetEngaged(bool on)
    {
        if (on == _engaged) return;
        _engaged = on;
        if (AtlasMinigame.DiagStep >= 0) return;                       // Autotest: ohne Sabotage kein Netz
        SabKit.Send(SystemTypes.Reactor, (on ? ReactorSystemType.AddUserOp : ReactorSystemType.RemoveUserOp) | (_console & ReactorSystemType.ConsoleIdMask));
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _t += dt;
        var r = Reactor;
        if (r != null && !r.IsActive && AtlasMinigame.DiagStep < 0) { SetEngaged(false); Done = true; return; }
        bool onTarget;
        if (_fire)
        {
            _switchT -= dt;
            if (_switchT <= 0f) { _active = (_active + Random.Range(1, 4)) % 4; _switchT = Random.Range(1.4f, 2.4f); }
            for (int i = 0; i < _flames.Count; i++)
            {
                float k = i == _active ? 1.25f + 0.15f * Mathf.Sin(_t * 18f) : 0.7f + 0.08f * Mathf.Sin(_t * 9f + i);
                _flames[i].transform.localScale = Vector3.one * 2.2f * k;
                _flames[i].color = i == _active ? Color.white : new Color(1f, 1f, 1f, 0.55f);
            }
            _cursor.localPosition = new Vector3(mouse.x, mouse.y, _cursor.localPosition.z);
            MatchKit.Set(_hose, 0, new Vector2(3.4f, -2.4f), 4);
            MatchKit.Set(_hose, 1, mouse, 4);
            _hose.enabled = down;
            onTarget = down && Vector2.Distance(mouse, (Vector2)_flames[_active].transform.localPosition + new Vector2(0f, 0.4f)) < 0.75f;
        }
        else
        {
            // der Abdruck wandert auf einer Lissajous-Bahn ueber die Glasplatte
            var p = _center + new Vector2(Mathf.Sin(_t * 0.9f) * 1.0f, Mathf.Sin(_t * 1.3f + 1f) * 1.2f);
            _target.localPosition = new Vector3(p.x, p.y, _target.localPosition.z);
            onTarget = down && Vector2.Distance(mouse, p) < 0.55f;
            _targetR.color = onTarget ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 1f, 1f, 0.9f);
        }
        // kurze Gnadenfrist, damit ein Zittern nicht sofort loslaesst
        _grace = onTarget ? 0.3f : _grace - dt;
        SetEngaged(_grace > 0f);
        if (AtlasMinigame.DiagStep >= 0) { _diagHeld = _engaged ? _diagHeld + dt : _diagHeld; if (_diagHeld > 2.5f) Done = true; }
        int users = r != null ? r.UserCount : 0;
        _msg.text = _engaged ? (users >= 2 ? "HOLDING..." : "WAITING FOR PARTNER") : (_fire ? "HIT THE FLAMES" : "TRACK THE PRINT");
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        down = true;
        mouse = _fire ? (Vector2)_flames[_active].transform.localPosition + new Vector2(0f, 0.4f) : (Vector2)_target.localPosition;
    }

    public void Dispose() => SetEngaged(false);
}

// ================================================================== O2-Typ: Klimaausfall (Code)

internal sealed class KeypadMechanic : IAtlasMechanic
{
    public string Name => "climatefail";
    private int _console;
    private string _code = "00000", _typed = "";
    private readonly List<(Vector2 P, int Digit)> _keys = new();
    private TextMeshPro _display;
    private float _red;
    private SpriteRenderer _displayR;
    private InputScript _script;
    public float Progress => _typed.Length / 5f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _console = ctx.ConsoleId;
        var t = ctx.AnyTask != null ? ctx.AnyTask.TryCast<NoOxyTask>() : null;
        if (t != null) _code = (Math.Abs(t.targetNumber) % 100000).ToString("00000");
        else _code = Random.Range(10000, 99999).ToString();
        AtlasTaskKit.Sprite(root, "task_steel_panel.png", 100f, Vector2.zero, 0);
        // Sensorzettel mit dem Code
        AtlasTaskKit.Sprite(root, "task_card.png", 100f, new Vector2(-2.3f, 0.9f), 1);
        MatchKit.Text(root, new Vector2(-2.3f, 1.35f), "SENSOR RESET", 1.6f, new Color(0.3f, 0.3f, 0.35f), 2);
        MatchKit.Text(root, new Vector2(-2.3f, 0.75f), _code, 3.6f, new Color(0.15f, 0.15f, 0.2f), 2);
        _displayR = AtlasTaskKit.Sprite(root, "task_display.png", 100f, new Vector2(1.0f, 1.75f), 1);
        _display = MatchKit.Text(root, new Vector2(1.0f, 1.72f), "", 3.4f, new Color(0.5f, 1f, 0.6f), 2);
        // Tastenfeld mit vertauschten Ziffern
        var digits = new List<int> { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
        for (int i = 9; i > 0; i--) { int j = Random.Range(0, i + 1); (digits[i], digits[j]) = (digits[j], digits[i]); }
        for (int i = 0; i < 10; i++)
        {
            var p = new Vector2(-0.5f + (i % 5) * 0.8f, 0.55f - (i / 5) * 0.9f);
            var k = AtlasTaskKit.Sprite(root, "task_key.png", 100f, p, 2);
            k.transform.localScale = Vector3.one * 0.7f;
            MatchKit.Text(root, p, digits[i].ToString(), 3f, new Color(0.15f, 0.15f, 0.2f), 3);
            _keys.Add((p, digits[i]));
        }
        MatchKit.Text(root, new Vector2(1.0f, -1.55f), "CLIMATE CONTROL", 1.8f, Color.white, 2);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2f);
        _displayR.color = Color.Lerp(Color.white, new Color(1f, 0.5f, 0.5f), _red);
        _display.text = _typed.PadRight(5, '_');
        var sys = SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp);
        if (sys != null && AtlasMinigame.DiagStep < 0 && (!sys.IsActive || sys.GetConsoleComplete(_console))) { Done = true; return; }
        if (Done || !pressed) return;
        foreach (var k in _keys)
        {
            if (!MatchKit.In(mouse, k.P, new Vector2(0.36f, 0.36f))) continue;
            _typed += k.Digit;
            if (_typed.Length < 5) return;
            if (_typed == _code) { SabKit.Send(SystemTypes.LifeSupp, LifeSuppSystemType.AddUserOp | (_console & LifeSuppSystemType.ConsoleIdMask)); Done = true; }
            else { _typed = ""; _red = 1f; }
            return;
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var ch in _code) _script.Tap(_keys.Find(k => k.Digit == ch - '0').P);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== O2-Typ: Wasserversorgung (Ventile nach Schaltplan)

internal sealed class ValvePlanMechanic : IAtlasMechanic
{
    public string Name => "waterworks";
    private int _console, _want, _have;
    private readonly List<(Vector2 P, Transform T)> _valves = new();
    private readonly List<SpriteRenderer> _plan = new();
    private InputScript _script;
    public float Progress => 0f;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _console = ctx.ConsoleId;
        var t = ctx.AnyTask != null ? ctx.AnyTask.TryCast<NoOxyTask>() : null;
        int seed = t != null ? t.targetNumber : Random.Range(1, 99999);
        _want = ((seed >> (_console * 4)) ^ (seed >> 9)) & 15;
        if (_want == 0) _want = 9;
        do _have = Random.Range(0, 16); while (_have == _want);
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_pipes.png", 100f, new Vector2(0.4f, -0.3f), 1).transform.localScale = new Vector3(0.85f, 0.85f, 1f);
        // Schaltplan links oben: gruen = offen, rot = zu
        AtlasTaskKit.Sprite(root, "task_card.png", 100f, new Vector2(-2.55f, 1.35f), 2).transform.localScale = Vector3.one * 0.8f;
        MatchKit.Text(root, new Vector2(-2.55f, 1.85f), "PLAN", 1.6f, new Color(0.3f, 0.3f, 0.35f), 3);
        for (int i = 0; i < 4; i++)
            _plan.Add(MatchKit.Box(root, new Vector2(-3.1f + i * 0.37f, 1.3f), new Vector2(0.28f, 0.28f), Color.white, 3));
        for (int i = 0; i < 4; i++)
        {
            var p = new Vector2(-1.1f + i * 1.4f, i % 2 == 0 ? 0.45f : -1.05f);
            var v = AtlasTaskKit.Sprite(root, "task_valve.png", 100f, p, 2).transform;
            v.localScale = Vector3.one * 0.7f;
            _valves.Add((p, v));
        }
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        for (int i = 0; i < 4; i++)
        {
            bool open = ((_have >> i) & 1) == 1, want = ((_want >> i) & 1) == 1;
            _plan[i].color = want ? new Color(0.35f, 0.85f, 0.45f) : new Color(0.85f, 0.3f, 0.3f);
            var t = _valves[i].T;
            t.localEulerAngles = new Vector3(0, 0, Mathf.MoveTowardsAngle(t.localEulerAngles.z, open ? 90f : 0f, 500f * dt));
            t.GetComponent<SpriteRenderer>().color = open ? new Color(0.7f, 1f, 0.7f) : Color.white;
        }
        var sys = SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp);
        if (sys != null && AtlasMinigame.DiagStep < 0 && (!sys.IsActive || sys.GetConsoleComplete(_console))) { Done = true; return; }
        if (Done || !pressed) return;
        for (int i = 0; i < 4; i++)
            if (Vector2.Distance(mouse, _valves[i].P) < 0.55f)
            {
                _have ^= 1 << i;
                if (_have == _want) { SabKit.Send(SystemTypes.LifeSupp, LifeSuppSystemType.AddUserOp | (_console & LifeSuppSystemType.ConsoleIdMask)); Done = true; }
            }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            for (int i = 0; i < 4; i++) if ((((_have ^ _want) >> i) & 1) == 1) _script.Tap(_valves[i].P);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Licht: Sicherungen (Museum) / Leistungsschalter (Wald)

internal sealed class SwitchesMechanic : IAtlasMechanic
{
    public string Name => _wald ? "breakers" : "fusebox";
    const int N = 5;
    private readonly bool _wald;
    private readonly List<(Vector2 P, SpriteRenderer Part, SpriteRenderer Lamp)> _slots = new();
    private Sprite _ok, _dead, _on, _off;
    private Transform _spare;
    private Vector2 _spareHome = new(2.8f, -1.3f);
    private int _drag = -1;
    private Vector2 _pressAt;
    private int _localActual, _localExpected;
    private bool _dragSpare;
    private InputScript _script;
    public float Progress => 0f;
    public bool Done { get; private set; }

    public SwitchesMechanic(bool wald) { _wald = wald; }

    private SwitchSystem Sys => SabKit.Sys<SwitchSystem>(SystemTypes.Electrical);
    private int Actual => AtlasMinigame.DiagStep >= 0 || Sys == null ? _localActual : Sys.ActualSwitches;
    private int Expected => AtlasMinigame.DiagStep >= 0 || Sys == null ? _localExpected : Sys.ExpectedSwitches;

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        _localExpected = Random.Range(0, 32);
        do _localActual = Random.Range(0, 32); while (_localActual == _localExpected);
        AtlasTaskKit.Sprite(root, _wald ? "task_wald_panel.png" : "task_steel_panel.png", 100f, Vector2.zero, 0);
        _ok = AtlasAssets.TaskSprite("task_fuse_ok.png", 100f, new Vector2(0.5f, 0.5f));
        _dead = AtlasAssets.TaskSprite("task_fuse_dead.png", 100f, new Vector2(0.5f, 0.5f));
        _on = AtlasAssets.TaskSprite("task_lamp_on.png", 100f, new Vector2(0.5f, 0.5f));
        _off = AtlasAssets.TaskSprite("task_lamp_off.png", 100f, new Vector2(0.5f, 0.5f));
        for (int i = 0; i < N; i++)
        {
            var p = new Vector2(-2.6f + i * 1.15f, -0.2f);
            SpriteRenderer part;
            if (_wald)
            {
                AtlasTaskKit.Sprite(root, "task_switch_plate.png", 100f, p, 1).transform.localScale = Vector3.one * 0.55f;
                part = AtlasTaskKit.Sprite(root, "task_switch_lever.png", 100f, p, 2, new Vector2(0.5f, 10f / 150f));
                part.transform.localScale = Vector3.one * 0.55f;
            }
            else
            {
                MatchKit.Box(root, p, new Vector2(0.8f, 1.2f), new Color(0.12f, 0.13f, 0.15f), 1);
                part = AtlasTaskKit.Sprite(root, "task_fuse_ok.png", 100f, p, 2);
            }
            var lamp = AtlasTaskKit.Sprite(root, "task_lamp_off.png", 100f, p + new Vector2(0f, 1.25f), 2);
            lamp.transform.localScale = Vector3.one * 0.55f;
            _slots.Add((p, part, lamp));
        }
        if (!_wald)
        {
            _spare = AtlasTaskKit.Sprite(root, "task_fuse_new.png", 100f, _spareHome, 5).transform;
            MatchKit.Text(root, _spareHome + new Vector2(0f, 0.75f), "SPARES", 1.6f, Color.white, 3);
        }
        MatchKit.Text(root, new Vector2(0f, 2.15f), _wald ? "RESET THE BREAKERS" : "REPLACE THE BLOWN FUSES", 2.2f, Color.white, 3);
    }

    private void Toggle(int i)
    {
        if (AtlasMinigame.DiagStep >= 0 || Sys == null) _localActual ^= 1 << i;
        else SabKit.Send(SystemTypes.Electrical, i);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        int wrong = Actual ^ Expected;
        for (int i = 0; i < N; i++)
        {
            bool ok = ((wrong >> i) & 1) == 0;
            _slots[i].Lamp.sprite = ok ? _on : _off;
            if (_wald)
            {
                bool up = ((Actual >> i) & 1) == 1;
                var t = _slots[i].Part.transform;
                t.localEulerAngles = new Vector3(0, 0, Mathf.MoveTowardsAngle(t.localEulerAngles.z, up ? 0f : 180f, 900f * dt));
            }
            else _slots[i].Part.sprite = ok ? _ok : _dead;
        }
        if (wrong == 0) { Done = true; return; }
        if (_wald)
        {
            // Schalter per Zug umlegen: hoch bzw. runter ziehen
            if (pressed) { _drag = -1; for (int i = 0; i < N; i++) if (MatchKit.In(mouse, _slots[i].P, new Vector2(0.45f, 0.9f))) { _drag = i; _pressAt = mouse; } }
            if (_drag >= 0 && Mathf.Abs(mouse.y - _pressAt.y) > 0.45f)
            {
                bool up = ((Actual >> _drag) & 1) == 1;
                if ((mouse.y > _pressAt.y) != up) Toggle(_drag);
                _drag = -1;
            }
            if (!down) _drag = -1;
            return;
        }
        // Museum: Ersatzsicherung in eine dunkle Fassung ziehen
        if (pressed && Vector2.Distance(mouse, _spare.localPosition) < 0.55f) _dragSpare = true;
        if (!_dragSpare) return;
        _spare.localPosition = new Vector3(mouse.x, mouse.y, _spare.localPosition.z);
        if (down) return;
        _dragSpare = false;
        for (int i = 0; i < N; i++)
            if (((wrong >> i) & 1) == 1 && Vector2.Distance(mouse, _slots[i].P) < 0.55f) Toggle(i);
        _spare.localPosition = new Vector3(_spareHome.x, _spareHome.y, _spare.localPosition.z);
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null || _script.Finished)
        {
            _script = new InputScript();
            int wrong = Actual ^ Expected;
            for (int i = 0; i < N; i++)
            {
                if (((wrong >> i) & 1) == 0) continue;
                var p = _slots[i].P;
                if (_wald)
                {
                    bool up = ((Actual >> i) & 1) == 1;
                    _script.Drag(p, p + new Vector2(0f, up ? -0.8f : 0.8f), 0.2f);
                }
                else _script.Drag(_spareHome, p, 0.3f);
            }
            _script.Wait(Vector2.zero, 0.2f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Comms: Kamerabild (Museum) / Funkmast (Wald)

internal sealed class TuneMechanic : IAtlasMechanic
{
    public string Name => _wald ? "antenna" : "cctv";
    private readonly bool _wald;
    private Rotary _a, _b;
    private float _ea, _eb, _hold;
    private Transform _knobA, _knobB, _dish, _picture;
    private SpriteRenderer _static;
    private TextMeshPro _bars;
    static readonly Vector2 KA = new(2.55f, 1.0f), KB = new(2.55f, -1.2f);
    private InputScript _script;
    public float Progress => Mathf.Clamp01(1f - (Mathf.Abs(_ea) + Mathf.Abs(_eb)) / 2f);
    public bool Done { get; private set; }

    public TuneMechanic(bool wald) { _wald = wald; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, _wald ? "task_wald_panel.png" : "task_steel_panel.png", 100f, Vector2.zero, 0);
        if (_wald)
        {
            MatchKit.Box(root, new Vector2(-1.0f, 0.1f), new Vector2(4.2f, 3.6f), new Color(0.1f, 0.14f, 0.24f), 1);
            _dish = AtlasTaskKit.Sprite(root, "task_dish.png", 100f, new Vector2(-1.0f, 0.1f), 2).transform;
            _bars = MatchKit.Text(root, new Vector2(-1.0f, -1.7f), "", 2.6f, new Color(0.5f, 1f, 0.6f), 3);
            MatchKit.Text(root, KA + new Vector2(0f, 0.02f), "AZIMUTH", 1.3f, Color.white, 4);
            MatchKit.Text(root, KB + new Vector2(0f, 0.02f), "FREQ", 1.3f, Color.white, 4);
        }
        else
        {
            var scr = new Vector2(-1.1f, 0.15f);
            _picture = AtlasTaskKit.Sprite(root, "task_gallery.png", 100f, scr, 1).transform;
            _picture.localScale = new Vector3(0.52f, 0.5f, 1f);
            _static = AtlasTaskKit.Sprite(root, "task_static.png", 100f, scr, 2);
            AtlasTaskKit.Sprite(root, "task_monitor.png", 100f, scr + new Vector2(0f, -0.1f), 3);
            MatchKit.Text(root, KA + new Vector2(0f, 0.02f), "H-HOLD", 1.3f, Color.white, 4);
            MatchKit.Text(root, KB + new Vector2(0f, 0.02f), "V-HOLD", 1.3f, Color.white, 4);
        }
        _knobA = AtlasTaskKit.Sprite(root, "task_focus_ring.png", 100f, KA, 3).transform;
        _knobB = AtlasTaskKit.Sprite(root, "task_focus_ring.png", 100f, KB, 3).transform;
        _knobA.localScale = _knobB.localScale = Vector3.one * 0.55f;
        _a = new Rotary(KA, 0.2f, 0.75f);
        _b = new Rotary(KB, 0.2f, 0.75f);
        _ea = (Random.value < 0.5f ? -1 : 1) * Random.Range(0.45f, 0.9f);
        _eb = (Random.value < 0.5f ? -1 : 1) * Random.Range(0.45f, 0.9f);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        var sys = SabKit.Sys<HudOverrideSystemType>(SystemTypes.Comms);
        if (sys != null && AtlasMinigame.DiagStep < 0 && !sys.IsActive) { Done = true; return; }
        _a.Tick(mouse, down, pressed); _b.Tick(mouse, down, pressed);
        _ea += _a.Delta / 360f; _eb += _b.Delta / 360f;
        _knobA.localEulerAngles += new Vector3(0, 0, _a.Delta);
        _knobB.localEulerAngles += new Vector3(0, 0, _b.Delta);
        float q = Progress;
        if (_wald)
        {
            _dish.localEulerAngles = new Vector3(0, 0, _ea * 60f);
            int bars = Mathf.Clamp(Mathf.RoundToInt(q * 5f), 0, 5);
            _bars.text = "SIGNAL " + new string('|', bars) + new string('.', 5 - bars);
        }
        else
        {
            // Bild rollt und rauscht, bis beide Regler stimmen
            _static.color = new Color(1f, 1f, 1f, Mathf.Clamp01(1.05f - q) * 0.95f);
            _static.transform.localPosition = new Vector3(-1.1f + Random.Range(-0.02f, 0.02f), 0.15f + Random.Range(-0.05f, 0.05f), _static.transform.localPosition.z);
            _picture.localPosition = new Vector3(-1.1f + _ea * 0.4f, 0.15f + Mathf.Repeat(Time.time * _eb * 2f, 0.6f) - 0.3f * Mathf.Sign(_eb) * Mathf.Min(1f, Mathf.Abs(_eb) * 3f), _picture.localPosition.z);
        }
        if (Done) return;
        _hold = Mathf.Abs(_ea) < 0.06f && Mathf.Abs(_eb) < 0.06f ? _hold + dt : 0f;
        if (_hold > 0.6f)
        {
            SabKit.Send(SystemTypes.Comms, 0);
            Done = true;
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _script ??= new InputScript().Arc(KA, 0.5f, 0f, -_ea * 360f, 0.7f).Arc(KB, 0.5f, 0f, -_eb * 360f, 0.7f).Wait(Vector2.zero, 1f);
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}

// ================================================================== Sturmholz: Baum zersaegen

internal sealed class SawMechanic : IAtlasMechanic
{
    public string Name => "sawlog";
    const float Need = 9f;                     // Saegestrecke in Einheiten (etwa sechs kraeftige Zuege)
    private Transform _saw, _logL, _logR;
    private SpriteRenderer _cut;
    private float _done, _lastX;
    private bool _grab;
    private float _st;
    public float Progress => _done / Need;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        _logL = AtlasTaskKit.Sprite(root, "task_fallen_tree.png", 100f, new Vector2(-0.2f, -0.7f), 1).transform;
        _logL.localScale = Vector3.one * 1.5f;
        _cut = MatchKit.Box(root, new Vector2(0.4f, -0.55f), new Vector2(0.08f, 0.01f), new Color(0.2f, 0.12f, 0.06f), 2);
        _saw = AtlasTaskKit.Sprite(root, "task_saw.png", 100f, new Vector2(0.4f, 0.1f), 4, new Vector2(0.35f, 0.4f)).transform;
        MatchKit.Text(root, new Vector2(0f, 2.1f), "SAW THROUGH THE TRUNK", 2.2f, Color.white, 5);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (pressed && Vector2.Distance(mouse, _saw.localPosition) < 1.6f) { _grab = true; _lastX = mouse.x; }
        if (!down) _grab = false;
        if (_grab && !Done)
        {
            float dx = mouse.x - _lastX;
            _lastX = mouse.x;
            _done += Mathf.Abs(dx);
            var p = _saw.localPosition;
            float depth = Mathf.Min(1f, _done / Need) * 0.55f;
            _saw.localPosition = new Vector3(Mathf.Clamp(mouse.x, -1.4f, 2.2f), 0.1f - depth, p.z);
            float h = Mathf.Max(0.01f, depth * 0.9f);
            _cut.transform.localScale = new Vector3(0.08f / 0.16f, h / 0.16f, 1f);
            _cut.transform.localPosition = new Vector3(0.4f, -0.2f - h / 2f, _cut.transform.localPosition.z);
            if (_done >= Need) Done = true;
        }
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        mouse = new Vector2(0.4f + Mathf.Sin(_st * 9f) * 1.3f, 0.1f);
        down = _st > 0.1f;
    }

    public void Dispose() { }
}
