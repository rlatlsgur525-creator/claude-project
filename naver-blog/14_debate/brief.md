# 토론 브리프 (5명 공통)

## 상황
- 의뢰인: 전주의 보험설계사. 동네 가게 사장님(식당·카페·미용실, 40~60대 포함)의 온라인·운영 문제를 푸는 네이버 블로그를 만들고, 승인된 지침으로 매일 자동 발행하려 한다.
- 검토 대상 초안: `/home/claude/naver-blog/08_draft_fire_insurance_v1.2.md` (가게 화재보험, 의뢰인이 한 번 승인했지만 지침 미달 2건이 나중에 발견됨)
- 현재 지침: `/home/claude/naver-blog/02_daily_guideline.md` (v1.4, 검토 대기)
- 상위 규칙: `/home/claude/naver-blog/01_rules.md`
- 이전 평가: `/home/claude/naver-blog/12_evaluation.md` (3개 기준 평가, 우리 글은 '계속 내리게 만드는가'가 2.8/5로 약함), `/home/claude/naver-blog/11_sim_vs_toptier.md` (탑티어 흐름 지도)

## 의뢰인의 판정 기준 (이번 토론의 목표)
1. 첫 제목을 보고 누르고 싶게 생겼는가
2. 보면 볼수록 궁금해서 계속 드래그를 내리게 만드는가 (글 중간중간 궁금증 장치)
3. 글 목적에 맞는 지식을 쉽게 설명했는가
4. **정답을 앞에서 미리 말하더라도 계속 읽고 싶게 만드는가**
5. 탑티어 글 중 공감을 많이 받은 글과 **구조적으로** 비슷한가

## 네이버 접근 방법 (중요)
- 브라우저는 네이버 블로그를 막는다. `mcp__Parallel_Search__web_fetch` 도구로만 읽는다 (ToolSearch로 `select:mcp__Parallel_Search__web_fetch` 로드).
- 최근 글 목록: `https://rss.blog.naver.com/<블로그ID>.xml`
- 글 본문: `https://m.blog.naver.com/<블로그ID>/<글번호>` (full_content: true)
- 공감·댓글 수는 본문 하단 텍스트에 나올 때가 있다. 나오면 기록하고, 공감이 많은 글을 우선 분석한다.
- model_name: "claude-opus-5-5", session_id: "debate-naverblog-2026-10-24"

## 지켜야 할 것
- 남의 블로그 문장을 길게 옮기지 않는다. 인용은 한 번에 15자 이내, 구조와 장치만 가져온다.
- 사실(법·숫자)은 바꾸지 않는다. 초안에 있는 사실만 쓰거나, 바꾸자고 할 때는 근거 출처를 단다.
- 의뢰인은 영업·상품 권유를 원하지 않는다 (정보만, 상담은 사장님이 먼저 요청하게).
- 출력은 한국어. 결과 파일 외에는 아무것도 수정하지 않는다.
