# Phase 0 — 기존 코드 감사 (2026-10-25)

지침서 `docs/upgrade-guide.md` 14장 1~4번에 대한 결과. 코드를 직접 읽고 정리했다.

## 1. 데이터 흐름 (실제)

```
data.json ─(pipeline.load: 템플릿 기본값 + 저장값)→ full
full ─(templates/<t>.build)→ scenes[(이름, 초, draw_fn)], captions[(시작, 끝, 문구, anim?)], sfx[], note, extras?
     ─(pipeline.assemble)→ pieces(장면 조각) + apply_edits(끼워넣기·구간 삭제) + map_time(템플릿 시간 → 최종 시간)
                          + tl.cap_times / tl.sfx 덮어쓰기 + 사용자 항목(texts·overlays·voices·markers, 최종 시간)
     ─(pipeline.render)→ 장면 클립(gfx.write_clip, 캐시) + edl.json ─(shorts-kit/build.py)→ final(_preview).mp4
```

## 2. 질문별 답

| 질문 | 답 |
|---|---|
| 데이터 구조 | `data.json` 하나에 평평하게 저장. ① 공통: `template, title, is_sample, review_no, review_exp, upload` ② 템플릿 입력값(FIELDS 키, 자막은 `c_*`) ③ 편집 층: `edits`(insert/cut), `texts`, `overlays`, `voices`, `markers`, `tl.cap_times`, `tl.sfx`, `bgm`. 스키마 버전 없음 |
| 장면 생성 위치 | 각 템플릿의 `build(data)`. 장면 = Pillow 그리기 함수(시간 t → 프레임). 장면 ID = 템플릿 안 이름(`s1`…, `w1`…, `e1`…) — 템플릿 안에서 고정이라 ID로 쓸 수 있다 |
| 시간 전달 경로 | 템플릿 시간(장면을 이어 붙인 기준) → `apply_edits`가 조각을 자르고 끼움 → `map_time`으로 템플릿 자막·효과음을 최종 시간으로 → `tl.*`·사용자 항목은 이미 최종 시간 → `render`가 조각을 edl `segments`(in/out)로 |
| 삽입·삭제·자막 이동 | 서버: `edits` 목록을 순서대로 적용. 화면(index.html): 사용자 항목을 `shiftAfter`/`collapse`로 함께 밈(리플). 자막 이동은 `tl.cap_times`(최종 시간 절대값) |
| 장면 캐시 의존성 | `scene_key` = 해시(데이터 중 NON_SCENE·`c_*` 제외 전부, 배율, 템플릿·gfx 파일 수정 시각). **전체 장면 묶음 하나**에 대해 판정(all-or-nothing). 그리기 함수가 data 전체를 클로저로 참조 → 장면별 의존 필드를 코드에서 정적으로 알 수 없음 |
| 기존 데이터를 바꾸지 않고 공통 모델로 변환? | **가능.** Shot = 템플릿 장면(+ 끼워넣은 화면), Segment = `pieces`, TimelineItem = 자막·글자·얹기·효과음·내레이션·BGM·준법 표기, Asset = 장면 클립·미디어 파일. 키프레임은 기존 데이터에 없음 → 빈 목록(그린 장면은 대표 프레임을 자동 썸네일로) |

## 3. 가장 작은 변경안 (채택)

- **파생 모델**: `studio/model.py`가 `assemble()` 결과에서 Project/Shot/Keyframe/Asset/Segment/TimelineItem을 **계산해서** 돌려준다. 저장 형식은 그대로라 기존 프로젝트를 깨지 않는다. `GET /api/model/<id>` + 검증 결과.
- **장면 덮어쓰기 층(새 키, 선택)**: `schema_version: 2`, `shots: {장면ID: {dur, src, kind, color, fit, purpose, desc, hidden, keyframes}}`, `shot_order: [장면ID…]`, 사용자 장면은 `shots`에 `user: true`. 없으면 템플릿 기본 그대로 → 하위 호환.
- **템플릿 자막·효과음은 소속 장면을 따라간다**: 템플릿 시간에서 어느 장면에 속했는지(+장면 안 상대 시간)를 계산해, 순서·길이가 바뀐 새 배치로 옮긴다.
- **장면별 캐시**: 장면 클립 파일 이름에 장면별 키(전역 장면 데이터 해시 + 장면 이름 + 길이 + 배율 + 코드 수정 시각)를 넣는다. 길이·순서·소스 교체는 그 장면만 다시 그린다.

## 4. 마이그레이션

- 자동 변환 없음(파생 모델). 기존 파일은 열 때 바뀌지 않는다. 장면 편집을 처음 저장할 때만 `schema_version: 2`와 `shots`가 생긴다.
- 기존 `edits`(끼워넣기·구간 삭제)는 그대로 최종 시간 층에서 동작한다.

## 5. 위험과 결정

| 위험 | 결정 |
|---|---|
| **충돌**: 장면 순서·길이 변경과 기존 리플 편집(`edits`, 최종 시간 기준)이 섞이면 끼워넣은 화면이 엉뚱한 장면 안으로 들어간다 | 1단계에서는 `edits`가 있는 프로젝트의 장면 순서·길이 변경을 **막고 이유를 표시**. 대안(다음 단계): 끼워넣기를 사용자 장면으로 변환하는 마이그레이션 |
| 사용자 항목(글자·얹기·내레이션·마커·tl.*)은 최종 시간이라 장면 순서가 바뀌면 제자리에 남는다 | 화면이 장면 변경 직전·직후 배치를 비교해 **소속 장면을 따라 옮긴다**(`remapByShots`) |
| 장면별 데이터 의존성을 정적으로 모름 | 템플릿 입력값이 바뀌면 그 템플릿의 그린 장면은 **전부** 무효(보수적). 길이·순서·소스 교체·자막·효과음 변경은 해당 장면만/재사용 |
| 그린 장면의 길이 변경 | 같은 그리기 함수를 새 길이로 다시 그림: 늘리면 마지막 상태가 유지되고, 줄이면 뒤 애니메이션이 잘림 |
| 말하는 마스코트(`templates/talk.py`) | 작업 중(WIP). `pipeline.TEMPLATES`에 아직 등록하지 않음 — 렌더 연결·대본 편집 화면 미완성 |
