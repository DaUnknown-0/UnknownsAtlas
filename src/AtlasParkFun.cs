// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasParkFun - Attraktionen zum Benutzen im Moonlight Carnival (User 01.10.). Achse der Karte ist
// Ablenkung und wechselnde Wege; jede Attraktion bedient sie auf ihre Art:
//   Hau den Lukas   Shooting Gallery. Zuschlagen laesst die Glocke ueber die ganze Karte klingen und
//                   blinkt 4 s auf der Minimap: ein Lockmittel. 25 s Abklingzeit fuer alle.
//   Kostuem         Werkstatt. Das Maskottchen "Moony" verdeckt Farbe, Hut und Namen bis zum Ablegen oder
//                   zum naechsten Meeting. Es gibt nur einen Anzug; jeder darf ihn einmal pro Runde tragen.
//   Riesenrad       Einstieg suedlich des Rads. Eine Runde (18 s) in der unteren Gondel; oben sieht man
//                   weiter (Technik des Hochsitzes: echte Position bleibt am Einstieg, die Figur faehrt
//                   mit der Gondel). Ein Fahrgast zugleich, nicht abbrechbar, am Einstieg angreifbar.
//   Pendelwagen     Achterbahn-Bahnsteige an der Coaster Station und noerdlich des Riesenrads (AtlasFerry).
//
// Netz: RPC 237 Op 13 [Unter-Op] ... Anfragen gehen an den Host (exklusive Dinge, Abklingzeiten), der
// verteilt das Ergebnis an alle. Im Freeplay ist man selbst Host, AtlasWorld.Send ist dort wirkungslos.

using System;
using System.Collections.Generic;
using Hazel;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasParkFun
{
    private const string LogPrefix = "[Atlas/ParkFun]";
    internal const byte OpFun = 13;
    private const byte LukasReq = 0, LukasHit = 1, CostumeReq = 2, CostumeState = 3, WheelReq = 4, WheelStart = 5;
    private const byte None = 255;
    private const int LayerShip = 9, LayerObjects = 12;

    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    private static Transform _root;

    public static void Reset()
    {
        CostumeOff();
        WheelEndLocal(false);
        _root = null;
        _lukasUntil = 0f; _lukasT0 = -10f; _lukas = _puck = _bellGlow = null;
        _wearer = None; _worn.Clear(); _rackFreeAt = 0f; _rack = null; _mascots.Clear(); _lastX.Clear();
        _rider = None; _wheelT0 = -100f; _ring = null; _wheelProp = null; Gondolas.Clear();
        _pingUntil = 0f; _ping = null;
        _meeting = false;
    }

    public static void Build(Transform parkRoot)
    {
        Reset();
        _root = parkRoot;
        BuildLukas();
        BuildRack();
        BuildWheel();
        // Achterbahn-Pendelwagen: Coaster Station (A) <-> Riesenrad-Nordrand (B)
        AtlasFerry.Create(_root, "shuttle", "task_park_shuttle.png", AtlasParkWorldData.ShuttlePath,
            AtlasParkWorldData.ShuttleA, AtlasParkWorldData.ShuttleB, 9f, 14f, 0.8f, "task_btn_coaster.png", "clack");
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: lukas {(_lukas != null ? "yes" : "no")}, wheel {(_ring != null ? "yes" : "no")} " +
                                   $"({Gondolas.Count} gondolas)");
    }

    // ------------------------------------------------------------------ gemeinsame Helfer

    private static SpriteRenderer Spr(string name, Sprite sprite, Vector2 at, float z)
    {
        var go = new GameObject($"Atlas_Fun_{name}") { layer = LayerObjects };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(at.x, at.y, z);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        AtlasMuseumBuilder.Mask(sr);
        return sr;
    }

    private static void Blocker(string name, Vector2 min, Vector2 max)
    {
        var go = new GameObject($"Atlas_Fun_{name}") { layer = LayerShip };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3((min.x + max.x) / 2f, (min.y + max.y) / 2f, 0f);
        go.AddComponent<BoxCollider2D>().size = max - min;
    }

    private static void ToHost(byte sub, byte arg)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        if (AmHost) HostRequest(sub, lp.PlayerId, arg);
        else AtlasWorld.Send(OpFun, w => { w.Write(sub); w.Write(arg); });
    }

    private static void Broadcast(byte sub, byte a, byte b)
    {
        Apply(sub, a, b);
        AtlasWorld.Send(OpFun, w => { w.Write(sub); w.Write(a); w.Write(b); });
    }

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case LukasReq or CostumeReq or WheelReq:
                if (AmHost && from != null) HostRequest(sub, from.PlayerId, r.ReadByte());
                break;
            case LukasHit or CostumeState or WheelStart:
                if (fromHost) Apply(sub, r.ReadByte(), r.ReadByte());
                break;
        }
    }

    private static void HostRequest(byte sub, byte pid, byte arg)
    {
        var pc = Player(pid);
        bool alive = pc != null && pc.Data != null && !pc.Data.IsDead && !pc.Data.Disconnected;
        // wer gerade faehrt, kann nichts anderes anfangen (Ablegen des Kostuems ausgenommen)
        if (sub != CostumeReq && (pid == _rider || AtlasFerry.IsRiding(pid))) return;
        float now = Time.time;
        switch (sub)
        {
            case LukasReq:
                if (!alive || now < _lukasUntil) return;
                Broadcast(LukasHit, pid, 0);
                break;
            case CostumeReq:
                if (arg == 1)
                {
                    if (!alive || _wearer != None || _worn.Contains(pid) || now < _rackFreeAt) return;
                    Broadcast(CostumeState, pid, 0);
                }
                else if (_wearer == pid) Broadcast(CostumeState, None, 0);
                break;
            case WheelReq:
                if (!alive || _rider != None) return;
                Broadcast(WheelStart, pid, 0);
                break;
        }
    }

    private static void Apply(byte sub, byte a, byte b)
    {
        switch (sub)
        {
            case LukasHit: LukasApply(a); break;
            case CostumeState: CostumeApply(a); break;
            case WheelStart: WheelApply(a); break;
        }
    }

    private static PlayerControl Player(byte id)
    {
        if (id == None) return null;
        foreach (var pc in PlayerControl.AllPlayerControls) if (pc != null && pc.PlayerId == id) return pc;
        return null;
    }

    private static float Dist(Vector2 at)
    {
        var lp = PlayerControl.LocalPlayer;
        return lp != null ? Vector2.Distance(lp.GetTruePosition(), at) : 20f;
    }

    // ------------------------------------------------------------------ Takt

    private static bool _meeting;

    public static void Tick(float dt)
    {
        if (_root == null) return;
        try
        {
            var lp = PlayerControl.LocalPlayer;
            bool meeting = MeetingHud.Instance != null || ExileController.Instance != null;
            if (meeting && !_meeting) OnMeeting();
            _meeting = meeting;
            if (AmHost) HostTick();
            LukasTick(lp);
            CostumeTick(lp, dt);
            WheelTick(lp, dt);
            PingTick();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    private static void OnMeeting()
    {
        // Meeting: Kostuem zurueck an den Haken, jeder darf es in der naechsten Runde wieder tragen;
        // Fahrten enden sofort (Figur unten, Gondel und Wagen in der Grundstellung)
        _worn.Clear();
        CostumeApply(None);
        WheelEndLocal(true);
    }

    private static void HostTick()
    {
        if (_wearer != None)
        {
            var pc = Player(_wearer);
            if (pc == null || pc.Data == null || pc.Data.IsDead || pc.Data.Disconnected) Broadcast(CostumeState, None, 0);
        }
    }

    /// <summary>Sichtfaktor (AtlasWorld.VisionFactor): oben im Riesenrad sieht man weiter.</summary>
    public static float VisionFactor => _wheelLocal ? Mathf.Lerp(1f, WheelVision, _wheelHeight) : 1f;

    // ================================================================== Hau den Lukas

    private const float LukasCooldown = 25f, LukasRise = 0.45f, LukasHold = 0.35f, LukasFall = 0.7f;
    private const float LukasPpu = 100f, LukasPivotY = (340f - 318f) / 340f;
    private const float PuckLow = (318f - 250f) / 100f, PuckHigh = (318f - 52f) / 100f;
    private static float _lukasUntil, _lukasT0 = -10f;
    private static SpriteRenderer _lukas, _puck, _bellGlow;

    private static void BuildLukas()
    {
        var spr = AtlasAssets.TaskSprite("task_park_lukas.png", LukasPpu, new Vector2(0.5f, LukasPivotY));
        if (spr == null) return;
        var foot = AtlasParkWorldData.Lukas;
        var rect = AtlasParkWorldData.LukasRect;
        float z = AtlasMuseumBuilder.SortZ(rect.Max.y);              // Hinterkante wie PropSortLine
        _lukas = Spr("Lukas", spr, foot, z);
        _puck = Spr("LukasPuck", AtlasAssets.TaskSprite("task_park_lukas_puck.png", LukasPpu, new Vector2(0.5f, 0.5f)),
            foot + new Vector2(0f, PuckLow), z - 0.00002f);
        _bellGlow = Spr("LukasGlow", Glow, foot + new Vector2(0f, PuckHigh + 0.2f), z - 0.00003f);
        _bellGlow.transform.localScale = new Vector3(1.6f, 1.6f, 1f);
        _bellGlow.color = new Color(1f, 0.85f, 0.45f, 0f);
        Blocker("LukasBlock", rect.Min, rect.Max);
    }

    private static void LukasTick(PlayerControl lp)
    {
        if (_lukas == null) return;
        float el = Time.time - _lukasT0;
        float u;
        if (el < LukasRise) u = 1f - (1f - el / LukasRise) * (1f - el / LukasRise);
        else if (el < LukasRise + LukasHold) u = 1f;
        else if (el < LukasRise + LukasHold + LukasFall) { float k = (el - LukasRise - LukasHold) / LukasFall; u = 1f - k * k; }
        else u = 0f;
        if (_puck != null)
        {
            var foot = AtlasParkWorldData.Lukas;
            var p = _puck.transform.position;
            _puck.transform.position = new Vector3(foot.x, foot.y + Mathf.Lerp(PuckLow, PuckHigh, u), p.z);
        }
        if (_bellGlow != null)
        {
            float g = el >= LukasRise && el < LukasRise + 1.2f ? 1f - (el - LukasRise) / 1.2f : 0f;
            _bellGlow.color = new Color(1f, 0.85f, 0.45f, 0.8f * g);
        }
        if (el >= LukasRise && el - Time.deltaTime < LukasRise)
        {
            // Glocke: ueberall hoerbar, nah lauter
            AtlasWeatherFx.Sfx("ding", Mathf.Lerp(0.9f, 0.35f, Mathf.Clamp01(Dist(AtlasParkWorldData.Lukas) / 35f)));
            Ping(AtlasParkWorldData.Lukas, _diagLongPing ? 12f : 4f);
        }
        if (lp == null || !AtlasUse.CanReach(lp, AtlasParkWorldData.LukasUse, 1.3f)) return;
        float wait = _lukasUntil - Time.time;
        if (wait > 0f) AtlasUse.Offer($"WAIT {Mathf.CeilToInt(wait)}", "task_btn_lukas.png", null, enabled: false);
        else AtlasUse.Offer("STRIKE", "task_btn_lukas.png", () => ToHost(LukasReq, 0));
    }

    private static void LukasApply(byte pid)
    {
        _lukasT0 = Time.time;
        _lukasUntil = Time.time + LukasCooldown;
        AtlasWeatherFx.Sfx("thud", Mathf.Lerp(0.5f, 0.05f, Mathf.Clamp01(Dist(AtlasParkWorldData.Lukas) / 12f)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} lukas struck by {pid}");
    }

    // ------------------------------------------------------------------ Minimap-Signal

    private static float _pingUntil;
    private static Vector2 _pingAt;
    private static SpriteRenderer _ping;

    private static void Ping(Vector2 world, float seconds)
    {
        _pingAt = world;
        _pingUntil = Time.time + seconds;
    }

    private static void PingTick()
    {
        bool on = Time.time < _pingUntil;
        var map = MapBehaviour.Instance;
        if (map == null || map.HerePoint == null || !map.IsOpen)
        {
            if (_ping != null) _ping.enabled = false;
            return;
        }
        if (_ping == null || _ping.transform.parent != map.HerePoint.transform.parent)
        {
            var here = map.HerePoint;
            var go = new GameObject("Atlas_FunPing") { layer = here.gameObject.layer };
            go.transform.SetParent(here.transform.parent, false);
            _ping = go.AddComponent<SpriteRenderer>();
            _ping.sprite = Ring;
            _ping.sharedMaterial = here.sharedMaterial;
            _ping.sortingLayerID = here.sortingLayerID;
            _ping.sortingOrder = here.sortingOrder + 1;
        }
        float scale = ShipStatus.Instance != null ? ShipStatus.Instance.MapScale : 1f;
        var hz = map.HerePoint.transform.localPosition.z;
        _ping.transform.localPosition = new Vector3(_pingAt.x / scale, _pingAt.y / scale, hz - 0.01f);
        float ph = Mathf.Repeat(Time.time * 1.6f, 1f);
        _ping.transform.localScale = Vector3.one * (0.7f + ph * 1.1f);     // Knopfgroesse auf der Karte
        _ping.color = new Color(1f, 0.82f, 0.3f, 1f - ph);
        _ping.enabled = on;
    }

    // ================================================================== Maskottchen-Kostuem

    private const float RackFree = 10f, MascotWidth = 0.95f;
    private const float MascotPivotY = (140f - 134f) / 140f;
    private static byte _wearer = None;
    private static readonly HashSet<byte> _worn = new();
    private static float _rackFreeAt;
    private static SpriteRenderer _rack;
    private static Sprite _mascot0, _mascot1;
    private static readonly Dictionary<byte, SpriteRenderer> _mascots = new();
    private static readonly Dictionary<byte, float> _lastX = new();
    private static readonly List<SpriteRenderer> _hidden = new();
    private static GameObject _hiddenNames;

    private static void BuildRack()
    {
        _mascot0 = AtlasAssets.TaskSprite("task_park_mascot_0.png", 100f, new Vector2(0.5f, MascotPivotY));
        _mascot1 = AtlasAssets.TaskSprite("task_park_mascot_1.png", 100f, new Vector2(0.5f, MascotPivotY));
        if (_mascot0 == null) return;
        // Garderobe: der Anzug haengt als Figur am Staender (ausgegraut, solange er unterwegs ist)
        var at = AtlasParkWorldData.CostumeRack;
        _rack = Spr("CostumeRack", _mascot0, at, AtlasMuseumBuilder.SortZ(at.y + 0.2f));
        _rack.transform.localScale = new Vector3(0.9f, 0.9f, 1f);
        Blocker("RackBlock", at + new Vector2(-0.45f, -0.05f), at + new Vector2(0.45f, 0.45f));
    }

    private static void CostumeTick(PlayerControl lp, float dt)
    {
        if (_rack != null)
        {
            bool home = _wearer == None;
            _rack.color = home ? (Time.time < _rackFreeAt ? new Color(1f, 1f, 1f, 0.55f) : Color.white) : new Color(1f, 1f, 1f, 0f);
        }
        DrawMascot(dt);
        if (lp == null || lp.Data == null) return;
        if (_wearer == lp.PlayerId)
        {
            if (AtlasUse.CanReach(lp, lp.GetTruePosition(), 1f)) AtlasUse.Offer("TAKE OFF", "task_btn_costume.png", () => ToHost(CostumeReq, 0));
            return;
        }
        if (_mascot0 == null || !AtlasUse.CanReach(lp, AtlasParkWorldData.CostumeUse, 1.3f)) return;
        if (_wearer != None) return;
        if (_worn.Contains(lp.PlayerId)) { AtlasUse.Offer("WORN", "task_btn_costume.png", null, enabled: false); return; }
        float wait = _rackFreeAt - Time.time;
        if (wait > 0f) AtlasUse.Offer($"WAIT {Mathf.CeilToInt(wait)}", "task_btn_costume.png", null, enabled: false);
        else AtlasUse.Offer("COSTUME", "task_btn_costume.png", () => ToHost(CostumeReq, 1));
    }

    private static void CostumeApply(byte pid)
    {
        if (pid == _wearer) return;
        if (_wearer != None) { _rackFreeAt = Time.time + RackFree; AtlasWeatherFx.Sfx("pop", 0.25f); }
        CostumeOff();
        _wearer = pid;
        if (pid != None) { _worn.Add(pid); AtlasWeatherFx.Sfx("pop", 0.3f); }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} costume worn by {(pid == None ? "nobody" : pid.ToString())}");
    }

    /// <summary>Verdeckte Teile des bisherigen Traegers wieder zeigen, Maskottchen weg.</summary>
    private static void CostumeOff()
    {
        foreach (var r in _hidden) if (r != null) r.enabled = true;
        _hidden.Clear();
        if (_hiddenNames != null) { _hiddenNames.SetActive(true); _hiddenNames = null; }
        foreach (var m in _mascots.Values) if (m != null) Object.Destroy(m.gameObject);
        _mascots.Clear();
    }

    private static void DrawMascot(float dt)
    {
        if (_wearer == None) return;
        var pc = Player(_wearer);
        if (pc == null || pc.Data == null || pc.Data.IsDead || _meeting) { if (_mascots.Count > 0 || _hidden.Count > 0) CostumeOff(); return; }
        // Farbe, Hut, Visier, Haustier und Namen verdecken; jeden Frame, weil Spiel und TOR sie wieder einschalten
        foreach (var part in new[] { "BodyForms", "Cosmetics" })
        {
            var t = pc.transform.Find(part);
            if (t == null) continue;
            foreach (var r in t.GetComponentsInChildren<SpriteRenderer>(true))
                if (r != null && r.enabled) { r.enabled = false; if (!_hidden.Contains(r)) _hidden.Add(r); }
        }
        var names = pc.transform.Find("Names");
        if (names != null && names.gameObject.activeSelf) { names.gameObject.SetActive(false); _hiddenNames = names.gameObject; }

        if (!_mascots.TryGetValue(_wearer, out var m) || m == null)
        {
            var go = new GameObject("Atlas_Mascot") { layer = pc.gameObject.layer };
            go.transform.SetParent(pc.transform, false);
            m = go.AddComponent<SpriteRenderer>();
            AtlasMuseumBuilder.Mask(m);
            _mascots[_wearer] = m;
        }
        float rs = Mathf.Max(0.05f, pc.transform.lossyScale.x);
        float k = MascotWidth / (_mascot0.bounds.size.x * rs);
        m.transform.localScale = new Vector3(k, k, 1f);
        m.transform.localPosition = new Vector3(0f, -AtlasMuseumBuilder.FeetOffset() / rs, -0.001f);
        // Blickrichtung und Schritt aus der Bewegung
        float x = pc.transform.position.x;
        _lastX.TryGetValue(_wearer, out var lx);
        float vx = dt > 0f ? (x - lx) / dt : 0f;
        _lastX[_wearer] = x;
        if (vx < -0.2f) m.flipX = true; else if (vx > 0.2f) m.flipX = false;
        bool moving = Mathf.Abs(vx) > 0.2f || (pc.MyPhysics != null && pc.MyPhysics.body != null && pc.MyPhysics.body.velocity.sqrMagnitude > 0.05f);
        m.sprite = moving && Mathf.Repeat(Time.time * 6f, 1f) < 0.5f ? _mascot1 : _mascot0;
        m.enabled = pc.Visible && !pc.inVent;
    }

    // ================================================================== Riesenrad-Gondel

    private const float WheelBoardT = 1.0f, WheelTurnT = 16f, WheelExitT = 1.0f, WheelVision = 3.0f, WheelZoom = 6.0f;
    // Licht auf 3/4 der Hoehe, Kamera auf gut halber: oben sieht man weit nach unten in den Park (User 01.10.)
    private const float WheelLightShare = 0.75f, WheelCamShare = 0.55f;
    private const float RiderScale = 0.55f, SeatDrop = 0.72f;
    private static float WheelTotal => WheelBoardT + WheelTurnT + WheelExitT;
    private static byte _rider = None;
    private static float _wheelT0 = -100f, _theta, _wheelHeight;
    private static bool _wheelLocal;
    private static SpriteRenderer _ring, _wheelProp;
    private static readonly List<(SpriteRenderer Back, SpriteRenderer Front)> Gondolas = new();
    private static float _wheelZ;

    private static void BuildWheel()
    {
        var ring = AtlasAssets.TaskSprite("task_park_wheel_ring.png", 100f, new Vector2(0.5f, 0.5f));
        if (ring == null) return;
        var ship = ShipStatus.Instance;
        if (ship != null)
            foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
                if (sr != null && sr.name.StartsWith("Prop_riesenrad_", StringComparison.Ordinal)) { _wheelProp = sr; break; }
        _wheelZ = _wheelProp != null ? _wheelProp.transform.position.z : AtlasMuseumBuilder.SortZ(AtlasParkWorldData.WheelHub.y - 6f);
        _ring = Spr("WheelRing", ring, AtlasParkWorldData.WheelHub, _wheelZ - 0.00002f);
        for (int k = 0; k < 8; k++)
        {
            var back = AtlasAssets.TaskSprite($"task_park_gondola_{k % 3}.png", 100f, new Vector2(0.5f, 0.94f));
            var front = AtlasAssets.TaskSprite($"task_park_gondola_front_{k % 3}.png", 100f, new Vector2(0.5f, 0.94f));
            if (back == null || front == null) continue;
            Gondolas.Add((Spr($"Gondola_{k}", back, AtlasParkWorldData.WheelHub, _wheelZ - 0.00003f),
                          Spr($"GondolaFront_{k}", front, AtlasParkWorldData.WheelHub, _wheelZ - 0.00004f)));
        }
        PlaceGondolas(0f);
    }

    /// <summary>Aufhaengepunkt der Gondel k bei Raddrehung theta (Grad, im Uhrzeigersinn).</summary>
    private static Vector2 GondolaAt(int k, float theta)
    {
        float a = (270f + k * 45f - theta) * Mathf.Deg2Rad;
        return AtlasParkWorldData.WheelHub + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * AtlasParkWorldData.WheelRadius;
    }

    private static void PlaceGondolas(float theta)
    {
        if (_ring != null) _ring.transform.localEulerAngles = new Vector3(0f, 0f, -theta);
        float alpha = _wheelProp != null ? _wheelProp.color.a : 1f;          // Durchsicht-Blende des Gestells mitmachen
        if (_ring != null) _ring.color = new Color(1f, 1f, 1f, alpha);
        for (int k = 0; k < Gondolas.Count; k++)
        {
            var p = GondolaAt(k, theta);
            var (b, f) = Gondolas[k];
            b.transform.position = new Vector3(p.x, p.y, b.transform.position.z);
            f.transform.position = new Vector3(p.x, p.y, f.transform.position.z);
            b.color = f.color = new Color(1f, 1f, 1f, alpha);
        }
    }

    private static void WheelTick(PlayerControl lp, float dt)
    {
        if (_ring == null) return;
        float el = Time.time - _wheelT0;
        if (_rider != None && el > WheelTotal) WheelEndLocal(false);
        float u = _rider != None ? Mathf.Clamp01((el - WheelBoardT) / WheelTurnT) : 0f;
        _theta = 360f * AtlasFigure.Smooth(u);
        PlaceGondolas(_theta);

        var pc = Player(_rider);
        if (pc != null && pc.Data != null && !pc.Data.IsDead && !_meeting)
        {
            // Einsteigen: Figur von der echten Position in die untere Gondel; dann mitfahren; dann zurueck
            float inT = Mathf.Clamp01(el / WheelBoardT), outT = Mathf.Clamp01((el - WheelBoardT - WheelTurnT) / WheelExitT);
            float w = AtlasFigure.Smooth(inT) * (1f - AtlasFigure.Smooth(outT));
            float f = Mathf.Lerp(1f, RiderScale, w);
            Vector2 tr = pc.transform.position;
            var seat = GondolaAt(0, _theta) + new Vector2(0f, -SeatDrop);
            var feetNow = tr + new Vector2(0f, -AtlasMuseumBuilder.FeetOffset() * f);
            AtlasFigure.Pose(pc, (seat - feetNow) * w, f, WheelLightShare);
            AtlasFigure.SetCollide(pc, false);
            // Brustwehr der eigenen Gondel vor die Figur legen
            if (Gondolas.Count > 0)
            {
                var front = Gondolas[0].Front.transform;
                front.position = new Vector3(front.position.x, front.position.y, w > 0.5f ? pc.transform.position.z - 0.0005f : _wheelZ - 0.00004f);
            }
            if (pc == lp)
            {
                _wheelLocal = true;
                lp.moveable = false;
                AtlasFigure.StopBody(lp);
                _wheelHeight = Mathf.Clamp01((seat.y - (AtlasParkWorldData.WheelHub.y - AtlasParkWorldData.WheelRadius - SeatDrop)) / (2f * AtlasParkWorldData.WheelRadius)) * w;
                AtlasView.ZoomTo(WheelZoom, _wheelHeight);
                AtlasView.Offset((seat - (Vector2)lp.transform.position) * w * WheelCamShare);
            }
        }
        else if (_rider != None && pc != null)
        {
            // Fahrgast tot (oder Meeting): Figur zurueck, die Gondel dreht leer zu Ende
            AtlasFigure.Pose(pc, Vector2.zero, 1f);
            AtlasFigure.SetCollide(pc, true);
            if (pc == lp && _wheelLocal) { _wheelLocal = false; _wheelHeight = 0f; AtlasView.Restore(); }
        }

        if (lp == null || _rider != None || !AtlasUse.CanReach(lp, AtlasParkWorldData.WheelBoard, 1.3f)) return;
        AtlasUse.Offer("RIDE", "task_btn_wheel.png", () => ToHost(WheelReq, 0));
    }

    private static void WheelApply(byte pid)
    {
        if (_rider != None) WheelEndLocal(false);
        _rider = pid;
        _wheelT0 = Time.time;
        var lp = PlayerControl.LocalPlayer;
        if (lp != null && lp.PlayerId == pid)
        {
            try { lp.NetTransform.RpcSnapTo(AtlasParkWorldData.WheelBoard + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
            AtlasFigure.StopBody(lp);
        }
        AtlasWeatherFx.Sfx("creak", Mathf.Lerp(0.4f, 0.05f, Mathf.Clamp01(Dist(AtlasParkWorldData.WheelBoard) / 15f)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} wheel ride for {pid}");
    }

    /// <summary>Fahrt beenden; snap = sofort ohne Animation (Meeting).</summary>
    private static void WheelEndLocal(bool snap)
    {
        if (_rider == None) return;
        var pc = Player(_rider);
        if (pc != null) { AtlasFigure.Pose(pc, Vector2.zero, 1f); AtlasFigure.SetCollide(pc, true); }
        var lp = PlayerControl.LocalPlayer;
        if (_wheelLocal)
        {
            _wheelLocal = false;
            _wheelHeight = 0f;
            AtlasView.Restore();
            if (lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null) lp.moveable = true;
        }
        if (Gondolas.Count > 0)
        {
            var front = Gondolas[0].Front.transform;
            front.position = new Vector3(front.position.x, front.position.y, _wheelZ - 0.00004f);
        }
        _rider = None;
        if (snap) _wheelT0 = -100f;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} wheel ride ended{(snap ? " (meeting)" : "")}");
    }

    // ================================================================== Diagnose (AtlasWorld.Diag "fun...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        var lp = PlayerControl.LocalPlayer;
        var feet = new Vector2(0f, AtlasMuseumBuilder.FeetOffset());
        // eine noch offene Karte (funlukasmap) wuerde die naechsten Fotos verdecken
        if (what != "funlukasmap" && MapBehaviour.Instance != null && MapBehaviour.Instance.IsOpen) MapBehaviour.Instance.Close();
        _diagLongPing = what == "funlukasmap";
        switch (what)
        {
            case "funlukas": snap(AtlasParkWorldData.LukasUse + feet); ToHost(LukasReq, 0); break;
            case "funlukasmap": snap(AtlasParkWorldData.LukasUse + feet); ToHost(LukasReq, 0); OpenMap(); break;
            case "funcostume": snap(AtlasParkWorldData.CostumeUse + feet); ToHost(CostumeReq, 1); break;
            case "funcostumedummy":
                foreach (var pc in PlayerControl.AllPlayerControls)
                    if (pc != null && pc != lp && pc.Data != null && !pc.Data.IsDead)
                    {
                        HostRequest(CostumeReq, pc.PlayerId, 1);
                        snap(pc.GetTruePosition() + new Vector2(-1.2f, -0.6f) + feet);
                        break;
                    }
                break;
            case "funwheel": snap(AtlasParkWorldData.WheelBoard + feet); ToHost(WheelReq, 0); break;
            // Foto oben: die Fahrt um 5 s vorstellen (Foto 6 s spaeter = Gondel am Scheitel)
            case "funwheeltop": snap(AtlasParkWorldData.WheelBoard + feet); ToHost(WheelReq, 0); _wheelT0 -= 3.5f; break;
            case "funwheeldummy":
                foreach (var pc in PlayerControl.AllPlayerControls)
                    if (pc != null && pc != lp && pc.Data != null && !pc.Data.IsDead)
                    {
                        try { pc.NetTransform.SnapTo(AtlasParkWorldData.WheelBoard + feet); } catch { }
                        HostRequest(WheelReq, pc.PlayerId, 0);
                        break;
                    }
                snap(AtlasParkWorldData.WheelBoard + new Vector2(-2.5f, -1.0f) + feet);
                break;
            case "funshuttle": AtlasFerry.Find("shuttle")?.Diag(0, snap); break;
            case "funshuttleback": AtlasFerry.Find("shuttle")?.Diag(1, snap); break;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag {what}: wearer {_wearer}, rider {_rider}, " +
                                   $"lukas cd {Mathf.Max(0f, _lukasUntil - Time.time):F1}");
    }

    private static bool _diagLongPing;

    private static void OpenMap()
    {
        try { if (HudManager.InstanceExists) HudManager.Instance.ToggleMapVisible(new MapOptions { Mode = MapOptions.Modes.Normal }); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} map: {e.Message}"); }
    }

    public static string DiagState() =>
        $"fun: wearer {_wearer}, rider {_rider} (theta {_theta:F0}), {AtlasFerry.Find("shuttle")?.DiagState()}";

    /// <summary>Faehrt der Spieler gerade Riesenrad (AtlasFerry lehnt dann ab)?</summary>
    public static bool IsBusy(byte pid) => pid != None && pid == _rider;

    // ------------------------------------------------------------------ prozedurale Sprites

    private static Sprite _glow, _ring2;
    private static Sprite Glow => _glow ??= Make(64, 64, (x, y) =>
    {
        float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f, r = Mathf.Sqrt(dx * dx + dy * dy);
        float a = Mathf.Clamp01(1f - r);
        return new Color32(255, 255, 255, (byte)(a * a * 255));
    });
    private static Sprite Ring => _ring2 ??= Make(48, 48, (x, y) =>
    {
        float dx = x - 23.5f, dy = y - 23.5f, r = Mathf.Sqrt(dx * dx + dy * dy);
        return r > 23.5f || r < 17f ? new Color32(0, 0, 0, 0) : new Color32(255, 255, 255, 255);
    });

    private static Sprite Make(int w, int h, Func<int, int, Color32> f)
    {
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        var px = new Color32[w * h];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                px[y * w + x] = f(x, y);
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Bilinear;
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.Apply(false, false);
        tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var s = Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f);
        s.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        return s;
    }
}
