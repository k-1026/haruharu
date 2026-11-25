"""자료 확인부터의 총괄과 자율형 A/B 비교. 실제 AI 호출 없음."""
import copy
from pathlib import Path
import unittest
import json
from tempfile import TemporaryDirectory
from unittest import mock

import 총괄
import 기획기록 as 기록모듈
from 검사분류 import 안_검사
from 대안비교 import 등록


def record():
    r=기록모듈.새_기록({'계절':'가을','언어권':['일본어'],'지역':['중구'],'체류기간':'1박2일','코스작성조건':{}},'사람:담당자',기록id='self')
    r['실행정책']={'모드':'자율이용','최대버전':2}
    return r


class 전체총괄시험(unittest.TestCase):
    def test_실제연결은_자료확인부터_A와B검증까지_관리하고_코스AI는_한번만(self):
        from 관리자조회 import 결과저장소
        from 관리자실행 import 코스시험
        from 기획실행 import 기획실행
        from test_단계연결 import 코스
        a=코스();a['확정조건']={k:False for k in a['확정조건']}
        day2=copy.deepcopy(a['칸목록'][0]);day2.update({'일차':2,'칸ID':'2일-오전-1','시간칸':'2일차오전'})
        a['칸목록'].append(day2)
        a['코스시작종료']={k:'미확인' for k in a['코스시작종료']}
        a['2일차오전구성']='미선택'
        b=copy.deepcopy(a);b['칸목록'][0]['장소명']='대구광역시 중구 향촌문화관'
        a['대안제안']={'코스':b,'이유':'문화관 중심으로 순서를 조정','무엇을':'낮 관광지 변경'}
        calls=[]
        def fn(path,text):
            calls.append(path)
            if path.endswith('수요요약.md'):return '{"요약":"출처별 범위를 구분합니다."}'
            if path.endswith('검증.md'):return '{"통과":true,"문제":[]}'
            if path.endswith('총괄.md'):return '{"행동":"담당자에게","대상":"A","이유":"모의 검토"}'
            raise AssertionError(path)
        def draft(path,text):
            calls.append(path);self.assertIn('대안제안',text);return json.dumps(a,ensure_ascii=False)
        with TemporaryDirectory() as folder,mock.patch('run_stage.단계_실행',side_effect=AssertionError('실제 AI 금지')):
            service=기획실행(코스시험(결과저장소(folder),실행함수=draft),단계함수=fn)
            p=service.시작({'계절':'가을','지역':['중구'],'언어권':['일본어'],'체류기간':'1박2일','자동진행동의':True})
            service.작업.join(3)
            self.assertFalse(service.작업.is_alive())
            p=service.상태(p['기획id']);self.assertEqual(p['상태'],'완료',p.get('안내'))
            r=기록모듈.읽기(folder,p['기록id'])
            self.assertEqual([x['안id'] for x in r['안']],['A','B'])
            self.assertEqual(r['총괄진행']['완료단계'],총괄.전체순서)
            self.assertEqual(calls.count('.claude/agents/코스검토.md'),1)
            self.assertEqual(calls.count('.claude/agents/검증.md'),2)
            self.assertIsNone(r['선택'])

    def test_모든단계를_한번씩_코드로_관리한다(self):
        seen=[];p={'상태':'진행중'}
        handlers={name:(lambda name=name:seen.append(name)) for name in 총괄.전체순서}
        총괄.전체_돌리기(p,handlers)
        self.assertEqual(seen,['자료확인','수요분석','코스작성','결과검사','보완검증'])
        self.assertEqual(p['총괄']['완료단계'],seen)
        self.assertTrue(all(x['판단']=='코드' for x in p['총괄']['결정']))

    def test_앞단계가_실패하면_뒤단계와_AI를_부르지않는다(self):
        seen=[];p={'상태':'진행중'}
        def fail():raise ValueError('자료 없음')
        handlers={name:(lambda name=name:seen.append(name)) for name in 총괄.전체순서}
        handlers['수요분석']=fail
        with self.assertRaisesRegex(ValueError,'자료 없음'):총괄.전체_돌리기(p,handlers)
        self.assertEqual(seen,['자료확인'])
        self.assertEqual(p['총괄']['실패단계'],'수요분석')


class 자율검사시험(unittest.TestCase):
    def test_미정운영입력은_초안의_사람결정으로_강요하지않는다(self):
        import test_단계연결 as fixture
        r=record();course=fixture.코스()
        course['확정조건']={'시작종료확정':False,'겹침처리':False,'2일차오전선택':False}
        course['코스시작종료']={'시작지점':'미확인','종료지점':'미확인','시작시각':'미확인','종료시각':'미확인'}
        course['2일차오전구성']='미선택'
        기록모듈.추가(r,'코스안',{'안id':'A','코스':course},'에이전트:코스')
        result=안_검사(r,'A',{'확정체류기간':'1박2일','코스작성조건':{},'근거목록':[]})
        text=str(result['사람결정'])
        self.assertNotIn('시작',text);self.assertNotIn('종료',text)
        self.assertNotIn('겹침처리',text);self.assertNotIn('2일차 오전은 담당자',text)
        self.assertIn('운영참고',r['경고'][-1]['결과'])


class 대안시험(unittest.TestCase):
    def 준비(self):
        r=record();a={'칸목록':[{'칸ID':'낮','일차':1,'시간칸':'낮','장소명':'근대골목','시각':{'값':'10:00'}}]}
        기록모듈.추가(r,'코스안',{'안id':'A','코스':a},'에이전트:코스')
        return r,a

    def test_차이가있는_B안만_이유와함께_등록하고_원본은_보존한다(self):
        r,a=self.준비();before=copy.deepcopy(a)
        b={'칸목록':[{'칸ID':'낮','일차':1,'시간칸':'낮','장소명':'서문시장','시각':{'값':'11:00'}},
                    {'칸ID':'오전','일차':2,'시간칸':'오전','장소명':'향촌문화관'}]}
        self.assertTrue(등록(r,{'코스':b,'이유':'식사 권역에 가까운 구성','무엇을':'낮 관광지 조정'},'r/01회차/통합시험_1'))
        self.assertEqual(r['안'][1]['안id'],'B');self.assertEqual(r['코스안'][0]['코스'],before)
        self.assertEqual(r['원래요청']['조건']['지역'],['중구'])
        self.assertEqual(r['코스안'][1]['코스']['대안설명']['왜'],'식사 권역에 가까운 구성')
        self.assertIsNone(r['선택'])

    def test_누락이나_같은코스는_B로_복제하지않는다(self):
        r,a=self.준비()
        self.assertFalse(등록(r,None,''))
        self.assertFalse(등록(r,{'코스':a,'이유':'말만 다름'},''))
        self.assertEqual(len(r['안']),1)
        self.assertIn('이유',r['대안상태'])

    def test_필수지역을_벗어난_B안은_자동등록하지않는다(self):
        r,a=self.준비()
        b={'칸목록':[{'장소명':'대구광역시 동구 평화시장'}]}
        self.assertFalse(등록(r,{'코스':b,'이유':'지역을 넓힘'},''))
        self.assertEqual(len(r['안']),1)


if __name__=='__main__':unittest.main()
