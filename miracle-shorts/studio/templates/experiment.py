"""비교 실험 — 같은 돈을 N가지 방법에 넣었을 때 결과를 계산해 비교. 30초, 그래픽만으로 제작.
구조: hunter/results/format_blueprints_1024.md 의 E 설계도 (고양이모래 3종 장면 분석).
셋업(전부 한 화면) → 동시 시작 → 결과 막대 → 1등을 먼저·가장 길게 → 나머지 짧게 → 상황별 기준(추천 아님).
숫자는 코드로 계산한다: 원금 × (1 + 연 r)^년, 세전·수수료 미반영.
"""
from gfx import *

NAME = "비교 실험"
DESC = "같은 돈을 2~4가지 방법에 넣으면? 계산으로 비교하고 상황별 기준을 정리. 30초."

FIELDS = [
    {"section": "조건"},
    {"key": "principal", "label": "원금 (원)", "type": "number", "default": 1000000, "min": 10000},
    {"key": "years", "label": "기간 (년)", "type": "number", "default": 10, "min": 1, "max": 40},
    {"key": "options", "label": "방법 (줄마다 '이름|연 %|한 줄 특징', 2~4개)", "type": "lines", "default": [
        "파킹통장|2|언제든 꺼내 쓸 수 있음", "정기예금|3|만기까지 묶이지만 원금 보장",
        "S&P500 ETF|7|원금 손실 가능 · 오래 둘 때"]},
    {"key": "rules", "label": "상황별 기준 (줄마다 하나, 최대 3개)", "type": "lines", "default": [
        "1년 안에 쓸 돈 → 꺼내기 쉬운 곳", "만기까지 안 쓸 돈 → 확정 이자", "10년 넘게 둘 돈 → 변동을 견딜 수 있을 때만"]},
    {"section": "자막 ([단어] = 노란 강조, / = 줄바꿈)"},
    {"key": "c_hook", "label": "0~3초 훅", "type": "text", "default": "같은 [{principal}],/{years}년 뒤 얼마 될까?"},
    {"key": "c_start", "label": "3~5초 동시 시작", "type": "text", "default": "같은 조건으로/[동시에] 계산했어요"},
    {"key": "c_grow", "label": "5~10초 결과 막대", "type": "text", "default": "{years}년 동안 굴려 보면"},
    {"key": "c_win", "label": "10~16초 1등", "type": "text", "default": "1위 [{w_name}]/{w_amount}"},
    {"key": "c_rest", "label": "16~23초 나머지", "type": "text", "default": "대신 [특징]이 다 달라요"},
    {"key": "c_rule", "label": "23~30초 기준", "type": "text", "default": "정답은 상품이 아니라/[언제 쓸 돈]인지예요"},
]

def parse(data):
    out = []
    for s in data["options"]:
        if not s.strip(): continue
        p = [x.strip() for x in s.split("|")] + ["", "", ""]
        try: r = float(p[1])
        except ValueError: r = None
        out.append({"name": p[0], "rate": r, "note": p[2]})
    return out

def won(n):
    return f"{n / 10000:,.1f}만 원".replace(".0만", "만") if n >= 10000 else f"{n:,.0f}원"

def validate(data):
    ops = parse(data); errs = []
    if not 2 <= len(ops) <= 4: errs.append("방법은 2~4개 넣어 주세요.")
    for o in ops:
        if o["rate"] is None: errs.append(f"'{o['name']}'의 연 % 를 숫자로 적어 주세요 (예: 파킹통장|2|특징).")
    return errs

def build(data):
    P = float(data["principal"]); Y = int(data["years"]); ops = parse(data)
    for o in ops: o["final"] = round(P * (1 + o["rate"] / 100) ** Y)
    rank = sorted(ops, key=lambda o: -o["final"]); win = rank[0]; mx = win["final"]
    COL = [BLUE, YELLOW, GREEN, (200, 120, 255)]
    for k, o in enumerate(ops): o["col"] = COL[k]
    slots = grid(len(ops), 90, 420, 990, 1010, cols=len(ops), gap=30)  # 아래 1030~1130은 특징 상자 자리

    def bars(d, t, grow, focus=None):
        for k, o in enumerate(ops):
            x, y, w, h = slots[k]
            val = P * (1 + o["rate"] / 100) ** (Y * grow)
            bh = (h - 170) * (val / mx)
            dim = focus is not None and o is not focus
            col = tuple(int(c * 0.35) for c in o["col"]) if dim else o["col"]
            d.rounded_rectangle([x + 10, y + h - 90 - bh, x + w - 10, y + h - 90], radius=12, fill=col)
            text_c(d, (x + w / 2, y + h - 45), o["name"], fit_font(d, o["name"], w, 36), GRAY_T if dim else WHITE)
            text_c(d, (x + w / 2, y + h - 120 - bh), won(val), fit_font(d, won(val), w + 20, 40, "Black"), GRAY_T if dim else WHITE)

    def e1(d, t):
        label_top(d, f"같은 {won(P)} · {Y}년 · 연 수익률 가정")
        for k, o in enumerate(ops):
            x, y, w, h = slots[k]; a = ease((t - k * 0.15) / 0.3)
            card(d, x, y + (1 - a) * 50, w, h - 40, (28, 32, 40))
            text_c(d, (x + w / 2, y + 120), o["name"], fit_font(d, o["name"], w - 30, 46, "Black"), o["col"])
            text_c(d, (x + w / 2, y + 220), f"연 {o['rate']:g}%", font(44, "ExtraBold"), WHITE)
            text_c(d, (x + w / 2, y + 420), "?", font(160, "Black"), GRAY_T)

    def e2(d, t):
        label_top(d, f"같은 {won(P)} · {Y}년 · 연 수익률 가정")
        bars(d, t, 0)
        text_c(d, (540, 360), "START", font(int(lerp(140, 90, ease(t / 0.4))), "Black"), YELLOW)

    def e3(d, t):
        p = ease(t / 4.0)
        label_top(d, f"{int(round(Y * p))}년 뒤")
        bars(d, t, p)

    def e4(d, t):
        label_top(d, "가장 큰 금액", win["col"])
        bars(d, t, 1, focus=win)
        a = ease(t / 0.4)
        text_c(d, (540, 360), f"+{won(win['final'] - P)}", font(int(70 * a) + 1, "Black"), win["col"])
        d.rounded_rectangle([110, 1150 - 120, 970, 1150 - 20], radius=16, fill=(28, 32, 40))
        text_c(d, (540, 1080), win["note"], fit_font(d, win["note"], 820, 40, "ExtraBold"), WHITE)

    rest = rank[1:]
    def e5(d, t):
        step = 7.0 / max(len(rest), 1); k = min(int(t / step), len(rest) - 1); o = rest[k]
        label_top(d, o["name"], o["col"])
        bars(d, t, 1, focus=o)
        d.rounded_rectangle([110, 1030, 970, 1130], radius=16, fill=(28, 32, 40))
        text_c(d, (540, 1080), o["note"], fit_font(d, o["note"], 820, 40, "ExtraBold"), WHITE)

    rules = [s for s in data["rules"] if s.strip()][:3]
    def e6(d, t):
        label_top(d, "상황별 기준", YELLOW)
        for k, s in enumerate(rules):
            a = ease((t - 0.3 - k * 0.9) / 0.3)
            if a <= 0: continue
            y = 440 + k * 210; x = 90 + (1 - a) * 60
            d.rounded_rectangle([x, y, x + 900, y + 170], radius=18, fill=(28, 32, 40), outline=YELLOW, width=4)
            lines = wrap(d, s, font(42, "ExtraBold"), 820)[:2]
            for j, ln in enumerate(lines):
                text_c(d, (x + 450, y + 85 + (j - (len(lines) - 1) / 2) * 52), ln, font(42, "ExtraBold"), WHITE)

    scenes = [("e1", 3.0, e1), ("e2", 2.0, e2), ("e3", 5.0, e3), ("e4", 6.0, e4), ("e5", 7.0, e5), ("e6", 7.0, e6)]
    v = dict(principal=won(P), years=Y, w_name=win["name"], w_amount=won(win["final"]))
    F = lambda k: data[k].format(**v)
    captions = [(0.0, 3.0, F("c_hook")), (3.0, 5.0, F("c_start")), (5.0, 10.0, F("c_grow")), (10.0, 16.0, F("c_win")),
                (16.0, 23.0, F("c_rest")), (23.0, 30.0, F("c_rule"))]
    sfx = ([{"t": 0.0, "name": "impact", "vol": 0.8}, {"t": 3.0, "name": "pop", "vol": 0.7}, {"t": 5.0, "name": "riser", "vol": 0.4}] +
           [{"t": round(5.4 + 0.8 * k, 2), "name": "tick", "vol": 0.35} for k in range(5)] +
           [{"t": 10.0, "name": "cash", "vol": 0.7}, {"t": 16.0, "name": "whoosh", "vol": 0.5}] +
           [{"t": round(16 + 7.0 / max(len(rest), 1) * k, 2), "name": "pop", "vol": 0.5} for k in range(1, len(rest))] +
           [{"t": 23.0, "name": "whoosh", "vol": 0.5}] +
           [{"t": round(23.3 + 0.9 * k, 2), "name": "pop", "vol": 0.5} for k in range(len(rules))] +
           [{"t": 28.5, "name": "ding", "vol": 0.6}])
    rates = "·".join(f"{o['rate']:g}" for o in ops)
    note = f"연 {rates}% 가정 · 연복리 · 세전 · 수수료 미반영"
    return scenes, captions, sfx, note
