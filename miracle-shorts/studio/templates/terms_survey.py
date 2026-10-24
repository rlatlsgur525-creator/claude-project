"""약관 전수조사 — 담보 하나를 전 보험사 약관으로 비교하는 30초 쇼츠.
구조(CLAUDE.md 수술비 편 합의안): 카드 N장 중 확인 필요만 빨강 → 약관 PDF 쌓임 → 표준/넓게/확인 필요 정렬
→ 넓게 보장 뒤집기 → 멈춤 후 확인 필요 뒤집기 → 비교 기준 조항 짚기(셀프체크) → 바로 끝.
자막의 {coverage} {total} {standard} {wide} {caution} {items} 는 입력값으로 자동 치환된다.
"""
import math, random
from gfx import *

NAME = "약관 전수조사"
DESC = "담보 하나(수술비·진단비·입원일당…)를 전 보험사 약관으로 비교. 30초, 그래픽만으로 제작."

FIELDS = [
    {"section": "비교 내용"},
    {"key": "coverage", "label": "담보 이름", "type": "text", "default": "수술비"},
    {"key": "total", "label": "비교한 보험사 수", "type": "number", "default": 24, "min": 4, "max": 30},
    {"key": "n_wide", "label": "넓게 보장 (곳)", "type": "number", "default": 4, "min": 1, "max": 12},
    {"key": "n_caution", "label": "확인 필요 (곳)", "type": "number", "default": 2, "min": 1, "max": 6,
     "help": "표준 = 전체 − 넓게 − 확인 필요 (자동 계산)"},
    {"key": "criterion", "label": "비교 기준 조항", "type": "text", "default": "수술의 정의"},
    {"key": "wide_label", "label": "넓게 보장 카드 뒷면 제목", "type": "text", "default": "수술 제외 항목"},
    {"key": "wide_value", "label": "넓게 보장 카드 뒷면 결과", "type": "text", "default": "적음"},
    {"key": "caution_label", "label": "확인 필요 카드 뒷면 제목", "type": "text", "default": "수술로 안 보는 것"},
    {"key": "caution_items", "label": "확인 필요 항목 (줄마다 하나, 최대 3개)", "type": "lines", "default": ["티눈", "사마귀"]},
    {"section": "셀프체크 조항 화면"},
    {"key": "clause_title", "label": "조항 제목", "type": "text", "default": "제○조 (수술의 정의)"},
    {"key": "clause_lines", "label": "조항 문구 (줄마다 하나, 최대 7줄)", "type": "lines", "default": [
        "① '수술'이란 의사가 치료를 직접", "목적으로 필요하다고 인정하여", "기구를 사용해 생체에 절단·절제 등의",
        "조작을 가하는 것을 말합니다.", "② 다음은 수술로 보지 않습니다.", "티눈·사마귀 제거 등 (예시 문구)"]},
    {"key": "clause_highlight", "label": "형광펜 칠할 줄에 들어있는 글자", "type": "text", "default": "티눈"},
    {"section": "자막 ([단어] = 노란 강조, / = 줄바꿈)"},
    {"key": "c_hook", "label": "0~2초 훅", "type": "text", "default": "{coverage} 싸서 가입했다면/이 [{caution}곳]인지 확인하세요"},
    {"key": "c_pdf", "label": "2~5초 약관 수집", "type": "text", "default": "{total}개 보험사 {coverage} 약관/[전부] 비교했습니다"},
    {"key": "c_std", "label": "5~8.5초 표준", "type": "text", "default": "[{standard}곳]은 거의 같고"},
    {"key": "c_wide", "label": "8.5~12초 넓게", "type": "text", "default": "[{wide}곳]은 더 넓게 줍니다"},
    {"key": "c_flip", "label": "12~20초 넓게 뒤집기", "type": "text", "default": "'수술'에서 빼는 항목이/더 [적어요]"},
    {"key": "c_pause", "label": "20~22.8초 멈춤", "type": "text", "default": "그런데 이 {caution}곳은…"},
    {"key": "c_reveal", "label": "22.8~26초 공개", "type": "text", "default": "[{items}]를/수술로 안 봅니다"},
    {"key": "c_check", "label": "26~30초 셀프체크", "type": "text", "default": "내 약관에 이 문구가/있는지만 [보세요]"},
]

CAP_KEYS = ["c_hook", "c_pdf", "c_std", "c_wide", "c_flip", "c_pause", "c_reveal", "c_check"]

def _vals(data):
    tot = int(data["total"]); nw = int(data["n_wide"]); nc = int(data["n_caution"])
    items = [s for s in data["caution_items"] if s.strip()][:3]
    return dict(coverage=data["coverage"], total=tot, wide=nw, caution=nc, standard=tot - nw - nc,
                items="·".join(items))

def validate(data):
    v = _vals(data); errs = []
    if v["standard"] < 0: errs.append("넓게 보장 + 확인 필요가 전체 보험사 수보다 많아요.")
    if not v["items"]: errs.append("확인 필요 항목을 하나 이상 넣어 주세요.")
    if len(data["clause_lines"]) > 7: errs.append("조항 문구는 7줄까지만 들어가요.")
    return errs

def codes(n):
    return [chr(65 + i) if n <= 26 else f"{chr(65 + i // 10)}{i % 10}" for i in range(n)]

def build(data):
    v = _vals(data); N = v["total"]; C = codes(N); sample = data.get("is_sample", True)
    order = list(range(N)); random.Random(7).shuffle(order)
    RED_IDX = sorted(order[:v["caution"]]); GREEN_IDX = sorted(order[v["caution"]:v["caution"] + v["wide"]])
    GRAY_IDX = [i for i in range(N) if i not in RED_IDX + GREEN_IDX]
    G = grid(N, 60, 330, 1020, 1130, cols=6, gap=22, aspect=180 / 140)
    big = font(min(58, G[0][2] * 0.42), "ExtraBold")

    def s1(d, t):
        label_top(d, f"보험사 {N}곳 · {v['coverage']} 약관")
        pulse = 0.5 + 0.5 * math.sin(t * 9)
        for i in range(N):
            x, y, w, h = G[i]; a = ease((t - i * 0.012) / 0.25)
            red = i in RED_IDX
            card(d, x, y + (1 - a) * 40, w, h, RED if red else GRAY, C[i], big, WHITE if red else GRAY_T,
                 glow=(255, 160, 130) if red and pulse > 0.4 else None)

    def s2(d, t):
        label_top(d, "회사별 약관 PDF")
        n = min(N, int(t / 2.4 * N) + 1)
        for k in range(n):
            drop = ease((t - k * 0.1) / 0.25)
            bx = W / 2 - 170 + ((k * 37) % 23) - 11
            by = 1130 - k * (336 / N) - (1 - drop) * 300
            d.rounded_rectangle([bx, by - 70, bx + 340, by], radius=10, fill=WHITE, outline=(200, 204, 212), width=2)
            d.rectangle([bx + 18, by - 56, bx + 74, by - 30], fill=RED)
            d.text((bx + 46, by - 43), "PDF", font=font(18, "Black"), fill=WHITE, anchor="mm")
            d.text((bx + 92, by - 43), f"{C[k]}사 약관", font=font(26, "Bold"), fill=(40, 44, 52), anchor="lm")
        text_c(d, (W / 2, 420), f"{n}", font(190, "Black"), YELLOW)
        text_c(d, (W / 2, 545), "개사 비교", font(52, "ExtraBold"), WHITE)

    gcols = 3 if len(GRAY_IDX) <= 18 else 4
    GS = grid(len(GRAY_IDX), 60, 440, 420, 1140, cols=gcols, gap=12, aspect=110 / 86)
    GW = grid(len(GREEN_IDX), 450, 440, 700, 1140, cols=2 if len(GREEN_IDX) > 1 else 1, gap=12, aspect=110 / 86)
    GR = grid(len(RED_IDX), 730, 440, 1020, 1140, cols=min(2, len(RED_IDX)), gap=12, aspect=110 / 86)
    # 그룹 카드를 위쪽에 붙인다
    def top_align(slots):
        if not slots: return slots
        dy = slots[0][1] - 440; return [(x, y - dy, w, h) for x, y, w, h in slots]
    GS, GW, GR = top_align(GS), top_align(GW), top_align(GR)
    def slot(i):
        if i in GRAY_IDX: return GS[GRAY_IDX.index(i)]
        if i in GREEN_IDX: return GW[GREEN_IDX.index(i)]
        return GR[RED_IDX.index(i)]

    def s3(d, t):
        p = ease((t - 0.2) / 1.4)
        for i in range(N):
            gx, gy, gw, gh = G[i]; sx, sy, sw, sh = slot(i)
            if i in RED_IDX: col = RED
            elif i in GREEN_IDX: col = tuple(int(lerp(a, b, p)) for a, b in zip(GRAY, GREEN))
            else: col = GRAY
            glow = (150, 240, 190) if (i in GREEN_IDX and t > 3.5 and int(t * 4) % 2 == 0) else None
            card(d, lerp(gx, sx, p), lerp(gy, sy, p), lerp(gw, sw, p), lerp(gh, sh, p), col, C[i],
                 font(lerp(big.size, min(38, sw * 0.44), p), "ExtraBold"), WHITE if col != GRAY else GRAY_T, glow=glow)
        a = ease((t - 1.5) / 0.4)
        if a > 0:
            for cx, num, name, c in [(240, v["standard"], "표준", GRAY_T), (575, v["wide"], "넓게 보장", GREEN),
                                     (875, v["caution"], "확인 필요", RED)]:
                text_c(d, (cx, 330), str(num), font(int(84 * a) + 1, "Black"), c)
                text_c(d, (cx, 395), name, font(36, "Bold"), c)
        label_top(d, f"기준: 약관 '{data['criterion']}' 조항")

    def flip_cards(d, t, idx, color, t0, step, back_fn, area, cols):
        slots = grid(len(idx), *area, cols=cols, gap=40)
        for k, i in enumerate(idx):
            x, y, w, h = slots[k]; sx, back = flip(t, t0 + k * step)
            cx = x + w / 2; w2 = w * sx
            if not back:
                card(d, x, y, w, h, color, f"{C[i]}사", font(min(110, w * 0.26), "Black"), sx=sx, radius=18)
            else:
                d.rounded_rectangle([cx - w2 / 2, y, cx + w2 / 2, y + h], radius=18, fill=WHITE, outline=color, width=8)
                if sx > 0.35: back_fn(d, cx, y, w, h, i)

    WIDE_SHOW = GREEN_IDX[:4]
    def s4(d, t):
        label_top(d, f"넓게 보장 {v['wide']}곳", GREEN)
        def back(d, cx, y, w, h, i):
            text_c(d, (cx, y + h * 0.2), f"{C[i]}사", font(44, "Black"), GREEN)
            text_c(d, (cx, y + h * 0.47), data["wide_label"], fit_font(d, data["wide_label"], w - 40, 40), (60, 66, 78))
            text_c(d, (cx, y + h * 0.72), data["wide_value"], fit_font(d, data["wide_value"], w - 40, 78, "Black"), GREEN)
        flip_cards(d, t, WIDE_SHOW, GREEN, 0.6, 0.8, back, (90, 360, 990, 1100), 2 if len(WIDE_SHOW) > 1 else 1)
        if v["wide"] > len(WIDE_SHOW):
            text_c(d, (W / 2, 1125), f"+ {v['wide'] - len(WIDE_SHOW)}곳 더", font(40, "Bold"), GREEN)

    items = [s for s in data["caution_items"] if s.strip()][:3]
    RED_SHOW = RED_IDX[:4]
    def s5(d, t):
        label_top(d, f"확인 필요 {v['caution']}곳", RED)
        shake = 6 * math.sin(t * 40) if 1.2 < t < 2.8 else 0
        def back(d, cx, y, w, h, i):
            text_c(d, (cx, y + h * 0.12), f"{C[i]}사", font(48, "Black"), RED)
            text_c(d, (cx, y + h * 0.3), data["caution_label"], fit_font(d, data["caution_label"], w - 40, 38), (60, 66, 78))
            fs = min(96, (h * 0.5) / max(len(items), 1) * 0.8)
            for k, s in enumerate(items):
                text_c(d, (cx, y + h * 0.42 + (k + 0.5) * h * 0.5 / len(items)), s, fit_font(d, s, w - 40, fs, "Black"), RED)
            if sample: text_c(d, (cx, y + h * 0.95), "(예시)", font(34, "Bold"), MUTED)
        area = (90 + shake, 420, 990 + shake, 1100)
        flip_cards(d, t, RED_SHOW, RED, 2.8, 0.12, back, area, min(2, len(RED_SHOW)))

    lines = data["clause_lines"][:7]
    hl = next((k for k, s in enumerate(lines) if data["clause_highlight"] and data["clause_highlight"] in s), len(lines) - 1)
    def s6(d, t):
        label_top(d, "셀프체크 · 내 약관에서 찾아보기", YELLOW)
        x, y, w, h = 90, 340, 900, 800
        d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=WHITE)
        d.text((x + 60, y + 70), data["clause_title"], font=fit_font(d, data["clause_title"], w - 120, 50, "Black"), fill=INK, anchor="lm")
        hp = ease((t - 0.5) / 1.2)
        for k, line in enumerate(lines):
            ly = y + 70 + (k + 2) * 88
            f = fit_font(d, line, w - 120, 44, "ExtraBold" if k == hl else "Bold")
            if k == hl and hp > 0:
                d.rectangle([x + 60, ly - 30, x + 60 + d.textlength(line, font=f) * hp, ly + 30], fill=YELLOW)
            d.text((x + 60, ly), line, font=f, fill=(200, 50, 20) if k == hl else INK, anchor="lm")

    scenes = [("s1", 2.0, s1), ("s2", 3.0, s2), ("s3", 7.0, s3), ("s4", 8.0, s4), ("s5", 6.0, s5), ("s6", 4.0, s6)]
    F = lambda k: data[k].format(**v)
    captions = [(0.0, 2.0, F("c_hook")), (2.0, 5.0, F("c_pdf")), (5.0, 8.5, F("c_std")), (8.5, 12.0, F("c_wide")),
                (12.0, 20.0, F("c_flip")), (20.0, 22.8, F("c_pause"), "fade"), (22.8, 26.0, F("c_reveal")),
                (26.0, 30.0, F("c_check"))]
    ticks = [{"t": round(2.3 + 0.4 * k, 2), "name": "tick", "vol": 0.4} for k in range(6)]
    flips = [{"t": round(12.6 + 0.8 * k, 2), "name": "pop", "vol": 0.5} for k in range(len(WIDE_SHOW))]
    sfx = ([{"t": 0.0, "name": "impact", "vol": 0.8}, {"t": 2.0, "name": "whoosh", "vol": 0.6}] + ticks +
           [{"t": 5.2, "name": "whoosh", "vol": 0.6}, {"t": 8.5, "name": "pop", "vol": 0.7},
            {"t": 12.0, "name": "whoosh", "vol": 0.5}] + flips +
           [{"t": 20.0, "name": "swoosh_down", "vol": 0.5}, {"t": 21.3, "name": "riser", "vol": 0.6},
            {"t": 22.8, "name": "impact", "vol": 0.8}, {"t": 26.0, "name": "whoosh", "vol": 0.5},
            {"t": 27.7, "name": "ding", "vol": 0.6}])
    note = f"회사 익명 · {data['criterion']} 조항 기준"
    return scenes, captions, sfx, note
