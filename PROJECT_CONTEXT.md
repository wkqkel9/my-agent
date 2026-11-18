# 현재 작업 상태

작업 전 [AGENTS.md](AGENTS.md)와 [확정 기획](PLANNING.md)을 읽는다.

- 앱: `index.html`의 영어 문장 확장·따라 쓰기 연습. 배포 설정은 `.github/workflows/pages.yml`.
- 공개 앱 주소: https://wkqkel9.github.io/my-agent/ (GitHub Pages). 수정 후 검증·커밋·푸시·배포 성공·실제 공개 반영까지 확인한다.
- 구현: 영작 입력 아래 액션 버튼 행을 제거했다. Enter 또는 모바일 키보드 전송으로 제출한다. 문장마다 60초, 정답 시 즉시 다음 문장, 시간 종료 후 내 답·한글 뜻 비교와 Enter·입력창 클릭으로 진행한다.
- AI 평가 연동: 등록된 정답과 일치하면 브라우저에서 즉시 통과한다. 그 외 모든 입력은 `https://writing-server.vercel.app/api/assess` → Groq `openai/gpt-oss-120b`로 판정한다. 브라우저 수동 오류 판정은 제거했다. 25초 대기 후 실패·재시도를 안내하며, 수정·재제출·단계 이동·시간 종료 이후의 오래된 응답은 무시한다.
- 피드백: 불필요한 표현 → 틀린 표현 → 빠진 표현 순서로 한 항목만 표시한다. 추가된 표현은 철자가 틀려도 전체를 먼저 표시하며, 수정 후 재제출하면 다시 판정한다. 정답·교정 표현·예시는 반복 제출·시간 종료에도 공개하지 않는다. 판정 불가 안내에도 예시를 넣지 않는다.
- 백엔드: `/home/user/work/writing-server` 독립 저장소의 `master` 브랜치. `evaluator.py`(Groq 평가), `api/index.py`(Vercel HTTP API), `main.py`(로컬 HTTP API), `db.py`(로컬 SQLite). 비밀 파일은 Git에서 제외하며 Vercel Production의 `GROQ_API_KEY`, `GROQ_MODEL` 환경변수로 운영한다.
- Groq 배포 확인: 서버 커밋 `b9377b2`, Vercel 배포 `dpl_EyYfFFCq7h9eDbzu6qjDFVvTiujB` READY. 공개 API HTTP 200·Groq 모델·정답/추가/오류/누락 판정·하이라이트 범위·CORS를 확인했다. 힌트는 한글로만 허용하고 교정 영어가 섞이면 평가 실패로 처리한다. 본동사 시제 변경은 불필요한 표현이 아닌 시제 오류로 판정하도록 지시한다.
- 현재 검증: AI 전용 요청·등록 정답 즉시 통과·빈 입력 전달·오래된 응답 무시·편집 중 응답 무시·실패 재시도·AI 정답 후 진행 테스트 통과. PC·모바일(1280·390px)의 AI 피드백·입력 하이라이트·실패 안내·단계 이동·가로 넘침·스크립트 오류 검증 통과.
- 기능 안내 챗봇 소스: `/home/user/work/ask-once/faq.json`, `chatbot.js`. API 요청 없이 검토한 FAQ로 답한다. `build_chatbot.py --output /home/user/work/my-agent/chatbot.js`로 실행 파일을 생성하고, Pages에서 HTML과 함께 배포한다. 분류·하위 질문·뒤로 가기와 실행 중 기능 문맥을 제공한다. PC·모바일(1280·390·360px) 분류·하위 질문·후속 입력·이동·초기화·스크립트 오류 검증과 기존 영작 회귀 검증을 통과했다. 공개 사이트에서도 동일한 챗봇 검증을 통과했으며 HTML·JS의 HTTP 200과 로컬 파일 일치를 확인했다.
- 시스템 Node가 없어 검증에는 `/tmp`의 Playwright Node와 Chromium을 사용했다. 일반 환경에서는 `node tests/expansion.test.js`, Playwright·Chromium 설치 후 `python tests/expansion.browser.py`로 실행한다.
- AGENTS.md를 공통 지침 원본으로 두고 Claude·Gemini·Cursor·Copilot용 파일에서 연결한다. 자동 로딩 여부는 각 도구 설정에 따라 다르다.

- 문서 위치: [PLANNING.md](PLANNING.md), [ARCHITECTURE.md](ARCHITECTURE.md) 및 [lesson/lesson2.md](lesson/lesson2.md) ~ [lesson/lesson6.md](lesson/lesson6.md)에 문서를 유지한다. 배포 확인 완료 주소:
  - 아키텍처 문서: https://wkqkel9.github.io/my-agent/ARCHITECTURE.html
  - Lesson 2: https://wkqkel9.github.io/my-agent/lesson/lesson2.html
  - Lesson 3: https://wkqkel9.github.io/my-agent/lesson/lesson3.html
  - Lesson 4: https://wkqkel9.github.io/my-agent/lesson/lesson4.html
  - Lesson 5: https://wkqkel9.github.io/my-agent/lesson/lesson5.html
  - Lesson 6: https://wkqkel9.github.io/my-agent/lesson/lesson6.html


- Docs UI: `_layouts/default.html`과 `wiki.css`에서 공통 헤더·문서 본문·사이드바를 제공한다. 이번 변경은 최상위 접기·폴더 구분선·파일 아이콘을 제거하고, lesson의 꺾쇠·한 단계 들여쓰기·선택 배경을 정리했다. 기본 문서는 PLANNING.md이며 docs.html·각 문서 URL에서 같은 사이드바를 유지한다. 배포 후 PC·모바일(1280·390·360px)에서 부모 항목 정렬·하위 문서 12px 들여쓰기·선택 표시·접기·키보드·문서 이동·기존 주소 연결·가로 넘침 검증을 통과했다. 공개 화면 이미지와 배포 CSS 일치도 확인했다.
