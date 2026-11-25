"""일차와 시각·명시된 머무는 시간만 대조. AI·이동시간 추정·시간표 재배치 없음."""
import re


def _분(value):
    if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):
        return None
    h,m=map(int,value.split(':'))
    return h*60+m


def 시간표_검사(결과, 조건, 체류):
    충돌,대기,참고=[],[],[]
    최대=2 if 체류=='1박2일' else 1
    경계={}
    for label in ['시작','종료']:
        day=조건.get(label+'일차')
        day=day if type(day) is int and 1<=day<=최대 else None
        minute=_분(조건.get(label+'시각'))
        if day is None:대기.append(label+' 일차 선택 대기 (이전 기록의 일차를 자동 지정하지 않음)')
        if minute is None:대기.append(label+' 시각 입력 대기')
        경계[label]=(day,minute,((day-1)*1440+minute) if day is not None and minute is not None else None)
    start,end=경계['시작'][2],경계['종료'][2]
    if start is not None and end is not None and start>end:
        충돌.append('종료 일차·시각이 시작보다 빠릅니다.')
    일정=[]
    for r in 결과.get('칸목록',[]):
        day=r.get('일차');t=r.get('시각',{})
        minute=_분(t.get('값')) if isinstance(t,dict) else None
        name=f"[{r.get('안','공통')}] {day}일차 {r.get('장소명') or r.get('칸ID','일정')}"
        if type(day) is not int or not 1<=day<=최대:
            충돌.append(name+': 지원하지 않는 일차');continue
        if minute is None:
            대기.append(name+': 시각 미정으로 시작·종료 범위 검사 대기');continue
        value=(day-1)*1440+minute
        text=t['값']
        duration=r.get('머무는시간')
        duration=duration if type(duration) in [int,float] and duration>=0 else None
        if start is not None and value<start:
            충돌.append(name+f': {text} 일정이 지정한 시작 전입니다.')
        if end is not None and value>end:
            충돌.append(name+f': {text} 일정이 지정한 종료 후입니다.')
        elif end is not None and duration is not None and value+duration>end:
            충돌.append(name+f': {text}부터 {duration}분 머물면 종료 시각을 넘습니다.')
        if duration is None:
            대기.append(name+': 머무는 시간 미정으로 끝나는 시각 검사 대기')
        for label,(bound_day,bound_min,_) in 경계.items():
            if bound_day is None and bound_min is not None:
                if (label=='시작' and minute<bound_min) or (label=='종료' and minute>bound_min):
                    참고.append(name+f': {label} 일차를 {day}일차, 시각을 {조건[label+"시각"]}로 선택하면 {text} 일정과 충돌합니다.')
                elif label=='종료' and duration is not None and minute+duration>bound_min:
                    참고.append(name+f': 종료를 {day}일차 {조건["종료시각"]}로 선택하면 {text} 일정의 머무는 시간을 포함해 종료를 넘습니다.')
        일정.append((r.get('안','공통'),value,duration,name))
    for i,(plan,minute,duration,name) in enumerate(일정):
        if duration is None:continue
        for other,other_min,other_duration,other_name in 일정[i+1:]:
            if plan==other and minute<=other_min<minute+duration:
                충돌.append(f'일정 겹침: {name}의 머무는 시간과 {other_name}의 시작이 겹칩니다.')
            elif plan==other and other_min<minute:
                # 입력 순서와 무관하게 검사한다. 반대 순서는 다음 쌍으로 확인할 수 없다.
                if other_duration is not None and other_min+other_duration>minute:
                    충돌.append(f'일정 겹침: {other_name}의 머무는 시간과 {name}의 시작이 겹칩니다.')
    return {'충돌':list(dict.fromkeys(충돌)),'확인대기':list(dict.fromkeys(대기)),
            '일차미정참고':list(dict.fromkeys(참고)),
            '검사범위':'일차·시각·명시된 머무는 시간 비교. 이동시간·영업시간 자동 검증 및 재배치 없음.'}
