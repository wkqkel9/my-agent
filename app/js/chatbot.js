// ── auth ──────────────────────────────────────────────────────────
let authToken = localStorage.getItem('jwt') || null;
let authRefreshToken = localStorage.getItem('refresh_token') || null;

const authBox     = document.getElementById('authBox');
const authOverlay = document.getElementById('authOverlay');
const authTitle   = document.getElementById('authTitle');
const authEyebrow = document.getElementById('authEyebrow');
const authSubmit  = document.getElementById('authSubmit');
const authMsg     = document.getElementById('authMsg');
const authUsernameEl = document.getElementById('authUsername');
const toggleAuth  = document.getElementById('toggleAuth');
const authBtn     = document.getElementById('authBtn');
const authClose   = document.getElementById('authClose');

let authMode = 'login'; // 'login' | 'signup'

function showAuth(show = true) {
  if (!authBox) return;
  authBox.hidden = !show;
  if (authOverlay) authOverlay.hidden = !show;
  if (show) authUsernameEl?.focus();
}

function setAuthMode(mode) {
  authMode = mode;
  const isSignup = mode === 'signup';
  if (authTitle)   authTitle.textContent   = isSignup ? '회원가입' : '로그인';
  if (authEyebrow) authEyebrow.textContent  = isSignup ? 'Sign up'  : 'Sign in';
  if (authSubmit)  authSubmit.textContent   = isSignup ? '회원가입' : '로그인';
  const passwordInput = document.getElementById('authPwd');
  if (passwordInput) {
    passwordInput.autocomplete = isSignup ? 'new-password' : 'current-password';
    passwordInput.minLength = isSignup ? 6 : 1;
    passwordInput.placeholder = isSignup ? '비밀번호 (6자 이상)' : '비밀번호';
  }
  if (toggleAuth)  toggleAuth.textContent   = isSignup ? '이미 계정이 있어요 → 로그인' : '회원가입';
  if (authMsg)     authMsg.textContent      = '';
}
setAuthMode('login');

function updateAuthBtn() {
  if (!authBtn) return;
  if (authToken) {
    authBtn.textContent = '로그아웃';
    authBtn.onclick = async () => {
      await fetch('/api/logout', { method: 'POST', headers: authToken ? {Authorization: `Bearer ${authToken}`} : {} }).catch(() => {});
      localStorage.removeItem('jwt');
      localStorage.removeItem('refresh_token');
      authToken = null;
      authRefreshToken = null;
      updateAuthBtn();
      if (document.body.dataset.protectedFeature) guardPractice(document.body.dataset.protectedFeature);
      document.querySelectorAll('[data-practice-gate]').forEach(gate => guardPractice(gate.dataset.practiceGate, gate.id));
    };
  } else {
    authBtn.textContent = '로그인';
    authBtn.onclick = () => { setAuthMode('login'); showAuth(true); };
  }
  window.dispatchEvent(new Event('authchange'));
}
updateAuthBtn();

async function guardPractice(feature, gateId = 'practiceGate') {
  const gate = document.getElementById(gateId);
  if (!gate) return;
  const content = document.getElementById('practiceContent');
  if (authToken) {
    gate.hidden = true;
    if (content) content.hidden = false;
  } else {
    // 로그인 전 표시 상태는 writing.js의 20문장 체험 카운터가 관리한다.
    window.dispatchEvent(new Event('trialgatecheck'));
  }
}
document.getElementById('practiceLogin')?.addEventListener('click',()=>{setAuthMode('login');showAuth(true);});
guardPractice(document.body.dataset.protectedFeature);
document.querySelectorAll('[data-practice-gate]').forEach(gate => guardPractice(gate.dataset.practiceGate, gate.id));

toggleAuth?.addEventListener('click', e => {
  e.preventDefault();
  setAuthMode(authMode === 'login' ? 'signup' : 'login');
});
authClose?.addEventListener('click', () => showAuth(false));
authOverlay?.addEventListener('click', () => showAuth(false));

authSubmit?.addEventListener('click', async () => {
  const username = authUsernameEl?.value.trim();
  const pwd   = document.getElementById('authPwd')?.value;
  if (!username || !pwd) { if (authMsg) authMsg.textContent = '아이디와 비밀번호를 입력하세요.'; return; }

  const isSignup = authMode === 'signup';
    const url  = isSignup ? '/api/signup' : '/api/login';
  const body = { username, pwd };

  try {
    const res  = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '요청 실패');

    if (isSignup) {
      if (data.session?.access_token) {
        authToken = data.session.access_token;
        authRefreshToken = data.session.refresh_token;
        localStorage.setItem('jwt', authToken);
        if (authRefreshToken) localStorage.setItem('refresh_token', authRefreshToken);
        showAuth(false); updateAuthBtn();
        if (document.body.dataset.protectedFeature) guardPractice(document.body.dataset.protectedFeature);
        document.querySelectorAll('[data-practice-gate]').forEach(gate => guardPractice(gate.dataset.practiceGate, gate.id));
      } else {
        setAuthMode('login');
        if (authMsg) authMsg.textContent = data.message || '가입했습니다. 이메일 인증이 필요하면 메일을 확인한 뒤 로그인하세요.';
      }
    } else {
      authToken = data.token;
      authRefreshToken = data.refresh_token;
      localStorage.setItem('jwt', authToken);
      if (authRefreshToken) localStorage.setItem('refresh_token', authRefreshToken);
      showAuth(false);
      updateAuthBtn();
      if (document.body.dataset.protectedFeature) guardPractice(document.body.dataset.protectedFeature);
      document.querySelectorAll('[data-practice-gate]').forEach(gate => guardPractice(gate.dataset.practiceGate, gate.id));
    }
  } catch (e) {
    if (authMsg) authMsg.textContent = e.message;
  }
});

// ── api helper ────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  let response = await fetch(url, { ...opts, headers });
  if (response.status === 401 && authRefreshToken && url !== '/api/refresh') {
    const refreshed = await fetch('/api/refresh', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:authRefreshToken})});
    if (refreshed.ok) {
      const session = await refreshed.json();
      authToken = session.token; authRefreshToken = session.refresh_token;
      localStorage.setItem('jwt', authToken); localStorage.setItem('refresh_token', authRefreshToken);
      headers.Authorization = `Bearer ${authToken}`;
      response = await fetch(url, { ...opts, headers });
    } else {
      authToken = null; authRefreshToken = null;
      localStorage.removeItem('jwt'); localStorage.removeItem('refresh_token');
      updateAuthBtn();
    }
  }
  return response;
}
window.apiFetch = apiFetch;

// ── chatbot ───────────────────────────────────────────────────────
(() => {
  'use strict';

  const fab     = document.querySelector('#chatFab');
  const panel   = document.querySelector('#chatPanel');
  const input   = document.querySelector('#chatInput');
  const log     = document.querySelector('#chatLog');
  const options = document.querySelector('#chatOptions');
  const form    = document.querySelector('#chatForm');
  const closeBtn = document.querySelector('#closeChat');

  if (!fab || !panel || !input || !log || !options || !form || !closeBtn) return;

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
    if (announce) appendMessage('--- typing Agent ---\n원하는 메뉴를 선택하세요.');
    renderChoices([
      { label: '1. 프로젝트 소개',    action: () => selectMenu('1', '1. 프로젝트 소개') },
      { label: '2. FAQ 대화',         action: () => selectMenu('2', '2. FAQ 대화') },
      { label: '3. 문법 뜻으로 찾기', action: () => selectMenu('3', '3. 문법 뜻으로 찾기') },
    ]);
  }

  async function selectMenu(choice, userLabel) {
    if (busy) return;
    if (userLabel) appendMessage(userLabel, true);
    busy = true;
    try {
      const res  = await apiFetch('/api/menu', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ choice }) });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          appendMessage('로그인이 필요합니다.');
          setAuthMode('login'); showAuth(true);
        } else if (res.status === 403) {
          appendMessage('권한이 없습니다. 관리자에게 문의하세요.');
        } else {
          appendMessage(data.error || '요청을 처리하지 못했습니다.');
        }
        return;
      }
      appendMessage(data.message);
      if (choice === '2') {
        mode = 'ask_name';
        input.placeholder = '이름 또는 별명 입력 (건너뛰기 가능)';
        renderChoices([
          { label: "건너뛰기 ('사용자'로 시작)", action: () => startChat('사용자', true) },
          { label: '‹ 메뉴로 돌아가기',          action: () => showMenu(true) },
        ]);
      } else if (choice === '3') {
        mode = 'search';
        input.placeholder = "문법 질문 입력 (끝내려면 '그만')";
        renderChoices([
          { label: '예: did 다음에 went를 써도 돼?', action: () => sendSearch('did 다음에 went를 써도 돼?') },
          { label: '그만 (메뉴로)',                   action: () => sendSearch('그만') },
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
    renderChoices([{ label: '그만 (메뉴로)', action: () => sendQuestion('그만') }]);
    input.focus();
  }

  async function sendQuestion(question) {
    if (busy) return;
    const trimmed = question.trim();
    if (!trimmed) return;
    appendMessage(trimmed, true);
    busy = true;
    try {
      const res  = await apiFetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: trimmed, name: userName }) });
      const data = await res.json();
      if (!res.ok) { appendMessage(data.error || '답변을 가져오지 못했습니다.'); return; }
      if (data.ended) { appendMessage(data.answer); showMenu(true); }
      else             appendMessage(`typing: ${data.answer}`);
    } catch (err) {
      appendMessage('로컬 서버(server.py)에 연결할 수 없습니다. python3 server.py가 실행 중인지 확인하세요.');
    } finally { busy = false; }
  }

  async function sendSearch(question) {
    if (busy) return;
    const trimmed = question.trim();
    if (!trimmed) return;
    appendMessage(trimmed, true);
    busy = true;
    try {
      const res  = await apiFetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: trimmed }) });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) { appendMessage('로그인이 필요합니다.'); setAuthMode('login'); showAuth(true); }
        else if (res.status === 403) appendMessage('검색 권한이 없습니다. 관리자에게 문의하세요.');
        else appendMessage(data.error || '문법 자료를 검색하지 못했습니다.');
        return;
      }
      if (data.ended) { appendMessage(data.message); showMenu(true); return; }
      const resultText = data.results.map(item => `${item.rank}위 (${item.score.toFixed(3)}) · ${item.text}`).join('\n');
      appendMessage(`[가까운 문법 자료 3개]\n${resultText}\n\n--- AI에게 보낼 질문 ---\n${data.prompt}`);
    } catch (err) {
      appendMessage('로컬 서버(server.py)에 연결할 수 없습니다. python3 server.py가 실행 중인지 확인하세요.');
    } finally { busy = false; }
  }

  function setOpen(open) {
    panel.hidden = !open;
    fab.setAttribute('aria-expanded', String(open));
    (open ? input : fab).focus();
  }

  fab.addEventListener('click', () => setOpen(panel.hidden));
  closeBtn.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) setOpen(false); });

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (busy) return;
    const value = input.value.trim();
    input.value = '';
    if (mode === 'menu') {
      if (['1','2','3','0'].includes(value)) selectMenu(value, value);
      else { if (value) appendMessage(value, true); appendMessage('1, 2, 3, 0 중에서 선택하세요.'); }
      return;
    }
    if (mode === 'ask_name') { if (value) appendMessage(value, true); startChat(value || '사용자', false); return; }
    if (mode === 'chat')     { if (value) sendQuestion(value); return; }
    if (mode === 'search')   { if (value) sendSearch(value); }
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
