import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.공통.오류기록 import 진단, 저장


class 오류기록시험(unittest.TestCase):
    def test_실행경계에서_제공자와_모델_시간을_예외에_보존한다(self):
        from app.공통 import run_stage
        async def fail(*args):raise RuntimeError('denied')
        with patch.object(run_stage,'_단계_실행',fail),patch.object(run_stage,'설정_읽기',return_value={'AI_PROVIDER':'claude','CLAUDE_MODEL':'example'}):
            coroutine=run_stage.단계_실행('수요요약.md','기록하지 않을 입력')
            try:coroutine.send(None)
            except RuntimeError as error:report=error.AI진단
            finally:coroutine.close()
        self.assertEqual(report['제공자'],'claude')
        self.assertEqual(report['모델'],'example')
        self.assertIn('경과초',report)
        self.assertNotIn('기록하지 않을 입력',str(report))

    def test_SDK_상세를_허용목록으로_보존하고_비밀값은_지운다(self):
        # 다른 시험의 SDK 대체 모듈과 독립적으로 설치된 ResultError의 공개 속성을 재현한다.
        class ResultError(RuntimeError):pass
        error=ResultError('request failed')
        error.api_error_status=429;error.terminal_reason='api_error';error.exit_code=1
        error.errors=['usage limit reached; Bearer private-token']
        error.result='API Error: key=my-secret-value';error.data={'prompt':'비공개 입력'}
        with patch('app.공통.오류기록.설정_읽기',return_value={'GEMINI_API_KEY':'my-secret-value'}):
            result=진단(error,제공자='claude',모델='example',단계='수요요약.md',경과초=1.2)
        self.assertEqual(result['HTTP상태'],429)
        self.assertEqual(result['종료이유'],'api_error')
        self.assertIn('usage limit',str(result))
        self.assertNotIn('private-token',str(result))
        self.assertNotIn('my-secret-value',str(result))
        self.assertNotIn('비공개 입력',str(result))

    def test_일반오류와_원인체인_저장_기존진단을_보존한다(self):
        error=RuntimeError('outer');error.__cause__=ValueError('inner')
        with TemporaryDirectory() as folder:
            저장(folder,error,단계='수요')
            저장(folder,TimeoutError('timeout'),단계='코스')
            data=json.loads((Path(folder)/'AI_오류.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['오류']),2)
        self.assertEqual(data['오류'][0]['원인'][0]['종류'],'ValueError')
        self.assertEqual(data['오류'][1]['종류'],'TimeoutError')

    def test_실제기획경계가_재호출없이_진단파일을_남긴다(self):
        from app.서버.관리자조회 import 결과저장소
        from app.서버.관리자실행 import 코스시험
        from app.공통.기획실행 import 기획실행
        def fail(*args):raise RuntimeError('API unavailable')
        with TemporaryDirectory() as folder,patch('app.공통.run_stage.단계_실행',side_effect=AssertionError('실제 AI 금지')):
            service=기획실행(코스시험(결과저장소(folder)),단계함수=fail)
            p=service.시작({'계절':'가을','언어권':['일본어'],'지역':['중구'],'체류기간':'1박2일','자동진행동의':True})
            service.작업.join(3)
            report=json.loads((Path(folder)/p['기획id']/'AI_오류.json').read_text(encoding='utf-8'))
        self.assertEqual(report['오류'][0]['메시지'],'API unavailable')
        self.assertEqual(p['상태'],'멈춤')

    def test_진단파일을_로그에서_읽을수있다(self):
        from app.서버.관리자조회 import 결과저장소
        with TemporaryDirectory() as folder:
            path=Path(folder)/'20261124_100000'/'01회차';path.mkdir(parents=True)
            저장(path,RuntimeError('failure'))
            self.assertIn('failure',결과저장소(folder).파일('20261124_100000/01회차/AI_오류.json')['본문'])

if __name__=='__main__':unittest.main()
