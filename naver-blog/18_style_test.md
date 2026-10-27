# 화풍 비교 테스트 (2026-10-24)

> 목적: `09_image_guide.md` v1.1 5번 "고정 화풍" 결정용. 같은 장면을 5가지 화풍으로 그려 나란히 비교한다.
> 생성: 사용자가 ChatGPT 또는 Gemini에서 직접 (v1.1 4번). 한 도구로 5장 모두 생성해야 공정하게 비교된다.

## 공통 장면 (화풍만 바꾼다)

화재보험 글 썸네일 후보로 쓸 수 있는 장면이다. 6-2 규칙을 지켰다: 글자가 생길 물건 없음, 사람이 들어갈 이유 없는 정물 구도, 나라·업종 이름 대신 재질 묘사, 겁주는 연출 없음.

```
A red fire extinguisher standing on a worn wooden counter, next to a small potted plant and two stainless steel bowls stacked together. Plain cream wall behind, soft morning light from the left, calm and reassuring mood. Still life, tight crop, background dissolved into soft blur.
```

## 화풍별 꼬리말 (공통 장면 뒤에 붙인다)

| # | 화풍 | 붙일 문장 |
|---|---|---|
| ① | 플랫 벡터 | `Style: flat vector illustration, simple geometric shapes, limited warm palette, no gradients, clean edges.` |
| ② | 한국 웹툰 | `Style: Korean webtoon illustration, clean line art, soft cel shading, bright friendly colors.` |
| ③ | 흑백 잉크 펜화 | `Style: black and white ink pen drawing, fine hatching, hand-drawn sketchbook feel, white paper texture.` |
| ④ | 수채화 | `Style: soft watercolor illustration, gentle color bleeding, visible paper grain, light airy tones.` |
| ⑤ | 클레이 미니어처 | `Style: handmade clay miniature diorama, matte plasticine texture, rounded soft shapes, studio lighting.` |

모든 프롬프트 마지막 줄에 붙인다:

```
Blog thumbnail, 4:3, generous empty space on the left for a title added later.
```

## 돌린 뒤 체크 (장마다)

- [ ] 글자·숫자·로고가 하나도 없다
- [ ] 사람·손·얼굴이 없다
- [ ] 한눈에 "그림"으로 보인다 (실사로 착각할 여지 없음)
- [ ] 왼쪽에 제목을 얹을 빈 공간이 있다

글자가 생겼을 때: `Keep everything the same, but make the [위치] a plain blank surface.`

## 고르는 기준 (사용자 판단)

| 기준 | 질문 |
|---|---|
| 작은 화면 가독성 | 휴대폰 검색 결과 썸네일 크기로 줄여도 무엇인지 보이는가 |
| 반복성 | 주제가 바뀌어도(리뷰, 배달앱, 세금) 같은 화풍으로 계속 그릴 수 있는가 |
| 재현성 | 같은 프롬프트로 다시 돌려도 비슷하게 나오는가 (한 화풍을 2번 돌려 비교) |
| 독자 신뢰 | 40~60대 사장님에게 가볍거나 유치해 보이지 않는가 |
| 캐릭터 궁합 | 고정 캐릭터를 넣었을 때 어울리는가 |

## 결과 기록

| # | 화풍 | 체크 4개 통과 | 메모 |
|---|---|---|---|
| ① | 플랫 벡터 | | |
| ② | 한국 웹툰 | | |
| ③ | 흑백 잉크 펜화 | | |
| ④ | 수채화 | | |
| ⑤ | 클레이 미니어처 | | |

**결정 (2026-10-27, 사용자):** ②·③·④를 섞는다. 사람은 ② 한국 웹툰, 가게·거리 같은 풍경은 ③ 흑백 잉크 펜화와 ④ 수채화를 섞은 느낌. 고정 스타일 문장은 `09_image_guide.md` v1.1 5번에 반영했다. 위 결과 표는 사용자가 ChatGPT에서 돌려 보고 바로 고른 것이라 칸별 기록은 비어 있다.
