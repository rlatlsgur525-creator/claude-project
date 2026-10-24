"""초안 기계 검사 (지침 v1.5 · 7장).

사용:
  python3 check_draft.py 새초안.md --prev 직전1.md 직전2.md ...   (직전 글은 최신 순)
  --publish 를 붙이면 빈칸이 남았을 때 실패 처리

초안 머리말에 아래 두 줄이 있어야 한다.
  > 메인 검색어: 노쇼 위약금 · ...
  > 얼굴: O1 / E1 / 훅=H2

본문 표시 (발행 시 시스템이 지움):
  결론 문장 줄 끝에 <!--결론-->, 범위 예고 줄 끝에 <!--범위-->
"""
import re, sys, argparse

BANNED = ["결론부터 말하면", "핵심만 먼저", "정리해볼게요", "알아보겠습니다", "꼭 확인하세요",
          "도움이 되셨길", "오늘은", "많은 분들이 궁금해하시는"]
NEXT_START = re.compile(r"^(다음 글은|다음 글에서는|다음 글에서)")


def parse(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"^## (.+)$", t, re.M)
    title = m.group(1).strip() if m else ""
    after = t[m.end():] if m else t
    body = after.split("**기준일·출처**")[0]
    kw = re.search(r"메인 검색어:\s*([^·\n]+)", t)
    face = re.search(r"얼굴:\s*(.+)", t)
    codes = {}
    if face:
        parts = [p.strip() for p in face.group(1).split("/")]
        for p in parts:
            if re.match(r"^O-?\d|^O-[a-z]", p): codes["O"] = p
            elif re.match(r"^E-?\d|^E-[a-z]", p): codes["E"] = p
            elif p.startswith("훅="): codes["훅"] = p[2:]
    tags = re.findall(r"^#[^#\s].*$", after, re.M)
    return dict(path=path, text=t, title=title, body=body,
                kw=kw.group(1).strip() if kw else None, codes=codes,
                tags=tags[-1].split() if tags else [])


def content_lines(body):
    out = []
    for l in body.split("\n"):
        s = l.strip()
        if not s or s == "---" or s.startswith("[AI") or s.startswith("[사진") or s.startswith("[도식") or s.startswith("#"):
            continue
        out.append(s)
    return out


def plain_len(body):
    b = re.sub(r"<!--.*?-->", "", body)
    b = re.sub(r"\[(사진|경험|도식)[^\]]*\]", "", b)
    b = re.sub(r"^\|[-| ]+\|$", "", b, flags=re.M)
    b = re.sub(r"[#>*|]|^---$", "", b, flags=re.M)
    return len(re.sub(r"\n+", "", b))


def first_sentence(lines):
    for s in lines:
        s = re.sub(r"[>*\"“”]", "", s).strip()
        if s and not s.startswith("<!--"):
            return s
    return ""


def last_sentence(lines):
    for s in reversed(lines):
        s = re.sub(r"[>*\"“”]|<!--.*?-->", "", s).strip()
        if s and not s.startswith("|") and not s.startswith("[") and not s.startswith("#"):
            return s
    return ""


def noun_run(title):
    # 조사·쉼표·물음표 없이 공백으로만 이어진 토큰 수 (최대)
    best = run = 0
    for tok in re.split(r"\s+", title):
        if re.search(r"[,?·+]|(과|와|을|를|이|가|은|는|에|의|로|으로|에서|하면|하니|보니)$", tok) or len(tok) > 6:
            run = 0
        else:
            run += 1
            best = max(best, run)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--prev", nargs="*", default=[])
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    d = parse(a.draft)
    prev = [parse(p) for p in a.prev]
    res = []

    def chk(name, ok, detail=""):
        res.append((name, ok, detail))

    T, B = d["title"], d["body"]
    kw = d["kw"]
    chk("머리말: 메인 검색어", kw is not None)
    chk("머리말: 얼굴 코드 (첫줄/마무리/훅)", all(k in d["codes"] for k in ["O", "E", "훅"]), str(d["codes"]))
    if kw:
        pos = T.find(kw) + 1
        chk("제목 검색어 15자 안", 0 < pos <= 15, f"{pos}자째")
        chk("본문 키워드 2~4회", 2 <= B.count(kw) <= 4, f"{B.count(kw)}회")
    chk("제목 25~40자", 25 <= len(T) <= 40, f"{len(T)}자")
    chk("제목 질문", "?" in T)
    chk("제목 명사 나열 없음 (5개 이상 연속)", noun_run(T) < 5, f"최대 {noun_run(T)}개")

    lines = content_lines(B)
    ci = next((i + 1 for i, l in enumerate(lines) if "<!--결론-->" in l), None)
    si = next((i + 1 for i, l in enumerate(lines) if "<!--범위-->" in l), None)
    chk("굵은 답 2줄째 안", ci is not None and ci <= 2 and "**" in lines[ci - 1], f"{ci}줄째" if ci else "표시 없음")
    chk("범위 예고 첫 7줄 안", si is not None and si <= 7, f"{si}줄째" if si else "표시 없음")

    secs = re.split(r"^### ", B, flags=re.M)[1:]
    bad = []
    for s in secs:
        head = s.split("\n")[0].strip()
        bodyl = s.split("\n")[1:]
        has = any(re.match(r"^\s*(\||- |\d+\. |> |✔|✓|☐|▶|[①-⑩]|\*\*Q|▸|\[ \])", l) for l in bodyl)
        if not has:
            bad.append(head)
    chk("구간마다 시각 요소", not bad, "줄글 구간: " + ", ".join(bad) if bad else f"{len(secs)}개 구간")
    numbered = [s.split("\n")[0] for s in secs if re.match(r"^\d+\.", s)]
    chk("번호 질문형 소제목 4~6개", 4 <= len(numbered) <= 6 and all("?" in h for h in numbered), f"{len(numbered)}개")
    nobold = []
    for s in secs:
        if not re.match(r"^\d+\.", s):
            continue
        first = next((l.strip() for l in s.split("\n")[1:] if l.strip() and not l.strip().startswith("[")), "")
        if not first.startswith("**"):
            nobold.append(s.split("\n")[0][:15])
    chk("구간 첫 문장 굵은 답", not nobold, ", ".join(nobold))
    faq = [s for s in secs if s.startswith("자주")]
    ok_faq = False
    if faq:
        qs = re.split(r"^\*\*Q\.", faq[0], flags=re.M)
        last = qs[-1].split("\n")[1:] if len(qs) > 1 else []
        ok_faq = any(l.strip() and not l.startswith("---") for l in last)
    chk("FAQ 마지막 Q에 답 있음", ok_faq)

    n = plain_len(B)
    chk("분량 1,700~2,800자", 1700 <= n <= 2800, f"{n}자")

    found = [b for b in BANNED if b in B]
    chk("상투어 없음", not found, ", ".join(found))

    nexts = [l for l in lines if NEXT_START.match(re.sub(r"[*>]", "", l).strip())]
    prev_next = sum(1 for p in prev[:9] if any(NEXT_START.match(re.sub(r"[*>]", "", l).strip()) for l in content_lines(p["body"])))
    chk("'다음 글은' 시작 문장 10편에 1번 이하", len(nexts) + prev_next <= 1, f"이번 {len(nexts)}, 직전 9편 {prev_next}")

    ga = len(re.findall(r"^\*[^*\n]+:[^*\n]+\*$", B, re.M))
    chk("기울임 풀이 줄 2번 이하", ga <= 2, f"{ga}번")

    fs, ls = first_sentence(lines), last_sentence(lines)
    for code, k, lim in [("첫 줄", "O", 3), ("마무리", "E", 3), ("제목 훅", "훅", 2)]:
        same = [p["path"] for p in prev[:lim] if p["codes"].get(k) and p["codes"].get(k) == d["codes"].get(k)]
        chk(f"{code} 코드 직전 {lim}편과 다름", not same, ", ".join(same))
    f6 = [p["path"] for p in prev[:10] if first_sentence(content_lines(p["body"]))[:6] == fs[:6]]
    l8 = [p["path"] for p in prev[:10] if last_sentence(content_lines(p["body"]))[-8:] == ls[-8:]]
    chk("첫 문장 앞 6자 직전 10편과 다름", not f6, f"'{fs[:6]}' " + ", ".join(f6))
    chk("끝 문장 끝 8자 직전 10편과 다름", not l8, f"'{ls[-8:]}' " + ", ".join(l8))

    chk("태그 10개 이하", len(d["tags"]) <= 10, f"{len(d['tags'])}개")
    fake = re.search(r"가상 시나리오:\s*예", d["text"]) is not None
    chk("가상 시나리오 아님" if a.publish else "가상 시나리오 (초안 단계 참고)", not fake or not a.publish, "예" if fake else "아니오")
    blanks = len(re.findall(r"\[(경험|숫자)", B))
    chk("빈칸 0" if a.publish else "빈칸 (초안 단계 참고)", blanks == 0 or not a.publish, f"{blanks}곳")
    urls = re.findall(r"https?://\S+", d["text"].split("## 이미지 계획")[0])
    shop = [u for u in urls if not re.search(r"go\.kr|law\.go|naver\.com/(service|notices)|smartplace\.naver|korea\.kr|help\.naver", u)]
    chk("상업 링크 0 (허용 도메인 밖 링크)", not shop, ", ".join(shop))

    fails = 0
    for name, ok, det in res:
        fails += (not ok)
        print(("통과 " if ok else "실패 ") + name + (f"  [{det}]" if det else ""))
    print(f"\n결과: {len(res) - fails}/{len(res)} 통과" + (" → 제출 불가" if fails else " → 제출 가능"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
