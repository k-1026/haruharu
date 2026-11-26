"""외부 AI 호출 없이 실제 SDK 명령을 구성해 Windows 길이 회귀를 검사한다."""
import asyncio
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from app.공통 import run_stage
from claude_agent_sdk import AssistantMessage, TextBlock
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport


class 클로드지침시험(unittest.TestCase):
    def 실행(self, mode='success'):
        body, _ = run_stage.에이전트_읽기('.claude/agents/코스검토.md')
        observed = []

        async def query(*, prompt, options):
            # 네트워크 경계만 대체한다. 실제 SDK 명령 생성은 그대로 검사한다.
            transport = SubprocessCLITransport(prompt=prompt, options=options)
            transport._cli_path = 'C:/claude.exe'
            command = subprocess.list2cmdline(transport._build_command())
            self.assertLess(len(command.encode('utf-16-le')) // 2, 32767)
            self.assertEqual(options.system_prompt['type'], 'file')
            path = Path(options.system_prompt['path'])
            observed.append(path)
            self.assertEqual(path.read_text(encoding='utf-8'), body)
            self.assertEqual(prompt, '입력 보존')
            if mode == 'error':
                raise RuntimeError('제공자 오류')
            if mode == 'cancel':
                raise asyncio.CancelledError()
            yield AssistantMessage(content=[TextBlock(text='코스 초안')], model='test')

        with patch('claude_agent_sdk.query', query):
            try:
                result = asyncio.run(run_stage._클로드_실행(body, '입력 보존', 'test', []))
                self.assertEqual(result, '코스 초안')
            finally:
                for path in observed:
                    self.assertFalse(path.exists(), '호출 후 지침 임시 파일이 남음')

    def test_긴_실제지침을_내용손실없이_짧은_명령으로_전달한다(self):
        self.실행()

    def test_제공자_오류에도_임시지침을_정리한다(self):
        with self.assertRaisesRegex(RuntimeError, '제공자 오류'):
            self.실행('error')

    def test_취소에도_임시지침을_정리한다(self):
        with self.assertRaises(asyncio.CancelledError):
            self.실행('cancel')


if __name__ == '__main__':
    unittest.main()
