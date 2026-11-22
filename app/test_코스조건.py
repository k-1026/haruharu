"""AI 호출 없이 2→3 담당자 입력과 에이전트 머리 읽기 확인."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_흐름  # 기존 시험과 같은 SDK 대역을 사용한다.
import orchestrator
import run_stage


class 코스조건시험(unittest.TestCase):
    def 받기(self, 기간, 답):
        with mock.patch('builtins.input', side_effect=답), mock.patch('builtins.print'):
            return orchestrator.코스조건_입력(기간)

    def test_빈값은_초기조건으로_추정하지_않음(self):
        조건 = self.받기('1박2일', [''] * 18)
        self.assertEqual(조건['시작지점'], '미확인')
        self.assertEqual(조건['치킨선택'], '미선택')
        self.assertEqual(조건['2일차오전구성'], '미선택')
        self.assertEqual(조건['운영방식'], '미정')
        self.assertEqual(len(조건['식사목록']), 3)

    def test_자유식은_식당을_정하지_않음(self):
        조건 = self.받기('당일', [''] * 6 + ['2', '3', '2', '2'])
        self.assertEqual(조건['2일차오전구성'], '해당없음')
        self.assertEqual(len(조건['식사목록']), 2)
        self.assertEqual(조건['식사목록'][0]['방식'], '자유식')
        self.assertEqual(조건['식사목록'][0]['식당'], '미선택')
        self.assertEqual(조건['식사목록'][1]['식비포함'], '불포함')

    def test_잘못된_시각은_다시_받음(self):
        조건 = self.받기('당일', ['동대구역', '25:00', '10:00', '역사관', '14:00', '', '', '', '', '', '', ''])
        self.assertEqual(조건['시작시각'], '10:00')

    def test_CRLF_머리는_지시문에_들어가지_않음(self):
        with tempfile.TemporaryDirectory() as 경로:
            파일 = Path(경로) / 'agent.md'
            파일.write_bytes(b'---\r\nname: test\r\ntools: Read, Glob\r\n---\r\nbody\r\n')
            with mock.patch.object(run_stage, '저장소', Path(경로)):
                본문, 도구 = run_stage.에이전트_읽기('agent.md')
            self.assertEqual(본문, 'body')
            self.assertEqual(도구, ['Read', 'Glob'])


if __name__ == '__main__':
    unittest.main()
