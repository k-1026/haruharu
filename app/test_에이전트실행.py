import unittest
import 기획기록 as 기록모듈
import 에이전트실행 as 실행


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

    def test_한도넘으면_호출안함_보류(self):
        r=rec();기록모듈.실행_기록(r,'에이전트:코스','코스','A','x','성공',AI호출=30);calls=[]
        self.assertIsNone(self.call(r,lambda p,i:calls.append(1) or '{}'))
        self.assertEqual(calls,[]);self.assertEqual(r['실행'][-1]['결과'],'보류')


if __name__=='__main__':unittest.main()
