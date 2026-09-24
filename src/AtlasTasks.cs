// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasTasks - tauscht die Minispiele der eigenen Karten-Tasks (docs/TASK_KONZEPT.md).
//
// Nie an den Prefabs in ShipStatus.CommonTasks/ShortTasks/LongTasks: das sind Assets, eine
// Aenderung dort sickert in die naechste Vanilla-Skeld-Runde. Getauscht wird nur
// PlayerTask.MinigamePrefab an den Task-INSTANZEN des lokalen Spielers, jede Runde neu, zweimal
// pro Sekunde abgeglichen (andere Mods ersetzen Tasks nachtraeglich: UC Auditor, Role Control).
// Die Prefabs haengen unter einem inaktiven Halter am ShipStatus und sterben mit der Runde.
// Verteilung, RpcSetTasks, RpcCompleteTask und der server-autoritative Taskwin bleiben vanilla.

using System;
using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasTasks
{
    private const string LogPrefix = "[Atlas/Task]";
    private static GameObject _holder;
    private static readonly Dictionary<TaskTypes, Minigame> Prefabs = new();
    private static float _nextSwap;

    private static bool EnsurePrefabs()
    {
        if (_holder != null) return true;
        var ship = ShipStatus.Instance;
        if (ship == null) return false;
        Prefabs.Clear();
        _holder = new GameObject("AtlasTaskPrefabs");
        _holder.SetActive(false);
        _holder.transform.SetParent(ship.transform, false);
        foreach (var kv in AtlasMuseumBuilder.D.CustomTasks)
        {
            var go = new GameObject($"AtlasTask_{kv.Value}") { layer = 5 };
            go.transform.SetParent(_holder.transform, false);
            var mg = go.AddComponent<AtlasMinigame>();
            mg.TransType = TransitionType.SlideBottom;
            Prefabs[kv.Key] = mg;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {Prefabs.Count} custom minigame prefab(s) for {AtlasMuseumBuilder.D.Key}");
        return true;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        if (!AtlasMuseumBuilder.Active) { _holder = null; return; }
        try
        {
            if (Time.time >= _nextSwap)
            {
                _nextSwap = Time.time + 0.25f;                     // Sabotage-Tasks erscheinen mitten in der Runde
                if (EnsurePrefabs()) Swap();
            }
            DiagTick();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} update failed: {e.Message}"); _nextSwap = Time.time + 5f; }
    }

    private static void Swap()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.myTasks == null || Prefabs.Count == 0) return;
        foreach (var t in lp.myTasks)
        {
            if (t == null || !Prefabs.TryGetValue(t.TaskType, out var mg)) continue;
            if (t.MinigamePrefab == mg) continue;
            t.MinigamePrefab = mg;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {t.TaskType} -> {mg.name}");
        }
    }

    // ------------------------------------------------------------ Autotest (Diagnostics.TaskTest)

    private static float _diagAt = -1f, _shotAt, _sabAt = -1f;
    private static int _ejectShots;
    private static int _diagPhase;
    private static AtlasMinigame _diagGame;

    private static int _diagIndex;

    private static void DiagTick()
    {
        var all = AtlasPlugin.CfgTaskTest?.Value;
        if (string.IsNullOrEmpty(all)) return;
        // mehrere Minispiele nacheinander in derselben Runde: "tomb,projector,steam@1"
        var list = all.Split(',');
        if (_diagPhase == 4 || _diagPhase == 5)
        {
            if (_diagPhase == 4 && _diagIndex + 1 < list.Length) { _diagIndex++; _diagPhase = 0; _diagAt = Time.time + 1.5f; }
            else if (_diagPhase == 4) { _diagPhase = 5; AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: all done"); }
            return;
        }
        var kind = list[Math.Min(_diagIndex, list.Length - 1)].Trim();
        int at = kind.IndexOf('@');
        AtlasMinigame.DiagStep = at > 0 && int.TryParse(kind.Substring(at + 1), out var st) ? st : -1;
        if (at > 0) kind = kind.Substring(0, at);
        if (_diagAt < 0f) { _diagAt = Time.time + 22f; return; }       // nach den Ansichtsfotos
        if (Time.time < _diagAt) return;
        switch (_diagPhase)
        {
            case 0:
                // die letzte Ansichts-Station oeffnet die Kameras und laesst sie offen: selbst schliessen
                if (Minigame.Instance != null)
                {
                    try { Minigame.Instance.ForceClose(); } catch { }
                    _diagAt = Time.time + 1.5f;
                    return;
                }
                // "world:storm" usw.: Welt-System ausloesen, nach 6 s Bildschirmfoto
                // "eject:2": Rauswurf-Szene Nr. 2 der Karte, drei Fotos im Verlauf
                // "step:EmptyGarbage": alle Tasks zuweisen, den Task wie AtlasMinigame.CompleteStep
                // einen Schritt weiterschalten und 20 s ueberleben (Absturz 24.09. nach "step 0 -> 1
                // of 2" bei EmptyGarbage und AlignEngineOutput)
                if (kind.StartsWith("step:", StringComparison.Ordinal) || kind.StartsWith("stepmg:", StringComparison.Ordinal)
                    || kind.StartsWith("stepmgnopin:", StringComparison.Ordinal))
                {
                    // stepmgnopin: Kontrolllauf ohne den Logger-Pin von AtlasMinigame
                    AtlasMinigame.DiagNoPin = kind.StartsWith("stepmgnopin:", StringComparison.Ordinal);
                    bool viaMg = !kind.StartsWith("step:", StringComparison.Ordinal);
                    StepRepro.Begin(kind.Substring(kind.IndexOf(':') + 1), viaMg);
                    _diagPhase = 11;
                    return;
                }
                if (kind == "extraroom")
                {
                    AtlasRoomDiag.Begin();
                    _diagPhase = 10;
                    return;
                }
                if (kind == "voidscene")
                {
                    AtlasEject.DiagVoid();
                    _ejectShots = 3; _shotAt = Time.time + 2.2f; _diagPhase = 7;
                    return;
                }
                if (kind.StartsWith("eject:", StringComparison.Ordinal) || kind.StartsWith("ejectskip:", StringComparison.Ordinal))
                {
                    bool sk = kind.StartsWith("ejectskip:", StringComparison.Ordinal);
                    AtlasEject.Diag(int.TryParse(kind.Substring(sk ? 10 : 6), out var ei) ? ei : 0, sk);
                    _ejectShots = 3; _shotAt = Time.time + 2.0f; _diagPhase = 7;
                    return;
                }
                if (kind.StartsWith("world:", StringComparison.Ordinal))
                {
                    AtlasWorld.Diag(kind.Substring(6));
                    _shotAt = Time.time + 6f; _diagPhase = 6;
                    return;
                }
                TaskTypes? type = null;
                // "sab:lights" usw.: echte Sabotage ausloesen, dann deren (getauschtes) Minispiel oeffnen
                if (kind.StartsWith("sab:", StringComparison.Ordinal))
                {
                    if (_sabAt < 0f)
                    {
                        var sys = kind switch { "sab:lights" => SystemTypes.Electrical, "sab:comms" => SystemTypes.Comms,
                                                "sab:reactor" => SystemTypes.Reactor, _ => SystemTypes.LifeSupp };
                        ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)sys);
                        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: sabotage {sys} started");
                        _sabAt = Time.time + 2.5f;
                        return;
                    }
                    if (Time.time < _sabAt) return;
                    _sabAt = -1f;
                    Shot(kind.Replace(':', '_'), "tasklist");
                    type = kind switch { "sab:lights" => TaskTypes.FixLights, "sab:comms" => TaskTypes.FixComms,
                                         "sab:reactor" => TaskTypes.ResetReactor, _ => TaskTypes.RestoreOxy };
                    Swap();
                }
                else
                    foreach (var kv in AtlasMuseumBuilder.D.CustomTasks) if (kv.Value == kind) type = kv.Key;
                if (type == null || !Prefabs.TryGetValue(type.Value, out var prefab)) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: no prefab for {kind}"); _diagPhase = 4; return; }
                PlayerTask task = null;
                foreach (var t in PlayerControl.LocalPlayer.myTasks) { if (t != null && t.TaskType == type.Value) task = t; }
                // Kein passender Task: nur als Traeger fuer Begin, abgehakt wird dann NICHTS
                AtlasMinigame.DiagNoComplete = task == null;
                if (task == null) foreach (var t in PlayerControl.LocalPlayer.myTasks) { if (t != null && t.TryCast<NormalPlayerTask>() != null) { task = t; break; } }
                var cam = Camera.main;
                var go = Object.Instantiate(prefab.gameObject, cam.transform);
                go.transform.localPosition = new Vector3(0f, 0f, -50f);
                _diagGame = go.GetComponent<AtlasMinigame>();
                _diagGame.Begin(task);
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: opened {kind} on task {(task != null ? task.TaskType.ToString() : "none")}");
                _diagPhase = 1; _shotAt = Time.time + 1.5f;
                break;
            case 1:
                if (Time.time < _shotAt) return;
                Shot(kind, "start");
                AtlasMinigame.DiagAuto = true;
                _diagPhase = 2;
                break;
            case 7:
                if (Time.time < _shotAt) return;
                Shot(kind, $"t{4 - _ejectShots}");
                _ejectShots--;
                _shotAt = Time.time + 1.6f;
                if (_ejectShots <= 0) { _shotAt = Time.time + 6f; _diagPhase = 8; }
                break;
            case 8:
                // warten, bis WrapUp gelaufen ist (Controller weg), dann weiter
                if (ExileController.Instance != null && Time.time < _shotAt) return;
                AtlasEject.ForceScene = -1;
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: {kind} finished");
                _diagPhase = 4;
                break;
            case 10:
                if (AtlasRoomDiag.Tick()) _diagPhase = 4;
                break;
            case 11:
                if (StepRepro.Tick()) _diagPhase = 4;
                break;
            case 6:
                if (Time.time < _shotAt) return;
                Shot(kind, "view");
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: {kind} -> {AtlasWorld.DiagState()}");
                AtlasMinigame.DiagAuto = false; _diagPhase = 4;
                break;
            case 2:
                if (AtlasMinigame.DiagProgress >= 0.5f || _diagGame == null || _diagGame.amClosing != Minigame.CloseState.None)
                { Shot(kind, "half"); _diagPhase = 3; _shotAt = Time.time + 60f; }
                break;
            case 3:
                if (_diagGame == null || _diagGame.amClosing != Minigame.CloseState.None)
                {
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: {kind} finished and closing");
                    AtlasMinigame.DiagAuto = false; _diagPhase = 4;
                }
                else if (Time.time > _shotAt) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: {kind} did not finish in 60 s"); Shot(kind, "stuck"); _diagPhase = 4; }
                break;
        }
    }

    internal static void Shot(string kind, string tag)
    {
        string dir = System.IO.Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
        System.IO.Directory.CreateDirectory(dir);
        string file = System.IO.Path.Combine(dir, $"task_{kind.Replace(':', '_')}_{tag}_{DateTime.Now:HHmmss}.png");
        ScreenCapture.CaptureScreenshot(file);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag shot -> {file}");
    }
}

/// <summary>Autotest "step:TaskType": einen mehrstufigen Task einen Schritt weiterschalten und
/// beobachten (Absturzsuche 24.09.).</summary>
internal static class StepRepro
{
    private static TaskTypes _type;
    private static float _t0, _next;
    private static int _phase;
    private static bool _viaMinigame;
    private static NormalPlayerTask _task;
    private static bool _gcDone;

    internal static void Begin(string typeName, bool viaMinigame = false)
    {
        _phase = 0;
        _viaMinigame = viaMinigame;
        _gcDone = false;
        if (!Enum.TryParse(typeName, out _type)) { AtlasPlugin.Logger.LogError($"[Atlas/Step] unknown task type {typeName}"); _phase = 9; return; }
        try
        {
            var ship = ShipStatus.Instance;
            var ids = new List<byte>();
            foreach (var arr in new[] { ship.CommonTasks, ship.LongTasks, ship.ShortTasks })
                if (arr != null) foreach (var t in arr) if (t != null) ids.Add((byte)t.Index);
            PlayerControl.LocalPlayer.Data.RpcSetTasks(new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<byte>(ids.ToArray()));
            AtlasPlugin.Logger.LogInfo($"[Atlas/Step] assigned {ids.Count} task(s), target {_type}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Step] assign failed: {e}"); _phase = 9; return; }
        _t0 = Time.time + 2f; _phase = 1;
    }

    // wie das Spiel selbst: die Konsole, deren FindTask genau diesen Task liefert
    private static Console ConsoleFor(NormalPlayerTask task)
    {
        foreach (var c in Object.FindObjectsOfType<Console>())
        {
            if (c == null) continue;
            PlayerTask t = null;
            try { t = c.FindTask(PlayerControl.LocalPlayer); } catch { }
            if (t != null && t.Pointer == task.Pointer) return c;
        }
        return null;
    }

    internal static bool Tick()
    {
        if (_phase == 9) return true;
        if (Time.time < _t0) return false;
        try
        {
            switch (_phase)
            {
                case 1:
                    NormalPlayerTask task = null;
                    foreach (var t in PlayerControl.LocalPlayer.myTasks)
                    {
                        var n = t != null ? t.TryCast<NormalPlayerTask>() : null;
                        if (n != null && n.TaskType == _type) { task = n; break; }
                    }
                    if (task == null) { AtlasPlugin.Logger.LogError($"[Atlas/Step] no {_type} task"); return true; }
                    if (_viaMinigame)
                    {
                        // wie ein Spieler: zur Konsole, Console.Use, das Minispiel spielt sich selbst
                        var con = ConsoleFor(task);
                        if (con == null) { AtlasPlugin.Logger.LogError($"[Atlas/Step] no console for {_type}"); return true; }
                        PlayerControl.LocalPlayer.NetTransform.RpcSnapTo((Vector2)con.transform.position + new Vector2(0f, -0.45f));
                        _task = task; _t0 = Time.time + 1f; _phase = 3;
                        AtlasPlugin.Logger.LogInfo($"[Atlas/Step] walking to {con.name}");
                        return false;
                    }
                    int before = task.taskStep;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] {_type}: NextStep from {before} of {task.MaxStep}, showStep {task.ShowTaskStep}");
                    task.NextStep();
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] {_type}: now {task.taskStep} of {task.MaxStep}, complete {task.IsComplete}, room {task.StartAt}");
                    _next = Time.time + 1f; _t0 = Time.time; _phase = 2;
                    return false;
                case 3:
                {
                    var con = ConsoleFor(_task);
                    float d = con.CanUse(PlayerControl.LocalPlayer.Data, out bool can, out bool could);
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] {con.name}: CanUse {can}, could {could}, dist {d:F2}");
                    AtlasMinigame.DiagAuto = true;
                    con.Use();
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] minigame {(Minigame.Instance != null ? Minigame.Instance.name : "none")}");
                    _t0 = Time.time + 0.5f; _phase = 4;
                    return false;
                }
                case 4:
                    // Hypothese 24.09.: der Logger des Minispiels (Minigame.logger, +0x40) wird vom
                    // il2cpp-GC eingesammelt, solange das Minispiel offen ist. Einmal waehrend des
                    // Spiels hart aufraeumen lassen; stuerzt Close danach reproduzierbar ab, stimmt sie.
                    if (!_gcDone && Minigame.Instance != null && Time.time > _t0 + 1.5f)
                    {
                        _gcDone = true;
                        Il2CppSystem.GC.Collect();
                        System.GC.Collect();
                        Il2CppSystem.GC.Collect();
                        AtlasPlugin.Logger.LogInfo("[Atlas/Step] forced il2cpp + managed GC while the minigame is open");
                    }
                    // warten, bis das Minispiel den Schritt gemacht und sich geschlossen hat
                    if (Minigame.Instance != null && Time.time < _t0 + 60f) return false;
                    AtlasMinigame.DiagAuto = false;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] {_type}: minigame closed, now {_task.taskStep} of {_task.MaxStep}, room {_task.StartAt}");
                    _next = Time.time + 1f; _t0 = Time.time; _phase = 2;
                    return false;
                case 2:
                    if (Time.time < _next) return false;
                    float el = Time.time - _t0;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Step] alive {el:F0}s");
                    if (el >= 3f && el < 4f) { HudManager.Instance.ToggleMapVisible(new MapOptions { Mode = MapOptions.Modes.Normal }); AtlasPlugin.Logger.LogInfo("[Atlas/Step] map opened"); }
                    if (el >= 7f && el < 8f && MapBehaviour.Instance != null && MapBehaviour.Instance.IsOpen) { MapBehaviour.Instance.Close(); AtlasPlugin.Logger.LogInfo("[Atlas/Step] map closed"); }
                    _next = Time.time + 1f;
                    if (el >= 20f) { AtlasPlugin.Logger.LogInfo($"[Atlas/Step] {_type}: survived 20 s"); return true; }
                    return false;
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Step] failed: {e}"); return true; }
        return true;
    }
}
