"""장소 위치 확인과 지도 길 자동 수집. 실제 외부 조회 없음(가짜 응답)."""
import json
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import 장소위치

저장소 = Path(__file__).resolve().parent.parent
장소CSV = '장소운영정보_중구동구_데모코스_2026.csv'


def 경로응답(a, b):
    """OSRM 도보 응답 흉내: 출발·도착 좌표를 그대로 잇는 선."""
    return {'code': 'Ok', 'routes': [{'geometry': {'type': 'LineString', 'coordinates': [[a[1], a[0]], [b[1], b[0]]]},
                                      'distance': 500, 'duration': 400}],
            'waypoints': [{'distance': 3}, {'distance': 4}]}


class 장소위치시험(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / 'data'; self.data.mkdir()
        for name in [장소CSV, '이동시간_중구동구_데모코스_2026.csv', '지도_대표위치.json', '장소좌표_검토용.csv']:
            shutil.copy(저장소 / 'research/data' / name, self.data / name)
        self.routes = Path(self.tmp.name) / 'road-routes.json'
        self.routes.write_text(json.dumps({'routes': {}}), encoding='utf-8')
        self.reports = Path(self.tmp.name) / '신고.json'
        env = mock.patch.dict(os.environ, {'HARUHARU_DATA_DIR': str(self.data)})
        env.start(); self.addCleanup(env.stop)

    def 행들(self):
        import csv
        with (self.data / 장소CSV).open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    def test_확인은_그_행의_좌표열만_바꾼다(self):
        before = (self.data / 장소CSV).read_bytes().decode('utf-8-sig').splitlines()
        장소위치.확인('봉산문화거리', 35.8631, 128.5965, 'https://korean.visitkorea.or.kr/x', '공식 상세 주소와 지도 대조', 신고파일=self.reports)
        after = (self.data / 장소CSV).read_bytes().decode('utf-8-sig').splitlines()
        바뀐 = [i for i, (x, y) in enumerate(zip(before, after)) if x != y]
        self.assertEqual(len(before), len(after))
        self.assertEqual([after[i].split(',')[1] for i in 바뀐], ['봉산문화거리'])
        r = next(x for x in self.행들() if x['장소명'] == '봉산문화거리')
        self.assertEqual((r['위도'], r['경도'], r['좌표검토상태'], r['좌표검토자']), ('35.8631', '128.5965', '사람확인완료', '관리자(화면)'))
        self.assertTrue(r['좌표확인일'] and r['좌표위치기준'] == '시설대표점')

    def test_확인한_장소는_지도점이_생긴다(self):
        self.assertIsNone(장소위치.지도점('봉산문화거리'))
        장소위치.확인('봉산문화거리', 35.8631, 128.5965, 'https://example.org/a', '근거', 신고파일=self.reports)
        self.assertEqual(장소위치.지도점('봉산문화거리'), (35.8631, 128.5965))

    def test_확인_입력을_검사한다(self):
        for 이름, 위도, 경도, url in [('없는곳', 35.8, 128.5, 'https://a'), ('봉산문화거리', 99, 128.5, 'https://a'),
                                   ('봉산문화거리', 35.8, 128.5, 'javascript:x'), ('봉산문화거리', 33.0, 126.5, 'https://a')]:
            with self.subTest(이름=이름, 위도=위도, url=url), self.assertRaises(ValueError):
                장소위치.확인(이름, 위도, 경도, url, '근거', 신고파일=self.reports)

    def test_확인대기에는_지도점이_없는_장소와_후보가_보인다(self):
        자동 = self.data / '좌표후보_자동.json'
        자동.write_text(json.dumps({'봉산문화거리': {'위도': '35.8631', '경도': '128.5965', '정밀도': '건물', '찾은이름': '봉산문화거리', '근거URL': 'https://nominatim.openstreetmap.org/x'}}, ensure_ascii=False), encoding='utf-8')
        목록 = 장소위치.확인대기(신고파일=self.reports)
        이름들 = [x['장소명'] for x in 목록]
        self.assertIn('봉산문화거리', 이름들)
        self.assertNotIn('김광석길', 이름들)   # 이미 확인된 장소
        self.assertNotIn('근대골목', 이름들)   # 대표위치로 지도점이 있음
        계산 = next(x for x in 목록 if x['장소명'] == '봉산문화거리')
        self.assertEqual(계산['후보'][0]['위도'], '35.8631')

    def test_후보찾기는_후보없는_장소만_묻고_저장한다(self):
        물음 = []
        def 묻기(url):
            물음.append(url); return [{'lat': '35.87', 'lon': '128.59', 'display_name': '봉산문화거리, 중구, 대구', 'addresstype': 'building'}]
        n = 장소위치.후보찾기(묻기=묻기, 쉬기=0, 신고파일=self.reports)
        self.assertGreaterEqual(n, 1)
        저장 = json.loads((self.data / '좌표후보_자동.json').read_text(encoding='utf-8'))
        self.assertIn('봉산문화거리', 저장)
        한번 = len(물음)
        장소위치.후보찾기(묻기=묻기, 쉬기=0, 신고파일=self.reports)
        self.assertEqual(len(물음), 한번)   # 이미 후보가 있으면 다시 묻지 않는다

    def test_길수집은_3km안_빠진쌍만_묻는다(self):
        물음 = []
        def 묻기(url):
            물음.append(url)
            a, b = [tuple(map(float, p.split(',')))[::-1] for p in url.split('/foot/')[1].split('?')[0].split(';')]
            return 경로응답(a, b)
        결과 = 장소위치.길수집(경로파일=self.routes, 묻기=묻기, 쉬기=0)
        self.assertGreater(결과['새경로'], 0)
        self.assertEqual(len(물음), 결과['새경로'] + 결과['실패'])
        평화 = 장소위치.지도점('평화시장 닭똥집골목')
        self.assertFalse([u for u in 물음 if f'{평화[1]:.6f},{평화[0]:.6f}' in u and '128.58' in u])   # 동구↔서문시장(약 4km)은 묻지 않음
        다시 = 장소위치.길수집(경로파일=self.routes, 묻기=묻기, 쉬기=0)
        self.assertEqual(다시['새경로'], 0)   # 이미 모은 쌍은 다시 묻지 않는다

    def test_장소파일이_바뀌면_자동작업을_다시_돈다(self):
        작업 = 장소위치.자동작업(self.routes, self.reports)
        시작 = []
        작업.시작 = lambda: 시작.append(1)
        작업.감시한번()                       # 처음 본 파일: 한 번 돈다
        작업.감시한번()                       # 그대로면 다시 돌지 않는다
        p = self.data / 장소CSV
        os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))   # 데이터 담당이 파일을 직접 고친 경우
        작업.감시한번()
        self.assertEqual(len(시작), 2)

    def test_화면의_긴_장소명으로_신고해도_목록_이름으로_맞춘다(self):
        장소위치.신고('대구광역시 중구 김광석길', '입구가 반대편이에요', 신고파일=self.reports)
        self.assertEqual(json.loads(self.reports.read_text(encoding='utf-8'))[0]['장소명'], '김광석길')

    def test_신고는_쌓이고_확인하면_처리된다(self):
        장소위치.신고('김광석길', '지도 위치가 길 건너편 같아요', 신고파일=self.reports)
        self.assertIn('김광석길', [x['장소명'] for x in 장소위치.확인대기(신고파일=self.reports)])
        장소위치.확인('김광석길', 35.8614, 128.6075, 'https://example.org/k', '현장 사진 대조', 신고파일=self.reports)
        self.assertNotIn('김광석길', [x['장소명'] for x in 장소위치.확인대기(신고파일=self.reports)])
        with self.assertRaises(ValueError):
            장소위치.신고('김광석길', '', 신고파일=self.reports)


if __name__ == '__main__':
    unittest.main()
