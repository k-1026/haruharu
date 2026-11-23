"""로컬 서버의 실제 HTTP 요청으로 쓰기 경계를 확인한다. AI는 가짜 실행기 사용."""
import http.client
import json
import threading
import unittest
from urllib.parse import quote
from http.server import ThreadingHTTPServer

from 관리자조회 import 핸들러
import test_관리자실행 as fixtures


class HTTP시험(unittest.TestCase):
    def test_HTTP_후보자료와_상시기획_초안_저장재조회(self):
        import test_단계연결 as course_fixtures
        code,places=self.request('GET','/api/places')
        self.assertEqual(code,200)
        self.assertTrue(any(r['장소명']=='동대구역' for r in places['장소목록']))
        token=self.request('GET','/api/session')[1]['token'];h={'X-Admin-Token':token}
        _,base=self.request('POST','/api/course/save',{'id':self.key,'조건':fixtures.코스조건()},h)
        p=self.store.루트/base['시험id']/'3단계_결과.md'
        p.write_text(json.dumps(course_fixtures.코스()),encoding='utf-8')
        code,result=self.request('POST','/api/course/review/save',{'시험id':base['시험id'],'확인내용':{'운영기준':'상시기획','운영조건':'금·토 출발 / 동계 확인','방문시작일':'2026-11-25'}},h)
        self.assertEqual(code,201)
        _,info=self.request('GET','/api/course/review?id='+quote(result['시험id']))
        self.assertEqual(info['저장값']['운영조건'],'금·토 출발 / 동계 확인')
        self.assertEqual(info['저장값']['방문시작일'],'')
        self.assertFalse(result['4단계준비검사']['진행가능'])
        self.assertEqual(self.calls,[])

    def test_HTTP_운영정보_저장과_준비검사는_AI없음(self):
        import test_단계연결 as course_fixtures
        token=self.request('GET','/api/session')[1]['token'];h={'X-Admin-Token':token}
        _,base=self.request('POST','/api/course/save',{'id':self.key,'조건':fixtures.코스조건()},h)
        p=self.store.루트/base['시험id']/'3단계_결과.md'
        p.write_text(json.dumps(course_fixtures.코스()),encoding='utf-8')
        code,info=self.request('GET','/api/course/review?id='+quote(base['시험id']))
        self.assertEqual(code,200);self.assertTrue(info['일정목록'])
        code,result=self.request('POST','/api/course/review/save',{'시험id':base['시험id'],'확인내용':{}},h)
        self.assertEqual(code,201);self.assertFalse(result['4단계준비검사']['진행가능'])
        self.assertEqual(self.calls,[])

    def test_HTTP_선택일차가_파일과_수정본에_왕복보존(self):
        import test_단계연결 as course_fixtures
        token=self.request('GET','/api/session')[1]['token'];h={'X-Admin-Token':token}
        conditions=fixtures.코스조건();conditions.update({'시작일차':1,'종료일차':2,'시작시각':'11:34','종료시각':'21:34'})
        code,base=self.request('POST','/api/course/save',{'id':self.key,'조건':conditions},h)
        self.assertEqual(code,201)
        url='/api/file?path='+quote(base['시험id']+'/코스작성조건_선택.json')
        saved=json.loads(self.request('GET',url)[1]['본문'])
        self.assertEqual((saved['시작일차'],saved['종료일차']),(1,2))
        folder=self.store.루트/base['시험id']
        (folder/'3단계_결과.md').write_text(json.dumps(course_fixtures.코스(),ensure_ascii=False),encoding='utf-8')
        conditions.update({'시작시각':'12:00','종료시각':'20:00'})
        code,revised=self.request('POST','/api/course/apply',{'시험id':base['시험id'],'조건':conditions},h)
        self.assertEqual(code,201)
        for filename in ['코스작성조건_선택.json','3단계_구조화.json']:
            content=json.loads(self.request('GET','/api/file?path='+quote(revised['시험id']+'/'+filename))[1]['본문'])
            obj=content.get('코스시작종료',content)
            self.assertEqual((obj['시작일차'],obj['종료일차']),(1,2))
        # 재조회해도 원래 저장한 입력을 바꾸지 않는다.
        self.assertEqual(json.loads(self.request('GET',url)[1]['본문'])['시작시각'],'11:34')
        self.assertEqual(self.calls,[])

    def test_HTTP_수동반영은_AI없이_별도수정본_저장(self):
        import test_단계연결 as course_fixtures
        token = self.request('GET', '/api/session')[1]['token']
        h={'X-Admin-Token':token}
        conditions=fixtures.코스조건()
        code,base=self.request('POST','/api/course/save',{'id':self.key,'조건':conditions},h)
        p=self.store.루트/base['시험id']/'3단계_결과.md'
        p.write_text(json.dumps(course_fixtures.코스(),ensure_ascii=False),encoding='utf-8')
        conditions.update({'시작지점':'시작A','종료지점':'종료B','2일차점심포함':'미포함'})
        code,result=self.request('POST','/api/course/apply',{'시험id':base['시험id'],'조건':conditions},h)
        self.assertEqual(code,201)
        self.assertNotEqual(base['시험id'],result['시험id'])
        self.assertTrue(result['수동수정본'])
        self.assertEqual(self.calls,[])

    def setUp(self):
        fixtures.재개시험.setUp(self)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), 핸들러(self.store, self.service))
        t = threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        t.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.port = self.httpd.server_port
        self.origin = f'http://127.0.0.1:{self.port}'

    def request(self, method, url, value=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        body = json.dumps(value, ensure_ascii=False).encode() if value is not None else None
        h = {'Origin': self.origin, 'Content-Type': 'application/json'}
        h.update(headers or {})
        conn.request(method, url, body, h)
        r = conn.getresponse()
        data = json.loads(r.read().decode())
        conn.close()
        return r.status, data

    def test_HTTP_저장_실행_상태(self):
        code, session = self.request('GET', '/api/session')
        self.assertEqual(code, 200)
        h = {'X-Admin-Token': session['token']}
        code, saved = self.request('POST', '/api/course/save', {'id': self.key, '조건': fixtures.코스조건()}, h)
        self.assertEqual(code, 201)
        self.assertEqual(self.calls, [])
        code, started = self.request('POST', '/api/course/start', {'시험id': saved['시험id']}, h)
        self.assertEqual(code, 202)
        self.service.작업들[saved['시험id']].join(3)
        code, status = self.request('GET', '/api/course/status?id=' + quote(saved['시험id']))
        self.assertEqual(code, 200)
        self.assertEqual(status['상태'], '검사확인필요')
        self.assertEqual(len(self.calls), 1)

    def test_다른사이트와_토큰없는_저장_거부(self):
        value = {'id': self.key, '조건': fixtures.코스조건()}
        self.assertEqual(self.request('POST', '/api/course/save', value)[0], 403)
        token = self.request('GET', '/api/session')[1]['token']
        self.assertEqual(self.request('POST', '/api/course/save', value,
                                     {'Origin': 'https://elsewhere.invalid', 'X-Admin-Token': token})[0], 403)
        self.assertEqual(self.calls, [])

    def raw(self, url):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('GET', url);r = conn.getresponse();body = r.read().decode();conn.close()
        return r.status, body

    def test_담당자화면과_관리자창_경로분리(self):
        code, body = self.raw('/')
        self.assertEqual(code, 200);self.assertIn('담당자', body)
        self.assertEqual(self.raw('/plan/')[1], body)
        self.assertIn('관리자', self.raw('/admin/')[1])
        self.assertEqual(self.request('GET', '/api/plan/course?id=' + quote('../x'))[0], 400)
        code, summary = self.request('GET', '/api/plan/course?id=' + quote(self.key))
        self.assertEqual(code, 200);self.assertFalse(summary['코스있음'])

    def test_읽기와_오류응답_유지(self):
        self.assertEqual(self.request('GET', '/api/runs')[0], 200)
        self.assertEqual(self.request('PUT', '/api/course/start', {})[0], 405)
        token = self.request('GET', '/api/session')[1]['token']
        self.assertEqual(self.request('POST', '/api/course/save', {'id': self.key, '조건': []},
                                     {'X-Admin-Token': token})[0], 400)
        self.assertEqual(self.request('GET', '/api/runs', headers={'Host': 'elsewhere.invalid'})[0], 403)
