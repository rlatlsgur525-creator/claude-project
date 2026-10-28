"""비즈니스 갈래용 새 소식 수집 (네이버 뉴스 검색 API).

사용 (naver-blog 폴더에서, 컴퓨터에 따라 python3 대신 python):
  python -X utf8 tools/news_fetch.py                 # 최근 24시간, 처음 보는 기사만
  python -X utf8 tools/news_fetch.py --hours 6 --all # 6시간, 이미 본 기사도 포함

키: 네이버 개발자센터(developers.naver.com)에서 애플리케이션을 등록하고 '검색' API를 고른 뒤,
naver-blog/.env 에 아래 두 줄을 사용자가 직접 적는다 (.env 는 .gitignore 대상, 저장소에 안 올라감).
  NAVER_CLIENT_ID=...
  NAVER_CLIENT_SECRET=...
검색 API 하루 호출 한도는 25,000회 (네이버 오픈 API 목록, 2026-10-28 확인).

검색어는 tools/news_queries.txt (한 줄에 하나, # 은 주석). 결과는 news/<날짜>.md 에 덧붙이고,
본 기사 링크는 tools/.news_seen.json 에 남겨 다음 실행에서 다시 보여 주지 않는다.
외부 패키지 없음.
"""
import argparse, html, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "tools" / "news_queries.txt"
SEEN = ROOT / "tools" / ".news_seen.json"
OUT = ROOT / "news"
API = "https://openapi.naver.com/v1/search/news.json"
KST = timezone(timedelta(hours=9))


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    cid, sec = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not cid or not sec:
        sys.exit("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 없습니다. naver-blog/.env 에 적어 주세요 (파일 맨 위 설명 참고).")
    return cid, sec


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def search(query, cid, sec, display=50):
    url = API + "?" + urllib.parse.urlencode({"query": query, "display": display, "sort": "date"})
    req = urllib.request.Request(url, headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r).get("items", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=24, help="이 시간 안에 나온 기사만 (기본 24)")
    ap.add_argument("--all", action="store_true", help="이미 본 기사도 보여 준다")
    a = ap.parse_args()

    cid, sec = load_env()
    queries = [l.strip() for l in QUERIES.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.strip().startswith("#")]
    seen = set(json.loads(SEEN.read_text(encoding="utf-8"))) if SEEN.exists() else set()
    since = datetime.now(KST) - timedelta(hours=a.hours)

    found = {}
    for q in queries:
        for it in search(q, cid, sec):
            link = it.get("originallink") or it["link"]
            when = parsedate_to_datetime(it["pubDate"])
            if when < since or (link in seen and not a.all):
                continue
            row = found.setdefault(link, {"title": clean(it["title"]), "desc": clean(it["description"]),
                                          "when": when, "naver": it["link"], "queries": []})
            row["queries"].append(q)

    rows = sorted(found.items(), key=lambda kv: kv[1]["when"], reverse=True)
    now = datetime.now(KST)
    lines = [f"\n## {now:%Y-%m-%d %H:%M} 수집 (최근 {a.hours:g}시간, {len(rows)}건)\n"]
    for link, r in rows:
        lines.append(f"- {r['when'].astimezone(KST):%m-%d %H:%M} **{r['title']}**  \n"
                     f"  {r['desc'][:120]}  \n  검색어: {', '.join(r['queries'])} · {link}")
    text = "\n".join(lines) + "\n"
    print(text)

    OUT.mkdir(exist_ok=True)
    with open(OUT / f"{now:%Y-%m-%d}.md", "a", encoding="utf-8") as f:
        f.write(text)
    SEEN.write_text(json.dumps(sorted(seen | {l for l, _ in rows}), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
