"""3단계 코스: AI는 짧은 주문서만 쓰고, 코드가 후보표를 만들고 완성 코스로 조립한다.

① 후보표_만들기 — 장소·이동·근거·운영주체를 상한 안에서 고른다 (데이터가 커져도 크기 일정)
② (AI) 주문서 — `.claude/agents/코스주문.md`
③ 주문서_검사 — 없는 번호·중복 등은 고치지 않고 문제로 돌려준다
④ 조립 — 사실 값(장소명·운영·이동·시각)은 코드만 쓴다
"""
import csv
import re
from pathlib import Path

from 장소정보 import _이름, 장소_기본파일, 이동_기본파일
from 운영검토 import 휴무요일

저장소 = Path(__file__).resolve().parent.parent
기본상한 = 30
근거상한 = 40
운영주체파일 = 저장소 / '지침/3_코스검토/11_운영주체_후보.md'


def _설정():
    from 설정 import 설정_읽기
    return 설정_읽기(저장소)


def _csv(이름, 기본):
    from 설정 import 자료_파일
    path = 자료_파일(_설정(), 이름, 기본, 저장소)
    with path.open(encoding='utf-8-sig', newline='') as f:
        return [dict(r) for r in csv.DictReader(f)]


def _상한(상한):
    if 상한 is not None:
        return 상한
    값 = (_설정().get('HARUHARU_COURSE_CANDIDATES') or '').strip()
    return int(값) if 값.isdigit() and int(값) > 0 else 기본상한


def _분(v):
    v = str(v or '').strip()
    return int(v) if v.isdigit() and int(v) > 0 else None


def 치킨장소인가(장소명):
    return '(치킨 옵션)' in (장소명 or '')


def _매일휴무(r):
    closed, _ = 휴무요일(r.get('정기휴무'))
    return closed is not None and len(closed) == 7


def _이전장소이름(이전코스):
    return {_이름(r.get('장소명') or '') for r in (이전코스 or {}).get('칸목록') or [] if r.get('장소명')}


def _장소고르기(입력, 이전코스, 장소행, 상한):
    지역 = set((입력.get('조건') or {}).get('지역') or [])
    치킨 = (입력.get('코스작성조건') or {}).get('치킨선택') == '선택'
    남은 = [r for r in 장소행
            if (not 지역 or r.get('구') in 지역) and (치킨 or not 치킨장소인가(r.get('장소명')))]
    이전 = _이전장소이름(이전코스)
    먼저 = [r for r in 남은 if _이름(r['장소명']) in 이전]
    나머지 = sorted([r for r in 남은 if r not in 먼저], key=_매일휴무)  # 안정 정렬: 원래 순서 유지
    묶음 = {}
    for r in 나머지:
        묶음.setdefault(r.get('코스칸') or '', []).append(r)
    고른 = 먼저[:상한]
    줄들 = list(묶음.values())
    while len(고른) < 상한 and any(줄들):
        for 줄 in 줄들:
            if 줄 and len(고른) < 상한:
                고른.append(줄.pop(0))
    return 고른


def _근거고르기(입력, 장소이름들):
    목록 = 입력.get('근거목록') or []
    우선 = ((입력.get('코드근거추출') or {}).get('AI전달근거ID')) or []
    순서 = {id: i for i, id in enumerate(우선)}
    def 점수(r):
        if r['근거ID'] in 순서:
            return (0, 순서[r['근거ID']])
        글 = ' '.join(str(r.get(k) or '') for k in ['항목', '원자료항목명'])
        return (1 if any(n and n in 글 for n in 장소이름들) else 2, 0)
    고른 = sorted(목록, key=점수)[:근거상한]
    return [{'근거ID': r['근거ID'], '항목': r.get('항목', ''),
             '요약': f"{r.get('원자료항목명', '')} {r.get('수치_원문', '')} ({r.get('표본_대상', '')})"[:80]}
            for r in 고른]


def 운영주체표_읽기(path=운영주체파일):
    """`| O번호 | 기관 | 역할 | ...` 행. 같은 O번호는 첫 행만, 설명은 기관 + 역할 앞 40자."""
    out, 본 = [], set()
    for 줄 in Path(path).read_text(encoding='utf-8').splitlines():
        칸 = [x.strip() for x in 줄.strip().strip('|').split('|')]
        if len(칸) < 3 or not re.fullmatch(r'O\d+', 칸[0]) or 칸[0] in 본:
            continue
        본.add(칸[0])
        out.append({'O번호': 칸[0], '설명': f'{칸[1]} — {칸[2][:40]}'})
    return out


def 후보표_만들기(입력, 이전코스=None, 장소행=None, 이동행=None, 상한=None):
    장소행 = _csv('HARUHARU_PLACES_FILE', 장소_기본파일) if 장소행 is None else 장소행
    이동행 = _csv('HARUHARU_TRAVEL_FILE', 이동_기본파일) if 이동행 is None else 이동행
    고른 = _장소고르기(입력, 이전코스, 장소행, _상한(상한))
    장소 = {}
    for i, r in enumerate(고른, 1):
        키 = f"P{r.get('순번') or i}"
        while 키 in 장소:
            키 += "'"
        장소[키] = r
    이름별 = {}
    for k, r in 장소.items():
        이름별.setdefault(_이름(r['장소명']), []).append(k)
    모호 = sorted(n for n, ks in 이름별.items() if len(ks) > 1)
    이동 = []
    for r in 이동행:
        if r.get('상태') != '확인':
            continue
        a, b = 이름별.get(_이름(r.get('출발장소') or '')), 이름별.get(_이름(r.get('도착장소') or ''))
        if not a or not b or len(a) > 1 or len(b) > 1:
            continue
        이동.append({'출발': a[0], '도착': b[0], '도보분': _분(r.get('도보_분')),
                   '대중교통분': _분(r.get('대중교통_분')), '행': r})
    return {'장소': 장소, '이동': 이동, '근거': _근거고르기(입력, [_이름(r['장소명']) for r in 고른]),
            '운영주체': 운영주체표_읽기(), '이름대응불명확': 모호}


def 후보표_글(후보표):
    """AI에게 넘길 줄 단위 표. 사실 값은 여기서만 보고, 주문서에는 번호만 쓴다."""
    줄 = ['# 장소 (번호|이름|구|칸|유형|운영시간|정기휴무|상태)']
    for k, r in 후보표['장소'].items():
        줄.append('|'.join([k] + [str(r.get(c) or '') for c in ['장소명', '구', '코스칸', '장소유형', '운영시간', '정기휴무', '상태']]))
    줄.append('# 이동 (출발>도착|도보분|대중교통분)')
    줄 += [f"{x['출발']}>{x['도착']}|{x['도보분'] or ''}|{x['대중교통분'] or ''}" for x in 후보표['이동']]
    줄.append('# 근거 (ID|항목|요약)')
    줄 += [f"{x['근거ID']}|{x['항목']}|{x['요약']}" for x in 후보표['근거']]
    줄.append('# 운영주체 (번호|설명)')
    줄 += [f"{x['O번호']}|{x['설명']}" for x in 후보표['운영주체']]
    return '\n'.join(줄)


술표현 = re.compile(r'맥주|치맥|술|주점')


def 주문서_읽기(원문):
    from 에이전트실행 import JSON_꺼내기
    return JSON_꺼내기(원문)


def _가족인가(입력):
    return '가족' in str((입력.get('조건') or {}).get('동행') or '')


def _칸검사(이름, 칸들, 후보표, 입력, 근거들, 운영들):
    문제, 본 = [], set()
    당일 = 입력.get('확정체류기간') == '당일'
    for r in 칸들:
        if not isinstance(r, dict):
            문제.append(f'{이름}: 칸 형식 오류'); continue
        id = r.get('칸ID') or '?'
        if id in 본:
            문제.append(f'{이름}: 칸ID 중복 {id}')
        본.add(id)
        if r.get('장소') not in 후보표['장소']:
            문제.append(f"{이름} {id}: 후보표에 없는 장소 {r.get('장소')}")
        for x in r.get('근거') or []:
            if x not in 근거들:
                문제.append(f'{이름} {id}: 없는 근거ID {x}')
        for x in r.get('운영') or []:
            if x not in 운영들:
                문제.append(f'{이름} {id}: 없는 운영주체 {x}')
        if 당일 and r.get('일차') == 2:
            문제.append(f'{이름} {id}: 당일 코스에 2일차')
        if r.get('일차') not in [1, 2]:
            문제.append(f'{이름} {id}: 일차 오류')
        if _가족인가(입력) and 술표현.search(str(r.get('이유') or '')):
            문제.append(f'{이름} {id}: 가족 코스에 술 표현')
    return 문제, 본


def 주문서_검사(주문서, 후보표, 입력, 한안=False):
    """틀린 곳을 고치지 않고 문제 문장으로 돌려준다. 빈 목록이면 통과."""
    if not isinstance(주문서, dict):
        return ['주문서 JSON을 읽지 못함']
    근거들 = {r['근거ID'] for r in 입력.get('근거목록') or []}
    운영들 = {x['O번호'] for x in 후보표.get('운영주체') or []}
    키 = '안' if 한안 else 'A'
    안 = 주문서.get(키)
    if not isinstance(안, dict) or not isinstance(안.get('칸'), list):
        return ['주문서에 안이 없음']
    문제, a칸 = _칸검사(키, 안['칸'], 후보표, 입력, 근거들, 운영들)
    if 한안:
        return 문제
    b = 주문서.get('B')
    if b is None:
        if not str(주문서.get('대안불가이유') or '').strip():
            문제.append('B: 대안불가이유 필요')
        return 문제
    if not isinstance(b, dict):
        return 문제 + ['B: 형식 오류']
    바꾼 = b.get('바꾼칸') or []
    b문제, _ = _칸검사('B', 바꾼, 후보표, 입력, 근거들, 운영들)
    문제 += b문제
    for id in [r.get('칸ID') for r in 바꾼 if isinstance(r, dict)] + list(b.get('뺀칸') or []):
        if id not in a칸:
            문제.append(f'B: A안에 없는 칸 {id}')
    return 문제
