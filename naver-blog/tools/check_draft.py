"""초안 기계 검사 (지침 v1.6 · 0-1장 규칙 등급, 7장 체크리스트).

사용 (컴퓨터에 따라 python3 대신 python):
  python3 tools/check_draft.py 새초안.md --prev 직전1.md 직전2.md ...   (직전 글은 최신 순)
  --publish 를 붙이면 발행 모드: 빈칸·자리표시·가상 시나리오·사실 검증 미완료가 필수 실패가 된다

결과 등급 (v1.6):
  필수 실패  발행 보류. 하나라도 있으면 종료 코드 1
  권고       형식 권장 사항. 글 유형상 벗어날 이유가 있으면 이유를 적고 넘어간다 (종료 코드에 영향 없음)
  정보       참고용 숫자
  사람 확인  스크립트가 판정할 수 없는 항목. 자동 통과로 치지 않는다

초안 머리말:
  > 메인 검색어: 노쇼 위약금 · ...          (필수)
  > 글 유형: 질문답변 | 비교 | 실험 | 사례 | 체크리스트   (권고)
  > 얼굴: O1 / E1 / 훅=H2                   (권고)
  > 사실 검증: fact_checks/파일.md          (발행 모드 필수)

본문 표시 (발행 시 시스템이 지움):
  결론 문장 줄 끝에 <!--결론-->, 범위 예고 줄 끝에 <!--범위-->
"""
import re, sys, argparse
from pathlib import Path

BANNED = ["결론부터 말하면", "핵심만 먼저", "정리해볼게요", "알아보겠습니다", "꼭 확인하세요",
          "도움이 되셨길", "오늘은", "많은 분들이 궁금해하시는"]
NEXT_START = re.compile(r"^(다음 글은|다음 글에서는|다음 글에서)")
TYPES = ["질문답변", "비교", "실험", "사례", "체크리스트"]
# 질문형 번호 소제목·FAQ는 실험형·사례형의 흐름(조건→결과, 문제→조치→결과)과 맞지 않을 수 있다
LOOSE_HEADINGS = {"실험", "사례"}
PLACEHOLDER = re.compile(r"^\s*\[(사진|도식|AI 일러스트|📷)")
BLOCKING_STATUS = ["미확인", "출처 충돌"]
HUMAN_CHECKS = [
    "제목이 약속한 질문에 본문이 답하는가",
    "중요한 법·제도·숫자 주장이 사실 검증표에서 '확인 완료'인가 (원문을 직접 본 것만)",
    "계산 예시와 도식 속 숫자가 본문과 일치하는가",
    "경험 문장이 실제 상담·방문에서 나온 것인가 (빈칸을 지웠다고 경험이 생기지 않는다)",
    "개인정보·저작권·이미지 사용 권한에 문제가 없는가",
    "보험·금융 주제의 준법 확인 (상품 권유·단정 표현 없음)",
]


def parse(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"^## (.+)$", t, re.M)
    title = m.group(1).strip() if m else ""
    after = t[m.end():] if m else t
    body = after.split("**기준일·출처**")[0]
    kw = re.search(r"메인 검색어:\s*([^·\n]+)", t)
    face = re.search(r"얼굴:\s*(.+)", t)
    typ = re.search(r"^> 글 유형:\s*(\S+)", t, re.M)
    fc = re.search(r"^> 사실 검증:\s*(\S+)", t, re.M)
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
                type=typ.group(1).strip() if typ else None,
                factcheck=fc.group(1).strip() if fc else None,
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


def find_factcheck(ref, draft_path):
    for base in [Path(draft_path).resolve().parent, Path(__file__).resolve().parent.parent]:
        p = base / ref
        if p.exists():
            return p
    return None


def factcheck_rows(path):
    """사실 검증표에서 (주장 ID, 검증 상태) 목록을 읽는다. '검증 상태' 열이 있는 표만 본다."""
    rows, col = [], None
    for l in open(path, encoding="utf-8").read().split("\n"):
        if not l.strip().startswith("|"):
            col = None
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if "검증 상태" in cells:
            col = cells.index("검증 상태")
            continue
        if col is None or re.match(r"^[-: ]+$", "".join(cells)) or len(cells) <= col:
            continue
        rows.append((cells[0], cells[col]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--prev", nargs="*", default=[])
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    d = parse(a.draft)
    prev = [parse(p) for p in a.prev]
    res = []

    def chk(level, name, ok, detail=""):
        res.append((level, name, ok, detail))

    T, B = d["title"], d["body"]
    kw = d["kw"]
    typ = d["type"]
    loose = typ in LOOSE_HEADINGS

    # ── 필수: 메타데이터와 실제 글의 일치
    chk("필수", "제목 줄 (## 제목)", bool(T))
    chk("필수", "머리말: 메인 검색어", kw is not None)
    if kw:
        chk("필수", "메인 검색어가 제목이나 본문에 있음", kw in T or kw in B, "제목에 있음" if kw in T else ("본문에만 있음" if kw in B else "없음"))
    chk("권고", "머리말: 글 유형 (" + "·".join(TYPES) + ")", typ in TYPES, typ or "없음")
    chk("권고", "머리말: 얼굴 코드 (첫줄/마무리/훅)", all(k in d["codes"] for k in ["O", "E", "훅"]), str(d["codes"]))

    # ── 권고: 제목 형식
    if kw:
        pos = T.find(kw) + 1
        chk("권고", "제목 검색어 15자 안", 0 < pos <= 15, f"{pos}자째")
        chk("권고", "본문 키워드 2~4회 (자연스러우면 벗어나도 됨)", 2 <= B.count(kw) <= 4, f"{B.count(kw)}회")
    chk("권고", "제목 25~40자", 25 <= len(T) <= 40, f"{len(T)}자")
    chk("권고", "제목 질문형", "?" in T)
    chk("권고", "제목 명사 나열 없음 (5개 이상 연속)", noun_run(T) < 5, f"최대 {noun_run(T)}개")

    # ── 권고: 첫 화면과 구간 구조
    lines = content_lines(B)
    ci = next((i + 1 for i, l in enumerate(lines) if "<!--결론-->" in l), None)
    si = next((i + 1 for i, l in enumerate(lines) if "<!--범위-->" in l), None)
    chk("권고", "답이 초반에 있음 (굵은 답 2줄째 안)", ci is not None and ci <= 2 and "**" in lines[ci - 1], f"{ci}줄째" if ci else "표시 없음")
    chk("권고", "범위 예고 첫 7줄 안", si is not None and si <= 7, f"{si}줄째" if si else "표시 없음")

    secs = re.split(r"^### ", B, flags=re.M)[1:]
    bad = []
    for s in secs:
        head = s.split("\n")[0].strip()
        bodyl = s.split("\n")[1:]
        has = any(re.match(r"^\s*(\||- |\d+\. |> |✔|✓|☐|▶|[①-⑩]|\*\*Q|▸|\[ \])", l) for l in bodyl)
        if not has:
            bad.append(head)
    chk("권고", "구간마다 표·목록 (필요한 구간만)", not bad, "줄글 구간: " + ", ".join(bad) if bad else f"{len(secs)}개 구간")
    numbered = [s.split("\n")[0] for s in secs if re.match(r"^\d+\.", s)]
    hlevel = "정보" if loose else "권고"
    chk(hlevel, "번호 질문형 소제목 4~6개", 4 <= len(numbered) <= 6 and all("?" in h for h in numbered), f"{len(numbered)}개")
    nobold = []
    for s in secs:
        if not re.match(r"^\d+\.", s):
            continue
        first = next((l.strip() for l in s.split("\n")[1:] if l.strip() and not l.strip().startswith("[")), "")
        if not first.startswith("**"):
            nobold.append(s.split("\n")[0][:15])
    chk("권고", "구간 첫 문장 굵은 답", not nobold, ", ".join(nobold))
    faq = [s for s in secs if s.startswith("자주")]
    if faq:
        qs = re.split(r"^\*\*Q\.", faq[0], flags=re.M)
        last = qs[-1].split("\n")[1:] if len(qs) > 1 else []
        chk("권고", "FAQ 마지막 Q에 답 있음", any(l.strip() and not l.startswith("---") for l in last))
    else:
        chk("정보", "FAQ", True, "없음 (선택 기법)")

    n = plain_len(B)
    chk("권고", "분량 1,700~2,800자 (유형에 따라 벗어나도 됨)", 1700 <= n <= 2800, f"{n}자")
    ga = len(re.findall(r"^\*[^*\n]+:[^*\n]+\*$", B, re.M))
    chk("권고", "기울임 풀이 줄 2번 이하", ga <= 2, f"{ga}번")

    # ── 필수: 상투어·반복 표현
    found = [b for b in BANNED if b in B]
    chk("필수", "상투어 없음", not found, ", ".join(found))
    nexts = [l for l in lines if NEXT_START.match(re.sub(r"[*>]", "", l).strip())]
    prev_next = sum(1 for p in prev[:9] if any(NEXT_START.match(re.sub(r"[*>]", "", l).strip()) for l in content_lines(p["body"])))
    chk("필수", "'다음 글은' 시작 문장 10편에 1번 이하", len(nexts) + prev_next <= 1, f"이번 {len(nexts)}, 직전 9편 {prev_next}")
    fs, ls = first_sentence(lines), last_sentence(lines)
    f6 = [p["path"] for p in prev[:10] if first_sentence(content_lines(p["body"]))[:6] == fs[:6]]
    l8 = [p["path"] for p in prev[:10] if last_sentence(content_lines(p["body"]))[-8:] == ls[-8:]]
    chk("필수", "첫 문장 앞 6자 직전 10편과 다름", not f6, f"'{fs[:6]}' " + ", ".join(f6))
    chk("필수", "끝 문장 끝 8자 직전 10편과 다름", not l8, f"'{ls[-8:]}' " + ", ".join(l8))
    for code, k, lim in [("첫 줄", "O", 3), ("마무리", "E", 3), ("제목 훅", "훅", 2)]:
        same = [p["path"] for p in prev[:lim] if p["codes"].get(k) and p["codes"].get(k) == d["codes"].get(k)]
        chk("권고", f"{code} 코드 직전 {lim}편과 다름", not same, ", ".join(same))

    # ── 필수: 운영 제한
    chk("필수", "태그 10개 이하", len(d["tags"]) <= 10, f"{len(d['tags'])}개")
    urls = re.findall(r"https?://\S+", d["text"].split("## 이미지 계획")[0])
    shop = [u for u in urls if not re.search(r"go\.kr|law\.go|naver\.com/(service|notices)|smartplace\.naver|korea\.kr|help\.naver", u)]
    chk("필수", "상업 링크 0 (허용 도메인 밖 링크)", not shop, ", ".join(shop))

    # ── 발행 모드에서만 필수가 되는 항목
    stage = "필수" if a.publish else "정보"
    fake = re.search(r"가상 시나리오:\s*예", d["text"]) is not None
    chk(stage, "가상 시나리오 아님", not fake, "예" if fake else "아니오")
    blanks = len(re.findall(r"\[(경험|숫자)", B))
    chk(stage, "빈칸 [경험]·[숫자] 0", blanks == 0, f"{blanks}곳")
    holders = [l.strip()[:20] for l in B.split("\n") if PLACEHOLDER.match(l)]
    chk(stage, "이미지 자리표시 0", not holders, f"{len(holders)}곳")
    if d["factcheck"]:
        p = find_factcheck(d["factcheck"], a.draft)
        if p is None:
            chk(stage, "사실 검증표", False, f"파일 없음: {d['factcheck']}")
        else:
            rows = factcheck_rows(p)
            block = [f"{i}({s})" for i, s in rows if any(b in s for b in BLOCKING_STATUS)]
            part = [i for i, s in rows if "일부 확인" in s]
            chk(stage, "사실 검증표: 미확인·출처 충돌 0", bool(rows) and not block,
                f"{len(rows)}건 중 " + (", ".join(block) if block else "모두 확인") if rows else "표 없음")
            if part:
                chk("권고", "사실 검증표: 일부 확인 항목 범위 좁히기", False, ", ".join(part))
    else:
        chk(stage, "사실 검증표 지정 (> 사실 검증:)", False, "머리말 없음")

    must_fail = [r for r in res if r[0] == "필수" and not r[2]]
    advise = [r for r in res if r[0] == "권고" and not r[2]]
    for level in ["필수", "권고", "정보"]:
        print(f"[{level}]")
        for lv, name, ok, det in res:
            if lv != level:
                continue
            mark = ("통과 " if ok else "실패 ") if level == "필수" else (("충족 " if ok else "권고 ") if level == "권고" else "정보 ")
            print("  " + mark + name + (f"  [{det}]" if det else ""))
    print("[사람 확인] (스크립트가 판정하지 않음)")
    for h in HUMAN_CHECKS:
        print("  ☐ " + h)
    musts = [r for r in res if r[0] == "필수"]
    verdict = "제출 불가" if must_fail else "제출 가능"
    if a.publish and not must_fail:
        verdict = "발행 전 사람 확인으로"
    print(f"\n결과: 필수 {len(musts) - len(must_fail)}/{len(musts)} 통과 · 권고 {len(advise)}건 → {verdict}")
    sys.exit(1 if must_fail else 0)


if __name__ == "__main__":
    main()
