// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasFerry - ein Fahrzeug zwischen zwei Anlegern (User 01.10.): Achterbahn-Pendelwagen im Park, Kanu auf
// dem Bach der Forest Station. Herausgeloest aus AtlasParkFun, damit beide dieselbe Mechanik nutzen.
// - Ein Fahrzeug je Strecke. Steht es am eigenen Anleger, faehrt "RIDE" mit einem los; steht es drueben,
//   holt "CALL" es leer heran (schneller). Der Host entscheidet, wer faehrt (exklusiv).
// - Waehrend der Fahrt bewegt der Fahrgast seine echte Position mit (Kollider aus auf allen Clients), die
//   anderen sehen ihn ueber die normale Positionsuebertragung; das Fahrzeug folgt bei fremden Fahrgaesten
//   deren uebertragener Position, nicht der eigenen Uhr (Abweichung sonst bis zu mehreren Metern).
// - Nicht abbrechbar; ein Meeting setzt das Fahrzeug ans Ziel.
//
// Netz: RPC 237 Op 15 [Unter-Op][Strecke][a][b]: Req (Fahrgast -> Host: Anleger), Start (Host -> alle:
// Fahrgast oder 255 = leer, Abfahrts-Anleger).

using System;
using System.Collections.Generic;
using Hazel;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class AtlasFerry
{
    private const string LogPrefix = "[Atlas/Ferry]";
    internal const byte OpFerry = 15;
    private const byte SubReq = 0, SubStart = 1, SubSync = 2, None = 255;
    private const float Step = 0.45f;
    // Fahrzeuge liegen HINTER dem Fahrgast (Sortierlinie 0,6 m noerdlich), er steht sichtbar darin
    private const int LayerObjects = 12;

    private static readonly List<AtlasFerry> All = new();
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;

    private readonly byte _id;
    private readonly string _name, _icon, _sound;
    private readonly Vector2[] _path;
    private readonly Vector2 _platA, _platB;
    private readonly float _speed, _callSpeed, _riderScale, _length;
    private SpriteRenderer _car;
    private byte _at, _rider = None, _from;
    private float _t0 = -100f;
    private bool _local;

    private AtlasFerry(byte id, string name, Vector2[] path, Vector2 platA, Vector2 platB, float speed, float callSpeed,
                       float riderScale, string icon, string sound)
    {
        _id = id; _name = name; _path = path; _platA = platA; _platB = platB;
        _speed = speed; _callSpeed = callSpeed; _riderScale = riderScale; _icon = icon; _sound = sound;
        for (int i = 1; i < path.Length; i++) _length += Vector2.Distance(path[i - 1], path[i]);
    }

    /// <summary>Strecke anlegen. path[0] liegt am Anleger A (platA = Use-Punkt am Ufer), path[^1] an B.</summary>
    public static AtlasFerry Create(Transform root, string name, string spriteFile, Vector2[] path, Vector2 platA, Vector2 platB,
                                    float speed, float callSpeed, float riderScale, string icon, string sound)
    {
        var f = new AtlasFerry((byte)All.Count, name, path, platA, platB, speed, callSpeed, riderScale, icon, sound);
        var spr = AtlasAssets.TaskSprite(spriteFile, 100f, new Vector2(0.5f, 0.5f));
        if (spr != null)
        {
            var go = new GameObject($"Atlas_Ferry_{name}") { layer = LayerObjects };
            go.transform.SetParent(root, false);
            var ls = root.lossyScale;                                   // das Ship ist skaliert: Meter sind Meter
            go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f);
            f._car = go.AddComponent<SpriteRenderer>();
            f._car.sprite = spr;
            AtlasMuseumBuilder.Mask(f._car);
        }
        f.Place(0f);
        All.Add(f);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {name}: {f._length:F1} m, {f._length / speed:F1} s per ride");
        return f;
    }

    /// <summary>Host: where every vehicle stands, for a client who does not know it (a player who
    /// joined, audit 04.10.: a newcomer assumed every vehicle at landing A).</summary>
    public static void HostSyncAll()
    {
        if (!AmHost) return;
        foreach (var f in All)
        {
            if (f._t0 > 0f) continue;
            byte id = f._id, at = f._at;
            AtlasWorld.Send(OpFerry, w => { w.Write(SubSync); w.Write(id); w.Write(at); w.Write((byte)0); });
        }
    }

    public static void ResetAll()
    {
        foreach (var f in All) f.EndLocal(true);
        All.Clear();
    }

    public static bool IsRiding(byte pid)
    {
        foreach (var f in All) if (f._rider == pid && f._t0 > 0f) return true;
        return false;
    }

    public static AtlasFerry Find(string name) => All.Find(f => f._name == name);

    // ------------------------------------------------------------------ Netz

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte(), id = r.ReadByte(), a = r.ReadByte(), b = r.ReadByte();
        if (id >= All.Count) return;
        var f = All[id];
        if (sub == SubReq && AmHost && from != null) f.HostRequest(from.PlayerId, a);
        else if (sub == SubStart && fromHost) f.Apply(a, b);
        else if (sub == SubSync && fromHost && f._t0 <= 0f && a <= 1) { f._at = a; f.Place(a); }
    }

    private void Request(byte station)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        if (AmHost) HostRequest(lp.PlayerId, station);
        else
        {
            byte id = _id;
            AtlasWorld.Send(OpFerry, w => { w.Write(SubReq); w.Write(id); w.Write(station); w.Write((byte)0); });
        }
    }

    private void HostRequest(byte pid, byte station)
    {
        PlayerControl pc = null;
        foreach (var p in PlayerControl.AllPlayerControls) if (p != null && p.PlayerId == pid) pc = p;
        if (pc == null || pc.Data == null || pc.Data.IsDead || pc.Data.Disconnected || station > 1) return;
        if (_t0 > 0f || IsRiding(pid) || AtlasParkFun.IsBusy(pid)) return;
        // The host checks what the asking client only checked for itself (audit 04.10.): no ride in
        // a meeting or exile, from a vent, from the lookout, or from farther than the landing.
        if (MeetingHud.Instance != null || ExileController.Instance != null) return;
        if (pc.inVent || AtlasLookout.IsUp(pid)) return;
        if (Vector2.Distance(pc.GetTruePosition(), station == 0 ? _platA : _platB) > 2.5f) return;
        byte rider = _at == station ? pid : None, from = _at == station ? station : (byte)(1 - station);
        Apply(rider, from);
        byte id = _id;
        AtlasWorld.Send(OpFerry, w => { w.Write(SubStart); w.Write(id); w.Write(rider); w.Write(from); });
    }

    private void Apply(byte rider, byte from)
    {
        if (_t0 > 0f) Finish();
        _rider = rider; _from = from; _t0 = Time.time;
        var lp = PlayerControl.LocalPlayer;
        float d = lp != null ? Vector2.Distance(lp.GetTruePosition(), from == 0 ? _platA : _platB) : 20f;
        AtlasWeatherFx.Sfx(_sound, Mathf.Lerp(0.45f, 0.05f, Mathf.Clamp01(d / 18f)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_name} {(rider == None ? "called (empty)" : $"ride for {rider}")} from {(from == 0 ? "A" : "B")}");
    }

    // ------------------------------------------------------------------ Ablauf

    private float Duration => _rider == None ? _length / _callSpeed : _length / _speed + 2f * Step;

    public static void TickAll(float dt)
    {
        bool meeting = MeetingHud.Instance != null || ExileController.Instance != null;
        foreach (var f in All)
        {
            try { f.Tick(meeting); }
            catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} {f._name} tick: {e.Message}"); }
        }
    }

    private void Tick(bool meeting)
    {
        if (meeting && _t0 > 0f) { EndLocal(true); return; }
        float el = Time.time - _t0;
        if (_t0 > 0f && el > Duration) Finish();
        var lp = PlayerControl.LocalPlayer;
        if (_t0 > 0f)
        {
            float trackT = _length / (_rider == None ? _callSpeed : _speed);
            float k = _rider == None ? el / trackT : Mathf.Clamp01((el - Step) / trackT);
            var carPos = Place(_from == 0 ? k : 1f - k);
            PlayerControl pc = null;
            if (_rider != None) foreach (var p in PlayerControl.AllPlayerControls) if (p != null && p.PlayerId == _rider) pc = p;
            if (pc != null && pc.Data != null && !pc.Data.IsDead)
            {
                AtlasFigure.SetCollide(pc, false);
                AtlasFigure.Pose(pc, Vector2.zero, _riderScale);
                if (pc == lp)
                {
                    _local = true;
                    lp.moveable = false;
                    var plat = _from == 0 ? _platA : _platB;
                    var dest = _from == 0 ? _platB : _platA;
                    Vector2 feet;
                    if (el < Step) feet = Vector2.Lerp(plat, carPos, AtlasFigure.Smooth(el / Step));
                    else if (k < 1f) feet = carPos;
                    else feet = Vector2.Lerp(carPos, dest, AtlasFigure.Smooth(Mathf.Clamp01((el - Step - trackT) / Step)));
                    AtlasFigure.SetPos(lp, feet + new Vector2(0f, AtlasMuseumBuilder.FeetOffset()));
                }
                else if (el > Step && k < 1f && _car != null)
                {
                    var f = pc.GetTruePosition();
                    _car.transform.position = new Vector3(f.x, f.y, AtlasMuseumBuilder.SortZ(f.y + 0.6f));
                }
            }
            return;
        }
        if (lp == null) return;
        for (byte s = 0; s < 2; s++)
        {
            if (!AtlasUse.CanReach(lp, s == 0 ? _platA : _platB, 1.3f)) continue;
            byte station = s;
            AtlasUse.Offer(_at == s ? "RIDE" : "CALL", _icon, () => Request(station));
            break;
        }
    }

    /// <summary>Fahrzeug auf den Fahrweg setzen; u = 0 Anleger A, 1 Anleger B.</summary>
    private Vector2 Place(float u)
    {
        float want = Mathf.Clamp01(u) * _length;
        var p = _path[0];
        var d = _path[1] - _path[0];
        for (int i = 1; i < _path.Length; i++)
        {
            float seg = Vector2.Distance(_path[i - 1], _path[i]);
            if (want <= seg || i == _path.Length - 1)
            {
                p = Vector2.Lerp(_path[i - 1], _path[i], seg > 0f ? Mathf.Clamp01(want / seg) : 0f);
                d = _path[i] - _path[i - 1];
                break;
            }
            want -= seg;
        }
        if (_car != null)
        {
            _car.transform.position = new Vector3(p.x, p.y, AtlasMuseumBuilder.SortZ(p.y + 0.6f));
            _car.transform.eulerAngles = new Vector3(0f, 0f, Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
        }
        return p;
    }

    private void Finish()
    {
        _at = (byte)(1 - _from);
        EndLocal(false);
        Place(_at);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_name} arrived at {(_at == 0 ? "A" : "B")}");
    }

    /// <summary>Fahrt beenden; snap = Meeting (Fahrzeug sofort ans Ziel, kein Ausstiegs-Snap).</summary>
    private void EndLocal(bool snap)
    {
        PlayerControl pc = null;
        if (_rider != None) foreach (var p in PlayerControl.AllPlayerControls) if (p != null && p.PlayerId == _rider) pc = p;
        if (pc != null) { AtlasFigure.Pose(pc, Vector2.zero, 1f); AtlasFigure.SetCollide(pc, true); }
        var lp = PlayerControl.LocalPlayer;
        if (_local && lp != null)
        {
            _local = false;
            if (!snap)
            {
                var dest = _from == 0 ? _platB : _platA;
                try { lp.NetTransform.RpcSnapTo(dest + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
            }
            if (lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null) lp.moveable = true;
        }
        if (snap && _t0 > 0f) { _at = (byte)(1 - _from); Place(_at); }
        _rider = None;
        _t0 = -100f;
    }

    // ------------------------------------------------------------------ Diagnose

    public void Diag(byte station, Action<Vector2> snap)
    {
        snap((station == 0 ? _platA : _platB) + new Vector2(0f, AtlasMuseumBuilder.FeetOffset()));
        Request(station);
    }

    public string DiagState() => $"{_name} {(_t0 > 0f ? "running" : "idle")} at {(_at == 0 ? "A" : "B")}";
}
