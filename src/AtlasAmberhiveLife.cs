// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
// Amberhive: sichtbare Umgebung, Host-Pollenspuren und rein optischer Sonnenlauf.
// Netz: AtlasWorld Op 24, Subs 16 (Zustand), 17 (Abdruecke), 18/19 reserviert.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using BepInEx.Configuration;
using Hazel;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal sealed class AtlasAmberhiveLife : IDisposable
{
    internal const int OptionId = 1730;
    internal static object PollenOption { get; private set; }
    private static FieldInfo _selection;
    private static ConfigEntry<bool> _pollenFallback, _logTest, _glowTest;
    private static ConfigEntry<int> _pollenTest;
    private static ConfigEntry<float> _sunTest;
    internal static AtlasAmberhiveLife Current { get; private set; }

    internal static void Bind(ConfigFile cfg)
    {
        _pollenFallback = cfg.Bind("Amberhive", "PollenTrails", false,
            "Host only: golden pollen footprints. TOR option 1730 takes precedence. Default off.");
        _pollenTest = cfg.Bind("Diagnostics", "AmberhivePollenTest", -1,
            "Freeplay only: -1 follows the option, 0 disables pollen, 1 enables pollen.");
        _sunTest = cfg.Bind("Diagnostics", "AmberhiveSunPeriodTest", 0f,
            "Freeplay only: sun cycle in seconds, minimum 30; 0 uses the normal 600 seconds.");
        _glowTest = cfg.Bind("Diagnostics", "AmberhiveGlowTest", false,
            "Freeplay only: demonstrate optical Glow Fade every 8 seconds, without changing vision or sabotage.");
        _logTest = cfg.Bind("Diagnostics", "AmberhiveLifeLog", false,
            "Log Life clock, pollen count, source gates and lamp state every 2 seconds for the game test.");
    }

    internal static void RegisterOption(Type co, Func<int, string, string[], object, bool, object> make)
    {
        _selection = co.GetField("selection", BindingFlags.Public | BindingFlags.Instance);
        PollenOption = make(OptionId, "Amberhive Pollen Trails", new[] { "Off", "On" }, null, false);
    }

    private static bool HostOption()
    {
        if (Freeplay && (_pollenTest?.Value ?? -1) >= 0) return _pollenTest.Value == 1;
        try { if (PollenOption != null && _selection != null) return (int)_selection.GetValue(PollenOption) == 1; }
        catch { }
        return _pollenFallback?.Value ?? false;
    }

    private static bool Freeplay => AmongUsClient.Instance != null && AmongUsClient.Instance.NetworkMode == NetworkModes.FreePlay;
    private static bool Host => Freeplay || (AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost);
    private static bool Paused => MeetingHud.Instance != null || ExileController.Instance != null;
    private const float Lifetime = AmberhiveLifeRules.Lifetime;
    private const int MaxPrints = 320, PacketPrints = 40;

    private readonly Transform _root;
    private readonly List<Object> _owned = new();
    private readonly List<Lamp> _lamps = new();
    private readonly List<Candle> _candles = new();
    private readonly List<(SpriteRenderer Sr, Color Original)> _racks = new();
    private readonly List<Print> _prints = new(), _honey = new();
    private readonly List<Print> _pending = new();
    private readonly Dictionary<byte, AmberhivePollenWalker> _walkers = new();
    private readonly Dictionary<byte, Walker> _localWalkers = new();
    private readonly Dictionary<byte, float> _transit = new();
    private readonly List<(PlayerControl Player, Vector2 Pos)> _visibleMoving = new();
    private readonly HashSet<byte> _visibleOwners = new();
    private readonly Func<Vector2, bool> _wet;
    private readonly AtlasMapDef _def;
    private Sprite _foot, _glow, _flame, _jar, _beam;
    private SpriteRenderer _sun, _pollenMat;
    private Vector2 _pollenAt;
    private bool _hasPollen, _enabled, _dark, _wasPaused, _wasHost, _synced, _disposed;
    private float _clock, _glowAt = -10f, _nextState, _nextPrintSend, _nextSample, _nextLog, _nextProps;
    private int _generation;
    private uint _serial;
    private int _sightFrame = -1;
    private int _fullCursor = -1;               // Vollabgleich der Abdruecke: naechstes Paket, -1 = keiner laeuft
    private float _nextFull;
    private bool _refresh;                      // Sicht und Laeufer nur jeden dritten Frame neu bewerten
    private Vector2 _sightAt;
    private float _sightRadiusSquared;
    private bool _sightReady;

    private sealed class Walker
    {
        internal Vector2 Pos, Step;
        internal float At, StepAt, MovingUntil, BlockUntil;
    }

    private sealed class Print
    {
        internal uint Id;
        internal Vector2 Pos;
        internal float Angle, Born;
        internal byte Owner;
        internal SpriteRenderer Sr;
    }

    private sealed class Lamp
    {
        internal SpriteRenderer Glow, Jar;
        internal Vector2 Pos;
        internal float From = 1f;
    }

    private sealed class Candle
    {
        internal SpriteRenderer Flame, Halo;
        internal Vector2 Feet;
        internal Vector3 Scale;
        internal float Phase, Draft, Direction;
    }

    internal AtlasAmberhiveLife(Transform parent, AtlasMapDef def, Func<Vector2, bool> wet)
    {
        Current?.Dispose();
        Current = this;
        _def = def; _wet = wet;
        var go = new GameObject("Atlas_AmberhiveLife");
        go.transform.SetParent(parent, false);
        _root = go.transform;
        Current = this;
        _wasHost = Host; _synced = Host; _enabled = Host && HostOption();
        BuildSprites();
        BuildPollen();
        BuildLamps();
        _sun = Renderer("CrownSun", _beam, Vector2.zero, AtlasMuseumBuilder.FloorZ - .8f);
        _sun.transform.localScale = new Vector3(7f, 4.8f, 1f);
        AtlasPlugin.Logger.LogInfo($"[Atlas/Life] bereit: Option {OptionId}, Pollenbereich {_pollenAt}, {_lamps.Count} Laternen");
    }

    internal void Tick(float dt)
    {
        if (_disposed || _root == null) return;
        if (!float.IsFinite(dt)) return;
        dt = Mathf.Clamp(dt, 0f, .2f);
        bool paused = Paused;
        bool authority = Host;
        if (authority != _wasHost)
        {
            _wasHost = authority;
            if (authority) { ClearTrails(); _generation++; _nextState = 0f; _synced = true; _fullCursor = -1; }
        }
        if (!paused) _clock += dt;
        if (paused && !_wasPaused)
        {
            ClearTrails();
            if (authority) { _generation++; _nextState = 0f; _fullCursor = -1; }
        }
        // Nach Meeting/Rauswurf einmal voll abgleichen: Gaeste, die den Rauswurf spaeter beenden, haben
        // die ersten Deltas verworfen.
        if (!paused && _wasPaused && authority) _nextFull = Time.time + 1.5f;
        _wasPaused = paused;
        if (Time.time >= _nextProps) { _nextProps = Time.time + 1f; BindProps(); }
        if (authority)
        {
            bool enabled = HostOption();
            if (_enabled != enabled)
            {
                _enabled = enabled; ClearTrails(); _generation++; _nextState = 0f; _fullCursor = -1;
            }
            bool dark = AtlasWorld.LightsOut();
            if (Freeplay && (_glowTest?.Value ?? false)) dark = (int)(_clock / 8f) % 2 == 1;
            if (_dark != dark)
            {
                for (int i = 0; i < _lamps.Count; i++) _lamps[i].From = LampLevel(i);
                _dark = dark; _glowAt = _clock; _nextState = 0f;
            }
            if (!paused && _enabled && _clock >= _nextSample)
            {
                _nextSample = _clock + .08f;
                HostSteps();
            }
            if (Time.time >= _nextState)
            {
                _nextState = Time.time + 1f;
                SendState();
            }
            // Deltas reichen im Normalfall (zuverlaessige RPCs). Die volle Liste nur selten als Abgleich und
            // hoechstens ein Paket je Frame: der Server trennt Spieler bei Datenschueben.
            if (_fullCursor < 0 && Time.time >= _nextFull)
            {
                _nextFull = Time.time + Lifetime;
                if (_prints.Count > 0) _fullCursor = 0;
            }
            if (_fullCursor >= 0)
            {
                if (_fullCursor >= _prints.Count) _fullCursor = -1;
                else { SendPrints(_prints, _fullCursor, PacketPrints); _fullCursor += PacketPrints; }
            }
            if (_pending.Count > 0 && Time.time >= _nextPrintSend)
            {
                _nextPrintSend = Time.time + .1f; SendPrints(_pending); _pending.Clear();
            }
        }
        _refresh = Time.frameCount % 3 == 0;
        if (paused) { _visibleMoving.Clear(); _visibleOwners.Clear(); }
        else if (_refresh) LocalWalkers();
        TickPrints(); TickSun(); TickLamps(); TickCandles();
        _pollenMat.enabled = _hasPollen && _enabled && _synced && !paused;
        if ((_logTest?.Value ?? false) && Time.time >= _nextLog)
        {
            _nextLog = Time.time + 2f;
            AtlasPlugin.Logger.LogInfo($"[Atlas/Life] Uhr={_clock:F2} Host={authority} Sync={_synced} Pollen={_enabled} " +
                $"Abdruecke={_prints.Count} Honig={_honey.Count} sichtbareLaeufer={_visibleMoving.Count} GlowFade={_dark} Generation={_generation}");
        }
    }

    // Nur der Host entscheidet ueber Schritte. Clients berechnen keine fremden Laufwege nach.
    private void HostSteps()
    {
        foreach (var p in PlayerControl.AllPlayerControls)
        {
            if (p == null) continue;
            byte id = p.PlayerId;
            if (!PublicWalker(p) || InTransit(id)) { _walkers.Remove(id); continue; }
            Vector2 pos = p.GetTruePosition();
            if (!_walkers.TryGetValue(id, out var w))
            {
                _walkers[id] = new AmberhivePollenWalker(pos.x, pos.y, _clock); continue;
            }
            if (!w.Sample(pos.x, pos.y, _clock, InPollen(pos), ClearLine(new Vector2(w.X, w.Y), pos), out var step)) continue;
            var print = new Print { Id = ++_serial, Pos = new Vector2(step.X, step.Y), Angle = step.Angle, Born = _clock };
            // Auf dem Host dieselbe Zentimeter-/Winkelquantisierung wie auf allen Gaesten.
            print.Pos = new Vector2(Mathf.Round(print.Pos.x * 100f) / 100f, Mathf.Round(print.Pos.y * 100f) / 100f);
            print.Angle = PackAngle(print.Angle) * (360f / 256f);
            AddPrint(print); _pending.Add(print);
        }
    }

    private static Walker NewWalker(Vector2 pos, float now) => new()
    {
        Pos = pos, Step = pos, At = now, StepAt = now, BlockUntil = now + .25f
    };

    internal void SuppressTransit(byte player, float seconds)
    {
        _transit[player] = _clock + seconds;
        _walkers.Remove(player); _localWalkers.Remove(player);
    }

    private bool InTransit(byte id) => _transit.TryGetValue(id, out float until) && until > _clock;

    // Ein fehlender oder halbtransparenter Koerper erzeugt keine neuen Informationen.
    // Strengere Alpha-Grenze auch fuer Impostoren/Geister, die einen Ninja halb sehen koennen.
    private static bool PublicWalker(PlayerControl p)
    {
        try
        {
            if (p == null || p.Data == null || p.Data.IsDead || p.Data.Disconnected || !p.Visible || p.inVent || p.walkingToVent ||
                p.inMovingPlat || p.onLadder || !p.gameObject.activeInHierarchy || AtlasFigure.Posed(p.PlayerId)) return false;
            var phantom = p.Data.Role?.TryCast<PhantomRole>();
            if (phantom != null && (phantom.IsInvisible || phantom.IsFading)) return false;
            var body = p.cosmetics?.currentBodySprite?.BodySprite;
            if (body == null || !body.enabled || !body.gameObject.activeInHierarchy || body.color.a < .98f) return false;
            if (RoleHidden(p)) return false;
            return true;
        }
        catch { return false; }
    }

    // Optionale Rollen bleiben ohne TOR-/Collection-Assembly ladbar. Felder werden einmal gesucht.
    private static bool _rolesRead;
    private static FieldInfo _ninja, _ninjaHidden, _scout, _scoutActive, _propsHidden;
    private static void ReadRoles()
    {
        if (_rolesRead) return;
        _rolesRead = true;
        foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
        {
            var ninja = a.GetType("TheOtherRoles.TheOtherRoles+Ninja", false) ?? a.GetType("TheOtherRoles.Ninja", false);
            var scout = a.GetType("UnknownsCollection.Scout", false);
            var props = a.GetType("TheOtherRoles.CustomGameModes.PropHunt", false);
            const BindingFlags flags = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
            if (ninja != null) { _ninja = ninja.GetField("ninja", flags); _ninjaHidden = ninja.GetField("isInvisble", flags); }
            if (scout != null) { _scout = scout.GetField("scout", flags); _scoutActive = scout.GetField("abilityActive", flags); }
            if (props != null) _propsHidden = props.GetField("invisPlayers", flags);
        }
    }

    private static bool RoleHidden(PlayerControl p)
    {
        try
        {
            ReadRoles();
            if (_ninja?.GetValue(null) is PlayerControl ninja && ninja.PlayerId == p.PlayerId && _ninjaHidden?.GetValue(null) is true) return true;
            if (_scout?.GetValue(null) is PlayerControl scout && scout.PlayerId == p.PlayerId && _scoutActive?.GetValue(null) is true) return true;
            if (_propsHidden?.GetValue(null) is IDictionary hidden && hidden.Contains(p.PlayerId)) return true;
        }
        catch { return true; }
        return false;
    }

    private static bool ClearLine(Vector2 a, Vector2 b)
    {
        try { return !PhysicsHelpers.AnythingBetween(a, b, Constants.ShadowMask, false); }
        catch { return false; }
    }

    private bool InSight(Vector2 p)
    {
        try
        {
            // Die komplette Sichtweiten-Patchkette nur einmal je Frame auswerten.
            if (_sightFrame != Time.frameCount)
            {
                _sightFrame = Time.frameCount; _sightReady = false;
                var local = PlayerControl.LocalPlayer;
                var ship = ShipStatus.Instance;
                if (local == null || local.Data == null || ship == null) return false;
                _sightAt = local.GetTruePosition();
                float radius = ship.CalculateLightRadius(local.Data);
                _sightRadiusSquared = radius * radius; _sightReady = true;
            }
            return _sightReady && (p - _sightAt).sqrMagnitude < _sightRadiusSquared && ClearLine(_sightAt, p);
        }
        catch { return false; }
    }

    private void LocalWalkers()
    {
        _visibleMoving.Clear();
        _visibleOwners.Clear();
        foreach (var p in PlayerControl.AllPlayerControls)
        {
            if (p == null) continue;
            byte id = p.PlayerId;
            Vector2 pos = p.GetTruePosition();
            // Billige Pruefungen zuerst; PublicWalker (Reflection, Farb-Getter) nur fuer sichtbare Spieler.
            if (InTransit(id) || !InSight(pos) || !PublicWalker(p)) { _localWalkers.Remove(id); continue; }
            _visibleOwners.Add(id);
            if (!_localWalkers.TryGetValue(id, out var w)) { _localWalkers[id] = NewWalker(pos, Time.time); continue; }
            Vector2 delta = pos - w.Pos;
            float elapsed = Mathf.Max(.01f, Time.time - w.At);
            w.At = Time.time; w.Pos = pos;
            if (delta.magnitude > Mathf.Min(1.4f, .45f + elapsed * 8f) || !ClearLine(pos - delta, pos))
            { w.Step = pos; w.MovingUntil = 0f; w.BlockUntil = Time.time + .5f; continue; }
            if (Time.time < w.BlockUntil) continue;
            if (delta.sqrMagnitude > .0001f) w.MovingUntil = Time.time + .16f;
            if (w.MovingUntil > Time.time) _visibleMoving.Add((p, pos));
            if (!_wet(pos) || Time.time - w.StepAt < .24f || (pos - w.Step).sqrMagnitude < .12f) continue;
            Vector2 d = pos - w.Step;
            var print = new Print { Pos = pos, Angle = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg - 90f,
                Born = Time.time, Owner = id, Sr = Renderer("HoneyStep", _foot, pos, AtlasMuseumBuilder.FloorZ - .95f) };
            print.Sr.transform.localScale = new Vector3(.19f, .32f, 1f);
            print.Sr.transform.localRotation = Quaternion.Euler(0f, 0f, print.Angle);
            _honey.Add(print); w.Step = pos; w.StepAt = Time.time;
            if (_honey.Count > 96) { DestroyPrint(_honey[0]); _honey.RemoveAt(0); }
        }
    }

    // Bienen werden nur durch im eigenen Licht sichtbare Laeufer verdraengt.
    internal Vector2 BeeAvoid(Vector2 pos, Vector2[] area, float dt)
    {
        if (!InSight(pos)) return pos;
        Vector2 push = Vector2.zero;
        foreach (var w in _visibleMoving)
        {
            Vector2 d = pos - w.Pos;
            float distance = d.magnitude;
            if (distance >= 1.65f || !ClearLine(w.Pos, pos)) continue;
            if (distance < .02f) d = Vector2.right;
            push += d.normalized * (1f - distance / 1.65f) * 3.2f;
        }
        Vector2 candidate = pos + Vector2.ClampMagnitude(push, 3.2f) * Mathf.Min(dt, .1f);
        return Inside(area, candidate) && ClearLine(pos, candidate) ? candidate : pos;
    }

    private void TickPrints()
    {
        for (int i = _prints.Count - 1; i >= 0; i--)
        {
            var p = _prints[i]; float age = _clock - p.Born;
            if (age >= Lifetime || !_enabled) { DestroyPrint(p); _prints.RemoveAt(i); continue; }
            if (!_synced || Paused) p.Sr.enabled = false;
            else if (_refresh) p.Sr.enabled = InSight(p.Pos);
            p.Sr.color = new Color(1f, .7f, .12f, .82f * Mathf.Clamp01((Lifetime - age) / 1.2f));
        }
        for (int i = _honey.Count - 1; i >= 0; i--)
        {
            var p = _honey[i]; float age = Time.time - p.Born;
            if (age >= 1.25f) { DestroyPrint(p); _honey.RemoveAt(i); continue; }
            bool ownerVisible = _visibleOwners.Contains(p.Owner);
            // Nach Sichtverlust verwerfen: keine spaetere Rekonstruktion fremder Bewegung.
            if (_refresh && (!ownerVisible || !InSight(p.Pos))) { DestroyPrint(p); _honey.RemoveAt(i); continue; }
            p.Sr.enabled = !Paused;
            p.Sr.color = new Color(.85f, .48f, .1f, .45f * (1f - age / 1.25f));
        }
    }

    private void AddPrint(Print p)
    {
        foreach (var old in _prints) if (old.Id == p.Id) return;
        if (_prints.Count >= MaxPrints) { DestroyPrint(_prints[0]); _prints.RemoveAt(0); }
        p.Sr = Renderer("PollenStep", _foot, p.Pos, AtlasMuseumBuilder.FloorZ - 1f);
        p.Sr.transform.localScale = new Vector3(.22f, .36f, 1f);
        p.Sr.transform.localRotation = Quaternion.Euler(0f, 0f, p.Angle);
        p.Sr.enabled = false;
        _prints.Add(p);
    }

    private static void DestroyPrint(Print p) { if (p.Sr != null) Object.Destroy(p.Sr.gameObject); }

    private void ClearTrails()
    {
        foreach (var p in _prints) DestroyPrint(p);
        foreach (var p in _honey) DestroyPrint(p);
        _prints.Clear(); _honey.Clear(); _pending.Clear(); _walkers.Clear(); _localWalkers.Clear(); _visibleMoving.Clear(); _visibleOwners.Clear();
    }

    private void BuildPollen()
    {
        if (_def.Props != null)
            foreach (var prop in _def.Props)
                if (prop.Kind == "flower_pots")
                { _pollenAt = new Vector2((prop.FootX0 + prop.FootX1) * .5f - 1.05f, prop.BaseY + .55f); _hasPollen = true; break; }
        _pollenMat = Renderer("PollenMat", _glow, _pollenAt, AtlasMuseumBuilder.FloorZ - .7f);
        _pollenMat.transform.localScale = new Vector3(1.6f, 1.3f, 1f);
        _pollenMat.color = new Color(1f, .64f, .06f, .32f);
        _pollenMat.enabled = false;
        if (!_hasPollen) AtlasPlugin.Logger.LogWarning("[Atlas/Life] Kein flower_pots-Prop, Pollenerzeugung ausgesetzt. Layout abstimmen.");
    }

    private bool InPollen(Vector2 pos)
    {
        Vector2 d = pos - _pollenAt;
        return _hasPollen && d.x * d.x / (.8f * .8f) + d.y * d.y / (.65f * .65f) <= 1f;
    }

    private void BuildLamps()
    {
        if (_def.Rooms == null) return;
        foreach (var room in _def.Rooms)
        {
            if (room.Area == null || room.Area.Length < 3) continue;
            Vector2 center = Vector2.zero;
            foreach (var p in room.Area) center += p;
            center /= room.Area.Length;
            float top = center.y;
            foreach (var p in room.Area) top = Mathf.Max(top, p.y);
            Vector2 at = new(center.x, top - .7f);
            var lamp = new Lamp { Pos = at };
            lamp.Jar = Renderer("GlowHoneyLantern_" + room.Key, _jar, at, AtlasMuseumBuilder.SortZ(at.y));
            lamp.Jar.transform.localScale = new Vector3(.42f, .58f, 1f);
            lamp.Glow = Renderer("GlowHoneyHalo_" + room.Key, _glow, at, AtlasMuseumBuilder.SortZ(at.y) - .001f);
            lamp.Glow.transform.localScale = new Vector3(2.6f, 2.2f, 1f);
            _lamps.Add(lamp);
        }
        // Stabile Reihenfolge der Welle vom Lamphouse bis zur Krone.
        var source = new Vector2(-17.2f, 0f);
        _lamps.Sort((a, b) => (a.Pos - source).sqrMagnitude.CompareTo((b.Pos - source).sqrMagnitude));
    }

    private float LampLevel(int index)
    {
        return AmberhiveLifeRules.LampLevel(_lamps[index].From, _dark, index, _clock - _glowAt);
    }

    private void TickLamps()
    {
        for (int i = 0; i < _lamps.Count; i++)
        {
            var l = _lamps[i]; float level = LampLevel(i);
            l.Glow.color = new Color(1f, .64f, .13f, level * .3f);
            l.Jar.color = Color.Lerp(new Color(.18f, .12f, .08f), new Color(1f, .81f, .31f), level);
        }
        float rackLevel = _lamps.Count > 0 ? LampLevel(0) : 1f;
        foreach (var rack in _racks)
        {
            if (rack.Sr == null) continue;
            float brightness = Mathf.Lerp(.24f, 1f, rackLevel);
            var c = rack.Original;
            // Alpha gehoert weiterhin Atlas' Moebel-Ausblendung.
            rack.Sr.color = new Color(c.r * brightness, c.g * brightness, c.b * brightness, rack.Sr.color.a);
        }
    }

    private void TickSun()
    {
        float period = Freeplay && (_sunTest?.Value ?? 0f) >= 30f ? _sunTest.Value : 600f;
        float angle = _clock / period * Mathf.PI * 2f;
        Vector2 center = new(Mathf.Sin(angle) * 2.5f, .4f + Mathf.Cos(angle) * .9f);
        _sun.transform.position = new Vector3(center.x, center.y, AtlasMuseumBuilder.FloorZ - .8f);
        _sun.transform.localRotation = Quaternion.Euler(0f, 0f, -24f + Mathf.Sin(angle) * 32f);
        _sun.color = new Color(1f, .83f, .42f, .14f + .035f * Mathf.Cos(angle));
        _sun.enabled = _synced;
        // Ausschliesslich Sprite-Farbe und Position. Kein LightSource-/Sichtradius-Eingriff.
    }

    private readonly HashSet<int> _bound = new();
    private void BindProps()
    {
        if (_def.Props == null) return;
        for (int i = 0; i < _def.Props.Length && i < AtlasMuseumBuilder.PropRenderers.Count; i++)
        {
            var sr = AtlasMuseumBuilder.PropRenderers[i];
            if (sr == null || !_bound.Add(i)) continue;
            var p = _def.Props[i];
            if (p.Kind == "glow_rack" || p.Kind == "lantern_cart") _racks.Add((sr, sr.color));
            if (p.Kind != "candle_rack" && p.Kind != "queen_throne") continue;
            var bounds = sr.bounds;
            for (int k = 0; k < 3; k++)
            {
                Vector2 feet = new(Mathf.Lerp(p.FootX0, p.FootX1, (k + 1f) / 4f), p.BaseY);
                Vector2 at = new(feet.x, bounds.min.y + bounds.size.y * (p.Kind == "queen_throne" ? .62f : .75f));
                var candle = new Candle { Feet = feet, Phase = i * 2.7f + k * 1.9f,
                    Flame = Renderer("CandleFlame", _flame, at, bounds.center.z - .01f),
                    Halo = Renderer("CandleHalo", _glow, at, bounds.center.z - .009f), Scale = new Vector3(.12f, .24f, 1f) };
                candle.Halo.transform.localScale = new Vector3(.72f, .62f, 1f);
                _candles.Add(candle);
            }
        }
    }

    private void TickCandles()
    {
        foreach (var c in _candles)
        {
            if (_refresh)
            {
                float dr = 0f, dir = 0f;
                if (_visibleMoving.Count > 0 && InSight(c.Feet))
                    foreach (var w in _visibleMoving)
                    {
                        float d = Vector2.Distance(w.Pos, c.Feet);
                        if (d > 2f || !ClearLine(w.Pos, c.Feet)) continue;
                        dr = Mathf.Max(dr, 1f - d / 2f);
                        dir += Mathf.Sign(c.Feet.x - w.Pos.x) * (1f - d / 2f);
                    }
                c.Draft = dr; c.Direction = dir;
            }
            float draft = c.Draft, direction = c.Direction;
            float flicker = 1f + .055f * Mathf.Sin(Time.time * 9f + c.Phase) + draft * .25f * Mathf.Sin(Time.time * 34f + c.Phase);
            c.Flame.transform.localScale = new Vector3(c.Scale.x / flicker, c.Scale.y * flicker, 1f);
            c.Flame.transform.localRotation = Quaternion.Euler(0f, 0f, direction * -24f);
            c.Flame.color = new Color(1f, .77f, .24f, .88f - draft * .18f);
            c.Halo.color = new Color(1f, .6f, .12f, .16f * flicker);
        }
    }

    private void SendState()
    {
        AtlasWorld.Send(AtlasAmberhive.OpHive, w =>
        {
            w.Write((byte)16); w.Write((byte)1); w.Write(_clock); w.Write(_generation);
            w.Write(_enabled); w.Write(_dark); w.Write(_glowAt); w.Write((byte)_lamps.Count);
            foreach (var lamp in _lamps) w.Write(lamp.From);
        });
    }

    private void SendPrints(List<Print> source, int first = 0, int max = int.MaxValue)
    {
        int end = max >= source.Count - first ? source.Count : first + max;
        for (int start = first; start < end; start += PacketPrints)
        {
            int offset = start, count = Mathf.Min(PacketPrints, end - start);
            AtlasWorld.Send(AtlasAmberhive.OpHive, w =>
            {
                w.Write((byte)17); w.Write(_generation); w.Write(_clock); w.Write((byte)count);
                for (int i = offset; i < offset + count; i++)
                {
                    var p = source[i];
                    // Hazel hat keinen Write(short): ohne UInt16-Cast werden vier statt zwei Bytes geschrieben.
                    w.Write(p.Id);
                    w.Write(unchecked((ushort)(short)Mathf.RoundToInt(p.Pos.x * 100f)));
                    w.Write(unchecked((ushort)(short)Mathf.RoundToInt(p.Pos.y * 100f)));
                    w.Write(PackAngle(p.Angle)); w.Write(p.Born);
                }
            });
        }
    }

    internal bool Receive(bool fromHost, byte sub, MessageReader r)
    {
        if (sub < 16 || sub > 19) return false;
        if (!fromHost || Host) return true;
        if (sub == 16)
        {
            if (r.ReadByte() != 1) return true;
            float clock = r.ReadSingle(); int generation = r.ReadInt32();
            bool enabled = r.ReadBoolean(), dark = r.ReadBoolean(); float glowAt = r.ReadSingle(); int count = r.ReadByte();
            if (!ValidClock(clock) || !float.IsFinite(glowAt) || glowAt > clock || count != _lamps.Count) return true;
            var levels = new float[count];
            for (int i = 0; i < count; i++)
            {
                levels[i] = r.ReadSingle();
                if (!float.IsFinite(levels[i]) || levels[i] < 0f || levels[i] > 1f) return true;
            }
            if (_generation != generation || !enabled) ClearTrails();
            _generation = generation; _clock = clock; _enabled = enabled; _dark = dark; _glowAt = glowAt; _synced = true;
            for (int i = 0; i < count; i++) _lamps[i].From = levels[i];
        }
        else if (sub == 17)
        {
            int generation = r.ReadInt32(); float clock = r.ReadSingle(); int count = r.ReadByte();
            if (!_synced || !_enabled || Paused || generation != _generation || !ValidClock(clock) || count > PacketPrints) return true;
            var incoming = new List<Print>(count);
            for (int i = 0; i < count; i++)
            {
                uint id = r.ReadUInt32(); Vector2 pos = new(r.ReadInt16() / 100f, r.ReadInt16() / 100f);
                float angle = r.ReadByte() * (360f / 256f), born = r.ReadSingle();
                if (!float.IsFinite(born) || born > clock + .1f || born < 0f ||
                    pos.x < _def.MinX || pos.x > _def.MaxX || pos.y < _def.MinY || pos.y > _def.MaxY) return true;
                if (clock - born < Lifetime) incoming.Add(new Print { Id = id, Pos = pos, Angle = angle, Born = born });
                if (id > _serial) _serial = id;
            }
            _clock = clock;
            foreach (var p in incoming) AddPrint(p);
        }
        return true;
    }

    private static bool ValidClock(float value) => float.IsFinite(value) && value >= 0f && value <= 604800f;
    private static byte PackAngle(float angle) => (byte)(Mathf.RoundToInt(Mathf.Repeat(angle, 360f) * (256f / 360f)) & 255);

    private SpriteRenderer Renderer(string name, Sprite sprite, Vector2 pos, float z)
    {
        var go = new GameObject(name) { layer = 8 };
        go.transform.SetParent(_root, false); go.transform.position = new Vector3(pos.x, pos.y, z);
        var sr = go.AddComponent<SpriteRenderer>(); sr.sprite = sprite;
        AtlasMuseumBuilder.Mask(sr);
        return sr;
    }

    // Kleine weiche Masken, direkt als Sprite erzeugt. Keine zusaetzlichen Downloads oder Shader.
    private void BuildSprites()
    {
        _beam = MakeSprite(96, 128, (x, y) =>
        {
            float width = .09f + .85f * (1f - y) * .5f;
            float edge = Mathf.Clamp01((1f - Mathf.Abs(x) / width) * 5f);
            float ends = Mathf.Clamp01((1f - Mathf.Abs(y)) * 5f);
            float rays = .87f + .13f * Mathf.Sin(x / width * 29f);
            return new Color(1f, 1f, 1f, edge * ends * rays);
        });
        _glow = MakeSprite(64, 64, (x, y) =>
        {
            float r = Mathf.Sqrt(x * x + y * y);
            float a = Mathf.Pow(Mathf.Clamp01(1f - r), 1.6f);
            return new Color(1f, 1f, 1f, a);
        });
        _foot = MakeSprite(24, 40, (x, y) =>
        {
            float sole = x * x / .48f + (y - .24f) * (y - .24f) / .42f;
            float heel = x * x / .31f + (y + .63f) * (y + .63f) / .06f;
            float a = Mathf.Clamp01((1f - Mathf.Min(sole, heel)) * 6f);
            return new Color(1f, 1f, 1f, a);
        });
        _flame = MakeSprite(24, 40, (x, y) =>
        {
            float width = Mathf.Lerp(.7f, .03f, (y + 1f) * .5f);
            float a = Mathf.Clamp01((1f - Mathf.Abs(x) / width) * 4f) * Mathf.Clamp01((1f - Mathf.Abs(y)) * 5f);
            return new Color(1f, 1f, .7f + .3f * (1f - y), a);
        });
        _jar = MakeSprite(32, 44, (x, y) =>
        {
            bool lid = y > .65f && y < .83f && Mathf.Abs(x) < .7f;
            float edge = x * x / .65f + y * y / .9f;
            if (lid) return new Color(.35f, .23f, .12f, 1f);
            if (edge > 1f) return Color.clear;
            float shade = Mathf.Lerp(.6f, 1f, Mathf.Clamp01(1f - edge));
            return new Color(shade, shade * .83f, shade * .4f, Mathf.Clamp01((1f - edge) * 12f));
        });
    }

    private Sprite MakeSprite(int width, int height, Func<float, float, Color> pixel)
    {
        var texture = new Texture2D(width, height, TextureFormat.RGBA32, false)
        { hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
        var colors = new Color32[width * height];
        for (int y = 0; y < height; y++)
            for (int x = 0; x < width; x++) colors[y * width + x] = pixel((x + .5f) / width * 2f - 1f, (y + .5f) / height * 2f - 1f);
        texture.SetPixels32(colors); texture.Apply(false, true);
        var sprite = Sprite.Create(texture, new Rect(0, 0, width, height), new Vector2(.5f, .5f), width);
        sprite.hideFlags = HideFlags.HideAndDontSave;
        _owned.Add(sprite); _owned.Add(texture);
        return sprite;
    }

    private static bool Inside(Vector2[] poly, Vector2 p)
    {
        if (poly == null || poly.Length < 3) return false;
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if ((poly[i].y > p.y) != (poly[j].y > p.y) &&
                p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x) inside = !inside;
        return inside;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        ClearTrails();
        foreach (var rack in _racks)
            if (rack.Sr != null) rack.Sr.color = new Color(rack.Original.r, rack.Original.g, rack.Original.b, rack.Sr.color.a);
        if (_root != null) Object.Destroy(_root.gameObject);
        foreach (var asset in _owned) if (asset != null) Object.Destroy(asset);
        _owned.Clear();
        if (Current == this) Current = null;
    }
}
