#!/usr/bin/env bash
# Build the reel from edit.json and render it. Logs how long each part took to <reel>/timings.log.
# Usage: render.sh <reel-folder> [--capcut] [--final]
# Gentle by default: 2 Chrome workers at low priority, 1080p preview. --final renders at the brand resolution (1080p by default).
set -euo pipefail
REEL="$(cd "$1" && pwd)"; shift
FINAL=0; ARGS=(); for a in "$@"; do [ "$a" = "--final" ] && FINAL=1 || ARGS+=("$a"); done
WORKERS="${REEL_WORKERS:-2}"                     # each worker is a Chrome; 2 keeps a 16 GB Mac usable
S="$(cd "$(dirname "$0")" && pwd)"
BRAND="${REELS_HOME:-$HOME/reels}/brand.json"
RES="$(python3 -c "import json;r=json.load(open('$BRAND')).get('resolution',[1080,1920]);print('portrait-4k' if r[0]>=2160 else 'portrait')")"
[ "$FINAL" = 1 ] || RES=portrait                 # previews at 1080p: a quarter of the pixels of 4K
stamp() { echo "$(date +%s) $1" >> "$REEL/timings.log"; }

# a preview cut leaves a 1080p master.mp4; re-cut it at the brand resolution so the final isn't an upscale
if [ "$FINAL" = 1 ]; then
  WANT="$(python3 -c "import json;print(json.load(open('$BRAND')).get('resolution',[1080,1920])[1])")"
  HAVE="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$REEL/master.mp4")"
  if [ "$HAVE" -lt "$WANT" ]; then echo "master.mp4 is ${HAVE}p, re-cutting at ${WANT}p for the final"; env -u REEL_PREVIEW python3 "$S/cut.py" "$REEL"; fi
fi

[ -s "$S/../engine/gsap.min.js" ] || bash "$S/setup_engine.sh"
stamp "build:start"; python3 "$S/build_reel.py" "$REEL" ${ARGS[@]+"${ARGS[@]}"}; stamp "build:end"
stamp "render:start"
# iPhone clips are HLG/bt2020. Rendering them as HDR writes ~12 GB of raw frames, takes 3x
# longer, drops the HTML overlay, and Instagram wants SDR anyway. REEL_HDR=1 to opt back in.
SDRFLAG=(--sdr); [ -n "${REEL_HDR:-}" ] && SDRFLAG=()
nice -n 15 npx -y hyperframes@0.8.145 render "$REEL/proj" --workers "$WORKERS" -o "$REEL/final.mp4" --resolution "$RES" --quality delivery "${SDRFLAG[@]}" --quiet
stamp "render:end"
# Final mix. Optional music bed (brand.json "music": path) sits ~18 dB under the voice and ducks further while she talks.
# Then bring the whole mix to -14 LUFS (video copied, not re-encoded).
MUSIC="$(python3 -c "import json,os;m=json.load(open('$BRAND')).get('music');print(os.path.expanduser(m) if m else '')")"
if [ -n "$MUSIC" ] && [ -f "$MUSIC" ]; then
  ffmpeg -v error -y -i "$REEL/final.mp4" -stream_loop -1 -i "$MUSIC" -filter_complex \
    "[1:a]volume=-18dB,afade=t=in:d=0.5[m];[0:a]asplit[v][key];[m][key]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[md];[v][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=7[a]" \
    -map 0:v -map "[a]" -c:v copy -ar 48000 -c:a aac -b:a 256k "$REEL/final_ln.mp4"
else
  ffmpeg -v error -y -i "$REEL/final.mp4" -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=7" -ar 48000 -c:a aac -b:a 256k "$REEL/final_ln.mp4"
fi
mv "$REEL/final_ln.mp4" "$REEL/final.mp4"
python3 "$S/timings.py" "$REEL"
