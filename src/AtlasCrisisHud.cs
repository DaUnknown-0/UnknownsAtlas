// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasCrisisHud - eine Zeile oben in der Bildmitte waehrend einer eigenen kritischen Sabotage (Rex erwacht,
// Conductor's Round): Restzeit und Stand fuer ALLE, auch fuer Spieler, die schon in Sicherheit sind, und fuer
// Geister (User 19.10.: "jeder soll sehen, wie lange sie noch laeuft, auch wenn man schon sicher ist").
// Die Zeile in der Aufgabenliste bleibt daneben bestehen; sie ist eingeklappt nicht zu sehen.

using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

internal static class AtlasCrisisHud
{
    private static TextMeshPro _text;
    private static string _owner;

    /// <summary>Zeile anzeigen oder aktualisieren; owner = Sabotage, der sie gehoert (nur die darf sie loeschen).</summary>
    public static void Show(string owner, string line, Color color)
    {
        try
        {
            var hud = HudManager.InstanceExists ? HudManager.Instance : null;
            if (hud == null) return;
            if (_text == null)
            {
                var go = new GameObject("Atlas_CrisisHud") { layer = 5 };
                go.transform.SetParent(hud.transform, false);
                go.transform.localPosition = new Vector3(0f, 2.55f, -5f);
                _text = go.AddComponent<TextMeshPro>();
                var src = hud.GetComponentInChildren<TextMeshPro>(true);
                if (src != null) { _text.font = src.font; _text.fontSharedMaterial = src.fontSharedMaterial; }
                _text.fontSize = 2.6f;
                _text.alignment = TextAlignmentOptions.Center;
                _text.enableWordWrapping = false;
                _text.rectTransform.sizeDelta = new Vector2(10f, 1f);
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null) mr.sortingOrder = 500;
            }
            _owner = owner;
            _text.text = line;
            _text.color = color;
            bool show = MeetingHud.Instance == null && ExileController.Instance == null;
            if (_text.gameObject.activeSelf != show) _text.gameObject.SetActive(show);
        }
        catch { }
    }

    public static void Hide(string owner)
    {
        if (_text == null || (owner != null && _owner != owner)) return;
        try { _text.gameObject.SetActive(false); } catch { }
        _owner = null;
    }

    public static void Reset()
    {
        if (_text != null) { try { Object.Destroy(_text.gameObject); } catch { } }
        _text = null; _owner = null;
    }
}
