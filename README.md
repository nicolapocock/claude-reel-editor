# claude reel editor

you drop a raw talking-head clip into claude code and get back a finished reel in your own brand, so the audio's cleaned up, the filler words are cut, and the captions and graphics actually match what you're saying. if you want, it also builds a capcut draft where you can change the captions and sounds yourself (the graphics come baked into the video, more on that below).

the first time you use it, it asks you about your brand (your colours, fonts, caption style, sounds and the call to action you always use) and saves that as a brand file, so every edit after that looks like you.

> **status: early.** i've been using this on my own reels and it's getting better every time, but it's not perfect yet… fonts in capcut are still super fussy and text animations get added by hand. the honest list is under [what it can't do yet](#what-it-cant-do-yet).

made by [@getgitgirl](https://instagram.com/getgitgirl).

## what you need

- a mac (that's what i've tested on, windows and linux are untested)
- [claude code](https://claude.com/claude-code) on a paid claude plan. the review page uses claude code's artifacts, and if your version doesn't have them claude just does the review with you in chat instead
- about 10 GB of free disk space
- optional: a free capcut account, for the editable capcut version

## install

if you're new to all this, follow the [step-by-step beginner guide](GUIDE.md), it walks you through everything from scratch.

already use claude code? open it and paste:

```
install the reel editor from github.com/nicolapocock/claude-reel-editor, plus the hyperframes skills it needs, then run its doctor check and fix anything missing
```

or do it yourself in terminal:

```bash
npx skills add heygen-com/hyperframes
```

```bash
npx skills add nicolapocock/claude-reel-editor
```

then check everything's there (ffmpeg, node, the hyperframes skills):

```bash
bash ~/.claude/skills/reel-editor/scripts/doctor.sh
```

## use it

1. film yourself talking to camera (phone is fine)
2. in claude code: **"edit this into a reel"** and drag the video in
3. first time only: answer the brand questions (about 5 minutes)
4. claude sends you a private **reel review** page on your claude.ai account. that's where you:
   - watch the rough cut with your changes applied as you make them (scrub, skip ±5 s)
   - tap words to cut them, and tap any "um" or pause it removed if you want it back
   - keep, change or drop each graphic, with a little mockup of where it sits
   - fix caption wording, pick the highlight words, merge captions
   - hear the sound clean-up and see the colour grade before and after
5. hit **build preview**, tell claude "build preview", and watch the draft (about 4 minutes)
6. leave notes at exact moments in the draft, then say "final" for the full-quality version (and a capcut link, if you turned that on). reels come out at 1080x1920, the biggest size instagram shows. you can pick 4K in setup instead (youtube shorts shows it), but it renders a lot slower and only looks sharper if you filmed in 4K

nothing renders until you've approved it, so your laptop isn't rendering versions you don't want.

## the capcut part (optional)

capcut lets you tweak the captions and sounds yourself after the edit, but it doesn't work everywhere yet.

| where you are | capcut version |
|---|---|
| australia, uk, most of europe and asia | ✅ usually works |
| united states | ❌ capcut's connector isn't available in the us yet |
| india | ❌ the capcut app isn't available |

if it doesn't work where you are, you still get the full finished reel as an mp4.

what you can change in the capcut draft, and what you can't:

- **editable:** the captions (words, timing, style) and the sound effects
- **baked into the video:** the graphics, screenshots, carousels and the hook title. change those on the review page before you build, not in capcut
- **swapped:** capcut can only use fonts from its own library or your capcut brand kit, so captions may look a bit different from the mp4, and some sounds get swapped for the closest one in capcut's library

to turn it on, you add capcut's connector to claude code once. in terminal:

```bash
claude mcp add --transport http --scope user capcut_creation https://www.capcut.com/api/external_mcp
```

then log in to capcut: type `claude` in terminal, then `/mcp`, pick `capcut_creation` and sign in with your capcut account in the browser. the rest of the setup (capcut's helper scripts and fonts) is in [`skills/reel-editor/references/capcut.md`](skills/reel-editor/references/capcut.md), or paste "set up the optional capcut route for the reel editor" into claude code and it walks you through it.

## where your footage goes and what costs extra

- **transcription:** runs on your computer with whisper by default, free. if you add an elevenlabs key (optional, for tighter caption timing), your clip's audio is sent to elevenlabs and that's billed to your elevenlabs account
- **the review page:** small low-res previews of your clip, the graphics and the sound checks are uploaded to a private page on your claude.ai account. only you can see it unless you share it
- **capcut (if you turn it on):** the finished video and caption files are uploaded to your capcut account
- **rendering:** happens on your own laptop, so it costs time, not money. a draft takes a few minutes, a 4K final takes longer
- **claude:** the edit uses your normal claude plan, there's nothing extra to pay

## do i need heygen?

no account or connector needed. hyperframes is made by heygen, but the skills you installed above run on your own computer, so there's nothing to log in to. (heygen's connector is for chat apps that can't run files locally, and for background music, which this setup leaves out.)

## make it yours

everything about how your reels look lives in two files in `~/reels/`:

- `brand.md`: your style in plain english (claude reads this)
- `brand.json`: the numbers (the scripts read this)

edit them any time, or just tell claude "never use outlined captions again" and it adds that to your rules. [`examples/getgitgirl/`](examples/getgitgirl/) is mine, if you want to see a filled-in one.

## what it can't do yet

- **capcut fonts:** the connector only offers a small font list. to use your own font, add it to your capcut brand kit first.
- **text animations in capcut:** you add these by hand (select all captions, pick an animation, about 10 seconds).
- **background music:** not included. add it in capcut or your posting app, where the trending sounds are anyway.
- **multi-camera edits:** it's built for one person talking to camera.
- **windows and linux:** untested. the scripts are written for a mac.

## what's in here

```
skills/reel-editor/
  SKILL.md                     the edit, step by step
  references/setup-interview.md   the brand questions
  references/rough-cut.md      how cuts get proposed
  references/capcut.md         the optional capcut route
  references/review.md         the reel review page, step by step
  review/                      the review page + the timing core it shares with the renderer
  scripts/                     audio cleanup, transcription, cutting, the reel template, qa, delivery, capcut draft
  engine/                      animation library, hyperframes motions and sound effects (downloaded or made on first run)
examples/getgitgirl/           my brand file, as a worked example
```

built on [hyperframes](https://github.com/heygen-com/hyperframes) for the graphics and captions, and capcut's official connector for the editable version.

[MIT](LICENSE)
