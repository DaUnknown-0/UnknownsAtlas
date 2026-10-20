// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasPreload - laedt das Kartenpaket der gewaehlten Karte schon in der Lobby.
//
// Befund 09.10.: die erste Runde je Karte stand rund 12 s zwischen "Received game start" und der
// Taskvergabe, weil Boden, Objekt- und Konsolenatlanten (17-22 Texturen, je ~0,5 s Dekodieren und
// Komprimieren) erst im ShipStatus.Start-Postfix geladen wurden. Zwei Spieler fielen dabei aus der Runde.
// Jetzt laedt jeder Client die Texturen, sobald die Wahl des Hosts (RPC 236) feststeht. Karten mit
// vorkomprimierten Paketen (.atx, AtlasTexturePack) entpacken bis zu zwei Texturen voraus im Hintergrund-Thread
// und laden je Frame eine hoch (wenige ms); Karten ohne Paket laden wie frueher eine Textur je Schritt mit
// Pause dazwischen. Der Bau findet sie danach im Cache von AtlasAssets. Ein Rundenstart mitten im Vorladen
// ist harmlos, der Bau laedt den Rest wie bisher.

using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasPreload
{
    private const string LogPrefix = "[Atlas/Preload]";
    /// <summary>Wartezeit nach einer Kartenwahl: der Host klickt sich oft erst durch die Karten.</summary>
    private const float SettleSeconds = 2f;
    /// <summary>Pause zwischen zwei Texturen ohne Paket (die dekodieren und komprimieren im Hauptthread).</summary>
    private const float StepSeconds = 0.25f;
    /// <summary>So viele Texturen werden vorab im Hintergrund entpackt (32-Bit-Prozess: nicht alle auf einmal).</summary>
    private const int Lookahead = 2;

    private struct Item
    {
        public string Res;
        public Assembly Asm;
        public Action Finish;
        public bool Started, Packed;
    }

    private static string _key;                 // Karte, deren Warteschlange laeuft oder fertig ist
    private static bool _queued;
    private static float _changedAt, _next, _startedAt, _foreignAt;
    private static int _total;
    private static double _mainMs;
    private static readonly List<Item> Work = new();

    /// <summary>Aus dem Lobby-Takt (AtlasSelection, HudManager.Update bei vorhandener LobbyBehaviour).</summary>
    internal static void Tick()
    {
        string key = AtlasSelection.CurrentKey;
        if (key != _key)
        {
            _key = key;
            _changedAt = Time.time;
            _queued = false;
            Work.Clear();
        }
        // Quellkarten fremder Aufgaben (AtlasForeignTasks), auch nach jeder Runde erneut; zweimal je Sekunde reicht
        if (Time.time >= _foreignAt && Time.time - _changedAt >= SettleSeconds)
        {
            _foreignAt = Time.time + 0.5f;
            try { AtlasForeignTasks.Preload(key != null ? AtlasSelection.Selected() : null); }
            catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} foreign maps: {e.Message}"); }
        }
        if (key == null) return;
        if (!_queued)
        {
            if (Time.time - _changedAt < SettleSeconds) return;
            _queued = true;
            Enqueue();
            _next = Time.time;
        }
        if (Work.Count == 0) return;

        for (int i = 0; i < Math.Min(Lookahead, Work.Count); i++)
        {
            if (Work[i].Started) continue;
            var it = Work[i];
            it.Started = true;
            it.Packed = AtlasAssets.BeginPrepare(it.Res, it.Asm);
            Work[i] = it;
        }
        var head = Work[0];
        if (!AtlasAssets.IsReady(head.Res)) return;              // Hintergrund entpackt noch
        if (!head.Packed && Time.time < _next) return;
        Work.RemoveAt(0);

        var sw = System.Diagnostics.Stopwatch.StartNew();
        try { head.Finish(); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} step failed: {e.Message}"); }
        _mainMs += sw.Elapsed.TotalMilliseconds;
        _next = Time.time + (head.Packed ? 0f : StepSeconds);
        if (Work.Count == 0)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_key}: {_total} texture(s) ready after {Time.time - _startedAt:F1} s, " +
                                       $"main thread {_mainMs:F0} ms");
    }

    private static void Enqueue()
    {
        var def = AtlasSelection.Selected();
        if (def == null) return;
        // Pakete anderer Karten zuerst freigeben: sonst lagen beim Durchklicken alle Karten zugleich im
        // 32-Bit-Prozess. Der Bau ruft dasselbe mit derselben Karte noch einmal auf (dann ohne Wirkung).
        AtlasAssets.ReleaseOtherMaps(def);

        var floor = new HashSet<int>();
        foreach (var t in def.FloorTiles ?? Array.Empty<(int, float, float, int, int)>()) floor.Add(t.Index);
        var props = new HashSet<int>();
        foreach (var p in def.Props ?? Array.Empty<(string, int, int, int, int, int, float, float, float, float, float)>()) props.Add(p.Atlas);
        var consoles = new HashSet<int>();
        foreach (var c in def.ConsoleSprites ?? Array.Empty<(string, int, int, int, int, int, float, float)>()) consoles.Add(c.Atlas);

        var asm = def.ResourceAssembly;
        foreach (int i in floor) Work.Add(new Item { Res = AtlasAssets.FloorRes(def, i), Asm = asm, Finish = () => AtlasAssets.MapFloorTile(def, i) });
        foreach (int k in props) Work.Add(new Item { Res = AtlasAssets.PropsRes(def, k), Asm = asm, Finish = () => AtlasAssets.MapPropsTexture(def, k) });
        foreach (int k in consoles) Work.Add(new Item { Res = AtlasAssets.ConsolesRes(def, k), Asm = asm, Finish = () => AtlasAssets.MapConsolesTexture(def, k) });
        _total = Work.Count;
        _mainMs = 0;
        _startedAt = Time.time;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {def.Key}: preloading {_total} texture(s) in the lobby");
    }
}
