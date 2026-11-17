"""Eigene Amberhive-Klaenge. Keine Aufnahmen oder fremden Samples.

Aufruf im Projekt: python tools/hive/sound/generate_sound.py
Abhaengigkeiten: numpy, ffmpeg (ausschliesslich als Vorbis-Encoder).
Die Schleifen sind periodisch synthetisiert. Pruefung nur mit verify/ (NVorbis).
"""
from pathlib import Path
import json
import shutil
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/amberhive/sound"
RATE = 24000
RNG = np.random.default_rng(2601116)


def noise(n, low, high):
    """Periodisches, weich bandbegrenztes Rauschen ohne abgeschnittene Enden."""
    f = np.fft.rfftfreq(n, 1 / RATE)
    width = max(20, (high - low) / 5)
    band = np.clip((f - low) / width, 0, 1) * np.clip((high - f) / width, 0, 1)
    z = (RNG.normal(size=f.size) + 1j * RNG.normal(size=f.size)) * band
    z[0] = z[-1] = 0
    x = np.fft.irfft(z, n)
    return x / max(1e-9, np.std(x))


def events(n, times, freq, decay, strength=1):
    """Weicher Anschlag mit umlaufendem Nachklang, auch ueber die Loopgrenze."""
    x = np.zeros(n)
    duration = min(n, int((decay * 16 + .05) * RATE))
    u = np.arange(duration) / RATE
    for at in times:
        f = freq * RNG.uniform(.90, 1.10)
        env = (1 - np.exp(-u / .012)) * np.exp(-u / decay)
        pulse = np.sin(2 * np.pi * (f * u + f * .018 * decay * (1 - np.exp(-u / decay)))) * env
        np.add.at(x, (np.arange(duration) + int(at * RATE)) % n, pulse * strength)
    return x


def generate(name, seconds=12):
    n = seconds * RATE
    t = np.arange(n) / RATE
    sin = lambda f, phase=0: np.sin(2 * np.pi * f * t + phase)
    if name in ("hive_buzz", "brood_buzz"):
        x = np.zeros(n)
        for j, f in enumerate((108, 137, 171) if name == "brood_buzz" else (112, 148)):
            ph = 2 * np.pi * f * t + .8 * sin((j + 1) / seconds, j)
            amp = .6 + .18 * sin((j + 2) / seconds, j)
            x += amp * (np.sin(ph) + .22 * np.sin(2 * ph) + .07 * np.sin(3 * ph))
        x += .09 * noise(n, 180, 780)
    elif name == "honey_well":
        x = .13 * noise(n, 80, 600)
        x += events(n, RNG.uniform(0, seconds, 28), 110, .13, 1.1)
        x += events(n, (1.2, 4.7, 8.8, 11.9), 190, .22, .65)
    elif name == "bellows":
        breath = (.5 + .5 * sin(1 / 3, -.5)) ** 1.6
        x = .5 * breath * noise(n, 160, 1400)
        ph = 2 * np.pi * 94 * t + 4 * sin(1 / 3)
        x += .28 * np.sin(ph) * (.5 + .5 * sin(1 / 3, 1.1)) ** 5
        x += events(n, (.4, 3.4, 6.4, 9.4), 65, .16, .5)
    elif name == "nectar_press":
        cycle = (.5 + .5 * sin(1 / 2)) ** 3
        x = .18 * noise(n, 160, 1200) * cycle + .16 * sin(64) * cycle
        x += events(n, (.45, 2.45, 4.45, 6.45, 8.45, 10.45), 83, .19, .9)
        x += events(n, (1.5, 3.5, 5.5, 7.5, 9.5, 11.5), 145, .08, .28)
    elif name == "wax_foundry":
        x = .26 * noise(n, 95, 780) * (.8 + .2 * sin(1 / 4))
        x += events(n, RNG.uniform(0, seconds, 42), 165, .07, .65)
        x += .08 * sin(51) * (.6 + .4 * sin(1 / 6))
    elif name == "mead_chimes":
        x = np.zeros(n)
        for at, f in ((1.0, 523), (8.4, 659), (17.2, 587)):
            for harmonic, level, decay in ((1, 1, 1.1), (2.4, .22, .5), (4.1, .08, .25)):
                x += events(n, (at,), f * harmonic, decay, level)
    elif name == "bridge_turn":
        x = .3 * noise(n, 90, 900) * (.8 + .2 * sin(2))
        x += .22 * sin(72, .9 * sin(1 / 3))
        x += events(n, np.arange(.15, seconds, .5), 120, .09, .5)
    elif name == "honey_flood":
        x = .4 * noise(n, 70, 1100) * (.8 + .2 * sin(1 / 3))
        x += events(n, RNG.uniform(0, seconds, 22), 95, .20, .6)
    elif name == "nectar_chute":
        x = .4 * noise(n, 180, 1700) * (.85 + .15 * sin(2))
        x += .12 * sin(122, .9 * sin(1 / 2)) + .08 * sin(197)
    else:
        raise ValueError(name)
    x -= np.mean(x)
    # Ruhiger Pegel, keine harten Transienten oder saettigenden Verzerrer.
    x *= min(.16 / max(1e-9, np.std(x)), .65 / np.max(np.abs(x)))
    return x.astype(np.float32)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"sample_rate": RATE, "channels": 1, "origin": "Original, prozedural mit numpy", "clips": {}}
    names = ("hive_buzz", "brood_buzz", "honey_well", "bellows", "nectar_press", "wax_foundry",
             "mead_chimes", "bridge_turn", "honey_flood", "nectar_chute")
    for name in names:
        x = generate(name, 24 if name == "mead_chimes" else 12)
        path = OUT / (name + ".ogg")
        # Nur ENCODING mit ffmpeg. Samples/Loopgrenzen prueft danach NVorbis.
        # libsndfile/Vorbis stuerzt unter dem lokalen Python 3.14 nativ ab.
        subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "pipe:0",
                        "-c:a", "libvorbis", "-q:a", "5", str(path)], input=x.astype("<f4").tobytes(), check=True)
        manifest["clips"][path.name] = {"frames": len(x), "seconds": len(x) / RATE,
                                        "master_rms": round(float(np.std(x)), 6),
                                        "master_peak": round(float(np.max(np.abs(x))), 6)}
        print(f"Erzeugt: {path.relative_to(ROOT)} ({len(x)} Frames)")
    (Path(__file__).parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
