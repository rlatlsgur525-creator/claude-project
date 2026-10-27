"""표지 템플릿 5종. brief(가게·메뉴·문구·사진 역할)를 받아 render.py 가 그릴 표지 장(slide)을 만든다.

인기 맛집 계정 표지에서 '구성 방식'만 빌리고, 글꼴·색·말투는 사장님 스타일(굵은 노랑, 빨강 붓띠, 말풍선)로 통일한다.
  A 불꽃 콜라주  : 사장님 기본. 위 입구 + 아래 메뉴, 크기 다른 3단 제목, 불꽃, 붓띠, 말풍선
  B 하단 큰 자막 : 메뉴 사진 한 장 + 아래쪽 굵은 흰 자막 두 줄 (사진이 주인공인 계정들 방식)
  C 마커 간판    : 메뉴 사진 + 빨강·검정 마커 글씨로 가게 이름을 크게 (지역 맛집 소개 계정 방식)
  D 띠 분할      : 위 입구 + 아래 메뉴를 검정 띠로 나누고 띠 안에 노랑 제목
  E 말풍선 후기  : 메뉴 사진 + 큰 말풍선 한 줄평 + 아래 위치 붓띠
"""
import re

import render

NAMES = {"A": "불꽃 콜라주", "B": "하단 큰 자막", "C": "마커 간판", "D": "띠 분할", "E": "말풍선 후기"}


def plain(t):
    return re.sub(r"[\[\]]", "", t)


def fit(text, key, frac, biggest, smallest=36):
    """가장 긴 줄이 화면 폭의 frac 를 넘지 않는 가장 큰 글자 크기."""
    lines = plain(text).split("\n")
    size = biggest
    while size > smallest:
        f = render.font(key, size)
        if max(f.getlength(l) for l in lines) <= render.W * frac:
            break
        size -= 4
    return size


def menu_photo(b):
    p = b["photos"]
    return {"image": p["signature"], "focus": p.get("signature_focus", [0.5, 0.5])}


def collage(b, split=0.46, feather=0.12):
    p = b["photos"]
    if not p.get("exterior"):
        return {**menu_photo(b), "shade": "top", "shade_amount": 120}
    s = {**menu_photo(b), "top_image": p["exterior"], "top_focus": p.get("exterior_focus", [0.5, 0.3]),
         "split": split, "feather": feather}
    if p.get("exterior_crop"):
        s["top_crop"] = p["exterior_crop"]
    return s


def cover_a(b):
    area, menu = b["area"], b["menu"]
    q = b.get("quotes", ["비주얼이\n[미쳤다]..!", "진짜\n[밥도둑]..!"])
    msize = fit(menu, "bold", 0.62, 230)
    return {**collage(b), "elements": [
        {"type": "flame", "x": 0.17, "y": 0.45, "size": 230, "rotate": -12, "tongues": 5},
        {"type": "pin", "x": 0.08, "y": 0.06, "size": 76},
        {"text": f"{area} 맛집", "font": "bold", "size": 70, "x": 0.27, "y": 0.06, "bg": "band", "rotate": -6, "shadow": False},
        {"text": area, "font": "bold", "size": fit(area, "bold", 0.3, 130), "x": 0.17, "y": 0.255, "stroke": 11,
         "stroke_color": "#111111", "rotate": -6},
        {"text": f"[{menu}]", "font": "bold", "size": msize, "x": 0.5, "y": 0.375, "stroke": 13,
         "stroke_color": "#111111", "hl": "#FFE600", "rotate": -6},
        {"text": "맛집", "font": "bold", "size": 112, "x": 0.87, "y": 0.355, "stroke": 10, "stroke_color": "#111111", "rotate": -6},
        {"text": b["hook"], "font": "round", "size": fit(b["hook"], "round", 0.78, 70), "x": 0.5, "y": 0.5, "bg": "band",
         "rotate": -6, "sparkle": "both", "shadow": False},
        {"text": q[0], "font": "round", "size": 52, "x": 0.15, "y": 0.6, "bg": "bubble", "rotate": -8, "shadow": False},
        {"type": "arrow", "from": [0.27, 0.565], "to": [0.36, 0.615], "bend": -0.4, "loop": True, "width": 5},
        {"text": q[1], "font": "round", "size": 56, "x": 0.86, "y": 0.73, "bg": "bubble", "rotate": 6, "shadow": False},
        {"type": "arrow", "from": [0.86, 0.6], "to": [0.92, 0.65], "bend": 0.5, "loop": True, "width": 5},
    ]}


def cover_b(b):
    area, menu, store = b["area"], b["menu"], b["store"]["name"]
    big = f"{area} [{menu}] 맛집"
    return {**menu_photo(b), "shade": "bottom", "shade_amount": 215, "shade_start": 0.45, "elements": [
        {"type": "pin", "x": 0.075, "y": 0.73, "size": 58},
        {"text": store, "font": "sub", "size": 46, "x": 0.075 + 0.03 + render.font("sub", 46).getlength(store) / render.W / 2 + 0.01,
         "y": 0.733, "shadow": "strong"},
        {"text": big, "font": "title", "size": fit(big, "title", 0.88, 112), "x": 0.5, "y": 0.815, "stroke": 6,
         "stroke_color": "#111111", "hl": "#FFE600"},
        {"text": plain(b["hook"]), "font": "title2", "size": fit(b["hook"], "title2", 0.86, 62), "x": 0.5, "y": 0.905,
         "shadow": "strong"},
    ]}


def cover_c(b):
    area, menu, store = b["area"], b["menu"], b["store"]["name"]
    return {**menu_photo(b), "shade": "bottom", "shade_amount": 170, "shade_start": 0.5, "elements": [
        {"text": f"!! {area} {menu} 찐맛집 !!", "font": "dokdo", "size": fit(f"!! {area} {menu} 찐맛집 !!", "dokdo", 0.7, 92), "x": 0.5, "y": 0.69, "color": "#FFFFFF",
         "stroke": 6, "stroke_color": "#111111"},
        {"text": f"[{store}]", "font": "dokdo", "size": fit(store, "dokdo", 0.86, 190), "x": 0.5, "y": 0.8,
         "hl": "#F0201A", "stroke": 9, "stroke_color": "#111111", "stroke2": 8, "stroke2_color": "#FFFFFF", "rotate": -3},
        {"text": b["hook"], "font": "dokdo", "size": fit(b["hook"], "dokdo", 0.86, 84), "x": 0.5, "y": 0.915,
         "hl": "#FFE600", "stroke": 6, "stroke_color": "#111111", "underline": True},
        {"type": "sparkle", "x": 0.1, "y": 0.79, "size": 70, "dir": 200, "width": 6},
        {"type": "sparkle", "x": 0.9, "y": 0.79, "size": 70, "dir": -20, "width": 6},
    ]}


def cover_d(b):
    area, menu, store = b["area"], b["menu"], b["store"]["name"]
    title = f"{area} [{menu}] 맛집"
    return {**collage(b, split=0.5, feather=0.03), "elements": [
        {"text": title, "font": "bold", "size": fit(title, "bold", 0.8, 120), "x": 0.5, "y": 0.5, "color": "#FFFFFF",
         "hl": "#FFE600", "bg": "box", "bg_color": "#111111", "bg_opacity": 0.92, "shadow": False},
        {"text": store, "font": "sub", "size": 46, "x": 0.5, "y": 0.405, "color": "#111111", "bg": "box",
         "bg_color": "#FFFFFF", "bg_opacity": 0.95, "shadow": False},
        {"text": b["hook"], "font": "round", "size": fit(b["hook"], "round", 0.8, 60), "x": 0.5, "y": 0.6, "bg": "band",
         "rotate": -3, "shadow": False},
    ]}


def cover_e(b):
    area, store = b["area"], b["store"]["name"]
    q = b.get("quotes", ["비주얼이\n[미쳤다]..!"])[0]
    return {**menu_photo(b), "shade": "top", "shade_amount": 150, "shade_start": 0.55, "elements": [
        {"text": q, "font": "round", "size": 96, "x": 0.36, "y": 0.17, "bg": "bubble", "rotate": -6, "shadow": False},
        {"type": "arrow", "from": [0.5, 0.27], "to": [0.6, 0.4], "bend": -0.45, "loop": True, "width": 7},
        {"type": "pin", "x": 0.2, "y": 0.9, "size": 70},
        {"text": f"{area} {store}", "font": "bold", "size": fit(f"{area} {store}", "bold", 0.66, 92), "x": 0.56, "y": 0.9,
         "bg": "band", "rotate": -4, "shadow": False, "sparkle": "right"},
    ]}


BUILD = {"A": cover_a, "B": cover_b, "C": cover_c, "D": cover_d, "E": cover_e}


def build_all(brief):
    return {k: fn(brief) for k, fn in BUILD.items()}
