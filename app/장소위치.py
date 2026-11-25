"""장소 위치 확인과 지도 길 자동 수집.

- 좌표는 코드가 찾아 후보로만 두고, 관리자가 '맞다'를 누른 것만 장소 CSV에 넣는다.
- 길(도보 경로)은 확인된 장소끼리 코드가 알아서 모은다. 화면 조회·AI 실행 중에는 외부에 묻지 않고,
  관리자 서버의 뒤쪽 작업에서만 1초에 한 번 묻는다.
"""
import csv
import io
import json
import math
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from 설정 import 설정_읽기, 자료_파일
from 장소정보 import 장소_기본파일, 좌표, 대표위치, _이름
from 파일쓰기 import 바꿔쓰기

기준 = Path(__file__).resolve().parent
경로파일_기본 = 기준 / '담당자화면' / 'road-routes.json'
신고파일_기본 = 기준 / 'runs' / '장소위치_신고.json'
최대거리 = 3000  # 직선 3km 안의 장소끼리만 도보 길을 모은다
대구범위 = ((35.55, 36.05), (128.35, 128.80))
검토열 = ['위도', '경도', '좌표검토자', '좌표확인일', '좌표근거URL', '좌표검토근거', '좌표검토상태', '좌표위치기준']


def _장소파일():
    return 자료_파일(설정_읽기(), 'HARUHARU_PLACES_FILE', 장소_기본파일)


def _자동후보파일():
    return _장소파일().with_name('좌표후보_자동.json')


def _행들():
    with _장소파일().open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _json읽기(path, 기본):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 기본


def _json쓰기(path, 값):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    임시 = path.with_name(path.name + '.tmp')
    임시.write_text(json.dumps(값, ensure_ascii=False, indent=2), encoding='utf-8')
    바꿔쓰기(임시, path)


def 지도점(이름):
    """지도와 같은 규칙: 확인된 장소 CSV 좌표, 없으면 확인된 지도 대표위치."""
    p = 좌표(이름)
    if p:
        return p
    r = 대표위치(이름)
    return tuple(r['중심']) if r else None


def _신고들(신고파일):
    return _json읽기(신고파일, [])


def 신고(장소명, 내용, 신고파일=신고파일_기본):
    내용 = str(내용 or '').strip()
    if not 내용 or len(내용) > 300:
        raise ValueError('무엇이 이상한지 300자 이내로 적어 주세요.')
    같은 = [r['장소명'] for r in _행들() if _이름(r['장소명']) == _이름(str(장소명 or ''))]
    if len(같은) != 1:
        raise ValueError('장소 목록에 없는 장소입니다.')
    장소명 = 같은[0]   # 화면의 '대구광역시 중구 ○○'도 목록 이름으로 맞춘다
    목록 = _신고들(신고파일)
    목록.append({'장소명': 장소명, '내용': 내용, '시각': datetime.now().astimezone().isoformat(timespec='seconds'), '상태': '열림'})
    _json쓰기(신고파일, 목록)
    return {'안내': '관리자에게 전달했어요. 위치를 확인하면 지도에 반영돼요.'}


def 확인대기(신고파일=신고파일_기본):
    자동 = _json읽기(_자동후보파일(), {})
    검토표 = {}
    try:
        with _장소파일().with_name('장소좌표_검토용.csv').open(encoding='utf-8-sig', newline='') as f:
            검토표 = {r['장소명']: r for r in csv.DictReader(f)}
    except OSError:
        pass
    신고들 = [x for x in _신고들(신고파일) if x.get('상태') == '열림']
    out = []
    for r in _행들():
        열린 = [x for x in 신고들 if x['장소명'] == r['장소명']]
        if 지도점(r['장소명']) and not 열린:
            continue
        후보 = []
        a = 자동.get(r['장소명'])
        if a and a.get('위도'):
            후보.append({**a, '출처': '자동 검색(OpenStreetMap)'})
        t = 검토표.get(r['장소명'])
        if t and t.get('위도'):
            후보.append({'위도': t['위도'], '경도': t['경도'], '정밀도': t.get('정밀도', ''), '찾은이름': t.get('찾은이름', ''),
                       '근거URL': t.get('근거URL', ''), '출처': '팀 검토표'})
        out.append({'순번': r.get('순번'), '장소명': r['장소명'], '구': r.get('구', ''), '주소': r.get('주소', ''),
                    '현재좌표': [r.get('위도'), r.get('경도')] if r.get('위도') else None,
                    '좌표검토상태': r.get('좌표검토상태', ''), '후보': 후보, '신고': 열린,
                    '못찾음': bool(a and a.get('못찾음'))})
    return out


def _줄바꿈(text):
    return '\r\n' if '\r\n' in text else '\n'


def 확인(장소명, 위도, 경도, 근거URL, 근거설명, 신고파일=신고파일_기본, 검토자='관리자(화면)', 검토상태='사람확인완료', 위치기준='시설대표점'):
    """관리자가 '맞다'를 누른 좌표를 장소 CSV의 그 행에만 쓴다. 다른 행·열은 바이트 그대로 둔다."""
    try:
        위도, 경도 = float(위도), float(경도)
    except (TypeError, ValueError):
        raise ValueError('위도·경도는 숫자여야 합니다.') from None
    (la, lb), (oa, ob) = 대구범위
    if not (la <= 위도 <= lb and oa <= 경도 <= ob):
        raise ValueError('대구 범위 밖 좌표입니다. 위도·경도 순서를 확인하세요.')
    if not re.match(r'https?://', str(근거URL or '')):
        raise ValueError('근거 URL(http·https)을 넣어 주세요.')
    근거설명 = str(근거설명 or '').strip()
    if not 근거설명:
        raise ValueError('무엇과 대조했는지 근거를 적어 주세요.')
    path = _장소파일()
    raw = path.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    nl = _줄바꿈(text)
    lines = text.split(nl)
    머리 = next(csv.reader([lines[0]]))
    찾음 = [i for i, line in enumerate(lines[1:], 1) if line and next(csv.reader([line]))[머리.index('장소명')] == 장소명]
    if len(찾음) != 1:
        raise ValueError('장소 목록에 없는 장소입니다.')
    i = 찾음[0]
    row = dict(zip(머리, next(csv.reader([lines[i]]))))
    if 검토상태 not in ['사람확인완료', '자료대조완료']:
        raise ValueError('검토상태는 사람확인완료 또는 자료대조완료만 씁니다.')
    row.update({'위도': repr(위도), '경도': repr(경도), '좌표검토자': 검토자,
                '좌표확인일': datetime.now().date().isoformat(), '좌표근거URL': 근거URL, '좌표검토근거': 근거설명,
                '좌표검토상태': 검토상태, '좌표위치기준': 위치기준})
    buf = io.StringIO()
    csv.writer(buf, lineterminator='').writerow([row.get(k, '') for k in 머리])
    lines[i] = buf.getvalue()
    임시 = path.with_name(path.name + '.tmp')
    임시.write_bytes((b'\xef\xbb\xbf' if bom else b'') + nl.join(lines).encode('utf-8'))
    바꿔쓰기(임시, path)
    신고들 = _신고들(신고파일)
    if any(x['장소명'] == 장소명 and x.get('상태') == '열림' for x in 신고들):
        for x in 신고들:
            if x['장소명'] == 장소명 and x.get('상태') == '열림':
                x['상태'] = '처리됨'
        _json쓰기(신고파일, 신고들)
    return {'장소명': 장소명, '좌표': [위도, 경도], '안내': '확인했어요. 이 장소와 이어지는 지도 길을 뒤에서 모읍니다.'}


def 후보찾기(묻기=None, 쉬기=1.0, 신고파일=신고파일_기본):
    """확인 대기 장소 중 후보가 하나도 없는 곳만 OpenStreetMap에 묻는다. 찾은 것은 후보로만 저장한다."""
    from 좌표받기 import 주소검색, 이름으로_보완
    path = _자동후보파일()
    자동 = _json읽기(path, {})
    새로 = 0; 물음 = 0
    for r in 확인대기(신고파일):
        if r['후보'] or r['장소명'] in 자동:
            continue
        주소 = r['주소'] or f"대구광역시 {r['구']}"
        if 물음 and 쉬기:
            time.sleep(쉬기)
        찾은 = None
        try:
            if r['주소']:
                물음 += 1
                위도, 경도, 정밀, 이름 = 주소검색(r['주소'], 묻기)
                if 위도 and 정밀 == '건물':
                    찾은 = (위도, 경도, 정밀, 이름)
            if not 찾은:
                if 물음 and 쉬기:
                    time.sleep(쉬기)
                물음 += 1
                찾은 = 이름으로_보완(r['장소명'], 주소, 묻기)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            찾은 = None
        시각 = datetime.now().astimezone().isoformat(timespec='seconds')
        if 찾은:
            위도, 경도, 정밀, 이름 = 찾은
            자동[r['장소명']] = {'위도': str(위도), '경도': str(경도), '정밀도': 정밀, '찾은이름': 이름,
                              '근거URL': 'https://www.openstreetmap.org/?mlat={}&mlon={}#map=18/{}/{}'.format(위도, 경도, 위도, 경도),
                              '찾은시각': 시각}
            새로 += 1
        else:
            자동[r['장소명']] = {'못찾음': True, '찾은시각': 시각}
        _json쓰기(path, 자동)
    return 새로


def _거리(a, b):
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians((a[0] + b[0]) / 2)))


def 길수집(경로파일=경로파일_기본, 묻기=None, 쉬기=1.1):
    """확인된 장소끼리(직선 3km 안) 아직 없는 도보 길만 모은다. 실패한 쌍은 기록하고 다시 묻지 않는다."""
    import 도로경로
    묻기 = 묻기 or 도로경로.요청
    cache = _json읽기(경로파일, {})
    cache.setdefault('routes', {}); cache.setdefault('failures', {})
    점들 = []
    for r in _행들():
        p = 지도점(r['장소명'])
        if p and tuple(p) not in 점들:
            점들.append(tuple(p))
    새경로 = 실패 = 0; 물음 = False
    for a in 점들:
        for b in 점들:
            if a == b or _거리(a, b) > 최대거리:
                continue
            key = 도로경로.키(a, b)
            if key in cache['routes'] or key in cache['failures']:
                continue
            if 물음 and 쉬기:
                time.sleep(쉬기)
            물음 = True
            결과 = 도로경로.경로수집([{'좌표': list(a), '일차': 1}, {'좌표': list(b), '일차': 1}], cache, 묻기, 쉬기=0)
            if key in 결과['routes']:
                cache['routes'][key] = 결과['routes'][key]; 새경로 += 1
            else:
                cache['failures'][key] = 결과['failures'].get(key, '실패'); 실패 += 1
            _json쓰기(경로파일, cache)
    return {'새경로': 새경로, '실패': 실패, '장소점': len(점들)}


class 자동작업:
    """서버 시작 때와 '맞다' 뒤에 후보찾기 → 길수집을 뒤쪽에서 한 번씩 돌린다. 동시에 하나만."""

    def __init__(self, 경로파일=경로파일_기본, 신고파일=신고파일_기본):
        self.경로파일, self.신고파일 = 경로파일, 신고파일
        self.잠금 = threading.Lock(); self.다시 = False; self.본시각 = None
        self.상태 = {'상태': '쉼', '안내': '아직 실행하지 않았어요.'}

    def 감시한번(self):
        """장소 CSV·지도 대표위치가 바뀌었으면(화면 밖에서 직접 고친 경우 포함) 자동작업을 다시 돈다."""
        파일 = [_장소파일(), _장소파일().with_name('지도_대표위치.json')]
        시각 = tuple(f.stat().st_mtime if f.exists() else 0 for f in 파일)
        if 시각 != self.본시각:
            self.본시각 = 시각
            self.시작()

    def 감시(self, 간격=120):
        """서버가 켜져 있는 동안 간격마다 파일이 바뀌었는지 본다. 바뀌지 않으면 외부에 묻지 않는다."""
        def 돌기():
            while True:
                try:
                    self.감시한번()
                except OSError:
                    pass
                time.sleep(간격)
        threading.Thread(target=돌기, daemon=True).start()

    def 시작(self):
        with self.잠금:
            if self.상태['상태'] == '진행중':
                self.다시 = True
                return dict(self.상태)
            self.상태 = {'상태': '진행중', '안내': '좌표 후보를 찾고 지도 길을 모으는 중이에요.', '시작': datetime.now().astimezone().isoformat(timespec='seconds')}
        threading.Thread(target=self._돌리기, daemon=True).start()
        return dict(self.상태)

    def _돌리기(self):
        while True:
            try:
                n = 후보찾기(신고파일=self.신고파일)
                길 = 길수집(self.경로파일)
                결과 = {'상태': '쉼', '안내': f"좌표 후보 {n}곳 새로 찾음 · 지도 길 {길['새경로']}개 새로 모음 · 실패 {길['실패']}개",
                      '끝': datetime.now().astimezone().isoformat(timespec='seconds')}
            except Exception as 오류:  # 외부 서버 장애가 관리자 서버를 멈추지 않게 한다
                결과 = {'상태': '쉼', '안내': f'자동 작업 실패: {type(오류).__name__}. 잠시 뒤 다시 시도하세요.'}
            with self.잠금:
                if self.다시:
                    self.다시 = False
                    continue
                self.상태 = 결과
                return


class 장소서비스:
    """HTTP 화면이 쓰는 묶음. 확인·신고는 바로 저장하고, 길 모으기는 뒤쪽 작업에 맡긴다."""

    def __init__(self, 신고파일=신고파일_기본, 경로파일=경로파일_기본, 작업=None):
        self.신고파일 = 신고파일
        self.작업 = 작업 or 자동작업(경로파일, 신고파일)

    def 목록(self):
        return {'대기': 확인대기(self.신고파일), '작업': dict(self.작업.상태)}

    def 확인(self, 값):
        결과 = 확인(값.get('장소명'), 값.get('위도'), 값.get('경도'), 값.get('근거URL'), 값.get('근거설명'), 신고파일=self.신고파일)
        결과['작업'] = self.작업.시작()
        return 결과

    def 신고(self, 값):
        return 신고(값.get('장소명'), 값.get('내용'), 신고파일=self.신고파일)
