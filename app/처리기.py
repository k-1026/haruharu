"""에이전트별 처리기: 에이전트를 부르고 결과를 공유 기획 기록의 해당 영역에 쓴다."""
import 기획기록 as 기록모듈
from 에이전트실행 import 호출

수집지침='.claude/agents/자료수집.md'
코스지침='.claude/agents/코스검토.md'
검증지침='.claude/agents/검증.md'
허용등급=['공식','통계','언론','개인','운영주체']


def _원본입력(runs루트,출처시험id):
    import json
    from pathlib import Path
    if not 출처시험id:return None
    조각=출처시험id.split('/')
    if any(p in ['','.','..'] for p in 조각):return None
    try:
        v=json.loads((Path(runs루트).joinpath(*조각)/'3단계_입력.json').read_text(encoding='utf-8'))
        return v if isinstance(v,dict) else None
    except (OSError,ValueError):
        return None


def 코스입력(기록,안id,runs루트,보완요청):
    """코스 에이전트에 줄 입력. 조건·희망은 항상 그 안의 최신 적용 조건으로 덮어쓴다.
    가져온 기존 시험 입력(근거목록·코스작성조건 등)은 그 안 → A안 순서로 찾아 바탕으로만 쓴다.
    꼭 지킬 조건을 바꾼 안이면 바탕 근거가 맞지 않을 수 있어 '자료재검토필요'를 붙인다."""
    기록모듈.맞추기(기록)
    적용=기록모듈.적용조건(기록,안id)
    출처=[x for x in 기록['코스안'] if x.get('출처시험id') and x.get('안id')==안id] or          [x for x in 기록['코스안'] if x.get('출처시험id') and x.get('안id')=='A']
    바탕=(_원본입력(runs루트,출처[0]['출처시험id']) if 출처 else None) or {'근거목록':기록['근거']}
    안=기록모듈.안_찾기(기록,안id)
    입력={**바탕,'조건':적용['조건'],'희망':적용['희망'],'원래요청':기록['원래요청'],
         '안':{'안id':안id,'설명':안.get('설명',''),'바꾼희망':안.get('바꾼희망',{}),'바꾼조건':안.get('바꾼조건',{}),'이유':안.get('이유','')},
         '보완요청':list(보완요청),'후보':[x for x in 기록['후보'] if x.get('상태') in ['후보','승인']]}
    if 적용['바꾼조건']:입력['자료재검토필요']=f"꼭 지킬 조건을 바꾼 안({', '.join(적용['바꾼조건'])}): 바탕 근거가 이 조건에 맞는지 다시 확인해야 함"
    같은안=[x for x in 기록['코스안'] if x.get('안id')==안id]
    if 같은안:
        이전=max(같은안,key=lambda x:x.get('버전',1));입력['이전코스']=이전['코스'];입력['이전버전']=이전.get('버전',1)
    return 입력


def 코스짜기(기록,안id,runs루트,보완요청,실행함수=None):
    입력=코스입력(기록,안id,runs루트,보완요청)
    값=호출(기록,'에이전트:코스',코스지침,'코스',안id,입력,'코스안 작성' if not 보완요청 else '보완 요청 반영',실행함수)
    if 값 is None:return False
    if not isinstance(값.get('칸목록'),list):
        기록모듈.실행_기록(기록,'에이전트:코스','코스',안id,'응답에 칸목록 없음','실패')
        return False
    버전=max(기록모듈.버전목록(기록,안id),default=0)+1
    기록모듈.추가(기록,'코스안',{'안id':안id,'코스':값,'버전':버전,'보완요청':list(보완요청)},'에이전트:코스','; '.join(보완요청))
    return True


되돌릴곳허용=['수집','코스']


def 최신안(기록,안id):
    같은안=[x for x in 기록['코스안'] if x.get('안id')==안id]
    if not 같은안:raise ValueError(f'없는 코스안: {안id}')
    return max(같은안,key=lambda x:x.get('버전',1))


def 검증하기(기록,안id,실행함수=None):
    안=최신안(기록,안id);버전=안.get('버전',1)
    입력={'안id':안id,'버전':버전,'코스':안['코스'],
         '코드점검':[x for x in 기록['경고'] if x.get('종류')=='코드점검' and x.get('안id')==안id],
         '근거':[{'id':x.get('근거ID') or x.get('id'),'출처등급':x.get('출처등급','')} for x in 기록['근거']],
         '후보':[{'이름':x.get('이름'),'상태':x.get('상태'),'출처등급':x.get('출처등급')} for x in 기록['후보']]}
    값=호출(기록,'에이전트:검증',검증지침,'검증',안id,입력,f'{안id}안 {버전}버전 독립 검증',실행함수)
    if 값 is None:return {'통과':False,'문제':[],'오류':True}
    문제=[x for x in 값.get('문제') or [] if isinstance(x,dict)]
    통과=bool(값.get('통과')) and not 문제
    for x in 문제:
        곳=x.get('되돌릴곳') if x.get('되돌릴곳') in 되돌릴곳허용 else '담당자'
        기록모듈.추가(기록,'경고',{'종류':'검증','안id':안id,'버전':버전,'되돌릴곳':곳,
                     '문구':f"[{x.get('종류','')}] {x.get('대상','')}: {x.get('내용','')}"},'에이전트:검증',f'{안id}안 {버전}버전')
        x['되돌릴곳']=곳
    기록모듈.추가(기록,'경고',{'종류':'검증결과','안id':안id,'버전':버전,'통과':통과,'문구':'검증 통과' if 통과 else f'검증 반려 {len(문제)}건'},'에이전트:검증')
    if not 통과:기록모듈.실행_기록(기록,'에이전트:검증','검증',안id,f'{len(문제)}건 문제로 반려','반려')
    return {'통과':통과,'문제':문제}


def 수집하기(기록,요청,실행함수=None):
    입력={'요청':요청,'조건':기록['조건'],'이미있는후보':[x.get('이름','') for x in 기록['후보']]}
    값=호출(기록,'에이전트:수집',수집지침,'수집',요청[:60],입력,'코스 빈칸 보완 요청',실행함수)
    if 값 is None:return 0
    n=0
    for x in 값.get('후보') or []:
        if not isinstance(x,dict):continue
        if not str(x.get('출처ID','')).strip() or x.get('출처등급') not in 허용등급:
            기록모듈.추가(기록,'경고',{'종류':'수집','문구':f"출처 없는 후보 제외: {x.get('이름','')}"},'에이전트:수집',요청)
            continue
        기록모듈.추가(기록,'후보',{k:x.get(k,'') for k in ['이름','종류','내용','출처ID','출처등급','확인일','메모']}|{'요청':요청},'에이전트:수집',x.get('출처ID',''))
        n+=1
    for 문구 in 값.get('못찾음') or []:
        기록모듈.추가(기록,'경고',{'종류':'수집','문구':f'못 찾음: {문구}'},'에이전트:수집',요청)
    return n
