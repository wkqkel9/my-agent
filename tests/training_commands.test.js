const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodes = new Map(), storage = new Map(), requests = [], events = {};
function element() {
  return {value: '', textContent: '', hidden: false, dataset: {}, style: {setProperty() {}},
    classList: {toggle() {}}, listeners: {}, addEventListener(k, f) {this.listeners[k] = f;},
    setAttribute() {}, getAttribute() {return '';}, focus() {}, scrollIntoView() {}, replaceChildren() {}, appendChild() {}};
}
const document = {querySelector(key) {if (!nodes.has(key)) nodes.set(key, element()); return nodes.get(key);}, createElement: element};
const localStorage = {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v)};
const window = {addEventListener(k, f) {events[k] = f;}, apiFetch: async () => ({ok: true, json: async () => ({history: [
  {korean: '이미 맞힌 문제', outcome: 'correct', corrected_sentence: 'Correct.'},
  {korean: '이미 맞힌 문제', outcome: 'incorrect', corrected_sentence: 'Correct.'},
  {korean: '나는 갔다.', outcome: 'incorrect', corrected_sentence: 'I went.', cefr_level: 'B2'},
  {korean: '나는 집에 왔다.', outcome: 'partial', corrected_sentence: 'I came home.'},
]})})};
const context = vm.createContext({window, document, localStorage, location: {hash: ''}, console, Date,
  clearInterval() {}, setInterval() {}, fetch: async (url, opts) => {
    requests.push(JSON.parse(opts.body));
    return {ok: true, json: async () => ({korean: `새 문제 ${requests.length}`, reference_answer: 'New question.', cefr_level: 'B1'})};
  }});
vm.runInContext(fs.readFileSync('app/js/writing.js', 'utf8'), context);
(async () => {
  await events.DOMContentLoaded();
  await window.applyTrainingCommand({level: 'B2', topic: '해외여행 ✈️'});
  assert.equal(requests.at(-1).cefr_level, 'B2');
  assert.equal(requests.at(-1).topic, '해외여행 ✈️');
  const previous = nodes.get('#koreanPrompt').textContent;
  assert.match(await window.applyTrainingCommand({next_question: true}), /다른 문제로 바꿨어요/);
  assert.equal(requests.at(-1).previous_question, previous);
  assert.equal(requests.at(-1).cefr_level, 'B2');
  assert.equal(requests.at(-1).topic, '해외여행 ✈️');
  assert.notEqual(nodes.get('#koreanPrompt').textContent, previous);
  const before = nodes.get('#koreanPrompt').textContent;
  assert.match(await window.applyTrainingCommand({mode: 'wrong'}), /오답이 없/);
  assert.equal(nodes.get('#koreanPrompt').textContent, before);
  storage.set('jwt', 'test-token');
  const calls = requests.length;
  assert.match(await window.applyTrainingCommand({mode: 'wrong'}), /오답 2개/);
  assert.equal(nodes.get('#koreanPrompt').textContent, '나는 갔다.');
  assert.match(await window.applyTrainingCommand({next_question: true}), /다음 오답 문제/);
  assert.equal(nodes.get('#koreanPrompt').textContent, '나는 집에 왔다.');
  await nodes.get('#btnNextDrill').listeners.click();
  assert.equal(requests.length, calls, 'review must reuse saved questions without generation');
  assert.match(await window.applyTrainingCommand({level: 'easier'}), /원래 문제/);
  await window.applyTrainingCommand({mode: 'normal'});
  await window.applyTrainingCommand({level: 'easier'});
  assert.equal(requests.at(-1).cefr_level, 'B1+');
  nodes.get('#summaryModal').hidden = true;
  const beforeFinish = requests.length;
  assert.match(await window.applyTrainingCommand({finish_session: true}), /훈련 결과/);
  assert.equal(nodes.get('#summaryModal').hidden, false);
  assert.equal(nodes.get('#sumTotalSolved').textContent, '0개');
  assert.equal(requests.length, beforeFinish);
  console.log('Practice commands: settings, empty notes, account review, latest result, next review, return to normal passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
