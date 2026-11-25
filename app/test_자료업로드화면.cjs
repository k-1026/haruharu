const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'담당자화면/plan.js'),'utf8').split('// ---------- 시작 ----------')[0];
function setup(errorStatus=0){
  const els=new Map(),calls=[];
  const chosen={계절:['가을'],언어권:['일본어'],지역:['중구'],체류기간:['1박2일']};
  const el=()=>({innerHTML:'',hidden:false,value:'0',disabled:false,querySelectorAll:()=>[],setAttribute(){}});
  const form=el();form.목표={value:'일본인 커플'};form.희망={value:'이동을 줄여 주세요'};
  form.querySelectorAll=selector=>{const name=selector.match(/data-name="([^"]+)"/);return name?(chosen[name[1]]||[]).map(v=>({dataset:{v}})):[];};
  els.set('order',form);
  const document={body:{setAttribute(){}},getElementById(id){if(!els.has(id))els.set(id,el());return els.get(id);}};
  const data={업로드id:'a'.repeat(32),파일명:'가상.csv',안내:'실제 조사 아님',시트:[{이름:'CSV',행수:1,경고:[],행:[{항목:'음식',세부항목:'불고기',값:45,단위:'%',출처:'가상 자료',대상:'일본인 커플',기간:'가을',지역:'중구'}]}]};
  const ctx={document,console,Uint8Array,btoa:t=>Buffer.from(t,'binary').toString('base64'),calls,data,errorStatus};vm.createContext(ctx);
  vm.runInContext(source+`\npost=async(url,body)=>{calls.push({url,body});if(errorStatus&&url.endsWith('/upload'))throw Object.assign(new Error('없는 요청입니다.'),{status:errorStatus});return url.endsWith('/upload')?data:{기획id:'demo'};};showProgress=()=>{};watch=()=>{};newForm();\n}`,ctx);
  return {els,calls,form};
}
test('CSV 미리보기 확인 전에는 시작을 막고 적용 후 업로드 ID를 전달한다',async()=>{
  const {els,calls,form}=setup();
  els.get('dataFile').files=[{name:'가상.csv',size:3,arrayBuffer:async()=>new Uint8Array([1,2,3]).buffer}];
  await els.get('dataFile').onchange();
  assert.equal(els.get('newGo').disabled,true);
  assert.match(els.get('uploadRows').innerHTML,/불고기/);
  assert.match(els.get('uploadRows').innerHTML,/실제 조사 아님/);
  els.get('uploadApply').onclick();assert.equal(els.get('newGo').disabled,false);
  await form.onsubmit({preventDefault(){}});
  const start=calls.find(c=>c.url==='/api/plan/start');
  assert.equal(start.body.기관업로드.확인,true);assert.equal(start.body.기관업로드.시트,'CSV');
  assert.equal(start.body.목표,'일본인 커플');assert.deepEqual([...start.body.지역],['중구']);
});
test('자료 빼기는 적용 ID를 제거하고 기존 자료만으로 시작한다',async()=>{
  const {els,calls,form}=setup();
  els.get('dataFile').files=[{name:'가상.csv',size:1,arrayBuffer:async()=>new Uint8Array([1]).buffer}];
  await els.get('dataFile').onchange();els.get('uploadApply').onclick();els.get('uploadRemove').onclick();
  await form.onsubmit({preventDefault(){}});
  assert.equal(calls.at(-1).body.기관업로드,undefined);
});
test('이전 서버의 404면 시작 버튼 옆에 원인과 조치를 표시한다',async()=>{
  const {els}=setup(404);
  els.get('dataFile').files=[{name:'가상.csv',size:1,arrayBuffer:async()=>new Uint8Array([1]).buffer}];
  await els.get('dataFile').onchange();
  assert.equal(els.get('newGo').disabled,true);
  assert.match(els.get('need').textContent,/서버.*재시작/);
  assert.match(els.get('uploadState').textContent,/업로드 실패/);
  els.get('uploadRemove').onclick();assert.equal(els.get('newGo').disabled,false);
});
