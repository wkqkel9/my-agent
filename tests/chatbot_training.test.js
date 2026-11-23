const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const nodes = new Map(), actions = [], messages = [];
function element() {return {value: '', hidden: true, dataset: {}, style: {}, listeners: {},
  addEventListener(k, f) {this.listeners[k] = f;}, setAttribute() {}, focus() {},
  replaceChildren() {}, append(n) {messages.push(n.textContent);}, appendChild() {}};}
function get(key) {if (!nodes.has(key)) nodes.set(key, element()); return nodes.get(key);}
const document = {getElementById: key => get('#' + key), querySelector: get, querySelectorAll: () => [],
  createElement: element, addEventListener() {}, body: {dataset: {}}};
const window = {dispatchEvent() {}, location: {search: ''}, applyTrainingCommand: async action => {
  actions.push(action); return '오답 복습을 시작했어요.';
}};
const context = vm.createContext({document, window, console, Event: function() {}, URLSearchParams,
  localStorage: {getItem: () => null}, fetch: async (url, opts) => {
    assert.equal(url, '/api/training_command');
    const inquiry = JSON.parse(opts.body).text.includes('?');
    return {ok: true, json: async () => ({handled: true, action: inquiry ? null : {mode: 'wrong'}, message: '가능해요. 실행하려면 요청해 주세요.'})};
  }});
vm.runInContext(fs.readFileSync('app/js/chatbot.js', 'utf8'), context);
(async () => {
  get('#chatInput').value = '오답으로 연습할 수 있어?';
  await get('#chatForm').listeners.submit({preventDefault() {}});
  assert.equal(actions.length, 0, 'inquiries must never execute');
  get('#chatInput').value = '오답노트로 연습해 줘';
  await get('#chatForm').listeners.submit({preventDefault() {}});
  assert.equal(actions.length, 1);
  assert.equal(actions[0].mode, 'wrong');
  assert(messages.includes('오답 복습을 시작했어요.'));
  console.log('Chatbot form: inquiry preserves state, command applies practice action and displays result passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
