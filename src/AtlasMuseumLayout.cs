// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Wohin jedes Skeld-Objekt im Vesper-Museum wandert. Grundregel: eine Konsole landet im
// Museumsraum, dessen SystemTypes-Traeger ihr Console.Room ist (Zuordnung in
// tools/museum_layout.py, ROOMS). Dann stimmen die Ortsangaben der Taskliste ("Gallery:
// Clear Asteroids") ohne jeden Eingriff in die Tasks. Ausnahmen sind nur die Sabotage-
// Stationen, deren Raum im Spiel nirgends angezeigt wird: Einbruchalarm A1/A2 (Reaktor-
// Handflaechen) und Loeschgas G1/G2 (O2-Keypads) stehen dort, wo der Bauplan sie will.
//
// Quelle der Skeld-Namen: Nightfall-Survey skeldship.json (60 Konsolen, 14 Vents, 13 Tueren).
// Schluessel = "<Console.Room>/<GameObject-Name>/<ConsoleId>" - so eindeutig wie noetig, weil
// z.B. DivertPowerConsole mit ConsoleId 1 in acht Raeumen steht.

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasMuseumLayout
{
    // ------------------------------------------------------------ Konsolen

    public static readonly Dictionary<string, Vector2> Consoles = new()
    {
        // Foyer (Cafeteria)
        ["Cafeteria/DataConsole/2"] = new(7.85f, -5.9f),            // Download (Ostwand; hinter dem Kassenhaeuschen war sie verdeckt)
        ["Cafeteria/FixWiringConsole/4"] = new(-6.5f, -3.3f),
        ["Cafeteria/GarbageConsole/2"] = new(6.3f, -3.3f),

        // Museumsshop (Admin)
        ["Admin/SwipeCardConsole/0"] = new(-5.7f, -16.5f),          // Kasse
        ["Admin/UploadDataConsole/0"] = new(0.5f, -20.1f),          // Upload
        ["Admin/FixWiringConsole/2"] = new(8.7f, -14.0f),
        ["Admin/NoOxyConsole/1"] = new(22.3f, -20.1f),              // G2 Loeschgas (Depot)

        // Sicherheitszentrale (Security)
        ["Security/DivertPowerConsole/1"] = new(-22.7f, -15.6f),     // Ostwand (Suedwand ist im Bild unsichtbar)
        ["Security/FixWiringConsole/5"] = new(-28.4f, -13.25f),      // Nordwand, westlich der Tuer
        ["Reactor/UpperHandConsole/0"] = new(-23.2f, -13.3f),       // A1 Einbruchalarm

        // Haustechnik (Electrical)
        ["Electrical/SwitchConsole/0"] = new(-29.1f, -6.2f),        // L Sicherungskasten
        ["Electrical/CalibrateConsole/0"] = new(-23.3f, -4.8f),
        ["Electrical/DivertPowerConsole/0"] = new(-22.3f, -6.0f),
        ["Electrical/UploadDataConsole/0"] = new(-28.8f, -12.2f),   // Download
        ["Electrical/FixWiringConsole/0"] = new(-22.3f, -10.6f),
        ["LifeSupp/NoOxyConsole/0"] = new(-22.3f, -9.0f),           // G1 Loeschgas

        // Aegyptischer Saal (Reactor)
        ["Reactor/StartReactorConsole/2"] = new(-29.1f, 1.5f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(-23.5f, 2.9f),
        ["Reactor/LowerHandConsole/1"] = new(21.8f, -4.5f),         // A2 Einbruchalarm (Laderampe)

        // Gemaeldegalerie (Weapons)
        ["Weapons/WeaponConsole/0"] = new(-10.5f, 7.7f),
        ["Weapons/UploadDataConsole/1"] = new(-16.3f, 7.8f),        // Download (Nordwand zwischen den Stellwaenden)
        ["Weapons/DivertPowerConsole/1"] = new(-20.3f, 1.6f),       // Westwand, suedlich der Aegypten-Tuer

        // Planetarium (Nav)
        ["Nav/ChartCourseConsole/0"] = new(-14.5f, 20.1f),
        ["Nav/StabilizeSteeringConsole/0"] = new(-13.3f, 15.6f),    // am Projektor (ostseitig, frei vom Linsenarm)
        ["Nav/UploadDataConsole/0"] = new(-20.1f, 13.0f),           // Download
        ["Nav/DivertPowerConsole/1"] = new(-20.1f, 18.5f),
        ["Nav/FixWiringConsole/3"] = new(-8.8f, 12.5f),

        // Mineralienkabinett (Shields)
        ["Shields/ShieldConsole/0"] = new(0f, 13.9f),               // vor der Tresorvitrine
        ["Shields/DivertPowerConsole/1"] = new(2.0f, 20.1f),

        // Telefonzentrale (Comms)
        ["Comms/FixCommsConsole/0"] = new(12.5f, 19.1f),            // C Telefonanlage
        ["Comms/UploadDataConsole/1"] = new(17.7f, 13.35f),         // Download (Ostwand, unter dem Funkregal)
        ["Comms/DivertPowerConsole/1"] = new(9.3f, 14.0f),

        // Technikhalle (UpperEngine)
        ["UpperEngine/AlignEngineConsole/0"] = new(17.6f, 4.95f),     // vor der Turbine (dahinter verdeckte sie das Sprite)
        ["UpperEngine/FuelEngineConsole/0"] = new(9.2f, 4.6f),      // Kessel der Dampfmaschine
        ["UpperEngine/DivertPowerConsole/1"] = new(10.0f, -2.7f),

        // Laderampe (LowerEngine)
        ["LowerEngine/AlignEngineConsole/1"] = new(23.0f, 9.0f),
        ["LowerEngine/FuelEngineConsole/0"] = new(25.7f, 3.8f),     // Tank des Lieferwagens
        ["LowerEngine/DivertPowerConsole/1"] = new(29.1f, 9.0f),

        // Restaurierungswerkstatt (MedBay)
        ["MedBay/MedScanner/0"] = new(16.0f, -8.5f),                // Roentgenrahmen
        ["MedBay/MedBayConsole/0"] = new(11.2f, -4.9f),             // Inspect Sample

        // Depot (Storage)
        ["Storage/gasCanConsole/0"] = new(24.5f, -19.9f),           // Kanister (Fuel Teil 1)
        ["Storage/FixWiringConsole/1"] = new(21.8f, -11.4f),
        ["Storage/AirlockConsole/0"] = new(29.1f, -12.0f),          // Muellschacht

        // Rotunde (LifeSupp)
        ["LifeSupp/CleanFilterConsole/0"] = new(-1.8f, 6.7f),       // Skelett abstauben (hinter dem Hals frei sichtbar)
        ["LifeSupp/GarbageConsole/0"] = new(3.75f, -1.2f),          // an der SO-Diagonalwand (stand hinter der Vitrine)
        ["LifeSupp/DivertPowerConsole/1"] = new(2.2f, 10.3f),       // an der Nordwand
    };

    // SystemConsole/MapConsole: ueber Typ und Rolle statt Namen gefunden (AtlasMuseumBuilder).
    public static readonly Vector2 EmergencyButton = new(0f, -5.35f);   // vor der Infotheke (Nordseite), ausserhalb ihres Sprites
    public static readonly Vector2 SurveillanceConsole = new(-28.4f, -16.8f);
    public static readonly Vector2 AdminTable = new(-26.5f, -18.55f);   // Gebaeudeplan: vor dem Tisch an der Suedwand
    public static readonly Vector2 FreeplayLaptop = new(-7.3f, -12.3f);

    // ---------------------------------------------------------------- Vents

    /// <summary>Vent-Id (Skeld) -> Museumsplatz. Nicht gelistete Vents fallen dem Wipe zu.</summary>
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [11] = new(-28.5f, 8.6f),    // W1 Aegypten
        [3] = new(-23.0f, -11.9f),   // W2 Haustechnik
        [5] = new(-23.3f, -19.8f),   // W3 Sicherheit
        [7] = new(-19.6f, 7.2f),     // M1 Galerie
        [6] = new(19.7f, -12.9f),    // M2 Werkstatt
        [0] = new(-2.5f, -19.7f),    // M3 Shop
        [10] = new(5.3f, 11.6f),     // O1 Mineralien
        [4] = new(20.3f, 8.7f),      // O2 Technikhalle
        [9] = new(28.7f, -7.4f),     // O3 Depot
    };

    /// <summary>Drei Dreiecksnetze; kein Netz verbindet zwei Stationen derselben Sabotage.</summary>
    public static readonly int[][] VentNetworks =
    {
        new[] { 11, 3, 5 },
        new[] { 7, 6, 0 },
        new[] { 10, 4, 9 },
    };

    // --------------------------------------------------------------- Tueren

    // Rollgitter: Mitte der Oeffnung, Laenge entlang der Oeffnung, Tuergruppe (SystemTypes,
    // nur als Gruppenschluessel - angezeigt wird er nirgends), Sicht frei ja/nein.
    // Die Skeld hat 7 senkrechte und 6 waagerechte Tueren; der Bauplan hat 7 + 6 Oeffnungen.
    // Aegypten und Haustechnik teilen sich eine Gruppe (die Skeld kennt nur 7 Tuergruppen).

    public readonly struct DoorSlot
    {
        public readonly Vector2 Center;
        public readonly float Length;
        public readonly SystemTypes Group;
        public readonly bool SeeThrough;
        public readonly string Label;

        public DoorSlot(string label, float cx, float cy, float length, SystemTypes group, bool seeThrough = true)
        {
            Label = label;
            Center = new Vector2(cx, cy);
            Length = length;
            Group = group;
            SeeThrough = seeThrough;
        }
    }

    public static readonly DoorSlot[] VerticalDoors =
    {
        new("Foyer-Ost", 8.25f, -8.75f, 2.5f, SystemTypes.MedBay),
        new("Sicherheit-Ost", -22.25f, -18.0f, 2.0f, SystemTypes.Security),
        new("Aegypten-Ost", -20.75f, 4.25f, 2.5f, SystemTypes.Electrical),
        new("Planetarium-Ost", -8.25f, 16.25f, 2.5f, SystemTypes.UpperEngine),
        new("Telefon-West", 8.75f, 16.25f, 2.5f, SystemTypes.LowerEngine),
        new("Rolltor", 21.25f, 3.0f, 4.0f, SystemTypes.Cafeteria, seeThrough: false),
        new("Depot-West", 21.25f, -18.0f, 2.0f, SystemTypes.Storage),
    };

    public static readonly DoorSlot[] HorizontalDoors =
    {
        new("Technikhalle-Sued", 15.25f, -3.25f, 2.5f, SystemTypes.MedBay),
        new("Sicherheit-Nord", -25.75f, -12.75f, 2.5f, SystemTypes.Electrical),
        new("Haustechnik-Nord", -25.75f, -4.25f, 2.5f, SystemTypes.Electrical),
        new("Planetarium-Sued", -13.75f, 10.75f, 2.5f, SystemTypes.UpperEngine),
        new("Telefon-Sued", 13.25f, 12.75f, 2.5f, SystemTypes.LowerEngine),
        new("Depot-Nord", 25.25f, -6.25f, 2.5f, SystemTypes.Storage),
    };

    // -------------------------------------------------------------- Kameras

    /// <summary>K1 Rotunde, K2 Galerie-Achse, K3 Technikhalle/Rolltor, K4 Hof.</summary>
    public static readonly Vector2[] Cameras =
    {
        new(3.3f, 9.3f),
        new(-20.0f, 7.6f),
        new(20.6f, 9.2f),
        new(21.8f, 11.6f),
    };

    // -------------------------------------------------------------- Minimap

    /// <summary>
    /// Wo die Sabotage-/Tuerknoepfe der Minimap (MapRoom je SystemTypes) sitzen. Tuerknoepfe
    /// gehoeren zur Gruppe (VerticalDoors/HorizontalDoors), Sonderknoepfe zur Station.
    /// </summary>
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(25.5f, 3.0f),       // Rolltor
        [SystemTypes.Storage] = new(25.5f, -14.8f),
        [SystemTypes.MedBay] = new(14.5f, -8.5f),
        [SystemTypes.Security] = new(-26.0f, -17.0f),
        [SystemTypes.Electrical] = new(-25.7f, -8.5f),    // Tueren + Licht
        [SystemTypes.UpperEngine] = new(-14.5f, 14.5f),   // Planetarium-Gitter
        [SystemTypes.LowerEngine] = new(15.8f, 17.5f),    // Telefon-Gitter
        [SystemTypes.Reactor] = new(-25.0f, 2.5f),        // Einbruchalarm
        [SystemTypes.LifeSupp] = new(0f, 7.5f),           // Loeschgas
        [SystemTypes.Comms] = new(11.5f, 15.0f),          // Telefonanlage
    };

    // ---------------------------------------------------------------- Spawn

    public static readonly Vector2 Spawn = new(0f, -8f);
    public const float SpawnRadius = 3.2f;
}
