const {test}=require('node:test');
const assert=require('node:assert/strict');
const UI=require('../담당자화면/map-model.js');

test('표시 동선은 작은 횡단 꺾임을 줄이되 출발·도착과 큰 회전을 보존한다',()=>{
  const ll=(x,y)=>[35.87+y/111320,128.59+x/(111320*Math.cos(35.87*Math.PI/180))];
  const points=[[0,0],[30,0],[30,1.5],[45,1.5],[45,0],[100,0],[100,80],[100,100]].map(p=>ll(...p));
  const before=JSON.stringify(points),path=UI.simplifyPath(points);
  assert.ok(path.length<points.length);assert.deepEqual(path,[points[0],points[5],points[7]]);
  assert.equal(JSON.stringify(points),before);assert.notEqual(path[0],points[0]);
  const loop=[[0,0],[100,0],[100,100],[0,100],[0,0]].map(p=>ll(...p));
  assert.equal(UI.simplifyPath(loop).length,5);
});

test('그리는 선과 캐릭터가 쓸 동선만 정리하고 원본 이동시간·거리는 보존한다',()=>{
  const points=[[35.86,128.6],[35.86001,128.6003],[35.86,128.6006],[35.86,128.601]];
  const data=UI.model([{일차:1,좌표:points[0]},{일차:1,좌표:points.at(-1)}]);
  const cache={routes:{[UI.routeKey(points[0],points.at(-1))]:{profile:'foot',points,durationSeconds:720,distance:950}}};
  const before=JSON.stringify(cache),leg=UI.routesFor(data,cache).legs[0];
  assert.equal(leg.path.length,2);assert.equal(leg.durationSeconds,720);assert.equal(leg.distance,950);
  const motion=UI.track(leg.path);
  assert.deepEqual(UI.sample(motion,0).point,leg.path[0]);assert.deepEqual(UI.sample(motion,1).point,leg.path.at(-1));
  assert.equal(JSON.stringify(cache),before);
});

test('도로에서 벗어날 정도로 굽이를 직선화하지 않는다',()=>{
  const ll=(x,y)=>[35.87+y/111320,128.59+x/(111320*Math.cos(35.87*Math.PI/180))];
  const road=[[0,0],[20,8],[40,10],[60,8],[80,0]].map(p=>ll(...p));
  assert.ok(UI.simplifyPath(road).length>=3);
});

test('보완한 바닥 보행길과 선·캐릭터는 같은 경로를 쓰고 대중교통은 제외한다',()=>{
  const origin={lat:35,lon:128,kx:100000,ky:100000};
  const path=[[35,128],[35.001,128],[35.001,128.001]];
  const routed={legs:[{canWalk:true,path},{canWalk:false,path:null}]};
  const before=JSON.stringify(routed),rows=UI.walkingRoadRows(routed,origin);
  assert.equal(rows.length,1);assert.equal(rows[0].length,path.length);
  assert.deepEqual(rows[0],path.map(p=>[(p[1]-origin.lon)*origin.kx,(p[0]-origin.lat)*origin.ky]));
  assert.equal(JSON.stringify(routed),before);
});

test('정면 걷기는 두 캐릭터의 원본 정면 모션 시선을 같은 쪽으로 맞춘다',()=>{
  const raccoon=UI.characterMotion('raccoon',1,0,0,'front');
  const weasel=UI.characterMotion('weasel',-1,0,0,'front');
  assert.equal(raccoon.view,'front');assert.equal(weasel.view,'front');
  assert.equal(raccoon.flip,false);assert.equal(weasel.flip,true);
  assert.equal(UI.characterMotion('raccoon',0,-1,0,'follow').view,'back');
});

test('대중교통 구간은 걷기 재생용 path는 비우고, 지도 표시용 도로 선(roadPath)만 붙인다',()=>{
  const data=UI.model([{일차:1,좌표:[35.86,128.6],다음이동:{도보분:60,대중교통분:39,노선:'401',확인일:'2026-11-19'}},{일차:1,좌표:[35.88,128.62]}]);
  const cache={routes:{[UI.routeKey(data.entries[0].point,data.entries[1].point)]:{profile:'foot',points:[[35.86,128.6],[35.88,128.62]],durationSeconds:3600}}};
  const before=JSON.stringify(data),result=UI.routesFor(data,cache);
  assert.equal(result.legs[0].mode,'transit');assert.equal(result.legs[0].durationSeconds,2340);
  assert.equal(result.legs[0].path,null);assert.equal(result.legs[0].canWalk,false);
  assert.deepEqual(result.legs[0].roadPath,[[35.86,128.6],[35.88,128.62]]);   // 사용자 결정(11/26): 버스 구간도 도로 선으로 보여 준다
  assert.equal(UI.routesFor(data,{}).legs[0].mode,'transit');
  assert.equal(UI.routesFor(data,{}).legs[0].roadPath,null);
  assert.match(UI.legTimeLabel(result.legs[0]),/대중교통.*39분/);
  assert.equal(JSON.stringify(data),before);
});

test('짧은 도보는 도보로 표시하고 다른 교통 시간도 함께 남긴다',()=>{
  const info=UI.travelInfo({도보분:17,대중교통분:11,노선:'232 / 402'},720);
  assert.equal(info.mode,'foot');assert.equal(info.walkSeconds,720);assert.equal(info.transitSeconds,660);
  assert.match(UI.legTimeLabel(info),/도보.*12분/);
  assert.equal(UI.travelInfo(null,720).transitSeconds,null);
});

test('전체 재생은 대중교통에서 기다리며 명시적 도착지 이동 후 도보를 이어간다',()=>{
  const stops=[1,2,3,4].map(순번=>({순번,일차:1}));
  const p=UI.playback([{from:stops[0],to:stops[1],mode:'foot'},{from:stops[1],to:stops[2],mode:'transit'},{from:stops[2],to:stops[3],mode:'foot'}]);
  p.startAll();p.advance(1);assert.equal(p.state.waiting,true);
  assert.equal(p.advance(100),null);assert.equal(p.state.progress,0);assert.equal(p.state.index,1);
  p.pause();assert.equal(p.confirmTransit().arrived.순번,3);assert.equal(p.state.playing,true);assert.equal(p.state.waiting,false);assert.equal(p.state.index,2);
  assert.equal(p.advance(1).done,true);
});

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

test('지도 경로가 없어도 이동표 시간이 있으면 시간을 보여 준다', () => {
  const m = require('../담당자화면/map-model.js');
  assert.equal(m.tableLabel({도보분: 14, 대중교통분: 9}), '도보 약 14분 · 지도 경로 준비 중');
  assert.equal(m.tableLabel({도보분: 32, 대중교통분: 21}), '대중교통 약 21분 · 지도 경로 준비 중');
  assert.equal(m.tableLabel(null), null);
  assert.equal(m.tableLabel({}), null);
});

test('홍보 화면도 포롱이·여울이를 너구리·족제비 그림으로 바꾼다', () => {
  const promo = require('../담당자화면/promo.js');
  assert.equal(promo.캐릭터('포롱이'), '너구리');
  assert.equal(promo.캐릭터('여울이'), '족제비');
  assert.equal(promo.캐릭터('너구리'), '너구리');
  assert.equal(promo.캐릭터('동등'), null);
  assert.equal(promo.그림('여울이'), 'weasel');
});

test('다음 일정이 위치 없는 숙소면 경로 미확인 대신 숙소를 정하면 안내한다고 쓴다', () => {
  const m = require('../담당자화면/map-model.js');
  assert.equal(m.legFallbackLabel({다음이동: null}, {시간칸: '숙박', 좌표: null}), '숙소를 정하면 이동 안내');
  assert.equal(m.legFallbackLabel({다음이동: {도보분: 14, 대중교통분: 9}}, {시간칸: '낮', 좌표: [35.8, 128.5]}), '도보 약 14분 · 지도 경로 준비 중');
  assert.equal(m.legFallbackLabel({다음이동: null}, {시간칸: '낮', 좌표: null}), '경로 미확인');
});

test('대중교통 구간은 두 장소 사이를 점선 조각으로 잇는다', () => {
  const m = require('../담당자화면/map-model.js');
  const rows = m.dashRows([0, 0], [100, 0], 10, 6);
  assert.ok(rows.length >= 6 && rows.length <= 7);
  assert.deepEqual(rows[0], [[0, 0], [10, 0]]);
  assert.ok(rows.every(r => r.length === 2 && r[1][0] <= 100));
  assert.deepEqual(m.dashRows([0, 0], [0, 0], 10, 6), []);
});

test('도로 선이 있는 대중교통 구간은 기다리지 않고 버스로 타고 가는 구간으로 재생한다', () => {
  const m = require('../담당자화면/map-model.js');
  const s = [1, 2, 3, 4].map(순번 => ({순번, 일차: 1}));
  const road = [[35.86, 128.6], [35.87, 128.61]];
  const legs = m.playableLegs([
    {from: s[0], to: s[1], mode: 'foot', canWalk: true, path: road},
    {from: s[1], to: s[2], mode: 'transit', canWalk: false, path: null, roadPath: road, durationSeconds: 1020},
    {from: s[2], to: s[3], mode: 'transit', canWalk: false, path: null, roadPath: null, durationSeconds: 600}]);
  assert.equal(legs[1].ride, true); assert.equal(legs[1].canWalk, true); assert.deepEqual(legs[1].path, road);
  assert.equal(legs[2].ride, undefined); assert.equal(legs[2].mode, 'transit');   // 도로 선이 없으면 예전처럼 안내만
  assert.match(m.legTimeLabel(legs[1]), /대중교통 약 17분/);
  const p = m.playback(legs); p.startAll(); p.advance(1);
  assert.equal(p.state.index, 1); assert.equal(p.state.waiting, false);   // 버스 구간에서 멈춰 기다리지 않는다
  p.advance(1); assert.equal(p.state.waiting, true);                     // 도로 선 없는 구간만 기다린다
});

test('목록에 넘기는 구간 정보(mode만 있음)도 버스 구간이면 대중교통 시간으로 쓴다', () => {
  const m = require('../담당자화면/map-model.js');
  assert.match(m.legTimeLabel({mode: 'ride', durationSeconds: 1200}), /대중교통 약 20분/);
});
