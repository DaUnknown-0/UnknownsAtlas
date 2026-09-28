# Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
# Licensed under GPL-3.0-or-later. See LICENSE for details.
#
# gen_roar.py - T-Rex-Gebruell (Rex-Sabotage, Rauswurf "T-Rex", Geisterbahn) aus echten Tieraufnahmen.
# Geschichtet wie der Jurassic-Park-Rex (Gary Rydstrom): hoch = Elefantenschrei, Mitte = Tigergrollen mit
# Loewen-Grunzer als Anschlag, tief = Alligator. Jede Schicht wird verlangsamt (tiefer, groesseres Tier),
# entrauscht, bandbegrenzt und gemischt; dann Huellkurve (harter Einsatz, Spitze bei 0,6 s, abklingendes
# Grollen), Saalhall, sanfte Saettigung. Ausgabe: assets/sfx_roar.wav, 22050 Hz, mono, 16 bit
# (EjectSynth laedt eingebettete sfx_<name>.wav vor dem Synth-Klang).
#
# Quellen, alle CC0 1.0 (Public Domain, keine Namensnennung noetig), Freesound-Vorschau-MP3s:
#   craigsmith "G12-47-Lions Roaring.wav"          https://freesound.org/people/craigsmith/sounds/437980/
#   craigsmith "G12-01-Alligator Growl.wav"        https://freesound.org/people/craigsmith/sounds/437933/
#   craigsmith "G12-44-Elephants and Tigers.wav"   https://freesound.org/people/craigsmith/sounds/437977/
# Die Quellen landen in tools/_roar_src/ (nicht im Repo). Braucht numpy, scipy und ffmpeg.
#
#   python tools/gen_roar.py            erzeugt assets/sfx_roar.wav
#   python tools/gen_roar.py --stems    zusaetzlich die Einzelschichten in tools/_roar_src/
import os, sys, subprocess, urllib.request
from fractions import Fraction
import numpy as np
from scipy.io import wavfile
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_roar_src")
OUT = os.path.join(HERE, "..", "assets", "sfx_roar.wav")
SOURCES = {
    "lions": "https://cdn.freesound.org/previews/437/437980_2524442-hq.mp3",
    "gator": "https://cdn.freesound.org/previews/437/437933_2524442-hq.mp3",
    "eleph_tiger": "https://cdn.freesound.org/previews/437/437977_2524442-hq.mp3",
}
SR = 44100
OUT_SR = 22050
_c = {}

def fetch():
    os.makedirs(SRC, exist_ok=True)
    for name, url in SOURCES.items():
        wav = os.path.join(SRC, name + ".wav")
        if os.path.exists(wav): continue
        mp3 = os.path.join(SRC, name + ".mp3")
        if not os.path.exists(mp3):
            print("lade", url)
            req = urllib.request.Request(url, headers={"User-Agent": "UnknownsAtlas-gen_roar/1.0"})
            with urllib.request.urlopen(req) as r, open(mp3, "wb") as f: f.write(r.read())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(SR), wav], check=True)

def load(name):
    if name not in _c:
        sr, x = wavfile.read(os.path.join(SRC, name + ".wav")); assert sr == SR
        _c[name] = x.astype(np.float64) / 32768
    return _c[name]

def cut(name, t0, t1, fin=0.02, fout=0.08):
    x = load(name)[int(t0 * SR):int(t1 * SR)].copy()
    a, b = int(fin * SR), int(fout * SR)
    x[:a] *= np.linspace(0, 1, a) ** 2
    x[-b:] *= np.linspace(1, 0, b) ** 2
    return x

def denoise(x, noise, strength=1.5, floor=0.08):
    """Spektrale Subtraktion mit Rauschprofil aus einer stillen Stelle."""
    n = 2048
    _, _, N = signal.stft(noise, SR, nperseg=n)
    prof = np.mean(np.abs(N), axis=1, keepdims=True)
    _, _, X = signal.stft(x, SR, nperseg=n)
    g = np.maximum(1 - strength * prof / (np.abs(X) + 1e-12), floor)
    g = signal.medfilt2d(g, (3, 5))                      # glaettet "musical noise"
    _, y = signal.istft(X * g, SR, nperseg=n)
    return y[:len(x)]

def slow(x, factor):
    """Verlangsamen um factor (> 1): tiefer und laenger, wie Band langsamer abspielen."""
    fr = Fraction(factor).limit_denominator(50)
    return signal.resample_poly(x, fr.numerator, fr.denominator)

def band(x, lo, hi, order=4):
    return signal.sosfiltfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)

def peq(x, f0, gain_db, q=0.9):
    """Glocken-EQ (RBJ)."""
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)

def norm(x): return x / (np.max(np.abs(x)) + 1e-12)

def place(buf, x, at, gain):
    i = int(at * SR); j = min(len(buf), i + len(x))
    buf[i:j] += x[:j - i] * gain

def reverb(x, rt=1.1, wet=0.22, seed=7):
    """Saal: exponentiell abklingendes, bandbegrenztes Rauschen als Impulsantwort + fruehe Reflexionen."""
    rng = np.random.default_rng(seed)
    n = int(SR * rt * 1.2); t = np.arange(n) / SR
    ir = band(rng.standard_normal(n) * np.exp(-6.9 * t / rt), 120, 5000, 2)
    ir[:int(0.012 * SR)] = 0
    for d, g in ((0.017, 0.5), (0.029, 0.35), (0.041, 0.3), (0.063, 0.2)):
        ir[int(d * SR)] += g * 3
    w = signal.fftconvolve(x, norm(ir))[:len(x) + n]
    dry = np.concatenate([x, np.zeros(len(w) - len(x))])
    return dry + wet * norm(w) * np.max(np.abs(x))

def trim(x, thr_db=-22):
    """Vorlauf abschneiden: ab 15 ms vor dem ersten Punkt ueber thr_db (relativ zum Maximum)."""
    h = int(0.01 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(h) / h, "same")) + 1e-12
    i = max(0, int(np.argmax(20 * np.log10(env / env.max()) > thr_db)) - int(0.015 * SR))
    y = x[i:].copy(); a = int(0.01 * SR); y[:a] *= np.linspace(0, 1, a)
    return y

def fade_out(x, fout):
    b = int(fout * SR); x = x.copy(); x[-b:] *= np.linspace(1, 0, b) ** 1.5; return x

def build(stems=False, length=2.6, rv=0.22):
    nz_l = load("lions")[int(93.25 * SR):int(93.75 * SR)]            # stille Stellen als Rauschprofil
    nz_g = load("gator")[int(12.5 * SR):int(14.3 * SR)]
    nz_e = load("eleph_tiger")[int(72.5 * SR):int(75.5 * SR)]
    E = trim(cut("eleph_tiger", 7.85, 9.45, fout=0.12))                # hoch: absteigender Elefantenschrei
    E = peq(band(slow(denoise(E, nz_e), 1.35), 350, 7000), 2500, -3, 0.7)
    L = trim(cut("lions", 97.1, 98.05, fout=0.3))                      # Anschlag: Loewen-Grunzer
    L = peq(band(slow(denoise(L, nz_l, 1.8), 1.25), 70, 6500), 180, +4, 0.8)
    T = trim(cut("eleph_tiger", 9.42, 11.85, fin=0.06, fout=0.5))      # Koerper: durchgehendes Tigergrollen
    T = peq(band(slow(denoise(T, nz_e), 1.3), 60, 5000), 250, +3, 0.8)
    G = trim(cut("gator", 15.25, 17.95, fin=0.05, fout=0.4))           # tief: Alligator
    G = peq(band(slow(denoise(G, nz_g), 1.4), 28, 700), 70, +5, 0.7)
    if stems:
        for nm, s in (("elefant", E), ("loewe", L), ("tiger", T), ("alligator", G)):
            save(os.path.join(SRC, f"stem_{nm}.wav"), signal.resample_poly(norm(s), 1, 2) * 0.9)
    buf = np.zeros(int(SR * (length + 4)))
    for x, gain, t0 in zip((E, L, T, G), (0.5, 0.85, 1.0, 0.75), (0.03, 0.0, 0.22, 0.0)):
        place(buf, norm(x), t0, gain)
    buf = buf[:int(SR * length)]
    tt = np.arange(len(buf)) / SR; pk = 0.6
    shape = np.where(tt < pk, 0.75 + 0.25 * np.sin(0.5 * np.pi * tt / pk),
                     0.35 + 0.65 * np.exp(-3.08 * (tt - pk) / (length - pk)))
    buf = band(fade_out(norm(buf) * shape, 0.3), 30, 9000, 2)
    y = fade_out(reverb(norm(buf), rt=1.1, wet=rv)[:int(SR * (length + 0.35))], 0.3)
    y = np.tanh(1.3 * norm(y)) / np.tanh(1.3)                          # sanfte Saettigung, mehr Druck
    return norm(signal.resample_poly(y, 1, 2)) * 0.95                  # 22050 Hz fuers Spiel

def save(path, y):
    wavfile.write(path, OUT_SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))

if __name__ == "__main__":
    fetch()
    y = build(stems="--stems" in sys.argv)
    save(OUT, y)
    print(f"{os.path.normpath(OUT)}: {len(y) / OUT_SR:.2f} s, {os.path.getsize(OUT) // 1024} KB")
