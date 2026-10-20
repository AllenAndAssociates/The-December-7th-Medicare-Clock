"""Mix dialogue, pickups, music beds and SFX into one 48 kHz stereo WAV.

Usage: python3 mix.py out.wav
Voice: on-camera cuts use Arric's speech-to-speech audio, pickups his cloned
TTS. Every voice piece is EQ-matched to one shared long-term spectrum, leveled
to -18 dBFS RMS, and the whole voice bus runs through one gentle compressor,
so cuts between clips and pickups don't jump in level or tone.
Music envelope values in timeline.json are the script's numbers; they sit
6 dB lower in RMS terms so a "-26 dB" bed lands about 14 dB under the voice.
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


BANDS = np.geomspace(70, 14000, 25)   # third-octave-ish analysis bands
NFFT = 4096


def ltas(x):
    """Long-term average spectrum (dB per band) of the sounding parts of x."""
    mono = x.mean(1)
    win = np.hanning(NFFT)
    frames = [mono[i:i + NFFT] * win for i in range(0, len(mono) - NFFT, NFFT // 4)]
    frames = [f for f in frames if np.sqrt((f ** 2).mean()) > 10 ** (-45 / 20)]
    p = (np.abs(np.fft.rfft(np.array(frames), axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    return np.array([10 * np.log10(p[(f >= lo) & (f < hi)].mean() + 1e-20) for lo, hi in zip(BANDS, BANDS[1:])])


def eq_to(x, have, want, limit=8.0):
    """Linear-phase EQ moving spectrum `have` toward `want` (band dB arrays)."""
    g = np.clip(want - have, -limit, limit)
    g = np.convolve(np.pad(g, 1, mode="edge"), [.25, .5, .25], mode="valid")   # smooth across bands
    centers = np.sqrt(BANDS[1:] * BANDS[:-1])
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    gain_db = np.interp(np.log(np.maximum(f, 1)), np.log(centers), g, left=g[0], right=g[-1])
    gain_db[f < 60] = -18          # same low cut on every piece
    h = np.fft.irfft(10 ** (gain_db / 20), NFFT)
    h = np.roll(h, NFFT // 2) * np.hanning(NFFT)
    n = len(x) + NFFT
    H_ = np.fft.rfft(h, n)
    y = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], n) * H_, n)[NFFT // 2:NFFT // 2 + len(x)] for c in range(2)], 1)
    return y.astype(np.float32)


def compress(x, thresh=-22.0, ratio=2.5, attack=0.010, release=0.120, floor=-52.0):
    """Gentle bus compressor (5 ms blocks, one-pole envelope), with a soft
    downward expander under `floor` so pauses stay clean."""
    blk = 240
    m = len(x) // blk * blk
    lvl = np.sqrt((x[:m].mean(1).reshape(-1, blk) ** 2).mean(1) + 1e-12)
    env = np.empty_like(lvl)
    e, ca, cr = 0.0, np.exp(-blk / SR / attack), np.exp(-blk / SR / release)
    for i, v in enumerate(lvl):
        c = ca if v > e else cr
        e = c * e + (1 - c) * v
        env[i] = e
    db = 20 * np.log10(env + 1e-12)
    gr = np.where(db > thresh, (thresh - db) * (1 - 1 / ratio), 0.0)
    gr += np.where(db < floor, np.maximum((db - floor) * 1.5, -18.0), 0.0)
    g = np.interp(np.arange(len(x)), np.arange(len(gr)) * blk + blk / 2, 10 ** (gr / 20))
    return x * g[:, None].astype(np.float32)


def declick(x):
    """Silence isolated ticks in pauses: 1 ms blocks peaking 22+ dB over the
    surrounding 50 ms when that surround is near-silent. Returns (x, times)."""
    mono = np.abs(x.mean(1))
    blk = 48
    nb = len(mono) // blk
    pk = mono[:nb * blk].reshape(nb, blk).max(1)
    ms = (mono[:nb * blk].reshape(nb, blk) ** 2).mean(1)
    found = []
    for i in np.where(pk > 10 ** (-60 / 20))[0]:
        ctx = np.r_[ms[max(0, i - 25):max(0, i - 3)], ms[i + 4:i + 26]]
        if not len(ctx):
            continue
        sur = 10 * np.log10(ctx.mean() + 1e-12)
        if sur < -50 and 20 * np.log10(pk[i] + 1e-12) - sur > 22:
            a, b = max(0, (i - 2) * blk), min(len(x), (i + 3) * blk)
            x[a:b] *= np.r_[np.linspace(1, 0, 24), np.zeros(b - a - 48), np.linspace(0, 1, 24)][:b - a, None]
            found.append(round(i * blk / SR, 3))
    return x, found


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

    # every voice piece -> one master spectrum (duration-weighted average)
    vparts = []
    for p in TL["pieces"]:
        x = load(os.path.join(ROOT, "audio", p["audio"]), p["in"], p["out"] - p["in"])
        vparts.append((p, x, ltas(x)))
    w = np.array([len(x) for _, x, _ in vparts], np.float64)
    target = 10 * np.log10((np.array([10 ** (l / 10) for _, _, l in vparts]) * w[:, None]).sum(0) / w.sum())
    for p, x, l in vparts:
        x, ticks = declick(x)
        if ticks:
            print(f"declicked {p['audio']} at", [round(p["start"] + t, 2) for t in ticks])
        x = eq_to(x, l, target)
        x *= 10 ** ((VOICE_RMS - rms_db(x)) / 20)
        place(voice, fade(x), p["start"])
    voice = compress(voice)
    voice *= 10 ** ((VOICE_RMS - rms_db(voice)) / 20)

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
