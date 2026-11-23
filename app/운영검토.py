"""담당자 운영·시간 확인 입력과 4단계 준비 검사. 외부 조회·AI 호출 없음."""
import copy
from datetime import date, timedelta, datetime
import re
from urllib.parse import urlsplit
from 시간표검사 import _분, 시간표_검사


def _key(r):
    if not isinstance(r,dict) or not isinstance(r.get('안','공통'),str) or not isinstance(r.get('칸ID'),str):raise ValueError('안·칸ID 형식을 확인하세요.')
    return r.get('안','공통'),r['칸ID']
def _text(v,limit=1000):
    if v is None:return ''
    if not isinstance(v,str) or len(v)>limit:raise ValueError('입력은 지정 길이 이내의 문자열이어야 합니다.')
    return v.strip()
def _day(v,maximum):
    if v in ['',None,'미정']:return '미정'
    if type(v) is not int or not 1<=v<=maximum:raise ValueError('일정의 일차를 확인하세요.')
    return v
def _time(v):
    v=_text(v,5)
    if v and _분(v) is None:raise ValueError('시각은 HH:MM 형식으로 입력하세요.')
    return v
def _date(v):
    v=_text(v,10)
    if v:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError()
            date.fromisoformat(v)
        except ValueError:raise ValueError('날짜는 실제 날짜의 YYYY-MM-DD 형식이어야 합니다.') from None
    return v
def _bool(v):
    if v is None:return False
    if type(v) is not bool:raise ValueError('확인 항목은 체크 여부로 입력하세요.')
    return v


요일='월화수목금토일'
재확인기간_일=90  # 제안서의 '3개월' 예시값. 팀이 숫자를 정하면 바꾼다.


def 휴무요일(text):
    """정기휴무 문구 → (매주 쉬는 요일 번호 집합 또는 None(미확인), 요일로 계산하지 않는 안내 문구 목록)."""
    text=(text or '').strip()
    if not text:return None,[]
    closed=set()
    for m in re.finditer(r'매주\s*([월화수목금토일])요일',text):closed.add(요일.index(m.group(1)))
    for m in re.finditer(r'([월화수목금토일])\s*[~\-–]\s*([월화수목금토일])(?:요일)?\s*(?:운영하지\s*않음|휴무|휴관|휴점)',text):
        a,b=요일.index(m.group(1)),요일.index(m.group(2))
        closed.update(range(a,b+1) if a<=b else [*range(a,7),*range(0,b+1)])
    notes=[]
    if re.search(r'번째|째\s*[월화수목금토일]|1월\s*1일|설|추석|명절|공휴일',text):notes.append(text)
    return closed,notes


def 출발가능요일(코스,검토,휴무조회=None):
    """상시 상품: 월~일 출발마다 각 일정의 방문 요일(1박2일이면 2일차=다음 요일)을 정기휴무와 대조."""
    if 휴무조회 is None:
        from 장소정보 import 장소찾기
        휴무조회=lambda name:(장소찾기(name) or {}).get('정기휴무','')
    excluded={(_key(r),r['대상명']) for r in 검토.get('운영확인',[]) if r.get('처리')=='제외'}
    slots={};unknown=[];notes=[]
    for t in 운영대상(코스):
        if (_key(t),t['대상명']) in excluded:continue
        closed,extra=휴무요일(휴무조회(t['대상명']))
        notes+=[f"{t['대상명']}: {x}" for x in extra]
        if closed is None or type(t['일차']) is not int:unknown.append(t['대상명']);continue
        slots.setdefault(_key(t),[]).append((t['일차'],closed))
    plans=sorted({k[0] for k in slots if k[0]!='공통'}) or ['공통']
    result={}
    for plan in plans:
        ok=[]
        for d in range(7):
            # 같은 칸에 자유식 후보가 여럿이면 하나라도 열려 있으면 된다.
            if all(any((d+day-1)%7 not in closed for day,closed in cands) for k,cands in slots.items() if k[0] in ['공통',plan]):ok.append(요일[d])
        result[plan]=ok
    return {'안별':result,'미확인':list(dict.fromkeys(unknown)),'안내':list(dict.fromkeys(notes))}


def 운영대상(코스):
    result=[]
    for row in 코스.get('칸목록',[]):
        if row.get('시간칸')=='숙박' or (row.get('시간칸')=='2일차오전' and 코스.get('2일차오전구성')=='자유시간'):
            continue
        meal=next((m for m in 코스.get('식사목록',[]) if _key(m)==_key(row)),{})
        candidates=meal.get('추천후보',[]) if meal.get('방식')=='자유식' else []
        names=candidates or [meal.get('식당') or row.get('장소명') or row['칸ID']]
        for name in names:
            result.append({'안':row.get('안','공통'),'칸ID':row['칸ID'],'일차':row.get('일차'),
                           '대상명':str(name),'후보제외가능':bool(candidates)})
    return result


def 화면정보(코스,입력):
    from 장소정보 import 운영정보_제안, 확인항목
    previous=코스.get('운영검토기록',{})
    rows=[]
    for r in 코스.get('칸목록',[]):
        start=r.get('시각',{}).get('값','');length=r.get('머무는시간');day=r.get('일차')
        endday='미정';end=''
        if type(day) is int and _분(start) is not None and type(length) in [int,float] and length>=0:
            endabs=(day-1)*1440+_분(start)+int(length);endday=endabs//1440+1;end=f'{endabs%1440//60:02d}:{endabs%60:02d}'
        old=next((x for x in previous.get('일정확인',[]) if _key(x)==_key(r)),{})
        rows.append({'안':r.get('안','공통'),'칸ID':r['칸ID'],'시간칸':r.get('시간칸',''),'장소명':r.get('장소명',''),
                     '시작일차':day,'시작시각':start,'종료일차':endday,'종료시각':end,
                     '장소권역':r.get('장소명',''),'이후연결':old.get('이후연결',''),
                     '연결확인':old.get('연결확인',False),'확인메모':old.get('확인메모','')})
    targets=운영대상(코스)
    for target in targets:
        suggestion=운영정보_제안(target['대상명'])
        target['보유자료']=suggestion.pop('보유자료')
        old=next((x for x in previous.get('운영확인',[]) if _key(x)==_key(target) and x['대상명']==target['대상명']),None)
        target['입력값']=copy.deepcopy(old if old is not None else suggestion)
        target['확인필요']=확인항목(target['입력값'],next(r for r in 코스['칸목록'] if _key(r)==_key(target)))
    return {'체류기간':입력['확정체류기간'],'일정목록':rows,'운영대상':targets,'저장값':previous}


def 검토입력_검사(값,코스,입력):
    if not isinstance(값,dict):raise ValueError('확인 입력 형식을 확인하세요.')
    maximum=2 if 입력.get('확정체류기간')=='1박2일' else 1
    mode=_text(값.get('운영기준')) or ('출발일시험' if 값.get('방문시작일') else '상시기획')
    if mode not in ['상시기획','출발일시험']:raise ValueError('운영 기준을 선택하세요.')
    result={'운영기준':mode,'운영조건':_text(값.get('운영조건')),
            '방문시작일':_date(값.get('방문시작일')) if mode=='출발일시험' else '', '일정확인':[],'운영확인':[],
            '겹침처리':_text(값.get('겹침처리'),30),'겹침메모':_text(값.get('겹침메모')),
            '담당자최종확인':_bool(값.get('담당자최종확인'))}
    if result['겹침처리'] not in ['', '미확인','노선겹침없음','피하기','연결하기','그대로두기']:raise ValueError('겹침 처리 선택지를 확인하세요.')
    allowed={_key(r) for r in 코스.get('칸목록',[])};seen=set()
    schedules=값.get('일정확인',[]);operations=값.get('운영확인',[])
    if not isinstance(schedules,list) or not isinstance(operations,list):raise ValueError('확인 내역은 목록이어야 합니다.')
    for r in schedules:
        if not isinstance(r,dict) or _key(r) not in allowed or _key(r) in seen:raise ValueError('없는 일정 또는 중복된 일정 확인입니다.')
        seen.add(_key(r));row={'안':_key(r)[0],'칸ID':_key(r)[1]}
        for prefix in ['시작','종료']:
            row[prefix+'일차']=_day(r.get(prefix+'일차'),maximum);row[prefix+'시각']=_time(r.get(prefix+'시각'))
        if all(type(row[p+'일차']) is int and row[p+'시각'] for p in ['시작','종료']):
            if (row['종료일차']-row['시작일차'])*1440+_분(row['종료시각'])-_분(row['시작시각'])<=0:
                raise ValueError(row['칸ID']+': 종료는 시작보다 늦어야 합니다.')
        for f in ['장소권역','이후연결','확인메모']:row[f]=_text(r.get(f))
        row['연결확인']=_bool(r.get('연결확인'));result['일정확인'].append(row)
    allowed_ops={(_key(r),r['대상명']) for r in 운영대상(코스)};seen=set()
    for r in operations:
        if not isinstance(r,dict) or not isinstance(r.get('대상명'),str):raise ValueError('운영 대상명 형식을 확인하세요.')
        k=(_key(r),r['대상명'])
        if k not in allowed_ops or k in seen:raise ValueError('없는 대상 또는 중복된 운영 확인입니다.')
        seen.add(k);row={'안':k[0][0],'칸ID':k[0][1],'대상명':k[1]}
        for f in ['처리','운영상태','출처명','출처URL','출처등급','메모']:row[f]=_text(r.get(f))
        row['처리']=row['처리'] or '유지';row['운영상태']=row['운영상태'] or '미확인'
        if row['처리'] not in ['유지','제외'] or row['운영상태'] not in ['운영','휴무','미확인']:raise ValueError('운영 상태·후보 처리 선택지를 확인하세요.')
        if row['처리']=='제외' and not next(x for x in 운영대상(코스) if (_key(x),x['대상명'])==k)['후보제외가능']:
            raise ValueError('자유식 추천 후보만 제외할 수 있습니다. 관광 일정은 기간을 수정하거나 별도로 재검토하세요.')
        if row['출처URL']:
            url=urlsplit(row['출처URL'])
            if url.scheme not in ['http','https'] or not url.netloc:raise ValueError('출처 URL은 http 또는 https 주소여야 합니다.')
        for f in ['영업시작','영업종료','마감시각']:row[f]=_time(r.get(f))
        row['마감구분']=_text(r.get('마감구분')) or ('확인' if row['마감시각'] else '미확인')
        if row['마감구분'] not in ['확인','해당없음','미확인']:raise ValueError('마감 정보 확인 상태를 선택하세요.')
        row['확인일']=_date(r.get('확인일'));row['익일종료']=_bool(r.get('익일종료'));row['방문일운영확인']=_bool(r.get('방문일운영확인'))
        if row['확인일'] and date.fromisoformat(row['확인일'])>datetime.now().astimezone().date():raise ValueError('확인일은 실제 확인한 날짜로 입력하세요. 미래 확인일은 사용할 수 없습니다.')
        period=next((x for x in result['일정확인'] if _key(x)==_key(row)),None)
        day=period['시작일차'] if period else next(x['일차'] for x in 코스['칸목록'] if _key(x)==_key(row))
        row['방문일자']=(date.fromisoformat(result['방문시작일'])+timedelta(days=day-1)).isoformat() if result['방문시작일'] and type(day) is int else ''
        result['운영확인'].append(row)
    return result


def 검토_반영(기존,검토):
    course=copy.deepcopy(기존)
    for confirm in 검토['일정확인']:
        row=next(r for r in course['칸목록'] if _key(r)==_key(confirm))
        day=confirm['시작일차'];start=confirm['시작시각'];endday=confirm['종료일차'];end=confirm['종료시각']
        if type(day) is int:row['일차']=day
        kind='확정' if confirm['연결확인'] else '가정'
        row['시각']={'값':start,'종류':kind if start else '미정'}
        row['종료일차']=endday;row['종료시각']={'값':end,'종류':kind if end else '미정'}
        row['머무는시간']=(endday-day)*1440+_분(end)-_분(start) if type(day) is int and type(endday) is int and start and end else '미확인'
        if confirm['장소권역'] and confirm['장소권역'] != row.get('장소명'):
            old_place=row.get('장소명','')
            row['장소명']=confirm['장소권역']
            if row.get('시간칸') not in ['점심','저녁','숙박','2일차오전']:
                row['근거ID']=[]
                row['운영주체후보']=[]
                warning={'경고ID':f"C-장소변경-{row['칸ID']}",'안':row.get('안','공통'),'칸ID':row['칸ID'],
                         '문구':f"수요 근거 없음: {old_place} → {row['장소명']} 수동 변경. 새 장소의 근거·운영정보 확인 필요",'적용근거ID':[]}
                course.setdefault('남은경고',[])[:]=[w for w in course.get('남은경고',[]) if w.get('경고ID')!=warning['경고ID']]
                course['남은경고'].append(warning)
                course.setdefault('미확인사항',[]).append({'종류':'장소변경','대상 칸ID':row['칸ID'],
                    '내용':f"{old_place} → {row['장소명']} 수동 변경. 이전 관광지의 근거·운영정보는 새 장소에 적용하지 않음."})
        for meal in course.get('식사목록',[]):
            if _key(meal)==_key(row):
                meal['시각']=copy.deepcopy(row['시각']);meal['이후연결']=confirm['이후연결']
                if confirm['장소권역']:meal['권역']=confirm['장소권역']
    for r in 검토['운영확인']:
        if r['처리']=='제외':
            meal=next((m for m in course.get('식사목록',[]) if _key(m)==_key(r)),None)
            if meal is not None:meal['추천후보']=[x for x in meal.get('추천후보',[]) if x!=r['대상명']]
    course['운영검토기록']=copy.deepcopy(검토)
    course['담당자최종확인기록']={'확인':검토['담당자최종확인'],'입력경로':'관리자 화면'}
    return course


def 준비_검사(코스,입력,검토,형식문제=None,휴무조회=None,오늘=None):
    missing=list(형식문제 or []);warnings=[];days=None
    오늘=오늘 or datetime.now().astimezone().date()
    조건=입력.get('코스작성조건',{});체류=입력.get('확정체류기간','당일')
    for p in ['시작','종료']:
        if type(조건.get(p+'일차')) is not int:missing.append(p+' 일차 확인 필요')
        if 조건.get(p+'지점') in [None,'','미확인','미정']:missing.append(p+' 장소 확인 필요')
        if _분(조건.get(p+'시각')) is None:missing.append(p+' 시각 확인 필요')
    if 체류=='1박2일' and 조건.get('2일차오전구성') not in ['후보일정추가','자유시간','종료장소로바로']:missing.append('2일차 오전 선택 필요')
    상시=not 검토.get('방문시작일')
    if 상시:
        days=출발가능요일(코스,검토,휴무조회)
        for name in days['미확인']:missing.append(name+': 정기휴무 미확인 (출발 가능 요일 계산 불가)')
        for plan,ok in days['안별'].items():
            label='' if plan=='공통' else f'({plan}) '
            if ok:warnings.append(f"출발 가능 요일 {label}: {' · '.join(ok)}")
            else:missing.append(f'E4 운영 충돌 {label}: 모든 요일에 휴무인 장소가 있어 출발 가능한 요일이 없음')
        for note in days['안내']:warnings.append('요일로 계산하지 않은 휴무 · '+note)
    times=시간표_검사(코스,조건,체류);missing+=times['충돌']+times['확인대기']
    for row in 코스.get('칸목록',[]):
        name=f"{row.get('안','공통')} · {row['칸ID']}"
        confirm=next((x for x in 검토['일정확인'] if _key(x)==_key(row)),None)
        if not confirm:missing.append(name+': 일정 시작·종료 확인 필요');continue
        if type(confirm['종료일차']) is not int or not confirm['종료시각']:missing.append(name+': 종료 일차·시각 필요')
        if not confirm['장소권역']:missing.append(name+': 장소·권역 확인 필요')
        if not confirm['연결확인'] or not confirm['이후연결'] or not confirm['확인메모']:missing.append(name+': 이동·이후 연결 확인과 메모 필요')
    targets=운영대상(코스)
    for target in targets:
        name=target['대상명'];row=next(r for r in 코스['칸목록'] if _key(r)==_key(target))
        op=next((r for r in 검토['운영확인'] if _key(r)==_key(target) and r['대상명']==name),None)
        if not op:missing.append(name+': 운영 확인 입력 필요');continue
        if op['운영상태']!='운영':missing.append(name+': 운영 여부 미확인 또는 휴무')
        if op.get('처리')=='제외':continue
        if not 상시 and not op['방문일운영확인']:missing.append(name+': 방문일 휴무·운영 확인 필요')
        if not op['출처명'] or not op['확인일'] or op['출처등급'] not in ['공식','운영주체']:missing.append(name+': 공식·운영주체 출처와 확인일 필요')
        elif (오늘-date.fromisoformat(op['확인일'])).days>재확인기간_일:missing.append(f"{name}: 확인일 {op['확인일']}이 {재확인기간_일}일을 넘어 다시 확인 필요")
        if op.get('마감구분') not in ['확인','해당없음'] or (op.get('마감구분')=='확인' and not op['마감시각']):missing.append(name+': 주문·입장 마감 확인 또는 해당없음 선택 필요')
        opening=_분(op['영업시작']);closing=_분(op['영업종료']);start=_분(row.get('시각',{}).get('값'));length=row.get('머무는시간')
        if opening is None or closing is None:missing.append(name+': 영업시간 입력 필요');continue
        if op['익일종료']:closing+=1440
        if closing<=opening:missing.append(name+': 영업 시작·종료 범위 확인 필요')
        if start is None or type(length) not in [int,float]:continue
        if op['익일종료'] and start<opening:start+=1440
        if start<opening or start+length>closing:missing.append(name+': 일정 체류시간이 영업시간 밖임')
        deadline=_분(op['마감시각'])
        if deadline is not None:
            if op['익일종료'] and deadline<opening:deadline+=1440
            if start>deadline:missing.append(name+': 주문·입장 마감 이후 도착')
    if any(m.get('방식')=='자유식' and not m.get('추천후보') for m in 코스.get('식사목록',[])):
        warnings.append('추천 후보가 없는 자유식은 확인한 권역 안내만 제공하며 특정 식당 이용을 보장하지 않습니다.')
    for row in 코스.get('칸목록',[]):
        if any(w.get('칸ID')==row.get('칸ID') and str(w.get('경고ID','')).startswith('C-장소변경-') for w in 코스.get('남은경고',[])):
            warnings.append(f"{row.get('장소명','')}: 장소 변경 후 수요 근거·운영정보 재확인 필요")
    if 검토.get('겹침처리') not in ['노선겹침없음','피하기','연결하기','그대로두기'] or not 검토.get('겹침메모'):missing.append('E7 겹침 처리 선택과 확인 메모 필요')
    if not 검토.get('담당자최종확인'):missing.append('담당자 최종 검토 확인 필요')
    missing=list(dict.fromkeys(missing))
    return {'진행가능':not missing,'상태':'준비 완료' if not missing else '확인 필요','확인필요':missing,'유지경고':warnings,
            '출발가능요일':days['안별'] if days else None,
            '검사범위':'입력한 운영·시간·담당자 확인의 일관성 검사. 실제 출처 진위·현장 운영을 자동 검증하지 않음. 4단계 AI 미실행.'}
