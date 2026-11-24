// 읽기 전용 서비스 운영 로그. AI 호출·저장·확정 API를 사용하지 않는다.
'use strict';
const $=id=>document.getElementById(id);
let generation=0,selected='';
async function read(url){const r=await fetch(url,{cache:'no-store'});const body=await r.json();if(!r.ok)throw new Error(body.오류||'기록을 읽지 못했습니다.');return body;}
function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
async function load(){
  const box=$('runs');box.replaceChildren(node('p','불러오는 중…'));
  try{
    const rows=await read('/api/runs');box.replaceChildren();
    if(!rows.length){box.append(node('p','저장된 실행이 없습니다.'));return;}
    for(const row of rows){const c=row.조건||{};const b=node('button',[c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · ')||row.id);
      b.append(node('small',row.id));b.onclick=()=>show(row.id);b.dataset.id=row.id;box.append(b);}
    if(selected)await show(selected);
  }catch(e){box.replaceChildren(node('p',e.message));}
}
async function show(id){
  const own=++generation;selected=id;$('notice').textContent='';$('logBody').textContent='불러오는 중…';$('logFile').disabled=true;
  try{
    const record=await read('/api/run?id='+encodeURIComponent(id));if(own!==generation)return;
    $('recordTitle').textContent=id;$('meta').textContent=`근거 ${record.근거수}건 · 경고 ${record.경고수}건 · 전달 검사 ${record.검사상태}`;
    $('runs').querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.id===id));
    const files=record.파일||[];const select=$('logFile');select.replaceChildren();
    for(const file of files){const option=node('option',file.경로.slice(id.length+1));option.value=file.경로;select.append(option);}
    select.disabled=!files.length;
    const progress=files.find(x=>x.이름==='기획_진행.json');if(progress)select.value=progress.경로;
    select.onchange=()=>file(select.value,own);
    if(files.length)await file(select.value,own);else $('logBody').textContent='조회할 기록 파일이 없습니다.';
  }catch(e){if(own===generation){$('notice').textContent=e.message;$('logBody').textContent='기록 조회를 완료하지 못했습니다.';}}
}
async function file(key,own){
  try{const r=await read('/api/file?path='+encodeURIComponent(key));if(own!==generation||$('logFile').value!==key)return;
    let text=r.본문;if(r.형식==='json'){try{text=JSON.stringify(JSON.parse(text),null,2);}catch{}}
    $('logBody').textContent=text;
  }catch(e){if(own===generation)$('notice').textContent=e.message;}
}
$('refresh').onclick=load;load();
