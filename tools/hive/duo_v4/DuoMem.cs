// Memory census: counts every loaded Unity object by type and name and estimates its native size.
// Written to duo_mem.tsv at each lobby snapshot so rounds can be compared (which objects pile up).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Il2CppInterop.Runtime;
using UnityEngine;
using UnityEngine.Profiling;

namespace DuoTest;

internal static class DuoMem
{
    static string MemFile => Path.Combine(DuoPlugin.Root, "duo_mem.tsv");

    static long TexBytes(Texture2D t)
    {
        double bpp = t.format switch
        {
            TextureFormat.DXT1 or TextureFormat.DXT1Crunched or TextureFormat.BC4 => 0.5,
            TextureFormat.DXT5 or TextureFormat.DXT5Crunched or TextureFormat.BC7 or TextureFormat.BC5 => 1,
            TextureFormat.Alpha8 or TextureFormat.R8 => 1,
            TextureFormat.RGB24 => 3,
            TextureFormat.RGB565 or TextureFormat.RGBA4444 or TextureFormat.ARGB4444 or TextureFormat.R16 => 2,
            TextureFormat.RGBAHalf => 8,
            TextureFormat.RGBAFloat => 16,
            _ => 4,
        };
        double b = (double)t.width * t.height * bpp;
        if (t.mipmapCount > 1) b *= 1.333;
        if (t.isReadable) b *= 2;   // CPU copy as well
        return (long)b;
    }

    internal static void Write(string label)
    {
        var sb = new StringBuilder();
        void Add(string type, string name, long count, long bytes) =>
            sb.Append(label).Append('\t').Append(type).Append('\t').Append(name.Replace('\t', ' ')).Append('\t').Append(count).Append('\t').Append(bytes).Append('\n');
        try
        {
            try { Add("gc", "il2cpp-before", 1, Il2CppSystem.GC.GetTotalMemory(false)); } catch { }
            // live set only: .NET wrappers hold strong handles on il2cpp objects until their finalizers ran
            for (int i = 0; i < 2; i++) { GC.Collect(); GC.WaitForPendingFinalizers(); }
            try { Il2CppSystem.GC.Collect(); } catch { }
            using (var p = System.Diagnostics.Process.GetCurrentProcess())
            {
                Add("proc", "private", 1, p.PrivateMemorySize64);
                Add("proc", "workingset", 1, p.WorkingSet64);
            }
            Add("gc", "dotnet", 1, GC.GetTotalMemory(false));
            try { Add("gc", "il2cpp", 1, Il2CppSystem.GC.GetTotalMemory(false)); } catch { }
            try { Add("unity", "allocated", 1, Profiler.GetTotalAllocatedMemoryLong()); Add("unity", "reserved", 1, Profiler.GetTotalReservedMemoryLong()); Add("unity", "mono", 1, Profiler.GetMonoUsedSizeLong()); } catch { }
            void Census<T>(Func<T, long> size, Func<T, string> key) where T : UnityEngine.Object
            {
                var all = Resources.FindObjectsOfTypeAll(Il2CppType.Of<T>());
                var groups = new Dictionary<string, (long n, long b)>();
                long total = 0;
                foreach (var o in all)
                {
                    T x; try { x = o.TryCast<T>(); } catch { continue; }
                    if (x == null) continue;
                    long b = 0; try { b = size(x); } catch { }
                    string k; try { k = key(x); } catch { k = "?"; }
                    groups.TryGetValue(k, out var g); groups[k] = (g.n + 1, g.b + b); total += b;
                }
                var tn = typeof(T).Name;
                Add(tn, "*TOTAL*", all.Length, total);
                foreach (var kv in groups.OrderByDescending(g => g.Value.b).ThenByDescending(g => g.Value.n).Take(400)) Add(tn, kv.Key, kv.Value.n, kv.Value.b);
            }
            try
            {
                var h = DuoHeap.Histogram(out var info);
                long tb = 0, tn = 0; foreach (var v in h.Values) { tb += v.b; tn += v.n; }
                Add("heap", "*TOTAL* " + info, tn, tb);
                foreach (var kv in h.OrderByDescending(x => x.Value.b).Take(300)) Add("heap", kv.Key, kv.Value.n, kv.Value.b);
            }
            catch (Exception e) { Add("heap", "error " + e.Message, 0, 0); }
            try
            {
                var sw = System.Diagnostics.Stopwatch.StartNew();
                var st = DuoHeap.ByStatics();
                Add("statroot", "*TIME* ms", st.Count, sw.ElapsedMilliseconds);
                foreach (var r in st.OrderByDescending(x => x.b).Take(150)) Add("statroot", $"{r.field} ptrs={r.ptrs}", r.n, r.b);
            }
            catch (Exception e) { Add("statroot", "error " + e.Message, 0, 0); }
            try
            {
                var hh = DuoHeap.ByHandles(out var hinfo);
                Add("handles", "*INFO* " + hinfo, hh.Count, 0);
                foreach (var r in hh.OrderByDescending(x => x.b).Take(200)) Add("handles", $"{r.cls} h={r.handles}", r.n, r.b);
            }
            catch (Exception e) { Add("handles", "error " + e.Message, 0, 0); }
            try
            {
                var inj = DuoHeap.ByInjected();
                Add("injected", "*COUNT*", inj.Count, 0);
                foreach (var r in inj.OrderByDescending(x => x.b).Take(150)) Add("injected", $"{r.key} objs={r.objs}", r.n, r.b);
            }
            catch (Exception e) { Add("injected", "error " + e.Message, 0, 0); }
            Census<Texture2D>(TexBytes, t => $"{(string.IsNullOrEmpty(t.name) ? "<noname>" : t.name)} {t.width}x{t.height} {t.format}{(t.isReadable ? " R" : "")} hf={(int)t.hideFlags}");
            Census<RenderTexture>(t => (long)t.width * t.height * 8, t => $"{t.name} {t.width}x{t.height}");
            Census<Sprite>(s => 0, s => $"{s.name} tex={(s.texture ? s.texture.name : "null")}");
            Census<Mesh>(m => (long)m.vertexCount * 48, m => $"{m.name} v={(m.vertexCount / 100) * 100}");
            Census<Material>(m => 0, m => $"{m.name} sh={(m.shader ? m.shader.name : "null")}");
            Census<AudioClip>(c => (long)c.samples * c.channels * 4, c => c.name);
            Census<GameObject>(g => 0, g => $"{g.name} scene={(g.scene.IsValid() ? g.scene.name : "none")} root={(g.transform.parent == null)}");
            // owners: every scene-less (asset) or DontDestroyOnLoad object grouped by its root object
            Census<Transform>(t => 0, t =>
            {
                var sc = t.gameObject.scene;
                string scn = sc.IsValid() ? sc.name : "none";
                if (scn != "none" && scn != "DontDestroyOnLoad") return "scene:" + scn;
                return $"{scn} root={t.root.name}";
            });
        }
        catch (Exception e) { Add("error", e.ToString().Replace('\n', '|'), 0, 0); }
        try
        {
            if (!File.Exists(Path.Combine(DuoPlugin.Root, "duo_prof_on"))) { }
            else if (!DuoProf.Installed) DuoProf.Install();
            else
            {
                foreach (var r in DuoProf.TakeAndReset().OrderByDescending(x => x.bytes).Take(120))
                    Add("alloc", $"{r.key} calls={r.calls} ms={(long)r.ms}", r.calls, r.bytes);
                foreach (var g in DuoProf.TakeGrowth().OrderByDescending(x => x.bytes).Take(40))
                    Add("grow", g.key, 1, g.bytes);
            }
        }
        catch (Exception e) { Add("alloc", "error " + e.Message, 0, 0); }
        File.AppendAllText(MemFile, sb.ToString());
    }
}
