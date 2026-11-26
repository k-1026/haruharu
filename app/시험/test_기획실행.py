import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest import mock

from app.서버.관리자조회 import 결과저장소
from app.서버.관리자실행 import 코스시험
from app.공통 import 기획기록 as 기록모듈
from app.공통 import 기획실행 as 모듈

견본 = Path(__file__).resolve().parents[1] / 'runs' / '20261122_223324' / '01회차'
견본있음 = (견본 / '2단계_결과.md').is_file() and (견본 / '통합시험_235320_982315' / '3단계_결과.md').is_file()

좋은입력 = {'계절': '봄', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일',
         '목표': '저녁까지 머물게', '희망': ['저녁은 동성로', ' ', '야경'], '자동진행동의': True}


class 입력검사시험(unittest.TestCase):
    def test_정상_입력은_정리된다(self):
        조건, 목표, 희망 = 모듈.입력_검사(좋은입력)
        self.assertEqual(조건, {'계절': '봄', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'})
        self.assertEqual((목표, 희망), ('저녁까지 머물게', ['저녁은 동성로', '야경']))

    def test_동의없거나_조건빠지면_거부(self):
        for 바꿈, 문구 in [({'자동진행동의': False}, '동의'), ({'지역': []}, '지역'), ({'체류기간': '추천받기'}, '체류 기간'),
                         ({'계절': '장마'}, '계절'), ({'언어권': ['독일어']}, '언어권')]:
            with self.subTest(바꿈=바꿈), self.assertRaisesRegex(ValueError, 문구):
                모듈.입력_검사({**좋은입력, **바꿈})

    def test_빈_코스조건은_관리자_조건검사를_통과(self):
        from app.서버.관리자실행 import 조건_검사
        for 체류 in ['당일', '1박2일']:
            결과 = 조건_검사(모듈.빈_코스조건(체류), 체류)
            self.assertEqual(결과['시작지점'], '미확인')
            self.assertTrue(all(m['방식'] == '미선택' for m in 결과['식사목록']))


@unittest.skipUnless(견본있음, '저장된 1~3단계 견본이 필요합니다')
class 끝까지시험(unittest.TestCase):
    def 준비(self, 단계함수, 코스함수):
        self.d = TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        저장소 = 결과저장소(self.d.name)
        self.코스 = 코스시험(저장소, 실행함수=코스함수)
        self.서비스 = 모듈.기획실행(self.코스, 단계함수=단계함수)
        self.guard = mock.patch('app.공통.run_stage.단계_실행', side_effect=AssertionError('자동시험에서 실제 AI 호출 금지'))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def 기다리기(self):
        self.서비스.작업.join(timeout=30)
        self.assertFalse(self.서비스.작업.is_alive())

    def test_조건만_넣으면_터미널_입력없이_초안과_기록까지(self):
        본 = []

        def 단계(에이전트, 입력):
            본.append((에이전트, 입력))
            if 에이전트.endswith('수요요약.md'):
                return '{"요약":"선택한 근거를 참고하며 자료별 한계를 구분합니다."}'
            if 에이전트.endswith('검증.md'):
                return '{"통과":true,"문제":[]}'
            if 에이전트.endswith('총괄.md'):
                return '{"행동":"담당자에게","대상":"A","이유":"모의 검증 완료"}'
            raise AssertionError('예상하지 않은 에이전트: ' + 에이전트)

        def 코스(에이전트, 요청):
            본.append((에이전트, 요청))
            칸 = lambda id, 일차, 시간칸, p: {'칸ID': id, '일차': 일차, '시간칸': 시간칸, '장소': p, '머무는분': 60, '근거': [], '운영': [], '이유': ''}
            return json.dumps({'A': {'칸': [칸('낮-1', 1, '낮', 'P1'), 칸('저녁-1', 1, '저녁', 'P6'), 칸('낮-2', 2, '낮', 'P11')], '식사': []}}, ensure_ascii=False)
        self.준비(단계, 코스)
        시작 = self.서비스.시작(좋은입력)
        self.assertEqual(시작['상태'], '진행중')
        self.기다리기()
        p = self.서비스.상태(시작['기획id'])
        self.assertEqual(p['상태'], '완료', p.get('안내'))
        self.assertEqual([s['상태'] for s in p['단계']], ['완료'] * 5)
        self.assertFalse(p['단계'][0]['AI'])
        self.assertTrue(all(s.get('시작') and s.get('끝') for s in p['단계']))
        self.assertIsNone(p['일하는중'])
        self.assertEqual([a for a, _ in 본], ['.claude/agents/수요요약.md', '.claude/agents/코스주문.md', '.claude/agents/코스주문.md', '.claude/agents/검증.md'])
        self.assertIn('B안보완요청', 본[2][1])  # 예전 A-only 저장 응답에는 B만 한 번 보완한다
        폴더 = Path(self.d.name) / 시작['기획id']
        for 이름 in ['1단계_선택.json', '2단계_선택.json']:
            self.assertIn('자동 진행', json.loads((폴더 / 이름).read_text(encoding='utf-8'))['자동처리'])
        self.assertIn('저녁은 동성로', 본[1][1])   # 희망이 코스 작성 입력에 들어감
        self.assertTrue((폴더 / '근거_추출.json').is_file())
        기록 = 기록모듈.읽기(self.d.name, p['기록id'])
        self.assertEqual(기록['원래요청']['희망'][0]['내용'], '저녁은 동성로')
        self.assertEqual(기록모듈.버전목록(기록, 'A'), [1])
        self.assertIsNone(기록['선택'])  # 사람이 고르기 전에는 선택 없음
        self.assertEqual(self.서비스.최근()['기획id'], 시작['기획id'])

    def test_진행중에_다시_누르면_같은_기획을_돌려준다(self):
        풀림 = threading.Event()
        진입 = threading.Event()
        self.addCleanup(풀림.set)

        def 단계(에이전트, 입력):
            진입.set()
            풀림.wait(10)
            raise TimeoutError('AI(claude)가 300초 동안 응답하지 않아 중단했습니다.')
        self.준비(단계, None)
        첫 = self.서비스.시작(좋은입력)
        self.assertTrue(진입.wait(2))
        둘 = self.서비스.시작(좋은입력)
        for _ in range(50):
            지금 = self.서비스.상태(첫['기획id'])
            if 지금.get('일하는중'):break
            threading.Event().wait(0.05)
        self.assertEqual(지금['일하는중']['에이전트'], '수요 근거 에이전트')
        self.assertEqual(첫['기획id'], 둘['기획id'])
        self.assertTrue(둘['중복'])
        풀림.set()
        self.기다리기()
        p = self.서비스.상태(첫['기획id'])
        self.assertEqual(p['상태'], '멈춤')
        self.assertEqual(p['단계'][1]['상태'], '실패')
        self.assertIn('응답하지 않아 중단', p['안내'])   # 기다리기만 하지 않고 이유를 보여 줌

    def test_서버가_다시_켜지면_진행중은_중단됨으로_보인다(self):
        self.준비(lambda a, i: '', None)
        폴더 = Path(self.d.name) / '20260101_000000' / '01회차'
        폴더.mkdir(parents=True)
        (폴더 / 모듈.진행파일).write_text(json.dumps({'기획id': '20260101_000000/01회차', '상태': '진행중', '단계': []}), encoding='utf-8')
        self.assertEqual(self.서비스.상태('20260101_000000/01회차')['상태'], '중단됨')


if __name__ == '__main__':
    unittest.main()
