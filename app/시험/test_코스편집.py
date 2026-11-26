import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.공통 import 기획기록
from app.단계3_코스검토 import 처리기
from app.단계3_코스검토 import 코스조립
from test_코스조립 import 시험입력, 후보, 정상주문


class 범위시험(unittest.TestCase):
    def setUp(self):
        self.입력 = 시험입력()
        self.표 = 후보(self.입력)
        주 = copy.deepcopy(정상주문()['A'])
        주['칸'].append({**주['칸'][1], '칸ID': '점심-2', '일차': 2})
        주['식사'].append({'칸ID': '점심-2', '방식': '자유식', '권역': 'P2', '후보': []})
        self.이전, 문제 = 코스조립.조립({'안': 주}, self.표, self.입력)
        self.assertEqual(문제, [])

    def 검사(self, **kw):
        from app.단계3_코스검토.코스편집 import 수정_검사
        return 수정_검사(self.이전, {'범위': '일정', '칸ID': ['점심-2'], '작업': '요청', '요청': '다른 점심으로', **kw})

    def test_날짜가_다른_같은_점심을_구분한다(self):
        v = self.검사()
        self.assertEqual(v['바꿀칸ID'], ['점심-2'])
        self.assertIn('점심-1', v['유지칸ID'])

    def test_하루와_전체_범위(self):
        self.assertEqual(self.검사(범위='하루', 일차=2)['허용일차'], [2])
        self.assertEqual(self.검사(범위='전체')['유지칸ID'], ['숙박-1', '2일차오전-1'])

    def test_없는_ID와_잘못된_요청은_AI_전에_거부(self):
        for 값 in [{'칸ID': ['없음']}, {'칸ID': []}, {'칸ID': '점심-2'}, {'범위': '알아서'}, {'요청': ''}, {'작업': '임의'}]:
            with self.subTest(값=값), self.assertRaises(ValueError):
                self.검사(**값)

    def test_개별점심_교체는_첫날점심과_식사기록을_보존(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        새 = {'칸': [{**옛['칸'][0], '장소': 'P4'}, {**next(r for r in 옛['칸'] if r['칸ID']=='점심-2'), '장소': 'P5'}],
              '식사': [{'칸ID': '점심-2', '방식': '지정식', '권역': 'P5', '후보': []}]}
        합, 문제 = 범위_합치기(새, 옛, self.검사())
        self.assertEqual(문제, [])
        self.assertEqual(합['칸'][0], 옛['칸'][0])
        self.assertEqual(next(r for r in 합['칸'] if r['칸ID']=='점심-1')['장소'], 'P2')
        self.assertEqual(next(r for r in 합['칸'] if r['칸ID']=='점심-2')['장소'], 'P5')
        self.assertIn(next(m for m in 옛['식사'] if m['칸ID']=='점심-1'), 합['식사'])

    def test_선택일차밖에_새일정을_넣지_못한다(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        _, 문제 = 범위_합치기({'칸': [{'칸ID': '추가-1', '일차': 1, '시간칸': '낮', '장소': 'P4'}]}, 옛, self.검사(범위='하루', 일차=2))
        self.assertTrue(문제)

    def test_제외요청은_AI가_남겨도_실패한다(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        _, 문제 = 범위_합치기(옛, 옛, self.검사(작업='제외'))
        self.assertTrue(문제)

    def test_선택일정_삭제와_신규일정_추가(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        합, 문제 = 범위_합치기({'칸': [], '식사': []}, 옛, self.검사(작업='제외'))
        self.assertEqual(문제, [])
        self.assertNotIn('점심-2', [r['칸ID'] for r in 합['칸']])
        self.assertNotIn('점심-2', [r['칸ID'] for r in 합['식사']])
        새 = {'칸': [{'칸ID': '추가-1', '일차': 2, '시간칸': '낮', '장소': 'P4', '뒤칸ID': '점심-2'}]}
        합, 문제 = 범위_합치기(새, 옛, self.검사(작업='추가'))
        self.assertEqual(문제, [])
        ids = [r['칸ID'] for r in 합['칸']]
        self.assertEqual(ids.index('추가-1'), ids.index('점심-2')+1)

    def test_새일정은_잠긴방문을_삽입기준으로_삼을수없다(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        새 = {'칸': [{'칸ID': '추가-1', '일차': 2, '시간칸': '낮', '장소': 'P4', '뒤칸ID': '낮-1'}]}
        _, 문제 = 범위_합치기(새, 옛, self.검사(작업='추가'))
        self.assertTrue(문제)

    def test_하루_전체의_추가도_지정위치와_기존순서를_지킨다(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        for 범위 in ['하루','전체']:
            with self.subTest(범위=범위):
                수정 = self.검사(범위=범위, 일차=1, 작업='추가')
                새 = {'칸':[{'칸ID':'새방문','일차':1,'시간칸':'낮','장소':'P4','뒤칸ID':옛['칸'][0]['칸ID']}]}
                합, 문제 = 범위_합치기(새, 옛, 수정)
                self.assertEqual(문제,[])
                self.assertEqual(합['칸'][1]['칸ID'],'새방문')
                self.assertEqual([r for r in 합['칸'] if r['칸ID']!='새방문'],옛['칸'])

    def test_유지식사_다음방문이_바뀌면_이동정보는_새로_검사한다(self):
        입 = copy.deepcopy(self.입력)
        입['부분수정'] = self.검사(칸ID=['낮-2'])
        옛 = 코스조립.이전_주문서(self.이전,self.표)
        새 = {'안':{'칸':[{**next(r for r in 옛['칸'] if r['칸ID']=='낮-2'),'장소':'P4'}],'식사':[]}}
        코스,문제=코스조립.조립(새,self.표,입,self.이전)
        self.assertEqual(문제,[])
        식사=next(m for m in 코스['식사목록'] if m['칸ID']=='점심-1')
        self.assertIn('봉산문화거리',식사['이후연결'])
        self.assertIsNone(식사['이동시간']['분'])

    def test_하루_순서와_체류시간_수정(self):
        from app.단계3_코스검토.코스편집 import 범위_합치기
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        둘 = [r for r in 옛['칸'] if r['일차']==2]
        합, 문제 = 범위_합치기({'칸': list(reversed(둘))}, 옛, self.검사(범위='하루', 일차=2, 작업='순서'))
        self.assertEqual(문제, [])
        self.assertEqual([r['칸ID'] for r in 합['칸'] if r['일차']==2], [r['칸ID'] for r in reversed(둘)])
        합, 문제 = 범위_합치기({'칸': [next(r for r in 옛['칸'] if r['칸ID']=='점심-2')]}, 옛, self.검사(작업='체류시간', 머무는분=45))
        self.assertEqual(문제, [])
        self.assertEqual(next(r for r in 합['칸'] if r['칸ID']=='점심-2')['머무는분'], 45)

    def test_식사수정은_과거방식_미선택에_덮어씌워지지_않는다(self):
        입 = copy.deepcopy(self.입력)
        입['코스작성조건']['식사목록'] = [{'일차':2, '시간칸':'점심', '방식':'미선택'}]
        입['부분수정'] = self.검사(작업='식사', 재방문허용=True)
        옛 = 코스조립.이전_주문서(self.이전, self.표)
        주 = {'안': {'칸': [next(r for r in 옛['칸'] if r['칸ID']=='점심-2')],
                     '식사': [{'칸ID':'점심-2','방식':'자유식','권역':'P2','후보':[]}]}}
        코스, 문제 = 코스조립.조립(주, self.표, 입, self.이전)
        self.assertEqual(문제, [])
        self.assertEqual(next(m for m in 코스['식사목록'] if m['칸ID']=='점심-2')['방식'], '자유식')

    def test_수정불가_이유만_답해도_그_이유를_보존한다(self):
        입 = copy.deepcopy(self.입력)
        입['부분수정'] = self.검사()
        _, 문제 = 코스조립.조립({'안':{'수정불가이유':'요청한 장소의 운영·이동 자료가 없습니다.'}},self.표,입,self.이전)
        self.assertEqual(문제,['요청한 장소의 운영·이동 자료가 없습니다.'])

    def test_새API도_조립까지_반영하며_무변경은_새버전으로_저장하지_않는다(self):
        r = 기획기록.새_기록({'계절': '봄', '지역': ['중구'], '체류기간': '1박2일'}, '사람:담당자', 기록id='t')
        기획기록.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': self.이전}, '에이전트:코스')
        원본 = copy.deepcopy(r['코스안'][0])
        새 = {'안': {'칸': [{'칸ID': '점심-2', '일차': 2, '시간칸': '점심', '장소': 'P5', '머무는분': 60, '근거': [], '운영': []}],
                      '식사': [{'칸ID': '점심-2', '방식': '자유식', '권역': 'P5', '후보': []}]}}
        본 = []
        def fn(p, i):
            본.append(json.loads(i))
            return json.dumps(새, ensure_ascii=False)
        with patch('app.단계3_코스검토.코스조립.후보표_만들기', return_value=self.표):
            self.assertTrue(처리기.부분수정(r, 'A', Path('.'), [], [], '점심 교체', fn, 수정옵션=self.검사()), r['실행'])
            self.assertEqual(r['코스안'][0], 원본)
            self.assertEqual(본[0]['부분수정']['바꿀칸ID'], ['점심-2'])
            self.assertTrue(r['코스안'][-1]['코스']['부분수정기록']['변경목록'])
            self.assertFalse(처리기.부분수정(r, 'A', Path('.'), [], [], '점심 교체', fn, 수정옵션=self.검사()))
        self.assertEqual(len(r['코스안']), 2)


class 서비스시험(unittest.TestCase):
    def setUp(self):
        범위시험.setUp(self)
        from app.공통.기획실행 import 기획실행, _쓰기, 진행파일
        self.임시 = TemporaryDirectory()
        self.addCleanup(self.임시.cleanup)
        self.root = Path(self.임시.name)
        self.folder = self.root/'20261126_000001/01회차'
        self.folder.mkdir(parents=True)
        self.기록 = 기획기록.새_기록(self.입력['조건'], '사람:담당자', 기록id='편집시험')
        기획기록.추가(self.기록, '코스안', {'안id':'A', '버전':1, '코스':self.이전}, '에이전트:코스')
        기획기록.저장(self.기록, self.root)
        _쓰기(self.folder, 진행파일, {'기록id':'편집시험','기획id':'20261126_000001/01회차','상태':'완료','활동':[]})
        def ai(path, text):
            if path.endswith('검증.md'):
                return '{"통과":true,"문제":[]}'
            return '{"안":{"칸":[],"식사":[]}}'
        self.서비스 = 기획실행(SimpleNamespace(저장소=SimpleNamespace(루트=self.root), _원본=lambda x:None), 단계함수=ai)
        self.addCleanup(lambda: self.서비스.작업.join(5) if self.서비스.작업 else None)

    def payload(self, **kw):
        return {'기획id':'20261126_000001/01회차','안id':'A','기준버전':1,'요청':'2일차 점심 제외',
                '수정':{'범위':'일정','칸ID':['점심-2'],'작업':'제외'},**kw}

    def test_최신버전이_아니거나_잘못된_범위면_작업을_시작하지_않는다(self):
        for kw in [{'기준버전':0},{'기준버전':None},{'수정':{'칸ID':['없는칸']}},{'수정':None}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.서비스.수정시작(self.payload(**kw))
        self.assertIsNone(self.서비스.작업)
        self.assertEqual(self.서비스.상태('20261126_000001/01회차')['상태'],'완료')

    def test_서비스_수정은_검사후_저장하고_총괄이_잠금을_풀지_않는다(self):
        with patch('app.단계3_코스검토.코스조립.후보표_만들기', return_value=self.표), patch.object(self.서비스,'_총괄',side_effect=AssertionError('수정 범위 재작성 금지')):
            self.서비스.수정시작(self.payload())
            self.서비스.작업.join(10)
        self.assertFalse(self.서비스.작업.is_alive())
        상태=self.서비스.상태('20261126_000001/01회차')
        self.assertEqual(상태['상태'],'완료',상태.get('안내'))
        기록=기획기록.읽기(self.root,'편집시험')
        self.assertEqual(기획기록.버전목록(기록,'A'),[1,2])
        새=처리기.최신안(기록,'A')['코스']
        self.assertNotIn('점심-2',[r['칸ID'] for r in 새['칸목록']])
        self.assertIn('점심-1',[r['칸ID'] for r in 새['칸목록']])


if __name__ == '__main__':
    unittest.main()
