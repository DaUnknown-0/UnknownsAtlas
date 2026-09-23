// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasSabotage - Sabotage-Regeln der Atlas-Karten.
//
// Tueren gleichzeitig mit anderen Sabotagen: auf der Skeld sperrt InfectedOverlay.CanUseDoors die
// Tuerknoepfe, solange eine Sabotage laeuft; auf Polus/Airship nicht. Die Atlas-Karten sind technisch
// die Skeld, sollen sich aber wie die grossen Karten verhalten (User 23.09.). Umgekehrt blockieren
// geschlossene Tueren keine Sabotage mehr (DoorsPreventingSabotage).

using HarmonyLib;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasSabotage
{
    [HarmonyPostfix]
    [HarmonyPatch(typeof(InfectedOverlay), nameof(InfectedOverlay.CanUseDoors), MethodType.Getter)]
    internal static void InfectedOverlay_CanUseDoors_Postfix(ref bool __result)
    {
        if (AtlasMuseumBuilder.Active) __result = true;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(InfectedOverlay), nameof(InfectedOverlay.DoorsPreventingSabotage), MethodType.Getter)]
    internal static void InfectedOverlay_DoorsPreventingSabotage_Postfix(ref bool __result)
    {
        if (AtlasMuseumBuilder.Active) __result = false;
    }
}
