"""가게 홍보용 인스타 카드뉴스(PNG) + 릴스(MP4) 자동 제작기.

사용법:
    python make.py posts/<게시물폴더>            # 카드뉴스 + 릴스 모두
    python make.py posts/<게시물폴더> --only card
    python make.py posts/<게시물폴더> --only reel

게시물 폴더 안의 post.yaml 과 사진/영상을 읽어 out/ 폴더에 결과물을 만든다.
가게 정보(이름·색·주소 등)는 stores/<가게>/store.yaml 에서 가져온다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CARD = (1080, 1350)   # 인스타 피드 4:5
REEL = (1080, 1920)   # 릴스 9:16
FPS = 30
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")

# ---------------------------------------------------------------- fonts

FONT_DIRS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
             Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
             ROOT / "fonts"]
FONT_CANDIDATES = {
    "bold": ["Pretendard-Bold.otf", "NotoSansKR-Bold.ttf", "NanumGothicExtraBold.ttf", "malgunbd.ttf"],
    "regular": ["Pretendard-Regular.otf", "NotoSansKR-Medium.ttf", "NanumGothic.ttf", "malgun.ttf"],
}
_font_cache = {}


def font(weight, size):
    key = (weight, size)
    if key not in _font_cache:
        for name in FONT_CANDIDATES[weight]:
            for d in FONT_DIRS:
                if (d / name).exists():
                    _font_cache[key] = ImageFont.truetype(str(d / name), size)
                    break
            if key in _font_cache:
                break
        else:
            sys.exit("한글 폰트를 찾지 못했습니다. studio/fonts/ 에 Pretendard 폰트를 넣어주세요.")
    return _font_cache[key]


# ---------------------------------------------------------------- helpers

def hex_rgb(h, alpha=None):
    h = h.lstrip("#")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return rgb + (alpha,) if alpha is not None else rgb


def wrap(draw, text, fnt, max_w):
    """한글은 글자 단위, 영문은 단어 단위로 줄바꿈. 직접 넣은 줄바꿈은 그대로 유지."""
    lines = []
    # 한글 폰트에는 이모지가 없어 □로 깨지므로 이미지 위 글자에서는 빼고, 캡션에만 쓴다
    text = EMOJI.sub("", str(text)).strip()
    # 따옴표 없이 쓴 YAML의 \n 도 줄바꿈으로 받아준다
    for para in text.replace("\\n", "\n").split("\n"):
        line = ""
        for token in re.findall(r"[A-Za-z0-9.,!?%'\"()\-]+|\s|.", para):
            trial = line + token
            if draw.textlength(trial, font=fnt) <= max_w or not line:
                line = trial
            else:
                lines.append(line.rstrip())
                line = token.lstrip()
        lines.append(line.rstrip())
    return lines


def draw_lines(draw, lines, fnt, x, y, fill, spacing=1.32, align="left", width=None):
    lh = int(fnt.size * spacing)
    for ln in lines:
        lx = x
        if align == "center":
            lx = x + (width - draw.textlength(ln, font=fnt)) / 2
        draw.text((lx, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def text_height(lines, fnt, spacing=1.32):
    return int(fnt.size * spacing) * len(lines)


def cover_fit(img, size):
    return ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), size, Image.LANCZOS)


def vertical_gradient(size, top_alpha, bottom_alpha, start=0.0):
    w, h = size
    grad = Image.new("L", (1, h))
    for y in range(h):
        t = max(0.0, (y / h - start) / (1 - start)) if start < 1 else 0
        grad.putpixel((0, y), int(top_alpha + (bottom_alpha - top_alpha) * t))
    return grad.resize(size)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("ffmpeg 오류:\n" + r.stderr[-2000:])
    return r


def has_audio(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return "Audio:" in r.stderr


# ---------------------------------------------------------------- card news

class Brand:
    def __init__(self, store):
        c = store.get("colors", {})
        self.name = store["name"]
        self.handle = store.get("instagram", "")
        self.primary = c.get("primary", "#1F3A2E")
        self.accent = c.get("accent", "#F2B544")
        self.light = c.get("background", "#F7F3EC")
        self.text = c.get("text", "#1B1B1B")
        self.store = store

    def tag(self):
        return f"@{self.handle}" if self.handle else self.name


def card_cover(slide, brand, base):
    W, H = CARD
    img = cover_fit(Image.open(base / slide["photo"]), CARD)
    shade = Image.new("RGB", CARD, (0, 0, 0))
    img = Image.composite(shade, img, vertical_gradient(CARD, 0, 215, start=0.35))
    d = ImageDraw.Draw(img)
    pad = 84
    # 상단 가게 라벨
    lab_f = font("bold", 34)
    lab = brand.name
    lw = d.textlength(lab, font=lab_f)
    d.rounded_rectangle((pad, pad, pad + lw + 48, pad + 66), 33, fill=hex_rgb(brand.accent))
    d.text((pad + 24, pad + 12), lab, font=lab_f, fill=hex_rgb(brand.primary))

    title_f = font("bold", slide.get("size", 92))
    sub_f = font("regular", 40)
    t_lines = wrap(d, slide["title"], title_f, W - pad * 2)
    s_lines = wrap(d, slide.get("sub", ""), sub_f, W - pad * 2) if slide.get("sub") else []
    y = H - pad - text_height(s_lines, sub_f, 1.45) - text_height(t_lines, title_f, 1.22) - 70
    y = draw_lines(d, t_lines, title_f, pad, y, "white", 1.22)
    d.rectangle((pad, y + 26, pad + 90, y + 34), fill=hex_rgb(brand.accent))
    draw_lines(d, s_lines, sub_f, pad, y + 66, (235, 235, 235), 1.45)
    return img


def card_photo(slide, brand, base, idx, total):
    W, H = CARD
    canvas = Image.new("RGB", CARD, hex_rgb(brand.light))
    ph_h = int(H * 0.58)
    canvas.paste(cover_fit(Image.open(base / slide["photo"]), (W, ph_h)), (0, 0))
    d = ImageDraw.Draw(canvas)
    pad = 80
    num_f = font("bold", 30)
    d.text((pad, ph_h + 56), f"{idx:02d}", font=num_f, fill=hex_rgb(brand.accent))
    title_f = font("bold", slide.get("size", 60))
    body_f = font("regular", 36)
    y = draw_lines(d, wrap(d, slide["title"], title_f, W - pad * 2), title_f, pad, ph_h + 104,
                   hex_rgb(brand.primary), 1.25)
    if slide.get("body"):
        draw_lines(d, wrap(d, slide["body"], body_f, W - pad * 2), body_f, pad, y + 18,
                   hex_rgb(brand.text), 1.55)
    foot_f = font("regular", 26)
    d.text((pad, H - 64), brand.tag(), font=foot_f, fill=(140, 140, 140))
    pg = f"{idx} / {total}"
    d.text((W - pad - d.textlength(pg, font=foot_f), H - 64), pg, font=foot_f, fill=(140, 140, 140))
    return canvas


def card_text(slide, brand, base, idx, total):
    W, H = CARD
    canvas = Image.new("RGB", CARD, hex_rgb(brand.primary))
    d = ImageDraw.Draw(canvas)
    pad = 96
    title_f = font("bold", slide.get("size", 76))
    body_f = font("regular", 40)
    t_lines = wrap(d, slide["title"], title_f, W - pad * 2)
    b_lines = wrap(d, slide.get("body", ""), body_f, W - pad * 2) if slide.get("body") else []
    block = text_height(t_lines, title_f, 1.25) + (60 + text_height(b_lines, body_f, 1.6) if b_lines else 0)
    y = (H - block) // 2
    d.rectangle((pad, y - 60, pad + 90, y - 50), fill=hex_rgb(brand.accent))
    y = draw_lines(d, t_lines, title_f, pad, y, "white", 1.25)
    if b_lines:
        draw_lines(d, b_lines, body_f, pad, y + 60, (225, 225, 225), 1.6)
    foot_f = font("regular", 26)
    d.text((pad, H - 70), brand.tag(), font=foot_f, fill=(200, 200, 200))
    return canvas


def info_card(brand, size, title=None):
    """가게 정보(위치·영업시간·연락처) 카드. 카드뉴스 마지막 장과 릴스 아웃트로에 같이 쓴다."""
    W, H = size
    s = brand.store
    canvas = Image.new("RGB", size, hex_rgb(brand.primary))
    d =ImageDraw.Draw(canvas)
    pad = 96
    rows = [(k, s.get(f)) for k, f in
            [("위치", "address"), ("영업시간", "hours"), ("휴무", "closed"), ("문의", "phone"),
             ("예약", "reservation")] if s.get(f)]
    name_f = font("bold", 84)
    key_f = font("bold", 32)
    val_f = font("regular", 38)
    head_f = font("regular", 36)

    val_w = W - pad * 2
    row_blocks = [(k, wrap(d, v, val_f, val_w)) for k, v in rows]
    block = 60 + 130 + sum(48 + text_height(v, val_f, 1.4) + 40 for _, v in row_blocks)
    y = max(pad, (H - block) // 2)
    head = title or s.get("cta", "지금 방문해 보세요")
    d.text((pad, y), head, font=head_f, fill=hex_rgb(brand.accent))
    y += 60
    d.text((pad, y), brand.name, font=name_f, fill="white")
    y += 150
    for k, v_lines in row_blocks:
        d.text((pad, y), k, font=key_f, fill=hex_rgb(brand.accent))
        y = draw_lines(d, v_lines, val_f, pad, y + 48, "white", 1.4) + 40

    if s.get("logo") and (ROOT / s["logo"]).exists():
        logo = Image.open(ROOT / s["logo"]).convert("RGBA")
        logo.thumbnail((180, 180))
        canvas.paste(logo, (W - pad - logo.width, pad), logo)
    if brand.handle:
        hf = font("bold", 34)
        txt = f"@{brand.handle}"
        tw = d.textlength(txt, font=hf)
        d.rounded_rectangle((pad, H - pad - 70, pad + tw + 56, H - pad), 35, fill=hex_rgb(brand.accent))
        d.text((pad + 28, H - pad - 58), txt, font=hf, fill=hex_rgb(brand.primary))
    return canvas


def make_cardnews(post, brand, base, out):
    slides = post["cardnews"]
    total = len(slides) + (1 if post.get("info_card", True) else 0)
    paths = []
    for i, slide in enumerate(slides, 1):
        layout = slide.get("layout", "cover" if i == 1 else "photo")
        if layout == "cover":
            img = card_cover(slide, brand, base)
        elif layout == "photo":
            img = card_photo(slide, brand, base, i, total)
        elif layout == "text":
            img = card_text(slide, brand, base, i, total)
        else:
            sys.exit(f"알 수 없는 layout: {layout} (cover / photo / text 중 하나)")
        p = out / f"card_{i:02d}.jpg"
        img.save(p, quality=93)
        paths.append(p)
    if post.get("info_card", True):
        p = out / f"card_{total:02d}.jpg"
        info_card(brand, CARD).save(p, quality=93)
        paths.append(p)
    if len(paths) > 10:
        print("! 인스타 캐러셀은 최대 10장입니다. 11장째부터는 올라가지 않아요.")
    return paths


# ---------------------------------------------------------------- reels

def reel_overlay(text, brand, path, position="bottom"):
    """릴스 한 컷 위에 올릴 자막 PNG (투명 배경)."""
    W, H = REEL
    img = Image.new("RGBA", REEL, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 상단 가게 태그
    tf = font("bold", 34)
    tag = brand.tag()
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle((60, 150, 60 + tw + 48, 216), 33, fill=hex_rgb(brand.primary, 220))
    d.text((84, 162), tag, font=tf, fill="white")
    if text:
        f = font("bold", 64)
        lines = wrap(d, text, f, W - 220)
        th = text_height(lines, f, 1.3)
        # 인스타 UI(하단 캡션·버튼)에 가리지 않도록 화면 아래 1/4보다 위에 둔다
        cy = {"top": 360, "center": (H - th) // 2, "bottom": int(H * 0.66) - th}[position]
        widest = max(d.textlength(l, font=f) for l in lines)
        x0 = (W - widest) / 2 - 44
        d.rounded_rectangle((x0, cy - 34, W - x0, cy + th + 18), 28, fill=(0, 0, 0, 150))
        draw_lines(d, lines, f, 0, cy, "white", 1.3, align="center", width=W)
    img.save(path)


def reel_segment(clip, idx, brand, base, tmp, keep_audio):
    src = base / clip["src"] if "src" in clip else None
    dur = float(clip.get("dur", 3))
    ov = tmp / f"ov_{idx:02d}.png"
    seg = tmp / f"seg_{idx:02d}.mp4"
    W, H = REEL
    if clip.get("info"):
        still = tmp / f"info_{idx:02d}.png"
        info_card(brand, REEL, clip.get("text")).save(still)
        Image.new("RGBA", REEL, (0, 0, 0, 0)).save(ov)
        src, is_image, pan = still, True, False
    else:
        reel_overlay(clip.get("text", ""), brand, ov, clip.get("position", "bottom"))
        is_image = src.suffix.lower() in IMAGE_EXT
        pan = True

    if is_image:
        # 사진: 살짝 확대한 뒤 천천히 좌우로 흐르는 켄번스 효과
        big = tmp / f"img_{idx:02d}.png"
        zoom = 1.12 if pan else 1.0
        cover_fit(Image.open(src), (int(W * zoom) // 2 * 2, int(H * zoom) // 2 * 2)).save(big)
        if pan:
            direction = "(iw-ow)*t/{d}" if idx % 2 == 0 else "(iw-ow)*(1-t/{d})"
            crop = f"crop={W}:{H}:x='{direction.format(d=dur)}':y='(ih-oh)/2'"
        else:
            crop = f"crop={W}:{H}"
        inputs = ["-loop", "1", "-t", f"{dur}", "-i", str(big)]
        vchain = f"[0:v]{crop},fps={FPS},setsar=1"
        audio_src = None
    else:
        start = float(clip.get("start", 0))
        inputs = ["-ss", f"{start}", "-t", f"{dur}", "-i", str(src)]
        speed = float(clip.get("speed", 1))
        vchain = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"setpts=PTS/{speed},fps={FPS},setsar=1")
        dur = dur / speed
        audio_src = "0:a" if keep_audio and speed == 1 and has_audio(src) else None

    inputs += ["-i", str(ov), "-f", "lavfi", "-t", f"{dur}", "-i", "anullsrc=r=44100:cl=stereo"]
    fc = f"{vchain}[v];[v][1:v]overlay=0:0,format=yuv420p[vo]"
    if audio_src:
        fc += f";[{audio_src}]aresample=44100,aformat=channel_layouts=stereo,apad[a]"
        amap = "[a]"
    else:
        amap = "2:a"
    run([FFMPEG, "-y", "-hide_banner", *inputs, "-filter_complex", fc,
         "-map", "[vo]", "-map", amap, "-t", f"{dur}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", str(seg)])
    return seg, dur


def make_reel(post, brand, base, out):
    cfg = post["reel"]
    clips = list(cfg["clips"])
    if cfg.get("outro", True):
        clips.append({"info": True, "dur": cfg.get("outro_dur", 2.5), "text": cfg.get("outro_text")})
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        segs, total = [], 0.0
        for i, clip in enumerate(clips):
            seg, d = reel_segment(clip, i, brand, base, tmp, cfg.get("keep_audio", True))
            segs.append(seg)
            total += d
            print(f"  컷 {i + 1}/{len(clips)} 완료 ({d:.1f}초)")
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
        joined = tmp / "joined.mp4"
        run([FFMPEG, "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(joined)])

        reel = out / "reel.mp4"
        bgm = cfg.get("bgm")
        if bgm:
            bgm_path = (base / bgm) if (base / bgm).exists() else ROOT / bgm
            vol = cfg.get("bgm_volume", 0.35)
            fade = max(0.0, total - 1.5)
            run([FFMPEG, "-y", "-hide_banner", "-i", str(joined), "-stream_loop", "-1", "-i", str(bgm_path),
                 "-filter_complex",
                 f"[1:a]volume={vol},afade=t=in:d=0.5,afade=t=out:st={fade}:d=1.5[b];"
                 f"[0:a][b]amix=inputs=2:duration=first:normalize=0[a]",
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-t", f"{total}", "-movflags", "+faststart", str(reel)])
        else:
            run([FFMPEG, "-y", "-hide_banner", "-i", str(joined), "-c", "copy",
                 "-movflags", "+faststart", str(reel)])

    # 릴스 커버: 첫 컷 1초 지점 프레임
    cover = out / "reel_cover.jpg"
    run([FFMPEG, "-y", "-hide_banner", "-ss", "1", "-i", str(reel), "-frames:v", "1", "-q:v", "2", str(cover)])
    return reel, cover, total


# ---------------------------------------------------------------- main

def build_caption(post, brand):
    cap = str(post.get("caption", "")).strip()
    tags = post.get("hashtags") or brand.store.get("hashtags") or []
    if tags:
        cap += "\n\n" + " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
    if len(cap) > 2200:
        print(f"! 캡션이 {len(cap)}자입니다. 인스타 한도 2200자를 넘어요.")
    return cap


def main():
    ap = argparse.ArgumentParser(description="인스타 카드뉴스·릴스 자동 제작")
    ap.add_argument("post_dir")
    ap.add_argument("--only", choices=["card", "reel"])
    a = ap.parse_args()

    base = Path(a.post_dir).resolve()
    post = yaml.safe_load((base / "post.yaml").read_text(encoding="utf-8"))
    store = yaml.safe_load((ROOT / "stores" / post["store"] / "store.yaml").read_text(encoding="utf-8"))
    brand = Brand(store)
    out = base / "out"
    out.mkdir(exist_ok=True)

    manifest = {"store": post["store"], "schedule": post.get("schedule"),
                "caption": build_caption(post, brand), "posts": []}
    prev = out / "manifest.json"
    if a.only and prev.exists():
        # 한쪽만 다시 만들 때는 다른 쪽 결과를 manifest에 남겨 둔다
        kept = "reel" if a.only == "card" else "cardnews"
        manifest["posts"] = [p for p in json.loads(prev.read_text(encoding="utf-8")).get("posts", [])
                             if p["type"] == kept]

    if post.get("cardnews") and a.only in (None, "card"):
        print("카드뉴스 만드는 중...")
        cards = make_cardnews(post, brand, base, out)
        manifest["posts"].append({"type": "cardnews", "files": [p.name for p in cards],
                                  "schedule": post.get("cardnews_schedule", post.get("schedule"))})
        print(f"  → {len(cards)}장 완료")
    if post.get("reel") and a.only in (None, "reel"):
        print("릴스 만드는 중...")
        reel, cover, total = make_reel(post, brand, base, out)
        manifest["posts"].append({"type": "reel", "files": [reel.name], "cover": cover.name,
                                  "seconds": round(total, 1),
                                  "schedule": post.get("reel_schedule", post.get("schedule"))})
        print(f"  → reel.mp4 완료 ({total:.1f}초)")

    (out / "caption.txt").write_text(manifest["caption"], encoding="utf-8")
    # YAML이 날짜를 datetime으로 읽으므로 ISO 문자열(+09:00 포함)로 저장
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2,
                   default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o)),
        encoding="utf-8")
    print(f"완료: {out}")


if __name__ == "__main__":
    main()
