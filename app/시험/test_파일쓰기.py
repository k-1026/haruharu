"""Windows에서 화면이 파일을 읽는 동안 교체가 거부돼도 잠깐 기다렸다 다시 바꾼다."""
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from app.공통 import 파일쓰기


class 바꿔쓰기시험(unittest.TestCase):
    def test_잠깐_거부돼도_다시_시도해_바꾼다(self):
        진짜 = os.replace
        횟수 = []

        def 가끔거부(a, b):
            횟수.append(1)
            if len(횟수) < 3:
                raise PermissionError(5, '액세스가 거부되었습니다')
            return 진짜(a, b)
        with TemporaryDirectory() as d:
            임시, 대상 = Path(d) / 'a.json.tmp', Path(d) / 'a.json'
            임시.write_text('새', encoding='utf-8'); 대상.write_text('옛', encoding='utf-8')
            with mock.patch('app.공통.파일쓰기.os.replace', side_effect=가끔거부), mock.patch('app.공통.파일쓰기.time.sleep'):
                파일쓰기.바꿔쓰기(임시, 대상)
            self.assertEqual(대상.read_text(encoding='utf-8'), '새')
        self.assertEqual(len(횟수), 3)

    def test_계속_거부되면_원래_오류를_올린다(self):
        with TemporaryDirectory() as d:
            임시, 대상 = Path(d) / 'a.tmp', Path(d) / 'a'
            임시.write_text('x', encoding='utf-8')
            with mock.patch('app.공통.파일쓰기.os.replace', side_effect=PermissionError(5, '거부')), mock.patch('app.공통.파일쓰기.time.sleep'):
                with self.assertRaises(PermissionError):
                    파일쓰기.바꿔쓰기(임시, 대상)

    def test_기획진행_쓰기도_재시도한다(self):
        from app.공통 import 기획실행
        진짜 = os.replace
        횟수 = []

        def 한번거부(a, b):
            횟수.append(1)
            if len(횟수) == 1:
                raise PermissionError(5, '거부')
            return 진짜(a, b)
        with TemporaryDirectory() as d, mock.patch('app.공통.파일쓰기.os.replace', side_effect=한번거부), mock.patch('app.공통.파일쓰기.time.sleep'):
            기획실행._쓰기(Path(d), '기획_진행.json', {'상태': '진행중'})
            self.assertIn('진행중', (Path(d) / '기획_진행.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
