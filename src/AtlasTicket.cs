// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasTicket - Sabotage "Conductor's Round" (Polaris Express; User 19.10., Vorbild: die O2-Masken in
// Submerged). Die Impostor rufen den Schaffner: alle Lebenden, auch die Impostor selbst, muessen binnen
// AtlasMapDef.TicketSeconds an einer Fahrkarten-Lochzange (AtlasMapDef.TicketStations) ihren Fahrschein
// stempeln. Wer es nicht schafft, fliegt aus dem Zug: Tod ohne Leiche (Exiled, wie Tode am Meeting-Ende).
// Haben alle gestempelt, ist die Sabotage behoben. Ein Meeting beendet sie wie beim Reaktor.
//
// Jede Karte mit "ticket" in der Kartendatei bekommt die Sabotage (Kartenknopf AtlasWorld.SabTicket); die
// Lochzangen sind Stationen in der Welt (Use-Knopf "STAMP", Minispiel ticketpunch in AtlasMechanicsTicket).
//
// Netz: RPC 237 (AtlasWorld), Op 17 [sub][...]
//   0 Start [sekunden*10 u16]                 Host -> alle
//   1 State [zeit*10 u16][n][ids...]          Host -> alle, alle 0,5 s: wer schon gestempelt hat
//   2 End [grund][n][ids...]                  Host -> alle: 0 alle gestempelt, 1 Meeting, 2 Zeit um (ids = Rauswurf)
//   3 Stamp                                   jeder -> Host: eigener Fahrschein gestempelt
// Gemeinsame Regeln wie beim Rex (AtlasRex): nicht waehrend einer Vanilla-Sabotage oder in deren
// Abklingzeit, Notfallknopf gesperrt, keine zweite Sabotage, danach 30 s Abklingzeit.

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasTicket
{
    private const string LogPrefix = "[Atlas/Ticket]";
    internal const byte OpTicket = 17;
    private const byte SubStart = 0, SubState = 1, SubEnd = 2, SubStamp = 3;
    internal const byte EndAllStamped = 0, EndMeeting = 1, EndLost = 2;
    internal const string Icon = "task_ticket_button.png";
    public const float Reach = 1.3f, PunchHold = 0.7f;

    private static AtlasMapDef D => AtlasMuseumBuilder.D;
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;

    /// <summary>Die Karte hat Lochzangen (Kartendatei "ticket"). Nur die Kartendefinition pruefen, nicht
    /// AtlasMuseumBuilder.Active: beim Anlegen der Sabotage-Kartenknoepfe (AddMapButtons) gilt der Bau noch als
    /// laufend (Playtest 19.10.: "0 sabotage map button(s)").</summary>
    public static bool Available => D != null && D.TicketStations != null && D.TicketStations.Length > 0;

    // ------------------------------------------------------------------ Zustand (alle Clients)
    public static bool Active { get; private set; }
    public static float TimeLeft { get; private set; }
    public static float Countdown { get; private set; } = 60f;
    /// <summary>Wer schon gestempelt hat (vom Host verteilt).</summary>
    public static readonly HashSet<byte> Stamped = new();
    public static bool LocalStamped => PlayerControl.LocalPlayer != null && Stamped.Contains(PlayerControl.LocalPlayer.PlayerId);
    private static bool _localSent;

    // Host
    private static float _hostSendAt;

    public static void Reset()
    {
        Active = false; TimeLeft = 0f; Stamped.Clear(); _localSent = false;
        _hint = null; _arrows.Clear();
    }

    // ------------------------------------------------------------------ Netz

    private static void Send(byte sub, Action<MessageWriter> body) =>
        AtlasWorld.Send(OpTicket, w => { w.Write(sub); body?.Invoke(w); });

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case SubStart when fromHost: ApplyStart(r.ReadUInt16() / 10f); break;
            case SubState when fromHost:
            {
                TimeLeft = r.ReadUInt16() / 10f;
                int n = r.ReadByte();
                Stamped.Clear();
                for (int i = 0; i < n; i++) Stamped.Add(r.ReadByte());
                break;
            }
            case SubEnd when fromHost:
            {
                byte why = r.ReadByte();
                int n = r.ReadByte();
                var ids = new List<byte>();
                for (int i = 0; i < n; i++) ids.Add(r.ReadByte());
                ApplyEnd(why, ids);
                break;
            }
            case SubStamp when AmHost: HostStamp(from); break;
        }
    }

    /// <summary>Minispiel: der eigene Fahrschein ist gestempelt.</summary>
    public static void Stamp()
    {
        if (!Active || _localSent) return;
        _localSent = true;
        AtlasWeatherFx.Sfx("ding", 0.7f);
        if (AmHost) HostStamp(PlayerControl.LocalPlayer);
        else Send(SubStamp, null);
    }

    // ------------------------------------------------------------------ Host

    /// <summary>Kartenknopf eines Impostors (AtlasWorld.HostSabRequest hat Rolle und Abklingzeit geprueft).</summary>
    internal static bool HostTryStart()
    {
        // immer nur eine Krise (Rex/Ticket/Runaway/Smoke, Reaktor, O2) zur Zeit, auch wenn der Aufrufer nicht prueft
        if (!Available || Active || AtlasWorld.CriticalActive()) return false;
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && (sab.AnyActive || sab.Timer > 0f))
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} refused: vanilla sabotage active {sab.AnyActive}, shared cooldown {sab.Timer:F0} s");
            return false;
        }
        HostStart();
        return true;
    }

    internal static void HostStart()
    {
        if (!Available || Active) return;
        _hostSendAt = 0f;
        float sec = D.TicketSeconds > 5f ? D.TicketSeconds : 60f;
        LockSabotages();
        ApplyStart(sec);
        Send(SubStart, w => w.Write((ushort)Mathf.Clamp(Mathf.RoundToInt(sec * 10f), 0, 65535)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: the conductor is coming ({sec:F0} s, {Needed().Count} ticket(s) to stamp)");
    }

    private static void HostStamp(PlayerControl from)
    {
        if (!Active || from == null || from.Data == null || from.Data.IsDead) return;
        if (Stamped.Add(from.PlayerId))
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: {from.Data.PlayerName} stamped ({Stamped.Count}/{Needed().Count})");
    }

    /// <summary>Alle, die stempeln muessen: lebend und verbunden.</summary>
    private static List<byte> Needed()
    {
        var out_ = new List<byte>();
        if (GameData.Instance == null) return out_;
        foreach (var p in GameData.Instance.AllPlayers)
            if (p != null && !p.IsDead && !p.Disconnected && p.Object != null) out_.Add(p.PlayerId);
        return out_;
    }

    private static void HostTick(float dt)
    {
        if (MeetingHud.Instance != null || ExileController.Instance != null) { HostEnd(EndMeeting, new List<byte>()); return; }
        TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        var need = Needed();
        bool all = need.Count > 0;
        foreach (var id in need) if (!Stamped.Contains(id)) { all = false; break; }
        LockSabotages();
        float now = Time.time;
        if (now >= _hostSendAt) { _hostSendAt = now + 0.5f; SendState(); }
        if (all) HostEnd(EndAllStamped, new List<byte>());
        else if (TimeLeft <= 0f)
        {
            var losers = new List<byte>();
            foreach (var id in need) if (!Stamped.Contains(id)) losers.Add(id);
            HostEnd(EndLost, losers);
        }
    }

    /// <summary>Wie bei einer Vanilla-Sabotage (User 19.10.): beim Ausloesen bekommen alle anderen Sabotagen die
    /// normale Abklingzeit von 30 s, die waehrend der Sabotage eingefroren bleibt und erst danach ablaeuft.</summary>
    private static void LockSabotages()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && sab.Timer < 29.5f) AtlasRex.SetSabotageTimer(30f);
    }

    private static void SendState()
    {
        ushort t = (ushort)Mathf.Clamp(Mathf.RoundToInt(TimeLeft * 10f), 0, 65535);
        var ids = new List<byte>(Stamped);
        Send(SubState, w => { w.Write(t); w.Write((byte)ids.Count); foreach (var id in ids) w.Write(id); });
    }

    internal static void HostEnd(byte result, List<byte> losers)
    {
        if (!Active) return;
        SendState();
        Send(SubEnd, w => { w.Write(result); w.Write((byte)losers.Count); foreach (var id in losers) w.Write(id); });
        ApplyEnd(result, losers);
        AtlasRex.SetSabotageTimer(30f);
        AtlasWorld.SetSabCooldown(30f);
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyStart(float sec)
    {
        Active = true;
        Countdown = sec; TimeLeft = sec;
        Stamped.Clear(); _localSent = false;
        _flashStart = Time.time;
        AtlasWeatherFx.Sfx("ding", 0.9f);
        MakeArrows();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} conductor's round: {sec:F0} s");
    }

    private static void ApplyEnd(byte result, List<byte> losers)
    {
        if (!Active) return;
        Active = false;
        FlashTick();
        ClearArrows();
        ShowHint(null, default);
        StripTaskLine();
        AtlasCrisisHud.Hide("ticket");
        int thrown = 0;
        if (result == EndLost)
            foreach (var id in losers) if (ThrowOff(id)) thrown++;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ended: {(result == EndAllStamped ? "all tickets stamped" : result == EndMeeting ? "meeting" : $"time is up, {thrown} thrown off the train")}");
    }

    /// <summary>Rauswurf ohne Leiche (wie TORs Tode am Meeting-Ende); laeuft auf jedem Client fuer dieselbe Liste.</summary>
    private static bool ThrowOff(byte id)
    {
        try
        {
            var info = GameData.Instance != null ? GameData.Instance.GetPlayerById(id) : null;
            var pc = info != null ? info.Object : null;
            if (pc == null || info.IsDead) return false;
            var client = AmongUsClient.Instance;
            if (client != null && client.NetworkMode == NetworkModes.FreePlay && pc == PlayerControl.LocalPlayer)
            {
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} freeplay: {info.PlayerName} would be thrown off the train now");
                return false;
            }
            pc.Exiled();
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {info.PlayerName} thrown off the train");
            return true;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} throw off {id}: {e.Message}"); return false; }
    }

    // ------------------------------------------------------------------ Takt

    public static void Tick(float dt)
    {
        if (!Available || !AtlasMuseumBuilder.Active) return;
        FlashTick();
        if (!Active) return;
        if (AmHost) HostTick(dt);
        else TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        if (!Active) return;
        ArrowsTick();
        TaskLineTick();
        HudLineTick();
        ClickTick();
    }

    private static void HudLineTick()
    {
        int need = 0;
        if (GameData.Instance != null)
            foreach (var p in GameData.Instance.AllPlayers) if (p != null && !p.IsDead && !p.Disconnected) need++;
        var lp = PlayerControl.LocalPlayer;
        bool dead = lp == null || lp.Data == null || lp.Data.IsDead;
        string mine = dead ? "" : LocalStamped ? "   <color=#7CE07C>your ticket is stamped</color>" : "   <color=#FFD27A>stamp your ticket!</color>";
        bool blink = !LocalStamped && !dead && Mathf.Repeat(Time.time, 1f) < 0.5f;
        AtlasCrisisHud.Show("ticket", $"CONDUCTOR'S ROUND  {Mathf.CeilToInt(TimeLeft)}s   ({Stamped.Count}/{need} stamped){mine}",
                            blink ? new Color(1f, 0.45f, 0.4f) : new Color(1f, 0.29f, 0.25f));
    }

    // ------------------------------------------------------------------ Rotes Blinken wie beim Reaktor

    private static SpriteRenderer _flash;
    private static float _flashStart;

    private static void FlashTick()
    {
        bool want = Active && !LocalStamped && MeetingHud.Instance == null && Mathf.Repeat(Time.time - _flashStart, 2f) < 1f;
        if (_flash == null)
        {
            if (!want) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_TicketFlash";
            _flash = go.GetComponent<SpriteRenderer>();
            if (_flash == null) { Object.Destroy(go); return; }
            _flash.enabled = true;
        }
        if (_flash.gameObject.activeSelf != want) _flash.gameObject.SetActive(want);
        if (want) _flash.color = new Color(1f, 0f, 0f, 0.373f);
    }

    // ------------------------------------------------------------------ Pfeile, Aufgabenliste

    private static readonly List<ArrowBehaviour> _arrows = new();

    private static void MakeArrows()
    {
        ClearArrows();
        try
        {
            var template = AtlasRex.VanillaArrow();
            foreach (var p in D.TicketStations)
            {
                ArrowBehaviour ab;
                if (template != null)
                {
                    var go = Object.Instantiate(template.gameObject);
                    go.name = "Atlas_TicketArrow";
                    go.SetActive(true);
                    ab = go.GetComponent<ArrowBehaviour>();
                    if (ab != null)
                    {
                        ab.MaxScale = 0.5f;
                        ab.transform.localScale = Vector3.one * 0.5f;
                        if (ab.image != null) ab.image.color = Color.red;
                    }
                }
                else
                {
                    var go = new GameObject("Atlas_TicketArrow") { layer = 5 };
                    var sr = go.AddComponent<SpriteRenderer>();
                    sr.sprite = AtlasRex.ArrowSprite();
                    sr.color = new Color(1f, 0.3f, 0.25f);
                    ab = go.AddComponent<ArrowBehaviour>();
                    ab.image = sr;
                }
                if (ab == null) continue;
                ab.target = new Vector3(p.x, p.y, 0f);
                _arrows.Add(ab);
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} arrows: {e.Message}"); }
    }

    private static void ArrowsTick()
    {
        var lp = PlayerControl.LocalPlayer;
        bool show = lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null && !LocalStamped;
        foreach (var a in _arrows) if (a != null && a.gameObject.activeSelf != show) a.gameObject.SetActive(show);
    }

    private static void ClearArrows()
    {
        foreach (var a in _arrows) if (a != null) Object.Destroy(a.gameObject);
        _arrows.Clear();
    }

    private const string TaskMark = "<color=#FF4A3F>Conductor's Round";

    private static void TaskLineTick()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel == null || panel.taskText == null) return;
            string text = Strip(panel.taskText.text ?? "");
            int need = 0;
            if (GameData.Instance != null)
                foreach (var p in GameData.Instance.AllPlayers) if (p != null && !p.IsDead && !p.Disconnected) need++;
            string state = LocalStamped ? "<color=#7CE07C>ticket stamped</color>" : "<color=#FFD27A>stamp your ticket!</color>";
            string line = $"{TaskMark}! {Mathf.CeilToInt(TimeLeft)}s</color> {state} <color=#FFFFFF>({Stamped.Count}/{need})</color>\n";
            panel.taskText.text = line + text;
        }
        catch { }
    }

    private static void StripTaskLine()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel != null && panel.taskText != null) panel.taskText.text = Strip(panel.taskText.text ?? "");
        }
        catch { }
    }

    // entfernt die eigene Zeile auch, wenn eine andere Krise (Rex/Ticket/Runaway/Smoke) ihre davor gesetzt hat;
    // vorher nur am Textanfang, dann setzte jede Krise ihre Zeile pro Takt erneut davor (Liste wuchs)
    private static string Strip(string text)
    {
        int at;
        while ((at = text.IndexOf(TaskMark, StringComparison.Ordinal)) >= 0)
        {
            int nl = text.IndexOf('\n', at);
            text = text.Substring(0, at) + (nl >= 0 ? text.Substring(nl + 1) : "");
        }
        return text;
    }

    // ------------------------------------------------------------------ Lochzangen

    private static TextMeshPro _hint;

    private static void ClickTick()
    {
        var lp = PlayerControl.LocalPlayer;
        Vector2 at = default;
        bool near = false;
        if (!LocalStamped)
            foreach (var st in D.TicketStations)
                if (AtlasUse.CanReach(lp, st, Reach)) { near = true; at = st; break; }
        ShowHint(near ? "stamp" : null, at);
        if (!near) return;
        AtlasUse.Offer("STAMP", Icon, OpenStation);
        if (!Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, at + new Vector2(0f, 0.4f)) < 1.2f) OpenStation();
    }

    private static void ShowHint(string kind, Vector2 at)
    {
        if (kind == null) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null)
        {
            var go = new GameObject("Atlas_TicketHint") { layer = 11 };
            if (ShipStatus.Instance != null) go.transform.SetParent(ShipStatus.Instance.transform, false);
            _hint = go.AddComponent<TextMeshPro>();
            var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
            if (src != null) { _hint.font = src.font; _hint.fontSharedMaterial = src.fontSharedMaterial; }
            _hint.fontSize = 2.2f; _hint.alignment = TextAlignmentOptions.Center; _hint.enableWordWrapping = false;
            _hint.color = new Color(1f, 0.85f, 0.45f);
            _hint.rectTransform.sizeDelta = new Vector2(5f, 1f);
            var mr = go.GetComponent<MeshRenderer>(); if (mr != null) mr.sortingOrder = 200;
        }
        _hint.gameObject.SetActive(true);
        _hint.text = "USE TO STAMP";
        _hint.transform.position = new Vector3(at.x, at.y + 1.4f, -2f);
    }

    internal static void OpenStation()
    {
        if (Minigame.Instance != null || Camera.main == null || PlayerControl.LocalPlayer == null) return;
        var go = new GameObject("AtlasTask_ticketpunch") { layer = 5 };
        go.transform.SetParent(Camera.main.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -50f);
        var mg = go.AddComponent<AtlasMinigame>();
        mg.TransType = TransitionType.SlideBottom;
        PlayerTask any = null;
        foreach (var t in PlayerControl.LocalPlayer.myTasks) if (t != null) { any = t; break; }
        mg.Begin(any);
    }

    // ------------------------------------------------------------------ Sperren wie beim Rex

    [HarmonyPostfix]
    [HarmonyPriority(Priority.Last)]
    [HarmonyPatch(typeof(EmergencyMinigame), nameof(EmergencyMinigame.Update))]
    internal static void EmergencyMinigame_Update_Postfix(EmergencyMinigame __instance)
    {
        if (!Active || __instance == null) return;
        try
        {
            __instance.StatusText.text = TranslationController.Instance.GetString(StringNames.EmergencyDuringCrisis, Array.Empty<Il2CppSystem.Object>());
            __instance.NumberText.text = string.Empty;
            __instance.ClosedLid.gameObject.SetActive(true);
            __instance.OpenLid.gameObject.SetActive(false);
            __instance.ButtonActive = false;
        }
        catch { }
    }

    /// <summary>Host: keine zweite Sabotage, solange der Schaffner unterwegs ist.</summary>
    [HarmonyPrefix]
    [HarmonyPatch(typeof(SabotageSystemType), nameof(SabotageSystemType.UpdateSystem))]
    internal static bool SabotageSystemType_UpdateSystem_Prefix() => !Active;

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "ticket...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        if (!Available) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: map has no ticket stations"); return; }
        switch (what)
        {
            case "ticket":
                HostStart();
                break;
            case "ticketstamp":
                if (!Active) HostStart();
                snap(D.TicketStations[0] + new Vector2(0f, 0.7f));      // Raumseite (Station 0 steht an der Suedwand)
                AtlasMinigame.DiagAuto = true;
                OpenStation();
                break;
            case "ticketlose":
                if (!Active) HostStart();
                TimeLeft = 1.5f;
                break;
        }
    }

    public static string DiagState() =>
        $"ticket {(Active ? "round" : "idle")}, time {TimeLeft:F1}, stamped {Stamped.Count}, local {(LocalStamped ? "stamped" : "open")}";

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix()
    {
        if (_flash != null) Object.Destroy(_flash.gameObject);
        _flash = null;
        ClearArrows();
        AtlasCrisisHud.Reset();
        Reset();
    }
}
