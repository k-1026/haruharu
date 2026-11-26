"""공개 결과와 내부 검토 기록의 경계를 확인한다. 실제 AI를 호출하지 않는다."""
import copy
import json
import unittest

from app.시험.test_홍보실행 import 코스, 입력2, 가짜홍보
from app.단계5_산출물.산출물 import 묶기, 결재파일, 제안서, 홍보물묶음
from app.단계4_홍보검토.디자인 import 만들기, 랜딩


class 공개자료시험(unittest.TestCase):
    def test_식사권역은_유지하되_미선택_식당을_확정방문지로_쓰지않는다(self):
        from app.단계5_산출물.공개자료 import 식사권역
        self.assertEqual(식사권역({'방식':'미선택','권역':'식사 방식 미선택 · 권역 후보: 대구광역시 중구 서문시장','추천후보':[]}), '대구광역시 중구 서문시장')
        self.assertEqual(식사권역({'방식':'미선택','권역':'식사 방식 미선택 · 권역 후보: 대구광역시 중구 산호찜갈비','추천후보':['대구광역시 중구 산호찜갈비']}), '중구 자유식')

    def bundle(self):
        promo = json.loads(가짜홍보()('', '입력 JSON:\n' + json.dumps({'확정코스':코스(), '담당자선택':{'코스이름':'골목 여행'}})).split('```json\n')[1].split('```')[0])
        promo['문구목록'][0]['본문'] = '골목을 걸어요. [미확인: 운영시간]'
        return 묶기(입력2()['조건'], 입력2(), 코스(), promo, {'코스이름':'골목 여행','홍보물':['SNS 카드뉴스','포스터'],'톤앤매너':'A'})

    def test_공개화면과_SVG는_검토정보를_제외하고_원본을_보존한다(self):
        b = self.bundle(); original = copy.deepcopy(b)
        for page in 만들기(b, 'http://localhost/tour?c=test'):
            for unwanted in ['근거:', '검토 초안', '남은 경고', '미확인', 'AI 초안', '식비 포함']:
                self.assertNotIn(unwanted, page['svg'])
        page = 랜딩(b, 'test')
        data = json.loads(page.split('const COURSE = ',1)[1].split(';\nconst PLACES',1)[0])
        self.assertNotIn('warnings', data)
        self.assertNotIn('R01', json.dumps(data))
        self.assertNotIn('미확인', json.dumps(data,ensure_ascii=False))
        self.assertNotIn('warningBox', page)
        self.assertEqual(data['places'][0]['원본장소'], original['시간표'][0]['장소'])
        self.assertEqual(b, original)

    def test_제출파일에는_검토기록이_없고_내부묶음에는_남는다(self):
        b = self.bundle()
        b['운영주체후보'].append('O7 시장 상인회 (이름 [U])')
        original = copy.deepcopy(b)
        for render in [결재파일, 제안서, 홍보물묶음]:
            page = render(b)
            for unwanted in ['남은 경고', '미확인', '[U]', '초안 · 담당자 검토 전', '표현 필터 기록', '식비 포함', 'R01', 'W1']:
                self.assertNotIn(unwanted, page, render.__name__)
            self.assertIn('개별 결제', page)
        self.assertEqual(b, original)
        self.assertTrue(b['남은경고'])

    def test_포함_문구도_제공하지않는_서비스로_안내하지않는다(self):
        from app.단계5_산출물.공개자료 import 공개묶음
        b=self.bundle();b['장면'][0]['문구']['본문']='식사 포함 상품입니다. 골목을 걸어요.'
        b['코스카드']['식사안내']='식비 포함'
        out=공개묶음(b)
        self.assertNotIn('식사 포함',out['장면'][0]['문구']['본문'])
        self.assertEqual(out['장면'][0]['번역'],[])
        self.assertEqual(out['장면'][0]['번역'],[])
        self.assertIn('개별 결제',out['코스카드']['식사안내'])

    def test_미정장소와_운영미확인_장면은_번역까지_함께_제외한다(self):
        from app.단계5_산출물.공개자료 import 공개묶음, 공개내보내기
        b=self.bundle()
        b['시간표'][0]['장소']='[미확인: 숙소]'
        b['장면'][0]['장소']='[미확인: 숙소]'
        b['대응표'][0]['장소']='[미확인: 숙소]'
        b['남은경고'].append({'경고':'[미확인] 운영시간','대상':'저녁-1 운영 자료 없음'})
        b['장면'][1]['문구']['본문']='오후 6시 입장 가능합니다.'
        original=copy.deepcopy(b)
        out=공개묶음(b)
        self.assertEqual(len(out['시간표']),1)
        self.assertEqual(len(out['장면']),1)
        self.assertEqual(out['장면'][0]['문구']['본문'],'')
        self.assertEqual(out['장면'][0]['번역'],[])
        self.assertNotIn('미확인',json.dumps(공개내보내기(b),ensure_ascii=False))
        self.assertNotIn('미확인',결재파일(b))
        self.assertEqual(b,original)


if __name__ == '__main__':
    unittest.main()
