"""통합시험 초안의 단계 경계. 실제 AI·네트워크를 사용하지 않는다."""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from 단계연결 import JSON_읽기, 코스_검사, 홍보_검사, 통합_실행


def 코스():
    return {
        '확정조건': {'시작종료확정': True, '겹침처리': True, '2일차오전선택': True},
        '코스시작종료': {'시작지점': '동대구역', '시작시각': '10:00', '종료지점': '역사관', '종료시각': '14:00'},
        '칸목록': [{'칸ID': '낮-1', '안': '공통', '일차': 1, '시간칸': '낮', '장소명': '근대골목', '시각': {'값': '10:30', '종류': '가정'}, '머무는시간': 90, '근거ID': ['R01'], '운영주체후보': []}],
        '식사목록': [], '운영방식': '미정', '2일차오전구성': '해당없음',
        '장소스토리': [], '대체이력': [], '담당자결정': [], '겹침이력': [],
        '남은경고': [], '미확인사항': [], '체크리스트': [],
    }


def 홍보():
    return {'코스카드': {'대상문장': '일본어', '코스이름': '미정', '한눈에': '근대골목', '식사안내': '식사 칸 없음', '남은경고': []},
            '대응표': [], '문구목록': [{'장면ID': '낮-1', '제목': '골목', '본문': '걸어요', '사실근거': '연결문장', '경고': []}],
            '번역목록': [{'장면ID': '낮-1', '언어': '영어', '번역': 'Walk', '역번역': '걷기', '상태': 'AI 초안', '검토자': '', '날짜': ''}],
            '표현필터': [], '코스변경': [], '시안': {'톤앤매너': '미선택', '장면별': [], '배치점검': []}}


입력2 = {'확정체류기간': '당일', '근거목록': [{'근거ID': 'R01'}], '경고목록': [], '코스작성조건': {'2일차오전구성': '해당없음'}}


class 경계시험(unittest.TestCase):
    def test_미확인사항_대상칸ID_별칭과_실제없는칸_구분(self):
        value = 코스()
        value['미확인사항'] = [{'대상 칸ID': '낮-1', '내용': '확인 필요'}]
        self.assertEqual(코스_검사(value, 입력2), [])
        value['미확인사항'][0]['대상 칸ID'] = '없는칸'
        self.assertTrue(any('없는 안·칸ID' in p for p in 코스_검사(value, 입력2)))

    def test_담당자선택_자유시간은_관광지_수요근거_요구안함(self):
        value = 코스()
        value['2일차오전구성'] = '자유시간'
        value['칸목록'].append({'칸ID': '오전', '일차': 2, '시간칸': '2일차오전',
                              '장소명': '자유시간 (담당자 선택)', '시각': {'값': '', '종류': '미정'}, '근거ID': []})
        source = {**입력2, '확정체류기간': '1박2일', '코스작성조건': {'2일차오전구성': '자유시간'}}
        self.assertFalse(any('근거 없음' in p for p in 코스_검사(value, source)))
        value['칸목록'][-1]['장소명'] = '새 관광지'
        value['칸목록'][-1]['시간칸'] = '낮'  # 일반 관광 칸은 계속 수요 근거를 요구한다.
        self.assertTrue(any('근거 없음' in p for p in 코스_검사(value, source)))

    def test_설명뒤_단일JSON블록_읽기(self):
        self.assertEqual(JSON_읽기('지침을 읽었습니다.\n```json\n{"칸목록": []}\n```\n결과입니다.'), {'칸목록': []})

    def test_복수블록과_설명속_불완전JSON은_추측하지않음(self):
        for text in ['```json\n{}\n```\n```json\n{}\n```',
                     '설명 {"a":1} 뒤 설명',
                     '설명\n```json\n{"a":1,"a":2}\n```',
                     '설명\n```json\n{"a":NaN}\n```']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                JSON_읽기(text)

    def test_JSON은_객체만(self):
        self.assertEqual(JSON_읽기('```json\n{"a":1}\n```'), {'a': 1})
        for 원문 in ['[]', '설명만 있음', '{"a": NaN}']:
            with self.subTest(원문=원문), self.assertRaises(ValueError):
                JSON_읽기(원문)

    def test_정상_코스(self):
        self.assertEqual(코스_검사(코스(), 입력2), [])

    def test_없는_근거와_미확인_시각(self):
        값 = 코스()
        값['칸목록'][0]['근거ID'] = ['R99']
        값['칸목록'][0]['시각'] = {'값': '13:00', '종류': '미정'}
        문제 = 코스_검사(값, 입력2)
        self.assertTrue(any('R99' in p for p in 문제))
        self.assertTrue(any('미정' in p for p in 문제))

    def test_수요근거_없음은_빈목록으로_보존(self):
        값 = 코스()
        값['칸목록'][0]['근거ID'] = []
        self.assertTrue(any('근거 없음' in p for p in 코스_검사(값, 입력2)))
        값['남은경고'] = [{'경고ID': 'C-1', '칸ID': '낮-1', '문구': '수요 근거 없음', '적용근거ID': []}]
        self.assertEqual(코스_검사(값, 입력2), [])

    def test_자유식_확정식당_오류(self):
        값 = 코스()
        값['식사목록'] = [{'칸ID': '낮-1', '방식': '자유식', '식당': '테스트식당', '식비포함': '미정', '추천후보': [], '권역': '중구', '시각': {'값': '', '종류': '미정'}}]
        self.assertTrue(any('자유식' in p for p in 코스_검사(값, 입력2)))

    def test_오전_자동결정과_확정조건_거짓(self):
        값 = 코스()
        값['2일차오전구성'] = '종료장소로바로'
        값['확정조건']['시작종료확정'] = False
        앞 = {**입력2, '확정체류기간': '1박2일', '코스작성조건': {'2일차오전구성': '미선택'}}
        self.assertTrue(any('오전' in p for p in 코스_검사(값, 앞)))
        self.assertTrue(any('시작종료확정' in p for p in 코스_검사(값, 앞)))

    def test_다른안의_동일칸ID는_구분(self):
        값 = 코스()
        둘 = copy.deepcopy(값['칸목록'][0]); 둘['안'] = '토요일안'
        값['칸목록'].append(둘)
        self.assertEqual(코스_검사(값, 입력2), [])
        값['칸목록'].append(copy.deepcopy(둘))
        self.assertTrue(any('중복' in p for p in 코스_검사(값, 입력2)))

    def test_홍보는_에이전트가_검토완료_못함(self):
        self.assertEqual(홍보_검사(홍보(), 코스()), [])
        값 = 홍보(); 값['번역목록'][0]['상태'] = '검토 완료'
        self.assertTrue(any('AI 초안' in p for p in 홍보_검사(값, 코스())))

    def test_알수없는_장면과_E6_진행중(self):
        값 = 홍보(); 값['문구목록'][0]['장면ID'] = '없는장면'
        값['코스변경'] = [{'요청장면ID': '낮-1', '재검토상태': '진행중'}]
        문제 = 홍보_검사(값, 코스())
        self.assertTrue(any('없는장면' in p for p in 문제))
        self.assertTrue(any('E6' in p for p in 문제))

    def test_담당자의_식사방식을_AI가_바꾸지_않음(self):
        값 = 코스()
        값['칸목록'][0]['시간칸'] = '점심'
        값['식사목록'] = [{'칸ID': '낮-1', '방식': '지정식', '식당': '식당A', '식비포함': '포함', '시각': {'값': '12:00', '종류': '가정'}, '권역': '중구', '추천후보': [], '이후연결': '다음 장소', '이동시간': {'분': '미확인', '적용조건': '미확인'}}]
        앞 = copy.deepcopy(입력2)
        앞['코스작성조건']['식사목록'] = [{'일차': 1, '시간칸': '점심', '방식': '자유식', '식당': '미선택', '식비포함': '미정'}]
        self.assertTrue(any('담당자 식사' in p for p in 코스_검사(값, 앞)))

    def test_홍보_빈문구와_중복장면_잡음(self):
        값 = 홍보(); 값['문구목록'] = []
        self.assertTrue(any('문구목록' in p for p in 홍보_검사(값, 코스())))
        값 = 홍보(); 값['문구목록'].append(copy.deepcopy(값['문구목록'][0]))
        self.assertTrue(any('중복' in p for p in 홍보_검사(값, 코스())))


class 연결시험(unittest.TestCase):
    def 실행(self, 선택=1, 코스값=None, 없는파일=False):
        async def 호출(에이전트, 입력):
            기록.append(입력)
            return json.dumps((코스값 or 코스()) if len(기록) == 1 else 홍보(), ensure_ascii=False)
        기록 = []
        with tempfile.TemporaryDirectory() as 경로:
            루트 = Path(경로)
            for 번호 in [3, 4]:
                (루트 / f'{번호}.md').write_text('agent', encoding='utf-8')
            for 경로명 in ['지침/3_코스검토/2_입력.md', '지침/3_코스검토/6_출력.md', '지침/4_홍보검토/2_입력.md', '지침/4_홍보검토/9_출력.md', '지침/공통/단계_넘김.md']:
                파일 = 루트 / 경로명; 파일.parent.mkdir(parents=True, exist_ok=True); 파일.write_text('초안 규칙', encoding='utf-8')
            단계 = {3: {'에이전트': '3.md'}, 4: {'에이전트': '없음.md' if 없는파일 else '4.md'}}
            with mock.patch('단계연결.저장소', 루트), mock.patch('단계연결.STAGES', 단계), mock.patch('builtins.print'):
                결과 = asyncio.run(통합_실행(루트 / '결과', 입력2, 호출, lambda *args: 선택))
            return 결과, 기록, list(루트.rglob('*.json'))

    def test_없는파일이면_AI_호출안함(self):
        결과, 기록, _ = self.실행(없는파일=True)
        self.assertEqual(기록, [])
        self.assertEqual(결과['상태'], '대기')

    def test_담당자_미확정이면_4단계_호출안함(self):
        결과, 기록, _ = self.실행(선택=2)
        self.assertEqual(len(기록), 1)
        self.assertEqual(결과['상태'], '초안')

    def test_정상_3에서4_연결(self):
        결과, 기록, 파일 = self.실행()
        self.assertEqual(len(기록), 2)
        self.assertEqual(결과['상태'], '4단계시험완료')
        self.assertTrue(any('4단계_전달_검사.json' in str(p) for p in 파일))

    def test_잘못된코스는_원문보존후_정지(self):
        결과, 기록, _ = self.실행(코스값={'칸목록': []})
        self.assertEqual(len(기록), 1)
        self.assertEqual(결과['상태'], '검사실패')

    def test_4단계에_확정코스와_조건을_전달(self):
        _, 기록, _ = self.실행()
        self.assertIn('확정코스', 기록[1])
        self.assertNotIn('확정コース', 기록[1])


if __name__ == '__main__':
    unittest.main()
