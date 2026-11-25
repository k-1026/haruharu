import * as THREE from './vendor/three/three.module.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const U=.08;
const ROUTE={ink:'#167F7B',edge:'#FFFCF4',ahead:'#A5CECA',transit:'#80619D'};
const routeDetails=legs=>legs.map(leg=>({from:leg.from.순번,to:leg.to.순번,mode:leg.mode,canWalk:leg.canWalk,
  durationSeconds:leg.durationSeconds,walkSeconds:leg.walkSeconds,transitSeconds:leg.transitSeconds,transport:leg.transport}));
function atmosphere(minutes){
  const time=globalThis.코스지도모델.sceneTime(minutes);
  const tint=(day,warm,night)=>new THREE.Color(day).lerp(new THREE.Color(warm),time.warm).lerp(new THREE.Color(night),time.night);
  return {...time,sky:tint('#DDECF1','#F3D3B5','#555F73'),ground:tint('#F1E8D9','#EBD4B9','#72727A'),park:tint('#D5DEBF','#D9D2AF','#7B887B'),water:tint('#BCD7DD','#B9CCCB','#849DA8')};
}
function journey(leg,progress,index,total){
  if(leg.mode==='transit'){
    const t=leg.transport||{},basis=[t.출처,t.기준요일,t.기준출발시각,t.확인일].filter(Boolean).join(' · ');
    return `<small>대중교통 이동 안내 ${index+1} / ${total}</small><strong>${esc(globalThis.코스지도모델.label(leg.from))} → ${esc(globalThis.코스지도모델.label(leg.to))}</strong><span>대중교통 약 ${Math.round(leg.durationSeconds/60)}분 · ${esc(t.노선||'노선 확인 필요')}</span><p class="transit-basis">${esc(basis)} 기준 자료</p><p class="transit-basis">실제 노선 경로는 미연결입니다. 걷기 없이 ‘도착지로 넘어가기’를 누르세요.</p>`;
  }
  const metres=Number.isFinite(leg.distance)?leg.distance:(leg.track?.total||0)/U;
  const remaining=Math.max(0,metres*(1-progress)),distance=remaining>=1000?(remaining/1000).toFixed(1)+'km':Math.round(remaining/10)*10+'m';
  return `<small>지금 걷는 구간 ${index+1} / ${total}</small><strong>${esc(globalThis.코스지도모델.label(leg.from))}<span aria-hidden="true"> → </span>${esc(globalThis.코스지도모델.label(leg.to))}</strong><span>${progress>=1?'도착했어요':`다음 장소까지 약 ${distance} · ${Math.floor(progress*100)}%`}<em>${esc(globalThis.코스지도모델.timeLabel(leg.durationSeconds))} 구간</em></span><progress max="1" value="${progress}" aria-label="현재 구간 진행"></progress>`;
}

async function loadRoutes(model){
  try{const response=await fetch('/plan/road-routes.json');if(!response.ok)throw Error();return globalThis.코스지도모델.routesFor(model,await response.json());}
  catch{return globalThis.코스지도모델.routesFor(model,{});}
}

async function roadFallback(host,model,routed,options={}){
  // GPU가 없는 환경에서도 실제 도로와 일정 위치는 남긴다.
  const response=await fetch('/plan/map-data.json');if(!response.ok)throw Error('도로 자료 없음');
  const geo=await response.json(),project=p=>[(p[1]-geo.origin.lon)*geo.origin.kx,-(p[0]-geo.origin.lat)*geo.origin.ky];
  const points=model.entries.filter(s=>s.point).map(s=>({...s,xy:project(s.point)}));
  const walkingRoads=globalThis.코스지도모델.walkingRoadRows(routed,geo.origin);
  const extent=[...points.map(s=>s.xy),...routed.legs.filter(leg=>leg.path).flatMap(leg=>leg.path.map(project))];
  const xs=extent.map(p=>p[0]),ys=extent.map(p=>p[1]);
  const left=xs.length?Math.min(...xs)-400:-2000,top=ys.length?Math.min(...ys)-400:-1500;
  const width=xs.length?Math.max(1000,Math.max(...xs)-left+400):4000,height=ys.length?Math.max(800,Math.max(...ys)-top+400):3000;
  const roads=(rows,color,width)=>`<g fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round">${(rows||[]).map(row=>`<polyline vector-effect="non-scaling-stroke" points="${row.map(p=>p[0]+','+(-p[1])).join(' ')}"/>`).join('')}</g>`;
  const routePaths=routed.legs.map(leg=>leg.canWalk?leg.path.map(p=>project(p).join(' ')).join(' L '):null);
  const transitLegs=routed.legs.filter(leg=>!leg.canWalk);
  const transitStroke=`<g fill="none" stroke="${ROUTE.transit}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">${transitLegs.filter(leg=>leg.roadPath).map(leg=>`<path vector-effect="non-scaling-stroke" d="M ${leg.roadPath.map(p=>project(p).join(' ')).join(' L ')}"/>`).join('')}</g><g fill="none" stroke="${ROUTE.transit}" stroke-width="3" stroke-dasharray="10 8" stroke-linecap="round">${transitLegs.filter(leg=>!leg.roadPath).map(leg=>`<path vector-effect="non-scaling-stroke" d="M ${project(leg.from.point).join(' ')} L ${project(leg.to.point).join(' ')}"/>`).join('')}</g>`;
  const routeStroke=(color,width,progress=false)=>`<g fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round">${routePaths.map((path,i)=>path?`<path ${progress?`data-flat-progress="${i}" pathLength="100" stroke-dasharray="100 100"`:''} vector-effect="non-scaling-stroke" d="M ${path}"/>`:'').join('')}</g>`;
  host.innerHTML=`<div class="map3d-tools"><button type="button" data-flat-play>전체 동선 재생</button><button type="button" data-flat-pause disabled>잠시 멈춤</button><button type="button" data-flat-transit-next hidden>도착지로 넘어가기</button><button type="button" data-flat-speed title="지도 미리보기 속도">속도 1×</button><button type="button" data-flat-home>전체 지도</button><button type="button" data-flat-follow>따라보기</button><span data-flat-clock title="코스 일정 시각 기준 분위기 · 실제 일몰 예측 아님"></span></div><p class="note" data-flat-status>청록은 걷기 · 보라는 버스·지하철(선은 도로 경로, 실제 노선과 다를 수 있음). 이 환경에서는 평면 지도로 표시합니다.</p>
    <svg class="map-road-fallback" viewBox="${left} ${top} ${width} ${height}" role="img" aria-label="코스 도로 지도">
    <rect data-flat-ground x="${left}" y="${top}" width="${width}" height="${height}" fill="#F1E8D9"/>
    ${roads(geo.minor,'#CBBEAB',2.5)}${roads(geo.minor,'#FFFCF5',1.3)}${roads(geo.walk,'#E8BB7A',1.5)}
    ${roads(geo.mid,'#AFA796',3.6)}${roads(geo.mid,'#FFF8ED',2.1)}${roads(geo.major,'#AD9D86',4.6)}${roads(geo.major,'#E5D9C5',3.1)}
    ${roads(walkingRoads,'#CBBEAB',16)}${roads(walkingRoads,'#FFFCF5',14)}
    ${transitStroke}${routeStroke(ROUTE.edge,11)}${routeStroke(ROUTE.ahead,6.5)}${routeStroke(ROUTE.ink,6.5,true)}
    ${points.map(s=>`<g data-map-stop="${s.순번}" role="button" tabindex="0" aria-label="${esc(globalThis.코스지도모델.label(s))} 설명 보기"><circle cx="${s.xy[0]}" cy="${s.xy[1]}" r="18" fill="${ROUTE.ink}" stroke="${ROUTE.edge}" stroke-width="4"/><text x="${s.xy[0]+27}" y="${s.xy[1]}" font-size="25" fill="#735335">${esc(s.순번+'. '+(s.kind==='area'?'[식사] ':'')+globalThis.코스지도모델.label(s))}</text></g>`).join('')}
    ${routed.legs.length?['raccoon','weasel'].map(type=>`<image data-flat-character="${type}" pointer-events="none" width="${width/13}" height="${width/10}" href="/plan/characters/transparent/${type}-front.png"/>`).join(''):''}</svg>
    <div class="map3d-hud" data-flat-journey></div><div data-fallback-areas>${model.areas.map(s=>`<button type="button" data-area="${s.순번}">${esc(globalThis.코스지도모델.label(s))} · 식당 후보</button>`).join('')}</div>
    <div class="map3d-detail" data-map-detail></div><p class="note">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · <a href="https://routing.openstreetmap.de/about.html" target="_blank" rel="noopener">FOSSGIS OSRM</a> · <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noopener">지도 수정 제보</a></p>`;
  const detail=host.querySelector('[data-map-detail]');
  function select(number){
    const area=model.areas.find(s=>s.순번===number);if(!area){detail.innerHTML='';return;}
    detail.innerHTML=`<b>${esc(globalThis.코스지도모델.label(area))}</b><p>자유식 후보이며 방문 확정이 아닙니다.</p>${area.candidates.length?area.candidates.map((c,i)=>`<p><button type="button" data-candidate="${i}">${esc(c.이름)} · 미리보기</button>${c.좌표?'':' · 좌표 확인 중'}</p>`).join(''):'<p>등록된 식당 후보가 없습니다.</p>'}`;
    detail.querySelectorAll('[data-candidate]').forEach(button=>button.onclick=()=>{
      const candidate=globalThis.코스지도모델.preview(model,number,Number(button.dataset.candidate));
    detail.textContent=candidate.이름+' · 후보 미리보기입니다. 코스와 확정 상태는 바뀌지 않았습니다.';
    });
  }
  host.querySelectorAll('[data-area]').forEach(button=>{
    button.onclick=()=>select(Number(button.dataset.area));
    button.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();button.click();}};
  });
  const svg=host.querySelector('svg');
  let sceneMinutes=globalThis.코스지도모델.clockMinutes(model.entries[0]?.시각);
  const progressPaths=new Map([...host.querySelectorAll('[data-flat-progress]')].map(p=>[Number(p.dataset.flatProgress),p]));
  function showTime(){const mood=atmosphere(sceneMinutes);host.querySelector('[data-flat-clock]').textContent=mood.label;
    host.querySelector('[data-flat-ground]').style.fill='#'+mood.ground.getHexString();svg.style.backgroundColor='#'+mood.ground.getHexString();}
  showTime();
  function focus(point){const [x,y]=project(point);svg.setAttribute('viewBox',`${x-600} ${y-450} 1200 900`);}
  function selectStop(number,{notify=true}={}){
    const item=model.entries.find(s=>s.순번===number);if(!item)return;
    player.pause();sync();next.hidden=true;if(item.point)focus(item.point);
    sceneMinutes=globalThis.코스지도모델.clockMinutes(item.시각);showTime();
    if(item.kind==='area')select(number);else detail.textContent=globalThis.코스지도모델.label(item);
    if(notify)options.onSelect?.(number);
  }
  host.querySelectorAll('[data-map-stop]').forEach(pin=>{
    pin.onclick=()=>selectStop(Number(pin.dataset.mapStop));
    pin.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectStop(Number(pin.dataset.mapStop));}};
  });
  const home=()=>svg.setAttribute('viewBox',`${left} ${top} ${width} ${height}`);
  host.querySelector('[data-flat-home]').onclick=home;
  function previewCandidate(number,index){
    const c=globalThis.코스지도모델.preview(model,number,index);if(!c)return;
    if(c.좌표)focus(c.좌표);options.onCandidate?.(number,index);
  }
  const tracks=routed.legs.map(leg=>leg.canWalk?globalThis.코스지도모델.track(leg.path.map(project)):null);
  const player=globalThis.코스지도모델.playback(routed.legs);
  const play=host.querySelector('[data-flat-play]'),pause=host.querySelector('[data-flat-pause]'),status=host.querySelector('[data-flat-status]'),next=host.querySelector('[data-flat-transit-next]'),hud=host.querySelector('[data-flat-journey]');play.disabled=!routed.legs.length;
  const sprites=[...host.querySelectorAll('[data-flat-character]')];
  let last=0,frame=0,dead=false,follow=false,playbackSpeed=1,shown=-1;
  function sync(){pause.disabled=player.state.finished||player.state.waiting||shown<0;pause.textContent=player.state.finished?'재생 완료':player.state.playing?'잠시 멈춤':'계속 재생';next.hidden=!player.state.waiting||shown!==player.state.index;}
  function place(sample){
    const size=follow?105:width/25;
    sprites.forEach((sprite,i)=>{sprite.setAttribute('width',size);sprite.setAttribute('height',size*1.35);sprite.setAttribute('x',sample.point[0]-size/2+(i?size*.48:-size*.48));sprite.setAttribute('y',sample.point[1]-size*1.3);
      const motion=globalThis.코스지도모델.characterMotion(sprite.dataset.flatCharacter,sample.direction[0],sample.direction[1],0,follow?'front':'overview');
      sprite.style.transformBox='fill-box';sprite.style.transformOrigin='center';sprite.style.transform=`scaleX(${motion.flip?-1:1})`;
      if(sprite.dataset.view!==motion.view){sprite.dataset.view=motion.view;sprite.setAttribute('href',`/plan/characters/transparent/${sprite.dataset.flatCharacter}-${motion.view}.png`);}});
    if(follow)svg.setAttribute('viewBox',`${sample.point[0]-600} ${sample.point[1]-450} 1200 900`);
  }
  sprites.forEach(sprite=>sprite.style.visibility='hidden');
  function enter(){const leg=routed.legs[player.state.index];shown=player.state.index;follow=leg.canWalk;
    status.textContent=globalThis.코스지도모델.label(leg.from)+' → '+globalThis.코스지도모델.label(leg.to)+' · '+globalThis.코스지도모델.legTimeLabel(leg);
    sprites.forEach(sprite=>sprite.style.visibility=leg.canWalk?'visible':'hidden');
    if(leg.canWalk)place(globalThis.코스지도모델.sample(tracks[shown],0));else home();
    sceneMinutes=globalThis.코스지도모델.courseMinutes(leg.from,leg.to,0);showTime();hud.innerHTML=journey(leg,0,shown,routed.legs.length);sync();options.onSelect?.(leg.from.순번,{playback:true});}
  function start(number=null){const ok=number===null?player.startAll():player.playLeg(number);if(!ok)return false;progressPaths.forEach(p=>p.style.visibility='hidden');enter();return true;}
  play.onclick=()=>start();pause.onclick=()=>{player.toggle();sync();};
  next.onclick=()=>{const leg=routed.legs[player.state.index],event=player.confirmTransit();if(!event)return;sceneMinutes=globalThis.코스지도모델.clockMinutes(leg.to.시각);showTime();focus(leg.to.point);hud.innerHTML=`<strong>${esc(globalThis.코스지도모델.label(leg.to))} 도착지 보기</strong>`;sync();options.onSelect?.(event.arrived.순번,{playback:!event.done});};
  host.querySelector('[data-flat-speed]').onclick=event=>{playbackSpeed=playbackSpeed===4?1:playbackSpeed*2;event.currentTarget.textContent=`속도 ${playbackSpeed}×`;};
  host.querySelector('[data-flat-home]').onclick=()=>{follow=false;home();};host.querySelector('[data-flat-follow]').onclick=()=>follow=true;
  function tick(now){if(dead)return;const dt=Math.min(.05,(now-last)/1000||0);last=now;
    if(player.state.playing&&shown!==player.state.index)enter();
    if(player.state.playing&&!player.state.waiting){const index=player.state.index,event=player.advance(dt/globalThis.코스지도모델.previewSeconds(tracks[index].total,playbackSpeed)),progress=event?1:player.state.progress;place(globalThis.코스지도모델.sample(tracks[index],progress));
      progressPaths.get(index).style.visibility='visible';progressPaths.get(index).style.strokeDashoffset=String((1-progress)*100);
      const leg=routed.legs[index];sceneMinutes=globalThis.코스지도모델.courseMinutes(leg.from,leg.to,progress);showTime();status.textContent=globalThis.코스지도모델.label(leg.from)+' → '+globalThis.코스지도모델.label(leg.to)+' · '+globalThis.코스지도모델.legTimeLabel(leg);hud.innerHTML=journey(leg,progress,index,routed.legs.length);
      if(player.state.waiting)sprites.forEach(sprite=>sprite.style.visibility='hidden');
      if(event){sync();options.onSelect?.(event.arrived.순번,{playback:!event.done});}}
    frame=requestAnimationFrame(tick);
  }
  frame=requestAnimationFrame(tick);
  return {select,selectStop,previewCandidate,playLeg:number=>start(number),routes:routeDetails(routed.legs),destroy(){dead=true;cancelAnimationFrame(frame);}};

}

export async function mount(host,stops,options={}){
  const model=globalThis.코스지도모델.model(stops),resources=[];
  const ticket={};host.routeMount=ticket;
  const routed=await loadRoutes(model);
  if(host.routeMount!==ticket)return {select(){},destroy(){}};
  host.innerHTML=`<div class="map3d-tools"><button type="button" data-play>전체 동선 재생</button><button type="button" data-pause disabled>잠시 멈춤</button><button type="button" data-transit-next hidden>도착지로 넘어가기</button><button type="button" data-speed title="지도 미리보기 속도 · 실제 소요시간과 별개">속도 1×</button><div class="camera-controls" aria-label="카메라 시점"><button type="button" data-home data-view="overview" aria-pressed="true">전체 지도</button><button type="button" data-view="follow" aria-pressed="false">따라보기</button><button type="button" data-view="front" aria-pressed="false">정면 가까이</button></div></div>
    <div class="map3d-stage"><canvas aria-label="도로와 식사 권역을 표시한 입체 지도"></canvas><div class="map3d-labels"></div><div class="map3d-clock" data-course-clock title="코스 일정 시각 기준 분위기 · 실제 일몰 예측 아님"></div><div class="map3d-hud" data-walk-hud role="status"></div></div>
    <p class="note" data-map-status role="status">도로 자료를 불러오는 중…</p><div class="map3d-detail" data-map-detail></div>
    <p class="note">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · <a href="https://routing.openstreetmap.de/about.html" target="_blank" rel="noopener">FOSSGIS OSRM</a> · <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noopener">지도 수정 제보</a></p>
    `;
  const stage=host.querySelector('.map3d-stage'),canvas=host.querySelector('canvas'),labels=host.querySelector('.map3d-labels');
  const status=host.querySelector('[data-map-status]'),detail=host.querySelector('[data-map-detail]');
  let renderer;
  try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});}
  catch{return roadFallback(host,model,routed,options);}
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
  const scene=new THREE.Scene();scene.background=new THREE.Color('#DDECF1');scene.fog=new THREE.Fog('#DDECF1',10000,20000);
  scene.add(new THREE.HemisphereLight('#ffffff','#ad9f82',2));
  const sun=new THREE.DirectionalLight('#fff1d0',2.2);sun.position.set(200,500,300);scene.add(sun);
  const camera=new THREE.PerspectiveCamera(42,1,1,20000),target=new THREE.Vector3();
  let azimuth=.1,elevation=.88,distance=500,dead=false,frame=0,selected=null,hasPlayed=false,last=0;
  const allPins=[],labelPins=[],strokeLayers=[],routeStrokes=[],terrainMaterials=[],completed=new Map(),candidateGroup=new THREE.Group();scene.add(candidateGroup);
  let sceneMinutes=globalThis.코스지도모델.clockMinutes(model.entries[0]?.시각);
  const clock=host.querySelector('[data-course-clock]');
  const material=color=>{const m=new THREE.MeshLambertMaterial({color});resources.push(m);return m;};
  const mesh=(geometry,mat,parent=scene)=>{resources.push(geometry);const x=new THREE.Mesh(geometry,mat);parent.add(x);return x;};
  let geo;
  try{const r=await fetch('/plan/map-data.json');if(!r.ok)throw Error();geo=await r.json();}
  catch{renderer.dispose();status.textContent='도로 자료를 불러오지 못했습니다. 일정과 식당 후보 목록은 계속 볼 수 있어요.';return {destroy(){},select(){}};}
  const project=p=>new THREE.Vector3((p[1]-geo.origin.lon)*geo.origin.kx*U,0,-(p[0]-geo.origin.lat)*geo.origin.ky*U);
  const legs=routed.legs.map(leg=>({...leg,track:leg.canWalk?globalThis.코스지도모델.track(leg.path.map(p=>{const v=project(p);return [v.x,v.z];})):null}));
  const player=globalThis.코스지도모델.playback(legs);
  let cameraMode='overview';const leadPos=new THREE.Vector3(),leadDir=new THREE.Vector3(0,0,1),cameraDir=new THREE.Vector3(0,0,1);
  let playbackSpeed=1,journeyKey='',arrivalHold=0,shownLeg=-1;
  const positions=[...model.entries.filter(s=>s.point).map(s=>project(s.point)),...legs.filter(leg=>leg.path).flatMap(leg=>leg.path.map(project))];
  const box=new THREE.Box3().setFromPoints(positions.length?positions:[new THREE.Vector3(-100,0,-100),new THREE.Vector3(100,0,100)]);
  box.getCenter(target);target.y=0;
  const size=new THREE.Vector3();box.getSize(size);
  const homeDistance=Math.max(280,Math.max(size.x,size.z)*1.5);distance=homeDistance;
  const viewTarget=target.clone();let viewDistance=distance;
  const roadBounds=new THREE.Box3().setFromPoints(['major','mid','minor','walk'].flatMap(k=>(geo[k]||[]).flatMap(row=>row.map(p=>new THREE.Vector3(p[0]*U,0,-p[1]*U)))));
  const floorSize=roadBounds.getSize(new THREE.Vector3()),floorCenter=roadBounds.getCenter(new THREE.Vector3());
  const floorMat=new THREE.MeshBasicMaterial({color:'#F1E8D9'});resources.push(floorMat);terrainMaterials.push({material:floorMat,kind:'ground'});
  const floor=mesh(new THREE.BoxGeometry(floorSize.x+100,8,floorSize.z+100),floorMat);floor.position.set(floorCenter.x,-4,floorCenter.z);
  function stroke(rows,color,layer,pixels,worldWidth=0,{round=false,cutoff=1e9}={}){
    // 높이를 쌓으면 가까운 카메라에서 도로와 동선이 분리된다. 같은 지면에서 표시 순서만 나눈다.
    const data=globalThis.코스지도모델.roadStrip(rows,.02,{round}),g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(data.positions,3));
    g.setAttribute('strokeNormal',new THREE.Float32BufferAttribute(data.normals,2));
    g.setAttribute('pathDistance',new THREE.Float32BufferAttribute(data.distances,1));
    const m=new THREE.ShaderMaterial({side:THREE.DoubleSide,depthWrite:false,fog:true,
      uniforms:THREE.UniformsUtils.merge([THREE.UniformsLib.fog,{ink:{value:new THREE.Color(color)},halfWidth:{value:.1},cutoff:{value:cutoff}}]),
      vertexShader:'#include <fog_pars_vertex>\n attribute vec2 strokeNormal; attribute float pathDistance; varying float vDistance; uniform float halfWidth; void main(){vDistance=pathDistance; vec3 p=position+vec3(strokeNormal.x,0.0,strokeNormal.y)*halfWidth; vec4 mvPosition=modelViewMatrix*vec4(p,1.0); gl_Position=projectionMatrix*mvPosition;\n #include <fog_vertex>\n }',
      fragmentShader:'#include <fog_pars_fragment>\n uniform vec3 ink; uniform float cutoff; varying float vDistance; void main(){if(vDistance>cutoff)discard; gl_FragColor=vec4(ink,1.0);\n #include <fog_fragment>\n #include <tonemapping_fragment>\n #include <colorspace_fragment>\n }'});
    resources.push(m);
    const object=mesh(g,m);object.frustumCulled=false;object.renderOrder=Math.round(layer*100);
    strokeLayers.push({material:m,pixels,worldWidth});return object;
  }
  function roads(collection,color,edge,y,width,pixels){
    const rows=(collection||[]).map(row=>row.map(p=>[p[0]*U,-p[1]*U]));
    stroke(rows,edge,y,pixels+1.5,width+.12);stroke(rows,color,y+.01,pixels,width);
  }
  function areas(collection,color,kind){
    const mat=new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide});resources.push(mat);terrainMaterials.push({material:mat,kind});
    for(const row of collection||[]){if(row.length<3)continue;const shape=new THREE.Shape(row.map(p=>new THREE.Vector2(p[0]*U,p[1]*U)));
      const polygon=mesh(new THREE.ShapeGeometry(shape),mat);polygon.rotation.x=-Math.PI/2;polygon.position.y=.01;
    }
  }
  areas(geo.park,'#D5DEBF','park');areas(geo.water,'#BCD7DD','water');
  roads(geo.river,'#BCD7DD','#A9C9D3',.2,1.4,2);
  roads(geo.rail,'#9B96A1','#D5CDBF',.3,.12,.7);
  roads(geo.minor,'#FFFCF5','#CBBEAB',.4,.26,1.3);
  roads(geo.walk,'#E8BB7A','#D2A35E',.5,.2,1.1);
  roads(geo.mid,'#FFF8ED','#AFA796',.6,.55,2.1);
  roads(geo.major,'#E5D9C5','#AD9D86',.7,.96,3.1);
  // 지도 벡터에서 생략된 보행 연결도 OSRM 도보 자료로 보완한다. 경로와 동일한 지면이다.
  roads(globalThis.코스지도모델.walkingRoadRows(routed,geo.origin),'#FFFCF5','#CBBEAB',.75,.55,14);
  function label(text,pos,callback,kind=''){
    const el=document.createElement('button');el.type='button';el.className='map3d-label '+kind;el.textContent=text;
    el.addEventListener('click',callback);labels.append(el);const offset=labelPins.filter(row=>row.pos.distanceTo(pos)<8).length*27;
    const row={el,pos,offset};labelPins.push(row);return row;
  }
  function candidatePreview(area,index){
    const c=globalThis.코스지도모델.preview(model,area.순번,index);if(!c)return;
    detail.innerHTML=`<b>${esc(c.이름)} · 후보 미리보기</b><p>아직 고른 식당이 아닙니다. 코스·선택·확정 상태는 바뀌지 않습니다.</p><button type="button" data-back>권역 후보로 돌아가기</button>`;
    detail.querySelector('[data-back]').onclick=()=>select(area.순번);
    if(c.좌표){target.copy(project(c.좌표));distance=Math.min(distance,220);}
    options.onCandidate?.(area.순번,index);
  }
  let candidateLabels=[];
  function clearCandidates(){
    candidateGroup.clear();for(const x of candidateLabels){x.el.remove();const i=labelPins.indexOf(x);if(i>=0)labelPins.splice(i,1);}candidateLabels=[];
  }
  function select(number){
    clearCandidates();selected=number;const area=model.areas.find(s=>s.순번===number);
    if(!area){detail.innerHTML='';return;}
    player.pause();syncPlayControls();
    detail.innerHTML=`<b>${esc(area.순번+'. '+globalThis.코스지도모델.label(area))}</b><p class="note">${esc(area.basis)}. 식당 후보 확인은 방문 확정이 아닙니다.</p>
      ${area.candidates.length?`<ul>${area.candidates.map((c,i)=>`<li><button type="button" data-candidate="${i}">${esc(c.이름)} · 미리보기</button>${c.좌표?'':' <small>좌표 확인 중</small>'}</li>`).join('')}</ul>`:'<p>등록된 식당 후보는 없습니다. 권역만 표시하며 특정 식당을 지정하지 않습니다.</p>'}
      <button type="button" data-close>후보 닫기</button>`;
    detail.querySelector('[data-close]').onclick=()=>select(null);
    detail.querySelectorAll('[data-candidate]').forEach(b=>b.onclick=()=>candidatePreview(area,Number(b.dataset.candidate)));
    for(const [i,c] of area.candidates.entries())if(c.좌표){
      const pos=project(c.좌표);
      candidateLabels.push(label(c.이름+' (후보)',pos.clone().setY(2),()=>candidatePreview(area,i),'candidate'));
    }
    if(area.point){target.copy(project(area.point));distance=Math.min(homeDistance,360);}
  }
  for(const item of model.entries)if(item.point){
    const pos=project(item.point),name=globalThis.코스지도모델.label(item);
    const row=label(`${item.순번}. ${name}`,pos.clone().setY(2),()=>selectStop(item.순번),'stop-marker '+item.kind+' slot-'+(item.시간칸==='저녁'?'eve':['밤','숙박'].includes(item.시간칸)?'night':'day'));
    row.el.setAttribute('aria-label',`${item.순번}. ${name}${item.kind==='area'?' · 식당 후보 보기':''}`);
    row.el.innerHTML=`<span class="map-stop-badge" aria-hidden="true">${item.순번}</span><span class="map-stop-name">${item.kind==='area'?'<span class="map-meal-tag">식사</span> ':''}${esc(name)}</span>`;
    row.number=item.순번;allPins.push(row);
  }
  function selectStop(number,{notify=true}={}){
    const item=model.entries.find(s=>s.순번===number);if(!item)return;
    player.pause();syncPlayControls();
    if(item.kind==='area')select(number);else{select(null);detail.textContent=globalThis.코스지도모델.label(item);}
    setView('overview');if(item.point){target.copy(project(item.point));distance=Math.min(homeDistance,210);}
    highlight(number);
    sceneMinutes=globalThis.코스지도모델.clockMinutes(item.시각);
    hud.textContent='';transitNext.hidden=true;
    if(notify)options.onSelect?.(number);
  }
  function highlight(number){for(const row of allPins)row.el.classList.toggle('is-focused',row.number===number);}
  function previewCandidate(number,index){const area=model.areas.find(s=>s.순번===number);if(area){select(number);candidatePreview(area,index);}}
  for(const [index,leg] of legs.entries()){
    if(!leg.canWalk){
      // 대중교통 구간: 노선 모양을 모르니 두 장소를 보라색 점선 직선으로만 잇는다.
      // 대중교통 구간: 같은 도로 위에 보라색 선으로. 도로 선이 없을 때만 두 장소를 점선 직선으로 잇는다.
      if(leg.roadPath){const rows=[leg.roadPath.map(p=>{const v=project(p);return [v.x,v.z];})];
        stroke(rows,ROUTE.edge,1.17,9,0,{round:true});stroke(rows,ROUTE.transit,1.18,5,0,{round:true});}
      else{const a=project(leg.from.point),b=project(leg.to.point);
        stroke(globalThis.코스지도모델.dashRows([a.x,a.z],[b.x,b.z],9,7),ROUTE.transit,1.18,3.2,0,{round:true});}
      const middle=project(leg.from.point).lerp(project(leg.to.point),.5).setY(3);
      const pin=label(globalThis.코스지도모델.legTimeLabel(leg),middle,()=>startPlayback(leg.from.순번),'travel-time transit');pin.routeFrom=leg.from.순번;continue;
    }
    const rows=[leg.path.map(p=>{const v=project(p);return [v.x,v.z];})];
    stroke(rows,ROUTE.edge,1.2,11,0,{round:true});stroke(rows,ROUTE.ahead,1.21,6.5,0,{round:true});
    const done=stroke(rows,ROUTE.ink,1.22,6.5,0,{round:true});routeStrokes.push({leg,done,index});
    const middle=globalThis.코스지도모델.sample(leg.track,.55);
    const timePin=label(globalThis.코스지도모델.legTimeLabel(leg),new THREE.Vector3(middle.point[0],3,middle.point[1]),()=>startPlayback(leg.from.순번),'travel-time foot');timePin.routeFrom=leg.from.순번;
  }
  function character(type){
    const group=new THREE.Group();scene.add(group);const body=material(type==='raccoon'?'#D58B4B':'#C98B58'),cream=material('#F6E7CB'),dark=material('#493126');
    const sphere=(r,x,y,z,mat)=>{const part=mesh(new THREE.SphereGeometry(r,12,10),mat,group);part.position.set(x,y,z);return part;};
    const trunk=sphere(3.2,0,5,0,body);trunk.scale.set(.85,1.25,.7);
    sphere(3.7,0,10,0,body);sphere(2.4,0,8.8,2,cream);
    sphere(1.15,-2.7,12.7,0,dark);sphere(1.15,2.7,12.7,0,dark);
    if(type==='raccoon'){sphere(1.15,-1.5,10,2.8,dark).scale.set(1.2,.65,.4);sphere(1.15,1.5,10,2.8,dark).scale.set(1.2,.65,.4);}
    sphere(.4,-1.3,10.2,3.4,dark);sphere(.4,1.3,10.2,3.4,dark);sphere(.55,0,9.2,4,dark);
    const legs=[sphere(1.2,-1.4,1.5,0,dark),sphere(1.2,1.4,1.5,0,dark)];
    const tail=sphere(1.8,0,4,-4,body);tail.scale.set(.8,1.8,1);tail.rotation.x=-.7;
    group.scale.setScalar(.16);return {group,legs};
  }
  const characters=[character('raccoon'),character('weasel')];
  // 원본 GIF와 별도로 만든 투명 APNG를 표시한다. 실제 리깅 모델과 구분한다.
  const motionSprites=characters.map((character,i)=>{
    const image=document.createElement('img');image.className='map3d-character';
    image.alt=i?'족제비':'너구리';image.draggable=false;
    const type=i?'weasel':'raccoon';
    const shadow=document.createElement('span');shadow.className='map-character-shadow';shadow.setAttribute('aria-hidden','true');labels.append(shadow);
    const row={image,shadow,type,view:'front',loaded:false};
    image.onload=()=>{row.loaded=true;character.group.visible=false;};
    image.onerror=()=>{row.loaded=false;image.hidden=true;character.group.visible=!!first;};
    labels.append(image);image.src=`/plan/characters/transparent/${type}-front.png`;
    return row;
  });
  const first=legs.find(leg=>leg.canWalk);for(const c of characters){c.group.visible=false;if(first)c.group.position.copy(project(first.path[0]));}
  let movement=new THREE.Vector3(0,0,1);
  const play=host.querySelector('[data-play]'),pause=host.querySelector('[data-pause]'),hud=host.querySelector('[data-walk-hud]'),transitNext=host.querySelector('[data-transit-next]');
  play.disabled=!legs.length;
  function syncPlayControls(){
    pause.disabled=!hasPlayed||player.state.finished||player.state.waiting;pause.textContent=player.state.finished?'재생 완료':player.state.playing?'잠시 멈춤':'계속 재생';
    transitNext.hidden=!player.state.waiting||shownLeg!==player.state.index;
    host.querySelectorAll('[data-view]').forEach(button=>button.disabled=player.state.waiting&&button.dataset.view!=='overview');
  }
  function setView(mode){
    cameraMode=mode;stage.dataset.camera=mode;
    scene.fog.near=mode==='overview'?10000:110;scene.fog.far=mode==='overview'?20000:650;
    host.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===mode)));
    if(mode==='overview'){box.getCenter(target);target.y=0;distance=homeDistance;azimuth=.1;elevation=.88;}
  }
  function enterLeg(){
    const leg=legs[player.state.index];shownLeg=player.state.index;hasPlayed=true;
    status.textContent=globalThis.코스지도모델.label(leg.from)+' → '+globalThis.코스지도모델.label(leg.to)+' · '+globalThis.코스지도모델.legTimeLabel(leg);
    highlight(leg.from.순번);options.onSelect?.(leg.from.순번,{playback:true});sceneMinutes=globalThis.코스지도모델.courseMinutes(leg.from,leg.to,0);
    journeyKey='';hud.innerHTML=journey(leg,0,player.state.index,legs.length);
    if(!leg.canWalk){
      setView('overview');const a=project(leg.from.point),b=project(leg.to.point);target.copy(a).lerp(b,.5);distance=Math.max(200,a.distanceTo(b)*1.7);leadPos.copy(a);syncPlayControls();return;
    }
    const sample=globalThis.코스지도모델.sample(leg.track,0);leadPos.copy(project(leg.path[0]));
    leadDir.set(sample.direction[0],0,sample.direction[1]);cameraDir.copy(leadDir);
    setView(cameraMode==='overview'?'front':cameraMode);
    // 재생 첫 순간부터 가까운 시점으로 두어 먼 지도에서 줌인하느라 구간이 끝나지 않게 한다.
    viewTarget.copy(leadPos).addScaledVector(cameraDir,cameraMode==='front'?-10:18).y=2.5;
    camera.position.copy(leadPos).addScaledVector(cameraDir,cameraMode==='front'?20:-32);camera.position.y=cameraMode==='front'?8.5:12;camera.lookAt(viewTarget);camera.updateMatrixWorld();
    syncPlayControls();
  }
  function startPlayback(number=null){
    const ok=number===null?player.startAll():player.playLeg(number);if(!ok)return false;
    completed.clear();arrivalHold=0;enterLeg();return true;
  }
  function arrived(event){
    if(!event)return;if(!event.done)arrivalHold=2.5;
    highlight(event.arrived.순번);options.onSelect?.(event.arrived.순번,{playback:!event.done});syncPlayControls();
    status.textContent=event.gap?'경로가 없는 구간은 자동으로 건너 걷지 않습니다. 다음 구간을 직접 선택해 주세요.':globalThis.코스지도모델.label(event.arrived)+(event.done?' 도착 · 재생 완료':' 도착 · 잠시 후 다음 구간');
  }
  play.onclick=()=>startPlayback();pause.onclick=()=>{player.toggle();syncPlayControls();};
  transitNext.onclick=()=>{
    const leg=legs[player.state.index],event=player.confirmTransit();if(!event)return;
    sceneMinutes=globalThis.코스지도모델.clockMinutes(leg.to.시각);target.copy(project(leg.to.point));leadPos.copy(target);distance=210;
    hud.innerHTML=`<small>대중교통 안내 확인</small><strong>${esc(globalThis.코스지도모델.label(leg.to))} 도착지 보기</strong>`;arrived(event);
  };
  host.querySelector('[data-speed]').onclick=event=>{playbackSpeed=playbackSpeed===4?1:playbackSpeed*2;event.currentTarget.textContent=`속도 ${playbackSpeed}×`;};
  host.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>setView(button.dataset.view));
  let dragging=null;
  const down=e=>{dragging=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};
  const move=e=>{if(!dragging)return;azimuth-=(e.clientX-dragging[0])*.008;elevation=Math.min(1.35,Math.max(.35,elevation+(e.clientY-dragging[1])*.006));dragging=[e.clientX,e.clientY];};
  const up=()=>dragging=null, wheel=e=>{e.preventDefault();distance=Math.min(2500,Math.max(80,distance*Math.exp(e.deltaY*.001)));};
  canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);canvas.addEventListener('wheel',wheel,{passive:false});
  function resize(){const w=Math.max(1,stage.clientWidth),h=Math.max(1,stage.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  const observer=new ResizeObserver(resize);observer.observe(stage);resize();
  status.textContent=`청록: 걷기 ${legs.filter(leg=>leg.canWalk).length}구간 · 보라: 버스·지하철 ${legs.filter(leg=>!leg.canWalk).length}구간(선은 도로 경로, 실제 노선과 다를 수 있음)${routed.missing.length?` · 경로 미확인 ${routed.missing.length}구간`:''}`;
  function tick(now){
    if(dead)return;const dt=Math.min(.05,(now-last)/1000||0);last=now;
    if(player.state.playing&&arrivalHold>0)arrivalHold=Math.max(0,arrivalHold-dt);
    if(player.state.playing&&arrivalHold===0&&shownLeg!==player.state.index)enterLeg();
    if(player.state.playing&&!player.state.waiting&&arrivalHold===0&&legs[player.state.index]){
      const index=player.state.index,leg=legs[index],event=player.advance(dt/globalThis.코스지도모델.previewSeconds(leg.track.total/U,playbackSpeed));
      const progress=event?1:player.state.progress;completed.set(index,progress);
      sceneMinutes=globalThis.코스지도모델.courseMinutes(leg.from,leg.to,progress);
      const sample=globalThis.코스지도모델.sample(leg.track,event?1:player.state.progress);
      const pos=new THREE.Vector3(sample.point[0],0,sample.point[1]),dir=new THREE.Vector3(sample.direction[0],0,sample.direction[1]);
      movement.copy(dir);leadPos.copy(pos);leadDir.copy(dir);
      for(const [i,c] of characters.entries()){
        c.group.position.copy(pos);c.group.rotation.y=Math.atan2(dir.x,dir.z);
      }
      const key=index+':'+Math.floor(progress*100);if(event||key!==journeyKey){hud.innerHTML=journey(leg,progress,index,legs.length);journeyKey=key;}
      if(event)arrived(event);
    }
    if(cameraMode==='overview'||!hasPlayed){viewTarget.lerp(target,.12);viewDistance+=(distance-viewDistance)*.12;
    camera.position.set(viewTarget.x+viewDistance*Math.sin(azimuth)*Math.cos(elevation),viewDistance*Math.sin(elevation),viewTarget.z+viewDistance*Math.cos(azimuth)*Math.cos(elevation));camera.lookAt(viewTarget);camera.updateMatrixWorld();}
    if(cameraMode!=='overview'&&hasPlayed){
      cameraDir.lerp(leadDir,Math.min(1,dt*2.5)).normalize();
      const front=cameraMode==='front',offset=front?20:-32,height=front?8.5:12;
      const wanted=leadPos.clone().addScaledVector(cameraDir,offset);wanted.y=height;
      camera.position.lerp(wanted,Math.min(1,dt*3));viewTarget.lerp(leadPos.clone().addScaledVector(cameraDir,front?-10:18).setY(2.5),Math.min(1,dt*4));camera.lookAt(viewTarget);camera.updateMatrixWorld();
    }
    const actualAzimuth=Math.atan2(camera.position.x-viewTarget.x,camera.position.z-viewTarget.z);
    const occupied=[],portrait=leadPos.clone().project(camera),portraitX=(portrait.x+1)/2*stage.clientWidth,portraitY=(-portrait.y+1)/2*stage.clientHeight;
    for(const row of labelPins){const p=row.pos.clone().project(camera);row.el.hidden=Math.abs(p.x)>1||Math.abs(p.y)>1||p.z>1||p.z< -1||(cameraMode!=='overview'&&(!row.number||row.pos.distanceTo(leadPos)>160));
      const x=(p.x+1)/2*stage.clientWidth,w=row.el.offsetWidth||100,h=row.el.offsetHeight||24;
      let y=(-p.y+1)/2*stage.clientHeight-row.offset;
      if(cameraMode!=='overview'&&hasPlayed&&Math.abs(x-portraitX)<145+w/2&&y>portraitY-160&&y<portraitY+20)y=portraitY-170;
      for(let attempt=0;attempt<8&&occupied.some(b=>Math.abs(b.x-x)<(b.w+w)/2+5&&Math.abs(b.y-y)<h+5);attempt++)y-=h+6;
      y=Math.max(h+5,y);if(!row.el.hidden)occupied.push({x,y,w});row.el.style.left=x+'px';row.el.style.top=y+'px';}
    for(const [i,row] of motionSprites.entries()){
      const p=characters[i].group.position.clone().project(camera);
      const walking=hasPlayed&&legs[player.state.index]?.canWalk&&legs[shownLeg]?.canWalk;
      row.image.hidden=!first||!row.loaded||!walking||Math.abs(p.x)>1||Math.abs(p.y)>1||p.z>1||p.z< -1;
      characters[i].group.visible=!!first&&!row.loaded&&walking;
      const motion=globalThis.코스지도모델.characterMotion(row.type,movement.x,movement.z,actualAzimuth,cameraMode);
      if(row.view!==motion.view){row.view=motion.view;row.image.src=`/plan/characters/transparent/${row.type}-${motion.view}.png`;}
      row.image.style.left=((p.x+1)/2*stage.clientWidth+(i?(cameraMode==='overview'?21:58):-(cameraMode==='overview'?21:58)))+'px';row.image.style.top=((-p.y+1)/2*stage.clientHeight)+'px';
      row.image.style.transform=`translate(-50%,-98%) scaleX(${motion.flip?-1:1})`;
      row.shadow.hidden=row.image.hidden;row.shadow.style.left=row.image.style.left;row.shadow.style.top=row.image.style.top;
    }
    for(const row of routeStrokes)row.done.material.uniforms.cutoff.value=hasPlayed?(completed.has(row.index)?row.leg.track.total*completed.get(row.index):-1):1e9;
    const mood=atmosphere(sceneMinutes),fade=1-Math.exp(-dt*2.5);
    scene.background.lerp(mood.sky,fade);scene.fog.color.copy(scene.background);for(const row of terrainMaterials)row.material.color.lerp(mood[row.kind],fade);
    clock.textContent=mood.label;
    const worldPerPixel=2*camera.position.distanceTo(viewTarget)*Math.tan(camera.fov*Math.PI/360)/Math.max(1,stage.clientHeight);
    for(const layer of strokeLayers)layer.material.uniforms.halfWidth.value=Math.max(layer.worldWidth,layer.pixels*worldPerPixel)/2;
    renderer.render(scene,camera);frame=requestAnimationFrame(tick);
  }
  frame=requestAnimationFrame(tick);
  return {select,selectStop,previewCandidate,playLeg:number=>startPlayback(number),routes:routeDetails(legs),destroy(){dead=true;cancelAnimationFrame(frame);observer.disconnect();clearCandidates();for(const row of motionSprites){row.image.onload=null;row.image.onerror=null;row.image.remove();row.shadow.remove();}for(const x of resources)x.dispose?.();renderer.dispose();}};
}
