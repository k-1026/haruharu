"""관리자 '장소 위치 확인' 화면 API와 기획자 신고 API. 외부 조회·실제 자료 파일 변경 없음."""
import http.client
import json
import os
import shutil
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from app.서버.관리자조회 import 결과저장소, 핸들러
from app.단계3_코스검토 import 장소위치

저장소 = Path(__file__).resolve().parents[2]


class 가짜작업:
    def __init__(self): self.시작횟수 = 0; self.상태 = {'상태': '쉼', '안내': '시험'}
    def 시작(self): self.시작횟수 += 1; return dict(self.상태)


class 장소위치HTTP시험(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        data = Path(self.tmp.name) / 'data'; data.mkdir()
        for name in ['장소운영정보_중구동구_데모코스_2026.csv', '이동시간_중구동구_데모코스_2026.csv', '지도_대표위치.json', '장소좌표_검토용.csv']:
            shutil.copy(저장소 / 'research/data' / name, data / name)
        env = mock.patch.dict(os.environ, {'HARUHARU_DATA_DIR': str(data)}); env.start(); self.addCleanup(env.stop)
        self.작업 = 가짜작업()
        서비스 = 장소위치.장소서비스(신고파일=Path(self.tmp.name) / '신고.json', 작업=self.작업)
        store = 결과저장소(Path(self.tmp.name) / 'runs')
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), 핸들러(store, 장소서비스=서비스))
        threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True).start()
        self.addCleanup(self.httpd.server_close); self.addCleanup(self.httpd.shutdown)
        self.origin = f'http://127.0.0.1:{self.httpd.server_port}'

    def request(self, method, url, value=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=5)
        h = {'Origin': self.origin, 'Content-Type': 'application/json', **(headers or {})}
        conn.request(method, url, json.dumps(value, ensure_ascii=False).encode() if value is not None else None, h)
        r = conn.getresponse(); body = r.read(); conn.close()
        return r.status, (json.loads(body.decode()) if 'json' in (r.getheader('Content-Type') or '') else body.decode())

    def 토큰(self):
        return {'X-Admin-Token': self.request('GET', '/api/session')[1]['token']}

    def test_관리자_화면과_대기목록을_보여준다(self):
        code, page = self.request('GET', '/admin/places-review')
        self.assertEqual(code, 200); self.assertIn('장소 위치 확인', page)
        self.assertEqual(self.request('GET', '/admin/place-review.js')[0], 200)
        code, data = self.request('GET', '/api/place-review')
        self.assertEqual(code, 200)
        self.assertIn('봉산문화거리', [x['장소명'] for x in data['대기']])
        self.assertIn('상태', data['작업'])

    def test_맞다를_누르면_저장하고_길수집을_시작한다(self):
        값 = {'장소명': '봉산문화거리', '위도': 35.8631, '경도': 128.5965, '근거URL': 'https://example.org/g', '근거설명': '공식 주소 대조'}
        self.assertEqual(self.request('POST', '/api/place-review/confirm', 값)[0], 403)   # 토큰 없으면 거부
        code, data = self.request('POST', '/api/place-review/confirm', 값, self.토큰())
        self.assertEqual(code, 201, data)
        self.assertEqual(self.작업.시작횟수, 1)
        _, 목록 = self.request('GET', '/api/place-review')
        self.assertNotIn('봉산문화거리', [x['장소명'] for x in 목록['대기']])

    def test_잘못된_좌표는_400(self):
        code, data = self.request('POST', '/api/place-review/confirm',
                                  {'장소명': '봉산문화거리', '위도': 33.0, '경도': 126.5, '근거URL': 'https://a', '근거설명': 'x'}, self.토큰())
        self.assertEqual(code, 400); self.assertIn('대구 범위', data['오류'])

    def test_기획자_신고는_대기목록에_올라간다(self):
        code, data = self.request('POST', '/api/place-review/report', {'장소명': '김광석길', '내용': '위치가 길 건너편 같아요'}, self.토큰())
        self.assertEqual(code, 201, data)
        _, 목록 = self.request('GET', '/api/place-review')
        김 = next(x for x in 목록['대기'] if x['장소명'] == '김광석길')
        self.assertEqual(김['신고'][0]['내용'], '위치가 길 건너편 같아요')


if __name__ == '__main__':
    unittest.main()
