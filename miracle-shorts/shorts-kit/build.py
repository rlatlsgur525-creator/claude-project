#!/usr/bin/env python3
"""Miracle Shorts render engine (ffmpeg). 9:16 shorts from an edit plan (edl.json).

  python3 build.py speech <media> [--noise -32] [--min 0.35]   -> JSON speech spans (silence-based)
  python3 build.py render <edl.json> [--preview]               -> mp4

edl.json:
{
 "out": "edit/final.mp4", "w":1080, "h":1920, "fps":30,
 "fonts": "kit/fonts",                       # dir with Pretendard-*.otf
 "segments": [                               # played in order
   {"src":"raw/a.mp4","in":2.1,"out":5.4,"fit":"crop","zoom":"punch"},
   {"src":"raw/photo.jpg","dur":3.0,"fit":"blur","zoom":"kenburns"},
   {"color":"#0e1116","dur":2.0}             # plain card (for text-only beats)
 ],                                          # fit: crop|blur ; zoom: none|punch|kenburns|out ; mute:true ; speed:1.0
 "captions": [ {"start":0.0,"end":1.8,"text":"10년 늦으면 [3억]이/사라진다?","style":"hook"} ],
                                             # times = OUTPUT timeline. [kw] = highlight, "/" = line break
                                             # style: hook (big, center) | main (lower-center) | top (label at top) | small
 "sfx":   [ {"t":0.0,"name":"impact","vol":0.8}, {"t":2.0,"src":"my.wav"} ],
 "voice": {"src":"vo.wav","vol":1.0,"offset":0},   # optional narration replacing nothing (mixed on top)
 "voices": [ {"src":"vo1.wav","offset":2.5,"vol":1.0} ],   # more narration clips (same as voice)
 "overlays": [ {"src":"logo.png","start":1.17,"end":3.0,"x":40,"y":300,"w":400,"fade":0.15},
               {"src":"clip.mp4","in":0,"start":5,"end":8,"x":0,"y":600,"w":1080,"vol":0.5} ],
                                             # image/video on top of the base (full-res px), drawn under captions
 # captions may also carry "pos":[x,y] (centre), "size":px, "color":"#RRGGBB", "layer":n
 "bgm":   {"src":"bgm.mp3","vol":0.22,"duck":true,"start":0,"fade_in":0.5,"fade_out":1.5},
 "highlight":"#FFD23F", "text":"#FFFFFF"
}
"""
import json, os, subprocess, sys, re, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.stderr.write(" ".join(cmd) + "\n" + p.stderr[-3000:]); sys.exit(1)
    return p

def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    j = json.loads(p.stdout or "{}")
    st = j.get("streams", [])
    return {"dur": float(j.get("format", {}).get("duration", 0) or 0),
            "audio": any(s["codec_type"] == "audio" for s in st),
            "video": next((s for s in st if s["codec_type"] == "video"), None)}

IMG = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp")

# ---------------- speech detection ----------------
def speech(path, noise=-32, mind=0.35):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}dB:d={mind}", "-f", "null", "-"],
                       capture_output=True, text=True)
    dur = probe(path)["dur"]; spans = []; cur = 0.0
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            s = float(m.group(1))
            if s - cur > 0.08: spans.append([round(cur, 3), round(s, 3)])
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m: cur = float(m.group(1))
    if dur - cur > 0.08: spans.append([round(cur, 3), round(dur, 3)])
    return {"duration": round(dur, 3), "speech": spans}

# ---------------- segments ----------------
def zoom_expr(zoom, dur):
    d = max(dur, 0.1)
    return {"none": "1",
            "punch": "1+0.10*min(t/0.18\\,1)",
            "kenburns": f"1+0.12*t/{d:.3f}",
            "out": f"1.12-0.12*t/{d:.3f}"}.get(zoom or "none", "1")

def seg_filter(seg, W, H, fps, dur):
    z = zoom_expr(seg.get("zoom"), dur)
    fit = seg.get("fit", "crop")
    sp = float(seg.get("speed", 1.0))
    pre = f"setpts=(PTS-STARTPTS)/{sp}," if sp != 1.0 else "setpts=PTS-STARTPTS,"
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    zoomf = (f"scale=w='trunc({W}*({z})/2)*2':h='trunc({H}*({z})/2)*2':eval=frame,crop={W}:{H}" if z != "1" else "")
    if fit == "blur":
        v = (f"[0:v]{pre}fps={fps},split[a][b];"
             f"[a]{cover},boxblur=30:2,eq=brightness=-0.08[bg];"
             f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
             f"[bg][fg]overlay=(W-w)/2:(H-h)/2" + (f",{zoomf}" if zoomf else "") + ",setsar=1,format=yuv420p[v]")
    else:
        v = f"[0:v]{pre}fps={fps},{cover}" + (f",{zoomf}" if zoomf else "") + ",setsar=1,format=yuv420p[v]"
    return v

def render_segment(seg, i, tmp, W, H, fps):
    out = os.path.join(tmp, f"seg_{i:03d}.mp4")
    if "color" in seg:
        dur = float(seg["dur"])
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={seg['color']}:s={W}x{H}:r={fps}:d={dur}",
               "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
               "-filter_complex", "[0:v]format=yuv420p,setsar=1[v]", "-map", "[v]", "-map", "1:a"]
    else:
        src = seg["src"]; is_img = src.lower().endswith(IMG)
        info = probe(src)
        if is_img:
            dur = float(seg.get("dur", 3)); inp = ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", src]
        else:
            a = float(seg.get("in", 0)); b = float(seg.get("out", info["dur"]))
            dur = (b - a) / float(seg.get("speed", 1.0))
            inp = ["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src]
        vf = seg_filter(seg, W, H, fps, dur)
        use_audio = (not is_img) and info["audio"] and not seg.get("mute")
        sp = float(seg.get("speed", 1.0))
        if use_audio:
            atempo = f"atempo={sp}," if sp != 1.0 else ""
            af = (f"[0:a]{atempo}aresample=48000,aformat=channel_layouts=stereo,"
                  f"afade=t=in:st=0:d=0.03,afade=t=out:st={max(dur-0.03,0):.3f}:d=0.03[a]")
            cmd = ["ffmpeg", "-y", *inp, "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]"]
        else:
            cmd = ["ffmpeg", "-y", *inp, "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
                   "-filter_complex", vf, "-map", "[v]", "-map", "1:a"]
    cmd += ["-t", f"{dur:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out]
    run(cmd); return out, dur

# ---------------- captions (ASS) ----------------
def ass_color(hexc, alpha="00"):
    h = hexc.lstrip("#"); r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(edl, W, H, path):
    hl = ass_color(edl.get("highlight", "#FFD23F")); tx = ass_color(edl.get("text", "#FFFFFF"))
    blk = "&H00000000"; shadow = "&H64000000"
    sty = [
        # name, font, size, align, marginV, outline
        ("hook", "Pretendard Black", 104, 5, 0, 7),
        ("main", "Pretendard ExtraBold", 76, 2, int(H * 0.30), 6),
        ("top", "Pretendard ExtraBold", 58, 8, int(H * 0.09), 5),
        ("small", "Pretendard ExtraBold", 48, 2, int(H * 0.20), 4),
    ]
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0",
             "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
             "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"]
    for n, f, s, al, mv, ol in sty:
        lines.append(f"Style: {n},{f},{s},{tx},{tx},{blk},{shadow},0,0,0,0,100,100,0,0,1,{ol},3,{al},70,70,{mv},1")
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for c in edl.get("captions", []):
        base = ass_color(c["color"]) if c.get("color") else tx
        txt = c["text"].replace("{", "(").replace("}", ")")
        txt = re.sub(r"\[(.+?)\]", lambda m: "{\\c" + hl + "}" + m.group(1) + "{\\c" + base + "}", txt)
        txt = txt.replace("/", "\\N")
        anim = c.get("anim", "pop")
        pre = {"pop": "{\\fscx82\\fscy82\\t(0,110,\\fscx100\\fscy100)}",
               "fade": "{\\fad(120,80)}", "none": ""}.get(anim, "")
        # optional per-caption overrides (full-res coords): pos [x, y] = text centre, size px, color #RRGGBB
        ov = ""
        if c.get("pos"): ov += "\\an5\\pos(%d,%d)" % (int(c["pos"][0]), int(c["pos"][1]))
        if c.get("size"): ov += "\\fs%d" % int(c["size"])
        if c.get("color"):
            ov += "\\c" + base
            h = c["color"].lstrip("#"); lum = (0.299 * int(h[0:2], 16) + 0.587 * int(h[2:4], 16) + 0.114 * int(h[4:6], 16)) / 255
            if lum < 0.4: ov += "\\3c&H00FFFFFF&\\4c&H64FFFFFF&"  # dark text → light outline/shadow so it stays readable
        if ov: pre = "{" + ov + "}" + pre
        lines.append(f"Dialogue: {int(c.get('layer', 0))},{ts(c['start'])},{ts(c['end'])},{c.get('style','main')},,0,0,0,,{pre}{txt}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

# ---------------- render ----------------
def render(edl_path, preview=False):
    edl = json.load(open(edl_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(edl_path))
    def P(p): return p if os.path.isabs(p) else os.path.join(base, p)
    for s in edl["segments"]:
        if "src" in s: s["src"] = P(s["src"])
    W, H, fps = int(edl.get("w", 1080)), int(edl.get("h", 1920)), int(edl.get("fps", 30))
    if preview: W, H = W // 2, H // 2
    out = P(edl.get("out", "final.mp4"))
    if preview: out = re.sub(r"\.mp4$", "_preview.mp4", out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fonts = P(edl.get("fonts", os.path.join(HERE, "fonts")))
    sfxdir = P(edl.get("sfx_dir", os.path.join(HERE, "sfx")))
    tmp = tempfile.mkdtemp(prefix="shorts_")
    segs = []; total = 0.0
    for i, s in enumerate(edl["segments"]):
        f, d = render_segment(s, i, tmp, W, H, fps); segs.append(f); total += d
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{f}'\n" for f in segs))
    joined = os.path.join(tmp, "joined.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    total = probe(joined)["dur"] or total
    # captions scaled for preview
    e2 = dict(edl)
    assf = os.path.join(tmp, "cap.ass")
    build_ass(e2, int(edl.get("w", 1080)), int(edl.get("h", 1920)), assf)  # full-res coords; libass scales for preview
    inputs = ["-i", joined]; fc = []; mix = ["[base]"]; idx = 1
    def fpath(p): return p.replace("\\", "/").replace(":", "\\:")  # Windows paths inside a filter graph
    # overlays (image / video on top of the base, before captions). x, y, w in full-res coords
    k = W / int(edl.get("w", 1080)); vcur = "0:v"; ov_audio = []
    for n, o in enumerate(edl.get("overlays", [])):
        src = P(o["src"]); s, e = float(o["start"]), float(o["end"]); fd = min(float(o.get("fade", 0.15)), (e - s) / 2)
        w = max(2, int(float(o.get("w", 400)) * k) // 2 * 2); x, y = int(float(o.get("x", 0)) * k), int(float(o.get("y", 0)) * k)
        if src.lower().endswith(IMG):
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", src]
            chain = f"[{idx}:v]scale={w}:-2,format=rgba"
        else:
            a = float(o.get("in", 0))
            inputs += ["-i", src]
            chain = f"[{idx}:v]trim=start={a:.3f}:duration={e - s:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB,scale={w}:-2,format=rgba"
            if float(o.get("vol", 0)) > 0 and probe(src)["audio"]:
                ov_audio.append(f"[{idx}:a]atrim=start={a:.3f}:duration={e - s:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                                f"aformat=channel_layouts=stereo,adelay={int(s * 1000)}|{int(s * 1000)},volume={o['vol']}")
        if fd > 0:
            chain += f",fade=t=in:st={s:.3f}:d={fd:.3f}:alpha=1,fade=t=out:st={e - fd:.3f}:d={fd:.3f}:alpha=1"
        fc.append(chain + f"[ov{n}]")
        fc.append(f"[{vcur}][ov{n}]overlay={x}:{y}:eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'[vo{n}]")
        vcur = f"vo{n}"; idx += 1
    fc.append(f"[{vcur}]ass='{fpath(assf)}':fontsdir='{fpath(fonts)}'[v]")
    fc.append("[0:a]aformat=channel_layouts=stereo,aresample=48000[base0]")
    # narration: legacy single "voice" or a list "voices" [{src, offset, vol}], plus overlay-video sound
    voices = ([edl["voice"]] if edl.get("voice") else []) + list(edl.get("voices", []))
    vlabels = []
    for n, vo in enumerate(voices):
        inputs += ["-i", P(vo["src"])]; ms = int(float(vo.get("offset", 0)) * 1000)
        fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={vo.get('vol',1.0)}[vc{n}]")
        vlabels.append(f"[vc{n}]"); idx += 1
    for n, ch in enumerate(ov_audio):
        fc.append(ch + f"[oa{n}]"); vlabels.append(f"[oa{n}]")
    if vlabels:
        fc.append("[base0]" + "".join(vlabels) + f"amix=inputs={len(vlabels) + 1}:normalize=0:duration=first[base1]"); basen = "base1"
    else:
        basen = "base0"
    bg = edl.get("bgm")
    if bg and bg.get("duck", True):
        fc.append(f"[{basen}]asplit=3[base][sc][sc2]")
    else:
        fc.append(f"[{basen}]asplit=2[base][sc2]")
    for s in edl.get("sfx", []):
        f = P(s["src"]) if s.get("src") else os.path.join(sfxdir, s["name"] + ".wav")
        if not os.path.exists(f): sys.stderr.write(f"skip missing sfx {f}\n"); continue
        inputs += ["-i", f]; ms = int(float(s["t"]) * 1000)
        fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={s.get('vol',0.7)}[s{idx}]")
        mix.append(f"[s{idx}]"); idx += 1
    if bg:
        inputs += ["-stream_loop", "-1", "-i", P(bg["src"])]
        st = float(bg.get("start", 0)); fo = float(bg.get("fade_out", 1.5)); fi = float(bg.get("fade_in", 0.5))
        chain = (f"[{idx}:a]atrim=start={st},asetpts=PTS-STARTPTS,atrim=0:{total:.3f},aresample=48000,"
                 f"aformat=channel_layouts=stereo,volume={bg.get('vol',0.22)},afade=t=in:st=0:d={fi},"
                 f"afade=t=out:st={max(total-fo,0):.3f}:d={fo}")
        if bg.get("duck", True):
            fc.append(chain + "[bgr]")
            fc.append("[bgr][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[bgm]")
        else:
            fc.append(chain + "[bgm]")
        mix.append("[bgm]"); idx += 1
    fc.append("[sc2]anullsink")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.7:level=false[a]")  # ~-3 dBFS: headroom for AAC overshoot on synth transients
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
           "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
           "-crf", "23" if preview else "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    run(cmd); shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"out": out, "duration": round(total, 2), "w": W, "h": H}, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 3: print(__doc__); sys.exit(0)
    if sys.argv[1] == "speech":
        a = sys.argv[2:]; noise = -32; mind = 0.35
        if "--noise" in a: noise = float(a[a.index("--noise") + 1])
        if "--min" in a: mind = float(a[a.index("--min") + 1])
        print(json.dumps(speech(a[0], noise, mind), ensure_ascii=False))
    elif sys.argv[1] == "render":
        render(sys.argv[2], "--preview" in sys.argv)
