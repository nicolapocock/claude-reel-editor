#!/usr/bin/env python3
"""QA gate for a finished reel. Checks size, length, loudness, and (if expected.txt exists) that no words were lost.
Usage: python3 qa.py <reel-folder> [video]     default video: final.mp4. Exit code 1 if anything fails."""
import difflib, json, os, re, shutil, subprocess, sys
from pathlib import Path

def _exe(n):
    """Windows: npx and node are .CMD/.EXE, and CreateProcess needs the resolved path."""
    return shutil.which(n) or n

reel = Path(sys.argv[1]).expanduser()
video = reel / (sys.argv[2] if len(sys.argv) > 2 else "final.mp4")
home = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser()
brand = json.load(open(home / "brand.json"))
fails = []

def probe(entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                          "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)

info = probe("stream=width,height:format=duration")
w, h = info["streams"][0]["width"], info["streams"][0]["height"]
dur = float(info["format"]["duration"])
want = [1080, 1920] if os.environ.get("REEL_PREVIEW") else brand.get("resolution", [1080, 1920])
print(f"size      {w}x{h}  (want {want[0]}x{want[1]})")
if [w, h] != list(want): fails.append("size")
print(f"length    {dur:.1f}s  (max {brand.get('max_seconds', 60)}s)")
if dur > brand.get("max_seconds", 60): fails.append("length")

ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)[-1])
print(f"loudness  {lufs:.1f} LUFS  (want -15 to -12.5)")
if not -15 <= lufs <= -12.5: fails.append("loudness")

exp = reel / "expected.txt"
if exp.exists():
    tok = lambda s: re.sub(r"[^a-z0-9' ]", " ", s.lower()).split()
    subprocess.run([_exe("npx"), "-y", "hyperframes", "transcribe", str(video), "-d", str(reel / "qa_transcript"),
                    "--json"], capture_output=True)
    heard = [t for wd in json.load(open(reel / "qa_transcript/transcript.json")) for t in tok(wd["text"])]
    expected = tok(exp.read_text())
    ratio = difflib.SequenceMatcher(None, expected, heard, autojunk=False).ratio()
    missing = [expected[i1:i2] for op, i1, i2, _, _ in
               difflib.SequenceMatcher(None, expected, heard, autojunk=False).get_opcodes() if op in ("delete", "replace")]
    print(f"words     {ratio:.0%} match" + (f"; check: {missing[:6]}" if missing else ""))
    if ratio < 0.95: fails.append("words")
else:
    print("words     skipped (write the approved script to expected.txt to check for clipped words)")

print("PASS" if not fails else f"FAIL: {', '.join(fails)}")
sys.exit(1 if fails else 0)
