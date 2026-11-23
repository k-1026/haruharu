'use strict';
const placeState={items:[],loaded:false};
function placeName(value){return value.replace(/^자유식\s*·\s*/,'').replace(/\s*\([^)]*\)/g,'').replace(/^대구광역시\s*/,'').replace(/^(중구|동구)\s+/,'').replace(/\s*(권역|일대)$/,'').trim();}
function findPlace(value){const found=placeState.items.filter(r=>placeName(r.장소명)===placeName(value));return found.length===1?found[0]:null;}
async function loadPlaces(){
  if(placeState.loaded)return;
  const info=await api('/api/places');placeState.items=info.장소목록;placeState.loaded=true;
}
function placeInfoView(data){
  const box=el('div',undefined,'placeinfo');
  if(!data?.장소명){box.append(el('p','보유한 운영정보 없음 · 직접 입력한 장소도 저장할 수 있습니다.'));return box;}
  box.append(el('strong',data.장소명));
  for(const [key,label] of [['운영시간','운영시간'],['정기휴무','휴무'],['마지막입장','입장 마감'],['출처ID','출처'],['출처등급','출처 구분'],['확인일','자료 확인일'],['비고','참고']])box.append(el('p',`${label}: ${data[key] || '자료 없음'}`));
  if(/^https?:\/\//.test(data.출처URL || '')){const link=el('a','출처 열기');link.href=data.출처URL;link.target='_blank';link.rel='noopener noreferrer';box.append(link);}
  box.append(el('small','저장된 자료입니다. 현재 운영·예약 가능 여부를 새로 확인한 것은 아닙니다.'));return box;
}
function attachPlacePicker(wrap,input){
  const list=el('datalist');list.id=input.id+'-places';input.setAttribute('list',list.id);input.setAttribute('autocomplete','off');input.placeholder='장소 이름 검색 또는 직접 입력';
  for(const data of placeState.items){const o=el('option');o.value=data.장소명;o.label=[data.구,data.장소유형].filter(Boolean).join(' · ');list.append(o);}
  const info=el('div',undefined,'placepreview');
  const update=()=>{
    info.replaceChildren();if(!input.value.trim())return;
    const data=findPlace(input.value),details=el('details');details.append(el('summary',data?'보유 운영정보 · 관리자 자료':'운영자료 없음 · 관리자 확인 필요'),placeInfoView(data));info.append(details);
  };
  input.addEventListener('input',update);input.addEventListener('change',update);input.placeRefresh=update;
  wrap.append(list,info);
}
