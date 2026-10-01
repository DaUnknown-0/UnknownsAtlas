// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasFigure - Spielerfigur verschoben und verkleinert zeichnen, waehrend die echte Position bleibt
// (Hochsitz, Riesenrad-Gondel, Achterbahn), und den Spieler-Kollider auf allen Clients abschalten.
// Herausgeloest aus AtlasLookout (Technik dort beschrieben, Autotests 25./26.09.):
// - wie der TOR-Mini das ganze Spieler-Objekt skalieren; TOR setzt root.localScale in jedem
//   PlayerControl.FixedUpdate zurueck, deshalb jeden Frame im HudManager.Update danach anwenden und den
//   TOR-Wert merken
// - der Versatz in Weltmetern geht auf die sichtbaren Kinder (BodyForms, Cosmetics, Names, Hand), geteilt
//   durch die Skalierung; Names und Light(Clone) werden gegen-skaliert (Namen lesbar, Sicht unveraendert)

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasFigure
{
    private static readonly string[] Parts = { "BodyForms", "Cosmetics", "Names", "Hand" };
    private static readonly Dictionary<byte, float> TorScale = new(), OurScale = new();
    private static readonly Dictionary<(byte, string), Vector3> BasePos = new();
    private static readonly HashSet<byte> NoCollide = new();

    public static void Reset()
    {
        foreach (var pc in PlayerControl.AllPlayerControls)
            if (pc != null) { Pose(pc, Vector2.zero, 1f); SetCollide(pc, true); }
        TorScale.Clear(); OurScale.Clear(); BasePos.Clear(); NoCollide.Clear();
    }

    /// <summary>true, solange die Figur von uns verschoben oder verkleinert ist.</summary>
    public static bool Posed(byte id) => OurScale.ContainsKey(id);

    /// <summary>Figur um offset (Weltmeter) versetzt und mit factor (1 = normal) skaliert zeichnen;
    /// offset 0 und factor 1 stellt den Ursprung wieder her. lightShare: so viel des Versatzes wandert die
    /// Lichtquelle mit (nur beim lokalen Spieler vorhanden); ohne liegt eine weit versetzte Figur ausserhalb
    /// der eigenen Sicht und wird wie jeder Spieler im Dunkeln ausgeblendet (Riesenrad-Test 01.10.). Weniger
    /// als 1 laesst die Sicht weiter nach unten reichen (User 01.10.: "erhoehe die Sichtweite nach unten").</summary>
    public static void Pose(PlayerControl pc, Vector2 offset, float factor, float lightShare = 0f)
    {
        try
        {
            byte id = pc.PlayerId;
            var root = pc.transform;
            float cur = root.localScale.y;
            // Wert von TOR (0,7, Mini kleiner) merken, sobald er nicht mehr unserer ist
            if (!OurScale.TryGetValue(id, out var ours) || Mathf.Abs(cur - ours) > 0.0005f) TorScale[id] = cur;
            float s0 = TorScale.TryGetValue(id, out var t0) ? t0 : cur;
            bool neutral = offset.sqrMagnitude < 1e-8f && Mathf.Abs(factor - 1f) < 1e-4f;
            if (neutral && !OurScale.ContainsKey(id)) return;
            float sc = neutral ? s0 : s0 * factor;
            root.localScale = new Vector3(sc, sc, 1f);
            if (neutral) OurScale.Remove(id); else OurScale[id] = sc;
            float f = neutral ? 1f : factor;
            foreach (var name in Parts)
            {
                var t = pc.transform.Find(name);
                if (t == null) continue;
                var key = (id, name);
                if (!BasePos.TryGetValue(key, out var b)) { b = t.localPosition; BasePos[key] = b; }
                // Versatz in Weltmetern, deshalb durch die Spielergroesse teilen
                t.localPosition = new Vector3(b.x + offset.x / sc, b.y + offset.y / sc, b.z);
                if (name == "Names") t.localScale = Vector3.one / f;       // Namen bleiben lesbar
            }
            var light = pc.transform.Find("Light(Clone)");
            if (light != null)
            {
                light.localScale = Vector3.one / f;                           // Sicht nicht mitschrumpfen
                var key = (id, "Light(Clone)");
                if (!BasePos.TryGetValue(key, out var lb)) { lb = light.localPosition; BasePos[key] = lb; }
                var lo = !neutral ? offset * lightShare / sc : Vector2.zero;
                light.localPosition = new Vector3(lb.x + lo.x, lb.y + lo.y, lb.z);
            }
        }
        catch { }
    }

    /// <summary>Kollider ab- und wieder anschalten; zurueckgesetzt wird nur, was wir abgeschaltet haben.</summary>
    public static void SetCollide(PlayerControl pc, bool on)
    {
        try
        {
            var col = pc.Collider;
            if (col == null) return;
            byte id = pc.PlayerId;
            if (!on)
            {
                if (col.enabled) { col.enabled = false; NoCollide.Add(id); }
            }
            else if (NoCollide.Remove(id)) col.enabled = true;
        }
        catch { }
    }

    // ------------------------------------------------------------------ Bewegung ohne Steuerung

    /// <summary>Spieler hart an eine Transform-Position setzen (Physik-Koerper mit).</summary>
    public static void SetPos(PlayerControl lp, Vector2 t)
    {
        try
        {
            var tr = lp.transform;
            tr.position = new Vector3(t.x, t.y, tr.position.z);
            var body = lp.MyPhysics != null ? lp.MyPhysics.body : null;
            if (body != null) { body.position = t; body.velocity = Vector2.zero; }
        }
        catch { }
    }

    public static void StopBody(PlayerControl lp)
    {
        try { if (lp.MyPhysics != null && lp.MyPhysics.body != null) lp.MyPhysics.body.velocity = Vector2.zero; } catch { }
    }

    /// <summary>Ein Stueck zum Ziel gehen (Transform-Koordinaten); true, sobald es erreicht ist.</summary>
    public static bool WalkTowards(PlayerControl lp, Vector2 target, float speed, float dt)
    {
        Vector2 cur = lp.transform.position;
        var next = Vector2.MoveTowards(cur, target, speed * dt);
        SetPos(lp, next);
        return (next - target).sqrMagnitude < 0.0004f;
    }

    /// <summary>Zwangsweise aussteigen: Meeting, Rauswurf, eigener Tod.</summary>
    public static bool MustLeave(PlayerControl lp) =>
        lp == null || lp.Data == null || lp.Data.IsDead || MeetingHud.Instance != null || ExileController.Instance != null;

    public static float Smooth(float x) => x * x * (3f - 2f * x);
}
