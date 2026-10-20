#!/usr/bin/env bash
# Rebuild the main video (Scenes 6-18) from the clips in the repo root.
#   1. timeline.json  <- tools/edl.py   (cuts, cue times, blocking, music, SFX)
#   2. graphics layer <- HyperFrames    (canvas + motion graphics, no speaker)
#   3. speaker key    <- tools/composite.py (green-screen key + moves/punch-ins)
#   4. audio mix      <- tools/mix.py   (dialogue, pickups, music beds, SFX)
#   5. mux + loudness normalize to -14 LUFS
set -euo pipefail
cd "$(dirname "$0")"
OUT=${1:-../Medicare_Clock_Main_Video.mp4}
WORK=${WORK:-build}
mkdir -p "$WORK"
python3 tools/edl.py > "$WORK/cues.txt"
python3 tools/build_graphics.py
(cd graphics && npx --yes hyperframes@0.8.166 render -q delivery -o "../$WORK/graphics.mp4" --quiet)
python3 tools/composite.py "$WORK/graphics.mp4" "$WORK/video.mp4"
python3 tools/mix.py "$WORK/mix.wav"
ffmpeg -nostdin -v error -y -i "$WORK/video.mp4" -i "$WORK/mix.wav" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 256k -movflags +faststart -shortest "$OUT"
echo "done: $OUT"
