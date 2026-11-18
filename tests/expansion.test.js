const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8'),nodes=new Map(),requests=[];
function element(){return {children:[],listeners:{},dataset:{},style:{},value:'',textContent:'',hidden:true,scrollTop:0,scrollLeft:0,append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},setAttribute(){},addEventListener(k,f){this.listeners[k]=f},focus(){}}}
const document={querySelector(k){if(!nodes.has(k))nodes.set(k,element());return nodes.get(k)},querySelectorAll(){return []},createElement:element,createDocumentFragment:element,createTextNode(t){return {textContent:t}},addEventListener(){}};
const context=vm.createContext({document,console,AbortController,Date,setTimeout,clearTimeout,setInterval(){return 1},clearInterval(){},fetch(url,options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const run=s=>vm.runInContext(s,context),flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 run('startPractice();expandInput.value="I read a book";submitExpansionAnswer()');assert.equal(run('round'),1);assert.equal(requests.length,0);
 for(const text of ['I gonna read a book','I raed books','read books','', '나는 책을 읽는다']){
  run(`expandInput.value=${JSON.stringify(text)};submitExpansionAnswer()`);await flush();
  assert.equal(run('feedback.hidden'),true);assert.equal(JSON.parse(requests.at(-1).options.body).text,text);
 }
 const beforeDuplicate=requests.length;run('submitExpansionAnswer()');await flush();assert.equal(requests.length,beforeDuplicate);
 const latest=requests.at(-1);latest.resolve({ok:true,json:async()=>({kind:'error',label:'틀린 표현',hint:'현재 시제로 바꿔보세요.',target:null,range:null,meaning:'읽는다'})});await flush();await flush();assert.equal(run('feedback.dataset.kind'),'error');
 const beforeCache=requests.length;run('submitExpansionAnswer()');await flush();assert.equal(requests.length,beforeCache);assert.equal(run('feedback.dataset.kind'),'error');
 requests[0].resolve({ok:true,json:async()=>({kind:'correct',label:'정답',hint:'정답입니다.'})});await flush();assert.equal(run('round'),1);
 run('expandInput.value="another answer";submitExpansionAnswer()');await flush();run('expandInput.value="edited answer";expandInput.listeners.input()');requests.at(-1).resolve({ok:true,json:async()=>({kind:'correct',label:'정답',hint:'정답입니다.'})});await flush();assert.equal(run('round'),1);assert.equal(run('feedback.hidden'),true);
 run('submitExpansionAnswer()');await flush();requests.at(-1).reject(new Error('offline'));await flush();await flush();assert.equal(run('feedback.dataset.kind'),'unavailable');assert(run('document.querySelector("#feedbackReason").textContent').includes('다시 시도'));
 run('submitExpansionAnswer()');await flush();requests.at(-1).resolve({ok:true,json:async()=>({kind:'correct',label:'정답',hint:'정답입니다.'})});await flush();await flush();assert.equal(run('round'),2);
 run('expandInput.value="stale first";submitExpansionAnswer()');await flush();const stale=requests.at(-1);
 run('expandInput.value="fresh second";submitExpansionAnswer()');await flush();const activeCount=requests.length;
 stale.resolve({ok:true,json:async()=>({kind:'correct',label:'정답',hint:'정답입니다.'})});await flush();await flush();run('submitExpansionAnswer()');await flush();assert.equal(requests.length,activeCount);
 requests.at(-1).resolve({ok:true,json:async()=>({kind:'error',label:'틀린 표현',hint:'현재 시제로 바꾸세요.'})});await flush();await flush();
 assert(!html.includes('function assessAnswer('));assert(!html.includes('function phraseFindings('));
 console.log('AI-only assessment, accepted answers, empty input, stale response, editing, failure and AI-correct advancement passed');
})().catch(e=>{console.error(e);process.exitCode=1});
