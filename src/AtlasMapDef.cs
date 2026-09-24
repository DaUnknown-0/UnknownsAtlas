// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMapDef - eine Karte, die per Relocate-in-Place in den Skeld-ShipStatus gebaut wird.
// Alles, was der Builder (AtlasMuseumBuilder) je Karte braucht, steht hier als Daten; die
// Werte kommen aus den generierten Klassen (AtlasMuseumData/Layout, AtlasWaldData/Layout).
// Karte #3 kostet damit nur eine weitere Factory-Methode unten.

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class AtlasMapDef
{
    public string Key;                 // AppDomain "UnknownsAtlas.ActiveMap" + Ressourcen-Praefix
    public string DisplayName;
    public string ResourcePrefix;      // museum_floor_{i}.jpg ...

    public float MinX, MinY, MaxX, MaxY;
    public Vector2[][] Walls, ShadowWalls, Opaque, Glass, Hallways;
    public bool[] OpaqueCastsShadow;
    public (string Key, string Name, SystemTypes Room, Vector2[] Area)[] Rooms;
    public float FloorPixelsPerMeter;
    public (int Index, float WorldX, float WorldY, int W, int H)[] FloorTiles;
    public float PropPixelsPerMeter;
    public (string Kind, int Atlas, int X, int Y, int W, int H, float WorldX, float WorldY, float BaseY, float FootX0, float FootX1)[] Props;
    public (string Key, int Atlas, int X, int Y, int W, int H, float PivotX, float PivotY)[] ConsoleSprites;
    /// <summary>Props, die nie ausblenden (Schaustuecke).</summary>
    public HashSet<string> NoFadeKinds = new();

    public Dictionary<string, Vector2> Consoles;
    public Vector2 EmergencyButton, SurveillanceConsole, AdminTable, FreeplayLaptop, Spawn;
    public float SpawnRadius;
    public Dictionary<int, Vector2> Vents;
    public int[][] VentNetworks;
    /// <summary>Zusaetzliche Verbindung zweier Vents ueber den dritten Nachbarn (Vent.Center), z. B. zwischen
    /// zwei Ringen. Museum und Wald nutzen sie nicht.</summary>
    public int[][] VentBridges = System.Array.Empty<int[]>();
    public AtlasMuseumLayout.DoorSlot[] VerticalDoors, HorizontalDoors;
    public Vector2[] Cameras;
    public Dictionary<SystemTypes, Vector2> MapButtons;
    public Color CameraColor;
    public float MinLight = 1f, MaxLight = 5f;
    /// <summary>Diagnose (AtlasMapShot): Teststellen fuer Bildschirmfotos; die letzte oeffnet die Kameras.</summary>
    public Vector2[] ViewSpots = System.Array.Empty<Vector2>();
    /// <summary>Task-Namen der Karte (docs/TASK_KONZEPT.md): jeder Karten-Task reitet auf einem Skeld-TaskType.</summary>
    public Dictionary<TaskTypes, string> TaskNames = new();
    /// <summary>Eigene Minispiele (Stufe B): TaskType -> Baustein-Art (AtlasMinigame).</summary>
    public Dictionary<TaskTypes, string> CustomTasks = new();
    /// <summary>
    /// Minispiel-Grafik dieser Karte: "task_x.png" (in jedem Minispiel) oder "art:task_x.png" (nur im
    /// Minispiel dieser Baustein-Art) -> eigene Datei. So nutzt der Park die Bausteine von Museum und
    /// Wald mit eigener Grafik, ohne dass die Mechaniken die Karte kennen muessen (AtlasTaskKit.Art).
    /// </summary>
    public Dictionary<string, string> TaskArt = new();
    /// <summary>Minispiel-Texte dieser Karte, gleiche Schluesselregel wie TaskArt (AtlasTaskKit.T).</summary>
    public Dictionary<string, string> TaskText = new();

    public static AtlasMapDef Museum() => new()
    {
        Key = "museum", DisplayName = "Vesper Museum", ResourcePrefix = "museum",
        MinX = AtlasMuseumData.MinX, MinY = AtlasMuseumData.MinY, MaxX = AtlasMuseumData.MaxX, MaxY = AtlasMuseumData.MaxY,
        Walls = AtlasMuseumData.Walls, ShadowWalls = AtlasMuseumData.ShadowWalls,
        Opaque = AtlasMuseumData.Opaque, OpaqueCastsShadow = AtlasMuseumData.OpaqueCastsShadow,
        Glass = AtlasMuseumData.Glass, Rooms = AtlasMuseumData.Rooms, Hallways = AtlasMuseumData.Hallways,
        FloorPixelsPerMeter = AtlasMuseumData.FloorPixelsPerMeter, FloorTiles = AtlasMuseumData.FloorTiles,
        PropPixelsPerMeter = AtlasMuseumData.PropPixelsPerMeter, Props = AtlasMuseumData.Props,
        ConsoleSprites = AtlasMuseumData.ConsoleSprites,
        NoFadeKinds = new() { "dino" },
        Consoles = AtlasMuseumLayout.Consoles,
        EmergencyButton = AtlasMuseumLayout.EmergencyButton, SurveillanceConsole = AtlasMuseumLayout.SurveillanceConsole,
        AdminTable = AtlasMuseumLayout.AdminTable, FreeplayLaptop = AtlasMuseumLayout.FreeplayLaptop,
        Spawn = AtlasMuseumLayout.Spawn, SpawnRadius = AtlasMuseumLayout.SpawnRadius,
        Vents = AtlasMuseumLayout.Vents, VentNetworks = AtlasMuseumLayout.VentNetworks,
        VerticalDoors = AtlasMuseumLayout.VerticalDoors, HorizontalDoors = AtlasMuseumLayout.HorizontalDoors,
        Cameras = AtlasMuseumLayout.Cameras, MapButtons = AtlasMuseumLayout.MapButtons,
        CameraColor = new Color(0x14 / 255f, 0x17 / 255f, 0x1c / 255f),
        ViewSpots = new Vector2[] { new(-6.9f, -7.2f), new(24.5f, -11.4f), new(22.8f, -4.3f), new(-9f, 7.65f), new(-27.4f, -16.8f) },
        TaskNames = new()
        {
            { TaskTypes.FixWiring, "Repair Showcase Lighting" },
            { TaskTypes.SwipeCard, "Close Out the Till" },
            { TaskTypes.CalibrateDistributor, "Stabilise Climate Control" },
            { TaskTypes.ChartCourse, "Trace a Constellation" },
            { TaskTypes.CleanO2Filter, "Dust the Skeleton" },
            { TaskTypes.DivertPower, "Restore Exhibit Power" },
            { TaskTypes.PrimeShields, "Arm the Vault Showcase" },
            { TaskTypes.StabilizeSteering, "Focus the Dome Projector" },
            { TaskTypes.UnlockManifolds, "Hieroglyph Sequence" },
            { TaskTypes.UploadData, "Sync the Audio Guide" },
            { TaskTypes.AlignEngineOutput, "Align the Flywheel" },
            { TaskTypes.ClearAsteroids, "Chase the Moths" },
            { TaskTypes.EmptyGarbage, "Empty the Bins" },
            { TaskTypes.FuelEngines, "Stoke the Steam Engine" },
            { TaskTypes.InspectSample, "Pigment Analysis" },
            { TaskTypes.StartReactor, "Tomb Lock" },
            { TaskTypes.SubmitScan, "Authenticity X-Ray" },
            { TaskTypes.ResetReactor, "Security Alarm" },
            { TaskTypes.RestoreOxy, "Climate Failure" },
            { TaskTypes.FixLights, "Replace the Fuses" },
            { TaskTypes.FixComms, "Restore the CCTV" },
        },
        CustomTasks = new()
        {
            { TaskTypes.CleanO2Filter, "dust" }, { TaskTypes.SwipeCard, "till" }, { TaskTypes.EmptyGarbage, "bins" },
            { TaskTypes.DivertPower, "fuse" }, { TaskTypes.FixWiring, "light" }, { TaskTypes.StartReactor, "tomb" },
            { TaskTypes.StabilizeSteering, "projector" }, { TaskTypes.UnlockManifolds, "hiero" }, { TaskTypes.PrimeShields, "vault" },
            { TaskTypes.CalibrateDistributor, "climate" }, { TaskTypes.AlignEngineOutput, "flywheel" }, { TaskTypes.FuelEngines, "steam" },
            { TaskTypes.ChartCourse, "constellation" }, { TaskTypes.ClearAsteroids, "moths" }, { TaskTypes.InspectSample, "pigment" },
            { TaskTypes.UploadData, "audio" },
            { TaskTypes.ResetReactor, "alarm" }, { TaskTypes.RestoreOxy, "climatefail" },
            { TaskTypes.FixLights, "fusebox" }, { TaskTypes.FixComms, "cctv" },
        },
    };

    /// <summary>Moonlight Carnival (docs/PARK_KONZEPT.md), Karte aus tools/gen_park.py, Minispiel-Grafik aus
    /// tools/gen_park_tasks.py. Die Minispiele sind Bausteine von Museum und Wald (TaskArt/TaskText).</summary>
    public static AtlasMapDef Park() => new()
    {
        Key = "park", DisplayName = "Moonlight Carnival", ResourcePrefix = "park",
        MinX = AtlasParkData.MinX, MinY = AtlasParkData.MinY, MaxX = AtlasParkData.MaxX, MaxY = AtlasParkData.MaxY,
        Walls = AtlasParkData.Walls, ShadowWalls = AtlasParkData.ShadowWalls,
        Opaque = AtlasParkData.Opaque, OpaqueCastsShadow = AtlasParkData.OpaqueCastsShadow,
        Glass = AtlasParkData.Glass, Rooms = AtlasParkData.Rooms, Hallways = AtlasParkData.Hallways,
        FloorPixelsPerMeter = AtlasParkData.FloorPixelsPerMeter, FloorTiles = AtlasParkData.FloorTiles,
        PropPixelsPerMeter = AtlasParkData.PropPixelsPerMeter, Props = AtlasParkData.Props,
        ConsoleSprites = AtlasParkData.ConsoleSprites,
        Consoles = AtlasParkLayout.Consoles,
        EmergencyButton = AtlasParkLayout.EmergencyButton, SurveillanceConsole = AtlasParkLayout.SurveillanceConsole,
        AdminTable = AtlasParkLayout.AdminTable, FreeplayLaptop = AtlasParkLayout.FreeplayLaptop,
        Spawn = AtlasParkLayout.Spawn, SpawnRadius = AtlasParkLayout.SpawnRadius,
        Vents = AtlasParkLayout.Vents, VentNetworks = AtlasParkLayout.VentNetworks, VentBridges = AtlasParkLayout.VentBridges,
        VerticalDoors = AtlasParkLayout.VerticalDoors, HorizontalDoors = AtlasParkLayout.HorizontalDoors,
        Cameras = AtlasParkLayout.Cameras, MapButtons = AtlasParkLayout.MapButtons,
        CameraColor = new Color(0x12 / 255f, 0x14 / 255f, 0x20 / 255f),
        // Festplatz (Spawn), Karussell, Lichtturm, Haupteingang, Security Booth mit Kameras (Stilblatt-Abnahme)
        ViewSpots = new Vector2[] { new(0f, 3.5f), new(-18.5f, -3.9f), new(17f, 14.2f), new(0f, -20.6f), new(12.5f, -12.5f) },
        TaskNames = new()
        {
            { TaskTypes.FixWiring, "Fix the Light Strings" },
            { TaskTypes.SwipeCard, "Badge Through the Turnstile" },
            { TaskTypes.CalibrateDistributor, "Balance the Carousel Motors" },
            { TaskTypes.ChartCourse, "Plan the Parade Route" },
            { TaskTypes.CleanO2Filter, "Clean the Cotton Candy Machine" },
            { TaskTypes.DivertPower, "Power a Ride" },
            { TaskTypes.PrimeShields, "Aim the Tower Spotlights" },
            { TaskTypes.StabilizeSteering, "Spot the Runaway Balloon" },
            { TaskTypes.UnlockManifolds, "Unlock the Ride Keys" },
            { TaskTypes.UploadData, "Collect the Ride Photos" },
            // zwei Motive (Karussell, Autoscooter) auf einem TaskType, wie Saege/Aussenborder im Wald
            { TaskTypes.AlignEngineOutput, "Tune the Ride Motors" },
            { TaskTypes.ClearAsteroids, "Shooting Gallery" },
            { TaskTypes.EmptyGarbage, "Clear the Popcorn Bins" },
            { TaskTypes.FuelEngines, "Refuel the Ride Generators" },
            { TaskTypes.InspectSample, "Allergen Test" },
            { TaskTypes.StartReactor, "Pump the Coaster Brakes" },
            { TaskTypes.SubmitScan, "Height Check" },
            { TaskTypes.ResetReactor, "Coaster Brake Failure" },
            { TaskTypes.RestoreOxy, "Ammonia Leak" },
            { TaskTypes.FixLights, "Park Blackout" },
            { TaskTypes.FixComms, "Speaker Feedback" },
        },
        // Swipe Card und Submit Scan bleiben vanilla (Drehkreuz-Ausweis, Messlatte)
        CustomTasks = new()
        {
            { TaskTypes.FixWiring, "lightstring" }, { TaskTypes.CalibrateDistributor, "motors" }, { TaskTypes.ChartCourse, "parade" },
            { TaskTypes.CleanO2Filter, "candy" }, { TaskTypes.DivertPower, "ridepower" }, { TaskTypes.PrimeShields, "spotlights" },
            { TaskTypes.StabilizeSteering, "balloon" }, { TaskTypes.UnlockManifolds, "ridekeys" }, { TaskTypes.UploadData, "photos" },
            { TaskTypes.AlignEngineOutput, "ridemotors" }, { TaskTypes.ClearAsteroids, "gallery" }, { TaskTypes.EmptyGarbage, "popcorn" },
            { TaskTypes.FuelEngines, "ridefuel" }, { TaskTypes.InspectSample, "allergen" }, { TaskTypes.StartReactor, "brakes" },
            { TaskTypes.ResetReactor, "brakefail" }, { TaskTypes.RestoreOxy, "ammonia" },
            { TaskTypes.FixLights, "blackout" }, { TaskTypes.FixComms, "feedback" },
        },
        TaskArt = ParkTaskArt(),
        TaskText = new()
        {
            { "motors:TEMP", "SPEED" }, { "motors:HUMIDITY", "ORGAN" }, { "motors:LIGHT", "LIGHTS" },
            { "parade:PATROL ROUTE", "PARADE ROUTE" },
            { "photos:FIND THE ANIMAL", "FIND THE SCREAMER" }, { "photos:COPYING", "PRINTING" },
            { "photos:INSERT THE SD CARD", "INSERT THE PHOTO CARD" },
            { "brakefail:TRACK THE PRINT", "FOLLOW THE BRAKE" },
            { "blackout:REPLACE THE BLOWN FUSES", "REPLACE THE BLOWN BULBS" },
            { "feedback:AZIMUTH", "AIM" }, { "feedback:FREQ", "GAIN" }, { "feedback:SIGNAL", "SOUND" },
        },
    };

    private static Dictionary<string, string> ParkTaskArt()
    {
        var a = new Dictionary<string, string>
        {
            // Tafeln: gestreifte Budenwand statt Holz/Museum, dunkles Fahrgeschaeft-Blech statt Stahl
            { "task_museum_panel.png", "task_park_panel.png" }, { "task_wald_panel.png", "task_park_panel.png" },
            { "task_shop_panel.png", "task_park_panel.png" }, { "task_steel_panel.png", "task_park_machine.png" },
            { "candy:task_museum_dino.png", "task_park_candy.png" }, { "candy:task_museum_dust.png", "task_park_sugar.png" },
            { "parade:task_trailmap.png", "task_park_parademap.png" }, { "parade:task_flag.png", "task_park_pennant.png" },
            { "parade:task_marker.png", "task_park_float.png" },
            { "spotlights:task_emitter.png", "task_park_spotlight.png" },
            { "balloon:task_panorama.png", "task_park_panorama.png" }, { "balloon:task_deer.png", "task_park_balloon.png" },
            { "ridekeys:task_cartouche.png", "task_park_keytag.png" },
            { "photos:task_photo.png", "task_park_photo.png" }, { "photos:task_deer.png", "task_park_rider.png" },
            { "photos:task_pc.png", "task_park_kiosk.png" },
            { "gallery:task_clearing.png", "task_park_booth.png" }, { "gallery:task_deer.png", "task_park_duck.png" },
            { "gallery:task_boar.png", "task_park_duck2.png" }, { "gallery:task_owl.png", "task_park_clown.png" },
            { "popcorn:task_container.png", "task_park_container.png" },
            { "ridefuel:task_boiler.png", "task_park_tank.png" },
            { "brakes:task_pump_body.png", "task_park_pump.png" }, { "brakes:task_water.png", "task_park_oil.png" },
            // Sabotagen
            { "brakefail:task_scanner.png", "task_park_brakepad.png" }, { "brakefail:task_marker.png", "task_park_brakeknob.png" },
            { "blackout:task_fuse_ok.png", "task_park_bulb_ok.png" }, { "blackout:task_fuse_dead.png", "task_park_bulb_dead.png" },
            { "blackout:task_fuse_new.png", "task_park_bulb_new.png" },
            { "feedback:task_dish.png", "task_park_speaker.png" },
        };
        for (int k = 0; k < 10; k++) a[$"ridekeys:task_glyph{k}.png"] = $"task_park_glyph{k}.png";
        return a;
    }

    public static AtlasMapDef Wald() => new()
    {
        Key = "wald", DisplayName = "Forest Station", ResourcePrefix = "wald",
        MinX = AtlasWaldData.MinX, MinY = AtlasWaldData.MinY, MaxX = AtlasWaldData.MaxX, MaxY = AtlasWaldData.MaxY,
        Walls = AtlasWaldData.Walls, ShadowWalls = AtlasWaldData.ShadowWalls,
        Opaque = AtlasWaldData.Opaque, OpaqueCastsShadow = AtlasWaldData.OpaqueCastsShadow,
        Glass = AtlasWaldData.Glass, Rooms = AtlasWaldData.Rooms, Hallways = AtlasWaldData.Hallways,
        FloorPixelsPerMeter = AtlasWaldData.FloorPixelsPerMeter, FloorTiles = AtlasWaldData.FloorTiles,
        PropPixelsPerMeter = AtlasWaldData.PropPixelsPerMeter, Props = AtlasWaldData.Props,
        ConsoleSprites = AtlasWaldData.ConsoleSprites,
        Consoles = AtlasWaldLayout.Consoles,
        EmergencyButton = AtlasWaldLayout.EmergencyButton, SurveillanceConsole = AtlasWaldLayout.SurveillanceConsole,
        AdminTable = AtlasWaldLayout.AdminTable, FreeplayLaptop = AtlasWaldLayout.FreeplayLaptop,
        Spawn = AtlasWaldLayout.Spawn, SpawnRadius = AtlasWaldLayout.SpawnRadius,
        Vents = AtlasWaldLayout.Vents, VentNetworks = AtlasWaldLayout.VentNetworks,
        VerticalDoors = AtlasWaldLayout.VerticalDoors, HorizontalDoors = AtlasWaldLayout.HorizontalDoors,
        Cameras = AtlasWaldLayout.Cameras, MapButtons = AtlasWaldLayout.MapButtons,
        CameraColor = new Color(0x16 / 255f, 0x30 / 255f, 0x1f / 255f),
        // Messe (Spawn), Funkmast-Vent, Generator-Vent, Steg, Wachstube mit Kameras
        ViewSpots = new Vector2[] { new(0f, 1f), new(10.2f, 12.2f), new(-16.8f, -13.4f), new(28.5f, -14.4f), new(-27f, -14.5f) },
        TaskNames = new()
        {
            { TaskTypes.FixWiring, "Splice Field Cable" },
            { TaskTypes.SwipeCard, "Punch the Time Card" },
            { TaskTypes.CalibrateDistributor, "Tune the Generator" },
            { TaskTypes.ChartCourse, "Plot the Patrol Route" },
            { TaskTypes.CleanO2Filter, "Clear the Intake Grate" },
            { TaskTypes.DivertPower, "Route Generator Power" },
            { TaskTypes.PrimeShields, "Light the Dock Lanterns" },
            { TaskTypes.StabilizeSteering, "Focus the Binoculars" },
            { TaskTypes.UnlockManifolds, "Open the Valves" },
            { TaskTypes.UploadData, "Collect Trail Cam Footage" },
            // zwei Motive (Saegewerk, Bootshaus) auf einem TaskType; GetString kennt den Schritt nicht
            { TaskTypes.AlignEngineOutput, "Align Saw and Outboard" },
            { TaskTypes.ClearAsteroids, "Wildlife Census" },
            { TaskTypes.EmptyGarbage, "Haul the Compost" },
            { TaskTypes.FuelEngines, "Refuel the Machines" },
            { TaskTypes.InspectSample, "Water Sample Analysis" },
            { TaskTypes.StartReactor, "Prime the Pump" },
            { TaskTypes.SubmitScan, "Tick Check" },
            { TaskTypes.ResetReactor, "Forest Fire" },
            { TaskTypes.RestoreOxy, "Water Supply Failure" },
            { TaskTypes.FixLights, "Reset the Breakers" },
            { TaskTypes.FixComms, "Realign the Radio Mast" },
        },
        CustomTasks = new()
        {
            { TaskTypes.StartReactor, "pump" }, { TaskTypes.EmptyGarbage, "compost" }, { TaskTypes.DivertPower, "route" },
            { TaskTypes.FixWiring, "splice" }, { TaskTypes.SwipeCard, "timecard" }, { TaskTypes.CalibrateDistributor, "generator" },
            { TaskTypes.ChartCourse, "patrol" }, { TaskTypes.CleanO2Filter, "grate" }, { TaskTypes.StabilizeSteering, "binoculars" },
            { TaskTypes.UnlockManifolds, "valves" }, { TaskTypes.UploadData, "trailcam" }, { TaskTypes.AlignEngineOutput, "saw" },
            { TaskTypes.ClearAsteroids, "census" }, { TaskTypes.FuelEngines, "refuel" }, { TaskTypes.InspectSample, "water" },
            { TaskTypes.PrimeShields, "lanterns" },
            { TaskTypes.ResetReactor, "fire" }, { TaskTypes.RestoreOxy, "waterworks" },
            { TaskTypes.FixLights, "breakers" }, { TaskTypes.FixComms, "antenna" },
        },
    };
}
