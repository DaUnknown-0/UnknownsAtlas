// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasVanillaCrisis - zusaetzliche kritische Sabotagen auf den Vanilla-Karten (User 20.10.: "zusaetzlich zum Reaktor,
// in den Einstellungen waehlbar, welche es gibt, auch Vanilla ueberschreibbar"). Bauweise wie Runaway Train
// (AtlasRunaway): zwei Stationen muessen GLEICHZEITIG gehalten werden (Hebel halten, Kurbel drehen), dann faellt der
// Stoerwert; nur eine: er steht; keine: er steigt. Bei 0 behoben, bei 100 oder Ablauf des Countdowns gewinnen die
// Impostor (ImpostorBySabotage). Ein Meeting beendet die Krise wie beim Reaktor.
//
// Einstellungen: AtlasVanillaOptions (TOR-Optionen 1720-1727, Host). Je Krise "Extra", "Replaces <Vanilla>" (der
// Vanilla-Knopf verschwindet von der Sabotage-Karte, der Host lehnt ihn ab) oder "Off".
// Nur wenn ALLE dieselbe Atlas-Version haben (AtlasHandshake.VersionMismatches): wer die Krise nicht kennt, sieht
// weder Stationen noch Countdown. Der Host prueft das zu Rundenbeginn und schickt den Gaesten die freigegebenen Krisen.
//
// Netz: RPC 237 (AtlasWorld), Op 20 [sub][...]
//   0 Allow [maske u16]                        Host -> alle: in dieser Runde freigegebene Krisen (Bit = Id)
//   1 Start [id][sekunden*10 u16]              Host -> alle
//   2 State [stoerung][zeit*10 u16][flags]     Host -> alle, alle 0,25 s (flags: Bit 0/1 = Station 0/1 besetzt)
//   3 End [grund]                              Host -> alle: 0 behoben, 1 Meeting, 2 verloren
//   4 Input [station][an]                      jeder -> Host
//   5 Request [id]                             Impostor -> Host (Kartenknopf)

using System;
using System.Collections.Generic;
using HarmonyLib;
using Hazel;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasVanillaCrisis
{
    private const string LogPrefix = "[Atlas/VanillaCrisis]";
    internal const byte OpCrisis = 20;
    private const byte SubAllow = 0, SubStart = 1, SubState = 2, SubEnd = 3, SubInput = 4, SubRequest = 5;
    internal const byte EndFixed = 0, EndMeeting = 1, EndLost = 2;
    public const float StartLevel = 30f, RiseNone = 1.5f, FallBoth = 6f, Reach = 1.4f;

    public sealed class Def
    {
        public byte Id;
        public string Key, Title, TaskLine, MapName, ReplacesLabel, BarWord, StartSfx;
        public byte MapId;                       // 0 Skeld, 2 Polus, 4 Airship
        public SystemTypes Replaces;             // Vanilla-Sabotage, die im Modus "Replace" wegfaellt
        public Vector2[] Stations;               // genau zwei
        public string[] Kinds;                   // Minispiel je Station ("brakelever" = Hebel halten, "handbrake" = Kurbel)
        public string[] Verbs;                   // Text am Benutzen-Knopf
        public string[] Hints;                   // Schrift ueber der Station
        public Vector2 Button;                   // Lage des Kartenknopfs (Weltkoordinaten)
        public float Seconds;
        public string[] LeverMsgs, CrankMsgs;
        public string LeverTitle, CrankTitle, LeverGauge, CrankGauge, Panel = "task_steel_panel.png";
        public float Shake;                      // Kamera-Rattern waehrend der Krise (0 = keins)
        public string Icon;                      // Motiv des Kartenknopfs (MapIcon): "engine", "meteor", "snow", "lava", "turb"
        public string Fx = "";                   // Welt-Effekt waehrend der Krise (FxTick): "meteor", "blizzard", "lava", "turbulence", "flashlight", "comms"
        public bool Critical = true;             // false: kein Countdown, keine Niederlage, Meeting beendet nichts (wie Licht/Funk)
        // Sabotagen fuer mehrere Karten (MapId 255): Stationen und Kartenknopf je Karte
        public Dictionary<byte, Vector2[]> StationsByMap;
        public Dictionary<byte, Vector2> ButtonByMap;
    }

    public static readonly Def[] Defs =
    {
        new Def
        {
            Id = 1, Key = "SkeldEngineFailure", Title = "Engine Failure", TaskLine = "Engine Failure", MapName = "Skeld",
            MapId = 0, Replaces = SystemTypes.Reactor, ReplacesLabel = "Reactor", BarWord = "STALL", StartSfx = "rush",
            // Upper und Lower Engine, oestlich der Triebwerke (Konsolen bei x -18,3 / -19,2)
            Stations = new[] { new Vector2(-16.6f, -1.3f), new Vector2(-16.6f, -13.4f) },
            Kinds = new[] { "brakelever", "handbrake" },
            Verbs = new[] { "THROTTLE", "PRIME" },
            Hints = new[] { "HOLD THE THROTTLE", "PRIME THE FUEL PUMP" },
            Button = new Vector2(-18.4f, -6.9f), Seconds = 45f, Shake = 0.025f, Icon = "engine",
            LeverMsgs = new[] { "GRAB THE THROTTLE", "PUSH HARDER", "TOO HARD", "HOLDING" },
            CrankMsgs = new[] { "CRANK CLOCKWISE", "FASTER", "TOO FAST", "PRIMING" },
            LeverTitle = "HOLD THE ENGINE THROTTLE", CrankTitle = "PRIME THE FUEL PUMP", LeverGauge = "THRUST", CrankGauge = "PUMP RATE",
        },
        new Def
        {
            Id = 2, Key = "SkeldMeteorShower", Title = "Meteor Shower", TaskLine = "Meteor Shower", MapName = "Skeld",
            MapId = 0, Replaces = SystemTypes.Reactor, ReplacesLabel = "Reactor", BarWord = "HULL DAMAGE", StartSfx = "boom",
            // Weapons (Kanone, Konsole 9,1|1,8) und Shields (Konsole 7,5|-14,0)
            Stations = new[] { new Vector2(8.2f, 1.0f), new Vector2(8.6f, -12.9f) },
            Kinds = new[] { "brakelever", "handbrake" },
            Verbs = new[] { "AIM", "CHARGE" },
            Hints = new[] { "KEEP THE GUNS ON TARGET", "CHARGE THE SHIELDS" },
            Button = new Vector2(10.6f, -4.2f), Seconds = 45f, Shake = 0.02f, Icon = "meteor", Fx = "meteor",
            LeverMsgs = new[] { "GRAB THE TURRET", "PULL HARDER", "OVERSHOT", "ON TARGET" },
            CrankMsgs = new[] { "CRANK CLOCKWISE", "FASTER", "TOO FAST", "CHARGING" },
            LeverTitle = "TRACK THE METEORS", CrankTitle = "CHARGE THE SHIELD GENERATOR", LeverGauge = "AIM", CrankGauge = "CHARGE RATE",
        },
        new Def
        {
            Id = 3, Key = "PolusBlizzard", Title = "Blizzard", TaskLine = "Blizzard", MapName = "Polus",
            MapId = 2, Replaces = SystemTypes.Laboratory, ReplacesLabel = "Seismic", BarWord = "STORM", StartSfx = "rush",
            // zwei Wetterstationen draussen: Ostseite (Temperaturfeld 30,9|-15,3) und Nordwest (Treibstofffeld 11,4|-6,2)
            Stations = new[] { new Vector2(30.2f, -15.9f), new Vector2(12.3f, -6.8f) },
            Kinds = new[] { "brakelever", "handbrake" },
            Verbs = new[] { "STABILIZE", "WIND UP" },
            Hints = new[] { "HOLD THE WEATHER VANE", "WIND UP THE HEATER" },
            Button = new Vector2(21.5f, -8.2f), Seconds = 50f, Shake = 0f, Icon = "snow", Fx = "blizzard",
            LeverMsgs = new[] { "GRAB THE VANE", "PULL HARDER", "TOO FAR", "HOLDING" },
            CrankMsgs = new[] { "CRANK CLOCKWISE", "FASTER", "TOO FAST", "HEATING" },
            LeverTitle = "RESET THE WEATHER STATION", CrankTitle = "WIND UP THE HEATER", LeverGauge = "WIND", CrankGauge = "HEAT",
        },
        new Def
        {
            Id = 4, Key = "PolusLavaFlood", Title = "Lava Flood", TaskLine = "Lava Flood", MapName = "Polus",
            MapId = 2, Replaces = SystemTypes.Laboratory, ReplacesLabel = "Seismic", BarWord = "LAVA", StartSfx = "boom",
            // Kuehlventile: Labor (Kaeltefeld 31,3|-6,7) und Kesselraum (Wasserrad 1,2|-23,1)
            Stations = new[] { new Vector2(30.6f, -7.4f), new Vector2(2.4f, -22.4f) },
            Kinds = new[] { "brakelever", "handbrake" },
            Verbs = new[] { "COOL", "PUMP" },
            Hints = new[] { "OPEN THE COOLANT VALVE", "PUMP COLD WATER" },
            Button = new Vector2(25.0f, -21.2f), Seconds = 45f, Shake = 0.012f, Icon = "lava", Fx = "lava",
            LeverMsgs = new[] { "GRAB THE VALVE", "PULL HARDER", "TOO FAR", "COOLING" },
            CrankMsgs = new[] { "CRANK CLOCKWISE", "FASTER", "TOO FAST", "PUMPING" },
            LeverTitle = "OPEN THE COOLANT VALVE", CrankTitle = "PUMP COLD WATER", LeverGauge = "FLOW", CrankGauge = "PUMP RATE",
        },
        new Def
        {
            Id = 5, Key = "AirshipTurbulence", Title = "Turbulence", TaskLine = "Turbulence", MapName = "Airship",
            MapId = 4, Replaces = SystemTypes.HeliSabotage, ReplacesLabel = "Crash Course", BarWord = "TILT", StartSfx = "rush",
            // Ballast: Cargo Bay (Gasfeld 39,0|1,5) und Gap Room links (Konsole 3,8|9,9)
            Stations = new[] { new Vector2(37.6f, 1.0f), new Vector2(4.6f, 9.3f) },
            Kinds = new[] { "brakelever", "handbrake" },
            Verbs = new[] { "TRIM", "WINCH" },
            Hints = new[] { "TRIM THE BALLAST", "WINCH THE COUNTERWEIGHT" },
            Button = new Vector2(24.2f, -1.2f), Seconds = 45f, Shake = 0.05f, Icon = "turb", Fx = "turbulence",
            LeverMsgs = new[] { "GRAB THE LEVER", "PULL HARDER", "TOO FAR", "TRIMMED" },
            CrankMsgs = new[] { "WINCH CLOCKWISE", "FASTER", "TOO FAST", "WINCHING" },
            LeverTitle = "TRIM THE BALLAST", CrankTitle = "WINCH THE COUNTERWEIGHT", LeverGauge = "BALANCE", CrankGauge = "WINCH RATE",
        },
        new Def
        {
            // Stromausfall mit Taschenlampen: alles dunkel, jeder Crewmate sieht nur einen Lichtkegel in Laufrichtung.
            // Reparatur am Lichtschalter der Karte (Hebel halten). Fungle hat keine Licht-Sabotage: dort nur "Extra".
            Id = 6, Key = "FlashlightBlackout", Title = "Blackout", TaskLine = "Blackout", MapName = "all maps",
            MapId = 255, Replaces = SystemTypes.Electrical, ReplacesLabel = "Lights", BarWord = "POWER", StartSfx = "",
            Critical = false, Icon = "torch", Fx = "flashlight",
            StationsByMap = new Dictionary<byte, Vector2[]>
            {
                [0] = new[] { new Vector2(-9.8f, -10.6f) },     // Skeld Electrical, Schalter (-9,8|-9,9)
                [1] = new[] { new Vector2(14.8f, 20.7f) },      // Mira Office, Schalter (14,8|21,4)
                [2] = new[] { new Vector2(9.7f, -11.8f) },      // Polus Electrical, Schalter (9,7|-11,1)
                [4] = new[] { new Vector2(16.6f, -8.5f) },      // Airship Electrical, Hebelfeld
                [5] = new[] { new Vector2(-3.4f, 4.0f) },       // Fungle: Lagerfeuer (keine Licht-Sabotage)
            },
            ButtonByMap = new Dictionary<byte, Vector2>
            {
                [0] = new Vector2(-7.2f, -12.4f), [1] = new Vector2(16.4f, 19.6f), [2] = new Vector2(7.6f, -12.8f),
                [4] = new Vector2(14.2f, -10.4f), [5] = new Vector2(-1.6f, 5.6f),
            },
            Kinds = new[] { "brakelever" }, Verbs = new[] { "RESTORE" }, Hints = new[] { "RESTORE THE POWER" },
            LeverMsgs = new[] { "GRAB THE BREAKER", "PULL HARDER", "TOO HARD", "RESTORING" },
            CrankMsgs = new[] { "", "", "", "" },
            LeverTitle = "HOLD THE MAIN BREAKER", CrankTitle = "", LeverGauge = "POWER", CrankGauge = "",
        },
        new Def
        {
            // Funkchaos: Aufgabenpfeile zeigen in falsche Richtungen, die Minikarte rauscht. Reparatur an der Funkkonsole.
            Id = 7, Key = "CommsChaos", Title = "Comms Chaos", TaskLine = "Comms Chaos", MapName = "all maps",
            MapId = 255, Replaces = SystemTypes.Comms, ReplacesLabel = "Comms", BarWord = "SIGNAL NOISE", StartSfx = "",
            Critical = false, Icon = "signal", Fx = "comms",
            StationsByMap = new Dictionary<byte, Vector2[]>
            {
                [0] = new[] { new Vector2(4.2f, -16.4f) },      // Skeld Comms (4,2|-17,1)
                [1] = new[] { new Vector2(14.9f, 4.9f) },       // Mira Comms (14,9|5,7)
                [2] = new[] { new Vector2(12.6f, -16.3f) },     // Polus Comms (13,7|-15,6)
                [4] = new[] { new Vector2(-13.6f, 2.0f) },      // Airship Comms (-14,2|2,8)
                [5] = new[] { new Vector2(22.6f, 13.6f) },      // Fungle Comms (23,4|14,8)
            },
            ButtonByMap = new Dictionary<byte, Vector2>
            {
                [0] = new Vector2(6.6f, -16.6f), [1] = new Vector2(13.0f, 4.0f), [2] = new Vector2(14.8f, -17.6f),
                [4] = new Vector2(-11.4f, 1.0f), [5] = new Vector2(20.6f, 11.6f),
            },
            Kinds = new[] { "brakelever" }, Verbs = new[] { "RETUNE" }, Hints = new[] { "RETUNE THE ANTENNA" },
            LeverMsgs = new[] { "GRAB THE DIAL", "TURN HARDER", "TOO FAR", "LOCKING ON" },
            CrankMsgs = new[] { "", "", "", "" },
            LeverTitle = "RETUNE THE ANTENNA", CrankTitle = "", LeverGauge = "SIGNAL", CrankGauge = "",
        },
    };
    public const float FallOne = 25f;            // nicht kritisch: eine Station haelt, Stoerung faellt in ~4 s

    // Eigene Grafik je Krise (tools/vc_art.py, assets/vanilla_crises): Schluessel der Dateien task_vc_<k>_*.png und
    // icon_vc_<k>.png, dazu die Anzeige: Wert bei Stoerung 0 (Mitte der gruenen Zone) und bei 100 (rote Zone bzw.
    // leer bei POWER/SIGNAL, deren gruene Zone oben liegt). Zonen wie in vc_art.gauge.
    private static readonly Dictionary<string, (string Art, float Calm, float Crit)> VcArt = new()
    {
        ["SkeldEngineFailure"] = ("engine", 67.5f, 100f),
        ["SkeldMeteorShower"] = ("meteor", 57.5f, 100f),
        ["PolusBlizzard"] = ("blizzard", 52.5f, 100f),
        ["PolusLavaFlood"] = ("lava", 15f, 100f),
        ["AirshipTurbulence"] = ("turb", 50f, 100f),
        ["FlashlightBlackout"] = ("blackout", 85f, 0f),
        ["CommsChaos"] = ("comms", 85f, 0f),
    };
    private static string ArtOf(Def d) => d != null && VcArt.TryGetValue(d.Key, out var v) ? v.Art : null;

    private static bool OnMap(Def d) => d.MapId == 255 ? d.StationsByMap != null && d.StationsByMap.ContainsKey(MapId()) : d.MapId == MapId();
    private static Vector2[] St(Def d) => d.StationsByMap != null && d.StationsByMap.TryGetValue(MapId(), out var v) ? v : d.Stations;
    private static Vector2 Btn(Def d) => d.ButtonByMap != null && d.ButtonByMap.TryGetValue(MapId(), out var v) ? v : d.Button;

    private static bool AmHost => AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
    private static bool FreePlay => AmongUsClient.Instance != null && AmongUsClient.Instance.NetworkMode == NetworkModes.FreePlay;

    // ------------------------------------------------------------------ Zustand (alle Clients)
    public static Def Current { get; private set; }
    public static bool Active => Current != null;
    public static float Level { get; private set; }
    public static float TimeLeft { get; private set; }
    private static readonly bool[] On = new bool[2];
    private static readonly bool[] MyInput = new bool[2];
    private static ushort _allowed;              // Bitmaske der freigegebenen Krisen (vom Host)
    private static bool _allowKnown;
    private static IntPtr _ship;                 // ShipStatus, fuer den die Runde vorbereitet ist

    // Host
    private static readonly HashSet<byte>[] Users = { new(), new() };
    private static float _hostSendAt, _allowSendAt;
    private static int _allowSends;

    public static void Reset()
    {
        Current = null; Level = 0f; TimeLeft = 0f;
        On[0] = On[1] = MyInput[0] = MyInput[1] = false;
        Users[0].Clear(); Users[1].Clear();
        _allowed = 0; _allowKnown = false; _allowSends = 0; _allowSendAt = 0f;
        _hint = null; _arrows.Clear();
    }

    /// <summary>Vanilla-Karte, keine Atlas-Karte gebaut, Runde laeuft (oder Freeplay).</summary>
    private static bool OnVanillaRound()
    {
        var ship = ShipStatus.Instance;
        if (ship == null || AtlasMuseumBuilder.Active || AmongUsClient.Instance == null) return false;
        if (!FreePlay && AmongUsClient.Instance.GameState != InnerNet.InnerNetClient.GameStates.Started) return false;
        return true;
    }

    /// <summary>Geladene Karte: 0 Skeld, 1 Mira, 2 Polus, 4 Airship, 5 Fungle, 3 Dleks (gespiegelt, keine Krisen).
    /// Am ShipStatus erkannt, nicht an der Option (im Freeplay bleibt sie auf der Skeld, auch wenn Polus laeuft).</summary>
    private static byte MapId()
    {
        try
        {
            var ship = ShipStatus.Instance;
            if (ship != null)
            {
                if (ship.TryCast<AirshipStatus>() != null) return 4;
                if (ship.TryCast<FungleShipStatus>() != null) return 5;
                if (ship.Type == ShipStatus.MapType.Hq) return 1;
                if (ship.Type == ShipStatus.MapType.Pb) return 2;
                if (ship.Type == ShipStatus.MapType.Ship) return ship.transform.localScale.x < 0f ? (byte)3 : (byte)0;
            }
            return GameOptionsManager.Instance.CurrentGameOptions.MapId;
        }
        catch { return 255; }
    }

    /// <summary>Krisen dieser Karte, die die Einstellungen erlauben (Autotest: alle).</summary>
    private static IEnumerable<Def> Configured()
    {
        byte map = MapId();
        bool test = DiagOn;
        if (!test && !AtlasVanillaOptions.On) yield break;
        foreach (var d in Defs)
            if (OnMap(d) && (test || AtlasVanillaOptions.ModeOf(d.Id) != AtlasVanillaOptions.Mode.Off)) yield return d;
    }

    private static bool Allowed(Def d) => _allowKnown && (_allowed & (1 << d.Id)) != 0;

    private static bool Replaced(SystemTypes sys)
    {
        if (!_allowKnown || DiagOn) return false;
        foreach (var d in Defs)
            if (OnMap(d) && d.Replaces == sys && Allowed(d) && AtlasVanillaOptions.ModeOf(d.Id) == AtlasVanillaOptions.Mode.Replace) return true;
        return false;
    }

    // ------------------------------------------------------------------ Netz

    private static void Send(byte sub, Action<MessageWriter> body) =>
        AtlasWorld.Send(OpCrisis, w => { w.Write(sub); body?.Invoke(w); });

    /// <summary>Aus AtlasWorld.PlayerControl_HandleRpc_Postfix, vor dessen Atlas-Karten-Pruefung.</summary>
    internal static void Receive(PlayerControl from, bool fromHost, MessageReader r)
    {
        byte sub = r.ReadByte();
        switch (sub)
        {
            case SubAllow when fromHost: _allowed = r.ReadUInt16(); _allowKnown = true; break;
            case SubStart when fromHost:
            {
                byte id = r.ReadByte();
                float sec = r.ReadUInt16() / 10f;
                var d = Find(id);
                if (d != null) ApplyStart(d, sec);
                break;
            }
            case SubState when fromHost:
                Level = r.ReadByte();
                TimeLeft = r.ReadUInt16() / 10f;
                { byte f = r.ReadByte(); On[0] = (f & 1) != 0; On[1] = (f & 2) != 0; }
                break;
            case SubEnd when fromHost: ApplyEnd(r.ReadByte()); break;
            case SubInput when AmHost: HostInput(from, r.ReadByte(), r.ReadBoolean()); break;
            case SubRequest when AmHost: HostRequest(from, r.ReadByte()); break;
        }
    }

    private static Def Find(byte id)
    {
        foreach (var d in Defs) if (d.Id == id) return d;
        return null;
    }

    public static void SetInput(byte station, bool on)
    {
        if (station > 1 || MyInput[station] == on) return;
        MyInput[station] = on;
        if (!Active && on) return;
        if (AmHost) HostInput(PlayerControl.LocalPlayer, station, on);
        else Send(SubInput, w => { w.Write(station); w.Write(on); });
    }

    public static void Request(byte id)
    {
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} map button {id} clicked");
        if (AmHost) HostRequest(PlayerControl.LocalPlayer, id);
        else Send(SubRequest, w => w.Write(id));
    }

    // ------------------------------------------------------------------ Host

    private static void HostPrepare()
    {
        // Freigabe: nur wenn jeder dieselbe Atlas-Version hat (Freeplay: immer)
        ushort mask = 0;
        var missing = FreePlay ? new List<string>() : AtlasHandshake.VersionMismatches();
        if (missing.Count == 0)
            foreach (var d in Configured()) mask |= (ushort)(1 << d.Id);
        else if (Configured().GetEnumerator().MoveNext())
            AtlasPlugin.Logger.LogWarning($"{LogPrefix} extra sabotages disabled this round, not everyone has this Atlas: {string.Join("; ", missing)}");
        _allowed = mask; _allowKnown = true;
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} round on map {MapId()}: allowed mask {mask}");
    }

    private static void HostRequest(PlayerControl from, byte id)
    {
        var d = Find(id);
        if (d == null || from == null || from.Data == null || from.Data.Role == null || !from.Data.Role.IsImpostor) return;
        if (!Allowed(d) || !OnMap(d)) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} refused: not allowed this round"); return; }
        HostTryStart(d);
    }

    internal static bool HostTryStart(Def d)
    {
        if (Active || CriticalActive()) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} refused: a critical sabotage is running"); return false; }
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && (sab.AnyActive || sab.Timer > 0f))
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} refused: sabotage active {sab.AnyActive}, shared cooldown {sab.Timer:F0} s");
            return false;
        }
        HostStart(d);
        return true;
    }

    private static void HostStart(Def d)
    {
        Users[0].Clear(); Users[1].Clear();
        _hostSendAt = 0f;
        LockSabotages();
        ApplyStart(d, d.Seconds);
        Send(SubStart, w => { w.Write(d.Id); w.Write((ushort)Mathf.Clamp(Mathf.RoundToInt(d.Seconds * 10f), 0, 65535)); });
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} host: {d.Key} started ({d.Seconds:F0} s)");
    }

    /// <summary>Laeuft eine kritische Sabotage (Vanilla oder eigene)?</summary>
    internal static bool CriticalActive()
    {
        if (Active) return true;
        var r = SabKit.Sys<ReactorSystemType>(SystemTypes.Reactor);
        var lab = SabKit.Sys<ReactorSystemType>(SystemTypes.Laboratory);
        var o = SabKit.Sys<LifeSuppSystemType>(SystemTypes.LifeSupp);
        var heli = SabKit.Sys<HeliSabotageSystem>(SystemTypes.HeliSabotage);
        return (r != null && r.IsActive) || (lab != null && lab.IsActive) || (o != null && o.IsActive) || (heli != null && heli.IsActive);
    }

    private static void HostInput(PlayerControl from, byte station, bool on)
    {
        if (!Active || from == null || from.Data == null || from.Data.IsDead || station > 1) return;
        if (on) Users[station].Add(from.PlayerId); else Users[station].Remove(from.PlayerId);
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

    private static void LockSabotages()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null && sab.Timer < 29.5f) AtlasRex.SetSabotageTimer(30f);
    }

    private static void HostTick(float dt)
    {
        if (!Current.Critical)
        {
            // wie Licht/Funk: kein Countdown, keine Niederlage, uebersteht Meetings; eine Station haelt -> repariert
            Prune(Users[0]); Prune(Users[1]);
            On[0] = Users[0].Count > 0; On[1] = Users[1].Count > 0;
            if (MeetingHud.Instance == null && (On[0] || On[1])) Level = Mathf.Max(0f, Level - FallOne * dt);
            LockSabotages();
            if (Time.time >= _hostSendAt) { _hostSendAt = Time.time + 0.25f; SendState(); }
            if (Level <= 0f) HostEnd(EndFixed);
            return;
        }
        if (MeetingHud.Instance != null || ExileController.Instance != null) { HostEnd(EndMeeting); return; }
        Prune(Users[0]); Prune(Users[1]);
        bool a = Users[0].Count > 0, b = Users[1].Count > 0;
        On[0] = a; On[1] = b;
        float rate = a && b ? -FallBoth : a || b ? 0f : RiseNone;
        Level = Mathf.Clamp(Level + rate * dt, 0f, 100f);
        TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        LockSabotages();
        if (Time.time >= _hostSendAt) { _hostSendAt = Time.time + 0.25f; SendState(); }
        if (Level <= 0f) HostEnd(EndFixed);
        else if (Level >= 100f || TimeLeft <= 0f) HostEnd(EndLost);
    }

    private static void SendState()
    {
        byte o = (byte)Mathf.Clamp(Mathf.RoundToInt(Level), 0, 100);
        ushort t = (ushort)Mathf.Clamp(Mathf.RoundToInt(TimeLeft * 10f), 0, 65535);
        byte f = (byte)((On[0] ? 1 : 0) | (On[1] ? 2 : 0));
        Send(SubState, w => { w.Write(o); w.Write(t); w.Write(f); });
    }

    internal static void HostEnd(byte result)
    {
        if (!Active) return;
        var d = Current;
        SendState();
        ApplyEnd(result);
        Send(SubEnd, w => w.Write(result));
        Users[0].Clear(); Users[1].Clear();
        AtlasRex.SetSabotageTimer(30f);
        if (result == EndLost) EndGame(d);
    }

    private static void EndGame(Def d)
    {
        if (FreePlay || GameManager.Instance == null)
        {
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} lost - freeplay: the game would end now (ImpostorBySabotage)");
            return;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} lost - impostors win by sabotage");
        GameManager.Instance.RpcEndGame(GameOverReason.ImpostorBySabotage, false);
    }

    // ------------------------------------------------------------------ Anwenden (alle Clients)

    private static void ApplyStart(Def d, float sec)
    {
        Current = d;
        TimeLeft = sec; Level = d.Critical ? StartLevel : 100f;
        On[0] = On[1] = MyInput[0] = MyInput[1] = false;
        _flashStart = Time.time;
        if (!string.IsNullOrEmpty(d.StartSfx)) AtlasWeatherFx.Sfx(d.StartSfx, 0.8f);
        MakeArrows(d);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key}: {sec:F0} s");
    }

    private static void ApplyEnd(byte result)
    {
        if (!Active) return;
        var d = Current;
        Current = null;
        Level = 0f; On[0] = On[1] = MyInput[0] = MyInput[1] = false;
        FlashTick();
        ClearArrows();
        ShowHint(-1, default);
        StripTaskLine(d);
        AtlasCrisisHud.Hide("vcrisis");
        SetShake(0f);
        FxClear();
        if (result == EndLost) AtlasWeatherFx.Sfx("boom", 1f);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} {d.Key} ended: {(result == EndFixed ? "fixed" : result == EndMeeting ? "meeting" : "lost")}");
    }

    // ------------------------------------------------------------------ Takt

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_Postfix()
    {
        try { Tick(Time.deltaTime); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} tick: {e.Message}"); }
    }

    private static void Tick(float dt)
    {
        if (!OnVanillaRound()) return;
        var ship = ShipStatus.Instance;
        if (ship.Pointer != _ship)
        {
            Reset();
            _ship = ship.Pointer;
            if (AmHost) HostPrepare();
        }
        if (AmHost && _allowSends < 3 && Time.time >= _allowSendAt)
        {
            // dreimal im Abstand von 3 s, falls ein Gast seinen ShipStatus erst spaet baut
            _allowSends++; _allowSendAt = Time.time + 3f;
            ushort m = _allowed;
            Send(SubAllow, w => w.Write(m));
        }
        DiagTick();
        FlashTick();
        if (!Active) return;
        if (AmHost) HostTick(dt);
        else if (Current.Critical) TimeLeft = Mathf.Max(0f, TimeLeft - dt);
        if (!Active) return;
        var d = Current;
        ArrowsTick();
        TaskLineTick(d);
        bool blink = Mathf.Repeat(Time.time, 1f) < 0.5f;
        if (d.Critical)
            AtlasCrisisHud.Show("vcrisis", $"{d.Title.ToUpperInvariant()}  {Mathf.CeilToInt(TimeLeft)}s   ({d.BarWord.ToLowerInvariant()} {Mathf.RoundToInt(Level)}%   {d.Verbs[0].ToLowerInvariant()} {(On[0] ? "ON" : "off")}   {d.Verbs[1].ToLowerInvariant()} {(On[1] ? "ON" : "off")})",
                                blink ? new Color(1f, 0.45f, 0.4f) : new Color(1f, 0.29f, 0.25f));
        else
            AtlasCrisisHud.Show("vcrisis", $"{d.Title.ToUpperInvariant()}   ({d.BarWord.ToLowerInvariant()} {Mathf.RoundToInt(Level)}%)", new Color(1f, 0.75f, 0.35f));
        SetShake(MeetingHud.Instance == null ? d.Shake * (0.5f + Level / 100f) * (d.Fx == "turbulence" ? 0.6f + 0.6f * Mathf.PerlinNoise(Time.time * 0.7f, 3.1f) : 1f) : 0f);
        FxTick(d);
        ClickTick(d);
        AtlasUse.Commit();
    }

    private static void SetShake(float amount)
    {
        try
        {
            var cam = Camera.main != null ? Camera.main.GetComponent<FollowerCamera>() : null;
            if (cam == null) return;
            cam.shakeAmount = amount;
            cam.shakePeriod = 30f;
        }
        catch { }
    }

    // ------------------------------------------------------------------ Welt-Effekte je Krise

    private static SpriteRenderer _tint, _snowA, _snowB, _burst, _heat;
    private static float _nextImpact, _impactUntil;
    private static Vector2 _burstAt;
    private const float SnowFarTile = 2.4f, SnowNearTile = 3.2f, HeatTile = 9f, BurstSize = 5.5f;

    // Effektbilder aus tools/vc_art.py (fx_vc_*.png); null, wenn die Datei fehlt (dann Laufzeitformen wie zuvor)
    private static Sprite FxSprite(string file, float width, bool white = false) =>
        AtlasAssets.OwnSprite(file, width, false, TextureWrapMode.Repeat, false, white);

    private static SpriteRenderer Overlay(string name, Sprite sprite, bool tiled = true)
    {
        var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
        if (fs == null) return null;
        var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
        go.name = name;
        var sr = go.GetComponent<SpriteRenderer>();
        if (sr == null) { Object.Destroy(go); return null; }
        if (sprite != null)
        {
            sr.sprite = sprite;
            sr.drawMode = tiled ? SpriteDrawMode.Tiled : SpriteDrawMode.Simple;
            if (tiled) sr.size = new Vector2(40f, 24f);
            go.transform.localScale = Vector3.one;
        }
        sr.enabled = true;
        go.SetActive(true);
        return sr;
    }

    private static void FxTick(Def d)
    {
        bool meeting = MeetingHud.Instance != null;
        float t = Time.time;
        switch (d.Fx)
        {
            case "meteor":
                // Einschlag alle 2,5..5 s: Lichtblitz (fx_vc_meteor_flash) an zufaelliger Stelle, heller Schleier, Donner, Rattern
                if (_tint == null) _tint = Overlay("Atlas_VCrisisTint", null);
                if (_burst == null) { var bs = FxSprite("fx_vc_meteor_flash.png", BurstSize); if (bs != null) _burst = Overlay("Atlas_VCrisisBurst", bs, false); }
                if (!meeting && t >= _nextImpact)
                {
                    _nextImpact = t + UnityEngine.Random.Range(2.5f, 5f); _impactUntil = t + 0.35f; AtlasWeatherFx.Sfx("boom", 0.45f);
                    _burstAt = new Vector2(UnityEngine.Random.Range(-3.5f, 3.5f), UnityEngine.Random.Range(-1.8f, 1.8f));
                }
                {
                    float kb = t < _impactUntil && !meeting ? (_impactUntil - t) / 0.35f : 0f;    // 1 -> 0
                    if (_tint != null)
                    {
                        float a = (_burst != null ? 0.22f : 0.45f) * Mathf.Clamp01(kb * 2f - 1f);
                        _tint.color = new Color(1f, 0.95f, 0.85f, a);
                        _tint.gameObject.SetActive(a > 0.001f);
                    }
                    if (_burst != null)
                    {
                        _burst.gameObject.SetActive(kb > 0.001f);
                        _burst.color = new Color(1f, 1f, 1f, Mathf.Clamp01(kb * 1.6f));
                        float sc = Mathf.Lerp(1.5f, 0.7f, kb);
                        _burst.transform.localScale = new Vector3(sc, sc, 1f);
                        var bp = _burst.transform.localPosition;
                        _burst.transform.localPosition = new Vector3(_burstAt.x, _burstAt.y, bp.z);
                    }
                }
                break;
            case "lava":
                // pulsierender Hitzeschein; darueber Hitzeschimmer (fx_vc_heat, kachelnd), steigt langsam und wabert
                if (_tint == null) _tint = Overlay("Atlas_VCrisisTint", null);
                if (_heat == null) { var hs = FxSprite("fx_vc_heat.png", HeatTile); if (hs != null) _heat = Overlay("Atlas_VCrisisHeat", hs); }
                {
                    float pulse = 0.08f + 0.06f * Mathf.Sin(t * 2.2f), strength = 0.6f + Level / 150f;
                    if (_tint != null)
                    {
                        float a = meeting ? 0f : pulse * strength * (_heat != null ? 0.55f : 1f);
                        _tint.color = new Color(1f, 0.42f, 0.08f, a);
                        _tint.gameObject.SetActive(a > 0.001f);
                    }
                    if (_heat != null)
                    {
                        float a = meeting ? 0f : Mathf.Clamp01((0.75f + 2f * (pulse - 0.08f)) * strength);
                        _heat.gameObject.SetActive(a > 0.001f);
                        _heat.color = new Color(1f, 1f, 1f, a);
                        var hp = _heat.transform.localPosition;
                        _heat.transform.localPosition = new Vector3(0.35f * Mathf.Sin(t * 0.9f), Mathf.Repeat(t * 0.45f, HeatTile) - HeatTile / 2f, hp.z);
                    }
                }
                break;
            case "flashlight": FlashlightTick(meeting); break;
            case "comms": CommsTick(); break;
            case "blizzard":
                // Schneetreiben (zwei Ebenen) und ein kalter Schleier, draussen dichter (BlizzardOutside)
                // fern: fx_vc_snow_far (kleine Flocken, langsam), nah: fx_vc_snow_near (grosse, schnell); sonst Laufzeitkacheln
                if (_snowA == null) _snowA = Overlay("Atlas_VCrisisSnowA", FxSprite("fx_vc_snow_far.png", SnowFarTile, true) ?? SnowSprite(0));
                if (_snowB == null) _snowB = Overlay("Atlas_VCrisisSnowB", FxSprite("fx_vc_snow_near.png", SnowNearTile, true) ?? SnowSprite(1));
                if (_tint == null) _tint = Overlay("Atlas_VCrisisTint", null);
                bool outside = BlizzardOutside();
                float k = meeting ? 0f : outside ? 1f : 0.25f;
                foreach (var (sr, speed, phase) in new[] { (_snowA, 1.6f, 0f), (_snowB, 2.7f, 5f) })
                {
                    if (sr == null) continue;
                    sr.gameObject.SetActive(k > 0f);
                    sr.color = new Color(1f, 1f, 1f, 0.85f * k);
                    float tile = sr.sprite != null ? sr.sprite.bounds.size.x : 4f;            // Verschiebung im Kachelmass: nahtlos
                    var p = sr.transform.localPosition;
                    sr.transform.localPosition = new Vector3(Mathf.Repeat(t * speed * 0.6f + phase, tile) - tile / 2f, tile / 2f - Mathf.Repeat(t * speed + phase, tile), p.z);
                }
                if (_tint != null) { _tint.color = new Color(0.85f, 0.92f, 1f, 0.22f * k); _tint.gameObject.SetActive(k > 0f); }
                break;
        }
    }

    private static void FxClear()
    {
        foreach (var sr in new[] { _tint, _snowA, _snowB, _dark, _noise, _burst, _heat }) if (sr != null) Object.Destroy(sr.gameObject);
        _tint = _snowA = _snowB = _dark = _noise = _burst = _heat = null;
        FakeTargets.Clear();
        _nextImpact = _impactUntil = 0f;
    }

    // ---- Taschenlampe: schwarze Flaeche mit Lichtkegel, folgt dem Spieler und seiner Laufrichtung (HUD-Ebene wie
    // der rote Reaktor-Blitz, unter den Knoepfen). Impostor und Geister sehen normal.
    private static SpriteRenderer _dark;
    private static Vector2 _look = Vector2.right;
    private static Sprite _coneSprite;
    private const float ConeWorld = 30f;

    private static void FlashlightTick(bool meeting)
    {
        var lp = PlayerControl.LocalPlayer;
        bool affected = !meeting && lp != null && lp.Data != null && !lp.Data.IsDead && !(lp.Data.Role != null && lp.Data.Role.IsImpostor);
        if (_dark == null)
        {
            if (!affected) return;
            // in der Welt, nicht im HUD: knapp vor den Spielern (z -1), hinter Aufgabenliste und Knoepfen (die HUD-Ebene
            // haette sie mit abgedeckt, Test 20.10.)
            var go = new GameObject("Atlas_VCrisisDark") { layer = lp.gameObject.layer };
            _dark = go.AddComponent<SpriteRenderer>();
            _dark.sprite = ConeSprite();
            _dark.color = Color.white;
        }
        _dark.gameObject.SetActive(affected);
        if (!affected) return;
        try
        {
            var v = lp.MyPhysics != null && lp.MyPhysics.body != null ? lp.MyPhysics.body.velocity : Vector2.zero;
            if (v.sqrMagnitude > 0.02f) _look = Vector2.Lerp(_look, v.normalized, 0.2f).normalized;
        }
        catch { }
        var p = lp.transform.position;
        _dark.transform.position = new Vector3(p.x, p.y, -1f);
        _dark.transform.rotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(_look.y, _look.x) * Mathf.Rad2Deg);
    }

    /// <summary>Schwarz mit Loch: kleiner Kreis um den Spieler (0,7) und Kegel nach +x (+-30 Grad, 4,2 Einheiten).</summary>
    private static Sprite ConeSprite()
    {
        if (_coneSprite != null) return _coneSprite;
        const int N = 512;
        float ppu = N / ConeWorld;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave };
        var px = new Color32[N * N];
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float wx = (x + 0.5f - N / 2f) / ppu, wy = (y + 0.5f - N / 2f) / ppu;
                float r = Mathf.Sqrt(wx * wx + wy * wy);
                float ang = Mathf.Abs(Mathf.Atan2(wy, wx)) * Mathf.Rad2Deg;
                float lightCircle = Mathf.Clamp01((0.9f - r) / 0.25f);
                float lightCone = wx > 0f ? Mathf.Clamp01((30f - ang) / 6f) * Mathf.Clamp01((4.2f - r) / 1.2f) : 0f;
                float light = Mathf.Max(lightCircle, lightCone);
                px[y * N + x] = new Color32(0, 0, 0, (byte)(250f * (1f - light)));
            }
        tex.SetPixels32(px);
        tex.Apply();
        _coneSprite = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), ppu);
        _coneSprite.hideFlags |= HideFlags.HideAndDontSave;
        return _coneSprite;
    }

    // ---- Funkchaos: Aufgabenpfeile auf falsche Ziele (je Aufgabe fest, alle 8 s neu), Rauschen ueber der Minikarte
    private static readonly Dictionary<IntPtr, Vector3> FakeTargets = new();
    private static SpriteRenderer _noise;
    private static float _fakeUntil;
    private const float NoiseTile = 2.5f;

    private static void CommsTick()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || lp.myTasks == null) return;
        if (Time.time >= _fakeUntil)
        {
            _fakeUntil = Time.time + 8f;
            FakeTargets.Clear();
            var rnd = new System.Random((int)(Time.time * 10f));
            foreach (var t in lp.myTasks)
            {
                var nt = t != null ? t.TryCast<NormalPlayerTask>() : null;
                if (nt == null || nt.Arrow == null) continue;
                var p = lp.transform.position;
                float a = (float)(rnd.NextDouble() * Mathf.PI * 2f), dist = 6f + (float)rnd.NextDouble() * 10f;
                FakeTargets[nt.Arrow.Pointer] = new Vector3(p.x + Mathf.Cos(a) * dist, p.y + Mathf.Sin(a) * dist, 0f);
            }
        }
        var map = MapBehaviour.Instance;
        bool open = map != null && map.IsOpen && MeetingHud.Instance == null;
        if (!open) { if (_noise != null) _noise.gameObject.SetActive(false); return; }
        if (_noise == null || _noise.transform.parent != map.transform)
        {
            if (_noise != null) Object.Destroy(_noise.gameObject);
            var go = new GameObject("Atlas_VCrisisNoise") { layer = map.gameObject.layer };
            go.transform.SetParent(map.transform, false);
            go.transform.localPosition = new Vector3(0f, 0f, -20f);
            _noise = go.AddComponent<SpriteRenderer>();
            _noise.sprite = FxSprite("fx_vc_noise.png", NoiseTile) ?? SnowSprite(0);
            _noise.drawMode = SpriteDrawMode.Tiled;
            _noise.size = new Vector2(14f, 9f);
            _noise.sortingOrder = 50;
        }
        _noise.gameObject.SetActive(true);
        _noise.color = new Color(1f, 1f, 1f, 0.6f + 0.3f * Mathf.PerlinNoise(Time.time * 9f, 0.3f));
        // Rauschbild springt jedes Bild um bis zu eine halbe Kachel: wirkt wie wechselndes Funkrauschen
        _noise.transform.localPosition = new Vector3(UnityEngine.Random.Range(-NoiseTile / 2f, NoiseTile / 2f), UnityEngine.Random.Range(-NoiseTile / 2f, NoiseTile / 2f), -20f);
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(ArrowBehaviour), nameof(ArrowBehaviour.Update))]
    internal static void ArrowBehaviour_Update_Prefix(ArrowBehaviour __instance)
    {
        if (FakeTargets.Count == 0 || Current == null || Current.Fx != "comms" || __instance == null) return;
        if (FakeTargets.TryGetValue(__instance.Pointer, out var t)) __instance.target = t;
    }

    private static readonly Sprite[] Snow = new Sprite[2];

    /// <summary>Kachel mit Schneeflocken (Laufzeit-Textur, nahtlos), zwei Groessen fuer die Parallaxe.</summary>
    private static Sprite SnowSprite(int layer)
    {
        if (Snow[layer] != null) return Snow[layer];
        const int N = 256;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave, wrapMode = TextureWrapMode.Repeat };
        var px = new Color32[N * N];
        var rnd = new System.Random(40 + layer);
        int flakes = layer == 0 ? 70 : 28;
        float rad = layer == 0 ? 1.6f : 3.2f;
        for (int i = 0; i < flakes; i++)
        {
            int cx = rnd.Next(N), cy = rnd.Next(N);
            for (int dy = -5; dy <= 5; dy++)
                for (int dx = -5; dx <= 5; dx++)
                {
                    float r = Mathf.Sqrt(dx * dx + dy * dy);
                    if (r > rad + 1f) continue;
                    int x = (cx + dx + N) % N, y = (cy + dy + N) % N;
                    byte a = (byte)(255f * Mathf.Clamp01(rad + 1f - r));
                    if (a > px[y * N + x].a) px[y * N + x] = new Color32(255, 255, 255, a);
                }
        }
        tex.SetPixels32(px);
        tex.Apply();
        Snow[layer] = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), N / 4f, 0, SpriteMeshType.FullRect);
        Snow[layer].hideFlags |= HideFlags.HideAndDontSave;
        return Snow[layer];
    }

    /// <summary>Polus: steht der lokale Spieler draussen (in keinem Raum ausser "Outside")?</summary>
    private static bool BlizzardOutside()
    {
        var lp = PlayerControl.LocalPlayer;
        var ship = ShipStatus.Instance;
        if (lp == null || ship == null || ship.AllRooms == null) return false;
        var pos = lp.GetTruePosition();
        foreach (var room in ship.AllRooms)
        {
            if (room == null || room.roomArea == null || room.RoomId == SystemTypes.Outside) continue;
            if (room.roomArea.OverlapPoint(pos)) return false;
        }
        return true;
    }

    /// <summary>Schneesturm: draussen nur 55 % der Sicht (nicht fuer Impostor-Sicht, wie Licht-Sabotage).</summary>
    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.CalculateLightRadius))]
    internal static void ShipStatus_CalculateLightRadius_Postfix([HarmonyArgument(0)] NetworkedPlayerInfo player, ref float __result)
    {
        try
        {
            if (Current == null || Current.Fx != "blizzard" || player == null || player.Role == null || player.Role.IsImpostor) return;
            if (PlayerControl.LocalPlayer == null || player.PlayerId != PlayerControl.LocalPlayer.PlayerId) return;
            if (BlizzardOutside()) __result *= 0.55f;
        }
        catch { }
    }

    // ------------------------------------------------------------------ Rotes Blinken wie beim Reaktor

    private static SpriteRenderer _flash;
    private static float _flashStart;

    private static void FlashTick()
    {
        bool want = Active && Current.Critical && MeetingHud.Instance == null && Mathf.Repeat(Time.time - _flashStart, 2f) < 1f;
        if (_flash == null)
        {
            if (!want) return;
            var fs = HudManager.InstanceExists ? HudManager.Instance.FullScreen : null;
            if (fs == null) return;
            var go = Object.Instantiate(fs.gameObject, fs.transform.parent);
            go.name = "Atlas_VanillaCrisisFlash";
            _flash = go.GetComponent<SpriteRenderer>();
            if (_flash == null) { Object.Destroy(go); return; }
            _flash.enabled = true;
        }
        if (_flash.gameObject.activeSelf != want) _flash.gameObject.SetActive(want);
        if (want) _flash.color = new Color(1f, 0f, 0f, 0.373f);
    }

    // ------------------------------------------------------------------ Pfeile, Aufgabenliste

    private static readonly List<ArrowBehaviour> _arrows = new();

    private static void MakeArrows(Def d)
    {
        ClearArrows();
        try
        {
            var template = AtlasRex.VanillaArrow();
            foreach (var p in St(d))
            {
                ArrowBehaviour ab;
                if (template != null)
                {
                    var go = Object.Instantiate(template.gameObject);
                    go.name = "Atlas_VanillaCrisisArrow";
                    go.SetActive(true);
                    ab = go.GetComponent<ArrowBehaviour>();
                    if (ab != null) { ab.MaxScale = 0.5f; ab.transform.localScale = Vector3.one * 0.5f; if (ab.image != null) ab.image.color = Color.red; }
                }
                else
                {
                    var go = new GameObject("Atlas_VanillaCrisisArrow") { layer = 5 };
                    var sr = go.AddComponent<SpriteRenderer>();
                    sr.sprite = AtlasRex.ArrowSprite();
                    sr.color = new Color(1f, 0.3f, 0.25f);
                    ab = go.AddComponent<ArrowBehaviour>();
                    ab.image = sr;
                }
                if (ab == null) continue;
                ab.target = new Vector3(p.x, p.y, 0f);
                _arrows.Add(ab);
            }
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

    private static string Mark(Def d) => $"<color=#FF4A3F>{d.TaskLine}";

    private static void TaskLineTick(Def d)
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel == null || panel.taskText == null) return;
            string text = Strip(panel.taskText.text ?? "", Mark(d));
            string line = d.Critical
                ? $"{Mark(d)}! {Mathf.CeilToInt(TimeLeft)}s</color> <color=#FFD27A>({d.BarWord.ToLowerInvariant()} {Mathf.RoundToInt(Level)}%)</color>\n"
                : $"{Mark(d)}</color> <color=#FFD27A>({d.Hints[0].ToLowerInvariant()})</color>\n";
            panel.taskText.text = line + text;
        }
        catch { }
    }

    private static void StripTaskLine(Def d)
    {
        try
        {
            var panel = HudManager.Instance != null ? HudManager.Instance.TaskPanel : null;
            if (panel != null && panel.taskText != null) panel.taskText.text = Strip(panel.taskText.text ?? "", Mark(d));
        }
        catch { }
    }

    private static string Strip(string text, string mark)
    {
        int at;
        while ((at = text.IndexOf(mark, StringComparison.Ordinal)) >= 0)
        {
            int nl = text.IndexOf('\n', at);
            text = text.Substring(0, at) + (nl >= 0 ? text.Substring(nl + 1) : "");
        }
        return text;
    }

    // ------------------------------------------------------------------ Stationen

    private static TextMeshPro _hint;

    private static void ClickTick(Def d)
    {
        var lp = PlayerControl.LocalPlayer;
        int st = -1;
        var sts = St(d);
        for (int i = 0; i < sts.Length; i++) if (AtlasUse.CanReach(lp, sts[i], Reach)) { st = i; break; }
        ShowHint(st, st >= 0 ? sts[st] : default);
        if (st < 0) return;
        int s = st;
        AtlasUse.Offer(d.Verbs[s], "task_button.png", () => OpenStation(d, s));
        if (!Input.GetMouseButtonDown(0) || Camera.main == null) return;
        Vector2 click = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        if (Vector2.Distance(click, sts[s] + new Vector2(0f, 0.4f)) < 1.2f) OpenStation(d, s);
    }

    private static void ShowHint(int station, Vector2 at)
    {
        if (station < 0 || Current == null) { if (_hint != null) _hint.gameObject.SetActive(false); return; }
        if (_hint == null)
        {
            var go = new GameObject("Atlas_VanillaCrisisHint") { layer = 11 };
            if (ShipStatus.Instance != null) go.transform.SetParent(ShipStatus.Instance.transform, false);
            _hint = go.AddComponent<TextMeshPro>();
            var src = HudManager.Instance != null ? HudManager.Instance.GetComponentInChildren<TextMeshPro>(true) : null;
            if (src != null) { _hint.font = src.font; _hint.fontSharedMaterial = src.fontSharedMaterial; }
            _hint.fontSize = 2.2f; _hint.alignment = TextAlignmentOptions.Center; _hint.enableWordWrapping = false;
            _hint.color = new Color(1f, 0.55f, 0.45f);
            _hint.rectTransform.sizeDelta = new Vector2(6f, 1f);
            var mr = go.GetComponent<MeshRenderer>(); if (mr != null) mr.sortingOrder = 200;
        }
        _hint.gameObject.SetActive(true);
        _hint.text = Current.Hints[station];
        _hint.transform.position = new Vector3(at.x, at.y + 1.4f, -2f);
    }

    internal static void OpenStation(Def d, int station)
    {
        if (Minigame.Instance != null || Camera.main == null || PlayerControl.LocalPlayer == null) return;
        byte idx = (byte)station;
        CrisisLink.Active = () => Active;
        CrisisLink.Over = () => Level;
        CrisisLink.TimeLeft = () => TimeLeft;
        // Hebel und Kurbel melden fest Station 0 bzw. 1 (AtlasRunaway.Brake/Handbrake); hier zaehlt die geoeffnete
        CrisisLink.SetInput = (_, on) => SetInput(idx, on);
        CrisisLink.BarWord = d.BarWord;
        CrisisLink.LeverMsgs = d.LeverMsgs;
        CrisisLink.CrankMsgs = d.CrankMsgs;
        CrisisLink.LeverTitle = d.LeverTitle; CrisisLink.CrankTitle = d.CrankTitle;
        CrisisLink.LeverGauge = d.LeverGauge; CrisisLink.CrankGauge = d.CrankGauge;
        CrisisLink.ArtKey = ArtOf(d);
        string vcPanel = CrisisLink.VcArt("panel");
        CrisisLink.Panel = vcPanel ?? d.Panel;
        if (VcArt.TryGetValue(d.Key, out var g)) { CrisisLink.GaugeCalm = g.Calm; CrisisLink.GaugeCrit = g.Crit; }
        var go = new GameObject($"AtlasTask_{d.Kinds[station]}") { layer = 5 };
        go.transform.SetParent(Camera.main.transform, false);
        go.transform.localPosition = new Vector3(0f, 0f, -50f);
        var mg = go.AddComponent<AtlasMinigame>();
        mg.TransType = TransitionType.SlideBottom;
        PlayerTask any = null;
        foreach (var t in PlayerControl.LocalPlayer.myTasks) if (t != null) { any = t; break; }
        mg.Begin(any);
    }

    // ------------------------------------------------------------------ Sabotage-Karte

    [HarmonyPostfix]
    [HarmonyPatch(typeof(MapBehaviour), nameof(MapBehaviour.Show))]
    internal static void MapBehaviour_Show_Postfix(MapBehaviour __instance)
    {
        try { if (OnVanillaRound() && __instance != null) BindMap(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} map: {e.Message}"); }
    }

    private static readonly List<(SpriteRenderer R, Def D)> MapButtons = new();

    private static void BindMap(MapBehaviour map)
    {
        var ov = map.infectedOverlay;
        var ship = ShipStatus.Instance;
        if (ov == null || ov.rooms == null || ship == null) return;
        MapButtons.Clear();
        // ersetzte Vanilla-Knoepfe ausblenden
        foreach (var r in ov.rooms)
        {
            if (r == null || r.special == null) continue;
            bool hide = Replaced(r.room);
            if (r.special.gameObject.activeSelf == hide) r.special.gameObject.SetActive(!hide);
        }
        SpriteRenderer template = null;
        foreach (var r in ov.rooms) if (r != null && r.special != null) { template = r.special; break; }
        if (template == null) return;
        var parent = map.HerePoint != null ? map.HerePoint.transform.parent : map.transform;
        float sx = Mathf.Sign(ship.transform.localScale.x);
        foreach (var d in Defs)
        {
            string name = $"Atlas_VCrisis_{d.Id}";
            var t = ov.transform.Find(name);
            bool want = OnMap(d) && Allowed(d);
            if (!want) { if (t != null) t.gameObject.SetActive(false); continue; }
            if (t == null)
            {
                var go = Object.Instantiate(template.gameObject, ov.transform);
                go.name = name;
                go.SetActive(true);
                t = go.transform;
            }
            t.gameObject.SetActive(true);
            var b = Btn(d);
            var local = new Vector3(b.x / ship.MapScale * sx, b.y / ship.MapScale, 0f);
            var wp = parent.TransformPoint(local);
            t.position = new Vector3(wp.x, wp.y, template.transform.position.z);
            var sr = t.GetComponent<SpriteRenderer>();
            if (sr != null && template.sprite != null)
            {
                float size = template.sprite.bounds.size.x;
                string art = ArtOf(d);
                // Grafik icon_vc_<k>.png (256 px, mit Mipmaps und DXT: auf der Karte nur ~40 px gross), sonst Laufzeit-Motiv
                sr.sprite = (art != null ? AtlasAssets.OwnSprite($"icon_vc_{art}.png", size, true, TextureWrapMode.Clamp, true) : null)
                            ?? MapIcon(d.Icon, size);
            }
            var bb = t.GetComponent<ButtonBehavior>();
            if (bb != null)
            {
                bb.OnClick = new UnityEngine.UI.Button.ButtonClickedEvent();
                byte id = d.Id;
                bb.OnClick.AddListener((Action)(() => Request(id)));
            }
            if (sr != null) MapButtons.Add((sr, d));
        }
        MapButtonTick();
    }

    private static readonly Dictionary<string, Sprite> Icons = new();

    /// <summary>Kartenknopf im Stil der Vanilla-Sabotageknoepfe: heller Kreis, dunkler Rand, Motiv je Krise.
    /// Zur Laufzeit gezeichnet (keine Grafikdatei), gleiche Groesse wie die Vorlage.</summary>
    private static Sprite MapIcon(string kind, float size)
    {
        string key = $"{kind}@{size:F3}";
        if (Icons.TryGetValue(key, out var have) && have != null) return have;
        const int N = 128;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Bilinear };
        var px = new Color32[N * N];
        var ink = new Color(0.16f, 0.13f, 0.12f);
        var fill = new Color(0.93f, 0.91f, 0.88f);
        var accent = new Color(0.95f, 0.45f, 0.12f);
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float u = (x + 0.5f) / N * 2f - 1f, v = (y + 0.5f) / N * 2f - 1f;
                float r = Mathf.Sqrt(u * u + v * v);
                Color c = new Color(0, 0, 0, 0);
                if (r < 0.98f) c = ink;
                if (r < 0.88f) c = fill;
                if (r < 0.88f && Glyph(kind, u / 0.88f, v / 0.88f, out bool dark)) c = dark ? ink : accent;
                float a = Mathf.Clamp01((0.98f - r) * N * 0.5f);   // weicher Rand
                c.a *= a;
                px[y * N + x] = c;
            }
        tex.SetPixels32(px);
        tex.Apply();
        var sp = Sprite.Create(tex, new Rect(0, 0, N, N), new Vector2(0.5f, 0.5f), N / Mathf.Max(0.05f, size));
        sp.hideFlags |= HideFlags.HideAndDontSave;
        Icons[key] = sp;
        return sp;
    }

    /// <summary>Motiv im Einheitskreis: true = Pixel gehoert zum Motiv (dark = Umriss/Nabe).</summary>
    private static bool Glyph(string kind, float u, float v, out bool dark)
    {
        dark = false;
        float r = Mathf.Sqrt(u * u + v * v), a = Mathf.Atan2(v, u);
        switch (kind)
        {
            case "engine":
            {
                // Turbinenrad: Nabe, sechs gebogene Schaufeln, Ring
                if (r < 0.16f) { dark = true; return true; }
                if (r > 0.70f && r < 0.80f) { dark = true; return true; }
                float blade = Mathf.Repeat(a * 6f / (2f * Mathf.PI) + r * 0.9f, 1f);
                return r < 0.70f && blade < 0.38f;
            }
            case "meteor":
            {
                // Brocken oben rechts mit Schweif nach unten links
                float bu = u - 0.25f, bv = v - 0.25f;
                if (bu * bu + bv * bv < 0.09f) { dark = bu * bu + bv * bv > 0.06f; return true; }
                float along = (u + v) * 0.7071f, across = (u - v) * 0.7071f;
                return along < 0.2f && along > -0.75f && Mathf.Abs(across) < 0.07f + 0.12f * (along + 0.75f) / 0.95f;
            }
            case "snow":
            {
                // sechsarmiger Stern mit Seitenaesten
                float arm = Mathf.Abs(Mathf.Repeat(a + Mathf.PI / 6f, Mathf.PI / 3f) - Mathf.PI / 6f) * r;
                if (r < 0.72f && arm < 0.06f) return true;
                float br = Mathf.Abs(r - 0.45f);
                return br < 0.06f && arm < 0.16f;
            }
            case "lava":
            {
                // Tropfen: Kreis unten, Spitze oben
                float dv = v + 0.18f;
                if (u * u + dv * dv < 0.16f) { dark = u * u + dv * dv < 0.03f; return true; }
                return v > 0.1f && v < 0.7f && Mathf.Abs(u) < 0.4f * (0.7f - v) / 0.6f;
            }
            case "turb":
            {
                // drei Wellenlinien
                for (int i = -1; i <= 1; i++)
                {
                    float wy = i * 0.32f + 0.1f * Mathf.Sin(u * 6f);
                    if (Mathf.Abs(v - wy) < 0.07f && Mathf.Abs(u) < 0.65f) return true;
                }
                return false;
            }
            case "torch":
            {
                // Taschenlampe schraeg, Lichtkegel nach oben rechts
                float along = (u + v) * 0.7071f, across = (v - u) * 0.7071f;
                if (along > -0.7f && along < -0.05f && Mathf.Abs(across) < 0.13f) { dark = true; return true; }
                return along >= -0.05f && along < 0.7f && Mathf.Abs(across) < 0.13f + (along + 0.05f) * 0.55f;
            }
            case "signal":
            {
                // Antenne mit drei Funkboegen
                if (Mathf.Abs(u) < 0.06f && v < 0.1f && v > -0.7f) { dark = true; return true; }
                float dr = Mathf.Sqrt(u * u + (v - 0.1f) * (v - 0.1f));
                float an = Mathf.Abs(Mathf.Atan2(u, v - 0.1f)) * Mathf.Rad2Deg;
                if (an > 55f) return false;
                return Mathf.Abs(dr - 0.25f) < 0.05f || Mathf.Abs(dr - 0.45f) < 0.05f || Mathf.Abs(dr - 0.65f) < 0.05f;
            }
            default:
                return r < 0.35f;
        }
    }

    private static void MapButtonTick()
    {
        var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage);
        bool wait = CriticalActive() || (sab != null && (sab.AnyActive || sab.Timer > 0f));
        foreach (var (r, d) in MapButtons)
            if (r != null) r.color = Current == d ? new Color(1f, 0.4f, 0.4f) : wait ? new Color(0.5f, 0.5f, 0.5f) : Color.white;
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(MapBehaviour), nameof(MapBehaviour.FixedUpdate))]
    internal static void MapBehaviour_FixedUpdate_Postfix()
    {
        if (MapButtons.Count == 0) return;
        try { MapButtonTick(); } catch { }
    }

    // ------------------------------------------------------------------ Sperren

    /// <summary>Waehrend einer eigenen Krise keine weitere Sabotage; im Modus "Replace" lehnt der Host die ersetzte
    /// Vanilla-Sabotage ab (der Knopf ist bei ehrlichen Clients ohnehin ausgeblendet).</summary>
    [HarmonyPrefix]
    [HarmonyPatch(typeof(SabotageSystemType), nameof(SabotageSystemType.UpdateSystem))]
    internal static bool SabotageSystemType_UpdateSystem_Prefix([HarmonyArgument(1)] MessageReader msgReader)
    {
        if (!OnVanillaRound()) return true;
        if (Active) return false;
        try
        {
            int pos = msgReader.Position;
            var sys = (SystemTypes)msgReader.ReadByte();
            msgReader.Position = pos;
            if (Replaced(sys)) { AtlasPlugin.Logger.LogInfo($"{LogPrefix} vanilla sabotage {sys} refused: replaced by an extra sabotage"); return false; }
        }
        catch { }
        return true;
    }

    [HarmonyPostfix]
    [HarmonyPriority(Priority.Last)]
    [HarmonyPatch(typeof(EmergencyMinigame), nameof(EmergencyMinigame.Update))]
    internal static void EmergencyMinigame_Update_Postfix(EmergencyMinigame __instance)
    {
        if (!Active || __instance == null) return;
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

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix()
    {
        if (_flash != null) Object.Destroy(_flash.gameObject);
        _flash = null;
        ClearArrows();
        SetShake(0f);
        FxClear();
        Reset();
        _ship = IntPtr.Zero;
        MapButtons.Clear();
    }

    // ------------------------------------------------------------------ Autotest (Diagnostics.TaskTest "vcrisis:<key>")
    // Nur im Freeplay-Autotest (AtlasMapShot.AutotestRun) auf einer Vanilla-Karte (Atlas ForceMap "vanilla:<karte>"):
    // startet die Krise, fotografiert, stellt sich an Station 0 und 1, oeffnet die Minispiele, haelt am Ende beide
    // Stationen (behoben) und meldet "vcrisis: all done".

    private static bool DiagOn
    {
        get
        {
            var v = AtlasPlugin.CfgTaskTest?.Value;
            return !string.IsNullOrEmpty(v) && v.StartsWith("vcrisis:", StringComparison.Ordinal) && AtlasMapShot.AutotestRun;
        }
    }

    private static int _diagStep;
    private static float _diagAt = -1f;

    private static void DiagTick()
    {
        if (!DiagOn) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        var d = Find(AtlasPlugin.CfgTaskTest.Value.Substring(8).Trim()) ?? FindKey(AtlasPlugin.CfgTaskTest.Value.Substring(8).Trim());
        if (d == null || !OnMap(d)) { if (_diagStep == 0) { _diagStep = 99; AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: no crisis '{AtlasPlugin.CfgTaskTest.Value}' on map {MapId()}"); } return; }
        if (_diagAt < 0f) { _diagAt = Time.time + 12f; return; }
        if (Time.time < _diagAt) return;
        _diagAt = Time.time + 4f;
        switch (_diagStep++)
        {
            case 0:
                if (Minigame.Instance != null) { try { Minigame.Instance.ForceClose(); } catch { } }
                RoleManager.Instance.SetRole(lp, AmongUs.GameOptions.RoleTypes.Impostor);
                HudManager.Instance.ToggleMapVisible(new MapOptions { Mode = MapOptions.Modes.Sabotage });
                break;
            case 1: AtlasTasks.Shot("vcrisis", d.Key + "_map"); break;
            case 2:
                if (MapBehaviour.Instance != null) MapBehaviour.Instance.Close();
                RoleManager.Instance.SetRole(lp, AmongUs.GameOptions.RoleTypes.Crewmate);
                AtlasRex.SetSabotageTimer(0f);
                { var sab = SabKit.Sys<SabotageSystemType>(SystemTypes.Sabotage); if (sab != null) sab.Timer = 0f; }
                HostTryStart(d);
                break;
            case 3: AtlasTasks.Shot("vcrisis", d.Key + "_start"); break;
            case 4: lp.NetTransform.RpcSnapTo(St(d)[0] + new Vector2(0f, -0.5f)); break;
            case 5: AtlasMinigame.DiagAuto = true; OpenStation(d, 0); break;
            case 6: AtlasTasks.Shot("vcrisis", d.Key + "_station0"); break;
            case 7:
                if (Minigame.Instance != null) { try { Minigame.Instance.ForceClose(); } catch { } }
                if (St(d).Length > 1) lp.NetTransform.RpcSnapTo(St(d)[1] + new Vector2(0f, -0.5f));
                break;
            case 8: if (St(d).Length > 1) { AtlasMinigame.DiagAuto = true; OpenStation(d, 1); } break;
            case 9: AtlasTasks.Shot("vcrisis", d.Key + "_station1"); break;
            case 10:
                if (Minigame.Instance != null) { try { Minigame.Instance.ForceClose(); } catch { } }
                Users[0].Add(lp.PlayerId); Users[1].Add(lp.PlayerId);
                break;
            case 11: AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: {DiagState()}"); break;
            case 12: AtlasPlugin.Logger.LogInfo($"{LogPrefix} vcrisis: all done"); break;
        }
    }

    private static Def Find(string idText) => byte.TryParse(idText, out byte id) ? Find(id) : null;

    private static Def FindKey(string key)
    {
        foreach (var d in Defs) if (string.Equals(d.Key, key, StringComparison.OrdinalIgnoreCase)) return d;
        return null;
    }

    public static string DiagState() =>
        $"vcrisis {(Active ? Current.Key : "idle")}, level {Level:F0}, time {TimeLeft:F1}, on {On[0]}/{On[1]}, allowed {_allowed}";
}
