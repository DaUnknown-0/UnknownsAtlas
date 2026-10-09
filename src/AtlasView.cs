// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasView - Kamera des lokalen Spielers herauszoomen und versetzen (Hochsitz, Riesenrad-Gondel).
// Herausgeloest aus AtlasLookout; Technik wie TORs Geister-Zoom:
// - Main Camera + "UI Camera" orthographicSize, dann ResolutionManager.ResolutionChanged (die Oberflaeche
//   zoomt mit, sonst stimmen die Klickflaechen der Knoepfe nicht)
// - die Sichtschatten zeichnet eine eigene Kamera (ShadowCollab) auf ein Viereck in Bildgroesse; beide
//   wachsen mit, sonst bleibt beim Herauszoomen ein dunkler Rahmen (Autotest 25.09.)
// - Versatz ueber HudManager.PlayerCam.Offset

using System;
using System.Collections.Generic;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasView
{
    private const string LogPrefix = "[Atlas/View]";
    private static float _base = 3f, _now = -1f;
    private static Vector2 _offset;
    private static readonly Dictionary<IntPtr, (float Ortho, Vector3 Scale)> ShadowBase = new();

    /// <summary>Kamera-Groesse ohne unseren Zoom (beim ersten Zoom gemerkt).</summary>
    public static float Base => _now < 0f && Camera.main != null ? Camera.main.orthographicSize : _base;

    public static bool Zoomed => _now >= 0f;

    public static void Reset()
    {
        Restore();
        ShadowBase.Clear();
        Shadows.Clear();
    }

    /// <summary>Zoom zwischen der Grundgroesse (t = 0) und z (t = 1).</summary>
    public static void ZoomTo(float z, float t)
    {
        if (_now < 0f && Camera.main != null) _base = Camera.main.orthographicSize;
        Apply(Mathf.Lerp(_base, z, t));
    }

    // Die Riesenrad-Fahrt aendert den Zoom 18 s lang in jedem Frame (Review 09.10.). Frueher suchte jeder
    // dieser Frames alle ShadowCollab der Szene und liess das ganze HUD neu anordnen. Jetzt: Schattenkameras
    // einmal je Zoom-Vorgang suchen, HUD hoechstens zehnmal pro Sekunde und am Ende eines Vorgangs neu setzen.
    private static readonly List<ShadowCollab> Shadows = new();
    private static float _hudAt, _hudZ = -1f;

    private static void Apply(float z)
    {
        if (Mathf.Abs(z - _now) < 0.002f)
        {
            // Zoom steht: eine noch ausstehende HUD-Anpassung nachholen
            if (_now >= 0f && Mathf.Abs(_hudZ - _now) > 0.002f) NotifyHud(_now);
            return;
        }
        _now = z;
        try
        {
            if (Camera.main != null) Camera.main.orthographicSize = z;
            ScaleShadow(z);
            foreach (var cam in Camera.allCameras)
                if (cam != null && cam.gameObject.name == "UI Camera") cam.orthographicSize = z;
            if (Time.unscaledTime >= _hudAt) NotifyHud(z);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} zoom: {e.Message}"); }
    }

    private static void NotifyHud(float z)
    {
        _hudAt = Time.unscaledTime + 0.1f;
        _hudZ = z;
        try { ResolutionManager.ResolutionChanged.Invoke((float)Screen.width / Screen.height, Screen.width, Screen.height, Screen.fullScreen); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} hud: {e.Message}"); }
    }

    private static void ScaleShadow(float z)
    {
        bool stale = Shadows.Count == 0;
        foreach (var s in Shadows) if (s == null) { stale = true; break; }
        if (stale)
        {
            Shadows.Clear();
            foreach (var s in Object.FindObjectsOfType<ShadowCollab>()) if (s != null) Shadows.Add(s);
        }
        foreach (var sc in Shadows)
        {
            if (sc == null || sc.ShadowCamera == null || sc.ShadowQuad == null) continue;
            if (!ShadowBase.TryGetValue(sc.Pointer, out var b))
            {
                b = (sc.ShadowCamera.orthographicSize, sc.ShadowQuad.transform.localScale);
                ShadowBase[sc.Pointer] = b;
            }
            float k = z / Mathf.Max(0.1f, _base);
            sc.ShadowCamera.orthographicSize = b.Ortho * k;
            sc.ShadowQuad.transform.localScale = new Vector3(b.Scale.x * k, b.Scale.y * k, b.Scale.z);
        }
    }

    public static void Offset(Vector2 o)
    {
        if ((o - _offset).sqrMagnitude < 0.000004f) return;
        _offset = o;
        try { if (HudManager.InstanceExists && HudManager.Instance.PlayerCam != null) HudManager.Instance.PlayerCam.Offset = o; }
        catch { }
    }

    public static void Restore()
    {
        Offset(Vector2.zero);
        if (_now < 0f) return;
        _now = -1f;
        _hudZ = -1f;
        try
        {
            if (Camera.main != null) Camera.main.orthographicSize = _base;
            ScaleShadow(_base);
            foreach (var cam in Camera.allCameras)
                if (cam != null && cam.gameObject.name == "UI Camera") cam.orthographicSize = _base;
            ResolutionManager.ResolutionChanged.Invoke((float)Screen.width / Screen.height, Screen.width, Screen.height, Screen.fullScreen);
        }
        catch { }
    }
}
