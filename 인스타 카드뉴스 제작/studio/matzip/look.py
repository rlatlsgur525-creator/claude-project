"""맛있게 필터 (filter.html 과 같은 계산식의 파이썬판).

    python look.py <사진> <저장경로> [v1|jeonju] [강도0~1]

v1 은 확정 기준, jeonju 는 흰색은 깨끗하게 두고 질감·선명도를 강하게 주는 스타일, none 은 필터 없음.
작업실의 밝기·따뜻함·채도·선명함 슬라이더는 apply(..., adjust={...}) 로 프리셋에 더해진다.
"""
import sys

import numpy as np
from PIL import Image, ImageOps

PRESETS = {
    "v1": dict(warm=(1.04, 1.0, 0.97), gamma=0.78, knee=0.85, contrast=1.12, vib=0.38, sat=1.0, bright=1.03,
               clarity=0.0, sharpen=0.0),
    "jeonju": dict(warm=(0.97, 1.0, 1.04), gamma=0.84, knee=0.82, contrast=1.18, vib=0.5, sat=1.06, bright=1.02,
                   clarity=0.55, sharpen=0.6),
}
DEFAULT_GAIN = (1.056, 1.010, 0.945)


def estimate_gain(a):
    """스테인리스 작업대처럼 밝고 무채색인 부분의 푸른 기를 60%만 걷어내는 색 보정값."""
    flat = a.reshape(-1, 3)
    step = max(1, len(flat) // 250000)
    s = flat[::step].astype(np.int32)
    r, g, b = s[:, 0], s[:, 1], s[:, 2]
    mx, mn = s.max(1), s.min(1)
    sat = np.where(mx == 0, 0, (mx - mn) / np.maximum(mx, 1))
    luma = 0.114 * b + 0.587 * g + 0.299 * r
    pick = (luma > 85) & (sat < 70 / 255) & (b >= r - 6)
    if pick.sum() < len(s) * 0.005:
        return np.array(DEFAULT_GAIN), False
    med = lambda v: np.sort(v)[len(v) >> 1] / 255
    ref = np.array([med(r[pick]), med(g[pick]), med(b[pick])])
    return 1 + 0.6 * (ref.mean() / ref - 1), True


def box(src, r, it):
    """가장자리를 늘려 붙인 박스 블러 (it 번 반복 = 가우시안 근사)."""
    a = src
    for _ in range(it):
        for axis in (1, 0):
            p = np.pad(a, [(r + 1, r) if ax == axis else (0, 0) for ax in range(2)], mode="edge")
            c = np.cumsum(p, axis=axis, dtype=np.float64)
            if axis == 1:
                a = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
            else:
                a = (c[2 * r + 1:, :] - c[:-2 * r - 1, :]) / (2 * r + 1)
    return a.astype(np.float32)


def tuned(preset, adjust=None):
    """화면의 밝기·따뜻함·채도·선명함 슬라이더(-1~1)를 프리셋 값에 더한다. 모두 0이면 프리셋 그대로."""
    P = dict(PRESETS[preset])
    a = adjust or {}
    b, w, s, c = (float(a.get(k) or 0) for k in ("bright", "warm", "sat", "sharp"))
    P["bright"] *= 1 + 0.12 * b
    P["gamma"] *= 1 - 0.18 * b
    P["warm"] = (P["warm"][0] * (1 + 0.05 * w), P["warm"][1], P["warm"][2] * (1 - 0.05 * w))
    P["vib"] = max(0.0, P["vib"] + 0.4 * s)
    P["sat"] *= 1 + 0.25 * s
    P["clarity"] = max(0.0, P["clarity"] + 0.5 * c)
    P["sharpen"] = max(0.0, P["sharpen"] + 0.6 * c)
    return P


def apply(img, preset="v1", strength=1.0, adjust=None):
    img = ImageOps.exif_transpose(img).convert("RGB")
    if preset == "none":
        return img
    P = tuned(preset, adjust)
    a = np.asarray(img)
    gain, _ = estimate_gain(a)
    x0 = a.astype(np.float32) / 255
    x = np.minimum(1, x0 * (gain * np.array(P["warm"])))
    Y = x @ np.array([.299, .587, .114], dtype=np.float32) + 1e-5
    Y2 = np.minimum(1, Y) ** P["gamma"]
    Y2 = np.where(Y2 > P["knee"], P["knee"] + (Y2 - P["knee"]) * 0.6, Y2)
    Y2 = 0.5 + (Y2 - 0.5) * P["contrast"]
    x = np.clip(x * (Y2 / Y)[..., None], 0, 1)
    if P["clarity"] or P["sharpen"]:
        L = x @ np.array([.299, .587, .114], dtype=np.float32)
        side = min(L.shape)
        L2 = L.copy()
        if P["clarity"]:
            L2 += (L - box(L, max(4, round(side * 0.02)), 3)) * P["clarity"] * 1.6
        if P["sharpen"]:
            L2 += (L - box(L, max(1, round(side / 900)), 1)) * P["sharpen"] * 1.5
        q = (np.clip(L2, 0, 1) + 1e-5) / (L + 1e-5)
        x = np.minimum(1, x * q[..., None])
    mx, mn = x.max(-1), x.min(-1)
    dl = mx - mn
    s = np.where(mx > 0, dl / np.maximum(mx, 1e-6), 0)
    s = np.minimum(1, s * (1 + P["vib"] * (1 - s)) * P["sat"])
    v = np.minimum(1, mx * P["bright"])
    f = np.where(dl[..., None] > 0,
                 v[..., None] * (1 - s[..., None] * (mx[..., None] - x) / np.maximum(dl[..., None], 1e-6)),
                 v[..., None])
    out = x0 + (f - x0) * strength
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    preset = sys.argv[3] if len(sys.argv) > 3 else "v1"
    k = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    apply(Image.open(src), preset, k).save(dst, quality=95)
