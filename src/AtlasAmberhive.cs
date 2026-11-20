// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasAmberhive - "Amberhive" (User 15.11.: eigene Karte, komplett frei gestaltet): eine Imkerei-Station in einem riesigen
// Bienenstock. Kartendateien tools/hive/gen_hive.py -> assets/amberhive/amberhive_1f.json und amberhive_2f.json, eingebettet
// als "UnknownsAtlas.Maps.amberhive.*". Keine ".map.json", damit AtlasMapFile sie nicht selbst anmeldet: hier waehlt die
// Host-Option "Amberhive Floors" (1729, AtlasVanillaOptions) vor jedem Bau die Fassung (1 Etage / 2 Etagen mit der Krone).
//
// Welt (AmberhiveWorld, Netz ueber AtlasWorld Op 24 "Hive" [sub][...], Host-autoritativ):
//   - Drehbruecke im Honigbrunnen: der Honigsee ist gesperrt bis auf die Bruecke; sie verbindet abwechselnd Nord-Sued und
//     West-Ost, dazwischen dreht sie sich (gesperrt). Sub 0 Bridge [phase] (Host -> alle).
//   - Honigflut: in Abstaenden laeuft Honig in einen von vier Gaengen; wer darin steht, laeuft langsamer. Sub 1 Flood [zone].
//   - Nektarrutsche (nur 2 Etagen): Einbahn von der Krone in den Brunnenring (nur der eigene Spieler, wie AtlasStairs).
// Kartendaten der Mechaniken stehen im Abschnitt "hive" der Kartendatei (Atlas liest ihn nicht).

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HarmonyLib;
using Hazel;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

internal static class AtlasAmberhive
{
    internal const string Key = "amberhive";
    internal const string Ns = "UnknownsAtlas.Maps.amberhive";
    internal const byte OpHive = 24;   // 22/23 = AtlasTaskDefer
    private const string LogPrefix = "[Atlas/Amberhive]";

    private static string _json1, _json2;

    internal static void Register()
    {
        var asm = typeof(AtlasAmberhive).Assembly;
        _json1 = Read(asm, "amberhive_1f.json");
        _json2 = Read(asm, "amberhive_2f.json");
        if (_json1 == null) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} not embedded in this build"); return; }
        var probe = AtlasMapFile.Read(_json1, asm, Ns);
        bool ok = AtlasMaps.Register(Key, probe.DisplayName ?? "Amberhive", Make, asm, Ns,
            Has(asm, "button_amberhive.png") ? "button_amberhive.png" : null,
            Has(asm, "icon_amberhive.png") ? "icon_amberhive.png" : null,
            "file:" + Hash(asm));
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {(ok ? "registered" : "NOT registered")} ({probe.Rooms?.Length ?? 0} rooms, " +
                                   $"2 floors {(_json2 != null ? "available" : "missing")})");
    }

    private static AtlasMapDef Make()
    {
        bool two = _json2 != null && AtlasVanillaOptions.AmberhiveFloors() == 1;
        var asm = typeof(AtlasAmberhive).Assembly;
        string json = two ? _json2 : _json1;
        var d = AtlasMapFile.Read(json, asm, Ns);
        d.World = new AmberhiveWorld(two, HiveData.Parse(json), d);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} building with {(two ? "2 floors (Crown)" : "1 floor")}");
        return d;
    }

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        AmberhiveWorld.Current?.Receive(from, fromHost, sub, r);
    }

    private static string Read(Assembly asm, string file)
    {
        var s = asm.GetManifestResourceStream($"{Ns}.{file}");
        if (s == null) return null;
        using (s) using (var r = new StreamReader(s, Encoding.UTF8)) return r.ReadToEnd();
    }

    private static bool Has(Assembly a, string file)
    {
        try { return a.GetManifestResourceInfo($"{Ns}.{file}") != null; } catch { return false; }
    }

    private static string Hash(Assembly asm)
    {
        using var sha = SHA256.Create();
        foreach (var n in asm.GetManifestResourceNames().Where(n => n.StartsWith(Ns + ".", StringComparison.Ordinal)).OrderBy(n => n, StringComparer.Ordinal))
        {
            var b = Encoding.UTF8.GetBytes(n);
            sha.TransformBlock(b, 0, b.Length, null, 0);
            using var s = asm.GetManifestResourceStream(n);
            using var ms = new MemoryStream();
            s.CopyTo(ms);
            var d = ms.ToArray();
            sha.TransformBlock(d, 0, d.Length, null, 0);
        }
        sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
        return BitConverter.ToString(sha.Hash).Replace("-", "").ToLowerInvariant();
    }
}

/// <summary>Abschnitt "hive" der Kartendatei: Lage der Mechaniken.</summary>
internal sealed class HiveData
{
    public Vector2 PitCenter; public float PitRadius = 2.55f, BridgeWidth = 1.7f, BridgeLength = 6.4f;
    public float OpenSeconds = 22f, TurnSeconds = 2.5f, BridgeWarning = 3f;
    public List<Vector2[]> FloodZones = new();
    public float FloodFirst = 40f, FloodGapMin = 45f, FloodGapMax = 65f, FloodWarning = 2.5f,
        FloodRise = 2f, FloodHold = 10f, FloodDrain = 2.5f, FloodSlow = 0.7f;
    public Vector2 ChuteTop, ChuteBottom, ChuteExit;
    public bool HasChute;
    /// <summary>Animierte Objektarten: Art -> Bildzahl (task_hive_anim_<art>_<k>.png).</summary>
    public Dictionary<string, int> Anim = new();

    internal static HiveData Parse(string json)
    {
        var h = new HiveData();
        try
        {
            using var doc = JsonDocument.Parse(json, new JsonDocumentOptions { AllowTrailingCommas = true, CommentHandling = JsonCommentHandling.Skip });
            if (!doc.RootElement.TryGetProperty("hive", out var e)) return h;
            Vector2 V(JsonElement a) => new(a[0].GetSingle(), a[1].GetSingle());
            float F(string n, float def) => e.TryGetProperty(n, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetSingle() : def;
            if (e.TryGetProperty("pit", out var pit)) { h.PitCenter = new Vector2(pit[0].GetSingle(), pit[1].GetSingle()); h.PitRadius = pit[2].GetSingle(); }
            h.BridgeWidth = F("bridgeWidth", h.BridgeWidth); h.BridgeLength = F("bridgeLength", h.BridgeLength);
            h.OpenSeconds = F("openSeconds", h.OpenSeconds); h.TurnSeconds = F("turnSeconds", h.TurnSeconds);
            h.BridgeWarning = F("bridgeWarning", h.BridgeWarning); h.FloodWarning = F("floodWarning", h.FloodWarning);
            h.FloodFirst = F("floodFirst", h.FloodFirst); h.FloodGapMin = F("floodGapMin", h.FloodGapMin); h.FloodGapMax = F("floodGapMax", h.FloodGapMax);
            h.FloodRise = F("floodRise", h.FloodRise); h.FloodHold = F("floodHold", h.FloodHold); h.FloodDrain = F("floodDrain", h.FloodDrain);
            h.FloodSlow = F("floodSlow", h.FloodSlow);
            if (e.TryGetProperty("floodZones", out var zs))
                foreach (var z in zs.EnumerateArray()) h.FloodZones.Add(z.EnumerateArray().Select(V).ToArray());
            if (e.TryGetProperty("anim", out var an) && an.ValueKind == JsonValueKind.Object)
                foreach (var p in an.EnumerateObject()) h.Anim[p.Name] = p.Value.GetInt32();
            if (e.TryGetProperty("chute", out var ch) && ch.ValueKind == JsonValueKind.Array && ch.GetArrayLength() >= 3)
            {
                h.ChuteTop = V(ch[0]); h.ChuteBottom = V(ch[1]); h.ChuteExit = V(ch[2]); h.HasChute = true;
            }
        }
        catch (Exception ex) { AtlasPlugin.Logger.LogWarning($"[Atlas/Amberhive] hive data: {ex.Message}"); }
        return h;
    }
}

internal sealed class AmberhiveWorld : IAtlasMapWorld
{
    private const string LogPrefix = "[Atlas/Amberhive]";
    internal static AmberhiveWorld Current;

    private readonly bool _two;
    private readonly HiveData _h;
    private Transform _root;

    // Drehbruecke: Phase 0 = Nord-Sued offen, 1 = Drehung nach West-Ost, 2 = West-Ost offen, 3 = Drehung zurueck
    private int _phase;
    private float _phaseT0, _hostNext;
    private float _clock, _nextSync;
    private int _entrySign, _entryPhase = -1, _lastFlood = -1;
    private GameObject _pitGo;
    private PolygonCollider2D _pitCol;
    private Transform _bridge;
    private SpriteRenderer _bridgeSr;

    // Honigflut
    private int _floodZone = -1;
    private float _floodT0, _hostFloodAt;
    private readonly List<SpriteRenderer> _floodSr = new();
    internal static float SlowFactor = 1f;

    // animierte Objekte: Renderer + Bilder
    private readonly List<(SpriteRenderer Sr, Sprite[] Frames, float Fps, float Phase)> _anims = new();

    // Rutsche
    private float _chuteT0 = -1f;
    private bool _chuteMoved;
    private float _chutePendingUntil;
    private readonly Dictionary<byte, float> _chuteCooldown = new();
    private SpriteRenderer _veil;

    private readonly AtlasMapDef _def;
    private AtlasAmberhiveSound _sound; // Amberhive sound

    public AmberhiveWorld(bool two, HiveData h, AtlasMapDef def) { _two = two; _h = h; _def = def; }

    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;

    public void OnBuilt(Transform worldRoot)
    {
        Current = this;
        // AtlasWorld liegt unter dem 1,2-fach skalierten Ship, Mechaniken brauchen Weltmeter.
        var go = new GameObject("Atlas_Amberhive");
        go.transform.SetParent(worldRoot, false);
        var scale = worldRoot.lossyScale;
        go.transform.localScale = new Vector3(1f / scale.x, 1f / scale.y, 1f / scale.z);
        go.transform.position = Vector3.zero;
        _root = go.transform;
        _clock = 0f; _phase = 0; _phaseT0 = 0f; _hostNext = _h.OpenSeconds;
        _hostFloodAt = _h.FloodFirst;
        BuildPit();
        BuildFlood();
        _animFrames = LoadAnimFrames();
        BuildBees();
        _life = new AtlasAmberhiveLife(_root, _def, p => _floodZone >= 0 && FloodLevel() > .35f && Inside(_h.FloodZones[_floodZone], p)); // AMBERHIVE LIFE
        _sound = new AtlasAmberhiveSound(_def, _h, _two); // Amberhive sound
        bool test = AtlasMapShot.AutotestRun;
        string testKind = AtlasPlugin.CfgTaskTest?.Value?.Split(',')[0].Trim();
        _sabDiag = test && string.Equals(testKind, "hivesab", StringComparison.OrdinalIgnoreCase);
        _diag = _sabDiag || test && string.Equals(testKind, "hive", StringComparison.OrdinalIgnoreCase);
        _diagT0 = Time.time + 6f; _diagStep = 0;
        _clip = test && string.Equals(AtlasPlugin.CfgTaskTest?.Value, "hiveclip", StringComparison.OrdinalIgnoreCase);
        _clipNext = Time.time + 6f; _clipStage = 0;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} world ready: bridge, {_h.FloodZones.Count} flood zones, chute {(_two && _h.HasChute ? "on" : "off")}");
    }

    public void OnDestroy()
    {
        _life?.Dispose(); _life = null; // AMBERHIVE LIFE
        _sound?.Dispose(); _sound = null; // Amberhive sound
        if (Current == this) Current = null;
        if (_chuteT0 >= 0f) EndChute(PlayerControl.LocalPlayer);
        if (_clip) { LockCam(null); Time.captureFramerate = 0; }
        SlowFactor = 1f;
        if (_veil != null) { try { Object.Destroy(_veil.gameObject); } catch { } }
        _veil = null;
    }

    public float VisionFactor(Vector2 pos) => 1f;

    private AtlasAmberhiveLife _life; // AMBERHIVE LIFE: ausschliesslich eigene Implementierungsdatei.

    public void Tick(float dt)
    {
        if (_root == null) return;
        if (MeetingHud.Instance == null && ExileController.Instance == null) _clock += Mathf.Max(0f, dt);
        if (AmHost) HostTick();
        if (MeetingHud.Instance != null || ExileController.Instance != null)
            _pendingBodies.Clear();
        else if (Time.time >= _nextBodyCheck && (_pendingBodies.Count > 0 || (AmHost && _phase % 2 == 1)))
        {
            _nextBodyCheck = Time.time + 0.25f;
            if (AmHost) ClearBridgeBodies();
            else ApplyPendingBodies();
        }
        TickBridge();
        TickFlood();
        if (_animFrames != null && _anims.Count == 0 && Time.frameCount % 30 == 0) BindAnims();
        TickAnims();
        _life?.Tick(dt); // AMBERHIVE LIFE: vor den Bienen, nach den uebrigen Animationen.
        TickBees(dt);
        if (_two && _h.HasChute) TickChute();
        _sound?.Tick(dt, _phase % 2 == 1, _floodZone, FloodLevel(), _chuteT0 >= 0f); // Amberhive sound
        if (_diag) TickDiag();
        if (_clip) TickClip();
    }

    // Aufnahme fuer die Vorfuehrung (Diagnostics.TaskTest = "hiveclip"): Bildserien der drehenden Bruecke und der Flut
    private bool _clip;
    private float _clipNext;
    private int _clipStage, _clipN;

    // Ablauf als Schritte: (Aktion, Wartezeit danach). Ein Schritt mit Bildserie wiederholt sich selbst.
    // Foto und Teleport nie im selben Frame: CaptureScreenshot liest erst am Frame-Ende.
    private void TickClip()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || Time.time < _clipNext) return;
        void Next(float wait) { _clipStage++; _clipNext = Time.time + wait; _clipN = 0; }
        bool Series(string name, int count, float gap)
        {
            Time.captureFramerate = 20;                  // Spielzeit pro Bild fest 1/20 s, Speichern bremst nicht
            Shot($"clip_{name}_{_clipN:D3}"); _clipN++; _clipNext = Time.time + gap;
            bool done = _clipN >= count;
            if (done) Time.captureFramerate = 0;
            return done;
        }
        var well = new Vector2(0f, 0.4f);
        switch (_clipStage)
        {
            case 0: Snap(new Vector2(-3.8f, 0.2f)); LockCam(well); Next(2f); break;
            case 1: if (AmHost) _hostNext = _clock; Next(0f); break;
            case 2: LockCam(well); if (Series("bridge", 90, 0.01f)) Next(0.3f); break;
            case 3: LockCam(null); Snap(new Vector2(-11.5f, 0.6f)); Next(1.5f); break;
            case 4: if (AmHost) Broadcast(1, 0); Next(0f); break;
            case 5: if (Series("flood", 80, 0.01f)) { _tourI = 0; _clipStage = 20; _clipNext = Time.time + 0.3f; } break;
            case 20: Snap(Tour[_tourI].Item2); _clipStage = 21; _clipNext = Time.time + 1.3f; break;
            case 21:
                Shot($"clip_room_{Tour[_tourI].Item1}"); _tourI++;
                _clipStage = _tourI < Tour.Length ? 20 : (_two ? 6 : 99); _clipNext = Time.time + 0.3f;
                break;
            case 6: Snap(new Vector2(0f, 23.0f)); Next(1.4f); break;
            case 7: Shot("clip_crown_archive"); Next(0.3f); break;
            case 8: Snap(new Vector2(-10.5f, 23.0f)); Next(1.4f); break;
            case 9: Shot("clip_crown_sundeck"); Next(0.3f); break;
            case 10: Snap(new Vector2(10.5f, 23.0f)); Next(1.4f); break;
            case 11: Shot("clip_crown_dock"); Next(0.3f); break;
            case 12: Snap(new Vector2(0f, 14.6f)); Next(1.4f); break;
            case 13: Shot("clip_stairs"); Next(0.3f); break;
            case 14: Snap(new Vector2(3.0f, 25.7f)); Next(1.4f); break;
            case 15: if (_h.HasChute) { _chuteT0 = Time.time; _chuteMoved = false; lp.moveable = false; } Next(0f); break;
            case 16: if (Series("chute", 70, 0.01f)) _clipStage = 99; break;
            default: LockCam(null); Time.captureFramerate = 0; _clip = false; AtlasPlugin.Logger.LogInfo($"{LogPrefix} clip done"); break;
        }
    }

    private int _tourI;
    private static readonly (string, Vector2)[] Tour =
    {
        ("mead", new Vector2(-2.5f, 9.0f)), ("queen", new Vector2(0f, -9.0f)), ("cellar", new Vector2(-9f, 6.5f)),
        ("keeper", new Vector2(9f, 6.5f)), ("bellows", new Vector2(-9f, -5.5f)), ("nursery", new Vector2(9f, -6.5f)),
        ("lamp", new Vector2(-17.2f, 0f)), ("foundry", new Vector2(17.2f, 0f)), ("guard", new Vector2(-17.2f, 10f)),
        ("waggle", new Vector2(17.2f, 10f)), ("wpress", new Vector2(-17.2f, -10.2f)), ("epress", new Vector2(17.2f, -10.2f)),
        ("wasp", new Vector2(-9.4f, -14.4f)), ("sun", new Vector2(9.2f, -14f)),
    };

    private void LockCam(Vector2? at)
    {
        try
        {
            var cam = Camera.main;
            var fc = cam != null ? cam.GetComponent<FollowerCamera>() : null;
            if (fc == null) return;
            fc.enabled = at == null;
            if (at != null) cam.transform.position = new Vector3(at.Value.x, at.Value.y, cam.transform.position.z);
        }
        catch { }
    }

    // ------------------------------------------------------------------ Autotest (Diagnostics.TaskTest = "hive")

    private bool _diag;
    internal bool DiagnosticsRunning => _diag || _clip;
    private float _diagT0;
    private int _diagStep;

    private void Shot(string name)
    {
        try
        {
            string dir = System.IO.Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
            System.IO.Directory.CreateDirectory(dir);
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, $"hive_{name}.png"));
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag shot: {e.Message}"); }
    }

    private void Snap(Vector2 p)
    {
        var lp = PlayerControl.LocalPlayer;
        try { lp.NetTransform.RpcSnapTo(p + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
    }

    private Vector2 Me => PlayerControl.LocalPlayer != null ? PlayerControl.LocalPlayer.GetTruePosition() : Vector2.zero;

    private void TickDiag()
    {
        if (_sabDiag) { TickSabDiag(); return; }
        float el = Time.time - _diagT0;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        int idx = 0;
        void Step(float at, Action a)
        {
            int me = idx++;
            if (_diagStep != me || el < at) return;
            _diagStep++;
            try { a(); } catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag {at}: {e.Message}"); }
        }
        void Check(bool ok, string label)
        {
            if (!ok) _diagFailures++;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} CHECK {(ok ? "PASS" : "FAIL")} {label}: {DiagState()}, player ({Me.x:F2}|{Me.y:F2})");
        }
        Step(0, () => {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag start: {DiagState()}");
            Check(Mathf.Abs(_root.lossyScale.x - 1f) < 0.001f, "world meters");
            Check(Mathf.Abs(_pitCol.bounds.size.x - 2f * _h.PitRadius) < 0.08f, "pit collider matches lake");
        });
        Step(1, () => Snap(new Vector2(0f, 3.4f)));
        Step(2, () => Shot("well"));
        Step(3, () => { Snap(new Vector2(3.3f,.2f)); Probe(new Vector2(1.7f,.2f), .9f); });
        Step(4, () => Check(Me.x > _h.PitRadius + .1f && Me.x < 3.2f, "pit blocks physical entry"));
        Step(5, () => Snap(new Vector2(0f, 1f)));
        Step(6, () => Check(Vector2.Distance(Me, new Vector2(0f,1f)) < 0.15f, "open bridge walkable"));
        Step(7, () => { if (AmHost) Broadcast(1, 0); Snap(new Vector2(-9.5f, 0f)); });
        Step(8, () => Check(Mathf.Abs(SlowFactor-1f) < .01f, "flood warning has no slow"));
        Step(12, () => { Shot("flood"); Check(Mathf.Abs(SlowFactor-_h.FloodSlow) < .02f, "flood slow active"); });
        Step(13, () => Snap(new Vector2(0f, 1f)));
        Step(14, () => { if (AmHost) _hostNext = _clock; });
        Step(15, () => { Shot("bridge_turn"); Check(_phase%2 == 1 && Me.y > _h.PitRadius+.2f, "turn returns to entry bank"); });
        Step(18, () => { Shot("bridge_we"); Check(_phase == 2, "bridge west-east open"); });
        Step(19, () => { if (_two && _h.HasChute) Snap(_h.ChuteTop); });
        Step(20, () => { if (_two && _h.HasChute) HostChute(lp); });
        Step(22, () => { if (_two && _h.HasChute) { Shot("chute_exit"); Check(Vector2.Distance(Me,_h.ChuteExit)<.15f && lp.moveable, "chute arrives and releases movement"); } });
        Step(23, () => { if (_two && _h.HasChute) { HostChute(lp); Check(_chuteT0 < 0f, "chute rejects request from bottom"); } });
        Step(24, () => Snap(new Vector2(0f, 9f)));
        Step(25, () => Shot("mead"));
        Step(26, () => Snap(new Vector2(-17.2f, 0f)));
        Step(27, () => Shot("lamphouse"));
        Step(28, () => Snap(new Vector2(0f, -9f)));
        Step(29, () => Shot("queen"));
        Step(30, () => { if (_two) Snap(new Vector2(0f, 23f)); });
        Step(31, () => { if (_two) Shot("crown"); });
        Step(32, () => { if (_two) AtlasStairs.Diag("stairs:0", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(34, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[0].B)<.15f && lp.moveable, "stairs 0 up"); });
        Step(35, () => { if (_two) AtlasStairs.Diag("stairsback:0", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(37, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[0].A)<.15f && lp.moveable, "stairs 0 down"); });
        Step(38, () => { if (_two) AtlasStairs.Diag("stairs:1", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(40, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[1].B)<.15f && lp.moveable, "stairs 1 up"); });
        Step(41, () => { if (_two) AtlasStairs.Diag("stairsback:1", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(43, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[1].A)<.15f && lp.moveable, "stairs 1 down"); });
        Step(44, () => { if (_two) AtlasStairs.Diag("stairs:2", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(46, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[2].B)<.15f && lp.moveable, "stairs 2 up"); });
        Step(47, () => { if (_two) AtlasStairs.Diag("stairsback:2", p => lp.NetTransform.RpcSnapTo(p)); });
        Step(49, () => { if (_two) Check(Vector2.Distance(Me,_def.Stairs[2].A)<.15f && lp.moveable, "stairs 2 down"); });
        Step(50, () => Snap(new Vector2(10.9f,8.05f)));
        Step(51, () => Probe(new Vector2(16f,9.4f), 3f));
        Step(54, () => { Shot("keeper_waggle"); Check(Vector2.Distance(Me,new Vector2(16f,9.4f)) < .25f, "walk Keeper to Waggle"); });
        Step(55, () => Probe(new Vector2(10.9f,8.05f), 3f));
        Step(58, () => Check(Vector2.Distance(Me,new Vector2(10.9f,8.05f)) < .25f, "walk Waggle to Keeper"));
        Step(59, () => Snap(new Vector2(2f,-14.55f)));
        Step(60, () => Probe(new Vector2(7f,-14.55f), 3f));
        Step(63, () => { Shot("queen_sun"); Check(Vector2.Distance(Me,new Vector2(7f,-14.55f)) < .25f, "walk Queen to Sun"); });
        Step(64, () => Probe(new Vector2(2f,-14.55f), 3f));
        Step(67, () => Check(Vector2.Distance(Me,new Vector2(2f,-14.55f)) < .25f, "walk Sun to Queen"));
        Step(68, () => Snap(new Vector2(-15.2f,-13.3f)));
        Step(69, () => Probe(new Vector2(-12.4f,-13.4f), 2f));
        Step(71, () => { Shot("west_press_wasp"); Check(Vector2.Distance(Me,new Vector2(-12.4f,-13.4f)) < .25f, "walk West Press to Wasp"); });
        Step(72, () => { AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag done: {_diagFailures} failure(s), {DiagState()}"); _diag = false; });
    }

    private int _diagFailures;
    private bool _sabDiag;

    private void TickSabDiag()
    {
        float el = Time.time - _diagT0;
        int idx = 0;
        void Step(float at, Action act)
        {
            if (_diagStep != idx++ || el < at) return;
            _diagStep++;
            try { act(); }
            catch (Exception e) { _diagFailures++; AtlasPlugin.Logger.LogWarning($"{LogPrefix} sabotage diag: {e}"); }
        }
        void Check(bool ok, string what)
        {
            if (!ok) _diagFailures++;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} CHECK {(ok ? "PASS" : "FAIL")} sabotage {what}");
        }
        void Start(SystemTypes type, string key)
        {
            var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
            if (sab != null) { sab.Timer = 0f; sab.IsDirty = true; }
            SabKit.Send(SystemTypes.Sabotage, (int)type);
            Snap(_def.Consoles[key] + Vector2.down * .65f);
        }
        void Open(string key)
        {
            var pos = _def.Consoles[key];
            var con = ShipStatus.Instance.AllConsoles.FirstOrDefault(c => c != null && Vector2.Distance(c.transform.position, pos) < .1f);
            Check(con != null, key + " exists");
            con?.Use();
        }
        void Close() { if (Minigame.Instance != null) Minigame.Instance.ForceClose(); }
        Step(0, () => Start(SystemTypes.Electrical, "Electrical/SwitchConsole/0"));
        Step(1, () => Snap(new Vector2(0f,3.4f)));
        Step(1.5f, () => Shot("well_lights_dark"));
        Step(2, () => { Check(AtlasWorld.LightsOut(), "lights started"); Snap(_def.Consoles["Electrical/SwitchConsole/0"] + Vector2.down*.65f); Open("Electrical/SwitchConsole/0"); });
        Step(3, () => { Check(Minigame.Instance != null, "lights panel opens"); Shot("sab_lights"); });
        Step(4, () => { Close(); var sw = SabKit.Sys<SwitchSystem>(SystemTypes.Electrical); for (int i=0; i<5; i++) if (((sw.ActualSwitches ^ sw.ExpectedSwitches) & (1<<i)) != 0) SabKit.Send(SystemTypes.Electrical,i); });
        Step(6, () => Check(!AtlasWorld.LightsOut(), "lights repaired"));
        Step(8, () => Start(SystemTypes.Comms, "Comms/FixCommsConsole/0"));
        Step(10, () => { Check(SabKit.Sys<HudOverrideSystemType>(SystemTypes.Comms)?.IsActive == true, "comms started"); Open("Comms/FixCommsConsole/0"); });
        Step(11, () => { Check(Minigame.Instance != null, "comms panel opens"); Shot("sab_comms"); });
        Step(12, () => { Close(); SabKit.Send(SystemTypes.Comms,0); });
        Step(14, () => Check(SabKit.Sys<HudOverrideSystemType>(SystemTypes.Comms)?.IsActive == false, "comms repaired"));
        Step(16, () => Start(SystemTypes.LifeSupp, "LifeSupp/NoOxyConsole/0"));
        Step(18, () => { Check(SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp)?.IsActive == true, "oxygen started"); Open("LifeSupp/NoOxyConsole/0"); });
        Step(19, () => { Check(Minigame.Instance != null, "oxygen panel opens"); Shot("sab_oxygen"); });
        Step(20, () => { Close(); SabKit.Send(SystemTypes.LifeSupp,LifeSuppSystemType.AddUserOp); SabKit.Send(SystemTypes.LifeSupp,LifeSuppSystemType.AddUserOp | 1); });
        Step(22, () => Check(SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp)?.IsActive == false, "oxygen repaired"));
        Step(24, () => Start(SystemTypes.Reactor, "Reactor/UpperHandConsole/0"));
        Step(26, () => { Check(SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor)?.IsActive == true, "reactor started"); Open("Reactor/UpperHandConsole/0"); });
        Step(27, () => { Check(Minigame.Instance != null, "reactor panel opens"); Shot("sab_reactor"); });
        // Freeplay testet hier das Ruecksetzprotokoll. Die Zwei-Personen-Regel braucht einen Mehrspieler-Test.
        Step(28, () => { Close(); SabKit.Send(SystemTypes.Reactor,ReactorSystemType.ClearCountdown); });
        Step(30, () => Check(SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor)?.IsActive == false, "reactor reset"));
        Step(32, () => { AtlasPlugin.Logger.LogInfo($"{LogPrefix} sabotage diag done: {_diagFailures} failure(s)"); _diag = false; });
    }
    private Vector2 _probeTarget;
    private float _probeUntil;

    private void Probe(Vector2 target, float seconds)
    {
        _probeTarget = target; _probeUntil = Time.time + seconds;
    }

    // Diagnose bewegt mit dem echten Physikkoerper. Kein Teleport durch die zu pruefende Wand.
    internal void ProbePhysics(PlayerPhysics physics)
    {
        if (!_diag || Time.time >= _probeUntil || !AtlasMapShot.AutotestRun || !physics.AmOwner || physics.body == null) return;
        Vector2 delta = _probeTarget - Me;
        physics.body.velocity = delta.magnitude < .05f ? Vector2.zero : delta.normalized * Mathf.Min(2.2f, delta.magnitude / Time.fixedDeltaTime);
    }

    // ------------------------------------------------------------------ Host-Takt

    private void HostTick()
    {
        float now = _clock;
        if (now >= _hostNext)
        {
            int next = (_phase + 1) % 4;
            _hostNext = now + (next % 2 == 0 ? _h.OpenSeconds : _h.TurnSeconds);
            Broadcast(0, (byte)next);
        }
        if (now >= _hostFloodAt && _h.FloodZones.Count > 0)
        {
            // Keine direkte Wiederholung derselben Zone.
            int zone = Random.Range(0, _h.FloodZones.Count > 1 && _lastFlood >= 0 ? _h.FloodZones.Count - 1 : _h.FloodZones.Count);
            if (_h.FloodZones.Count > 1 && _lastFlood >= 0 && zone >= _lastFlood) zone++;
            _lastFlood = zone;
            _hostFloodAt = now + Random.Range(_h.FloodGapMin, _h.FloodGapMax);
            Broadcast(1, (byte)zone);
        }
        if (Time.time >= _nextSync)
        {
            _nextSync = Time.time + 2f;
            AtlasWorld.Send(AtlasAmberhive.OpHive, w =>
            {
                w.Write((byte)2); w.Write((byte)_phase); w.Write(_clock - _phaseT0);
                w.Write((byte)(_floodZone < 0 ? 255 : _floodZone)); w.Write(_clock - _floodT0);
                w.Write(Mathf.Max(0f, _hostFloodAt - _clock));
            });
        }
    }

    private void Broadcast(byte sub, byte arg)
    {
        Apply(sub, arg);
        AtlasWorld.Send(AtlasAmberhive.OpHive, w => { w.Write(sub); w.Write(arg); });
    }

    // Sub 0/1: Ereignisse; 2: regelmaessiger Host-Zustand; 3: Rutschenfreigabe; 4: Rutschenanfrage.
    internal void Receive(PlayerControl from, bool fromHost, byte sub, MessageReader r)
    {
        if (_life?.Receive(fromHost, sub, r) == true) return; // AMBERHIVE LIFE: Subs 16 bis 19.
        if (sub == 4) { if (AmHost) HostChute(from); return; }
        if (!fromHost) return;
        if (sub == 5)
        {
            byte id = r.ReadByte();
            _pendingBodies[id] = new Vector2(r.ReadSingle(), r.ReadSingle());
            ApplyPendingBodies();
            return;
        }
        if (sub == 2)
        {
            int phase = r.ReadByte(); float age = r.ReadSingle();
            int zone = r.ReadByte(); float floodAge = r.ReadSingle(), nextFlood = r.ReadSingle();
            if (phase > 3 || !float.IsFinite(age) || !float.IsFinite(floodAge) || !float.IsFinite(nextFlood)) return;
            if (_phase != phase) { _phase = phase; if (phase % 2 == 1) ClearBridge(); }
            _phaseT0 = _clock - Mathf.Max(0f, age);
            _hostNext = _phaseT0 + (phase % 2 == 0 ? _h.OpenSeconds : _h.TurnSeconds);
            _floodZone = zone < _h.FloodZones.Count ? zone : -1;
            if (_floodZone >= 0) _lastFlood = _floodZone;
            _floodT0 = _clock - Mathf.Max(0f, floodAge);
            _hostFloodAt = _clock + Mathf.Max(0f, nextFlood);
            return;
        }
        if (sub == 3)
        {
            byte pid = r.ReadByte();
            _life?.SuppressTransit(pid, 3f); // AMBERHIVE LIFE: keine Spuren auf der Rutsche.
            var lp = PlayerControl.LocalPlayer;
            if (lp != null && lp.PlayerId == pid && _two && _h.HasChute && AtlasUse.CanReach(lp, _h.ChuteTop, 1.35f)) BeginChute(lp);
            return;
        }
        if (sub <= 1) Apply(sub, r.ReadByte());
    }

    private void Apply(byte sub, byte arg)
    {
        switch (sub)
        {
            case 0:
                _phase = arg % 4; _phaseT0 = _clock;
                if (_phase % 2 == 1) ClearBridge();
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} bridge phase {_phase} ({(_phase == 0 ? "north-south" : _phase == 2 ? "west-east" : "turning")})");
                break;
            case 1:
                if (arg < _h.FloodZones.Count) { _floodZone = arg; _lastFlood = arg; _floodT0 = _clock; }
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} honey flood in zone {arg}");
                break;
        }
    }

    // ------------------------------------------------------------------ Drehbruecke

    /// <summary>Winkel der Bruecke in Grad (90 = Nord-Sued, 0 = West-Ost).</summary>
    private float BridgeAngle()
    {
        float k = Mathf.Clamp01((_clock - _phaseT0) / Mathf.Max(0.1f, _h.TurnSeconds));
        k = k * k * (3f - 2f * k);
        return _phase switch { 0 => 90f, 1 => 90f - 90f * k, 2 => 0f, _ => 90f * k };
    }

    private void BuildPit()
    {
        _pitGo = new GameObject("Atlas_HivePit") { layer = AtlasMuseumBuilder.LayerShip };
        _pitGo.transform.SetParent(_root, false);
        _pitGo.transform.position = new Vector3(_h.PitCenter.x, _h.PitCenter.y, 0f);
        _pitCol = _pitGo.AddComponent<PolygonCollider2D>();
        var go = new GameObject("Atlas_HiveBridge");
        go.transform.SetParent(_root, false);
        go.transform.position = new Vector3(_h.PitCenter.x, _h.PitCenter.y, AtlasMuseumBuilder.FloorZ - 0.6f);
        _bridge = go.transform;
        _bridgeSr = go.AddComponent<SpriteRenderer>();
        var spr = AtlasAssets.TaskSprite("task_hive_bridge.png", 100f, new Vector2(0.5f, 0.5f));
        if (spr != null)
        {
            _bridgeSr.sprite = spr;
            float s = _h.BridgeLength / spr.bounds.size.x;
            go.transform.localScale = new Vector3(s, s, 1f);
        }
        else
        {
            _bridgeSr.sprite = Solid(new Color32(150, 98, 44, 255));
            go.transform.localScale = new Vector3(_h.BridgeLength, _h.BridgeWidth, 1f);
        }
        AtlasMuseumBuilder.Mask(_bridgeSr);
        SetPitShape(90f, open: true);
    }

    private float _shapeAngle = -999f;
    private bool _shapeOpen;

    private void TickBridge()
    {
        if (_bridge == null) return;
        float a = BridgeAngle();
        _bridge.rotation = Quaternion.Euler(0f, 0f, a);
        bool open = _phase % 2 == 0;
        var lp = PlayerControl.LocalPlayer;
        if (open && lp != null && lp.Data != null && !lp.Data.IsDead)
        {
            var d = lp.GetTruePosition() - _h.PitCenter;
            var axis = _phase == 0 ? Vector2.up : Vector2.right;
            float along = Vector2.Dot(d, axis);
            float across = Mathf.Abs(d.x * axis.y - d.y * axis.x);
            if (Mathf.Abs(along) >= _h.PitRadius + 0.35f && across < _h.BridgeWidth / 2f + 0.4f)
            { _entrySign = along >= 0f ? 1 : -1; _entryPhase = _phase; }
        }
        float remaining = _h.OpenSeconds - (_clock - _phaseT0);
        bool warn = open && remaining <= _h.BridgeWarning;
        if (_bridgeSr != null)
            _bridgeSr.color = warn && Mathf.Sin(_clock * 10f) > 0f ? new Color(1f, 0.65f, 0.3f) : Color.white;
        if (open != _shapeOpen || Mathf.Abs(a - _shapeAngle) > 0.5f) SetPitShape(a, open);
    }

    /// <summary>Kollider des Honigsees: offen = Kreis ohne den Brueckenstreifen (zwei Teile), sonst der ganze Kreis.</summary>
    private void SetPitShape(float angle, bool open)
    {
        _shapeAngle = angle; _shapeOpen = open;
        if (_pitCol == null) return;
        const int n = 40;
        float r = _h.PitRadius, hw = _h.BridgeWidth / 2f;
        if (!open)
        {
            var pts = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<Vector2>(n);
            for (int i = 0; i < n; i++) { float t = 2f * Mathf.PI * i / n; pts[i] = new Vector2(r * Mathf.Cos(t), r * Mathf.Sin(t)); }
            _pitCol.pathCount = 1;
            _pitCol.SetPath(0, pts);
            return;
        }
        // Streifen entlang der Brueckenachse (Winkel angle): Punkte mit |Abstand zur Achse| > hw
        float ax = Mathf.Cos(angle * Mathf.Deg2Rad), ay = Mathf.Sin(angle * Mathf.Deg2Rad);
        Vector2 nrm = new(-ay, ax);
        float off = Mathf.Asin(Mathf.Clamp(hw / r, 0f, 0.99f));
        _pitCol.pathCount = 2;
        for (int side = 0; side < 2; side++)
        {
            // Bogen auf der Seite +nrm bzw. -nrm, von der einen Streifenkante zur anderen
            float baseAng = Mathf.Atan2(side == 0 ? nrm.y : -nrm.y, side == 0 ? nrm.x : -nrm.x);
            float half = Mathf.PI / 2f - off;
            var list = new List<Vector2>();
            int m = n / 2;
            for (int i = 0; i <= m; i++)
            {
                float t = baseAng - half + 2f * half * i / m;
                list.Add(new Vector2(r * Mathf.Cos(t), r * Mathf.Sin(t)));
            }
            var pts = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<Vector2>(list.Count);
            for (int i = 0; i < list.Count; i++) pts[i] = list[i];
            _pitCol.SetPath(side, pts);
        }
    }

    private float _nextBodyCheck;
    private readonly Dictionary<byte, Vector2> _pendingBodies = new();

    private static void MoveBody(DeadBody body, Vector2 target)
    {
        // TruePosition ist der Meldepunkt und kann vom Transform abweichen.
        Vector3 pos = body.transform.position + (Vector3)(target - body.TruePosition);
        pos.z = pos.y / 1000f;
        body.transform.position = pos;
    }

    private void ApplyPendingBodies()
    {
        // Die Killanimation kann beim Empfaenger noch laufen, wenn das Ziel eintrifft.
        foreach (var body in Object.FindObjectsOfType<DeadBody>())
            if (_pendingBodies.Remove(body.ParentId, out var dest)) MoveBody(body, dest);
    }

    private void ClearBridgeBodies()
    {
        var axis = _phase == 1 ? Vector2.up : Vector2.right;
        foreach (var body in Object.FindObjectsOfType<DeadBody>())
        {
            var delta = body.TruePosition - _h.PitCenter;
            if (delta.magnitude >= _h.PitRadius + 0.25f) continue;
            float sign = Vector2.Dot(delta, axis) >= 0f ? 1f : -1f;
            var dest = _h.PitCenter + axis * sign * (_h.PitRadius + 0.5f);
            MoveBody(body, dest);
            AtlasWorld.Send(AtlasAmberhive.OpHive, w =>
            {
                w.Write((byte)5); w.Write(body.ParentId); w.Write(dest.x); w.Write(dest.y);
            });
        }
    }

    /// <summary>Beginn einer Drehung: wer auf der Bruecke steht, kommt ans naechste Brueckenende (nur der eigene Spieler).</summary>
    private void ClearBridge()
    {
        if (AmHost)
        {
            ClearBridgeBodies();
            _nextBodyCheck = Time.time + 0.25f;
        }
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.Data == null || lp.Data.IsDead || lp.inVent) return;
        var p = lp.GetTruePosition();
        var d = p - _h.PitCenter;
        float margin = lp.Collider != null ? lp.Collider.bounds.extents.x + 0.06f : 0.3f;
        if (d.magnitude >= _h.PitRadius + margin) return;
        float a = (_phase == 1 ? 90f : 0f) * Mathf.Deg2Rad;
        var axis = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
        int oldPhase = (_phase + 3) % 4;
        float s = _entryPhase == oldPhase ? _entrySign : (Vector2.Dot(d, axis) >= 0f ? 1f : -1f);
        var dest = _h.PitCenter + axis * s * (_h.PitRadius + margin + 0.15f);
        try { lp.NetTransform.RpcSnapTo(dest + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} bridge turns: moved off the bridge to ({dest.x:F1}|{dest.y:F1})");
    }

    // ------------------------------------------------------------------ Honigflut

    private void BuildFlood()
    {
        for (int zi = 0; zi < _h.FloodZones.Count; zi++)
        {
            var z = _h.FloodZones[zi];
            float x0 = z.Min(p => p.x), x1 = z.Max(p => p.x), y0 = z.Min(p => p.y), y1 = z.Max(p => p.y);
            var go = new GameObject("Atlas_HiveFlood");
            go.transform.SetParent(_root, false);
            go.transform.position = new Vector3((x0 + x1) / 2f, (y0 + y1) / 2f, AtlasMuseumBuilder.FloorZ - 0.5f);
            var sr = go.AddComponent<SpriteRenderer>();
            var spr = AtlasAssets.TaskSprite($"task_hive_flood_{zi}.png", 60f, new Vector2(0.5f, 0.5f))
                      ?? AtlasAssets.TaskSprite("task_hive_flood.png", 100f, new Vector2(0.5f, 0.5f));
            if (spr != null)
            {
                sr.sprite = spr;
                go.transform.localScale = new Vector3((x1 - x0) / spr.bounds.size.x, (y1 - y0) / spr.bounds.size.y, 1f);
            }
            else
            {
                sr.sprite = Solid(new Color32(236, 160, 30, 255));
                go.transform.localScale = new Vector3(x1 - x0, y1 - y0, 1f);
            }
            AtlasMuseumBuilder.Mask(sr);
            sr.color = new Color(1f, 1f, 1f, 0f);
            _floodSr.Add(sr);
        }
    }

    private float FloodLevel()
    {
        if (_floodZone < 0) return 0f;
        float t = _clock - _floodT0 - _h.FloodWarning;
        if (t < 0f) return 0f;
        if (t < _h.FloodRise) return t / _h.FloodRise;
        t -= _h.FloodRise;
        if (t < _h.FloodHold) return 1f;
        t -= _h.FloodHold;
        if (t < _h.FloodDrain) return 1f - t / _h.FloodDrain;
        _floodZone = -1;
        return 0f;
    }

    private void TickFlood()
    {
        float lv = FloodLevel();
        for (int i = 0; i < _floodSr.Count; i++)
        {
            float a = i == _floodZone ? lv : 0f;
            bool warn = i == _floodZone && _clock - _floodT0 < _h.FloodWarning;
            if (warn) a = 0.15f + 0.15f * (0.5f + 0.5f * Mathf.Sin(_clock * 8f));
            var sr = _floodSr[i];
            if (sr == null) continue;
            sr.color = new Color(1f, 1f, 1f, 0.82f * a);
        }
        SlowFactor = 1f;
        if (_floodZone < 0 || lv < 0.4f) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.Data == null || lp.Data.IsDead || lp.inVent || !lp.CanMove || _chuteT0 >= 0f) return;
        if (Inside(_h.FloodZones[_floodZone], lp.GetTruePosition())) SlowFactor = Mathf.Lerp(1f, _h.FloodSlow, lv);
    }

    private static bool Inside(Vector2[] poly, Vector2 p)
    {
        bool c = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if ((poly[i].y > p.y) != (poly[j].y > p.y) && p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)
                c = !c;
        return c;
    }

    // ------------------------------------------------------------------ Rutsche (nur 2 Etagen)

    private const float ChuteFade = 0.25f, ChuteHold = 0.15f, ChuteSlide = 0.45f;

    private void TickChute()
    {
        var lp = PlayerControl.LocalPlayer;
        if (_chuteT0 >= 0f) { RunChute(lp); return; }
        if (lp == null || !AtlasUse.CanReach(lp, _h.ChuteTop, 1.0f)) return;
        AtlasUse.Offer("SLIDE", "task_hive_slide_button.png", () =>
        {
            var p = PlayerControl.LocalPlayer;
            if (_chuteT0 >= 0f || Time.time < _chutePendingUntil || !AtlasUse.CanReach(p, _h.ChuteTop, 1f)) return;
            _chutePendingUntil = Time.time + 2f;
            if (AmHost) HostChute(p);
            else AtlasWorld.Send(AtlasAmberhive.OpHive, w => w.Write((byte)4));
        });
    }

    private void HostChute(PlayerControl from)
    {
        if (!_two || !_h.HasChute || MeetingHud.Instance != null || ExileController.Instance != null) return;
        if (from == null || from.Data == null || from.Data.IsDead || from.inVent) return;
        // CanMove liest den UI-Zustand des Hosts (Chat, Karte, Aufgabe), nicht den des Gastes.
        // Fuer Gaeste daher nur netzneutrale Felder pruefen.
        if (from.AmOwner ? !from.CanMove : (!from.moveable || from.onLadder || from.inMovingPlat)) return;
        if (!AtlasUse.HostNear(from, _h.ChuteTop, 1.0f)) return;
        if (_chuteCooldown.TryGetValue(from.PlayerId, out float until) && _clock < until) return;
        _chuteCooldown[from.PlayerId] = _clock + 2f;
        byte pid = from.PlayerId;
        _life?.SuppressTransit(pid, 3f); // AMBERHIVE LIFE: Host sperrt auch fremde Rutschende.
        if (from.AmOwner) BeginChute(from);
        AtlasWorld.Send(AtlasAmberhive.OpHive, w => { w.Write((byte)3); w.Write(pid); });
    }

    private void BeginChute(PlayerControl p)
    {
        if (_chuteT0 >= 0f) return;
        _chuteT0 = Time.time; _chuteMoved = false;
        p.moveable = false;
        AtlasFigure.StopBody(p);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} chute: sliding down (host approved)");
    }

    private void RunChute(PlayerControl lp)
    {
        float el = Time.time - _chuteT0;
        bool abort = lp == null || lp.Data == null || lp.Data.IsDead || MeetingHud.Instance != null || ExileController.Instance != null;
        if (abort) { EndChute(lp); return; }
        float a = el < ChuteFade ? el / ChuteFade : el < ChuteFade + ChuteHold ? 1f : 1f - (el - ChuteFade - ChuteHold) / ChuteFade;
        Veil(Mathf.Clamp01(a));
        if (!_chuteMoved && el >= ChuteFade)
        {
            _chuteMoved = true;
            try { lp.NetTransform.RpcSnapTo(_h.ChuteBottom + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
        }
        // Rauslutschen: nach der Blende rutscht man vom Rutschenende bis zum Ausstieg
        float s0 = ChuteFade + ChuteHold;
        if (_chuteMoved && el >= s0 && lp.MyPhysics != null && lp.MyPhysics.body != null)
        {
            float k = Mathf.Clamp01((el - s0) / ChuteSlide);
            AtlasFigure.SetPos(lp, Vector2.Lerp(_h.ChuteBottom, _h.ChuteExit, k) + new Vector2(0f, AtlasMuseumBuilder.FeetOffset()));
            AtlasFigure.StopBody(lp);
        }
        if (el >= s0 + Mathf.Max(ChuteFade, ChuteSlide))
        {
            try { lp.NetTransform.RpcSnapTo(_h.ChuteExit + new Vector2(0f, AtlasMuseumBuilder.FeetOffset())); } catch { }
            EndChute(lp);
        }
    }

    private void EndChute(PlayerControl lp)
    {
        _chuteT0 = -1f;
        Veil(0f);
        if (lp != null && lp.Data != null && MeetingHud.Instance == null && ExileController.Instance == null)
        {
            lp.moveable = true;
            try { lp.MyPhysics.body.velocity = Vector2.zero; } catch { }
        }
    }

    private void Veil(float alpha)
    {
        if (_veil == null)
        {
            if (alpha <= 0f) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_ChuteVeil";
            _veil = go.GetComponent<SpriteRenderer>();
            if (_veil == null) { Object.Destroy(go); return; }
            _veil.enabled = true;
        }
        bool on = alpha > 0.001f;
        if (_veil.gameObject.activeSelf != on) _veil.gameObject.SetActive(on);
        if (on) _veil.color = new Color(0.55f, 0.33f, 0.05f, alpha);
    }

    // ------------------------------------------------------------------ animierte Objekte

    private static readonly Dictionary<string, float> AnimFps = new()
    {
        ["bellows_big"] = 5f, ["nectar_press"] = 6f, ["wax_cauldron"] = 5f, ["glow_rack"] = 3f, ["dance_floor"] = 4f,
    };

    private Dictionary<string, Sprite[]> _animFrames;
    private int _animTries;

    private Dictionary<string, Sprite[]> LoadAnimFrames()
    {
        if (_h.Anim.Count == 0) return null;
        var frames = new Dictionary<string, Sprite[]>();
        foreach (var kv in _h.Anim)
        {
            var arr = new Sprite[kv.Value];
            bool ok = true;
            for (int k = 0; k < kv.Value; k++)
            {
                arr[k] = AtlasAssets.TaskSprite($"task_hive_anim_{kv.Key}_{k}.png", 120f, Vector2.zero);
                if (arr[k] == null) { ok = false; break; }
            }
            if (ok) frames[kv.Key] = arr;
        }
        return frames.Count > 0 ? frames : null;
    }

    /// <summary>Renderer der animierten Objekte aus Atlas' Objektliste (Name "Prop_&lt;Art&gt;_&lt;n&gt;"); sucht, bis die Objekte stehen.</summary>
    private void BindAnims()
    {
        if (++_animTries > 20) { _animFrames = null; return; }
        foreach (var sr in AtlasMuseumBuilder.PropRenderers)
        {
            if (sr == null) continue;
            string name = sr.gameObject.name;
            if (!name.StartsWith("Prop_", StringComparison.Ordinal)) continue;
            int cut = name.LastIndexOf('_');
            string kind = cut > 5 ? name.Substring(5, cut - 5) : null;
            if (kind == null || !_animFrames.TryGetValue(kind, out var fr)) continue;
            _anims.Add((sr, fr, AnimFps.TryGetValue(kind, out var f) ? f : 5f, Random.value * fr.Length));
        }
        if (_anims.Count > 0)
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_anims.Count} animated object(s) ({string.Join(", ", _animFrames.Keys)})");
    }

    private void TickAnims()
    {
        float t = Time.time;
        foreach (var a in _anims)
        {
            if (a.Sr == null) continue;
            int k = (int)(t * a.Fps + a.Phase) % a.Frames.Length;
            if (a.Sr.sprite != a.Frames[k]) a.Sr.sprite = a.Frames[k];
        }
    }

    // ------------------------------------------------------------------ Bienen (nur Optik, jeder Client fuer sich)

    private sealed class Bee
    {
        public SpriteRenderer Sr; public Vector2 Pos, Target; public Vector2[] Area; public float Speed, Phase, Wait;
    }

    private readonly List<Bee> _bees = new();
    private Sprite[] _beeFrames;

    private void BuildBees()
    {
        var f0 = AtlasAssets.TaskSprite("task_hive_bee_0.png", 120f, new Vector2(0.5f, 0.3f));
        var f1 = AtlasAssets.TaskSprite("task_hive_bee_1.png", 120f, new Vector2(0.5f, 0.3f));
        if (f0 == null || f1 == null || _def?.Rooms == null) return;
        _beeFrames = new[] { f0, f1 };
        var rooms = _def.Rooms.Where(r => r.Area != null && r.Area.Length >= 3).ToList();
        int n = Mathf.Min(12, rooms.Count);
        var rnd = new System.Random(4711);
        foreach (var r in rooms.OrderBy(_ => rnd.Next()).Take(n))
        {
            var go = new GameObject("Atlas_HiveBee");
            go.transform.SetParent(_root, false);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = f0;
            AtlasMuseumBuilder.Mask(sr);
            var b = new Bee { Sr = sr, Area = r.Area, Speed = 0.8f + (float)rnd.NextDouble() * 0.6f, Phase = (float)rnd.NextDouble() * 10f };
            b.Pos = RandomIn(r.Area, rnd); b.Target = RandomIn(r.Area, rnd);
            _bees.Add(b);
        }
    }

    private static Vector2 RandomIn(Vector2[] poly, System.Random rnd)
    {
        float x0 = poly.Min(p => p.x), x1 = poly.Max(p => p.x), y0 = poly.Min(p => p.y), y1 = poly.Max(p => p.y);
        for (int i = 0; i < 30; i++)
        {
            var p = new Vector2(x0 + (float)rnd.NextDouble() * (x1 - x0), y0 + (float)rnd.NextDouble() * (y1 - y0));
            if (Inside(poly, p)) return p;
        }
        return new Vector2((x0 + x1) / 2f, (y0 + y1) / 2f);
    }

    private readonly System.Random _beeRnd = new();

    private void TickBees(float dt)
    {
        if (_bees.Count == 0) return;
        float t = Time.time;
        foreach (var b in _bees)
        {
            if (b.Sr == null) continue;
            b.Pos = _life?.BeeAvoid(b.Pos, b.Area, dt) ?? b.Pos; // AMBERHIVE LIFE: nur sichtbare Laeufer.
            if (b.Wait > 0f) b.Wait -= dt;
            else
            {
                var d = b.Target - b.Pos;
                float step = b.Speed * dt;
                if (d.magnitude <= step)
                {
                    b.Pos = b.Target;
                    b.Target = RandomIn(b.Area, _beeRnd);
                    b.Wait = (float)_beeRnd.NextDouble() * 1.5f;
                }
                else
                {
                    b.Pos += d.normalized * step;
                    b.Sr.flipX = d.x > 0f;
                }
            }
            float bob = Mathf.Sin(t * 3.1f + b.Phase) * 0.12f;
            var p = b.Pos + new Vector2(Mathf.Sin(t * 1.7f + b.Phase) * 0.15f, 1.1f + bob);
            b.Sr.transform.position = new Vector3(p.x, p.y, AtlasMuseumBuilder.SortZ(b.Pos.y - 1.5f));
            b.Sr.sprite = _beeFrames[(int)((t + b.Phase) * 16f) % 2];
        }
    }

    // ------------------------------------------------------------------ Hilfen

    private static Sprite Solid(Color32 c)
    {
        var tex = new Texture2D(4, 4, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave };
        var px = new Color32[16];
        for (int i = 0; i < 16; i++) px[i] = c;
        tex.SetPixels32(px);
        tex.Apply(false, true);
        var s = Sprite.Create(tex, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f), 4f);
        s.hideFlags |= HideFlags.HideAndDontSave;
        return s;
    }

    // ------------------------------------------------------------------ Diagnose (Autotest)

    internal string DiagState() =>
        $"bridge phase {_phase} angle {BridgeAngle():F0}, flood zone {_floodZone} level {FloodLevel():F2}, slow {SlowFactor:F2}, chute {(_chuteT0 >= 0f ? "moving" : "idle")}";
}

/// <summary>Honigflut: der eigene Spieler laeuft langsamer, solange er im gefluteten Gang steht.</summary>
[HarmonyPatch(typeof(PlayerPhysics), nameof(PlayerPhysics.FixedUpdate))]
internal static class AmberhiveSlowPatch
{
    public static void Postfix(PlayerPhysics __instance)
    {
        try
        {
            if (__instance == null || !__instance.AmOwner || __instance.body == null) return;
            AmberhiveWorld.Current?.ProbePhysics(__instance);
            if (AmberhiveWorld.SlowFactor >= 0.999f) return;
            __instance.body.velocity *= AmberhiveWorld.SlowFactor;
        }
        catch { }
    }
}
