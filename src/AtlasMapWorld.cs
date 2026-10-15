// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// IAtlasMapWorld - Welt-Mechaniken einer Karte aus einem anderen Plugin (AtlasMaps.Register, API 2).
//
// Atlas ruft das Objekt an denselben Stellen wie seine eigenen Welt-Systeme (Wetter, Fahrgeschaefte,
// Rex): einmal nach dem Kartenbau, jeden Frame waehrend der Runde (HudManager.Update, nach Atlas'
// eigenen Mechaniken und vor AtlasUse.Commit, damit OfferUse eines Karten-Plugins greift), bei der
// Lichtberechnung des lokalen Spielers und beim Abbau des Schiffs. Die Factory der Karte liefert vor
// jedem Bau eine frische AtlasMapDef und damit auch ein frisches World-Objekt; Zustand lebt also je
// Runde. Alles laeuft in try/catch, ein Fehler im Plugin bringt die Karte nicht um.

using UnityEngine;

namespace UnknownsAtlas;

public interface IAtlasMapWorld
{
    /// <summary>Nach dem Kartenbau auf jedem Client; worldRoot ist das Welt-Objekt der Karte unter ShipStatus.</summary>
    void OnBuilt(Transform worldRoot);

    /// <summary>Jeder Frame waehrend der Runde (HudManager.Update), auf jedem Client.</summary>
    void Tick(float dt);

    /// <summary>Faktor auf den Sichtradius des lokalen Spielers an dieser Position (1 = unveraendert).</summary>
    float VisionFactor(Vector2 pos);

    /// <summary>ShipStatus.OnDestroy: eigene Objekte und Zustand aufraeumen.</summary>
    void OnDestroy();
}
