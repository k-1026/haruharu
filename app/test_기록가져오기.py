import json
import tempfile
import unittest
from pathlib import Path
import 기록가져오기


def make(root,with_result=True):
    base=root/'run1'/'01회차';test=base/'통합시험_1';test.mkdir(parents=True)
    (base/'1단계_선택.json').write_text(json.dumps({'조건':{'계절':'봄'}},ensure_ascii=False),encoding='utf-8')
    (base/'3단계_전달_준비.json').write_text(json.dumps({'근거목록':[{'근거ID':'R1'},{'근거ID':'R2'}],'경고목록':[{'경고ID':'W1','문구':'a'}]},ensure_ascii=False),encoding='utf-8')
    (test/'3단계_입력.json').write_text(json.dumps({'코스작성조건':{'시작지점':'A'}},ensure_ascii=False),encoding='utf-8')
    if with_result:
        (test/'3단계_결과.md').write_text(json.dumps({'칸목록':[{'칸ID':'낮'}],'남은경고':[{'경고ID':'W2'}]},ensure_ascii=False),encoding='utf-8')
    return 'run1/01회차/통합시험_1'


class 가져오기시험(unittest.TestCase):
    def test_근거_경고_코스안_조건(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=make(root);src=root/'run1'/'01회차'/'3단계_전달_준비.json';before=src.stat().st_mtime_ns
            r=기록가져오기.가져오기(root,key)
            self.assertEqual(len(r['근거']),2);self.assertEqual(len(r['경고']),2);self.assertEqual(len(r['코스안']),1)
            self.assertEqual(r['코스안'][0]['안id'],'A');self.assertEqual(r['조건']['계절'],'봄')
            self.assertEqual(r['조건']['코스작성조건'],{'시작지점':'A'})
            self.assertEqual(r['기록id'],'통합시험_1')
            self.assertTrue((root/'기획'/'통합시험_1'/'기획기록.json').exists())
            self.assertEqual(src.stat().st_mtime_ns,before)
            with self.assertRaises(FileExistsError):기록가져오기.가져오기(root,key)

    def test_코스결과_없으면_코스안0_경고(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r=기록가져오기.가져오기(root,make(root,False))
            self.assertEqual(r['코스안'],[])
            self.assertTrue(any('코스 결과 없음' in x.get('문구','') for x in r['경고']))

    def test_실제_AI처럼_앞말과_json블록이_붙어도_코스를_읽는다(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=make(root)
            (root/'run1'/'01회차'/'통합시험_1'/'3단계_결과.md').write_text('지침 파일을 먼저 읽겠습니다.\n```json\n{"칸목록":[{"칸ID":"낮"}]}\n```\n',encoding='utf-8')
            r=기록가져오기.가져오기(root,key)
            self.assertEqual(len(r['코스안']),1);self.assertEqual(r['코스안'][0]['코스']['칸목록'][0]['칸ID'],'낮')


if __name__=='__main__':unittest.main()
