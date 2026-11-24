import unittest
from 공식좌표 import 추출, 후보수집


class 공식좌표시험(unittest.TestCase):
    def test_공식_마커형식과_장소이름을_대조한다(self):
        self.assertEqual(추출("findingAway('향촌문화관', '35.8733', '128.5941')",'향촌문화관'),('35.8733','128.5941'))
        self.assertEqual(추출('apiKakaoMap("map",\'원주통닭\',35.86837,128.597475);','원주통닭'),('35.86837','128.597475'))
        with self.assertRaises(ValueError):추출("findingAway('다른시설','35.8','128.6')",'향촌문화관')
        with self.assertRaises(ValueError):추출("findingAway('향촌문화관','128.6','35.8')",'향촌문화관')

    def test_수집은_후보만_만들고_실패도_남긴다(self):
        sources=[{'장소명':'향촌문화관','URL':'https://access.visitkorea.or.kr/ms/detail.do?cotId=example'},
                 {'장소명':'위험','URL':'http://127.0.0.1/internal'}]
        calls=[]
        def read(url):calls.append(url);return "findingAway('향촌문화관','35.8733','128.5941')"
        rows=후보수집(sources,read)
        self.assertEqual(len(calls),1)
        self.assertEqual(rows[0]['검토상태'],'검토대기')
        self.assertEqual(rows[0]['사용'],'')
        self.assertEqual(rows[1]['검토상태'],'수집실패')

    def test_기념관_주소핀은_정문으로_추정하지않는다(self):
        with self.assertRaises(ValueError):추출('placeX=861656; placeY=661819','국채보상운동기념관')

if __name__=='__main__':unittest.main()
