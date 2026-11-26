// 브라우저 권한 없이 폼 직렬화와 비동기 버튼 상태를 검증한다. 실제 화면 렌더 시험은 아님.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
function setup(){
  const nodes=new Map(),values={};
  const node=id=>{if(!nodes.has(id))nodes.set(id,{disabled:false,textContent:'',replaceChildren(){},addEventListener(){},elements:{namedItem:name=>({value:values[name] || ''})}});return nodes.get(id);};
  const context=vm.createContext({document:{getElementById:node},$:node,clearTimeout(){},setTimeout(){return 1;},JSON});
  vm.runInContext(fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면/코스조건.js'),'utf8'),context);
  return {context,values,node,nodes,run:code=>vm.runInContext(code,context)};
}
test('실제 폼 생성 코드가 시작·종료 그룹을 나누고 선택한 일차를 다시 읽음',()=>{
  const x=setup();
  const make=(tag,text,cls)=>{
    let value='';
    const n={tag,text,cls,children:[],disabled:false,append(...items){this.children.push(...items);},replaceChildren(){this.children=[];},setAttribute(){},addEventListener(){}};
    Object.defineProperty(n,'id',{set(id){x.nodes.set(id,n);},get(){return '';}});
    Object.defineProperty(n,'value',{set(v){value=String(v);},get(){return value;}});
    return n;
  };
  for(const id of ['courseInputs','mealInputs']){const n=x.node(id);n.children=[];n.append=(...items)=>n.children.push(...items);n.replaceChildren=()=>{n.children=[];};}
  x.context.el=make;
  x.node('courseForm').elements.namedItem=name=>[...x.nodes.values()].find(n=>n.name===name);
  x.run("courseState.duration='1박2일';buildCourseForm('1박2일')");
  const anchors=x.node('courseInputs').children[0];
  assert.equal(anchors.children.length,2);
  assert.equal(anchors.children[0].children[0].text,'전체 여행 시작');
  assert.equal(anchors.children[1].children[0].text,'전체 여행 종료');
  assert.deepEqual(anchors.children[0].children.slice(1).map(n=>n.children[1].name),['시작일차','시작지점','시작시각']);
  x.context.sample={시작일차:1,종료일차:2,시작시각:'11:34',종료시각:'21:34',식사목록:[]};
  x.run('fillCourseForm(sample)');
  assert.equal(x.run('readCourseForm().시작일차'),1);assert.equal(x.run('readCourseForm().종료일차'),2);
});
test('1박2일의 모든 식사와 미정 값을 입력 그대로 전송',()=>{
  const x=setup();x.values['meal-0-방식']='자유식';
  x.run("courseState.duration='1박2일';courseState.meals=[[1,'점심'],[1,'저녁'],[2,'점심']]");
  const value=JSON.parse(x.run('JSON.stringify(readCourseForm())'));
  assert.equal(value.시작지점,'');assert.equal(value.식사목록.length,3);assert.equal(value.식사목록[0].방식,'자유식');assert.equal(value.식사목록[0].식당,'');
});
test('조건 수정 후 이전 저장으로 AI를 시작할 수 없음',()=>{
  const x=setup();x.run("courseState.job={상태:'준비',시험id:'old'};courseEdited()");
  assert.equal(x.run('courseState.job'),null);assert.equal(x.node('courseStart').disabled,true);
});
test('조건을 바꿔도 선택한 기존 초안의 수동 반영 대상은 유지',()=>{
  const x=setup();x.values['시작일차']='1';x.values['종료일차']='2';x.run("courseState.baseJobId='original';courseState.job={상태:'담당자확인대기'};courseEdited()");
  assert.equal(x.run('courseState.baseJobId'),'original');assert.equal(x.node('courseApply').disabled,false);assert.equal(x.node('courseStart').disabled,true);
});
test('점심 미포함 선택을 자동 해석하지 않고 그대로 전송',()=>{
  const x=setup();x.values['2일차점심포함']='미포함';x.run("courseState.duration='1박2일';courseState.meals=[]");
  assert.equal(x.run("readCourseForm()['2일차점심포함']"),'미포함');
});
test('일차 선택은 숫자로 보내고 미정 일차를 임의 지정하지 않음',()=>{
  const x=setup();x.values['시작일차']='1';x.values['종료일차']='2';
  x.run("courseState.duration='1박2일';courseState.meals=[]");
  assert.equal(x.run('readCourseForm().시작일차'),1);assert.equal(x.run('readCourseForm().종료일차'),2);
  x.values['종료일차']='';assert.equal(x.run('readCourseForm().종료일차'),'미정');
});
test('수동 반영 버튼은 AI 시작 API를 호출하지 않음',async()=>{
  const x=setup();x.values['시작일차']='1';x.values['종료일차']='1';const calls=[];x.context.recordCall=(url,value)=>{calls.push(url);return {시험id:'new',상태:'담당자확인대기'};};
  x.run("courseState.baseJobId='old';courseState.recordId='record';courseState.duration='당일';courseState.meals=[];coursePost=async(url,value)=>recordCall(url,value);verifyCourseSaved=async()=>({});drawCourseStatus=()=>{};loadRecord=async()=>{};renderStages=()=>{};renderPanel=async()=>{};globalThis.state={}");
  await x.run('applyCourse()');assert.deepEqual(calls,['/api/course/apply']);assert.equal(x.run('courseState.baseJobId'),'new');
});
test('저장 후 재조회한 일차가 선택값과 다르면 성공으로 표시하지 않음',async()=>{
  const x=setup();x.context.api=async()=>({본문:JSON.stringify({시작일차:'미정',종료일차:2})});
  await assert.rejects(x.run("verifyCourseSaved({시험id:'test'},{시작일차:1,종료일차:2})"),/저장값이 선택값과 다릅니다/);
});
test('저장 요약은 명시적으로 읽은 일차·장소·시각을 표시',()=>{
  const x=setup();const text=x.run("courseSummaryText({시작일차:1,종료일차:2,시작지점:'시작A',종료지점:'종료B',시작시각:'11:34',종료시각:'21:34'})");
  assert.match(text,/시작: 1일차 · 시작A · 11:34/);assert.match(text,/종료: 2일차 · 종료B · 21:34/);
});
test('진행 설명 앞뒤의 단일 JSON 코드 블록으로 시간표를 읽음',()=>{
  const x=setup();x.context.source='지침을 읽었습니다.\n```json\n{"칸목록":[{"장소명":"근대골목"}]}\n```\n확인하세요.';
  assert.equal(x.run('readCourseJSON(source).칸목록[0].장소명'),'근대골목');
  x.context.source='```json\n{}\n```\n```json\n{}\n```';
  assert.throws(()=>x.run('readCourseJSON(source)'));
});
test('실제 저장된 3단계 결과를 읽어 시간표 표시 함수에 전달',()=>{
  const x=setup();const blocks=[];
  x.context.el=(tag,text,cls)=>({tag,text,cls});
  x.context.table=rows=>({tag:'table',rows});
  x.context.markdown=text=>({tag:'markdown',text});
  x.context.panel={append:(...nodes)=>blocks.push(...nodes)};
  x.context.source='자료를 확인하겠습니다.\n```json\n'+JSON.stringify({칸목록:[{일차:1,시간칸:'낮',장소명:'근대골목',시각:{값:'10:00',종류:'가정'},근거ID:['R01']}],식사목록:[],남은경고:[],미확인사항:[]})+'\n```';
  x.run('renderCourseResult(panel,source)');
  assert.ok(blocks.some(n=>n.tag==='table' && n.rows.some(r=>r.includes('근대골목'))));
  assert.ok(!blocks.some(n=>n.tag==='markdown'));
});
test('결과 보기에서 구조화 JSON 파일을 골라도 원문 대신 시간표로 렌더',async()=>{
  const x=setup();
  x.context.document.querySelectorAll=()=>[];
  for(const id of ['panel','fileSelect']) {const n=x.node(id);n.append=()=>{};n.replaceChildren=()=>{};}
  let code=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면/app.js'),'utf8');
  code=code.slice(0,code.indexOf("$('runSearch').addEventListener"));
  vm.runInContext(code,x.context);
  x.context.el=(tag,text)=>({tag,text});
  x.context.selected={이름:'3단계_구조화.json',경로:'run/round/job/3단계_구조화.json',단계:3};
  x.run("state.record={파일:[selected]};courseState.selectedJobId='run/round/job';state.stage=3;state.view='result';state.file=selected.경로;fileData=async()=>({이름:selected.이름,형식:'json',본문:'{\"칸목록\":[]}'});renderCourseResult=()=>{globalThis.rendered=true}");
  await x.run('renderPanel()');assert.equal(x.context.rendered,true);
});
test('시작 버튼 중복 클릭은 API 한 번만 호출',async()=>{
  const x=setup();let resolve,count=0;
  x.context.reply=new Promise(r=>resolve=r);x.context.countCall=()=>count++;
  x.run("courseState.job={상태:'준비',시험id:'one'};coursePost=async()=>{countCall();return reply};drawCourseStatus=()=>{}");
  const first=x.run('startCourse()');await x.run('startCourse()');
  assert.equal(count,1);assert.equal(x.node('courseStart').disabled,true);
  resolve({상태:'실행중'});await first;assert.equal(count,1);
});
test('저장 중 다른 실행을 선택하면 이전 응답으로 화면을 바꾸지 않음',async()=>{
  const x=setup();x.values['시작일차']='1';x.values['종료일차']='1';let resolve;
  x.context.reply=new Promise(r=>resolve=r);
  x.run("courseState.recordId='first';courseState.duration='당일';courseState.meals=[];coursePost=()=>reply");
  const pending=x.run('saveCourse({preventDefault(){}})');
  x.run("courseState.generation++;courseState.recordId='second';courseState.job=null;courseState.busy=false");
  resolve({상태:'준비',시험id:'first/job'});await pending;
  assert.equal(x.run('courseState.recordId'),'second');assert.equal(x.run('courseState.job'),null);
});
test('일차를 고르지 않았으면 수동 저장 요청을 보내지 않음',async()=>{
  const x=setup();const calls=[];x.context.post=()=>calls.push(1);
  x.run("courseState.baseJobId='old';courseState.meals=[];coursePost=async()=>post()");
  await x.run('applyCourse()');assert.equal(calls.length,0);assert.match(x.node('courseMessage').textContent,/일차/);
});
test('일차 미선택이어도 버튼은 클릭해 원인을 확인할 수 있음',()=>{
  const x=setup();x.run("courseState.baseJobId='saved';courseButtons()");
  assert.equal(x.node('courseApply').disabled,false);
});
test('서버 재시작의 만료 토큰은 새 토큰으로 한 번만 재시도',async()=>{
  const x=setup();let posts=0;
  x.context.api=async(path,options)=>{
    if(path==='/api/session')return {token:'new'};
    posts++;if(posts===1){const e=new Error('화면을 새로고침한 뒤 다시 저장하세요.');e.status=403;throw e;}
    assert.equal(options.headers['X-Admin-Token'],'new');return {saved:true};
  };
  x.run("courseState.token='old'");assert.equal((await x.run("coursePost('/api/course/apply',{})")).saved,true);assert.equal(posts,2);
});
test('전달 검사는 선택한 수정본 하나만 고름',()=>{
  const x=setup();x.context.document.querySelectorAll=()=>[];
  let code=fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면/app.js'),'utf8');code=code.slice(0,code.indexOf("$('runSearch').addEventListener"));vm.runInContext(code,x.context);
  x.run("state.stage=3;state.record={id:'run/round',파일:[{이름:'3단계_전달_검사.json',경로:'run/round/old/3단계_전달_검사.json'},{이름:'3단계_전달_검사.json',경로:'run/round/new/3단계_전달_검사.json'},{이름:'3단계_전달_준비.json',경로:'run/round/3단계_전달_준비.json'}]};courseState.selectedJobId='run/round/new'");
  const files=JSON.parse(x.run('JSON.stringify(selectedCheckFiles())'));assert.equal(files.length,1);assert.equal(files[0].경로,'run/round/new/3단계_전달_검사.json');
  x.run("courseState.selectedJobId='run/round/old'");assert.match(x.run('selectedCheckFiles()[0].경로'),/\/old\//);
  x.run('state.stage=2');assert.equal(x.run('selectedCheckFiles()[0].경로'),'run/round/3단계_전달_준비.json');
});
test('최신 저장본과 이전 저장본의 번호·저장 시각을 구분',()=>{
  const x=setup();x.run("courseState.history=[{시험id:'new',기록시각:'2026-11-23T00:18:46+09:00',상태:'담당자확인대기'},{시험id:'old',기록시각:'2026-11-22T23:53:20+09:00',상태:'담당자확인대기'}]");
  assert.match(x.run('revisionLabel(courseState.history[0])'),/최신 · 저장본 2/);
  assert.match(x.run('revisionLabel(courseState.history[1])'),/이전 · 저장본 1/);
  assert.match(x.run('revisionLabel(courseState.history[0])'),/2026/);
});
test('미정 초안은 사용자가 명시적으로 고르면 저장 가능',()=>{
  const x=setup();x.values['시작일차']='미정';x.values['종료일차']='미정';
  assert.doesNotThrow(()=>x.run('requireCourseDays()'));
  assert.equal(x.run('readCourseForm().시작일차'),'미정');
});
