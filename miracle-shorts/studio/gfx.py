"""공통 그리기 도구: 폰트, 색, 카드, 이징, 클립 쓰기 (Pillow 프레임 → ffmpeg mp4).
화면 배치 규칙 (1080x1920):
  위 라벨 y≈270 · 그래픽 y 300~1150 · main 자막 ~1170~1344 · small 자막 ~1430~1536 · 하단 16% 비움
"""
import glob, math, os, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "shorts-kit", "fonts")
W, H, FPS = 1080, 1920, 30

BG = (14, 17, 22)
GRAY = (58, 65, 80)
GRAY_T = (170, 178, 192)
GREEN = (47, 191, 113)
RED = (255, 99, 61)
WHITE = (245, 246, 248)
INK = (30, 34, 42)
MUTED = (110, 116, 128)
YELLOW = (255, 210, 63)
BLUE = (77, 148, 255)

def ffmpeg_bin(name="ffmpeg"):
    p = shutil.which(name)
    if p: return p
    hits = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\\" + name + ".exe"))
    return hits[0] if hits else name

_fc = {}
def font(size, w="Bold"):
    k = (int(size), w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(FONTS, f"Pretendard-{w}.otf"), int(size))
    return _fc[k]

def ease(p):  # easeInOutCubic
    p = max(0.0, min(1.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2

def lerp(a, b, p): return a + (b - a) * p

def text_c(d, xy, s, f, fill):
    d.text(xy, s, font=f, fill=fill, anchor="mm")

def fit_font(d, s, maxw, size, w="Bold", minsize=24):
    """maxw 안에 들어가도록 글자 크기를 줄인다."""
    while size > minsize and d.textlength(s, font=font(size, w)) > maxw:
        size -= 2
    return font(size, w)

def wrap(d, s, f, maxw):
    """글자 단위 줄바꿈 (한국어)."""
    lines, cur = [], ""
    for word in s.split(" "):
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= maxw: cur = t; continue
        if cur: lines.append(cur)
        cur = word
        while d.textlength(cur, font=f) > maxw:  # 한 단어가 너무 길면 글자 단위로 자름
            i = len(cur)
            while i > 1 and d.textlength(cur[:i], font=f) > maxw: i -= 1
            lines.append(cur[:i]); cur = cur[i:]
    if cur: lines.append(cur)
    return lines

def label_top(d, s, color=GRAY_T):
    text_c(d, (W / 2, 270), s, fit_font(d, s, W - 160, 40), color)

def card(d, x, y, w, h, fill, label=None, lf=None, lc=WHITE, glow=None, sx=1.0, radius=16):
    """sx: 가로 축척(뒤집기용)."""
    cx = x + w / 2; w2 = max(w * sx, 2)
    x1, x2 = cx - w2 / 2, cx + w2 / 2
    if glow:
        d.rounded_rectangle([x1 - 8, y - 8, x2 + 8, y + h + 8], radius=radius + 6, outline=glow, width=6)
    d.rounded_rectangle([x1, y, x2, y + h], radius=radius, fill=fill)
    if label and sx > 0.35:
        text_c(d, (cx, y + h / 2), label, lf, lc)

def flip(t, t0, dur=0.45):
    """(가로 축척, 뒷면 여부)"""
    p = (t - t0) / dur
    if p <= 0: return 1.0, False
    if p >= 1: return 1.0, True
    return abs(math.cos(math.pi * p)), p >= 0.5

def grid(n, x0, y0, x1, y1, cols=None, gap=20, aspect=None):
    """n개를 영역 안에 격자로 배치 → [(x, y, w, h)]"""
    if n <= 0: return []
    cols = cols or min(n, max(1, round(math.sqrt(n * (x1 - x0) / max(y1 - y0, 1)))))
    rows = math.ceil(n / cols)
    w = (x1 - x0 - gap * (cols - 1)) / cols
    h = (y1 - y0 - gap * (rows - 1)) / rows
    if aspect: w, h = min(w, h / aspect), min(h, w * aspect)
    tw = cols * w + (cols - 1) * gap; th = rows * h + (rows - 1) * gap
    ox = x0 + (x1 - x0 - tw) / 2; oy = y0 + (y1 - y0 - th) / 2
    out = []
    for i in range(n):
        c, r = i % cols, i // cols
        last = n - (rows - 1) * cols  # 마지막 줄 가운데 정렬
        shift = (cols - last) * (w + gap) / 2 if r == rows - 1 and last < cols else 0
        out.append((ox + shift + c * (w + gap), oy + r * (h + gap), w, h))
    return out

# ---------------- 마스코트 (brand/mascot/README.md, studio/library/mascot/*.png) ----------------
MASCOT_DIR = os.path.join(HERE, "library", "mascot")
SVG_DIR = os.path.join(HERE, "library", "mascot_svg")
_mc = {}
def mascot_img(name, h, mirror=False):
    k = (name, int(h), mirror)
    if k not in _mc:
        im = Image.open(os.path.join(MASCOT_DIR, name + ".png")).convert("RGBA")
        im = im.resize((max(1, round(im.width * h / im.height)), int(h)), Image.LANCZOS)
        if mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        _mc[k] = im
    return _mc[k]

def svg_img(name, h, ink="#000", paper="#fff", edge=None, mirror=False):
    """벡터 포즈(library/mascot_svg/<name>.svg, brand/mascot/vectorize.py로 만듦)를 높이 h로 그린다.
    PNG와 달리 크게 키워도 선이 선명하고, 잉크·바탕·테두리 색을 장면 팔레트에 맞춰 바꿀 수 있다. 필요: pip install resvg-py"""
    k = ("svg", name, int(h), ink, paper, edge, mirror)
    if k not in _mc:
        import io, re, resvg_py
        svg = open(os.path.join(SVG_DIR, name + ".svg"), encoding="utf-8").read()
        edge = edge or paper
        svg = re.sub(r"\.edge\{fill:[^;]+;stroke:[^;]+;", f".edge{{fill:{edge};stroke:{edge};", svg)
        svg = re.sub(r"\.paper\{fill:[^}]+\}", f".paper{{fill:{paper}}}", svg)
        svg = re.sub(r"\.ink\{fill:[^}]+\}", f".ink{{fill:{ink}}}", svg)
        # 높이만 준다: resvg는 너비·높이를 같이 주면 너비에 맞춰 높이가 몇 px 달라진다
        im = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg, height=int(h))))).convert("RGBA")
        if mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        _mc[k] = im
    return _mc[k]

def draw_mascot(d, name, cx, top, h, t, appear=0.0, mirror=False, enter="right"):
    """전신 포즈를 (cx 가운데, top 위쪽, 높이 h)에 그린다. appear초에 옆에서 미끄러져 들어오고, 이후 살짝 숨쉬듯 움직인다."""
    if t < appear: return
    im = mascot_img(name, h, mirror); p = ease((t - appear) / 0.3)
    dx = (1 - p) * (140 if enter == "right" else -140); dy = 5 * math.sin((t - appear) * 2.6)
    if p < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * p)))
    d._image.paste(im, (int(cx - im.width / 2 + dx), int(top + dy)), im)

def mascot_avatar(name, size):
    """포즈 그림에서 얼굴 부분을 동그랗게 잘라낸 아바타 (권위 카드·말풍선용)"""
    k = ("avatar", name, size)
    if k not in _mc:
        im = Image.open(os.path.join(MASCOT_DIR, name + ".png")).convert("RGBA")
        a = im.getchannel("A"); H = im.height
        top = a.crop((0, 0, im.width, int(H * 0.15))).getbbox()
        cx = (top[0] + top[2]) // 2 if top else im.width // 2
        side = int(H * 0.2); y0 = max(0, (top[1] if top else 0) - int(side * 0.05))
        face = Image.new("RGBA", (side, side), (255, 255, 255, 255))
        face.alpha_composite(im.crop((cx - side // 2, y0, cx + side // 2, y0 + side)))
        face = face.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size * 4, size * 4), 0); ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
        face.putalpha(mask.resize((size, size), Image.LANCZOS)); _mc[k] = face
    return _mc[k]

def write_clip(path, dur, draw_fn, scale=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w, h = W // scale, H // scale
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(round(dur * FPS))):
        im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
        draw_fn(d, i / FPS)
        if scale != 1: im = im.resize((w, h), Image.BILINEAR)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait(): raise RuntimeError(f"ffmpeg failed: {path}")
