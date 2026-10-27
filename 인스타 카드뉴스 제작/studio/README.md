# 가게 홍보 인스타 자동 제작 · 예약 게시

사장님이 찍은 사진·영상 + 짧은 문구 → **카드뉴스(1080×1350, 최대 10장)** 와 **릴스(1080×1920 MP4)** 를 만들고,
Uplika로 인스타그램에 **예약 게시**까지 합니다.

## 폴더 구조

```
studio/
  make.py                         제작 스크립트
  stores/<가게>/store.yaml        가게 정보 (이름·색·주소·영업시간·해시태그) — 한 번만 작성
  posts/<날짜-제목>/
      post.yaml                   이번 게시물 문구·구성·예약 시각
      media/                      사진(jpg/png/webp)·영상(mp4/mov)
      out/                        ← 결과물 (card_01.jpg…, reel.mp4, reel_cover.jpg, caption.txt, manifest.json)
  bgm/                            (선택) 저작권 문제 없는 배경음악
```

## 쓰는 법

1. `stores/` 에 가게 폴더를 하나 만들고 `store.yaml` 을 채웁니다 (`sample-cafe` 복사해서 수정).
2. `posts/` 에 게시물 폴더를 만들고 `media/` 에 사진·영상을 넣은 뒤 `post.yaml` 을 씁니다 (샘플 참고).
3. 제작:
   ```
   python make.py posts/2026-10-25-autumn-menu
   python make.py posts/2026-10-25-autumn-menu --only card   # 카드뉴스만 다시
   python make.py posts/2026-10-25-autumn-menu --only reel   # 릴스만 다시
   ```
4. 예약 게시: Claude에게 **"posts/2026-10-25-autumn-menu 예약 걸어줘"** 라고 하면
   `out/manifest.json` 을 읽어 파일을 Uplika에 올리고 `schedule` 시각에 인스타 예약을 겁니다
   (카드뉴스 → 캐러셀 피드, 릴스 → 릴스, 커버는 `reel_cover.jpg`).

## 카드 레이아웃

| layout | 모양 |
| --- | --- |
| `cover` | 사진 전체 + 하단 큰 제목·부제 (첫 장 기본값) |
| `photo` | 위 58% 사진 + 아래 제목·설명 (2장째부터 기본값) |
| `text`  | 메인 색 배경에 글만 — 할인·공지 강조용 |
| (자동)  | 마지막 장에 가게 정보 카드. `info_card: false` 로 끔 |

## 릴스 컷

- 사진: `dur` 초 동안 천천히 좌우로 흐르는 효과
- 영상: `start` 초부터 `dur` 초 잘라 씀, `speed: 2` 로 빨리 감기
- `text`: 화면 중앙 아래 자막, `position: top | center | bottom`
- `outro: true`: 끝에 가게 정보 화면
- `bgm`: 음악 파일 경로, `bgm_volume` 0~1 (기본 0.35)

## 참고

- 이미지 위 글자에서는 이모지가 자동으로 빠집니다(폰트 미지원). 캡션에는 그대로 들어갑니다.
- 폰트는 Pretendard → Noto Sans KR → 나눔고딕 → 맑은 고딕 순으로 찾습니다. `fonts/` 에 넣어도 됩니다.
- ffmpeg는 `pip install imageio-ffmpeg` 로 함께 설치된 것을 씁니다.
