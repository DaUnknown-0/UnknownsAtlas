// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Baustein "Auf Zielen halten" (28.10.): vier Ziele nebeneinander, auf jedem die Maustaste kurz halten, bis es umschlaegt
// (trocken -> gegossen, roh -> geroestet). Ein optionales Werkzeug folgt beim Halten der Maus. Fuer Karten anderer Plugins:
// die Arten "watering" und "roast" sind derselbe Baustein, Grafik und Texte kommen ueber AtlasMapDef.TaskArt/TaskText
// ("<art>:task_hold_bg.png", "task_hold_center.png", "task_hold_off.png", "task_hold_on.png", "task_hold_tool.png",
// Text "HOLD ON EACH ONE").

using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class HoldTargetsMechanic : IAtlasMechanic
{
    private readonly string _kind;
    public string Name => _kind;
    const float Need = 1.2f, Reach = 0.75f;
    private readonly List<(Vector2 P, SpriteRenderer R, Vector3 Scale)> _targets = new();
    private readonly float[] _held = new float[4];
    private readonly bool[] _on = new bool[4];
    private Sprite _onSprite;
    private SpriteRenderer _tool;
    private TextMeshPro _msg;
    private InputScript _script;
    private float _t;

    public HoldTargetsMechanic(string kind) { _kind = kind; }

    public float Progress { get { int n = 0; foreach (var o in _on) if (o) n++; return n / 4f; } }
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        if (AtlasAssets.TaskArtExists(AtlasTaskKit.Art("task_hold_bg.png")))
            AtlasTaskKit.Sprite(root, "task_hold_bg.png", 100f, Vector2.zero, 1);
        if (AtlasAssets.TaskArtExists(AtlasTaskKit.Art("task_hold_center.png")))
            AtlasTaskKit.Sprite(root, "task_hold_center.png", 100f, new Vector2(0f, -1.35f), 2);
        _onSprite = AtlasAssets.TaskSprite("task_hold_on.png", 100f, new Vector2(0.5f, 0.5f));
        for (int i = 0; i < 4; i++)
        {
            var p = new Vector2(-2.4f + i * 1.6f, 0.55f);
            var r = AtlasTaskKit.Sprite(root, "task_hold_off.png", 100f, p, 3);
            _targets.Add((p, r, r.transform.localScale));
        }
        if (AtlasAssets.TaskArtExists(AtlasTaskKit.Art("task_hold_tool.png")))
        {
            _tool = AtlasTaskKit.Sprite(root, "task_hold_tool.png", 100f, Vector2.zero, 8, new Vector2(0.15f, 0.2f));
            _tool.enabled = false;
        }
        _msg = MatchKit.Text(root, new Vector2(0f, 2.25f), AtlasTaskKit.T("HOLD ON EACH ONE"), 2.2f, Color.white, 9);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (Done) return;
        _t += dt;
        int hover = -1;
        for (int i = 0; i < 4; i++)
            if (!_on[i] && Vector2.Distance(mouse, _targets[i].P) < Reach) { hover = i; break; }
        if (_tool != null)
        {
            _tool.enabled = down;
            _tool.transform.localPosition = new Vector3(mouse.x, mouse.y, _tool.transform.localPosition.z);
            _tool.transform.localEulerAngles = new Vector3(0f, 0f, down && hover >= 0 ? Mathf.Sin(_t * 9f) * 6f : 0f);
        }
        for (int i = 0; i < 4; i++)
        {
            if (_on[i]) continue;
            var (p, r, sc) = _targets[i];
            if (down && hover == i) _held[i] += dt;
            float k = Mathf.Clamp01(_held[i] / Need);
            // waehrend des Haltens wackelt das Ziel leicht und wird heller
            float wob = down && hover == i ? 1f + 0.05f * Mathf.Sin(_t * 18f) : 1f;
            r.transform.localScale = sc * wob;
            r.color = Color.Lerp(new Color(0.8f, 0.8f, 0.8f), Color.white, k);
            if (k >= 1f)
            {
                _on[i] = true;
                r.sprite = _onSprite;
                r.color = Color.white;
                r.transform.localScale = sc * 1.08f;
            }
        }
        int n = 0;
        foreach (var o in _on) if (o) n++;
        if (n == 4) { Done = true; _msg.text = AtlasTaskKit.T("DONE"); if (_tool != null) _tool.enabled = false; }
        else _msg.text = $"{AtlasTaskKit.T("HOLD ON EACH ONE")}  {n}/4";
    }

    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_script == null)
        {
            _script = new InputScript();
            foreach (var t in _targets) _script.Hold(t.P, Need + 0.25f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}
