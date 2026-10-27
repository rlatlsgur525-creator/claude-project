"""Naver search keywords for the report.

  python -I -X utf8 keywords.py candidates <store_dir>
      Prints 20~30 candidate search keywords (one per line) built from the store's city, dong,
      category and menus. Pass them to the uplika tool research_naver_keywords.

  python -I -X utf8 keywords.py merge <store_dir> <volumes.tsv>
      volumes.tsv: one 'keyword<TAB>monthly searches' per line, copied from research_naver_keywords rows.
      Picks the top 10 by volume (store name excluded) and writes searchTerms into draft.json for every
      blog post, marking where each keyword appears: in (title/body), tag (hashtags only), miss.
"""
import json, os, re, sys


def norm(s):
    return re.sub(r"\s+", "", s or "")


def candidates(d):
    f = json.load(open(os.path.join(d, "facts.json"), encoding="utf-8"))
    city, dong, cat = f["city"], f["dong"], (f["category"] or "").split(",")[0]
    out = []
    add = lambda k: k and k not in out and out.append(k)
    for k in [f"{city}맛집", f"{city} 점심 맛집", f"{city} 저녁 맛집", f"{city}밥집", f"{city}{cat}", f"{city}{cat}맛집",
              f"{city} 혼밥", f"{city} 아침식사", f"{city} 가성비 맛집", f"{dong}맛집", f"{dong}밥집", f"{dong} 점심",
              f"{dong}{cat}", f"{dong} 맛집 추천", f"{dong} 혼밥"]:
        add(k)
    if cat in ("한식", "백반,가정식", "가정식"):
        add(f"{city} 백반"); add(f"{dong} 백반"); add(f"{city}집밥")
    for m in f["menus"][:6]:
        m = re.sub(r"\d+g|\s", "", m)
        add(f"{city}{m}"); add(f"{dong}{m}")
    for k in out[:30]:
        print(k)


def where(kw, post):
    k = norm(kw)
    if k in norm(post["title"]) and (k in norm(post["title"])):
        return "in", "제목"
    body = norm(re.sub(r"#[0-9A-Za-z가-힣_]+", " ", post["text"]))
    if k in body:
        return "in", "본문"
    if any(k == norm(t) for t in post["hashtags"]):
        return "tag", None
    return "miss", None


def merge(d, tsv):
    f = json.load(open(os.path.join(d, "facts.json"), encoding="utf-8"))
    dp = os.path.join(d, "draft.json")
    draft = json.load(open(dp, encoding="utf-8"))
    rows = []
    for line in open(tsv, encoding="utf-8"):
        parts = re.split(r"\t|,", line.strip())
        if len(parts) < 2:
            continue
        try:
            vol = int(re.sub(r"[^\d]", "", parts[1]))
        except ValueError:
            continue
        kw = parts[0].strip()
        if norm(f["store"]) in norm(kw) or norm(f["naverName"]) in norm(kw):
            continue
        rows.append((kw, vol))
    rows.sort(key=lambda r: -r[1])
    top = rows[:10]
    if len(top) < 5:
        sys.exit(f"검색량이 있는 키워드가 {len(top)}개뿐입니다. research_naver_keywords를 다시 부르거나 후보를 늘리세요.")
    for b, p in zip(draft["blogs"], f["posts"]):
        terms = []
        for kw, vol in top:
            w, note = where(kw, p)
            t = {"kw": kw, "vol": vol, "where": w}
            if note:
                t["note"] = note
            terms.append(t)
        b["searchTerms"] = terms
        inc = sum(t["where"] != "miss" for t in terms)
        print(f"{b['title'][:30]}: 상위 {len(terms)}개 중 {inc}개 포함 (태그에만 {sum(t['where']=='tag' for t in terms)}개)")
        print("  빠진 검색어: " + ", ".join(f"{t['kw']}({t['vol']:,})" for t in terms if t["where"] == "miss"))
    draft["_topSearchTerms"] = [{"kw": k, "vol": v} for k, v in top]
    json.dump(draft, open(dp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "candidates":
        candidates(sys.argv[2])
    elif cmd == "merge":
        merge(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
