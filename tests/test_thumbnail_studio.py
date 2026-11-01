"""Thumbnail studio server: footage list, brand fonts, saved settings, byte ranges, and what it refuses.
Run: python3 tests/test_thumbnail_studio.py   (no dependencies, no network)"""
import importlib.util, json, socket, tempfile, threading, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("studio", ROOT / "skills/reel-editor/scripts/thumbnail_studio.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
FONT = ROOT / "skills/reel-editor/engine/hf/assets/fonts/Caveat-700-latin.woff2"
if not FONT.exists(): print("skipped: run skills/reel-editor/scripts/setup_engine.sh first (the test uses its font)"); raise SystemExit(0)

with tempfile.TemporaryDirectory() as d:
    home = Path(d) / "reels"; reel = home / "2026-01-01-test"; empty = home / "2026-01-02-empty"
    reel.mkdir(parents=True); empty.mkdir()
    (reel / "raw.mov").write_bytes(b"0123456789"); (reel / "master.mp4").write_bytes(b"m"); (reel / "raw.wav").write_bytes(b"w")
    (home / "brand.json").write_text(json.dumps({"colors": {"main": "#ED84B0"}, "title_y": 380, "fonts": {
        "head": {"family": "Caveat", "file": str(FONT), "weight": 700},
        "body": {"family": "Missing", "file": str(Path(d) / "nope.otf")}}}))
    (Path(d) / "secret.txt").write_text("private")

    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = ThreadingHTTPServer(("127.0.0.1", port), m.make_handler(home, port))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}"

    def req(path, data=None, method="GET", headers=None):
        h = {"Content-Type": "application/json", **(headers or {})} if data is not None else (headers or {})
        r = urllib.request.Request(url + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r) as res: return res.status, res.read()
        except urllib.error.HTTPError as e: return e.code, e.read()

    def put(settings, **headers): return req("/api/settings?reel=" + reel.name, json.dumps(settings).encode(), "PUT", headers)[0]

    assert m.running(port) == str(home.resolve()), "health check"
    st, body = req("/"); assert st == 200 and b"thumbnail studio" in body
    c = json.loads(req("/api/reel?reel=" + reel.name)[1])
    assert [x["file"] for x in c["sources"]] == ["master.mp4", "raw.mov"], c["sources"]
    assert all(x["fps"] == 30 for x in c["sources"]), "unreadable video falls back to 30 fps"   # clean master first; raw.wav isn't footage
    assert [f["role"] for f in c["fonts"]] == ["head"], "missing font files are left out, so the page falls back"
    assert c["colors"]["main"] == "#ED84B0" and c["titleY"] == 380 and c["settings"] is None
    assert req(c["fonts"][0]["url"])[1] == FONT.read_bytes()
    assert json.loads(req("/api/reel?reel=" + empty.name)[1])["sources"] == []
    assert json.loads(req("/api/reels")[1])["reels"] == [reel.name], "only reels with footage are offered"
    assert req("/", method="HEAD")[0] == 501, "no stock HEAD handler serving the working folder"
    st, body = req("/api/reel?reel=nope"); assert st == 404 and "No reel folder" in json.loads(body)["error"]

    # byte ranges let the browser seek
    assert req(f"/media?reel={reel.name}&file=raw.mov", headers={"Range": "bytes=2-5"}) == (206, b"2345")
    assert req(f"/media?reel={reel.name}&file=raw.mov", headers={"Range": "bytes=-3"})[1] == b"789"

    # settings round trip, and bad settings never overwrite good ones
    good = dict(source="raw.mov", time=1.25, headline="my ai\nreel editor", font="head", size=120, color="#ed84b0",
                y=400, style="panel", guides={"tall": True, "square": False})
    assert put(good) == 200
    assert json.loads(req("/api/reel?reel=" + reel.name)[1])["settings"] == good
    for bad in ({"time": float("nan")}, {"time": -1}, {"source": "../brand.json"}, {"source": "edit.json"},
                {"headline": "x" * 201}, {"color": "red"}, {"style": "neon"}, {"size": 999}, {"font": "../x"},
                {"guides": {"tall": 1, "square": False}}, {"extra": 1}):
        assert put({**good, **bad}) == 400, bad
    assert put({k: v for k, v in good.items() if k != "y"}) == 400
    assert json.loads(req("/api/reel?reel=" + reel.name)[1])["settings"] == good

    # refusals: other folders, other files, other websites
    for path in ("/media?reel=..&file=secret.txt", f"/media?reel={reel.name}&file=../secret.txt", f"/media?reel={reel.name}&file=raw.wav",
                 f"/media?reel={reel.name}&file=brand.json", "/api/reel?reel=..", "/font?role=body", "/font?role=../x", "/thumbnail.json", "/nope"):
        assert req(path)[0] in (403, 404), path
    assert put(good, Origin="https://example.com") == 403
    assert req("/api/settings?reel=" + reel.name, json.dumps(good).encode(), "PUT", {"Content-Type": "text/plain"})[0] == 403
    assert req("/api/reel?reel=" + reel.name, headers={"Host": "evil.example:80"})[0] == 403          # DNS rebinding
    assert req(f"/media?reel={reel.name}&file=raw.mov", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert req("/", headers={"Sec-Fetch-Site": "cross-site"})[0] == 200                               # the review page's link still opens it
    server.shutdown()
print("PASS: thumbnail studio server (footage, fonts, settings, ranges, refusals)")
