// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasEject - eigene Rauswurf-Szenen der Atlas-Karten.
//
// Die Szenen sind Daten (assets/eject_scenes.json aus tools/eject_scenes.py) und werden von der
// geteilten EjectEngine abgespielt - derselben Logik wie im Vorschau-Kino (tools/eject_theater).
// Pro Karte gibt es Rauswurf-Szenen und Skip-Szenen (niemand fliegt, Gleichstand).
//
// Einstieg ohne eigenen Detour: der Rauswurf wird im HudManager.Update-Takt erkannt (taucht
// ExileController.Instance neu auf, wird dessen Animate-Koroutine gestoppt und die Szene gestartet).
// Die Skeld-Runden in 0.3.0.4 kamen NICHT von einem Detour, sondern vom Phantom-GameStartManager,
// siehe AtlasSelection.LobbyScreenOrNull.
//
// Szenenwahl: der Host wuerfelt beim Meeting-Start je eine Rauswurf- und eine Skip-Szene (nie zweimal
// dieselbe hintereinander) und schickt beide ueber RPC 237 Op 7. Ohne Nachricht (Spaet-Beitritt)
// faellt jeder Client auf einen Seed aus PlayerId, Toten, Spiel-Id und Rauswurfzaehler zurueck.
//
// Void (Unknown's Collection): spielt UC seine eigene Void-Szene, setzt es den AppDomain-Eintrag
// "UnknownsCollection.VoidScene" - dann haelt sich Atlas bei diesem Rauswurf heraus.

using System;
using System.Collections.Generic;
using System.Linq;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasEject
{
    private const string LogPrefix = "[Atlas/Eject]";
    private const string VoidKey = "UnknownsCollection.VoidScene";
    /// <summary>Diagnose: Szene erzwingen (Index in der jeweiligen Liste), -1 = normal.</summary>
    internal static int ForceScene = -1;
    /// <summary>Vom Host fuer den naechsten Rauswurf gewaehlt (RPC 237 Op 7), -1 = keine Wahl.</summary>
    internal static int NextScene = -1, NextSkip = -1;
    private static int _lastScene = -1, _lastSkip = -1, _exiles;
    private static ExileController _seen;
    private static bool _meetingSeen;
    private static EjectEngine.Doc _doc;

    private static EjectEngine.Doc Doc
    {
        get
        {
            if (_doc != null) return _doc;
            EjectEngine.Log = m => AtlasPlugin.Logger.LogInfo($"{LogPrefix} {m}");
            EjectEngine.Warn = m => AtlasPlugin.Logger.LogWarning($"{LogPrefix} {m}");
            _doc = EjectEngine.LoadDoc("eject_scenes.json");
            if (_doc != null) AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_doc.Scenes.Count} scene(s) loaded");
            return _doc;
        }
    }

    private static List<EjectEngine.SceneDef> List(bool skip) =>
        Doc?.Scenes.Where(s => s.Map == AtlasMuseumBuilder.D.Key && s.Skip == skip).ToList() ?? new List<EjectEngine.SceneDef>();

    private static bool VoidClaimed()
    {
        try { return AppDomain.CurrentDomain.GetData(VoidKey) is bool b && b; } catch { return false; }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        if (!AtlasMuseumBuilder.Active) { _seen = null; _meetingSeen = false; return; }
        try
        {
            bool meeting = MeetingHud.Instance != null;
            if (meeting && !_meetingSeen && AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost) HostPick();
            _meetingSeen = meeting;

            var ec = ExileController.Instance;
            if (ec == null) { _seen = null; return; }
            if (_seen != null && ec == _seen) return;
            _seen = ec;
            if (ec.TryCast<SkeldExileController>() == null) return;
            if (VoidClaimed()) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} Void scene from Unknown's Collection - Atlas stays out"); return; }
            Start(ec);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} hook failed: {e}"); }
    }

    private static int PickIndex(int n, int last)
    {
        int pick = UnityEngine.Random.Range(0, n);
        if (n > 1 && pick == last) pick = (pick + UnityEngine.Random.Range(1, n)) % n;
        return pick;
    }

    private static void HostPick()
    {
        int n = List(false).Count, k = List(true).Count;
        if (n == 0) return;
        NextScene = PickIndex(n, _lastScene);
        NextSkip = k > 0 ? PickIndex(k, _lastSkip) : 0;
        AtlasWorld.SendEjectScene((byte)NextScene, (byte)NextSkip);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host picked {List(false)[NextScene].Id} / {(k > 0 ? List(true)[NextSkip].Id : "-")} for the next ejection");
    }

    private static EjectEngine.SceneDef Pick(ExileController ec)
    {
        bool skip = ec.initData == null || ec.initData.networkedPlayer == null;
        var list = List(skip);
        if (list.Count == 0) return null;
        int idx;
        int chosen = skip ? NextSkip : NextScene;
        if (ForceScene >= 0) idx = ForceScene % list.Count;
        else if (chosen >= 0) idx = chosen % list.Count;
        else
        {
            int pid = skip ? 255 : ec.initData.networkedPlayer.PlayerId;
            int dead = 0;
            foreach (var p in GameData.Instance.AllPlayers) if (p != null && p.IsDead) dead++;
            int game = AmongUsClient.Instance != null ? AmongUsClient.Instance.GameId : 0;
            idx = new System.Random(pid * 7919 + dead * 104729 + game + _exiles * 31).Next(list.Count);
        }
        if (skip) { _lastSkip = idx; NextSkip = -1; } else { _lastScene = idx; NextScene = -1; }
        _exiles++;
        return list[idx];
    }

    private static void Start(ExileController ec)
    {
        var def = Pick(ec);
        if (def == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} no scene for {AtlasMuseumBuilder.D.Key}"); return; }
        var run = new EjectEngine.Run(def, Doc);
        try { run.Setup(ec, null); }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"{LogPrefix} setup of {def.Id} failed, vanilla animation stays: {e}");
            run.Release();
            return;
        }
        ec.StopAllCoroutines();
        ec.StartCoroutine(EjectEngine.Play(run).WrapToIl2Cpp());
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} scene {def.Id} (player {(run.P != null ? "yes" : "none")})");
    }

    // ================================================================== Diagnose

    /// <summary>"voidscene" im TaskTest: Skip-Rauswurf, dann die Void-Szene von Unknown's Collection (Reflection).</summary>
    internal static void DiagVoid()
    {
        var ship = ShipStatus.Instance;
        var t = AccessTools.TypeByName("UnknownsCollection.VoidModifier");
        var m = t != null ? AccessTools.Method(t, "DiagScene") : null;
        if (ship == null || m == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: Unknown's Collection (VoidModifier.DiagScene) not found"); return; }
        var ec = Object.Instantiate(ship.ExileCutscenePrefab);
        ec.transform.SetParent(HudManager.Instance.transform, false);
        ec.transform.localPosition = new Vector3(0f, 0f, -60f);
        HudManager.Instance.SetHudActive(false);          // wie nach einem echten Meeting (WrapUp blendet sie wieder ein)
        ec.BeginForGameplay(null, false);
        m.Invoke(null, new object[] { ec, PlayerControl.LocalPlayer.Data });
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: void scene requested");
    }

    /// <summary>"eject:&lt;n&gt;" im TaskTest: Rauswurf eines Dummys mit Szene n; "ejectskip:&lt;n&gt;": Skip-Szene n.</summary>
    internal static void Diag(int scene, bool skip = false)
    {
        ForceScene = scene;
        var ship = ShipStatus.Instance;
        if (ship == null || ship.ExileCutscenePrefab == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: no exile prefab"); return; }
        NetworkedPlayerInfo victim = null;
        if (!skip)
            foreach (var p in GameData.Instance.AllPlayers)
                if (p != null && !p.IsDead && p.PlayerId != PlayerControl.LocalPlayer.PlayerId) { victim = p; break; }
        var ec = Object.Instantiate(ship.ExileCutscenePrefab);
        ec.transform.SetParent(HudManager.Instance.transform, false);
        ec.transform.localPosition = new Vector3(0f, 0f, -60f);
        HudManager.Instance.SetHudActive(false);          // wie nach einem echten Meeting (WrapUp blendet sie wieder ein)
        ec.BeginForGameplay(victim, false);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: eject {(victim != null ? victim.PlayerName : "nobody")}, scene index {scene}");
    }
}
