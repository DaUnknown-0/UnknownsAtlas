// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasTaskDefer - Task-Listen erst nach dem Kartenbau anlegen (Bug 30.10., Hollowmere Manor).
//
// Spielbericht: bei wechselnden Gaesten (nie beim Host) standen nur 2 oder 3 von 8 Tasks in der Liste, der Rest fehlte
// komplett (keine Zeile, keine Markierung, Konsole tot). Das Log einer Betroffenen zeigte: ihr Client hatte nur die
// beiden Common-Tasks angelegt.
//
// Ursache: Atlas baut die Karte in ShipStatus.Start (AtlasMuseumBuilder) und haengt erst dort die geliehenen Aufgaben
// anderer Karten an (AtlasForeignTasks, Index 30 und hoeher). Vanilla PlayerControl.SetTasks -> CoSetTasks wartet aber nur
// auf ShipStatus.Instance, das schon in Awake steht. Kommen Schiff und Task-Liste beim Gast im selben Netzwerkpaket an,
// legt CoSetTasks die Tasks VOR dem Bau an: GetTaskById findet die geliehene Aufgabe nicht, die Koroutine bricht ab, und
// alles danach (Common zuerst, dann Long, dann Short) fehlt. Der Host verteilt erst nach seinem eigenen Bau und ist nie
// betroffen.
//
// Fix: solange eine Atlas-Karte gewaehlt ist und das Schiff noch nicht gestartet (gebaut) ist, haelt ein Prefix den
// SetTasks-Aufruf an und spielt ihn nach ShipStatus.Start (nach dem Bau, Priority.Last) unveraendert ab. Sicherheitsnetz:
// spaetestens nach MaxWait Sekunden mit Schiff wird trotzdem abgespielt.

using System;
using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasTaskDefer
{
    private const string LogPrefix = "[Atlas/TaskDefer]";
    private const float MaxWait = 8f;

    private static ShipStatus _started;
    private static bool _replaying;
    private static float _since = -1f;
    private static readonly List<(PlayerControl Player, Il2CppSystem.Collections.Generic.List<NetworkedPlayerInfo.TaskInfo> Tasks)> Held = new();

    private static bool AtlasRound() =>
        AtlasPlugin.CfgEnabled is { Value: true } && AtlasPlugin.CfgBuildPocMap is { Value: true } && AtlasPlugin.SelectedMap() != null;

    private static bool Ready()
    {
        var ship = ShipStatus.Instance;
        return ship != null && ship == _started;
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.SetTasks), typeof(Il2CppSystem.Collections.Generic.List<NetworkedPlayerInfo.TaskInfo>))]
    private static bool SetTasks_Prefix(PlayerControl __instance, Il2CppSystem.Collections.Generic.List<NetworkedPlayerInfo.TaskInfo> tasks)
    {
        if (_replaying || __instance == null) return true;
        try
        {
            if (!AtlasRound() || Ready()) return true;
            // die neueste Liste je Spieler gilt (ein zweites SetTasks vor dem Bau ersetzt die erste)
            Held.RemoveAll(h => h.Player == null || h.Player == __instance);
            // eigene Kopie: die Liste des Aufrufers kann bis zum Abspielen wiederverwendet werden
            var copy = new Il2CppSystem.Collections.Generic.List<NetworkedPlayerInfo.TaskInfo>();
            if (tasks != null) foreach (var t in tasks) copy.Add(t);
            Held.Add((__instance, copy));
            if (_since < 0f) _since = Time.realtimeSinceStartup;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {Name(__instance)}: {copy.Count} task(s) held until the map is built" +
                $" (ship {(ShipStatus.Instance == null ? "not there yet" : "not started yet")})");
            return false;
        }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"{LogPrefix} hold failed, vanilla path: {e.Message}");
            return true;
        }
    }

    // nach AtlasMuseumBuilder.ShipStatus_Start_Postfix (Bau), auch wenn gar nicht gebaut wird
    [HarmonyPostfix]
    [HarmonyPriority(Priority.Last)]
    [HarmonyPatch(typeof(ShipStatus), "Start")]
    private static void ShipStatus_Start_Postfix(ShipStatus __instance)
    {
        _started = __instance;
        _startedAt = Time.realtimeSinceStartup;
        _repaired = 0;
        Replay("map built");
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    private static void ShipStatus_OnDestroy_Postfix(ShipStatus __instance)
    {
        if (_started == __instance) { _started = null; _startedAt = -1f; }
        Held.Clear();
        _since = -1f;
    }

    // Sicherheitsnetz: nie dauerhaft ohne Tasks
    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    private static void HudManager_Update_Postfix()
    {
        if (Held.Count > 0 && _since >= 0f && ShipStatus.Instance != null && Time.realtimeSinceStartup - _since > MaxWait)
            Replay($"no map start after {MaxWait:F0} s");
        try { RepairTick(); }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} repair failed: {e.Message}"); _nextRepair = Time.realtimeSinceStartup + 10f; }
    }

    // ------------------------------------------------------------------ Wächter (User 30.10.: "als Backup")
    //
    // Die Host-Liste steht bei jedem Client in Data.Tasks (der Host synchronisiert sie). Fehlen davon lokal Tasks in myTasks,
    // werden sie genau wie in vanilla CoSetTasks nachgebaut (Prototyp aus ShipStatus.GetTaskById, Id/Owner, Initialize).
    // Nur in Atlas-Runden, nur der eigene Spieler, nie als Impostor (Fake-Tasks, der UC-Auditor raeumt seine absichtlich
    // lokal ab), fruehestens 3 s nach dem Bau, alle 2 s. Erledigte bleiben erledigt.

    private static float _nextRepair, _startedAt = -1f;
    private static int _repaired;

    private static void RepairTick()
    {
        float now = Time.realtimeSinceStartup;
        if (now < _nextRepair) return;
        _nextRepair = now + 2f;
        var ship = ShipStatus.Instance;
        if (ship == null || ship != _started || !AtlasMuseumBuilder.Active || Held.Count > 0) return;
        if (_startedAt < 0f || now - _startedAt < 3f) return;
        var lp = PlayerControl.LocalPlayer;
        var data = lp != null ? lp.Data : null;
        if (data == null || data.Tasks == null || lp.myTasks == null || data.Tasks.Count == 0) return;
        if (data.Role != null && data.Role.IsImpostor) return;
        if (AmongUsClient.Instance == null || AmongUsClient.Instance.IsGameOver) return;

        var have = new HashSet<uint>();
        foreach (var t in lp.myTasks)
            if (t != null && t.TryCast<NormalPlayerTask>() != null) have.Add(t.Id);
        if (have.Count >= data.Tasks.Count) return;

        int built = 0;
        foreach (var info in data.Tasks)
        {
            if (info == null || have.Contains(info.Id)) continue;
            var proto = ship.GetTaskById(info.TypeId);
            if (proto == null)
            {
                AtlasPlugin.Logger.LogWarning($"{LogPrefix} repair: task {info.Id} (type index {info.TypeId}) has no prototype on this map");
                continue;
            }
            var task = UnityEngine.Object.Instantiate(proto, lp.transform);
            task.Id = info.Id;
            task.Owner = lp;
            task.Initialize();
            if (info.Complete) task.taskStep = task.MaxStep;
            lp.myTasks.Add(task);
            built++;
        }
        if (built > 0)
        {
            _repaired += built;
            AtlasPlugin.Logger.LogWarning($"{LogPrefix} repair: {built} missing task(s) rebuilt from the host's list " +
                $"({have.Count + built} of {data.Tasks.Count} now, {_repaired} this round)");
        }
    }

    private static void Replay(string why)
    {
        if (Held.Count == 0) return;
        var list = Held.ToArray();
        Held.Clear();
        _since = -1f;
        _replaying = true;
        try
        {
            foreach (var (player, tasks) in list)
            {
                if (player == null) continue;
                try
                {
                    player.SetTasks(tasks);
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} {Name(player)}: {tasks.Count} task(s) set ({why})");
                }
                catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} {Name(player)}: replay failed: {e.Message}"); }
            }
        }
        finally { _replaying = false; }
    }

    private static string Name(PlayerControl p)
    {
        try { return p.Data?.PlayerName ?? $"#{p.PlayerId}"; } catch { return "?"; }
    }
}
