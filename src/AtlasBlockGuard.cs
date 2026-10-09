// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasBlockGuard - wer gerade in einer Sperre steht, wenn sie sich schliesst, kommt dort heraus, wo er
// herkam (User 09.10.).
//
// Schranken, Karussellseil, Bruecke und Drehkreuz-Stau im Park sowie das Sturmholz im Wald schalten einen
// Kollider auf der Schiffsebene ein. Stand ein Spieler schon darin, drueckte ihn die Physik auf irgendeine
// Seite heraus, im schlimmsten Fall auf die falsche oder in eine Ecke, in der er festhing.
//
// Bewegung ist client-seitig: jeder Client kuemmert sich nur um seinen eigenen Spieler. Dafuer merkt sich
// der Baustein die letzten Fusspositionen (5 s, laenger als jede Vorwarnung). Schliesst eine Sperre, sucht er die juengste Position
// AUSSERHALB der Sperre und setzt den Spieler an die Kante auf genau dieser Seite. Ohne solche Position
// (stand schon die ganze Zeit darin) geht es zur naechsten Kante quer zur Sperre.

using System;
using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal static class AtlasBlockGuard
{
    private const string LogPrefix = "[Atlas/Block]";
    private const float Keep = 5f, Every = 0.05f, Margin = 0.06f;

    private static readonly List<(float T, Vector2 P)> History = new();
    private static float _next;

    public static void Reset() { History.Clear(); _next = 0f; }

    /// <summary>Jeden Frame (AtlasWorld-Takt): Fussposition des eigenen Spielers mitschreiben.</summary>
    public static void Track()
    {
        var lp = PlayerControl.LocalPlayer;
        if (lp == null || Time.time < _next) return;
        _next = Time.time + Every;
        Vector2 p;
        try { p = lp.GetTruePosition(); } catch { return; }
        History.Add((Time.time, p));
        while (History.Count > 0 && Time.time - History[0].T > Keep) History.RemoveAt(0);
    }

    /// <summary>Gleich schliesst sich eine achsparallele Sperre (Mitte, Groesse in Weltmetern): steht der eigene
    /// Spieler darin, vorher auf die Seite setzen, von der er kam. Vor dem Einschalten des Kolliders aufrufen.</summary>
    public static void ClearLocal(Vector2 center, Vector2 size, string what)
    {
        try
        {
            var lp = PlayerControl.LocalPlayer;
            if (lp == null || lp.Data == null || lp.Data.IsDead || lp.inVent) return;
            var col = lp.Collider;
            if (col == null || !col.enabled) return;                       // faehrt gerade (Kollider aus)
            float r = col.bounds.extents.x + Margin;
            var min = center - size / 2f - new Vector2(r, r);
            var max = center + size / 2f + new Vector2(r, r);
            var feet = lp.GetTruePosition();
            if (!Inside(feet, min, max)) return;

            // juengste Position ausserhalb der Sperre
            Vector2? from = null;
            for (int i = History.Count - 1; i >= 0; i--)
                if (!Inside(History[i].P, min, max)) { from = History[i].P; break; }

            Vector2 target;
            if (from.HasValue)
            {
                var f = from.Value;
                // die Kante, ueber die er hereinkam: die Achse, auf der er am weitesten draussen war
                float ox = f.x < min.x ? min.x - f.x : f.x > max.x ? f.x - max.x : 0f;
                float oy = f.y < min.y ? min.y - f.y : f.y > max.y ? f.y - max.y : 0f;
                target = ox >= oy
                    ? new Vector2(f.x < min.x ? min.x : max.x, Mathf.Clamp(feet.y, min.y, max.y))
                    : new Vector2(Mathf.Clamp(feet.x, min.x, max.x), f.y < min.y ? min.y : max.y);
            }
            else
            {
                // keine Vorgeschichte: zur naechsten Kante quer zur Sperre (die schmale Seite wird durchquert)
                if (size.x < size.y)
                    target = new Vector2(feet.x < center.x ? min.x : max.x, feet.y);
                else
                    target = new Vector2(feet.x, feet.y < center.y ? min.y : max.y);
            }

            var offset = (Vector2)lp.transform.position - feet;            // Transform liegt ueber den Fuessen
            var to = target + offset;
            try { lp.NetTransform.RpcSnapTo(to); }
            catch { AtlasFigure.SetPos(lp, to); }
            AtlasFigure.StopBody(lp);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} {what} closed on the local player: moved from ({feet.x:F2},{feet.y:F2}) " +
                                       $"to ({target.x:F2},{target.y:F2}) {(from.HasValue ? "back where they came from" : "to the nearest side")}");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} {what}: {e.Message}"); }
    }

    /// <summary>Wie ClearLocal, Groesse aus einem (schon platzierten, noch inaktiven) BoxCollider2D.</summary>
    public static void ClearLocal(BoxCollider2D box, string what)
    {
        if (box == null) return;
        // bounds eines inaktiven Kolliders sind leer: aus Transform und Groesse rechnen (Drehung nur in 90-Grad-Schritten)
        var t = box.transform;
        Vector2 c = t.TransformPoint(box.offset);
        Vector2 ex = t.TransformVector(new Vector3(box.size.x, 0f, 0f));
        Vector2 ey = t.TransformVector(new Vector3(0f, box.size.y, 0f));
        var size = new Vector2(Mathf.Abs(ex.x) + Mathf.Abs(ey.x), Mathf.Abs(ex.y) + Mathf.Abs(ey.y));
        ClearLocal(c, size, what);
    }

    private static bool Inside(Vector2 p, Vector2 min, Vector2 max) =>
        p.x > min.x && p.x < max.x && p.y > min.y && p.y < max.y;
}
