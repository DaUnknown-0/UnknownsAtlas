// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasReachDiag - Selbsttest: ist jede Konsole von genug Seiten erreichbar? (User 24.10., Zugkarte: "manche Tasks
// sind nur aus bestimmten Winkeln machbar", Notfallknopf ohne Benutzen-Knopf.)
//
// Nur mit ATLAS_REACH_DIAG=1 im Freeplay einer Atlas-Karte: 3 s nach dem Kartenbau stellt der Test den eigenen
// Spieler um jede Konsole (Aufgaben, Notfallknopf, Kameras, Admin, Laptop) auf 16 Richtungen x 5 Abstaende, prueft,
// ob dort Platz fuer den Spieler ist (keine feste Kollision im Spielerkreis), und fragt CanUse der Konsole. Pro
// Konsole eine Logzeile "reach <key> at x,y: stand a/80, use b/80, dirs ...", dann "diag: all done" und Ende.

using System;
using System.Collections;
using System.Linq;
using System.Text;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using HarmonyLib;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasReachDiag
{
    private const string LogPrefix = "[Atlas/ReachDiag]";
    private static readonly bool On = Environment.GetEnvironmentVariable("ATLAS_REACH_DIAG") == "1";
    private static float _at = -1f;
    private static bool _done;

    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static class TickPatch
    {
        public static bool Prepare() => On;

        public static void Postfix(HudManager __instance)
        {
            if (_done || !AtlasMuseumBuilder.Active || PlayerControl.LocalPlayer == null) return;
            if (_at < 0f) { _at = Time.time + 3f; return; }
            if (Time.time < _at) return;
            _done = true;
            __instance.StartCoroutine(Run().WrapToIl2Cpp());
        }
    }

    private static IEnumerator Run()
    {
        var me = PlayerControl.LocalPlayer;
        var col = me.Collider;
        Vector2 off = col != null ? col.offset * (Vector2)me.transform.lossyScale : Vector2.zero;
        float rad = 0.2f;
        try { if (col is CircleCollider2D) rad = col.Cast<CircleCollider2D>().radius * me.transform.lossyScale.x; } catch { }
        Vector3 home = me.transform.position;
        int mask = Constants.ShipAndObjectsMask;
        float[] radii = { 0.3f, 0.45f, 0.6f, 0.8f, 1.0f };
        const int Dirs = 16;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} start: player radius {rad:F2}, map {AtlasMaps.ActiveKey}");

        var items = new System.Collections.Generic.List<(string Name, Vector2 Pos, Func<bool> Use, float Dist)>();
        foreach (var c in UnityEngine.Object.FindObjectsOfType<Console>())
        {
            if (c == null) continue;
            var cc = c;
            string name = c.name + "/" + c.ConsoleId;
            try { if (c.TaskTypes != null && c.TaskTypes.Length > 0) name += " " + string.Join("+", c.TaskTypes.Select(t => t.ToString())); } catch { }
            items.Add((name, (Vector2)c.transform.position, () => { cc.CanUse(me.Data, out bool can, out _); return can; }, c.UsableDistance));
        }
        foreach (var s in UnityEngine.Object.FindObjectsOfType<SystemConsole>())
        {
            if (s == null) continue;
            var ss = s;
            items.Add(("System:" + s.name, (Vector2)s.transform.position, () => { ss.CanUse(me.Data, out bool can, out _); return can; }, s.UsableDistance));
        }
        foreach (var m in UnityEngine.Object.FindObjectsOfType<MapConsole>())
        {
            if (m == null) continue;
            var mm = m;
            items.Add(("Map:" + m.name, (Vector2)m.transform.position, () => { mm.CanUse(me.Data, out bool can, out _); return can; }, m.UsableDistance));
        }
        foreach (var v in UnityEngine.Object.FindObjectsOfType<Vent>())
        {
            if (v == null) continue;
            items.Add(("Vent:" + v.Id, (Vector2)v.transform.position, null, v.UsableDistance));
        }

        foreach (var (name, pos, use, dist) in items)
        {
            if (pos.y < -100f) continue;                          // geparkt
            int stand = 0, ok = 0;
            var reach = new StringBuilder();
            var dirs = new StringBuilder();
            for (int d = 0; d < Dirs; d++)
            {
                float a = Mathf.PI * 2f * d / Dirs;
                var dir = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                bool any = false, inReach = false;
                foreach (float r in radii)
                {
                    var q = pos + dir * r;
                    bool free = true;
                    foreach (var h in Physics2D.OverlapCircleAll(q, rad * 0.95f, mask))
                    {
                        if (h == null || h.isTrigger || h == col) continue;
                        free = false; break;
                    }
                    if (!free) continue;
                    stand++;
                    if (r <= dist) inReach = true;
                    if (use == null) continue;
                    me.transform.position = new Vector3(q.x - off.x, q.y - off.y, home.z);
                    Physics2D.SyncTransforms();
                    bool can = false;
                    try { can = use(); } catch { }
                    if (can) { ok++; any = true; }
                }
                if (any) dirs.Append(d.ToString("X"));
                if (inReach) reach.Append(d.ToString("X"));
            }
            AtlasPlugin.Logger.LogInfo(FormattableString.Invariant(
                $"{LogPrefix} reach {name} at {pos.x:F2},{pos.y:F2}: range {dist:F2}, reachDirs {reach.Length}/16 [{reach}], stand {stand}/{Dirs * radii.Length}, use {(use == null ? "-" : ok.ToString())}, dirs {dirs}"));
            yield return null;
        }
        // Benutzen-Taste wie im Spiel: Spieler neben jede Systemkonsole stellen, ein paar Physik-Takte warten, Ziel lesen
        foreach (var s in UnityEngine.Object.FindObjectsOfType<SystemConsole>())
        {
            if (s == null || s.transform.position.y < -100f) continue;
            foreach (var d in new[] { new Vector2(0f, -0.6f), new Vector2(0.6f, 0f), new Vector2(0f, 0.6f), new Vector2(-0.6f, 0f) })
            {
                var q = (Vector2)s.transform.position + d;
                me.transform.position = new Vector3(q.x - off.x, q.y - off.y, home.z);
                Physics2D.SyncTransforms();
                for (int k = 0; k < 6; k++) yield return new WaitForFixedUpdate();
                string target = "none";
                try { var t = HudManager.Instance.UseButton.currentTarget; if (t != null) target = t.TryCast<MonoBehaviour>()?.name ?? "?"; } catch { }
                AtlasPlugin.Logger.LogInfo(FormattableString.Invariant($"{LogPrefix} hud {s.name} from {d.x:F1},{d.y:F1}: target {target}"));
            }
        }
        me.transform.position = home;
        Physics2D.SyncTransforms();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: all done ({items.Count} item(s))");
        yield return new WaitForSeconds(0.5f);
        Application.Quit();
    }
}
