"""맛집 리뷰 카드뉴스 렌더러.

post.json(사진별 문구·위치·장식)을 읽어 손글씨 자막이 들어간 카드 이미지를 만든다.

    python render.py posts/<게시물>            # 카드 이미지만
    python render.py posts/<게시물> --reel     # 카드 + 릴스(mp4)

좌표 x, y 는 모두 0~1 비율(왼쪽 위가 0,0). 텍스트는 글 덩어리의 '가운데'가 그 점에 온다.
문구 안의 [대괄호] 부분은 강조색(hl)으로 칠한다.
"""
import argparse
import json
import math
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parent / "fonts"
W, H = 1080, 1350          # 인스타 피드 4:5
SS = 2                     # 2배로 그린 뒤 줄여서 선을 부드럽게
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")

FONTS = {
    "hand": "Gaegu-Bold.ttf",            # 둥근 손글씨 (기본)
    "pen": "NanumPenScript-Regular.ttf", # 얇은 펜 손글씨
    "brush": "NanumBrushScript-Regular.ttf",
    "bold": "BlackHanSans-Regular.ttf",  # 표지용 굵은 제목
    "round": "Jua-Regular.ttf",
    "dohyeon": "DoHyeon-Regular.ttf",
    # 정보형 맛집 계정(taste.jeonju) 표지용 고딕
    "title": "Pretendard-Black.otf",     # 표지 큰 제목
    "title2": "Pretendard-ExtraBold.otf",
    "sub": "Pretendard-SemiBold.otf",    # 제목 위 작은 한 줄
    # 포인트용
    "bagel": "BagelFatOne-Regular.ttf",  # 통통한 팝 글씨
    "gasoek": "GasoekOne-Regular.ttf",   # 아주 굵은 레트로 간판체
    "gugi": "Gugi-Regular.ttf",
    "sunflower": "Sunflower-Bold.ttf",
    "dongle": "Dongle-Bold.ttf",
    "gowun": "GowunDodum-Regular.ttf",
    "stylish": "Stylish-Regular.ttf",
    "bwpicture": "BlackAndWhitePicture-Regular.ttf",
    # 손글씨 더
    "dokdo": "Dokdo-Regular.ttf",        # 거친 마커
    "eastsea": "EastSeaDokdo-Regular.ttf",
    "singleday": "SingleDay-Regular.ttf",
    "cute": "CuteFont-Regular.ttf",
    "poorstory": "PoorStory-Regular.ttf",
    "kirang": "KirangHaerang-Regular.ttf",
    "gamja": "GamjaFlower-Regular.ttf",
    "himelody": "HiMelody-Regular.ttf",
    "yeonsung": "YeonSung-Regular.ttf",
}
_fc = {}


def font(key, size):
    k = (key, size)
    if k not in _fc:
        path = FONT_DIR / FONTS.get(key, key)
        if not path.exists():
            sys.exit(f"폰트 없음: {path}")
        _fc[k] = ImageFont.truetype(str(path), size)
    return _fc[k]


def rgba(c, a=255):
    c = c.lstrip("#")
    if len(c) == 8:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4, 6))
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def jitter(seed):
    return random.Random(seed)


# ---------------------------------------------------------------- base photo

def base_image(slide, post_dir):
    img = Image.open(post_dir / slide["image"])
    img = ImageOps.exif_transpose(img).convert("RGB")
    fx, fy = slide.get("focus", [0.5, 0.5])
    top = slide.get("top_image")     # 표지 콜라주: 위쪽에 가게 입구, 아래쪽에 시그니처 메뉴
    split = float(slide.get("split", 0.42))            # 위 사진이 차지하는 비율
    feather = float(slide.get("feather", 0.1))         # 두 사진이 섞이는 폭
    if top:   # 메뉴 사진은 아래쪽(겹치는 폭 포함)에만 맞춰 넣어 음식이 위 사진에 가리지 않게
        bh = int(H * SS * (1 - split + feather))
        menu = ImageOps.fit(img, (W * SS, bh), Image.LANCZOS, centering=(fx, fy))
        img = Image.new("RGB", (W * SS, H * SS))
        img.paste(menu, (0, H * SS - bh))
    else:
        img = ImageOps.fit(img, (W * SS, H * SS), Image.LANCZOS, centering=(fx, fy))
    if top:
        th = int(H * SS * (split + feather))
        timg = ImageOps.exif_transpose(Image.open(post_dir / top)).convert("RGB")
        if slide.get("top_crop"):                       # [x0, y0, x1, y1] 비율로 잘라 쓰기 (글자 든 부분 빼기 등)
            cx0, cy0, cx1, cy1 = slide["top_crop"]
            timg = timg.crop((int(cx0 * timg.width), int(cy0 * timg.height), int(cx1 * timg.width), int(cy1 * timg.height)))
        tfx, tfy = slide.get("top_focus", [0.5, 0.5])
        timg = ImageOps.fit(timg, (W * SS, th), Image.LANCZOS, centering=(tfx, tfy))
        if slide.get("top_dim"):
            timg = Image.blend(timg, Image.new("RGB", timg.size, (0, 0, 0)), float(slide["top_dim"]))
        m = Image.new("L", (1, th))
        f0, f1 = (split - feather) * H * SS, th
        for y in range(th):
            m.putpixel((0, y), 255 if y < f0 else int(255 * (1 - (y - f0) / max(1, f1 - f0)) ** 1.3))
        img.paste(timg, (0, 0), m.resize(timg.size))
    shade = slide.get("shade")      # 글자 읽히게 위/아래를 살짝 어둡게
    if shade:
        amount = int(slide.get("shade_amount", 170))     # 가장 어두운 끝의 진하기 (0~255)
        start = float(slide.get("shade_start", 0.45))    # 어두워지기 시작하는 위치
        g = Image.new("L", (1, H * SS))
        for y in range(H * SS):
            t = y / (H * SS)
            t = 1 - t if shade == "top" else t
            g.putpixel((0, y), int(amount * max(0, (t - start) / (1 - start)) ** 1.4))
        img = Image.composite(Image.new("RGB", img.size, (0, 0, 0)), img, g.resize(img.size))
    if slide.get("dim"):
        img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), float(slide["dim"]))
    return img.convert("RGBA")


# ---------------------------------------------------------------- hand-drawn bits

def rough_poly(box, seed, wobble=0.06, n=10):
    """붓으로 칠한 듯 가장자리가 들쭉날쭉한 사각형."""
    x0, y0, x1, y1 = box
    r = jitter(seed)
    h = y1 - y0
    pts = []
    for i in range(n + 1):
        pts.append((x0 + (x1 - x0) * i / n, y0 + r.uniform(-wobble, wobble) * h * 2))
    pts.append((x1 + r.uniform(0, 0.15) * h, (y0 + y1) / 2))
    for i in range(n, -1, -1):
        pts.append((x0 + (x1 - x0) * i / n, y1 + r.uniform(-wobble, wobble) * h * 2))
    pts.append((x0 - r.uniform(0, 0.15) * h, (y0 + y1) / 2))
    return pts


def rough_blob(box, seed):
    """말풍선처럼 테두리가 거친 둥근 덩어리."""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    r = jitter(seed)
    pts = []
    for i in range(72):
        a = 2 * math.pi * i / 72
        k = 1 + r.uniform(-0.04, 0.06)
        # 모서리를 살짝 각지게 (superellipse)
        c, s = math.cos(a), math.sin(a)
        e = 0.6
        pts.append((cx + rx * k * math.copysign(abs(c) ** e, c), cy + ry * k * math.copysign(abs(s) ** e, s)))
    return pts


def heart(d, cx, cy, s, color, width=None):
    pts = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * s / 32, cy + y * s / 32))
    if width:
        d.line(pts + [pts[0]], fill=color, width=width, joint="curve")
    else:
        d.polygon(pts, fill=color)


def sparkle(d, cx, cy, size, direction, color, width):
    """글자 옆의 '빛나는' 짧은 선 3개. direction 은 선들이 향하는 각도(도)."""
    for off in (-40, 0, 40):
        a = math.radians(direction + off)
        r0, r1 = size * 0.35, size * (1.0 if off == 0 else 0.8)
        d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                (cx + math.cos(a) * r1, cy + math.sin(a) * r1)], fill=color, width=width)


def wavy(d, x0, x1, y, amp, color, width, seed):
    r = jitter(seed)
    pts = []
    n = 24
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        pts.append((x, y + math.sin(i / n * math.pi * 1.2) * amp * 0.3 + r.uniform(-1, 1) * amp * 0.08 - (i / n) * amp * 0.6))
    d.line(pts, fill=color, width=width, joint="curve")


# ---------------------------------------------------------------- text block

def parse_line(line):
    """'전주 [갈비찜] 맛집' -> [('전주 ', False), ('갈비찜', True), (' 맛집', False)]"""
    out = []
    for part in re.split(r"(\[[^\]]*\])", line):
        if part.startswith("[") and part.endswith("]"):
            out.append((part[1:-1], True))
        elif part:
            out.append((part, False))
    return out


def text_layer(el, seed):
    s = SS
    size = int(el.get("size", 72) * s)
    f = font(el.get("font", "hand"), size)
    color = rgba(el.get("color", "#FFFFFF"))
    hl = rgba(el.get("hl", "#FFE14D"))
    align = el.get("align", "center")
    lh = int(size * el.get("line_gap", 1.18))
    stroke = int(el.get("stroke", 0) * s)
    stroke_c = rgba(el.get("stroke_color", "#000000"))
    text = EMOJI.sub("", str(el["text"])).replace("\\n", "\n")
    lines = [parse_line(l) for l in text.split("\n")]
    widths = [sum(f.getlength(t) for t, _ in ln) for ln in lines]
    bw = int(max(widths or [1])) + stroke * 2
    heart_w = int(size * 0.75) if el.get("heart") else 0
    pad = int(size * 0.9)
    lw, lhh = bw + heart_w + pad * 2, lh * len(lines) + pad * 2
    layer = Image.new("RGBA", (lw, lhh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tx0, ty0 = pad, pad

    # 배경 (붓띠 / 말풍선 / 테이프 / 상자)
    bg = el.get("bg")
    if bg:
        bgc = rgba(el.get("bg_color", {"band": "#E02424", "bubble": "#111111", "tape": "#F6C99A",
                                       "box": "#000000"}[bg]),
                   int(255 * el.get("bg_opacity", {"box": 0.55}.get(bg, 1.0))))
        m = size * 0.28
        box = (tx0 - m * 1.4, ty0 - m * 0.7, tx0 + bw + heart_w + m * 1.4, ty0 + lh * len(lines) + m * 0.2)
        if bg == "band":
            d.polygon(rough_poly(box, seed), fill=bgc)
        elif bg == "tape":
            d.polygon(rough_poly(box, seed, wobble=0.03), fill=bgc)
        elif bg == "bubble":
            bb = (box[0] - m, box[1] - m * 0.8, box[2] + m, box[3] + m * 0.8)
            d.polygon(rough_blob(bb, seed), fill=bgc)
            if el.get("bg_outline", True):   # 바깥에 빨간 거친 테두리
                ring = rough_blob((bb[0] - m * .4, bb[1] - m * .4, bb[2] + m * .4, bb[3] + m * .4), seed + 1)
                d.line(ring + [ring[0]], fill=rgba(el.get("bg_outline_color", "#E02424")),
                       width=int(size * 0.09))
        elif bg == "box":
            d.rounded_rectangle(box, radius=int(size * 0.35), fill=bgc)

    # 그림자 (사진 위에서 읽히게). shadow: "strong" 은 정보형 표지처럼 짙고 넓게 번진 그림자
    shadow = el.get("shadow", True)
    if shadow and not stroke:
        strong = shadow == "strong"
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        y = ty0
        for ln, w in zip(lines, widths):
            x = tx0 + {"left": 0, "center": (bw - w) / 2, "right": bw - w}[align]
            for t, _ in ln:
                sd.text((x, y + size * (0.05 if strong else 0.04)), t, font=f, fill=(0, 0, 0, 235 if strong else 200),
                        stroke_width=int(size * 0.03) if strong else 0, stroke_fill=(0, 0, 0, 235))
                x += f.getlength(t)
            y += lh
        sh = sh.filter(ImageFilter.GaussianBlur(size * (0.11 if strong else 0.07)))
        if strong:   # 두 번 겹쳐 더 진하게
            sh = Image.alpha_composite(sh, sh)
        layer = Image.alpha_composite(sh, layer) if not bg else Image.alpha_composite(layer, sh)
        d = ImageDraw.Draw(layer)

    # 글자. hl_grad 가 있으면 강조 단어를 위→아래 그라데이션으로 칠한다
    grad = el.get("hl_grad")
    hmask = Image.new("L", layer.size, 0) if grad else None
    hd = ImageDraw.Draw(hmask) if grad else None
    y = ty0
    last_x_end = tx0
    # stroke2: 검정 테두리 바깥에 한 겹 더 (썸네일용 이중 테두리)
    stroke2 = int(el.get("stroke2", 0) * s)
    if stroke2:
        s2c = rgba(el.get("stroke2_color", "#FFFFFF"))
        yy = ty0
        for ln, w in zip(lines, widths):
            x = tx0 + {"left": 0, "center": (bw - w) / 2, "right": bw - w}[align]
            for t, _ in ln:
                d.text((x, yy), t, font=f, fill=s2c, stroke_width=stroke + stroke2, stroke_fill=s2c)
                x += f.getlength(t)
            yy += lh
    for ln, w in zip(lines, widths):
        x = tx0 + {"left": 0, "center": (bw - w) / 2, "right": bw - w}[align]
        for t, is_hl in ln:
            d.text((x, y), t, font=f, fill=hl if is_hl else color,
                   stroke_width=stroke, stroke_fill=stroke_c)
            if is_hl and grad:
                hd.text((x, y), t, font=f, fill=255)
            x += f.getlength(t)
        last_x_end = x
        y += lh
    if grad:
        c0, c1 = rgba(grad[0]), rgba(grad[1])
        col = Image.new("RGBA", (1, layer.height))
        asc = f.getbbox("가")
        for yy in range(layer.height):
            k = ((yy - ty0) % lh - asc[1]) / max(1, asc[3] - asc[1])
            k = min(1, max(0, k))
            col.putpixel((0, yy), tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(4)))
        gimg = col.resize(layer.size)
        gimg.putalpha(hmask)
        layer = Image.alpha_composite(layer, gimg)
        d = ImageDraw.Draw(layer)

    deco_c = rgba(el.get("deco_color", el.get("color", "#FFFFFF")))
    lw_line = max(3, int(size * 0.07))
    if el.get("heart"):
        hc = rgba(el.get("heart_color", el.get("hl", "#FFE14D")))
        heart(d, last_x_end + heart_w * 0.55, y - lh + size * 0.55, size * 0.62, hc,
              None if el.get("heart_fill") else max(3, int(size * 0.07)))
    if el.get("underline"):
        uy = y - lh + size * 1.12
        wavy(d, tx0 - size * 0.1, tx0 + bw + heart_w * 0.5, uy, size * 0.25, hl, lw_line, seed)
    sp = el.get("sparkle")
    if sp:
        mid_y = ty0 + lh * len(lines) / 2 - size * 0.1
        if sp in ("left", "both"):
            sparkle(d, tx0 - size * 0.25, mid_y, size * 0.75, 180, deco_c, lw_line)
        if sp in ("right", "both"):
            sparkle(d, tx0 + bw + heart_w + size * 0.25, mid_y, size * 0.75, 0, deco_c, lw_line)
    return layer


def paste_center(canvas, layer, x, y, rotate=0):
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    cx, cy = int(x * W * SS), int(y * H * SS)
    canvas.alpha_composite(layer, (cx - layer.width // 2, cy - layer.height // 2))


# ---------------------------------------------------------------- other elements

def draw_arrow(canvas, el, seed):
    s = SS
    (fx, fy), (tx, ty) = el["from"], el["to"]
    p0 = (fx * W * s, fy * H * s)
    p2 = (tx * W * s, ty * H * s)
    dx, dy = p2[0] - p0[0], p2[1] - p0[1]
    ln = math.hypot(dx, dy) or 1
    bend = el.get("bend", 0.3)
    c = ((p0[0] + p2[0]) / 2 - dy / ln * ln * bend, (p0[1] + p2[1]) / 2 + dx / ln * ln * bend)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p2[1]))
    if el.get("loop"):  # 중간에 작은 고리 (손으로 그린 느낌)
        k = 18
        cx, cy = pts[k]
        r = ln * 0.07
        ang = math.atan2(pts[k + 1][1] - pts[k - 1][1], pts[k + 1][0] - pts[k - 1][0])
        loop = [(cx + r * math.cos(ang - math.pi / 2 + a) - r * math.cos(ang - math.pi / 2),
                 cy + r * math.sin(ang - math.pi / 2 + a) - r * math.sin(ang - math.pi / 2))
                for a in [i / 20 * 2 * math.pi for i in range(21)]]
        pts = pts[:k] + loop + pts[k:]
    width = int(el.get("width", 6) * s)
    color = rgba(el.get("color", "#FFFFFF"))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    end = pts[-1]
    prev = pts[-4]
    a = math.atan2(end[1] - prev[1], end[0] - prev[0])
    head = width * 4.5
    wings = [(end[0] - head * math.cos(a - 0.55), end[1] - head * math.sin(a - 0.55)),
             (end[0] - head * math.cos(a + 0.55), end[1] - head * math.sin(a + 0.55))]
    sh =Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for dd, col in ((sd, (0, 0, 0, 170)), (d, color)):
        dd.line(pts, fill=col, width=width, joint="curve")
        for wpt in wings:
            dd.line([wpt, end], fill=col, width=width)
        r = width / 2
        for pt in (pts[0], end, *wings):
            dd.ellipse((pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r), fill=col)
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(width * 0.8)))
    canvas.alpha_composite(layer)


def draw_pin(canvas, el):
    s = SS
    size = el.get("size", 70) * s
    cx, cy = el["x"] * W * s, el["y"] * H * s
    color = rgba(el.get("color", "#E53935"))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = size * 0.38
    top = cy - size * 0.5
    d.ellipse((cx - r, top, cx + r, top + 2 * r), fill=color)
    d.polygon([(cx - r * 0.86, top + r * 1.5), (cx + r * 0.86, top + r * 1.5), (cx, cy + size * 0.5)], fill=color)
    ir = r * 0.42
    d.ellipse((cx - ir, top + r - ir, cx + ir, top + r + ir), fill=rgba(el.get("inner", "#FFFFFF")))
    sh = layer.split()[3].filter(ImageFilter.GaussianBlur(size * 0.06))
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", canvas.size, 0)] * 3 + [sh.point(lambda v: v * 0.6)]))
    canvas.alpha_composite(layer)


def draw_heart(canvas, el):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    heart(ImageDraw.Draw(layer), el["x"] * W * SS, el["y"] * H * SS, el.get("size", 60) * SS,
          rgba(el.get("color", "#E53935")), None if el.get("fill", True) else int(5 * SS))
    if el.get("rotate"):
        layer = layer.rotate(el["rotate"], center=(el["x"] * W * SS, el["y"] * H * SS), resample=Image.BICUBIC)
    canvas.alpha_composite(layer)


def draw_dust(canvas, el, seed):
    """표지 어두운 부분에 흩뿌린 반짝이 가루 (작은 빛점 + 가끔 십자별)."""
    r = jitter(seed)
    y0, y1 = el.get("from", 0.5), el.get("to", 1.0)
    n = int(el.get("count", 60))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x = r.uniform(0, W * SS)
        y = r.uniform(y0, y1) * H * SS
        s = r.uniform(1.2, 4.5) * SS
        a = int(r.uniform(90, 230))
        d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, a))
        if r.random() < 0.12:   # 십자별
            L = s * r.uniform(4, 7)
            d.line([(x - L, y), (x + L, y)], fill=(255, 255, 255, a), width=max(1, int(s * 0.5)))
            d.line([(x, y - L), (x, y + L)], fill=(255, 255, 255, a), width=max(1, int(s * 0.5)))
    glow = layer.filter(ImageFilter.GaussianBlur(3 * SS))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(layer)


def draw_burst(canvas, el, seed):
    """만화 집중선: 가운데를 비워 두고 바깥에서 안쪽으로 뻗는 흰 선."""
    r = jitter(seed)
    cx, cy = el.get("x", 0.5) * W * SS, el.get("y", 0.5) * H * SS
    inner = el.get("inner", 0.42) * W * SS
    outer = math.hypot(W, H) * SS
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = rgba(el.get("color", "#FFFFFF"))
    for i in range(int(el.get("count", 110))):
        a = 2 * math.pi * i / el.get("count", 110) + r.uniform(-0.02, 0.02)
        r0 = inner * r.uniform(1.0, 1.5)
        wdt = r.uniform(0.002, 0.009)
        p0 = (cx + math.cos(a) * r0, cy + math.sin(a) * r0)
        p1 = (cx + math.cos(a - wdt) * outer, cy + math.sin(a - wdt) * outer)
        p2 = (cx + math.cos(a + wdt) * outer, cy + math.sin(a + wdt) * outer)
        d.polygon([p0, p1, p2], fill=col[:3] + (int(col[3] * r.uniform(0.35, 0.9)),))
    canvas.alpha_composite(layer)


def flame_poly(cx, by, w, h, r, tongues=5, lean=0.0):
    """아래가 둥글고 위로 혀가 여러 갈래 솟는 불꽃 외곽선."""
    pts = []
    for i in range(tongues):
        x0 = cx - w / 2 + w * i / tongues
        x1 = cx - w / 2 + w * (i + 1) / tongues
        mid = 1 - abs((i + 0.5) / tongues - 0.5) * 1.4          # 가운데 혀가 가장 높다
        th = h * mid * r.uniform(0.75, 1.0)
        pts.append((x0, by - th * 0.35))
        pts.append(((x0 + x1) / 2 + w * lean * 0.15 + r.uniform(-1, 1) * w * 0.03, by - th))
    pts.append((cx + w / 2, by - h * 0.15))
    for i in range(13):                                          # 아래쪽 둥근 바닥
        a = math.pi * i / 12
        pts.append((cx + math.cos(a) * w / 2, by - h * 0.15 + math.sin(a) * h * 0.22))
    return pts


def draw_flame(canvas, el, seed):
    r = jitter(seed)
    size = el.get("size", 160) * SS
    cx, by = el["x"] * W * SS, el["y"] * H * SS
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = size * el.get("width", 0.9), size
    n = int(el.get("tongues", 5))
    outer = flame_poly(cx, by, w, h, r, n, el.get("lean", 0))
    d.line(outer + [outer[0]], fill=rgba(el.get("outline", "#111111")), width=int(size * 0.06), joint="curve")
    d.polygon(outer, fill=rgba(el.get("color", "#E8221B")))
    inner = flame_poly(cx, by, w * 0.6, h * 0.62, jitter(seed + 7), max(3, n - 2), el.get("lean", 0))
    d.polygon(inner, fill=rgba(el.get("inner", "#FF8A1C")))
    if el.get("rotate"):
        layer = layer.rotate(el["rotate"], center=(cx, by - h / 2), resample=Image.BICUBIC)
    canvas.alpha_composite(layer)


def draw_sparkle(canvas, el):
    d = ImageDraw.Draw(canvas)
    sparkle(d, el["x"] * W * SS, el["y"] * H * SS, el.get("size", 60) * SS, el.get("dir", -45),
            rgba(el.get("color", "#FFFFFF")), int(el.get("width", 5) * SS))


# ---------------------------------------------------------------- slides

def render_slide(slide, post_dir, idx):
    canvas = base_image(slide, post_dir)
    for j, el in enumerate(slide.get("elements", [])):
        seed = idx * 100 + j
        t = el.get("type", "text")
        if t == "text":
            paste_center(canvas, text_layer(el, seed), el.get("x", 0.5), el.get("y", 0.5), el.get("rotate", 0))
        elif t == "arrow":
            draw_arrow(canvas, el, seed)
        elif t == "pin":
            draw_pin(canvas, el)
        elif t == "heart":
            draw_heart(canvas, el)
        elif t == "sparkle":
            draw_sparkle(canvas, el)
        elif t == "dust":
            draw_dust(canvas, el, seed)
        elif t == "burst":
            draw_burst(canvas, el, seed)
        elif t == "flame":
            draw_flame(canvas, el, seed)
    return canvas.resize((W, H), Image.LANCZOS).convert("RGB")


def info_slide(post, post_dir):
    """마지막 정보 카드: 마지막 사진을 흐리게 깔고 가게 정보를 손글씨로."""
    st = post["store"]
    src = post.get("info_bg") or all_slides(post)[-1]["image"]
    img = Image.open(post_dir / src)
    img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (W * SS, H * SS), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(28 * SS))
    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.55).convert("RGBA")
    rows = [("주소", st.get("address")), ("영업시간", st.get("hours")), ("휴무", st.get("closed")),
            ("전화", st.get("phone")), ("주차", st.get("parking"))]
    rows = [(k, v) for k, v in rows if v]
    els = [{"type": "pin", "x": 0.5, "y": 0.2, "size": 90},
           {"text": st["name"], "size": 110, "x": 0.5, "y": 0.31, "underline": True},
           {"text": st.get("area", ""), "size": 54, "x": 0.5, "y": 0.4, "color": "#FFE14D"}]
    y = 0.5
    for k, v in rows:
        els.append({"text": f"[{k}]  {v}", "font": "pen", "size": 58, "x": 0.5, "y": y})
        y += 0.075
    if post.get("save_cta", True):
        els.append({"text": "저장해두고 꼭 가보세요!", "size": 60, "x": 0.5, "y": min(0.9, y + 0.05),
                    "sparkle": "both", "heart": True, "heart_color": "#FF5A5F", "heart_fill": True})
    for j, el in enumerate(els):
        if el.get("type") == "pin":
            draw_pin(img, el)
        else:
            paste_center(img, text_layer(el, 900 + j), el["x"], el["y"])
    return img.resize((W, H), Image.LANCZOS).convert("RGB")


def caption_text(post):
    cap = post.get("caption", "").strip()
    tags = post.get("hashtags", [])
    if tags:
        cap += "\n\n" + " ".join(t if t.startswith("#") else "#" + t for t in tags)
    return cap


def all_slides(post):
    """표지 후보(covers)가 있으면 고른 표지(cover, 없으면 첫 후보)를 맨 앞에 붙인 전체 장 목록."""
    covers = post.get("covers")
    if not covers:
        return post["slides"]
    return [covers.get(post.get("cover") or "", next(iter(covers.values())))] + post["slides"]


def render_covers(post_dir, post):
    """표지 후보를 out/covers/<키>.jpg 로 모두 그린다."""
    cdir = post_dir / "out" / "covers"
    cdir.mkdir(parents=True, exist_ok=True)
    for k, slide in post.get("covers", {}).items():
        render_slide(slide, post_dir, 1).save(cdir / f"{k}.jpg", quality=94)


def render_all(post_dir, covers=False):
    post_dir = Path(post_dir).resolve()
    post = json.loads((post_dir / "post.json").read_text(encoding="utf-8-sig"))
    out = post_dir / "out"
    out.mkdir(exist_ok=True)
    for old in out.glob("[0-9][0-9].jpg"):
        old.unlink()
    if post.get("covers") and (covers or not (out / "covers").exists()):
        render_covers(post_dir, post)
    files = []
    for i, slide in enumerate(all_slides(post), 1):
        p = out / f"{i:02d}.jpg"
        chosen = out / "covers" / f"{post.get('cover') or next(iter(post.get('covers') or {'': 0}))}.jpg"
        if i == 1 and post.get("covers") and chosen.exists():
            p.write_bytes(chosen.read_bytes())       # 이미 그린 표지 후보를 그대로 쓴다
        else:
            render_slide(slide, post_dir, i).save(p, quality=94)
        files.append(p.name)
    if post.get("info_slide", True) and post.get("store", {}).get("address"):
        p = out / f"{len(files) + 1:02d}.jpg"
        info_slide(post, post_dir).save(p, quality=94)
        files.append(p.name)
    (out / "caption.txt").write_text(caption_text(post), encoding="utf-8")
    return files


# ---------------------------------------------------------------- reel

REEL_MOVES = [   # 하이라이트 컷마다 돌아가며 쓰는 카메라 움직임 (F = 컷 프레임 수)
    ("1+0.14*on/{F}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),            # 확대
    ("1.14", "(iw-iw/zoom)*on/{F}", "ih/2-(ih/zoom/2)"),                   # 왼→오 이동
    ("1.14-0.14*on/{F}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),          # 축소
    ("1.14", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(1-on/{F})"),               # 아래→위 이동
]
X264 = ["-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30"]


def render_reel(post_dir, files):
    """하이라이트 릴스(9:16).
    1) 표지 카드(글자 포함)를 흐린 배경 위에 띄워 cover_seconds 동안
    2) 나머지 장은 글자 없는 원본 사진을 화면 가득 채워 짧게, 확대·이동을 번갈아
    3) reel.clips 에 적은 영상 조각을 지정한 위치에 끼워 넣기
       {"file": "clips/a.mp4", "start": 1.0, "len": 2.0, "after": 1}  (after = 몇 번째 장 뒤, 0 = 표지 뒤)
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    post_dir = Path(post_dir).resolve()
    post = json.loads((post_dir / "post.json").read_text(encoding="utf-8-sig"))
    cfg = post.get("reel", {})
    sec = float(cfg.get("seconds_per_slide", 1.6))
    cover_sec = float(cfg.get("cover_seconds", 2.4))
    RW, RH = 1080, 1920
    out = post_dir / "out"
    run = lambda args: subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", *args], check=True)
    clips = {}
    for c in cfg.get("clips", []):
        clips.setdefault(int(c.get("after", 0)), []).append(c)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        segs, durs = [], []

        def still(img, seconds, move, name):
            frame = td / f"{name}.png"
            img.save(frame)
            F = int(seconds * 30)
            z, x, y = (s.format(F=F) for s in move)
            vf = (f"scale={RW * 2}:{RH * 2},zoompan=z='{z}':x='{x}':y='{y}':d={F}:s={RW}x{RH}:fps=30")
            seg = td / f"{name}.mp4"
            run(["-loop", "1", "-i", str(frame), "-vf", vf, "-frames:v", str(F), *X264, str(seg)])
            segs.append(seg)
            durs.append(F / 30)

        def add_clips(after):
            for k, c in enumerate(clips.get(after, [])):
                src = post_dir / c["file"]
                seg = td / f"c{after:02d}_{k}.mp4"
                run(["-ss", str(c.get("start", 0)), "-t", str(c.get("len", 2.0)), "-i", str(src), "-an",
                     "-vf", f"scale={RW}:{RH}:force_original_aspect_ratio=increase,crop={RW}:{RH},fps=30",
                     *X264, str(seg)])
                segs.append(seg)
                durs.append(float(c.get("len", 2.0)))

        # 1) 표지 카드
        card = Image.open(out / files[0]).convert("RGB")
        bg = ImageOps.fit(card, (RW, RH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.35)
        bg.paste(card, (0, (RH - H) // 2))
        still(bg, cover_sec, ("1+0.05*on/{F}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"), "s00")
        add_clips(0)
        # 2) 나머지 장: 원본 사진을 9:16 으로 가득
        slides = all_slides(post)
        for i, slide in enumerate(slides[1:], 1):
            src = ImageOps.exif_transpose(Image.open(post_dir / slide["image"])).convert("RGB")
            fx, fy = slide.get("focus", [0.5, 0.5])
            still(ImageOps.fit(src, (RW, RH), Image.LANCZOS, centering=(fx, fy)), sec,
                  REEL_MOVES[(i - 1) % len(REEL_MOVES)], f"s{i:02d}")
            add_clips(i)
        if len(files) > len(slides):   # 정보 카드가 있으면 마지막에 카드째로
            info = Image.open(out / files[-1]).convert("RGB")
            ibg = ImageOps.fit(info, (RW, RH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
            ibg.paste(info, (0, (RH - H) // 2))
            still(ibg, sec + 0.6, REEL_MOVES[0], "s99")
        lst = td / "l.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segs), encoding="utf-8")
        reel = out / "reel.mp4"
        total = sum(durs)
        bgm = cfg.get("bgm")
        cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if bgm:
            cmd += ["-stream_loop", "-1", "-i", str((post_dir / bgm) if (post_dir / bgm).exists() else bgm),
                    "-filter_complex", f"[1:a]volume={cfg.get('bgm_volume', 0.8)},afade=t=out:st={total - 1.2}:d=1.2[a]",
                    "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "copy", "-t", f"{total}", "-movflags", "+faststart", str(reel)]
        subprocess.run(cmd, check=True)
    # 릴스 커버 = 첫 카드
    ImageOps.fit(Image.open(out / files[0]).convert("RGB"), (RW, RH), Image.LANCZOS) \
        .save(out / "reel_cover.jpg", quality=92)
    return reel


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("post_dir")
    ap.add_argument("--reel", action="store_true")
    a = ap.parse_args()
    fs = render_all(a.post_dir)
    print("카드:", ", ".join(fs))
    if a.reel:
        print("릴스:", render_reel(a.post_dir, fs))
