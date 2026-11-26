const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../담당자화면/plan.js');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');

test('입장 화면은 새 조건과 지난 코스 진입만 제공한다',()=>{
  const html=ui.입장화면();assert.match(html,/entryNew/);assert.match(html,/entrySaved/);
  assert.match(html,/AI 실행 없이/);assert.doesNotMatch(html,/type="submit"|\/api\/plan\/start/);
});

test('지난 코스는 고정 레일이 아닌 닫힌 부유 창이며 두 메뉴 형태가 같다',()=>{
  const html=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'담당자화면/index.html'),'utf8');
  assert.match(html,/class="history-panel"[^>]*hidden/);assert.match(html,/class="service-nav"/);
  assert.match(html,/>코스 기획<\/a>/);assert.match(html,/>서비스 운영 로그 ↗<\/a>/);
});

test('장소마다 배지를 반복하지 않고 위치 정보만 닫힌 상세에 둔다',()=>{
  const html=ui.위치안내({위치설명:'권역 대표 위치 · 관광센터 입구 아님',진입안내:'관광센터 기준, 입구 미확정',위치근거URL:'https://example.org/proof',지도링크:'https://map.kakao.com/link/map/x'});
  assert.doesNotMatch(html,/location-badge/);
  assert.match(html,/<details class="location-info"><summary>위치 정보<\/summary>/);
  assert.doesNotMatch(html,/<details[^>]*\bopen/);
  assert.doesNotMatch(html.split('<details')[0],/관광센터|kakao|위치 근거/);
});

test('비교 화면에는 큰 지도 진입 버튼을 두고 지도를 함께 렌더링하지 않는다',()=>{
  const html=render();
  assert.match(html,/id="openMap"/);assert.match(html,/지도 크게 보기/);
  assert.doesNotMatch(html,/id="mapbox"|id="timeline"/);
  assert.ok(html.indexOf('id="openMap"')<html.indexOf('plan-choices'));
  assert.match(html,/<section class="card freedom">/);
  assert.match(html,/<section class="card request-card">/);
});

test('장소 설명과 후보는 선택한 장소 패널에서만 보여 준다',()=>{
  const html=ui.장소패널({순번:5,표시명:'서문시장 야시장',장소안내:{소개:'저녁 시장 구간',이용시간:'19:00-23:00',휴무:'월~목',출처URL:'https://example.org'},식당후보:[]});
  assert.match(html,/서문시장 야시장/);assert.match(html,/저녁 시장 구간/);
  assert.match(html,/보유 자료 기준/);assert.doesNotMatch(html,/location-badge/);
});

test('왼쪽 일정 선택은 지도 이동과 오른쪽 설명을 함께 갱신하고 지도 선택은 되먹임하지 않는다',()=>{
  const calls=[],pressed={};let closedFocus=false;
  const close={},button={dataset:{stop:'5'},setAttribute:(key,value)=>pressed[key]=value,focus:()=>closedFocus=true};
  const view={classList:{add(){},remove(){}},querySelectorAll:()=>[button],querySelector:()=>button};
  const panel={hidden:true,innerHTML:'',querySelector:()=>close,querySelectorAll:()=>[]};
  const document={getElementById:id=>id==='mapView'?view:panel};
  const fixture=[{순번:5,표시명:'서문시장 야시장',일차:1,좌표:[35.86,128.58],장소안내:{소개:'야시장 설명'}}];
  const source=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'담당자화면/plan.js'),'utf8').split('// ---------- 시작 ----------')[0];
  vm.runInNewContext(source+'\nexplorerStops=fixture;mapController={selectStop:(...x)=>calls.push(x)};selectStop(5);selectStop(5,true);\n}',{document,fixture,calls,console});
  assert.equal(calls.length,1);assert.equal(calls[0][0],5);assert.equal(calls[0][1].notify,false);
  assert.equal(panel.hidden,false);assert.match(panel.innerHTML,/야시장 설명/);assert.equal(pressed['aria-pressed'],'true');
  close.onclick();assert.equal(panel.hidden,true);assert.equal(closedFocus,true);
});

test('큰 지도는 별도 보기를 열고 돌아가면 원래 화면의 초점과 입력을 복구한다',()=>{
  const elements=new Map(),calls=[];
  const original={isConnected:true,focus:()=>calls.push('focus')},wrap={inert:false},header={inert:false};
  const make=()=>({hidden:true,setAttribute(){},addEventListener(){},classList:{add(){},remove(){}},focus(){},querySelectorAll:()=>[],innerHTML:''});
  const document={activeElement:original,createElement:make,getElementById:id=>elements.get(id),querySelector:selector=>selector==='.wrap'?wrap:header,
    body:{classList:{add(){},remove(){}},append:view=>elements.set(view.id,view)}};
  elements.set('backCompare',make());elements.set('openMap',original);
  const result={};const source=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'담당자화면/plan.js'),'utf8').split('// ---------- 시작 ----------')[0];
  vm.runInNewContext(source+'\ndraw=()=>{mapController={destroy:()=>calls.push("destroy")}};openMap([{일차:1,표시명:"야시장"}]);result.html=document.getElementById("mapView").innerHTML;result.open=!document.getElementById("mapView").hidden;result.inert=wrap.inert;closeMap();result.closed=document.getElementById("mapView").hidden;\n}',{document,result,calls,wrap,console});
  assert.equal(result.open,true);assert.equal(result.inert,true);assert.equal(result.closed,true);assert.equal(wrap.inert,false);
  assert.deepEqual(calls,['destroy','focus']);assert.equal((result.html.match(/시설·권역의 대표 위치/g)||[]).length,1);
  assert.match(result.html,/class="explorer-list"/);assert.match(result.html,/id="placePanel"[^>]*hidden/);
});

test('식당 후보는 지도에 표시하되 방문 연결선에는 넣지 않는다',()=>{
  const {model}=require('../담당자화면/map-model.js');
  const input=[
    {순번:1,일차:1,시간칸:'낮',표시명:'관광A',좌표:[35.86,128.58]},
    {순번:2,일차:1,시간칸:'점심',표시명:'자유식',좌표:null,식당후보:[{이름:'후보식당',좌표:[35.87,128.60]}]},
    {순번:3,일차:1,시간칸:'낮',표시명:'관광B',좌표:[35.86,128.59]}];
  const data=model(input);
  assert.equal(data.areas[0].candidates[0].이름,'후보식당');
  assert.equal(data.entries.length,3);
  assert.equal(data.entries.filter(s=>s.표시명==='후보식당').length,0);
});

function render(overrides={}){
  const elements=new Map();
  const document={getElementById(id){if(!elements.has(id))elements.set(id,{innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null});return elements.get(id);}};
  const fixture={안id:'A',버전:4,시간칸:['저녁'],요약:{일정:[],코스있음:true,확인할것:[],출발가능요일:null},
    원래요청:{희망:[{id:'희망-1',내용:'야경을 넣고 싶어요'}]},검사함:true,
    분류:{AI수정:[{문구:'저녁-1: 이동시간 39분 초과',출처:'검증'}],자료보완:[],사람결정:[]},
    정리:{안:[{안id:'A',버전:4,버전들:[1,2,3,4],검증:'반려',설명:'원래 요청',
      희망반영:[{희망id:'희망-1',반영:'일부',이유:'일본어 관심 목록에 2025 3번(R154). 운영시간은 확인하지 못했습니다.'}]}]},
    ...overrides};
  const source=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'담당자화면/plan.js'),'utf8').split('// ---------- 시작 ----------')[0];
  vm.runInNewContext(source+'\ndraw=()=>{};showRecord("stored",{},fixture);\n}',{document,fixture,console,코스편집:require('../담당자화면/편집.js')});
  return elements.get('main').innerHTML;
}

test('하루 시간표에서 저장된 시작·종료·체류시간을 함께 보여 준다',()=>{
  const html=render({요약:{코스있음:true,확인할것:[],일정:[{일차:1,시간칸:'낮',표시명:'관광지',시각:'10:00',종료시각:'11:00',종료일차:1,머무는시간:60}]}});
  assert.match(html,/10:00~11:00 · 60분/);
});

test('미정 시각은 추정하지 않고 날짜를 넘기는 종료는 다음 일차를 표시한다',()=>{
  const html=render({요약:{코스있음:true,확인할것:[],일정:[
    {일차:1,시간칸:'밤',표시명:'밤 방문',시각:'23:30',종료시각:'00:30',종료일차:2,머무는시간:60},
    {일차:2,시간칸:'낮',표시명:'시각 미정 방문',시각:'',종료시각:'',머무는시간:45}]}});
  assert.match(html,/23:30~2일차 00:30 · 60분/);
  assert.match(html,/시각 미정 · 45분/);
  assert.doesNotMatch(html,/undefined|NaN/);
});

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
  assert.match(html,/미생성/);
  assert.match(html,/어디까지 자유롭게 이용하나요/);
  assert.match(html,/예약이나 이용권에 실제로 정해진 시간/);
  assert.doesNotMatch(html,/코스 수정 화면|href=["'][^"']*admin\/(?:course|edit)/);
  assert.doesNotMatch(html.split('팀 검토용 상세')[0],/href=["'][^"']*admin/);
});

test('B안 미생성 이유와 가상 업로드 경고를 생략하거나 HTML로 실행하지 않는다',()=>{
  const reason='후보가 부족합니다. '+ '사유 '.repeat(80)+'<script>oops</script>';
  const html=render({정리:{안:[{안id:'A',버전:4,버전들:[4],검증:'검증 전'}],대안상태:{상태:'미생성',이유:reason}},
    기관업로드:{파일명:'가상.csv',적용행수:13,가상자료:true,경고:['실제 조사 아님']}});
  assert.match(html,/&lt;script&gt;oops&lt;\/script&gt;/);
  assert.match(html,/시연용 가상 자료 · 실제 조사 아님/);
  assert.match(html,/적용 13행/);
});

test('저장된 실제 B안은 미생성 안내 대신 비교 카드로 표시한다',()=>{
  const html=render({정리:{안:[
    {안id:'A',버전:1,버전들:[1],검증:'검증 전'},
    {안id:'B',버전:1,버전들:[1],검증:'검증 전',설명:'이동을 줄인 구성'}]}});
  assert.match(html,/B안 · 구성을 조정한 안/);
  assert.doesNotMatch(html,/missing-plan/);
});

test('장소 설명에 위치 신고 양식이 있다', () => {
  const html = ui.장소패널({순번: 2, 장소명: '대구광역시 중구 김광석길', 표시명: '중구 김광석길', 장소안내: {}, 식당후보: []});
  assert.match(html, /위치가 이상해요/);
  assert.match(html, /data-place-report/);
  assert.match(html, /maxlength="300"/);
});
