"""기존 결과의 명시적 재정리. AI 호출과 원본 덮어쓰기 없이 검사한다.

견본은 runs/20261122_131912/01회차/2단계_결과.md의 바이트 복사본이다.
실제 AI 출력의 처리 회귀시험용이며, 수치 정확성을 보증하는 조사 원본은 아니다.
"""
import unittest
import json
import tempfile
from pathlib import Path

from app.공통.기존결과 import 근거_펼치기, 재검사
from app.공통.흐름 import 전달_준비, 전달_검사, 근거표_읽기, 경고_읽기


class 기존결과시험(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.원문 = (Path(__file__).parents[1] / '시험자료/실제_2단계결과_20261122.md').read_text(encoding='utf-8')

    def test_전체근거와_수치_복원(self):
        글 = 근거_펼치기(self.원문)
        행들 = 근거표_읽기(글)
        self.assertEqual(len(행들), 200)
        byid = {r['근거ID']: r for r in 행들}
        self.assertEqual(set(byid), {f'R{i:02d}' for i in range(1, 201)})
        self.assertEqual(byid['R18']['수치'], 3)
        self.assertEqual(byid['R70']['수치'], 2)
        self.assertEqual(byid['R149']['수치'], 15.4)
        self.assertEqual(byid['R178']['수치'], 100)
        self.assertEqual(byid['R175']['수치'], 1.1)
        self.assertIn('관광지명', byid['R18']['파일_행위치'])
        self.assertIn('kosis_foreign_companion', byid['R125']['파일_행위치'])
        self.assertIn('kosis_foreign_purpose', byid['R121']['파일_행위치'])
        self.assertIn('n=80', byid['R182']['표본_대상'])
        self.assertIn('n=8', byid['R178']['표본_대상'])

    def test_전달검사_통과와_원문보존(self):
        글 = 근거_펼치기(self.원문)
        조건 = {'계절': '봄', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'}
        전달 = 전달_준비(조건, '1박2일', '경고를남기고진행', 글, '기관 데이터: 없음')
        self.assertEqual(전달_검사(전달), [])
        self.assertEqual(경고_읽기(글), 경고_읽기(self.원문))
        self.assertIn('응답자 30명 미만: 해석하지 않음', 글)
        # 기존 정상 10열 행은 원문 그대로 유지한다.
        for row in 근거표_읽기(self.원문):
            if row.get('열_수') == 10:
                actual = next(r for r in 전달['근거목록'] if r['근거ID'] == row['근거ID'])
                self.assertEqual(actual, row)

    def test_출처없는_축약표는_추측안함(self):
        with self.assertRaisesRegex(ValueError, '공통 출처'):
            근거_펼치기('## 근거표\n| ID | 조건 · 항목 | 수치 |\n|---|---|---|\n| R01 | 일본 · 밥 | 2% |\n')

    def test_횟수없는_묶음은_추측안함(self):
        with self.assertRaises(ValueError):
            근거_펼치기(self.원문.replace('ID : 관광지 (3번)', 'ID : 관광지'))

    def test_중복을_조용히_제거안함(self):
        글 = 근거_펼치기(self.원문.replace('R19 대구 근대골목', 'R18 대구 근대골목'))
        ids = [r['근거ID'] for r in 근거표_읽기(글)]
        self.assertEqual(ids.count('R18'), 2)

    def test_원래_수치130개와_경고13개_유지(self):
        새행들 = {r['근거ID']: r for r in 근거표_읽기(근거_펼치기(self.원문))}
        for r in 근거표_읽기(self.원문):
            self.assertEqual(새행들[r['근거ID']]['수치'], r['수치'])
        self.assertEqual(len(경고_읽기(근거_펼치기(self.원문))), 13)
        self.assertTrue(새행들['R178']['계산값'])

    def test_새폴더_저장과_사람선택_보존(self):
        with tempfile.TemporaryDirectory() as td:
            원본 = Path(td) / '원본'
            원본.mkdir()
            조건 = {'계절': '봄', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'}
            for 이름, 값 in [('1단계_선택.json', {'조건': 조건}),
                             ('2단계_선택.json', {'담당자선택_E3': '미선택', '확정체류기간': '1박2일'}),
                             ('3단계_전달_준비.json', {})]:
                (원본 / 이름).write_text(json.dumps(값, ensure_ascii=False), encoding='utf-8')
            (원본 / '1단계_결과.md').write_text('기존 결과', encoding='utf-8')
            (원본 / '2단계_결과.md').write_text(self.원문, encoding='utf-8')
            이전 = {p.name: p.read_bytes() for p in 원본.iterdir()}
            폴더, 전달 = 재검사(원본, Path(td) / '새기록')
            self.assertNotEqual(폴더, 원본)
            self.assertEqual(이전, {p.name: p.read_bytes() for p in 원본.iterdir()})
            self.assertEqual(전달['담당자선택_E3'], '미선택')
            self.assertTrue(any('E3' in s for s in 전달['검사결과']))
            self.assertEqual(전달['2단계결과_원문'], self.원문)
            self.assertNotIn('코스작성조건', 전달)


if __name__ == '__main__':
    unittest.main()
