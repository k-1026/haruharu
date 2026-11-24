"""공유 기획 기록: 기획 하나 = 기록 파일 하나.
에이전트·사람·코드가 모두 이 기록만 읽고 쓴다. 모든 쓰기는 결정이력에 남는다(추가만).
권한: 조건 변경·후보 승인은 사람만. 에이전트가 올린 후보는 항상 '후보'. 확정 자료 파일은 쓰지 않는다.

조건을 세 겹으로 나눠 둔다.
- 원래요청: 처음 받은 조건·목표·희망. 만든 뒤에는 바꾸지 않는다(AI가 요청을 바꿨는지 대조용).
- 조건(필수): 계절·언어권·지역·체류기간처럼 꼭 지킬 조건. 바꾸려면 사람이 바꾼다.
- 희망: 조정해도 되는 바람(예: 저녁은 동구에서). 대안(B안 등)은 희망을 바꿔 만든다.
안(A·B…)마다 적용 조건과 바꾼 점을 따로 두고, 코스안은 안id·버전으로 쌓는다. 사람이 고른 안과 버전은 선택에 둔다."""
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

버전=2  # 기록 형식 버전. 1 → 2: 원래요청·희망·안·선택 추가
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


def 새_기록(조건,작성자,목표='',기록id=None,희망=()):
    _사람만(작성자,'기획 생성')
    기록id=_id검사(기록id or datetime.now().strftime('%Y%m%d_%H%M%S_')+secrets.token_hex(3))
    희망목록=[{'id':f'희망-{i}','내용':str(x).strip()} for i,x in enumerate(희망,1) if str(x).strip()]
    기록={'버전':버전,'기록id':기록id,'생성시각':_지금(),'목표':목표,'조건':dict(조건),'희망':희망목록,
         '원래요청':{'조건':json.loads(json.dumps(조건,ensure_ascii=False)),'목표':목표,'희망':[dict(x) for x in 희망목록]},
         '안':[{'안id':'A','설명':'원래 요청을 유지한 안','바꾼희망':{},'바꾼조건':{},'작성자':작성자,'시각':_지금()}],
         '선택':None,'근거':[],'후보':[],'코스안':[],'경고':[],'결정이력':[],'실행':[],'한도':dict(기본한도)}
    _이력(기록,작성자,'생성','조건',근거='담당자 입력',요약=목표)
    return 기록


def 맞추기(기록):
    """형식 1 기록(가져온 기존 저장본 등)을 2로 맞춘다. 원래요청은 지금 조건으로 채우고 그렇게 채웠음을 남긴다."""
    if 기록.get('버전',1)>=2:return 기록
    기록.setdefault('희망',[])
    기록.setdefault('원래요청',{'조건':json.loads(json.dumps(기록.get('조건',{}),ensure_ascii=False)),'목표':기록.get('목표',''),
                           '희망':[],'메모':'형식 1 기록이라 맞출 때의 조건으로 채움'})
    안들=list(dict.fromkeys(x.get('안id','A') for x in 기록.get('코스안',[]))) or ['A']
    기록.setdefault('안',[{'안id':a,'설명':'원래 요청을 유지한 안' if a=='A' else '형식 1 기록의 안','바꾼희망':{},'바꾼조건':{},
                         '작성자':'코드:맞추기','시각':_지금()} for a in 안들])
    기록.setdefault('선택',None)
    기록['버전']=2
    return 기록


def 안_찾기(기록,안id):
    return next((x for x in 기록.get('안',[]) if x['안id']==안id),None)


def 안_추가(기록,안id,설명,작성자,바꾼희망=None,바꾼조건=None,이유=''):
    """대안을 등록한다. 희망은 에이전트도 바꿀 수 있지만, 꼭 지킬 조건(필수)을 바꾸는 안은 사람만 만든다."""
    _작성자(작성자)
    if not isinstance(안id,str) or not re.fullmatch(r'[A-Z]',안id):raise ValueError('안id는 A~Z 한 글자')
    if 안_찾기(기록,안id):raise ValueError(f'이미 있는 안: {안id}')
    바꾼희망=dict(바꾼희망 or {});바꾼조건=dict(바꾼조건 or {})
    if 바꾼조건:_사람만(작성자,'꼭 지킬 조건을 바꾼 안 만들기')
    없는희망=[k for k in 바꾼희망 if not any(h['id']==k for h in 기록.get('희망',[]))]
    if 없는희망:raise ValueError(f'없는 희망: {없는희망}')
    없는조건=[k for k in 바꾼조건 if k not in 기록['조건']]
    if 없는조건:raise ValueError(f'없는 조건: {없는조건}')
    기록['안'].append({'안id':안id,'설명':설명,'바꾼희망':바꾼희망,'바꾼조건':바꾼조건,'이유':이유,'작성자':작성자,'시각':_지금()})
    _이력(기록,작성자,'안추가','안',안id,이유,설명[:80])


def 적용조건(기록,안id):
    """그 안이 따르는 조건 = 꼭 지킬 조건 + 희망, 거기에 그 안에서 바꾼 것을 덮어쓴 값."""
    안=안_찾기(기록,안id)
    if 안 is None:raise ValueError(f'없는 안: {안id}')
    조건={**기록['조건'],**안.get('바꾼조건',{})}
    희망=[{**h,'내용':안.get('바꾼희망',{}).get(h['id'],h['내용']),'바뀜':h['id'] in 안.get('바꾼희망',{})} for h in 기록.get('희망',[])]
    return {'조건':조건,'희망':희망,'바꾼조건':list(안.get('바꾼조건',{})),'원래요청과_다름':bool(안.get('바꾼조건') or 안.get('바꾼희망'))}


def 버전목록(기록,안id):
    return sorted({x.get('버전',1) for x in 기록['코스안'] if x.get('안id')==안id})


def 선택(기록,안id,버전값,작성자,근거=''):
    """사람이 안과 버전을 고른다. 이 선택이 있어야 뒤 단계(확정·홍보·문서)가 무엇을 쓸지 안다."""
    _사람만(작성자,'안 선택')
    if 버전값 not in 버전목록(기록,안id):raise ValueError(f'없는 코스안: {안id}안 {버전값}버전')
    기록['선택']={'안id':안id,'버전':버전값,'작성자':작성자,'시각':_지금()}
    _이력(기록,작성자,'선택','선택',f'{안id}-{버전값}',근거,f'{안id}안 {버전값}버전 선택')


def 검증상태(기록,안id,버전값):
    """그 안·그 버전의 검증 결과와 남은 문제만 모은다. 다른 버전의 경고를 섞지 않는다."""
    같은=[x for x in 기록['경고'] if x.get('안id')==안id and x.get('버전',1)==버전값]
    결과=[x for x in 같은 if x.get('종류')=='검증결과']
    return {'검증':('통과' if 결과[-1].get('통과') else '반려') if 결과 else '검증 전',
            '남은문제':[x['문구'] for x in 같은 if x.get('종류')=='검증'] if 결과 and not 결과[-1].get('통과') else [],
            '코드점검':next((x['문구'] for x in reversed(같은) if x.get('종류')=='코드점검'),None)}


def 추가(기록,영역,항목,작성자,근거=''):
    _작성자(작성자)
    if 영역 not in 쓰기영역:raise ValueError(f'쓸 수 없는 영역: {영역}')
    if not isinstance(항목,dict):raise ValueError('항목은 dict여야 합니다.')
    if 영역=='코스안':
        if not 안_찾기(맞추기(기록),항목.get('안id','')):raise ValueError(f"등록하지 않은 안: {항목.get('안id')}. 안_추가로 먼저 등록하세요.")
        if any(x.get('안id')==항목['안id'] and x.get('버전',1)==항목.get('버전',1) for x in 기록['코스안']):
            raise ValueError(f"이미 있는 버전: {항목['안id']}안 {항목.get('버전',1)}버전")
    새={**항목,'id':f'{영역}-{len(기록[영역])+1}','작성자':작성자,'시각':_지금()}
    if 영역=='후보':새['상태']='후보'  # 승인은 승인()으로만, 사람만
    기록[영역].append(새)
    _이력(기록,작성자,'추가',영역,새['id'],근거,str(항목.get('이름') or 항목.get('문구') or '')[:80])
    return 새['id']


def 조건_변경(기록,값,작성자,근거):
    _사람만(작성자,'조건 변경')
    if not isinstance(값,dict):raise ValueError('조건은 dict여야 합니다.')
    기록['조건'].update(값)  # 원래요청은 그대로 둔다
    _이력(기록,작성자,'조건변경','조건',근거=근거,요약=', '.join(값))


def 승인(기록,후보id,작성자,근거):
    _사람만(작성자,'후보 승인')
    item=next((x for x in 기록['후보'] if x.get('id')==후보id),None)
    if item is None:raise ValueError(f'없는 후보: {후보id}')
    item['상태']='승인'
    _이력(기록,작성자,'승인','후보',후보id,근거)


def 한도_확인(기록,에이전트,행동,대상=''):
    한도={**기본한도,**기록.get('한도',{})}
    실패=sum(1 for x in 기록['실행'] if (x['에이전트'],x['행동'],x['대상'])==(에이전트,행동,대상) and x['결과'] in ['실패','반려'])
    if 실패>=한도['같은일_재시도']:return False,f"재시도 한도 {한도['같은일_재시도']}회 도달: {에이전트} · {행동} · {대상}"
    호출=sum(int(x.get('AI호출',0)) for x in 기록['실행'])
    if 호출>=한도['AI호출']:return False,f"AI 호출 한도 {한도['AI호출']}회 도달"
    return True,''


def 실행_기록(기록,에이전트,행동,대상,이유,결과,AI호출=0,비용메모=''):
    _작성자(에이전트)
    if 결과 not in 실행결과:raise ValueError(f'결과는 {실행결과} 중 하나')
    if type(AI호출) is not int or AI호출<0:raise ValueError('AI호출은 0 이상의 정수')
    item={'id':f"실행-{len(기록['실행'])+1}",'시각':_지금(),'에이전트':에이전트,'행동':행동,'대상':대상,
          '이유':이유,'결과':결과,'AI호출':AI호출,'비용메모':비용메모}
    기록['실행'].append(item)
    _이력(기록,에이전트,'실행','실행',item['id'],이유,f'{행동} · {대상} → {결과}')
    return item['id']


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
    return 맞추기(json.loads(_경로(루트,기록id).read_text(encoding='utf-8')))
