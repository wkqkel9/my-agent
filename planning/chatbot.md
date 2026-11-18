---
layout: default
title: 기능 안내 챗봇 기획
permalink: /planning/chatbot.html
docs_group: planning
planning_order: 4
---

# 기능 안내 챗봇

- 우측 하단 챗봇은 영작·필사 이용 방법을 검토된 FAQ와 규칙으로 안내하며 실시간 모델 API를 호출하지 않는다.
- 기능 분류 → 세부 질문 → 복귀 경로를 제공하고, 직접 입력한 후속 질문도 선택 중인 기능 문맥으로 처리한다.
- FAQ 원본과 챗봇 소스는 `ask-once` 프로젝트에서 관리하고, 현재 프로젝트에는 생성된 실행 파일 `chatbot.js`만 배포한다.
