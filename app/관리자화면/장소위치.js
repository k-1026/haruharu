// 관리자 '장소 위치 확인': 코드가 찾은 좌표 후보를 보고 '맞다'를 누르면 장소 CSV에 반영하고 길 수집을 시작한다.
(function(){
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let token=null,timer=null;
async function get(url){const r=await fetch(url,{cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오지 못했습니다.');return d;}
async function post(url,body){
  token=token||(await get('/api/session')).token;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':token},body:JSON.stringify(body)});
  const d=await r.json();if(!r.ok)throw new Error(d.오류||'저장하지 못했습니다.');return d;
}
const 지도=(위도,경도)=>`https://www.openstreetmap.org/?mlat=${encodeURIComponent(위도)}&mlon=${encodeURIComponent(경도)}#map=18/${encodeURIComponent(위도)}/${encodeURIComponent(경도)}`;
function 카드(p,i){
  const c=p.후보[0]||{};
  const 후보=p.후보.length?p.후보.map(x=>`<li>${esc(x.출처)} · ${esc(x.정밀도||'정밀도 미상')} · ${esc(x.찾은이름||'')} · <a href="${esc(지도(x.위도,x.경도))}" target="_blank" rel="noopener">지도에서 보기 ↗</a></li>`).join('')
    :`<li>${p.못찾음?'자동 검색으로 찾지 못했어요. 지도에서 직접 찾아 숫자를 넣어 주세요.':'아직 찾는 중이에요.'}</li>`;
  const 신고=p.신고.length?`<p class="warn">기획자 신고: ${p.신고.map(x=>esc(x.내용)).join(' · ')}</p>`:'';
  return `<article class="place-card"><h3>${esc(p.장소명)} <small>${esc(p.구)} · ${esc(p.주소||'주소 없음')}</small></h3>${신고}
  <ul>${후보}</ul>
  <form data-i="${i}" class="confirm">
    <label>위도 <input name="위도" inputmode="decimal" required value="${esc(c.위도||'')}"></label>
    <label>경도 <input name="경도" inputmode="decimal" required value="${esc(c.경도||'')}"></label>
    <label>근거 URL <input name="근거URL" type="url" required value="${esc(c.근거URL||'')}"></label>
    <label>무엇과 대조했나요 <input name="근거설명" required value="${esc(c.위도?'자동 검색 위치를 지도에서 보고 시설 위치와 맞는지 확인':'')}"></label>
    <button class="btn primary" type="submit">맞다 · 이 위치로 확인</button><span class="err" role="alert"></span>
  </form></article>`;
}
async function load(){
  try{
    const d=await get('/api/place-review');
    $('job').textContent='자동 작업: '+(d.작업.상태==='진행중'?'진행 중 · ':'')+(d.작업.안내||'');
    $('list').innerHTML=d.대기.length?d.대기.map(카드).join(''):'<p>확인할 장소가 없어요. 모든 장소가 지도에 표시돼요.</p>';
    $('list').querySelectorAll('form.confirm').forEach(f=>f.onsubmit=async e=>{
      e.preventDefault();const p=d.대기[Number(f.dataset.i)],v=Object.fromEntries(new FormData(f));
      f.querySelector('.err').textContent='';f.querySelector('button').disabled=true;
      try{const r=await post('/api/place-review/confirm',{장소명:p.장소명,...v});$('notice').textContent=p.장소명+': '+r.안내;await load();}
      catch(err){f.querySelector('.err').textContent=err.message;f.querySelector('button').disabled=false;}
    });
    clearTimeout(timer);if(d.작업.상태==='진행중')timer=setTimeout(load,10000);
  }catch(err){$('list').innerHTML=`<p class="err">${esc(err.message)}</p>`;}
}
$('refresh').onclick=load;load();
})();
