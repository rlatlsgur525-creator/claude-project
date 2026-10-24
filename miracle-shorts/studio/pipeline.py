"""프로젝트(data.json) → 타임라인 조립 → 장면 클립 → edl.json → build.py 렌더 → 점검·음량 파형.
템플릿 모듈 규약: NAME, DESC, FIELDS, CAP_KEYS, validate(data) -> [오류], build(data) -> (scenes, captions, sfx, note)
  scenes: [(이름, 초, draw_fn(d, t))]   captions: [(시작, 끝, 문구[, anim])]   note: 준법 표기 둘째 줄
  CAP_KEYS: captions 순서대로 그 문구를 만드는 FIELDS 키 (타임라인에서 자막을 누르면 해당 칸으로 이동)
타임라인에서 고친 값은 data.json에 따로 저장된다:
  tl.cap_times: [[시작, 끝], …] 자막 시간 (자막 개수가 같을 때만 적용)
  tl.sfx: [{t, name, vol}, …] 효과음 전체 (있으면 템플릿 기본값 대신 씀)
  bgm: {file, vol, duck, start} 배경음악 (studio/music/ 안의 파일)
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
TEMPLATES = ["terms_survey", "warning", "experiment"]
MAX_SEC = 60  # 1분 초과 쇼츠는 음악 저작권 신고 시 차단될 수 있어 기본 상한으로 둔다
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")

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

def assemble(full):
    """템플릿 결과 + 타임라인 수정값 → (scenes, edl 뼈대, 타임라인 표시용 dict)"""
    T = template(full["template"])
    scenes, captions, sfx, note = T.build(full)
    total = round(sum(d for _, d, _ in scenes), 3)
    keys = list(getattr(T, "CAP_KEYS", []))
    caps = [{"start": c[0], "end": c[1], "text": c[2], "style": "main", **({"anim": c[3]} if len(c) > 3 else {}),
             "key": keys[i] if i < len(keys) else None} for i, c in enumerate(captions)]
    tl = full.get("tl") or {}
    times = tl.get("cap_times")
    if times and len(times) == len(caps):
        for c, (s, e) in zip(caps, times):
            c["start"], c["end"] = max(0.0, float(s)), min(total, float(e))
    default_sfx = sfx
    if tl.get("sfx") is not None: sfx = tl["sfx"]
    small = {"start": 0.0, "end": total, "text": compliance_line(full) + "/" + note, "style": "small", "anim": "none"}
    bgm = full.get("bgm") or None
    if bgm and not bgm.get("file"): bgm = None
    view = {"total": total, "captions": caps, "small": small, "sfx": sfx, "bgm": bgm,
            "custom": {"cap_times": bool(times and len(times) == len(caps)), "sfx": tl.get("sfx") is not None},
            "scenes": [], "default_sfx": default_sfx}
    t = 0.0
    for i, (name, dur, _) in enumerate(scenes):
        view["scenes"].append({"name": name, "label": f"장면 {i + 1}", "start": round(t, 3), "dur": dur}); t += dur
    return scenes, caps, small, sfx, bgm, total, view

def check(data, caps, total):
    """업로드 전 점검 목록 → [(수준, 문구)]"""
    out = []
    out.append(("ok" if total <= MAX_SEC else "warn",
                f"길이 {total:.1f}초" + ("" if total <= MAX_SEC else f" — {MAX_SEC}초를 넘으면 음악 저작권 신고 시 차단될 수 있어요")))
    out.append(("ok", "1080×1920 · 30fps · H.264/AAC · 음량 -14 LUFS 자동 맞춤"))
    st = review_status(data)
    out.append(("ok" if st == "심의 완료" else "warn", {"심의 전": "심의필 번호가 없어요 → 화면에 '심의 전 · 게시 불가'가 표시돼요",
                                                      "심의 만료": "심의 유효기간이 지났어요 → 게시 중이면 내리고 재심의를 받으세요",
                                                      "심의 완료": "심의필 표기 들어감"}[st]))
    if data.get("is_sample", True): out.append(("warn", "예시 데이터로 표시돼요. 실제 데이터로 바꾼 뒤 '예시 데이터' 체크를 끄세요"))
    if data.get("bgm", {}).get("file"):
        out.append(("warn", "BGM은 저작권 걱정 없는 음원인지 확인하세요 (유튜브 오디오 보관함 등)"))
    banned = ["무조건", "확정", "보장합니다", "100%", "최고", "1등", "유일"]
    for c in caps:
        for b in banned:
            if b in c["text"]: out.append(("warn", f"단정·과장 표현 의심: '{b}' ({c['text']})"))
        for line in c["text"].split("/"):
            plain = re.sub(r"[\[\]]", "", line)
            if len(plain) > 16: out.append(("warn", f"자막 한 줄이 길어요({len(plain)}자): {plain} — '/'로 나눠 주세요"))
        if c["text"].count("[") > 1: out.append(("warn", f"강조는 한 자막에 한 단어만: {c['text']}"))
    for a, b in zip(caps, caps[1:]):
        if b["start"] < a["end"] - 0.01: out.append(("warn", f"자막이 겹쳐요: {a['end']:.1f}초 / {b['start']:.1f}초"))
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

def timeline(pid):
    full = load(pid)
    errs = template(full["template"]).validate(full)
    if errs: return {"ok": False, "errors": errs}
    *_, view = assemble(full)
    pdir = os.path.join(PROJECTS, pid)
    st = json.load(open(os.path.join(pdir, "render.json"), encoding="utf-8")) if os.path.exists(os.path.join(pdir, "render.json")) else {}
    view.update(ok=True, hash=data_hash(full), rendered=st, sfx_names=sfx_names(), music=music_files())
    return view

def render(pid, preview=True):
    pdir = os.path.join(PROJECTS, pid)
    full = load(pid)
    errs = template(full["template"]).validate(full)
    if errs: return {"ok": False, "errors": errs}
    scenes, caps, small, sfx, bgm, total, _ = assemble(full)
    scale = 2 if preview else 1
    segs = []
    for name, dur, fn in scenes:
        gfx.write_clip(os.path.join(pdir, "scenes", f"{name}.mp4"), dur, fn, scale)
        segs.append({"src": f"scenes/{name}.mp4", "fit": "crop", "zoom": "none", "mute": True})
    edl_caps = [{k: v for k, v in c.items() if k != "key"} for c in caps] + [small]
    # build.py --preview 는 결과 이름에 _preview를 붙인다 → final_preview.mp4
    edl = {"out": "final.mp4", "w": 1080, "h": 1920, "fps": 30, "segments": segs, "captions": edl_caps,
           "sfx": [{"t": s["t"], "name": s["name"], "vol": s.get("vol", 0.7)} for s in sfx]}
    if bgm:
        edl["bgm"] = {"src": os.path.join(MUSIC, bgm["file"]), "vol": float(bgm.get("vol", 0.22)),
                      "duck": bool(bgm.get("duck", True)), "start": float(bgm.get("start", 0))}
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
    return {"ok": True, "video": f"/files/{pid}/{out}", "kind": kind, "checks": check(full, caps, total), "wave": wave}
