const {test}=require('node:test'),assert=require('node:assert/strict');
const edit=require('../담당자화면/편집.js');
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
