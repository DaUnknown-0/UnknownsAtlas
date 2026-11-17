// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
// Amberhive: rein lokale Atmosphaere, ohne Netzwerk oder Spieler-Ortung.

using System;
using System.Collections.Generic;
using BepInEx.Configuration;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal sealed class AtlasAmberhiveSound : IDisposable
{
    private const string Prefix = "[Atlas/Amberhive/Sound]";
    private const float MixLimit = .24f;
    private static ConfigEntry<bool> _enabled;
    private static ConfigEntry<int> _volume;
    private static AtlasAmberhiveSound _current;

    private readonly HiveData _hive;
    private readonly bool _twoFloors;
    private readonly Voice[] _voices;
    private bool _ended, _disposed, _faulted;

    private sealed class Voice
    {
        internal readonly string Name;
        internal readonly Vector2[] Points;
        internal readonly float Near, Far, Gain;
        internal AudioClip Clip;
        internal AudioSource Source;
        internal float Level, Target;
        internal bool Failed;

        internal Voice(string name, Vector2[] points, float near, float far, float gain)
        { Name = name; Points = points; Near = near; Far = far; Gain = gain; }
    }

    internal static void Bind(ConfigFile config)
    {
        _enabled = config.Bind("Amberhive Sound", "Enabled", true,
            "Lokale Amberhive-Klangkulisse. Nur dieser Client, keine Host-Option.");
        _volume = config.Bind("Amberhive Sound", "Volume", 60,
            new ConfigDescription("Lokale Lautstaerke von 0 bis 100 Prozent. 0 schaltet die Klangkulisse aus. " +
                "Zusaetzlich gilt die Effektlautstaerke des Spiels.", new AcceptableValueRange<int>(0, 100)));
        // Config.Reload() und lokale Config-UIs wirken ohne neue Runde. Auf dem Hauptthread stoppen.
    }

    internal AtlasAmberhiveSound(AtlasMapDef map, HiveData hive, bool twoFloors)
    {
        _current?.Dispose();
        _current = this;
        _hive = hive;
        _twoFloors = twoFloors;
        var rooms = new List<Vector2>();
        if (map.Rooms != null)
            foreach (var room in map.Rooms)
                if (room.Area != null && room.Area.Length > 0) rooms.Add(Center(room.Area));
        rooms.Add(hive.PitCenter);
        var brood = new List<Vector2>(Anchors(map, "queen_throne", "queen"));
        brood.AddRange(Anchors(map, "brood_cradle", "nursery"));
        _voices = new[]
        {
            new Voice("hive_buzz", rooms.ToArray(), 0f, 9f, .032f),
            new Voice("brood_buzz", brood.ToArray(), 1.6f, 7f, .13f),
            new Voice("honey_well", new[] { hive.PitCenter }, 2.5f, 8f, .15f),
            new Voice("bellows", Anchors(map, "bellows_big", "bellows"), 1.5f, 6.5f, .13f),
            new Voice("nectar_press", Anchors(map, "nectar_press", "wpress", "epress"), 1.5f, 6.5f, .12f),
            new Voice("wax_foundry", Anchors(map, "wax_cauldron", "foundry"), 1.5f, 6.5f, .13f),
            new Voice("mead_chimes", new[] { map.EmergencyButton }, 1f, 7f, .06f),
            new Voice("bridge_turn", new[] { hive.PitCenter }, 2.5f, 8f, .14f),
            new Voice("honey_flood", Array.Empty<Vector2>(), .5f, 6f, .14f),
            new Voice("nectar_chute", Array.Empty<Vector2>(), 0f, 1f, .12f),
        };
        AtlasPlugin.Logger.LogInfo($"{Prefix} bereit: 10 Klangtypen, lokal, Standard 60 Prozent");
    }

    // Quellen folgen den aktuellen Karten-/Propdaten, auch nach Layoutaenderungen.
    // Mehrere Quellen eines Typs ergeben genau EINE Stimme mit dem staerksten Naehepegel.
    private static Vector2[] Anchors(AtlasMapDef map, string kind, params string[] roomKeys)
    {
        var points = new List<Vector2>();
        if (map.Props != null)
            foreach (var p in map.Props)
                if (p.Kind == kind) points.Add(new Vector2((p.FootX0 + p.FootX1) * .5f, p.BaseY));
        if (points.Count == 0 && map.Rooms != null)
            foreach (var room in map.Rooms)
                if (Array.IndexOf(roomKeys, room.Key) >= 0 && room.Area != null && room.Area.Length > 0)
                    points.Add(Center(room.Area));
        return points.ToArray();
    }

    private static Vector2 Center(Vector2[] polygon)
    {
        var sum = Vector2.zero;
        foreach (var p in polygon) sum += p;
        return sum / polygon.Length;
    }

    private bool CanPlay()
    {
        if (_disposed || _ended || _faulted || _enabled?.Value != true || (_volume?.Value ?? 0) <= 0) return false;
        if (!AtlasMuseumBuilder.Active || AtlasMuseumBuilder.D?.Key != AtlasAmberhive.Key) return false;
        if (MeetingHud.Instance != null || ExileController.Instance != null) return false;
        var client = AmongUsClient.Instance;
        if (client == null || PlayerControl.LocalPlayer == null || PlayerControl.LocalPlayer.Data == null) return false;
        if (client.GameState == InnerNet.InnerNetClient.GameStates.Ended) return false;
        return client.NetworkMode == NetworkModes.FreePlay || client.GameState == InnerNet.InnerNetClient.GameStates.Started;
    }

    internal void Tick(float dt, bool bridgeTurning, int floodZone, float floodLevel, bool sliding)
    {
        if (!CanPlay() || SoundManager.Instance == null) { Silence(); return; }
        try
        {
            var listener = PlayerControl.LocalPlayer.GetTruePosition();
            // Fuer Weltmechaniken nur ihren bestehenden Zustand lesen. Keine neuen RPCs.
            for (int i = 0; i < _voices.Length; i++)
            {
                var v = _voices[i];
                float attenuation = 0f;
                if (i == 8)
                {
                    if (floodZone >= 0 && floodZone < _hive.FloodZones.Count && floodLevel > 0f)
                        attenuation = Falloff(DistanceToArea(listener, _hive.FloodZones[floodZone]), v.Near, v.Far) * Mathf.Clamp01(floodLevel);
                }
                else if (i == 9) attenuation = _twoFloors && _hive.HasChute && sliding ? 1f : 0f;
                else if (i != 7 || bridgeTurning)
                    foreach (var p in v.Points)
                        attenuation = Mathf.Max(attenuation, Falloff(Vector2.Distance(listener, p), v.Near, v.Far));
                v.Target = v.Gain * attenuation;
                // Kurze Fahrtgeraeusche beginnen schneller als der Raumton.
                float rate = i >= 7 ? .6f : .18f;
                v.Level = Mathf.MoveTowards(v.Level, v.Target, Mathf.Clamp(dt, 0f, .1f) * rate);
                // Auch Mechaniken kurz ausblenden, damit das Abschneiden der Welle nicht klickt.
            }
            float sum = 0f;
            foreach (var v in _voices) sum += v.Level;
            // Summe der tatsaechlich ausgeblendeten Pegel begrenzen, auch beim Raumwechsel.
            float gain = Mathf.Clamp01((_volume?.Value ?? 0) / 100f) * (sum > MixLimit ? MixLimit / sum : 1f);
            foreach (var v in _voices) UpdateSource(v, v.Level * gain);
        }
        catch (Exception e)
        {
            _faulted = true;
            Silence();
            AtlasPlugin.Logger.LogWarning($"{Prefix} fuer diese Runde angehalten: {e.Message}");
        }
    }

    internal static float Falloff(float distance, float near, float far)
    {
        float k = Mathf.Clamp01((distance - near) / Mathf.Max(.01f, far - near));
        return 1f - k * k * (3f - 2f * k);
    }

    // Flut ist eine Flaeche: innerhalb ueberall gleich laut, ausserhalb Abstand zum Rand.
    internal static float DistanceToArea(Vector2 p, Vector2[] polygon)
    {
        if (polygon == null || polygon.Length < 3) return float.PositiveInfinity;
        bool inside = false;
        float nearest = float.PositiveInfinity;
        for (int i = 0, j = polygon.Length - 1; i < polygon.Length; j = i++)
        {
            Vector2 a = polygon[j], b = polygon[i], edge = b - a;
            float u = edge.sqrMagnitude > .00001f ? Mathf.Clamp01(Vector2.Dot(p - a, edge) / edge.sqrMagnitude) : 0f;
            nearest = Mathf.Min(nearest, Vector2.Distance(p, a + edge * u));
            if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) inside = !inside;
        }
        return inside ? 0f : nearest;
    }

    private static void UpdateSource(Voice v, float volume)
    {
        if (v.Failed) return;
        if (volume <= .0005f) { Stop(v); return; }
        if (v.Clip == null)
        {
            try { v.Clip = Load(v.Name); }
            catch (Exception e)
            {
                v.Failed = true;
                AtlasPlugin.Logger.LogWarning($"{Prefix} {v.Name} nicht ladbar: {e.Message}");
                return;
            }
        }
        // Eine Stimme pro eindeutigem Clip. StopSound stoppt im Spiel clip-basiert.
        if (v.Source != null && !v.Source.isPlaying) Stop(v);
        if (v.Source == null)
        {
            v.Source = SoundManager.Instance.PlaySound(v.Clip, true, 0f, SoundManager.Instance.SfxChannel);
            if (v.Source == null) return;
            v.Source.spatialBlend = 0f;
            v.Source.panStereo = 0f;
            v.Source.dopplerLevel = 0f;
            v.Source.priority = 220;
        }
        v.Source.volume = volume;
    }

    private static AudioClip Load(string name)
    {
        using var stream = typeof(AtlasAmberhiveSound).Assembly.GetManifestResourceStream($"{AtlasAmberhive.Ns}.sound.{name}.ogg");
        if (stream == null) throw new InvalidOperationException("Eingebetteter Vorbis-Clip fehlt");
        using var decoder = new NVorbis.VorbisReader(stream, false);
        long frames = decoder.TotalSamples;
        int channels = decoder.Channels, rate = decoder.SampleRate;
        if (frames < 1 || frames > 30L * 48000 || channels != 1 || rate != 24000)
            throw new InvalidOperationException("Unerwartetes Audioformat");
        var samples = new float[checked((int)frames * channels)];
        int offset = 0;
        while (offset < samples.Length)
        {
            int read = decoder.ReadSamples(samples, offset, samples.Length - offset);
            if (read <= 0) throw new InvalidOperationException($"Vorbis unvollstaendig: {offset}/{samples.Length}");
            offset += read;
        }
        AudioClip clip = null;
        try
        {
            clip = AudioClip.Create("atlas_amberhive_" + name, (int)frames, channels, rate, false);
            clip.hideFlags |= HideFlags.HideAndDontSave;
            ClipFill.SetData(clip, samples, channels);
            return clip;
        }
        catch
        {
            if (clip != null) Object.Destroy(clip);
            throw;
        }
    }

    private static void Stop(Voice v)
    {
        var source = v.Source;
        if (source == null) { v.Source = null; return; }
        // Den SoundManager-eigenen AudioSource nicht zerstoeren.
        try { source.volume = 0f; source.Stop(); } catch { }
        try { if (SoundManager.Instance != null && v.Clip != null) SoundManager.Instance.StopSound(v.Clip); } catch { }
        v.Source = null;
    }

    private void Silence()
    {
        if (_voices == null) return;
        foreach (var v in _voices) { Stop(v); v.Level = v.Target = 0f; }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Silence();
        foreach (var v in _voices)
        {
            if (v.Clip != null) Object.Destroy(v.Clip);
            v.Clip = null;
        }
        if (ReferenceEquals(_current, this)) _current = null;
    }

    // Auch dann sofort still, wenn nach Meeting/Rundenende kein Welt-Tick mehr kommt.
    [HarmonyPatch]
    private static class Lifecycle
    {
        [HarmonyPrefix, HarmonyPatch(typeof(MeetingHud), nameof(MeetingHud.Start))]
        private static void Meeting() => _current?.Silence();

        [HarmonyPrefix, HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnGameEnd))]
        private static void End()
        {
            if (_current == null) return;
            _current._ended = true;
            _current.Silence();
        }

        [HarmonyPostfix, HarmonyPriority(Priority.Last), HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
        private static void Watchdog()
        {
            if (_current != null && !_current.CanPlay()) _current.Silence();
        }
    }
}
