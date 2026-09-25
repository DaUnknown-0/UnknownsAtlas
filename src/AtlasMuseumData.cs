// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AUTOMATISCH ERZEUGT von tools/gen_museum.py aus tools/museum_layout.py - NICHT VON HAND
// AENDERN. Koordinaten = Weltmeter (Museum (0,0) = Welt (0,0), Norden = +y).

using UnityEngine;

namespace UnknownsAtlas;

public static class AtlasMuseumData
{
    public const float MinX = -24.50f, MinY = -14.00f, MaxX = 29.00f, MaxY = 17.50f;

    /// <summary>Bewegungskanten (Ship): begehbare Flaeche, vor Nordwaenden um 0,3 m zurueckgenommen.</summary>
    public static readonly Vector2[][] Walls =
    {
        new Vector2[] { new(-15.400f, -7.900f), new(-15.400f, -0.800f), new(-11.500f, -0.800f), new(-11.500f, -0.500f), new(-11.500f, -0.300f), new(-11.500f, 0.000f), new(-15.400f, 0.000f), new(-15.400f, 2.700f), new(-15.400f, 3.000f), new(-15.900f, 3.000f), new(-15.900f, 2.700f), new(-15.900f, -3.000f), new(-18.400f, -3.000f), new(-18.400f, -3.300f), new(-18.400f, -3.500f), new(-18.400f, -3.800f), new(-15.900f, -3.800f), new(-15.900f, -5.000f), new(-15.900f, -5.300f), new(-15.400f, -5.300f), new(-15.400f, -7.500f), new(-15.900f, -7.500f), new(-15.900f, -7.800f), new(-15.900f, -11.500f), new(-23.300f, -11.500f), new(-23.300f, -3.800f), new(-20.900f, -3.800f), new(-20.900f, -3.500f), new(-20.900f, -3.300f), new(-20.900f, -3.000f), new(-23.300f, -3.000f), new(-23.300f, 7.700f), new(-15.900f, 7.700f), new(-15.900f, 5.500f), new(-15.900f, 5.200f), new(-15.400f, 5.200f), new(-15.400f, 5.500f), new(-15.400f, 7.700f), new(-15.000f, 7.700f), new(-15.000f, 8.000f), new(-15.000f, 8.200f), new(-15.000f, 8.500f), new(-17.400f, 8.500f), new(-17.400f, 16.200f), new(-8.500f, 16.200f), new(-8.500f, 15.000f), new(-8.500f, 14.700f), new(-8.000f, 14.700f), new(-5.000f, 14.700f), new(-4.500f, 14.700f), new(-4.500f, 15.000f), new(-4.500f, 16.200f), new(4.500f, 16.200f), new(4.500f, 15.000f), new(4.500f, 14.700f), new(5.000f, 14.700f), new(8.500f, 14.700f), new(9.000f, 14.700f), new(9.000f, 15.000f), new(9.000f, 16.100f), new(18.000f, 16.100f), new(18.000f, 10.000f), new(14.500f, 10.000f), new(14.500f, 9.700f), new(14.500f, 9.500f), new(14.500f, 9.200f), new(19.500f, 9.200f), new(19.500f, 5.000f), new(19.500f, 4.700f), new(20.000f, 4.700f), new(20.000f, 5.000f), new(20.000f, 7.700f), new(20.000f, 8.000f), new(20.000f, 9.200f), new(23.000f, 9.200f), new(27.900f, 9.200f), new(27.900f, 0.200f), new(23.000f, 0.200f), new(22.800f, 0.200f), new(22.800f, -0.100f), new(22.800f, -0.300f), new(22.800f, -0.600f), new(27.900f, -0.600f), new(27.900f, -7.400f), new(20.000f, -7.400f), new(20.000f, -4.800f), new(20.000f, -4.500f), new(19.500f, -4.500f), new(19.500f, -4.800f), new(19.500f, -6.000f), new(8.500f, -6.000f), new(8.500f, -5.750f), new(8.000f, -5.750f), new(8.000f, -6.050f), new(8.000f, -13.000f), new(-2.500f, -13.000f), new(-8.000f, -13.000f), new(-8.000f, -9.800f), new(-8.000f, -9.500f), new(-8.000f, -6.550f), new(-8.000f, -6.250f), new(-8.500f, -6.250f), new(-8.500f, -6.550f), new(-8.500f, -7.900f) },
        new Vector2[] { new(19.500f, -2.000f), new(19.500f, -2.300f), new(20.000f, -2.300f), new(20.000f, -2.000f), new(20.000f, -0.600f), new(20.300f, -0.600f), new(20.300f, -0.300f), new(20.300f, -0.100f), new(20.300f, 0.200f), new(20.000f, 0.200f), new(20.000f, 0.700f), new(20.000f, 1.000f), new(19.500f, 1.000f), new(16.500f, 1.000f), new(16.500f, 0.700f), new(16.500f, 0.500f), new(16.500f, 0.200f), new(19.500f, 0.200f) },
        new Vector2[] { new(8.500f, 0.200f), new(14.000f, 0.200f), new(14.000f, 0.500f), new(14.000f, 0.700f), new(14.000f, 1.000f), new(7.000f, 1.000f), new(7.000f, 1.700f), new(7.000f, 2.000f), new(6.500f, 2.000f), new(6.500f, 1.700f), new(6.500f, 1.310f), new(2.690f, -2.500f), new(2.000f, -2.500f), new(2.000f, -2.800f), new(2.000f, -3.000f), new(2.000f, -3.300f), new(8.000f, -3.300f), new(8.000f, -3.550f), new(8.500f, -3.550f), new(8.500f, -3.250f) },
        new Vector2[] { new(1.500f, 11.000f), new(1.500f, 10.700f), new(1.500f, 10.500f), new(1.500f, 10.200f), new(2.690f, 10.200f), new(6.500f, 6.390f), new(6.500f, 6.000f), new(6.500f, 5.700f), new(7.000f, 5.700f), new(7.000f, 6.000f), new(7.000f, 9.200f), new(12.000f, 9.200f), new(12.000f, 9.500f), new(12.000f, 9.700f), new(12.000f, 10.000f), new(9.000f, 10.000f), new(9.000f, 12.200f), new(9.000f, 12.500f), new(8.500f, 12.500f), new(5.000f, 12.500f), new(4.500f, 12.500f), new(4.500f, 12.200f), new(4.500f, 11.000f) },
        new Vector2[] { new(-4.500f, 12.200f), new(-4.500f, 12.500f), new(-5.000f, 12.500f), new(-8.000f, 12.500f), new(-8.500f, 12.500f), new(-8.500f, 12.200f), new(-8.500f, 8.500f), new(-12.500f, 8.500f), new(-12.500f, 8.200f), new(-12.500f, 8.000f), new(-12.500f, 7.700f), new(-7.000f, 7.700f), new(-7.000f, 6.000f), new(-7.000f, 5.700f), new(-6.500f, 5.700f), new(-6.500f, 6.000f), new(-6.500f, 6.390f), new(-2.690f, 10.200f), new(-1.500f, 10.200f), new(-1.500f, 10.500f), new(-1.500f, 10.700f), new(-1.500f, 11.000f), new(-4.500f, 11.000f) },
        new Vector2[] { new(-7.000f, 1.700f), new(-7.000f, 0.000f), new(-9.000f, 0.000f), new(-9.000f, -0.300f), new(-9.000f, -0.500f), new(-9.000f, -0.800f), new(-8.500f, -0.800f), new(-8.500f, -3.750f), new(-8.500f, -4.050f), new(-8.000f, -4.050f), new(-8.000f, -3.750f), new(-8.000f, -3.300f), new(-2.000f, -3.300f), new(-2.000f, -3.000f), new(-2.000f, -2.800f), new(-2.000f, -2.500f), new(-2.690f, -2.500f), new(-6.500f, 1.310f), new(-6.500f, 1.700f), new(-6.500f, 2.000f), new(-7.000f, 2.000f) },
    };

    /// <summary>Schattenkanten (Shadow): begehbare Flaeche plus Stirnseite der Nordwaende.</summary>
    public static readonly Vector2[][] ShadowWalls =
    {
        new Vector2[] { new(-15.400f, -7.900f), new(-15.400f, -7.450f), new(-15.400f, -0.500f), new(-15.400f, -0.050f), new(-11.500f, -0.050f), new(-11.500f, 0.000f), new(-15.400f, 0.000f), new(-15.400f, 0.450f), new(-15.400f, 3.000f), new(-15.900f, 3.000f), new(-15.900f, -2.550f), new(-15.900f, -3.000f), new(-18.400f, -3.000f), new(-18.400f, -3.050f), new(-15.900f, -3.050f), new(-15.900f, -3.500f), new(-15.900f, -4.550f), new(-15.400f, -4.550f), new(-15.400f, -5.000f), new(-15.400f, -7.050f), new(-15.400f, -7.500f), new(-15.900f, -7.500f), new(-15.900f, -11.050f), new(-15.900f, -11.500f), new(-23.300f, -11.500f), new(-23.300f, -11.050f), new(-23.300f, -3.500f), new(-23.300f, -3.050f), new(-20.900f, -3.050f), new(-20.900f, -3.000f), new(-23.300f, -3.000f), new(-23.300f, -2.550f), new(-23.300f, 8.000f), new(-23.300f, 8.450f), new(-15.900f, 8.450f), new(-15.900f, 8.000f), new(-15.900f, 5.950f), new(-15.400f, 5.950f), new(-15.400f, 8.000f), new(-15.400f, 8.450f), new(-15.000f, 8.450f), new(-15.000f, 8.500f), new(-17.400f, 8.500f), new(-17.400f, 8.950f), new(-17.400f, 16.500f), new(-17.400f, 16.950f), new(-8.500f, 16.950f), new(-8.500f, 16.500f), new(-8.500f, 15.450f), new(-8.000f, 15.450f), new(-5.000f, 15.450f), new(-4.500f, 15.450f), new(-4.500f, 16.500f), new(-4.500f, 16.950f), new(4.500f, 16.950f), new(4.500f, 16.500f), new(4.500f, 15.450f), new(5.000f, 15.450f), new(8.500f, 15.450f), new(9.000f, 15.450f), new(9.000f, 16.400f), new(9.000f, 16.850f), new(18.000f, 16.850f), new(18.000f, 16.400f), new(18.000f, 10.450f), new(18.000f, 10.000f), new(14.500f, 10.000f), new(14.500f, 9.950f), new(19.500f, 9.950f), new(19.500f, 9.500f), new(19.500f, 5.450f), new(20.000f, 5.450f), new(20.000f, 8.000f), new(20.000f, 8.450f), new(20.000f, 9.500f), new(20.000f, 9.950f), new(23.000f, 9.950f), new(27.900f, 9.950f), new(27.900f, 9.500f), new(27.900f, 0.650f), new(27.900f, 0.200f), new(23.000f, 0.200f), new(22.800f, 0.200f), new(22.800f, 0.150f), new(27.900f, 0.150f), new(27.900f, -0.300f), new(27.900f, -6.950f), new(27.900f, -7.400f), new(20.000f, -7.400f), new(20.000f, -6.950f), new(20.000f, -4.500f), new(19.500f, -4.500f), new(19.500f, -5.550f), new(19.500f, -6.000f), new(8.500f, -6.000f), new(8.500f, -5.750f), new(8.000f, -5.750f), new(8.000f, -12.550f), new(8.000f, -13.000f), new(-2.500f, -13.000f), new(-8.000f, -13.000f), new(-8.000f, -12.550f), new(-8.000f, -9.500f), new(-8.000f, -9.050f), new(-8.000f, -6.250f), new(-8.500f, -6.250f), new(-8.500f, -7.450f), new(-8.500f, -7.900f) },
        new Vector2[] { new(19.500f, -1.550f), new(20.000f, -1.550f), new(20.000f, -0.300f), new(20.000f, 0.150f), new(20.300f, 0.150f), new(20.300f, 0.200f), new(20.000f, 0.200f), new(20.000f, 0.650f), new(20.000f, 1.000f), new(19.500f, 1.000f), new(16.500f, 1.000f), new(16.500f, 0.950f), new(19.500f, 0.950f), new(19.500f, 0.500f) },
        new Vector2[] { new(8.500f, 0.500f), new(8.500f, 0.950f), new(14.000f, 0.950f), new(14.000f, 1.000f), new(7.000f, 1.000f), new(7.000f, 1.450f), new(7.000f, 2.000f), new(6.500f, 2.000f), new(6.500f, 1.760f), new(6.500f, 1.310f), new(2.690f, -2.500f), new(2.000f, -2.500f), new(2.000f, -2.550f), new(8.000f, -2.550f), new(8.000f, -2.800f), new(8.500f, -2.800f) },
        new Vector2[] { new(1.500f, 11.000f), new(1.500f, 10.950f), new(2.690f, 10.950f), new(6.500f, 7.140f), new(6.500f, 6.690f), new(6.500f, 6.450f), new(7.000f, 6.450f), new(7.000f, 9.500f), new(7.000f, 9.950f), new(12.000f, 9.950f), new(12.000f, 10.000f), new(9.000f, 10.000f), new(9.000f, 10.450f), new(9.000f, 12.500f), new(8.500f, 12.500f), new(5.000f, 12.500f), new(4.500f, 12.500f), new(4.500f, 11.450f), new(4.500f, 11.000f) },
        new Vector2[] { new(-4.500f, 11.450f), new(-4.500f, 12.500f), new(-5.000f, 12.500f), new(-8.000f, 12.500f), new(-8.500f, 12.500f), new(-8.500f, 8.950f), new(-8.500f, 8.500f), new(-12.500f, 8.500f), new(-12.500f, 8.450f), new(-7.000f, 8.450f), new(-7.000f, 8.000f), new(-7.000f, 6.450f), new(-6.500f, 6.450f), new(-6.500f, 6.690f), new(-6.500f, 7.140f), new(-2.690f, 10.950f), new(-1.500f, 10.950f), new(-1.500f, 11.000f), new(-4.500f, 11.000f) },
        new Vector2[] { new(-7.000f, 0.450f), new(-7.000f, 0.000f), new(-9.000f, 0.000f), new(-9.000f, -0.050f), new(-8.500f, -0.050f), new(-8.500f, -0.500f), new(-8.500f, -3.300f), new(-8.000f, -3.300f), new(-8.000f, -3.000f), new(-8.000f, -2.550f), new(-2.000f, -2.550f), new(-2.000f, -2.500f), new(-2.690f, -2.500f), new(-6.500f, 1.310f), new(-6.500f, 1.760f), new(-6.500f, 2.000f), new(-7.000f, 2.000f) },
    };

    /// <summary>Hindernisse, die Weg UND Sicht sperren (Ship + Shadow).</summary>
    public static readonly Vector2[][] Opaque =
    {
        new Vector2[] { new(6.600f, -12.600f), new(8.000f, -12.600f), new(8.000f, -10.900f), new(6.600f, -10.900f) },
        new Vector2[] { new(-8.000f, -9.400f), new(-7.400f, -9.400f), new(-7.400f, -6.700f), new(-8.000f, -6.700f) },
        new Vector2[] { new(-8.000f, -11.700f), new(-7.300f, -11.700f), new(-7.300f, -10.100f), new(-8.000f, -10.100f) },
        new Vector2[] { new(-15.400f, -4.200f), new(-15.000f, -4.200f), new(-15.000f, -1.200f), new(-15.400f, -1.200f) },
        new Vector2[] { new(-23.300f, -10.600f), new(-22.500f, -10.600f), new(-22.500f, -7.600f), new(-23.300f, -7.600f) },
        new Vector2[] { new(-20.950f, -7.500f), new(-20.984f, -7.328f), new(-21.082f, -7.182f), new(-21.228f, -7.084f), new(-21.400f, -7.050f), new(-21.572f, -7.084f), new(-21.718f, -7.182f), new(-21.816f, -7.328f), new(-21.850f, -7.500f), new(-21.816f, -7.672f), new(-21.718f, -7.818f), new(-21.572f, -7.916f), new(-21.400f, -7.950f), new(-21.228f, -7.916f), new(-21.082f, -7.818f), new(-20.984f, -7.672f) },
        new Vector2[] { new(-22.500f, 3.400f), new(-21.600f, 3.400f), new(-21.600f, 5.600f), new(-22.500f, 5.600f) },
        new Vector2[] { new(-22.500f, -2.600f), new(-21.600f, -2.600f), new(-21.600f, -0.400f), new(-22.500f, -0.400f) },
        new Vector2[] { new(-12.900f, 5.300f), new(-12.700f, 5.300f), new(-12.700f, 7.500f), new(-12.900f, 7.500f) },
        new Vector2[] { new(-12.900f, 0.500f), new(-12.700f, 0.500f), new(-12.700f, 2.700f), new(-12.900f, 2.700f) },
        new Vector2[] { new(-14.000f, 13.200f), new(-14.034f, 13.372f), new(-14.132f, 13.518f), new(-14.278f, 13.616f), new(-14.450f, 13.650f), new(-14.622f, 13.616f), new(-14.768f, 13.518f), new(-14.866f, 13.372f), new(-14.900f, 13.200f), new(-14.866f, 13.028f), new(-14.768f, 12.882f), new(-14.622f, 12.784f), new(-14.450f, 12.750f), new(-14.278f, 12.784f), new(-14.132f, 12.882f), new(-14.034f, 13.028f) },
        new Vector2[] { new(9.500f, 15.400f), new(15.500f, 15.400f), new(15.500f, 16.400f), new(9.500f, 16.400f) },
        new Vector2[] { new(17.400f, 10.000f), new(18.000f, 10.000f), new(18.000f, 15.000f), new(17.400f, 15.000f) },
        new Vector2[] { new(10.800f, 2.300f), new(11.200f, 2.300f), new(11.200f, 2.700f), new(10.800f, 2.700f) },
        new Vector2[] { new(16.800f, 2.300f), new(17.200f, 2.300f), new(17.200f, 2.700f), new(16.800f, 2.700f) },
        new Vector2[] { new(9.000f, 5.000f), new(13.000f, 5.000f), new(13.000f, 7.000f), new(9.000f, 7.000f) },
        new Vector2[] { new(15.000f, 5.500f), new(19.000f, 5.500f), new(19.000f, 8.500f), new(15.000f, 8.500f) },
        new Vector2[] { new(8.500f, -2.600f), new(9.100f, -2.600f), new(9.100f, -0.800f), new(8.500f, -0.800f) },
        new Vector2[] { new(21.500f, -3.800f), new(26.700f, -3.800f), new(26.700f, -2.600f), new(21.500f, -2.600f) },
        new Vector2[] { new(24.500f, 0.400f), new(27.100f, 0.400f), new(27.100f, 5.900f), new(24.500f, 5.900f) },
    };

    /// <summary>Wirft Hindernis j einen Schatten? (false = steht an einer Wand)</summary>
    public static readonly bool[] OpaqueCastsShadow = { false, false, false, false, false, true, true, true, true, true, true, false, false, true, true, true, true, false, true, true };

    /// <summary>Hindernisse, die nur den Weg sperren (ShortObjects, kein Schatten).</summary>
    public static readonly Vector2[][] Glass =
    {
        new Vector2[] { new(3.200f, 4.000f), new(3.167f, 4.141f), new(3.068f, 4.278f), new(2.906f, 4.409f), new(2.684f, 4.529f), new(2.409f, 4.636f), new(2.087f, 4.728f), new(1.726f, 4.802f), new(1.334f, 4.856f), new(0.922f, 4.889f), new(0.500f, 4.900f), new(0.078f, 4.889f), new(-0.334f, 4.856f), new(-0.726f, 4.802f), new(-1.087f, 4.728f), new(-1.409f, 4.636f), new(-1.684f, 4.529f), new(-1.906f, 4.409f), new(-2.068f, 4.278f), new(-2.167f, 4.141f), new(-2.200f, 4.000f), new(-2.167f, 3.859f), new(-2.068f, 3.722f), new(-1.906f, 3.591f), new(-1.684f, 3.471f), new(-1.409f, 3.364f), new(-1.087f, 3.272f), new(-0.726f, 3.198f), new(-0.334f, 3.144f), new(0.078f, 3.111f), new(0.500f, 3.100f), new(0.922f, 3.111f), new(1.334f, 3.144f), new(1.726f, 3.198f), new(2.087f, 3.272f), new(2.409f, 3.364f), new(2.684f, 3.471f), new(2.906f, 3.591f), new(3.068f, 3.722f), new(3.167f, 3.859f) },
        new Vector2[] { new(1.880f, 2.200f), new(1.859f, 2.307f), new(1.798f, 2.398f), new(1.707f, 2.459f), new(1.600f, 2.480f), new(1.493f, 2.459f), new(1.402f, 2.398f), new(1.341f, 2.307f), new(1.320f, 2.200f), new(1.341f, 2.093f), new(1.402f, 2.002f), new(1.493f, 1.941f), new(1.600f, 1.920f), new(1.707f, 1.941f), new(1.798f, 2.002f), new(1.859f, 2.093f) },
        new Vector2[] { new(-10.120f, -3.600f), new(-10.141f, -3.493f), new(-10.202f, -3.402f), new(-10.293f, -3.341f), new(-10.400f, -3.320f), new(-10.507f, -3.341f), new(-10.598f, -3.402f), new(-10.659f, -3.493f), new(-10.680f, -3.600f), new(-10.659f, -3.707f), new(-10.598f, -3.798f), new(-10.507f, -3.859f), new(-10.400f, -3.880f), new(-10.293f, -3.859f), new(-10.202f, -3.798f), new(-10.141f, -3.707f) },
        new Vector2[] { new(3.600f, 7.000f), new(4.800f, 7.000f), new(4.800f, 7.800f), new(3.600f, 7.800f) },
        new Vector2[] { new(-4.800f, 0.100f), new(-3.600f, 0.100f), new(-3.600f, 0.900f), new(-4.800f, 0.900f) },
        new Vector2[] { new(3.600f, 0.100f), new(4.800f, 0.100f), new(4.800f, 0.900f), new(3.600f, 0.900f) },
        new Vector2[] { new(-1.000f, 14.500f), new(1.000f, 14.500f), new(1.000f, 16.500f), new(-1.000f, 16.500f) },
        new Vector2[] { new(-3.800f, 12.400f), new(-2.200f, 12.400f), new(-2.200f, 13.200f), new(-3.800f, 13.200f) },
        new Vector2[] { new(2.200f, 12.400f), new(3.800f, 12.400f), new(3.800f, 13.200f), new(2.200f, 13.200f) },
        new Vector2[] { new(2.200f, -8.000f), new(2.173f, -7.750f), new(2.092f, -7.506f), new(1.960f, -7.274f), new(1.780f, -7.060f), new(1.556f, -6.869f), new(1.293f, -6.706f), new(0.999f, -6.574f), new(0.680f, -6.478f), new(0.344f, -6.420f), new(0.000f, -6.400f), new(-0.344f, -6.420f), new(-0.680f, -6.478f), new(-0.999f, -6.574f), new(-1.293f, -6.706f), new(-1.556f, -6.869f), new(-1.780f, -7.060f), new(-1.960f, -7.274f), new(-2.092f, -7.506f), new(-2.173f, -7.750f), new(-2.200f, -8.000f), new(-2.173f, -8.250f), new(-2.092f, -8.494f), new(-1.960f, -8.726f), new(-1.780f, -8.940f), new(-1.556f, -9.131f), new(-1.293f, -9.294f), new(-0.999f, -9.426f), new(-0.680f, -9.522f), new(-0.344f, -9.580f), new(-0.000f, -9.600f), new(0.344f, -9.580f), new(0.680f, -9.522f), new(0.999f, -9.426f), new(1.293f, -9.294f), new(1.556f, -9.131f), new(1.780f, -8.940f), new(1.960f, -8.726f), new(2.092f, -8.494f), new(2.173f, -8.250f) },
        new Vector2[] { new(-4.600f, -4.200f), new(-3.400f, -4.200f), new(-3.400f, -3.400f), new(-4.600f, -3.400f) },
        new Vector2[] { new(3.400f, -4.200f), new(4.600f, -4.200f), new(4.600f, -3.400f), new(3.400f, -3.400f) },
        new Vector2[] { new(-7.000f, -5.200f), new(-5.200f, -5.200f), new(-5.200f, -4.700f), new(-7.000f, -4.700f) },
        new Vector2[] { new(5.200f, -5.200f), new(7.000f, -5.200f), new(7.000f, -4.700f), new(5.200f, -4.700f) },
        new Vector2[] { new(-6.400f, -12.700f), new(-3.000f, -12.700f), new(-3.000f, -11.700f), new(-6.400f, -11.700f) },
        new Vector2[] { new(-13.800f, -7.900f), new(-11.200f, -7.900f), new(-11.200f, -6.800f), new(-13.800f, -6.800f) },
        new Vector2[] { new(-19.900f, -6.400f), new(-18.100f, -6.400f), new(-18.100f, -5.000f), new(-19.900f, -5.000f) },
        new Vector2[] { new(-19.400f, 6.500f), new(-17.800f, 6.500f), new(-17.800f, 7.300f), new(-19.400f, 7.300f) },
        new Vector2[] { new(-19.400f, 2.500f), new(-17.800f, 2.500f), new(-17.800f, 3.300f), new(-19.400f, 3.300f) },
        new Vector2[] { new(-19.400f, -1.500f), new(-17.800f, -1.500f), new(-17.800f, -0.700f), new(-19.400f, -0.700f) },
        new Vector2[] { new(-17.100f, 0.400f), new(-16.100f, 0.400f), new(-16.100f, 1.400f), new(-17.100f, 1.400f) },
        new Vector2[] { new(-11.800f, 3.750f), new(-10.000f, 3.750f), new(-10.000f, 4.250f), new(-11.800f, 4.250f) },
        new Vector2[] { new(10.000f, 11.500f), new(14.000f, 11.500f), new(14.000f, 12.500f), new(10.000f, 12.500f) },
        new Vector2[] { new(14.600f, 6.000f), new(14.524f, 6.383f), new(14.307f, 6.707f), new(13.983f, 6.924f), new(13.600f, 7.000f), new(13.217f, 6.924f), new(12.893f, 6.707f), new(12.676f, 6.383f), new(12.600f, 6.000f), new(12.676f, 5.617f), new(12.893f, 5.293f), new(13.217f, 5.076f), new(13.600f, 5.000f), new(13.983f, 5.076f), new(14.307f, 5.293f), new(14.524f, 5.617f) },
        new Vector2[] { new(9.000f, -0.400f), new(13.500f, -0.400f), new(13.500f, 0.400f), new(9.000f, 0.400f) },
        new Vector2[] { new(17.000f, -0.400f), new(19.300f, -0.400f), new(19.300f, 0.400f), new(17.000f, 0.400f) },
        new Vector2[] { new(12.500f, -6.000f), new(12.700f, -6.000f), new(12.700f, -3.000f), new(12.500f, -3.000f) },
        new Vector2[] { new(25.500f, -5.400f), new(26.700f, -5.400f), new(26.700f, -4.400f), new(25.500f, -4.400f) },
        new Vector2[] { new(22.950f, 0.200f), new(23.050f, 0.200f), new(23.050f, 6.000f), new(22.950f, 6.000f) },
        new Vector2[] { new(20.000f, 7.950f), new(23.000f, 7.950f), new(23.000f, 8.050f), new(20.000f, 8.050f) },
    };

    /// <summary>Raeume: Schluessel, Anzeigename, SystemTypes-Traeger, Umriss.</summary>
    public static readonly (string Key, string Name, SystemTypes Room, Vector2[] Area)[] Rooms =
    {
        ("rotunde", "Rotunda", SystemTypes.LifeSupp, new Vector2[] { new(2.690f, -2.500f), new(6.500f, 1.310f), new(6.500f, 6.690f), new(2.690f, 10.500f), new(-2.690f, 10.500f), new(-6.500f, 6.690f), new(-6.500f, 1.310f), new(-2.690f, -2.500f) }),
        ("nische", "Rotunda", SystemTypes.Shields, new Vector2[] { new(-4.500f, 11.000f), new(4.500f, 11.000f), new(4.500f, 16.500f), new(-4.500f, 16.500f) }),
        ("foyer", "Foyer", SystemTypes.Cafeteria, new Vector2[] { new(-8.000f, -9.500f), new(-2.500f, -9.500f), new(-2.500f, -13.000f), new(8.000f, -13.000f), new(8.000f, -3.000f), new(-8.000f, -3.000f) }),
        ("shop", "Foyer", SystemTypes.Admin, new Vector2[] { new(-8.000f, -13.000f), new(-2.500f, -13.000f), new(-2.500f, -9.500f), new(-8.000f, -9.500f) }),
        ("sicherheit", "Security Office", SystemTypes.Security, new Vector2[] { new(-15.400f, -7.900f), new(-8.500f, -7.900f), new(-8.500f, -0.500f), new(-15.400f, -0.500f) }),
        ("haustechnik", "Utilities", SystemTypes.Electrical, new Vector2[] { new(-23.300f, -11.500f), new(-15.900f, -11.500f), new(-15.900f, -3.500f), new(-23.300f, -3.500f) }),
        ("aegypten", "Egyptian Hall", SystemTypes.Reactor, new Vector2[] { new(-23.300f, -3.000f), new(-15.900f, -3.000f), new(-15.900f, 8.000f), new(-23.300f, 8.000f) }),
        ("galerie", "Gallery", SystemTypes.Weapons, new Vector2[] { new(-15.400f, 0.000f), new(-7.000f, 0.000f), new(-7.000f, 8.000f), new(-15.400f, 8.000f) }),
        ("planetarium", "Planetarium", SystemTypes.Nav, new Vector2[] { new(-17.400f, 8.500f), new(-8.500f, 8.500f), new(-8.500f, 16.500f), new(-17.400f, 16.500f) }),
        ("telefon", "Switchboard", SystemTypes.Comms, new Vector2[] { new(9.000f, 10.000f), new(18.000f, 10.000f), new(18.000f, 16.400f), new(9.000f, 16.400f) }),
        ("technikhalle", "Machine Hall", SystemTypes.UpperEngine, new Vector2[] { new(7.000f, 1.000f), new(19.500f, 1.000f), new(19.500f, 9.500f), new(7.000f, 9.500f) }),
        ("werkstatt", "Restoration", SystemTypes.MedBay, new Vector2[] { new(8.500f, -6.000f), new(19.500f, -6.000f), new(19.500f, 0.500f), new(8.500f, 0.500f) }),
        ("hof", "Depot & Loading Dock", SystemTypes.LowerEngine, new Vector2[] { new(20.000f, 0.200f), new(27.900f, 0.200f), new(27.900f, 9.500f), new(20.000f, 9.500f) }),
        ("depot", "Depot & Loading Dock", SystemTypes.Storage, new Vector2[] { new(20.000f, -7.400f), new(27.900f, -7.400f), new(27.900f, -0.300f), new(20.000f, -0.300f) }),
    };

    public const float PropPixelsPerMeter = 160f;

    /// <summary>Objekt-Sprites: Art, Atlas-Rechteck (x, y von UNTEN, w, h), Welt-Ecke links unten,
    /// Standlinie (z-Sortierung wie Spieler: z = y / 1000).
    /// FootX0/FootX1 = Grundflaeche ohne Schattenrand (fuer die Durchsicht-Blende).</summary>
    public static readonly (string Kind, int Atlas, int X, int Y, int W, int H, float WorldX, float WorldY, float BaseY, float FootX0, float FootX1)[] Props =
    {
        ("kasse", 0, 0, 1636, 320, 535, 6.300f, -12.900f, -12.600f, 6.600f, 8.000f),
        ("garderobe", 0, 2278, 2230, 192, 686, -8.300f, -9.700f, -9.400f, -8.000f, -7.400f),
        ("regal_shop", 0, 1960, 1661, 208, 510, -8.300f, -12.000f, -11.700f, -8.000f, -7.300f),
        ("monitorwand", 0, 2886, 3344, 160, 752, -15.700f, -4.500f, -4.200f, -15.400f, -15.000f),
        ("schaltschrank", 0, 3048, 3344, 224, 752, -23.600f, -10.900f, -10.600f, -23.300f, -22.500f),
        ("kessel", 0, 2268, 1236, 240, 398, -22.150f, -8.250f, -7.950f, -21.850f, -20.950f),
        ("sarkophag", 0, 322, 1644, 240, 527, -22.800f, 3.100f, 3.400f, -22.500f, -21.600f),
        ("sarkophag", 0, 564, 1644, 240, 527, -22.800f, -2.900f, -2.600f, -22.500f, -21.600f),
        ("stellwand", 0, 2472, 2275, 128, 641, -13.200f, 5.000f, 5.300f, -12.900f, -12.700f),
        ("stellwand", 0, 2602, 2275, 128, 641, -13.200f, 0.200f, 0.500f, -12.900f, -12.700f),
        ("projektor", 0, 1768, 1227, 240, 407, -15.200f, 12.450f, 12.750f, -14.900f, -14.000f),
        ("vermittlung", 0, 0, 1202, 1056, 432, 9.200f, 15.100f, 15.400f, 9.500f, 15.500f),
        ("funkregal", 0, 514, 3042, 192, 1054, 17.100f, 9.700f, 10.000f, 17.400f, 18.000f),
        ("stuetze", 0, 1444, 1210, 160, 424, 10.500f, 2.000f, 2.300f, 10.800f, 11.200f),
        ("stuetze", 0, 1606, 1210, 160, 424, 16.500f, 2.000f, 2.300f, 16.800f, 17.200f),
        ("dampfmaschine", 0, 738, 2183, 736, 733, 8.700f, 4.700f, 5.000f, 9.000f, 13.000f),
        ("turbine", 0, 0, 2173, 736, 743, 14.700f, 5.200f, 5.500f, 15.000f, 19.000f),
        ("regal_werk", 0, 3704, 2374, 192, 542, 8.200f, -2.900f, -2.600f, 8.500f, 9.100f),
        ("hochregal", 0, 2170, 1672, 928, 499, 21.200f, -4.100f, -3.800f, 21.500f, 26.700f),
        ("lieferwagen", 0, 0, 2918, 512, 1178, 24.200f, 0.100f, 0.400f, 24.500f, 27.100f),
        ("dino", 0, 806, 1646, 1152, 525, -3.100f, 2.800f, 3.100f, -2.200f, 3.200f),
        ("spieluhr", 0, 1284, 547, 185, 300, 1.020f, 1.620f, 1.920f, 1.320f, 1.880f),
        ("nachtlicht", 0, 1471, 547, 185, 300, -10.980f, -4.180f, -3.880f, -10.680f, -10.120f),
        ("vitrine", 0, 2510, 1269, 288, 365, 3.300f, 6.700f, 7.000f, 3.600f, 4.800f),
        ("vitrine", 0, 2800, 1269, 288, 365, -5.100f, -0.200f, 0.100f, -4.800f, -3.600f),
        ("vitrine", 0, 3090, 1269, 288, 365, 3.300f, -0.200f, 0.100f, 3.600f, 4.800f),
        ("tresorvitrine", 0, 2732, 2315, 416, 601, -1.300f, 14.200f, 14.500f, -1.000f, 1.000f),
        ("tischvitrine", 0, 2184, 888, 352, 312, -4.100f, 12.100f, 12.400f, -3.800f, -2.200f),
        ("tischvitrine", 0, 2538, 888, 352, 312, 1.900f, 12.100f, 12.400f, 2.200f, 3.800f),
        ("infotheke", 0, 1476, 2220, 800, 696, -2.500f, -9.900f, -9.600f, -2.200f, 2.200f),
        ("vitrine", 0, 3380, 1269, 288, 365, -4.900f, -4.500f, -4.200f, -4.600f, -3.400f),
        ("vitrine", 0, 3670, 1269, 288, 365, 3.100f, -4.500f, -4.200f, 3.400f, 4.600f),
        ("bank", 0, 1658, 632, 384, 215, -7.300f, -5.500f, -5.200f, -7.000f, -5.200f),
        ("bank", 0, 2044, 632, 384, 215, 4.900f, -5.500f, -5.200f, 5.200f, 7.000f),
        ("tresen_kasse", 0, 514, 856, 640, 344, -6.700f, -13.000f, -12.700f, -6.400f, -3.000f),
        ("admintisch", 0, 0, 849, 512, 351, -14.100f, -8.200f, -7.900f, -13.800f, -11.200f),
        ("klima", 0, 1058, 1209, 384, 425, -20.200f, -6.700f, -6.400f, -19.900f, -18.100f),
        ("tischvitrine", 0, 2892, 888, 352, 312, -19.700f, 6.200f, 6.500f, -19.400f, -17.800f),
        ("tischvitrine", 0, 3246, 888, 352, 312, -19.700f, 2.200f, 2.500f, -19.400f, -17.800f),
        ("tischvitrine", 0, 3600, 888, 352, 312, -19.700f, -1.800f, -1.500f, -19.400f, -17.800f),
        ("stele", 0, 2010, 1229, 256, 405, -17.400f, 0.100f, 0.400f, -17.100f, -16.100f),
        ("bank", 0, 2430, 632, 384, 215, -12.100f, 3.450f, 3.750f, -11.800f, -10.000f),
        ("vermittlungstisch", 0, 1446, 874, 736, 326, 9.700f, 11.200f, 11.500f, 10.000f, 14.000f),
        ("schwungrad", 0, 3150, 2315, 416, 601, 12.300f, 4.700f, 5.000f, 12.600f, 14.600f),
        ("werktisch", 0, 0, 544, 816, 303, 8.700f, -0.700f, -0.400f, 9.000f, 13.500f),
        ("werktisch", 0, 818, 544, 464, 303, 16.700f, -0.700f, -0.400f, 17.000f, 19.300f),
        ("glaswand", 0, 3274, 3344, 128, 752, 12.200f, -6.300f, -6.000f, 12.500f, 12.700f),
        ("kiste", 0, 1156, 865, 288, 335, 25.200f, -5.700f, -5.400f, 25.500f, 26.700f),
        ("lampe", 0, 3568, 2342, 134, 574, 27.080f, 6.480f, 6.780f, 27.380f, 27.620f),
        ("dino_rex", 0, 708, 3160, 2176, 936, -6.300f, 2.780f, 3.080f, -2.200f, 3.200f),
        ("dino_rex_jaw", 0, 3223, 767, 350, 80, -5.556f, 6.011f, 3.080f, -2.200f, 3.200f),
        ("dino_rex_head", 0, 2816, 636, 405, 211, -5.744f, 6.236f, 3.080f, -2.200f, 3.200f),
    };
    public const int PropAtlasCount = 1;

    public const float FloorPixelsPerMeter = 160f;

    /// <summary>Bodenkacheln: Ressourcen-Index, Welt-Ecke links unten, Pixelmasse.</summary>
    public static readonly (int Index, float WorldX, float WorldY, int W, int H)[] FloorTiles =
    {
        (0, -24.5000f, 9.6250f, 1712, 1260),
        (1, -13.8000f, 9.6250f, 1712, 1260),
        (2, -3.1000f, 9.6250f, 1712, 1260),
        (3, 7.6000f, 9.6250f, 1712, 1260),
        (4, 18.3000f, 9.6250f, 1712, 1260),
        (5, -24.5000f, 1.7500f, 1712, 1260),
        (6, -13.8000f, 1.7500f, 1712, 1260),
        (7, -3.1000f, 1.7500f, 1712, 1260),
        (8, 7.6000f, 1.7500f, 1712, 1260),
        (9, 18.3000f, 1.7500f, 1712, 1260),
        (10, -24.5000f, -6.1250f, 1712, 1260),
        (11, -13.8000f, -6.1250f, 1712, 1260),
        (12, -3.1000f, -6.1250f, 1712, 1260),
        (13, 7.6000f, -6.1250f, 1712, 1260),
        (14, 18.3000f, -6.1250f, 1712, 1260),
        (15, -24.5000f, -14.0000f, 1712, 1260),
        (16, -13.8000f, -14.0000f, 1712, 1260),
        (17, -3.1000f, -14.0000f, 1712, 1260),
        (18, 7.6000f, -14.0000f, 1712, 1260),
        (19, 18.3000f, -14.0000f, 1712, 1260),
    };

    /// <summary>Eigene Task-Bloecke: Schluessel, Atlas, Rechteck (y von UNTEN), Pivot normiert.</summary>
    public static readonly (string Key, int Atlas, int X, int Y, int W, int H, float PivotX, float PivotY)[] ConsoleSprites =
    {
        ("Admin/FixWiringConsole/2", 0, 1169, 495, 211, 186, 0.4408f, 0.4140f),
        ("Admin/NoOxyConsole/1", 0, 1017, 903, 173, 208, 0.4277f, 0.3702f),
        ("Admin/SwipeCardConsole/0", 0, 1774, 1121, 173, 221, 0.4277f, 0.3891f),
        ("Admin/UploadDataConsole/0", 0, 226, 1117, 230, 225, 0.5304f, 0.4400f),
        ("AdminTable", 0, 433, 1349, 198, 260, 0.4343f, 0.3577f),
        ("Cafeteria/DataConsole/2", 0, 458, 1117, 222, 225, 0.3378f, 0.4400f),
        ("Cafeteria/FixWiringConsole/4", 0, 743, 491, 211, 190, 0.4408f, 0.2789f),
        ("Cafeteria/GarbageConsole/2", 0, 888, 688, 185, 200, 0.4324f, 0.2650f),
        ("Comms/DivertPowerConsole/1", 0, 1415, 906, 224, 205, 0.5134f, 0.4390f),
        ("Comms/FixCommsConsole/0", 0, 175, 1346, 256, 263, 0.4492f, 0.3764f),
        ("Comms/UploadDataConsole/1", 0, 682, 1117, 222, 225, 0.3378f, 0.4400f),
        ("Electrical/CalibrateConsole/0", 0, 1192, 905, 221, 206, 0.3982f, 0.2573f),
        ("Electrical/DivertPowerConsole/0", 0, 1641, 906, 216, 205, 0.3472f, 0.4390f),
        ("Electrical/FixWiringConsole/0", 0, 1075, 689, 299, 199, 0.4114f, 0.4322f),
        ("Electrical/SwitchConsole/0", 0, 1196, 1365, 243, 244, 0.5514f, 0.4467f),
        ("Electrical/UploadDataConsole/0", 0, 606, 900, 182, 211, 0.4286f, 0.3649f),
        ("EmergencyButton", 0, 0, 1344, 173, 265, 0.4277f, 0.3509f),
        ("FreeplayLaptop", 0, 1021, 1362, 173, 247, 0.4277f, 0.3765f),
        ("LifeSupp/CleanFilterConsole/0", 0, 1115, 1753, 224, 295, 0.4420f, 0.3254f),
        ("LifeSupp/DivertPowerConsole/1", 0, 0, 484, 198, 197, 0.3788f, 0.2690f),
        ("LifeSupp/GarbageConsole/0", 0, 378, 486, 185, 195, 0.4324f, 0.3949f),
        ("LifeSupp/NoOxyConsole/0", 0, 0, 890, 213, 221, 0.3521f, 0.4434f),
        ("LowerEngine/AlignEngineConsole/1", 0, 633, 1349, 192, 260, 0.4323f, 0.3577f),
        ("LowerEngine/DivertPowerConsole/1", 0, 0, 683, 216, 205, 0.3472f, 0.4390f),
        ("LowerEngine/FuelEngineConsole/0", 0, 1341, 1771, 205, 277, 0.4390f, 0.3357f),
        ("MedBay/MedBayConsole/0", 0, 889, 1752, 224, 296, 0.4420f, 0.3142f),
        ("MedBay/MedScanner/0", 0, 0, 1611, 336, 437, 0.4613f, 0.3593f),
        ("Nav/ChartCourseConsole/0", 0, 215, 892, 214, 219, 0.4393f, 0.2420f),
        ("Nav/DivertPowerConsole/1", 0, 218, 683, 224, 205, 0.5134f, 0.4390f),
        ("Nav/FixWiringConsole/3", 0, 1376, 689, 299, 199, 0.4114f, 0.4322f),
        ("Nav/StabilizeSteeringConsole/0", 0, 1755, 1775, 224, 273, 0.4420f, 0.3516f),
        ("Nav/UploadDataConsole/0", 0, 906, 1117, 230, 225, 0.5304f, 0.4400f),
        ("Reactor/LowerHandConsole/1", 0, 1138, 1117, 221, 225, 0.5068f, 0.4400f),
        ("Reactor/StartReactorConsole/2", 0, 676, 1715, 211, 333, 0.6351f, 0.3754f),
        ("Reactor/UnlockManifoldsConsole/2", 0, 1648, 1380, 173, 229, 0.4277f, 0.3974f),
        ("Reactor/UpperHandConsole/0", 0, 431, 895, 173, 216, 0.4277f, 0.2454f),
        ("Security/DivertPowerConsole/1", 0, 444, 683, 216, 205, 0.3472f, 0.4390f),
        ("Security/FixWiringConsole/5", 0, 956, 491, 211, 190, 0.4408f, 0.2789f),
        ("Shields/DivertPowerConsole/1", 0, 200, 484, 176, 197, 0.4261f, 0.2690f),
        ("Shields/ShieldConsole/0", 0, 1593, 1119, 179, 223, 0.4302f, 0.3946f),
        ("Storage/AirlockConsole/0", 0, 790, 902, 225, 209, 0.3333f, 0.4354f),
        ("Storage/FixWiringConsole/1", 0, 1677, 689, 307, 199, 0.4886f, 0.4322f),
        ("Storage/gasCanConsole/0", 0, 0, 1113, 224, 229, 0.4420f, 0.3624f),
        ("SurveillanceConsole", 0, 338, 1671, 336, 377, 0.4851f, 0.3820f),
        ("UpperEngine/AlignEngineConsole/0", 0, 827, 1349, 192, 260, 0.4323f, 0.3577f),
        ("UpperEngine/DivertPowerConsole/1", 0, 565, 489, 176, 192, 0.4261f, 0.4010f),
        ("UpperEngine/FuelEngineConsole/0", 0, 1548, 1771, 205, 277, 0.4390f, 0.3357f),
        ("Weapons/DivertPowerConsole/1", 0, 662, 683, 224, 205, 0.5134f, 0.4390f),
        ("Weapons/UploadDataConsole/1", 0, 1361, 1117, 230, 225, 0.5304f, 0.4400f),
        ("Weapons/WeaponConsole/0", 0, 1441, 1371, 205, 238, 0.4390f, 0.2227f),
    };

    /// <summary>Beschriftungen der Minimap (Weltmeter): Mitte, halbe Breite/Hoehe. Die Sabotage- und
    /// Tuerknoepfe weichen ihnen aus (AtlasMuseumBuilder.AvoidLabels).</summary>
    public static readonly (float X, float Y, float HalfW, float HalfH)[] MapLabels =
    {
        (-0.021f, 8.600f, 1.812f, 0.333f),
        (2.379f, -11.283f, 1.229f, 0.417f),
        (-11.971f, -4.283f, 3.188f, 0.417f),
        (-19.600f, -7.500f, 1.625f, 0.333f),
        (-19.621f, 2.417f, 2.854f, 0.417f),
        (-11.200f, 3.917f, 1.542f, 0.417f),
        (-12.971f, 12.500f, 2.604f, 0.333f),
        (13.500f, 13.200f, 2.708f, 0.333f),
        (13.250f, 5.250f, 2.750f, 0.333f),
        (14.000f, -2.750f, 2.500f, 0.333f),
        (23.921f, -4.483f, 2.979f, 0.875f),
    };
    /// <summary>Gelenke des T. rex in Weltmetern (AtlasRex): Halsgelenk = Drehpunkt des Kopfes,
    /// Kiefergelenk, Augenhoehle.</summary>
    public static readonly Vector2 RexNeck = new(-3.275f, 6.826f), RexJaw = new(-3.475f, 6.408f), RexEye = new(-4.100f, 7.225f);
    /// <summary>Gaenge als Hallway-Raeume (nur AllRooms, nicht FastRooms).</summary>
    public static readonly Vector2[][] Hallways =
    {
        new Vector2[] { new(-8.000f, 12.500f), new(-5.000f, 12.500f), new(-5.000f, 15.000f), new(-8.000f, 15.000f) },
        new Vector2[] { new(5.000f, 12.500f), new(8.500f, 12.500f), new(8.500f, 15.000f), new(5.000f, 15.000f) },
    };
}
