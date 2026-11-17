// Heap trace (2026-11-13): when does the il2cpp heap grow? Every half second while the file "duo_trace_on" is in the
// instance folder: seconds since start, il2cpp heap size, il2cpp used size, process private bytes, the game phase and
// the last DUO mark, into duo_trace.tsv. The heap only grows, so the rows where it jumps name the phase that made
// it grow (map build, intro, play, meeting, end screen).
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

namespace DuoTest;

internal static class DuoTrace
{
    [DllImport("GameAssembly", CallingConvention = CallingConvention.Cdecl)] static extern long il2cpp_gc_get_heap_size();
    [DllImport("GameAssembly", CallingConvention = CallingConvention.Cdecl)] static extern long il2cpp_gc_get_used_size();

    static bool? on;
    static long next;
    static StreamWriter w;
    static readonly long t0 = Environment.TickCount64;
    internal static string LastMark = "";

    internal static void Tick()
    {
        on ??= File.Exists(Path.Combine(DuoPlugin.Root, "duo_trace_on"));
        if (on != true) return;
        long now = Environment.TickCount64;
        if (now < next) return;
        next = now + 500;
        try
        {
            if (w == null)
            {
                w = new StreamWriter(Path.Combine(DuoPlugin.Root, "duo_trace.tsv"), false) { AutoFlush = true };
                w.WriteLine("t\theap_mb\tused_mb\tprivate_mb\tphase\tmark");
            }
            string phase;
            if (!ReferenceEquals(MeetingHud.Instance, null)) phase = "meeting";
            else if (!ReferenceEquals(ExileController.Instance, null)) phase = "exile";
            else if (!ReferenceEquals(IntroCutscene.Instance, null)) phase = "intro";
            else if (!ReferenceEquals(ShipStatus.Instance, null)) phase = "play:" + ShipStatus.Instance.Type;
            else if (!ReferenceEquals(LobbyBehaviour.Instance, null)) phase = "lobby";
            else phase = "other";
            long priv = Process.GetCurrentProcess().PrivateMemorySize64;
            w.WriteLine($"{(now - t0) / 1000.0:F1}\t{il2cpp_gc_get_heap_size() / 1048576.0:F1}\t{il2cpp_gc_get_used_size() / 1048576.0:F1}\t{priv / 1048576}\t{phase}\t{LastMark}");
        }
        catch { on = false; }
    }
}
