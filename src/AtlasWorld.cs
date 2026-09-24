// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasWorld - lebendige Karten: Wetter, Blitze, eigene Sabotagen und Laserschranken.
//
// Host-autoritativ ueber RPC 237 (ID-Registry): [237][Op][Payload]
//   1 Weather   [state]                 Host -> alle: 0 klar, 1 Regen, 2 Nebel, 3 Sturm (nur Wald)
//   2 Strike    [x*100 short][y*100 short]  Host -> alle: Blitzeinschlag (Blitz, Donner)
//   3 SabStart  [kind][count][idx...]  Host -> alle: 1 Sturmholz (Baum-Indizes)
//   4 SabReq    [kind]                  Impostor -> Host: bittet um Sturmholz (Kartenknopf)
//   5 Repair    [kind][arg]             beliebig -> Host: Baum zersaegt
//   6 SabEnd    [kind][arg]             Host -> alle: Sabotage (bzw. ein Baum) beendet
//   7 EjectScene [normal][skip]         Host -> alle: Szenen fuer den naechsten Rauswurf bzw. Skip (AtlasEject)
//   8 Hello [maj][min][build][rev][on]  jeder -> alle, auch in der Lobby: Versions-Abgleich (AtlasHandshake)
//   9 BuildFailed                       Gast -> Host: Atlas-Karte wurde bei mir nicht gebaut (AtlasHandshake)
//  10 ParkEvent [art]                   Host -> alle: Fahrgeschaeft im Park startet (AtlasParkWorld)
//
// Wald: Regen und Sturm verlangsamen den Waldbrand-Countdown (Reaktor-System) auf die Haelfte. Im
// Sturm kann ein Blitz einen Waldbrand ausloesen, auch waehrend Licht oder Comms sabotiert sind
// (zwei Sabotagen gleichzeitig), oder einen Baum quer ueber einen Weg werfen.
// Museum: Laserschranken in den Durchgaengen; jeder Durchgang wird im Kamera-Minispiel protokolliert.
// Jeder Client wertet die Schranken selbst aus (Spielerpositionen sind ohnehin synchron).

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasWorld
{
    private const string LogPrefix = "[Atlas/World]";
    public const byte RpcId = 237;
    private const byte OpWeather = 1, OpStrike = 2, OpSabStart = 3, OpSabReq = 4, OpRepair = 5, OpSabEnd = 6, OpEjectScene = 7;
    public const byte SabTrees = 1;

    public enum Weather : byte { Clear, Rain, Fog, Storm }

    private static bool Wald => AtlasMuseumBuilder.D.Key == "wald";
    private static bool Museum => AtlasMuseumBuilder.D.Key == "museum";
    private static bool Park => AtlasMuseumBuilder.D.Key == "park";
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;

    // ------------------------------------------------------------------ Zustand
    public static Weather CurrentWeather { get; private set; }
    private static float _weatherUntil, _nextStrike, _sabCooldownUntil;
    private static Transform _root;
    private static readonly List<(Vector2 C, bool Vertical, float Len)> TreeSpots = new();
    private static readonly Dictionary<int, GameObject> Trees = new();
    private static readonly Dictionary<int, float> TreeUntil = new();

    public static void Reset()
    {
        CurrentWeather = Weather.Clear;
        _weatherUntil = 0f; _nextStrike = 0f; _sabCooldownUntil = 0f;
        Trees.Clear(); TreeUntil.Clear(); TreeSpots.Clear();
        Lasers.Clear(); LaserLog.Clear(); LastPos.Clear();
        _root = null;
        AtlasWeatherFx.Reset();
        AtlasParkWorld.Reset();
    }

    /// <summary>Nach dem Kartenbau: Baum-Stellen, Nebelmaschine, Laserschranken anlegen.</summary>
    public static void OnBuilt(ShipStatus ship)
    {
        Reset();
        var go = new GameObject("Atlas_World");
        go.transform.SetParent(ship.transform, false);
        _root = go.transform;
        _weatherUntil = Time.time + Random.Range(40f, 70f);   // jede Runde beginnt mit klarem Himmel
        var D = AtlasMuseumBuilder.D;
        if (Wald)
        {
            // Sturmholz: quer ueber die Waldwege (Flurflaechen), Ausrichtung nach der langen Seite
            foreach (var h in D.Hallways)
            {
                if (h == null || h.Length < 3) continue;
                float x0 = float.MaxValue, y0 = float.MaxValue, x1 = float.MinValue, y1 = float.MinValue;
                foreach (var p in h) { x0 = Mathf.Min(x0, p.x); y0 = Mathf.Min(y0, p.y); x1 = Mathf.Max(x1, p.x); y1 = Mathf.Max(y1, p.y); }
                float w = x1 - x0, hh = y1 - y0;
                if (Mathf.Max(w, hh) < 3f || Mathf.Min(w, hh) > 4.5f) continue;
                bool horizontalPath = w > hh;
                TreeSpots.Add((new Vector2((x0 + x1) / 2f, (y0 + y1) / 2f), horizontalPath, Mathf.Min(w, hh) + 0.8f));
            }
        }
        else if (Museum)
        {
            BuildLasers();
        }
        if (Park) AtlasParkWorld.Build(ship, _root);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: {TreeSpots.Count} tree spot(s), {Lasers.Count} laser(s)");
    }

    // ------------------------------------------------------------------ Netz

    /// <summary>Host: Rauswurf-Szene an alle (AtlasEject.HostPick).</summary>
    internal static void SendEjectScene(byte normal, byte skip) => Send(OpEjectScene, w => { w.Write(normal); w.Write(skip); });

    internal static void Send(byte op, Action<MessageWriter> body)
    {
        try
        {
            if (AmongUsClient.Instance == null || AmongUsClient.Instance.NetworkMode == NetworkModes.FreePlay || PlayerControl.LocalPlayer == null) return;
            var w = AmongUsClient.Instance.StartRpcImmediately(PlayerControl.LocalPlayer.NetId, RpcId, SendOption.Reliable, -1);
            w.Write(op);
            body?.Invoke(w);
            AmongUsClient.Instance.FinishRpcImmediately(w);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} send {op}: {e.Message}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.HandleRpc))]
    internal static void PlayerControl_HandleRpc_Postfix(PlayerControl __instance, byte callId, MessageReader reader)
    {
        if (callId != RpcId) return;
        try
        {
            var client = AmongUsClient.Instance;
            bool fromHost = __instance != null && client != null && __instance.OwnerId == client.HostId;
            byte op = reader.ReadByte();
            // Versions-Abgleich und Bau-Meldung gelten auch in der Lobby bzw. ohne gebaute Karte
            if (op == AtlasHandshake.OpHello || op == AtlasHandshake.OpBuildFailed) { AtlasHandshake.Receive(op, __instance, reader); return; }
            if (!AtlasMuseumBuilder.Active) return;
            switch (op)
            {
                case OpWeather when fromHost: ApplyWeather((Weather)reader.ReadByte()); break;
                case OpStrike when fromHost: ApplyStrike(new Vector2(reader.ReadInt16() / 100f, reader.ReadInt16() / 100f)); break;
                case OpSabStart when fromHost:
                {
                    byte kind = reader.ReadByte(); int n = reader.ReadByte();
                    var idx = new List<int>();
                    for (int i = 0; i < n; i++) idx.Add(reader.ReadByte());
                    ApplySabStart(kind, idx);
                    break;
                }
                case OpSabEnd when fromHost: ApplySabEnd(reader.ReadByte(), reader.ReadByte()); break;
                case OpSabReq when AmHost: HostSabRequest(__instance, reader.ReadByte()); break;
                case OpRepair when AmHost: HostRepair(reader.ReadByte(), reader.ReadByte()); break;
                case OpEjectScene when fromHost: AtlasEject.NextScene = reader.ReadByte(); AtlasEject.NextSkip = reader.ReadByte(); break;
                case AtlasParkWorld.OpParkEvent when fromHost: AtlasParkWorld.Apply((AtlasParkWorld.Ev)reader.ReadByte()); break;
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} rpc: {e.Message}"); }
    }

    // ------------------------------------------------------------------ Host-Logik

    private static bool CriticalActive()
    {
        var r = SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor);
        var o = SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp);
        return (r != null && r.IsActive) || (o != null && o.IsActive);
    }

    private static void HostTick()
    {
        if (!AmHost || MeetingHud.Instance != null || ExileController.Instance != null) return;
        float now = Time.time;
        if (Park) AtlasParkWorld.HostTick(CriticalActive());
        if (Wald)
        {
            if (now >= _weatherUntil)
            {
                Weather next;
                if (CurrentWeather != Weather.Clear) { next = Weather.Clear; _weatherUntil = now + Random.Range(45f, 90f); }
                else
                {
                    float r = Random.value;
                    next = r < 0.45f ? Weather.Rain : r < 0.75f ? Weather.Fog : Weather.Storm;
                    _weatherUntil = now + (next == Weather.Storm ? Random.Range(30f, 50f) : Random.Range(35f, 60f));
                }
                ApplyWeather(next);
                Send(OpWeather, w => w.Write((byte)next));
                _nextStrike = now + Random.Range(4f, 8f);
            }
            if (CurrentWeather == Weather.Storm && now >= _nextStrike)
            {
                _nextStrike = now + Random.Range(7f, 13f);
                var D = AtlasMuseumBuilder.D;
                var room = D.Rooms[Random.Range(0, D.Rooms.Length)];
                var c = Vector2.zero; foreach (var p in room.Area) c += p; c /= room.Area.Length;
                c += Random.insideUnitCircle * 2f;
                ApplyStrike(c);
                Send(OpStrike, w => { w.Write((short)(c.x * 100f)); w.Write((short)(c.y * 100f)); });
                float roll = Random.value;
                if (roll < 0.3f && !CriticalActive())
                {
                    // Blitz setzt den Wald in Brand - auch neben einer laufenden Licht-/Comms-Sabotage
                    ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor, ReactorSystemType.StartCountdown);
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} lightning started a forest fire");
                }
                else if (roll < 0.5f && Trees.Count == 0 && TreeSpots.Count > 0) HostStartSab(SabTrees, 1);
            }
            foreach (var kv in new List<KeyValuePair<int, float>>(TreeUntil))
                if (now >= kv.Value) { ApplySabEnd(SabTrees, (byte)kv.Key); Send(OpSabEnd, w => { w.Write(SabTrees); w.Write((byte)kv.Key); }); }
        }
    }

    private static void HostSabRequest(PlayerControl from, byte kind)
    {
        if (from == null || from.Data == null || from.Data.Role == null || !from.Data.Role.IsImpostor || from.Data.IsDead) return;
        if (Time.time < _sabCooldownUntil || CriticalActive()) return;
        if (kind == AtlasParkWorld.SabRide)
        {
            if (Park && AtlasParkWorld.HostRide()) _sabCooldownUntil = Time.time + 30f;
            return;
        }
        if (kind != SabTrees || !Wald || Trees.Count > 0) return;
        HostStartSab(kind, Mathf.Min(3, TreeSpots.Count));
        _sabCooldownUntil = Time.time + 30f;
    }

    private static void HostStartSab(byte kind, int trees)
    {
        var idx = new List<int>();
        if (kind == SabTrees)
        {
            var pool = new List<int>();
            for (int i = 0; i < TreeSpots.Count; i++) if (!Trees.ContainsKey(i)) pool.Add(i);
            for (int i = 0; i < trees && pool.Count > 0; i++) { int j = Random.Range(0, pool.Count); idx.Add(pool[j]); pool.RemoveAt(j); }
            foreach (var i in idx) TreeUntil[i] = Time.time + 45f;
        }
        ApplySabStart(kind, idx);
        Send(OpSabStart, w => { w.Write(kind); w.Write((byte)idx.Count); foreach (var i in idx) w.Write((byte)i); });
    }

    private static void HostRepair(byte kind, byte arg)
    {
        if (kind == SabTrees && !Trees.ContainsKey(arg)) return;
        ApplySabEnd(kind, arg);
        Send(OpSabEnd, w => { w.Write(kind); w.Write(arg); });
    }

    /// <summary>Impostor-Knopf auf der Sabotage-Karte.</summary>
    public static void RequestSab(byte kind)
    {
        if (AmHost) HostSabRequest(PlayerControl.LocalPlayer, kind);
        else Send(OpSabReq, w => w.Write(kind));
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyWeather(Weather w)
    {
        CurrentWeather = w;
        AtlasWeatherFx.SetWeather(w);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} weather -> {w}");
    }

    private static void ApplyStrike(Vector2 p) => AtlasWeatherFx.Strike(p);

    private static void ApplySabStart(byte kind, List<int> idx)
    {
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} sabotage {kind} started ({idx.Count})");
        if (kind == SabTrees) foreach (var i in idx) SpawnTree(i);
    }

    private static void ApplySabEnd(byte kind, byte arg)
    {
        if (kind == SabTrees)
        {
            if (Trees.TryGetValue(arg, out var go) && go != null) Object.Destroy(go);
            Trees.Remove(arg); TreeUntil.Remove(arg);
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} sabotage {kind} ended ({arg})");
    }

    // ------------------------------------------------------------------ Sturmholz

    private static void SpawnTree(int i)
    {
        if (i < 0 || i >= TreeSpots.Count || Trees.ContainsKey(i) || _root == null) return;
        var s = TreeSpots[i];
        var go = new GameObject($"Atlas_Tree_{i}") { layer = 9 };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(s.C.x, s.C.y, (s.C.y + 0.36f) / 1000f - 0.001f);
        // Weg waagerecht -> Baum liegt senkrecht quer darueber
        go.transform.localEulerAngles = new Vector3(0, 0, s.Vertical ? 90f : 0f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite("task_fallen_tree.png", 100f, new Vector2(0.5f, 0.5f));
        go.transform.localScale = new Vector3(s.Len / 4.2f, 1f, 1f);
        var col = go.AddComponent<BoxCollider2D>();
        col.size = new Vector2(4.0f, 0.5f);
        Trees[i] = go;
    }

    /// <summary>Sichtfaktor fuer die Lichtberechnung (Wald-Nebel, Sturm).</summary>
    public static float VisionFactor(Vector2 pos)
    {
        float f = 1f;
        if (Wald) f *= CurrentWeather == Weather.Fog ? 0.65f : CurrentWeather == Weather.Storm ? 0.85f : 1f;
        if (Park) f *= AtlasParkWorld.VisionFactor(pos);
        return f;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.CalculateLightRadius))]
    internal static void ShipStatus_CalculateLightRadius_Postfix(ref float __result)
    {
        if (!AtlasMuseumBuilder.Active) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        __result *= VisionFactor(lp.GetTruePosition());
    }

    /// <summary>Regen und Sturm geben der Crew mehr Zeit gegen den Waldbrand (Countdown laeuft halb so schnell).</summary>
    [HarmonyPrefix]
    [HarmonyPatch(typeof(ReactorSystemType), nameof(ReactorSystemType.Deteriorate))]
    internal static void ReactorSystemType_Deteriorate_Prefix(ref float __0)
    {
        if (AtlasMuseumBuilder.Active && Wald && (CurrentWeather == Weather.Rain || CurrentWeather == Weather.Storm)) __0 *= 0.5f;
    }

    // ------------------------------------------------------------------ Welt-Reparaturen (Klick in der Welt)

    private static byte _pendingKind, _pendingArg;
    public static bool IsWorldRepair(string name) => name == "sawlog";

    public static void RepairDone(string name)
    {
        byte kind = SabTrees, arg = _pendingArg;
        if (AmHost) HostRepair(kind, arg);
        else Send(OpRepair, w => { w.Write(kind); w.Write(arg); });
    }

    private static void OpenRepair(string kind, byte arg)
    {
        if (Minigame.Instance != null || Camera.main == null) return;
        _pendingArg = arg;
        var go = new GameObject($"AtlasTask_{kind}") { layer = 5 };
        go.transform.SetParent(Camera.main.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -50f);
        var mg = go.AddComponent<AtlasMinigame>();
        mg.TransType = TransitionType.SlideBottom;
        PlayerTask any = null;
        foreach (var t in PlayerControl.LocalPlayer.myTasks) if (t != null) { any = t; break; }
        mg.Begin(any);
    }

    private static TextMeshPro _hint;

    private static void ClickTick()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.Data == null || lp.Data.IsDead || Minigame.Instance != null || MeetingHud.Instance != null) { ShowHint(null, default); return; }
        var me = lp.GetTruePosition();
        // naechstes reparierbares Objekt in Reichweite
        string kind = null; byte arg = 0; Vector2 at = default; float best = 1.9f;
        foreach (var kv in Trees)
        {
            if (kv.Value == null) continue;
            float d = Vector2.Distance(me, kv.Value.transform.position);
            if (d < best) { best = d; kind = "sawlog"; arg = (byte)kv.Key; at = kv.Value.transform.position; }
        }
        ShowHint(kind, at);
        if (kind == null || !Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, at) < 1.6f) OpenRepair(kind, arg);
    }

    private static void ShowHint(string kind, Vector2 at)
    {
        if (kind == null) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null && _root != null)
        {
            var go = new GameObject("Atlas_Hint") { layer = 11 };
            go.transform.SetParent(_root, false);
            _hint = go.AddComponent<TextMeshPro>();
            var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
            if (src != null) { _hint.font = src.font; _hint.fontSharedMaterial = src.fontSharedMaterial; }
            _hint.fontSize = 2.2f; _hint.alignment = TextAlignmentOptions.Center; _hint.enableWordWrapping = false;
            _hint.color = new Color(1f, 0.9f, 0.4f);
            _hint.rectTransform.sizeDelta = new Vector2(5f, 1f);
            var hmr = go.GetComponent<MeshRenderer>(); if (hmr != null) hmr.sortingOrder = 200;   // ueber Nebel/Wetter
        }
        if (_hint == null) return;
        _hint.gameObject.SetActive(true);
        _hint.text = "CLICK TO SAW";
        _hint.transform.position = new Vector3(at.x, at.y + 1.1f, -2f);
    }

    // ------------------------------------------------------------------ Laserschranken (Museum)

    private static readonly List<(Vector2 A, Vector2 B, string Label, LineRenderer L, float Flash)> Lasers = new();
    private static readonly List<(float T, string Label)> LaserLog = new();
    private static readonly Dictionary<byte, Vector2> LastPos = new();
    private static Material _laserMat;

    private static void BuildLasers()
    {
        var D = AtlasMuseumBuilder.D;
        var slots = new List<(AtlasMuseumLayout.DoorSlot S, bool V)>();
        foreach (var s in D.VerticalDoors) slots.Add((s, true));
        foreach (var s in D.HorizontalDoors) slots.Add((s, false));
        // jede zweite Tuer bekommt eine Schranke (sonst waere das Museum ein Lasergitter)
        for (int i = 0; i < slots.Count; i += 2)
        {
            var (s, v) = slots[i];
            var half = v ? new Vector2(0f, s.Length / 2f) : new Vector2(s.Length / 2f, 0f);
            var a = s.Center - half; var b = s.Center + half;
            var go = new GameObject($"Atlas_Laser_{i}") { layer = 11 };
            go.transform.SetParent(_root, false);
            var lr = go.AddComponent<LineRenderer>();
            lr.useWorldSpace = true;
            lr.positionCount = 2;
            lr.SetPosition(0, new Vector3(a.x, a.y, -0.5f));
            lr.SetPosition(1, new Vector3(b.x, b.y, -0.5f));
            lr.startWidth = lr.endWidth = 0.035f;
            if (_laserMat == null) _laserMat = new Material(Shader.Find("Sprites/Default")) { hideFlags = HideFlags.HideAndDontSave };
            lr.sharedMaterial = _laserMat;
            lr.startColor = lr.endColor = new Color(1f, 0.1f, 0.1f, 0.35f);
            Lasers.Add((a, b, RoomName(s.Center), lr, 0f));
        }
    }

    private static string RoomName(Vector2 p)
    {
        string best = "Hall"; float bd = float.MaxValue;
        foreach (var r in AtlasMuseumBuilder.D.Rooms)
        {
            var c = Vector2.zero; foreach (var q in r.Area) c += q; c /= r.Area.Length;
            float d = Vector2.Distance(c, p);
            if (d < bd) { bd = d; best = r.Name; }
        }
        return best;
    }

    private static bool Cross(Vector2 p1, Vector2 p2, Vector2 a, Vector2 b)
    {
        float D(Vector2 u, Vector2 v, Vector2 w) => (v.x - u.x) * (w.y - u.y) - (v.y - u.y) * (w.x - u.x);
        return D(a, b, p1) * D(a, b, p2) < 0f && D(p1, p2, a) * D(p1, p2, b) < 0f;
    }

    private static void LaserTick(float dt)
    {
        if (Lasers.Count == 0) return;
        foreach (var pc in PlayerControl.AllPlayerControls)
        {
            if (pc == null || pc.Data == null || pc.Data.IsDead || pc.inVent) continue;
            var p = pc.GetTruePosition();
            if (LastPos.TryGetValue(pc.PlayerId, out var prev) && Vector2.Distance(prev, p) < 3f)
                for (int i = 0; i < Lasers.Count; i++)
                {
                    var l = Lasers[i];
                    if (!Cross(prev, p, l.A, l.B)) continue;
                    Lasers[i] = (l.A, l.B, l.Label, l.L, 1f);
                    LaserLog.Add((Time.time, l.Label));
                    if (LaserLog.Count > 20) LaserLog.RemoveAt(0);
                }
            LastPos[pc.PlayerId] = p;
        }
        for (int i = 0; i < Lasers.Count; i++)
        {
            var l = Lasers[i];
            float f = Mathf.Max(0f, l.Flash - dt);
            float a = 0.25f + 0.1f * Mathf.Sin(Time.time * 3f + i) + f * 0.7f;
            l.L.startColor = l.L.endColor = new Color(1f, 0.1f + f * 0.4f, 0.1f, a);
            Lasers[i] = (l.A, l.B, l.Label, l.L, f);
        }
    }

    // ------------------------------------------------------------------ Kamera-Minispiel: Laserprotokoll

    [HarmonyPostfix]
    [HarmonyPatch(typeof(SurveillanceMinigame), nameof(SurveillanceMinigame.Update))]
    internal static void SurveillanceMinigame_Update_Postfix(SurveillanceMinigame __instance)
    {
        if (!AtlasMuseumBuilder.Active || __instance == null || Lasers.Count == 0) return;
        try
        {
            // am Minispiel selbst suchen statt cachen: jede Oeffnung ist eine neue Instanz
            var holder = __instance.transform.Find("Atlas_SurvLog");
            TextMeshPro text;
            if (holder == null)
            {
                var go = new GameObject("Atlas_SurvLog") { layer = __instance.gameObject.layer };
                go.transform.SetParent(__instance.transform, false);
                go.transform.localPosition = new Vector3(0f, -1.72f, -5f);
                // dunkler Streifen unter dem Monitor: die Tastatur darunter ist fast weiss
                // Das Minispiel zeichnet auf eigener Sortierebene: Ebene + hoechste Order uebernehmen,
                // sonst liegt das Protokoll hinter Monitor und Tisch (Autotest 23.09.)
                int layerId = 0, top = 0;
                foreach (var r in __instance.GetComponentsInChildren<SpriteRenderer>(true))
                    if (r != null && r.sortingOrder >= top) { top = r.sortingOrder; layerId = r.sortingLayerID; }
                var bar = MatchKit.Box(go.transform, Vector2.zero, new Vector2(7.6f, 0.34f), new Color(0.04f, 0.06f, 0.05f, 0.92f), 0);
                bar.sortingLayerID = layerId; bar.sortingOrder = top + 1;
                var tgo = new GameObject("text") { layer = go.layer };
                tgo.transform.SetParent(go.transform, false);
                tgo.transform.localPosition = new Vector3(0f, 0f, -0.1f);
                text = tgo.AddComponent<TextMeshPro>();
                var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
                if (src != null) { text.font = src.font; text.fontSharedMaterial = src.fontSharedMaterial; }
                text.fontSize = 1.5f; text.alignment = TextAlignmentOptions.Center; text.enableWordWrapping = false;
                text.color = new Color(0.55f, 1f, 0.6f);
                text.rectTransform.sizeDelta = new Vector2(7.4f, 0.4f);
                var mr = tgo.GetComponent<MeshRenderer>(); if (mr != null) { mr.sortingLayerID = layerId; mr.sortingOrder = top + 2; }
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} laser log on sorting layer {layerId}, order {top + 1}");
            }
            else text = holder.GetComponentInChildren<TextMeshPro>();
            if (text == null) return;
            var parts = new List<string>();
            for (int i = LaserLog.Count - 1; i >= 0 && parts.Count < 4; i--)
            {
                float ago = Time.time - LaserLog[i].T;
                if (ago > 90f) break;
                parts.Add($"{LaserLog[i].Label} {Mathf.FloorToInt(ago)}s");
            }
            text.text = parts.Count > 0 ? "LASER LOG:  " + string.Join("  |  ", parts) : "LASER LOG:  no trips";
        }
        catch { }
    }

    // ------------------------------------------------------------------ Sabotage-Karte: neue Knoepfe

    private static readonly List<(ButtonBehavior B, SpriteRenderer R, byte Kind)> MapButtons = new();

    public static void AddMapButtons(MapBehaviour copy, Func<Vector2, Vector3> mapWorld)
    {
        MapButtons.Clear();
        try
        {
            var ov = copy != null ? copy.infectedOverlay : null;
            if (ov == null || ov.rooms == null) return;
            SpriteRenderer template = null;
            foreach (var r in ov.rooms) if (r != null && r.special != null) { template = r.special; break; }
            if (template == null) return;
            var D = AtlasMuseumBuilder.D;
            var list = new List<(byte Kind, Vector2 W, string Icon, float Scale)>();
            if (Wald && TreeSpots.Count > 0) list.Add((SabTrees, TreeSpots[0].C, "task_fallen_tree.png", 0.16f));
            if (Park) list.Add((AtlasParkWorld.SabRide, AtlasParkWorld.RideButtonSpot(), "task_button.png", 0.45f));
            foreach (var (kind, w, icon, scale) in list)
            {
                var go = Object.Instantiate(template.gameObject, ov.transform);
                go.name = $"Atlas_Sab_{kind}";
                var p = mapWorld(w);
                go.transform.position = new Vector3(p.x, p.y, template.transform.position.z);
                var sr = go.GetComponent<SpriteRenderer>();
                sr.sprite = AtlasAssets.TaskSprite(icon, 100f, new Vector2(0.5f, 0.5f));
                go.transform.localScale = Vector3.one * scale / Mathf.Max(0.01f, ov.transform.lossyScale.x);
                var bb = go.GetComponent<ButtonBehavior>();
                if (bb == null) continue;
                bb.OnClick = new UnityEngine.UI.Button.ButtonClickedEvent();
                byte k = kind;
                bb.OnClick.AddListener((Action)(() => RequestSab(k)));
                MapButtons.Add((bb, sr, kind));
            }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {MapButtons.Count} sabotage map button(s)");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} map buttons: {e.Message}"); }
    }

    private static void MapButtonTick()
    {
        bool cooling = Time.time < _sabCooldownUntil || CriticalActive();
        foreach (var (b, r, kind) in MapButtons)
        {
            if (r == null) continue;
            bool active = Trees.Count > 0 || AtlasParkWorld.EventActive;
            r.color = active ? new Color(1f, 0.4f, 0.4f) : cooling && AmHost ? new Color(0.5f, 0.5f, 0.5f) : Color.white;
        }
    }

    // ------------------------------------------------------------------ Diagnose (AtlasTasks, "world:<was>")

    public static string DiagState() =>
        $"weather {CurrentWeather}, trees {Trees.Count}, lasers {Lasers.Count}, log {LaserLog.Count}" +
        (Park ? "; " + AtlasParkWorld.DiagState() : "");

    private static void Snap(Vector2 p)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp != null) lp.NetTransform.RpcSnapTo(p);
    }

    public static void Diag(string what)
    {
        var D = AtlasMuseumBuilder.D;
        void Weather(Weather w) { _weatherUntil = Time.time + 120f; ApplyWeather(w); Send(OpWeather, x => x.Write((byte)w)); }
        switch (what)
        {
            case "clear": Weather(AtlasWorld.Weather.Clear); break;
            case "rain": Weather(AtlasWorld.Weather.Rain); break;
            case "fog": Weather(AtlasWorld.Weather.Fog); break;
            case "storm": Weather(AtlasWorld.Weather.Storm); _nextStrike = Time.time + 1f; break;
            case "strike":
                ApplyStrike(PlayerControl.LocalPlayer.GetTruePosition() + new Vector2(2f, 1f));
                break;
            case "fire":
                ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)SystemTypes.Reactor);
                foreach (var r in D.Rooms)
                    if (r.Room == SystemTypes.Reactor) { var c = Vector2.zero; foreach (var q in r.Area) c += q; Snap(c / r.Area.Length); }
                break;
            case "firestorm":
                // Waldbrand + Licht gleichzeitig: Blitz darf neben einer nicht-kritischen Sabotage zuenden
                ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)SystemTypes.Electrical);
                Weather(AtlasWorld.Weather.Storm);
                ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor, ReactorSystemType.StartCountdown);
                break;
            // Park (AtlasParkWorld): Fahrgeschaefte sofort, Spieler an eine Stelle mit Blick darauf
            case "coaster": Snap(new Vector2(15.8f, 5.6f)); AtlasParkWorld.DiagStart(AtlasParkWorld.Ev.Coaster); break;
            case "carousel": Snap(new Vector2(-18.25f, 8.0f)); AtlasParkWorld.DiagStart(AtlasParkWorld.Ev.Carousel); break;
            case "ghost":
                Snap(new Vector2(-32.25f, 10.2f));
                AtlasParkWorld.DiagDummyInGhost();
                AtlasParkWorld.DiagStart(AtlasParkWorld.Ev.GhostFlash);
                break;
            case "flume": Snap(new Vector2(32.75f, -6.6f)); AtlasParkWorld.DiagStart(AtlasParkWorld.Ev.Flume); break;
            case "jam": Snap(new Vector2(0f, -16.2f)); AtlasParkWorld.DiagStart(AtlasParkWorld.Ev.TurnstileJam); break;
            case "oneway": AtlasParkWorld.DiagOneWay(); break;
            // Lichtebene: bei einer Laterne stehen (an), dann Park Blackout ausloesen (aus, Neon bleibt)
            case "lamps": Snap(AtlasParkWorldData.Lamps[2] + new Vector2(0f, -1.2f)); break;
            case "blackout":
                Snap(AtlasParkWorldData.Lamps[2] + new Vector2(0f, -1.2f));
                ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)SystemTypes.Electrical);
                break;
            case "trees":
                HostStartSab(SabTrees, 3);
                if (Trees.Count > 0) foreach (var kv in Trees) { Snap((Vector2)kv.Value.transform.position + new Vector2(0f, -1.2f)); break; }
                break;
            case "saw":
                foreach (var kv in Trees) { AtlasMinigame.DiagAuto = true; OpenRepair("sawlog", (byte)kv.Key); break; }
                break;
            case "sabmap":
                // Testspieler zum Impostor machen und die Sabotage-Karte oeffnen (Kartenknoepfe sehen)
                RoleManager.Instance.SetRole(PlayerControl.LocalPlayer, AmongUs.GameOptions.RoleTypes.Impostor);
                HudManager.Instance.ToggleMapVisible(new MapOptions { Mode = MapOptions.Modes.Sabotage });
                break;
            case "sabtap":
                // den Sturmholz-Knopf wie ein Klick ausloesen, dann Karte zu
                foreach (var (b, _, _) in MapButtons) { if (b != null) b.OnClick.Invoke(); break; }
                if (MapBehaviour.Instance != null) MapBehaviour.Instance.Close();
                break;
            case "laser":
                if (Lasers.Count > 0)
                {
                    var l = Lasers[0];
                    var mid = (l.A + l.B) / 2f;
                    var n = new Vector2(-(l.B - l.A).y, (l.B - l.A).x).normalized;
                    LastPos[PlayerControl.LocalPlayer.PlayerId] = mid - n * 0.6f;
                    Snap(mid + n * 0.6f);
                }
                break;
            case "cams": AtlasMapShot.OpenCamerasForDiag(); break;
        }
        _sabCooldownUntil = 0f;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag {what}: {DiagState()}");
    }

    // ------------------------------------------------------------------ Takt

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        if (!AtlasMuseumBuilder.Active || _root == null) return;
        try
        {
            float dt = Time.deltaTime;
            HostTick();
            LaserTick(dt);
            ClickTick();
            MapButtonTick();
            AtlasWeatherFx.Tick(dt, Wald);
            AtlasParkWorld.Tick(dt);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix() => Reset();
}
