const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function setup(){
  const nodes=new Map(),fields=new Map(),handlers={};
  const field=name=>{if(!fields.has(name))fields.set(name,{value:'',checked:false});return fields.get(name);};
  const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',disabled:false,addEventListener:(name,fn)=>handlers[name]=fn,elements:{namedItem:field},querySelectorAll:()=>[field('ro-0-방문일운영확인')]});return nodes.get(id);};
  const c=vm.createContext({document:{getElementById:node},$:node,courseState:{recordId:'record',selectedJobId:'base'},state:{}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'관리자화면/운영확인.js'),'utf8'),c);
  vm.runInContext("reviewState.jobId='base';reviewState.info={일정목록:[{안:'공통',칸ID:'숙박'}],운영대상:[{안:'공통',칸ID:'숙박',대상명:'권역',후보제외가능:false}]}",c);
  return {c,node,field,handlers,run:code=>vm.runInContext(code,c)};
}
test('숙박 익일 종료와 운영 확인 체크를 그대로 직렬화',()=>{
  const x=setup();x.field('rp-0-시작일차').value='1';x.field('rp-0-종료일차').value='2';x.field('rp-0-시작시각').value='23:00';x.field('rp-0-종료시각').value='09:00';x.field('ro-0-방문일운영확인').checked=true;
  const v=JSON.parse(x.run('JSON.stringify(readReviewForm())'));
  assert.equal(v.일정확인[0].종료일차,2);assert.equal(v.일정확인[0].시작시각,'23:00');assert.equal(v.운영확인[0].방문일운영확인,true);assert.equal(v.담당자최종확인,false);
});
test('방문일을 바꾸면 운영 확인과 최종 확인을 다시 요구',()=>{
  const x=setup();x.field('담당자최종확인').checked=true;x.field('ro-0-방문일운영확인').checked=true;
  x.handlers.change({target:{name:'방문시작일'}});assert.equal(x.field('담당자최종확인').checked,false);assert.equal(x.field('ro-0-방문일운영확인').checked,false);
});
test('검토 반영 버튼은 전용 저장 API만 호출',async()=>{
  const x=setup(),calls=[];x.c.coursePost=async(url,payload)=>{calls.push(url);assert.equal(payload.시험id,'base');return {시험id:'new'};};
  x.c.loadRecord=async()=>{};x.c.renderStages=()=>{};x.c.renderPanel=async()=>{};
  await x.run('saveReview({preventDefault(){}})');assert.deepEqual(calls,['/api/course/review/save']);
});
test('선택한 저장본이 바뀌면 잘못된 코스에 저장하지 않음',async()=>{
  const x=setup();x.c.coursePost=async()=>{throw new Error('호출되면 안 됨');};x.run("courseState.selectedJobId='other'");
  await x.run('saveReview({preventDefault(){}})');assert.match(x.node('reviewMessage').textContent,/선택이 바뀌/);
});

test('상시 기획 저장은 오래된 방문일을 보내지 않고 운영 조건을 보존',()=>{
  const x=setup();x.field('운영기준').value='상시기획';x.field('방문시작일').value='2026-11-25';x.field('운영조건').value='금·토 출발 / 동계 제외';
  const v=JSON.parse(x.run('JSON.stringify(readReviewForm())'));
  assert.equal(v.방문시작일,'');assert.equal(v.운영기준,'상시기획');assert.equal(v.운영조건,'금·토 출발 / 동계 제외');
});

test('명시적인 일괄 이동 검토도 사용자 체크와 메모가 있을 때만 반영',()=>{
  const x=setup();x.field('전체연결확인').checked=true;x.field('전체연결메모').value='이동 여유와 다음 연결을 확인';
  let v=JSON.parse(x.run('JSON.stringify(readReviewForm())'));
  assert.equal(v.일정확인[0].연결확인,true);assert.equal(v.일정확인[0].확인메모,'이동 여유와 다음 연결을 확인');
  x.field('전체연결확인').checked=false;v=JSON.parse(x.run('JSON.stringify(readReviewForm())'));assert.equal(v.일정확인[0].연결확인,false);
});

test('관리자 상세의 시간 변경도 방문일·최종 확인을 해제하고 다른 항목은 유지',()=>{
  const x=setup();x.field('담당자최종확인').checked=true;x.field('ro-0-방문일운영확인').checked=true;x.field('ro-0-영업종료').value='21:00';
  x.handlers.change({target:{name:'ro-0-영업종료'}});
  assert.equal(x.field('담당자최종확인').checked,false);assert.equal(x.field('ro-0-방문일운영확인').checked,false);
  const value=JSON.parse(x.run('JSON.stringify(readReviewForm())'));assert.equal(value.운영확인[0].영업종료,'21:00');
});
