import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.서버.관리자조회 import 결과저장소


class 운영진단시험(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = '20261125_015124/01회차'
        self.folder = self.root / self.key
        self.folder.mkdir(parents=True)
        self.store = 결과저장소(self.root)
        self.trial = self.key + '/통합시험_015141_738022'

    def 저장(self, name, data):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def 실패(self):
        self.저장('기획_진행.json', {'상태':'멈춤', '시험id':self.trial, '단계':[
            {'이름':'자료 확인','상태':'완료'}, {'이름':'수요 근거 정리','상태':'완료'},
            {'이름':'코스 작성','상태':'실패'}, {'이름':'결과 검사','상태':'대기'}]})
        self.저장('통합시험_015141_738022/AI_오류.json', {'오류':[{
            '종류':'CLINotFoundError','메시지':'Claude Code not found',
            '제공자':'claude','모델':'test','경과초':0.05,
            '원인':[{'종류':'FileNotFoundError','메시지':'[WinError 206] 파일 이름이나 확장명이 너무 깁니다'}]}]})

    def test_과거_하위오류를_실패단계와_실제원인으로_요약한다(self):
        self.실패()
        self.저장('3단계_전달_준비.json', {'검사결과':['통과']})
        summary = self.store.상세(self.key)['운영진단']
        self.assertEqual(summary['상태'], '실패')
        self.assertEqual(summary['실패단계'], '3단계 · 코스 작성')
        self.assertIn('명령행', summary['원인'])
        self.assertNotIn('설치하세요', summary['조치'])
        self.assertEqual(summary['로그경로'], self.trial + '/AI_오류.json')
        self.assertEqual(self.store.목록()[0]['운영진단']['상태'], '실패')

    def test_새_실행중에는_이전_실패를_현재오류로_보이지않는다(self):
        self.실패()
        self.저장('기획_진행.json', {'상태':'진행중','시험id':self.key+'/통합시험_020000_000001',
            '단계':[{'이름':'코스 작성','상태':'진행중'}]})
        summary = self.store.상세(self.key)['운영진단']
        self.assertEqual(summary['상태'], '진행중')
        self.assertEqual(summary['원인'], '')

    def test_세부오류없는_중단도_확인된_안내를_유지한다(self):
        self.저장('기획_진행.json', {'상태':'멈춤','안내':'근거를 확보하지 못했습니다.',
            '단계':[{'이름':'수요 근거 정리','상태':'실패'}]})
        summary = self.store.상세(self.key)['운영진단']
        self.assertIn('근거를 확보하지 못했습니다', summary['원인'])
        self.assertEqual(summary['오류종류'], '미수집')

    def test_진행_JSON이_깨지면_완료로_추정하지않는다(self):
        (self.folder/'기획_진행.json').write_text('{', encoding='utf-8')
        summary = self.store.상세(self.key)['운영진단']
        self.assertEqual(summary['상태'], '기록 확인 필요')

    def test_다른_실행의_시험id를_따라가지않는다(self):
        self.저장('기획_진행.json', {'상태':'멈춤','시험id':'20261124_100000/01회차/통합시험_010000_000001'})
        summary = self.store.상세(self.key)['운영진단']
        self.assertNotIn('20261124', summary['로그경로'])

    def test_진행의_단계배열이_깨져도_다른기록_조회를_막지않는다(self):
        self.저장('기획_진행.json', {'상태':'멈춤','단계':None})
        self.assertEqual(self.store.목록()[0]['운영진단']['상태'], '기록 확인 필요')

    def test_현재_통합시험의_내장오류만_있어도_진단한다(self):
        self.저장('통합시험_015141_738022/통합시험_상태.json', {
            '상태':'실행실패','오류상세':{'종류':'AI응답시간초과','제공자':'claude'}})
        summary = self.store.상세(self.key)['운영진단']
        self.assertEqual(summary['실패단계'], '3단계 · 코스 작성')
        self.assertIn('제한 시간', summary['원인'])
        self.assertTrue(summary['로그경로'].endswith('/통합시험_상태.json'))


if __name__ == '__main__':
    unittest.main()
