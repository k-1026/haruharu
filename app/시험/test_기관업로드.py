import base64
import csv
import io
import unittest
import json
from unittest import mock
from tempfile import TemporaryDirectory

from app.단계2_수요근거.기관업로드 import 보관함, 근거합치기
from app.단계2_수요근거.근거추출 import 요약입력, 결과문서

HEAD=['출처','기간','지역','대상','항목','값','단위','표본수','세부항목']
ROW=['시연용 가상 자료(실제 조사 아님)','2026년 가을(가상)','대구광역시 중구','일본인 커플(가상)','저녁 음식 선호',45,'%',100,'불고기']
COND={'계절':'가을','언어권':['일본어'],'지역':['중구'],'체류기간':'1박2일'}


def 파일(rows=None):
    f=io.StringIO();w=csv.writer(f);w.writerow(HEAD);w.writerows(rows or [ROW]);return f.getvalue().encode('utf-8-sig')


class 업로드시험(unittest.TestCase):
    def test_기획_시작에서_요약_A_B_부분수정입력까지_업로드근거유지(self):
        from app.공통.기획실행 import 기획실행
        from app.서버.관리자실행 import 코스시험
        from app.서버.관리자조회 import 결과저장소
        from test_단계연결 import 코스
        from app.공통 import 기획기록
        from app.단계3_코스검토 import 처리기
        a=코스()
        a['칸목록'].append({'칸ID':'2일-오전-1','일차':2,'시간칸':'2일차오전','장소명':'대구광역시 중구 서문시장','근거ID':[]})
        b=json.loads(json.dumps(a));b['칸목록'][0]['장소명']='대구광역시 중구 향촌문화관'
        a['대안제안']={'코스':b,'이유':'시장 대신 문화관','무엇을':'낮 관광 변경'}
        calls=[]
        def ai(path,text):
            calls.append((path,text))
            if path.endswith('수요요약.md'):return '{"요약":"가상 수치를 실제 조사로 해석하지 않습니다."}'
            if path.endswith('검증.md'):return '{"통과":true,"문제":[]}'
            if path.endswith('총괄.md'):return '{"행동":"담당자에게","대상":"A","이유":"모의 확인"}'
            return json.dumps(a)
        with TemporaryDirectory() as folder,mock.patch('app.공통.run_stage.단계_실행',side_effect=AssertionError('실제 AI 금지')):
            service=기획실행(코스시험(결과저장소(folder),실행함수=ai),단계함수=ai)
            p=service.자료미리보기({'파일명':'가상.csv','내용':base64.b64encode(파일()).decode()})
            started=service.시작({**COND,'목표':'일본인 커플','자동진행동의':True,
                '기관업로드':{'업로드id':p['업로드id'],'시트':'CSV','확인':True}})
            service.작업.join(5)
            status=service.상태(started['기획id'])
            self.assertEqual(status['상태'],'완료',status.get('안내'))
            r=기획기록.읽기(folder,status['기록id'])
            self.assertEqual([x['안id'] for x in r['안']],['A','B'])
            self.assertIn('불고기',next(t for p,t in calls if p.endswith('수요요약.md')))
            for plan in ['A','B']:
                inp=처리기.코스입력(r,plan,folder,[])
                self.assertIn('불고기',str(inp['근거목록']))
            self.assertEqual(r['기관업로드']['적용행수'],1)

    def test_미리보기_확인_근거표_AI입력까지_원래출처와행을_유지(self):
        with TemporaryDirectory() as folder:
            store=보관함(folder)
            p=store.미리보기({'파일명':'가상.csv','내용':base64.b64encode(파일()).decode()})
            self.assertEqual(p['시트'][0]['행수'],1)
            with self.assertRaisesRegex(ValueError,'확인'):store.선택(p['업로드id'],'CSV',False)
            data=store.선택(p['업로드id'],'CSV',True)
            r={'조건':COND,'근거':[],'경고':[],'미확인':[],'선택파일':[]}
            근거합치기(r,data)
            self.assertIn('가상',r['근거'][0]['출처'])
            self.assertIn('행 2',r['근거'][0]['파일 · 행 위치'])
            self.assertIn('불고기',str(요약입력(r)))
            self.assertIn('45%',결과문서(r,'요약'))
            self.assertIn('실제 조사 아님',str(r['경고']))

    def test_숫자오류는_제외하고_서로다른대상은_합산하지않음(self):
        rows=[ROW,ROW[:5]+['NaN']+ROW[6:],ROW[:5]+[60]+ROW[6:]]
        with TemporaryDirectory() as folder:
            p=보관함(folder).미리보기({'파일명':'a.csv','내용':base64.b64encode(파일(rows)).decode()})
            self.assertEqual(p['시트'][0]['행수'],2)
            self.assertTrue(p['시트'][0]['경고'])

    def test_선택지역밖자료는_코스근거에_넣지않음(self):
        row=ROW.copy();row[2]='대구광역시 동구'
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=store.미리보기({'파일명':'a.csv','내용':base64.b64encode(파일([row])).decode()})
            r={'조건':COND,'근거':[],'경고':[],'미확인':[],'선택파일':[]}
            근거합치기(r,store.선택(p['업로드id'],'CSV',True))
            self.assertFalse(r['근거']);self.assertIn('제외',str(r['미확인']))

    def test_임의경로_형식_잘못된헤더_차단(self):
        with TemporaryDirectory() as folder:
            store=보관함(folder)
            for name,content in [('../x.csv',파일()),('a.pdf',b'pdf'),('a.csv',b'a,b\n1,2')]:
                with self.subTest(name=name),self.assertRaises(ValueError):
                    store.미리보기({'파일명':name,'내용':base64.b64encode(content).decode()})
            with self.assertRaises(ValueError):store.선택('../secret','CSV',True)

    def test_시연CSV와엑셀의_13행이_동일하고_가상표시_유지(self):
        from pathlib import Path
        samples=Path(__file__).parents[1]/'시험자료';results=[]
        with TemporaryDirectory() as folder:
            for ext in ['csv','xlsx']:
                p=samples/('시연용_가상설문_일본인커플_중구_가을.'+ext)
                preview=보관함(folder).미리보기({'파일명':p.name,'내용':base64.b64encode(p.read_bytes()).decode()})
                rows=preview['시트'][0]['행'];self.assertEqual(len(rows),13)
                self.assertTrue(all('실제 조사 아님' in x['출처'] for x in rows));results.append(rows)
            self.assertEqual(results[0],results[1])

    def test_봄조건에서_가을자료_전부제외돼도_근거없는_W경고를_만들지않음(self):
        from app.단계2_수요근거.근거추출 import 추출
        from app.공통.흐름 import 전달_준비,전달_검사
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=store.미리보기({'파일명':'가상.csv','내용':base64.b64encode(파일()).decode()})
            data=store.선택(p['업로드id'],'CSV',True)
            r=추출({**COND,'계절':'봄'});근거합치기(r,data)
            self.assertEqual(r['기관업로드']['적용행수'],0)
            self.assertTrue(r['기관업로드']['가상자료'])
            self.assertTrue(all(w['적용근거ID'] for w in r['경고']))
            handoff=전달_준비(r['조건'],'1박2일','경고를남기고진행',결과문서(r,'원래 자료만 참고'),'기관 데이터: 있음 / 미적용')
            self.assertEqual(전달_검사(handoff),[])
            self.assertIn('제외',str(handoff['미확인사항']))


class 조건대조시험(unittest.TestCase):
    """기획 조건(계절·지역)과 업로드 행의 기간·지역을 대조한다."""
    def 시연자료(self,store):
        from pathlib import Path
        p=Path(__file__).parents[1]/'시험자료'/'시연용_가상설문_일본인커플_중구_가을.csv'
        return store.미리보기({'파일명':p.name,'내용':base64.b64encode(p.read_bytes()).decode()})

    def test_봄조건에_가을자료면_적용0행_제외수와이유를_경고에(self):
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=self.시연자료(store)
            data=store.선택(p['업로드id'],'CSV',True,{**COND,'계절':'봄'})
            self.assertEqual(data['행'],[])
            self.assertEqual(len(data['제외행']),13)
            self.assertTrue(any('13행' in w and '계절' in w for w in data['경고']),data['경고'])
            r={'조건':{**COND,'계절':'봄'},'근거':[],'경고':[],'미확인':[],'선택파일':[]}
            근거합치기(r,data)
            self.assertEqual(r['기관업로드']['적용행수'],0)
            self.assertFalse(r['근거'])
            self.assertTrue(any('13행' in w for w in r['기관업로드']['경고']),r['기관업로드']['경고'])

    def test_가을조건이면_13행_모두적용(self):
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=self.시연자료(store)
            data=store.선택(p['업로드id'],'CSV',True,COND)
            self.assertEqual(len(data['행']),13);self.assertEqual(data['제외행'],[])
            r={'조건':COND,'근거':[],'경고':[],'미확인':[],'선택파일':[]}
            근거합치기(r,data)
            self.assertEqual(r['기관업로드']['적용행수'],13);self.assertEqual(len(r['근거']),13)

    def test_예전형식_적용자료도_근거합치기에서_다시걸러냄(self):
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=self.시연자료(store)
            data=store.선택(p['업로드id'],'CSV',True)  # 조건 없이 고른 예전 기록
            self.assertEqual(len(data['행']),13)
            r={'조건':{**COND,'계절':'봄'},'근거':[],'경고':[],'미확인':[],'선택파일':[]}
            근거합치기(r,data)
            self.assertEqual(r['기관업로드']['적용행수'],0)
            self.assertTrue(any('13행' in w for w in r['기관업로드']['경고']))

    def test_월로_적힌기간은_계절로_대조하고_정할수없으면_남기고경고(self):
        rows=[ROW[:1]+['2026년 4월']+ROW[2:],ROW[:1]+['2026.10']+ROW[2:],ROW[:1]+['2026년']+ROW[2:]]
        with TemporaryDirectory() as folder:
            store=보관함(folder);p=store.미리보기({'파일명':'a.csv','내용':base64.b64encode(파일(rows)).decode()})
            data=store.선택(p['업로드id'],'CSV',True,{**COND,'계절':'봄'})
            self.assertEqual([x['기간'] for x in data['행']],['2026년 4월','2026년'])
            self.assertEqual([x['기간'] for x in data['제외행']],['2026.10'])
            self.assertTrue(any('계절 확인 불가' in w and '4행' in w for w in data['경고']),data['경고'])

    def test_시작하면_적용자료json에_조건에맞는행만_보존(self):
        from app.공통.기획실행 import 기획실행
        from app.서버.관리자실행 import 코스시험
        from app.서버.관리자조회 import 결과저장소
        from pathlib import Path
        def ai(path,text):raise RuntimeError('이 시험은 AI를 부르지 않습니다')
        with TemporaryDirectory() as folder,mock.patch('app.공통.run_stage.단계_실행',side_effect=AssertionError('실제 AI 금지')):
            service=기획실행(코스시험(결과저장소(folder),실행함수=ai),단계함수=ai)
            p=self.시연자료(service.자료보관함)
            started=service.시작({**COND,'계절':'봄','목표':'일본인 커플','자동진행동의':True,
                '기관업로드':{'업로드id':p['업로드id'],'시트':'CSV','확인':True}})
            service.작업.join(5)
            saved=json.loads((Path(folder)/started['기획id']/'기관데이터'/'적용자료.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['행'],[]);self.assertEqual(len(saved['제외행']),13)
            self.assertTrue(saved['경고'])

    def 고르기(self,rows,head=HEAD,조건=None):
        f=io.StringIO();w=csv.writer(f);w.writerow(head);w.writerows(rows)
        with TemporaryDirectory() as folder:
            store=보관함(folder)
            p=store.미리보기({'파일명':'a.csv','내용':base64.b64encode(f.getvalue().encode('utf-8-sig')).decode()})
            return store.선택(p['업로드id'],'CSV',True,조건 or {**COND,'계절':'봄'})

    def test_기간이_비었거나_계절월이없으면_남기고_계절확인불가(self):
        rows=[ROW[:1]+[v]+ROW[2:] for v in ['','2025','연간','2024~2025']]
        data=self.고르기(rows)
        self.assertEqual(len(data['행']),4);self.assertEqual(data['제외행'],[])
        self.assertTrue(any('계절 확인 불가 4행' in w for w in data['경고']),data['경고'])

    def test_지역이_비었거나_대구전체면_남기고_지역확인불가(self):
        rows=[ROW[:2]+[v]+ROW[3:] for v in ['','대구 전체','대구광역시']]
        data=self.고르기(rows,조건=COND)
        self.assertEqual(len(data['행']),3);self.assertEqual(data['제외행'],[])
        self.assertTrue(any('지역 확인 불가 3행' in w for w in data['경고']),data['경고'])

    def test_계절과_상관없는표도_버리지않고_확인불가만_표시(self):
        rows=[['구청 안내','미확인','대구','방문객','입장료',3000,'원',''],
              ['구청 안내','상시','대구','방문객','장소 수',12,'곳','']]
        data=self.고르기(rows,head=HEAD[:-1])
        self.assertEqual(len(data['행']),2);self.assertEqual(data['제외행'],[])
        joined=' '.join(data['경고'])
        self.assertIn('계절 확인 불가',joined);self.assertIn('지역 확인 불가',joined)
        r={'조건':{**COND,'계절':'봄'},'근거':[],'경고':[],'미확인':[],'선택파일':[]}
        근거합치기(r,data)
        self.assertEqual(r['기관업로드']['적용행수'],2)

    def test_분명히_다른것만_제외_봄조건에_가을과_동구(self):
        rows=[ROW,ROW[:1]+['2026년 봄']+['대구광역시 동구']+ROW[3:],ROW[:1]+['2026년 봄']+ROW[2:]]
        data=self.고르기(rows)
        self.assertEqual([x['원래행'] for x in data['행']],[4])
        self.assertEqual([x['원래행'] for x in data['제외행']],[2,3])
