"""4단계 홍보 실행 · 5단계 산출물 시험. 실제 AI·네트워크 없이 가짜 응답으로 확인한다."""
import json
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

from app.공통 import 기획기록 as 기록모듈
from app.서버.관리자조회 import 결과저장소
from app.서버.관리자실행 import 코스시험
from app.공통.기획실행 import 기획실행
from app.단계4_홍보검토.홍보실행 import 홍보실행
from app.단계5_산출물 import 산출물

시험id = '20261125_100000/01회차/통합시험_100001_000001'


def 코스():
    return {'확정조건': {'시작종료확정': False, '겹침처리': False, '2일차오전선택': False},
            '코스시작종료': {'시작지점': '미확인', '시작시각': '미확인', '종료지점': '미확인', '종료시각': '미확인'},
            '시작종료후보': {'시작': {'장소': '근대골목 (코스 첫 장소)', '시각': '10:00'}},
            '칸목록': [{'칸ID': '낮-1', '일차': 1, '시간칸': '낮', '안': '공통', '장소명': '근대골목 (대구광역시 중구)', '시각': {'값': '10:00', '종류': '가정'}, '근거ID': ['R01'], '운영주체후보': ['O1']},
                    {'칸ID': '저녁-1', '일차': 1, '시간칸': '저녁', '안': '공통', '장소명': '자유식 · 동성로 권역', '시각': {'값': '18:00', '종류': '가정'}, '근거ID': [], '운영주체후보': []}],
            '식사목록': [{'칸ID': '저녁-1', '방식': '자유식', '시각': {'값': '18:00', '종류': '가정'}, '권역': '동성로', '식당': '', '추천후보': ['산호찜갈비'], '식비포함': '미정'}],
            '운영방식': '미정', '2일차오전구성': '해당없음', '장소스토리': [], '대체이력': [], '담당자결정': [],
            '겹침이력': [{'장소': '근대골목', '상품ID': 'G2', '선택': '미선택', '문구': '골목투어와 겹침'}],
            '남은경고': [{'경고ID': 'W1', '적용근거ID': ['R01'], '문구': '대구 전체 자료'}], '미확인사항': [], '체크리스트': []}


def 입력2():
    return {'조건': {'방문객': '외국인', '계절': '가을', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '당일'},
            '확정체류기간': '당일', '요약': '가을 일본 방문객 근거는 간접 근거입니다.',
            '근거목록': [{'근거ID': 'R01', '항목': '좋았던 점', '수치_원문': '23.0%', '출처': 'S12', '표본': 'n=83'}],
            '경고목록': [{'경고ID': 'W1', '종류': '간접 근거', '문구': '대구 전체 자료', '적용근거ID': ['R01']}],
            '담당자선택_E3': '경고를남기고진행'}


def 가짜홍보(번역='大邱近代通りを歩く', 경고='근거 없음'):
    def fn(agent, req):
        d = json.loads(req.split('입력 JSON:\n', 1)[1].split('\n\n이전 결과')[0])
        칸 = d['확정코스']['칸목록']
        out = {'코스카드': {'대상문장': '가을 일본어권 당일 여행자라면 → 이 코스', '코스이름': d['담당자선택']['코스이름'],
                         '한눈에': '근대골목 → 자유식 · 동성로', '식사안내': '저녁-1 자유식 · 추천 후보 외 선택 가능', '남은경고': ['W1 대구 전체 자료']},
               '대응표': [{'장면ID': r['칸ID'], '장소': r['장소명'], '홍보물': 'SNS 카드뉴스', '상태': '초안'} for r in 칸],
               '문구목록': [{'장면ID': r['칸ID'], '제목': '근대골목 산책' if r['칸ID'] == '낮-1' else '동성로 저녁', '본문': '약 10:00 출발',
                          '사실근거': {'출처ID': 'S12', '근거ID목록': ['R01']} if r['근거ID'] else '연결문장', '경고': '없음' if r['근거ID'] else 경고} for r in 칸],
               '번역목록': [{'장면ID': r['칸ID'], '언어': '일본어', '번역': 번역 if r['칸ID'] == '낮-1' else '東城路で夕食', '역번역': '근대골목 걷기', '상태': 'AI초안'} for r in 칸],
               '표현필터': [{'장면ID': '낮-1', '표현': '인기', '종류': '근거 없는 스토리', '처리': '미처리'}],
               '코스변경': [], '시안': {'톤앤매너': 'A', '장면별': [{'장면ID': r['칸ID'], '주연': '너구리', '배치세트': '발견', '포즈': '새 포즈 필요'} for r in 칸], '배치점검': '없음'}}
        fn.호출 += 1
        return '```json\n' + json.dumps(out, ensure_ascii=False) + '\n```'
    fn.호출 = 0
    return fn


class 홍보시험(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        runs = Path(self.tmp.name) / 'runs'
        폴더 = runs / 시험id
        폴더.mkdir(parents=True)
        (폴더 / '3단계_입력.json').write_text(json.dumps(입력2(), ensure_ascii=False), encoding='utf-8')
        (폴더 / '통합시험_상태.json').write_text('{}', encoding='utf-8')
        기록 = 기록모듈.새_기록(입력2()['조건'], '사람:시험', 기록id=시험id.split('/')[-1])
        기록모듈.추가(기록, '코스안', {'안id': 'A', '버전': 1, '코스': 코스()}, '에이전트:코스')
        기록모듈.저장(기록, runs)
        self.runs = runs

    def tearDown(self):
        self.tmp.cleanup()

    def 서비스(self, fn):
        return 홍보실행(기획실행(코스시험(결과저장소(self.runs))), fn)

    def 값(self, **바꿈):
        return {'시험id': 시험id, '안id': 'A', '시작지점': '근대골목', '시작시각': '10:00', '종료지점': '동성로', '종료시각': '20:00',
                '겹침처리': '연결하기', '톤앤매너': 'A+B', '홍보물': ['SNS 카드뉴스'], '확인동의': True, **바꿈}

    def 기다리기(self, s, hid):
        for _ in range(100):
            st = s.상태(hid)
            if st['상태'] != '진행중':
                return st
            time.sleep(0.05)
        self.fail('끝나지 않음')

    def test_확인없이는_시작하지_않음(self):
        s = self.서비스(가짜홍보())
        with self.assertRaises(ValueError):
            s.시작(self.값(확인동의=False))
        with self.assertRaises(ValueError):
            s.시작(self.값(겹침처리=''))
        with self.assertRaises(ValueError):
            s.시작(self.값(시작시각='10시'))

    def test_준비값은_숙소를_끝으로_쓰지_않음(self):
        p = self.서비스(가짜홍보()).준비(시험id, 'A')
        self.assertEqual(p['기본값']['시작지점'], '근대골목')
        self.assertEqual(p['체류기간'], '당일')
        self.assertEqual(len(p['겹침이력']), 1)

    def test_홍보에도_설문원문과_해석범위를_전달한다(self):
        s = self.서비스(가짜홍보())
        원문 = {'원자료항목명': '동성로/중구 시내 일원', '표본_대상': '일본 n=83',
              '파일_행위치': '원본.csv:243', '경고': ['개별 시설 수치 아님'], '기준연도': '2024', '연도': '2024'}
        입력 = 입력2()
        입력['근거목록'][0].update(원문)
        _, 데이터 = s._요청(코스(), 입력, {'톤앤매너': 'A', '홍보물': ['SNS 카드뉴스'], '코스이름': '시험'})
        for k, v in 원문.items():
            self.assertEqual(데이터['근거목록'][0].get(k), v, k)

    def test_코스가_바뀌면_옛_홍보는_조회만_가능하고_산출물은_재확인한다(self):
        s = self.서비스(가짜홍보())
        hid = s.시작(self.값())['홍보id']
        self.기다리기(s, hid)
        s.산출물({'홍보id': hid, '홍보확인': True})
        옛문서 = s.문서(hid, '결재')
        기록 = 기록모듈.읽기(self.runs, 시험id.split('/')[-1])
        기록모듈.추가(기록, '코스안', {'안id': 'A', '버전': 2, '코스': 코스()}, '코드:시험')
        기록모듈.저장(기록, self.runs)
        self.assertTrue(s.결과(hid).get('다시확인필요'))
        self.assertEqual(s.결과(hid)['현재코스버전'], 2)
        self.assertEqual(s.문서(hid, '결재'), 옛문서)
        with self.assertRaisesRegex(ValueError, '코스.*버전'):
            s.산출물({'홍보id': hid, '홍보확인': True})

    def test_다른안의_새버전은_현재홍보를_무효화하지않는다(self):
        s = self.서비스(가짜홍보())
        hid = s.시작(self.값())['홍보id']
        self.기다리기(s, hid)
        기록 = 기록모듈.읽기(self.runs, 시험id.split('/')[-1])
        기록모듈.안_추가(기록, 'B', '시험 대안', '코드:시험')
        기록모듈.추가(기록, '코스안', {'안id': 'B', '버전': 2, '코스': 코스()}, '코드:시험')
        기록모듈.저장(기록, self.runs)
        self.assertIs(s.결과(hid).get('다시확인필요'), False)

    def test_AI오류는_실패로_남기고_5단계로_넘기지않는다(self):
        def 오류(agent, req):
            raise TimeoutError('시험용 응답 시간 초과')
        s = self.서비스(오류)
        hid = s.시작(self.값())['홍보id']
        self.assertEqual(self.기다리기(s, hid)['상태'], '실패')
        self.assertTrue((self.runs / hid / 'AI_오류.json').is_file())
        with self.assertRaises(ValueError):
            s.산출물({'홍보id': hid, '홍보확인': True})

    def test_1부터5까지_기존실행기를_연결하고_원본과_경고를_보존한다(self):
        """실제 CSV·실행·검사·저장, AI 응답과 사람 입력만 시험값. 실제 승인 아님."""
        호출 = []

        def 단계(agent, req):
            호출.append(agent)
            if agent.endswith('수요요약.md'):
                return '{"요약":"자료의 조사 범위와 한계를 구분한 시험용 요약입니다."}'
            if agent.endswith('검증.md'):
                return '{"통과":true,"문제":[]}'
            if agent.endswith('총괄.md'):
                return '{"행동":"담당자에게","대상":"A","이유":"연결 시험 종료"}'
            raise AssertionError(agent)

        def 주문(agent, req):
            호출.append(agent)
            장소 = {r.split('|')[1]: r.split('|')[0] for r in req.splitlines()
                  if r.startswith('P') and '|' in r}
            def 칸(id, 시간칸, 이름):
                p = next(v for k, v in 장소.items() if 이름 in k)
                return {'칸ID': id, '일차': 1, '시간칸': 시간칸, '장소': p,
                        '머무는분': 60, '근거': [], '운영': [], '이유': '연결 시험용'}
            return json.dumps({'A': {'칸': [칸('낮-1', '낮', '근대골목'), 칸('점심-1', '점심', '서문시장'),
                                           칸('저녁-1', '저녁', '산호찜갈비')], '식사': []},
                               'B': None, '대안불가이유': '이 시험은 A안의 단계 연결만 확인'}, ensure_ascii=False)

        기획 = 기획실행(코스시험(결과저장소(self.runs), 실행함수=주문), 단계함수=단계)
        with mock.patch('app.공통.run_stage.단계_실행', side_effect=AssertionError('자동시험의 실제 AI 호출 금지')):
            p = 기획.시작({'계절': '가을', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '당일',
                         '목표': '단계 연결 시험 (실제 승인 아님)', '희망': [], '자동진행동의': True})
            기획.작업.join(15)
            self.assertFalse(기획.작업.is_alive())
            p = 기획.상태(p['기획id'])
            self.assertEqual(p['상태'], '완료', p.get('안내'))
            sid = p['기획id'] + '/' + p['기록id']
            원본 = 기록모듈.읽기(self.runs, p['기록id'])
            self.assertIsNone(원본['선택'])
            홍보 = 홍보실행(기획, 가짜홍보())
            확인 = self.값(시험id=sid, 겹침처리='겹침 확인 후 그대로 진행', 코스이름='자동시험 전용')
            with self.assertRaises(ValueError):
                홍보.시작({**확인, '확인동의': False})
            hid = 홍보.시작(확인)['홍보id']
            self.assertEqual(self.기다리기(홍보, hid)['상태'], '홍보완료')
            out = 홍보.산출물({'홍보id': hid, '홍보확인': True})
        이후 = 기록모듈.읽기(self.runs, p['기록id'])
        self.assertEqual(원본['코스안'], 이후['코스안'])
        self.assertEqual(원본['근거'], 이후['근거'])
        self.assertEqual(len(out['산출물']['문서']), 3)
        self.assertIn('.claude/agents/수요요약.md', 호출)
        self.assertIn('.claude/agents/코스주문.md', 호출)
        self.assertIn('.claude/agents/검증.md', 호출)
        for 이름 in ['결재파일.html', '제안서.html', '홍보물묶음.html']:
            글 = (self.runs / hid / '산출물' / 이름).read_text(encoding='utf-8')
            self.assertIn('근거 없음', 글)
            self.assertNotIn('<script', 글)

    def test_4단계부터_5단계까지(self):
        fn = 가짜홍보()
        s = self.서비스(fn)
        hid = s.시작(self.값(코스이름='시험 코스'))['홍보id']
        st = self.기다리기(s, hid)
        self.assertEqual(st['상태'], '홍보완료', st)
        self.assertEqual(fn.호출, 1)  # 검사 통과면 다시 부르지 않는다
        폴더 = self.runs / hid
        확정 = json.loads((폴더 / '3단계_확정.json').read_text(encoding='utf-8'))
        self.assertTrue(all(확정['확정조건'][k] for k in ['시작종료확정', '겹침처리', '2일차오전선택']))
        self.assertEqual(확정['코스시작종료']['종료지점'], '동성로')
        원본 = 기록모듈.읽기(self.runs, 시험id.split('/')[-1])
        self.assertEqual(원본['코스안'][0]['코스']['코스시작종료']['시작지점'], '미확인')  # 원래 초안은 그대로
        self.assertEqual(원본['선택']['안id'], 'A')
        r = s.결과(hid)
        self.assertEqual(r['홍보']['번역목록'][0]['상태'], 'AI 초안')
        with self.assertRaises(ValueError):
            s.산출물({'홍보id': hid, '홍보확인': False})
        with self.assertRaises(ValueError):
            s.산출물({'홍보id': hid, '홍보확인': True, '표현처리': {r['필터키'][0]: '고침필요'}})
        out = s.산출물({'홍보id': hid, '홍보확인': True, '표현처리': {r['필터키'][0]: '그대로둠'}, '받는쪽': 'O1 대구광역시 중구청 관광과'})
        self.assertEqual(s.상태(hid)['상태'], '산출물완료')
        self.assertEqual({x['항목']: x['결과'] for x in out['산출물']['대조']['항목']}['코스'], '같음')
        for name in ['결재파일.html', '제안서.html', '홍보물묶음.html']:
            text = (폴더 / '산출물' / name).read_text(encoding='utf-8')
            self.assertIn('W1', text)  # 경고는 세 파일 모두에 따라간다
            self.assertIn('[미확인: 식비 포함 여부]', text) if name != '홍보물묶음.html' else None
            self.assertNotIn('<script', text)
        self.assertIn('인기', (폴더 / '산출물/홍보물묶음.html').read_text(encoding='utf-8'))  # E5 그대로 둠 기록

    def test_검사에_걸리면_한번만_다시_부름(self):
        fn = 가짜홍보(번역='近代の路地')  # 용어집 표기 大邱近代通り 없음
        s = self.서비스(fn)
        hid = s.시작(self.값())['홍보id']
        st = self.기다리기(s, hid)
        self.assertEqual(fn.호출, 2)
        self.assertEqual(st['상태'], '홍보완료')
        self.assertTrue(any('용어집' in x for x in s.결과(hid)['검사']['검사결과']))

    def test_대조는_빠진_장면과_근거없음_경고를_찾음(self):
        홍보 = json.loads(가짜홍보(경고='없음')('', '입력 JSON:\n' + json.dumps({'확정코스': 코스(), '담당자선택': {'코스이름': 'x'}})).split('\n', 1)[1].rsplit('\n', 1)[0])
        홍보['대응표'] = 홍보['대응표'][:1]
        b = 산출물.묶기(입력2()['조건'], 입력2(), 코스(), 홍보, {'톤앤매너': 'A'})
        결과 = {x['항목']: x['결과'] for x in b['대조']['항목']}
        self.assertEqual(결과['코스'], '다름')
        self.assertEqual(결과['미확인 표시'], '다름')
        self.assertTrue(any(x['단계'] == '5단계' for x in b['남은경고']))


if __name__ == '__main__':
    unittest.main()
