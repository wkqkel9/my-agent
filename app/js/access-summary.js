(() => {
  const status = document.querySelector('#summaryStatus');
  const gate = document.querySelector('#summaryGate');
  const content = document.querySelector('#summaryContent');
  const login = document.querySelector('#summaryLogin');
  const refresh = document.querySelector('#summaryRefresh');
  const counts = document.querySelector('#summaryCounts');
  const runs = document.querySelector('#summaryRuns');

  function renderTable(records) {
    if (!records.length) { runs.textContent = '아직 접근 기록이 없습니다.'; return; }
    const table = document.createElement('table');
    table.innerHTML = '<thead><tr><th>시각</th><th>기능</th><th>결과</th></tr></thead>';
    const body = document.createElement('tbody');
    records.forEach(record => {
      const row = document.createElement('tr');
      [record.timestamp, record.feature === 'writing' ? '영작' : '필사', record.outcome === 'ok' ? '허용' : '차단'].forEach(value => {
        const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
      });
      body.append(row);
    });
    table.append(body); runs.replaceChildren(table);
  }

  async function load() {
    let token = localStorage.getItem('jwt');
    content.hidden = true;
    if (!token) {
      status.textContent = '로그인하면 내 계정의 접근 기록을 볼 수 있습니다.';
      login.hidden = false; refresh.hidden = true;
      return;
    }
    login.hidden = true; refresh.hidden = false; status.textContent = '불러오는 중…';
    const headers = {Authorization: `Bearer ${token}`};
    try {
      let [summaryResponse, runsResponse] = await Promise.all([
        fetch('/api/access-summary', {headers}), fetch('/api/access-runs?limit=100', {headers}),
      ]);
      if ((summaryResponse.status === 401 || runsResponse.status === 401) && localStorage.getItem('refresh_token')) {
        const refreshResponse = await fetch('/api/refresh', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({refresh_token:localStorage.getItem('refresh_token')}),
        });
        if (refreshResponse.ok) {
          const session = await refreshResponse.json();
          token = session.token;
          localStorage.setItem('jwt', session.token);
          localStorage.setItem('refresh_token', session.refresh_token);
          headers.Authorization = `Bearer ${token}`;
          [summaryResponse, runsResponse] = await Promise.all([
            fetch('/api/access-summary', {headers}), fetch('/api/access-runs?limit=100', {headers}),
          ]);
        }
      }
      const summaryData = await summaryResponse.json(); const runsData = await runsResponse.json();
      if (summaryResponse.status === 401 || runsResponse.status === 401) {
        status.textContent = '로그인이 만료됐습니다. 다시 로그인해 주세요.'; login.hidden = false; return;
      }
      if (!summaryResponse.ok || !runsResponse.ok) throw new Error(summaryData.error || runsData.error || '기록을 불러오지 못했습니다.');
      const summary = summaryData.summary;
      counts.innerHTML = `<table><thead><tr><th>연습</th><th>허용</th><th>차단</th><th>합계</th></tr></thead><tbody><tr><th>영작</th><td>${summary.writing.allowed}</td><td>${summary.writing.denied}</td><td>${summary.writing.allowed + summary.writing.denied}</td></tr><tr><th>필사</th><td>${summary.copywriting.allowed}</td><td>${summary.copywriting.denied}</td><td>${summary.copywriting.allowed + summary.copywriting.denied}</td></tr></tbody></table>`;
      renderTable(runsData.runs); content.hidden = false; gate.hidden = true;
    } catch (error) { status.textContent = error.message; gate.hidden = false; }
  }

  window.refreshAccessSummary = load;
  login.addEventListener('click', () => { document.querySelector('#authBtn')?.click(); });
  refresh.addEventListener('click', load);
  window.addEventListener('authchange', load);
  window.addEventListener('focus', load);
  load();
})();
