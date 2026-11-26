"""네트워크 없이 SDK 비동기 경계와 취소 시 연결 정리를 확인한다."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest import mock

from app.공통 import run_stage


class 취소시험(unittest.TestCase):
    def test_별도스레드없이_비동기SDK를_기다리고_닫는다(self):
        from google import genai
        with mock.patch.object(genai, 'Client') as client, \
             mock.patch.object(run_stage.asyncio, 'to_thread', side_effect=AssertionError('스레드 요청 금지')):
            api = client.return_value.aio
            api.models.generate_content = mock.AsyncMock(return_value=SimpleNamespace(text='결과'))
            api.aclose = mock.AsyncMock()
            task = run_stage._제미나이_실행('지침', '입력', 'sample-model', 'test-only-key', [], 30)
            with self.assertRaises(StopIteration) as ended:
                task.send(None)  # 모의 SDK가 즉시 응답하므로 이벤트 루프나 소켓이 필요 없다.
            self.assertEqual(ended.exception.value, '결과')
            api.models.generate_content.assert_awaited_once()
            api.aclose.assert_awaited_once()

    def test_취소되면_SDK연결을_닫고_취소를_그대로_올린다(self):
        from google import genai
        with mock.patch.object(genai, 'Client') as client, \
             mock.patch.object(run_stage.asyncio, 'to_thread', side_effect=AssertionError('스레드 요청 금지')):
            api = client.return_value.aio
            api.models.generate_content = mock.AsyncMock(side_effect=asyncio.CancelledError())
            api.aclose = mock.AsyncMock()
            task = run_stage._제미나이_실행('지침', '입력', 'sample-model', 'test-only-key', [], 30)
            with self.assertRaises(asyncio.CancelledError):
                task.send(None)
            api.aclose.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
