"""총괄: 공유 기획 기록을 보고 다음 할 일을 정하고, 처리기를 부르고, 부족하면 되돌린다.
다음_할일()은 지금 규칙이고, 다음 단계에서 AI 판단으로 바꾼다(입출력 고정).
실행·한도·권한 검사는 항상 코드(처리기·기획기록)가 한다.
사용: python 총괄.py <기록id> [--모의]"""
import json
import shutil
import sys
from pathlib import Path
import 기획기록 as 기록모듈
import 처리기
import 기록도구

행동목록=['코스','수집','점검','검증','담당자에게']


def _최신(기록):
    if not 기록['코스안']:return None
    안=기록['코스안'][-1]
    return 처리기.최신안(기록,안['안id'])


def _경고(기록,종류,안id,버전):
    return [x for x in 기록['경고'] if x.get('종류')==종류 and x.get('안id')==안id and x.get('버전',1)==버전]


def 다음_할일(기록):
    안=_최신(기록)
    if 안 is None:return {'행동':'코스','대상':'A','이유':'코스안이 아직 없음'}
    안id=안['안id'];버전=안.get('버전',1)
    결과=_경고(기록,'검증결과',안id,버전)
    if 결과:
        if 결과[-1].get('통과'):return {'행동':'담당자에게','대상':안id,'이유':f'{안id}안 {버전}버전 검증 통과 · 담당자 검토'}
        문제=_경고(기록,'검증',안id,버전)
        if any(x.get('되돌릴곳')=='담당자' for x in 문제):
            return {'행동':'담당자에게','대상':안id,'이유':'에이전트가 풀 수 없는 문제: '+'; '.join(x['문구'] for x in 문제 if x.get('되돌릴곳')=='담당자')}
        수집문제=[x['문구'] for x in 문제 if x.get('되돌릴곳')=='수집']
        마지막검증=max((i for i,x in enumerate(기록['실행']) if x['에이전트']=='에이전트:검증' and x['대상']==안id),default=-1)
        수집함=any(x['에이전트']=='에이전트:수집' for x in 기록['실행'][마지막검증+1:])
        if 수집문제 and not 수집함:
            return {'행동':'수집','대상':'; '.join(수집문제),'이유':f'{안id}안 {버전}버전 검증에서 자료 부족'}
        return {'행동':'코스','대상':안id,'이유':'검증 문제 반영해 다시 작성: '+'; '.join(x['문구'] for x in 문제)}
    if not _경고(기록,'코드점검',안id,버전):return {'행동':'점검','대상':안id,'이유':f'{안id}안 {버전}버전 요일·시간표 점검 전'}
    return {'행동':'검증','대상':안id,'이유':f'{안id}안 {버전}버전 독립 검증 전'}


def _보완요청(기록,안id):
    안=_최신(기록)
    if 안 is None:return []
    문제=[x['문구'] for x in _경고(기록,'검증',안id,안.get('버전',1))]
    수집=[f"후보: {x.get('이름')} ({x.get('출처ID')})" for x in 기록['후보'] if x.get('상태') in ['후보','승인']]
    return 문제+수집


def 돌리기(기록,runs루트,실행함수=None,최대단계=12,저장=False):
    steps=[]
    for _ in range(최대단계):
        d=다음_할일(기록)
        if d['행동'] not in 행동목록:d={'행동':'담당자에게','대상':'','이유':f"허용되지 않은 행동: {d['행동']}"}
        steps.append(d)
        if d['행동']=='담당자에게':break
        n=len(기록['실행'])
        if d['행동']=='코스':처리기.코스짜기(기록,d['대상'],runs루트,_보완요청(기록,d['대상']),실행함수)
        elif d['행동']=='수집':처리기.수집하기(기록,d['대상'],실행함수)
        elif d['행동']=='점검':기록도구.코스_점검(기록,d['대상'])
        elif d['행동']=='검증':처리기.검증하기(기록,d['대상'],실행함수)
        if 저장:기록모듈.저장(기록,runs루트)
        보류=[x for x in 기록['실행'][n:] if x['결과']=='보류']
        if 보류:
            steps.append({'행동':'담당자에게','대상':d['대상'],'이유':보류[-1]['이유']});break
    else:
        steps.append({'행동':'담당자에게','대상':'','이유':f'최대 {최대단계}단계 도달'})
    last=steps[-1]
    기록['결정이력'].append({'시각':기록모듈._지금(),'작성자':'에이전트:총괄','행동':'담당자에게','영역':'',
                         '대상id':last['대상'],'근거':' → '.join(s['행동'] for s in steps),'요약':last['이유']})
    if 저장:기록모듈.저장(기록,runs루트)
    return steps


def 모의응답():
    """AI 없이 흐름을 보여 주는 정해진 응답: 검증 첫 번째는 자료 부족으로 반려, 두 번째는 통과."""
    횟수={'검증':0}
    def fn(지침,입력글):
        if 지침.endswith('코스검토.md'):return json.dumps({'칸목록':[],'식사목록':[],'메모':'모의 코스'},ensure_ascii=False)
        if 지침.endswith('자료수집.md'):
            return json.dumps({'후보':[{'이름':'향촌문화관(모의)','종류':'관광지','내용':'모의 응답','출처ID':'S70','출처등급':'공식'}],'못찾음':[]},ensure_ascii=False)
        횟수['검증']+=1
        if 횟수['검증']==1:
            return json.dumps({'통과':False,'문제':[{'종류':'운영','대상':'밤','내용':'평일 밤 후보 없음(모의)','되돌릴곳':'수집'}]},ensure_ascii=False)
        return '{"통과":true,"문제":[]}'
    return fn


if __name__=='__main__':
    if len(sys.argv)<2:sys.exit('사용: python 총괄.py <기록id> [--모의]')
    root=Path(__file__).resolve().parent/'runs';기록id=sys.argv[1];모의='--모의' in sys.argv
    if 모의:  # 원래 기록은 그대로 두고 복사본에서 돌린다
        새id=기록id+'_모의';src=root/'기획'/기록id;dst=root/'기획'/새id
        if dst.exists():shutil.rmtree(dst)
        r=기록모듈.읽기(root,기록id);r['기록id']=새id;r['코스안']=[]  # 흐름을 처음부터 보여 주기 위해 코스안 비움
        기록id=새id
    else:
        r=기록모듈.읽기(root,기록id)
    steps=돌리기(r,root,모의응답() if 모의 else None,저장=True)
    for i,s in enumerate(steps,1):print(f"{i}. {s['행동']} · {s['대상'][:40]} · {s['이유'][:80]}")
    print('기록:',root/'기획'/기록id/'기획기록.json')
