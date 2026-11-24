// 담당자 화면: 저장된 코스를 지도·시간표로 보여 준다. 읽기 전용, AI 호출 없음.
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function get(url){const r=await fetch(url);const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오기 실패');return d;}

async function loadList(){
  const box=$('saved');
  try{
    const runs=await get('/api/runs');const items=[];
    for(const run of runs){
      let info;try{info=await get('/api/course?id='+encodeURIComponent(run.id));}catch{continue;}
      for(const t of info.시험목록||[])if(t.시험id)items.push({id:t.시험id,조건:run.조건,시각:t.기록시각||''});
    }
    items.sort((a,b)=>b.시각.localeCompare(a.시각));
    if(!items.length){box.innerHTML='<p class="empty">저장된 코스가 없습니다.</p>';return;}
    box.innerHTML='';
    items.forEach((it,i)=>{
      const c=it.조건||{};const b=document.createElement('button');
      b.innerHTML=`${esc([c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · '))}<br><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small>`;
      b.onclick=()=>{box.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');show(it.id,c);};
      box.append(b);if(i===0)b.click();
    });
  }catch(e){box.innerHTML=`<p class="empty">${esc(e.message)}</p>`;}
}

async function show(id,cond){
  const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  let s;try{s=await get('/api/plan/course?id='+encodeURIComponent(id));}catch(e){main.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return;}
  const k=s.조건||{};
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간,k.시작지점&&k.종료지점?`${k.시작지점} → ${k.종료지점}`:''].filter(Boolean);
  const days=s.출발가능요일?.length?`<p>출발 가능 요일: <span class="days">${esc(s.출발가능요일.join(' · '))}</span> <span class="note">(장소별 정기휴무로 계산)</span></p>`:'';
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
  <section class="card ai"><div class="aihead"><span class="aibadge">AI 코스</span><strong>${s.코스있음?'이 코스에서 확인할 것':'아직 코스가 없어요'}</strong></div>${days}
    ${s.확인할것.length?`<ul>${s.확인할것.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="note">확인할 것이 없습니다.</p>'}
    <p class="note">A·B안 추천과 판단 이유는 다음 단계에서 이 카드에 표시됩니다.</p></section>
  ${s.코스있음?`<section class="card"><div class="aihead"><strong>동선 · 시간표</strong></div>
    <div class="mapgrid"><div id="mapbox"></div><div class="timeline" id="timeline"></div></div></section>`:''}`;
  if(s.코스있음)draw(s.일정);
}

function draw(stops){
  const tl=$('timeline');let lastDay=null;
  for(const s of stops){
    const meal=s.표시명.startsWith('자유식')||['점심','저녁'].includes(s.시간칸);
    const cls=!s.좌표?'none':s.일차===2?'d2':meal?'meal':'';
    if(s.일차!==lastDay){tl.insertAdjacentHTML('beforeend',`<div class="daylabel">${esc(s.일차)}일차</div>`);lastDay=s.일차;}
    const link=s.지도링크?`<br><a target="_blank" rel="noopener" href="${esc(s.지도링크)}">이 위치를 카카오맵에서 보기 ↗</a>`:'';
    tl.insertAdjacentHTML('beforeend',`<div class="stop" data-n="${s.순번}"><div class="num ${cls}">${s.순번}</div><div><b>${esc(s.시각||'시각 미정')}</b> ${esc(s.표시명)} <small>· ${esc(s.시간칸)}${s.좌표?'':' · 좌표 미확인'}</small>${link}</div></div>`);
  }
  $('mapbox').innerHTML=routeSvg(stops);
}

// 바탕 지도 없이 좌표만으로 그리는 동선 그림. 외부 프로그램·이미지를 불러오지 않는다.
function routeSvg(stops){
  const pts=stops.filter(s=>s.좌표);
  const none=stops.length-pts.length;
  if(!pts.length)return `<div class="nomap">이 코스의 장소에 아직 좌표가 없습니다.<br><span class="note">장소 CSV의 위도·경도를 채우면 여기에 동선이 그려집니다.</span></div>`;
  const W=600,H=460,P=48;
  const lat0=pts.reduce((a,s)=>a+s.좌표[0],0)/pts.length,kx=Math.cos(lat0*Math.PI/180);
  const xy=s=>[s.좌표[1]*kx,-s.좌표[0]];  // 경도는 위도에 맞춰 줄여 실제 비율로
  const raw=pts.map(xy),xs=raw.map(p=>p[0]),ys=raw.map(p=>p[1]);
  const minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);
  const span=Math.max(maxx-minx,maxy-miny,0.003);  // 한 곳뿐이어도 300m 남짓 범위로
  const sc=Math.min((W-2*P),(H-2*P))/span;
  const ox=(W-(maxx-minx)*sc)/2,oy=(H-(maxy-miny)*sc)/2;
  const seen={};
  const at=pts.map((s,i)=>{let x=ox+(raw[i][0]-minx)*sc,y=oy+(raw[i][1]-miny)*sc;
    const key=Math.round(x/6)+','+Math.round(y/6);const k=seen[key]=(seen[key]||0)+1;
    if(k>1)y+=24*(k-1);  // 같은 자리(같은 주소)는 아래로 비켜 그린다
    return {s,x,y};});
  // 축척: 화면 1px = 몇 m
  const mPerPx=111320/sc;const nice=[50,100,200,250,500,1000,2000,5000].find(m=>m/mPerPx>=70)||5000;
  const barPx=nice/mPerPx,barLabel=nice>=1000?(nice/1000)+'km':nice+'m';
  let lines='';
  for(const day of [...new Set(at.map(p=>p.s.일차))]){
    const d=at.filter(p=>p.s.일차===day);if(d.length<2)continue;
    lines+=`<polyline class="route ${day===2?'d2':''}" points="${d.map(p=>p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ')}"/>`;
  }
  const dots=at.map(({s,x,y})=>{const meal=['점심','저녁'].includes(s.시간칸);const c=s.일차===2?'d2':meal?'meal':'';
    return `<g class="pin ${c}" data-n="${s.순번}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><title>${esc(s.순번+'. '+s.표시명+' · '+s.일차+'일차 '+(s.시각||'시각 미정'))}</title><circle r="13"/><text dy="4.5">${s.순번}</text>${x>W*0.62?`<text class="lbl end" x="-17" dy="4">`:`<text class="lbl" x="17" dy="4">`}${esc(s.표시명)}</text></g>`;}).join('');
  return `<div class="routemap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="코스 동선 그림">
    <text class="north" x="${W-26}" y="30">N ↑</text>
    ${lines}${dots}
    <g transform="translate(20,${H-22})"><line class="bar" x1="0" y1="0" x2="${barPx.toFixed(1)}" y2="0"/><text class="barlbl" x="${(barPx/2).toFixed(1)}" y="-6">${barLabel}</text></g>
  </svg><p class="note">바탕 지도 없이 장소 위치만 그린 동선입니다. 선은 순서를 잇는 직선이며 실제 이동 경로가 아닙니다.${none?` 좌표가 없는 장소 ${none}곳은 그림에서 빠졌습니다.`:''}</p></div>`;
}

$('newBtn').onclick=()=>$('newDlg').showModal();
$('newOk').onclick=()=>$('newDlg').close();  // 서버 보안 설정이 HTML 안의 onclick을 막아서 여기서 연결
loadList();
