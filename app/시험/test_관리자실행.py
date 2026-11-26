"""저장된 2단계에서의 재개. 실제 AI 없이 실행 경계와 HTTP를 시험한다."""
import json
from pathlib import Path
import tempfile
import threading
import unittest

from app.서버.관리자조회 import 결과저장소
from app.서버.관리자실행 import 코스시험, 조건_검사


def 전달():
    return {'조건': {'계절': '봄', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'},
            '확정체류기간': '1박2일', '담당자선택_E3': '경고를남기고진행', '요약': '시험',
            '근거목록': [{'근거ID': 'R01', '항목': '방문객', '수치_원문': '1%', '수치': 1,
                        '파일_행위치': '시험.csv · 시험행', '출처': '시험 자료'}],
            '경고목록': [], '미확인사항': [], '검사결과': ['통과']}


def 코스조건():
    return {'시작지점': '', '시작시각': '', '종료지점': '', '종료시각': '',
            '운영방식': '', '치킨선택': '', '2일차오전구성': '',
            '식사목록': [{'일차': d, '시간칸': s, '방식': '', '식당': '', '식비포함': ''}
                       for d, s in [(1, '점심'), (1, '저녁'), (2, '점심')]]}


class 재개시험(unittest.TestCase):
    def test_미정은_대기로_분리하고_잘못된시각은_계속오류(self):
        import test_단계연결 as fixtures
        value = 코스조건()
        value['2일차오전구성'] = '자유시간'
        for r in value['식사목록']:
            r.update({'방식': '자유식', '식비포함': '불포함'})
        job = self.service.저장(self.key, value)
        folder = Path(self.tmp.name) / job['시험id']
        course = fixtures.코스()
        course['코스시작종료'] = {k: '미확인' for k in ['시작지점','시작시각','종료지점','종료시각']}
        course['확정조건']['시작종료확정'] = False
        course['2일차오전구성'] = '자유시간'
        course['미확인사항'] = [{'대상 칸ID': '낮-1', '내용': '확인 필요'}]
        course['칸목록'].append({'칸ID':'오전','일차':2,'시간칸':'2일차오전','장소명':'자유시간',
                                 '시각':{'값':'','종류':'미정'},'근거ID':[]})
        for slot in ['점심','저녁']:
            course['칸목록'].append({'칸ID':slot,'일차':1,'시간칸':slot,'시각':{'값':'12:00','종류':'가정'},'근거ID':[]})
            course['식사목록'].append({'칸ID':slot,'방식':'자유식','식당':'','식비포함':'불포함','시각':{'값':'12:00','종류':'가정'}})
        raw = folder / '3단계_결과.md'
        raw.write_text(json.dumps(course, ensure_ascii=False), encoding='utf-8')
        status = self.service.재검사(job['시험id'])
        self.assertEqual(status['문제'], [])
        self.assertEqual(status['상태'], '담당자확인대기')
        self.assertEqual(len(status['담당자확인대기']), 5)
        self.assertFalse(status['담당자확정'])
        course['코스시작종료']['시작시각'] = '99:00'
        raw.write_text(json.dumps(course), encoding='utf-8')
        self.assertIn('시작시각 형식 오류', self.service.재검사(job['시험id'])['문제'])
        self.assertEqual(self.calls, [])

    def test_저장결과_재검사는_AI호출없이_원문보존(self):
        job = self.service.저장(self.key, 코스조건())
        folder = Path(self.tmp.name) / job['시험id']
        text = '먼저 자료를 읽겠습니다.\n```json\n{"확정조건": {}}\n```'
        (folder / '3단계_결과.md').write_text(text, encoding='utf-8')
        result = self.service.재검사(job['시험id'])
        self.assertEqual(self.calls, [])
        self.assertEqual(result['상태'], '검사확인필요')
        self.assertFalse(result['담당자확정'])
        self.assertTrue(any('필드' in p for p in result['문제']))
        self.assertEqual((folder / '3단계_결과.md').read_text(encoding='utf-8'), text)
        self.assertEqual(json.loads((folder / '3단계_구조화.json').read_text(encoding='utf-8')), {'확정조건': {}})
        self.assertTrue((folder / '통합시험_상태_재검사전.json').exists())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = 결과저장소(Path(self.tmp.name))
        self.key = '20261122_223324/01회차'
        self.folder = Path(self.tmp.name) / self.key
        self.folder.mkdir(parents=True)
        self.source = self.folder / '3단계_전달_준비.json'
        self.source.write_text(json.dumps(전달(), ensure_ascii=False), encoding='utf-8')
        self.calls = []

        async def fake(agent, prompt):
            self.calls.append((agent, prompt))
            return '{"확정조건": {}}'
        self.service = 코스시험(self.store, 실행함수=fake)

    def test_미정입력과_원본보존(self):
        before = self.source.read_bytes()
        result = self.service.저장(self.key, 코스조건())
        p = Path(self.tmp.name) / result['시험id']
        saved = json.loads((p / '3단계_입력.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['코스작성조건']['시작지점'], '미확인')
        self.assertEqual(saved['코스작성조건']['2일차오전구성'], '미선택')
        self.assertEqual(saved['코스작성조건']['식사목록'][0]['식비포함'], '미정')
        self.assertEqual(saved['코스작성조건']['결정기록']['입력경로'], '관리자 화면')
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.calls, [])

    def test_거짓통과는_재검사로_차단(self):
        bad = 전달(); bad['근거목록'] = []
        self.source.write_text(json.dumps(bad), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '전달 검사'):
            self.service.저장(self.key, 코스조건())

    def test_시작전_원본변경_차단(self):
        job = self.service.저장(self.key, 코스조건())
        self.source.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '변경'):
            self.service.시작(job['시험id'])
        self.assertEqual(self.calls, [])

    def test_3단계만_호출하고_불완전결과_확인필요(self):
        job = self.service.저장(self.key, 코스조건())
        self.service.시작(job['시험id'])
        self.service.작업들[job['시험id']].join(3)
        status = self.service.상태(job['시험id'])
        self.assertEqual(len(self.calls), 1)
        self.assertIn('코스주문.md', self.calls[0][0])
        self.assertEqual(status['상태'], '검사확인필요')
        self.assertFalse(status['담당자확정'])
        folder = Path(self.tmp.name) / job['시험id']
        self.assertTrue((folder / '3단계_결과.md').is_file())
        self.assertTrue((folder / '3단계_주문서.json').is_file())
        크기 = json.loads((folder / '3단계_크기.json').read_text(encoding='utf-8'))
        self.assertEqual(set(크기), {'받은글자', '쓴글자', '경과초'})

    def test_3단계는_주문지침을_부르고_조립본을_저장한다(self):
        칸 = lambda id, 일차, 시간칸, p: {'칸ID': id, '일차': 일차, '시간칸': 시간칸, '장소': p, '머무는분': 60, '근거': [], '운영': [], '이유': '시험'}
        주문 = {'A': {'칸': [칸('낮-1', 1, '낮', 'P1'), 칸('점심-1', 1, '점심', 'P2'), 칸('저녁-1', 1, '저녁', 'P6'), 칸('낮-2', 2, '낮', 'P11')],
                      '식사': [{'칸ID': '점심-1', '방식': '자유식', '권역': 'P2', '후보': []}, {'칸ID': '저녁-1', '방식': '지정식', '권역': 'P6', '후보': []}]}}
        원문 = json.dumps(주문, ensure_ascii=False)
        async def 주문함수(agent, prompt):
            self.calls.append((agent, prompt)); return 원문
        service = 코스시험(self.store, 실행함수=주문함수)
        job = service.저장(self.key, 코스조건()); service.시작(job['시험id']); service.작업들[job['시험id']].join(3)
        self.assertTrue(self.calls[0][0].endswith('코스주문.md'))
        self.assertIn('P1|근대골목', self.calls[0][1])
        folder = Path(self.tmp.name) / job['시험id']
        결과 = json.loads((folder / '3단계_결과.md').read_text(encoding='utf-8'))
        self.assertIn('체크리스트', 결과)
        self.assertEqual(결과['칸목록'][0]['장소명'], '대구광역시 중구 근대골목')
        self.assertEqual(json.loads((folder / '3단계_크기.json').read_text(encoding='utf-8'))['쓴글자'], len(원문))
        self.assertNotEqual(service.상태(job['시험id'])['상태'], '실행실패')

    def test_틀린_주문서는_검사확인필요(self):
        async def 틀림(agent, prompt):
            return '{"A":{"칸":[{"칸ID":"낮-1","일차":1,"시간칸":"낮","장소":"P99","머무는분":60}],"식사":[]}}'
        service = 코스시험(self.store, 실행함수=틀림)
        job = service.저장(self.key, 코스조건()); service.시작(job['시험id']); service.작업들[job['시험id']].join(3)
        status = service.상태(job['시험id'])
        self.assertEqual(status['상태'], '검사확인필요')
        self.assertTrue([p for p in status['문제'] if 'P99' in p])

    def test_실행중_중복시작은_한번만(self):
        entered, release = threading.Event(), threading.Event()

        async def blocking(agent, prompt):
            self.calls.append(agent); entered.set(); release.wait(3)
            return '{}'
        service = 코스시험(self.store, 실행함수=blocking)
        job = service.저장(self.key, 코스조건())
        service.시작(job['시험id'])
        self.assertTrue(entered.wait(2))
        self.assertEqual(service.시작(job['시험id'])['상태'], '실행중')
        release.set(); service.작업들[job['시험id']].join(3)
        self.assertEqual(len(self.calls), 1)

    def test_실행실패는_민감정보없이_보존(self):
        from unittest.mock import patch
        async def bad(agent, prompt):
            raise RuntimeError('SECRET_DO_NOT_EXPOSE')
        service = 코스시험(self.store, 실행함수=bad)
        # 실제 설정된 비밀값이 예외에 섞인 상황을 재현한다.
        # 무표시 임의 문자열 전체가 비밀인지 알아맞히도록 요구하지 않는다.
        with patch('app.공통.오류기록.설정_읽기', return_value={'GEMINI_API_KEY': 'SECRET_DO_NOT_EXPOSE'}):
            job = service.저장(self.key, 코스조건()); service.시작(job['시험id'])
            service.작업들[job['시험id']].join(3)
        status = service.상태(job['시험id'])
        self.assertEqual(status['상태'], '실행실패')
        self.assertNotIn('SECRET', json.dumps(status))
        self.assertEqual(status['오류상세']['메시지'], '[가림]')
        오류파일 = Path(self.tmp.name) / job['시험id'] / 'AI_오류.json'
        self.assertNotIn('SECRET', 오류파일.read_text(encoding='utf-8'))

    def test_서버재시작은_계속실행중으로_표시안함(self):
        job = self.service.저장(self.key, 코스조건())
        p = Path(self.tmp.name) / job['시험id'] / '통합시험_상태.json'
        p.write_text(json.dumps({'상태': '실행중'}), encoding='utf-8')
        self.assertEqual(코스시험(self.store).상태(job['시험id'])['상태'], '중단됨')

    def test_경로이탈과_임의폴더저장_차단(self):
        for key in ['../escape', '20261122_223324/01회차/..', self.key + '/통합시험_000000_000001']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.service.저장(key, 코스조건())

    def test_잘못된시각과_식사조건_차단(self):
        for key, value in [('시작시각', '25:00'), ('운영방식', '알아서')]:
            bad = 코스조건(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                조건_검사(bad, '1박2일')
        bad = 코스조건(); bad['식사목록'][0].update({'방식': '자유식', '식당': '확정식당'})
        with self.assertRaises(ValueError):
            조건_검사(bad, '1박2일')

    def test_당일은_2일차_추가안함(self):
        value = 코스조건(); value['식사목록'] = value['식사목록'][:2]
        checked = 조건_검사(value, '당일')
        self.assertEqual(checked['2일차오전구성'], '해당없음')
        self.assertEqual(len(checked['식사목록']), 2)

    def test_정상결과도_사람확정없이_초안으로_저장(self):
        조건 = 코스조건()
        조건.update({'시작일차':1,'종료일차':2,'시작지점': '장소A', '시작시각': '10:00', '종료지점': '장소B', '종료시각': '14:00',
                     '2일차오전구성': '자유시간', '운영방식': '개별이동형'})
        for r in 조건['식사목록']:
            r.update({'방식': '자유식', '식비포함': '불포함'})
        결과 = {'확정조건': {'시작종료확정': True, '겹침처리': True, '2일차오전선택': True},
              '코스시작종료': {k: 조건[k] for k in ['시작지점', '시작시각', '종료지점', '종료시각']},
              '운영방식': '개별이동형', '2일차오전구성': '자유시간',
              '칸목록': [], '식사목록': [], '장소스토리': [], '대체이력': [], '담당자결정': [],
              '겹침이력': [], '남은경고': [], '미확인사항': [], '체크리스트': []}
        for i, r in enumerate(조건['식사목록']):
            시각='18:00' if r['시간칸']=='저녁' else '12:00'
            칸 = {'칸ID': f'meal-{i}', '일차': r['일차'], '시간칸': r['시간칸'],
                 '시각': {'값': 시각, '종류': '가정'}, '근거ID': [], '머무는시간':60}
            결과['칸목록'].append(칸)
            결과['식사목록'].append({'칸ID': f'meal-{i}', '방식': '자유식', '식당': '', '식비포함': '불포함',
                                  '시각': {'값': 시각, '종류': '가정'}})

        # AI는 이제 주문서만 쓰므로, 완성 코스의 분류 검사는 저장본 재검사 경로로 확인한다
        service = self.service
        job = service.저장(self.key, 조건)
        (Path(self.tmp.name) / job['시험id'] / '3단계_결과.md').write_text(json.dumps(결과, ensure_ascii=False), encoding='utf-8')
        service.재검사(job['시험id'])
        self.assertEqual(service.상태(job['시험id'])['상태'], '초안생성')
        self.assertFalse(service.상태(job['시험id'])['담당자확정'])
        결과폴더 = Path(self.tmp.name) / job['시험id']
        self.assertFalse((결과폴더 / '4단계_결과.md').exists())

    def test_쓰지않은_식사조건은_검사에서_알림(self):
        bad = {'확정조건': {}, '코스시작종료': {}, '운영방식': '미정', '2일차오전구성': '미선택',
               **{k: [] for k in ['칸목록', '식사목록', '장소스토리', '대체이력', '담당자결정', '겹침이력', '남은경고', '미확인사항', '체크리스트']}}
        service = self.service
        job = service.저장(self.key, 코스조건())
        (Path(self.tmp.name) / job['시험id'] / '3단계_결과.md').write_text(json.dumps(bad, ensure_ascii=False), encoding='utf-8')
        service.재검사(job['시험id'])
        self.assertTrue(any('식사 칸' in e for e in service.상태(job['시험id'])['문제']))


if __name__ == '__main__':
    unittest.main()
