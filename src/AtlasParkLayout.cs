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
        ["Admin/FixWiringConsole/2"] = new(13.410f, -4.450f),
        ["Admin/NoOxyConsole/1"] = new(19.200f, 2.200f),
        ["Admin/SwipeCardConsole/0"] = new(12.460f, 2.450f),
        ["Admin/UploadDataConsole/0"] = new(11.550f, -1.480f),
        ["Cafeteria/DataConsole/2"] = new(-4.750f, 6.450f),
        ["Cafeteria/FixWiringConsole/4"] = new(2.750f, 6.450f),
        ["Cafeteria/GarbageConsole/2"] = new(7.450f, 3.950f),
        ["Comms/DivertPowerConsole/1"] = new(25.550f, 14.350f),
        ["Comms/FixCommsConsole/0"] = new(32.000f, 18.800f),
        ["Comms/UploadDataConsole/1"] = new(32.450f, 14.650f),
        ["Electrical/CalibrateConsole/0"] = new(11.910f, -21.050f),
        ["Electrical/DivertPowerConsole/0"] = new(14.930f, -21.050f),
        ["Electrical/FixWiringConsole/0"] = new(16.440f, -21.050f),
        ["Electrical/SwitchConsole/0"] = new(10.800f, -23.200f),
        ["Electrical/UploadDataConsole/0"] = new(13.430f, -23.450f),
        ["LifeSupp/CleanFilterConsole/0"] = new(25.640f, -14.550f),
        ["LifeSupp/DivertPowerConsole/1"] = new(26.450f, -18.600f),
        ["LifeSupp/GarbageConsole/0"] = new(21.550f, -17.130f),
        ["LifeSupp/NoOxyConsole/0"] = new(22.000f, -22.800f),
        ["LowerEngine/AlignEngineConsole/1"] = new(-20.300f, -14.550f),
        ["LowerEngine/DivertPowerConsole/1"] = new(-11.820f, -14.550f),
        ["LowerEngine/FuelEngineConsole/0"] = new(-16.060f, -14.550f),
        ["MedBay/MedBayConsole/0"] = new(31.550f, -15.550f),
        ["MedBay/MedScanner/0"] = new(33.500f, -21.000f),
        ["Nav/ChartCourseConsole/0"] = new(-4.730f, 23.450f),
        ["Nav/DivertPowerConsole/1"] = new(-6.450f, 14.920f),
        ["Nav/FixWiringConsole/3"] = new(2.180f, 23.450f),
        ["Nav/StabilizeSteeringConsole/0"] = new(-0.520f, 23.450f),
        ["Nav/UploadDataConsole/0"] = new(-6.450f, 19.730f),
        ["Reactor/LowerHandConsole/1"] = new(33.600f, 6.400f),
        ["Reactor/StartReactorConsole/2"] = new(27.130f, 6.950f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(34.450f, 2.520f),
        ["Reactor/UpperHandConsole/0"] = new(23.600f, 6.400f),
        ["Security/DivertPowerConsole/1"] = new(15.570f, -10.550f),
        ["Security/FixWiringConsole/5"] = new(16.450f, -14.540f),
        ["Shields/DivertPowerConsole/1"] = new(18.480f, 20.450f),
        ["Shields/ShieldConsole/0"] = new(14.270f, 20.450f),
        ["Storage/AirlockConsole/0"] = new(-24.550f, -16.030f),
        ["Storage/FixWiringConsole/1"] = new(-27.180f, -13.550f),
        ["Storage/gasCanConsole/0"] = new(-32.300f, -13.550f),
        ["UpperEngine/AlignEngineConsole/0"] = new(-23.300f, 4.450f),
        ["UpperEngine/DivertPowerConsole/1"] = new(-13.550f, 0.360f),
        ["UpperEngine/FuelEngineConsole/0"] = new(-16.680f, 4.450f),
        ["Weapons/DivertPowerConsole/1"] = new(-13.550f, 14.750f),
        ["Weapons/UploadDataConsole/1"] = new(-18.390f, 20.450f),
        ["Weapons/WeaponConsole/0"] = new(-22.300f, 20.450f),
    };
    public static readonly Vector2 EmergencyButton = new(0.000f, 2.500f);
    public static readonly Vector2 SurveillanceConsole = new(11.600f, -11.600f);
    public static readonly Vector2 AdminTable = new(15.500f, -1.800f);
    public static readonly Vector2 FreeplayLaptop = new(5.000f, -3.400f);
    public static readonly Vector2 Spawn = new(0.000f, 0.500f);
    public const float SpawnRadius = 3.0f;
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [0] = new(-34.600f, 21.400f),
        [3] = new(-14.400f, 19.600f),
        [4] = new(4.600f, 22.400f),
        [12] = new(20.200f, 12.800f),
        [6] = new(26.600f, 18.600f),
        [1] = new(-34.600f, 6.600f),
        [5] = new(-15.000f, -3.600f),
        [13] = new(19.200f, -4.200f),
        [7] = new(33.800f, -4.200f),
        [2] = new(-31.600f, -21.000f),
        [9] = new(-12.400f, -22.200f),
        [10] = new(4.800f, -23.800f),
        [11] = new(16.200f, -23.000f),
        [8] = new(35.400f, -16.400f),
    };
    public static readonly int[][] VentNetworks =
    {
        new[] { 0, 3, 4, 12, 6 },
        new[] { 1, 5, 13, 7 },
        new[] { 2, 9, 10, 11, 8 },
    };
    public static readonly int[][] VentBridges =
    {
        new[] { 4, 5 },
        new[] { 7, 8 },
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] VerticalDoors =
    {
        new("fairground-W", -8.250f, 1.750f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("fairground-E", 8.250f, 1.750f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("workshop-E", -23.750f, -17.500f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("workshop-W", -33.250f, -17.500f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("carousel-E", -12.750f, 1.750f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("bumpercars-W", -21.250f, -17.500f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("firstaid-W", 30.750f, -19.500f, 2.50f, SystemTypes.MedBay, seeThrough: false),
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] HorizontalDoors =
    {
        new("fairground-S", -0.000f, -5.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("workshop-N", -28.750f, -12.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("carousel-S", -18.500f, -5.250f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("bumpercars-N", -14.500f, -13.750f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("security-N", 13.500f, -9.750f, 2.50f, SystemTypes.Security, seeThrough: false),
        new("substation-N", 13.500f, -20.250f, 2.50f, SystemTypes.Electrical, seeThrough: false),
    };
    public static readonly Vector2[] Cameras =
    {
        new(6.800f, 18.000f),
        new(4.000f, 12.600f),
        new(-34.100f, 10.200f),
        new(28.800f, -6.800f),
    };
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(0.000f, 1.800f),
        [SystemTypes.Storage] = new(-28.500f, -16.700f),
        [SystemTypes.UpperEngine] = new(-18.500f, 0.800f),
        [SystemTypes.LowerEngine] = new(-16.000f, -17.700f),
        [SystemTypes.Security] = new(13.500f, -12.200f),
        [SystemTypes.Electrical] = new(13.500f, -21.450f),
        [SystemTypes.MedBay] = new(33.750f, -18.700f),
        [SystemTypes.LifeSupp] = new(24.000f, -18.200f),
        [SystemTypes.Comms] = new(29.000f, 16.800f),
        [SystemTypes.Reactor] = new(28.500f, 0.550f),
    };
}

/// <summary>Park-Welt-System (AtlasParkWorld): Sperrflaechen und Wege der Fahrgeschaefte.</summary>
internal static class AtlasParkWorldData
{
    public static readonly (Vector2 Min, Vector2 Max, bool Vertical)[] Crossings =
    {
        (new(8.800f, 15.400f), new(10.000f, 18.600f), true),
        (new(14.200f, 8.000f), new(17.400f, 9.200f), false),
        (new(27.600f, 8.000f), new(30.800f, 9.200f), false),
    };
    public static readonly (Vector2 Min, Vector2 Max)[] CarouselGates =
    {
        (new(-19.500f, 4.990f), new(-17.000f, 5.510f)),
        (new(-24.510f, 0.000f), new(-23.990f, 2.500f)),
    };
    public static readonly Vector2 CarouselCenter = new(-18.500f, 0.000f);
    public const float CarouselRadius = 2.8f;
    public static readonly (Vector2 Min, Vector2 Max) FlumeBridge = (new(31.500f, -9.600f), new(34.000f, -7.400f));
    public static readonly (Vector2 Min, Vector2 Max, bool Inward)[] Turnstiles =
    {
        (new(-4.500f, -18.400f), new(-2.000f, -17.900f), true),
        (new(2.000f, -18.400f), new(4.500f, -17.900f), false),
    };
    public static readonly Vector2[] TrackLoop = new Vector2[] { new(36.400f, 8.600f), new(9.400f, 8.600f), new(9.400f, 24.400f), new(36.400f, 24.400f), new(36.400f, 8.600f) };
    public static readonly Vector2[] CanalLine = new Vector2[] { new(37.000f, -8.500f), new(21.500f, -8.500f) };
    public static readonly Vector2[] GhostRide = new Vector2[] { new(-32.200f, -4.600f), new(-32.200f, -3.200f), new(-29.300f, -3.200f), new(-29.300f, 2.900f), new(-34.800f, 2.900f), new(-34.800f, 5.400f), new(-32.200f, 5.400f), new(-32.200f, 7.800f) };
    public static readonly Vector2 GhostMonitor = new(-29.400f, 10.000f);
    /// <summary>Laternen am Weg (Lichtebene, gehen bei Park Blackout aus); Bild task_park_lamppost(_off).png.</summary>
    public static readonly Vector2[] Lamps = new Vector2[] { new(-10.000f, 0.450f), new(10.000f, 0.450f), new(-9.160f, 18.020f), new(7.890f, 15.550f), new(-33.550f, 10.000f), new(-26.000f, 2.550f), new(-33.550f, -7.000f), new(-27.450f, -10.500f), new(-34.000f, -17.300f), new(-36.600f, -10.300f), new(-19.760f, -8.110f), new(-5.760f, -7.970f), new(1.240f, -7.900f), new(8.240f, -7.830f), new(15.230f, -7.760f), new(13.640f, -19.550f) };
    public static readonly Vector2 LampPivot = new(0.5000f, 0.1615f);
    public const float LampPixelsPerMeter = 160f;
}
