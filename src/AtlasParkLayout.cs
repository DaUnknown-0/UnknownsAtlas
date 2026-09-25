// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AUTOMATISCH ERZEUGT von tools/gen_park.py aus tools/park_layout.py - NICHT VON HAND AENDERN.
// Moonlight Carnival (Graybox): Plaetze der Skeld-Mechanik (Weltmeter).

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasParkLayout
{
    public static readonly Dictionary<string, Vector2> Consoles = new()
    {
        ["Admin/FixWiringConsole/2"] = new(-3.650f, -7.050f),
        ["Admin/NoOxyConsole/1"] = new(1.200f, -7.300f),
        ["Admin/SwipeCardConsole/0"] = new(-5.450f, -7.050f),
        ["Admin/UploadDataConsole/0"] = new(1.450f, -10.950f),
        ["Cafeteria/DataConsole/2"] = new(-5.450f, 3.490f),
        ["Cafeteria/FixWiringConsole/4"] = new(-2.590f, 5.450f),
        ["Cafeteria/GarbageConsole/2"] = new(5.450f, 3.270f),
        ["Comms/DivertPowerConsole/1"] = new(21.950f, 11.560f),
        ["Comms/FixCommsConsole/0"] = new(21.500f, 15.600f),
        ["Comms/UploadDataConsole/1"] = new(16.700f, 16.250f),
        ["Electrical/CalibrateConsole/0"] = new(4.690f, -15.050f),
        ["Electrical/DivertPowerConsole/0"] = new(1.660f, -15.050f),
        ["Electrical/FixWiringConsole/0"] = new(5.950f, -15.920f),
        ["Electrical/SwitchConsole/0"] = new(1.300f, -17.200f),
        ["Electrical/UploadDataConsole/0"] = new(3.220f, -18.950f),
        ["LifeSupp/CleanFilterConsole/0"] = new(13.190f, -15.050f),
        ["LifeSupp/DivertPowerConsole/1"] = new(14.450f, -15.910f),
        ["LifeSupp/GarbageConsole/0"] = new(14.450f, -17.420f),
        ["LifeSupp/NoOxyConsole/0"] = new(10.000f, -19.800f),
        ["LowerEngine/AlignEngineConsole/1"] = new(-9.650f, -15.050f),
        ["LowerEngine/DivertPowerConsole/1"] = new(-9.000f, -20.450f),
        ["LowerEngine/FuelEngineConsole/0"] = new(-2.050f, -15.610f),
        ["MedBay/MedBayConsole/0"] = new(21.860f, -15.050f),
        ["MedBay/MedScanner/0"] = new(19.500f, -18.000f),
        ["Nav/ChartCourseConsole/0"] = new(-0.320f, 16.950f),
        ["Nav/DivertPowerConsole/1"] = new(2.690f, 16.950f),
        ["Nav/FixWiringConsole/3"] = new(-2.180f, 9.050f),
        ["Nav/StabilizeSteeringConsole/0"] = new(4.450f, 10.570f),
        ["Nav/UploadDataConsole/0"] = new(-5.440f, 10.320f),
        ["Reactor/LowerHandConsole/1"] = new(19.400f, 4.900f),
        ["Reactor/StartReactorConsole/2"] = new(14.640f, 5.450f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(9.550f, -0.290f),
        ["Reactor/UpperHandConsole/0"] = new(10.600f, 4.900f),
        ["Security/DivertPowerConsole/1"] = new(6.950f, -10.950f),
        ["Security/FixWiringConsole/5"] = new(6.870f, -7.050f),
        ["Shields/DivertPowerConsole/1"] = new(14.450f, 11.080f),
        ["Shields/ShieldConsole/0"] = new(13.140f, 16.740f),
        ["Storage/AirlockConsole/0"] = new(-16.680f, -18.450f),
        ["Storage/FixWiringConsole/1"] = new(-13.050f, -17.850f),
        ["Storage/gasCanConsole/0"] = new(-13.500f, -12.550f),
        ["UpperEngine/AlignEngineConsole/0"] = new(-18.000f, 5.450f),
        ["UpperEngine/DivertPowerConsole/1"] = new(-9.550f, 5.420f),
        ["UpperEngine/FuelEngineConsole/0"] = new(-13.760f, 5.450f),
        ["Weapons/DivertPowerConsole/1"] = new(-10.820f, 15.450f),
        ["Weapons/UploadDataConsole/1"] = new(-15.060f, 15.450f),
        ["Weapons/WeaponConsole/0"] = new(-19.300f, 15.450f),
    };
    public static readonly Vector2 EmergencyButton = new(0.000f, 3.400f);
    public static readonly Vector2 SurveillanceConsole = new(4.100f, -8.100f);
    public static readonly Vector2 AdminTable = new(-1.500f, -8.300f);
    public static readonly Vector2 FreeplayLaptop = new(5.200f, -1.600f);
    public static readonly Vector2 Spawn = new(0.000f, 1.200f);
    public const float SpawnRadius = 2.4f;
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [0] = new(-19.300f, 9.300f),
        [3] = new(-4.300f, 16.000f),
        [12] = new(9.400f, 16.600f),
        [6] = new(21.800f, 16.100f),
        [1] = new(-16.600f, -5.000f),
        [5] = new(-18.200f, -2.200f),
        [13] = new(-5.300f, -10.900f),
        [7] = new(20.300f, -2.300f),
        [2] = new(-20.300f, -18.300f),
        [9] = new(-2.200f, -20.300f),
        [10] = new(5.400f, -17.400f),
        [11] = new(14.300f, -20.300f),
        [8] = new(18.200f, -15.200f),
    };
    public static readonly int[][] VentNetworks =
    {
        new[] { 0, 3, 12, 6 },
        new[] { 1, 5, 13, 7 },
        new[] { 2, 9, 10, 11, 8 },
    };
    public static readonly int[][] VentBridges =
    {
        new[] { 3, 5 },
        new[] { 7, 8 },
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] VerticalDoors =
    {
        new("fairground-W", -6.250f, 1.750f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("fairground-E", 6.250f, 1.750f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("workshop-E", -12.250f, -16.250f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("carousel-E", -8.750f, 1.750f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("bumpercars-W", -10.750f, -16.250f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("firstaid-W", 17.250f, -18.250f, 2.50f, SystemTypes.MedBay, seeThrough: false),
        new("coldstore-W", 8.750f, -17.250f, 2.50f, SystemTypes.Storage, seeThrough: false),
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] HorizontalDoors =
    {
        new("fairground-N", -0.000f, 6.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("workshop-N", -15.000f, -11.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("carousel-S", -15.000f, -3.250f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("bumpercars-N", -3.000f, -14.250f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("security-N", 5.000f, -6.250f, 2.50f, SystemTypes.Security, seeThrough: false),
        new("substation-N", 3.250f, -14.250f, 2.50f, SystemTypes.Electrical, seeThrough: false),
    };
    public static readonly Vector2[] Cameras =
    {
        new(4.200f, 14.600f),
        new(2.800f, 5.700f),
        new(-13.400f, -4.400f),
        new(18.800f, -6.000f),
    };
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(0.000f, 2.300f),
        [SystemTypes.Storage] = new(-16.750f, -14.700f),
        [SystemTypes.UpperEngine] = new(-14.000f, 2.300f),
        [SystemTypes.LowerEngine] = new(-6.000f, -16.950f),
        [SystemTypes.Security] = new(5.000f, -8.200f),
        [SystemTypes.Electrical] = new(3.500f, -16.200f),
        [SystemTypes.MedBay] = new(20.000f, -16.950f),
        [SystemTypes.LifeSupp] = new(12.000f, -16.950f),
        [SystemTypes.Comms] = new(19.250f, 13.950f),
        [SystemTypes.Reactor] = new(15.000f, 2.550f),
    };
}

/// <summary>Park-Welt-System (AtlasParkWorld): Sperrflaechen und Wege der Fahrgeschaefte.</summary>
internal static class AtlasParkWorldData
{
    public static readonly (Vector2 Min, Vector2 Max, bool Vertical)[] Crossings =
    {
        (new(6.800f, 11.000f), new(8.000f, 14.200f), true),
        (new(10.500f, 7.300f), new(13.700f, 8.500f), false),
    };
    public static readonly (Vector2 Min, Vector2 Max)[] CarouselGates =
    {
        (new(-16.500f, 5.990f), new(-14.000f, 6.510f)),
    };
    public static readonly Vector2 CarouselCenter = new(-14.000f, 1.500f);
    public const float CarouselRadius = 2.8f;
    public static readonly (Vector2 Min, Vector2 Max) FlumeBridge = (new(17.000f, -8.700f), new(19.000f, -7.300f));
    public static readonly (Vector2 Min, Vector2 Max, bool Inward)[] Turnstiles =
    {
        (new(-4.500f, -3.500f), new(-2.000f, -3.000f), true),
        (new(2.000f, -3.500f), new(4.500f, -3.000f), false),
    };
    public static readonly Vector2[] TrackLoop = new Vector2[] { new(23.900f, 7.900f), new(7.400f, 7.900f), new(7.400f, 18.400f), new(23.900f, 18.400f), new(23.900f, 7.900f) };
    public static readonly Vector2[] CanalLine = new Vector2[] { new(21.500f, -8.000f), new(9.500f, -8.000f) };
    public static readonly Vector2[] GhostRide = new Vector2[] { new(-15.000f, -4.200f), new(-15.000f, -5.000f), new(-13.600f, -5.000f), new(-13.600f, -7.300f), new(-16.400f, -7.300f), new(-16.400f, -9.800f), new(-15.000f, -9.800f), new(-15.000f, -10.900f) };
    public static readonly Vector2 GhostMonitor = new(-18.800f, -12.600f);
    /// <summary>Laternen am Weg (Lichtebene, gehen bei Park Blackout aus); Bild task_park_lamppost(_off).png.</summary>
    public static readonly Vector2[] Lamps = new Vector2[] { new(-7.500f, 2.750f), new(7.750f, 0.750f), new(-1.000f, 7.500f), new(-7.750f, 11.250f), new(-16.250f, 7.250f), new(6.750f, 11.600f), new(11.100f, 7.500f), new(5.500f, -5.750f), new(10.500f, -5.750f), new(16.000f, -4.000f), new(-9.500f, -11.750f), new(10.500f, -11.750f), new(-11.500f, -15.250f), new(14.500f, -11.750f) };
    public static readonly Vector2 LampPivot = new(0.5000f, 0.1615f);
    public const float LampPixelsPerMeter = 160f;
}
