# 현재 작업 상태

작업 전 [AGENTS.md](AGENTS.md)와 [확정 기획](PLANNING.md)을 읽는다.

- 앱: `index.html`의 영어 문장 확장·따라 쓰기 연습. 배포 설정은 `.github/workflows/pages.yml`.
- 최신 확인 앱 배포: 커밋 `940ab4c`, GitHub Actions 실행 `44239799664` 성공. 주소: https://wkqkel9.github.io/my-agent/
- 로컬 구현: 영작 입력 아래 액션 버튼 행을 제거했다. Enter 또는 모바일 키보드 전송으로 제출한다. 문장마다 60초, 정답 시 즉시 다음 문장, 시간 종료 후 답·예시 비교와 Enter·입력창 클릭으로 진행한다.
- 피드백: 허용 표현·어순과 `I read a book`을 인정한다. 철자·문법 오류 위치, 누락된 뜻, 주어·동사·목적어 안내를 제공하며 반복 제출 시 누락 표현의 구체적인 힌트를 보여준다. 수정하면 이전 오류 표시를 지운다. 판정하기 어려운 답은 오답으로 단정하지 않고 예시를 제공한다.
- 연습 종료 시 실제 정답 수를 표시하며 시간 초과 문장은 정답으로 세지 않는다. 범용 AI 판정은 없고 네 문장 체험의 규칙·허용 표현에 한정된다.
- 검증: `tests/expansion.test.js`의 32개 판정 사례와 상태·입력 테스트 통과. `tests/expansion.browser.py`로 Chromium PC(1280px)·모바일(390px)의 진행·피드백·시간 종료·재시작·화면 넘침·스크립트 오류를 확인했다. 모바일 피드백 화면도 이미지로 확인했다.
- 위 구현은 공개 사이트에 배포됐다. HTTP 200, 배포 HTML과 로컬 파일 일치, 실제 공개 사이트의 PC·모바일 브라우저 테스트 통과를 확인했다.
- 시스템 Node가 없어 검증에는 `/tmp`의 Playwright Node와 Chromium을 사용했다. 일반 환경에서는 `node tests/expansion.test.js`, Playwright·Chromium 설치 후 `python tests/expansion.browser.py`로 실행한다.
- AGENTS.md를 공통 지침 원본으로 두고 Claude·Gemini·Cursor·Copilot용 파일에서 연결한다. 자동 로딩 여부는 각 도구 설정에 따라 다르다.
