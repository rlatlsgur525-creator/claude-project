#!/usr/bin/env python3
"""약관 전수조사 #1 수술비 — 비트별 모션그래픽 클립 생성 (Pillow 프레임 → ffmpeg).
usage: python make_scenes.py [--preview]     -> scenes/s1.mp4 … s6.mp4
자막·효과음은 넣지 않는다. edit/edl.json에서 build.py가 입힌다.
화면 배치: 그래픽은 y 300~1150, 아래는 main/small 자막 자리, 하단 16%는 비운다.
데이터는 예시다(실제 약관 반영 전).
"""
import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "shorts-kit", "fonts")
OUT = os.path.join(HERE, "scenes")
W, H, FPS = 1080, 1920, 30

BG = (14, 17, 22)
GRAY = (58, 65, 80)
GRAY_T = (170, 178, 192)
GREEN = (47, 191, 113)
RED = (255, 99, 61)
WHITE = (245, 246, 248)
YELLOW = (255, 210, 63)

_fc = {}
def font(size, w="Bold"):
    k = (size, w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(FONTS, f"Pretendard-{w}.otf"), size)
    return _fc[k]

def ease(p):  # easeInOutCubic
    p = max(0.0, min(1.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2

def lerp(a, b, p): return a + (b - a) * p

def text_c(d, xy, s, f, fill):
    d.text(xy, s, font=f, fill=fill, anchor="mm")

# 익명 코드 24개 (A~X). 등급은 예시.
CODES = [chr(65 + i) for i in range(24)]
RED_IDX = [8, 19]
GREEN_IDX = [2, 6, 13, 22]
GRAY_IDX = [i for i in range(24) if i not in RED_IDX + GREEN_IDX]

def grid_pos(i):
    cw, ch, g = 140, 180, 22
    x0 = (W - (6 * cw + 5 * g)) // 2
    c, r = i % 6, i // 6
    return x0 + c * (cw + g), 330 + r * (ch + g), cw, ch

def card(d, x, y, w, h, fill, label=None, lf=None, lc=WHITE, glow=None, sx=1.0):
    """sx: 가로 축척(뒤집기용)."""
    cx = x + w / 2; w2 = max(w * sx, 2)
    x1, x2 = cx - w2 / 2, cx + w2 / 2
    if glow:
        d.rounded_rectangle([x1 - 8, y - 8, x2 + 8, y + h + 8], radius=22, outline=glow, width=6)
    d.rounded_rectangle([x1, y, x2, y + h], radius=16, fill=fill)
    if label and sx > 0.35:
        text_c(d, (cx, y + h / 2), label, lf, lc)

def frames(n):
    for i in range(n):
        yield i, i / FPS

def write(name, dur, draw_fn, preview):
    os.makedirs(OUT, exist_ok=True)
    s = 2 if preview else 1
    path = os.path.join(OUT, name + ".mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W//s}x{H//s}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
           "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, t in frames(int(round(dur * FPS))):
        im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
        draw_fn(d, t)
        if s != 1: im = im.resize((W // s, H // s), Image.BILINEAR)
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    print("wrote", path)

def label_top(d, s, color=GRAY_T):
    text_c(d, (W / 2, 270), s, font(40, "Bold"), color)

# ---- S1 0~2초: 24장, 2장만 빨강 ----
def s1(d, t):
    label_top(d, "보험사 24곳 · 질병수술비 약관")
    pulse = 0.5 + 0.5 * math.sin(t * 9)
    for i in range(24):
        x, y, w, h = grid_pos(i)
        a = ease((t - i * 0.012) / 0.25)
        y = y + (1 - a) * 40
        red = i in RED_IDX
        card(d, x, y, w, h, RED if red else GRAY, CODES[i], font(58, "ExtraBold"),
             WHITE if red else GRAY_T, glow=(255, 160, 130) if red and pulse > 0.4 else None)

# ---- S2 2~5초: 약관 PDF가 쌓임 + 카운터 ----
def s2(d, t):
    label_top(d, "회사별 약관 PDF")
    n = min(24, int(t / 2.4 * 24) + 1)
    for k in range(n):
        drop = ease((t - k * 0.1) / 0.25)
        bx = W / 2 - 170 + ((k * 37) % 23) - 11
        by = 1130 - k * 14 - (1 - drop) * 300
        d.rounded_rectangle([bx, by - 70, bx + 340, by], radius=10, fill=WHITE, outline=(200, 204, 212), width=2)
        d.rectangle([bx + 18, by - 56, bx + 74, by - 30], fill=RED)
        d.text((bx + 46, by - 43), "PDF", font=font(18, "Black"), fill=WHITE, anchor="mm")
        d.text((bx + 92, by - 43), f"{CODES[k]}사 약관", font=font(26, "Bold"), fill=(40, 44, 52), anchor="lm")
    text_c(d, (W / 2, 420), f"{n}", font(190, "Black"), YELLOW)
    text_c(d, (W / 2, 545), "개사 비교", font(52, "ExtraBold"), WHITE)

# ---- S3 5~12초: 18 / 4 / 2 정렬 ----
SW, SH, SG = 86, 110, 12
def group_slot(i):
    if i in GRAY_IDX:
        k = GRAY_IDX.index(i); return 90 + (k % 3) * (SW + SG), 440 + (k // 3) * (SH + SG)
    if i in GREEN_IDX:
        k = GREEN_IDX.index(i); return 480 + (k % 2) * (SW + SG), 440 + (k // 2) * (SH + SG)
    k = RED_IDX.index(i); return 800 + k * (SW + SG), 440

def s3(d, t):
    p = ease((t - 0.2) / 1.4)
    for i in range(24):
        gx, gy, gw, gh = grid_pos(i)
        sx, sy = group_slot(i)
        x, y = lerp(gx, sx, p), lerp(gy, sy, p)
        w, h = lerp(gw, SW, p), lerp(gh, SH, p)
        if i in RED_IDX: col = RED
        elif i in GREEN_IDX: col = tuple(int(lerp(a, b, p)) for a, b in zip(GRAY, GREEN))
        else: col = GRAY
        glow = (150, 240, 190) if (i in GREEN_IDX and t > 3.5 and int(t * 4) % 2 == 0) else None
        card(d, x, y, w, h, col, CODES[i], font(int(lerp(58, 38, p)), "ExtraBold"),
             WHITE if col != GRAY else GRAY_T, glow=glow)
    a = ease((t - 1.5) / 0.4)
    if a > 0:
        for cx, num, name, c in [(237, "18", "표준", GRAY_T), (529, "4", "넓게 보장", GREEN), (849, "2", "확인 필요", RED)]:
            text_c(d, (cx, 330), num, font(int(84 * a) + 1, "Black"), c)
            text_c(d, (cx, 395), name, font(36, "Bold"), c)
    label_top(d, "기준: 약관 '수술의 정의' 조항")

# ---- S4 12~20초: 초록 카드 뒤집기 ----
def flip_sx(t, t0, dur=0.45):
    p = (t - t0) / dur
    if p <= 0: return 1.0, False
    if p >= 1: return 1.0, True
    return abs(math.cos(math.pi * p)), p >= 0.5

def s4(d, t):
    label_top(d, "넓게 보장 4곳", GREEN)
    cw, ch, g = 400, 340, 40
    x0 = (W - (2 * cw + g)) // 2
    for k in range(4):
        x, y = x0 + (k % 2) * (cw + g), 360 + (k // 2) * (ch + g)
        sx, back = flip_sx(t, 0.6 + k * 0.8)
        cx = x + cw / 2; w2 = cw * sx
        if not back:
            card(d, x, y, cw, ch, GREEN, f"{CODES[GREEN_IDX[k]]}사", font(96, "Black"), sx=sx)
        else:
            d.rounded_rectangle([cx - w2 / 2, y, cx + w2 / 2, y + ch], radius=18, fill=WHITE, outline=GREEN, width=8)
            if sx > 0.35:
                text_c(d, (cx, y + 70), f"{CODES[GREEN_IDX[k]]}사", font(44, "Black"), GREEN)
                text_c(d, (cx, y + 160), "수술 제외 항목", font(40, "Bold"), (60, 66, 78))
                text_c(d, (cx, y + 240), "적음", font(78, "Black"), GREEN)

# ---- S5 20~26초: 멈춤 → 빨간 카드 뒤집기 ----
def s5(d, t):
    label_top(d, "확인 필요 2곳", RED)
    cw, ch, g = 400, 620, 40
    x0 = (W - (2 * cw + g)) // 2
    shake = 6 * math.sin(t * 40) if 1.2 < t < 2.8 else 0
    for k in range(2):
        x, y = x0 + k * (cw + g) + shake, 420
        sx, back = flip_sx(t, 2.8 + k * 0.12, 0.5)
        cx = x + cw / 2; w2 = cw * sx
        if not back:
            card(d, x, y, cw, ch, RED, f"{CODES[RED_IDX[k]]}사", font(120, "Black"), sx=sx)
        else:
            d.rounded_rectangle([cx - w2 / 2, y, cx + w2 / 2, y + ch], radius=18, fill=WHITE, outline=RED, width=8)
            if sx > 0.35:
                text_c(d, (cx, y + 80), f"{CODES[RED_IDX[k]]}사", font(48, "Black"), RED)
                text_c(d, (cx, y + 190), "수술로 안 보는 것", font(38, "Bold"), (60, 66, 78))
                text_c(d, (cx, y + 300), "티눈", font(96, "Black"), RED)
                text_c(d, (cx, y + 420), "사마귀", font(96, "Black"), RED)
                text_c(d, (cx, y + 545), "(예시)", font(36, "Bold"), (120, 126, 138))

# ---- S6 26~30초: '수술의 정의' 조항 짚기 ----
CLAUSE = ["제○조 (수술의 정의)", "", "① '수술'이란 의사가 치료를 직접",
          "목적으로 필요하다고 인정하여", "기구를 사용해 생체에 절단·절제 등의", "조작을 가하는 것을 말합니다.",
          "② 다음은 수술로 보지 않습니다.", "티눈·사마귀 제거 등 (예시 문구)"]
def s6(d, t):
    label_top(d, "셀프체크 · 내 약관에서 찾아보기", YELLOW)
    x, y, w, h = 90, 340, 900, 800
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=WHITE)
    hp = ease((t - 0.5) / 1.2)
    for k, line in enumerate(CLAUSE):
        ly = y + 70 + k * 88
        if k == 7 and hp > 0:
            tw = d.textlength(line, font=font(44, "ExtraBold"))
            d.rectangle([x + 60, ly - 30, x + 60 + tw * hp, ly + 30], fill=YELLOW)
        f = font(50, "Black") if k == 0 else font(44, "ExtraBold" if k >= 6 else "Bold")
        d.text((x + 60, ly), line, font=f, fill=(30, 34, 42) if k != 7 else (200, 50, 20), anchor="lm")

SCENES = [("s1", 2.0, s1), ("s2", 3.0, s2), ("s3", 7.0, s3), ("s4", 8.0, s4), ("s5", 6.0, s5), ("s6", 4.0, s6)]

if __name__ == "__main__":
    preview = "--preview" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    for name, dur, fn in SCENES:
        if not only or name in only: write(name, dur, fn, preview)
