---
name: matzip-review
description: 사장님이 보낸 맛집 사진으로 인스타 게시물을 만든다. 사장님이 "썸네일은 이거, 나머지는 이거"라고 사진 역할을 말하면 Claude가 게시물 작업실에 상을 다 차려 두고(필터, 표지 후보 5개, 캡션), 사장님은 작업실에서 표지 하나 고르고 캡션만 확인한다. 필터·사진·문구는 사장님이 작업실에서 직접 고칠 수도 있다. 확정되면 Uplika로 예약한다. "맛집 게시물 만들어줘", "이 사진으로 게시물", "썸네일은 이거", "inbox 처리", "B로 해줘", "예약 걸어줘" 요청에 사용.
---

# 맛집 게시물 자동 제작

도구는 `studio/matzip/` 에 있다. 사장님은 **사진과 역할만 알려 주고, 작업실에서 표지 하나 고르고 캡션을 확인한다.** 필터나 문구를 바꾸고 싶으면 사장님이 작업실에서 직접 바꾼다.

| 파일 | 역할 |
| --- | --- |
| `review.py` | **게시물 작업실** (http://127.0.0.1:8770). 사진 올리기·역할, 필터 슬라이더, 표지 문구, 표지 5개 고르기, 캡션, 확정. 게시물 여러 개를 위쪽에서 바꿔 가며 쓴다 |
| `make_post.py` | brief.json → 필터 입힌 사진(`photos_f/`), 표지 후보 5개(`out/covers/A~E.jpg`, 모아 보기 `all.jpg`), 카드, 캡션. `--pick B` 로 표지 확정과 릴스 생성. 작업실의 [표지 5개 만들기]·[확정]과 같다 |
| `look.py` | 맛있게 필터 (웹 필터 filter.html 과 같은 결과) + 밝기·따뜻함·채도·선명함 조절 |
| `covers.py` | 표지 템플릿 5종 (A 불꽃 콜라주, B 하단 큰 자막, C 마커 간판, D 띠 분할, E 말풍선 후기) |
| `render.py` | 카드 그리기, 하이라이트 릴스 |
| `PLAYBOOK.md` | 인기 게시물 비교, 형식 기준 |

## 1. 재료 받기
- 사장님이 사진을 보내며 역할을 말한다. 예: "썸네일은 1번 2번, 나머지는 3~6번".
  - **썸네일 위 = 가게 입구·간판**, **썸네일 아래 = 대표 메뉴 클로즈업**, **나머지 = 본문(말한 순서대로)**.
  - 말하지 않은 사진은 Claude가 사진을 보고 정한다(상차림 → 클로즈업 → 쌈·조합 → 사리·볶음밥 → 반찬 → 내부). 쓸 데 없는 사진은 빼 둔다(작업실에서 '안 씀'으로 보인다).
  - 입구 사진이 없으면 한 번 요청하고, 없다고 하면 그대로 진행한다(콜라주 표지 A·D는 메뉴 사진만으로 그려진다).
- 사진 파일은 채팅 첨부 경로나 `studio/matzip/inbox/<가게명>/` 에서 받는다. 파일 경로를 알 수 없으면 "작업실의 [사진 올리기]로 넣어 주세요"라고 안내한다.
- 가게명, 지역, 대표 메뉴를 알 수 없으면 묻는다. 주소와 영업시간은 모르면 `(확인 필요)` 로 둔다. **지어내지 않는다.**

## 2. 상 차리기
- 사진을 **전부 직접 본다**(Read). 사진에 이미 글씨가 있으면 `exterior_crop` 으로 잘라 내고, 음식이 잘 보이게 `signature_focus` 를 맞춘다.
- `posts/<YYYY-MM-DD>-<영문슬러그>/photos/` 에 사진을 복사하고 `brief.json` 을 쓴다. 형식은 `make_post.py` 맨 위 설명과 `posts/2026-10-23-sukine-jeonju/brief.json` 을 참고한다.
  - `hook`: 표지 한 줄 문구. `[강조]` 는 1~2단어만.
  - `quotes`: 말풍선 2개.
  - `look`: 기본 `{"preset": "v1", "strength": 1}`. 사장님이 이미 필터를 입혀 보냈으면 `{"preset": "none"}`.
  - 캡션은 PLAYBOOK의 hand 템플릿, 사장님 말투로 쓰고 2200자 이하. 해시태그 4~6개.
- 인기 계정의 글꼴·색·말투를 통째로 가져오지 않는다. "상위글 따라한 느낌"이라는 피드백이 있었다.
- `python make_post.py posts/<폴더>` 를 실행하고 `out/covers/all.jpg` 를 **직접 열어 본다.** 글자가 잘리거나 겹치면 brief 문구를 줄이고 다시 돌린다.

## 3. 사장님께 넘기기
- 작업실을 띄운다: `preview_start` 로 `review` 를 켜고(이미 켜져 있으면 그대로), `POST /api/open {"slug": "<폴더명>"}` 으로 새 게시물을 연다. 핸드폰 주소는 `studio/matzip/phone_url.txt` 에 있다(서버를 켤 때마다 키가 바뀐다).
- `out/covers/all.jpg` 를 SendUserFile 로 보내고 짧게 말한다: "상 차려 뒀어요. 썸네일 5개 중 하나 고르시고 캡션 확인해 주세요." + 작업실 주소.
- 사장님은 작업실에서 고르고 [확정]을 누르거나, 채팅으로 "B로 해줘"라고 한다. 채팅으로 오면 `python make_post.py posts/<폴더> --pick B` 를 실행한다.
  - 결과: 카드뉴스 `out/01~NN.jpg`, 하이라이트 릴스 `out/reel.mp4`, 캡션 `out/caption.txt`, `status: approved`.
- 사장님이 작업실에서 필터나 문구를 바꿨다면 brief.json 이 바뀌어 있다. 다시 만들 때 그 값을 덮어쓰지 않는다.

## 4. 예약 게시 (status 가 approved 일 때만)
- Uplika `list_accounts` 로 **instagram** 계정을 확인한다. 없으면 https://uplika.com/dashboard/connections 연결을 안내하고 멈춘다.
- 게시 전에 계정, 예약 시각, 캡션 첫 줄을 사장님께 확인받는다. 바깥으로 나가는 일이므로 매번 확인한다. 시간대는 +09:00 이다.
- 파일 올리기:
  1. 파일마다 `media_presign` 을 호출한다(contentType image/jpeg, video/mp4, bytes는 실제 크기).
  2. PowerShell `Invoke-WebRequest -Method PUT -InFile <파일> -ContentType <같은 타입> -Uri <uploadUrl>` 로 업로드한다.
  3. `media_complete` 를 호출한다.
- 게시는 두 번에 나눠서 한다.
  - 카드뉴스: `publish` 에 `mediaIds` = 카드들(최대 10장), `content` = caption.txt, `scheduledAt` 을 넣는다.
  - 릴스: `publish` 에 `mediaIds` = reel.mp4, `options.instagram.contentType: reel`, `coverMediaId` = reel_cover.jpg 를 넣는다. 시간은 사장님께 묻는다.
- 받은 post id들을 post.json 의 `published` 에 기록한다.
