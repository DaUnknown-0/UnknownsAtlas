// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasHandshake - wer in der Lobby welches Atlas hat, und ob die Karte in der Runde wirklich steht.
//
// Atlas-Karten sind Relocate-in-Place auf der Skeld: wer Atlas nicht (oder in einer anderen Version)
// hat, spielt auf der echten Skeld, waehrend alle anderen durchs Museum laufen; fuer ihn gehen die
// anderen durch Waende. Deshalb:
//   1. Versions-Abgleich ueber RPC 237 Op 8 (jeder an alle): Version mit allen vier Stellen und ob der
//      Kartenbau eingeschaltet ist. Der Absender kommt aus dem Transport (OwnerId), nie aus dem Payload.
//   2. Ist eine Atlas-Karte gewaehlt und passt nicht jeder, steht ueber dem Startknopf des Hosts, wer
//      fehlt, und BeginGame wird gesperrt (Prefix false ueberspringt das Original). Vanilla-Karten
//      bleiben frei, dort braucht niemand Atlas.
//   3. Selbsttest in der Runde: soll eine Atlas-Karte stehen und tut es nicht (Bau gescheitert, wie am
//      23.09. durch den Phantom-GameStartManager), bekommt der Spieler eine Meldung, und ein Gast meldet
//      es dem Host (Op 9), damit der sieht, wer auf der falschen Karte spielt.
//   4. Der Abgleich erscheint als Spalte "Atlas" in der Mod-Check-Uebersicht von Forgotten Fixes
//      (AppDomain-Vertrag TORMods.Handshake.*), aber nur solange eine Atlas-Karte gewaehlt ist: sonst
//      waere in jeder Vanilla-Lobby jeder ohne Atlas rot markiert.
// Clients bis 0.3.0.5 kennen Op 8/9 nicht, ignorieren sie und senden selbst nichts. Sie gelten als
// "fehlt oder veraltet", was fuer eine Atlas-Karte auch stimmt.

using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using Hazel;
using UnityEngine;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasHandshake
{
    private const string LogPrefix = "[Atlas/Handshake]";
    internal const byte OpHello = 8, OpBuildFailed = 9;
    private const string Guid = AtlasPlugin.Id;
    private const string BoardRegistry = "TORMods.Handshake.Registry";
    private const string BoardPrefix = "TORMods.Handshake.";
    private const char StatusSep = '\u001f';
    private const string Marker = "Unknown's Atlas";

    private readonly struct Peer
    {
        public readonly Version Version;
        public readonly bool Enabled;
        public Peer(Version version, bool enabled) { Version = version; Enabled = enabled; }
    }

    private static readonly Dictionary<int, Peer> Peers = new();
    private static bool _sent, _boardDirty = true, _boardListed;
    private static float _resendAt, _nextCheck;
    private static List<string> _warn = new();

    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    private static bool Online => AmongUsClient.Instance != null && AmongUsClient.Instance.NetworkMode != NetworkModes.FreePlay;
    private static bool LocalEnabled => AtlasPlugin.CfgEnabled is { Value: true } && AtlasPlugin.CfgBuildPocMap is { Value: true };
    private static bool AtlasMapChosen => AtlasSelection.CurrentKey != null;

    private static Version Norm(Version v) =>
        new(Math.Max(0, v.Major), Math.Max(0, v.Minor), Math.Max(0, v.Build), Math.Max(0, v.Revision));
    private static Version Local => Norm(AtlasPlugin.Version);
    private static string Fmt(Version v) => v.Revision > 0 ? v.ToString(4) : v.ToString(3);

    // ------------------------------------------------------------------ Netz

    private static void SendHello()
    {
        var ac = AmongUsClient.Instance;
        if (ac == null || PlayerControl.LocalPlayer == null) return;
        var v = Local;
        Peers[ac.ClientId] = new Peer(v, LocalEnabled);
        _boardDirty = true;
        AtlasWorld.Send(OpHello, w =>
        {
            w.Write((byte)v.Major); w.Write((byte)v.Minor); w.Write((byte)v.Build); w.Write((byte)v.Revision);
            w.Write(LocalEnabled);
        });
    }

    /// <summary>Aus AtlasWorld.PlayerControl_HandleRpc_Postfix (Kanal 237), vor dessen Active-Pruefung.</summary>
    internal static void Receive(byte op, PlayerControl sender, MessageReader reader)
    {
        var ac = AmongUsClient.Instance;
        if (ac == null || sender == null) return;
        switch (op)
        {
            case OpHello:
            {
                byte a = reader.ReadByte(), b = reader.ReadByte(), c = reader.ReadByte(), d = reader.ReadByte();
                bool enabled = reader.ReadBoolean();
                Peers[sender.OwnerId] = new Peer(new Version(a, b, c, d), enabled);
                _boardDirty = true;
                break;
            }
            case OpBuildFailed when ac.AmHost:
            {
                var def = AtlasPlugin.SelectedMap();
                string who = sender.Data != null ? sender.Data.PlayerName : $"#{sender.OwnerId}";
                AtlasPlugin.Logger.LogError($"{LogPrefix} {who} reports: Atlas map was NOT built on their client");
                Notify($"{who} is not on {(def != null ? def.DisplayName : "the Atlas map")}: the map failed to build for them");
                break;
            }
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnGameJoined))]
    internal static void AmongUsClient_OnGameJoined_Postfix()
    {
        Peers.Clear();
        _sent = false;
        _boardDirty = true;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnPlayerJoined))]
    internal static void AmongUsClient_OnPlayerJoined_Postfix()
    {
        if (PlayerControl.LocalPlayer != null) SendHello();
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.Start))]
    internal static void GameStartManager_Start_Postfix() => _sent = false;

    // ------------------------------------------------------------------ Abgleich

    /// <summary>Alle Spieler, deren Atlas nicht zu meinem passt, mit Grund. Leer = alle passen.</summary>
    internal static List<string> Mismatches()
    {
        var list = new List<string>();
        var ac = AmongUsClient.Instance;
        if (ac == null || ac.allClients == null) return list;
        var local = Local;
        for (int i = 0; i < ac.allClients.Count; i++)
        {
            var c = ac.allClients[i];
            if (c == null || c.Character == null || c.Id == ac.ClientId || c.Character == PlayerControl.LocalPlayer) continue;
            string name = c.Character.Data != null ? c.Character.Data.PlayerName : $"#{c.Id}";
            if (!Peers.TryGetValue(c.Id, out var p)) list.Add($"{name}: Unknown's Atlas missing or outdated");
            else if (p.Version != local) list.Add($"{name}: Atlas v{Fmt(p.Version)} (host v{Fmt(local)})");
            else if (!p.Enabled) list.Add($"{name}: Atlas map building switched off");
        }
        return list;
    }

    // Lobby: Hallo senden, Mod-Check-Spalte pflegen, beim Host die Warnung ueber dem Startknopf.
    // Priority.Low: nach TORs Postfix, der GameStartText jeden Frame neu setzt oder leert.
    [HarmonyPostfix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.Update))]
    [HarmonyPriority(Priority.Low)]
    internal static void GameStartManager_Update_Postfix(GameStartManager __instance)
    {
        try
        {
            if (PlayerControl.LocalPlayer != null)
            {
                if (!_sent) { _sent = true; _resendAt = Time.unscaledTime + 5f; SendHello(); }
                else if (AtlasMapChosen && Time.unscaledTime >= _resendAt) { _resendAt = Time.unscaledTime + 5f; SendHello(); }
            }
            PublishBoard();
            if (!AmHost || !Online || __instance == null || !AtlasMapChosen) return;
            if (__instance.startState == GameStartManager.StartingStates.Countdown) return;
            if (Time.unscaledTime >= _nextCheck) { _nextCheck = Time.unscaledTime + 0.25f; _warn = Mismatches(); }
            if (_warn.Count == 0) return;
            var text = __instance.GameStartText;
            if (text == null || (text.text != null && text.text.Contains(Marker))) return;

            var def = AtlasPlugin.SelectedMap();
            string msg = $"<color=#FFA500FF>{Marker}: {(def != null ? def.DisplayName : "Atlas map")} selected, start blocked until everyone has Atlas v{Fmt(Local)}</color>\n" +
                         $"<color=#FF0000FF>{string.Join("\n", _warn)}</color>";
            text.text = string.IsNullOrEmpty(text.text) ? msg : text.text + "\n" + msg;
            var cam = Camera.main;
            if (cam != null)
            {
                Vector3 tl = cam.ViewportToWorldPoint(new Vector3(0f, 1f, 10f));
                tl.z = text.transform.position.z;
                text.transform.position = tl + new Vector3(0.7f, -0.5f, 0f);
            }
            text.alignment = TMPro.TextAlignmentOptions.TopLeft;
            text.rectTransform.pivot = new Vector2(0f, 1f);
            __instance.GameStartTextParent.SetActive(true);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby tick: {e.Message}"); _nextCheck = Time.unscaledTime + 5f; }
    }

    // Start sperren, solange eine Atlas-Karte gewaehlt ist und nicht jeder dasselbe Atlas hat.
    // HarmonyX fuehrt alle Prefixe aus (auch AtlasSelections Broadcast); false ueberspringt das Original.
    [HarmonyPrefix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.BeginGame))]
    internal static bool GameStartManager_BeginGame_Prefix()
    {
        try
        {
            if (!AmHost || !Online || !AtlasMapChosen) return true;
            var bad = Mismatches();
            if (bad.Count == 0) return true;
            Notify($"Start blocked: not everyone has Unknown's Atlas v{Fmt(Local)} ({string.Join(", ", bad.Select(b => b.Split(':')[0]))})");
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} start blocked: {string.Join(" | ", bad)}");
            return false;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} start gate: {e.Message}"); return true; }
    }

    // ------------------------------------------------------------ Mod-Check-Spalte (Forgotten Fixes)

    private static void PublishBoard()
    {
        try
        {
            if (!AtlasMapChosen) { if (_boardListed) Unlist(); return; }
            if (_boardListed && !_boardDirty) return;
            var status = new Dictionary<int, string>();
            var local = Local;
            foreach (var kv in Peers)
            {
                if (!kv.Value.Enabled) continue;                     // Kartenbau aus = wie fehlend
                int d = local.CompareTo(kv.Value.Version);
                status[kv.Key] = (d > 0 ? "old" : d < 0 ? "new" : "ok") + StatusSep + Fmt(kv.Value.Version);
            }
            AppDomain.CurrentDomain.SetData(BoardPrefix + Guid + ".name", "Atlas");
            AppDomain.CurrentDomain.SetData(BoardPrefix + Guid + ".status", status);
            var reg = AppDomain.CurrentDomain.GetData(BoardRegistry) as string ?? "";
            if (!reg.Split(',').Contains(Guid))
                AppDomain.CurrentDomain.SetData(BoardRegistry, reg == "" ? Guid : reg + "," + Guid);
            _boardListed = true;
            _boardDirty = false;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} board publish: {e.Message}"); }
    }

    private static void Unlist()
    {
        // Der Registry-String wird ersetzt, nie veraendert (Leser vergleichen per Referenz)
        var reg = AppDomain.CurrentDomain.GetData(BoardRegistry) as string ?? "";
        AppDomain.CurrentDomain.SetData(BoardRegistry, string.Join(",", reg.Split(',').Where(g => g.Length > 0 && g != Guid)));
        AppDomain.CurrentDomain.SetData(BoardPrefix + Guid + ".status", null);
        _boardListed = false;
        _boardDirty = true;
    }

    // ------------------------------------------------------------------ Selbsttest in der Runde

    private static ShipStatus _seenShip, _checkedShip;
    private static float _seenAt, _diagDoneAt = -1f;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        try
        {
            DiagFinish();
            var ship = ShipStatus.Instance;
            if (ship == null) { _seenShip = _checkedShip = null; return; }
            if (ship != _seenShip) { _seenShip = ship; _seenAt = Time.time; }
            if (_checkedShip == ship || Time.time - _seenAt < 3f) return;
            _checkedShip = ship;
            var def = AtlasPlugin.SelectedMap();
            if (def == null || !AtlasMuseumBuilder.IsSkeld(ship) || AtlasMuseumBuilder.Active) return;

            AtlasPlugin.Logger.LogError($"{LogPrefix} self check: {def.DisplayName} was selected but NOT built - this client plays the plain Skeld");
            Notify($"Unknown's Atlas: {def.DisplayName} could not be built, you are on the plain Skeld. Please leave and send your BepInEx log to the host.");
            if (!AmHost) AtlasWorld.Send(OpBuildFailed, null);
            if (DiagBuildFail) _diagDoneAt = Time.time + 2f;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} self check: {e.Message}"); }
    }

    private static void Notify(string msg)
    {
        try
        {
            var hud = HudManager.Instance;
            if (hud != null && hud.Notifier != null) hud.Notifier.AddDisconnectMessage(msg);
        }
        catch { }
    }

    // ------------------------------------------------------------------ Diagnose

    /// <summary>TaskTest "buildfail": der Bau wird uebersprungen, der Selbsttest muss anschlagen.</summary>
    internal static bool DiagBuildFail =>
        string.Equals(AtlasPlugin.CfgTaskTest?.Value?.Trim(), "buildfail", StringComparison.OrdinalIgnoreCase);

    private static void DiagFinish()
    {
        if (_diagDoneAt < 0f || Time.time < _diagDoneAt) return;
        _diagDoneAt = -1f;
        try
        {
            string dir = System.IO.Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
            System.IO.Directory.CreateDirectory(dir);
            string file = System.IO.Path.Combine(dir, $"task_buildfail_{DateTime.Now:HHmmss}.png");
            ScreenCapture.CaptureScreenshot(file);
            AtlasPlugin.Logger.LogInfo($"[Atlas/Task] diag shot -> {file}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag shot: {e.Message}"); }
        AtlasPlugin.Logger.LogInfo("[Atlas/Task] diag: all done");
    }
}
