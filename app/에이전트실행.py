"""기록 조각(JSON)으로 에이전트를 부르고 JSON 결과를 돌려준다.
한도 확인 → 호출 → 실행 기록. 실패해도 예외를 올리지 않고 기록에 남긴다."""
import asyncio
import inspect
import json
import re
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


def _부르기(실행함수,지침경로,입력글):
    결과=실행함수(지침경로,입력글)
    return asyncio.run(결과) if inspect.isawaitable(결과) else 결과


def 호출(기록,에이전트,지침경로,행동,대상,입력,이유,실행함수=None):
    ok,why=기록모듈.한도_확인(기록,에이전트,행동,대상)
    if not ok:
        기록모듈.실행_기록(기록,에이전트,행동,대상,why,'보류')
        return None
    if 실행함수 is None:
        from run_stage import 단계_실행 as 실행함수
    입력글=json.dumps(입력,ensure_ascii=False)
    try:
        글=_부르기(실행함수,지침경로,입력글)
    except Exception as e:
        기록모듈.실행_기록(기록,에이전트,행동,대상,f'{이유} / 오류: {type(e).__name__}: {e}'[:300],'실패',AI호출=1)
        return None
    값=JSON_꺼내기(글)
    if 값 is None:
        기록모듈.실행_기록(기록,에이전트,행동,대상,이유+' / 응답에 JSON 없음','실패',AI호출=1)
        return None
    기록모듈.실행_기록(기록,에이전트,행동,대상,이유,'성공',AI호출=1)
    return 값
