// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasUse - der Use-Knopf fuer Dinge in der Welt (Hochsitz, Gondel, Achterbahn, Kostuem, Hau den Lukas).
// Herausgeloest aus AtlasLookout (Muster wie an den Kameras): Jede Mechanik bietet in ihrem Tick per
// Offer() an, was der Knopf gerade tun soll; das erste Angebot eines Frames gewinnt. Commit() am Ende des
// Frames setzt Symbol und Beschriftung oder gibt den Knopf an Vanilla zurueck.
// - Klick ueber einen Listener am PassiveButton plus Taste E; kein DoClick-Detour (Dedup-Risiko, siehe
//   Memory "Il2Cpp-Dedup-Detour")
// - ein Angebot in der Naehe einer Station gilt nur, wenn Vanilla gerade kein eigenes Ziel hat
//   (Konsole, Vent, Leiche); ein Angebot "im Fahrgeschaeft" (Aussteigen) immer
// - Symbole sind 256-px-Bilder (tools/gen_climb_button.py und Nachfolger), so gross wie das Vanilla-Symbol

using System;
using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasUse
{
    private const string LogPrefix = "[Atlas/Use]";

    private static string _label, _icon;
    private static bool _enabled;
    private static Action _act;
    private static bool _owned;
    private static IntPtr _hooked;
    private static readonly Dictionary<string, Sprite> Icons = new();

    public static void Reset()
    {
        _label = null; _icon = null; _act = null;
    }

    /// <summary>Knopf fuer diesen Frame anbieten. always = auch wenn Vanilla ein Ziel hat (im Fahrgeschaeft);
    /// enabled = false zeigt den Knopf ausgegraut (z. B. "WAIT 12").</summary>
    public static void Offer(string label, string iconFile, Action onUse, bool always = false, bool enabled = true)
    {
        if (_label != null) return;
        if (!always)
        {
            var ub = HudManager.InstanceExists ? HudManager.Instance.UseButton : null;
            if (ub == null || ub.currentTarget != null) return;
        }
        _label = label; _icon = iconFile; _act = enabled ? onUse : null; _enabled = enabled;
    }

    /// <summary>Gemeinsame Bedingung fuer Stationen in der Welt: lebend, frei beweglich, nichts offen.</summary>
    public static bool CanReach(PlayerControl lp, Vector2 spot, float radius)
    {
        if (lp == null || lp.Data == null || lp.Data.IsDead || lp.inVent || !lp.CanMove) return false;
        if (Minigame.Instance != null || MeetingHud.Instance != null) return false;
        return Vector2.Distance(lp.GetTruePosition(), spot) < radius;
    }

    /// <summary>Ende des Frames: Angebot anwenden oder den Knopf zurueckgeben.</summary>
    public static void Commit()
    {
        var ub = HudManager.InstanceExists ? HudManager.Instance.UseButton : null;
        string label = _label, icon = _icon;
        var act = _act;
        _label = null; _icon = null;
        if (ub == null) return;
        if (label == null)
        {
            _act = null;
            if (_owned) { _owned = false; try { ub.SetTarget(null); } catch { } }
            return;
        }
        try
        {
            if (_hooked != ub.Pointer)
            {
                var pb = ub.GetComponent<PassiveButton>();
                if (pb != null) pb.OnClick.AddListener((Action)OnClick);
                _hooked = ub.Pointer;
            }
            var sprite = Icon(ub, icon);
            if (sprite != null) ub.graphic.sprite = sprite;
            if (_enabled) ub.SetEnabled(); else ub.SetDisabled();
            if (ub.buttonLabelText != null) ub.buttonLabelText.text = label;
            _owned = true;
            _act = act;
            if (_enabled && Input.GetKeyDown(KeyCode.E)) OnClick();                    // Use-Taste auf der Tastatur
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} button: {e.Message}"); }
    }

    private static Sprite Icon(UseButton ub, string file)
    {
        if (string.IsNullOrEmpty(file)) return null;
        if (Icons.TryGetValue(file, out var s) && s != null) return s;
        float w = ub.graphic != null && ub.graphic.sprite != null ? ub.graphic.sprite.bounds.size.x : 1f;
        // nur beim ersten Mal messen: danach liegt schon unser Symbol auf dem Knopf
        if (Icons.Count > 0) foreach (var o in Icons.Values) if (o != null) { w = o.bounds.size.x; break; }
        s = AtlasAssets.TaskSprite(file, 256f / Mathf.Max(0.2f, w), new Vector2(0.5f, 0.5f));
        if (s == null) s = AtlasAssets.TaskSprite("task_climb_button.png", 256f / Mathf.Max(0.2f, w), new Vector2(0.5f, 0.5f));
        Icons[file] = s;
        return s;
    }

    private static void OnClick()
    {
        if (!_owned) return;
        var act = _act;
        _act = null;                                                       // ein Klick, eine Aktion
        try { act?.Invoke(); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} action: {e.Message}"); }
    }
}
