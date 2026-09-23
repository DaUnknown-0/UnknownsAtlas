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
    public AtlasMuseumLayout.DoorSlot[] VerticalDoors, HorizontalDoors;
    public Vector2[] Cameras;
    public Dictionary<SystemTypes, Vector2> MapButtons;
    public Color CameraColor;
    public float MinLight = 1f, MaxLight = 5f;
    /// <summary>Diagnose (AtlasMapShot): Teststellen fuer Bildschirmfotos; die letzte oeffnet die Kameras.</summary>
    public Vector2[] ViewSpots = System.Array.Empty<Vector2>();

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
    };

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
    };
}
