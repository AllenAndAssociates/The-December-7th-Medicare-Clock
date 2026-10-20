"""Mix dialogue, pickups, music beds and SFX into one 48 kHz stereo WAV.

Usage: python3 mix.py out.wav
Levels: every dialogue cut is leveled to -18 dBFS RMS. Music envelope values in
timeline.json are the script's numbers; they sit 6 dB lower in RMS terms so a
"-26 dB" bed lands about 14 dB under the voice.
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
TL = json.load(open(os.path.join(ROOT, "timeline.json")))
SR = 48000
VOICE_RMS = -18.0
MUSIC_TRIM = -6.0
SFX_TRIM = -9.0


def load(path, start=None, dur=None, rate=SR):
    cmd = ["ffmpeg", "-nostdin", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vn", "-ac", "2", "-ar", str(rate), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def rms_db(x, gate=-45.0):
    """RMS of the parts that are actually sounding (50 ms blocks above the gate)."""
    mono = x.mean(1)
    n = len(mono) // 2400 * 2400
    if n == 0:
        return -90.0
    blk = np.sqrt((mono[:n].reshape(-1, 2400) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(blk)
    live = blk[db > gate]
    return float(20 * np.log10(np.sqrt((live ** 2).mean()) + 1e-12)) if len(live) else -90.0


def fade(x, fin=0.012, fout=0.012):
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def place(bus, x, t):
    i = int(round(t * SR))
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(bus), i + len(x))
    bus[i:j] += x[:j - i]


def envelope(points, n):
    ts = np.arange(n) / SR
    pts = np.array(points, dtype=np.float64)
    return 10 ** (np.interp(ts, pts[:, 0], pts[:, 1]) / 20)


def main(out):
    n = int(TL["total"] * SR) + SR
    voice, music, sfx = (np.zeros((n, 2), np.float32) for _ in range(3))

    for p in TL["pieces"]:
        if p["kind"] == "clip":
            x = load(os.path.join(REPO, p["src"]), p["in"], p["out"] - p["in"])
        else:
            x = load(os.path.join(ROOT, "audio", p["src"]), p["in"], p["out"] - p["in"])
        x *= 10 ** ((VOICE_RMS - rms_db(x)) / 20)
        place(voice, fade(x), p["start"])

    for m in TL["music"]:
        x = load(os.path.join(ROOT, "audio", m["src"]))
        x *= 10 ** ((MUSIC_TRIM - rms_db(x, gate=-60)) / 20)
        span = m["until"] - m["at"]
        off = m["from"] if m["from"] is not None else max(0.0, len(x) / SR - span)
        x = x[int(off * SR):int((off + span) * SR)]
        bus = np.zeros_like(music)
        place(bus, fade(x, 0.02, 0.05), m["at"])
        music += bus * envelope(m["env"], n)[:, None]

    cache = {}
    for h in TL["sfx"]:
        k = (h["name"], h["pitch"])
        if k not in cache:
            # pitch by resampling: decode at a shifted rate, play back at SR
            rate = int(SR / (2 ** (h["pitch"] / 12)))
            x = load(os.path.join(ROOT, "audio", "sfx", h["name"] + ".mp3"), rate=rate)
            x /= max(np.abs(x).max(), 1e-6)
            cache[k] = fade(x, 0.002, 0.03)
        place(sfx, cache[k] * 10 ** ((h["db"] + SFX_TRIM) / 20), h["t"])

    mix = voice + music + sfx
    mix = mix[:int(TL["total"] * SR)]
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", out, f"{len(pcm) / SR:.2f}s")


if __name__ == "__main__":
    main(sys.argv[1])
