// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMaps - oeffentliche Schnittstelle fuer Karten aus anderen Plugins.
//
// Ein Plugin, das Atlas als Abhaengigkeit nennt, meldet in seinem Load() eine Karte an:
//
//     AtlasMaps.Register("mymap", "My Map", () => new AtlasMapDef { ... }, typeof(MyPlugin).Assembly,
//                        "MyPlugin.Resources", "button_mymap.png", "icon_mymap.png", "1.0.0");
//
// Die Karte erscheint dann neben Museum, Forest und Carnival im Freeplay-Menue und im Lobby-Kartenwaehler
// und wird genauso gebaut (Relocate-in-Place auf der Skeld). Die Factory laeuft vor jedem Kartenbau neu,
// sie darf also eigene Einstellungen lesen (zum Beispiel eine Groessen-Variante). Boden, Objekte, Konsolen
// und Minimap kommen aus den eingebetteten Ressourcen der angegebenen Assembly
// ("<Namensraum>.<Praefix>_floor_<i>.jpg" usw., siehe AtlasAssets).
//
// Im Handshake meldet jeder Client, welche fremden Karten er in welcher Inhaltsversion hat; ist eine
// solche Karte gewaehlt, sperrt der Host den Start, bis alle dieselbe haben.

using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace UnknownsAtlas;

public static class AtlasMaps
{
    /// <summary>Version dieser Schnittstelle (steigt bei inkompatiblen Aenderungen).</summary>
    public const int ApiVersion = 2;        // 2 (15.10.): AtlasMapDef.World + die Helfer unten

    /// <summary>
    /// Meldet eine Karte an. key: eindeutiger Schluessel (auch AppDomain "UnknownsAtlas.ActiveMap"),
    /// label: kurzer Name fuer die Knoepfe, make: Factory der Kartendaten, resources/resourceNamespace:
    /// Herkunft von Logo und Symbol (Kartenpaket: AtlasMapDef.ResourceAssembly/ResourceNamespace),
    /// button: Freeplay-Logo 1000 x 250 (null = Schriftzug), icon: Lobby-Symbol 256 x 256 (null = Skeld-Symbol),
    /// contentVersion: muss bei allen Spielern gleich sein. Rueckgabe false, wenn der Schluessel belegt ist.
    /// </summary>
    public static bool Register(string key, string label, Func<AtlasMapDef> make, Assembly resources,
        string resourceNamespace, string button = null, string icon = null, string contentVersion = "1")
    {
        try
        {
            return AtlasSelection.Register(new AtlasSelection.MapEntry
            {
                Key = key, Label = label ?? key, Make = make, Asm = resources, Ns = resourceNamespace,
                Button = button, Icon = icon, ContentVersion = contentVersion ?? "",
            });
        }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"[Atlas] map registration '{key}' failed: {e}");
            return false;
        }
    }

    /// <summary>Schluessel der gerade gebauten Atlas-Karte, sonst null.</summary>
    public static string ActiveKey => AtlasMuseumBuilder.Active ? AtlasMuseumBuilder.D?.Key : null;

    /// <summary>Schluessel der fuer die naechste Runde gewaehlten Karte (Lobby/Freeplay), sonst null.</summary>
    public static string SelectedKey => AtlasSelection.CurrentKey;

    // ------------------------------------------------------------------ Welt-Mechaniken (API 2, seit 15.10.)
    // Helfer fuer AtlasMapDef.World: der Use-Knopf, die gebauten Moebel, Bildfolgen, Geraeusche und der
    // Autotest. Alles nur waehrend eine Atlas-Karte steht; sonst still ohne Wirkung.

    /// <summary>Den Use-Knopf fuer diesen Frame anbieten (aus Tick heraus): Beschriftung, Symbol (256-px-Datei,
    /// zuerst aus dem Kartenpaket, sonst Atlas), Aktion; always = auch wenn Vanilla ein Ziel hat; enabled = false
    /// zeigt ihn ausgegraut. Das erste Angebot eines Frames gewinnt, Atlas' eigene Mechaniken kommen zuerst.</summary>
    public static void OfferUse(string label, string iconFile, Action onUse, bool always = false, bool enabled = true)
    {
        if (!AtlasMuseumBuilder.Active) return;
        AtlasUse.Offer(label, iconFile, onUse, always, enabled);
    }

    /// <summary>Lokaler Spieler lebt, kann sich bewegen, hat nichts offen und steht naeher als radius an spot.</summary>
    public static bool CanReach(Vector2 spot, float radius) => AtlasUse.CanReach(PlayerControl.LocalPlayer, spot, radius);

    /// <summary>Gebaute Moebel einer Art (AtlasMapDef.Props[].Kind): Index, Renderer, Standpunkt (Fussmitte).</summary>
    public static List<(int Index, SpriteRenderer Renderer, Vector2 Pos)> Props(string kind) => AtlasMuseumBuilder.PropsOfKind(kind);

    /// <summary>Ein Bild des Konsolen-Atlas der Karte (AtlasMapDef.ConsoleSprites, Schluessel) als Sprite; null ohne Eintrag.</summary>
    // Nicht an Active binden: IAtlasMapWorld.OnBuilt laeuft mitten im Kartenbau, Active wird erst danach true
    // (Test 16.10.: alle Tauschbilder einer angemeldeten Karte fehlten).
    public static Sprite SpriteFor(string key) => AtlasMuseumBuilder.D?.ConsoleSprites != null ? AtlasMuseumBuilder.SpriteFor(key, null) : null;

    /// <summary>"key" plus "key/1".."key/n" als Bildfolge; null, wenn schon das Ruhebild fehlt.</summary>
    public static Sprite[] SpriteSet(string key) => AtlasMuseumBuilder.D?.ConsoleSprites != null ? AtlasMuseumBuilder.SpriteSet(key, null) : null;

    /// <summary>Einzelgeraeusch aus Atlas' Klangvorrat (creak, whoosh, thud, slam, grind, clack, chime, ding, clock ...).</summary>
    public static void Sfx(string clip, float volume) => AtlasWeatherFx.Sfx(clip, volume);

    /// <summary>Autotest-Lauf (Freeplay mit Diagnostics.ForceMap oder TaskTest): nur dann darf ein Plugin den
    /// Spieler von selbst bewegen oder fotografieren.</summary>
    public static bool AutotestRun => AtlasMapShot.AutotestRun;

    /// <summary>Bildschirmfoto nach &lt;Spiel&gt;/AtlasShots/task_&lt;kind&gt;_&lt;tag&gt;_&lt;Uhrzeit&gt;.png (Autotest).</summary>
    public static void Shot(string kind, string tag) => AtlasTasks.Shot(kind, tag);
}
