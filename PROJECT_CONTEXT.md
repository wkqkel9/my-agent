# 현재 작업 상태

작업 전 [AGENTS.md](AGENTS.md)와 [확정 기획](PLANNING.md)을 읽는다.

- 화면: `index.html`은 소개·영작/필사 데모, `writing.html`은 영작 전용 페이지다. 상단 탭은 소개·영작·필사·Docs이며, 영작은 별도 페이지로 이동한다.
- 다음 영작 고도화 범위: 사용자는 주제와 CEFR 난이도만 선택한다. 초기에는 영어 인터뷰를 우선하며, 외부 기준과 자동 검증을 통과한 독립 제작 문제를 4단계로 제공한다. 오답·시간 종료를 학습 요소별로 누적해 취약 요소의 출제 비중을 높이고, 시간 종료 시 해당 단계의 대표 답안 하나를 공개한다. 아직 앱에는 구현하지 않았다.
- 공통 코드: `writing.js`가 두 페이지의 영작 연습·AI 평가를 담당하고 `site.css`가 공통 디자인을 제공한다. 필사 코드는 소개 페이지에만 있다. `.github/workflows/pages.yml`에서 새 HTML·JS·CSS를 함께 배포한다.
- 공개 앱 주소: https://wkqkel9.github.io/my-agent/ (GitHub Pages). 수정 후 검증·커밋·푸시·배포 성공·실제 공개 반영까지 확인한다.
- 구현: 영작 입력 아래 액션 버튼 행을 제거했다. Enter 또는 모바일 키보드 전송으로 제출한다. 문장마다 60초, 정답 시 즉시 다음 문장, 시간 종료 후 내 답·한글 뜻 비교와 Enter·입력창 클릭으로 진행한다.
- AI 평가 연동: 등록된 정답과 일치하면 브라우저에서 즉시 통과한다. 그 외 모든 입력은 `https://writing-server.vercel.app/api/assess` → Groq `openai/gpt-oss-120b`로 판정한다. 브라우저 수동 오류 판정은 제거했다. 동일 단계·동일 원문 입력의 AI 결과를 메모리에 최대 100개 재사용하고, 진행 중 중복 제출은 무시한다. 응답 대기 중에는 피드백을 숨기고 평가 중 안내를 표시하지 않으며, 결과·실패가 도착했을 때만 표시한다. 25초 대기 후 실패·재시도를 안내하며, 수정·재제출·단계 이동·시간 종료 이후의 오래된 응답은 무시한다.
- 피드백: 불필요한 표현 → 틀린 표현 → 빠진 표현 순서로 한 항목만 표시한다. 추가된 표현은 철자가 틀려도 전체를 먼저 표시하며, 수정 후 재제출하면 다시 판정한다. 정답·교정 표현·예시는 반복 제출·시간 종료에도 공개하지 않는다. 판정 불가 안내에도 예시를 넣지 않는다.
- 백엔드: `/home/user/work/writing-server` 독립 저장소의 `master` 브랜치. `evaluator.py`(Groq 평가), `api/index.py`(Vercel HTTP API), `main.py`(로컬 HTTP API), `db.py`(로컬 SQLite). 비밀 파일은 Git에서 제외하며 Vercel Production의 `GROQ_API_KEY`, `GROQ_MODEL` 환경변수로 운영한다.
- Groq 배포 확인: 서버 커밋 `9238312`, Vercel 배포 `dpl_9KwVydoiTssqRkxNhSV5eTM7WU8G` READY. 공개 API와 실제 브라우저에서 Groq 시제 오류 응답을 확인했다. 힌트는 한글로만 허용하고 교정 영어가 섞이면 평가 실패로 처리한다. 본동사 시제 변경은 불필요한 표현이 아닌 시제 오류로 판정하도록 지시한다.
- 속도 최적화: 120B `reasoning_effort=low`, 간결한 지시문·구조화 JSON·출력 상한 1024토큰. 형식 검증 실패에만 medium으로 한 차례 재평가한다. 직접 Groq 호출 8개 사례는 0.51~0.87초로 모두 통과했다. 공개 Vercel API의 동일 3개 입력은 기존 1.86~4.59초에서 0.96~1.16초로 측정됐다(소수 표본이며 지연 변동 가능).
- 페이지 분리 검증: 소개·영작 양쪽의 기존 AI 연습 회귀 테스트 통과. 1280·390·360px에서 소개/영작 탭·활성 표시·필사 체험 복귀·필사 입력·영작 단계 진행·가로 넘침·스크립트 오류 검증 통과.
- 현재 검증: AI 전용 요청·등록 정답 즉시 통과·빈 입력 전달·오래된 응답 무시·편집 중 응답 무시·실패 재시도·AI 정답 후 진행 테스트 통과. PC·모바일(1280·390px)의 AI 피드백·입력 하이라이트·실패 안내·단계 이동·가로 넘침·스크립트 오류 검증 통과.
- 기능 안내 챗봇 소스: `/home/user/work/ask-once/faq.json`, `chatbot.js`. API 요청 없이 검토한 FAQ로 답한다. `build_chatbot.py --output /home/user/work/my-agent/chatbot.js`로 실행 파일을 생성하고, Pages에서 HTML과 함께 배포한다. 분류·하위 질문·뒤로 가기와 실행 중 기능 문맥을 제공한다. PC·모바일(1280·390·360px) 분류·하위 질문·후속 입력·이동·초기화·스크립트 오류 검증과 기존 영작 회귀 검증을 통과했다. 공개 사이트에서도 동일한 챗봇 검증을 통과했으며 HTML·JS의 HTTP 200과 로컬 파일 일치를 확인했다.
- 시스템 Node가 없어 검증에는 `/tmp`의 Playwright Node와 Chromium을 사용했다. 일반 환경에서는 `node tests/expansion.test.js`, Playwright·Chromium 설치 후 `python tests/expansion.browser.py`로 실행한다.
- 로컬 Docs 미리보기는 Homebrew Ruby와 프로젝트 내부 `vendor/bundle`을 사용하는 `bin/docs`로 실행한다. 주소는 `http://127.0.0.1:4000/my-agent/docs.html`이며 설치 패키지·빌드 결과·Bundler 로컬 설정은 Git에서 제외한다.
- AGENTS.md를 공통 지침 원본으로 두고 Claude·Gemini·Cursor·Copilot용 파일에서 연결한다. 자동 로딩 여부는 각 도구 설정에 따라 다르다.

- 문서 위치: [PLANNING.md](PLANNING.md)는 기능별 기획의 목차이며, 세부 기획은 `planning/`, 구현·배포 구조는 [ARCHITECTURE.md](ARCHITECTURE.md), 회차별 기록은 `lesson/`에 유지한다. 배포 확인 완료 주소:
  - 아키텍처 문서: https://wkqkel9.github.io/my-agent/ARCHITECTURE.html
  - 소개 기획: https://wkqkel9.github.io/my-agent/planning/introduction.html
  - 영작 기획: https://wkqkel9.github.io/my-agent/planning/writing.html
  - 필사 기획: https://wkqkel9.github.io/my-agent/planning/transcription.html
  - 챗봇 기획: https://wkqkel9.github.io/my-agent/planning/chatbot.html
  - Lesson 2: https://wkqkel9.github.io/my-agent/lesson/lesson2.html
  - Lesson 3: https://wkqkel9.github.io/my-agent/lesson/lesson3.html
  - Lesson 4: https://wkqkel9.github.io/my-agent/lesson/lesson4.html
  - Lesson 5: https://wkqkel9.github.io/my-agent/lesson/lesson5.html
  - Lesson 6: https://wkqkel9.github.io/my-agent/lesson/lesson6.html


- 문서 배포: `.github/workflows/pages.yml`에 `ARCHITECTURE.md`를 포함하며, 렌더링 후 `docs.html`·`PLANNING.html`·`ARCHITECTURE.html`의 생성 여부를 검사한다. `ARCHITECTURE.md`는 현재 Pages → Vercel → Groq 흐름을 설명한다.
- Docs UI: `_layouts/default.html`과 `wiki.css`에서 공통 헤더·문서 본문·사이드바를 제공한다. 이번 변경은 최상위 접기·폴더 구분선·파일 아이콘을 제거하고, lesson의 꺾쇠·한 단계 들여쓰기·선택 배경을 정리했다. 기본 문서는 PLANNING.md이며 docs.html·각 문서 URL에서 같은 사이드바를 유지한다. 배포 후 PC·모바일(1280·390·360px)에서 부모 항목 정렬·하위 문서 12px 들여쓰기·선택 표시·접기·키보드·문서 이동·기존 주소 연결·가로 넘침 검증을 통과했다. 공개 화면 이미지와 배포 CSS 일치도 확인했다.
