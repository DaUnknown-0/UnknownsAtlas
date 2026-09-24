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
// RPC 236 (ID-Registry): [236][Karten-Index] 0 = keine, 1 = Museum, 2 = Wald, 3 = Park. Nur vom Host.

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
    // Icon = rundes Symbol fuer den Lobby-Kartenwaehler (256 x 256, tools/gen_icons.py)
    private static readonly (string Key, string Label, Func<AtlasMapDef> Make, string Button, string Icon)[] Maps =
    {
        ("museum", "Museum", AtlasMapDef.Museum, "button_museum.png", "icon_museum.png"),
        ("wald", "Forest", AtlasMapDef.Wald, "button_wald.png", "icon_wald.png"),
        ("park", "Carnival", AtlasMapDef.Park, "button_park.png", "icon_park.png"),
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
        bool changed = _current != idx;
        if (changed)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} map -> {(idx == 0 ? "vanilla" : Maps[idx - 1].Key)}");
        _current = idx;
        if (broadcast) Broadcast();
        if (changed) RefreshLobbyView();
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
        LobbyVisualTick();
        if (!AmHost) return;
        _resendTimer -= Time.deltaTime;
        if (_resendTimer > 0f) return;
        _resendTimer = 5f;
        Broadcast();
    }

    // ------------------------------------------------------------ Lobby-Ansicht (nicht editieren)

    // Ausserhalb des Editiermodus zeigt die Lobby die Karte an zwei Stellen: das Kartenbanner des
    // GameStartManager und die Einstellungsuebersicht (LobbyViewSettingsPane). Beide lesen die
    // Karte aus den Spieloptionen, und die sind bei einer Atlas-Karte technisch die Skeld
    // (Test 23.09.: "in der Lobby wird die Skeld angezeigt").

    [HarmonyPostfix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.UpdateMapImage))]
    internal static void GameStartManager_UpdateMapImage_Postfix(GameStartManager __instance, MapNames __0)
    {
        if (_current == 0 || __0 != MapNames.Skeld) return;
        try { ShowAtlasBanner(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby banner: {e.Message}"); }
    }

    private static void ShowAtlasBanner(GameStartManager g)
    {
        var r = g != null ? g.MapImage : null;
        if (r == null || r.sprite == null || _current == 0) return;
        if (OwnLogos.Contains(r.sprite)) return;
        var logo = Logo(r.sprite.bounds.size.x);
        if (logo != null) r.sprite = logo;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(LobbyViewSettingsPane), nameof(LobbyViewSettingsPane.DrawNormalTab))]
    internal static void LobbyViewSettingsPane_DrawNormalTab_Postfix(LobbyViewSettingsPane __instance)
    {
        if (_current == 0 || __instance == null) return;
        try
        {
            string skeld = TranslationController.Instance.GetString(StringNames.MapNameSkeld, new Il2CppSystem.Object[0]);
            string name = Maps[_current - 1].Make().DisplayName;
            foreach (var t in __instance.GetComponentsInChildren<TextMeshPro>(true))
                if (t != null && t.text != null && t.text.Contains(skeld)) t.text = t.text.Replace(skeld, name);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby view: {e.Message}"); }
    }

    // Test 23.09.: Banner, Waehlerkopf und Uebersicht zeigten trotz der Postfixe weiter die Skeld.
    // UpdateMapImage und die Kopfanzeige des Waehlers laufen offenbar an den Patches vorbei
    // (kleine Il2Cpp-Methoden werden in den Aufrufer eingebaut). Deshalb gleicht die Lobby den
    // sichtbaren Zustand zweimal pro Sekunde selbst ab, bei allen Spielern.
    private static float _visualNext;
    private static readonly HashSet<Sprite> OwnLogos = new();

    private static Sprite Logo(float width)
    {
        var sp = AtlasAssets.ButtonSprite(Maps[_current - 1].Button, width);
        if (sp != null) OwnLogos.Add(sp);
        return sp;
    }

    // Das Spiel setzt das Kartenbanner im Infofeld jeden Frame neu (Test 23.09.: "Room Settings
    // flackert mit dem Museum"), deshalb laeuft der Banner-Abgleich direkt NACH GameStartManager.Update.
    private static readonly List<SpriteRenderer> SkeldNameRenderers = new();
    private static Sprite _skeldName;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.Update))]
    internal static void GameStartManager_Update_Postfix(GameStartManager __instance)
    {
        if (_current == 0 || __instance == null) return;
        try
        {
            var banner = __instance.MapImage;
            if (banner != null && banner.sprite != null && !OwnLogos.Contains(banner.sprite))
            {
                var logo = Logo(banner.sprite.bounds.size.x);
                if (logo != null) banner.sprite = logo;
            }
            for (int i = SkeldNameRenderers.Count - 1; i >= 0; i--)
            {
                var r = SkeldNameRenderers[i];
                if (r == null) { SkeldNameRenderers.RemoveAt(i); continue; }
                if (r.sprite != null && !OwnLogos.Contains(r.sprite))
                {
                    var logo = Logo(r.sprite.bounds.size.x);
                    if (logo != null) r.sprite = logo;
                }
            }
        }
        catch { }
    }

    /// <summary>
    /// Der Lobby-Bildschirm oder null, OHNE einen zu erzeugen. GameStartManager.Instance ist ein
    /// DestroyableSingleton-Getter und KONSTRUIERT ein leeres Objekt, wenn keins existiert (alle
    /// Felder null). Beim Rundenstart wird der echte Lobby-Bildschirm abgebaut, waehrend
    /// LobbyBehaviour.Update noch einen Moment laeuft; traf LobbyVisualTick dieses Fenster, blieb
    /// ein Phantom-GameStartManager in die Runde stehen, das native ShipStatus.Start warf eine
    /// NullReferenceException, der Atlas-Bau lief nie und die Runde spielte auf der Skeld
    /// (User 23.09., 0.3.0.3/0.3.0.4; im Log immer "GameStartManager=ALIVE (leak)"). Gleiches
    /// Muster wie UTS LobbyScreen.InstanceOrNull.
    /// </summary>
    private static GameStartManager LobbyScreenOrNull()
    {
        try { return DestroyableSingleton<GameStartManager>.InstanceExists ? DestroyableSingleton<GameStartManager>._instance : null; }
        catch { return null; }
    }

    private static void LobbyVisualTick()
    {
        if (Time.time < _visualNext) return;
        _visualNext = Time.time + 0.5f;
        try
        {
            var g = LobbyScreenOrNull();
            var banner = g != null ? g.MapImage : null;
            if (_current > 0)
            {
                if (banner != null && banner.sprite != null && !OwnLogos.Contains(banner.sprite))
                {
                    var logo = Logo(banner.sprite.bounds.size.x);
                    if (logo != null) banner.sprite = logo;
                }
                var picker = Object.FindObjectOfType<GameOptionsMapPicker>();
                if (picker != null && picker.isActiveAndEnabled)
                {
                    var head = picker.MapName;
                    if (head != null && head.sprite != null && !OwnLogos.Contains(head.sprite))
                    {
                        var logo = Logo(head.sprite.bounds.size.x);
                        if (logo != null) head.sprite = logo;
                    }
                    var sel = picker.selectedButton;
                    if (sel != null && sel.Button != null && !sel.name.StartsWith("Atlas_", StringComparison.Ordinal))
                        sel.Button.SelectButton(false);
                    MarkLobby(_current);
                }
                // jedes weitere Bild mit dem Skeld-Schriftzug (Infofeld "Room Settings" u. a.)
                Sprite skeldName = null;
                if (g != null && g.AllMapIcons != null)
                    foreach (var m in g.AllMapIcons) if (m != null && m.Name == MapNames.Skeld) skeldName = m.NameImage;
                if (skeldName != null)
                {
                    void Scan(GameObject root)
                    {
                        if (root == null) return;
                        foreach (var r in root.GetComponentsInChildren<SpriteRenderer>(true))
                            if (r != null && r.sprite == skeldName && !SkeldNameRenderers.Contains(r))
                            {
                                SkeldNameRenderers.Add(r);
                                var logo = Logo(r.sprite.bounds.size.x);
                                if (logo != null) r.sprite = logo;
                            }
                    }
                    Scan(g.gameObject);
                    if (g.LobbyInfoPane != null) Scan(g.LobbyInfoPane.gameObject);
                    if (picker != null) Scan(picker.gameObject);
                }
                var pane = Object.FindObjectOfType<LobbyViewSettingsPane>();
                if (pane != null && pane.isActiveAndEnabled) LobbyViewSettingsPane_DrawNormalTab_Postfix(pane);
            }
            else if (banner != null && banner.sprite != null && OwnLogos.Contains(banner.sprite) && g != null)
            {
                // wieder eine Vanilla-Karte: Originalbanner zurueck
                g.UpdateMapImage((MapNames)GameOptionsManager.Instance.CurrentGameOptions.MapId);
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby visuals: {e.Message}"); _visualNext = Time.time + 5f; }
    }

    /// <summary>Nach einer Kartenwahl (Klick oder RPC des Hosts) die Lobby-Ansicht nachziehen.</summary>
    private static void RefreshLobbyView()
    {
        try
        {
            var g = LobbyScreenOrNull();
            if (g == null) return;
            _visualNext = 0f;                                   // sofort beim naechsten Lobby-Frame abgleichen
            if (_current > 0) ShowAtlasBanner(g);
            else g.UpdateMapImage((MapNames)GameOptionsManager.Instance.CurrentGameOptions.MapId);
            var pane = Object.FindObjectOfType<LobbyViewSettingsPane>();
            if (pane != null && pane.isActiveAndEnabled) pane.RefreshTab();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby refresh: {e.Message}"); }
    }

    // ------------------------------------------------------------ Freeplay-Menue

    // Wie Submerged (MapSelectButtonPatches, 24.09.): VOR dem Vanilla-Show klonen und die Klone in
    // popover.buttons eintragen. Show meldet genau dieses Array per OpenOverlayMenu als Menue-Elemente
    // an; nur diese bekommen Hover (gruener Hintergrund) und Controller-Auswahl. Niedrige Prioritaet,
    // damit der Submerged-Prefix zuerst laeuft und sein Knopf im Raster schon steht.
    [HarmonyPrefix]
    [HarmonyPriority(Priority.Low)]
    [HarmonyPatch(typeof(FreeplayPopover), nameof(FreeplayPopover.Show))]
    internal static void FreeplayPopover_Show_Prefix(FreeplayPopover __instance)
    {
        try { AddFreeplayButtons(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} freeplay buttons failed: {e}"); }
    }

    // Jeder Kartenknopf (Vanilla, Submerged, Atlas) landet hier; die Atlas-Klone tragen map = Skeld
    // und waehlen vorher ihre Atlas-Karte, alle anderen setzen die Auswahl zurueck.
    [HarmonyPrefix]
    [HarmonyPatch(typeof(FreeplayPopover), nameof(FreeplayPopover.OnMapButtonPressed))]
    internal static void FreeplayPopover_OnMapButtonPressed_Prefix(FreeplayPopoverButton button)
    {
        try
        {
            int idx = 0;
            string n = button != null ? button.name : null;
            if (n != null && n.StartsWith("Atlas_", StringComparison.Ordinal))
                for (int i = 0; i < Maps.Length; i++)
                    if (n == $"Atlas_{Maps[i].Key}") { idx = i + 1; break; }
            Set(idx, false);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} freeplay map press: {e.Message}"); }
    }

    private static void AddFreeplayButtons(FreeplayPopover popover)
    {
        var all = popover.GetComponentsInChildren<FreeplayPopoverButton>(true);
        if (all.Length == 0) return;
        foreach (var b in all)
            if (b != null && b.name.StartsWith("Atlas_", StringComparison.Ordinal)) return;   // schon da

        var mapField = AccessTools.Property(typeof(FreeplayPopoverButton), "map");
        FreeplayPopoverButton skeld = null;
        var added = new List<FreeplayPopoverButton>();
        float minX = float.MaxValue, maxX = float.MinValue, minY = float.MaxValue;
        var xs = new List<float>();
        foreach (var b in all)
        {
            var p = b.transform.localPosition;
            xs.Add(p.x);
            minX = Mathf.Min(minX, p.x); maxX = Mathf.Max(maxX, p.x); minY = Mathf.Min(minY, p.y);
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
            var clone = Object.Instantiate(skeld.gameObject, skeld.transform.parent);
            clone.name = $"Atlas_{Maps[i].Key}";
            // Zeile 1: links Museum, rechts Wald. Zeile 2: der Park allein in der Mitte, wie der
            // Fungle-Knopf im Vanilla-Raster (in der Mitte von Zeile 1 ueberlappte er beide, Test 23.09.)
            float x = cols.Count >= 2
                ? (i == 0 ? cols[0] : i == 1 ? cols[cols.Count - 1] : (cols[0] + cols[cols.Count - 1]) / 2f)
                : cols[0] + (i - 1f) * 2.6f;
            float y = i < 2 ? rowY : rowY - rowStep;
            clone.transform.localPosition = new Vector3(x, y, skeld.transform.localPosition.z);
            // Skeld-Logo abdunkeln, Kartenname als Schrift darueber (keine eigene Grafik)
            if (!ApplyButtonArt(clone, Maps[i].Button))
            {
                Tint(clone, i == 0 ? new Color(0.22f, 0.17f, 0.10f) : new Color(0.09f, 0.20f, 0.12f));
                AddLabel(clone, Maps[i].Label, popover.gameObject);
            }
            // Der Klick laeuft ueber OnPressEvent -> FreeplayPopover.OnMapButtonPressed; das Abo
            // haelt nur der Vanilla-Knopf (Instantiate kopiert es nicht, Test 23.09.), also wie
            // Submerged den Delegate uebernehmen. Die Kartenwahl macht der OnMapButtonPressed-Prefix.
            var fpb = clone.GetComponent<FreeplayPopoverButton>();
            if (fpb != null)
            {
                fpb.OnPressEvent = skeld.OnPressEvent;
                added.Add(fpb);
            }
        }
        if (popover.buttons != null && added.Count > 0)
        {
            var list = new List<FreeplayPopoverButton>(popover.buttons);
            list.AddRange(added);
            popover.buttons = list.ToArray();
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} freeplay: {Maps.Length} map buttons added ({popover.buttons?.Length ?? 0} in the menu)");
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

    private static MapIconByName SkeldInfo(GameOptionsMapPicker picker)
    {
        if (picker.AllMapIcons == null) return null;
        foreach (var m in picker.AllMapIcons)
            if (m != null && m.Name == MapNames.Skeld) return m;
        return null;
    }

    private static void AddLobbyButtons(GameOptionsMapPicker picker)
    {
        var buttons = picker.GetComponentsInChildren<MapSelectButton>(true);
        if (buttons.Length == 0) return;
        foreach (var b in buttons)
            if (b != null && b.name.StartsWith("Atlas_", StringComparison.Ordinal)) return;
        var skeldInfo = SkeldInfo(picker);
        if (skeldInfo == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby picker: no Skeld entry"); return; }

        LobbyAtlasButtons.Clear();
        MapSelectButton first = null, last = null;
        foreach (var b in buttons)
        {
            if (first == null || b.transform.localPosition.x < first.transform.localPosition.x) first = b;
            if (last == null || b.transform.localPosition.x > last.transform.localPosition.x) last = b;
            // Vanilla-Knopf: waehlt seine Karte selbst (SelectMap(MapIconByName)), Atlas aus
            if (b.Button != null)
                b.Button.OnClick.AddListener((Action)(() => { Set(0, true); MarkLobby(0); }));
        }
        float step = buttons.Length > 1 ? (last.transform.localPosition.x - first.transform.localPosition.x) / (buttons.Length - 1) : 1f;

        for (int i = 0; i < Maps.Length; i++)
        {
            int idx = i + 1;
            var clone = Object.Instantiate(first.gameObject, first.transform.parent);
            clone.name = $"Atlas_{Maps[i].Key}";
            clone.transform.localPosition = last.transform.localPosition + new Vector3(step * (i + 1), 0f, 0f);
            var msb = clone.GetComponent<MapSelectButton>();
            // eigenes rundes Symbol in derselben Groesse wie das Skeld-Symbol; Kreis, Ring und
            // Haken bleiben die des Vanilla-Knopfs
            if (msb != null && msb.MapIcon != null && msb.MapIcon.sprite != null)
            {
                var icon = AtlasAssets.ButtonSprite(Maps[i].Icon, msb.MapIcon.sprite.bounds.size.x);
                if (icon != null) msb.MapIcon.sprite = icon;
            }
            var pb = msb != null ? msb.Button : clone.GetComponent<PassiveButton>();
            if (pb == null) continue;
            pb.OnClick = new UnityEngine.UI.Button.ButtonClickedEvent();
            pb.OnClick.AddListener((Action)(() =>
            {
                // Technisch die Skeld - ueber denselben Weg wie ein Vanilla-Knopf, damit die
                // Einstellung wirklich uebernommen wird (Test 23.09.: SelectMap(0) liess Polus stehen)
                try { picker.SelectMap(skeldInfo); }
                catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} select skeld failed: {e.Message}"); }
                Set(idx, true);
                MarkLobby(idx);
                ShowAtlasInPicker(picker, idx);
            }));
            LobbyAtlasButtons.Add(pb);
        }
        FitLobbyRow(picker, step);
        MarkLobby(_current);
        if (_current > 0) ShowAtlasInPicker(picker, _current);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} lobby picker: {Maps.Length} map buttons added (step {step:F2})");
    }

    // Mit Submerged stehen 9 Symbole in der Reihe; Forest und Carnival lagen rechts ausserhalb des
    // sichtbaren (und klickbaren) Bereichs (User 24.09.: "nicht alle Maps waehlbar"). Rueckt die
    // ganze Reihe zusammen und verkleinert sie gleichmaessig, bis sie in ButtonClickMask passt.
    private static void FitLobbyRow(GameOptionsMapPicker picker, float step)
    {
        try
        {
            var all = new List<MapSelectButton>(picker.GetComponentsInChildren<MapSelectButton>(true));
            all.RemoveAll(b => b == null);
            if (all.Count < 2 || step <= 0f) return;
            all.Sort((a, b) => a.transform.localPosition.x.CompareTo(b.transform.localPosition.x));
            var parent = all[0].transform.parent;
            var mask = picker.ButtonClickMask;
            if (mask == null || parent == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby picker: no click mask, row not fitted"); return; }
            float left = all[0].transform.localPosition.x;
            float right = parent.InverseTransformPoint(mask.bounds.max).x;
            float needed = (all.Count - 1) * step;
            float avail = right - left - step * 0.5f;     // der letzte Knopf muss ganz hinein
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} lobby picker: {all.Count} buttons, left {left:F2}, mask right {right:F2}, needed {needed:F2}, available {avail:F2}");
            if (avail >= needed) return;
            float s = Mathf.Clamp(avail / needed, 0.55f, 1f);
            for (int i = 0; i < all.Count; i++)
            {
                var t = all[i].transform;
                var p = t.localPosition;
                t.localPosition = new Vector3(left + i * step * s, p.y, p.z);
                t.localScale *= s;
            }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} lobby picker: row fitted, scale {s:F2}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} lobby picker fit: {e.Message}"); }
    }

    /// <summary>Haken nur am Atlas-Knopf, Karten-Logo im Kopf des Waehlers.</summary>
    private static void ShowAtlasInPicker(GameOptionsMapPicker picker, int idx)
    {
        if (idx <= 0) return;
        try
        {
            var sel = picker.selectedButton;
            if (sel != null && sel.Button != null) sel.Button.SelectButton(false);
            var name = picker.MapName;
            if (name != null && name.sprite != null)
            {
                if (!OwnLogos.Contains(name.sprite))
                {
                    var logo = AtlasAssets.ButtonSprite(Maps[idx - 1].Button, name.sprite.bounds.size.x);
                    if (logo != null) { OwnLogos.Add(logo); name.sprite = logo; }
                }
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} picker header: {e.Message}"); }
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
                // Abnahme Menue-Anmeldung: ist der Park-Knopf ein waehlbares Menue-Element? Dann
                // markieren, damit das Foto den Hover-Hintergrund zeigt.
                try
                {
                    var park = GameObject.Find("Atlas_park")?.GetComponent<FreeplayPopoverButton>();
                    var cm = ControllerManager.Instance;
                    bool listed = false;
                    var sel = cm?.CurrentUiState?.SelectableUiElements;
                    if (sel != null && park != null)
                        foreach (var e in sel) if (e != null && e.Pointer == park.Button.Pointer) { listed = true; break; }
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Select] ui shot: menu has {pop.buttons?.Length ?? 0} buttons, park selectable {listed}");
                    if (park != null) cm?.SetCurrentSelected(park.Button);
                }
                catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Select] ui shot select: {e.Message}"); }
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
                // optional: den Atlas-Knopf wie ein Spieler druecken (Abnahme des Freeplay-Starts)
                var key = AtlasPlugin.CfgUiShotClick?.Value;
                if (!string.IsNullOrEmpty(key))
                {
                    var go = GameObject.Find($"Atlas_{key}");
                    var pb = go != null ? go.GetComponent<PassiveButton>() : null;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Select] ui shot: click Atlas_{key} ({(pb != null ? "found" : "missing")})");
                    pb?.OnClick.Invoke();
                }
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Select] ui shot failed: {e}"); _phase = 2; }
    }
}

/// <summary>
/// Diagnose (Config Diagnostics.LobbyShot): hostet vom Hauptmenue eine lokale Lobby, oeffnet die
/// Spieleinstellungen und fotografiert den Kartenwaehler; danach Druck auf den Carnival-Knopf und
/// ein zweites Foto. Abnahme der Knopfreihe mit Submerged (24.09.).
/// </summary>
[HarmonyPatch]
internal static class AtlasLobbyShot
{
    private static int _phase;
    private static float _t = -1f;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(MainMenuManager), "LateUpdate")]
    internal static void MainMenuManager_LateUpdate_Postfix()
    {
        if (AtlasPlugin.CfgLobbyShot is not { Value: true } || _phase != 0) return;
        if (_t < 0f) _t = Time.time + 10f;
        if (Time.time < _t) return;
        _phase = 1;
        try
        {
            var host = Object.FindObjectOfType<HostLocalGameButton>(true);
            if (host == null) { AtlasPlugin.Logger.LogWarning("[Atlas/Select] lobby shot: no HostLocalGameButton"); return; }
            host.NetworkMode = NetworkModes.LocalGame;
            host.OnClick();
            AtlasPlugin.Logger.LogInfo("[Atlas/Select] lobby shot: hosting a local lobby");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Select] lobby shot host failed: {e}"); }
    }

    // HudManager.Update statt LobbyBehaviour.Update: dessen nativer Code ist mit einer zweiten
    // Methode zusammengelegt (il2cpp-Dedup, Pruefung 24.09.), ein Detour traefe beide.
    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_LobbyShot_Postfix()
    {
        if (AtlasPlugin.CfgLobbyShot is not { Value: true } || _phase < 1 || _phase >= 6) return;
        if (LobbyBehaviour.Instance == null) return;
        try
        {
            switch (_phase)
            {
                case 1: _t = Time.time + 6f; _phase = 2; break;
                case 2:
                    if (Time.time < _t) return;
                    var pane = Object.FindObjectOfType<LobbyInfoPane>(true);
                    var edit = pane != null && pane.EditButton != null ? pane.EditButton.GetComponent<PassiveButton>() : null;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Select] lobby shot: edit button {(edit != null ? "found" : "missing")}");
                    edit?.OnClick.Invoke();
                    _t = Time.time + 2f; _phase = 3;
                    break;
                case 3:
                    if (Time.time < _t) return;
                    var menu = GameSettingMenu.Instance;
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Select] lobby shot: settings menu {(menu != null ? "open" : "missing")}");
                    menu?.GameSettingsButton?.OnClick.Invoke();
                    _t = Time.time + 2f; _phase = 4;
                    break;
                case 4:
                    if (Time.time < _t) return;
                    Shot("before");
                    var park = GameObject.Find("Atlas_park")?.GetComponent<MapSelectButton>();
                    AtlasPlugin.Logger.LogInfo($"[Atlas/Select] lobby shot: Atlas_park {(park != null ? $"at local x {park.transform.localPosition.x:F2}, scale {park.transform.localScale.x:F2}" : "missing")}");
                    park?.Button?.OnClick.Invoke();
                    _t = Time.time + 1.5f; _phase = 5;
                    break;
                case 5:
                    if (Time.time < _t) return;
                    Shot("park");
                    AtlasPlugin.Logger.LogInfo("[Atlas/Select] lobby shot done");
                    _phase = 6;
                    break;
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Select] lobby shot failed: {e}"); _phase = 6; }
    }

    private static void Shot(string tag)
    {
        string dir = System.IO.Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
        System.IO.Directory.CreateDirectory(dir);
        string file = System.IO.Path.Combine(dir, $"lobby_{tag}_{DateTime.Now:HHmmss}.png");
        ScreenCapture.CaptureScreenshot(file);
        AtlasPlugin.Logger.LogInfo($"[Atlas/Select] lobby shot {tag} -> {file}");
    }
}
