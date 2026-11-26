import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from app.공통.설정 import 설정_읽기
from app.단계3_코스검토.장소정보 import 장소목록


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


class 코드배치시험(unittest.TestCase):
    def test_단계별_이동후에도_자료와_화면의_기준경로는_그대로다(self):
        import importlib
        root = Path(__file__).resolve().parents[2]
        확인 = {'app.공통.설정': ('프로젝트', root),
              'app.공통.run_stage': ('저장소', root),
              'app.서버.관리자조회': ('기준', root / 'app'),
              'app.단계3_코스검토.코스조립': ('저장소', root),
              'app.단계4_홍보검토.홍보실행': ('저장소', root),
              'app.단계5_산출물.산출물': ('ROOT', root)}
        for 모듈, (속성, 경로) in 확인.items():
            with self.subTest(모듈=모듈):
                self.assertEqual(getattr(importlib.import_module(모듈), 속성), 경로)


if __name__=='__main__':unittest.main()
