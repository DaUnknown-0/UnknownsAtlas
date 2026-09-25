// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Plugin-Einstieg des Minimal-PoC. Registriert die Karten in der AtlasRegistry und haengt
// die beiden Replace-in-Place-Hooks an ShipStatus.Awake / ShipStatus.Begin (AtlasBuilder).
//
// Bewusst KEIN Reactor-API-Aufruf: Reactor 2.3.1 enthaelt keine Karten-/ShipStatus-
// Registrierung (Binaerscan der installierten Reactor.dll: Identifier "ShipStatus",
// "RegisterCustomShipStatus", "MapSelection" = 0 Treffer; Kontrollen "Reactor"=43,
// "RegisterCustomRpc"=1). Das Package bleibt als Stack-Nachweis referenziert.

using BepInEx;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using UnityEngine;

namespace UnknownsAtlas;

[BepInPlugin(AtlasPlugin.Id, "UNKNOWN'S ATLAS", AtlasPlugin.VersionString)]
[BepInProcess("Among Us.exe")]
public class AtlasPlugin : BasePlugin
{
    public const string Id = "com.daunknown0.atlas";
    public const string PluginName = "Unknown's Atlas";
    public const string VersionString = "0.3.0.17";
    public static readonly System.Version Version = System.Version.Parse(VersionString);

    public static BepInEx.Logging.ManualLogSource Logger = null!;

    internal static readonly Harmony Harmony = new(Id);

    // BepInEx-Config statt TOR-CustomOptions: der PoC soll ohne TOR-Abhaengigkeit ladbar
    // bleiben (Gate-Frage 3). Option-ID-Block 1720-1739 ist in der ID-Registry reserviert,
    // falls spaeter TOR-CustomOptions noetig werden.
    public static ConfigEntry<bool> CfgEnabled = null!;
    public static ConfigEntry<bool> CfgBuildPocMap = null!;
    public static ConfigEntry<bool> CfgErrorStackTraces = null!;
    public static ConfigEntry<string> CfgForceMap = null!;
    public static ConfigEntry<bool> CfgMapShot = null!;
    public static ConfigEntry<bool> CfgUiShot = null!;
    public static ConfigEntry<string> CfgUiShotClick = null!;
    public static ConfigEntry<bool> CfgLobbyShot = null!;
    public static ConfigEntry<string> CfgTaskTest = null!;
    public static ConfigEntry<bool> CfgViewTestVanilla = null!;

    /// <summary>Die Karte fuer die naechste Skeld-Runde (Auswahl im Freeplay-/Lobby-Menue).</summary>
    internal static AtlasMapDef SelectedMap() => AtlasSelection.Selected();

    public override void Load()
    {
        Logger = Log;

        CfgEnabled = Config.Bind("General", "Enabled", true,
            "Master switch of Unknown's Atlas.");
        CfgBuildPocMap = Config.Bind("PoC", "BuildPocMap", true,
            "Replace the loaded vanilla ship with the selected custom map on round start.");
        CfgForceMap = Config.Bind("Diagnostics", "ForceMap", "",
            "Diagnostics only: always build this map on the Skeld (museum), ignoring the " +
            "in-game map selection. Leave empty for normal play.");
        CfgUiShot = Config.Bind("Diagnostics", "UiShot", false,
            "Diagnostics only: open the Freeplay map menu once in the main menu and take a screenshot.");
        CfgUiShotClick = Config.Bind("Diagnostics", "UiShotClick", "",
            "Diagnostics only: after the UiShot screenshot, press this Atlas map button (museum, wald).");
        CfgLobbyShot = Config.Bind("Diagnostics", "LobbyShot", false,
            "Diagnostics only: host a local lobby from the main menu, open the game settings and photograph " +
            "the map picker (before and after pressing the Carnival button) into AtlasShots.");
        CfgTaskTest = Config.Bind("Diagnostics", "TaskTest", "",
            "Diagnostics only: shortly after the round starts, open this custom minigame (dust, pump), " +
            "let it play itself and write screenshots to AtlasShots.");
        CfgMapShot = Config.Bind("Diagnostics", "MapShot", false,
            "Diagnostics only: F11 renders the whole Atlas map to <game>/AtlasShots/*.png. The automatic " +
            "shots and view spots after the round start only run in autotests (freeplay with ForceMap or TaskTest).");
        CfgViewTestVanilla = Config.Bind("Diagnostics", "ViewTestVanilla", false,
            "Diagnostics only: on an UNMODIFIED map, snap the local player to a test spot and take a screen shot + vision log once per round.");
        CfgErrorStackTraces = Config.Bind("Diagnostics", "ErrorStackTraces", true,
            "Ask Unity for script stack traces on errors. Answers WHERE the NullReferenceExceptions " +
            "after the map wipe come from - Unity logs them without a trace by default.");

        if (CfgErrorStackTraces.Value)
        {
            // Messbefund 25.08.2026, 19:13: 0 NullReferenceExceptions vor dem Bau, 3793 danach,
            // mehrere pro Frame - aber Unity loggt sie ohne Stack, also ohne Verursacher.
            // ScriptOnly kostet nichts, solange nichts wirft, und benennt im Fehlerfall die Quelle.
            Application.SetStackTraceLogType(LogType.Error, StackTraceLogType.ScriptOnly);
            Application.SetStackTraceLogType(LogType.Exception, StackTraceLogType.ScriptOnly);
            Logger.LogInfo("[Atlas] error stack traces enabled (Diagnostics.ErrorStackTraces)");
        }

        Logger.LogInfo($"[Atlas] v{VersionString} loaded ({Id})");

        Logger.LogInfo("[Atlas] Maps: museum (Vesper Museum) - chosen in the Freeplay/Lobby map picker");

        // Register in the Mod Manager (hosted by Forgotten Fixes / UsefulTORStuff), same as this
        // project family's other released mods: via AppDomain, no compile-time reference, so it
        // works whether or not Forgotten Fixes is installed. Before the Enabled gate, so a disabled
        // Atlas still shows up there and can be switched back on.
        try
        {
            var modData = new System.Collections.Generic.Dictionary<string, object>
            {
                { "Guid", Id },
                { "Name", PluginName },
                { "Version", Version },
                { "RepositoryOwner", AtlasUpdater.RepositoryOwner },
                { "RepositoryName", AtlasUpdater.RepositoryName },
                { "ButtonColor", new Color(0.89f, 0.71f, 0.31f) },
                { "Enabled", CfgEnabled },
                { "RuntimeEnabled", CfgEnabled.Value },
            };
            System.AppDomain.CurrentDomain.SetData($"ModManager.RegisteredMod.{Id}", modData);
            Logger.LogInfo($"[Atlas] Registered in Mod Manager registry (runtime={CfgEnabled.Value}).");
        }
        catch (System.Exception ex)
        {
            Logger.LogError($"[Atlas] Failed to register in Mod Manager: {ex}");
        }

        if (!CfgEnabled.Value)
        {
            Logger.LogInfo("[Atlas] Enabled=false - patches NOT applied.");
            return;
        }

        // eigene Minispiele: die Il2Cpp-Klasse muss vor dem ersten AddComponent registriert sein
        try { Il2CppInterop.Runtime.Injection.ClassInjector.RegisterTypeInIl2Cpp<AtlasMinigame>(); }
        catch (System.Exception e) { Logger.LogError($"[Atlas] AtlasMinigame registration failed: {e}"); }

        Harmony.PatchAll(typeof(AtlasPlugin).Assembly);
        Logger.LogInfo("[Atlas] Patches applied (map build, map selection, diagnostics)");
        AtlasMuseumBuilder.PatchTaskNames(Harmony);

        // Self-updater: checks the GitHub releases and offers an in-game update (main menu and
        // Mod Manager), like the family's other mods.
        AddComponent<AtlasUpdater>();
    }
}

// Version line in the top-corner PingTracker readout, folded into the shared "Unknown's
// Collective" line alongside this project family's other mods (see UnknownsCollective.cs).
[HarmonyPatch(typeof(PingTracker), nameof(PingTracker.Update))]
[HarmonyPriority(Priority.Low)]
internal static class AtlasVersionDisplayPatch
{
    private static string? cachedLine;

    public static void Postfix(PingTracker __instance)
    {
        if (__instance == null || __instance.text == null) return;
        string text = __instance.text.text;
        if (string.IsNullOrEmpty(text)) return;

        cachedLine ??= $"<color=#E3B64F>{AtlasPlugin.PluginName}</color> v{VersionDisplay.Format(AtlasPlugin.Version)}";
        UnknownsCollective.Contribute(AtlasPlugin.Id, cachedLine);
        text = UnknownsCollective.Render(__instance.text, text);
        // TMP rebuilds its mesh on every assignment, even with an identical string
        if (!string.Equals(__instance.text.text, text, System.StringComparison.Ordinal))
            __instance.text.text = text;
    }
}
