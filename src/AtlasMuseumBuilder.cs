// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMuseumBuilder - "Relocate-in-Place" fuer das Vesper-Museum.
//
// Das Museum BEHAELT
// die komplette Mechanik der Skeld: jede Konsole, jeder Vent, jede Tuer, jede Kamera und
// saemtliche Systeme bleiben dieselben Objekte mit denselben Ids. Sie werden nur an die
// Museumsplaetze gesetzt (D.cs). Was die Skeld netzwerkseitig kann, kann
// das Museum damit ohne eine Zeile eigenen Netzcode: Tasks, Sabotagen, Tueren, Kameras,
// Admin, Vents. Geworfen wird nur die Kulisse (Boeden, Waende, Deko) und die fuenf Vents,
// die der Bauplan nicht braucht.
//
// Hook: ShipStatus.Start-Postfix. Start laeuft auf JEDEM Client (Begin nur auf dem Host,
// dort werden die Tasks verteilt - die brauchen die Konsolen nicht an Ort und Stelle).
// SkeldShipStatus ueberschreibt Start nicht (Stub geprueft), der Basis-Patch greift also.
//
// ShipStatus.Type bleibt MapType.Ship: jede Vanilla-Verzweigung auf den Kartentyp soll sich
// genau wie auf der Skeld verhalten, denn es SIND die Skeld-Systeme. Andere Mods erkennen
// das Museum am AppDomain-Eintrag "UnknownsAtlas.ActiveMap" = "museum".
//
// Voraussetzung: die Lobby steht auf der Skeld. Auf jeder anderen Karte baut nichts.

using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using InnerNet;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasMuseumBuilder
{
    private const string LogPrefix = "[Atlas/Museum]";
    public const string AppDomainKey = "UnknownsAtlas.ActiveMap";

    // Physik-Ebenen (Nightfall-Survey: Ship 9, Shadow 10, ShortObjects 12, Ignore Raycast 2).
    private const int LayerShip = 9;
    private const int LayerShadow = 10;
    private const int LayerShortObjects = 12;
    private const int LayerIgnoreRaycast = 2;

    // Weltmeter -> z. Skeld: Boeden ~8, Konsolen ~6,8, Spieler ~y/1000.
    private const float FloorZ = 9f;
    private const float ColliderZ = 8f;   // Skeld-Wandtiefe, siehe BuildWalls

    private static ShipStatus _builtFor;

    /// <summary>Die Karte, die gerade gebaut wird bzw. aktiv ist.</summary>
    internal static AtlasMapDef D = AtlasMapDef.Museum();
    private static Material _maskingMaterial;
    private static Material _defaultSpriteMaterial;

    /// <summary>Sprite dem Sichtsystem unterwerfen (hinter Waenden abgedunkelt wie die Skeld).</summary>
    private static void Mask(SpriteRenderer sr)
    {
        if (sr != null && _maskingMaterial != null) sr.sharedMaterial = _maskingMaterial;
    }

    /// <summary>true, solange eine Museumsrunde laeuft (fuer die Raumnamen).</summary>
    internal static bool Active => _builtFor != null;

    internal static bool ShouldBuild(ShipStatus ship) =>
        AtlasPlugin.CfgEnabled is { Value: true } &&
        AtlasPlugin.CfgBuildPocMap is { Value: true } &&
        AtlasPlugin.SelectedMap() != null &&
        IsSkeld(ship);

    internal static bool IsSkeld(ShipStatus ship) =>
        ship != null && ship.Type == ShipStatus.MapType.Ship &&
        ship.name.StartsWith("SkeldShip", StringComparison.Ordinal);

    // ------------------------------------------------------------------ Patches

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.Awake))]
    internal static void ShipStatus_Awake_Postfix(ShipStatus __instance)
    {
        if (!ShouldBuild(__instance)) return;
        D = AtlasPlugin.SelectedMap();
        // Spawn frueh setzen: SpawnPlayer liest InitialSpawnCenter, bevor wir bauen koennten.
        try { ApplySpawn(__instance); }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} Awake failed: {e}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), "Start")]
    internal static void ShipStatus_Start_Postfix(ShipStatus __instance)
    {
        if (!ShouldBuild(__instance) || _builtFor == __instance) return;
        if (AtlasHandshake.DiagBuildFail) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: build skipped (TaskTest buildfail)"); return; }
        try
        {
            D = AtlasPlugin.SelectedMap();
            _blocks = null;
            VentArt.Clear();
            Build(__instance);
            _builtFor = __instance;
            AppDomain.CurrentDomain.SetData(AppDomainKey, D.Key);
            AtlasMapShot.Arm();
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} build failed: {e}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix(ShipStatus __instance)
    {
        if (_builtFor != null && _builtFor != __instance) return;
        _builtFor = null;
        FadeProps.Clear();
        VentArt.Clear();
        AppDomain.CurrentDomain.SetData(AppDomainKey, null);
    }

    /// <summary>Raumnamen: "Admin" -> "Museum Shop" usw., nur waehrend einer Museumsrunde.</summary>
    [HarmonyPostfix]
    [HarmonyPatch(typeof(TranslationController), nameof(TranslationController.GetString),
        new[] { typeof(SystemTypes) })]
    internal static void TranslationController_GetString_Postfix(SystemTypes room, ref string __result)
    {
        if (!Active) return;
        foreach (var r in D.Rooms)
        {
            if (r.Room != room) continue;
            __result = r.Name;
            return;
        }
    }

    /// <summary>
    /// Task-Namen der Karte ("Fix Wiring" -> "Repair Showcase Lighting"), nur waehrend einer
    /// Atlas-Runde. Wird in AtlasPlugin.Load einzeln und abgesichert gepatcht (PatchTaskNames),
    /// damit eine fehlende Ueberladung nicht die anderen Atlas-Patches mitreisst.
    /// </summary>
    internal static void TaskName_Postfix(TaskTypes task, ref string __result)
    {
        if (!Active) return;
        if (D.TaskNames.TryGetValue(task, out var name)) __result = name;
    }

    /// <summary>
    /// "Divert Power to Gallery" baut DivertPowerTask selbst aus StringNames.DivertPowerTo, nicht
    /// ueber GetString(TaskTypes): den vanilla Satzanfang durch den Kartennamen ersetzen
    /// ("Restore Exhibit Power - Gallery").
    /// </summary>
    internal static void DivertText_Postfix(Il2CppSystem.Text.StringBuilder __0)
    {
        if (!Active || __0 == null || !D.TaskNames.TryGetValue(TaskTypes.DivertPower, out var name)) return;
        var fmt = TranslationController.Instance?.GetString(StringNames.DivertPowerTo, new Il2CppSystem.Object[0]) ?? "";
        int cut = fmt.IndexOf("{0}", StringComparison.Ordinal);
        var prefix = cut > 0 ? fmt.Substring(0, cut) : "";
        if (prefix.Length > 0) __0.Replace(prefix, name + " - ");
    }

    /// <summary>"Download Data" (Schritt 1 von Upload Data) kommt aus StringNames, nicht aus GetString(TaskTypes).</summary>
    internal static void UploadText_Postfix(Il2CppSystem.Text.StringBuilder __0)
    {
        if (!Active || __0 == null || !D.TaskNames.TryGetValue(TaskTypes.UploadData, out var name)) return;
        var dl = TranslationController.Instance?.GetString(StringNames.DownloadData, new Il2CppSystem.Object[0]);
        if (!string.IsNullOrEmpty(dl)) __0.Replace(dl, name);
    }

    internal static void PatchTaskNames(HarmonyLib.Harmony harmony)
    {
        try
        {
            var upload = HarmonyLib.AccessTools.Method(typeof(UploadDataTask), nameof(UploadDataTask.AppendTaskText));
            if (upload != null)
                harmony.Patch(upload, postfix: new HarmonyLib.HarmonyMethod(typeof(AtlasMuseumBuilder), nameof(UploadText_Postfix)));
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} upload text patch failed: {e.Message}"); }

        try
        {
            var divert = HarmonyLib.AccessTools.Method(typeof(DivertPowerTask), nameof(DivertPowerTask.AppendTaskText));
            if (divert != null)
                harmony.Patch(divert, postfix: new HarmonyLib.HarmonyMethod(typeof(AtlasMuseumBuilder), nameof(DivertText_Postfix)));
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} divert text patch failed: {e.Message}"); }

        try
        {
            var target = HarmonyLib.AccessTools.Method(typeof(TranslationController), nameof(TranslationController.GetString),
                new[] { typeof(TaskTypes) });
            if (target == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} GetString(TaskTypes) not found - task names stay vanilla"); return; }
            harmony.Patch(target, postfix: new HarmonyLib.HarmonyMethod(typeof(AtlasMuseumBuilder), nameof(TaskName_Postfix)));
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} task names patched");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} task name patch failed: {e.Message}"); }
    }

    /// <summary>
    /// Diagnose (Test 22.09.: ein Task-Marker lag unter der Karte): beim Oeffnen der Karte jeden
    /// Task-Marker und den Hier-Punkt in Weltmeter zurueckrechnen und mit der naechsten Konsole
    /// bzw. der Spielerposition vergleichen. Ein fester Versatz aller Marker verraet sofort, ob
    /// die Task-Ebene anders verschoben werden muss als die Hier-Punkt-Ebene.
    /// </summary>
    [HarmonyPostfix]
    [HarmonyPatch(typeof(MapBehaviour), nameof(MapBehaviour.Show))]
    internal static void MapBehaviour_Show_Postfix(MapBehaviour __instance)
    {
        if (!Active || __instance == null || __instance.HerePoint == null) return;
        try
        {
            var ship = ShipStatus.Instance;
            float scale = ship != null ? ship.MapScale : 1f;
            var space = __instance.HerePoint.transform.parent;
            Vector2 ToWorld(Vector3 p) { var l = space.InverseTransformPoint(p); return new Vector2(l.x * scale, l.y * scale); }

            var lp = PlayerControl.LocalPlayer;
            if (lp != null)
            {
                var here = ToWorld(__instance.HerePoint.transform.position);
                var truth = (Vector2)lp.transform.position;
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} map check: here=({here.x:F1},{here.y:F1}) player=({truth.x:F1},{truth.y:F1})");
            }
            if (__instance.taskOverlay == null || ship == null) return;
            foreach (var r in __instance.taskOverlay.GetComponentsInChildren<SpriteRenderer>())
            {
                if (r == null || !r.enabled || !r.gameObject.activeInHierarchy) continue;
                var w = ToWorld(r.transform.position);
                string best = "-";
                float bestD = float.MaxValue;
                foreach (var c in ship.AllConsoles)
                {
                    if (c == null) continue;
                    float d = Vector2.Distance(w, c.transform.position);
                    if (d < bestD) { bestD = d; best = c.name; }
                }
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} map check: marker '{r.name}' at ({w.x:F1},{w.y:F1}) nearest console '{best}' d={bestD:F1}");
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} map check failed: {e.Message}"); }
    }

    // --------------------------------------------------------------------- Bau

    private static void ApplySpawn(ShipStatus ship)
    {
        ship.InitialSpawnCenter = D.Spawn;
        ship.MeetingSpawnCenter = D.Spawn;
        ship.MeetingSpawnCenter2 = D.Spawn;
        ship.SpawnRadius = D.SpawnRadius;
    }

    private static void Build(ShipStatus ship)
    {
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} BEGIN BUILD over '{ship.name}' (MapScale={ship.MapScale:F3})");
        ApplySpawn(ship);

        // 1. Alles einsammeln, was ueberleben muss - VOR dem Wipe, solange die Raum-Eltern
        //    noch existieren (Konsolen-Bild gehoert oft dem Eltern-Sprite, siehe Marker).
        var keep = new List<Transform>();
        // Vents tragen selbst eine Console-Komponente (Log 22.09.: "AdminVent/0" ohne Slot).
        // Sie laufen ausschliesslich ueber den Vent-Pfad, sonst ueberleben auch die unbenutzten.
        var consoles = ship.GetComponentsInChildren<Console>(true)
            .Where(c => c.GetComponent<Vent>() == null).ToArray();
        var systemConsoles = ship.GetComponentsInChildren<SystemConsole>(true).ToArray();
        var mapConsoles = ship.GetComponentsInChildren<MapConsole>(true).ToArray();
        var vents = ship.GetComponentsInChildren<Vent>(true).ToArray();
        var doors = ship.GetComponentsInChildren<OpenableDoor>(true).ToArray();
        var cameras = ship.GetComponentsInChildren<SurvCamera>(true).ToArray();

        var needsMarker = new HashSet<IntPtr>();
        foreach (var c in consoles) { keep.Add(c.transform); if (!OwnsImage(c.Image, c.transform)) needsMarker.Add(c.Pointer); }
        foreach (var c in systemConsoles) { keep.Add(c.transform); if (!OwnsImage(c.Image, c.transform)) needsMarker.Add(c.Pointer); }
        foreach (var c in mapConsoles) { keep.Add(c.transform); if (!OwnsImage(c.Image, c.transform)) needsMarker.Add(c.Pointer); }
        foreach (var v in vents) if (D.Vents.ContainsKey(v.Id)) keep.Add(v.transform);
        foreach (var d in doors) keep.Add(d.transform);
        foreach (var c in cameras) keep.Add(c.transform);
        if (ship.DummyLocations != null) foreach (var t in ship.DummyLocations) if (t != null) keep.Add(t);

        // Sicht: Among Us wirft Schatten nicht auf die Welt, sondern blendet Sprites mit dem
        // Material "MaskingShader" dort aus, wo das Licht nicht hinkommt (Vergleich Skeld/Museum
        // 22.09.: alle Skeld-Boeden tragen es, unsere Kacheln trugen Sprites-Default und blieben
        // hinter jeder Wand sichtbar). Das Material VOR dem Wipe von einem Skeld-Boden holen.
        _maskingMaterial = null;
        foreach (var r in ship.GetComponentsInChildren<SpriteRenderer>(true))
        {
            var m = r != null ? r.sharedMaterial : null;
            if (m != null && m.name.StartsWith("MaskingShader", StringComparison.Ordinal)) { _maskingMaterial = m; break; }
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} masking material: {(_maskingMaterial != null ? _maskingMaterial.name : "NOT FOUND - walls will not block sight")}");
        _defaultSpriteMaterial = null;
        foreach (var r in ship.GetComponentsInChildren<SpriteRenderer>(true))
        {
            var m = r != null ? r.sharedMaterial : null;
            if (m != null && m.name.StartsWith("Sprites-Default", StringComparison.Ordinal)) { _defaultSpriteMaterial = m; break; }
        }

        // Material mit Outline-Shader von einer Konsole, die ihr Bild selbst traegt.
        Material outlineMat = null;
        foreach (var c in consoles)
            if (!needsMarker.Contains(c.Pointer) && c.Image != null) { outlineMat = c.Image.sharedMaterial; break; }

        // Schluessel VOR dem Umhaengen bilden (Name/Raum/Id aendern sich nicht, aber sicher ist sicher).
        var consoleKeys = new Dictionary<IntPtr, string>();
        foreach (var c in consoles) consoleKeys[c.Pointer] = $"{c.Room}/{c.name}/{c.ConsoleId}";

        // Referenzierte Effekt-Objekte (Waffen-Animation, Schilde, Luke) behalten, aber parken:
        // ShipStatus.FireWeapon/StartShields/OpenHatch greifen auf sie zu.
        var parked = new List<Transform>();
        void Park(Component c) { if (c != null) parked.Add(c.transform); }
        Park(ship.WeaponsImage);
        if (ship.ShieldsImages != null) foreach (var s in ship.ShieldsImages) Park(s);
        Park(ship.ShieldBorder);
        Park(ship.Hatch);
        Park(ship.HatchParticles);
        Park(ship.MedScanner);

        // 2. Umhaengen an den Ship-Root (Weltlage bleibt). Nur oberste Ebene: steckt ein
        //    Behalte-Objekt in einem anderen, wandert es mit seinem Elternteil.
        // Il2Cpp-Wrapper sind keine stabilen Schluessel (t.parent liefert einen neuen Wrapper):
        // verglichen wird ueber den nativen Pointer.
        var candidates = keep.Concat(parked).Where(t => t != null)
            .GroupBy(t => t.Pointer).Select(g => g.First()).ToList();
        var all = new HashSet<IntPtr>(candidates.Select(t => t.Pointer));
        var roots = candidates.Where(t => !HasAncestorIn(t, all, ship.transform)).ToList();
        foreach (var t in roots) t.SetParent(ship.transform, true);

        // 3. Wipe: alle Kinder des Ship-Roots ausser den geretteten.
        var rootSet = new HashSet<IntPtr>(roots.Select(t => t.Pointer));
        int wiped = 0;
        for (int i = ship.transform.childCount - 1; i >= 0; i--)
        {
            var child = ship.transform.GetChild(i);
            if (rootSet.Contains(child.Pointer)) continue;
            Object.DestroyImmediate(child.gameObject);
            wiped++;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} kept {roots.Count} root object(s), wiped {wiped}");

        // 4. Geometrie-Wurzel in Weltmetern (Ship-Root ist 1,2-fach skaliert und liegt bei z 8).
        var world = new GameObject("Atlas_Museum");
        world.transform.SetParent(ship.transform, false);
        var ls = ship.transform.lossyScale;
        world.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f / ls.z);
        world.transform.position = Vector3.zero;

        BuildFloor(world);
        int walls = BuildWalls(world);
        int props = BuildProps(world);
        int lit = UnmaskOccluders();
        BuildRooms(ship, world);

        // 5. Umsetzen.
        int placed = 0, unplaced = 0;
        foreach (var c in consoles)
        {
            if (c == null) continue;
            var key = consoleKeys[c.Pointer];
            if (!D.Consoles.TryGetValue(key, out var pos))
            {
                AtlasPlugin.Logger.LogWarning($"{LogPrefix} console without museum slot: {key} - parked");
                MoveTo(c.transform, new Vector2(0f, -300f));
                unplaced++;
                continue;
            }
            MoveTo(c.transform, pos);
            SortLikePlayer(c.transform);
            c.checkWalls = false;
            c.onlySameRoom = false;
            c.onlyFromBelow = false;
            // Winzige Skeld-Bilder (A2 = Reactor/LowerHandConsole: 0,34 x 0,06 m) sind im Museum
            // nicht auffindbar - auch sie bekommen den Graybox-Kasten.
            bool tiny = ForceMarker.Contains(key) ||
                        (c.Image != null && c.Image.bounds.size.x * c.Image.bounds.size.y < 0.05f);
            if (needsMarker.Contains(c.Pointer) || tiny)
            {
                if (tiny && c.Image != null) c.Image.enabled = false;
                c.Image = AddMarker(c.gameObject, outlineMat, key);
                AtlasPlugin.Logger.LogInfo($"{LogPrefix} console marker for {key}{(tiny ? " (tiny skeld image)" : "")}");
            }
            c.Image = ApplyBlock(c.gameObject, key, c.Image, outlineMat);
            placed++;
        }

        foreach (var sc in systemConsoles)
        {
            if (sc == null) continue;
            Vector2 pos;
            string role;
            if (sc == ship.EmergencyButton) { pos = D.EmergencyButton; role = "emergency"; }
            else if (sc.FreeplayOnly) { pos = D.FreeplayLaptop; role = "freeplay"; }
            else { pos = D.SurveillanceConsole; role = "surveillance"; }
            MoveTo(sc.transform, pos);
            SortLikePlayer(sc.transform);
            sc.onlyFromBelow = false;
            if (needsMarker.Contains(sc.Pointer)) sc.Image = AddMarker(sc.gameObject, outlineMat, role);
            sc.Image = ApplyBlock(sc.gameObject, role switch
            {
                "emergency" => "EmergencyButton",
                "freeplay" => "FreeplayLaptop",
                _ => "SurveillanceConsole",
            }, sc.Image, outlineMat);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} system console '{sc.name}' -> {role} ({pos.x:F1},{pos.y:F1})");
        }

        foreach (var mc in mapConsoles)
        {
            if (mc == null) continue;
            MoveTo(mc.transform, D.AdminTable);
            SortLikePlayer(mc.transform);
            if (needsMarker.Contains(mc.Pointer)) mc.Image = AddMarker(mc.gameObject, outlineMat, "admin");
            mc.Image = ApplyBlock(mc.gameObject, "AdminTable", mc.Image, outlineMat);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} map console '{mc.name}' -> admin table");
        }

        foreach (var t in parked)
        {
            if (t == null || t == (ship.MedScanner != null ? ship.MedScanner.transform : null)) continue;
            MoveTo(t, new Vector2(0f, -300f));
            // Unsichtbar schalten: sichtbar geparkt zogen sie den Rahmen jeder Gesamtaufnahme
            // (Survey-Foto 22.09.) bis y -308 auf und drueckten das Museum auf ~12 px/m.
            foreach (var r in t.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
        }

        int ventCount = PlaceVents(ship, vents);
        int doorCount = PlaceDoors(doors);
        int camCount = PlaceCameras(ship, cameras);

        if (ship.DummyLocations != null)
        {
            int n = ship.DummyLocations.Length;
            for (int i = 0; i < n; i++)
            {
                var t = ship.DummyLocations[i];
                if (t == null) continue;
                float a = Mathf.PI * 2f * i / Mathf.Max(1, n);
                MoveTo(t, D.Spawn + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * 3.6f);
            }
        }

        // Arrays auf Ueberlebende eindampfen (entfernte Vents, evtl. verlorene Konsolen).
        ship.AllConsoles = new Il2CppReferenceArray<Console>(ship.AllConsoles.Where(c => c != null).ToArray());
        ship.AllCameras = new Il2CppReferenceArray<SurvCamera>(ship.AllCameras.Where(c => c != null).ToArray());

        ship.CameraColor = D.CameraColor;

        try { AtlasWorld.OnBuilt(ship); } catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} world: {e}"); }
        RebuildMinimap(ship);
        Physics2D.SyncTransforms();

        AtlasPlugin.Logger.LogInfo(
            $"{LogPrefix} BUILD DONE: consoles {placed} placed/{unplaced} parked, vents {ventCount}, " +
            $"doors {doorCount}, cameras {camCount}, wall rings {walls}, props {props}, rooms {ship.AllRooms.Length}");
    }

    // ------------------------------------------------------------------ Helfer

    private static bool OwnsImage(SpriteRenderer image, Transform owner) =>
        image != null && image.transform.IsChildOf(owner);

    private static bool HasAncestorIn(Transform t, HashSet<IntPtr> set, Transform stop)
    {
        for (var p = t.parent; p != null && p != stop; p = p.parent)
            if (set.Contains(p.Pointer)) return true;
        return false;
    }

    /// <summary>Setzt die Welt-xy, behaelt z (die Skeld-Tiefenstaffel stimmt so weiter).</summary>
    private static void MoveTo(Transform t, Vector2 pos)
    {
        var p = t.position;
        t.position = new Vector3(pos.x, pos.y, p.z);
    }

    private static Dictionary<string, (int Atlas, int X, int Y, int W, int H, float PX, float PY)> _blocks;

    /// <summary>
    /// Eigener Task-Block (tools/museum_consoles.py) statt des Skeld-Bilds. Alle alten Renderer der
    /// Konsole werden abgeschaltet, der neue bekommt das Kontur-Material des alten Bilds, damit das
    /// gelbe Hervorheben beim Naehertreten weiter funktioniert. Ohne Eintrag bleibt alles wie es war.
    /// </summary>
    private static SpriteRenderer ApplyBlock(GameObject owner, string key, SpriteRenderer current, Material outlineMat)
    {
        if (_blocks == null)
        {
            _blocks = new();
            foreach (var b in D.ConsoleSprites) _blocks[b.Key] = (b.Atlas, b.X, b.Y, b.W, b.H, b.PivotX, b.PivotY);
        }
        if (!_blocks.TryGetValue(key, out var e)) return current;
        var tex = AtlasAssets.MapConsolesTexture(D, e.Atlas);
        if (tex == null) return current;

        var mat = current != null && current.sharedMaterial != null ? current.sharedMaterial : outlineMat;
        foreach (var r in owner.GetComponentsInChildren<SpriteRenderer>(true)) r.enabled = false;

        var sprite = Sprite.Create(tex, new Rect(e.X, e.Y, e.W, e.H), new Vector2(e.PX, e.PY),
            D.PropPixelsPerMeter, 0, SpriteMeshType.FullRect);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var go = new GameObject("Atlas_Block") { layer = LayerShortObjects };
        go.transform.SetParent(owner.transform, false);
        var ls = owner.transform.lossyScale;
        go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f);
        var p = owner.transform.position;
        // Bodenbloecke (Scanner-Ring) liegen UNTER dem Spieler, der darauf steht. Nach Standlinie
        // sortiert kippte die Reihenfolge beim Drueberlaufen hin und her (Test 22.09.: Flackern,
        // Spieler steckte im Ring).
        // An Wand/Theke stehende Bloecke (Test 23.09.: der Spieler verschwand hinter der Kasse):
        // Standlinie = Kante des Hindernisses direkt noerdlich, dann steht jeder Spieler davor.
        float z = FloorBlocks.Contains(key) ? FloorZ - 1f : SortZ(BackedStandLine(p)) - 0.0002f;
        go.transform.position = new Vector3(p.x, p.y, z);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        if (mat != null) sr.sharedMaterial = mat;
        return sr;
    }

    // Eigene Vent-Bilder (Key "Vent/<id>" im Konsolen-Atlas). Das Bild sitzt auf einem EIGENEN
    // Kind-Renderer, der Skeld-Renderer (myRend) wird unsichtbar: EnterVent/ExitVent spielen die
    // Skeld-Klappenanimation und setzen dabei das Skeld-Bild, und zwar NACH HudManager.Update, so
    // dass ein Zuruecksetzen dort beim Venten nicht griff (User 23.09.: "Vent geht zurueck zum
    // Original"). Der Kind-Renderer teilt die Material-Instanz von myRend, damit die rote/gelbe
    // Kontur (Vent.SetOutline schreibt in myRend.material) weiter sichtbar ist.
    private static readonly List<(SpriteRenderer Orig, SpriteRenderer Art, Sprite S)> VentArt = new();

    private static void ApplyVentArt(Vent v)
    {
        if (_blocks == null)
        {
            _blocks = new();
            foreach (var b in D.ConsoleSprites) _blocks[b.Key] = (b.Atlas, b.X, b.Y, b.W, b.H, b.PivotX, b.PivotY);
        }
        if (!_blocks.TryGetValue($"Vent/{v.Id}", out var e)) return;
        // Das Bild sitzt am Vent-Feld myRend (nicht zwingend am selben GameObject).
        SpriteRenderer sr = null;
        try { sr = v.myRend; } catch { }
        if (sr == null) sr = v.GetComponentInChildren<SpriteRenderer>(true);
        var tex = AtlasAssets.MapConsolesTexture(D, e.Atlas);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} vent art {v.Id}: renderer '{(sr != null ? sr.name : "none")}', tex {(tex != null)}");
        if (sr == null || tex == null) return;
        var ls = v.transform.lossyScale;
        var sprite = Sprite.Create(tex, new Rect(e.X, e.Y, e.W, e.H), new Vector2(e.PX, e.PY),
            D.PropPixelsPerMeter * Mathf.Abs(ls.x), 0, SpriteMeshType.FullRect);
        sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var go = new GameObject("AtlasVentArt") { layer = sr.gameObject.layer };
        go.transform.SetParent(sr.transform, false);
        var art = go.AddComponent<SpriteRenderer>();
        art.sprite = sprite;
        art.sortingLayerID = sr.sortingLayerID;
        art.sortingOrder = sr.sortingOrder;
        art.color = sr.color;
        art.sharedMaterial = sr.material;                 // Instanz von myRend: Kontur greift mit
        sr.enabled = false;
        // Die Idle-Animation muss nicht mehr laufen; Ein-/Aussteigen spielt sie trotzdem (unsichtbar).
        try { var anim = v.myAnim; if (anim != null) anim.enabled = false; } catch { }
        foreach (var an in v.GetComponentsInChildren<Animator>(true)) an.enabled = false;
        VentArt.Add((sr, art, sprite));
    }

    private static Sprite _markerSprite;

    private static readonly HashSet<string> FloorBlocks = new() { "MedBay/MedScanner/0" };

    /// <summary>
    /// Standlinie eines Blocks: seine eigene y, ausser direkt noerdlich (bis 0,9 m) liegt eine Wand
    /// oder ein Hindernis (Theke, Regal) - dann dessen Kante. Hinter diese Kante kommt kein Spieler,
    /// der Block liegt also immer hinter jedem, der davor steht.
    /// </summary>
    private static float BackedStandLine(Vector2 p)
    {
        float best = float.MaxValue;
        void Scan(Vector2[][] polys)
        {
            if (polys == null) return;
            foreach (var poly in polys)
                for (int i = 0; i < poly.Length; i++)
                {
                    var a = poly[i]; var b = poly[(i + 1) % poly.Length];
                    if ((a.x - p.x) * (b.x - p.x) > 0f || Mathf.Abs(b.x - a.x) < 1e-4f) continue;
                    float y = a.y + (b.y - a.y) * (p.x - a.x) / (b.x - a.x);
                    if (y > p.y && y - p.y < 0.9f && y < best) best = y;
                }
        }
        Scan(D.Walls); Scan(D.Opaque); Scan(D.Glass);
        return best < float.MaxValue ? best + 0.05f : p.y;
    }

    /// <summary>Konsolen, deren Skeld-Bild im Museum nicht lesbar ist (A2: Kabelstrang 0,34 x 0,06 m).</summary>
    private static readonly HashSet<string> ForceMarker = new() { "Reactor/LowerHandConsole/1" };

    /// <summary>
    /// Graybox-Konsole fuer Konsolen, deren Bild der (jetzt geloeschten) Raumkulisse gehoerte,
    /// z.B. Reaktor-Handflaechen oder Motor-Konsolen. Bekommt das Outline-Material einer echten
    /// Konsole, damit das gelbe Hervorheben beim Naehertreten funktioniert.
    /// </summary>
    private static SpriteRenderer AddMarker(GameObject owner, Material mat, string label)
    {
        _markerSprite ??= AtlasAssets.ConsoleMarkerSprite();
        var go = new GameObject("Atlas_ConsoleMarker") { layer = LayerShortObjects };
        go.transform.SetParent(owner.transform, false);
        var ls = owner.transform.lossyScale;
        go.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f);
        go.transform.localPosition = new Vector3(0f, 0f, 0.001f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = _markerSprite;
        if (mat != null) sr.sharedMaterial = mat;
        return sr;
    }

    // ---------------------------------------------------------- Tiefensortierung

    // Spieler bekommen z = transform.y / 1000, ihre Fuesse (GetTruePosition) liegen aber tiefer.
    // Ein Objekt mit Standlinie b steht vor einem Spieler genau dann, wenn dessen Fuesse ueber b
    // liegen, also transform.y > b + Fussversatz. Daher z = (b + Fussversatz) / 1000.
    private const float FallbackFeetOffset = 0.3636f;
    private static float _feetOffset = float.NaN;

    private static float FeetOffset()
    {
        if (!float.IsNaN(_feetOffset)) return _feetOffset;
        var pc = PlayerControl.LocalPlayer;
        if (pc == null) return FallbackFeetOffset;
        try
        {
            _feetOffset = pc.transform.position.y - pc.GetTruePosition().y;
            if (_feetOffset < 0f || _feetOffset > 1f) _feetOffset = FallbackFeetOffset;
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} player feet offset {_feetOffset:F3}");
        }
        catch { return FallbackFeetOffset; }
        return _feetOffset;
    }

    private static float SortZ(float baseY) => (baseY + FeetOffset()) / 1000f;

    /// <summary>Konsole wie ein Objekt mit Standlinie an ihrer Position einsortieren (statt der
    /// Skeld-Tiefe ~6,8, die sie hinter jedes Museumsmoebel legen wuerde).</summary>
    private static void SortLikePlayer(Transform t)
    {
        var p = t.position;
        t.position = new Vector3(p.x, p.y, SortZ(p.y) - 0.0001f);
    }

    /// <summary>Moebel, Vitrinen, Exponate: je ein Sprite aus dem Objektatlas, Pivot links unten.</summary>
    private static int BuildProps(GameObject world)
    {
        FadeProps.Clear();
        PropRenderers.Clear();
        var root = Child(world, "Atlas_Props", LayerShortObjects);
        int n = 0;
        foreach (var p in D.Props)
        {
            var tex = AtlasAssets.MapPropsTexture(D, p.Atlas);
            if (tex == null) continue;
            var sprite = Sprite.Create(tex, new Rect(p.X, p.Y, p.W, p.H), Vector2.zero, D.PropPixelsPerMeter);
            sprite.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
            var go = Child(root, $"Prop_{p.Kind}_{n}", LayerShortObjects);
            go.transform.position = new Vector3(p.WorldX, p.WorldY, SortZ(p.BaseY));
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            Mask(sr);
            PropRenderers.Add(sr);
            float top = p.WorldY + p.H / D.PropPixelsPerMeter;
            // Das Skelett ist das Schaustueck der Rotunde: nie ausblenden (User 22.09.).
            if (top - p.BaseY > FadeMinHeight && !D.NoFadeKinds.Contains(p.Kind))
                FadeProps.Add(new FadeProp(sr, p.FootX0, p.FootX1, p.BaseY, top));
            n++;
        }
        return n;
    }

    /// <summary>
    /// Blickdichte Moebel verschatteten ihr eigenes Sprite (Test 22.09.: Garderobe und Hochregale
    /// halb dunkel), weil das Sprite hinter der eigenen Schattenkante liegt. NoShadowBehaviour hat im
    /// Test nichts bewirkt. Loesung wie die Skeld-Waende: diese Sprites bekommen das normale
    /// Sprite-Material und werden vom Sichtsystem nie ausgeblendet; Spieler dahinter bleiben
    /// trotzdem unsichtbar, weil nur die Spieler maskiert werden. Props-Reihenfolge = OPAQUE-
    /// Reihenfolge (gen_museum: erst alle OPAQUE, dann GLASS, dann Deko), Index j = Hindernis j.
    /// </summary>
    private static int UnmaskOccluders()
    {
        if (_defaultSpriteMaterial == null) return 0;
        // Gleiche Render-Queue wie die maskierten Sprites und Spieler, sonst sortiert Unity nach
        // Queue statt nach Tiefe (Test 22.09.: Hochregal lag VOR dem Spieler in der Gasse).
        var unmasked = new Material(_defaultSpriteMaterial) { name = "Atlas_UnmaskedProp" };
        int queue = _maskingMaterial != null ? _maskingMaterial.renderQueue : _defaultSpriteMaterial.renderQueue;
        var lp = PlayerControl.LocalPlayer;
        var playerRend = lp != null && lp.cosmetics != null && lp.cosmetics.currentBodySprite != null ? lp.cosmetics.currentBodySprite.BodySprite : null;
        if (playerRend != null && playerRend.sharedMaterial != null) queue = playerRend.sharedMaterial.renderQueue;
        unmasked.renderQueue = queue;
        AtlasPlugin.Logger.LogInfo(
            $"{LogPrefix} render queues: masking={(_maskingMaterial != null ? _maskingMaterial.renderQueue : -1)} " +
            $"default={_defaultSpriteMaterial.renderQueue} player={(playerRend != null && playerRend.sharedMaterial != null ? playerRend.sharedMaterial.renderQueue : -1)} -> {queue}");
        int n = 0;
        int count = Math.Min(OpaqueShadowObjects.Count, PropRenderers.Count);
        for (int j = 0; j < count; j++)
        {
            if (PropRenderers[j] == null || OpaqueShadowObjects[j] == null) continue;
            PropRenderers[j].sharedMaterial = unmasked;
            n++;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} occluder sprites unmasked: {n}/{OpaqueShadowObjects.Count} (Rest steht an Waenden, ohne Schatten)");
        return n;
    }

    // ------------------------------------------------------ Durchsicht-Blende

    // Wunsch aus dem Test 22.09.: Hochregal und Oldtimer verschlucken den eigenen Spieler ganz.
    // Steht der LOKALE Spieler mit den Fuessen hinter einem hohen Objekt (innerhalb seines
    // Sprites, noerdlich der Standlinie), blendet es weich auf FadeAlpha. Andere Spieler bleiben
    // verdeckt - Verstecken hinter Moebeln ist Spielmechanik, nur man selbst soll sich sehen.
    private const float FadeMinHeight = 0.9f;
    private const float FadeAlpha = 0.4f;

    private sealed class FadeProp
    {
        public readonly SpriteRenderer R;
        public readonly float X0, X1, Base, Top;
        public float Alpha = 1f;
        public FadeProp(SpriteRenderer r, float x0, float x1, float b, float t) { R = r; X0 = x0; X1 = x1; Base = b; Top = t; }
    }

    private static readonly List<FadeProp> FadeProps = new();
    private static readonly List<GameObject> OpaqueShadowObjects = new();
    private static readonly List<SpriteRenderer> PropRenderers = new();

    [HarmonyPostfix]
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static void HudManager_Update_FadePostfix()
    {
        if (!Active) return;
        for (int i = 0; i < VentArt.Count; i++)
        {
            var (orig, art, sp) = VentArt[i];
            if (orig != null && orig.enabled) orig.enabled = false;
            if (art != null && art.sprite != sp) art.sprite = sp;
        }
        if (FadeProps.Count == 0) return;
        var lp = PlayerControl.LocalPlayer;
        if (lp == null) return;
        Vector2 feet;
        try { feet = lp.GetTruePosition(); } catch { return; }
        float step = Mathf.Clamp01(Time.deltaTime * 8f);
        for (int i = 0; i < FadeProps.Count; i++)
        {
            var f = FadeProps[i];
            if (f.R == null) continue;
            // Fuesse ueber der Grundflaeche (nicht dem Sprite mit Schattenrand) und klar hinter der
            // Standlinie. Test 22.09.: neben einer Vitrine zu stehen blendete sie schon aus.
            bool behind = feet.x > f.X0 && feet.x < f.X1 && feet.y > f.Base + 0.1f && feet.y < f.Top - 0.15f;
            float target = behind ? FadeAlpha : 1f;
            if (Mathf.Approximately(f.Alpha, target)) continue;
            f.Alpha = Mathf.MoveTowards(f.Alpha, target, step);
            var c = f.R.color;
            f.R.color = new Color(c.r, c.g, c.b, f.Alpha);
        }
    }

    // --------------------------------------------------------------- Geometrie

    /// <summary>Boden aus Kacheln (160 px/m). Kanten ueberlappen nicht; Clamp verhindert Naehte.</summary>
    private static void BuildFloor(GameObject world)
    {
        var root = new GameObject("Atlas_Floor") { layer = LayerShip };
        root.transform.SetParent(world.transform, false);
        int n = 0;
        foreach (var t in D.FloorTiles)
        {
            var sprite = AtlasAssets.MapFloorTile(D, t.Index);
            if (sprite == null) continue;
            var go = new GameObject($"Tile_{t.Index}") { layer = LayerShip };
            go.transform.SetParent(root.transform, false);
            go.transform.localPosition = new Vector3(t.WorldX, t.WorldY, FloorZ);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sortingOrder = -1000;
            Mask(sr);
            n++;
        }
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} floor: {n}/{D.FloorTiles.Length} tiles");
    }

    private static GameObject Child(GameObject parent, string name, int layer)
    {
        var go = new GameObject(name) { layer = layer };
        go.transform.SetParent(parent.transform, false);
        return go;
    }

    private static Vector2[] Closed(Vector2[] ring)
    {
        var closed = new Vector2[ring.Length + 1];
        Array.Copy(ring, closed, ring.Length);
        closed[ring.Length] = ring[0];
        return closed;
    }

    /// <summary>
    /// Waende wie die Skeld: je Kette ein EdgeCollider auf Ship (Bewegung) und ein zweiter auf
    /// Shadow (Sichtkegel). Blickdichte Moebel genauso, Glas nur auf ShortObjects.
    /// </summary>
    private static int BuildWalls(GameObject world)
    {
        // Tiefe wie die Skeld-Waende (Schiffs-Root z 8): der GPU-Lichtrenderer baut aus den Kanten
        // ein 3D-Verdeckungsnetz, und bei z 0 schnitt die Schattenkamera es weg - die Umkreissuche
        // fand die Kanten, aber nichts warf Schatten (Test 22.09., view shot + vision log).
        var walls = Child(world, "Atlas_Walls", LayerShip);
        walls.transform.localPosition = new Vector3(0f, 0f, ColliderZ);
        int i = 0;
        foreach (var ring in D.Walls)
        {
            Child(walls, $"Wall_{i}", LayerShip).AddComponent<EdgeCollider2D>().points = Closed(ring);
            i++;
        }
        int k0 = 0;
        foreach (var ring in D.ShadowWalls)
        {
            Child(walls, $"WallShadow_{k0}", LayerShadow).AddComponent<EdgeCollider2D>().points = Closed(ring);
            k0++;
        }

        OpaqueShadowObjects.Clear();
        var opaque = Child(world, "Atlas_Opaque", LayerShip);
        opaque.transform.localPosition = new Vector3(0f, 0f, ColliderZ);
        int j = 0;
        foreach (var poly in D.Opaque)
        {
            var pts = Closed(poly);
            Child(opaque, $"Opaque_{j}", LayerShip).AddComponent<EdgeCollider2D>().points = pts;
            bool casts = j >= D.OpaqueCastsShadow.Length || D.OpaqueCastsShadow[j];
            GameObject shadowGo = null;
            if (casts)
            {
                shadowGo = Child(opaque, $"OpaqueShadow_{j}", LayerShadow);
                shadowGo.AddComponent<EdgeCollider2D>().points = pts;
            }
            OpaqueShadowObjects.Add(shadowGo);
            j++;
        }

        var glass = Child(world, "Atlas_Glass", LayerShortObjects);
        glass.transform.localPosition = new Vector3(0f, 0f, ColliderZ);
        int k = 0;
        foreach (var poly in D.Glass)
        {
            var col = Child(glass, $"Glass_{k}", LayerShortObjects).AddComponent<PolygonCollider2D>();
            col.points = poly;
            k++;
        }

        AtlasPlugin.Logger.LogInfo($"{LogPrefix} walls: {i} ring(s), {j} opaque, {k} glass");
        return i;
    }

    /// <summary>
    /// PlainShipRoom je Museumsraum (Raumanzeige unten links, Admin-Zaehlung, onlySameRoom)
    /// plus Hallway-Raeume fuer die Gaenge. FastRooms kennt jede SystemTypes nur einmal.
    /// </summary>
    private static void BuildRooms(ShipStatus ship, GameObject world)
    {
        var root = Child(world, "Atlas_Rooms", LayerIgnoreRaycast);
        var all = new List<PlainShipRoom>();
        var fast = new Il2CppSystem.Collections.Generic.Dictionary<SystemTypes, PlainShipRoom>();

        PlainShipRoom Make(string name, SystemTypes type, Vector2[] area)
        {
            // Raum-Transform auf die Flaechenmitte: das Kamera-Minispiel setzt seine Kameras auf
            // room.transform.position + survCamera.Offset (Test 22.09.: mit Transform bei 0,0
            // zeigten alle vier Bilder das Foyer).
            Vector2 c = Vector2.zero;
            foreach (var q in area) c += q;
            c /= area.Length;
            var go = Child(root, name, LayerIgnoreRaycast);
            go.transform.localPosition = new Vector3(c.x, c.y, 0f);
            var rel = new Vector2[area.Length];
            for (int i = 0; i < area.Length; i++) rel[i] = area[i] - c;
            var col = go.AddComponent<PolygonCollider2D>();
            col.isTrigger = true;
            col.points = rel;
            var room = go.AddComponent<PlainShipRoom>();
            room.RoomId = type;
            room.roomArea = col;
            return room;
        }

        foreach (var r in D.Rooms)
        {
            var room = Make($"Room_{r.Key}", r.Room, r.Area);
            all.Add(room);
            if (!fast.ContainsKey(r.Room)) fast.Add(r.Room, room);
        }
        for (int i = 0; i < D.Hallways.Length; i++)
            all.Add(Make($"Hallway_{i}", SystemTypes.Hallway, D.Hallways[i]));

        ship.AllRooms = new Il2CppReferenceArray<PlainShipRoom>(all.ToArray());
        ship.FastRooms = fast;
    }

    // ---------------------------------------------------- Vents, Tueren, Kameras

    private static int PlaceVents(ShipStatus ship, Vent[] vents)
    {
        var byId = new Dictionary<int, Vent>();
        foreach (var v in vents)
        {
            if (v == null || !D.Vents.TryGetValue(v.Id, out var pos)) continue;
            MoveTo(v.transform, pos);
            ApplyVentArt(v);
            byId[v.Id] = v;
        }

        foreach (var net in D.VentNetworks)
        {
            for (int i = 0; i < net.Length; i++)
            {
                if (!byId.TryGetValue(net[i], out var v)) continue;
                byId.TryGetValue(net[(i + 1) % net.Length], out var right);
                byId.TryGetValue(net[(i + net.Length - 1) % net.Length], out var left);
                v.Left = left;
                v.Right = right;
                v.Center = null;
            }
        }

        // AllVents: alles, was noch lebt (auch Vents, die andere Mods schon angemeldet haben).
        ship.AllVents = new Il2CppReferenceArray<Vent>(ship.AllVents.Where(v => v != null).ToArray());
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} vents: {byId.Count} placed, AllVents={ship.AllVents.Length}");
        return byId.Count;
    }

    /// <summary>
    /// Verteilt die 13 Skeld-Tueren nach Ausrichtung auf die 13 Gitteroeffnungen, streckt sie
    /// auf die Oeffnungsbreite und setzt die Tuergruppe um. Rollgitter lassen die Sicht durch:
    /// ihr Schatten-Kollider wird abgeschaltet (Door.SetDoorway schaltet nur .enabled, ein
    /// inaktives GameObject bleibt davon unberuehrt).
    /// </summary>
    private static int PlaceDoors(OpenableDoor[] doors)
    {
        var vertical = new List<OpenableDoor>();
        var horizontal = new List<OpenableDoor>();
        foreach (var d in doors)
        {
            if (d == null) continue;
            var box = DoorCollider(d);
            if (box == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} door '{d.name}' has no collider - skipped"); continue; }
            var size = box.bounds.size;
            (size.y > size.x ? vertical : horizontal).Add(d);
        }
        // Stabil nach Id, damit jeder Client dieselbe Tuer an dieselbe Oeffnung setzt.
        vertical.Sort((a, b) => a.Id.CompareTo(b.Id));
        horizontal.Sort((a, b) => a.Id.CompareTo(b.Id));

        int placed = Assign(vertical, D.VerticalDoors, true);
        placed += Assign(horizontal, D.HorizontalDoors, false);

        if (vertical.Count != D.VerticalDoors.Length ||
            horizontal.Count != D.HorizontalDoors.Length)
            AtlasPlugin.Logger.LogWarning(
                $"{LogPrefix} door count mismatch: skeld {vertical.Count}V/{horizontal.Count}H, " +
                $"museum {D.VerticalDoors.Length}V/{D.HorizontalDoors.Length}H");
        return placed;
    }

    private static BoxCollider2D DoorCollider(OpenableDoor d)
    {
        var plain = d.TryCast<PlainDoor>();
        if (plain != null && plain.myCollider != null) return plain.myCollider;
        return d.GetComponent<BoxCollider2D>();
    }

    private static int Assign(List<OpenableDoor> doors, AtlasMuseumLayout.DoorSlot[] slots, bool vertical)
    {
        int n = Math.Min(doors.Count, slots.Length);
        for (int i = 0; i < n; i++)
        {
            var d = doors[i];
            var slot = slots[i];
            var t = d.transform;

            MoveTo(t, slot.Center);
            Physics2D.SyncTransforms();
            var box = DoorCollider(d);
            var size = box.bounds.size;
            float current = vertical ? size.y : size.x;
            if (current > 0.01f)
            {
                float f = (slot.Length + 0.1f) / current;
                var s = t.localScale;
                t.localScale = vertical ? new Vector3(s.x, s.y * f, s.z) : new Vector3(s.x * f, s.y, s.z);
            }
            // Kollidermitte auf die Oeffnungsmitte ziehen (Pivot sitzt nicht immer mittig).
            Physics2D.SyncTransforms();
            var c = (Vector2)box.bounds.center;
            var p = t.position;
            t.position = new Vector3(p.x + slot.Center.x - c.x, p.y + slot.Center.y - c.y, p.z);

            d.Room = slot.Group;

            var plain = d.TryCast<PlainDoor>();
            if (slot.SeeThrough && plain != null && plain.shadowCollider != null &&
                plain.shadowCollider.gameObject != d.gameObject)
                plain.shadowCollider.gameObject.SetActive(false);

            AtlasPlugin.Logger.LogInfo(
                $"{LogPrefix} door #{d.Id} '{d.name}' -> {slot.Label} ({slot.Group}, " +
                $"{(slot.SeeThrough ? "gitter" : "blickdicht")})");
        }
        return n;
    }

    private static int PlaceCameras(ShipStatus ship, SurvCamera[] cameras)
    {
        Physics2D.SyncTransforms();   // Raum-Kollider wurden eben erst angelegt/verschoben
        // Reihenfolge von AllCameras = Reihenfolge im Kamera-Minispiel.
        var order = ship.AllCameras != null ? ship.AllCameras.ToArray() : cameras;
        int n = 0;
        foreach (var cam in order)
        {
            if (cam == null || n >= D.Cameras.Length) continue;
            var pos = D.Cameras[n];
            MoveTo(cam.transform, pos);
            LinkCameraRoom(ship, cam, pos);
            n++;
        }
        return n;
    }

    /// <summary>
    /// Das Kamera-Minispiel sucht seine Bilder NICHT in AllCameras, sondern in den Raeumen
    /// (SurveillanceMinigame.FilteredRooms = AllRooms mit gesetztem survCamera). Unsere Raeume
    /// hatten keine - im Test 22.09. zeigten alle vier Bilder nur Rauschen. Zusaetzlich zielt
    /// die Kamera ueber Offset auf die Raummitte statt auf den alten Skeld-Blickpunkt.
    /// </summary>
    private static void LinkCameraRoom(ShipStatus ship, SurvCamera cam, Vector2 pos)
    {
        PlainShipRoom best = null;
        foreach (var r in ship.AllRooms)
        {
            if (r == null || r.roomArea == null || r.RoomId == SystemTypes.Hallway || r.survCamera != null) continue;
            if (r.roomArea.OverlapPoint(pos)) { best = r; break; }
        }
        if (best == null)
        {
            float bestD = float.MaxValue;
            foreach (var r in ship.AllRooms)
            {
                if (r == null || r.roomArea == null || r.RoomId == SystemTypes.Hallway || r.survCamera != null) continue;
                float d = Vector2.Distance(r.roomArea.bounds.center, pos);
                if (d < bestD) { bestD = d; best = r; }
            }
        }
        if (best == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} camera '{cam.name}' has no room"); return; }
        best.survCamera = cam;
        Vector2 center = best.transform.position;
        cam.Offset = new Vector3(0f, 0f, cam.Offset.z);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} camera '{cam.name}' -> room {best.RoomId} ({best.name}), view center ({center.x:F1},{center.y:F1})");
    }

    // ---------------------------------------------------------------- Minimap

    /// <summary>
    /// ShipStatus.MapPrefab ist ein ASSET (kein Elternteil in der Szene, Log vom 25.08.). Ein
    /// Eingriff dort wuerde die Skeld-Minimap bis zum Neustart verbiegen. Deshalb eine Kopie
    /// unter einem inaktiven Halter (ihr Awake laeuft nicht), die wird umgebaut und als
    /// MapPrefab eingetragen. Der Halter haengt am Ship und stirbt mit ihm.
    /// Kartenraum: MapBehaviour setzt HerePoint.localPosition = Weltposition / MapScale.
    /// </summary>
    private static void RebuildMinimap(ShipStatus ship)
    {
        if (ship.MapPrefab == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} no MapPrefab"); return; }

        var holder = new GameObject("Atlas_MapTemplate");
        holder.SetActive(false);
        holder.transform.SetParent(ship.transform, false);
        var copy = Object.Instantiate(ship.MapPrefab, holder.transform);
        copy.name = "MuseumMap";
        ship.MapPrefab = copy;

        // Eine noch lebende Karten-Instanz (vorige Runde) zeigt sonst weiter die Skeld.
        if (MapBehaviour.Instance != null)
        {
            Object.Destroy(MapBehaviour.Instance.gameObject);
            MapBehaviour.Instance = null;
        }

        var space = copy.HerePoint != null ? copy.HerePoint.transform.parent : copy.transform;

        // Hierarchie loggen: erst das Protokoll macht aus der Heuristik unten einen Befund.
        var lines = new List<string>();
        foreach (var r in copy.GetComponentsInChildren<SpriteRenderer>(true))
            if (r.sprite != null)
                lines.Add($"{Path(r.transform, copy.transform)}({r.sprite.bounds.size.x:F1}x{r.sprite.bounds.size.y:F1})");
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} minimap renderers: {string.Join(", ", lines)}");

        // Grundriss der Skeld = Renderer "Background" (Log 22.09.: 9,8 x 5,6). Der groesste
        // Renderer war falsch: "FadedBackground" ist die Abdunklung hinter der Karte (1x1-Sprite,
        // riesig skaliert) und muss bleiben.
        SpriteRenderer bg = null;
        foreach (var r in copy.GetComponentsInChildren<SpriteRenderer>(true))
            if (r.sprite != null && r.name == "Background" && !InOverlay(r.transform, copy)) { bg = r; break; }
        if (bg == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} minimap: no 'Background' renderer"); return; }

        // Massstab: das Museum (61 x 43 m) ist breiter als die Skeld. MapScale so waehlen, dass
        // es genau in das Rechteck des Skeld-Grundrisses passt - das Kartenfenster ist darauf gebaut.
        var bMin = space.InverseTransformPoint(bg.bounds.min);
        var bMax = space.InverseTransformPoint(bg.bounds.max);
        float bgW = Mathf.Abs(bMax.x - bMin.x), bgH = Mathf.Abs(bMax.y - bMin.y);
        float mW = D.MaxX - D.MinX, mH = D.MaxY - D.MinY;
        float oldScale = ship.MapScale;
        float scale = Mathf.Max(mW / Mathf.Max(bgW, 0.01f), mH / Mathf.Max(bgH, 0.01f));
        ship.MapScale = scale;

        // Mitte: HerePoint/Taskmarker liegen bei Welt/MapScale im jeweiligen Overlay-Raum. Die
        // Museumsmitte soll auf die Mitte des alten Grundrisses fallen, also werden Hier-Punkt-,
        // Task-, Sabotage- und Zaehler-Ebene gemeinsam um dieselbe Weltstrecke verschoben.
        var museumCenter = new Vector2((D.MinX + D.MaxX) * 0.5f,
                                       (D.MinY + D.MaxY) * 0.5f);
        var bgCenter = (Vector2)(bMin + bMax) * 0.5f;
        var shiftWorld = space.TransformVector(bgCenter - museumCenter / scale);
        shiftWorld.z = 0f;
        var shifted = new List<string>();
        void Shift(Component c, string label)
        {
            if (c == null) return;
            c.transform.position += shiftWorld;
            shifted.Add($"{label}@{c.transform.localPosition.x:F2},{c.transform.localPosition.y:F2}");
        }
        Shift(space, "here");
        // Die Task-Ebene haengt (Skeld) UNTER der Hier-Punkt-Ebene und wandert mit ihr mit. Ein
        // zweiter Schub hat sie im Test 22.09. um genau diese Strecke (-4,1 | -9,6 m) versetzt.
        if (copy.taskOverlay != null && !copy.taskOverlay.transform.IsChildOf(space)) Shift(copy.taskOverlay, "tasks");
        AtlasPlugin.Logger.LogInfo(
            $"{LogPrefix} minimap scale {oldScale:F2} -> {scale:F2} (bg {bgW:F2}x{bgH:F2} @ {bgCenter.x:F2},{bgCenter.y:F2}); shifted {string.Join(", ", shifted)}");

        Vector3 MapWorld(Vector2 w) => space.TransformPoint(new Vector3(w.x / scale, w.y / scale, 0f));

        var sprite = AtlasAssets.MapMinimapSprite(D, scale);
        if (sprite != null)
        {
            var go = new GameObject("Atlas_MinimapFloor") { layer = bg.gameObject.layer };
            go.transform.SetParent(space, false);
            var local = space.InverseTransformPoint(bg.transform.position);
            go.transform.localPosition = new Vector3(museumCenter.x / scale, museumCenter.y / scale, local.z);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sortingLayerID = bg.sortingLayerID;
            sr.sortingOrder = bg.sortingOrder;
            sr.sharedMaterial = bg.sharedMaterial;
            bg.enabled = false;
        }

        // Skeld-Raumnamen ausblenden (Text ausserhalb der Overlays); unsere stehen im Bild.
        int hidden = 0;
        foreach (var tmp in copy.GetComponentsInChildren<TextMeshPro>(true))
        {
            if (InOverlay(tmp.transform, copy)) continue;
            tmp.gameObject.SetActive(false);
            hidden++;
        }
        // Weitere Skeld-Zeichnung (falls die Hierarchie mehr als ein Grundrissbild hat) bleibt
        // vorerst stehen: blind abschalten traefe auch Knoepfe. Das Renderer-Log oben entscheidet.

        // Sabotage-/Tuerknoepfe.
        int buttons = 0;
        if (copy.infectedOverlay != null && copy.infectedOverlay.rooms != null)
        {
            foreach (var room in copy.infectedOverlay.rooms)
            {
                if (room == null) continue;
                if (!D.MapButtons.TryGetValue(room.room, out var w) && !RoomCenter(room.room, out w))
                {
                    room.gameObject.SetActive(false);
                    continue;
                }
                var p = MapWorld(w);
                room.transform.position = new Vector3(p.x, p.y, room.transform.position.z);
                buttons++;
            }
        }

        // Admin-Zaehler.
        int counters = 0;
        if (copy.countOverlay != null && copy.countOverlay.CountAreas != null)
        {
            foreach (var area in copy.countOverlay.CountAreas)
            {
                if (area == null) continue;
                if (!RoomCenter(area.RoomType, out var w)) { area.gameObject.SetActive(false); continue; }
                var p = MapWorld(w);
                area.transform.position = new Vector3(p.x, p.y, area.transform.position.z);
                counters++;
            }
        }

        AtlasWorld.AddMapButtons(copy, MapWorld);

        AtlasPlugin.Logger.LogInfo(
            $"{LogPrefix} minimap: scale {scale:F3}, {hidden} label(s) hidden, {buttons} button room(s), {counters} counter(s)");
    }

    private static bool InOverlay(Transform t, MapBehaviour map)
    {
        if (map.infectedOverlay != null && t.IsChildOf(map.infectedOverlay.transform)) return true;
        if (map.countOverlay != null && t.IsChildOf(map.countOverlay.transform)) return true;
        if (map.taskOverlay != null && t.IsChildOf(map.taskOverlay.transform)) return true;
        return false;
    }

    private static bool RoomCenter(SystemTypes type, out Vector2 center)
    {
        foreach (var r in D.Rooms)
        {
            if (r.Room != type) continue;
            Vector2 sum = Vector2.zero;
            foreach (var p in r.Area) sum += p;
            center = sum / r.Area.Length;
            return true;
        }
        center = default;
        return false;
    }

    private static string Path(Transform t, Transform stop)
    {
        var parts = new List<string>();
        for (var p = t; p != null && p != stop; p = p.parent) parts.Add(p.name);
        parts.Reverse();
        return string.Join("/", parts);
    }
}
