import json
import tempfile
import unittest
from pathlib import Path
import 기획기록 as 기록모듈
import 처리기


def rec():
    return 기록모듈.새_기록({'계절':'봄'},'사람:담당자',기록id='t')


class 수집시험(unittest.TestCase):
    def test_출처있는_후보만_쓰고_나머지는_경고(self):
        r=rec()
        응답={'후보':[{'이름':'향촌문화관','출처ID':'S70','출처등급':'공식','내용':'월 휴관'},
                    {'이름':'가짜 야시장','출처ID':'','출처등급':'AI 생성'}],'못찾음':['평일 밤 야시장 없음']}
        n=처리기.수집하기(r,'평일 밤 후보',실행함수=lambda p,i:json.dumps(응답,ensure_ascii=False))
        self.assertEqual(n,1);self.assertEqual(len(r['후보']),1);self.assertEqual(r['후보'][0]['상태'],'후보')
        self.assertEqual(len(r['경고']),2);self.assertTrue(all(x['종류']=='수집' for x in r['경고']))


class 코스시험(unittest.TestCase):
    def test_새버전_코스안과_입력에_보완요청_후보(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);t=root/'r'/'01회차'/'통합시험_1';t.mkdir(parents=True)
            (t/'3단계_입력.json').write_text(json.dumps({'조건':{'계절':'봄'},'근거목록':[]},ensure_ascii=False),encoding='utf-8')
            r=rec();기록모듈.추가(r,'코스안',{'안id':'A','코스':{'칸목록':[]},'출처시험id':'r/01회차/통합시험_1'},'코드:가져오기')
            기록모듈.추가(r,'후보',{'이름':'향촌문화관'},'에이전트:수집');seen={}
            def fn(p,i):seen['p']=p;seen['i']=json.loads(i);return '{"칸목록":[{"칸ID":"낮"}]}'
            self.assertTrue(처리기.코스짜기(r,'A',root,['야시장 월~목 휴무'],실행함수=fn))
            self.assertEqual(len(r['코스안']),2);self.assertEqual(r['코스안'][-1]['버전'],2)
            self.assertEqual(seen['p'],'.claude/agents/코스검토.md')
            self.assertEqual(seen['i']['보완요청'],['야시장 월~목 휴무']);self.assertEqual(seen['i']['후보'][0]['이름'],'향촌문화관')
            self.assertEqual(seen['i']['조건'],{'계절':'봄'})

    def test_칸목록_없으면_실패(self):
        r=rec()
        self.assertFalse(처리기.코스짜기(r,'A',Path('.'),[],실행함수=lambda p,i:'{"설명":"x"}'))
        self.assertEqual(r['코스안'],[]);self.assertEqual(r['실행'][-1]['결과'],'실패')


class 검증시험(unittest.TestCase):
    def rec(self):
        r=rec();기록모듈.추가(r,'코스안',{'안id':'A','코스':{'칸목록':[]},'버전':1},'에이전트:코스');return r

    def test_통과면_성공(self):
        r=self.rec();out=처리기.검증하기(r,'A',실행함수=lambda p,i:'{"통과":true,"문제":[]}')
        self.assertTrue(out['통과']);self.assertEqual(r['실행'][-1]['결과'],'성공')

    def test_문제있으면_반려와_허용밖_되돌릴곳은_담당자(self):
        r=self.rec()
        응답={'통과':False,'문제':[{'종류':'운영','대상':'야시장','내용':'월~목 휴무','되돌릴곳':'수집'},
                                  {'종류':'표현','대상':'제목','내용':'단정','되돌릴곳':'홍보'}]}
        out=처리기.검증하기(r,'A',실행함수=lambda p,i:json.dumps(응답,ensure_ascii=False))
        self.assertFalse(out['통과']);self.assertEqual(r['실행'][-1]['결과'],'반려')
        ws=[x for x in r['경고'] if x['종류']=='검증']
        self.assertEqual([w['되돌릴곳'] for w in ws],['수집','담당자'])
        self.assertTrue(all(w['안id']=='A' and w['버전']==1 for w in ws))

    def test_응답실패면_오류표시(self):
        out=처리기.검증하기(self.rec(),'A',실행함수=lambda p,i:'x')
        self.assertTrue(out.get('오류'));self.assertFalse(out['통과'])


if __name__=='__main__':unittest.main()
