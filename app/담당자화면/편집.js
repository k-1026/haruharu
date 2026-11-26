(function(root){
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const 작업={요청:'자유롭게 요청',교체:'장소 교체',제외:'일정 제외',추가:'일정 추가',순서:'방문 순서',체류시간:'머무는 시간',식사:'식사 구성'};
  function 요청값(rec,v){
    if(!(v.요청||'').trim())throw new Error('수정 요청을 적어 주세요.');
    if(v.요청.length>1000)throw new Error('수정 요청은 1000자 이내로 적어 주세요.');
    if(v.범위==='일정'&&!(v.칸ID||[]).length)throw new Error('바꿀 개별 일정을 선택해 주세요.');
    if(v.작업==='체류시간'&&(!Number.isInteger(v.머무는분)||v.머무는분<5||v.머무는분>480))throw new Error('머무는 시간은 5~480분으로 입력해 주세요.');
    return {기획id:rec.기획id,안id:rec.안id,기준버전:rec.버전,요청:v.요청.trim(),수정:{...v,요청:undefined}};
  }
  function 화면(rec,이전=false){
    if(!rec.수정대상)return '<p class="note">새 수정 화면을 불러오려면 서비스 서버를 다시 시작한 뒤 코스를 다시 열어 주세요.</p>';
    const days=[...new Set(rec.수정대상.map(r=>r.일차))];
    return `<form id="courseEdit" class="course-editor"><fieldset ${이전?'disabled':''}><legend class="sr-only">코스 수정 요청</legend>
      <p class="note">어떤 장소든 바꿀 수 있어요. 변경 범위를 먼저 고르고 원하는 내용을 적어 주세요. 선택하지 않은 방문과 이전 초안은 보존해요.</p>
      ${이전?'<p class="err">이전 버전은 수정할 수 없어요. 최신 코스로 돌아가 주세요.</p>':''}
      <div class="edit-controls"><label>수정 범위<select id="editScope"><option value="일정">개별 일정</option><option value="하루">하루</option><option value="전체">전체 코스</option></select></label>
      <label id="editDayLabel" hidden>수정할 날짜<select id="editDay">${days.map(d=>`<option value="${esc(d)}">${esc(d)}일차</option>`).join('')}</select></label>
      <label>수정 방식<select id="editAction">${Object.entries(작업).map(([v,t])=>`<option value="${v}">${t}</option>`).join('')}</select></label></div>
      <div id="editTargets" class="edit-targets">${days.map(d=>`<div><h4>${esc(d)}일차</h4>${rec.수정대상.filter(r=>r.일차===d).map(r=>`<label class="edit-target ${r.수정가능?'':'edit-locked'}"><input type="checkbox" name="editStop" value="${esc(r.칸ID)}" ${r.수정가능?'':'disabled'}><span><small>${esc(r.시간칸)}${r.수정가능?'':' · 기본 구간'}</small>${esc(r.장소명)}</span></label>`).join('')}</div>`).join('')}</div>
      <p id="editKeep" class="note" aria-live="polite"></p>
      <label id="editPlaceLabel" hidden>바꿀 장소 · 선택 사항<select id="editPlace"><option value="">요청과 동선에 맞춰 제안받기</option>${(rec.장소후보||[]).map(r=>`<option value="${esc(r.장소명)}">${esc(r.장소명)} · ${esc(r.시간칸)} · ${esc(r.상태)}</option>`).join('')}</select></label>
      <label id="editMinutesLabel" hidden>머무는 시간(분)<input id="editMinutes" type="number" min="5" max="480" step="1" value="60"></label>
      <label for="editText">원하는 변경 내용</label><textarea id="editText" maxlength="1000" rows="3" placeholder="예: 2일차는 실내 위주로, 점심은 전날과 다른 음식으로 바꿔 주세요. 유지할 장소나 원하는 순서도 적어 주세요."></textarea>
      <div class="edit-examples" aria-label="요청 예시">${['같은 장소를 반복하지 않게 바꿔 주세요.','걷는 시간을 줄여 주세요.','실내 관광을 늘려 주세요.','식사 후보를 다양하게 제안해 주세요.'].map(t=>`<button type="button" class="pill" data-edit-example="${esc(t)}">${esc(t)}</button>`).join('')}</div>
      <label class="edit-repeat"><input type="checkbox" id="editRepeat"> 같은 장소 재방문을 허용해요</label>
      <p class="note">선택 지역·기간은 유지해요. 기본 숙박·자유시간 구간은 보존하며, 운영·이동 자료가 부족하면 확인할 점으로 남겨요. 요청이 보존 대상에도 영향을 주면 수정 범위를 넓혀 주세요.</p>
      <button class="btn primary" id="editSubmit" type="submit">요청대로 수정하기</button><p id="editError" class="err" role="alert"></p>
      </fieldset></form>`;
  }
  function 연결(container,rec,onSubmit){
    const form=container.querySelector('#courseEdit');if(!form)return;
    const $=id=>form.querySelector('#'+id);
    function 값(){return {범위:$('editScope').value,일차:Number($('editDay').value),작업:$('editAction').value,
      칸ID:[...form.querySelectorAll('[name=editStop]:checked')].map(x=>x.value),요청:$('editText').value,
      대체장소:$('editAction').value==='교체'?$('editPlace').value:'',머무는분:Number($('editMinutes').value),재방문허용:$('editRepeat').checked};}
    function 갱신(){
      const v=값(),선택=rec.수정대상.filter(r=>r.수정가능&&(v.범위==='전체'||v.범위==='하루'&&r.일차===v.일차||v.범위==='일정'&&v.칸ID.includes(r.칸ID)));
      $('editTargets').hidden=v.범위!=='일정';$('editDayLabel').hidden=v.범위!=='하루';
      $('editMinutesLabel').hidden=v.작업!=='체류시간';$('editPlaceLabel').hidden=v.작업!=='교체';
      $('editKeep').textContent=`수정 대상 ${선택.length}개 · 나머지 ${rec.수정대상.length-선택.length}개 방문 보존${선택.length?' — '+선택.map(r=>`${r.일차}일차 ${r.장소명}`).join(', '):''}`;
    }
    form.addEventListener('change',갱신);
    form.querySelectorAll('[data-edit-example]').forEach(b=>b.onclick=()=>{$('editText').value=[$('editText').value.trim(),b.dataset.editExample].filter(Boolean).join('\n');$('editText').focus();});
    form.onsubmit=async e=>{e.preventDefault();$('editError').textContent='';
      try{const payload=요청값(rec,값());$('editSubmit').disabled=true;await onSubmit(payload);}
      catch(err){$('editError').textContent=err.message;$('editSubmit').disabled=false;}};
    갱신();
  }
  const api={화면,요청값,연결};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.코스편집=api;
})(typeof globalThis!=='undefined'?globalThis:this);
