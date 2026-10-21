// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasStairs - Treppen zwischen Ebenen einer Karte (User 18.10., Polaris Express als Doppelstockzug).
//
// Eine Karte von oben kann zwei Ebenen nicht uebereinander zeigen. Jede Ebene ist deshalb ein eigener
// Grundriss auf der Karte (z. B. Unterdeck suedlich der Wagen), und eine Treppe ist kein Weg durch die
// Flaeche, sondern ein Paar von Absaetzen: am oberen Absatz bringt der Use-Knopf ("DOWN") einen zum unteren
// und umgekehrt. Der 3D-Nachbau stapelt die Ebenen wieder (Kartenfeld "levels", nur Daten fuer Werkzeuge).
//
// - Daten: AtlasMapDef.Stairs (Kartendatei: "stairs"), je Treppe zwei Absaetze und zwei Knopftexte.
// - Ablauf nur beim eigenen Spieler: kurze Blende (Kopie von HudManager.FullScreen, beruehrt TORs
//   showFlash nicht), in der Mitte RpcSnapTo an den anderen Absatz, Bewegung erst danach wieder frei.
//   Die anderen sehen den Wechsel ueber die normale Positionsuebertragung; ein eigenes RPC braucht es nicht.
// - Wie jede Station in der Welt (AtlasUse.CanReach): nur lebend, nicht im Vent, kein Minispiel, kein Meeting.
//   Ein Meeting oder der eigene Tod waehrend der Blende brechen sie ab (Bewegung zurueck, Blende aus).

using System;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasStairs
{
    private const string LogPrefix = "[Atlas/Stairs]";
    private const float Reach = 1.0f, FadeOut = 0.22f, Hold = 0.08f, FadeIn = 0.3f;
    internal const string Icon = "task_stairs_button.png";

    private static (Vector2 A, Vector2 B, string LabelA, string LabelB)[] _stairs = Array.Empty<(Vector2, Vector2, string, string)>();
    private static float _t0 = -1f;
    private static Vector2 _dest;
    private static bool _moved;
    private static int _uses;
    private static SpriteRenderer _veil;

    public static void Reset()
    {
        if (_veil != null) { try { Object.Destroy(_veil.gameObject); } catch { } }
        _veil = null;
        _stairs = Array.Empty<(Vector2, Vector2, string, string)>();
        _t0 = -1f; _moved = false; _uses = 0;
    }

    public static void Build(AtlasMapDef d)
    {
        _stairs = d?.Stairs ?? Array.Empty<(Vector2, Vector2, string, string)>();
        if (_stairs.Length > 0) AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_stairs.Length} stair(s)");
    }

    public static void Tick(float dt)
    {
        if (_stairs.Length == 0) return;
        var lp = PlayerControl.LocalPlayer;
        if (_t0 >= 0f) { Run(lp); return; }
        if (lp == null) return;
        for (int i = 0; i < _stairs.Length; i++)
        {
            var s = _stairs[i];
            for (int end = 0; end < 2; end++)
            {
                var spot = end == 0 ? s.A : s.B;
                if (!AtlasUse.CanReach(lp, spot, Reach)) continue;
                var dest = end == 0 ? s.B : s.A;
                string label = (end == 0 ? s.LabelA : s.LabelB) ?? "STAIRS";
                AtlasUse.Offer(label, Icon, () => Begin(dest));
                return;
            }
        }
    }

    private static void Begin(Vector2 dest)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || _t0 >= 0f) return;
        _dest = dest; _moved = false; _t0 = Time.time;
        lp.moveable = false;
        try { lp.MyPhysics.body.velocity = Vector2.zero; } catch { }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} using stairs from ({lp.GetTruePosition().x:F1}|{lp.GetTruePosition().y:F1}) to ({dest.x:F1}|{dest.y:F1})");
    }

    private static void Run(PlayerControl lp)
    {
        float el = Time.time - _t0;
        bool abort = lp == null || lp.Data == null || lp.Data.IsDead || MeetingHud.Instance != null || ExileController.Instance != null;
        if (abort) { End(lp, "aborted"); return; }
        float a = el < FadeOut ? el / FadeOut : el < FadeOut + Hold ? 1f : 1f - (el - FadeOut - Hold) / FadeIn;
        Veil(Mathf.Clamp01(a));
        if (!_moved && el >= FadeOut)
        {
            _moved = true;
            try { lp.NetTransform.RpcSnapTo(_dest + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); }
            catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} snap: {e.Message}"); }
        }
        if (el >= FadeOut + Hold + FadeIn) { _uses++; End(lp, "arrived"); }
    }

    private static void End(PlayerControl lp, string how)
    {
        _t0 = -1f;
        Veil(0f);
        // also when he died on the stairs: the ghost has to walk too (audit 21.10.); meeting and exile
        // hand movement back themselves
        if (lp != null && lp.Data != null && MeetingHud.Instance == null && ExileController.Instance == null) lp.moveable = true;
        if (lp != null) AtlasPlugin.Logger.LogInfo($"{LogPrefix} {how} at ({lp.GetTruePosition().x:F1}|{lp.GetTruePosition().y:F1})");
    }

    private static void Veil(float alpha)
    {
        if (_veil == null)
        {
            if (alpha <= 0f) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_StairsVeil";
            _veil = go.GetComponent<SpriteRenderer>();
            if (_veil == null) { Object.Destroy(go); return; }
            _veil.enabled = true;
        }
        bool on = alpha > 0.001f;
        if (_veil.gameObject.activeSelf != on) _veil.gameObject.SetActive(on);
        if (on) _veil.color = new Color(0.02f, 0.02f, 0.03f, alpha);
    }

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "stairs", "stairsback")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        if (_stairs.Length == 0) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: map has no stairs"); return; }
        int idx = 0;
        int colon = what.IndexOf(':');
        if (colon > 0 && int.TryParse(what.Substring(colon + 1), out var n)) idx = Mathf.Clamp(n, 0, _stairs.Length - 1);
        var s = _stairs[idx];
        bool back = what.StartsWith("stairsback", StringComparison.Ordinal);
        snap((back ? s.B : s.A) + new Vector2(0f, AtlasMuseumBuilder.FeetOffset()));
        Begin(back ? s.A : s.B);
    }

    public static string DiagState()
    {
        var lp = PlayerControl.LocalPlayer;
        string at = lp != null ? $"({lp.GetTruePosition().x:F1}|{lp.GetTruePosition().y:F1})" : "-";
        return $"stairs {_stairs.Length}, used {_uses}, {(_t0 >= 0f ? "moving" : "idle")}, player at {at}";
    }
}
