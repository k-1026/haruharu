import unittest
from 도로경로 import 경로검사, 경로수집


class 도로경로시험(unittest.TestCase):
    def response(self):
        return {'code':'Ok','waypoints':[{'distance':2},{'distance':3}],
                'routes':[{'distance':200,'duration':160,'geometry':{'type':'LineString','coordinates':[[128.6,35.86],[128.601,35.86],[128.601,35.861]]}}]}

    def test_좌표순서를_변환하고_도보출처를_보존한다(self):
        row=경로검사(self.response(),[35.86,128.6],[35.861,128.601])
        self.assertEqual(row['points'][1],[35.86,128.601])
        self.assertEqual(row['profile'],'foot')
        self.assertEqual(row['durationSeconds'],160)

    def test_실패_멀리보정_잘못된좌표는_직선으로_대체하지않는다(self):
        for kind in ['error','snap','coords','endpoint']:
            data=self.response()
            if kind=='error':data['code']='NoRoute'
            elif kind=='snap':data['waypoints'][0]['distance']=500
            elif kind=='coords':data['routes'][0]['geometry']['coordinates'][1]=[999,999]
            else:data['routes'][0]['geometry']['coordinates'][0]=[128,35]
            with self.subTest(kind=kind),self.assertRaises(ValueError):경로검사(data,[35.86,128.6],[35.861,128.601])

    def test_캐시는_재사용하고_누락과_일차를_건너뛰지않는다(self):
        stops=[{'일차':1,'좌표':[35.86,128.6]},{'일차':1,'좌표':[35.861,128.601]},
               {'일차':1,'좌표':None},{'일차':2,'좌표':[35.86,128.6]}]
        calls=[]
        def ask(url):calls.append(url);return self.response()
        result=경로수집(stops,{},ask,쉬기=0)
        again=경로수집(stops,result,lambda url:self.fail('캐시를 다시 조회함'),쉬기=0)
        self.assertEqual(len(calls),1);self.assertIn('/routed-foot/',calls[0])
        self.assertEqual(len(again['routes']),1)
