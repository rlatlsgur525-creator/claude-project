"""프로젝트(data.json) → 타임라인 조립 → 장면 클립(캐시) → edl.json → build.py 렌더 → 점검·음량.
템플릿 모듈 규약: NAME, DESC, FIELDS, CAP_KEYS, validate(data) -> [오류], build(data) -> (scenes, captions, sfx, note)
  scenes: [(이름, 초, draw_fn(d, t))]   captions: [(시작, 끝, 문구[, anim])]   note: 준법 표기 둘째 줄
  CAP_KEYS: captions 순서대로 그 문구를 만드는 FIELDS 키

시간 규칙
  - 템플릿이 만든 자막·효과음은 '원래 시간'이고, edits(끼워넣기·구간 삭제)를 차례로 적용해 '최종 시간'으로 옮긴다.
  - 사용자가 넣거나 고친 것(tl.cap_times, tl.sfx, texts, overlays, voices, markers)은 모두 '최종 시간'으로 저장한다.
    끼워넣기·구간 삭제를 할 때 화면(UI)이 이 값들도 함께 민다(프리미어의 리플 편집과 같다).
data.json 편집 키
  edits:    [{type:"insert", at, dur, kind:"image|video|color", src, in, color, fit, vol} | {type:"cut", a, b}]
  texts:    [{start, end, text, style, pos:[x,y], size, color, anim}]   직접 넣은 글자
  overlays: [{src, start, end, x, y, w, fade, in, vol}]                 이미지·영상·마스코트를 위에 얹기
  voices:   [{src, offset, vol, dur}]                                   내레이션 녹음·파일
  markers:  [{t, label}]   tl.cap_times / tl.sfx   bgm: {file, vol, duck, start, fade_in, fade_out}
미디어 경로: "media/파일"(프로젝트 폴더) 또는 "library/파일"(studio/library, 마스코트 등 공용)
"""
import hashlib, importlib, json, os, re, subprocess, sys
from datetime import date
import numpy as np
import gfx

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "shorts-kit", "build.py")
SFX_DIR = os.path.join(HERE, "..", "shorts-kit", "sfx")
PROJECTS = os.path.join(HERE, "projects")
MUSIC = os.path.join(HERE, "music")
LIBRARY = os.path.join(HERE, "library")
TEMPLATES = ["terms_survey", "warning", "experiment"]
MAX_SEC = 60  # 1분 초과 쇼츠는 음악 저작권 신고 시 차단될 수 있어 기본 상한으로 둔다
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
VID_EXT = (".mp4", ".mov", ".m4v", ".webm")
# 장면 그림에 영향을 주지 않는 키 → 바뀌어도 장면 클립을 다시 그리지 않는다
NON_SCENE = {"title", "review_no", "review_exp", "tl", "bgm", "edits", "texts", "overlays", "voices", "markers", "upload",
             "shots", "shot_order", "schema_version", "voice", "_speech"}  # is_sample은 그림의 "(예시)"에도 쓰여 제외하지 않는다

def template(key):
    return importlib.import_module("templates." + key)

def defaults(key):
    return {f["key"]: f["default"] for f in template(key).FIELDS if "key" in f}

def load(pid):
    data = json.load(open(os.path.join(PROJECTS, pid, "data.json"), encoding="utf-8"))
    return {**defaults(data["template"]), **data}

def data_hash(data):
    return hashlib.sha1(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]

def sfx_names():
    return sorted(f[:-4] for f in os.listdir(SFX_DIR) if f.endswith(".wav"))

def music_files():
    if not os.path.isdir(MUSIC): return []
    return sorted(f for f in os.listdir(MUSIC) if f.lower().endswith(AUDIO_EXT))

def media_path(pid, rel):
    """'media/x.png' → 프로젝트 폴더, 'library/x.png' → 공용 라이브러리. 폴더 밖 경로는 거부."""
    if rel.startswith("library/"): base, sub = LIBRARY, rel[len("library/"):]
    elif rel.startswith("media/"): base, sub = os.path.join(PROJECTS, pid, "media"), rel[len("media/"):]
    else: raise ValueError("bad media path")
    base = os.path.normpath(base); p = os.path.normpath(os.path.join(base, sub))
    if not p.startswith(base + os.sep): raise ValueError("bad media path")
    return p

def media_list(pid):
    out = []
    for kind, folder, prefix in [("project", os.path.join(PROJECTS, pid, "media"), "media/"), ("library", LIBRARY, "library/")]:
        if not os.path.isdir(folder): continue
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                typ = "image" if ext in IMG_EXT else "video" if ext in VID_EXT and ext != ".webm" else "audio" if ext in AUDIO_EXT else None
                if not typ: continue
                rel = os.path.relpath(os.path.join(root, f), folder).replace("\\", "/")
                out.append({"path": prefix + rel, "name": rel, "type": typ, "where": kind})
    return out

def probe_dur(path):
    p = subprocess.run([gfx.ffmpeg_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try: return round(float(p.stdout.strip()), 3)
    except ValueError: return 0.0

def compliance_line(data):
    """화면 하단 small 자막. 심의필이 없으면 '게시 불가' 표기를 강제한다."""
    first = []
    if data.get("is_sample", True): first.append("예시 데이터")
    no, exp = data.get("review_no", "").strip(), data.get("review_exp", "").strip()
    first.append(f"심의필 {no}" + (f" (~{exp})" if exp else "") if no else "심의 전 · 게시 불가")
    return " · ".join(first)

def review_status(data):
    no, exp = data.get("review_no", "").strip(), data.get("review_exp", "").strip()
    if not no: return "심의 전"
    if exp and exp < date.today().isoformat(): return "심의 만료"
    return "심의 완료"

# ---------------- 리플 편집 ----------------
def apply_edits(pieces, edits):
    """pieces: [{kind, dur, ...}] 연속 배치. edits 순서대로 끼워넣기·구간 삭제 → (pieces, 시간 변환 함수 목록)"""
    maps = []
    for ed in edits:
        total = sum(p["dur"] for p in pieces)
        if ed.get("type") == "insert":
            t = min(max(0.0, float(ed["at"])), total); d = max(0.05, float(ed["dur"]))
            out, acc, done = [], 0.0, False
            for p in pieces:
                if not done and acc <= t < acc + p["dur"] - 1e-6 and t > acc + 1e-6:
                    a, b = dict(p), dict(p); cut = t - acc
                    a["dur"] = cut; b["dur"] = p["dur"] - cut; b["in"] = p.get("in", 0) + cut
                    out += [a, {**ed, "kind": ed.get("kind", "color"), "dur": d, "insert": True}, b]; done = True
                elif not done and abs(acc - t) < 1e-6:
                    out += [{**ed, "kind": ed.get("kind", "color"), "dur": d, "insert": True}, p]; done = True
                else:
                    out.append(p)
                acc += p["dur"]
            if not done: out.append({**ed, "kind": ed.get("kind", "color"), "dur": d, "insert": True})
            pieces = out
            maps.append(("insert", t, d))
        elif ed.get("type") == "cut":
            a, b = sorted([float(ed["a"]), float(ed["b"])]); a = max(0.0, a); b = min(total, b)
            if b - a < 0.02: continue
            out, acc = [], 0.0
            for p in pieces:
                s, e = acc, acc + p["dur"]; acc = e
                if e <= a or s >= b: out.append(p); continue
                if s < a:  # 앞부분 남김
                    q = dict(p); q["dur"] = a - s; out.append(q)
                if e > b:  # 뒷부분 남김
                    q = dict(p); q["dur"] = e - b; q["in"] = p.get("in", 0) + (b - s); out.append(q)
            pieces = out
            maps.append(("cut", a, b))
    return pieces, maps

def map_time(x, maps, end=False):
    for kind, a, b in maps:
        if kind == "insert":
            if x > a + 1e-6 or (not end and abs(x - a) < 1e-6): x += b
        else:
            if x >= b: x -= (b - a)
            elif x > a: x = a
    return round(x, 3)

# ---------------- 조립 ----------------
def speech_spans(path):
    """녹음 파일의 말소리 구간 [(시작, 끝)] — 말하는 마스코트의 말하기/대기 전환용. 파일 수정 시각으로 캐시."""
    cf = path + ".speech.json"
    if os.path.exists(cf):
        c = json.load(open(cf))
        if c.get("mtime") == os.path.getmtime(path): return c["spans"]
    p = subprocess.run([gfx.ffmpeg_bin(), "-hide_banner", "-i", path, "-af", "silencedetect=noise=-34dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    spans, cur = [], 0.0
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m and float(m.group(1)) - cur > 0.08: spans.append([round(cur, 3), round(float(m.group(1)), 3)])
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m: cur = float(m.group(1))
    d = probe_dur(path)
    if d - cur > 0.08: spans.append([round(cur, 3), round(d, 3)])
    json.dump({"mtime": os.path.getmtime(path), "spans": spans}, open(cf, "w"))
    return spans

def assemble(full, pid=None, scale=None):
    """→ dict: scenes(그리기 함수), pieces, captions(템플릿), texts, sfx, overlays, voices, small, bgm, total"""
    T = template(full["template"])
    v = full.get("voice") or {}
    if pid and v.get("src"):
        try: full["_speech"] = speech_spans(media_path(pid, v["src"]))
        except (ValueError, OSError): full["_speech"] = None
    out = T.build(full)
    scenes, captions, sfx, note = out[:4]
    extras = out[4] if len(out) > 4 else {}
    shots = shot_layout(full, scenes)
    smap = shot_time_map(shots)  # 템플릿 시간 → 장면 배치 반영 시간 (배치가 기본이면 그대로)
    captions = [(*smap.span(c[0], c[1]), *c[2:]) for c in captions]
    sfx = [{**s, "t": smap.point(s["t"])} for s in sfx]
    pieces = []
    for s in shots:
        if s["hidden"]: continue
        p = {"kind": s["kind"], "name": s["id"], "shot": s["id"], "label": s["label"], "dur": s["dur"], "in": float(s.get("in") or 0)}
        if s["kind"] != "scene": p.update({k: s[k] for k in ("src", "color", "fit", "vol") if s.get(k) is not None})
        pieces.append(p)
    pieces, maps = apply_edits(pieces, full.get("edits") or [])
    total = round(sum(p["dur"] for p in pieces), 3)
    keys = list(getattr(T, "CAP_KEYS", []))
    caps = []
    for i, c in enumerate(captions):
        if c[0] is None: s = e = 0.0  # 숨긴 장면에 있던 자막
        else: s, e = map_time(c[0], maps), map_time(c[1], maps, end=True)
        caps.append({"start": s, "end": e, "text": c[2], "style": extras.get("cap_style", "main"), **({"anim": c[3]} if len(c) > 3 else {}),
                     **({"pos": extras["cap_pos"]} if extras.get("cap_pos") else {}),
                     "key": keys[i] if i < len(keys) else None, "idx": i, "gone": e - s < 0.05})
    tl = full.get("tl") or {}
    times = tl.get("cap_times")
    custom_caps = bool(times and len(times) == len(caps))
    if custom_caps:
        for c, (s, e) in zip(caps, times):
            c["start"], c["end"] = max(0.0, float(s)), min(total, float(e)); c["gone"] = c["end"] - c["start"] < 0.05
    if tl.get("sfx") is not None:
        sfx_out = tl["sfx"]
    else:
        sfx_out = []
        for s in sfx:
            if s["t"] is None: continue  # 숨긴 장면의 효과음
            t = map_time(s["t"], maps)
            if any(k == "cut" and a < s["t"] < b for k, a, b in maps): continue
            sfx_out.append({**s, "t": t})
    clamp = lambda items, k0, k1: [dict(o) for o in items if float(o[k0]) < total]
    small = {"start": 0.0, "end": total, "text": compliance_line(full) + "/" + note, "style": "small", "anim": "none",
             **({"pos": extras["small_pos"]} if extras.get("small_pos") else {}), **({"size": extras["small_size"]} if extras.get("small_size") else {})}
    bgm = full.get("bgm") or None
    if bgm and not bgm.get("file"): bgm = None
    t = 0.0
    for p in pieces: p["start"] = round(t, 3); t += p["dur"]
    mascot, t = [], 0.0
    for name, a, d in extras.get("mascot_track") or []:
        mascot.append({"clip": name, "in": a, "start": round(t, 3), "dur": d}); t += d
    return {"scenes": scenes, "pieces": pieces, "captions": caps, "texts": clamp(full.get("texts") or [], "start", "end"),
            "sfx": sfx_out, "overlays": clamp(full.get("overlays") or [], "start", "end"),
            "voices": [dict(v) for v in (full.get("voices") or []) if float(v["offset"]) < total],
            "tvoices": extras.get("voices") or [], "mascot": mascot, "mascot_box": extras.get("mascot_box"),
            "small": small, "bgm": bgm, "total": total, "markers": full.get("markers") or [], "shots": shots,
            "custom": {"cap_times": custom_caps, "sfx": tl.get("sfx") is not None}}

# ---------------- 장면(Shot) 층 ----------------
SHOT_KINDS = ("scene", "image", "video", "color")

def shot_layout(full, scenes):
    """템플릿 장면 + 장면 덮어쓰기(data.shots, data.shot_order) → 순서대로 장면 목록(숨긴 장면 포함).
    shots[ID] 키: dur, kind(scene|image|video|color), src, color, fit, in, vol, purpose, desc, hidden, keyframes, user"""
    info = getattr(template(full["template"]), "SHOTS", {})
    ov = full.get("shots") or {}
    out, t = [], 0.0
    for i, (n, d, fn) in enumerate(scenes):
        o = ov.get(n) or {}
        out.append({"id": n, "user": False, "label": f"장면 {i + 1}", "tstart": round(t, 3), "tdur": d,
                    "dur": round(float(o.get("dur") or d), 3), "kind": o.get("kind") or "scene", "fn": fn,
                    "src": o.get("src"), "color": o.get("color"), "fit": o.get("fit"), "in": o.get("in"), "vol": o.get("vol"),
                    "purpose": o.get("purpose") or info.get(n, {}).get("purpose", ""), "desc": o.get("desc") or info.get(n, {}).get("desc", ""),
                    "hidden": bool(o.get("hidden")), "keyframes": o.get("keyframes") or []})
        t += d
    for k, o in ov.items():
        if not o.get("user"): continue
        out.append({"id": k, "user": True, "label": o.get("label") or "추가 장면", "tstart": None, "tdur": 0.0,
                    "dur": round(float(o.get("dur") or 2.0), 3), "kind": o.get("kind") or "color", "fn": None,
                    "src": o.get("src"), "color": o.get("color") or "#0e1116", "fit": o.get("fit"), "in": o.get("in"), "vol": o.get("vol"),
                    "purpose": o.get("purpose") or "", "desc": o.get("desc") or "", "hidden": bool(o.get("hidden")),
                    "keyframes": o.get("keyframes") or []})
    order = [i for i in (full.get("shot_order") or []) if any(s["id"] == i for s in out)]
    seq = [next(s for s in out if s["id"] == i) for i in order] + [s for s in out if s["id"] not in order]
    t = 0.0
    for k, s in enumerate(seq):
        s["index"] = k + 1; s["start"] = None if s["hidden"] else round(t, 3)
        if not s["hidden"]: t += s["dur"]
    return seq

class ShotTimeMap:
    """템플릿 시간 → 장면 순서·길이가 바뀐 뒤의 시간. 항목은 '시작 시각이 속한 장면'을 따라가고 그 장면 길이 안으로 잘린다.
    숨긴 장면에 속하면 None. 배치가 템플릿 기본(순서·길이 같음, 사용자 장면 없음)이면 그대로 돌려준다."""
    def __init__(self, shots):
        self.tmpl = sorted([s for s in shots if not s["user"]], key=lambda s: s["tstart"])  # 템플릿 원래 순서
        self.default = [s["id"] for s in shots if not s["hidden"]] == [s["id"] for s in self.tmpl] and \
            all(abs(s["dur"] - s["tdur"]) < 1e-6 for s in self.tmpl)
    def shot_of(self, x):
        for s in self.tmpl:
            if s["tstart"] - 1e-6 <= x < s["tstart"] + s["tdur"] - 1e-6: return s
        return self.tmpl[-1] if self.tmpl else None
    def point(self, x):
        if self.default: return x
        s = self.shot_of(x)
        if s is None or s["hidden"]: return None
        return round(s["start"] + max(0.0, min(x - s["tstart"], s["dur"] - 0.05)), 3)
    def span(self, a, b):
        if self.default: return a, b
        s = self.shot_of(a)
        if s is None or s["hidden"]: return None, None
        a2 = s["start"] + max(0.0, min(a - s["tstart"], s["dur"] - 0.05))
        b2 = s["start"] + max(0.05, min(b - s["tstart"], s["dur"]))
        return round(a2, 3), round(max(a2 + 0.05, b2), 3)

def shot_time_map(shots):
    return ShotTimeMap(shots)

ANIM_DIR = os.path.join(LIBRARY, "anim")

def mascot_track_file(pid, track, preview):
    """마스코트 동작 조각들을 하나의 초록 배경 영상으로 이어 붙인다 (조각 목록이 같으면 재사용)."""
    clips = json.load(open(os.path.join(ANIM_DIR, "clips.json"), encoding="utf-8"))
    key = data_hash({"t": [[m["clip"], m["in"], m["dur"]] for m in track], "p": preview, "c": clips})
    out = os.path.join(PROJECTS, pid, f"mascot_{'p' if preview else 'f'}.mp4"); mf = out + ".key"
    if os.path.exists(out) and os.path.exists(mf) and open(mf).read() == key: return out
    inputs, fc = [], []
    for i, m in enumerate(track):
        inputs += ["-i", os.path.join(ANIM_DIR, clips[m["clip"]]["file"])]
        sz = "540:720" if preview else "1080:1440"
        fc.append(f"[{i}:v]trim=start={m['in']:.3f}:duration={m['dur']:.3f},setpts=PTS-STARTPTS,fps=30,scale={sz},setsar=1[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(track))) + f"concat=n={len(track)}:v=1:a=0[out]")
    subprocess.run([gfx.ffmpeg_bin(), "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
                    "-c:v", "libx264", "-crf", "16" if not preview else "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", out], check=True)
    open(mf, "w").write(key)
    return out

def check(data, A):
    """업로드 전 점검 목록 → [(수준, 문구)]"""
    out, total = [], A["total"]
    out.append(("ok" if total <= MAX_SEC else "warn",
                f"길이 {total:.2f}초" + ("" if total <= MAX_SEC else f" — {MAX_SEC}초를 넘으면 음악 저작권 신고 시 차단될 수 있어요")))
    st = review_status(data)
    out.append(("ok" if st == "심의 완료" else "warn", {"심의 전": "심의필 번호가 없어요 → 화면에 '심의 전 · 게시 불가'가 표시돼요",
                                                      "심의 만료": "심의 유효기간이 지났어요 → 게시 중이면 내리고 재심의를 받으세요",
                                                      "심의 완료": "심의필 표기 들어감"}[st]))
    if data.get("is_sample", True): out.append(("warn", "예시 데이터로 표시돼요. 실제 데이터로 바꾼 뒤 '예시 데이터' 체크를 끄세요"))
    if A["bgm"]: out.append(("warn", "BGM은 저작권 걱정 없는 음원인지 확인하세요 (유튜브 오디오 보관함 등)"))
    banned = ["무조건", "확정", "보장합니다", "100%", "최고", "1등", "유일"]
    caps = [c for c in A["captions"] if not c["gone"]] + A["texts"]
    for c in caps:
        for b in banned:
            if b in c["text"]: out.append(("warn", f"단정·과장 표현 의심: '{b}' ({c['text']})"))
        if c.get("style", "main") in ("main", "hook"):
            for line in c["text"].split("/"):
                plain = re.sub(r"[\[\]]", "", line)
                if len(plain) > 16: out.append(("warn", f"자막 한 줄이 길어요({len(plain)}자): {plain} — '/'로 나눠 주세요"))
        if c["text"].count("[") > 1: out.append(("warn", f"강조는 한 자막에 한 단어만: {c['text']}"))
    mains = sorted([c for c in caps if c.get("style", "main") == "main" and not c.get("pos")], key=lambda c: c["start"])
    for a, b in zip(mains, mains[1:]):
        if b["start"] < a["end"] - 0.01: out.append(("warn", f"아래 자막이 겹쳐요: {a['end']:.2f}초 / {b['start']:.2f}초"))
    last_change, gap = 0.0, 0.0
    edges = sorted({p["start"] for p in A["pieces"]} | {c["start"] for c in caps} | {o["start"] for o in A["overlays"]})
    for x in edges + [A["total"]]:
        gap = max(gap, x - last_change); last_change = x
    if gap > 8: out.append(("warn", f"화면 변화 없이 {gap:.1f}초가 지나는 구간이 있어요 (8초 규칙)"))
    return out

def waveform(path, step=0.05):
    """렌더된 영상의 음량(dBFS)을 step초 단위로 → 타임라인 파형용"""
    p = subprocess.run([gfx.ffmpeg_bin(), "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True)
    x = np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768
    n = int(8000 * step); k = len(x) // n
    if k == 0: return {"step": step, "db": []}
    rms = np.sqrt(np.mean(x[:k * n].reshape(k, n) ** 2, axis=1))
    db = np.maximum(20 * np.log10(np.maximum(rms, 1e-6)), -60)
    return {"step": step, "db": [round(float(v), 1) for v in db]}

def loudness(path):
    p = subprocess.run([gfx.ffmpeg_bin(), "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr); pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk else None)

def timeline(pid):
    full = load(pid)
    errs = template(full["template"]).validate(full)
    if errs: return {"ok": False, "errors": errs}
    A = assemble(full, pid)
    pdir = os.path.join(PROJECTS, pid)
    rf = os.path.join(pdir, "render.json")
    st = json.load(open(rf, encoding="utf-8")) if os.path.exists(rf) else {}
    view = {k: v for k, v in A.items() if k not in ("scenes", "shots")}
    view["shots"] = [{k: v for k, v in s.items() if k != "fn"} for s in A["shots"]]
    view["has_edits"] = bool(full.get("edits"))
    view.update(ok=True, hash=data_hash(full), rendered=st, sfx_names=sfx_names(), music=music_files(),
                media=media_list(pid), checks=check(full, A))
    return view

def scene_key(full, scale):
    """장면 그림에 영향을 주는 값 + 템플릿·그리기 코드 수정 시각"""
    T = template(full["template"])
    src = {k: v for k, v in full.items() if k not in NON_SCENE and not k.startswith("c_")}
    mt = [os.path.getmtime(T.__file__), os.path.getmtime(gfx.__file__)]
    return data_hash({"d": src, "s": scale, "m": mt})

def render(pid, preview=True):
    pdir = os.path.join(PROJECTS, pid)
    full = load(pid)
    errs = template(full["template"]).validate(full)
    if errs: return {"ok": False, "errors": errs}
    A = assemble(full, pid)
    scale = 2 if preview else 1
    sdir = os.path.join(pdir, "scenes_preview" if preview else "scenes_final")
    drawn, reused = ensure_shot_clips(full, A, sdir, scale)
    cached = not drawn
    segs = []
    for p in A["pieces"]:
        if p["kind"] == "scene":
            segs.append({"src": shot_clip_path(full, A, sdir, scale, p["name"]), "in": round(p["in"], 3),
                         "out": round(p["in"] + p["dur"], 3), "fit": "crop", "zoom": "none", "mute": True})
        elif p["kind"] == "color":
            segs.append({"color": p.get("color", "#0e1116"), "dur": p["dur"]})
        elif p["kind"] == "image":
            segs.append({"src": media_path(pid, p["src"]), "dur": p["dur"], "fit": p.get("fit", "blur"), "zoom": p.get("zoom", "kenburns")})
        elif p["kind"] == "video":
            a = float(p.get("in", 0))
            segs.append({"src": media_path(pid, p["src"]), "in": a, "out": a + p["dur"], "fit": p.get("fit", "crop"),
                         "zoom": "none", "mute": float(p.get("vol", 1)) == 0})
    caps = [{k: v for k, v in c.items() if k in ("start", "end", "text", "style", "anim")} for c in A["captions"] if not c["gone"]]
    for t in A["texts"]:
        caps.append({k: t[k] for k in ("start", "end", "text", "style", "anim", "pos", "size", "color") if t.get(k) not in (None, "")})
        caps[-1]["layer"] = 1
    caps.append(A["small"])
    # build.py --preview 는 결과 이름에 _preview를 붙인다 → final_preview.mp4
    edl = {"out": "final.mp4", "w": 1080, "h": 1920, "fps": 30, "segments": segs, "captions": caps,
           "sfx": [{"t": s["t"], "name": s["name"], "vol": s.get("vol", 0.7)} for s in A["sfx"]],
           "overlays": [{**{k: o[k] for k in ("start", "end", "x", "y", "w", "fade", "in", "vol") if k in o},
                         "src": media_path(pid, o["src"])} for o in A["overlays"]],
           "voices": [{"src": media_path(pid, v["src"]), "offset": v["offset"], "vol": v.get("vol", 1.0)} for v in A["voices"]]}
    if A["bgm"]:
        b = A["bgm"]
        edl["bgm"] = {"src": os.path.join(MUSIC, b["file"]), "vol": float(b.get("vol", 0.22)), "duck": bool(b.get("duck", True)),
                      "start": float(b.get("start", 0)), "fade_in": float(b.get("fade_in", 0.5)), "fade_out": float(b.get("fade_out", 1.5))}
    json.dump(edl, open(os.path.join(pdir, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    env = dict(os.environ); env["PATH"] = os.path.dirname(gfx.ffmpeg_bin()) + os.pathsep + env.get("PATH", "")
    p = subprocess.run([sys.executable, BUILD, "render", os.path.join(pdir, "edl.json")] + (["--preview"] if preview else []),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if p.returncode: return {"ok": False, "errors": ["렌더 실패: " + p.stderr[-800:]]}
    out = "final_preview.mp4" if preview else "final.mp4"
    kind = "preview" if preview else "final"
    wave = waveform(os.path.join(pdir, out))
    json.dump(wave, open(os.path.join(pdir, f"wave_{kind}.json"), "w"))
    rf = os.path.join(pdir, "render.json")
    st = json.load(open(rf, encoding="utf-8")) if os.path.exists(rf) else {}
    st[kind] = data_hash(full)
    json.dump(st, open(rf, "w", encoding="utf-8"))
    checks = check(full, A)
    lu, pk = loudness(os.path.join(pdir, out))
    if lu is not None:
        ok = -15.5 <= lu <= -12.5 and (pk is None or pk <= -0.5)
        checks.insert(1, ("ok" if ok else "warn", f"음량 {lu:.1f} LUFS · 최고 {pk:.1f} dB (목표 -14 LUFS 근처)"))
    checks.insert(1, ("ok", "1080×1920 · 30fps · H.264/AAC"))
    return {"ok": True, "video": f"/files/{pid}/{out}", "kind": kind, "checks": checks, "wave": wave, "cached": cached,
            "shots_drawn": drawn, "shots_reused": reused}

# ---------------- 스토리보드용: 장면 썸네일·장면 단독 미리보기 ----------------
def shot_thumb(pid, shot_id):
    """장면 대표 이미지(270×480 PNG). 그린 장면은 장면 길이 70% 지점을 바로 그린다. 키가 같으면 재사용."""
    from PIL import Image, ImageDraw
    full = load(pid); A = assemble(full, pid)
    s = next(x for x in A["shots"] if x["id"] == shot_id)
    key = data_hash({"k": shot_key(full, A, 4, shot_id) if s["kind"] == "scene" and not s["user"] else
                     [s["kind"], s.get("src"), s.get("color"), s.get("in")], "v": 2})
    tdir = os.path.join(PROJECTS, pid, "thumbs"); os.makedirs(tdir, exist_ok=True)
    out = os.path.join(tdir, f"{shot_id}__{key}.png")
    if os.path.exists(out): return out
    for f in os.listdir(tdir):
        if f.startswith(shot_id + "__"): os.remove(os.path.join(tdir, f))
    W, H = 270, 480
    if s["kind"] == "scene" and not s["user"]:
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG); d = ImageDraw.Draw(im)
        s["fn"](d, min(s["dur"] * 0.7, max(0.0, s["dur"] - 0.1))); im = im.resize((W, H), Image.BILINEAR)
    elif s["kind"] == "image" and s.get("src"):
        src = Image.open(media_path(pid, s["src"])).convert("RGB"); im = Image.new("RGB", (W, H), (14, 17, 22))
        src.thumbnail((W, H)); im.paste(src, ((W - src.width) // 2, (H - src.height) // 2))
    elif s["kind"] == "video" and s.get("src"):
        subprocess.run([gfx.ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{float(s.get('in') or 0) + 0.3:.2f}", "-i", media_path(pid, s["src"]),
                        "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2", out])
        return out
    else:
        im = Image.new("RGB", (W, H), s.get("color") or "#0e1116")
    im.save(out)
    return out

def shot_preview_clip(pid, shot_id):
    """그린 장면 하나만 미리보기 배율로 렌더(이미 있으면 재사용) → 파일 경로, 새로 그렸는지"""
    full = load(pid); A = assemble(full, pid)
    sdir = os.path.join(PROJECTS, pid, "scenes_preview")
    drawn, _ = ensure_shot_clips(full, A, sdir, 2, only=shot_id)
    return shot_clip_path(full, A, sdir, 2, shot_id), bool(drawn)

# ---------------- 장면별 클립 캐시 ----------------
def shot_key(full, A, scale, name):
    """장면 하나의 캐시 키 = 템플릿 그림 데이터 전체(장면별 의존을 코드에서 알 수 없어 보수적으로) + 장면 이름 + 길이 + 배율 + 코드 수정 시각"""
    s = next(x for x in A["shots"] if x["id"] == name)
    return data_hash({"g": scene_key(full, scale), "n": name, "d": s["dur"]})

def shot_clip_path(full, A, sdir, scale, name):
    return os.path.join(sdir, f"{name}__{shot_key(full, A, scale, name)}.mp4")

def ensure_shot_clips(full, A, sdir, scale, only=None):
    """보이는 '그린 장면'의 클립이 없으면 그리고, 있으면 재사용한다. → (그린 장면 ID 목록, 재사용한 장면 ID 목록)
    현재 배치에서 쓰지 않는 옛 클립 파일은 지운다(only가 없을 때)."""
    os.makedirs(sdir, exist_ok=True)
    fns = {n: fn for n, _, fn in A["scenes"]}
    drawn, reused, keep = [], [], set()
    for s in A["shots"]:
        if s["hidden"] or s["kind"] != "scene" or s["user"]: continue
        if only and s["id"] != only: continue
        path = shot_clip_path(full, A, sdir, scale, s["id"]); keep.add(os.path.basename(path))
        if os.path.exists(path) and os.path.getsize(path) > 0: reused.append(s["id"]); continue
        tmp = path + ".part.mp4"
        gfx.write_clip(tmp, s["dur"], fns[s["id"]], scale); os.replace(tmp, path)
        drawn.append(s["id"])
    if not only:
        for f in os.listdir(sdir):
            if f.endswith(".mp4") and f not in keep: os.remove(os.path.join(sdir, f))
    return drawn, reused

# ---------------- 내보내기 ----------------
def srt(pid):
    full = load(pid); A = assemble(full, pid)
    items = [c for c in A["captions"] if not c["gone"]] + [t for t in A["texts"] if t.get("style", "main") != "small"]
    items.sort(key=lambda c: c["start"])
    def ts(t): ms = int(round(t * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out = []
    for i, c in enumerate(items, 1):
        txt = re.sub(r"[\[\]]", "", c["text"]).replace("/", "\n")
        out.append(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{txt}\n")
    return "\n".join(out)

def thumbnail(pid, t):
    pdir = os.path.join(PROJECTS, pid)
    src = os.path.join(pdir, "final.mp4") if os.path.exists(os.path.join(pdir, "final.mp4")) else os.path.join(pdir, "final_preview.mp4")
    out = os.path.join(pdir, "thumbnail.png")
    subprocess.run([gfx.ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", src, "-frames:v", "1", out], check=True)
    return out
