// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasSmoke - Sabotage "Smoke in the Cars" (Polaris Express, User 19.10., ersetzt O2). Im Tender bricht ein
// Kohlenfeuer aus, der Rauch zieht durch den Zug: die Sicht aller Lebenden sinkt mit der Rauchdichte, Rauchwolken
// und Feuerschein (AtlasTrainWorld). Behoben wird sie, indem alle Dachluken (Kartendatei "smoke".hatches, drei
// Orte) einmal aufgekurbelt werden (Minispiel hatchcrank); Impostor koennen sie nicht wieder schliessen. Sind
// alle offen, klart es auf. Countdown-Ende: Impostor gewinnen (ImpostorBySabotage). Meeting beendet sie.
//
// Netz: RPC 237 (AtlasWorld), Op 19 [sub][...]
//   0 Start [sekunden*10 u16]                 Host -> alle
//   1 State [zeit*10 u16][offen bits]         Host -> alle, alle 0,5 s
//   2 End [grund]                             Host -> alle: 0 behoben, 1 Meeting, 2 Zeit um
//   3 Open [luke]                             jeder -> Host: Luke aufgekurbelt

using System;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using System.Collections.Generic;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasSmoke
{
    private const string LogPrefix = "[Atlas/Smoke]";
    internal const byte OpSmoke = 19;
    private const byte SubStart = 0, SubState = 1, SubEnd = 2, SubOpen = 3;
    internal const byte EndFixed = 0, EndMeeting = 1, EndLost = 2;
    internal const string Icon = "task_train_smoke_button.png";
    public const float Reach = 1.4f, MinVision = 0.32f, DensityRise = 0.07f, DensityFall = 0.25f, CrankTurns = 2.5f;

    private static AtlasMapDef D => AtlasMuseumBuilder.D;
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    public static bool Available => D != null && D.SmokeHatches != null && D.SmokeHatches.Length > 0;
    public static int HatchCount => Available ? D.SmokeHatches.Length : 0;

    // ------------------------------------------------------------------ Zustand (alle Clients)
    public static bool Active { get; private set; }
    public static float TimeLeft { get; private set; }
    public static byte OpenBits { get; private set; }
    /// <summary>Rauchdichte 0..1 (lokal geglaettet): Sicht und Wolken.</summary>
    public static float Density { get; private set; }
    public static float VisionFactor => Mathf.Lerp(1f, MinVision, Density);
    /// <summary>Luke, deren Minispiel gerade geoeffnet wird (AtlasMinigame.Create hat keinen Parameter).</summary>
    internal static int PendingHatch;
    private static float _hostSendAt;

    public static bool IsOpen(int i) => (OpenBits & (1 << i)) != 0;
    public static int OpenCount { get { int n = 0; for (int i = 0; i < HatchCount; i++) if (IsOpen(i)) n++; return n; } }

    public static void Reset()
    {
        Active = false; TimeLeft = 0f; OpenBits = 0; Density = 0f; PendingHatch = 0;
        _hint = null; _arrows.Clear();
    }

    // ------------------------------------------------------------------ Netz

    private static void Send(byte sub, Action<MessageWriter> body) =>
        AtlasWorld.Send(OpSmoke, w => { w.Write(sub); body?.Invoke(w); });

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case SubStart when fromHost: ApplyStart(r.ReadUInt16() / 10f); break;
            case SubState when fromHost: TimeLeft = r.ReadUInt16() / 10f; OpenBits = r.ReadByte(); break;
            case SubEnd when fromHost: ApplyEnd(r.ReadByte()); break;
            case SubOpen when AmHost: HostOpen(from, r.ReadByte()); break;
        }
    }

    /// <summary>Minispiel: diese Luke ist aufgekurbelt.</summary>
    public static void OpenHatch(int i)
    {
        if (!Active || i < 0 || i >= HatchCount) return;
        AtlasWeatherFx.Sfx("whoosh", 0.7f);
        if (AmHost) HostOpen(PlayerControl.LocalPlayer, (byte)i);
        else Send(SubOpen, w => w.Write((byte)i));
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
        _hostSendAt = 0f;
        float sec = D.SmokeSeconds > 5f ? D.SmokeSeconds : 60f;
        LockSabotages();
        ApplyStart(sec);
        Send(SubStart, w => w.Write((ushort)Mathf.Clamp(Mathf.RoundToInt(sec * 10f), 0, 65535)));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: fire in the tender ({sec:F0} s, {HatchCount} hatch(es))");
    }

    private static void HostOpen(PlayerControl from, byte i)
    {
        if (!Active || from == null || from.Data == null || from.Data.IsDead || i >= HatchCount) return;
        if (IsOpen(i)) return;
        OpenBits |= (byte)(1 << i);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: hatch {i} opened by {from.Data.PlayerName} ({OpenCount}/{HatchCount})");
    }

    private static void LockSabotages()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && sab.Timer < 29.5f) AtlasRex.SetSabotageTimer(30f);
    }

    private static void HostTick(float dt)
    {
        if (MeetingHud.Instance != null || ExileController.Instance != null) { HostEnd(EndMeeting); return; }
        TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        LockSabotages();
        float now = Time.time;
        if (now >= _hostSendAt) { _hostSendAt = now + 0.5f; SendState(); }
        if (OpenCount >= HatchCount) HostEnd(EndFixed);
        else if (TimeLeft <= 0f) HostEnd(EndLost);
    }

    private static void SendState()
    {
        ushort t = (ushort)Mathf.Clamp(Mathf.RoundToInt(TimeLeft * 10f), 0, 65535);
        byte bits = OpenBits;
        Send(SubState, w => { w.Write(t); w.Write(bits); });
    }

    internal static void HostEnd(byte result)
    {
        if (!Active) return;
        SendState();
        ApplyEnd(result);
        Send(SubEnd, w => w.Write(result));
        AtlasRex.SetSabotageTimer(30f);
        AtlasWorld.SetSabCooldown(30f);
        if (result == EndLost) EndGame();
    }

    private static void EndGame()
    {
        var client = AmongUsClient.Instance;
        if (client == null || client.NetworkMode == NetworkModes.FreePlay || GameManager.Instance == null)
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} time is up - freeplay: the game would end now (ImpostorBySabotage)");
            return;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} time is up - impostors win by sabotage");
        GameManager.Instance.RpcEndGame(GameOverReason.ImpostorBySabotage, false);
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyStart(float sec)
    {
        Active = true;
        TimeLeft = sec; OpenBits = 0;
        _flashStart = Time.time;
        AtlasWeatherFx.Sfx("fire", 0.8f);
        MakeArrows();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} smoke in the cars: {sec:F0} s");
    }

    private static void ApplyEnd(byte result)
    {
        if (!Active) return;
        Active = false;
        FlashTick();
        ClearArrows();
        ShowHint(false, default);
        StripTaskLine();
        AtlasCrisisHud.Hide("smoke");
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ended: {(result == EndFixed ? "hatches open, smoke clears" : result == EndMeeting ? "meeting" : "time is up")}");
    }

    // ------------------------------------------------------------------ Takt

    public static void Tick(float dt)
    {
        if (!Available || !AtlasMuseumBuilder.Active) return;
        FlashTick();
        // Rauchdichte: steigt waehrend der Sabotage auf den Anteil geschlossener Luken, faellt danach
        float target = Active ? (HatchCount - OpenCount) / (float)Mathf.Max(1, HatchCount) : 0f;
        Density = Mathf.MoveTowards(Density, target, (target > Density ? DensityRise : DensityFall) * dt);
        if (!Active) return;
        if (AmHost) HostTick(dt);
        else TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        if (!Active) return;
        ArrowsTick();
        TaskLineTick();
        bool blink = Mathf.Repeat(Time.time, 1f) < 0.5f;
        AtlasCrisisHud.Show("smoke", $"SMOKE IN THE CARS  {Mathf.CeilToInt(TimeLeft)}s   (hatches open {OpenCount}/{HatchCount})",
                            blink ? new Color(1f, 0.45f, 0.4f) : new Color(1f, 0.29f, 0.25f));
        ClickTick();
    }

    // ------------------------------------------------------------------ Rotes Blinken

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
            go.name = "Atlas_SmokeFlash";
            _flash = go.GetComponent<SpriteRenderer>();
            if (_flash == null) { Object.Destroy(go); return; }
            _flash.enabled = true;
        }
        if (_flash.gameObject.activeSelf != want) _flash.gameObject.SetActive(want);
        if (want) _flash.color = new Color(1f, 0f, 0f, 0.373f);
    }

    // ------------------------------------------------------------------ Pfeile, Aufgabenliste

    private static readonly List<(ArrowBehaviour A, int Hatch)> _arrows = new();

    private static void MakeArrows()
    {
        ClearArrows();
        try
        {
            var template = AtlasRex.VanillaArrow();
            for (int i = 0; i < HatchCount; i++)
            {
                var p = D.SmokeHatches[i];
                ArrowBehaviour ab;
                if (template != null)
                {
                    var go = Object.Instantiate(template.gameObject);
                    go.name = "Atlas_SmokeArrow";
                    go.SetActive(true);
                    ab = go.GetComponent<ArrowBehaviour>();
                    if (ab != null) { ab.MaxScale = 0.5f; ab.transform.localScale = Vector3.one * 0.5f; if (ab.image != null) ab.image.color = Color.red; }
                }
                else
                {
                    var go = new GameObject("Atlas_SmokeArrow") { layer = 5 };
                    var sr = go.AddComponent<SpriteRenderer>();
                    sr.sprite = AtlasRex.ArrowSprite();
                    sr.color = new Color(1f, 0.3f, 0.25f);
                    ab = go.AddComponent<ArrowBehaviour>();
                    ab.image = sr;
                }
                if (ab == null) continue;
                ab.target = new Vector3(p.x, p.y, 0f);
                _arrows.Add((ab, i));
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} arrows: {e.Message}"); }
    }

    private static void ArrowsTick()
    {
        var lp = PlayerControl.LocalPlayer;
        bool alive = lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null;
        foreach (var (a, i) in _arrows)
        {
            if (a == null) continue;
            bool show = alive && !IsOpen(i);
            if (a.gameObject.activeSelf != show) a.gameObject.SetActive(show);
        }
    }

    private static void ClearArrows()
    {
        foreach (var (a, _) in _arrows) if (a != null) Object.Destroy(a.gameObject);
        _arrows.Clear();
    }

    private const string TaskMark = "<color=#FF4A3F>Smoke in the Cars";

    private static void TaskLineTick()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel == null || panel.taskText == null) return;
            string text = Strip(panel.taskText.text ?? "");
            string line = $"{TaskMark}! {Mathf.CeilToInt(TimeLeft)}s</color> <color=#FFD27A>(hatches {OpenCount}/{HatchCount})</color>\n";
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

    // ------------------------------------------------------------------ Luken

    private static TextMeshPro _hint;

    private static void ClickTick()
    {
        var lp = PlayerControl.LocalPlayer;
        int near = -1; Vector2 at = default;
        for (int i = 0; i < HatchCount; i++)
            if (!IsOpen(i) && AtlasUse.CanReach(lp, D.SmokeHatches[i], Reach)) { near = i; at = D.SmokeHatches[i]; break; }
        ShowHint(near >= 0, at);
        if (near < 0) return;
        int h = near;
        AtlasUse.Offer("OPEN", Icon, () => OpenStation(h));
        if (!Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, at + new Vector2(0f, 0.4f)) < 1.2f) OpenStation(h);
    }

    private static void ShowHint(bool on, Vector2 at)
    {
        if (!on) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null)
        {
            var go = new GameObject("Atlas_SmokeHint") { layer = 11 };
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
        _hint.text = "USE TO OPEN THE HATCH";
        _hint.transform.position = new Vector3(at.x, at.y + 1.4f, -2f);
    }

    internal static void OpenStation(int hatch)
    {
        if (Minigame.Instance != null || Camera.main == null || PlayerControl.LocalPlayer == null) return;
        PendingHatch = hatch;
        var go = new GameObject("AtlasTask_hatchcrank") { layer = 5 };
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

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "smoke...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        if (!Available) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: map has no hatches"); return; }
        switch (what)
        {
            case "smoke": HostStart(); break;
            case "smokehatch":
                if (!Active) HostStart();
                snap(D.SmokeHatches[0] + new Vector2(0f, -0.7f));
                AtlasMinigame.DiagAuto = true;
                OpenStation(0);
                break;
            case "smokeall":
                if (!Active) HostStart();
                OpenBits = (byte)((1 << HatchCount) - 1);
                break;
            case "smokelose":
                if (!Active) HostStart();
                TimeLeft = 1.5f;
                break;
        }
    }

    public static string DiagState() =>
        $"smoke {(Active ? "active" : "idle")}, time {TimeLeft:F1}, open {OpenCount}/{HatchCount}, density {Density:F2}";

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
