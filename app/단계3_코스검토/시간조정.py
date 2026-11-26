"""기존 시작일의 가정 시각을 새 시작 시각에 맞춰 이동한다. AI·운영정보 추정 없음."""
from copy import deepcopy
from app.단계3_코스검토.시간표검사 import _분


def 시간표_조정(결과, 조건, 체류):
    시작분=_분(조건.get('시작시각'))
    보고={'이동분':0,'안별이동분':{},'변경목록':[],'확인사항':[]}
    if 시작분 is None:
        보고['확인사항'].append('시작 시각 미정: 시간표 자동 조정 대기')
        return 보고
    최대=2 if 체류=='1박2일' else 1
    칸들=결과.get('칸목록',[])
    안들=list(dict.fromkeys(r.get('안','공통') for r in 칸들))
    변경=[]
    for 안 in 안들:
        rows=[r for r in 칸들 if r.get('안','공통')==안 and type(r.get('일차')) is int
              and isinstance(r.get('시각'),dict) and _분(r['시각'].get('값')) is not None]
        if not rows:
            보고['확인사항'].append(f'{안}: 기존 시작 시각이 없어 자동 조정 대기');continue
        첫=min(rows,key=lambda r:(r['일차'],_분(r['시각']['값'])))
        원일차=첫['일차'];목표일차=조건.get('시작일차')
        if type(목표일차) is not int:
            목표일차=원일차
            보고['확인사항'].append('시작 일차 미정: 기존 일정의 일차를 유지하고 시각만 조정했습니다. 일차 선택은 별도로 필요합니다.')
        차이=(목표일차-원일차)*1440+시작분-_분(첫['시각']['값'])
        보고['안별이동분'][안]=차이
        for r in rows:
            # 다음 날 일정은 그대로 둔다. 시작일을 바꿔 전체 일차가 바뀌는 경우에만 일차를 함께 이동한다.
            if r['일차']!=원일차:continue
            if r['시각'].get('종류')!='가정':
                if 차이:보고['확인사항'].append(f"{안} {r.get('칸ID')}: 확정 시각은 자동 이동하지 않았습니다. 새 시작 조건과의 충돌을 확인하세요.")
                continue
            absolute=(r['일차']-1)*1440+_분(r['시각']['값'])+차이
            day,minute=divmod(absolute,1440);day+=1
            if not 1<=day<=최대:
                raise ValueError('시작 시각에 맞춰 이동하면 일정이 체류 기간 밖으로 나갑니다. 시작 조건이나 일정 길이를 조정하세요.')
            if 차이:
                변경.append((r,day,f'{minute//60:02d}:{minute%60:02d}'))
    # 전체 조정안이 유효한지 확인한 뒤에만 변경한다.
    바뀐={}
    for r,day,time in 변경:
        보고['변경목록'].append(f"{r.get('안','공통')} · {r.get('칸ID')}: {r['일차']}일차 {r['시각']['값']} → {day}일차 {time} (가정)")
        r['일차']=day;r['시각']={'값':time,'종류':'가정'}
        바뀐[(r.get('안','공통'),r.get('칸ID'))]=r
    for meal in 결과.get('식사목록',[]):
        key=(meal.get('안','공통'),meal.get('칸ID'))
        if key not in 바뀐:continue
        if meal.get('시각',{}).get('종류')=='확정':
            보고['확인사항'].append(f'{key}: 확정 식사 시각은 유지했습니다. 일정표와 식사 시각을 재확인하세요.')
        else:
            meal['시각']=deepcopy(바뀐[key]['시각'])
            meal['이후연결']='시간표 조정 후 다음 일정 연결을 다시 확인하세요. 이전 생성 문구는 수정 전 기록입니다.'
    values=list(보고['안별이동분'].values())
    보고['이동분']=values[0] if values and len(set(values))==1 else 0
    if 변경:
        보고['확인사항'].append('시작일의 가정 시각을 이동했습니다. 머무는 시간과 일정 간 간격은 유지했으며 다음 날의 기존 시각은 유지했습니다.')
        보고['확인사항'].append('식사 시간대·식당/야시장 영업시간·교통편·시작 장소에서 첫 일정까지 이동을 재확인하세요. 이 조정은 운영 가능성을 검증하지 않습니다.')
    return 보고
