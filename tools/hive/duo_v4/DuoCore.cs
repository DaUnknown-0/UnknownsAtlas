// DuoTest: multi-client test driver for the TOR mod family. Test-only, never shipped.
// duo_role.txt next to Among Us.exe:  "host A <clients> <plan>"  or  "client B"
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using HarmonyLib;
using Hazel;
using InnerNet;
using UnityEngine;

namespace DuoTest;

[BepInPlugin("test.duotest", "DuoTest", "1.0.0")]
[BepInDependency("me.eisbison.theotherroles")]
[BepInDependency("com.tormod.usefultorstuff", BepInDependency.DependencyFlags.SoftDependency)]
[BepInDependency("com.trackerteam.forceimpostor", BepInDependency.DependencyFlags.SoftDependency)]
[BepInDependency("com.tormod.unknownscollection", BepInDependency.DependencyFlags.SoftDependency)]
public class DuoPlugin : BasePlugin
{
    internal static ManualLogSource L;
    internal static bool IsHost, Active;
    internal static string Tag = "?";
    internal static int ExpectedClients = 1;
    internal static string Plan = "smoke";
    internal static string Root;
    internal const byte CallId = 222;

    // A click into the BepInEx console starts Windows' "select" mode (title "Auswählen ..."), and while it lasts every
    // console write blocks: the game hangs at its next log line ("Keine Rückmeldung", 13.11.). Test copies only.
    [System.Runtime.InteropServices.DllImport("kernel32.dll")] private static extern IntPtr GetStdHandle(int n);
    [System.Runtime.InteropServices.DllImport("kernel32.dll")] private static extern bool GetConsoleMode(IntPtr h, out uint m);
    [System.Runtime.InteropServices.DllImport("kernel32.dll")] private static extern bool SetConsoleMode(IntPtr h, uint m);
    [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern IntPtr CreateFileW(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);

    private static void NoQuickEdit()
    {
        try
        {
            // CONIN$ instead of the std handle: BepInEx allocates the console itself, stdin may not point at it
            IntPtr h = CreateFileW("CONIN$", 0xC0000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
            if (h == new IntPtr(-1)) h = GetStdHandle(-10);
            if (GetConsoleMode(h, out uint m)) SetConsoleMode(h, (m & ~0x40u) | 0x80u); // QUICK_EDIT off, EXTENDED_FLAGS on
        }
        catch { }
    }

    public override void Load()
    {
        L = Log;
        Root = Paths.GameRootPath;
        NoQuickEdit();
        var f = Path.Combine(Root, "duo_role.txt");
        var parts = File.Exists(f) ? File.ReadAllText(f).Split((char[])null, StringSplitOptions.RemoveEmptyEntries) : new string[0];
        if (parts.Length < 2 || (parts[0] != "host" && parts[0] != "client")) { L.LogWarning("DUO no duo_role.txt, idle"); return; }
        IsHost = parts[0] == "host";
        Tag = parts[1];
        if (parts.Length > 2) int.TryParse(parts[2], out ExpectedClients);
        if (parts.Length > 3) Plan = parts[3];
        Active = true;
        Application.runInBackground = true;
        var hx = new Harmony("test.duotest");
        hx.PatchAll();
        try { if (AmongUs.Data.DataManager.IsSettingsLoaded) AmongUs.Data.DataManager.Settings.ForceLoad(); } catch (Exception e) { L.LogWarning("DUO settings reload: " + e.Message); }
        AddComponent<DuoDriver>();
        Say($"loaded as {parts[0]} {Tag}, clients={ExpectedClients}, plan={Plan}");
    }

    internal static string Now() => DateTime.Now.ToString("HH:mm:ss.fff");
    internal static void Say(string m) { if (m.StartsWith("=== ")) DuoTrace.LastMark = m.Substring(4).Replace('	', ' '); L.LogInfo($"DUO {Now()} [{Tag}] {m}"); }

    // ---- wire: [222][string] to everyone; the sender also handles its own message ----
    internal static void Broadcast(string msg, bool alsoLocal = true)
    {
        try
        {
            var w = AmongUsClient.Instance.StartRpcImmediately(PlayerControl.LocalPlayer.NetId, CallId, SendOption.Reliable, -1);
            w.Write(msg);
            AmongUsClient.Instance.FinishRpcImmediately(w);
        }
        catch (Exception e) { Say("send failed: " + e.Message); }
        if (alsoLocal) DuoCommands.Handle(msg, PlayerControl.LocalPlayer ? PlayerControl.LocalPlayer.PlayerId : (byte)255);
    }
}

public class DuoDriver : MonoBehaviour
{
    public DuoDriver(IntPtr p) : base(p) { }
    internal static float QuitAt = -1f;
    internal static DuoDriver Instance;
    static bool started;

    void Awake() { Instance = this; }

    void Update()
    {
        if (QuitAt > 0 && Time.realtimeSinceStartup > QuitAt) { DuoPlugin.Say("quit"); QuitAt = -1; Application.Quit(); }
        if (!started && FindObjectOfType<MainMenuManager>() != null)
        {
            started = true;
            StartCoroutine((DuoPlugin.IsHost ? DuoHost.Run() : DuoClient.Run()).WrapToIl2Cpp());
        }
        DuoCommands.Tick();
        HiveV4.Tick();
        DuoTrace.Tick();
        // after a game end: host presses "play again" first, clients a bit later
        if (Time.realtimeSinceStartup > navCheck)
        {
            navCheck = Time.realtimeSinceStartup + 1f;
            var nav = FindObjectOfType<EndGameNavigation>();
            if (nav == null) { navAt = -1f; navDone = false; }
            else if (!navDone)
            {
                if (navAt < 0) navAt = Time.realtimeSinceStartup + (DuoPlugin.IsHost ? 6f : 14f);
                else if (Time.realtimeSinceStartup > navAt) { navDone = true; DuoPlugin.Say("end screen: NextGame"); try { nav.NextGame(); } catch (Exception e) { DuoPlugin.Say("NextGame failed " + e.Message); } }
            }
        }
    }
    static float navCheck, navAt = -1f;
    static bool navDone;

    internal static void Start(IEnumerator e) => Instance.StartCoroutine(e.WrapToIl2Cpp());
}

internal static class Co
{
    internal static IEnumerator Wait(float s) { float t = Time.realtimeSinceStartup + s; while (Time.realtimeSinceStartup < t) yield return null; }
    internal static IEnumerator Until(Func<bool> p, float timeout) { float t = Time.realtimeSinceStartup + timeout; while (Time.realtimeSinceStartup < t) { bool ok; try { ok = p(); } catch { ok = false; } if (ok) yield break; yield return null; } }

    static string Puid() { try { return EOSManager.Instance ? EOSManager.Instance.ProductUserId : "none"; } catch (Exception e) { return "ERR " + e.GetType().Name; } }

    internal static IEnumerator WaitEos()
    {
        float t0 = Time.realtimeSinceStartup;
        while (Time.realtimeSinceStartup - t0 < 45f)
        {
            var e = EOSManager.Instance;
            var id = Puid();
            if (e && e.loginFlowFinished && !string.IsNullOrEmpty(id) && !id.StartsWith("ERR")) break;
            yield return Wait(1f);
        }
        var m = EOSManager.Instance;
        var cur = Puid();
        DuoPlugin.Say($"EOS after {Time.realtimeSinceStartup - t0:F0}s puid={cur}");
        if (m && (string.IsNullOrEmpty(cur) || cur.StartsWith("ERR")))
        {
            var fake = "0002d0e5d0e5d0e5d0e5d0e5d0e50a0" + (char)('1' + (DuoPlugin.Tag[0] - 'A'));
            try { m.userId = Epic.OnlineServices.ProductUserId.FromString(new Epic.OnlineServices.Utf8String(fake)); } catch (Exception ex) { DuoPlugin.Say("fake puid failed: " + ex.Message); }
            DuoPlugin.Say($"test puid now {Puid()}");
        }
        try
        {
            var gom = GameOptionsManager.Instance;
            if (!gom.HasOptions) gom.Initialize();
            if (gom.GameHostOptions == null) gom.LoadOrCreateNormalGameHostOptions();
            if (gom.GameSearchOptions == null) gom.LoadOrCreateNormalGameSearchOptions();
        }
        catch (Exception ex) { DuoPlugin.Say("options init failed: " + ex.Message); }
    }
}

[HarmonyPatch]
public static class DuoPatches
{
    // Save files: UTS already turned "settings.amogus" into "settings.amogus_TOR"; we run last and
    // append _DUO<tag>, seeded once from whatever name we were handed.
    static string Redirect(string name)
    {
        if (!DuoPlugin.Active || string.IsNullOrEmpty(name) || name.Contains("_DUO")) return name;
        var own = name + "_DUO" + DuoPlugin.Tag;
        try
        {
            var dir = Application.persistentDataPath;
            var to = Path.Combine(dir, own);
            var from = Path.Combine(dir, name);
            if (!File.Exists(to) && File.Exists(from)) File.Copy(from, to);
        }
        catch { }
        return own;
    }

    [HarmonyPatch(typeof(AmongUs.Data.Settings.SettingsData), nameof(AmongUs.Data.Settings.SettingsData.FileName), MethodType.Getter)]
    [HarmonyPostfix, HarmonyPriority(Priority.Last)]
    public static void SettingsName(ref string __result) => __result = Redirect(__result);

    [HarmonyPatch(typeof(AmongUs.Data.Player.PlayerData), nameof(AmongUs.Data.Player.PlayerData.FileName), MethodType.Getter)]
    [HarmonyPostfix, HarmonyPriority(Priority.Last)]
    public static void PlayerName(ref string __result) => __result = Redirect(__result);

    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.HandleRpc))]
    [HarmonyPostfix]
    public static void HandleRpc(PlayerControl __instance, [HarmonyArgument(0)] byte callId, [HarmonyArgument(1)] MessageReader reader)
    {
        if (callId != DuoPlugin.CallId || !DuoPlugin.Active) return;
        try { DuoCommands.Handle(reader.ReadString(), __instance ? __instance.PlayerId : (byte)255); }
        catch (Exception e) { DuoPlugin.Say("rpc error " + e); }
    }

}
