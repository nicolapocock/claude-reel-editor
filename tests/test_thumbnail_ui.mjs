// Thumbnail studio in a real browser: sampled frames + seeking, brand fonts with fallback, settings surviving a reload,
// PNG export sizes, crop guides kept out of downloads, and helpful errors for missing or unplayable footage.
// Run: node tests/test_thumbnail_ui.mjs   (needs Node 22+, ffmpeg and Google Chrome; set CHROME=/path/to/chrome if it's elsewhere)
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, copyFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { createServer } from "node:net";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SKILL = join(ROOT, "skills/reel-editor");
if (!existsSync(join(SKILL, "engine/hf/assets/fonts/Caveat-700-latin.woff2"))) { console.log("skipped: run skills/reel-editor/scripts/setup_engine.sh first (the test uses its font)"); process.exit(0); }
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (!existsSync(CHROME)) { console.log("SKIP: Google Chrome not found (set CHROME=/path/to/chrome)"); process.exit(0); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------- a throwaway reels workspace ----------
const tmp = mkdtempSync(join(tmpdir(), "thumb-ui-")), home = join(tmp, "reels"), reel = join(home, "2026-01-01-test");
mkdirSync(reel, { recursive: true }); mkdirSync(join(home, "2026-01-02-empty"));
copyFileSync(join(SKILL, "engine/hf/assets/fonts/Caveat-700-latin.woff2"), join(tmp, "Head.woff2"));
writeFileSync(join(tmp, "Broken.otf"), "this is not a font");
writeFileSync(join(home, "brand.json"), JSON.stringify({ colors: { main: "#ED84B0", light: "#FFEEF5" }, title_y: 380, fonts: {
  head: { family: "Caveat", file: join(tmp, "Head.woff2"), weight: 700 },
  body: { family: "Broken", file: join(tmp, "Broken.otf"), weight: 400 } } }));
// 3 s test video whose red channel rises with time (255 * t / 3), so a pixel tells us which frame is showing
execFileSync("ffmpeg", ["-v", "error", "-f", "lavfi", "-i", "color=c=black:s=270x480:r=30:d=3", "-vf", "format=rgb24,geq=r='255*T/3':g='0':b='0'",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", join(reel, "master.mp4")]);
writeFileSync(join(reel, "raw.avi"), "not really a video");

// ---------- studio server + headless Chrome ----------
const port = await new Promise(ok => { const s = createServer().listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); }), base = `http://127.0.0.1:${port}/`;
const server = spawn("python3", [join(SKILL, "scripts/thumbnail_studio.py"), "--port", port], { env: { ...process.env, REELS_HOME: home }, stdio: "ignore" });
const profile = join(tmp, "chrome");
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run", "--mute-audio", "about:blank"], { stdio: "ignore" });
let ws, id = 0; const pending = new Map();
function cdp(method, params = {}) { return new Promise((ok, fail) => { const i = ++id; pending.set(i, { ok, fail }); ws.send(JSON.stringify({ id: i, method, params })); }); }
async function js(expr) {
  const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
async function until(expr, what, ms = 20000) {
  for (const end = Date.now() + ms; Date.now() < end; await sleep(100)) { try { if (await js(expr)) return; } catch {} }
  throw new Error("timed out waiting for " + what + " (status: " + await js(`document.querySelector('#status')?.textContent`).catch(() => "?") + ")");
}
async function open(query) { await cdp("Page.navigate", { url: base + query }); await sleep(300); await until(`document.readyState === "complete"`, "page load"); }
const redAt = `(() => document.querySelector('#cover').getContext('2d').getImageData(20, 20, 1, 1).data[0])()`;
const close = (a, b, tol, what) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

try {
  let port_ = null;
  for (let i = 0; i < 100 && !port_; i++, await sleep(100)) { try { port_ = readFileSync(join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; } catch {} }
  const targets = await (await fetch(`http://127.0.0.1:${port_}/json/list`)).json();
  ws = new WebSocket(targets.find(t => t.type === "page").webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));
  ws.addEventListener("message", e => { const m = JSON.parse(e.data); const p = pending.get(m.id); if (p) { pending.delete(m.id); m.error ? p.fail(new Error(m.error.message)) : p.ok(m.result); } });
  await cdp("Page.enable"); await cdp("Browser.setDownloadBehavior", { behavior: "deny" });
  let up = false; for (let i = 0; i < 50 && !up; i++, await sleep(100)) { try { up = (await fetch(base + "api/health")).ok; } catch {} }
  if (!up) throw new Error("the thumbnail studio server didn't start on port " + port);

  // 1. six evenly spaced sampled frames; picking one and the slider both land on the exact frame
  await open("?reel=2026-01-01-test");
  await until(`document.querySelectorAll('#samples button').length === 6`, "six sampled frames");
  const times = await js(`[...document.querySelectorAll('#samples button')].map(b => +b.dataset.t)`);
  const dur = await js(`document.querySelector('#video').duration`);
  times.forEach((t, i) => close(t, dur * (i + 1) / 7, 0.01, "sample " + i));
  assert.match(await js(`document.querySelector('main').textContent`), /sampled frames/i);
  assert.doesNotMatch(await js(`document.querySelector('main').textContent`), /\bbest\b/i, "never claims to pick the best frame");
  await js(`document.querySelectorAll('#samples button')[3].click()`);
  await until(`Math.abs(document.querySelector('#video').currentTime - ${times[3]}) < 0.02 && document.querySelectorAll('#samples button')[3].getAttribute('aria-pressed') === 'true'`, "sample seek");
  await until(`Math.abs(${redAt} - ${255 * times[3] / 3}) < 25`, "the picked frame on the cover");
  await js(`(() => { const s = document.querySelector('#seek'); s.value = 2.5; s.dispatchEvent(new Event('input')); })()`);
  await until(`Math.abs(document.querySelector('#video').currentTime - 2.5) < 0.02`, "slider seek");
  await until(`Math.abs(${redAt} - 212) < 25`, "the slider's frame on the cover");
  await js(`document.querySelector('#next').click()`);
  await until(`Math.abs(document.querySelector('#video').currentTime - (2.5 + 1/30)) < 0.02`, "one frame forward");

  // 2. brand fonts load; a broken one falls back to system sans and says so
  assert.deepEqual(await js(`[...document.querySelector('#font').options].map(o => o.value)`), ["system", "head"]);
  assert.equal(await js(`document.querySelector('#font').value`), "head");
  assert.ok(await js(`document.fonts.check('700 50px "brand-head"')`), "brand font registered");
  assert.match(await js(`document.querySelector('#status').textContent`), /Broken font.*system sans/);

  // 3. long headlines wrap, keep manual line breaks and stay inside the frame
  await js(`(() => { const set = (s, v) => { const e = document.querySelector(s); e.value = v; e.dispatchEvent(new Event('input')); };
    set('#headline', 'this headline is long enough that it has to wrap onto several lines\\nsupercalifragilisticexpialidociouslywordy'); set('#size', 220); set('#y', 1920); })()`);
  const L = await js(`window.coverLayout`);
  assert.ok(L.lines.length >= 4 && L.widest <= 900 && L.top >= 96 && L.bottom <= 1824, JSON.stringify(L));
  assert.ok(L.lines.some(l => l.startsWith("supercal")), "manual line break kept");

  // 4. settings survive a reload
  await js(`(() => { document.querySelector('#style [data-v=panel]').click(); document.querySelector('.sw[data-c="#FFEEF5"]').click();
    const g = document.querySelector('#gtall'); g.checked = true; g.dispatchEvent(new Event('change'));
    const s = document.querySelector('#seek'); s.value = 1.5; s.dispatchEvent(new Event('input')); })()`);
  await until(`Math.abs(document.querySelector('#video').currentTime - 1.5) < 0.02`, "seek before reload");
  await sleep(900);   // autosave debounce
  const saved = JSON.parse(readFileSync(join(reel, "thumbnail.json"), "utf8"));
  assert.equal(saved.style, "panel"); assert.equal(saved.color, "#FFEEF5"); close(saved.time, 1.5, 0.02, "saved time");
  await open("?reel=2026-01-01-test");
  await until(`document.querySelectorAll('#samples button').length === 6`, "reload");
  assert.match(await js(`document.querySelector('#headline').value`), /^this headline is long[\s\S]*\nsupercal/);
  assert.equal(await js(`document.querySelector('#style [aria-pressed=true]').dataset.v`), "panel");
  assert.equal(await js(`document.querySelector('#gtall').checked && !document.querySelector('#gTall').hidden`), true);
  assert.equal(await js(`document.querySelector('#source').value`), "master.mp4");
  assert.equal(await js(`document.querySelector('#font').value`), "head");
  close(await js(`document.querySelector('#video').currentTime`), 1.5, 0.02, "restored frame");

  // 5. PNG exports at the three sizes, and crop guides never in them
  await js(`(() => { window.__blobs = []; const real = URL.createObjectURL; URL.createObjectURL = b => { window.__blobs.push(b); return real(b); }; })()`);
  const exportAll = `(async () => { window.__blobs = []; for (const [k, b] of [...document.querySelectorAll('.export')].entries()) {
      b.click(); while (window.__blobs.length < k + 1) await new Promise(r => setTimeout(r, 50)); }
    return Promise.all(window.__blobs.map(async b => { const i = await createImageBitmap(b); const c = new OffscreenCanvas(i.width, i.height); const x = c.getContext('2d'); x.drawImage(i, 0, 0);
      const d = x.getImageData(0, 0, i.width, i.height).data; let h = 0; for (let k = 0; k < d.length; k += 7) h = (h * 31 + d[k]) | 0; return { type: b.type, w: i.width, h: i.height, sum: h }; })); })()`;
  await js(`(() => { for (const id of ['#gtall', '#gsquare']) { const g = document.querySelector(id); g.checked = true; g.dispatchEvent(new Event('change')); } })()`);
  assert.ok(await js(`document.querySelector('#gSquare').offsetHeight > 0 && document.querySelector('#gTall').offsetHeight > 0`), "guides visible on screen");
  const withGuides = await js(exportAll);
  assert.deepEqual(withGuides.map(x => [x.type, x.w, x.h]), [["image/png", 1080, 1920], ["image/png", 1080, 1440], ["image/png", 1080, 1080]]);
  await js(`(() => { for (const id of ['#gtall', '#gsquare']) { const g = document.querySelector(id); g.checked = false; g.dispatchEvent(new Event('change')); } })()`);
  const without = await js(exportAll);
  assert.deepEqual(withGuides.map(x => x.sum), without.map(x => x.sum), "downloads are identical with guides on or off");

  // 6. footage the browser can't play, a reel with no footage, and a reel that doesn't exist
  await js(`(() => { const s = document.querySelector('#source'); s.value = 'raw.avi'; s.dispatchEvent(new Event('change')); })()`);
  await until(`/can't play raw\\.avi/.test(document.querySelector('#status').textContent)`, "unplayable footage message");
  // switching footage quickly never leaves a mixed or broken frame strip
  await js(`(() => { const s = document.querySelector('#source'); for (const v of ['master.mp4', 'raw.avi', 'master.mp4']) { s.value = v; s.dispatchEvent(new Event('change')); } })()`);
  await until(`document.querySelectorAll('#samples button').length === 6`, "frames after switching footage");
  await sleep(1500);
  assert.equal(await js(`document.querySelectorAll('#samples button').length`), 6);
  assert.doesNotMatch(await js(`document.querySelector('#status').textContent`), /took too long|Couldn't sample/);
  await open("?reel=2026-01-02-empty");
  await until(`/No footage in this reel folder/.test(document.querySelector('#status').textContent)`, "no footage message");
  await open("?reel=nope");
  await until(`/No reel folder with that name/.test(document.querySelector('#status').textContent)`, "missing reel message");
  await open("");
  await until(`document.querySelector('.side a')?.textContent === '2026-01-01-test'`, "reel picker");
  console.log("PASS: thumbnail studio UI (frames + seeking, fonts + fallback, wrap, reload, 3 PNG sizes, guides excluded, errors)");
} finally {
  ws?.close(); chrome.kill(); server.kill();
  await sleep(300); rmSync(tmp, { recursive: true, force: true });
}
