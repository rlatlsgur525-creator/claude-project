# 인수인계 (2026-10-25 기준)

## 다른 컴퓨터에서 이어서 할 때 (먼저)
1. 저장소 루트에서 `git pull`.
2. 이 폴더의 `CLAUDE.md` → 이 파일 → `19_quality_system.md` 순서로 읽는다.
3. 검사기가 이 컴퓨터에서 도는지 확인: `naver-blog` 폴더에서 `python3 -m unittest tools/test_check_draft.py -v` (Windows는 `python` 또는 `py`). 12개 모두 OK여야 한다. 외부 패키지는 필요 없다 (Python 3.8 이상).
4. 네이버 임시저장·발행은 Uplika 커넥터 + 그 컴퓨터 브라우저의 Uplika 확장이 켜져 있어야 한다 (`bridge_status`로 확인). 확장이 없는 컴퓨터에서는 글 파일 작업만 한다.
5. 이미지 렌더(`img/*.html` → PNG): `img/render.py`(Playwright 필요) 또는 Windows에서는 Edge headless (아래 "도구" 참고).

## 지금까지 한 일 (순서대로)
1. 비슷한 기획 블로그 10곳 vs 블로그차트 탑티어 10곳 비교 → `01_rules.md`
2. 일일 지침 v1.0 → v1.5 (2026-10-24 사용자 승인) → **v1.6 (2026-10-25, 사용자 지시 "콘텐츠 품질 시스템 개선 지침" 이행)**
3. 화재보험 초안 v1.2 → 토론(`14_debate/`) → v2.0~v2.3, 독립 심사 3회(`16_judge_*`)로 v2.2가 3개 기준 통과. v2.3은 심사 지적 반영본 (재심사 안 함)
4. 시뮬레이션 5편(`10_sim/`) + 탑티어 비교(`11`) + 평가(`12`)
5. 악성 리뷰 초안 3틀(`17_review_drafts/`, 모두 가상 시나리오). 사용자 결정: A·B·C를 섞어 쓴다
6. 이미지 방향 결정(`09` v1.1), 화풍 비교 테스트 준비(`18_style_test.md`)
7. 2026-10-24: 화재보험 v2.3을 네이버 임시저장 (logNo 224452539251). 렌더 썸네일·four_way·bar_compare 포함
8. **2026-10-25: 품질 시스템 개선 (Phase 0~2 완료, 3~5 형식만)** → `19_quality_system.md`
   - 규칙 3등급(필수·권고·선택): `02` v1.6 0-1장, `01` v1.3 근거 등급, `09` v1.2
   - 글 유형 5개(질문답변·비교·실험·사례·체크리스트)와 유형별 구조: `02` 3장
   - `tools/check_draft.py` v1.6: 필수/권고/정보/사람 확인. 필수 실패만 종료 코드 1. 발행 모드에 이미지 자리표시·사실 검증표 검사 추가
   - 회귀 테스트 `tools/test_check_draft.py` 12개 통과. v1.5 결과는 `tools/tests/baseline_v1.5_checker.txt`
   - 사실 검증표 `fact_checks/` 신설. 화재보험 17건 정리, 16건 미확인
   - 경험 은행 v2 (필드·동의·익명화 규칙), 발행 기록에 성과 표 추가
   - 독립 심사 기준 v2 (10항목, 유형별 비중), 벤치마킹 방법 (4집단, 등급 표시)

## 파일 지도
| 파일 | 내용 | 상태 |
|---|---|---|
| 19_quality_system.md | 품질 시스템 기준 문서 (진단·흐름·사실 검증·심사·벤치마킹·성과) | v1 (2026-10-25) |
| 01_rules.md | 상위 규칙 | v1.3 |
| 02_daily_guideline.md | 일일 지침 | v1.6 (문구 사용자 확인 대기, v1.5 승인 기록 보존) |
| 09_image_guide.md | 이미지 지침 | v1.0 + v1.1 결정 + v1.2 등급 |
| 06_publish_log.md | 발행 표 + 성과 표 | 발행 0편, 임시저장 1편 |
| 13_experience_bank.md | 경험 은행 v2 | 비어 있음 (사람 입력 대기) |
| fact_checks/ | 사실 검증표 | 화재보험 v2.3: 17건 중 16건 미확인 |
| 15_draft_fire_insurance_v2.3.md | 화재보험 최신 초안 | [경험] 2곳, 캡처 2장, AI 일러스트 1장 미완성. 검사기 필수 통과(초안 모드), 발행 모드 실패 |
| 17_review_drafts/A·B·C | 악성 리뷰 3틀 | 가상 시나리오 → 발행 모드 실패 |
| 03~05, 07, 08, 10_sim, 11, 12, 14_debate | 이전 버전·시뮬레이션·비교·토론 | 참고용, 고치지 않음 |
| tools/check_draft.py | 기계 검사 v1.6 | 사용 중 |
| tools/test_check_draft.py, tools/tests/ | 회귀 테스트·고정 문서·v1.5 기준 결과 | 12개 통과 |
| img/ | 렌더 HTML·PNG | four_way, bar_compare, thumbnail_fire 완성 |

## 사용자가 정해야 할 것 (막혀 있는 것)
1. **지침 v1.6 문구 확인** — 내용은 사용자 지시대로 반영했다. 등급 분류(특히 상투어·첫 6자/끝 8자 지문을 필수로 둔 것)에 이견이 있으면 알려 준다
2. **AI 이미지 고정 화풍** — `18_style_test.md`로 5가지를 생성해 고르는 중
3. **고정 캐릭터** — 도입 여부와 콘셉트
4. **말투** — 사용자가 직접 쓴 글 3~5개 필요

## 사용자가 해야 할 것
- 화재보험 v2.3의 [경험] 2곳, 직접 캡처 2장(의무보험 대상 조회 화면, 계약서 특약란)
- 상담·방문 후 경험 은행에 1~2문장 (`13_experience_bank.md` 빠른 입력 줄)
- 악성 리뷰 초안은 실제 상담 사례로 바꾼 뒤에만 발행

## 다음 할 일 (제안 순서)
1. **화재보험 사실 검증**: `fact_checks/fire_insurance_v2.3.md` 16건을 법령·판결·행안부 원문으로 확인. 못 찾은 문장은 범위를 좁히거나 삭제
2. **v2.3을 v2 기준으로 독립 심사** (`19_quality_system.md` 5장, 초안 안 쓴 에이전트)
3. 사용자 [경험]·캡처가 오면 `check_draft.py --publish` 필수 통과 → 사람 확인 → 임시저장 갱신 (새로 임시저장 후 구판 삭제. `update_post`는 임시저장 글을 바로 발행하므로 쓰지 않는다)
4. 첫 발행 후 네이버 통계·Uplika `get_insights`로 측정 가능한 지표 확인 → `06` 성과 표 문단 고치기
5. 동일 분야 벤치마킹 1차 (10곳 × 3~5편, `benchmark/`)
6. 화풍·캐릭터 확정 → `09`에 반영

## 도구
- 검사: `python3 tools/check_draft.py 초안.md --prev 직전글들... [--publish]`
- 테스트: `python3 -m unittest tools/test_check_draft.py -v`
- 렌더: `python3 img/render.py img/x.html img/x.png` (Playwright 설치 필요). Playwright가 없는 Windows에서는 Edge headless로 렌더했다: `msedge --headless=new --force-device-scale-factor=2 --window-size=860,<높이> --screenshot=<png> file:///<html>`. HTML에 높이를 고정해 둔다 (`bar_compare.html` 860, `thumbnail_fire.html` 645)
- 렌더 HTML의 글꼴은 `../../miracle-shorts/shorts-kit/fonts/Pretendard-*.otf`를 상대 경로로 쓴다 (없으면 맑은 고딕)

## 알려진 한계
- 우리 블로그 발행 글 0편 → [검증] 등급 규칙 없음. 모든 형식 규칙은 [반복]·[가설]
- 탑티어 공감 수는 끌림 4편, 김주부 1편만 확인. 조회수·체류시간 비공개
- 분량 상한 2,800자는 심사 요구에 맞춰 올린 값, 근거 측정 없음
- AI 독립 심사 통과는 실제 독자 검증이 아니다
- 사실 검증표의 '확인 완료'를 원문을 실제로 봤는지 스크립트는 알 수 없다 (사람 확인)
