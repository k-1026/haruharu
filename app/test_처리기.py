import json
import tempfile
import unittest
from pathlib import Path
import 기획기록 as 기록모듈
import 처리기


def rec():
    return 기록모듈.새_기록({'계절':'봄'},'사람:담당자',기록id='t')


class 수집시험(unittest.TestCase):
    def test_출처있는_후보만_쓰고_나머지는_경고(self):
        r=rec()
        응답={'후보':[{'이름':'향촌문화관','출처ID':'S70','출처등급':'공식','내용':'월 휴관'},
                    {'이름':'가짜 야시장','출처ID':'','출처등급':'AI 생성'}],'못찾음':['평일 밤 야시장 없음']}
        n=처리기.수집하기(r,'평일 밤 후보',실행함수=lambda p,i:json.dumps(응답,ensure_ascii=False))
        self.assertEqual(n,1);self.assertEqual(len(r['후보']),1);self.assertEqual(r['후보'][0]['상태'],'후보')
        self.assertEqual(len(r['경고']),2);self.assertTrue(all(x['종류']=='수집' for x in r['경고']))


if __name__=='__main__':unittest.main()
