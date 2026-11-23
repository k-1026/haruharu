"""공유 기획 기록: 기획 하나 = 기록 파일 하나.
에이전트·사람·코드가 모두 이 기록만 읽고 쓴다. 모든 쓰기는 결정이력에 남는다(추가만).
권한: 조건 변경·후보 승인은 사람만. 에이전트가 올린 후보는 항상 '후보'. 확정 자료 파일은 쓰지 않는다."""
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

버전=1
쓰기영역=['근거','후보','코스안','경고']
기본한도={'같은일_재시도':2,'AI호출':30}
실행결과=['성공','실패','반려','보류']


def _지금():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _id검사(기록id):
    if not isinstance(기록id,str) or not re.fullmatch(r'[0-9A-Za-z가-힣_\-]+',기록id):
        raise ValueError('기록id 형식을 확인하세요.')
    return 기록id


def _작성자(작성자):
    if not isinstance(작성자,str) or not re.match(r'^(사람|에이전트|코드):.+',작성자):
        raise ValueError('작성자는 사람:/에이전트:/코드: 로 시작해야 합니다.')
    return 작성자


def _사람만(작성자,일):
    if not _작성자(작성자).startswith('사람:'):raise PermissionError(f'{일}은 사람만 할 수 있습니다.')


def _이력(기록,작성자,행동,영역='',대상id='',근거='',요약=''):
    기록['결정이력'].append({'시각':_지금(),'작성자':작성자,'행동':행동,'영역':영역,'대상id':대상id,'근거':근거,'요약':요약})


def 새_기록(조건,작성자,목표='',기록id=None):
    _사람만(작성자,'기획 생성')
    기록id=_id검사(기록id or datetime.now().strftime('%Y%m%d_%H%M%S_')+secrets.token_hex(3))
    기록={'버전':버전,'기록id':기록id,'생성시각':_지금(),'목표':목표,'조건':dict(조건),
         '근거':[],'후보':[],'코스안':[],'경고':[],'결정이력':[],'실행':[],'한도':dict(기본한도)}
    _이력(기록,작성자,'생성','조건',근거='담당자 입력',요약=목표)
    return 기록


def 추가(기록,영역,항목,작성자,근거=''):
    _작성자(작성자)
    if 영역 not in 쓰기영역:raise ValueError(f'쓸 수 없는 영역: {영역}')
    if not isinstance(항목,dict):raise ValueError('항목은 dict여야 합니다.')
    새={**항목,'id':f'{영역}-{len(기록[영역])+1}','작성자':작성자,'시각':_지금()}
    if 영역=='후보':새['상태']='후보'  # 승인은 승인()으로만, 사람만
    기록[영역].append(새)
    _이력(기록,작성자,'추가',영역,새['id'],근거,str(항목.get('이름') or 항목.get('문구') or '')[:80])
    return 새['id']


def 조건_변경(기록,값,작성자,근거):
    _사람만(작성자,'조건 변경')
    if not isinstance(값,dict):raise ValueError('조건은 dict여야 합니다.')
    기록['조건'].update(값)
    _이력(기록,작성자,'조건변경','조건',근거=근거,요약=', '.join(값))


def 승인(기록,후보id,작성자,근거):
    _사람만(작성자,'후보 승인')
    item=next((x for x in 기록['후보'] if x.get('id')==후보id),None)
    if item is None:raise ValueError(f'없는 후보: {후보id}')
    item['상태']='승인'
    _이력(기록,작성자,'승인','후보',후보id,근거)


def _경로(루트,기록id):
    return Path(루트)/'기획'/_id검사(기록id)/'기획기록.json'


def 저장(기록,루트):
    path=_경로(루트,기록['기록id']);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    try:
        with tmp.open('w',encoding='utf-8') as f:json.dump(기록,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()
    return path


def 읽기(루트,기록id):
    return json.loads(_경로(루트,기록id).read_text(encoding='utf-8'))
