import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from 설정 import 설정_읽기
from 장소정보 import 장소목록


class 환경설정시험(unittest.TestCase):
    def test_팀원_설정파일을_읽고_실제_환경변수가_우선한다(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'.env').write_text('# 개인 키\nAI_PROVIDER=gemini\nGEMINI_API_KEY="file-key"\nGEMINI_MODEL=sample-model\n',encoding='utf-8')
            settings=설정_읽기(root,{'GEMINI_API_KEY':'process-key'})
            self.assertEqual(settings['AI_PROVIDER'],'gemini')
            self.assertEqual(settings['GEMINI_API_KEY'],'process-key')
            self.assertEqual(settings['GEMINI_MODEL'],'sample-model')

    def test_자료_경로와_파일명을_설정에서_읽는다(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'places.csv').write_text('장소명,운영시간\n테스트 관광지,09:00-18:00\n',encoding='utf-8')
            (root/'travel.csv').write_text('출발장소,도착장소\n테스트 관광지,테스트 역\n',encoding='utf-8')
            with mock.patch.dict(os.environ,{'HARUHARU_DATA_DIR':str(root),'HARUHARU_PLACES_FILE':'places.csv','HARUHARU_TRAVEL_FILE':'travel.csv'}):
                rows=장소목록()
            self.assertEqual(rows[0]['장소명'],'테스트 관광지')
            self.assertTrue(any(row['장소명']=='테스트 역' for row in rows))


if __name__=='__main__':unittest.main()
