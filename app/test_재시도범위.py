"""실제 AI 없이 새 버전·새 상황의 재시도를 이전 실패가 막지 않는지 확인한다."""
from pathlib import Path
import unittest

import 기획기록 as 기록모듈
import 처리기
import 총괄
import run_stage


class 재시도범위시험(unittest.TestCase):
    def 기록(self):
        return 기록모듈.새_기록({}, '사람:담당자', 기록id='retry')

    def test_코스는_같은버전_실패만_묶고_새버전은_다시_쓸수있다(self):
        r = self.기록()
        본 = []
        def 실패(p, i):
            본.append(1)
            return 'JSON 없음'
        for _ in range(3):
            self.assertFalse(처리기.코스짜기(r, 'A', Path('.'), [], 실패))
        self.assertEqual(len(본), 2)
        # 담당자가 새 초안을 저장하면 이전 버전 생성 실패와 별개의 작업이다.
        기록모듈.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': {'칸목록': []}}, '사람:담당자')
        self.assertTrue(처리기.코스짜기(r, 'A', Path('.'), [], lambda p, i: '{"칸목록":[]}'))
        self.assertEqual(기록모듈.버전목록(r, 'A'), [1, 2])

    def test_총괄은_같은상황에서_두번만_묻고_새버전에서는_다시판단한다(self):
        r = self.기록()
        기록모듈.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': {'칸목록': []}}, '사람:담당자')
        본 = []
        def 실패(p, i):
            본.append(1)
            return '설명만 있음'
        총괄.AI_다음_할일(r, 실패)
        총괄.AI_다음_할일(r, 실패)
        self.assertEqual(len(본), 2)
        기록모듈.추가(r, '코스안', {'안id': 'A', '버전': 2, '코스': {'칸목록': []}}, '사람:담당자')
        d = 총괄.AI_다음_할일(r, lambda p, i: '{"행동":"점검","대상":"A","이유":"새 버전"}')
        self.assertEqual(d['판단'], 'AI')

    def test_코스_검증결과가_새로생기면_총괄은_다시판단한다(self):
        r = self.기록()
        기록모듈.추가(r, '코스안', {'안id': 'A', '버전': 1, '코스': {'칸목록': []}}, '사람:담당자')
        총괄.AI_다음_할일(r, lambda p, i: '설명만 있음')
        기록모듈.추가(r, '경고', {'종류': '검증결과', '안id': 'A', '버전': 1, '통과': False}, '에이전트:검증')
        d = 총괄.AI_다음_할일(r, lambda p, i: '{"행동":"점검","대상":"A","이유":"검증 결과 확인"}')
        self.assertEqual(d['판단'], 'AI')

    def test_역할별_응답대기는_기존900초설정에도_짧게제한한다(self):
        for path, seconds in [('코스검토.md', 60), ('총괄.md', 10), ('검증.md', 30), ('수요근거.md', 30)]:
            with self.subTest(path=path):
                self.assertEqual(run_stage.제한초_읽기({'AI_TIMEOUT_SECONDS': '900'}, '.claude/agents/' + path), seconds)
        self.assertEqual(run_stage.제한초_읽기({'AI_TIMEOUT_SECONDS': '5'}, '.claude/agents/코스검토.md'), 5)


if __name__ == '__main__':
    unittest.main()
