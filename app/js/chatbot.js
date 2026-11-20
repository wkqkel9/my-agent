// Connected to local Python backend (server.py -> main.py & bot.py).
(() => {
  'use strict';

  const fab = document.querySelector('#chatFab');
  const panel = document.querySelector('#chatPanel');
  const input = document.querySelector('#chatInput');
  const log = document.querySelector('#chatLog');
  const options = document.querySelector('#chatOptions');
  const form = document.querySelector('#chatForm');
  const closeBtn = document.querySelector('#closeChat');

  if (!fab || !panel || !input || !log || !options || !form || !closeBtn) return;

  // mode: 'menu' | 'ask_name' | 'chat' | 'search'
  let mode = 'menu';
  let userName = '사용자';
  let busy = false;

  function appendMessage(text, isUser = false) {
    const node = document.createElement('div');
    node.className = 'message' + (isUser ? ' user' : '');
    node.style.whiteSpace = 'pre-line';
    node.textContent = text;
    log.append(node);
    log.scrollTop = log.scrollHeight;
  }

  function renderChoices(items) {
    options.replaceChildren();
    for (const item of items) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = item.label;
      button.addEventListener('click', item.action);
      options.append(button);
    }
  }

  function showMenu(announce = true) {
    mode = 'menu';
    input.placeholder = '메뉴 번호(1, 2, 3)를 입력하거나 버튼을 누르세요';
    if (announce) {
      appendMessage('--- typing Agent ---\n원하는 메뉴를 선택하세요.');
    }
    renderChoices([
      { label: '1. 프로젝트 소개', action: () => selectMenu('1', '1. 프로젝트 소개') },
      { label: '2. FAQ 대화', action: () => selectMenu('2', '2. FAQ 대화') },
      { label: '3. 문법 뜻으로 찾기', action: () => selectMenu('3', '3. 문법 뜻으로 찾기') },
    ]);
  }

  async function selectMenu(choice, userLabel) {
    if (busy) return;
    if (userLabel) appendMessage(userLabel, true);
    busy = true;
    try {
      const res = await fetch('/api/menu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMessage(data.error || '요청을 처리하지 못했습니다.');
        return;
      }

      appendMessage(data.message);
      if (choice === '2') {
        mode = 'ask_name';
        input.placeholder = '이름 또는 별명 입력 (건너뛰기 가능)';
        renderChoices([
          {
            label: "건너뛰기 ('사용자'로 시작)",
            action: () => startChat('사용자', true),
          },
          { label: '‹ 메뉴로 돌아가기', action: () => showMenu(true) },
        ]);
      } else if (choice === '3') {
        mode = 'search';
        input.placeholder = "문법 질문 입력 (끝내려면 '그만')";
        renderChoices([
          { label: '예: did 다음에 went를 써도 돼?', action: () => sendSearch('did 다음에 went를 써도 돼?') },
          { label: '그만 (메뉴로)', action: () => sendSearch('그만') },
        ]);
      } else {
        showMenu(false);
      }
    } catch (err) {
      appendMessage('로컬 서버(server.py)에 연결할 수 없습니다. python3 server.py가 실행 중인지 확인하세요.');
    } finally {
      busy = false;
    }
  }

  function startChat(name, fromButton = false) {
    userName = (name || '').trim() || '사용자';
    mode = 'chat';
    if (fromButton) appendMessage(`이름: ${userName}`, true);
    appendMessage(`영작 Agent 이용 방법을 물어보세요. (${userName}님)\n끝내려면 '그만'을 입력하세요.`);
    input.placeholder = "질문을 입력하세요 (끝내려면 '그만')";
    renderChoices([
      { label: '그만 (메뉴로)', action: () => sendQuestion('그만') },
    ]);
    input.focus();
  }

  async function sendQuestion(question) {
    if (busy) return;
    const trimmed = question.trim();
    if (!trimmed) return;

    appendMessage(trimmed, true);
    busy = true;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed, name: userName }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMessage(data.error || '답변을 가져오지 못했습니다.');
        return;
      }
      if (data.ended) {
        appendMessage(data.answer);
        showMenu(true);
      } else {
        appendMessage(`typing: ${data.answer}`);
      }
    } catch (err) {
      appendMessage('로컬 서버(server.py)에 연결할 수 없습니다. python3 server.py가 실행 중인지 확인하세요.');
    } finally {
      busy = false;
    }
  }

  async function sendSearch(question) {
    if (busy) return;
    const trimmed = question.trim();
    if (!trimmed) return;

    appendMessage(trimmed, true);
    busy = true;
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendMessage(data.error || '문법 자료를 검색하지 못했습니다.');
        return;
      }
      if (data.ended) {
        appendMessage(data.message);
        showMenu(true);
        return;
      }
      const resultText = data.results
        .map((item) => `${item.rank}위 (${item.score.toFixed(3)}) · ${item.text}`)
        .join('\n');
      appendMessage(`[가까운 문법 자료 3개]\n${resultText}\n\n--- AI에게 보낼 질문 ---\n${data.prompt}`);
    } catch (err) {
      appendMessage('로컬 서버(server.py)에 연결할 수 없습니다. python3 server.py가 실행 중인지 확인하세요.');
    } finally {
      busy = false;
    }
  }

  function setOpen(open) {
    panel.hidden = !open;
    fab.setAttribute('aria-expanded', String(open));
    (open ? input : fab).focus();
  }

  fab.addEventListener('click', () => setOpen(panel.hidden));
  closeBtn.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) setOpen(false);
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (busy) return;
    const value = input.value.trim();
    input.value = '';

    if (mode === 'menu') {
      if (value === '1') {
        selectMenu('1', '1');
      } else if (value === '2') {
        selectMenu('2', '2');
      } else if (value === '3') {
        selectMenu('3', '3');
      } else if (value === '0') {
        selectMenu('0', '0');
      } else {
        if (value) appendMessage(value, true);
        appendMessage('1, 2, 3, 0 중에서 선택하세요.');
      }
      return;
    }

    if (mode === 'ask_name') {
      if (value) appendMessage(value, true);
      startChat(value || '사용자', false);
      return;
    }

    if (mode === 'chat') {
      if (!value) return;
      sendQuestion(value);
      return;
    }

    if (mode === 'search') {
      if (!value) return;
      sendSearch(value);
    }
  });

  log.replaceChildren();
  showMenu(true);

  async function runCaptureDemo() {
    const params = new URLSearchParams(window.location.search);
    const capture = params.get('capture');
    if (!['search', 'faq'].includes(capture)) return;
    setOpen(true);
    if (capture === 'search') {
      await selectMenu('3', '3. 문법 뜻으로 찾기');
      await sendSearch('did 다음에 went를 써도 돼?');
      log.scrollTop = 210;
      return;
    }
    await selectMenu('2', '2. FAQ 대화');
    startChat('사용자', true);
    await sendQuestion('영작 시간은 몇 초야?');
    await sendQuestion('영작이랑 필사는 뭐가 달라?');
  }

  runCaptureDemo();
})();
