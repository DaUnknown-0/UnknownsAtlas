// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasRex - dritte kritische Sabotage im Museum: "Rex erwacht" (User 25.09.; Konzept und Prototyp:
// https://claude.ai/artifact/TwpK278eBi1gas4QT28nxR).
//
// Die Impostor wecken das T.-rex-Skelett der Rotunde. Die Crew hat 50 s, es an zwei Stationen wieder
// einzuschlaefern: Spieluhr (Rotunde) im Wiegenlied-Tempo kurbeln, Sternenprojektor (Security Office)
// ausgerichtet halten. Schlafbalken 0-100: eine Station im Takt +2/s, beide +6/s, niemand -1/s. Alle
// 10-13 s bruellt der Rex (1,6 s Vorwarnung: er reisst das Maul auf) und kostet 6 Punkte. Balken voll =
// behoben, Countdown bei null = die Impostor gewinnen (ImpostorBySabotage). Allein ist es mit Absicht
// nicht zu schaffen (etwa 67 s), zu zweit etwa 20 s plus Laufweg.
//
// Balancing (User 25.09.): Impostor koennen an den Stationen nur HELFEN. Fehlbedienung zaehlt 0, nie
// negativ; mehrere Spieler je Station, der Host fuehrt je Station eine Liste der Spieler im Takt und die
// Station zaehlt, solange die Liste nicht leer ist; Bruellen, Zielwandern und Countdown nur beim Host.
//
// Netz: RPC 237 (AtlasWorld), Op 11 [sub][...]
//   0 Start                                  Host -> alle
//   1 State [schlaf][zeit*10 u16][flags]     Host -> alle, alle 0,25 s (flags: 1 Spieluhr, 2 Nachtlicht)
//   2 Roar                                   Host -> alle: in 1,6 s bruellt er (Vorwarnung laeuft lokal)
//   3 End [0 eingeschlafen, 1 Meeting, 2 Impostor gewinnen]   Host -> alle
//   4 Input [station][an]                    jeder -> Host
// Ausgeloest wird ueber den Kartenknopf (AtlasWorld OpSabReq, Art SabRex).

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;
using Random = UnityEngine.Random;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasRex
{
    private const string LogPrefix = "[Atlas/Rex]";
    internal const byte OpRex = 11;
    private const byte SubStart = 0, SubState = 1, SubRoar = 2, SubEnd = 3, SubInput = 4;
    internal const byte Music = 0, Light = 1;
    internal const byte EndSlept = 0, EndMeeting = 1, EndLost = 2;

    public const float Countdown = 50f, RateOne = 2f, RateBoth = 6f, Decay = 1f, RoarLoss = 6f;
    public const float RoarMin = 10f, RoarMax = 13f, Warn = 1.6f;
    public const float CrankMin = 0.75f, CrankMax = 1.35f, ProjTol = 9f;

    private static bool Museum => AtlasMuseumBuilder.Active && AtlasMuseumBuilder.D.Key == "museum";
    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;

    // ------------------------------------------------------------------ Zustand (alle Clients)
    public static bool Active { get; private set; }
    public static float Sleep { get; private set; }
    public static float TimeLeft { get; private set; }
    public static bool MusicOn { get; private set; }
    public static bool LightOn { get; private set; }
    /// <summary>Zaehlt jedes Bruellen; die Minispiele reagieren darauf (Kurbel schlaegt zurueck, Ziel springt).</summary>
    public static int Roars { get; private set; }
    /// <summary>0..1 waehrend der Vorwarnung vor dem Bruellen.</summary>
    public static float WarnPhase { get; private set; }
    /// <summary>Das eigene Spieluhr-Minispiel ist offen (dann spielt die Welt-Melodie nicht doppelt).</summary>
    internal static bool LocalCranking;
    private static float _roarAt = -1f;
    private static readonly bool[] MyInput = new bool[2];

    // Host
    private static readonly HashSet<byte> MusicUsers = new(), LightUsers = new();
    private static float _hostNextHit, _hostSendAt;
    private static bool _hostWarned;

    public static void Reset()
    {
        Active = false; Sleep = 0f; TimeLeft = Countdown; MusicOn = LightOn = false;
        Roars = 0; WarnPhase = 0f; _roarAt = -1f; LocalCranking = false;
        MyInput[0] = MyInput[1] = false;
        MusicUsers.Clear(); LightUsers.Clear();
        _headPivot = _jawPivot = null; _eye = null; _awake = 0f; _headAng = _jawAng = 0f;
        _hint = null; _arrows.Clear(); _shakeT = 0f; _roarShake = 0f;
    }

    // ------------------------------------------------------------------ Netz

    private static void Send(byte sub, Action<MessageWriter> body) =>
        AtlasWorld.Send(OpRex, w => { w.Write(sub); body?.Invoke(w); });

    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case SubStart when fromHost: ApplyStart(); break;
            case SubState when fromHost:
            {
                Sleep = r.ReadByte();
                TimeLeft = r.ReadUInt16() / 10f;
                byte f = r.ReadByte();
                MusicOn = (f & 1) != 0; LightOn = (f & 2) != 0;
                break;
            }
            case SubRoar when fromHost: ApplyRoar(); break;
            case SubEnd when fromHost: ApplyEnd(r.ReadByte()); break;
            case SubInput when AmHost: HostInput(from, r.ReadByte(), r.ReadBoolean()); break;
        }
    }

    /// <summary>Minispiel: dieser Spieler ist an einer Station im Takt (an) oder nicht mehr (aus).</summary>
    public static void SetInput(byte station, bool on)
    {
        if (station > 1 || MyInput[station] == on) return;
        MyInput[station] = on;
        if (!Active && on) return;
        if (AmHost) HostInput(PlayerControl.LocalPlayer, station, on);
        else Send(SubInput, w => { w.Write(station); w.Write(on); });
    }

    // ------------------------------------------------------------------ Host

    /// <summary>Kartenknopf eines Impostors (AtlasWorld.HostSabRequest hat Rolle, Tod und Abklingzeit geprueft).</summary>
    internal static bool HostTryStart()
    {
        if (!Museum || Active) return false;
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        // wie jede Sabotage: nicht waehrend einer anderen und nicht in der gemeinsamen Abklingzeit
        if (sab != null && (sab.AnyActive || sab.Timer > 0f))
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} refused: vanilla sabotage active {sab.AnyActive}, shared cooldown {sab.Timer:F0} s");
            return false;
        }
        HostStart();
        return true;
    }

    internal static void HostStart()
    {
        if (!Museum || Active) return;
        MusicUsers.Clear(); LightUsers.Clear();
        _hostNextHit = Time.time + Random.Range(5.5f, 7f);
        _hostWarned = false;
        _hostSendAt = 0f;
        LockSabotages();
        ApplyStart();
        Send(SubStart, null);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: Rex is awake ({Countdown:F0} s)");
    }

    private static void HostInput(PlayerControl from, byte station, bool on)
    {
        if (!Active || from == null || from.Data == null || from.Data.IsDead || station > 1) return;
        var set = station == Music ? MusicUsers : LightUsers;
        if (on) set.Add(from.PlayerId); else set.Remove(from.PlayerId);
    }

    private static void Prune(HashSet<byte> set)
    {
        if (set.Count == 0) return;
        var gone = new List<byte>();
        foreach (var id in set)
        {
            var info = GameData.Instance != null ? GameData.Instance.GetPlayerById(id) : null;
            if (info == null || info.IsDead || info.Disconnected) gone.Add(id);
        }
        foreach (var id in gone) set.Remove(id);
    }

    private static void HostTick(float dt)
    {
        // Wie beim Reaktor: ein Meeting (gemeldete Leiche) beendet die Sabotage
        if (MeetingHud.Instance != null || ExileController.Instance != null) { HostEnd(EndMeeting); return; }
        Prune(MusicUsers); Prune(LightUsers);
        bool a = MusicUsers.Count > 0, b = LightUsers.Count > 0;
        MusicOn = a; LightOn = b;
        float rate = a && b ? RateBoth : a || b ? RateOne : Sleep > 0f ? -Decay : 0f;
        Sleep = Mathf.Clamp(Sleep + rate * dt, 0f, 100f);
        TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        float now = Time.time;
        if (!_hostWarned && now >= _hostNextHit - Warn) { _hostWarned = true; ApplyRoar(); Send(SubRoar, null); }
        if (now >= _hostNextHit)
        {
            Sleep = Mathf.Max(0f, Sleep - RoarLoss);
            _hostNextHit = now + Random.Range(RoarMin, RoarMax);
            _hostWarned = false;
        }
        LockSabotages();
        if (now >= _hostSendAt) { _hostSendAt = now + 0.25f; SendState(); }
        if (Sleep >= 100f) HostEnd(EndSlept);
        else if (TimeLeft <= 0f) HostEnd(EndLost);
    }

    private static void SendState()
    {
        byte s = (byte)Mathf.Clamp(Mathf.RoundToInt(Sleep), 0, 100);
        ushort t = (ushort)Mathf.Clamp(Mathf.RoundToInt(TimeLeft * 10f), 0, 65535);
        byte f = (byte)((MusicOn ? 1 : 0) | (LightOn ? 2 : 0));
        Send(SubState, w => { w.Write(s); w.Write(t); w.Write(f); });
    }

    internal static void HostEnd(byte result)
    {
        if (!Active) return;
        SendState();
        ApplyEnd(result);
        Send(SubEnd, w => w.Write(result));
        MusicUsers.Clear(); LightUsers.Clear();
        // Nach einer kritischen Sabotage die gemeinsame Abklingzeit wie in Vanilla
        SetSabotageTimer(30f);
        AtlasWorld.SetSabCooldown(30f);
        if (result == EndLost) EndGame();
    }

    /// <summary>Waehrend der Rex wach ist, kann keine andere Sabotage starten: die gemeinsame Abklingzeit
    /// der Sabotage-Karte bleibt oben (die Knoepfe zeigen sie wie nach jeder Sabotage an).</summary>
    private static void LockSabotages()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && sab.Timer < 5f) SetSabotageTimer(10f);
    }

    private static void SetSabotageTimer(float t)
    {
        try
        {
            var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
            if (sab == null) return;
            sab.Timer = Mathf.Max(sab.Timer, t);
            sab.IsDirty = true;
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} sabotage timer: {e.Message}"); }
    }

    private static void EndGame()
    {
        var client = AmongUsClient.Instance;
        if (client == null || client.NetworkMode == NetworkModes.FreePlay || GameManager.Instance == null)
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} time is up - freeplay: the game would end now (ImpostorBySabotage)");
            return;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} time is up - impostors win by sabotage");
        GameManager.Instance.RpcEndGame(GameOverReason.ImpostorBySabotage, false);
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyStart()
    {
        Active = true;
        Sleep = 0f; TimeLeft = Countdown; MusicOn = LightOn = false;
        WarnPhase = 0f; _roarAt = -1f;
        MyInput[0] = MyInput[1] = false;
        RoarFx();
        _flashStart = Time.time;
        MakeArrows();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} Rex awake");
    }

    private static void ApplyRoar() => _roarAt = Time.time + Warn;

    private static void ApplyEnd(byte result)
    {
        if (!Active) return;
        Active = false;
        if (result == EndSlept) Sleep = 100f;
        MusicOn = LightOn = false;
        WarnPhase = 0f; _roarAt = -1f;
        MyInput[0] = MyInput[1] = false;
        FlashTick();
        ClearArrows();
        ShowHint(null, default);
        StripTaskLine();
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} ended: {(result == EndSlept ? "Rex sleeps" : result == EndMeeting ? "meeting" : "impostors win")}");
    }

    // ------------------------------------------------------------------ Takt

    public static void Tick(float dt)
    {
        if (!Museum) return;
        AnimateRex(dt);
        ShakeTick(dt);
        FlashTick();
        if (!Active) { MelodyTick(dt, false); return; }
        if (AmHost) HostTick(dt);
        else TimeLeft = Mathf.Max(0f, TimeLeft - dt);                // zwischen zwei Zustandsmeldungen weiterzaehlen
        if (!Active) return;
        if (_roarAt > 0f)
        {
            WarnPhase = Mathf.Clamp01(1f - (_roarAt - Time.time) / Warn);
            if (Time.time >= _roarAt) { _roarAt = -1f; WarnPhase = 0f; Roars++; RoarFx(); }
        }
        ArrowsTick();
        TaskLineTick();
        ClickTick();
        MelodyTick(dt, true);
    }

    // ------------------------------------------------------------------ Der Rex bewegt sich

    private static Transform _headPivot, _jawPivot;
    private static SpriteRenderer _eye;
    private static float _awake, _headAng, _jawAng, _roarShake;

    /// <summary>Nach dem Kartenbau: Kopf und Unterkiefer (eigene Sprites, museum_art) an Gelenke haengen.</summary>
    public static void OnBuilt(ShipStatus ship)
    {
        // Hier gilt der Bau noch nicht als fertig (AtlasMuseumBuilder.Active), deshalb nur die Karte pruefen
        if (ship == null || AtlasMuseumBuilder.D.Key != "museum") return;
        try
        {
            SpriteRenderer body = null, head = null, jaw = null;
            foreach (var sr in ship.GetComponentsInChildren<SpriteRenderer>(true))
            {
                if (sr == null) continue;
                string n = sr.name;
                if (n.StartsWith("Prop_dino_rex_head_", StringComparison.Ordinal)) head = sr;
                else if (n.StartsWith("Prop_dino_rex_jaw_", StringComparison.Ordinal)) jaw = sr;
                else if (n.StartsWith("Prop_dino_rex_", StringComparison.Ordinal) && n.Length > 14 && char.IsDigit(n[14])) body = sr;
            }
            if (body == null || head == null || jaw == null)
            {
                AtlasPlugin.Logger.LogWarning($"{LogPrefix} rex sprites missing (body {body != null}, head {head != null}, jaw {jaw != null})");
                return;
            }
            // Tiefe: Kopf vor Unterkiefer vor Rumpf (alle drei haben dieselbe Standlinie)
            float z = body.transform.position.z;
            _headPivot = new GameObject("Atlas_RexHead") { layer = head.gameObject.layer }.transform;
            _headPivot.SetParent(body.transform.parent, false);
            _headPivot.position = new Vector3(AtlasMuseumData.RexNeck.x, AtlasMuseumData.RexNeck.y, z - 0.0003f);
            var hp = head.transform.position;
            head.transform.SetParent(_headPivot, true);
            head.transform.position = new Vector3(hp.x, hp.y, z - 0.0003f);
            _jawPivot = new GameObject("Atlas_RexJaw") { layer = jaw.gameObject.layer }.transform;
            _jawPivot.SetParent(_headPivot, false);
            _jawPivot.position = new Vector3(AtlasMuseumData.RexJaw.x, AtlasMuseumData.RexJaw.y, z - 0.00015f);
            var jp = jaw.transform.position;
            jaw.transform.SetParent(_jawPivot, true);
            jaw.transform.position = new Vector3(jp.x, jp.y, z - 0.00015f);
            // rotes Glimmen in der Augenhoehle
            var eg = new GameObject("Atlas_RexEye") { layer = head.gameObject.layer };
            eg.transform.SetParent(_headPivot, false);
            eg.transform.position = new Vector3(AtlasMuseumData.RexEye.x, AtlasMuseumData.RexEye.y, z - 0.0004f);
            _eye = eg.AddComponent<SpriteRenderer>();
            _eye.sprite = GlowSprite();
            _eye.color = new Color(1f, 0.2f, 0.12f, 0f);
            eg.transform.localScale = Vector3.one * 0.7f;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} rig ready: neck {AtlasMuseumData.RexNeck}, jaw {AtlasMuseumData.RexJaw}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} rig: {e.Message}"); }
    }

    private static void AnimateRex(float dt)
    {
        if (_headPivot == null) return;
        _awake = Mathf.MoveTowards(_awake, Active ? 1f : 0f, dt * (Active ? 1.6f : 0.35f));
        _roarShake = Mathf.Max(0f, _roarShake - dt);
        float agit = Active ? 1f - Sleep / 100f : 0f;
        float t = Time.time;
        // Kopf: pendelt (unruhiger, je wacher), hebt die Schnauze bei der Warnung und beim Bruellen
        float sway = Mathf.Sin(t * 1.5f) * (2f + 4f * agit) + Mathf.Sin(t * 3.7f) * 0.8f * agit;
        float lift = _roarShake > 0f ? -11f + Mathf.Sin(t * 40f) * 1.5f : -WarnPhase * 7f;
        float headT = (sway + lift) * _awake;
        float jawT = (_roarShake > 0f ? 24f : WarnPhase > 0f ? 5f + 14f * WarnPhase : 2f + 1.5f * Mathf.Sin(t * 6f)) * _awake;
        float k = 1f - Mathf.Exp(-dt * 9f);
        _headAng = Mathf.Lerp(_headAng, headT, k);
        _jawAng = Mathf.Lerp(_jawAng, jawT, k);
        if (_awake <= 0f) { _headAng = Mathf.MoveTowards(_headAng, 0f, dt * 20f); _jawAng = Mathf.MoveTowards(_jawAng, 0f, dt * 20f); }
        _headPivot.localRotation = Quaternion.Euler(0f, 0f, _headAng);
        if (_jawPivot != null) _jawPivot.localRotation = Quaternion.Euler(0f, 0f, _jawAng);
        if (_eye != null)
        {
            float a = _awake * (0.75f + 0.25f * Mathf.Sin(t * 9f));
            _eye.color = new Color(1f, 0.22f, 0.12f, a);
            _eye.transform.localScale = Vector3.one * (0.6f + 0.12f * Mathf.Sin(t * 9f) + (_roarShake > 0f ? 0.25f : 0f));
        }
    }

    private static Sprite _glow;
    private static Sprite GlowSprite()
    {
        if (_glow != null) return _glow;
        const int N = 64;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Bilinear };
        var px = new Color32[N * N];
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float u = (x + 0.5f) / N * 2f - 1f, v = (y + 0.5f) / N * 2f - 1f;
                float d = Mathf.Sqrt(u * u + v * v);
                float a = Mathf.Clamp01(1f - d);
                a = a * a * (0.6f + 0.4f * Mathf.Clamp01(1f - d * 3f) * 2f);
                px[y * N + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(a) * 255f));
            }
        tex.SetPixels32(px);
        tex.Apply(false, true);
        _glow = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), N);
        _glow.hideFlags = HideFlags.HideAndDontSave;
        return _glow;
    }

    // ------------------------------------------------------------------ Bruellen: Ton und Wackeln

    private static float _shakeT;

    private static void RoarFx()
    {
        _roarShake = 0.75f;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        var me = lp.GetTruePosition();
        float d = Vector2.Distance(me, AtlasMuseumData.RexNeck);
        AtlasWeatherFx.Sfx("roar", d < 9f ? 0.95f : 0.5f);
        // Wackeln nur in der Rotunde (User 25.09.)
        if (InRoom(me, "Rotunda")) _shakeT = 0.7f;
    }

    private static void ShakeTick(float dt)
    {
        var cam = HudManager.InstanceExists ? HudManager.Instance.PlayerCam : null;
        if (cam == null) return;
        if (_shakeT > 0f)
        {
            _shakeT -= dt;
            cam.shakeAmount = 0.09f * Mathf.Clamp01(_shakeT / 0.7f + 0.3f);
            cam.shakePeriod = 30f;
            if (_shakeT <= 0f) { cam.shakeAmount = 0f; }
        }
    }

    private static bool InRoom(Vector2 p, string name)
    {
        foreach (var r in AtlasMuseumBuilder.D.Rooms)
            if (r.Name == name && InPoly(r.Area, p)) return true;
        return false;
    }

    private static bool InPoly(Vector2[] poly, Vector2 p)
    {
        bool inside = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if ((poly[i].y > p.y) != (poly[j].y > p.y)
                && p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)
                inside = !inside;
        return inside;
    }

    // ------------------------------------------------------------------ Wiegenlied in der Welt

    // Brahms, Wiegenlied op. 49 Nr. 4 (gemeinfrei), vereinfacht; Indizes in NoteHz
    private static readonly float[] NoteHz = { 261.63f, 293.66f, 329.63f, 349.23f, 392f, 440f, 493.88f, 523.25f };
    private static readonly int[] Melody =
    {
        2, 2, 4, 2, 2, 4, 2, 4, 7, 6, 5, 5, 4, 1, 2, 3, 1, 1, 2, 3, 1, 3, 6, 5, 4, 6, 7,
        0, 0, 7, 5, 3, 4, 2, 0, 3, 4, 5, 4, 0, 0, 7, 5, 3, 4, 2, 0, 3, 2, 1, 0,
    };
    private static readonly AudioClip[] NoteClips = new AudioClip[8];
    private static int _melodyIdx;
    private static float _melodyAcc;

    /// <summary>Naechste Note der Melodie; pitch &gt; 1 = zu schnell gekurbelt (klingt schrill).</summary>
    internal static void PlayNextNote(float vol, float pitch)
    {
        try
        {
            if (SoundManager.Instance == null || vol <= 0.01f) return;
            int n = Melody[_melodyIdx++ % Melody.Length];
            var src = SoundManager.Instance.PlaySound(NoteClip(n), false, vol);
            if (src != null) src.pitch = pitch;
        }
        catch { }
    }

    private static AudioClip NoteClip(int i)
    {
        if (NoteClips[i] != null) return NoteClips[i];
        const int rate = 22050;
        int n = (int)(rate * 1.3f);
        var s = new float[n];
        float f = NoteHz[i] * 2f;                                             // Spieluhr: eine Oktave hoeher
        for (int k = 0; k < n; k++)
        {
            float t = (float)k / rate;
            float env = Mathf.Exp(-t * 3.2f) * Mathf.Clamp01(t / 0.004f);
            float v = Mathf.Sin(2f * Mathf.PI * f * t) + 0.22f * Mathf.Sin(2f * Mathf.PI * f * 4.02f * t) * Mathf.Exp(-t * 9f)
                      + 0.12f * Mathf.Sin(2f * Mathf.PI * f * 2f * t);
            s[k] = v * env * 0.32f;
        }
        var c = AudioClip.Create($"atlas_rexnote_{i}", n, 1, rate, false);
        c.hideFlags |= HideFlags.HideAndDontSave;
        c.SetData(s, 0);
        NoteClips[i] = c;
        return c;
    }

    /// <summary>Wer in Hoerweite der Spieluhr steht, hoert das Wiegenlied, solange jemand im Takt kurbelt.</summary>
    private static void MelodyTick(float dt, bool active)
    {
        if (!active || !MusicOn || LocalCranking) { _melodyAcc = 0f; return; }
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        float d = Vector2.Distance(lp.GetTruePosition(), AtlasMuseumLayout.RexMusicBox);
        float vol = 0.5f * Mathf.Clamp01(1f - d / 10f);
        if (vol <= 0.02f) return;
        _melodyAcc += dt * 3.1f;
        while (_melodyAcc >= 1f) { _melodyAcc -= 1f; PlayNextNote(vol, 1f); }
    }

    // ------------------------------------------------------------------ Rotes Blinken wie beim Reaktor

    // HudManager.StartReactorFlash blieb ohne echte Reaktoraufgabe dunkel (Autotest 25.09.); deshalb eine
    // eigene Kopie des Vollbilds (gleiches Rot 0,37, gleiche Ebene), die TORs showFlash nicht beruehrt.
    private static SpriteRenderer _flash;
    private static float _flashStart;

    private static void FlashTick()
    {
        bool want = Active && MeetingHud.Instance == null && Mathf.Repeat(Time.time - _flashStart, 2f) < 1f;
        if (_flash == null)
        {
            if (!want) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_RexFlash";
            _flash = go.GetComponent<SpriteRenderer>();
            if (_flash == null) { Object.Destroy(go); return; }
            _flash.enabled = true;
        }
        if (_flash.gameObject.activeSelf != want) _flash.gameObject.SetActive(want);
        if (want) _flash.color = new Color(1f, 0f, 0f, 0.373f);
    }

    // ------------------------------------------------------------------ Pfeile, Aufgabenliste

    private static readonly List<ArrowBehaviour> _arrows = new();
    private static Sprite _arrowSprite;

    private static void MakeArrows()
    {
        ClearArrows();
        try
        {
            // Wie beim Reaktor (User 25.09.): den Pfeil der Vanilla-Sabotageaufgabe klonen
            var template = VanillaArrow();
            foreach (var p in new[] { AtlasMuseumLayout.RexMusicBox, AtlasMuseumLayout.RexNightLight })
            {
                ArrowBehaviour ab;
                if (template != null)
                {
                    var go = Object.Instantiate(template.gameObject);
                    go.name = "Atlas_RexArrow";
                    go.SetActive(true);
                    ab = go.GetComponent<ArrowBehaviour>();
                }
                else
                {
                    var go = new GameObject("Atlas_RexArrow") { layer = 5 };
                    var sr = go.AddComponent<SpriteRenderer>();
                    sr.sprite = ArrowSprite();
                    sr.color = new Color(1f, 0.3f, 0.25f);
                    ab = go.AddComponent<ArrowBehaviour>();
                    ab.image = sr;
                }
                if (ab == null) continue;
                // Vanilla faerbt die Pfeile der Sabotageaufgaben rot und zeigt sie halb so gross wie die
                // Vorlage (Vergleich mit dem Alarm im Autotest 25.09.)
                if (template != null)
                {
                    ab.MaxScale = 0.5f;
                    ab.transform.localScale = Vector3.one * 0.5f;
                    if (ab.image != null) ab.image.color = Color.red;
                }
                ab.target = new Vector3(p.x, p.y, 0f);
                _arrows.Add(ab);
            }
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {_arrows.Count} arrow(s) ({(template != null ? "vanilla sabotage arrow" : "fallback sprite")})");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} arrows: {e.Message}"); }
    }

    private static void ArrowsTick()
    {
        var lp = PlayerControl.LocalPlayer;
        bool show = lp != null && lp.Data != null && !lp.Data.IsDead && MeetingHud.Instance == null;
        foreach (var a in _arrows) if (a != null && a.gameObject.activeSelf != show) a.gameObject.SetActive(show);
    }

    private static void ClearArrows()
    {
        foreach (var a in _arrows) if (a != null) Object.Destroy(a.gameObject);
        _arrows.Clear();
    }

    /// <summary>Pfeil aus einer Sabotageaufgabe der Karte (Reaktor zuerst), wie ihn Vanilla zu den Konsolen zeigt.</summary>
    private static ArrowBehaviour VanillaArrow()
    {
        var ship = ShipStatus.Instance;
        if (ship == null || ship.SpecialTasks == null) return null;
        ArrowBehaviour any = null;
        foreach (var t in ship.SpecialTasks)
        {
            var st = t != null ? t.TryCast<SabotageTask>() : null;
            if (st == null || st.Arrows == null) continue;
            foreach (var a in st.Arrows)
            {
                if (a == null) continue;
                if (t.TryCast<ReactorTask>() != null) return a;
                any ??= a;
                break;
            }
        }
        return any;
    }

    private static Sprite ArrowSprite()
    {
        if (_arrowSprite != null) return _arrowSprite;
        const int N = 64;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Bilinear };
        var px = new Color32[N * N];
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                // Pfeilspitze nach rechts mit dunklem Rand (Among-Us-Look)
                float u = (x + 0.5f) / N, v = Mathf.Abs((y + 0.5f) / N - 0.5f) * 2f;
                float inner = 0.9f - u - v * 0.75f;
                byte a = (byte)(Mathf.Clamp01(inner * 20f) * 255f);
                bool edge = inner < 0.09f;
                px[y * N + x] = edge ? new Color32(20, 16, 18, a) : new Color32(255, 255, 255, a);
            }
        tex.SetPixels32(px);
        tex.Apply(false, true);
        _arrowSprite = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), 150f);
        _arrowSprite.hideFlags = HideFlags.HideAndDontSave;
        return _arrowSprite;
    }

    private const string TaskMark = "<color=#FF4A3F>Rex Awake";

    /// <summary>Zeile oben in der Aufgabenliste, wie bei Reaktor und O2 (Countdown und Schlafbalken).</summary>
    private static void TaskLineTick()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel == null || panel.taskText == null) return;
            string text = panel.taskText.text ?? "";
            text = Strip(text);
            bool blink = Mathf.Repeat(Time.time, 1f) < 0.5f;
            string line = $"{TaskMark}! {Mathf.CeilToInt(TimeLeft)}s</color> <color=#{(blink ? "FFD27A" : "FFFFFF")}>(asleep {Mathf.FloorToInt(Sleep)}%)</color>\n";
            panel.taskText.text = line + text;
        }
        catch { }
    }

    private static void StripTaskLine()
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel != null && panel.taskText != null) panel.taskText.text = Strip(panel.taskText.text ?? "");
        }
        catch { }
    }

    private static string Strip(string text)
    {
        if (!text.StartsWith(TaskMark, StringComparison.Ordinal)) return text;
        int nl = text.IndexOf('\n');
        return nl >= 0 ? text.Substring(nl + 1) : "";
    }

    // ------------------------------------------------------------------ Stationen anklicken

    private static TextMeshPro _hint;

    private static void ClickTick()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.Data == null || lp.Data.IsDead || Minigame.Instance != null || MeetingHud.Instance != null) { ShowHint(null, default); return; }
        var me = lp.GetTruePosition();
        string kind = null; Vector2 at = default;
        if (Vector2.Distance(me, AtlasMuseumLayout.RexMusicBox) < 1.9f) { kind = "rexmusic"; at = AtlasMuseumLayout.RexMusicBox; }
        else if (Vector2.Distance(me, AtlasMuseumLayout.RexNightLight) < 1.9f) { kind = "rexlight"; at = AtlasMuseumLayout.RexNightLight; }
        ShowHint(kind, at);
        if (kind == null || !Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, at + new Vector2(0f, 0.5f)) < 1.4f) OpenStation(kind);
    }

    private static void ShowHint(string kind, Vector2 at)
    {
        if (kind == null) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null)
        {
            var go = new GameObject("Atlas_RexHint") { layer = 11 };
            if (ShipStatus.Instance != null) go.transform.SetParent(ShipStatus.Instance.transform, false);
            _hint = go.AddComponent<TextMeshPro>();
            var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
            if (src != null) { _hint.font = src.font; _hint.fontSharedMaterial = src.fontSharedMaterial; }
            _hint.fontSize = 2.2f; _hint.alignment = TextAlignmentOptions.Center; _hint.enableWordWrapping = false;
            _hint.color = new Color(1f, 0.55f, 0.45f);
            _hint.rectTransform.sizeDelta = new Vector2(5f, 1f);
            var mr = go.GetComponent<MeshRenderer>(); if (mr != null) mr.sortingOrder = 200;
        }
        _hint.gameObject.SetActive(true);
        _hint.text = kind == "rexmusic" ? "CLICK TO WIND" : "CLICK TO ALIGN";
        _hint.transform.position = new Vector3(at.x, at.y + 1.6f, -2f);
    }

    internal static void OpenStation(string kind)
    {
        if (Minigame.Instance != null || Camera.main == null || PlayerControl.LocalPlayer == null) return;
        var go = new GameObject($"AtlasTask_{kind}") { layer = 5 };
        go.transform.SetParent(Camera.main.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -50f);
        var mg = go.AddComponent<AtlasMinigame>();
        mg.TransType = TransitionType.SlideBottom;
        // Traeger fuer Minigame.Begin; die Stationen schliessen immer OHNE Schritt (IAtlasMechanic.Leave)
        PlayerTask any = null;
        foreach (var t in PlayerControl.LocalPlayer.myTasks) if (t != null) { any = t; break; }
        mg.Begin(any);
    }

    // ------------------------------------------------------------------ Notfallknopf gesperrt

    [HarmonyPostfix]
    [HarmonyPriority(Priority.Last)]
    [HarmonyPatch(typeof(EmergencyMinigame), nameof(EmergencyMinigame.Update))]
    internal static void EmergencyMinigame_Update_Postfix(EmergencyMinigame __instance)
    {
        if (!Active || !Museum || __instance == null) return;
        try
        {
            __instance.StatusText.text = TranslationController.Instance.GetString(StringNames.EmergencyDuringCrisis, Array.Empty<Il2CppSystem.Object>());
            __instance.NumberText.text = string.Empty;
            __instance.ClosedLid.gameObject.SetActive(true);
            __instance.OpenLid.gameObject.SetActive(false);
            __instance.ButtonActive = false;
        }
        catch { }
    }

    /// <summary>Host: keine zweite Sabotage, solange der Rex wach ist (zusaetzlich zur hochgehaltenen Abklingzeit).</summary>
    [HarmonyPrefix]
    [HarmonyPatch(typeof(SabotageSystemType), nameof(SabotageSystemType.UpdateSystem))]
    internal static bool SabotageSystemType_UpdateSystem_Prefix() => !(Active && Museum);

    // ------------------------------------------------------------------ Diagnose (AtlasWorld.Diag "rex...")

    internal static void Diag(string what, Action<Vector2> snap)
    {
        switch (what)
        {
            case "rex":
                HostStart();
                snap(new Vector2(-3.4f, 5.4f));                          // Blick auf Kopf und Podest
                break;
            case "rexmusic":
                if (!Active) HostStart();
                snap(AtlasMuseumLayout.RexMusicBox + new Vector2(0f, -0.9f));
                AtlasMinigame.DiagAuto = true;
                OpenStation("rexmusic");
                break;
            case "rexlight":
                if (!Active) HostStart();
                snap(AtlasMuseumLayout.RexNightLight + new Vector2(0f, -0.9f));
                AtlasMinigame.DiagAuto = true;
                OpenStation("rexlight");
                break;
            case "rexboth":
                // beide Stationen "besetzt" (zweiter Spieler simuliert), damit der Balken zu zweit fuellt
                if (!Active) HostStart();
                if (PlayerControl.LocalPlayer != null) { MusicUsers.Add(PlayerControl.LocalPlayer.PlayerId); LightUsers.Add(PlayerControl.LocalPlayer.PlayerId); }
                snap(new Vector2(-1.5f, 1.6f));
                break;
            case "arrowinfo":
                // Vergleich mit Vanilla: alle Pfeile in der Szene und der Vollbild-Blitz
                foreach (var a in Object.FindObjectsOfType<ArrowBehaviour>())
                {
                    if (a == null) continue;
                    var t = a.transform;
                    string path = t.name; for (var p = t.parent; p != null; p = p.parent) path = p.name + "/" + path;
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} arrow {path}: local {t.localScale} lossy {t.lossyScale} color {(a.image != null ? a.image.color.ToString() : "-")} max {a.MaxScale}");
                }
                var fs = HudManager.Instance != null ? HudManager.Instance.FullScreen : null;
                if (fs != null) AtlasPlugin.Logger.LogInfo($"{LogPrefix} fullscreen enabled {fs.enabled} active {fs.gameObject.activeInHierarchy} color {fs.color}");
                break;
            case "rexlose":
                if (!Active) HostStart();
                TimeLeft = 1.5f;
                break;
        }
    }

    public static string DiagState() =>
        $"rex {(Active ? "awake" : "asleep")}, sleep {Sleep:F0}, time {TimeLeft:F1}, music {MusicOn}, light {LightOn}, roars {Roars}";

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix()
    {
        if (_flash != null) Object.Destroy(_flash.gameObject);
        _flash = null;
        ClearArrows();
        Reset();
    }
}
