// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMapShot - Diagnose-Werkzeug (voruebergehend): rendert die GANZE Museumskarte mit einer
// eigenen Orthokamera in ein PNG unter <Spielordner>\AtlasShots\. Laeuft einmal automatisch
// kurz nach dem Bau und auf F11. So laesst sich jede Aenderung an Boden, Waenden und
// Objektplaetzen in einem Bild abnehmen, statt Raum fuer Raum durchzulaufen.
// Abschalten: Config [Diagnostics] MapShot = false. Die Datei kann spaeter ersatzlos weg.
//
// NUR IM AUTOTEST (Fix 0.3.0.7): bis 0.3.0.6 lief die automatische Aufnahme in JEDER Atlas-Runde,
// weil MapShot standardmaessig an war. Sie setzte den eigenen Spieler kurz nach dem Start per SnapTo
// nacheinander an alle Foto-Stellen und oeffnete am Ende die Kameras (User 23.09.: "ich werde immer
// noch rum teleportiert"). Automatik, F12 und der Vanilla-Vergleich laufen jetzt nur noch im Freeplay
// mit Diagnostics.ForceMap oder TaskTest; bestehende Configs mit MapShot = true sind damit harmlos.
// F11 (Kartenbild rendern, bewegt niemanden) bleibt mit MapShot erlaubt.
//
// Gerendert werden nur Welt-Ebenen (Players 8, Ship 9, Objects 11, ShortObjects 12): keine
// HUD-Kamera, keine Sichtabdunklung - das Bild zeigt die Karte so, wie sie gebaut ist.

using System;
using System.IO;
using System.Linq;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasMapShot
{
    private const string LogPrefix = "[Atlas/Shot]";
    private const float PixelsPerMeter = 40f;
    private const int WorldMask = (1 << 8) | (1 << 9) | (1 << 11) | (1 << 12);

    private static int _autoFrames = -1;

    /// <summary>Autotest-Lauf: Freeplay UND Diagnostics.ForceMap oder TaskTest gesetzt. Nur dann darf
    /// irgendetwas hier den Spieler bewegen oder von selbst aufnehmen.</summary>
    internal static bool AutotestRun =>
        AmongUsClient.Instance != null && AmongUsClient.Instance.NetworkMode == NetworkModes.FreePlay &&
        (!string.IsNullOrWhiteSpace(AtlasPlugin.CfgForceMap?.Value) || !string.IsNullOrWhiteSpace(AtlasPlugin.CfgTaskTest?.Value));

    /// <summary>Vom Builder nach dem Bau gerufen: im Autotest in ~1,5 s ein Bild (Dummies/Spieler stehen dann).</summary>
    internal static void Arm()
    {
        _autoFrames = _viewFrames = _screenFrames = _nextSpotFrames = -1;
        if (AtlasPlugin.CfgMapShot is { Value: true } && AutotestRun) { _autoFrames = 90; _viewFrames = 420; }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        // Vergleichsbasis: auf der unveraenderten Skeld dieselbe Sicht-Messung (Config ViewTestVanilla).
        if (!AtlasMuseumBuilder.Active && AtlasPlugin.CfgViewTestVanilla is { Value: true } && ShipStatus.Instance != null && AutotestRun)
        {
            if (_vanillaFor != ShipStatus.Instance) { _vanillaFor = ShipStatus.Instance; _viewFrames = 420; _vanillaMode = true; }
        }
        else if (!AtlasMuseumBuilder.Active || AtlasPlugin.CfgMapShot is not { Value: true }) return;

        bool shoot = Input.GetKeyDown(KeyCode.F11);
        if (_autoFrames > 0 && --_autoFrames == 0) shoot = true;
        bool view = AutotestRun && Input.GetKeyDown(KeyCode.F12);
        if (_viewFrames > 0 && --_viewFrames == 0) view = true;

        if (shoot)
        {
            try { Capture(); }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} capture failed: {e}"); }
        }
        if (view)
        {
            // Feste Teststelle: Foyer vor der Nordwand. Links und rechts der Rotunden-Oeffnung
            // muss der Rotundenboden hinter der Wand im Schatten liegen.
            _spotIndex = 0;
            SnapToSpot();
        }
        if (_screenFrames > 0 && --_screenFrames == 0)
        {
            try { VisionDiagnostics(); CaptureScreen(); AtlasMuseumBuilder.LogLoopingAudio("at view spot"); }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} view capture failed: {e}"); }
            // Naechste Teststelle (nur Museum); ScreenCapture schreibt erst am Frame-Ende.
            if (!_vanillaMode && ++_spotIndex < ViewSpots.Length) _nextSpotFrames = 30;
        }
        if (_nextSpotFrames > 0 && --_nextSpotFrames == 0) SnapToSpot();
    }

    /// <summary>Letzte Sicherung: nie ausserhalb eines Autotests teleportieren oder Kameras oeffnen.</summary>
    private static bool MayMovePlayer() => AutotestRun;

    private static Vector2[] ViewSpots => AtlasMuseumBuilder.D.ViewSpots;
    private static int _spotIndex;
    private static int _nextSpotFrames = -1;

    internal static void OpenCamerasForDiag() => OpenCameras();

    private static void OpenCameras()
    {
        foreach (var sc in Object.FindObjectsOfType<SystemConsole>())
        {
            if (sc == null || sc.MinigamePrefab == null || sc.MinigamePrefab.TryCast<SurveillanceMinigame>() == null) continue;
            var mg = Object.Instantiate(sc.MinigamePrefab, Camera.main.transform, false);
            mg.transform.localPosition = new Vector3(0f, 0f, -50f);
            mg.Begin(null);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} surveillance minigame opened for the view test");
            return;
        }
        AtlasPlugin.Logger.LogWarning($"{LogPrefix} no surveillance console found");
    }

    private static void SnapToSpot()
    {
        if (!MayMovePlayer()) { _screenFrames = _nextSpotFrames = -1; return; }
        try
        {
            // Offene Minigames (Notfallknopf o.ae.) verdecken sonst die Aufnahme.
            if (Minigame.Instance != null) Minigame.Instance.Close();
            var lp = PlayerControl.LocalPlayer;
            var spot = _vanillaMode ? VanillaSpot : ViewSpots[Math.Min(_spotIndex, ViewSpots.Length - 1)];
            if (lp != null && lp.NetTransform != null) lp.NetTransform.SnapTo(spot);
            if (!_vanillaMode && _spotIndex == ViewSpots.Length - 1) OpenCameras();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} snap failed: {e.Message}"); }
        _screenFrames = 45;
    }

    private static readonly Vector2 VanillaSpot = new(-4.5f, 1.5f);   // Skeld: Cafeteria-Westteil, links die Wand zum Gang
    private static int _screenFrames = -1;

    /// <summary>Fertiger Bildschirm (alle Kameras, Licht, HUD) - genau das, was der Spieler sieht.</summary>
    private static void CaptureScreen()
    {
        string dir = Path.Combine(Paths.GameRootPath, "AtlasShots");
        Directory.CreateDirectory(dir);
        string file = Path.Combine(dir, $"view_{DateTime.Now:yyyyMMdd_HHmmss}.png");
        ScreenCapture.CaptureScreenshot(file);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} screen shot -> {file}");
    }

    private static int _viewFrames = -1;
    private static ShipStatus _vanillaFor;
    private static bool _vanillaMode;

    /// <summary>
    /// Sicht-Diagnose (User 22.09.: "Waende blockieren die Sicht nicht"): welche Kollider findet
    /// eine Umkreissuche mit derselben Maske, die das Licht nutzt (Constants.ShadowMask), rund um
    /// den lokalen Spieler - und welcher Licht-Renderer laeuft.
    /// </summary>
    private static void VisionDiagnostics()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        Vector2 pos = lp.GetTruePosition();
        var hits = Physics2D.OverlapCircleAll(pos, 6f, Constants.ShadowMask);
        var names = new System.Collections.Generic.List<string>();
        foreach (var h in hits)
            if (h != null) names.Add($"{h.gameObject.name}[{h.gameObject.layer}{(h.isTrigger ? ",T" : "")}{(h.enabled ? "" : ",off")}]");
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} vision: mask={Constants.ShadowMask} at ({pos.x:F1},{pos.y:F1}) hits={hits.Length}: {string.Join(", ", names)}");
        var ls = lp.lightSource;
        if (ls != null)
        {
            var rends = ls.GetComponentsInChildren<Renderer>(true);
            var rn = new System.Collections.Generic.List<string>();
            foreach (var r in rends) rn.Add($"{r.gameObject.name}(layer {r.gameObject.layer}, z {r.transform.position.z:F2}, {(r.enabled ? "on" : "off")}, mat {(r.sharedMaterial != null ? r.sharedMaterial.name : "-")})");
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} vision: lightSource '{ls.name}' renderers: {string.Join(", ", rn)}");
        }
        else AtlasPlugin.Logger.LogInfo($"{LogPrefix} vision: local player has no lightSource");

        foreach (var sc in Object.FindObjectsOfType<ShadowCollab>())
        {
            var c = sc.ShadowCamera;
            var q = sc.ShadowQuad;
            AtlasPlugin.Logger.LogInfo(
                $"{LogPrefix} vision: ShadowCollab '{sc.name}' cam={(c != null ? $"{c.name} mask={c.cullingMask} pos=({c.transform.position.x:F1},{c.transform.position.y:F1},{c.transform.position.z:F1}) near={c.nearClipPlane} far={c.farClipPlane} ortho={c.orthographicSize:F2} enabled={c.enabled} rt={(c.targetTexture != null ? c.targetTexture.width + "x" + c.targetTexture.height : "-")}" : "-")} " +
                $"quad={(q != null ? $"{q.name} layer={q.gameObject.layer} z={q.transform.position.z:F2} on={q.enabled} active={q.gameObject.activeInHierarchy} mat={(q.sharedMaterial != null ? q.sharedMaterial.name : "-")}" : "-")}");
        }
        var main = Camera.main;
        if (main != null)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} vision: main cam mask={main.cullingMask} z={main.transform.position.z:F1} near={main.nearClipPlane} far={main.farClipPlane} ortho={main.orthographicSize:F2}");
        // Boeden unter dem Spieler: Layer/Tiefe/Sortierung
        var near = new System.Collections.Generic.List<string>();
        foreach (var sr in Object.FindObjectsOfType<SpriteRenderer>())
        {
            if (sr == null || !sr.enabled || sr.sprite == null) continue;
            var b = sr.bounds;
            if (!b.Contains(new Vector3(pos.x, pos.y, b.center.z)) || b.size.x < 3f) continue;
            near.Add($"{sr.gameObject.name}(layer {sr.gameObject.layer}, z {sr.transform.position.z:F2}, order {sr.sortingOrder}, size {b.size.x:F0}x{b.size.y:F0}, mat {(sr.sharedMaterial != null ? sr.sharedMaterial.name : "-")})");
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} vision: large sprites under player: {string.Join(", ", near)}");
    }

    /// <summary>Bild aus Camera.main MIT Licht/Schatten (was der Spieler sieht, ohne HUD).</summary>
    private static void CaptureView()
    {
        var cam = Camera.main;
        if (cam == null) return;
        int pw = 1600, ph = 900;
        var rt = new RenderTexture(pw, ph, 24, RenderTextureFormat.ARGB32);
        var tex = new Texture2D(pw, ph, TextureFormat.RGB24, false);
        var prevTarget = cam.targetTexture;
        var prevActive = RenderTexture.active;
        try
        {
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, pw, ph), 0, 0);
            tex.Apply(false, false);
        }
        finally
        {
            cam.targetTexture = prevTarget;
            RenderTexture.active = prevActive;
        }
        byte[] png = ImageConversion.EncodeToPNG(tex).ToArray();
        string dir = Path.Combine(Paths.GameRootPath, "AtlasShots");
        Directory.CreateDirectory(dir);
        string file = Path.Combine(dir, $"view_{DateTime.Now:yyyyMMdd_HHmmss}.png");
        File.WriteAllBytes(file, png);
        rt.Release();
        Object.Destroy(rt);
        Object.Destroy(tex);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} view shot -> {file}");
    }

    /// <summary>Park-Diagnose: Gesamtbild waehrend eines Fahrgeschaefts (Zug, Boot, Karussell sichtbar).</summary>
    internal static void DiagCapture()
    {
        try { Capture(); } catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag capture: {e.Message}"); }
    }

    private static void Capture()
    {
        float w = AtlasMuseumBuilder.D.MaxX - AtlasMuseumBuilder.D.MinX;
        float h = AtlasMuseumBuilder.D.MaxY - AtlasMuseumBuilder.D.MinY;
        int pw = Mathf.RoundToInt(w * PixelsPerMeter), ph = Mathf.RoundToInt(h * PixelsPerMeter);

        var go = new GameObject("Atlas_ShotCamera");
        var cam = go.AddComponent<Camera>();
        cam.enabled = false;
        cam.orthographic = true;
        cam.orthographicSize = h * 0.5f;
        cam.aspect = w / h;
        cam.nearClipPlane = 0.1f;
        cam.farClipPlane = 200f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = ShipStatus.Instance != null ? ShipStatus.Instance.CameraColor : Color.black;
        cam.cullingMask = WorldMask;
        go.transform.position = new Vector3(
            (AtlasMuseumBuilder.D.MinX + AtlasMuseumBuilder.D.MaxX) * 0.5f,
            (AtlasMuseumBuilder.D.MinY + AtlasMuseumBuilder.D.MaxY) * 0.5f, -50f);

        var rt = new RenderTexture(pw, ph, 24, RenderTextureFormat.ARGB32);
        var tex = new Texture2D(pw, ph, TextureFormat.RGB24, false);
        var previous = RenderTexture.active;
        try
        {
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, pw, ph), 0, 0);
            tex.Apply(false, false);
        }
        finally
        {
            RenderTexture.active = previous;
            cam.targetTexture = null;
        }

        byte[] png = ImageConversion.EncodeToPNG(tex).ToArray();
        string dir = Path.Combine(Paths.GameRootPath, "AtlasShots");
        Directory.CreateDirectory(dir);
        string file = Path.Combine(dir, $"museum_{DateTime.Now:yyyyMMdd_HHmmss}.png");
        File.WriteAllBytes(file, png);

        Object.Destroy(go);
        rt.Release();
        Object.Destroy(rt);
        Object.Destroy(tex);

        AtlasPlugin.Logger.LogInfo($"{LogPrefix} map shot {pw}x{ph} -> {file}");
    }
}
