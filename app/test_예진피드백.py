import copy
import unittest
from unittest.mock import patch
from 단계연결 import 코스_검사,홍보_검사
from test_단계연결 import 코스,홍보,입력2
from 운영검토 import 검토_반영
from run_stage import 에이전트_읽기


class 피드백시험(unittest.TestCase):
    def test_4단계_지침과_스킬을_직접_동봉한다(self):
        text,tools=에이전트_읽기('.claude/agents/홍보검토.md')
        self.assertIn('첨부 지침: 지침/4_홍보검토/12_번역_용어집.md',text)
        self.assertIn('鄕村文化館',text)
        self.assertIn('첨부 지침: .claude/skills/홍보문구/SKILL.md',text)
        self.assertEqual(tools,[])

    def test_자유시간은_권역이름이_아니라_칸종류로_판정한다(self):
        c=코스();c['2일차오전구성']='자유시간'
        c['칸목록'].append({'칸ID':'오전','일차':2,'시간칸':'2일차오전','장소명':'중구 도심 (반월당역 주변)',
                              '시각':{'값':'','종류':'미정'},'근거ID':[]})
        source={**입력2,'확정체류기간':'1박2일','코스작성조건':{'2일차오전구성':'자유시간'}}
        self.assertFalse(any('근거 없음' in p for p in 코스_검사(c,source)))
        c['칸목록'][-1]['시간칸']='낮'
        self.assertTrue(any('근거 없음' in p for p in 코스_검사(c,source)))

    def test_후보제외는_같은칸의_잔여이름도_제거하고_원본을_보존한다(self):
        c=코스();c['칸목록'][0]['장소명']='동성로 · 추천 후보: 산호찜갈비 · 봉산찜갈비 · 원주통닭'
        c['식사목록']=[{'안':'공통','칸ID':'낮-1','권역':c['칸목록'][0]['장소명'],
                         '추천후보':['산호찜갈비','봉산찜갈비','원주통닭']}]
        original=copy.deepcopy(c)
        result=검토_반영(c,{'일정확인':[],'운영확인':[{'안':'공통','칸ID':'낮-1','처리':'제외','대상명':'봉산찜갈비'}],'담당자최종확인':False})
        self.assertNotIn('봉산찜갈비',result['칸목록'][0]['장소명'])
        self.assertNotIn('봉산찜갈비',result['식사목록'][0]['권역'])
        self.assertEqual(c,original)
        self.assertIn('원주통닭',result['식사목록'][0]['권역'])

    def test_홍보의_비후보식당과_잘못된_출처와_용어를_잡는다(self):
        c=코스();c['칸목록'][0]['장소명']='향촌문화관'
        p=홍보();p['문구목록'][0].update({'본문':'향촌문화관과 봉산찜갈비','사실근거':{'근거ID':['KTO-SM'],'출처ID':['FAKE']}})
        p['번역목록'][0].update({'언어':'일본어','번역':'香村文化館'})
        with patch('홍보검사.장소목록',return_value=[{'장소명':'봉산찜갈비','장소유형':'식당'}]):
            problems=홍보_검사(p,c,[{'근거ID':'R01','출처ID':'S1'}])
        for term in ['봉산찜갈비','용어집','KTO-SM','FAKE']:
            self.assertTrue(any(term in x for x in problems),term)

    def test_허용된_후보_공식표기_스토리출처는_통과한다(self):
        c=코스();c['식사목록']=[{'추천후보':['봉산찜갈비']}]
        p=홍보();p['문구목록'][0].update({'본문':'향촌문화관과 봉산찜갈비','사실근거':{'근거ID':['R01'],'출처ID':['KTO-SM','S1']}})
        p['번역목록'][0].update({'언어':'일본어','번역':'鄕村文化館'})
        self.assertEqual(홍보_검사(p,c,[{'근거ID':'R01','출처ID':'S1'}]),[])

if __name__=='__main__':unittest.main()
