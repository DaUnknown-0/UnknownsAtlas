// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasWorldFx - die Welt-Effekte der sichtbaren Tasks (Visual Tasks) auf den Atlas-Karten.
//
// Die eigenen Minispiele rufen wie die Vanilla-Minispiele PlayerControl.RpcPlayAnimation(TaskType).
// Das laeuft bei ALLEN Spielern ueber PlayerControl.PlayAnimation; die Skeld-Objekte, die dort
// sonst animiert wuerden (Waffen, Schildlichter, Muellschacht), gibt es auf den Atlas-Karten nicht
// mehr. Deshalb haengt hier ein Postfix, der am passenden Ort der Karte einen eigenen Effekt zeigt
// (Ort = die Konsole des Raums, zu dem der Skeld-Effekt gehoert: Weapons, Shields, Storage).
// Damit bleibt die Beweiskraft der Visual Tasks erhalten.

using System;
using System.Collections;
using System.Collections.Generic;
using BepInEx.Unity.IL2CPP.Utils;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasWorldFx
{
    private const string LogPrefix = "[Atlas/Fx]";
    private static readonly List<GameObject> Persistent = new();
    private static int _lanterns;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.PlayAnimation))]
    internal static void PlayerControl_PlayAnimation_Postfix(PlayerControl __instance, byte __0)
    {
        if (!AtlasMuseumBuilder.Active || ShipStatus.Instance == null) return;
        try
        {
            if (!VisualTasksOn()) return;
            var type = (TaskTypes)__0;
            bool wald = AtlasMuseumBuilder.D.Key == "wald";
            bool park = AtlasMuseumBuilder.D.Key == "park";
            switch (type)
            {
                case TaskTypes.ClearAsteroids when park:
                    // Schiessbude: ein Treffer-Stern ueber dem Stand
                    if (Find(SystemTypes.Weapons, type, out var wp))
                        Flash(wp + new Vector2(UnityEngine.Random.Range(-0.4f, 0.4f), 0.9f), "task_park_pop.png", Color.white, 0.8f, 0.45f);
                    break;
                case TaskTypes.PrimeShields when park:
                    if (Find(SystemTypes.Shields, type, out var sp)) ShipStatus.Instance.StartCoroutine(CoSpotlights(sp));
                    break;
                case TaskTypes.EmptyGarbage when park:
                    if (Find(SystemTypes.Storage, type, out var gp))
                        Flash(gp + new Vector2(0f, 0.7f), "task_park_puff.png", Color.white, 1.1f, 1.4f, rise: true);
                    break;
                case TaskTypes.ClearAsteroids:
                    if (Find(SystemTypes.Weapons, type, out var w))
                        Flash(w + new Vector2(0f, 0.9f), wald ? "task_lamp_on.png" : "task_torch.png",
                              wald ? new Color(1f, 0.3f, 0.3f) : new Color(1f, 0.95f, 0.8f), wald ? 0.6f : 1.4f, 0.35f);
                    break;
                case TaskTypes.PrimeShields:
                    if (!Find(SystemTypes.Shields, type, out var s)) break;
                    if (wald) Lanterns(s);
                    else ShipStatus.Instance.StartCoroutine(CoLaser(s));
                    break;
                case TaskTypes.EmptyGarbage:
                    if (Find(SystemTypes.Storage, type, out var g))
                        Flash(g + new Vector2(0f, 0.7f), "task_steam.png", wald ? new Color(0.55f, 0.42f, 0.28f) : new Color(0.75f, 0.72f, 0.66f), 1.2f, 1.4f, rise: true);
                    break;
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} {__0}: {e.Message}"); }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.OnDestroy))]
    internal static void ShipStatus_OnDestroy_Postfix()
    {
        Persistent.Clear();
        _lanterns = 0;
    }

    private static bool VisualTasksOn()
    {
        try { return GameOptionsManager.Instance.CurrentGameOptions.GetBool(AmongUs.GameOptions.BoolOptionNames.VisualTasks); }
        catch { return true; }
    }

    /// <summary>Position der Konsole fuer diesen Task in diesem Raum (die umgezogene Skeld-Konsole).</summary>
    private static bool Find(SystemTypes room, TaskTypes type, out Vector2 pos)
    {
        pos = default;
        Console best = null;
        foreach (var c in ShipStatus.Instance.AllConsoles)
        {
            if (c == null || c.TaskTypes == null) continue;
            bool has = false;
            foreach (var t in c.TaskTypes) if (t == type) has = true;
            if (!has) continue;
            if (best == null || c.Room == room) best = c;
            if (c.Room == room) break;
        }
        if (best == null) return false;
        pos = best.transform.position;
        return true;
    }

    private static SpriteRenderer WorldSprite(string file, Vector2 p, float scale, Color c)
    {
        var go = new GameObject("Atlas_Fx") { layer = 11 };
        go.transform.SetParent(ShipStatus.Instance.transform, true);
        go.transform.position = new Vector3(p.x, p.y, (p.y + 0.36f) / 1000f - 0.002f);
        go.transform.localScale = Vector3.one * scale;
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite(file, 100f, new Vector2(0.5f, 0.5f));
        sr.color = c;
        return sr;
    }

    private static void Flash(Vector2 p, string file, Color c, float scale, float time, bool rise = false)
    {
        var sr = WorldSprite(file, p, scale, c);
        ShipStatus.Instance.StartCoroutine(CoFade(sr, c, time, rise));
    }

    private static IEnumerator CoFade(SpriteRenderer sr, Color c, float time, bool rise)
    {
        float t = 0f;
        var p0 = sr.transform.position;
        while (t < time && sr != null)
        {
            t += Time.deltaTime;
            float k = t / time;
            sr.color = new Color(c.r, c.g, c.b, c.a * (1f - k));
            if (rise) sr.transform.position = p0 + new Vector3(Mathf.Sin(t * 30f) * 0.05f, k * 0.6f, 0f);
            yield return null;
        }
        if (sr != null) Object.Destroy(sr.gameObject);
    }

    /// <summary>Museum: das Laserraster der Tresorvitrine leuchtet rot auf.</summary>
    private static IEnumerator CoLaser(Vector2 p)
    {
        var bars = new List<SpriteRenderer>();
        for (int i = 0; i < 4; i++)
        {
            var b = WorldSprite("task_white.png", p + new Vector2(-0.6f + i * 0.4f, 0.7f), 1f, new Color(1f, 0.15f, 0.15f, 0.8f));
            b.transform.localScale = new Vector3(0.04f / 0.16f, 1.2f / 0.16f, 1f);
            bars.Add(b);
            var h = WorldSprite("task_white.png", p + new Vector2(0f, 0.2f + i * 0.3f), 1f, new Color(1f, 0.15f, 0.15f, 0.8f));
            h.transform.localScale = new Vector3(1.4f / 0.16f, 0.04f / 0.16f, 1f);
            bars.Add(h);
        }
        float t = 0f;
        while (t < 2.5f)
        {
            t += Time.deltaTime;
            float a = 0.5f + 0.4f * Mathf.Sin(t * 14f);
            foreach (var b in bars) if (b != null) b.color = new Color(1f, 0.15f, 0.15f, a * (1f - t / 2.5f));
            yield return null;
        }
        foreach (var b in bars) if (b != null) Object.Destroy(b.gameObject);
    }

    /// <summary>Park: zwei Scheinwerferkegel am Lichtturm schwenken kurz ueber den Himmel.</summary>
    private static IEnumerator CoSpotlights(Vector2 p)
    {
        var beams = new List<SpriteRenderer>();
        for (int i = 0; i < 2; i++)
        {
            var b = WorldSprite("task_park_beam.png", p + new Vector2(i == 0 ? -0.35f : 0.35f, 0.4f), 1f, new Color(1f, 0.95f, 0.75f, 0f));
            // Sprite-Pivot ist die Mitte: den Kegel um seinen Fuss drehen, deshalb ein Halter
            var holder = new GameObject("Atlas_FxBeam") { layer = 11 };
            holder.transform.SetParent(ShipStatus.Instance.transform, true);
            holder.transform.position = b.transform.position;
            b.transform.SetParent(holder.transform, true);
            b.transform.localPosition = new Vector3(0f, 1.1f, 0f);
            beams.Add(b);
        }
        float t = 0f;
        while (t < 2.8f)
        {
            t += Time.deltaTime;
            float a = Mathf.Clamp01(t * 3f) * Mathf.Clamp01((2.8f - t) * 1.5f) * 0.75f;
            for (int i = 0; i < beams.Count; i++)
            {
                if (beams[i] == null) continue;
                beams[i].color = new Color(1f, 0.95f, 0.75f, a);
                beams[i].transform.parent.localEulerAngles = new Vector3(0, 0, (i == 0 ? 1f : -1f) * (18f + 22f * Mathf.Sin(t * 2.2f + i)));
            }
            yield return null;
        }
        foreach (var b in beams) if (b != null) Object.Destroy(b.transform.parent.gameObject);
    }

    /// <summary>Wald: die Steglaternen glimmen auf und bleiben an (bis Rundenende).</summary>
    private static void Lanterns(Vector2 p)
    {
        if (_lanterns > 0) return;
        for (int i = 0; i < 3; i++)
        {
            var sr = WorldSprite("task_lantern_on.png", p + new Vector2(-0.9f + i * 0.9f, 0.9f), 0.45f, Color.white);
            Persistent.Add(sr.gameObject);
        }
        _lanterns = 3;
    }
}
