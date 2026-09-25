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
// Kartenverkleinerung 24.09. (docs/KARTEN_VERKLEINERUNG.md): zusammengelegte Raeume bestehen aus
// Teilflaechen gleichen Namens, je Skeld-System eine (Foyer = Cafeteria + Admin-Shop-Ecke,
// Rotunda = LifeSupp + Shields-Nische, Depot & Loading Dock = LowerEngine + Storage).
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
        ["Cafeteria/DataConsole/2"] = new(7.75f, -8.2f),                // Download (Ostwand, noerdlich des Kassenhaeuschens; das Ost-Tor liegt jetzt weiter noerdlich)
        ["Cafeteria/FixWiringConsole/4"] = new(-6.5f, -3.3f),
        ["Cafeteria/GarbageConsole/2"] = new(6.3f, -3.3f),

        // Foyer, Shop-Ecke (Admin)
        ["Admin/SwipeCardConsole/0"] = new(-4.7f, -11.2f),              // Kasse (Shop-Ecke, Kundenseite des Tresens)
        ["Admin/UploadDataConsole/0"] = new(-7.75f, -12.4f),            // Upload (Westwand unter dem Wandregal)
        ["Admin/FixWiringConsole/2"] = new(-1.6f, -12.8f),
        ["Admin/NoOxyConsole/1"] = new(20.8f, -7.1f),                   // G2 Loeschgas (Depot)

        // Sicherheitszentrale (Security)
        ["Security/DivertPowerConsole/1"] = new(-8.75f, -1.8f),         // Ostwand, noerdlich des Foyer-Tors
        ["Security/FixWiringConsole/5"] = new(-14.4f, -0.75f),
        ["Reactor/UpperHandConsole/0"] = new(-13.0f, -0.8f),            // A1 Einbruchalarm

        // Haustechnik (Electrical)
        ["Electrical/SwitchConsole/0"] = new(-23.0f, -5.2f),            // L Sicherungskasten
        ["Electrical/CalibrateConsole/0"] = new(-17.2f, -3.8f),
        ["Electrical/DivertPowerConsole/0"] = new(-16.2f, -4.0f),
        ["Electrical/UploadDataConsole/0"] = new(-22.7f, -11.2f),       // Download
        ["Electrical/FixWiringConsole/0"] = new(-16.2f, -9.6f),
        ["LifeSupp/NoOxyConsole/0"] = new(-16.2f, -8.0f),               // G1 Loeschgas

        // Aegyptischer Saal (Reactor)
        ["Reactor/StartReactorConsole/2"] = new(-23.0f, 1.5f),
        ["Reactor/UnlockManifoldsConsole/2"] = new(-17.4f, 2.9f),
        ["Reactor/LowerHandConsole/1"] = new(20.35f, 6.4f),             // A2 Einbruchalarm (Rampe, noerdlich des Rolltors)

        // Gemaeldegalerie (Weapons)
        ["Weapons/WeaponConsole/0"] = new(-10.5f, 7.7f),
        ["Weapons/UploadDataConsole/1"] = new(-15.1f, 6.6f),            // Download (Westwand; Nordwand hat das Planetarium-Tor)
        ["Weapons/DivertPowerConsole/1"] = new(-15.1f, 1.6f),           // Westwand, suedlich der Aegypten-Tuer

        // Planetarium (Nav)
        ["Nav/ChartCourseConsole/0"] = new(-14.5f, 16.2f),
        ["Nav/StabilizeSteeringConsole/0"] = new(-13.3f, 13.1f),        // am Projektor (ostseitig, frei vom Linsenarm)
        ["Nav/UploadDataConsole/0"] = new(-17.1f, 10.5f),               // Download
        ["Nav/DivertPowerConsole/1"] = new(-17.1f, 14.0f),
        ["Nav/FixWiringConsole/3"] = new(-8.8f, 10.0f),

        // Rotunden-Nische, ehemals Mineralienkabinett (Shields)
        ["Shields/ShieldConsole/0"] = new(0.0f, 13.9f),                 // vor der Tresorvitrine (Rotunden-Nische)
        ["Shields/DivertPowerConsole/1"] = new(3.6f, 16.2f),

        // Telefonzentrale (Comms)
        ["Comms/FixCommsConsole/0"] = new(12.5f, 15.1f),                // C Telefonanlage
        ["Comms/UploadDataConsole/1"] = new(17.7f, 15.8f),              // Download (Ostwand, noerdlich des Funkregals)
        ["Comms/DivertPowerConsole/1"] = new(9.3f, 10.6f),

        // Technikhalle (UpperEngine)
        ["UpperEngine/AlignEngineConsole/0"] = new(17.6f, 4.95f),       // vor der Turbine (dahinter verdeckte sie das Sprite)
        ["UpperEngine/FuelEngineConsole/0"] = new(9.2f, 4.6f),          // Kessel der Dampfmaschine
        ["UpperEngine/DivertPowerConsole/1"] = new(10.0f, 1.3f),

        // Depot & Laderampe, Rampenteil (LowerEngine)
        ["LowerEngine/AlignEngineConsole/1"] = new(21.5f, 9.0f),
        ["LowerEngine/FuelEngineConsole/0"] = new(24.2f, 3.8f),         // Tank des Lieferwagens
        ["LowerEngine/DivertPowerConsole/1"] = new(27.6f, 9.0f),

        // Restaurierungswerkstatt (MedBay)
        ["MedBay/MedScanner/0"] = new(16.0f, -4.5f),                    // Roentgenrahmen
        ["MedBay/MedBayConsole/0"] = new(11.2f, -0.9f),                 // Inspect Sample

        // Depot & Laderampe, Depotteil (Storage)
        ["Storage/gasCanConsole/0"] = new(23.0f, -7.1f),                // Kanister (Fuel Teil 1)
        ["Storage/FixWiringConsole/1"] = new(20.3f, -6.4f),
        ["Storage/AirlockConsole/0"] = new(27.6f, -5.8f),               // Muellschacht

        // Rotunde (LifeSupp)
        ["LifeSupp/CleanFilterConsole/0"] = new(-3.4f, 2.5f),              // Skelett abstauben: vor dem ueberragenden Kopf
        ["LifeSupp/GarbageConsole/0"] = new(3.75f, -1.2f),              // an der SO-Diagonalwand (stand hinter der Vitrine)
        ["LifeSupp/DivertPowerConsole/1"] = new(2.2f, 10.3f),           // an der Nordwand
    };

    // SystemConsole/MapConsole: ueber Typ und Rolle statt Namen gefunden (AtlasMuseumBuilder).
    public static readonly Vector2 EmergencyButton = new(0f, -5.35f);   // vor der Infotheke (Nordseite), ausserhalb ihres Sprites
    public static readonly Vector2 SurveillanceConsole = new(-14.5f, -2.7f);   // vor der Monitorwand (Westwand)
    public static readonly Vector2 AdminTable = new(-12.5f, -6.05f);   // Gebaeudeplan: vor dem Tisch an der Suedwand
    public static readonly Vector2 FreeplayLaptop = new(5.0f, -12.6f);

    // Sabotage "Rex erwacht" (AtlasRex): Stationen = Objekte "spieluhr"/"nachtlicht" aus museum_layout.py
    public static readonly Vector2 RexMusicBox = new(1.6f, 2.2f);       // Rotunde, vor dem Podest
    public static readonly Vector2 RexNightLight = new(-10.4f, -3.6f);  // Security Office, Raummitte
    public static readonly Vector2 RexMapButton = new(-1.2f, 6.0f);     // Kartenknopf (Rotunde, unter dem Kopf)

    // ---------------------------------------------------------------- Vents

    /// <summary>Vent-Id (Skeld) -> Museumsplatz. Nicht gelistete Vents fallen dem Wipe zu.</summary>
    public static readonly Dictionary<int, Vector2> Vents = new()
    {
        [11] = new(-22.4f, 7.4f),    // W1 Aegypten
        [3] = new(-16.9f, -10.9f),   // W2 Haustechnik
        [5] = new(-9.4f, -7.2f),     // W3 Sicherheit
        [7] = new(-14.6f, 0.6f),     // M1 Galerie
        [6] = new(18.9f, -5.4f),     // M2 Werkstatt
        [0] = new(2.0f, -12.5f),     // M3 Foyer (Shop)
        [10] = new(-3.8f, 15.9f),    // O1 Rotunden-Nische
        [4] = new(18.9f, 1.6f),      // O2 Technikhalle
        [9] = new(27.2f, -1.2f),     // O3 Depot
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
    // Die Skeld hat 7 senkrechte und 6 waagerechte Tueren. Ueberzaehlige Tueren blieben an ihrem
    // Skeld-Platz (unter dem Grundriss) stehen, deshalb genau 7 + 6 Oeffnungen (museum_layout.OPENINGS).
    // Gruppen = nur Schluessel fuer die Tuer-Sabotage; alle sieben Skeld-Tuergruppen sind belegt.

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
        new("Foyer-West", -8.25f, -5.0f, 2.5f, SystemTypes.Security),
        new("Foyer-Ost", 8.25f, -4.5f, 2.5f, SystemTypes.MedBay),
        new("Sicherheit-West", -15.65f, -6.25f, 2.5f, SystemTypes.Electrical),
        new("Aegypten-Ost", -15.65f, 4.25f, 2.5f, SystemTypes.Electrical),
        new("Telefon-West", 8.75f, 13.75f, 2.5f, SystemTypes.LowerEngine),
        new("Rolltor", 19.75f, 3.0f, 4.0f, SystemTypes.Cafeteria, seeThrough: false),
        new("Werkstatt-Ost", 19.75f, -3.25f, 2.5f, SystemTypes.Storage),
    };

    public static readonly DoorSlot[] HorizontalDoors =
    {
        new("Sicherheit-Nord", -10.25f, -0.25f, 2.5f, SystemTypes.Security),
        new("Haustechnik-Nord", -19.65f, -3.25f, 2.5f, SystemTypes.Electrical),
        new("Planetarium-Sued", -13.75f, 8.25f, 2.5f, SystemTypes.UpperEngine),
        new("Telefon-Sued", 13.25f, 9.75f, 2.5f, SystemTypes.LowerEngine),
        new("Technikhalle-Sued", 15.25f, 0.75f, 2.5f, SystemTypes.MedBay),
        new("Depot-Nord", 21.55f, -0.05f, 2.5f, SystemTypes.Storage),
    };

    // -------------------------------------------------------------- Kameras

    /// <summary>K1 Rotunde, K2 Galerie, K3 Technikhalle, K4 Laderampe.</summary>
    public static readonly Vector2[] Cameras =
    {
        new(3.3f, 9.3f),
        new(-15.1f, 7.7f),
        new(7.4f, 9.1f),
        new(20.4f, 9.2f),
    };

    // -------------------------------------------------------------- Minimap

    /// <summary>
    /// Wo die Sabotage-/Tuerknoepfe der Minimap (MapRoom je SystemTypes) sitzen. Tuerknoepfe
    /// gehoeren zur Gruppe (VerticalDoors/HorizontalDoors), Sonderknoepfe zur Station.
    /// </summary>
    public static readonly Dictionary<SystemTypes, Vector2> MapButtons = new()
    {
        [SystemTypes.Cafeteria] = new(21.5f, 3.0f),       // Rolltor
        [SystemTypes.Storage] = new(24.0f, -4.8f),
        [SystemTypes.MedBay] = new(14.0f, -3.0f),
        [SystemTypes.Security] = new(-12.0f, -4.5f),
        [SystemTypes.Electrical] = new(-19.6f, -7.5f),    // Tueren + Licht
        [SystemTypes.UpperEngine] = new(-13.75f, 11.0f),  // Planetarium-Gitter
        [SystemTypes.LowerEngine] = new(15.0f, 13.0f),    // Telefon-Gitter
        [SystemTypes.Reactor] = new(-19.0f, 2.5f),        // Einbruchalarm
        [SystemTypes.LifeSupp] = new(0f, 7.5f),           // Loeschgas
        [SystemTypes.Comms] = new(11.5f, 13.5f),          // Telefonanlage
    };

    // ---------------------------------------------------------------- Spawn

    public static readonly Vector2 Spawn = new(0f, -8f);
    public const float SpawnRadius = 3.2f;
}
