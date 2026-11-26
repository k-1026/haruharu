import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from app.공통 import 기획기록 as 기록모듈


def new():
    return 기록모듈.새_기록({'계절':'봄'},'사람:담당자','하룻밤 머무는 코스',기록id='t1')


class 기록시험(unittest.TestCase):
    def test_생성하면_영역과_결정이력_첫줄(self):
        r=new()
        for k in ['조건','근거','후보','코스안','경고','결정이력','실행','한도','목표','기록id','버전']:self.assertIn(k,r)
        self.assertEqual(len(r['결정이력']),1);self.assertEqual(r['결정이력'][0]['행동'],'생성')
        with self.assertRaises(PermissionError):기록모듈.새_기록({},'에이전트:총괄')

    def test_에이전트_후보는_항상_후보상태(self):
        r=new();i=기록모듈.추가(r,'후보',{'이름':'야시장','상태':'승인'},'에이전트:수집','웹 검색')
        self.assertEqual(i,'후보-1')
        self.assertEqual(r['후보'][0]['상태'],'후보')
        self.assertEqual(r['결정이력'][-1]['대상id'],'후보-1')

    def test_에이전트는_조건변경_승인_불가_이력도_안남음(self):
        r=new();i=기록모듈.추가(r,'후보',{'이름':'A'},'에이전트:수집');n=len(r['결정이력'])
        with self.assertRaises(PermissionError):기록모듈.조건_변경(r,{'계절':'여름'},'에이전트:총괄','')
        with self.assertRaises(PermissionError):기록모듈.승인(r,i,'에이전트:총괄','')
        self.assertEqual(len(r['결정이력']),n);self.assertEqual(r['조건'],{'계절':'봄'})

    def test_사람_승인(self):
        r=new();i=기록모듈.추가(r,'후보',{'이름':'A'},'에이전트:수집')
        기록모듈.승인(r,i,'사람:담당자','공식 안내 확인')
        self.assertEqual(r['후보'][0]['상태'],'승인');self.assertEqual(r['결정이력'][-1]['행동'],'승인')
        with self.assertRaises(ValueError):기록모듈.승인(r,'후보-99','사람:담당자','')
        with self.assertRaises(ValueError):기록모듈.추가(r,'조건',{},'사람:담당자')

    def test_저장_읽기_왕복과_잘못된id(self):
        with tempfile.TemporaryDirectory() as d:
            r=new();p=기록모듈.저장(r,Path(d))
            self.assertEqual(p,Path(d)/'기획'/'t1'/'기획기록.json')
            self.assertEqual(기록모듈.읽기(Path(d),'t1'),r)
            with self.assertRaises(ValueError):기록모듈.읽기(Path(d),'../x')
            with self.assertRaises(ValueError):기록모듈.새_기록({},'사람:a',기록id='a/b')

    def test_저장_실패해도_기존파일_유지(self):
        with tempfile.TemporaryDirectory() as d:
            r=new();p=기록모듈.저장(r,Path(d));before=p.read_text(encoding='utf-8')
            r['목표']='바뀜'
            with mock.patch.object(기록모듈.json,'dump',side_effect=OSError('디스크')):
                with self.assertRaises(OSError):기록모듈.저장(r,Path(d))
            self.assertEqual(p.read_text(encoding='utf-8'),before)


class 한도시험(unittest.TestCase):
    def test_같은일_실패2번이면_재시도_한도(self):
        r=new()
        for _ in range(2):기록모듈.실행_기록(r,'에이전트:수집','수집','평일 밤','빈칸','실패',AI호출=1)
        ok,why=기록모듈.한도_확인(r,'에이전트:수집','수집','평일 밤')
        self.assertFalse(ok);self.assertIn('재시도',why)
        self.assertTrue(기록모듈.한도_확인(r,'에이전트:수집','수집','주말 밤')[0])

    def test_AI호출_합이_한도면_멈춤(self):
        r=new();기록모듈.실행_기록(r,'에이전트:코스','코스','A','첫 생성','성공',AI호출=30)
        ok,why=기록모듈.한도_확인(r,'에이전트:검증','검증','A')
        self.assertFalse(ok);self.assertIn('AI 호출',why)

    def test_실행기록은_결과값검사와_이력(self):
        r=new()
        with self.assertRaises(ValueError):기록모듈.실행_기록(r,'에이전트:수집','수집','x','y','이상함')
        i=기록모듈.실행_기록(r,'코드:점검','점검','A','요일 검사','성공')
        self.assertEqual(r['실행'][0]['id'],i);self.assertEqual(r['결정이력'][-1]['행동'],'실행')

class 안과버전시험(unittest.TestCase):
    def rec(self):
        return 기록모듈.새_기록({'계절':'봄','지역':['중구','동구'],'체류기간':'1박2일'},'사람:담당자','저녁까지 머물게',
                             기록id='ab',희망=['저녁은 동구 평화시장에서','야경 포함'])

    def 코스(self,r,안id,버전):
        기록모듈.추가(r,'코스안',{'안id':안id,'버전':버전,'코스':{'칸목록':[]}},'에이전트:코스')

    def test_원래요청은_조건을_바꿔도_그대로(self):
        r=self.rec()
        기록모듈.조건_변경(r,{'계절':'여름'},'사람:담당자','담당자 수정')
        self.assertEqual(r['원래요청']['조건']['계절'],'봄');self.assertEqual(r['조건']['계절'],'여름')
        self.assertEqual([h['id'] for h in r['원래요청']['희망']],['희망-1','희망-2'])

    def test_B안은_희망만_바꾸고_적용조건이_따로(self):
        r=self.rec()
        기록모듈.안_추가(r,'B','저녁을 중구로 옮긴 안','에이전트:총괄',바꾼희망={'희망-1':'저녁은 중구 동성로에서'},이유='동구 이동 40분')
        a=기록모듈.적용조건(r,'A');b=기록모듈.적용조건(r,'B')
        self.assertEqual(a['희망'][0]['내용'],'저녁은 동구 평화시장에서');self.assertFalse(a['원래요청과_다름'])
        self.assertEqual(b['희망'][0]['내용'],'저녁은 중구 동성로에서');self.assertTrue(b['희망'][0]['바뀜'])
        self.assertEqual(b['조건'],a['조건']);self.assertTrue(b['원래요청과_다름'])

    def test_꼭지킬조건을_바꾸는_안은_사람만(self):
        r=self.rec()
        with self.assertRaises(PermissionError):기록모듈.안_추가(r,'B','당일로','에이전트:총괄',바꾼조건={'체류기간':'당일'})
        기록모듈.안_추가(r,'B','당일로','사람:담당자',바꾼조건={'체류기간':'당일'})
        self.assertEqual(기록모듈.적용조건(r,'B')['조건']['체류기간'],'당일');self.assertEqual(r['조건']['체류기간'],'1박2일')

    def test_없는_희망_조건_안은_거부(self):
        r=self.rec()
        with self.assertRaises(ValueError):기록모듈.안_추가(r,'B','x','에이전트:총괄',바꾼희망={'희망-9':'?'})
        with self.assertRaises(ValueError):기록모듈.안_추가(r,'A','x','에이전트:총괄')
        with self.assertRaises(ValueError):self.코스(r,'C',1)

    def test_버전은_안마다_따로_쌓이고_겹치지_않음(self):
        r=self.rec();기록모듈.안_추가(r,'B','대안','에이전트:총괄',바꾼희망={'희망-2':'야경 빼기'})
        self.코스(r,'A',1);self.코스(r,'A',2);self.코스(r,'B',1)
        self.assertEqual(기록모듈.버전목록(r,'A'),[1,2]);self.assertEqual(기록모듈.버전목록(r,'B'),[1])
        with self.assertRaises(ValueError):self.코스(r,'A',2)

    def test_선택은_사람만_있는_버전만(self):
        r=self.rec();self.코스(r,'A',1)
        with self.assertRaises(PermissionError):기록모듈.선택(r,'A',1,'에이전트:총괄')
        with self.assertRaises(ValueError):기록모듈.선택(r,'A',2,'사람:담당자')
        기록모듈.선택(r,'A',1,'사람:담당자','지도 비교 후')
        self.assertEqual((r['선택']['안id'],r['선택']['버전']),('A',1))

    def test_검증상태는_그_버전_경고만(self):
        r=self.rec();self.코스(r,'A',1);self.코스(r,'A',2)
        기록모듈.추가(r,'경고',{'종류':'검증','안id':'A','버전':1,'문구':'야시장 휴무'},'에이전트:검증')
        기록모듈.추가(r,'경고',{'종류':'검증결과','안id':'A','버전':1,'통과':False,'문구':'반려'},'에이전트:검증')
        기록모듈.추가(r,'경고',{'종류':'검증결과','안id':'A','버전':2,'통과':True,'문구':'통과'},'에이전트:검증')
        self.assertEqual(기록모듈.검증상태(r,'A',1),{'검증':'반려','남은문제':['야시장 휴무'],'코드점검':None})
        self.assertEqual(기록모듈.검증상태(r,'A',2)['남은문제'],[])
        self.assertEqual(기록모듈.검증상태(r,'B',1)['검증'],'검증 전')

    def test_형식1_기록을_읽으면_맞춰진다(self):
        old={'버전':1,'기록id':'old','조건':{'계절':'봄'},'목표':'','근거':[],'후보':[],'코스안':[{'안id':'A','코스':{}}],
             '경고':[],'결정이력':[],'실행':[],'한도':{}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'기획'/'old';p.mkdir(parents=True);(p/'기획기록.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
            r=기록모듈.읽기(d,'old')
        self.assertEqual(r['버전'],2);self.assertEqual(r['원래요청']['조건'],{'계절':'봄'})
        self.assertEqual([a['안id'] for a in r['안']],['A']);self.assertIsNone(r['선택'])


if __name__=='__main__':unittest.main()
