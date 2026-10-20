// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// Die Lochzange der Sabotage "Conductor's Round" (AtlasTicket):
//
//   ticketpunch  Fahrschein liegt in der Zange; Griff gedrueckt halten (Maus auf dem Griff), die Zange
//                schliesst sich in PunchHold Sekunden, das Loch erscheint, "STAMPED" und das Minispiel
//                schliesst ohne Task-Schritt (Leave). Loslassen oeffnet die Zange wieder.
//
// Meldet nur "gestempelt" (AtlasTicket.Stamp); Zeit und Rauswurf rechnet der Host.

using TMPro;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class TicketPunchMechanic : IAtlasMechanic
{
    public string Name => "ticketpunch";
    static readonly Vector2 Ticket = new(-0.9f, -0.2f);
    static readonly Vector2 TicketSize = new(3.2f, 1.7f);
    static readonly Vector2 Jaw = new(0.95f, 0.55f);             // Drehpunkt der Zange ueber dem Fahrschein
    static readonly Vector2 Grip = new(2.4f, 0.1f);              // Griff: hier druecken

    private float _hold, _doneAt;
    private bool _stamped;
    private Transform _upper;
    private SpriteRenderer _hole, _fill;
    private TextMeshPro _msg, _timer;

    public float Progress => Mathf.Clamp01(_hold / AtlasTicket.PunchHold);
    public bool Done => false;
    public bool Leave { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        MatchKit.Text(root, new Vector2(0f, 2.0f), "STAMP YOUR TICKET", 2.1f, Color.white, 6);
        // Fahrschein: Papier mit rotem Streifen und Zeilen, gezackte Abrisskante angedeutet
        MatchKit.Box(root, Ticket, TicketSize + new Vector2(0.12f, 0.12f), new Color(0.11f, 0.1f, 0.12f), 1);
        MatchKit.Box(root, Ticket, TicketSize, new Color(0.93f, 0.83f, 0.59f), 2);
        MatchKit.Box(root, Ticket + new Vector2(0f, 0.55f), new Vector2(2.8f, 0.22f), new Color(0.69f, 0.24f, 0.2f), 3);
        MatchKit.Text(root, Ticket + new Vector2(0f, 0.55f), "POLARIS EXPRESS", 1.3f, new Color(1f, 0.93f, 0.8f), 4);
        for (int i = 0; i < 3; i++)
            MatchKit.Box(root, Ticket + new Vector2(-0.55f, 0.1f - i * 0.3f), new Vector2(1.6f, 0.06f), new Color(0.47f, 0.38f, 0.24f), 3);
        MatchKit.Text(root, Ticket + new Vector2(-0.55f, -0.65f), "VALID FOR ONE JOURNEY", 0.95f, new Color(0.47f, 0.38f, 0.24f), 4);
        // Lochfeld (hier kommt das Loch hin)
        MatchKit.Symbol(root, Ticket + new Vector2(1.05f, -0.25f), 2, 0.46f, new Color(0.47f, 0.38f, 0.24f, 0.35f), 3);
        _hole = MatchKit.Symbol(root, Ticket + new Vector2(1.05f, -0.25f), 2, 0.4f, new Color(0.08f, 0.07f, 0.07f, 0f), 5);
        // Zange: Unterteil fest, Oberteil dreht um Jaw und drueckt den Stempelkopf auf das Lochfeld
        MatchKit.Box(root, new Vector2(1.6f, -0.95f), new Vector2(2.2f, 0.28f), new Color(0.2f, 0.2f, 0.23f), 4);
        MatchKit.Box(root, new Vector2(0.7f, -0.6f), new Vector2(0.3f, 0.5f), new Color(0.26f, 0.26f, 0.3f), 4);
        var up = new GameObject("jaw") { layer = 5 };
        up.transform.SetParent(root, false);
        up.transform.localPosition = new Vector3(Jaw.x, Jaw.y, -0.07f);
        _upper = up.transform;
        MatchKit.Box(_upper, new Vector2(0.9f, 0f), new Vector2(2.4f, 0.26f), new Color(0.33f, 0.33f, 0.38f), 7);
        MatchKit.Box(_upper, new Vector2(1.55f, 0f), new Vector2(0.9f, 0.34f), new Color(0.76f, 0.6f, 0.26f), 8);   // Messinggriff
        MatchKit.Box(_upper, new Vector2(0.1f, -0.3f), new Vector2(0.22f, 0.5f), new Color(0.33f, 0.33f, 0.38f), 7);  // Stempelstift
        MatchKit.Symbol(root, Jaw, 2, 0.2f, new Color(0.6f, 0.5f, 0.3f), 9);
        MatchKit.Text(root, Grip + new Vector2(0f, -0.55f), "HOLD THE GRIP", 1.1f, new Color(0.85f, 0.85f, 0.9f), 6);
        // Fortschritt und Restzeit unten
        MatchKit.Box(root, new Vector2(0f, -2.05f), new Vector2(6.1f, 0.34f), new Color(0.05f, 0.06f, 0.09f, 0.95f), 6);
        _fill = MatchKit.Box(root, new Vector2(-3.0f, -2.05f), new Vector2(0.01f, 0.24f), new Color(0.95f, 0.75f, 0.35f), 7);
        _timer = MatchKit.Text(root, new Vector2(0f, -2.04f), "", 1.35f, Color.white, 8);
        _msg = MatchKit.Text(root, new Vector2(0f, 1.3f), "", 1.7f, Color.white, 6);
        Apply();
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        if (!AtlasTicket.Active && AtlasMinigame.DiagStep < 0) { Leave = true; return; }
        if (_stamped)
        {
            if (Time.time >= _doneAt) Leave = true;
            Apply();
            return;
        }
        bool onGrip = down && MatchKit.In(mouse, Grip, new Vector2(0.9f, 0.6f));
        _hold = onGrip ? Mathf.Min(AtlasTicket.PunchHold, _hold + dt) : Mathf.Max(0f, _hold - dt * 2.5f);
        if (_hold >= AtlasTicket.PunchHold)
        {
            _stamped = true;
            _doneAt = Time.time + 0.8f;
            AtlasTicket.Stamp();
        }
        _msg.text = _stamped ? "STAMPED" : onGrip ? "PUNCHING" : "HOLD THE GRIP";
        _msg.color = _stamped ? new Color(0.5f, 1f, 0.6f) : onGrip ? new Color(1f, 0.85f, 0.45f) : Color.white;
        Apply();
    }

    private void Apply()
    {
        float t = Progress;
        _upper.localRotation = Quaternion.Euler(0f, 0f, -28f * (1f - t));
        var c = _hole.color; c.a = _stamped ? 1f : 0f; _hole.color = c;
        float w = Mathf.Max(0.01f, 6.0f * t);
        _fill.transform.localScale = new Vector3(w / 0.16f, 0.24f / 0.16f, 1f);
        var p = _fill.transform.localPosition;
        _fill.transform.localPosition = new Vector3(-3.0f + w / 2f, p.y, p.z);
        _timer.text = $"CONDUCTOR IN {Mathf.CeilToInt(AtlasTicket.TimeLeft)}s";
        if (_stamped) _msg.text = "STAMPED";
    }

    // Autotest: Maus auf den Griff und halten
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        mouse = Grip;
        down = true;
    }

    public void Dispose() { }
}
