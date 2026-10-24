---
name: miracle-shorts
description: 신혁이 준 사진·영상·대본으로 유튜브 쇼츠/릴스(9:16)를 기획하고 실제 mp4로 편집할 때 사용. '쇼츠 만들어줘', '/miracle-shorts', 촬영본 편집 요청에 사용. 미라클톡과 소상공인 고객 홍보 쇼츠 모두.
---

# 미라클 쇼츠

신혁(김신혁FP, '미라클톡' 운영, 전주 메트라이프 FP)이 주는 소재로 쇼츠를 기획하고 편집해 mp4로 전달한다. 쓰임은 두 갈래다. ① 미라클톡: 경제·연금·보험 정보 쇼츠. ② 소상공인 고객: 식당·1인숍 홍보 쇼츠.

참고한 공개 스킬: appie-kit의 viral-shorts-course·video-editing-pro·short-form-video-production, video-use (https://github.com/S3YED/appie-kit, MIT), HyperFrames (https://github.com/heygen-com/hyperframes). 아래는 그 원칙을 한국어와 이 작업공간에 맞게 옮긴 것이다.

## 원칙

1. **프리셋 없음. 소재에서 출발한다.** 포맷을 먼저 고르게 하지 않는다. 받은 소재를 보고 그 소재로 가장 강한 영상이 뭔지 판단한다.
2. **질문 → 계획 확인 → 실행 → 반복.** 컷 편집에 들어가기 전에 쉬운 말로 된 계획을 신혁이 승인해야 한다. 단, "알아서 해줘", "바로 뽑아줘"라고 하면 계획을 한 줄로 밝히고 바로 실행한다.
3. **오디오가 먼저, 화면은 따라간다.** 말이 있는 소재는 말 끊기는 지점이 컷 후보다.
4. **보여주기 전에 직접 검수한다.** 내가 올리지 않을 결과물은 보여주지 않는다.
5. 아래 수치와 예시는 검증된 출발점이다. 소재가 다른 걸 요구하면 벗어나도 된다. 반드시 지킬 것은 '하드 규칙'뿐이다.

## 0. 작업 환경 준비 (세션마다 한 번)

작업공간은 매번 새로 열리므로 아래를 먼저 실행한다. 이미 `~/shorts-kit/build.py`가 있으면 건너뛴다.

```bash
mkdir -p ~/shorts-kit/fonts && cd ~/shorts-kit
# 1) 이 문서 맨 아래 '부록 A/B'의 sfx.py, build.py를 Write 도구로 ~/shorts-kit/ 에 그대로 저장
# 2) 폰트 (Pretendard, OFL) — npm 레지스트리로 받는다
npm pack pretendard@1.3.9 --silent && tar xzf pretendard-1.3.9.tgz && \
  cp package/dist/public/static/Pretendard-{Bold,ExtraBold,Black}.otf fonts/ && rm -rf package pretendard-1.3.9.tgz
# 3) 효과음 키트 합성 (저작권 없음): whoosh pop ding impact tick riser swoosh_down cash
python3 sfx.py sfx
# 4) 원본 지침이 더 필요할 때만 (선택)
git clone -q --depth 1 https://github.com/S3YED/appie-kit.git ~/shorts-kit/ref-appie   # skills/content/viral-shorts-course, video-editing-pro
```

이 작업공간의 제약은 다음과 같다. 이후 작업은 이 범위 안에서 한다.
- Hugging Face와 OpenAI 서버가 막혀 있어 Whisper 같은 음성 인식 모델을 받을 수 없다. 그래서 자막은 대본과 무음 감지로 맞춘다(6장).
- Mixkit·Pixabay 등 효과음·음악 사이트도 셸에서 막혀 있다. 효과음은 합성 키트를 쓰고, BGM은 신혁이 준 파일을 쓴다(7장).
- pip, npm, GitHub는 된다.

## 1. 소재 파악

받은 파일은 원본이다. 작업 폴더(`~/shorts/<프로젝트>/raw/`)에 복사해서 쓴다.
- 영상마다 `ffprobe`로 길이·해상도·회전·오디오 유무를 확인한다.
- 영상마다 프레임 시트를 만들어 Read로 본다: `ffmpeg -i X -vf "fps=6/길이,scale=320:-1,tile=6x1" -frames:v 1 sheet.jpg`
- 말이 있는 영상은 `python3 ~/shorts-kit/build.py speech X.mp4`로 말한 구간 목록을 뽑는다. 무음 0.35초 이상을 경계로 본다. 시끄러운 매장이면 `--noise -28`.
- 무엇을 봤는지 쉬운 말로 2~3줄 요약한다. 예: "정면 토크 42초, 찌개 끓는 근접샷 8초, 외관 사진 2장"

## 2. 소재에 맞춘 질문 (고정 체크리스트 아님)

소재를 보고 정말 모르는 것만 묻는다. 보통 2~4개다. AskUserQuestion이 있으면 그걸로 묻는다.
- 누구 채널인가: 미라클톡 / 어느 가게
- 이 영상으로 시청자가 뭘 하게 만들고 싶은가: 저장, 댓글, 상담 문의, 방문·예약
- 말소리: 신혁의 육성이 있는지, 대본이 있는지, 자막만 갈지
- BGM 파일이 있는지 (없으면 7장의 선택지를 제시)
- 길이: 정해주지 않으면 소재가 버티는 만큼. 기본은 25~35초, 최대 45초

## 3. 기획 원칙 (viral-shorts-course 합의 원칙 기반)

**구조 (순서대로):**
1. 훅 2~3초: 첫 화면만 봐도 무슨 얘기인지 알게 하고, 질문을 연다. "어떻게"가 아니라 "무슨 일이 일어나는지"를 말한다.
2. 예고 1줄: "끝까지 보면 ○○를 알게 된다"
3. 바로 본론으로 들어가는 문장. "자 시작해볼게요" 같은 말은 금지
4. 중간은 "그리고"가 아니라 "그런데 / 그래서"로 잇는다. 긴장이 쌓여야 한다
5. 보상(답·결과) 직전에 0.3~0.5초 숨 고르기
6. 보상은 기대를 채우면서 살짝 반전을 준다
7. 보상 직후 바로 끝낸다. 아웃트로, "구독 좋아요", 긴 로고 금지. 로고와 CTA는 마지막 1~2초 안에서 끝낸다

**말과 글:**
- 초등학생도 이해할 단어를 쓴다. "포트폴리오, 리스크 헤지, 수익률 제고" 대신 "돈을 나눠 담기, 사고 대비, 더 불어나게"
- 첫 화면은 소리를 끄고 봐도 컨셉이 보여야 한다. 얼굴, 대비, 3~5단어 텍스트면 충분하다
- 보상이 공유할 만한지 본다: "친구한테 캡처해서 보낼까?"
- 포맷 일관성: 잘 된 구조는 시리즈로 반복한다. "52주 연속 할 수 있는 포맷인가?"

**미라클톡 준법 규칙 (금융 콘텐츠, 반드시 지킴):**
- 수익률 보장이나 "무조건", "확정" 같은 단정 표현을 쓰지 않는다
- 특정 상품명·회사명을 홍보하지 않는다. 원리 설명으로만 구성한다
- 숫자 예시는 가정을 화면에 상시 표기한다: "연 ○% 가정·세전·수수료 미반영 예시" (`small` 자막 스타일)
- 숫자는 계산을 실제로 돌려서 검증한다 (python)
- 상품 광고 성격이면 "준법감시 심의 후 게시"를 전달 메시지에 적는다

**소상공인 쇼츠:**
- 음식은 소리가 반이다. 지글지글·보글보글 원음을 살리고 BGM을 낮춘다
- 가격·기간·위치는 마지막에 한 화면으로 정리한다
- 손님 얼굴이 나오면 동의 여부를 확인하라고 전달 메시지에 적는다

## 4. 계획 제안 → 확인

4~8문장으로 제안하고 컷표를 함께 보여준다. 담을 내용: 어떤 구조인지, 어떤 테이크·구간을 쓸지, 훅을 뭘로 할지, 자막 스타일, 효과음·BGM 방향, 예상 길이. 컷표 형식은 이렇다.

| # | 출력 시간 | 소재(원본 구간) | 화면 자막 | 효과음 | 연출 |
|---|---|---|---|---|---|

승인을 받으면 실행한다. 수정 요청이 오면 계획만 고쳐서 다시 확인받는다.

## 5. 편집 원칙 (video-editing-pro 기반)

- **훅은 첫 문장이 아니라 가장 강한 문장이다.** 전체를 훑어 제일 센 주장·대비·숫자를 찾아 맨 앞으로 옮긴다. 1.5~3초 안에 핵심이 끝나야 한다.
- **문장 선택:** 이야기를 진전시키거나, 주장을 증명하거나, 보상을 주는 문장만 남긴다. 같은 말을 다시 하는 문장은 자른다. 나열은 가장 강한 2개만 남긴다.
- **멈춤 처리:**

| 멈춤 길이 | 처리 |
|---|---|
| 0.1초 미만 | 건드리지 않음 |
| 0.15~0.3초 | 문장 사이면 자름, 강조 쉼이면 둠 |
| 0.3~0.5초 | 빠른 구간은 자르고, 감정 구간은 숨 쉴 틈으로 둠 |
| 0.5초 초과 | 무조건 자름 |

  컷 앞뒤에는 0.05~0.2초 여유를 남긴다. 단어 중간을 자르면 안 된다.
- **추임새:** "어, 음, 그러니까, 뭐지"는 자른다. 다 지우면 조립한 소리가 나므로 사람다운 말맛은 일부 남긴다.
- **에너지 곡선:** 0~3초 최고조(빠른 컷) → 3~15초 증거 제시(3~5초마다 새 정보) → 15~25초 핵심 공개(가장 센 장면) → 마지막 짧게. 컷 간격은 끝으로 갈수록 짧게 한다.
- **8초 규칙:** 8초 넘게 화면 변화가 없으면 안 된다. 컷 전환, 줌(`punch`), 자막 등장, 사진 켄번즈, B롤 중 하나를 5~8초마다 넣는다.
- **자막:** 구(3~6어절)마다 의미를 담은 단어 하나만 `[대괄호]`로 강조한다. 숫자·결과·고유명사·손실 단어가 대상이다. "그리고, 진짜, 그냥"은 강조하지 않는다. 한 줄은 12자 안팎으로, 길면 `/`로 줄을 나눈다.
- **안전 영역:** 오른쪽 아래(좋아요·댓글 버튼)와 하단 16%(제목·설명)를 피한다. 스타일 기본값이 이미 피하게 잡혀 있다.

## 6. 실행

작업 폴더 구조: `~/shorts/<프로젝트>/raw/`(원본 복사본), `edit/edl.json`, `edit/final.mp4`

**edl.json 작성 (build.py 맨 위 설명 참고):**
- `segments`: 재생 순서대로 놓는다. 영상은 `in/out`, 사진은 `dur`, 글자 화면은 `color`.
  - `fit`: 세로 영상은 `crop`, 가로 영상·사진은 `blur`(흐린 배경 위에 원본 전체)
  - `zoom`: `punch`(강조 순간 빠른 줌인), `kenburns`(사진 천천히 확대), `out`, `none`
  - `mute`: 원음을 뺄 때. 내레이션을 따로 깔 경우 등
- `captions`: **출력 타임라인 기준 초.** `style`은 `hook`(크게, 화면 중앙), `main`(하단 중앙), `top`(상단 라벨), `small`(가정·출처 표기). `anim`은 `pop` 기본, `fade`, `none`.
- `sfx`: `{"t":초,"name":"whoosh"}` 형식. 키트에 없는 소리는 `"src"`로 파일을 지정한다.
- `voice`: 별도로 녹음한 내레이션 파일과 `offset`
- `bgm`: `{"src":..., "vol":0.18~0.3, "duck":true}`. 말소리가 나오면 BGM이 자동으로 낮아진다(덕킹).

**자막 타이밍 맞추기 (음성 인식 없이):**
1. 대본이 있으면: `speech` 결과의 말한 구간을 대본 문장에 순서대로 대응시킨다. 한 구간에 문장이 여러 개면 글자 수 비율로 나눈다.
2. 대본이 없으면: 구간별 프레임과 길이를 보고 무슨 말일지 추정해 쓰지 않는다. 신혁에게 대본을 받거나, 캡컷 '자동 자막'에서 SRT로 내보내 달라고 요청한다(한국어 인식이 좋다). SRT를 받으면 그 시간을 그대로 쓴다.
3. 컷 편집으로 시간이 당겨졌으면 출력 시간을 이렇게 계산한다: `출력 시간 = 원본 시간 - 세그먼트 in + 그 세그먼트의 출력 시작`

**렌더 순서:**
1. `python3 ~/shorts-kit/build.py render edit/edl.json --preview` → 540×960 미리보기
2. 자체 검수(8장). 문제가 있으면 고치고 다시 렌더한다. 최대 3회까지만 돌고, 그래도 남은 문제는 신혁에게 알린다
3. `python3 ~/shorts-kit/build.py render edit/edl.json` → 1080×1920 최종본. 음량은 -14 LUFS로 자동 맞춰진다

**하드 규칙 (어기면 조용히 망가짐):**
1. 자막은 필터 체인의 맨 마지막에 입힌다. build.py가 이미 그렇게 한다. 다른 오버레이를 추가하면 자막 앞에 넣는다
2. 세그먼트별로 따로 추출한 뒤 `-c copy`로 이어 붙인다. 재인코딩을 반복하지 않는다
3. 모든 컷 경계에 30ms 오디오 페이드를 넣는다. 안 넣으면 '틱' 소리가 난다. build.py가 처리한다
4. 단어 중간에서 자르지 않는다. 컷 앞뒤 여유는 30~200ms
5. 원본 파일은 수정하지 않는다
6. 계획 승인 전에는 최종 렌더를 하지 않는다 ("알아서" 지시는 예외)

## 7. 소리

**효과음 키트** (합성, 저작권 없음):

| 이름 | 쓰는 곳 |
|---|---|
| `impact` | 훅 첫 프레임, 충격적인 숫자 |
| `whoosh` | 화면 전환, 자막 슬라이드 |
| `swoosh_down` | 퇴장, 다음 주제로 넘어갈 때 |
| `pop` | 키워드·말풍선 등장 |
| `tick` | 숫자 카운트, 체크리스트 |
| `riser` | 보상 공개 직전 0.8~1.5초 (긴장) |
| `ding` | 정답·결과 공개, 마무리 |
| `cash` | 돈·절약·혜택 |

밀도는 이렇게 잡는다. 정보형은 전환과 강조에 2~4번. 예능식은 컷마다 넣는다. 훅에서는 효과음을 꼭 쓴다. 볼륨은 0.4~0.8로 하고, 내레이션을 가리면 줄인다.

**BGM** (셸에서 음악 사이트 접속 불가). 선택지는 이 순서로 제시한다.
1. 신혁이 첨부한 음원 파일. 유튜브 오디오 보관함이나 캡컷에서 받은 것
2. Higgsfield 음악 생성(연결돼 있으면). 크레딧이 들어가므로 먼저 확인받는다
3. BGM 없이 렌더해서 전달하고, 업로드할 때 유튜브 쇼츠 앱에서 음악을 붙이도록 안내

분위기 가이드: 금융·상담은 잔잔한 피아노(85~95 BPM). 음식·일상은 경쾌한 어쿠스틱. 경고·충격 정보는 낮은 베이스. 사연은 따뜻한 스트링. BGM의 고조 구간을 보상 직전에 맞추면 긴장이 공짜로 생긴다. 볼륨은 0.18~0.3에 덕킹을 켠다.

## 8. 검수 (보여주기 전에 직접)

렌더 결과물로 확인한다.
- 0~3초, 각 컷 경계 전후, 마지막 2초의 프레임을 뽑아 Read로 본다: `ffmpeg -ss T -i final.mp4 -frames:v 1 -vf scale=540:-1 f.jpg`
  - 첫 프레임만으로 컨셉이 보이는가 (소리 끄고 테스트)
  - 자막이 잘리거나 안전 영역을 침범하지 않는가. 원본 속 글자와 겹치지 않는가 (겹치면 `top`/`main` 위치를 바꾸거나 `small`로)
  - 강조 단어가 구마다 하나씩만 있는가
- `ffprobe`로 길이가 계획과 맞는지, `ebur128`로 음량이 -14 LUFS 근처이고 피크가 -1dB 아래인지 본다
- 훅이 3초 안에 끝나는가. 보상 후에 군더더기가 없는가
- 미라클톡: 준법 규칙 4개를 다시 확인한다

## 9. 전달

- `SendUserFile`로 final.mp4를 보낸다. 한 줄로 무엇을 만들었는지 말한다
- 같이 줄 것: 제목 후보 3개, 설명 1~2줄, 해시태그 5개, (미라클톡) 준법 확인 사항, 다음에 시도할 것 1개 (예: "훅을 숫자형으로 바꾼 B안")
- 수정 요청은 edl.json만 고쳐서 다시 렌더한다. 원본을 다시 분석하지 않는다

## 10. 소재 없이 그래픽만으로 만드는 쇼츠 (모션그래픽)

촬영본이 없고 AI 캐릭터 이미지, 텍스트, 숫자 애니메이션만으로 만들 때 쓴다. 신혁이 처음 보여준 '심기좋게' 영상 같은 경우다.
- 간단한 경우: 이미지를 `segments`에 사진으로 넣고 `kenburns`·`punch`와 `hook`/`main` 자막만으로 구성한다. build.py로 충분하다.
- 복잡한 경우(카운트업, 그래프, 요소별 등장): HyperFrames를 쓴다.
  `git clone -q --depth 1 https://github.com/heygen-com/hyperframes.git ~/shorts-kit/ref-hf` 후 `skills/hyperframes/SKILL.md`를 읽고 그 계약을 따른다. 세로는 1080×1920. Chromium은 `/opt/pw-browsers`에 있다. 렌더한 mp4를 build.py의 세그먼트로 넣으면 효과음·BGM·자막 처리는 그대로 쓸 수 있다.
- 캐릭터 이미지는 연결된 이미지 생성 도구(Higgsfield, OpenArt)로 만든다. 크레딧을 쓰기 전에 확인받는다. 같은 캐릭터를 매번 재사용해 브랜드 얼굴로 만든다.

## 부록 A — ~/shorts-kit/sfx.py

```python
#!/usr/bin/env python3
"""Synthesize a small royalty-free SFX kit (48kHz stereo WAV).
usage: python3 sfx.py <out_dir>
names: whoosh pop ding impact tick riser swoosh_down cash
"""
import sys, os, wave, numpy as np
SR = 48000
rng = np.random.default_rng(7)

def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
    return e

def lowpass(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode="same")

def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1; return x / m * peak

def whoosh(d=0.45):
    n = int(SR * d); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n); seg = 512
    for i in range(0, n, seg):  # sweeping band: lowpass width shrinks -> brighter
        p = i / n; k = int(40 - 34 * p)
        out[i:i + seg] = lowpass(noise, k)[i:i + seg]
    shape = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return norm(out * shape, 0.7)

def swoosh_down(d=0.4):
    return whoosh(d)[::-1].copy()

def pop(d=0.12):
    n = int(SR * d); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 300
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(np.sin(ph) * env(n, 0.001, 0.03), 0.8)

def ding(d=1.2):
    n = int(SR * d); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318.5, 1), (2637, .35), (3955, .15), (1975.5, .25)])
    return norm(x * env(n, 0.002, 0.35), 0.6)

def impact(d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 6) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.28)
    click = lowpass(rng.standard_normal(n), 3) * env(n, 0.0005, 0.015)
    return norm(np.tanh(2.2 * (body + 0.6 * click)), 0.9)

def tick(d=0.05):
    n = int(SR * d)
    return norm(lowpass(rng.standard_normal(n), 2) * env(n, 0.0003, 0.008), 0.6)

def riser(d=1.6):
    n = int(SR * d); t = np.arange(n) / SR
    f = 200 * (2 ** (3 * t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    noise = lowpass(rng.standard_normal(n), 6) * 0.6
    return norm((tone + noise) * (t / d) ** 2, 0.6)

def cash(d=0.7):
    a = ding(0.7) * 0.6; n = len(a)
    b = np.zeros(n); c = tick(0.05); b[:len(c)] += c; b[int(.06 * SR):int(.06 * SR) + len(c)] += c
    return norm(a + b, 0.7)

KIT = dict(whoosh=whoosh, pop=pop, ding=ding, impact=impact, tick=tick, riser=riser, swoosh_down=swoosh_down, cash=cash)

def write(path, x):
    x = np.clip(x, -1, 1); st = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"; os.makedirs(out, exist_ok=True)
    for k, fn in KIT.items(): write(os.path.join(out, k + ".wav"), fn())
    print("wrote", ", ".join(KIT))
```

## 부록 B — ~/shorts-kit/build.py

```python
#!/usr/bin/env python3
"""Miracle Shorts render engine (ffmpeg). 9:16 shorts from an edit plan (edl.json).

  python3 build.py speech <media> [--noise -32] [--min 0.35]   -> JSON speech spans (silence-based)
  python3 build.py render <edl.json> [--preview]               -> mp4

edl.json:
{
 "out": "edit/final.mp4", "w":1080, "h":1920, "fps":30,
 "fonts": "kit/fonts",                       # dir with Pretendard-*.otf
 "segments": [                               # played in order
   {"src":"raw/a.mp4","in":2.1,"out":5.4,"fit":"crop","zoom":"punch"},
   {"src":"raw/photo.jpg","dur":3.0,"fit":"blur","zoom":"kenburns"},
   {"color":"#0e1116","dur":2.0}             # plain card (for text-only beats)
 ],                                          # fit: crop|blur ; zoom: none|punch|kenburns|out ; mute:true ; speed:1.0
 "captions": [ {"start":0.0,"end":1.8,"text":"10년 늦으면 [3억]이/사라진다?","style":"hook"} ],
                                             # times = OUTPUT timeline. [kw] = highlight, "/" = line break
                                             # style: hook (big, center) | main (lower-center) | top (label at top) | small
 "sfx":   [ {"t":0.0,"name":"impact","vol":0.8}, {"t":2.0,"src":"my.wav"} ],
 "voice": {"src":"vo.wav","vol":1.0,"offset":0},   # optional narration replacing nothing (mixed on top)
 "bgm":   {"src":"bgm.mp3","vol":0.22,"duck":true,"start":0,"fade_in":0.5,"fade_out":1.5},
 "highlight":"#FFD23F", "text":"#FFFFFF"
}
"""
import json, os, subprocess, sys, re, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.stderr.write(" ".join(cmd) + "\n" + p.stderr[-3000:]); sys.exit(1)
    return p

def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    j = json.loads(p.stdout or "{}")
    st = j.get("streams", [])
    return {"dur": float(j.get("format", {}).get("duration", 0) or 0),
            "audio": any(s["codec_type"] == "audio" for s in st),
            "video": next((s for s in st if s["codec_type"] == "video"), None)}

IMG = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp")

# ---------------- speech detection ----------------
def speech(path, noise=-32, mind=0.35):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise}dB:d={mind}", "-f", "null", "-"],
                       capture_output=True, text=True)
    dur = probe(path)["dur"]; spans = []; cur = 0.0
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            s = float(m.group(1))
            if s - cur > 0.08: spans.append([round(cur, 3), round(s, 3)])
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m: cur = float(m.group(1))
    if dur - cur > 0.08: spans.append([round(cur, 3), round(dur, 3)])
    return {"duration": round(dur, 3), "speech": spans}

# ---------------- segments ----------------
def zoom_expr(zoom, dur):
    d = max(dur, 0.1)
    return {"none": "1",
            "punch": "1+0.10*min(t/0.18\\,1)",
            "kenburns": f"1+0.12*t/{d:.3f}",
            "out": f"1.12-0.12*t/{d:.3f}"}.get(zoom or "none", "1")

def seg_filter(seg, W, H, fps, dur):
    z = zoom_expr(seg.get("zoom"), dur)
    fit = seg.get("fit", "crop")
    sp = float(seg.get("speed", 1.0))
    pre = f"setpts=(PTS-STARTPTS)/{sp}," if sp != 1.0 else "setpts=PTS-STARTPTS,"
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    zoomf = (f"scale=w='trunc({W}*({z})/2)*2':h='trunc({H}*({z})/2)*2':eval=frame,crop={W}:{H}" if z != "1" else "")
    if fit == "blur":
        v = (f"[0:v]{pre}fps={fps},split[a][b];"
             f"[a]{cover},boxblur=30:2,eq=brightness=-0.08[bg];"
             f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
             f"[bg][fg]overlay=(W-w)/2:(H-h)/2" + (f",{zoomf}" if zoomf else "") + ",setsar=1,format=yuv420p[v]")
    else:
        v = f"[0:v]{pre}fps={fps},{cover}" + (f",{zoomf}" if zoomf else "") + ",setsar=1,format=yuv420p[v]"
    return v

def render_segment(seg, i, tmp, W, H, fps):
    out = os.path.join(tmp, f"seg_{i:03d}.mp4")
    if "color" in seg:
        dur = float(seg["dur"])
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={seg['color']}:s={W}x{H}:r={fps}:d={dur}",
               "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
               "-filter_complex", "[0:v]format=yuv420p,setsar=1[v]", "-map", "[v]", "-map", "1:a"]
    else:
        src = seg["src"]; is_img = src.lower().endswith(IMG)
        info = probe(src)
        if is_img:
            dur = float(seg.get("dur", 3)); inp = ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", src]
        else:
            a = float(seg.get("in", 0)); b = float(seg.get("out", info["dur"]))
            dur = (b - a) / float(seg.get("speed", 1.0))
            inp = ["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src]
        vf = seg_filter(seg, W, H, fps, dur)
        use_audio = (not is_img) and info["audio"] and not seg.get("mute")
        sp = float(seg.get("speed", 1.0))
        if use_audio:
            atempo = f"atempo={sp}," if sp != 1.0 else ""
            af = (f"[0:a]{atempo}aresample=48000,aformat=channel_layouts=stereo,"
                  f"afade=t=in:st=0:d=0.03,afade=t=out:st={max(dur-0.03,0):.3f}:d=0.03[a]")
            cmd = ["ffmpeg", "-y", *inp, "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]"]
        else:
            cmd = ["ffmpeg", "-y", *inp, "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
                   "-filter_complex", vf, "-map", "[v]", "-map", "1:a"]
    cmd += ["-t", f"{dur:.3f}", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out]
    run(cmd); return out, dur

# ---------------- captions (ASS) ----------------
def ass_color(hexc, alpha="00"):
    h = hexc.lstrip("#"); r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(edl, W, H, path):
    hl = ass_color(edl.get("highlight", "#FFD23F")); tx = ass_color(edl.get("text", "#FFFFFF"))
    blk = "&H00000000"; shadow = "&H64000000"
    sty = [
        # name, font, size, align, marginV, outline
        ("hook", "Pretendard Black", 104, 5, 0, 7),
        ("main", "Pretendard ExtraBold", 76, 2, int(H * 0.30), 6),
        ("top", "Pretendard ExtraBold", 58, 8, int(H * 0.09), 5),
        ("small", "Pretendard ExtraBold", 48, 2, int(H * 0.20), 4),
    ]
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0",
             "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
             "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"]
    for n, f, s, al, mv, ol in sty:
        lines.append(f"Style: {n},{f},{s},{tx},{tx},{blk},{shadow},0,0,0,0,100,100,0,0,1,{ol},3,{al},70,70,{mv},1")
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for c in edl.get("captions", []):
        txt = c["text"].replace("{", "(").replace("}", ")")
        txt = re.sub(r"\[(.+?)\]", lambda m: "{\\c" + hl + "}" + m.group(1) + "{\\c" + tx + "}", txt)
        txt = txt.replace("/", "\\N")
        anim = c.get("anim", "pop")
        pre = {"pop": "{\\fscx82\\fscy82\\t(0,110,\\fscx100\\fscy100)}",
               "fade": "{\\fad(120,80)}", "none": ""}.get(anim, "")
        lines.append(f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},{c.get('style','main')},,0,0,0,,{pre}{txt}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

# ---------------- render ----------------
def render(edl_path, preview=False):
    edl = json.load(open(edl_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(edl_path))
    def P(p): return p if os.path.isabs(p) else os.path.join(base, p)
    for s in edl["segments"]:
        if "src" in s: s["src"] = P(s["src"])
    W, H, fps = int(edl.get("w", 1080)), int(edl.get("h", 1920)), int(edl.get("fps", 30))
    if preview: W, H = W // 2, H // 2
    out = P(edl.get("out", "final.mp4"))
    if preview: out = re.sub(r"\.mp4$", "_preview.mp4", out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fonts = P(edl.get("fonts", os.path.join(HERE, "fonts")))
    sfxdir = P(edl.get("sfx_dir", os.path.join(HERE, "sfx")))
    tmp = tempfile.mkdtemp(prefix="shorts_")
    segs = []; total = 0.0
    for i, s in enumerate(edl["segments"]):
        f, d = render_segment(s, i, tmp, W, H, fps); segs.append(f); total += d
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{f}'\n" for f in segs))
    joined = os.path.join(tmp, "joined.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    total = probe(joined)["dur"] or total
    # captions scaled for preview
    e2 = dict(edl)
    assf = os.path.join(tmp, "cap.ass")
    build_ass(e2, int(edl.get("w", 1080)), int(edl.get("h", 1920)), assf)  # full-res coords; libass scales for preview
    inputs = ["-i", joined]; fc = []; mix = ["[base]"]; idx = 1
    fc.append(f"[0:v]ass='{assf}':fontsdir='{fonts}'[v]")
    fc.append("[0:a]aformat=channel_layouts=stereo,aresample=48000[base0]")
    if edl.get("voice"):
        vo = edl["voice"]; inputs += ["-i", P(vo["src"])]
        ms = int(float(vo.get("offset", 0)) * 1000)
        fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={vo.get('vol',1.0)}[vo]")
        fc.append("[base0][vo]amix=inputs=2:normalize=0[base1]"); idx += 1; basen = "base1"
    else:
        basen = "base0"
    bg = edl.get("bgm")
    if bg and bg.get("duck", True):
        fc.append(f"[{basen}]asplit=3[base][sc][sc2]")
    else:
        fc.append(f"[{basen}]asplit=2[base][sc2]")
    for s in edl.get("sfx", []):
        f = P(s["src"]) if s.get("src") else os.path.join(sfxdir, s["name"] + ".wav")
        if not os.path.exists(f): sys.stderr.write(f"skip missing sfx {f}\n"); continue
        inputs += ["-i", f]; ms = int(float(s["t"]) * 1000)
        fc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={s.get('vol',0.7)}[s{idx}]")
        mix.append(f"[s{idx}]"); idx += 1
    if bg:
        inputs += ["-stream_loop", "-1", "-i", P(bg["src"])]
        st = float(bg.get("start", 0)); fo = float(bg.get("fade_out", 1.5)); fi = float(bg.get("fade_in", 0.5))
        chain = (f"[{idx}:a]atrim=start={st},asetpts=PTS-STARTPTS,atrim=0:{total:.3f},aresample=48000,"
                 f"aformat=channel_layouts=stereo,volume={bg.get('vol',0.22)},afade=t=in:st=0:d={fi},"
                 f"afade=t=out:st={max(total-fo,0):.3f}:d={fo}")
        if bg.get("duck", True):
            fc.append(chain + "[bgr]")
            fc.append("[bgr][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[bgm]")
        else:
            fc.append(chain + "[bgm]")
        mix.append("[bgm]"); idx += 1
    fc.append("[sc2]anullsink")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
           "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
           "-crf", "23" if preview else "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out]
    run(cmd); shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"out": out, "duration": round(total, 2), "w": W, "h": H}, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 3: print(__doc__); sys.exit(0)
    if sys.argv[1] == "speech":
        a = sys.argv[2:]; noise = -32; mind = 0.35
        if "--noise" in a: noise = float(a[a.index("--noise") + 1])
        if "--min" in a: mind = float(a[a.index("--min") + 1])
        print(json.dumps(speech(a[0], noise, mind), ensure_ascii=False))
    elif sys.argv[1] == "render":
        render(sys.argv[2], "--preview" in sys.argv)
```
