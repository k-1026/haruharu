// 담당자에게 보여 주는 말만 정리한다. 원본 코스·근거·검사 기록은 수정하지 않는다.
(function(root){
  function 문장(value){
    let text=String(value??'');
    const interest=/관심/.test(text);
    const countNote=interest&&/((?:19|20)\d{2})\s*년?\s*\d+\s*번/.test(text)&&!/실제 방문.*아니/.test(text);
    text=text.replace(/((?:19|20)\d{2})\s*년?\s*(\d+)\s*번/g,(_,year,n)=>
      interest?`${year}년 관심 관광지 목록에 ${n}회 등장`:`${year}년 자료에 ${n}회 기록`);
    text=text
      .replace(/\b(?:S3-[A-Z]+\d*|[RWSO]\d+)(?:[~～·,\s]*(?:[RWSO]\d+))*/g,'')
      .replace(/(?:희망|후보)-\d+\s*(?:반영)?/g,'')
      .replace(/(낮오후|낮|점심|저녁|밤|숙박)-\d+/g,(_,slot)=>(slot==='낮오후'?'오후':slot)+' 일정')
      .replace(/2일-오전-\d+/g,'둘째 날 오전')
      .replace(/\([^)]*운영시트[^)]*\)/g,'')
      .replace(/치킨선택 필드는 미선택 그대로입니다\.?/g,'치킨 식사 여부는 아직 정하지 않았어요.')
      .replace(/저장소에서 확인된/g,'확보한 자료에서 확인된')
      .replace(/2단계에도/g,'수요 분석 자료에도')
      .replace(/\(\s*\)|\[\s*\]/g,'')
      .replace(/\(\s*[,·]\s*/g,'(').replace(/\s+([,.])/g,'$1')
      .replace(/\(\s+/g,'(').replace(/\s{2,}/g,' ').trim();
    return text+(countNote?' 관심 목록에 포함된 횟수이며 실제 방문자 수는 아니에요.':'');
  }
  function 짧게(value,max=140){
    const text=문장(value);
    return text.length>max?text.slice(0,max-1).trimEnd()+'…':text;
  }
  function 상태(rec){
    const groups=rec.분류||{};
    if(!rec.검사함)return {종류:'대기',제목:'아직 검토가 끝나지 않았어요',설명:'코스는 초안이에요. 일정과 운영 정보를 확인한 뒤 진행해 주세요.'};
    if((groups.AI수정||[]).length||(groups.자료보완||[]).length||rec.검증==='반려')
      return {종류:'보완',제목:'일정에 보완할 점이 있어요',설명:'이동·운영 정보 등 확인이 남아 있어요. 지금은 확정 전 초안으로 검토해 주세요.'};
    if(rec.검증!=='통과')return {종류:'대기',제목:'코스 검토가 더 필요해요',설명:'기본 점검 이후의 검토가 아직 끝나지 않았어요.'};
    return {종류:'확인',제목:'초안 검토를 마쳤어요',설명:'담당자가 장소·시간과 운영 조건을 확인한 뒤 확정해 주세요.'};
  }
  function 할일(rec){
    const texts=[...(rec.분류?.사람결정||[]).map(x=>x.문구||''),...(rec.요약?.확인할것||[])];
    const result=[];const seen=new Set();let unknown=false;
    const add=(제목,설명)=>{if(!seen.has(제목)){seen.add(제목);result.push({제목,설명});}};
    for(const text of texts){
      if(/좌표|희망.*(?:일부|못지킴)/.test(text))continue;
      if(/시작|종료/.test(text))add('여행의 시작과 끝','집결·해산 장소와 시각을 정해 주세요.');
      else if(/2일|둘째|오전선택/.test(text))add('둘째 날 오전','관광·자유시간·바로 귀가 중 어떻게 보낼지 골라 주세요.');
      else if(/숙박|숙소/.test(text))add('숙박 일정','숙소와 도착·다음 날 출발 시각을 확인해 주세요.');
      else if(/식사|식당|식비/.test(text))add('식사 방식','자유식·지정식과 식사 비용의 포함 여부를 정해 주세요.');
      else if(/운영\s*방식|단체|개별/.test(text))add('여행 운영 방식','단체 동행 또는 개별 이동 방식을 골라 주세요.');
      else if(/겹침|노선/.test(text))add('기존 상품과의 겹침','겹치는 구간을 유지할지 조정할지 골라 주세요.');
      else if(text)unknown=true;
    }
    if(unknown)add('추가 확인','그 밖의 담당자 확인 사항이 있어요. 팀 검토 후 진행해 주세요.');
    return result;
  }
  function 보완요약(rec){
    const texts=[...(rec.분류?.AI수정||[]),...(rec.분류?.자료보완||[])].map(x=>x.문구||'');
    const notes=[];
    for(const text of texts){
      const travel=text.match(/이동[^.]*?(\d+)분[^.]*?상한\s*(\d+)분/)||text.match(/대중교통\s*(\d+)분[^.]*?상한\s*(\d+)분/);
      if(travel)notes.push(`한 구간의 이동이 ${travel[1]}분으로 기준 ${travel[2]}분을 넘어요.`);
      else if(/일정 겹침|시간.*겹/.test(text))notes.push('일부 일정의 시간이 겹쳐 조정이 필요해요.');
      else if(/선택 지역 밖|범위 밖 후보|필수 조건 지역 못지킴/.test(text))notes.push('선택한 지역 밖 장소가 있어 동선을 조정해야 해요.');
      else if(/야시장/.test(text)&&/요일|동계|운영|휴무/.test(text))notes.push('야시장 운영 요일과 시간을 확인해야 해요.');
      else if(/운영시간|운영 시간/.test(text))notes.push('일부 방문 장소의 운영시간 확인이 남아 있어요.');
    }
    return [...new Set(notes)].slice(0,2);
  }
  function 위치안내(s){
    const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const lines=[s.위치설명,s.진입안내].filter(Boolean).map(x=>`<p class="note">${safe(x)}</p>`).join('');
    const proof=s.위치근거URL?`<a href="${safe(s.위치근거URL)}" target="_blank" rel="noopener">위치 근거</a>`:'';
    const map=s.지도링크?`<a href="${safe(s.지도링크)}" target="_blank" rel="noopener">카카오맵에서 보기 ↗</a>`:'';
    return lines||proof||map?`<details class="location-info"><summary>위치 정보</summary>${lines}<p>${[proof,map].filter(Boolean).join(' · ')}</p></details>`:'';
  }
  function 장소패널(s){
    const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const name=문장((s.표시명||s.장소명||'장소 미정').split(/\s+[—–]\s+/)[0]),info=s.장소안내||{};
    const candidates=s.식당후보||[];
    return `<button type="button" class="panel-close" data-place-close aria-label="장소 설명 닫기"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button><p class="eyebrow">${safe(s.일차)}일차 · ${safe(s.시각||'권장 시각 미정')}</p>
      <h2 tabindex="-1" id="placeTitle">${safe(name)}</h2><p>${safe(info.소개||'아직 장소 소개가 등록되지 않은 일정입니다.')}</p>
      ${info.이용시간||info.휴무?`<section class="place-facts"><h3>이용 참고 <small>보유 자료 기준</small></h3>${info.이용시간?`<p>이용시간 · ${safe(info.이용시간)}</p>`:''}${info.휴무?`<p>휴무 · ${safe(info.휴무)}</p>`:''}<p class="note">운영일·시간은 방문 전에 다시 확인해 주세요.${info.확인일?' 자료 확인일 '+safe(info.확인일):''}</p></section>`:''}
      ${info.주소?`<p class="note">${safe(info.주소)}</p>`:''}
      ${s.식사권역?`<section><h3>식당 후보</h3><p class="note">후보를 눌러도 방문이 확정되지 않습니다.</p>${candidates.length?candidates.map((c,i)=>`<button type="button" class="candidate-choice" data-explore-candidate="${i}">${safe(c.이름)} <small>미리보기${c.좌표?'':' · 위치 확인 중'}</small></button>`).join(''):'<p class="note">아직 등록된 식당 후보가 없습니다. 권역만 표시합니다.</p>'}<div id="candidatePreview" role="status"></div></section>`:''}
      ${!s.좌표&&!s.권역표시?.중심?'<p class="note">이 일정은 아직 지도 위치가 정해지지 않았습니다. 목록에는 계속 남겨 둡니다.</p>':''}
      ${위치안내(s)}${info.출처URL?`<p><a target="_blank" rel="noopener" href="${safe(info.출처URL)}">장소 안내 출처 ↗</a></p>`:''}`;
  }
  const 닭=`<svg class="drum" viewBox="0 0 24 24" aria-hidden="true"><path d="M10.6 14.8 5 20" stroke="#8A4B1F" stroke-width="4.4" stroke-linecap="round"/><circle cx="4.1" cy="19.1" r="1.9" fill="#FFF3DC" stroke="#8A4B1F" stroke-width=".8"/><circle cx="5.9" cy="20.9" r="1.9" fill="#FFF3DC" stroke="#8A4B1F" stroke-width=".8"/><path d="M10.6 14.8 5 20" stroke="#FFF3DC" stroke-width="2.6" stroke-linecap="round"/><path d="M8.6 13.9C7.4 10.6 8.4 6.6 11.5 4.6C12.6 3.9 13.4 4.1 14.4 3.6C15.6 3 16.6 2.9 17.7 3.6C18.7 4.2 19 5.1 19.9 5.8C20.9 6.6 21.6 7.4 21.4 8.8C21.3 9.9 20.5 10.6 20.4 11.7C20.3 12.9 20.1 13.9 19 14.8C17.6 15.9 16.3 15.6 15 16C13.6 16.4 12.6 17 11.2 16.5C10 16 9.2 15.2 8.6 13.9Z" fill="#C8701A" stroke="#8A4B1F" stroke-width=".8" stroke-linejoin="round"/><path d="M11.4 7.2c1.1-1.6 2.8-2.4 4.4-2.2" stroke="#F4BE63" stroke-width="1.1" stroke-linecap="round" fill="none"/><g fill="#F4BE63"><circle cx="16.8" cy="8.2" r=".75"/><circle cx="14" cy="10.6" r=".7"/><circle cx="18.4" cy="11.6" r=".6"/><circle cx="12.4" cy="13.4" r=".55"/></g></svg>`;
  const 치킨장소=name=>/닭|치킨|치맥/.test(String(name||''));
  function 입장화면(){return `<div class="entry-backdrop" aria-hidden="true"><svg class="bk-sky" viewBox="0 0 1440 640" preserveAspectRatio="none"><defs><linearGradient id="bSky" x1="0" x2="1"><stop offset="0" stop-color="#FFF5DD"/><stop offset=".55" stop-color="#FFEBCF"/><stop offset="1" stop-color="#FCD9B8"/></linearGradient><linearGradient id="bNight" x1="0" x2="1"><stop offset=".5" stop-color="#F6C3A0" stop-opacity="0"/><stop offset=".7" stop-color="#E9AE9A" stop-opacity=".7"/><stop offset=".86" stop-color="#A88AA6"/><stop offset="1" stop-color="#5C6290"/></linearGradient></defs><rect width="1440" height="640" fill="url(#bSky)"/><rect class="night-veil" width="1440" height="640" fill="url(#bNight)"/><path class="sky-path" d="M100 84 Q740 -70 1300 110" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-dasharray="1 13" vector-effect="non-scaling-stroke" opacity=".95"/></svg><svg class="bk-sun" viewBox="0 0 240 240"><g class="sun"><circle cx="120" cy="120" r="96" fill="#FFE7AE" opacity=".55"/><circle cx="120" cy="120" r="50" fill="#FFCF72" opacity=".9"/></g><g fill="#fff" opacity=".7"><ellipse cx="200" cy="190" rx="40" ry="9"/></g></svg><svg class="bk-moon" viewBox="0 0 520 340"><g class="night-sky"><path d="M362 76a34 34 0 1 0 20 62a28 28 0 1 1-20-62z" fill="#FFF1D2"/><g fill="#FFEBB5"><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(446 50) scale(0.9)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(486 186) scale(0.6)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(310 226) scale(0.5)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(410 258) scale(0.5)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(92 48) scale(0.45)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(340 300) scale(0.4)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(108 214) scale(0.45)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(470 110) scale(0.5)"/></g></g></svg><svg class="bk-ridge" viewBox="0 0 1440 140" preserveAspectRatio="none"><defs><linearGradient id="bRidge" x1="0" x2="1"><stop offset="0" stop-color="#EBCFA5"/><stop offset=".55" stop-color="#E7B48F"/><stop offset=".8" stop-color="#9D86A0"/><stop offset="1" stop-color="#6E6A93"/></linearGradient></defs><path d="M0 118C110 96 190 66 300 78S470 34 570 56S700 26 790 48S930 74 1010 64S1170 88 1250 94S1390 104 1440 100V140H0z" fill="url(#bRidge)" opacity=".55"/></svg><svg class="bk-tower" viewBox="0 0 360 180"><g fill="#6E6A93" opacity=".62"><path d="M30 180Q180 124 330 180z"/><rect x="174" y="58" width="12" height="104"/><ellipse cx="180" cy="72" rx="26" ry="14"/><ellipse cx="180" cy="60" rx="12" ry="6"/><rect x="178.5" y="10" width="3" height="46"/><rect x="246" y="136" width="30" height="44"/><rect x="282" y="120" width="26" height="60"/><rect x="314" y="142" width="30" height="38"/><rect x="40" y="146" width="28" height="34"/><rect x="74" y="132" width="24" height="48"/></g><g class="bk-lights" fill="#FFE3A0"><rect x="168" y="70" width="5" height="4" rx="1"/><rect x="178" y="70" width="5" height="4" rx="1"/><rect x="188" y="70" width="5" height="4" rx="1"/><rect x="288" y="130" width="4" height="5"/><rect x="297" y="146" width="4" height="5"/><rect x="254" y="148" width="4" height="5"/><rect x="322" y="154" width="4" height="5"/><rect x="80" y="142" width="4" height="5"/></g></svg><svg class="bk-drumstars" viewBox="176 2 122 84"><g class="drum-stars"><g fill="none" stroke="#FFEBB5" stroke-width="1.3" stroke-linecap="round" opacity=".6"><polygon points="238,20 264,12 288,24 286,50 260,60 236,46"/><path d="M238 44L196 64M196 64L185 55M196 64L189 75"/></g><g fill="#FFF1C8"><circle cx="238" cy="20" r="3.2"/><circle cx="264" cy="12" r="2.6"/><circle cx="288" cy="24" r="3"/><circle cx="286" cy="50" r="2.4"/><circle cx="260" cy="60" r="2.8"/><circle cx="236" cy="46" r="2.6"/><circle cx="196" cy="64" r="2.4"/><circle cx="185" cy="55" r="2.8"/><circle cx="189" cy="75" r="2.6"/></g></g></svg><svg class="bk-cloud" viewBox="0 0 200 60"><g fill="#fff" opacity=".75"><ellipse cx="90" cy="34" rx="64" ry="14"/><ellipse cx="130" cy="24" rx="36" ry="14"/></g></svg></div><section class="entry-screen"><div class="entry-copy"><h1>대구의 낮과 밤을,<br>하나의 여행으로.</h1><p class="entry-lead">조건을 고르면 AI가 낮 관광부터 저녁, 숙박까지 이어지는 대구 코스 초안을 만들어요.</p><div class="entry-actions"><button class="btn primary big" id="entryNew">새 코스 기획하기</button></div></div><section class="entry-recent" aria-labelledby="recentTitle"><div class="recent-head"><h2 id="recentTitle">이어서 보기</h2><button class="btn link" id="entrySaved">지난 코스 전체</button></div><div class="recent-list" id="recentList"><p class="empty">불러오는 중…</p></div><p class="note">저장된 코스와 지도는 AI 실행 없이 다시 볼 수 있어요.</p></section><div class="entry-band"><ol class="entry-flow" aria-label="기획 순서"><li><b>조건 고르기</b><small>계절·언어권·지역·체류 기간</small></li><li><b>AI 초안 받기</b><small>A안과 대안을 함께 만들어요</small></li><li><b>지도로 검토</b><small>동선·운영시간·이동 시간</small></li><li><b>홍보물·결재 파일</b><small>확정한 안으로 이어서</small></li></ol><button type="button" class="scroll-cue" id="toDay">코스가 이어지는 하루 보기<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button></div></section><h2 class="day-title" id="dayTitle">코스가 이어지는 하루<span>낮 관광에서 저녁, 밤과 숙박까지 이렇게 이어서 기획해요</span></h2><section class="entry-day" aria-label="코스가 이어지는 하루"><div class="day-scene" aria-hidden="true"><svg class="scene-svg" viewBox="0 0 1200 260" preserveAspectRatio="xMidYMax slice" aria-hidden="true"><defs><linearGradient id="skyG" x1="0" x2="1"><stop offset="0" stop-color="#FFF4DA"/><stop offset=".42" stop-color="#FFE2BA"/><stop offset=".62" stop-color="#F6B183"/><stop offset=".8" stop-color="#8F5F7B"/><stop offset="1" stop-color="#2A3155"/></linearGradient><linearGradient id="hillG" x1="0" x2="1"><stop offset="0" stop-color="#F4DDB4"/><stop offset=".55" stop-color="#EDB48C"/><stop offset=".8" stop-color="#6E4F6E"/><stop offset="1" stop-color="#363C62"/></linearGradient><linearGradient id="cityG" x1="0" x2="1"><stop offset="0" stop-color="#E7C58F"/><stop offset=".5" stop-color="#D88A5C"/><stop offset=".78" stop-color="#4B3A57"/><stop offset="1" stop-color="#1F2542"/></linearGradient><linearGradient id="groundG" x1="0" x2="1"><stop offset="0" stop-color="#FBEBCB"/><stop offset=".55" stop-color="#F5C9A2"/><stop offset=".8" stop-color="#7A5A74"/><stop offset="1" stop-color="#2C3354"/></linearGradient></defs><rect width="1200" height="260" fill="url(#skyG)"/><circle cx="130" cy="72" r="58" fill="#FFE9B5" opacity=".7"/><circle cx="130" cy="72" r="34" fill="#FFC861"/><g fill="#fff" opacity=".75"><ellipse cx="300" cy="58" rx="48" ry="12"/><ellipse cx="330" cy="50" rx="28" ry="12"/><ellipse cx="470" cy="86" rx="36" ry="9"/></g><path d="M1088 34a26 26 0 1 0 16 47a22 22 0 1 1-16-47z" fill="#FFF0C9"/><g fill="#FFE6A6"><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(980 40) scale(1)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(1040 88) scale(0.7)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(1150 36) scale(0.8)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(1160 110) scale(0.55)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(900 60) scale(0.5)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(1120 140) scale(0.45)"/><path d="M0-7L1.9-1.9 7 0 1.9 1.9 0 7-1.9 1.9-7 0-1.9-1.9z" transform="translate(820 34) scale(0.45)"/></g><path d="M0 196 C120 170 220 184 330 176 S560 160 700 178 S900 150 1010 168 S1140 160 1200 172 V260 H0z" fill="url(#hillG)" opacity=".85"/><g fill="url(#cityG)"><path d="M176 212V148h18v-28l9-26 9 26v28h28v-28l9-26 9 26v28h18v64z"/><rect x="205" y="78" width="2" height="12"/><rect x="200" y="82" width="12" height="2"/><path d="M300 182q50-20 100 0l-8 5q-42-15-84 0z"/><rect x="314" y="186" width="72" height="26"/><path d="M500 212v-38l18-12h204l18 12v38z"/><path d="M880 212q40-46 100-40t60 40z"/><rect x="928" y="96" width="9" height="90"/><ellipse cx="932.5" cy="110" rx="18" ry="10"/><rect x="931.5" y="58" width="2.5" height="42"/><rect x="990" y="160" width="40" height="52"/><rect x="1036" y="146" width="34" height="66"/><rect x="1084" y="166" width="36" height="46"/><rect x="1130" y="154" width="40" height="58"/></g><g fill="#FFD47A"><rect x="1000" y="170" width="5" height="6" rx="1"/><rect x="1012" y="184" width="5" height="6" rx="1"/><rect x="1000" y="198" width="5" height="6" rx="1"/><rect x="1046" y="156" width="5" height="6" rx="1"/><rect x="1058" y="170" width="5" height="6" rx="1"/><rect x="1046" y="184" width="5" height="6" rx="1"/><rect x="1058" y="198" width="5" height="6" rx="1"/><rect x="1094" y="176" width="5" height="6" rx="1"/><rect x="1106" y="190" width="5" height="6" rx="1"/><rect x="1094" y="204" width="5" height="6" rx="1"/><rect x="1140" y="164" width="5" height="6" rx="1"/><rect x="1152" y="178" width="5" height="6" rx="1"/><rect x="1140" y="192" width="5" height="6" rx="1"/><rect x="1152" y="206" width="5" height="6" rx="1"/></g><g class="chick-sign"><rect x="691.5" y="140" width="2.6" height="34" fill="#6b3f22"/><circle cx="693" cy="122" r="19" fill="#C2551F" stroke="#FFD089" stroke-width="2"/><g transform="translate(678 107) scale(1.25)"><path d="M10.6 14.8 5 20" stroke="#8A4B1F" stroke-width="4.4" stroke-linecap="round"/><circle cx="4.1" cy="19.1" r="1.9" fill="#FFF3DC" stroke="#8A4B1F" stroke-width=".8"/><circle cx="5.9" cy="20.9" r="1.9" fill="#FFF3DC" stroke="#8A4B1F" stroke-width=".8"/><path d="M10.6 14.8 5 20" stroke="#FFF3DC" stroke-width="2.6" stroke-linecap="round"/><path d="M8.6 13.9C7.4 10.6 8.4 6.6 11.5 4.6C12.6 3.9 13.4 4.1 14.4 3.6C15.6 3 16.6 2.9 17.7 3.6C18.7 4.2 19 5.1 19.9 5.8C20.9 6.6 21.6 7.4 21.4 8.8C21.3 9.9 20.5 10.6 20.4 11.7C20.3 12.9 20.1 13.9 19 14.8C17.6 15.9 16.3 15.6 15 16C13.6 16.4 12.6 17 11.2 16.5C10 16 9.2 15.2 8.6 13.9Z" fill="#C8701A" stroke="#8A4B1F" stroke-width=".8" stroke-linejoin="round"/><path d="M11.4 7.2c1.1-1.6 2.8-2.4 4.4-2.2" stroke="#F4BE63" stroke-width="1.1" stroke-linecap="round" fill="none"/><g fill="#F4BE63"><circle cx="16.8" cy="8.2" r=".75"/><circle cx="14" cy="10.6" r=".7"/><circle cx="18.4" cy="11.6" r=".6"/><circle cx="12.4" cy="13.4" r=".55"/></g></g></g><g class="steam" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".7"><path d="M560 150c-5-6 5-10 0-16"/><path d="M590 146c-5-6 5-10 0-16"/><path d="M620 150c-5-6 5-10 0-16"/></g><g fill="#FFC15E" class="lanterns"><circle cx="538" cy="166" r="4.5"/><circle cx="572" cy="162" r="4.5"/><circle cx="606" cy="166" r="4.5"/><circle cx="640" cy="162" r="4.5"/><circle cx="674" cy="166" r="4.5"/><circle cx="708" cy="162" r="4.5"/></g><path d="M520 162 Q620 176 720 162" stroke="#7a4a2a" stroke-width="1.2" fill="none" opacity=".5"/><path d="M0 214 C200 206 380 222 600 216 S980 204 1200 214 V260 H0z" fill="url(#groundG)"/><path d="M40 240 C240 222 400 252 600 236 S900 222 1160 238" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="1 11" opacity=".95"/><g stroke="#fff" stroke-width="3"><circle cx="200" cy="234" r="8" fill="#E69628"/><circle cx="600" cy="236" r="8" fill="#C2551F"/><circle cx="1000" cy="230" r="8" fill="#252D4A"/></g></svg><img class="walker weasel" src="/plan/characters/transparent/weasel-side.png" alt=""><img class="walker raccoon" src="/plan/characters/transparent/raccoon-side.png" alt=""></div><div class="t-day"><span class="t-when">낮</span><b>중구·동구 관광</b><small>근대골목·서문시장 등 운영 중인 곳 위주</small><em class="chick-note">${닭}치킨은 장소 해설·이야기로 가볍게</em></div><div class="t-eve"><span class="t-when">저녁</span><b>대구 음식 중에서 고르기</b><span class="eve-opts"><i class="opt-chicken">${닭}평화시장 닭똥집골목</i><i>동성로 닭요리</i><i>다른 대구 음식</i></span></div><div class="t-night"><span class="t-when">밤</span><b>근거리는 귀가, 원거리는 하룻밤</b><small>야경 → 숙박 → 다음 날 오전 · 가족 코스는 술 없이</small></div></section>`;}
  const api={문장,짧게,상태,할일,보완요약,위치안내,장소패널,입장화면,닭,치킨장소};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.기획표시=api;
})(typeof globalThis!=='undefined'?globalThis:this);

if(typeof document!=='undefined'){
// 담당자 화면: ① 조건 고르기 → ② AI 에이전트들이 코스를 만드는 모습 → ③ 코스 확인(동선·시간표).
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain=s=>esc(기획표시.문장(s));
const short=s=>esc(기획표시.짧게(s));
const slotName=s=>({'낮오후':'오후','2일차오전':'둘째 날 오전'}[s]||s);
const stopName=s=>기획표시.문장((s.표시명||s.장소명||(s.시간칸==='2일차오전'?'둘째 날 오전':slotName(s.시간칸))||'일정 미정').split(/\s*[—–]\s*/)[0]);
async function get(url){const r=await fetch(url);const d=await r.json();if(!r.ok)throw new Error(d.오류||'불러오기 실패');return d;}
let token=null,poll=null,tick=null,last=null,savedItems=null;
async function post(url,body){
  token=token||(await get('/api/session')).token;
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':token},body:JSON.stringify(body)});
  const d=await r.json();if(!r.ok)throw Object.assign(new Error(d.오류||'요청 실패'),{status:r.status});return d;
}
const guide=n=>`<ol class="guide">${['조건 고르기','AI가 코스 만들기','코스 확인','홍보물 · 번역','최종 산출물'].map((t,i)=>`<li class="${i+1===n?'on':''}"><b>${i+1}</b>${t}</li>`).join('')}</ol>`;
const 칸색=s=>s.일차===2&&s.시간칸==='2일차오전'?'day':['저녁'].includes(s.시간칸)?'eve':['밤','숙박'].includes(s.시간칸)?'night':'day';

// ---------- 지난 코스 목록 ----------
async function loadList(select){
  const box=$('saved');
  try{
    const runs=await get('/api/runs');const items=[];
    const infos=await Promise.all(runs.map(run=>get('/api/course?id='+encodeURIComponent(run.id)).catch(()=>null)));  // 한 번에 받아 첫 화면 목록이 빨리 뜨게
    runs.forEach((run,i)=>{for(const t of infos[i]?.시험목록||[])if(t.시험id)items.push({id:t.시험id,조건:run.조건,시각:t.기록시각||''});});
    items.sort((a,b)=>b.시각.localeCompare(a.시각));savedItems=items;renderRecent();
    if(!items.length){box.innerHTML='<p class="empty">아직 만든 코스가 없어요.</p>';return items;}
    box.innerHTML='';
    for(const it of items){
      const c=it.조건||{};const b=document.createElement('button');b.dataset.id=it.id;
      b.innerHTML=`<b>${esc([c.계절,c.체류기간].filter(Boolean).join(' · '))}</b> ${esc([(c.언어권||[]).join('·'),(c.지역||[]).join('·')].filter(Boolean).join(' · '))}<br><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small>`;
      b.onclick=()=>{hideHistory();show(it.id,c);};box.append(b);
    }
    if(select)show(select,(items.find(x=>x.id===select)||{}).조건||{});
    return items;
  }catch(e){box.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return [];}
}
function renderRecent(){
  const box=$('recentList');if(!box||!savedItems)return;
  if(!savedItems.length){box.innerHTML='<div class="recent-empty"><img src="/plan/characters/promo/raccoon-front.png" alt=""><p>아직 만든 코스가 없어요.<br>첫 코스를 기획해 보세요.</p></div>';return;}
  box.innerHTML=savedItems.slice(0,3).map(it=>{const c=it.조건||{};return `<button type="button" class="recent-item stay-${c.체류기간==='당일'?'day':'night'}" data-id="${esc(it.id)}"><span class="recent-band" aria-hidden="true"></span><b>${esc([c.계절,c.체류기간].filter(Boolean).join(' · ')||'조건 미기록')}</b><span>${esc([(c.언어권||[]).join('·'),(c.지역||[]).join('·')].filter(Boolean).join(' · '))}</span><small>${esc(it.시각.replace('T',' ').slice(0,16))}</small></button>`;}).join('');
  box.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>{const it=savedItems.find(x=>x.id===b.dataset.id);show(it.id,it.조건||{});});
  fitBackdrop();
}
function fitBackdrop(){
  const b=document.querySelector('.entry-backdrop'),e=document.querySelector('.entry-screen');
  if(!b||!e){removeEventListener('resize',fitBackdrop);return;}
  b.style.height=Math.round(e.getBoundingClientRect().bottom+scrollY+150)+'px';  // 첫 화면 내용 아래 150px에 대구 지평선
}
function setView(v){document.body?.setAttribute?.('data-view',v);}
function mark(id){$('saved').querySelectorAll('button').forEach(x=>x.classList.toggle('on',x.dataset.id===id));}
function hideHistory(){const panel=$('historyPanel');if(panel)panel.hidden=true;$('historyBtn')?.setAttribute('aria-expanded','false');}
function showHistory(){const panel=$('historyPanel');if(!panel)return;panel.hidden=false;$('historyBtn').setAttribute('aria-expanded','true');$('historyClose').focus();}
function showLanding(){hideHistory();mark(null);setView('landing');$('progress').hidden=!(last&&last.상태==='진행중');$('main').innerHTML=기획표시.입장화면();$('entryNew').onclick=()=>newForm();$('entrySaved').onclick=showHistory;$('toDay').onclick=()=>$('dayTitle').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});renderRecent();fitBackdrop();addEventListener('resize',fitBackdrop);}

// ---------- ① 조건 고르기 (주문서) ----------
const 선택지={계절:['봄','여름','가을','겨울'],언어권:['영어권','일본어','중국어 간체','중국어 번체'],지역:['중구','동구'],체류기간:['당일','1박2일']};
const 여러개={언어권:1,지역:1};
function newForm(){
  hideHistory();
  mark(null);setView('form');
  const q=(name,label,help)=>`<div class="q"><span>${label}${help?`<small>${help}</small>`:''}</span><div class="pills" data-name="${name}">${선택지[name].map(v=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(v)}">${esc(v)}</button>`).join('')}</div></div>`;
  $('main').innerHTML=`<section class="card">${guide(1)}
    <h2>어떤 코스를 만들까요?</h2>
    <p class="lead">꼭 지킬 조건을 고르고, 바라는 점이 있으면 적어 주세요. AI 에이전트들이 자료 확인부터 코스 초안까지 이어서 만들어요.</p>
    <p class="note">고른 지역과 여행 조건 안에서 코스를 제안해요. 시작·종료 장소나 식사 방식이 미정이어도 초안부터 볼 수 있어요.</p>
    <form class="order order-layout" id="order"><div class="order-fields">
      ${q('계절','계절')}${q('언어권','대상 언어권','여러 개 고를 수 있어요')}${q('지역','지역','여러 개 고를 수 있어요')}${q('체류기간','체류 기간')}
      <div class="sec">바라는 점 <span class="note">(선택 · 지키기 어려우면 AI가 이유를 남기고 조정할 수 있어요)</span></div>
      <label class="q"><span>목표</span><input name="목표" maxlength="300" placeholder="예: 필수 대상은 일본인 커플, 중구에서 저녁과 숙박으로 연결"></label>
      <label class="q"><span>희망 사항<small>한 줄에 하나</small></span><textarea name="희망" rows="3" placeholder="예: 저녁 이후 야경을 넣고 싶어요&#10;이동을 줄이고 여유롭게 식사하고 싶어요"></textarea></label>
      <section class="upload-data"><h3>가지고 있는 자료 함께 쓰기 <small>(선택)</small></h3>
        <p class="note">CSV·엑셀(XLSX) 표를 읽어 수요 근거에 더해요. 1MB 이하, 시트당 100행까지예요. 출처·기간·지역·대상·항목·값·단위·표본수 열이 필요해요.</p>
        <p><a href="/plan/examples/demo.csv" download>시연용 가상 CSV 받기</a> · <a href="/plan/examples/demo.xlsx" download>시연용 가상 엑셀 받기</a></p>
        <label class="q"><span>자료 파일</span><input type="file" id="dataFile" accept=".csv,.xlsx"></label>
        <div id="uploadPreview" aria-live="polite"></div><p class="note" id="uploadState">올리지 않으면 기존 자료만 사용해요.</p>
        <button type="button" class="btn" id="uploadRemove" hidden>자료 빼기</button>
      </section>
      </div><aside class="order-summary" aria-label="만들어질 코스 미리보기"><div class="peek" aria-hidden="true"><img src="/plan/characters/promo/raccoon-front.png" alt=""></div><h3>만들어질 코스</h3><div class="sum-chips" id="sumChips"></div><ol class="sum-day" id="sumDay"></ol>
      <p class="agree">시작하면 중간 알림·경고는 기록에 남기고 <b>코스 초안까지 자동으로 진행</b>해요. 위에서 적용한 자료를 함께 쓰며, 홍보물과 최종 문서는 코스를 확인한 뒤 따로 만들어요.</p>
      ${last&&last.상태==='진행중'?'<p class="note">지금 만들고 있는 코스가 있어요. 한 번에 하나씩 만들어요. 끝난 뒤 시작해 주세요.</p>':''}
      <div class="go"><span class="note" id="need"></span><span class="err" id="newErr"></span><button class="btn primary big" id="newGo" type="submit" disabled>코스 만들기 시작</button></div></aside>
    </form></section>`;
  const f=$('order');
  let appliedUpload=null,uploadPending=false,uploadVersion=0,uploadError='';
  const 값=()=>{const v={};for(const n in 선택지){const on=[...f.querySelectorAll(`[data-name="${n}"] [aria-pressed=true]`)].map(b=>b.dataset.v);v[n]=여러개[n]?on:on[0]||'';}return v;};
  const check=()=>{const v=값();const miss=Object.keys(선택지).filter(n=>!v[n]||!v[n].length).map(n=>({계절:'계절',언어권:'언어권',지역:'지역',체류기간:'체류 기간'}[n]));
    $('need').textContent=uploadPending?(uploadError||'파일 미리보기 아래의 「내용 확인 · 이 자료 적용」을 눌러 주세요.'):miss.length?`남은 것: ${miss.join(', ')}`:'모든 조건을 골랐어요.';$('newGo').disabled=miss.length>0||uploadPending;미리보기(v);};
  const 미리보기=v=>{
    const chips=[v.계절,(v.언어권||[]).join('·'),(v.지역||[]).join('·'),v.체류기간].filter(Boolean);
    $('sumChips').innerHTML=chips.length?chips.map(c=>`<span class="chip">${esc(c)}</span>`).join(''):'<span class="note">왼쪽에서 조건을 고르면 여기에 모여요.</span>';
    const 지역=(v.지역||[]).length?v.지역.join('·'):'선택한 지역';
    const 단계=v.체류기간==='당일'?[['day','낮',`${지역} 관광`],['eve','저녁','대구 음식 중 선택 · 닭요리 포함'],['home','이후','귀가']]
      :v.체류기간==='1박2일'?[['day','낮',`${지역} 관광`],['eve','저녁','대구 음식 중 선택 · 닭요리 포함'],['night','밤','야경 → 숙박'],['day2','둘째 날','오전 일정 후 귀가']]
      :[['day','낮','관광'],['eve','저녁','식사 선택'],['night','이후','체류 기간에 따라 달라져요']];
    $('sumDay').className='sum-day'+(v.체류기간?'':' is-empty');
    $('sumDay').innerHTML=단계.map(([k,t,d])=>`<li class="s-${k}"><span>${t}</span><p>${k==='eve'&&v.체류기간?기획표시.닭:''}${esc(d)}</p></li>`).join('');
  };
  f.querySelectorAll('.pills').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('.pill');if(!b)return;
    if(!여러개[g.dataset.name])g.querySelectorAll('.pill').forEach(x=>x!==b&&x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');check();}));
  $('uploadRemove').onclick=()=>{uploadVersion++;appliedUpload=null;uploadPending=false;uploadError='';$('dataFile').value='';$('uploadPreview').innerHTML='';$('uploadState').textContent='자료를 뺐어요. 기존 자료만 사용해요.';$('uploadRemove').hidden=true;check();};
  $('dataFile').onchange=async()=>{
    const version=++uploadVersion,file=$('dataFile').files[0];appliedUpload=null;uploadError='';
    if(!file){$('uploadRemove').onclick();return;}
    uploadPending=true;$('uploadRemove').hidden=false;$('uploadPreview').innerHTML='';$('uploadState').textContent='파일을 읽고 숫자·열을 검사하고 있어요.';check();
    try{
      if(file.size>1024*1024)throw new Error('1MB 이하 파일을 골라 주세요.');
      const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
      const data=await post('/api/plan/upload',{파일명:file.name,내용:btoa(binary)});
      if(version!==uploadVersion||$('order')!==f)return;
      const sheets=data.시트.filter(s=>s.행수>0);
      $('uploadPreview').innerHTML=`<label>사용할 시트 <select id="uploadSheet">${sheets.map((s,i)=>`<option value="${i}">${esc(s.이름)} (${s.행수}행)</option>`).join('')}</select></label><div id="uploadRows"></div><button type="button" class="btn primary" id="uploadApply">내용 확인 · 이 자료 적용</button>`;
      const preview=()=>{appliedUpload=null;uploadPending=true;const s=sheets[Number($('uploadSheet').value)];
        $('uploadRows').innerHTML=`<p>${esc(data.안내)}</p><div class="upload-table"><table><thead><tr><th>항목</th><th>값</th><th>대상</th><th>기간·지역</th><th>출처</th></tr></thead><tbody>${s.행.slice(0,5).map(r=>`<tr><td>${esc(r.항목)} ${esc(r.세부항목||'')}</td><td>${esc(r.값)}${esc(r.단위)}</td><td>${esc(r.대상)}</td><td>${esc(r.기간)} · ${esc(r.지역)}</td><td>${esc(r.출처)}</td></tr>`).join('')}</tbody></table></div><p class="note">${s.행수}행 중 처음 5행을 보여 줍니다. 다른 지역·계절 행은 코스에 적용할 때 제외해요.</p>${s.경고.map(w=>`<p class="err">${esc(w)}</p>`).join('')}${data.시트.filter(x=>!x.행수).map(x=>`<p class="note">${esc(x.이름)}: 읽을 수 있는 표가 없어 사용하지 않아요.</p>`).join('')}`;
        $('uploadState').textContent='원하는 시트인지 확인한 뒤 적용해 주세요.';$('uploadApply').disabled=false;check();};
      $('uploadSheet').onchange=preview;preview();
      $('uploadApply').onclick=()=>{const s=sheets[Number($('uploadSheet').value)];appliedUpload={업로드id:data.업로드id,시트:s.이름,확인:true};uploadPending=false;$('uploadState').textContent=`${data.파일명} · ${s.이름} ${s.행수}행을 함께 검토해요.`;$('uploadApply').disabled=true;check();};
    }catch(e){if(version===uploadVersion&&$('order')===f){uploadError='업로드 실패: '+(e.status===404?'실행 중인 서버가 업로드 기능을 지원하지 않습니다. 서버를 재시작하고 화면을 새로고침해 주세요.':e.message);$('uploadState').textContent=uploadError;check();}}
  };
  check();
  f.onsubmit=async e=>{e.preventDefault();$('newGo').disabled=true;$('newErr').textContent='';
    try{if(uploadPending)throw new Error('자료 내용을 확인하고 적용하거나 빼 주세요.');const p=await post('/api/plan/start',{...값(),목표:f.목표.value.trim(),희망:f.희망.value.split('\n').map(x=>x.trim()).filter(Boolean),자동진행동의:true,...(appliedUpload?{기관업로드:appliedUpload}:{})});  // 시작 버튼 옆 안내 문구를 보고 누르는 것이 동의
      $('main').innerHTML='';showProgress(p);watch(p.기획id);}
    catch(err){$('newErr').textContent=err.message;check();}};
}

// ---------- ② 진행 상황: 지금 일하는 에이전트 ----------
const 아이콘=[ // 돋보기 · 막대그래프 · 지도핀 · 체크 (직접 그린 단순 도형)
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 20V11M12 20V5M19 20v-6"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-6-5.6-6-10.5a6 6 0 0 1 12 0C18 15.4 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="6" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M12 8.5v4M12 12.5 6.5 16M12 12.5l5.5 3.5"/></svg>'];
const 걸린=(a,b)=>{const s=Math.max(0,Math.round(((b?new Date(b):new Date())-new Date(a))/1000));return s<60?`${s}초`:`${Math.floor(s/60)}분 ${s%60}초`;};
function showProgress(p){
  last=p;const box=$('progress');if(!p){box.hidden=true;return;}
  box.hidden=false;const c=p.조건||{};const 진행=p.상태==='진행중';
  const head={진행중:'AI 에이전트들이 코스를 만들고 있어요',완료:'코스 초안이 나왔어요',멈춤:'진행이 멈췄어요',중단됨:'실행이 끊겼어요'}[p.상태]||p.상태;
  const cards=(p.단계||[]).map((s,i)=>{const cls={진행중:'now',완료:'done',실패:'fail'}[s.상태]||'';
    const st=s.상태==='진행중'?`일하는 중 · <span data-since="${esc(s.시작)}">${걸린(s.시작)}</span>`:s.상태==='완료'?`완료 · ${s.시작?걸린(s.시작,s.끝):''}`:s.상태==='실패'?'멈춤':'차례 기다리는 중';
    return `<div class="agent ${cls}"><span class="tag">${s.AI===false?'코드':'AI'}</span><div class="ic">${아이콘[i]||''}</div><b>${esc(s.에이전트||s.이름)}</b><p>${esc(s.하는일||s.이름)}</p><div class="st">${st}</div></div>`;}).join('');
  const w=p.일하는중;
  const msg=진행&&w?`<div class="working">지금 <b>${esc(w.에이전트)}</b>가 일하고 있어요 — ${esc(w.하는일)}. 몇 분 걸릴 수 있어요. 창을 닫거나 새로고침해도 이어서 볼 수 있어요.</div>`
    :p.상태==='완료'?`<div class="working ok">${esc(p.안내||'')}</div>`:`<div class="working ${진행?'':'stop'}">${esc(p.안내||'')}</div>`;
  const 활동=(p.활동||[]).slice(-8).reverse();
  const 로그=활동.length?`<details><summary>만드는 과정 자세히 보기</summary><ol class="log">${활동.map(a=>`<li class="${a.상태==='진행중'?'now':a.상태==='실패'?'fail':''}"><b>${esc(a.에이전트)}</b> ${plain(a.하는일)}${a.결정?`<br><span class="note">${short(a.결정)}</span>`:''}<span class="when">${a.상태==='진행중'?'일하는 중':a.시작?걸린(a.시작,a.끝):''}</span></li>`).join('')}</ol></details>`:'';
  const 정리=p.정리;const 남은=정리?정리.사람이정할것:((p.검사&&p.검사.남은문제)||[]);
  box.innerHTML=`${guide(p.상태==='완료'?3:2)}${진행?'<div class="progress-walk" aria-hidden="true"><span class="pw-path"></span><img class="walker weasel" src="/plan/characters/transparent/weasel-side.png" alt=""><img class="walker raccoon" src="/plan/characters/transparent/raccoon-side.png" alt=""></div>':''}<div class="top"><div><h2>${esc(head)}</h2><span class="note">${esc([c.계절,(c.언어권||[]).join('·'),(c.지역||[]).join('·'),c.체류기간].filter(Boolean).join(' · '))}${p.목표?' · 목표: '+esc(p.목표):''}</span></div>
    <div>${p.상태==='완료'&&p.시험id?`<button class="btn primary" id="seeNew">만든 코스 보기</button> `:''}${진행?'':'<button class="btn" id="closeP">닫기</button>'}</div></div>
    ${msg}<div class="agents">${cards}</div>
    ${로그}
    ${남은.length?'<p class="note">담당자가 정할 항목은 만든 코스에서 간단히 확인할 수 있어요.</p>':''}
    ${p.희망&&p.희망.length?`<p class="note">바라는 점: ${p.희망.map(esc).join(' / ')}</p>`:''}`;
  if($('seeNew'))$('seeNew').onclick=()=>{box.hidden=true;loadList(p.시험id);};
  if($('closeP'))$('closeP').onclick=()=>{box.hidden=true;};
  clearInterval(tick);if(진행)tick=setInterval(()=>box.querySelectorAll('[data-since]').forEach(x=>x.textContent=걸린(x.dataset.since)),1000);
}
function watch(id){
  clearInterval(poll);
  poll=setInterval(async()=>{
    try{const p=await get('/api/plan/status?id='+encodeURIComponent(id));showProgress(p);
      if(p.상태!=='진행중'){clearInterval(poll);clearInterval(tick);if(p.상태==='완료')loadList();}}
    catch{clearInterval(poll);}
  },3000);
}

// ---------- ③ 코스 확인 ----------
async function show(id,cond,안,버전){
  mark(id);setView('course');const main=$('main');main.innerHTML='<p class="empty">불러오는 중…</p>';
  try{const rec=await get('/api/plan/record?id='+encodeURIComponent(id)+(안?'&안='+안:'')+(버전?'&버전='+버전:''));if(rec.있음)return showRecord(id,cond||{},rec);}catch{}
  let s;try{s=await get('/api/plan/course?id='+encodeURIComponent(id));}catch(e){main.innerHTML=`<p class="empty">${esc(e.message)}</p>`;return;}
  const k=s.조건||{};cond=cond||{};
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간,k.시작지점&&k.종료지점&&!(k.시작지점==='미확인'&&k.종료지점==='미확인')?`${k.시작지점} → ${k.종료지점}`:'시작·종료 장소 미정'].filter(Boolean);
  const days=s.출발가능요일?.length?`<p>출발 가능 요일: <span class="days">${esc(s.출발가능요일.join(' · '))}</span> <span class="note">(장소별 정기휴무로 계산)</span></p>`:'';
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
  <section class="card ai"><div class="aihead"><span class="aibadge">AI 코스 초안</span><strong>${s.코스있음?'담당자가 확인할 것':'아직 코스가 없어요'}</strong></div>${days}
    ${s.확인할것.length?`<ul>${s.확인할것.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="note">확인할 것이 없어요.</p>'}
    <p class="note">이전 방식으로 저장된 초안이에요. 이 기록에는 A·B 비교 정보가 없어요. 아래 시각은 추천 동선을 살펴보는 기준이며 실제 예약·운영시간을 확인해야 해요.</p></section>
  ${s.코스있음?`<section class="card map-launch"><div><h3>동선 · 시간표</h3><p class="note">큰 지도에서 방문 순서와 장소 설명을 살펴보세요.</p></div><button class="btn primary" id="openMap">지도 크게 보기 ↗</button></section>`:''}`;
  if(s.코스있음)$('openMap').onclick=()=>openMap(s.일정,{id,cond});
}
const 분류이름={AI수정:['AI가 고칠 것','시간 겹침·형식 오류처럼 코스가 틀린 것. 총괄이 코스 에이전트에게 고치게 해요. 남아 있으면 고치지 못한 것이에요.'],
  자료보완:['자료 보완','자료가 없어 생긴 것. 수집 에이전트가 저장소 자료에서 찾아요. 남아 있으면 못 찾은 것이에요.'],
  사람결정:['담당자가 정할 것','시작·종료, 2일차 오전, 식사 방식, 지키지 못한 희망처럼 사람이 정할 것이에요.']};
const 칸이름={낮:'낮',낮오후:'오후',점심:'점심',저녁:'저녁',밤:'밤',숙박:'숙박','2일차오전':'둘째 날 오전'};
function 시간표(일정){
  if(!일정.length)return '<div class="day-schedule"><p class="empty">아직 일정이 없어요.</p></div>';
  let day=null;const days=new Set(일정.map(x=>x.일차)).size;
  const rows=일정.map(x=>{const n=stopName(x),c=칸색(x);const head=days>1&&x.일차!==day?`<li class="ds-day">${esc(x.일차)}일차</li>`:'';day=x.일차;
    return head+`<li class="ds-row slot-${c}"><span class="ds-time">${esc(x.시각||'미정')}</span><span class="ds-dot" aria-hidden="true"></span><span class="ds-name">${기획표시.치킨장소(n)?`<em class="chick-stop" title="치킨·닭요리 요소">${기획표시.닭}${esc(n)}</em>`:esc(n)}<small>${esc(칸이름[x.시간칸]||x.시간칸||'')}</small></span></li>`;}).join('');
  return `<div class="day-schedule"><h3>하루 시간표 <span class="note">권장 순서·시각</span></h3><ol>${rows}</ol></div>`;
}
function showRecord(id,cond,rec){
  const main=$('main');const 정리=rec.정리;const 안=정리.안.find(a=>a.안id===rec.안id);const s=rec.요약;
  const 원희망=Object.fromEntries((rec.원래요청.희망||[]).map(h=>[h.id,h.내용]));
  const 이전=rec.버전!==안.버전;
  const 상태=기획표시.상태({...rec,검증:이전?'검증 전':안.검증});
  const 주요확인=기획표시.보완요약(rec);
  const tabs=정리.안.map(a=>{
    const active=a.안id===rec.안id;
    const label=a.안id==='A'?'A안 · 내 요청을 우선한 안':`${a.안id}안 · 구성을 조정한 안`;
    const reason=a.대안설명?.왜||a.이유||a.설명||'저장된 코스의 동선과 일정을 확인해 보세요.';
    return `<button class="tab plan-choice ${active?'on':''}" aria-pressed="${active}" data-plan="${esc(a.안id)}"><span class="choice-top"><b>${esc(label)}</b><span class="choice-badge">${active?'보고 있는 코스':'다른 코스 보기'}</span></span><small>${short(reason)}</small></button>`;
  }).join('')+(!정리.안.some(a=>a.안id==='B')?`<div class="tab plan-choice missing-plan"><span class="choice-top"><b>B안 · 구성을 조정한 안</b><span class="choice-badge">미생성</span></span><small>${esc(정리.대안상태?.이유||'이 저장 기록에는 B안과 미생성 사유가 저장되지 않았어요.')}</small></div>`:'');
  const vers=(안.버전들||[]).length>1?`<div class="vers"><span>수정 이력</span> ${안.버전들.map(v=>`<button class="pill" aria-pressed="${v===rec.버전}" data-v="${v}">${v}번째 초안${v===안.버전?' · 최신':''}</button>`).join('')}</div>`:'';
  const 바꾼=Object.entries(안.바꾼희망||{});
  const 설명=안.대안설명||{};
  const alt=바꾼.length||안.대안설명?`<div class="alternative-note"><h3>이 대안은 이렇게 달라요</h3>
    ${바꾼.map(([k,v])=>`<p class="chg"><s>${plain(원희망[k]||'원래 희망')}</s> → <b>${plain(v)}</b></p>`).join('')}
    <p>${short(설명.왜||안.이유||'변경 이유는 팀 검토가 필요해요.')}</p>
    ${설명.남은문제?`<p class="note">더 확인할 점: ${short(설명.남은문제)}</p>`:''}</div>`:'';
  // 이전 버전에는 최신 버전의 희망 반영 설명을 붙이지 않는다.
  const wish=!이전&&(안.희망반영||[]).length?`<section class="card request-card"><h3>요청을 이렇게 반영했어요</h3><ul class="wish">${안.희망반영.map(h=>{
    const status=({지킴:'일정에 반영',일부:'일부 반영',못지킴:'조정 필요'})[h.반영]||'확인 필요';
    const reason=기획표시.문장(h.이유||'반영 이유가 아직 정리되지 않았어요.');
    return `<li class="w-${esc(h.반영)}"><div><span class="tagw">${esc(status)}</span> <b>${plain(h.내용||원희망[h.희망id]||'요청 사항')}</b></div><p>${esc(기획표시.짧게(reason))}</p>${reason.length>140?`<details class="reason-more"><summary>반영 이유 더 보기</summary><p>${esc(reason)}</p></details>`:''}</li>`;
  }).join('')}</ul></section>`:'';
  const 필수=rec.필수조건반영||안.필수조건반영||[];
  const required=필수.length?`<details class="condition-detail"><summary>선택 조건 반영 내용</summary><ul>${필수.map(x=>`<li><b>${plain(x.조건)} · ${plain(x.반영)}</b><p>${plain(x.이유||'이유를 다시 확인해야 합니다.')}</p></li>`).join('')}</ul></details>`:'';
  const 분=rec.분류||{};
  const 검사=`<h3>검사 원문</h3><p class="note">아래는 팀 검토용 기록이에요. 같은 확인 항목이 여러 검사에서 반복될 수 있어요.</p><div class="three">${Object.keys(분류이름).map(k=>`<div class="col c-${k}"><b>${분류이름[k][0]} <span class="cnt">${(분[k]||[]).length}</span><span class="sr-only"> · ${esc(rec.안id)}안 ${rec.버전}버전</span></b><ul>${(분[k]||[]).map(x=>`<li>${esc(x.문구)}<small> · ${esc(x.출처)}</small></li>`).join('')||'<li class="none">없음</li>'}</ul></div>`).join('')}</div>`;
  const 기=rec.부분수정기록;
  const 부분=기?`<p class="note">최근 수정 요청: ${plain(기.요청)}</p>`:'';
  const chips=[cond.계절,(cond.언어권||[]).join('·'),(cond.지역||[]).join('·'),cond.체류기간].filter(Boolean);
  main.innerHTML=`<div class="cond">${chips.map(c=>`<span class="chip">${esc(c)}</span>`).join('')}</div>
    <section class="card ai recommendation"><div class="aihead"><span class="aibadge">코스 초안</span><h2>코스 제안</h2><span class="draft-badge">확정 전 초안</span>${s.코스있음?`<button class="btn primary compare-map-button" id="openMap" title="동선 · 시간표">지도 크게 보기 ↗</button>`:''}</div>
      <p class="lead">${정리.안.length>1?'요청을 바탕으로 만든 코스와 대안을 비교해 보세요.':'요청을 바탕으로 만든 코스예요. 동선과 일정을 먼저 살펴보세요.'}</p>
      <div class="tabs plan-choices">${tabs}</div>
      ${rec.기관업로드?`<details class="upload-result"><summary>함께 참고한 자료: ${esc(rec.기관업로드.파일명)} · 적용 ${esc(rec.기관업로드.적용행수)}행${rec.기관업로드.가상자료?' (시연용 가상 자료 · 실제 조사 아님)':''}</summary>${(rec.기관업로드.경고||[]).map(w=>`<p class="note">${esc(w)}</p>`).join('')}</details>`:''}
      <div class="rec-split">${시간표(s.일정||[])}<div class="rec-side">
      ${이전?'<div class="review-status state-대기"><b>이전 수정본을 보고 있어요</b><p>최신 코스로 돌아가서 현재 검토 내용을 확인해 주세요.</p><button class="btn" id="latestPlan">최신 코스 보기</button></div>':''}
      <div class="review-status state-${상태.종류}" role="status"><b>${esc(상태.제목)}</b><p>${esc(상태.설명)}</p>${주요확인.length?`<ul>${주요확인.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:''}</div>
      ${s.출발가능요일?.length?`<p class="departure"><b>출발 요일 참고</b> ${esc(s.출발가능요일.join(' · '))}<span class="note">정기휴무 기준이에요. 운영 변경 여부는 출발 전 확인해 주세요.</span></p>`:''}
      ${부분}${alt}${required}</div></div></section>
    <section class="card freedom"><h3>어디까지 자유롭게 이용하나요?</h3><p>표시된 순서와 시각은 권장 일정이에요. 관광·식사는 장소의 운영시간 안에서 선택할 수 있도록 기획합니다.</p><p class="note">예약이나 이용권에 실제로 정해진 시간이 있다면 그 조건을 따라야 해요. 미정인 사용처·유효시간·포함 혜택은 아직 확정된 상품 조건이 아니에요. 집결·해산이나 숙소 예약을 먼저 입력할 필요는 없어요.</p></section>
    ${wish}
    <details class="card"><summary>코스 수정하기 · 바꾸고 싶은 부분이 있나요?</summary><p class="note">고른 일정만 다시 제안해요. 나머지 일정과 이전 초안은 보존해요.</p>
      <div class="pills" id="redo">${rec.시간칸.map(k=>`<button type="button" class="pill" aria-pressed="false" data-v="${esc(k)}">${esc(slotName(k))}</button>`).join('')}</div>
      <div class="redo-row"><input id="redoText" maxlength="300" placeholder="예: 낮은 유지하고 저녁만 설문 음식 후보로 바꿔 주세요"><button class="btn primary" id="redoGo" disabled>다시 만들기</button></div>
      <p class="note" id="keep"></p><p class="err" id="redoErr"></p></details>
    <details class="card technical"><summary>팀 검토용 상세 · 수정 이력과 검사 기록</summary><p class="note">${esc(rec.안id)}안은 ${rec.안id==='A'?'원래 요청으로 만든 코스':'구성을 조정한 대안'}이고, ${rec.버전}버전은 같은 코스를 ${rec.버전}번째로 작성한 기록이에요. 서로 다른 여행 상품 ${rec.버전}개를 뜻하지 않아요.</p>${vers}${검사}<p><a href="/admin/">서비스 제공자용 로그 보기 ↗</a></p></details>`;
  if(s.코스있음)$('openMap').onclick=()=>openMap(s.일정,{id,cond,rec});
  if(!이전&&globalThis.홍보화면)globalThis.홍보화면.붙이기(main,{id,cond,rec,돌아가기:()=>show(id,cond,rec.안id,rec.버전)});  // ④ 홍보물 · ⑤ 산출물
  if($('latestPlan'))$('latestPlan').onclick=()=>show(id,cond,rec.안id);
  main.querySelectorAll('.tab[data-plan]').forEach(b=>b.onclick=()=>show(id,cond,b.dataset.plan));
  main.querySelectorAll('.vers .pill').forEach(b=>b.onclick=()=>show(id,cond,rec.안id,b.dataset.v));
  const redo=$('redo');const pick=()=>[...redo.querySelectorAll('[aria-pressed=true]')].map(b=>b.dataset.v);
    const upd=()=>{const p=pick();$('keep').textContent=p.length?`그대로 둘 일정: ${rec.시간칸.filter(k=>!p.includes(k)).map(slotName).join(', ')||'없음'}`:'';$('redoGo').disabled=!p.length||!$('redoText').value.trim();};
  redo.onclick=e=>{const b=e.target.closest('.pill');if(!b)return;b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');upd();};
  $('redoText').oninput=upd;
  $('redoGo').onclick=async()=>{const p=pick();$('redoGo').disabled=true;$('redoErr').textContent='';
    try{const r=await post('/api/plan/revise',{기획id:rec.기획id,안id:rec.안id,바꿀:p,유지:rec.시간칸.filter(k=>!p.includes(k)),요청:$('redoText').value.trim()});
      showProgress(r);watch(r.기획id);window.scrollTo({top:0,behavior:'smooth'});}
    catch(err){$('redoErr').textContent=err.message;upd();}};
}
let mapController=null,mapVersion=0,explorerStops=[],selectedStop=null,returnFocus=null;
function closeMap(){
  const view=$('mapView');if(!view||view.hidden)return;
  mapVersion++;mapController?.destroy();mapController=null;view.hidden=true;setView('course');
  document.body.classList.remove('map-open');
  document.querySelector('.wrap').inert=false;document.querySelector('body > header').inert=false;
  (returnFocus?.isConnected?returnFocus:$('openMap'))?.focus();
}
function openMap(stops,context={}){
  let view=$('mapView');
  if(!view){
    view=document.createElement('section');view.id='mapView';view.className='map-explorer';view.hidden=true;
    view.setAttribute('role','dialog');view.setAttribute('aria-modal','true');view.setAttribute('aria-label','코스 지도 탐색');view.tabIndex=-1;
    document.body.append(view);
    view.addEventListener('keydown',e=>{
      if(e.key==='Escape'){e.preventDefault();closeMap();return;}
      if(e.key==='Tab'){
        const focusable=[...view.querySelectorAll('button,a,summary,[tabindex="0"]')].filter(x=>!x.disabled&&x.getClientRects().length);
        const first=focusable[0],last=focusable.at(-1);
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
      }
    });
  }
  if(view.hidden)returnFocus=document.activeElement;
  mapController?.destroy();mapController=null;selectedStop=null;
  explorerStops=stops.map((s,i)=>({...s,표시명:stopName(s),순번:s.순번??i+1}));
  const plans=context.rec?.정리?.안||[],current=context.rec?.안id;
  const tabs=plans.map(a=>`<button type="button" class="explorer-plan ${a.안id===current?'active':''}" aria-pressed="${a.안id===current}" data-explorer-plan="${esc(a.안id)}">${esc(a.안id)}안</button>`).join('');
  let day=null;const list=explorerStops.map((s,index)=>{
    const heading=day!==s.일차?`<h3 class="explorer-day">${esc(s.일차)}일차</h3>`:'';day=s.일차;
    const next=explorerStops[index+1],segment=next&&next.일차===s.일차?`<div class="stop-transfer"><span data-route-time="${s.순번}">경로 확인 중</span><button type="button" data-play-segment="${s.순번}" disabled aria-label="${esc(stopName(s))}에서 ${esc(stopName(next))}까지 구간 재생">구간 재생</button></div>`:'';
    return heading+`<button type="button" class="explorer-stop slot-${칸색(s)}" data-stop="${s.순번}" aria-pressed="false"><span class="stop-order">${s.순번}</span><span><small>${esc(s.시각||'시각 미정')}${칸이름[s.시간칸]?' · '+esc(칸이름[s.시간칸]):''}</small><b>${기획표시.치킨장소(stopName(s))?기획표시.닭:''}${esc(stopName(s))}</b></span></button>${segment}`;
  }).join('');
  view.innerHTML=`<header class="explorer-header"><button type="button" class="btn" id="backCompare">← 코스 비교</button><h1>${current?esc(current)+'안':'저장 코스'} · 지도 탐색</h1><nav aria-label="비교할 코스">${tabs}</nav>${plans.length&&!plans.some(a=>a.안id==='B')?'<span class="note">B안 아직 없음</span>':''}</header>
    <div class="explorer-body"><nav class="explorer-list" aria-label="방문 순서"><h2>방문 순서</h2>${list}</nav>
    <div class="explorer-map"><div id="mapbox"></div><p class="map-reference-note">시설·권역의 대표 위치 기준 · 코스 이해용으로 정리한 동선(실제 보행 안내와 다를 수 있음) · 이동시간은 원본 자료 기준 · 대중교통 경로 미연결</p></div>
    <aside class="place-panel" id="placePanel" aria-label="선택한 장소 설명" aria-live="polite" hidden></aside></div>`;
  view.hidden=false;view.classList.remove('place-open');document.body.classList.add('map-open');setView('map');
  document.querySelector('.wrap').inert=true;document.querySelector('body > header').inert=true;
  $('backCompare').onclick=closeMap;
  view.querySelectorAll('[data-stop]').forEach(button=>button.onclick=()=>selectStop(Number(button.dataset.stop)));
  view.querySelectorAll('[data-play-segment]').forEach(button=>button.onclick=()=>mapController?.playLeg?.(Number(button.dataset.playSegment)));
  view.querySelectorAll('[data-explorer-plan]').forEach(button=>button.onclick=async()=>{
    if(button.dataset.explorerPlan===current)return;
    button.disabled=true;const version=mapVersion;
    try{
      const rec=await get('/api/plan/record?id='+encodeURIComponent(context.id)+'&안='+encodeURIComponent(button.dataset.explorerPlan));
      if(view.hidden||mapVersion!==version)return;
      showRecord(context.id,context.cond||{},rec);openMap(rec.요약.일정,{...context,rec});
    }catch{button.disabled=false;button.textContent='불러오기 재시도';}
  });
  $('backCompare').focus();draw(explorerStops);
}
function selectStop(number,fromMap=false){
  const stop=explorerStops.find(s=>s.순번===number);if(!stop)return;
  selectedStop=number;
  const view=$('mapView'),panel=$('placePanel');view.classList.add('place-open');panel.hidden=false;
  panel.innerHTML=기획표시.장소패널(stop);
  view.querySelectorAll('[data-stop]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.stop)===number)));
  panel.querySelector('[data-place-close]').onclick=()=>{
    panel.hidden=true;view.classList.remove('place-open');view.querySelector(`[data-stop="${number}"]`)?.focus();
  };
  panel.querySelectorAll('[data-explore-candidate]').forEach(button=>button.onclick=()=>{const index=Number(button.dataset.exploreCandidate);showCandidate(number,index);mapController?.previewCandidate?.(number,index);});
  if(!fromMap)mapController?.selectStop?.(number,{notify:false});
}
function showCandidate(number,index){
  const stop=explorerStops.find(s=>s.순번===number),candidate=stop?.식당후보?.[index];if(!candidate)return;
  if(selectedStop!==number)selectStop(number,true);
  const panel=$('candidatePreview');if(panel)panel.innerHTML=`<p><b>${esc(candidate.이름)}</b></p><p class="note">후보 미리보기 · 방문 확정은 바뀌지 않습니다.${candidate.좌표?'':' 위치는 확인 중입니다.'}</p>`;
}
function draw(stops){
  const version=++mapVersion;mapController?.destroy();mapController=null;
  const box=$('mapbox');box.innerHTML='<p class="note">큰 지도를 불러오는 중…</p>';
  import('/plan/three-map.js').then(m=>{
    if(version!==mapVersion)return null;
    return m.mount(box,stops,{externalDetails:true,onSelect:(number,event)=>{
      selectStop(number,true);
      if(event?.playback){$('placePanel').hidden=true;$('mapView').classList.remove('place-open');}
    },onCandidate:showCandidate});
  }).then(controller=>{
    if(!controller)return;if(version!==mapVersion){controller.destroy();return;}
    mapController=controller;if(selectedStop!==null)controller.selectStop?.(selectedStop,{notify:false});
    for(const node of $('mapView').querySelectorAll('[data-route-time]')){
      const leg=controller.routes?.find(leg=>leg.from===Number(node.dataset.routeTime));
      if(!leg){const s=stops.find(x=>x.순번===Number(node.dataset.routeTime));node.textContent=코스지도모델.tableLabel(s?.다음이동)||'경로 미확인';continue;}
      const alt=leg.mode==='transit'?코스지도모델.timeLabel(leg.walkSeconds):leg.transitSeconds?'대중교통 약 '+Math.round(leg.transitSeconds/60)+'분':'대중교통 자료 없음';
      node.innerHTML=`<b class="mode-primary ${leg.mode==='transit'?'transit':'foot'}">${esc(코스지도모델.legTimeLabel(leg))}</b><small class="mode-alt">${esc(alt)}</small>`;
      const t=leg.transport||{};node.title=[t.노선,t.출처,t.기준요일,t.기준출발시각,t.확인일,t.비고].filter(Boolean).join(' · ');
    }
    for(const button of $('mapView').querySelectorAll('[data-play-segment]')){
      const leg=controller.routes?.find(leg=>leg.from===Number(button.dataset.playSegment));button.disabled=!leg;
      if(leg)button.textContent=leg.mode==='transit'?'이동 안내':'구간 재생';
    }
  }).catch(()=>{if(version===mapVersion)box.innerHTML='<p class="note">지도를 불러오지 못했습니다. 왼쪽 일정과 장소 설명은 계속 볼 수 있습니다.</p>';});
}

// ---------- 시작 ----------
$('newBtn').onclick=()=>{$('progress').hidden=!(last&&last.상태==='진행중');newForm();};
$('historyBtn').onclick=()=>{$('historyPanel').hidden?showHistory():hideHistory();};
$('historyClose').onclick=()=>{hideHistory();$('historyBtn').focus();};
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('historyPanel').hidden){hideHistory();$('historyBtn').focus();}});
(async()=>{
  showLanding();
  const items=await loadList();
  let p=null;try{p=(await get('/api/plan/latest')).기획;}catch{}
  if(p&&p.상태==='진행중'){showProgress(p);watch(p.기획id);$('main').innerHTML='';return;}  // 새로고침해도 진행 상황을 이어서 보여 줌
})();

}
