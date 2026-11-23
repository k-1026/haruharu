// 담당자 화면: 저장된 코스를 지도·시간표로 보여 준다. 읽기 전용, AI 호출 없음.
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function get(url){const r=await fetch(url);const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오기 실패');return d;}
let map=null;

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
  ${s.코스있음?`<section class="card"><div class="aihead"><strong>동선 · 시간표</strong><span class="note">지도 선은 직선이며 실제 이동 경로가 아닙니다.</span></div>
    <div class="mapgrid"><div id="mapbox"></div><div class="timeline" id="timeline"></div></div></section>`:''}`;
  if(s.코스있음)draw(s.일정);
}

function draw(stops){
  const tl=$('timeline');let lastDay=null;
  for(const s of stops){
    const meal=s.표시명.startsWith('자유식')||['점심','저녁'].includes(s.시간칸);
    const cls=!s.좌표?'none':s.일차===2?'d2':meal?'meal':'';
    if(s.일차!==lastDay){tl.insertAdjacentHTML('beforeend',`<div class="daylabel">${esc(s.일차)}일차</div>`);lastDay=s.일차;}
    tl.insertAdjacentHTML('beforeend',`<div class="stop"><div class="num ${cls}">${s.순번}</div><div><b>${esc(s.시각||'시각 미정')}</b> ${esc(s.표시명)} <small>· ${esc(s.시간칸)}${s.좌표?'':' · 좌표 미확인'}</small><br><a target="_blank" rel="noopener" href="${esc(s.네이버)}">네이버 지도에서 열기 ↗</a></div></div>`);
  }
  const pts=stops.filter(s=>s.좌표);const box=$('mapbox');
  if(map){map.remove();map=null;}
  if(!pts.length||typeof L==='undefined'){box.innerHTML='<div class="nomap">장소 좌표를 입력하면 지도가 표시됩니다.<br><span class="note">장소 CSV의 위도·경도 칸(네이버 지도에서 확인한 값)</span></div>';return;}
  box.innerHTML='<div id="map"></div>';
  map=L.map('map');L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
  for(const s of pts){
    const cls=s.일차===2?'d2':(['점심','저녁'].includes(s.시간칸)?'meal':'');
    L.marker(s.좌표,{icon:L.divIcon({className:'',html:`<div class="num ${cls}">${s.순번}</div>`,iconSize:[26,26],iconAnchor:[13,13]})}).bindPopup(`${s.순번}. ${esc(s.표시명)}<br>${esc(s.일차)}일차 ${esc(s.시각||'시각 미정')}`).addTo(map);
  }
  L.polyline(pts.map(s=>s.좌표),{color:'#2b6fd2',weight:4,opacity:.75}).addTo(map);
  map.fitBounds(L.latLngBounds(pts.map(s=>s.좌표)).pad(.2));
}

$('newBtn').onclick=()=>$('newDlg').showModal();
loadList();
