"""Collect one store's week from public Naver pages (no login) into <out>/facts.json and <out>/draft.json.

Usage:
  python -I -X utf8 collect.py --place <naver.me link | place URL | place id> --name "가게 이름" \
      --start 2026-10-12 --end 2026-10-18 --out <run_dir>/<store_slug>

What it does (all read-only):
  1. Resolves the place id, reads the place home / visitor reviews / blog-cafe review pages.
  2. Keeps visitor reviews and blog posts created between --start and --end (inclusive).
  3. Opens each in-range blog post and checks its structure, sponsorship marks, hashtags.
  4. Opens the other recent blog posts too (up to 10) to count sponsored posts and posts per week.
  5. Downloads review photos and in-range blog photos into <out>/img/.
  6. Writes facts.json (raw facts) and draft.json (report skeleton; TODO fields are for the writer).
"""
import argparse, datetime as dt, html as H, json, os, re, sys, time, urllib.request

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
SPONSOR_MARKS = ["reviewnote", "리뷰노트", "체험단", "제공받", "원고료", "협찬", "revu.net", "레뷰", "강남맛집", "dinnerqueen", "디너의여왕", "지원받", "소정의"]
DISCLOSE_WORDS = ["협찬", "제공받", "체험단", "원고료", "지원받", "소정의"]
WEEKDAYS = "월화수목금토일"


def get(url, referer=None, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Referer": referer} if referer else {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                return (data, r.geturl()) if binary else (data.decode("utf-8", errors="replace"), r.geturl())
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                raise
            time.sleep(2)


def apollo(page):
    m = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\});\s*\n", page, re.S) or re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\});", page, re.S)
    if not m:
        raise SystemExit("네이버 페이지 구조를 읽지 못했습니다 (__APOLLO_STATE__ 없음).")
    return json.loads(m.group(1))


def resolve_place_id(place):
    if re.fullmatch(r"\d+", place):
        return place
    m = re.search(r"/place/(\d+)", place) or re.search(r"/(?:restaurant|cafe|hairshop|hospital|accommodation)/(\d+)", place)
    if m:
        return m.group(1)
    _, final = get(place)
    m = re.search(r"/place/(\d+)", final) or re.search(r"[?&](?:pinId|id)=(\d{5,})", final) or re.search(r"/(\d{6,})", final)
    if not m:
        raise SystemExit(f"플레이스 ID를 찾지 못했습니다: {final}")
    return m.group(1)


def kdate(d):
    return f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def parse_review_date(s, end):
    """'10.17.토' -> date, choosing the year so the date is not after end."""
    m = re.match(r"(?:(\d{2,4})\.)?(\d{1,2})\.(\d{1,2})", s or "")
    if not m:
        return None
    y = int(m.group(1)) if m.group(1) else end.year
    if y < 100:
        y += 2000
    d = dt.date(y, int(m.group(2)), int(m.group(3)))
    if not m.group(1) and d > end + dt.timedelta(days=7):
        d = d.replace(year=d.year - 1)
    return d


def parse_blog_date(item, today):
    cs = item.get("createdString")  # '26.10.18.일'
    if cs:
        d = parse_review_date(cs, today)
        if d:
            return d
    s = item.get("date") or ""
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d+)일 전", s)
    if m:
        return today - dt.timedelta(days=int(m.group(1)))
    if "시간 전" in s or "분 전" in s:
        return today
    if s.startswith("어제"):
        return today - dt.timedelta(days=1)
    return None


def text_of(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", H.unescape(t)).strip()


def analyze_post(url, menus):
    m = re.search(r"blog\.naver\.com/([^/?#]+)/(\d+)", url)
    page, _ = get(f"https://m.blog.naver.com/PostView.naver?blogId={m.group(1)}&logNo={m.group(2)}")
    raw_low = page.lower()
    page = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    comps = re.findall(r'<div class="se-component se-([a-zA-Z]+)[^"]*"(.*?)(?=<div class="se-component se-|<div class="post_footer|$)', page, re.S)
    flow, body, images, has_map = [], [], [], False
    for kind, frag in comps:
        frag = frag.split(">", 1)[1] if ">" in frag else frag  # drop the rest of the opening tag
        if kind == "quotation":
            t = text_of(frag)
            if t:
                flow.append(t if len(t) <= 14 else t[:13] + "…")
        elif kind == "text":
            body.append(text_of(frag))
        elif kind in ("image", "imageGroup", "imageStrip"):
            images += re.findall(r'data-lazy-src="([^"]+)"', frag)
        elif kind == "placesMap":
            has_map = True
    title_m = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    title = H.unescape(title_m.group(1)) if title_m else ""
    when = re.search(r"(20\d\d)\. ?(\d{1,2})\. ?(\d{1,2})\. ?(\d{1,2}):(\d\d)", page)
    text = " ".join(body)
    tags = []
    for t in re.findall(r"#([0-9A-Za-z가-힣_]+)", text):
        if t not in tags:
            tags.append(t)
    sponsor_marks = sorted({mk for mk in SPONSOR_MARKS if mk.lower() in raw_low})
    disclosed = any(w in text for w in DISCLOSE_WORDS)
    menus_hit = [mn for mn in menus if mn and mn in text]
    title_words = [w for w in re.findall(r"[가-힣]{2,}", title)]
    menus_title = [mn for mn in menus if mn and any(w in mn for w in title_words)]
    food_imgs = [u for u in images if "pstatic.net" in u or "blogfiles" in u]
    tail = text[int(len(text) * 0.7):] + " " + " ".join(flow[-2:])
    checks = [
        [bool(re.search(r"0\d{1,3}-\d{3,4}-\d{4}|영업|라스트|휴무|주소", text)), "주소·전화·영업시간 같은 가게 정보를 적음"],
        [has_map, "네이버 지도 첨부"],
        [len(flow) >= 3, f"소제목으로 단락을 나눔 ({len(flow)}개)"],
        [len(food_imgs) >= 6, f"사진 {len(food_imgs)}장"],
        [bool(re.search(r"\d{1,3},?\d{3}\s?원", text)), "가격을 적음"],
        [bool(re.search(r"총평|마무리|결론|한줄평|한 줄 평|추천합니|추천해요|추천드려", tail)), "마지막에 총평을 정리"],
        [len(tags) >= 5, f"해시태그 {len(tags)}개"],
        [len(menus_hit) >= 2, "메뉴를 2개 이상 소개" if len(menus_hit) >= 2 else f"소개한 메뉴가 {len(menus_hit)}개뿐 ({', '.join(menus_hit) or '없음'})"],
        ["주차" in text, "주차 안내" if "주차" in text else "주차 안내 없음"],
        [not sponsor_marks or disclosed, "협찬 사실을 글로 밝힘" if (sponsor_marks and disclosed) else ("체험단 표시 없음" if not sponsor_marks else "협찬 사실을 글로 밝히지 않음 (배너만 있음)")],
    ]
    return {
        "url": url, "title": title,
        "published": f"{when.group(1)}-{int(when.group(2)):02d}-{int(when.group(3)):02d} {int(when.group(4)):02d}:{when.group(5)}" if when else None,
        "flow": flow, "text": text[:6000], "hashtags": tags, "imageUrls": food_imgs,
        "hasMap": has_map, "sponsorMarks": sponsor_marks, "disclosedInText": disclosed,
        "menusMentioned": menus_hit, "menusInTitle": menus_title, "checks": checks,
    }


def download(url, path, referer):
    try:
        data, _ = get(url, referer=referer, binary=True)
        open(path, "wb").write(data)
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--from-label", default="소상공인 문제해결 프로젝트")
    a = ap.parse_args()
    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    today = dt.date.today()
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)

    pid = resolve_place_id(a.place)
    base = f"https://m.place.naver.com/place/{pid}"
    home = apollo(get(base + "/home")[0])
    vis = apollo(get(base + "/review/visitor?reviewSort=recent")[0])
    ugc = apollo(get(base + "/review/ugc?type=photoView&reviewSort=recent")[0])

    pdb = next(v for k, v in home.items() if k.startswith("PlaceDetailBase"))
    menus = []
    for k, v in home.items():
        if k.startswith("PlaceMenuItem"):
            n = re.sub(r"\(.*?\)", "", v.get("name") or "").strip()
            if n and n not in menus:
                menus.append(n)
    blog_total = 0
    for k, v in ugc.get("ROOT_QUERY", {}).items():
        if k.startswith("fsasReviews") and '"buyWithMyMoneyType":false' in k and isinstance(v, dict):
            blog_total = v.get("total") or 0
    addr = pdb.get("address") or ""
    city = (re.search(r"(\S+?)시\s", addr + " ") or re.search(r"(\S+?)시", pdb.get("roadAddress") or "") or [None, ""])[1]
    dong = (re.search(r"(\S+?[동읍면리가])\s", addr + " ") or [None, ""])[1]

    # visitor reviews in range
    reviews = []
    for k, v in vis.items():
        if not k.startswith("VisitorReview:"):
            continue
        d = parse_review_date(v.get("created") or v.get("visited"), end)
        if not d or not (start <= d <= end):
            continue
        photos = []
        for i, m in enumerate(v.get("media") or []):
            u = m.get("thumbnail")
            if not u or m.get("type") != "image":
                continue
            fn = f"visit-{d:%m%d}-{v['id']}-{i+1}.jpg"  # full id: ids from the same day share their first characters
            if download(u, os.path.join(a.out, "img", fn), "https://m.place.naver.com/"):
                photos.append("img/" + fn)
        reviews.append({
            "id": v["id"], "date": d.isoformat(), "dateLabel": kdate(d), "stars": int(v.get("rating") or 0),
            "body": v.get("body") or "", "orderedItem": (v.get("item") or {}).get("name"),
            "origin": v.get("originType"), "photos": photos,
        })
    reviews.sort(key=lambda r: r["date"])

    # blog list: all visible, in range flagged
    blog_items = []
    for k, v in ugc.items():
        if k.startswith("FsasReview:") and v.get("type") == "blog":
            d = parse_blog_date(v, today)
            blog_items.append({"date": d.isoformat() if d else None, "url": v.get("url"), "title": H.unescape(v.get("title") or ""), "author": v.get("name"), "inRange": bool(d and start <= d <= end)})
    # Naver shows only the latest ~10 posts; if the list is full, older weeks may be undercounted
    shown_oldest = min((b["date"] for b in blog_items if b["date"]), default=None)
    list_limited = len(blog_items) >= 10 and shown_oldest and shown_oldest > (start - dt.timedelta(days=35)).isoformat()
    # posts after the report week must not leak into this week's agency numbers
    blog_items = [b for b in blog_items if b["date"] and b["date"] <= end.isoformat()]
    blog_items.sort(key=lambda b: b["date"] or "", reverse=True)

    posts, sponsored = [], 0
    for idx, b in enumerate(blog_items):
        try:
            info = analyze_post(b["url"], menus)
        except Exception as e:  # noqa: BLE001
            b["error"] = str(e)
            continue
        b["sponsored"] = bool(info["sponsorMarks"])
        sponsored += b["sponsored"]
        if b["inRange"]:
            n = len(posts) + 1
            files = []
            for i, u in enumerate(info["imageUrls"]):
                fn = f"blog{n}-{i+1:02d}.jpg"
                u2 = re.sub(r"type=w\d+", "type=w773", u)
                if download(u2, os.path.join(a.out, "img", fn), "https://m.blog.naver.com/"):
                    files.append("img/" + fn)
            info.update({"date": b["date"], "author": b["author"], "localImages": files})
            posts.append(info)

    # posts per week (Mon-Sun), 6 weeks ending with the report week
    weeks = []
    for w in range(5, -1, -1):
        ws = start - dt.timedelta(days=7 * w)
        we = ws + dt.timedelta(days=6)
        n = sum(1 for b in blog_items if b["date"] and ws.isoformat() <= b["date"] <= we.isoformat())
        weeks.append({"lb": f"{ws.month}/{ws.day}주", "n": n})

    facts = {
        "store": a.name, "placeId": pid, "naverName": pdb.get("name"), "category": pdb.get("category"),
        "address": addr, "roadAddress": pdb.get("roadAddress"), "city": city, "dong": dong, "menus": menus,
        "start": a.start, "end": a.end, "checkedAt": today.isoformat(),
        "totals": {"visitor": pdb.get("visitorReviewsTotal") or 0, "blog": blog_total or pdb.get("cafeBlogReviewsTotal") or 0},
        "reviews": reviews, "posts": posts, "recentBlogs": blog_items,
        "agency": {"weeks": weeks, "recentCount": len(blog_items), "sponsoredCount": sponsored, "listLimited": bool(list_limited)},
    }
    json.dump(facts, open(os.path.join(a.out, "facts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # draft skeleton: auto fields filled, writer fields set to TODO
    iso = start.isocalendar()
    thursday = start + dt.timedelta(days=3)  # a week belongs to the month that holds its Thursday
    week_of_month = (thursday.day - 1) // 7 + 1
    draft = {
        "store": a.name, "from": a.from_label,
        "id": f"w{iso[0]}-{iso[1]:02d}",
        "label": f"{thursday.month}월 {week_of_month}주",
        "range": f"{start.month}월 {start.day}일({WEEKDAYS[start.weekday()]}) ~ {end.month}월 {end.day}일({WEEKDAYS[end.weekday()]})",
        "checkedAt": f"{today.year}년 {today.month}월 {today.day}일",
        "counts": {"visitor": len(reviews), "blog": len(posts)},
        "totals": facts["totals"],
        "score": None,
        "headline": "TODO",
        "reviews": [{
            "date": r["dateLabel"], "stars": r["stars"], "quote": "TODO", "summary": "TODO", "tags": ["TODO"],
            "photo": r["photos"][0] if r["photos"] else None, "photoCap": "TODO" if r["photos"] else None, "flag": None,
        } for r in reviews],
        "blogs": [{
            "date": (p["published"] or p["date"]),
            "title": p["title"], "author": p["author"], "url": p["url"],
            "sponsor": ("글에 체험단 표시(" + ", ".join(p["sponsorMarks"]) + ")가 있어요." + ("" if p["disclosedInText"] else " 본문에는 협찬이라는 말이 없어요.")) if p["sponsorMarks"] else None,
            "structure": {"grade": None, "tone": None, "flow": p["flow"] + (["해시태그"] if p["hashtags"] else []), "checks": p["checks"]},
            "photos": [{"src": "TODO: localImages 중 음식 사진 경로", "cap": "TODO"}],
            "summary": ["TODO"], "keywords": ["TODO"], "searchTerms": [], "searchNote": "TODO",
        } for p in posts],
        "agency": {"weeks": weeks, "verdict": "TODO", "tone": "TODO", "points": [{"tag": "TODO", "tone": "TODO", "text": "TODO"}], "asks": ["TODO"]},
    }
    json.dump(draft, open(os.path.join(a.out, "draft.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"가게: {a.name} (네이버: {pdb.get('name')}, {pdb.get('category')}, {addr})")
    print(f"기간: {a.start} ~ {a.end} | 전체 방문자 리뷰 {facts['totals']['visitor']} · 블로그 {facts['totals']['blog']}")
    print(f"기간 안 새 글: 방문자 리뷰 {len(reviews)}개, 블로그 {len(posts)}개")
    print(f"최근 블로그 {len(blog_items)}개 중 체험단 표시 {sponsored}개 | 주별: " + ", ".join(f"{w['lb']} {w['n']}" for w in weeks) + (" (목록이 10개뿐이라 앞 주는 덜 셌을 수 있음)" if list_limited else ""))
    for p in posts:
        print(f"  블로그 {p['published']} {p['title'][:40]} | 사진 {len(p['localImages'])}장 | 체험단 {p['sponsorMarks'] or '없음'}")
    if a.name.replace(" ", "") != (pdb.get("name") or "").replace(" ", ""):
        print(f"주의: 시트의 가게 이름({a.name})과 네이버 이름({pdb.get('name')})이 다릅니다. 링크가 맞는지 확인하세요.")


if __name__ == "__main__":
    main()
