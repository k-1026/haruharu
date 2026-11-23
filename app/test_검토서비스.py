import copy
import json
from pathlib import Path
import unittest
import test_관리자실행 as fixtures
import test_단계연결 as course_fixtures
import test_운영검토 as review_fixtures
from 관리자실행 import 조건_검사


class 검토서비스시험(unittest.TestCase):
    def setUp(self):
        fixtures.재개시험.setUp(self)
        c,s,d=review_fixtures.example()
        conditions=fixtures.코스조건()
        conditions.update(s['코스작성조건']);conditions['종료시각']='14:00';conditions['2일차점심포함']='포함'
        for r in conditions['식사목록']:r.update({'방식':'자유식','식비포함':'불포함'})
        self.conditions=conditions
        source=fixtures.전달();source['코스작성조건']=조건_검사(conditions,'1박2일')
        course=course_fixtures.코스();course.update(c);course['코스시작종료']['종료시각']='14:00'
        for r in course['칸목록']:r['근거ID']=['R01'] if r['시간칸']=='낮' else []
        course['확정조건'].update({'시작종료확정':True,'2일차오전선택':True})
        for day,slot,time in [(1,'점심','12:00'),(1,'저녁','18:00'),(2,'점심','12:00')]:
            key=f'{day}-{slot}';name=key+'권역'
            course['칸목록'].append({'안':'공통','칸ID':key,'일차':day,'시간칸':slot,'장소명':name,'시각':{'값':time,'종류':'가정'},'머무는시간':60,'근거ID':[]})
            course['식사목록'].append({'안':'공통','칸ID':key,'방식':'자유식','식당':'','권역':name,'추천후보':[],'식비포함':'불포함','시각':{'값':time,'종류':'가정'}})
            d['일정확인'].append({'안':'공통','칸ID':key,'시작일차':day,'시작시각':time,'종료일차':day,'종료시각':f'{int(time[:2])+1:02d}:00',
                                  '장소권역':name,'이후연결':'다음 장소 연결','연결확인':True,'확인메모':'이동 여유 확인'})
            op=copy.deepcopy(d['운영확인'][0]);op.update({'칸ID':key,'대상명':name,'영업시작':'09:00','영업종료':'22:00','마감시각':'21:00'});d['운영확인'].append(op)
        self.payload=d
        self.keyjob=self.key+'/통합시험_100000_000001'
        p=Path(self.tmp.name)/self.keyjob;p.mkdir()
        for name,data in [('3단계_입력.json',source),('3단계_결과.md',course),
                          ('통합시험_상태.json',{'종류':'관리자3단계','상태':'초안생성','시험id':self.keyjob,'원본id':self.key})]:
            (p/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        self.before={x.name:x.read_bytes() for x in p.iterdir()}

    def test_사람확인_기간_운영이_맞아야_4단계준비(self):
        state=self.service.검토반영(self.keyjob,self.payload)
        self.assertTrue(state['4단계준비검사']['진행가능'],state['4단계준비검사'])
        self.assertTrue(state['담당자확정'])
        self.assertEqual(state['상태'],'4단계준비완료')
        self.assertEqual(self.calls,[])
        self.assertEqual(self.before,{x.name:x.read_bytes() for x in (Path(self.tmp.name)/self.keyjob).iterdir()})
        self.service.시작(state['시험id']);self.assertEqual(self.calls,[])
        # 후속 조건 수정은 이전 담당자 확인을 재사용하지 않는다.
        changed=copy.deepcopy(self.conditions);changed['시작시각']='11:00'
        new=self.service.수정반영(state['시험id'],changed)
        self.assertFalse(new['담당자확정']);self.assertFalse(new['4단계준비검사']['진행가능'])

    def test_최종확인_미선택은_완료로_저장안함(self):
        self.payload['담당자최종확인']=False
        state=self.service.검토반영(self.keyjob,self.payload)
        self.assertFalse(state['4단계준비검사']['진행가능'])
        self.assertFalse(state['담당자확정']);self.assertEqual(self.calls,[])
