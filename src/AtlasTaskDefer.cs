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
//
// 06.11.: Das war nur ein Teil. Die eigentliche Ursache des Abbruchs war die Nummerierung: der Host zaehlt die Aufgaben in
// ShipStatus.Begin neu durch, die Gaeste nicht (siehe RenumberLikeHost unten). Seitdem zaehlt jeder Client nach dem Bau
// genauso, und der Abbruch an "NO_PROTOTYPE" kann nicht mehr entstehen.

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
        _lastCounts.Clear();
        _nextRequest = 0f;
        _repairFailed.Clear();
        RenumberLikeHost(__instance, "map built");
        Replay("map built");
    }

    // ------------------------------------------------------------------ Nummerierung wie beim Host (Ursache, 06.11.)
    //
    // User 06.11.: "Der Taskbar von letzter Woche ist wieder dabei", Gaeste mit 1 von 7 Tasks, Log: "1:NO_PROTOTYPE#3(missing)".
    // ShipStatus.Begin laeuft nur beim Host und ruft als Erstes AssignTaskIndexes: alle Aufgaben in der Reihenfolge Common,
    // Long, Short lueckenlos neu durchnummeriert (im GameAssembly nachgelesen, Werkzeuge in TOR Mod/docs/il2cpp-disasm). Gaeste
    // nummerieren nie neu, sie behalten die Nummern der Prefabs und die, die AtlasForeignTasks vergibt (groesster + 1). Solange
    // die Listen vanilla sind, stimmt beides; auf Atlas-Karten haengen die geliehenen Aufgaben aber am Ende IHRER Liste (Long
    // vor Short, also verschoben sich beim Host alle Short-Nummern), und Hollowmere entfernt Clear Asteroids und Align Engine
    // Output (Luecken an 2 und 3). Die Nummer des Hosts meinte beim Gast eine andere Aufgabe oder keine: CoSetTasks brach an
    // der ersten fehlenden ab (Common-Tasks da, der Rest fehlte; das war auch der Fehler vom 30.10.), der Waechter baute
    // andere Typen nach. Der Host baut die Karte in ShipStatus.Start, Begin kommt erst Frames spaeter (CoStartGameHost wartet
    // auf die Clients), also nummeriert er die fertigen Listen. Jeder Client tut nach dem Bau dasselbe, bevor zurueckgehaltene
    // Listen abgespielt werden; der Waechter prueft spaeter, ob ein Plugin die Listen danach noch geaendert hat.
    internal static void RenumberLikeHost(ShipStatus ship, string why)
    {
        if (ship == null || !AtlasMuseumBuilder.Active) return;
        var ac = AmongUsClient.Instance;
        // beim Host nummeriert Begin selbst; danach neu zu zaehlen wuerde seine schon verteilten Nummern verschieben
        if (ac != null && ac.AmHost && TasksHandedOut()) return;
        try
        {
            int n = 0, changed = 0;
            var before = new Dictionary<IntPtr, int>();
            foreach (var list in new[] { ship.CommonTasks, ship.LongTasks, ship.ShortTasks })
                if (list != null) foreach (var t in list) if (t != null) before[t.Pointer] = t.Index;
            ship.AssignTaskIndexes();
            foreach (var list in new[] { ship.CommonTasks, ship.LongTasks, ship.ShortTasks })
                if (list != null) foreach (var t in list)
                    if (t != null) { n++; if (before.TryGetValue(t.Pointer, out int old) && old != t.Index) changed++; }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} task indexes numbered like the host's ShipStatus.Begin ({why}): {n} task(s), {changed} changed");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} renumbering failed ({why}): {e}"); }
    }

    // Listen nach dem Bau noch geaendert (ein Karten-Plugin kuerzt erst im ersten Tick)? Dann nicht mehr lueckenlos.
    private static bool Sequential(ShipStatus ship)
    {
        int i = 0;
        foreach (var list in new[] { ship.CommonTasks, ship.LongTasks, ship.ShortTasks })
            if (list != null) foreach (var t in list) if (t != null && t.Index != i++) return false;
        return true;
    }

    private static bool TasksHandedOut()
    {
        foreach (var pc in PlayerControl.AllPlayerControls)
            if (pc != null && pc.Data != null && pc.Data.Tasks != null && pc.Data.Tasks.Count > 0) return true;
        return false;
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

    // ------------------------------------------------------------------ Waechter (User 30.10.: "als Backup")
    //
    // Die Host-Liste steht bei jedem Client in Data.Tasks. Fehlen davon Task-Objekte in myTasks, werden sie genau wie in vanilla
    // CoSetTasks nachgebaut (Prototyp aus ShipStatus.GetTaskById, Id/Owner, Initialize). Erledigte bleiben erledigt.
    // Gilt fuer ALLE Spieler (User-Screenshot 30.10.: DrSuspect sah bei sich 6/8, Mo 1/8): vermutlich ignoriert CompleteTask eine
    // Meldung, wenn das Objekt dieses Spielers auf dem Empfaenger fehlt. Bei fremden Spielern nur, wenn ihre Liste TEILWEISE
    // da ist (Muster eines Abbruchs); eine leere fremde Liste wird nur protokolliert. Nur Atlas-Runden, fruehestens 3 s nach dem
    // Bau, alle 2 s, nie fuer Impostor (Fake-Tasks, der UC-Auditor raeumt seine absichtlich lokal ab).

    private static float _nextRepair, _startedAt = -1f;
    private static int _repaired;
    private static readonly Dictionary<byte, (int Local, int Host)> _lastCounts = new();
    private static readonly HashSet<(byte Player, uint Id)> _repairFailed = new();

    private static void RepairTick()
    {
        float now = Time.realtimeSinceStartup;
        if (now < _nextRepair) return;
        _nextRepair = now + 2f;
        var ship = ShipStatus.Instance;
        if (ship == null || ship != _started || !AtlasMuseumBuilder.Active || Held.Count > 0) return;
        // Gast: hat ein Plugin die Listen nach dem Bau geaendert, wieder wie der Host zaehlen (der Host bleibt bei Begin)
        if (AmongUsClient.Instance != null && !AmongUsClient.Instance.AmHost && !Sequential(ship)) RenumberLikeHost(ship, "lists changed after the build");
        if (_startedAt < 0f || now - _startedAt < 3f) return;
        if (AmongUsClient.Instance == null || AmongUsClient.Instance.IsGameOver) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp != null && lp.Data != null && lp.Data.Role != null && !lp.Data.Role.IsImpostor) RequestHostList(now);
        foreach (var pc in PlayerControl.AllPlayerControls)
        {
            if (pc == null) continue;
            try { CheckPlayer(pc, ship, pc == lp, now); }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} check of {Name(pc)} failed: {e.Message}"); }
        }
    }

    private static void CheckPlayer(PlayerControl pc, ShipStatus ship, bool local, float now)
    {
        var data = pc.Data;
        if (data == null || data.Disconnected || data.Tasks == null || pc.myTasks == null || data.Tasks.Count == 0) return;
        if (data.Role != null && data.Role.IsImpostor) return;

        var have = new HashSet<uint>();
        foreach (var t in pc.myTasks)
            if (t != null && t.TryCast<NormalPlayerTask>() != null) have.Add(t.Id);

        // Diagnose: einmal je Runde der eigene Stand, danach jede Aenderung und jede Luecke; native Abbrueche stehen in keinem Log
        var counts = (Local: have.Count, Host: data.Tasks.Count);
        bool known = _lastCounts.TryGetValue(pc.PlayerId, out var last);
        if ((!known && (local || have.Count < data.Tasks.Count)) || (known && last != counts))
        {
            var list = new List<string>();
            foreach (var info in data.Tasks)
            {
                if (info == null) continue;
                string kind;
                try { var proto = ship.GetTaskById(info.TypeId); kind = proto != null ? proto.TaskType.ToString() : "NO_PROTOTYPE"; }
                catch (Exception e) { kind = "THROWS:" + e.GetType().Name; }
                list.Add($"{info.Id}:{kind}#{info.TypeId}{(info.Complete ? "(done)" : "")}{(have.Contains(info.Id) ? "" : "(missing)")}");
            }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} task check {Name(pc)}{(local ? " (me)" : "")}, {now - _startedAt:F0} s after the build: " +
                $"list {counts.Host}, objects {counts.Local}: {string.Join(", ", list)}");
        }
        _lastCounts[pc.PlayerId] = counts;
        if (have.Count >= data.Tasks.Count || (!local && have.Count == 0)) return;

        int built = 0;
        foreach (var info in data.Tasks)
        {
            if (info == null || have.Contains(info.Id) || _repairFailed.Contains((pc.PlayerId, info.Id))) continue;
            // je Task eigener Versuch: bricht einer ab, kommen die uebrigen trotzdem; einmal ins Log, nicht alle 2 s erneut
            NormalPlayerTask task = null;
            string kind = "?";
            try
            {
                var proto = ship.GetTaskById(info.TypeId);
                if (proto == null) throw new InvalidOperationException("no prototype on this map");
                kind = proto.TaskType.ToString();
                task = UnityEngine.Object.Instantiate(proto, pc.transform);
                task.Id = info.Id;
                task.Owner = pc;
                task.Initialize();
                if (info.Complete) task.taskStep = task.MaxStep;
                pc.myTasks.Add(task);
                built++;
            }
            catch (Exception e)
            {
                _repairFailed.Add((pc.PlayerId, info.Id));
                AtlasPlugin.Logger.LogError($"{LogPrefix} repair {Name(pc)}: task {info.Id} ({kind}, type index {info.TypeId}) failed: {e}");
                try { if (task != null) UnityEngine.Object.Destroy(task.gameObject); } catch { }
            }
        }
        if (built > 0)
        {
            _repaired += built;
            AtlasPlugin.Logger.LogWarning($"{LogPrefix} repair {Name(pc)}: {built} missing task object(s) rebuilt " +
                $"({have.Count + built} of {data.Tasks.Count} now, {_repaired} this round)");
        }
    }

    // ------------------------------------------------------------------ Abgleich mit dem Host (User 30.10.)
    //
    // Der Waechter oben vergleicht nur mit der EIGENEN Data.Tasks. Ist schon die zu kurz, sieht er nichts. Deshalb fragt ein
    // Gast 4 s nach dem Bau und danach alle 30 s den Host nach seiner Liste. Fehlende Eintraege kommen in Data.Tasks, die
    // Task-Objekte baut dann RepairTick. Abweichender Fortschritt wird nur protokolliert ("nicht geteilt"), nicht veraendert.
    // Nur eine Antwort vom Host zaehlt (Absender aus dem Transport). Ein Host ohne diese Version antwortet nicht: dann bleibt
    // alles, wie es ist.
    internal const byte OpTaskRequest = 22, OpTaskList = 23;
    private const int MaxListed = 64;
    private static float _nextRequest;

    private static void RequestHostList(float now)
    {
        var ac = AmongUsClient.Instance;
        if (ac.AmHost || now - _startedAt < 4f || now < _nextRequest) return;
        _nextRequest = now + 30f;
        AtlasWorld.Send(OpTaskRequest, null);
    }

    internal static void Receive(byte op, PlayerControl sender, Hazel.MessageReader reader)
    {
        var ac = AmongUsClient.Instance;
        if (ac == null || sender == null) return;
        if (op == OpTaskRequest)
        {
            if (!ac.AmHost || sender.Data?.Tasks == null) return;
            var tasks = sender.Data.Tasks;
            int n = Math.Min(tasks.Count, MaxListed);
            AtlasWorld.Send(OpTaskList, w =>
            {
                w.Write(sender.PlayerId);
                w.Write((byte)n);
                for (int i = 0; i < n; i++) { var t = tasks[i]; w.Write(t.Id); w.Write(t.TypeId); w.Write(t.Complete); }
            });
            return;
        }
        if (op != OpTaskList || sender.OwnerId != ac.HostId || ac.AmHost) return;
        byte target = reader.ReadByte();
        int count = reader.ReadByte();
        var lp = PlayerControl.LocalPlayer;
        bool mine = lp != null && lp.PlayerId == target && lp.Data?.Tasks != null && count <= MaxListed;
        int added = 0, doneHost = 0, doneLocal = 0;
        for (int i = 0; i < count; i++)
        {
            uint id = reader.ReadUInt32();
            byte type = reader.ReadByte();
            bool complete = reader.ReadBoolean();
            if (!mine) continue;
            if (complete) doneHost++;
            NetworkedPlayerInfo.TaskInfo own = null;
            foreach (var t in lp.Data.Tasks) if (t != null && t.Id == id) { own = t; break; }
            if (own == null)
            {
                lp.Data.Tasks.Add(new NetworkedPlayerInfo.TaskInfo(type, id) { Complete = complete });
                added++;
            }
            else if (own.Complete) doneLocal++;
        }
        if (!mine) return;
        if (added > 0)
        {
            AtlasPlugin.Logger.LogWarning($"{LogPrefix} host list has {count} task(s), {added} were missing in this client's list: added");
            _nextRepair = 0f;
            GameData.Instance?.RecomputeTaskCounts();
        }
        if (doneHost != doneLocal || added > 0)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} progress: host says {doneHost} of {count} done, this client {doneLocal}");
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
