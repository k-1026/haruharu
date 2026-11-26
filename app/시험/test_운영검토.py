import copy
import unittest
from datetime import date
from app.단계3_코스검토.운영검토 import 검토입력_검사, 검토_반영, 준비_검사, 화면정보, 휴무요일, 출발가능요일


def example():
    source={'확정체류기간':'1박2일','코스작성조건':{'시작일차':1,'종료일차':2,'시작지점':'장소A','종료지점':'장소B',
           '시작시각':'10:00','종료시각':'11:00','2일차오전구성':'자유시간'}}
    course={'코스시작종료':copy.deepcopy(source['코스작성조건']),'2일차오전구성':'자유시간',
            '칸목록':[{'안':'공통','칸ID':'관광','일차':1,'시간칸':'낮','장소명':'장소A','시각':{'값':'10:00','종류':'가정'},'머무는시간':60},
                    {'안':'공통','칸ID':'숙박','일차':1,'시간칸':'숙박','장소명':'숙박 권역','시각':{'값':'22:00','종류':'가정'},'머무는시간':600},
                    {'안':'공통','칸ID':'자유','일차':2,'시간칸':'2일차오전','장소명':'자유시간','시각':{'값':'08:00','종류':'가정'},'머무는시간':120}],
            '식사목록':[], '미확인사항':[], '확정조건':{'겹침처리':True},'남은경고':[]}
    data={'방문시작일':'2026-11-25','일정확인':[], '운영확인':[], '겹침처리':'노선겹침없음','겹침메모':'기존 상품 목록과 동선을 대조함', '담당자최종확인':True}
    for r in course['칸목록']:
        key=r['칸ID'];end={'관광':(1,'11:00'),'숙박':(2,'08:00'),'자유':(2,'10:00')}[key]
        data['일정확인'].append({'안':'공통','칸ID':key,'시작일차':r['일차'],'시작시각':r['시각']['값'],
                               '종료일차':end[0],'종료시각':end[1],'장소권역':r['장소명'],'이후연결':'다음 일정 또는 종료 장소로 연결',
                               '연결확인':True,'확인메모':'이동 여유와 연결을 담당자가 확인'})
    data['운영확인']=[{'안':'공통','칸ID':'관광','대상명':'장소A','처리':'유지','운영상태':'운영','영업시작':'09:00','영업종료':'18:00',
                     '익일종료':False,'마감시각':'17:00','출처명':'운영 주체 안내','출처URL':'https://example.invalid/hours','출처등급':'운영주체',
                     '확인일':'2026-11-23','방문일운영확인':True,'메모':'방문 요일과 휴무 확인'}]
    return course,source,data


class 운영검토시험(unittest.TestCase):
    def test_자유식_휴무후보만_명시적으로_제외가능(self):
        c,s,d=example();c['칸목록'][0]['시간칸']='저녁'
        c['식사목록']=[{'안':'공통','칸ID':'관광','방식':'자유식','추천후보':['후보A','후보B'],'식당':''}]
        op=d['운영확인'][0];op['대상명']='후보A';op['처리']='제외';op['운영상태']='휴무'
        other=copy.deepcopy(op);other.update({'대상명':'후보B','처리':'유지','운영상태':'운영'})
        d['운영확인'].append(other)
        result,ready=self.run_check(c,s,d)
        self.assertEqual(result['식사목록'][0]['추천후보'],['후보B'])
        self.assertTrue(ready['진행가능'])

    def run_check(self,course,source,data):
        checked=검토입력_검사(data,course,source)
        revised=검토_반영(course,checked)
        return revised,준비_검사(revised,source,checked)

    def test_정상기간과_출처확인_최종확인후에만_준비(self):
        c,s,d=example();before=copy.deepcopy(c)
        r,check=self.run_check(c,s,d)
        self.assertTrue(check['진행가능'])
        self.assertEqual(c,before)
        self.assertEqual(r['칸목록'][1]['머무는시간'],600)
        d['담당자최종확인']=False
        self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_운영마감초과_휴무_출처미확인은_통과안함(self):
        for field,value in [('영업종료','10:30'),('운영상태','휴무'),('출처명',''),('방문일운영확인',False)]:
            c,s,d=example();d['운영확인'][0][field]=value
            with self.subTest(field=field):self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_숙박역전_일정중복ID_잘못된날짜는_거부(self):
        c,s,d=example();d['일정확인'][1]['종료일차']=1;d['일정확인'][1]['종료시각']='08:00'
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)
        c,s,d=example();d['일정확인'].append(copy.deepcopy(d['일정확인'][0]))
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)
        c,s,d=example();d['방문시작일']='2026-02-30'
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)

    def test_미정기간과_미확인연결은_준비안됨(self):
        c,s,d=example();d['일정확인'][2]['종료시각']='';d['일정확인'][2]['연결확인']=False
        self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_수정없는화면정보에_숙박자유시간도_있음(self):
        c,s,d=example();info=화면정보(c,s)
        self.assertEqual(len(info['일정목록']),3)
        self.assertEqual(len(info['운영대상']),1)

    def test_첫_관광지_변경은_이전_근거를_새_장소에_붙이지_않음(self):
        c,s,d=example();c['칸목록'][0]['근거ID']=['R19'];c['칸목록'][0]['운영주체후보']=['옛 운영 주체']
        d['일정확인'][0]['장소권역']='향촌문화관'
        revised,ready=self.run_check(c,s,d)
        first=revised['칸목록'][0]
        self.assertEqual(first['장소명'],'향촌문화관')
        self.assertEqual(first['근거ID'],[])
        self.assertEqual(first['운영주체후보'],[])
        self.assertTrue(any('근거 없음' in w['문구'] and w['칸ID']=='관광' for w in revised['남은경고']))
        self.assertTrue(any('재확인 필요' in w for w in ready['유지경고']))
        self.assertEqual(c['칸목록'][0]['근거ID'],['R19'])


class 상시요일시험(unittest.TestCase):
    def check(self,휴무,확인일='2026-11-23'):
        c,s,d=example();d['방문시작일']='';d['운영확인'][0].update({'방문일운영확인':False,'확인일':확인일})
        checked=검토입력_검사(d,c,s)
        return 준비_검사(검토_반영(c,checked),s,checked,휴무조회=lambda n:휴무,오늘=date(2026,11,23))

    def test_휴무문구_해석(self):
        self.assertEqual(휴무요일('월~목 운영하지 않음')[0],{0,1,2,3})
        self.assertEqual(휴무요일('매주 월요일(공휴일이면 정상 개관), 1월 1일')[0],{0})
        self.assertTrue(휴무요일('매주 월요일, 1월 1일')[1])
        self.assertEqual(휴무요일('없음 (상시 개방)'),(set(),[]))
        self.assertIsNone(휴무요일('')[0])

    def test_상시상품은_출발일없이_요일로_통과(self):
        ready=self.check('매주 일요일')
        self.assertTrue(ready['진행가능'],ready['확인필요'])
        self.assertEqual(ready['출발가능요일']['공통'],list('월화수목금토'))

    def test_모든요일_휴무면_E4(self):
        ready=self.check('월~일 휴무')
        self.assertFalse(ready['진행가능'])
        self.assertTrue(any('E4' in m for m in ready['확인필요']))

    def test_정기휴무_빈칸은_미확인(self):
        self.assertTrue(any('정기휴무 미확인' in m for m in self.check('')['확인필요']))

    def test_확인일이_오래되면_재확인(self):
        self.assertTrue(any('다시 확인' in m for m in self.check('없음','2026-07-01')['확인필요']))

    def test_1박2일_2일차는_다음요일(self):
        c,s,d=example();d['방문시작일']=''
        c['칸목록'][2].update({'시간칸':'낮','장소명':'장소C'})
        c['2일차오전구성']='후보일정추가'
        d['일정확인'][2]['장소권역']='장소C';d['운영확인'][0]['방문일운영확인']=False
        extra=dict(d['운영확인'][0],칸ID='자유',대상명='장소C');d['운영확인'].append(extra)
        checked=검토입력_검사(d,c,s)
        days=출발가능요일(검토_반영(c,checked),checked,lambda n:'매주 월요일' if n=='장소C' else '없음')
        self.assertNotIn('일',days['안별']['공통'])  # 일요일 출발 → 2일차 월요일 휴무
        self.assertIn('월',days['안별']['공통'])


class 근거복원시험(unittest.TestCase):
    def test_원래장소로_되돌리면_근거복원(self):
        c,s,d=example();c['칸목록'][0].update({'장소명':'향촌문화관','근거ID':['R19']})
        이력=lambda k:[{'장소명':'대구광역시 중구 장소A','근거ID':['R19','R91'],'운영주체후보':['구청'],'시험id':'옛'}] if k==('공통','관광') else []
        d['일정확인'][0]['장소권역']='장소A';d['운영확인'][0]['대상명']='향촌문화관'
        revised=검토_반영(c,검토입력_검사(d,c,s),이력)
        first=revised['칸목록'][0]
        self.assertEqual(first['근거ID'],['R19','R91'])
        self.assertFalse(any(str(w.get('경고ID','')).startswith('C-장소변경-') for w in revised['남은경고']))

    def test_이미되돌렸는데_근거가_비었으면_저장할때_복원(self):
        c,s,d=example();c['칸목록'][0]['근거ID']=[]
        c['남은경고']=[{'경고ID':'C-장소변경-관광','칸ID':'관광','문구':'수요 근거 없음'}]
        revised=검토_반영(c,검토입력_검사(d,c,s),lambda k:[{'장소명':'장소A','근거ID':['R19'],'시험id':'옛'}])
        self.assertEqual(revised['칸목록'][0]['근거ID'],['R19']);self.assertEqual(revised['남은경고'],[])

    def test_다른장소면_근거를_붙이지_않음(self):
        c,s,d=example();d['일정확인'][0]['장소권역']='향촌문화관'
        revised=검토_반영(c,검토입력_검사(d,c,s),lambda k:[{'장소명':'장소A','근거ID':['R19'],'시험id':'옛'}])
        self.assertEqual(revised['칸목록'][0]['근거ID'],[])


class 정리사항시험(unittest.TestCase):
    def ready(self,c,s,d):
        checked=검토입력_검사(d,c,s);return 준비_검사(검토_반영(c,checked),s,checked)

    def test_AI가_노선겹침없음이면_E7_충족(self):
        c,s,d=example();d.update({'겹침처리':'','겹침메모':''})
        self.assertFalse(self.ready(c,s,d)['진행가능'])
        c['겹침이력']=[{'장소':'노선 겹침','상품ID':'없음','선택':'해당 없음'}]
        r=self.ready(c,s,d)
        self.assertTrue(r['진행가능'],r['확인필요'])
        self.assertTrue(any('E7' in w for w in r['유지경고']))

    def test_개인출처는_시험인정_경고유지_오래되면_막음(self):
        c,s,d=example();d['운영확인'][0]['출처등급']='개인'
        r=self.ready(c,s,d)
        self.assertTrue(r['진행가능'],r['확인필요'])
        self.assertTrue(any('개인 출처' in w for w in r['유지경고']))
        d['운영확인'][0]['출처등급']='기타'
        self.assertFalse(self.ready(c,s,d)['진행가능'])

    def test_공휴일_예외는_안내로만(self):
        for text in ['매주 월요일(월요일이 공휴일이면 다음 날 휴무), 1월 1일','매주 월요일(공휴일이면 정상 개관), 1월 1일, 설날·추석 당일. 휴관일이 법정공휴일이면 대체 휴관일은 공휴일 다음 첫 평일']:
            closed,notes=휴무요일(text)
            self.assertEqual(closed,{0});self.assertEqual(notes,[text])

    def test_CSV_등급_변환(self):
        from app.단계3_코스검토.장소정보 import 등급
        self.assertEqual(등급('개인'),'개인');self.assertEqual(등급('공식(S70); 개인(S71)'),'개인')
        self.assertEqual(등급('공식'),'공식');self.assertEqual(등급('미정'),'기타');self.assertEqual(등급(''),'')


class 지점요일시험(unittest.TestCase):
    def test_종료지점이_관람장소면_요일검사에_포함(self):
        c,s,d=example();d['방문시작일']=''
        조건={'시작지점':'동대구역','시작일차':1,'종료지점':'국채보상운동기념관','종료일차':2}
        지점=lambda n:'매주 월요일, 1월 1일' if n=='국채보상운동기념관' else None
        days=출발가능요일(c,d,lambda n:'없음',조건,지점)
        self.assertNotIn('일',days['안별']['공통'])  # 일요일 출발 → 2일차 월요일 휴관
        self.assertIn('토',days['안별']['공통'])
        self.assertTrue(any('종료 지점' in x for x in days['안내']))

    def test_CSV에_없는_지점은_넘어가고_빈칸휴무는_미확인(self):
        c,s,d=example()
        days=출발가능요일(c,d,lambda n:'없음',{'시작지점':'동대구역','시작일차':1},lambda n:None)
        self.assertEqual(days['미확인'],[])
        days=출발가능요일(c,d,lambda n:'없음',{'종료지점':'김광석길','종료일차':1},lambda n:'')
        self.assertTrue(days['미확인'])


class 권역자유식시험(unittest.TestCase):
    def test_CSV에_없는_권역만_있는_자유식은_운영확인_제외(self):
        from app.단계3_코스검토.운영검토 import 운영대상
        c,s,d=example()
        c['칸목록'].append({'안':'공통','칸ID':'점심2','일차':2,'시간칸':'점심','장소명':'자유식 · 중구 도심 (반월당역 주변)'})
        c['칸목록'].append({'안':'공통','칸ID':'점심1','일차':1,'시간칸':'점심','장소명':'자유식 · 대구광역시 중구 서문시장 권역'})
        c['식사목록']=[{'안':'공통','칸ID':'점심2','방식':'자유식','추천후보':[],'식당':''},
                     {'안':'공통','칸ID':'점심1','방식':'자유식','추천후보':[],'식당':''}]
        ids=[t['칸ID'] for t in 운영대상(c)]
        self.assertNotIn('점심2',ids)
        self.assertIn('점심1',ids)


class 상시개방시험(unittest.TestCase):
    def test_출처있는_상시개방만_하루전체(self):
        from app.단계3_코스검토.장소정보 import 상시개방
        self.assertTrue(상시개방({'운영시간':'상시 개방 (운영시간 없음)','출처ID':'S99'}))
        self.assertFalse(상시개방({'운영시간':'상시 개방 (운영시간 없음)','출처ID':''}))
        self.assertFalse(상시개방({'운영시간':'','출처ID':'S99'}))


if __name__=='__main__':unittest.main()
