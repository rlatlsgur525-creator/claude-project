"""말하는 마스코트 — 대본만 쓰면 되는 쇼츠.
마스코트(상반신)가 가운데서 말하고, 줄마다 동작(손가락·가리키기·놀람·엄지척)과 포인트 카드가 붙는다.
타이밍: 녹음(voice.marks = 프롬프터에서 '다음'을 누른 시각)이 있으면 그대로, 없으면 글자 수로 추정.
말하기/대기 동작: 녹음의 말소리 구간(_speech, pipeline이 계산)으로 나눈다.
동작 클립: studio/library/anim/clips.json (같은 자세로 시작·끝나는 초록 배경 클립).
"""
import json, math, os, re
from gfx import *

NAME = "말하는 마스코트"
DESC = "대본을 한 줄씩 쓰고 녹음만 하면, 마스코트가 말하고 포인트 카드가 나오는 쇼츠."

GESTURES = [["", "없음"], ["finger", "손가락 위로(포인트)"], ["point", "카드 가리키기"], ["surprised", "놀람"], ["thumbs", "엄지척"]]
ANIM_DIR = os.path.join(HERE, "library", "anim")

def gesture_options():
    """화면의 동작 고르기용. 동작 클립이 아직 없는 것은 '준비 중'으로 표시(고르면 효과음만 나고 마스코트는 말하기 동작 그대로)."""
    try: have = json.load(open(os.path.join(ANIM_DIR, "clips.json"), encoding="utf-8"))
    except OSError: have = {}
    return [[k, n if not k or k in have else n + " · 준비 중"] for k, n in GESTURES]

FIELDS = [
    {"section": "대본 (한 줄 = 한 문장)"},
    {"key": "lines", "label": "대본", "type": "script", "options": gesture_options(), "default": [
        {"text": "수술비 싸서 가입했다면, 이것부터 확인하세요", "card": "", "gesture": "surprised"},
        {"text": "24개 보험사 수술비 약관을 전부 비교해 봤는데요", "card": "24개사 약관/[전부] 비교", "gesture": "finger"},
        {"text": "18곳은 거의 같고, 4곳은 더 넓게 줘요", "card": "넓게 보장 [4곳]", "gesture": "point"},
        {"text": "그런데 2곳은 티눈·사마귀를 수술로 안 봐요", "card": "확인 필요 [2곳]", "gesture": "surprised"},
        {"text": "내 약관 '수술의 정의'에 제외 항목이 있는지만 보세요", "card": "'수술의 정의'/[제외 항목] 확인", "gesture": "thumbs"}]},
    {"key": "note", "label": "준법 표기 둘째 줄", "type": "text", "default": "회사 익명 · 개인 상황에 따라 다를 수 있음"},
]
CAP_KEYS = []  # 자막은 대본 줄에서 나온다
SCENE_KEYS = ("voice",)  # 포인트 카드 시간이 녹음 시각(voice.marks)을 따르므로, 다시 녹음하면 배경 장면도 다시 그린다
BG_COL = (238, 240, 244)
MASCOT_BOX = (0, 480, 1080)  # x, y, 폭 — 3:4 클립(1080×1440)을 화면 아래에 붙인다
CAP_POS = [540, 1440]

def clips():
    return json.load(open(os.path.join(ANIM_DIR, "clips.json"), encoding="utf-8"))

def validate(data):
    lines = [l for l in data.get("lines") or [] if l.get("text", "").strip()]
    if not lines: return ["대본을 한 줄 이상 써 주세요."]
    if not os.path.exists(os.path.join(ANIM_DIR, "clips.json")): return ["마스코트 동작 클립이 없어요 (studio/library/anim)."]
    return []

def wrap2(text, n=14):
    """자막 한 줄이 길면 가운데 근처 띄어쓰기에서 '/'로 나눈다 (이미 '/'가 있으면 그대로)."""
    if "/" in text or len(re.sub(r"[\[\]]", "", text)) <= n: return text
    sp = [m.start() for m in re.finditer(" ", text)]
    if not sp: return text
    mid = len(text) / 2; k = min(sp, key=lambda i: abs(i - mid))
    return text[:k] + "/" + text[k + 1:]

def timing(data):
    """줄마다 (시작, 끝), 전체 길이"""
    lines = [l for l in data["lines"] if l.get("text", "").strip()]
    v = data.get("voice") or {}
    marks = v.get("marks") or []
    if v.get("src") and len(marks) >= len(lines) and v.get("dur"):
        starts = [max(0.0, float(m)) for m in marks[:len(lines)]]; total = round(float(v["dur"]) + 0.4, 2)
    else:  # 녹음 전: 글자 수로 추정 (초당 약 6.5자)
        starts, t = [], 0.3
        for l in lines:
            starts.append(round(t, 2)); n = len(re.sub(r"[\s\[\]/]", "", l["text"]))
            t += max(1.6, n / 6.5 + 0.35) + (0.5 if l.get("gesture") else 0)
        total = round(t + 0.4, 2)
    ends = [round(starts[i + 1] - 0.05, 2) for i in range(len(starts) - 1)] + [round(total - 0.2, 2)]
    return lines, starts, ends, total

def mascot_track(data, lines, starts, ends, total):
    """[(클립, 클립 안 시작, 길이)] 전체를 빈틈없이 채운다."""
    C = clips(); speech = data.get("_speech")
    events = []  # (시작, 클립)
    busy_until = -1
    for l, s in zip(lines, starts):
        g = l.get("gesture") or ""
        if g and g in C and s >= busy_until:
            events.append((s, g)); busy_until = s + C[g]["out"] - C[g]["in"]
    def speaking(a, b):
        if not speech: return [(a, b, True)]  # 녹음 전에는 줄 동안 계속 말한다
        out, t = [], a
        for s, e in speech:
            s, e = max(s, a), min(e, b)
            if e - s <= 0: continue
            if s - t > 0.35: out.append((t, s, False))
            out.append((min(t, s) if s - t <= 0.35 else s, e, True)); t = e
        if b - t > 0: out.append((t, b, b - t <= 0.35))
        return out
    # 줄 구간(말하기) 밖은 대기
    spans = []
    t = 0.0
    for s, e in zip(starts, ends):
        if s > t: spans.append((t, s, False))
        spans += speaking(s, e); t = e
    if total > t: spans.append((t, total, False))
    # 동작 구간을 기본(말하기·대기) 구간 위에 덮어쓴다
    gest = [(s, min(total, s + C[g]["out"] - C[g]["in"]), g) for s, g in events]
    pieces = []
    for a, b, talking in spans:
        cur = [(a, b)]
        for gs, ge, _ in gest:
            cur = [seg for x0, x1 in cur for seg in ((x0, min(x1, gs)), (max(x0, ge), x1)) if seg[1] - seg[0] > 0.02]
        pieces += [(x0, x1, "talk" if talking else "idle") for x0, x1 in cur]
    pieces += [(gs, ge, g) for gs, ge, g in gest]
    pieces.sort()
    track, phase = [], {"talk": 0.0, "idle": 0.0}
    for a, b, name in pieces:
        if name in phase:  # 반복 클립은 이어지던 위치부터 계속 → 매번 처음부터 시작하지 않는다
            L = C[name]["out"] - C[name]["in"]; x = a
            while b - x > 0.02:
                p = phase[name] % L; d = min(b - x, L - p)
                track.append((name, round(C[name]["in"] + p, 3), round(d, 3))); phase[name] += d; x += d
        else:
            track.append((name, C[name]["in"], round(b - a, 3)))
    return [p for p in track if p[2] > 0.02]

def build(data):
    lines, starts, ends, total = timing(data)
    C = clips()
    # 카드: 줄의 card가 있으면 그 줄 시작(+손가락이면 동작 뒤) ~ 다음 카드 전까지
    cards = []
    for i, (l, s) in enumerate(zip(lines, starts)):
        if l.get("card", "").strip():
            lead = 0.7 if l.get("gesture") in ("finger", "point") else 0.15
            cards.append([round(s + lead, 2), None, l["card"].strip()])
    for i, c in enumerate(cards):
        c[1] = cards[i + 1][0] - 0.05 if i + 1 < len(cards) else total
    def draw_card(d, txt, p):
        rows = [r for r in txt.split("/") if r.strip()][:3]
        h = 120 + 110 * len(rows); w = 860; x0 = (W - w) / 2; y0 = 250 + (380 - h) / 2
        sc = 0.85 + 0.15 * p
        cx, cy = W / 2, y0 + h / 2; ww, hh = w * sc, h * sc
        d.rounded_rectangle([cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2], radius=34, fill=WHITE, outline=(20, 20, 24), width=7)
        for j, r in enumerate(rows):
            y = cy - hh / 2 + (60 + 110 * j + 55) * sc
            parts = re.split(r"(\[.+?\])", r)
            f = fit_font(d, re.sub(r"[\[\]]", "", r), ww - 80, int(84 * sc), "Black")
            tw = d.textlength(re.sub(r"[\[\]]", "", r), font=f); x = cx - tw / 2
            for part in parts:
                if not part: continue
                hl = part.startswith("["); s = part.strip("[]")
                d.text((x, y), s, font=f, fill=RED if hl else INK, anchor="lm"); x += d.textlength(s, font=f)
    def bg(d, t):
        d.rectangle([0, 0, W, H], fill=BG_COL)
        for a, b, txt in cards:
            if a <= t <= b:
                p = ease((t - a) / 0.18); draw_card(d, txt, p)
    scenes = [("bg", total, bg)]
    captions = [(s, e, wrap2(l["text"])) for l, s, e in zip(lines, starts, ends)]
    sfx = [{"t": a, "name": "pop", "vol": 0.6} for a, _, _ in cards]
    for l, s in zip(lines, starts):
        if l.get("gesture") == "surprised": sfx.append({"t": s, "name": "impact", "vol": 0.5})
        if l.get("gesture") == "thumbs": sfx.append({"t": s + 0.3, "name": "ding", "vol": 0.5})
    sfx.sort(key=lambda s: s["t"])
    note = data.get("note", "")
    x, y, w = MASCOT_BOX
    extras = {"mascot_track": mascot_track(data, lines, starts, ends, total),
              "mascot_box": {"x": x, "y": y, "w": w}, "cap_style": "mainbox", "cap_pos": CAP_POS,
              "small_pos": [540, 180], "small_size": 40}
    v = data.get("voice") or {}
    if v.get("src"): extras["voices"] = [{"src": v["src"], "offset": 0.0, "vol": 1.0}]
    return scenes, captions, sfx, note, extras
