// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasRoomDiag - Prototyp "zusaetzliche Raeume" (docs/PARK_KONZEPT.md, Schritt 2), nur im Autotest.
//
// Museum und Wald nutzen genau die 14 Skeld-Raeume. Die Parkkarte braucht mehr: Raeume mit eigenem
// Namen in der Standortanzeige und eigenem Zaehler auf dem Admin-Tisch, deren SystemTypes die Skeld
// gar nicht kennt. TaskTest "extraroom" macht dafuer im Builder aus dem Gang, der dem Spawn am
// naechsten liegt, einen Raum vom Typ Kitchen ("Test Room") und prueft dann:
//   1. Standortanzeige: der Spieler steht im Raum, der RoomTracker muss "Test Room" zeigen
//   2. Admin-Tisch: ein Dummy steht im Raum, der geklonte Zaehler muss ihn zaehlen
//   3. TORs Admin-Zaehlung (MapCountOverlay-Prefix, liest FastRooms[RoomType] je Zaehler) laeuft
//      ohne Fehler durch
// Das Ergebnis steht im Log ("[Atlas/Rooms] RESULT ...") und in zwei Bildschirmfotos.

using System;
using System.Text;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasRoomDiag
{
    private const string LogPrefix = "[Atlas/Rooms]";
    internal const SystemTypes RoomType = SystemTypes.Kitchen;
    internal const string RoomName = "Test Room";

    /// <summary>Der Builder soll den Testraum anlegen (nur im Autotest mit TaskTest "extraroom").</summary>
    internal static bool Wanted =>
        AtlasMapShot.AutotestRun &&
        string.Equals(AtlasPlugin.CfgTaskTest?.Value?.Trim(), "extraroom", StringComparison.OrdinalIgnoreCase);

    private static int _step;
    private static float _at;
    private static Vector2 _center;
    private static string _tracker = "?";
    private static MapConsole _console;

    internal static void Begin()
    {
        _step = 0;
        _at = Time.time;
    }

    /// <summary>Ein Schritt je Aufruf; true, wenn fertig.</summary>
    internal static bool Tick()
    {
        if (Time.time < _at) return false;
        try
        {
            switch (_step)
            {
                case 0:
                {
                    var ship = ShipStatus.Instance;
                    if (ship == null || !ship.FastRooms.ContainsKey(RoomType))
                    {
                        AtlasPlugin.Logger.LogError($"{LogPrefix} RESULT FAIL: no {RoomType} room in FastRooms (builder did not create it)");
                        return true;
                    }
                    var room = ship.FastRooms[RoomType];
                    _center = room.roomArea != null ? (Vector2)room.roomArea.bounds.center : (Vector2)room.transform.position;
                    PlayerControl.LocalPlayer.NetTransform.SnapTo(_center);
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} player snapped into the test room at ({_center.x:F1},{_center.y:F1})");
                    _step = 1; _at = Time.time + 1.5f;
                    return false;
                }
                case 1:
                {
                    var hud = HudManager.Instance;
                    _tracker = hud != null && hud.roomTracker != null && hud.roomTracker.text != null ? hud.roomTracker.text.text : "?";
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} room tracker shows '{_tracker}'");
                    AtlasTasks.Shot("extraroom", "tracker");
                    // ein Dummy in den Raum; der eigene Spieler bleibt stehen (Admin zeigt ihn nicht)
                    int moved = 0;
                    foreach (var d in Object.FindObjectsOfType<DummyBehaviour>())
                    {
                        var pc = d != null ? d.GetComponent<PlayerControl>() : null;
                        if (pc == null || pc.NetTransform == null) continue;
                        pc.NetTransform.SnapTo(_center + new Vector2(0.7f, 0f));
                        moved++;
                        break;
                    }
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} {moved} dummy moved into the test room");
                    _step = 2; _at = Time.time + 1f;
                    return false;
                }
                case 2:
                {
                    // wie ein Spieler: zum Admin-Tisch und ihn benutzen (ein direktes ToggleMapVisible
                    // oeffnete im Freeplay nichts, Test 23.09.)
                    _console = null;
                    foreach (var c in Object.FindObjectsOfType<MapConsole>()) { if (c != null) { _console = c; break; } }
                    if (_console == null) { AtlasPlugin.Logger.LogError($"{LogPrefix} RESULT FAIL: no admin console (MapConsole)"); return true; }
                    // Die Karte wird umgeschaltet, nicht geoeffnet: eine schon offene Karte (Klick im
                    // Testfenster, Test 23.09.) schloesse der Aufruf wieder. Also erst schliessen.
                    if (MapBehaviour.Instance != null && MapBehaviour.Instance.IsOpen) MapBehaviour.Instance.Close();
                    PlayerControl.LocalPlayer.NetTransform.SnapTo(_console.transform.position);
                    _step = 3; _at = Time.time + 0.8f;
                    return false;
                }
                case 3:
                    _console.Use();
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} admin console used, map {(MapBehaviour.Instance != null && MapBehaviour.Instance.IsOpen ? "open" : "NOT open")}");
                    _step = 4; _at = Time.time + 2f;
                    return false;
                case 5:
                    // erst jetzt schliessen: ScreenCapture schreibt am Ende des Frames, ein Close im
                    // selben Frame nahm die Karte mit aus dem Bild (Test 23.09.)
                    try { MapBehaviour.Instance?.Close(); } catch { }
                    return true;
                default:
                {
                    var map = MapBehaviour.Instance;
                    var sb = new StringBuilder();
                    int testCount = -1, counters = 0;
                    if (map != null && map.countOverlay != null && map.countOverlay.CountAreas != null)
                        foreach (var a in map.countOverlay.CountAreas)
                        {
                            if (a == null) continue;
                            counters++;
                            int icons = 0;
                            if (a.myIcons != null)
                                foreach (var ic in a.myIcons) if (ic != null && ic.gameObject.activeSelf) icons++;
                            sb.Append($"{a.RoomType}={icons}{(a.gameObject.activeInHierarchy ? "" : "(off)")} ");
                            if (a.RoomType == RoomType) testCount = icons;
                        }
                    AtlasPlugin.Logger.LogInfo($"{LogPrefix} admin counters ({counters}): {sb}");
                    AtlasTasks.Shot("extraroom", "admin");
                    bool nameOk = _tracker.Contains(RoomName);
                    bool countOk = testCount >= 1;
                    AtlasPlugin.Logger.LogInfo(
                        $"{LogPrefix} RESULT {(nameOk && countOk ? "PASS" : "FAIL")}: tracker '{_tracker}' ({(nameOk ? "ok" : "wrong")}), " +
                        $"test room counter {(testCount < 0 ? "missing" : testCount.ToString())} ({(countOk ? "ok" : "wrong")})");
                    _step = 5; _at = Time.time + 0.6f;
                    return false;
                }
            }
        }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"{LogPrefix} RESULT FAIL at step {_step}: {e}");
            return true;
        }
    }
}
