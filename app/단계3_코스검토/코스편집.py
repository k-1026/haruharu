"""담당자 수정 범위 검증·주문 합치기·실제 변경 비교. 특정 장소 예외 없음."""
from copy import deepcopy

작업목록 = {'요청', '교체', '제외', '추가', '순서', '체류시간', '식사'}


def 수정대상(코스):
    return [{'칸ID': r.get('칸ID'), '일차': r.get('일차'), '시간칸': r.get('시간칸'),
             '장소명': r.get('장소명', ''), '머무는분': r.get('머무는시간'),
             '수정가능': r.get('시간칸') != '숙박' and not str(r.get('장소명', '')).startswith('자유시간')}
            for r in 코스.get('칸목록') or []]


def 수정_검사(코스, 값):
    if not isinstance(값, dict):
        raise ValueError('수정 내용을 확인해 주세요.')
    요청 = 값.get('요청')
    if not isinstance(요청, str) or not 요청.strip() or len(요청) > 1000:
        raise ValueError('수정 요청을 1~1000자로 적어 주세요.')
    범위, 작업 = 값.get('범위', '일정'), 값.get('작업', '요청')
    if not isinstance(범위, str) or not isinstance(작업, str) or 범위 not in {'일정', '하루', '전체'} or 작업 not in 작업목록:
        raise ValueError('수정 범위와 작업을 다시 선택해 주세요.')
    대상 = 수정대상(코스)
    ids = [r['칸ID'] for r in 대상]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('일정 식별자가 없거나 중복돼 수정할 수 없습니다. 새 초안을 만들어 주세요.')
    가능 = [r for r in 대상 if r['수정가능']]
    if 범위 == '일정':
        선택 = 값.get('칸ID')
        if not isinstance(선택, list) or not 선택 or any(not isinstance(x, str) for x in 선택):
            raise ValueError('바꿀 개별 일정을 하나 이상 선택해 주세요.')
        if set(선택) - {r['칸ID'] for r in 가능}:
            raise ValueError('선택한 일정이 없거나 기본 숙박·자유시간 구간입니다. 최신 코스를 확인해 주세요.')
    elif 범위 == '하루':
        일차 = 값.get('일차')
        if type(일차) is not int or 일차 not in [r['일차'] for r in 가능]:
            raise ValueError('수정할 날짜를 선택해 주세요.')
        선택 = [r['칸ID'] for r in 가능 if r['일차'] == 일차]
    else:
        선택 = [r['칸ID'] for r in 가능]
    바꿀 = [r['칸ID'] for r in 가능 if r['칸ID'] in 선택]
    if not 바꿀:
        raise ValueError('수정 가능한 일정이 없습니다.')
    분 = 값.get('머무는분')
    if 작업 == '체류시간' and (type(분) is not int or not 5 <= 분 <= 480):
        raise ValueError('머무는 시간은 5~480분으로 입력해 주세요.')
    return {'범위': 범위, '일차': 값.get('일차'), '작업': 작업, '요청': 요청.strip(), '바꿀칸ID': 바꿀,
            '유지칸ID': [x for x in ids if x not in 바꿀],
            '허용일차': sorted({r['일차'] for r in 가능 if r['칸ID'] in 바꿀}),
            '머무는분': 분 if 작업 == '체류시간' else None,
            '대체장소': str(값.get('대체장소') or '')[:150],
            '재방문허용': 값.get('재방문허용') is True}


def 범위_합치기(새안, 이전안, 수정):
    """잠긴 방문은 복원. 선택 방문은 응답 순서로 채우며 신규 방문은 뒤칸ID로 삽입."""
    이전 = deepcopy(이전안.get('칸') or [])
    선택 = set(수정['바꿀칸ID'])
    옛 = {r['칸ID']: r for r in 이전}
    받은 = [deepcopy(r) for r in 새안.get('칸') or [] if r.get('칸ID') not in 옛 or r['칸ID'] in 선택]
    문제 = []
    for r in 받은:
        if r.get('일차') not in 수정['허용일차']:
            문제.append(f"수정 범위 밖 일차: {r.get('칸ID')}")
        if r.get('칸ID') in 옛 and r.get('일차') != 옛[r['칸ID']]['일차'] and 수정['범위'] != '전체':
            문제.append(f"선택한 일정을 다른 날로 이동할 수 없는 범위: {r['칸ID']}")
        기준 = r.get('뒤칸ID')
        if 기준 is not None and (기준 not in 선택 or 옛.get(기준, {}).get('일차') != r.get('일차')):
            문제.append('새 일정의 삽입 기준은 같은 날 선택한 방문이어야 합니다.')
    작업 = 수정['작업']
    if 작업 == '제외' and any(r.get('칸ID') in 선택 for r in 받은):
        문제.append('제외할 일정이 수정 결과에 남아 있습니다.')
    if 작업 == '제외' and 받은:
        문제.append('일정 제외 작업 중 새 방문을 추가할 수 없습니다.')
    if 작업 == '추가':
        # 추가는 기존 선택 방문까지 보존하며, 신규 방문만 응답에서 사용한다.
        신규 = [r for r in 받은 if r.get('칸ID') not in 옛]
        if not 신규:
            문제.append('추가된 일정이 없습니다.')
        받은 = [r for r in 이전 if r['칸ID'] in 선택] + 신규
    if 작업 in {'교체', '체류시간', '식사'} and not 선택.issubset({r.get('칸ID') for r in 받은}):
        문제.append('교체·시간·식사 수정에서는 선택한 일정의 칸ID를 유지해야 합니다.')
    if 작업 in {'교체', '체류시간', '식사', '순서'} and {r.get('칸ID') for r in 받은} != 선택:
        문제.append('선택한 방문만 바꿀 수 있습니다. 추가·제외는 해당 수정 방식을 선택해 주세요.')
    if 작업 == '순서':
        for r in 받은:
            if any(r.get(k) != 옛.get(r.get('칸ID'), {}).get(k) for k in ['장소', '머무는분', '시간칸']):
                문제.append('순서 수정 중 장소·머무는 시간·시간대가 변경됐습니다.')
    if 작업 == '체류시간':
        for r in 받은:
            if r.get('칸ID') in 선택:
                if r.get('장소') != 옛.get(r['칸ID'], {}).get('장소'):
                    문제.append('머무는 시간 수정 중 장소가 변경됐습니다.')
                r['머무는분'] = 수정['머무는분']
    if 문제:
        return None, 문제
    # 하루/전체는 응답의 순서를 그대로 사용한다. 개별은 선택 자리만 바꾸고 잠긴 방문의 순서를 보존한다.
    out = []
    if 수정['범위'] in {'하루', '전체'} and 작업 != '추가':
        for day in sorted({r['일차'] for r in 이전 + 받은}):
            if day in 수정['허용일차']:
                out.extend(r for r in 받은 if r['일차'] == day)
                out.extend(r for r in 이전 if r['일차'] == day and r['칸ID'] not in 선택)
            else:
                out.extend(r for r in 이전 if r['일차'] == day)
    else:
        for r in 이전:
            if r['칸ID'] not in 선택:
                out.append(r)
                continue
            # 개별 방문은 같은 날의 선택 자리를 응답 순서로 채운다.
            교체 = next((n for n in 받은 if n['일차'] == r['일차'] and n.get('칸ID') in 옛 and n not in out), None)
            if 교체:
                out.append(교체)
        for r in 받은:
            if r in out:
                continue
            기준 = r.pop('뒤칸ID', None)
            if 기준 is None:
                기준 = next((x['칸ID'] for x in reversed(이전) if x['칸ID'] in 선택 and x['일차'] == r['일차']), None)
            위치 = next((i+1 for i, x in enumerate(out) if x['칸ID'] == 기준 and x['일차'] == r['일차']), None)
            if 위치 is None:
                위치 = next((i for i, x in enumerate(out) if x['일차'] > r['일차']), len(out))
            # 같은 기준 뒤 신규 방문은 응답 순서를 유지한다.
            while 위치 < len(out) and out[위치].get('_삽입기준') == 기준:
                위치 += 1
            r['_삽입기준'] = 기준
            out.insert(위치, r)
    for r in out:
        r.pop('_삽입기준', None)
    있는 = {r['칸ID'] for r in out}
    유지 = set(옛) - 선택
    if 작업 == '추가':
        유지 = set(옛)
    식사 = [deepcopy(m) for m in 이전안.get('식사') or [] if m['칸ID'] in 유지 and m['칸ID'] in 있는]
    식사 += [deepcopy(m) for m in 새안.get('식사') or [] if m.get('칸ID') not in 유지 and m.get('칸ID') in 있는]
    # 교체되지 않은 식사는 AI가 생략해도 기존 기록을 이어 받는다.
    식사id = {m['칸ID'] for m in 식사}
    for m in 이전안.get('식사') or []:
        if m['칸ID'] in 있는 and m['칸ID'] not in 식사id:
            row = next(r for r in out if r['칸ID'] == m['칸ID'])
            식사.append({**deepcopy(m), '권역': row['장소'], '후보': m.get('후보', []) if row['장소'] == 옛[m['칸ID']]['장소'] else []})
    return {**새안, '칸': out, '식사': 식사}, []


def 변경_비교(이전, 새):
    옛 = {r['칸ID']: r for r in 이전.get('칸목록') or []}
    지금 = {r['칸ID']: r for r in 새.get('칸목록') or []}
    변경 = []
    label = lambda r: f"{r.get('일차')}일차 {r.get('장소명', '')}"
    for id, r in 옛.items():
        if id not in 지금:
            변경.append(f'제외: {label(r)}')
        else:
            n = 지금[id]
            if (r.get('장소명'), r.get('일차')) != (n.get('장소명'), n.get('일차')):
                변경.append(f'변경: {label(r)} → {label(n)}')
            if r.get('머무는시간') != n.get('머무는시간'):
                변경.append(f"머무는 시간: {label(n)} {r.get('머무는시간')} → {n.get('머무는시간')}분")
    변경 += [f'추가: {label(r)}' for id, r in 지금.items() if id not in 옛]
    공통 = set(옛) & set(지금)
    if [x for x in 옛 if x in 공통] != [x for x in 지금 if x in 공통]:
        변경.append('방문 순서를 변경했습니다.')
    def 식사(c):
        return {m['칸ID']: {k: m.get(k) for k in ['방식', '권역', '식당', '추천후보', '식비포함']} for m in c.get('식사목록') or []}
    if 식사(이전) != 식사(새):
        변경.append('식사 구성·후보를 변경했습니다.')
    return 변경
