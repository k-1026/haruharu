'use strict';
const $ = id => document.getElementById(id);
const state = {runs: [], record: null, stage: 2, view: 'result', file: '', cache: new Map(), generation: 0};
const stageNames = ['기획 조건', '수요 근거', '코스 검토', '홍보 검토', '산출물'];
function el(tag, text, cls) {const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n;}
async function api(path, options={}) {const r = await fetch(path, {cache:'no-store',...options}); let body;try{body=await r.json();}catch{throw new Error('서버 응답을 읽지 못했습니다. 새로고침해 주세요.');} if(!r.ok){const e=new Error(body.오류 || '요청을 처리하지 못했습니다.');e.status=r.status;throw e;}return body;}
function dateLabel(s) {return /^\d{8}_\d{6}$/.test(s) ? `${s.slice(0,4)}.${s.slice(4,6)}.${s.slice(6,8)} ${s.slice(9,11)}:${s.slice(11,13)}:${s.slice(13,15)}` : s;}
function conditionValues(c) {return [c.계절 || (c.시기 ? c.시기.join('·')+'월' : ''), ...(Array.isArray(c.언어권) ? c.언어권 : [c.언어권]), ...(Array.isArray(c.지역) ? c.지역 : [c.지역]), c.체류기간].filter(Boolean);}
function badge(text, status) {return el('span',text,'badge '+({'실패':'failed','통과':'passed','읽기 오류':'error'}[status] || ''));}
function inline(node, text) {
  // AI가 반환한 HTML·링크를 실행하지 않는다. 강조와 코드만 DOM 노드로 만든다.
  for(const part of String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g)) {
    if(part.startsWith('**') && part.endsWith('**')) node.append(el('strong',part.slice(2,-2)));
    else if(part.startsWith('`') && part.endsWith('`')) node.append(el('code',part.slice(1,-1)));
    else node.append(document.createTextNode(part));
  }
}
function table(lines) {
  const rows = lines.map(l => l.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g,'|')));
  const headers = rows.shift();
  const data = rows.filter(r => !r.every(c => /^[-:\s]*$/.test(c)));
  const box = el('div',undefined,'tablebox'), tools = el('div',undefined,'tabletools');
  const search = el('input'); search.placeholder = '이 표에서 검색 · R01, 음식, 경고'; search.setAttribute('aria-label','표 내용 검색');
  const count = el('span'); tools.append(search,count);
  const wrap = el('div',undefined,'tablewrap'), t = el('table'), head = el('thead'), tr = el('tr'), body = el('tbody');
  for(const h of headers) {const th=el('th'); inline(th,h); th.scope='col'; tr.append(th);} head.append(tr); t.append(head,body); wrap.append(t);
  const expand = el('button',undefined,'expand'); let all = false;
  function draw() {
    const q = search.value.toLowerCase(); const filtered = data.filter(r => r.join(' ').toLowerCase().includes(q));
    const shown = all || q ? filtered : filtered.slice(0,8); body.replaceChildren();
    for(const row of shown) {const line=el('tr'); for(const c of row) {const td=el('td'); inline(td,c); line.append(td);} body.append(line);}
    count.textContent=`${filtered.length.toLocaleString()}행${q ? ' 검색됨' : ' · 전체'}`;
    expand.hidden = filtered.length <= 8 || Boolean(q);
    expand.textContent = all ? '기본 8행만 보기' : `나머지 ${Math.max(0,filtered.length-8).toLocaleString()}행 펼치기`;
    expand.style.display = expand.hidden ? 'none' : '';
  }
  search.addEventListener('input',draw); expand.addEventListener('click',()=>{all=!all; draw();});
  box.append(tools,wrap,expand); draw(); return box;
}
function markdown(text) {
  const frag = document.createDocumentFragment(), lines = text.split(/\r?\n/); let i=0;
  while(i<lines.length) {
    const line=lines[i];
    if(line.trim().startsWith('```')) {const chunk=[];i++;while(i<lines.length && !lines[i].trim().startsWith('```')) chunk.push(lines[i++]); frag.append(el('pre',chunk.join('\n')));i++;continue;}
    if(line.trim().startsWith('|')) {const chunk=[];while(i<lines.length && lines[i].trim().startsWith('|')) chunk.push(lines[i++]);frag.append(table(chunk));continue;}
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if(heading) {const h=el('h'+Math.min(3,heading[1].length));inline(h,heading[2]);frag.append(h);i++;continue;}
    if(/^\s*[-*]\s/.test(line)) {const ul=el('ul');while(i<lines.length && /^\s*[-*]\s/.test(lines[i])) {const li=el('li');inline(li,lines[i++].replace(/^\s*[-*]\s/,''));ul.append(li);}frag.append(ul);continue;}
    if(line.trim() && !/^---+$/.test(line.trim())) {const p=el('p');inline(p,line.replace(/^>\s?/,''));frag.append(p);}i++;
  }
  return frag;
}
function renderRuns() {
  const q=$('runSearch').value.toLowerCase(); $('runList').replaceChildren();
  for(const r of state.runs.filter(r => (r.id+' '+conditionValues(r.조건).join(' ')).toLowerCase().includes(q))) {
    const b=el('button',undefined,'run'+(state.record?.id===r.id?' selected':''));
    b.append(el('strong',conditionValues(r.조건).join(' · ') || '조건 기록 없음'),el('span',dateLabel(r.실행),'rundate'));
    const meta=el('span',undefined,'runmeta');meta.append(el('i',r.회차),badge(r.검사상태==='기록 없음'?'검사 기록 없음':`검사 ${r.검사상태}`,r.검사상태));b.append(meta);
    b.addEventListener('click',()=>loadRecord(r.id)); $('runList').append(b);
  }
}
function filesForStage() {
  const files=state.record?.파일 || [];
  const parent=state.record?.id;
  return files.filter(f => state.stage>=3?Boolean(courseState.selectedJobId) && f.경로.startsWith(courseState.selectedJobId+'/') && (f.단계===state.stage || (state.stage===3 && f.이름==='코스작성조건_선택.json')):f.경로===parent+'/'+f.이름 && (f.단계===state.stage || (state.stage===2 && f.이름==='3단계_전달_준비.json')));
}
function selectedCheckFiles(){return (state.record?.파일 || []).filter(f=>state.stage<3?f.경로===state.record.id+'/3단계_전달_준비.json':Boolean(courseState.selectedJobId) && f.경로===courseState.selectedJobId+`/${state.stage}단계_전달_검사.json`);}
async function fileData(path) {
  if(!state.cache.has(path)) state.cache.set(path,await api('/api/file?path='+encodeURIComponent(path)));
  return state.cache.get(path);
}
async function loadRecord(id,preferredJob=null) {
  const generation=++state.generation;
  $('notice').textContent='기록을 읽고 있습니다…';
  try {
    const r=await api('/api/run?id='+encodeURIComponent(id)); if(generation!==state.generation)return;
    state.record=r; state.cache.clear(); state.stage=r.파일.some(f=>f.이름==='2단계_결과.md')?2:1;state.file='';
    $('empty').classList.add('hidden');$('record').classList.remove('hidden');$('notice').textContent='';
    $('recordTitle').textContent=dateLabel(r.실행)+' · '+r.회차;
    $('conditions').replaceChildren(...conditionValues(r.조건).map(v=>el('span',v,'condition')));
    $('recordBadge').replaceWith(Object.assign(badge(`2→3 전달 검사 ${r.검사상태}`,r.검사상태),{id:'recordBadge'}));
    $('evidenceCount').textContent=r.근거수.toLocaleString();$('warningCount').textContent=r.경고수.toLocaleString();$('fileCount').textContent=r.파일.length+'개';
    renderRuns(); renderStages();await loadCourse(r,preferredJob);if(state.record?.id===id)await renderPanel();
  } catch(e) {if(generation===state.generation)$('notice').textContent=e.message;}
}
function renderStages() {
  $('stages').replaceChildren();
  stageNames.forEach((name,i)=>{
    const n=i+1, has=state.record.파일.some(f=>f.단계===n && /결과.*\.md$/.test(f.이름) && (n<3?f.경로===state.record.id+'/'+f.이름:Boolean(courseState.selectedJobId) && f.경로.startsWith(courseState.selectedJobId+'/')));
    const b=el('button',`${n}단계 ${name}`,'stagebutton'+(state.stage===n?' active':'')); b.disabled=!has;
    b.title=has?'저장된 단계 결과 보기':'생성된 결과 파일 없음'; b.setAttribute('aria-pressed',String(state.stage===n));
    if(!has)b.append(el('small','미실행'));
    b.addEventListener('click',()=>{state.stage=n;state.file='';renderStages();renderPanel();});$('stages').append(b);
  });
}
async function checks(panel,generation=state.generation) {
  panel.append(el('p','저장된 검사 결과입니다. 통과해도 원자료 수치나 번역이 검증됐다는 뜻은 아닙니다.','help'));
  const candidates=selectedCheckFiles(); let count=0,totalErrors=0;
  for(const f of candidates) {
    const data=await fileData(f.경로); let parsed;
    try {parsed=JSON.parse(data.본문);} catch {const c=el('div',undefined,'checkcard fail');c.append(el('strong',f.이름),el('p','JSON을 읽을 수 없습니다. 원문 보기에서 파일을 확인하세요.'));panel.append(c);count++;totalErrors++;continue;}
    if(!Array.isArray(parsed.검사결과))continue;
    if(Array.isArray(parsed.형식검사)) {
      const ok=parsed.형식검사.length===1 && parsed.형식검사[0]==='통과';
      const card=el('section',undefined,'checkcard'+(ok?'':' fail'));
      card.append(el('p',f.경로.split('/').slice(2).join('/'),'footnote'));
      card.append(el('h3','3단계 앱 검사'),badge(ok?'형식·연결 통과':'앱 검사 확인 필요',ok?'통과':'실패'));
      if(!ok){const ul=el('ul');parsed.형식검사.forEach(p=>ul.append(el('li',String(p))));card.append(ul);totalErrors+=parsed.형식검사.length;}
      const waiting=parsed.담당자확인대기 || [];
      if(waiting.length){card.append(el('h3','담당자 확인 대기'));const ul=el('ul');waiting.forEach(p=>ul.append(el('li',String(p))));card.append(ul);}
      if(parsed.시간표검사){card.append(timeCheckView(parsed.시간표검사));totalErrors+=(parsed.시간표검사.충돌 || []).length;}
      if(parsed['4단계준비검사'] && typeof readinessView==='function')card.append(readinessView(parsed['4단계준비검사']));
      card.append(el('p',parsed['4단계준비검사']?.진행가능?'담당자 확인과 앱 준비 검사를 통과했습니다. 4단계 AI는 실행하지 않았습니다.':'코스 초안을 볼 수 있습니다. 4단계 AI는 실행하지 않았습니다.','help'));panel.append(card);count++;continue;
    }
    const passed=parsed.검사결과.length===1 && parsed.검사결과[0]==='통과';
    const card=el('section',undefined,'checkcard'+(passed?'':' fail')),head=el('div',undefined,'checkhead');
    const label=f.이름==='3단계_전달_준비.json'?'2→3 전달 준비 검사':f.이름.replace('.json','').replaceAll('_',' ');
    head.append(el('span',label),badge(passed?'통과':'확인 필요',passed?'통과':'실패'));card.append(head);
    card.append(el('p',f.경로.split('/').slice(2).join('/') || f.이름,'footnote'));
    if(passed)card.append(el('p','이 파일에 기록된 검사에서 오류가 발견되지 않았습니다.'));
    else {const errors=new Map();for(const e of parsed.검사결과) errors.set(String(e),(errors.get(String(e))||0)+1);const ul=el('ul');for(const [e,n] of errors)ul.append(el('li',e+(n>1?` (${n}건 반복)`:'')));card.append(ul);totalErrors+=parsed.검사결과.length;}
    panel.append(card);count++;
  }
  if(!count)panel.append(el('p','저장된 전달 검사 기록이 없습니다. 파일이 만들어졌다는 이유로 통과 처리하지 않습니다.'));
  if(generation===state.generation)$('errorCount').textContent=totalErrors?String(totalErrors):'';
}
async function renderPanel() {
  const generation=++state.generation;const panel=$('panel');panel.replaceChildren();
  showRevisionMeta();
  document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.view===state.view)));
  const files=filesForStage();const select=$('fileSelect');select.replaceChildren();
  for(const f of files) {const o=el('option',f.경로.split('/').slice(2).join('/') || f.이름);o.value=f.경로;select.append(o);}
  if(!files.some(f=>f.경로===state.file))state.file=(files.find(f=>new RegExp(`^${state.stage}단계_결과.*\\.md$`).test(f.이름)) || files[0])?.경로 || '';
  select.value=state.file;select.disabled=state.view==='checks';
  try {
    if(state.view==='checks') {const buffer=el('div');await checks(buffer);if(generation===state.generation)panel.replaceChildren(...buffer.childNodes);return;}
    if(!state.file){panel.append(el('p','이 단계에 저장된 결과 파일이 없습니다.'));return;}
    const data=await fileData(state.file);if(generation!==state.generation)return;
    const isCourse=state.stage===3 && /3단계_(결과.*\.md|구조화\.json)$/.test(data.이름);
    if(state.view==='raw' || (data.형식==='json' && !isCourse)) {
      const label=el('p',data.이름,'sectionlabel');let body=data.본문;
      if(data.형식==='json'){try{body=JSON.stringify(JSON.parse(body),null,2);}catch{panel.append(el('p','JSON 형식 오류가 있습니다. 저장된 원문을 그대로 표시합니다.','help'));}}
      panel.append(label,el('pre',body));
    } else if(isCourse && state.view==='result') {
      const normalized=state.record.파일.find(f=>f.경로===state.file.replace(/3단계_결과\.md$/,'3단계_구조화.json'));
      const content=normalized?(await fileData(normalized.경로)).본문:data.본문;
      if(generation!==state.generation)return;
      const checkFile=state.record.파일.find(f=>f.경로===state.file.replace(/3단계_(결과\.md|구조화\.json)$/,'3단계_전달_검사.json'));
      if(checkFile){const check=JSON.parse((await fileData(checkFile.경로)).본문);if(generation!==state.generation)return;if(check.시간표검사)panel.append(timeCheckView(check.시간표검사));if(check['4단계준비검사'] && typeof readinessView==='function')panel.append(readinessView(check['4단계준비검사']));}
      renderCourseResult(panel,content);
    } else {panel.append(markdown(data.본문));}
  } catch(e) {if(generation===state.generation)panel.append(el('p',e.message,'help'));}
}
async function refresh() {
  const id=state.record?.id;$('notice').textContent='실행 목록을 읽고 있습니다…';
  try {state.runs=await api('/api/runs');$('runCount').textContent=state.runs.length;renderRuns();
    if(state.runs.length) await loadRecord(state.runs.some(r=>r.id===id)?id:state.runs[0].id);
    else {$('record').classList.add('hidden');$('empty').classList.remove('hidden');$('notice').textContent='';}
  } catch(e) {$('notice').textContent=e.message;}
}
$('runSearch').addEventListener('input',renderRuns);$('refresh').addEventListener('click',refresh);
$('fileSelect').addEventListener('change',e=>{state.file=e.target.value;renderPanel();});
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{state.view=b.dataset.view;renderPanel();}));
refresh();
