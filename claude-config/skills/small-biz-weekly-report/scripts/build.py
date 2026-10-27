"""Check every store's draft.json in a run folder, fill the score and structure grade, and write report.html.

  python -I -X utf8 build.py <run_dir>

<run_dir> holds one folder per store (each made by collect.py). Exit code 1 with a list of problems if any
draft still has TODO fields or breaks a writing rule; fix draft.json and run again.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")
TONES = {"good", "mid", "warn"}


def norm(s):
    return re.sub(r"[\s.,!~?…·'\"]+", "", s or "")


def score_for(posts, peers):
    """peers: list of other stores' post counts this week (same city and category)."""
    if len(peers) >= 5:
        below = sum(p < posts for p in peers) + 0.5 * sum(p == posts for p in peers)
        pct = round(below / len(peers) * 100)
        value = 1 if pct < 30 else 2 if pct < 50 else 3 if pct < 70 else 4 if pct < 90 else 5
        return {"value": value, "method": "pct", "peers": len(peers), "pct": pct, "posts": posts}
    value = 5 if posts >= 4 else {3: 4, 2: 3, 1: 2}.get(posts, 1)
    return {"value": value, "method": "count", "peers": len(peers) + 1, "posts": posts}


EXAMPLE = os.path.join(HERE, "..", "references", "example-draft.json")


def writer_strings(d):
    """Sentences the writer fills in (not tool-made fields)."""
    out = [d.get("headline", "")]
    for r in d.get("reviews", []):
        out += [r.get("summary") or "", r.get("flag") or ""]
    for b in d.get("blogs", []):
        out += list(b.get("summary") or []) + [b.get("searchNote") or ""]
    a = d.get("agency", {})
    out += [p.get("text", "") for p in a.get("points", []) if isinstance(p, dict)] + list(a.get("asks") or [])
    return [s for s in out if isinstance(s, str) and len(s) >= 15]


def check(d, facts, sdir):
    err = []
    example = set(writer_strings(json.load(open(EXAMPLE, encoding="utf-8"))))
    copied = [s for s in writer_strings(d) if s in example]
    if copied and not (d["store"] == "숙이네 밥상" and d["range"].startswith("10월 12일")):
        err.append("예시(example-draft.json) 문장을 그대로 썼습니다. 이번 주 사실로 다시 쓰세요: " + " / ".join(copied))
    blob = json.dumps({k: v for k, v in d.items() if not k.startswith("_")}, ensure_ascii=False)
    if "TODO" in blob:
        err.append("아직 TODO가 남아 있습니다: " + ", ".join(sorted(set(re.findall(r'"(\w+)": "TODO', blob)))))
    if len(d.get("headline", "")) > 90:
        err.append(f"headline이 {len(d['headline'])}자입니다. 90자 이하로 줄이세요.")
    for i, (r, raw) in enumerate(zip(d["reviews"], facts["reviews"])):
        tag = f"reviews[{i}] ({r['date']})"
        if r["quote"] and norm(r["quote"]) not in norm(raw["body"]):
            err.append(f"{tag} quote가 리뷰 원문에 그대로 없습니다. 원문에서 그대로 한 구절을 고르세요: {raw['body'][:80]}")
        if len(r["quote"]) > 40:
            err.append(f"{tag} quote가 {len(r['quote'])}자입니다. 40자 이하로.")
        if len(r["summary"]) > 120:
            err.append(f"{tag} summary가 {len(r['summary'])}자입니다. 120자 이하로.")
        if not 1 <= len(r["tags"]) <= 4 or any(len(t) > 10 for t in r["tags"]):
            err.append(f"{tag} tags는 1~4개, 각 10자 이하로.")
        if r.get("flag") and len(r["flag"]) > 90:
            err.append(f"{tag} flag가 너무 깁니다 (90자 이하).")
        if not raw["body"].strip() and r["quote"]:
            err.append(f"{tag} 글 없는 리뷰입니다. quote는 빈 문자열로 두세요.")
    for i, b in enumerate(d["blogs"]):
        tag = f"blogs[{i}]"
        if not 1 <= len(b["photos"]) <= 3:
            err.append(f"{tag} photos는 1~3장.")
        for p in b["photos"]:
            if not os.path.exists(os.path.join(sdir, p["src"])):
                err.append(f"{tag} 사진 파일이 없습니다: {p['src']}")
            if len(p.get("cap", "")) > 20:
                err.append(f"{tag} 사진 설명(cap)은 20자 이하로: {p.get('cap')}")
        if not 2 <= len(b["summary"]) <= 5 or any(len(x) > 70 for x in b["summary"]):
            err.append(f"{tag} summary는 2~5줄, 줄마다 70자 이하.")
        if not 4 <= len(b["keywords"]) <= 10:
            err.append(f"{tag} keywords는 4~10개.")
        if not b["searchTerms"]:
            err.append(f"{tag} searchTerms가 비었습니다. keywords.py merge를 먼저 실행하세요.")
        if len(b.get("searchNote", "")) > 160:
            err.append(f"{tag} searchNote는 160자 이하로.")
    a = d["agency"]
    if a["tone"] not in TONES:
        err.append("agency.tone은 good, mid, warn 중 하나.")
    if len(a["verdict"]) > 14:
        err.append("agency.verdict는 14자 이하 (예: '활동이 줄었어요').")
    if not 2 <= len(a["points"]) <= 4:
        err.append("agency.points는 2~4개.")
    for p in a["points"]:
        if p["tone"] not in TONES or len(p["tag"]) > 4 or len(p["text"]) > 110:
            err.append(f"agency.points '{p['tag']}': tone은 good/mid/warn, tag는 4자 이하, text는 110자 이하.")
    if not 1 <= len(a["asks"]) <= 3:
        err.append("agency.asks는 1~3개.")
    return err


def main():
    run = sys.argv[1]
    stores = []
    for name in sorted(os.listdir(run)):
        sdir = os.path.join(run, name)
        if os.path.exists(os.path.join(sdir, "draft.json")):
            stores.append((sdir, json.load(open(os.path.join(sdir, "draft.json"), encoding="utf-8")),
                           json.load(open(os.path.join(sdir, "facts.json"), encoding="utf-8"))))
    if not stores:
        sys.exit("draft.json이 있는 가게 폴더가 없습니다.")
    template = open(TEMPLATE, encoding="utf-8").read()
    problems = 0
    for sdir, d, f in stores:
        posts = d["counts"]["visitor"] + d["counts"]["blog"]
        peers = [o[1]["counts"]["visitor"] + o[1]["counts"]["blog"] for o in stores
                 if o[0] != sdir and o[2]["city"] == f["city"] and o[2]["category"] == f["category"]]
        d["score"] = score_for(posts, peers)
        for b in d["blogs"]:
            ok = sum(1 for c in b["structure"]["checks"] if c[0])
            b["structure"]["grade"], b["structure"]["tone"] = ("짜임새 좋음", "good") if ok >= 8 else ("보통", "mid") if ok >= 6 else ("짜임새 아쉬움", "warn")
        err = check(d, f, sdir)
        json.dump(d, open(os.path.join(sdir, "draft.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if err:
            problems += 1
            print(f"[고칠 것] {d['store']}")
            for e in err:
                print("  - " + e)
            continue
        data = json.dumps({k: v for k, v in d.items() if not k.startswith("_")}, ensure_ascii=False).replace("</", "<\\/")
        open(os.path.join(sdir, "report.html"), "w", encoding="utf-8").write(template.replace("/*__REPORT_DATA__*/null", data))
        s = d["score"]
        print(f"[완료] {d['store']}: 새 글 {posts}개, {s['value']}점 ({'글 개수 기준' if s['method']=='count' else f'상위 {s['pct']}%'}) -> {os.path.join(sdir, 'report.html')}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
