// 읽기 전용 서비스 운영 로그. AI 호출·저장·확정 API를 사용하지 않는다.
'use strict';
const $=id=>document.getElementById(id);
let generation=0,selected='';
async function read(url){const r=await fetch(url,{cache:'no-store'});const body=await r.json();if(!r.ok)throw new Error(body.오류||'기록을 읽지 못했습니다.');return body;}
function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
function badge(state){const n=node('span',state||'기록 없음');n.className='badge';n.dataset.state=state;return n;}
function renderDiagnosis(d){
  const box=$('diagnosis');box.replaceChildren();
  const date=new Date(d.시각);const stamp=d.시각&&!Number.isNaN(date.getTime())?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(date):'시각 미수집';
  const banner=node('div');banner.className='status-banner';banner.append(badge(d.상태),node('span',stamp+' · 저장 기록 기준'));box.append(banner);
  if(d.상태==='실패'){
    const failure=node('section');failure.className='failure-card';failure.append(node('h3',d.실패단계==='미기록'?'실행 중단 · 단계 미기록':d.실패단계+'에서 멈췄습니다'));
    const grid=node('div');grid.className='cause-grid';
    for(const [label,text] of [['실패 원인',d.원인],['확인할 항목',d.조치]]){const card=node('div');card.append(node('h4',label),node('p',text));grid.append(card);}failure.append(grid);
    if(d.로그경로){const button=node('button','상세 오류 보기');button.type='button';button.onclick=()=>{$('rawLogs').open=true;$('logFile').value=d.로그경로;file(d.로그경로,generation);$('logBody').focus();};failure.append(button);}box.append(failure);
  }else if(d.상태==='기록 확인 필요'){box.append(node('p','기록 파일을 읽지 못했습니다. 아래 원문에서 저장 상태를 확인하세요.'));}
  const steps=d.단계||[];
  if(steps.length){
    box.append(node('h3','단계별 실행'));
    const list=node('ol');list.className='stage-list';
    for(const [i,step] of steps.entries()){
      const li=node('li');li.dataset.state=step.상태;
      const name=node('span');name.append(node('b',String(i+1).padStart(2,'0')),node('strong',step.이름));
      li.append(name,badge(step.상태));
      if(step.시작&&step.끝){const ms=Date.parse(step.끝)-Date.parse(step.시작);if(Number.isFinite(ms)&&ms>=0)li.append(node('small',Math.round(ms/1000)+'초'));}
      list.append(li);
    }box.append(list);
  }else box.append(node('p','이 실행에는 단계별 진행 기록이 없습니다.'));
  if(d.상태==='실패'){
    const facts=node('dl');facts.className='diagnosis-facts';
    for(const [label,value] of [['AI',d.제공자],['모델',d.모델],['오류 종류',d.오류종류],['실패 호출',d.경과초==null?'미수집':d.경과초+'초']]){const pair=node('div');pair.append(node('dt',label),node('dd',value));facts.append(pair);}box.append(facts);
  }
}
async function load(){
  const box=$('runs');box.replaceChildren(node('p','불러오는 중…'));
  try{
    const rows=await read('/api/runs');box.replaceChildren();
    if(!rows.length){box.append(node('p','저장된 실행이 없습니다.'));return;}
    for(const row of rows){const c=row.조건||{};const b=node('button',[c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · ')||row.id);
      b.prepend(badge(row.운영진단?.상태));b.append(node('small',row.id));b.onclick=()=>show(row.id);b.dataset.id=row.id;box.append(b);}
    await show(rows.some(x=>x.id===selected)?selected:rows[0].id);
  }catch(e){box.replaceChildren(node('p',e.message));}
}
async function show(id){
  const own=++generation;selected=id;$('notice').textContent='';$('diagnosis').replaceChildren(node('p','진단을 불러오는 중…'));$('logBody').textContent='불러오는 중…';$('logFile').disabled=true;$('rawLogs').open=false;
  try{
    const record=await read('/api/run?id='+encodeURIComponent(id));if(own!==generation)return;
    const c=record.조건||{};$('recordTitle').textContent=[c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · ')||id;
    renderDiagnosis(record.운영진단||{상태:'기록 없음'});
    $('meta').textContent=`근거 ${record.근거수}건 · 경고 ${record.경고수}건 · 단계 전달 검사: ${record.검사상태} (전체 실행 결과와 별도)`;
    $('runs').querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.id===id));
    const files=record.파일||[];const select=$('logFile');select.replaceChildren();
    for(const file of files){const option=node('option',file.경로.slice(id.length+1));option.value=file.경로;select.append(option);}
    select.disabled=!files.length;
    const first=files.find(x=>x.경로===record.운영진단?.로그경로)||files.find(x=>x.이름==='기획_진행.json');if(first)select.value=first.경로;
    select.onchange=()=>file(select.value,own);
    if(files.length)await file(select.value,own);else $('logBody').textContent='조회할 기록 파일이 없습니다.';
  }catch(e){if(own===generation){$('diagnosis').replaceChildren();$('notice').textContent=e.message;$('logBody').textContent='기록 조회를 완료하지 못했습니다.';}}
}
async function file(key,own){
  try{const r=await read('/api/file?path='+encodeURIComponent(key));if(own!==generation||$('logFile').value!==key)return;
    let text=r.본문;if(r.형식==='json'){try{text=JSON.stringify(JSON.parse(text),null,2);}catch{}}
    $('logBody').textContent=text;
  }catch(e){if(own===generation)$('notice').textContent=e.message;}
}
$('refresh').onclick=load;load();
