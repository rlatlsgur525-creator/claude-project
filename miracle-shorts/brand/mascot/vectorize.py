#!/usr/bin/env python3
"""마스코트 포즈(흰 배경 PNG) → SVG 벡터 그림. 스튜디오 공용 라이브러리 mascot_svg/에 넣는다.
usage: python vectorize.py                  (raw/*.png 중 포즈 파일 전부)
       python vectorize.py point.png
필요: pip install vtracer  (렌더에서 SVG를 쓰려면 resvg-py도: gfx.svg_img)

왜: 이미지 모델이 그린 캐릭터를 벡터로 바꾸면 (1) 얼굴 확대·줌인에도 선이 뭉개지지 않고
(2) 잉크·바탕 색을 코드에서 바꿔 장면 색(팔레트)에 맞출 수 있다. 우리 마스코트는 흑백 2색이라 그대로 따진다.
SVG 구성(아래부터): 스티커 테두리(class=edge) → 바탕 실루엣(class=paper, 셔츠 등 흰 면) → 선·검은 면(class=ink)
"""
import os, re, sys, tempfile
import numpy as np
from PIL import Image
import vtracer
from make_cutouts import RAW, SKIP, MAX_H, STROKE, bg_mask

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "studio", "library", "mascot_svg")
# PNG(make_cutouts.cutout)와 같은 기하를 원본 px로 환산한다 → 같은 높이로 그리면 인물 크기·테두리·여백이 PNG와 같다
#   PNG: 실루엣 bbox ±CROP → 높이 MAX_H로 축소(f) → 바깥 여백 STROKE+4 → 테두리 STROKE//2 번 1px 팽창(+원본에서 1px)
CROP = 12

def trace(mask):
    """True 영역을 검은 면으로 보고 패스 목록(d, transform)을 돌려준다"""
    im = Image.fromarray(np.where(mask, 0, 255).astype("uint8")).convert("RGB")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.svg")
        im.save(src)
        vtracer.convert_image_to_svg_py(src, dst, colormode="binary", filter_speckle=4, corner_threshold=60, path_precision=2)
        svg = open(dst, encoding="utf-8").read()
    return re.findall(r'<path d="([^"]+)"[^>]*?(?:transform="([^"]+)")?\s*/>', svg)

def paths(items, cls):
    return "\n".join(f'<path class="{cls}" d="{d}"' + (f' transform="{t}"' if t else "") + "/>" for d, t in items)

def vectorize(path, out):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    body = ~bg_mask(im)
    ys, xs = np.nonzero(body)
    cx0, cy0, cx1, cy1 = max(0, xs.min() - CROP), max(0, ys.min() - CROP), min(w, xs.max() + 1 + CROP), min(h, ys.max() + 1 + CROP)
    f = min(1.0, MAX_H / (cy1 - cy0))  # PNG가 줄인 배율
    pad = round((STROKE + 4) / f); edge = (STROKE // 2) / f + 1
    M = pad  # 자른 영역 + 바깥 여백이 원본 밖으로 나갈 수 있어 빈 칸을 덧댄다
    body = np.pad(body, M); ink = np.pad(np.asarray(im.convert("L")) < 128, M)
    x0, y0, x1, y1 = cx0 + M - pad, cy0 + M - pad, cx1 + M + pad, cy1 + M + pad
    sil, lines = trace(body[y0:y1, x0:x1]), trace((ink & body)[y0:y1, x0:x1])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0}" height="{y1 - y0}" viewBox="0 0 {x1 - x0} {y1 - y0}">\n'
           f'<style>.edge{{fill:#fff;stroke:#fff;stroke-width:{edge * 2:.1f};stroke-linejoin:round}} .paper{{fill:#fff}} .ink{{fill:#000}}</style>\n'
           f'{paths(sil, "edge")}\n{paths(sil, "paper")}\n{paths(lines, "ink")}\n</svg>\n')
    with open(out, "w", encoding="utf-8") as f: f.write(svg)
    return (int(x1 - x0), int(y1 - y0)), len(svg) // 1024

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or sorted(f for f in os.listdir(RAW) if f.endswith(".png") and f not in SKIP)
    for n in names:
        size, kb = vectorize(os.path.join(RAW, n), os.path.join(OUT, n[:-4] + ".svg"))
        print(n, size, f"{kb}KB")
