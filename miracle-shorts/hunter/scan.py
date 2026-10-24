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
