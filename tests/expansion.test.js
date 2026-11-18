// Run with: node tests/expansion.test.js (no third-party dependencies).
const fs = require('node:fs');
const html = fs.readFileSync('index.html', 'utf8');
function verify(html) {
 const assert=(condition,message)=>{if(!condition)throw new Error(message);};
 const nodes=new Map();
 function element(){return {children:[],listeners:{},dataset:{},style:{},value:'',textContent:'',hidden:true,scrollTop:0,scrollLeft:0,append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},setAttribute(key,value){this[key]=value;},addEventListener(key,fn){this.listeners[key]=fn;},focus(){}};}
 const document={querySelector(selector){if(!nodes.has(selector))nodes.set(selector,element());return nodes.get(selector);},querySelectorAll(){return [];},createElement:element,createDocumentFragment:element,createTextNode(text){return {textContent:text};},addEventListener(){}};
 const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
 assert(!/<button\b/.test(html.split('id="expansion"')[1].split('id="copywriting"')[0]),'No expansion action buttons');
 assert(html.includes('enterkeyhint="send"'),'Mobile keyboard action available');
 const cases=[
  [0,'I read a book.','correct'],[0,'I read books.','correct'],[0,'I READ A BOOK!','correct'],
  [1,'Before going to bed, I read a book.','correct'],[2,'Every night before bed I read books.','correct'],
  [3,"Even when I'm busy, I read a book every night before bed.",'correct'],
  [1,'I read books before sleeping.','correct'],[1,'I read books prior to going to bed.','correct'],
  [0,'read books.','incomplete'],[0,'I books.','incomplete'],[0,'I read','incomplete'],
  [2,'I raed books.','typo'],[2,'I read bokks before bed.','typo'],
  [0,'I reads a book.','error'],[0,'I read book.','error'],[0,'I read a books.','error'],
  [1,'I read a book before go to bed.','error'],[0,"I don't read books.",'error'],
  [0,'I buy a book.','error'],[0,'I read books last night.','error'],
  [0,'I raed a book.','typo'],[0,'I reed books.','typo'],[0,'I read bokks.','typo'],
  [2,'I read a book before bed.','incomplete'],[3,'I read a book every night.','incomplete'],
  [1,'I read a book before','incomplete'],[0,'','input'],[0,'나는 책을 읽는다','input'],
  [0,'I enjoy reading books.','review'],[0,'I read books before bed.','review'],
  [1,'I before bed read books.','review'],[0,'<img src=x onerror=alert(1)>','review']
 ];
 const checks=`
 for(const [stage,text,kind] of cases){round=stage;assert(assessAnswer(text).kind===kind,text+' expected '+kind+' got '+assessAnswer(text).kind);}
 startPractice();const originalDeadline=deadline;
 expandInput.value='  I raed a book.';showFeedback(assessAnswer(expandInput.value));
 assert(feedback.dataset.kind==='typo','Typo UI');
 assert(expandHighlight.children[0].children[1].textContent==='raed','Highlight offsets include leading spaces');
 assert(deadline===originalDeadline&&running,'Errors do not reset or pause countdown');
 expandInput.listeners.input();assert(feedback.hidden&&expandSurface.dataset.reviewed==='false','Editing clears old feedback');
 expandInput.value='I read a book.';submitExpansionAnswer();assert(round===1&&running&&expandInput.value==='','Singular accepted and advances');
 expandInput.value='I read a book.';submitExpansionAnswer();assert(feedback.dataset.kind==='incomplete','Missing meaning feedback');
 assert(document.querySelector('#koreanPrompt').children[1].textContent==='잠들기 전에','Missing meaning marked in prompt');
 submitExpansionAnswer();assert(document.querySelector('#feedbackReason').textContent.includes('before bed'),'Repeat submission gives concrete phrase');
 expandInput.value='Before bed, I read a book.';submitExpansionAnswer();assert(round===2,'Alternative order accepted');
 expandInput.value='I read a book every night before bed.';submitExpansionAnswer();assert(round===3,'Night clause accepted');
 expandInput.value='Even on busy days I read a book every night before bed.';submitExpansionAnswer();assert(practiceState==='complete'&&!running&&solved===4,'Completion');
 assert(expandStatus.textContent.includes('4 / 4'),'Correct completion count');
 expandInput.listeners.keydown({key:'Enter',isComposing:true,preventDefault(){throw Error('IME intercepted');}});assert(practiceState==='complete','IME Enter ignored');
 submitExpansionAnswer();assert(round===0&&running,'Enter restarts completed practice');
 expandInput.value='My unfinished answer';deadline=Date.now()-1;submitExpansionAnswer();assert(practiceState==='timeout'&&expandInput.value==='My unfinished answer','Timeout preserves answer');
 submitExpansionAnswer();assert(round===1&&running,'Enter advances after timeout');
 expandInput.value='I read a book before bed.';expandInput.listeners.beforeinput({inputType:'insertLineBreak',isComposing:false,preventDefault(){}});assert(round===2,'Mobile beforeinput submits');
 finish();expandInput.listeners.click();assert(round===3&&running,'Tap continues timeout');
 expandInput.value='I read a book before bed every night even when I am busy.';submitExpansionAnswer();
 assert(expandStatus.textContent.includes('2 / 4'),'Timeouts are not counted as correct');
 expandInput.listeners.click();assert(round===0&&running&&solved===0,'Tap restarts completion');
 round=3;const missing=assessAnswer('I read a book every night.');assert(missing.meaning==='잠들기 전에','Selective missing clause');
 return cases.length;
 `;
 const count=new Function('document','setInterval','clearInterval','assert','cases',source+'\n'+checks)(document,()=>1,()=>{},assert,cases);
 return `${count} classification cases and button-free lifecycle, editing, timing, IME, mobile submit tests passed.`;
}
console.log(verify(html));
