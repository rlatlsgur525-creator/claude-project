#!/usr/bin/env python3
"""마스코트 포즈(흰 배경 PNG) → 배경 투명 PNG로 잘라 스튜디오 공용 라이브러리에 넣는다.
usage: python make_cutouts.py            (raw/*.png 중 포즈 파일 전부)
가장자리와 이어진 흰 영역만 투명하게 만든다. 셔츠처럼 선으로 둘러싸인 흰색은 그대로 남는다.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "..", "..", "studio", "library", "mascot")
SKIP = {"sheet.png", "original.png"}  # 설정표·원본 시안(좌우 2컷)은 오려내지 않는다
MAX_H = 1400
STROKE = 14  # 흰 테두리 두께(px, 높이 1400 기준)

def cutout(path, out):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    KEY = (255, 0, 255)  # 바깥 흰색을 이 색으로 채운 뒤 투명 처리 (L 모드 floodfill은 이 Pillow에서 채워지지 않았다)
    c = im.copy()
    seeds = [(x, y) for x in range(0, w, 16) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 16) for x in (0, w - 1)]
    for s in seeds:
        if sum(c.getpixel(s)) > 228 * 3 and c.getpixel(s) != KEY: ImageDraw.floodfill(c, s, KEY, thresh=40)
    a = np.asarray(c)
    bg = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255)
    alpha = Image.fromarray(np.where(bg, 0, 255).astype("uint8")).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = im.copy(); rgba.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 20 else 0).getbbox()
    rgba = rgba.crop((max(0, bbox[0] - 12), max(0, bbox[1] - 12), min(w, bbox[2] + 12), min(h, bbox[3] + 12)))
    if rgba.height > MAX_H: rgba = rgba.resize((round(rgba.width * MAX_H / rgba.height), MAX_H), Image.LANCZOS)
    # 흰 스티커 테두리: 검은 정장이 어두운 쇼츠 배경에 묻히지 않게 실루엣 바깥에 흰 띠를 두른다
    pad = STROKE + 4
    canvas = Image.new("RGBA", (rgba.width + pad * 2, rgba.height + pad * 2), (0, 0, 0, 0)); canvas.paste(rgba, (pad, pad))
    ring = canvas.getchannel("A")
    for _ in range(STROKE // 2): ring = ring.filter(ImageFilter.MaxFilter(3))
    ring = ring.filter(ImageFilter.GaussianBlur(1))
    sticker = Image.new("RGBA", canvas.size, (255, 255, 255, 0)); sticker.putalpha(ring)
    sticker.alpha_composite(canvas)
    sticker.save(out, optimize=True)
    return sticker.size
    return rgba.size

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or sorted(f for f in os.listdir(RAW) if f.endswith(".png") and f not in SKIP)
    for n in names:
        size = cutout(os.path.join(RAW, n), os.path.join(OUT, n))
        print(n, size)
