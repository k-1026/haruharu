import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import run_stage
from 제미나이자료 import 저장소도구


class AI연결시험(unittest.TestCase):
    def test_제미나이_선택은_설정한_모델과_키로_전달한다(self):
        config={'AI_PROVIDER':'gemini','GEMINI_MODEL':'sample-model','GEMINI_API_KEY':'test-only-key'}
        with mock.patch.object(run_stage,'설정_읽기',return_value=config), \
             mock.patch.object(run_stage,'에이전트_읽기',return_value=('지침 본문',['Read','Grep','Glob'])), \
             mock.patch.object(run_stage,'_제미나이_실행',new_callable=mock.AsyncMock,return_value='결과') as call:
            result=asyncio.run(run_stage.단계_실행('.claude/agents/코스검토.md','입력'))
        self.assertEqual(result,'결과')
        self.assertEqual(call.await_args.args[:4],('지침 본문','입력','sample-model','test-only-key'))

    def test_제미나이_키가_없으면_외부_호출전에_중단한다(self):
        config={'AI_PROVIDER':'gemini','GEMINI_MODEL':'sample-model','GEMINI_API_KEY':''}
        with mock.patch.object(run_stage,'설정_읽기',return_value=config), \
             mock.patch.object(run_stage,'에이전트_읽기',return_value=('지침',[])), \
             mock.patch.object(run_stage,'_제미나이_실행',new_callable=mock.AsyncMock) as call:
            with self.assertRaisesRegex(ValueError,'GEMINI_API_KEY'):
                asyncio.run(run_stage.단계_실행('agent.md','입력'))
        call.assert_not_awaited()

    def test_실제_SDK_요청_형식은_지침과_읽기_도구를_포함한다(self):
        from google import genai
        with mock.patch.object(genai,'Client') as client:
            client.return_value.aio.models.generate_content=mock.AsyncMock(return_value=SimpleNamespace(text='코스 초안'))
            client.return_value.aio.aclose=mock.AsyncMock()
            result=asyncio.run(run_stage._제미나이_실행('지침','입력','sample-model','test-only-key',['Read','Grep','Glob']))
        self.assertEqual(result,'코스 초안')
        self.assertEqual(client.call_args.kwargs['api_key'],'test-only-key')
        params=client.return_value.aio.models.generate_content.call_args.kwargs
        self.assertEqual(params['model'],'sample-model')
        self.assertEqual(params['config'].system_instruction,'지침')
        self.assertEqual(len(params['config'].tools),3)

    def test_자료도구는_지침을_읽고_비밀파일과_경로이탈은_거부한다(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'지침').mkdir()
            (root/'지침'/'예시.md').write_text('대구 관광 안내',encoding='utf-8')
            (root/'.env').write_text('GEMINI_API_KEY=secret',encoding='utf-8')
            read,search,files=저장소도구(root)
            self.assertIn('대구 관광',read('지침/예시.md'))
            self.assertIn('지침/예시.md',files('지침/*.md'))
            self.assertIn('대구 관광',search('대구','지침'))
            for path in ['.env','../outside.md','app/runs/private.json']:
                with self.subTest(path=path),self.assertRaises(ValueError):read(path)

    def test_응답이_제한시간을_넘으면_끊고_이유를_알린다(self):
        async def 느린(*a):
            await asyncio.sleep(5)
            return '늦은 결과'
        config={'AI_PROVIDER':'claude','AI_TIMEOUT_SECONDS':'1'}
        with mock.patch.object(run_stage,'설정_읽기',return_value=config),              mock.patch.object(run_stage,'에이전트_읽기',return_value=('지침',[])),              mock.patch.object(run_stage,'_클로드_실행',side_effect=느린):
            with self.assertRaisesRegex(run_stage.AI응답시간초과,'1초 동안 응답하지 않아'):
                asyncio.run(run_stage.단계_실행('agent.md','입력'))

    def test_제한시간_설정값을_검사한다(self):
        self.assertEqual(run_stage.제한초_읽기({}),run_stage.기본_제한초)
        self.assertEqual(run_stage.제한초_읽기({'AI_TIMEOUT_SECONDS':'120'}),120)
        for 값 in ['abc','0','-5']:
            with self.subTest(값=값),self.assertRaises(ValueError):run_stage.제한초_읽기({'AI_TIMEOUT_SECONDS':값})

    def test_제미나이_통신에도_제한시간을_건다(self):
        from google import genai
        with mock.patch.object(genai,'Client') as client:
            client.return_value.aio.models.generate_content=mock.AsyncMock(return_value=SimpleNamespace(text='결과'))
            client.return_value.aio.aclose=mock.AsyncMock()
            asyncio.run(run_stage._제미나이_실행('지침','입력','sample-model','test-only-key',[],30))
        self.assertEqual(client.call_args.kwargs['http_options'].timeout,30000)


if __name__=='__main__':unittest.main()
