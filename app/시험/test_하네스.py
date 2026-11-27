"""하네스 채점·돌리기를 가짜 AI로 시험한다 (토큰 0)."""
import json
from pathlib import Path
import tempfile
import unittest

from app.하네스.채점 import 채점
from app.하네스 import 돌리기 as 하네스


def _쓰기(폴더, 이름, 값):
    (Path(폴더) / 이름).write_text(json.dumps(값, ensure_ascii=False), encoding='utf-8')


def _칸(id, 시간칸, 장소명, 일차=1):
    return {'칸ID': id, '일차': 일차, '시간칸': 시간칸, '장소명': 장소명}


def _폴더(코스, 치킨선택='', 초=20.0, 충돌=()):
    d = tempfile.mkdtemp()
    _쓰기(d, '통합시험_상태.json', {'상태': '초안생성'})
    _쓰기(d, '3단계_크기.json', {'받은글자': 7000, '쓴글자': 1200, '경과초': 초})
    _쓰기(d, '3단계_전달_검사.json', {'형식검사': ['통과'], '시간표검사': {'충돌': list(충돌)}})
    _쓰기(d, '3단계_후보표.json', {'장소': {'P1': {'장소명': '대구광역시 중구 근대골목'},
                                        'P2': {'장소명': '대구광역시 중구 서문시장'},
                                        'P3': {'장소명': '대구광역시 중구 A치킨 (치킨 옵션)'}}})
    _쓰기(d, '3단계_구조화.json', 코스)
    return d, {'확정체류기간': '1박2일', '코스작성조건': {'치킨선택': 치킨선택}}


def _코스(A, B=None, 이유=''):
    return {'칸목록': A, '대안제안': {'코스': {'칸목록': B}} if B else None, '대안불가이유': 이유, '체크리스트': []}


기본A = [_칸('낮-1', '낮', '대구광역시 중구 근대골목'), _칸('점심-1', '점심', '대구광역시 중구 서문시장'),
       _칸('숙박-1', '숙박', '숙소 (중구 도심, 업체 미고정)')]


def _결과(점수):
    return {h['항목']: h['결과'] for h in 점수['항목']}


class 채점시험(unittest.TestCase):
    def test_규칙을_지킨_코스는_모두_통과(self):
        d, 입력 = _폴더(_코스(기본A, 기본A[:2]))
        점수 = 채점(d, 입력)
        self.assertTrue(점수['전체통과'], 점수['항목'])

    def test_60초_넘으면_시간_실패(self):
        d, 입력 = _폴더(_코스(기본A, 기본A[:2]), 초=61)
        self.assertEqual(_결과(채점(d, 입력))['시간(60초 이하)'], '실패')

    def test_치킨_미선택인데_치킨이면_실패(self):
        A = 기본A + [_칸('저녁-1', '저녁', '대구광역시 중구 A치킨 (치킨 옵션)')]
        d, 입력 = _폴더(_코스(A, 기본A[:2]))
        self.assertEqual(_결과(채점(d, 입력))['치킨(담당자 선택 시 저녁 1번까지)'], '실패')
        d, 입력 = _폴더(_코스(A, 기본A[:2]), 치킨선택='선택')
        self.assertEqual(_결과(채점(d, 입력))['치킨(담당자 선택 시 저녁 1번까지)'], '통과')

    def test_조립되어_치킨표시가_빠져도_치킨으로_센다(self):
        A = 기본A + [_칸('저녁-1', '저녁', '대구광역시 중구 A치킨')]
        d, 입력 = _폴더(_코스(A, 기본A[:2]), 치킨선택='선택')
        r = _결과(채점(d, 입력))
        self.assertEqual(r['치킨 선택 시 저녁 후보에 치킨 보임'], '통과')
        self.assertEqual(r['치킨(담당자 선택 시 저녁 1번까지)'], '통과')

    def test_낮_치킨은_실패(self):
        A = 기본A + [_칸('점심-2', '점심', '대구광역시 중구 A치킨 (치킨 옵션)', 2)]
        d, 입력 = _폴더(_코스(A, 기본A[:2]), 치킨선택='선택')
        r = _결과(채점(d, 입력))
        self.assertEqual(r['낮 치킨 식사 없음'], '실패')

    def test_후보표_밖_장소_숙박없음_B없음_충돌(self):
        A = [_칸('낮-1', '낮', '대구광역시 중구 지어낸장소')]
        d, 입력 = _폴더(_코스(A), 충돌=['저녁 운영시간 밖'])
        r = _결과(채점(d, 입력))
        self.assertEqual(r['후보표 밖 장소 없음'], '실패')
        self.assertEqual(r['1박2일 숙박 칸'], '실패')
        self.assertEqual(r['A/B 둘 다(또는 B 불가 이유)'], '실패')
        self.assertEqual(r['휴무·운영시간·시간 충돌 없음'], '실패')

    def test_B_불가_이유가_있으면_통과(self):
        d, 입력 = _폴더(_코스(기본A, 이유='후보가 부족함'))
        self.assertEqual(_결과(채점(d, 입력))['A/B 둘 다(또는 B 불가 이유)'], '통과')


class 돌리기시험(unittest.TestCase):
    def test_엉뚱한_답이면_형식_실패로_기록(self):
        with tempfile.TemporaryDirectory() as d:
            표 = 하네스.돌리기(실행함수=lambda 지침, 글: '답 없음', 결과위치=d)
            r = 표['회차'][0]
            self.assertEqual(_결과(r)['형식(조립·형식 검사)'], '실패')
            self.assertTrue(list(Path(d).glob('점수표_*.md')))

    def test_시간초과는_오류와_함께_실패로_기록(self):
        async def 느림(지침, 글):
            raise TimeoutError('AI가 제한 시간 안에 응답하지 않음')
        with tempfile.TemporaryDirectory() as d:
            표 = 하네스.돌리기(실행함수=느림, 결과위치=d, 반복=2)
            r = 표['회차'][0]
            self.assertEqual(r['상태'], '실행실패')
            self.assertEqual(_결과(r)['시간(60초 이하)'], '실패')
            self.assertTrue(r['오류'])
            self.assertEqual(표['요약']['항목']['시간(60초 이하)'], '0/2')


if __name__ == '__main__':
    unittest.main()


예전답 = (Path(__file__).resolve().parents[1] / '하네스/시험상황/고정입력/일본인커플_중구_가을_1박2일_4단계/예전_AI결과_20261126.md')
홍보상황 = '일본인커플_중구_가을_1박2일_홍보'


class 홍보하네스시험(unittest.TestCase):
    def _돌리기(self, 답):
        with tempfile.TemporaryDirectory() as d:
            return _결과(하네스.돌리기(홍보상황, 실행함수=lambda 에이전트, 요청: 답, 결과위치=d)['회차'][0])

    def test_예전_실제답은_통과(self):
        r = self._돌리기(예전답.read_text(encoding='utf-8'))
        self.assertTrue(all(v == '통과' for v in r.values()), r)

    def test_금지표현과_내부표시는_실패(self):
        답 = 예전답.read_text(encoding='utf-8').replace('골목을 천천히 걸으며', '대구 최고의 골목 R53을 걸으며', 1)
        r = self._돌리기(답)
        self.assertEqual(r['금지 표현 없음'], '실패')
        self.assertEqual(r['공개 문구에 내부 표시 없음'], '실패')

    def test_엉뚱한_답은_두번_부르고_실패(self):
        with tempfile.TemporaryDirectory() as d:
            회 = 하네스.돌리기(홍보상황, 실행함수=lambda a, b: '답 없음', 결과위치=d)['회차'][0]
        self.assertEqual(_결과(회)['형식·참조 검사(제품 홍보_검사)'], '실패')
        self.assertIn('2회', _결과(회) and next(h['메모'] for h in 회['항목'] if h['항목'].startswith('시간')))

    def test_시간초과는_실패로_기록(self):
        def 느림(a, b):
            raise TimeoutError('응답 없음')
        with tempfile.TemporaryDirectory() as d:
            회 = 하네스.돌리기(홍보상황, 실행함수=느림, 결과위치=d)['회차'][0]
        self.assertEqual(회['상태'], '실패')
        self.assertEqual(_결과(회)['시간(호출마다 420초 이하)'], '실패')


class 수요산출물하네스시험(unittest.TestCase):
    def test_2단계_근거_밖_숫자는_실패(self):
        with tempfile.TemporaryDirectory() as d:
            회 = 하네스.돌리기('일본인커플_중구_가을_1박2일_수요', 결과위치=d,
                         실행함수=lambda a, b: '```json\n{"요약": "일본인 방문객이 987654명으로 늘었다."}\n```')['회차'][0]
        r = _결과(회)
        self.assertEqual(r['요약에 근거 밖 숫자 없음'], '실패')
        self.assertEqual(r['기관 자료 반영(가상설문 행 적용)'], '통과')
        self.assertEqual(r['시간(요약 30초 이하)'], '통과')

    def test_2단계_엉뚱한_답은_형식_실패(self):
        with tempfile.TemporaryDirectory() as d:
            회 = 하네스.돌리기('일본인커플_중구_가을_1박2일_수요', 결과위치=d, 실행함수=lambda a, b: '답 없음')['회차'][0]
        self.assertEqual(_결과(회)['형식(요약 읽힘 · 3단계 전달 검사 통과)'], '실패')

    def test_5단계_고정_결과는_통과(self):
        with tempfile.TemporaryDirectory() as d:
            회 = 하네스.돌리기('일본인커플_중구_가을_1박2일_산출물', 결과위치=d)['회차'][0]
        self.assertTrue(회['전체통과'], 회['항목'])
