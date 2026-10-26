#!/usr/bin/env python3
"""Phase 1~3 검증: 공통 장면 모델, 장면 덮어쓰기(순서·길이·숨김·소스·추가), 장면별 캐시.
usage: python tests/test_scenes.py            (미리보기 렌더 포함, 약 1~2분)
       python tests/test_scenes.py --final    (+ 기존 세 프로젝트 최종 MP4 렌더)
기존 프로젝트 파일은 바꾸지 않는다. 시험은 임시 프로젝트(_test_*)에서 하고 끝나면 지운다.
"""
import json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import pipeline, model

SEEDS = ["01-수술비", "02-해지-경고", "03-100만원-실험"]
ok_count = 0
def check(cond, msg):
    global ok_count
    if not cond: raise AssertionError(msg)
    ok_count += 1; print("  ✓", msg)

def caps(pid): return [(c["start"], c["end"]) for c in pipeline.assemble(pipeline.load(pid), pid)["captions"]]

def temp_project(seed, name):
    d = os.path.join(pipeline.PROJECTS, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    shutil.copy(os.path.join(pipeline.PROJECTS, seed, "data.json"), os.path.join(d, "data.json"))
    return name

def save(pid, data): json.dump(data, open(os.path.join(pipeline.PROJECTS, pid, "data.json"), "w", encoding="utf-8"), ensure_ascii=False)
def raw(pid): return json.load(open(os.path.join(pipeline.PROJECTS, pid, "data.json"), encoding="utf-8"))

def main():
    final = "--final" in sys.argv
    print("1) 기존 프로젝트: 모델 변환·검증 (파일 변경 없음)")
    for pid in SEEDS:
        before = open(os.path.join(pipeline.PROJECTS, pid, "data.json"), "rb").read()
        m = model.build(pid)
        check(not m["validation"]["errors"], f"{pid}: 모델 검증 오류 없음 ({len(m['shots'])}장면 · {len(m['segments'])}구간 · {len(m['timeline_items'])}항목)")
        check(open(os.path.join(pipeline.PROJECTS, pid, "data.json"), "rb").read() == before, f"{pid}: data.json 그대로")

    print("2) 장면 덮어쓰기 (임시 프로젝트)")
    pid = temp_project("01-수술비", "_test_shots")
    d = raw(pid); d.update(tl={}, texts=[], overlays=[], edits=[], shots={}, shot_order=[]); save(pid, d)  # 사용자 수정값 없이 템플릿 기본으로
    base = caps(pid)
    # 순서 바꾸기: s2 ↔ s3
    d["shots"] = {}; d["shot_order"] = ["s1", "s3", "s2", "s4", "s5", "s6"]; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    st = {s["id"]: s["start"] for s in A["shots"]}
    check(st["s3"] == 2.0 and st["s2"] == 9.0, "순서 변경: s3가 2초, s2가 9초에서 시작")
    c = [(x["start"], x["end"]) for x in A["captions"]]
    check(c[1] == (9.0, 12.0), f"s2의 자막(원래 2~5초)이 s2를 따라 9~12초로 이동: {c[1]}")
    check(c[2] == (2.0, 5.5), f"s3의 첫 자막(원래 5~8.5초)이 2~5.5초로 이동: {c[2]}")
    check(A["total"] == 30.0, "전체 길이 그대로 30초")
    # 길이 바꾸기: s4 8초 → 5초
    d["shot_order"] = []; d["shots"] = {"s4": {"dur": 5.0}}; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check(A["total"] == 27.0, f"s4를 5초로 → 전체 27초 ({A['total']})")
    check(next(s for s in A["shots"] if s["id"] == "s5")["start"] == 17.0, "뒤 장면 s5가 17초로 당겨짐")
    c = [(x["start"], x["end"]) for x in A["captions"]]
    check(c[4] == (12.0, 17.0), f"s4 자막(12~20초)이 장면 길이에 맞춰 12~17초로: {c[4]}")
    check(c[5][0] == 17.0, f"s5 자막이 17초에서 시작: {c[5]}")
    # 숨기기
    d["shots"] = {"s2": {"hidden": True}}; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check(A["total"] == 27.0 and A["captions"][1]["gone"], "s2 숨김 → 27초, s2 자막 빠짐")
    # 소스 교체: s1을 공용 이미지로 → 자막·다른 장면 그대로
    d["shots"] = {"s1": {"kind": "image", "src": "library/mascot/surprised.png", "fit": "blur"}}; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check([(x["start"], x["end"]) for x in A["captions"]] == base, "s1 소스를 이미지로 바꿔도 자막 시간 그대로")
    check(raw(pid)["c_hook"] == d["c_hook"], "s1 소스 교체 후 자막 문구 그대로")
    # 사용자 장면 추가: s1 뒤에 1.5초 빈 화면
    d["shots"] = {"u1": {"user": True, "kind": "color", "color": "#ffffff", "dur": 1.5}}
    d["shot_order"] = ["s1", "u1", "s2", "s3", "s4", "s5", "s6"]; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check(A["total"] == 31.5 and A["pieces"][1]["kind"] == "color", "사용자 장면 추가 → 31.5초, 두 번째 구간이 빈 화면")
    check(A["captions"][1]["start"] == 3.5, f"s2 자막이 1.5초 밀려 3.5초 시작: {A['captions'][1]['start']}")
    m = model.build(pid)
    check(not m["validation"]["errors"], "덮어쓴 프로젝트도 모델 검증 통과")
    # 검증이 잘못된 값을 잡는지
    d["shots"] = {"s1": {"kind": "image", "src": "media/없는파일.png"}}; d["shot_order"] = []; save(pid, d)
    check(any("소스 파일이 없어요" in e for e in model.build(pid)["validation"]["errors"]), "없는 소스 파일을 검증이 잡음")
    d["shots"] = {"s1": {"dur": 0.05}}; save(pid, d)
    check(any("허용 범위" in e for e in model.build(pid)["validation"]["errors"]), "잘못된 장면 길이를 검증이 잡음")

    print("3) 장면별 캐시 (미리보기 렌더)")
    d["shots"] = {}; save(pid, d)
    t = time.time(); r = pipeline.render(pid, True)
    check(r["ok"] and len(r["shots_drawn"]) == 6, f"첫 렌더: 6장면을 그림 ({time.time() - t:.1f}초)")
    t = time.time(); r = pipeline.render(pid, True)
    check(r["ok"] and r["shots_drawn"] == [] and len(r["shots_reused"]) == 6, f"그대로 다시 렌더: 0장면 그림, 6장면 재사용 ({time.time() - t:.1f}초)")
    d["c_hook"] = "자막만 바꿈/[캐시] 확인"; save(pid, d)
    r = pipeline.render(pid, True)
    check(r["shots_drawn"] == [], "자막 문구만 바꿈 → 다시 그린 장면 없음")
    d["shots"] = {"s4": {"dur": 6.0}}; save(pid, d)
    r = pipeline.render(pid, True)
    check(r["shots_drawn"] == ["s4"] and len(r["shots_reused"]) == 5, f"s4 길이만 바꿈 → s4만 다시 그림 {r['shots_drawn']}")
    d["shots"] = {"s4": {"dur": 6.0}, "s1": {"kind": "image", "src": "library/mascot/surprised.png"}}; save(pid, d)
    r = pipeline.render(pid, True)
    check(r["shots_drawn"] == [] and "s1" not in r["shots_reused"], "s1 소스를 이미지로 교체 → 그리지 않고 이미지 사용")
    dur = float(subprocess.run([pipeline.gfx.ffmpeg_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                os.path.join(pipeline.PROJECTS, pid, "final_preview.mp4")], capture_output=True, text=True).stdout)
    check(abs(dur - 28.0) < 0.15, f"렌더 결과 길이 = 데이터 길이 28초 ({dur:.2f})")
    d["months"] = 1; d["total"] = 20; save(pid, d)  # 템플릿 입력값 변경 → 그린 장면 전부 무효 (보수적)
    r = pipeline.render(pid, True)
    check(len(r["shots_drawn"]) == 5, f"템플릿 입력값(보험사 수) 변경 → 그린 장면 5개 모두 다시 그림 {r['shots_drawn']}")
    shutil.rmtree(os.path.join(pipeline.PROJECTS, pid))

    print("3b) 말하는 마스코트 (임시 프로젝트, 미리보기 렌더)")
    pid = "_test_talk"; d0 = os.path.join(pipeline.PROJECTS, pid); shutil.rmtree(d0, ignore_errors=True); os.makedirs(os.path.join(d0, "media"))
    d = {"template": "talk", "title": pid, "is_sample": True, "review_no": "", "review_exp": "", **pipeline.defaults("talk")}; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    m_end = sum(x["dur"] for x in A["mascot"])
    check(A["mascot"] and abs(m_end - A["total"]) < 0.05, f"마스코트 동작 조각이 영상 전체를 채움 ({m_end:.2f} / {A['total']:.2f}초)")
    check(all(x["clip"] in ("idle", "talk", "finger") for x in A["mascot"]), "클립이 없는 동작(가리키기·놀람·엄지척)은 말하기/대기로 대신함")
    r = pipeline.render(pid, True)
    check(r["ok"], "녹음 전(글자 수 어림) 미리보기 렌더 성공" + ("" if r["ok"] else f": {r['errors']}"))
    edl = json.load(open(os.path.join(d0, "edl.json"), encoding="utf-8"))
    check(edl["overlays"] and edl["overlays"][0].get("chroma") and edl["overlays"][0]["end"] == A["total"], "edl: 마스코트가 초록 배경 제거 얹기로 영상 전체에 들어감")
    check(any(c.get("style") == "mainbox" and c.get("pos") == [540, 1440] for c in edl["captions"]), "edl: 대본 자막이 박스 자막·가슴 위 위치로 들어감")
    # 초록 배경이 지워졌는지: 마스코트 영역 맨 위 가장자리(배경 부분) 픽셀이 초록이 아니어야 한다
    px = subprocess.run([pipeline.gfx.ffmpeg_bin(), "-v", "error", "-ss", "1", "-i", os.path.join(d0, "final_preview.mp4"), "-frames:v", "1",
                         "-vf", "crop=4:4:20:250", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    rgb = tuple(px[:3])
    check(len(px) >= 3 and not (rgb[1] > 150 and rgb[0] < 120 and rgb[2] < 120), f"마스코트 초록 배경이 화면에 남지 않음 (배경 픽셀 {rgb})")
    # 녹음(말소리 1.2초 + 쉼 0.8초 ×5)을 넣고 줄 시작 시각을 주면 → 시간이 녹음을 따르고, 카드 때문에 배경 장면을 다시 그린다
    wav = os.path.join(d0, "media", "script_test.wav")
    tone = ";".join(f"sine=f=220:d=1.2[a{i}];anullsrc=r=48000:cl=stereo,atrim=0:0.8[s{i}]" for i in range(5))
    subprocess.run([pipeline.gfx.ffmpeg_bin(), "-v", "error", "-y", "-filter_complex",
                    tone + ";" + "".join(f"[a{i}]aformat=sample_rates=48000:channel_layouts=stereo[b{i}];" for i in range(5))
                    + "".join(f"[b{i}][s{i}]" for i in range(5)) + "concat=n=10:v=0:a=1[o]", "-map", "[o]", wav], check=True)
    d["voice"] = {"src": "media/script_test.wav", "dur": pipeline.probe_dur(wav), "marks": [0, 2, 4, 6, 8]}; save(pid, d)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check([c["start"] for c in A["captions"]] == [0, 2, 4, 6, 8] and abs(A["total"] - (d["voice"]["dur"] + 0.4)) < 0.01,
          f"녹음 시각대로 자막 시작 0·2·4·6·8초, 길이 = 녹음 + 0.4초 ({A['total']})")
    check(any(x["clip"] == "idle" for x in A["mascot"]), "녹음의 쉬는 구간에서 마스코트가 대기 동작으로 바뀜")
    r = pipeline.render(pid, True)
    check(r["ok"] and r["shots_drawn"], f"녹음을 넣으면 카드 시간이 바뀌어 배경 장면을 다시 그림 {r.get('shots_drawn')}")
    edl = json.load(open(os.path.join(d0, "edl.json"), encoding="utf-8"))
    check(any(v["src"].endswith("script_test.wav") for v in edl["voices"]), "edl: 대본 녹음이 소리로 들어감")
    shutil.rmtree(d0)

    print("3c) 채팅 스토리보드 (chat_tools, 임시 프로젝트, 미리보기 렌더)")
    import chat_tools, tempfile
    pid = "_test_plan"; shutil.rmtree(os.path.join(pipeline.PROJECTS, pid), ignore_errors=True)
    plan = {"title": pid, "headline": "시험 헤드라인/[강조]", "beats": [
        {"text": "첫 장면 자막", "prompt": "첫 그림", "purpose": "훅"}, {"text": "둘째 장면 [강조] 자막", "prompt": "둘째 그림"},
        {"text": "셋째 장면 자막", "prompt": "셋째 그림", "dur": 3.0}]}
    pf = os.path.join(tempfile.mkdtemp(), "plan.json"); json.dump(plan, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    chat_tools.cmd_new(pid, pf, force=True)
    A = pipeline.assemble(pipeline.load(pid), pid)
    check([s["id"] for s in A["shots"]] == ["b1", "b2", "b3"] and A["shots"][2]["dur"] == 3.0, "계획 → 장면 b1~b3, 길이 준 장면은 그 길이(3초)")
    head = [c for c in A["captions"] if c["idx"] is None]
    check(len(head) == 1 and head[0]["start"] == 0 and head[0]["end"] == A["total"], "헤드라인이 0초~끝까지 고정 자막으로 들어감")
    check(not model.build(pid)["validation"]["errors"], "계획 프로젝트 모델 검증 통과")
    chat_tools.cmd_keyframe(pid, "b2", os.path.join(pipeline.LIBRARY, "mascot", "think.png"), "시험 그림")
    d = raw(pid)
    check(d["shots"]["b2"]["kind"] == "image" and d["shots"]["b2"]["keyframes"][0]["approved"], "키프레임 → b2가 이미지 장면, 승인된 키프레임 기록")
    r = pipeline.render(pid, True)
    check(r["ok"] and sorted(r["shots_drawn"]) == ["b1", "b3"], f"렌더: 키프레임 없는 b1·b3만 대기 화면을 그림 {r.get('shots_drawn')}")
    edl = json.load(open(os.path.join(pipeline.PROJECTS, pid, "edl.json"), encoding="utf-8"))
    check(any(c.get("style") == "top" and c.get("size") == 84 and c["text"] == plan["headline"] for c in edl["captions"]), "edl: 헤드라인이 위 큰 글씨로 들어감")
    check(any(s.get("src", "").endswith("kf_b2.png") for s in edl["segments"]), "edl: b2 구간이 키프레임 이미지")
    plan["headline"] = "바뀐 헤드라인"; plan["beats"][0]["text"] = "바뀐 첫 자막"; json.dump(plan, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    chat_tools.cmd_update(pid, pf)
    d = raw(pid)
    check(d["headline"] == "바뀐 헤드라인" and d["shots"]["b2"]["kind"] == "image", "update: 헤드라인·자막만 바뀌고 키프레임은 그대로")
    shutil.rmtree(os.path.join(pipeline.PROJECTS, pid))

    if final:
        print("4) 기존 세 프로젝트 최종 MP4")
        for p in SEEDS:
            t = time.time(); r = pipeline.render(p, False)
            check(r["ok"], f"{p}: 최종 렌더 성공 ({time.time() - t:.0f}초)")
    print(f"\n통과 {ok_count}개")

if __name__ == "__main__":
    try: main()
    except AssertionError as e:
        print("  ✗ 실패:", e)
        for t in ("_test_shots", "_test_talk", "_test_plan"): shutil.rmtree(os.path.join(pipeline.PROJECTS, t), ignore_errors=True)
        sys.exit(1)
