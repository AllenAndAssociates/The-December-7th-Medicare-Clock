"""Key Arric off the green screen and composite him over the graphics layer.

Usage: python3 composite.py graphics.mp4 out_video.mp4 [workers]
Splits the frame range across worker processes, then concatenates.
Reads timeline.json for the cut list, blocking keyframes and hidden spans.
From the "live" cue on, silent footage of Arric (timeline "idle") plays inside
the contact card's portrait circle.
"""
import json
import os
import subprocess
import sys
import tempfile
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image

from keyer import key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
TL = json.load(open(os.path.join(ROOT, "timeline.json")))
FPS, W, H = TL["fps"], TL["width"], TL["height"]
SRC_FPS = 24
CROP_X, CROP_W = 400, 1120          # the part of the source frame Arric can occupy
BASE = 0.80                         # "100%" = source scaled to 80%, bottom-anchored
# Portrait circle on the contact card (matches #por / #por img in the graphics):
# source crop [0:900, 560:1360] scaled 0.825 with its top-left at (122, 202),
# masked to the circle inside the gold ring.
POR_CROP, POR_K, POR_XY = (560, 0, 800, 900), 0.825, (122, 202)
POR_C, POR_R = (450, 450), 288


def ease(u, kind):
    if kind == "inout":
        return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
    return 1 - (1 - u) ** 3


def blocking(t):
    kf = TL["block"]
    cur = kf[0]
    for i, k in enumerate(kf):
        if k["t"] <= t:
            cur = k
            nxt = kf[i + 1] if i + 1 < len(kf) else None
            if nxt and nxt.get("ease") and t < nxt["t"]:
                u = ease((t - k["t"]) / (nxt["t"] - k["t"]), nxt["ease"])
                return k["x"] + (nxt["x"] - k["x"]) * u, k["s"] + (nxt["s"] - k["s"]) * u
    return cur["x"], cur["s"]


def visible(t):
    # hard cuts only: Arric is never semi-transparent over a card
    return not any(a <= t < b for a, b in TL["hidden"])


def grab(path, t, crop):
    x, y, w, h = crop
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


@lru_cache(maxsize=None)
def source_cx(src):
    """Torso centroid of a clip, from one fixed frame, so every cut and every
    worker frames the same clip identically."""
    a = key(grab(os.path.join(REPO, src), 5.0, (CROP_X, 0, CROP_W, H)))[600:, :, 3].astype(np.float32)
    return float((a.sum(0) * np.arange(CROP_W)).sum() / max(a.sum(), 1))


class ClipReader:
    """Sequential RGB frame reader for one cut, cropped to the speaker area."""

    def __init__(self, piece):
        self.piece = piece
        path = os.path.join(REPO, piece["src"])
        self.proc = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{piece['in']:.3f}", "-i", path,
             "-t", f"{piece['out'] - piece['in'] + 0.2:.3f}", "-vf", f"crop={CROP_W}:{H}:{CROP_X}:0",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx, self.rgba, self.cx = -1, None, source_cx(piece["src"])

    def frame(self, t):
        want = int((t - self.piece["start"]) * SRC_FPS + 1e-6)
        while self.idx < want:
            buf = self.proc.stdout.read(CROP_W * H * 3)
            if len(buf) < CROP_W * H * 3:
                break  # past the end of the source: hold the last frame
            self.idx += 1
            if self.idx >= want:
                self.rgba = key(np.frombuffer(buf, np.uint8).reshape(H, CROP_W, 3))
        return self.rgba

    def close(self):
        self.proc.stdout.close()
        self.proc.kill()


class Idle:
    """Ping-pong loop of silent footage for the portrait circle."""

    def __init__(self):
        x, y, w, h = POR_CROP
        self.segs = []
        head_cx = None
        for src, a, b in TL["idle"]:
            raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.3f}", "-i", os.path.join(REPO, src),
                                  "-t", f"{b - a:.3f}", "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True, check=True).stdout
            frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
            keyed = [key(f) for f in frames]
            # line every clip's head up with the first one (the still it replaces)
            al = keyed[0][:500, :, 3].astype(np.float32)
            cx = float((al.sum(0) * np.arange(w)).sum() / max(al.sum(), 1))
            head_cx = cx if head_cx is None else head_cx
            dx = int(round(head_cx - cx))
            sw, sh = int(round(w * POR_K)), int(round(h * POR_K))
            sprites = [np.asarray(Image.fromarray(np.roll(f, dx, axis=1)).resize((sw, sh), Image.BILINEAR)) for f in keyed]
            self.segs.append(sprites)
        # play order: each segment forward then back; the first segment twice more
        # so the familiar shot dominates and the cut to another clip is rare
        order = []
        for i, seg in enumerate(self.segs):
            reps = 3 if i == 0 else 1
            for _ in range(reps):
                order += seg + seg[::-1]
        self.order = order
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt((xx - POR_C[0]) ** 2 + (yy - POR_C[1]) ** 2)
        self.mask = np.clip(POR_R + 0.5 - d, 0, 1).astype(np.float32)

    def draw(self, bg, t):
        n = int((t - TL["cues"]["live"]) * SRC_FPS)
        spr = self.order[n % len(self.order)]
        x0, y0 = POR_XY
        sh, sw = spr.shape[:2]
        x1, y1 = min(x0 + sw, W), min(y0 + sh, H)
        sp = spr[:y1 - y0, :x1 - x0]
        a = sp[..., 3:4].astype(np.float32) / 255.0 * self.mask[y0:y1, x0:x1, None]
        region = bg[y0:y1, x0:x1].astype(np.float32)
        bg[y0:y1, x0:x1] = (sp[..., :3] * a + region * (1 - a) + 0.5).astype(np.uint8)


def render_range(args):
    gfx_path, out_path, f0, f1 = args
    clips = [p for p in TL["pieces"] if p["kind"] == "clip"]
    gfx = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{f0 / FPS:.4f}", "-i", gfx_path,
                            "-frames:v", str(f1 - f0), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    reader, last = None, None
    idle = Idle() if f1 / FPS > TL["cues"]["live"] else None
    for n in range(f0, f1):
        t = n / FPS
        buf = gfx.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            last = buf
        bg = np.frombuffer(last, np.uint8).reshape(H, W, 3).copy()
        piece = next((p for p in clips if p["start"] <= t < p["end"]), None)
        if idle is not None and t >= TL["cues"]["live"]:
            idle.draw(bg, t)
        if piece is not None and visible(t):
            if reader is None or reader.piece is not piece:
                if reader:
                    reader.close()
                reader = ClipReader(piece)
            rgba = reader.frame(t)
            x, s = blocking(t)
            k = BASE * s / 100.0
            sw, sh = max(1, int(round(CROP_W * k))), max(1, int(round(H * k)))
            spr = np.asarray(Image.fromarray(rgba).resize((sw, sh), Image.BILINEAR))
            left = int(round(x * W - reader.cx * k))
            top = H - sh
            # clip the sprite to the frame
            x0, y0 = max(left, 0), max(top, 0)
            x1, y1 = min(left + sw, W), min(top + sh, H)
            if x1 > x0 and y1 > y0:
                sp = spr[y0 - top:y1 - top, x0 - left:x1 - left]
                a = sp[..., 3:4].astype(np.float32) / 255.0
                region = bg[y0:y1, x0:x1].astype(np.float32)
                bg[y0:y1, x0:x1] = (sp[..., :3] * a + region * (1 - a) + 0.5).astype(np.uint8)
        enc.stdin.write(bg.tobytes())
        if (n - f0) % 300 == 0:
            print(f"frames {f0}-{f1}: at {n}", flush=True)
    if reader:
        reader.close()
    enc.stdin.close()
    enc.wait()
    gfx.kill()
    return out_path


def main(gfx_path, out_path, workers=4):
    total = int(round(TL["total"] * FPS))
    step = -(-total // workers)
    tmp = tempfile.mkdtemp(prefix="composite-")
    jobs = [(gfx_path, os.path.join(tmp, f"part{i}.mp4"), i * step, min(total, (i + 1) * step))
            for i in range(workers) if i * step < total]
    with Pool(len(jobs)) as pool:
        parts = pool.map(render_range, jobs)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", out_path], check=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
