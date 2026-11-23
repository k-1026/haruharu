import json
import unittest
from pathlib import Path
import 기획기록 as 기록모듈
import 총괄


def rec():
    return 기록모듈.새_기록({'체류기간':'당일','코스작성조건':{}},'사람:담당자',기록id='t')


def 코스(r,v):
    기록모듈.추가(r,'코스안',{'안id':'A','코스':{'칸목록':[],'식사목록':[]},'버전':v},'에이전트:코스')


class 규칙시험(unittest.TestCase):
    def test_코스없으면_코스(self):
        self.assertEqual(총괄.다음_할일(rec())['행동'],'코스')

    def test_점검없으면_점검_있으면_검증(self):
        r=rec();코스(r,1);self.assertEqual(총괄.다음_할일(r)['행동'],'점검')
        기록모듈.추가(r,'경고',{'종류':'코드점검','안id':'A','버전':1},'코드:점검')
        self.assertEqual(총괄.다음_할일(r)['행동'],'검증')

    def test_반려_수집이면_수집_뒤에_코스(self):
        r=rec();코스(r,1);기록모듈.추가(r,'경고',{'종류':'코드점검','안id':'A','버전':1},'코드:점검')
        기록모듈.실행_기록(r,'에이전트:검증','검증','A','x','반려')
        기록모듈.추가(r,'경고',{'종류':'검증','안id':'A','버전':1,'되돌릴곳':'수집','문구':'평일 밤 후보 없음'},'에이전트:검증')
        기록모듈.추가(r,'경고',{'종류':'검증결과','안id':'A','버전':1,'통과':False},'에이전트:검증')
        d=총괄.다음_할일(r);self.assertEqual(d['행동'],'수집');self.assertIn('평일 밤',d['대상'])
        기록모듈.실행_기록(r,'에이전트:수집','수집','평일 밤','x','성공')
        self.assertEqual(총괄.다음_할일(r)['행동'],'코스')

    def test_반려_담당자면_담당자에게_통과도_담당자에게(self):
        r=rec();코스(r,1)
        기록모듈.추가(r,'경고',{'종류':'검증','안id':'A','버전':1,'되돌릴곳':'담당자','문구':'?'},'에이전트:검증')
        기록모듈.추가(r,'경고',{'종류':'검증결과','안id':'A','버전':1,'통과':False},'에이전트:검증')
        self.assertEqual(총괄.다음_할일(r)['행동'],'담당자에게')
        r=rec();코스(r,1);기록모듈.추가(r,'경고',{'종류':'검증결과','안id':'A','버전':1,'통과':True},'에이전트:검증')
        self.assertEqual(총괄.다음_할일(r)['행동'],'담당자에게')


class 돌리기시험(unittest.TestCase):
    def test_모의흐름_되돌아갔다가_통과(self):
        r=rec();steps=총괄.돌리기(r,Path('.'),실행함수=총괄.모의응답())
        self.assertEqual([s['행동'] for s in steps],['코스','점검','검증','수집','코스','점검','검증','담당자에게'])
        self.assertEqual(r['결정이력'][-1]['행동'],'담당자에게')
        self.assertEqual(len(r['후보']),1)

    def test_계속반려면_한도로_멈춤(self):
        def fn(p,i):
            if p.endswith('코스검토.md'):return '{"칸목록":[]}'
            return json.dumps({'통과':False,'문제':[{'종류':'운영','대상':'x','내용':'y','되돌릴곳':'코스'}]},ensure_ascii=False)
        r=rec();steps=총괄.돌리기(r,Path('.'),실행함수=fn)
        self.assertLessEqual(len(steps),12);self.assertEqual(steps[-1]['행동'],'담당자에게')
        self.assertIn('한도',steps[-1]['이유'])


if __name__=='__main__':unittest.main()
