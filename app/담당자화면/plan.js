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
  function 위치안내(s){
    const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const lines=[s.위치설명,s.진입안내].filter(Boolean).map(x=>`<p class="note">${safe(x)}</p>`).join('');
    const proof=s.위치근거URL?`<a href="${safe(s.위치근거URL)}" target="_blank" rel="noopener">위치 근거</a>`:'';
    const map=s.지도링크?`<a href="${safe(s.지도링크)}" target="_blank" rel="noopener">카카오맵에서 보기 ↗</a>`:'';
    return lines||proof||map?`<details class="location-info"><summary>위치 정보</summary>${lines}<p>${[proof,map].filter(Boolean).join(' · ')}</p></details>`:'';
  }
  function 장소패널(s){
    const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const name=문장((s.표시명||s.장소명||'장소 미정').split(/\s+[—–]\s+/)[0]),info=s.장소안내||{};
    const candidates=s.식당후보||[];
    return `<button type="button" class="panel-close" data-place-close aria-label="장소 설명 닫기"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button><p class="eyebrow">${safe(s.일차)}일차 · ${safe(s.시각||'권장 시각 미정')}</p>
      <h2 tabindex="-1" id="placeTitle">${safe(name)}</h2><p>${safe(info.소개||'아직 장소 소개가 등록되지 않은 일정입니다.')}</p>
      ${info.이용시간||info.휴무?`<section class="place-facts"><h3>이용 참고 <small>보유 자료 기준</small></h3>${info.이용시간?`<p>이용시간 · ${safe(info.이용시간)}</p>`:''}${info.휴무?`<p>휴무 · ${safe(info.휴무)}</p>`:''}<p class="note">운영일·시간은 방문 전에 다시 확인해 주세요.${info.확인일?' 자료 확인일 '+safe(info.확인일):''}</p></section>`:''}
      ${info.주소?`<p class="note">${safe(info.주소)}</p>`:''}
      ${s.식사권역?`<section><h3>식당 후보</h3><p class="note">후보를 눌러도 방문이 확정되지 않습니다.</p>${candidates.length?candidates.map((c,i)=>`<button type="button" class="candidate-choice" data-explore-candidate="${i}">${safe(c.이름)} <small>미리보기${c.좌표?'':' · 위치 확인 중'}</small></button>`).join(''):'<p class="note">아직 등록된 식당 후보가 없습니다. 권역만 표시합니다.</p>'}<div id="candidatePreview" role="status"></div></section>`:''}
      ${!s.좌표&&!s.권역표시?.중심?'<p class="note">이 일정은 아직 지도 위치가 정해지지 않았습니다. 목록에는 계속 남겨 둡니다.</p>':''}
      ${위치안내(s)}${info.출처URL?`<p><a target="_blank" rel="noopener" href="${safe(info.출처URL)}">장소 안내 출처 ↗</a></p>`:''}`;
  }
  const 닭=`<svg class="drum" viewBox="0 0 24 24" aria-hidden="true"><path d="M14.6 3.2c3.4 0 6.2 2.7 6.2 6.1 0 3.2-2.4 5.6-5.5 6l-3.5 3.6a2 2 0 1 1-2.7 2.5 2 2 0 1 1-2.5-2.7l3.6-3.5c.4-3.1 2.8-5.5 6-5.5"/></svg>`;
  const 치킨장소=name=>/닭|치킨|치맥/.test(String(name||''));
  function 입장화면(){return `<section class="entry-screen"><div class="entry-copy"><h1>대구의 낮과 밤을,<br>하나의 여행으로.</h1><p class="entry-lead">관광객 유형과 조건을 고르면 AI가 낮 관광부터 저녁, 숙박까지 이어지는 코스 초안을 만들어요. 안을 비교하고 지도에서 동선을 확인한 뒤, 홍보물과 결재 파일까지 이어서 만들 수 있어요.</p><div class="entry-actions"><button class="btn primary big" id="entryNew">새 코스 기획하기</button></div><ol class="entry-flow" aria-label="기획 순서"><li><b>조건 고르기</b><small>계절·언어권·지역·체류 기간</small></li><li><b>AI 초안 받기</b><small>A안과 대안을 함께 만들어요</small></li><li><b>지도로 검토</b><small>동선·운영시간·이동 시간</small></li><li><b>홍보물·결재 파일</b><small>확정한 안으로 이어서</small></li></ol></div><section class="entry-recent" aria-labelledby="recentTitle"><div class="recent-head"><h2 id="recentTitle">이어서 보기</h2><button class="btn link" id="entrySaved">지난 코스 전체</button></div><div class="recent-list" id="recentList"><p class="empty">불러오는 중…</p></div><p class="note">저장된 코스와 지도는 AI 실행 없이 다시 볼 수 있어요.</p></section></section><section class="entry-day" aria-label="코스가 이어지는 하루"><div class="t-day"><span class="t-when">낮</span><b>중구·동구 관광</b><small>근대골목·서문시장 등 운영 중인 곳 위주</small><em class="chick-note">${닭}치킨은 장소 해설·이야기로 가볍게</em></div><div class="t-eve"><span class="t-when">저녁</span><b>대구 음식 중에서 고르기</b><span class="eve-opts"><i class="opt-chicken">${닭}평화시장 닭똥집골목</i><i>동성로 닭요리</i><i>다른 대구 음식</i></span></div><div class="t-night"><span class="t-when">밤</span><b>근거리는 귀가, 원거리는 하룻밤</b><small>야경 → 숙박 → 다음 날 오전 · 가족 코스는 술 없이</small></div></section>`;}
  const api={문장,짧게,상태,할일,보완요약,위치안내,장소패널,입장화면,닭,치킨장소};
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
let token=null,poll=null,tick=null,last=null,savedItems=null;
async function post(url,body){
  token=token||(await get('/api/session')).token;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':token},body:JSON.stringify(body)});
  const d=await r.json();if(!r.ok)throw new Error(d.오류||'요청 실패');return d;
}
const guide=n=>`<ol class="guide">${['조건 고르기','AI가 코스 만들기','코스 확인','홍보물 · 번역','최종 산출물'].map((t,i)=>`<li class="${i+1===n?'on':''}"><b>${i+1}</b>${t}</li>`).join('')}</ol>`;
const 칸색=s=>s.일차===2&&s.시간칸==='2일차오전'?'day':['저녁'].includes(s.시간칸)?'eve':['밤','숙박'].includes(s.시간칸)?'night':'day';

// ---------- 지난 코스 목록 ----------
async function loadList(select){
  const box=$('saved');
  try{
    const runs=await get('/api/runs');const items=[];
    const infos=await Promise.all(runs.map(run=>get('/api/course?id='+encodeURIComponent(run.id)).catch(()=>null)));  // 한 번에 받아 첫 화면 목록이 빨리 뜨게
    runs.forEach((run,i)=>{for(const t of infos[i]?.시험목록||[])if(t.시험id)items.push({id:t.시험id,조건:run.조건,시각:t.기록시각||''});});
    items.sort((a,b)=>b.시각.localeCompare(a.시각));savedItems=items;renderRecent();
    if(!items.length){box.innerHTML='<p class="empty">아직 만든 코스가 없어요.</p>';return items;}
    box.innerHTML='';
    for(const it of items){
      const c=it.조건||{};const b=document.createElement('button');b.dataset.id=it.id;
      b.innerHTML=`<b>${esc([c.계절,c.체류기간].filter(Boolean).join(' · '))}</b> ${esc([(c.언어권||[]).join('·'),(c.지역||[]).join('·')].filter(Boolean).join(' · '))}<br><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small>`;
      b.onclick=()=>{hideHistory();show(it.id,c);};box.append(b);
    }
    if(select)show(select,(items.find(x=>x.id===select)||{}).조건||{});
    return items;
  }catch(e){box.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return [];}
}
function renderRecent(){
  const box=$('recentList');if(!box||!savedItems)return;
  if(!savedItems.length){box.innerHTML='<p class="empty recent-empty">아직 만든 코스가 없어요. 첫 코스를 기획해 보세요.</p>';return;}
  box.innerHTML=savedItems.slice(0,4).map(it=>{const c=it.조건||{};return `<button type="button" class="recent-item stay-${c.체류기간==='당일'?'day':'night'}" data-id="${esc(it.id)}"><span class="recent-band" aria-hidden="true"></span><b>${esc([c.계절,c.체류기간].filter(Boolean).join(' · ')||'조건 미기록')}</b><span>${esc([(c.언어권||[]).join('·'),(c.지역||[]).join('·')].filter(Boolean).join(' · '))}</span><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small></button>`;}).join('');
  box.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>{const it=savedItems.find(x=>x.id===b.dataset.id);show(it.id,it.조건||{});});
}
function setView(v){document.body?.setAttribute?.('data-view',v);}
function mark(id){$('saved').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.id===id));}
function hideHistory(){const panel=$('historyPanel');if(panel)panel.hidden=true;$('historyBtn')?.setAttribute('aria-expanded','false');}
function showHistory(){const panel=$('historyPanel');if(!panel)return;panel.hidden=false;$('historyBtn').setAttribute('aria-expanded','true');$('historyClose').focus();}
function showLanding(){hideHistory();mark(null);setView('landing');$('progress').hidden=!(last&&last.상태==='진행중');$('main').innerHTML=기획표시.입장화면();$('entryNew').onclick=()=>newForm();$('entrySaved').onclick=showHistory;renderRecent();}

// ---------- ① 조건 고르기 (주문서) ----------
const 선택지={계절:['봄','여름','가을','겨울'],언어권:['영어권','일본어','중국어 간체','중국어 번체'],지역:['중구','동구'],체류기간:['당일','1박2일']};
const 여러개={언어권:1,지역:1};
function newForm(){
  hideHistory();
  mark(null);setView('form');
  const q=(name,label,help)=>`<div class="q"><span>${label}${help?`<small>${help}</small>`:''}</span><div class="pills" data-name="${name}">${선택지[name].map(v=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(v)}">${esc(v)}</button>`).join('')}</div></div>`;
  $('main').innerHTML=`<section class="card">${guide(1)}
    <h2>어떤 코스를 만들까요?</h2>
    <p class="lead">꼭 지킬 조건을 고르고, 바라는 점이 있으면 적어 주세요. AI 에이전트들이 자료 확인부터 코스 초안까지 이어서 만들어요.</p>
    <p class="note">고른 지역과 여행 조건 안에서 코스를 제안해요. 시작·종료 장소나 식사 방식이 미정이어도 초안부터 볼 수 있어요.</p>
    <form class="order order-layout" id="order"><div class="order-fields">
      ${q('계절','계절')}${q('언어권','대상 언어권','여러 개 고를 수 있어요')}${q('지역','지역','여러 개 고를 수 있어요')}${q('체류기간','체류 기간')}
      <div class="sec">바라는 점 <span class="note">(선택 · 지키기 어려우면 AI가 이유를 남기고 조정할 수 있어요)</span></div>
      <label class="q"><span>목표</span><input name="목표" maxlength="300" placeholder="예: 필수 대상은 일본인 커플, 중구에서 저녁과 숙박으로 연결"></label>
      <label class="q"><span>희망 사항<small>한 줄에 하나</small></span><textarea name="희망" rows="3" placeholder="예: 저녁 이후 야경을 넣고 싶어요&#10;이동을 줄이고 여유롭게 식사하고 싶어요"></textarea></label>
      </div><aside class="order-summary" aria-label="만들어질 코스 미리보기"><h3>만들어질 코스</h3><div class="sum-chips" id="sumChips"></div><ol class="sum-day" id="sumDay"></ol>
      <p class="agree">시작하면 중간 알림·경고는 기록에 남기고 <b>코스 초안까지 자동으로 진행</b>해요. 기관 데이터는 '없음'으로 진행하고, 홍보물과 최종 문서는 코스를 확인한 뒤 따로 만들어요.</p>
      ${last&&last.상태==='진행중'?'<p class="note">지금 만들고 있는 코스가 있어요. 한 번에 하나씩 만들어요. 끝난 뒤 시작해 주세요.</p>':''}
      <div class="go"><span class="note" id="need"></span><span class="err" id="newErr"></span><button class="btn primary big" id="newGo" type="submit" disabled>코스 만들기 시작</button></div></aside>
    </form></section>`;
  const f=$('order');
  const 값=()=>{const v={};for(const n in 선택지){const on=[...f.querySelectorAll(`[data-name="${n}"] [aria-pressed=true]`)].map(b=>b.dataset.v);v[n]=여러개[n]?on:on[0]||'';}return v;};
  const check=()=>{const v=값();const miss=Object.keys(선택지).filter(n=>!v[n]||!v[n].length).map(n=>({계절:'계절',언어권:'언어권',지역:'지역',체류기간:'체류 기간'}[n]));
    $('need').textContent=miss.length?`남은 것: ${miss.join(', ')}`:'모든 조건을 골랐어요.';$('newGo').disabled=miss.length>0;미리보기(v);};
  const 미리보기=v=>{
    const chips=[v.계절,(v.언어권||[]).join('·'),(v.지역||[]).join('·'),v.체류기간].filter(Boolean);
    $('sumChips').innerHTML=chips.length?chips.map(c=>`<span class="chip">${esc(c)}</span>`).join(''):'<span class="note">왼쪽에서 조건을 고르면 여기에 모여요.</span>';
    const 지역=(v.지역||[]).length?v.지역.join('·'):'선택한 지역';
    const 단계=v.체류기간==='당일'?[['day','낮',`${지역} 관광`],['eve','저녁','대구 음식 중 선택 · 닭요리 포함'],['home','이후','귀가']]
      :v.체류기간==='1박2일'?[['day','낮',`${지역} 관광`],['eve','저녁','대구 음식 중 선택 · 닭요리 포함'],['night','밤','야경 → 숙박'],['day2','둘째 날','오전 일정 후 귀가']]
      :[['day','낮','관광'],['eve','저녁','식사 선택'],['night','이후','체류 기간에 따라 달라져요']];
    $('sumDay').className='sum-day'+(v.체류기간?'':' is-empty');
    $('sumDay').innerHTML=단계.map(([k,t,d])=>`<li class="s-${k}"><span>${t}</span><p>${k==='eve'&&v.체류기간?기획표시.닭:''}${esc(d)}</p></li>`).join('');
  };
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
    ${msg}<div class="agents">${cards}</div>
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
  mark(id);setView('course');const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  try{const rec=await get('/api/plan/record?id='+encodeURIComponent(id)+(안?'&안='+안:'')+(버전?'&버전='+버전:''));if(rec.있음)return showRecord(id,cond||{},rec);}catch{}
  let s;try{s=await get('/api/plan/course?id='+encodeURIComponent(id));}catch(e){main.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return;}
  const k=s.조건||{};cond=cond||{};
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간,k.시작지점&&k.종료지점&&!(k.시작지점==='미확인'&&k.종료지점==='미확인')?`${k.시작지점} → ${k.종료지점}`:'시작·종료 장소 미정'].filter(Boolean);
  const days=s.출발가능요일?.length?`<p>출발 가능 요일: <span class="days">${esc(s.출발가능요일.join(' · '))}</span> <span class="note">(장소별 정기휴무로 계산)</span></p>`:'';
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
  <section class="card ai"><div class="aihead"><span class="aibadge">AI 코스 초안</span><strong>${s.코스있음?'담당자가 확인할 것':'아직 코스가 없어요'}</strong></div>${days}
    ${s.확인할것.length?`<ul>${s.확인할것.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="note">확인할 것이 없어요.</p>'}
    <p class="note">이전 방식으로 저장된 초안이에요. 이 기록에는 A·B 비교 정보가 없어요. 아래 시각은 추천 동선을 살펴보는 기준이며 실제 예약·운영시간을 확인해야 해요.</p></section>
  ${s.코스있음?`<section class="card map-launch"><div><h3>동선 · 시간표</h3><p class="note">큰 지도에서 방문 순서와 장소 설명을 살펴보세요.</p></div><button class="btn primary" id="openMap">지도 크게 보기 ↗</button></section>`:''}`;
  if(s.코스있음)$('openMap').onclick=()=>openMap(s.일정,{id,cond});
}
const 분류이름={AI수정:['AI가 고칠 것','시간 겹침·형식 오류처럼 코스가 틀린 것. 총괄이 코스 에이전트에게 고치게 해요. 남아 있으면 고치지 못한 것이에요.'],
  자료보완:['자료 보완','자료가 없어 생긴 것. 수집 에이전트가 저장소 자료에서 찾아요. 남아 있으면 못 찾은 것이에요.'],
  사람결정:['담당자가 정할 것','시작·종료, 2일차 오전, 식사 방식, 지키지 못한 희망처럼 사람이 정할 것이에요.']};
const 칸이름={낮:'낮',낮오후:'오후',점심:'점심',저녁:'저녁',밤:'밤',숙박:'숙박','2일차오전':'둘째 날 오전'};
function 시간표(일정){
  if(!일정.length)return '<div class="day-schedule"><p class="empty">아직 일정이 없어요.</p></div>';
  let day=null;const days=new Set(일정.map(x=>x.일차)).size;
  const rows=일정.map(x=>{const n=stopName(x),c=칸색(x);const head=days>1&&x.일차!==day?`<li class="ds-day">${esc(x.일차)}일차</li>`:'';day=x.일차;
    return head+`<li class="ds-row slot-${c}"><span class="ds-time">${esc(x.시각||'미정')}</span><span class="ds-dot" aria-hidden="true"></span><span class="ds-name">${기획표시.치킨장소(n)?`<em class="chick-stop" title="치킨·닭요리 요소">${기획표시.닭}${esc(n)}</em>`:esc(n)}<small>${esc(칸이름[x.시간칸]||x.시간칸||'')}</small></span></li>`;}).join('');
  return `<div class="day-schedule"><h3>하루 시간표 <span class="note">권장 순서·시각</span></h3><ol>${rows}</ol></div>`;
}
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
  const wish=!이전&&(안.희망반영||[]).length?`<section class="card request-card"><h3>요청을 이렇게 반영했어요</h3><ul class="wish">${안.희망반영.map(h=>{
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
    <section class="card ai recommendation"><div class="aihead"><span class="aibadge">코스 초안</span><h2>코스 제안</h2><span class="draft-badge">확정 전 초안</span>${s.코스있음?`<button class="btn primary compare-map-button" id="openMap" title="동선 · 시간표">지도 크게 보기 ↗</button>`:''}</div>
      <p class="lead">${정리.안.length>1?'요청을 바탕으로 만든 코스와 대안을 비교해 보세요.':'요청을 바탕으로 만든 코스예요. 동선과 일정을 먼저 살펴보세요.'}</p>
      <div class="tabs plan-choices">${tabs}</div>
      <div class="rec-split">${시간표(s.일정||[])}<div class="rec-side">
      ${이전?'<div class="review-status state-대기"><b>이전 수정본을 보고 있어요</b><p>최신 코스로 돌아가서 현재 검토 내용을 확인해 주세요.</p><button class="btn" id="latestPlan">최신 코스 보기</button></div>':''}
      <div class="review-status state-${상태.종류}" role="status"><b>${esc(상태.제목)}</b><p>${esc(상태.설명)}</p>${주요확인.length?`<ul>${주요확인.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:''}</div>
      ${s.출발가능요일?.length?`<p class="departure"><b>출발 요일 참고</b> ${esc(s.출발가능요일.join(' · '))}<span class="note">정기휴무 기준이에요. 운영 변경 여부는 출발 전 확인해 주세요.</span></p>`:''}
      ${부분}${alt}${required}</div></div></section>
    <section class="card freedom"><h3>어디까지 자유롭게 이용하나요?</h3><p>표시된 순서와 시각은 권장 일정이에요. 관광·식사는 장소의 운영시간 안에서 선택할 수 있도록 기획합니다.</p><p class="note">예약이나 이용권에 실제로 정해진 시간이 있다면 그 조건을 따라야 해요. 미정인 사용처·유효시간·포함 혜택은 아직 확정된 상품 조건이 아니에요. 집결·해산이나 숙소 예약을 먼저 입력할 필요는 없어요.</p></section>
    ${wish}
    <details class="card"><summary>코스 수정하기 · 바꾸고 싶은 부분이 있나요?</summary><p class="note">고른 일정만 다시 제안해요. 나머지 일정과 이전 초안은 보존해요.</p>
      <div class="pills" id="redo">${rec.시간칸.map(k=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(k)}">${esc(slotName(k))}</button>`).join('')}</div>
      <div class="redo-row"><input id="redoText" maxlength="300" placeholder="예: 낮은 유지하고 저녁만 설문 음식 후보로 바꿔 주세요"><button class="btn primary" id="redoGo" disabled>다시 만들기</button></div>
      <p class="note" id="keep"></p><p class="err" id="redoErr"></p></details>
    <details class="card technical"><summary>팀 검토용 상세 · 수정 이력과 검사 기록</summary><p class="note">${esc(rec.안id)}안은 ${rec.안id==='A'?'원래 요청으로 만든 코스':'구성을 조정한 대안'}이고, ${rec.버전}버전은 같은 코스를 ${rec.버전}번째로 작성한 기록이에요. 서로 다른 여행 상품 ${rec.버전}개를 뜻하지 않아요.</p>${vers}${검사}<p><a href="/admin/">서비스 제공자용 로그 보기 ↗</a></p></details>`;
  if(s.코스있음)$('openMap').onclick=()=>openMap(s.일정,{id,cond,rec});
  if(!이전&&globalThis.홍보화면)globalThis.홍보화면.붙이기(main,{id,cond,rec,돌아가기:()=>show(id,cond,rec.안id,rec.버전)});  // ④ 홍보물 · ⑤ 산출물
  if($('latestPlan'))$('latestPlan').onclick=()=>show(id,cond,rec.안id);
  main.querySelectorAll('.tab[data-plan]').forEach(b=>b.onclick=()=>show(id,cond,b.dataset.plan));
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
let mapController=null,mapVersion=0,explorerStops=[],selectedStop=null,returnFocus=null;
function closeMap(){
  const view=$('mapView');if(!view||view.hidden)return;
  mapVersion++;mapController?.destroy();mapController=null;view.hidden=true;setView('course');
  document.body.classList.remove('map-open');
  document.querySelector('.wrap').inert=false;document.querySelector('body > header').inert=false;
  (returnFocus?.isConnected?returnFocus:$('openMap'))?.focus();
}
function openMap(stops,context={}){
  let view=$('mapView');
  if(!view){
    view=document.createElement('section');view.id='mapView';view.className='map-explorer';view.hidden=true;
    view.setAttribute('role','dialog');view.setAttribute('aria-modal','true');view.setAttribute('aria-label','코스 지도 탐색');view.tabIndex=-1;
    document.body.append(view);
    view.addEventListener('keydown',e=>{
      if(e.key==='Escape'){e.preventDefault();closeMap();return;}
      if(e.key==='Tab'){
        const focusable=[...view.querySelectorAll('button,a,summary,[tabindex="0"]')].filter(x=>!x.disabled&&x.getClientRects().length);
        const first=focusable[0],last=focusable.at(-1);
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
      }
    });
  }
  if(view.hidden)returnFocus=document.activeElement;
  mapController?.destroy();mapController=null;selectedStop=null;
  explorerStops=stops.map((s,i)=>({...s,표시명:stopName(s),순번:s.순번??i+1}));
  const plans=context.rec?.정리?.안||[],current=context.rec?.안id;
  const tabs=plans.map(a=>`<button type="button" class="explorer-plan ${a.안id===current?'active':''}" aria-pressed="${a.안id===current}" data-explorer-plan="${esc(a.안id)}">${esc(a.안id)}안</button>`).join('');
  let day=null;const list=explorerStops.map((s,index)=>{
    const heading=day!==s.일차?`<h3 class="explorer-day">${esc(s.일차)}일차</h3>`:'';day=s.일차;
    const next=explorerStops[index+1],segment=next&&next.일차===s.일차?`<div class="stop-transfer"><span data-route-time="${s.순번}">경로 확인 중</span><button type="button" data-play-segment="${s.순번}" disabled aria-label="${esc(stopName(s))}에서 ${esc(stopName(next))}까지 구간 재생">구간 재생</button></div>`:'';
    return heading+`<button type="button" class="explorer-stop slot-${칸색(s)}" data-stop="${s.순번}" aria-pressed="false"><span class="stop-order">${s.순번}</span><span><small>${esc(s.시각||'시각 미정')}${칸이름[s.시간칸]?' · '+esc(칸이름[s.시간칸]):''}</small><b>${기획표시.치킨장소(stopName(s))?기획표시.닭:''}${esc(stopName(s))}</b></span></button>${segment}`;
  }).join('');
  view.innerHTML=`<header class="explorer-header"><button type="button" class="btn" id="backCompare">← 코스 비교</button><h1>${current?esc(current)+'안':'저장 코스'} · 지도 탐색</h1><nav aria-label="비교할 코스">${tabs}</nav>${plans.length&&!plans.some(a=>a.안id==='B')?'<span class="note">B안 아직 없음</span>':''}</header>
    <div class="explorer-body"><nav class="explorer-list" aria-label="방문 순서"><h2>방문 순서</h2>${list}</nav>
    <div class="explorer-map"><div id="mapbox"></div><p class="map-reference-note">시설·권역의 대표 위치 기준 · 도보 경로·시간은 지도 추정 · 실제 입구는 별도 확인</p></div>
    <aside class="place-panel" id="placePanel" aria-label="선택한 장소 설명" aria-live="polite" hidden></aside></div>`;
  view.hidden=false;view.classList.remove('place-open');document.body.classList.add('map-open');setView('map');
  document.querySelector('.wrap').inert=true;document.querySelector('body > header').inert=true;
  $('backCompare').onclick=closeMap;
  view.querySelectorAll('[data-stop]').forEach(button=>button.onclick=()=>selectStop(Number(button.dataset.stop)));
  view.querySelectorAll('[data-play-segment]').forEach(button=>button.onclick=()=>mapController?.playLeg?.(Number(button.dataset.playSegment)));
  view.querySelectorAll('[data-explorer-plan]').forEach(button=>button.onclick=async()=>{
    if(button.dataset.explorerPlan===current)return;
    button.disabled=true;const version=mapVersion;
    try{
      const rec=await get('/api/plan/record?id='+encodeURIComponent(context.id)+'&안='+encodeURIComponent(button.dataset.explorerPlan));
      if(view.hidden||mapVersion!==version)return;
      showRecord(context.id,context.cond||{},rec);openMap(rec.요약.일정,{...context,rec});
    }catch{button.disabled=false;button.textContent='불러오기 재시도';}
  });
  $('backCompare').focus();draw(explorerStops);
}
function selectStop(number,fromMap=false){
  const stop=explorerStops.find(s=>s.순번===number);if(!stop)return;
  selectedStop=number;
  const view=$('mapView'),panel=$('placePanel');view.classList.add('place-open');panel.hidden=false;
  panel.innerHTML=기획표시.장소패널(stop);
  view.querySelectorAll('[data-stop]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.stop)===number)));
  panel.querySelector('[data-place-close]').onclick=()=>{
    panel.hidden=true;view.classList.remove('place-open');view.querySelector(`[data-stop="${number}"]`)?.focus();
  };
  panel.querySelectorAll('[data-explore-candidate]').forEach(button=>button.onclick=()=>{const index=Number(button.dataset.exploreCandidate);showCandidate(number,index);mapController?.previewCandidate?.(number,index);});
  if(!fromMap)mapController?.selectStop?.(number,{notify:false});
}
function showCandidate(number,index){
  const stop=explorerStops.find(s=>s.순번===number),candidate=stop?.식당후보?.[index];if(!candidate)return;
  if(selectedStop!==number)selectStop(number,true);
  const panel=$('candidatePreview');if(panel)panel.innerHTML=`<p><b>${esc(candidate.이름)}</b></p><p class="note">후보 미리보기 · 방문 확정은 바뀌지 않습니다.${candidate.좌표?'':' 위치는 확인 중입니다.'}</p>`;
}
function draw(stops){
  const version=++mapVersion;mapController?.destroy();mapController=null;
  const box=$('mapbox');box.innerHTML='<p class="note">큰 지도를 불러오는 중…</p>';
  import('/plan/three-map.js').then(m=>{
    if(version!==mapVersion)return null;
    return m.mount(box,stops,{externalDetails:true,onSelect:(number,event)=>{
      selectStop(number,true);
      if(event?.playback){$('placePanel').hidden=true;$('mapView').classList.remove('place-open');}
    },onCandidate:showCandidate});
  }).then(controller=>{
    if(!controller)return;if(version!==mapVersion){controller.destroy();return;}
    mapController=controller;if(selectedStop!==null)controller.selectStop?.(selectedStop,{notify:false});
    for(const node of $('mapView').querySelectorAll('[data-route-time]')){
      const leg=controller.routes?.find(leg=>leg.from===Number(node.dataset.routeTime));node.textContent=leg?코스지도모델.timeLabel(leg.durationSeconds):'경로 미확인';
    }
    for(const button of $('mapView').querySelectorAll('[data-play-segment]'))button.disabled=!controller.routes?.some(leg=>leg.from===Number(button.dataset.playSegment));
  }).catch(()=>{if(version===mapVersion)box.innerHTML='<p class="note">지도를 불러오지 못했습니다. 왼쪽 일정과 장소 설명은 계속 볼 수 있습니다.</p>';});
}

// ---------- 시작 ----------
$('newBtn').onclick=()=>{$('progress').hidden=!(last&&last.상태==='진행중');newForm();};
$('historyBtn').onclick=()=>{$('historyPanel').hidden?showHistory():hideHistory();};
$('historyClose').onclick=()=>{hideHistory();$('historyBtn').focus();};
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('historyPanel').hidden){hideHistory();$('historyBtn').focus();}});
(async()=>{
  showLanding();
  const items=await loadList();
  let p=null;try{p=(await get('/api/plan/latest')).기획;}catch{}
  if(p&&p.상태==='진행중'){showProgress(p);watch(p.기획id);$('main').innerHTML='';return;}  // 새로고침해도 진행 상황을 이어서 보여 줌
})();

}
