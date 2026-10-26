"""공통 장면 모델 (schema_version 2) — 지침서 5장의 Project / Shot / Keyframe / Asset / Segment / TimelineItem.

저장 형식(data.json)은 바꾸지 않는다. 이 모듈은 pipeline.assemble() 결과에서 모델을 '계산'하고 검증만 한다.
  - Shot     : 장면 계획 단위 (템플릿 장면 + 사용자 장면). data.shots / data.shot_order로 덮어쓴다
  - Keyframe : 장면의 시각 기준 이미지 (data.shots[ID].keyframes). 그린 장면은 자동 썸네일만 있고 키프레임은 0개일 수 있다
  - Asset    : 파일 (그린 장면 클립, 프로젝트 미디어, 공용 라이브러리, 음악)
  - Segment  : 타임라인에서 실제로 재생되는 구간 (pipeline의 pieces = 장면을 끼워넣기·구간 삭제로 자른 결과)
  - TimelineItem : 자막·글자·얹기·효과음·내레이션·BGM·준법 표기·마커
"""
import os
import pipeline

SCHEMA_VERSION = 2
PURPOSES = ["훅", "설명", "증거", "반전", "결론", "기타"]
MAX_TOTAL = 180.0  # 쇼츠 최대 길이(초). 60초 초과는 pipeline.check가 따로 경고

def _asset_id(path): return "asset:" + path

def build(pid):
    full = pipeline.load(pid)
    A = pipeline.assemble(full, pid)
    pdir = os.path.join(pipeline.PROJECTS, pid)
    assets, seen = [], set()
    def add_asset(path, typ, origin, abspath=None):
        aid = _asset_id(path)
        if aid in seen: return aid
        seen.add(aid)
        if abspath is None:
            try: abspath = pipeline.media_path(pid, path)
            except ValueError: abspath = None
        assets.append({"id": aid, "path": path, "type": typ, "origin": origin, "exists": bool(abspath and os.path.exists(abspath))})
        return aid
    def media_type(p):
        e = os.path.splitext(p)[1].lower()
        return "image" if e in pipeline.IMG_EXT else "video" if e in pipeline.VID_EXT else "audio"
    def origin(p): return "library" if p.startswith("library/") else "user"

    # 장면별 클립 캐시 상태 (미리보기 기준)
    sdir = os.path.join(pdir, "scenes_preview")
    shots, keyframes = [], []
    for s in A["shots"]:
        if s["kind"] == "scene" and not s["user"]:
            path = pipeline.shot_clip_path(full, A, sdir, 2, s["id"])
            src = {"type": "drawn", "template_scene": s["id"]}
            render = "cached" if os.path.exists(path) else "not_rendered"
        elif s["kind"] in ("image", "video"):
            src = {"type": s["kind"], "asset": add_asset(s["src"], s["kind"], origin(s["src"])) if s.get("src") else None}
            render = "source"
        else:
            src = {"type": "color", "color": s.get("color") or "#0e1116"}; render = "source"
        kids = []
        for i, k in enumerate(s.get("keyframes") or []):
            kid = k.get("id") or f"{s['id']}-kf{i + 1}"
            keyframes.append({"id": kid, "shot_id": s["id"], "asset": add_asset(k["src"], "image", origin(k["src"])) if k.get("src") else None,
                              "prompt": k.get("prompt", ""), "refs": k.get("refs", []), "gen_status": k.get("gen_status", "uploaded"),
                              "approved": bool(k.get("approved")), "role": k.get("role", "reference"), "order": i})
            kids.append(kid)
        shots.append({"id": s["id"], "index": s["index"], "user": s["user"], "purpose": s["purpose"], "desc": s["desc"],
                      "dur": s["dur"], "template_dur": s["tdur"], "start": s["start"], "hidden": s["hidden"],
                      "visual": s["kind"], "source": src, "prompt": (full.get("shots") or {}).get(s["id"], {}).get("prompt", ""),
                      "keyframes": kids, "status": {"render": render, "changed": s["id"] in (full.get("shots") or {})}})
    segments = []
    for i, p in enumerate(A["pieces"]):
        if p["kind"] == "scene": src = {"drawn": p["name"]}
        elif p["kind"] in ("image", "video"): src = {"asset": add_asset(p["src"], p["kind"], origin(p["src"]))}
        else: src = {"color": p.get("color", "#0e1116")}
        segments.append({"id": f"seg{i + 1}", "shot_id": p.get("shot"), "insert": bool(p.get("insert")), "source": src,
                         "src_in": round(float(p.get("in") or 0), 3), "src_out": round(float(p.get("in") or 0) + p["dur"], 3),
                         "start": p["start"], "dur": round(p["dur"], 3), "speed": 1.0, "fit": p.get("fit", "crop"), "zoom": p.get("zoom", "none")})
    items = []
    def shot_at(t):
        for p in A["pieces"]:
            if p["start"] - 1e-6 <= t < p["start"] + p["dur"] - 1e-6: return p.get("shot")
        return None
    for c in A["captions"]:
        if c["gone"]: continue
        fixed = c["idx"] is None  # 영상 내내 고정(plan의 헤드라인)
        items.append({"id": f"fixed_{c.get('key') or 'cap'}" if fixed else f"cap{c['idx'] + 1}", "track": "caption",
                      "kind": "fixed_caption" if fixed else "template_caption", "start": c["start"], "end": c["end"],
                      "shot_id": None if fixed else shot_at(c["start"]), "props": {"text": c["text"], "style": c["style"], "field": c.get("key")}})
    for i, t in enumerate(A["texts"]):
        items.append({"id": t.get("id") or f"text{i + 1}", "track": "text", "kind": "text", "start": t["start"], "end": t["end"],
                      "shot_id": shot_at(t["start"]), "props": {k: t[k] for k in ("text", "style", "pos", "size", "color", "anim") if k in t}})
    for i, o in enumerate(A["overlays"]):
        items.append({"id": o.get("id") or f"ovl{i + 1}", "track": "overlay", "kind": media_type(o["src"]), "start": o["start"], "end": o["end"],
                      "shot_id": shot_at(o["start"]), "props": {"asset": add_asset(o["src"], media_type(o["src"]), origin(o["src"])),
                                                                 **{k: o[k] for k in ("x", "y", "w", "fade", "vol") if k in o}}})
    for i, s in enumerate(A["sfx"]):
        items.append({"id": f"sfx{i + 1}", "track": "sfx", "kind": "sfx", "start": s["t"], "end": s["t"], "shot_id": shot_at(s["t"]),
                      "props": {"name": s["name"], "vol": s.get("vol", 0.7)}})
    for i, v in enumerate(A["voices"]):
        items.append({"id": v.get("id") or f"voice{i + 1}", "track": "voice", "kind": "voice", "start": v["offset"],
                      "end": round(v["offset"] + float(v.get("dur") or 0), 3), "shot_id": shot_at(v["offset"]),
                      "props": {"asset": add_asset(v["src"], "audio", origin(v["src"])), "vol": v.get("vol", 1.0)}})
    if A["bgm"]:
        mp = os.path.join(pipeline.MUSIC, A["bgm"]["file"])
        items.append({"id": "bgm", "track": "bgm", "kind": "bgm", "start": 0.0, "end": A["total"], "shot_id": None,
                      "props": {"asset": add_asset("music/" + A["bgm"]["file"], "audio", "music", mp), **{k: v for k, v in A["bgm"].items() if k != "file"}}})
    items.append({"id": "compliance", "track": "compliance", "kind": "small", "start": 0.0, "end": A["total"], "shot_id": None,
                  "props": {"text": A["small"]["text"]}})
    for i, m in enumerate(A["markers"]):
        items.append({"id": f"marker{i + 1}", "track": "marker", "kind": "marker", "start": m["t"], "end": m["t"], "shot_id": shot_at(m["t"]),
                      "props": {"label": m.get("label", "")}})
    project = {"id": pid, "title": full.get("title", pid), "template": full["template"], "schema_version": SCHEMA_VERSION,
               "stored_schema_version": full.get("schema_version", 1), "aspect": "9:16", "width": 1080, "height": 1920, "fps": 30,
               "total": A["total"], "is_sample": full.get("is_sample", True), "review": pipeline.review_status(full),
               "has_edits": bool(full.get("edits")), "voice": full.get("voice")}
    m = {"project": project, "shots": shots, "keyframes": keyframes, "assets": assets, "segments": segments, "timeline_items": items}
    m["validation"] = validate(m)
    return m

def validate(m):
    """→ {"errors": [...], "warnings": [...]} — 저장·렌더 전에 막아야 할 것은 errors"""
    errs, warns = [], []
    ids = [s["id"] for s in m["shots"]]
    if len(ids) != len(set(ids)): errs.append("장면 ID가 중복돼요")
    vis = [s for s in m["shots"] if not s["hidden"]]
    if not vis: errs.append("보이는 장면이 하나도 없어요")
    for s in m["shots"]:
        if not (0.2 <= s["dur"] <= 60): errs.append(f"{s['id']}: 장면 길이 {s['dur']}초는 허용 범위(0.2~60초) 밖이에요")
        if s["visual"] not in pipeline.SHOT_KINDS: errs.append(f"{s['id']}: 지원하지 않는 시각 자료 유형 '{s['visual']}'")
        if s["visual"] in ("image", "video"):
            a = s["source"].get("asset")
            if not a: errs.append(f"{s['id']}: 소스 파일이 지정되지 않았어요")
            elif not next(x for x in m["assets"] if x["id"] == a)["exists"]: errs.append(f"{s['id']}: 소스 파일이 없어요 ({a[6:]})")
        if s["purpose"] and s["purpose"] not in PURPOSES: warns.append(f"{s['id']}: 목적 '{s['purpose']}'은 정해진 목록에 없어요")
    kid = [k["id"] for k in m["keyframes"]]
    if len(kid) != len(set(kid)): errs.append("키프레임 ID가 중복돼요")
    for k in m["keyframes"]:
        if k["asset"] and not next(x for x in m["assets"] if x["id"] == k["asset"])["exists"]: warns.append(f"키프레임 {k['id']}: 이미지 파일이 없어요")
    total = m["project"]["total"]
    if total > MAX_TOTAL: errs.append(f"전체 길이 {total:.1f}초가 쇼츠 최대 {MAX_TOTAL:.0f}초를 넘어요")
    for it in m["timeline_items"]:
        if it["start"] < -1e-6 or it["end"] < it["start"] - 1e-6: errs.append(f"{it['id']}: 시간 범위가 잘못됐어요 ({it['start']}~{it['end']})")
        elif it["start"] > total + 1e-3: warns.append(f"{it['id']}: 영상 길이 밖에서 시작해요 ({it['start']}초)")
        if it["track"] in ("caption", "text") and not str(it["props"].get("text", "")).strip(): warns.append(f"{it['id']}: 빈 자막")
        a = it["props"].get("asset")
        if a and not next(x for x in m["assets"] if x["id"] == a)["exists"]: errs.append(f"{it['id']}: 파일이 없어요 ({a[6:]})")
    t = 0.0
    for sg in m["segments"]:
        if abs(sg["start"] - t) > 1e-2: errs.append(f"{sg['id']}: 구간이 이어지지 않아요 ({t:.2f} → {sg['start']:.2f})")
        if sg["dur"] <= 0: errs.append(f"{sg['id']}: 길이가 0 이하예요")
        t = sg["start"] + sg["dur"]
    if abs(t - total) > 1e-2: errs.append(f"구간 합계 {t:.2f}초와 전체 길이 {total:.2f}초가 달라요")
    return {"errors": errs, "warnings": warns}
