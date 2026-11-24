// 담당자 화면: ① 조건 고르기 → ② AI 에이전트들이 코스를 만드는 모습 → ③ 코스 확인(동선·시간표).
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
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
    <form class="order" id="order">
      ${q('계절','계절')}${q('언어권','대상 언어권','여러 개 고를 수 있어요')}${q('지역','지역','여러 개 고를 수 있어요')}${q('체류기간','체류 기간')}
      <div class="sec">바라는 점 <span class="note">(선택 · 지키기 어려우면 AI가 이유를 남기고 조정할 수 있어요)</span></div>
      <label class="q"><span>목표</span><input name="목표" maxlength="300" placeholder="예: 당일 관광객을 저녁까지 머물게 하기"></label>
      <label class="q"><span>희망 사항<small>한 줄에 하나</small></span><textarea name="희망" rows="3" placeholder="예: 저녁은 평화시장 닭똥집골목에서&#10;야경을 넣고 싶어요"></textarea></label>
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
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>'];
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
  const 남은=(p.검사&&p.검사.남은문제)||[];
  box.innerHTML=`${guide(p.상태==='완료'?3:2)}<div class="top"><div><h2>${esc(head)}</h2><span class="note">${esc([c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · '))}${p.목표?' · 목표: '+esc(p.목표):''}</span></div>
    <div>${p.상태==='완료'&&p.시험id?`<button class="btn primary" id="seeNew">만든 코스 보기</button> `:''}${진행?'':'<button class="btn" id="closeP">닫기</button>'}</div></div>
    <div class="agents">${cards}</div>${msg}
    ${남은.length?`<details><summary>담당자가 확인할 것 ${남은.length}건</summary><ul>${남은.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:''}
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
async function show(id,cond){
  mark(id);const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  let s;try{s=await get('/api/plan/course?id='+encodeURIComponent(id));}catch(e){main.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return;}
  const k=s.조건||{};cond=cond||{};
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간,k.시작지점&&k.종료지점&&!(k.시작지점==='미확인'&&k.종료지점==='미확인')?`${k.시작지점} → ${k.종료지점}`:'시작·종료 장소 미정'].filter(Boolean);
  const days=s.출발가능요일?.length?`<p>출발 가능 요일: <span class="days">${esc(s.출발가능요일.join(' · '))}</span> <span class="note">(장소별 정기휴무로 계산)</span></p>`:'';
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
  <section class="card ai"><div class="aihead"><span class="aibadge">AI 코스 초안</span><strong>${s.코스있음?'담당자가 확인할 것':'아직 코스가 없어요'}</strong></div>${days}
    ${s.확인할것.length?`<ul>${s.확인할것.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="note">확인할 것이 없어요.</p>'}
    <p class="note">초안이에요. 확정은 담당자가 해요. A·B안 비교는 다음 단계에서 이 카드에 붙어요.</p></section>
  ${s.코스있음?`<section class="card"><div class="aihead"><strong>동선 · 시간표</strong>
    <span class="legend"><span><i class="lg-day"></i>낮</span><span><i class="lg-eve"></i>저녁</span><span><i class="lg-night"></i>밤·숙박</span></span></div>
    <div class="mapgrid"><div id="mapbox"></div><div class="timeline" id="timeline"></div></div></section>`:''}`;
  if(s.코스있음)draw(s.일정);
}
function draw(stops){
  const tl=$('timeline');let lastDay=null;
  for(const s of stops){
    const cls=!s.좌표?'none':칸색(s);
    if(s.일차!==lastDay){tl.insertAdjacentHTML('beforeend',`<div class="daylabel">${esc(s.일차)}일차</div>`);lastDay=s.일차;}
    const link=s.지도링크?`<br><a target="_blank" rel="noopener" href="${esc(s.지도링크)}">이 위치를 카카오맵에서 보기 ↗</a>`:'';
    tl.insertAdjacentHTML('beforeend',`<div class="stop"><div class="num ${cls}">${s.순번}</div><div><b>${esc(s.시각||'시각 미정')}</b> ${esc(s.표시명)} <small>· ${esc(s.시간칸)}${s.좌표?'':' · 좌표 미확인'}</small>${link}</div></div>`);
  }
  $('mapbox').innerHTML=routeSvg(stops);
}
// 바탕 지도 없이 좌표만으로 그리는 동선 그림. 외부 프로그램·이미지를 불러오지 않는다.
function routeSvg(stops){
  const pts=stops.filter(s=>s.좌표);const none=stops.length-pts.length;
  if(!pts.length)return `<div class="nomap">이 코스의 장소에 아직 좌표가 없어요.<br><span class="note">장소 CSV의 위도·경도를 채우면 여기에 동선이 그려져요.</span></div>`;
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
(async()=>{
  const items=await loadList();
  let p=null;try{p=(await get('/api/plan/latest')).기획;}catch{}
  if(p&&p.상태==='진행중'){showProgress(p);watch(p.기획id);$('main').innerHTML='';return;}  // 새로고침해도 진행 상황을 이어서 보여 줌
  if(items.length)show(items[0].id,items[0].조건);else newForm();
})();
