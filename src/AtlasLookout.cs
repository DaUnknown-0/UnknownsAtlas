// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasLookout - der Hochsitz der Forest Station (User 25.09.): wer hinaufklettert, sieht weiter (die
// Kamera zoomt heraus, der Sichtradius waechst); runterklettern macht es rueckgaengig.
//
// - Hochklettern ueber den Use-Knopf wie an den Kameras: an der Leiter zeigt er ein eigenes Symbol
//   ("CLIMB", tools/gen_climb_button.py), oben "CLIMB DOWN" (auch Taste E). Wer oben runterklettert,
//   geht erst selbst zur Klappe ueber der Leiter.
// - Oben ist eine begehbare Kanzel (User 26.09.: mehrere Spieler standen ineinander; "in alle Richtungen
//   bewegen, auch nach oben, und dann nach oben schauen"). Die echte Position liegt dabei IN der
//   Grundflaeche des Hochsitzes (Deck = gen_wald HS_*), die Figur wird um die Deckhoehe angehoben
//   gezeichnet. Der Kollider ist oben aus (auf allen Clients, wie bei den Airship-Leitern), auf dem Deck
//   haelt die Begrenzung nach der Physik. Wer hochklettert, bekommt den freien Platz naechst der Klappe.
// - Die Kamera schaut in die Richtung, in der man auf dem Deck steht (Nordrand -> Blick nach Norden).
// - Die vier Eckpfosten sind Sichtblocker: Schattenkanten, nur beim Spieler aktiv, der oben steht.
// - Sprites (gen_wald HS_KINDS): Unterbau mit Deck hinter den Figuren, Gelaender und Pfosten davor, das
//   Dach ganz vorn; es blendet aus, solange jemand oben steht.
// - Wer oben steht, bleibt killbar: Kills pruefen die Sichtlinie mit ShipAndObjectsMask, der Hochsitz-
//   Kollider liegt auf ShortObjects.
// - Ein Meeting, der eigene Tod oder ein geoeffnetes Minispiel holen einen herunter.
//
// Netz: RPC 237 Op 12 [spieler][oben]  jeder -> alle (angehobene Figur + Kollider aus bei den anderen).

using System;
using System.Collections.Generic;
using Hazel;
using Object = UnityEngine.Object;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasLookout
{
    private const string LogPrefix = "[Atlas/Lookout]";
    internal const byte OpLookout = 12;
    // Fuss der Leiter (Transform-Position vor der Sprosse links am Hochsitz)
    internal static readonly Vector2 LadderFoot = new(12.95f, 2.3f);
    // Deck in Fuss-Koordinaten (GetTruePosition): Grundflaeche 12,5..14,1 x 2,6..4,2 plus 0,2 m Ueberstand
    // seitlich (gen_wald HS_OVER), abzueglich Gelaender und halber Figurbreite.
    private static readonly Rect Walk = Rect.MinMaxRect(12.52f, 2.78f, 14.08f, 4.08f);
    private static readonly Vector2 HatchFeet = new(12.95f, 2.82f);            // Klappe ueber der Leiter
    // Eckpfosten (gen_wald HS_POST = 0,14 m) in Fuss-Koordinaten
    private static readonly Rect[] Posts =
    {
        Rect.MinMaxRect(12.30f, 2.60f, 12.44f, 2.74f), Rect.MinMaxRect(14.16f, 2.60f, 14.30f, 2.74f),
        Rect.MinMaxRect(12.30f, 4.06f, 12.44f, 4.20f), Rect.MinMaxRect(14.16f, 4.06f, 14.30f, 4.20f),
    };
    private const float DeckHeight = 2.2f, ViewK = 0.55f;                     // gen_wald HS_FLOOR, museum_art.K
    private const float ClimbTime = 0.9f, WalkSpeed = 2.4f, UpScale = 0.5f;  // 0,7 x 0,5 = Mini-Groesse (0,35)
    private const float SpotGap = 0.32f, RoofAlpha = 0.25f;
    // Sichtstufen: Sichtradius-Faktor, Kamera-Groesse, wie weit die Kamera in Blickrichtung schaut
    internal static readonly (string Name, float Vision, float Zoom, float Look)[] Levels =
    {
        ("light", 1.3f, 3.8f, 0f), ("medium", 1.6f, 4.5f, 0f), ("strong", 2.0f, 5.5f, 0f),
        ("max", 3.0f, 6.5f, 0f), ("max-look", 3.0f, 6.0f, 4f),
    };
    internal static int Level = 4;                              // Sicht x3, Zoom 6, 4 m Blick (User 25./26.09.)

    private static bool Wald => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "wald";

    private enum St { Down, Climbing, Up, Descending }
    private static St _state;
    private static float _p;                                   // 0 unten .. 1 oben (lokaler Spieler)
    private static Vector2? _walkTo;                           // Transform-Ziel, zu dem die Figur oben selbst geht
    private static Vector2 _look;                              // aktuelle Blickrichtung (-1..1)
    private static readonly HashSet<byte> UpPlayers = new();
    private static readonly Dictionary<byte, float> Lifts = new();
    private static bool _partsSorted;
    private static SpriteRenderer _roof;
    private static float _roofAlpha = 1f;
    private static GameObject _posts;

    /// <summary>Faktor fuer den eigenen Sichtradius (AtlasWorld.VisionFactor). Der Bonus darf ueber den
    /// normalen Hoechstradius gehen, aber nicht bei Lichtsabotage oder Nebel (User 04.10.): von oben
    /// sieht man in die Dunkelheit und in den Nebel nicht weiter als unten.</summary>
    public static float VisionFactor =>
        Wald && !LightsOut() && AtlasWorld.CurrentWeather != AtlasWorld.Weather.Fog
            ? Mathf.Lerp(1f, Levels[Level].Vision, Smooth(_p)) : 1f;

    private static bool LightsOut() => AtlasWorld.LightsOut();

    private static float Smooth(float x) => x * x * (3f - 2f * x);

    private static float Feet => AtlasMuseumBuilder.FeetOffset();
    // Hub der Figur: Deckhoehe in Bildmetern, abzueglich dessen, was die Verkleinerung die Fuesse schon hebt
    private static float Lift => DeckHeight * ViewK - Feet * (1f - UpScale);
    private static Vector2 ToTransform(Vector2 feet) => feet + new Vector2(0f, Feet);
    private static Rect WalkT => new(Walk.x, Walk.y + Feet, Walk.width, Walk.height);

    public static void Reset()
    {
        // Figur, Kollider und Kamera setzt AtlasWorld.Reset ueber AtlasFigure/AtlasView zurueck
        _state = St.Down; _p = 0f; _walkTo = null; _look = Vector2.zero;
        UpPlayers.Clear(); Lifts.Clear();
        _partsSorted = false; _roof = null; _roofAlpha = 1f; _posts = null;
    }

    // ------------------------------------------------------------------ Netz

    internal static void Receive(PlayerControl from, MessageReader r)
    {
        byte id = r.ReadByte(); bool up = r.ReadBoolean();
        if (from == null || from.PlayerId != id) return;           // jeder meldet nur sich selbst
        if (up) UpPlayers.Add(id); else UpPlayers.Remove(id);
    }

    /// <summary>Steht der Spieler gerade oben auf dem Hochsitz?</summary>
    internal static bool IsUp(byte pid) => UpPlayers.Contains(pid);

    /// <summary>Den eigenen Stand erneut melden (fuer einen Spieler, der ihn noch nicht kennt).</summary>
    internal static void Reannounce()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || !UpPlayers.Contains(lp.PlayerId)) return;
        byte id = lp.PlayerId;
        AtlasWorld.Send(OpLookout, w => { w.Write(id); w.Write(true); });
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
        if (!_partsSorted) SortParts();

        // Zwangsweise herunter: Tod, Meeting, Rauswurf, Minispiel
        bool forced = lp.Data.IsDead || MeetingHud.Instance != null || ExileController.Instance != null;
        if (_state != St.Down && forced) Snap();
        else if (_state != St.Down && Minigame.Instance != null && _state != St.Descending) Descend();

        var footT = LadderFoot;
        var hatchT = ToTransform(HatchFeet);
        switch (_state)
        {
            case St.Climbing:
                // die Leiter hoch bis zur Klappe, dann selbst zum freien Platz
                _p = Mathf.MoveTowards(_p, 1f, dt / ClimbTime);
                AtlasFigure.SetPos(lp, Vector2.Lerp(footT, hatchT, Smooth(_p)));
                if (_p >= 1f)
                {
                    _state = St.Up;
                    _walkTo = FreeSpot(lp);
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} up (vision x{Levels[Level].Vision}, zoom {Levels[Level].Zoom}), spot {_walkTo.Value.x:F2}/{_walkTo.Value.y:F2}");
                }
                break;
            case St.Up:
                if (_walkTo.HasValue && AtlasFigure.WalkTowards(lp, _walkTo.Value, WalkSpeed, dt))
                {
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} arrived at {_walkTo.Value.x:F2}/{_walkTo.Value.y:F2}");
                    _walkTo = null;
                }
                KeepOnDeck(lp);
                break;
            case St.Descending:
                if (_walkTo.HasValue)
                {
                    if (AtlasFigure.WalkTowards(lp, _walkTo.Value, WalkSpeed, dt)) _walkTo = null;         // erst zur Klappe
                    break;
                }
                _p = Mathf.MoveTowards(_p, 0f, dt / ClimbTime);
                AtlasFigure.SetPos(lp, Vector2.Lerp(footT, hatchT, Smooth(_p)));
                if (_p <= 0f) Land();
                break;
        }
        if (_state != St.Down)
        {
            // Nur oben und ohne Zielweg frei beweglich (andere Stellen setzen moveable gern wieder frei)
            bool free = _state == St.Up && !_walkTo.HasValue && Minigame.Instance == null;
            if (lp.moveable != free) lp.moveable = free;
            AtlasView.ZoomTo(Levels[Level].Zoom, Smooth(_p));
            LookTick(lp, dt);
        }
        // Die Eckpfosten blocken die Sicht nicht mehr (User 04.10.: wer oben steht, blendet sie aus
        // wie das Auge einen Fensterrahmen). SetPosts bleibt, falls sie wieder gebraucht werden.
        SetPosts(false);
        RoofTick(lp, dt);
        UseOffer(lp);
        LiftTick(dt, lp);
    }

    internal static void Climb()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || _state != St.Down) return;
        try { lp.NetTransform.RpcSnapTo(LadderFoot); } catch { }
        AtlasFigure.StopBody(lp);
        lp.moveable = false;
        _walkTo = null;
        _state = St.Climbing;
        Announce(true);
    }

    internal static void Descend()
    {
        if (_state == St.Down || _state == St.Descending) return;
        var lp = PlayerControl.LocalPlayer;
        bool fromTop = _state == St.Up;
        _state = St.Descending;
        _walkTo = fromTop ? ToTransform(HatchFeet) : null;
        if (lp != null) { lp.moveable = false; AtlasFigure.StopBody(lp); }
    }

    private static void Land()
    {
        var lp = PlayerControl.LocalPlayer;
        _state = St.Down; _p = 0f; _walkTo = null;
        if (lp != null)
        {
            try { lp.NetTransform.RpcSnapTo(LadderFoot); } catch { }
            AtlasFigure.SetCollide(lp, true);
            if (lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null) lp.moveable = true;
        }
        AtlasView.Restore();
        Announce(false);
    }

    /// <summary>Sofort herunter (Meeting, Tod): ohne Animation. Die Leiche bleibt, wo der Kill war;
    /// lebend landet man am Fuss der Leiter.</summary>
    private static void Snap()
    {
        var lp = PlayerControl.LocalPlayer;
        bool dead = lp == null || lp.Data == null || lp.Data.IsDead;
        _p = 0f; _walkTo = null;
        _state = St.Down;
        AtlasView.Restore();
        Announce(false);
        if (lp == null) return;
        // The ghost comes down as well (audit 04.10.: killed on the deck, it stayed up there with its
        // collider back on); only the body stays where the kill was. Never inside a meeting.
        if (MeetingHud.Instance == null) { try { lp.NetTransform.RpcSnapTo(LadderFoot); } catch { } }
        AtlasFigure.SetCollide(lp, true);
        SetLift(lp, 0f);
        // Beim Klettern, Absteigen oder Gehen zum freien Platz ist die Bewegung gesperrt. Ein Tod in diesem
        // Moment liess den Geist sonst bis zum naechsten Meeting stehen (Review 09.10.).
        if (dead && MeetingHud.Instance == null) lp.moveable = true;
    }

    // ------------------------------------------------------------------ Bewegung oben

    /// <summary>Oben: nach der Physik auf dem Deck halten.</summary>
    private static void KeepOnDeck(PlayerControl lp)
    {
        var r = WalkT;
        Vector2 pos = lp.transform.position;
        var c = new Vector2(Mathf.Clamp(pos.x, r.xMin, r.xMax), Mathf.Clamp(pos.y, r.yMin, r.yMax));
        if ((c - pos).sqrMagnitude < 1e-8f) return;
        try
        {
            lp.transform.position = new Vector3(c.x, c.y, lp.transform.position.z);
            var body = lp.MyPhysics != null ? lp.MyPhysics.body : null;
            if (body != null) body.position = c;
        }
        catch { }
    }

    /// <summary>Freier Platz auf dem Deck (Transform-Koordinaten), so nah wie moeglich an der Klappe.</summary>
    private static Vector2 FreeSpot(PlayerControl lp)
    {
        var taken = new List<Vector2>();
        foreach (var pc in PlayerControl.AllPlayerControls)
            if (pc != null && pc != lp && pc.Data != null && !pc.Data.IsDead && UpPlayers.Contains(pc.PlayerId))
                taken.Add(pc.transform.position);
        var hatch = ToTransform(HatchFeet);
        var r = WalkT;
        Vector2 best = hatch;
        float bestScore = float.MinValue;
        for (float x = r.xMin; x <= r.xMax + 0.001f; x += 0.08f)
        for (float y = r.yMin; y <= r.yMax + 0.001f; y += 0.08f)
        {
            var q = new Vector2(x, y);
            float free = 10f;
            foreach (var o in taken) free = Mathf.Min(free, Vector2.Distance(o, q));
            float score = Mathf.Min(free, SpotGap) * 10f - Vector2.Distance(q, hatch);   // erst Abstand, dann Naehe
            if (score > bestScore) { bestScore = score; best = q; }
        }
        return best;
    }

    /// <summary>Kamera in die Richtung, in der man auf dem Deck steht: Mitte = geradeaus, Rand = hinaus.</summary>
    private static void LookTick(PlayerControl lp, float dt)
    {
        var r = WalkT;
        Vector2 pos = lp.transform.position;
        var d = new Vector2((pos.x - r.center.x) / (r.width / 2f), (pos.y - r.center.y) / (r.height / 2f));
        if (d.sqrMagnitude > 1f) d.Normalize();
        if (_state != St.Up) d = Vector2.zero;
        _look = Vector2.MoveTowards(_look, d, dt * 2.5f);
        AtlasView.Offset(_look * (Levels[Level].Look * Smooth(_p)));
    }

    // ------------------------------------------------------------------ Pfosten und Dach

    /// <summary>Schattenkanten der vier Eckpfosten; nur beim Spieler aktiv, der oben steht.</summary>
    private static void SetPosts(bool on)
    {
        if (_posts == null)
        {
            if (!on) return;
            var ship = ShipStatus.Instance;
            var world = ship != null ? ship.transform.Find("Atlas_Museum") : null;
            if (world == null) return;
            _posts = new GameObject("Atlas_LookoutPosts") { layer = 10 };            // Shadow
            _posts.transform.SetParent(world, false);
            _posts.transform.localPosition = new Vector3(0f, 0f, 8f);               // Wandtiefe (Builder ColliderZ)
            for (int i = 0; i < Posts.Length; i++)
            {
                var r = Posts[i];
                var go = new GameObject($"Post_{i}") { layer = 10 };
                go.transform.SetParent(_posts.transform, false);
                go.AddComponent<EdgeCollider2D>().points = new[]
                {
                    new Vector2(r.xMin, r.yMin), new Vector2(r.xMax, r.yMin), new Vector2(r.xMax, r.yMax),
                    new Vector2(r.xMin, r.yMax), new Vector2(r.xMin, r.yMin),
                };
            }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} corner posts block vision ({Posts.Length})");
        }
        if (_posts.activeSelf != on) _posts.SetActive(on);
    }

    /// <summary>Dach aus, solange jemand oben steht (oder man selbst unten dahinter).</summary>
    private static void RoofTick(PlayerControl lp, float dt)
    {
        if (_roof == null) return;
        bool behind = false;
        try
        {
            var f = lp.GetTruePosition();
            behind = _state == St.Down && f.x > 12.1f && f.x < 14.5f && f.y > 4.25f && f.y < 6.6f;
        }
        catch { }
        // Someone who drops out while up top never announces "down"; without this the roof stayed
        // see-through for the rest of the round and wrongly said that somebody is up there.
        if (UpPlayers.Count > 0)
            UpPlayers.RemoveWhere(id =>
            {
                var pc = GameData.Instance != null ? GameData.Instance.GetPlayerById(id) : null;
                return pc == null || pc.Disconnected || pc.IsDead;
            });
        float target = UpPlayers.Count > 0 || _state != St.Down || behind ? RoofAlpha : 1f;
        if (Mathf.Approximately(_roofAlpha, target)) return;
        _roofAlpha = Mathf.MoveTowards(_roofAlpha, target, dt * 4f);
        var c = _roof.color;
        _roof.color = new Color(c.r, c.g, c.b, _roofAlpha);
    }

    /// <summary>Front (Gelaender, Pfosten) und Dach vor alle Figuren auf dem Deck legen; der Unterbau bleibt
    /// an der Hinterkante der Grundflaeche einsortiert (AtlasMuseumBuilder.PropSortLine).</summary>
    private static void SortParts()
    {
        var ship = ShipStatus.Instance;
        if (ship == null) return;
        foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
        {
            if (sr == null) continue;
            float line;
            if (sr.name.StartsWith("Prop_hochsitz_front_", StringComparison.Ordinal)) line = 2.6f - 0.9f;
            else if (sr.name.StartsWith("Prop_hochsitz_roof_", StringComparison.Ordinal)) { line = 2.6f - 1.0f; _roof = sr; }
            else continue;
            var t = sr.transform;
            t.position = new Vector3(t.position.x, t.position.y, AtlasMuseumBuilder.SortZ(line));
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {sr.name} sorted in front of the deck (z {t.position.z:F4})");
        }
        _partsSorted = true;                                        // Karte ohne Hochsitz: nicht weiter suchen
    }

    // ------------------------------------------------------------------ Figur anheben

    private static void LiftTick(float dt, PlayerControl lp)
    {
        float lift = Lift;
        foreach (var pc in PlayerControl.AllPlayerControls)
        {
            if (pc == null || pc.Data == null) continue;
            // A canoe rider belongs to AtlasFerry, which switches his collider off and poses him every
            // frame; this tick runs after it and switched the collider back on and reset the pose, so
            // the rider hit the shoreline walls on every client (Opus audit 2026-10-02).
            if (AtlasFerry.IsRiding(pc.PlayerId)) continue;
            float target;
            bool up;
            if (pc == lp) { target = Smooth(_p) * lift; up = _state != St.Down; }
            else
            {
                up = UpPlayers.Contains(pc.PlayerId) && !pc.Data.IsDead && MeetingHud.Instance == null;
                Lifts.TryGetValue(pc.PlayerId, out var cur);
                target = Mathf.MoveTowards(cur, up ? lift : 0f, dt * lift / ClimbTime);
            }
            if (pc.Data.IsDead) { target = 0f; up = false; }
            // oben kein Kollider (die echte Position liegt in der Hochsitz-Grundflaeche), unten wieder an
            AtlasFigure.SetCollide(pc, !up);
            // TOR setzt die Spielergroesse in jedem FixedUpdate zurueck: solange angehoben, jeden Frame anwenden
            if (target <= 0f && !AtlasFigure.Posed(pc.PlayerId)) { Lifts[pc.PlayerId] = 0f; continue; }
            SetLift(pc, target);
        }
    }

    /// <summary>Figur um lift (Weltmeter) anheben; oben auf UpScale verkleinert (AtlasFigure).</summary>
    private static void SetLift(PlayerControl pc, float lift)
    {
        float k = Mathf.Clamp01(lift / Mathf.Max(0.01f, Lift));
        AtlasFigure.Pose(pc, new Vector2(0f, lift), k <= 0f ? 1f : Mathf.Lerp(1f, UpScale, k));
        Lifts[pc.PlayerId] = lift;
    }

    // ------------------------------------------------------------------ Use-Knopf (wie an den Kameras)

    private static void UseOffer(PlayerControl lp)
    {
        if (_state == St.Down)
        {
            if (AtlasUse.CanReach(lp, LadderFoot, 1.6f)) AtlasUse.Offer("CLIMB", "task_climb_button.png", Climb);
        }
        else if (_state == St.Up) AtlasUse.Offer("CLIMB DOWN", "task_climb_button.png", Descend, always: true);
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
            // oben zu einem Deckrand gehen (Nord, Sued, West, Ost): Blickrichtung und Begrenzung pruefen
            case "lookoutn": case "lookouts": case "lookoutw": case "lookoute":
            {
                if (_state != St.Up) break;
                var r = WalkT;
                char d = what[7];
                Vector2 lp0 = PlayerControl.LocalPlayer.transform.position;
                // bewusst ueber den Rand hinaus: KeepOnDeck muss begrenzen
                _walkTo = d == 'n' ? new Vector2(r.center.x, r.yMax + 1f) : d == 's' ? new Vector2(r.center.x, r.yMin - 1f)
                        : d == 'w' ? new Vector2(r.xMin - 1f, r.center.y) : new Vector2(r.xMax + 1f, r.center.y);
                _walkTo = new Vector2(Mathf.Clamp(_walkTo.Value.x, r.xMin, r.xMax), Mathf.Clamp(_walkTo.Value.y, r.yMin, r.yMax));
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} walk {d} from {lp0.x:F2}/{lp0.y:F2} to {_walkTo.Value.x:F2}/{_walkTo.Value.y:F2} (deck {r.xMin:F2}..{r.xMax:F2} x {r.yMin:F2}..{r.yMax:F2})");
                break;
            }
            case "lookouttree":
            {
                var lp = PlayerControl.LocalPlayer;
                if (lp == null) break;
                void Dump(Transform t, int depth)
                {
                    var rr = t.GetComponent<Renderer>();
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} tree {new string(' ', depth * 2)}{t.name} active={t.gameObject.activeSelf} local={t.localPosition} renderer={(rr != null ? rr.GetType().Name : "-")}");
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
                // eine Testfigur (Freeplay-Dummy) steht oben an der Klappe, man selbst schaut von unten zu
                if (_state != St.Down) Snap();
                foreach (var pc in PlayerControl.AllPlayerControls)
                {
                    if (pc == null || pc == PlayerControl.LocalPlayer || pc.Data == null || pc.Data.IsDead) continue;
                    UpPlayers.Add(pc.PlayerId);
                    AtlasFigure.SetCollide(pc, false);
                    try { pc.NetTransform.SnapTo(ToTransform(HatchFeet)); } catch { }
                    break;
                }
                snap(LadderFoot + new Vector2(-1.2f, -1.4f));
                break;
        }
        var me = PlayerControl.LocalPlayer;
        string pos = me != null ? $"{me.GetTruePosition().x:F2}/{me.GetTruePosition().y:F2}" : "-";
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag {what}: state {_state}, level {Levels[Level].Name}, feet {pos}, look {_look.x:F2}/{_look.y:F2}");
    }
}
