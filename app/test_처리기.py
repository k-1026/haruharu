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
            def fn(p,i):
                seen['p']=p;seen['i']=json.loads(i)
                return '{"안":{"칸":[{"칸ID":"낮-1","일차":1,"시간칸":"낮","장소":"P1","머무는분":60,"근거":[],"운영":[],"이유":""}],"식사":[]}}'
            self.assertTrue(처리기.코스짜기(r,'A',root,['야시장 월~목 휴무'],실행함수=fn))
            self.assertEqual(len(r['코스안']),2);self.assertEqual(r['코스안'][-1]['버전'],2)
            self.assertEqual(seen['p'],'.claude/agents/코스주문.md')
            self.assertIn('P1|근대골목',seen['i']['후보표'])
            self.assertIn('체크리스트',r['코스안'][-1]['코스'])
            self.assertEqual(seen['i']['보완요청'],['야시장 월~목 휴무']);self.assertEqual(seen['i']['후보'][0]['이름'],'향촌문화관')
            self.assertEqual(seen['i']['조건'],{'계절':'봄'})

    def test_칸목록_없으면_실패(self):
        r=rec()
        self.assertFalse(처리기.코스짜기(r,'A',Path('.'),[],실행함수=lambda p,i:'{"설명":"x"}'))
        self.assertEqual(r['코스안'],[]);self.assertEqual(r['실행'][-1]['결과'],'실패')


class 부분수정시험(unittest.TestCase):
    def test_부분수정은_유지칸_시각을_고정한다(self):
        r=rec()
        첫={'안':{'칸':[{'칸ID':'낮-1','일차':1,'시간칸':'낮','장소':'P1','머무는분':90,'근거':[],'운영':[],'이유':''},
                     {'칸ID':'저녁-1','일차':1,'시간칸':'저녁','장소':'P6','머무는분':90,'근거':[],'운영':[],'이유':''}],'식사':[]}}
        self.assertTrue(처리기.코스짜기(r,'A',Path('.'),[],실행함수=lambda p,i:json.dumps(첫,ensure_ascii=False)))
        이전=r['코스안'][-1]['코스']
        새={'안':{'칸':[{'칸ID':'저녁-1','일차':1,'시간칸':'저녁','장소':'P5','머무는분':80,'근거':[],'운영':[],'이유':''}],'식사':[]}}
        self.assertTrue(처리기.부분수정(r,'A',Path('.'),['낮'],['저녁'],'저녁만 다른 찜갈비',실행함수=lambda p,i:json.dumps(새,ensure_ascii=False)))
        코스=r['코스안'][-1]['코스']
        낮=lambda c:next(x for x in c['칸목록'] if x['칸ID']=='낮-1')
        self.assertEqual(낮(코스)['시각'],낮(이전)['시각'])
        self.assertIn('봉산찜갈비',next(x for x in 코스['칸목록'] if x['칸ID']=='저녁-1')['장소명'])
        self.assertEqual(코스['부분수정기록']['코드가_되돌린_유지칸'],0)


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

class 안별입력시험(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory();self.root=Path(self.d.name)
        t=self.root/'r'/'01회차'/'통합시험_1';t.mkdir(parents=True)
        (t/'3단계_입력.json').write_text(json.dumps({'조건':{'계절':'봄','체류기간':'1박2일'},'근거목록':[{'id':'E1'}],'코스작성조건':{'시작지점':'동대구역'}},ensure_ascii=False),encoding='utf-8')
        self.r=기록모듈.새_기록({'계절':'봄','체류기간':'1박2일'},'사람:담당자',기록id='t',희망=['저녁은 동구'])
        기록모듈.추가(self.r,'코스안',{'안id':'A','코스':{'칸목록':[]},'출처시험id':'r/01회차/통합시험_1'},'코드:가져오기')

    def tearDown(self):self.d.cleanup()

    def test_B안은_A의_바탕근거에_B안_조건과_희망을_싣는다(self):
        기록모듈.안_추가(self.r,'B','저녁 중구','에이전트:총괄',바꾼희망={'희망-1':'저녁은 중구'},이유='이동 40분')
        i=처리기.코스입력(self.r,'B',self.root,[])
        self.assertEqual(i['근거목록'],[{'id':'E1'}]);self.assertEqual(i['코스작성조건'],{'시작지점':'동대구역'})
        self.assertEqual(i['희망'][0]['내용'],'저녁은 중구');self.assertEqual(i['안']['안id'],'B')
        self.assertEqual(i['원래요청']['희망'][0]['내용'],'저녁은 동구')
        self.assertNotIn('이전코스',i);self.assertNotIn('자료재검토필요',i)  # A안 코스를 B안 이전 버전으로 섞지 않음

    def test_꼭지킬조건을_바꾼_안은_조건_덮어쓰고_재검토_표시(self):
        기록모듈.안_추가(self.r,'B','당일','사람:담당자',바꾼조건={'체류기간':'당일'})
        i=처리기.코스입력(self.r,'B',self.root,[])
        self.assertEqual(i['조건']['체류기간'],'당일');self.assertIn('체류기간',i['자료재검토필요'])

    def test_같은안_다시짜면_최신버전을_이전코스로(self):
        기록모듈.추가(self.r,'코스안',{'안id':'A','버전':2,'코스':{'칸목록':[{'칸ID':'v2'}]}},'에이전트:코스')
        i=처리기.코스입력(self.r,'A',self.root,['고칠 점'])
        self.assertEqual(i['이전버전'],2);self.assertEqual(i['이전코스'],{'칸목록':[{'칸ID':'v2'}]})
        self.assertTrue(처리기.코스짜기(self.r,'A',self.root,['고칠 점'],실행함수=lambda p,x:'{"안":{"칸":[],"식사":[]}}'))
        self.assertEqual(기록모듈.버전목록(self.r,'A'),[1,2,3])


if __name__=='__main__':unittest.main()
