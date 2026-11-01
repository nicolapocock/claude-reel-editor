#!/usr/bin/env python3
"""Thumbnail studio: pick a cover frame and headline for a reel, export PNGs. Runs on this computer only.
The review page lives on claude.ai and can't read local files, so this small server shows your full-quality footage
to the studio page (review/thumbnail.html) at http://127.0.0.1:4848. Nothing is uploaded anywhere.

Usage: python3 thumbnail_studio.py [reel-folder] [--port 4848] [--open]
  Serves every reel in ~/reels (or REELS_HOME). Prints the studio link for [reel-folder] if given; --open opens it.
  Already running? It prints the link again and exits, so it's safe to run any time.
Saves the cover settings to <reel>/thumbnail.json. Footage it offers: raw.* (the raw clip), master.mp4, final.mp4."""
import argparse, json, math, mimetypes, os, re, subprocess, sys, threading, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

PORT = 4848
APP = "reel-thumbnail-studio"
PAGE = Path(__file__).resolve().parents[1] / "review" / "thumbnail.html"
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".webm", ".mkv", ".avi"}
FONT_EXT = {".otf", ".ttf", ".woff", ".woff2"}
STYLES = {"shadow", "panel", "fade"}
LABELS = {"master.mp4": "Clean master", "final.mp4": "Final reel"}


def sources(reel):   # clean master first: graded, no captions or graphics, so it makes the best cover
    raw = [p.name for p in sorted(reel.glob("raw.*")) if p.suffix.lower() in VIDEO_EXT and p.is_file()]
    return [n for n in ("master.mp4",) if (reel / n).is_file()] + raw + [n for n in ("final.mp4",) if (reel / n).is_file()]


def fps(f):   # so the page's 1-frame buttons step one real frame; 30 if ffprobe can't tell
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
                              "-of", "csv=p=0", str(f)], capture_output=True, text=True, timeout=10).stdout.strip()
        n, d = out.split("/"); r = float(n) / float(d)
        return r if 1 <= r <= 240 else 30
    except (OSError, ValueError, ZeroDivisionError, subprocess.SubprocessError): return 30


def source_ok(name):   # what a saved setting may point at, whether or not the file exists today
    return name in LABELS or (name.startswith("raw.") and "/" not in name and Path(name).suffix.lower() in VIDEO_EXT)


def check_settings(d):
    if not isinstance(d, dict): raise ValueError("expected an object")
    keys = {"source", "time", "headline", "font", "size", "color", "y", "style", "guides"}
    if set(d) != keys: raise ValueError("unexpected or missing settings")
    if not isinstance(d["source"], str) or not source_ok(d["source"]): raise ValueError("unknown footage")
    if not isinstance(d["headline"], str) or len(d["headline"]) > 200: raise ValueError("headline too long")
    if not isinstance(d["font"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", d["font"]): raise ValueError("bad font")
    if not isinstance(d["color"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", d["color"]): raise ValueError("bad colour")
    if d["style"] not in STYLES: raise ValueError("bad style")
    for k, lo, hi in (("time", 0, 86400), ("size", 40, 220), ("y", 0, 1920)):
        v = d[k]
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi: raise ValueError("bad " + k)
    g = d["guides"]
    if not isinstance(g, dict) or set(g) != {"tall", "square"} or any(type(x) is not bool for x in g.values()):
        raise ValueError("bad guides")


def make_handler(home, port):
    home = home.expanduser().resolve()
    lock = threading.Lock()
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    def brand():
        try: return json.loads((home / "brand.json").read_text())
        except (OSError, ValueError): return {}

    def font_file(role):
        f = (brand().get("fonts") or {}).get(role) or {}
        p = Path(str(f.get("file", ""))).expanduser()
        return p if f.get("file") and p.suffix.lower() in FONT_EXT and p.is_file() else None

    class Handler(BaseHTTPRequestHandler):   # not SimpleHTTPRequestHandler: its HEAD would serve the working folder
        def log_message(self, *a): pass

        def reel(self, q):   # a folder directly inside the reels workspace, by name only
            name = (q.get("reel") or [""])[0]
            if not name or name.startswith(".") or "/" in name or "\\" in name: return None
            p = (home / name).resolve()
            return p if p.parent == home and p.is_dir() else None

        def allowed(self):
            # DNS-rebinding guard: only answer requests addressed to this machine. Other websites may link to the
            # studio page, but not pull footage or settings into their own pages.
            if self.headers.get("Host") not in hosts: return False
            return self.headers.get("Sec-Fetch-Site") != "cross-site" or urlsplit(self.path).path == "/"

        def do_GET(self):
            if not self.allowed(): return self.send_error(403)
            u = urlsplit(self.path); q = parse_qs(u.query)
            if u.path == "/": return self.send_file(PAGE, "text/html; charset=utf-8")
            if u.path == "/api/health": return self.send_json({"app": APP, "home": str(home)})
            if u.path == "/api/reels":
                names = sorted((p.name for p in home.iterdir() if p.is_dir() and not p.name.startswith(".") and sources(p)), reverse=True) if home.is_dir() else []
                return self.send_json({"reels": names})
            if u.path == "/api/reel":
                r = self.reel(q)
                if not r: return self.send_json({"error": "No reel folder with that name in " + str(home)}, 404)
                b = brand()
                fonts = [{"role": role, "family": f.get("family", role), "weight": f.get("weight", 700), "style": f.get("style", "normal"),
                          "url": "/font?role=" + quote(role)} for role, f in (b.get("fonts") or {}).items() if font_file(role)]
                try: saved = json.loads((r / "thumbnail.json").read_text())
                except (OSError, ValueError): saved = None
                return self.send_json({"name": r.name, "sources": [{"file": n, "label": LABELS.get(n, "Raw clip"), "fps": fps(r / n)} for n in sources(r)],
                                       "fonts": fonts, "colors": b.get("colors") or {}, "titleY": b.get("title_y"), "settings": saved})
            if u.path == "/media":
                r, name = self.reel(q), (q.get("file") or [""])[0]
                if not r or name not in sources(r): return self.send_error(404)
                return self.send_file(r / name)
            if u.path == "/font":
                f = font_file((q.get("role") or [""])[0])
                return self.send_file(f) if f else self.send_error(404)
            self.send_error(404)

        def do_PUT(self):
            u = urlsplit(self.path)
            origin = self.headers.get("Origin")
            if not self.allowed() or (origin and origin.split("//")[-1] not in hosts) or u.path != "/api/settings" \
                    or self.headers.get("Content-Type") != "application/json":
                return self.send_error(403)
            r = self.reel(parse_qs(u.query))
            if not r: return self.send_error(404)
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not 0 < n <= 20000: raise ValueError("bad size")
                d = json.loads(self.rfile.read(n), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
                check_settings(d)
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            with lock:
                tmp = r / "thumbnail.json.tmp"
                tmp.write_text(json.dumps(d, indent=1)); os.replace(tmp, r / "thumbnail.json")
            self.send_json({"saved": True})

        def send_json(self, value, status=200):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def send_file(self, f, ctype=None):   # with byte ranges, so the browser can seek inside long videos
            size = f.stat().st_size; start, end = 0, size - 1
            rng = self.headers.get("Range")
            if rng:
                m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng)
                if not m or not any(m.groups()): return self.send_error(416)
                a, b = m.groups()
                if a: start, end = int(a), min(int(b), end) if b else end
                else: start = max(0, size - int(b))
                if start > end or start >= size:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
            self.send_response(206 if rng else 200)
            self.send_header("Content-Type", ctype or mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-store")
            if rng: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with f.open("rb") as s:
                s.seek(start); left = end - start + 1
                try:
                    while left:
                        chunk = s.read(min(1 << 16, left))
                        if not chunk: break
                        self.wfile.write(chunk); left -= len(chunk)
                except (BrokenPipeError, ConnectionResetError): pass
    return Handler


def running(port):   # what the studio already answering on this port (from an earlier run) serves, or None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as r: h = json.load(r)
        return h.get("home") if h.get("app") == APP else None
    except (OSError, ValueError): return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reel", nargs="?", help="reel folder (or its name) to print the link for")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--open", action="store_true", help="open the studio in your browser")
    a = ap.parse_args()
    home = Path(os.environ.get("REELS_HOME", "~/reels")).expanduser().resolve()
    url = f"http://127.0.0.1:{a.port}/"
    if a.reel:
        r = Path(a.reel).expanduser()
        r = (r if r.is_absolute() or r.exists() else home / a.reel).resolve()
        if r.parent != home or not r.is_dir(): sys.exit(f"{a.reel} isn't a reel folder inside {home}")
        if not sources(r): print(f"Note: no footage in {r.name} yet (raw.mov, raw.mp4, master.mp4 or final.mp4).")
        url += "?reel=" + quote(r.name)
    other = running(a.port)
    if other and other != str(home): sys.exit(f"Port {a.port} has a thumbnail studio for {other}. Run again with --port {a.port + 1}.")
    if other:
        print("Thumbnail studio is already running:", url, flush=True)
        if a.open: webbrowser.open(url)
        return
    try: server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(home, a.port))
    except OSError:
        sys.exit(f"Port {a.port} is busy with another app. Run again with --port {a.port + 1}.")
    print("Thumbnail studio:", url, flush=True)
    if a.open: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass


if __name__ == "__main__": main()
