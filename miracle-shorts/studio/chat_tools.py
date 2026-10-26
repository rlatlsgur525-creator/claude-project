#!/usr/bin/env python3
"""채팅으로 쇼츠 만들기 — Claude Code가 쓰는 명령 도구 (절차는 .claude/skills/chat-shorts/SKILL.md).
템플릿 'plan'(채팅 스토리보드) 프로젝트를 만들고, 장면에 키프레임을 끼우고, 렌더한다. 사람은 스튜디오에서 이어서 고친다.

usage:
  python chat_tools.py new <id> <plan.json> [--force]   계획 → 새 프로젝트 (있으면 --force 로 덮어씀)
  python chat_tools.py update <id> <plan.json>         헤드라인·대본·준법 표기만 바꿈 (키프레임은 그대로)
  python chat_tools.py keyframe <id> <b1> <파일> [--prompt "…"]   장면 b1에 이미지·영상을 끼움
  python chat_tools.py show <id>                       장면표 (번호·시간·자막·그림 설명·키프레임)
  python chat_tools.py render <id> [--final] [--sheet 파일.png]   미리보기(기본)·최종 렌더, 장면 모음 이미지
plan.json: {"title", "headline", "note"?, "style"?, "beats": [{"text", "prompt", "dur"?, "purpose"?}]}
"""
import json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipeline, model
from templates import plan as T

IMG = (".png", ".jpg", ".jpeg", ".webp")
VID = (".mp4", ".mov", ".m4v")

def pdir(pid): return os.path.join(pipeline.PROJECTS, pid)
def raw(pid): return json.load(open(os.path.join(pdir(pid), "data.json"), encoding="utf-8"))
def save(pid, d): json.dump(d, open(os.path.join(pdir(pid), "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def read_plan(path):
    p = json.load(open(path, encoding="utf-8"))
    bs = [b for b in p.get("beats") or [] if (b.get("text") or "").strip()]
    if not bs: sys.exit("plan.json에 beats가 없어요")
    return p, [{"text": b["text"].strip(), "prompt": (b.get("prompt") or "").strip(), "dur": b.get("dur")} for b in bs], bs

def apply_plan(d, p, beats, src):
    d.update(beats=beats, headline=p.get("headline", d.get("headline", "")), note=p.get("note", d.get("note", T.FIELDS[-1]["default"])))
    if p.get("title"): d["title"] = p["title"]
    if p.get("style"): d["style"] = p["style"]
    shots = d.setdefault("shots", {})
    for i, b in enumerate(src):
        o = shots.setdefault(f"b{i + 1}", {})
        o["prompt"] = o["desc"] = (b.get("prompt") or "").strip()  # desc = 스토리보드 카드에 보이는 설명
        if b.get("purpose"): o["purpose"] = b["purpose"]
    for k in [k for k in shots if k.startswith("b") and k[1:].isdigit() and int(k[1:]) > len(src)]: del shots[k]  # 줄어든 장면
    return d

def cmd_new(pid, path, force=False):
    if os.path.exists(pdir(pid)) and not force: sys.exit(f"이미 있는 프로젝트예요: {pid} (덮어쓰려면 --force)")
    p, beats, src = read_plan(path)
    os.makedirs(os.path.join(pdir(pid), "media"), exist_ok=True)
    d = {"template": "plan", "title": pid, "is_sample": True, "review_no": "", "review_exp": "", **pipeline.defaults("plan")}
    save(pid, apply_plan(d, p, beats, src)); report(pid)

def cmd_update(pid, path):
    p, beats, src = read_plan(path)
    save(pid, apply_plan(raw(pid), p, beats, src)); report(pid)

def cmd_keyframe(pid, shot, f, prompt=None):
    ext = os.path.splitext(f)[1].lower()
    if ext not in IMG + VID: sys.exit(f"이미지({', '.join(IMG)})나 영상({', '.join(VID)})만 넣을 수 있어요")
    d = raw(pid); n = len(T.beats(d))
    if not (shot.startswith("b") and shot[1:].isdigit() and 1 <= int(shot[1:]) <= n): sys.exit(f"장면은 b1~b{n} 중 하나예요")
    rel = f"media/kf_{shot}{ext}"; shutil.copyfile(f, os.path.join(pdir(pid), rel))
    o = d.setdefault("shots", {}).setdefault(shot, {})
    o.update(kind="video" if ext in VID else "image", src=rel, fit="crop")
    if ext in VID: o.update(**{"in": 0.0, "vol": 0})
    o["keyframes"] = [{"src": rel, "prompt": prompt or o.get("prompt", ""), "gen_status": "generated", "approved": True, "role": "start"}]
    save(pid, d); print(f"{shot} ← {rel}")

def report(pid):
    m = model.build(pid); full = pipeline.load(pid); A = pipeline.assemble(full, pid)
    print(f"[{pid}] {full.get('title')} · {A['total']:.1f}초 · 헤드라인: {full.get('headline', '')}")
    caps = {c["idx"]: c for c in A["captions"] if c["idx"] is not None}
    for i, s in enumerate(A["shots"]):
        if s["hidden"]: continue
        c = caps.get(i, {}); kf = s["src"] if s["kind"] != "scene" else "(대기)"
        print(f"  {s['id']:>4} {s['start']:5.1f}~{s['start'] + s['dur']:5.1f}s  {pipeline.re.sub(r'[\[\]]', '', c.get('text', '')).replace('/', ' '):<28} | {(full['shots'].get(s['id']) or {}).get('prompt', '')[:34]:<34} | {kf}")
    for e in m["validation"]["errors"]: print("  ✗", e)
    for lv, msg in pipeline.check(full, A):
        if lv != "ok": print("  !", msg)

def cmd_render(pid, final=False, sheet=None):
    r = pipeline.render(pid, preview=not final)
    if not r["ok"]: sys.exit("렌더 실패: " + "; ".join(r["errors"]))
    out = os.path.join(pdir(pid), "final.mp4" if final else "final_preview.mp4")
    print("영상:", out)
    for lv, msg in r["checks"]: print(("  ✓ " if lv == "ok" else "  ! ") + msg)
    if sheet:  # 장면마다 가운데 한 장 → 가로로 이어 붙인 확인용 이미지
        A = pipeline.assemble(pipeline.load(pid), pid)
        mids = [s["start"] + s["dur"] / 2 for s in A["shots"] if not s["hidden"]]
        ff = pipeline.gfx.ffmpeg_bin(); tmp = sheet + ".parts"; os.makedirs(tmp, exist_ok=True)
        for i, t in enumerate(mids):
            subprocess.run([ff, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", out, "-frames:v", "1", "-vf", "scale=270:-2", os.path.join(tmp, f"{i:02d}.png")], check=True)
        subprocess.run([ff, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%02d.png"), "-vf", f"tile={len(mids)}x1:padding=6:color=0x0e1116",
                        "-frames:v", "1", sheet], check=True)
        shutil.rmtree(tmp); print("장면 모음:", sheet)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    flag = lambda k: k in a and (a.remove(k) or True)
    def opt(k):
        if k not in a: return None
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    c = a[0]
    if c == "new": force = flag("--force"); cmd_new(a[1], a[2], force)
    elif c == "update": cmd_update(a[1], a[2])
    elif c == "keyframe": pr = opt("--prompt"); cmd_keyframe(a[1], a[2], a[3], pr)
    elif c == "show": report(a[1])
    elif c == "render": fin = flag("--final"); sh = opt("--sheet"); cmd_render(a[1], fin, sh)
    else: sys.exit(__doc__)
