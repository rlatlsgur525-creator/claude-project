#!/usr/bin/env python3
"""미라클 쇼츠 스튜디오 — 로컬 웹 툴.  python server.py  →  http://127.0.0.1:8765
프로젝트는 projects/<id>/data.json 에 저장된다(GitHub로 동기화). 영상(mp4)은 저장소에 올리지 않는다.
"""
import json, mimetypes, os, re, subprocess, sys, threading, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote, quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipeline, model

PORT = 8765
LOCK = threading.Lock()  # 렌더는 한 번에 하나
ID_RE = re.compile(r"^[0-9A-Za-z가-힣_\-]{1,60}$")

def proj_path(pid, *rest):
    if not ID_RE.match(pid): raise ValueError("bad id")
    return os.path.join(pipeline.PROJECTS, pid, *rest)

def list_projects():
    out = []
    if not os.path.isdir(pipeline.PROJECTS): return out
    for pid in sorted(os.listdir(pipeline.PROJECTS)):
        f = os.path.join(pipeline.PROJECTS, pid, "data.json")
        if not os.path.exists(f): continue
        d = json.load(open(f, encoding="utf-8"))
        out.append({"id": pid, "title": d.get("title", pid), "template": d["template"],
                    "templateName": pipeline.template(d["template"]).NAME, "review": pipeline.review_status(d),
                    "review_exp": d.get("review_exp", ""),
                    "hasPreview": os.path.exists(proj_path(pid, "final_preview.mp4")),
                    "hasFinal": os.path.exists(proj_path(pid, "final.mp4"))})
    return out

class H(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def do_GET(self):
        u = urlparse(self.path); parts = [unquote(p) for p in u.path.split("/") if p]
        try:
            if u.path in ("/", "/index.html"):
                return self.serve_file(os.path.join(HERE, "index.html"), "text/html; charset=utf-8")
            if u.path == "/api/templates":
                return self.send_json([{"key": k, "name": pipeline.template(k).NAME, "desc": pipeline.template(k).DESC,
                                        "fields": pipeline.template(k).FIELDS} for k in pipeline.TEMPLATES])
            if u.path == "/api/projects": return self.send_json(list_projects())
            if len(parts) == 3 and parts[:2] == ["api", "project"]:
                d = json.load(open(proj_path(parts[2], "data.json"), encoding="utf-8"))
                return self.send_json({**pipeline.defaults(d["template"]), **d})
            if len(parts) == 3 and parts[0] == "files" and parts[2] in ("final.mp4", "final_preview.mp4", "thumbnail.png"):
                return self.serve_file(proj_path(parts[1], parts[2]), mimetypes.guess_type(parts[2])[0])
            if len(parts) >= 4 and parts[0] == "media":  # /media/<pid>/media|library/<파일>
                rel = "/".join(parts[2:]); proj_path(parts[1])
                f = pipeline.media_path(parts[1], rel)
                return self.serve_file(f, mimetypes.guess_type(f)[0] or "application/octet-stream")
            if len(parts) == 3 and parts[:2] == ["api", "srt"]:
                b = pipeline.srt(parts[2]).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "application/x-subrip; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(parts[2] + ".srt"))
                self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
            if len(parts) == 3 and parts[:2] == ["api", "timeline"]:
                return self.send_json(pipeline.timeline(parts[2]))
            if len(parts) == 3 and parts[:2] == ["api", "model"]:
                proj_path(parts[2]); return self.send_json(model.build(parts[2]))
            if len(parts) == 4 and parts[:2] == ["api", "shot-thumb"]:
                proj_path(parts[2]); return self.serve_file(pipeline.shot_thumb(parts[2], parts[3]), "image/png")
            if len(parts) == 4 and parts[0] == "shotclip" and re.match(r"^[0-9A-Za-z_]+__[0-9a-f]{12}\.mp4$", parts[3]):
                return self.serve_file(proj_path(parts[1], "scenes_preview", parts[3]), "video/mp4")
            if len(parts) == 3 and parts[:2] == ["api", "wave"]:
                kind = parse_qs(u.query).get("kind", ["preview"])[0]
                f = proj_path(parts[2], f"wave_{'final' if kind == 'final' else 'preview'}.json")
                return self.send_json(json.load(open(f)) if os.path.exists(f) else {"step": 0.05, "db": []})
            if len(parts) == 2 and parts[0] == "sfx" and parts[1][:-4] in pipeline.sfx_names():
                return self.serve_file(os.path.join(pipeline.SFX_DIR, parts[1]), "audio/wav")
            if len(parts) == 2 and parts[0] == "music" and parts[1] in pipeline.music_files():
                return self.serve_file(os.path.join(pipeline.MUSIC, parts[1]), mimetypes.guess_type(parts[1])[0] or "audio/mpeg")
        except (ValueError, FileNotFoundError):
            return self.send_json({"error": "not found"}, 404)
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path); parts = [unquote(p) for p in u.path.split("/") if p]
        try:
            if u.path == "/api/projects":
                b = self.body(); pid = b["id"].strip()
                if os.path.exists(proj_path(pid)): return self.send_json({"error": "같은 이름의 프로젝트가 있어요"}, 400)
                os.makedirs(proj_path(pid))
                d = {"template": b["template"], "title": b.get("title") or pid, "is_sample": True,
                     "review_no": "", "review_exp": "", **pipeline.defaults(b["template"])}
                json.dump(d, open(proj_path(pid, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                return self.send_json({"id": pid})
            if len(parts) == 3 and parts[:2] == ["api", "project"]:
                d = self.body()
                json.dump(d, open(proj_path(parts[2], "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                return self.send_json({"ok": True})
            if u.path == "/api/open-music":
                os.makedirs(pipeline.MUSIC, exist_ok=True); os.startfile(pipeline.MUSIC)
                return self.send_json({"ok": True})
            if len(parts) == 3 and parts[:2] == ["api", "open-media"]:
                d = proj_path(parts[2], "media"); os.makedirs(d, exist_ok=True); os.startfile(d)
                return self.send_json({"ok": True})
            if len(parts) == 3 and parts[:2] == ["api", "upload"]:  # 본문 = 파일 바이트, ?name=파일이름
                name = os.path.basename(parse_qs(u.query).get("name", ["file"])[0]).replace(" ", "_")
                if not re.match(r"^[0-9A-Za-z가-힣_.\-()]{1,120}$", name): return self.send_json({"error": "파일 이름에 쓸 수 없는 글자가 있어요"}, 400)
                d = proj_path(parts[2], "media"); os.makedirs(d, exist_ok=True)
                n = int(self.headers.get("Content-Length", 0)); data = self.rfile.read(n)
                stem, ext = os.path.splitext(name); f = os.path.join(d, name); k = 1
                while os.path.exists(f): f = os.path.join(d, f"{stem}_{k}{ext}"); k += 1
                open(f, "wb").write(data)
                if ext.lower() == ".webm":  # 브라우저 녹음 → wav
                    wav = os.path.splitext(f)[0] + ".wav"
                    subprocess.run([pipeline.gfx.ffmpeg_bin(), "-v", "error", "-y", "-i", f, "-ar", "48000", "-ac", "2", wav], check=True)
                    os.remove(f); f = wav
                rel = "media/" + os.path.basename(f)
                dur = pipeline.probe_dur(f) if not f.lower().endswith(pipeline.IMG_EXT) else 0
                return self.send_json({"path": rel, "dur": dur})
            if len(parts) == 4 and parts[:2] == ["api", "shot-render"]:  # 이 장면만 미리보기로 렌더
                if not LOCK.acquire(blocking=False): return self.send_json({"ok": False, "errors": ["다른 영상을 만드는 중이에요."]})
                try:
                    path, drawn = pipeline.shot_preview_clip(parts[2], parts[3])
                    return self.send_json({"ok": True, "url": f"/shotclip/{parts[2]}/{os.path.basename(path)}", "drawn": drawn})
                finally: LOCK.release()
            if len(parts) == 3 and parts[:2] == ["api", "thumb"]:
                t = float(parse_qs(u.query).get("t", ["0"])[0]); pipeline.thumbnail(parts[2], t)
                return self.send_json({"url": f"/files/{parts[2]}/thumbnail.png"})
            if len(parts) == 3 and parts[:2] == ["api", "render"]:
                preview = parse_qs(u.query).get("preview", ["1"])[0] == "1"
                if not LOCK.acquire(blocking=False): return self.send_json({"ok": False, "errors": ["다른 영상을 만드는 중이에요. 잠시 뒤 다시 눌러 주세요."]})
                try: return self.send_json(pipeline.render(parts[2], preview))
                finally: LOCK.release()
        except ValueError:
            return self.send_json({"error": "잘못된 이름"}, 400)
        except Exception as e:
            return self.send_json({"ok": False, "errors": [f"{type(e).__name__}: {e}"]}, 500)
        self.send_json({"error": "not found"}, 404)

    def serve_file(self, path, ctype):
        size = os.path.getsize(path); rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-"); start = int(a or 0); end = int(b) if b else size - 1
            self.send_response(206); self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start); left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk: break
                try: self.wfile.write(chunk)
                except ConnectionError: break
                left -= len(chunk)

if __name__ == "__main__":
    os.makedirs(pipeline.PROJECTS, exist_ok=True); os.makedirs(pipeline.MUSIC, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print(f"미라클 쇼츠 스튜디오: {url}  (끄려면 이 창을 닫으세요)")
    if "--no-browser" not in sys.argv: webbrowser.open(url)
    srv.serve_forever()
