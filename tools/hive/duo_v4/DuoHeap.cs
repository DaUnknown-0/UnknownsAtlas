// Il2Cpp heap histogram: every managed object reachable from il2cpp statics and from all Unity objects,
// grouped by class (count, bytes). Uses the liveness API Unity itself uses for FindObjectsOfTypeAll.
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Il2CppInterop.Runtime.InteropTypes;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace DuoTest;

internal static class DuoHeap
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void RegCb(IntPtr arr, int size, IntPtr ud);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void WorldCb();
    const string GA = "GameAssembly";
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_unity_liveness_calculation_begin(IntPtr filter, int max, IntPtr cb, IntPtr ud, IntPtr onStarted, IntPtr onStopped);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern void il2cpp_unity_liveness_calculation_end(IntPtr state);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern void il2cpp_unity_liveness_calculation_from_root(IntPtr root, IntPtr state);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern void il2cpp_unity_liveness_calculation_from_statics(IntPtr state);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_class_get_name(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_class_get_namespace(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_class_get_declaring_type(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern int il2cpp_class_instance_size(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern int il2cpp_class_get_rank(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern int il2cpp_class_array_element_size(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_class_get_element_class(IntPtr k);
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern IntPtr il2cpp_capture_memory_snapshot();
    [DllImport(GA, CallingConvention = CallingConvention.Cdecl)] static extern void il2cpp_free_captured_memory_snapshot(IntPtr s);

    static readonly List<IntPtr> found = new();
    internal static List<IntPtr> LastTargets = new();
    static RegCb regCb; static WorldCb noop;

    static void OnObjects(IntPtr arr, int size, IntPtr ud)
    {
        for (int i = 0; i < size; i++) found.Add(Marshal.ReadIntPtr(arr, i * IntPtr.Size));
    }

    static readonly Dictionary<IntPtr, string> names = new();
    static string Name(IntPtr k)
    {
        if (names.TryGetValue(k, out var n)) return n;
        try
        {
            if (il2cpp_class_get_rank(k) > 0) n = Name(il2cpp_class_get_element_class(k)) + "[]";
            else
            {
                n = Marshal.PtrToStringAnsi(il2cpp_class_get_name(k));
                var decl = il2cpp_class_get_declaring_type(k);
                if (decl != IntPtr.Zero) n = Name(decl) + "+" + n;
                else { var ns = Marshal.PtrToStringAnsi(il2cpp_class_get_namespace(k)); if (!string.IsNullOrEmpty(ns)) n = ns + "." + n; }
            }
        }
        catch { n = "?"; }
        names[k] = n;
        return n;
    }

    internal static Dictionary<string, (long n, long b)> Histogram(out string info)
    {
        found.Clear();
        var hist = new Dictionary<string, (long n, long b)>();
        regCb ??= OnObjects; noop ??= () => { };
        var roots = Resources.FindObjectsOfTypeAll(Il2CppType.Of<UnityEngine.Object>());
        var rootPtrs = new List<IntPtr>(roots.Length);
        foreach (var o in roots) if (o != null) rootPtrs.Add(o.Pointer);
        IntPtr filter = Il2CppClassPointerStore<Il2CppSystem.Object>.NativeClassPtr;
        var state = il2cpp_unity_liveness_calculation_begin(filter, 4096, Marshal.GetFunctionPointerForDelegate(regCb), IntPtr.Zero,
            Marshal.GetFunctionPointerForDelegate(noop), Marshal.GetFunctionPointerForDelegate(noop));
        il2cpp_unity_liveness_calculation_from_statics(state);
        foreach (var r in rootPtrs) il2cpp_unity_liveness_calculation_from_root(r, state);
        il2cpp_unity_liveness_calculation_end(state);
        GC.KeepAlive(roots);
        long total = 0;
        foreach (var obj in found)
        {
            if (obj == IntPtr.Zero) continue;
            IntPtr k = (IntPtr)((long)Marshal.ReadIntPtr(obj) & ~1L);
            long size;
            try
            {
                int rank = il2cpp_class_get_rank(k);
                if (rank > 0) size = 4 * IntPtr.Size + (long)Marshal.ReadInt32(obj, 3 * IntPtr.Size) * il2cpp_class_array_element_size(k);
                else
                {
                    size = il2cpp_class_instance_size(k);
                    if (Name(k) == "System.String") size = 2 * IntPtr.Size + 4 + 2L * Marshal.ReadInt32(obj, 2 * IntPtr.Size);
                }
            }
            catch { size = 0; }
            var nm = Name(k);
            hist.TryGetValue(nm, out var h); hist[nm] = (h.n + 1, h.b + size); total += size;
        }
        info = $"objects={found.Count} roots={rootPtrs.Count} bytes={total}";
        found.Clear();
        return hist;
    }
    // ---------------------------------------------------------------- .NET statics -> il2cpp bytes
    sealed class RefEq : IEqualityComparer<object>
    {
        public new bool Equals(object a, object b) => ReferenceEquals(a, b);
        public int GetHashCode(object o) => RuntimeHelpers.GetHashCode(o);
    }
    static readonly Dictionary<Type, FieldInfo[]> instFields = new();
    static FieldInfo[] InstFields(Type t)
    {
        if (instFields.TryGetValue(t, out var f)) return f;
        var l = new List<FieldInfo>();
        for (var x = t; x != null && x != typeof(object); x = x.BaseType)
            foreach (var fi in x.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
                if (!fi.FieldType.IsPrimitive && !fi.FieldType.IsEnum && fi.FieldType != typeof(string) && !fi.FieldType.IsPointer && fi.FieldType != typeof(IntPtr)) l.Add(fi);
        return instFields[t] = l.ToArray();
    }
    static bool Skip(object o) { var t = o.GetType(); return t.IsPrimitive || t.IsEnum || o is string || o is Type || o is MemberInfo || o is Assembly || o is Module || t.IsPointer; }

    internal static List<(string field, long n, long b, int ptrs)> ByStatics()
    {
        var visited = new HashSet<object>(new RefEq());
        var perField = new List<(string, List<IntPtr>)>();
        int budget = 3_000_000;
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            string an = asm.GetName().Name;
            if (an.StartsWith("System") || an.StartsWith("Microsoft") || an == "mscorlib" || an == "netstandard" || an == "DuoTest" || asm.IsDynamic) continue;
            Type[] types; try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException e) { types = Array.FindAll(e.Types, x => x != null); } catch { continue; }
            foreach (var t in types)
            {
                if (t.ContainsGenericParameters) continue;
                FieldInfo[] fs; try { fs = t.GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly); } catch { continue; }
                foreach (var f in fs)
                {
                    if (f.IsLiteral || f.FieldType.IsPrimitive || f.FieldType.IsEnum || f.FieldType == typeof(string) || f.FieldType == typeof(IntPtr) || f.FieldType.IsPointer) continue;
                    object v; try { v = f.GetValue(null); } catch { continue; }
                    if (v == null || Skip(v)) continue;
                    var ptrs = new List<IntPtr>();
                    var q = new Queue<object>(); if (visited.Add(v)) q.Enqueue(v);
                    while (q.Count > 0 && budget-- > 0)
                    {
                        var o = q.Dequeue();
                        if (o is Il2CppObjectBase ib) { try { var p = ib.Pointer; if (p != IntPtr.Zero) ptrs.Add(p); } catch { } continue; }
                        void Push(object c) { if (c != null && !Skip(c) && visited.Add(c)) q.Enqueue(c); }
                        try
                        {
                            if (o is Array arr) { if (!arr.GetType().GetElementType().IsPrimitive) foreach (var e in arr) Push(e); continue; }
                            if (o is Delegate d) { foreach (var dd in d.GetInvocationList()) Push(dd.Target); continue; }
                            foreach (var fi in InstFields(o.GetType())) { object c; try { c = fi.GetValue(o); } catch { continue; } Push(c); }
                        }
                        catch { }
                    }
                    if (ptrs.Count > 0) perField.Add(($"{an}:{t.FullName}.{f.Name}", ptrs));
                }
            }
        }
        var res = new List<(string, long, long, int)>();
        regCb ??= OnObjects; noop ??= () => { };
        IntPtr filter = Il2CppClassPointerStore<Il2CppSystem.Object>.NativeClassPtr;
        foreach (var (name, ptrs) in perField)
        {
            found.Clear();
            var state = il2cpp_unity_liveness_calculation_begin(filter, 4096, Marshal.GetFunctionPointerForDelegate(regCb), IntPtr.Zero,
                Marshal.GetFunctionPointerForDelegate(noop), Marshal.GetFunctionPointerForDelegate(noop));
            foreach (var p in ptrs) il2cpp_unity_liveness_calculation_from_root(p, state);
            il2cpp_unity_liveness_calculation_end(state);
            long b = 0; foreach (var obj in found) b += SizeOf(obj);
            res.Add((name, found.Count, b, ptrs.Count));
            found.Clear();
        }
        return res;
    }

    static long SizeOf(IntPtr obj)
    {
        if (obj == IntPtr.Zero) return 0;
        IntPtr k = (IntPtr)((long)Marshal.ReadIntPtr(obj) & ~1L);
        try
        {
            if (il2cpp_class_get_rank(k) > 0) return 4 * IntPtr.Size + (long)Marshal.ReadInt32(obj, 3 * IntPtr.Size) * il2cpp_class_array_element_size(k);
            if (Name(k) == "System.String") return 2 * IntPtr.Size + 4 + 2L * Marshal.ReadInt32(obj, 2 * IntPtr.Size);
            return il2cpp_class_instance_size(k);
        }
        catch { return 0; }
    }
    // ---------------------------------------------------------------- GC handles -> retained bytes per target class
    internal static List<(string cls, int handles, long n, long b)> ByHandles(out string info)
    {
        var res = new List<(string, int, long, long)>();
        var targets = new List<IntPtr>();
        long heapBytes = 0; int sections = 0;
        IntPtr snap = il2cpp_capture_memory_snapshot();
        try
        {
            int P = IntPtr.Size;                                  // 32-bit: every {count, ptr} pair is 8 bytes
            sections = Marshal.ReadInt32(snap, 0);
            IntPtr secs = Marshal.ReadIntPtr(snap, 4);
            for (int i = 0; i < sections; i++) heapBytes += (uint)Marshal.ReadInt32(secs, i * 16 + 8);
            int ptrSize = Marshal.ReadInt32(snap, 32), hdr = Marshal.ReadInt32(snap, 36);
            if (P != 4 || ptrSize != 4 || hdr != 8) { info = $"layout? ptr={ptrSize} hdr={hdr}"; return res; }
            int count = Marshal.ReadInt32(snap, 24);
            IntPtr arr = Marshal.ReadIntPtr(snap, 28);
            for (int i = 0; i < count; i++) { long v = Marshal.ReadInt64(arr, i * 8); if (v != 0) targets.Add((IntPtr)v); }
        }
        finally { il2cpp_free_captured_memory_snapshot(snap); }
        LastTargets = targets;
        var groups = new Dictionary<string, List<IntPtr>>();
        foreach (var t in targets)
        {
            IntPtr k = (IntPtr)((long)Marshal.ReadIntPtr(t) & ~1L);
            var nm = Name(k);
            if (!groups.TryGetValue(nm, out var l)) groups[nm] = l = new List<IntPtr>();
            l.Add(t);
        }
        regCb ??= OnObjects; noop ??= () => { };
        IntPtr filter = Il2CppClassPointerStore<Il2CppSystem.Object>.NativeClassPtr;
        long all = 0;
        foreach (var kv in groups)
        {
            found.Clear();
            var state = il2cpp_unity_liveness_calculation_begin(filter, 4096, Marshal.GetFunctionPointerForDelegate(regCb), IntPtr.Zero,
                Marshal.GetFunctionPointerForDelegate(noop), Marshal.GetFunctionPointerForDelegate(noop));
            foreach (var p in kv.Value) il2cpp_unity_liveness_calculation_from_root(p, state);
            il2cpp_unity_liveness_calculation_end(state);
            long b = 0; foreach (var o in found) b += SizeOf(o);
            res.Add((kv.Key, kv.Value.Count, found.Count, b));
            found.Clear();
        }
        // everything reachable from all handles together (no double counting)
        found.Clear();
        var st = il2cpp_unity_liveness_calculation_begin(filter, 4096, Marshal.GetFunctionPointerForDelegate(regCb), IntPtr.Zero,
            Marshal.GetFunctionPointerForDelegate(noop), Marshal.GetFunctionPointerForDelegate(noop));
        foreach (var p in targets) il2cpp_unity_liveness_calculation_from_root(p, st);
        il2cpp_unity_liveness_calculation_from_statics(st);
        il2cpp_unity_liveness_calculation_end(st);
        foreach (var o in found) all += SizeOf(o);
        info = $"handles={targets.Count} sections={sections} heapBytes={heapBytes} reachableAll={all} objectsAll={found.Count}";
        found.Clear();
        return res;
    }
    // ---------------------------------------------------------------- injected objects (.NET side) -> il2cpp bytes
    static Dictionary<IntPtr, Type> injected;
    static MethodInfo getMono;
    static void IndexInjected()
    {
        injected = new Dictionary<IntPtr, Type>();
        var ci = Type.GetType("Il2CppInterop.Runtime.Injection.ClassInjector, Il2CppInterop.Runtime");
        var isReg = ci?.GetMethod("IsTypeRegisteredInIl2Cpp", new[] { typeof(Type) });
        var store = Type.GetType("Il2CppInterop.Runtime.Il2CppClassPointerStore, Il2CppInterop.Runtime");
        var getPtr = store?.GetMethod("GetNativeClassPointer", BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic, null, new[] { typeof(Type) }, null);
        try
        {
            foreach (var tt in ci.Assembly.GetTypes())
            {
                var mm = tt.GetMethod("GetMonoObjectFromIl2CppPointer", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static, null, new[] { typeof(IntPtr) }, null);
                if (mm != null) { getMono = mm; break; }
            }
        }
        catch (ReflectionTypeLoadException) { }
        if (isReg == null || getPtr == null || getMono == null) { DuoPlugin.Say($"injected index: isReg={isReg != null} getPtr={getPtr != null} getMono={getMono != null}"); return; }
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            string an = asm.GetName().Name;
            if (asm.IsDynamic) continue;
            string loc; try { loc = asm.Location ?? ""; } catch { continue; }
            // only real managed code (mods, BepInEx, Il2CppInterop): the generated interop proxies live in BepInEx\interop
            string ll = loc.Replace(System.IO.Path.DirectorySeparatorChar, (char)47).ToLowerInvariant();
            if (!ll.Contains("/plugins/") && !ll.Contains("/core/")) continue;
            Type[] types; try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException e) { types = Array.FindAll(e.Types, x => x != null); } catch { continue; }
            foreach (var t in types)
            {
                if (t.ContainsGenericParameters || !typeof(Il2CppObjectBase).IsAssignableFrom(t)) continue;
                try
                {
                    if (!(bool)isReg.Invoke(null, new object[] { t })) continue;
                    var k = (IntPtr)getPtr.Invoke(null, new object[] { t });
                    if (k != IntPtr.Zero) injected[k] = t;
                }
                catch { }
            }
        }
        DuoPlugin.Say($"injected index: {injected.Count} types");
    }

    static List<IntPtr> Collect(object root, HashSet<object> visited, ref int budget)
    {
        var ptrs = new List<IntPtr>();
        var q = new Queue<object>(); if (root != null && visited.Add(root)) q.Enqueue(root);
        bool first = true;
        while (q.Count > 0 && budget-- > 0)
        {
            var o = q.Dequeue();
            if (!first && o is Il2CppObjectBase ib) { try { var p = ib.Pointer; if (p != IntPtr.Zero) ptrs.Add(p); } catch { } continue; }
            first = false;
            void Push(object c) { if (c != null && !Skip(c) && visited.Add(c)) q.Enqueue(c); }
            try
            {
                if (o is Array arr) { if (!arr.GetType().GetElementType().IsPrimitive) foreach (var e in arr) Push(e); continue; }
                if (o is Delegate d) { foreach (var dd in d.GetInvocationList()) Push(dd.Target); continue; }
                foreach (var fi in InstFields(o.GetType())) { object c; try { c = fi.GetValue(o); } catch { continue; } Push(c); }
            }
            catch { }
        }
        return ptrs;
    }

    internal static List<(string key, int objs, long n, long b)> ByInjected()
    {
        var res = new List<(string, int, long, long)>();
        if (injected == null) IndexInjected();
        if (injected.Count == 0 || getMono == null) return res;
        var groups = new Dictionary<string, (int objs, List<IntPtr> ptrs)>();
        var visited = new HashSet<object>(new RefEq());
        int budget = 3_000_000;
        foreach (var t in LastTargets)
        {
            IntPtr k = (IntPtr)((long)Marshal.ReadIntPtr(t) & ~1L);
            if (!injected.TryGetValue(k, out var type)) continue;
            object mono; try { mono = getMono.Invoke(null, new object[] { t }); } catch { continue; }
            if (mono == null) continue;
            // name the group by what the object carries: a delegate by its method, a coroutine by its enumerator
            string key = type.FullName;
            foreach (var fi in InstFields(mono.GetType()))
            {
                object v; try { v = fi.GetValue(mono); } catch { continue; }
                if (v is Delegate dl) { key += " => " + dl.Method.DeclaringType?.FullName + "." + dl.Method.Name; break; }
                if (v is System.Collections.IEnumerator en && v.GetType() != mono.GetType()) { key += " => " + v.GetType().FullName; break; }
            }
            var ptrs = Collect(mono, visited, ref budget);
            if (!groups.TryGetValue(key, out var g)) g = (0, new List<IntPtr>());
            g.objs++; g.ptrs.AddRange(ptrs); groups[key] = g;
        }
        regCb ??= OnObjects; noop ??= () => { };
        IntPtr filter = Il2CppClassPointerStore<Il2CppSystem.Object>.NativeClassPtr;
        foreach (var kv in groups)
        {
            found.Clear();
            if (kv.Value.ptrs.Count > 0)
            {
                var state = il2cpp_unity_liveness_calculation_begin(filter, 4096, Marshal.GetFunctionPointerForDelegate(regCb), IntPtr.Zero,
                    Marshal.GetFunctionPointerForDelegate(noop), Marshal.GetFunctionPointerForDelegate(noop));
                foreach (var p in kv.Value.ptrs) il2cpp_unity_liveness_calculation_from_root(p, state);
                il2cpp_unity_liveness_calculation_end(state);
            }
            long b = 0; foreach (var o in found) b += SizeOf(o);
            res.Add((kv.Key, kv.Value.objs, found.Count, b));
            found.Clear();
        }
        return res;
    }
}
