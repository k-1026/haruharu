import unittest

import run_stage


class 입력자료시험(unittest.TestCase):
    def test_코스는_지침과_장소자료를_받아_파일탐색없이_작성한다(self):
        본문, 도구 = run_stage.에이전트_읽기('.claude/agents/코스검토.md')
        self.assertEqual(도구, [])
        self.assertIn('첨부 지침: 지침/3_코스검토/12_코스_체크리스트.md', 본문)
        self.assertIn('장소명,', 본문)
        self.assertIn('출발장소,', 본문)
        self.assertIn('자료가 없으면 미확인', 본문)

    def test_수요요약은_파일조회도구가_없다(self):
        본문, 도구 = run_stage.에이전트_읽기('.claude/agents/수요요약.md')
        self.assertEqual(도구, [])
        self.assertIn('요약', 본문)

    def test_검증은_출처대장을_독립적으로_조회할수있다(self):
        본문, 도구 = run_stage.에이전트_읽기('.claude/agents/검증.md')
        self.assertIn('Read', 도구)
        self.assertIn('research/sources.md', 본문)


if __name__ == '__main__':
    unittest.main()
