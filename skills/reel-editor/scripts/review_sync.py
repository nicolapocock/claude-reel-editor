#!/usr/bin/env python3
"""Bridge between a reel folder and the Reel Review page.
  export <reel> <proposal.json> <out-dir>   build reel.json (the page's data) + assets to upload
  import <reel> <review.json>               turn the person's decisions into edl.json + edit.json for cut.py/render.sh
The cut timeline is computed by review/core.js (run with node), the same file the page uses, so review and render agree.

proposal.json (Claude writes this per reel):
  {"title", "proposedCut": [[srcStart, srcEnd], ...] (kept lines), "accentWords": ["claude", ...],
   "cards": [{"id","type","kind","what","anchor":"word","after":srcSec,"end_anchor"?,"place":[x,y,w,h], "sfx":{"name","db"}, ...build_reel fields}]}"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pacing import pacing

def _exe(n):
    """Windows: npx and node are .CMD/.EXE, and CreateProcess needs the resolved path."""
    return shutil.which(n) or n

HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "review" / "core.js"
HOME = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser()
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

def raw_clip(reel):   # the raw clip's name keeps its extension (raw.mov from an iPhone, raw.mp4 from Android)
    return next(iter(sorted(reel.glob("raw.*"))), reel / "raw.mov")


def node(reel_json, decisions):
    # data goes in on stdin: long clips would overflow the command-line length limit
    js = f"""const C=require({json.dumps(str(CORE))});const I=JSON.parse(require("fs").readFileSync(0,"utf8"));const R=I.r,D=I.d;
const P=C.plan(R,D);process.stdout.write(JSON.stringify({{spans:P.spans,cutDur:P.cutDur,pauses:P.pauses,
captions:C.captions(R,D,P),graphics:C.graphics(R,D,P),hash:C.hash(D)}}));"""
    return json.loads(subprocess.run([_exe("node"), "-e", js], input=json.dumps({"r": reel_json, "d": decisions}),
                                     capture_output=True, text=True, check=True).stdout)

def export(reel, proposal, out):
    out.mkdir(parents=True, exist_ok=True)
    brand = json.load(open(HOME / "brand.json"))
    src = [w for w in json.load(open(reel / "transcript.json")) if w["text"].strip()]
    words = [{"text": w["text"], "s": round(w["start"], 3), "e": round(w["end"], 3)} for w in src]
    # Whisper's word times run back to back, hiding pauses. Measure real silences in the cleaned voice (threshold just
    # above this clip's noise floor) and pull word edges back to them, so pauses show up as gaps the review can trim.
    import array, math, wave
    wf = wave.open(str(reel / "voice.wav")); sr = wf.getframerate(); pcm = array.array("h"); pcm.frombytes(wf.readframes(wf.getnframes()))
    hop = int(sr * 0.05)
    lev = sorted(20 * math.log10(max(1.0, math.sqrt(sum(x * x for x in pcm[i:i + hop:4]) / (hop / 4))) / 32768) for i in range(0, len(pcm) - hop, hop))
    thresh = min(lev[len(lev) // 10] + 5, -20)
    sd = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(reel / "voice.wav"), "-af", f"silencedetect=noise={thresh:.1f}dB:d=0.15", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    sil = list(zip(map(float, re.findall(r"silence_start: ([\d.]+)", sd)), map(float, re.findall(r"silence_end: ([\d.]+)", sd))))
    for a, b in sil:
        for w in words:
            if w["s"] < a < w["e"] and a - w["s"] > 0.08: w["e"] = round(a, 3)
            elif a <= w["s"] < b and w["e"] - b > 0.08: w["s"] = round(b, 3)
    # fillers ("um", "uh") found by tighten.py's Whisper pass: slot them in as removable words
    fj = reel / "fillers.json"
    if fj.exists():
        for t in json.load(open(fj))["transcription"]:
            txt = t["text"].strip()
            if norm(txt) in set(pacing(brand)["fillers"]):
                s, e = t["offsets"]["from"] / 1000, t["offsets"]["to"] / 1000
                if not any(w["s"] < e - 0.05 and w["e"] > s + 0.05 for w in words):
                    words.append({"text": txt.strip(",.").lower(), "s": round(s, 3), "e": round(max(e, s + 0.25), 3), "filler": True})
                else:   # Whisper folded the um into a neighbouring word: split it off so cutting it removes its audio
                    e = round(max(e, s + 0.25), 3)
                    for w in words:
                        if w["s"] < e - 0.05 and w["e"] > s + 0.05 and not w.get("filler"):
                            if w["s"] >= s - 0.05: w["s"] = round(min(e, w["e"] - 0.05), 3)   # starts with the um: start after it
                            elif w["e"] <= e + 0.05: w["e"] = round(s, 3)  # word ends with the um: end before it
                    words.append({"text": "um", "s": round(s, 3), "e": e, "filler": True})
        words.sort(key=lambda w: w["s"])
    keep = proposal["proposedCut"]
    proposed_cut = [i for i, w in enumerate(words) if not w.get("filler") and
                    not any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in keep)]
    # pauses Claude keeps on purpose: after a question or exclamation, or longer than 0.8 s after a sentence end
    keep_pauses = [i for i in range(len(words) - 1) if re.search(r"[?!]$", words[i]["text"]) or
                   (re.search(r"[.]$", words[i]["text"]) and words[i + 1]["s"] - words[i]["e"] > 0.8)]
    acc = set(proposal.get("accentWords", []))
    mode = brand.get("captions", {}).get("mode", "phrase")
    caps, cur = [], []
    for i, w in enumerate(words):
        if w.get("filler"): continue
        cur.append(i)
        nxt = next((j for j in range(i + 1, len(words)) if not words[j].get("filler")), None)
        if mode == "word" or len(cur) >= 3 or re.search(r"[.,!?;:]$", w["text"]) or (nxt and words[nxt]["s"] - w["e"] > 0.35):
            caps.append({"w": cur, "acc": [k for k in cur if norm(words[k]["text"]) in acc]}); cur = []
    if cur: caps.append({"w": cur, "acc": [k for k in cur if norm(words[k]["text"]) in acc]})
    board = []
    for c in proposal["cards"]:
        hits = [i for i, w in enumerate(words) if norm(w["text"]) == norm(c["anchor"]) and w["s"] >= c.get("after", 0)]
        if not hits: print("warning: anchor not found:", c["id"], c["anchor"]); continue
        g = {k: v for k, v in c.items() if k not in ("anchor", "after", "end_anchor")}
        g["w0"] = hits[0]
        if c.get("end_anchor"):
            e = [i for i, w in enumerate(words) if norm(w["text"]) == norm(c["end_anchor"]) and i >= hits[0]]
            if e: g["w1"] = e[0]
        board.append(g)
    reel_json = {"title": proposal["title"], "srcDur": float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(raw_clip(reel))], capture_output=True, text=True).stdout),
                 "speed": pacing(brand)["speed"], "pacing": pacing(brand), "words": words, "proposedCut": proposed_cut, "keepPauses": keep_pauses,
                 "captions": caps, "board": board,
                 "style": {"capSize": brand["captions"].get("size", 104), "capY": brand["captions"].get("y", 1250),
                           "mode": mode, "editorial": brand["captions"].get("style") == "editorial",
                           "cap": brand["colors"].get("caption", "#FFFFFF"), "acc": brand["colors"].get("caption_accent", "#FF7DB8"),
                           "main": brand["colors"]["main"], "case": brand["captions"].get("case", "lower")},
                 "grade": brand.get("grade")}
    P = node(reel_json, {"cut": proposed_cut})
    print(f"{len(words)} words ({sum(1 for w in words if w.get('filler'))} fillers), {len(caps)} captions, {len(board)} graphics, "
          f"proposed cut {P['cutDur']:.1f}s, {len(P['pauses'])} pauses ({len(keep_pauses)} kept on purpose)")
    json.dump(reel_json, open(out / "reel.json", "w"))
    return reel_json

def do_import(reel, review):
    reel_json = json.load(open(reel / "review_reel.json"))
    d = json.load(open(review)) if Path(review).exists() else {}
    # same defaults as the page's blank() + decisions(), so the build's fingerprint matches what the page computes
    d = {"restoredFillers": [], "restoredPauses": [], "trimmedPauses": [], "board": {}, "sfxOff": {}, **d}
    if d.get("cut") is None: d["cut"] = reel_json["proposedCut"]          # [] is a real decision ("cut nothing"), not "unset"
    if d.get("captions") is None: d["captions"] = reel_json["captions"]
    P = node(reel_json, d)
    json.dump({"source": raw_clip(reel).name, "audio": "voice.wav", "keep": [[round(a, 3), round(b, 3)] for a, b in P["spans"]]},
              open(reel / "edl.json", "w"))
    caps = [{"start": round(c["start"], 3), "end": round(c["end"], 3),
             "words": [{"text": re.sub(r"[.,!?;:]+$", "", w["text"]), "t": round(w["t"], 3), "accent": w["accent"]} for w in c["words"]]}
            for c in P["captions"] if not c.get("gone")]
    cards, changes = [], []
    for g in P["graphics"]:
        if g.get("gone") or g["state"] == "d": continue
        note = ((d.get("board") or {}).get(g["id"]) or {}).get("note")
        if g["state"] == "c": changes.append(f"{g['id']} @ cut {g['start']:.1f}s: {note or '(no note)'}")
        spec = {k: v for k, v in g.items() if k not in ("id", "kind", "what", "w0", "w1", "state", "place", "moved", "gone")}
        spec.update(start=round(g["start"], 3), end=round(g["end"], 3), id=g["id"])
        if g["id"] in (d.get("sfxOff") or {}) and d["sfxOff"][g["id"]]: spec["sfx"] = False
        cards.append(spec)
    punch, last = [], -9.0   # punch-ins on sentence starts in the cut, at most every ~6 s (emphasis, not every line)
    for c in caps:
        if c["start"] - last > 6: punch.append(c["start"]); last = c["start"]
    json.dump({"captions": caps, "punch": punch, "cards": cards, "hash": P["hash"]}, open(reel / "edit.json", "w"), indent=1)
    print(f"cut {P['cutDur']:.1f}s from {len(P['spans'])} spans; {len(caps)} captions; {len(cards)} graphics; hash {P['hash']}")
    for c in changes: print("CHANGE REQUESTED:", c)
    for k, n in (d.get("notes") or {}).items():
        if n.strip(): print(f"NOTE ({k}):", n.strip())
    if (d.get("brandRequest") or "").strip(): print("BRAND CHANGE REQUESTED (only apply if confirmed):", d["brandRequest"].strip())
    for r in d.get("revisions") or []: print(f"REVISION @ cut {r['t']:.1f}s:", r["text"])

if __name__ == "__main__":
    cmd, reel = sys.argv[1], Path(sys.argv[2]).expanduser()
    if cmd == "export":
        r = export(reel, json.load(open(sys.argv[3])), Path(sys.argv[4]))
        json.dump(r, open(reel / "review_reel.json", "w"))
    elif cmd == "import": do_import(reel, sys.argv[3])
    else: sys.exit(__doc__)
