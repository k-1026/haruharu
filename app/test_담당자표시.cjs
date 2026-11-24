const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('./담당자화면/plan.js');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');

function render(overrides={}){
  const elements=new Map();
  const document={getElementById(id){if(!elements.has(id))elements.set(id,{innerHTML:'',querySelectorAll:()=>[]});return elements.get(id);}};
  const fixture={안id:'A',버전:4,시간칸:['저녁'],요약:{일정:[],코스있음:true,확인할것:[],출발가능요일:null},
    원래요청:{희망:[{id:'희망-1',내용:'야경을 넣고 싶어요'}]},검사함:true,
    분류:{AI수정:[{문구:'저녁-1: 이동시간 39분 초과',출처:'검증'}],자료보완:[],사람결정:[]},
    정리:{안:[{안id:'A',버전:4,버전들:[1,2,3,4],검증:'반려',설명:'원래 요청',
      희망반영:[{희망id:'희망-1',반영:'일부',이유:'일본어 관심 목록에 2025 3번(R154). 운영시간은 확인하지 못했습니다.'}]}]},
    ...overrides};
  const source=fs.readFileSync(path.join(__dirname,'담당자화면/plan.js'),'utf8').split('// ---------- 시작 ----------')[0];
  vm.runInNewContext(source+'\ndraw=()=>{};showRecord("stored",{},fixture);\n}',{document,fixture,console});
  return elements.get('main').innerHTML;
}

test('코스 제안과 동선을 먼저 보여 주고 버전·검사 원문은 접힌 팀 상세에 둔다',()=>{
  const html=render();
  assert.match(html,/코스 제안/);
  assert.ok(html.indexOf('동선 · 시간표')<html.indexOf('팀 검토용 상세'));
  assert.match(html,/<details[^>]*class="[^"]*technical/);
  assert.doesNotMatch(html,/<details[^>]*class="[^"]*technical[^>]*\bopen/);
  const basic=html.split('팀 검토용 상세')[0];
  assert.doesNotMatch(basic,/R154|검사 결과|4버전/);
  assert.match(basic,/2025년 관심 관광지 목록에 3회 등장/);
  assert.match(basic,/보완할 점/);
});

test('이전 수정본은 최신 검사 통과 상태로 표시하지 않는다',()=>{
  const html=render({버전:1,정리:{안:[{안id:'A',버전:4,버전들:[1,4],검증:'통과',희망반영:[]}]},
    분류:{AI수정:[],자료보완:[],사람결정:[]}});
  assert.match(html,/이전 수정본/);
  assert.doesNotMatch(html.split('팀 검토용 상세')[0],/초안 검토를 마쳤어요/);
});

test('관심 목록의 연도와 등장 횟수를 풀고 내부 근거 번호를 감춘다',()=>{
  const text=ui.문장('일본어 관심 목록에는 올라 있으나(R133 2024 2번, R154 2025 3번) 실제 방문 수는 아닙니다(W4).');
  assert.match(text,/2025년 관심 관광지 목록에 3회 등장/);
  assert.match(text,/실제 방문 수는 아닙니다/);
  assert.doesNotMatch(text,/R133|R154|W4/);
});

test('구체적 비율과 부정·한계는 바꾸지 않는다',()=>{
  const text=ui.문장('일본 응답 1.7%(R76)라 근거가 약합니다. 운영시간은 확인하지 못했습니다(S69).');
  assert.match(text,/1\.7%/);
  assert.match(text,/근거가 약합니다/);
  assert.match(text,/확인하지 못했습니다/);
  assert.doesNotMatch(text,/R76|S69/);
});

test('일정 내부 이름과 이동 초과를 담당자 문장으로 풀어 쓴다',()=>{
  assert.equal(ui.문장('밤-1에 야시장을 넣었습니다.'),'밤 일정에 야시장을 넣었습니다.');
  const notes=ui.보완요약({분류:{AI수정:[{문구:'김광석길에서 평화시장까지 대중교통 39분으로 상한 30분을 넘는다.'}],자료보완:[]}});
  assert.match(notes[0],/39분/);
  assert.match(notes[0],/30분/);
  assert.doesNotMatch(notes[0],/AI|검증|R\d+/);
});

test('시간 범위 밖과 지역 미확인을 지역 위반으로 단정하지 않는다',()=>{
  const notes=ui.보완요약({분류:{AI수정:[{문구:'일정이 시작·종료 범위 밖입니다.'}],
    자료보완:[{문구:'필수 조건 지역 미확인: 소속 지역 자료 부족'}]}});
  assert.ok(!notes.some(text=>text.includes('지역 밖')));
});

test('반복된 시작·종료 검사와 일차 선택을 한 개의 담당자 할 일로 묶는다',()=>{
  const result=ui.할일({분류:{사람결정:[
    {문구:'시작 장소 담당자 입력 대기'}, {문구:'종료 시각 입력 대기'},
    {문구:'확정조건 미충족: 시작종료확정'}, {문구:'2일차 오전은 담당자가 선택한 값이어야 함'}]},
    요약:{확인할것:['좌표 미확인: 김광석길','숙박 시간 미정']}});
  assert.equal(result.filter(x=>x.제목==='여행의 시작과 끝').length,1);
  assert.ok(result.some(x=>x.제목==='둘째 날 오전'));
  assert.ok(result.some(x=>x.제목==='숙박 일정'));
  assert.doesNotMatch(JSON.stringify(result),/좌표|확정조건|2일차|칸ID/);
});

test('검사가 없거나 보완이 남았으면 문제 없는 코스라고 추천하지 않는다',()=>{
  assert.equal(ui.상태({검사함:false,분류:{},검증:'통과'}).종류,'대기');
  assert.equal(ui.상태({검사함:true,분류:{AI수정:[{문구:'이동 초과'}]},검증:'통과'}).종류,'보완');
  assert.equal(ui.상태({검사함:true,분류:{},검증:'검증 전'}).종류,'대기');
  const result=ui.상태({검사함:true,분류:{},검증:'통과'});
  assert.equal(result.종류,'확인');
  assert.doesNotMatch(result.제목,/확정|판매 가능/);
});

test('이해할 수 없는 내부 항목은 긴 원문 대신 확인 안내를 남긴다',()=>{
  const result=ui.할일({분류:{사람결정:[{문구:"('공통', None) 참조를 확인"}]},요약:{확인할것:[]}});
  assert.equal(result.length,1);
  assert.doesNotMatch(JSON.stringify(result),/None|공통/);
});

test('운영 입력 화면으로 보내지 않고 자율 이용과 없는 B안을 설명한다',()=>{
  const html=render();
  assert.match(html,/A안 · 내 요청을 우선한 안/);
  assert.match(html,/B안 · 구성을 조정한 안/);
  assert.match(html,/아직 없음/);
  assert.match(html,/어디까지 자유롭게 이용하나요/);
  assert.match(html,/예약이나 이용권에 실제로 정해진 시간/);
  assert.doesNotMatch(html,/코스 수정 화면|href=["'][^"']*admin\/(?:course|edit)/);
  assert.doesNotMatch(html.split('팀 검토용 상세')[0],/href=["'][^"']*admin/);
});

test('저장된 실제 B안은 미생성 안내 대신 비교 카드로 표시한다',()=>{
  const html=render({정리:{안:[
    {안id:'A',버전:1,버전들:[1],검증:'검증 전'},
    {안id:'B',버전:1,버전들:[1],검증:'검증 전',설명:'이동을 줄인 구성'}]}});
  assert.match(html,/B안 · 구성을 조정한 안/);
  assert.doesNotMatch(html,/missing-plan/);
});
