import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from app.단계3_코스검토.좌표보완 import 수집

class 보완시험(unittest.TestCase):
    def test_검토완료는_건너뛰고_나머지만_후보로_기록한다(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)/'p.csv'
            p.write_text('순번,장소명,주소,위도,경도,좌표검토상태\n1,확인된곳,주소,35,128,자료대조완료\n2,기념관,대구 중구 어느로 1,,,\n3,서문시장,,,,\n4,새시설,,,,\n',encoding='utf-8')
            before=p.read_bytes();queries=[]
            def query(url):queries.append(url);return [{'lat':'35.87','lon':'128.60','addresstype':'building','display_name':'기념관'}]
            with patch('app.단계3_코스검토.좌표보완.장소파일',return_value=p):result=수집(query,쉬기=0)
            self.assertEqual(p.read_bytes(),before)
        self.assertEqual(len(queries),1);self.assertEqual(len(result),3)
        self.assertEqual(result[0]['사용'],'');self.assertEqual(result[0]['검토자'],'')
        self.assertEqual(result[1]['검토상태'],'진입점 자료 필요')
        self.assertEqual(result[2]['검토상태'],'공식 주소 필요')
