// 담당자 화면 ④ 홍보물(4단계) · ⑤ 최종 산출물(5단계).
// 코스 화면 아래에 '다음 단계' 카드를 붙이고, 확인 → 홍보 초안 → 산출물 순서로 보여 준다.
// 원본 코스·검사 기록은 고치지 않는다. 확정한 안·버전과 홍보 디자인 설정만 보낸다.
(function(){
// 지침의 캐릭터 이름(포롱이=너구리, 여울이=족제비)이 바뀌어도 같은 그림을 고른다
const 캐릭터별칭={너구리:'너구리',포롱이:'너구리',raccoon:'너구리',족제비:'족제비',여울이:'족제비',weasel:'족제비'};
const 캐릭터=n=>캐릭터별칭[String(n??'').trim()]||null;
const 그림=n=>캐릭터(n)==='너구리'?'raccoon':'weasel';
function 재생성설정(p,ctx){
  const previous=ctx.이전확인||{};
  return {기본값:{...p.기본값},
    톤앤매너:previous.톤앤매너||'A+B',홍보물:previous.홍보물||p.선택지.홍보물.slice(0,2)};
}
function 확정요약(p){
  const e=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  return '<div class="course-card"><b>'+e(p.코스확정?.코스이름||p.기본값.코스이름)+'</b><p>'+e(p.안id)+'안 · '+e(p.버전)+'버전 · 확정한 코스를 그대로 사용해요.</p><details><summary>사용할 일정 보기 · 변경은 코스 화면에서</summary><ol>'+(p.코스요약||[]).map(r=>'<li>'+e(r.일차)+'일차 · '+e(r.시간칸)+' · '+e(r.장소명)+'</li>').join('')+'</ol></details></div>';
}
if(typeof module!=='undefined')module.exports={캐릭터,그림,재생성설정,확정요약};
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function get(url){const r=await fetch(url);const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오기 실패');return d;}
let token=null,poll=null;
async function post(url,body){
  token=token||(await get('/api/session')).token;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':token},body:JSON.stringify(body)});
  const d=await r.json();if(!r.ok)throw new Error(d.오류||'요청 실패');return d;
}
const 톤설명={A:['따뜻한 귀향 탐험','갈색·크림 계열 · 반가움과 호기심 · 낮 장면에 어울려요'],B:['별빛 밤 탐험','어두운 배경과 별빛 포인트 · 저녁·밤 체류를 강조해요'],
  C:['정보 안내형','흰 배경 · 읽기 쉬운 안내 · 지도·코스 카드에 어울려요'],'A+B':['낮은 귀향 · 밤은 별빛','시간 칸에 따라 낮은 A, 저녁·밤·숙박은 B로 나눠요']};
const 오전설명={후보일정추가:'후보 일정 추가',자유시간:'자유시간',종료장소로바로:'종료 장소로 바로 이동'};
const 상태말={진행중:'만드는 중',홍보완료:'홍보 초안 나옴',산출물완료:'최종 산출물 완성',실패:'멈춤',중단됨:'끊김'};
const guide=n=>`<ol class="guide">${['조건 고르기','AI가 코스 만들기','코스 확인','홍보물 · 번역','최종 산출물'].map((t,i)=>`<li class="${i+1===n?'on':''}"><b>${i+1}</b>${t}</li>`).join('')}</ol>`;
const text=v=>Array.isArray(v)?v.map(text).join(' / '):typeof v==='object'&&v?(v.안내?text(v.안내):Object.entries(v).map(([k,x])=>`${k}: ${text(x)}`).join(' / ')):String(v??'');
const factText=f=>{if(!f)return '';if(typeof f==='string')return f;if(Array.isArray(f))return f.map(factText).join(' · ');
  const ids=[].concat(f.출처ID||[]).join(', ');const r=[].concat(f.근거ID목록||f.근거ID||[]).join(', ');return [ids,r].filter(Boolean).join(' · ');};

// ---------- 코스 화면에 붙는 '다음 단계' 카드 ----------
async function 붙이기(main,ctx){
  const sec=document.createElement('section');sec.className='card next-step';sec.id='promoEntry';
  const tech=main.querySelector('.technical');tech?main.insertBefore(sec,tech):main.append(sec);
  sec.innerHTML=`<div class="next-head"><div><span class="step-no">다음 단계</span><h3>코스 확정 → 홍보물 · 랜딩페이지</h3>
    <p class="note">이 코스로 정하면 홍보 검토 에이전트가 장면별 문구·번역 초안·캐릭터 시안을 만들고, 이어서 결재 파일·제안서·홍보물 묶음을 만들어요.</p></div>
    <button class="btn primary" id="promoGo">${esc(ctx.rec.안id)}안으로 홍보 준비</button></div><div id="promoList"></div>`;
  $('promoGo').onclick=()=>코스확정화면(ctx,()=>확인화면(ctx));
  try{const {목록}=await get('/api/promo/list?id='+encodeURIComponent(ctx.rec.기획id));
    if(목록.length)$('promoList').innerHTML=`<p class="note">이 기획에서 만든 홍보물</p><div class="promo-runs">${목록.map(x=>`<button class="promo-run" data-id="${esc(x.홍보id)}"><b>${esc(x.코스이름||'코스 이름 미정')}</b> <span class="st st-${esc(x.상태)}">${esc(상태말[x.상태]||x.상태)}</span><br><small>${esc(x.안id)}안 ${esc(x.버전)}버전 · ${esc((x.시작시각||'').replace('T',' ').slice(0,16))}</small></button>`).join('')}</div>`;
    sec.querySelectorAll('.promo-run').forEach(b=>b.onclick=()=>결과화면(b.dataset.id,ctx));
  }catch{}
}

async function 코스확정화면(ctx,다음){
  const main=$('main');let p;
  try{p=await get(`/api/promo/prepare?id=${encodeURIComponent(ctx.id)}&안=${encodeURIComponent(ctx.rec.안id)}&버전=${ctx.rec.버전}`);}
  catch(e){main.innerHTML=`<p class="err">${esc(e.message)}</p>`;return;}
  if(p.코스확정)return 다음();
  main.innerHTML=`<section class="card promo-form">${guide(3)}<button class="btn link" id="backConfirm">← 코스로 돌아가기</button><h2>홍보에 쓸 코스를 확정해 주세요</h2><p>${esc(p.안id)}안 · ${esc(p.버전)}버전의 일정과 확인 사항을 검토해 주세요. 제목은 자동으로 제안하며 원할 때 바꿀 수 있어요.</p><form id="courseConfirmForm" class="order"><div class="q"><label for="confirmName">코스 제목 (선택)</label><input id="confirmName" name="코스이름" maxlength="40" value="${esc(p.기본값.코스이름||'')}" placeholder="이 코스를 소개할 이름을 입력하세요"></div><p class="note">홍보에 사용할 안·버전을 저장합니다. 제목을 비우면 자동 제목을 사용해요. 운영·번역 검토는 계속 필요하며 코스를 수정하면 다시 확정해야 합니다.</p><div class="go"><span class="err" id="confirmErr" role="alert"></span><button class="btn primary big" id="confirmGo" type="submit">이 코스로 확정 · 홍보 준비</button></div></form></section>`;
  $('backConfirm').onclick=()=>ctx.돌아가기();
  $('courseConfirmForm').onsubmit=async e=>{e.preventDefault();$('confirmGo').disabled=true;$('confirmErr').textContent='';
    try{await post('/api/plan/confirm',{시험id:ctx.id,안id:ctx.rec.안id,버전:ctx.rec.버전,코스이름:e.target.코스이름.value.trim(),확인동의:true});await 다음();}
    catch(err){$('confirmErr').textContent=err.message;$('confirmGo').disabled=false;}
  };
}

// ---------- ④-1 담당자 확인 ----------
async function 확인화면(ctx){
  const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  let p;try{p=await get(`/api/promo/prepare?id=${encodeURIComponent(ctx.id)}&안=${encodeURIComponent(ctx.rec.안id)}&버전=${ctx.rec.버전}`);}
  catch(e){main.innerHTML=`<p class="err">${esc(e.message)}</p>`;return;}
  if(!p.코스확정)return 코스확정화면(ctx,()=>확인화면(ctx));
  const setting=재생성설정(p,ctx);
  const 톤=Object.keys(톤설명).map(k=>`<label class="tone tone-${k.replace('+','')}"><input type="radio" name="톤앤매너" value="${esc(k)}" ${k===setting.톤앤매너?'checked':''}><b>${esc(톤설명[k][0])}</b><small>${esc(톤설명[k][1])}</small></label>`).join('');
  main.innerHTML=`<section class="card promo-form">${guide(4)}
    <button class="btn link" id="backCourse">← 코스로 돌아가기</button>
    <h2>홍보물 디자인을 골라 주세요</h2>
    <p class="lead">확정한 코스로 문구와 번역을 만들어요. 일정은 다시 입력하지 않습니다.</p>
    ${확정요약(p)}
    <form id="promoForm" class="order">
      <div class="q"><span>톤앤매너</span><div class="tones">${톤}</div></div>
      <div class="q"><span>만들 홍보물<small>여러 개 고를 수 있어요</small></span><div class="pills" data-name="홍보물" data-multi="1">${p.선택지.홍보물.map(v=>`<button type="button" class="pill" aria-pressed="${setting.홍보물.includes(v)}" data-v="${esc(v)}">${esc(v)}</button>`).join('')}</div></div>
      <div class="q"><span>번역 언어</span><p class="langs">${p.언어.length?p.언어.map(esc).join(' · '):'조건에 언어권이 없어 번역하지 않아요'} <span class="note">(1단계 조건 그대로)</span></p></div>
      <div class="go"><span class="err" id="promoErr"></span><button class="btn primary big" id="promoStart" type="submit">홍보물 · 번역 만들기</button></div>
    </form><p class="note">홍보 검토 에이전트(AI)가 3~6분쯤 걸려요. 창을 닫아도 이어서 볼 수 있어요.</p></section>`;
  $('backCourse').onclick=()=>ctx.돌아가기();
  const f=$('promoForm');
  f.querySelectorAll('.pills').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('.pill');if(!b)return;
    if(!g.dataset.multi)g.querySelectorAll('.pill').forEach(x=>x!==b&&x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');}));
  const pick=n=>[...f.querySelectorAll(`[data-name="${n}"] [aria-pressed=true]`)].map(b=>b.dataset.v);
  f.onsubmit=async e=>{e.preventDefault();$('promoErr').textContent='';$('promoStart').disabled=true;
    try{const r=await post('/api/promo/start',{시험id:ctx.id,안id:ctx.rec.안id,버전:p.버전,톤앤매너:f.톤앤매너.value,홍보물:pick('홍보물')});
      결과화면(r.홍보id,ctx);}
    catch(err){$('promoErr').textContent=err.message;$('promoStart').disabled=false;}};
}

// ---------- ④-2 진행 · 홍보 결과 · ⑤ 산출물 ----------
async function 결과화면(홍보id,ctx){
  clearInterval(poll);
  const main=$('main');
  let r;try{r=await get('/api/promo/result?id='+encodeURIComponent(홍보id));}catch(e){main.innerHTML=`<p class="err">${esc(e.message)}</p>`;return;}
  const 진행=r.진행;
  if(진행.상태==='진행중'){진행화면(r,ctx);poll=setInterval(async()=>{try{const n=await get('/api/promo/result?id='+encodeURIComponent(홍보id));
    if(n.진행.상태!=='진행중'){clearInterval(poll);결과화면(홍보id,ctx);}else 진행화면(n,ctx);}catch{clearInterval(poll);}},3000);return;}
  if(!r.홍보){main.innerHTML=`<section class="card">${guide(4)}<button class="btn link" id="backCourse">← 코스로 돌아가기</button><h2>홍보물을 만들지 못했어요</h2><p class="err">${esc(진행.안내)}</p><button class="btn primary" id="retry">다시 만들기</button></section>`;
    $('backCourse').onclick=()=>ctx.돌아가기();$('retry').onclick=()=>확인화면({...ctx,id:진행.시험id,
      rec:{...ctx.rec,안id:진행.안id,버전:r.현재코스버전}});return;}
  홍보화면(홍보id,r,ctx);
}
function 진행화면(r,ctx){
  const p=r.진행;const since=p.일하는중?.시작;
  $('main').innerHTML=`<section class="card">${guide(4)}<button class="btn link" id="backCourse">← 코스로 돌아가기</button><h2>홍보물을 만들고 있어요</h2>
    <div class="working">${esc(p.안내)}${since?` <span class="note">· 시작 ${esc(since.slice(11,16))}</span>`:''}</div>
    <div class="agents four">${p.단계.map(s=>`<div class="agent ${({진행중:'now',완료:'done',실패:'fail'})[s.상태]||''}"><span class="tag">${s.AI?'AI':s.에이전트==='담당자'?'사람':'코드'}</span><b>${esc(s.에이전트)}</b><p>${esc(s.하는일)}</p><div class="st">${esc(({진행중:'일하는 중',완료:'완료',실패:'멈춤'})[s.상태]||'차례 기다리는 중')}</div></div>`).join('')}</div>
    <p class="note">검사에 걸리면 문제를 알려 한 번 더 고쳐 써요. 번역은 모두 AI 초안이고 원어민 검토가 따로 필요해요.</p></section>`;
  $('backCourse').onclick=()=>{clearInterval(poll);ctx.돌아가기();};
}
function 장면카드(c,시안,칸,번역,lang,톤){
  const 주연=캐릭터(시안&&시안.주연)||'동등';const 밤=['저녁','밤','숙박'].includes(칸?.시간칸);
  const cls=톤==='B'||(톤==='A+B'&&밤)?'night':'';
  const img=(n,k)=>`<img class="${k}" src="/plan/characters/promo/${그림(n)}-front.png" alt="${n}">`;
  const chars=주연==='너구리'?img('너구리','lead')+img('족제비','side'):주연==='족제비'?img('족제비','lead')+img('너구리','side'):img('너구리','both r')+img('족제비','both w');
  const tr=lang!=='한국어'?번역.find(t=>t.언어===lang):null;
  const bubble=c.말풍선&&typeof c.말풍선==='object'?Object.entries(c.말풍선).filter(([,v])=>v).map(([k,v])=>`<div class="bubble b-${캐릭터(k)==='너구리'?'r':'w'}"><b>${esc(k)}</b>${esc(v)}</div>`).join(''):'';
  return `<article class="scene ${cls}"><div class="chars">${chars}</div><div class="scene-body">
    <div class="tags"><span>${esc(c.장면ID)}</span><span>${esc(칸?.시간칸||'')}${칸?.시각?' · 약 '+esc(칸.시각):''}</span><span>${esc((칸?.장소명||'').replace(/\s*\(.*?\)/g,''))}</span></div>
    ${tr?(()=>{const m=String(tr.번역||'').match(/^\s*[【\[][^】\]]+[】\]]\s*([\s\S]*?)\s*[【\[][^】\]]+[】\]]\s*([\s\S]*)$/);const l=lang==='일본어'?'ja':lang==='영어권'||lang==='영어'?'en':'zh';return m?`<h4 lang="${l}">${esc(m[1])}</h4><p lang="${l}">${esc(m[2])}</p>`:`<h4 lang="${l}">${esc(tr.번역)}</h4>`;})()+`<p class="note">역번역(참고): ${esc(tr.역번역||'')} · <b>${esc(tr.상태||'AI 초안')}</b></p>`
      :tr===undefined&&lang!=='한국어'?`<p class="warn">이 장면의 ${esc(lang)} 번역이 없어요.</p>`:`<h4>${esc(c.제목)}</h4><p>${esc(c.본문)}</p>${bubble}`}
    <p class="meta">사실 근거 ${esc(factText(c.사실근거))||'—'} · 경고 <span class="${c.경고&&c.경고!=='없음'?'warn':''}">${esc(text(c.경고)||'없음')}</span> · 주연 ${esc(주연)} · ${esc(시안?.배치세트||'')} · ${esc(시안?.포즈||'')}</p></div></article>`;
}
function 홍보화면(홍보id,r,ctx){
  const h=r.홍보,확인=r.확인||{},card=h.코스카드||{};const 톤=확인.톤앤매너||'A';
  const 칸=Object.fromEntries((r.칸||[]).map(x=>[(x.안||'공통')+'|'+x.칸ID,x]));
  const 시안=Object.fromEntries(((h.시안||{}).장면별||[]).map(x=>[(x.안||'공통')+'|'+x.장면ID,x]));
  const langs=['한국어',...new Set((h.번역목록||[]).map(t=>t.언어))];
  const 검사=(r.검사?.검사결과||[]).filter(x=>x!=='통과');
  const 필터=h.표현필터||[];const 산=r.산출물;
  const render=lang=>(h.문구목록||[]).map(c=>{const k=(c.안||'공통')+'|'+c.장면ID;return 장면카드(c,시안[k],칸[k],(h.번역목록||[]).filter(t=>(t.안||'공통')+'|'+t.장면ID===k),lang,톤);}).join('');
  $('main').innerHTML=`<section class="card promo-result">${guide(산?5:4)}<button class="btn link" id="backCourse">← 코스로 돌아가기</button>
    ${r.다시확인필요?`<p class="warn" role="alert">${esc(r.진행.재확인안내)}</p>`:''}
    <div class="aihead"><span class="aibadge">홍보 초안</span><h2>${esc(card.코스이름&&card.코스이름!=='미정'?card.코스이름:(확인.코스이름||'코스 이름 미정'))}</h2><span class="draft-badge">번역 AI 초안 · 검토 전</span></div>
    <form id="resultNameForm" class="name-confirm"><label>코스 제목 (선택) <input name="코스이름" maxlength="40" value="${esc(확인.코스이름||'')}" placeholder="홍보물과 랜딩에 쓸 이름"></label><button class="btn" type="submit" ${r.다시확인필요?'disabled':''}>이 코스로 확정 · 제목 적용</button><span class="err" id="nameErr" role="alert"></span><p class="note">${r.코스확정?`${esc(r.코스확정.안id)}안 ${esc(r.코스확정.버전)}버전 · 홍보용 코스 확정됨`:'이 코스로 확정하면 홍보물과 랜딩에 반영됩니다. 제목은 선택 입력입니다.'} · 운영·번역 검토와 구분합니다.</p></form>
    <div class="course-card t-${esc(톤.replace('+',''))}"><p class="who">${esc(text(card.대상문장))}</p><p class="flow">${esc(text(card.한눈에))}</p><p><b>식사</b> 식사는 개별 선택·개별 결제입니다.</p>${(()=>{const w=Array.isArray(card.남은경고)?card.남은경고:card.남은경고&&card.남은경고!=='없음'?[card.남은경고]:[];
      return w.length?`<details class="card-warn"><summary><b>남은 경고 ${w.length}건</b> · 담당자 검토용 (펼쳐 보기)</summary><ul>${w.map(x=>`<li>${esc(text(x))}</li>`).join('')}</ul></details>`:'<p><b>남은 경고</b> 없음</p>';})()}</div>
    ${검사.length?`<details class="check-box" open><summary>검사에서 남은 문제 ${검사.length}건 · 담당자 검토용</summary><ul>${검사.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:'<p class="ok-line">앱 검사 통과 · 장면 ID·후보 식당·용어집 표기·출처 ID 기준 (번역의 자연스러움은 사람이 검토해요)</p>'}
    ${r.디자인?`<section class="design-preview"><h3>이 코스로 만든 홍보물 디자인</h3><p class="note">홍보 검토 에이전트의 문구를 최신 시안에 배치했습니다. QR은 이 홍보물의 코스 페이지로 연결됩니다.</p><div class="design-actions"><a class="btn" href="${esc(r.디자인.미리보기)}" target="_blank" rel="noopener">디자인 크게 보기 · 인쇄</a><a class="btn primary" href="${esc(r.디자인.다운로드)}" download>홍보물 내려받기 (ZIP)</a><a class="btn" href="${esc(r.디자인.랜딩)}" target="_blank" rel="noopener">QR 코스 페이지</a></div><iframe title="실제 코스 홍보물 디자인" src="${esc(r.디자인.미리보기)}" loading="lazy"></iframe></section>`:''}
    <details class="check-box" id="reviewNotes"><summary>담당자 검토 사항 · 공개에서 제외되는 안내</summary><p class="note">아래 내용은 공개 화면과 제출 파일에 넣지 않습니다. 제외가 적절한지 확인하고 필요한 내용은 코스 또는 문구를 수정해 주세요. 제외는 확인 완료를 뜻하지 않습니다.</p><ul>${(r.검토사항||[]).map(w=>`<li>${esc(w.경고)} · ${esc(w.대상)}</li>`).join('')}</ul><h4>공개에서 제외한 안내</h4><ul>${(r.공개제외||[]).map(w=>`<li>${esc(w)}</li>`).join('')||'<li>없음</li>'}</ul></details>
    <div class="lang-tabs" role="tablist">${langs.map((l,i)=>`<button role="tab" class="pill" aria-pressed="${i===0}" data-lang="${esc(l)}">${esc(l)}</button>`).join('')}</div>
    <details class="check-box"><summary>담당자용 문구·번역 원문과 근거 검토</summary><div class="scenes" id="scenes">${render('한국어')}</div></details>
    <h3>장면 → 홍보물</h3><table class="tbl"><thead><tr><th>장면</th><th>장소</th><th>홍보물</th><th>상태</th></tr></thead><tbody>${(h.대응표||[]).map(d=>`<tr><td>${esc(d.장면ID)}</td><td>${esc(d.장소)}</td><td>${esc(text(d.홍보물))}</td><td>${esc(d.상태)}</td></tr>`).join('')}</tbody></table>
    </section>
    <section class="card deliver">${guide(5)}<h2>최종 산출물</h2>
    ${산?`<div class="docs">${[['결재','결재 파일','기관 내부 보고 · 코스·추진 내용·결재란'],['제안서','제안서','여행사·운영 주체 후보용 · 코스·협력 제안'],['홍보물','홍보물 묶음','코스 카드·장면 시안·언어별 문구표']].map(([k,t,s])=>`<a class="doc" href="${esc(산.문서[k])}" target="_blank" rel="noopener"><b>${t}</b><small>${s}</small><span>열기 · PDF로 저장 ↗</span></a>`).join('')}</div>
      <h3>세 파일 대조</h3><table class="tbl"><thead><tr><th>항목</th><th>결과</th><th>다른 곳</th></tr></thead><tbody>${산.대조.항목.map(x=>`<tr class="r-${esc(x.결과)}"><td>${esc(x.항목)}</td><td>${esc(x.결과)}</td><td>${esc(x.다른곳)}</td></tr>`).join('')}</tbody></table>
      <p class="note">검토 기록은 담당자 화면에 보관하고 제출 파일에는 넣지 않아요. 만든 시각 ${esc((산.만든시각||'').replace('T',' ').slice(0,16))}. 변경한 내용이 있으면 아래에서 파일을 갱신하세요. AI는 실행하지 않아요.</p>`:'<p class="lead">문구·번역과 수정이 필요한 표현을 검토한 뒤 공개 미리보기를 확인하세요. 최종 파일은 새 AI 실행 없이 검토한 내용을 문서로 묶어요.</p>'}
    <form id="deliverForm" class="order">
      ${필터.length?`<div class="sec">수정이 필요한 홍보 표현</div><table class="tbl"><thead><tr><th>장면</th><th>표현</th><th>종류</th><th>처리</th></tr></thead><tbody>${필터.map((f,i)=>`<tr><td>${esc(f.장면ID)}</td><td>${esc(f.표현)}</td><td>${esc(f.종류)}</td><td><select data-key="${esc(r.필터키[i])}" aria-label="${esc(f.표현)} 처리"><option value="미처리">미처리</option><option value="그대로둠">근거 확인 · 사용</option><option value="고침필요">수정 필요</option></select></td></tr>`).join('')}</tbody></table><p class="note">최상급·운영시간·제공 서비스처럼 근거 확인이 필요한 표현입니다. 미처리 또는 수정 필요가 있으면 파일을 만들 수 없어요. 근거를 확인한 표현만 사용으로 결정하세요.</p>`:'<p class="note">수정이 필요한 홍보 표현이 없어요.</p>'}
      <div class="q"><span>제안서 받는 쪽<small>3단계 운영 주체 후보</small></span><select name="받는쪽"><option value="">[담당자 기입]으로 비워 두기</option>${(r.받는쪽후보||[]).map(x=>`<option>${esc(x)}</option>`).join('')}</select></div>
      <label class="agree check"><input type="checkbox" name="홍보확인"> 문구·번역과 공개에서 제외되는 안내를 검토했어요. 내부 검토 기록은 별도로 보관돼요.</label>
      <div class="go"><span class="err" id="deliverErr"></span><button class="btn link" type="button" id="remake">문구·번역 새로 생성</button><button class="btn primary big" id="deliverGo" type="submit" ${r.다시확인필요||!r.코스확정?'disabled':''}>${r.다시확인필요?'최신 코스로 홍보물 재작성 필요':!r.코스확정?'위에서 사용할 코스 확정 필요':산?'변경사항으로 파일 갱신':'결재 파일 · 제안서 · 홍보물 묶음 만들기'}</button></div>
    </form></section>`;
  $('backCourse').onclick=()=>ctx.돌아가기();$('remake').onclick=()=>확인화면({...ctx,id:r.진행.시험id,
    rec:{...ctx.rec,안id:r.진행.안id,버전:r.현재코스버전},이전확인:r.확인,이전버전:r.진행.버전});
  document.querySelectorAll('.lang-tabs .pill').forEach(b=>b.onclick=()=>{document.querySelectorAll('.lang-tabs .pill').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('scenes').innerHTML=render(b.dataset.lang);const frame=document.querySelector('.design-preview iframe');if(frame&&r.디자인)frame.src=r.디자인.미리보기+'&lang='+encodeURIComponent(b.dataset.lang);});
  const f=$('deliverForm');
  for(const sel of f.querySelectorAll('select[data-key]'))sel.value=r.산출물선택?.표현처리?.[sel.dataset.key]||'미처리';
  f.받는쪽.value=r.산출물선택?.받는쪽||'';
  $('resultNameForm').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;$('nameErr').textContent='';
    try{await post('/api/plan/confirm',{시험id:r.진행.시험id,안id:r.진행.안id,버전:r.진행.버전,코스이름:e.target.코스이름.value.trim(),확인동의:true});await 결과화면(홍보id,ctx);}
    catch(err){$('nameErr').textContent=err.message;button.disabled=false;}
  };
  f.onsubmit=async e=>{e.preventDefault();$('deliverErr').textContent='';
    if(!f.홍보확인.checked){$('deliverErr').textContent='문구·번역과 공개 제외 안내를 먼저 검토해 주세요.';return;}
    if([...f.querySelectorAll('select[data-key]')].some(x=>x.value!=='그대로둠')){$('deliverErr').textContent='수정이 필요한 홍보 표현을 먼저 처리해 주세요.';return;}
    if(!window.confirm('최종 파일을 만들까요?\n선택한 코스와 문구를 사용하고 내부 경고·검토 기록은 파일에서 제외합니다.\n공개에서 제외한 안내 '+(r.공개제외||[]).length+'건을 검토했는지 확인해 주세요.\n식사는 개별 선택·개별 결제이며 새 AI 실행은 없습니다.'))return;
    $('deliverGo').disabled=true;
    const 처리={};f.querySelectorAll('select[data-key]').forEach(s=>처리[s.dataset.key]=s.value);
    try{await post('/api/promo/deliver',{홍보id,홍보확인:f.홍보확인.checked,표현처리:처리,받는쪽:f.받는쪽.value});
      await 결과화면(홍보id,ctx);document.querySelector('.deliver')?.scrollIntoView({behavior:'smooth'});}
    catch(err){$('deliverErr').textContent=err.message;$('deliverGo').disabled=false;}};
}
window.홍보화면={붙이기,결과화면,확인화면};
})();
