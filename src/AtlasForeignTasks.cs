// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasForeignTasks - Aufgaben aus anderen Karten (AtlasMapDef.ForeignTasks), z. B. "Make Burger" aus Airship.
//
// Die Minispiele stecken im Paket ihrer Karte. Deshalb laedt der Kartenbau das Schiff der Quellkarte per
// Addressables (synchron, einmal je Runde) und haelt es, bis die Runde endet (ShipStatus.OnDestroy): solange
// zeigen die Minispiel-Prefabs auf gueltige Grafik. Kosten: Ladezeit beim Rundenstart und der Speicher der
// Quellkarte, beides nur in Runden auf einer Karte mit solchen Aufgaben.
//
// Je Aufgabe:
//   - Task: KOPIE des NormalPlayerTask-Prefabs der Quellkarte unter einem inaktiven Halter am ShipStatus (nie
//     das Prefab selbst aendern: das Asset gilt in der naechsten Airship-Runde weiter). StartAt = Raum der
//     Karte, Index = groesster vorhandener + 1, angehaengt an dieselbe Liste (Common/Short/Long) wie in der
//     Quellkarte. Verteilung, RpcSetTasks und GetTaskById laufen damit vanilla; alle Clients bauen dieselbe
//     Karte mit demselben Code und kommen auf denselben Index.
//   - Konsole: Kopie einer gewoehnlichen Skeld-Konsole der Karte (Kollider, Kontur-Material, Benutzbarkeit),
//     umgestellt auf die fremde Aufgabe, an die Lage aus Consoles[Key] gesetzt, Bild aus ConsoleSprites[Key].

using System;
using System.Collections.Generic;
using System.Linq;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasForeignTasks
{
    private const string LogPrefix = "[Atlas/ForeignTask]";
    private static readonly Dictionary<int, AsyncOperationHandle<GameObject>> Handles = new();
    private static GameObject _holder;

    internal static void Build(ShipStatus ship, Material outlineMat)
    {
        ReleaseCopies();            // die vorgeladenen Quellkarten bleiben (Preload), nur alte Kopien weg
        var defs = AtlasMuseumBuilder.D.ForeignTasks;
        if (defs == null || defs.Length == 0) return;
        var t0 = System.Diagnostics.Stopwatch.StartNew();

        // Vorlage fuer die Konsolen: eine schlichte Aufgaben-Konsole dieser Karte
        Console template = null;
        foreach (var c in ship.AllConsoles)
            if (c != null && c.GetIl2CppType().Name == "Console" && c.TaskTypes != null && c.TaskTypes.Length == 1) { template = c; break; }
        if (template == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} no console to copy, none added"); return; }

        _holder = new GameObject("AtlasForeignTasks");
        _holder.SetActive(false);
        _holder.transform.SetParent(ship.transform, false);

        int nextIndex = 0;
        foreach (var list in new[] { ship.CommonTasks, ship.ShortTasks, ship.LongTasks })
            if (list != null) foreach (var t in list) if (t != null) nextIndex = Math.Max(nextIndex, t.Index + 1);

        var consoles = ship.AllConsoles.ToList();
        int added = 0;
        foreach (var (type, shipId, key, room) in defs)
        {
            try
            {
                var source = SourceShip(shipId);
                if (source == null) continue;
                NormalPlayerTask found = null;
                int kind = -1;
                var lists = new[] { source.CommonTasks, source.ShortTasks, source.LongTasks };
                for (int k = 0; k < 3 && found == null; k++)
                    if (lists[k] != null) foreach (var t in lists[k]) if (t != null && t.TaskType == type) { found = t; kind = k; break; }
                if (found == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} {type}: not in map {shipId}"); continue; }
                if (!AtlasMuseumBuilder.D.Consoles.TryGetValue(key, out var pos)) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} {type}: no slot {key}"); continue; }

                var task = Object.Instantiate(found.gameObject, _holder.transform).GetComponent<NormalPlayerTask>();
                task.name = $"Atlas_{type}";
                task.StartAt = room;
                task.Index = nextIndex++;
                switch (kind)
                {
                    case 0: ship.CommonTasks = Append(ship.CommonTasks, task); break;
                    case 1: ship.ShortTasks = Append(ship.ShortTasks, task); break;
                    default: ship.LongTasks = Append(ship.LongTasks, task); break;
                }

                var go = Object.Instantiate(template.gameObject, template.transform.parent);
                go.name = $"Atlas_{type}Console";
                // Bild und Grundflaeche der Vorlage gehoeren nicht zur neuen Konsole
                for (int i = go.transform.childCount - 1; i >= 0; i--)
                {
                    var ch = go.transform.GetChild(i);
                    if (ch.name == "Atlas_Block" || ch.name == "Atlas_ConsoleMarker") Object.DestroyImmediate(ch.gameObject);
                }
                var con = go.GetComponent<Console>();
                con.TaskTypes = new Il2CppStructArray<TaskTypes>(new[] { type });
                con.ValidTasks = new Il2CppReferenceArray<TaskSet>(0);
                con.ConsoleId = 0;
                con.Room = room;
                con.checkWalls = false;
                con.onlySameRoom = false;
                con.onlyFromBelow = false;
                AtlasMuseumBuilder.MoveTo(go.transform, pos);
                AtlasMuseumBuilder.SortLikePlayer(go.transform);
                con.Image = AtlasMuseumBuilder.ApplyBlock(go, key, con.Image, outlineMat);
                consoles.Add(con);
                added++;
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} {type} from map {shipId} ({(kind == 0 ? "common" : kind == 1 ? "short" : "long")}, index {task.Index}) at {key} ({pos.x:F1},{pos.y:F1})");
            }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} {type}: {e}"); }
        }
        ship.AllConsoles = new Il2CppReferenceArray<Console>(consoles.ToArray());
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {added} of {defs.Length} added in {t0.ElapsedMilliseconds} ms");
    }

    private static ShipStatus SourceShip(int shipId)
    {
        var t0 = System.Diagnostics.Stopwatch.StartNew();
        bool preloaded = Handles.TryGetValue(shipId, out var h);
        if (!preloaded)
        {
            if (!StartLoad(shipId, out h)) return null;
        }
        // Rundenstart vor dem Ende des Vorladens (oder ohne Lobby, Freeplay): den Rest abwarten
        if (!h.IsDone) h.WaitForCompletion();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} map {shipId} {(preloaded ? "from the lobby preload" : "loaded")}, waited {t0.ElapsedMilliseconds} ms ({h.Status})");
        if (h.Status != AsyncOperationStatus.Succeeded || h.Result == null) return null;
        return h.Result.GetComponent<ShipStatus>();
    }

    private static bool StartLoad(int shipId, out AsyncOperationHandle<GameObject> h)
    {
        h = default;
        var prefabs = AmongUsClient.Instance?.ShipPrefabs;
        if (prefabs == null || shipId < 0 || shipId >= prefabs.Count || prefabs[shipId] == null) return false;
        h = Addressables.LoadAssetAsync<GameObject>(prefabs[shipId].RuntimeKey);
        Handles[shipId] = h;
        return true;
    }

    // ------------------------------------------------------------------ Vorladen in der Lobby
    //
    // 17.10.: Eine Plugin-Karte borgt sich eine Aufgabe der Airship. Deren Prefab wurde beim Rundenstart synchron geladen
    // (WaitForCompletion): 804 ms Stillstand im Hauptthread, der groesste Rest des Erstlade-Freezes nach den
    // vorkomprimierten Texturen. Jetzt laedt der Lobby-Takt (AtlasPreload) die Quellkarten asynchron vor;
    // ShipStatus.OnDestroy gibt sie nach der Runde frei, die Lobby laedt sie dann erneut.

    private static readonly HashSet<int> _loggedReady = new();
    private static readonly Dictionary<int, float> _preloadStart = new();

    /// <summary>Aus dem Lobby-Takt: Quellkarten der gewaehlten Karte asynchron laden, andere freigeben.</summary>
    internal static void Preload(AtlasMapDef def)
    {
        var need = new HashSet<int>();
        if (def?.ForeignTasks != null) foreach (var d in def.ForeignTasks) need.Add(d.ShipId);
        foreach (var id in new List<int>(Handles.Keys))
        {
            if (need.Contains(id) || _holder != null) continue;             // waehrend einer Runde nichts freigeben
            try { Addressables.Release(Handles[id]); } catch { }
            Handles.Remove(id);
            _loggedReady.Remove(id);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} map {id} released (not needed by {def?.Key ?? "the vanilla map"})");
        }
        foreach (int id in need)
        {
            if (!Handles.ContainsKey(id))
            {
                if (StartLoad(id, out _)) { _preloadStart[id] = Time.time; _loggedReady.Remove(id); }
                continue;
            }
            var h = Handles[id];
            if (h.IsDone && _loggedReady.Add(id))
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} map {id} preloaded in the lobby after {Time.time - (_preloadStart.TryGetValue(id, out var s) ? s : Time.time):F1} s ({h.Status})");
        }
    }

    private static void ReleaseCopies()
    {
        try { if (_holder != null) Object.Destroy(_holder); } catch { }
        _holder = null;
    }

    private static Il2CppReferenceArray<NormalPlayerTask> Append(Il2CppReferenceArray<NormalPlayerTask> list, NormalPlayerTask t)
    {
        var l = list != null ? list.ToList() : new List<NormalPlayerTask>();
        l.Add(t);
        return new Il2CppReferenceArray<NormalPlayerTask>(l.ToArray());
    }

    /// <summary>Runde vorbei (oder neuer Bau): Kopien weg, Quellkarten freigeben.</summary>
    internal static void Release()
    {
        try { if (_holder != null) Object.Destroy(_holder); } catch { }
        _holder = null;
        foreach (var h in Handles.Values) try { Addressables.Release(h); } catch { }
        Handles.Clear();
        _loggedReady.Clear();
    }
}
