const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
test('후보 선택은 야시장과 낮 시장을 구분하고 부분일치로 확정하지 않음',()=>{
  const c=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면/장소선택.js'),'utf8'),c);
  vm.runInContext("placeState.items=[{장소명:'서문시장'},{장소명:'서문시장 야시장'},{장소명:'원주통닭 (치킨 옵션)'}]",c);
  assert.equal(vm.runInContext("findPlace('대구광역시 중구 서문시장 권역').장소명",c),'서문시장');
  assert.equal(vm.runInContext("findPlace('서문시장 야시장').장소명",c),'서문시장 야시장');
  assert.equal(vm.runInContext("findPlace('자유식 · 대구광역시 중구 서문시장 권역').장소명",c),'서문시장');
  assert.equal(vm.runInContext("findPlace('서문')",c),null);
});

test('실제 폼 생성으로 보유 시간 보존·접힌 일정·외부 폼 연결·상시 날짜 숨김 확인',()=>{
  const nodes=new Map(),fields=new Map();
  const make=(tag,text)=>{
    let id='',name='',value='';
    const n={tag,text,children:[],dataset:{},attrs:{},checked:false,classList:{toggle(){}},append(...items){this.children.push(...items);},replaceChildren(){this.children=[];},hasChildNodes(){return this.children.length>0;},setAttribute(k,v){this.attrs[k]=v;},addEventListener(){}};
    Object.defineProperty(n,'id',{get:()=>id,set:v=>{id=v;nodes.set(v,n);}});
    Object.defineProperty(n,'name',{get:()=>name,set:v=>{name=v;fields.set(v,n);}});
    Object.defineProperty(n,'value',{get:()=>value,set:v=>{value=String(v);}});
    if(tag==='select')Object.defineProperty(n,'options',{get:()=>n.children});return n;
  };
  const node=id=>{if(!nodes.has(id)){const n=make('div');n.id=id;n.elements={namedItem:name=>{if(!fields.has(name)){const f=make('input');f.name=name;}return fields.get(name);}};}return nodes.get(id);};
  const c=vm.createContext({document:{getElementById:node},$:node,el:make,courseState:{},clearTimeout(){}});
  for(const file of ['장소선택.js','코스조건.js','운영확인.js'])vm.runInContext(fs.readFileSync(path.join(path.resolve(__dirname, '..'),'관리자화면',file),'utf8'),c);
  c.info={체류기간:'1박2일',저장값:{},일정목록:[{안:'공통',칸ID:'낮',시간칸:'낮',장소명:'서문시장',시작일차:1,시작시각:'10:00',종료일차:1,종료시각:'11:00'},{안:'공통',칸ID:'숙박',시간칸:'숙박',장소명:'숙소',시작일차:1}],운영대상:[{안:'공통',칸ID:'낮',대상명:'서문시장',확인필요:['출처 보완'],보유자료:{장소명:'서문시장',운영시간:'09:00-18:00'},입력값:{영업시작:'09:00',영업종료:'18:00',방문일운영확인:false}}]};
  vm.runInContext('reviewState.info=info;buildReview(info)',c);
  assert.equal(fields.get('ro-0-영업종료').value,'18:00');assert.equal(fields.get('ro-0-방문일운영확인').checked,false);
  assert.equal(fields.get('ro-0-영업종료').attrs.form,'reviewForm');assert.equal(fields.get('ro-0-방문일운영확인').attrs.form,'reviewForm');
  assert.equal(node('reviewPeriods').children[0].open,false);assert.equal(node('reviewPeriods').children[1].open,false);
  assert.equal(fields.get('운영기준').value,'상시기획');assert.equal(fields.get('방문시작일').disabled,true);
  assert.equal(vm.runInContext('readReviewForm().방문시작일',c),'');
  assert.equal(vm.runInContext('readReviewForm().운영확인[0].영업종료',c),'18:00');
  assert.equal(vm.runInContext('readReviewForm().일정확인[0].시작시각',c),'10:00');
});
