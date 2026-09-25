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
        ["Admin/FixWiringConsole/2"] = new(-14.950f, -1.300f),
        ["Admin/NoOxyConsole/1"] = new(18.000f, -12.300f),
        ["Admin/SwipeCardConsole/0"] = new(-9.050f, 3.690f),
        ["Admin/UploadDataConsole/0"] = new(-14.950f, 3.540f),
        ["Cafeteria/DataConsole/2"] = new(-4.300f, 5.450f),
        ["Cafeteria/FixWiringConsole/4"] = new(2.920f, 5.450f),
        ["Cafeteria/GarbageConsole/2"] = new(-4.450f, 0.790f),
        ["Comms/DivertPowerConsole/1"] = new(5.770f, 15.690f),
        ["Comms/FixCommsConsole/0"] = new(2.400f, 14.600f),
        ["Comms/UploadDataConsole/1"] = new(-1.350f, 15.520f),
        ["Electrical/CalibrateConsole/0"] = new(-9.050f, -11.150f),
        ["Electrical/DivertPowerConsole/0"] = new(-13.580f, -6.550f),
        ["Electrical/FixWiringConsole/0"] = new(-11.180f, -11.450f),
        ["Electrical/SwitchConsole/0"] = new(-15.100f, -8.200f),
        ["Electrical/UploadDataConsole/0"] = new(-9.050f, -9.020f),
        ["LifeSupp/CleanFilterConsole/0"] = new(11.140f, 16.450f),
        ["LifeSupp/DivertPowerConsole/1"] = new(13.950f, 9.640f),
        ["LifeSupp/GarbageConsole/0"] = new(9.570f, 10.800f),
        ["LifeSupp/NoOxyConsole/0"] = new(-25.800f, 2.400f),
        ["LowerEngine/AlignEngineConsole/1"] = new(8.700f, -6.550f),
        ["LowerEngine/DivertPowerConsole/1"] = new(8.550f, -11.260f),
        ["LowerEngine/FuelEngineConsole/0"] = new(13.260f, -6.550f),
        ["MedBay/MedBayConsole/0"] = new(-22.160f, 4.450f),
        ["MedBay/MedScanner/0"] = new(-22.500f, -1.200f),
        ["Nav/ChartCourseConsole/0"] = new(-19.960f, 16.450f),
        ["Nav/DivertPowerConsole/1"] = new(-22.370f, 16.450f),
        ["Nav/FixWiringConsole/3"] = new(-18.550f, 14.220f),
        ["Nav/StabilizeSteeringConsole/0"] = new(-26.450f, 12.380f),
        ["Nav/UploadDataConsole/0"] = new(-24.440f, 9.550f),
        ["Reactor/LowerHandConsole/1"] = new(-24.900f, 16.300f),
        ["Reactor/StartReactorConsole/2"] = new(15.050f, 16.450f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(16.570f, 9.550f),
        ["Reactor/UpperHandConsole/0"] = new(17.000f, 15.900f),
        ["Security/DivertPowerConsole/1"] = new(-19.550f, -10.440f),
        ["Security/FixWiringConsole/5"] = new(-24.240f, -6.050f),
        ["Shields/DivertPowerConsole/1"] = new(21.850f, -9.150f),
        ["Shields/ShieldConsole/0"] = new(19.240f, -6.050f),
        ["Storage/AirlockConsole/0"] = new(4.450f, -10.350f),
        ["Storage/FixWiringConsole/1"] = new(-4.450f, -10.250f),
        ["Storage/gasCanConsole/0"] = new(-2.050f, -6.050f),
        ["UpperEngine/AlignEngineConsole/0"] = new(-13.800f, 16.450f),
        ["UpperEngine/DivertPowerConsole/1"] = new(-5.550f, 11.750f),
        ["UpperEngine/FuelEngineConsole/0"] = new(-9.890f, 16.450f),
        ["Weapons/DivertPowerConsole/1"] = new(8.580f, -0.770f),
        ["Weapons/UploadDataConsole/1"] = new(15.450f, 1.460f),
        ["Weapons/WeaponConsole/0"] = new(9.990f, 5.950f),
    };
    public static readonly Vector2 EmergencyButton = new(0.000f, 2.500f);
    public static readonly Vector2 SurveillanceConsole = new(-25.000f, -9.000f);
    public static readonly Vector2 AdminTable = new(-12.000f, 1.300f);
    public static readonly Vector2 FreeplayLaptop = new(3.800f, -1.200f);
    public static readonly Vector2 Spawn = new(0.000f, 2.000f);
    public const float SpawnRadius = 2.4f;
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [11] = new(-19.800f, 10.600f),
        [3] = new(-9.300f, -6.900f),
        [5] = new(-19.800f, -6.300f),
        [7] = new(-5.800f, 16.200f),
        [6] = new(4.300f, -6.300f),
        [0] = new(-9.300f, -1.300f),
        [10] = new(5.000f, 10.400f),
        [4] = new(18.700f, 10.500f),
        [9] = new(14.700f, -12.200f),
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
        new("labor-E", -18.250f, 1.500f, 2.50f, SystemTypes.MedBay, seeThrough: false),
        new("saegewerk-E", -4.750f, 13.250f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("lager-W", -5.250f, -8.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("lager-E", 5.250f, -8.750f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("bootshaus-W", 7.750f, -9.750f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
    };
    public static readonly AtlasMuseumLayout.DoorSlot[] HorizontalDoors =
    {
        new("messe-S", -0.000f, -2.250f, 2.50f, SystemTypes.Cafeteria, seeThrough: false),
        new("saegewerk-S", -9.750f, 9.750f, 2.50f, SystemTypes.UpperEngine, seeThrough: false),
        new("lager-N", -0.000f, -5.250f, 2.50f, SystemTypes.Storage, seeThrough: false),
        new("bootshaus-N", 11.750f, -5.750f, 2.50f, SystemTypes.LowerEngine, seeThrough: false),
        new("wachstube-N", -22.750f, -5.250f, 2.50f, SystemTypes.Security, seeThrough: false),
        new("generator-N", -12.000f, -5.750f, 2.50f, SystemTypes.Electrical, seeThrough: false),
    };
    public static readonly Vector2[] Cameras =
    {
        new(4.000f, -3.000f),
        new(15.200f, 5.500f),
        new(19.200f, 16.200f),
        new(-5.900f, -4.800f),
    };
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(0.000f, 2.800f),
        [SystemTypes.MedBay] = new(-22.500f, 1.800f),
        [SystemTypes.UpperEngine] = new(-9.750f, 14.300f),
        [SystemTypes.Storage] = new(0.000f, -8.450f),
        [SystemTypes.LowerEngine] = new(11.750f, -8.700f),
        [SystemTypes.Security] = new(-22.500f, -8.200f),
        [SystemTypes.Electrical] = new(-12.000f, -8.200f),
        [SystemTypes.Comms] = new(2.250f, 13.800f),
        [SystemTypes.LifeSupp] = new(11.750f, 13.800f),
        [SystemTypes.Reactor] = new(17.250f, 13.800f),
    };
}
