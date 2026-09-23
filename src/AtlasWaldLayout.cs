// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AUTOMATISCH ERZEUGT von tools/gen_wald.py aus tools/wald_layout.py - NICHT VON HAND AENDERN.
// Forststation Nadelkamm: Plaetze der Skeld-Mechanik (Weltmeter).

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasWaldLayout
{
    public static readonly Dictionary<string, Vector2> Consoles = new()
    {
        ["Admin/FixWiringConsole/2"] = new(-16.450f, -0.820f),
        ["Admin/NoOxyConsole/1"] = new(27.600f, -17.800f),
        ["Admin/SwipeCardConsole/0"] = new(-10.280f, 4.450f),
        ["Admin/UploadDataConsole/0"] = new(-16.450f, 3.700f),
        ["Cafeteria/DataConsole/2"] = new(-4.300f, 5.450f),
        ["Cafeteria/FixWiringConsole/4"] = new(2.920f, 5.450f),
        ["Cafeteria/GarbageConsole/2"] = new(-4.450f, 0.790f),
        ["Comms/DivertPowerConsole/1"] = new(1.550f, 13.320f),
        ["Comms/FixCommsConsole/0"] = new(4.600f, 17.600f),
        ["Comms/UploadDataConsole/1"] = new(8.780f, 18.450f),
        ["Electrical/CalibrateConsole/0"] = new(-12.730f, -12.550f),
        ["Electrical/DivertPowerConsole/0"] = new(-11.550f, -16.540f),
        ["Electrical/FixWiringConsole/0"] = new(-13.680f, -17.450f),
        ["Electrical/SwitchConsole/0"] = new(-17.400f, -15.000f),
        ["Electrical/UploadDataConsole/0"] = new(-11.550f, -14.410f),
        ["LifeSupp/CleanFilterConsole/0"] = new(18.260f, 18.450f),
        ["LifeSupp/DivertPowerConsole/1"] = new(28.450f, 13.870f),
        ["LifeSupp/GarbageConsole/0"] = new(21.870f, 18.450f),
        ["LifeSupp/NoOxyConsole/0"] = new(-29.300f, 2.400f),
        ["LowerEngine/AlignEngineConsole/1"] = new(10.700f, -12.550f),
        ["LowerEngine/DivertPowerConsole/1"] = new(10.550f, -17.220f),
        ["LowerEngine/FuelEngineConsole/0"] = new(15.520f, -12.550f),
        ["MedBay/MedBayConsole/0"] = new(-25.660f, 4.450f),
        ["MedBay/MedScanner/0"] = new(-26.000f, -1.200f),
        ["Nav/ChartCourseConsole/0"] = new(-25.360f, 18.450f),
        ["Nav/DivertPowerConsole/1"] = new(-22.660f, 18.450f),
        ["Nav/FixWiringConsole/3"] = new(-21.390f, 9.550f),
        ["Nav/StabilizeSteeringConsole/0"] = new(-29.450f, 16.510f),
        ["Nav/UploadDataConsole/0"] = new(-19.550f, 13.140f),
        ["Reactor/LowerHandConsole/1"] = new(-20.600f, 16.500f),
        ["Reactor/StartReactorConsole/2"] = new(22.160f, 5.180f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(29.450f, 1.310f),
        ["Reactor/UpperHandConsole/0"] = new(25.500f, 17.600f),
        ["Security/DivertPowerConsole/1"] = new(-29.450f, -11.550f),
        ["Security/FixWiringConsole/5"] = new(-23.550f, -15.630f),
        ["Shields/DivertPowerConsole/1"] = new(27.470f, -9.550f),
        ["Shields/ShieldConsole/0"] = new(23.260f, -9.550f),
        ["Storage/AirlockConsole/0"] = new(-5.450f, -13.360f),
        ["Storage/FixWiringConsole/1"] = new(2.390f, -11.550f),
        ["Storage/gasCanConsole/0"] = new(-1.830f, -11.550f),
        ["UpperEngine/AlignEngineConsole/0"] = new(-14.300f, 18.450f),
        ["UpperEngine/DivertPowerConsole/1"] = new(-3.550f, 13.760f),
        ["UpperEngine/FuelEngineConsole/0"] = new(-10.060f, 18.450f),
        ["Weapons/DivertPowerConsole/1"] = new(17.450f, -0.110f),
        ["Weapons/UploadDataConsole/1"] = new(9.550f, 0.030f),
        ["Weapons/WeaponConsole/0"] = new(10.160f, 6.180f),
    };
    public static readonly Vector2 EmergencyButton = new(0.000f, 2.500f);
    public static readonly Vector2 SurveillanceConsole = new(-28.000f, -15.000f);
    public static readonly Vector2 AdminTable = new(-13.000f, 1.300f);
    public static readonly Vector2 FreeplayLaptop = new(3.800f, -1.200f);
    public static readonly Vector2 Spawn = new(0.000f, 2.000f);
    public const float SpawnRadius = 2.4f;
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [11] = new(-28.500f, 10.500f),
        [3] = new(-16.800f, -12.800f),
        [5] = new(-24.000f, -11.600f),
        [7] = new(-4.000f, 18.300f),
        [6] = new(4.000f, -18.300f),
        [0] = new(-8.000f, -1.300f),
        [10] = new(10.200f, 11.000f),
        [4] = new(27.800f, 5.000f),
        [9] = new(17.000f, -18.300f),
    };
    public static readonly int[][] VentNetworks =
    {
        new[] { 11, 3, 5 },
        new[] { 7, 6, 0 },
        new[] { 10, 4, 9 },
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] VerticalDoors =
    {
        new("messe-W", -5.250f, 2.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("messe-E", 5.250f, 2.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("labor-E", -21.750f, 1.500f, 2.50f, SystemTypes.MedBay, seeThrough: false),
        new("saegewerk-E", -2.750f, 15.250f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("lager-W", -6.250f, -14.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("lager-E", 6.250f, -14.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("bootshaus-W", 9.750f, -15.750f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] HorizontalDoors =
    {
        new("messe-S", -0.000f, -2.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("saegewerk-S", -8.750f, 11.750f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("lager-N", -0.000f, -10.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("bootshaus-N", 14.000f, -11.750f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("wachstube-N", -26.500f, -10.750f, 2.50f, SystemTypes.Security, seeThrough: false),
        new("generator-N", -14.500f, -11.750f, 2.50f, SystemTypes.Electrical, seeThrough: false),
    };
    public static readonly Vector2[] Cameras =
    {
        new(4.000f, -3.000f),
        new(17.000f, 6.000f),
        new(27.500f, 18.000f),
        new(-5.000f, -9.000f),
    };
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(0.000f, 2.800f),
        [SystemTypes.MedBay] = new(-26.000f, 1.800f),
        [SystemTypes.UpperEngine] = new(-9.000f, 16.300f),
        [SystemTypes.Storage] = new(0.000f, -14.200f),
        [SystemTypes.LowerEngine] = new(14.000f, -14.700f),
        [SystemTypes.Security] = new(-26.500f, -13.700f),
        [SystemTypes.Electrical] = new(-14.500f, -14.200f),
        [SystemTypes.Comms] = new(6.500f, 15.925f),
        [SystemTypes.LifeSupp] = new(22.500f, 15.800f),
        [SystemTypes.Reactor] = new(25.500f, 2.800f),
    };
}
