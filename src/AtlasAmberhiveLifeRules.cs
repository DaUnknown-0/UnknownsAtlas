// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
// Reine Zeit-/Bewegungsregeln, auch ohne Unity und ohne Spielstart pruefbar.
using System;

namespace UnknownsAtlas;

internal static class AmberhiveLifeRules
{
    internal const float Lifetime = 6f, Coating = 6f, StepGap = .34f;

    internal static float LampLevel(float from, bool dark, int index, float age)
    {
        float k = Math.Clamp((age - index * .13f) / .45f, 0f, 1f);
        k = k * k * (3f - 2f * k);
        return from + ((dark ? 0f : 1f) - from) * k;
    }
}

internal readonly record struct AmberhiveLifeStep(float X, float Y, float Angle);

internal sealed class AmberhivePollenWalker
{
    internal float X { get; private set; }
    internal float Y { get; private set; }
    private float _at, _stepX, _stepY, _stepAt, _pollenUntil, _blockUntil;
    private bool _left;

    internal AmberhivePollenWalker(float x, float y, float now)
    {
        X = _stepX = x; Y = _stepY = y; _at = _stepAt = now; _blockUntil = now + .25f;
    }

    internal bool Sample(float x, float y, float now, bool inPollen, bool clearLine, out AmberhiveLifeStep step)
    {
        step = default;
        if (!float.IsFinite(x) || !float.IsFinite(y) || !float.IsFinite(now) || now < _at) return false;
        float elapsed = Math.Max(.01f, now - _at);
        float dx = x - X, dy = y - Y;
        bool jump = MathF.Sqrt(dx * dx + dy * dy) > Math.Min(1.4f, .45f + elapsed * 8f) || !clearLine;
        X = x; Y = y; _at = now;
        if (jump)
        {
            _pollenUntil = 0f; _stepX = x; _stepY = y; _blockUntil = now + .5f;
            return false;
        }
        if (now < _blockUntil) return false;
        if (inPollen) _pollenUntil = now + AmberhiveLifeRules.Coating;
        dx = x - _stepX; dy = y - _stepY;
        float distance = MathF.Sqrt(dx * dx + dy * dy);
        if (_pollenUntil <= now || now - _stepAt < AmberhiveLifeRules.StepGap || distance < .4f) return false;
        _left = !_left;
        float side = _left ? .1f : -.1f;
        step = new AmberhiveLifeStep(x - dy / distance * side, y + dx / distance * side,
            MathF.Atan2(dy, dx) * (180f / MathF.PI) - 90f);
        _stepX = x; _stepY = y; _stepAt = now;
        return true;
    }
}
