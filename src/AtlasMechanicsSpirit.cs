// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Baustein "Geisterbrett" (spirit): das Brett buchstabiert ein Wort, Buchstabe fuer Buchstabe leuchtet auf,
// dann zieht der Spieler die Planchette in derselben Reihenfolge ueber die Buchstaben und zum Schluss auf
// GOODBYE. Ein falscher Buchstabe unter dem Fenster setzt die Folge zurueck (rotes Aufblitzen), das Wort
// bleibt. Eine Simon-Variante; genutzt von Karten anderer Plugins ueber AtlasMapDef.CustomTasks.
//
// Grafik (aus dem Paket der Karte, AtlasAssets.TaskSprite sucht dort zuerst):
//   task_spirit_board.png      720 x 520, das Brett mit allen Zeichen an den Stellen unten (100 px = 1 Einheit)
//   task_spirit_planchette.png 160 x 170, Drehpunkt = Fenster (Mitte, 0,5/0,56)
//   task_spirit_glow.png       110 x 110, weicher Lichtfleck, wird getoent
//
// Zeichenpositionen (Einheiten): Reihe A-M bei y 0,78, N-Z bei y 0,2 (x von -2,7 in 0,45-Schritten), Ziffern
// 1-9 und 0 bei y -0,42 (x von -2,25 in 0,5-Schritten), YES (-2,3 / 1,5), NO (2,3 / 1,5), GOODBYE (0 / -1,15).

using System.Collections.Generic;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class SpiritMechanic : IAtlasMechanic
{
    public string Name => "spirit";
    private const float ShowSecs = 0.55f, GapSecs = 0.22f, Hit = 0.27f;
    private static readonly string[] Words =
        { "LEAVE", "BELOW", "COLD", "HIDE", "SEVEN", "RUN", "DOOR", "BURN", "ALONE", "WAKE", "LIES", "MINE" };
    private static readonly Vector2 Goodbye = new(0f, -1.15f);

    private readonly Dictionary<char, Vector2> _pos = new();
    private readonly List<SpriteRenderer> _glows = new();
    private SpriteRenderer _showGlow, _planchette;
    private string _word;
    private int _shown = -1, _next;
    private float _t, _red, _wrong;
    private bool _watching = true;
    private InputScript _script;
    public float Progress => _word == null ? 0f : _next / (float)(_word.Length + 1);
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        for (int i = 0; i < 13; i++) _pos[(char)('A' + i)] = new Vector2(-2.7f + i * 0.45f, 0.78f);
        for (int i = 0; i < 13; i++) _pos[(char)('N' + i)] = new Vector2(-2.7f + i * 0.45f, 0.2f);
        for (int i = 0; i < 10; i++) _pos[(char)('1' + i < ':' ? '1' + i : '0')] = new Vector2(-2.25f + i * 0.5f, -0.42f);
        AtlasTaskKit.Sprite(root, "task_spirit_board.png", 100f, Vector2.zero, 0);
        _word = Words[Random.Range(0, Words.Length)];
        _showGlow = AtlasTaskKit.Sprite(root, "task_spirit_glow.png", 100f, Goodbye, 2);
        _showGlow.color = new Color(0.6f, 0.95f, 0.9f, 0f);
        _planchette = AtlasTaskKit.Sprite(root, "task_spirit_planchette.png", 100f, Goodbye, 5, new Vector2(0.5f, 0.56f));
        _planchette.color = new Color(1f, 1f, 1f, 0.85f);
        _t = -0.8f;
    }

    private void Light(Vector2 p, Transform root)
    {
        var g = AtlasTaskKit.Sprite(root, "task_spirit_glow.png", 100f, p, 1);
        g.color = new Color(0.55f, 0.95f, 0.85f, 0.75f);
        _glows.Add(g);
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _red = Mathf.Max(0f, _red - dt * 2.5f);
        _planchette.color = Color.Lerp(new Color(1f, 1f, 1f, 0.85f), new Color(1f, 0.4f, 0.4f, 0.95f), _red);
        if (_watching)
        {
            // das Brett buchstabiert: je Buchstabe ShowSecs leuchten, GapSecs Pause
            _t += dt;
            if (_t < 0f) return;
            int idx = (int)(_t / (ShowSecs + GapSecs));
            float phase = _t - idx * (ShowSecs + GapSecs);
            if (idx >= _word.Length)
            {
                _watching = false;
                AtlasPlugin.Logger.LogInfo($"[Atlas/Task] spirit: word shown ({_word}), now repeat");
                _showGlow.color = new Color(0.6f, 0.95f, 0.9f, 0f);
                return;
            }
            var p = _pos[_word[idx]];
            _showGlow.transform.localPosition = new Vector3(p.x, p.y, -0.02f);
            float a = phase < ShowSecs ? Mathf.Sin(Mathf.Clamp01(phase / ShowSecs) * Mathf.PI) : 0f;
            _showGlow.color = new Color(0.6f, 0.95f, 0.9f, 0.85f * a);
            _shown = idx;
            return;
        }
        if (Done) return;
        if (down)
        {
            var cur = (Vector2)_planchette.transform.localPosition;
            var to = Vector2.Lerp(cur, mouse, Mathf.Clamp01(dt * 14f));
            _planchette.transform.localPosition = new Vector3(to.x, to.y, -0.05f);
        }
        var at = (Vector2)_planchette.transform.localPosition;
        if (_next < _word.Length)
        {
            char want = _word[_next];
            if (Vector2.Distance(at, _pos[want]) < Hit)
            {
                Light(_pos[want], _planchette.transform.parent);
                _next++;
                AtlasPlugin.Logger.LogInfo($"[Atlas/Task] spirit: {_next}/{_word.Length} at ({at.x:F2},{at.y:F2})");
                _wrong = 0f;
                return;
            }
            // ein anderer Buchstabe unter dem Fenster: kurz Zeit zum Weiterziehen, dann zurueck auf Anfang
            bool other = false;
            foreach (var kv in _pos)
                if (kv.Key != want && Vector2.Distance(at, kv.Value) < Hit * 0.8f && _word.IndexOf(kv.Key) >= _next) { other = true; break; }
            _wrong = other ? _wrong + dt : 0f;
            if (_wrong > 0.3f)
            {
                _wrong = 0f;
                _next = 0;
                _red = 1f;
                foreach (var g in _glows) if (g != null) Object.Destroy(g.gameObject);
                _glows.Clear();
            }
            return;
        }
        if (Vector2.Distance(at, Goodbye) < Hit + 0.1f)
        {
            Light(Goodbye, _planchette.transform.parent);
            Done = true;
        }
    }

    private float _simLog;
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        if (_watching) { mouse = Goodbye; down = false; return; }
        _simLog += dt;
        if (_simLog > 2f) { _simLog = 0f; AtlasPlugin.Logger.LogInfo($"[Atlas/Task] spirit sim: next {_next}, planchette ({_planchette.transform.localPosition.x:F2},{_planchette.transform.localPosition.y:F2}), script {(_script == null ? "none" : _script.Finished ? "finished" : "running")}"); }
        if (_script == null || (_script.Finished && !Done))
        {
            // vom aktuellen Stand aus (nach einem Fehlgriff beginnt die Folge von vorn)
            var pts = new List<Vector2> { (Vector2)_planchette.transform.localPosition };
            for (int i = _next; i < _word.Length; i++) pts.Add(_pos[_word[i]]);
            pts.Add(Goodbye);
            _script = new InputScript().Wait(pts[0], 0.3f).Path(pts, 0.5f);
        }
        _script.Next(dt, out mouse, out down);
    }

    public void Dispose() { }
}
