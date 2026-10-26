# 미라클톡 마스코트 — 캐릭터 설정 (2026-10-24 확정)

신혁이 고른 2차 시안 1번(`raw/original.png`)이 기준이다. 새 그림을 만들 때 이 문서의 **고정 요소**를 바꾸지 않는다.

## 고정 요소 (바꾸지 않는다)

| 항목 | 설정 |
|---|---|
| 인물 | 20대 후반 한국인 남성 직원. 딱딱한 전문가가 아니라 친근한 젊은 사원 느낌 |
| 머리 | 짧은 검은 머리, **5:5 가르마**, 앞머리가 양옆으로 부드럽게 내려옴, 약간 볼륨 |
| 얼굴 | **안경 없음**, 부드러운 턱선(성인), 밝은 미소, 순한 눈 |
| 옷 | 검은 정장(재킷 앞 열림) · 흰 셔츠 · 검은 넥타이(살짝 느슨) · 검은 구두 |
| 소품 | 얇은 태블릿 (상담·분석의 상징) |
| 그림체 | 흑백 2D 플랫 벡터. 검정 면 + 흰 면만, 회색·그라데이션·명암 없음, 일정한 굵은 외곽선 |
| 쇼츠에 넣을 때 | 흰 스티커 테두리(라이브러리 PNG에 이미 들어 있음) — 어두운 배경에서도 보이게 |

## 파일

| 경로 | 내용 |
|---|---|
| `raw/original.png` | 확정 시안 (전신 + 상반신) |
| `raw/sheet.png` | 4방향 전신 + 표정 6종 설정표 (일부 컷의 정장이 회색으로 나옴 → 기준은 검정) |
| `raw/<포즈>.png` | 포즈 원본 (흰 배경) |
| `../../studio/library/mascot/<포즈>.png` | **스튜디오에서 바로 쓰는 투명 PNG** (흰 테두리). 미디어 탭 [공용]에 보인다 |
| `make_cutouts.py` | raw → 투명 PNG 변환. 새 포즈를 raw에 넣고 실행 |
| `vectorize.py` | raw → SVG 벡터(`../../studio/library/mascot_svg/<포즈>.svg`). 확대해도 선명하고 `gfx.svg_img`로 색을 바꿀 수 있다 (`docs/ai-image-vector.md`) |

현재 포즈: `point`(옆을 가리키며 설명) · `surprised`(놀람, 경고 훅) · `think`(턱 괴고 태블릿 분석) · `thumbsup`(좋은 결과) · `stop`(팔로 X, "하지 마세요") · `wave`(인사)

## 스튜디오 템플릿에서 쓰는 곳 (자동, '마스코트 진행자 넣기'로 끄고 켬)

| 템플릿 | 장면 → 포즈 |
|---|---|
| 경고형 | 훅 `stop`(팔로 X) · 권위 카드 얼굴 아바타(`point`에서 얼굴만) · 손해 `surprised` · 결과 `thumbsup` · 체크리스트 `point`(좌우 반전해 목록을 가리킴) |
| 약관 전수조사 | 훅 `surprised`(첫 화면 = 썸네일에 얼굴) · 넓게 보장 `thumbsup` · 확인 필요: 멈춤 동안 `think` → 공개 순간 `surprised` |
| 비교 실험 | 셋업 `think` · 상황별 기준 `point`(반전). **1등 금액 화면에는 넣지 않는다** — 엄지척이 상품 추천처럼 보일 수 있어서 |

배치 규칙: 마스코트는 오른쪽 세로 띠(가운데 x≈905, 위 y≈400, 높이 ≈720)에 서고, 내용은 왼쪽 x 40~760으로 좁힌다. 아래 자막 자리(y 1170 아래)는 침범하지 않는다. 그리기 함수는 `studio/gfx.py`의 `draw_mascot`, `mascot_avatar`.

## 새 포즈 만드는 법 (일관성 유지)

1. Higgsfield 레퍼런스 요소 **`miracle-fp`** (id `b68c1175-a130-4133-a527-bd6380b98fbe`)를 프롬프트에 넣는다: `<<<b68c1175-a130-4133-a527-bd6380b98fbe>>>`
2. 모델은 Nano Banana Pro, 비율 3:4, 2k. 장당 약 0.5크레딧.
3. 프롬프트 틀 (포즈 부분만 바꾼다):

```
Full-body single character <<<b68c1175-a130-4133-a527-bd6380b98fbe>>>, exact same character design,
[포즈와 표정 설명], whole body head to toe visible. Flat 2D vector illustration, strictly black and white only,
suit solid black fill, white shirt, black tie, clean bold outlines, no gray, no gradients, no shading,
pure white background, single character only, no text, no props besides the tablet.
```

4. 받은 PNG를 `raw/<포즈이름>.png`로 저장 → `python make_cutouts.py <포즈이름>.png` → 스튜디오 [공용]에 나타남.
5. 벡터도 만든다: `python vectorize.py <포즈이름>.png` → `studio/library/mascot_svg/<포즈이름>.svg` (필요: `pip install vtracer resvg-py`)

## 다음에 만들 것 (후보)

- 상반신만 있는 버전(화면 아래에서 고개 내밀기), 말풍선용 얼굴 클로즈업
- 같은 그림체로 사물 2D화: 보험증권, 약관 PDF, 병원, 계산기, 돈봉투 등 → 모두 흑백 플랫 벡터로 통일
- 다른 사람(고객·빌런 유형)은 마스코트와 구별되게 머리·옷을 다르게 하고 같은 그림체 유지
