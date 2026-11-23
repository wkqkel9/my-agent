const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const nodes = new Map(), actions = [], messages = [], requests = [], replies = [];
function element() {return {value: '', hidden: true, dataset: {}, style: {}, listeners: {},
  addEventListener(k, f) {this.listeners[k] = f;}, setAttribute() {}, focus() {},
  replaceChildren() {}, append(n) {messages.push(n.textContent);}, appendChild() {}};}
function get(key) {if (!nodes.has(key)) nodes.set(key, element()); return nodes.get(key);}
const document = {getElementById: key => get('#' + key), querySelector: get, querySelectorAll: () => [],
  createElement: element, addEventListener() {}, body: {dataset: {}}};
const window = {dispatchEvent() {}, addEventListener() {}, location: {search: ''}, applyTrainingCommand: async action => {
  actions.push(action); return '오답 복습을 시작했어요.';
}};
const context = vm.createContext({document, window, console, Event: function() {}, URLSearchParams,
  localStorage: {getItem: () => null}, fetch: async (url, opts) => {
    assert.equal(url, '/api/training_command');
    requests.push(JSON.parse(opts.body));
    assert(replies.length, 'expected a server reply');
    return {ok: true, json: async () => replies.shift()};
  }});
vm.runInContext(fs.readFileSync('app/js/chatbot.js', 'utf8'), context);
async function send(text, reply) {
  replies.push({handled: true, ...reply});
  get('#chatInput').value = text;
  await get('#chatForm').listeners.submit({preventDefault() {}});
}

(async () => {
  await send('오답으로 연습할 수 있어?', {action: null, message: '가능해요. 실행하려면 요청해 주세요.'});
  assert.equal(actions.length, 0, 'inquiries must never execute');
  await send('오답노트로 연습해 줘', {action: {mode: 'wrong'}});
  assert.equal(actions.length, 1);
  assert.equal(actions[0].mode, 'wrong');
  assert(messages.includes('오답 복습을 시작했어요.'));

  const pending = {missing: ['level'], settings: {topic: '해외여행 ✈️'}};
  await send('여행 주제로 하고 난이도도 바꿔 줘', {action: null, pending, message: '어느 난이도로 바꿀까요?'});
  assert(messages.includes('어느 난이도로 바꿀까요?'));
  assert.equal(actions.length, 1, 'incomplete instructions never apply partial settings');
  await send('지원하는 난이도가 뭐야?', {action: null, message: '난이도 안내'});
  assert.deepEqual(requests.at(-1).pending, pending);
  await send('B2', {action: {topic: '해외여행 ✈️', level: 'B2'}});
  assert.deepEqual(requests.at(-1), {text: 'B2', pending});
  assert.deepEqual(actions.at(-1), {topic: '해외여행 ✈️', level: 'B2'});
  await send('A2', {action: null, message: '명령 안내'});
  assert.deepEqual(requests.at(-1), {text: 'A2'});

  await send('난이도 바꿔 줘', {action: null, pending, message: '어느 난이도로 바꿀까요?'});
  await send('취소', {action: null, pending: null, message: '설정 변경을 취소했어요.'});
  assert.deepEqual(requests.at(-1).pending, pending);
  await send('A2', {action: null, message: '명령 안내'});
  assert.deepEqual(requests.at(-1), {text: 'A2'});
  assert.equal(actions.length, 2);
  console.log('Chatbot form: inquiries, commands, contextual replies and cancellation passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
