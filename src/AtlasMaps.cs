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
using System.Reflection;

namespace UnknownsAtlas;

public static class AtlasMaps
{
    /// <summary>Version dieser Schnittstelle (steigt bei inkompatiblen Aenderungen).</summary>
    public const int ApiVersion = 1;

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
}
