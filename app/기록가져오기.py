"""runs/의 기존 저장본(1~3단계 결과)을 공유 기획 기록으로 옮긴다. 원본은 읽기만 한다.
사용: python 기록가져오기.py <실행>/<회차>/통합시험_*"""
import json
import sys
from pathlib import Path
import 기획기록 as 기록모듈

기준=Path(__file__).resolve().parent


def _json(path):
    try:
        v=json.loads(path.read_text(encoding='utf-8'))
        return v if isinstance(v,dict) else None
    except (OSError,ValueError):
        return None


def 가져오기(runs루트,시험id,작성자='사람:가져오기'):
    root=Path(runs루트).resolve();조각=시험id.split('/')
    if len(조각)!=3 or any(p in ['','.','..'] for p in 조각):raise ValueError('시험id는 <실행>/<회차>/통합시험_* 형식')
    원본=root/조각[0]/조각[1];시험=원본/조각[2]
    if not 시험.is_dir():raise ValueError(f'없는 시험: {시험id}')
    if (root/'기획'/조각[2]/'기획기록.json').exists():raise FileExistsError(f'이미 가져온 기록: {조각[2]}')
    선택=_json(원본/'1단계_선택.json') or {};전달=_json(원본/'3단계_전달_준비.json') or {}
    입력=_json(시험/'3단계_입력.json') or {};코스=_json(시험/'3단계_결과.md')
    조건={**(선택.get('조건') or 전달.get('조건') or {}),'코스작성조건':입력.get('코스작성조건',{})}
    r=기록모듈.새_기록(조건,작성자,'기존 저장본 가져오기',기록id=조각[2])
    r['결정이력'][-1]['근거']=f'{조각[0]}/{조각[1]}/1단계_선택.json'
    src2=f'{조각[0]}/{조각[1]}/3단계_전달_준비.json'
    for x in 전달.get('근거목록',[]):기록모듈.추가(r,'근거',x if isinstance(x,dict) else {'값':x},'코드:가져오기',src2)
    for x in 전달.get('경고목록',[]):기록모듈.추가(r,'경고',x if isinstance(x,dict) else {'문구':str(x)},'코드:가져오기',src2)
    if 코스:
        기록모듈.추가(r,'코스안',{'안id':'A','코스':코스,'출처시험id':시험id},'코드:가져오기',시험id+'/3단계_결과.md')
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
