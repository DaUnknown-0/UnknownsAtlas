// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasParkWorld - Welt-System von Moonlight Carnival (docs/PARK_KONZEPT.md, Schritt 4).
//
// Achse der Karte: Ablenkung und wechselnde Wege. Der Host startet alle 22 bis 38 s ein Fahrgeschaeft
// (RPC 237 Op 10 [Art]); jeder Client spielt denselben Ablauf ab Empfang: 2 s Vorwarnung (Glocke,
// blinkende Lampen), dann das Ereignis. Nie waehrend Meeting, Rauswurf oder kritischer Sabotage.
//   Coaster Run     Schranken an den drei Bahnuebergaengen 6 s zu, der Zug faehrt die Runde
//   Carousel Spin   Karussell dreht 10 s, Seile sperren Nord- und Westoeffnung (Tueren S/O bleiben)
//   Ghost Flash     Wagen faehrt durch den Tunnel, der Blitz fotografiert alle darin; das Foto (Figuren
//                   in der aktuell sichtbaren Farbe) zeigt der Monitor am Nordausgang bis zum naechsten Blitz
//   Log Flume Drop  Boot faehrt den Kanal hinab, am Sturz ist die Ost-Bruecke 4 s nass und gesperrt
//   Turnstile Jam   beide Drehkreuze klemmen 5 s
// Dauerhaft: die Drehkreuze sind Einbahn (West nur nach Norden in den Park, Ost nur nach Sueden), und
// die Geisterbahn ist dunkel (Sichtfaktor). Impostor: "Ride Override" auf der Sabotage-Karte startet
// sofort eine Achterbahnfahrt (Host prueft, 30 s Abklingzeit wie Sturmholz).
//
// Sperren sind Kollider auf der Schiffsebene (9) wie das Sturmholz. Die Einbahn schaltet jeder Client
// fuer SEINEN Spieler: Bewegung ist client-seitig, fremde Positionen kommen uebers Netz und werden
// von den Kollidern nicht beruehrt. Der Kollider eines Drehkreuzes ist an, sobald der eigene Spieler
// auf der Ausgangsseite steht (zurueck geht nicht), und aus auf der Eingangsseite (durch geht).

using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class AtlasParkWorld
{
    private const string LogPrefix = "[Atlas/Park]";
    internal const byte OpParkEvent = 10;
    internal const byte SabRide = 2;
    private const int LayerShip = 9, LayerObjects = 12;
    private const float Announce = 2f;

    internal enum Ev : byte { None = 0, Coaster = 1, Carousel = 2, GhostFlash = 3, Flume = 4, TurnstileJam = 5 }

    internal static bool IsPark => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "park";
    internal static bool EventActive => _ev != Ev.None;

    private sealed class Gate
    {
        public GameObject Blocker;          // Kollider (Schiffsebene)
        public SpriteRenderer Bar;          // Schranke/Seil, sichtbar wenn zu
        public readonly List<SpriteRenderer> Lamps = new();
        public Vector2 Center;
        public bool Closed;
    }

    private static Transform _root;
    private static readonly List<Gate> Crossings = new(), CarouselGates = new(), Turnstiles = new();
    private static readonly List<bool> TurnInward = new();
    private static Gate _bridge;
    private static SpriteRenderer _train, _boat, _ghostCar, _carousel, _flash, _monitor;
    private static readonly List<(SpriteRenderer Body, SpriteRenderer Visor)> MonitorFigures = new();
    private static TextMeshPro _monitorText;

    private static Ev _ev;
    private static float _t0, _nextEvent = -1f;
    private static int _cues;                   // bereits gespielte Geraeusche/Schritte des laufenden Ereignisses

    // ------------------------------------------------------------------ Aufbau

    public static void Reset()
    {
        _root = null; _bridge = null;
        Crossings.Clear(); CarouselGates.Clear(); Turnstiles.Clear(); TurnInward.Clear(); MonitorFigures.Clear();
        _train = _boat = _ghostCar = _carousel = _flash = _monitor = null; _monitorText = null;
        _ev = Ev.None; _nextEvent = -1f; _diagOneWay = 0; _diagCaptureAt = -1f;
    }

    public static void Build(ShipStatus ship, Transform worldRoot)
    {
        Reset();
        var go = new GameObject("Atlas_Park") { layer = LayerObjects };
        go.transform.SetParent(worldRoot, false);
        // Das Ship ist skaliert (1,2): Gegenmassstab wie beim Kartenbau, damit Meter Meter sind
        var ls = worldRoot.lossyScale;
        go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f / ls.z);
        go.transform.position = Vector3.zero;
        _root = go.transform;

        foreach (var (min, max, vertical) in AtlasParkWorldData.Crossings)
            Crossings.Add(MakeGate(min, max, Stripe, vertical, lamps: true, new Color(1f, 1f, 1f)));
        foreach (var (min, max) in AtlasParkWorldData.CarouselGates)
            CarouselGates.Add(MakeGate(min, max, Rope, (max.x - min.x) < (max.y - min.y), lamps: false, new Color(1f, 0.85f, 0.3f)));
        _bridge = MakeGate(AtlasParkWorldData.FlumeBridge.Min, AtlasParkWorldData.FlumeBridge.Max, Rope, false, lamps: true,
            new Color(0.7f, 0.9f, 1f));
        foreach (var (min, max, inward) in AtlasParkWorldData.Turnstiles)
        {
            var g = MakeGate(min, max, Stripe, false, lamps: true, new Color(0.75f, 0.75f, 0.8f));
            Turnstiles.Add(g);
            TurnInward.Add(inward);
        }

        BuildLamps();
        _carousel = Spr("Carousel", Disc, AtlasParkWorldData.CarouselCenter, AtlasParkWorldData.CarouselRadius * 2f, AtlasParkWorldData.CarouselCenter.y - AtlasParkWorldData.CarouselRadius);
        // Fahrzeuge: gezeichnet in tools/gen_park_tasks.py (Draufsicht, 100 px/m), sonst die Pixel-Ersatzformen
        _train = Ride("Train", "task_park_train.png", Cart, AtlasParkWorldData.TrackLoop[0], 3.6f, 0.32f, Color.white);
        _boat = Ride("Boat", "task_park_boat.png", Boat, AtlasParkWorldData.CanalLine[0], 2.2f, 0.45f, Color.white);
        _ghostCar = Ride("GhostCar", "task_park_ghostcar.png", Cart, AtlasParkWorldData.GhostRide[0], 1.3f, 0.5f, new Color(0.55f, 0.35f, 0.75f));
        var ghostC = RoomCenter(SystemTypes.Laboratory);
        _flash = Spr("GhostFlash", Circle, ghostC, 14f, ghostC.y - 7f);
        _flash.color = new Color(1f, 1f, 1f, 0f);

        // Foto-Monitor am Nordausgang: dunkler Rahmen, Beschriftung, Platz fuer 8 Figuren
        var mp = AtlasParkWorldData.GhostMonitor;
        _monitor = Spr("RidePhoto", Px, mp, 2.2f, mp.y - 0.8f, aspect: 0.6f);
        _monitor.color = new Color(0.08f, 0.07f, 0.12f);
        for (int i = 0; i < 8; i++)
        {
            var p = mp + new Vector2(-0.8f + (i % 4) * 0.53f, i < 4 ? 0.22f : -0.36f);
            var body = Spr($"PhotoFigure_{i}", CrewBody, p, 0.42f, mp.y - 0.81f, aspect: 1.15f);
            var visor = Spr($"PhotoVisor_{i}", CrewVisor, p, 0.42f, mp.y - 0.82f, aspect: 1.15f);
            body.gameObject.SetActive(false); visor.gameObject.SetActive(false);
            MonitorFigures.Add((body, visor));
        }
        // keine Schrift: Weltschrift ist nicht sichtmaskiert und laege auch ueber der HUD-Karte (Test 23.09.);
        // die Figuren sind maskiert und nur in Sichtweite zu sehen

        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ready: {Crossings.Count} crossing(s), {CarouselGates.Count} carousel gate(s), " +
                                   $"{Turnstiles.Count} turnstile(s), bridge {(_bridge != null ? "yes" : "no")}");
    }

    private static SpriteRenderer Ride(string name, string file, Sprite fallback, Vector2 at, float width, float aspect, Color fallbackTint)
    {
        var drawn = AtlasAssets.TaskSprite(file, 100f, new Vector2(0.5f, 0.5f));
        SpriteRenderer sr;
        if (drawn != null) sr = Spr(name, drawn, at, drawn.bounds.size.x, at.y, drawn.bounds.size.y / drawn.bounds.size.x);
        else { sr = Spr(name, fallback, at, width, at.y, aspect); sr.color = fallbackTint; }
        sr.gameObject.SetActive(false);
        return sr;
    }

    private static Vector2 RoomCenter(SystemTypes t) =>
        AtlasMuseumBuilder.RoomCenters.TryGetValue(t, out var c) ? c : Vector2.zero;

    private static Gate MakeGate(Vector2 min, Vector2 max, Sprite barSprite, bool vertical, bool lamps, Color tint)
    {
        var g = new Gate { Center = (min + max) / 2f };
        var size = max - min;
        var blocker = new GameObject("Atlas_ParkBlocker") { layer = LayerShip };
        blocker.transform.SetParent(_root, false);
        blocker.transform.position = new Vector3(g.Center.x, g.Center.y, 0f);
        var col = blocker.AddComponent<BoxCollider2D>();
        col.size = size;
        blocker.SetActive(false);
        g.Blocker = blocker;

        // Schranke: ein Balken quer ueber die Oeffnung
        float len = vertical ? size.y : size.x;
        g.Bar = Spr("Bar", barSprite, g.Center, len, g.Center.y - 0.05f, aspect: 0.14f);
        if (vertical) g.Bar.transform.localEulerAngles = new Vector3(0f, 0f, 90f);
        g.Bar.color = tint;
        g.Bar.gameObject.SetActive(false);
        if (lamps)
        {
            var half = vertical ? new Vector2(0f, size.y / 2f + 0.25f) : new Vector2(size.x / 2f + 0.25f, 0f);
            foreach (var p in new[] { g.Center - half, g.Center + half })
            {
                var l = Spr("Lamp", Circle, p, 0.34f, p.y - 0.2f);
                l.color = new Color(0.35f, 0.08f, 0.08f);
                g.Lamps.Add(l);
            }
        }
        return g;
    }

    private static SpriteRenderer Spr(string name, Sprite sprite, Vector2 at, float width, float baseY, float aspect = 1f)
    {
        var go = new GameObject($"Atlas_Park_{name}") { layer = LayerObjects };
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(at.x, at.y, AtlasMuseumBuilder.SortZ(baseY));
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        float w = sprite.bounds.size.x, h = sprite.bounds.size.y;
        go.transform.localScale = new Vector3(width / w, width * aspect / h, 1f);
        AtlasMuseumBuilder.Mask(sr);
        return sr;
    }

    // ------------------------------------------------------------------ Host

    public static void HostTick(bool critical)
    {
        float now = Time.time;
        if (_nextEvent < 0f) _nextEvent = now + 20f;
        if (_ev != Ev.None || now < _nextEvent) return;
        if (critical) { _nextEvent = now + 5f; return; }
        float r = Random.value;
        var kind = r < 0.35f ? Ev.Coaster : r < 0.55f ? Ev.Carousel : r < 0.75f ? Ev.GhostFlash : r < 0.9f ? Ev.Flume : Ev.TurnstileJam;
        HostStart(kind);
    }

    private static void HostStart(Ev kind)
    {
        Apply(kind);
        AtlasWorld.Send(OpParkEvent, w => w.Write((byte)kind));
        _nextEvent = Time.time + Duration(kind) + Random.Range(22f, 38f);
    }

    /// <summary>Impostor-Knopf "Ride Override": sofort eine Achterbahnfahrt. false = abgelehnt.</summary>
    public static bool HostRide()
    {
        if (_ev != Ev.None) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} ride override rejected: {_ev} is running"); return false; }
        HostStart(Ev.Coaster);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ride override: coaster run");
        return true;
    }

    /// <summary>Auf der Strecke zwischen Parkbuero und Bahnhof: dort liegt kein anderer Kartenknopf (am
    /// Bahnhof verdeckte ihn das Reaktor-Symbol, Test 23.09.).</summary>
    public static Vector2 RideButtonSpot() => new(16.8f, 3.2f);   // Bahnhof, abseits des Reaktor-Knopfs

    // ------------------------------------------------------------------ Ablauf (alle Clients)

    private static float Duration(Ev kind) => Announce + kind switch
    {
        Ev.Coaster => 6f, Ev.Carousel => 10f, Ev.GhostFlash => 4f, Ev.Flume => 6f, Ev.TurnstileJam => 5f, _ => 0f,
    };

    public static void Apply(Ev kind)
    {
        if (kind == Ev.None || _root == null) return;
        _ev = kind;
        _t0 = Time.time;
        _cues = 0;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} event {kind}");
    }

    public static void Tick(float dt)
    {
        if (!IsPark || _root == null) return;
        try
        {
            float el = Time.time - _t0;
            bool coaster = false, carousel = false, bridge = false, jam = false;
            if (_ev != Ev.None)
            {
                if (el > Duration(_ev)) { EndEvent(); }
                else
                {
                    bool live = el >= Announce;
                    Cue(0, true, _ev == Ev.GhostFlash ? "creak" : "bell", 0.45f, EventSpot(_ev));
                    switch (_ev)
                    {
                        case Ev.Coaster:
                            coaster = live;
                            Cue(1, live, "rush", 0.55f, EventSpot(_ev));
                            Move(_train, AtlasParkWorldData.TrackLoop, live ? (el - Announce) / 6f : -1f);
                            break;
                        case Ev.Carousel:
                            carousel = live;
                            Cue(1, live, "clock", 0.4f, EventSpot(_ev));
                            if (live && _carousel != null) _carousel.transform.Rotate(0f, 0f, -120f * dt);
                            break;
                        case Ev.GhostFlash:
                            Move(_ghostCar, AtlasParkWorldData.GhostRide, live ? Mathf.Clamp01((el - Announce) / 3f) : -1f);
                            if (el >= Announce + 3f && Cue(1, true, "thud", 0.35f, EventSpot(_ev))) TakePhoto();
                            break;
                        case Ev.Flume:
                            Move(_boat, AtlasParkWorldData.CanalLine, live ? Mathf.Clamp01((el - Announce) / 3f) : -1f);
                            bridge = el >= Announce + 2f;
                            Cue(1, bridge, "splash", 0.5f, AtlasParkWorldData.FlumeBridge.Min);
                            break;
                        case Ev.TurnstileJam:
                            jam = live;
                            Cue(1, live, "slam", 0.35f, EventSpot(_ev));
                            break;
                    }
                }
            }
            bool blink = _ev != Ev.None && Mathf.Repeat(el * 2.5f, 1f) < 0.5f;
            foreach (var g in Crossings) SetGate(g, coaster, blink && _ev == Ev.Coaster);
            foreach (var g in CarouselGates) SetGate(g, carousel, false);
            LampTick(dt);
            if (_carousel != null)
            {
                // Das Karussell selbst ist ein Kartenobjekt (park_art.py); die Scheibe zeigt nur die Fahrt als Wirbel
                _carousel.enabled = carousel;
                _carousel.color = new Color(1f, 0.92f, 0.85f, 0.35f);
            }
            if (_bridge != null) SetGate(_bridge, bridge, blink && _ev == Ev.Flume);
            TurnstileTick(jam, blink && _ev == Ev.TurnstileJam);
            if (_flash != null && _flash.color.a > 0f)
                _flash.color = new Color(1f, 1f, 1f, Mathf.Max(0f, _flash.color.a - dt * 2.5f));
            DiagOneWayTick();
            DiagCaptureTick();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    private static void EndEvent()
    {
        if (_train != null) _train.gameObject.SetActive(false);
        if (_boat != null) _boat.gameObject.SetActive(false);
        if (_ghostCar != null) _ghostCar.gameObject.SetActive(false);
        _ev = Ev.None;
    }

    /// <summary>Einmaliger Schritt k des laufenden Ereignisses, sobald cond gilt; true genau beim Ausloesen.</summary>
    private static bool Cue(int k, bool cond, string sound, float vol, Vector2 at)
    {
        if (!cond || (_cues & (1 << k)) != 0) return false;
        _cues |= 1 << k;
        var lp = PlayerControl.LocalPlayer;
        float dist = lp != null ? Vector2.Distance(lp.GetTruePosition(), at) : 20f;
        AtlasWeatherFx.Sfx(sound, vol * Mathf.Lerp(1f, 0.15f, Mathf.Clamp01(dist / 35f)));
        return true;
    }

    private static Vector2 EventSpot(Ev kind) => kind switch
    {
        Ev.Coaster => RoomCenter(SystemTypes.Reactor),
        Ev.Carousel => AtlasParkWorldData.CarouselCenter,
        Ev.GhostFlash => RoomCenter(SystemTypes.Laboratory),
        Ev.Flume => AtlasParkWorldData.FlumeBridge.Min,
        _ => (AtlasParkWorldData.Turnstiles[0].Min + AtlasParkWorldData.Turnstiles[1].Max) / 2f,
    };

    private static void SetGate(Gate g, bool closed, bool blink)
    {
        if (g == null) return;
        if (g.Closed != closed)
        {
            g.Closed = closed;
            if (g.Blocker != null) g.Blocker.SetActive(closed);
            if (g.Bar != null) g.Bar.gameObject.SetActive(closed);
        }
        foreach (var l in g.Lamps)
            if (l != null) l.color = blink || closed ? new Color(1f, 0.15f, 0.12f) : new Color(0.35f, 0.08f, 0.08f);
    }

    /// <summary>Sprite entlang eines Polygonzugs; u in [0,1], u &lt; 0 = ausblenden.</summary>
    private static void Move(SpriteRenderer sr, Vector2[] path, float u)
    {
        if (sr == null) return;
        if (u < 0f || u > 1f || path == null || path.Length < 2) { sr.gameObject.SetActive(false); return; }
        if (!sr.gameObject.activeSelf) sr.gameObject.SetActive(true);
        float total = 0f;
        for (int i = 1; i < path.Length; i++) total += Vector2.Distance(path[i - 1], path[i]);
        float want = u * total;
        for (int i = 1; i < path.Length; i++)
        {
            float seg = Vector2.Distance(path[i - 1], path[i]);
            if (want <= seg || i == path.Length - 1)
            {
                var p = Vector2.Lerp(path[i - 1], path[i], seg > 0f ? Mathf.Clamp01(want / seg) : 0f);
                var d = path[i] - path[i - 1];
                sr.transform.position = new Vector3(p.x, p.y, AtlasMuseumBuilder.SortZ(p.y - 0.4f));
                sr.transform.eulerAngles = new Vector3(0f, 0f, Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
                return;
            }
            want -= seg;
        }
    }

    // ------------------------------------------------------------------ Geisterbahn

    private static void TakePhoto()
    {
        var ship = ShipStatus.Instance;
        if (_flash != null) _flash.color = new Color(1f, 1f, 1f, 0.85f);
        if (ship == null || !ship.FastRooms.ContainsKey(SystemTypes.Laboratory)) return;
        var area = ship.FastRooms[SystemTypes.Laboratory].roomArea;
        var colors = new List<int>();
        foreach (var pc in PlayerControl.AllPlayerControls)
        {
            if (pc == null || pc.Data == null || pc.Data.IsDead || pc.Data.Disconnected) continue;
            if (area == null || !area.OverlapPoint(pc.GetTruePosition())) continue;
            colors.Add(pc.CurrentOutfit != null ? pc.CurrentOutfit.ColorId : pc.Data.DefaultOutfit.ColorId);
        }
        for (int i = 0; i < MonitorFigures.Count; i++)
        {
            var (body, visor) = MonitorFigures[i];
            bool on = i < colors.Count;
            body.gameObject.SetActive(on); visor.gameObject.SetActive(on);
            if (on)
            {
                int c = colors[i];
                body.color = c >= 0 && c < Palette.PlayerColors.Length ? (Color)Palette.PlayerColors[c] : Color.gray;
            }
        }
        if (_monitorText != null) _monitorText.text = colors.Count == 0 ? "RIDE PHOTO: empty" : $"RIDE PHOTO: {colors.Count}";
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ghost train photo: {colors.Count} rider(s)");
    }

    /// <summary>Sichtfaktor: die Geisterbahn ist dunkel.</summary>
    public static float VisionFactor(Vector2 pos)
    {
        var ship = ShipStatus.Instance;
        if (ship == null || !ship.FastRooms.ContainsKey(SystemTypes.Laboratory)) return 1f;
        var area = ship.FastRooms[SystemTypes.Laboratory].roomArea;
        return area != null && area.OverlapPoint(pos) ? 0.35f : 1f;
    }

    // ------------------------------------------------------------------ Drehkreuze (Einbahn, je Client)

    private static void TurnstileTick(bool jam, bool blink)
    {
        var lp = PlayerControl.LocalPlayer;
        bool alive = lp != null && lp.Data != null && !lp.Data.IsDead;
        var pos = lp != null ? lp.GetTruePosition() : Vector2.zero;
        for (int i = 0; i < Turnstiles.Count; i++)
        {
            var (min, max, inward) = AtlasParkWorldData.Turnstiles[i];
            // Ausgangsseite: hinein (nach Norden) -> noerdlich des Kreuzes; hinaus (nach Sueden) -> suedlich
            bool exitSide = inward ? pos.y > max.y : pos.y < min.y;
            bool near = pos.x > min.x - 3f && pos.x < max.x + 3f;
            bool closed = jam || (alive && exitSide && near);
            var g = Turnstiles[i];
            if (g.Blocker != null && g.Blocker.activeSelf != closed) g.Blocker.SetActive(closed);
            if (g.Bar != null && g.Bar.gameObject.activeSelf != jam) g.Bar.gameObject.SetActive(jam);
            g.Closed = closed;
            foreach (var l in g.Lamps)
                if (l != null) l.color = jam ? (blink ? new Color(1f, 0.15f, 0.12f) : new Color(0.5f, 0.1f, 0.1f))
                                             : (exitSide && alive ? new Color(0.8f, 0.25f, 0.2f) : new Color(0.25f, 0.85f, 0.35f));
        }
    }

    // ------------------------------------------------------------------ Diagnose (TaskTest "world:...")

    /// <summary>Freeplay/Autotest: Ereignis sofort (ueberschreibt ein laufendes).</summary>
    public static void DiagStart(Ev kind)
    {
        EndEvent();
        Apply(kind);
        _nextEvent = Time.time + 60f;
        _diagCaptureAt = Time.time + Announce + 2.2f;
    }

    private static float _diagCaptureAt = -1f;

    private static void DiagCaptureTick()
    {
        if (_diagCaptureAt < 0f || Time.time < _diagCaptureAt) return;
        _diagCaptureAt = -1f;
        AtlasMapShot.DiagCapture();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag map shot during {_ev}");
    }

    /// <summary>Freeplay/Autotest: einen Dummy in die Geisterbahn stellen, damit das Foto jemanden zeigt.</summary>
    public static void DiagDummyInGhost()
    {
        foreach (var d in Object.FindObjectsOfType<DummyBehaviour>())
        {
            var pc = d != null ? d.GetComponent<PlayerControl>() : null;
            if (pc == null || pc.NetTransform == null) continue;
            pc.NetTransform.SnapTo(new Vector2(-15.2f, -7.0f));   // im Tunnel zwischen den Zickzack-Waenden
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: dummy placed in the ghost train");
            return;
        }
    }

    private static int _diagOneWay;
    private static string _diagOneWayLog = "";

    /// <summary>Einbahn-Probe: Spieler noerdlich, dann suedlich der Drehkreuze; je einen Frame spaeter den
    /// Kollider-Zustand pruefen. Erwartet: noerdlich "in" zu, "out" offen; suedlich "in" offen, "out" zu.</summary>
    public static void DiagOneWay()
    {
        _diagOneWay = 1;
        _diagOneWayLog = "";
        PlayerControl.LocalPlayer.NetTransform.SnapTo(new Vector2(0f, -1.2f));    // Festplatz, noerdlich zwischen beiden Drehkreuzen (je 3 m Reichweite)
    }

    private static void DiagOneWayTick()
    {
        if (_diagOneWay == 0 || Turnstiles.Count < 2) return;
        string state = $"in={(Turnstiles[0].Closed ? "closed" : "open")} out={(Turnstiles[1].Closed ? "closed" : "open")}";
        if (_diagOneWay == 1) { _diagOneWay = 2; return; }                 // ein Frame nach dem Snap
        if (_diagOneWay == 2)
        {
            bool ok = Turnstiles[0].Closed && !Turnstiles[1].Closed;
            _diagOneWayLog = $"north: {state} ({(ok ? "ok" : "WRONG")})";
            PlayerControl.LocalPlayer.NetTransform.SnapTo(new Vector2(0f, -4.8f));
            _diagOneWay = 3;
            return;
        }
        if (_diagOneWay == 3) { _diagOneWay = 4; return; }
        bool ok2 = !Turnstiles[0].Closed && Turnstiles[1].Closed;
        bool pass = _diagOneWayLog.Contains("(ok)") && ok2;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} one-way RESULT {(pass ? "PASS" : "FAIL")}: {_diagOneWayLog}; south: {state} ({(ok2 ? "ok" : "WRONG")})");
        _diagOneWay = 0;
    }

    public static string DiagState() =>
        $"park event {_ev}, crossings closed {Crossings.FindAll(g => g.Closed).Count}/{Crossings.Count}, " +
        $"carousel gates closed {CarouselGates.FindAll(g => g.Closed).Count}, bridge {(_bridge != null && _bridge.Closed ? "closed" : "open")}, " +
        $"turnstiles in={(Turnstiles.Count > 0 && Turnstiles[0].Closed ? "closed" : "open")} out={(Turnstiles.Count > 1 && Turnstiles[1].Closed ? "closed" : "open")}";

    // ------------------------------------------------------------------ Graybox-Sprites (prozedural)

    private static Sprite _px, _stripe, _rope, _circle, _disc, _cart, _boatS, _crewBody, _crewVisor;
    private static Sprite Px => _px ??= Make(4, 4, (x, y) => new Color32(255, 255, 255, 255));
    private static Sprite Stripe => _stripe ??= Make(64, 10, (x, y) =>
        y == 0 || y == 9 ? new Color32(20, 16, 24, 255) : ((x + y) / 6) % 2 == 0 ? new Color32(220, 40, 44, 255) : new Color32(245, 242, 236, 255));
    private static Sprite Rope => _rope ??= Make(64, 8, (x, y) =>
        y == 0 || y == 7 ? new Color32(30, 22, 12, 255) : (x / 5) % 2 == 0 ? new Color32(236, 190, 60, 255) : new Color32(30, 30, 34, 255));
    private static Sprite Circle => _circle ??= Make(32, 32, (x, y) =>
    {
        float dx = x - 15.5f, dy = y - 15.5f, r = Mathf.Sqrt(dx * dx + dy * dy);
        return r > 15.5f ? new Color32(0, 0, 0, 0) : r > 13.5f ? new Color32(20, 16, 24, 255) : new Color32(255, 255, 255, 255);
    });
    private static Sprite Disc => _disc ??= Make(96, 96, (x, y) =>
    {
        float dx = x - 47.5f, dy = y - 47.5f, r = Mathf.Sqrt(dx * dx + dy * dy);
        if (r > 47.5f) return new Color32(0, 0, 0, 0);
        if (r > 45f) return new Color32(20, 16, 24, 255);
        if (r < 8f) return new Color32(250, 214, 90, 255);
        int seg = (int)((Mathf.Atan2(dy, dx) + Mathf.PI) / (2f * Mathf.PI) * 12f) % 12;
        if (r > 40f) return seg % 2 == 0 ? new Color32(250, 214, 90, 255) : new Color32(200, 60, 120, 255);
        return seg % 2 == 0 ? new Color32(230, 90, 150, 255) : new Color32(250, 236, 220, 255);
    });
    private static Sprite Cart => _cart ??= Make(96, 30, (x, y) =>
    {
        bool gap = x % 32 < 2 || x % 32 > 29;
        if (gap) return y > 12 && y < 17 ? new Color32(60, 60, 70, 255) : new Color32(0, 0, 0, 0);
        bool edge = y < 2 || y > 27 || x % 32 < 4 || x % 32 > 27;
        bool window = y > 15 && y < 24 && x % 32 > 8 && x % 32 < 24;
        return edge ? new Color32(20, 16, 24, 255) : window ? new Color32(250, 220, 120, 255) : new Color32(210, 50, 60, 255);
    });
    private static Sprite Boat => _boatS ??= Make(64, 28, (x, y) =>
    {
        float dx = (x - 31.5f) / 31.5f, dy = (y - 13.5f) / 13.5f;
        float r = dx * dx + dy * dy;
        return r > 1f ? new Color32(0, 0, 0, 0) : r > 0.8f ? new Color32(40, 26, 14, 255) : r > 0.45f ? new Color32(150, 100, 56, 255) : new Color32(110, 72, 40, 255);
    });
    private static Sprite CrewBody => _crewBody ??= Make(20, 24, (x, y) =>
    {
        bool body = (x >= 4 && x <= 15 && y >= 3 && y <= 19) && !(y > 16 && (x < 6 || x > 13)) && !(y < 6 && x > 8 && x < 11);
        bool pack = x >= 1 && x <= 4 && y >= 7 && y <= 15;
        return body || pack ? new Color32(255, 255, 255, 255) : new Color32(0, 0, 0, 0);
    });
    private static Sprite CrewVisor => _crewVisor ??= Make(20, 24, (x, y) =>
        x >= 9 && x <= 16 && y >= 12 && y <= 16 ? new Color32(150, 210, 230, 255) : new Color32(0, 0, 0, 0));

    // ------------------------------------------------------------ Lichtebene: Laternen am Weg

    private static readonly List<(SpriteRenderer Post, SpriteRenderer Glow)> Lamps = new();
    private static Sprite _lampOn, _lampOff, _glow;
    private static float _lampLevel = 1f;

    private static Sprite Glow => _glow ??= Make(64, 64, (x, y) =>
    {
        float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f, r = Mathf.Sqrt(dx * dx + dy * dy);
        float a = Mathf.Clamp01(1f - r);
        return new Color32(255, 255, 255, (byte)(a * a * 255));
    });

    private static void BuildLamps()
    {
        Lamps.Clear();
        _lampLevel = 1f;
        _lampOn = AtlasAssets.TaskSprite("task_park_lamppost.png", AtlasParkWorldData.LampPixelsPerMeter, AtlasParkWorldData.LampPivot);
        _lampOff = AtlasAssets.TaskSprite("task_park_lamppost_off.png", AtlasParkWorldData.LampPixelsPerMeter, AtlasParkWorldData.LampPivot);
        if (_lampOn == null) return;
        foreach (var p in AtlasParkWorldData.Lamps)
        {
            var glow = Spr("LampGlow", Glow, p, 4.6f, p.y);
            glow.transform.position = new Vector3(p.x, p.y, 8.5f);            // ueber dem Boden (z 9), hinter allem anderen
            glow.color = new Color(1f, 0.78f, 0.48f, 0.3f);
            var post = Spr("Lamp", _lampOn, p, _lampOn.bounds.size.x, p.y);
            Lamps.Add((post, glow));
        }
    }

    /// <summary>Park Blackout (Licht-Sabotage): Laternen flackern und gehen aus; Leuchtreklamen bleiben an.</summary>
    private static bool Blackout()
    {
        try
        {
            var ship = ShipStatus.Instance;
            if (ship == null || !ship.Systems.ContainsKey(SystemTypes.Electrical)) return false;
            var s = ship.Systems[SystemTypes.Electrical].TryCast<SwitchSystem>();
            return s != null && s.ActualSwitches != s.ExpectedSwitches;
        }
        catch { return false; }
    }

    private static void LampTick(float dt)
    {
        if (Lamps.Count == 0) return;
        float target = Blackout() ? 0f : 1f;
        float prev = _lampLevel;
        _lampLevel = Mathf.MoveTowards(_lampLevel, target, dt * (target < prev ? 1.6f : 0.8f));
        if (Mathf.Approximately(prev, _lampLevel) && (_lampLevel == 0f || _lampLevel == 1f)) return;
        for (int i = 0; i < Lamps.Count; i++)
        {
            var (post, glow) = Lamps[i];
            if (post == null || glow == null) continue;
            // beim Ausgehen flackern die Laternen einzeln
            float f = _lampLevel > 0f && _lampLevel < 1f ? Mathf.Clamp01(_lampLevel + (Mathf.PerlinNoise(i * 3.1f, Time.time * 9f) - 0.5f) * 0.8f) : _lampLevel;
            glow.color = new Color(1f, 0.78f, 0.48f, 0.3f * f);
            post.sprite = f > 0.5f ? _lampOn : _lampOff;
        }
    }

    private static Sprite Make(int w, int h, Func<int, int, Color32> f)
    {
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        var px = new Color32[w * h];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                px[y * w + x] = f(x, y);
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Bilinear;
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.Apply(false, false);
        tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var s = UnityEngine.Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f);
        s.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        return s;
    }
}
