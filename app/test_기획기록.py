import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import 기획기록 as 기록모듈


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


if __name__=='__main__':unittest.main()
