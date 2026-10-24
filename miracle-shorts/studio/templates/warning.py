"""경고형 "절대 ~하지 마세요" — 25초, 그래픽만으로 제작.
구조: hunter/results/format_blueprints_1024.md 의 B 설계도 (냉동고기 레퍼런스 장면 분석).
훅 명령 → 권위 출처 → 손해 → 전환 → 대안 단계 → 효과 → 사례 → 결과 → 체크리스트(행동 촉구).
원본과 달리 대안은 말·자막으로 이름을 분명히 밝힌다(답을 숨기면 분노 댓글 → 신뢰 하락).
"""
from gfx import *

NAME = "경고형"
DESC = "'절대 ~하지 마세요' — 손해 이유와 대안을 25초에. 그래픽만으로 제작."

FIELDS = [
    {"section": "내용"},
    {"key": "topic", "label": "위 라벨 (주제)", "type": "text", "default": "보험 해지 전 체크"},
    {"key": "action", "label": "하지 말아야 할 행동 (짧게)", "type": "text", "default": "보험 바로 해지"},
    {"key": "authority", "label": "권위 출처 카드", "type": "text", "default": "7년 차 FP · 해지 상담 현장"},
    {"key": "losses", "label": "손해 이유 (줄마다 하나, 최대 3개)", "type": "lines", "default": [
        "다시 가입하면 보험료가 오를 수 있어요", "그사이 병이 생기면 가입이 어려울 수 있어요"]},
    {"key": "steps", "label": "대안 단계 (줄마다 하나, 최대 3개)", "type": "lines", "default": [
        "감액·납입유예 먼저 확인", "새 보험 승인 뒤에 해지"]},
    {"key": "effect", "label": "효과 한 줄", "type": "text", "default": "보장 공백 없이 정리"},
    {"key": "case", "label": "사례 (익명·각색)", "type": "text", "default": "보험료가 부담돼 해지하려던 30대 고객"},
    {"key": "case_result", "label": "사례 결과", "type": "text", "default": "감액으로 보장은 남기고 보험료는 줄임"},
    {"key": "mascot", "label": "마스코트 진행자 넣기 (훅 X팔 · 권위 얼굴 · 놀람 · 엄지척 · 가리키기)", "type": "bool", "default": True},
    {"section": "자막 ([단어] = 노란 강조, / = 줄바꿈)"},
    {"key": "c_hook", "label": "0~2초 훅", "type": "text", "default": "보험 해지,/절대 [바로] 하지 마세요"},
    {"key": "c_auth", "label": "2~3.5초 권위", "type": "text", "default": "7년 동안 해지 상담하며/본 건데요"},
    {"key": "c_loss", "label": "3.5~8초 손해", "type": "text", "default": "다시 가입하면/보험료가 [오를 수] 있어요"},
    {"key": "c_turn", "label": "8~9초 전환", "type": "text", "default": "그래서 [순서]를 바꿔야 해요"},
    {"key": "c_steps", "label": "9~13초 대안", "type": "text", "default": "감액·유예 먼저,/해지는 [승인 뒤]에"},
    {"key": "c_effect", "label": "13~16초 효과", "type": "text", "default": "보장 [공백] 없이/정리할 수 있어요"},
    {"key": "c_case", "label": "16~19초 사례", "type": "text", "default": "실제 상담에서도"},
    {"key": "c_result", "label": "19~22초 결과", "type": "text", "default": "보장은 남기고/보험료는 [줄였어요]"},
    {"key": "c_cta", "label": "22~25초 행동 촉구", "type": "text", "default": "해지 전에/이 [두 가지]만 확인하세요"},
]

CAP_KEYS = ["c_hook", "c_auth", "c_loss", "c_turn", "c_steps", "c_effect", "c_case", "c_result", "c_cta"]

def validate(data):
    errs = []
    if not [s for s in data["losses"] if s.strip()]: errs.append("손해 이유를 하나 이상 넣어 주세요.")
    if not [s for s in data["steps"] if s.strip()]: errs.append("대안 단계를 하나 이상 넣어 주세요.")
    return errs

def x_mark(d, cx, cy, r, color, width=22, p=1.0):
    d.line([cx - r, cy - r, cx - r + 2 * r * min(1, p * 2), cy - r + 2 * r * min(1, p * 2)], fill=color, width=width)
    if p > 0.5:
        q = (p - 0.5) * 2
        d.line([cx + r, cy - r, cx + r - 2 * r * q, cy - r + 2 * r * q], fill=color, width=width)

def check_mark(d, cx, cy, r, color, width=16, p=1.0):
    a = (cx - r, cy); b = (cx - r * 0.3, cy + r * 0.7); c = (cx + r, cy - r * 0.7)
    q1 = min(1, p * 2); d.line([a, (lerp(a[0], b[0], q1), lerp(a[1], b[1], q1))], fill=color, width=width)
    if p > 0.5:
        q2 = (p - 0.5) * 2; d.line([b, (lerp(b[0], c[0], q2), lerp(b[1], c[1], q2))], fill=color, width=width)

def rows(d, t, items, color, mark, t0, step, y0=420, gap=170, x1=990):
    for k, s in enumerate(items):
        a = ease((t - t0 - k * step) / 0.3)
        if a <= 0: continue
        y = y0 + k * gap; x = 90 + (1 - a) * 60; w = x1 - 90
        d.rounded_rectangle([x, y, x + w, y + 140], radius=18, fill=(28, 32, 40), outline=color, width=4)
        d.ellipse([x + 30, y + 30, x + 110, y + 110], fill=color)
        mark(d, x + 70, y + 70, 22, WHITE, 10, 1.0)
        lines = wrap(d, s, font(42, "ExtraBold"), w - 180)[:2]
        for j, ln in enumerate(lines):
            d.text((x + 140, y + 70 + (j - (len(lines) - 1) / 2) * 50), ln, font=font(42, "ExtraBold"), fill=WHITE, anchor="lm")

def build(data):
    losses = [s for s in data["losses"] if s.strip()][:3]
    steps = [s for s in data["steps"] if s.strip()][:3]
    M = data.get("mascot", True)  # 마스코트가 진행자로 나온다: 훅 X팔·권위 아바타·놀람·엄지척·가리키기

    def w1(d, t):  # 훅: 행동 + X (마스코트가 팔로 X)
        label_top(d, data["topic"], RED)
        if M:
            d.rounded_rectangle([60, 430, 680, 640], radius=24, fill=GRAY)
            text_c(d, (370, 535), data["action"], fit_font(d, data["action"], 540, 76, "Black"), WHITE)
            d.ellipse([200, 690, 540, 1030], outline=RED, width=22)
            x_mark(d, 370, 860, 92, RED, 28, ease((t - 0.25) / 0.5))
            draw_mascot(d, "stop", 870, 380, 760, t, appear=0.05)
        else:
            d.rounded_rectangle([140, 430, 940, 650], radius=24, fill=GRAY)
            text_c(d, (540, 540), data["action"], fit_font(d, data["action"], 720, 76, "Black"), WHITE)
            d.ellipse([340, 700, 740, 1100], outline=RED, width=24)
            x_mark(d, 540, 900, 110, RED, 30, ease((t - 0.25) / 0.5))

    def w2(d, t):  # 권위 출처 (마스코트 얼굴 아바타)
        label_top(d, data["topic"])
        d.rounded_rectangle([140, 560, 940, 900], radius=28, fill=(28, 32, 40), outline=YELLOW, width=5)
        if M:
            d.ellipse([194, 634, 386, 826], fill=YELLOW)
            d._image.paste(av := mascot_avatar("point", 180), (200, 640), av)
        else:
            d.ellipse([200, 640, 380, 820], fill=YELLOW)
            text_c(d, (290, 730), "FP", font(70, "Black"), BG)
        lines = wrap(d, data["authority"], font(48, "ExtraBold"), 500)[:2]
        for j, ln in enumerate(lines):
            d.text((420, 730 + (j - (len(lines) - 1) / 2) * 62), ln, font=font(48, "ExtraBold"), fill=WHITE, anchor="lm")

    def w3(d, t):  # 손해 (마스코트 놀람)
        label_top(d, "이렇게 되면 손해", RED)
        rows(d, t, losses, RED, lambda d, cx, cy, r, c, w, p: d.line([cx - r, cy, cx + r, cy], fill=c, width=w), 0.1, 1.4,
             x1=760 if M else 990)
        if M: draw_mascot(d, "surprised", 910, 420, 700, t, appear=0.2)

    def w4(d, t):  # 전환: 행동에 줄 긋기
        label_top(d, data["topic"])
        d.rounded_rectangle([140, 600, 940, 820], radius=24, fill=GRAY)
        text_c(d, (540, 710), data["action"], fit_font(d, data["action"], 720, 76, "Black"), GRAY_T)
        p = ease(t / 0.5); d.line([170, 710, 170 + 740 * p, 710], fill=RED, width=14)

    def w5(d, t):  # 대안 단계
        label_top(d, "이렇게 하세요", GREEN)
        rows(d, t, steps, GREEN, check_mark, 0.1, 1.2)

    def w6(d, t):  # 효과 (마스코트 엄지척)
        label_top(d, "결과", GREEN)
        p = ease(t / 0.4)
        if M:
            draw_mascot(d, "thumbsup", 250, 390, 740, t, appear=0.0, enter="left")
            d.ellipse([560, 470, 860, 770], fill=GREEN)
            check_mark(d, 710, 620, 80, WHITE, 26, ease((t - 0.2) / 0.5))
            lines = wrap(d, data["effect"], font(58, "Black"), 520)[:2]
            for j, ln in enumerate(lines):
                text_c(d, (710, 880 + j * 72), ln, font(58, "Black"), WHITE if p > 0.5 else GRAY_T)
        else:
            d.ellipse([390, 460, 690, 760], fill=GREEN)
            check_mark(d, 540, 610, 80, WHITE, 26, ease((t - 0.2) / 0.5))
            text_c(d, (540, 880), data["effect"], fit_font(d, data["effect"], 860, 64, "Black"), WHITE if p > 0.5 else GRAY_T)

    def w7(d, t):  # 사례 → 결과 (16~22초, 6초)
        label_top(d, "실제 상담 사례 (각색)", YELLOW)
        d.rounded_rectangle([110, 420, 970, 700], radius=30, fill=WHITE)
        d.polygon([(220, 700), (300, 700), (230, 770)], fill=WHITE)
        lines = wrap(d, data["case"], font(46, "ExtraBold"), 760)[:3]
        for j, ln in enumerate(lines):
            text_c(d, (540, 560 + (j - (len(lines) - 1) / 2) * 60), ln, font(46, "ExtraBold"), INK)
        a = ease((t - 3.0) / 0.4)
        if a > 0:
            y = 820 + (1 - a) * 40
            d.rounded_rectangle([110, y, 970, y + 220], radius=24, fill=(20, 60, 40), outline=GREEN, width=5)
            lines = wrap(d, data["case_result"], font(46, "ExtraBold"), 760)[:2]
            for j, ln in enumerate(lines):
                text_c(d, (540, y + 110 + (j - (len(lines) - 1) / 2) * 60), ln, font(46, "ExtraBold"), WHITE)

    def w8(d, t):  # 체크리스트 (마스코트가 왼쪽 목록을 가리킴)
        label_top(d, "해지 전 체크리스트" if "해지" in data["topic"] else data["topic"], YELLOW)
        x1 = 740 if M else 970
        for k, s in enumerate(steps):
            y = 460 + k * 190
            d.rounded_rectangle([90, y, x1, y + 150], radius=18, fill=(28, 32, 40))
            d.rounded_rectangle([130, y + 35, 210, y + 115], radius=12, outline=YELLOW, width=6)
            check_mark(d, 170, y + 75, 26, YELLOW, 10, ease((t - 0.4 - k * 0.6) / 0.4))
            d.text((250, y + 75), s, font=fit_font(d, s, x1 - 290, 44, "ExtraBold"), fill=WHITE, anchor="lm")
        if M: draw_mascot(d, "point", 905, 400, 720, t, mirror=True)

    scenes = [("w1", 2.0, w1), ("w2", 1.5, w2), ("w3", 4.5, w3), ("w4", 1.0, w4), ("w5", 4.0, w5),
              ("w6", 3.0, w6), ("w7", 6.0, w7), ("w8", 3.0, w8)]
    captions = [(0.0, 2.0, data["c_hook"]), (2.0, 3.5, data["c_auth"]), (3.5, 8.0, data["c_loss"]),
                (8.0, 9.0, data["c_turn"]), (9.0, 13.0, data["c_steps"]), (13.0, 16.0, data["c_effect"]),
                (16.0, 19.0, data["c_case"]), (19.0, 22.0, data["c_result"]), (22.0, 25.0, data["c_cta"])]
    sfx = ([{"t": 0.0, "name": "impact", "vol": 0.8}, {"t": 2.0, "name": "whoosh", "vol": 0.5}] +
           [{"t": round(3.6 + 1.4 * k, 2), "name": "pop", "vol": 0.5} for k in range(len(losses))] +
           [{"t": 8.0, "name": "swoosh_down", "vol": 0.5}] +
           [{"t": round(9.1 + 1.2 * k, 2), "name": "ding", "vol": 0.35} for k in range(len(steps))] +
           [{"t": 13.0, "name": "whoosh", "vol": 0.5}, {"t": 16.0, "name": "whoosh", "vol": 0.5},
            {"t": 19.0, "name": "pop", "vol": 0.6}] +
           [{"t": round(22.4 + 0.6 * k, 2), "name": "tick", "vol": 0.5} for k in range(len(steps))] +
           [{"t": 24.0, "name": "ding", "vol": 0.6}])
    note = "사례는 익명·각색 · 개인 상황에 따라 다를 수 있음"
    return scenes, captions, sfx, note
