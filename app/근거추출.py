"""지침의 조건으로 CSV 행을 고르고 근거표를 만든다. AI·원본 수정 없음.

기준: 1_기획조건/자료_고르기, 2_수요근거/근거표·경고.
선택행에는 CSV 헤더를 1행으로 센 위치와 원래 값을 그대로 보존한다.
"""
from collections import defaultdict
import csv
import copy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from 흐름 import 계절_월, 조건_문장

자료루트 = Path(__file__).resolve().parent.parent / 'research/data'
관심파일 = '외국인/관광데이터랩_대구광역시_외국인관심관광지_월별통합_202201-202609.csv'
계절파일 = '외국인/관광데이터랩_대구광역시중구동구_외국인방문자수_계절합계_2022-2026.csv'
국가파일 = '외국인/관광데이터랩_대구광역시중구동구_외국인방문자국가비율_2022-2026.csv'
숙박파일 = '외국인/외래관광객조사_대구방문외국인_국적별숙박여부_2025.csv'
언어대응 = {'일본어': ('일본어', ['일본'], '일본'), '영어권': ('영어권', ['미국'], '미주'),
          '중국어 간체': ('중간체', ['중국'], '중국'), '중국어 번체': ('중번체', ['대만', '홍콩'], '대만')}
조사시기 = {'봄': '4~5월(1기)', '여름': '6~8월(2기)', '가을': '9~10월(3기)', '겨울': '11~12월(4기)'}
코시스 = [('숙박기간', '숙박'), ('가장좋았던점', '좋았던 점'), ('방문관광지', '방문객'),
         ('추천관광지상위10', '방문객'), ('추천음식상위20', '음식'), ('숙박유형', '숙박'), ('숙박선택이유', '숙박')]
열 = ['ID', '항목', '원자료 항목명', '수치', '파일 · 행 위치', '출처', '연도', '표본 · 대상', '한계', '경고']


def _숫자(v):
    try:
        n = Decimal(str(v).replace(',', ''))
        return n if n.is_finite() else None
    except InvalidOperation:
        return None


def 추출(조건, root=None):
    root = Path(root) if root is not None else 자료루트
    월 = 계절_월[조건['계절']]
    언어 = [언어대응[x][0] for x in 조건['언어권']]
    국가 = {n for x in 조건['언어권'] for n in 언어대응[x][1]}
    코시스국가 = {언어대응[x][2] for x in 조건['언어권']}
    지역 = 조건['지역']
    r = {'조건': dict(조건), '선택행': [], '근거': [], '경고': [], '미확인': [], '선택파일': []}
    경고별 = defaultdict(list)
    변동 = defaultdict(list)

    def 읽기(file, predicate):
        try:
            with (root / file).open(encoding='utf-8-sig', newline='') as f:
                rows = [{'파일': file, '행': i, '값': row} for i, row in enumerate(csv.DictReader(f), 2) if predicate(row)]
        except (OSError, UnicodeError, csv.Error) as error:
            r['미확인'].append(f'자료 없음 또는 읽기 실패: {file} ({type(error).__name__})')
            return []
        r['선택파일'].append({'파일': file, '선택행수': len(rows)})
        if not rows:
            r['미확인'].append(f'조건에 맞는 행 없음: {file}')
        r['선택행'].extend(rows)
        return rows

    def 근거(row, 항목, 이름, 값, 단위, 출처, 연도, 표본, 한계, 경고문구=(), 위치=None, 시계열=None):
        n = _숫자(값)
        if n is None:
            r['미확인'].append(f"값 미확인: {row['파일']} 행 {row['행']} · {이름} / {한계}")
            return
        id = f"R{len(r['근거']) + 1:02d}"
        r['근거'].append(dict(zip(열, [id, 항목, 이름, f'{값}{단위}',
            위치 or f"{row['파일']} 행 {row['행']}", 출처, str(연도), 표본, 한계, '없음'])))
        for kind, text in 경고문구:
            경고별[(kind, text)].append(id)
        if 시계열 is not None:
            변동[시계열].append((id, str(연도), n))

    # KOSIS는 조건별 주변값이다. 계절×국가×숙박의 교차 통계로 합치지 않는다.
    for 이름, 항목 in 코시스:
        if 조건['체류기간'] == '당일' and 이름 in ['숙박유형', '숙박선택이유']:
            continue
        file = f'외국인/대구_외국인{이름}_2024.csv'
        def 맞음(v):
            c, s = v.get('category'), v.get('subgroup')
            return ((c == '전체' and s == '소계') or (c == '거주국가' and s in 코시스국가) or
                    (c == '조사시기' and (s == 조사시기[조건['계절']] or
                     (조건['체류기간'] == '추천받기' and 이름 == '숙박기간'))) or
                    (c == '대구 체류 여부' and s in (['당일여행', '숙박여행'] if 조건['체류기간'] == '추천받기' else
                     ['당일여행' if 조건['체류기간'] == '당일' else '숙박여행'])))
        for row in 읽기(file, 맞음):
            v = row['값']
            if v.get('band') and v['band'] not in ['1 + 2순위', '1+2순위', '단위: 박']:
                continue
            limit = '대구 전체, 구 구분 없음. 각 조건을 따로 나눈 값이며 계절×국가 교차값이 아님.'
            warnings = [('간접 근거', limit)]
            if v['category'] == '거주국가':
                warnings.append(('간접 근거', '언어권을 거주국가로 대신 잼. 영어권은 미주, 번체는 대만이며 홍콩은 없음.'))
            if v['category'] == '조사시기' and 조건['계절'] != '여름':
                warnings.append(('기간 다름', f"계절 기준과 조사시기가 다름: {조건['계절']} {월}월 / {v['subgroup']}"))
            sample = _숫자(v.get('sample_n'))
            if sample is not None and sample < 100:
                warnings.append(('표본 작음', f"응답자 {v['sample_n']}명. 100명 미만 기준은 시험값(팀 확정 전)."))
            근거(row, 항목, f"{v['category']} / {v['subgroup']} / {v['item']}" + (f" / {v['band']}" if v.get('band') else ''),
                v.get('value_pct'), '박' if v.get('band') == '단위: 박' else '%', 'KOSIS 대구관광실태조사', 2024,
                f"외국인 n={v.get('sample_n', '미확인')}", limit, warnings)

    for row in 읽기(계절파일, lambda v: v.get('지역') in 지역 and v.get('계절') == 조건['계절']):
        v = row['값']
        limit = '빅데이터 추정. 언어권·체류 기간 구분 없음. ' + v.get('상태', '') + '. ' + v.get('월별값', '') + '. ' + v.get('계산식', '')
        근거(row, '방문객', f"{v['지역']} {v['계절']} 외국인 방문자 수", v.get('계절합계_명'), '명', '관광데이터랩', v['연도'],
            v['지역'] + ' 외국인', limit, [('간접 근거', '방문자 수는 언어권·체류 기간 구분 없음.')], 시계열=('방문자 수', v['지역']))
    for row in 읽기(국가파일, lambda v: v.get('지역') in 지역 and v.get('국가명') in 국가):
        v = row['값']
        근거(row, '방문객', f"{v['지역']} / {v['국가명']} 거주 국가 비율", v.get('비율_퍼센트'), '%', '관광데이터랩', v['기간'],
            v['지역'] + ' 외국인', '계절·숙박 구분 없음. 국가 비율×방문자 수로 언어권별 수를 만들지 않음.',
            [('간접 근거', '국가 비율은 계절·숙박 구분 없음.')], 시계열=('국가 비율', v['지역'], v['국가명']))
    if '중구' in 지역:
        # 구별 국가 비율과 같은 집계의 중복 독립 근거로 세지 않는다. 선택 원본만 보존.
        읽기('datalab_jung_origin_country_2022_2026.csv', lambda v: v.get('country') in 국가)
        groups = defaultdict(list)
        for row in 읽기('datalab_jung_paid_attraction_foreign_monthly_2022_2026.csv',
                       lambda v: v.get('status') == '값' and v.get('year_month', '')[4:6].isdigit() and int(v['year_month'][4:6]) in 월):
            groups[row['값']['year_month'][:4]].append(row)
        for year, rows in sorted(groups.items()):
            months = {int(x['값']['year_month'][4:6]) for x in rows}
            if months != set(월):
                r['미확인'].append(f'향촌문화관 {year} {조건["계절"]} 일부 월만 있음: ' + ', '.join(f"{x['값']['year_month']} {x['값']['foreign_entrants']}명" for x in rows))
                continue
            values = [_숫자(x['값']['foreign_entrants']) for x in rows]
            if None in values:
                r['미확인'].append(f'향촌문화관 {year} 입장객 수치 미확인')
                continue
            limit = '향촌문화관 1곳, 중구 전체 수요 아님. 계산값: ' + ' + '.join(f"{x['값']['year_month']} {x['값']['foreign_entrants']}" for x in rows)
            근거(rows[0], '방문객', '향촌문화관 계절 입장객 합계', str(sum(values)), '명', '관광데이터랩', year, '향촌문화관 외국인 입장객', limit,
                [('간접 근거', '향촌문화관 1곳의 외국인 입장객으로 중구 전체 수요가 아님.')],
                위치=f"{rows[0]['파일']} 행 " + ','.join(str(x['행']) for x in rows), 시계열=('향촌문화관',))
    for row in 읽기(숙박파일, lambda v: v.get('국적') in 국가 | {'전체'}):
        v = row['값']; sample = _숫자(v.get('대구방문응답자수_명'))
        limit = '2025 출국조사, KOSIS 2024와 대상·연도 다름. 계절·구 구분 없음. ' + v.get('표본메모', '') + '. ' + v.get('계산식', '')
        warnings = [('간접 근거', '국적별 숙박 여부는 계절·구 구분 없음. KOSIS 2024와 합치지 않음.')]
        if sample is not None and sample < 100:
            warnings.append(('표본 작음', v.get('표본메모', '') + ' / 100명 미만 기준은 시험값(팀 확정 전).'))
        for name in ['대구숙박비율_가중_퍼센트', '대구당일비율_가중_퍼센트']:
            근거(row, '숙박', v['국적'] + ' / ' + name, v.get(name), '%', '한국관광공사 외래관광객조사', v['조사연도'],
                f"대구 방문 외국인 n={v.get('대구방문응답자수_명', '미확인')}", limit, warnings)
    for name, label in [('purpose', 'purpose'), ('companion', 'companion')]:
        for row in 읽기(f'kosis_foreign_{name}_2024.csv', lambda v: True):
            v = row['값']
            근거(row, '보조', v[label], v.get('pct'), '%', 'KOSIS 대구관광실태조사', 2024,
                f"외국인 n={v.get('sample_n', '미확인')}", '조건 구분 없음. ' + v.get('note', ''), [('간접 근거', '방문 목적·동반자는 전체 외국인 보조 자료.')])
    interests = defaultdict(list)
    for row in 읽기(관심파일, lambda v: v.get('지역') in 지역 and v.get('언어명') in 언어 and
                   v.get('기간', '')[4:6].isdigit() and int(v['기간'][4:6]) in 월):
        v = row['값']; interests[(v['지역'], v['기간'][:4], v['언어명'], v['관광지명'])].append(row)
    for (district, year, language, place), rows in sorted(interests.items()):
        근거(rows[0], '방문객', f'{district} / {language} / {place} 관심 목록 등장', str(len(rows)), '회', '관광데이터랩', year,
            '관심 관광지 월별 목록', f"{조건['계절']} 월별 목록 등장 횟수 합(계산값), 방문자 수가 아님. 원래 장소명 유지.",
            위치=f"{관심파일} 행 " + ','.join(str(x['행']) for x in rows))
    for key, values in 변동.items():
        ns = [v[2] for v in values]
        if len(ns) > 1 and max(ns) > 0 and max(ns) >= min(ns) * 2:
            경고별[('변동 큼', ' / '.join(key) + ': 연도별 값 2배 이상 변동. 기준은 시험값(팀 확정 전).')].extend(x[0] for x in values)
    for (kind, text), ids in 경고별.items():
        id = f"W{len(r['경고']) + 1}"
        r['경고'].append({'경고ID': id, '종류': kind, '문구': text, '적용근거ID': ids})
        for row in r['근거']:
            if row['ID'] in ids:
                row['경고'] = ('' if row['경고'] == '없음' else row['경고'] + ', ') + f'{kind} {id}'
    r['미확인'] = list(dict.fromkeys(r['미확인']))
    return r


def _셀(v):
    return str(v).replace('|', '／').replace('\n', ' ')


def 자료확인문서(r):
    lines = ['## 조건 요약', 조건_문장(r['조건']), '', '## 볼 수 있는 자료', '| 파일 | 선택 행 수 |', '|---|---|']
    lines += [f"| {x['파일']} | {x['선택행수']} |" for x in r['선택파일']]
    lines += ['', '## 알림 (E1)', '- [구분 없음] KOSIS·외래관광객조사는 구별 자료가 아닙니다.',
              '- [따로만 나뉨] KOSIS의 계절·거주국가는 따로 나뉜 자료이며 교차값이 아닙니다.',
              '- 기관 데이터로 채우면 좋은 곳: 선택 지역의 계절·언어권·숙박 교차 자료.', '',
              '## 2단계로 넘기는 것', '선택 행과 원래 위치는 근거_추출.json에 보존합니다. 수치는 2단계 근거표에서 다룹니다.']
    return '\n'.join(lines)


def 결과문서(r, 요약):
    # AI가 새 표·경고를 끼워 넣어 코드 근거를 덮어쓰지 못하게 제목 이후는 받지 않는다.
    요약 = re.split(r'^\s*#{1,6}\s', str(요약), maxsplit=1, flags=re.M)[0].strip()
    lines = ['## 수요 분석 요약', 요약 or 'AI 요약이 없어 코드가 고른 근거표를 확인해야 합니다.', '', '## 근거표',
             '| ' + ' | '.join(열) + ' |', '| ' + ' | '.join(['---'] * len(열)) + ' |']
    lines += ['| ' + ' | '.join(_셀(row[k]) for k in 열) + ' |' for row in r['근거']]
    lines += ['', '## 경고 (E3)']
    lines += [f"- [{w['경고ID']} {w['종류']}] {w['문구']} (적용 근거: {' · '.join(w['적용근거ID'])})" for w in r['경고']] or ['- 없음']
    lines += ['', '## 미확인사항'] + ['- ' + v for v in r['미확인']]
    lines += ['', '## 담당자 선택 (E3)', '- 미선택 (별도 자동 진행 동의 기록을 따름)']
    return '\n'.join(lines)


def 요약입력(r):
    # 전체 근거는 저장한다. AI에는 같은 세부구분의 대표값·닭 관련 행을 작은 표로 준다.
    groups = defaultdict(list)
    for row in r['근거']:
        file = row['파일 · 행 위치'].split(' 행 ')[0]
        if file == 관심파일:
            key = (file, row['연도'], *row['원자료 항목명'].split(' / ')[:2])
        else:
            key = (row['항목'], file, ' / '.join(row['원자료 항목명'].split(' / ')[:2]))
        groups[key].append(row)
    chosen = []
    for rows in groups.values():
        if rows[0]['파일 · 행 위치'].startswith(관심파일):
            rows = sorted(rows, key=lambda x: _숫자(x['수치'][:-1]), reverse=True)
        chosen += rows[:3] + [x for x in rows[3:] if '닭' in x['원자료 항목명'] or '치킨' in x['원자료 항목명']]
    ids = {x['ID'] for x in chosen}
    columns = ['ID', '항목', '원자료 항목명', '수치', '연도', '표본 · 대상']
    warnings = [{**w, '적용근거ID': [id for id in w['적용근거ID'] if id in ids]} for w in r['경고'] if ids.intersection(w['적용근거ID'])]
    return {'조건': r['조건'], '근거열': columns, '근거': [[row[k] for k in columns] for row in chosen],
            '전체근거행수': len(r['근거']), '경고': warnings, '미확인': r['미확인'],
            '주의': '요약용 일부 행. 전체 근거는 코드가 보존하며 표·수치·경고를 다시 작성하지 않는다. 연도별 자료의 대표 연도를 임의로 정하지 않는다.'}


def 전달입력_줄이기(입력):
    """저장된 전체 입력을 보존하며 AI 요청에서만 중복 원문·접힌 근거를 뺀다."""
    표시 = 입력.get('코드근거추출')
    if not 표시:
        return 입력
    out = copy.deepcopy(입력)
    ids = set(표시['AI전달근거ID'])
    out.pop('2단계결과_원문', None)
    out['근거목록'] = [r for r in out.get('근거목록', []) if r['근거ID'] in ids]
    warnings = []
    for w in out.get('경고목록', []):
        w['적용근거ID'] = [id for id in w['적용근거ID'] if id in ids]
        if w['적용근거ID']:
            warnings.append(w)
    out['경고목록'] = warnings
    out['근거전달설명'] = '전체 근거와 원문은 저장본에 보존했다. 이번 AI 요청의 근거목록에 있는 ID만 인용한다. 생략된 근거를 읽은 것으로 쓰지 않는다.'
    return out
