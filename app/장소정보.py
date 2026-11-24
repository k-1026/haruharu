"""저장소의 장소·이동 자료 읽기 전용 조회. 웹 조회 및 AI 호출 없음."""
import csv
import re
import json
import math
from 설정 import 설정_읽기, 자료_파일

장소_기본파일='장소운영정보_중구동구_데모코스_2026.csv'
이동_기본파일='이동시간_중구동구_데모코스_2026.csv'


def _이름(name):
    name=re.sub(r'^자유식\s*·\s*', '', name)
    name=re.sub(r'\s*\([^)]*\)', '', name)
    name=re.sub(r'^대구광역시\s*', '', name)
    name=re.sub(r'^(중구|동구)\s+', '', name)
    return re.sub(r'\s*(권역|일대)$', '', name).strip()


def 장소목록():
    config=설정_읽기()
    placefile=자료_파일(config,'HARUHARU_PLACES_FILE',장소_기본파일)
    travelfile=자료_파일(config,'HARUHARU_TRAVEL_FILE',이동_기본파일)
    with placefile.open(encoding='utf-8-sig',newline='') as f:
        rows=[dict(r,자료파일=placefile.name) for r in csv.DictReader(f)]
    names={_이름(r['장소명']) for r in rows}
    with travelfile.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            for key in ['출발장소','도착장소']:
                name=r[key]
                if _이름(name) not in names:
                    rows.append({'장소명':name,'장소유형':'이동 기준점','운영시간':'','상태':'운영정보 없음',
                                 '자료파일':travelfile.name})
                    names.add(_이름(name))
    return rows


def 장소찾기(name):
    matches=[r for r in 장소목록() if _이름(r['장소명'])==_이름(name)]
    return matches[0] if len(matches)==1 else None


def 진입안내(name):
    """선택한 시연 진입 방향만 안내한다. 미확인 입구 좌표를 만들지 않는다."""
    path=자료_파일(설정_읽기(),'HARUHARU_PLACES_FILE',장소_기본파일).with_name('시연_진입기준.json')
    try:rows=json.loads(path.read_text(encoding='utf-8')).get('장소',{})
    except (OSError,ValueError):return ''
    return rows.get(_이름(name),'')


def 권역위치(name):
    path=자료_파일(설정_읽기(),'HARUHARU_PLACES_FILE',장소_기본파일).with_name('식사권역_표시.json')
    try:return json.loads(path.read_text(encoding='utf-8')).get(_이름(name))
    except (OSError,ValueError):return None


def 대표위치(name, 시간칸=''):
    """입구와 별도로 자료 대조한 지도 대표점. 등록 별칭·명시 권역만 허용한다."""
    path=자료_파일(설정_읽기(),'HARUHARU_PLACES_FILE',장소_기본파일).with_name('지도_대표위치.json')
    try:rows=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return None
    raw=str(name or '')
    clean=re.sub(r'^식사 방식 미선택\s*·\s*권역 후보:\s*','',raw)
    clean=re.split(r'\s+[—–]\s+',clean,maxsplit=1)[0]
    key=re.sub(r'\s+','',_이름(clean))
    matches=[r for r in rows.values() if key in [re.sub(r'\s+','',_이름(a)) for a in r.get('별칭',[])]]
    if not matches and _숙박권역_명시(시간칸,raw):
        matches=[rows['동성로']] if '동성로' in rows else []
    if len(matches)!=1:return None
    row=matches[0];p=row.get('중심')
    if not (isinstance(p,list) and len(p)==2 and all(isinstance(n,(int,float)) and math.isfinite(n) for n in p)
            and abs(p[0])<=90 and abs(p[1])<=180):return None
    if row.get('검토상태') not in ['자료대조완료','사람확인완료']:return None
    if not all(row.get(k) for k in ['근거','근거URL','검토자','확인일','설명']):return None
    return dict(row)


def _숙박권역_명시(시간칸,이름):
    return 시간칸 in ['숙박','2일차오전'] and bool(re.search(r'동성로\s*(?:일대|권역|거리)',이름)) and not re.search(r'또는|혹은|중\s*미선택',이름)


def 장소안내(name,시간칸=''):
    path=자료_파일(설정_읽기(),'HARUHARU_PLACES_FILE',장소_기본파일).with_name('지도_장소소개.json')
    try:items=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):items={}
    basic=장소찾기(name) or {}
    representative=대표위치(name,시간칸=시간칸) or {}
    key=basic.get('장소명') or representative.get('이름','').split(' · ')[0]
    intro=items.get(key,{})
    return {'소개':intro.get('소개',''),'출처URL':intro.get('출처URL') or basic.get('출처URL',''),
            '주소':basic.get('주소') or representative.get('주소',''),
            '이용시간':basic.get('운영시간',''),'휴무':basic.get('정기휴무',''),'확인일':basic.get('확인일','')}


def 좌표(name):
    """장소 CSV의 위도·경도. 빈칸·숫자 아님·없는 장소는 None(추정하지 않음)."""
    matches=[r for r in 장소목록() if _이름(r['장소명'])==_이름(name)]
    if len(matches)!=1:return None
    row=matches[0]
    if '좌표검토상태' in row:
        # 검토 정보가 있는 자료에서는 미검토·입구 대기 좌표를 노출하지 않는다.
        if row.get('좌표검토상태') not in ['자료대조완료','사람확인완료']:return None
        if any(not row.get(x) for x in ['좌표검토자','좌표근거URL','좌표확인일','좌표검토근거','좌표위치기준']):return None
    try:return float(matches[0].get('위도','')),float(matches[0].get('경도',''))
    except (TypeError,ValueError):return None


def 등급(text):
    """CSV 출처등급 → 화면 선택지. 공식·운영주체는 정확히 그 값일 때만, 개인이 섞이면 개인(시험 인정), 나머지는 기타."""
    text=(text or '').strip()
    if text in ['공식','운영주체']:return text
    return '개인' if '개인' in text else '기타' if text else ''


def 상시개방(data):
    """운영시간이 '상시 개방'이고 출처ID가 있을 때만 참. 출처 없는 상시는 미확인으로 둔다."""
    return str(data.get('운영시간','')).replace(' ','').startswith('상시개방') and bool(str(data.get('출처ID','')).strip())


def 운영정보_제안(name):
    data=장소찾기(name) or {}
    hours=data.get('운영시간','')
    # 계절별/요일별 복수 시간은 임의로 하나를 선택하지 않는다.
    spans=re.findall(r'(\d{2}:\d{2})\s*[-~–]\s*(\d{2}:\d{2})',hours)
    opening,closing=spans[0] if len(spans)==1 else ('','')
    last=data.get('마지막입장','')
    deadline=re.fullmatch(r'\d{2}:\d{2}',last)
    lo=re.search(r'라스트오더\s*(\d{2}:\d{2})',hours)
    limit=last if deadline else lo.group(1) if lo else ''
    always=상시개방(data)
    if always:
        # data_spec 11-1 규칙: 출처가 있는 '상시 개방'만 하루 전체(00:00~다음 날 00:00)로 보고 마감은 해당 없음.
        opening,closing,limit='00:00','00:00',''
    return {'영업시작':opening,'영업종료':closing,'마감시각':limit,
            '마감구분':'해당없음' if always or last.replace(' ','')=='해당없음' else '확인' if limit else '미확인',
            '출처명':data.get('출처ID',''),'출처URL':data.get('출처URL','') if data.get('출처URL','').startswith(('http://','https://')) else '',
            '출처등급':등급(data.get('출처등급','')),
            '확인일':data.get('확인일',''),'운영상태':'미확인','처리':'유지','익일종료':always,
            '방문일운영확인':False,'메모':' / '.join(data.get(k,'') for k in ['정기휴무','비고'] if data.get(k)),
            '보유자료':data}


def 확인항목(op, row):
    result=[]
    if not op.get('영업시작') or not op.get('영업종료'):result.append('영업시간 누락 또는 계절·요일별 선택 필요')
    if not op.get('출처명') or not op.get('확인일') or op.get('출처등급') not in ['공식','운영주체','개인']:result.append('출처·확인일 보완 필요')
    elif op.get('출처등급')=='개인':result.append('개인 출처: 시험에서만 인정, 판매 확정 전 공식 확인 필요')
    if op.get('마감구분','미확인')=='미확인':result.append('주문·입장 마감 정보 미확인')
    if not op.get('방문일운영확인'):result.append('운영 요일·휴무·계절 예외 확인 필요')
    if op.get('운영상태')=='휴무':result.append('휴무로 입력됨')
    from 시간표검사 import _분
    start=_분(row.get('시각',{}).get('값'));length=row.get('머무는시간')
    opening=_분(op.get('영업시작'));closing=_분(op.get('영업종료'));deadline=_분(op.get('마감시각'))
    if start is not None and opening is not None and closing is not None:
        if op.get('익일종료'):
            closing+=1440
            if start<opening:start+=1440
            if deadline is not None and deadline<opening:deadline+=1440
        if type(length) in [int,float] and (start<opening or start+length>closing):result.append('일정 체류시간과 영업시간 충돌')
        if deadline is not None and start>deadline:result.append('주문·입장 마감 이후 도착')
    return result
