---
name: shorts-format-hunter
description: 주제와 상관없이 작은 채널에서 크게 터진 쇼츠(아웃라이어)를 유튜브 API로 찾아 포맷을 해부하고, 미라클톡·소상공인 주제로 이식 가능한지 판정할 때 사용. '포맷 찾아줘', '아웃라이어 스캔', '/shorts-format-hunter', 유튜브 쇼츠 링크 분석 요청에 사용.
---

# 쇼츠 포맷 헌터

**원칙:** 내 주제에서 잘 된 영상을 찾지 않는다. 주제와 무관하게 **포맷 자체가 터진 영상**을 먼저 찾고, 그 다음에 신혁의 주제(① 미라클톡: 경제·연금·보험, 20~40대 대상 ② 소상공인 고객 홍보)를 그 틀에 넣을 수 있는지 본다. 제작은 `miracle-shorts` 스킬로 넘긴다.

흐름: **① 스캔 → ② 포맷 해부 → ③ 포맷 검증 → ④ 이식 판정 → ⑤ 제작 브리프**

## 0. 준비

- **API 키:** 신혁에게 YouTube Data API 키를 받는다. 키는 메모리나 파일에 저장하지 않고 세션 환경변수로만 쓴다: `export YT_KEY=...`. 이 대화에서 이미 받았으면 다시 묻지 않는다.
- **접속 확인:** `curl -s -o /dev/null -w "%{http_code}" "https://www.googleapis.com/youtube/v3/videos?part=id&id=x&key=$YT_KEY"`
  - 403이나 연결 거부가 나면 이렇게 안내하고 멈춘다: "claude.ai 웹 → 설정 → 기능에서 `googleapis.com`, `i.ytimg.com`을 허용한 뒤 새 작업에서 다시 불러주세요"
- **스캐너:** 부록의 `scan.py`를 Write로 `~/hunter/scan.py`에 저장한다. 이미 있으면 건너뛴다.
- **할당량:** 하루 10,000포인트. 기본 스캔 1회에 약 3,000~4,500을 쓴다. 검색 1회가 100포인트이고, 나머지 조회는 50개당 1포인트다. 초기화는 한국 시간 오후 4~5시(미국 태평양 자정)다. 쓴 양은 결과의 `quota_used`로 알려준다.

## 1. 스캔 (아웃라이어 발굴)

```bash
cd ~/hunter && python3 scan.py --out hunt_$(date +%m%d)          # 한국, 최근 90일, 15개 카테고리 전체
python3 scan.py --cats 22,24,26,27 --days 30 --out hunt_x        # 카테고리·기간 좁히기
python3 scan.py --q "자영업" --out hunt_q                          # 특정 검색어 (주제 탐색이 아니라 장르 탐색용)
python3 scan.py --region US --lang en --out hunt_us               # 해외 포맷 (한국에 아직 안 들어온 틀 찾기)
```

기본 기준: 3분 이하, 조회 20만 이상, 구독자 50만 이하, **구독자 대비 50배 이상**, **채널 최근 쇼츠 중앙값 대비 10배 이상**. 점수는 채널 평균 대비 배수에 가장 큰 가중치를 준다. 평소보다 훨씬 터졌다는 건 사람이 아니라 포맷 덕분일 가능성이 높다는 뜻이기 때문이다.

결과(`outliers.md/csv/json`)에서 상위 15~20개를 표로 보여준다. 각 영상에는 **한 줄 포맷 추정**을 붙인다. 제목과 썸네일을 보고 "어떤 틀인지"를 추정하는 것이다. 썸네일은 `curl -s -o t.jpg <thumb>`로 받아 Read로 본다.

그다음 신혁이 고르게 하거나, "알아서"라고 하면 **틀이 서로 다른 상위 5개**를 골라 2단계로 넘긴다. 같은 틀이 여러 개면 그 자체로 검증 신호이므로 묶어서 한 번만 해부한다.

걸러낼 것은 다음과 같다. 이런 영상은 포맷이 아니라 다른 요인이 조회수를 만든 경우다.
- 유명인·아이돌 출연
- 뉴스 속보
- 음원 챌린지 (음원 자체가 조회수를 만든 경우)
- 원본 영상을 재업로드한 클립 계정

## 2. 포맷 해부

영상마다 아래를 모은다.
- **장면 분석:** Higgsfield `video_analysis_create`에 `youtube_url`을 넣고 `video_analysis_status`로 완료를 기다린다. 3~5분 걸린다. 크레딧이 드는지 처음에 한 번 확인한다.
- **첫 화면:** 썸네일과 첫 장면 설명을 보고 "소리 없이도 무슨 얘기인지 보이는가"를 판단한다.
- **댓글 상위 20개:** `commentThreads?part=snippet&videoId=ID&order=relevance&maxResults=20` (1포인트). 사람들이 왜 반응했는지가 가장 솔직하게 드러난다. 무엇에 놀랐는지, 무엇을 공유하고 싶어했는지, 무엇에 공감했는지를 본다.
- **제목·설명·태그**

이걸로 **포맷 카드**를 쓴다.

```
## [포맷 이름: 6~12자, 틀을 설명하는 이름]  예: "숨은 숫자 공개형"
- 레퍼런스: 제목 (링크) — 조회 / 구독자 / 채널 평균 대비 N배
- 틀 (주제 제거): "[익숙한 것]의 [숨겨진 숫자]를 공개 → [예상 밖 결과] → [한 줄 반전]"
- 왜 터졌나 (댓글 근거): 2~3줄
- 훅: 유형(질문/충격 숫자/결과 먼저/공감 상황/도발) + 첫 화면 구성 + 첫 대사
- 구조 비트: 0~2초 훅 / 2~5초 예고 / … / 보상 위치 / 끝내는 방식
- 편집: 길이, 컷 수, 평균 컷 길이, 자막 스타일, 효과음 밀도, BGM 분위기
- 화면 구성: 얼굴 출연 / 손·물건 / B롤 / 그래픽 / 화면 녹화 비율
- 제작 방식: 실사 촬영 / 스톡 / AI 생성 / 모션그래픽 — 혼자 폰으로 가능한가
- 핵심 장치: 이 포맷을 이 포맷이게 만드는 단 하나 (예: "마지막 숫자를 끝까지 숨김")
```

## 3. 포맷 검증

한 영상만 터졌다면 운일 수 있다. 다음 두 가지로 확인한다.
- 같은 틀을 설명하는 검색어 2~3개로 `scan.py --q "..." --min-mult 5`를 돌린다(각 100~300포인트). 다른 채널에서도 같은 틀이 평균의 5배 이상 나왔는지 본다.
- 해외판(`--region US --lang en`)에서도 같은 틀이 보이면 더 강한 신호다.

판정은 세 단계다.
- **검증됨:** 다른 채널 2개 이상에서도 터짐
- **유망:** 1개에서 더 터짐
- **단발:** 운일 수 있음

## 4. 이식 판정

틀의 빈칸에 신혁의 주제를 넣어 **미라클톡 예시 2개, 소상공인 예시 1개**를 실제 제목과 첫 대사 수준으로 만든다. 그다음 1~5점으로 매긴다.

| 기준 | 가중치 | 질문 |
|---|---|---|
| 훅 이식성 | ×3 | 주제를 바꿔도 핵심 장치가 그대로 작동하는가. 원본이 '음식'이나 '동물'이라서 터진 거면 1점 |
| 제작 가능성 | ×2 | 신혁 혼자 폰과 이 작업공간 도구로 만들 수 있는가 (AI 생성이 필요하면 비용까지) |
| 타깃 적합 | ×2 | 20~40대가 멈춰서 볼 이유가 있는가 / 가게 손님이 반응할까 |
| 반복성 | ×1 | 이 틀로 주제만 바꿔 10편 이상 나오는가 |
| 준법 | 통과/불가 | 미라클톡: 수익률 보장·단정·상품명 홍보 없이 가능한가. 불가면 미라클톡 이식은 탈락 |

판정 기준(만점 40점):
- **32점 이상:** 바로 제작
- **24~31점:** 조건부. 무엇을 바꾸면 되는지 적는다
- **23점 이하:** 패스

점수만 주지 말고 **가장 약한 고리 한 줄**을 함께 쓴다.

## 5. 제작 브리프 → miracle-shorts

"바로 제작"이나 조건부 승인이 나면 브리프를 만든다. 구조 비트별 초, 컷 수, 각 컷의 화면(촬영할 것 / 이미지 생성할 것), 자막 문구와 강조 단어, 효과음 위치, BGM 분위기를 담는다. 실사형이면 신혁이 찍을 **샷 리스트와 대본**도 준다.

브리프가 준비되면 `miracle-shorts` 스킬로 넘긴다. 브리프의 구조는 miracle-shorts의 edl.json(segments / captions / sfx / bgm)에 그대로 옮겨 적을 수 있게 맞춘다.

**저작권:** 가져오는 건 틀뿐이다. 원본의 대본 문장, 영상, 음원, 썸네일 디자인은 그대로 쓰지 않는다.

## 6. 결과 전달과 누적

- 스캔 표와 포맷 카드는 답장에 요약한다. 전체 카드는 `format_cards_<날짜>.md` 파일로 SendUserFile한다. `outliers.csv`도 함께 보낸다.
- 신혁이 원하면 포맷 카드를 모으는 **포맷 라이브러리** 페이지(Artifact, db 기능)를 만들어 쌓는다. 그 전에는 파일로 전달한다.
- 다음에 해볼 것 하나를 제안한다. 예: "해외판 스캔으로 국내에 아직 없는 틀 찾기"

## 부록 — ~/hunter/scan.py

```python
#!/usr/bin/env python3
"""Shorts outlier scanner (YouTube Data API v3). Topic-agnostic: finds shorts that blew up
relative to their channel, so the FORMAT (not the creator) is likely the reason.

usage:
  YT_KEY=... python3 scan.py [--region KR] [--lang ko] [--days 90] [--pages 2]
                             [--cats all|1,22,24] [--q "검색어"] [--min-mult 10] [--min-ratio 50]
                             [--max-subs 500000] [--out out_dir]
outputs: out_dir/outliers.json, outliers.csv, outliers.md   (sorted by score)
quota (default, all 15 categories x 2 pages): ~3,000-4,500 of 10,000 daily units.
"""
import argparse, csv, json, math, os, re, statistics, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

API = "https://www.googleapis.com/youtube/v3/"
CATS = {"1": "영화/애니", "2": "자동차", "10": "음악", "15": "동물", "17": "스포츠", "19": "여행",
        "20": "게임", "22": "인물/블로그", "23": "코미디", "24": "엔터", "25": "뉴스/정치",
        "26": "노하우/스타일", "27": "교육", "28": "과학기술", "29": "비영리"}
UNITS = {"search": 100, "videos": 1, "channels": 1, "playlistItems": 1}
used = 0

def get(ep, **params):
    global used
    params["key"] = os.environ["YT_KEY"]
    url = API + ep + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                used += UNITS.get(ep, 1)
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf8", "ignore")
            if e.code == 403 and "quota" in body.lower():
                sys.exit("QUOTA_EXCEEDED: daily quota used up. Try again after 17:00 KST (midnight PT).")
            if e.code in (500, 503) and attempt < 2: time.sleep(2); continue
            sys.stderr.write(f"HTTP {e.code} {ep}: {body[:300]}\n"); return {}
        except Exception as e:
            if attempt < 2: time.sleep(2); continue
            sys.stderr.write(f"ERR {ep}: {e}\n"); return {}

def iso_dur(s):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m: return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se

def chunks(xs, n=50):
    for i in range(0, len(xs), n): yield xs[i:i + n]

def videos_info(ids):
    out = {}
    for c in chunks(list(ids)):
        j = get("videos", part="snippet,statistics,contentDetails", id=",".join(c), maxResults=50)
        for it in j.get("items", []):
            s = it.get("statistics", {}); sn = it["snippet"]
            out[it["id"]] = {"id": it["id"], "title": sn["title"], "channelId": sn["channelId"],
                             "channel": sn["channelTitle"], "published": sn["publishedAt"],
                             "categoryId": sn.get("categoryId"), "tags": sn.get("tags", [])[:8],
                             "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                             "dur": iso_dur(it["contentDetails"].get("duration")),
                             "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0) or 0),
                             "comments": int(s.get("commentCount", 0) or 0)}
    return out

def channels_info(ids):
    out = {}
    for c in chunks(list(ids)):
        j = get("channels", part="statistics,contentDetails,snippet", id=",".join(c), maxResults=50)
        for it in j.get("items", []):
            s = it["statistics"]
            out[it["id"]] = {"subs": None if s.get("hiddenSubscriberCount") else int(s.get("subscriberCount", 0)),
                             "videoCount": int(s.get("videoCount", 0)), "title": it["snippet"]["title"],
                             "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]}
    return out

def channel_baseline(uploads, exclude):
    """median views of the channel's recent shorts (<=180s), excluding the outlier itself"""
    j = get("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50)
    ids = [it["contentDetails"]["videoId"] for it in j.get("items", []) if it["contentDetails"]["videoId"] != exclude]
    if not ids: return None, 0
    info = videos_info(ids)
    vs = [v["views"] for v in info.values() if 0 < v["dur"] <= 180]
    if len(vs) < 3: vs = [v["views"] for v in info.values()]
    return (statistics.median(vs) if vs else None), len(vs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="KR"); ap.add_argument("--lang", default="ko")
    ap.add_argument("--days", type=int, default=90); ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--cats", default="all"); ap.add_argument("--q", default="")
    ap.add_argument("--min-mult", type=float, default=10); ap.add_argument("--min-ratio", type=float, default=50)
    ap.add_argument("--max-subs", type=int, default=500000); ap.add_argument("--min-views", type=int, default=200000)
    ap.add_argument("--out", default="hunt"); a = ap.parse_args()
    if not os.environ.get("YT_KEY"): sys.exit("set YT_KEY")
    os.makedirs(a.out, exist_ok=True)
    after = (datetime.now(timezone.utc) - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cats = list(CATS) if a.cats == "all" else [c.strip() for c in a.cats.split(",")]
    found = {}
    for cat in cats + ([None] if a.q else []):
        token = None
        for _ in range(a.pages):
            p = dict(part="id", type="video", videoDuration="short", order="viewCount", maxResults=50,
                     regionCode=a.region, relevanceLanguage=a.lang, publishedAfter=after)
            if cat and not a.q: p["videoCategoryId"] = cat
            if a.q: p["q"] = a.q
            if token: p["pageToken"] = token
            j = get("search", **p)
            for it in j.get("items", []):
                found.setdefault(it["id"]["videoId"], cat)
            token = j.get("nextPageToken")
            if not token: break
        if a.q: break
    vids = videos_info(found)
    vids = {k: v for k, v in vids.items() if 0 < v["dur"] <= 180 and v["views"] >= a.min_views}
    chans = channels_info({v["channelId"] for v in vids.values()})
    rows = []
    for v in vids.values():
        c = chans.get(v["channelId"]);
        if not c: continue
        subs = c["subs"]
        if subs is not None and subs > a.max_subs: continue
        ratio = v["views"] / max(subs, 1) if subs else None
        if ratio is not None and ratio < a.min_ratio: continue
        rows.append({**v, "subs": subs, "ratio": ratio, "uploads": c["uploads"]})
    # baseline only for survivors (cheap: 2 units each)
    out = []
    for r in sorted(rows, key=lambda r: -(r["ratio"] or 0))[:150]:
        base, n = channel_baseline(r["uploads"], r["id"])
        mult = r["views"] / base if base else None
        if mult is not None and mult < a.min_mult: continue
        age = max((datetime.now(timezone.utc) - datetime.fromisoformat(r["published"].replace("Z", "+00:00"))).days, 1)
        score = (math.log10(mult or 1) * 2 + math.log10(r["ratio"] or 1) + math.log10(max(r["views"], 1)) * 0.5
                 + (0.3 if age <= 30 else 0))
        out.append({"score": round(score, 2), "id": r["id"], "url": f"https://www.youtube.com/shorts/{r['id']}",
                    "title": r["title"], "channel": r["channel"], "category": CATS.get(r["categoryId"], r["categoryId"]),
                    "views": r["views"], "subs": r["subs"], "ratio": round(r["ratio"], 1) if r["ratio"] else None,
                    "channel_median": int(base) if base else None, "multiple": round(mult, 1) if mult else None,
                    "baseline_n": n, "dur": r["dur"], "age_days": age, "likes": r["likes"], "comments": r["comments"],
                    "like_rate": round(r["likes"] / max(r["views"], 1) * 100, 2),
                    "thumb": f"https://i.ytimg.com/vi/{r['id']}/hqdefault.jpg", "tags": r["tags"]})
    out.sort(key=lambda x: -x["score"])
    json.dump({"scanned_at": datetime.now().isoformat(timespec="minutes"), "params": vars(a),
               "quota_used": used, "searched": len(found), "outliers": out},
              open(os.path.join(a.out, "outliers.json"), "w"), ensure_ascii=False, indent=1)
    keys = ["score", "url", "title", "channel", "category", "views", "subs", "ratio", "channel_median", "multiple",
            "dur", "age_days", "like_rate"]
    with open(os.path.join(a.out, "outliers.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    def k(n): return "-" if n is None else (f"{n/10000:.1f}만" if n >= 10000 else f"{n:,}")
    md = ["| # | 영상 | 채널 | 조회 | 구독자 | 구독자 대비 | 채널 평균 대비 | 길이 |", "|---|---|---|---|---|---|---|---|"]
    for i, o in enumerate(out[:40], 1):
        md.append(f"| {i} | [{o['title'][:40]}]({o['url']}) | {o['channel'][:16]} | {k(o['views'])} | {k(o['subs'])} | "
                  f"{o['ratio'] or '-'}배 | {o['multiple'] or '-'}배 | {o['dur']}초 |")
    open(os.path.join(a.out, "outliers.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(json.dumps({"searched": len(found), "shorts_checked": len(vids), "outliers": len(out), "quota_used": used,
                      "out": os.path.abspath(a.out)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
```
