"""runs/의 기존 저장본(1~3단계 결과)을 공유 기획 기록으로 옮긴다. 원본은 읽기만 한다.
사용: python 기록가져오기.py <실행>/<회차>/통합시험_*"""
import json
import sys
from pathlib import Path
from app.공통 import 기획기록 as 기록모듈

기준=Path(__file__).resolve().parents[1]


def _json(path):
    try:
        v=json.loads(path.read_text(encoding='utf-8'))
        return v if isinstance(v,dict) else None
    except (OSError,ValueError):
        return None


def _코스(path):
    """3단계 결과는 실제 AI 답이라 앞말과 ```json 블록이 붙을 수 있다. 3단계 검사와 같은 읽기를 쓴다."""
    from app.공통.단계연결 import JSON_읽기
    try:
        return JSON_읽기(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return None


def 가져오기(runs루트,시험id,작성자='사람:가져오기',목표='기존 저장본 가져오기',희망=()):
    root=Path(runs루트).resolve();조각=시험id.split('/')
    if len(조각)!=3 or any(p in ['','.','..'] for p in 조각):raise ValueError('시험id는 <실행>/<회차>/통합시험_* 형식')
    원본=root/조각[0]/조각[1];시험=원본/조각[2]
    if not 시험.is_dir():raise ValueError(f'없는 시험: {시험id}')
    if (root/'기획'/조각[2]/'기획기록.json').exists():raise FileExistsError(f'이미 가져온 기록: {조각[2]}')
    선택=_json(원본/'1단계_선택.json') or {};전달=_json(원본/'3단계_전달_준비.json') or {}
    입력=_json(시험/'3단계_입력.json') or {};코스=_코스(시험/'3단계_결과.md')
    조건={**(선택.get('조건') or 전달.get('조건') or {}),'코스작성조건':입력.get('코스작성조건',{})}
    r=기록모듈.새_기록(조건,작성자,목표,기록id=조각[2],희망=희망)
    if 전달.get('기관업로드'):r['기관업로드']=전달['기관업로드']
    if 전달.get('기획모드')=='자율이용':
        r['실행정책']={'모드':'자율이용','대안비교':True,'최대버전':2}
    r['결정이력'][-1]['근거']=f'{조각[0]}/{조각[1]}/1단계_선택.json'
    src2=f'{조각[0]}/{조각[1]}/3단계_전달_준비.json'
    for x in 전달.get('근거목록',[]):기록모듈.추가(r,'근거',x if isinstance(x,dict) else {'값':x},'코드:가져오기',src2)
    for x in 전달.get('경고목록',[]):기록모듈.추가(r,'경고',x if isinstance(x,dict) else {'문구':str(x)},'코드:가져오기',src2)
    if 코스:
        제안=코스.get('대안제안')
        주안={k:v for k,v in 코스.items() if k!='대안제안'}
        기록모듈.추가(r,'코스안',{'안id':'A','코스':주안,'출처시험id':시험id},'코드:가져오기',시험id+'/3단계_결과.md')
        if 전달.get('대안비교요청'):
            from app.단계3_코스검토.대안비교 import 등록
            등록(r,제안,시험id)
            if 제안 is None and isinstance(코스.get('대안불가이유'),str) and 코스['대안불가이유'].strip():
                r['대안상태']['이유']=코스['대안불가이유'].strip()[:500]
                r['대안명시불가']=True
        for x in 코스.get('남은경고',[]):기록모듈.추가(r,'경고',{**x,'안id':'A'} if isinstance(x,dict) else {'문구':str(x)},'코드:가져오기',시험id+'/3단계_결과.md')
    else:
        기록모듈.추가(r,'경고',{'문구':'코스 결과 없음','종류':'가져오기'},'코드:가져오기',시험id)
    기록모듈.저장(r,root)
    return r


if __name__=='__main__':
    if len(sys.argv)!=2:sys.exit('사용: python 기록가져오기.py <실행>/<회차>/통합시험_*')
    r=가져오기(기준/'runs',sys.argv[1])
    print(기준/'runs'/'기획'/r['기록id']/'기획기록.json')
    print({k:len(r[k]) for k in ['근거','후보','코스안','경고','결정이력']})
