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


미정 = {'값': '', '종류': '미정'}
기본시작 = '10:00'
오전구성값 = ['후보일정추가', '자유시간', '종료장소로바로']
운영방식값 = ['단체동행형', '개별이동형', '미정']


def _시각글(분):
    return f'{분 // 60 % 24:02d}:{분 % 60:02d}'


def _시각분(t):
    v = t.get('값') if isinstance(t, dict) else None
    if not isinstance(v, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v):
        return None
    h, m = map(int, v.split(':'))
    return h * 60 + m


def 이동찾기(후보표, a, b):
    """(분, 수단, 이동행) — 대중교통 우선, 없으면 도보. 없으면 None."""
    for x in 후보표['이동']:
        if x['출발'] == a and x['도착'] == b:
            if x['대중교통분']:
                return x['대중교통분'], '대중교통', x['행']
            if x['도보분']:
                return x['도보분'], '도보', x['행']
    return None


def 시각_계산(칸들, 후보표, 시작, 고정=None):
    """칸 순서대로 시각·종료시각을 붙인다. 이동 기록이 없으면 그 뒤는 미정(지어내지 않음)."""
    고정 = 고정 or {}
    out, 현재, 종류, 이전, 일차 = [], None, None, None, None
    for r in 칸들:
        r = dict(r)
        if r.get('일차') != 일차:
            일차 = r.get('일차')
            시작값 = 시작 if 일차 == 1 else {'값': 기본시작, '종류': '가정'}
            현재, 종류, 이전 = _시각분(시작값), 시작값.get('종류'), None
        elif 이전 is not None and 현재 is not None:
            이동 = 이동찾기(후보표, 이전, r.get('장소')) if r.get('장소') else None
            현재 = 현재 + 이동[0] if 이동 else None
            종류 = '가정'
        elif 이전 is None and 현재 is not None and out:
            현재 = None  # 앞 칸이 CSV 밖 장소면 이동 시간을 알 수 없다
        if r.get('칸ID') in 고정:
            g = 고정[r['칸ID']]
            r['시각'], r['종료시각'] = g.get('시각', dict(미정)), g.get('종료시각', dict(미정))
            현재, 종류 = _시각분(r['종료시각']), '가정'
        else:
            머무는 = r.get('머무는시간')
            r['시각'] = {'값': _시각글(현재), '종류': 종류} if 현재 is not None else dict(미정)
            if 현재 is not None and type(머무는) is int:
                현재 += 머무는
                r['종료시각'] = {'값': _시각글(현재), '종류': '가정'}
            else:
                현재, r['종료시각'] = None, dict(미정)
        이전 = r.get('장소')
        out.append(r)
    return out


def _운영주체(행, 주문값):
    csv값 = [x for x in re.split(r'[;,·\s]+', 행.get('운영주체후보') or '') if re.fullmatch(r'O\d+', x)]
    return csv값 or list(주문값 or [])


def _장소명(행):
    return ' '.join(x for x in ['대구광역시', 행.get('구', ''), _이름(행['장소명'])] if x)


def _담당자식사(입력, 일차, 시간칸):
    return next((m for m in (입력.get('코스작성조건') or {}).get('식사목록') or []
                 if m.get('일차') == 일차 and m.get('시간칸') == 시간칸), {})


def _시작(입력):
    t = (입력.get('코스작성조건') or {}).get('시작시각')
    return {'값': t, '종류': '확정'} if _시각분({'값': t}) is not None else {'값': 기본시작, '종류': '가정'}


def _빈칸(id, 일차, 시간칸, 이름):
    return {'칸ID': id, '일차': 일차, '시간칸': 시간칸, '장소': None, '장소명': 이름,
            '머무는시간': None, '근거ID': [], '운영주체후보': []}


def _고정칸추가(행들, 입력):
    """CSV에 없는 칸(숙박·2일차 오전 자유시간)은 코드가 정해진 문장으로 넣는다."""
    if 입력.get('확정체류기간') != '1박2일':
        return 행들
    구 = '·'.join((입력.get('조건') or {}).get('지역') or []) or '대구'
    첫날 = [r for r in 행들 if r.get('일차') == 1]
    둘째 = [r for r in 행들 if r.get('일차') == 2]
    숙박 = [_빈칸('숙박-1', 1, '숙박', f'숙소 ({구} 도심, 업체 미고정)')]
    if (입력.get('코스작성조건') or {}).get('2일차오전구성') == '자유시간':
        둘째 = [_빈칸('2일차오전-1', 2, '2일차오전', '자유시간 (담당자 선택)')] + 둘째
    return 첫날 + 숙박 + 둘째


def _식사행(m, 행들, 위치, 후보표, 입력, 안이름):
    i = 위치[m['칸ID']]
    r, 다음 = 행들[i], (행들[i + 1] if i + 1 < len(행들) else None)
    담당 = _담당자식사(입력, r['일차'], r['시간칸'])
    방식 = 담당.get('방식') if 담당.get('방식') not in [None, '', '미선택'] else m.get('방식', '미선택')
    이동 = 이동찾기(후보표, r.get('장소'), 다음.get('장소')) if 다음 and r.get('장소') and 다음.get('장소') else None
    if 이동:
        분, 수단, 행 = 이동
        적용 = (f"{_이름(r['장소명'])} → {_이름(다음['장소명'])} {수단} {분}분 ({행.get('도구', '')}, "
              f"{행.get('기준요일', '')} {행.get('기준출발시각', '')} 조회, {행.get('확인일', '')}). "
              f"{_이름(r['장소명'])} 이용 시 참고값")
    else:
        분, 적용 = None, '이동 시간 미확인'
    return {'칸ID': r['칸ID'], '안': 안이름, '방식': 방식, '시각': r['시각'],
            '권역': f"자유식 · {r['장소명']} 권역" if 방식 == '자유식' else r['장소명'],
            '식당': r['장소명'] if 방식 == '지정식' else '',
            '추천후보': [_장소명(후보표['장소'][p]) for p in m.get('후보') or [] if p in 후보표['장소']],
            '식비포함': 담당.get('식비포함') if 담당.get('식비포함') in ['포함', '불포함', '미정'] else '미정',
            '이동시간': {'분': 분, '적용조건': 적용}, '이후연결': 다음['장소명'] if 다음 else ''}


def 안_조립(안, 후보표, 입력, 안이름='공통', 고정=None):
    """주문서 한 안 → 칸목록·식사목록·시작종료·확정조건. 사실 값은 후보표에서만 가져온다."""
    조건 = 입력.get('코스작성조건') or {}
    체류 = 입력.get('확정체류기간')
    행들 = []
    for r in 안.get('칸') or []:
        p = 후보표['장소'][r['장소']]
        행들.append({'칸ID': r['칸ID'], '일차': r['일차'], '시간칸': r['시간칸'], '장소': r['장소'],
                   '장소명': _장소명(p), '머무는시간': r.get('머무는분'), '근거ID': list(r.get('근거') or []),
                   '운영주체후보': _운영주체(p, r.get('운영')), '이유': r.get('이유', '')})
    행들 = 시각_계산(_고정칸추가(행들, 입력), 후보표, _시작(입력), 고정)
    칸목록 = [{'칸ID': r['칸ID'], '일차': r['일차'], '시간칸': r['시간칸'], '안': 안이름, '장소명': r['장소명'],
             '시각': r['시각'], '머무는시간': r.get('머무는시간'), '근거ID': r.get('근거ID') or [],
             '운영주체후보': r.get('운영주체후보') or [], '종료일차': r['일차'], '종료시각': r['종료시각']}
            for r in 행들]
    위치 = {r['칸ID']: i for i, r in enumerate(행들)}
    식사목록 = [_식사행(m, 행들, 위치, 후보표, 입력, 안이름) for m in 안.get('식사') or [] if m.get('칸ID') in 위치]
    시작종료 = {k: 조건.get(k, '미확인') for k in ['시작지점', '시작시각', '종료지점', '종료시각', '시작일차', '종료일차']}
    오전 = 조건.get('2일차오전구성', '미선택') if 체류 == '1박2일' else '해당없음'
    out = {'칸목록': 칸목록, '식사목록': 식사목록, '코스시작종료': 시작종료,
           '확정조건': {'시작종료확정': all(시작종료.get(k) not in [None, '', '미확인', '미정']
                                       for k in ['시작지점', '시작시각', '종료지점', '종료시각']),
                    '겹침처리': False, '2일차오전선택': 체류 != '1박2일' or 오전 in 오전구성값},
           '운영방식': 조건.get('운영방식') if 조건.get('운영방식') in 운영방식값 else '미정',
           '2일차오전구성': 오전, '담당자결정': [],
           '장소이유': {r['칸ID']: r['이유'] for r in 행들 if r.get('이유')},
           '_장소번호': {r['칸ID']: r['장소'] for r in 행들 if r.get('장소')}}
    for k in ['희망반영', '대안설명']:
        if 안.get(k):
            out[k] = 안[k]
    return out


기존상품파일 = 저장소 / '지침/3_코스검토/9_기존_상품_목록.md'
이동상한분 = 30  # 2_입력.md 5장 (가정)
노선겹침기준 = 3  # 8_기존_상품_겹침.md 1장 (임시 기준)


def _표행(글, 제목):
    """`## n. 제목` 아래 첫 표의 데이터 행(머리·구분선 제외)."""
    out, 안쪽 = [], False
    for 줄 in 글.splitlines():
        if 줄.startswith('## '):
            안쪽 = 제목 in 줄
            continue
        if 안쪽 and 줄.startswith('|') and not re.fullmatch(r'[|\s:-]+', 줄):
            out.append([x.strip() for x in 줄.strip().strip('|').split('|')])
    return out[1:]


def 기존상품_읽기(path=기존상품파일):
    글 = Path(path).read_text(encoding='utf-8')
    별칭 = {}
    for 행 in _표행(글, '같은 장소로 보는 이름'):
        for 표기 in re.split(r',\s*', re.sub(r'\s*\(\d{4}-.*$', '', 행[1])):
            표기 = re.sub(r'\s*\([^)]*출발점\)', '', 표기).strip()
            if 표기:
                별칭[표기] = 행[0]
    경유 = {}
    for 행 in _표행(글, '상품별 경유 장소'):
        이름들 = re.split(r',|/', re.sub(r'`[^`]*`', '', 행[1]))
        경유[행[0]] = [_대표(이름.strip(' …'), 별칭) for 이름 in 이름들 if 이름.strip(' …')]
    return {'경유': 경유, '별칭': 별칭}


def _대표(이름, 별칭):
    이름 = re.sub(r'^\d코스:\s*', '', 이름.strip())
    return _이름(별칭.get(이름, 이름))


def _분범위(운영시간):
    m = re.search(r'(\d{1,2}:\d{2})\s*[-~–]\s*(\d{1,2}:\d{2})', 운영시간 or '')
    if not m:
        return None
    a, b = (_시각분({'값': x.zfill(5)}) for x in m.groups())
    return (a, b) if a is not None and b is not None else None


def _운영충돌(행, 칸행):
    """운영시간 표기가 있고 도착 시각이 그 밖이면 True. 표기·시각이 없으면 판단하지 않는다(None)."""
    if _매일휴무(행):
        return True
    범위, 시각 = _분범위(행.get('운영시간')), _시각분(칸행.get('시각'))
    if 범위 is None or 시각 is None:
        return None
    return not (범위[0] <= 시각 < 범위[1])


def _겹침(코스장소, 상품):
    이력, 노선 = [], []
    for 이름, 칸id in 코스장소:
        ids = [g for g, 경유 in 상품['경유'].items() if 이름 in 경유]
        if ids:
            이력.append({'장소': 이름, '칸ID': 칸id, '상품ID': ' · '.join(ids), '종류': '장소 겹침',
                       '선택': '미선택', '메모': '같은 장소를 지나는 기존 상품이 있음. 담당자가 피하기 / 연결하기 / 그대로 두기 중 선택'})
    for g, 경유 in 상품['경유'].items():
        연속 = 0
        for i, (이름, 칸id) in enumerate(코스장소):
            연속 = 연속 + 1 if 이름 in 경유 else 0
            if 연속 == 노선겹침기준:
                묶음 = [n for n, _ in 코스장소[i - 연속 + 1:i + 1]]
                노선.append({'장소': ' → '.join(묶음), '칸ID': 칸id, '상품ID': g, '종류': '노선 겹침', '선택': '미선택',
                           '메모': f'연속 {노선겹침기준}곳이 기존 상품 {g} 경유지와 같음(임시 기준). 선택 전에는 코스 확정 불가'})
    return 이력 + 노선


def _체크(안이름, 번호, 결과, 메모):
    return {'안': 안이름, 'C번호': 번호, '결과': 결과, '메모': 메모}


def _체크리스트(코스, 후보표, 입력, 안이름, 번호들, 이동결과, 저녁충돌):
    행들 = {id: 후보표['장소'][p] for id, p in 번호들.items()}
    칸들 = {r['칸ID']: r for r in 코스['칸목록']}
    치킨 = [id for id, r in 행들.items() if 치킨장소인가(r['장소명'])]
    치킨선택 = (입력.get('코스작성조건') or {}).get('치킨선택') == '선택'
    치킨문제 = (치킨 and not 치킨선택) or len(치킨) > 1 or any(칸들[id]['시간칸'] != '저녁' for id in 치킨)
    지역 = set((입력.get('조건') or {}).get('지역') or [])
    구밖 = [r['장소명'] for r in 행들.values() if 지역 and r.get('구') not in 지역]
    관광 = [r['장소명'] for r in 행들.values() if re.search('관광지|해설', r.get('장소유형') or '')]
    노선 = [x for x in 코스['겹침이력'] if x['종류'] == '노선 겹침']
    return [
        _체크(안이름, 'C1', '재확인 필요', f"관광지·해설 유형 {len(관광)}곳. 대표 관광지 범위는 팀 확정 전"),
        _체크(안이름, 'C2', '통과 못 함' if 치킨문제 else '통과', f"치킨 식사 {len(치킨)}곳 (담당자 치킨 선택: {'예' if 치킨선택 else '아니오'})"),
        _체크(안이름, 'C3', '재확인 필요', '같은 음식 단위는 팀 확정 전'),
        _체크(안이름, 'C4', 이동결과[0], 이동결과[1]),
        _체크(안이름, 'C5', 저녁충돌[0], 저녁충돌[1]),
        _체크(안이름, 'C6', '통과 못 함' if 노선 else '통과', '노선 겹침 미선택: ' + ', '.join(x['상품ID'] for x in 노선) if 노선 else '노선 겹침 없음'),
        _체크(안이름, 'C7', '통과' if 코스['확정조건']['시작종료확정'] else '확인 불가', '시작·종료는 담당자 입력값만 씀'),
        _체크(안이름, 'C8', '통과 못 함' if 구밖 else '통과', '고른 구 밖: ' + ', '.join(구밖) if 구밖 else '모든 장소가 고른 구 안'),
        _체크(안이름, 'C9', '통과', '운영 주체 후보 또는 "운영 주체 미확인" 표시'),
        _체크(안이름, 'C10', '통과', '시각은 확정/가정/미정, 운영정보는 확인/미확인으로 코드가 표시')]


def 파생_채우기(코스, 후보표, 입력, 안이름='공통'):
    """남은경고·미확인사항·장소별근거·겹침이력·체크리스트·대체후보. 코스 칸은 바꾸지 않는다."""
    코스 = dict(코스)
    번호들 = dict(코스.get('_장소번호') or {})
    근거 = {r['근거ID']: r for r in 입력.get('근거목록') or []}
    운영설명 = {x['O번호']: x['설명'] for x in 후보표.get('운영주체') or []}
    칸목록 = [dict(r) for r in 코스['칸목록']]
    칸들 = {r['칸ID']: r for r in 칸목록}
    # 남은 경고: 2단계 경고는 빠짐없이 이어받는다
    경고 = []
    for w in 입력.get('경고목록') or []:
        적용 = [r['칸ID'] for r in 칸목록 if set(r['근거ID']) & set(w.get('적용근거ID') or [])]
        경고.append({**w, '코스적용': ' · '.join(적용) if 적용 else '코스 장소에는 안 붙음'})
    for r in 칸목록:
        자유 = r['시간칸'] == '2일차오전' and r['장소명'].startswith('자유시간')
        if not r['근거ID'] and r['시간칸'] not in ['점심', '저녁', '숙박'] and not 자유:
            경고.append({'경고ID': f"N-{r['칸ID']}", '안': 안이름, '칸ID': r['칸ID'], '종류': '근거 없음',
                       '문구': f"{r['장소명']}: 이 칸을 뒷받침하는 수요 근거 없음 (근거 없음)", '코스적용': r['칸ID']})
    # 미확인 사항
    미확인 = []
    def 남김(종류, id, 내용):
        미확인.append({'종류': 종류, '안': 안이름, '대상 칸ID': id, '내용': 내용})
    if 칸목록 and 칸목록[0]['시각'].get('종류') == '가정':
        남김('가정값', 칸목록[0]['칸ID'], f"시작 시각 {칸목록[0]['시각']['값']}은 기본값 가정. 담당자 시작 시각이 정해지면 다시 계산")
    for r in 칸목록:
        if r['시각'].get('종류') == '미정':
            남김('미정 시각', r['칸ID'], f"{r['장소명']}: 앞 칸에서 오는 이동 시간 기록이 없어 시각 미정")
    for id, p in 번호들.items():
        if 후보표['장소'][p].get('상태') != '확인':
            남김('운영정보 미확인', id, f"{칸들[id]['장소명']}: 운영 정보 상태 '{후보표['장소'][p].get('상태') or '없음'}'. 판매 전 공식 확인 필요")
    for 이름 in 후보표.get('이름대응불명확') or []:
        for id, p in 번호들.items():
            if _이름(후보표['장소'][p]['장소명']) == 이름:
                남김('이름 대응 불명확', id, f"'{이름}'과 같은 이름의 장소가 여럿이라 이동 시간을 맞추지 않음")
                break
    # 이동 판정 (C4)
    순서 = [r for r in 칸목록 if r['칸ID'] in 번호들]
    초과, 없음 = [], []
    for a, b in zip(순서, 순서[1:]):
        if a['일차'] != b['일차']:
            continue
        이동 = 이동찾기(후보표, 번호들[a['칸ID']], 번호들[b['칸ID']])
        if 이동 is None:
            없음.append(f"{a['칸ID']}→{b['칸ID']}")
            남김('이동 시간 미확인', b['칸ID'], f"{a['장소명']} → {b['장소명']} 이동 기록 없음")
        elif 이동[0] > 이동상한분:
            초과.append(b['칸ID'])
    이동결과 = (('확인 불가', '이동 시간 미확인: ' + ', '.join(없음)) if 없음 else
             ('경고', f'{이동상한분}분 초과: ' + ', '.join(초과)) if 초과 else ('통과', f'모든 구간 {이동상한분}분 이내'))
    # 운영 충돌과 대체후보 (자동으로 바꾸지 않음)
    저녁 = []
    for r in 칸목록:
        p = 번호들.get(r['칸ID'])
        if not p:
            continue
        충돌 = _운영충돌(후보표['장소'][p], r)
        if r['시간칸'] == '저녁':
            저녁.append(충돌)
        if 충돌:
            코스칸 = 후보표['장소'][p].get('코스칸')
            쓴 = set(번호들.values())
            r['대체후보'] = [_장소명(x) for k, x in 후보표['장소'].items() if k not in 쓴 and x.get('코스칸') == 코스칸]
            남김('운영 충돌', r['칸ID'], f"{r['장소명']}: 운영시간 '{후보표['장소'][p].get('운영시간')}' 밖이거나 매일 휴무. 대체후보는 담당자 선택")
    저녁충돌 = (('확인 불가', '저녁 칸 없음') if not 저녁 else ('통과 못 함', '저녁 도착이 운영시간 밖') if any(저녁)
             else ('확인 불가', '저녁 시각 또는 운영시간 미확인') if None in 저녁 else ('통과', '저녁 도착 시각이 운영시간 안'))
    # 장소별 근거
    장소근거 = []
    for id, p in 번호들.items():
        r, 행 = 칸들[id], 후보표['장소'][p]
        ids = r['근거ID']
        장소근거.append({'장소': r['장소명'], '칸ID': id, '안': 안이름,
                     '넣은이유': f"{(코스.get('장소이유') or {}).get(id, '')} ({' · '.join(ids) or '근거 없음'})",
                     '근거수치': ' · '.join(f"{x} {근거[x].get('수치_원문', '')} ({근거[x].get('표본_대상', '')})" for x in ids if x in 근거) or '없음',
                     '운영정보': '확인' if 행.get('상태') == '확인' else '미확인',
                     '운영주체후보': ' · '.join(f"{o} {운영설명.get(o, '')}" for o in r['운영주체후보']) or '운영 주체 미확인',
                     '이어받은경고': [w['경고ID'] for w in 경고 if id in str(w.get('코스적용'))]})
    코스장소 = [(_이름(후보표['장소'][번호들[r['칸ID']]]['장소명']), r['칸ID']) for r in 순서]
    코스.update({'칸목록': 칸목록, '남은경고': 경고, '미확인사항': 미확인, '장소별근거': 장소근거,
               '겹침이력': [{**x, '안': 안이름} for x in _겹침(코스장소, 기존상품_읽기())],
               '장소스토리': [], '대체이력': []})
    코스['확정조건'] = {**코스['확정조건'], '겹침처리': not any(x['종류'] == '노선 겹침' for x in 코스['겹침이력'])}
    코스['체크리스트'] = _체크리스트(코스, 후보표, 입력, 안이름, 번호들, 이동결과, 저녁충돌)
    return 코스


def 이전_주문서(이전코스, 후보표):
    """완성 코스 → 주문서 모양(P번호). 고쳐 쓰기·부분수정 입력용. CSV 밖 칸(숙박·자유시간)은 코드가 다시 넣으므로 뺀다."""
    번호 = {}
    for k, r in 후보표['장소'].items():
        번호.setdefault(_이름(r['장소명']), []).append(k)
    def p(이름):
        ks = 번호.get(_이름(이름 or ''))
        return ks[0] if ks and len(ks) == 1 else None
    칸들 = []
    for r in 이전코스.get('칸목록') or []:
        if p(r.get('장소명')):
            칸들.append({'칸ID': r['칸ID'], '일차': r['일차'], '시간칸': r['시간칸'], '장소': p(r['장소명']),
                       '머무는분': r.get('머무는시간'), '근거': list(r.get('근거ID') or []),
                       '운영': list(r.get('운영주체후보') or []), '이유': ''})
    있는 = {r['칸ID'] for r in 칸들}
    식사 = [{'칸ID': m['칸ID'], '방식': m.get('방식', '미선택'), '권역': next(r['장소'] for r in 칸들 if r['칸ID'] == m['칸ID']),
           '후보': [x for x in (p(n) for n in m.get('추천후보') or []) if x]}
          for m in 이전코스.get('식사목록') or [] if m.get('칸ID') in 있는]
    return {'칸': 칸들, '식사': 식사}


def _유지합치기(새안, 이전안, 유지시간칸):
    """유지할 시간칸은 이전 주문 그대로, 나머지 자리는 새 주문으로. 순서는 이전 코스 순서."""
    새칸 = list(새안.get('칸') or [])
    out, 쓴 = [], set()
    for r in 이전안['칸']:
        if r['시간칸'] in 유지시간칸:
            out.append(r)
            continue
        키 = (r['일차'], r['시간칸'])
        if 키 not in 쓴:
            out += [n for n in 새칸 if (n.get('일차'), n.get('시간칸')) == 키]
            쓴.add(키)
    out += [n for n in 새칸 if n not in out]
    유지id = {r['칸ID'] for r in out if r['시간칸'] in 유지시간칸}
    식사 = [m for m in 이전안['식사'] if m['칸ID'] in 유지id] + [m for m in 새안.get('식사') or [] if m.get('칸ID') not in 유지id]
    return {**새안, '칸': out, '식사': 식사}


def _B주문(a, b):
    바꾼 = {r['칸ID']: r for r in b.get('바꾼칸') or []}
    뺀 = set(b.get('뺀칸') or [])
    칸들 = [바꾼.get(r['칸ID'], r) for r in a['칸'] if r['칸ID'] not in 뺀]
    식사 = []
    for m in a.get('식사') or []:
        if m['칸ID'] in 뺀:
            continue
        식사.append({**m, '권역': 바꾼[m['칸ID']]['장소'], '후보': []} if m['칸ID'] in 바꾼 else m)
    return {'칸': 칸들, '식사': 식사}


def _완성(안, 후보표, 입력, 고정=None):
    코스 = 파생_채우기(안_조립(안, 후보표, 입력, '공통', 고정), 후보표, 입력)
    for k in ['_장소번호', '장소이유']:
        코스.pop(k, None)
    return 코스


def 조립(주문서, 후보표, 입력, 이전코스=None, 유지시간칸=None):
    """주문서 → (완성 코스, 문제목록). 문제가 있으면 (None, 문제): 추측해서 고치지 않는다."""
    한안 = isinstance(주문서, dict) and '안' in 주문서
    문제 = 주문서_검사(주문서, 후보표, 입력, 한안)
    if 문제:
        return None, 문제
    안 = 주문서['안' if 한안 else 'A']
    고정 = None
    if 유지시간칸 and 이전코스:
        안 = _유지합치기(안, 이전_주문서(이전코스, 후보표), set(유지시간칸))
        고정 = {r['칸ID']: r for r in 이전코스.get('칸목록') or [] if r.get('시간칸') in 유지시간칸}
    코스 = _완성(안, 후보표, 입력, 고정)
    if 한안:
        return 코스, []
    b = 주문서.get('B')
    if b is None:
        코스['대안제안'] = None
        코스['대안불가이유'] = 주문서.get('대안불가이유', '')
    else:
        코스['대안제안'] = {'이유': b.get('이유', ''), '무엇을': b.get('무엇을', ''), '바꾼희망': b.get('바꾼희망') or {},
                        '코스': _완성(_B주문(안, b), 후보표, 입력)}
    return 코스, []
