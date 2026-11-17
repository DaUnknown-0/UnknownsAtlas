// Allocation profile: wraps every Harmony patch method of the mods (and Atlas' tick runner) and
// charges il2cpp heap growth (gc used size before/after) to it. Coarse (Boehm counts whole blocks),
// but over a round the large allocators stand out.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using HarmonyLib;

namespace DuoTest;

internal static class DuoProf
{
    [DllImport("GameAssembly", CallingConvention = CallingConvention.Cdecl)] static extern long il2cpp_gc_get_used_size();
    [DllImport("GameAssembly", CallingConvention = CallingConvention.Cdecl)] static extern long il2cpp_gc_get_heap_size();
    static readonly Dictionary<string, long> grow = new();
    static readonly Dictionary<string, (long bytes, long calls, double ms)> acc = new();
    static readonly string[] Mods = { "UnknownsAtlas", "TheOtherRoles", "UsefulTORStuff", "UnknownsCollection", "Reactor", "TOR-Bypass", "ForceImpostorMod" };
    static Harmony h;
    static readonly Dictionary<MethodBase, string> names = new();
    internal static bool Installed;

    internal static void Install()
    {
        if (Installed) return;
        Installed = true;
        h = new Harmony("test.duotest.prof");
        var pre = new HarmonyMethod(typeof(DuoProf).GetMethod(nameof(Pre), BindingFlags.Static | BindingFlags.NonPublic)) { priority = Priority.First };
        var post = new HarmonyMethod(typeof(DuoProf).GetMethod(nameof(Post), BindingFlags.Static | BindingFlags.NonPublic)) { priority = Priority.Last };
        var targets = new HashSet<MethodBase>();
        foreach (var orig in Harmony.GetAllPatchedMethods().ToList())
        {
            var info = Harmony.GetPatchInfo(orig);
            if (info == null) continue;
            foreach (var p in info.Prefixes.Concat(info.Postfixes).Concat(info.Finalizers))
            {
                var m = p.PatchMethod;
                if (m == null || m.DeclaringType == null || m.IsGenericMethod) continue;
                var an = m.DeclaringType.Assembly.GetName().Name;
                if (!Mods.Contains(an)) continue;
                names[m] = $"{an}:{m.DeclaringType.FullName}.{m.Name} <- {orig.DeclaringType?.Name}.{orig.Name}";
                targets.Add(m);
            }
        }
        // TOR's per-frame helpers one by one (HUD update and FixedUpdate split into their parts)
        foreach (var tn in new[] { "TheOtherRoles.Patches.HudManagerUpdatePatch", "TheOtherRoles.Patches.PlayerControlFixedUpdatePatch", "TheOtherRoles.Objects.CustomButton", "TheOtherRoles.Utilities.EventUtility" })
        {
            var t = AccessTools.TypeByName(tn);
            if (t == null) continue;
            foreach (var m in t.GetMethods(BindingFlags.Static | BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
            {
                if (m.IsGenericMethod || m.IsAbstract || m.GetMethodBody() == null || targets.Contains(m)) continue;
                if (m.Name == "Postfix" || m.Name == "Prefix") continue;
                names[m] = $"TOR-part:{t.Name}.{m.Name}";
                targets.Add(m);
            }
        }
        // UC's per-frame effect ticks (UCFx.ticks), one by one
        try
        {
            var fx = AccessTools.TypeByName("UnknownsCollection.UCFx");
            var list = fx != null ? AccessTools.Field(fx, "ticks")?.GetValue(null) as System.Collections.IEnumerable : null;
            if (list != null)
                foreach (var o in list)
                    if (o is Delegate d && d.Method != null && !d.Method.IsGenericMethod && d.Method.GetMethodBody() != null && !targets.Contains(d.Method))
                    {
                        names[d.Method] = $"UCFx-tick:{d.Method.DeclaringType?.Name}.{d.Method.Name}";
                        targets.Add(d.Method);
                    }
        }
        catch (Exception e) { DuoPlugin.Say("prof: UCFx ticks " + e.Message); }
        int ok = 0;
        foreach (var m in targets)
        {
            try { h.Patch(m, prefix: pre, postfix: post); ok++; }
            catch { }
        }
        // Atlas' per-feature tick runner: charge by tick name as well
        try
        {
            var run = AccessTools.Method(AccessTools.TypeByName("UnknownsAtlas.AtlasWorld"), "Run");
            if (run != null) h.Patch(run, prefix: new HarmonyMethod(typeof(DuoProf).GetMethod(nameof(RunPre), BindingFlags.Static | BindingFlags.NonPublic)),
                postfix: new HarmonyMethod(typeof(DuoProf).GetMethod(nameof(RunPost), BindingFlags.Static | BindingFlags.NonPublic)));
        }
        catch (Exception e) { DuoPlugin.Say("prof: Run hook failed " + e.Message); }
        DuoPlugin.Say($"prof: wrapped {ok}/{targets.Count} patch methods");
    }

    struct St { public long used; public long t; public long heap; }
    static void Pre(MethodBase __originalMethod, out St __state) { __state = new St { used = il2cpp_gc_get_used_size(), t = System.Diagnostics.Stopwatch.GetTimestamp(), heap = il2cpp_gc_get_heap_size() }; }
    static void Post(MethodBase __originalMethod, St __state) => Charge(names.TryGetValue(__originalMethod, out var n) ? n : __originalMethod.Name, __state);
    static void RunPre(out St __state) { __state = new St { used = il2cpp_gc_get_used_size(), t = System.Diagnostics.Stopwatch.GetTimestamp(), heap = il2cpp_gc_get_heap_size() }; }
    static void RunPost(string name, St __state) => Charge("AtlasWorld.Run:" + name, __state);

    static void Charge(string key, St s)
    {
        long d = il2cpp_gc_get_used_size() - s.used;
        double ms = (System.Diagnostics.Stopwatch.GetTimestamp() - s.t) * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
        acc.TryGetValue(key, out var a);
        acc[key] = (a.bytes + Math.Max(0, d), a.calls + 1, a.ms + ms);
        long g = il2cpp_gc_get_heap_size() - s.heap;
        if (g > 0) { grow.TryGetValue(key, out var gv); grow[key] = gv + g; }
    }

    internal static IEnumerable<(string key, long bytes, long calls, double ms)> TakeAndReset()
    {
        var l = acc.Select(kv => (kv.Key, kv.Value.bytes, kv.Value.calls, kv.Value.ms)).ToList();
        acc.Clear();
        return l;
    }

    // heap expansion per wrapped method since the last call (the methods inside which the il2cpp heap grew)
    internal static List<(string key, long bytes)> TakeGrowth()
    {
        var l = grow.Select(kv => (kv.Key, kv.Value)).ToList();
        grow.Clear();
        return l;
    }
}
