import unittest
from 시간조정 import 시간표_조정


def item(key,time,day=1,kind='가정'):
    return {'칸ID':key,'일차':day,'안':'공통','시각':{'값':time,'종류':kind},'머무는시간':90}


class 시간조정시험(unittest.TestCase):
    def test_11시34분기준_간격유지와_식사시각_동기화(self):
        obj={'칸목록':[item('낮','10:00'),item('점심','11:41'),item('밤','20:00'),item('오전','',2)],
             '식사목록':[{'칸ID':'점심','시각':{'값':'11:41','종류':'가정'}}]}
        report=시간표_조정(obj,{'시작일차':1,'시작시각':'11:34'},'1박2일')
        self.assertEqual([r['시각']['값'] for r in obj['칸목록']],['11:34','13:15','21:34',''])
        self.assertEqual(obj['식사목록'][0]['시각']['값'],'13:15')
        self.assertEqual(report['이동분'],94)
        self.assertEqual(시간표_조정(obj,{'시작일차':1,'시작시각':'11:34'},'1박2일')['이동분'],0)

    def test_일차미정은_기존일차를_보존(self):
        obj={'칸목록':[item('낮','10:00')],'식사목록':[]}
        report=시간표_조정(obj,{'시작일차':'미정','시작시각':'11:34'},'1박2일')
        self.assertEqual(obj['칸목록'][0]['일차'],1)
        self.assertTrue(any('일차 미정' in x for x in report['확인사항']))

    def test_확정시각은_멋대로_이동안함(self):
        obj={'칸목록':[item('낮','10:00'),item('예약','12:00',kind='확정')],'식사목록':[]}
        report=시간표_조정(obj,{'시작일차':1,'시작시각':'11:34'},'1박2일')
        self.assertEqual(obj['칸목록'][1]['시각']['값'],'12:00')
        self.assertTrue(any('확정' in x for x in report['확인사항']))

    def test_체류범위밖은_부분수정없이_거부(self):
        obj={'칸목록':[item('낮','10:00'),item('끝','23:30')],'식사목록':[]}
        with self.assertRaises(ValueError):시간표_조정(obj,{'시작일차':1,'시작시각':'23:00'},'당일')
        self.assertEqual(obj['칸목록'][0]['시각']['값'],'10:00')


if __name__=='__main__':unittest.main()
