(function(root){
  const valid=p=>Array.isArray(p)&&p.length===2&&p.every(n=>typeof n==='number'&&Number.isFinite(n))&&Math.abs(p[0])<=90&&Math.abs(p[1])<=180;
  const label=s=>s.표시명||s.장소명||'일정';
  function model(input){
    const stops=input.map((s,i)=>({...s,순번:s.순번??i+1}));
    const places=[],areas=[],missing=[],entries=[];
    for(const s of stops){
      const meal=!!s.식사권역||(!s.좌표&&['점심','저녁'].includes(s.시간칸));
      let point=valid(s.좌표)?s.좌표.slice():null,item;
      if(meal){
        const candidates=(s.식당후보||[]).map(c=>({...c,좌표:valid(c.좌표)?c.좌표.slice():null}));
        const points=candidates.filter(c=>c.좌표).map(c=>c.좌표),official=valid(s.권역표시?.중심);
        point=official?s.권역표시.중심.slice():point|| (points.length?[0,1].map(k=>points.reduce((sum,p)=>sum+p[k],0)/points.length):null);
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
  function motionView(dx,dz,azimuth){
    const toward=dx*Math.sin(azimuth)+dz*Math.cos(azimuth);
    const right=dx*Math.cos(azimuth)-dz*Math.sin(azimuth);
    return {view:Math.abs(toward)>Math.abs(right)?(toward>=0?'front':'back'):'side',flip:right<0};
  }
  const routeKey=(a,b)=>[a,b].map(p=>p.map(v=>v.toFixed(6)).join(',')).join(';');
  function routesFor(data,cache){
    const legs=[],missing=[];
    for(const leg of data.legs){
      const route=cache?.routes?.[routeKey(leg.from.point,leg.to.point)];
      if(route?.profile==='foot'&&route.points?.length>=2&&route.points.every(valid))legs.push({...leg,path:route.points,distance:route.distance,durationSeconds:route.durationSeconds});
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
    const state={index:0,progress:0,playing:false,mode:'all',finished:false};
    return {state,startAll(){if(!legs.length)return false;Object.assign(state,{index:0,progress:0,playing:true,mode:'all',finished:false});return true;},
      playLeg(number){const index=legs.findIndex(leg=>leg.from.순번===number);if(index<0)return false;Object.assign(state,{index,progress:0,playing:true,mode:'single',finished:false});return true;},
      pause(){state.playing=false;},toggle(){if(!state.finished&&legs.length)state.playing=!state.playing;},
      advance(delta){
        if(!state.playing)return null;state.progress=Math.min(1,state.progress+delta);if(state.progress<1)return null;
        const leg=legs[state.index],next=legs[state.index+1];
        const gap=!!next&&(next.from.순번!==leg.to.순번||next.from.일차!==leg.to.일차);
        const done=state.mode==='single'||!next||gap;
        if(done){state.playing=false;state.finished=true;}else{state.index++;state.progress=0;}
        return {arrived:leg.to,done,gap};
      }};
  }
  root.코스지도모델={model,preview,valid,label,motionView,routeKey,routesFor,track,sample,timeLabel,playback,roadStrip,clockMinutes,courseMinutes,sceneTime,previewSeconds};
  if(typeof module!=='undefined')module.exports=root.코스지도모델;
})(typeof globalThis!=='undefined'?globalThis:this);
