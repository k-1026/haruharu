(function(root){
  const valid=p=>Array.isArray(p)&&p.length===2&&p.every(n=>typeof n==='number'&&Number.isFinite(n))&&Math.abs(p[0])<=90&&Math.abs(p[1])<=180;
  const label=s=>s.개인선택후보?`내 ${s.시간칸||'식사'} · ${s.개인선택후보}`:s.표시명||s.장소명||'일정';
  function model(input){
    const stops=input.map((s,i)=>({...s,순번:s.순번??i+1}));
    const places=[],areas=[],missing=[],entries=[];
    for(const s of stops){
      const meal=!!s.식사권역||(!s.좌표&&['점심','저녁'].includes(s.시간칸));
      let point=valid(s.좌표)?s.좌표.slice():null,item;
      if(meal){
        const candidates=(s.식당후보||[]).map(c=>({...c,좌표:valid(c.좌표)?c.좌표.slice():null}));
        const points=candidates.filter(c=>c.좌표).map(c=>c.좌표),official=valid(s.권역표시?.중심);
        point=valid(s.경로좌표)?s.경로좌표.slice():official?s.권역표시.중심.slice():point|| (points.length?[0,1].map(k=>points.reduce((sum,p)=>sum+p[k],0)/points.length):null);
        item={...s,point,candidates,kind:'area',basis:s.위치설명||(official?s.권역표시.근거:'후보 분포 참고 중심 · 입구/방문 식당 아님')};
        areas.push(item);
      }else{item={...s,point,kind:s.위치유형==='권역대표점'?'region':'place'};if(point)places.push(item);}
      entries.push(item);
      if(!point)missing.push({...s,이유:meal?'권역 위치 확인 중':s.시간칸==='숙박'?'숙소 미지정 · 목록에 유지':s.시간칸==='2일차오전'?'자유시간/장소 선택 전 · 목록에 유지':'좌표 근거 확인 중'});
    }
    const legs=[];
    for(let i=1;i<entries.length;i++){const a=entries[i-1],b=entries[i];if(a.point&&b.point&&a.일차===b.일차)legs.push({from:a,to:b});}
    return {stops,entries,places,areas,missing,legs};
  }
  function preview(data,number,index){const candidate=data.areas.find(s=>s.순번===number)?.candidates[index];return candidate?{...candidate,확정:false}:null;}
  function candidateStops(stops,number,candidate){
    const result=stops.map(s=>({...s})),i=result.findIndex(s=>s.순번===number);if(i<0)return result;
    result[i]={...result[i],장소명:candidate.장소명,경로좌표:candidate.좌표,경로기준표시:candidate.이름};
    for(const leg of candidate.후보이동||[]){
      const from=leg.도착===candidate.장소명?i-1:i;
      if(from<0||!result[from+1]||result[from].일차!==result[from+1].일차)continue;
      result[from]={...result[from],다음이동:{도보분:leg.분,출처:leg.출처,확인일:leg.확인일},후보경로:leg};
    }
    return result;
  }
  // QR 페이지에서 재사용하는 개인 지도 상태. 공통 코스 저장 API·AI 호출 없음.
  function personalMeals(bundle,storage,{preview=false}={}){
    if(bundle?.형식버전!==1||!Array.isArray(bundle.일정)||!Array.isArray(bundle.식사묶음))throw Error('지원하는 식사 후보 데이터가 아닙니다.');
    const clone=v=>JSON.parse(JSON.stringify(v));
    const base=clone(bundle),key='haruharu:meal:'+JSON.stringify([base.코스키,base.안id,base.버전,preview?'preview':'tourist']);
    let choices={};
    function candidate(id,name){
      const pack=base.식사묶음.find(p=>p.칸ID===id),c=pack?.후보.find(c=>c.장소명===name);
      if(!c)throw Error('저장된 후보 묶음 안에서 선택하세요.');
      if((c.오류||[]).length)throw Error(c.오류.join(' / '));
      if(!preview&&(!pack.공개준비||!c.선택가능))throw Error('운영·시간·이동 확인이 남아 있습니다. 직원 확인 후 이용할 수 있습니다.');
      if(!valid(c.좌표)||(c.후보이동||[]).some(l=>!Number.isFinite(l.분)||l.분<0||!Array.isArray(l.경로)||l.경로.length<2||!l.경로.every(valid)))throw Error('이동 경로 확인이 필요합니다.');
      return c;
    }
    function view(next){
      let stops=clone(base.일정);
      for(const [id,name] of Object.entries(next)){
        const c=candidate(id,name),stop=stops.find(s=>s.칸ID===id);
        if(!stop)throw Error('식사 일정이 바뀌었습니다. 다시 불러오세요.');
        stops=candidateStops(stops,stop.순번,c);
        stops.find(s=>s.칸ID===id).개인선택후보=name;
      }
      // 인접 식사의 개인 선택까지 바뀌어 저장 구간과 맞지 않으면 낡은 경로를 사용하지 않는다.
      for(const [id,name] of Object.entries(next)){
        const i=stops.findIndex(s=>s.칸ID===id),c=candidate(id,name);
        for(const leg of c.후보이동||[]){
          const a=leg.도착===name?stops[i-1]:stops[i],b=leg.도착===name?stops[i]:stops[i+1];
          if(!a||!b||a.일차!==b.일차||a.장소명!==leg.출발||b.장소명!==leg.도착)throw Error('인접 식사 선택이 달라 경로를 다시 확인해야 합니다.');
        }
      }
      return {선택:clone(next),일정:stops,비공개미리보기:preview};
    }
    try{
      const saved=JSON.parse(storage?.getItem(key)||'{}');
      if(saved&&typeof saved==='object'&&!Array.isArray(saved))for(const [id,name] of Object.entries(saved)){
        try{view({...choices,[id]:name});choices={...choices,[id]:name};}catch{}
      }
    }catch{}
    function save(next){
      const result=view(next);
      if(!storage?.setItem)throw Error('이 기기에 개인 선택을 저장할 수 없습니다.');
      try{storage.setItem(key,JSON.stringify(next));}catch{throw Error('개인 선택 저장이 차단되어 있습니다. 브라우저 저장 설정을 확인하세요.');}
      choices=next;return result;
    }
    return {snapshot:()=>view(choices),select:(id,name)=>save({...choices,[id]:name}),
      clear:id=>{const next={...choices};delete next[id];return save(next);}};
  }
  function motionView(dx,dz,azimuth){
    const toward=dx*Math.sin(azimuth)+dz*Math.cos(azimuth);
    const right=dx*Math.cos(azimuth)-dz*Math.sin(azimuth);
    return {view:Math.abs(toward)>Math.abs(right)?(toward>=0?'front':'back'):'side',flip:right<0};
  }
  function characterMotion(type,dx,dz,azimuth,cameraMode){
    const motion=cameraMode==='front'?{view:'front',flip:false}:motionView(dx,dz,azimuth);
    // 두 원본 정면 클립의 사선 시선이 반대이므로 족제비 표시만 반전한다.
    return {...motion,flip:motion.view==='front'&&type==='weasel'?!motion.flip:motion.flip};
  }
  const routeKey=(a,b)=>[a,b].map(p=>p.map(v=>v.toFixed(6)).join(',')).join(';');
  function travelInfo(info,walkSeconds){
    const seconds=n=>typeof n==='number'&&Number.isFinite(n)&&n>0?n*60:null;
    const source=info||{},tableWalk=seconds(source.도보분),transitSeconds=seconds(source.대중교통분);
    const walking=typeof walkSeconds==='number'&&Number.isFinite(walkSeconds)&&walkSeconds>0?walkSeconds:tableWalk;
    const limit=typeof source.도보기준분==='number'&&source.도보기준분>0?source.도보기준분:20;
    const mode=transitSeconds&&(!tableWalk||tableWalk>limit*60)?'transit':'foot';
    return {mode,canWalk:mode==='foot',walkSeconds:walking,transitSeconds,transport:source,
      durationSeconds:mode==='transit'?transitSeconds:walking};
  }
  // 좌표·도보 경로가 아직 없어 지도 선을 그릴 수 없을 때, 이동표(CSV) 시간만으로 안내한다.
  function tableLabel(info){
    const t=travelInfo(info);const s=t.mode==='transit'?t.transitSeconds:t.walkSeconds;
    if(!s)return null;
    return (t.mode==='transit'?'대중교통 약 ':'도보 약 ')+Math.round(s/60)+'분 · 지도 경로 준비 중';
  }
  // 대중교통 구간은 실제 노선 모양을 모르니, 두 장소를 잇는 점선 조각(직선)으로만 보여 준다.
  function dashRows(a,b,dash=10,gap=6){
    const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);if(!len)return [];
    const ux=dx/len,uy=dy/len,rows=[];
    for(let t=0;t<len;t+=dash+gap){const e=Math.min(len,t+dash);rows.push([[a[0]+ux*t,a[1]+uy*t],[a[0]+ux*e,a[1]+uy*e]]);}
    return rows;
  }
  // 지도 선이 없을 때의 구간 안내: 위치 없는 숙소로 가는 구간은 '미확인'이 아니라 숙소를 정해야 하는 구간이다.
  function legFallbackLabel(from,to){
    if(to&&to.시간칸==='숙박'&&!to.좌표)return '숙소를 정하면 이동 안내';
    return tableLabel(from&&from.다음이동)||'경로 미확인';
  }
  // 도로 선이 있는 대중교통 구간은 '버스로 타고 가는 구간'(ride)으로 재생한다: 기다리지 않고 도로 선을 따라 빠르게 이동.
  // 도로 선이 없는 구간만 예전처럼 안내 후 '도착지로 넘어가기'를 기다린다. 지도에 그리는 선(roadPath)은 그대로다.
  function playableLegs(legs){
    return legs.map(leg=>leg.mode==='transit'&&leg.roadPath?{...leg,mode:'ride',ride:true,canWalk:true,path:leg.roadPath,distance:null}:leg);
  }
  function legTimeLabel(leg){return leg.mode==='transit'||leg.mode==='ride'||leg.ride?'대중교통 약 '+Math.round(leg.durationSeconds/60)+'분':timeLabel(leg.durationSeconds);}
  // 도로 굽이를 보존하고 거의 일직선인 잔점만 정리한다. 원본·이동시간은 건드리지 않는다.
  function simplifyPath(points,toleranceMeters=2){
    const copy=points.map(p=>p.slice());if(copy.length<3||toleranceMeters<=0)return copy;
    const origin=copy[0],kx=111320*Math.cos(origin[0]*Math.PI/180);
    const metric=copy.map(p=>[(p[1]-origin[1])*kx,(p[0]-origin[0])*111320]);
    const keep=new Set([0,copy.length-1]),pending=[[0,copy.length-1]];
    while(pending.length){
      const [first,last]=pending.pop(),a=metric[first],b=metric[last];
      const dx=b[0]-a[0],dy=b[1]-a[1],length2=dx*dx+dy*dy;
      let largest=toleranceMeters*toleranceMeters,index=-1;
      for(let i=first+1;i<last;i++){
        const p=metric[i],t=length2?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2)):0;
        const distance2=(p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2;
        if(distance2>largest){largest=distance2;index=i;}
      }
      if(index>=0){keep.add(index);pending.push([first,index],[index,last]);}
    }
    return copy.filter((_,i)=>keep.has(i));
  }
  // 바닥 지도에 빠진 보행길도 같은 보유 도보 좌표로 보완한다.
  function walkingRoadRows(routed,origin){
    return routed.legs.filter(leg=>leg.canWalk&&leg.path).map(leg=>leg.path.map(p=>[(p[1]-origin.lon)*origin.kx,(p[0]-origin.lat)*origin.ky]));
  }
  function routesFor(data,cache){
    const legs=[],missing=[];
    for(const leg of data.legs){
      const route=leg.from.후보경로?.경로?{profile:'foot',points:leg.from.후보경로.경로,durationSeconds:leg.from.후보경로.분*60}:cache?.routes?.[routeKey(leg.from.point,leg.to.point)];
      const info=travelInfo(leg.from.다음이동,leg.from.후보경로?leg.from.후보경로.분*60:route?.durationSeconds);
      const road=route?.profile==='foot'&&route.points?.length>=2&&route.points.every(valid)?simplifyPath(route.points):null;
      if(info.mode==='transit')legs.push({...leg,...info,path:null,distance:null,roadPath:road});
      else if(route?.profile==='foot'&&route.points?.length>=2&&route.points.every(valid))legs.push({...leg,...info,path:simplifyPath(route.points),distance:route.distance});
      else missing.push(leg);
    }
    return {legs,missing};
  }
  function track(points){
    const path=[points[0]],lengths=[0];
    for(const p of points.slice(1)){const a=path.at(-1),d=Math.hypot(p[0]-a[0],p[1]-a[1]);if(d>0){path.push(p);lengths.push(lengths.at(-1)+d);}}
    return {points:path,lengths,total:lengths.at(-1)};
  }
  function sample(route,t){
    if(route.points.length<2)return {point:route.points[0],direction:[0,1]};
    const d=Math.max(0,Math.min(1,t))*route.total;
    let i=1;while(i<route.lengths.length-1&&route.lengths[i]<d)i++;
    const a=route.points[i-1],b=route.points[i],length=route.lengths[i]-route.lengths[i-1],fraction=(d-route.lengths[i-1])/length;
    return {point:a.map((v,k)=>v+(b[k]-v)*fraction),direction:a.map((v,k)=>(b[k]-v)/length)};
  }
  function timeLabel(seconds){
    if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<=0)return '도보 시간 미확인';
    const minutes=Math.max(1,Math.round(seconds/60));
    return '도보 약 '+(minutes>=60?`${Math.floor(minutes/60)}시간 ${minutes%60?minutes%60+'분':''}`.trim():minutes+'분');
  }
  // 도로의 중심 좌표와 좌우 방향을 분리해 확대율에 맞춰 폭만 조정한다.
  function roadStrip(rows,y=0,{round=false}={}){
    const positions=[],normals=[],distances=[];
    const vertex=(p,n,d)=>{positions.push(p[0],y,p[1]);normals.push(n[0]||0,n[1]||0);distances.push(d);};
    for(const row of rows){let covered=0;const joints=[];
    for(let i=1;i<row.length;i++){
      const a=row[i-1],b=row[i],dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz);
      if(!length)continue;
      const nx=-dz/length||0,nz=dx/length||0;
      for(const [p,side,d] of [[a,1,covered],[b,1,covered+length],[a,-1,covered],[b,1,covered+length],[b,-1,covered+length],[a,-1,covered]])vertex(p,[nx*side,nz*side],d);
      if(!joints.length)joints.push([a,covered]);covered+=length;joints.push([b,covered]);
    }
    if(round)for(const [p,d] of joints)for(let i=0;i<12;i++){
      vertex(p,[0,0],d);vertex(p,[Math.cos(i*Math.PI/6),Math.sin(i*Math.PI/6)],d);vertex(p,[Math.cos((i+1)*Math.PI/6),Math.sin((i+1)*Math.PI/6)],d);
    }}
    return {positions,normals,distances};
  }
  function clockMinutes(value){
    const match=typeof value==='string'&&value.match(/^\s*(\d{1,2}):(\d{2})\s*$/);
    if(!match||+match[1]>23||+match[2]>59)return null;
    return +match[1]*60+(+match[2]);
  }
  function courseMinutes(from,to,progress){
    const a=clockMinutes(from?.시각);let b=clockMinutes(to?.시각);
    if(a===null)return null;if(b===null)return a;
    if(b<a){if(a>=18*60&&b<=6*60)b+=1440;else return a;}
    return a+(b-a)*Math.max(0,Math.min(1,Number(progress)||0));
  }
  function sceneTime(minutes){
    const known=typeof minutes==='number'&&Number.isFinite(minutes),m=known?((minutes%1440)+1440)%1440:720;
    const smooth=(a,b)=>{const t=Math.max(0,Math.min(1,(m-a)/(b-a)));return t*t*(3-2*t);};
    const night=m<8*60?1-smooth(5*60,8*60):smooth(17*60,20*60);
    const warm=smooth(14*60,17*60)*(1-night),rounded=Math.floor(m);
    const label=known?`${String(Math.floor(rounded/60)).padStart(2,'0')}:${String(rounded%60).padStart(2,'0')} · ${night>.05?'저녁':m>=14*60?'오후':'낮'}`:'시각 미정 · 낮 기준';
    return {night,warm,label};
  }
  function previewSeconds(distance,speed=1){
    const seconds=typeof distance==='number'&&Number.isFinite(distance)&&distance>=0?Math.max(8,distance/25):30;
    return seconds/(Number.isFinite(speed)&&speed>0?speed:1);
  }
  function playback(legs){
    const state={index:0,progress:0,playing:false,mode:'all',finished:false,waiting:false};
    function arrive(){
      const leg=legs[state.index],next=legs[state.index+1];
      const gap=!!next&&(next.from.순번!==leg.to.순번||next.from.일차!==leg.to.일차),done=state.mode==='single'||!next||gap;
      if(done){state.playing=false;state.finished=true;state.waiting=false;}
      else{state.index++;state.progress=0;state.waiting=next.mode==='transit';}
      return {arrived:leg.to,done,gap};
    }
    return {state,startAll(){if(!legs.length)return false;Object.assign(state,{index:0,progress:0,playing:true,mode:'all',finished:false,waiting:legs[0].mode==='transit'});return true;},
      playLeg(number){const index=legs.findIndex(leg=>leg.from.순번===number);if(index<0)return false;Object.assign(state,{index,progress:0,playing:true,mode:'single',finished:false,waiting:legs[index].mode==='transit'});return true;},
      pause(){state.playing=false;},toggle(){if(!state.finished&&legs.length)state.playing=!state.playing;},
      confirmTransit(){if(!state.waiting)return null;state.playing=true;state.progress=1;return arrive();},
      advance(delta){
        if(!state.playing||state.waiting)return null;state.progress=Math.min(1,state.progress+delta);if(state.progress<1)return null;
        return arrive();
      }};
  }
  root.코스지도모델={model,preview,candidateStops,personalMeals,valid,label,motionView,routeKey,routesFor,track,sample,timeLabel,playback,roadStrip,clockMinutes,courseMinutes,sceneTime,previewSeconds,travelInfo,legTimeLabel,tableLabel,legFallbackLabel,dashRows,playableLegs,simplifyPath,characterMotion,walkingRoadRows};
  if(typeof module!=='undefined')module.exports=root.코스지도모델;
})(typeof globalThis!=='undefined'?globalThis:this);
