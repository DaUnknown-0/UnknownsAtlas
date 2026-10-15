# Packt Kartentexturen (Boden, Objekt- und Konsolenatlanten) als fertiges DXT mit Mipmaps (".atx").
#
# Warum: das Spiel dekodierte jede PNG/JPG im Hauptthread, rechnete Mipmaps und komprimierte nach DXT,
# rund 0,5 s je Textur (Rundenstart-Pause 09.10.). Mit .atx bleibt zur Laufzeit nur Entpacken (Hintergrund-
# Thread) und Hochladen (Hauptthread, wenige ms). AtlasTexturePack.cs liest das Format.
#
#   python pack_textures.py <ordner> <praefix> [<praefix> ...]           packt <praefix>_floor_*.jpg,
#                                                                          _props_*.png, _consoles_*.png
#   python pack_textures.py --check <ordner> <praefix> [<praefix> ...]   prüft, ob alle .atx aktuell sind
#
# Format (little endian): "ATX1", u8 Unity-TextureFormat (10 = DXT1, 12 = DXT5), u8 Version 1, u16 0,
# i32 Breite, i32 Höhe, i32 Mip-Anzahl, i32 Rohlänge, u32 CRC32 der Quelldatei, danach raw Deflate der
# Mip-Kette (größte Stufe zuerst). Zeilen von unten nach oben wie in Unity (Bild vor dem Kodieren gespiegelt).
import glob, io, os, struct, sys, zlib

import numpy as np
from PIL import Image

MAGIC = b"ATX1"
HEADER = 28  # Magic + Format/Version/Reserve + Breite/Höhe/Mips/Rohlänge + CRC
DXT1, DXT5 = 10, 12


def sources(folder, prefix):
    out = []
    for pat in (f"{prefix}_floor_*.jpg", f"{prefix}_props_*.png", f"{prefix}_consoles_*.png"):
        out += sorted(glob.glob(os.path.join(folder, pat)))
    return out


def crc_of(path):
    with open(path, "rb") as f:
        return zlib.crc32(f.read()) & 0xFFFFFFFF


def mip_chain(img):
    """Stufen wie Unity (Breite >> i, mindestens 1); Alpha vormultipliziert gefiltert gegen dunkle Säume."""
    rgba = img.mode == "RGBA"
    a = np.asarray(img, dtype=np.float32) / 255.0
    if rgba:
        a[..., :3] *= a[..., 3:4]
    levels = [a]
    while max(a.shape[0], a.shape[1]) > 1:
        h, w = a.shape[0], a.shape[1]
        nh, nw = max(1, h // 2), max(1, w // 2)
        # Box-Filter über 2x2 (ungerade Kanten: letzte Zeile/Spalte fällt weg, wie Unitys Box-Filter)
        b = a[: nh * (2 if h > 1 else 1), : nw * (2 if w > 1 else 1)]
        if h > 1:
            b = (b[0::2] + b[1::2]) / 2
        if w > 1:
            b = (b[:, 0::2] + b[:, 1::2]) / 2
        a = b
        levels.append(a)
    out = []
    for lv in levels:
        lv = lv.copy()
        if rgba:
            al = lv[..., 3:4]
            lv[..., :3] = np.where(al > 1e-4, lv[..., :3] / np.maximum(al, 1e-4), 0)
        arr = np.clip(lv * 255 + 0.5, 0, 255).astype(np.uint8)
        out.append(Image.fromarray(arr, "RGBA" if rgba else "RGB"))
    return out


def encode_level(img, fmt):
    w, h = img.size
    bw, bh = (w + 3) // 4, (h + 3) // 4
    if (bw * 4, bh * 4) != (w, h):  # auf ganze 4x4-Blöcke auffüllen (Rand wiederholen)
        arr = np.asarray(img)
        arr = np.pad(arr, ((0, bh * 4 - h), (0, bw * 4 - w), (0, 0)), mode="edge")
        img = Image.fromarray(arr, img.mode)
    buf = io.BytesIO()
    img.save(buf, "DDS", pixel_format="DXT1" if fmt == DXT1 else "DXT5")
    raw = buf.getvalue()
    head = 148 if raw[84:88] == b"DX10" else 128
    data = raw[head:]
    want = bw * bh * (8 if fmt == DXT1 else 16)
    if len(data) != want:
        raise ValueError(f"DXT-Stufe {w}x{h}: {len(data)} statt {want} Bytes")
    return data


def pack(path):
    img = Image.open(path)
    img = img.convert("RGBA" if "A" in img.getbands() or img.mode == "P" else "RGB")
    w, h = img.size
    if w % 4 or h % 4:
        raise ValueError(f"{path}: {w}x{h} nicht durch 4 teilbar")
    fmt = DXT5 if img.mode == "RGBA" else DXT1
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # Unity: erste Zeile = unten
    levels = mip_chain(img)
    raw = b"".join(encode_level(lv, fmt) for lv in levels)
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    payload = comp.compress(raw) + comp.flush()
    head = MAGIC + struct.pack("<BBHiiiiI", fmt, 1, 0, w, h, len(levels), len(raw), crc_of(path))
    out = os.path.splitext(path)[0] + ".atx"
    with open(out, "wb") as f:
        f.write(head + payload)
    return out, fmt, w, h, len(levels), len(raw), len(payload)


def is_current(path):
    atx = os.path.splitext(path)[0] + ".atx"
    if not os.path.exists(atx):
        return False
    with open(atx, "rb") as f:
        head = f.read(HEADER)
    return head[:4] == MAGIC and struct.unpack("<I", head[24:28])[0] == crc_of(path)


def main(argv):
    check = argv[:1] == ["--check"]
    if check:
        argv = argv[1:]
    if len(argv) < 2:
        print(__doc__ if __doc__ else "usage: pack_textures.py [--check] <ordner> <praefix> ...")
        return 2
    folder, prefixes = argv[0], argv[1:]
    stale, total_src, total_atx = [], 0, 0
    for prefix in prefixes:
        files = sources(folder, prefix)
        if not files:
            print(f"keine Quellen für '{prefix}' in {folder}")
            return 1
        for p in files:
            if check:
                if not is_current(p):
                    stale.append(p)
                continue
            out, fmt, w, h, mips, raw, comp = pack(p)
            total_src += os.path.getsize(p)
            total_atx += comp + HEADER
            print(f"{os.path.basename(out)}: {'DXT1' if fmt == DXT1 else 'DXT5'} {w}x{h}, {mips} Mips, "
                  f"{raw / 1e6:.1f} MB roh -> {comp / 1e6:.2f} MB")
    if check:
        for p in stale:
            print(f"VERALTET: {p}")
        print("alles aktuell" if not stale else f"{len(stale)} veraltet")
        return 1 if stale else 0
    print(f"Quellen {total_src / 1e6:.1f} MB -> .atx {total_atx / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
