// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasSelection - welche Atlas-Karte (Museum, Wald oder keine) in der naechsten Runde gebaut wird.
//
// Beide Karten sitzen technisch auf der Skeld (Relocate-in-Place). Die Auswahl erscheint deshalb
// als zusaetzliche Karten-Knoepfe NEBEN den Vanilla-Karten:
//   - Freeplay (Uebung): zwei weitere Knoepfe im Freeplay-Kartenmenue, lokal.
//   - Lobby: zwei weitere Knoepfe im Karten-Picker der Spieleinstellungen (nur Host). Der Host
//     schickt die Wahl per RPC 236 an alle (bei Aenderung, bei jedem Beitritt, alle 5 s in der
//     Lobby und unmittelbar vor dem Spielstart - Reliable-Nachrichten kommen in Reihenfolge an,
//     also vor dem Spawn des ShipStatus).
// Ein Vanilla-Kartenknopf setzt die Auswahl zurueck. Spieler ohne Atlas sehen die Skeld.
//
// RPC 236 (ID-Registry): [236][Karten-Index] 0 = keine, 1 = Museum, 2 = Wald. Nur vom Host.

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using InnerNet;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasSelection
{
    private const string LogPrefix = "[Atlas/Select]";
    public const byte RpcId = 236;

    // Reihenfolge = Index im RPC (+1)
    // Button = eingebettetes Logo fuer den Freeplay-Knopf (1000 x 250, tools/gen_buttons.py); null = Schrift
    private static readonly (string Key, string Label, Func<AtlasMapDef> Make, string Button)[] Maps =
    {
        ("museum", "Museum", AtlasMapDef.Museum, "button_museum.png"),
        ("wald", "Forest", AtlasMapDef.Wald, "button_wald.png"),
    };

    private static int _current;   // 0 = keine
    private static AtlasMapDef _cached;
    private static int _cachedIndex = -1;

    public static string CurrentKey => _current == 0 ? null : Maps[_current - 1].Key;

    /// <summary>Gewaehlte Karte oder null. Diagnostics.ForceMap ueberstimmt (Autotests).</summary>
    public static AtlasMapDef Selected()
    {
        int idx = _current;
        var force = AtlasPlugin.CfgForceMap?.Value;
        if (!string.IsNullOrEmpty(force))
            for (int i = 0; i < Maps.Length; i++)
                if (string.Equals(Maps[i].Key, force, StringComparison.OrdinalIgnoreCase)) idx = i + 1;
        if (idx == 0) return null;
        if (_cachedIndex != idx) { _cached = Maps[idx - 1].Make(); _cachedIndex = idx; }
        return _cached;
    }

    private static void Set(int idx, bool broadcast)
    {
        if (idx < 0 || idx > Maps.Length) idx = 0;
        if (_current != idx)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} map -> {(idx == 0 ? "vanilla" : Maps[idx - 1].Key)}");
        _current = idx;
        if (broadcast) Broadcast();
    }

    // ------------------------------------------------------------------ Netz

    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    private static bool Online => AmongUsClient.Instance != null && AmongUsClient.Instance.NetworkMode != NetworkModes.FreePlay;

    private static void Broadcast()
    {
        if (!AmHost || !Online || PlayerControl.LocalPlayer == null) return;
        try
        {
            var w = AmongUsClient.Instance.StartRpcImmediately(PlayerControl.LocalPlayer.NetId, RpcId, SendOption.Reliable, -1);
            w.Write((byte)_current);
            AmongUsClient.Instance.FinishRpcImmediately(w);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} broadcast failed: {e.Message}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.HandleRpc))]
    internal static void PlayerControl_HandleRpc_Postfix(PlayerControl __instance, byte callId, MessageReader reader)
    {
        if (callId != RpcId) return;
        try
        {
            var client = AmongUsClient.Instance;
            if (client == null || __instance == null || __instance.OwnerId != client.HostId) return;
            Set(reader.ReadByte(), broadcast: false);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} rpc read failed: {e.Message}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnGameJoined))]
    internal static void AmongUsClient_OnGameJoined_Postfix()
    {
        // Als Gast gilt nur, was der Host sagt. Der Host behaelt seine letzte Wahl.
        if (!AmHost) Set(0, broadcast: false);
        _resendTimer = 1f;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnPlayerJoined))]
    internal static void AmongUsClient_OnPlayerJoined_Postfix() => _resendTimer = 1f;

    [HarmonyPrefix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.BeginGame))]
    internal static void GameStartManager_BeginGame_Prefix() => Broadcast();

    private static float _resendTimer = 5f;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(LobbyBehaviour), nameof(LobbyBehaviour.Update))]
    internal static void LobbyBehaviour_Update_Postfix()
    {
        if (!AmHost) return;
        _resendTimer -= Time.deltaTime;
        if (_resendTimer > 0f) return;
        _resendTimer = 5f;
        Broadcast();
    }

    // ------------------------------------------------------------ Freeplay-Menue

    [HarmonyPostfix]
    [HarmonyPatch(typeof(FreeplayPopover), nameof(FreeplayPopover.Show))]
    internal static void FreeplayPopover_Show_Postfix(FreeplayPopover __instance)
    {
        try { AddFreeplayButtons(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} freeplay buttons failed: {e}"); }
    }

    private static void AddFreeplayButtons(FreeplayPopover popover)
    {
        var all = popover.GetComponentsInChildren<FreeplayPopoverButton>(true);
        if (all.Length == 0) return;
        foreach (var b in all)
            if (b != null && b.name.StartsWith("Atlas_", StringComparison.Ordinal)) return;   // schon da

        var mapField = AccessTools.Property(typeof(FreeplayPopoverButton), "map");
        FreeplayPopoverButton skeld = null;
        float minX = float.MaxValue, maxX = float.MinValue, minY = float.MaxValue;
        var xs = new List<float>();
        foreach (var b in all)
        {
            var p = b.transform.localPosition;
            xs.Add(p.x);
            minX = Mathf.Min(minX, p.x); maxX = Mathf.Max(maxX, p.x); minY = Mathf.Min(minY, p.y);
            // Vanilla-Knoepfe setzen die Auswahl zurueck
            var pb = b.GetComponent<PassiveButton>();
            if (pb != null) pb.OnClick.AddListener((Action)(() => Set(0, false)));
            var map = mapField != null ? (MapNames)mapField.GetValue(b) : MapNames.Skeld;
            if (map == MapNames.Skeld) skeld = b;
        }
        if (skeld == null) skeld = all[0];
        // Raster aus den Vanilla-Knoepfen ablesen: Spalten = verschiedene x, Zeilen = verschiedene y
        var cols = new List<float>();
        var rows = new List<float>();
        foreach (var b in all)
        {
            var p = b.transform.localPosition;
            if (!cols.Exists(v => Mathf.Abs(v - p.x) < 0.05f)) cols.Add(p.x);
            if (!rows.Exists(v => Mathf.Abs(v - p.y) < 0.05f)) rows.Add(p.y);
        }
        cols.Sort();
        rows.Sort();
        float rowStep = rows.Count > 1 ? rows[1] - rows[0] : 0.8f;
        float rowY = rows[0] - rowStep;

        for (int i = 0; i < Maps.Length; i++)
        {
            int idx = i + 1;
            var clone = Object.Instantiate(skeld.gameObject, skeld.transform.parent);
            clone.name = $"Atlas_{Maps[i].Key}";
            // linke und rechte Spalte (die Mitte gehoert dem einzelnen Fungle-Knopf)
            float x = cols.Count >= 2 ? (i == 0 ? cols[0] : cols[cols.Count - 1]) : cols[0] + (i - 0.5f) * 2.6f;
            clone.transform.localPosition = new Vector3(x, rowY, skeld.transform.localPosition.z);
            // Skeld-Logo abdunkeln, Kartenname als Schrift darueber (keine eigene Grafik)
            if (!ApplyButtonArt(clone, Maps[i].Button))
            {
                Tint(clone, i == 0 ? new Color(0.22f, 0.17f, 0.10f) : new Color(0.09f, 0.20f, 0.12f));
                AddLabel(clone, Maps[i].Label, popover.gameObject);
            }
            var pb = clone.GetComponent<PassiveButton>();
            if (pb != null) pb.OnClick.AddListener((Action)(() => Set(idx, false)));
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} freeplay: {Maps.Length} map buttons added");
    }

    // ------------------------------------------------------------- Lobby-Picker

    [HarmonyPostfix]
    [HarmonyPatch(typeof(GameOptionsMapPicker), nameof(GameOptionsMapPicker.Initialize))]
    internal static void GameOptionsMapPicker_Initialize_Postfix(GameOptionsMapPicker __instance)
    {
        try { AddLobbyButtons(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} lobby buttons failed: {e}"); }
    }

    private static readonly List<PassiveButton> LobbyAtlasButtons = new();

    private static void AddLobbyButtons(GameOptionsMapPicker picker)
    {
        var buttons = picker.GetComponentsInChildren<MapSelectButton>(true);
        if (buttons.Length == 0) return;
        foreach (var b in buttons)
            if (b != null && b.name.StartsWith("Atlas_", StringComparison.Ordinal)) return;

        LobbyAtlasButtons.Clear();
        MapSelectButton first = null, last = null;
        foreach (var b in buttons)
        {
            if (first == null || b.transform.localPosition.x < first.transform.localPosition.x) first = b;
            if (last == null || b.transform.localPosition.x > last.transform.localPosition.x) last = b;
            if (b.Button != null)
                b.Button.OnClick.AddListener((Action)(() => { Set(0, true); MarkLobby(0); }));
        }
        float step = buttons.Length > 1 ? (last.transform.localPosition.x - first.transform.localPosition.x) / (buttons.Length - 1) : 1f;
        var skeldLocal = first.transform.localPosition;
        MapSelectButton skeldButton = first;

        for (int i = 0; i < Maps.Length; i++)
        {
            int idx = i + 1;
            var clone = Object.Instantiate(skeldButton.gameObject, skeldButton.transform.parent);
            clone.name = $"Atlas_{Maps[i].Key}";
            clone.transform.localPosition = last.transform.localPosition + new Vector3(step * (i + 1), 0f, 0f);
            Tint(clone, i == 0 ? new Color(0.45f, 0.36f, 0.2f) : new Color(0.2f, 0.4f, 0.24f));
            AddLabel(clone, Maps[i].Label, picker.gameObject);
            var msb = clone.GetComponent<MapSelectButton>();
            var pb = msb != null ? msb.Button : clone.GetComponent<PassiveButton>();
            if (pb == null) continue;
            pb.OnClick = new UnityEngine.UI.Button.ButtonClickedEvent();
            pb.OnClick.AddListener((Action)(() =>
            {
                picker.SelectMap(0);   // technisch Skeld
                Set(idx, true);
                MarkLobby(idx);
            }));
            LobbyAtlasButtons.Add(pb);
        }
        MarkLobby(_current);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} lobby picker: {Maps.Length} map buttons added (step {step:F2})");
    }

    private static void MarkLobby(int idx)
    {
        for (int i = 0; i < LobbyAtlasButtons.Count; i++)
        {
            var b = LobbyAtlasButtons[i];
            if (b == null) continue;
            try { b.SelectButton(idx == i + 1); } catch { }
        }
    }

    // ------------------------------------------------------------------ Optik

    /// <summary>Ersetzt das Skeld-Logo des geklonten Knopfs durch das eigene Logo, gleiche Weltgroesse.</summary>
    private static bool ApplyButtonArt(GameObject clone, string resource)
    {
        if (string.IsNullOrEmpty(resource)) return false;
        // Aufbau des Vanilla-Knopfs (Log 23.09.): Wurzel = Logo-Sprite (2,10 x 0,47), Kind
        // "Background" = weisser Rahmen als 9-Slice-Sprite. Zum Show-Zeitpunkt ist die Skalierung
        // 0 (Aufklapp-Animation), deshalb alles in LOKALEN Groessen rechnen. Das eigene Bild bringt
        // den Rahmen mit: es ersetzt das Logo in voller Rahmenbreite, der Vanilla-Rahmen geht aus.
        var logo = clone.GetComponent<SpriteRenderer>();
        if (logo == null) return false;
        float width = 0f;
        foreach (var sr in clone.GetComponentsInChildren<SpriteRenderer>(true))
        {
            if (sr == null || sr == logo || sr.sprite == null) continue;
            float w = sr.drawMode != SpriteDrawMode.Simple ? sr.size.x : sr.sprite.bounds.size.x;
            width = Mathf.Max(width, w * Mathf.Abs(sr.transform.localScale.x));
            sr.enabled = false;
        }
        if (width <= 0.01f && logo.sprite != null) width = logo.sprite.bounds.size.x * 1.1f;
        var sprite = AtlasAssets.ButtonSprite(resource, width);
        if (sprite == null) return false;
        logo.sprite = sprite;
        logo.color = Color.white;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} button art {resource}: width {width:F2}");
        return true;
    }

    private static void Tint(GameObject go, Color c)
    {
        foreach (var sr in go.GetComponentsInChildren<SpriteRenderer>(true))
            if (sr != null) sr.color = sr.color * c;
    }

    private static void AddLabel(GameObject button, string text, GameObject fontSource)
    {
        foreach (var t in button.GetComponentsInChildren<TextMeshPro>(true)) t.gameObject.SetActive(false);
        var src = fontSource.GetComponentInChildren<TextMeshPro>(true);
        var go = new GameObject("Atlas_Label") { layer = button.layer };
        go.transform.SetParent(button.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -1f);
        var tmp = go.AddComponent<TextMeshPro>();
        if (src != null) { tmp.font = src.font; tmp.fontSharedMaterial = src.fontSharedMaterial; }
        tmp.text = text;
        tmp.fontSize = 3.2f;
        tmp.alignment = TextAlignmentOptions.Center;
        tmp.color = Color.white;
        tmp.overrideColorTags = true;
        tmp.enableWordWrapping = false;
        tmp.fontStyle = FontStyles.Bold;
        tmp.faceColor = new Color32(255, 255, 255, 255);
        var mr = go.GetComponent<MeshRenderer>();
        var btnRend = button.GetComponentInChildren<SpriteRenderer>(true);
        if (mr != null && btnRend != null) { mr.sortingLayerID = btnRend.sortingLayerID; mr.sortingOrder = btnRend.sortingOrder + 5; }
    }
}

/// <summary>
/// Diagnose (Config Diagnostics.UiShot): oeffnet 8 s nach dem Hauptmenue das Freeplay-Kartenmenue
/// und macht ein Bildschirmfoto nach AtlasShots\ui_*.png - Abnahme der neuen Kartenknoepfe ohne Klick.
/// </summary>
[HarmonyPatch]
internal static class AtlasUiShot
{
    private static float _t = -1f;
    private static int _phase;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(MainMenuManager), "LateUpdate")]
    internal static void MainMenuManager_LateUpdate_Postfix(MainMenuManager __instance)
    {
        if (AtlasPlugin.CfgUiShot is not { Value: true } || _phase >= 2) return;
        if (_t < 0f) _t = Time.time + 8f;
        if (Time.time < _t) return;
        try
        {
            if (_phase == 0)
            {
                __instance.OpenGameModeMenu();
                var pop = Object.FindObjectOfType<FreeplayPopover>(true);
                if (pop == null) { AtlasPlugin.Logger.LogWarning("[Atlas/Select] ui shot: no FreeplayPopover"); _phase = 2; return; }
                pop.gameObject.SetActive(true);
                pop.Show();
                _phase = 1; _t = Time.time + 1.5f;
            }
            else
            {
                string dir = System.IO.Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
                System.IO.Directory.CreateDirectory(dir);
                string file = System.IO.Path.Combine(dir, $"ui_{DateTime.Now:yyyyMMdd_HHmmss}.png");
                ScreenCapture.CaptureScreenshot(file);
                AtlasPlugin.Logger.LogInfo($"[Atlas/Select] ui shot -> {file}");
                _phase = 2;
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Select] ui shot failed: {e}"); _phase = 2; }
    }
}
