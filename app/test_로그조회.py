"""소켓·외부 AI 없이 관리자 기본 경로가 읽기 전용 로그를 제공하는지 검사한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from 관리자조회 import 결과저장소, 핸들러


class 로그시험(unittest.TestCase):
    def test_관리자_기본문서는_운영로그이고_기존개발화면은_보존한다(self):
        with TemporaryDirectory() as folder:
            handler=핸들러(결과저장소(folder),object(),object())
            obj=object.__new__(handler);obj.호스트확인=lambda:True;obj.path='/admin/'
            responses=[];obj.응답=lambda *args:responses.append(args)
            obj.do_GET()
        body=responses[0][1].decode('utf-8')
        self.assertIn('서비스 운영 로그',body)
        self.assertNotIn('courseForm',body)
        self.assertNotIn('courseStart',body)
        self.assertTrue((Path(__file__).parent/'관리자화면/index.html').is_file())

    def test_진행파일은_조회하지만_비밀설정은_조회하지않는다(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);r=root/'20261124_100000'/'01회차';r.mkdir(parents=True)
            (r/'기획_진행.json').write_text('{"상태":"완료"}',encoding='utf-8')
            (root/'.env').write_text('SECRET=test',encoding='utf-8')
            store=결과저장소(root)
            self.assertIn('상태',store.파일('20261124_100000/01회차/기획_진행.json')['본문'])
            self.assertTrue(any(x['이름']=='기획_진행.json' for x in store.상세('20261124_100000/01회차')['파일']))
            with self.assertRaises((ValueError,FileNotFoundError)):store.파일('.env')


if __name__=='__main__':unittest.main()
