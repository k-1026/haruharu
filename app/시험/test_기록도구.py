import unittest
from app.공통 import 기획기록 as 기록모듈
from app.공통 import 기록도구


def record():
    r=기록모듈.새_기록({'체류기간':'당일','코스작성조건':{'시작일차':1,'종료일차':1,'시작지점':'A','종료지점':'B','시작시각':'10:00','종료시각':'18:00'}},'사람:담당자',기록id='t')
    코스={'칸목록':[{'안':'공통','칸ID':'낮','일차':1,'시간칸':'낮','장소명':'없는장소','시각':{'값':'11:00','종류':'가정'},'머무는시간':60}],'식사목록':[]}
    기록모듈.추가(r,'코스안',{'안id':'A','코스':코스},'코드:가져오기')
    return r


class 도구시험(unittest.TestCase):
    def test_점검하면_경고와_실행이_남음(self):
        r=record();n=len(r['경고'])
        out=기록도구.코스_점검(r,'A')
        self.assertIn('출발가능요일',out);self.assertIn('충돌',out['시간표']);self.assertIn('확인대기',out['시간표'])
        self.assertEqual(len(r['경고']),n+1);self.assertEqual(r['경고'][-1]['종류'],'코드점검')
        self.assertEqual(r['실행'][-1]['에이전트'],'코드:점검');self.assertEqual(r['실행'][-1]['AI호출'],0)

    def test_최신버전을_점검하고_버전표시(self):
        r=record();기록모듈.추가(r,'코스안',{'안id':'A','코스':{'칸목록':[],'식사목록':[]},'버전':2},'에이전트:코스')
        기록도구.코스_점검(r,'A');self.assertEqual(r['경고'][-1]['버전'],2)

    def test_없는_안id(self):
        with self.assertRaises(ValueError):기록도구.코스_점검(record(),'Z')


if __name__=='__main__':unittest.main()
