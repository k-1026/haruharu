const {test}=require('node:test');
const assert=require('node:assert/strict');
const UI=require('./담당자화면/map-model.js');

test('걷기 미리보기는 거리 비례 속도로 진행하고 긴 구간을 24초에 압축하지 않는다',()=>{
  assert.equal(UI.previewSeconds(1000),40);
  assert.equal(UI.previewSeconds(4000),160);
  assert.equal(UI.previewSeconds(4000,4),40);
  assert.equal(UI.previewSeconds(0),8);
  assert.equal(UI.previewSeconds(null),30);
});

test('일정 시각을 보간하고 미정·역행 시각을 현재 시각으로 대체하지 않는다',()=>{
  assert.equal(UI.clockMinutes('18:30'),1110);assert.equal(UI.clockMinutes('25:00'),null);
  assert.equal(UI.clockMinutes('미정'),null);assert.equal(UI.clockMinutes(''),null);
  assert.equal(UI.courseMinutes({시각:'16:00'},{시각:'18:00'},.5),1020);
  assert.equal(UI.courseMinutes({시각:'23:00'},{시각:'01:00'},.5),1440);
  assert.equal(UI.courseMinutes({시각:'12:00'},{시각:'10:00'},.5),720);
  assert.equal(UI.courseMinutes({시각:''},{시각:'18:00'},.5),null);
});

test('지도 시간대는 일정 시각만 사용하며 오후·저녁은 연속적으로 전환한다',()=>{
  assert.equal(UI.sceneTime(12*60).night,0);assert.equal(UI.sceneTime(20*60).night,1);
  assert.ok(UI.sceneTime(18*60).night>0&&UI.sceneTime(18*60).night<1);
  assert.equal(UI.sceneTime(9*60).night,0);assert.equal(UI.sceneTime(0).night,1);
  assert.equal(UI.sceneTime(1440).night,1);assert.equal(UI.sceneTime(null).label,'시각 미정 · 낮 기준');
  assert.equal(UI.sceneTime(18*60).label,'18:00 · 저녁');
});

test('둥근 경로의 진행 거리도 캐릭터 누적 경로와 일치한다',()=>{
  const data=UI.roadStrip([[[0,0],[10,0],[10,30]]],1,{round:true});
  assert.equal(Math.max(...data.distances),40);assert.equal(Math.min(...data.distances),0);
  assert.equal(data.positions.length/3,data.distances.length);
  assert.ok(data.positions.length>36);assert.ok(data.normals.every(Number.isFinite));
});

test('도로 띠는 실제 꺾인 좌표를 유지하고 겹친 점에서도 유효한 폭을 갖는다',()=>{
  const mesh=UI.roadStrip([[[0,0],[0,0],[10,0],[10,10]]],.6);
  assert.equal(mesh.positions.length,36);assert.equal(mesh.normals.length,24);
  assert.ok(mesh.positions.every(Number.isFinite));assert.ok(mesh.normals.every(Number.isFinite));
  assert.deepEqual(mesh.positions.slice(0,3),[0,.6,0]);
  assert.deepEqual(mesh.positions.slice(-3),[10,.6,0]);
  assert.deepEqual(mesh.normals.slice(0,2),[0,1]);
  assert.deepEqual(mesh.normals.slice(-2),[1,0]);
});

test('도보 추정 시간과 미확인 값을 구분한다',()=>{
  assert.equal(UI.timeLabel(720),'도보 약 12분');assert.equal(UI.timeLabel(3660),'도보 약 1시간 1분');
  assert.equal(UI.timeLabel(null),'도보 시간 미확인');
});

test('전체 재생은 연속 구간을 끝까지, 구간 재생은 그 구간만 진행한다',()=>{
  const stops=[1,2,3].map(순번=>({순번,일차:1})),legs=[{from:stops[0],to:stops[1]},{from:stops[1],to:stops[2]}];
  const p=UI.playback(legs);p.startAll();assert.equal(p.advance(1).done,false);assert.equal(p.state.index,1);
  assert.equal(p.advance(1).done,true);assert.equal(p.state.playing,false);
  p.playLeg(1);assert.equal(p.advance(1).done,true);assert.equal(p.state.index,0);
  assert.equal(p.playLeg(99),false);
});

test('전체 재생도 경로 누락 구간을 가로질러 이어 걷지 않는다',()=>{
  const p=UI.playback([{from:{순번:1,일차:1},to:{순번:2,일차:1}},
    {from:{순번:4,일차:1},to:{순번:5,일차:1}}]);p.startAll();assert.equal(p.advance(1).gap,true);assert.equal(p.state.playing,false);
});

test('꺾인 경로의 누적 거리를 따라 이동하고 모퉁이를 직선으로 가로지르지 않는다',()=>{
  const track=UI.track([[0,0],[10,0],[10,30]]);
  assert.deepEqual(UI.sample(track,.5).point,[10,10]);
  assert.deepEqual(UI.sample(track,.5).direction,[0,1]);
  assert.deepEqual(UI.sample(track,1).point,[10,30]);
});

test('도보 캐시가 있는 구간만 그리고 실패 구간을 직선으로 대체하지 않는다',()=>{
  const model=UI.model([{일차:1,좌표:[35.86,128.6]},{일차:1,좌표:[35.861,128.601]},{일차:1,좌표:[35.862,128.601]}]);
  const cache={routes:{[UI.routeKey(model.entries[0].point,model.entries[1].point)]:
    {profile:'foot',points:[[35.86,128.6],[35.86,128.601],[35.861,128.601]]}}};
  const result=UI.routesFor(model,cache);
  assert.equal(result.legs.length,1);assert.equal(result.missing.length,1);
  assert.equal(result.legs[0].path.length,3);
});

test('캐릭터 모션은 카메라를 기준으로 정면·측면·후면을 고른다',()=>{
  assert.deepEqual(UI.motionView(0,1,0),{view:'front',flip:false});
  assert.equal(UI.motionView(0,-1,0).view,'back');
  assert.deepEqual(UI.motionView(1,0,0),{view:'side',flip:false});
  assert.deepEqual(UI.motionView(-1,0,0),{view:'side',flip:true});
  assert.equal(UI.motionView(1,0,Math.PI/2).view,'front');
});

test('현재 코스는 대표 권역을 이용해 6개 위치와 5구간을 표시한다',()=>{
  const data=UI.model([
    {일차:1,좌표:[35.86857,128.58339],위치유형:'권역대표점'},
    {일차:1,식사권역:true,권역표시:{중심:[35.86888,128.58076]},식당후보:[]},
    {일차:1,좌표:[35.86142,128.60746]},
    {일차:1,식사권역:true,권역표시:{중심:[35.88275,128.619]},식당후보:[]},
    {일차:1,좌표:[35.86888,128.58076],위치유형:'권역대표점'},
    {일차:1,시간칸:'숙박',좌표:[35.87017,128.59406],위치유형:'권역대표점'},
    {일차:2,시간칸:'2일차오전'}]);
  assert.equal(data.entries.filter(s=>s.point).length,6);assert.equal(data.legs.length,5);
  assert.equal(data.areas.length,2);assert.equal(data.entries[5].kind,'region');
  assert.equal(data.missing.length,1);assert.equal(data.legs.at(-1).to.순번,6);
});
test('미정 일정은 남기고 권역은 후보 위치의 참고 중심으로 표시한다',()=>{
  const input=[{순번:1,일차:1,표시명:'관광',좌표:[35.86,128.6]},
    {순번:2,일차:1,식사권역:true,식당후보:[{이름:'가게',좌표:[35.87,128.61]}]},
    {순번:3,일차:1,시간칸:'숙박',표시명:'숙소 미정'}];
  const before=JSON.stringify(input),data=UI.model(input);
  assert.equal(data.stops.length,3);assert.equal(data.areas.length,1);
  assert.deepEqual(data.areas[0].point,[35.87,128.61]);
  assert.equal(data.missing[0].표시명,'숙소 미정');assert.equal(JSON.stringify(input),before);
});
test('후보 미리보기는 코스 선택·동선을 바꾸지 않는다',()=>{
  const data=UI.model([{순번:1,식사권역:true,식당후보:[{이름:'식당',좌표:[35.87,128.6]}]}]);
  const before=JSON.stringify(data),result=UI.preview(data,1,0);
  assert.equal(result.이름,'식당');assert.equal(result.확정,false);assert.equal(JSON.stringify(data),before);
});
test('좌표 누락과 일차 경계를 실제 이동처럼 연결하지 않는다',()=>{
  const data=UI.model([{일차:1,좌표:[35.86,128.6]},{일차:1,표시명:'미확인'},
    {일차:1,좌표:[35.87,128.6]},{일차:2,좌표:[35.88,128.6]}]);
  assert.equal(data.legs.length,0);assert.equal(data.missing.length,1);
});
test('잘못된 좌표를 버리고 공식 권역 대표점을 후보와 구분한다',()=>{
  const data=UI.model([{좌표:[128,35]},{식사권역:true,권역표시:{중심:[35.86,128.58],근거:'공식 대표점'},식당후보:[]}]);
  assert.equal(data.places.length,0);assert.equal(data.areas[0].candidates.length,0);
  assert.deepEqual(data.areas[0].point,[35.86,128.58]);
});
