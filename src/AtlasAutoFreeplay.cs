// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasAutoFreeplay - nur fuer Autotests: sind Diagnostics.TaskTest UND Diagnostics.ForceMap gesetzt,
// startet Atlas nach dem EOS-Login selbst einen Freeplay (Skeld, die ForceMap baut daraus die Karte).
// Vorher hing das am Nightfall Survey Tool (AutoStartMap); ist das deaktiviert, blieb der Test im
// Hauptmenue stehen (23.09.). Verfahren wie dort: Login abwarten, Popover samt Vorfahren aktivieren,
// FreeplayPopover.PlayMap. Einmal pro Prozess; ohne beide Einstellungen passiert nichts.

using System;
using System.Collections;
using BepInEx.Unity.IL2CPP.Utils;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch(typeof(MainMenuManager), nameof(MainMenuManager.Start))]
internal static class AtlasAutoFreeplay
{
    private static bool _fired;

    internal static void Postfix(MainMenuManager __instance)
    {
        if (_fired) return;
        if (string.IsNullOrWhiteSpace(AtlasPlugin.CfgTaskTest?.Value) || string.IsNullOrWhiteSpace(AtlasPlugin.CfgForceMap?.Value)) return;
        _fired = true;
        __instance.StartCoroutine(Run());
    }

    private static IEnumerator Run()
    {
        AtlasPlugin.Logger.LogInfo("[Atlas/Diag] auto freeplay: waiting for EOS login ...");
        float t0 = Time.time;
        while (true)
        {
            bool ok = false;
            try { ok = EOSManager.Instance != null && EOSManager.Instance.HasFinishedLoginFlow(); } catch { }
            if (ok) break;
            if (Time.time - t0 > 45f) { AtlasPlugin.Logger.LogError("[Atlas/Diag] auto freeplay: EOS login timeout"); yield break; }
            yield return null;
        }
        try
        {
            var popover = Object.FindObjectOfType<FreeplayPopover>(true);
            if (popover == null) { AtlasPlugin.Logger.LogError("[Atlas/Diag] auto freeplay: no FreeplayPopover"); yield break; }
            for (var t = popover.transform; t != null; t = t.parent) if (!t.gameObject.activeSelf) t.gameObject.SetActive(true);
            popover.Show();
            popover.PlayMap(MapNames.Skeld);
            AtlasPlugin.Logger.LogInfo("[Atlas/Diag] auto freeplay: started (Skeld, ForceMap builds the Atlas map)");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Diag] auto freeplay failed: {e}"); }
    }
}
