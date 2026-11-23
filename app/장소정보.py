"""저장소의 장소·이동 자료 읽기 전용 조회. 웹 조회 및 AI 호출 없음."""
import csv
import re
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
    return {'영업시작':opening,'영업종료':closing,'마감시각':limit,
            '마감구분':'확인' if limit else '해당없음' if last=='해당없음' else '미확인',
            '출처명':data.get('출처ID',''),'출처URL':data.get('출처URL','') if data.get('출처URL','').startswith(('http://','https://')) else '',
            '출처등급':data.get('출처등급','') if data.get('출처등급') in ['공식','운영주체'] else '기타' if data.get('출처등급') else '',
            '확인일':data.get('확인일',''),'운영상태':'미확인','처리':'유지','익일종료':False,
            '방문일운영확인':False,'메모':' / '.join(data.get(k,'') for k in ['정기휴무','비고'] if data.get(k)),
            '보유자료':data}


def 확인항목(op, row):
    result=[]
    if not op.get('영업시작') or not op.get('영업종료'):result.append('영업시간 누락 또는 계절·요일별 선택 필요')
    if not op.get('출처명') or not op.get('확인일') or op.get('출처등급') not in ['공식','운영주체']:result.append('공식·운영주체 출처 보완 필요')
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
