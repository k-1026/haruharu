"""4단계 홍보 실행 · 5단계 산출물 시험. 실제 AI·네트워크 없이 가짜 응답으로 확인한다."""
import json
import tempfile
import time
import unittest
from pathlib import Path

import 기획기록 as 기록모듈
from 관리자조회 import 결과저장소
from 관리자실행 import 코스시험
from 기획실행 import 기획실행
from 홍보실행 import 홍보실행
import 산출물

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
