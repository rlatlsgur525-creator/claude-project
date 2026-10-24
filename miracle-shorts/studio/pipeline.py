"""프로젝트(data.json) → 장면 클립 → edl.json → build.py 렌더 → 점검 결과.
템플릿 모듈 규약: NAME, DESC, FIELDS, validate(data) -> [오류], build(data) -> (scenes, captions, sfx, note)
  scenes: [(이름, 초, draw_fn(d, t))]   captions: [(시작, 끝, 문구[, anim])]   note: 준법 표기 둘째 줄
"""
import importlib, json, os, re, subprocess, sys
from datetime import date
import gfx

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "shorts-kit", "build.py")
PROJECTS = os.path.join(HERE, "projects")
TEMPLATES = ["terms_survey", "warning", "experiment"]
MAX_SEC = 60  # 1분 초과 쇼츠는 음악 저작권 신고 시 차단될 수 있어 기본 상한으로 둔다

def template(key):
    return importlib.import_module("templates." + key)

def defaults(key):
    return {f["key"]: f["default"] for f in template(key).FIELDS if "key" in f}

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

def check(data, edl, total):
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
    banned = ["무조건", "확정", "보장합니다", "100%", "최고", "1등", "유일"]
    for c in edl["captions"]:
        for b in banned:
            if b in c["text"]: out.append(("warn", f"단정·과장 표현 의심: '{b}' ({c['text']})"))
    for c in edl["captions"]:
        if c["style"] == "main":
            for line in c["text"].split("/"):
                plain = re.sub(r"[\[\]]", "", line)
                if len(plain) > 16: out.append(("warn", f"자막 한 줄이 길어요({len(plain)}자): {plain} — '/'로 나눠 주세요"))
            if c["text"].count("[") > 1: out.append(("warn", f"강조는 한 자막에 한 단어만: {c['text']}"))
    return out

def render(pid, preview=True):
    pdir = os.path.join(PROJECTS, pid)
    data = json.load(open(os.path.join(pdir, "data.json"), encoding="utf-8"))
    T = template(data["template"])
    full = {**defaults(data["template"]), **data}
    errs = T.validate(full)
    if errs: return {"ok": False, "errors": errs}
    scenes, captions, sfx, note = T.build(full)
    scale = 2 if preview else 1
    segs = []
    for name, dur, fn in scenes:
        path = os.path.join(pdir, "scenes", f"{name}.mp4")
        gfx.write_clip(path, dur, fn, scale)
        segs.append({"src": f"scenes/{name}.mp4", "fit": "crop", "zoom": "none", "mute": True})
    total = sum(d for _, d, _ in scenes)
    caps = [{"start": c[0], "end": c[1], "text": c[2], "style": "main", **({"anim": c[3]} if len(c) > 3 else {})}
            for c in captions]
    caps.append({"start": 0.0, "end": total, "text": compliance_line(full) + "/" + note, "style": "small", "anim": "none"})
    # build.py --preview 는 결과 이름에 _preview를 붙인다 → final_preview.mp4
    edl = {"out": "final.mp4", "w": 1080, "h": 1920, "fps": 30, "segments": segs, "captions": caps, "sfx": sfx}
    if full.get("bgm"): edl["bgm"] = {"src": full["bgm"], "vol": 0.22, "duck": True}
    json.dump(edl, open(os.path.join(pdir, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    env = dict(os.environ); env["PATH"] = os.path.dirname(gfx.ffmpeg_bin()) + os.pathsep + env.get("PATH", "")
    p = subprocess.run([sys.executable, BUILD, "render", os.path.join(pdir, "edl.json")] + (["--preview"] if preview else []),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if p.returncode: return {"ok": False, "errors": ["렌더 실패: " + p.stderr[-800:]]}
    out = "final_preview.mp4" if preview else "final.mp4"
    return {"ok": True, "video": f"/files/{pid}/{out}", "checks": check(full, edl, total)}
