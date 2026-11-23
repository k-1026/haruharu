"""기존 2단계 결과를 명시적으로 재정리한다. AI·원표 검증을 대신하지 않는다.

원래의 엄격한 전달 검사는 그대로 둔다. 이 함수는 알려진 축약 표에 한해
원문에 적힌 공통 설명을 각 행으로 옮긴다. 알 수 없는 형식은 예외로 중단한다.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

from 흐름 import 근거표_열, _칸, 경고_읽기, 전달_준비, 전달_검사


def _공통(문맥, 이름):
    m = re.search(rf'^\s*-?\s*{re.escape(이름)}:\s*(.+)$', 문맥, re.M)
    return m[1].strip() if m else ''


def _펼친행(머리, 행들, 문맥, 경고):
    출처 = _공통(문맥, '출처')
    if not 출처:
        m = re.search(r'KOSIS\s+2024|외래관광객조사\s+2025', 문맥)
        출처 = m[0] if m else ''
    if not 출처:
        raise ValueError('축약표의 공통 출처를 확인할 수 없음')
    연도 = _공통(문맥, '연도') or (re.search(r'20\d{2}', 출처)[0] if re.search(r'20\d{2}', 출처) else '')
    항목 = _공통(문맥, '항목') or re.sub(r'^\*\*', '', 문맥.strip()).split()[0]
    if 항목 not in ['방문객', '보조', '좋았던', '음식', '숙박']:
        raise ValueError('축약표의 공통 항목을 확인할 수 없음')
    if 항목 == '좋았던':
        항목 = '좋았던 점'
    묶음 = 머리[0] == '연도' and len(머리) == 2 and 머리[1].startswith('ID : 관광지')
    if not 묶음 and 머리 not in [
        ['ID', '구분 / 관광지', '수치', '파일', '경고'],
        ['ID', '항목명', '수치'], ['ID', '조건 · 항목', '수치'],
        ['ID', '원자료 항목명', '수치', '표본 · 한계', '경고'],
    ]:
        raise ValueError('지원하지 않는 축약표 머리: ' + str(머리))
    결과 = []
    for 칸 in 행들:
        if len(칸) != len(머리):
            raise ValueError('축약표의 행 길이가 머리와 다름')
        if 묶음:
            횟수 = re.search(r'(\d+)번', 칸[0]) or re.search(r'(\d+)번', 머리[1])
            if not 횟수:
                raise ValueError('관심 관광지 등장 횟수가 명시되지 않음')
            장소들 = re.findall(r'\b(R\d+)\s+(.+?)(?=\s*·\s*R\d+\b|$)', 칸[1])
            if not 장소들 or len(장소들) != len(re.findall(r'\bR\d+\b', 칸[1])):
                raise ValueError('관심 관광지 묶음을 분리할 수 없음')
            년 = re.match(r'20\d{2}', 칸[0])
            if not 년:
                raise ValueError('관심 관광지 연도가 없음')
            파일 = _공통(문맥, '파일 · 행 위치')
            if not 파일:
                raise ValueError('관심 관광지 공통 파일 없음')
            for rid, 장소 in 장소들:
                위치 = 파일.replace('[연도]', 년[0]).replace('관광지명', '관광지명=' + 장소)
                결과.append([rid, 항목, '관심 관광지 / ' + 장소,
                           횟수[1] + '번 (계산값: 원문 연도별 등장 횟수)', 위치, 출처, 년[0],
                           _공통(문맥, '표본 · 대상'), _공통(문맥, '한계'), ' '.join(경고.get(rid, [])) or '—'])
            continue
        행 = dict(zip(머리, 칸))
        rid, 이름 = 행['ID'], 칸[1]
        파일 = 행.get('파일')
        if not 파일:
            # 보조 절만 두 파일을 쓴다. 원문에 적힌 항목별 대응을 사용한다.
            if 항목 == '보조':
                분류 = 이름.split(' / ')[0]
                m = re.search(rf'{re.escape(분류)}:\s*(F\d+)\b', 문맥)
            else:
                m = re.search(r'\bF\d+\b', 문맥)
            파일 = m[1] if 항목 == '보조' and m else m[0] if m else ''
        if not 파일:
            raise ValueError(f'{rid}: 공통 파일 없음')
        # 행 번호를 꾸미지 않는다. 원문에 있는 항목으로 검색할 수 있는 위치를 남긴다.
        위치 = f'{파일} · 원문 항목={이름}'
        표본 = 행.get('표본 · 한계', '')
        if not 표본:
            # 공통 설명을 그대로 보존한다. 서로 다른 조건의 표본을 합산하지 않는다.
            표본 = ' '.join(l.strip(' -') for l in 문맥.splitlines() if 'n=' in l)
        한계 = _공통(문맥, '한계') or '공통 설명은 원문 절에 보존. 구·계절·국가 교차값으로 해석하지 않음'
        if '가중 계산값' in 문맥:
            한계 += ' · ' + ' '.join(l.strip(' -') for l in 문맥.splitlines() if '가중 계산값' in l or '계절 · 구' in l)
        수치 = 행['수치']
        if '가중 계산값' in 문맥:
            수치 += ' (가중 계산값: 원문 공통 설명)'
        결과.append([rid, 항목, 이름, 수치, 위치, 출처, 연도, 표본, 한계,
                   행.get('경고') or ' '.join(경고.get(rid, [])) or '—'])
    return 결과


def 근거_펼치기(글):
    """원문 공통 설명을 유지하고 축약 표만 10열로 펼친 Markdown을 반환한다."""
    연결 = {}
    for w in 경고_읽기(글):
        for rid in w['적용근거ID']:
            연결.setdefault(rid, []).append(w['경고ID'])
    줄들, 결과, 문맥 = 글.splitlines(), [], []
    영역, i = False, 0
    while i < len(줄들):
        줄 = 줄들[i]
        if 줄.startswith('## '):
            영역 = 줄.startswith(('## 근거표', '## 더 보기'))
            문맥 = []
        if 영역 and 줄.startswith('**') and 줄.endswith('**'):
            문맥 = []
        if not 영역 or not 줄.strip().startswith('|'):
            결과.append(줄)
            문맥.append(줄)
            i += 1
            continue
        원표 = []
        while i < len(줄들) and 줄들[i].strip().startswith('|'):
            원표.append(줄들[i])
            i += 1
        표 = [_칸(l) for l in 원표 if not all(set(c) <= set('-: ') for c in _칸(l))]
        머리 = 표[0]
        if 머리 == list(근거표_열) or 머리[0] == '약칭':
            결과.extend(원표)
            continue
        행들 = _펼친행(머리, 표[1:], '\n'.join(문맥), 연결)
        결과 += ['| ' + ' | '.join(근거표_열) + ' |', '|' + '---|' * 10]
        for 행 in 행들:
            결과.append('| ' + ' | '.join(str(c).replace('|', '／') for c in 행) + ' |')
    return '\n'.join(결과) + '\n'


def 재검사(원본폴더, 저장루트):
    """선택 기록을 재사용하고 새 실행 폴더에 저장한다. 원본에는 쓰지 않는다."""
    원본폴더, 저장루트 = Path(원본폴더), Path(저장루트)
    원문 = (원본폴더 / '2단계_결과.md').read_text(encoding='utf-8')
    선택1 = json.loads((원본폴더 / '1단계_선택.json').read_text(encoding='utf-8'))
    선택2 = json.loads((원본폴더 / '2단계_선택.json').read_text(encoding='utf-8'))
    이전 = json.loads((원본폴더 / '3단계_전달_준비.json').read_text(encoding='utf-8'))
    정리 = ('> 기존 2단계 결과의 표 형식만 재정리한 기록입니다. AI 재실행·원표 수치 검증은 하지 않았습니다.\n'
          '> 아래 본문의 담당자 미선택 표시는 생성 당시 기록입니다. 실제 E3 선택은 2단계_선택.json을 사용합니다.\n'
          '> 3단계 코스 조건은 아직 입력 전이며, 실제 3단계는 실행하지 않았습니다.\n\n'
          + 근거_펼치기(원문))
    전달 = 전달_준비(선택1['조건'], 선택2.get('확정체류기간', '미선택'),
                   선택2.get('담당자선택_E3', '미선택'), 정리, 이전.get('기관데이터', '기관 데이터: 없음'))
    전달['2단계결과_원문'] = 원문
    전달['검사결과'] = 전달_검사(전달) or ['통과']
    전달['재검사기록'] = {'원본폴더': str(원본폴더.resolve()),
        '원문SHA256': hashlib.sha256(원문.encode()).hexdigest(),
        '처리': '원문 공통 설명·묶음 표를 10열 행으로 펼침. 수치·경고 변경 없음. 원표 수치 검증 아님.',
        '코스조건': '아직 입력하지 않음. 다음 단계 초안 작성 전 담당자 입력 필요'}
    # 초 단위 충돌 시에도 기존 실행을 덮어쓰지 않는다.
    실행 = 저장루트 / datetime.now().strftime('%Y%m%d_%H%M%S')
    실행.mkdir(parents=True, exist_ok=False)
    새폴더 = 실행 / '01회차'
    새폴더.mkdir()
    for 이름 in ['1단계_결과.md', '1단계_선택.json', '2단계_선택.json']:
        shutil.copyfile(원본폴더 / 이름, 새폴더 / 이름)
    (새폴더 / '2단계_결과.md').write_text(정리, encoding='utf-8')
    (새폴더 / '3단계_전달_준비.json').write_text(json.dumps(전달, ensure_ascii=False, indent=2), encoding='utf-8')
    return 새폴더, 전달


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='기존 2단계 결과 재정리·전달 검사 (AI 호출 없음)')
    p.add_argument('원본폴더', type=Path)
    p.add_argument('--저장루트', type=Path, default=Path(__file__).parent / 'runs')
    a = p.parse_args()
    폴더, 전달 = 재검사(a.원본폴더, a.저장루트)
    print(json.dumps({'저장위치': str(폴더), '근거수': len(전달['근거목록']),
                      '경고수': len(전달['경고목록']), '검사결과': 전달['검사결과'],
                      '남은일': '담당자 코스조건 입력 후 3단계 초안 시험. 실제 AI는 호출하지 않았음'}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if 전달['검사결과'] == ['통과'] else 2)
