"""실제 저장 응답의 B 누락 형태를 재현한다. 외부 AI 호출 없음."""
import copy
import json
import unittest
from tempfile import TemporaryDirectory

import 기획기록 as 기록
import 대안비교


class 보완시험(unittest.TestCase):
    def 준비(self):
        r = 기록.새_기록({'계절':'가을','언어권':['일본어'],'지역':['중구'],'체류기간':'1박2일'},
                       '사람:담당자', '일본인 커플', 기록id='demo')
        r['실행정책']={'모드':'자율이용','대안비교':True}
        a={'칸목록':[{'일차':1,'시간칸':'낮','장소명':'대구광역시 중구 근대골목'},
                     {'일차':2,'시간칸':'오전','장소명':'대구광역시 중구 향촌문화관'}]}
        기록.추가(r,'코스안',{'안id':'A','코스':a},'에이전트:코스')
        대안비교.등록(r,None,'')
        return r,a

    def test_누락시_B만_한번_보완하고_A와_조건을_보존(self):
        r,a=self.준비();before=copy.deepcopy(a);calls=[]
        b=copy.deepcopy(a);b['칸목록'][0]['장소명']='대구광역시 중구 서문시장'
        def ai(path,text):
            calls.append(json.loads(text))
            return json.dumps({'대안제안':{'코스':b,'이유':'시장 중심으로 이동 축소','무엇을':'첫날 낮 관광 변경'}})
        with TemporaryDirectory() as root:
            self.assertTrue(대안비교.보완(r,root,ai))
            대안비교.보완(r,root,ai)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['조건']['지역'],['중구'])
        self.assertEqual(calls[0]['원래요청']['목표'],'일본인 커플')
        self.assertEqual(a,before)
        self.assertEqual(r['대안상태']['상태'],'생성')

    def test_만들수없다는_이유를_보존하고_반복하지않음(self):
        r,_=self.준비();calls=[]
        def ai(*args):
            calls.append(1);return '{"대안제안":null,"대안불가이유":"중구 안에서 확인된 대체 후보가 부족합니다."}'
        with TemporaryDirectory() as root:
            self.assertFalse(대안비교.보완(r,root,ai))
            대안비교.보완(r,root,ai)
        self.assertEqual(len(calls),1)
        self.assertIn('후보가 부족',r['대안상태']['이유'])
        self.assertEqual(len(r['코스안']),1)

    def test_중구밖이나_둘째날이없는_보완안은_거절(self):
        for name,day in [('대구광역시 동구 평화시장',True),('대구광역시 중구 서문시장',False)]:
            r,a=self.준비();b=copy.deepcopy(a);b['칸목록'][0]['장소명']=name
            if not day:b['칸목록']=b['칸목록'][:1]
            with TemporaryDirectory() as root:
                self.assertFalse(대안비교.보완(r,root,lambda *args:json.dumps({'대안제안':{'코스':b,'이유':'조정'}})))
            self.assertTrue(r['대안상태']['이유'])

    def test_연결실패도_이유가_남고_A는_볼수있음(self):
        r,_=self.준비()
        def ai(*args):raise ValueError('연결 실패')
        with TemporaryDirectory() as root:self.assertFalse(대안비교.보완(r,root,ai))
        self.assertIn('실패',r['대안상태']['이유'])
        self.assertEqual(len(r['코스안']),1)
