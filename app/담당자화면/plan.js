// 담당자에게 보여 주는 말만 정리한다. 원본 코스·근거·검사 기록은 수정하지 않는다.
(function(root){
  function 문장(value){
    let text=String(value??'');
    const interest=/관심/.test(text);
    const countNote=interest&&/((?:19|20)\d{2})\s*년?\s*\d+\s*번/.test(text)&&!/실제 방문.*아니/.test(text);
    text=text.replace(/((?:19|20)\d{2})\s*년?\s*(\d+)\s*번/g,(_,year,n)=>
      interest?`${year}년 관심 관광지 목록에 ${n}회 등장`:`${year}년 자료에 ${n}회 기록`);
    text=text
      .replace(/\b(?:S3-[A-Z]+\d*|[RWSO]\d+)(?:[~～·,\s]*(?:[RWSO]\d+))*/g,'')
      .replace(/(?:희망|후보)-\d+\s*(?:반영)?/g,'')
      .replace(/(낮오후|낮|점심|저녁|밤|숙박)-\d+/g,(_,slot)=>(slot==='낮오후'?'오후':slot)+' 일정')
      .replace(/2일-오전-\d+/g,'둘째 날 오전')
      .replace(/\([^)]*운영시트[^)]*\)/g,'')
      .replace(/치킨선택 필드는 미선택 그대로입니다\.?/g,'치킨 식사 여부는 아직 정하지 않았어요.')
      .replace(/저장소에서 확인된/g,'확보한 자료에서 확인된')
      .replace(/2단계에도/g,'수요 분석 자료에도')
      .replace(/\(\s*\)|\[\s*\]/g,'')
      .replace(/\(\s*[,·]\s*/g,'(').replace(/\s+([,.])/g,'$1')
      .replace(/\(\s+/g,'(').replace(/\s{2,}/g,' ').trim();
    return text+(countNote?' 관심 목록에 포함된 횟수이며 실제 방문자 수는 아니에요.':'');
  }
  function 짧게(value,max=140){
    const text=문장(value);
    return text.length>max?text.slice(0,max-1).trimEnd()+'…':text;
  }
  function 상태(rec){
    const groups=rec.분류||{};
    if(!rec.검사함)return {종류:'대기',제목:'아직 검토가 끝나지 않았어요',설명:'코스는 초안이에요. 일정과 운영 정보를 확인한 뒤 진행해 주세요.'};
    if((groups.AI수정||[]).length||(groups.자료보완||[]).length||rec.검증==='반려')
      return {종류:'보완',제목:'일정에 보완할 점이 있어요',설명:'이동·운영 정보 등 확인이 남아 있어요. 지금은 확정 전 초안으로 검토해 주세요.'};
    if(rec.검증!=='통과')return {종류:'대기',제목:'코스 검토가 더 필요해요',설명:'기본 점검 이후의 검토가 아직 끝나지 않았어요.'};
    return {종류:'확인',제목:'초안 검토를 마쳤어요',설명:'담당자가 장소·시간과 운영 조건을 확인한 뒤 확정해 주세요.'};
  }
  function 할일(rec){
    const texts=[...(rec.분류?.사람결정||[]).map(x=>x.문구||''),...(rec.요약?.확인할것||[])];
    const result=[];const seen=new Set();let unknown=false;
    const add=(제목,설명)=>{if(!seen.has(제목)){seen.add(제목);result.push({제목,설명});}};
    for(const text of texts){
      if(/좌표|희망.*(?:일부|못지킴)/.test(text))continue;
      if(/시작|종료/.test(text))add('여행의 시작과 끝','집결·해산 장소와 시각을 정해 주세요.');
      else if(/2일|둘째|오전선택/.test(text))add('둘째 날 오전','관광·자유시간·바로 귀가 중 어떻게 보낼지 골라 주세요.');
      else if(/숙박|숙소/.test(text))add('숙박 일정','숙소와 도착·다음 날 출발 시각을 확인해 주세요.');
      else if(/식사|식당|식비/.test(text))add('식사 방식','자유식·지정식과 식사 비용의 포함 여부를 정해 주세요.');
      else if(/운영\s*방식|단체|개별/.test(text))add('여행 운영 방식','단체 동행 또는 개별 이동 방식을 골라 주세요.');
      else if(/겹침|노선/.test(text))add('기존 상품과의 겹침','겹치는 구간을 유지할지 조정할지 골라 주세요.');
      else if(text)unknown=true;
    }
    if(unknown)add('추가 확인','그 밖의 담당자 확인 사항이 있어요. 팀 검토 후 진행해 주세요.');
    return result;
  }
  function 보완요약(rec){
    const texts=[...(rec.분류?.AI수정||[]),...(rec.분류?.자료보완||[])].map(x=>x.문구||'');
    const notes=[];
    for(const text of texts){
      const travel=text.match(/이동[^.]*?(\d+)분[^.]*?상한\s*(\d+)분/)||text.match(/대중교통\s*(\d+)분[^.]*?상한\s*(\d+)분/);
      if(travel)notes.push(`한 구간의 이동이 ${travel[1]}분으로 기준 ${travel[2]}분을 넘어요.`);
      else if(/일정 겹침|시간.*겹/.test(text))notes.push('일부 일정의 시간이 겹쳐 조정이 필요해요.');
      else if(/선택 지역 밖|범위 밖 후보|필수 조건 지역 못지킴/.test(text))notes.push('선택한 지역 밖 장소가 있어 동선을 조정해야 해요.');
      else if(/야시장/.test(text)&&/요일|동계|운영|휴무/.test(text))notes.push('야시장 운영 요일과 시간을 확인해야 해요.');
      else if(/운영시간|운영 시간/.test(text))notes.push('일부 방문 장소의 운영시간 확인이 남아 있어요.');
    }
    return [...new Set(notes)].slice(0,2);
  }
  const api={문장,짧게,상태,할일,보완요약};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.기획표시=api;
})(typeof globalThis!=='undefined'?globalThis:this);

if(typeof document!=='undefined'){
// 담당자 화면: ① 조건 고르기 → ② AI 에이전트들이 코스를 만드는 모습 → ③ 코스 확인(동선·시간표).
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain=s=>esc(기획표시.문장(s));
const short=s=>esc(기획표시.짧게(s));
const slotName=s=>({'낮오후':'오후','2일차오전':'둘째 날 오전'}[s]||s);
const stopName=s=>기획표시.문장((s.표시명||s.장소명||(s.시간칸==='2일차오전'?'둘째 날 오전':slotName(s.시간칸))||'일정 미정').split(/\s*[—–]\s*/)[0]);
async function get(url){const r=await fetch(url);const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오기 실패');return d;}
let token=null,poll=null,tick=null,last=null;
async function post(url,body){
  token=token||(await get('/api/session')).token;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':token},body:JSON.stringify(body)});
  const d=await r.json();if(!r.ok)throw new Error(d.오류||'요청 실패');return d;
}
const guide=n=>`<ol class="guide">${['조건 고르기','AI가 코스 만들기','코스 확인'].map((t,i)=>`<li class="${i+1===n?'on':''}"><b>${i+1}</b>${t}</li>`).join('')}</ol>`;
const 칸색=s=>s.일차===2&&s.시간칸==='2일차오전'?'day':['저녁'].includes(s.시간칸)?'eve':['밤','숙박'].includes(s.시간칸)?'night':'day';

// ---------- 지난 코스 목록 ----------
async function loadList(select){
  const box=$('saved');
  try{
    const runs=await get('/api/runs');const items=[];
    for(const run of runs){
      let info;try{info=await get('/api/course?id='+encodeURIComponent(run.id));}catch{continue;}
      for(const t of info.시험목록||[])if(t.시험id)items.push({id:t.시험id,조건:run.조건,시각:t.기록시각||''});
    }
    items.sort((a,b)=>b.시각.localeCompare(a.시각));
    if(!items.length){box.innerHTML='<p class="empty">아직 만든 코스가 없어요.</p>';return items;}
    box.innerHTML='';
    for(const it of items){
      const c=it.조건||{};const b=document.createElement('button');b.dataset.id=it.id;
      b.innerHTML=`<b>${esc([c.계절,c.체류기간].filter(Boolean).join(' · '))}</b> ${esc([(c.언어권||[]).join('·'),(c.지역||[]).join('·')].filter(Boolean).join(' · '))}<br><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small>`;
      b.onclick=()=>show(it.id,c);box.append(b);
    }
    if(select)show(select,(items.find(x=>x.id===select)||{}).조건||{});
    return items;
  }catch(e){box.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return [];}
}
function mark(id){$('saved').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.id===id));}

// ---------- ① 조건 고르기 (주문서) ----------
const 선택지={계절:['봄','여름','가을','겨울'],언어권:['영어권','일본어','중국어 간체','중국어 번체'],지역:['중구','동구'],체류기간:['당일','1박2일']};
const 여러개={언어권:1,지역:1};
function newForm(){
  mark(null);
  const q=(name,label,help)=>`<div class="q"><span>${label}${help?`<small>${help}</small>`:''}</span><div class="pills" data-name="${name}">${선택지[name].map(v=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(v)}">${esc(v)}</button>`).join('')}</div></div>`;
  $('main').innerHTML=`<section class="card">${guide(1)}
    <h2>어떤 코스를 만들까요?</h2>
    <p class="lead">꼭 지킬 조건을 고르고, 바라는 점이 있으면 적어 주세요. AI 에이전트들이 자료 확인부터 코스 초안까지 이어서 만들어요.</p>
    <p class="note">고른 지역과 여행 조건 안에서 코스를 제안해요. 시작·종료 장소나 식사 방식이 미정이어도 초안부터 볼 수 있어요.</p>
    <form class="order" id="order">
      ${q('계절','계절')}${q('언어권','대상 언어권','여러 개 고를 수 있어요')}${q('지역','지역','여러 개 고를 수 있어요')}${q('체류기간','체류 기간')}
      <div class="sec">바라는 점 <span class="note">(선택 · 지키기 어려우면 AI가 이유를 남기고 조정할 수 있어요)</span></div>
      <label class="q"><span>목표</span><input name="목표" maxlength="300" placeholder="예: 필수 대상은 일본인 커플, 중구에서 저녁과 숙박으로 연결"></label>
      <label class="q"><span>희망 사항<small>한 줄에 하나</small></span><textarea name="희망" rows="3" placeholder="예: 저녁 이후 야경을 넣고 싶어요&#10;이동을 줄이고 여유롭게 식사하고 싶어요"></textarea></label>
      <p class="agree">시작하면 중간 알림·경고는 기록에 남기고 <b>코스 초안까지 자동으로 진행</b>해요. 기관 데이터는 '없음'으로 진행하고, 코스 확정·홍보·문서는 하지 않아요.</p>
      ${last&&last.상태==='진행중'?'<p class="note">지금 만들고 있는 코스가 있어요. 한 번에 하나씩 만들어요. 끝난 뒤 시작해 주세요.</p>':''}
      <div class="go"><span class="note" id="need"></span><span class="err" id="newErr"></span><button class="btn primary big" id="newGo" type="submit" disabled>코스 만들기 시작</button></div>
    </form></section>`;
  const f=$('order');
  const 값=()=>{const v={};for(const n in 선택지){const on=[...f.querySelectorAll(`[data-name="${n}"] [aria-pressed=true]`)].map(b=>b.dataset.v);v[n]=여러개[n]?on:on[0]||'';}return v;};
  const check=()=>{const v=값();const miss=Object.keys(선택지).filter(n=>!v[n]||!v[n].length).map(n=>({계절:'계절',언어권:'언어권',지역:'지역',체류기간:'체류 기간'}[n]));
    $('need').textContent=miss.length?`남은 것: ${miss.join(', ')}`:'';$('newGo').disabled=miss.length>0;};
  f.querySelectorAll('.pills').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('.pill');if(!b)return;
    if(!여러개[g.dataset.name])g.querySelectorAll('.pill').forEach(x=>x!==b&&x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');check();}));
  check();
  f.onsubmit=async e=>{e.preventDefault();$('newGo').disabled=true;$('newErr').textContent='';
    try{const p=await post('/api/plan/start',{...값(),목표:f.목표.value.trim(),희망:f.희망.value.split('\n').map(x=>x.trim()).filter(Boolean),자동진행동의:true});  // 시작 버튼 옆 안내 문구를 보고 누르는 것이 동의
      $('main').innerHTML='';showProgress(p);watch(p.기획id);}
    catch(err){$('newErr').textContent=err.message;check();}};
}

// ---------- ② 진행 상황: 지금 일하는 에이전트 ----------
const 아이콘=[ // 돋보기 · 막대그래프 · 지도핀 · 체크 (직접 그린 단순 도형)
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 20V11M12 20V5M19 20v-6"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-6-5.6-6-10.5a6 6 0 0 1 12 0C18 15.4 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="6" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M12 8.5v4M12 12.5 6.5 16M12 12.5l5.5 3.5"/></svg>'];
const 걸린=(a,b)=>{const s=Math.max(0,Math.round(((b?new Date(b):new Date())-new Date(a))/1000));return s<60?`${s}초`:`${Math.floor(s/60)}분 ${s%60}초`;};
function showProgress(p){
  last=p;const box=$('progress');if(!p){box.hidden=true;return;}
  box.hidden=false;const c=p.조건||{};const 진행=p.상태==='진행중';
  const head={진행중:'AI 에이전트들이 코스를 만들고 있어요',완료:'코스 초안이 나왔어요',멈춤:'진행이 멈췄어요',중단됨:'실행이 끊겼어요'}[p.상태]||p.상태;
  const cards=(p.단계||[]).map((s,i)=>{const cls={진행중:'now',완료:'done',실패:'fail'}[s.상태]||'';
    const st=s.상태==='진행중'?`일하는 중 · <span data-since="${esc(s.시작)}">${걸린(s.시작)}</span>`:s.상태==='완료'?`완료 · ${s.시작?걸린(s.시작,s.끝):''}`:s.상태==='실패'?'멈춤':'차례 기다리는 중';
    return `<div class="agent ${cls}"><span class="tag">${s.AI===false?'코드':'AI'}</span><div class="ic">${아이콘[i]||''}</div><b>${esc(s.에이전트||s.이름)}</b><p>${esc(s.하는일||s.이름)}</p><div class="st">${st}</div></div>`;}).join('');
  const w=p.일하는중;
  const msg=진행&&w?`<div class="working">지금 <b>${esc(w.에이전트)}</b>가 일하고 있어요 — ${esc(w.하는일)}. 몇 분 걸릴 수 있어요. 창을 닫거나 새로고침해도 이어서 볼 수 있어요.</div>`
    :p.상태==='완료'?`<div class="working ok">${esc(p.안내||'')}</div>`:`<div class="working ${진행?'':'stop'}">${esc(p.안내||'')}</div>`;
  const 활동=(p.활동||[]).slice(-8).reverse();
  const 로그=활동.length?`<details><summary>만드는 과정 자세히 보기</summary><ol class="log">${활동.map(a=>`<li class="${a.상태==='진행중'?'now':a.상태==='실패'?'fail':''}"><b>${esc(a.에이전트)}</b> ${plain(a.하는일)}${a.결정?`<br><span class="note">${short(a.결정)}</span>`:''}<span class="when">${a.상태==='진행중'?'일하는 중':a.시작?걸린(a.시작,a.끝):''}</span></li>`).join('')}</ol></details>`:'';
  const 정리=p.정리;const 남은=정리?정리.사람이정할것:((p.검사&&p.검사.남은문제)||[]);
  box.innerHTML=`${guide(p.상태==='완료'?3:2)}<div class="top"><div><h2>${esc(head)}</h2><span class="note">${esc([c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · '))}${p.목표?' · 목표: '+esc(p.목표):''}</span></div>
    <div>${p.상태==='완료'&&p.시험id?`<button class="btn primary" id="seeNew">만든 코스 보기</button> `:''}${진행?'':'<button class="btn" id="closeP">닫기</button>'}</div></div>
    ${msg}<details><summary>단계별 진행 상황</summary><div class="agents">${cards}</div></details>
    ${로그}
    ${남은.length?'<p class="note">담당자가 정할 항목은 만든 코스에서 간단히 확인할 수 있어요.</p>':''}
    ${p.희망&&p.희망.length?`<p class="note">바라는 점: ${p.희망.map(esc).join(' / ')}</p>`:''}`;
  if($('seeNew'))$('seeNew').onclick=()=>{box.hidden=true;loadList(p.시험id);};
  if($('closeP'))$('closeP').onclick=()=>{box.hidden=true;};
  clearInterval(tick);if(진행)tick=setInterval(()=>box.querySelectorAll('[data-since]').forEach(x=>x.textContent=걸린(x.dataset.since)),1000);
}
function watch(id){
  clearInterval(poll);
  poll=setInterval(async()=>{
    try{const p=await get('/api/plan/status?id='+encodeURIComponent(id));showProgress(p);
      if(p.상태!=='진행중'){clearInterval(poll);clearInterval(tick);if(p.상태==='완료')loadList();}}
    catch{clearInterval(poll);}
  },3000);
}

// ---------- ③ 코스 확인 ----------
async function show(id,cond,안,버전){
  mark(id);const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  try{const rec=await get('/api/plan/record?id='+encodeURIComponent(id)+(안?'&안='+안:'')+(버전?'&버전='+버전:''));if(rec.있음)return showRecord(id,cond||{},rec);}catch{}
  let s;try{s=await get('/api/plan/course?id='+encodeURIComponent(id));}catch(e){main.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return;}
  const k=s.조건||{};cond=cond||{};
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간,k.시작지점&&k.종료지점&&!(k.시작지점==='미확인'&&k.종료지점==='미확인')?`${k.시작지점} → ${k.종료지점}`:'시작·종료 장소 미정'].filter(Boolean);
  const days=s.출발가능요일?.length?`<p>출발 가능 요일: <span class="days">${esc(s.출발가능요일.join(' · '))}</span> <span class="note">(장소별 정기휴무로 계산)</span></p>`:'';
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
  <section class="card ai"><div class="aihead"><span class="aibadge">AI 코스 초안</span><strong>${s.코스있음?'담당자가 확인할 것':'아직 코스가 없어요'}</strong></div>${days}
    ${s.확인할것.length?`<ul>${s.확인할것.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="note">확인할 것이 없어요.</p>'}
    <p class="note">이전 방식으로 저장된 초안이에요. 이 기록에는 A·B 비교 정보가 없어요. 아래 시각은 추천 동선을 살펴보는 기준이며 실제 예약·운영시간을 확인해야 해요.</p></section>
  ${s.코스있음?`<section class="card"><div class="aihead"><strong>동선 · 시간표</strong>
    <span class="legend"><span><i class="lg-day"></i>낮</span><span><i class="lg-eve"></i>저녁</span><span><i class="lg-night"></i>밤·숙박</span></span></div>
    <div class="mapgrid"><div id="mapbox"></div><div class="timeline" id="timeline"></div></div></section>`:''}`;
  if(s.코스있음)draw(s.일정);
}
const 분류이름={AI수정:['AI가 고칠 것','시간 겹침·형식 오류처럼 코스가 틀린 것. 총괄이 코스 에이전트에게 고치게 해요. 남아 있으면 고치지 못한 것이에요.'],
  자료보완:['자료 보완','자료가 없어 생긴 것. 수집 에이전트가 저장소 자료에서 찾아요. 남아 있으면 못 찾은 것이에요.'],
  사람결정:['담당자가 정할 것','시작·종료, 2일차 오전, 식사 방식, 지키지 못한 희망처럼 사람이 정할 것이에요.']};
function showRecord(id,cond,rec){
  const main=$('main');const 정리=rec.정리;const 안=정리.안.find(a=>a.안id===rec.안id);const s=rec.요약;
  const 원희망=Object.fromEntries((rec.원래요청.희망||[]).map(h=>[h.id,h.내용]));
  const 이전=rec.버전!==안.버전;
  const 상태=기획표시.상태({...rec,검증:이전?'검증 전':안.검증});
  const 주요확인=기획표시.보완요약(rec);
  const tabs=정리.안.map(a=>{
    const active=a.안id===rec.안id;
    const label=a.안id==='A'?'A안 · 내 요청을 우선한 안':`${a.안id}안 · 구성을 조정한 안`;
    const reason=a.대안설명?.왜||a.이유||a.설명||'저장된 코스의 동선과 일정을 확인해 보세요.';
    return `<button class="tab plan-choice ${active?'on':''}" aria-pressed="${active}" data-plan="${esc(a.안id)}"><span class="choice-top"><b>${esc(label)}</b><span class="choice-badge">${active?'보고 있는 코스':'다른 코스 보기'}</span></span><small>${short(reason)}</small></button>`;
  }).join('')+(!정리.안.some(a=>a.안id==='B')?`<div class="tab plan-choice missing-plan"><span class="choice-top"><b>B안 · 구성을 조정한 안</b><span class="choice-badge">아직 없음</span></span><small>${short(정리.대안상태?.이유||'이 저장 기록에는 B안이 없어요. 새 기획에서는 A/B 비교안을 함께 요청해요.')}</small></div>`:'');
  const vers=(안.버전들||[]).length>1?`<div class="vers"><span>수정 이력</span> ${안.버전들.map(v=>`<button class="pill" aria-pressed="${v===rec.버전}" data-v="${v}">${v}번째 초안${v===안.버전?' · 최신':''}</button>`).join('')}</div>`:'';
  const 바꾼=Object.entries(안.바꾼희망||{});
  const 설명=안.대안설명||{};
  const alt=바꾼.length||안.대안설명?`<div class="alternative-note"><h3>이 대안은 이렇게 달라요</h3>
    ${바꾼.map(([k,v])=>`<p class="chg"><s>${plain(원희망[k]||'원래 희망')}</s> → <b>${plain(v)}</b></p>`).join('')}
    <p>${short(설명.왜||안.이유||'변경 이유는 팀 검토가 필요해요.')}</p>
    ${설명.남은문제?`<p class="note">더 확인할 점: ${short(설명.남은문제)}</p>`:''}</div>`:'';
  // 이전 버전에는 최신 버전의 희망 반영 설명을 붙이지 않는다.
  const wish=!이전&&(안.희망반영||[]).length?`<section class="card"><h3>요청을 이렇게 반영했어요</h3><ul class="wish">${안.희망반영.map(h=>{
    const status=({지킴:'일정에 반영',일부:'일부 반영',못지킴:'조정 필요'})[h.반영]||'확인 필요';
    const reason=기획표시.문장(h.이유||'반영 이유가 아직 정리되지 않았어요.');
    return `<li class="w-${esc(h.반영)}"><div><span class="tagw">${esc(status)}</span> <b>${plain(h.내용||원희망[h.희망id]||'요청 사항')}</b></div><p>${esc(기획표시.짧게(reason))}</p>${reason.length>140?`<details class="reason-more"><summary>반영 이유 더 보기</summary><p>${esc(reason)}</p></details>`:''}</li>`;
  }).join('')}</ul></section>`:'';
  const 필수=rec.필수조건반영||안.필수조건반영||[];
  const required=필수.length?`<details class="condition-detail"><summary>선택 조건 반영 내용</summary><ul>${필수.map(x=>`<li><b>${plain(x.조건)} · ${plain(x.반영)}</b><p>${plain(x.이유||'이유를 다시 확인해야 합니다.')}</p></li>`).join('')}</ul></details>`:'';
  const 분=rec.분류||{};
  const 검사=`<h3>검사 원문</h3><p class="note">아래는 팀 검토용 기록이에요. 같은 확인 항목이 여러 검사에서 반복될 수 있어요.</p><div class="three">${Object.keys(분류이름).map(k=>`<div class="col c-${k}"><b>${분류이름[k][0]} <span class="cnt">${(분[k]||[]).length}</span><span class="sr-only"> · ${esc(rec.안id)}안 ${rec.버전}버전</span></b><ul>${(분[k]||[]).map(x=>`<li>${esc(x.문구)}<small> · ${esc(x.출처)}</small></li>`).join('')||'<li class="none">없음</li>'}</ul></div>`).join('')}</div>`;
  const 기=rec.부분수정기록;
  const 부분=기?`<p class="note">최근 수정 요청: ${plain(기.요청)}</p>`:'';
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간].filter(Boolean);
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
    <section class="card ai recommendation"><div class="aihead"><span class="aibadge">코스 초안</span><h2>코스 제안</h2><span class="draft-badge">확정 전 초안</span></div>
      <p class="lead">${정리.안.length>1?'요청을 바탕으로 만든 코스와 대안을 비교해 보세요.':'요청을 바탕으로 만든 코스예요. 동선과 일정을 먼저 살펴보세요.'}</p>
      <div class="tabs plan-choices">${tabs}</div>
      ${(s.일정||[]).length?`<p class="route-preview">${s.일정.slice(0,5).map(x=>esc(stopName(x))).join(' <span aria-hidden="true">→</span> ')}${s.일정.length>5?' …':''}</p>`:''}
      ${이전?'<div class="review-status state-대기"><b>이전 수정본을 보고 있어요</b><p>최신 코스로 돌아가서 현재 검토 내용을 확인해 주세요.</p><button class="btn" id="latestPlan">최신 코스 보기</button></div>':''}
      <div class="review-status state-${상태.종류}" role="status"><b>${esc(상태.제목)}</b><p>${esc(상태.설명)}</p>${주요확인.length?`<ul>${주요확인.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:''}</div>
      ${s.출발가능요일?.length?`<p class="departure"><b>출발 요일 참고</b> ${esc(s.출발가능요일.join(' · '))}<span class="note">정기휴무 기준이에요. 운영 변경 여부는 출발 전 확인해 주세요.</span></p>`:''}
      ${부분}${alt}${required}</section>
    ${s.코스있음?`<section class="card"><div class="aihead"><strong>동선 · 시간표</strong>
      <span class="legend"><span><i class="lg-day"></i>낮</span><span><i class="lg-eve"></i>저녁</span><span><i class="lg-night"></i>밤·숙박</span></span></div>
      <div class="mapgrid"><div id="mapbox"></div><div class="timeline" id="timeline"></div></div></section>`:''}
    <section class="card freedom"><h3>어디까지 자유롭게 이용하나요?</h3><p>표시된 순서와 시각은 권장 일정이에요. 관광·식사는 장소의 운영시간 안에서 선택할 수 있도록 기획합니다.</p><p class="note">예약이나 이용권에 실제로 정해진 시간이 있다면 그 조건을 따라야 해요. 미정인 사용처·유효시간·포함 혜택은 아직 확정된 상품 조건이 아니에요. 집결·해산이나 숙소 예약을 먼저 입력할 필요는 없어요.</p></section>
    ${wish}
    <section class="card"><h3>바꾸고 싶은 부분이 있나요?</h3><p class="note">고른 일정만 다시 제안해요. 나머지 일정과 이전 초안은 보존해요.</p>
      <div class="pills" id="redo">${rec.시간칸.map(k=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(k)}">${esc(slotName(k))}</button>`).join('')}</div>
      <div class="redo-row"><input id="redoText" maxlength="300" placeholder="예: 낮은 유지하고 저녁만 설문 음식 후보로 바꿔 주세요"><button class="btn primary" id="redoGo" disabled>다시 만들기</button></div>
      <p class="note" id="keep"></p><p class="err" id="redoErr"></p></section>
    <details class="card technical"><summary>팀 검토용 상세 · 수정 이력과 검사 기록</summary><p class="note">${esc(rec.안id)}안은 ${rec.안id==='A'?'원래 요청으로 만든 코스':'구성을 조정한 대안'}이고, ${rec.버전}버전은 같은 코스를 ${rec.버전}번째로 작성한 기록이에요. 서로 다른 여행 상품 ${rec.버전}개를 뜻하지 않아요.</p>${vers}${검사}<p><a href="/admin/">서비스 제공자용 로그 보기 ↗</a></p></details>`;
  if(s.코스있음)draw(s.일정);
  if($('latestPlan'))$('latestPlan').onclick=()=>show(id,cond,rec.안id);
  main.querySelectorAll('.tab').forEach(b=>b.onclick=()=>show(id,cond,b.dataset.plan));
  main.querySelectorAll('.vers .pill').forEach(b=>b.onclick=()=>show(id,cond,rec.안id,b.dataset.v));
  const redo=$('redo');const pick=()=>[...redo.querySelectorAll('[aria-pressed=true]')].map(b=>b.dataset.v);
    const upd=()=>{const p=pick();$('keep').textContent=p.length?`그대로 둘 일정: ${rec.시간칸.filter(k=>!p.includes(k)).map(slotName).join(', ')||'없음'}`:'';$('redoGo').disabled=!p.length||!$('redoText').value.trim();};
  redo.onclick=e=>{const b=e.target.closest('.pill');if(!b)return;b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');upd();};
  $('redoText').oninput=upd;
  $('redoGo').onclick=async()=>{const p=pick();$('redoGo').disabled=true;$('redoErr').textContent='';
    try{const r=await post('/api/plan/revise',{기획id:rec.기획id,안id:rec.안id,바꿀:p,유지:rec.시간칸.filter(k=>!p.includes(k)),요청:$('redoText').value.trim()});
      showProgress(r);watch(r.기획id);window.scrollTo({top:0,behavior:'smooth'});}
    catch(err){$('redoErr').textContent=err.message;upd();}};
}
function draw(stops){
  const tl=$('timeline');let lastDay=null;
  for(const s of stops){
    const cls=!s.좌표?'none':칸색(s);
    if(s.일차!==lastDay){tl.insertAdjacentHTML('beforeend',`<div class="daylabel">${esc(s.일차)}일차</div>`);lastDay=s.일차;}
    const link=s.지도링크?`<br><a target="_blank" rel="noopener" href="${esc(s.지도링크)}">이 위치를 카카오맵에서 보기 ↗</a>`:'';
    const name=stopName(s);
    tl.insertAdjacentHTML('beforeend',`<div class="stop"><div class="num ${cls}">${s.순번}</div><div><b>${esc(s.시각||'시각 미정')}</b> ${esc(name)}${name===slotName(s.시간칸)?'':` <small>· ${esc(slotName(s.시간칸))}</small>`}${link}</div></div>`);
  }
  $('mapbox').innerHTML=routeSvg(stops);
}
// 바탕 지도 없이 좌표만으로 그리는 동선 그림. 외부 프로그램·이미지를 불러오지 않는다.
function routeSvg(stops){
  const pts=stops.filter(s=>s.좌표);const none=stops.length-pts.length;
  if(pts.length<2)return `<div class="nomap"><div><b>지도 위치 정보는 추가 확인이 필요해요</b><p class="note">여행 순서와 시각은 시간표에서 확인할 수 있어요.</p></div></div>`;
  const W=600,H=460,P=48;
  const lat0=pts.reduce((a,s)=>a+s.좌표[0],0)/pts.length,kx=Math.cos(lat0*Math.PI/180);
  const raw=pts.map(s=>[s.좌표[1]*kx,-s.좌표[0]]),xs=raw.map(p=>p[0]),ys=raw.map(p=>p[1]);
  const minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);
  const span=Math.max(maxx-minx,maxy-miny,0.003),sc=Math.min(W-2*P,H-2*P)/span;
  const ox=(W-(maxx-minx)*sc)/2,oy=(H-(maxy-miny)*sc)/2,seen={};
  const at=pts.map((s,i)=>{let x=ox+(raw[i][0]-minx)*sc,y=oy+(raw[i][1]-miny)*sc;
    const key=Math.round(x/6)+','+Math.round(y/6);const k=seen[key]=(seen[key]||0)+1;if(k>1)y+=24*(k-1);return {s,x,y};});
  const mPerPx=111320/sc;const nice=[50,100,200,250,500,1000,2000,5000].find(m=>m/mPerPx>=70)||5000;
  const barPx=nice/mPerPx,barLabel=nice>=1000?(nice/1000)+'km':nice+'m';
  let lines='';
  for(const day of [...new Set(at.map(p=>p.s.일차))]){const d=at.filter(p=>p.s.일차===day);if(d.length<2)continue;
    lines+=`<polyline class="route ${day===2?'d2':''}" points="${d.map(p=>p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ')}"/>`;}
  const dots=at.map(({s,x,y})=>`<g class="pin ${칸색(s)}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><title>${esc(s.순번+'. '+s.표시명+' · '+s.일차+'일차 '+(s.시각||'시각 미정'))}</title><circle r="13"/><text dy="4.5">${s.순번}</text>${x>W*0.62?'<text class="lbl end" x="-17" dy="4">':'<text class="lbl" x="17" dy="4">'}${esc(s.표시명)}</text></g>`).join('');
  return `<div class="routemap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="코스 동선 그림"><text class="north" x="${W-26}" y="30">N ↑</text>${lines}${dots}
    <g transform="translate(20,${H-22})"><line class="bar" x1="0" y1="0" x2="${barPx.toFixed(1)}" y2="0"/><text class="barlbl" x="${(barPx/2).toFixed(1)}" y="-6">${barLabel}</text></g></svg>
    <p class="note">바탕 지도 없이 장소 위치만 그린 동선이에요. 선은 순서를 잇는 직선이며 실제 이동 경로가 아니에요.${none?` 좌표가 없는 장소 ${none}곳은 그림에서 빠졌어요.`:''}</p></div>`;
}

// ---------- 시작 ----------
$('newBtn').onclick=()=>{$('progress').hidden=!(last&&last.상태==='진행중');newForm();};
if($('savedCourses'))$('savedCourses').open=window.matchMedia('(min-width:901px)').matches;
(async()=>{
  const items=await loadList();
  let p=null;try{p=(await get('/api/plan/latest')).기획;}catch{}
  if(p&&p.상태==='진행중'){showProgress(p);watch(p.기획id);$('main').innerHTML='';return;}  // 새로고침해도 진행 상황을 이어서 보여 줌
  if(items.length)show(items[0].id,items[0].조건);else newForm();
})();

}
