import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from app.서버 import 담당자요약


def course():
    return {'칸목록':[
        {'안':'공통','칸ID':'낮','일차':1,'시간칸':'낮','장소명':'대구광역시 중구 김광석길','시각':{'값':'11:30'}},
        {'안':'공통','칸ID':'점심','일차':1,'시간칸':'점심','장소명':'자유식 · 서문시장 권역','시각':{'값':'13:00'}},
        {'안':'공통','칸ID':'숙박','일차':1,'시간칸':'숙박','장소명':'숙박 권역','시각':{'값':''}}],
        '식사목록':[{'안':'공통','칸ID':'점심','방식':'자유식','권역':'서문시장','추천후보':['가게A','가게B']}]}


class 담당자요약시험(unittest.TestCase):
    def test_종료시각과_체류분을_계산없이_그대로_전달하고_원본을_보존한다(self):
        import copy
        c={'칸목록':[{'일차':1,'장소명':'관광지','시각':{'값':'10:00'},
                    '종료일차':1,'종료시각':{'값':'11:00'},'머무는시간':60},
                   {'일차':2,'장소명':'미정 장소','시각':{'값':'','종류':'미정'},'머무는시간':45}]}
        before=copy.deepcopy(c)
        rows=담당자요약.코스요약(c,{})['일정']
        self.assertEqual((rows[0]['시각'],rows[0]['종료시각'],rows[0]['머무는시간']),('10:00','11:00',60))
        self.assertEqual(rows[0]['종료일차'],1)
        self.assertEqual(rows[1]['종료시각'],'')
        self.assertEqual(rows[1]['머무는시간'],45)
        self.assertEqual(c,before)

    def test_같은날_다음장소_이동안내를_저장변경없이_연결한다(self):
        import copy
        c={'칸목록':[{'일차':1,'장소명':'서문시장'},{'일차':1,'장소명':'김광석길'},
                         {'일차':2,'장소명':'평화시장 닭똥집골목'}]}
        before=copy.deepcopy(c);result=담당자요약.코스요약(c,{})
        self.assertEqual(result['일정'][0]['다음이동']['대중교통분'],20)
        self.assertNotIn('다음이동',result['일정'][1])
        self.assertEqual(c,before)

    def test_야시장소개와_자료기준_이용정보를_원본변경없이_제공한다(self):
        c={'칸목록':[{'일차':1,'시간칸':'밤','장소명':'서문시장 야시장 (대구광역시 중구)'}]}
        result=담당자요약.코스요약(c,{})['일정'][0]['장소안내']
        self.assertIn('야시장',result['소개'])
        self.assertEqual(result['이용시간'],'19:00-23:00')
        self.assertTrue(result['출처URL'].startswith('https://'))
        self.assertNotIn('장소안내',c['칸목록'][0])
    def test_대표좌표로_동선을_연결해도_입구나_호텔을_확정하지않는다(self):
        import copy
        names=['근대골목','서문시장','김광석길','평화시장 닭똥집골목 (대구광역시 동구) — 희망 반영','서문시장 야시장',
               '숙소 (중구 동성로 일대 호텔 후보 권역, 업체 미고정)','']
        slots=['낮','점심','낮오후','저녁','밤','숙박','2일차오전']
        c={'칸목록':[{'순번':i+1,'일차':1 if i<6 else 2,'시간칸':slot,'장소명':name} for i,(name,slot) in enumerate(zip(names,slots))]}
        c['칸목록'][3]['칸ID']='저녁-1'
        c['식사목록']=[{'칸ID':'저녁-1','방식':'미선택','권역':'동구 평화시장 일대 (평화시장 닭똥집골목, 희망-1)'}]
        before=copy.deepcopy(c);s=담당자요약.코스요약(c,{})
        self.assertTrue(all(row['좌표'] for row in s['일정'][:6]))
        self.assertIsNone(s['일정'][6]['좌표'])
        self.assertTrue(s['일정'][1]['식사권역'])
        self.assertFalse(s['일정'][5]['식사권역'])
        self.assertIn('대표',s['일정'][0]['위치설명'])
        self.assertIn('업체',s['일정'][5]['위치설명'])
        self.assertEqual(c,before)
    def test_자유식후보는_선택없이_별도지도위치로_반환한다(self):
        c=course();c['식사목록'][0]['추천후보']=['가게A','가게B']
        with mock.patch.object(담당자요약,'좌표',side_effect=lambda n:(35.87,128.60) if n=='가게A' else None):
            result=담당자요약.코스요약(c,{})
        meal=result['일정'][1]
        self.assertIsNone(meal['좌표'])
        self.assertEqual(meal['식당후보'][0]['좌표'],[35.87,128.60])
        self.assertIsNone(meal['식당후보'][1]['좌표'])
        self.assertNotIn('선택',c)

    def test_명시적으로_제외한_후보는_지도자료에서_제거한다(self):
        c=course();c['운영검토기록']={'운영확인':[{'안':'공통','칸ID':'점심','대상명':'가게A','처리':'제외'}]}
        result=담당자요약.코스요약(c,{})
        self.assertEqual([x['이름'] for x in result['일정'][1]['식당후보']],['가게B'])

    def summary(self):
        with mock.patch.object(담당자요약,'좌표',side_effect=lambda n:(35.86,128.6) if '김광석길' in n else None):
            return 담당자요약.코스요약(course(),{'시작지점':'김광석길'})

    def test_칸목록_순서와_표시명(self):
        s=self.summary()
        self.assertTrue(s['코스있음'])
        self.assertEqual([x['순번'] for x in s['일정']],[1,2,3])
        self.assertEqual(s['일정'][0]['표시명'],'중구 김광석길')
        self.assertEqual(s['일정'][0]['좌표'],[35.86,128.6])
        self.assertTrue(s['일정'][0]['지도링크'].startswith('https://map.kakao.com/link/map/'))
        self.assertTrue(s['일정'][0]['지도링크'].endswith(',35.86,128.6'))

    def test_자유식은_한점이고_좌표미확인(self):
        s=self.summary()
        self.assertEqual(s['일정'][1]['표시명'],'자유식 · 서문시장')
        self.assertIsNone(s['일정'][1]['좌표'])
        self.assertIsNone(s['일정'][1]['지도링크'])  # 좌표가 없으면 링크도 만들지 않는다
        # 자유식은 권역이라 좌표 확인 대상이 아니다.
        self.assertFalse(any('좌표 미확인' in x for x in s['확인할것']))

    def test_장소명이_자유식이면_식사목록없어도_자유식_괄호설명은_뺌(self):
        c={'칸목록':[{'칸ID':'저녁','일차':1,'시간칸':'저녁','장소명':'자유식 · 대구광역시 중구 (추천 후보: 가게A)','시각':{'값':'19:00'}},
                   {'칸ID':'밤','일차':1,'시간칸':'밤','장소명':'대구광역시 중구 서문시장 야시장 (금·토·일만)','시각':{'값':'20:00'}}]}
        with mock.patch.object(담당자요약,'좌표',return_value=None):
            s=담당자요약.코스요약(c,{})
        self.assertEqual(s['일정'][0]['표시명'],'자유식 · 중구')
        self.assertEqual(s['일정'][1]['표시명'],'중구 서문시장 야시장')
        self.assertFalse(any('자유식' in x for x in s['확인할것']))

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

    def test_실제_AI처럼_앞말과_json블록이_붙어도_읽는다(self):
        글={'x/3단계_결과.md':'지침 파일을 먼저 읽겠습니다.\n```json\n{"칸목록":[{"칸ID":"낮","장소명":"향촌문화관","일차":1,"시간칸":"낮"}],"식사목록":[]}\n```',
           'x/3단계_입력.json':'{"코스작성조건":{}}'}
        class 저장소:
            def 파일(self,경로):return {'본문':글[경로]}
        class 서비스:
            pass
        svc=서비스();svc.저장소=저장소()
        s=담당자요약.요약_불러오기(svc,'x')
        self.assertTrue(s['코스있음']);self.assertEqual(s['일정'][0]['표시명'],'향촌문화관')


if __name__=='__main__':unittest.main()
