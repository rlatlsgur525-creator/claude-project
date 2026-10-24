#!/usr/bin/env python3
"""Synthesize a small royalty-free SFX kit (48kHz stereo WAV).
usage: python3 sfx.py <out_dir>
names: whoosh pop ding impact tick riser swoosh_down cash
"""
import sys, os, wave, numpy as np
SR = 48000
rng = np.random.default_rng(7)

def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
    return e

def lowpass(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode="same")

def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1; return x / m * peak

def whoosh(d=0.45):
    n = int(SR * d); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n); seg = 512
    for i in range(0, n, seg):  # sweeping band: lowpass width shrinks -> brighter
        p = i / n; k = int(40 - 34 * p)
        out[i:i + seg] = lowpass(noise, k)[i:i + seg]
    shape = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return norm(out * shape, 0.7)

def swoosh_down(d=0.4):
    return whoosh(d)[::-1].copy()

def pop(d=0.12):
    n = int(SR * d); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 300
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(np.sin(ph) * env(n, 0.001, 0.03), 0.8)

def ding(d=1.2):
    n = int(SR * d); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318.5, 1), (2637, .35), (3955, .15), (1975.5, .25)])
    return norm(x * env(n, 0.002, 0.35), 0.6)

def impact(d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 6) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.28)
    click = lowpass(rng.standard_normal(n), 3) * env(n, 0.0005, 0.015)
    return norm(np.tanh(2.2 * (body + 0.6 * click)), 0.9)

def tick(d=0.05):
    n = int(SR * d)
    return norm(lowpass(rng.standard_normal(n), 2) * env(n, 0.0003, 0.008), 0.6)

def riser(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    f = 200 * (2 ** (3 * t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    noise = lowpass(rng.standard_normal(n), 6) * 0.6
    return norm((tone + noise) * (t / d) ** 2, 0.6)

def cash(d=0.7):
    a = ding(0.7) * 0.6; n = len(a)
    b = np.zeros(n); c = tick(0.05); b[:len(c)] += c; b[int(.06 * SR):int(.06 * SR) + len(c)] += c
    return norm(a + b, 0.7)

KIT = dict(whoosh=whoosh, pop=pop, ding=ding, impact=impact, tick=tick, riser=riser, swoosh_down=swoosh_down, cash=cash)

def write(path, x):
    x = np.clip(x, -1, 1); st = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"; os.makedirs(out, exist_ok=True)
    for k, fn in KIT.items(): write(os.path.join(out, k + ".wav"), fn())
    print("wrote", ", ".join(KIT))
