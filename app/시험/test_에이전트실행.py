import unittest
import unittest.mock
from app.공통 import 기획기록 as 기록모듈
from app.공통 import 에이전트실행 as 실행


def rec():
    return 기록모듈.새_기록({},'사람:담당자',기록id='t')


class 호출시험(unittest.TestCase):
    def call(self,r,fn):
        return 실행.호출(r,'에이전트:수집','.claude/agents/자료수집.md','수집','밤',{'요청':'밤'},'빈칸',실행함수=fn)

    def test_JSON블록이면_dict와_성공(self):
        r=rec();out=self.call(r,lambda p,i:'설명\n```json\n{"a":1}\n```')
        self.assertEqual(out,{'a':1});self.assertEqual(r['실행'][-1]['결과'],'성공');self.assertEqual(r['실행'][-1]['AI호출'],1)

    def test_비동기함수도_받음(self):
        async def fn(p,i):return '{"b":2}'
        self.assertEqual(self.call(rec(),fn),{'b':2})

    def test_글만_오면_실패(self):
        r=rec();self.assertIsNone(self.call(r,lambda p,i:'모르겠어요'));self.assertEqual(r['실행'][-1]['결과'],'실패')

    def test_예외면_실패(self):
        def boom(p,i):raise RuntimeError('네트워크')
        r=rec();self.assertIsNone(self.call(r,boom));self.assertEqual(r['실행'][-1]['결과'],'실패')
        self.assertEqual(r['실행'][-1]['AI호출'],1)

    def test_혼잡오류는_기다렸다_재시도(self):
        waits=[];calls=[]
        def fn(p,i):
            calls.append(1)
            if len(calls)<3:raise RuntimeError('503 UNAVAILABLE. The model is overloaded.')
            return '{"ok":1}'
        r=rec()
        with unittest.mock.patch.object(실행.time,'sleep',waits.append):
            self.assertEqual(self.call(r,fn),{'ok':1})
        self.assertEqual(len(calls),3);self.assertEqual(waits,[5,15])
        self.assertEqual(r['실행'][-1]['결과'],'성공');self.assertEqual(r['실행'][-1]['AI호출'],3)
        self.assertIn('혼잡 재시도 2회',r['실행'][-1]['이유'])

    def test_혼잡이_계속되면_실패_그외오류는_재시도안함(self):
        r=rec();calls=[]
        def busy(p,i):calls.append(1);raise RuntimeError('429 RESOURCE_EXHAUSTED')
        with unittest.mock.patch.object(실행.time,'sleep',lambda s:None):
            self.assertIsNone(self.call(r,busy))
        # 수집 30초 예산에서는 5+15초 뒤의 45초 대기를 시작하지 않는다.
        self.assertEqual(len(calls),3);self.assertEqual(r['실행'][-1]['결과'],'실패')
        calls.clear()
        def bad(p,i):calls.append(1);raise ValueError('API key not valid')
        self.assertIsNone(self.call(rec(),bad));self.assertEqual(len(calls),1)

    def test_한도넘으면_호출안함_보류(self):
        r=rec();기록모듈.실행_기록(r,'에이전트:코스','코스','A','x','성공',AI호출=30);calls=[]
        self.assertIsNone(self.call(r,lambda p,i:calls.append(1) or '{}'))
        self.assertEqual(calls,[]);self.assertEqual(r['실행'][-1]['결과'],'보류')

    def test_혼잡재시도도_남은_AI호출수를_넘지않는다(self):
        r=rec()
        기록모듈.실행_기록(r,'에이전트:코스','코스','A','이전 호출','성공',AI호출=29)
        calls=[]
        def busy(p,i):
            calls.append(1)
            raise RuntimeError('503 overloaded')
        with unittest.mock.patch.object(실행.time,'sleep') as wait:
            self.assertIsNone(self.call(r,busy))
        self.assertEqual(len(calls),1)
        wait.assert_not_called()
        self.assertEqual(sum(x['AI호출'] for x in r['실행']),30)

    def test_혼잡대기중_역할시간을_소진하면_다시호출하지않는다(self):
        clock=[0.0];calls=[]
        def busy(p,i):
            calls.append(1)
            clock[0]+=29
            raise RuntimeError('503 overloaded')
        with unittest.mock.patch.object(실행.time,'monotonic',side_effect=lambda:clock[0]), \
             unittest.mock.patch.object(실행.time,'sleep') as wait:
            r=rec()
            self.assertIsNone(self.call(r,busy))
        self.assertEqual(len(calls),1)
        wait.assert_not_called()
        self.assertIn('시간',r['실행'][-1]['이유'])

    def test_응답시간초과는_재시도하지_않고_이유를_남긴다(self):
        from app.공통 import run_stage
        calls=[]
        def fn(p,i):
            calls.append(1);raise run_stage.AI응답시간초과('AI(claude)가 900초 동안 응답하지 않아 중단했습니다.')
        r=rec()
        self.assertIsNone(self.call(r,fn))
        self.assertEqual(len(calls),1);self.assertEqual(r['실행'][-1]['결과'],'실패')
        self.assertIn('응답하지 않아 중단',r['실행'][-1]['이유'])


if __name__=='__main__':unittest.main()
