// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasGallery - das Porträt "The Founder" auf der Staffelei der Galerie (User 01.10.): seine Augen folgen
// dem LOKALEN Spieler. Reiner Grusel, keine Information: jeder sieht nur, dass das Bild ihn selbst ansieht.
// Augenweiss liegt im Prop-Bild (museum_art "staffelei"), die Pupillen sind ein eigenes Sprite
// (task_museum_pupil.png) an AtlasMuseumData.PortraitEyes, knapp vor der Standlinie der Staffelei.

using System;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasGallery
{
    private const string LogPrefix = "[Atlas/Gallery]";
    private const int LayerObjects = 12;
    private const float Follow = 7f, Range = 14f;

    private static bool Museum => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "museum";
    private static readonly SpriteRenderer[] Pupils = new SpriteRenderer[2];
    private static SpriteRenderer _easel;
    private static Vector2 _look;

    public static void Reset()
    {
        Pupils[0] = Pupils[1] = null;
        _easel = null;
        _look = Vector2.zero;
    }

    public static void Build(ShipStatus ship, Transform worldRoot)
    {
        Reset();
        var eyes = AtlasMuseumData.PortraitEyes;
        if (eyes == null || eyes.Length < 2) return;
        var spr = AtlasAssets.TaskSprite("task_museum_pupil.png", AtlasMuseumData.PropPixelsPerMeter, new Vector2(0.5f, 0.5f));
        if (spr == null) return;
        foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
            if (sr != null && sr.name.StartsWith("Prop_staffelei_", StringComparison.Ordinal)) { _easel = sr; break; }
        float z = (_easel != null ? _easel.transform.position.z : AtlasMuseumBuilder.SortZ(AtlasMuseumData.PortraitBaseY)) - 0.0001f;
        var ls = worldRoot.lossyScale;
        for (int i = 0; i < 2; i++)
        {
            var go = new GameObject($"Atlas_Gallery_Pupil_{i}") { layer = LayerObjects };
            go.transform.SetParent(worldRoot, false);
            go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f);       // das Ship ist skaliert
            go.transform.position = new Vector3(eyes[i].x, eyes[i].y, z);
            Pupils[i] = go.AddComponent<SpriteRenderer>();
            Pupils[i].sprite = spr;
            AtlasMuseumBuilder.Mask(Pupils[i]);
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} portrait eyes at {eyes[0].x:F2}/{eyes[0].y:F2}, easel {(_easel != null ? "found" : "missing")}");
    }

    public static void Tick(float dt)
    {
        if (!Museum || Pupils[0] == null) return;
        try
        {
            var eyes = AtlasMuseumData.PortraitEyes;
            var lp = PlayerControl.LocalPlayer;
            Vector2 want = Vector2.zero;
            if (lp != null)
            {
                var head = lp.GetTruePosition() + new Vector2(0f, 0.5f);
                var d = head - (eyes[0] + eyes[1]) / 2f;
                if (d.magnitude < Range) want = d.normalized * Mathf.Clamp01(d.magnitude / 1.5f);
            }
            _look = Vector2.Lerp(_look, want, Mathf.Clamp01(dt * Follow));
            // Pupille innerhalb des Augenweiss: Halbachse minus Pupillenradius (Pupille = 45 % des Weiss)
            float rx = AtlasMuseumData.PortraitEyeRx * 0.55f, ry = AtlasMuseumData.PortraitEyeRy * 0.55f;
            float a = _easel != null ? _easel.color.a : 1f;                   // Durchsicht-Blende mitmachen
            for (int i = 0; i < 2; i++)
            {
                var t = Pupils[i].transform;
                t.position = new Vector3(eyes[i].x + _look.x * rx, eyes[i].y + _look.y * ry, t.position.z);
                Pupils[i].color = new Color(1f, 1f, 1f, a);
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }
}
