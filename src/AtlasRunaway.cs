// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasRunaway - Sabotage "Runaway Train" (Polaris Express, User 19.10., ersetzt den Reaktor). Die Impostor klemmen
// den Regler fest: der Zug beschleunigt (AtlasTrainWorld: Bildlauf, Rattern, Funken), Ueberdruck 0..100 steigt.
// Bremsen geht nur zu zweit gleichzeitig an beiden Zugenden: Dampfbremse im Fuehrerstand (Hebel im Bereich halten,
// Minispiel brakelever) und Handbremse auf der hinteren Plattform (Kurbel, Minispiel handbrake). Beide im Takt:
// Ueberdruck faellt; nur einer: er steht; niemand: er steigt. Bei 0 behoben, bei 100 oder Countdown-Ende
// entgleist der Zug: Impostor gewinnen (ImpostorBySabotage). Meeting beendet sie wie beim Reaktor.
//
// Balancing wie beim Rex: Impostor koennen an den Stationen nur helfen (Fehlbedienung zaehlt 0), mehrere Spieler je
// Station, der Host fuehrt die Listen und rechnet, die Clients melden nur "im Takt an/aus".
//
// Netz: RPC 237 (AtlasWorld), Op 18 [sub][...]
//   0 Start [sekunden*10 u16]                 Host -> alle
//   1 State [ueberdruck][zeit*10 u16][flags]  Host -> alle, alle 0,25 s (flags: 1 Dampfbremse, 2 Handbremse)
//   2 End [grund]                             Host -> alle: 0 behoben, 1 Meeting, 2 entgleist
//   3 Input [station][an]                     jeder -> Host

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasRunaway
{
    private const string LogPrefix = "[Atlas/Runaway]";
    internal const byte OpRunaway = 18;
    private const byte SubStart = 0, SubState = 1, SubEnd = 2, SubInput = 3;
    internal const byte Brake = 0, Handbrake = 1;
    internal const byte EndFixed = 0, EndMeeting = 1, EndLost = 2;
    internal const string Icon = "task_train_runaway_button.png";
    public const float StartOver = 30f, RiseNone = 1.5f, RiseOne = 0f, FallBoth = 6f, Reach = 1.4f;
    public const float LeverMin = 0.55f, LeverMax = 0.85f, CrankMin = 0.6f, CrankMax = 1.5f;

    private static AtlasMapDef D => AtlasMuseumBuilder.D;
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    public static bool Available => D != null && D.RunawaySeconds > 0f;

    // ------------------------------------------------------------------ Zustand (alle Clients)
    public static bool Active { get; private set; }
    public static float Over { get; private set; }
    public static float TimeLeft { get; private set; }
    public static float Countdown { get; private set; } = 45f;
    public static bool BrakeOn { get; private set; }
    public static bool HandbrakeOn { get; private set; }
    /// <summary>Fahrtfaktor fuer AtlasTrainWorld: 1 bei Ueberdruck 0, 2,6 bei 100.</summary>
    public static float SpeedFactor => Active ? 1f + 1.6f * Mathf.Clamp01(Over / 100f) : 1f;
    private static readonly bool[] MyInput = new bool[2];

    // Host
    private static readonly HashSet<byte> BrakeUsers = new(), HandbrakeUsers = new();
    private static float _hostSendAt;

    public static void Reset()
    {
        Active = false; Over = 0f; TimeLeft = 0f; BrakeOn = HandbrakeOn = false;
        MyInput[0] = MyInput[1] = false; BrakeUsers.Clear(); HandbrakeUsers.Clear();
        _hint = null; _arrows.Clear();
    }

    // ------------------------------------------------------------------ Netz

    private static void Send(byte sub, Action<MessageWriter> body) =>
        AtlasWorld.Send(OpRunaway, w => { w.Write(sub); body?.Invoke(w); });

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case SubStart when fromHost: ApplyStart(r.ReadUInt16() / 10f); break;
            case SubState when fromHost:
            {
                Over = r.ReadByte();
                TimeLeft = r.ReadUInt16() / 10f;
                byte f = r.ReadByte();
                BrakeOn = (f & 1) != 0; HandbrakeOn = (f & 2) != 0;
                break;
            }
            case SubEnd when fromHost: ApplyEnd(r.ReadByte()); break;
            case SubInput when AmHost: HostInput(from, r.ReadByte(), r.ReadBoolean()); break;
        }
    }

    /// <summary>Minispiel: dieser Spieler bremst an einer Station richtig (an) oder nicht mehr (aus).</summary>
    public static void SetInput(byte station, bool on)
    {
        if (station > 1 || MyInput[station] == on) return;
        MyInput[station] = on;
        if (!Active && on) return;
        if (AmHost) HostInput(PlayerControl.LocalPlayer, station, on);
        else Send(SubInput, w => { w.Write(station); w.Write(on); });
    }

    // ------------------------------------------------------------------ Host

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
        BrakeUsers.Clear(); HandbrakeUsers.Clear();
        _hostSendAt = 0f;
        float sec = D.RunawaySeconds > 5f ? D.RunawaySeconds : 45f;
        LockSabotages();
        ApplyStart(sec);
        Send(SubStart, w => w.Write((ushort)Mathf.Clamp(Mathf.RoundToInt(sec * 10f), 0, 65535)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: regulator jammed ({sec:F0} s)");
    }

    private static void HostInput(PlayerControl from, byte station, bool on)
    {
        if (!Active || from == null || from.Data == null || from.Data.IsDead || station > 1) return;
        var set = station == Brake ? BrakeUsers : HandbrakeUsers;
        if (on) set.Add(from.PlayerId); else set.Remove(from.PlayerId);
    }

    private static void Prune(HashSet<byte> set)
    {
        if (set.Count == 0) return;
        var gone = new List<byte>();
        foreach (var id in set)
        {
            var info = GameData.Instance != null ? GameData.Instance.GetPlayerById(id) : null;
            if (info == null || info.IsDead || info.Disconnected) gone.Add(id);
        }
        foreach (var id in gone) set.Remove(id);
    }

    private static void LockSabotages()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && sab.Timer < 29.5f) AtlasRex.SetSabotageTimer(30f);
    }

    private static void HostTick(float dt)
    {
        if (MeetingHud.Instance != null || ExileController.Instance != null) { HostEnd(EndMeeting); return; }
        Prune(BrakeUsers); Prune(HandbrakeUsers);
        bool a = BrakeUsers.Count > 0, b = HandbrakeUsers.Count > 0;
        BrakeOn = a; HandbrakeOn = b;
        float rate = a && b ? -FallBoth : a || b ? RiseOne : RiseNone;
        Over = Mathf.Clamp(Over + rate * dt, 0f, 100f);
        TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        LockSabotages();
        float now = Time.time;
        if (now >= _hostSendAt) { _hostSendAt = now + 0.25f; SendState(); }
        if (Over <= 0f) HostEnd(EndFixed);
        else if (Over >= 100f || TimeLeft <= 0f) HostEnd(EndLost);
    }

    private static void SendState()
    {
        byte o = (byte)Mathf.Clamp(Mathf.RoundToInt(Over), 0, 100);
        ushort t = (ushort)Mathf.Clamp(Mathf.RoundToInt(TimeLeft * 10f), 0, 65535);
        byte f = (byte)((BrakeOn ? 1 : 0) | (HandbrakeOn ? 2 : 0));
        Send(SubState, w => { w.Write(o); w.Write(t); w.Write(f); });
    }

    internal static void HostEnd(byte result)
    {
        if (!Active) return;
        SendState();
        ApplyEnd(result);
        Send(SubEnd, w => w.Write(result));
        BrakeUsers.Clear(); HandbrakeUsers.Clear();
        AtlasRex.SetSabotageTimer(30f);
        AtlasWorld.SetSabCooldown(30f);
        if (result == EndLost) EndGame();
    }

    private static void EndGame()
    {
        var client = AmongUsClient.Instance;
        if (client == null || client.NetworkMode == NetworkModes.FreePlay || GameManager.Instance == null)
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} derailed - freeplay: the game would end now (ImpostorBySabotage)");
            return;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} derailed - impostors win by sabotage");
        GameManager.Instance.RpcEndGame(GameOverReason.ImpostorBySabotage, false);
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyStart(float sec)
    {
        Active = true;
        Countdown = sec; TimeLeft = sec; Over = StartOver; BrakeOn = HandbrakeOn = false;
        MyInput[0] = MyInput[1] = false;
        _flashStart = Time.time;
        AtlasWeatherFx.Sfx("rush", 0.8f);
        MakeArrows();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} runaway train: {sec:F0} s");
    }

    private static void ApplyEnd(byte result)
    {
        if (!Active) return;
        Active = false;
        Over = 0f; BrakeOn = HandbrakeOn = false;
        MyInput[0] = MyInput[1] = false;
        FlashTick();
        ClearArrows();
        ShowHint(null, default);
        StripTaskLine();
        AtlasCrisisHud.Hide("runaway");
        if (result == EndLost) AtlasWeatherFx.Sfx("boom", 1f);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ended: {(result == EndFixed ? "train under control" : result == EndMeeting ? "meeting" : "derailed")}");
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
        bool blink = Mathf.Repeat(Time.time, 1f) < 0.5f;
        AtlasCrisisHud.Show("runaway", $"RUNAWAY TRAIN  {Mathf.CeilToInt(TimeLeft)}s   (overspeed {Mathf.RoundToInt(Over)}%   brake {(BrakeOn ? "ON" : "off")}   handbrake {(HandbrakeOn ? "ON" : "off")})",
                            blink ? new Color(1f, 0.45f, 0.4f) : new Color(1f, 0.29f, 0.25f));
        ClickTick();
    }

    // ------------------------------------------------------------------ Rotes Blinken wie beim Reaktor

    private static SpriteRenderer _flash;
    private static float _flashStart;

    private static void FlashTick()
    {
        bool want = Active && MeetingHud.Instance == null && Mathf.Repeat(Time.time - _flashStart, 2f) < 1f;
        if (_flash == null)
        {
            if (!want) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_RunawayFlash";
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
            foreach (var p in new[] { D.RunawayBrake, D.RunawayHandbrake })
            {
                ArrowBehaviour ab;
                if (template != null)
                {
                    var go = Object.Instantiate(template.gameObject);
                    go.name = "Atlas_RunawayArrow";
                    go.SetActive(true);
                    ab = go.GetComponent<ArrowBehaviour>();
                    if (ab != null) { ab.MaxScale = 0.5f; ab.transform.localScale = Vector3.one * 0.5f; if (ab.image != null) ab.image.color = Color.red; }
                }
                else
                {
                    var go = new GameObject("Atlas_RunawayArrow") { layer = 5 };
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
        bool show = lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null;
        foreach (var a in _arrows) if (a != null && a.gameObject.activeSelf != show) a.gameObject.SetActive(show);
    }

    private static void ClearArrows()
    {
        foreach (var a in _arrows) if (a != null) Object.Destroy(a.gameObject);
        _arrows.Clear();
    }

    private const string TaskMark = "<color=#FF4A3F>Runaway Train";

    private static void TaskLineTick()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel == null || panel.taskText == null) return;
            string text = Strip(panel.taskText.text ?? "");
            string line = $"{TaskMark}! {Mathf.CeilToInt(TimeLeft)}s</color> <color=#FFD27A>(overspeed {Mathf.RoundToInt(Over)}%)</color>\n";
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

    // ------------------------------------------------------------------ Stationen

    private static TextMeshPro _hint;

    private static void ClickTick()
    {
        var lp = PlayerControl.LocalPlayer;
        string kind = null; Vector2 at = default;
        if (AtlasUse.CanReach(lp, D.RunawayBrake, Reach)) { kind = "brakelever"; at = D.RunawayBrake; }
        else if (AtlasUse.CanReach(lp, D.RunawayHandbrake, Reach)) { kind = "handbrake"; at = D.RunawayHandbrake; }
        ShowHint(kind, at);
        if (kind == null) return;
        string k = kind;
        AtlasUse.Offer(k == "brakelever" ? "BRAKE" : "WIND", Icon, () => OpenStation(k));
        if (!Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, at + new Vector2(0f, 0.4f)) < 1.2f) OpenStation(kind);
    }

    private static void ShowHint(string kind, Vector2 at)
    {
        if (kind == null) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null)
        {
            var go = new GameObject("Atlas_RunawayHint") { layer = 11 };
            if (ShipStatus.Instance != null) go.transform.SetParent(ShipStatus.Instance.transform, false);
            _hint = go.AddComponent<TextMeshPro>();
            var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
            if (src != null) { _hint.font = src.font; _hint.fontSharedMaterial = src.fontSharedMaterial; }
            _hint.fontSize = 2.2f; _hint.alignment = TextAlignmentOptions.Center; _hint.enableWordWrapping = false;
            _hint.color = new Color(1f, 0.55f, 0.45f);
            _hint.rectTransform.sizeDelta = new Vector2(5f, 1f);
            var mr = go.GetComponent<MeshRenderer>(); if (mr != null) mr.sortingOrder = 200;
        }
        _hint.gameObject.SetActive(true);
        _hint.text = kind == "brakelever" ? "USE TO BRAKE" : "USE TO WIND";
        _hint.transform.position = new Vector3(at.x, at.y + 1.4f, -2f);
    }

    internal static void OpenStation(string kind)
    {
        if (Minigame.Instance != null || Camera.main == null || PlayerControl.LocalPlayer == null) return;
        CrisisLink.UseRunaway();
        var go = new GameObject($"AtlasTask_{kind}") { layer = 5 };
        go.transform.SetParent(Camera.main.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -50f);
        var mg = go.AddComponent<AtlasMinigame>();
        mg.TransType = TransitionType.SlideBottom;
        PlayerTask any = null;
        foreach (var t in PlayerControl.LocalPlayer.myTasks) if (t != null) { any = t; break; }
        mg.Begin(any);
    }

    // ------------------------------------------------------------------ Sperren

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

    [HarmonyPrefix]
    [HarmonyPatch(typeof(SabotageSystemType), nameof(SabotageSystemType.UpdateSystem))]
    internal static bool SabotageSystemType_UpdateSystem_Prefix() => !Active;

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "runaway...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        if (!Available) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: map has no runaway stations"); return; }
        switch (what)
        {
            case "runaway": HostStart(); break;
            case "runawaybrake":
                if (!Active) HostStart();
                snap(D.RunawayBrake + new Vector2(0f, -0.7f));
                AtlasMinigame.DiagAuto = true;
                OpenStation("brakelever");
                break;
            case "runawaywheel":
                if (!Active) HostStart();
                snap(D.RunawayHandbrake + new Vector2(0f, -0.7f));
                AtlasMinigame.DiagAuto = true;
                OpenStation("handbrake");
                break;
            case "runawayboth":
                if (!Active) HostStart();
                if (PlayerControl.LocalPlayer != null) { BrakeUsers.Add(PlayerControl.LocalPlayer.PlayerId); HandbrakeUsers.Add(PlayerControl.LocalPlayer.PlayerId); }
                break;
            case "runawaylose":
                if (!Active) HostStart();
                TimeLeft = 1.5f;
                break;
        }
    }

    public static string DiagState() =>
        $"runaway {(Active ? "active" : "idle")}, over {Over:F0}, time {TimeLeft:F1}, brake {BrakeOn}, handbrake {HandbrakeOn}";

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix()
    {
        if (_flash != null) Object.Destroy(_flash.gameObject);
        _flash = null;
        ClearArrows();
        Reset();
    }
}
