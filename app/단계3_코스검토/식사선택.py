"""식사 후보 비교와 한 칸 반영. 장소별 임시 코드·AI 재작성·조회 시 저장 없음."""
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
import json
import math
import re

from app.단계3_코스검토.장소정보 import 장소목록, 장소찾기, 좌표, 대표위치, 이동안내, _이름
from app.단계3_코스검토.도로경로 import 키, 거리
from app.단계3_코스검토.운영검토 import 휴무요일

경로파일=Path(__file__).resolve().parents[1]/'담당자화면/road-routes.json'
추가경로={}


@lru_cache(maxsize=2)
def _캐시(path,mtime):
    return json.loads(Path(path).read_text(encoding='utf-8')).get('routes',{})


def 위치(name):
    return 좌표(name) or (대표위치(name) or {}).get('중심')


def 구간(a,b):
    pa,pb=위치(a),위치(b)
    if not pa or not pb:return None
    if _이름(a)==_이름(b):
        return {'출발':a,'도착':b,'분':0,'경로':[list(pa),list(pb)],'출처':'같은 장소','확인일':''}
    try:route=추가경로.get(키(pa,pb)) or _캐시(str(경로파일),경로파일.stat().st_mtime_ns).get(키(pa,pb),{})
    except (OSError,ValueError):route={}
    table=이동안내(a,b) or {}
    seconds=route.get('durationSeconds')
    minutes=table.get('도보분')
    if not isinstance(minutes,(int,float)) or minutes<=0:
        minutes=math.ceil(seconds/60) if isinstance(seconds,(int,float)) and math.isfinite(seconds) and seconds>0 else None
    if minutes is None:return None
    return {'출발':a,'도착':b,'분':minutes,'경로':route.get('points'),
            '출처':table.get('출처') or route.get('source',''),'확인일':table.get('확인일') or route.get('fetchedAt',''),
            '시간근거':'보유 이동표·도보' if table.get('도보분') else 'OSRM 도보 예상',
            '주의':'대표 위치 기준 예상 이동시간 · 실제 방문일 재확인'}


def 경로보완(course,id,name,conditions):
    """명시적인 후보 비교 요청 때만 부족한 방향의 도보 경로를 조회한다. 원본 코스·자료 파일에 쓰지 않는다."""
    from app.단계3_코스검토.도로경로 import 경로수집
    report=비교(course,id,name,conditions)
    for leg in report['후보이동']:
        if leg.get('분') is not None and leg.get('경로'):continue
        a,b=위치(leg['출발']),위치(leg['도착'])
        if not a or not b:continue
        result=경로수집([{'일차':1,'좌표':list(a)},{'일차':1,'좌표':list(b)}],{'routes':추가경로},쉬기=0,시간보완=True)
        if len(추가경로)>1000:추가경로.clear()
        추가경로.update(result['routes'])


def _분(value):
    if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):return None
    h,m=map(int,value.split(':'));return h*60+m


def _시각(row,key):
    value=row.get(key) or {}
    return _분(value.get('값')) if isinstance(value,dict) else None


def _행(course,id):
    rows=course.get('칸목록',[])
    matches=[(i,r) for i,r in enumerate(rows) if r.get('칸ID')==id]
    if len(matches)!=1 or matches[0][1].get('시간칸') not in ['점심','저녁']:raise ValueError('식사 일정을 다시 선택하세요.')
    i,row=matches[0]
    meal=next((m for m in course.get('식사목록',[]) if (m.get('안','공통'),m.get('칸ID'))==(row.get('안','공통'),id)),{})
    prev=rows[i-1] if i>0 and rows[i-1].get('일차')==row.get('일차') else None
    nxt=rows[i+1] if i+1<len(rows) and rows[i+1].get('일차')==row.get('일차') else None
    return row,meal,prev,nxt


def _등록후보(course,row,conditions):
    _,meal,_,_=_행(course,row['칸ID'])
    anchor=meal.get('식사기준장소') or row.get('장소명','')
    gu=(장소찾기(anchor) or {}).get('구')
    regions=conditions.get('지역') or ([gu] if gu else [])
    excluded={_이름(x.get('대상명','')) for x in (course.get('운영검토기록') or {}).get('운영확인',[])
              if x.get('칸ID')==row['칸ID'] and x.get('처리')=='제외'}
    return [p for p in 장소목록() if p.get('장소유형') in ['식당','식당가','시장']
            and _이름(p.get('장소명','')) not in excluded
            and row['시간칸'] in p.get('코스칸','') and (not regions or p.get('구') in regions)
            and (not gu or p.get('구')==gu)
            and (row['시간칸']=='저녁' or '(치킨 옵션)' not in p.get('장소명',''))]


def 비교(course,id,name,conditions):
    row,meal,prev,nxt=_행(course,id)
    candidate=next((p for p in _등록후보(course,row,conditions) if p.get('장소명')==name),None)
    if candidate is None:raise ValueError('선택한 지역·식사 시간대의 등록 후보를 고르세요.')
    errors=[];warnings=[]
    start,end=_시각(row,'시각'),_시각(row,'종료시각')
    anchor=meal.get('식사기준장소') or row.get('장소명','')
    ap,cp=위치(anchor),위치(name)
    if not cp:errors.append('후보 위치 확인 필요: 지도 경로를 비교할 수 없습니다.')
    radius=meal.get('권역반경m',1500)
    if not isinstance(radius,(int,float)) or isinstance(radius,bool) or not 100<=radius<=5000:radius=1500
    meters=round(거리(ap,cp)) if ap and cp else None
    if not ap:errors.append('식사 권역 기준 위치 확인 필요')
    if meters is not None and meters>radius:errors.append(f'기존 식사 권역 밖: 기준점에서 {meters}m (반경 {radius}m)')
    hours=candidate.get('운영시간','')
    spans=re.findall(r'(\d\d:\d\d)\s*[-~–]\s*(\d\d:\d\d)',hours)
    if start is None or end is None:warnings.append('식사 시각 미정: 방문일·시각 확정 후 영업과 이동 재확인')
    if len(spans)==1 and start is not None and end is not None:
        opening,closing=map(_분,spans[0]);s,e=start,end
        if opening is not None and closing is not None:
            if closing<=opening:
                closing+=1440
                if s<opening:s+=1440
            if e<s:e+=1440
            if s<opening or e>closing:errors.append('식사 시간과 영업시간 충돌')
    elif len(spans)!=1 and '상시' not in hours:warnings.append('영업시간 상세 확인 필요')
    deadline=_분(candidate.get('마지막입장',''))
    if deadline is not None and start is not None and start>deadline:errors.append('주문 마감 이후 도착')
    if not candidate.get('마지막입장'):warnings.append('주문 마감 확인 필요')
    closed,extra=휴무요일(candidate.get('정기휴무',''))
    if closed is None:warnings.append('정기휴무 상세 확인 필요')
    visit=conditions.get('방문시작일') or (course.get('운영검토기록') or {}).get('방문시작일')
    if visit:
        try:
            day=date.fromisoformat(visit)+timedelta(days=int(row['일차'])-1)
            if closed is not None and day.weekday() in closed:errors.append('방문일 정기휴무')
        except (ValueError,TypeError):warnings.append('방문일 확인 필요')
    else:warnings.append('방문일 미정: 정기휴무 '+(candidate.get('정기휴무') or '확인 필요'))
    warnings.extend(extra)
    if not str(candidate.get('출처URL','')).startswith(('https://','http://')):warnings.append('운영정보 원문 링크 보완 필요')
    basis={'시각':row.get('시각'),'종료시각':row.get('종료시각'),'일차':row.get('일차'),'방문시작일':visit,
           '영업시간':hours,'휴무':candidate.get('정기휴무'),'후보좌표':list(cp) if cp else None,'권역반경m':radius,
           '인접일정':[{k:r.get(k) for k in ['장소명','시각','종료시각']} if r else None for r in [prev,nxt]]}
    savedreports=(meal.get('후보묶음') or {}).get('검토',[])+[meal.get('선택검토') or {}]
    stored=next((r for r in savedreports if r.get('장소명')==name and r.get('비교기준')==basis),{})
    def savedleg(a,b):
        for l in stored.get('후보이동',[]):
            if l.get('출발')!=a or l.get('도착')!=b:continue
            minutes=l.get('분');points=l.get('경로')
            if isinstance(minutes,(int,float)) and not isinstance(minutes,bool) and math.isfinite(minutes) and minutes>=0 and isinstance(points,list) and len(points)>=2:
                return deepcopy(l)
    before=[];after=[]
    for neighbor,incoming in [(prev,True),(nxt,False)]:
        if neighbor is None:continue
        if neighbor.get('시간칸') in ['숙박','2일차오전'] and not 위치(neighbor.get('장소명','')):
            warnings.append('인접 숙소·자유시간 위치 미정: 해당 이동은 위치 지정 후 재확인');continue
        a,b=(neighbor.get('장소명',''),name) if incoming else (name,neighbor.get('장소명',''))
        leg=구간(a,b);archived=savedleg(a,b)
        if archived:
            if leg is None:leg=archived
            elif not leg.get('경로'):leg={**archived,**leg,'경로':archived['경로']}
        old=구간(neighbor.get('장소명',''),row.get('장소명','')) if incoming else 구간(row.get('장소명',''),neighbor.get('장소명',''))
        before.append(old or {'출발':neighbor.get('장소명','') if incoming else row.get('장소명',''),'도착':row.get('장소명','') if incoming else neighbor.get('장소명',''),'분':None})
        after.append(leg or {'출발':a,'도착':b,'분':None})
        if leg is None:errors.append('앞뒤 이동시간 자료 필요: '+a+' → '+b);continue
        if not leg.get('경로'):warnings.append('도로 경로 미확인: '+a+' → '+b)
        t=_시각(neighbor,'종료시각' if incoming else '시각')
        if t is None:warnings.append(('이전' if incoming else '다음')+' 일정 시각 미정: 이동 여유 재확인')
        if incoming and t is not None and start is not None and t+leg['분']>start:errors.append('이전 일정 종료 후 식사 시작까지 이동시간 부족')
        if not incoming and t is not None and end is not None and end+leg['분']>t:errors.append('다음 일정 시작까지 이동시간 부족')
    selected=meal.get('경로선택후보')==name and (meal.get('선택검토') or {}).get('비교기준')==basis
    return {'장소명':name,'이름':_이름(name),'치킨':'(치킨 옵션)' in name,'좌표':list(cp) if cp else None,
            '칸ID':id,'시간칸':row['시간칸'],'반영가능':not errors,'오류':errors,'확인필요':list(dict.fromkeys(warnings)),
            '기존이동':before,'후보이동':after,'권역거리m':meters,'권역반경m':radius,
            '권역':meal.get('권역') or anchor,'운영시간':hours,'휴무':candidate.get('정기휴무',''),
            '운영출처':candidate.get('출처URL',''),'자료확인일':candidate.get('확인일',''),
            '경로선택됨':selected,'비교기준':basis,
            '상태':('비교 시 이동 조회' if all('앞뒤 이동시간 자료' in e for e in errors) else '선택 불가') if errors else '확인 후 선택' if warnings else '선택 가능'}


def 후보목록(course,row,conditions):
    rows=[비교(course,row['칸ID'],p['장소명'],conditions) for p in _등록후보(course,row,conditions)]
    return sorted(rows,key=lambda x:(not x['반영가능'],not x['경로선택됨'],x['치킨'],x['권역거리m'] if x['권역거리m'] is not None else float('inf')))


def 반영(course,id,name,conditions,미확인동의=False):
    if _행(course,id)[0]['시간칸']=='점심':
        raise ValueError('점심은 식당 하나를 지정하지 않고 후보 묶음을 저장하세요. 관광객이 자기 지도에서 선택합니다.')
    report=비교(course,id,name,conditions)
    if report['오류']:raise ValueError(' / '.join(report['오류']))
    if report['확인필요'] and 미확인동의 is not True:raise ValueError('남은 확인 사항을 읽고 초안 반영에 동의해 주세요.')
    row,meal,_,_=_행(course,id)
    if report['경로선택됨']:raise ValueError('이미 같은 조건에서 경로 기준으로 선택한 후보입니다.')
    result=deepcopy(course)
    newrow,newmeal,_,_=_행(result,id)
    if not newmeal:
        newmeal={'칸ID':id,'안':row.get('안','공통'),'권역':row.get('장소명',''),'식비포함':'불포함'}
        result.setdefault('식사목록',[]).append(newmeal)
    newmeal.update({'방식':'자유식','식당':'','식사기준장소':meal.get('식사기준장소') or row['장소명'],
                    '경로선택후보':name,'선택검토':deepcopy(report),
                    '추천후보':[x['장소명'] for x in 후보목록(course,row,conditions)]})
    newrow['장소명']=name
    outgoing=next((leg for leg in report['후보이동'] if leg['출발']==name),None)
    newmeal['이동시간']={'분':outgoing['분'] if outgoing else None,'적용조건':'후보 이후 도보 예상시간 · 미정 인접 장소는 위치 지정 후 재확인'}
    if outgoing:newmeal['이후연결']=outgoing['도착']
    for evidence in result.get('장소별근거',[]):
        if evidence.get('칸ID')==id:
            previous=deepcopy(evidence)
            evidence.update({'장소':name,'넣은이유':'담당자가 식사 후보와 앞뒤 이동을 비교해 경로 기준으로 선택',
                             '근거수치':'없음','운영정보':'후보 비교 자료 기준 · 방문일 재확인','이전식사근거':previous})
    for key in ['장소스토리']:
        if isinstance(result.get(key),list):result[key]=[x for x in result[key] if x.get('칸ID')!=id]
    review=result.get('운영검토기록') or {}
    if isinstance(review.get('운영확인'),list):
        review['운영확인']=[x for x in review['운영확인'] if x.get('칸ID')!=id]
    result['식사선택기록']={**report,'이전장소':row['장소명'],'미확인동의':미확인동의,
                          '안내':'식사 한 곳의 경로 기준 후보만 변경. 기존 시간·권역·다른 일정은 보존. 식당 예약·지정식 확정 아님.'}
    return result


def 묶음반영(course,id,names,conditions,미확인동의=False):
    """직원은 후보만 구성한다. 공통 방문 행·시각·기준점은 변경하지 않는다."""
    row,meal,_,_=_행(course,id)
    if row['시간칸']!='점심':raise ValueError('점심 일정을 선택하세요.')
    if not isinstance(names,list) or not 2<=len(names)<=12 or any(not isinstance(n,str) for n in names):
        raise ValueError('점심 후보를 2개 이상 12개 이하로 선택하세요.')
    if len(set(names))!=len(names):raise ValueError('같은 후보를 중복 선택할 수 없습니다.')
    reports=[비교(course,id,n,conditions) for n in names]
    errors=[e for r in reports for e in r['오류']]
    if errors:raise ValueError(' / '.join(dict.fromkeys(errors)))
    if any(r['확인필요'] for r in reports) and 미확인동의 is not True:
        raise ValueError('자료 보완이 남은 초안 후보 묶음임을 확인하세요. 관광객 공개 준비 완료가 아닙니다.')
    if (meal.get('후보묶음') or {}).get('후보')==names:raise ValueError('이미 같은 후보 묶음입니다.')
    result=deepcopy(course)
    _,newmeal,_,_=_행(result,id)
    if not newmeal:
        newmeal={'칸ID':id,'안':row.get('안','공통'),'권역':row['장소명'],'식비포함':'불포함'}
        result.setdefault('식사목록',[]).append(newmeal)
    newmeal.update({'방식':'자유식','식당':'','식사기준장소':meal.get('식사기준장소') or row['장소명'],
                    '추천후보':names[:],'후보묶음':{'선택주체':'관광객','후보':names[:],'검토':reports}})
    for key in ['경로선택후보','선택검토']:newmeal.pop(key,None)
    result['식사후보묶음기록']={'칸ID':id,'후보':names[:],'선택주체':'관광객',
        '안내':'직원이 점심 후보 묶음을 저장했습니다. 공통 일정은 유지하며 관광객이 개인 지도에서 선택합니다.'}
    return result


def 관광객묶음(course,conditions):
    """저장 후보만 최신 운영·경로와 대조한다. GET 조회에서 경로 수집·파일 쓰기 없음."""
    result=[]
    for meal in course.get('식사목록',[]):
        pack=meal.get('후보묶음')
        if not isinstance(pack,dict):continue
        candidates=[]
        for name in pack.get('후보',[]):
            try:report=비교(course,meal['칸ID'],name,conditions)
            except ValueError:
                report={'장소명':name,'이름':_이름(name),'반영가능':False,'오류':['등록·권역 조건이 달라져 직원 재검토 필요'],
                        '확인필요':[],'좌표':None,'후보이동':[]}
            ready=report['반영가능'] and not report['확인필요'] and all(l.get('경로') for l in report['후보이동'])
            candidates.append({**report,'선택가능':bool(ready)})
        result.append({'칸ID':meal['칸ID'],'선택주체':'관광객','후보':candidates,
                       '공개준비':len(candidates)>=2 and all(c['선택가능'] for c in candidates)})
    return result


def 잠근선택_보존(course,old,locked):
    """일반 코스 수정에서도 원래 식사 권역·후보 선택을 보존한다. 이웃 변경 시 이전 비교 결과만 무효화한다."""
    previous={m['칸ID']:m for m in old.get('식사목록',[]) if m.get('칸ID') in locked}
    def neighbors(c,id):
        try:_,_,before,after=_행(c,id)
        except ValueError:return None
        return [{k:r.get(k) for k in ['칸ID','일차','장소명','시각','종료시각']} if r else None for r in [before,after]]
    for meal in course.get('식사목록',[]):
        original=previous.get(meal['칸ID'],{})
        for key in ['식사기준장소','권역반경m','경로선택후보','선택검토','후보묶음']:
            if key in original:meal[key]=deepcopy(original[key])
        if meal.get('선택검토') and neighbors(course,meal['칸ID'])!=neighbors(old,meal['칸ID']):
            meal['선택검토']={}
            course.setdefault('미확인사항',[]).append({'종류':'식사 이동 재확인','대상칸ID':meal['칸ID'],
                '내용':'인접 일정이 바뀌어 이전 식당 후보 비교를 다시 확인해야 합니다. 식사 권역·선택은 보존했습니다.'})
