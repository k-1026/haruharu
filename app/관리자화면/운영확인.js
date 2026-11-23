'use strict';
const reviewState={jobId:'',info:null,version:0,busy:false};
function reviewReset(){reviewState.version++;reviewState.jobId='';reviewState.info=null;document.getElementById('reviewForm').classList.add('hidden');document.getElementById('reviewMessage').textContent='코스 결과가 있는 저장본을 선택하세요.';document.getElementById('plannerIssues')?.replaceChildren?.();}
function reviewValue(name){return document.getElementById('reviewForm').elements.namedItem(name)?.value || '';}
function reviewChecked(name){return document.getElementById('reviewForm').elements.namedItem(name)?.checked===true;}
function reviewSet(name,value){const node=document.getElementById('reviewForm').elements.namedItem(name);if(node){const explicit=node.options && [...node.options].some(o=>o.value===value);node.value=['미정','미확인'].includes(value) && !explicit?'':value ?? '';node.placeRefresh?.();}}
function reviewCheck(name,label,checked=false){const wrap=el('label',undefined,'reviewcheck'),input=el('input');input.type='checkbox';input.name=name;input.setAttribute('form','reviewForm');input.checked=checked;wrap.append(input,el('span',label));return wrap;}
function dayOptions(){return [['','미정'],['1','1일차'],...(reviewState.info.체류기간==='1박2일'?[['2','2일차']]:[])];}
function buildReview(info){
  const saved=info.저장값 || {};const periods=$('reviewPeriods');periods.replaceChildren();
  info.일정목록.forEach((r,i)=>{
    const missing=![1,2].includes(r.시작일차) || ![1,2].includes(r.종료일차) || !/^\d{2}:\d{2}$/.test(r.시작시각) || !/^\d{2}:\d{2}$/.test(r.종료시각);
    const card=el('details',undefined,'reviewitem plannerday');card.open=false;card.id=`planner-slot-${i}`;
    const time=t=>/^\d{2}:\d{2}$/.test(t || '')?t:'시간 미정';
    const special=r.시간칸==='숙박' || r.시간칸==='2일차오전';
    const short=r.시간칸==='숙박'?'숙박 · 숙소 도착과 다음 날 출발':r.시간칸==='2일차오전'?'2일차 자유시간 · 시작과 끝':`${r.시간칸} · ${r.장소명}`;
    const range=special?`${r.시작시각?(r.시간칸==='숙박'?'도착 ':'시작 ')+time(r.시작시각):'시작 미정'} → ${r.종료시각?(r.시간칸==='숙박'?'출발 ':'끝 ')+time(r.종료시각):'끝 미정'}`:`${r.시작일차 || '?'}일차 ${time(r.시작시각)}${r.종료시각?' → '+time(r.종료시각):''}`;
    card.append(el('summary',`${short} · ${range}　${missing?'확인 필요':'수정하기'}`));const grid=el('div',undefined,'reviewgrid');
    for(const prefix of ['시작','종료']){const label=r.시간칸==='숙박'?(prefix==='시작'?'숙소 도착':'다음 날 숙소 출발'):r.시간칸==='2일차오전'?(prefix==='시작'?'자유시간 시작':'자유시간 끝'):prefix;grid.append(courseInput(`rp-${i}-${prefix}일차`,label+' 일차','',dayOptions()),courseInput(`rp-${i}-${prefix}시각`,label+' 시각','time'));}
    grid.append(courseInput(`rp-${i}-장소권역`,r.시간칸==='숙박'?'숙박 권역':r.시간칸==='2일차오전'?'자유시간 권역':'방문 장소·권역'));
    if(r.시간칸==='숙박' || r.시간칸==='2일차오전'){
      const preset=el('button',r.시간칸==='숙박'?'1일차 밤 → 2일차 아침으로 일차 채우기':'2일차 오전으로 일차 채우기','secondarybutton');preset.type='button';
      preset.addEventListener('click',()=>{const start= document.getElementById('reviewForm').elements.namedItem(`rp-${i}-시작일차`),end=document.getElementById('reviewForm').elements.namedItem(`rp-${i}-종료일차`);if(!start.value)start.value=r.시간칸==='숙박'?'1':'2';if(!end.value)end.value='2';document.getElementById('reviewForm').elements.namedItem('담당자최종확인').checked=false;document.getElementById('reviewForm').elements.namedItem(`rp-${i}-연결확인`).checked=false;});
      grid.append(preset,el('p','일차만 채웁니다. 도착·출발 시각은 실제 계획에 맞춰 입력하세요.','footnote'));
    }
    const admin=el('details',undefined,'planneroptional');admin.append(el('summary','관리자 상세 · 이 구간의 이동 연결'));
    admin.append(courseInput(`rp-${i}-이후연결`,'다음 일정·종료 장소까지의 연결'),courseInput(`rp-${i}-확인메모`,'이동·숙박·자유시간 확인 메모'),reviewCheck(`rp-${i}-연결확인`,'이 기간과 다음 장소까지의 이동·연결을 확인했습니다.',r.연결확인));
    card.append(grid,admin);periods.append(card);
    for(const key of ['시작일차','시작시각','종료일차','종료시각','장소권역','이후연결','확인메모'])reviewSet(`rp-${i}-${key}`,key==='이후연결' && !r[key]?info.일정목록[i+1]?.장소명 || '전체 여행 종료 장소':r[key]);
  });
  const operations=$('reviewOperations');operations.replaceChildren();
  info.운영대상.forEach((target,i)=>{
    const old=target.입력값 || (saved.운영확인 || []).find(r=>r.안===target.안 && r.칸ID===target.칸ID && r.대상명===target.대상명) || {};
    const issues=target.확인필요 || [];
    const card=el('details',undefined,'reviewitem');card.open=issues.length>0;card.dataset.needs=String(issues.length>0);
    card.append(el('summary',`${target.대상명} · ${issues.length?'확인 '+issues.length+'건':'입력된 확인 정보 있음'}`));
    if(typeof placeInfoView==='function')card.append(placeInfoView(target.보유자료));
    if(issues.length){const ul=el('ul',undefined,'reviewissues');issues.forEach(t=>ul.append(el('li',t)));card.append(ul);}
    const grid=el('div',undefined,'reviewgrid');
    const known=el('details',undefined,'reviewknown');known.append(el('summary','채워진 정보·선택 정보 수정하기'));const knownGrid=el('div',undefined,'reviewgrid');known.append(knownGrid);
    const add=(key,label,type='text',options=null,always=false)=>{const field=courseInput(`ro-${i}-${key}`,label,type,options);(always || !old[key] || ['미확인','기타'].includes(old[key])?grid:knownGrid).append(field);};
    add('운영상태','운영 여부 확인','',[['','미확인'],['운영','운영'],['휴무','휴무']]);
    if(target.후보제외가능)grid.append(courseInput(`ro-${i}-처리`,'추천 후보 처리','',[['유지','유지'],['제외','후보에서 제외']]));
    add('마감구분','주문·입장 마감 정보','',[['미확인','미확인'],['확인','마감 시각 확인'],['해당없음','해당 없음 (확인한 경우)']]);
    for(const [key,label] of [['영업시작','영업 시작'],['영업종료','영업 종료'],['마감시각','주문·입장 마감 (해당 시)']]){
      if(key==='마감시각')knownGrid.append(courseInput(`ro-${i}-${key}`,label,'time'));else add(key,label,'time');
    }
    add('출처명','확인한 자료·운영 주체');add('출처등급','출처 구분','',[['','미확인'],['공식','공식 안내'],['운영주체','운영 주체 직접 확인'],['기타','기타 · 재확인 필요']]);add('확인일','자료 확인일','date');
    knownGrid.append(courseInput(`ro-${i}-출처URL`,'출처 URL (있는 경우)','url'),courseInput(`ro-${i}-메모`,'요일·휴무·예외 운영 등 확인 내용'));
    known.append(reviewCheck(`ro-${i}-익일종료`,'영업 종료가 다음 날입니다.',old.익일종료));
    card.append(grid,known,reviewCheck(`ro-${i}-방문일운영확인`,'특정 출발일의 요일·휴무·예외 운영을 출처로 확인했습니다. (상시 기획은 앱이 정기휴무로 요일을 계산하므로 비워 두세요)',old.방문일운영확인));operations.append(card);
    for(const key of ['운영상태','처리','영업시작','영업종료','마감시각','마감구분','출처명','출처URL','출처등급','확인일','메모'])reviewSet(`ro-${i}-${key}`,old[key] ?? (key==='처리'?'유지':key==='마감구분'?(old.마감시각?'확인':'미확인'):''));
  });
  reviewSet('방문시작일',saved.방문시작일);reviewSet('겹침처리',saved.겹침처리);reviewSet('겹침메모',saved.겹침메모);
  reviewSet('운영기준',saved.운영기준 || (saved.방문시작일?'출발일시험':'상시기획'));reviewSet('운영조건',saved.운영조건);
  document.getElementById('reviewForm').elements.namedItem('전체연결확인').checked=false;reviewSet('전체연결메모','');
  updateReviewMode();
  $('reviewOverview').textContent=`일정 ${info.일정목록.length}개 · 기간 미정 ${info.일정목록.filter(r=>![1,2].includes(r.종료일차) || !r.종료시각).length}개 · 운영 확인 대상 ${info.운영대상.filter(t=>t.확인필요?.length).length}개. 저장된 값은 다시 입력하지 않아도 됩니다.`;
  document.getElementById('reviewForm').elements.namedItem('담당자최종확인').checked=false;
  renderPlannerIssues(info);
}
function renderPlannerIssues(info){
  const box=$('plannerIssues');box.replaceChildren();const seen=new Set();
  const add=(title,description,action)=>{const line=el('div',undefined,'plannerwarning');const copy=el('div');copy.append(el('strong',title),el('p',description));line.append(copy);if(action){const button=el('button',action.label,'secondarybutton');button.type='button';button.addEventListener('click',action.run);line.append(button);}box.append(line);};
  const editSlot=(index,field='시작시각')=>{const card=$('planner-slot-'+index);if(card){card.open=true;card.scrollIntoView({behavior:'smooth',block:'center'});document.getElementById('reviewForm').elements.namedItem(`rp-${index}-${field}`)?.focus();}};
  const status=courseState.job || {},conditions=readCourseForm();
  if(!conditions.종료지점 || conditions.종료지점==='미확인')add('전체 여행 종료 장소 미정','종료 장소를 정해야 2일차 자유시간 뒤의 이동도 확인할 수 있습니다.',{label:'종료 장소 정하기',run:()=>{$('courseDetails').open=true;$('course-종료지점').focus();}});
  const first=info.일정목록.find(r=>r.시간칸!=='숙박');
  if(first && conditions.시작지점 && conditions.시작지점!=='미확인' && typeof placeName==='function' && placeName(first.장소명)!==placeName(conditions.시작지점))add('시작 장소와 첫 관광지가 다릅니다',`전체 여행 시작: ${conditions.시작지점} / 첫 관광: ${first.장소명}. ${conditions.시작지점}에서 관광을 시작한다면 아래 버튼을 누르세요. 집결 장소라면 첫 관광까지 이동 시간을 확인하세요.`,{label:'시작 장소를 첫 관광지로',run:()=>{const i=info.일정목록.indexOf(first),field=document.getElementById('reviewForm').elements.namedItem(`rp-${i}-장소권역`);field.value=conditions.시작지점;field.placeRefresh?.();field.dispatchEvent(new Event('change',{bubbles:true}));editSlot(i,'장소권역');$('reviewMessage').textContent='첫 관광지를 시작 장소로 바꿨습니다. 아래 ‘수정한 코스 저장’을 눌러야 반영됩니다. 기존 관광지 근거·운영정보는 새 장소에 사용할 수 없으므로 저장 뒤 다시 확인하세요.';}});
  for(const [kind,label] of [['숙박','숙박 시간'],['2일차오전','2일차 자유시간']]){
    const index=info.일정목록.findIndex(r=>r.시간칸===kind && (!r.종료시각 || !r.시작시각));
    if(index>=0)add(label+' 미정',kind==='숙박'?'숙소에 도착할 때와 다음 날 숙소를 떠날 때를 입력하세요.': '2일차 자유시간이 시작하고 끝나는 시각을 입력하세요.',{label:'시간 입력',run:()=>editSlot(index)});
  }
  if((status.문제 || []).some(x=>x.includes('겹침처리')) || (status.담당자확인대기 || []).some(x=>x.includes('E7 겹침')))add('기존 상품과 노선 겹침 확인 대기','기존 상품과 겹치는지 확인한 뒤 처리 방법을 정해야 합니다.',{label:'관리자 검토 열기',run:()=>{$('adminDetails').open=true;}});
  const minutes=value=>/^\d{2}:\d{2}$/.test(value || '')?Number(value.slice(0,2))*60+Number(value.slice(3)):null;
  const rows=info.일정목록.filter(r=>Number.isInteger(r.시작일차) && Number.isInteger(r.종료일차) && minutes(r.시작시각)!==null && minutes(r.종료시각)!==null);
  for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
    const a=rows[i],b=rows[j];if(a.안!==b.안)continue;
    const startA=(a.시작일차-1)*1440+minutes(a.시작시각),endA=(a.종료일차-1)*1440+minutes(a.종료시각),startB=(b.시작일차-1)*1440+minutes(b.시작시각),endB=(b.종료일차-1)*1440+minutes(b.종료시각);
    if(startA<endB && startB<endA)add('일정 시간이 겹침',`${a.시간칸} ${a.시작시각}~${a.종료시각}와 ${b.시간칸} ${b.시작시각}~${b.종료시각}가 겹칩니다. 어느 시간을 바꿀지 정하세요.`,{label:'뒤 일정 수정',run:()=>editSlot(info.일정목록.indexOf(b))});
  }
  for(const a of rows){
    const endA=(a.종료일차-1)*1440+minutes(a.종료시각);
    const next=rows.filter(b=>b!==a && b.안===a.안 && (b.시작일차-1)*1440+minutes(b.시작시각)>=endA)
      .sort((b,c)=>(b.시작일차-c.시작일차)*1440+minutes(b.시작시각)-minutes(c.시작시각))[0];
    if(!next)continue;
    const gap=(next.시작일차-1)*1440+minutes(next.시작시각)-endA;
    if(gap<=5)add('다음 장소까지 이동 여유 확인',`${a.시간칸} ${a.종료시각} 종료 → ${next.시간칸} ${next.시작시각} 시작: ${gap}분 간격입니다. 이동 시간을 확인하거나 다음 일정의 시작 시각을 늦추세요.`,{label:'다음 시작 시각 수정',run:()=>editSlot(info.일정목록.indexOf(next))});
  }
  for(const target of info.운영대상){
    const conflicts=(target.확인필요 || []).filter(t=>/충돌|휴무로|마감 이후/.test(t));if(!conflicts.length)continue;
    const key=target.대상명+conflicts.join();if(seen.has(key))continue;seen.add(key);
    add(target.대상명+' 운영시간 재검토',conflicts.join(' / '),{label:'일정 수정',run:()=>editSlot(info.일정목록.findIndex(r=>r.안===target.안 && r.칸ID===target.칸ID))});
  }
  if(!box.hasChildNodes())box.append(el('p','현재 표시할 일정·운영시간 충돌이 없습니다. 미확인 자료는 관리자 상세에 남아 있습니다.','footnote'));
}
async function loadReview(id){
  const version=++reviewState.version;reviewState.jobId=id;reviewState.info=null;reviewState.busy=true;
  $('reviewForm').classList.add('hidden');$('reviewMessage').textContent='선택한 코스의 일정·운영 확인 항목을 읽고 있습니다…';
  try{const info=await api('/api/course/review?id='+encodeURIComponent(id));if(version!==reviewState.version || courseState.selectedJobId!==id)return;
    reviewState.info=info;buildReview(info);$('reviewForm').classList.remove('hidden');$('reviewMessage').textContent='저장된 코스입니다. 수정할 일정만 펼치세요. 운영자료와 세부 검사는 아래 관리자 상세에서 확인할 수 있습니다.';
  }catch(e){if(version===reviewState.version)$('reviewMessage').textContent=e.message;}
  finally{if(version===reviewState.version){reviewState.busy=false;$('reviewSave').disabled=false;}}
}
function readReviewForm(){
  const mode=reviewValue('운영기준') || '상시기획';
  const value={운영기준:mode,운영조건:reviewValue('운영조건'),방문시작일:mode==='출발일시험'?reviewValue('방문시작일'):'',겹침처리:reviewValue('겹침처리'),겹침메모:reviewValue('겹침메모'),담당자최종확인:reviewChecked('담당자최종확인'),일정확인:[],운영확인:[]};
  reviewState.info.일정목록.forEach((r,i)=>{
    const row={안:r.안,칸ID:r.칸ID,연결확인:reviewChecked(`rp-${i}-연결확인`)};
    for(const key of ['시작일차','종료일차'])row[key]=Number(reviewValue(`rp-${i}-${key}`)) || '미정';
    for(const key of ['시작시각','종료시각','장소권역','이후연결','확인메모'])row[key]=reviewValue(`rp-${i}-${key}`);
    if(reviewChecked('전체연결확인') && reviewValue('전체연결메모')){row.연결확인=true;row.확인메모=row.확인메모 || reviewValue('전체연결메모');}
    value.일정확인.push(row);
  });
  reviewState.info.운영대상.forEach((r,i)=>{
    const row={안:r.안,칸ID:r.칸ID,대상명:r.대상명,익일종료:reviewChecked(`ro-${i}-익일종료`),방문일운영확인:reviewChecked(`ro-${i}-방문일운영확인`)};
    for(const key of ['운영상태','영업시작','영업종료','마감시각','마감구분','출처명','출처URL','출처등급','확인일','메모'])row[key]=reviewValue(`ro-${i}-${key}`);
    row.처리=r.후보제외가능?reviewValue(`ro-${i}-처리`):'유지';value.운영확인.push(row);
  });return value;
}
async function saveReview(event){
  event.preventDefault();if(reviewState.busy || !reviewState.info)return;
  const id=reviewState.jobId,version=reviewState.version,record=courseState.recordId;
  if(courseState.job===null){$('reviewMessage').textContent='위쪽 시작·종료 등 코스 조건에 미저장 변경이 있습니다. 먼저 기존 초안에 수정 반영한 뒤 운영·일정 확인을 입력하세요.';return;}
  if(courseState.selectedJobId!==id){$('reviewMessage').textContent='저장본 선택이 바뀌었습니다. 확인 항목을 다시 불러오세요.';return;}
  const value=readReviewForm();reviewState.busy=true;$('reviewSave').disabled=true;$('reviewMessage').textContent='운영·일정 확인을 저장하고 4단계 준비 여부를 검사하고 있습니다. AI 호출 없음.';
  try{const job=await coursePost('/api/course/review/save',{시험id:id,확인내용:value});if(version!==reviewState.version)return;
    await loadRecord(record,job.시험id);state.stage=3;state.view='result';renderStages();await renderPanel();
    $('reviewMessage').textContent='수정한 코스를 새 초안으로 저장했습니다. AI를 실행하거나 코스를 확정하지 않았습니다.';
  }catch(e){if(version===reviewState.version)$('reviewMessage').textContent=e.message;}
  finally{if(version===reviewState.version){reviewState.busy=false;$('reviewSave').disabled=false;}}
}
function readinessView(value){
  const card=el('section',undefined,'checkcard');card.append(el('h3','앱 추가 운영점검 · 기존 4단계 준비 검사'),badge(value.진행가능?'추가점검 통과 · AI 미실행':'추가 확인 항목',value.진행가능?'통과':'실패'));
  for(const [title,key] of [['확인할 항목','확인필요'],['유지할 경고','유지경고']]){
    if(!value[key]?.length)continue;card.append(el('h4',title));const ul=el('ul');for(const p of value[key])ul.append(el('li',String(p)));card.append(ul);
  }card.append(el('p',value.검사범위 || '입력된 확인 내용에 근거한 준비 검사입니다.','help'));return card;
}
function updateReviewMode(){
  const dated=reviewValue('운영기준')==='출발일시험';
  $('reviewDateField').classList.toggle('hidden',!dated);
  document.getElementById('reviewForm').elements.namedItem('방문시작일').disabled=!dated;
  $('reviewModeHelp').textContent=dated?'이 출발일을 기준으로 요일·휴무·계절 예외를 확인합니다.':'상시 상품은 출발일을 받지 않습니다. 앱이 월~일 출발을 장소별 정기휴무와 대조해 ‘출발 가능 요일’을 보여 줍니다(1박2일은 2일차를 다음 요일로 계산). 가능한 요일이 없으면 E4 운영 충돌로 막습니다. 1월 1일·명절·n번째 일요일 같은 휴무는 계산하지 않고 안내로만 붙입니다.';
}
document.getElementById('reviewForm').addEventListener('submit',saveReview);
function reviewChanged(event){
  if(!event.target.name || !/^(rp-|ro-|운영기준$|운영조건$|방문시작일$|전체연결|겹침|담당자최종확인$)/.test(event.target.name))return;
  if(event.target.name!=='담당자최종확인')document.getElementById('reviewForm').elements.namedItem('담당자최종확인').checked=false;
  if(event.target.name==='운영기준')updateReviewMode();
  if(['방문시작일','운영기준','운영조건'].includes(event.target.name))reviewState.info?.운영대상.forEach((r,i)=>{const input=document.getElementById('reviewForm').elements.namedItem(`ro-${i}-방문일운영확인`);if(input)input.checked=false;});
  if(/^rp-/.test(event.target.name))document.getElementById('reviewForm').elements.namedItem('전체연결확인').checked=false;
  const periodChange=event.target.name.match(/^rp-(\d+)-(?!연결확인$)/);
  if(periodChange)document.getElementById('reviewForm').elements.namedItem(`rp-${periodChange[1]}-연결확인`).checked=false;
  const opChange=event.target.name.match(/^ro-(\d+)-(?!방문일운영확인$)/);
  if(opChange)document.getElementById('reviewForm').elements.namedItem(`ro-${opChange[1]}-방문일운영확인`).checked=false;
  const dayChange=event.target.name.match(/^rp-(\d+)-시작일차$/);
  if(dayChange && reviewState.info){const target=reviewState.info.일정목록[Number(dayChange[1])];reviewState.info.운영대상.forEach((r,i)=>{if(r.안===target.안 && r.칸ID===target.칸ID)document.getElementById('reviewForm').elements.namedItem(`ro-${i}-방문일운영확인`).checked=false;});}
}
document.getElementById('reviewForm').addEventListener('change',reviewChanged);
document.getElementById('adminDetails')?.addEventListener('change',reviewChanged);
