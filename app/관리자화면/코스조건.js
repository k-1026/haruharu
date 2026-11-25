'use strict';
const courseState = {recordId:'',duration:'',job:null,baseJobId:'',selectedJobId:'',history:[],busy:false,poll:null,generation:0,token:'',meals:[]};
const courseLabels = {준비:'조건 저장 완료',실행중:'3단계 AI 실행 중',초안생성:'코스 초안 생성 완료',담당자확인대기:'코스 초안 · 담당자 확인 대기',시간충돌확인필요:'코스 초안 · 시간 충돌 확인 필요',검사확인필요:'초안 생성 · 앱 검사 확인 필요',실행실패:'AI 실행 실패',중단됨:'시험 중단됨','4단계준비완료':'4단계 준비 완료 · AI 미실행'};
function courseInput(name,label,type='text',options=null) {
  const wrap=el('label',undefined,'coursefield');wrap.append(el('span',label));
  const input=el(options?'select':'input');input.name=name;input.id='course-'+name;
  input.setAttribute('form',/^(rp|ro)-/.test(name)?'reviewForm':'courseForm');
  input.setAttribute('aria-label',label);
  if(options) {for(const [value,text,placeholder] of options){const o=el('option',text);o.value=value;if(placeholder){o.disabled=true;o.selected=true;}input.append(o);}}
  else {input.type=type;input.maxLength=200;if(type==='text')input.placeholder='미정이면 비워 두세요';}
  wrap.append(input);
  if(type==='text' && !options && /지점$|식당$|장소권역$/.test(name) && typeof attachPlacePicker==='function')attachPlacePicker(wrap,input);
  return wrap;
}
function buildCourseForm(duration) {
  const box=$('courseInputs');box.replaceChildren();
  const anchors=el('div',undefined,'courseanchors');box.append(anchors);
  for(const prefix of ['시작','종료']) {
    const group=el('fieldset',undefined,'anchorcard');group.append(el('legend','전체 여행 '+prefix));
    group.append(courseInput(prefix+'일차',prefix+' 일차','',[['','일차를 선택하세요',true],['1','1일차'],...(duration==='1박2일'?[['2','2일차']]:[]),['미정','미정으로 저장 (초안)']]));
    group.append(courseInput(prefix+'지점',prefix+' 장소'));
    group.append(courseInput(prefix+'시각',prefix+' 시각','time'));anchors.append(group);
  }
  const settings=el('div',undefined,'coursegrid');
  settings.append(el('p','저장된 식사·운영 조건입니다. 이 설정의 변경은 새 AI 시험용이며 기존 초안 수정에는 적용하지 않습니다.','footnote'));
  settings.append(courseInput('운영방식','운영 방식','', [['','미정'],['단체동행형','단체 동행형'],['개별이동형','개별 이동형']]));
  settings.append(courseInput('치킨선택','치킨 저녁 옵션','', [['','미정'],['선택','선택'],['안함','선택 안 함']]));
  if(duration==='1박2일')settings.append(courseInput('2일차오전구성','2일차 오전 구성','', [['','미정'],['후보일정추가','일정 후보 추가'],['자유시간','자유시간'],['종료장소로바로','추가 관광 없이 종료 장소로 이동']]));
  const adminOptions=$('adminCourseOptions');if(adminOptions?.append){adminOptions.replaceChildren();adminOptions.append(settings);}else box.append(settings);
  if(duration==='1박2일')box.append(courseInput('2일차점심포함','2일차 점심을 코스에 넣을까요?','', [['','미정'],['포함','포함'],['미포함','미포함']]));
  courseState.meals=[[1,'점심'],[1,'저녁'],...(duration==='1박2일'?[[2,'점심']]:[])];
  const meals=$('mealInputs');meals.replaceChildren();
  const adminMeals=$('adminMealOptions');if(adminMeals?.append){adminMeals.replaceChildren();adminMeals.append(meals);meals.classList.remove('hidden');}
  courseState.meals.forEach(([day,slot],i)=>{
    const row=el('div',undefined,'mealrow');row.append(el('h4',`${day}일차 ${slot}`));
    row.append(courseInput(`meal-${i}-방식`,'식사 방식','',[['','미정'],['지정식','지정식'],['자유식','자유식']]));
    row.append(courseInput(`meal-${i}-식당`,'지정 식당'));
    row.append(courseInput(`meal-${i}-식비포함`,'식비 포함 여부','',[['','미정'],['포함','포함'],['불포함','불포함']]));meals.append(row);
    const select=$('course-meal-'+i+'-방식'),restaurant=$('course-meal-'+i+'-식당');
    function update(){restaurant.disabled=select.value!=='지정식';if(restaurant.disabled)restaurant.value='';}
    select.addEventListener('change',update);update();
  });
}
function courseSummaryText(value) {
  const day=v=>[1,2].includes(Number(v))?Number(v)+'일차':'일차 미정';
  const part=p=>`${day(value[p+'일차'])} · ${value[p+'지점'] && value[p+'지점']!=='미확인'?value[p+'지점']:'장소 미정'} · ${value[p+'시각'] && value[p+'시각']!=='미확인'?value[p+'시각']:'시각 미정'}`;
  return '전체 여행 시작: '+part('시작')+' / 전체 여행 종료: '+part('종료');
}
function showCourseSelection(){document.getElementById('courseCurrent').textContent='지금 선택한 값 — '+courseSummaryText(readCourseForm());}
function showSavedCourse(value){document.getElementById('courseSaved').textContent='저장된 값 — '+courseSummaryText(value);}
function courseFeedback(text){document.getElementById('courseMessage').textContent=text;document.getElementById('courseActionMessage').textContent=text;}
async function verifyCourseSaved(job,requested) {
  const data=await api('/api/file?path='+encodeURIComponent(job.시험id+'/코스작성조건_선택.json'));
  const saved=JSON.parse(data.본문);
  for(const name of ['시작일차','종료일차']) {
    if((saved[name] || '미정')!==requested[name])throw new Error(name+'의 저장값이 선택값과 다릅니다. 새로고침 후 저장된 시험을 확인하세요.');
  }
  return saved;
}
function courseValue(name) {return $('courseForm').elements.namedItem(name)?.value || '';}
function requireCourseDays(){for(const name of ['시작일차','종료일차'])if(!courseValue(name))throw new Error(name+'를 선택하세요. 모르면 ‘미정으로 저장’을 명시적으로 선택하세요.');}
function readCourseForm() {
  const value={};for(const name of ['시작지점','시작시각','종료지점','종료시각','운영방식','치킨선택'])value[name]=courseValue(name);
  for(const name of ['시작일차','종료일차'])value[name]=Number(courseValue(name)) || '미정';
  value['2일차오전구성']=courseState.duration==='1박2일'?courseValue('2일차오전구성'):'해당없음';
  value['2일차점심포함']=courseState.duration==='1박2일'?(courseValue('2일차점심포함') || '미정'):'해당없음';
  value.식사목록=courseState.meals.map(([day,slot],i)=>({일차:day,시간칸:slot,방식:courseValue(`meal-${i}-방식`),식당:courseValue(`meal-${i}-식당`),식비포함:courseValue(`meal-${i}-식비포함`)}));return value;
}
function fillCourseForm(value) {
  const set=(name,v)=>{const input=$('courseForm').elements.namedItem(name);if(input){input.value=['미확인','미선택','미정'].includes(v)?'':v || '';input.placeRefresh?.();}};
  for(const name of ['시작일차','시작지점','시작시각','종료일차','종료지점','종료시각','운영방식','치킨선택','2일차오전구성','2일차점심포함'])set(name,value[name]);
  courseState.meals.forEach(([day,slot],i)=>{const row=(value.식사목록 || []).find(r=>r.일차===day && r.시간칸===slot) || {};
    for(const field of ['방식','식당','식비포함'])set(`meal-${i}-${field}`,row[field]);
    $('course-meal-'+i+'-식당').disabled=row.방식!=='지정식';
  });
}
function courseButtons() {
  const running=courseState.job?.상태==='실행중';
  $('courseFields').disabled=courseState.busy || running;
  $('courseSave').disabled=courseState.busy || running;
  $('courseStart').disabled=courseState.busy || courseState.job?.상태!=='준비';
  $('courseApply').disabled=courseState.busy || running || !courseState.baseJobId;
  const fields=$('courseForm').elements;
  if(fields?.[Symbol.iterator])for(const field of fields){
    if(field.tagName==='INPUT' || field.tagName==='SELECT')field.disabled=courseState.busy || running || (/^meal-\d+-식당$/.test(field.name) && courseValue(field.name.replace('식당','방식'))!=='지정식');
  }
}
function savedTimeLabel(value){if(!value)return '저장 시각 기록 없음';const d=new Date(value);return Number.isNaN(d.getTime())?'저장 시각 확인 필요':d.toLocaleString('ko-KR',{timeZone:'Asia/Seoul',hour12:false});}
function revisionLabel(job,index=courseState.history.findIndex(r=>r.시험id===job.시험id)){
  return `${index===0?'최신':'이전'} · 저장본 ${index<0?'확인 중':courseState.history.length-index} · ${savedTimeLabel(job.기록시각)} · ${courseLabels[job.상태] || job.상태}`;
}
function showRevisionMeta(){
  const job=courseState.history.find(r=>r.시험id===courseState.selectedJobId);
  const text=job?revisionLabel(job)+'\n기록 번호: '+job.시험id.split('/').pop():'저장된 수정본을 선택하세요.';
  document.getElementById('courseRevision').textContent=text;
  document.getElementById('plannerRevision').textContent=job?revisionLabel(job):'코스가 있는 저장본을 선택해 주세요.';
  document.getElementById('revisionMeta').textContent=text;
  document.getElementById('revisionMeta').hidden=state.stage<3;
}
function drawCourseStatus(job) {
  const box=$('courseStatus');box.replaceChildren();if(!job)return;
  const card=el('div',undefined,'checkcard');card.append(el('h3',courseLabels[job.상태] || job.상태),el('p',job.안내 || ''));
  if(job.시험id)card.append(el('p',job.시험id.split('/').pop(),'footnote'));
  if(job.문제?.length){const ul=el('ul'),counts=new Map();for(const p of job.문제)counts.set(String(p),(counts.get(String(p))||0)+1);for(const [p,n] of counts)ul.append(el('li',p+(n>1?` (${n}건)`:'')));card.append(ul);}
  if(job.담당자확인대기?.length){card.append(el('h4','담당자 확인 대기'));const ul=el('ul');job.담당자확인대기.forEach(p=>ul.append(el('li',String(p))));card.append(ul);}
  if(job.시간표검사)card.append(timeCheckView(job.시간표검사));
  if(job['4단계준비검사'] && typeof readinessView==='function')card.append(readinessView(job['4단계준비검사']));
  if(['초안생성','검사확인필요','담당자확인대기','시간충돌확인필요','4단계준비완료'].includes(job.상태)){
    const button=el('button','3단계 결과 보기','secondarybutton');button.type='button';
    button.addEventListener('click',async()=>{await loadRecord(courseState.recordId,job.시험id);state.stage=3;state.view='result';state.file=job.시험id+'/3단계_결과.md';renderStages();await renderPanel();$('panel').scrollIntoView({behavior:'smooth',block:'start'});});card.append(button);
  }
  box.append(card);
}
async function loadCourse(record,preferredJob=null) {
  const previous=courseState.recordId===record.id?courseState.selectedJobId:'';
  const gen=++courseState.generation;clearTimeout(courseState.poll);
  courseState.recordId=record.id;courseState.job=null;courseState.baseJobId='';courseState.selectedJobId='';courseState.history=[];courseState.busy=false;
  if(typeof reviewReset==='function')reviewReset();
  $('courseCurrent').textContent='';$('courseSaved').textContent='아직 저장된 조건을 읽지 않았습니다.';
  $('courseActionMessage').textContent='';
  $('courseForm').classList.add('hidden');$('courseStatus').replaceChildren();$('courseHistory').replaceChildren();
  $('courseMessage').textContent='3단계 입력 가능 여부를 확인하고 있습니다…';
  try {
    const [info]=await Promise.all([api('/api/course?id='+encodeURIComponent(record.id)),typeof loadPlaces==='function'?loadPlaces():Promise.resolve()]);if(gen!==courseState.generation)return;
    courseState.duration=info.확정체류기간;courseState.history=info.시험목록;buildCourseForm(info.확정체류기간);
    showCourseSelection();
    $('courseForm').classList.remove('hidden');$('courseMessage').textContent='2→3 전달 검사 통과 · 조건을 저장한 뒤 시험을 시작하세요.';
    if(info.시험목록.length) {
      const label=el('label','저장된 3단계 시험 ','historylabel'),select=el('select');select.setAttribute('aria-label','저장된 3단계 시험 선택');
      info.시험목록.forEach((job,index)=>{const option=el('option',revisionLabel(job,index));option.value=job.시험id;select.append(option);});
      label.append(select);$('courseHistory').append(label);
      const choose=async id=>{const selection=++courseState.generation;clearTimeout(courseState.poll);courseState.busy=true;courseButtons();try{
        const [job,data]=await Promise.all([api('/api/course/status?id='+encodeURIComponent(id)),api('/api/file?path='+encodeURIComponent(id+'/코스작성조건_선택.json'))]);
        if(selection!==courseState.generation)return;const saved=JSON.parse(data.본문);courseState.job=job;courseState.selectedJobId=id;courseState.baseJobId=job.수정가능?job.시험id:'';fillCourseForm(saved);showSavedCourse(saved);showCourseSelection();showRevisionMeta();if(typeof loadReview==='function')loadReview(id);state.file='';state.cache.clear();renderStages();if(state.stage>=3)await renderPanel();drawCourseStatus(job);if(job.상태==='실행중')pollCourse(id,selection);
      }catch(e){if(selection===courseState.generation){$('courseMessage').textContent=e.message;select.value=courseState.selectedJobId;}}finally{if(selection===courseState.generation){courseState.busy=false;courseButtons();}}};
      select.addEventListener('change',()=>choose(select.value));select.value=info.시험목록.some(j=>j.시험id===(preferredJob || previous))?(preferredJob || previous):info.시험목록[0].시험id;await choose(select.value);
    }
    courseButtons();
  } catch(e){if(gen===courseState.generation)$('courseMessage').textContent=e.message;}
}
async function coursePost(path,value) {
  if(!courseState.token)courseState.token=(await api('/api/session')).token;
  const send=()=>api(path,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':courseState.token},body:JSON.stringify(value)});
  try{return await send();}catch(e){
    if(e.status!==403 || !e.message.includes('새로고침'))throw e;
    // 서버 재시작으로 토큰만 만료된 경우, 거부된 쓰기 요청을 새 토큰으로 한 번만 재시도한다.
    courseState.token=(await api('/api/session')).token;return send();
  }
}
async function saveCourse(event) {
  event.preventDefault();if(courseState.busy || courseState.job?.상태==='실행중')return;
  try{requireCourseDays();}catch(e){courseFeedback(e.message);return;}
  const gen=courseState.generation,id=courseState.recordId,value=readCourseForm();
  courseState.busy=true;courseButtons();courseFeedback('조건을 저장하고 있습니다…');
  try {const job=await coursePost('/api/course/save',{id,조건:value});if(gen!==courseState.generation)return;
    const saved=await verifyCourseSaved(job,value);if(gen!==courseState.generation)return;
    showSavedCourse(saved);courseState.job=job;courseState.baseJobId='';drawCourseStatus(job);$('courseMessage').textContent='조건 저장·재조회 확인 완료. 새 코스를 만들 때만 AI 시험 시작을 누르세요. 기존 초안 수정은 저장된 시험에서 기존 초안을 다시 선택하세요.';
  }catch(e){if(gen===courseState.generation)courseFeedback(e.message);}
  finally{if(gen===courseState.generation){courseState.busy=false;courseButtons();}}
}
async function applyCourse() {
  if(courseState.busy || courseState.job?.상태==='실행중')return;
  if(!courseState.baseJobId){courseFeedback('수정할 기존 코스 초안을 먼저 선택하세요.');return;}
  try{requireCourseDays();}catch(e){courseFeedback(e.message);return;}
  const gen=courseState.generation,base=courseState.baseJobId,record=courseState.recordId,value=readCourseForm();
  courseState.busy=true;courseButtons();courseFeedback('AI 호출 없이 기존 초안에 수정 사항을 반영하고 있습니다…');
  try {
    const job=await coursePost('/api/course/apply',{시험id:base,조건:value});if(gen!==courseState.generation)return;
    const saved=await verifyCourseSaved(job,value);if(gen!==courseState.generation)return;showSavedCourse(saved);
    courseState.job=job;courseState.baseJobId=job.시험id;drawCourseStatus(job);
    await loadRecord(record,job.시험id);state.stage=3;state.view='result';state.file=job.시험id+'/3단계_결과.md';renderStages();await renderPanel();
    courseFeedback('AI 재실행 없이 새 수정본을 저장했습니다. 시작 시각에 맞춘 시간표와 다시 확인할 항목을 확인하세요.');
  }catch(e){if(gen===courseState.generation)courseFeedback(e.message);}
  finally{if(gen===courseState.generation){courseState.busy=false;courseButtons();}}
}
async function startCourse() {
  if(courseState.busy || courseState.job?.상태!=='준비')return;
  const gen=courseState.generation,id=courseState.job.시험id;courseState.busy=true;courseButtons();
  try{const job=await coursePost('/api/course/start',{시험id:id});if(gen!==courseState.generation)return;
    courseState.job=job;drawCourseStatus(job);if(job.상태==='실행중')pollCourse(id,gen);
  }catch(e){if(gen===courseState.generation)$('courseMessage').textContent=e.message;}
  finally{if(gen===courseState.generation){courseState.busy=false;courseButtons();}}
}
function pollCourse(id,gen) {
  clearTimeout(courseState.poll);courseState.poll=setTimeout(async()=>{
    if(gen!==courseState.generation)return;
    try{const job=await api('/api/course/status?id='+encodeURIComponent(id));if(gen!==courseState.generation)return;
      courseState.job=job;courseState.history=courseState.history.map(r=>r.시험id===job.시험id?job:r);showRevisionMeta();if(job.수정가능)courseState.baseJobId=job.시험id;drawCourseStatus(job);courseButtons();if(job.상태==='실행중')pollCourse(id,gen);
      else {$('courseMessage').textContent='3단계 시험이 끝났습니다. 아래 결과 보기에서 확인하세요.';}
    }catch(e){if(gen===courseState.generation){$('courseMessage').textContent='진행 상태를 읽지 못했습니다. 서버가 켜져 있는지 확인하고 목록을 새로고침하세요. '+e.message;}}
  },2000);
}
function readCourseJSON(text) {
  let source=text.trim();
  if(/^\s*```/m.test(source)) {
    const blocks=[...source.matchAll(/^\s*```(?:json)?[^\S\n]*\r?\n([\s\S]*?)^\s*```[^\S\n]*$/gm)];
    if(blocks.length!==1 || [...source.matchAll(/^\s*```/gm)].length!==2)throw new Error('JSON 코드 블록이 여러 개이거나 불완전합니다.');
    source=blocks[0][1].trim();
  }
  const value=JSON.parse(source);if(!value || Array.isArray(value) || typeof value!=='object')throw new Error('JSON 객체가 필요합니다.');return value;
}
function timeCheckView(value) {
  const box=el('section',undefined,'checkcard');box.append(el('h3','시간표 충돌 검사'));
  for(const [title,key] of [['확인된 충돌','충돌'],['검사 대기','확인대기'],['일차 선택 전 참고 · 확정 판정 아님','일차미정참고']]) {
    const items=value[key] || [];if(!items.length)continue;box.append(el('h4',title));const ul=el('ul');for(const item of items)ul.append(el('li',String(item)));box.append(ul);
  }
  if(!(value.충돌 || []).length)box.append(el('p','선택된 범위에서 확인된 시간 충돌 없음. 미정 항목과 이동·운영 조건은 별도 확인이 필요합니다.'));
  return box;
}
function renderCourseResult(panel,text) {
  let value;try{value=readCourseJSON(text);}catch{panel.append(el('p','코스 구조를 읽지 못했습니다. 저장된 원문을 표시합니다.','help'),markdown(text));return;}
  if(!value || typeof value!=='object' || !Array.isArray(value.칸목록)){panel.append(el('p','시간표 구조를 확인해야 합니다. 원문 · JSON에서 결과를 확인하세요.','help'),el('pre',text));return;}
  panel.append(el('h2','3단계 코스 초안'),el('p',value.운영검토기록?'담당자의 운영·일정 확인을 반영했습니다. 4단계 준비 여부는 준비 검사 결과를 확인하세요. AI는 실행하지 않았습니다.':value.코스수정기록?'기존 AI 초안에 담당자 수정 사항을 반영했습니다. AI를 다시 실행하지 않았으며 코스 확정 전입니다.':'AI가 생성한 초안입니다. 시간·운영정보·식사 구성과 남은 경고를 확인하세요. 담당자가 확정한 코스가 아닙니다.','help'));
  if(value.코스수정기록){panel.append(el('h3','담당자 수정 반영 · AI 재실행 없음'));for(const p of value.코스수정기록.변경목록 || [])panel.append(el('p',p));for(const p of value.코스수정기록.재검토항목 || [])panel.append(el('p',p,'help'));panel.append(el('p','아래 기존 AI 메모와 근거는 수정 전 생성 기록을 포함합니다. 변경된 구간은 재검토가 필요합니다.','help'));}
  const start=value.코스시작종료 || {},day=v=>[1,2].includes(v)?`${v}일차`:'일차 미정';panel.append(el('p',`시작: ${day(start.시작일차)} ${start.시작지점 || '미정'} ${start.시작시각 || ''} → 종료: ${day(start.종료일차)} ${start.종료지점 || '미정'} ${start.종료시각 || ''}`));
  const cell=v=>String(v??'미정').replaceAll('|',' / ').replaceAll('\n',' ');
  const time=v=>v && typeof v==='object'?`${v.값 || '미정'} (${v.종류 || '미정'})`:'미정';
  const rows=['| 안 | 일차 | 시각 | 구분 | 장소 | 근거 |','|---|---|---|---|---|---|'];
  for(const r of value.칸목록){if(!r || typeof r!=='object')continue;rows.push('| '+[r.안 || '공통',r.일차,time(r.시각),r.시간칸,r.장소명,Array.isArray(r.근거ID)?r.근거ID.join(', '):'미확인'].map(cell).join(' | ')+' |');}
  panel.append(table(rows));
  for(const [title,key] of [['식사 구성','식사목록'],['남은 경고','남은경고'],['미확인 사항','미확인사항']]){
    panel.append(el('h3',title));const values=Array.isArray(value[key])?value[key]:[];
    if(!values.length){panel.append(el('p','기록 없음'));continue;}
    for(const r of values){if(r==null)continue;panel.append(el('p',key==='식사목록'?`${r.안 || '공통'} · ${r.칸ID || ''} · ${r.방식 || '미정'} · 식비 ${r.식비포함 || '미정'} · ${r.식당 || r.권역 || '식당·권역 미정'}`:typeof r==='object'?r.문구 || `${r.칸ID || r['대상 칸ID'] || ''} · ${r.내용 || JSON.stringify(r)}`:String(r)));}
  }
}
document.getElementById('courseForm').addEventListener('submit',saveCourse);
document.getElementById('courseStart').addEventListener('click',startCourse);
document.getElementById('courseApply').addEventListener('click',applyCourse);
function courseEdited(){if(courseState.busy || courseState.job?.상태==='실행중')return;courseState.job=null;clearTimeout(courseState.poll);drawCourseStatus(null);showCourseSelection();document.getElementById('courseMessage').textContent='미저장 변경이 있습니다. 기존 초안은 수정 반영 버튼을 눌러 저장하세요.';courseButtons();}
document.getElementById('courseForm').addEventListener('input',courseEdited);
document.getElementById('courseForm').addEventListener('change',courseEdited);
for(const id of ['adminCourseOptions','adminMealOptions']){
  document.getElementById(id)?.addEventListener('input',courseEdited);
  document.getElementById(id)?.addEventListener('change',courseEdited);
}
