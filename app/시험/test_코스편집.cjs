const {test}=require('node:test'),assert=require('node:assert/strict');
const edit=require('../담당자화면/편집.js');
const display=require('../담당자화면/plan.js'),model=require('../담당자화면/map-model.js');

function personalFixture(version=2,ready=true){
 const stops=[{순번:1,칸ID:'a',일차:1,장소명:'앞',시각:'11:00',좌표:[35.87,128.58]},
 {순번:2,칸ID:'m',일차:1,장소명:'기준점',시간칸:'점심',식사권역:true,시각:'12:00',종료시각:'13:00',머무는시간:60},
 {순번:3,칸ID:'b',일차:1,장소명:'뒤',시각:'13:30',좌표:[35.87,128.61]}];
 const candidate={장소명:'식당B',이름:'식당B',좌표:[35.87,128.60],선택가능:ready,반영가능:true,오류:[],확인필요:ready?[]:['방문일 미정'],
 후보이동:[{출발:'앞',도착:'식당B',분:10,경로:[[35.87,128.58],[35.87,128.6]]},{출발:'식당B',도착:'뒤',분:12,경로:[[35.87,128.6],[35.87,128.61]]}]};
 return {형식버전:1,코스키:'r/01/t',안id:'A',버전:version,일정:stops,식사묶음:[{칸ID:'m',공개준비:ready,후보:[candidate]}]};
}
function memoryStorage(){const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)};}

test('관광객 선택은 기기별로 분리하고 새로 열어도 복원하며 공통 일정은 수정하지 않는다',()=>{
 const pack=personalFixture(),before=structuredClone(pack),store=memoryStorage();
 const a=model.personalMeals(pack,store),b=model.personalMeals(pack,memoryStorage());
 const chosen=a.select('m','식당B');
 assert.equal(chosen.선택.m,'식당B');assert.equal(chosen.일정[1].장소명,'식당B');
 assert.equal(chosen.일정[1].시각,'12:00');assert.equal(chosen.일정[1].종료시각,'13:00');
 assert.equal(model.label(chosen.일정[1]),'내 점심 · 식당B');
 assert.equal(chosen.일정[0].다음이동.도보분,10);assert.equal(chosen.일정[1].다음이동.도보분,12);
 assert.deepEqual(chosen.일정[2],before.일정[2]);assert.deepEqual(pack,before);
 assert.equal(b.snapshot().선택.m,undefined);
 assert.equal(model.personalMeals(pack,store).snapshot().선택.m,'식당B');
 assert.equal(model.personalMeals(personalFixture(3),store).snapshot().선택.m,undefined);
 a.clear('m');assert.deepEqual(a.snapshot().일정,pack.일정);
});

test('관광객 개인 선택은 식당 이름과 변경 전후 이동시간을 바로 설명한다',()=>{
 const c={장소명:'대백<img>',이름:'대백<img>',기존이동:[{분:27}],후보이동:[{출발:'김광석길',도착:'대백<img>',분:10}]};
 const html=display.개인식사안내(c);
 assert.match(html,/내 점심/);assert.match(html,/27분 → 10분/);assert.match(html,/17분 감소/);
 assert.match(html,/나머지 일정/);assert.ok(!html.includes('<img>'));assert.match(html,/&lt;img&gt;/);
});

test('관광객은 미검증·미등록 후보를 선택할 수 없고 직원의 비공개 미리보기만 별도로 허용한다',()=>{
 const pack=personalFixture(2,false),store=memoryStorage();
 assert.throws(()=>model.personalMeals(pack,store).select('m','식당B'),/확인/);
 assert.throws(()=>model.personalMeals(pack,store).select('m','임의식당'),/후보/);
 assert.equal(model.personalMeals(pack,store,{preview:true}).select('m','식당B').선택.m,'식당B');
 assert.equal(model.personalMeals(pack,store).snapshot().선택.m,undefined);
 pack.식사묶음[0].후보[0].오류=['다음 일정 충돌'];
 assert.throws(()=>model.personalMeals(pack,store,{preview:true}).select('m','식당B'),/충돌/);
});

test('직원 점심 패널은 후보 묶음을 구성하며 단일식당 반영을 안내하지 않는다',()=>{
 const html=display.장소패널({일차:1,시간칸:'점심',식사권역:true,저장후보:['식당B'],식당후보:[{장소명:'식당B',이름:'식당B'}]});
 assert.match(html,/후보 묶음 저장/);assert.match(html,/data-meal-option/);assert.match(html,/관광객/);
 const preview=display.식사비교({시간칸:'점심',반영가능:true,확인필요:['방문일 미정']});
 assert.doesNotMatch(preview,/이 후보로 반영|mealAcknowledge/);
});
test('식사 비교는 앞뒤 시간·차이·불가 사유와 명시 반영을 표시한다',()=>{
 const value={장소명:'식당<img>',반영가능:true,확인필요:['방문일 미정'],오류:[],기존이동:[{출발:'앞',도착:'옛 식당',분:8},{출발:'옛 식당',도착:'뒤',분:12}],후보이동:[{출발:'앞',도착:'새 식당',분:10},{출발:'새 식당',도착:'뒤',분:9}]};
 const html=display.식사비교(value);for(const t of ['기존','후보','8분','10분','12분','9분','이 후보로 반영','mealAcknowledge'])assert.ok(html.includes(t),t);
 assert.ok(!html.includes('<img>'));assert.ok(html.includes('&lt;img&gt;'));
 assert.match(display.식사비교({...value,반영가능:false,오류:['다음 일정 이동시간 부족']}),/disabled/);
});
test('식사 후보 경로 미리보기는 원본과 다른 일정·시각을 보존한다',()=>{
 const stops=[{순번:1,일차:1,장소명:'앞',좌표:[35.87,128.58]},{순번:2,일차:1,칸ID:'m',장소명:'원래 식당',식사권역:true,권역표시:{중심:[35.87,128.59]},시각:'12:00'},{순번:3,일차:1,장소명:'뒤',좌표:[35.87,128.61]}];
 const before=structuredClone(stops);const result=model.candidateStops(stops,2,{장소명:'새 후보',좌표:[35.87,128.60],후보이동:[{분:10},{분:12}]});
 assert.deepEqual(stops,before);for(const k of Object.keys(before[0]))assert.deepEqual(result[0][k],before[0][k]);assert.deepEqual(result[2],before[2]);assert.equal(result[1].시각,'12:00');
 assert.deepEqual(model.model(result).entries[1].point,[35.87,128.60]);
});
test('식사 경로 기준 위치가 있으면 위치 미정이라고 표시하지 않는다',()=>{
 const html=display.장소패널({일차:1,시간칸:'점심',식사권역:true,경로좌표:[35.87,128.6],식당후보:[]});
 assert.ok(!html.includes('아직 지도 위치가 정해지지 않았습니다'));
});
const rec={기획id:'r/01회차',안id:'B',버전:3,수정대상:[
 {칸ID:'l1',일차:1,시간칸:'점심',장소명:'가게A',수정가능:true},
 {칸ID:'l2',일차:2,시간칸:'점심',장소명:'가게A',수정가능:true},
 {칸ID:'s',일차:1,시간칸:'숙박',장소명:'숙소',수정가능:false}],장소후보:[{장소명:'가게B',시간칸:'점심·저녁',상태:'확인'}]};
test('날짜·방문 식별자로 수정하고 보고 있는 안·버전을 전달',()=>{
 const p=edit.요청값(rec,{범위:'일정',칸ID:['l2'],작업:'요청',요청:'다른 점심으로'});
 assert.deepEqual(p.수정.칸ID,['l2']);assert.equal(p.기준버전,3);assert.equal(p.안id,'B');
});
test('일정 선택 누락·빈 요청·시간 입력 오류는 전송 전에 안내',()=>{
 assert.throws(()=>edit.요청값(rec,{범위:'일정',칸ID:[],요청:'교체'}),/일정/);
 assert.throws(()=>edit.요청값(rec,{범위:'전체',요청:''}),/요청/);
 assert.throws(()=>edit.요청값(rec,{범위:'전체',작업:'체류시간',머무는분:0,요청:'짧게'}),/5~480/);
});
test('하루·전체 범위와 추가·교체 후보를 제공하고 HTML을 이스케이프',()=>{
 const html=edit.화면({...rec,장소후보:[{장소명:'<img src=x>',시간칸:'점심'}]});
 for(const text of ['개별 일정','하루','전체 코스','일정 추가','방문 순서','머무는 시간','식사 구성','1일차','2일차'])assert.ok(html.includes(text),text);
 assert.match(html,/value="l2"/);assert.ok(!html.includes('<img src=x>'));assert.match(html,/&lt;img/);
 assert.match(edit.화면(rec,true),/<fieldset disabled/);
});
