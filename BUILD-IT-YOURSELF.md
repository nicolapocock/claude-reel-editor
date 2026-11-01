# build your own reel editor

this repo works out of the box, but if you want to understand it, change it, or build your own version from scratch, this is the walkthrough. you don't need to know how to code. you need claude code, an idea of how you want your reels to look, and a couple of evenings.

i built this by talking to claude code and fixing what came back. these are the decisions that made it work, in the order i'd build it again, with a prompt you can paste for each part.

---

## how it works, in plain english

a reel goes through six steps. each one is a small script that claude runs for you:

1. **listen.** it writes down every word you said and when you said it (the transcript).
2. **clean the sound.** it takes out background noise, softens harsh "s" sounds, and makes your voice the volume instagram expects.
3. **cut.** it suggests which lines to cut, then removes the "um"s and long pauses inside the lines you keep. how hard it trims is your pacing choice (natural, tight or fast).
4. **add graphics and captions.** it fills in a ready-made template in your brand: captions, website screenshots, a carousel, stickers, a list card.
5. **render.** it turns all of that into a video file.
6. **check.** it measures the loudness, looks for text running off the edge, and makes sure no words got clipped.

before step 5, you approve everything on a review page, so nothing renders until it looks right.

---

## the four decisions that matter most

**1. claude fills in a template instead of designing each reel.**
my first version had claude design every graphic from scratch. it looked good, and it took over an hour per reel and cooked my laptop. now the look lives in one template, and claude only decides which word gets highlighted and which graphic goes where. that took a reel from 85 minutes down to about 4.

**2. your brand lives in a file.**
the first time you run it, it interviews you (colours, fonts, caption style, sounds) and saves the answers in `brand.md` and `brand.json`. every reel reads that file. when you correct something ("never outline the captions"), it goes in the file, so you only say it once.

**3. you approve before anything renders.**
rendering video is the slow, hot part. so you review the cuts, the graphics and the captions on a page first, watch a live rough cut, and only then build a preview.

**4. one timing engine, shared.**
the review page and the renderer use the same little file (`review/core.js`) to work out where everything lands after the cuts, so the edit you approve is the edit that renders.

---

## build it, step by step

open claude code in an empty folder and paste these one at a time. let each one finish and check what it made before you move on.

**step 1: the brand interview**
```
help me build a reel editor. first, interview me one question at a time about my brand for short-form videos: colours (with hex codes), fonts, caption style, sound effects, pacing, and my usual call to action. ask me for a reel i love as a reference. then save my answers as brand.md (for people) and brand.json (for scripts).
```

**step 2: clean audio and transcript**
```
write a script that takes a talking-head video, removes background noise, evens out my voice, and sets it to -14 LUFS (the volume instagram uses). then write a second script that transcribes it with word-level timestamps. test both on my clip and tell me the background noise level before and after.
```

**step 3: cuts**
```
show me my transcript as numbered lines with the cuts you'd suggest (repeats, false starts, the bit before i turn the camera round). after i approve, write a script that cuts those lines, removes every um and every pause over 0.25 seconds inside the lines i kept, and speeds it up 1.1x. check that no words got clipped at the joins.
```

**step 4: the template**
```
using hyperframes (npx skills add heygen-com/hyperframes), build ONE reusable template that reads my brand.json and an edit.json, and renders captions plus a few graphic types: a hook title, a website screenshot card, a colour block, a list card, a sticker and a carousel. you only fill in edit.json per reel, never design from scratch. render my clip and show me frames at each graphic.
```

**step 5: guardrails**
```
add checks so text can never leave the frame, graphics never cover my face, and captions clear when their phrase ends. measure loudness and background noise after every render and fail the check if they're off.
```

**step 6: a review page (optional, but it's the best part)**
```
make me a private review page where i can watch a live rough cut with my changes applied, tap words to cut them, restore any um or pause that was removed, keep/change/drop each graphic, and edit caption wording. save my decisions so you can read them back, and use the same timing code on the page and in the render.
```

**step 7: make it a skill**
```
turn everything we built into a claude code skill with a SKILL.md, so next time i can just say "edit this into a reel" and drag a video in.
```

---

## mistakes i made so you don't have to

- **rendering bigger than instagram shows.** instagram caps reels at 1080x1920, so anything bigger only made my renders slower. render at 1080p and use two render workers, not all of them.
- **sound effects you can't hear.** generated sounds came out about 20 dB quieter than my voice. measure them; don't trust your ears on laptop speakers.
- **"um"s hiding in the transcript.** whisper (the free transcriber) leaves them out. telling it to expect "um, uh" in a prompt makes it write them down so they can be cut.
- **a fixed silence level.** outdoors, the background never goes quiet enough, so nothing gets cut. set the silence level just above each clip's own background noise.
- **text running off the edge.** long words in big fonts overflow. measure the real width and shrink until it fits, on the page and in the render.
- **screenshots of a "verifying you are human" page.** some sites block automated screenshots. check that a screenshot isn't blank before using it.
- **cutting an "um" that's glued to the next word.** the transcriber sometimes folds it into the next word, so cutting it removes nothing. split it off first.

---

## what it costs

- **claude:** a paid plan (pro or higher). a reel uses a chunk of your session.
- **everything else is free:** ffmpeg, hyperframes, whisper, deepfilternet (noise removal).
- **optional:** elevenlabs for more precise word timing (a few dollars of credit), and a free capcut account for an editable capcut version (not available in the us or india yet).

---

## where things live in this repo

```
skills/reel-editor/SKILL.md          the whole process, for claude
skills/reel-editor/references/       the brand interview, rough cut rules, review page, capcut, motions
skills/reel-editor/review/           the review page and the shared timing engine
skills/reel-editor/scripts/          one script per step
examples/getgitgirl/                 my brand file, as a worked example
```

if you build your own version, i'd love to see it. tag me [@getgitgirl](https://instagram.com/getgitgirl).
