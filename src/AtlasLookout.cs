// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasLookout - der Hochsitz der Forest Station (User 25.09.): wer hinaufklettert, sieht weiter (die
// Kamera zoomt heraus, der Sichtradius waechst); runterklettern macht es rueckgaengig.
//
// - Hochklettern ueber den Use-Knopf wie an den Kameras: an der Leiter zeigt er ein eigenes Symbol
//   ("CLIMB", tools/gen_climb_button.py), oben "CLIMB DOWN". Oben steht man still; auch eine
//   Bewegungstaste klettert wieder hinunter.
// - Wer oben steht, bleibt normal killbar: die echte Position bleibt am Fuss der Leiter, nur die Figur
//   wird angehoben (Leichen, Kill- und Meldereichweite wie gewohnt).
// - Ein Meeting, der eigene Tod oder ein geoeffnetes Minispiel holen einen sofort herunter.
// - Sichtstufen (Levels) zum Vergleich; Standard ist "mittel".
//
// Netz: RPC 237 Op 12 [spieler][oben]  jeder -> alle, nur Optik (angehobene Figur bei den anderen).

using System;
using System.Collections.Generic;
using Hazel;
using TMPro;
using Object = UnityEngine.Object;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasLookout
{
    private const string LogPrefix = "[Atlas/Lookout]";
    internal const byte OpLookout = 12;
    // Fuss der Leiter (Sprosse links am Hochsitz, gen_wald.py "hochsitz"), Kabinenboden liegt im Bild
    // 2,2 m * K = 1,2 m hoeher, dazu der Abstand vom Fuss zur Vorderkante
    internal static readonly Vector2 LadderFoot = new(12.95f, 2.3f);
    // Oben steht die Figur IN der Kabine (User 25.09.): etwas kleiner, mittig im Fenster, die Beine hinter
    // der Frontwand ("hochsitz_front" wird davor einsortiert). Werte aus dem Autotest-Bild kalibriert.
    // Verkleinert wird wie beim TOR-Mini das ganze Spieler-Objekt (Hose und Hut schrumpften sonst nicht mit,
    // User 25.09.); Hub und Versatz in Weltmetern.
    private const float Lift = 1.81f, ClimbTime = 0.9f, UpScale = 0.5f, UpShiftX = 0.245f;   // 0,7 x 0,5 = Mini-Groesse (0,35)
    // Sichtstufen: Sichtradius-Faktor, Kamera-Groesse, Kamera-Versatz nach links (oestlich ist nur Wald)
    internal static readonly (string Name, float Vision, float Zoom, float CamX)[] Levels =
    {
        ("light", 1.3f, 3.8f, 0f), ("medium", 1.6f, 4.5f, 0f), ("strong", 2.0f, 5.5f, 0f),
        ("max", 3.0f, 6.5f, 0f), ("max-left", 3.0f, 6.0f, -4f),
    };
    internal static int Level = 4;                              // "max-left": vom User am 25.09. gewaehlt

    private static bool Wald => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "wald";

    private enum St { Down, Climbing, Up, Descending }
    private static St _state;
    private static float _p;                                   // 0 unten .. 1 oben (lokaler Spieler)
    private static float _zoomBase = 3f, _zoomNow = -1f;
    private static readonly HashSet<byte> UpPlayers = new();
    private static readonly Dictionary<byte, float> Lifts = new();
    private static readonly Dictionary<(byte, string), Vector3> BasePos = new();
    // Sichtbare Teile der Figur (Autotest 25.09.: pc.cosmetics hebt nur Hut/Visier, der Koerper blieb unten).
    // Licht, Aufgabenpfeile und Kollision bleiben am Fuss der Leiter.
    private static readonly string[] Parts = { "BodyForms", "Cosmetics", "Names", "Hand" };
    private static readonly Dictionary<byte, float> TorScale = new(), OurScale = new();
    private static bool _frontSorted;

    /// <summary>Faktor fuer den eigenen Sichtradius (AtlasWorld.VisionFactor).</summary>
    public static float VisionFactor => Wald ? Mathf.Lerp(1f, Levels[Level].Vision, Smooth(_p)) : 1f;

    private static float Smooth(float x) => x * x * (3f - 2f * x);

    public static void Reset()
    {
        RestoreZoom();
        foreach (var pc in PlayerControl.AllPlayerControls) if (pc != null) SetLift(pc, 0f);
        _state = St.Down; _p = 0f;
        UpPlayers.Clear(); Lifts.Clear(); BasePos.Clear(); ShadowBase.Clear(); TorScale.Clear(); OurScale.Clear();
        _frontSorted = false;
    }

    // ------------------------------------------------------------------ Netz

    internal static void Receive(PlayerControl from, MessageReader r)
    {
        byte id = r.ReadByte(); bool up = r.ReadBoolean();
        if (from == null || from.PlayerId != id) return;           // jeder meldet nur sich selbst
        if (up) UpPlayers.Add(id); else UpPlayers.Remove(id);
    }

    private static void Announce(bool up)
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        if (up) UpPlayers.Add(lp.PlayerId); else UpPlayers.Remove(lp.PlayerId);
        byte id = lp.PlayerId;
        AtlasWorld.Send(OpLookout, w => { w.Write(id); w.Write(up); });
    }

    // ------------------------------------------------------------------ Takt

    public static void Tick(float dt)
    {
        if (!Wald) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.Data == null) return;

        // Zwangsweise herunter: Tod, Meeting, Rauswurf, Minispiel
        bool forced = lp.Data.IsDead || MeetingHud.Instance != null || ExileController.Instance != null;
        if (_state != St.Down && forced) { Snap(); return; }
        if (_state != St.Down && Minigame.Instance != null && _state != St.Descending) Descend();

        switch (_state)
        {
            case St.Down:
                break;
            case St.Climbing:
                _p = Mathf.MoveTowards(_p, 1f, dt / ClimbTime);
                if (_p >= 1f) { _state = St.Up; AtlasPlugin.Logger.LogInfo($"{LogPrefix} up (vision x{Levels[Level].Vision}, zoom {Levels[Level].Zoom})"); }
                break;
            case St.Up:
                if (WantsDown()) Descend();
                break;
            case St.Descending:
                _p = Mathf.MoveTowards(_p, 0f, dt / ClimbTime);
                if (_p <= 0f) Land();
                break;
        }
        if (_state != St.Down)
        {
            lp.moveable = false;                                   // andere Stellen setzen es gern wieder frei
            ApplyZoom(Mathf.Lerp(_zoomBase, Levels[Level].Zoom, Smooth(_p)));
            ApplyCamOffset(Levels[Level].CamX * Smooth(_p));
        }
        if (!_frontSorted) SortFront();
        UseButtonTick(lp);
        LiftTick(dt, lp);
    }

    private static bool WantsDown()
    {
        if (Input.GetKeyDown(KeyCode.W) || Input.GetKeyDown(KeyCode.A) || Input.GetKeyDown(KeyCode.S) || Input.GetKeyDown(KeyCode.D)
            || Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.RightArrow))
            return true;
        return false;
    }

    internal static void Climb()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || _state != St.Down) return;
        try { lp.NetTransform.RpcSnapTo(LadderFoot); } catch { }
        try { if (lp.MyPhysics != null && lp.MyPhysics.body != null) lp.MyPhysics.body.velocity = Vector2.zero; } catch { }
        if (_zoomNow < 0f && Camera.main != null) _zoomBase = Camera.main.orthographicSize;
        lp.moveable = false;
        _state = St.Climbing;
        Announce(true);
    }

    internal static void Descend()
    {
        if (_state == St.Down || _state == St.Descending) return;
        _state = St.Descending;
    }

    private static void Land()
    {
        var lp = PlayerControl.LocalPlayer;
        _state = St.Down; _p = 0f;
        if (lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null) lp.moveable = true;
        RestoreZoom();
        Announce(false);
    }

    /// <summary>Sofort herunter (Meeting, Tod): ohne Animation.</summary>
    private static void Snap()
    {
        _p = 0f;
        _state = St.Down;
        RestoreZoom();
        Announce(false);
        var lp = PlayerControl.LocalPlayer;
        if (lp != null) SetLift(lp, 0f);
    }

    // ------------------------------------------------------------------ Figur anheben

    private static void LiftTick(float dt, PlayerControl lp)
    {
        foreach (var pc in PlayerControl.AllPlayerControls)
        {
            if (pc == null || pc.Data == null) continue;
            float target;
            if (pc == lp) target = Smooth(_p) * Lift;
            else
            {
                bool up = UpPlayers.Contains(pc.PlayerId) && !pc.Data.IsDead && MeetingHud.Instance == null;
                Lifts.TryGetValue(pc.PlayerId, out var cur);
                target = Mathf.MoveTowards(cur, up ? Lift : 0f, dt * Lift / ClimbTime);
            }
            if (pc.Data.IsDead) target = 0f;
            // TOR setzt die Spielergroesse in jedem FixedUpdate zurueck: solange angehoben, jeden Frame anwenden
            if (target <= 0f && !OurScale.ContainsKey(pc.PlayerId)) { Lifts[pc.PlayerId] = 0f; continue; }
            SetLift(pc, target);
        }
    }

    private static void SetLift(PlayerControl pc, float lift)
    {
        try
        {
            byte id = pc.PlayerId;
            var root = pc.transform;
            float cur = root.localScale.y;
            // Wert von TOR (0,7, Mini kleiner) merken, sobald er nicht mehr unserer ist
            if (!OurScale.TryGetValue(id, out var ours) || Mathf.Abs(cur - ours) > 0.0005f) TorScale[id] = cur;
            float s0 = TorScale.TryGetValue(id, out var t0) ? t0 : cur;
            float k = Mathf.Clamp01(lift / Lift);
            float f = Mathf.Lerp(1f, UpScale, k);
            float sc = s0 * f;
            if (k <= 0f)
            {
                root.localScale = new Vector3(s0, s0, 1f);
                OurScale.Remove(id);
                sc = s0;
            }
            else
            {
                root.localScale = new Vector3(sc, sc, 1f);
                OurScale[id] = sc;
            }
            foreach (var name in Parts)
            {
                var t = pc.transform.Find(name);
                if (t == null) continue;
                var key = (id, name);
                if (!BasePos.TryGetValue(key, out var b)) { b = t.localPosition; BasePos[key] = b; }
                // Hub in Weltmetern, deshalb durch die Spielergroesse teilen
                t.localPosition = new Vector3(b.x + UpShiftX * k / sc, b.y + lift / sc, b.z);
                if (name == "Names") t.localScale = Vector3.one / f;       // Namen bleiben lesbar
            }
            var light = pc.transform.Find("Light(Clone)");
            if (light != null) light.localScale = Vector3.one / f;        // Sicht nicht mitschrumpfen
            Lifts[id] = lift;
        }
        catch { }
    }

    // ------------------------------------------------------------------ Use-Knopf (wie an den Kameras)

    private static bool _useOwned;
    private static Sprite _useIcon;
    private static IntPtr _hookedButton;

    private static void UseButtonTick(PlayerControl lp)
    {
        var ub = HudManager.InstanceExists ? HudManager.Instance.UseButton : null;
        if (ub == null) return;
        string label = null;
        if (_state == St.Down)
        {
            bool can = !lp.Data.IsDead && Minigame.Instance == null && MeetingHud.Instance == null && !lp.inVent && lp.CanMove
                       && Vector2.Distance(lp.GetTruePosition(), LadderFoot) < 1.6f && ub.currentTarget == null;
            if (can) label = "CLIMB";
        }
        else if (_state == St.Up) label = "CLIMB DOWN";
        if (label == null)
        {
            if (_useOwned) { _useOwned = false; try { ub.SetTarget(null); } catch { } }
            return;
        }
        try
        {
            if (_hookedButton != ub.Pointer)
            {
                var pb = ub.GetComponent<PassiveButton>();
                if (pb != null) pb.OnClick.AddListener((Action)OnUse);
                _hookedButton = ub.Pointer;
            }
            if (_useIcon == null)
            {
                // so gross wie das Vanilla-Symbol auf dem Knopf
                float w = ub.graphic != null && ub.graphic.sprite != null ? ub.graphic.sprite.bounds.size.x : 1f;
                _useIcon = AtlasAssets.TaskSprite("task_climb_button.png", 256f / Mathf.Max(0.2f, w), new Vector2(0.5f, 0.5f));
            }
            if (_useIcon != null) ub.graphic.sprite = _useIcon;
            ub.SetEnabled();
            if (ub.buttonLabelText != null) ub.buttonLabelText.text = label;
            _useOwned = true;
            if (Input.GetKeyDown(KeyCode.E)) OnUse();                    // Use-Taste auf der Tastatur
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} use button: {e.Message}"); }
    }

    private static void OnUse()
    {
        if (!_useOwned) return;
        if (_state == St.Down) Climb();
        else if (_state == St.Up) Descend();
    }

    /// <summary>Die Kabinenfront vor die Figur legen: tiefer einsortiert als der Leiterfuss.</summary>
    private static void SortFront()
    {
        var ship = ShipStatus.Instance;
        if (ship == null) return;
        foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
        {
            if (sr == null || !sr.name.StartsWith("Prop_hochsitz_front_", StringComparison.Ordinal)) continue;
            var t = sr.transform;
            t.position = new Vector3(t.position.x, t.position.y, AtlasMuseumBuilder.SortZ(LadderFoot.y - 0.6f));
            _frontSorted = true;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} cabin front sorted in front of the ladder (z {t.position.z:F4})");
            return;
        }
        _frontSorted = true;                                        // Karte ohne Hochsitz-Front: nicht weiter suchen
    }

    private static float _camOffset;

    private static void ApplyCamOffset(float x)
    {
        if (Mathf.Abs(x - _camOffset) < 0.002f) return;
        _camOffset = x;
        try { if (HudManager.InstanceExists && HudManager.Instance.PlayerCam != null) HudManager.Instance.PlayerCam.Offset = new Vector2(x, 0f); }
        catch { }
    }

    // ------------------------------------------------------------------ Kamera

    private static void ApplyZoom(float z)
    {
        if (Mathf.Abs(z - _zoomNow) < 0.002f) return;
        _zoomNow = z;
        try
        {
            if (Camera.main != null) Camera.main.orthographicSize = z;
            ScaleShadow(z);
            // Die Oberflaeche zoomt mit, sonst stimmen die Klickflaechen der Knoepfe nicht (wie TORs Geister-Zoom)
            foreach (var cam in Camera.allCameras)
                if (cam != null && cam.gameObject.name == "UI Camera") cam.orthographicSize = z;
            ResolutionManager.ResolutionChanged.Invoke((float)Screen.width / Screen.height, Screen.width, Screen.height, Screen.fullScreen);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} zoom: {e.Message}"); }
    }

    // Die Sichtschatten zeichnet eine eigene Kamera (ShadowCollab) auf ein Viereck in Bildgroesse; beide
    // muessen mitwachsen, sonst blieb beim Herauszoomen ein dunkler Rahmen (Autotest 25.09.).
    private static readonly Dictionary<IntPtr, (float Ortho, Vector3 Scale)> ShadowBase = new();

    private static void ScaleShadow(float z)
    {
        foreach (var sc in Object.FindObjectsOfType<ShadowCollab>())
        {
            if (sc == null || sc.ShadowCamera == null || sc.ShadowQuad == null) continue;
            if (!ShadowBase.TryGetValue(sc.Pointer, out var b))
            {
                b = (sc.ShadowCamera.orthographicSize, sc.ShadowQuad.transform.localScale);
                ShadowBase[sc.Pointer] = b;
            }
            float k = z / Mathf.Max(0.1f, _zoomBase);
            sc.ShadowCamera.orthographicSize = b.Ortho * k;
            sc.ShadowQuad.transform.localScale = new Vector3(b.Scale.x * k, b.Scale.y * k, b.Scale.z);
        }
    }

    private static void RestoreZoom()
    {
        ApplyCamOffset(0f);
        if (_zoomNow < 0f) return;
        _zoomNow = -1f;
        try
        {
            if (Camera.main != null) Camera.main.orthographicSize = _zoomBase;
            ScaleShadow(_zoomBase);
            foreach (var cam in Camera.allCameras)
                if (cam != null && cam.gameObject.name == "UI Camera") cam.orthographicSize = _zoomBase;
            ResolutionManager.ResolutionChanged.Invoke((float)Screen.width / Screen.height, Screen.width, Screen.height, Screen.fullScreen);
        }
        catch { }
    }

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "lookout...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        switch (what)
        {
            case "lookoutbase":
                snap(LadderFoot);
                break;
            case "lookout1": case "lookout2": case "lookout3": case "lookout4": case "lookout5":
                Level = what[7] - '1';
                if (_state == St.Down) { snap(LadderFoot); Climb(); }
                break;
            case "lookouttree":
            {
                var lp = PlayerControl.LocalPlayer;
                if (lp == null) break;
                void Dump(Transform t, int depth)
                {
                    var r = t.GetComponent<Renderer>();
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} tree {new string(' ', depth * 2)}{t.name} active={t.gameObject.activeSelf} local={t.localPosition} renderer={(r != null ? r.GetType().Name : "-")}");
                    if (depth < 2) for (int i = 0; i < t.childCount; i++) Dump(t.GetChild(i), depth + 1);
                }
                Dump(lp.transform, 0);
                foreach (var sc in Object.FindObjectsOfType<ShadowCollab>())
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} shadow {sc.name}: cam ortho {(sc.ShadowCamera != null ? sc.ShadowCamera.orthographicSize : -1f)} quad scale {(sc.ShadowQuad != null ? sc.ShadowQuad.transform.localScale.ToString() : "-")} parent {(sc.transform.parent != null ? sc.transform.parent.name : "-")}");
                break;
            }
            case "lookoutdown":
                Descend();
                break;
            case "lookoutdummy":
                // eine Testfigur (Freeplay-Dummy) steht oben, man selbst schaut von unten zu
                if (_state != St.Down) Snap();
                foreach (var pc in PlayerControl.AllPlayerControls)
                {
                    if (pc == null || pc == PlayerControl.LocalPlayer || pc.Data == null || pc.Data.IsDead) continue;
                    try { pc.NetTransform.SnapTo(LadderFoot); } catch { }
                    UpPlayers.Add(pc.PlayerId);
                    break;
                }
                snap(LadderFoot + new Vector2(-1.2f, -1.4f));
                break;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag {what}: state {_state}, level {Levels[Level].Name}");
    }
}
