// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasDoorCamArt - eigene Bilder fuer Tueren und Ueberwachungskameras einer Karte (seit 15.10.).
//
// Beides liegt wie die Vent-Bilder im Konsolen-Atlas der Karte (AtlasMapDef.ConsoleSprites), gleiche
// Groesse und gleicher Anker je Satz:
//   Tueren:  "Door/<Label>"        = zu (Ruhebild)
//            "Door/<Label>/1..n"   = Zwischenbilder, das letzte = offen; das Label ist das der DoorSlot
//            Fehlt der Satz, bleibt die Skeld-Tuer samt ihrer Animation.
//   Kameras: "Camera/<i>"          = Kamera i (Reihenfolge von AtlasMapDef.Cameras), Ruhebild
//            "Camera/<i>/on"       = waehrend jemand die Kameras ansieht (das Spiel ruft SetAnimation(true))
// Die Skeld-Renderer werden abgeschaltet, die eigenen Bilder haengen als Kind am selben Objekt und
// uebernehmen dessen Sortierung. Oeffnen und Schliessen laufen die Bilder in 50-ms-Schritten durch,
// angestossen vom Zustand der Tuer (PlainDoor.Open), der auf jedem Client gleich ist.

using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasDoorCamArt
{
    private const string LogPrefix = "[Atlas/DoorCam]";
    private const float FrameSecs = 0.05f;

    private sealed class DoorEntry
    {
        public OpenableDoor Door;
        public SpriteRenderer Art;
        public Sprite[] Frames;      // [0] zu .. [n] offen
        public bool WasOpen;
        public float Since = -10f;   // Zeitpunkt des letzten Zustandswechsels
    }

    private sealed class CamEntry
    {
        public SurvCamera Cam;
        public SpriteRenderer Art;
        public Sprite Off, On;
    }

    private static readonly List<DoorEntry> Doors = new();
    private static readonly List<CamEntry> Cams = new();

    internal static void Reset()
    {
        Doors.Clear();
        Cams.Clear();
    }

    /// <summary>Vom Builder nach dem Setzen einer Tuer: eigene Bilder, wenn die Karte welche hat.</summary>
    internal static void ApplyDoor(OpenableDoor d, AtlasMuseumLayout.DoorSlot slot)
    {
        var frames = AtlasMuseumBuilder.SpriteSet($"Door/{slot.Label}", d.transform);
        if (frames == null) return;
        SpriteRenderer orig = d.GetComponent<SpriteRenderer>();
        if (orig == null) orig = d.GetComponentInChildren<SpriteRenderer>(true);
        var go = new GameObject("AtlasDoorArt") { layer = d.gameObject.layer };
        go.transform.SetParent(d.transform, false);
        var ls = d.transform.lossyScale;
        go.transform.localScale = new Vector3(1f / Mathf.Max(0.0001f, ls.x), 1f / Mathf.Max(0.0001f, ls.y), 1f);
        var art = go.AddComponent<SpriteRenderer>();
        bool open = IsOpen(d);
        art.sprite = frames[open ? frames.Length - 1 : 0];
        if (orig != null)
        {
            art.sortingLayerID = orig.sortingLayerID;
            art.sortingOrder = orig.sortingOrder;
            art.color = orig.color;
        }
        foreach (var r in d.GetComponentsInChildren<SpriteRenderer>(true))
            if (r != art) r.enabled = false;
        Doors.Add(new DoorEntry { Door = d, Art = art, Frames = frames, WasOpen = open });
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} door {slot.Label}: {frames.Length} frame(s)");
    }

    /// <summary>Vom Builder nach dem Setzen einer Kamera.</summary>
    internal static void ApplyCamera(SurvCamera cam, int index)
    {
        var off = AtlasMuseumBuilder.SpriteFor($"Camera/{index}", cam.transform);
        if (off == null) return;
        var on = AtlasMuseumBuilder.SpriteFor($"Camera/{index}/on", cam.transform) ?? off;
        SpriteRenderer orig = cam.GetComponentInChildren<SpriteRenderer>(true);
        var go = new GameObject("AtlasCameraArt") { layer = cam.gameObject.layer };
        go.transform.SetParent(cam.transform, false);
        var ls = cam.transform.lossyScale;
        go.transform.localScale = new Vector3(1f / Mathf.Max(0.0001f, ls.x), 1f / Mathf.Max(0.0001f, ls.y), 1f);
        var art = go.AddComponent<SpriteRenderer>();
        art.sprite = off;
        if (orig != null)
        {
            art.sortingLayerID = orig.sortingLayerID;
            art.sortingOrder = orig.sortingOrder;
        }
        foreach (var r in cam.GetComponentsInChildren<SpriteRenderer>(true))
            if (r != art) r.enabled = false;
        Cams.Add(new CamEntry { Cam = cam, Art = art, Off = off, On = on });
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} camera {index}: own art{(on != off ? " with tally light" : "")}");
    }

    private static bool IsOpen(OpenableDoor d)
    {
        try { var p = d.TryCast<PlainDoor>(); if (p != null) return p.Open; } catch { }
        return true;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        if (Doors.Count == 0) return;
        float now = Time.time;
        for (int i = 0; i < Doors.Count; i++)
        {
            var e = Doors[i];
            if (e.Door == null || e.Art == null) continue;
            bool open = IsOpen(e.Door);
            if (open != e.WasOpen) { e.WasOpen = open; e.Since = now; }
            int n = e.Frames.Length - 1;
            int k = Mathf.Min(n, (int)((now - e.Since) / FrameSecs));
            var sp = e.Frames[open ? k : n - k];
            if (e.Art.sprite != sp) e.Art.sprite = sp;
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(SurvCamera), nameof(SurvCamera.SetAnimation))]
    internal static void SurvCamera_SetAnimation_Postfix(SurvCamera __instance, bool on)
    {
        for (int i = 0; i < Cams.Count; i++)
        {
            var e = Cams[i];
            if (e.Cam == null || e.Art == null || e.Cam.Pointer != __instance.Pointer) continue;
            // das Spiel schaltet die Skeld-Renderer hier wieder an; unsere bleiben die einzigen
            foreach (var r in e.Cam.GetComponentsInChildren<SpriteRenderer>(true))
                if (r != e.Art && r.enabled) r.enabled = false;
            e.Art.sprite = on ? e.On : e.Off;
        }
    }
}
