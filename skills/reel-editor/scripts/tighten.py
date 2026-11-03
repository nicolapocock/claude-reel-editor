#!/usr/bin/env python3
"""Tighten an approved rough cut: remove fillers and shorten pauses inside the kept spans, as hard as brand.json "pacing" says (scripts/pacing.py).
Run after the person approves edl.json, before cut.py. Rewrites edl.json (the original is kept as edl_rough.json).
Usage: python3 tighten.py <reel-folder>
       python3 tighten.py <reel-folder> --detect   only find the fillers (writes fillers.json); run before the review page

How: Whisper normally hides fillers inside neighbouring words, so it is re-run with a prompt full of "um, uh",
which makes it write them down. Pauses come from silencedetect on the cleaned voice. Every cut edge keeps the preset's
air (50-150 ms) so words never clip."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

def _exe(n):
    """Windows: npx and node are .CMD/.EXE, and CreateProcess needs the resolved path."""
    return shutil.which(n) or n

reel = Path(sys.argv[1]).expanduser()
DETECT = "--detect" in sys.argv[2:]
edl = {} if DETECT else json.load(open(reel / "edl.json"))
voice = reel / edl.get("audio", "voice.wav")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pacing import pacing
P_ = pacing(json.load(open(Path(os.environ.get("REELS_HOME", "~/reels")).expanduser() / "brand.json")))
PAD, MIN_PAUSE = P_["air"], P_["pause_min"]
FILLERS = set(P_["fillers"])

# 1. fillers. Preferred source is the step-1 transcript: ElevenLabs Scribe and Parakeet both write
# "um"/"uh" down, with word timings accurate enough to cut on. Whisper is only the fallback - it
# hides fillers unless prompted for them, and its -oj segment offsets cover just the front of one
# (measured here: "um" reported 0.44-0.96 where it actually ran 0.80-1.60), so cutting on those
# offsets removes the start of the filler and leaves its tail in the edit.
cuts = []
found = False

def filler_cuts(items, get):
    """Cut spans for every filler in a word list. `get` maps one item -> (text, start, end)."""
    out = []
    for k, it in enumerate(items):
        txt, a, b = get(it)
        if re.sub(r"[^a-z]", "", txt.lower()) not in FILLERS:
            continue
        nxt = get(items[k + 1])[1] if k + 1 < len(items) else b
        out.append((a - 0.02, max(b, min(nxt, a + 1.0)) - 0.02))   # never past the next word
    return out

tx = reel / "transcript.json"
if tx.exists():
    words = json.load(open(tx))
    cuts = filler_cuts(words, lambda w: (w["text"], w["start"], w["end"]))
    found = True
    print(f"fillers found in transcript.json: {len(cuts)}", [round(a, 1) for a, _ in cuts])
    # review_sync.py reads fillers.json to mark these words removable (grey) on the review
    # page. Whisper used to write it; on the transcript path we write it ourselves, in the
    # same shape, or the page shows no fillers even though we found them.
    json.dump({"transcription": [
        {"text": w["text"], "offsets": {"from": int(w["start"] * 1000), "to": int(w["end"] * 1000)}}
        for w in words if re.sub(r"[^a-z]", "", w["text"].lower()) in FILLERS]},
        open(reel / "fillers.json", "w"))

def find_whisper():
    cli = shutil.which("whisper-cli") or next((str(p) for p in Path("~/.cache/hyperframes/whisper").expanduser().rglob("whisper-cli*")), None)
    model = next(iter(sorted(Path("~/.cache/hyperframes/whisper/models").expanduser().glob("ggml-small*.bin"))), None)
    return cli, model

if not found:
    cli, model = find_whisper()
    if not (cli and model):   # no transcript and no whisper: let HyperFrames' transcriber fetch what it can
        print("no transcript.json and local Whisper not installed: trying to install it (one time, a few minutes)")
        try:
            subprocess.run([_exe("npx"), "-y", "hyperframes", "transcribe", str(voice), "-d", str(reel / "_whisper_setup"), "--json"],
                           capture_output=True)
        except OSError as e:
            print("couldn't install Whisper:", e)
        shutil.rmtree(reel / "_whisper_setup", ignore_errors=True)
        cli, model = find_whisper()
    if cli and model:
        wav16 = reel / "v16.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(voice), "-ar", "16000", "-ac", "1", str(wav16)], check=True)
        r = subprocess.run([cli, "-m", str(model), "-f", str(wav16), "--prompt", "Um, uh, so, like, um, I mean, uh, you know.",
                            "-ml", "1", "-sow", "-oj", "-of", str(reel / "fillers")], capture_output=True, text=True)
        if r.returncode == 0 and (reel / "fillers.json").exists():
            found = True
            toks = [t for t in json.load(open(reel / "fillers.json"))["transcription"] if t["text"].strip()]
            cuts = filler_cuts(toks, lambda t: (t["text"].strip(), t["offsets"]["from"] / 1000, t["offsets"]["to"] / 1000))
            print(f"fillers found by whisper (timings are coarse): {len(cuts)}", [round(a, 1) for a, _ in cuts])
        else:
            (reel / "fillers.json").unlink(missing_ok=True)   # never leave a stale or half-written file behind
            print("whisper-cli failed:", (r.stderr or "").strip()[-300:])
if not found:
    print("FILLERS NOT DETECTED: um/uh won't be cut automatically. Tell the person, and offer to cut them by hand on the review.")
if DETECT: sys.exit(0 if found else 3)

# 2. pauses, via silencedetect on the cleaned voice. The threshold sits just above THIS clip's background noise
#    (outdoor or noisy rooms never reach a fixed -40 dB, so a fixed threshold finds nothing).
import array, math, wave
wf = wave.open(str(voice)); sr = wf.getframerate(); pcm = array.array("h"); pcm.frombytes(wf.readframes(wf.getnframes()))
hop = int(sr * 0.05)
lev = sorted(20 * math.log10(max(1.0, math.sqrt(sum(x * x for x in pcm[i:i + hop:4]) / (hop / 4))) / 32768)
             for i in range(0, len(pcm) - hop, hop))
floor = lev[len(lev) // 10]
thresh = min(floor + 5, -20)
print(f"background noise {floor:.0f} dB -> pause threshold {thresh:.0f} dB")
out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(voice), "-af", f"silencedetect=noise={thresh:.1f}dB:d={MIN_PAUSE}", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
pauses = [(a + PAD, b - PAD) for a, b in zip(starts, ends) if b - a > MIN_PAUSE]
cuts += pauses
cuts.sort()

# 3. subtract the cuts from each approved span (span order is preserved, so a moved CTA stays moved)
def subtract(span, cuts):
    a, b = span; parts, cur = [], a
    for ca, cb in cuts:
        if cb <= cur or ca >= b: continue
        if ca > cur + 0.05: parts.append([round(cur, 3), round(ca, 3)])
        cur = max(cur, cb)
    if b > cur + 0.05: parts.append([round(cur, 3), round(b, 3)])
    return parts
before = sum(b - a for a, b in edl["keep"])
shutil.copy(reel / "edl.json", reel / "edl_rough.json")
edl["keep"] = [p for span in edl["keep"] for p in subtract(span, cuts)]
after = sum(b - a for a, b in edl["keep"])
json.dump(edl, open(reel / "edl.json", "w"))
print(f"{len(pauses)} pauses + fillers removed: {before:.1f}s -> {after:.1f}s kept ({len(edl['keep'])} pieces)")
