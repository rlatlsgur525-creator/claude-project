"""채팅 스토리보드 — 채팅으로 만드는 쇼츠 (Claude Code의 chat-shorts 스킬이 채운다).
대본 한 줄(비트) = 장면 하나(b1, b2 …). 장면 화면은 키프레임 이미지·영상(data.shots[bN], studio/chat_tools.py keyframe)이고,
키프레임이 아직 없으면 '키프레임 대기' 화면에 그림 설명(prompt)을 보여 준다. 헤드라인은 영상 내내 위에 고정.
타이밍: 녹음(voice.marks)이 있으면 그대로, 없으면 비트의 dur, 그것도 없으면 글자 수로 어림.
"""
import re
from gfx import *

NAME = "채팅 스토리보드"
DESC = "대본 한 줄 = 장면 하나. 채팅으로 장면을 설계하고 키프레임 그림을 넣어 만드는 쇼츠."

FIELDS = [
    {"section": "헤드라인 (영상 내내 위에 고정)"},
    {"key": "headline", "label": "헤드라인 ('/' 줄바꿈, [ ] 노란 강조)", "type": "text", "default": "수술비 싸서 가입했다면/[이것] 확인하세요"},
    {"section": "대본 (한 줄 = 장면 하나)"},
    {"key": "beats", "label": "장면", "type": "script", "columns": [
        {"key": "prompt", "label": "키프레임 그림 설명", "type": "text"},
        {"key": "dur", "label": "길이 (초, 비우면 자동)", "type": "number"}],
     "default": [
        {"text": "수술비 특약, 다 똑같다고 생각하셨죠", "prompt": "보험증권을 들여다보며 고개를 갸웃하는 직장인", "dur": None},
        {"text": "보험사마다 [수술]의 정의가 조금씩 달라요", "prompt": "여러 장의 약관 문서가 책상 위에 펼쳐진 모습", "dur": None},
        {"text": "어떤 약관은 일부 시술을 수술로 안 봐요", "prompt": "돋보기로 약관의 작은 글씨를 비추는 손", "dur": None},
        {"text": "내 약관 '수술의 정의'만 먼저 확인하세요", "prompt": "휴대폰 화면의 약관 PDF에서 '수술'을 검색하는 손", "dur": None}]},
    {"key": "note", "label": "준법 표기 둘째 줄", "type": "text", "default": "예시 · 개인 상황에 따라 다를 수 있음"},
]
CAP_KEYS = []  # 자막은 대본 줄에서 나온다
SCENE_KEYS = ("voice",)  # 녹음 시각이 바뀌면 장면 길이가 바뀐다

HEAD_POS, HEAD_SIZE = [540, 250], 84

def beats(data):
    return [b for b in data.get("beats") or [] if (b.get("text") or "").strip()]

def validate(data):
    if not beats(data): return ["대본(장면)을 한 줄 이상 써 주세요."]
    return []

def timing(data):
    """장면마다 (시작, 끝), 전체 길이. 장면은 빈틈없이 이어진다."""
    bs = beats(data)
    v = data.get("voice") or {}
    marks = v.get("marks") or []
    if v.get("src") and len(marks) >= len(bs) and v.get("dur"):
        starts = [0.0] + [max(0.0, float(m)) for m in marks[1:len(bs)]]; total = round(float(v["dur"]) + 0.4, 2)
    else:
        starts, t = [], 0.0
        for b in bs:
            starts.append(round(t, 2)); n = len(re.sub(r"[\s\[\]/]", "", b["text"]))
            t += float(b["dur"]) if b.get("dur") else max(2.0, n / 6.5 + 0.6)
        total = round(t, 2)
    ends = starts[1:] + [total]
    return bs, starts, ends, total

def wrap2(text, n=14):
    """자막 한 줄이 길면 가운데 근처 띄어쓰기에서 '/'로 나눈다 (이미 '/'가 있으면 그대로)."""
    if "/" in text or len(re.sub(r"[\[\]]", "", text)) <= n: return text
    sp = [m.start() for m in re.finditer(" ", text)]
    if not sp: return text
    mid = len(text) / 2; k = min(sp, key=lambda i: abs(i - mid))
    return text[:k] + "/" + text[k + 1:]

def waiting(i, b):
    """키프레임이 없는 장면: 번호와 그림 설명을 보여 주는 대기 화면"""
    def draw(d, t):
        d.rectangle([0, 0, W, H], fill=BG)
        x0, y0, x1, y1 = 90, 560, W - 90, 1120
        d.rounded_rectangle([x0, y0, x1, y1], radius=28, outline=GRAY, width=4)
        text_c(d, (W / 2, y0 + 80), f"장면 {i + 1} · 키프레임 대기", font(44, "ExtraBold"), GRAY_T)
        f = font(46, "Bold"); y = y0 + 170
        for line in wrap(d, b.get("prompt") or "(그림 설명 없음)", f, x1 - x0 - 100)[:5]:
            text_c(d, (W / 2, y), line, f, WHITE); y += 66
    return draw

def build(data):
    bs, starts, ends, total = timing(data)
    scenes = [(f"b{i + 1}", round(e - s, 3), waiting(i, b)) for i, (b, s, e) in enumerate(zip(bs, starts, ends))]
    captions = [(s + 0.05, e - 0.05, wrap2(b["text"])) for b, s, e in zip(bs, starts, ends)]
    sfx = [{"t": s, "name": "whoosh", "vol": 0.35} for s in starts[1:]]
    extras = {"fixed_caps": [{"text": data.get("headline", ""), "style": "top", "pos": HEAD_POS, "size": HEAD_SIZE, "anim": "none", "key": "headline"}]
              if (data.get("headline") or "").strip() else []}
    v = data.get("voice") or {}
    if v.get("src"): extras["voices"] = [{"src": v["src"], "offset": 0.0, "vol": 1.0}]
    return scenes, captions, sfx, data.get("note", ""), extras
