"""로컬 결과 조회만 검증. AI·네트워크 외부 호출 없음."""
import json
import tempfile
import unittest
from pathlib import Path

from app.서버.관리자조회 import 결과저장소


class 조회시험(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'runs'
        self.round = self.root / '20261122_131912' / '01회차'
        self.round.mkdir(parents=True)
        self.store = 결과저장소(self.root)

    def 저장(self, 이름, 값):
        경로 = self.round / 이름
        경로.parent.mkdir(parents=True, exist_ok=True)
        경로.write_text(json.dumps(값, ensure_ascii=False), encoding='utf-8')

    def test_조건과_전달실패를_목록에_구분(self):
        self.저장('1단계_선택.json', {'조건': {'계절': '봄', '지역': ['중구'], '언어권': ['일본어'], '체류기간': '1박2일'}})
        self.저장('3단계_전달_준비.json', {'검사결과': ['W1 연결 누락'], '근거목록': [{'근거ID': 'R01'}], '경고목록': [{'경고ID': 'W1'}]})
        목록 = self.store.목록()
        self.assertEqual(len(목록), 1)
        self.assertEqual(목록[0]['조건']['지역'], ['중구'])
        self.assertEqual(목록[0]['검사상태'], '실패')
        self.assertEqual(목록[0]['근거수'], 1)

    def test_깨진_JSON에도_결과파일은_열수있음(self):
        (self.round / '3단계_전달_준비.json').write_text('{', encoding='utf-8')
        목록 = self.store.목록()
        self.assertEqual(목록[0]['검사상태'], '읽기 오류')
        self.assertEqual(self.store.파일('20261122_131912/01회차/3단계_전달_준비.json')['본문'], '{')

    def test_검사없는_실행을_통과로_표시안함(self):
        (self.round / '2단계_결과.md').write_text('# 생성된 결과', encoding='utf-8')
        self.assertEqual(self.store.목록()[0]['검사상태'], '기록 없음')

    def test_통합시험_하위폴더도_별도기록(self):
        self.저장('통합시험_210000_000001/3단계_전달_검사.json', {'검사결과': ['통과']})
        self.저장('통합시험_210000_000001/4단계_전달_검사.json', {'검사결과': ['R99 없음']})
        목록 = self.store.목록()
        self.assertEqual(len(목록), 1)
        상세 = self.store.상세(목록[0]['id'])
        self.assertEqual(len(상세['통합시험']), 1)
        self.assertTrue(any(f['이름'] == '4단계_전달_검사.json' for f in 상세['파일']))

    def test_임의파일과_경로이탈을_거부(self):
        (self.round / 'secret.json').write_text('secret', encoding='utf-8')
        for 키 in ['../../secret.json', '/etc/passwd', '20261122_131912/01회차/secret.json', '20261122_131912/01회차/..\\secret.json']:
            with self.subTest(키=키), self.assertRaises((ValueError, FileNotFoundError)):
                self.store.파일(키)

    def test_시안과_기관업로드는_파일목록에_노출안함(self):
        (self.round / '기관데이터.csv').write_text('data', encoding='utf-8')
        (self.round / '.env').write_text('secret', encoding='utf-8')
        상세 = self.store.상세('20261122_131912/01회차')
        self.assertEqual(상세['파일'], [])

    def test_빈runs(self):
        self.assertEqual(결과저장소(Path(self.tmp.name) / '없는폴더').목록(), [])

    def test_한글이름_기획과_검사예제도_목록과_코스로_조회한다(self):
        from app.서버.관리자실행 import 코스시험
        서비스 = 코스시험(self.store)
        for 이름 in ['최신기획', '검사예제_코스', '검사예제_입력']:
            회차 = self.root / 이름 / '01회차'
            시험 = 회차 / '통합시험_120000_000001'
            시험.mkdir(parents=True)
            self.assertEqual(서비스._원본(이름 + '/01회차'), 회차)
            self.assertEqual(서비스._시험(이름 + '/01회차/' + 시험.name), 시험)
        (self.root / '기관업로드' / '01회차').mkdir(parents=True)
        self.assertEqual({r['실행'] for r in self.store.목록()},
                         {'20261122_131912', '최신기획', '검사예제_코스', '검사예제_입력'})

    def test_최근기획은_폴더이름보다_실제시작시각을_따른다(self):
        from app.공통.기획실행 import 기획실행
        from app.서버.관리자실행 import 코스시험
        서비스 = 기획실행(코스시험(self.store))
        for 이름, 시각 in [('최신기획', '2026-11-26T12:07:25+09:00'),
                            ('20261127_100000', '2026-11-27T10:00:00+09:00')]:
            회차 = self.root / 이름 / '01회차'
            회차.mkdir(parents=True)
            (회차 / '기획_진행.json').write_text(json.dumps(
                {'기획id': 이름 + '/01회차', '시작시각': 시각, '상태': '완료'}), encoding='utf-8')
        self.assertEqual(서비스.상태('최신기획/01회차')['상태'], '완료')
        self.assertEqual(서비스.최근()['기획id'], '20261127_100000/01회차')

    def test_한글기획도_홍보목록과_문서경로를_읽는다(self):
        from app.공통 import 기획기록
        from app.공통.기획실행 import 기획실행
        from app.서버.관리자실행 import 코스시험
        from app.단계4_홍보검토.홍보실행 import 홍보실행
        서비스 = 홍보실행(기획실행(코스시험(self.store)))
        키 = '최신기획/01회차/홍보_20261126_130000'
        폴더 = self.root / 키
        폴더.mkdir(parents=True)
        시험키 = '최신기획/01회차/통합시험_120000_000001'
        (self.root / 시험키).mkdir()
        기록 = 기획기록.새_기록({}, '사람:시험', 기록id=시험키.split('/')[-1])
        기획기록.추가(기록, '코스안', {'안id': 'A', '버전': 1, '코스': {}}, '코드:시험')
        기획기록.저장(기록, self.root)
        (폴더 / '홍보_진행.json').write_text(json.dumps(
            {'홍보id': 키, '상태': '홍보완료', '시험id': 시험키, '안id': 'A', '버전': 1}), encoding='utf-8')
        self.assertEqual(서비스._홍보폴더(키), 폴더)
        self.assertEqual(서비스.목록('최신기획/01회차')[0]['홍보id'], 키)
        with self.assertRaises(ValueError):
            서비스._홍보폴더('최신기획/../홍보_20261126_130000')


if __name__ == '__main__':
    unittest.main()
