"""게시물 작업실: 사진 넣기 → 역할 정하기 → 필터 조절 → 표지 문구 → 표지 5개 중 고르기 → 캡션 확인 → 릴스까지.

    python review.py                    → 가장 최근 게시물을 연다 (http://127.0.0.1:8770)
    python review.py posts/<게시물>      → 그 게시물을 연다
    python review.py --phone            → 같은 와이파이의 핸드폰에서 열 수 있는 주소(비밀 키 포함)를 찍어 준다

- 화면 위쪽에서 게시물을 바꾸거나 새로 만든다.
- 사진은 화면에서 올리거나, Claude가 posts/<게시물>/photos/ 에 넣고 brief.json 을 써 둔다.
- [표지 5개 만들기] = make_post.py 와 같다. 표지를 누르고 [확정] 하면 카드뉴스와 릴스가 만들어지고 status 가 approved 가 된다.
- /edit 은 예전 고급 편집(장마다 글자 위치·색). 표지 후보가 있는 게시물에는 쓰지 않는다.
"""
import io
import json
import mimetypes
import os
import re
import secrets
import socket
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, unquote, urlparse

from PIL import Image, ImageOps

import covers
import look
import make_post
import render

PORT = int(os.environ.get("PORT") or 8770)
POSTS = Path(__file__).resolve().parent / "posts"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
LOCK = threading.Lock()
# --phone 일 때만 와이파이에 열고, 주소에 붙은 비밀 키(첫 접속 때 쿠키로 저장)가 있어야 들어온다
TOKEN = secrets.token_urlsafe(9) if "--phone" in sys.argv else None
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIDE = 2560          # 올린 사진은 이 크기로 줄여 둔다 (카드 2배 해상도보다 조금 크게)
PREVIEW_SIDE = 900
_small = {}              # 필터 미리보기용으로 줄인 원본 (경로, 수정시각) → 이미지


def latest_post():
    ds = sorted((d for d in POSTS.iterdir() if (d / "brief.json").exists()), key=lambda d: d.stat().st_mtime)
    return ds[-1] if ds else None


CURRENT = Path(ARGS[0]).resolve() if ARGS else (latest_post() if POSTS.exists() else None)


def cur():
    if not CURRENT:
        raise ValueError("게시물을 먼저 만들어 주세요.")
    return CURRENT


def read_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write_json(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def photo_list(d):
    ph = d / "photos"
    return [f"photos/{f.name}" for f in sorted(ph.iterdir())] if ph.exists() else []


def inside(base, rel):
    """rel 이 base 폴더 안의 파일일 때만 그 경로를 돌려준다."""
    f = (base / rel).resolve()
    return f if f.is_file() and f.is_relative_to(base.resolve()) else None


def safe_stem(name):
    s = re.sub(r"[^\w가-힣-]+", "-", Path(name).stem).strip("-")[:40]
    return s or "photo"


def small(f):
    key = (str(f), f.stat().st_mtime)
    if key not in _small:
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((PREVIEW_SIDE, PREVIEW_SIDE))
        if len(_small) > 40:
            _small.clear()
        _small[key] = im
    return _small[key]


def new_post(name, area, menu):
    slug = f"{date.today().isoformat()}-{safe_stem(name)}"
    d, n = POSTS / slug, 2
    while d.exists():
        d, n = POSTS / f"{slug}-{n}", n + 1
    (d / "photos").mkdir(parents=True)
    write_json(d / "brief.json", {
        "store": {"name": name, "area": area, "address": "(주소 확인 필요)", "hours": "(영업시간 확인 필요)"},
        "area": area, "menu": menu, "hook": "",
        "quotes": ["비주얼이\n[미쳤다]..!", "진짜\n[밥도둑]..!"],
        "look": {"preset": "v1", "strength": 1.0},
        "photos": {}, "order": [], "caption": "", "hashtags": [],
    })
    return d


def save_upload(d, name, data):
    """핸드폰 사진을 바로 세우고 MAX_SIDE 로 줄여 photos/<이름>.jpg 로 저장한다."""
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        raise ValueError(f"{name}: 사진으로 열 수 없습니다. jpg·png 로 보내 주세요. (아이폰 HEIC 는 '가장 호환성 높은' 형식으로)")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    ph = d / "photos"
    ph.mkdir(exist_ok=True)
    taken = {f.stem for f in ph.iterdir()}
    stem, n = safe_stem(name), 2
    while stem in taken:
        stem, n = f"{safe_stem(name)}-{n}", n + 1
    im.save(ph / f"{stem}.jpg", quality=93)
    return f"photos/{stem}.jpg"


# 예전 고급 편집 화면 (/edit): 장마다 글자 위치·색까지 고친다
PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>맛집 게시물 검수</title>
<style>
:root{--bg:#f4f1ec;--card:#fff;--ink:#1d1b18;--mute:#7a736a;--line:#e3ddd3;--acc:#e0482a;--ok:#2f7d4f}
*{box-sizing:border-box}body{margin:0;font-family:"Pretendard","Noto Sans KR","Malgun Gothic",sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;z-index:5;background:#1d1b18;color:#fff;display:flex;gap:12px;align-items:center;padding:12px 20px;flex-wrap:wrap}
header h1{font-size:17px;margin:0 auto 0 0}header .st{font-size:13px;padding:3px 10px;border-radius:99px;background:#444}
header .st.approved{background:var(--ok)}
button{font:inherit;border:0;border-radius:8px;padding:9px 14px;cursor:pointer;background:#e9e4dc;color:var(--ink)}
button.primary{background:var(--acc);color:#fff}button.ok{background:var(--ok);color:#fff}button:disabled{opacity:.5}
main{max-width:1240px;margin:0 auto;padding:20px}
.slide{display:grid;grid-template-columns:minmax(0,440px) 1fr;gap:20px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:18px}
.slide h2{grid-column:1/-1;margin:0;font-size:15px;color:var(--mute)}
.pic{position:relative;cursor:crosshair}.pic img{width:100%;display:block;border-radius:8px}
.pic .dot{position:absolute;width:16px;height:16px;margin:-8px;border:3px solid #fff;border-radius:50%;background:var(--acc);box-shadow:0 0 0 2px #0006;pointer-events:none}
.els{display:flex;flex-direction:column;gap:10px}
.el{border:1px solid var(--line);border-radius:10px;padding:10px;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px 8px;font-size:13px}
.el.sel{border-color:var(--acc);box-shadow:0 0 0 2px #e0482a33}
.el .head{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;font-weight:600}
.el textarea{grid-column:1/-1;font:inherit;font-size:15px;padding:8px;border:1px solid var(--line);border-radius:8px;min-height:54px;resize:vertical}
.el label{display:flex;flex-direction:column;gap:2px;color:var(--mute)}
.el input,.el select{font:inherit;font-size:13px;padding:5px;border:1px solid var(--line);border-radius:6px;min-width:0;width:100%}
.el input[type=color]{padding:0;height:30px}
.el .chk{flex-direction:row;align-items:center;gap:4px}
.el .chk input{width:auto}
.tools{display:flex;gap:6px;flex-wrap:wrap}.tools button{padding:6px 10px;font-size:13px}
.x{background:none;color:var(--mute);padding:2px 6px}
.cap{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;gap:10px}
.cap textarea{font:inherit;font-size:15px;line-height:1.6;min-height:340px;padding:12px;border:1px solid var(--line);border-radius:8px}
.cap input{font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px}
.hint{font-size:13px;color:var(--mute)}
.count{font-size:12px;color:var(--mute);text-align:right}
video{width:100%;max-width:300px;border-radius:10px}
@media(max-width:760px){.slide{grid-template-columns:1fr}.el{grid-template-columns:repeat(3,minmax(0,1fr))}
  header{padding:8px 12px;gap:6px}header h1{font-size:15px;flex-basis:calc(100% - 70px)}header button{flex:1;padding:9px 8px;font-size:14px}}
</style></head><body>
<header><h1 id="title">맛집 게시물 검수</h1><span class="st" id="st"></span>
<button id="save" class="primary" title="Ctrl+S">저장하고 다시 그리기</button><button id="approve" class="ok">승인 → 릴스 생성</button></header>
<main>
<p class="hint">요소를 고른 뒤 사진을 클릭하면 그 자리로 옮겨집니다. 화살표는 클릭 = 끝점, Shift+클릭 = 시작점. 문구의 <b>[대괄호]</b>는 강조색이 됩니다.</p>
<div id="slides"></div>
<div class="cap"><h2 style="margin:0;font-size:15px">캡션</h2>
<textarea id="caption"></textarea><div class="count" id="cnt"></div>
<label class="hint">해시태그 (쉼표로 구분)<br><input id="tags" style="width:100%"></label>
<label class="hint">예약 시각 (예: 2026-10-25T12:00:00+09:00)<br><input id="sched" style="width:100%"></label>
<div id="reel"></div></div>
</main>
<script>
let post, sel = {s: 0, e: 0}, ver = Date.now();
const FONTS = {title: "표지 제목(프리텐다드 블랙)", title2: "제목(프리텐다드 엑스트라볼드)", sub: "작은 한 줄(프리텐다드)",
  bold: "굵은 제목(검은고딕)", gasoek: "가석(레트로 간판)", bagel: "베이글(통통 팝)", gugi: "구기", sunflower: "해바라기", dohyeon: "도현", round: "주아",
  dongle: "동글", gowun: "고운돋움", stylish: "스타일리시", bwpicture: "흑백사진",
  hand: "손글씨(둥근)", pen: "펜 손글씨", brush: "붓글씨", dokdo: "독도(거친 마커)", eastsea: "동해독도", singleday: "싱글데이",
  cute: "귀여운", poorstory: "푸어스토리", kirang: "기랑해랑", gamja: "감자꽃", himelody: "하이멜로디", yeonsung: "연성"};
const GRADS = {"": "단색", "#FFFDF0,#FFDD7A": "크림 노랑", "#EFFFF9,#8EF0CF": "민트", "#FFF0F5,#FF9EC4": "핑크", "#F0F7FF,#8EC5FF": "하늘"};
const BGS = {"": "없음", band: "붓띠", bubble: "말풍선", tape: "테이프", box: "반투명 상자"};
const $ = q => document.querySelector(q);

async function load() {
  post = await (await fetch('/api/post')).json();
  $('#title').textContent = (post.store?.name || '') + ' 게시물 검수';
  $('#caption').value = post.caption || '';
  $('#tags').value = (post.hashtags || []).join(', ');
  $('#sched').value = post.schedule || '';
  draw();
}
function opt(map, v) { return Object.entries(map).map(([k, t]) => `<option value="${k}" ${k == (v || '') ? 'selected' : ''}>${t}</option>`).join('') }
function draw() {
  $('#st').textContent = post.status === 'approved' ? '승인됨' : '초안';
  $('#st').className = 'st ' + (post.status || '');
  const box = $('#slides'); box.innerHTML = '';
  const n = post.slides.length;
  post.slides.forEach((s, si) => {
    const d = document.createElement('section'); d.className = 'slide';
    const els = (s.elements || []).map((e, ei) => elHtml(e, si, ei)).join('');
    const dots = (s.elements || []).map((e, ei) => {
      const p = e.type === 'arrow' ? e.to : [e.x ?? .5, e.y ?? .5];
      return (sel.s === si && sel.e === ei) ? `<span class="dot" style="left:${p[0] * 100}%;top:${p[1] * 100}%"></span>` : '';
    }).join('');
    d.innerHTML = `<h2>${si + 1} / ${n + (post.info_slide !== false ? 1 : 0)} · ${s.image}</h2>
      <div class="pic" data-s="${si}"><img src="/out/${String(si + 1).padStart(2, '0')}.jpg?v=${ver}">${dots}</div>
      <div class="els">${els}<div class="tools">
        <button data-add="text" data-s="${si}">+ 문구</button><button data-add="arrow" data-s="${si}">+ 화살표</button>
        <button data-add="pin" data-s="${si}">+ 위치핀</button><button data-add="heart" data-s="${si}">+ 하트</button>
        <button data-add="dust" data-s="${si}">+ 반짝이 가루</button><button data-add="burst" data-s="${si}">+ 집중선</button><button data-add="flame" data-s="${si}">+ 불꽃</button>
        <label class="hint" style="margin-left:auto">사진 위치 <input type="range" min="0" max="1" step=".05" value="${(s.focus || [.5, .5])[1]}" data-focus="${si}"></label>
        <select data-shade="${si}">${opt({"": "그늘 없음", top: "위쪽 어둡게", bottom: "아래쪽 어둡게"}, s.shade)}</select>
      </div></div>`;
    box.appendChild(d);
  });
  {
    const info = post.info_slide !== false;
    const d = document.createElement('section'); d.className = 'slide';
    d.innerHTML = `<h2>${info ? `${n + 1} / ${n + 1} · 가게 정보 (자동)` : '가게 정보 (캡션·예약용, 카드로는 안 나감)'}</h2>${info ? `<div><img style="width:100%;border-radius:8px" src="/out/${String(n + 1).padStart(2, '0')}.jpg?v=${ver}"></div>` : '<div></div>'}
      <div class="els">${['name', 'area', 'address', 'hours', 'closed', 'phone', 'parking'].map(k =>
        `<label class="hint">${{name: '가게명', area: '지역', address: '주소', hours: '영업시간', closed: '휴무', phone: '전화', parking: '주차'}[k]}<input data-store="${k}" value="${post.store?.[k] || ''}" style="width:100%;font:inherit;padding:6px;border:1px solid #e3ddd3;border-radius:6px"></label>`).join('')}</div>`;
    box.appendChild(d);
  }
  $('#cnt').textContent = capText().length + ' / 2200자';
  $('#reel').innerHTML = post.status === 'approved' ? `<video src="/out/reel.mp4?v=${ver}" controls></video>` : '';
}
function elHtml(e, si, ei) {
  const t = e.type || 'text', on = sel.s === si && sel.e === ei ? 'sel' : '';
  const k = `data-s="${si}" data-e="${ei}"`;
  const head = `<div class="head"><span>${{text: '문구', arrow: '화살표', pin: '위치핀', heart: '하트', sparkle: '반짝', dust: '반짝이 가루', burst: '집중선', flame: '불꽃'}[t]}</span><button class="x" data-del ${k}>삭제</button></div>`;
  if (t === 'text') return `<div class="el ${on}" ${k}>${head}
    <textarea data-f="text" ${k}>${(e.text || '').replace(/\\n/g, '\n')}</textarea>
    <label>글꼴<select data-f="font" ${k}>${opt(FONTS, e.font || 'hand')}</select></label>
    <label>크기<input type="number" data-f="size" ${k} value="${e.size || 72}"></label>
    <label>회전<input type="number" data-f="rotate" ${k} value="${e.rotate || 0}"></label>
    <label>글자색<input type="color" data-f="color" ${k} value="${e.color || '#ffffff'}"></label>
    <label>강조색<input type="color" data-f="hl" ${k} value="${e.hl || '#ffe14d'}"></label>
    <label>강조 그라데이션<select data-f="hl_grad" ${k}>${opt(GRADS, (e.hl_grad || []).join(','))}</select></label>
    <label>배경<select data-f="bg" ${k}>${opt(BGS, e.bg)}</select></label>
    <label>정렬<select data-f="align" ${k}>${opt({center: '가운데', left: '왼쪽', right: '오른쪽'}, e.align || 'center')}</select></label>
    <label>반짝<select data-f="sparkle" ${k}>${opt({"": '없음', left: '왼쪽', right: '오른쪽', both: '양쪽'}, e.sparkle)}</select></label>
    <label>테두리<input type="number" data-f="stroke" ${k} value="${e.stroke || 0}"></label>
    <label>바깥 테두리<input type="number" data-f="stroke2" ${k} value="${e.stroke2 || 0}"></label>
    <label class="chk"><input type="checkbox" data-f="heart" ${k} ${e.heart ? 'checked' : ''}>하트</label>
    <label class="chk"><input type="checkbox" data-f="underline" ${k} ${e.underline ? 'checked' : ''}>밑줄</label>
    <label>그림자<select data-f="shadow" ${k}>${opt({"true": '보통', strong: '진하게', "false": '없음'}, String(e.shadow ?? true))}</select></label></div>`;
  if (t === 'dust') return `<div class="el ${on}" ${k}>${head}
    <label>개수<input type="number" data-f="count" ${k} value="${e.count || 60}"></label>
    <label>시작(0~1)<input type="number" step=".05" data-f="from" ${k} value="${e.from ?? .5}"></label>
    <label>끝(0~1)<input type="number" step=".05" data-f="to" ${k} value="${e.to ?? 1}"></label></div>`;
  if (t === 'burst') return `<div class="el ${on}" ${k}>${head}
    <label>선 개수<input type="number" data-f="count" ${k} value="${e.count || 110}"></label>
    <label>빈 가운데 크기<input type="number" step=".05" data-f="inner" ${k} value="${e.inner ?? .42}"></label></div>`;
  if (t === 'arrow') return `<div class="el ${on}" ${k}>${head}
    <label>휘어짐<input type="number" step=".1" data-f="bend" ${k} value="${e.bend ?? .3}"></label>
    <label>굵기<input type="number" data-f="width" ${k} value="${e.width || 6}"></label>
    <label>색<input type="color" data-f="color" ${k} value="${e.color || '#ffffff'}"></label>
    <label class="chk"><input type="checkbox" data-f="loop" ${k} ${e.loop ? 'checked' : ''}>고리</label></div>`;
  return `<div class="el ${on}" ${k}>${head}
    <label>크기<input type="number" data-f="size" ${k} value="${e.size || 60}"></label>
    <label>색<input type="color" data-f="color" ${k} value="${e.color || '#e53935'}"></label></div>`;
}
function capText() { return $('#caption').value }
function el(t) { return post.slides[+t.dataset.s].elements[+t.dataset.e] }

document.addEventListener('input', ev => {
  const t = ev.target;
  if (t.dataset.f) {
    const e = el(t), f = t.dataset.f;
    let v = t.type === 'checkbox' ? t.checked : t.value;
    if (['size', 'rotate', 'stroke', 'stroke2', 'bend', 'width', 'count', 'from', 'to', 'inner'].includes(f)) v = parseFloat(v) || 0;
    if (f === 'shadow') v = v === 'strong' ? 'strong' : v === 'true';
    if (f === 'hl_grad') v = v ? v.split(',') : '';
    if (v === '' || v === false && f !== 'shadow') delete e[f]; else e[f] = v;
  } else if (t.dataset.store) { post.store[t.dataset.store] = t.value }
  else if (t.dataset.focus) { const s = post.slides[+t.dataset.focus]; s.focus = [(s.focus || [.5])[0], +t.value] }
  else if (t.dataset.shade !== undefined) { const s = post.slides[+t.dataset.shade]; if (t.value) s.shade = t.value; else delete s.shade }
  else if (t.id === 'caption') { post.caption = t.value; $('#cnt').textContent = t.value.length + ' / 2200자' }
  else if (t.id === 'tags') post.hashtags = t.value.split(',').map(x => x.trim().replace(/^#/, '')).filter(Boolean);
  else if (t.id === 'sched') post.schedule = t.value || null;
});
document.addEventListener('change', ev => { if (ev.target.dataset.shade !== undefined) ev.target.dispatchEvent(new Event('input', {bubbles: true})) });
document.addEventListener('click', ev => {
  const t = ev.target;
  const card = t.closest('.el');
  if (card && !t.closest('[data-del]') && !(sel.s == card.dataset.s && sel.e == card.dataset.e)) {
    sel = {s: +card.dataset.s, e: +card.dataset.e};
    document.querySelectorAll('.el').forEach(c => c.classList.toggle('sel', c === card));
    document.querySelectorAll('.dot').forEach(d => d.remove());
  }
  if (t.dataset.del !== undefined) { post.slides[+t.dataset.s].elements.splice(+t.dataset.e, 1); draw(); return }
  if (t.dataset.add) {
    const s = post.slides[+t.dataset.s];
    const add = {text: {text: '새 문구', size: 70, x: .5, y: .5}, arrow: {type: 'arrow', from: [.4, .4], to: [.55, .55], bend: .3},
      pin: {type: 'pin', x: .1, y: .1, size: 70}, heart: {type: 'heart', x: .5, y: .5, size: 54},
      dust: {type: 'dust', from: .55, to: 1, count: 60}, burst: {type: 'burst', x: .5, y: .5, inner: .42, count: 110, color: '#FFFFFFB0'},
      flame: {type: 'flame', x: .2, y: .45, size: 200, rotate: -12}}[t.dataset.add];
    // 배경 효과(가루·집중선·불꽃)는 글자 아래에 깔리도록 맨 앞에 넣는다
    s.elements = s.elements || [];
    if (['dust', 'burst', 'flame'].includes(add.type)) { s.elements.unshift(add); sel = {s: +t.dataset.s, e: 0}; draw(); return; }
    s.elements.push(add); sel = {s: +t.dataset.s, e: s.elements.length - 1}; draw(); return;
  }
  const pic = t.closest('.pic');
  if (pic) {
    const r = pic.getBoundingClientRect(), x = +((ev.clientX - r.left) / r.width).toFixed(3), y = +((ev.clientY - r.top) / r.height).toFixed(3);
    if (sel.s !== +pic.dataset.s) { sel = {s: +pic.dataset.s, e: 0} }
    const e = post.slides[sel.s].elements[sel.e]; if (!e) return;
    if (e.type === 'arrow') { if (ev.shiftKey) e.from = [x, y]; else e.to = [x, y] } else { e.x = x; e.y = y }
    save();
  }
});
async function save() {
  $('#save').disabled = true; $('#save').textContent = '그리는 중...';
  const r = await fetch('/api/post', {method: 'POST', body: JSON.stringify(post)});
  if (!r.ok) alert(await r.text());
  ver = Date.now(); draw(); $('#save').disabled = false; $('#save').textContent = '저장하고 다시 그리기';
}
$('#save').onclick = save;
document.addEventListener('keydown', ev => { if ((ev.ctrlKey || ev.metaKey) && ev.key === 's') { ev.preventDefault(); save() } });
$('#approve').onclick = async () => {
  if (!confirm('이대로 승인할까요? 릴스까지 만들고 예약 대기열에 올립니다.')) return;
  $('#approve').disabled = true; $('#approve').textContent = '릴스 만드는 중...';
  await fetch('/api/post', {method: 'POST', body: JSON.stringify(post)});
  const r = await fetch('/api/approve', {method: 'POST'});
  if (!r.ok) alert(await r.text()); else post.status = 'approved';
  ver = Date.now(); draw(); $('#approve').disabled = false; $('#approve').textContent = '승인 → 릴스 생성';
};
load();
</script></body></html>"""

# 작업실 화면: 사진·필터·표지 문구를 사장님이 직접 고치고, 표지 5개 중 하나를 골라 확정한다
STUDIO = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>게시물 작업실</title>
<style>
:root{--bg:#f6f3ee;--card:#fff;--line:#e3ddd3;--fg:#1d1b18;--mut:#6b655c;--acc:#e0401b;--ok:#1f7a4d;--warn:#fff4d6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,"Malgun Gothic",sans-serif}
header{position:sticky;top:0;z-index:5;background:#1d1b18;color:#fff;padding:10px 16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
header select{flex:1 1 180px;max-width:360px;font:inherit;padding:7px;border-radius:8px;border:0}
header .st{font-size:13px;padding:3px 10px;border-radius:99px;background:#444;margin-left:auto}.st.approved{background:var(--ok)}
button{font:inherit;border:0;border-radius:8px;padding:9px 14px;cursor:pointer;background:#e9e4dc;color:var(--fg)}
button:disabled{opacity:.5;cursor:default}
header button{background:#3a3631;color:#fff}
main{max-width:1100px;margin:0 auto;padding:12px 16px 60px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}
h2{font-size:16px;margin:0 0 4px}.hint{color:var(--mut);font-size:13px;margin:0 0 10px}
.photos{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.ph{border:2px solid var(--line);border-radius:10px;padding:5px;background:#faf8f5}
.ph.cur{border-color:var(--acc)}
.ph img{width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:6px;display:block;cursor:pointer}
.ph.off img{opacity:.35}
.ph select{width:100%;margin-top:5px;font:inherit;font-size:13px;padding:5px;border:1px solid var(--line);border-radius:6px}
.ph .mv{display:flex;gap:4px;margin-top:4px;align-items:center;font-size:12px;color:var(--mut)}
.ph .mv button{padding:3px 9px;font-size:13px}
.ph .tag{font-size:12px;font-weight:700;color:var(--acc)}
.up{display:inline-block;background:var(--fg);color:#fff;border-radius:8px;padding:10px 16px;cursor:pointer;margin-bottom:12px}
.up input{display:none}
.look{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}
.prev{position:relative;cursor:crosshair;align-self:start}.prev img{width:100%;display:block;border-radius:8px;background:#ddd;min-height:120px}
.prev .dot{position:absolute;width:20px;height:20px;margin:-10px;border:3px solid #fff;border-radius:50%;background:var(--acc);box-shadow:0 0 0 2px #0006;pointer-events:none}
.prev .badge{position:absolute;left:8px;top:8px;background:#000a;color:#fff;font-size:12px;padding:2px 8px;border-radius:99px}
.seg{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.seg button[aria-pressed=true]{background:var(--acc);color:#fff}
.sl{display:grid;grid-template-columns:70px 1fr 44px;align-items:center;gap:8px;margin:6px 0;font-size:14px}
.sl input{width:100%}.sl output{text-align:right;color:var(--mut);font-size:13px}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.f{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
label.t{display:flex;flex-direction:column;gap:3px;font-size:13px;color:var(--mut)}
label.t.w{grid-column:1/-1}
textarea,input[type=text]{width:100%;font:inherit;color:var(--fg);padding:9px;border:1px solid var(--line);border-radius:8px;background:#fff}
textarea.cap{min-height:280px}
.big{display:block;width:100%;margin-top:14px;padding:15px;border:0;border-radius:12px;background:var(--acc);color:#fff;font:700 17px/1.2 inherit;cursor:pointer}
.covers{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.cv{background:#faf8f5;border:3px solid transparent;border-radius:12px;padding:5px;cursor:pointer;text-align:left;font:inherit;color:inherit}
.cv img{width:100%;display:block;border-radius:8px}.cv b{display:block;padding:5px 3px 1px;font-size:14px}
.cv[aria-pressed=true]{border-color:var(--acc)}
.strip{display:flex;gap:8px;overflow-x:auto;padding:8px 0 4px}.strip img{height:170px;border-radius:8px}
.warn{background:var(--warn);border:1px solid #ecd48a;border-radius:10px;padding:10px 12px;font-size:14px;margin-bottom:10px}
.done{background:#e8f4ec;border:1px solid #b8dcc5;border-radius:12px;padding:14px;margin-top:14px}
video{width:100%;max-width:340px;display:block;margin:10px 0;border-radius:10px;background:#000}
.err{position:fixed;left:16px;right:16px;bottom:16px;z-index:9;background:#b3261e;color:#fff;padding:12px 14px;border-radius:10px;display:none}
dialog{border:0;border-radius:14px;padding:18px;width:min(420px,92vw)}dialog .f{grid-template-columns:1fr}
.empty{color:var(--mut);font-size:14px;padding:6px 0}
@media(max-width:760px){.look{grid-template-columns:1fr}.f{grid-template-columns:1fr 1fr}.covers{grid-template-columns:repeat(2,minmax(0,1fr))}
  .photos{grid-template-columns:repeat(2,minmax(0,1fr))}.strip img{height:130px}}
</style></head><body>
<header><select id="posts" aria-label="게시물"></select><button id="newBtn">+ 새 게시물</button><span class="st" id="st"></span></header>
<main id="app">
<section><h2>1. 사진</h2>
<p class="hint">사진을 올리고 쓰임을 정하세요. 표지는 <b>위 = 가게 입구</b>, <b>아래 = 대표 메뉴</b> 두 장이 들어가고, 본문 사진은 글자 없이 순서대로 넘어갑니다.</p>
<label class="up">사진 올리기<input type="file" id="file" accept="image/*" multiple></label>
<div class="photos" id="photos"></div></section>

<section><h2>2. 필터</h2>
<p class="hint">모든 사진에 같은 필터가 들어갑니다. 위 사진을 누르면 그 사진으로 미리 봅니다. 미리보기를 누르면 <b>그 지점이 화면 가운데</b>로 오도록 맞춥니다.</p>
<div class="look"><div class="prev" id="prev"><img id="pimg" alt="필터 미리보기"><span class="badge" id="pbadge">필터</span></div>
<div><div class="seg" id="presets"></div><div id="sliders"></div>
<div class="row"><button id="hold">누르는 동안 원본</button><button id="resetLook">필터 처음대로</button></div></div></div></section>

<section><h2>3. 표지 문구</h2>
<p class="hint"><b>[대괄호]</b> 안 글자는 노랑으로 강조됩니다. 말풍선은 엔터로 두 줄까지.</p>
<div class="f">
<label class="t">가게 이름<input type="text" data-k="store.name"></label>
<label class="t">지역 (표지)<input type="text" data-k="area" placeholder="전주"></label>
<label class="t">대표 메뉴<input type="text" data-k="menu" placeholder="갈비찜"></label>
<label class="t w">한 줄 문구<input type="text" data-k="hook" placeholder="푸짐한 한 냄비, [밥도둑] 인정!"></label>
<label class="t">말풍선 1<textarea rows="2" data-k="quotes.0"></textarea></label>
<label class="t">말풍선 2<textarea rows="2" data-k="quotes.1"></textarea></label>
</div>
<button class="big" id="build">표지 5개 만들기</button></section>

<section id="pickSec"><h2>4. 표지 고르기</h2>
<div id="stale" class="warn" hidden>사진·필터·문구가 바뀌었어요. <b>표지 5개 만들기</b>를 다시 눌러야 반영됩니다.</div>
<div id="coverBox"><p class="empty">아직 표지가 없어요. 위에서 <b>표지 5개 만들기</b>를 눌러 주세요.</p></div></section>

<section><h2>5. 캡션 확인</h2>
<p class="hint">주소·영업시간이 "확인 필요"로 남아 있으면 꼭 채워 주세요.</p>
<textarea class="cap" id="caption"></textarea>
<p class="hint" id="cnt" style="text-align:right;margin:4px 0 8px"></p>
<label class="t">해시태그 (쉼표로 구분)<input type="text" id="tags"></label>
<button class="big" id="go">이 표지로 확정하고 릴스 만들기</button>
<div id="result"></div></section>
</main>
<div class="err" id="err"></div>
<dialog id="dlg"><form method="dialog"><h2 style="margin-bottom:12px">새 게시물</h2><div class="f">
<label class="t">가게 이름<input type="text" name="name" required></label>
<label class="t">지역 (표지에 크게)<input type="text" name="area" placeholder="전주" required></label>
<label class="t">대표 메뉴<input type="text" name="menu" placeholder="갈비찜" required></label></div>
<div class="row" style="justify-content:flex-end;margin-top:14px"><button value="cancel" formnovalidate>취소</button><button value="ok" style="background:var(--acc);color:#fff">만들기</button></div></form></dialog>
<script>
const NAMES = __NAMES__;
const PRESETS = {v1: '맛있게 기본', jeonju: '쨍하고 선명하게', none: '필터 없음'};
const SLIDERS = [['strength', '강도', 0, 100], ['bright', '밝기', -100, 100], ['warm', '따뜻함', -100, 100],
  ['sat', '색 진하게', -100, 100], ['sharp', '선명함', -100, 100]];
const ROLES = {ext: '표지 위 · 가게 입구', sig: '표지 아래 · 대표 메뉴', body: '본문 사진', off: '안 씀'};
const $ = q => document.querySelector(q);
let S, b, pick = null, curImg = null, stale = false, saveT, prevT, ver = Date.now();

function err(m) { const e = $('#err'); e.textContent = m; e.style.display = 'block'; clearTimeout(e._t); e._t = setTimeout(() => e.style.display = 'none', 6000) }
async function api(path, body, raw) {
  const r = await fetch(path, body === undefined ? {} : {method: 'POST', body: raw ? body : JSON.stringify(body)});
  const t = await r.text();
  if (!r.ok) throw new Error(t);
  try { return JSON.parse(t) } catch { return t }
}
async function load() {
  S = await api('/api/state');
  b = S.brief; pick = S.post?.cover || null; stale = false; ver = Date.now();
  $('#posts').innerHTML = S.posts.map(p => `<option value="${p.slug}" ${p.slug === S.slug ? 'selected' : ''}>${p.name} · ${p.slug.slice(0, 10)}</option>`).join('')
    || '<option>게시물 없음</option>';
  $('#app').style.display = b ? '' : 'none';
  if (!b) { $('#dlg').showModal(); return }
  if (typeof b.look === 'string') b.look = {preset: b.look};
  b.look = {preset: 'v1', strength: 1, ...b.look};
  b.quotes = b.quotes || ['', ''];
  document.querySelectorAll('[data-k]').forEach(i => i.value = getK(i.dataset.k) || '');
  $('#caption').value = b.caption || ''; $('#tags').value = (b.hashtags || []).join(', ');
  count();
  curImg = b.photos?.signature || order()[0] || S.photos[0] || null;
  drawPhotos(); drawLook(); drawCovers(); status();
  if (S.post?.status === 'approved') showDone();
}
function getK(k) { return k.split('.').reduce((o, p) => o?.[p], b) }
function setK(k, v) { const ps = k.split('.'), last = ps.pop(); let o = b; for (const p of ps) o = o[p] = o[p] ?? (/^\d+$/.test(last) ? [] : {}); o[last] = v }

// ── 사진 역할 ──
function order() { return (b.order || []).map(o => typeof o === 'string' ? o : o.image) }
function roleOf(r) { const p = b.photos || {}; return p.exterior === r ? 'ext' : p.signature === r ? 'sig' : order().includes(r) ? 'body' : 'off' }
function drop(r) {
  const p = b.photos = b.photos || {};
  if (p.exterior === r) { delete p.exterior; delete p.exterior_crop; delete p.exterior_focus }
  if (p.signature === r) { delete p.signature; delete p.signature_focus }
  b.order = (b.order || []).filter(o => (typeof o === 'string' ? o : o.image) !== r);
}
function setRole(r, role) {
  const p = b.photos = b.photos || {};
  drop(r);
  if (role === 'ext') { if (p.exterior) drop(p.exterior); p.exterior = r }
  if (role === 'sig') { if (p.signature) drop(p.signature); p.signature = r }
  if (role === 'body') b.order.push(r);
  changed(true); drawPhotos();
}
function move(r, d) {
  const i = order().indexOf(r), j = i + d; if (j < 0 || j >= b.order.length) return;
  [b.order[i], b.order[j]] = [b.order[j], b.order[i]]; changed(true); drawPhotos();
}
function drawPhotos() {
  const sorted = [...S.photos].sort((x, y) => rank(x) - rank(y));
  $('#photos').innerHTML = sorted.map(r => {
    const role = roleOf(r), n = order().indexOf(r);
    return `<div class="ph ${r === curImg ? 'cur' : ''} ${role === 'off' ? 'off' : ''}">
      <img src="/f/${r}?v=${ver}" data-cur="${r}" alt="" loading="lazy">
      <select data-role="${r}">${Object.entries(ROLES).map(([k, t]) => `<option value="${k}" ${k === role ? 'selected' : ''}>${t}</option>`).join('')}</select>
      ${role === 'body' ? `<div class="mv"><button data-mv="${r}" data-d="-1" aria-label="앞으로">◀</button><span class="tag">본문 ${n + 1}번째</span><button data-mv="${r}" data-d="1" aria-label="뒤로">▶</button></div>`
        : role === 'off' ? '' : `<div class="mv"><span class="tag">${role === 'ext' ? '표지 위' : '표지 아래'}</span></div>`}</div>`;
  }).join('') || '<p class="empty">아직 사진이 없어요.</p>';
}
function rank(r) { const role = roleOf(r); return role === 'ext' ? -2 : role === 'sig' ? -1 : role === 'body' ? order().indexOf(r) : 999 }

// ── 필터 ──
function drawLook() {
  const L = b.look;
  $('#presets').innerHTML = Object.entries(PRESETS).map(([k, t]) => `<button data-preset="${k}" aria-pressed="${L.preset === k}">${t}</button>`).join('');
  $('#sliders').innerHTML = SLIDERS.map(([k, t, lo, hi]) => {
    const v = Math.round((L[k] ?? (k === 'strength' ? 1 : 0)) * 100);
    return `<label class="sl">${t}<input type="range" min="${lo}" max="${hi}" step="5" value="${v}" data-look="${k}" ${L.preset === 'none' ? 'disabled' : ''}><output>${v}</output></label>`;
  }).join('');
  preview();
}
function focusOf(r) {
  const p = b.photos || {};
  if (p.exterior === r) return p.exterior_focus || [.5, .3];
  if (p.signature === r) return p.signature_focus || [.5, .5];
  const o = (b.order || []).find(o => typeof o !== 'string' && o.image === r);
  return o?.focus || [.5, .5];
}
function setFocus(r, f) {
  const p = b.photos || {};
  if (p.exterior === r) p.exterior_focus = f;
  else if (p.signature === r) p.signature_focus = f;
  else { const i = order().indexOf(r); if (i < 0) return err('안 쓰는 사진은 중심을 정할 필요가 없어요.'); b.order[i] = {image: r, focus: f} }
  changed(true); preview();
}
function preview(orig) {
  if (!curImg) { $('#pimg').removeAttribute('src'); $('.prev .dot')?.remove(); return }
  clearTimeout(prevT);
  prevT = setTimeout(() => {
    $('#pimg').src = `/api/preview?img=${encodeURIComponent(curImg)}&look=${encodeURIComponent(JSON.stringify(orig ? {preset: 'none'} : b.look))}`;
    $('#pbadge').textContent = orig ? '원본' : '필터';
  }, orig ? 0 : 200);
  const role = roleOf(curImg), f = focusOf(curImg);
  $('.prev .dot')?.remove();
  if (role !== 'off') $('#prev').insertAdjacentHTML('beforeend', `<span class="dot" style="left:${f[0] * 100}%;top:${f[1] * 100}%"></span>`);
}

// ── 표지 ──
function drawCovers() {
  const P = S.post;
  $('#stale').hidden = !stale;
  if (!P?.covers) { $('#coverBox').innerHTML = '<p class="empty">아직 표지가 없어요. 위에서 <b>표지 5개 만들기</b>를 눌러 주세요.</p>'; return }
  $('#coverBox').innerHTML = `<p class="hint">하나를 누르세요.</p><div class="covers">${Object.keys(P.covers).map(k =>
    `<button class="cv" data-k="${k}" aria-pressed="${k === pick}"><img src="/f/out/covers/${k}.jpg?v=${ver}" alt="${NAMES[k] || k}"><b>${k} · ${NAMES[k] || ''}</b></button>`).join('')}</div>
    <p class="hint" style="margin-top:12px">2장부터 (글자 없이 사진만)</p><div class="strip">${P.slides.map((s, i) => `<img src="/f/out/${String(i + 2).padStart(2, '0')}.jpg?v=${ver}" alt="">`).join('')}</div>`;
}
function status() {
  const P = S.post;
  $('#st').textContent = P?.status === 'approved' && !stale ? '게시 준비 완료' : pick ? `표지 ${pick} 선택` : P?.covers ? '표지 고르는 중' : '준비 중';
  $('#st').className = 'st ' + (P?.status === 'approved' && !stale ? 'approved' : '');
}
function showDone() {
  $('#result').innerHTML = `<div class="done"><b>게시 준비가 끝났어요.</b><br>표지 ${S.post.cover} · 카드뉴스 ${S.post.slides.length + 1}장과 릴스가 만들어졌습니다. Claude에게 "예약 걸어줘"라고 말하면 시간을 확인하고 올립니다.
    <video src="/f/out/reel.mp4?v=${ver}" controls playsinline></video></div>`;
}
function count() { $('#cnt').textContent = $('#caption').value.length + ' / 2200자' }

// ── 저장 ──
function changed(look) {
  if (look && S.post?.covers) { stale = true; $('#stale').hidden = false; $('#result').innerHTML = ''; status() }
  clearTimeout(saveT); saveT = setTimeout(saveBrief, 600);
}
async function saveBrief() { clearTimeout(saveT); try { await api('/api/brief', b) } catch (e) { err('저장 실패: ' + e.message) } }

document.addEventListener('input', ev => {
  const t = ev.target;
  if (t.dataset.look) {
    const v = +t.value; t.nextElementSibling.textContent = v; b.look[t.dataset.look] = v / 100; changed(true); preview();
  } else if (t.dataset.k) { setK(t.dataset.k, t.value); changed(true) }
  else if (t.id === 'caption') { b.caption = t.value; count(); changed() }
  else if (t.id === 'tags') { b.hashtags = t.value.split(',').map(x => x.trim().replace(/^#/, '')).filter(Boolean); changed() }
});
document.addEventListener('change', ev => { if (ev.target.dataset.role) setRole(ev.target.dataset.role, ev.target.value) });
document.addEventListener('click', ev => {
  const t = ev.target;
  if (t.dataset.cur) { curImg = t.dataset.cur; drawPhotos(); preview(); return }
  if (t.dataset.mv) { move(t.dataset.mv, +t.dataset.d); return }
  if (t.dataset.preset) { b.look.preset = t.dataset.preset; changed(true); drawLook(); return }
  const cv = t.closest('.cv');
  if (cv) { pick = cv.dataset.k; document.querySelectorAll('.cv').forEach(x => x.setAttribute('aria-pressed', String(x === cv))); status(); return }
  const pv = t.closest('#prev');
  if (pv && curImg) { const r = $('#pimg').getBoundingClientRect(); setFocus(curImg, [+((ev.clientX - r.left) / r.width).toFixed(2), +((ev.clientY - r.top) / r.height).toFixed(2)]) }
});
$('#resetLook').onclick = () => { b.look = {preset: b.look.preset, strength: 1}; changed(true); drawLook() };
$('#hold').addEventListener('pointerdown', () => preview(true));
for (const e of ['pointerup', 'pointerleave']) $('#hold').addEventListener(e, () => preview());
$('#file').onchange = async ev => {
  const files = [...ev.target.files]; ev.target.value = '';
  const lbl = $('.up'); const txt = lbl.firstChild;
  for (const [i, f] of files.entries()) {
    txt.textContent = `올리는 중 ${i + 1}/${files.length}...`;
    try {
      const {rel} = await api('/api/upload?name=' + encodeURIComponent(f.name), f, true);
      S.photos.push(rel); b.order = b.order || []; b.order.push(rel); curImg = curImg || rel;
    } catch (e) { err(e.message) }
  }
  txt.textContent = '사진 올리기';
  changed(true); drawPhotos(); preview();
};
$('#build').onclick = async () => {
  const btn = $('#build'); btn.disabled = true; btn.textContent = '필터 입히고 표지 만드는 중... (30초쯤)';
  try { await saveBrief(); await api('/api/build', {}); await load(); $('#pickSec').scrollIntoView({behavior: 'smooth'}) }
  catch (e) { err(e.message) }
  btn.disabled = false; btn.textContent = '표지 5개 만들기';
};
$('#go').onclick = async () => {
  if (stale) return err('바뀐 내용이 있어요. 표지 5개 만들기를 먼저 눌러 주세요.');
  if (!pick) return err('표지를 먼저 골라 주세요.');
  const btn = $('#go'); btn.disabled = true; btn.textContent = '카드뉴스와 릴스를 만드는 중... (1분쯤)';
  try { await saveBrief(); await api('/api/pick', {cover: pick}); await load() } catch (e) { err(e.message) }
  btn.disabled = false; btn.textContent = '이 표지로 확정하고 릴스 만들기';
};
$('#posts').onchange = async ev => { await saveBrief(); await api('/api/open', {slug: ev.target.value}); load() };
$('#newBtn').onclick = () => $('#dlg').showModal();
$('#dlg').addEventListener('close', async () => {
  if ($('#dlg').returnValue !== 'ok') return;
  const fd = Object.fromEntries(new FormData($('#dlg form')));
  try { if (b) await saveBrief(); await api('/api/new', fd); await load() } catch (e) { err(e.message) }
});
load().catch(e => err(e.message));
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="text/plain; charset=utf-8", cookie=False):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", f"mk={TOKEN}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800")
        self.end_headers()
        self.wfile.write(body)

    def json(self, data):
        return self.send(200, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")

    def body(self, limit=60 << 20):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError("파일이 너무 큽니다 (60MB 까지).")
        return self.rfile.read(n)

    def allowed(self):
        if not TOKEN or self.client_address[0] in ("127.0.0.1", "::1"):   # PC 자신은 키 없이
            return True
        q = parse_qs(urlparse(self.path).query).get("k", [""])[0]
        c = SimpleCookie(self.headers.get("Cookie", ""))
        return secrets.compare_digest(q, TOKEN) or ("mk" in c and secrets.compare_digest(c["mk"].value, TOKEN))

    def do_GET(self):
        if not self.allowed():
            return self.send(403, "주소에 비밀 키가 빠졌습니다. PC에 찍힌 핸드폰 주소를 그대로 여세요.")
        u = urlparse(self.path)
        path, q = unquote(u.path), parse_qs(u.query)
        try:
            if path == "/":
                return self.send(200, STUDIO.replace("__NAMES__", json.dumps(covers.NAMES, ensure_ascii=False)),
                                 "text/html; charset=utf-8", cookie=bool(TOKEN))
            if path == "/edit":
                return self.send(200, PAGE, "text/html; charset=utf-8", cookie=bool(TOKEN))
            if path == "/api/state":
                posts = [{"slug": d.name, "name": read_json(d / "brief.json").get("store", {}).get("name", d.name)}
                         for d in sorted(POSTS.iterdir(), reverse=True) if (d / "brief.json").exists()]
                if not CURRENT:
                    return self.json({"posts": posts, "slug": None, "brief": None, "post": None, "photos": []})
                pj = CURRENT / "post.json"
                return self.json({"posts": posts, "slug": CURRENT.name, "brief": read_json(CURRENT / "brief.json"),
                                  "post": read_json(pj) if pj.exists() else None, "photos": photo_list(CURRENT)})
            if path == "/api/preview":
                f = inside(cur(), q["img"][0])
                if not f:
                    return self.send(404, "사진 없음")
                lk = make_post.look_of({"look": json.loads(q.get("look", ['"v1"'])[0])})
                im = look.apply(small(f), lk["preset"], lk["strength"], lk)
                out = io.BytesIO()
                im.save(out, "JPEG", quality=88)
                return self.send(200, out.getvalue(), "image/jpeg")
            if path.startswith("/f/"):
                f = inside(cur(), path[3:])
                if f:
                    return self.send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            # 예전 고급 편집(/edit)용
            if path == "/api/post":
                return self.send(200, (cur() / "post.json").read_bytes(), "application/json")
            if path.startswith("/out/"):
                f = inside(cur() / "out", path[5:])
                if f:
                    return self.send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        except Exception as e:
            return self.send(500, f"{type(e).__name__}: {e}")
        self.send(404, "없음")

    def do_POST(self):
        global CURRENT
        if not self.allowed():
            return self.send(403, "권한 없음")
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        try:
            with LOCK:
                if path == "/api/open":
                    d = (POSTS / json.loads(self.body())["slug"]).resolve()
                    if d.parent != POSTS or not (d / "brief.json").exists():
                        return self.send(404, "그런 게시물이 없습니다.")
                    CURRENT = d
                    return self.send(200, "ok")
                if path == "/api/new":
                    data = json.loads(self.body())
                    if not all((data.get(k) or "").strip() for k in ("name", "area", "menu")):
                        return self.send(400, "가게 이름, 지역, 대표 메뉴를 모두 적어 주세요.")
                    CURRENT = new_post(data["name"].strip(), data["area"].strip(), data["menu"].strip())
                    return self.send(200, "ok")
                if path == "/api/brief":
                    write_json(cur() / "brief.json", json.loads(self.body()))
                    return self.send(200, "ok")
                if path == "/api/upload":
                    return self.json({"rel": save_upload(cur(), q.get("name", ["photo.jpg"])[0], self.body())})
                if path == "/api/build":   # make_post.py 와 같다: 필터 → 표지 5개 → 카드
                    return self.json(make_post.main(cur()))
                if path == "/api/pick":    # 표지 확정 → 카드·릴스 만들고 게시 대기
                    data = json.loads(self.body())
                    d = cur()
                    p, b = read_json(d / "post.json"), read_json(d / "brief.json")
                    if data.get("cover") not in p.get("covers", {}):
                        return self.send(400, "표지를 먼저 골라 주세요.")
                    p["cover"], p["status"] = data["cover"], "draft"
                    p["caption"], p["hashtags"] = b.get("caption", ""), b.get("hashtags", [])
                    write_json(d / "post.json", p)
                    files = render.render_all(d)
                    render.render_reel(d, files)
                    p["status"] = "approved"
                    write_json(d / "post.json", p)
                    return self.json({"files": files})
                # 예전 고급 편집(/edit)용
                if path == "/api/post":
                    data = json.loads(self.body())
                    if data.get("status") == "approved":
                        data["status"] = "draft"   # 승인 후 다시 고치면 재승인 필요
                    write_json(cur() / "post.json", data)
                    render.render_all(cur())
                    return self.send(200, "ok")
                if path == "/api/approve":
                    files = render.render_all(cur())
                    render.render_reel(cur(), files)
                    p = read_json(cur() / "post.json")
                    p["status"] = "approved"
                    write_json(cur() / "post.json", p)
                    return self.send(200, "ok")
        except ValueError as e:     # 사장님이 고칠 수 있는 문제 (사진 빠짐 등)
            return self.send(400, str(e))
        except Exception as e:      # 화면에 그대로 띄운다
            return self.send(500, f"{type(e).__name__}: {e}")
        self.send(404, "없음")


if __name__ == "__main__":
    if ARGS and not (CURRENT / "brief.json").exists():
        sys.exit("사용법: python review.py [posts/<게시물폴더>] [--phone] [--no-open]")
    POSTS.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0" if TOKEN else "127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print(f"작업실: {url}  (끝내려면 Ctrl+C)")
    if TOKEN:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))   # 실제로 보내지는 않고, 와이파이 쪽 내 IP만 알아낸다
            ip = s.getsockname()[0]
        finally:
            s.close()
        phone = f"http://{ip}:{PORT}/?k={TOKEN}"
        print(f"핸드폰(같은 와이파이): {phone}")
        (POSTS.parent / "phone_url.txt").write_text(phone + "\n", encoding="utf-8")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    srv.serve_forever()
