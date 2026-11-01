# Reel Review page

A private page on the person's claude.ai account where they approve the edit before anything renders: cuts, graphics, captions, sound and colour, then a draft preview with timestamped notes. It needs Claude Code with Artifacts (the `Artifact` and `ArtifactData` tools) and the `db` + `assets` capabilities. If those aren't available, review in chat instead (rough-cut lines, then a card list) and skip this file.

## One time per reel

1. After transcribing and cleaning audio, run `python3 scripts/tighten.py <reel> --detect` so the "um"s are found (it writes `fillers.json`; without it the page shows no grey "um"s and none get cut). If it installs local Whisper first, that's normal. If it prints `FILLERS NOT DETECTED` (exit code 3), tell them the "um"s won't be cut automatically and that they can tap them out on the page. Then write `proposal.json` in the reel folder (format in the header of `scripts/review_sync.py`): the kept lines, accent words, and every graphic anchored to a spoken word with its `place` box and sound.
2. `python3 scripts/review_sync.py export <reel> proposal.json <out>` → `<out>/reel.json` (also saved as `<reel>/review_reel.json`).
3. Make the assets (keep them light, `nice -n 15`):
   - a 540x960 source proxy of `raw.mov` with the **cleaned** `voice.wav` as its audio (h264, ~900 kbps). The raw phone audio is ~20 dB quieter, so a proxy with it makes the voice sound broken
   - per graphic: `thumb_<id>.jpg` (180x320 frame at its anchor word) and `img_<id>.jpg` (its screenshot/image, 480 wide)
   - `audio_original.mp4` / `audio_cleaned.mp4` (same 10 s), `colour_before.jpg` / `colour_after.jpg` (same frame, grade applied), `sfx_<name>.mp4` for each sound
   - the brand's caption fonts (.otf/.ttf/.woff2) **only if the person owns them and the page stays private**
   Asset uploads accept mp4 (audio too), jpg/png, fonts; not m4a or wav.
4. First time only: publish `review/reel-review.html` with `files: {"core.js": "review/core.js"}`, `capabilities: {"db": {"rules": [{"path": "reel", "write": "admin"}, {"path": "builds", "write": "admin"}]}, "assets": {}}` (only editors can change the reel data and the preview; anyone you share it with at Contributor level can still record review decisions), `icon: "video"`. Later reels reuse the same page URL.
5. Start the thumbnail studio for this reel (see "Thumbnail studio" below) and note the link it prints.
6. Upload the assets to the page (`asset: true`, up to 25 per call), then write `reel/current` = `reel.json` plus `srcUrl`, per-graphic `thumbUrl`/`imgUrl`, `assets` {audioOriginal, audioCleaned, colourBefore, colourAfter, sfx{name:url}}, `fonts` {body, accent}, `thumbnailUrl` (the studio link) and `thumbnailCmd` (`python3 <absolute path to this skill>/scripts/thumbnail_studio.py --open`, for reopening it from Terminal). Delete `review/current` and `builds/latest` from the previous reel (ask first if they hold notes).
7. Send the link. Tell them: tap words to cut, tap ⏸ / grey "um"s to keep them, Play rough cut to watch the live cut, then Build preview.

## When they say "build preview"

1. `ArtifactData get review/current` (save to a file). Missing is fine: it means "use the proposal".
2. `python3 scripts/review_sync.py import <reel> <review.json>` → `edl.json` + `edit.json`. Act on every `CHANGE REQUESTED`, `NOTE` and `REVISION` line it prints before rendering; `BRAND CHANGE REQUESTED` only touches brand.json after they confirm.
3. `REEL_PREVIEW=1 python3 scripts/cut.py <reel>` then `REEL_PREVIEW=1 bash scripts/render.sh <reel>` (1080p, 2 workers, low priority).
4. Grab frames at every graphic and the longest caption words; fix anything out of frame before sending.
5. 540p proxy of `final.mp4` → upload → `ArtifactData set builds/latest` {url, hash (from edit.json), at, cutDur}. The page compares that hash with the live decisions and marks the preview outdated when they change.

## Thumbnail studio (the Cover tab)

The cover is made on their computer, not on claude.ai: Artifacts can't read local files, and a cover needs full-quality frames. `scripts/thumbnail_studio.py` is a small server bound to 127.0.0.1 only. It serves every reel in the workspace and the page `review/thumbnail.html`; footage, fonts and settings never leave the machine.

- **Start it** (when loading a reel, or when they say "open my thumbnail studio", "make a cover", "thumbnail"): `nohup python3 scripts/thumbnail_studio.py <reel> >> ~/reels/.thumbnail-studio.log 2>&1 &` (use `REELS_HOME` if set), wait a second, then `curl -s http://127.0.0.1:4848/api/health` must return `"app": "reel-thumbnail-studio"`. Only then send the link: `http://127.0.0.1:4848/?reel=<folder name>`. Running it again when it's already up just prints the link, so it's always safe. If port 4848 belongs to another app, pass `--port 4849`, and put that port in `thumbnailUrl`.
- **It stops when the computer restarts** (or the process is killed). The Cover tab tells them to ask you to reopen it; start it again as above. Add `--open` to open it in their browser when they're at the computer.
- **What it does:** six evenly spaced sampled frames (never call them the best or AI-picked: they choose the expression), a frame slider with ±1 frame, footage choice (clean `master.mp4`, the raw clip `raw.*`, `final.mp4`), a headline with manual line breaks that wraps and shrinks to stay in frame, brand fonts and colours from `brand.json` (a font that fails falls back to system sans), size, colour, vertical position, three styles (soft shadow, cream panel, dark fade), optional centred 3:4 and square crop guides (never in exports), and PNG downloads at 1080x1920, 1080x1440 and 1080x1080 to their Downloads folder. Canvas PNGs carry no camera or location metadata.
- **Saved with the reel** in `<reel>/thumbnail.json` (footage, time, headline, styling) on every change, and restored on reopen.
- **"Can't play raw.mov"**: some iPhone HEVC files only play in Safari. Suggest the clean master, Safari, or make an H.264 copy (`ffmpeg -i raw.mov -c:v libx264 -crf 18 -c:a aac raw.mp4`).
- Tests: `python3 tests/test_thumbnail_studio.py` and `node tests/test_thumbnail_ui.mjs` (headless Chrome).

## Final

After they approve the draft: `bash scripts/render.sh <reel> --final` only when `brand.json` asks for 4K (it re-cuts the 1080p preview master first); at 1080p the approved draft is the final. Then QA, deliver, and on the CapCut route `--capcut` (`--final --capcut` for 4K) plus `capcut_draft.py`.
