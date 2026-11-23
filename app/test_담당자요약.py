import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import 담당자요약


def course():
    return {'칸목록':[
        {'안':'공통','칸ID':'낮','일차':1,'시간칸':'낮','장소명':'대구광역시 중구 김광석길','시각':{'값':'11:30'}},
        {'안':'공통','칸ID':'점심','일차':1,'시간칸':'점심','장소명':'자유식 · 서문시장 권역','시각':{'값':'13:00'}},
        {'안':'공통','칸ID':'숙박','일차':1,'시간칸':'숙박','장소명':'숙박 권역','시각':{'값':''}}],
        '식사목록':[{'안':'공통','칸ID':'점심','방식':'자유식','권역':'서문시장','추천후보':['가게A','가게B']}]}


class 담당자요약시험(unittest.TestCase):
    def summary(self):
        with mock.patch.object(담당자요약,'좌표',side_effect=lambda n:(35.86,128.6) if '김광석길' in n else None):
            return 담당자요약.코스요약(course(),{'시작지점':'김광석길'})

    def test_칸목록_순서와_표시명(self):
        s=self.summary()
        self.assertTrue(s['코스있음'])
        self.assertEqual([x['순번'] for x in s['일정']],[1,2,3])
        self.assertEqual(s['일정'][0]['표시명'],'중구 김광석길')
        self.assertEqual(s['일정'][0]['좌표'],[35.86,128.6])
        self.assertTrue(s['일정'][0]['네이버'].startswith('https://map.naver.com/p/search/'))

    def test_자유식은_한점이고_좌표미확인(self):
        s=self.summary()
        self.assertEqual(s['일정'][1]['표시명'],'자유식 · 서문시장')
        self.assertIsNone(s['일정'][1]['좌표'])
        self.assertTrue(any('좌표 미확인' in x for x in s['확인할것']))

    def test_시각미정_칸은_확인할것(self):
        s=self.summary()
        self.assertEqual(s['일정'][2]['시각'],'')
        self.assertTrue(any('숙박' in x and '미정' in x for x in s['확인할것']))
        self.assertFalse(any('E7' in x or 'W1' in x for x in s['확인할것']))

    def test_결과파일_없으면_코스없음(self):
        class 저장소:
            def 파일(self,경로):raise ValueError('없음')
        class 서비스:
            pass
        svc=서비스();svc.저장소=저장소()
        s=담당자요약.요약_불러오기(svc,'x/01회차/통합시험_1')
        self.assertFalse(s['코스있음']);self.assertEqual(s['일정'],[])


if __name__=='__main__':unittest.main()
