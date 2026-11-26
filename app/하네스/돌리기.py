"""하네스 실행: 시험 상황 하나로 3단계를 실제 AI로 N번 돌리고 점수표(JSON + md)를 남긴다.

사용:  python -m app.하네스.돌리기            (기본 1회)
       python -m app.하네스.돌리기 --반복 3
제품 동작은 바꾸지 않는다. /plan/ 화면과 같은 3단계 경로(관리자실행.코스시험 저장→시작)를 부르기만 한다.
"""
import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from app.공통.기획실행 import 빈_코스조건
from app.서버.관리자실행 import 코스시험
from app.서버.관리자조회 import 결과저장소
from app.하네스.채점 import 채점

여기 = Path(__file__).resolve().parent
상황폴더 = 여기 / '시험상황'
결과폴더 = 여기 / '결과'
기본상황 = '일본인커플_중구_가을_1박2일'


def _커밋():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, cwd=여기)
        해시 = r.stdout.strip() or '알수없음'
        바뀜 = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=여기).stdout.strip()
        return 해시 + (' (커밋 안 한 변경 있음)' if 바뀜 else '')
    except OSError:
        return '알수없음'


def 한번(상황, 작업루트, 실행함수=None):
    """작업루트 아래에 원본 실행 폴더를 흉내 내 만들고, 3단계만 한 번 돌려 채점한다."""
    키 = datetime.now().strftime('%Y%m%d_%H%M%S') + '/01회차'
    원본 = Path(작업루트) / 키
    원본.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(상황폴더 / 상황['고정입력'], 원본 / '3단계_전달_준비.json')
    시험 = 코스시험(결과저장소(작업루트), 실행함수)
    입력전달 = json.loads((원본 / '3단계_전달_준비.json').read_text(encoding='utf-8'))
    조건 = {**빈_코스조건(입력전달['확정체류기간']), **(상황.get('코스조건덮어쓰기') or {})}
    상태 = 시험.저장(키, 조건)
    시험.시작(상태['시험id'])
    작업 = 시험.작업들.get(상태['시험id'])
    if 작업:
        작업.join()
    폴더 = 시험._시험(상태['시험id'])
    입력 = json.loads((폴더 / '3단계_입력.json').read_text(encoding='utf-8'))
    점수 = 채점(폴더, 입력)
    점수['시험폴더'] = str(폴더)
    return 점수


def _이전점수표(결과폴더, 상황이름):
    """같은 시험 상황의 가장 최근 점수표. 다른 상황과는 비교하지 않는다."""
    for p in sorted(결과폴더.glob('점수표_*.json'), reverse=True):
        try:
            값 = json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            continue
        if 값.get('상황') == 상황이름:
            return 값
    return None


def 요약(회차들):
    """항목별로 '매번 지켰나'를 본다."""
    이름들 = list(dict.fromkeys(h['항목'] for r in 회차들 for h in r['항목']))
    항목 = {}
    for n in 이름들:
        결과 = [next((h['결과'] for h in r['항목'] if h['항목'] == n), '실패') for r in 회차들]
        항목[n] = f"{결과.count('통과')}/{len(결과)}"
    초 = [r['경과초'] for r in 회차들 if r['경과초'] is not None]
    return {'항목': 항목, '매번통과': all(r['전체통과'] for r in 회차들),
            '경과초_최대': max(초) if 초 else None, '경과초_평균': round(sum(초) / len(초), 1) if 초 else None}


def 비교문장(지금, 이전):
    if not 이전:
        return '이전 점수표 없음 (첫 기록)'
    a, b = 지금['요약'], 이전.get('요약') or {}
    바뀐 = [f"{k} {b['항목'].get(k, '-')}→{v}" for k, v in a['항목'].items() if (b.get('항목') or {}).get(k) != v]
    시간 = f"최대 {b.get('경과초_최대')}초→{a['경과초_최대']}초"
    return f"이전({이전.get('기록시각', '?')[:16]}) 대비: " + (', '.join(바뀐) if 바뀐 else '항목 결과 같음') + f" · {시간}"


def md표(점수표):
    줄 = [f"# 하네스 점수표 — {점수표['기록시각'][:19]}", '',
         f"- 조건: {점수표['조건']}", f"- 커밋: {점수표['커밋']}", f"- 반복: {len(점수표['회차'])}회",
         f"- 비교: {점수표['비교']}",
         f"- 결과: {'매번 모두 통과' if 점수표['요약']['매번통과'] else '실패 항목 있음'}", '',
         '| 항목 | 통과 횟수 |', '|---|---|']
    줄 += [f'| {k} | {v} |' for k, v in 점수표['요약']['항목'].items()]
    for i, r in enumerate(점수표['회차'], 1):
        줄 += ['', f"## {i}회차 — 상태 {r['상태']} · {r['경과초']}초 · 받은 {r['받은글자']}자 / 쓴 {r['쓴글자']}자 "
               f"(목표 받은 {r['목표글자']['받은글자']} · 쓴 {r['목표글자']['쓴글자']})", '',
               '| 항목 | 결과 | 메모 |', '|---|---|---|']
        줄 += [f"| {h['항목']} | {h['결과']} | {str(h['메모']).replace('|', '/')} |" for h in r['항목']]
        if r.get('오류'):
            줄 += ['', '오류 기록(AI_오류.json):', '```json', json.dumps(r['오류'], ensure_ascii=False, indent=2)[:3000], '```']
    return '\n'.join(줄) + '\n'


def 돌리기(상황이름=기본상황, 반복=1, 실행함수=None, 결과위치=None):
    결과폴더 = Path(결과위치) if 결과위치 else globals()['결과폴더']
    결과폴더.mkdir(parents=True, exist_ok=True)
    상황 = json.loads((상황폴더 / f'{상황이름}.json').read_text(encoding='utf-8'))
    시각 = datetime.now()
    작업루트 = 결과폴더 / '작업' / 시각.strftime('%Y%m%d_%H%M%S')
    회차들 = []
    for i in range(반복):
        print(f'[{i + 1}/{반복}] 3단계 실행 중... (최대 약 1분)', flush=True)
        r = 한번(상황, 작업루트 / f'{i + 1:02d}', 실행함수)
        print(f"   → 상태 {r['상태']}, {r['경과초']}초, {'모두 통과' if r['전체통과'] else '실패 있음'}", flush=True)
        회차들.append(r)
    점수표 = {'기록시각': 시각.astimezone().isoformat(), '커밋': _커밋(), '조건': 상황['설명'], '상황': 상황이름,
            '회차': 회차들, '요약': 요약(회차들)}
    점수표['비교'] = 비교문장(점수표, _이전점수표(결과폴더, 상황이름))
    이름 = '점수표_' + 시각.strftime('%Y%m%d_%H%M%S')
    (결과폴더 / f'{이름}.json').write_text(json.dumps(점수표, ensure_ascii=False, indent=2), encoding='utf-8')
    (결과폴더 / f'{이름}.md').write_text(md표(점수표), encoding='utf-8')
    print(f"점수표: {결과폴더 / (이름 + '.md')}\n{점수표['비교']}")
    return 점수표


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='3단계 하네스 (실제 AI)')
    p.add_argument('--반복', type=int, default=1)
    p.add_argument('--상황', default=기본상황)
    a = p.parse_args()
    돌리기(a.상황, max(1, a.반복))
