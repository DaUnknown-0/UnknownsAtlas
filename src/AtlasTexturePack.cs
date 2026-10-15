// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasTexturePack - vorkomprimierte Kartentexturen (".atx", erzeugt von tools/pack_textures.py).
//
// Vorher dekodierte jede Kartentextur im Hauptthread PNG/JPG, rechnete Mipmaps und komprimierte nach DXT:
// rund 0,5 s je Textur, 17 bis 22 Texturen je Karte (Rundenstart-Pause 09.10.), dazu ein unkomprimiertes
// Zwischenbild bis 64 MB im 32-Bit-Prozess. Eine .atx enthaelt die fertige DXT1/DXT5-Mip-Kette, raw Deflate
// gepackt. Read laeuft ohne Unity-Aufruf und darf deshalb im Hintergrund-Thread laufen; Upload braucht den
// Hauptthread, kopiert aber nur Speicher und laedt hoch.
//
// Format (little endian, 28 Byte Kopf): "ATX1", u8 TextureFormat (10 = DXT1, 12 = DXT5), u8 Version 1,
// u16 0, i32 Breite, i32 Hoehe, i32 Mip-Anzahl, i32 Rohlaenge, u32 CRC32 der Quelldatei; danach die Mip-Kette
// (groesste Stufe zuerst, Zeilen von unten wie Unity).

using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using UnityEngine;

namespace UnknownsAtlas;

internal sealed class PackedTexture
{
    public int Width, Height, Mips;
    public TextureFormat Format;
    public byte[] Data;
}

internal static class AtlasTexturePack
{
    private const int HeaderSize = 28;

    /// <summary>Ressourcenname der gepackten Fassung: "....museum_floor_0.jpg" -> "....museum_floor_0.atx".</summary>
    public static string PackedName(string res)
    {
        int dot = res.LastIndexOf('.');
        return (dot > 0 ? res.Substring(0, dot) : res) + ".atx";
    }

    public static bool Has(Assembly asm, string res)
    {
        try { return asm.GetManifestResourceInfo(PackedName(res)) != null; }
        catch { return false; }
    }

    /// <summary>Liest und entpackt eine .atx. Keine Unity-Aufrufe: darf im Hintergrund laufen. null bei Fehler.</summary>
    public static PackedTexture Read(Assembly asm, string res)
    {
        try
        {
            using var s = asm.GetManifestResourceStream(PackedName(res));
            if (s == null) return null;
            var head = new byte[HeaderSize];
            if (!ReadFully(s, head)) return null;
            if (head[0] != 'A' || head[1] != 'T' || head[2] != 'X' || head[3] != '1' || head[5] != 1) return null;
            var fmt = (TextureFormat)head[4];
            if (fmt != TextureFormat.DXT1 && fmt != TextureFormat.DXT5) return null;
            int w = BitConverter.ToInt32(head, 8), h = BitConverter.ToInt32(head, 12);
            int mips = BitConverter.ToInt32(head, 16), raw = BitConverter.ToInt32(head, 20);
            if (w <= 0 || h <= 0 || mips <= 0 || raw <= 0 || raw != ChainSize(w, h, mips, fmt)) return null;
            var data = new byte[raw];
            using (var z = new DeflateStream(s, CompressionMode.Decompress))
                if (!ReadFully(z, data)) return null;
            return new PackedTexture { Width = w, Height = h, Mips = mips, Format = fmt, Data = data };
        }
        catch { return null; }
    }

    /// <summary>Hauptthread: Textur anlegen, Mip-Kette hineinkopieren, hochladen, CPU-Abbild verwerfen.</summary>
    public static Texture2D Upload(PackedTexture p)
    {
        var tex = new Texture2D(p.Width, p.Height, p.Format, p.Mips, false);
        tex.hideFlags |= HideFlags.HideAndDontSave | HideFlags.DontSaveInEditor;
        var pin = GCHandle.Alloc(p.Data, GCHandleType.Pinned);
        try { tex.LoadRawTextureData(pin.AddrOfPinnedObject(), p.Data.Length); }
        finally { pin.Free(); }
        tex.Apply(false, true);
        return tex;
    }

    /// <summary>Byte-Laenge der Mip-Kette, wie Unity sie fuer LoadRawTextureData erwartet.</summary>
    private static int ChainSize(int w, int h, int mips, TextureFormat fmt)
    {
        int block = fmt == TextureFormat.DXT1 ? 8 : 16;
        long sum = 0;
        for (int i = 0; i < mips; i++)
        {
            int lw = Math.Max(1, w >> i), lh = Math.Max(1, h >> i);
            sum += (long)((lw + 3) / 4) * ((lh + 3) / 4) * block;
        }
        return sum > int.MaxValue ? -1 : (int)sum;
    }

    private static bool ReadFully(Stream s, byte[] buf)
    {
        int read = 0;
        while (read < buf.Length)
        {
            int n = s.Read(buf, read, buf.Length - read);
            if (n <= 0) return false;
            read += n;
        }
        return true;
    }
}
