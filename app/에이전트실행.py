"""기록 조각(JSON)으로 에이전트를 부르고 JSON 결과를 돌려준다.
한도 확인 → 호출 → 실행 기록. 실패해도 예외를 올리지 않고 기록에 남긴다."""
import asyncio
import inspect
import json
import re
import time
import 기획기록 as 기록모듈


def JSON_꺼내기(글):
    if not isinstance(글,str):return None
    blocks=re.findall(r'```json\s*(.*?)```',글,re.S)
    for 후보 in [*reversed(blocks),글.strip()]:
        try:
            v=json.loads(후보)
            if isinstance(v,dict):return v
        except ValueError:
            continue
    return None


혼잡대기초=[5,15,45]  # 503·429 같은 일시적 혼잡일 때 기다렸다 다시 부르는 간격
_혼잡표시=re.compile(r'\b(503|429|500|502|504)\b|UNAVAILABLE|RESOURCE_EXHAUSTED|overloaded|Overloaded|rate limit|temporarily',re.I)


def 혼잡오류인가(e):
    if isinstance(e,TimeoutError):return False
    code=getattr(e,'code',None) or getattr(e,'status_code',None)
    return code in [429,500,502,503,504] or bool(_혼잡표시.search(str(e)))


def _한번(실행함수,지침경로,입력글):
    결과=실행함수(지침경로,입력글)
    return asyncio.run(결과) if inspect.isawaitable(결과) else 결과


def _부르기(실행함수,지침경로,입력글,시도,최대시도=4):
    """혼잡 오류만 기다렸다 재시도. 키·형식 오류 등은 바로 올린다. 시도 목록에 호출 횟수를 쌓는다."""
    from run_stage import 호출_기한, 제한초_읽기, AI응답시간초과
    from 설정 import 설정_읽기
    기한=time.monotonic()+제한초_읽기(설정_읽기(),지침경로)
    기존=호출_기한.get()
    if 기존 is not None:기한=min(기한,기존)
    token=호출_기한.set(기한)
    try:
        횟수=min(len(혼잡대기초)+1,최대시도)
        for i in range(횟수):
            if time.monotonic()>=기한:raise AI응답시간초과('AI 호출 제한 시간을 소진했습니다.')
            시도.append(1)
            try:
                return _한번(실행함수,지침경로,입력글)
            except Exception as e:
                if not 혼잡오류인가(e) or i==횟수-1:raise
                if time.monotonic()+혼잡대기초[i]>=기한:
                    raise AI응답시간초과('혼잡 재시도에 필요한 시간이 남지 않아 중단했습니다.') from e
                time.sleep(혼잡대기초[i])
    finally:
        호출_기한.reset(token)


def 호출(기록,에이전트,지침경로,행동,대상,입력,이유,실행함수=None):
    ok,why=기록모듈.한도_확인(기록,에이전트,행동,대상)
    if not ok:
        기록모듈.실행_기록(기록,에이전트,행동,대상,why,'보류')
        return None
    if 실행함수 is None:
        from run_stage import 단계_실행 as 실행함수
    입력글=json.dumps(입력,ensure_ascii=False);시도=[]
    try:
        한도={**기록모듈.기본한도,**기록.get('한도',{})}
        남은=한도['AI호출']-sum(int(x.get('AI호출',0)) for x in 기록['실행'])
        글=_부르기(실행함수,지침경로,입력글,시도,남은)
    except Exception as e:
        from 오류기록 import 진단, 안전문장
        기록.setdefault('AI오류',[]).append(진단(e,단계=지침경로))
        기록모듈.실행_기록(기록,에이전트,행동,대상,안전문장(f'{이유}{_재시도문구(시도)} / 오류: {type(e).__name__}: {e}')[:300],'실패',AI호출=len(시도))
        return None
    값=JSON_꺼내기(글)
    if 값 is None:
        기록모듈.실행_기록(기록,에이전트,행동,대상,이유+_재시도문구(시도)+' / 응답에 JSON 없음','실패',AI호출=len(시도))
        return None
    기록모듈.실행_기록(기록,에이전트,행동,대상,이유+_재시도문구(시도),'성공',AI호출=len(시도))
    return 값


def _재시도문구(시도):
    return f' (혼잡 재시도 {len(시도)-1}회)' if len(시도)>1 else ''
