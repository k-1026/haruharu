import csv
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.단계2_수요근거 import 근거추출
from app.공통.흐름 import 전달_준비, 전달_검사


조건 = {'계절': '가을', '언어권': ['일본어'], '지역': ['중구'], '체류기간': '1박2일'}


class 추출시험(unittest.TestCase):
    def test_실제자료의_일본어_가을_중구_조건으로_전달검사를_통과한다(self):
        r = 근거추출.추출(조건)
        self.assertTrue(r['근거'])
        self.assertTrue(r['선택행'])
        글 = 근거추출.결과문서(r, '코드가 고른 근거를 참고합니다.')
        self.assertEqual(전달_검사(전달_준비(조건, '1박2일', '경고를남기고진행', 글, '기관 데이터: 없음')), [])
        self.assertTrue(any('닭튀김/치킨' in row['원자료 항목명'] for row in r['근거']))
        for row in r['선택행']:
            if row['파일'].endswith('대구_외국인추천음식상위20_2024.csv'):
                self.assertIn((row['값']['category'], row['값']['subgroup']),
                              [('전체', '소계'), ('조사시기', '9~10월(3기)'), ('거주국가', '일본'), ('대구 체류 여부', '숙박여행')])
        self.assertTrue(any('시험값' in w['문구'] for w in r['경고']))

    def test_원자료값과_행위치를_보존한다(self):
        r = 근거추출.추출(조건)
        row = next(x for x in r['선택행'] if x['파일'].endswith('대구_외국인추천음식상위20_2024.csv'))
        with (근거추출.자료루트 / row['파일']).open(encoding='utf-8-sig', newline='') as f:
            original = list(csv.DictReader(f))[row['행'] - 2]
        self.assertEqual(row['값'], original)

    def test_동구_당일은_중구전용과_숙박형전용자료를_쓰지않는다(self):
        r = 근거추출.추출({**조건, '지역': ['동구'], '체류기간': '당일'})
        files = {x['파일'] for x in r['선택행']}
        self.assertNotIn('datalab_jung_origin_country_2022_2026.csv', files)
        self.assertFalse(any('paid_attraction' in p or '숙박유형' in p or '숙박선택이유' in p for p in files))

    def test_자료가없으면_미확인으로_남기고_지어내지않는다(self):
        with TemporaryDirectory() as folder:
            r = 근거추출.추출(조건, Path(folder))
        self.assertEqual(r['근거'], [])
        self.assertTrue(r['미확인'])

    def test_요약_AI에_근거표를_다시쓰게하지않는다(self):
        r = 근거추출.추출(조건)
        글 = 근거추출.결과문서(r, '요약\n## 근거표\n가짜 수치 999')
        self.assertEqual(글.count('## 근거표'), 1)
        self.assertNotIn('가짜 수치', 글)

    def test_AI입력만_줄이고_저장입력과_원래근거는_보존한다(self):
        r = 근거추출.추출(조건)
        s = 근거추출.요약입력(r)
        data = 전달_준비(조건, '1박2일', '경고를남기고진행', 근거추출.결과문서(r, '시험 요약'), '기관 데이터: 없음')
        data['코드근거추출'] = {'AI전달근거ID': [x[0] for x in s['근거']]}
        before = copy.deepcopy(data)
        compact = 근거추출.전달입력_줄이기(data)
        self.assertEqual(data, before)
        self.assertNotIn('2단계결과_원문', compact)
        self.assertLess(len(compact['근거목록']), len(data['근거목록']))
        kept = {r['근거ID'] for r in compact['근거목록']}
        self.assertTrue(all(set(w['적용근거ID']) <= kept for w in compact['경고목록']))
        self.assertTrue(any('치킨' in r['원자료항목명'] for r in compact['근거목록']))

    def test_관심근거를_줄여도_선택한_지역과_언어권_조합을_모두_남긴다(self):
        rows = []
        for i, (district, language) in enumerate([('중구', '일본어'), ('중구', '영어권'), ('동구', '일본어'), ('동구', '영어권')], 1):
            rows.append({'ID': f'R{i:02}', '항목': '방문객', '파일 · 행 위치': 근거추출.관심파일 + f' 행 {i+1}',
                         '연도': '2024', '원자료 항목명': f'{district} / {language} / 관광지 관심 목록 등장',
                         '수치': f'{i}회', '표본 · 대상': '관심 목록'})
        result = 근거추출.요약입력({'조건': 조건, '근거': rows, '경고': [], '미확인': []})
        self.assertEqual({row[0] for row in result['근거']}, {'R01', 'R02', 'R03', 'R04'})


if __name__ == '__main__':
    unittest.main()
