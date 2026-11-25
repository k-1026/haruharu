import json
from pathlib import Path
import unittest
import test_관리자실행 as fixtures
import test_단계연결 as course_fixtures


class 수동반영시험(unittest.TestCase):
    def test_일차선택_수정본에_보존하고_시작시각조정(self):
        self.edit.update({'시작일차':1,'종료일차':2,'시작시각':'11:34'})
        status,result=self.수정()
        self.assertEqual(result['코스시작종료']['시작일차'],1)
        self.assertEqual(result['코스시작종료']['종료일차'],2)
        # 이 축약 fixture에는 1일차 식사도 없어 기존 형식 확인 상태가 우선한다.
        self.assertEqual(status['상태'],'검사확인필요')
        self.assertFalse(any('시작 전' in x for x in status['시간표검사']['충돌']))
        self.assertEqual(result['칸목록'][0]['시각']['값'],'11:34')
        self.assertEqual(self.calls,[])

    def setUp(self):
        fixtures.재개시험.setUp(self)
        self.initial = fixtures.코스조건()
        for row in self.initial['식사목록']:
            row.update({'방식': '자유식', '식비포함': '불포함'})
        self.initial['2일차오전구성'] = '자유시간'
        self.base = self.service.저장(self.key, self.initial)
        folder = Path(self.tmp.name) / self.base['시험id']
        result = course_fixtures.코스()
        result['2일차오전구성'] = '자유시간'
        (folder / '3단계_결과.md').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        self.before = {p.name:p.read_bytes() for p in folder.iterdir()}
        self.edit = fixtures.코스조건()
        self.edit.update({'시작지점':'시작A', '시작시각':'10:00', '종료지점':'종료B', '종료시각':'14:00',
                          '2일차오전구성':'자유시간','2일차점심포함':'포함'})
        for r in self.edit['식사목록']:
            r.update({'방식':'자유식','식비포함':'불포함'})

    def 수정(self):
        status = self.service.수정반영(self.base['시험id'], self.edit)
        path = Path(self.tmp.name) / status['시험id']
        return status, json.loads((path/'3단계_구조화.json').read_text(encoding='utf-8'))

    def test_원본보존_AI없이_시작종료와_점심반영(self):
        status, result = self.수정()
        self.assertNotEqual(status['시험id'], self.base['시험id'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.before, {p.name:p.read_bytes() for p in (Path(self.tmp.name)/self.base['시험id']).iterdir()})
        self.assertEqual(result['코스시작종료']['시작지점'], '시작A')
        self.assertEqual(result['코스시작종료']['종료시각'], '14:00')
        lunches = [r for r in result['칸목록'] if r['일차']==2 and r['시간칸']=='점심']
        self.assertEqual(len(lunches), 1)
        self.assertEqual(lunches[0]['시각'], {'값':'','종류':'미정'})
        self.assertFalse(status['담당자확정'])
        self.assertTrue(status['수동수정본'])
        self.assertTrue(status['담당자확인대기'])

    def test_미포함으로_바꿔도_원래수정본_유지(self):
        status, result = self.수정()
        self.edit['2일차점심포함']='미포함'
        second = self.service.수정반영(status['시험id'], self.edit)
        p=Path(self.tmp.name)/second['시험id']
        obj=json.loads((p/'3단계_구조화.json').read_text(encoding='utf-8'))
        self.assertFalse(any(r['일차']==2 and r['시간칸']=='점심' for r in obj['칸목록']))
        self.assertFalse(any(r['칸ID']==next(r for r in result['칸목록'] if r['일차']==2 and r['시간칸']=='점심')['칸ID'] for r in obj['식사목록']))
        self.assertEqual(self.calls, [])

    def test_다른변경_몰래반영안함(self):
        self.edit['운영방식']='단체동행형'
        with self.assertRaisesRegex(ValueError, '운영방식'):
            self.수정()

    def test_점심선택_입력검사(self):
        self.edit['2일차점심포함']='알아서'
        with self.assertRaises(ValueError):
            self.수정()

    def test_미정이면_점심을_자동추가하지않음(self):
        self.edit['2일차점심포함']='미정'
        status,result=self.수정()
        self.assertFalse(any(r['일차']==2 and r['시간칸']=='점심' for r in result['칸목록']))
        self.assertTrue(any('점심' in p and '여부' in p for p in status['담당자확인대기']))

    def test_여러안에는_각각_점심칸_추가(self):
        p=Path(self.tmp.name)/self.base['시험id']/'3단계_결과.md'
        obj=json.loads(p.read_text(encoding='utf-8'))
        other=dict(obj['칸목록'][0]); other['안']='대안'
        obj['칸목록'].append(other)
        p.write_text(json.dumps(obj), encoding='utf-8')
        status,result=self.수정()
        self.assertEqual({r.get('안','공통') for r in result['칸목록'] if r['시간칸']=='점심' and r['일차']==2}, {'공통','대안'})

    def test_원본2단계가_바뀌면_수정차단(self):
        obj=json.loads(self.source.read_text(encoding='utf-8'));obj['요약']='새 근거'
        self.source.write_text(json.dumps(obj),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'2단계 결과'):
            self.수정()


if __name__=='__main__':
    unittest.main()
