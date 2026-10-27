"""사진 + brief.json → 필터 입힌 사진, 표지 후보 5개, 카드뉴스, 캡션까지 한 번에.

    python make_post.py posts/<게시물>

brief.json 예 (posts/2026-10-23-sukine-jeonju/brief.json 참고)
{
  "store": {"name": "숙이네 밥상", "area": "전주 완산구", "address": "...", "hours": "...", "phone": "..."},
  "area": "전주", "menu": "갈비찜",
  "hook": "푸짐한 한 냄비, [밥도둑] 인정!",
  "quotes": ["비주얼이\\n[미쳤다]..!", "진짜\\n[밥도둑]..!"],
  "look": "v1",                       # 맛있게 필터 (v1 | jeonju | none) 또는
                                      # {"preset": "v1", "strength": 1, "bright": 0, "warm": 0, "sat": 0, "sharp": 0}
  "photos": {"exterior": "photos/입구.jpg", "exterior_crop": [0, 0, 1, 1],
             "signature": "photos/집게샷.jpg", "signature_focus": [0.5, 0.3]},
  "order": ["photos/상차림.jpg", {"image": "photos/반찬.jpg", "focus": [0.5, 0.6]}],
  "caption": "...", "hashtags": ["전주맛집", ...],
  "reel": {"clips": [{"file": "clips/a.mp4", "start": 0, "len": 2, "after": 1}]}
}
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import covers
import look
import render


def look_of(b):
    """brief 의 look 을 {"preset", "strength", 밝기·따뜻함·채도·선명함} 꼴로 맞춘다."""
    lk = b.get("look", "v1")
    lk = {"preset": lk} if isinstance(lk, str) else dict(lk)
    return {"preset": "v1", "strength": 1.0, **lk}


def filtered(post_dir, rel, lk, fresh):
    """photos/x.jpg → photos_f/x.jpg (필터 적용본). 원본·필터 설정이 그대로면 다시 만들지 않는다."""
    if not rel or lk["preset"] == "none":
        return rel
    src = post_dir / rel
    dst = post_dir / "photos_f" / (Path(rel).stem + ".jpg")
    if not fresh or not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.parent.mkdir(exist_ok=True)
        look.apply(Image.open(src), lk["preset"], lk["strength"], lk).save(dst, quality=95)
    return dst.relative_to(post_dir).as_posix()


def contact_sheet(post_dir, keys):
    """표지 후보 5개를 한 장에 (채팅으로 보내 고르기 쉽게)."""
    w = 360
    h = int(w * render.H / render.W)
    sheet = Image.new("RGB", (w * len(keys) + 12 * (len(keys) - 1), h + 70), "white")
    d = ImageDraw.Draw(sheet)
    f = render.font("title2", 34)
    for i, k in enumerate(keys):
        im = Image.open(post_dir / "out" / "covers" / f"{k}.jpg").resize((w, h))
        x = i * (w + 12)
        sheet.paste(im, (x, 70))
        d.text((x + 8, 14), f"{k}  {covers.NAMES[k]}", font=f, fill=(20, 20, 20))
    p = post_dir / "out" / "covers" / "all.jpg"
    sheet.save(p, quality=90)
    return p


def main(post_dir):
    post_dir = Path(post_dir).resolve()
    b = json.loads((post_dir / "brief.json").read_text(encoding="utf-8-sig"))
    if not b.get("photos", {}).get("signature"):
        raise ValueError("표지 아래에 들어갈 대표 메뉴 사진을 골라 주세요.")
    for k in ("area", "menu", "hook"):
        if not b.get(k):
            raise ValueError("표지 문구의 지역, 대표 메뉴, 한 줄 문구를 채워 주세요.")
    lk = look_of(b)
    # 필터 설정이 바뀌었으면 필터 적용본을 전부 새로 만든다
    mark = post_dir / "photos_f" / "_look.json"
    fresh = mark.exists() and json.loads(mark.read_text(encoding="utf-8")) == lk
    ph = dict(b["photos"])
    ph["exterior"] = filtered(post_dir, ph.get("exterior"), lk, fresh)
    ph["signature"] = filtered(post_dir, ph["signature"], lk, fresh)
    brief = {**b, "photos": ph}
    slides = []
    for o in b.get("order", []):
        o = {"image": o} if isinstance(o, str) else dict(o)
        o["image"] = filtered(post_dir, o["image"], lk, fresh)
        slides.append({"focus": [0.5, 0.5], **o, "elements": []})
    if lk["preset"] != "none":
        mark.write_text(json.dumps(lk), encoding="utf-8")
    post = {
        "status": "draft",
        "style": "thumb",
        "store": b["store"],
        "schedule": b.get("schedule"),
        "covers": covers.build_all(brief),
        "cover": None,
        "slides": slides,
        "info_slide": False,
        "caption": b.get("caption", ""),
        "hashtags": b.get("hashtags", []),
        "reel": {"seconds_per_slide": 1.6, "cover_seconds": 2.4, "bgm": None, **b.get("reel", {})},
    }
    (post_dir / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    files = render.render_all(post_dir, covers=True)
    sheet = contact_sheet(post_dir, list(post["covers"]))
    print("표지 후보:", sheet)
    print("카드:", ", ".join(files))
    return post


def pick(post_dir, key):
    """채팅으로 "B로 해줘" 했을 때: 표지를 고르고 카드·릴스까지 만들어 게시 대기 상태로."""
    post_dir = Path(post_dir).resolve()
    p = json.loads((post_dir / "post.json").read_text(encoding="utf-8-sig"))
    if key not in p.get("covers", {}):
        sys.exit(f"표지 후보에 {key} 가 없습니다: {', '.join(p.get('covers', {}))}")
    p["cover"], p["status"] = key, "draft"
    (post_dir / "post.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    files = render.render_all(post_dir)
    print("릴스:", render.render_reel(post_dir, files))
    p["status"] = "approved"
    (post_dir / "post.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("사용법: python make_post.py posts/<게시물폴더> [--pick A]")
    if "--pick" in sys.argv:
        pick(sys.argv[1], sys.argv[sys.argv.index("--pick") + 1].upper())
    else:
        try:
            main(sys.argv[1])
        except ValueError as e:
            sys.exit(str(e))
