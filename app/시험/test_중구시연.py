"""중구 MVP 범위를 A/B안·부분 수정에서도 지킨다. 실제 AI 호출 없음."""
import json
import unittest
from pathlib import Path

from app.공통 import 기획기록
from app.단계3_코스검토 import 처리기


def 주문(*칸들, 식사=()):
    return json.dumps({'안': {'칸': [{'칸ID': id, '일차': d, '시간칸': t, '장소': p, '머무는분': 60, '근거': [], '운영': [], '이유': ''}
                                    for id, d, t, p in 칸들], '식사': list(식사)}}, ensure_ascii=False)


class 중구시연시험(unittest.TestCase):
    def record(self):
        return 기획기록.새_기록(
            {'계절': '가을', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'},
            '사람:담당자', '일본인 커플의 저녁·숙박 연계', 기록id='jungu_demo', 희망=['저녁에 야경을 보고 싶어요'])

    def test_원안과_대안은_선택한_지역과_설문음식근거를_받는다(self):
        r = self.record()
        기획기록.안_추가(r, 'B', '야경보다 여유로운 식사', '에이전트:총괄',
                     바꾼희망={'희망-1': '여유로운 저녁 식사'}, 이유='야경 일정의 운영 정보 부족')
        for plan in ['A', 'B']:
            data = 처리기.코스입력(r, plan, Path('.'), [])
            self.assertEqual(data['조건']['지역'], ['중구'])
            self.assertIn('필수조건반영', ' '.join(data['출력추가']))
            self.assertIn('치킨은 필수', data['저녁기획원칙'])
            food = data['저녁음식근거']
            japan = {x['음식']: x for x in food if x['대상'] == '일본'}
            self.assertEqual(japan['닭튀김/치킨']['비율'], '1.7')
            self.assertEqual(japan['불고기']['표본수'], '83.0')
            self.assertTrue(all(x['출처파일'].endswith('대구_외국인추천음식상위20_2024.csv') for x in food))

    def test_중구안에_동구장소를_주문하면_코스를_만들지_않고_이유를_남긴다(self):
        # 주문서 방식: 동구 장소는 후보표에 없어 AI가 고를 수 없다. 번호를 지어내면 조립하지 않는다.
        r = self.record()
        self.assertFalse(처리기.코스짜기(r, 'A', Path('.'), [], lambda p, i: 주문(('저녁-1', 1, '저녁', 'P8'))))
        self.assertEqual(r['코스안'], [])
        self.assertIn('후보표에 없는 장소 P8', r['실행'][-1]['이유'])

    def test_중구만_고르면_후보표에_동구장소가_없다(self):
        본 = {}
        def fn(p, i):
            본['i'] = json.loads(i); return 주문(('낮-1', 1, '낮', 'P1'))
        r = self.record()
        self.assertTrue(처리기.코스짜기(r, 'A', Path('.'), [], fn))
        self.assertNotIn('동구', 본['i']['후보표'].split('# 이동')[0])
        region = next(x for x in 처리기.최신안(r, 'A')['코스']['필수조건반영'] if x['조건'] == '지역')
        self.assertEqual(region['반영'], '지킴')

    def test_부분수정도_후보표밖이면_막고_이전버전은_보존한다(self):
        r = self.record()
        original = {'칸목록': [{'칸ID': '낮', '일차': 1, '시간칸': '낮', '장소명': '근대골목'},
                            {'칸ID': '저녁', '일차': 1, '시간칸': '저녁', '장소명': '산호찜갈비'}]}
        기획기록.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': original}, '에이전트:코스')
        self.assertFalse(처리기.부분수정(r, 'A', Path('.'), ['낮'], ['저녁'], '저녁만 바꿔 줘', lambda p, i: 주문(('저녁', 1, '저녁', 'P8'))))
        self.assertEqual(original['칸목록'][1]['장소명'], '산호찜갈비')
        self.assertEqual(기획기록.버전목록(r, 'A'), [1])   # 이전 버전 보존, 새 버전 없음

    def test_동구를_고른_기존기능은_계속_허용한다(self):
        r = self.record()
        r['조건']['지역'] = ['중구', '동구']
        # 치킨을 고른 동구 포함 기획이면 평화시장(P8)이 후보표에 들어가 주문할 수 있다
        self.assertTrue(처리기.코스짜기(r, 'A', Path('.'), [], lambda p, i: 주문(('저녁-1', 1, '저녁', 'P8')),
                                     추가입력={'코스작성조건': {'치킨선택': '선택'}}))
        region = next(x for x in 처리기.최신안(r, 'A')['코스']['필수조건반영'] if x['조건'] == '지역')
        self.assertEqual(region['반영'], '지킴')

    def test_처음부터_가져온_코스도_지역위반을_AI수정으로_분류한다(self):
        from app.공통 import 검사분류
        r = self.record()
        기획기록.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': {
            '칸목록': [{'칸ID': '저녁', '일차': 1, '시간칸': '저녁', '장소명': '평화시장 닭똥집골목'}]}}, '코드:가져오기')
        groups = 검사분류.안_검사(r, 'A')
        self.assertTrue(any('필수 조건 지역' in x['문구'] for x in groups['AI수정']))

    def test_B안_식당후보가_동구이면_조립하지_않는다(self):
        r = self.record()
        기획기록.안_추가(r, 'B', '식사 위주', '에이전트:총괄', 바꾼희망={'희망-1': '식사 위주'}, 이유='야경 운영 미확인')
        # 식사 추천후보에 동구 장소 번호를 넣어도 후보표 밖이라 조립하지 않는다
        글 = 주문(('저녁-1', 1, '저녁', 'P2'), 식사=[{'칸ID': '저녁-1', '방식': '자유식', '권역': 'P2', '후보': ['P8']}])
        self.assertFalse(처리기.코스짜기(r, 'B', Path('.'), [], lambda p, i: 글))
        self.assertIn('후보표에 없는 식사 후보 P8', r['실행'][-1]['이유'])
        self.assertEqual(r['조건']['지역'], ['중구'])

    def test_자료에_없는_장소를_중구라고_추정하지_않는다(self):
        from app.단계1_기획조건.기획기준 import 지역반영
        report = 지역반영({'칸목록': [{'장소명': '확인하지 않은 새 식당'}]}, self.record()['조건'])
        self.assertEqual(report['반영'], '미확인')
        self.assertIn('자료가 부족', report['이유'])


if __name__ == '__main__':
    unittest.main()
