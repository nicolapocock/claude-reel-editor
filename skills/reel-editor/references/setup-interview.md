# Setup interview

Runs once, before the first edit. Output: `~/reels/brand.md` (for people and for you) and `~/reels/brand.json` (for the scripts).

## How to run it

- **One question at a time.** Plain language, no jargon. Most people installing this are not technical.
- Offer 2-4 concrete options where you can, plus "something else".
- If they say "I don't know", suggest a sensible choice from what they've already told you and move on. Don't stall.
- If they share a reel they love, look at it (download it with `yt-dlp` if you can, or ask for a screenshot) and pull colours, caption style and pacing from it.
- At the end, show a short summary and ask "anything to change?" before writing the files.

## The questions

1. **What's your account about, and who's watching?** (one sentence each)
2. **Show me a reel you wish you'd made.** A link or screenshot. This is the best single input. Ask what they like about it.
3. **Brand colours.** Hex codes if they have them, or describe them ("soft pink and black"). Ask which one is the pop colour.
4. **Colours or styles you never want.** (e.g. "no black text", "no neon")
5. **Fonts.** Headline font and body font if they have them. If not, offer 3 free pairs that fit their vibe (e.g. Google Fonts). Note: CapCut can only use fonts in its own library or the person's CapCut brand kit.
6. **Caption style.** Offer:
   - one word at a time, big and centred
   - short phrases (2-4 words) near the bottom
   - full-sentence subtitles
   Then: highlight colour for key words? Lowercase or sentence case? Any outlines or boxes (many creators now avoid them)?
7. **Graphics energy.** Clean and minimal / playful and scrapbook / bold and editorial. Ask if they have stickers, logos or brand images in a folder.
7a. **How many graphics?** Minimal (one every 8-12 s, mostly you on camera) / balanced (every 4-6 s, the default) / busy (every 2-4 s). → `"graphics": "minimal" | "balanced" | "busy"`.
8. **Sound effects.** None / subtle (a whoosh at cuts) / lots (pops, snaps, dings).
9a. **Carousel.** "Do you want a carousel (a spinning row of images/screenshots) in every reel?" Yes → `"require_carousel": true`.
9. **Pacing.** Natural (normal speed, only long pauses and clear "um"s go; the default) / tight (1.1x, most pauses go) / fast (1.15x, every gap goes). → `"pacing"`. Then: "Any filler words you want kept, or extra ones to cut, like 'like' or 'so'?" (single words only) Only if they change the list, set `"fillers"` (an empty list keeps every filler).
10. **Your usual call to action.** e.g. "comment GUIDE and I'll send it", "follow for part 2". Always at the end?
11. **Where do you post?** Instagram / TikTok / YouTube Shorts / all.
12. **CapCut.** "Do you want an editable CapCut version too, so you can tweak captions and sounds yourself?" If yes, explain plainly: it needs a free CapCut account, and the connector currently doesn't work from the United States, and the CapCut app is not available in India. If they're in either place, set `"capcut": false` and reassure them the MP4 route gives the same finished reel.
13. **Video quality.** 1080p (default: the most Instagram and TikTok show, and works on any computer) or 4K (only worth it for YouTube Shorts and clips filmed in 4K; renders much slower and needs ~35 GB free disk and a recent Mac).

## brand.md - write it in this shape

```markdown
# <name>'s reel brand

## Account
<what it's about> · <who watches>

## Reference reel
<link> - what they love about it: <...>

## Colours
- Main: #...  (what it's for)
- Pop: #...   (key words, buttons)
- Light: #... (backgrounds)
- Never: <...>

## Fonts
- Headlines: <font>
- Body/captions: <font>
- CapCut stand-in (if their font isn't in CapCut): <font>

## Captions
<style, size, case, highlight colour, position, what's banned>

## Graphics
<energy, card style, where their assets folder is>

## Sound
<none / subtle / lots, favourites>

## Pacing
<natural / tight / fast, filler rule, max length>

## Call to action
<their usual CTA>, always at the end

## Rules
<every "never" they've said, added to over time>
```

## brand.json - write it in this shape

```json
{
  "name": "Sam",
  "resolution": [1080, 1920],
  "pacing": "natural",
  "graphics": "balanced",
  "max_seconds": 60,
  "colors": { "main": "#1A1A1A", "pop": "#FF5A36", "light": "#FFF6EE", "caption": "#FFFFFF", "caption_accent": "#FF5A36" },
  "capcut": false,
  "capcut_font": null,
  "sfx": "subtle",
  "deliver_dir": "~/Movies/Reels",
  "grade": null,
  "captions": { "mode": "word", "case": "lower", "size": 104, "y": 1250 },
  "fonts": {
    "head":   { "family": "Montserrat", "file": "~/reels/fonts/Montserrat-Bold.ttf", "weight": 700 },
    "body":   { "family": "Montserrat", "file": "~/reels/fonts/Montserrat-Medium.ttf", "weight": 500 },
    "accent": { "family": "Playfair Display", "file": "~/reels/fonts/PlayfairDisplay-Italic.ttf", "weight": 400, "style": "italic" }
  }
}
```

- `captions.mode`: `word` (one word at a time) or `phrase` (2-4 words). `y` is the caption's distance from the top on a 1920-tall frame (1250 = mid-chest). `case`: `"lower"` makes captions all lowercase; any other value keeps the casing as spoken.
- `fonts`: download the font files into `~/reels/fonts/` (Google Fonts are free: fetch the family's .ttf files from https://fonts.google.com or the google/fonts GitHub repo). No file = a clean system font is used instead. `accent` is the font for accent words: for a plain look, set it to the same file as `head` (or delete it).

- `resolution`: `[1080, 1920]` (default) or `[2160, 3840]` for 4K.
- `capcut_font`: a CapCut font URI (`vimo://...`), filled in later - see capcut.md.
- `grade`: optional ffmpeg colour filter string; leave `null` unless they ask for a look.
- `deliver_dir`: on Windows/Linux use `~/Videos/Reels`. Never a cloud-synced folder (Desktop on iCloud, OneDrive) - big video files make it struggle.

See `examples/` in the repo for a complete filled-in pair.
