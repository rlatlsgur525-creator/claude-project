# claude-project

여러 컴퓨터(서브·메인)에서 같이 작업하는 프로젝트입니다. 코드와 설정은 GitHub 비공개 저장소로 동기화합니다.

## 작업 규칙
- 작업을 시작하기 전에 `git pull`로 최신 상태를 받습니다.
- 작업을 마치면 커밋하고 `git push`로 올립니다.
- 컴퓨터마다 다른 개인 설정은 `.claude/settings.local.json`에 둡니다(커밋하지 않음).
- 비밀번호, API 키, `.env` 파일은 커밋하지 않습니다.

## 프로젝트
- `naver-blog/` — 동네 가게 사장님 대상 네이버 블로그. 작업 전 `naver-blog/CLAUDE.md` → `naver-blog/HANDOFF.md` 순서로 읽습니다.
- `miracle-shorts/` — 미라클톡 유튜브 쇼츠. 작업 전 `miracle-shorts/CLAUDE.md`를 읽습니다.
