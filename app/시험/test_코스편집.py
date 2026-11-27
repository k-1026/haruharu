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


class 식사후보시험(unittest.TestCase):
    def test_점심_후보묶음은_방문전체를_보존하고_선택주체만_관광객으로_분리(self):
        self.c['칸목록'][1]['시간칸']='점심'
        before=copy.deepcopy(self.c)
        result=self.m.묶음반영(self.c,'m',['식당A','식당B'],{'지역':['중구']},미확인동의=True)
        self.assertEqual(self.c,before)
        self.assertEqual(result['칸목록'],before['칸목록'])
        self.assertEqual(result['식사목록'][0]['권역'],before['식사목록'][0]['권역'])
        self.assertEqual(result['식사목록'][0]['후보묶음']['선택주체'],'관광객')
        self.assertEqual(result['식사목록'][0]['후보묶음']['후보'],['식당A','식당B'])
        self.assertNotIn('경로선택후보',result['식사목록'][0])
        with self.assertRaises(ValueError):self.m.묶음반영(self.c,'m',['식당A','식당A'],{},True)
        with self.assertRaises(ValueError):self.m.묶음반영(self.c,'m',[],{},True)

    def test_저녁_묶음은_치킨_1곳_이상이_필수이고_점심은_1곳도_가능(self):
        cond={'지역':['중구']}
        saved=self.m.묶음반영(self.c,'m',['식당A','치킨C (치킨 옵션)'],cond,True)
        self.assertEqual(saved['식사목록'][0]['후보묶음']['후보'],['식당A','치킨C (치킨 옵션)'])
        with self.assertRaisesRegex(ValueError,'치킨 후보가 1곳 이상'):self.m.묶음반영(self.c,'m',['식당A','식당B'],cond,True)
        self.places.append({**self.places[0],'장소명':'서문시장','장소유형':'시장','코스칸':'점심·저녁'})
        with self.assertRaisesRegex(ValueError,'치킨 후보가 1곳 이상'):self.m.묶음반영(self.c,'m',['식당A','서문시장'],cond,True)
        with self.assertRaisesRegex(ValueError,'2개'):self.m.묶음반영(self.c,'m',['치킨C (치킨 옵션)'],cond,True)
        with self.assertRaises(ValueError):self.m.묶음반영(self.c,'m',['치킨C (치킨 옵션)','치킨D (치킨 옵션)'],cond,True)
        self.c['칸목록'][1]['시간칸']='점심'
        one=self.m.묶음반영(self.c,'m',['식당A'],cond,True)
        self.assertEqual(one['식사목록'][0]['후보묶음']['후보'],['식당A'])

    def test_점심은_직원의_단일식당반영을_막고_확인안된_묶음은_공개준비중(self):
        self.c['칸목록'][1]['시간칸']='점심'
        with self.assertRaisesRegex(ValueError,'후보 묶음'):self.m.반영(self.c,'m','식당B',{},True)
        result=self.m.묶음반영(self.c,'m',['식당A','식당B'],{},True)
        pack=self.m.관광객묶음(result,{})[0]
        self.assertEqual(pack['선택주체'],'관광객')
        self.assertTrue(pack['공개준비'])  # 점심은 선택 사항이라 후보가 미확인이어도 공개한다.
        self.assertTrue(all(not c['선택가능'] for c in pack['후보']))
        for p in self.places:p['마지막입장']='21:00'
        ready=self.m.관광객묶음(result,{'방문시작일':'2026-11-26'})[0]
        self.assertTrue(ready['공개준비'])
        self.assertTrue(all(c['선택가능'] for c in ready['후보']))
        self.c['칸목록'][2]['시각']['값']='19:25'
        with self.assertRaisesRegex(ValueError,'다음 일정'):self.m.묶음반영(self.c,'m',['식당A','식당B'],{},True)

    def test_저장된_후보경로는_서버재시작후에도_쓰되_인접일정변경시_재사용하지않는다(self):
        self.c['칸목록'][1]['시간칸']='점심'
        saved=self.m.묶음반영(self.c,'m',['식당A','식당B'],{},True)
        with patch.object(self.m,'구간',return_value=None):
            rows=self.m.관광객묶음(saved,{})[0]['후보']
            self.assertTrue(all(c['반영가능'] for c in rows))
            saved['칸목록'][2]['장소명']='바뀐 다음장소'
            self.assertTrue(all(not c['반영가능'] for c in self.m.관광객묶음(saved,{})[0]['후보']))
        saved['칸목록'][2]['장소명']='뒤'
        with patch.object(self.m,'구간',side_effect=lambda a,b:{'출발':a,'도착':b,'분':10,'경로':None}):
            self.assertTrue(all(c['후보이동'][0]['경로'] for c in self.m.관광객묶음(saved,{})[0]['후보']))

    def test_관광객공개는_휴무와_인접일정시각이_비면_막는다(self):
        self.c['칸목록'][1]['시간칸']='점심'
        for p in self.places:p['마지막입장']='21:00'
        saved=self.m.묶음반영(self.c,'m',['식당A','식당B'],{},True)
        conditions={'방문시작일':'2026-11-26'}
        self.assertTrue(all(c['선택가능'] for c in self.m.관광객묶음(saved,conditions)[0]['후보']))
        self.places[0]['정기휴무']=''
        self.assertFalse(self.m.관광객묶음(saved,conditions)[0]['후보'][0]['선택가능'])
        self.places[0]['정기휴무']='연중무휴'
        saved['칸목록'][0]['종료시각']['값']=''
        self.assertFalse(any(c['선택가능'] for c in self.m.관광객묶음(saved,conditions)[0]['후보']))

    def test_관광객묶음_저녁은_치킨이_선택가능해야_공개준비_시장은_선택가능으로_보이되_세지않음(self):
        for p in self.places:p['마지막입장']='21:00'
        cond={'지역':['중구'],'방문시작일':'2026-11-26'}
        saved=self.m.묶음반영(self.c,'m',['식당A','치킨C (치킨 옵션)'],cond,True)
        pack=self.m.관광객묶음(saved,cond)[0]
        self.assertEqual((pack['시간칸'],pack['자유해결허용'],pack['공개준비']),('저녁',False,True))
        self.assertEqual({k for k in ['분류','구역형','치킨'] if k in pack['후보'][0]},{'분류','구역형','치킨'})
        self.places[2]['정기휴무']=''
        self.assertFalse(self.m.관광객묶음(saved,cond)[0]['공개준비'])
        self.places[2]['정기휴무']='연중무휴'
        self.places.append({**self.places[0],'장소명':'서문시장','장소유형':'시장','코스칸':'점심·저녁','마지막입장':'21:00'})
        with_market=self.m.묶음반영(self.c,'m',['서문시장','치킨C (치킨 옵션)'],cond,True)
        market=self.m.관광객묶음(with_market,cond)[0]['후보'][0]
        self.assertTrue(market['구역형'] and market['선택가능'])
        self.places[2]['정기휴무']=''
        self.assertFalse(self.m.관광객묶음(with_market,cond)[0]['공개준비'])  # 시장만으로는 치킨 조건을 채우지 못한다.

    def setUp(self):
        from app.단계3_코스검토 import 식사선택
        self.m=식사선택
        def row(id,slot,name,start,end):
            return {'칸ID':id,'안':'공통','일차':1,'시간칸':slot,'장소명':name,
                    '시각':{'값':start,'종류':'가정'},'종료시각':{'값':end,'종류':'가정'},'머무는시간':60}
        self.c={'칸목록':[row('a','낮','앞','17:00','18:00'),row('m','저녁','식당A','18:20','19:20'),row('b','밤','뒤','19:40','20:40')],
                '식사목록':[{'칸ID':'m','안':'공통','방식':'미선택','권역':'도심 권역','추천후보':['식당A'],'식비포함':'미정'}]}
        self.places=[{'장소명':n,'구':'중구','코스칸':'점심·저녁' if not chicken else '저녁','장소유형':'식당',
                      '운영시간':hours,'정기휴무':'연중무휴','출처ID':'S1','확인일':'2026-11-26',
                      '출처URL':'https://example.org/food'} for n,chicken,hours in [('식당A',False,'10:00-22:00'),('식당B',False,'10:00-22:00'),('치킨C (치킨 옵션)',True,'11:00-22:00'),('치킨D (치킨 옵션)',True,'11:00-18:30')]]
        self.patches=[patch.object(self.m,'장소목록',return_value=self.places),patch.object(self.m,'좌표',return_value=(35.87,128.59)),
                      patch.object(self.m,'구간',side_effect=lambda a,b:{'출발':a,'도착':b,'분':10,'경로':[[35.87,128.59],[35.871,128.591]],'출처':'시험 경로','확인일':'2026-11-26'})]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_저녁은_다른음식과_치킨을_같이_제시하고_늦은마감충돌_구분(self):
        rows=self.m.후보목록(self.c,self.c['칸목록'][1],{'지역':['중구']})
        self.assertGreaterEqual(len(rows),3)
        self.assertTrue(any(x['치킨'] for x in rows))
        late=next(x for x in rows if '치킨D' in x['장소명'])
        self.assertFalse(late['반영가능'])

    def test_선택한_식사만_수정하고_시간권역과_나머지_전부_보존(self):
        before=copy.deepcopy(self.c)
        result=self.m.반영(self.c,'m','식당B',{'지역':['중구']},미확인동의=True)
        self.assertEqual(self.c,before)
        self.assertEqual(result['칸목록'][::2],before['칸목록'][::2])
        for key in ['시각','종료시각','머무는시간','일차','칸ID']:
            self.assertEqual(result['칸목록'][1][key],before['칸목록'][1][key])
        self.assertEqual(result['식사목록'][0]['권역'],'도심 권역')
        self.assertEqual(result['식사목록'][0]['방식'],'자유식')
        self.assertEqual(result['식사목록'][0]['경로선택후보'],'식당B')

    def test_경로누락과_다음일정_충돌은_반영불가(self):
        with patch.object(self.m,'구간',return_value=None):
            with self.assertRaisesRegex(ValueError,'이동'):self.m.반영(self.c,'m','식당B',{'지역':['중구']},미확인동의=True)
        self.c['칸목록'][2]['시각']['값']='19:25'
        with self.assertRaisesRegex(ValueError,'다음 일정'):self.m.반영(self.c,'m','식당B',{'지역':['중구']},미확인동의=True)

    def test_점심은_치킨과_다른구를_빼고_자료부족을_성공으로_바꾸지않음(self):
        self.c['칸목록'][1]['시간칸']='점심'
        self.places.append({**self.places[0],'장소명':'동구식당','구':'동구'})
        rows=self.m.후보목록(self.c,self.c['칸목록'][1],{'지역':['중구']})
        self.assertFalse(any(x['치킨'] or x['장소명']=='동구식당' for x in rows))
        self.c['칸목록'][1]['시각']['값']=''
        self.assertNotIn('영업시간 상세 확인 필요',self.m.비교(self.c,'m','식당B',{'지역':['중구']})['확인필요'])
        with self.assertRaisesRegex(ValueError,'확인'):self.m.묶음반영(self.c,'m',['식당A','식당B'],{'지역':['중구']})

    def test_후보분류와_구역형(self):
        cond={'지역':['중구'],'방문시작일':'2026-11-26'}
        self.assertEqual(self.m.비교(self.c,'m','치킨D (치킨 옵션)',cond)['분류'],'불가')
        a=self.m.비교(self.c,'m','식당A',cond)
        self.assertEqual(a['분류'],'확인후');self.assertFalse(a['구역형'])
        for p in self.places:p['마지막입장']='21:00'
        self.assertEqual(self.m.비교(self.c,'m','식당A',cond)['분류'],'바로')
        self.places.append({**self.places[0],'장소명':'서문시장','장소유형':'시장','코스칸':'점심·저녁'})
        market=self.m.비교(self.c,'m','서문시장',cond)
        self.assertTrue(market['구역형'])
        self.assertEqual(market['분류'],'확인후')
        self.assertTrue(any('구체 식당 미수집' in w for w in market['확인필요']))

    def test_세트제안은_치킨을_먼저_두고_멀거나_불가한_후보는_뺀다(self):
        cond={'지역':['중구']}
        names=self.m.제안(self.c,'m',cond)
        self.assertEqual(names[0],'치킨C (치킨 옵션)')
        self.assertNotIn('치킨D (치킨 옵션)',names)
        self.assertEqual(set(names),{'치킨C (치킨 옵션)','식당A','식당B'})
        self.assertEqual(len(self.m.제안(self.c,'m',cond,최대=2)),2)
        def leg(a,b):return {'출발':a,'도착':b,'분':25 if b=='식당B' else 10,'경로':[[35.87,128.59],[35.871,128.591]]}
        self.c['칸목록'][0]['종료시각']['값']='16:00'
        def far(a,b):return {'출발':a,'도착':b,'분':25 if 'C' in b else 10,'경로':[[35.87,128.59],[35.871,128.591]]}
        with patch.object(self.m,'구간',side_effect=far):
            self.assertEqual(self.m.제안(self.c,'m',cond)[0],'치킨C (치킨 옵션)')  # 치킨은 멀어도 남긴다.
        with patch.object(self.m,'구간',side_effect=leg):
            self.assertNotIn('식당B',self.m.제안(self.c,'m',cond))
            self.assertIn('식당B',self.m.제안(self.c,'m',cond,도보분=30))

    def test_점심_제안은_치킨이_없고_시장_기준이면_시장을_먼저_두며_중복이_없다(self):
        cond={'지역':['중구']}
        self.c['칸목록'][1]['시간칸']='점심'
        self.assertFalse(any('치킨' in n for n in self.m.제안(self.c,'m',cond)))
        self.places.append({**self.places[0],'장소명':'서문시장','장소유형':'시장','코스칸':'점심'})
        self.c['식사목록'][0]['식사기준장소']='서문시장'
        names=self.m.제안(self.c,'m',cond)
        self.assertEqual(names[0],'서문시장')
        self.assertEqual(names.count('서문시장'),1)

    def test_서비스_후보묶음_저장과_QR조회는_개인선택으로_공통기록을_쓰지않는다(self):
        from app.공통.기획실행 import 기획실행
        self.c['칸목록'][1]['시간칸']='점심'
        with TemporaryDirectory() as folder:
            root=Path(folder)
            r=기획기록.새_기록({'지역':['중구']},'사람:시험',기록id='meal-pack')
            기획기록.추가(r,'코스안',{'안id':'A','버전':1,'코스':self.c},'코드:시험')
            기획기록.저장(r,root)
            service=기획실행(SimpleNamespace(저장소=SimpleNamespace(루트=root)))
            service.코스._시험=lambda key:root
            request={'시험id':'x/y/meal-pack','안id':'A','기준버전':1,'칸ID':'m','후보':['식당A','식당B'],'미확인동의':True}
            with patch('app.공통.기록도구.코스_점검'):
                self.assertEqual(service.식사묶음반영(request)['버전'],2)
            stored=기획기록.읽기(root,'meal-pack')
            self.assertEqual(stored['코스안'][0],r['코스안'][0])
            self.assertEqual(stored['코스안'][-1]['코스']['칸목록'],self.c['칸목록'])
            source=root/'기획/meal-pack/기획기록.json';before=source.read_bytes()
            pack=service.관광객식사({**request,'기준버전':2})
            self.assertEqual(pack['버전'],2)
            self.assertEqual(pack['코스키'],'meal-pack')
            self.assertEqual(len(pack['식사묶음']),1)
            self.assertNotIn('원래요청',pack)
            self.assertEqual(source.read_bytes(),before)
            with self.assertRaisesRegex(ValueError,'최신'):service.식사묶음반영(request)

    def test_서비스_비교는_저장없이_반영은_최신버전만_새로_추가(self):
        from app.공통.기획실행 import 기획실행
        with TemporaryDirectory() as folder:
            root=Path(folder)
            r=기획기록.새_기록({'지역':['중구']},'사람:시험',기록id='meal-test')
            기획기록.추가(r,'코스안',{'안id':'A','버전':1,'코스':self.c},'코드:시험')
            기획기록.저장(r,root)
            source=root/'기획/meal-test/기획기록.json';before=source.read_bytes()
            service=기획실행(SimpleNamespace(저장소=SimpleNamespace(루트=root)))
            service.코스._시험=lambda key:root
            request={'시험id':'x/y/meal-test','안id':'A','기준버전':1,'칸ID':'m','장소명':'식당B','미확인동의':True}
            preview=service.식사비교(request)
            self.assertTrue(preview['반영가능']);self.assertEqual(source.read_bytes(),before)
            with patch('app.공통.기록도구.코스_점검'):
                result=service.식사반영(request)
            stored=기획기록.읽기(root,'meal-test')
            self.assertEqual(result['버전'],2)
            self.assertEqual(stored['코스안'][0],r['코스안'][0])
            self.assertEqual(stored['원래요청'],r['원래요청'])
            self.assertEqual(stored['코스안'][-1]['코스']['칸목록'][::2],self.c['칸목록'][::2])
            with self.assertRaisesRegex(ValueError,'최신'):service.식사반영(request)

    def test_저장_이동시간은_식사이후_방향을_쓰며_이전방향과_섞지않는다(self):
        def leg(a,b):return {'출발':a,'도착':b,'분':13 if b=='식당B' else 11,'경로':[[35.87,128.59],[35.871,128.591]]}
        with patch.object(self.m,'구간',side_effect=leg):
            result=self.m.반영(self.c,'m','식당B',{'지역':['중구']},미확인동의=True)
        self.assertEqual(result['식사목록'][0]['이동시간']['분'],11)
        self.assertEqual(result['식사목록'][0]['이후연결'],'뒤')

    def test_검토가_무효화된_같은_식당은_재확인_반영할수있다(self):
        self.c['식사목록'][0].update({'경로선택후보':'식당B','선택검토':{}})
        report=self.m.비교(self.c,'m','식당B',{'지역':['중구']})
        self.assertFalse(report['경로선택됨'])
        result=self.m.반영(self.c,'m','식당B',{'지역':['중구']},미확인동의=True)
        self.assertTrue(result['식사목록'][0]['선택검토'])


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

    def test_다른_일정_수정에서도_잠근_식사_선택과_원래권역을_보존한다(self):
        meal=next(m for m in self.이전['식사목록'] if m['칸ID']=='점심-1')
        fields={'식사기준장소':'원래 기준점','권역반경m':1200,'경로선택후보':meal.get('식당') or '선택식당',
                '선택검토':{'후보이동':[],'확인필요':['방문일 확인']}}
        meal.update(copy.deepcopy(fields))
        order=코스조립.이전_주문서(self.이전,self.표)
        result,issues=코스조립.조립({'안':order},self.표,{**self.입력,'부분수정':self.검사(재방문허용=True)},self.이전)
        self.assertEqual(issues,[])
        saved=next(m for m in result['식사목록'] if m['칸ID']=='점심-1')
        for key,value in fields.items():self.assertEqual(saved.get(key),value)

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
