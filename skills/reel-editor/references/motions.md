# Motions (HyperFrames catalog, cached in engine/hf)

Use with a `motion` card in edit.json: `{"type":"motion","name":"<name>","start":..,"end":..,"vars":{..},"box":[x,y,w,h]}`.
Carousels also take `"images": [..]` and every slot is filled for you. `box` is where it sits on the 1080x1920 frame (default: full width, top).
Add more from the 392-item catalog: `cd engine/hf && npx hyperframes add <name>` (browse with `npx hyperframes catalog`).

| motion | size | use it for | settings (vars) |
|---|---|---|---|
| carousel-circle-1 | 1920x1080 | lists of tools/examples (the brand's required carousel) | `image1..N` (use images), `speed`, `background` |
| carousel-orbit-1 | 1920x1080 | lists of tools/examples (the brand's required carousel) | `image1..N` (use images), `speed`, `background` |
| carousel-path-1 | 1920x1080 | lists of tools/examples (the brand's required carousel) | `image1..N` (use images), `speed`, `background` |
| carousel-vision-1 | 1920x1080 | lists of tools/examples (the brand's required carousel) | `image1..N` (use images), `speed`, `background` |
| animated-bar-chart | fits box | comparing a few numbers | none (text is in the file) |
| caption-camera-follow | fits box | use the `follow` card instead (brand font + colours) | `accent`, `framing`, `smear` |
| caption-editorial-emphasis | 1920x1080 | don't mount: the template's editorial caption style does this in brand fonts | none (text is in the file) |
| chart-story | fits box | a chart that builds with exact values | `type`, `data`, `labels`, `emphasize`, `unit`, `accent`, `exit` |
| chat-message | fits box | a DM or chat bubble | `type`, `text`, `cardTitle`, `cardDomain`, `tail`, `delivered` |
| code-terminal-run | fits box | a command being typed | `prompt_glyph`, `cadence`, `cues`, `accent`, `exit` |
| count-up | fits box | a number that matters (stats, results) | `start`, `end`, `prefix`, `suffix`, `accent`, `glow`, `exit` |
| hw-arrow | 1920x1080 | point at something on screen | none (text is in the file) |
| hw-underline | 1920x1080 | circle/underline a word or UI element | none (text is in the file) |
| native-notification-pop | fits box | one iOS/macOS notification | `title`, `body`, `app_label`, `os`, `at`, `accent`, `exit` |
| notification-stack | fits box | results / alerts stacking up | `titles`, `bodies`, `expand`, `cues`, `accent`, `exit` |
| oversized-cursor | fits box | a click on a button in a screenshot | `cursor_variant`, `target_x`, `target_y`, `click_label`, `exit` |
| x-follow-card | fits box | follow CTA (X) | none (text is in the file) |
| instagram-follow | 1080x1920 | follow CTA at the end | none (text is in the file) |
| mk-line-graph | 1920x1080 | growth over time | none (text is in the file) |
| yt-comment-card | 1920x1080 | a comment you're replying to | none (text is in the file) |
